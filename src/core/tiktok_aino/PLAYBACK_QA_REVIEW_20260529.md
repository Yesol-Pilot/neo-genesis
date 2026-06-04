# Playback QA Review - AiNo Reference Benchmark 2026-05-29

Playback benchmark: `output\tiktok_aino_reference_research\reference_benchmark_url_first_playback_verified_20260529.md`  
Validation output: `output\tiktok_aino_reference_research\reference_benchmark_url_first_playback_verified_20260529.validation.json`  
Playback QA JSON: `output\tiktok_aino_reference_research\playback_qa_20260529\playback_qa_results.json`  
Contact sheet: `output\tiktok_aino_reference_research\playback_qa_20260529\playback_qa_1s_contact_sheet_all.jpg`  
Reviewed at: 2026-05-29 KST  
Applies to: `올바른 AiNo` / `@leftaino`

## 1. Conclusion

The playback QA gate passed for candidate config generation.

Result:

- 20 benchmark rows still pass structural validation.
- 16 rows have clean first-screen playback captures.
- 4 TikTok rows loaded video but were partially blocked by TikTok app-open/content-warning overlays.
- The benchmark is now strong enough to generate candidate reference configs.
- It is not yet wired into the production router.

## 2. Clean vs Partial Rows

Clean playback rows:

`R002`, `R004`, `R005`, `R007`, `R008`, `R010`, `R011`, `R012`, `R013`, `R014`, `R015`, `R016`, `R017`, `R018`, `R019`, `R020`

Partial overlay rows:

`R001`, `R003`, `R006`, `R009`

Partial rows are still useful for title/body/metadata and risk review, but they should not be used as exact first-frame references.

## 3. Candidate Configs Generated

Generated config files:

- `config/reference_patterns.json`
- `config/format_router.json`
- `config/hook_patterns.json`
- `config/scene_type_library.json`
- `config/cta_patterns.json`

Status in each file:

`candidate_config_ready_not_wired`

This means the configs are ready for implementation wiring, but the production pipeline does not yet consume them automatically.

## 4. Practical Findings

The repeated high-performing visual grammar is:

1. Large, high-contrast vertical caption in the first screen.
2. Named actor or issue keyword immediately visible.
3. Real clip, debate/hearing frame, news graphic, or public-location visual behind the text.
4. Very little subtlety in the hook; nuance must be added after the stop signal.
5. CTA often pushes share/comment, but AiNo should convert this into save/share/judgment-question CTAs.

## 5. AiNo Transformation Rule

Do not copy the reference clips, faces, claims, or visual layouts directly.

Transform them as:

1. Use the same stop-signal category: actor, issue, number, quote, or civic scene.
2. Replace accusation-style wording with claim-boundary wording.
3. Add a visible source card in the opening seconds.
4. Use original cinematic/generated context scenes where real footage rights are not clear.
5. Keep CTA focused on save, share, next part, or a judgment criterion.

## 6. Next Implementation Gate

The next code task is to wire these configs into `pipeline.py` without hardcoding strategy language:

1. Load `reference_patterns.json`, `format_router.json`, `hook_patterns.json`, `scene_type_library.json`, and `cta_patterns.json`.
2. Create `reference_fit.json` from selected topic + format router.
3. Make scene planning read `scene_type_library.json`.
4. Make script hook generation use `hook_patterns.json`.
5. Keep upload blocked if final visuals copy a real person, party logo, fake news UI, or unsourced allegation.
