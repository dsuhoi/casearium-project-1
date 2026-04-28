from __future__ import annotations

import json
import re
from typing import Any

from langchain_openai import ChatOpenAI

from app.config import Settings


class CloudJsonLLM:
    def __init__(self, settings: Settings, fast: bool = False) -> None:
        self.settings = settings
        self.model = settings.fast_text_model if fast else settings.default_text_model
        self.enabled = settings.cloud_enabled
        self._client = None
        if self.enabled:
            self._client = ChatOpenAI(
                model=self.model,
                base_url=settings.foundation_models_base_url,
                api_key=settings.foundation_models_api_key,
                temperature=0.05,
                max_tokens=900,
            )

    def invoke_json(self, system: str, user: str) -> dict[str, Any] | None:
        if not self._client:
            return None
        response = self._client.invoke(
            [
                ("system", f"{system}\nВерни только валидный JSON без markdown."),
                ("user", user),
            ],
            response_format={"type": "json_object"},
        )
        return parse_json_object(str(response.content or ""))


def parse_json_object(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fenced:
        try:
            parsed = json.loads(fenced.group(1))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass

    body = re.search(r"\{[\s\S]*\}", text)
    if body:
        try:
            parsed = json.loads(body.group(0))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
    return None
