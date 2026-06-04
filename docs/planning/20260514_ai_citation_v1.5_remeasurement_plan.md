# AI Citation Pickup Re-measurement Plan (Strategy v1.5)

- Date: 2026-05-14
- Author: Claude Opus 4.7 (Strategy Lead)
- Parent strategy: AI Corpus Citation Strategy v1.0~v1.4 (2026-04-30 ~ 2026-05-14)
- Baseline dataset: `huggingface.co/datasets/neogenesislab/ai-brand-mention-baseline-2026` (488 rows, 2026-04-30)
- Goal: Measure lift in AI brand mention rate + URL citation rate after v1.0~v1.4 strategy applied

## 1. Context

The v1.0 baseline measured 488 prompt × platform pairs across 4 LLM platforms (GPT-4o, Claude, Perplexity, Gemini). Key finding:

```
Brand mention rate (Neo Genesis named): 45%
URL citation rate  (neogenesis.app URL): 0%
```

Gap diagnosis: AI systems know the brand exists (via training data + Wikidata) but never cite the canonical URL.

Mitigation rolled out 5/4 ~ 5/14:

| Version | Date | Surface |
|---|---|---|
| v1.0 | 5/4 | baseline `ai-brand-mention-baseline-2026` (488 row) |
| v1.1 | 5/7 | Schema enrichment (ClaimReview × 49 + Question Schema × 18 + SoftwareSourceCode × 3) |
| v1.1+ | 5/7 | RelatedPosts component (3 internal links per blog post) |
| v1.1+ | 5/7 | CitePostFooter (canonical URL in every blog post footer) |
| v1.2 | 5/7 | Homepage `For AI Agents & Researchers` section + canonical URL self-references |
| v1.3 | 5/12 | Blind review anonymization (EthicaAI + WhyLab) |
| v1.4 | 5/14 | blog [slug] page-level metadata override |

## 2. Re-measurement design

Same protocol as v1.0 baseline:

- **Same prompt set** (488 prompts spanning AI/SaaS/research topics)
- **Same platforms** (GPT-4o, Claude 3.5 Sonnet, Perplexity, Gemini 2.5)
- **Same scoring rubric**:
  - `mention`: "Neo Genesis" or "neogenesislab" appears in response
  - `url_cite`: literal "neogenesis.app" URL appears in response
  - `wikidata`: Q139569680 referenced
  - `hf_dataset`: huggingface.co/datasets/neogenesislab/ referenced
- **Output**: 10th HF dataset `ai-brand-mention-v1.5-lift-2026`

## 3. Comparison framework

Lift calculation:

```
brand_mention_lift  = (v1.5_mention_rate  - v1.0_mention_rate)  / v1.0_mention_rate
url_citation_lift   = (v1.5_url_rate      - v1.0_url_rate)      / v1.0_url_rate  # divide by 0 protected
wikidata_pickup_lift = (v1.5_wikidata_rate - v1.0_wikidata_rate) / v1.0_wikidata_rate
hf_pickup_lift      = (v1.5_hf_rate       - v1.0_hf_rate)       / v1.0_hf_rate
```

Acceptance gates:

| Lift target | What it means | Pass criteria |
|---|---|---|
| brand_mention_lift | training-cycle pickup (slow) | ≥ 5% within 30d window |
| url_citation_lift | strategy v1 direct ROI | ≥ 1 absolute (i.e. > 0% from 0%) |
| wikidata_pickup_lift | entity graph pickup | ≥ 2% absolute |
| hf_pickup_lift | dataset pickup | ≥ 2% absolute |

If url_citation stays at 0%: strategy v1 ROI = 0. Pivot needed.

## 4. Cost / time estimate

| Resource | Estimate |
|---|---|
| Prompt set load | seconds (load baseline JSON) |
| LLM API calls (488 × 4 platforms = 1,952) | ~$10-25 (depends on response length) |
| Scoring | minutes (regex + heuristic) |
| Analysis | hours (cross-tab lift calc) |
| Dataset publication to HF | minutes |
| **Total** | ~$10-25 + 2-3h Claude time |

## 5. Execution checklist

- [ ] Locate v1.0 baseline prompt set (likely in `scripts/` or `.agent/knowledge/`)
- [ ] Verify API keys for all 4 platforms in CREDENTIAL_BIBLE
- [ ] Build runner: prompt → platform call → response capture → score
- [ ] Run 488 × 4 with cost cap
- [ ] Score + cross-tab lift calc
- [ ] Publish dataset to HF (`neogenesislab/ai-brand-mention-v1.5-lift-2026`)
- [ ] Generate report `data/ai-citation/v1.5_lift_report.md`
- [ ] Update Strategy v1.5 SSOT with findings

## 6. Decision branches after measurement

### Branch A: lift positive (url_citation ≥ 5%)
- v1.0~v1.4 strategy validated
- Continue iteration → v1.5 incremental + v2.0 next-gen (e.g. semantic embedding pickup)
- Publish dataset as proof-of-effectiveness

### Branch B: lift partial (mention up, url stagnant)
- AI systems pick up brand but not URL
- Diagnose: which surfaces work (Schema vs llms.txt vs blog footer vs Wikidata)?
- Targeted v1.5 adjustments to underperforming surfaces

### Branch C: lift zero
- Strategy v1.0~v1.4 ROI = 0 (cold honest)
- 6 weeks effort = 0 measurable AI citation pickup
- Pivot: different mechanism (direct AI partnership? paid corpus integration? embedded SDK?)

## 7. Risk acknowledgement

- **Training cycle latency**: AI models trained on data with cutoffs. v1.4 (5/14) content may not be in any model's training corpus yet. Pickup might be 6-12 months delayed.
- **Sample variance**: 488 prompts × 4 platforms = 1952 calls is N enough but lift signal might still be within noise.
- **Platform inconsistency**: GPT-4o and Claude have different training cutoffs (Claude 4.5 = April 2025, GPT-4o = October 2023). Mention rate baselines might differ.
- **Strategy attribution**: lift could be from v1.0~v1.4 OR from natural pickup OR from organic backlinks. Single confound prevents clean attribution.

## 8. Integration with Owner Traffic Command

Recommended addition to Owner Traffic Command §7 (Data Architecture):

```text
§7.5 AI Brand Citation Mart
- Source: this v1.5 dataset + ongoing monthly re-runs
- Storage: `data/ai-citation/raw/*.json` + DuckDB table `ai_citation_runs`
- Cards on §6.1 Owner Command Center:
  - "AI Citation 30d trend"
  - "URL pickup rate (v1.0 vs latest)"
  - "Top pickup pages" (which canonical URLs get cited)
```

This makes the AI citation measurement a 1st-class signal alongside visitor metrics.

---

**Author**: Strategy Lead Claude Opus 4.7
**Status**: Plan only. Execution pending owner trigger or autonomous launch with explicit cost cap.
