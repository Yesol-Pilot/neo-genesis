# Master Credential Access Standard

> **목적**: Neo Genesis fleet 의 **모든 디바이스**에서 **모든 에이전트** (Claude / Codex / Sora / Gemini / Antigravity / Ollama / 자동화 스크립트 / cron / hook) 가 마스터 크레덴셜에 **표준화된 방식으로 접근**한다.
>
> **작성**: 2026-05-03 (owner 지시 "마스터크레덴셜은 모든 디바이스에서 모든 에이전트들이 기본적으로 접근하고 활용해야 해")
>
> **SSOT 분류**: 운영 표준 — `NEO_MASTER_RULES.md` 의 mandatory rule 로 승격

---

## 1. 핵심 원칙

### 1.1 단일 마스터 SSOT
- **권위 위치**: `desktop-sol01` 의 `D:/00.test/neo-genesis/.env.local`
- 이 파일이 **모든 마스터 크레덴셜의 진실 공급원**
- gitignored, mode 600, 평문 (vault 도입은 Phase 2)

### 1.2 모든 디바이스 표준 접근
- 각 fleet 디바이스 는 자신의 **로컬 캐시**: `~/.neo-genesis/credentials.env` (mode 600)
- 마스터 → 디바이스 캐시 동기화: `scripts/sync_credentials_to_fleet.py` (sora-pull or push)
- 디바이스가 마스터에 직접 접근하지 않는다 — 항상 로컬 캐시 사용

### 1.3 모든 에이전트 표준 lookup
- **Python 에이전트**: `from infra.agent_runtime.credential_loader import load_credentials; load_credentials()`
- **Bash / cron / hook**: `source infra/agent-runtime/credential_loader.sh`
- **Node.js 에이전트**: 환경변수는 부모 shell 또는 `.env.local` 직접 읽기 (dotenv)
- **수동 테스트**: `python infra/agent-runtime/credential_loader.py` 또는 `NEO_CRED_VERBOSE=1 source infra/agent-runtime/credential_loader.sh`

### 1.4 Override 정책 (Cron / CI 안전)
- 부모 shell 에 이미 `export` 된 **non-empty** 변수 → 유지 (덮어쓰지 않음)
- 부모 shell 에 **빈 export** 변수 → 로컬 파일 값으로 override
- 미정의 변수 → 로컬 파일 값으로 set

이 정책은 cron / CI / Docker 환경에서 **부모 shell 의 빈 export 가 자동 무효화**되도록 한다.

---

## 2. Lookup 우선순위 (탐지 순서)

| Rank | 경로 | 디바이스 | 비고 |
|---:|---|---|---|
| 1 | `~/.neo-genesis/credentials.env` | 모든 fleet | **권장 표준** — sync 후 mode 600 |
| 2 | `D:/00.test/neo-genesis/.env.local` | desktop-sol01, desktop-yesol | 마스터 SSOT (sol01) |
| 3 | `D:/00.test/neo-genesis/.env` | desktop-sol01 등 | 일부 키 (GitHub/Vercel/Supabase) |
| 4 | `~/neo-genesis-runtime/.env.local` | Unix 디바이스 (ysh-server, mac-studio) | runtime 어댑터 디렉토리 |
| 5 | `~/neo-genesis-runtime/.env` | Unix 디바이스 | runtime 어댑터 |
| 6 | `~/sora/secrets/.env` | ysh-server 운영 | Sora 전용 secrets |
| 7 | `/home/ysh/sora/secrets/.env` | ysh-server (root 호출 시) | absolute path fallback |
| 8 | `$(pwd)/.env.local` | 모든 디바이스 | 호출자 cwd |
| 9 | `$(pwd)/.env` | 모든 디바이스 | 호출자 cwd fallback |

**같은 키가 여러 파일에 있으면**: 먼저 발견된 + 부모 shell 미정의 변수만 set. 즉 우선순위 1 의 파일이 set 한 변수는 2,3,4... 에 같은 키가 있어도 덮어쓰지 않음.

---

## 3. Canonical 마스터 키 (4 카테고리)

### 3.1 GitHub
| 키 | 계정 | 권한 | 용도 |
|---|---|---|---|
| `GITHUB_PAT_YESOL_PILOT` | Yesol-Pilot | full classic PAT | **Yesol-Pilot/* 전용** (정책 §1.1) |
| `GITHUB_TOKEN` (legacy) | neogenesislab | classic | ⚠️ Yesol-Pilot/* 사용 금지 |
| `GITHUB_PAT` (legacy) | neogenesislab | classic | ⚠️ 동일 제약 |
| `OPENREVIEW_GITHUB_PAT` | openreview-neurlps | scoped | EthicaAI 학술 push 전용 |

**GitHub 인증 런타임 주의 (2026-05-03)**:
- Windows Credential Manager: Target=`git:https://github.com`, User=`Yesol-Pilot`, Type=`Generic`
- PowerShell: `credential.helper=manager` 경유 자동 인증을 기본 push 경로로 사용
- Git Bash: Windows Credential Manager lookup 호환성이 깨질 수 있으므로 기본 push 경로로 쓰지 않음. 필요 시 PowerShell 우회 또는 일회성 URL embed 사용
- 기준 push 검증: `5d54262 -> 0a0734a master -> master`, 기준 commit `0a0734a`

### 3.2 LLM Inference
| 키 | provider | 측정 cron 사용 | 비고 |
|---|---|---|---|
| `HF_TOKEN` | HuggingFace | no | Inference Providers + Datasets write |
| `OPENAI_API_KEY` | OpenAI | yes (cron) | 진짜 sk-proj-* (PAPER/WhyLab/.env 동기화) |
| `ANTHROPIC_API_KEY` | Anthropic | yes (단 credit 부족) | owner PASS 결정 (5/3) |
| `GEMINI_API_KEY` | Google AI Studio | yes (cron) | Gemini 2.5 Flash / Pro |
| `PERPLEXITY_API_KEY` | Perplexity | n/a | owner PASS 결정 (5/3) |

### 3.3 Wikidata / Wikimedia
| 키 | 용도 |
|---|---|
| `WIKIDATA_USERNAME` | BotPassword (`Neogenesislab@claude`) |
| `WIKIDATA_PASSWORD` | BotPassword 비밀번호 |
| `QUICKSTATEMENTS_TOKEN` | API 토큰 (revoke pending) |
| `QUICKSTATEMENTS_USERNAME` | `Neogenesislab` |

### 3.4 인프라 / 운영
| 키 | 용도 |
|---|---|
| `SUPABASE_ACCESS_TOKEN` | Management API (DDL/migration) |
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` | 공용 Supabase |
| `SORA_SUPABASE_URL` / `SORA_SUPABASE_KEY` | Sora 전용 (`kfoixzebpztikurwqgdr`) |
| `VERCEL_TOKEN` | Vercel CLI deploy |
| `NEO_ALERT_BOT_TOKEN` / `NEO_ALERT_CHAT_ID` | Telegram bot (@sora_yesol_bot) |
| `PC_AGENT_TOKEN` | PC Agent 인증 |
| `DASHBOARD_TOKEN` | 대시보드 Bearer 인증 |

---

## 4. 디바이스 sync 흐름

### 4.1 마스터 → 디바이스 push (`sync_credentials_to_fleet.py`)
```
desktop-sol01: D:/00.test/neo-genesis/.env.local
                ↓ (scp via Tailscale SSH)
desktop-yesol:  C:/Users/CTS_Sol/.neo-genesis/credentials.env  (chmod 600)
ysh-server:     /home/ysh/.neo-genesis/credentials.env         (chmod 600)
mac-studio:     /Users/ysh/.neo-genesis/credentials.env        (chmod 600)
```

mobile (`s26-ultra`, `tab-s10-ultra`) 는 sync 대상에서 **제외** — 모바일은 승인-only 디바이스, 키 보유 금지.

### 4.2 디바이스 → 마스터 pull (변경 발생 시)
- 새 키가 fleet 디바이스에서 발급된 경우 (예: ysh-server 에서 새 토큰)
- → manual 보고 후 owner 가 `desktop-sol01:.env.local` 에 추가
- 디바이스에서 마스터를 직접 수정 금지 (정책 §1.1 single source of truth)

### 4.3 동기화 빈도
- **manual trigger**: 새 키 발급 / 갱신 / revoke 시
- **자동 trigger**: 다음 세션 또는 owner 명시 지시
- mass rotation 시 모든 디바이스 일괄 sync 후 verify

---

## 5. 에이전트별 강제 적용

### 5.1 Claude Code
- 세션 시작 시 `CLAUDE.md` 가 SSOT 자동 import (`@./infra/agent-runtime/credential_loader.py` 명시)
- 코드 작성 시 `from infra.agent_runtime.credential_loader import load_credentials` 패턴 강제

### 5.2 Codex
- `AGENTS.md` 가 lookup 표준 import
- shell 작업 시 `source infra/agent-runtime/credential_loader.sh` 사용

### 5.3 Sora (운영 에이전트)
- 서버 startup 시 `~/sora/secrets/.env` 또는 `~/.neo-genesis/credentials.env` 자동 import
- 텔레그램 봇 / Brain Worker / Dashboard 모두 동일 lookup

### 5.4 Gemini CLI / Antigravity
- `GEMINI.md` 가 SSOT import
- google-genai SDK 는 `GEMINI_API_KEY` 환경변수 자동 인식

### 5.5 Ollama / Local LLM
- 키 사용 안 함 (로컬 추론) — credential lookup 불필요
- 단 hub publish 시 `HF_TOKEN` 필요 → bash loader 사용

### 5.6 Cron / Scheduled Task
- Windows: `cmd.exe /c "python <abs_path>/credential_loader.py && <command>"` 또는 wrapper batch
- Unix: cron 실행 명령 앞에 `source <abs_path>/credential_loader.sh && <command>`

---

## 6. 보안 Guardrails

### 6.1 절대 금지
- 마스터 크레덴셜을 **chat 메시지 / 로그 / git commit / Slack / 공개 dashboard** 출력 금지
- 토큰 값을 코드에 **하드코딩** 금지 (`sk-proj-...` 같은 raw 값)
- 토큰 redaction 규칙: 출력 시 `len + first 8 chars` 만 노출 (`sk-proj-... (164 chars)`)

### 6.2 Audit log 의무
- 매번 크레덴셜 사용 시점 → `.agent/shared-brain/credential_audit.jsonl` 에 append
- 형식: `{ts, agent, device, key_name, action, redacted_token_hint}`
- 마스터 키 노출 의심 시 즉시 revoke + 새 토큰 발급

### 6.3 Rotation 정책 (권장)
- HF_TOKEN: 90일
- GitHub PAT: 90일 (또는 작업 종료 즉시)
- Wikidata BotPassword: 사용 후 즉시 revoke
- API keys (OpenAI / Anthropic / Gemini): 365일 또는 owner 결정

### 6.4 Chat 노출 시 즉각 대응
- owner 가 토큰을 chat 에 직접 위임 시 (예: 본 세션의 GITHUB_PAT_YESOL_PILOT, HF_TOKEN)
- 박제 + 사용 + **작업 종료 후 owner 에게 revoke 권고** 공식 보고
- 다음 세션 시작 전 새 토큰 발급 권장

---

## 7. 표준 사용 예시

### Python 에이전트
```python
import os
from infra.agent_runtime.credential_loader import load_credentials, require

load_credentials()
require("HF_TOKEN", "GITHUB_PAT_YESOL_PILOT")  # 누락 시 즉시 RuntimeError

from huggingface_hub import HfApi
api = HfApi(token=os.environ["HF_TOKEN"])
```

### Bash 자동화
```bash
#!/usr/bin/env bash
source infra/agent-runtime/credential_loader.sh
git push https://Yesol-Pilot:${GITHUB_PAT_YESOL_PILOT}@github.com/Yesol-Pilot/neo-genesis.git master
```

### Cron 등록 (Windows)
```
schtasks /create /tn "NeoGenesis-Daily" /tr "<python_abs> <script_abs>"
# script_abs 안에서 from credential_loader import load_credentials
```

### 진단 (모든 키 presence 확인, 값은 redacted)
```bash
python D:/00.test/neo-genesis/infra/agent-runtime/credential_loader.py
# 또는
NEO_CRED_VERBOSE=1 source D:/00.test/neo-genesis/infra/agent-runtime/credential_loader.sh
```

---

## 8. 변경 이력

| 날짜 | 변경 |
|---|---|
| 2026-05-03 | 초안 작성 (owner 지시). credential_loader.{py,sh} 동시 도입 + lookup 표준 + audit guardrails |

---

## 9. 관련 문서

- `D:/00.test/CREDENTIAL_BIBLE.md` — 키 별 사용 위치 (값 X, 위치만)
- `.agent/knowledge/AGENT_SHARED_MEMORY.md` — 에이전트 운영 메모리
- `.agent/NEO_MASTER_RULES.md` — 운영 헌장 (mandatory rule)
- `infra/agent-runtime/credential_loader.py` / `.sh` — 도구
- `scripts/sync_credentials_to_fleet.py` — fleet 동기화 (Phase 2)
