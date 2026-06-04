# URL-First Reference Collection Review - AiNo 2026-05-29

Source benchmark: `output\tiktok_aino_reference_research\reference_benchmark_url_first_candidate_20260529.md`  
Validation output: `output\tiktok_aino_reference_research\reference_benchmark_url_first_candidate_20260529.validation.json`  
Thumbnail contact sheet: `output\tiktok_aino_reference_research\url_first_collection_20260529\benchmark_thumbnail_contact_sheet.jpg`  
Collected at: 2026-05-29 KST  
Applies to: `올바른 AiNo` / `@leftaino`

## 1. Conclusion

This is the first structurally usable URL-first reference benchmark candidate.

The benchmark passes `reference_benchmark.py` structural validation:

- 20 direct post rows.
- 10 TikTok direct video URLs.
- 10 YouTube Shorts direct URLs.
- No URL citation-token contamination.
- Required row-level hook, scene, caption, voice, CTA, risk, and pipeline-rule fields present.

However, do not promote final reference configs yet. Hook and scene fields are coded from public title, metadata, and thumbnail/contact-sheet inspection, not full video playback. This is enough to unblock reference collection, but not enough to finalize viral hook, scene, and CTA routers.

## 2. Validation Result

| Field | Result |
| --- | --- |
| `passed` | `true` |
| `row_count` | `20` |
| TikTok rows | `10` |
| YouTube Shorts rows | `10` |
| Instagram Reels rows | `0` |
| blockers | none |
| warnings | `instagram_reels_rows_missing` |
| row errors | none |

## 3. What This Benchmark Can Drive Now

Allowed:

1. Topic and source-fit heuristics.
2. Reference pattern exploration for high-salience actor/issue captions.
3. A candidate library of scene types such as face clip, debate/news frame, vertical caption, and document-style text.
4. Risk controls against copying high-allegation formats directly.

Not allowed yet:

1. Final `reference_patterns.json`.
2. Final `format_router.json`.
3. Final `hook_patterns.json`.
4. Final `scene_type_library.json`.
5. Final `cta_patterns.json`.

## 4. Main Production Insight

The strongest repeated pattern is not polished card-news. It is a high-salience actor or issue keyword placed in a large vertical caption over a real clip or broadcast-derived frame. For `올바른 AiNo`, the usable transformation is:

1. Keep the immediate named-actor/issue stop signal.
2. Add a visible source card in the opening seconds.
3. Replace unsourced allegation phrasing with claim-boundary wording.
4. End with save/share or judgment-question CTA instead of raw outrage bait.

## 5. Next Gate

Before config promotion:

1. Playback-sample at least 12 of the 20 URLs.
2. Confirm actual first 1s/3s/5s visuals against the coded fields.
3. Confirm whether the thumbnail differs from the opening frame.
4. Replace `thumbnail_metadata_coded` fields with `playback_verified` fields.
5. Re-run `reference_benchmark.py`.

Only after this gate should candidate configs be generated from the benchmark.
