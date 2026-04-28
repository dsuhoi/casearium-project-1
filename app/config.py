from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import os

from pydantic import BaseModel


class Settings(BaseModel):
    foundation_models_base_url: str = "https://foundation-models.api.cloud.ru/v1"
    foundation_models_api_key: str = ""
    default_text_model: str = "Qwen/Qwen3-235B-A22B-Instruct-2507"
    fast_text_model: str = "Qwen/Qwen3-235B-A22B-Instruct-2507"
    ocr_model: str = "deepseek-ai/DeepSeek-OCR-2"
    rag_docs_dir: Path = Path("docs/Кейсариум")

    @property
    def cloud_enabled(self) -> bool:
        return bool(self.foundation_models_api_key.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        foundation_models_base_url=os.getenv("FOUNDATION_MODELS_BASE_URL", Settings.model_fields["foundation_models_base_url"].default),
        foundation_models_api_key=os.getenv("FOUNDATION_MODELS_API_KEY", ""),
        default_text_model=os.getenv("DEFAULT_TEXT_MODEL", Settings.model_fields["default_text_model"].default),
        fast_text_model=os.getenv("FAST_TEXT_MODEL", Settings.model_fields["fast_text_model"].default),
        ocr_model=os.getenv("OCR_MODEL", Settings.model_fields["ocr_model"].default),
        rag_docs_dir=Path(os.getenv("RAG_DOCS_DIR", str(Settings.model_fields["rag_docs_dir"].default))),
    )
