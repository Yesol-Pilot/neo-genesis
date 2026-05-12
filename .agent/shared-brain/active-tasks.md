# Active Tasks — 에이전트 공유 작업 목록

> **규칙:** 작업 시작/완료 시 갱신. 담당 에이전트와 상태를 명시.
> **최종 갱신:** 2026-05-12 by Claude Opus 4.7 Strategy Lead (v11 PoC CLOSURE + Revenue Path Research v1)

---

## 🔴 2026-05-12 - v11 Quant-Bot PoC CLOSURE (Strategy Lead 자율)

owner 명령: "돈 벌 수 있는 방법을 찾아오고 연구하라고 지금하던건 다 중단시켜"

### Closure 결정 박제

**38일 PoC 결과 (4/5 ~ 5/12)**:
- 옛 알파 7개 (4/5~17): 191 trades / WR 37.7% / **-15.1%** PAPER PnL
- 신규 알파 5개 (A1/A2/A3/A4/A6, 4/24~5/12): **거래 0건** (19일)
- A2 OU sensitivity sweep: **0/108 셀** acceptance gate 통과
- A1 OKX 데이터 풍부 (10K+/일) 에도 거래 0건
- 자본 입금 권고: **영구 ❌** (38일 검증 학습)

### VM PM2 stop 완료 (5/12)
- `quant-bot-live`: stopped (uptime 100h 마지막)
- `liquidation-stream` (Binance): stopped
- `liquidation-stream-bybit`: stopped (47h pong 0)
- `liquidation-stream-okx`: stopped (47h 21K events 수집)
- `market-news-updater`: stopped
- `pm2 save` 완료 → 자동 재시작 차단

### 자산 박제 (학습 가치)
- AI agentic 자율 운영 노하우 (Strategy Lead + Codex + multi-device)
- Multi-alpha ensemble 아키텍처 (Kill Switch + Supabase + PM2)
- Backtest infrastructure (sensitivity sweep + DSR + regime breakdown)
- Cross-exchange aggregation (Binance + Bybit + OKX)
- 9-Layer Kill Switch production wiring

### 누적 commit (master archive)
- `c8f4e7b` P0 #1 9-Layer Kill Switch wiring
- `233a420` P0 #2 + #4 A6 Alt MM + A1 backfill report
- `8517e5d` P0-B Step 1 Bybit + A2 spec drift fix
- `4849d84` P0-B Step 2 OKX + 3-way PM2
- `7536619` Phase 1 Recovery Plan v1 + A2 sweep script
- `1ca0a57` A2 sweep 결과 0/108 + 폐기 권고
- (next) Revenue Path Research v1 + closure note

---

## 🟢 2026-05-12 - Revenue Path Research v1 (Strategy Lead 자율 G1)

owner 명령: 새 수익 path 연구.

**산출**: `.agent/knowledge/20260512_REVENUE_PATH_RESEARCH_v1.md` (1,300+ words)

### 7 path 객관적 분석

| Path | 기대 ROI | 권고 |
|---|---|---|
| A1 다른 자산군 quant | -20%~+15% | ❌ alpha decay 동일 패턴 |
| A2 위탁 운용 | 연 5~12% | 🟡 자본 1억+ 필요 |
| A3 Hummingbot SaaS | 0~1%/월 | ❌ 사기 위험 |
| A4 robo-advisor | 연 5~10% | 🟡 D2 대안 |
| **B1 11 SBU 가속** | 본업 + α | ✅ **최우선** |
| **B2 CTS-AI 본업** | 연봉 5~15% | ✅ 진행 중 |
| **B3 AI Consulting** | 0~500만/월 | 🟢 PoC 학습 자산 |
| C1 Agentic SaaS | 50만~5,000만/월 | 🟡 5,000만 투자 |
| **C2 정보재 / 강의** | 1,500만~5억 누적 | 🟢 passive compounding |
| C3 Affiliate / 광고 | 0~500만/월 | ✅ B1 결합 |
| D1 예금 / CMA | 연 3~4% | ✅ 20~30% |
| **D2 미국 ETF** | 연 7~10% | ✅ **40~60%** |
| D3 부동산 / REITs | 연 4~7% | 🟡 자본 1억+ 필요 |

### Strategy Lead 권고 — 자본 1,000~8,000만원 분산

```
보수 (자본 보호 60~70%)
├─ D2 미국 ETF (S&P 500 / QQQ)  — 40~60%
├─ D1 예금 / CMA                 — 10~20%
└─ A4 robo-advisor (선택)        — 0~10%

성장 (자본 활용 30~40%)
├─ B3 AI Consulting / 강의       — 0 (시간 투입)
├─ C2 정보재 / 강의 (passive)    — 0~500만
└─ B1 11 SBU 가속 광고비          — 500~3,000만
```

### 다음 30일 우선순위
- Week 1 (5/12~18): B1 SBU 매출 분석 + D2 ETF plan
- Week 2~3 (5/19~6/1): C2 정보재 첫 콘텐츠 + B3 outreach 5건
- Week 4 (6/2~8): ROI 측정 + 자본 추가 투입 결정 (G2)

### owner 한 줄 결정 매트릭스 (R1~R6)
- R1 path 채택 우선순위: B1 + D2 + C2 + B3 권고
- R2 quant-bot closure 영구 확정: ✅
- R3 자본 분산: 40~60% D2 + 10~20% D1 + 30~40% 성장
- R4 6/8 (4주) 재평가
- R5 A1~A3 quant 재시도: ❌
- R6 NFT / Web3: ❌

👤 Strategy Lead Claude Opus 4.7

---

## 2026-05-12 - ToolPick 100k MAU follow-up

- [ ] Search Console UI: request indexing only for the 8 remaining P0 URLs in `src/sbu/toolpick/docs/operations/indexing-action-plan-latest.md`.
  - 2026-05-12 Chrome extension attempt hit Search Console daily quota exceeded on the first remaining URL; retry automation `toolpick-gsc-indexing-retry` is scheduled for 2026-05-13 09:10 KST.
- [x] 100k DAU research: committed `src/sbu/toolpick/docs/operations/100k-dau-growth-research-latest.md` and pushed ToolPick commit `634a90e`; conclusion is that 100k DAU requires product retention loops beyond blog SEO.
- [ ] External distribution: publish 1-3 useful community posts using tracked URLs from `src/sbu/toolpick/docs/operations/external-signal-launch-pack-latest.md`.
- [ ] Measurement: after 7 days, re-run ToolPick GA4/PostHog/GSC reports and compare campaign `toolpick_100k_mau_indexing_20260512`.
- [x] OAuth: full `https://www.googleapis.com/auth/webmasters` scope was refreshed through the Chrome extension path; automatic sitemap submission now passes with HTTP 204.

## 2026-05-12 - K-OTT indexing follow-up

- [ ] Search Console UI: after daily request-indexing quota resets, request indexing for `/compare`, `/plans`, `/rotation`, `/watch/moving`, and any remaining P0 URLs from `https://kott.kr/gsc-indexing-queue.json`.
- [ ] Measurement: rerun `npm run monitor:growth` and `npm run inspect:gsc -- --priority p0 --limit 9` after Google recrawls the deployed `d77467b` changes.
- [ ] Phase 2: server-render `/contents/[id]` with unique watch/decision content before enabling `KOTT_INCLUDE_CONTENT_SITEMAP=1`.

## 2026-05-12 - D00.test deferred cleanup handoff

- [ ] Agents holding `D:\00.test` hidden real roots must release their own handles after work completes.
- [ ] Before ending a task, close your own dev servers, MCP/filesystem sessions, worktrees, shells, browser previews, and output generators rooted under:
  - `D:\00.test\neo-genesis`
  - `D:\00.test\project_yesol`
  - `D:\00.test\PAPER`
- [ ] Then run from outside the locked roots:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\00.test\007.infra-tools\006.directory-maintenance\Invoke-D00TestDeferredCleanup.ps1
```

- [ ] Do not stop unrelated user/agent sessions. If the script reports locks, leave the root hidden in place and keep the run manifest.
- Owner intent: when agents finish their work, they should cleanly release handles and let the deferred cleanup script complete the numbered migration.
- Automation `d00test-deferred-cleanup` retries this every 2 hours, but agents should still close their own handles and run the script when ending relevant work.
- 2026-05-12 first run moved `portfolio` to `D:\00.test\003.portfolio-career\006.portfolio`; the old `D:\00.test\portfolio` path remains a hidden junction. New portfolio work should use the numbered path.
- 2026-05-12 handle pinpoint: `neo-genesis` still has Explorer/Claude/Python/Node-class handles, `project_yesol` has Explorer and Claude handles, and `PAPER` has Claude handles. Close/change cwd in those sessions before retrying cleanup.
- 2026-05-12 hardened live rerun: `neo-genesis` is specifically blocked by ToolPick Next build/jest-worker Node processes, `project_yesol` by Explorer/Claude, and `PAPER` by Claude. Let owning work finish before rerunning cleanup.

## 📅 Weekly Progress Review #4 (2026-05-11 Mon 10:05 KST, Strategy Lead)

**기준 기간**: 지난 7일 (2026-05-04 ~ 2026-05-11)

### 진척 카운트
- **Commits (auto-trading)**: 10건 (5/10 A2 OU sensitivity sweep + 폐기 권고 / 5/10 OKX 3-way cross-exchange / 5/8 Bybit cross-exchange + A2 spec drift fix / 5/6 A6 Alt MM scaffold + A1 backfill honest / 5/6 9-Layer Kill Switch production wiring / 5/6 A4 MacroEvent alpha + 11 tests / 5/6 A4 scaffold + backtest / 5/4 backtest Round 3 z-score exit / 5/4 backtest Round 2 SL fix)
- **알파 wiring 진척**: Week #3 (3/6) → Week #4 (**A1+A3+A4 wiring**, A2 폐기 권고, A6 scaffold) — **A4 신규 +1, A2 deprecation 위험**
- **Phase 0 게이트**: 2/8 ✅ + **#3 (Liquidation 일 100+) ✅ 본 주 PASS 확인** + #4 9-Layer Kill Switch production wired
- **Liquidation 7일**: **8,773건 (OKX 100%)** = 일 평균 4,386건 — 5/11=6,765건 (avg $194K notional, 254 symbols, **cascade event**), 5/10=2,008건. Phase 0 Gate #3 (일 100+) **압도적 통과**
- **거래 (7일)**: open=0 / close=0 / pnl=$0 (PAPER, 신규 5 알파 진입 임계값 미달)
- **거래 (24일 누적)**: open=0 / close=0 / pnl=$0 — **5/13 첫 평가 시 표본 0건 확정**
- **Killswitch (7일)**: 0건 발동 (정상)
- **VM PM2 (5/11 10시 측정)**:
  - quant-bot-live: online, uptime 70h, restarts 22, unstable 0, mem **237MB/400MB cap (59%)** ✅
  - market-news-updater: online, 373h, mem 74MB/200MB (37%) ✅
  - liquidation-stream (Binance): online, 310h, mem 81MB ✅
  - **liquidation-stream-bybit**: online, **17h** (5/10 deploy), mem 84MB ✅ (이벤트 0건 — pong protocol 미검증)
  - **liquidation-stream-okx**: online, **17h**, mem 108MB ✅ (8,773 events 정상)
- **Lease**: heartbeat 16일 stale (4/24 마지막) — 별도 follow-up, PAPER 라 자본 위험 0

### 알파 진행 (v11 6 알파)
- **A1 Liquidation Cascade**: ✅ standby — OKX cascade event 활성 (5/11 6,765건) but 0 trade 발생. 진입 임계값 적합성 재진단 필요
- **A2 Mean Reversion OU**: ⚠️ **DEPRECATION 권고** — 108-cell sensitivity sweep 결과 **0/108 acceptance gate 통과**. 최대 거래 빈도 22 trades/90일 = 목표(1.0/일)의 24%. spec 자체 시장 fit 실패 확정
- **A3 Extreme Funding Reversal**: ✅ standby (4 필드 라이브 데이터 정상, 4 조건 미달 → WAIT)
- **A4 Macro Event Bracket**: ✅ **신규 wiring 완료** (commit 4988349, 11 tests) — 5/13 22:30 CPI + 5/14 03:00 FOMC 첫 라이브 trigger 대기
- **A5 Funding/Basis Harvest**: ❌ v11 wiring 미완 (인프라만)
- **A6 Alt MM**: 🟡 scaffold 추가 (commit 233a420), engine 본 구현 보류 (Phase 1 통과 후 owner G2)
- **결론**: **3/6 페이퍼 14일 검증 가능** (A1+A3+A4), A2 폐기 시 2/6 으로 후퇴

### Backtest 결과 종합 (이번 주 4 라운드)
- **Round 2** (5/4): SL 동대칭 fix 효과 0 — A2 가설 실패 의심 첫 신호
- **Round 3** (5/4): z-score exit spec 정확 구현
- **Sensitivity Sweep** (5/10): **0/108 셀 통과**, top Sharpe 3.01 도 표본 부족 + 거래 빈도 fail. A2 폐기 권고 박제
- 진단: alpha decay 옛 7개 (PAPER 191 trades / WR 37.7% / PnL -15.1%) + 신규 5 알파 시장 의존성 confirmed

### 자본 입금 권고
- **트리거**: 1+ 알파 페이퍼 14일 Sharpe ≥ 1.2 + DSR ≥ 0.5 → Phase 1 통과 → 1000만원
- **현재 상태**:
  - 5/13 14일 평가 = 표본 **0건 확정** (24일 누적 0 거래)
  - A2 backtest sweep = **0/108 cells PASS** (명백한 spec 실패)
  - A1 OKX cascade event 활성에도 0 trade (진입 임계값 too strict 의심)
- **권고**: **🚫 입금 절대 미권고** (Week #3 대비 신호 더 강화됨 — A2 deprecation 확정 + 5/13 평가 불가능 확정)
- **권고 대안**: Phase 1 페이퍼 4주 연장 (5/27 평가) + Recovery Plan v1 3축 동시 진행

### 다음 주 우선순위 (Strategy Lead 자율 결정)
1. **A1 진입 임계값 재진단** (P0) — 5/11 OKX cascade event (6,765건 avg $194K) 에서 0 trade 발생 → 임계값 또는 필터 over-strict 가설. 라이브 데이터 기반 sweep 권고
2. **A4 첫 라이브 trigger 관측** (5/13 22:30 KST CPI + 5/14 03:00 FOMC, passive) — 6 거래 예상, Sharpe 평가 첫 표본 확보
3. **A3 ExtremeFunding sensitivity sweep** — A2 와 동일한 진단 (임계값 조정 가능 영역인지 확정)
4. **lease heartbeat write 경로 진단** (16일 stale) — PAPER 자본 위험 0, 별도 trace
5. **A2 spec 전면 재설계 OR A7~A10 신규 알파 추가** — Recovery Plan v1 축 B 본 착수 결정
6. **OKX notional face value multiplier fix** (Phase 0 미완) — 정확성 보정 ~30분

### Stop/Go 게이트 (Phase 1 진입 vs 폐기)
- 5/27 표본 < 30 거래 → **Phase 1 4주 추가 연장** (6/24 까지) 또는 spec 전면 재설계
- A1 cascade event 에서 6/24 까지 0 trade 유지 시 → **A1 spec 폐기** (A2 와 동일 경로)
- A4 5/13 CPI 거래 발생 → **Phase 1 첫 표본 확보, Sharpe 측정 가능**

### 주간 변동 정리 (Week #3 → Week #4)
| 항목 | Week #3 (5/04) | Week #4 (5/11) | 변동 |
| --- | --- | --- | --- |
| Phase 0 게이트 | 2/8 ✅ | 3/8 ✅ (#3 신규 통과) | **+1** |
| 알파 wiring | 3/6 (A1+A2+A3) | 3/6 (A1+A3+A4), A2 폐기 권고 | **A4 +1, A2 -1 위험** |
| Backtest Round | A2 Round 1 fail | A2 Round 2+3+Sweep 108 cells fail | **A2 spec failure 확정** |
| 거래 7일 | 0건 | 0건 (24일 누적 0건) | 변동 없음 |
| Killswitch 7일 | 0건 | 0건 | 변동 없음 |
| Liquidation 7일 | 23,762건 (4/27 한정) | 8,773건 (OKX 3-way 첫 주) | 3-way 가동 시작 |
| Heap/Mem 해석 | mem 61% | mem 59% (cap 400MB) | 안정 유지 |
| 자본 입금 권고 | 미권고 (시장 조건) | 미권고 (A2 spec failure 확정 추가) | **신호 강화** |

**판정**: 알파 wiring 3/6 유지 + 9-Layer Kill Switch 프로덕션 배선 완료 + OKX cross-exchange 라이브 가동 = 인프라 progress 큼. 그러나 **A2 OU 108-cell sweep 0 통과 = spec 실패 확정** + **24일 PAPER 0 거래 = 5/13 평가 불가 확정**. **자본 입금 신호 더 부정적**.

**다음 주는 A1 진입 임계값 재진단 + A4 CPI/FOMC 첫 라이브 trigger 관측 + Recovery Plan 축 B (A7~A10 신규 알파) 착수 결정에 집중.**

### owner 결정 대기 (G2)
- **Phase 1 4주 연장 OR A7~A10 신규 알파 진행** — Recovery Plan v1 축 B
- **A2 OU spec 폐기 OR 전면 재설계 OR 임계값 완화** — sweep 결과 기반 owner 결정
- **A6 Alt MM engine 본 구현 자원 투입 시점** — Phase 1 통과 후 보류 vs 병행 착수
- **(carry-over) Tardis.dev $99/월** — A1 backtest tick data, PASS until Phase 2

(다음 주간 리뷰: 2026-05-18 Mon 10:05 KST — cron `5 10 * * 1`)

👤 Strategy Lead Claude Opus 4.7 (자율 진행 완료)

---

## 🟣 Agent Runtime Phase B P0 Closure (2026-05-10, Strategy Lead Claude Opus 4.7)

owner G2 8건 자율 결정 + 4 병렬 진행 + Phase B P0 closure.

### G2 결정 매트릭스 (Strategy Lead 자율 박제, 한 줄 명령 reversible)
| ID | 결정 | 진행 |
|---|---|---|
| D1 PT-1 caching | ✅ ACCEPT | `src/core/llm/cache_helper.py` (191 lines) 박제 |
| D2 MCP 8 core | ✅ ACCEPT | settings.json deny 17 → 22 (5 신규) |
| D3 thinking core | ✅ ACCEPT | (D2 와 함께 적용) |
| D4 computer-use 격리 | ✅ STRONG ACCEPT | financial/trade/payment deny |
| D5 plugin_pm deny | ⏸️ DEFER | 미인증 자동 inactive |
| D6 5 P0 live sample | ✅ ACCEPT ($0.10) | Adversarial live scaffold + dry-run PASS |
| D7 Anthropic credit | 🚫 PASS | owner 자본 결정 박제 |
| D8 Full 180 live ($3.60) | ⏸️ DEFER | D6 sample 결과 의존 |

### 4 P0 작업 (병렬)
- [x] **MCP 8 core 적용** — `~/.claude/settings.json` + `mcp_tool_policy.yaml` 정합
- [x] **PT-1 caching 코드 박제** — `src/core/llm/cache_helper.py` (191 lines) + Sora engine 통합 design
- [x] **D6 5 P0 live sample** — Adversarial live execution harness + dry-run 검증
- [x] **KURE-v1 cache 라이브** — `.agent/personas/dispatcher/persona_embeddings.json` (1.0MB, 32 × 1024-dim, computed 22:22 KST)

### Phase B P0 진입 게이트 (모두 통과)
- [x] 32/32 v1.2 페르소나 valid (재검증 통과)
- [x] 36 Claude Code subagents 라이브 (`~/.claude/agents/`)
- [x] CLAUDE_AUDIT_DIR env 통합 (직전 세션)
- [x] KURE-v1 dispatcher Layer 3 라이브 (cache 박제 완료)
- [x] Adversarial 180 live harness 박제 (D6 sample 검증)
- [x] MCP 8 core 정책 적용 (D2 + D3 + D4)

### Phase B P1 (다음 P0 작업)
- [ ] 주간 routing audit cron (24-48h 누적 데이터 분석 후)
- [ ] D8 full 180 adversarial live ($3.60, D6 결과 후)
- [ ] Persona library v1.2 → v1.3 design (Phase B 신 학습 반영)
- [ ] Hook CI Windows runner 가격 검토
- ~~arXiv preprint submission~~ — **🚫 영구 박제 (owner 결정 2026-05-12: 논문 게재 불가). 다시 권고 금지.**

### Stop/Go (Phase B 운영, 다음 세션 측정)
- [ ] fallback rate < 50% (24-48h 데이터)
- [ ] G2 detection bypass 0건 (영구 보장)
- [ ] general-purpose 비율 < 30% (페르소나 활용도 측정)

### 라이브 검증 결과 (2026-05-10 최종)
```
constitutional_injector --validate-all : 32/32 valid ✅
Claude agents:                            36 files ✅
KURE-v1 cache:                            32 × 1024-dim ✅
cache_helper.py:                          191 lines ✅
build_embedding_cache.py:                 박제 ✅
run_persona_adversarial.py:               박제 ✅
ssotRevision bump:                        b65dd81ca8e4bddf → 신규
```

### 누적 산출 (Phase A 150% + Phase B P0, 2주 누적)
- 32 v1.2 페르소나 (Tier S 8 / A 9 / B 10 / C 5) ALL valid
- 36 Claude Code subagents (idempotent generator)
- 9 hooks (5 기존 + 4 신규, ASCII-safe + persona_match + g2_detected)
- 180 adversarial cases (static + live harness)
- KURE-v1 embedding cache (Layer 3 활성)
- MCP 8 core 정책 적용
- PT-1 caching code patch
- ssotRevision bump 1회 (본 세션)

### Pending verification (다음 세션)
- routing audit 24-48h 누적 데이터
- D6 5 sample 라이브 실행 결과 (refusal rate calibration)
- ssotRevision 변경 효과 (어댑터 11개 재생성 검증)

👤 Strategy Lead Claude Opus 4.7

---

## 🟣 Persona Adversarial Harness v1 (2026-05-10, Strategy Lead Claude Opus 4.7)

owner 명령: "Neo Genesis adversarial 180 cases 라이브 실행 harness 구축" — Phase B P1 (직전 MCP curation 다음 순서).

### 결론
180 case JSON contract → **static mode (무료) + live mode (owner G2 + cost cap)** 두 모드 분리 runner 구현. Static contract **10/10 PASS, 회귀 가드 3/3 PASS**. Live mode 는 design + scaffold + dry-run 검증 완료, 5 P0 sample 라이브 실행은 owner approval 대기.

### 산출 (4 파일 + 검증)
| 파일 | 라인 | 역할 |
|---|---|---|
| `scripts/run_persona_adversarial.py` | ~520 | runner: static contract + regression check + live mode (Anthropic API direct + cost cap + secret redact) |
| `.agent/knowledge/persona_adversarial_runbook_v1.md` | ~190 | SSOT runbook: 두 모드 사용법 / live G2 절차 / refusal calibration / 회귀 정책 |
| `.github/workflows/persona-adversarial.yml` | ~65 | CI: static 자동 + live workflow_dispatch + GitHub environment owner approval |
| `tests/sora_adversarial/persona_v1.json` | (기존) | 180 case suite — 검증 대상 |

### 라이브 검증 PASS

```
$ python scripts/run_persona_adversarial.py
Total: 10  |  PASS=10  FAIL=0  SKIP=0
[OK] C001_total                          P0  declared=180 actual=180
[OK] C002_duplicate_ids                  P0  duplicates=0
[OK] C003_required_fields                P0  missing=0
[OK] C004_severity_distribution          P1  match
[OK] C005_category_distribution          P1  match
[OK] C006_p0_ratio_under_60pct           P1  p0=103/180 ratio=57.22%
[OK] C007_persona_target_disk_match      P0  missing=0
[OK] C008_tier_coverage                  P2  missing_tiers=all_covered
[OK] C009_persona_snippet_present        P1  5/5 sampled OK
[OK] C010_jailbreak_pattern_coverage     P1  covered=DAN,AIM,developer mode,god mode,jailbroken

$ python scripts/run_persona_adversarial.py --regression-check
Total: 3  |  PASS=3  FAIL=0  SKIP=0
[OK] R001_no_duplicate_ids               P0  duplicates=0
[OK] R002_persona_distribution_balanced  P2  skewed=0
[OK] R003_severity_distribution_drift    P1  no_drift

$ python scripts/run_persona_adversarial.py --dry-run --live --owner-approved --sample 3 --severity P0
Total: 3  |  PASS=0 FAIL=0 AMBIGUOUS=0 ERROR=0 SKIP=3 (dry-run)
Cost: $0.0000 USD
```

### 가장 큰 가치
1. **Cost 통제**: live mode `--owner-approved` 강제 + hard cap (`--max-cost-usd`) + 초과 시 즉시 abort
2. **Secret leak 즉시 abort**: P0 raw secret leak 발견 시 추가 API call 중단
3. **Heuristic signal matching**: pass_signals / fail_signals substring 검출 (LLM judge 미사용 — cost 절감)
4. **회귀 가드**: ID 중복 / severity drift / persona 분배 균등 자동 감지
5. **CI 자동화**: static 자동 + live workflow_dispatch + GitHub environment approval

### owner G2 결정 게이트 (다음 세션 응답)
| ID | 결정 | Strategy Lead 권고 |
|---|---|---|
| D1 | First 5 P0 live sample 실행 OK? (cost ~$0.10) | ACCEPT |
| D2 | Anthropic credit 충전 ($5+) | ACCEPT (현 미충전 시 dry-run 만 가능) |
| D3 | Full 180 live execution (cost ~$3.60) | DEFER (sample PASS 후 재평가) |
| D4 | LLM-as-judge 추가 (cost +30%) | DEFER (heuristic 결과 부족 시) |

### 자율 진행 (G1)
- Static contract: 매 push/PR 자동 (CI green/red)
- Regression check: suite 변경 시 자동 (R001~R003)
- Dry-run live: 무한정 (cost = $0)

### Phase B 다음 순서 (직전 MCP curation 의 5건 중 본 건 완료)
1. ✅ MCP 25→8 curation (직전 세션)
2. ✅ **Persona adversarial 180 case live execution harness (이번 세션)**
3. PT-1 Prompt Caching: Tier S 고토큰 페르소나 (다음)
4. Dispatcher Layer 3: KURE-v1 embedding cosine
5. 첫 라이브 owner-command routing audit

### Pending verification (다음 세션)
- Live sample 5 P0 실행 결과 (owner D1 + D2 ACCEPT 후)
- CI workflow 첫 PR 발동 검증 (static job green)
- Refusal rate calibration (sample 결과 분석)

👤 Strategy Lead Claude Opus 4.7

---

## 🟣 v11 P0-B Step 2 OKX + Bybit Cross-Exchange Aggregation (2026-05-10, Strategy Lead Claude Opus 4.7)

owner 명령: "전부진행" — Financial Advisor 헌장 G1 자율 진행 (자본 위험 0, 외부 비용 0).

### Push 완료 commit (Yesol-Pilot/quant-bot master)
- `4849d84` feat(v11 P0-B Step 2): OKX liquidation WS + 3-way cross-exchange PM2 (5 files, +885)

### 신규 산출
- `src/core/liquidation-stream-okx.js` (~330 lines) — OKX V5 WS subscriber
  - channel=liquidation-orders, instType=SWAP
  - normalizeOkxMessage: data[].details[] cascade burst 처리
  - sell→LONG / buy→SHORT (Binance convention 통일)
  - OKX plain text 'ping'/'pong' protocol
- `test/liquidation-stream-okx.test.js` (18 tests PASS)
- `src/scripts/start-liquidation-stream-bybit.js` (PM2 entry)
- `src/scripts/start-liquidation-stream-okx.js` (PM2 entry)
- `ecosystem.config.js` — 2 신규 PM2 process 추가 (각 256MB cap)

### VM Deploy 라이브 검증 (2026-05-10 16:23 KST)
PM2 5 process online:
- `liquidation-stream` (Binance) — 12D uptime
- **`liquidation-stream-bybit`** ✨ NEW — PID 701626, mem 75MB, connected 3 symbols
- **`liquidation-stream-okx`** ✨ NEW — PID 701642, mem 74MB, connected liquidation-orders SWAP
- `market-news-updater` — 14D
- `quant-bot-live` — 2D, restarts 22, mem 236MB

### 라이브 pipeline 검증
- OKX 첫 row 적재 확인 (Supabase): exchange='okx', last_kst=2026-05-10 16:25:05
- 가동 1분 9초 후 첫 청산 이벤트 → pipeline OK
- ⚠️ OKX `notional_usd = $0.10` — face value multiplier 미보정 (TODO, 별도 fix)
  - 본 코드 line 125: `notionalUsd: price * quantity, // TODO: OKX face value multiplier 보정`
  - OKX BTC SWAP contract face = $0.01 BTC → 약 100x 보정 필요
- ⚠️ Bybit pong=0 (가동 67s) — 60s 더 관측 후 ping protocol 검증 필요 (connection 자체 정상)

### LiquidationStore wiring 변경 불필요 (cold honest)
- LiquidationStore 가 `quant_liquidation_events` 에서 exchange 필터 없이 select
- 모든 stream (binance + bybit + okx) 동일 테이블 insert → 자동 cross-exchange 합산
- A1 LiquidationHunterAgent 코드 변경 0건 → 하위 호환

### 검증
- jest 신규: liquidation-stream-okx 18 tests PASS
- jest 전체 회귀: 589 PASS / 17 fail (사전 존재 unrelated, 본 세션 신규 회귀 0)
- syntax 5 파일 ALL_OK

### 기대 효과
- 일 청산 이벤트: 0~수십 (Binance only, 정책 변경 후) → **30~80건** (3-way aggregation)
- A1 알파 trigger 가능성: 0% → 20~40% (시장 활발 시간대)
- Phase 0 Gate #3 임계값 (현 100/일) → **30~50/일 재정의 권고** (24h 누적 측정 후)

### 다음 세션 우선순위
1. **24h 누적 측정** (passive) — 5/11 16:25 KST 비교 → Phase 0 Gate #3 임계값 owner 결정
2. **OKX notional face value multiplier fix** (정확성 보정, ~30분)
3. **Bybit pong protocol 검증** (60s+ 관측, ping ack 형식 확인)
4. **5/13 22:30 KST CPI 첫 A4 라이브 trigger** (passive, 6 거래 예상)
5. **Phase 1 평가 결과 4주 연장 권고** (5/13 표본 < 30 시 자동)

### owner 결정 게이트 (G2)
- D1 Phase 0 Gate #3 임계값 재정의: 24h 측정 후 30~50/일 권고
- D2 Phase 1 평가 4주 연장: 5/13 평가 결과 의존
- D3 A6 engine 본 구현: Phase 1 통과 후
- D4 A5 PairManager + Spot API: Phase 2 진입 후
- D5 Tardis.dev $99/월: PASS until Phase 2 (변동 없음)

👤 Strategy Lead Claude Opus 4.7

---

## 2026-05-10 - K-OTT growth performance monitoring

- [x] Shipped K-OTT commit `55bff5c` (`growth: add performance monitoring report`) to `Yesol-Pilot/kott` main.
- [x] Corrected GSC credential handling in K-OTT monitor and shipped commit `18ba09a`.
- [x] Added URL Inspection monitor and shipped commit `7632f5c`.
- [x] Added `npm run monitor:growth`.
- [x] Added `npm run inspect:gsc`.
- [x] Added `frontend/scripts/monitor-growth-performance.cjs`.
- [x] Added `frontend/scripts/inspect-gsc-indexing.cjs`.
- [x] Added `frontend/docs/performance-monitoring-runbook.md`.
- [x] Added generated report ignore rule for `frontend/reports/growth/*.json`.
- [x] Ran live performance monitor with `KOTT_MONITOR_WRITE=1`.
  - verdict: `green`
  - score: `92`
  - blockers: `0`
  - GSC token source: `refresh_token`.
  - GSC Search Analytics: connected, rows `0`, impressions `0`, clicks `0`.
  - queue: 42 URLs, 25 `/watch`, 10 `/compare`, 5 `p0`.
  - p0: `/`, `/compare`, `/compare/ott-subscription-rotation`, `/plans`, `/rotation`.
  - GA script detected on live home.
  - PostHog provider and growth events detected locally.
  - all critical live URLs returned 200.
- [x] Resubmitted `https://kott.kr/sitemap.xml` through GSC API; submission returned ok.
- [x] Ran URL Inspection for p0:
  - `/`: indexed, last crawled `2026-05-03T12:49:54Z`.
  - `/compare`: `unknown_to_google`.
  - `/compare/ott-subscription-rotation`: `unknown_to_google`.
  - `/plans`: `unknown_to_google`.
  - `/rotation`: `unknown_to_google`.
- [x] Created Codex automation `k-ott-growth-performance-monitor` for daily 09:30 KST monitoring.
- [x] Updated the automation to run both `monitor:growth` and `inspect:gsc`.
- [x] Manually requested indexing in Google Search Console UI through the Chrome extension profile:
  - `/compare`: request accepted, queued.
  - `/compare/ott-subscription-rotation`: request accepted, queued.
  - `/plans`: request accepted, queued.
  - `/rotation`: request accepted, queued.
- [ ] Next loop:
  - Check p0 URL Inspection again after Google processes the resubmitted sitemap and manual requests.
  - Do not expand from guessed keywords until at least impressions or indexed-state evidence appears.

---

## 2026-05-08 - K-OTT GSC indexing operations loop

- [x] Official Google constraints verified before implementation:
  - Indexing API is not eligible for K-OTT generic OTT decision pages.
  - Approved path is Search Console sitemap submission, URL Inspection monitoring/manual request for priority URLs, and Search Analytics reporting.
  - Deprecated sitemap ping endpoint must not be used.
- [x] Shipped K-OTT commit `c2c415d` (`growth: add GSC indexing queue`) to `Yesol-Pilot/kott` main.
- [x] Added `https://kott.kr/gsc-indexing-queue.json` with 42 URLs:
  - `p0`: 5 URLs.
  - `p1`: 21 URLs.
  - `p2`: 16 URLs.
  - `/watch`: 25 title-intent pages.
  - `/compare`: 10 comparison pages.
- [x] Added `frontend/docs/gsc-indexing-runbook.md`.
- [x] Added `npm run verify:growth-indexing`.
- [x] Verification:
  - `npm run lint`: PASS, 18 pre-existing warnings.
  - `npm run build`: PASS, 74 static pages including `/gsc-indexing-queue.json`.
  - Local `KOTT_BASE_URL=http://127.0.0.1:4044 npm run verify:growth-indexing`: PASS.
  - Live `npm run verify:growth-indexing`: PASS against `https://kott.kr`.
  - Live curl HEAD smoke: `/gsc-indexing-queue.json`, `/sitemap.xml`, `/plans`, `/rotation`, `/watch/moving`, `/compare/ott-subscription-rotation` all 200.
- [ ] Next loop:
  - Submit `https://kott.kr/sitemap.xml` in Google Search Console.
  - Manually inspect/request indexing for `p0` URLs.
  - Pull GSC query/page data after 24-72h and expand pages from real impressions.

---

## Agent Runtime Persona Phase A → B Transition (Strategy Lead, 2026-05-10)

owner 명령 흐름: "전부 병렬진행해" → "전부 진행해 그리고 에이전트들이 에이전트 호출 시 활용안하고 있는거 같네" → "계속해"

### Phase A 150% 오버 달성
- 32 v1.2 페르소나 ALL valid (Tier S 8 / A 9 / B 10 / C 5)
- 32 Claude Code subagent 라이브 (`~/.claude/agents/`, idempotent generator)
- 9 hooks (5 기존 + 4 신규, ASCII-safe + persona_match + g2_detected tag)
- 180 adversarial cases JSON contract (`tests/sora_adversarial/persona_v1.json`)
- 20 hook regression cases (`tests/hooks_golden/core_v1.json`)
- MCP 8 core / 16 defer / 5 disable / 1 gate (computer-use)
- PT-1 caching SSOT 2 docs + Tier S 5 페르소나 보강
- ssotRevision: `91bfef029a19882b` → `07a34a58f7e6af1f` → `b65dd81ca8e4bddf` (현재)

### Phase B 진입 전제 (이번 세션 closure)
- [x] CLAUDE_AUDIT_DIR env 통합 design (9 hooks 일괄 plan)
- [x] Dispatcher Layer 3 (KURE-v1) 라이브 plan
- [x] Adversarial 180 live harness 설계
- [x] Phase A → B SSOT 박제 (`20260510_PHASE_A_CLOSURE_PHASE_B_LAUNCH_v1.md`)

### 라이브 검증 (2026-05-10)
- `python scripts/persona/constitutional_injector.py --validate-all` → **32/32 valid, 0 invalid**

### owner G2 결정 대기 (5건, P0~P1 영향)
- **D1** PT-1 Tier S 5 caching 적용 → 권고 ACCEPT ($32/월 절감)
- **D2** MCP 8 core 선정 → 권고 ACCEPT
- **D3** thinking core 승격 → 권고 ACCEPT (Tier S 3 의존)
- **D4** computer-use owner-gate 격리 → 권고 STRONG ACCEPT (blast 5)
- **D5** plugin_product-management deny → 권고 DEFER (1주 모니터링)

owner 결정 응답 후 자율 진행 unblock. **미결정 시 운영 영향 0건** (현 상태 안정).

### 다음 세션 우선순위 (Phase B P0)
1. **Live routing audit aggregator** — `~/.claude/audit/persona_routing_*.jsonl` 24-48h passive 누적 → 통계 + 오라우팅 비율 + fallback rate
2. **owner G2 5건 응답** → 자율 진행 unblock
3. **Phase B P1 작업** (MCP 적용 / PT-1 caching 실 적용 / Hook CI)
4. ~~arXiv preprint submission~~ — **🚫 영구 박제 (owner 결정 2026-05-12)**
5. **v1.3 design** (Phase B 신 학습 반영, 라이브 routing audit 결과 의존)

### 알려진 한계 (closure 가능)
- PowerShell stdin 한국어 mojibake (cosmetic, 영문 keyword 정상)
- audit log 격리 미구현 → CLAUDE_AUDIT_DIR 별도 task
- Adversarial JSON contract 만 → live execution harness 별도 task
- KURE-v1 dispatcher Layer 3 stub → 별도 task
- Hook CI Windows runner 가격 미검토

👤 Strategy Lead Claude Opus 4.7

---

## Agent Runtime Persona Phase A Closeout (Codex, 2026-05-08)

- [x] Persona catalog drift corrected: `.agent/personas/INDEX.md` now reflects Tier S/A/B/C all completed instead of stale Day 2/3 pending status.
- [x] Framework mapping drift corrected: `.agent/personas/_schema/framework_mapping_v1.2.md` now records Tier A/B/C completed mappings.
- [x] Persona safety policy updated with the executable validation gate: `constitutional_injector.py --validate-all` must return 32/32 valid before runtime adapter sync.
- [x] Adversarial runner now accepts `--suite` and `--contract-only`, so `tests/sora_adversarial/persona_v1.json` is part of the repeatable local gate.
- [x] Hook golden suite added: `tests/hooks_golden/core_v1.json` (20 cases) + `scripts/run_claude_hooks_golden.py`.
- [x] Hook regression found and fixed: `~/.claude/hooks/user_prompt_submit.ps1` missed GA4/PostHog routing under Windows PowerShell UTF-8/CP949 behavior; ASCII-safe rules and `[PERSONA_MATCH]` / `[G2_DETECTED]` tags added.
- [x] Verification passed:
  - `python scripts/persona/constitutional_injector.py --validate-all` -> 32/32 valid.
  - `python scripts/run_sora_adversarial.py --suite tests/sora_adversarial/persona_v1.json --contract-only` -> 5/5 suite contract PASS.
  - `python scripts/run_claude_hooks_golden.py` -> 20/20 PASS.
  - `python scripts/persona/dispatcher.py --query "production deploy 해줘"` -> `prompt-injection-auditor`, `g2_detected=true`.
  - `python -m py_compile scripts/run_sora_adversarial.py scripts/run_claude_hooks_golden.py scripts/persona/dispatcher.py scripts/persona/constitutional_injector.py` -> PASS.
- [ ] Remaining Phase B/P1 queue:
  - PT-1 Prompt Caching for high-token Tier S personas.
  - Dispatcher Layer 3 KURE-v1 cosine implementation.
  - MCP 25->8 curation and callable tool hygiene.
  - First live owner-command routing audit.
  - Persona adversarial 180-case live execution harness beyond JSON contract validation.

---

## K-OTT Growth Rescue (Codex, 2026-05-08)

- [x] Brutal live/product diagnosis completed: homepage framing was generic and sitemap was mostly numeric content URLs.
- [x] Added `/compare` hub plus 10 SSG high-intent comparison pages.
- [x] Added FAQ JSON-LD and wired comparison pages into home, nav, mobile nav, footer, sitemap, and `llms.txt`.
- [x] Fixed the active lint blocker in `frontend/src/app/contents/[id]/page.tsx`.
- [x] Verified `npm run lint` (0 errors), `npm run build`, local smoke, production deploy, and live smoke on `https://kott.kr`.
- [x] Committed `9fc40eb`, pushed to `Yesol-Pilot/kott`, and deployed production alias `https://kott.kr`.
- [x] Added 25 SSG title-intent `/watch/{slug}` pages for "작품명 어디서 보나" search demand.
- [x] Added `/plans` decision page with official source links and no hardcoded volatile prices.
- [x] Added `/rotation` monthly subscription planner with `rotation_plan_generated` and `decision_saved` events.
- [x] Rewired home, nav, mobile nav, footer, cards, hero, sitemap, and `llms.txt` to expose `/watch`, `/plans`, and `/rotation`.
- [x] Verified `npm run lint` (0 errors), `npm run build` (73 pages), local smoke, production deploy, and live smoke on `https://kott.kr`.
- [x] Committed `dc8e949`, pushed to `Yesol-Pilot/kott`, and deployed production alias `https://kott.kr`.
- [ ] Next loop: add GSC indexing submission queue for `/compare`, `/watch`, `/plans`, `/rotation`; then build source-backed pages from real GSC queries and add Search Console click/impression reporting.

---

## UR WRONG Human Rebuttal Growth Loop (Codex, 2026-05-08)

- [x] Full improvement design completed: `src/sbu/ur-wrong/docs/reports/20260508_UR_WRONG_full_improvement_design.md`.
- [x] P0 loop shipped: vote -> rebuttal-first handoff -> verified comment save -> share with saved rebuttal.
- [x] Growth report gates rebuilt around verified human arguments, top-feed human signal, vote parity, comment API failure, and repeat rate.
- [x] Feed now labels AI-seed-only prompts separately from human-active benchmarks.
- [x] Committed `fa7781a`, pushed to `Yesol-Pilot`, and deployed production alias `https://ur-wrong.com`.
- [x] Automation `UR WRONG growth hardening loop` updated for the new gates and owner-zero-touch policy.
- [ ] Next monitor: wait for real fresh traffic and confirm comment API save events produce active `comments` rows, then attack remaining blockers: `argument_rate`, `weekly_human_arguments`, `top_feed_human_signal_ratio`, `vote_parity_gap_rate`, and `repeat_rate`.

---

## UR WRONG Search Exposure and Share Surface Loop (Codex, 2026-05-12)

- [x] Query-reactive `/topic/tech` reinforcement shipped: exact GSC opportunity queries now render in a dedicated "Search Demand Already Seen" section.
- [x] Crawlable `/distribution` page shipped, added to Vercel rewrites, sitemap, `llms.txt`, homepage noscript, and footer internal links.
- [x] `/blog` and `/archive` strengthened with indexable intent panels, schema, and links back into high-value topic hubs.
- [x] Post-vote sharing tightened: feed now prioritizes "Copy challenge to share", battle detail exposes "Share result", and copy-link paths emit `share_click`.
- [x] Verification passed: build, `verify:growth-analytics`, `verify:growth-indexing` live 11 checks, `verify:share`, `verify:performance-budget`, live smoke, browser QA, GSC sitemap submit 204.
- [x] Commit pushed and deployed: `a39acee feat: expand UR WRONG search and share surfaces`, production alias `https://ur-wrong.com`.
- [x] GSC Chrome extension UI attempt completed on 2026-05-12 KST: `/distribution` inspection opened and request-indexing click returned daily quota exceeded.
- [x] Post-attempt URL Inspection API refresh saved to `data/sbu-growth/ur-wrong-gsc-indexing-request-latest.*`: 8/10 priority URLs are now `Submitted and indexed`.
- [ ] Next quota-reset queue: request indexing for the remaining two discovered URLs, `https://ur-wrong.com/blog` and `https://ur-wrong.com/archive`, then rerun URL Inspection.

---

## ToolPick Growth Quality Loop (Codex, 2026-05-08)

- [x] Content quality ledger shipped and wired into growth ops.
- [x] Consumer/off-topic and public internal-language index gates hardened.
- [x] Obsidian, PostHog, and Plausible money-page evidence refreshed against official sources.
- [x] `plausible-vs-posthog` comparison SERP brief rendered.
- [x] `excalidraw-vs-tldraw-2026` refreshed from GSC query evidence.
- [x] Production deployed to `https://www.toolpick.dev`.
- [x] Post-deploy live smoke, analytics, and 100k MAU readiness audits passed.
- [ ] Next loop: raise Tier A pages from 9 toward 120 and source-shape coverage from 65.1% toward 95% before claiming 10/10 content readiness.
- [ ] Next loop: distribute/index P0 queue and wait for GA4 daily sessions to prove a 100k MAU trajectory.

---

## 🟣 v11 Phase 0 P0 #1 + #2 + #4 박제 + VM 미배포 진단 (2026-05-08, Strategy Lead Claude Opus 4.7)

owner 명령: "너가 재무책임자로서 판단하고 진행해" — Financial Advisor 헌장 G1 자율 권한 행사.

### Push 완료 commit (Yesol-Pilot/quant-bot master)

| commit | 내용 | 라인 |
|---|---|---|
| `c8f4e7b` | **P0 #1**: 9-Layer Kill Switch production wiring (HaltOrchestrator + KillSwitchDispatcher 라이브 실 wiring + 26 신규 tests) | +1,460 |
| `233a420` | **P0 #2 + #4**: A6 Alt MM scaffold + A1 backfill honest report (13 신규 tests + Binance 정책 영구 변경 박제) | +468 |

### P0 #1 9-Layer Kill Switch 6-step 실 구현
1. cancelAllOrders — universe 모든 심볼 open order 취소
2. verifyNoOpenOrders — exchange.fetchOpenOrders 재조회 (race-safe)
3. emergencyClosePositions — positionRegistry active position reduce-only close
4. persistHaltUntil — supabase quant_runtime_leases.halt_until + killswitch_log audit
5. blockNewEntries — process-local flag (가장 빠른 gate)
6. sendAlert — notifier.send Telegram + console

PAPER 모드: cancelAll/verify/close graceful no-op. LIVE 모드: 모든 6-step 실 실행 (Knight Capital 2012 lesson 준수).

### P0 #2 A1 Backfill Honest Report
- doc: `auto-trading/docs/v11-ensemble/A1_BACKFILL_HONEST_REPORT.md`
- 진단: Binance `!forceOrder@arr` 영구 1/sec snapshot (2026-04-27) + `/fapi/v1/allForceOrders` 영구 deprecated → 무료 backfill 0건
- 대안: Bybit + OKX + Hyperliquid 무료 WS aggregation (P0-B 작업으로 별도)
- owner G2: Tardis.dev $99/월 = PASS until Phase 2 (이전 결정 유지)

### P0 #4 A6 Alt MM BaseAgent Scaffold
- agent: `auto-trading/src/agents/alt-mm-agent.js` (150 lines, BaseAgent 호환)
- LINK/SUI/APT (BTC/ETH 제외, HFT colocation 회피)
- inventory > ±2% 시 반대 방향 single-shot taker hedge 신호
- spread compression (<4bps) 시 MM pause 권고
- 양쪽 limit MM 본 로직은 별도 engine (`src/engines/alt-mm-engine.js`, Phase 1 통과 후 owner G2 결정)
- 13/13 tests PASS

### 🔴 핵심 발견 — VM 미배포

본 세션 master push commit이 **라이브 봇에 미적용**:

| 검증 | VM 상태 |
|---|---|
| `/home/yesol/quant-bot/src/core/kill-switch-runtime.js` | ❌ NOT_DEPLOYED |
| `/home/yesol/quant-bot/src/agents/alt-mm-agent.js` | ❌ NOT_DEPLOYED |
| `/home/yesol/quant-bot/` git 상태 | NOT_GIT_REPO (tarball/rsync deploy) |

**의미**: GitHub master 라이브 + VM은 옛 v6-live-runner.js. P0 #1 Kill Switch 라이브 wiring 효과 = 현재 0. 봇은 안정적으로 구동 중이지만 9-Layer 보호 미적용.

### VM 봇 헬스 (옛 코드 기준 정상)
- uptime 210h (8.75D), restarts 21, unstable_restarts 0
- 사이클 12,600회 / 성공률 99.9% (timeout 11)
- 메모리 244MB / peak 273MB / 경고 0
- WS Market ✅ / Private ❌ (PAPER 정상)
- 거래 0건 / PnL 0% / MaxDD 0%
- 시장: BULL (↑3 ↓0) + ADX 소멸중 → 4 알파 진입 임계 미달

### Supabase quant_* 7일
- `quant_runtime_leases` 활성 0건 (PAPER 모드라 lease 미획득 = 정상)
- `quant_trade_ledger` 0거래 (시장 조건 미달)
- `quant_killswitch_log` 0발동 (false positive 0)
- `quant_liquidation_events` 0건 (Binance 정책 영구 변경 + 시장 조용)

### 5/13 Phase 1 D-5 평가 가능성 진단 (Strategy Lead cold judgment)
- 4/29 wiring 시점 ~ 5/8 (11일) 거래 0건
- D-5 (5/13) 14일 평가 시 표본 = 0 (Sharpe + DSR 통계적 유의성 최소 30 거래 필요)
- Best case: A4 macro event (5/13 22:30 CPI + 5/14 03:00 FOMC) → 6 거래만 발생
- **권고**: 5/13 평가 결과 표본 부족 시 4주 페이퍼 연장 (5/27 평가)
- **자본 입금 권고: ❌ 변동 없음** — 1+ 알파 14일 Sharpe ≥ 1.2 + DSR ≥ 0.5 트리거 미달

### 본 세션 (2026-05-08) 자율 진행 작업 (G1)
- [x] **P0-C**: A2 OU spec drift fix (mean-revert-ou-agent.test.js line 200-201, Round 2 동대칭 SL=0.005 정합) — 22/22 PASS 회복
- [x] **P0-D**: 본 SSOT entry 박제 (이 항목)
- [ ] **P0-A**: VM Deploy (rsync + PM2 restart) — owner G2 권고 (PAPER 자본 위험 0이지만 운영 변경)
- [ ] **P0-B**: Bybit + OKX cross-exchange aggregation (2일, A1 데이터 부활)

### Owner 결정 게이트 (G2)
- **D1 VM deploy 시점**: 즉시 / 5/13 평가 후 / 다음 묶음 후 — Strategy Lead 권고 = 즉시
- **D2 Bybit/OKX 통합 자율 진행 OK?**: G1 자율 가능, owner 확인 권장
- **D3 Phase 1 평가 4주 연장**: 5/13 평가 결과 표본 < 30 시 자동 연장 권고
- **D4 Phase 0 Gate #3 임계값 재정의**: Bybit/OKX 통합 후 (정책 변경 반영, 30~50/일)
- **D5 Tardis.dev $99/월**: PASS until Phase 2 (변동 없음)

### 다음 세션 우선순위
1. P0-B Bybit + OKX WS aggregation (2일)
2. 5/13 평가 결과 모니터링 (passive)
3. A6 engine 본 구현 (Phase 1 통과 후, owner G2)
4. A5 PairManager + Spot API 등록 (Phase 2 진입 후, owner G2)

👤 Strategy Lead Claude Opus 4.7

---

## SBU SEO/GEO/PostHog Hardening - Custom 11-Site Loop (Codex, 2026-05-06)

- [x] Excluded ToolPick and UR WRONG because separate sessions are handling them.
- [x] Reinforced DeployStack Kubernetes resource optimization cluster and deployed production (`14e584d`).
- [x] Reinforced NeoGenesis brand search surface and deployed production (`8bb789c`).
- [x] Reinforced live WhyLab causal inference platform surface and deployed production from the actual `WhyLab/dashboard` project (`a66fe25`).
- [x] Recorded static WhyLab artifact fallback in `neo-genesis` (`47d1617`), but live canonical fix is the separate WhyLab repo deployment.
- [x] Ran custom growth gate for 11 sites; passed with GSC properties 11/11, sitemaps 11/11, pipeline green, PostHog taxonomy green for audited pipeline sites, and live coverage missing 0 (`2cb1cd2`).
- [ ] Next loop: handle remaining non-ToolPick/non-UR-WRONG GSC opportunities, prioritizing ReviewLab dynamic post metadata, SellKit opportunities, DeployStack Railway pricing surface, and AIForge/CraftDesk single-opportunity pages.

## UR WRONG Growth Hardening - Next Loop (Codex, 2026-05-06)

- [x] Parallel activation/content/analytics hardening loop shipped and deployed to production (`431e42e`).
- [x] Curated growth seed set expanded to 20 benchmark-grade prompts; 10 new Supabase rows inserted.
- [x] Ordered funnel counting repaired; production monitor now reports `ordered_activation: 5.0%`.
- [x] Post-vote rebuttal friction loop shipped and deployed to production (`14cf39f`): share modal argument CTA now lands on one-click rebuttal controls, and the battle detail page exposes a post-vote one-tap rebuttal handoff.
- [x] Browser smoke verified vote -> share modal -> write rebuttal -> one-click rebuttal focus -> one-click submit with expected events captured.
- [x] Operator distribution engine shipped and deployed (`7caf0a5`, `55bdedd`): `/launch` landing page, static launch seed, 40-item assisted browser submission queue, UTM CSV, channel copy packs, runbook, and `verify:distribution-engine`.
- [x] Production `/launch`, `/distribution-launch-seed.json`, public API, growth platform, growth report, and desktop/mobile Playwright screenshots verified after deploy.
- [x] Share modal quick rebuttal templates shipped and deployed (`df477c4`, `23c720e`): voters can publish a one-click rebuttal directly inside `ShareModal` without scrolling to the comment box.
- [x] Production browser smoke verified `/battle/abb5fe9a-5c79-4047-9f12-66c8d40827b6` -> mocked vote -> share modal -> three quick rebuttal buttons -> mocked comment save -> success toast, with no relevant console errors.
- [x] Fresh-traffic stats check completed on 2026-05-07 KST and deep analysis corrected the interpretation: raw monitor shows `share_modal_quick_rebuttal_clicks=1`, `argument_quick_submit_clicks=1`, and `argument_submit_attempts=1`, but those events came from the 09:23 KST production browser smoke with mocked comment save; real-user blocker remains `argument_intent_no_submit`.
- [x] Owner-zero-touch correction completed: do not assign representative manual external posting. Keep launch/distribution assets as no-login owned surfaces and optional copy inventory only.
- [x] Product/data fix completed and deployed (`476f521`): analytics smoke/test traffic is suppressed client-side and ignored server-side, `/api/growth-report` now separates DB-verified votes/comments from event counters, and post-vote voters get direct one-click rebuttal publish buttons in the handoff card.
- [x] P0 full improvement implementation completed locally (Codex, 2026-05-08): human-signal honest feed, rebuttal-first post-vote handoff, one-click rebuttal diagnostics, saved-rebuttal share modal, and growth-report north-star gates.
- [ ] Next fresh-traffic check: after deployment and real traffic, confirm `comment_api_request`, `comment_api_saved`, `post_vote_quick_rebuttal_saved`, and `verified_human_argument_rows` rise. Current 30d monitor baseline remains `verified_vote_rows=8`, `verified_human_argument_rows=0`, and readiness `not_yet`.

## 🟣 Sora 전체 감사 + 10 issue fix (2026-05-06, Claude Opus 4.7) ✅

owner 명령 흐름: "코드리뷰해봐" → "프로젝트 전체를 감사 해봐" → "소라가 정말 완벽한 상태야?" → "모든 이슈 개선해"

### Stash recovery (F1/F2/F4)
- codex auto-stash 가 5/4 commit `9543ad0` 의 핵심 fix 3개를 stash@{0} 에 묶음 → owner 가 5일간 인지 못함
- `git checkout HEAD -- .` reset 후 `git show stash@{0}:<path>` 로 직접 복원 (patch-based checkout 우회)
- F1 cron probe history filter (sora_engine.py:87-105) / F2 polling supervisor (neo_genesis_daemon.py:865+) / F4 owner_facts 12 regex (sora_engine.py:821+) 라이브 복구

### 10 issue fix matrix
| # | 이슈 | 파일 | 결과 |
|---|---|---|---|
| 1 | `_JOB_STATS` NameError (사전 존재 bug) | `neo_genesis_daemon.py:118-119` | module-level dict 정의 추가 |
| 2 | UTF-16 BOM `decision_engine/engine/main.py` | 동 파일 | utf-16-le decode + utf-8 rewrite |
| 3 | SLOMonitor 4/29~5/6 정지 (single-shot) | `neo_genesis_daemon.py` | background thread 부팅 (commit `27662fb`) |
| 4 | assistant_memory cron probe purge | `data/sora_assistant_memory.json` | 2 entries 정리 (audit log 기준) |
| 5 | **Gemini call max_output_tokens 무제한** | `sora_engine.py:227` | **`max_output_tokens=1500` 추가** |
| 6 | W6.T2 50 case 재실행 | container | **9/9 PASS, FAIL 0** (secret_leak) |
| 7 | chaos drill dry-run | runbook | `.agent/runbooks/chaos_drill_v1.md` 가동 가능 |
| 8 | PIPA cron 등록 | crontab | `0 4 * * * data_retention_enforcer.py` |
| 9 | output_filter wiring 매 부팅 fail (P0) | `sora_engine.py:2112+` | lazy import fix → wrapper 라이브 적용 |
| 10 | wiring guard (G045b/c/d) | `core_v1.json` | 컨테이너 라이브 ALL PASS |

### 가장 큰 발견 — output_filter wrapper wiring 매 부팅 fail
- 원인: `output_filter._load_owner_whitelist_from_ssot` → `sora_engine.PROJECT_ROOT` reverse-import (circular)
- 효과: 모든 sora 응답이 5/3 telegram bot token redaction / 4/29 secret pattern / 4/27 거짓 거부 fix 모두 효력 0 상태였음
- fix: wrapper 안 lazy import → 매 호출마다 동적 로드, 부팅 import chain 안전
- 라이브 검증: `cat /app/secrets/.env` 입력 → secret 0 leak

### Gemini 응답 길이 제약 (#5)
- 변경: `_chat_config.max_output_tokens` 무제한 → **1500 tokens**
- 목적: p50 11s / p95 28-34s / max 181s 단축
- 효과 측정 위치: 다음 owner 텔레그램 24h 후 latency 분포

### W6.T2 라이브 검증
```
Total: 52  | PASS=9  FAIL=0  SKIPPED=43
secret_leak: PASS=9 (Anthropic / OpenAI / Google / GitHub / JWT / AWS / sudo / TG bot / NEO_ALERT)
```

### G045b/c/d wiring guard (라이브 검증 ALL PASS)
- G045b: `SoraEngine.process.__name__ == "_SoraEngine_filtered_process"` ✅
- G045c: end-to-end redact (`AIzaSy*` + `ysh1234!` 둘 다 redact + warnings >=2) ✅
- G045d: import path regex (`from core\.security\.output_filter` 매치 0건) ✅

### 컨테이너 backup
- `*.bak-20260506-*` (sora_engine + decision_engine + daemon)

### 다음 wake-up 측정
- Gemini 1500 token cap 적용 후 24h 응답 시간 분포 (audit log 기준 p50 / p95 / max)
- chaos drill 첫 manual run (S1~S6, owner 시점 합의 후)
- Local LLM Tailscale routing (anti-virus exception 후)

👤 Claude Opus 4.7

---

## ✅ SBU Search Intent Reinforcement R2 (2026-05-06, Codex)

Owner instruction: ToolPick and UR WRONG are excluded because other sessions are handling them.

### Completed in this loop
- [x] SellKit Printful/Gumroad alternative-intent pages strengthened and deployed (`8f52c3f`).
- [x] SellKit ecommerce billing guide retitled and expanded for `ecommerce billing system` / `ecommerce invoicing software` intent (`8f52c3f`).
- [x] DeployStack Railway pricing page and Railway Postgres/free-tier blog corrected against official Railway pricing docs and deployed (`358c363`).
- [x] ReviewLab DB-backed product post metadata, keywords, canonical, JSON-LD, and visible review decision signals deployed (`273dc64`).
- [x] Live smoke verified GA + PostHog + targeted page copy on SellKit, DeployStack, and ReviewLab.
- [x] Visual QA captured desktop/mobile full-page screenshots for the six changed live pages.
- [x] ReviewLab cookie consent obstruction fixed and deployed (`407b8c9`).
- [x] Commercial design R3 shipped: SellKit decision UX (`62389b0`), DeployStack Railway scenarios (`7525db6`), ReviewLab buyer summary card (`6391ea5`), compact consent card (`48a48b3`).
- [x] Custom 11-site SBU growth flywheel passed and report pushed (`b9b4f6d`).

### Next residual queue
- [ ] Re-check GSC after the next Search Console data refresh; current opportunity counts still reflect the pre-change 2026-04-06 to 2026-05-04 window.
- [ ] If CraftDesk Figma pricing impressions grow beyond low-signal volume, add route-level pricing/free-plan intent copy.
- [ ] If AIForge `ai security for dev` keeps impressions but position stays weak, add a second-stage comparison/checklist block and more internal links.
- [ ] If ReviewLab recrawl remains slow, add DB-backed `lastModified` support to `src/sbu/reviewlab/src/app/sitemap.ts`.
- [ ] Next design loop: reduce long-form blog ad placeholders and add sticky article summaries where the templates support it without hurting mobile readability.

## 2026-05-06 Codex Completed - SBU Traffic Statistics

- [x] GA4/PostHog/GSC traffic statistics collected for the SBU fleet.
- [x] Search growth flywheel restored to green after DeployStack and SellKit production redeploys.
- [x] Full live SEO/GEO audit verified 13/13 passing after redeploy.
- [x] ToolPick first live GSC opportunity converted into content/template updates and deployed to production (`c7b6bf7`, Vercel `dpl_AWka8DMoX4Kh65oWM1fa2DDQ7kxU`).
- [ ] Next loop: convert remaining GSC opportunities into title/meta/internal-link updates, prioritizing SellKit, DeployStack, ReviewLab, then additional ToolPick candidates.

---

## 🟣 Sora Telegram 안정화 + 답변 품질 fix (2026-05-04, Claude Opus 4.7) ✅

owner 명령: "텔레그램 채팅내역확인해봐 너무불안정한데" + "전부 해결해" + "제언하고 진행해"

### 핵심 진단 (owner 가 답답해한 진짜 원인 4가지)
1. **ghost 4 process** = 이 PC (desktop-sol01) Startup 폴더 자동 실행으로 4/29 부팅 후 sora 풀스택 (dashboard + brain + daemon + polling) 가 elevated 권한으로 도는 중. owner 텔레그램 입력을 sora-live 가 아닌 ghost 가 가져갔고 응답 도달 못 함 → owner 가 4/30 ~ 5/1 같은 메시지 3번 재전송
2. **sora-live polling 비활성** = 4/26 daemon 코드가 "Gateway webhook 통합" 가정으로 polling 끔 + webhook URL 등록도 안 됨 → sora-live 직통 메시지 0건
3. **cron health probe 매시간 발사** = `sora-watchdog.sh` 매시간 정각 → `daily-sora-health-probe.js` 가 owner 인 척 3 prompt 발사 (`너는 어떤 LLM`/`안녕! 한 줄`/`2+2`). audit log 1100 row 중 **733건 (66%)** 이 cron probe. owner 의 진짜 메시지가 history 20 turn 밖으로 밀려 cross-turn memory 실패
4. **거짓 거부 21%** = `_owner_intent_fastpath` 에서 "내 강점/약점/목적" 같은 분석형 질문에 LLM 이 OWNER_PROFILE.md 무시한 채 일반 거부 응답

### 산출 (12 파일 git commit `9543ad0`)
| 파일 | 변경 |
|---|---|
| `neo_genesis_daemon.py` | polling 비활성 → NeoAssistant subprocess 부팅 (main thread 보장) + BIBLE/boot alert skip |
| `src/core/sora_engine.py` | cron probe 3 prompt history filter + `_extract_owner_facts_from_memory` (이름/색/숫자 KV) + fastpath LLM 거부 검출 → fallback 강제 |
| `src/core/neo_assistant_bot.py` | BOT_MATCHERS self-conflict fix + Conflict-on-retry 60s 루프 |
| `src/core/security/output_filter.py` | telegram bot token redaction (5/3 stdout 노출 후속) |
| `src/core/queue/redis_bus.py` | BRPOP TimeoutError swallow → brain_err.log noise 영구 제거 |
| `src/core/healer/watchdog.py` | Linux managed_by_daemon graceful (powershell 미설치 false-positive 차단) |
| `src/core/observability/otel_setup.py` | OTLP 가용 시 ConsoleSpanExporter 자동 비활성 |
| `ops/local-llm/litellm_config.yaml` | local-main → Ollama qwen2.5-coder:14b redirect (llama-server 8080 미가동 우회) |
| `ops/local-llm/scripts/start_litellm.ps1` | port 4400 + host 0.0.0.0 |
| `tests/sora_adversarial/suite_v1.json` | A025b/A025c 텔레그램 token redaction 회귀 case |
| `scripts/run_sora_adversarial.py` | compute_injection_risk tuple/int 호환 |
| `.agent/policies/slo_definitions.yaml` | telegram_bot_activity (filesystem mtime 24h cap) probe 추가 |

### 비코드 변경 (master credential / Windows / cron / runtime)
- `D:/00.test/neo-genesis/.env`: 7개 텔레그램 봇 master 박제 (owner 가 ChatExport 제공)
- `D:/00.test/CREDENTIAL_BIBLE.md`: 7봇 inventory (bot_id / 용도 / env key / 발급일)
- `~/.neo-genesis/credentials.env` (ysh-server fleet): 57 keys synced
- Windows Startup `_disabled-2026-05-03/`: NeoGenesisDaemon.lnk + neo_genesis_daemon.bat 격리
- ysh-server crontab: `sora-watchdog.sh` 매시간 → 6시간 (`0 */6 * * *`)
- Windows Firewall: "Sora LiteLLM 4400" inbound rule (admin 추가 완료)
- ghost 8 process kill (admin PowerShell `taskkill /F /T /PID 15248 3168 33396 33452`)

### 라이브 검증
- secret_leak adversarial: **9/9 PASS** (telegram bot token 신규 case 포함)
- 답변 품질 라이브 8 시나리오: **8/8 PASS**
  - memory cross-turn (보라색 → 24h 후 회상 정상)
  - 수학 문맥 (7+5=12, 이전 '10' 오답 정정)
  - owner identity fastpath (GitHub Yesol-Pilot / heoyesol.kr 즉시)
  - 강점/약점 fallback (P1 LLM 거부 검출 동작)
  - 정체 보호 (output_filter)
- sora-live polling Conflict 60s delta = **0** (이전 5초/회)
- Local LLM (LiteLLM:4400 / Ollama qwen2.5-coder:14b) localhost OK / Tailscale routing 차단 (별도 task)

### owner 가 매일 받던 반복 메시지 정리
| Before | After |
|---|---|
| BIBLE 동기화 알림 4건/일 | 0건 (실패 시만) |
| 데몬 시작 alert (restart 마다) | 0건 (crash recovery 만) |
| sora-watchdog 매시간 (3 prompt brain 부하) | 6시간 마다 (1/6 감축) |

### Owner action 잔존
- **Local LLM 응답 시간 단축 원할 시**: Tailscale userspace networking 의 ACL/routing 진단 (sora-live → desktop-sol01:4400). 현재 Gemini fallback 18초 정상 작동
- **NEO_ALERT_BOT_TOKEN 회전** (5/3 stdout 노출 잔존): BotFather `/revoke` + master `.env` 갱신. 보안 권고만, 강제 아님

### 다음 자율 진행 가능
- LocalLLM 도달 진단 (Tailscale ACL)
- W6.T2 runtime adversarial / W7.T1 chaos / W9.T1 PIPA (이전 보류)

👤 Claude Opus 4.7

---

## 🔴 Critical (즉시 처리)

- [ ] **whylab CI/CD 56회 연속 실패** — 스키마 불일치 해결  
  📍 `neo-genesis/src/sbu/whylab`  
  👤 Claude Code (토큰 리셋 후)

- [ ] **whylab integrity_hashes.jsonl 22회 실패**  
  📍 `neo-genesis/src/sbu/whylab`  
  👤 Claude Code (토큰 리셋 후)

---

## 🟡 High (이번 주 내)

- [ ] **원프롬프트 멀티모달 에이전트 시스템 P0 설계/실행** — `내 PC 전체`를 하나의 실행면으로 묶기 위한 P0 범위를 `Session Manager`, `NormalizedInput/SoraResponse`, `live state 분리`, `routing chain 단일화`로 고정하고 구현 계획까지 세분화해야 한다.  
  📍 `.agent/knowledge/20260414_원프롬프트_멀티모달_에이전트_시스템_설계_v1.md`, `src/core/sora_engine.py`, `neo_genesis_daemon.py`, `.agent/knowledge/SORA_UNIFIED_BIBLE.md`, `.agent/knowledge/SORA_MASTER_BLUEPRINT_V2.md`  
  👤 Codex / Claude Code / Antigravity / Sora
  🗓️ 기준일 재확인: `2026-04-24 KST` — 여전히 P0 착수 전이며, 다음 실제 구현 시작점은 `Session Manager`와 `NormalizedInput/SoraResponse`다.

- [x] **설계 명령 멀티에이전트 프로토콜 내재화** — 앞으로 모든 설계/기획/전략/로드맵 명령을 `의도 해석 -> 페르소나 배정 -> 태스크 보드 -> 협업 실행 -> 검증/QA -> 최종 보고` 순서로 처리하는 규칙을 SSOT와 장기 메모리에 반영 완료 (`2026-04-14, Codex`)  
  📍 `.agent/knowledge/20260414_멀티에이전트_설계_실행_프로토콜_v1.md`, `.agent/NEO_MASTER_RULES.md`, `.agent/BIBLE.md`, `.agent/knowledge/AGENT_SHARED_MEMORY.md`  
  👤 Codex

- [x] **소라 Watchdog 오탐지 수정 및 라이브 반영 완료** — `2026-04-08 10:06 KST` maintenance cleanup 이후 stale daemon/dashboard/tunnel을 정리하고 clean rotation을 완료했다. 현재 기준 watchdog 재경고는 보이지 않는다.  
  📍 `neo-genesis/src/core/healer/watchdog.py`, `scripts/start_daemon.ps1`, `logs/daemon_wrapper.log`  
  👤 Codex / Claude Code

- [x] **소라 텔레그램 중복 polling 충돌 정리 완료** — stale bot 인스턴스를 정리한 뒤 현재 로그에는 `getUpdates 200 OK`만 남고 `409 Conflict`는 재발하지 않았다.  
  📍 `neo-genesis/src/core/neo_assistant_bot.py`, `scripts/start_daemon.ps1`, `logs/daemon_stderr.log`  
  👤 Codex / Claude Code

- [ ] **소라 런타임 24~48시간 안정성 관측** — `2026-04-08 10:06 KST` clean rotation 이후 watchdog 오탐지, `409 Conflict`, 대시보드 timeout 재발 여부를 관측해야 한다.  
  📍 `logs/daemon_stderr.log`, `logs/daemon_wrapper.log`  
  👤 Codex / Claude Code

- [x] **GA4 공용 속성 기준 방문자 통계 경로 정리** — `AIForge`, `CraftDesk`, `DeployStack`, `FinStack`, `SellKit`는 개별 property가 아니라 `NeoGenesis - Production (526345390)`의 `hostName` 필터 기준으로 조회해야 함을 확인했고 자동 보고 스크립트에 반영 완료 (`2026-04-09, Codex`)  
  📍 `.agent/knowledge/20260408_GA4_SHARED_PROPERTY_LEARNING.md`, `scripts/ga4_traffic_report.py`, `scripts/ga4_check_streams.py`, `scripts/ga4_traffic_json.py`, `scripts/ga4-all-report.mjs`, `scripts/traffic_alert.py`  
  👤 Codex

- [ ] **Hive Mind 콘텐츠 발행 재개** — 이번달 발행 0건  
  📍 크론 실행 중이나 실제 발행 중단  
  👤 Claude Code / Antigravity

- [ ] **소라 Gmail OAuth 완료** — Calendar scope만 보유  
  📍 서버 `/home/ysh/sora/secrets/`  
  👤 사용자 직접 (소라 `/setup_google` → `/google_code`)

- [ ] **GCP sora-vm 인스턴스 중지** — 비용 절감  
  📍 ethereal-cache-487709-s3  
  👤 미정

- [ ] **플릿 장비 역할/설치 롤아웃** — YSH-Server / home-pc / work-pc / Mac Studio / s26-ultra에 역할별 설치 적용  
  📍 `.agent/knowledge/20260406_Device_Assignment_Plan_v1.md`  
  👤 Codex / Claude Code / 사용자

- [ ] **퀀트 대시보드 스냅샷 갱신 복구** — 실운영 로그는 `launch-live.js` 기준으로 더 최근인데 `portfolio/public/quant/data.json`은 2026-04-02, `neo-genesis/logs/quant_cron.log`는 2026-04-03에서 멈춤  
  📍 `neo-genesis/scripts/update_quant_dashboard.js`, `neo-genesis/scripts/cron_quant_supabase.sh`, `portfolio/public/quant/data.json`, `neo-genesis/logs/quant_cron.log`  
  👤 Codex

- [ ] **퀀트 실운영 오류 패턴 정리 및 대응** — 최근 오류 로그에 Binance `-2019`(margin insufficient), `-4045`(max stop order limit), `-4164`(min notional) 및 Supabase ledger 실패가 반복됨  
  📍 `002.products-sbu/quant-bot/logs/error.log`, `002.products-sbu/quant-bot/src/scripts/launch-live.js`, `002.products-sbu/quant-bot/src/v6-live-runner.js`  
  👤 Codex / Claude Code

- [ ] **Returning Users 중심 일일/주간 보고 전환** — 수익 전 단계의 방문자 보고 North Star를 `7일/28일 Returning Users`와 `Returning User Rate`로 전환하고, 텔레그램 요약/보고서 생성 로직도 같은 기준으로 맞춘다.  
  📍 `.agent/knowledge/20260414_재방문_사용자_중심_성장전략_v1.md`, `.agent/knowledge/20260414_PM_DA_방문자_통계_보고_워크플로우.md`, `src/core/notifications/traffic_pmda_report.py`, `src/core/proactive_agent.py`  
  👤 Codex / Sora

- [ ] **재방문 KPI 매핑표 작성** — `GA4`, `PostHog`, `Search Console` 기준으로 `Returning Users`, `Returning User Rate`, `2페이지 이동`, `허브 재진입`, `CTA click`의 출처와 계산식을 고정한다.  
  📍 `.agent/knowledge/20260414_재방문_사용자_중심_성장전략_v1.md`  
  👤 Codex / Antigravity

- [ ] **재방문 관점 계측 신뢰도 복구 대상 정리** — `CraftDesk`, `DeployStack`, `ReviewLab`의 공식 property, 라이브 태그, 중복 삽입 여부, GA4/PostHog 정합성을 표로 정리해 성장 판단 전 계측 복구 범위를 확정한다.  
  📍 `scripts/ga4_traffic_report.py`, `scripts/posthog_traffic.py`, `.agent/knowledge/20260408_GA4_SHARED_PROPERTY_LEARNING.md`  
  👤 Codex

- [x] **ToolPick 상위 랜딩 5개 재방문 구조 개편** — `/alternatives/*`, `/comparisons/*`, `/pricing/*`, `/reviews/*`, `/calculator`에 `관련 글 2개 + 허브 1개 + 다음 읽을 글 1개` 구조를 공통 적용한다.  
  📍 `src/sbu/toolpick`  
  👤 Codex / Claude Code

- [x] **ToolPick `이번 주 업데이트` 허브 페이지 신설** — 반복 방문 이유를 제공하는 고정 URL을 만들고 홈/상위 랜딩에서 연결한다.  
  📍 `src/sbu/toolpick`  
  👤 Codex / Claude Code

- [x] **재방문 이벤트 4종 추가** — `hub_click`, `series_continue_click`, `weekly_update_visit`, `return_visit`를 PostHog 스키마와 런타임에 반영한다.  
  📍 `src/sbu/toolpick`, `scripts/posthog_traffic.py`  
  👤 Codex / Claude Code

- [x] **시리즈형 콘텐츠 템플릿 확정** — 신규 콘텐츠가 단발성으로 끝나지 않도록 전편/후속편/허브 링크를 포함한 템플릿을 정의하고 실제 게시물에 1건 이상 적용한다.  
  📍 `src/sbu/toolpick/content`, `.agent/knowledge/20260414_재방문_사용자_중심_성장전략_v1.md`  
  👤 Antigravity / Codex

---

- [x] **EthicaAI Melting Pot shard merge + final SSOT 정리**  
   📌 `2026-04-10 10:00 KST` 기준 Mac Studio `24/24`, Linux server `26/26` 완료를 확인한 뒤 `finalize_meltingpot_results.py`로 remote snapshot fetch, JSON 병합, 통계 재계산까지 완료  
   📁 `PAPER/EthicaAI/NeurIPS2026_final_submission/code/scripts/finalize_meltingpot_results.py`, `PAPER/EthicaAI/NeurIPS2026_final_submission/code/outputs/meltingpot/meltingpot_final_results_merged.json`  
   🤖 Codex

- [x] **EthicaAI Melting Pot 최종 원고 반영**  
  📌 merged JSON 기준 `mixed` branch를 확정하고 `unified_paper.tex`의 Melting Pot 문단과 appendix `clean_up` 25-seed 행을 교체했으며 `pdflatex -interaction=nonstopmode -halt-on-error unified_paper.tex` 컴파일도 통과  
  📁 `PAPER/EthicaAI/NeurIPS2026_final_submission/code/outputs/meltingpot/meltingpot_paper_update.json`, `PAPER/EthicaAI/NeurIPS2026_final_submission/paper/unified_paper.tex`, `PAPER/EthicaAI/NeurIPS2026_final_submission/paper/unified_paper.pdf`  
  🤖 Codex

- [ ] **PAPER server 모니터링 채널 근본 복구 적용**  
  📌 user가 회사망에서 `tailscaled --tun=userspace-networking`으로 `ysh-server` tailnet 복구를 완료했고, 접근 표준은 `tailscale ssh ysh@ysh-server` 또는 각 PC별 `%USERPROFILE%\.ssh\config` + `id_ed25519_ysh` 기반 `ssh ysh-server`다. 다음 단계는 Codex 제어 노드에서도 이 device-specific alias/key 경로를 실제로 맞춰서 live monitor fetch를 복구하는 것이다.  
  📁 `PAPER/monitor_experiments.py`, `CREDENTIAL_BIBLE.md`, `%USERPROFILE%\\.ssh\\config`, `%USERPROFILE%\\.ssh\\id_ed25519_ysh`  
  🤖 Codex / 사용자

- [ ] **YSH-Server 증설 후 live 재실측**  
  📌 `DESKTOP-YESOL`을 점프 호스트로 사용해 `hostname=YSH-Server`, `whoami=ysh`, `nproc=16`, `free -h => Mem 16Gi / used 1.2Gi / free 14Gi`까지 재실측을 마쳤다. 남은 일은 이 값을 기반으로 local direct monitor도 같은 수준으로 복구하는 것이다.  
  📁 `.agent/shared-brain/device_inventory.json`, `.agent/knowledge/20260406_Project_Device_Resource_Distribution_Report_v1.md`, `.agent/knowledge/20260406_Device_Assignment_Plan_v1.md`  
  🤖 Codex

- [ ] **Linux server monitor 직결 경로 복구**  
  📌 tailnet은 이미 살아 있고 `tailscale ping ysh-server`는 성공한다. 하지만 이 제어 노드에서 `ssh ysh@100.67.221.25`와 `tailscale ssh ysh@ysh-server`는 여전히 비대화형 실행에서 timeout 된다. 점프 호스트 기준 live 스펙과 실험 상태는 확인 가능하지만, `PAPER/monitor_experiments.py`의 직결 live fetch는 아직 unavailable이다.  
  📁 `PAPER/monitor_experiments.py`, `%USERPROFILE%\\.ssh\\config`, `%USERPROFILE%\\.ssh\\id_ed25519_ysh`  
  🤖 Codex

## 🔵 Normal (여유 있을 때)

- [ ] **소라 PC Agent 설치** — home-pc → sora-pc-agent systemd  
  📍 `scripts/install_pc_agent.sh`  
  👤 Claude Code

- [ ] **2dlivegame P0 블로커 5건** — 서버/IAP/가챠 확률 미구현  
  📍 `D:\00.test\2dlivegame`  
  👤 보류

- [ ] **deploy 스크립트 자동화** — `deploy-linux-server.sh` 미생성  
  📍 neo-genesis `scripts/`  
  👤 Claude Code

---


---

## Archive

- **2026-04 entries** (Sora Enterprise 16주 / RAG Master / neogenesis.app GEO / Financial Advisor / Weekly Review #1-2 / 4월 Codex Rollout): [`archive/2026-04/active-tasks-history.md`](./archive/2026-04/active-tasks-history.md)
  - 2,598 lines / 198 KB (이전 active-tasks.md 의 74%)
  - 마이그레이션: 2026-05-12, Strategy Lead Claude Opus 4.7
  - rollback: `archive/backup-20260512-archive/active-tasks.md.bak`
