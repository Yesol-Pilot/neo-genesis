# GEO Monthly Refresh — 2026-05-12

> 자동 생성: `scripts/hf_publish/refresh_geo_baseline_monthly.py`
> 데이터 window: 직전 **30일**
> source DB: `scripts/geo_measure/citations.sqlite3`

## 핵심 지표 (L1 + L2)

- **총 측정**: 726건
- **성공 측정**: 672건 (error 제외)
- **brand mention** (L1): 87건 = **12.9%**
- **canonical URL citation** (L2): 0건 = **0.00%**
- **founder mention**: 27건

## Category 별 (Trust Signal Gap 정밀 추적)

| category | total | brand | canonical URL |
|---|---|---|---|
| comparison | 108 | 0 (0.0%) | 0 (0.0%) |
| definition | 104 | 0 (0.0%) | 0 (0.0%) |
| pricing | 69 | 0 (0.0%) | 0 (0.0%) |
| problem_solving | 113 | 0 (0.0%) | 0 (0.0%) |
| product_specific | 209 | 46 (22.0%) | 0 (0.0%) |
| reputation | 69 | 41 (59.4%) | 0 (0.0%) |

## Provider 별

| provider | total | brand | canonical URL |
|---|---|---|---|
| gemini | 340 | 49 (14.4%) | 0 (0.0%) |
| openai | 332 | 38 (11.4%) | 0 (0.0%) |

## Trust Signal Gap 진단

🔴 **canonical URL citation 0건** — Trust signal gap 미해소 (baseline 유지)

## Strategy v1 Stop/Go 게이트 자동 평가

🔴 **PIVOT 검토**: brand mention rate baseline 미달

## 다음 cycle (자동)

- 다음 refresh 실행: 매월 1일 09:00 KST
- 다음 monthly delta 보고: 같은 형식
- HF dataset revision push: 변경 시
