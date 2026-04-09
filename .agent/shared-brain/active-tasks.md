# Active Tasks — 에이전트 공유 작업 목록

> **규칙:** 작업 시작/완료 시 갱신. 담당 에이전트와 상태를 명시.  
> **최종 갱신:** 2026-04-09 by Claude (Sora Unified Bible v1 통합)

---

## 🟣 Sora Unified Bible 이행 — Tier S (즉시, 1주 내)

기반: `.agent/knowledge/SORA_UNIFIED_BIBLE.md` §13, `.agent/SORA_CONSTITUTION.md`

- [x] **Bible 작성 + 오너 주권 원칙 반영** — v1 완료 (2026-04-09, Claude)
  📍 `.agent/knowledge/SORA_UNIFIED_BIBLE.md`

- [x] **SORA_CONSTITUTION.md 분리** — 8개 Article, Owner Sovereignty Article 0 (2026-04-09, Claude)
  📍 `.agent/SORA_CONSTITUTION.md`

- [x] **permissions.yaml 스캐폴드** — deny는 자기보호 루프만, ask는 고지-확인 트리거 (2026-04-09, Claude)
  📍 `.agent/policies/permissions.yaml`

- [x] **blast_radius.yaml 스캐폴드** — tier 0-5 + 고지 템플릿 (2026-04-09, Claude)
  📍 `.agent/policies/blast_radius.yaml`

- [x] **capability_tokens.yaml 스캐폴드** — subagent별 base capability (2026-04-09, Claude)
  📍 `.agent/policies/capability_tokens.yaml`

- [x] **progress-ledger.md 스캐폴드** — Magentic-One 2-Ledger 패턴 (2026-04-09, Claude)
  📍 `.agent/shared-brain/progress-ledger.md`

- [x] **Pydantic contracts v1** — SideEffectBudget, DisclosureBundle, ToolCallEnvelope 등 (2026-04-09, Claude)
  📍 `src/core/contracts/sora_contracts.py`

- [x] **Hook pipeline 실제 구현** — SessionStart, UserPromptSubmit, PreToolUse, PostToolUse 4종 (2026-04-09, Claude)
  📍 `src/core/hooks/*.py` (5파일, 11/11 syntax OK)

- [x] **permissions.yaml 로더 + 평가기** — deny>ask>allow, owner_override, device_constraints (2026-04-09, Claude)
  📍 `src/core/governance/policy_engine.py`

- [x] **의도 분류기 (OwnerIntent 생성)** — 키워드 기반 + 엔티티 추출 (2026-04-09, Claude)
  📍 `src/core/nlu/intent_classifier.py`

- [x] **Uncertainty-triggered HITL** — confidence + device tier별 임계값 (2026-04-09, Claude)
  📍 `src/core/governance/hitl_gate.py`

- [x] **progress-ledger 자동 동기화** — PostToolUse → events.jsonl 이벤트 기록 (2026-04-09, Claude)
  📍 `src/core/hooks/post_tool_use.py`

## 🟣 Sora Dashboard v4 — Antigravity-Grade + CLI Code Agent

기반: `.agent/knowledge/SORA_DASHBOARD_V4_SPEC.md`
구현: Codex CLI + Claude CLI (소라가 이 둘을 subprocess로 소환)

### Phase 1: 스트리밍 기반
- [ ] `gemini_stream.py` + `ollama_stream.py` — 스트리밍 어댑터
- [ ] `chat_stream.py` — `/api/v2/chat/stream` SSE
- [ ] `sora_engine.py` — `process_stream()` 추가
- [ ] 프론트엔드 SSE 스트리밍

### Phase 2: Claude CLI + Codex CLI 코딩 에이전트
- [ ] `cli_code_agent.py` — subprocess + stdout 파싱 (Claude CLI `--print --output-format stream-json`)
- [ ] `code_execute.py` — `/api/v2/code/execute` SSE
- [ ] `model_router_v4.py` — intent→model/cli 라우팅
- [ ] `intent_classifier.py` — 코딩 서브 의도

### Phase 3: 프론트엔드 + 마무리
- [ ] `ThinkingBlock` + `ToolCard` + `DiffViewer` + `ModelBadge`
- [ ] `ApprovalDialog` — DisclosureBundle 대시보드 렌더링
- [ ] E2E 테스트

---

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
  📍 `neo-genesis/auto-trading/logs/error.log`, `neo-genesis/auto-trading/src/scripts/launch-live.js`, `neo-genesis/auto-trading/src/v6-live-runner.js`  
  👤 Codex / Claude Code

---

- [ ] **EthicaAI Melting Pot shard merge + final SSOT 정리**  
   📌 Mac Studio head run과 Linux server tail shard(`12-24`) 완료 후 JSON 병합, 통계 재계산, 최종 SSOT 파일 생성 필요  
   📁 `PAPER/EthicaAI/NeurIPS2026_final_submission/code/scripts/merge_meltingpot_results.py`, remote outputs on Mac Studio / YSH-Server  
   🤖 Codex

- [ ] **EthicaAI Melting Pot 최종 원고 반영**  
  📌 merged JSON 생성 후 `integrate_meltingpot_results.py` 산출물을 기준으로 본문 Melting Pot 문단과 appendix `clean_up` 행을 교체해야 함  
  📁 `PAPER/EthicaAI/NeurIPS2026_final_submission/code/scripts/integrate_meltingpot_results.py`, `PAPER/EthicaAI/NeurIPS2026_final_submission/paper/unified_paper.tex`  
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

## ✅ Recently Completed

- [x] GA4 shared-property reporting 기준 내재화 + 자동 보고 스크립트 일괄 정리 (`NeoGenesis - Production`, `hostName` 필터, Windows 콘솔 ASCII alert 출력) — 4/9, Codex
- [x] EthicaAI Melting Pot sharding support 추가 + Linux server tail shard launch + Mac overlap guard 설정 — 4/6, Codex
- [x] EthicaAI 모니터 false stall 판정 수정 + paper-update scaffold 구축 — 4/6, Codex
- [x] WhyLab Docker E5 appendix TODO 제거 + 실결과 반영/compile check — 4/6, Codex
- [x] PAPER monitor resilient fallback 추가 (`live/cached/unavailable`, SSH port probe, last-good cache) — 4/7, Codex
- [x] PAPER monitor root-cause isolation + repair assets 준비 (`tailscale ping`, `ssh_diag`, 포트 가변 credential parsing, `server_enable_monitoring_sshd.sh`) — 4/7, Codex

- [x] 퀀트봇 버그 4건 수정 (Ghost Position, -4045, Health, Supabase 키) — 4/5, Claude Code
- [x] Gemini LLM 트레이더 영구 삭제 — 4/5, Claude Code
- [x] 소라 God Mode Phase 1-3 완료 — 4/5, Claude Code
- [x] ComfyUI 이미지 생성 체인 구축 — 4/5, Claude Code
- [x] NEO_MASTER_RULES.md v1.0 작성 — 4/5, Claude Code
- [x] NeurIPS 자가 감사 — 4/5, Antigravity
- [x] Shared Brain 시스템 구축 — 4/6, Antigravity
- [ ] **퀀트봇 VM cutover + runtime lease 활성화**  
  - `auto-trading/src/scripts/setup-runtime-coordination.sql`를 Supabase에 적용하고 VM `.env`에 `RUNTIME_COORDINATION_REQUIRED=true` 설정 필요  
  - 이후 primary를 PC가 아니라 VM 하나로 고정하고 dashboard를 `quant_runtime_leases` 기준 heartbeat로 개편  
  - 경로: `neo-genesis/auto-trading/docs/RESILIENCE-v8.4-pc-down.md`, `neo-genesis/auto-trading/src/core/runtime-coordinator.js`  
  - 담당: Codex / Claude Code
---

## Codex Rollout Update (2026-04-06 22:25)

- Completed: `DESKTOP-SOL01`, `YSH-Server`, `MX Mac Studio`
- Applied:
  - shared runtime bundle copied to remote runtime path
  - home-level `CLAUDE.md`, `GEMINI.md`, `Codex AGENTS.md` pointers installed
- Pending: `DESKTOP-YESOL`, `S26 Ultra`, `Tab S10 Ultra`
- Blockers:
  - `DESKTOP-YESOL`: no `SSH`, `WinRM`, or `PC Agent`
  - `S26 Ultra`, `Tab S10 Ultra`: no remote shell / automation channel
- [x] **퀀트봇 VM baseline cutover 완료**
  - 전용 VM `quant-bot` 생성, Supabase runtime lease SQL 적용, 원격 배포/PM2/systemd 구성 완료
  - 현재 VM은 `asia-northeast3-a`, `e2-medium`, host maintenance `MIGRATE`, automatic restart 활성화 상태
  - 경로: `neo-genesis/auto-trading/docs/RESILIENCE-v8.4-pc-down.md`, `neo-genesis/auto-trading/src/core/runtime-coordinator.js`
  - 담당: Codex

- [x] **퀀트봇 Binance API 화이트리스트 반영 후 재기동 완료**
  - 신규 VM 공인 IP `34.50.8.236` 반영 후 원격 `quant-bot-live` 재기동 성공
  - 현재 PM2 `online`, runtime lease 획득, exchange init/Private WS/오케스트레이터 루프 시작 확인
  - 담당: 사용자 + Codex

- [ ] **퀀트봇 Telegram 채널 실패 원인 점검**
  - 원격 로그: `Telegram 봇 실행 실패: ... getMe failed`
  - 거래 코어는 동작하지만 원격 제어/알림 채널은 불안정할 수 있음
  - 담당: Codex

- [ ] **퀀트봇 grid margin insufficient 튜닝**
  - 원격 로그: `GRID-MGR ... -2019 Margin is insufficient`
  - 그리드 일부 주문이 자금 제약으로 거절되고 있어 배치 수량/레벨 재조정 필요
  - 담당: Codex / Claude Code

## Codex Rollout Update (2026-04-07 00:12)

- `DESKTOP-YESOL`: user-reported installed, OpenSSH enabled, host `100.71.28.36`, user `CTS_Sol`
- `DESKTOP-YESOL`: direct Codex login verification still pending because current SSH auth from this machine failed
- `S26 Ultra`, `Tab S10 Ultra`: remain in mobile operator mode, not remote shell targets
- Fleet rollout status:
  - `DESKTOP-SOL01`, `YSH-Server`, `MX Mac Studio`: verified installed
  - `DESKTOP-YESOL`: user-reported installed, auth verification pending
  - `S26 Ultra`, `Tab S10 Ultra`: network-online operator devices

## Codex Rollout Update (2026-04-07 00:22)

- `DESKTOP-YESOL`: direct Codex SSH verification completed
- Verified on host `100.71.28.36` as user `CTS_Sol`
- Verified files:
  - `C:\Users\CTS_Sol\.claude\CLAUDE.md`
  - `C:\Users\CTS_Sol\.gemini\GEMINI.md`
  - `C:\Users\CTS_Sol\.codex\AGENTS.md`
  - `C:\Users\CTS_Sol\neo-genesis-runtime\AGENTS.md`
  - `C:\Users\CTS_Sol\neo-genesis-runtime\infra\agent-runtime\LIVE_STATUS.md`
- Fleet rollout status:
  - `DESKTOP-SOL01`, `DESKTOP-YESOL`, `YSH-Server`, `MX Mac Studio`: verified installed
  - `S26 Ultra`, `Tab S10 Ultra`: network-online operator devices

## Codex Fleet Status Tracking (2026-04-07 11:15)

- [x] Added central device inventory and heartbeat ledger
  - `.agent/shared-brain/device_inventory.json`
  - `.agent/shared-brain/device_heartbeats.json`
- [x] Added rollout/status manager
  - `scripts/fleet_runtime_manager.py`
  - `infra/agent-runtime/runtime_heartbeat.py`
- [x] Updated Windows and Unix rollout installers to refresh runtime adapters and heartbeat support
- [x] Re-synced and verified `DESKTOP-SOL01`, `DESKTOP-YESOL`, `MX Mac Studio`
- [ ] Recover `YSH-Server` SSH path from this control node
  - current state: `ssh ysh@100.67.221.25` timeout
- [ ] Bring `Tab S10 Ultra` back online in Tailscale operator mode when needed

## Codex Remote Access Update (2026-04-08 12:05)

- [x] **`desktop-sol01` 관리자 SSH 키 마감 + 키 기반 접속 검증 완료**
  - `desktop-sol01`의 `C:\\ProgramData\\ssh\\administrators_authorized_keys`에 `desktop-yesol` 운영 키를 반영하고 `sshd` 재시작 완료
  - `desktop-yesol`에서 `ssh -i %USERPROFILE%\\.ssh\\id_ed25519_ysh -o IdentitiesOnly=yes yesol@desktop-sol01 hostname` 검증 성공
  - 현재 운영 표준은 `ssh desktop-sol01`
  - 담당: 사용자 + Codex

- [x] **`desktop-yesol` 운영 점프 호스트 기준 원격 접근 표준 고정**
  - `ysh-server`: `ssh ysh-server`
  - fallback: `tailscale ssh ysh@ysh-server`
  - `desktop-sol01`: `ssh desktop-sol01`
  - 운영 메모는 `.agent/shared-brain/handoff.md`에 반영 완료
  - 담당: 사용자 + Codex

- [x] **비모바일 4대 runtime 재수렴 완료**
  - `desktop-sol01`, `desktop-yesol`, `ysh-server`, `mx-macbuild-mac-studio` 모두 `verified_installed`
  - 현재 canonical runtime revision: `1c848a59e10557fb`
  - 담당: Codex

## Codex Experiment Follow-up (2026-04-07 12:04)

- [ ] **YSH-Server EthicaAI tail shard 재기동**
  - 원인확인 완료: `last reboot` 기준 `2026-04-07 11:00` 리붓이 `server_tail.log`의 `context canceled` 시각과 일치
  - 현재 상태: 서버에는 `meltingpot_final.py` 프로세스가 없고 tail shard는 부팅 후 자동 복구되지 않음
  - 재개 지점: `meltingpot_final_results_server_tail.json`의 기존 완료분을 유지한 채 shard resume 필요
  - 담당: Codex

- [ ] **YSH-Server Melting Pot 감시/복구 설계 보강**
  - 현재 `monitor_meltingpot_final.sh`는 재시작 스크립트가 아니라 종료 감시 + 텔레그램 알림만 수행
  - 현재 crontab에는 Melting Pot 재기동 엔트리가 없고, reboot 후 자동 복구 경로가 없음
  - 추가 이슈: 감시 스크립트가 `running`이 아니면 모두 `completed`로 알리므로 reboot/crash도 완료로 오탐 가능
  - 담당: Codex

## Codex Experiment Recovery (2026-04-07 12:28)

- [x] **YSH-Server EthicaAI tail shard 재기동**
  - `/home/ysh/neurips2026/EthicaAI/NeurIPS2026_final_submission/code/scripts/server_launch_meltingpot_tail.sh` 배포 완료
  - `meltingpot_tail.env` + `@reboot` crontab 등록 완료
  - 재기동 직후 상태: `completed_pairs=4/26`, `new_state=running`
  - 담당: Codex

- [x] **모니터 live 경로 복구**
  - `PAPER/monitor_experiments.py`에 `ProxyJump(CTS_Sol@100.71.28.36)` fallback 추가
  - 2026-04-07 12:28 KST 기준 `monitor_status=live`, `probe_pid=49863`, `cpu_tick_delta_5s=4741` 확인
  - 담당: Codex

- [ ] **YSH-Server Telegram 완료 알림 스크립트 정정**
  - 기존 `/home/ysh/neurips2026/monitor_meltingpot_final.sh`는 reboot/crash도 `completed`로 오탐 가능
  - 현재 auto-recovery는 해결됐지만 알림 문구/조건 보정은 별도 후속 작업
  - 담당: Codex

## Codex Quant Monitoring (2026-04-07 12:34)

- [x] **퀀트봇 모니터링 SSOT 복구**
  - `quant_dashboard.runtime` 컬럼 실적용 완료
  - VM `quant-bot` 재배포 후 `quant_dashboard.updated_at`와 `runtime.heartbeatAt`가 60초 주기로 갱신되는 것 확인
  - 담당: Codex

- [x] **공개 Quant 대시보드 런타임 표시 반영**
  - `portfolio/public/resume/projects/quant.html`이 JSON string/JSONB 혼합 응답과 `runtime` 필드를 모두 처리하도록 수정
  - `portfolio` commit `7f11448` push 완료
  - 담당: Codex
## Codex Quant Fee Edge (2026-04-07 17:20)

- [x] **퀀트봇 fee-adjusted execution policy 배포**
  - `src/core/trade-edge-policy.js` 추가, `config.js` 전략별 leverage cap / TP-SL / fee buffer 정책 반영, `v6-live-runner.js` 실주문 직전 skip + leverage override 연결
  - `quant-bot` VM에 최소 파일 배포 후 lease TTL 경과 뒤 `pm2 restart quant-bot-live --update-env`로 정상 기동 복구
  - 담당: Codex

- [ ] **퀀트봇 24~48h 수수료 효율 관측**
  - 새 정책 배포는 완료됐지만 아직 `edge ->` / `skip:` 실거래 로그 표본이 부족함
  - 다음 점검 때 `commission / realized pnl / net income` 기준으로 pre/post 비교 필요
  - 담당: Codex

## Codex Paper Claim Audit (2026-04-07 18:05)

- [x] **Claude 협업구조 기반 논문 점검**
  - `claude_collab.py --mode review`로 EthicaAI/WhyLab 원고 리스크를 재검토했고, EthicaAI Melting Pot overclaim이 현재 가장 큰 blocker라는 결론을 재확인했다.
  - `claude_collab.py --mode architecture`로 8.0+ 기준 실행 순서를 재검토했고, 결과 대기 전에는 claim calibration과 branch-ready rewrite를 먼저 끝내는 것이 최적이라는 결론을 반영했다.
  - 담당: Codex

- [x] **EthicaAI Melting Pot claim audit / branch rewrite 초안 준비**
  - `PAPER/EthicaAI/NeurIPS2026_final_submission/paper/MELTINGPOT_CLAIM_AUDIT.md`
  - `PAPER/EthicaAI/NeurIPS2026_final_submission/paper/MELTINGPOT_BRANCH_REWRITE.md`
  - 현재 `clean_up`은 merged result 전까지 `flagship positive result`가 아니라 `boundary-condition check`로만 취급한다.
  - 담당: Codex

- [x] **WhyLab 8.0+ framing note 준비**
  - `PAPER/WhyLab/paper/WHYLAB_8PLUS_NOTES.md`
  - E5 Docker 결과는 gain claim이 아니라 `transparent inactivity`와 `proxy calibration` 중심으로 해석하도록 고정했다.
  - 담당: Codex

- [ ] **EthicaAI merged result 반영**
  - Melting Pot head/tail 완료 후 `merge_meltingpot_results.py` 실행
  - `integrate_meltingpot_results.py` 결과로 본문/appendix/abstract/conclusion 문구를 동시 교체
  - 담당: Codex

- [x] **EthicaAI finalization 경로 준비**
  - `PAPER/EthicaAI/NeurIPS2026_final_submission/code/scripts/finalize_meltingpot_results.py` 추가
  - 현재 상태에서 `--allow-partial --sync-only`로 Mac `21`, server `13` 결과 스냅샷 fetch 성공
  - 기본 실행은 shard 미완료 시 `Melting Pot shards are not complete yet`로 안전 차단됨
  - 담당: Codex

- [x] **Stable acceptance plan 수립 + 선제 claim calibration**
  - `PAPER/STABLE_ACCEPTANCE_PLAN.md` 추가
  - EthicaAI `unified_paper.tex`의 Melting Pot overclaim을 mixed-safe wording으로 낮춤
  - WhyLab `main.tex`의 우선성/효과 과장을 보수적으로 조정
  - `pdflatex` 1회 빌드 기준 두 원고 모두 컴파일 성공
  - 담당: Codex

- [ ] **WhyLab 안정권 보강 실험/서술**
  - 현재 null-result framing만으로는 significance가 약하므로, 가능하면 unstable slice 추가 증거나 rebuttal-ready discussion 강화가 필요
  - 담당: Codex / Claude Code

## Codex Quant Runtime Review (2026-04-08 10:45)

- [x] **Capital tier + shadow telemetry hardening**
  - Runtime profile now carries shadow promotion candidates, tier transition state, and skip-audit telemetry for owner-facing monitoring.
  - Owner can inspect why signals were skipped and which shadow symbols are ready for manual promotion review.
  - Owner: Codex

- [x] **Claude re-review after implementation**
  - `claude_collab.py --mode review` and `--mode architecture` were re-run on the patched workspace.
  - Claude judged the prior blockers mostly resolved and converged on one next high-value step: wire SmartTrend trailing/partial TP into the real execution path.
  - Owner: Codex / Claude Code

- [x] **SmartTrend trailing / partial TP execution wiring**
  - Live path now uses exchange STOP protection plus bot-managed partial TP / trailing ratchet with tier-aware partial gating, remaining-amount sync, rollback handling, and emergency-close retry control.
  - Claude final reviewer result after hardening: `NO_NEW_SIGNAL`.
  - Owner: Codex

- [ ] **Managed-exit VM rollout decision**
  - Local code and tests are complete, but VM/live deployment has not been executed in this round.
  - Next owner decision: deploy the managed-exit hardening to `quant-bot` VM now, or hold for another data review window.
  - Owner: Codex / Owner

- [x] **Master orchestrator runtime hardening**
  - Fixed the undefined `balResp` branch, removed the bad `this.exchange` timeout-close reference, normalized recovered live-position metadata, and clamped orchestrator confidence to `0..100`.
  - Added `test/orchestrator-confidence.test.js`; Claude re-review result was `NO_NEW_SIGNAL`.
  - Owner: Codex

- [ ] **ExecutionPlanner real-path integration decision**
  - The orchestrator runtime is now stable, but `ExecutionPlanner` still remains a design-only module rather than the live execution path.
  - Next decision: keep the current direct `futuresExecutor` path, or promote `ExecutionPlanner` into the real signal-to-order pipeline as a separate structural refactor.
  - Owner: Codex / Owner

- [x] **Shadow promotion threshold hardening**
  - `capital-tier-router.js` default gate raised to `20 trades / 60% win rate / 3% pnlPct`
  - Promotion status now distinguishes `collecting_data`, `below_edge_threshold`, and `under_observation`
  - Backward-compatible aliases remain in place so runtime/dashboard consumers do not break immediately
  - Claude final re-review result on this patch: `NO_NEW_SIGNAL`
  - Owner: Codex / Claude Code

- [ ] **Quant latest local changes VM rollout decision**
  - Managed-exit hardening, orchestrator runtime fixes, and shadow promotion threshold tightening are all local-only right now
  - Next owner decision: deploy this combined patch set to `quant-bot` VM now, or hold for another local review window
  - Owner: Codex / Owner

- [x] **Quant dashboard telemetry exposure**
  - `scripts/update_quant_dashboard.js` now writes `skip_audit` and `shadow_candidates` into the static fallback JSON
  - `portfolio/public/resume/projects/quant.html` now renders `Skip Audit (24h)` and `Shadow Promotion Watch`
  - Claude architect chose this over immediate VM rollout as the next safest high-value step
  - Owner: Codex / Claude Code

- [ ] **Quant telemetry live-population rollout**
  - UI and mirror path are ready, but current runtime payload on the VM does not yet populate the new telemetry fields with live values
  - Next owner decision: roll out the latest quant runtime patch set to `quant-bot` VM, then observe 24-48h of skip/promotion data before larger structural changes
  - Owner: Codex / Owner

- [x] **Managed-exit VM rollout**
  - Latest runtime patch set was synced to `quant-bot` VM and `npm ci --omit=dev` completed successfully
  - First restart failed on a stale runtime lease; PM2 was stopped and the stuck `quant_runtime_leases` row was manually cleared after process-state verification
  - Second start succeeded; current instance `quant-bot:42859:25439af1` is online and publishing runtime telemetry
  - Owner: Codex

- [x] **Quant latest local changes VM rollout**
  - Managed-exit hardening, orchestrator fixes, shadow promotion thresholds, and telemetry-oriented runtime payload changes are now live on the VM
  - PM2 state was re-saved after rollout
  - Owner: Codex

- [x] **Quant telemetry live-population rollout**
  - `quant_runtime_leases` and `quant_dashboard.runtime` now contain live `skipAudit`, `runtimeProfile`, and shadow promotion threshold data
  - Static fallback JSON mirror was refreshed after the successful rollout
  - Owner: Codex

- [x] **Quant portfolio public telemetry deployment**
  - Staged only `public/quant/data.json`, `public/resume/projects/quant-data.json`, and `public/resume/projects/quant.html` in `D:\00.test\portfolio`
  - Committed as `1061dec feat: expose quant runtime telemetry`, pushed to `Yesol-Pilot/portfolio main`, then published `dist` with `npm run deploy`
  - Live verification passed: `https://heoyesol.kr/resume/projects/quant.html` now exposes `Skip Audit (24h)` and `Shadow Promotion Watch`
  - Owner: Codex

- [ ] **Quant 24-48h telemetry observation**
  - Rollout is complete, but current `skipAudit.total` and shadow candidate trade counts are still near zero because only the first live cycles have elapsed
  - Next step: observe 24-48h for real skip reasons, `collecting_data -> below_edge_threshold / under_observation` transitions, and any stale-lease recurrence on restart
  - Owner: Codex / Owner

## Codex Paper 8.5 Push (2026-04-08 10:58)

- [x] **WhyLab 8.5 route audit from existing results**
  - Added `PAPER/WhyLab/experiments/analyze_85_path.py`
  - Generated `PAPER/WhyLab/experiments/results/why85_path.json`
  - Generated `PAPER/WhyLab/paper/WHYLAB_85_EXECUTION.md`
  - Conclusion: fixed C2 is not 8.5-ready; the only remaining high-value path is a targeted real-task comparison on the E9 baseline-fail slice (`baseline vs fixed C2 vs adaptive C2`)
  - Owner: Codex

- [x] **EthicaAI residual paper blocker removal**
  - Updated `PAPER/EthicaAI/NeurIPS2026_final_submission/paper/unified_paper.tex` to replace stale `3 seeds` table wording with `pilot rerun` / `clean_up (pilot)`
  - Verified `pdflatex` build success and `python PAPER/monitor_experiments.py` now reports `Paper blockers: none`
  - Owner: Codex

- [x] **WhyLab selective adaptive real-task follow-up completed**
  - Added `PAPER/WhyLab/experiments/e9_swebench_selective.py` and `PAPER/WhyLab/experiments/launch_e9_selective_background.ps1`
  - Added runbooks / result notes:
    - `PAPER/WhyLab/paper/WHYLAB_85_SELECTIVE_RUNBOOK.md`
    - `PAPER/WhyLab/paper/WHYLAB_85_SELECTIVE_RESULT.md`
  - Ran the full top-cell selective follow-up on `E9 baseline-fail slice` (`T=0.7`, `max_attempts=3`, `n=92`)
  - Result: `adaptive C2` showed no net gain over `fixed C2` on pass / oscillation / regression; only mean rejection count decreased
  - Current implication: WhyLab `8.5` route is closed on the current model/policy; keep WhyLab on the stable-accept track unless a materially different setup is approved
  - Owner: Codex

- [x] **WhyLab manuscript recalibrated to match the selective follow-up**
  - Updated `PAPER/WhyLab/paper/main.tex` to state that adaptive C2 helps in `E7v2` but does not beat fixed C2 on the targeted SWE-bench slice
  - Added the selective-result caveat to the abstract, E7v2 discussion, cross-environment analysis, conclusion, limitations, and future-work sections
  - Reframed the paper-level message around `phase-aware deployment` / `selective intervention`, not universal gain
  - Hardened figure/table captions to make the same message readable without relying on body text
  - Added `PAPER/WhyLab/paper/WHYLAB_REBUTTAL_READY.md` for reviewer-facing defense points
  - Added `PAPER/WhyLab/paper/WHYLAB_REBUTTAL_DRAFT.md` with reviewer 1/2/3/4/5 expected comments and answer drafts
  - Verified with `pdflatex -interaction=nonstopmode -halt-on-error main.tex` five times
  - Final git state captured on branch `codex/whylab-final-state` at commit `88fa509`
  - Owner: Codex

- [ ] **WhyLab detailed remediation execution**
  - Fresh Codex + Claude Opus review consensus says the remaining blockers are significance framing, adaptive-C2 demotion, deployment-rule operationalization, theory-practice quantification, and baseline/robustness evidence surfacing
  - Detailed plan captured in `PAPER/WhyLab/paper/WHYLAB_DETAILED_REMEDIATION_PLAN.md`
  - Immediate no-new-experiment path:
    - patch abstract / intro / E7v2 / E5 / cross-env / conclusion / limitations to remove residual overclaim
    - add an experiment map table and a deployment checklist subsection
    - surface `E10` simple baselines and permutation E-value evidence in the main text
  - Low-cost analysis path:
    - quantify `(A1)` violation rate from E6 traces
    - pull a concise Docker per-tier calibration summary
    - improve figure readability where the caption currently carries more signal than the plot
  - Owner: Codex

- [x] **Quant market/news-aware control-plane P0**
  - Added `src/core/market-context.js` and `src/core/event-risk-gate.js`
  - Orchestrator confidence now consumes soft market/news caution modifiers, while `v6-live-runner.js` applies hard event/news shock entry blocks and size/confidence reductions right before execution
  - Shadow execution now also respects the same hard block logic so promotion stats stay aligned with live gating
  - Local validation passed with `27 suites / 232 tests`; Claude re-review returned `NO_NEW_SIGNAL`
  - Owner: Codex / Claude Code

- [ ] **Quant market/news gate VM rollout decision**
  - The market/news-aware gate is local-only right now; the VM runtime still runs the previous live patch set
  - Next owner decision: deploy this control-plane patch to `quant-bot` VM and observe 24-48h of `marketContext` / `event_risk` skips before tuning thresholds further
  - Owner: Codex / Owner

- [ ] **WhyLab 8.0 feasibility gate**
  - `Claude Opus` plus Codex consensus: `8.0` is not feasible with the current evidence bundle
  - Current governing note is `PAPER/WhyLab/paper/WHYLAB_80_FEASIBILITY_PLAN.md`
  - Decision rule:
    - default path = `stable accept` via manuscript/analysis hardening
    - `8.0` path only reopens if one new real-task experiment produces a statistically defensible positive gain
  - Explicit no-go:
    - do not treat same-family adaptive reruns, more E5 Docker expansion, or writing polish alone as an `8.0` route
  - Owner: Codex

- [ ] **WhyLab 8.0 conditional action-plan execution**
  - Owner requested an explicit `8.0-targeted` roadmap rather than only a feasibility verdict
  - Governing docs:
    - `PAPER/WhyLab/paper/WHYLAB_80_FEASIBILITY_PLAN.md`
    - `PAPER/WhyLab/paper/WHYLAB_80_ACTION_PLAN.md`
  - Execution rule:
    - Phase 0 = manuscript hardening
    - Phase 1 = low-cost analyses from existing assets
    - Phase 2 = exactly one decisive real-task experiment only if the route is materially different from the exhausted adaptive path
  - Stop/go rule:
    - if Phase 2 does not yield a statistically defensible real-task gain, the 8.0 route closes and the paper returns to the stable-accept track
  - Owner: Codex

- [ ] **WhyLab 8.0 action-plan Phase 1 analyses**
  - Phase 0 manuscript hardening is complete in `PAPER/WhyLab/paper/main.tex`
  - Added:
    - deployment checklist subsection
    - experiment map table
    - E10 simple-baseline comparison table
  - Reframed:
    - `E7v2` significance as pairwise-positive / 3-way-underpowered
    - `adaptive C2` as scoped calibration
    - `E5` as stable-regime calibration sanity check
  - Next step is Phase 1:
    - quantify `(A1)` violation rate from E6 traces
    - summarize Docker per-tier calibration
    - clean up any figure/readability issues that remain after the manuscript patch
  - Owner: Codex

- [ ] **WhyLab 8.0 reopen follow-up: Gemini 2.5 Flash Docker confirmatory run**
  - Direct Claude reviewer pass confirmed that 8.0 cannot reopen without a new Docker-ground-truth positive result on a materially different setup.
  - Locked protocol:
    - `PAPER/WhyLab/paper/WHYLAB_80_REOPEN_PROTOCOL.md`
    - materially different setup = `gemini-2.5-flash` + Docker ground-truth + existing 67-problem prefilter + `baseline` vs `whylab_c2`
  - Infra validation:
    - `/home/ysh/whylab_docker_g25_smoke` completed one `baseline` and one `whylab_c2` episode successfully under Docker
    - `whylab_c2` recorded real audit rejections, so the code path is live
  - Active full run:
    - host: `YSH-Server`
    - workdir: `/home/ysh/whylab_docker_g25_full`
    - launch time: `2026-04-08 16:19:29 KST`
    - scope: `67 problems x 3 seeds x 2 conditions = 402 episodes`
  - Stop/go rule:
    - if this run is null or ambiguous, close the 8.0 route and return WhyLab to the stable-accept track
    - if this run is positive and defensible, rerun cold Claude review before touching the paper narrative
  - Owner: Codex

- [x] **Quant market/news gate VM rollout**
  - The live `quant-bot` VM now runs the market/news-aware control-plane patch set.
  - Rolled files:
    - `src/config.js`
    - `src/orchestrator.js`
    - `src/v6-live-runner.js`
    - `src/core/market-context.js`
    - `src/core/event-risk-gate.js`
  - Validation:
    - remote `node --check` passed on all touched runtime files
    - `pm2 restart quant-bot-live --update-env` recovered successfully after one stale-lease retry
    - current live instance recovered as `quant-bot:44219:a2f6676b`
    - live logs confirm `Lease acquired`, `small-account safe mode`, `capital tier=micro`, and 60-second loop start
  - Owner: Codex

- [ ] **Quant market/news telemetry observation window**
  - The structural rollout is complete; the next step is to observe real live behavior for `24-48h`
  - Watch items:
    - actual `marketContext` / `event_risk` skip accumulation
    - whether the live news snapshot meaningfully changes gating versus the previous neutral fallback
    - recurring stale-lease churn during PM2 restarts
    - intermittent Telegram `getMe` failure during startup
    - partial upstream feed failure (`bls_cpi fetch failed`) on the VM
  - Tuning should happen only after live skip data accumulates
  - Owner: Codex

- [ ] **Quant live news updater hardening**
  - `market-news-updater` is now online under PM2 and persisted with `pm2 save`
  - Current live path:
    - `fed_press` and `coindesk` succeeded
    - `bls_cpi` failed on the VM during the first live run
  - Next step:
    - determine whether `bls_cpi` is a transient TLS/network issue or a persistent source incompatibility on the VM
    - if persistent, either adjust the fetch path or demote/remove that source from the default live set
  - Owner: Codex
