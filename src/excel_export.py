from __future__ import annotations

from io import BytesIO

import xlsxwriter

from .approval import summarize_records
from .models import ExtractedRecord, OCRToken, ValidationIssue


def _write_title(ws, workbook, title: str, subtitle: str):
    title_fmt = workbook.add_format({"bold": True, "font_size": 18, "font_color": "#0F172A"})
    sub_fmt = workbook.add_format({"font_size": 10, "font_color": "#64748B"})
    ws.merge_range("A1:H1", title, title_fmt)
    ws.merge_range("A2:H2", subtitle, sub_fmt)


def _write_kpis(ws, workbook, records: list[ExtractedRecord]):
    summary = summarize_records(records)
    card_title = workbook.add_format({"bold": True, "font_color": "#64748B", "font_size": 9})
    card_value = workbook.add_format({"bold": True, "font_color": "#0F172A", "font_size": 16, "num_format": "#,##0"})
    card_note = workbook.add_format({"font_color": "#64748B", "font_size": 9})
    border_fmt = workbook.add_format({"border": 1, "border_color": "#DCE3ED", "bg_color": "#FFFFFF"})

    cards = [
        ("업로드 파일", summary["count"], "건"),
        ("검토 필요", summary["review_count"], "건"),
        ("실중량 합계", summary["real_weight_total"], "kg"),
        ("공급가액 합계", summary["supply_amount_total"], "원"),
    ]
    ranges = [("A4:B6", "A4", "A5", "B5"), ("C4:D6", "C4", "C5", "D5"), ("E4:F6", "E4", "E5", "F5"), ("G4:H6", "G4", "G5", "H5")]
    for (label, value, unit), (merge_range, label_cell, value_cell, unit_cell) in zip(cards, ranges):
        ws.merge_range(merge_range, "", border_fmt)
        ws.write(label_cell, label, card_title)
        ws.write_number(value_cell, value, card_value)
        ws.write(unit_cell, unit, card_note)


def build_first_excel(records: list[ExtractedRecord], tokens: list[OCRToken], issues: list[ValidationIssue]) -> bytes:
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    _write_record_sheet(workbook, "1차_추출데이터", records, include_review=True)
    _write_raw_sheet(workbook, tokens)
    _write_validation_sheet(workbook, issues)
    workbook.close()
    return output.getvalue()


def build_approval_excel(records: list[ExtractedRecord], tokens: list[OCRToken], issues: list[ValidationIssue]) -> bytes:
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    ws = workbook.add_worksheet("2차_품의서")
    ws.set_tab_color("#2563EB")
    ws.set_column("A:A", 8)
    ws.set_column("B:B", 13)
    ws.set_column("C:C", 12)
    ws.set_column("D:D", 14)
    ws.set_column("E:F", 14)
    ws.set_column("G:G", 10)
    ws.set_column("H:H", 16)
    ws.set_column("I:K", 18)

    _write_title(ws, workbook, "계근장 데이터 품의서", "AI OCR 1차 추출 + Python 검증 기반 최종 산출물")
    _write_kpis(ws, workbook, records)

    header_fmt = workbook.add_format(
        {"bold": True, "font_color": "#334155", "bg_color": "#F1F5F9", "border": 1, "border_color": "#DCE3ED", "align": "center", "valign": "vcenter"}
    )
    body_fmt = workbook.add_format({"border": 1, "border_color": "#E5E7EB", "align": "center", "valign": "vcenter"})
    num_fmt = workbook.add_format({"border": 1, "border_color": "#E5E7EB", "align": "right", "num_format": "#,##0"})
    money_fmt = workbook.add_format({"border": 1, "border_color": "#E5E7EB", "align": "right", "num_format": "#,##0"})
    warn_fmt = workbook.add_format({"border": 1, "border_color": "#E5E7EB", "align": "center", "bg_color": "#FEF3C7", "font_color": "#92400E"})
    ok_fmt = workbook.add_format({"border": 1, "border_color": "#E5E7EB", "align": "center", "bg_color": "#DCFCE7", "font_color": "#166534"})
    total_fmt = workbook.add_format({"bold": True, "bg_color": "#EAF0F7", "border": 1, "border_color": "#CBD5E1", "align": "right", "num_format": "#,##0"})
    total_label_fmt = workbook.add_format({"bold": True, "bg_color": "#EAF0F7", "border": 1, "border_color": "#CBD5E1", "align": "center"})

    headers = ["순번", "일자", "전표번호", "차량번호", "실중량(kg)", "95% 중량(kg)", "단가(원)", "공급가액(원)", "상태", "검토사유", "파일명"]
    start_row = 8
    for col, header in enumerate(headers):
        ws.write(start_row, col, header, header_fmt)

    for idx, record in enumerate(records, start=start_row + 1):
        excel_row = idx + 1
        values = [
            record.seq,
            record.date or "",
            record.slip_no or "",
            record.vehicle_no or "",
            record.real_weight_kg or 0,
            record.weight_95_kg or 0,
            record.unit_price_krw or 0,
        ]
        for col, value in enumerate(values):
            fmt = num_fmt if col in [4, 5, 6] else body_fmt
            ws.write(idx, col, value, fmt)
        ws.write_formula(idx, 7, f"=E{excel_row}*G{excel_row}", money_fmt, record.supply_amount_krw or 0)
        ws.write(idx, 8, "검토필요" if record.needs_review else "정상", warn_fmt if record.needs_review else ok_fmt)
        ws.write(idx, 9, record.review_reason, body_fmt)
        ws.write(idx, 10, record.filename, body_fmt)

    total_row = start_row + 1 + len(records)
    ws.merge_range(total_row, 0, total_row, 3, "합계", total_label_fmt)
    if records:
        first = start_row + 2
        last = total_row
        ws.write_formula(total_row, 4, f"=SUM(E{first}:E{last})", total_fmt)
        ws.write_formula(total_row, 5, f"=SUM(F{first}:F{last})", total_fmt)
        ws.write(total_row, 6, "-", total_label_fmt)
        ws.write_formula(total_row, 7, f"=SUM(H{first}:H{last})", total_fmt)
    else:
        for col in [4, 5, 7]:
            ws.write_number(total_row, col, 0, total_fmt)

    ws.freeze_panes(start_row + 1, 0)
    ws.autofilter(start_row, 0, max(total_row - 1, start_row), len(headers) - 1)

    note_row = total_row + 3
    note_fmt = workbook.add_format({"font_color": "#64748B", "font_size": 9})
    ws.merge_range(note_row, 0, note_row, 10, "처리 기준: 공급가액은 Excel 수식 = 실중량(kg) × 단가(원)으로 계산됩니다. 검토필요 행은 원본 이미지 확인 후 확정하십시오.", note_fmt)

    _write_record_sheet(workbook, "1차_추출데이터", records, include_review=True)
    _write_raw_sheet(workbook, tokens)
    _write_validation_sheet(workbook, issues)
    workbook.close()
    return output.getvalue()


def _write_record_sheet(workbook, sheet_name: str, records: list[ExtractedRecord], include_review: bool = True):
    ws = workbook.add_worksheet(sheet_name)
    ws.set_column("A:A", 8)
    ws.set_column("B:B", 30)
    ws.set_column("C:J", 15)
    ws.set_column("K:M", 25)

    header_fmt = workbook.add_format({"bold": True, "bg_color": "#EAF0F7", "border": 1, "align": "center"})
    body_fmt = workbook.add_format({"border": 1, "border_color": "#E5E7EB"})
    num_fmt = workbook.add_format({"border": 1, "border_color": "#E5E7EB", "num_format": "#,##0"})

    headers = [
        "순번", "파일명", "일자", "전표번호", "차량번호", "실중량(kg)", "95% 중량(kg)", "단가(원)", "공급가액(원)", "평균신뢰도", "상태", "검토사유", "추출방식"
    ]
    for col, header in enumerate(headers):
        ws.write(0, col, header, header_fmt)
    for row, record in enumerate(records, start=1):
        values = [
            record.seq,
            record.filename,
            record.date or "",
            record.slip_no or "",
            record.vehicle_no or "",
            record.real_weight_kg or 0,
            record.weight_95_kg or 0,
            record.unit_price_krw or 0,
            record.supply_amount_krw or 0,
            record.confidence or 0,
            "검토필요" if record.needs_review else "정상",
            record.review_reason,
            record.source,
        ]
        for col, value in enumerate(values):
            fmt = num_fmt if col in [5, 6, 7, 8] else body_fmt
            ws.write(row, col, value, fmt)
    ws.freeze_panes(1, 0)
    if records:
        ws.autofilter(0, 0, len(records), len(headers) - 1)


def _write_raw_sheet(workbook, tokens: list[OCRToken]):
    ws = workbook.add_worksheet("1차_OCR_RAW")
    ws.set_column("A:A", 30)
    ws.set_column("B:B", 8)
    ws.set_column("C:C", 60)
    ws.set_column("D:D", 12)
    ws.set_column("E:E", 60)
    header_fmt = workbook.add_format({"bold": True, "bg_color": "#EAF0F7", "border": 1})
    body_fmt = workbook.add_format({"border": 1, "border_color": "#E5E7EB"})
    headers = ["파일명", "페이지", "OCR 텍스트", "신뢰도", "BBox"]
    for col, header in enumerate(headers):
        ws.write(0, col, header, header_fmt)
    for row, token in enumerate(tokens, start=1):
        ws.write(row, 0, token.filename, body_fmt)
        ws.write(row, 1, token.page_no, body_fmt)
        ws.write(row, 2, token.text, body_fmt)
        ws.write(row, 3, token.confidence if token.confidence is not None else "", body_fmt)
        ws.write(row, 4, str(token.bbox or ""), body_fmt)
    ws.freeze_panes(1, 0)


def _write_validation_sheet(workbook, issues: list[ValidationIssue]):
    ws = workbook.add_worksheet("검증로그")
    ws.set_column("A:A", 8)
    ws.set_column("B:B", 30)
    ws.set_column("C:D", 15)
    ws.set_column("E:E", 60)
    header_fmt = workbook.add_format({"bold": True, "bg_color": "#EAF0F7", "border": 1})
    body_fmt = workbook.add_format({"border": 1, "border_color": "#E5E7EB"})
    headers = ["순번", "파일명", "레벨", "필드", "메시지"]
    for col, header in enumerate(headers):
        ws.write(0, col, header, header_fmt)
    if not issues:
        ws.write(1, 0, "검증 오류 없음", body_fmt)
        return
    for row, issue in enumerate(issues, start=1):
        ws.write(row, 0, issue.seq, body_fmt)
        ws.write(row, 1, issue.filename, body_fmt)
        ws.write(row, 2, issue.level, body_fmt)
        ws.write(row, 3, issue.field, body_fmt)
        ws.write(row, 4, issue.message, body_fmt)
    ws.freeze_panes(1, 0)
