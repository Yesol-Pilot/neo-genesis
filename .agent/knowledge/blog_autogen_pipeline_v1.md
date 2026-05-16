# Blog Auto-Generation Pipeline v1 — Design SSOT

> **Owner:** Yesol Heo (`@Yesol-Pilot`)
> **Status:** v1 (initial), 2026-05-04
> **Pipeline path:** `D:/00.test/neo-genesis/scripts/blog_autogen/`
> **Log file:** `D:/00.test/neo-genesis/.agent/knowledge/blog_autogen_log.jsonl`
> **Schedule:** Windows Task `NeoGenesis-Blog-Autogen-Daily` (10:30 KST daily)

## 1. Why this exists

`neogenesis.app/blog` had 12 hand-written posts and zero automation as of 2026-05-04. The HIVE MIND content engine that powers the SBU sites (`toolpick.dev`, `aiforge.neogenesis.app`, etc.) was never wired to the corporate domain itself. Owner directive (2026-05-04): "네오제네시스 블로그 게시글 생성 자동화도 되지 않고 있는데?"

This pipeline closes that gap with a self-contained Python module (no Node, no Next-side runtime work) that:

1. **Senses** topic gaps using GEO citation data + existing blog corpus.
2. **Drafts** a 1500–2500-word post via the cheapest available LLM.
3. **Validates** quality against the V-Score gate (V ≥ 184.5).
4. **Verifies** every cited URL with HTTP HEAD before commit.
5. **Appends** the post to the two TypeScript SSOT files atomically.
6. **Commits + pushes** to the `Yesol-Pilot/landing` repo.
7. **Triggers** Vercel deploy (webhook) and IndexNow (Yandex + IndexNow.org).
8. **Logs** the full run record to a JSONL audit trail.

Everything is one process. No queues, no Redis, no orchestrators. The pipeline finishes or it errors — no half-states.

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Windows Scheduled Task (10:30 KST daily)                       │
│  scripts/blog_autogen/run_pipeline.bat                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  scripts/blog_autogen/run_pipeline.py                           │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
│  │  Sense   │→ │  Think   │→ │ Validate │→ │   Append +   │    │
│  │ topic    │  │ Gemini   │  │ V-Score  │  │  Commit +    │    │
│  │ gap      │  │ → Claude │  │ ≥ 184.5  │  │   Deploy +   │    │
│  │ analyzer │  │ → OpenAI │  │ (5 retry)│  │  IndexNow    │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘    │
│                                                                  │
│  └─→ runs/draft-<slug>.json (artifact)                          │
│  └─→ .agent/knowledge/blog_autogen_log.jsonl (audit)            │
└─────────────────────────────────────────────────────────────────┘
```

## 3. Files

| File | Purpose |
|---|---|
| `scripts/blog_autogen/run_pipeline.py` | Main orchestrator (~600 lines) |
| `scripts/blog_autogen/topic_gap_analyzer.py` | GEO + blog corpus gap analysis |
| `scripts/blog_autogen/v_score_validator.py` | V ≥ 184.5 quality gate |
| `scripts/blog_autogen/prompts/draft_post.md` | LLM system prompt |
| `scripts/blog_autogen/run_pipeline.bat` | Windows scheduled-task wrapper |
| `scripts/blog_autogen/runs/` | Per-run JSON artifacts |
| `.agent/knowledge/blog_autogen_log.jsonl` | Append-only audit log |
| `logs/blog_autogen/run-YYYY-MM-DD.log` | Stdout/stderr of each run |

## 4. Sense — topic gap selection

Priority order (highest leverage first):

1. **GEO 0% prompts** — categories where Neo Genesis is mentioned in ≤ 50% of measurement calls. The pipeline reads `scripts/geo_measure/citations.sqlite3` and groups by `prompt_id`. The first un-covered prompt with `mention_rate=0` becomes the topic. The post is written to *answer that exact prompt* so future LLM probes can find a direct response on-site.
2. **Press releases without a paired engineering explainer** — every entry in `press-releases.ts` should have a corresponding `/blog/explainer-*` post.
3. **Research assets without a /blog cross-link** — entries in `research-assets.ts` are 1st-party citation sources; the blog translates them into operator-facing engineering takeaways.
4. **Evergreen rotation** — five fallback topics covering measurement methodology, deploy patterns, idempotent pipelines, IndexNow coverage, Schema.org best practices.

The selector deduplicates against existing `BLOG_POSTS` slugs (parsed live from `sbus.ts`) and against any candidate already proposed in the same run. GEO prompts also run a lightweight topic-coverage check against existing blog slug/title tokens, so a prompt such as "compare DevOps platforms like Vercel" is not repeatedly selected after a semantically matching article has shipped under a refined slug.

Locale rotation: Mondays produce Korean posts (Asia/Seoul market), other days produce English. Override with `--locale ko|en`.

## 5. Think — provider chain

| Order | Provider / Model | Cost (USD / 1K out) | Use case |
|---|---|---|---|
| 1 | Gemini 2.5 Flash | $0.0000 (free tier) | Default |
| 2 | Gemini 2.5 Flash (paid) | $0.0003 | If free-tier rate-limited |
| 3 | Gemini 2.5 Pro | $0.0050 | If Flash quality fails V-Score |
| 4 | Claude Haiku 4.5 | $0.0010 | If Gemini chain exhausts |
| 5 | OpenAI GPT-4o-mini | $0.0006 | Last resort |

The chain auto-falls-through on `HTTP 429`, `403`, JSON parse failure, or empty candidates. Cost cap is **$0.10 per run**, tracked from the `usage.completion_tokens` / `usageMetadata.candidatesTokenCount` fields. If any single attempt exceeds the cap, the pipeline aborts before commit.

For GEO candidates, the draft prompt now treats `suggested_slug` as a required exact slug rather than a soft suggestion. This keeps future dedupe deterministic even when the model would otherwise invent a nearby slug.

JSON output is enforced by:
- Gemini: `responseMimeType: "application/json"` in `generationConfig`
- OpenAI: `response_format: {"type": "json_object"}`
- Claude: prompt-driven (the system prompt requires raw JSON without fences)

A tolerant extractor strips fences and trims trailing commas.

## 6. V-Score quality gate (V ≥ 184.5)

Maximum theoretical score: 185.

| Component | Max | Computation |
|---|---|---|
| Word count | 50 | `min(50, wc / 30)` — 50 at 1500 words |
| Authoritative citations | 30 | `min(30, n × 5)` — caps at 6 |
| Headings (h2/h3) | 30 | `min(30, n × 3)` — caps at 10 |
| Numerical signals | 40 | `min(40, n × 4)` — caps at 10, regex over `$N`, `N%`, `Nms`, `Nx`, dates, version strings, Q-IDs |
| FAQ entries | 20 | `min(20, n × 4)` — caps at 5 |
| Internal cross-links | 15 | `min(15, n × 5)` — caps at 3 |

Hard structural failures (any of these blocks publish, regardless of numeric score):

- word count < 1500
- < 8 h2/h3 headings
- < 5 authoritative citations (allowlist of 30+ canonical hosts)
- < 10 numerical signals
- < 5 FAQ entries
- < 3 internal cross-links
- missing `title`, `summary`, `lead`, `category`, or `wordCount`
- LLM returned `slug: "REJECT_INSUFFICIENT_SOURCES"`

The pipeline retries up to 5 times. On each retry, the rejected post's errors and actual validator counts are appended to the user prompt so the LLM can correct. If the actual body word count is below 1800, the repair prompt explicitly asks for 2000-2400 body words and 10-12 headings. This retry budget is intentional: the 2026-05-14 recovery run passed V-Score on attempt 4.

## 7. Citation HEAD verification

Before commit, each `citations[].url` is checked with HTTP HEAD (8s timeout). If HEAD returns 405/403, the pipeline retries with GET (some hosts disable HEAD). Dead URLs are dropped and the post is re-validated; if the filtered post still passes V-Score, the pipeline publishes the filtered version.

If dropping dead citations pushes V-Score below threshold, the same run does not abort immediately. The dead URLs are injected into the next LLM retry prompt with an explicit "do not cite these URLs again" instruction. Only after the retry budget is exhausted does the run exit with `dead_citations_below_threshold` and save the rejected draft to `runs/dead-citation-*.json`.

`--skip-citation-verify` is available for offline/test runs.

## 8. TS file mutation (atomic, idempotent)

Two SSOT files are touched:

- `src/landing/src/lib/data/sbus.ts` — append a `BlogPost` metadata entry inside the `BLOG_POSTS` array
- `src/landing/src/lib/data/blog-content.ts` — append a `BlogContent` body entry inside the `BLOG_CONTENT` array

Both writes use a temp-file + atomic rename. Idempotency is enforced by a `slug: "<slug>"` substring check before insertion. Running the pipeline twice in a row produces 1 post, not 2.

The TS rendering uses `json.dumps(value, ensure_ascii=False)` for all string literals so Korean characters and special punctuation are encoded correctly.

## 9. Git + Vercel + IndexNow

- **Commit:** the two SSOT files plus the generated per-slug thumbnail assets are staged. Commit message embeds the V-Score, word count, citation count, and FAQ count.
- **Push:** `git push origin HEAD` from the nested landing repo. If the default git credential helper fails, the pipeline runs `gh auth setup-git -h github.com` and retries. If that also fails, it retries with `GITHUB_PAT_YESOL_PILOT`, `GITHUB_TOKEN`, or `GH_TOKEN` via a one-shot Git extraheader. The push to `Yesol-Pilot/landing master` triggers Vercel automatically because the landing project has Git integration.
- **Vercel webhook (optional):** if `VERCEL_DEPLOY_HOOK` is set, the pipeline POSTs to it as a redundant trigger.
- **IndexNow:** POSTs the new blog URL + `/blog` index + `sitemap.xml` to Yandex (most reliable for new domains) and api.indexnow.org (Bing path; first-time domains often 403 until Bingbot discovers the key file naturally — harmless).

## 10. Run log (JSONL audit trail)

Every run appends one JSON line to `.agent/knowledge/blog_autogen_log.jsonl`:

```json
{
  "started": "2026-05-04T01:30:00Z",
  "args": {...},
  "phases": {
    "sense": {...},
    "think": {"attempts": [...], "cost_used_usd": 0.0021},
    "quality": {"v_score": 187.5, ...},
    "citation_verify": {...},
    "append": {"status": "ok"},
    "git": {"status": "ok", "commit": "abc1234"},
    "deploy": {...},
    "indexnow": {...}
  },
  "status": "published",
  "v_score": 187.5,
  "slug": "...",
  "url": "https://neogenesis.app/blog/...",
  "logged_at": "2026-05-04T01:32:14Z"
}
```

This log is the SSOT for owner-facing run history.

## 11. Schedule

Windows Scheduled Task: `NeoGenesis-Blog-Autogen-Daily`

```
schtasks /Create /SC DAILY /ST 10:30 /TN NeoGenesis-Blog-Autogen-Daily ^
  /TR "D:\00.test\neo-genesis\scripts\blog_autogen\run_pipeline.bat" /F
```

10:30 KST is intentionally chosen to avoid the 09:00 quant Risk Officer cron and the 10:01 Daily Strategy Briefing routine.

The task self-skips if `BLOG_POSTS` already has 20+ entries (oversaturation guard). At 1 post/day, this cap is reached on roughly 2026-05-12.

## 12. Owner G2 actions (none required for v1)

The pipeline is fully autonomous within the SBU Autonomous Growth standing approval. Specifically:

- ✅ **MDX commit/push** — within scope (file-based blog under `Yesol-Pilot/neo-genesis`)
- ✅ **Vercel production deploy** — within scope (Git push triggers automatically)
- ✅ **IndexNow ping** — within scope (URL submission, no auth-protected actions)
- ✅ **LLM API spend < $0.10/run** — well below G2 threshold

No owner G2 action is required to operate the pipeline. The owner should:

1. Confirm scheduled task creation (one-time).
2. Review the first 3-5 generated posts before un-attended automation is fully trusted.
3. If V-Score retries spike, audit the prompt at `scripts/blog_autogen/prompts/draft_post.md`.

## 13. Stop / fail-safe behaviors

| Condition | Behavior |
|---|---|
| Existing blog count ≥ 20 | Skip, status=`skipped` |
| LLM chain all fail | Exit 1 + log |
| Cost cap reached | Exit 2 + log |
| V-Score < 184.5 after 5 attempts | Exit 3 + save rejected draft |
| Citation HEAD reduces V-Score below threshold after retries | Exit 4 + save draft |
| TS append throws (file shape changed) | Exit 5 + log |
| Git commit/push fails | Exit 6 + log |
| Thumbnail generation fails or produces no PNG | Exit 7 + log; no commit/push |

All exits write a JSONL log entry. The Windows wrapper captures stdout/stderr to `logs/blog_autogen/run-YYYY-MM-DD.log` for owner-side debugging.

## 14. v2 candidates (deferred)

- Markdown alternate route (`/blog/<slug>/markdown`) — already exists, no work needed
- Image generation via FLUX.1-dev for OG images
- Korean ↔ English translation pairing (publish both, link with `hreflang`)
- Topical clustering — when 5+ posts share a category, surface a `/blog/category/<x>` hub
- Schema.org `LearningResource` + `BreadcrumbList` (already emitted by `app/blog/[slug]/page.tsx`)

These are tracked in `.agent/shared-brain/active-tasks.md` under "Blog autogen v2" if the owner approves.
