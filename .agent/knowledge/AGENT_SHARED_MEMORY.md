# 에이전트 공유 메모리 (Shared Agent Memory)

> **목적:** Sora, Claude Code, Antigravity, Codex가 공통으로 참고하는 장기 지식 저장소
> **갱신 규칙:** 중요한 사실, 안정된 운영 지식, 반복 교훈만 기록
> **최종 갱신:** 2026-04-14
> **주의:** 규칙 SSOT는 `NEO_MASTER_RULES.md`, 현재 상태 SSOT는 `shared-brain/`이다. 이 파일은 장기 메모리다.

---

## 1. 에이전트 협업 구조

```
SSOT: D:/00.test/neo-genesis/.agent/
├── NEO_MASTER_RULES.md         ← 공통 규칙 SSOT
├── BIBLE.md                    ← 운영 레퍼런스/인덱스
│
├── (generated adapters)
│   ├── ../AGENTS.md            ← Codex 런타임 진입점
│   ├── ../CLAUDE.md            ← Claude Code 런타임 진입점
│   ├── ../GEMINI.md            ← Gemini CLI 런타임 진입점
│   └── ../infra/agent-runtime/ ← Ollama/상태 요약/설치 가이드
│
├── shared-brain/               ← 현재 상태 동기화
│   ├── status.json             ← 에이전트 실시간 상태
│   ├── daily-log.md            ← 일별 변경 기록
│   ├── active-tasks.md         ← 공유 작업 목록
│   └── handoff.md              ← 세션 전환/토큰 소진 인수인계
│
├── knowledge/
│   ├── OWNER_PROFILE.md        ← 대표님 프로필
│   ├── AGENT_SHARED_MEMORY.md  ← 이 파일 (장기 교훈/사실)
│   └── (기존 연구 보고서들)

접근 방식:
  소라         → ChromaDB RAG 검색 (rag_search 도구)
  Claude Code  → 루트 `CLAUDE.md` import + shared-brain 직접 읽기
  안티그래비티 → 파일 직접 읽기 (세션 시작 시 shared-brain/ 자동 참조)
  Codex        → 루트 `AGENTS.md` + SSOT + shared-brain 우선
  Gemini CLI   → 루트 `GEMINI.md` import + shared-brain 직접 읽기
  Ollama       → generated `infra/agent-runtime/ollama/Modelfile`
```

---

## 2. 운영 사실 스냅샷 (2026-04-06)

### 소라
- Phase 1~4 완료 배포
- 폴백: Gemini 3.1 → Gemini 2.5 → Ollama qwen2.5-coder:14b
- 외부 연동: Google Calendar ✅, Gmail ✅ (API 승인됨), Notion ❌ (불필요)
- 모델 표시: 모든 응답 끝에 `_(model-name)_` 자동 표시
- 감사 로그: `/api/v2/audit`
- 권장 운영 구조: `YSH-Server 메인 + home-pc GPU 워커 + Vercel UI + Cloudflare Tunnel + GCP 보조/복구`
- `YSH-Server`는 2026-04-07 기준 `16코어 / 16GiB`로 재실측됐고, 현재도 `소라 코어 전용 1차 노드`로 유지한다.
- `MX Mac Studio`는 `상시 실행 노드`가 아니라 `Apple 빌드 / 격리 연구 / 필요 시 보조 Ollama` 용도의 on-demand 노드로 둔다.
- GCP는 완전 미사용이 아니라 `소라 메인 미사용 + 보조/잔존 리소스 존재` 상태

### Claude Code
- 실제 최근 버전 기록은 `shared-brain/status.json`을 기준으로 본다.
- 버전 관련 규칙은 `CLAUDE.md`와 실제 실행 상태가 어긋날 수 있으므로 실행 전 재확인한다.

### Codex
- 운영 문서 정비와 로컬 규칙 검증에 투입 가능하다.
- SSOT, BIBLE, shared-brain 간 불일치가 있으면 함께 수정한다.
- Telegram ops notifier 표준: `src/core/ops_telegram_alerts.py`, `scripts/telegram_ops_notify.py`, `scripts/run_with_telegram.py`
- 장기 실험과 외부 agent 권한 요청 결과는 Telegram으로 남기는 것을 운영 기본값으로 사용

### 운영 이슈 (미해결)
| 이슈 | 위치 | 우선순위 |
|------|------|---------|
| whylab CI/CD 56회 실패 | src/sbu/whylab | 🔴 |
| Gmail token Calendar scope만 보유 | gcal_token.json | 🟡 (재인증 완료됨) |

---

## 3. 에이전트별 교훈 & 피드백

### 소라 (Sora)
- 서버 상태 파악: 메모리/기록 맹신 금지 → SSH 직접 확인 필수
- `sora_context.json`의 connected_devices = SSH 체크 대상 목록
- 배포 현황은 실시간 `docker ps` 확인이 사실

### Claude Code
- Claude Code 버전 정책은 `CLAUDE.md`를 보되, 실제 실행 버전은 `shared-brain/status.json`으로 재검증
- PowerShell에서 `&&` 금지 → `;` 사용
- 코드 수정 전 사이드이펙트 표 작성 의무 (CLAUDE.md 규칙)
- 소라 작업 전 항상 서버 상태 먼저 확인

### 안티그래비티 (Gemini)
- `NEO_MASTER_RULES.md`가 SSOT, `BIBLE.md`는 운영 참고서
- `.agent/knowledge/`의 연구 보고서 인덱싱 완료

### Codex
- 로컬 규칙 파일과 프로젝트 문서를 먼저 읽고 작업
- 문서 정비 시 SSOT 우선순위와 shared-brain 현재성을 함께 맞춘다
- 기본 운영 모드는 자율 실행이며, 복구 가능한 로컬 작업은 선실행 후보고를 원칙으로 한다
- 권한 상승, 배포, 삭제, 외부 공유는 승인 게이트를 유지한다
- Claude/Gemini 공통 규칙에서 흡수한 `Doc-First`, `사이드이펙트 표`, `안전 > 효율`, `최소 권한`을 SSOT 절차로 내재화 완료
- 역할별 최적화/공통 공유층은 `AGENT_RUNTIME_OPTIMIZATION.md`를 기준으로 본다

### 방문자 통계 보고 공통 규칙 (2026-04-14)
- 방문자 통계 보고는 앞으로 `숫자 나열`이 아니라 `DA + 20년차 PM 의사결정 보고`로 작성한다.
- 최소 구조는 `Executive Summary -> Business Signal -> Intent Analysis -> Quality Diagnosis -> Measurement Integrity -> Action Queue`다.
- 핵심 분석 순서는 `획득 -> 의도 -> 참여 -> 전환 대체지표 -> 재방문 -> 콘텐츠 운영 -> 계측 신뢰도`다.
- 상위 페이지는 URL 그대로 나열하지 말고 `가격 탐색형`, `대안 비교형`, `구매 검토형`, `정보 탐색형`, `문제 해결형` 같은 의도군으로 묶어 해석한다.
- `GA4`, `PostHog`, `Search Console`, 내부 로그가 충돌하면 성과 해석보다 먼저 `Measurement Integrity`를 경고로 보고한다.
- 방문자 통계의 최종 산출물은 항상 `이번 주에 무엇을 더 만들지`, `무엇을 멈출지`, `무슨 실험을 할지`까지 포함한다.
- 상세 절차 문서는 `20260414_PM_DA_방문자_통계_보고_워크플로우.md`다.

### 재방문 사용자 중심 성장 전략 (2026-04-14)
- Neo Genesis가 직접 수익화보다 `트래픽 축적 -> 사용자화 -> 재방문 형성`을 우선하는 단계에서는 North Star를 `Returning Users`로 둔다.
- 최상위 지표는 `7일 Returning Users`, `28일 Returning Users`, `Returning User Rate`다.
- 총 방문자 수와 페이지뷰는 참고지표이고, 의사결정의 중심은 `재방문`, `2페이지 이동`, `세션당 페이지수`, `허브 재진입`이다.
- 신규 콘텐츠는 단발성 글로 끝내지 말고 `관련 글 2개 + 허브 1개 + 다음 읽을 글 1개`를 기본 구조로 둔다.
- ToolPick는 `alternatives`, `comparisons`, `pricing`, `reviews`, `calculator`를 재방문 실험의 1차 허브로 본다.
- 상세 전략 문서는 `20260414_재방문_사용자_중심_성장전략_v1.md`다.

### 설계 명령 멀티에이전트 처리 규칙 (2026-04-14)
- 사용자의 `설계`, `기획`, `전략`, `로드맵`, `방안 수립`, `내재화` 성격 명령은 모두 멀티에이전트 협업 과제로 취급한다.
- 모든 설계 명령은 `의도 해석 -> 페르소나 추출 -> 태스크 보드 -> 협업 실행 -> 검증/QA -> 최종 보고` 순서로 처리한다.
- 필요한 페르소나는 요청 성격에 맞춰 `PM`, `DA`, `Architect`, `Developer`, `Designer`, `QA`, `Ops`, `Research`, `Legal/Policy` 중에서 배정한다.
- 태스크는 반드시 `담당`, `선행조건`, `산출물`, `완료 기준`, `검증 방식`을 포함한다.
- 태스크 없는 설계안, QA 없는 완료 선언, 증거 없는 완료 보고는 허용하지 않는다.
- 상세 프로토콜 문서는 `20260414_멀티에이전트_설계_실행_프로토콜_v1.md`다.

---

### AI Agent Environment Optimization Rule (2026-04-24)

- 모든 프로젝트의 에이전트 환경 최적화 기준은 `.agent/knowledge/20260424_AI_AGENT_ENVIRONMENT_OPTIMIZATION_BLUEPRINT.md`를 참조한다.
- 기본 원칙은 `owner control + auditable execution + reproducible quality`다. 무제한 자율 실행을 목표로 하지 않는다.
- 표준 레이어는 runtime, tool plane, agent plane, UX plane, memory, evaluation, security, governance로 분리한다.
- 기본 패턴은 LangGraph식 state graph, MCP tool gateway, A2A/handoff, AG-UI control plane, OpenTelemetry trace, sandbox, eval harness다.
- 작업 전 goal, scope, side effect, authority, official source를 확인하고, 작업 후 tests, logs, diff, source attribution, residual risk를 남긴다.
- 심층 v2 레지스트리는 `.agent/knowledge/agent-environment/`이며, 기본 stack은 `LangGraph + Pydantic AI + Mastra`, 보조 stack은 `OpenAI Agents SDK`, enterprise workflow는 `Microsoft Agent Framework`다.
- 공개 benchmark 점수보다 `D:/00.test` 로컬 golden task, BFCL식 tool-call test, AgentDojo/MCP security case를 우선한다.

---

## 4. 통합 지식 동기화 절차

### 새로운 중요 사실 발견 시
```
1. 에이전트가 사실 발견/확인
2. 현재 상태면 `shared-brain/`, 장기 지식이면 이 파일 업데이트
3. 소라: 필요 시 ChromaDB 재인덱싱
4. Claude Code / Antigravity / Codex: 다음 세션 또는 현재 세션에서 반영
```

### 주요 결정사항 추가 시
- `OWNER_PROFILE.md`의 "핵심 결정사항" 표에 추가
- 날짜 필수 기재

### 런타임 어댑터 갱신 시
1. `.agent/NEO_MASTER_RULES.md`, `BIBLE.md`, `AGENT_SHARED_MEMORY.md`, `shared-brain/*` 중 원본을 먼저 수정
2. `python scripts/sync_agent_context.py` 실행
3. 필요 시 각 디바이스에서 `python scripts/sync_agent_context.py --install-home` 실행
4. Ollama는 `ollama create neo-genesis-shared -f infra/agent-runtime/ollama/Modelfile`로 재빌드

---

### Master Credential Access Standard (2026-05-03)

owner 지시: "마스터크레덴셜은 모든 디바이스에서 모든 에이전트들이 기본적으로 접근하고 활용해야 해"

- 표준 SSOT: `.agent/knowledge/MASTER_CREDENTIAL_ACCESS_STANDARD.md`
- 마스터 단일 소스: `desktop-sol01: D:/00.test/neo-genesis/.env.local + .env` (둘의 합집합, .env.local 우선)
- 디바이스 로컬 캐시: `~/.neo-genesis/credentials.env` (mode 600, sync 시 자동 생성)
- 모든 에이전트 표준 lookup:
  - **Python**: `from infra.agent_runtime.credential_loader import load_credentials; load_credentials()`
  - **Bash / cron / hook**: `source infra/agent-runtime/credential_loader.sh`
  - **Verbose 진단**: `python infra/agent-runtime/credential_loader.py` 또는 `NEO_CRED_VERBOSE=1 source infra/agent-runtime/credential_loader.sh`
- Fleet 동기화: `python scripts/sync_credentials_to_fleet.py [--target <device>] [--dry-run]`
- Override 정책: 부모 shell 의 set + non-empty 변수는 유지 (cron/CI 안전), 빈 변수는 override
- 보안 guardrails: chat / log / git commit / 공개 dashboard 출력 금지 / 토큰 redaction (len + first 8 chars only) / audit log 의무
- 첫 fleet 동기화 (2026-05-03):
  - `ysh-server`: 43 keys synced + chmod 600 ✅
  - `desktop-yesol`, `mx-macbuild-mac-studio`: offline → 다음 online 시 자동 재시도

---

## 5. 에이전트 간 역할 분담

> 2026-04-24 갱신: 오너 주력 에이전트가 Codex → **Claude Code**로 전환. Codex는 fallback(토큰 소진/장기 background/shell economical) 경로로 유지.

| 역할 | 주력 | 보조/대체 | 비고 |
|------|---|---|------|
| 텔레그램 실시간 명령 실행 | 소라 | - | 24/7 |
| 코드 작성/리뷰/배포 | **Claude Code** | Codex (fallback) | 오너 대화형 주력 |
| 딥 리서치/전략 분석 | 안티그래비티 | Claude Code (수렴) | 요청 시 |
| 공통 지식 관리 (SSOT/메모리) | **Claude Code** | Codex (fallback) | 오너 주력 |
| 서버 인프라 모니터링 | 소라 | - | 자동 |
| 장시간 autonomous background | Codex | Claude Code (감독) | Claude 토큰 보존 |

---

## 6. 변경 이력

| 날짜 | 에이전트 | 변경 내용 |
|------|---------|---------|
| 2026-04-05 | Claude Code | 초기 파일 생성. 소라 God Mode Phase 1~4 완료 기록 |
| 2026-04-06 | Codex | SSOT 기준으로 역할 재정의, BIBLE/Shared Brain과의 계층 관계 정리 |
| 2026-04-06 | Codex | Codex 자율 실행 정책 및 승인 경계 등록 |
| 2026-04-06 | Codex | Claude/Gemini 공통 설계 원칙을 SSOT에 반영: Doc-First, 사이드이펙트 표, 안전 우선, 최소 권한 |
| 2026-04-06 | Codex | 소라 운영 아키텍처 v1 추가. YSH-Server 중심 운영, GCP 보조/복구 전용으로 정리 |
| 2026-04-06 | Codex | 통합 에이전트 런타임 어댑터 추가: 루트 AGENTS/CLAUDE/GEMINI + Ollama Modelfile + 동기화 스크립트 |
| 2026-04-06 | Codex | 소라 플릿 상세설계 v1 추가. Ollama는 `DESKTOP-SOL01`, `S26 Ultra`는 1차 승인 장치, `S10 Ultra`는 2차 대시보드/명령 장치로 고정 |
| 2026-04-06 | Codex | 소라 제어면 인증 강화 v1 적용. URL/localStorage 장기 토큰 제거, 세션 기반 인증 + 짧은 수명의 action token + 내부 서비스 시크릿 구조로 정리 |
| 2026-04-14 | Codex | 방문자 통계 보고를 `DA + 20년차 PM` 의사결정 워크플로우로 내재화. SSOT/BIBLE/장기 메모리/어댑터 기준 업데이트 |
| 2026-04-24 | Claude Code | 오너 주력 에이전트 전환(Codex → Claude). Codex는 토큰 소진/장기 background/shell economical fallback로 유지. Collaboration Contract · CLAUDE_COLLABORATION · AGENT_RUNTIME_OPTIMIZATION 갱신 |
| 2026-04-24 | Claude Code | Agent/UX 심층 리서치 수렴: research-patterns-v2에 LATS·Plan-and-Act·GoalAct·Mem0·A-Mem·Magentic dual-ledger 추가, ux-pattern-library-v2에 OSS 라이브러리 픽과 4개 UX 원칙 추가, threat-model-v2에 적응 공격(Attacker Moves Second) 섹션 추가, framework-scorecard에 Temporal+OpenAI SDK 통합 추가 |
## 2026-04-06 Codex: Sora 품질 루프 / 자동 보고 게이트
- `src/core/time_context.py`를 추가해 상대 날짜 요청에 절대 날짜 기준을 주입한다.
- `sora_engine`, `agent_router`, `prompt_builder`가 시간 기준을 함께 보게 조정했다.
- `chat_review_loop`가 최근 24시간 채팅에서 상대 날짜 혼동이 섞인 불만 재진입을 잡아내고 `절대 날짜 우선` 개선안을 제안한다.
- `report_gate`는 `reply_markup`을 유지할 수 있으며, `neo_scheduler`, `proactive_agent`, `sora_notify`, `mission_controller_v2`의 자동 보고를 먼저 심사한다.
- 24시간 실로그 재검토 결과: 품질 점수 `64`, 오류형 응답 `2`, 불만 재진입 `4`.
## 2026-04-26 Codex: SBU Autonomous Growth Standing Approval

- Owner instruction: "모두 자율주행되도록 규칙 변경 하고 진행해".
- Canonical rule: `.agent/knowledge/20260426_SBU_AUTONOMOUS_GROWTH_RULE.md`.
- SBU growth operations are autonomous by default: content, SEO, analytics, sitemap/llms, GitHub, Vercel, indexing, revalidation, cron, publishing pipeline repair, and live smoke verification.
- Standing approval now includes SBU-scoped Vercel environment-variable updates and broken automation credential rotation when the credential source is owner-controlled and target scope is limited to the intended SBU or `Yesol-Pilot`.
- Secret handling remains strict: never print, log, commit, or paste secret values. Report only sanitized status.
- File-based SBU blogs require MDX commit/push, Vercel production deploy, live blog listing, detail 200, expected title/date, and sitemap inclusion. DB-only publish is not success.

### C Drive Management Preference (2026-05-10)

- Owner preference: C drive cleanup should not default to deletion. Prefer moving/re-homing valuable large artifacts to D drive, then verify the tool still works.
- Agents are the main source of installs and generated artifacts, so future agent work must avoid creating large state on C whenever practical.
- Canonical rule: `.agent/knowledge/20260510_C_DRIVE_MANAGEMENT_POLICY.md`.
- Applied migration record: `.agent/knowledge/20260510_C_DRIVE_MIGRATION_RECORD.md`.
- Current desktop-home state after cleanup: C free space is about `450.4 GiB`, up from about `112.1 GiB`.
- Default D targets: `D:\00.test\` for repos/SSOT, `D:\002.models-ai\` for model stores, `D:\003.agent-runtime\` for package/tool caches and runtime state, `D:\004.local-dev\` for local tools/experiments, `D:\005.output\` for temp/exports, `D:\006.virtualization\` for future platform migrations, and existing live `D:\wsl\` / `D:\docker\` roots until supported migration.
- Cleanup classification must be `MOVE`, `CACHE-REBUILD`, `KEEP`, or `DELETE`; `MOVE` wins over `DELETE` unless the target is disposable cache or a confirmed duplicate.
- Important compatibility junctions now exist from old C paths to D: Ollama models, HuggingFace cache, npm cache, Playwright, Puppeteer, Docker WSL data, Gemini state, and Miniconda. Do not replace these junctions with real C directories.
- `Ubuntu-24.04` WSL now lives under `D:\wsl\Ubuntu-24.04`; Downloads were archived under `D:\output\downloads-archive\20260510`.
- Remaining C-side work: pagefile shrink requires elevated Windows settings and reboot; `C:\Users\yesol\miniconda3._old_20260510` is registered for RunOnce cleanup after next login if locked files remain.

### D Drive Root Directory Preference (2026-05-10)

- Owner preference: D drive root should stay clean and categorized, not become a dumping ground after C drive migration.
- Canonical rule: `.agent/knowledge/20260510_D_DRIVE_ROOT_POLICY.md`.
- New agent-created root-level folders under `D:\` are prohibited unless the policy is updated.
- Default destinations now use D root 001-category folders where available: `D:\001.workspace`, `D:\002.models-ai`, `D:\003.agent-runtime`, `D:\004.local-dev`, `D:\005.output`, `D:\006.virtualization`, `D:\007.apps-managed`, and `D:\009.archive`.
- Compatibility aliases currently exist as hidden junctions: `D:\models`, `D:\ComfyUI_models`, `D:\agent-cache`, `D:\automations`, `D:\local-dev`, `D:\output`, `D:\tmp`, `D:\mods`, `D:\steam`, `D:\agent-runtime`, and `D:\agent-state`.
- Applied root cleanup: moved `.playwright-cli`, `app`, `google_calendar_tool`, `AntiGravity`, a loose root `.txt`, and `llama.cpp` into archive/local-dev locations.
- Do not casually move app-managed roots: `D:\KakaoTalk`, `D:\Telegram Desktop`, `D:\Creative App`, `D:\Launcher`, or `D:\.claude`. `D:\steam` and `D:\mods` are now compatibility junctions to `D:\007.apps-managed`.
- `D:\agenttest` was classified as `Yesol-Pilot/game-pipeline` and copied/verified to `D:\00.test\006.games-labs\game-pipeline`. The old `D:\agenttest` root is empty but locked; HKCU RunOnce `RemoveEmptyAgenttest20260511` will remove it only if still empty at next login.
- `D:\.claude` and the empty locked `D:\agenttest` residual root are hidden for root readability; neither was moved.

### D00.test Subdirectory Reorganization Preference (2026-05-11)

- Owner preference: `D:\00.test` and its subdirectories should not stay as a flat mixed list of active projects, duplicates, similar split projects, temp output, and uncontrolled backups.
- Canonical rule: `.agent/knowledge/20260510_D00TEST_DIRECTORY_REORGANIZATION_POLICY.md`.
- Target taxonomy uses numbered buckets: `001.ssot-agent-runtime`, `002.products-sbu`, `003.portfolio-career`, `004.research-paper`, `005.client-work`, `006.games-labs`, `007.infra-tools`, `008.mirrors-external`, `009.archive`, `010.tmp-output`.
- Owner explicitly prefers `001~` three-digit numbering for D drive and nested workspace organization. Do not create new `00/10/20` bucket names.
- Default-visible `D:\00.test` directories are now only `001~010`. Use `Get-ChildItem -Force` to see hidden compatibility aliases and no-touch roots.
- Hidden junction aliases now include `D:\00.test\.claude`, `.codex_tmp`, `jobsearch`, `sora-app`, `sora-android`, and `neo-genesis__sbu_autogrowth`.
- Hidden real compatibility roots still physically at old paths: `neo-genesis`, `project_yesol`, and `PAPER`. Move them only after locks/config references are cleared.
- `portfolio` moved on 2026-05-12 to `D:\00.test\003.portfolio-career\006.portfolio`; the old `D:\00.test\portfolio` path is a hidden junction alias.
- A stray root `docs` folder created on 2026-05-12 was moved to `D:\00.test\010.tmp-output\006.root-docs-reports`; `D:\00.test\docs` is a hidden junction alias. New reports should live under the owning project or a numbered output bucket.
- First visible children inside numbered buckets are now numbered too. Old child names remain hidden junction aliases, including `003.portfolio-career\jobsearch`, `009.archive\reorg-manifests`, and `010.tmp-output\codex_tmp`.
- `D:\00.test\DIRECTORY_INDEX.md` is the quick navigation index. As of the first 2026-05-12 deferred cleanup run, `neo-genesis`, `project_yesol`, and `PAPER` are still deferred because open handles remain. Do not force copy-delete those roots.
- A 2026-05-12 handle-level `neo-genesis` check found Explorer, Claude worktree, Python, Node, node_repl, and cmd handles after direct safe blockers were stopped. Moving `neo-genesis` requires a maintenance window; do not kill active Claude sessions casually.
- A later 2026-05-12 pinpoint found `project_yesol` held by Explorer and Claude (`.claude`) and `PAPER` held by Claude (`.claude`). Agents should close/change cwd before retrying deferred cleanup.
- The deferred cleanup script now enforces minimum handle scan timeouts (`HandleTimeoutSeconds >= 60`, `SlowHandleTimeoutSeconds >= 180`) because a 5-second dry-run produced a false `dry_run_would_move` for `neo-genesis`.
- The hardened live rerun at 2026-05-12 13:47 moved nothing: `neo-genesis` was blocked by ToolPick Next build/jest-worker node processes, `project_yesol` by Explorer/Claude handles, and `PAPER` by Claude handles.
- Deferred cleanup is now scripted at `D:\00.test\007.infra-tools\006.directory-maintenance\Invoke-D00TestDeferredCleanup.ps1`. Agents should close their own handles at task end and run it from outside locked roots; run manifests go to `009.archive\001.reorg-manifests\deferred-cleanup-runs`.
- Automation `d00test-deferred-cleanup` is paused as of 2026-05-14. The remaining hidden real roots (`neo-genesis`, `project_yesol`, `PAPER`) are intentionally parked until a manual maintenance window clears long-running agent/session handles.
- 2026-05-14 visible-root residual cleanup moved `.playwright-cli` into `010.tmp-output` and recreated `neo-genesis_untracked_backup_20260505_083608` wrappers into `009.archive/003.reviewed-clones`; no deletes were performed.
- Applied batch 1 moved only low-risk items: root `acl_*` and `devices*.json` snapshots, duplicate `cts_slides`, stale `source` WSL venv, empty root `scripts`, and root `test-results` into numbered `root-cleanup-20260510` buckets.
- Resolved `neo-genesis_untracked_backup_20260505_083608`: active `auto-trading` SSOT was promoted to `D:\00.test\002.products-sbu\quant-bot`; the duplicate clean mirror and remaining reviewed backup wrapper were archived under `D:\00.test\009.archive\reviewed-clones`.
- Consolidated former root `_archive`, `_extracted`, and `tmp\interview_supergent_20260430` into `009.archive\legacy-root-archive`, `003.portfolio-career\extracted-assets`, and `010.tmp-output\interview_supergent_20260430`.
- Leave Google Drive temp roots, `personal/`, `_secrets/`, and live app/agent state untouched for cleanup unless a dedicated supported migration plan exists.

### Personal Legal/Financial Context Routing (2026-05-12)

- Owner feedback: agents were unaware that personal rehabilitation/legal context was already organized locally, causing the owner to re-explain the same facts in every session.
- Routing SSOT: `.agent/knowledge/PERSONAL_CONTEXT_ROUTING.md`.
- Protected local root: `D:\00.test\personal`.
- Default remains no-touch: do not inspect, index, move, summarize, upload, or share `personal/` unless the owner explicitly asks about personal legal, rehabilitation, debt, finance, court, or law-firm context.
- When explicitly authorized, agents must first check the existing organized context before asking the owner to restate facts:
  - `D:\00.test\personal\PROJECT_SPEC.md`
  - `D:\00.test\personal\전체자료_마스터인덱스.xlsx`
  - `D:\00.test\personal\01_사건서류\legal_case_status.md`
  - `D:\00.test\personal\05_전략보고서\`
  - `D:\00.test\personal\08_법무법인_제출용\`
- New owner-provided case facts should be folded back into the relevant tracker/report instead of remaining only in chat history.
