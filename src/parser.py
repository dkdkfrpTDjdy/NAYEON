from __future__ import annotations

import re
from statistics import mean

from .models import ExtractedRecord, OCRToken

DATE_PATTERNS = [
    re.compile(r"(?P<y>20\d{2})[.\-/년\s]+(?P<m>\d{1,2})[.\-/월\s]+(?P<d>\d{1,2})"),
    re.compile(r"(?P<y>\d{2})[.\-/년\s]+(?P<m>\d{1,2})[.\-/월\s]+(?P<d>\d{1,2})"),
]

WEIGHT_PATTERN = re.compile(r"(?P<num>\d{1,3}(?:[,\s]?\d{3})+|\d{4,6})(?:\s?kg|\s?KG|\s?킬로)?")
REAL_WEIGHT_LABEL_PATTERN = re.compile(r"(?:실중량|순중량|정산중량|net\s*weight|net)[^0-9]{0,12}(?P<num>\d{1,3}(?:[,\s]?\d{3})+|\d{4,6})", re.IGNORECASE)
WEIGHT_95_LABEL_PATTERN = re.compile(r"(?:95\s*%|95퍼센트|구십오)[^0-9]{0,12}(?P<num>\d{1,3}(?:[,\s]?\d{3})+|\d{4,6})", re.IGNORECASE)
SLIP_PATTERN = re.compile(r"(?:전표|계량|No\.?|NO\.?|번호)[^0-9]{0,10}(?P<num>\d{3,8})", re.IGNORECASE)
VEHICLE_PATTERNS = [
    re.compile(r"(?P<veh>\d{2,3}[가-힣]\s?\d{4})"),
    re.compile(r"(?P<veh>\d{4,6})"),
]


def normalize_number(text: str) -> int | None:
    cleaned = re.sub(r"[^0-9]", "", text or "")
    if not cleaned:
        return None
    return int(cleaned)


def normalize_date(text: str) -> str | None:
    for pattern in DATE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        y = int(match.group("y"))
        if y < 100:
            y += 2000
        m = int(match.group("m"))
        d = int(match.group("d"))
        if 1 <= m <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{m:02d}-{d:02d}"
    return None


def tokens_to_text(tokens: list[OCRToken]) -> str:
    return "\n".join(token.text for token in tokens if token.text)


def extract_slip_no(raw_text: str) -> str | None:
    match = SLIP_PATTERN.search(raw_text)
    if match:
        return match.group("num")
    numeric_candidates = re.findall(r"\b\d{3}\b", raw_text)
    return numeric_candidates[0] if numeric_candidates else None


def extract_vehicle_no(raw_text: str) -> str | None:
    for pattern in VEHICLE_PATTERNS:
        match = pattern.search(raw_text)
        if match:
            return match.group("veh").replace(" ", "")
    return None


def extract_weight_candidates(raw_text: str) -> list[int]:
    candidates: list[int] = []
    for match in WEIGHT_PATTERN.finditer(raw_text):
        value = normalize_number(match.group("num"))
        if value is None:
            continue
        if 100 <= value <= 200000:
            candidates.append(value)
    return candidates


def choose_real_weight(candidates: list[int]) -> int | None:
    if not candidates:
        return None
    plausible = [v for v in candidates if v >= 1000]
    return plausible[0] if plausible else candidates[0]


def extract_labeled_number(raw_text: str, pattern: re.Pattern[str]) -> int | None:
    match = pattern.search(raw_text)
    if not match:
        return None
    return normalize_number(match.group("num"))


def extract_real_weight(raw_text: str, candidates: list[int]) -> int | None:
    labeled = extract_labeled_number(raw_text, REAL_WEIGHT_LABEL_PATTERN)
    if labeled is not None:
        return labeled
    return choose_real_weight(candidates)


def extract_weight_95(raw_text: str) -> int | None:
    return extract_labeled_number(raw_text, WEIGHT_95_LABEL_PATTERN)


def average_confidence(tokens: list[OCRToken]) -> float | None:
    values = [t.confidence for t in tokens if t.confidence is not None]
    if not values:
        return None
    return float(mean(values))


def parse_record_from_tokens(
    tokens: list[OCRToken],
    seq: int,
    filename: str,
    default_unit_price: int,
) -> ExtractedRecord:
    raw_text = tokens_to_text(tokens)
    weights = extract_weight_candidates(raw_text)
    return ExtractedRecord(
        seq=seq,
        filename=filename,
        date=normalize_date(raw_text),
        slip_no=extract_slip_no(raw_text),
        vehicle_no=extract_vehicle_no(raw_text),
        real_weight_kg=extract_real_weight(raw_text, weights),
        weight_95_kg=extract_weight_95(raw_text),
        unit_price_krw=default_unit_price,
        confidence=average_confidence(tokens),
        source="regex",
        raw_text=raw_text,
        extra={"weight_candidates": weights},
    )
