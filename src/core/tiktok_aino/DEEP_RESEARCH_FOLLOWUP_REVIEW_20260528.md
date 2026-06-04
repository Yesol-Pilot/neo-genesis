# Deep Research Follow-up Review - AiNo 2026-05-28

Reviewed source: `C:\Users\yesol\Downloads\deep-research-reportaino2.md`  
Project snapshot: `output\tiktok_aino_reference_research\deep-research-reportaino2_20260528.md`  
Previous request: `DEEP_RESEARCH_FOLLOWUP_REQUEST_20260528.md`  
Next request: `DEEP_RESEARCH_URL_BENCHMARK_REQUEST_20260528.md`  
Reviewed at: 2026-05-28 KST  
Applies to: `올바른 AiNo` / `@leftaino`

## 1. Conclusion

Reject this report as the final benchmark dataset.

It still does not provide the requested post-level URL table. It explicitly says the 20~30 actual post benchmark with direct URLs, metrics, and first-1/3/5-second coding was not completed. Therefore it must not be used to finalize `reference_patterns.json`, `format_router.json`, `hook_patterns.json`, `scene_type_library.json`, or `cta_patterns.json`.

Use it only as a provisional production codebook for these decisions:

1. Prefer `evidence_briefing`, `hybrid live_to_short`, `timeline_explainer`, and `fact_check` over generic card-news.
2. Put source/document/date context in the first 0~5 seconds, not only at the end.
3. Treat live or field footage grammar as a trust signal, but do not fake official documents or real-person footage with AI.
4. Keep comment-battle and satire formats behind stricter safety gates.
5. Optimize CTA for save, share, and next-part viewing before pure comment fighting.

## 2. Requirement Check

| Requirement | Result | Evidence in report |
| --- | --- | --- |
| 20~30 actual post rows | Fail | The report states the final table was not completed. |
| Direct platform URLs per row | Fail | Candidate table has channels/events, not post URLs. |
| TikTok 8+, Shorts 8+, Reels 4+ | Fail | No platform-balanced URL table. |
| Public metrics by post | Fail | Only a few secondary-public clues such as channel subscribers or reported views. |
| First 1s/3s/5s coding per post | Fail | Provided as inferred grammar, not row-level coding. |
| Scene/caption/voice/CTA fields per post | Fail | Provided as format-level guidance only. |
| JSON-ready codebook | Partial | Format codebook is useful but not benchmark-backed. |
| Explicit limitations | Pass | The report clearly states uncertainty instead of inventing URLs or metrics. |

## 3. Adopted Provisional Rules

These rules are allowed because they are operationally useful and already align with the current evidence-first architecture. They remain provisional until a URL-backed benchmark exists.

| Area | Provisional rule |
| --- | --- |
| Hook | First second should show a concrete scene, document, quote, number, or contradiction. Avoid abstract symbolic images as the main hook. |
| First 3 seconds | Identify the place, actor group, issue, or claim boundary in one short caption. |
| First 5 seconds | Show the stakes: date, event name, document/source, or public consequence. |
| Source card | For evidence formats, place source/date in 0~5 seconds. For live-to-short, place it immediately after the moment clip. |
| Captions | Use dense but short Korean captions. Keep a single line near 10~18 Korean characters where possible. |
| Voice | Prefer natural narration or real field audio when available. Avoid political impersonation. |
| Visuals | Use cinematic realistic scenes only when they represent context, not evidence. Do not create fake official documents or fake news screens. |
| CTA | Prefer save/share/next-part prompts. Comment prompts should ask for a judgment criterion, not identity-based fighting. |

## 4. Format Decisions

| Format | Decision | Rule |
| --- | --- | --- |
| `evidence_briefing` | Adopt | Requires at least two credible sources and source card in the opening seconds. |
| `hybrid live_to_short` | Adopt with gate | Use real public clips only when rights and context are controlled; otherwise recreate context through clearly generated illustrative scenes. |
| `timeline_explainer` | Adopt | Use timestamp or sequence cards; one step per card/cut. |
| `fact_check` | Adopt | Must include original claim capture or exact cited claim source; otherwise block. |
| `news_clip` | Limited | Useful for acquisition, but pure clipping should not become default production. |
| `satire_character` | Limited | Must use fictional characters and avoid real-person face/voice imitation. |
| `comment_battle` | Limited | Requires factual rebuttal card and toxicity filter; no hate, doxxing, or unverified allegations. |

## 5. Implementation Decision

Create a disabled provisional config:

- `config/reference_codebook_provisional.json`

Do not create or enable the final benchmark-derived configs yet:

- `config/reference_patterns.json`
- `config/format_router.json`
- `config/hook_patterns.json`
- `config/scene_type_library.json`
- `config/cta_patterns.json`

The final five configs require direct post URLs and row-level coding. A format-level narrative report is not enough.

## 6. Next Research Requirement

The next request must be narrower and more mechanical:

1. Return direct platform post URLs first.
2. If fewer than 20 direct URLs can be collected, stop and report `FAILED_URL_COLLECTION`.
3. Do not include channel-only candidates in the benchmark table.
4. Put every row in a machine-readable table.
5. Use `확인 불가` for unavailable metrics, but never use `확인 불가` for URL.

Use `DEEP_RESEARCH_URL_BENCHMARK_REQUEST_20260528.md` as the next request text.
