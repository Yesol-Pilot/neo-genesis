# Jarvis Architecture v2 — 1인 창업가용 자율 AI 파트너 (2026-05-24)

> **Author**: Strategy Lead Claude Opus 4.7 (1M)
> **Trigger**: owner "나만의 자비스를 만들기 위한 상세 연구 및 설계" — 텔레그램/슬랙 단일 게이트 → 멀티 에이전트(Hermes/Claude CLI/Codex CLI/Antigravity) 업무 분해 → 기획·설계·개발·디자인·구현·디버깅·고도화 전 과정 자동화·반복화 + 비판적 파트너 + warn-then-obey + PC/크롬 제어 + 환각 없는 도구 호출 + 초개인화 메모리 + 자가발전 + 로컬 멀티모달 생성
> **선행**: `20260520_JARVIS_ARCHITECTURE_v1.md` (백본 70% 라이브 확인)
> **본 v2 근거**: 3-갈래 라이브 심층조사 (frontier agentic CLI / RTX 4070 로컬 추론 / 게이트웨이·큐·메모리 하드닝) + `command_governor.py`·`system_tools.py` 실측

---

## 0. 한 장 요약 (TL;DR)

**자비스는 그린필드가 아니다. 70%가 이미 라이브다.** 빠진 30%는 (1) 게이트웨이 무결성, (2) 내구성 있는 작업 큐 + 동시성 제어, (3) 멀티-CLI 오케스트레이션 배선, (4) 초개인화 메모리, (5) 로컬 추론·멀티모달 tier. v2는 **재작성이 아니라 라이브 sora/hub/governor를 진화**시키는 설계다.

핵심 설계 원리 4가지:

1. **2-Phase Sovereignty (숙의 → 집행)** — owner가 원한 "비판적 파트너 + 무조건 복종"의 모순을 한 모델로 합친다. **결정 전(Phase A): 강제 반론(devil's advocate, 최소 N개 반대 의견 의무)**. **결정 후(Phase B): 절대 복종(warn-then-obey, 예외 0)**. 게이트는 owner의 "진행".
2. **환각은 결정론으로 차단** — 위험 명령 execute 결정에서 LLM을 배제(이미 라이브 학습). 위험 분류·allowlist 바이너리 매칭은 regex/코드, LLM은 NL 이해·포맷만.
3. **무료·오픈소스·로컬 우선, 클라우드는 escalation** — 종량제 비용 폭주 불가 구조. Claude Max/GPT Pro/Gemini Ultra 구독은 정액. 로컬 Qwen3는 RTX 4070 12GB에서 routine 담당.
4. **모든 것은 reversible + 감사된다** — 각 컴포넌트 독립 롤백. 전 명령 audit JSONL + SQLite.

**즉시 처리할 무결성 갭 (본 세션 발견)**: `command_governor.py`가 정본으로 참조하는 `project_jarvis_governance.md`가 메모리 디렉토리·`MEMORY.md` 인덱스 양쪽에 **부재** → 본 설계의 §2 거버넌스를 정본으로 복원.

---

## 0.5 제약 갱신 (2026-05-24) — **오직 desktop-home (이 PC)에서 호스팅**

> owner 명령 "오직 이 PC만 사용해야해". 본 §0.5가 이하 ysh-server 전제를 **override**한다.

**해석 (owner 확정 2026-05-24)**: "오직 이 PC" = **다른 디바이스(ysh-server/플릿) 미사용**. 게이트웨이·오케스트레이터·큐·메모리·온톨로지·벡터DB·PC제어·로컬추론 전부 desktop-home(Win11+WSL2). **클라우드는 허용 — 단 반드시 CLI로 접근, API 직접 호출 금지.**

**클라우드 = CLI only (API 금지) — 핵심 제약 (owner 명시)**:
- **이유(설계 정합)**: API = 종량제 → 키 유출 시 비용폭주(battlefield ₩849K 사고 재현 위험). CLI = 구독 정액(Claude Max / GPT Pro / Google AI Ultra) + OAuth 인증(`.credentials.json`/`auth.json`, 이미 symlink 공유) → **유출 가능한 종량 API 키가 hot-path에 없음 = 비용폭주·키유출 구조적 불가**. 이 제약은 안전장치다.
- **§4 routing override (이하 본 블록이 정본)**:
  | 역할 | API(금지) | → CLI/로컬(정정) |
  |---|---|---|
  | L1 빠른 triage/분류 | ~~Gemini Flash API~~ | **로컬 Ollama (Qwen3-8B / qwen2.5:14b)** — `agent_router.py`의 `genai.Client(api_key=)` 경로 제거 |
  | L2 설계·비판 | — | **Claude Code CLI** (`claude -p`, Max) ✓ |
  | L2 구현·디버그 | — | **Codex CLI** (`codex exec`, Pro) ✓ |
  | L3 Google·멀티모달·장문 | ~~Gemini API / ADK~~ | **Gemini CLI(6/18 sunset)/Antigravity CLI(`agy`)** — CLI만. headless 미성숙 → 역할 최소 |
  | 이미지/영상 | ~~Gemini image API / OpenAI Sora API~~ | **로컬 ComfyUI** (Flux/SDXL/LTX/Wan). `execution_gate`의 `comfyui_*`/`local_generate_image`가 정답, `generate_image`(Gemini API) 비활성 |
  | 메모리(Graphiti) 추출 LLM | ~~cloud API~~ | **로컬 Ollama** (OpenAI-호환 endpoint) → 완전 로컬 메모리 파이프라인 |
- **§4.3 정정**: "Gemini API 직접 호출 / Antigravity Python SDK" → **Gemini는 CLI로만**(API/SDK 금지). 
- **§4.1 정정**: L1 tier = Gemini Flash(API) → **로컬 Ollama**. 종량제 노출 = **0** (Gemini budget 캡도 불필요해짐).
- ⚠️ **파트너 리스크 지적**: 구독 CLI를 24/7 자율 워커로 돌리면 구독 rate-limit/ToS(원래 대화형 개발 용도) 저촉 가능. Claude Code/Codex는 agentic 용도 명시라 대체로 안전, 단 **고빈도 L1을 CLI로 돌리면 위험** → **L1 = 로컬이 정답**. 이 제약이 오히려 로컬-퍼스트를 강제 = 설계상 바람직.

**바뀌는 것 (이하 섹션 override)**:
| 원래(v2 초안) | "오직 이 PC" 정정 |
|---|---|
| §3/§4 오케스트레이터 = ysh-server always-on | **desktop-home Windows Service / WSL2 systemd** |
| §1.1 PC Agent Hub = ysh-server :7700 | **desktop-home 로컬 hub** (또는 hub 자체 불필요 — 제어 대상이 곧 자기 자신) |
| §6 메모리 Neo4j/Qdrant = ysh-server | **desktop-home Docker (WSL2)** |
| §9 "ysh ufw" P0 | Jarvis 범위 밖 (일반 보안 항목으로 잔존) |
| §5.1 게이트웨이 long-polling | **유지 — 이 제약에서 오히려 정답** (아래) |

**always-on 문제 해결 (핵심)**: desktop-home은 로그온 의존(Startup) = 진짜 always-on 아님. 정정:
1. 게이트웨이를 **Windows Service(NSSM) 또는 WSL2 systemd(linger)**로 승격 — 로그온 무관 상시 가동.
2. 전원 절전 끄기(`powercfg /change standby-timeout-ac 0`) + (선택) Wake-on-LAN.
3. **Telegram long-polling + update 24h 보관**을 이용 — PC가 잠깐 꺼져도 메시지 유실 0. 재가동 시 buffered update를 dedup(update_id)으로 안전 재수신. → **단일 PC라도 webhook 불필요, long-polling이 더 견고**. (webhook은 공인 IP/터널 필요 = 단일 가정 PC에 부적합.)

**이 제약의 이점**: (a) ysh-server 노출포트/미상 사용자(jhhan) 보안 리스크 회피, (b) PC 제어가 로컬 = WebSocket fan-out 불필요·환각 표면 축소, (c) RTX 4070 GPU가 같은 호스트 = 로컬 추론/생성 직결, (d) 감사·메모리·secret 전부 owner 단독 통제. **단점**: 진짜 24/7은 PC 전원 의존(위 1~2로 완화).

---

## 0.6 라우팅 확정 + P0 착수 (2026-05-24 turn 5, owner "진행해")

**라우팅 결정 = (A) 확정 (reversible)**: CLI-only 유지 + L1 = warm 로컬. owner "진행해" = 권고안 위임 → G1 박제.
- **3-계층 분리** (owner "기본 호출 누가?" 응답):
  - ① 트리거 = 게이트웨이(텔레그램) + **스케줄러(Hermes cron / Windows Task Scheduler)** — 자동화·반복 작업을 큐에 enqueue.
  - ② **기본 호출자 = 오케스트레이터** (`brain/worker.py` + `agent_router.py` 진화) — 큐에서 꺼내 분류·라우팅·워커 호출·결과 기록. **CLI도 Hermes도 아님.**
  - ③ 워커 = Codex 네이티브 러너(주력) / Claude CLI(특화·절약) / 로컬(L1·routine) / ComfyUI(이미지·영상).
- **Hermes 역할 정정**: CLI 호출자 X(네이티브 `codex_runtime/runner.py`가 이미 `codex exec --json --sandbox` 호출 — 검증). 트리거/스케줄러 O(자동화·반복). 단 WSL2 always-on·5/20 false-pass 리스크 → Task Scheduler가 신뢰성 위.
- **L1 엔진 확정 (turn 6, 이 PC 실측 근거)**: Ollama 가동 중(200). 로컬 실재 = `llama3.2:3b`(2GB,즉답)/`llama3.1:8b`/`qwen2.5-coder:14b` (`qwen3.6:35b`=23GB라 12GB VRAM 초과·RAM offload 느림). `:cloud` 모델 다수 등록됐으나 **현재 403(미인증)**.
  - **L1 라우팅 = 로컬 small(`llama3.2:3b`/`llama3.1:8b`)** — $0, 가동 중, L1=라우팅이라 로컬 약점 무관.
  - **스마트 클라우드 = Ollama Cloud via CLI**(`gemini-3-flash-preview:cloud`/`Qwen3.5:cloud`/`deepseek-v4-flash:cloud`) — **owner 의 "Gemini CLI ₩10만"을 더 안전하게 실현**: Google API 키 0(=battlefield 위험 클래스 제거) + 정액 + 로컬 ollama 인터페이스(=CLI 정신 부합) + Flash급 속도. **현재 403 → owner `ollama signin` 1회**. **raw Google Gemini API 키는 미생성**(불필요·위험만).
  - 환각은 엔진 아닌 **스택**(MCP schema + `execution_gate` registry + 5-10 sub-group + 증거게이트)이 무해화 → 엔진 swappable, 어려운 tool-calling은 Codex/Claude.
  - 다음 brick: `agent_router.py` 의 raw Gemini API(`genai.Client(api_key=)`) primary 경로 **제거** → 로컬+키워드 L1.
  - 체감 속도는 L1 엔진이 아니라 **즉시 ack + 스트리밍**으로 해결.

**P0 첫 brick 라이브 (검증 완료)** — control-plane ledger:
- `src/core/queue/sqlite_ledger.py` (신규, 순수 stdlib) — WAL durable queue + **fencing token**(Kleppmann) + **kill switch**(epoch 무효화) + ingress dedup(update_id+content_hash, 26h TTL) + token bucket + **strict approval FSM**(confirm_id hash + action_hash bind + TTL) + **증거 게이트**(`can_report_success`: exit_code=0+output_hash 없으면 "실행 완료" 보고 불가).
- `tests/core/test_sqlite_fencing_queue.py` (신규) — **8/8 PASS** (`python tests/core/test_sqlite_fencing_queue.py`): enqueue/claim/complete · stale worker fencing 차단 · kill switch freeze · dedup · token bucket · approval FSM(승인/만료/action변경/바인딩위반) · 증거 게이트 · 멱등.
- blast radius 0 (신규 파일, 라이브 import 0). 롤백 = 2파일 삭제.

**아직 아님 (정직)**: 이건 control-plane **기반 라이브러리**다. 라이브 배선 X — 게이트웨이(`telegram_webhook.py`)·오케스트레이터(`brain/worker.py`)·L1 로컬 전환(`agent_router.py` Gemini-API 제거)·approval 인라인버튼·결정론 allowlist·tree-sitter·메모리·로컬서빙 전부 다음. 멀티프로세스 동시성 부하 테스트도 future(현 테스트는 단일프로세스 논리 검증).

**외부 보고서 #5(`deep-research-report_new.md`) 교차검증 + 보정 (turn 7)**:
- ✅ **P0 독립 검증**: #5의 receipt 프로토콜·fencing 큐(BEGIN IMMEDIATE + lease_token WHERE)·approval FSM(confirm_id+digest bind+supersede+60s)·persistent dedup(+payload_hash)이 본 ledger 구현과 정확히 일치 → 기반 설계 확증.
- 🔴 **kill switch 과대보고 정정**: 본 P0 `activate_kill_switch`는 **DB 측(새 claim 차단 + lease epoch 무효 + frozen)만** 구현. **이미 실행 중인 프로세스(브라우저/셸/영상)를 0.5초 내 멈추는 프로세스-신호 계층(worker supervisor SIGTERM/CTRL_BREAK + 장기 도구 200~250ms heartbeat 취소토큰)은 미구현** = kill switch의 나머지 절반. "0.5초 SLA"는 DB=진실원천 + 프로세스신호=즉시성 두 계층이 있어야 성립.
- **채택 업그레이드**: ① **sqlite-vec** 임베디드 벡터검색 (오직-이-PC에 최적, Neo4j+Graphiti 서비스보다 가벼움 → 메모리 초기층은 SQLite ledger + sqlite-vec, 무거워지면 Qdrant/GraphRAG 승격) ② lock key = **`(repo_id, rel_path)`** (절대경로 미사용, §5.3 canonical_uri 대체) ③ **cost-route 토큰버킷**(research/browser/image/video/cloud_coder 비용클래스 분리) ④ Open WebUI 사용 시 Tailscale 뒤 + Direct Connections off.
- **반영 안 함**: #5의 Hermes-center → 라이브 증거(5/20 WSL2 false-pass + always-on 아님 + native base 존재)로 **native 오케스트레이터 중심 + Hermes=스케줄러** 유지(§0.6). ledger가 양쪽 다 받쳐 fork는 게이트웨이 wire 단계로 defer. #5의 L1=Gemini-API는 CLI-only(§0.5)로 override.

**다음 brick (순서)**: ① `agent_router` L1 → 로컬+키워드 (Gemini API 제거) → ② 게이트웨이 dedup+ratelimit 배선 → ③ approval 인라인버튼 → ④ 오케스트레이터가 ledger claim/complete 사용하도록 wire.

---

## 0.7 병렬 웹 검증 결과 (turn 8, 5 에이전트 공식출처 실측) — 일부 설계 변경

owner "에이전트 병렬 호출해 실제 검색·조사" → 5 영역 공식출처 검증. 내 기존 주장 4개 확증 + **3개 새 사실로 설계 변경**.

| 영역 | 판정 | 근거(공식) |
|---|---|---|
| Hermes center? | **REFUTE** — `delegate_task`=in-process 스레드(외부 CLI orchestration=Issue#413 **미구현**), WSL2 systemd "unreliable"(공식 FAQ 직접 명시), cron #13653 open, native memory 3,575자뿐. → **native 오케스트레이터 center 확정, Hermes=보조** | NousResearch/hermes-agent FAQ·#413 |
| Ollama Cloud(내 제안) | **CONFIRM(조건부)** — 실재, `ollama signin`이 403 해소(Google키 0), **Pro $20/mo(≈₩27K, ₩10만 내)**, `ollama run`/localhost:11434 경유=**CLI-not-API 충족**. ⚠️ **`gemini-3-flash:cloud` tool-calling 버그(#73909 open)** → tool-calling은 `qwen3.5:cloud`/로컬+테스트 | ollama.com/pricing·/blog/cloud-models |
| Claude/Codex 한도 | **CHANGED** — **2026-06-15부터 `claude -p`가 plan 한도와 분리 → 별도 월 Agent SDK 크레딧(Max20x=$200/mo)**. owner "Claude 한도 낮음" 전제는 **지금만 참, 6/15 후 소멸**. Codex Pro=20x(높으나 무제한 X). 공식 CLI 바이너리 subprocess=ToS OK / OAuth 토큰 추출·Agent SDK 직접=금지 | support.claude.com/articles/15036540 |
| Antigravity 워커 | **REFUTE(defer 확정)** — `agy`: API키 인증 없음(#78 open), JSON 불안정, 세션ID 노출 없음(#7)→병렬 불가. Gemini CLI **6/18 sunset 확정**. → flag 뒤 defer | antigravity-cli #7·#78 |
| 메모리/로컬모델 | **CHANGED** — 시작=**Mem0(Apache-2.0, Ollama 추출/임베딩) + sqlite-vec(단 pre-v1 v0.1.9, 버전고정)**, 승격=Graphiti+Neo4j Community. (내 Graphiti-first 정정.) **L1=`qwen2.5:3b`**(arXiv Pareto-dominant, llama3.2:3b 우위), tool-calling=`qwen3:8b`/보유 `qwen2.5-coder:14b` | mem0·getzep/graphiti·sqlite-vec·arXiv 2604.02367 |

**🔴 3개 설계 변경**:
1. **Claude 6/15 한도 분리** → "Codex 주력 because Claude 제약"은 **3주 시한부**. 6/15 후 Claude `-p`가 독립 $200 크레딧 → **모델 특성 기반 듀얼 워커**(Codex=구현/Claude=설계·비판)로, 한도 때문이 아니라 강점 때문에 분업.
2. **메모리 = Mem0 + sqlite-vec(버전고정) 시작** → 무거워지면 Graphiti+Neo4j 승격. (sqlite-vec 단독은 pre-v1.)
3. **L1 = `qwen2.5:3b`**. **Gemini 접근 = `agy` CLI 아닌 Ollama-cloud `gemini-3-flash:cloud`**(agy 워커 미성숙 확정 → Ollama-cloud가 유일한 CLI-compliant Gemini 경로).

**✅ 확증(유지)**: native 오케스트레이터 center / Antigravity defer / Ollama-cloud=CLI-not-API 유효 / L1 로컬 / Codex 네이티브 러너 주력.

**owner action**: `ollama signin`(클라우드 tier 활성) + (선택) `ollama pull qwen2.5:3b`(L1 라우터). **단 only-this-PC라 cron 스케줄러는 ysh-server 불가 → Windows Task Scheduler 또는 오케스트레이터 내장 APScheduler.**

**인증 정합(중요)**: 오케스트레이터는 **공식 `claude`/`codex` CLI 바이너리를 subprocess로** 호출(구독 OAuth=정액, ToS OK). raw 종량 API 키(ANTHROPIC/CODEX_API_KEY) 미사용 → owner CLI-only 규칙 + 정액 둘 다 충족.

---

## 0.8 섀도 control-plane 완성 (turn 9, owner "전권 위임 진행") — 34 tests green

owner "다되면 최종 판단하고 진행 / 내 개입 필요할 때까지 자율, 단 연구·분석 기반" → 검증 끝난 설계를 코드로. 라이브 무변경(전부 `src/core/jarvis/` + `src/core/queue/` 신규).

**산출 (6 모듈 + 5 테스트스위트, 34 tests PASS)**:
| 모듈 | 역할 | 문제 | tests |
|---|---|---|---|
| `queue/sqlite_ledger.py` | durable queue + fencing + kill-switch DB + dedup + token bucket + approval FSM + 증거게이트 | 2.4·2.1 | 8 |
| `jarvis/command_router.py` | 결정론 위험분류 + allowlist 바이너리(shell=False) + 주입방어 + lane 라우팅 (한국어 어미 robust) | **2.2** | 9 |
| `jarvis/gateway_guard.py` | owner allowlist + dedup + per-chat/cost-route token bucket | **2.1** | 4 |
| `jarvis/process_supervisor.py` | kill-switch 프로세스 계층 (취소토큰 + SIGTERM supervisor + watcher) — §0.7 "나머지 절반" | **2.4** | 5 |
| `jarvis/worker_dispatch.py` | Codex/Claude/로컬 CLI 워커 argv + 증거(tool_runs) 기록 + runner 주입 | 4 | (e2e) |
| `jarvis/orchestrator.py` | 전 파이프라인: 게이트→라우팅→2-Phase 거버넌스→큐→워커→증거보고 ("기본 호출자") | 2/3 | e2e 8 |

**테스트로 증명된 owner 핵심 요구**:
- 환각 차단 ✅ — 워커 실패 시 증거게이트가 "실행 완료" 거짓 보고 봉쇄 (`test_failed_worker_no_false_success`).
- 2-Phase Sovereignty ✅ — 명시 위험 → warn+confirm_id → "진행" → 실행 (`test_explicit_danger_warn_then_obey`).
- 모호한 위험 → 재입력 강제(LLM 미경유) ✅ / 비-owner 차단 ✅ / dedup ✅ / kill-switch 실행거부 ✅.
- fencing(stale worker 차단) ✅ / 토큰버킷 rate-limit ✅ / 프로세스 강제종료 ✅.

**정직한 범위 (grill-toast 자기검증)**:
- **섀도다 — 라이브 미배선.** `telegram_webhook.py`/`agent_router.py` 무변경, 어떤 라이브 코드도 jarvis/ 를 import 안 함 → blast radius 0, 롤백=폴더 삭제.
- **e2e 는 fake runner** — 파이프라인 로직 검증이지 **실 codex/claude/ollama 호출은 미검증**(라이브 smoke=구독 quota 소모, owner 승인 사안).
- **멀티프로세스 부하 미테스트** (단일프로세스 논리 검증).
- **text "진행" 승인은 최근 1건만** (multi-pending 모호성) → robust 경로 = **inline button confirm_id**(ledger `decide_approval` 기구현, 배선 TODO).
- L1 로컬 모델(`qwen2.5:3b`) 미pull / 메모리(Mem0+sqlite-vec) / tree-sitter(2.3) 미착수.

**🚦 owner-gate 도달 (자율 진행 정지점)**:
1. **`ollama signin`** (+ 선택 `ollama pull qwen2.5:3b`) → 스마트 클라우드 + L1 로컬 모델 활성. (내가 pull 대행 가능.)
2. **라이브 cutover** — 섀도 control-plane을 라이브 telegram/agent_router에 배선. 라이브 런타임 동작 변경 → sora 현 상태 SSH 확인 + owner go 필요(warn-then-obey).

**다음 brick (gate 통과 후)**: 실 CLI smoke 1회 → inline-button approval 배선 → L1 ollama 연결 → 메모리(Mem0+sqlite-vec) → 라이브 cutover(백업+섀도 병행) → tree-sitter(2.3).

### 0.8.1 라이브 검증 (turn 10, owner "전부 열고 검증") — 실 호출, 3 통합버그 fix
- ✅ **DESIGN 레인 LIVE**: orchestrator → 실제 `claude -p` → 증거게이트 → "✅ 실행 완료" (실 한국어 출력 캡처, `tests/core/smoke_live_dispatch.py`).
- ✅ **CHAT/로컬 레인 LIVE**: orchestrator → 로컬 `ollama qwen2.5:3b` → 성공 (실 출력 "안녕하세요…").
- ✅ **증거게이트(환각 차단) 라이브 확인**: 워커 실패 시 "실행 완료" 거짓보고 차단 / 성공 시 실 output_hash 기록.
- 🐛 **fake-runner e2e 가 못 잡은 실 통합버그 3건 발견+수정** (`worker_dispatch.py`):
  1. `claude --bare` 가 구독 OAuth 를 건너뜀 → "Not logged in" → **`--bare` 제거**.
  2. 비대화형 stdin 3초 대기 → **`stdin=DEVNULL`**.
  3. Windows cp949 가 UTF-8 CLI 출력 깨뜨림(stdout 유실) → **`encoding=utf-8`**.
  + 비용: `--bare` 없으면 cwd CLAUDE.md(135K tok) 로드 → **`JARVIS_WORKER_CWD`(깨끗한 dir)** 로 회피.
- ✅ `ollama signin`(이미 로그인 dpthf1537) / `qwen2.5:3b` pull 완료 / **34/34 회귀 그린**(fix 후).
- ❌ **Ollama-cloud 검증 실패**: `qwen3.5:cloud`·`gemini-3-flash:cloud` → `/api/generate` **403** + `ollama run` 무응답 (signin 됐는데도). agent 검증의 "Pro $20면 됨"이 **이 계정엔 미적용** → 스마트 클라우드 tier **보류**(로컬 qwen + Claude/Codex CLI 로 충분).
- ⏳ CODE 레인(codex) live smoke 미실행(동일 dispatch 경로 = 메커니즘 증명됨; codex-특화 인증/git-cwd 별도) / 라이브 Telegram cutover 미착수.

### 0.8.2 🚦 owner 개입 필요 (자율 진행 한계 도달)
1. **Ollama 클라우드 활성** — ollama.com 플랜 확인(403 = 계정 클라우드 미활성). 미활성이면 스마트 클라우드 보류, 로컬+CLI 로 운영(지장 없음).
2. **라이브 cutover bot 결정** — 7봇 중 Jarvis 전용 1개 지정 필요(live sora 와 같은 토큰이면 409 충돌). 결정 시 Telegram long-poll 게이트웨이 + Windows Service 배선(백업+섀도 병행).

### 0.8.3 문제 2.3 완료 (turn 11, owner "다음") — tree-sitter Typed Outline IR
- `src/core/jarvis/ts_outline.py` (신규) — **py-tree-sitter + tree-sitter-typescript** (설치 완료). `.ts`→language_typescript / `.tsx`→language_tsx 분리. API 최신(Query()+QueryCursor.matches). 추출: interface/type/enum/function/class/method + **hook(`^use[A-Z]`)·component(PascalCase+tsx)·route_handler(GET/POST..)** 재분류 + exported/default/async/signature/line. `outline_dir()` 전 SBU 일괄.
- WSL 경로(2.3 후반): `canonical_rel(repo_root, path)` = lock key (repo-rel posix, 절대경로 미사용 — 검증 #5) + `to_wsl`/`to_win`(wslpath bridge).
- `tests/core/test_jarvis_ts_outline.py` **12/12 PASS** (interface/type/enum/default component/route/hook/arrow component/class+method/비-export/.ts 비-component 분류/canonical_rel/extract_file). 실 tree-sitter 파싱(목 아님).
- **→ owner 4대 문제(2.1 게이트 / 2.2 환각·주입 / 2.3 TS-TSX / 2.4 큐·fencing) 전부 코드+테스트 완료.** 누적 **46 tests green** (ledger8+router9+gateway4+supervisor5+e2e8+ts_outline12).
- 다음 자율 brick: 메모리(Mem0+sqlite-vec, "모든 대화 기억·초개인화") → inline-button approval(decide_approval) → (gate 후) cutover.

---

## 1. 현재 상태 — Cold Honest (v1 → v2 gap)

### 1.0 검증 보정 (2026-05-24 turn 2) — **기존 base가 §1.1 표보다 큼**

owner가 제시한 외부 설계서 #4(`docs/architecture/20260524_jarvis_sovereign_agent_design.md`)가 참조한 파일을 Glob+Grep 실측한 결과 **전부 실재** → 본 v2의 §1.1 표·§1.2 일부는 **과소계상**이었음(정정):

| 추가 확인된 기존 자산 (실측) | 내용 |
|---|---|
| `src/core/governance/execution_gate.py` | **진짜 G0-G5 권한 모델** — `AUTHORITY_ORDER{G0..G5}` + 도구별 `ToolPolicy`(deploy=G5 / remote_pc_command=G3 / gmail_send=G4 / save_to_memory=G2 + requires_external_approval) + `GateDecision`. command_governor 위에 capability gate 이미 존재 |
| `src/core/gateway/telegram_webhook.py` + `chat_api.py` | **webhook 진입점 이미 스캐폴드** (polling 외) |
| `src/core/brain/agent_router.py` | **멀티에이전트 라우터 이미 존재** — Gemini flash-lite 주 + 2.5 fallback + Ollama `qwen2.5:14b` 로컬-퍼스트(LiteLLM) + `remote_claude_run`(Claude CLI) + ComfyUI(집PC GPU). 에이전트별 5-10 도구 |
| `src/core/codex_runtime/runner.py` + `context.py` | Codex CLI 실행 경로 이미 존재 |
| `src/core/queue/redis_bus.py` | Redis 신호 버스 (단 SQLite durable ledger는 없음 = 신규 정확) |

**함의 (중요)**: 오케스트레이션·권한게이트·로컬-퍼스트 라우팅·Claude/Codex-as-tool은 **이미 코드로 존재**. "70%"는 오히려 과소 — **빠진 건 에이전트가 아니라 control-plane 내구성·무결성**(durable queue+fencing / ingress dedup+rate-limit / strict approval FSM / 증거기반 실행진실). #4가 이 갭을 정확히 짚었고, **레포-ground 현재상태 정본 = #4**. 본 v2는 #4를 backbone으로, §0.5(오직 이 PC)를 host override로 합성한다(→ v2.1). 단 `agent_router`의 LiteLLM이 `ysh-server:4000`을 가리키므로 "오직 이 PC"에선 desktop-home로 재지정 필요(env 교체).

### 1.1 이미 라이브인 것

> **검증 출처 구분** (grill-toast 자기정정): 본 세션 직접 검증 = `command_governor.py` 전문 Read + `system_tools.py` governor 배선 Grep + `pc_agent/`·`security/` 파일 존재 Glob. **런타임 가동 상태(:7700 응답, PC agent 현재 연결, sora 현재 프로세스)는 v1 문서(2026-05-20, 4일 전) 기준 — 미재검증**. `feedback_server_check`(SSH 직접 확인 필수) 정합상, Phase 1 착수 전 라이브 재확인 필요.

| 컴포넌트 | 파일/위치 | 상태(출처) |
|---|---|---|
| PC Agent Hub (WebSocket fabric) | `src/core/pc_agent/hub.py`, ysh-server :7700 | ✅ 라이브 |
| 원격 도구 (sora ALL_TOOLS 등록) | `system_tools.py` `remote_pc_command`(602) / `remote_batch_exec`(787) / `remote_claude_run`(683) / `remote_vercel_deploy`(763) / `confirm_pending_command`(813) | ✅ 라이브 |
| **warn-then-obey governor** | `src/core/security/command_governor.py` (11 위험패턴 + audit JSONL + stage/take_pending TTL 600s) | ✅ 라이브 |
| 결정론적 명령 라우터 (환각 우회) | `sora_engine._tool_intent_fastpath` §9/10 | ✅ 라이브 |
| 디바이스 별칭 resolver | `system_tools.resolve_device`(571) + `DEVICE_ALIASES`(562) | ✅ 라이브 |
| Telegram owner allowlist | `_reject_unauthorized_chat`, NEO_ALERT_CHAT_ID=1566967334 | ✅ 라이브 |
| PC agent (desktop-home) | Startup `sora_pc_agent.vbs` → ws://100.67.221.25:7700 | ✅ 라이브(로그온 시) |
| Hermes Agent v0.14.0 | WSL2, `/usr/local/bin/hermes` | 🟡 idle (cron은 ysh-server crontab로 이관됨) |
| Claude/Codex CLI 인증 공유 | Windows↔WSL2 symlink (`.credentials.json`/`auth.json`) | ✅ 라이브 |
| 온톨로지 v0.4 (Neo4j+JSONL) | `.agent/ontology/` 30+ 파일 | 🟡 로컬 JSONL 작동 / AuraDB NXDOMAIN 소멸 |
| Qdrant 벡터 DB | ysh-server :6333 | ✅ 가동(단 인증 없이 노출 — §9) |

### 1.2 작동하지 않거나 빠진 것

- **게이트웨이 무결성 없음** — update_id 중복제거·rate-limit·strict approval 미구현 (owner 문제 2.1 정확)
- **내구성 큐 없음** — `governor_pending.json` 단일 파일, fencing token·동시성 제어 부재 (owner 문제 2.4 정확)
- **멀티-CLI 오케스트레이션 미배선** — Claude/Codex CLI가 워커로 자동 라우팅되지 않음 (Hermes `delegate_task`는 in-process지 CLI subprocess 아님)
- **초개인화 메모리 약함** — cron probe가 history를 밀어내 cross-turn 실패 이력 (sora 5/4 사건). Graphiti급 영속 메모리 미통합
- **로컬 추론 tier 미가동** — LL-1(안티바이러스 예외) 미해소로 로컬 LLM 라우팅 차단
- **tree-sitter TS/TSX 정규화 부재** — Python `ast`가 11 SBU의 TS/TSX 0줄 파싱 (owner 문제 2.3 정확)

### 1.3 발견된 무결성 갭 (본 세션)

`command_governor.py:5`가 거버넌스 정본으로 `project_jarvis_governance.md`를 명시하나 **메모리 디렉토리(8개 파일)·`MEMORY.md` 인덱스 어디에도 없음**. live 안전코드가 존재하지 않는 정본을 가리킨다 → 본 설계 §2를 정본 텍스트로 복원(별도 메모리 파일 + MEMORY.md 포인터).

---

## 2. 설계 철학 — 2-Phase Sovereignty (숙의 → 집행)

owner 요구의 핵심 모순: *"AI는 비판적으로 검토하고 모두가 옳다 해도 누군가는 틀렸다 할 수 있어야"* + *"리스크에도 내가 진행하라면 모든 명령 수행"*. 둘은 **단계 분리**로 깔끔히 합쳐진다.

```
┌─ Phase A: 숙의 (DELIBERATION) ────────────────────────────┐
│  AI = 적대적 파트너 (Red Team)                              │
│  • 모든 비자명한 결정 전 반론 ≥2개 의무 (devil's advocate)   │
│  • 리스크·비용·대안 표면화. "동의" 금지, "이게 틀릴 수 있는 │
│    3가지" 먼저.                                            │
│  • 위험 명령 → 결정론적 분류 → "왜 위험 + 권고" 반환         │
└──────────────────────────── owner 결정 ("진행") ───────────┘
                                  │  ← Sovereign Gate
┌─ Phase B: 집행 (EXECUTION) ──────▼────────────────────────┐
│  AI = 절대 집행기 (warn-then-obey)                          │
│  • owner override = sovereign. 무엇이든 반드시 실행. 예외 0  │
│  • 재논쟁 금지(이미 Phase A에서 끝남). 환각 보고 금지        │
│  • 전 명령 audit. 결과는 ground-truth만 보고               │
└───────────────────────────────────────────────────────────┘
```

**구현 매핑**:
- Phase A 반론 = Claude 워커의 `--append-system-prompt`에 "principal engineer로서 모든 제안에서 결함·리스크·더 단순한 대안 3개를 먼저 찾아라. 검증(validate)하지 말고 반증(refute)하라" 주입 (조사 검증된 패턴).
- Sovereign Gate = inline keyboard `callback_query` + 60s TTL `confirm_id` (텍스트 "진행" 매칭의 취약성 제거, §5.1).
- Phase B = 기존 `command_governor` + `confirm_pending_command` 진화.

**환각 차단 원리 (이미 라이브 학습)**: v1 §11에서 Gemini Flash AND Pro 둘 다 `rm -rf`를 "실행했다" 환각(도구 호출 0건). 구조적 결론 = **위험 명령에서 LLM tool-calling 신뢰 불가**. → execute 결정은 결정론적 라우터가, LLM은 NL 이해·결과 포맷만. v2는 이를 allowlist 바이너리 매칭(§5.2)으로 강화.

---

## 3. 목표 아키텍처 (전체 데이터 흐름)

```
[텔레그램/슬랙 한 통]
   │  (1) Gateway 무결성 layer  ── §5.1
   │   • 단일 폴러 불변식 (PID flock)  • update_id dedup (TTL/LRU)
   │   • per-chat 토큰버킷 rate-limit  • owner chat_id allowlist
   ▼
[Orchestrator]  (sora_engine 진화, ysh-server always-on)
   │  (2) 의도 해석 + 위험 분류 (결정론 우선) ── §5.2
   │  (3) 작업 분해 → SQLite 내구성 큐 (fencing lease) ── §5.4
   │  (4) Phase A 숙의: 비판적 파트너 반론 (위험 시 Sovereign Gate)
   ▼
[Brain 라우팅]  ── §4
   ├─ L0 로컬 Qwen3 (routine, $0, RTX 4070)  ── §7
   ├─ L1 Gemini Flash (의도해석/단순 즉답)
   ├─ L2 Claude CLI (설계·비판리뷰) + Codex CLI (대량구현·디버깅) ── 워커
   └─ L3 Cloud frontier (Opus/Gemini Pro/GPT, 장문·고난도 escalation)
   ▼
[워커 실행면]  ── §8
   ├─ CLI 워커: claude -p / codex exec (구조화 출력 캡처)
   ├─ MCP 도구: github/supabase/vercel/cloudflare/chrome/...
   ├─ 로컬 멀티모달: ComfyUI(이미지/비디오) / whisper / TTS ── §7
   └─ PC Agent Hub → 디바이스(exec/read/screenshot/status) ── 라이브
   ▼
[회신 + 감사 + 메모리]  ── §6
   • 텔레그램 결과 보고 (ground-truth)
   • audit JSONL + SQLite  • Graphiti bi-temporal 메모리 갱신
   • 자가발전 루프 (reflection → 정책/스킬 개선)
```

### 컴포넌트 책임 (Single Responsibility)

| 계층 | 책임 | 신뢰 경계 |
|---|---|---|
| Gateway | 입력 검증·dedup·rate-limit·승인 FSM | 신뢰 안 함 (외부 입력) |
| Orchestrator | 의도해석·분해·라우팅·큐·거버넌스 | owner 명령만 |
| Brain | 추론·계획·반론 | 도구 호출 결정 X (위험명령) |
| Worker (CLI/MCP) | 실제 작업 실행 | sandbox + allowlist |
| PC Agent | "멍청한 실행기" | 안전 전부 상위 layer (현 설계 유지) |
| Memory | 영속·검색·자가발전 | personal 절대 분리 (§9) |

---

## 4. 브레인 / 멀티 에이전트 오케스트레이션

### 4.1 4-tier Brain (성능 × 속도 × 비용)

| Tier | 엔진 | 용도 | 비용 |
|---|---|---|---|
| **L0 로컬** | Qwen3-14B Q4 (RTX 4070) | routine·분류·RAG·도구호출, 프라이버시, 오프라인 fallback | $0 |
| **L1 빠른 길** | Gemini Flash | 의도해석·단순 즉답(~1s) | 저(Flash, 한도캡 ₩100K) |
| **L2 워커** | Claude CLI + Codex CLI | 설계·비판리뷰·대량구현·디버깅 | $0 (Max/Pro 정액) |
| **L3 escalation** | Opus 4.7 / Gemini 2.x Pro / GPT-5.x | 장문(>100K)·고난도 판단·창작 | 정액 구독 |

종량제 노출은 Gemini Flash(L1)뿐 → 게이트웨이 rate-limit(§5.1) + GCP budget ₩100K(기 설정)로 이중 차단. battlefield(₩849K) 급 사고 구조적 불가.

### 4.2 워커 라우팅 정책 (각 도구의 검증된 강점)

| 작업 (전 SDLC) | 워커 | 비대화형 호출 | 근거 |
|---|---|---|---|
| **기획·아키텍처 + 비판 리뷰** | `claude -p --model opus` | `--append-system-prompt "반증하라"` + `--output-format json` | Opus 추론·반론 깊이 (Phase A 적대 파트너) |
| **대량 구현** | `codex exec` | `--sandbox workspace-write --ask-for-approval never --json` | gpt-5.x throughput, git diff native, 병렬 편집 |
| **디버깅·오류 분석** | `codex exec` (stdin pipe) | `npm test 2>&1 \| codex exec --json "진단+최소수정"` | 파이프 + JSON 이벤트 단계추적 |
| **보안·품질 리뷰** | `claude -p --model opus` | `--append-system-prompt "adversarial reviewer, STRIDE/DREAD"` | constitution 안전추론 |
| **웹·크롬 자동화** | Claude-in-Chrome MCP / `claude --chrome` | MCP `navigate/computer/read_page` | 네이티브 브라우저 통합 |
| **배포·CI** | `codex exec` | `--sandbox danger-full-access --model gpt-5-mini` | git native, 저비용 |
| **Gemini/Google 연동** | Gemini API 직접 / Antigravity SDK | (CLI 보류, §4.3) | Antigravity CLI headless 미성숙 |
| **routine·분류·RAG** | 로컬 Qwen3 | Ollama OpenAI-API | $0, 프라이버시 |
| **스케줄·알림** | ysh-server crontab + Telegram | (Hermes 대체, §4.4) | always-on |

**구조화 출력 캡처 (큐 워커용, 검증)**:
```python
# Claude 워커
r = subprocess.run(["claude","-p","--output-format","json",
    "--dangerously-skip-permissions","--bare","--max-budget-usd","1.00", prompt],
    capture_output=True, text=True, timeout=300)
data = json.loads(r.stdout)  # result / session_id / total_cost_usd / usage
# Codex 워커 (JSONL stream)
proc = subprocess.Popen(["codex","exec","--json","--sandbox","workspace-write",
    "--ask-for-approval","never", prompt], stdout=PIPE, text=True)
# event["type"]=="turn.completed" 에서 최종 수집
```
exit code 0 = 성공. `--bare`(Claude)는 hooks/MCP/CLAUDE.md 스킵 → 워커 부팅 속도. `--fork-session`은 멱등 재시도.

### 4.3 Antigravity 현황 (frontier 검증, 2026-05)

Google I/O 2026(5/19)에서 **Gemini CLI의 후계 = Antigravity CLI(`agy`)** 발표(Gemini CLI 2026-06-18 sunset 예정). **그러나 headless로 신뢰성 있게 쓰기 아직 부적합**: `--print`는 있으나 (a) JSON 구조화 출력 플래그 없음(Issue #7), (b) API 키 인증 미지원·키링 의존(Issue #78), (c) subprocess 통합 "awkward" 피드백, (d) MCP 공식 미확인.

→ **G1 결정**: Antigravity CLI는 **세 번째 워커로 보류**. Google 연동은 **Gemini API 직접 호출 또는 Antigravity Python SDK**로 대체. CLI가 API 키 인증 + `--print` JSON을 공식 지원하면 워커 추가(reversible, 1줄 라우팅 추가). *(주의: 이 Antigravity 일정은 조사 에이전트 보고이며 본 모델 컷오프 이후 — owner가 Google 공식으로 재확인 권장. `feedback_verify_frontier_models` 정합.)*

### 4.4 Hermes 역할 재정의

조사 결과 Hermes `delegate_task`는 **동일 프로세스 내 자식 AIAgent**지 외부 CLI subprocess 오케스트레이션이 아니다. SBU sitemap cron도 이미 false-pass로 ysh-server crontab 이관됨(5/20). → **G1 결정**: Hermes를 오케스트레이터로 승격하지 않음. `hermes gateway`(systemd, SQLite 세션, 멀티채널)는 **Telegram 게이트웨이 대안 후보로만 평가 보류**(현 sora 폴링이 이미 작동). Hermes 설치는 sunk-cost 보존, 신규 의존 추가 안 함.

### 4.5 오케스트레이터 = sora_engine 진화 + LangGraph 패턴

신규 프레임워크 통째 도입 대신, **이미 라이브인 sora_engine을 오케스트레이터-of-record로 진화**하고, 다단계·재개 필요 작업만 **LangGraph 스타일 상태머신 + SQLite 체크포인트**(§5.4 큐가 곧 체크포인트)로 모델링. 각 CLI 워커 호출 = 1 노드, 실패 시 노드만 재시도. (LangGraph 라이브러리는 선택 — SQLite 큐 + asyncio로 동등 구현 가능, 1인 운영 복잡도 최소화.)

---

## 5. 4대 하드닝 정밀 스펙 (owner 문제 2.1~2.4 응답)

> 전 항목 라이브 조사로 구현 가능 스펙(DDL·regex·FSM) 확보. 아래는 요지 + 정본 코드 위치. 상세 구현 코드는 본 문서 작성과 함께 조사된 레퍼런스 스펙을 `scripts/jarvis/` 구현 시 그대로 사용.

### 5.1 Telegram 게이트웨이 무결성 (문제 2.1)

| 하위문제 | 스펙 | 구현 |
|---|---|---|
| 409 Conflict | 단일 폴러 불변식 | `fcntl.flock(LOCK_EX\|LOCK_NB)` PID 파일; 부팅 시 `deleteWebhook` 선행; offset 영속 |
| 중복 유입 | update_id strict dedup | `OrderedDict` LRU + TTL(3600s, max 10K) + `offset=last_uid+1` SQLite 영속 |
| rate-limit 부재 | per-chat 토큰버킷 | owner: cap=5 refill=2/s, 비-owner: hard-reject. **LLM 호출 前** 게이트 → 비용폭주 차단 |
| "진행" 텍스트 취약 | inline keyboard FSM | `callback_data="approve:{nonce}"` (≤64B), 60s TTL, chat_id당 1 pending(신규 위험명령 → 이전 EXPIRED), `answerCallbackQuery` 즉시 |

**승인 상태머신**: `IDLE → PENDING_APPROVAL → (CONFIRMED→EXECUTING→IDLE | REJECTED | EXPIRED)`. 위장 탭(다른 user의 callback) 차단: `approval.chat_id == callback.from.id` 검증.

**호스트 선택**: always-on Linux(ysh-server)는 NAT 뒤 → **long-polling 권장**(webhook의 공인 IP+TLS 부담 회피). 단 §9 노출포트 정리 선행.

### 5.2 환각 차단 + warn-then-obey 라우터 (문제 2.2)

기존 `command_governor.classify_risk`(11 패턴) → **확장**:

1. **결정론 우선**: 위험 분류·승인은 regex/코드. LLM은 NL 이해·포맷만. (이미 라이브 학습 §2)
2. **주입 메타문자 선차단**: `[;&|`$]|\$\(|\$\{|&&|\|\||curl.*\|\s*sh` 탐지 시 CRITICAL.
3. **allowlist 바이너리 매칭** (신규, 핵심): `shlex.split` → `ALLOWED_COMMANDS` dict(바이너리 절대경로 + 허용 플래그/서브커맨드/경로 prefix). `shell=False` 절대. 최소 env(PATH 하이재킹 방지). 미허용 → `ValueError`.
4. **재입력 강제**: 모호한 위험 NL("회사 PC 정리해줘") → LLM에 위임 X → "정확한 대상·옵션을 다시 입력하세요" 결정론 반환.
5. **threat model**: command injection(`;&&|$()` 백틱) / regex bypass(`re.ASCII` 병용, null byte는 shlex가 차단) / path traversal(`\.\./` + resolve prefix 검증) / 길이 DoS(>2048 차단). **bash + PowerShell 양쪽** 패턴(`Remove-Item -Recurse`, `Invoke-Expression`, `format X:`).

정본: `command_governor.py` 확장 + 신규 `executor.build_safe_argv()`.

### 5.3 tree-sitter TS/TSX Outline IR + WSL 경로 (문제 2.3)

- **추출기**: `py-tree-sitter` + `tree-sitter-typescript` (`.ts`→`language_typescript()`, `.tsx`→`language_tsx()` — 반드시 분리). S-expression 쿼리로 `interface_declaration`/`type_alias_declaration`/`function_declaration`/`arrow_function`/`class_declaration`/`method_definition` 추출 → **Typed Outline IR** `{kind,name,line,exported,file}`. Hook = `^use[A-Z]`, Component = 대문자 시작 function. `node_modules`/`.next`/`dist` 제외. (정확 타입정보 필요 시 tsc Compiler API 대안, but outline엔 tree-sitter로 충분.)
- **WSL 경로 가드**: `wslpath -u/-w` 양방향 정규화 + `lru_cache`. **파일락/mmap/sqlite/socket은 `/mnt/` 경계 금지**(VirtioFS 락 프로토콜 불일치) → `PathGuard.check(op)`가 `/mnt/c/...`에서 이 연산 시 `ValueError`. 에이전트 상태/큐 DB는 **WSL native `/home`·`/var/lib`에만**. 공백 경로는 `wslpath`가 안전 처리.

정본: 신규 `scripts/jarvis/ts_outline.py` + `wsl_paths.py`. (전 SBU 코드를 에이전트가 "API로 읽히게" — 에이전트 가독성 §, 2026-05-20 audit와 연계.)

### 5.4 SQLite 내구성 큐 + fencing lease + KILL_SWITCH (문제 2.4)

`governor_pending.json`(단일파일) → **SQLite WAL**.

```sql
PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;
PRAGMA busy_timeout=10000; PRAGMA foreign_keys=ON;
-- jobs(id, created_at, command, safe_argv, status, risk_level, chat_id,
--      confirm_id, fencing_token, worker_id, lease_expires, result_*, exit_code)
-- approvals(id=confirm_id, job_id, requested_at, expires_at, decided_at, decision, telegram_cb_id)
-- audit(id, ts, job_id, event, agent_id, fencing_tk, detail)
-- kill_switch(id=1, active, activated_by, activated_at, reason)
-- fencing_sequence(id=1, next_val)  -- 단조증가 발급기
```

- **fencing token (Kleppmann)**: `claim_job` 시 `UPDATE fencing_sequence SET next_val=next_val+1 RETURNING next_val`. `complete_job`은 `WHERE worker_id=? AND fencing_token=?` — **stale 워커 커밋은 rowcount=0으로 거부**.
- **`BEGIN IMMEDIATE`**: 읽기→쓰기 업그레이드 시 SQLITE_BUSY 방지. WAL + busy_timeout 10s. 예외 시 ROLLBACK.
- **KILL_SWITCH**: 단일 TX로 `kill_switch.active=1` + running→cancelled + `lease_expires=0`. 워커 `claim_job` 첫 쿼리가 kill_switch 확인 → poll 주기 ≤0.5s → **0.5초 내 전 플릿 동결**. 실행 중 subprocess는 worker_id로 SIGTERM.

정본: 신규 `scripts/jarvis/job_store.py` + `kill_switch.py`. 텔레그램 한 단어(`/kill`)가 즉시 트리거.

---

## 6. 메모리 / 초개인화 / 컨텍스트 무결성

owner: "모든 대화 기억 + 초개인화 + 컨텍스트 장애 없이 + 자가발전". sora 5/4 사건(cron probe가 history 밀어냄)의 구조적 해결.

### 6.1 스택 = Graphiti(기존 Neo4j) + Qdrant + KURE-v1

조사 비교(LongMemEval): **Graphiti 63.8% > Letta ~55% > Mem0 49%**. Graphiti 채택 근거: (1) Neo4j 1st-class(기존 온톨로지 노드와 공존), (2) bi-temporal(구정보 자동 무효화 = 자가발전 핵심), (3) 커스텀 embedder 주입 → **KURE-v1(1024-dim 한국어)** 그대로, (4) JSONL 온톨로지를 `EpisodeType.json`으로 ingestion.

- **자가발전**: 동일 엔티티 새 정보 → 이전 `valid_to`=now + 새 엣지. owner 선호·프로젝트 상태·결정이 자동 갱신, outdated 주입 방지.
- **AuraDB 소멸 대응**: 클라우드 미러(`394b2602`) NXDOMAIN 확정 → **로컬 Neo4j(Docker, scaffold 기존) 또는 desktop-home 로컬**로 Graphiti 백엔드 단일화. 로컬 JSONL은 SSOT 유지.

### 6.2 3-tier 컨텍스트 예산 (컨텍스트 장애 방지)

Letta 아이디어 자체구현: **L1 Core**(owner 프로필+현 작업, 항상 인컨텍스트) / **L2 Episodic**(최근 N턴 슬라이딩, ~40K 예산) / **L3 Archival**(Graphiti 검색, on-demand). cron probe 같은 노이즈는 episodic에서 자동 필터(이미 sora 라이브 fix). 예산 초과분은 archival에 이미 영속 → 유실 0.

### 6.3 기존 자산 통합

`OWNER_PROFILE.md` + memory 파일 8종 + ontology v0.4 + assistant_memory를 Graphiti episode로 점진 ingestion. personal/(법무·금융)은 **절대 분리**(§9, `PERSONAL_CONTEXT_ROUTING.md`).

---

## 7. 로컬 추론 + 멀티모달 생성 (RTX 4070 SUPER 12GB)

> 핵심 현실: **12GB는 단일슬롯 시분할 GPU**. LLM·이미지·비디오는 VRAM 공존 불가 → 온디맨드 모델 스왑(NVMe에서 ~8-12s 재로드).

### 7.1 always-on tier (GPU ~10-12GB)

| 컴포넌트 | 선택 | VRAM | 비고 |
|---|---|---|---|
| 주 LLM (도구호출) | **Qwen3-14B Q4_K_M** (GGUF) | 8.5GB | MCP 네이티브 학습, Tau2-Bench 65.1. 8 KV-head GQA → KV cache 경량. **Q8/Q4 KV cache 필수**(12GB) |
| 더 긴 컨텍스트 필요 시 | Qwen3-8B Q4 | 4.8GB | ~85K 토큰, 도구호출 거의 동급 |
| 서빙 | **Ollama**(최소운영) 또는 TabbyAPI+EXL2(~25% 빠름) | — | OpenAI-호환 API, WSL2 CUDA 성숙 |
| 임베딩 | **BGE-M3** GPU 1.2GB + **KURE-v1** CPU | 1.2GB | 한국어 RAG |
| 리랭커 | bge-reranker-v2-m3 | CPU | BERT급 ~50ms/q |

권장 always-on 예산: Qwen3-14B(8.5) + BGE-M3(1.2) + KV(~2.3, Q4 cache ~56K) + overhead(0.3) ≈ **12.3GB(경계)**. OOM 시 BGE-M3 CPU 이동 또는 주 LLM을 Qwen3-8B로.

### 7.2 온디맨드 tier (LLM 언로드 후 스왑)

| 용도 | 선택 | VRAM | 시간 |
|---|---|---|---|
| 이미지 빠름 | SDXL FP8 | ~5GB | 15-20s/img |
| 이미지 고품질 | Flux.1 Schnell GGUF Q5 | ~10GB | 15-25s (4-step) |
| 이미지 최고 | Flux.1 Dev GGUF Q5+FP8 T5 | ~11GB | 45-90s |
| 비디오 빠름 | **LTX-Video 0.9.8 13B FP8** | ~12GB | 7-9분/5s클립 |
| 비디오 고품질 | Wan2.2 14B GGUF Q4 + T5 CPU offload (Wan2GP) | ~8GB+RAM | 10-15분/5s |
| STT | faster-whisper large-v3-turbo int8 | 1.5GB / CPU | ~12× realtime |
| TTS 한국어 | **XTTS-v2** (CPU) 또는 Piper(KO 커뮤니티) | CPU | 음성 자비스 |

owner ComfyUI 기존 가동 → 워크플로우 재사용. 비디오는 background 작업 불가(7-15분 GPU 독점) → on-demand만.

### 7.3 로컬 vs 클라우드 분담

| 로컬(RTX 4070) | 클라우드(escalation) |
|---|---|
| routine 명령·자동화·도구호출·분류 | 장문(>100K)·고난도 판단·창작 |
| 프라이버시·오프라인 fallback | 대규모 repo 전체 컨텍스트 코딩 |
| 한국어 RAG(KURE+BGE) | frontier 비판·뉘앙스 |
| 이미지/비디오/STT/TTS | 속도 critical 시 상용 API |

**증설·클라우드 트리거**(owner 필요 시): (a) 비디오를 일상화하려면 24GB+ GPU 또는 상용 API, (b) 더 큰 로컬 LLM(30B+) 원하면 24GB GPU, (c) always-on GPU 작업이 desktop-home 로그온 의존을 벗어나야 하면 24/7 GPU 노드. 현재는 **무료·로컬 우선** 원칙 충족.

---

## 8. 도구 호출 무결성 (수십개 자체 도구 환각 없이)

owner: "수십가지 자체 도구를 환각 없이 호출하고 자연스럽게 수행". 3중 장치:

1. **callable_tools registry** (기존 `.agent/registries/callable_tools.json`) = 도구 SSOT. MCP 8 core(github/supabase/filesystem/memory/cloudflare/vercel/scheduled-tasks/thinking) + 결정론 fastpath 도구(remote_pc_command 등).
2. **MCP 우선 + 스키마 검증** (CLAUDE.md 0-B 기본 레이어). 과잉 도구 노출 = 정확도 저하 → 25→8 큐레이션 기 적용.
3. **결정론 fastpath** (환각 차단): "device에서 cmd 실행"·"진행"·이미지 생성 같은 명시 패턴은 LLM execute 결정 우회 → 직접 도구 호출. 모호 NL은 재입력 강제(§5.2).

**PC/크롬 제어**: PC Agent Hub(라이브) + Claude-in-Chrome MCP(navigate/computer/read_page/form_input). 둘 다 governor + 2-phase 게이트 하류.

---

## 9. 보안 / 거버넌스 / 운영

| 항목 | 조치 |
|---|---|
| **거버넌스 정본 복원** | `project_jarvis_governance.md` 메모리 신규 + MEMORY.md 포인터 (본 세션, §1.3 갭) |
| Gateway 보안 | owner chat_id allowlist(라이브) + 토큰버킷 + NEO_ALERT_BOT 토큰 회전(잔존 권고) |
| ysh-server 노출포트 | Qdrant 6333/6334 + :7700 hub가 public IP 1.225.23.2 직결(5/20 발견) → **ufw로 Tailscale-only 제한** P0 |
| 미상 사용자 | ysh-server `jhhan` claude `--dangerously-skip-permissions` 세션(5/20) → owner 확인 |
| personal 분리 | 법무·금융 `personal/`은 메모리·shared prompt 절대 미유입 (`PERSONAL_CONTEXT_ROUTING.md`) |
| API 키 한도 | GCP budget ₩100K × 2 + battlefield 차단 유지. 신규 키 application restriction 의무 |
| 감사 | 전 명령 audit JSONL + SQLite audit 테이블. 주간 리뷰 |
| secret | `.env*` Read 금지(grep+redact 강제, 5/18 룰). gitleaks 22 repo 활성 |

---

## 10. 단계별 로드맵 (무료·오픈소스·reversible)

| Phase | 내용 | 위험 | 신규 의존 | 상태 |
|---|---|---|---|---|
| **0. 정본/안전** | governance memory 복원 + ysh ufw + NEO_ALERT 토큰 회전 | 낮음 | 0 | 본 세션 일부 |
| **1. 게이트웨이 하드닝** (§5.1) | 단일폴러 + dedup + 토큰버킷 + inline approval FSM | 중 | py-only | 다음 |
| **2. 내구성 큐** (§5.4) | SQLite WAL + fencing + KILL_SWITCH (`governor_pending.json` 대체) | 중 | sqlite(내장) | 다음 |
| **3. 오케스트레이션 배선** (§4) | sora→Claude/Codex CLI 워커 라우팅 + 구조화 캡처 + 2-phase | 핵심 | CLI(설치됨) | P1 |
| **4. 메모리** (§6) | Graphiti(로컬 Neo4j) + KURE embedder + 3-tier context | 중 | graphiti-core | P1 |
| **5. 로컬 tier** (§7) | LL-1 안티바이러스 예외(owner 30분) → Qwen3-14B Ollama + ComfyUI 스왑 스케줄러 + 음성 | owner 의존 | ollama(있음) | P2 |
| **6. 정규화·자가발전** (§5.3) | ts_outline + WSL guard + reflection 루프 | 낮음 | tree-sitter | P2 |

비용: Phase 0-4 = **$0 추가**(전부 OSS + 정액 구독). Phase 5-6 = $0(로컬). 증설/클라우드는 owner 트리거(§7.3)만.

---

## 11. G1 자율 결정 박제 (한 줄 reversible) + owner 게이트

| ID | 결정 | reversible |
|---|---|---|
| G1-J1 | 재작성 X — 라이브 sora/hub/governor 진화 | 설계 선택, 코드 무변경 |
| G1-J2 | 2-Phase Sovereignty 채택 (숙의 반론 + 집행 복종) | §2 문서 |
| G1-J3 | 환각=결정론 차단 유지·강화 (allowlist 바이너리) | command_governor 확장 |
| G1-J4 | 게이트웨이 long-polling 유지 (webhook X, NAT) | gateway 설정 1줄 |
| G1-J5 | 큐 = SQLite WAL+fencing (governor_pending.json 대체) | DB 파일 삭제 = 롤백 |
| G1-J6 | 메모리 = Graphiti on 로컬 Neo4j + KURE | graphiti 미설치 = 미영향 |
| G1-J7 | 로컬 주 LLM = Qwen3-14B Q4 (8B fallback) | ollama pull/rm |
| G1-J8 | **Antigravity CLI 워커 보류** (headless 미성숙) → Gemini API 직접 | 라우팅 1줄 추가 |
| G1-J9 | Hermes 오케스트레이터 승격 X (게이트웨이 보류) | 설치 보존, 의존 0 |
| G1-J10 | governance memory 정본 복원 (§1.3 갭) | 메모리 파일 |

**owner 결정 게이트 (G2 — owner 1회 입력 후 영구 자동)**:
1. **LL-1 안티바이러스 예외** (30분) — 로컬 LLM tier(Phase 5) 차단 해소. owner만 가능.
2. **로컬 Neo4j 가동 위치** — ysh-server Docker vs desktop-home (Graphiti 백엔드). AuraDB 소멸 대체.
3. **ysh-server ufw Tailscale-only** — public IP 노출포트 차단 (P0 보안). owner sudo.
4. **NEO_ALERT_BOT_TOKEN 회전** — 5/3 stdout 노출 잔존. BotFather.
5. (선택) GPU 24/7 always-on 원하면 증설/클라우드 — 현 무료 원칙선 충분.

---

## 12. 부록 — 출처 (라이브 조사 검증)

- Claude Code CLI: code.claude.ai/docs/en/cli-reference (`-p`/`--output-format json`/`--bare`/`--resume`)
- Codex CLI: developers.openai.com/codex/noninteractive (`codex exec --json --sandbox`)
- Antigravity: developers.googleblog.com (Gemini CLI→Antigravity CLI 전환), GitHub Issue #7/#78 (headless 한계)
- Hermes Agent: hermes-agent.nousresearch.com/docs (gateway/cron/memory/hooks; delegate_task in-process)
- 오케스트레이션: LangGraph(Postgres checkpoint) vs OpenAI Agents SDK vs Mastra 비교
- Qwen3: qwenlm.github.io/blog/qwen3 / apxml.com (14B/8B VRAM·KV cache)
- 서빙: Ollama vs llama.cpp vs vLLM vs TabbyAPI(EXL2) 2026 비교
- 이미지/비디오: Flux GGUF 12GB / LTX-Video·Wan2.2 VRAM (willitrunai.com)
- 음성: faster-whisper / XTTS-v2 / Piper (한국어)
- Telegram: core.telegram.org/bots/api#getupdates, /bots/faq(rate limit), /api/bots/buttons(inline)
- 분산락: Kleppmann "How to do distributed locking" (fencing token)
- SQLite: sqlite.org WAL / BEGIN IMMEDIATE / busy_timeout
- tree-sitter: tree-sitter.github.io/py-tree-sitter, pypi tree-sitter-typescript
- 메모리: github.com/getzep/graphiti (bi-temporal, Neo4j 1st-class, LongMemEval 63.8%), Mem0/Letta 비교

---

**Cold honest**: 본 v2는 **설계·연구**다. 라이브 가동 코드 0줄 신규(governance memory 복원 제외). 70% 백본은 실측 라이브, 30%(게이트웨이 하드닝·큐·오케스트레이션·메모리·로컬tier)는 구현 대기. Antigravity 일정·로컬 모델 수치는 조사 에이전트 보고(본 컷오프 이후 일부) — owner 공식 재확인 권장. Phase 1부터는 owner "진행" 시 G1 자율 구현 가능.

👤 Strategy Lead Claude Opus 4.7 (1M)
