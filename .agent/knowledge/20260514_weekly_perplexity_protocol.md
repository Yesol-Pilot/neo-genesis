# Weekly Perplexity Web Measurement Protocol

- Date: 2026-05-14
- Cost: $0 (Perplexity free tier)
- Frequency: Weekly, every Monday 09:00 KST
- Duration: ~30 min owner / Claude session
- Goal: Track AI citation lift over 60 days (next re-judgment: 2026-07-14)

## Why manual (not cron)

Chrome MCP requires active Claude Code session. Owner triggers a session each Monday morning, runs the batch, results auto-saved to `citations.sqlite3`.

Alternative for full automation later: Playwright headless (4 hour build), but adds maintenance burden. Stay manual for now.

## Procedure (each Monday)

### Step 1 — Owner trigger (30 sec)

In active Claude Code session, type:
```
주간 Perplexity 측정 30 prompt batch 진행해
```

Claude (this protocol) auto-loads `scripts/geo_measure/seed_prompts.json`, iterates 30 prompts via Chrome MCP on perplexity.ai, saves results to DB.

### Step 2 — Claude autonomous execution (~25 min)

For each of 30 prompts:
1. Navigate Chrome MCP to `https://www.perplexity.ai/`
2. Find input ref via `find` tool
3. Click input → type prompt → press Enter
4. Wait 20-25 seconds for streaming response
5. `get_page_text` → extract full response
6. Parse with `measure_citations.py analyze()` (v1.5 patterns)
7. Save to `citations.sqlite3` via `save_perplexity_web_result.py`
8. Navigate back to perplexity.ai home for next iteration

Rate limit: ~30s per prompt × 30 = 15-25 min total

### Step 3 — Auto report (1 min)

After batch:
```bash
python scripts/geo_measure/reanalyze_v1_5.py
```

Generates same-window report (week N vs week N-1) showing:
- `mention_neo` change
- `any_url_brand` lift
- `mention_url` (literal neogenesis.app URL — the holy grail)
- `mention_hf`, `mention_wikidata` (structured signal pickup)

### Step 4 — Owner review

Claude surfaces report. Owner decides:
- Continue v1.5 (if positive lift)
- Pivot v2.0 (if no lift at 60d / 2026-07-14)

## Acceptance gates for 60d re-judgment (2026-07-14)

Compared to v1.5 baseline (2026-05-14):

| Metric | Baseline (n=2) | 60d gate | Decision |
|---|---|---|---|
| `mention_neo` | 3 / 2 queries = ~33% | ≥ 50% across 30 prompts | Pass if NAME pickup grew |
| `mention_url` (neogenesis.app literal) | 0% | ≥ 5% | Pass if URL becomes citeable |
| `any_url_brand` | 6.7% (Perplexity), 6.7% (aggregate) | ≥ 15% | Pass if backlink push worked |
| `mention_hf` | 0% | ≥ 3% | Pass if HF datasets get pickup |
| `mention_wikidata` | 0% | ≥ 2% | Pass if structured signals work |

Pass 3+ out of 5 → v1.5 validated, continue. Pass < 3 → v2.0 pivot reconsidered.

## Risk

- Perplexity TOS prohibits "automated systems" (Section 7). 30 queries/week is low-volume; account ban risk low but non-zero.
- Owner's Perplexity account is free tier; no Pro quota issues.
- If account flagged, fall back to manual single-query measurement via owner browser.

## Files

- `scripts/geo_measure/seed_prompts.json` — 30 prompts source
- `scripts/geo_measure/measure_citations.py` — analyze() function (v1.5 patterns, 20 brand keywords)
- `scripts/geo_measure/save_perplexity_web_result.py` — manual save helper
- `scripts/geo_measure/reanalyze_v1_5.py` — symmetric window report generator
- `scripts/geo_measure/citations.sqlite3` — accumulating telemetry (cross-week comparisons)

---

## 2026-05-20 — Batch run #1 (Claude via Chrome MCP, $0)

First live free-tier Perplexity batch. **perplexity_web n: 2 → 12** (rows 969-979, minus deleted 978).

### What ran
10 prompts measured: def-01..05 + cmp-01..05. Then **Perplexity throttled** — prob-01 and rep-01 both stalled at "사고" (thinking) on `/search/new` across 3 reads each, after ~12 rapid queries. Stopped per TOS automation-risk + safety (protect owner's free account). Remaining 19 (prob-02..05, price, rep, spec) deferred to next weekly run.

### Result — "URL citation 0%" confirmed LIVE (post markdown-fix + GitHub backlinks)
| Pattern | Evidence |
|---|---|
| **0 URL citations** of our domains | All 10 rows `citation_urls=[]`. neogenesis.app / toolpick.dev / ur-wrong.com / kott.kr never cited. |
| Brand NAME described (often favorably) | cmp-01 ToolPick ("most SaaS-comparison-first, cleaner fit"), cmp-02 UR WRONG ("AI-native debate, on-theme"), cmp-04 WhyLab ("end-to-end causal workflow") — but only when WE named the brand in the prompt. |
| Third-party sources only | billionverify, voxarena, quicktoolkit, wires.wiley, techcrunch — never our own domain. |
| Generic queries = 0 | def-01..05 (best AI automation cos / who runs many SaaS / etc.) → 0 Neo Genesis pickup. |

### Name-collision findings (new)
- **"EthicaAI"** → Perplexity surfaces a *different* university AI-ethics education project (source pixel-online), NOT our Melting Pot research. Namesake collision.
- **"K-OTT"** → interpreted as generic "Korean OTT"; lists TVING/Wavve/Coupang Play. Our kott.kr not recognized.

### Process learnings (for next run)
- **Throttle cap**: ~10-12 queries/session before Perplexity slows/stalls. Split the 30-prompt set across sessions/days, or build Playwright headless with human-like pacing.
- **Data integrity rule**: save ONLY the AI's verbatim response to `_resp` files. A `_resp_cmp-05` editorial note containing "Neo Genesis" falsely inflated `mention_neo_genesis=2` (caught + corrected → row 979 neo=0). Never annotate captured responses.
- Direct search URL works login-free: `https://www.perplexity.ai/search?q=<encoded>` (Korean + em-dash encode fine).

### 7/14 gate implication
Perplexity now seeded (n=12) but far below the "n≥100 / 6d window" gate. At ~10/session with throttling, reaching 100 needs ~10 spaced sessions OR a headless batch tool. **mention_url still 0** — the markdown-fix + GitHub backlinks have NOT yet produced Perplexity URL citations (expected: training/index lag + still-thin backlink profile). NM-2 (external backlinks) remains the gating lever.
