from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OCRToken:
    filename: str
    page_no: int
    text: str
    confidence: float | None = None
    bbox: list[list[float]] | None = None


@dataclass
class ExtractedRecord:
    seq: int
    filename: str
    date: str | None = None
    slip_no: str | None = None
    vehicle_no: str | None = None
    real_weight_kg: int | None = None
    weight_95_kg: int | None = None
    unit_price_krw: int = 180
    supply_amount_krw: int | None = None
    confidence: float | None = None
    needs_review: bool = False
    review_reason: str = ""
    source: str = "regex"
    raw_text: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationIssue:
    seq: int
    filename: str
    level: str
    field: str
    message: str


@dataclass
class ExtractionResult:
    records: list[ExtractedRecord]
    tokens: list[OCRToken]
    validation_issues: list[ValidationIssue]
