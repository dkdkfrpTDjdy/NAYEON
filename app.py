from __future__ import annotations

import traceback
from datetime import datetime

import pandas as pd
import streamlit as st

from src.approval import apply_business_rules, summarize_records
from src.config import load_config
from src.excel_export import build_approval_excel, build_first_excel
from src.llm_refine import refine_records_with_llm
from src.models import ExtractedRecord, OCRToken, ValidationIssue
from src.ocr_engine import get_ocr_engine
from src.parser import parse_record_from_tokens
from src.validation import validate_records

st.set_page_config(page_title="계근장 데이터 추출 시스템", page_icon="⚖️", layout="wide")

CUSTOM_CSS = """
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
[data-testid="stHeader"] {background: #F8FAFC;}
.main {background: #F8FAFC;}
.card {
  border: 1px solid #DCE3ED;
  background: #FFFFFF;
  border-radius: 16px;
  padding: 18px 20px;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.05);
}
.card-title {font-size: 13px; color: #64748B; font-weight: 700; margin-bottom: 6px;}
.card-value {font-size: 28px; color: #0F172A; font-weight: 800; line-height: 1.1;}
.card-unit {font-size: 13px; color: #64748B; font-weight: 700; margin-left: 4px;}
.panel {
  border: 1px solid #DCE3ED;
  background: #FFFFFF;
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.05);
}
.small-muted {font-size: 12px; color: #94A3B8;}
.status-ok {color: #16A34A; font-weight: 700;}
.status-warn {color: #D97706; font-weight: 700;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

config = load_config()


def init_state():
    defaults = {
        "records": [],
        "tokens": [],
        "issues": [],
        "last_error": None,
        "processed": False,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def record_to_dict(record: ExtractedRecord) -> dict:
    return {
        "순번": record.seq,
        "일자": record.date or "",
        "전표번호": record.slip_no or "",
        "차량번호": record.vehicle_no or "",
        "실중량(kg)": record.real_weight_kg or 0,
        "95% 중량(kg)": record.weight_95_kg or 0,
        "단가(원)": record.unit_price_krw or 0,
        "공급가액(원)": record.supply_amount_krw or 0,
        "상태": "검토필요" if record.needs_review else "정상",
        "검토사유": record.review_reason,
        "파일명": record.filename,
    }


def render_card(label: str, value: str | int, unit: str = ""):
    st.markdown(
        f"""
        <div class="card">
            <div class="card-title">{label}</div>
            <span class="card-value">{value}</span><span class="card-unit">{unit}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def run_extraction(uploaded_files, unit_price: int, weight_95_method: str, prefer_ocr_95: bool, use_llm: bool):
    all_tokens: list[OCRToken] = []
    records: list[ExtractedRecord] = []
    engine = get_ocr_engine(config.ocr_engine)

    for seq, uploaded in enumerate(uploaded_files, start=1):
        image_bytes = uploaded.getvalue()
        file_tokens = engine.extract(image_bytes, filename=uploaded.name, page_no=1)
        all_tokens.extend(file_tokens)
        record = parse_record_from_tokens(file_tokens, seq=seq, filename=uploaded.name, default_unit_price=unit_price)
        record.unit_price_krw = unit_price
        records.append(record)

    records = apply_business_rules(
        records,
        weight_95_method=weight_95_method,
        default_unit_price=unit_price,
        prefer_ocr_95=prefer_ocr_95,
    )

    if use_llm:
        records = refine_records_with_llm(records, api_key=config.openai_api_key, model=config.openai_model)
        records = apply_business_rules(
            records,
            weight_95_method=weight_95_method,
            default_unit_price=unit_price,
            prefer_ocr_95=prefer_ocr_95,
        )

    issues = validate_records(records, confidence_threshold=config.confidence_review_threshold)
    return records, all_tokens, issues


init_state()

header_left, header_right = st.columns([1.8, 2.2])
with header_left:
    st.markdown("### ⚖️ 계근장 데이터 추출 시스템")
    st.markdown("<div class='small-muted'>AI 이미지 인식 기반 자동 데이터 추출 및 품의서 변환</div>", unsafe_allow_html=True)
with header_right:
    b1, b2, b3 = st.columns([1.1, 1, 1.2])
    with b1:
        start_clicked = st.button("▷ 1차 데이터 추출 시작", type="primary", use_container_width=True)
    with b2:
        first_excel_placeholder = st.empty()
    with b3:
        approval_excel_placeholder = st.empty()

st.divider()

left, right = st.columns([1.05, 2.15], gap="large")

with left:
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.subheader("이미지 업로드")
    uploaded_files = st.file_uploader(
        "계근장 이미지를 여기에 업로드하세요",
        type=["jpg", "jpeg", "png", "bmp", "gif"],
        accept_multiple_files=True,
        label_visibility="visible",
    )
    st.caption("JPG, PNG, BMP, GIF 지원")

    st.markdown("#### 처리 설정")
    unit_price = st.number_input("단가(원)", min_value=1, value=config.default_unit_price, step=1)
    method_label = st.selectbox("95% 중량 계산 기준", ["반올림", "버림", "올림"], index=0)
    method_map = {"반올림": "round", "버림": "floor", "올림": "ceil"}
    prefer_ocr_95 = st.checkbox("OCR에서 95% 중량이 읽히면 그 값을 우선 사용", value=False)
    use_llm = st.checkbox("LLM 2차 보정 사용", value=False, disabled=not bool(config.openai_api_key))
    if not config.openai_api_key:
        st.caption("OPENAI_API_KEY가 없어 LLM 2차 보정은 비활성화됩니다.")

    if uploaded_files:
        st.markdown(f"#### 업로드된 파일 ({len(uploaded_files)}개)")
        for file in uploaded_files:
            st.write(f"✅ {file.name} · {len(file.getvalue()) / 1024:,.0f} KB")
    st.markdown("</div>", unsafe_allow_html=True)

if start_clicked:
    if not uploaded_files:
        st.warning("이미지를 먼저 업로드하세요.")
    else:
        with st.spinner("OCR 추출 및 품의서 데이터 생성 중입니다..."):
            try:
                records, tokens, issues = run_extraction(
                    uploaded_files,
                    unit_price=int(unit_price),
                    weight_95_method=method_map[method_label],
                    prefer_ocr_95=prefer_ocr_95,
                    use_llm=use_llm,
                )
                st.session_state.records = records
                st.session_state.tokens = tokens
                st.session_state.issues = issues
                st.session_state.processed = True
                st.session_state.last_error = None
            except Exception:
                st.session_state.last_error = traceback.format_exc()
                st.session_state.processed = False

records: list[ExtractedRecord] = st.session_state.records
issues: list[ValidationIssue] = st.session_state.issues
summary = summarize_records(records)

with right:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_card("업로드 파일", len(uploaded_files or []), "")
    with c2:
        render_card("추출 대기", max(len(uploaded_files or []) - summary["count"], 0), "")
    with c3:
        render_card("추출 완료", summary["count"], "")
    with c4:
        render_card("실중량 합계", f"{summary['real_weight_total']:,}", "kg")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.subheader(f"추출된 데이터 · {summary['count']}건")

    if st.session_state.last_error:
        st.error("처리 중 오류가 발생했습니다.")
        st.code(st.session_state.last_error)
    elif records:
        df = pd.DataFrame([record_to_dict(r) for r in records])
        st.dataframe(df, use_container_width=True, hide_index=True)

        if issues:
            st.markdown("#### 검증 로그")
            issue_df = pd.DataFrame([
                {
                    "순번": issue.seq,
                    "파일명": issue.filename,
                    "레벨": issue.level,
                    "필드": issue.field,
                    "메시지": issue.message,
                }
                for issue in issues
            ])
            st.dataframe(issue_df, use_container_width=True, hide_index=True)
        else:
            st.markdown("<span class='status-ok'>검증 오류 없음</span>", unsafe_allow_html=True)
    else:
        st.info("이미지 업로드 후 `1차 데이터 추출 시작`을 누르면 결과가 표시됩니다.")
    st.markdown("</div>", unsafe_allow_html=True)

# Header download buttons are populated after records exist.
if records:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    first_excel = build_first_excel(records, st.session_state.tokens, issues)
    approval_excel = build_approval_excel(records, st.session_state.tokens, issues)
    with first_excel_placeholder:
        st.download_button(
            "⇩ 1차 엑셀 다운로드",
            data=first_excel,
            file_name=f"계근장_1차_데이터_{timestamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with approval_excel_placeholder:
        st.download_button(
            "▣ 2차 품의서 엑셀 다운로드",
            data=approval_excel,
            file_name=f"계근장_2차_품의서_{timestamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
else:
    with first_excel_placeholder:
        st.button("⇩ 1차 엑셀 다운로드", disabled=True, use_container_width=True)
    with approval_excel_placeholder:
        st.button("▣ 2차 품의서 엑셀 다운로드", disabled=True, use_container_width=True)
