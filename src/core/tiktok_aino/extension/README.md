# AiNo TikTok Extension Bridge

This folder contains the local Chrome Extension scaffold for `@leftaino` upload
assistance and TikTok Studio metric collection.

The extension is intentionally a helper, not an evasion tool:

- It does not bypass CAPTCHA, login, security checks, rate limits, or platform warnings.
- It does not click the final public post button by default.
- It prepares a draft upload package, fills safe metadata, and asks for operator review.
- It labels AI-generated realistic media when the upload UI exposes that option.

## Local Bridge

Start the local bridge from the repo root:

```powershell
python -m src.core.tiktok_aino.extension.local_bridge
```

Default bridge URL:

```text
http://127.0.0.1:8757
```

Endpoints:

- `GET /health`
- `GET /latest`
- `GET /job?run_id=<run_id>`
- `GET /video?token=<token>`
- `POST /metrics`

Use `/latest` only for single-package testing. For scheduled batches, use
`/job?run_id=<run_id>` so the extension or browser automation loads the exact
video, caption, and planned publish time for that slot.

For performance monitoring, load the matching package first, open the video's
TikTok Studio analytics/detail page, then click `Studio 지표 수집`. The bridge
stores the raw Studio text and the loaded `run_id` in local JSONL under
`studio_metrics/`; `src.core.tiktok_aino.monitoring` turns that into a response
plan.

## Chrome Load

1. Open `chrome://extensions`.
2. Enable Developer mode.
3. Load unpacked: `src/core/tiktok_aino/extension/chrome`.
4. Open TikTok upload or Studio in the already logged-in Chrome profile.
5. Use the extension popup to load the latest package and prepare the current tab.

If TikTok displays CAPTCHA, login, suspicious activity, or policy review prompts, the
content script stops and reports the blocker.
