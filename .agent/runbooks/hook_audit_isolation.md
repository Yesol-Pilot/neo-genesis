# Hook Audit Isolation — `CLAUDE_AUDIT_DIR` Runbook

> 2026-05-10 신설 (Claude Opus 4.7).
> Scope: `~/.claude/hooks/*.ps1` 의 audit log 출력 디렉토리 격리 / CI 안전 / 테스트 회귀 0건 보장.

## 목적

직전 `tests/hooks_golden/core_v1.json` 20-case suite 가 실 `~/.claude/audit/` 일일 audit 파일을 오염시키는 위험 + CI 자동 trigger 보류 상태 였다. 9 PowerShell hooks (실 8개, `session_start` 미존재) 를 일괄 패치해 다음 패턴을 강제했다.

```powershell
$auditDir = if ($env:CLAUDE_AUDIT_DIR) { $env:CLAUDE_AUDIT_DIR } else { "$env:USERPROFILE\.claude\audit" }
if (-not (Test-Path $auditDir)) {
    New-Item -ItemType Directory -Path $auditDir -Force | Out-Null
}
```

`CLAUDE_AUDIT_DIR` env 가 set 이면 우선, 그 외 기존 owner 운영 동작 유지 (회귀 0건).

## 패치 대상 (8 hooks / 10 audit-path 라인)

| Hook | 영향 라인 |
|---|---|
| `user_prompt_submit.ps1` | 2 (`persona_routing` + `user_prompt`) |
| `pre_tool_use.ps1` | 2 (`agent_tool_use` + `pre_tool`) |
| `post_tool_use.ps1` | 1 |
| `stop.ps1` | 1 |
| `subagent_stop.ps1` | 1 |
| `pre_compact.ps1` | 1 |
| `notification.ps1` | 1 |
| `session_end.ps1` | 1 |

각 파일 PowerShell parser 구문 검증 통과 (`[System.Management.Automation.Language.Parser]::ParseFile` errors=0).

## Runner 통합

`scripts/run_claude_hooks_golden.py` 의 `_case_hook_exit()` 가 매 case 마다 `tempfile.TemporaryDirectory(prefix="hook_golden_audit_")` 로 격리 dir 생성 + `CLAUDE_AUDIT_DIR=<temp>` env override 주입. case 종료 시 자동 cleanup. 실 `~/.claude/audit` 무영향 보장.

선택 검증 키 (case 단위):
- `expected_audit_files: ["user_prompt_*.jsonl"]` — glob 패턴이 격리 dir 에서 매치되어야 PASS.
- `env_overrides: { "MY_VAR": "value" }` — case 별 추가 env 변수 (CLAUDE_AUDIT_DIR 위에 덮어쓰기 가능).

## 사용법

### 단일 hook 격리 테스트

```powershell
$env:CLAUDE_AUDIT_DIR = "C:\temp\my_isolation"
'{"prompt":"test"}' | powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\hooks\user_prompt_submit.ps1"
ls $env:CLAUDE_AUDIT_DIR  # → user_prompt_<date>.jsonl 격리 dir 에 생성
Remove-Item Env:CLAUDE_AUDIT_DIR
```

### Runner 격리 검증

```bash
cd D:/00.test/neo-genesis
python scripts/run_claude_hooks_golden.py
# 결과: 20/20 PASS + 실 audit log 0 변경
```

### CI 환경

`hooks-quality-gate.yml` workflow_dispatch stub 이 자동 trigger 가능 상태로 unblock. 격리된 audit dir 사용으로 CI 환경에서도 안전 (실 owner 운영 분리 + temp dir 자동 cleanup).

`hook source vendoring` (별도 owner action) 결정만 남았다 — 본 task 범위 밖.

## Troubleshooting

| 증상 | 원인 | 해결 |
|---|---|---|
| Runner 가 `expected_audit_files` glob 미매치로 FAIL | hook 의 audit dir 결정 로직이 env 우선이 아님 | 본 runbook 패턴 (`if ($env:CLAUDE_AUDIT_DIR) { ... }`) 적용 확인. `Grep` 으로 `\.claude\\audit` 잔여 하드코딩 검색. |
| Permission denied on temp dir | OS user 가 `$env:TEMP` 쓰기 권한 부재 | `tempfile.gettempdir()` 가 가리키는 경로 권한 확인. |
| `~/.claude/audit` 의 실 파일 카운트가 변경 | hook 가 env override 우회 | `Grep` 으로 `\.claude\\audit` 하드코딩 검색. 본 runbook 패턴 누락된 라인 발견 시 정정. |
| 신규 hook 추가 후 isolation 누락 | `~/.claude/hooks/<new>.ps1` 가 본 runbook 패턴 미적용 | 신규 hook 작성 시 동일 helper 변수 패턴 의무. golden 20 cases 에 신규 hook entry 추가 + `expected_audit_files` 검증 명시. |

## 회귀 검증 결과 (2026-05-10)

- PowerShell parser: 8/8 OK (errors=0)
- Hook golden runner: **20/20 PASS** (격리 dir 주입)
- Isolation smoke test:
  - 실행 전 `~/.claude/audit` 파일 카운트 = 23
  - 실행 후 카운트 = **23 (무변동)**
  - 격리 dir = `user_prompt_<date>.jsonl` (284 bytes) 1건 생성

## 향후 작업

- CI workflow 자동 trigger 활성화 — 별도 owner gate (hook source vendoring 결정 필요).
- `expected_audit_files` 검증 케이스 확대 — 현 20 case 는 stdout/exit 만 검증, audit content 검증 case 추가 가능.
- Linux/macOS hook 동등 패턴 (현재 Windows PowerShell only).
