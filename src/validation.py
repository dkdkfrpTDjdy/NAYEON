from __future__ import annotations

from .models import ExtractedRecord, ValidationIssue

REQUIRED_FIELDS = ["date", "slip_no", "vehicle_no", "real_weight_kg"]


def validate_records(
    records: list[ExtractedRecord],
    confidence_threshold: float = 0.70,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for record in records:
        reasons: list[str] = []
        for field_name in REQUIRED_FIELDS:
            value = getattr(record, field_name)
            if value in (None, ""):
                issues.append(
                    ValidationIssue(
                        seq=record.seq,
                        filename=record.filename,
                        level="ERROR",
                        field=field_name,
                        message="필수값 누락",
                    )
                )
                reasons.append(f"{field_name} 누락")

        if record.real_weight_kg is not None and record.real_weight_kg <= 0:
            issues.append(
                ValidationIssue(record.seq, record.filename, "ERROR", "real_weight_kg", "실중량은 0보다 커야 함")
            )
            reasons.append("실중량 비정상")

        if record.unit_price_krw is not None and record.unit_price_krw <= 0:
            issues.append(
                ValidationIssue(record.seq, record.filename, "ERROR", "unit_price_krw", "단가는 0보다 커야 함")
            )
            reasons.append("단가 비정상")

        expected_supply = None
        if record.real_weight_kg is not None and record.unit_price_krw is not None:
            expected_supply = record.real_weight_kg * record.unit_price_krw
        if expected_supply is not None and record.supply_amount_krw not in (None, expected_supply):
            issues.append(
                ValidationIssue(record.seq, record.filename, "WARN", "supply_amount_krw", "공급가액 재계산 필요")
            )
            reasons.append("공급가액 검산 불일치")

        if record.confidence is not None and record.confidence < confidence_threshold:
            issues.append(
                ValidationIssue(record.seq, record.filename, "WARN", "confidence", "OCR 평균 신뢰도 낮음")
            )
            reasons.append("OCR 신뢰도 낮음")

        if reasons:
            record.needs_review = True
            record.review_reason = "; ".join(reasons)
        else:
            record.needs_review = False
            record.review_reason = ""
    return issues
