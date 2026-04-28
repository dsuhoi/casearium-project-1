from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class RoutingResult:
    """Structured routing result passed to downstream agents."""

    client_type: str
    category: str
    priority: str
    route_to: str
    confidence: float
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataclass to plain dict for transport/serialization."""
        return {
            "client_type": self.client_type,
            "category": self.category,
            "priority": self.priority,
            "route_to": self.route_to,
            "confidence": self.confidence,
            "summary": self.summary,
        }


class SupportRequestClassifier:
    """Rule-based classifier for first-line fintech support requests."""

    B2B_TRIGGERS = [
        "api",
        "вебхук",
        "webhook",
        "интеграц",
        "инн",
        "договор",
        "счет компании",
        "корпоратив",
        "менеджер",
    ]
    B2C_TRIGGERS = [
        "личн",
        "карта",
        "приложен",
        "мой счет",
        "мне",
        " я ",
    ]
    REPEAT_TRIGGERS = ["уже", "третий день", "снова", "повторно", "до сих пор", "никто не отвечает"]

    CATEGORY_TRIGGERS = {
        "security_incident": [
            "взлом",
            "украли",
            "несанкционирован",
            "не я",
            "потерял доступ",
            "не мой",
            "списани",
        ],
        "complaint": [
            "не работает",
            "верните деньги",
            "уже третий день",
            "никто не отвечает",
            "жалоба",
            "хватит",
        ],
        "technical_issue": [
            "api",
            "вебхук",
            "webhook",
            "ошибка",
            "не подключается",
            "настрой",
            "интеграц",
        ],
        "consultation": [
            "тариф",
            "комисси",
            "услови",
            "как работает",
            "как настроить",
            "какая",
        ],
    }
    ESCALATION_TRIGGERS = ["соедините", "живым менеджером", "хватит ботов", "оператор", "человек"]

    def classify(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Classify raw request payload and return routing metadata."""
        message = str(payload.get("message", "")).strip()
        message_norm = f" {message.lower()} "

        client_type, client_hits = self._detect_client_type(message_norm)
        category, category_hits = self._detect_category(message_norm)
        priority = self._detect_priority(category, message_norm)
        route_to = self._detect_route(client_type, category)
        confidence = self._estimate_confidence(client_hits, category_hits, category)
        summary = self._build_summary(client_type, category, message)

        return RoutingResult(
            client_type=client_type,
            category=category,
            priority=priority,
            route_to=route_to,
            confidence=confidence,
            summary=summary,
        ).to_dict()

    def _detect_client_type(self, message: str) -> tuple[str, int]:
        """Detect B2B/B2C using keyword hits and return score."""
        b2b_hits = self._count_hits(message, self.B2B_TRIGGERS)
        b2c_hits = self._count_hits(message, self.B2C_TRIGGERS)
        if b2b_hits > b2c_hits:
            return "B2B", b2b_hits
        return "B2C", max(b2c_hits, 1)

    def _detect_category(self, message: str) -> tuple[str, int]:
        """Detect request category with escalation override and tie-breaks."""
        if self._count_hits(message, self.ESCALATION_TRIGGERS):
            return "escalation", 1

        ranked: List[tuple[str, int]] = []
        for category, triggers in self.CATEGORY_TRIGGERS.items():
            ranked.append((category, self._count_hits(message, triggers)))

        # При равенстве берем более критичный порядок категорий.
        priority_order = ["security_incident", "complaint", "technical_issue", "consultation"]
        ranked.sort(key=lambda item: (item[1], -priority_order.index(item[0])), reverse=True)
        best_category, best_hits = ranked[0]
        if best_hits == 0:
            return "consultation", 1
        return best_category, best_hits

    def _detect_priority(self, category: str, message: str) -> str:
        """Map category and repeat signals to business priority."""
        if category == "security_incident":
            return "Critical"
        if category in {"complaint", "escalation"} or self._count_hits(message, self.REPEAT_TRIGGERS):
            return "High"
        return "Normal"

    def _detect_route(self, client_type: str, category: str) -> str:
        """Route request to target agent based on category/client rules."""
        if category == "security_incident":
            return "security_ops_agent"
        if category == "complaint":
            return "complaints_agent"
        if category == "escalation":
            return "human_agent"
        if client_type == "B2B":
            return "b2b_expert_agent"
        return "b2c_consultant_agent"

    @staticmethod
    def _count_hits(message: str, triggers: List[str]) -> int:
        """Count how many trigger fragments are present in message."""
        return sum(1 for trigger in triggers if trigger in message)

    @staticmethod
    def _estimate_confidence(client_hits: int, category_hits: int, category: str) -> float:
        """Estimate confidence score from number of trigger matches."""
        base = 0.65
        base += min(client_hits, 3) * 0.08
        base += min(category_hits, 3) * 0.09
        if category in {"security_incident", "escalation"}:
            base += 0.05
        return round(min(base, 0.99), 2)

    @staticmethod
    def _build_summary(client_type: str, category: str, message: str) -> str:
        """Build short human-readable summary for logs/context."""
        snippets = {
            "consultation": "Консультационный запрос",
            "complaint": "Жалоба клиента",
            "security_incident": "Признаки инцидента безопасности",
            "technical_issue": "Технический вопрос/ошибка",
            "escalation": "Запрос на перевод к человеку",
        }
        excerpt = message[:80].replace("\n", " ")
        return f"{snippets.get(category, 'Запрос клиента')} ({client_type}): {excerpt}"


def classify_support_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience wrapper around SupportRequestClassifier."""
    return SupportRequestClassifier().classify(payload)


if __name__ == "__main__":
    sample_input = {
        "message": "Как настроить вебхук для уведомлений о платежах?",
        "source": "web_chat",
        "timestamp": "2026-04-28T09:15:00Z",
        "user_id": "u_123456",
    }
    print(classify_support_request(sample_input))
