# Architecture

## 목표

계근장 이미지에서 업무용 데이터를 추출하고, 검증 가능한 Excel 산출물로 변환한다.

## 파이프라인

```text
Streamlit UI
→ 이미지 업로드
→ src.image_preprocess
→ src.ocr_engine.EasyOCREngine
→ src.parser 규칙 기반 1차 구조화
→ src.llm_refine 선택형 LLM 2차 보정
→ src.approval 업무 산식 적용
→ src.validation 검증
→ src.excel_export Excel 생성
```

## Layer 분리

| Layer | 파일 | 책임 |
|---|---|---|
| UI | app.py | 업로드, 실행 버튼, KPI 카드, 결과 테이블, 다운로드 |
| OCR | image_preprocess.py, ocr_engine.py | 이미지 보정, 로컬 OCR 실행 |
| 구조화 | parser.py, llm_refine.py | OCR 텍스트를 계근장 필드로 변환 |
| 업무룰 | approval.py | 95% 중량, 공급가액 계산 |
| 검증 | validation.py | 필수값, confidence, 산식 검증 |
| 출력 | excel_export.py | 1차 Excel, 2차 품의서 Excel 생성 |

## 비즈니스 룰

- 공급가액은 `실중량(kg) × 단가(원)`으로 계산한다.
- 95% 중량은 UI 선택 기준에 따른다.
- LLM은 숫자 계산의 기준이 아니다.
- 검토필요 행은 최종 승인 전 원본 계근장 이미지로 확인한다.

## 확장 포인트

- 계근장 양식별 parser 추가: `src/parser.py`
- 거래처별 단가표 연동: `src/approval.py`
- DB 저장: `src/repository.py` 추가
- FastAPI 백엔드 전환: Streamlit UI를 API client로 바꾸고 현재 src 모듈 재사용
