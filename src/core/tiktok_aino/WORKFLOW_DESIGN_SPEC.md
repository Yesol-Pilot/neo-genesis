# TikTok AiNo Content Workflow Design Spec

Version: 2026-05-14 v1

Owner channel: `올바른 AiNo` / `@leftaino`

This document is the workflow SSOT for the AiNo TikTok/Reels/Shorts content-generation system. Implementation should follow this document first, then the JSON strategy configs, then code.

Related design layers:

- `REFERENCE_BASED_CONTENT_ARCHITECTURE_20260528.md`: reference-based content architecture for topic selection, format routing, script briefs, scene design, engagement design, QA gates, and implementation backlog.
- `DEEP_RESEARCH_REPORT_REVIEW_20260528.md`: review of `C:\Users\yesol\Downloads\deep-research-report_aino.md`, accepted/rejected findings, and implementation priorities.
- `DEEP_RESEARCH_FOLLOWUP_REVIEW_20260528.md`: review of `C:\Users\yesol\Downloads\deep-research-reportaino2.md`; rejects it as final URL benchmark but accepts a disabled provisional codebook.
- `DEEP_RESEARCH_URL_BENCHMARK_REQUEST_20260528.md`: stricter request for direct post URLs before final reference configs are enabled.
- `DEEP_RESEARCH_URL_BENCHMARK_REVIEW_20260528.md`: review of `C:\Users\yesol\Downloads\aino.md`; confirms `FAILED_URL_COLLECTION` and keeps final reference configs blocked.
- `URL_FIRST_REFERENCE_COLLECTION_REVIEW_20260529.md`: direct URL-first collection review; first 20-row structural benchmark candidate, still pending playback QA before config promotion.
- `PLAYBACK_QA_REVIEW_20260529.md`: Playwright playback QA result; 16 clean first-screen rows, 4 partial overlay rows, and candidate config generation.
- `config/reference_codebook_provisional.json`: disabled provisional format codebook extracted from the second follow-up report.
- `config/reference_patterns.json`, `config/format_router.json`, `config/hook_patterns.json`, `config/scene_type_library.json`, `config/cta_patterns.json`: playback-QA-derived candidate configs, not yet wired into production routing.
- `../../../output/tiktok_aino_reference_research/20260528_top_performing_political_shortform_references.md`: external reference evidence used to derive the 2026-05-28 architecture update.

## 1. Operating Goal

Build a repeatable content operation, not a one-off video generator.

The pipeline must produce three things for every candidate:

1. A documented reason for choosing the keyword/topic.
2. A documented editorial angle and script structure.
3. A documented production plan for visuals, TTS, rendering, QA, upload, and feedback.

The channel may cover political and civic issues, but the automation must operate as public-interest commentary and news explainer production. It must not optimize for voter persuasion, paid political promotion, fake engagement, or misleading civic/election claims.

## 2. Research Inputs

Official TikTok sources currently used as design constraints:

- Creator Rewards: high-quality original content over one minute, with rewards formula signals around originality, play duration, search value, audience engagement, and ad value.
  - https://newsroom.tiktok.com/introducing-the-new-creator-rewards-program?lang=en
- Creator Search Insights: creators should use search-topic demand to shape relevant content.
  - https://newsroom.tiktok.com/creator-search-insights/?lang=en
- For You recommendations: user interactions and completion of longer videos are strong interest signals; follower count is not a direct recommendation factor.
  - https://newsroom.tiktok.com/how-tiktok-recommends-videos-for-you?lang=en
- AIGC requirements: realistic AI-generated images, audio, and video require labeling/disclosure; fake authoritative sources and misleading public-figure content are prohibited.
  - https://support.tiktok.com/en/using-tiktok/creating-videos/ai-generated-content
- Integrity and authenticity: misinformation about voting, election procedures, candidate qualifications, results, fake authoritative civic information, and paid political advertising are not allowed or FYF-ineligible.
  - https://www.tiktok.com/community-guidelines/en/integrity-authenticity
- Political ads policy: political parties, candidates, officials, and related political actors are restricted from advertising; organic commentary must still follow community guidelines.
  - https://ads.tiktok.com/help/article/tiktok-ads-policy-politics-government-and-elections

Design implication:

- Build for originality, watch time, finish rate, search value, comments/shares, and trust.
- Avoid copied news clips, fake official-looking documents, generated public-figure likenesses, and unverified election/civic claims.
- Every run must preserve enough artifacts to explain why it was generated and why it was allowed or blocked.

## 3. Full Workflow

```text
01_signal_collection
  -> 02_keyword_research
  -> 03_topic_pool
  -> 04_topic_scoring
  -> 04A_deep_research_reference_fit
  -> 05_editorial_plan
  -> 06_fact_pack
  -> 06A_risk_flags
  -> 06B_source_card
  -> 07_angle_brief
  -> 08_script_variants
  -> 09_selected_script
  -> 10_storyboard_brief
  -> 11_content_plan
  -> 12_visual_plan
  -> 13_tts_performance_plan
  -> 14_tts_plan
  -> 15_render_plan
  -> 16_quality_gate
  -> 17_upload_plan
  -> 18_performance_feedback
  -> next 02_keyword_research
```

Each flow must write a machine-readable artifact when it materially affects the final video.

## 4. Artifact Contract

| Flow | Artifact | Status |
| --- | --- | --- |
| 01 Signal Collection | `signal_snapshot.json` | Implemented |
| 02 Keyword Research | `keyword_plan.json` | Implemented |
| 03 Topic Pool | `topic_pool.json` | Implemented |
| 04 Topic Scoring | `topic_plan.json` | Implemented |
| 04A Deep Research Reference Fit | `deep_research_report.json` | Implemented |
| 05 Editorial Plan | `editorial_plan.json` | Implemented |
| 06 Fact Pack | `fact_pack.json` | Implemented |
| 06A Risk Flags | `risk_flags.json` | Implemented |
| 06B Source Card | `source_card.json` | Implemented |
| 07 Angle Brief | `angle_brief.json` | Implemented |
| 08 Script Variants | `script_variants.json` | Partially implemented in manifest |
| 09 Selected Script | `selected_script.json` | Implemented |
| 10 Storyboard Brief | `storyboard_brief.json` | Implemented |
| 11 Content Plan | `content_plan.json` | Implemented |
| 12 Visual Plan | `visual_plan.json` | Implemented |
| 13 TTS Performance Plan | `tts_performance_plan.json` | Implemented |
| 14 TTS Plan | `tts_plan.json` | Implemented |
| 15 Render Plan | `render_manifest.json` plus `manifest.json` | Implemented |
| 16 Quality Gate | `upload_validation` plus `verification_report.html` | Implemented |
| 17 Upload Plan | `upload_plan.json` | Implemented |
| 18 Performance Feedback | `performance_feedback.json` | Implemented |

## 5. Flow 01: Signal Collection

### Purpose

Collect fresh public signals before choosing keywords. The system must not rely only on a static list of user-provided terms.

### Inputs

- Broad public-news queries from `keyword_strategy.json`.
- Google News RSS results for the past 24 to 48 hours.
- TikTok search/reference signals when available.
- Account performance history from prior posts.
- Studio metrics collected by the extension.
- Policy risk terms from config.

### Processing

1. Fetch broad news candidates.
2. Normalize title, publisher, URL, published time, and query.
3. Extract candidate entities, institutions, action terms, issue terms, and risk terms.
4. Keep raw source evidence; do not summarize away the URL.
5. Mark source reliability and duplication.

### Output Schema

```json
{
  "version": "signal_collection_v1",
  "collected_at": "2026-05-14T00:00:00+09:00",
  "sources": ["google_news_rss", "tiktok_search", "account_metrics"],
  "raw_items": [
    {
      "title": "종합특검, 감사원 압수수색",
      "publisher": "example",
      "url": "https://example.com",
      "published_at": "2026-05-14T00:00:00+09:00",
      "query": "특검"
    }
  ],
  "detected_terms": {
    "entities": ["윤석열"],
    "institutions": ["감사원"],
    "actions": ["압수수색"],
    "issues": ["관저 이전"],
    "risk_terms": []
  }
}
```

### Gate

Block or mark weak if:

- all items are opinion columns with no hard-news support;
- all items are single-source;
- items are about voting procedures or election results without authoritative civic source;
- items require generated public-figure likenesses to explain.

## 6. Flow 02: Keyword Research

### Purpose

Convert fresh signals into concrete searchable keywords.

### Current Implementation

Implemented as `build_keyword_plan` in `pipeline.py`.

SSOT config:

- `config/keyword_strategy.json`

Output:

- `keyword_plan.json`

### Keyword Classes

| Class | Examples | Use |
| --- | --- | --- |
| Entity | 이재명, 윤석열, 김건희, 민주당, 국민의힘 | Search surface, not enough alone |
| Institution | 감사원, 검찰, 국회, 대통령실 | Source and accountability context |
| Action | 압수수색, 송치, 특검, 해명, 판결 | High-intent signal |
| Issue | 관저 이전, 검찰개혁, 공천개입 | Best topic nucleus |
| Format intent | 전말, 근거, 책임, 오해와 진실 | Packaging query |
| Risk | 투표 방법, 선거 결과, 여론조사 | Needs policy review |

### Scoring

Keyword score must consider:

- support count across recent public items;
- concrete modifier count;
- high-intent action terms;
- trusted source support;
- phrase specificity;
- generic single-word cap;
- policy risk penalty.

### Selection Rule

Prefer:

- `감사원 압수수색`
- `관저 이전`
- `검찰개혁 입법`
- `김건희 특검`

Demote:

- `특검`
- `의혹`
- `정치`
- `논란`
- `뉴스`

### Output Schema

```json
{
  "version": "keyword_research_v1",
  "base_queries": ["한국 정치", "국회", "특검"],
  "expanded_queries": ["감사원 압수수색", "감사원 압수수색 전말"],
  "selected_keywords": [
    {
      "keyword": "감사원 압수수색",
      "score": 104,
      "support_count": 4,
      "matched_modifiers": ["압수수색", "감사원"],
      "rationale": ["support=4", "modifiers=압수수색,감사원"]
    }
  ],
  "rejected_keywords": []
}
```

### Acceptance

- At least one selected keyword must be a concrete phrase or a named entity plus action.
- Top keyword must not be a generic single term unless no concrete phrase exists.
- Expanded queries must include both base queries and selected keyword templates.

## 7. Flow 03: Topic Pool

### Purpose

Build multiple candidate topics from selected keywords before choosing the final one.

### Inputs

- `keyword_plan.json`
- expanded Google News results
- previous performance feedback
- source registry

### Processing

1. Fetch items for expanded keyword queries.
2. Group by specific overlap, not just shared broad entity.
3. Create one candidate per issue cluster.
4. Attach support sources.
5. Attach risk and format hints.

### Output Schema

```json
{
  "version": "topic_pool_v1",
  "candidates": [
    {
      "topic_id": "topic_001",
      "title": "감사원 압수수색과 관저 이전 의혹",
      "keywords": ["감사원 압수수색", "관저 이전"],
      "source_ids": ["hot_news_01", "hot_news_02"],
      "support_count": 5,
      "risk": "medium",
      "format_hint": "reward_deep"
    }
  ]
}
```

### Gate

Reject candidates when:

- sources are unrelated except for a broad person name;
- candidate needs speculation to connect articles;
- candidate is too abstract to support nine cards;
- candidate is mainly about election logistics without authoritative election source.

## 8. Flow 04: Topic Scoring

### Purpose

Select a topic using content-production value, not only hotness.

### Score Axes

| Axis | Why It Matters |
| --- | --- |
| Recency | Current issues get search and feed attention |
| Source support | Reduces misinformation risk |
| Search value | Supports Creator Rewards search-value signal |
| Conflict clarity | Makes the script easier to follow |
| Visual potential | Prevents generic background images |
| Retention potential | Supports 60s+ completion |
| Comment trigger | Supports engagement |
| Originality potential | Avoids copied news clip behavior |
| Policy risk | Prevents civic/election/AIGC violations |
| Monetization fit | Keeps reward candidate viable |

### Output Schema

```json
{
  "version": "topic_plan_v1",
  "selected_topic_id": "topic_001",
  "selection_reason": "highest source support and concrete search phrase",
  "scores": {
    "recency": 90,
    "source_support": 88,
    "search_value": 92,
    "visual_potential": 84,
    "policy_risk": 72
  },
  "blocked_candidates": []
}
```

### Acceptance

- Selected topic must have a clear issue nucleus.
- Selected topic must include at least two usable sources for `reward_deep`.
- If policy risk is high, topic must route to a safer explanatory angle or be blocked.

## 8-A. Flow 04A: Deep Research Reference Fit

### Purpose

Topic heat alone is not enough. Before writing the script, the system must prove the topic can become a strong short-form video: clear conflict, enough public-source support, searchable phrasing, a reference-style hook, cinematic sceneability, comment potential, and a safe monetization path.

### Current Implementation

Implemented as `build_deep_research_report` in `pipeline.py`.

SSOT config:

- `config/deep_research_strategy.json`

Output:

- `deep_research_report.json`

### Score Axes

| Axis | Why It Matters |
| --- | --- |
| Heat | Recent public attention and news recency |
| Source density | Support from more than one public item or trusted publisher |
| Search value | Terms that can map to titles, captions, hashtags, and future search |
| Reference fit | Whether the issue matches a reusable high-retention short-form structure |
| Narrative tension | Conflict, contradiction, pressure, or unanswered explanation |
| Evidence density | Records, reports, investigation terms, official bodies, or documents |
| Cinematic sceneability | Whether distinct realistic scenes can be generated per card |
| Comment potential | Whether viewers can answer with a low-friction numbered choice |
| Follower conversion | Whether the video creates a reason to follow for the next verification |
| Monetization fit | One-minute-plus originality, watch duration, search, engagement, and safety |
| Policy safety | Civic/election/AIGC risk that can block or demote the topic |

### Acceptance

- The pipeline may override the raw heat winner when another candidate has a stronger deep-research score.
- A topic should be demoted if it has weak reference fit, weak sceneability, thin source support, or high policy risk.
- The selected archetype must feed the script with a research question, counterpoint focus, comment trigger, and follower promise.

## 9. Flow 05: Editorial Plan

### Purpose

Decide how the selected topic will be framed before writing the script.

### Angle Types

| Angle | Best For |
| --- | --- |
| `timeline_explainer` | Fast-moving investigations or official actions |
| `evidence_gap` | Claims with confirmed and unconfirmed parts |
| `accountability_line` | Public authority and responsibility issues |
| `misunderstanding_truth` | Confusing or polarizing claims |
| `three_criteria` | Policy, economy, education, civic judgment |
| `counterpoint_review` | High-risk claims requiring fairness and restraint |

### Output Schema

```json
{
  "version": "editorial_plan_v1",
  "topic_title": "감사원 압수수색과 관저 이전 의혹",
  "angle": "timeline_explainer",
  "core_question": "무엇이 확인됐고 무엇이 아직 비어 있나?",
  "viewer_promise": "1분 안에 전말, 근거, 책임 기준을 분리한다",
  "tone": "단정적 분노가 아니라 차분한 긴장감",
  "must_include": ["전말", "근거", "책임"],
  "must_avoid": ["범죄 확정", "실존 인물 합성", "정당 로고"]
}
```

### Acceptance

- Must include one viewer promise.
- Must include one final comment question.
- Must include at least one risk-control instruction.
- Must not include direct support/opposition CTA for a party/candidate.

## 9A. Flow 06/06A: Fact Pack And Risk Flags

### Purpose

The script must not be written from a topic title alone. It needs a fact boundary first, then a separate risk boundary.

### Required Artifacts

| Artifact | Purpose | Gate |
| --- | --- | --- |
| `fact_pack.json` | Separates confirmed facts, reported claims, counterpoints, unanswered questions, and source URLs | Evidence briefing requires at least two credible source items |
| `risk_flags.json` | Separates election, AIGC, defamation, copyright, public-importance, and political-actor monetization risk | Any high-risk flag requires manual review or block |
| `source_card.json` or equivalent field | Defines the source card shown in the first 3~12 seconds | Missing source card blocks 60~80s evidence briefing |

### `risk_flags.json` Minimum Schema

```json
{
  "version": "risk_flags_v1",
  "election": {"level": "none", "reason": ""},
  "aigc": {"level": "low", "requires_label": true},
  "defamation": {"level": "none", "reason": ""},
  "copyright": {"level": "low", "reason": ""},
  "public_importance": {"level": "high", "reason": ""},
  "political_actor_monetization": {"level": "none", "reason": ""},
  "manual_review_required": false,
  "publish_blockers": [],
  "safe_rewrite_notes": []
}
```

### Acceptance

- Do not generate fake document, news, court, assembly, or official-looking screens when no real source exists.
- Do not turn reported claims into confirmed facts.
- Do not publish `evidence_briefing_75` if source support is weak.
- Keep short acquisition clips subordinate to the same source/risk constraints.

## 10. Flow 08: Script Variants

### Purpose

Generate more than one script and score them before rendering.

### Required Variants

- `hook_pressure`: strongest first-card stop signal.
- `evidence_first`: starts from source credibility.
- `comment_trigger`: optimized for final discussion question.

### Script Requirements

- 9 to 12 scenes for `reward_deep`.
- 65 to 95 seconds for `reward_deep`.
- First card: short, concrete, searchable.
- Last card: summary plus comment/follow/share CTA.
- TTS body per scene should fit natural Korean speech.

### Output Schema

```json
{
  "version": "script_variants_v1",
  "variants": [
    {
      "variant_id": "hook_pressure",
      "title": "특검, 48시간 전말",
      "score": 91,
      "blockers": []
    }
  ]
}
```

## 11. Flow 09: Selected Script

### Purpose

Freeze one script before any image/TTS work.

### Output Schema

```json
{
  "version": "selected_script_v1",
  "variant_id": "hook_pressure",
  "selection_reason": "best hook and retention score",
  "script": {}
}
```

### Acceptance

- Selected script must pass policy and readability gates.
- Selected script must be linked to the topic and editorial plan.

## 12. Flow 10/11: Storyboard And Content Plan

### Purpose

Translate the selected script into a production plan.

### Current Implementation

Implemented as `build_content_plan` in `pipeline.py`.

Output:

- `content_plan.json`

### Scene Fields

Each scene plan must include:

- scene id;
- script role;
- narrative step;
- viewer question;
- on-screen text;
- narration goal;
- evidence need;
- image need;
- visual role;
- issue type;
- location;
- camera;
- required anchors;
- avoid/safety constraints;
- source ids.

### Acceptance

- Every scene must have an image need.
- Every scene must have a viewer question.
- Every scene must carry source ids when claims are present.
- Final scene must contain a comment question.

## 13. Flow 12: Visual Plan

### Purpose

Prevent generic, repetitive, or irrelevant images.

### Required Scene Pattern

| Scene | Role | Visual Job |
| --- | --- | --- |
| 1 | hook | Stop the scroll with one strong foreground object |
| 2 | why_now | Show current signal, newsroom, public-office tension |
| 3 | criteria | Show issue split or judgment framework |
| 4 | evidence | Show documents, records, source packets |
| 5 | responsibility | Show hearing room, microphone, empty answer seat |
| 6 | verification | Show confirmed vs unresolved materials |
| 7 | counterpoint | Show held conclusion or blank space |
| 8 | responsibility review | Show summary of criteria |
| 9 | cta | Show comment cards/editor desk |

### Hard Safety Rules

- No real politician likeness.
- No party logo.
- No readable fake document text.
- No fake official news page.
- No election campaign material.
- Add AIGC disclosure when realistic.

### Output Schema

```json
{
  "version": "visual_plan_v1",
  "scenes": [
    {
      "scene_id": 1,
      "prompt_basis": "content_plan.image_need",
      "required_anchors": ["public record folder", "civic entrance"],
      "avoid": ["real politician likeness", "party logo"]
    }
  ]
}
```

## 14. Flow 13/14: TTS Performance And TTS Plan

### Purpose

Produce a Korean speech plan before audio generation.

### Rules

- Use ElevenLabs as publish candidate.
- Windows/system TTS is preview only.
- Convert numbers, dates, percentages, handles, URLs, and hashtags into Korean reading text.
- Split long sentences.
- Remove excessive emotional punctuation.
- Keep generic TTS voice; do not mimic public figures.

### Output Schema

```json
{
  "version": "tts_plan_v1",
  "provider": "elevenlabs",
  "voice": "Anna Kim",
  "model": "eleven_multilingual_v2",
  "scene_texts": [
    {
      "scene_id": 1,
      "tts_text": "특검, 사십팔 시간 전말..."
    }
  ],
  "warnings": []
}
```

## 15. Flow 15: Render Plan

### Purpose

Render once production inputs are frozen.

### Rules

- 1080x1920 vertical video.
- Text is rendered by the system, not baked into AI images.
- Respect TikTok right rail and bottom UI safe zones.
- Static hold images; no shaking/constant zoom.
- Use transitions only between scenes.

### Outputs

- `preview_1080x1920.mp4`
- `storyboard.png`
- `mobile_preview_storyboard.png`
- `render_manifest.json`
- `manifest.json`
- `verification_report.html`

## 16. Flow 16: Quality Gate

### Gate Matrix

| Gate | Pass Criteria |
| --- | --- |
| Policy | no civic misinformation, no paid political ad language, no fake public figure content |
| Sources | every claim maps to known source |
| Search value | concrete keywords in title/caption/hashtags |
| Readability | mobile text fits safe zones |
| TTS | ElevenLabs generated for publish candidate |
| Visual | all scenes have generated images for publish candidate |
| Visual diversity | location/camera/palette not repetitive |
| Reward fit | 60s+ original explainer for `reward_deep` |
| AIGC | disclosure present when realistic generated media is used |
| Upload | manifest validates as `publish_ready` |

### Status Semantics

- `needs_revision`: do not upload.
- `upload_ready`: technically uploadable but not recommended.
- `publish_ready`: candidate for scheduling.
- `published`: posted or scheduled in TikTok.
- `monitoring`: metrics collection phase.

## 17. Flow 17: Upload Plan

### Purpose

Keep browser upload automation auditable.

### Rules

- Extension fills upload fields only after `publish_ready`.
- Stop on login, CAPTCHA, security warning, suspicious activity, or account restriction.
- Final public post action should remain human-confirmable unless the owner explicitly changes operating mode.
- AIGC label candidate should be selected for realistic generated images.

### Output Schema

```json
{
  "version": "upload_plan_v1",
  "run_id": "leftaino_...",
  "status": "planned",
  "caption": "...",
  "hashtags": [],
  "aigc_label_required": true,
  "schedule_time_local": "2026-05-14T19:30:00+09:00"
}
```

## 18. Flow 18: Performance Feedback

### Purpose

Feed actual results back into keyword and editorial selection.

### Metrics

- views;
- average watch time;
- completion rate;
- likes;
- comments;
- shares;
- saves;
- followers gained;
- profile visits;
- restrictions or removal;
- RPM/qualified views when available.

### Feedback Rules

- Reward high completion and high comment rate.
- Reward keywords that generate follows, not only views.
- Penalize topics with low retention despite high views.
- Penalize visual patterns that correlate with low completion.
- Cool down policy-sensitive keywords after warnings/restrictions.

### Output Schema

```json
{
  "version": "performance_feedback_v1",
  "run_id": "leftaino_...",
  "topic_keywords": ["감사원 압수수색"],
  "format": "reward_deep",
  "feedback": {
    "keyword_adjustments": [{"keyword": "감사원 압수수색", "delta": 8}],
    "format_adjustments": [{"format": "reward_deep", "delta": 4}],
    "visual_adjustments": [{"pattern": "document_table", "delta": -3}]
  }
}
```

## 19. Implementation Roadmap

### Phase A: Artifact Completeness

1. Add `signal_snapshot.json`. Done.
2. Add `topic_pool.json`. Done.
3. Add `topic_plan.json`. Done.
4. Add `editorial_plan.json`. Done.
5. Add `selected_script.json`. Done.

Done when every publish candidate can explain:

- why this keyword;
- why this topic;
- why this angle;
- why this script;
- why these images and TTS settings.

### Phase B: Visual/TTS Planning

1. Split `visual_plan.json` from `visual_assets.json`. Done.
2. Split `tts_plan.json` from TTS lint. Done.
3. Add explicit prompt lineage from content plan to generated asset. Done.

### Phase C: Upload and Scheduling

1. Add `upload_plan.json`. Done.
2. Add schedule slot reasoning. Done.
3. Ensure extension refuses anything below `publish_ready`. Done via `validate_manifest_for_upload` and `build_upload_job`.

### Phase D: Feedback Loop

1. Normalize Studio metrics into `performance_feedback.json`. Done.
2. Feed keyword and format adjustments into the next `keyword_plan`. Done.
3. Add regression tests for performance-weighted selection. Done.

### Phase E: Operational Hardening

1. Harden Chrome Studio metrics capture with `studio_metrics_capture_v2`, structured metric nodes, snapshots, capture quality, and warnings. Done.
2. Add bridge-side metrics enrichment before JSONL append, including normalized metrics and capture-quality flags. Done.
3. Add paid/external image budget controls around script quality gates and daily caps. Done.
4. Add HA monitor cadence at 2h, 24h, and 72h after publish/schedule reference time. Done.

## 20. Engineering Rules

- Do not hardcode strategy language in `pipeline.py`.
- Put keywords, templates, weights, thresholds, and risk terms in JSON config.
- Every new flow must have a test that verifies artifact creation or scoring behavior.
- Every external/public claim must retain source ids.
- Every realistic AI visual must keep AIGC disclosure path intact.
- Local fallback images or fallback TTS may produce previews but must block publish readiness.

## 21. Current Status

Implemented:

- `keyword_plan.json`
- `signal_snapshot.json`
- `topic_pool.json`
- `topic_plan.json`
- `editorial_plan.json`
- `selected_script.json`
- `content_plan.json`
- `visual_plan.json`
- `tts_plan.json`
- `render_manifest.json`
- `upload_plan.json`
- `performance_feedback.json`
- hot-topic keyword expansion from recent signal candidates
- generic single-keyword caps
- script-first image planning
- visual diversity gates
- ElevenLabs publish gate
- performance-weighted keyword, topic, and format reranking
- Chrome Extension Studio metrics capture v2 and bridge enrichment
- paid/external image budget gating before provider calls
- post-publish monitor cadence for 2h, 24h, and 72h windows

Next implementation target:

1. Run paid image provider smoke only with `AINO_PRIVACY_MODE=cloud_explicit` and an explicit budget window.
2. Capture real Studio detail metrics through the extension after the next actual scheduled post is live.
3. Use 2h/24h/72h monitor reports to tune hook, visual pattern, and slot selection.
4. Keep `config/reference_codebook_provisional.json` disabled until a 20+ direct-URL benchmark table is available.
5. Validate any new Deep Research benchmark with `python -m src.core.tiktok_aino.reference_benchmark <path> --json` before promoting reference-derived configs.

Upload automation should remain gated by `publish_ready`; fallback images or fallback TTS continue to block scheduling.
