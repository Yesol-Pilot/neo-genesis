# Handoff: Claude Code 세션 (2026-04-10 최종, UI/UX 미완 명시)

> **작성자:** Claude Opus 4.6
> **세션 유형:** 전체 Phase 상세설계 + Phase 0~4 구현 + 프론트엔드 완성 + 브라우저 E2E 검증 + Docker v6.3 재빌드

---

## 2026-04-24 운영 전환 — Claude primary, Codex fallback

**결정**: 오너 주력 에이전트를 Codex → **Claude Code**로 전환. Codex는 fallback으로 유지.

**배경**:
- 오너가 세션에서 명시적으로 "앞으로 메인으로 클로드를 쓰고 코덱스는 토큰을 다썼을때만 쓸거야"
- 현 Claude Code 2.1.88 + opus-4-7 1M 컨텍스트 조합이 장시간 리팩터·리뷰·수렴 분석에 가장 적합

**Fallback 트리거 (Codex로 전환하는 조건)**:
1. Claude 토큰 소진 (세션 한도 초과)
2. 24시간 이상 autonomous background 실행이 필요한 장기 작업
3. repo-native shell + apply_patch가 더 경제적인 반복 작업 (예: 대량 파일 batch 편집)
4. Claude 가용성 장애 (API 다운 등)

**Handoff 프로토콜** (Claude → Codex):
1. `handoff.md`에 scoped handoff 기록 (goal, scope, files touched, pending verification, non-goals)
2. Codex는 scope 확인 후 SSOT 경계 준수하며 재개
3. 완료 시 같은 섹션에 상태 entry 추가
4. G2+ 파괴적/외부 액션은 실행자 관계없이 오너 승인 유지

**SSOT 반영 파일** (2026-04-24):
- `.agent/contracts/COLLABORATION_CONTRACT.md` — Core Collaboration Shape + Cross-Review Rule + Fallback Handoff 섹션
- `.agent/knowledge/CLAUDE_COLLABORATION.md` — Objective + Best Collaboration Shape
- `.agent/knowledge/AGENT_RUNTIME_OPTIMIZATION.md` — §2 role table + §4 routing table
- `.agent/knowledge/AGENT_SHARED_MEMORY.md` — §5 role table + §6 change history

---

## 2026-04-24 Agent/UX 심층 리서치 내재화

Claude 4병렬 리서치(R1-R4) → Codex 기존 v2 팩(P0~P6 구현 완료)과 갭 매칭.

**추가된 항목** (6개 파일):
- `research-patterns-v2.md`: LATS, Plan-and-Act, GoalAct/HiPlan, Mem0, A-Mem, Episodic Memory Position, Magentic-One dual-ledger, Mixture-of-Agents
- `ux-product-pattern-library-v2.md`: §3.1 (4 UX 원칙: plan-before-execute, 4-layer status, undo-first approval, 3-level uncertainty + AX + anti-workslop + ambient invocation), §4.1 (OSS 라이브러리 picks: AI Elements, assistant-ui, Streamdown, CodeMirror 6, Shiki-stream, react-xtermjs, cmdk, Tremor, Base UI, Motion v12)
- `framework-scorecard-v2.md`: §1.1 Durable Execution (Temporal+OpenAI SDK, Restate, Dapr Agents, Inngest, Trigger.dev, DSPy, Mirascope)
- `security-governance-threat-model-v2.md`: §5.1 Dynamic/Adaptive Red-Team (Attacker Moves Second 경고)
- `benchmark-eval-registry-v2.md`: AgentHarm (ICLR 2025) + Attacker Moves Second 추가
- `README.md`: Watch List (AX, ARLAS, AgentSociety, AI Scientist-v2, BeeAI, Computer-Use 성숙도)

**플릿 영향**: 해시 bump 1회, 4대 재동기화 1회.

---

## 2026-04-14 운영 메모

- 설계/전략/로드맵 요청은 이제 기본적으로 `멀티에이전트 태스크 보드` 방식으로 처리한다.
- 다음 세션 에이전트는 설계 명령을 받으면 바로 답변 초안부터 쓰지 말고, 먼저 `의도 -> 페르소나 -> 태스크 -> QA 게이트`를 잡아야 한다.
- 관련 기준 문서:
  - `.agent/knowledge/20260414_멀티에이전트_설계_실행_프로토콜_v1.md`
  - `.agent/knowledge/20260414_재방문_사용자_중심_성장전략_v1.md`

- `Sora`의 routine Telegram 방문자 보고는 이제 단순 운영 요약이 아니라 `PM/DA 방문자 보고` 형식으로 보낸다.
- 적용 경로:
  - `src/core/proactive_agent.py`
  - `src/core/notifications/traffic_pmda_report.py`
  - `src/core/governance/report_gate.py`
- 대체 대상:
  - `evening_report()` 일일 텔레그램 루틴
  - `weekly_digest()` 주간 텔레그램 루틴
- 유지 대상:
  - `morning_briefing()` 일정/운영 브리핑
  - anomaly/approval/security 계열 알림
- 보고 포맷은 고정:
  - `Executive Summary`
  - `Business Signal`
  - `Intent Analysis`
  - `Quality Diagnosis`
  - `Measurement Integrity`
  - `Action Queue`
- `traffic_pmda_report`는 `report_gate`에서 AI 재작성 없이 HTML 본문을 그대로 통과시킨다. 이유는 대표님용 PM/DA 보고 포맷을 임의 요약으로 망가뜨리지 않기 위해서다.

## 완료된 것

### 백엔드 (전부 서버 배포 완료, Docker v6.3)
| 모듈 | 파일 | 상태 |
|------|------|------|
| 3-Checkpoint 보안/버그 14건 | 10개 파일 | ✅ 코드 수정 + 배포 |
| Fleet API (4 endpoints) | api_fleet.py | ✅ 17 routes 등록 확인 |
| File API (4 endpoints) | api_files.py | ✅ 등록 |
| Git API (5 endpoints) | api_git.py | ✅ 등록 |
| Terminal WebSocket | terminal.py | ✅ 등록 |
| Search API | unified_search.py | ✅ 등록 |
| 자동화 엔진 | workflow_engine.py | ✅ 배포 |
| 알림 매니저 | alert_manager.py | ✅ 배포 |
| CLI 한도 관리 | cli_quota_manager.py | ✅ 배포 |
| RAG 인덱서 | code_indexer.py | ✅ 배포 |
| LiteLLM 프록시 | litellm_proxy.py | ✅ 배포 |
| 관찰성 | tracer.py | ✅ 배포 |
| 프롬프트 관리 | prompt_registry.py | ✅ 배포 |
| 품질 테스트 | golden_tests.py | ✅ 배포 |
| 플러그인 | plugin_manager.py | ✅ 배포 |
| 백업 스크립트 | sora_backup.py | ✅ 배포 |
| 메트릭 수집기 | collect_metrics.py | ✅ 배포 |

### 프론트엔드 (전부 Vercel 배포 완료)
| 컴포넌트 | 파일 | 브라우저 확인 |
|----------|------|------------|
| Fleet Dashboard | devices/page.tsx | ✅ 6대 디바이스 표시 |
| DeviceCard | DeviceCard.tsx | ✅ 역할 태그, 상태 dot |
| Terminal 탭 | TerminalPanel.tsx | ✅ 4대 버튼 표시 |
| Code 탭 | CodeEditor/FileTree/GitPanel | ✅ UI 렌더링 |
| Chat | chat/page.tsx | ✅ AI 응답 |
| Home | home/page.tsx | ✅ KPI |
| 검색 패널 | SearchPanel.tsx | ✅ settings 스크롤 확인 |
| 알림 설정 | AlertSettings.tsx | ✅ 5개 규칙 + 조용한 시간 |
| 자동화 | AutomationPanel.tsx | ✅ 5/6 활성 |
| 관찰성 | ObservabilityPanel.tsx | ✅ 렌더링 |
| 플러그인 | PluginPanel.tsx | ✅ MCP 등록 구조 표시 |
| 원격 데스크톱 | RemoteDesktop.tsx | ✅ 준비 중 표시 |
| 메트릭 | DeviceMetrics.tsx | ✅ 코드 존재 |
| 설정 | DeviceSettings.tsx | ✅ 코드 존재 |

### 설계 문서 (5건)
- `SORA_MASTER_BLUEPRINT_V2.md` — 전체 Phase 설계
- `SORA_GOD_TIER_VISION_REPORT.md` — 비전 보고서
- `SORA_COMPASS_ANALYSIS.md` — Compass 교차 분석
- `feedback_completion_verification.md` — 완료 검증 룰
- `feedback_docker_deployment.md` — Docker 배포 교훈 7건

---

## 남은 것 (다음 세션)

### 🔴 P0: Antigravity 수준 UI/UX 구현 (다음 세션 최우선)

현재 UI는 "기능이 동작하는 프로토타입"이지 "제품 수준"이 아니다. 오너가 명시적으로 "Antigravity 수준의 UI/UX가 있어야 한다"고 요구함.

구체적으로 부족한 것:
1. **DeviceCard** — "NaN일 전" 버그, 실시간 게이지 애니메이션 없음, CPU/RAM 값 미표시
2. **전체 디자인** — flat zinc-900 단색, 그라데이션/글로우/depth 없음
3. **FileTree** — 기본 텍스트 목록, smooth expand/collapse 없음
4. **Terminal** — 버튼만 있고 실제 xterm.js SSH 연결 E2E 미확인
5. **애니메이션** — 전환 효과, 스켈레톤 로딩, 호버 효과 부재
6. **Settings** — 텍스트 나열, 카드형 대시보드가 아님
7. **반응형** — 모바일 최적화 부족
8. **전체** — Cursor/Windsurf 수준의 IDE UX와 거리가 멀다

다음 세션에서:
- Antigravity 디자인 시스템 정의 (색상 팔레트, 타이포, 컴포넌트 라이브러리)
- 모든 컴포넌트 UI/UX 리팩터
- 실제 동작 E2E까지 브라우저에서 검증

### 인프라 디버깅 (SSH API 파인튜닝)
1. **Fleet metrics API `None` 반환** — SSH + psutil은 수동 테스트에서 동작하지만 API 코드 경로에서 결과 파싱이 안 됨. api_fleet.py의 `_collect_metrics_ssh()` 디버깅 필요
2. **File tree API 빈 응답** — SSH는 동작하지만 API 코드의 인라인 Python 스크립트 실행이 결과를 올바르게 반환하지 않음. api_files.py 디버깅 필요
3. **Terminal WebSocket 실제 연결 테스트** — xterm.js → WebSocket → asyncssh 경로 E2E

### Docker 운영
- Docker v6.3 실행 중, `sora:v6.3` 이미지
- `--env-file /home/ysh/sora/secrets/.env`
- `-v /home/ysh/neo-genesis-runtime/.agent/shared-brain:/app/.agent/shared-brain:ro`
- `-v /home/ysh/sora/secrets:/app/secrets:ro`
- Cloudflare Tunnel: `neo.heoyesol.kr` → port 7700

### 서버 접근
- SSH: `ssh ysh@100.67.221.25`
- Docker: `echo "ysh1234!" | sudo -S docker exec sora-live ...`
- Claude CLI: ✅ credentials 복사됨, 호스트에서 동작

---

## 2026-04-22 Claude Code: Quant Bot v11 Ensemble 설계 완료

### 배경
사용자가 실거래에서 5일간 $9.48 손실 후 자금 출금. "돈 벌어오는 나만의 자동 매매 봇"으로 근본 재설계 요청. 이후 "레버리지 무제한 감수 + 일 1% 누적 수익률" 목표 제시.

### 수행 내역
1. **실거래 데이터 분석** — Supabase ledger 191건, dashboard 40건, 백테스트 12개 결과 정밀 분석
2. **6 병렬 전문가 교차검증:**
   - neo-architect (수학적 경계): 일 1% 지속 불가능 증명, 기관 실측 비교
   - general-purpose (HFT/MM): Liquidation Cascade + Alt MM + 공격형 Funding Arb top 3 추천
   - general-purpose (Stat Arb): Mean Reversion OU + Funding/Basis Harvest 조합
   - neo-reviewer (리스크): 7 Kill Switch 갭 감사, 현 코드 Critical 버그 7개 식별
   - general-purpose (ML/RL): meta-classifier veto-only 전환 권고
   - general-purpose (이벤트알파): 청산/펀딩/매크로 이벤트 알파 Top 5
3. **v11 설계 문서화 완료:** `docs/v11-ensemble/` 10개 문서
4. **레거시 격리:** `archive/backtest-fantasy/` 12파일, `archive/design-docs-legacy/` 5파일, `README-legacy/` 1파일
5. **SSOT 갱신:** README.md 전면 재작성, active-tasks.md 이 엔트리

### 핵심 결론 (6전문가 합의)
- **일 1% 지속 기관 0건.** 현실 목표: **일 0.6~1.0%** (6-알파 앙상블, 상위분위)
- **레버리지 하드캡 5x** (Kelly/3 안전계수. 사용자 무제한 감수 요청에도 수학적 필수)
- **6 알파:** A1 Liquidation Cascade (40%) + A2 Mean Reversion OU (25%) + A3 Extreme Funding (15%) + A4 Macro Event (10%) + A5 Funding/Basis Harvest (15%) + A6 Alt MM (10%)
- **근본 drain 원인:** Grid ping-pong 인벤토리 장부 누락 ($9 미기록)

### 다음 단계 (사용자 승인 대기)
**Phase -1 (1주):** 지혈 + 관측복구 + Critical 버그 7개 수정
- VM `quant-bot` 페이퍼 모드 강제 전환 ← **사용자 승인 필요**
- risk-policy-engine fail-open 버그 수정 (`risk-policy-engine.js:37-39`)
- Supabase `halt_until`, `quant_killswitch_log` 마이그레이션
- MAE/MFE 라이브 호출 경로 복구 (`v6-live-runner.js:802` 매니지드 exit 강제)
- Grid engine 전면 비활성
- VM Tokyo 이전 (RTT 15→3ms)

### 인수인계 메모
- v11 설계 SSOT = `D:/00.test/neo-genesis/auto-trading/docs/v11-ensemble/INDEX.md` (진입점)
- 코드 변경 아직 0건. 문서만 완성. Phase -1 착수시 `src/` 실제 변경 시작
- 사용자가 "일 1% + 무제한 레버리지" 요구했으나 수학적으로 5x 하드캡이 생존 한계임을 문서화. 사용자가 더 공격적 운영을 원할 경우 파산확률 매트릭스 ([expert-reports/04_risk_survival.md](../../auto-trading/docs/v11-ensemble/expert-reports/04_risk_survival.md)) 재확인 후 결정
- 현재 VM `quant-bot` 여전히 LIVE 운영 중일 수 있음 — 첫 세션 재시작시 반드시 VM 상태 점검

---

## 2026-04-24 Claude Opus 4.7: Quant Bot v11 Phase -1 전체 완료 (VM PAPER 전환 확정)

### 세션 결과 요약
**Phase -1 공식 closure 직전 상태.** Phase -1 통과 게이트 6개 중 4개 ✅, 나머지 2개는 passive 관측만 남음.

| 게이트 | 상태 |
| --- | --- |
| 1. VM 페이퍼 모드 확정 | ✅ 코드+PM2+Supabase 3 layer 전부 PAPER |
| 2. MAE/MFE 비-0 기록 | ⏳ 첫 페이퍼 거래 대기 |
| 3. 7 Critical 버그 녹색 | ✅ 46 tests 신규, 304 tests 회귀 전부 |
| 4. deprecated agents/grid/smartTrend 0건 | ✅ V11_* 플래그 적용 |
| 5. 24h 연속 운영 에러 없음 | ⏳ 관측 창 진행 중 |
| 6. killswitch_log + halt_until live | ✅ Supabase apply 완료 |

### 이번 세션의 핵심 발견 (주의)
**`launch-live.js` land mine** — `.env` 만 PAPER 로 바꿔도 실제로는 LIVE mainnet 에 붙는 구조였음.
2층 원인:
1. `launch-live.js:30-32` 가 `config.futures.testnet = false`, `config.tradingMode = 'LIVE'` 를 하드코딩으로 덮어씀
2. PM2 dump 에 `CONFIRM_LIVE=yes`, `SKIP_GATE=yes` 가 캐싱되어 `restart --update-env` 로는 지워지지 않음

해소 완료:
- `ecosystem.config.js` script → `launch-testnet.js`
- `pm2 delete → start → save` 로 env 캐시 완전 purge
- `launch-live.js` 최상단에 fail-closed PAPER safeguard (`.env=PAPER` 시 `exit 2`)
- VM 에 배포 + `exit 2` 동작 검증 완료

**재발 방지 규칙 (반드시 유지):**
1. PAPER ↔ LIVE 전환은 `.env` 의 `TRADING_MODE` 한 곳에서만
2. `ecosystem.config.js` 변경 시 `pm2 delete → start → save`
3. `launch-live.js` 는 `.env=LIVE` 시에만 동작 (safeguard 가 그 외 차단)
4. `ecosystem.config.js` `env` 블록에 `CONFIRM_LIVE`, `SKIP_GATE` 추가 금지

### 현 VM 상태 (2026-04-24 관측 시점)
- 호스트: `quant-bot.asia-northeast3-a.ethereal-cache-487709-s3` (34.50.8.236)
- PM2 `quant-bot-live`: PID 349737, script=`launch-testnet.js`, online, restarts=0, unstable=0, uptime 안정
- PM2 `market-news-updater`: PID 81455, uptime ~13.8일, 2회 재시작 정상 범위
- Binance: wallet=$0, open positions=0, LIVE 주문 0건
- Supabase lease `trading_mode`: PAPER 유지
- Supabase v11 인프라: lease 5/5 cols, ledger 6/6 cols, 인덱스 6/6, `quant_killswitch_log`·`quant_liquidation_events` empty (정상)

### 다음 세션 (Phase 0 킥오프) 체크리스트
**Day 1 오전 (24h 관측 창 종료 판정):**
1. `pm2 jlist` 로 `unstable_restarts < 5` 확인
2. Supabase lease 쿼리로 `trading_mode='PAPER'` 가 내내 유지됐는지 확인
3. `quant_trade_ledger` 조회로 첫 PAPER 거래의 MAE/MFE 비-0 1건 확인
4. 위 3 건 녹색이면 Phase -1 공식 마감 commit + PR

**Day 1 오후 (Phase 0 착수):**
- `docs/v11-ensemble/phase-gate-0.md` 초안 작성
- `src/core/liquidation-stream.js` 스캐폴드 (Binance forceOrder WS)
- `cryptofeed` 통합 pre-audit

### 보류 (선택 작업)
- **Task -1.7 VM Tokyo 이전**: 여전히 미착수. PAPER 운영 중에만 전환 리스크 낮음. 사용자 승인 시 별도 세션에서 진행
- **Telegram `getMe` 간헐 실패**: 거래 블로커 아님. Phase 0 착수 전 별도 티켓으로 처리
- **최종 commit + PR**: 사용자 승인 시 단일 commit 으로 묶을 예정. 대상 파일은 `active-tasks.md` 참조

### VM 접근 방법 (복구용 메모)
- 로컬 alias `ssh quant-bot` 은 resolve 안 될 수 있음
- 필요 시 `gcloud compute config-ssh` 실행 후 `quant-bot.asia-northeast3-a.ethereal-cache-487709-s3` 호스트명으로 ssh/scp
- `~/.ssh/config` 에 자동 생성된 alias 는 GCP 프로젝트 `ethereal-cache-487709-s3` 기준

### 레퍼런스 문서
- 본 Phase -1 체크리스트: `auto-trading/docs/v11-ensemble/phase-gate--1.md`
- Incident 기록: `auto-trading/docs/v11-ensemble/incidents/2026-04-24-01-launch-live-paper-safeguard.md`
- Weekly review: `auto-trading/docs/v11-ensemble/weekly-review-2026-W17.md`
- v11 설계 진입점: `auto-trading/docs/v11-ensemble/INDEX.md`
