from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class AppConfig:
    openai_api_key: str | None
    openai_model: str
    ocr_engine: str
    default_unit_price: int
    confidence_review_threshold: float
    max_upload_mb: int


def load_config() -> AppConfig:
    api_key = os.getenv("OPENAI_API_KEY") or None
    return AppConfig(
        openai_api_key=api_key,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5.5-mini"),
        ocr_engine=os.getenv("OCR_ENGINE", "easyocr").strip().lower(),
        default_unit_price=int(os.getenv("DEFAULT_UNIT_PRICE", "180")),
        confidence_review_threshold=float(os.getenv("CONFIDENCE_REVIEW_THRESHOLD", "0.70")),
        max_upload_mb=int(os.getenv("MAX_UPLOAD_MB", "50")),
    )
