# AiNo TikTok HA Runbook

## Current Decision

YSH server is retired and must not be used as the AiNo TikTok control tower.
The active operating mode is local control on `desktop-home` using the local HA
state directory:

```text
D:\00.test\neo-genesis\output\tiktok_aino_ha_state
```

Remote control is disabled by default. Enable it only after an owner-controlled
personal replacement host has been explicitly promoted, SSH/auth has been
verified, and `src/core/tiktok_aino/config/ha_strategy.json` has been updated.
Company PCs, company accounts, company networks, and company-managed cloud
projects are not allowed.

## Active Roles

- `desktop-home`: local control, generation, Chrome/TikTok upload scheduling, monitoring.
- `yesol-asus`: personal ASUS failover candidate, not active yet.
- `oracle-cloud-personal`: future personal Oracle Cloud control/generation/monitoring candidate, not active yet.
- `vertex-ai-personal`: future personal Google Cloud/Vertex AI generation backend candidate, not an upload worker.
- `ysh-server`: retired, do not target for queue, SSH, SCP, or credential sync.

## Infrastructure Boundary

Allowed:

- Personal `desktop-home`.
- Personal `yesol-asus`, after SSH/auth verification.
- Personal Oracle Cloud resources, after account ownership, SSH, secrets, and cost boundaries are verified.
- Personal Google Cloud/Vertex AI resources for model or image generation fallback only.

Not allowed:

- Company PC or company-managed workstation.
- Company Google account, company cloud project, company billing, company network, or company VPN.
- Any hidden reuse of old YSH paths or credentials.

Vertex AI is not a browser upload host. Browser scheduling still requires a
logged-in, owner-controlled Chrome profile on a personal Windows machine unless
a dedicated, compliant remote browser environment is built later.

## Windows Upload Worker

Scheduled task:

```text
AiNo TikTok HA Upload Worker
```

Required process environment in the task action:

```powershell
$env:AINO_NODE_ID = "desktop-home"
$env:AINO_UPLOAD_AUTOMATION_ENABLED = "true"
$env:AINO_UPLOAD_MODE = "schedule"
$env:AINO_REMOTE_UPLOAD_ENABLED = "false"
$env:AINO_PYTHON = "C:\Users\yesol\miniconda3\python.exe"
$env:PYTHONPATH = "D:\00.test\neo-genesis"
```

The worker script is:

```powershell
D:\00.test\neo-genesis\scripts\tiktok_aino_ha_worker.ps1 -Role upload -Once
```

When `AINO_REMOTE_UPLOAD_ENABLED=false`, the script skips remote batch upload and
uses local HA state directly.

## Manual Checks

Run the single local preflight first:

```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = "."
python -m src.core.tiktok_aino.publish_queue_runner --queue output\tiktok_aino_live_issue_20260609\publish_queue_20260609_162400\publish_queue.json --preflight
```

Run the local publish queue audit before opening any browser workflow:

```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = "."
python -m src.core.tiktok_aino.publish_queue_runner --queue output\tiktok_aino_live_issue_20260609\publish_queue_20260609_162400\publish_queue.json --audit
```

Generate the local execution packet before any owner-approved schedule run:

```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = "."
python -m src.core.tiktok_aino.publish_queue_runner --queue output\tiktok_aino_live_issue_20260609\publish_queue_20260609_162400\publish_queue.json --packet
```

Run the local publish queue dry-run before any manual scheduling:

```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = "."
python -m src.core.tiktok_aino.publish_queue_runner --queue output\tiktok_aino_live_issue_20260609\publish_queue_20260609_162400\publish_queue.json --mode dry-run
```

If any planned slot is already past or too close, create a new local-only queue
before scheduling:

```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = "."
python -m src.core.tiktok_aino.publish_queue_runner --queue output\tiktok_aino_live_issue_20260609\publish_queue_20260609_162400\publish_queue.json --rollover-past-slots
```

Manual schedule execution is an external browser action and requires explicit
owner instruction in the current session:

```powershell
$env:AINO_UPLOAD_AUTOMATION_ENABLED = "true"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = "."
python -m src.core.tiktok_aino.publish_queue_runner --queue output\tiktok_aino_live_issue_20260609\publish_queue_20260609_162400\publish_queue.json --mode schedule --confirm-external-action --owner-instruction "owner explicitly requested upload schedule post in current session"
```

Audit the current queue:

```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = "."
$env:AINO_UPLOAD_AUTOMATION_ENABLED = "true"
python -m src.core.tiktok_aino.ha_publisher audit
```

Run one local upload worker pass:

```powershell
$env:AINO_UPLOAD_AUTOMATION_ENABLED = "true"
$env:AINO_REMOTE_UPLOAD_ENABLED = "false"
python -m src.core.tiktok_aino.ha_publisher --node-id desktop-home worker-once --operation upload --upload-mode schedule
```

Check the scheduled task:

```powershell
Get-ScheduledTaskInfo -TaskName "AiNo TikTok HA Upload Worker"
```

Expected healthy state:

- `ha_publisher audit` returns `ok=true`.
- `active_lease_count=0` unless a worker is currently running.
- `stale_upload_count=0`.
- Windows scheduled task `LastTaskResult=0`.

## Safety Rules

- Never upload or schedule `needs_revision` content.
- Manual queue execution should use `publish_queue_runner`; do not bypass it with per-manifest upload commands unless diagnosing a single failed item.
- `--preflight` is the preferred local entry point: it audits, rolls over stale slots if needed, writes a packet, and runs safe dry-run without scheduling or publishing.
- `--audit` is local-only and does not call Chrome, upload automation, scheduling, publishing, or performance measurement.
- `--packet` is local-only and writes the current audit result plus safe and external-gated commands for handoff.
- `--rollover-past-slots` is local-only and writes a new queue file; it does not upload, schedule, or publish.
- `prepare`, `schedule`, and `publish` require `--confirm-external-action` in `publish_queue_runner`.
- `prepare`, `schedule`, and `publish` also require `--owner-instruction` with an explicit upload/schedule/post instruction from the current session; continuation prompts are not valid.
- `schedule` and `publish` require `AINO_UPLOAD_AUTOMATION_ENABLED=true`.
- Stop on TikTok login, CAPTCHA, security check, account restriction, or unclear final-submit UI.
- Verify successful schedules in TikTok Studio content list by exact title and scheduled time.
- Keep upload/schedule verification separate from performance measurement.
- Treat scheduled rows, future rows, and zero-metric rows as `scheduled_not_evaluable`.
- Keep old past jobs as `expired` rather than deleting them, so the audit trail remains intact.
- Do not reintroduce YSH defaults. Replacement failover must be configured explicitly.
- Do not introduce company assets as failover. Use personal cloud or personal hardware only.
