# Receipt Room 11:59 Design

## Conclusion

`Receipt Room 11:59` is not a prompt-to-video feature. It is a planning gate that turns global pop-culture gossip signals into a symbolic tabloid microdrama plan. The video generator only runs after the issue passes source, trend, drama, motion, and policy gates.

## Research Inputs

- TikTok Next 2026: Reali-TEA, Curiosity Detours, and Emotional ROI support real-time cultural tea, comment-led discovery, and emotional payoff.
- TikTok Trends guidance: trend selection should use platform trend signals rather than intuition alone.
- Pew 2026 TikTok research: TikTok remains broad among US adults and especially young users, so pop-culture entertainment is a strong global proxy.
- Vogue TikTok Trend Tracker: weekly trend signals include fan-reaction topics around Euphoria, Billie Eilish, Olivia Rodrigo, nostalgia, and celebrity culture.
- Omdia 2026 microdrama research: vertical one-to-two-minute microdramas are becoming a core mobile engagement format.
- TikTok AIGC and Integrity policies: realistic AI people, voice cloning, false public-figure contexts, private figures, and minors require strict boundaries or blocking.

Sources are registered in `config/receipt_room_strategy.json`.

## Agent Board

| Persona | Responsibility | Output |
| --- | --- | --- |
| Trend Scout | Collect structured issue candidates from trend and entertainment sources | Candidate JSON with source IDs and trend signals |
| Gossip Analyst | Split verified facts, reported sightings, fan speculation, and unsupported rumors | Evidence levels and claim sensitivity |
| Risk Editor | Block likeness, voice clone, minors, private figures, endorsements, and unsupported sensitive claims | Risk labels, blockers, warnings |
| Drama Architect | Convert the issue into a microdrama format | Episode format, hook, story beats |
| Character Designer | Convert real people into symbolic archetypes | Screen characters and visual rules |
| Shot Director | Build a motion-first shot list | Visual prompts, captions, camera motion |
| Roast Gate | Reject static, vague, low-conflict, or unsafe plans before generation | Pass/fail gate and revision blockers |

## Structured Input

The planner expects an issue candidate, not a free-form message.

```json
{
  "title": "The red carpet run-in that split the internet",
  "summary": "A public celebrity run-in became a fan debate.",
  "entities": ["Public Figure A", "Public Figure B"],
  "source_ids": ["people", "vogue_trend_tracker", "tiktok_creative_center"],
  "keywords": ["red carpet", "awkward", "fan theory"],
  "trend_signals": {
    "trend_velocity": 86,
    "fandom_conflict": 88,
    "visual_drama": 92,
    "microdrama_fit": 85,
    "search_intent": 76,
    "freshness": 80,
    "originality": 70
  },
  "claims": [
    {
      "text": "The public appearance was reported by entertainment media.",
      "evidence_level": "reported",
      "sensitivity": "ordinary",
      "source_ids": ["people"]
    },
    {
      "text": "Fans debated whether the interaction was awkward.",
      "evidence_level": "fan_speculation",
      "sensitivity": "ordinary",
      "source_ids": ["tiktok_creative_center"]
    }
  ]
}
```

## Scoring

The score is config-owned:

```text
total =
  source_reliability * 22
+ trend_velocity * 14
+ fandom_conflict * 16
+ visual_drama * 14
+ microdrama_fit * 12
+ search_intent * 10
+ freshness * 8
+ originality * 4
- risk_penalty
```

Minimums:

- `minimum_to_plan`: 72
- `minimum_to_generate`: 82
- weak source base adds a penalty
- hard policy blockers force `blocked`

## Video Contract

Every accepted episode must contain:

- a two-second cultural hook
- a verified fact card
- a fan-speculation card
- a contradiction or uncertainty beat
- a symbolic microdrama scene
- a verdict meter
- a comment jury prompt

Every shot needs motion. Static beauty shots fail the roast gate.

## Character Reference Contract

The video model must not invent character design from scratch. Generate and approve character references before paid video.

Required:

- adult-coded symbolic characters
- expressive faces and readable emotion
- full visible character design with a strong body line
- exaggerated archetype features through wardrobe, posture, props, and body language
- female glamour can use fitted couture, high-slit or corset-inspired silhouettes, confident sensual posture, polished hair and makeup
- male characters should also be exaggerated through status, tailoring, posture, and social tension

Creative briefs should stay positive and heat-forward. Internal risk gates stay in code and should not be pasted into image or video prompts.

## Privacy Contract

`AINO_PRIVACY_MODE=local_only` is the default for generation work.

- Local-only mode blocks external image generation, ElevenLabs TTS, paid Veo/Vertex calls, and live network trend research unless a network-research flag is explicitly supplied. Artifacts, manifests, QA files, and reports remain on the local filesystem.
- Cloud generation requires `AINO_PRIVACY_MODE=cloud_explicit` plus the provider-specific paid/submit switch. This mode accepts that provider-side request, billing, abuse-prevention, cache, or service logs may exist.
- Do not promise "no external record" for OpenAI, Gemini, Vertex, ElevenLabs, TikTok, or public web research. The only defensible no-provider-record mode is local rendering or local model inference.
- If the episode needs cloud video quality, create and approve local character references first, then make a single explicit cloud run with the minimum prompt and asset payload needed for final generation.

## Safety Contract

Safety checks are backend gates, not creative copy. The planner separates verified reporting, fan speculation, and commentary, then emits heat-forward fictionalized visual prompts without publishing the internal prohibition list.

## Execution

```powershell
python -m src.core.tiktok_aino.receipt_room_planner --demo --output output\receipt_room_demo_plan.json
```

The output is an episode plan for later Sora/Veo generation. It is not an upload package and should not publish anything by itself.
