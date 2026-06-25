from __future__ import annotations

import json
from pathlib import Path

from .models import ExtractedRecord

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "records": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "date": {"type": ["string", "null"], "description": "YYYY-MM-DD"},
                    "slip_no": {"type": ["string", "null"]},
                    "vehicle_no": {"type": ["string", "null"]},
                    "real_weight_kg": {"type": ["integer", "null"]},
                    "weight_95_kg": {"type": ["integer", "null"]},
                    "unit_price_krw": {"type": ["integer", "null"]},
                    "confidence": {"type": ["number", "null"]},
                    "needs_review": {"type": "boolean"},
                    "review_reason": {"type": "string"},
                },
                "required": [
                    "date",
                    "slip_no",
                    "vehicle_no",
                    "real_weight_kg",
                    "weight_95_kg",
                    "unit_price_krw",
                    "confidence",
                    "needs_review",
                    "review_reason",
                ],
            },
        },
        "document_notes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["records", "document_notes"],
}


def _load_prompt() -> str:
    prompt_path = Path(__file__).resolve().parents[1] / "prompts" / "extract_prompt.md"
    return prompt_path.read_text(encoding="utf-8")


def refine_records_with_llm(
    records: list[ExtractedRecord],
    api_key: str | None,
    model: str,
) -> list[ExtractedRecord]:
    if not api_key:
        return records

    try:
        from openai import OpenAI
    except Exception:
        return records

    client = OpenAI(api_key=api_key)
    refined: list[ExtractedRecord] = []

    for record in records:
        user_payload = {
            "filename": record.filename,
            "regex_record": {
                "date": record.date,
                "slip_no": record.slip_no,
                "vehicle_no": record.vehicle_no,
                "real_weight_kg": record.real_weight_kg,
                "weight_95_kg": record.weight_95_kg,
                "unit_price_krw": record.unit_price_krw,
                "confidence": record.confidence,
            },
            "ocr_text": record.raw_text,
        }
        try:
            response = client.responses.create(
                model=model,
                input=[
                    {
                        "role": "system",
                        "content": [{"type": "input_text", "text": _load_prompt()}],
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": json.dumps(user_payload, ensure_ascii=False),
                            }
                        ],
                    },
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "weighbridge_records",
                        "schema": SCHEMA,
                        "strict": True,
                    }
                },
            )
            content = getattr(response, "output_text", None)
            if not content:
                # SDK compatibility fallback. Avoid failing the whole batch.
                content = response.output[0].content[0].text
            parsed = json.loads(content)
            items = parsed.get("records") or []
            if not items:
                refined.append(record)
                continue
            item = items[0]
            record.date = item.get("date") or record.date
            record.slip_no = item.get("slip_no") or record.slip_no
            record.vehicle_no = item.get("vehicle_no") or record.vehicle_no
            record.real_weight_kg = item.get("real_weight_kg") or record.real_weight_kg
            record.weight_95_kg = item.get("weight_95_kg") or record.weight_95_kg
            record.unit_price_krw = item.get("unit_price_krw") or record.unit_price_krw
            record.confidence = item.get("confidence") or record.confidence
            record.needs_review = bool(item.get("needs_review", record.needs_review))
            record.review_reason = item.get("review_reason") or record.review_reason
            record.source = "llm_refined"
            refined.append(record)
        except Exception as exc:
            record.extra["llm_error"] = str(exc)
            refined.append(record)

    return refined
