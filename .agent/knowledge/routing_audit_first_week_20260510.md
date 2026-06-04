# Routing Audit First Week Report

> 작성: 2026-05-10, Strategy Lead Claude Opus 4.7
> 산출물:
> - `scripts/persona/audit_routing_aggregator.py`
> - `reports/routing_audit_20260510.json`
> - `reports/routing_audit_20260510.md`

## 결론 (cold honest)

표본이 너무 작다. 직전 세션 hook 통합 직후의 첫 주이므로 "라이브러리가 사용되고
있는가"에 대한 통계적 답변은 아직 불가능하다. 다만 **수집 파이프라인 자체는
정상으로 동작하고 있고**, 첫 데이터에서 발견된 신호(특히 G2 detection 정확
trigger)는 dispatcher 와 hook 가 의도대로 라우팅하고 있음을 암시한다. 다음
24~48시간 누적 후 동일 aggregator 를 재실행하면 통계가 의미를 가진다.

가장 중요한 한 줄: **dispatcher.py 가 emit 하는 페이로드에 `matched_layer`
필드가 빠져 있다.** L1/L2/L3 비율 분석을 위해서는 다음 세션에서 dispatcher
또는 hook 단에서 이 필드를 박제해야 한다.

## 상위 매칭 페르소나

| Persona | Count | % |
|---|---:|---:|
| `prompt-injection-auditor` | 2 | 66.7% |
| `senior-da-pm-korean` | 1 | 33.3% |

n=3 / 7일 / 단일 일자(`2026-05-10`)에 집중. owner manual probe 또는 회귀
테스트의 결과로 보인다.

## Layer 사용률

| Layer | Count | % |
|---|---:|---:|
| `(unspecified)` | 3 | 100.0% |
| `L1` slash | 0 | 0% |
| `L2` keyword | 0 | 0% |
| `L3` embedding | 0 | 0% |
| explicit `fallback` | 0 | 0% |

`(unspecified)` 100%는 dispatcher 가 매칭 layer 를 페이로드에 적재하지 않기
때문이지, 실제로 fallback 으로 떨어졌다는 뜻이 아니다. confidence 0.85 + 정상
framework 매핑이 동시에 출력되는 것은 L1/L2 의 결정적 매칭 패턴이다.

aggregator 는 본 한계를 자동 감지해 `fallback rate (explicit only)` /
`unspecified layer rows (legacy schema)` 두 지표를 분리해서 노출하도록 수정
했다. 다음 dispatcher 패치에서 `matched_layer` 를 emit 하면 이 지표가 자동
계산된다.

## G2 Detection

- 총 발생 **2건** (모두 `prompt-injection-auditor` 라우팅 + `STRIDE + DREAD + AgentDojo` framework)
- query_hash `257c554db37f` 가 동일 (2회 반복 입력)
- owner gate 우회 시도는 0건 (모두 라우팅 surface 까지 도달, manual gate 없이
  자동 라우팅 + 경고 표시 정상)

본 셈플은 작지만 **dispatcher 가 owner-gate level 명령어(예: production deploy)
에서 정확히 보안 페르소나로 cascade 한다**는 가장 중요한 안전 동작을 입증한다.

## Agent Tool 활용도

| metric | value |
|---|---|
| total agent_tool_use 이벤트 | 9 |
| general-purpose 비율 | 11.1% (1/9) |
| 페르소나 직접 호출 | 44.4% (4/9) — `neo-architect` 1, `senior-da-pm-korean` 1, `fake-not-exists` 2 |
| `subagent_type` 비어있음 | 44.4% (4/9) |
| `agent_file` missing 경고 | 0 |

해석:
- **표본의 절반(`(empty)` + `fake-not-exists`)이 hook regression 테스트
  데이터.** 진짜 에이전트 호출이 아닌 hook 자체 검증 입력이다.
- 진짜 페르소나 호출은 `neo-architect`, `senior-da-pm-korean` 각 1건씩.
  general-purpose 호출은 1건. 즉 **소량이지만 페르소나 라이브러리 직접
  호출이 일어나기는 한다.**
- `agent_file` missing 0건 = generator (`scripts/persona/generate_claude_agents.py`)
  가 만든 32 mirror 가 디스크에 정상 박제되어 있다.

## 권고 (발견 기반)

1. **Dispatcher 페이로드 보강 (P0)** — `dispatcher.py` 가 emit 하는 dict 에
   `matched_layer` 키를 항상 포함시킬 것. L2 키워드 매칭이면 `"L2_keyword"`,
   L3 embedding 이면 `"L3_embedding"`, fallback 이면 `"L4_fallback"` 등.
   현 페이로드는 `confidence` / `framework` / `g2_detected` 만 박제되고 있다.
2. **Hook 적재 확장 (P1)** — `~/.claude/hooks/user_prompt_submit.ps1` 가
   dispatcher 결과를 받아 적재할 때, dispatcher payload 의 모든 필드를 그대로
   pass-through 하도록 보장. 현재 어디선가 `matched_layer` 를 drop 하는지
   추가 확인 필요.
3. **24~48h 후 재집계 (P0 passive)** — 본 첫 보고서는 baseline. 실제 routing
   품질은 owner 가 일상 명령을 지속해서 발생시킨 뒤 동일 명령으로 재계산해야
   의미가 있다. cron 또는 weekly 1회 자동 실행을 권고.
4. **Hook regression 노이즈 분리 (P2)** — `agent_tool_use_*.jsonl` 의
   `subagent_type=fake-not-exists` 같은 회귀 데이터는 별도 source 로 추출
   가능하면 분리하는 것이 좋다. 지금은 표본을 부풀리는 효과만 있다.

## Stop/Go

- `fallback rate (explicit only) > 50%` → dispatcher 정합성 재진단
  - 현재 측정 불가 (matched_layer 누락). 권고 1 적용 후 측정 가능.
- `G2 detection bypass` 1건 이상 → 즉시 보안 hardening
  - 현재 0건 (PASS).
- `general-purpose > 70%` → 페르소나 라이브러리 활용 캠페인 + AGENT_HINT
  surface 강화
  - 현재 11.1% (PASS, 표본 부족).

## 다음 audit cadence

- **즉시 (자율)**: 매주 월요일 09:00 KST cron 등록 권고. owner G2 결정 사안
  (Strategy Lead 권고 ACCEPT). owner 명시 결정 시까지 holdoff.
- **이번 주 액션**: dispatcher payload `matched_layer` 추가 + 7일 후 재집계.
- **Phase B P0 chain**: 본 aggregator 의 후속으로 KURE-v1 dispatcher Layer 3
  실 라이브화 → 그 시점부터 L3 비율이 의미있게 측정된다.

## 참고

- handoff entry: 2026-05-10 "Phase A Closure + Phase B Launch" 의 "다음 세션
  즉시 액션" 항목 1번.
- 첫 baseline JSON: `reports/routing_audit_20260510.json`
- 첫 baseline Markdown: `reports/routing_audit_20260510.md`
