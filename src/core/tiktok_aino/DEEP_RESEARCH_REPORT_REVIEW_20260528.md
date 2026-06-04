# Deep Research Report Review - AiNo 2026-05-28

Reviewed source: `C:\Users\yesol\Downloads\deep-research-report_aino.md`  
Project snapshot: `output\tiktok_aino_reference_research\deep-research-report_aino_20260528.md`  
Follow-up request: `DEEP_RESEARCH_FOLLOWUP_REQUEST_20260528.md`  
Reviewed at: 2026-05-28 KST  
Applies to: `올바른 AiNo` / `@leftaino`

## 1. Conclusion

The report is useful as a policy, economics, and trust-architecture layer, but it is not enough as a top-reference benchmark.

Adopt it for these decisions:

1. Move the default production posture from "provocative card-news" to "evidence briefing with visible source cards."
2. Treat `60~80s` as the main monetization/search format, with `24~45s` as an acquisition booster only.
3. Add an explicit `risk_flags.json` gate between fact extraction and script generation.
4. Make TikTok the discovery channel, YouTube Shorts the asset/monetization hub, and Instagram Reels a secondary experiment channel.
5. Keep AIGC disclosure, source links, and correction loops as default publishing metadata.

Do not accept it as complete reference research because it did not provide the requested 20~30 post-level benchmark table with URLs, dates, metrics, first-3-second coding, caption density, TTS tone, and CTA type.

## 2. Verification Notes

The report contains Deep Research citation tokens such as `turn46view0`, not reusable public URLs. Before hardcoding policy-sensitive assumptions, use official sources.

Current official-source checks aligned with the report:

| Claim area | Verified basis |
| --- | --- |
| TikTok Creator Rewards favors high-quality original content over one minute and uses originality, play duration, search value, and engagement signals | TikTok Newsroom: `https://newsroom.tiktok.com/introducing-the-new-creator-rewards-program/?lang=en` |
| TikTok requires labeling realistic AI-generated images/audio/video and warns against fake authoritative sources or misleading public-figure contexts | TikTok Support: `https://support.tiktok.com/en/using-tiktok/creating-videos/ai-generated-content` |
| TikTok political/GPPPA accounts have monetization and incentive restrictions | TikTok Support: `https://support.tiktok.com/en-GB/using-tiktok/growing-your-audience/government-politician-and-political-party-accounts` |
| TikTok integrity rules cover misinformation, civic/election integrity, synthetic media, fake engagement, and paid political advertising | TikTok Community Guidelines: `https://www.tiktok.com/community-guidelines/en/integrity-authenticity/` |
| YouTube requires disclosure for realistic meaningfully altered/synthetic content and says disclosure alone does not limit audience or monetization eligibility | YouTube Help: `https://support.google.com/youtube/answer/14328491` |
| YouTube Partner Program Shorts threshold includes 1,000 subscribers plus 10 million valid public Shorts views in 90 days | YouTube Help: `https://support.google.com/youtube/answer/72851` |
| Google Cloud TTS has Korean voices including Chirp 3 HD / Neural2 / WaveNet tiers | Google Cloud docs: `https://docs.cloud.google.com/text-to-speech/docs/list-voices-and-types` |
| ElevenLabs supports Korean through multilingual models and defaults API TTS to `eleven_multilingual_v2` | ElevenLabs docs: `https://elevenlabs.io/docs/api-reference/text-to-speech/convert` |

## 3. What Changes From The Current Design

### 3.1 Format Priority

Existing design:

- `moment_short` 24~45s for acquisition.
- `reward_explainer` 61~75s for rewards/search.
- `three_part_arc` for series.

Report-driven correction:

- Default daily production should start from `evidence_briefing_75`.
- `moment_short` remains useful, but it should not be the default for civic/political issues unless the evidence density is low and the goal is only acquisition.
- The pipeline should not stretch a weak script past 60s. The required condition is source density, not duration.

Recommended mapping:

| Format | Role | Default use |
| --- | --- | --- |
| `evidence_briefing_75` | Main format | 60~80s, one claim, source card in first 12s |
| `moment_short` | Acquisition booster | 24~45s, one scene, one judgment question |
| `timeline_explainer` | Trust builder | 65~90s, event sequence and accountability line |
| `misread_correction` | Search/save content | 60~80s, common misunderstanding corrected with source |
| `three_part_arc` | Return/series format | Only after part 1 proves retention or comment quality |

### 3.2 Topic Scoring

Previous architecture over-weighted audience emotion and comment conflict. The report argues that this increases short-term engagement but weakens platform trust and monetization.

Use this revised top-level score:

| Score item | Weight | Notes |
| --- | ---: | --- |
| `evidence_density` | 30 | Two or more credible sources, source quote, clear claim boundary |
| `civic_value` | 25 | Public interest, accountability, institutional relevance |
| `recency` | 15 | Freshness and active search/news signal |
| `visualizability` | 15 | Can be shown through document, timeline, hearing room, newsroom, data card, or civic scene |
| `explainability_75s` | 10 | One claim can be explained in 60~80s without padding |
| `risk_adjustment` | 5 | Positive only when legal/platform risk is controlled; otherwise penalty |

Keep `left_emotion` and `comment_conflict`, but demote them to secondary fields under `audience_response`. They may select the CTA, but they must not override weak evidence.

### 3.3 New Artifact Gate

Add `risk_flags.json` as an explicit artifact. Do not hide these checks inside generic `quality` fields.

Minimum schema:

```json
{
  "version": "risk_flags_v1",
  "election": {"level": "none|low|medium|high", "reason": "..."},
  "aigc": {"level": "none|low|medium|high", "requires_label": true},
  "defamation": {"level": "none|low|medium|high", "reason": "..."},
  "copyright": {"level": "none|low|medium|high", "reason": "..."},
  "public_importance": {"level": "low|medium|high", "reason": "..."},
  "political_actor_monetization": {"level": "none|low|medium|high", "reason": "..."},
  "manual_review_required": true,
  "publish_blockers": ["..."],
  "safe_rewrite_notes": ["..."]
}
```

Gate rule:

- Any `high` in election, defamation, AIGC public-figure, fake authoritative source, or copyright requires manual review.
- Missing source link requires block.
- Less than two distinct credible sources blocks evidence briefing.

### 3.4 Source Card Requirement

Every 60~80s evidence briefing must include a visible source moment within 3~12 seconds.

Source card fields:

```json
{
  "source_name": "기관/언론/문서명",
  "source_type": "official|news|court|assembly|poll|platform_policy",
  "published_at": "YYYY-MM-DD",
  "claim_boundary": "confirmed_fact|reported_claim|opinion|unverified",
  "display_text": "화면에 보여줄 1줄 출처 문구",
  "source_url": "https://..."
}
```

This source card should drive the image plan. If there is no source card, do not generate a fake document image.

### 3.5 TTS Provider Decision

The report recommends:

- Google Cloud TTS first for Korean news-style briefing.
- ElevenLabs second for character voice and expressive brand identity.
- OpenAI TTS for prototype, English version, or fallback.

Operational decision:

- Do not remove the current ElevenLabs path because the owner already has an `Anna Kim` workflow and voice settings.
- Add a POC track: compare Google Korean news-style voice vs ElevenLabs Anna Kim on the same 75s script.
- Choose by measured naturalness, pronunciation errors, retention drop around first 12 seconds, and cost.

### 3.6 Platform Role

Current TikTok-only operational thinking is too narrow for monetization.

Adopt this funnel:

| Platform | Role |
| --- | --- |
| TikTok | Discovery, fast issue testing, comments/search signal |
| YouTube Shorts | Long-term archive, Shorts monetization path, bridge to long-form |
| Instagram Reels | Brand surface, format experiment, secondary distribution |

This does not change the immediate TikTok upload automation priority, but it changes how content is generated: source cards, titles, captions, and descriptions must be reusable across platforms.

## 4. What To Reject Or Defer

| Report item | Decision | Reason |
| --- | --- | --- |
| `07:00 / 12:00 / 18:00` slots | Defer | Current operational slots are `08:10 / 11:20 / 19:30 KST`; use report times as experiment variables only |
| Fully automated publishing from day one | Reject | Report itself recommends 3-week policy-compliant semi-automation first |
| Pure "comment conflict" optimization | Reject | Long-term trust, policy risk, and monetization suffer |
| Google Cloud TTS replacing ElevenLabs immediately | Defer | Needs Korean voice POC against existing Anna Kim settings |
| Report as final reference benchmark | Reject | Lacks post-level reference table and direct URLs |

## 5. Implementation Priority

### P0

1. Add `risk_flags.json` generation and publish gate.
2. Revise topic score to prioritize `evidence_density` and `civic_value`.
3. Add `source_card` to script and storyboard contracts.
4. Add `evidence_briefing_75` as the default format when evidence density passes.
5. Add AI/source/correction disclosure fields to `publish_payload` / `upload_plan`.
6. Keep daily performance measurement once per day only; do not create per-post polling loops.

### P1

1. Build TTS A/B harness: ElevenLabs Anna Kim vs Google Cloud Korean voice.
2. Create platform-specific metadata: TikTok caption, YouTube Shorts title/description, Instagram caption.
3. Add 21-day experiment tracking for hook type, source-card position, CTA type, TTS voice, and completion rate.

### P2

1. Build the missing 20~30-post benchmark dataset.
2. Add YouTube upload/export path.
3. Add longer-form follow-up funnel: 3~5 minute explanation script, newsletter/Telegram summary, correction log.

## 6. Required Next Research

The missing research is now narrower:

1. Select 20~30 Korean political/news/civic short-form reference posts.
2. Code each post by URL, date, platform, length, views, likes, comments, first 3s hook, source card presence, caption density, scene type, TTS/voice style, CTA type, and risk posture.
3. Use the coded table to tune `reference_fit.json`, not generic commentary.

Until this benchmark exists, the report should guide risk and operating model, but not visual style or viral format selection.

Use `DEEP_RESEARCH_FOLLOWUP_REQUEST_20260528.md` as the exact prompt for this follow-up research. If the next report again lacks URL-backed post-level rows, reject it as insufficient and request the table first.
