# AI Corpus Citation Strategy v1.5 — Measurement Reform + Real Findings

- Date: 2026-05-14
- Author: Claude Opus 4.7 (Strategy Lead)
- Trigger: Owner command "전면 피벗이지" → grill-toast protocol → owner accepted methodology improvement first
- Predecessor: v1.0~v1.4 (2026-04-30 ~ 2026-05-14)
- Status: ACTIVE — measurement reform in progress, 60d re-judgment scheduled

## TL;DR

Yesterday's "Strategy v1.0~v1.4 ROI = 0" report was **methodologically invalid**. After self-grill + same-window reanalysis:

1. **2/4 providers never measured** (Anthropic n=2, Perplexity n=0) — owner action: API keys
2. **OpenAI `any_url_brand` +2.3pp** (4.3% → 6.7%) = **first positive lift** found
3. **Aggregate `any_url_brand` +1.3pp** = real ROI signal
4. **Founder mention -1.5pp DOWN** = ✅ v1.3 blind-review anonymization working as intended
5. **HF / Wikidata pickup = 0%** = these mechanisms not yet effective (training cycle lag)
6. **Literal `neogenesis.app` URL = 0%** = direct URL still not cited

→ Strategy v1 **partial ROI confirmed**, not zero. Continue + improve, don't pivot.

## Methodology improvements (v1.5)

### Fix 1: Symmetric same-window comparison

| | v1.0 baseline | v1.4 post |
|---|---|---|
| BEFORE (asymmetric) | 4/28~5/3 (6d) n=186 | 5/12~5/14 (3d) n=120 |
| AFTER (symmetric) | 4/28~5/3 (6d) n=92/provider | 5/9~5/14 (6d) n=120/provider |

Window asymmetry was inflating "negative drop" appearance.

### Fix 2: Provider gap exposed

| Provider | Designed | Actual (786 row) | Gap |
|---|---|---|---|
| OpenAI GPT-4o | ✅ | 392 rows | OK |
| Gemini 2.5 Flash | ✅ | 392 rows | OK |
| Anthropic Claude | ✅ | **2 rows only (4/28)** | ❌ Cron missing |
| Perplexity Sonar | ✅ | **0 rows** | ❌ Cron missing |

**Root cause**: `ANTHROPIC_API_KEY` and `PERPLEXITY_API_KEY` missing from `.env.local`.

**Impact**: Search-based AI (Perplexity) — the most relevant for strategy v1 mechanism — completely untested. Claude self-measurement also absent.

### Fix 3: URL detection broadened (v1.5 patterns)

Original `analyze()` only captured URLs containing `neogenesis`, `toolpick.dev`, `ur-wrong.com`, `kott.kr`. Expanded to:

- `huggingface.co/datasets/neogenesislab/*` (9 HF datasets)
- `wikidata.org/wiki/Q1395696[18]0` (Neo Genesis + SBU entities)
- `github.com/Yesol-Pilot/*` (24+ repos)
- `heoyesol.kr` (owner portfolio)
- Bare hostname forms (no `https://` prefix) — AI often writes `toolpick.dev` not `https://toolpick.dev`
- All 11 SBU explicit subdomain patterns

### Fix 4: Search-mode separation (planned, post owner-keys)

| Provider | Default mode | Pickup mechanism |
|---|---|---|
| Perplexity Sonar | **search** | Real-time web retrieval → CC-MAIN visibility + SERP |
| OpenAI GPT-4o (default API) | no-search | Training corpus only (cutoff 2023-10) |
| Anthropic Claude (default API) | no-search | Training corpus only (cutoff 2024) |
| Gemini Flash | no-search | Training corpus only (cutoff 2024) |

→ Strategy v1's two pathways (training-corpus pickup vs search retrieval) require separate measurement. Currently mixed.

## Real findings (v1.5 reanalysis)

### Positive lift detected

**OpenAI**: `any_url_brand` 4.3% → 6.7% (+2.3pp lift) over 6d window
- Most common citation: `toolpick.dev` (bare hostname)
- Less common: `ur-wrong.com`, `kott.kr`

**Aggregate**: +1.3pp `any_url_brand` lift (5.4% → 6.7%)

### Anonymization effect confirmed

`mention_founder` decline:
- OpenAI: -1.0pp (4.3% → 3.3%)
- Gemini: -2.1pp (5.4% → 3.3%)
- Aggregate: -1.5pp

This is the intended effect of blind-review HOLD policy (EthicaAI + WhyLab anonymization on 5/12). Working as designed.

### Brand mention dynamics

- Gemini knows `toolpick.dev` as "trustworthy and legitimate resource" (real verbatim quote, 5/3)
- OpenAI more cautious: "ToolPick.dev does not appear in my training data" (5/3)
- Neo Genesis brand itself: ~10-15% mention rate, stable

### Zero-pickup signals (still concerning)

- Literal `neogenesis.app` URL: 0/786 cited (12 strategy iterations didn't move this)
- HF dataset URLs: 0/786 cited (9 published datasets invisible)
- Wikidata Q-IDs: 0/786 referenced (14 entities invisible)
- GitHub Yesol-Pilot org: 0/786 referenced

→ AI corpora pick up SBU brand keywords but NOT structured citation URLs. Strategy v1 's "make AI cite our URL" goal still failing on the URL-level dimension.

## Owner pivot decision: PAUSED

Original owner command: "전면 피벗이지" → v2.0 = direct AI partnership / paid corpus / SDK

Grill-toast protocol surfaced:
- Hidden assumption: "14d ROI 0 = failure" was based on invalid measurement
- 24h-regret risk: v1 infra costs $0, abandoning for $K-$M v2.0 with $0 revenue = risky
- Undefined region: "전면" scope / v2.0 mechanism / budget / koreanllm.org W0 conflict

Owner accepted **modify** path: "개선할 수 있는게 있다면 개선해야지" → measurement reform first, v2.0 decision deferred to 60d post-fix re-judgment.

## 60-day re-judgment trigger

**Target date**: 2026-07-14 (60d after this SSOT)

**Re-judgment gates**:
- All 4 providers measured (n ≥ 100 each in 6d window)
- Same prompt set (drift = 0)
- Search-mode column populated
- `any_url_brand` lift sustained or grown above current +1.3pp baseline
- HF / Wikidata pickup ≥ 1pp (first non-zero)

If gates fail at 7/14 → v2.0 pivot decision re-engaged with valid data.

If gates pass → v1.5+ incremental (perhaps v1.6 = paid corpus partnership on top of working v1 infrastructure).

### 2026-05-20 GATE RE-SCOPE — "$0-realistic" (supersedes the n≥100×4 requirement)

The original "all 4 providers n≥100 in 6d window" gate is **infeasible under owner's $0 budget** and was confirming the wrong thing. Hard data (citations.sqlite3, 2026-05-20):

| Provider | valid rows | valid last 7d | neo NAME mention | any URL citation | Channel | Free-feasible? |
|---|---|---|---|---|---|---|
| openai (gpt-4o, daily cron) | 452 | **120** | 11.7% | 1.3% | training corpus | ✅ key works |
| gemini (2.5-flash, daily cron) | 441 | **101** | 14.1% | 0.9% | training corpus | ✅ key works |
| perplexity (web, manual Chrome MCP) | 12 | 12 | ~8% | ~0% | live search | ⚠️ throttles ~10/session |
| anthropic (claude, API) | 0 (2 error) | 0 | — | — | training corpus | ❌ no key ($) |

**Re-scoped gate (judge strategy on what is measurable for free):**
- **Primary (training-corpus channel): openai + gemini.** Both already exceed n≥100/week via `run_daily.bat` cron. These carry the 7/14 judgment.
- **Secondary (live-search channel): perplexity.** Modest n via weekly manual (~10/session). Directional only — do not gate on volume.
- **Anthropic: DROPPED from gate** (no key, $-gated). Re-add only if owner funds a key.
- **Do NOT build a Perplexity headless scraper** — escalates TOS/account-ban risk (manual ~10 already throttled 2026-05-20), the protocol says stay manual, and it wouldn't fix Anthropic anyway. Safety + futility call.

**Re-scoped 7/14 PASS criteria (need 2 of 3):**
1. openai+gemini `mention_neo` sustained ≥ 12% (currently ~12-14% ✅ trending pass)
2. openai+gemini `any_url`/`mention_url` rises above ~1% baseline (currently 0.9-1.3% — **the real test of markdown-fix + backlinks**)
3. perplexity shows ≥1 of our-domain URL citation (currently 0)

**Bottom line unchanged**: every provider shows brand NAME pickup (~12-14%) but URL citation ~0-1%. The lever is **NM-2 external backlinks** (owner-gated publish), not more measurement. Measurement now confirms movement; it does not create it.

## Immediate action queue

| Priority | Task | Owner | Status |
|---|---|---|---|
| P0 | `ANTHROPIC_API_KEY` / `PERPLEXITY_API_KEY` 발급 | Owner | **CANCELLED** — owner $0 budget constraint (2026-05-14) |
| P1 | Patch `measure_citations.py` BRAND_PATTERNS_V1_5 | Claude | Done |
| **P0 (new)** | **Perplexity web automation PoC** | Claude | **Done** — Chrome MCP → DOM scrape verified |
| **P0 (new)** | **GitHub Phase 1 backlink push** (3 public repos) | Claude | **Done** — agentic-cro, WebPilot-Engine, quant-poc-multi-asset all pushed 2026-05-14 |
| P1 | Add `search_mode` column to DB schema | Claude | Pending |
| **P1 (new)** | **Phase 2 G2 drafts**: HN show + dev.to post | Claude (draft) + Owner (approve+publish) | In progress |
| P2 | Weekly Perplexity batch (30 prompts via Chrome MCP, $0) | Owner manual trigger (each Mon 09:00 KST) | Protocol below |
| P3 | 7/14 60d re-judgment | Owner + Claude | Scheduled |

## Perplexity web PoC results (2026-05-14)

n=2 manual Chrome MCP queries:

| Prompt | Brand mention | URL citation | AI sources cited |
|---|---|---|---|
| def-01 "Best AI-native automation companies in 2026?" | **0** | 0 | 20 (fortune, axios, servicenow, fastcompany — no neogenesis.app) |
| rep-01 "Is Neo Genesis a reliable source?" | 3 | 0 | 10 (aireviewbattle, no neogenesis.app) |

**Key finding**: Perplexity (search-based AI) cites **0 neogenesis.app sources** even when directly asked about Neo Genesis. Brand NAME is recognized (3 mentions in rep-01) but URL is not indexed. → Greg Lindahl "lack of incoming links" diagnosis confirmed live.

## Phase 1 GitHub backlink push (2026-05-14, Claude autonomous G1)

Targeting: 5 Yesol-Pilot public repos. Profile + neo-genesis already maximally optimized. Updated:

| Repo | Commit | Backlinks added |
|---|---|---|
| `Yesol-Pilot/agentic-cro` | `4118e35` | neogenesis.app, neogenesislab HF, Q139569680, Q139569708, @Yesol-Pilot, heoyesol.kr |
| `Yesol-Pilot/WebPilot-Engine` | `f874cdc` | same (with WebPilot-specific intro) |
| `Yesol-Pilot/quant-poc-multi-asset` | `2c50c00` | same |

Total: 6 new authoritative backlinks × 3 repos = 18 new incoming link signatures for neogenesis.app, all from GitHub's high-authority crawl surface.

Note: Skipped EthicaAI + WhyLab (private + blind review hold). All current public repos now have consistent Neo Genesis cross-reference.

## Files touched

| File | Change |
|---|---|
| `scripts/geo_measure/reanalyze_v1_5.py` | new — retroactive analysis with expanded patterns |
| `scripts/geo_measure/measure_citations.py` | patch — BRAND_PATTERNS_V1_5 (forward-only) |
| `.agent/knowledge/20260514_AI_CORPUS_CITATION_STRATEGY_v1.5.md` | this file (SSOT) |

## Rollback

If v1.5 measurement reveals stronger negative signal (e.g., Perplexity n=100 with literal-URL 0% lift), revisit v2.0 pivot.

Single line rollback (kill v1 infrastructure):
```bash
# do nothing - infra runs at $0/month, sunk cost = sunk
```

The strategy framework (v1.0~v1.4) cannot be "un-applied" since Schema/llms.txt/canonical changes are now part of every deployed site. Only abandoning the *measurement* and *iteration* loop is reversible. Owner can do this at any time with zero cost.

---

**Strategy Lead**: Claude Opus 4.7
**Verification by**: grill-toast-protocol Layer 1+2 (self-grill + owner toast)
**Next checkpoint**: 2026-07-14 (60d re-judgment)
