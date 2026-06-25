# 계근장 OCR 데이터 추출 및 품의서 Excel 생성 시스템

이미지 계근장 파일을 업로드하면 로컬 Python OCR 엔진을 먼저 거쳐 1차 데이터를 추출하고, 선택적으로 OpenAI API로 2차 구조화 보정을 수행한 뒤, 1차 추출 Excel과 2차 품의서 Excel을 다운로드하는 Streamlit 웹앱입니다.

## 핵심 흐름

```text
이미지 업로드
→ Python 이미지 전처리
→ 로컬 OCR 엔진 EasyOCR 1차 추출
→ 규칙 기반 파서 1차 구조화
→ 선택 옵션: OpenAI Structured Outputs 2차 보정
→ Python 검증 및 산식 적용
→ 1차 Excel / 2차 품의서 Excel 다운로드
```

## 주요 기능

- JPG, PNG, BMP, GIF 이미지 다중 업로드
- 파일별 OCR 원문, 신뢰도, 추출 로그 보존
- 계근장 필드 추출
  - 일자
  - 전표번호
  - 차량번호
  - 실중량(kg)
  - 95% 중량(kg)
  - 단가(원)
  - 공급가액(원)
- 95% 중량 계산 기준 선택
  - 반올림
  - 버림
  - OCR 추출값 우선
- 검증 로그 생성
  - 필수값 누락
  - 중량/단가/공급가액 검산
  - 낮은 OCR confidence
  - 수기 검토 필요 여부
- 최종 Excel 산출물 생성
  - `2차_품의서`
  - `1차_추출데이터`
  - `1차_OCR_RAW`
  - `검증로그`

## 실행 방법

### 1. 로컬 실행

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
streamlit run app.py
```

### 2. Docker 실행

```bash
docker build -t weighbridge-ocr-approval-app .
docker run --env-file .env -p 8501:8501 weighbridge-ocr-approval-app
```

브라우저에서 접속:

```text
http://localhost:8501
```

## 환경 변수

`.env.example`을 `.env`로 복사한 뒤 필요한 값을 설정합니다.

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.5-mini
OCR_ENGINE=easyocr
DEFAULT_UNIT_PRICE=180
CONFIDENCE_REVIEW_THRESHOLD=0.70
```

OpenAI API 키가 없으면 로컬 OCR + 규칙 기반 파서만 사용합니다. API 키가 있으면 UI에서 `LLM 2차 보정 사용`을 켤 수 있습니다.

## GitHub 업로드 절차

```bash
git init
git add .
git commit -m "Initial weighbridge OCR approval app"
# GitHub CLI 사용 시
gh repo create weighbridge-ocr-approval-app --private --source=. --remote=origin --push
```

GitHub 웹에서 업로드할 경우, 이 폴더 전체를 새 repository에 올리면 됩니다.

## 폴더 구조

```text
weighbridge_ocr_approval_app/
├── app.py
├── requirements.txt
├── requirements-ci.txt
├── Dockerfile
├── .env.example
├── .gitignore
├── .streamlit/
│   └── config.toml
├── src/
│   ├── approval.py
│   ├── config.py
│   ├── excel_export.py
│   ├── image_preprocess.py
│   ├── llm_refine.py
│   ├── models.py
│   ├── ocr_engine.py
│   ├── parser.py
│   └── validation.py
├── prompts/
│   └── extract_prompt.md
├── docs/
│   ├── architecture.md
│   └── quality_metrics.md
├── samples/
│   ├── sample_records.csv
│   └── README.md
└── tests/
    ├── test_approval.py
    └── test_parser.py
```

## 운영 기준

이 앱은 LLM이 숫자를 최종 확정하지 않습니다. 숫자 계산과 검증은 Python 산식으로 처리합니다.

- 공급가액 = 실중량(kg) × 단가(원)
- 95% 중량 = 선택한 업무룰에 따라 계산
- OCR confidence가 낮거나 필수값이 누락된 행은 `검토필요`로 표시
- LLM 보정 결과도 Python validation을 통과해야 최종 산출물에 반영

## 한계

- 계근장 양식이 바뀌면 `src/parser.py`와 `prompts/extract_prompt.md`의 패턴을 조정해야 합니다.
- 필기체, 흐린 이미지, 심한 기울어짐, 저해상도 이미지는 수기 검토율이 높아질 수 있습니다.
- 운영 전 최소 50~100건 샘플로 필드별 정확도, 문서 완전일치율, 수기 검토율을 측정해야 합니다.
