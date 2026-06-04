# URL Benchmark Review - AiNo 2026-05-28

Reviewed source: `C:\Users\yesol\Downloads\aino.md`  
Project snapshot: `output\tiktok_aino_reference_research\aino_20260528_failed_url_collection.md`  
Validator: `python -m src.core.tiktok_aino.reference_benchmark C:\Users\yesol\Downloads\aino.md --json`  
Reviewed at: 2026-05-28 KST  
Applies to: `올바른 AiNo` / `@leftaino`

## 1. Conclusion

Reject this file as a usable URL-backed short-form benchmark.

The file correctly starts with `FAILED_URL_COLLECTION`, so it should not be treated as a successful research output. It contains only 10 rows, all marked as YouTube, with no TikTok rows, no Instagram Reels rows, and no actual Shorts URLs. The URLs also include Deep Research citation tokens inside the URL cell, so they are not clean direct post URLs.

Do not promote any final reference-derived configs from this file:

- `reference_patterns.json`
- `format_router.json`
- `hook_patterns.json`
- `scene_type_library.json`
- `cta_patterns.json`

## 2. Automated Validation Result

| Field | Result |
| --- | --- |
| `passed` | `false` |
| `row_count` | `10` |
| TikTok rows | `0` |
| YouTube Shorts rows | `10` by platform label, but URLs are ordinary `watch?v=` pages, not Shorts |
| Instagram Reels rows | `0` |
| blockers | `failed_url_collection_marker`, `url_rows_lt_20`, `tiktok_rows_lt_8`, `row_level_validation_failed` |
| warnings | `instagram_reels_rows_missing` |
| row error count | `69` |

Row error breakdown:

| Error code | Count | Meaning |
| --- | ---: | --- |
| `url_contains_non_url_text` | 10 | URL cell includes Deep Research citation text. |
| `url_platform_mismatch` | 10 | Rows are not valid Shorts/TikTok/Reels post URLs. |
| `critical_coding_required` | 49 | Required fields such as first 1s/3s/5s hook, caption density, or voice style are still `확인 불가`. |

## 3. Why This Is Not Enough

The file is better than the previous report in one narrow way: it admits failure instead of pretending the benchmark is complete.

But it still fails the production need:

1. There are only 10 rows, not 20 or more.
2. There are no TikTok references.
3. There are no Instagram Reels references.
4. The YouTube links are normal long-form watch pages, not Shorts URLs.
5. Metrics are mostly `확인 불가`.
6. The most important coding fields, especially first 1s/3s/5s hooks, are not filled.
7. It leans on archive/news long-form examples, not top-performing political short-form references.

## 4. What Can Be Salvaged

Only a weak editorial insight can be salvaged:

- Historical broadcast archive material can support `evidence_briefing` or `timeline_explainer` formats.
- `원본 테이프`, `당시 보도`, `날짜+행사명+핵심의제` style hooks are useful as wording patterns.

These are not benchmark-backed enough to drive visual routing, hook scoring, CTA selection, or automatic scheduling.

## 5. Next Move

Stop relying on a broad Deep Research prompt for this specific dataset. The next collection pass should be URL-first and mechanical:

1. Search platform-native surfaces directly.
2. Capture direct TikTok video URLs and YouTube Shorts URLs first.
3. Do not write analysis until 20 clean URLs are collected.
4. Then code first 1s/3s/5s, caption density, voice, CTA, and pipeline rule.
5. Run `reference_benchmark.py` before any config promotion.

Until then, `config/reference_codebook_provisional.json` remains disabled and final reference configs remain blocked.
