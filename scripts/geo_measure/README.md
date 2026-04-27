# Neo Genesis GEO/LLMO Citation Measurement

> Reference: `.agent/knowledge/20260427_AI_TRAFFIC_MAXIMIZATION_MASTER_v1.md` Phase 0 §6
> 목적: 4 LLM (Anthropic / OpenAI / Perplexity / Gemini) 응답에서 Neo Genesis + 11 SBU mention 빈도 측정 → baseline + 트렌드 자동 추적

## 구조

| 파일 | 역할 |
|---|---|
| `seed_prompts.json` | 30 시드 prompt (definition / comparison / problem-solving / pricing / reputation / product-specific 6 카테고리) |
| `measure_citations.py` | 매일 4 LLM 호출 + 응답 파싱 + sqlite 저장 |
| `aggregate_report.py` | 일/주/월 리포트 자동 생성 (Markdown + JSON) |
| `citations.sqlite3` | 로컬 측정 DB (자동 생성) |

## 비용 (월)

30 prompt × 4 provider × 30회/월 = 3,600 calls

| Provider | 단가 (대략) | 월 비용 |
|---|---|---|
| Anthropic Claude Sonnet 4.6 | ~$0.005/call | $4-5 |
| OpenAI GPT-4o | ~$0.005/call | $4-5 |
| Perplexity Sonar | ~$0.008/call | $7-8 |
| Gemini 2.5 Flash | ~$0.001/call | $1 |
| **합계** | | **$16-19** |

CLAUDE_MAX 같은 기존 키 사용 시 추가 비용 0.

## 환경 변수

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
export PERPLEXITY_API_KEY=pplx-...
export GEMINI_API_KEY=AIza...   # 또는 GOOGLE_API_KEY
```

## 사용

```bash
# 한 번 실행 (모든 provider)
python scripts/geo_measure/measure_citations.py

# 특정 provider 만
python scripts/geo_measure/measure_citations.py --providers anthropic,gemini

# 카테고리 필터
python scripts/geo_measure/measure_citations.py --filter comparison

# dry-run (DB 저장 안 함)
python scripts/geo_measure/measure_citations.py --dry-run --filter def-01

# 리포트 — 어제 1일
python scripts/geo_measure/aggregate_report.py

# 리포트 — 최근 28일
python scripts/geo_measure/aggregate_report.py --window 28
```

## cron 등록 (Linux/Mac)

```cron
# 매일 09:00 KST (00:00 UTC) 측정
0 0 * * * cd /home/yesol/neo-genesis && /usr/bin/python3 scripts/geo_measure/measure_citations.py >> logs/geo_measure/$(date +\%Y-\%m-\%d).log 2>&1

# 매일 09:30 KST 일일 리포트
30 0 * * * cd /home/yesol/neo-genesis && /usr/bin/python3 scripts/geo_measure/aggregate_report.py --window 1 >> logs/geo_measure/report-daily.log 2>&1

# 매주 월요일 10:00 KST 주간 리포트
0 1 * * 1 cd /home/yesol/neo-genesis && /usr/bin/python3 scripts/geo_measure/aggregate_report.py --window 7 >> logs/geo_measure/report-weekly.log 2>&1

# 매월 1일 10:00 KST 월간 리포트
0 1 1 * * cd /home/yesol/neo-genesis && /usr/bin/python3 scripts/geo_measure/aggregate_report.py --window 28 >> logs/geo_measure/report-monthly.log 2>&1
```

## Windows Task Scheduler 등록

```powershell
# 일일 측정
$action = New-ScheduledTaskAction -Execute "python.exe" `
    -Argument "scripts\geo_measure\measure_citations.py" `
    -WorkingDirectory "D:\00.test\neo-genesis"
$trigger = New-ScheduledTaskTrigger -Daily -At 9:00am
Register-ScheduledTask -TaskName "NeoGenesis-GEO-Measure" `
    -Action $action -Trigger $trigger -RunLevel Highest
```

## KPI 트래킹

매주 월요일 weekly review 에 다음 메트릭 포함:

- **Citation rate** = mentions 발생 응답 / 총 호출
  - Phase 0 baseline 목표: 측정 시작
  - Phase 1 (M2-3) 목표: ≥ 5%
  - Phase 2 (M4-6) 목표: ≥ 15%
  - Phase 4 (M10-12) 목표: ≥ 30%
- **Provider 분포**: ChatGPT/Claude/Perplexity/Gemini 별 mention rate (플랫폼 분기 분석)
- **Category 분포**: 어떤 prompt 카테고리에서 mention 강한지 (definition vs comparison vs reputation)
- **Sentiment**: positive 비율, negative 발생 시 즉시 alert
- **SBU 분포**: 어떤 SBU 가 인용 받는지 (toolpick vs whylab vs 기타)
- **Founder mention**: 창업자 entity resolution 강도

## 다음 단계

- M3: 첫 90일 baseline → niche 진입 결정
- M6: Phase 2 진입 시 SE Ranking ($95) 또는 Otterly Lite ($29) 추가 (DIY 보완)
- M12: ROI 입증 후 Profound ($399+) 검토
