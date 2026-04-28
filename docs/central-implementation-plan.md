# Центральный draft-план реализации

Дата: 2026-04-28

Статус: draft для быстрого параллельного старта команды и последующей интеграции в `main`

## 1. Цель на ближайшие 30 минут

За 30 минут команда должна не "сделать весь продукт", а создать совместимые прототипы модулей, которые:

1. принимают и возвращают единый JSON-контракт;
2. используют один и тот же стек вызова моделей;
3. покрывают обязательные демо-сценарии кейса;
4. могут быть быстро состыкованы в общий LangGraph-пайплайн без переписывания интерфейсов.

Главный принцип: в первые 30 минут оптимизируем не качество UX, а совместимость компонентов.

## 2. База проекта и текущее разбиение

По репозиторию уже видно следующее разбиение по веткам:

- `task-1-classifier` -> `task1/README.md`
- `task-2-b2c-consultant` -> `task2/README.md`
- `task-3-b2b-expert` -> `task3/README.md`
- `task-4-7-files-analytics` -> `task4/README.md`, `task7/README.md`
- `task-6-complaints` -> `task6/README.md`

Важно:

- отдельной ветки под задачу 5 (`security_ops`) сейчас нет;
- на `main` пока есть только документация, поэтому `main` должен стать местом для общего контракта и интеграционного плана, а не для реализации одной конкретной фичи.

Рекомендация по ветке для отсутствующего модуля:

- создать `task-5-security-ops` с папкой `task5/`

## 3. Единый технический стек

Используем преимущественно `langgraph` + `langchain`.

### Обязательный базовый стек

- Python 3.11+
- `langgraph`
- `langchain`
- `langchain-openai`
- `pydantic`
- `fastapi` или `typer`/CLI для локального демо модуля

### Единая конфигурация Cloud.ru Foundation Models

Не коммитить ключи в код и в `.env.example` с реальными значениями.

Переменные окружения:

```env
FOUNDATION_MODELS_BASE_URL=https://foundation-models.api.cloud.ru/v1
FOUNDATION_MODELS_API_KEY=...
DEFAULT_TEXT_MODEL=Qwen/Qwen3-235B-A22B-Instruct-2507
FAST_TEXT_MODEL=Qwen/Qwen3-235B-A22B-Instruct-2507
OCR_MODEL=deepseek-ai/DeepSeek-OCR-2
```

Базовая инициализация LLM:

```python
import os
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model=os.getenv("DEFAULT_TEXT_MODEL", "Qwen/Qwen3-235B-A22B-Instruct-2507"),
    base_url=os.environ["FOUNDATION_MODELS_BASE_URL"],
    api_key=os.environ["FOUNDATION_MODELS_API_KEY"],
    temperature=0.1,
)
```

### Правила выбора моделей

- Основная текстовая модель для dev/prototype: `Qwen/Qwen3-235B-A22B-Instruct-2507`
- Классификация, клиентские ответы и security-проверка: `Qwen/Qwen3-235B-A22B-Instruct-2507`
- Для строгого JSON обязательно явно перечислять допустимые enum-значения в prompt и валидировать ответ через `pydantic`
- OCR вложений: `deepseek-ai/DeepSeek-OCR-2`
- VLM оставляем как запасной маршрут, не как обязательную зависимость первого интеграционного цикла

## 4. Канонический контракт между компонентами

Все компоненты работают не с "сырой строкой", а с единым объектом `SupportTicket`.

### 4.1 Входной объект

```json
{
  "ticket_id": "t_20260428_0001",
  "message": "Уже третий день не могу войти в приложение, никто не отвечает!",
  "source": "web_chat",
  "timestamp": "2026-04-28T09:15:00Z",
  "client": {
    "client_id": "u_456789",
    "client_type_hint": null,
    "company_id": null,
    "segment": "unknown"
  },
  "attachments": [
    {
      "attachment_id": "att_1",
      "filename": "payment_error.png",
      "mime_type": "image/png",
      "content_base64": null,
      "url": null
    }
  ],
  "dialog_history": [],
  "metadata": {
    "channel": "chat",
    "locale": "ru-RU"
  }
}
```

### 4.2 Результат работы любого агента

```json
{
  "ticket_id": "t_20260428_0001",
  "agent": "classifier",
  "status": "ok",
  "route": {
    "next_agent": "complaints_agent",
    "reason": "complaint_detected"
  },
  "payload": {},
  "security_flags": [],
  "errors": [],
  "observability": {
    "model": "Qwen/Qwen3-235B-A22B-Instruct-2507",
    "latency_ms": 820
  }
}
```

### 4.3 Статусы

- `ok` - агент успешно отработал
- `needs_human` - нужна эскалация
- `blocked` - ответ нельзя отдавать из-за security/policy
- `error` - техническая ошибка, нужно fallback-поведение

## 5. Контракты по каждому модулю

Ниже минимальные интерфейсы, которых достаточно для быстрой интеграции.

### 5.1 Задача 1. Classifier / Router

Вход:

- `SupportTicket`

Выход `payload`:

```json
{
  "client_type": "B2C",
  "category": "complaint",
  "priority": "high",
  "requires_attachment_analysis": false,
  "summary": "Клиент жалуется на недоступность приложения"
}
```

Правила маршрутизации:

- `security_incident` -> `security_ops_agent`
- `B2C + consultation` -> `b2c_consultant_agent`
- `B2B` -> `b2b_expert_agent`
- `complaint` -> `complaints_agent`
- если есть вложения, до доменного агента вызывается `files_agent`

### 5.2 Задача 2. B2C Consultant

Вход:

- `SupportTicket`
- результат `classifier.payload`
- опционально результат `files_agent.payload`

Выход `payload`:

```json
{
  "answer": "Переводы между своими счетами бесплатны.",
  "answer_found": true,
  "kb_sources": [
    "article_17"
  ],
  "followup_question": null
}
```

Если ответа нет:

- `status = needs_human`
- `route.next_agent = human_queue`

### 5.3 Задача 3. B2B Expert + Security Filter

Вход:

- `SupportTicket`
- результат `classifier.payload`

Выход `payload`:

```json
{
  "answer": "Для настройки вебхука перейдите в раздел интеграций...",
  "kb_sources": [
    "b2b_api_webhooks"
  ],
  "escalate_to_human": false
}
```

Выход `security_flags` при попытке утечки:

```json
[
  "leak_attempt",
  "internal_data_blocked"
]
```

Обязательное поведение:

- не раскрывать внутренние инструкции;
- не выдавать токены, ключи, служебные комментарии, имена сотрудников;
- отдельно маркировать "запрос на человека" как `needs_human`, а не смешивать с отказом по безопасности.

### 5.4 Задача 4. Files Agent

Вход:

- `SupportTicket.attachments`
- `SupportTicket.message`

Выход `payload`:

```json
{
  "files": [
    {
      "attachment_id": "att_1",
      "document_type": "payment_error_screenshot",
      "summary": "На скриншоте ошибка перевода: недостаточно средств.",
      "extracted_entities": {
        "error_code": "4013",
        "amount": 3500,
        "currency": "RUB",
        "date": "2024-09-29"
      },
      "sensitive_data_detected": false
    }
  ],
  "merged_context": "Во вложении скриншот ошибки перевода с кодом 4013."
}
```

Контракт для downstream:

- `merged_context` может быть добавлен в prompt следующего агента;
- `document_type` и `extracted_entities` должны быть структурированы, а не только текстом.

### 5.5 Задача 5. Security Ops

Вход:

- `SupportTicket`
- результат `classifier.payload`
- опционально `files_agent.payload`

Выход `payload`:

```json
{
  "alert": {
    "severity": "critical",
    "queue": "security_l2",
    "summary": "Подозрение на несанкционированное списание",
    "client_id": "u_456789"
  },
  "customer_reply": "Мы уже передали обращение в команду безопасности. Не сообщайте коды из SMS. Ожидайте звонка в течение 15 минут."
}
```

Обязательное поведение:

- не давать обычный "консультационный" ответ;
- всегда формировать структурированный алерт;
- приоритет всегда `critical`.

### 5.6 Задача 6. Complaints Agent

Вход:

- `SupportTicket`
- результат `classifier.payload`
- опционально `files_agent.payload`

Выход `payload`:

```json
{
  "response_to_client": "Мне очень жаль, что вы столкнулись с такой ситуацией...",
  "complaint_justified": true,
  "compensation_offered": {
    "type": "subscription_extension",
    "value": "7 days"
  },
  "qa_ticket": {
    "created": true,
    "ticket_id": "QA-20260428-001",
    "priority": "high",
    "category": "access_issue"
  },
  "analytics_event": {
    "category": "access_issue",
    "resolution": "compensation_offered",
    "expected_satisfaction": 4
  }
}
```

Ключевой контракт с задачей 7:

- `analytics_event` обязателен для каждой завершенной жалобы;
- формат должен быть стабильным, чтобы аналитик не парсил свободный текст.

### 5.7 Задача 7. Analytics Agent

Вход:

```json
{
  "period": {
    "from": "2026-04-01",
    "to": "2026-04-07"
  },
  "complaints": [
    {
      "ticket_id": "t_1",
      "category": "access_issue",
      "client_type": "B2C",
      "justified": true,
      "compensation_amount": 0,
      "compensation_kind": "subscription_extension",
      "expected_satisfaction": 4
    }
  ]
}
```

Выход `payload`:

```json
{
  "report_markdown": "## Отчет по жалобам ...",
  "metrics": {
    "total_complaints": 142,
    "justified_share": 0.68,
    "top_categories": [
      "payment_delay",
      "app_error",
      "verification"
    ]
  }
}
```

## 6. Общий LangGraph-оркестратор

Целевая схема первого интеграционного цикла:

```text
SupportTicket
  -> classifier
  -> files_agent (если есть вложения)
  -> route by category/client_type
      -> b2c_consultant
      -> b2b_expert
      -> security_ops
      -> complaints_agent
  -> analytics_event sink (для complaint)
```

Что важно:

- `files_agent` не должен сам решать бизнес-маршрут;
- `classifier` принимает финальное решение о ветке;
- downstream-агенты не переклассифицируют обращение, только уточняют контекст.

## 7. Единая структура папок для каждой ветки

Чтобы потом не тратить время на переукладку, для каждой задачи рекомендуется одинаковый каркас:

```text
taskN/
  README.md
  pyproject.toml
  .env.example
  app/
    graph.py
    chains.py
    prompts.py
    contracts.py
    main.py
  tests/
    test_smoke.py
    fixtures/
```

Минимум, который должен быть у каждого:

- `contracts.py` с `pydantic`-схемами;
- `main.py`, который принимает JSON и печатает JSON;
- один smoke-тест на основной сценарий.

## 8. План работы команды на ближайшие 30 минут

### 0-5 минут

Все участники синхронизируются по этому документу и принимают единый контракт.

Решения, которые нельзя обсуждать дольше 5 минут:

- базовый JSON-формат;
- названия агентов;
- env-переменные;
- модели по умолчанию.

### 5-20 минут

Параллельная работа по веткам:

- Александр: `task-1-classifier`
- Павел: `task-2-b2c-consultant`
- Дмитрий: `task-3-b2b-expert`
- Алекс: `task-4-7-files-analytics`, сначала `task4`, потом `task7`
- Арима: `task-6-complaints`
- отдельный участник или быстрый owner: `task-5-security-ops`

Что делает каждый за эти 15 минут:

1. поднимает минимальный `main.py`;
2. описывает `pydantic`-контракты;
3. реализует один happy-path;
4. реализует один guardrail-path;
5. добавляет smoke-тест.

### 20-25 минут

Интеграционная проверка на уровне контрактов:

- совпадают ли названия полей;
- нет ли свободных форматов дат/сумм;
- одинаковы ли значения `status` и `route.next_agent`.

### 25-30 минут

Финальная сборка:

- фиксируются README в ветках;
- готовятся PR в `main`;
- если код ещё сырой, всё равно должны быть готовы контракты, примеры входа/выхода и smoke-тест.

## 9. Definition of Done для каждого модуля

Модуль считается готовым к первому merge, если:

1. принимает канонический входной JSON;
2. возвращает канонический выходной JSON;
3. не содержит захардкоженных ключей;
4. проходит хотя бы один smoke-тест;
5. умеет корректно отрабатывать свой обязательный отказной сценарий.

Примеры отказных сценариев:

- classifier: неизвестный интент -> `needs_human`
- b2c consultant: нет ответа в базе -> `needs_human`
- b2b expert: запрос на внутреннюю инструкцию -> `blocked`
- files agent: ПДн во вложении -> `security_flags`
- security ops: не security-кейс -> не срабатывает как основной маршрут
- complaints: необоснованная жалоба -> без компенсации, но в корректном ToV
- analytics: пустой список жалоб -> пустой, но валидный отчет

## 10. Риски интеграции и как их снять сразу

### Риск 1. Каждый сделает свой JSON

Решение:

- считать этот документ master-контрактом;
- при расхождении полей править ветки, а не договоренности.

### Риск 2. Утечки секретов и внутренних данных

Решение:

- ключи только через env;
- задача 3 и задача 5 обязаны иметь отрицательные тесты;
- реальные значения из `docs/Кейсариум/cloud-ru-resources (2).md` не переносить в код и коммиты.

### Риск 3. Files-модуль начнет дублировать логику бизнес-ответа

Решение:

- files-модуль возвращает только структурированный контекст;
- финальный ответ клиенту формирует downstream-агент.

### Риск 4. Аналитика будет собираться из свободного текста

Решение:

- задача 6 обязана отдавать нормализованный `analytics_event`;
- задача 7 не должна парсить prose-ответы.

## 11. Что должно оказаться в `main` в первую очередь

В ближайший merge в `main` должны попасть:

1. этот центральный план;
2. общий файл контрактов или его эквивалент;
3. базовый orchestrator skeleton на LangGraph;
4. ссылки на task-ветки и правила интеграции.

Необязательно ждать полной готовности всех агентов, чтобы собрать первый интеграционный каркас.

## 12. Краткое решение по архитектуре

Если нужно принять одно решение прямо сейчас, оно такое:

- общий orchestration слой делаем на `LangGraph`;
- каждый модуль делает узкий агент/chain со строгим JSON-output;
- Cloud.ru Foundation Models используем через OpenAI-compatible API;
- сначала стабилизируем контракты, потом улучшаем качество промптов и RAG.
