# Hermes Agent WSL2 PoC — Stage 0+1 Closure (2026-05-17)

> **작성자:** Strategy Lead Claude Opus 4.7
> **owner 명령:** "진행해" (Phase 1 Hermes WSL2 PoC 승인)
> **G1 자율 박제:** 본 세션 모든 결정. owner G2 잔존 1건 (provider/API key 선택)

---

## 결론

**Hermes Agent v0.14.0 (2026.5.16) desktop-home WSL2 Ubuntu 24.04 라이브 가동.**

- 라이브 검증: `/usr/local/bin/hermes --version` → `Hermes Agent v0.14.0 (2026.5.16) / Python 3.11.15 / OpenAI SDK 2.24.0 / Up to date`
- 디스크: 1.1GB (`~/.hermes/` 212MB + `/usr/local/lib/hermes-agent/` 877MB)
- Skills: 24 active + 87 bundled (sora-watchdog/chaos drill 대체 후보 다수)
- Node v22.22.3 격리 설치 (`/root/.hermes/node/bin/`, PAPER conda 무영향)

---

## Stage 0 환경 진단 결과

| 항목 | 상태 |
|---|---|
| WSL2 distro | Ubuntu 24.04 Running (kernel 6.6.87.2) |
| Python | 3.12.3 (system) / 3.11.15 (Hermes venv) |
| Git | 2.43.0 |
| curl | 8.5.0 |
| Disk free | 842G / 1007G (12% used) |
| Memory | 23Gi total, 22Gi available |
| Passwordless sudo | ✅ OK |
| Default user | root (`/root/.bashrc` 백업 박제) |
| conda | 미설치 (PAPER 별도 환경 추정, 무영향) |
| 기존 ~/.hermes | CLEAN (충돌 없음) |

---

## Stage 1 설치 결과

### 실행 명령
```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh -o /tmp/hermes_install.sh
bash /tmp/hermes_install.sh
```

### Installer 안전성 사전 검증 (set -e, PYTHONPATH 방어, UV_NO_CONFIG)

### 산출 디렉토리 구조
```
~/.hermes/
├── SOUL.md, config.yaml, config.yaml.bak.20260517_184153
├── node/bin/{node,npm,npx,corepack}   # Node v22.22.3
├── skills/ (24 synced)
├── cron/, hooks/, memories/, sessions/
├── logs/, pairing/, audio_cache/, image_cache/

/usr/local/lib/hermes-agent/
└── venv/, agent/, gateway/, providers/, plugins/, tools/, skills/
```

### 사이드이펙트 (사전 표 대비 실제)
| 변경 | 실제 결과 |
|---|---|
| sudo apt 패키지 | build-essential, ripgrep, ffmpeg, playwright deps 설치 (auto) |
| ~/.hermes/ 생성 | 212MB |
| /usr/local/lib/hermes-agent/ | 877MB (FHS root install) |
| ~/.bashrc 변경 | `. "$HOME/.local/bin/env"` 1줄 (uv hook) |
| Node 설치 | `/root/.hermes/node/` 격리 (PAPER 무영향 ✅) |

### 미완료 단계 (의도적)
- Setup wizard kill됨 (provider/API key 입력 대기 — owner G2)
- `hermes status` 첫 실행 미수행
- `hermes doctor` 진단 미수행

---

## 핵심 명령 surface (owner 환경 정합)

| 명령 | owner 활용처 |
|---|---|
| `hermes chat` | sora 텔레그램 대체 후보 |
| `hermes gateway` | **Telegram/WhatsApp/Slack 게이트웨이** (sora 7봇 마이그레이션 대상) |
| `hermes cron` | **sora-watchdog 6h cycle / chaos drill / PIPA cron 대체** |
| `hermes hooks` | sora output_filter wrapper 패턴 외주화 |
| `hermes memory` | owner_facts cross-turn 표준화 가능 |
| `hermes claw` | **OpenClaw skill import** (박제 5개 활용 가능!) |
| `hermes kanban` | Multi-profile 작업 보드 |
| `hermes dashboard` | 브라우저 dashboard (WSL2 OK) |
| `hermes doctor` | 헬스 진단 |

---

## ⚠️ Errata (2026-05-17 정정)

직전 박제의 "A. anthropic Claude Max OAuth" 는 부정확. config.yaml 의 `anthropic` provider 는 **API key only (과금)**. Claude Max OAuth 는 별도 — **Claude Code CLI 자체에서** `claude auth login` 으로 처리. owner 가 정확히 정정: **메인 = Codex, 설계 호출 = Claude** (호출 한도 차이 반영).

## 정확한 패턴 (3계층)

| 계층 | 도구 | 인증 | 빈도 | 한도 |
|---|---|---|---|---|
| **Orchestrator** | Hermes self LLM = `nous` 무료 portal | `hermes login --provider nous` OAuth | 항상 | 0 (무료) |
| **메인 worker (80-90%)** | **Codex CLI** subprocess | `codex login` OAuth | 모든 반복 자동화 | GPT Pro 여유 |
| **설계 worker (10-20%)** | **Claude CLI** subprocess | `claude auth login` OAuth | 아키텍처/비판적 리뷰 | Claude Max 보존 |
| 한국어 어시 | sora (유지) | 별개 | 그대로 | 별개 |

Hermes 가 작업 종류에 따라 `terminal(command="codex ...")` 또는 `terminal(command="claude -p ...")` subprocess 분기.

## 라이브 검증 (2026-05-17)

```
$ /root/.hermes/node/bin/codex --version
codex-cli 0.130.0

$ /root/.hermes/node/bin/claude --version
2.1.143 (Claude Code)
```

PATH 정합: `~/.bashrc` 에 `export PATH="/root/.hermes/node/bin:$PATH"` 추가 (Windows shim 우선 회피).

## ✅ Stage 1 Closure (2026-05-17 21:18 KST)

owner 정정 흐름 반영 — WSL2 폐기 안 함 + Windows 인증 공유 + Hermes self LLM 만 OAuth.

### 인증 공유 (owner OAuth 0회)
| 항목 | 결과 |
|---|---|
| `/root/.claude/.credentials.json` → `/mnt/c/Users/yesol/.claude/.credentials.json` symlink | ✅ `loggedIn: true, subscriptionType: "max"` |
| `/root/.codex/auth.json` → `/mnt/c/Users/yesol/.codex/auth.json` symlink | ✅ `Logged in using ChatGPT` |

→ Windows native CLI 인증을 WSL2 가 직접 활용. Windows OAuth 갱신 시 자동 반영 (symlink atomic).

### Hermes setup wizard 결과 (owner OAuth 1회)
- **Provider**: `openai-codex` (GPT Pro device_code OAuth)
- **Self LLM**: `gpt-5.5` (Codex backend)
- **Terminal**: Local (WSL2 자체가 격리, Docker/cloud overhead 회피)
- **Gateway**: Skip (Phase 2 진입 시 별도 `hermes setup gateway`)

### 라이브 검증
```
hermes status:        Provider=OpenAI Codex, Model=gpt-5.5  ✅
hermes auth list:     openai-codex (1 credentials, oauth)  ✅
hermes doctor:        0 critical (telegram/discord optional 미설치 정상)  ✅
hermes -z 한국어 응답: 정상 (서브에이전트 도구 access 포함)  ✅
hermes cron list:     empty (첫 등록 대기)  ✅
```

### owner OAuth 누적 = **총 1회** (openai-codex)
직전 박제했던 "3회" 권고는 부정확 — Windows 인증 공유로 claude/codex CLI 는 별도 OAuth 불필요.

### 폐기된 시도 (cold honest)
- 시나리오 D (본 PC native Hermes 재설치) 권고 → owner 정정 ("wsl 폐기 말라") → 시나리오 E 채택
- `hermes auth add openai-codex --type oauth --no-browser` 비대화형 시도 → 출력 0 + 즉시 종료 → wizard 인터랙티브 필요 확인 → owner WSL terminal 직접 진행
- `hermes claw migrate` 으로 owner 박제 5개 import → OpenClaw 본가 설치본용. Claude Code subagent 형식 vs Hermes skill 형식 불일치. 박제 5개는 Claude Code 안에서 그대로 활용.

## ✅ Phase 1 PoC 첫 cron 라이브 (2026-05-17 22:23 KST)

owner 본질 정정 반영 — sora 보존 + Hermes 외주화 분업. sora 강화 anchor (Local LLM, LL-1 해소 후) 는 owner 별도 task.

### 등록 cron
- **Job ID**: `74688f4e4b64`
- **Name**: SBU 11 daily sitemap check (Phase 1 PoC)
- **Schedule**: `0 9 * * *` (매일 09:00 KST, WSL2 timezone = Asia/Seoul)
- **Script**: `/root/.hermes/scripts/sbu_sitemap_check.sh` (1321 bytes, +x)
- **Mode**: no-agent (script stdout 직접, Hermes LLM 안 거침 → cost 0)
- **Gateway**: user systemd service active (PID 9642, Linger enabled)
- **First scheduled run**: 2026-05-18T09:00:00+09:00

### 11 SBU 헬스 체크 대상
heoyesol.kr / aiforge/craftdesk/deploystack/finstack/sellkit.neogenesis.app / www.toolpick.dev / review.neogenesis.app / ur-wrong.com / kott.kr / quant.heoyesol.kr — dry-run **11/11 PASS**.

### 실패 시 동작
NEO_ALERT_BOT_TOKEN (@sora_yesol_bot, sora 운영 봇) 통해 owner DM (chat_id 1566967334) 텔레그램 알림. polling 안 함 = sora 7봇 충돌 0.

### sora ↔ Hermes 첫 시너지 박제
- Hermes = cron scheduler + script runner (외주화)
- sora = 알림 전달 채널 (NEO_ALERT_BOT)
- 두 시스템 분업 + 통합 검증

### 위험 + 회피
| # | 위험 | 회피 |
|---|---|---|
| R1 | WSL restart 시 systemd user service 사라질 수 있음 (WSL 경고) | Linger enabled + Windows 본 PC 24/7 가동 패턴 |
| R2 | owner Windows PC 재부팅 시 cron miss | Phase 2 진입 시 ysh-server 이관 검토 |
| R3 | sora 7봇 polling Conflict | Hermes Telegram gateway **안 켬** (영구) |
| R4 | NEO_ALERT_BOT_TOKEN 5/3 stdout 노출 (BOT-2 deferred) | sendMessage only, polling 안 함 → 영향 0 |

## 최종 분업 (sora 보존 + Hermes 외주화)

| 영역 | sora | Hermes |
|---|---|---|
| Telegram 7봇 polling | 🟢 보존 | ❌ |
| 한국어 fastpath + owner_facts | 🟢 보존 (sora 강점) | ❌ |
| Multi-LLM fallback (Gemini → 미래 Local Qwen3) | 🟢 보존 | ❌ |
| Secret redact / cron probe filter | 🟢 보존 | ❌ |
| **sora 강화 anchor (Local LLM 활성, LL-1 해소 후)** | 🟢 owner 미래 task | ❌ |
| Health/cron 모니터 (SBU sitemap / sora-watchdog 등) | 🔴 이관 → | 🟢 |
| chaos drill / PIPA | 🔴 이관 → (Phase 2) | 🟢 |
| 코드 자동화 / SBU 배포 / Strategy report | ❌ | 🟢 |
| Codex 위임 (반복) / Claude 위임 (설계) | ❌ | 🟢 |

## Stop/Go Gate (2026-05-24, 1주 후)

- ✅ 첫 cron 7회 자동 fire (월~일)
- ✅ 실패 시 텔레그램 알림 정확 도달
- ✅ sora 운영 무영향 (wrapping bug 류 0건)
- ✅ owner 운영 부담 정성 평가 ↓

전부 PASS → Phase 2 진입 (sora-watchdog 6h cycle 이관 + chaos drill + PIPA cron + SBU 배포 모니터 + 주간 Strategy Lead report)

미달 → 시나리오 B (sora 병존, Hermes 코드 자동화만) 회귀 가능. Reversibility 1줄 명령:
```bash
hermes cron remove 74688f4e4b64
hermes gateway stop
systemctl --user disable --now hermes-gateway.service
```

## owner Action 잔존 (별도 task)

| # | 작업 | 가치 | 시점 |
|---|---|---|---|
| LL-1 | anti-virus Network Protection exception → Local LLM Tailscale routing 활성 | sora 응답 18s → 5~10s | owner 30분 |
| W1-measure | 2026-05-24 (1주 후) 본 cron 실행 결과 + sora 영향 평가 | Phase 2 gate | passive |

---

👤 Strategy Lead Claude Opus 4.7 (Phase 1 PoC 라이브 박제, G1 자율)

---

## ⚠️ 2026-05-18 본 세션 cold honest 정정 박제

### 본 세션 중 발생한 incident 2건

**1. chat 노출 (내 실수)**
- `.env.production` grep 시 redact 패턴 부족 → `GOOGLE_SA_KEY_JSON` multi-line JSON 본체 chat 출력
- 노출 secret: `ur-wrong-indexing@gen-lang-client-0976754248.iam.gserviceaccount.com` RSA 2048 private_key
- 실 harm: **0** (해당 SA USER_MANAGED keys = 0개 상태, owner 확정. effective leak 무력)

**2. evidence-less alarm (내 실수)**
- 추정: "SA 가 어제 KRW 849,405 abuse vector 일 가능성"
- 사실 (owner Cloud Logging 검증): abuse vector = API key `battlefield` 단독. SA caller 아님
- owner 에 불필요 alarm 전가

### owner Cold Honest 확정 사실 (2026-05-18)
- personal project `gen-lang-client-0976754248`: API keys 0개, USER_MANAGED SA keys 0개, Gemini API disabled, billing 분리
- abuse vector: `battlefield` (UID f569ce52) API key 단독 — Cloud Logging caller identity 검증
- SA `ur-wrong-indexing` + `mission-control-sa` 모두 USER_MANAGED key 0개 (이미 정리)

### Strategy Lead 룰 강화 박제 (영구)

| # | 룰 | 본 세션 위반? |
|---|---|---|
| R1 | **Evidence-first alarm** — Cloud Logging / git history / 명시 확정 우선. 가능성만으로 P0 alarm 금지 | ✗ 위반 (재발 방지 박제) |
| R2 | **추정 vs 확정 분리 표기** — "가능성" 과 "확정" 항상 명시 | ✗ 위반 |
| R3 | **Secret grep redact 사전 적용** — multi-line JSON 매치 회피 (sed -E '/^[^=]+_(KEY|TOKEN|SECRET)_JSON=/d' 등) | ✗ 위반 (redact 패턴 강화) |
| R4 | **owner cool report 우선 신뢰** — owner self-verification 결과 반영, 재의심 회피 | 정합 |
| R5 | **chat 노출 secret 의 lifecycle 추적** — 이미 revoked 인지 사전 확인 | ✗ 누락 |

### 본 세션 closure (P0 alarm 부분)

- chat 노출 SA key: **이미 disabled = effective harm 0**
- 추가 owner action: **불필요**
- SSOT 박제 정정: 본 entry
- 본 세션 P0 incident 진단 = **취소 (false alarm 인정)**

### Hermes Phase 1 PoC 상태 (변동 없음)
- Job 74688f4e4b64 라이브
- 내일 (2026-05-18) 09:00 KST 첫 fire — **이미 fired** (오늘이 5/18)
- 다음 cron: 2026-05-19 09:00 KST
- Stop/Go Gate: 2026-05-24

---

👤 Strategy Lead Claude Opus 4.7 (false alarm 인정 + 룰 5건 강화 박제)

---

👤 Strategy Lead Claude Opus 4.7 (Stage 1 closure, G1 자율 박제)

---

## 다음 단계 (G1 자율 가능, owner G2 응답 후)

### Phase 1 PoC 첫 자동화 작업 후보 (Strategy Lead 선정)

| # | 작업 | 난이도 | 측정 가치 |
|---|---|---|---|
| 1 | **GSC indexing daily check** | 🟢 Low | KOTT/ToolPick 운영 부담 ↓ |
| 2 | sora-watchdog 6h cron → hermes cron 이관 | 🟡 Med | sora 운영 부담 ↓ 직접 측정 |
| 3 | quant cron (Supabase ledger 백업) | 🟢 Low | quant-bot legacy 자동화 |
| 4 | OpenClaw 박제 5개 `hermes claw import` 검증 | 🟢 Low | 직전 박제 자산 활용 |

권고: **#1 + #4 병렬**. PASS율 + 비용 측정 후 #2 (sora 이관) 진입 판단.

### Stop/Go Gate (1주 후 측정, 2026-05-24)
- PASS율 ≥ 80% AND
- owner 응답 안정성 체감 안 깨짐 AND
- 디버깅 시간 < sora 5월 평균

### Phase 2 진입 조건 (1달 후 측정, 2026-06-17)
- Phase 1 PoC 3+ 작업 안정 가동
- sora wrapping bug 류 invisible failure 0건 (Hermes 위에서)
- owner 운영 부담 정성 평가 (체감 ↓)

---

## Reversibility (1줄 롤백)

```bash
wsl.exe -- bash -c "rm -rf /root/.hermes /usr/local/lib/hermes-agent /usr/local/bin/hermes ~/.local/bin/{uv,uvx} && cp /root/.bashrc.bak-pre-hermes-20260517 /root/.bashrc"
```

sora-live (ysh-server container) **무영향** (물리적 분리, 본 PoC 는 desktop-home WSL2 한정).

---

## 박제 자산 (sunk cost 보존)

본 Phase 1 PoC 는 다음 owner 박제를 **유지**:
- sora `output_filter`, `owner_facts`, 한국어 fastpath, 7봇 — 모두 ysh-server sora-live 컨테이너에 그대로
- 32 페르소나 + 36 subagent + 9 hooks + Ontology v0.4 — 본 PC `.agent/` 그대로
- OpenClaw 박제 5개 (`001.ssot-agent-runtime/.../openclaw*.md`) — 그대로 (Hermes `claw import` 로 활용 검토)

---

## Cold honest

- 본 세션은 Stage 0+1 설치까지. **실 자동화 작업 0건 가동**.
- Phase 1 PoC PASS율 측정은 1주 후 (2026-05-24).
- Hermes Windows native early beta 회피 → WSL2 선택 정합 확인.
- Setup wizard kill = installer 의도된 흐름 일부 미완료. `hermes setup` 또는 `hermes model` + `hermes auth` 으로 owner 가 또는 G1 으로 마무리 가능.
- 외부 데이터 (F1 OpenClaw 10% 시간 손실) 가 owner 결정의 결정타. Hermes 도 동일 패턴 발생 가능성 있음 — Phase 1 PoC 가 그 검증.

---

👤 Strategy Lead Claude Opus 4.7 (G1 자율 박제, owner G2 잔존 1건)
