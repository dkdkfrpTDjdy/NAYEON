from __future__ import annotations

import math
from copy import deepcopy

from .models import ExtractedRecord


def calculate_weight_95(real_weight_kg: int | None, method: str = "round") -> int | None:
    if real_weight_kg is None:
        return None
    value = real_weight_kg * 0.95
    if method == "floor":
        return int(math.floor(value))
    if method == "ceil":
        return int(math.ceil(value))
    return int(round(value))


def calculate_supply_amount(real_weight_kg: int | None, unit_price_krw: int | None) -> int | None:
    if real_weight_kg is None or unit_price_krw is None:
        return None
    return int(real_weight_kg * unit_price_krw)


def apply_business_rules(
    records: list[ExtractedRecord],
    weight_95_method: str,
    default_unit_price: int,
    prefer_ocr_95: bool = False,
) -> list[ExtractedRecord]:
    output: list[ExtractedRecord] = []
    for record in records:
        item = deepcopy(record)
        if not item.unit_price_krw:
            item.unit_price_krw = default_unit_price
        if not prefer_ocr_95 or item.weight_95_kg is None:
            item.weight_95_kg = calculate_weight_95(item.real_weight_kg, weight_95_method)
        item.supply_amount_krw = calculate_supply_amount(item.real_weight_kg, item.unit_price_krw)
        output.append(item)
    return output


def summarize_records(records: list[ExtractedRecord]) -> dict[str, int]:
    return {
        "count": len(records),
        "real_weight_total": sum(r.real_weight_kg or 0 for r in records),
        "weight_95_total": sum(r.weight_95_kg or 0 for r in records),
        "supply_amount_total": sum(r.supply_amount_krw or 0 for r in records),
        "review_count": sum(1 for r in records if r.needs_review),
    }
