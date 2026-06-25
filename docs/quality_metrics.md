# Quality Metrics

운영 배포 전 최소 50~100건의 실제 계근장 이미지로 측정한다.

| 지표 | 정의 | 목표 예시 |
|---|---|---:|
| Field Accuracy | 필드 단위 정답률 | 95% 이상 |
| Document Exact Match | 문서 1건 전체 필드 완전 일치율 | 90% 이상 |
| Numeric Accuracy | 실중량, 95% 중량, 단가, 공급가액 정답률 | 98% 이상 |
| Manual Review Rate | 검토필요로 분기된 비율 | 10% 이하 |
| False Pass Rate | 오류가 있는데 정상 처리된 비율 | 1% 이하 |
| Processing Time | 이미지 1장 처리 시간 | 10초 이하 |
| Cost per Document | LLM 사용 시 문서 1건당 비용 | 내부 기준 설정 |

## 검수 샘플 컬럼

```text
filename,date_true,slip_no_true,vehicle_no_true,real_weight_true,weight_95_true,unit_price_true
```

## 운영 중지 조건

- False Pass Rate가 1%를 넘는 경우
- 실중량/공급가액 오류가 반복되는 경우
- 새 계근장 양식에서 필드 누락이 3건 이상 연속 발생하는 경우
