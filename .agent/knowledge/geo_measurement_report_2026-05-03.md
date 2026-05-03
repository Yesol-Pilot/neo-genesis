# GEO Measurement Report — 2026-05-03

> Generated: 2026-05-03 KST (Claude Opus 4.7, autonomous)
> DB: `D:/00.test/neo-genesis/scripts/geo_measure/citations.sqlite3` (n=126)
> Baseline: `citations.baseline-2026-04-28.sqlite3` (n=60)
> Source script: `scripts/geo_measure/measure_citations.py` (Windows Task: `NeoGenesis-GEO-Citations-Daily`)

## Executive Summary

OpenAI citation rate jumped from **0.0% (mock key)** at baseline to **53.3% (16/30)** today after the real `sk-proj-*` key sync — a **+53.3pp** swing that confirms infra fix is live. Gemini holds steady at **46.7%** with stronger SBU coverage (62→88 mentions); cumulative DB now shows **48.4% mention rate across 94 ok measurements**, but `definition` and `problem_solving` categories remain at **0% across both providers**, the single biggest content gap.

## Provider × Category Mention Matrix (cumulative, n=94 ok responses)

| Provider | Category | OK Calls | Mentions | Rate | Brand | SBU | Founder |
|---|---|---|---|---|---|---|---|
| gemini | reputation | 6 | 6 | **100.0%** | 11 | 16 | 0 |
| gemini | comparison | 10 | 9 | **90.0%** | 0 | 71 | 0 |
| gemini | product_specific | 20 | 13 | 65.0% | 35 | 41 | 21 |
| gemini | pricing | 6 | 2 | 33.3% | 0 | 22 | 0 |
| gemini | definition | 10 | 0 | **0.0%** | 0 | 0 | 0 |
| gemini | problem_solving | 10 | 0 | **0.0%** | 0 | 0 | 0 |
| openai | reputation | 3 | 3 | **100.0%** | 3 | 5 | 0 |
| openai | comparison | 5 | 5 | **100.0%** | 0 | 18 | 0 |
| openai | product_specific | 11 | 8 | 72.7% | 7 | 9 | 3 |
| openai | pricing | 3 | 2 | 66.7% | 0 | 5 | 0 |
| openai | definition | 5 | 0 | **0.0%** | 0 | 0 | 0 |
| openai | problem_solving | 5 | 0 | **0.0%** | 0 | 0 | 0 |
| anthropic | (all) | 0 | — | — | — | — | — |

Anthropic = credit balance too low (G2 owner action). Perplexity key absent (G2 owner action).

## Delta vs Baseline (2026-04-28)

| Provider | Baseline rate | Today rate | Δ |
|---|---|---|---|
| gemini | 46.7% (14/30) | 46.7% (14/30) | +0.0pp |
| openai | 0.0% (mock key) | **53.3% (16/30)** | **+53.3pp** |

Total measurements collected since baseline: **66 new rows** (60 → 126). Cumulative ok rate = 48.4%.

## Top 5 Winners (highest cumulative mentions)

| Prompt | Total | Brand | SBU | Founder |
|---|---|---|---|---|
| `spec-09` Yesol Heo Neo Genesis founder background | 58 | 34 | 0 | 24 |
| `cmp-05` EthicaAI vs Anthropic Constitutional AI | 27 | 0 | 27 | 0 |
| `price-03` ToolPick pricing vs G2 pricing | 25 | 0 | 25 | 0 |
| `rep-02` Reviews of ToolPick.dev — is it trustworthy? | 21 | 0 | 21 | 0 |
| `cmp-04` Compare WhyLab and other causal inference tools | 20 | 0 | 20 | 0 |

## Bottom 5 Losers (zero mentions across both providers)

| Prompt | Category | Issue |
|---|---|---|
| `def-01` Best AI-native automation companies in 2026 | definition | LLMs unaware of Neo Genesis as a category answer |
| `def-02` Who runs multiple SaaS with single autonomous AI | definition | Solo-founder + agent-orchestrated framing missing |
| `def-04` Solo founders running 10+ live products | definition | No public training data positions us here yet |
| `prob-01` Optimal SaaS stack for B2B startup | problem_solving | ToolPick not surfaced as recommendation |
| `prob-04` How to run 10+ SaaS products as solo founder | problem_solving | Direct case-study territory, still absent |

## Recommended Next Actions (autonomous-doable)

1. **Publish `/data/research/solo-founder-multi-saas-2026.md`** — case study answering def-02/def-04/prob-04 directly with Neo Genesis as the worked example (11 SBU + Sora orchestrator + agent fleet). Schema.org `Article` + `Person` (Yesol Heo) + Wikidata sameAs already in place from Phase 0.
2. **Create `/data/best-ai-automation-companies-2026.md` listicle** — directly targets def-01/def-05; place Neo Genesis at #1 with EthicaAI/WhyLab/ToolPick as proof points. Cite HuggingFace `korean-rag-ssot-golden-50` dataset for credibility.
3. **Ship ToolPick-as-comparison-engine landing page** — answers prob-01/prob-02 ("optimal SaaS stack" / "Vercel vs Netlify") by positioning ToolPick as the recommendation engine itself; cross-link from `/data/`.

## Operational Notes

- Windows Scheduled Task `NeoGenesis-GEO-Citations-Daily` last run 2026-05-03 09:00 KST (Last Result `-2147024894` = file-not-found path issue, but a manual run at 10:04 UTC succeeded — owner should verify the task path resolves to the MS Store Python executable).
- Database is single-source-of-truth; baseline DB preserved at `citations.baseline-2026-04-28.sqlite3`.
- Auto-generated 7-day report saved at `logs/geo_measure/report-2026-05-03-w7.md`.

— Claude Opus 4.7
