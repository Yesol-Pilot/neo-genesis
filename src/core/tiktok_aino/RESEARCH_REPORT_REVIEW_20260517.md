# TikTok AiNo Research Report Review - 2026-05-17

Reviewed source: `C:\Users\yesol\Downloads\deep-research-report (1).md`

## Conclusion

The report is useful as a general TikTok operations framework, but it cannot be applied as-is to `올바른 AiNo`.

For this account, the current production path is:

1. account-specific Korean political trend selection
2. script/storyboard/image/TTS generation
3. visual and Korean readability QA
4. Chrome/Studio scheduling automation
5. Studio-list verification
6. native metrics capture and feedback

The API-first parts of the report are future-track only unless TikTok approves the required Content Posting API scopes. Browser/Chrome extension automation remains the primary path for upload and scheduling.

## What To Adopt

- Keep a content registry for every item: `content_id`, topic, sources, claims, storyboard, asset provider, TTS provider, QA score, schedule time, publish status, failure reason.
- Track status transitions instead of treating upload clicks as success: `generated -> reviewed -> prepared -> scheduled_visible -> published -> measured`.
- Use KPI tiers beyond views: average watch percentage, completion, three-second retention, replay, comments, shares, saves, profile visits, follows, and pipeline failure rate.
- Keep policy checks before publishing: copyright, privacy, generated/edited content disclosure, watermark/logo checks, civic/election misinformation risk, fake engagement risk.
- Treat cross-posting as platform adaptation, not blind reposting.

## What Must Be Changed For AiNo

- The report says monetization direct design is out of scope. That conflicts with the account goal. AiNo needs monetization-oriented scoring from the start: watch time, follower conversion, save/share intent, and repeatable series potential.
- The report is too generic about content identity. AiNo needs progressive-leaning Korean politics, warm but sharp framing, and topic selection from real-time Korean political attention clusters.
- The report assumes an approved API path. This account should not depend on API approval. Studio browser automation and Chrome extension capture are the operational baseline.
- The report does not encode the account slot policy. AiNo uses KST dayparts: `08:10`, `11:20`, `19:30`.
- The report lacks duplicate-content safeguards. Reposting weak or already scheduled topics is blocked unless explicitly approved as reference-based remake analysis.

## Current Scheduling Blocker

The latest schedule attempt was not marked scheduled because Studio verification failed.

Evidence:

- `output\tiktok_aino_performance_reports\studio_content_post_schedule_20260517T104251Z.json`
  - `contains_topic = false`
  - `contains_time = false`
- `output\tiktok_aino_performance_reports\manual_schedule_attempt_20260517T105741Z.json`
  - `click.ok = false`
  - `confirm.ok = false`
  - `verify.has_topic = false`
  - `verify.has_time = false`

This means the browser automation reached or interacted with the upload flow, but the new post did not become visible in the Studio content list. Marking it as scheduled would create false-positive state and duplicate posting risk.

## Implementation Priority

1. Harden Studio scheduler before queuing more posts.
   - detect prepared upload state
   - set schedule date/time only after upload processing is complete
   - handle generated-content disclosure controls
   - click final schedule action with Korean/English selector fallbacks
   - refresh Studio content list and require topic/time visibility

2. Keep corrected KST dayparts.
   - morning: `08:10`
   - lunch: `11:20`
   - evening: `19:30`

3. Generate only from the corrected 3-day plan after scheduler verification passes.
   - plan: `output\tiktok_aino\schedule_plans\curated_three_day_plan_20260517_dayparts_corrected.json`

4. Add monitoring loop.
   - capture Studio visible rows
   - record missing metrics explicitly
   - do not infer performance from stale snapshots

## Operating Rule

Never set an item to `scheduled` unless it is visible in TikTok Studio with matching topic text and scheduled time. If visibility fails, keep status as `schedule_failed` and preserve screenshots/JSON evidence.
