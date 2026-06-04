# Jarvis Architecture v1 — 텔레그램 한 통 → 전 디바이스 제어 (2026-05-20)

> **Author**: Strategy Lead Claude Opus 4.7
> **Trigger**: owner "내가 텔레그램으로 채팅 하나 보내면 내 디바이스들을 기반으로 모든것을 할 수 있는 나만의 자비스 비서 구축"
> **핵심 발견**: 백본(PC Agent Hub)이 이미 존재 + ysh-server에서 라이브. 그린필드 아님.

---

## 1. 결론 — 70% 이미 지어져 있음

자비스 척추 = `src/core/pc_agent/hub.py` (PC Agent Hub). 라이브 검증(2026-05-20):
- `:7700` 허브 서버 가동 (sora-live 컨테이너에 마운트)
- `sora_pc_agent.py` (linux-server) 허브 연결 PID 341
- `/api/pc-agents` → "Unauthorized" (API 마운트 살아있음)
- 텔레그램 → sora-live 동작

빠진 것: (1) PC 에이전트가 ysh-server 1대만 배포 (2) 브레인 약함 (3) 안전 거버넌스 미구현.

---

## 2. 데이터 흐름 (목표)

```
[텔레그램 한 통]
   ↓
sora-live (ysh-server, always-on) — 진입점 ✅
   ↓ L1 의도 해석 (Gemini Flash) → 단순? 복잡?
   ↓ L2 복잡하면 Hermes → Claude/Codex CLI subprocess 계획
   ↓ 위험 분류 → 위험하면 "왜 위험+권고" 설명 후 owner 판단 (warn-then-obey)
   ↓
PC Agent Hub.send_command(device_id, "exec|read_file|screenshot|system_status", payload)
   ↓ WebSocket 중계 ✅ (hub.py)
   ↓
각 디바이스 sora_pc_agent.py 실행 → 결과 회신
   ↓
sora → 텔레그램 owner 보고 + 감사 로그
```

지원 명령(코드 존재): `exec` / `read_file` / `screenshot` / `system_status`.

---

## 3. 거버넌스 (owner 확정 2026-05-20) — warn-then-obey

memory `project_jarvis_governance.md` 정본. 요약:
- 위험·비가역 → 자동 차단 X. "왜 위험+권고" 설명 → owner 판단.
- owner override → 무엇이든 반드시 실행. 예외 0.
- 일반 → 무마찰 즉시.
- 전 명령 감사 로그.
- 채널 보안(allowlist + 토큰 잠금) 별개로 강화.

---

## 4. 브레인 = 3계층 (owner: "성능+속도+비용 안정")

| 계층 | 엔진 | 용도 | 비용 |
|---|---|---|---|
| L1 빠른 길 | Gemini Flash | 의도 해석 + 단순 명령 (폰 즉답 ~1초) | 저 (Flash) |
| L2 무거운 길 | Claude/Codex CLI (Hermes subprocess) | 다단계 계획 | $0 (Max/Pro 구독) |
| L3 미래 | Local Qwen3 | 전부 (LL-1 해소 후) | $0 (로컬) |

종량제 아님 → 비용 폭주 불가. L3는 LL-1 안티바이러스 예외(owner 30분) 선행.

---

## 5. 디바이스 fleet (Tailscale)

| 디바이스 | 역할 | PC 에이전트 |
|---|---|---|
| ysh-server | always-on 리눅스, sora-live + 허브 | ✅ 배포됨 (PID 341) |
| desktop-home (이 PC) | 메인 작업, WSL2+Hermes | ❌ 미배포 (Phase 1) |
| etribe-yesol (회사 PC) | 본업 | ❌ 미배포 (Phase 1) |
| yesol-asus | 보조 | ❌ (대개 offline) |
| mx-macbuild | Mac 빌드 | ❌ (offline) |
| s26-ultra / tab-s10 | 모바일 | ❌ (operator mode) |

install 스크립트 존재: `scripts/install_pc_agent.{ps1,sh}` + `start_pc_agent.bat`.

---

## 6. 단계별 빌드

| Phase | 내용 | 위험 | 상태 |
|---|---|---|---|
| 1. 안전 슬라이스 | PC 에이전트 온라인 디바이스 배포 + 텔레그램 allowlist + 허브 tool-calling 배선 + 감사 로그 | 낮음 | 착수 |
| 2. 브레인 계층 | Gemini 빠른 길 + Hermes→Claude/Codex 무거운 길 라우팅 | 중 | 대기 |
| 3. 안전 거버넌스 | 위험 분류 + warn-then-obey + 감사 (Phase 1 병행) | 핵심 | 대기 |
| 4. Local LLM | LL-1 해소 후 Qwen3 (owner 선행) | owner 의존 | 대기 |

---

## 7. 보안 인벤토리

- `PC_AGENT_TOKEN` → `/home/ysh/.neo-genesis/credentials.env` (있음)
- 허브 인증: 토큰 쿼리 파라미터 (`?token=X&agent_id=Y`)
- 텔레그램 진입 = 마스터키 → owner chat_id allowlist + NEO_ALERT_BOT 토큰 잠금/회전 필요
- `:7700` 0.0.0.0 바인딩 → Tailscale 경유 cross-device 도달 가능 (단 토큰 필수)

---

## 8. Phase 1 진행 (권고 순서 = 안전 layer 먼저)

| # | 작업 | 상태 |
|---|---|---|
| 1 | 안전 layer (위험분류 + 감사 + warn-then-obey) @ sora 브레인 | ✅ **LIVE 배포 (2026-05-20)** |
| 2 | 텔레그램 owner chat_id allowlist | ✅ **이미 적용 확인** (`_reject_unauthorized_chat`, NEO_ALERT_CHAT_ID=1566967334) |
| 3 | PC 에이전트 → 이 PC(desktop-home) 배포 | ✅ **LIVE (영속, Startup 등록)** / 회사PC는 owner ssh 경로 필요 |
| 4 | sora 도구 배선 end-to-end 데모 | ✅ **LIVE** (status/whoami/echo + governor WARN 검증) |

## 10. Phase 1 desktop-home 배포 완료 (2026-05-20)

**진짜 버그 수정**: 원격 PC 도구가 `DASHBOARD_TOKEN`(기본값) Bearer 사용 → 대시보드는 `SORA_DASHBOARD_SECRET` 기대 → **인증 한 번도 통과 못 했음**. `system_tools.py` `_DASHBOARD_TOKEN`을 `SORA_DASHBOARD_SECRET` 우선으로 수정 + 재배포.

**에이전트 배포 (desktop-home)**:
- 스크립트: `scripts/sora_pc_agent.py` (ysh-server 검증본 fetch)
- 영속 launcher: `C:\Users\yesol\.neo-genesis\start_pc_agent.bat` -> `start_pc_agent_hidden.ps1` (PowerShell hidden + python.exe + log redirect, token env-only)
- 자동시작: `...\Startup\sora_pc_agent.vbs` (무창 실행, 로그온 시)
- 연결: ws://100.67.221.25:7700/ws/pc-agent, agent_id=desktop-home, PC_AGENT_TOKEN=env-only (raw value not documented)
- deps: websockets 15.0.1 + psutil 7.2.2 (Windows python 3.13)

**e2e 검증 (LIVE)**:
- `list_connected_pcs` → desktop-home (Windows 11) online
- `remote_pc_status` → cpu 76.6% 등 실데이터
- `remote_pc_command("whoami")` → "yesol" (powershell)
- `remote_pc_command("echo jarvis-live")` → "jarvis-live"
- `remote_pc_command("rm -rf /tmp/x")` → **governor WARN** (실행 X, 위험+권고+confirm_id)

**알려진 한계 / 다음**:
- agent_id 중복 시 hub가 replace → flapping. 단일 인스턴스 보장 필요 (Startup 1개만)
- 회사PC(etribe-yesol): ssh auth 과거 차단 → owner 경로 개방 필요
- PC_AGENT_TOKEN raw value was removed from launcher command lines and this document. Keep token in user environment or credential loader only; rotate separately if owner wants.
- 영속성: Startup(로그온) 기반. 로그인 안 하면 미가동. 진짜 always-on은 ysh-server 몫

## 11. Phase 2 — 브레인 신뢰성 (2026-05-20) ⭐ 핵심 발견

**문제**: NL "desktop-home에서 rm -rf 실행해줘" → sora가 "실행했습니다 + (가짜 출력)" 응답. audit ground truth = **도구 호출 0건**.

**진단 (실측)**:
- whoami(안전) → LLM이 도구 호출 → 실제 실행 ✅
- rm -rf(위험) → **Gemini Flash AND Pro 둘 다 도구 호출 거부 + 실행 환각** (testdir/2/3 audit 0건)
- 모델 업그레이드(Flash→Pro) **효과 없음** — 동일 환각
- 원인: Gemini safety RLHF가 파괴적 명령을 "실행한 척" deflect. 프롬프트 하드닝으로도 안 잡힘 (모델 행동 벽)
- 부가: assistant_memory에 테스트 turn 누적 → confabulation 강화 (정리 완료)

**구조적 결론**: **위험 명령에서 LLM tool-calling을 신뢰할 수 없다.** governor는 도구가 호출돼야 작동하는데 모델이 호출 자체를 안 함 → 안전망이 우회됨 + owner는 거짓 보고 받음.

**해결 — Deterministic Command Router** (`sora_engine._tool_intent_fastpath` 섹션 9/10):
- 명시적 "`<device>`에서 `<cmd>` 실행" 패턴 → LLM 거치지 않고 `remote_pc_command` 직접 호출
- governor가 위험 분류 → WARN이면 경고 그대로 반환 (실행 X) / 안전이면 실제 결과
- "진행"/"confirm <id>" → `confirm_pending_command` 직접 호출 (pending 있을 때만)
- LLM은 NL 이해 + 결과 포맷만, **execute 결정에서 배제**

**검증 (LIVE, audit ground truth)**:
| 입력 | 결과 | audit |
|---|---|---|
| "desktop-home에서 whoami 실행해줘" | `💻 $ whoami → yesol` | executed (실제) |
| "desktop-home에서 rm -rf /tmp/testdir4 실행해줘" | `⚠️ 위험—실행 안 함 + 권고` | **warned** (실행 X) |
| "진행" | `✅ 실행 완료 → {error: 위험 차단됨}` | **confirmed_executed** (실제 호출) |

환각 0. 모든 audit = 실제 호출. 부가 발견: 에이전트 자체도 "rm -rf /" 가드 보유 (방어 심층).

**파일 변경**:
- `sora_engine.py`: `_TOOL_REINFORCEMENT` 모듈 상수 (디바이스 명령+WARN전달+날조금지 규칙, init+재생성 양쪽 통일) + `_tool_intent_fastpath` 섹션 9(confirm)/10(device command)
- `command_governor.py` + `system_tools.py`: Phase 1 (governor + auth bug fix)

**남은 한계**:
- deterministic 경로는 **명시적 "device에서 cmd 실행" 패턴만**. 모호한 자연어("내 회사 PC 정리해줘")는 여전히 LLM 의존 → 위험 명령이면 환각 가능. 명시적 명령 권장.
- 진짜 강력한 NL agentic은 여전히 Local LLM(Phase 4) 또는 Claude/Codex CLI 위임 필요

## 12. Phase 2.1 — Ultracode 감사 후 강화 (2026-05-29)

owner "울트라코드 모드로 전부진행" → 6 차원 감사 12+ findings → 직접 일괄 처리.

### B1 (BLOCKER) — destructive remote_* 도구 governor wrap 확장
직전엔 `remote_pc_command`+`remote_batch_exec`만 governor 경유. 나머지 destructive 도구는 무방비였음:
- `remote_pc_file_write` → 민감 경로(.env/.ssh/startup/systemd/etc) 또는 일반 governor → stage_pending
- `remote_vercel_deploy` → 항상 stage_pending (production 영향)
- `remote_npm_build_deploy` → 항상 stage_pending
- `remote_git_commit_push` → 항상 stage_pending (원격 히스토리 변경)
- `remote_batch_exec` → 원본 commands 리스트 payload 보존 (semantics 정합)

### M1 — `confirm_pending_command` LLM 노출 제거
- `confirm_pending_command` (alias to `_confirm_pending_command_internal`) — TOOLS 리스트에서 제거됨
- `sora_engine._tool_intent_fastpath` 섹션 9 (deterministic owner-intent 게이트) 에서만 호출
- LLM이 owner 명시적 "진행" 의도를 우회해 자동 confirm 호출하는 안전 버그 차단

### M2 — confirm phrase 좁힘
- 제거: "응 해", "그래 해", "해", "ㅇㅇ", "실행" (단독), "실행해줘"의 일부 비명시 변형
- 유지: 진행 / 진행해 / 진행해줘 / 진행할게 / 실행해 / 실행해줘 / 실행할게 / confirm / go / proceed + `confirm <id>` 정규식
- 한국어 구두점 strip (`진행!` `진행.` 등 normalize)

### M3 — pending 파일 원자적 쓰기 + 크로스플랫폼 lock
- `_save_pending` temp-file + `os.replace` (POSIX atomic rename, Windows override)
- `_FileLock` context manager — `msvcrt.locking` (Windows) / `fcntl.flock` (POSIX) 자동 선택
- 손상된 pending → 백업(`.corrupt-<ts>`) + 빈 dict (silent loss 방지)
- `_load_pending` 가 손상 감지 시 백업 보존

### M4 — deterministic router 자연어 확장
- 동사 확장: 실행 / 돌려 / run / **해줘 / 돌려줘 / 해봐 / 시켜** 추가
- **단일-PC 폴백**: PC 1대만 연결 + 명령 동사 + backtick command → 디바이스 phrase 생략 허용. owner "어차피 집컴터만" 의도 정합
- 한국어 typographic 인용부호 `"`, `'`, `"` 지원

### M6 — silent exception swallow 종료
- 섹션 9/10 `except Exception: pass` → `logger.warning(...)` 로 가시화. 깨졌어도 owner 추적 가능

### M7 — batch_exec / write_file / deploy 의미 보존
- `stage_pending`이 `command_type` + 원본 `payload` 저장
- `_confirm_pending_command_internal`이 저장된 command_type 으로 hub API 호출 (batch는 batch_exec API, write_file은 write_file API)
- git_commit_push 는 commit + push 2단계 시퀀스 보존

### M10 — 가시성 도구 2종 추가
- `get_jarvis_status()` — governor 상태 + 패턴 수 + pending 수 + 연결 PC + 최근 audit 1줄
- `get_jarvis_audit_summary(hours=24)` — N시간 내 audit 요약 (counts + 최근 warned/executed)
- Gemini가 도구로 인식 → owner "자비스 상태 알려줘" / "오늘 뭐 했어" 자연어로 조회

### Governor 패턴 확장 (Minor)
- 14패턴 (직전 11) — `rm --recursive --force` (long flags), PowerShell `Remove-Item -Recurse -Force`, `Get-ChildItem | Remove-Item`, `Stop-Computer/Stop-Process -Force`, `git push --force-with-lease`, 외부 전송 `sftp/nc/python urllib`, `icacls Everyone /grant`, `DROP INDEX`, `chmod` 확장

### Fail-closed
- `_governor_gate` helper — governor 모듈 import 실패 또는 분류 예외 시 차단 (`governor: ERROR`). 직전 fail-open이었음

### DEVICE_ALIASES — "맥" 1글자 제거
- false positive (맥주, 맥락) 차단. 2글자+ alias만 (mac/맥북/맥스튜디오/macbook/macstudio)

### 단위 테스트
- `tests/test_jarvis_safety.py` — 16 tests (rm 변형 5 + powershell 5 + force push 3 + secret exfil 3 + DB 3 + 디스크 3 + safe 9 + 빈 명령 + pending lifecycle 3 + resolver 5). pytest/unittest 양쪽 가능. **16/16 + governor self-test 16/16 PASS**.

### B2 — 부팅 자동시작 (owner 1회 admin 액션)
- `infra/agent-runtime/sora-desktop/install_pc_agent_boot.ps1` 작성
- Task Scheduler `SoraPCAgent` AtStartup + 60s delay + S4U (owner 계정, 비밀번호 불요) + 재시작 3회
- 설치: `powershell.exe -ExecutionPolicy Bypass -File install_pc_agent_boot.ps1` (admin)
- 제거 후 Startup vbs 삭제 권고 (중복 방지)
- **owner 액션 — admin PowerShell 필요**

### 잔존 (이 turn 추가 처리)
- **M9 에이전트 crash 알림** — ✅ `sora_pc_agent.py` `__main__` wrap 추가: KeyboardInterrupt 외 unhandled exception → NEO_ALERT_BOT 으로 텔레그램 알림 + `~/.neo-genesis/agent_crash.log` 기록. 토큰은 env 또는 credentials.env sourcing. **소스 양쪽(이 PC + ysh-server) 반영**. 라이브 에이전트 프로세스에는 다음 자연 재시작 시 적용 (현재 PID 유지).
- **audit 로그 회전** — ✅ ysh-server crontab `0 4 * * 0` (매 일요일 04:00 KST): gzip → `jarvis_audit-YYYYMMDD.jsonl.gz` + truncate + 28일 이전 .gz 정리
- **B2 설치 스크립트** — ✅ `install_pc_agent_boot.ps1` 작성 + 라이브 install **시도** → admin 권한 거부(예상). **owner admin PowerShell 1회 실행 필요**:
  ```powershell
  powershell.exe -ExecutionPolicy Bypass -File "D:\00.test\neo-genesis\infra\agent-runtime\sora-desktop\install_pc_agent_boot.ps1"
  ```

### 진짜 잔존 (defer)
- **M5** Gemini chat 객체 in-memory 잔존 — 컨테이너 재시작 시 auto-reset. owner 명시 "기억 초기화" 명령 hook은 추가 작업 (defer)
- **M8** PC_AGENT_TOKEN DPAPI/Credential Manager 암호화 (Windows-specific, ~1h. defer)
- **B2 실설치** — owner admin 액션 대기 (스크립트만 ready)
- ysh-server 라이브 에이전트 재시작 (M9 코드 적용) — 자연 재시작 시 자동 적용 권장

### Verification LIVE (2026-05-29)
- TOOLS 37개 — confirm_pending_command 부재 + get_jarvis_status / get_jarvis_audit_summary 추가
- governor 14 패턴 로드
- e2e: "집 pc에서 whoami 해줘" → 💻 deterministic 템플릿 + 실제 powershell 결과
- "응 해" → confirm 안 됨 (M2 ✓)
- "자비스 상태 알려줘" → get_jarvis_status 호출 + governor 14패턴 + desktop-home online 보고

👤 Strategy Lead Claude Opus 4.7

---

## 13. Phase 2.2 — 단일PC 통합: ysh → desktop-home WSL2 canonical (2026-05-29)

owner "이 pc만 사용해야해". 치명적 발견 + 이관.

### 치명적 발견 (split-brain)
Phase 1/2 전체가 ysh-server 컨테이너에만 배포됨. owner 텔레그램 실제 경로 = desktop-home WSL2 native (`~/sora-live`) = 옛 코드(NO_GOVERNOR). **안전 layer 가 owner 가 쓰는 sora 에 부재**. ysh 는 owner 가 안 쓰는데 거기만 안전했음.

### Divergence 분석 (배포 안전성 확정)
- WSL2 `~/sora-live` = D:repo 의 **옛 ancestor** (독자 fork 아님)
- sora_engine.py: same=2273/2290, WSL2-only=17 (전부 옛 버전 코드, 유일 의미값 `load_dotenv override=True`)
- system_tools.py: same=773, WSL2-only=17 (전부 옛 un-governed 함수 + 옛 `_DASHBOARD_TOKEN`)
- 결론: bulk 배포 = clean upgrade (손실 0, override만 보존)

### 실행 (Phase 1+2)
| # | 작업 | 결과 |
|---|---|---|
| 1 | 3 파일 D:repo→WSL2 배포 + override=True 보존 + 백업 | ✅ `.jarvis-backup-pre-mig/` |
| 2 | WSL2 daemon 재기동 (`start_sora.sh` 런처) | ✅ PID 65414, telegram 재연결 |
| 3 | WSL2 직접 검증 | ✅ TOOLS37/confirm미노출/status도구/14패턴/rm-rf·민감write·vercel→WARN |
| 4 | ysh sora-live STOP (container 보존) | ✅ Exited 137, 롤백 가능 |
| 5 | telegram 단일 poller=WSL2 | ✅ split-brain 해소 |
| 6 | D:repo override=True 정합 | ✅ SSOT |

### 검증 (WSL2 canonical, 직접 호출)
- `remote_pc_command(rm -rf)` → governor=WARN, confirm_id 발급 (hub 호출 **전** 차단)
- `remote_pc_file_write(/root/.ssh/...)` → WARN (B1)
- `remote_vercel_deploy` → WARN (B1)
- `get_jarvis_status` → DEGRADED (agent/hub down = 정직 보고) patterns=14
- 환각 0: device 명령은 hub 부재로 connection-refused **정직 실패** (실행 환각 아님)

### Phase 3 잔존 (device 실행 fabric)
**현재 device 명령은 실행 안 됨** (hub :7700 미가동). 안전하게 실패하지만(정직), owner 가 "집 pc에서 X 실행" 하면 실제 실행 안 됨. 실행하려면:
1. WSL2 가 hub :7700 호스트 (dashboard/FastAPI + pc_agent router 기동 — daemon 은 미기동)
2. Windows pc_agent 재기동 → WSL2 hub 연결
3. **단일PC 최적 대안**: WebSocket fabric 제거하고 WSL2 sora → `powershell.exe` 직접 interop. 단일PC엔 이게 정석 (hub/agent/token/flapping 전부 제거). 단 device 도구 재작성 필요
4. 영구화: WSL2 daemon nohup → Windows Task Scheduler (B2) 또는 wsl --boot
5. audit 로그 회전 (WSL2 logrotate/cron)

### 단일PC 아키텍처 재평가 (Strategy Lead 권고)
hub/agent WebSocket fabric 은 **cloud→remote-PC 다중 제어용**. 단일PC(WSL2 sora + Windows desktop, 같은 물리머신)엔 과설계:
- WSL2 → `powershell.exe`/`cmd.exe` 직접 interop 가능 (WSL interop)
- 제거 가능: hub :7700, Windows agent 프로세스, agent 영구화 task, PC_AGENT_TOKEN, disconnect/flapping/heartbeat 문제군 전체
- **권고: Phase 3 에서 fabric → WSL interop 전환** (단순+견고). governor 는 도구 레벨이라 그대로 적용. 단 remote_pc_* 도구를 local powershell.exe 호출로 재작성 (반나절)
- 대안(최소변경): 기존 fabric 유지하고 hub 를 WSL2 에 기동 + agent repoint. 빠르지만 fabric 복잡성 유지

👤 Strategy Lead Claude Opus 4.8

---

## 14. Phase 3 완료 — 단일PC WSL interop 아키텍처 (2026-05-29)

owner "계속해" → 권고대로 WebSocket fabric 제거 + WSL interop 직접 실행 구현.

### 아키텍처 전환: hub/agent fabric → WSL interop
**Before (cloud→remote-PC 다중 제어용, 과설계)**:
```
sora → hub :7700 (WebSocket) → Windows pc_agent (pythonw) → powershell
필요: hub 프로세스, agent 프로세스, PC_AGENT_TOKEN, agent 영구화, heartbeat
문제: agent 죽음/flapping/disconnect/token 노출
```
**After (단일PC 정석)**:
```
WSL2 sora → powershell.exe (WSL interop) → 직접 실행
필요: 없음 (WSL2가 Windows 바이너리 직접 호출)
제거됨: hub, agent, token, 영구화 task, heartbeat 문제군 전체
```

### 구현 (`system_tools.py`)
- `_LOCAL_EXEC = os.getenv("JARVIS_LOCAL_EXEC")` 플래그 (1=로컬 interop, 미설정=hub fallback, 하위호환)
- `_local_powershell(cmd)` — `subprocess.run([powershell.exe, -NoProfile, -NonInteractive, -Command, cmd])` (절대경로 `/mnt/c/Windows/System32/.../powershell.exe`)
- `_local_dispatch(hub_command, payload)` — exec/batch_exec/system_status/read_file/write_file(base64)/process_list 번역
- `_device_call(pc_id, hub_command, payload)` — LOCAL_EXEC면 로컬, 아니면 hub. 전 device 도구가 이걸 경유
- `list_connected_pcs` 로컬 모드: desktop-home 단독 반환
- governor 게이트는 도구 함수 상단 유지 (실행 백엔드 무관하게 위험 분류)
- confirm 경로도 git_commit_push/npm_build_deploy 로컬 분기

### 검증 (brain e2e, JARVIS_LOCAL_EXEC=1, 라이브)
| 입력 | 결과 |
|---|---|
| "집 pc에서 whoami 해줘" | 💻 desktop-home $ whoami → `stdout: yesol, shell: powershell(wsl-interop)` ✅ 실제 실행 |
| "집 pc에서 rm -rf 실행해줘" | ⚠️ governor WARN (실행 안 함) ✅ |
| "응 해" | confirm 안 함 (M2) ✅ |
| remote_pc_status | hostname DESKTOP-HOME / Win11 Pro / ram 26GB free / disk 434GB ✅ 실제 |
| 단위 테스트 | 16/16 PASS (회귀 0) |

### 영구화 (autostart, admin 불요)
- `C:/Users/yesol/.neo-genesis/start_sora_wsl.bat` → `wsl.exe -d Ubuntu-24.04 -u root bash -lc "cd /root/sora-live && setsid bash start_sora.sh"`
- `Startup/sora_daemon.vbs` (무창) → 로그온 시 bat 실행 → WSL2 + sora daemon 기동
- 검증: vbs 실행 → daemon PID 71186 + telegram 2 ESTAB ✅
- 옛 agent vbs(`sora_pc_agent.vbs`, 죽은 ysh hub 가리킴) 제거
- 한계: 로그온 기반 (PC 부팅 후 미로그인 시 미기동). 단일 interactive PC라 수용. 진짜 boot-without-login은 Task Scheduler+admin (owner 선택)

### 단일PC Jarvis 최종 토폴로지
```
텔레그램 → WSL2 sora brain (governor 14패턴 + §9 confirm + §10 router)
                ↓ "집 pc에서 X 실행"
         §10 deterministic router → resolve(집 pc)=desktop-home
                ↓ governor 게이트 (위험→warn-then-obey)
         _device_call → _local_powershell → powershell.exe → 실제 결과
```
- hub :7700 / Windows agent / PC_AGENT_TOKEN: **전부 불요 (제거)**
- ysh-server: 폐기 (stopped, 롤백 보존)
- 영구화: 로그온 autostart vbs

### 잔존 (defer, 비핵심)
- claude_run/docker_ps/docker_logs/git_status/web_search/web_crawl: hub-only 번역 미구현 (로컬 모드서 fallback 실패 — secondary 도구, 필요 시 추가)
- screenshot: 로컬 미구현 (Windows 캡처는 별도)
- 진짜 boot-without-login 영구화 (Task Scheduler+admin)
- M5/M8 (chat reset hook / 토큰 DPAPI) — 단일PC+interop으로 M8(PC_AGENT_TOKEN)은 사실상 무의미해짐

👤 Strategy Lead Claude Opus 4.8

---

### 11b. 디바이스 별칭 resolver (2026-05-20)
owner 질문 "집 pc라고 해도 추론 가능?" → deterministic 경로에 자연어 지칭 해석 추가.
- `system_tools.resolve_device(phrase, connected_ids)`: (1) agent_id 직접 포함 (2) `DEVICE_ALIASES` 키워드 매칭 (**연결된 것만**) (3) 단일 PC 폴백
- `DEVICE_ALIASES`: desktop-home=[집/집pc/집컴퓨터/홈/home/내pc/이pc/데스크탑] / etribe-yesol=[회사/사무실/work] / linux-server=[서버/리눅스/ysh] / yesol-asus=[아수스/노트북] / mac-studio=[맥/mac]
- fastpath 섹션 10 정규식 한글 가능 (`(.{1,24}?)\s*에서`) → resolve_device → governor
- **검증 LIVE**: "집 pc에서 whoami" → desktop-home "yesol" / "집 컴퓨터에서 hostname" → "desktop-home" / "내 pc에서 rm -rf" → governor WARN. 미연결 디바이스(회사/맥) 지칭은 None (해석 안 함 = 안전)
- owner 편집 가능: `DEVICE_ALIASES` 키워드 추가

## 9. 안전 layer 구현 (LIVE) — 2026-05-20

**핵심 발견**: 자비스 도구가 이미 sora에 등록돼 있었음 (`system_tools.py` → `ALL_TOOLS`):
`remote_pc_command`(exec) / `remote_batch_exec` / `remote_claude_run` / `remote_vercel_deploy` 등.
PC 에이전트는 "멍청한 실행기" (shell=True, allowlist 0) → **모든 안전은 sora 브레인 layer에만 가능**.

**구현**:
- `src/core/security/command_governor.py` (신규) — `classify_risk()` (11 위험 패턴) + `audit()` (JSONL) + `stage_pending()`/`take_pending()` (warn-then-obey 상태, TTL 600s)
- `src/core/tools/system_tools.py` (수정) — `remote_pc_command` + `remote_batch_exec`에 governor 게이트 + `confirm_pending_command` 신규 도구 (owner "진행" 시 보류 명령 실행)
- 감사 로그: `/app/logs/jarvis_audit.jsonl` (bind-mount → `/home/ysh/sora/data/logs`, 재시작 생존)

**흐름**: 위험 명령 → 즉시 실행 X → "⚠️위험+권고+confirm_id" 반환 → owner "진행" → `confirm_pending_command` → 실행 + audit. 일반 명령 → 즉시 실행 + audit.

**검증 (LIVE in sora-live container)**:
- governor 8/8 분류 테스트 PASS (로컬) + 컨테이너에서 `rm -rf`→dangerous / `ls`→safe
- stage→WARN→confirm→audit e2e PASS (로컬)
- `confirm_pending_command` ∈ TOOLS (31개)
- 배포: 소스 편집(SSOT 보존) + docker cp + restart

**거버넌스 정합**: warn-then-obey. governor는 자동 차단 X — 위험 명령은 경고+보류, owner "진행" 시 무조건 실행 (예외 0). owner override = sovereign.

👤 Strategy Lead Claude Opus 4.7
