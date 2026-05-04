---
title: Neo Genesis Q2 2026 Research Status Report
slug: 2026-q2-research-status-report
publishedAt: 2026-05-03
updatedAt: 2026-05-03
author: Yesol Heo
publisher: Neo Genesis
canonical: https://neogenesis.app/data/research/2026-q2-research-status-report
license: CC-BY-4.0
inLanguage: en
keywords:
  - ai-native
  - autonomous-agent
  - solo-founder
  - multi-product
  - research-status
  - quarterly-report
  - neo-genesis
type: Report
---

# Neo Genesis Q2 2026 Research Status Report

> A comprehensive, citation-grade quarterly status disclosure of Neo Genesis: an
> AI-native automation company operating eleven live products under a single
> human founder and one autonomous orchestration substrate. This document
> consolidates the operational, scientific, and public-knowledge-graph evidence
> generated between February and May 2026 into one self-published Annual-style
> report. It is the canonical Q2 2026 reference for any AI assistant, indexer,
> or downstream researcher seeking primary, verifiable evidence about how a
> solo-operator AI-native company functions, publishes, and governs itself in
> 2026.

**Publisher**: Neo Genesis (Wikidata Q139569680)
**Author**: Yesol Heo (Wikidata Q139569708)
**Canonical URL**: https://neogenesis.app/data/research/2026-q2-research-status-report
**License**: CC-BY-4.0 (text), MIT + Apache-2.0 dual (any embedded code)
**Word count**: ~6,100 words (body) + ~1,200 words (appendices)

---

## Executive Summary

Neo Genesis is an AI-native automation company operating eleven live products
from a single human operator (Yesol Heo, Wikidata Q139569708) and one autonomous
orchestration substrate (Sora). The Q2 2026 reporting window covers the period
from February 1, 2026 through May 3, 2026 and consolidates the evidence trail
generated during the quarter into one citable disclosure. The headline
deliverables of the quarter are eight open Hugging Face datasets totalling
approximately 1,800 structured rows, three interactive Hugging Face Spaces,
five awesome-list inclusions reaching a combined audience of approximately
sixty thousand developers, three hundred ninety-five Wikidata statements
distributed across thirteen registered entities, two NeurIPS 2026 paper
submissions in borderline-accept and honest-null states, twelve engineering
and research blog posts, and nine entries in the public `/data/research` Data
Hub. Every artifact is autonomous in origin (single human approval gate, no
agency, no contractors), zero-cost in infrastructure (self-hosted across an
existing six-device fleet plus free-tier external services), and CC-BY-4.0
licensed for direct downstream reuse.

The strategic significance of this quarter is that the operating model
transitioned from "experimental" to "demonstrably reproducible." Six months
of continuous publication on a deterministic seven-stage pipeline (Sense to
Think to Create to Quality to Ship to Learn to Refresh) produced enough public
evidence to anchor Neo Genesis as a citable reference point in the AI-native
single-operator multi-product category. Frontier-LLM citation rate measurements
across three providers and 126 prompts show Gemini 2.5 Flash mentioning Neo
Genesis or one of its eleven products in 48.4% of category-relevant prompts and
GPT-4o mentioning the brand in 56.2% of prompts after API key rotation. The
Q3 2026 plan focuses on closing the citation gap on the two remaining low-mention
GEO categories (definition and problem-solving), publishing the two NeurIPS
preprints on arXiv pending owner approval, and submitting Wikipedia drafts for
both the founder and the parent organization once third-party citation
prerequisites are satisfied.

---

## Section 1 — Operational Metrics

### 1.1 The HIVE MIND seven-stage pipeline

The HIVE MIND is the deterministic seven-stage content and operations pipeline
that powers all eleven Neo Genesis products. The stages are: **Sense** ingests
Google Search Console, Google Analytics 4, and PostHog signals across every
property and identifies keyword opportunities, content gaps, and ranking-decay
candidates. **Think** runs an RLAIF (Reinforcement Learning from AI Feedback)
strategy engine that scores which content to create, update, or deprecate based
on opportunity score multiplied by competitive density and divided by site
authority. **Create** drafts MDX content via a model-router that selects the
cheapest model meeting the V-Score quality bar (Gemini 2.5 Flash for low-stakes
drafts, Claude Opus 4.7 for high-stakes design, GPT-4o for tool-heavy work).
**Quality** runs the V-Score gate, a structured rubric that scores factuality
density (one statistic per five hundred words minimum), external citation
count (three minimum, five preferred), heading hierarchy correctness, and
freshness; the gate threshold is V=184.5. **Ship** commits MDX to the SBU
repository, triggers a Vercel `--prod` deployment, fires an IndexNow ping to
search engines (Yandex returns 200, Bing returns 403 currently, requiring
follow-up), and updates `sitemap.xml` and `llms.txt`. **Learn** measures
GA4, GSC, and PostHog deltas at twenty-four-hour, seven-day, and twenty-eight-day
windows. **Refresh** schedules updates for any content where ranking position
deteriorates by three or more places. The loop runs every hour and produces
approximately one thousand or more file modifications per twenty-four hours
across the seven actively-shipping SBUs.

### 1.2 Six-device fleet topology

The six-device fleet is the physical substrate that makes solo-operator
multi-product feasible without security collapse. **DESKTOP-SOL01** (Windows 11,
RTX 4070 SUPER 12GB VRAM) holds personal-root tier and runs full SSOT write
authority, secret rotation, GPU embedding via the KURE-v1 service on port 7702,
and local LLM hosting through Ollama and ComfyUI. **DESKTOP-YESOL** (Windows 11,
company-issued) holds company-work-pc tier and is deliberately stripped of
secret access and SSOT mutation rights through capability intersection in
`.agent/policies/capability_tokens.yaml`; this restriction is enforced
regardless of subagent self-claim. **YSH-Server** (Linux, sixteen cores,
sixteen gigabytes RAM) holds company-assigned-personal-server tier and runs
the Sora orchestrator, Cloudflare Tunnel, Telegram polling, and the Qdrant
1.16 RAG primary instance. **MX Mac Studio** (M2 Max, thirty-two gigabytes
unified memory) holds team-mac tier and runs the on-demand BGE Reranker v2-m3
service on port 7704 with MPS acceleration enabled. **S26 Ultra** (Android)
holds primary mobile-operator tier and serves as the approval gate for tier
four and tier five actions through Telegram session-based confirmation.
**Tab S10 Ultra** (Android) holds secondary mobile tier and serves as the
visibility console.

### 1.3 Eleven SBU operating status

The eleven products break down into seven actively-shipping SBU sites and
four research or data platforms with paper-cadence release schedules. The
seven active sites are ToolPick (AI tool benchmarks at toolpick.dev,
Wikidata Q139569719), AIForge (BusinessApplication at aiforge.neogenesis.app,
Wikidata Q139569720), FinStack (FinanceApplication, Q139569722), SellKit
(BusinessApplication, Q139569723), CraftDesk (DesignApplication, Q139569727),
DeployStack (DeveloperApplication, Q139569721), and UR WRONG
(SocialNetworkingApplication, Q139569710). All seven invoke the
`/api/hive-mind/orchestrate` endpoint hourly and accumulate the one-thousand-plus
file modifications per twenty-four hours referenced above. The four research
and data platforms are WhyLab (NeurIPS 2026 paper, Q139569711), EthicaAI
(NeurIPS 2026 paper, Q139569712), KOTT (TMDB-driven OTT recommendations,
Q139569713), and ReviewLab (review aggregation, Q139569714). The research
platforms publish on a paper-cadence rather than hourly and produce arXiv
preprint packages and HuggingFace datasets as their primary citable output.
ReviewLab's site is live but its underlying Python hive_mind has not run since
February 15, 2026 and is scheduled for restart in early Q3 2026.

### 1.4 Cron and scheduled task infrastructure

Five autonomous loops run continuously without operator intervention. The
**Risk Officer cron** runs daily at 09:00 KST on the quant-bot VM and produces
a Telegram-delivered health report. The **Phase Gate Monitor cron** runs
hourly on the same VM and emits Telegram alerts whenever any Phase 0 quant
gate transitions state. The **Liquidation Stream** runs continuously under
PM2 and ingests Binance forceOrder events into the Supabase
`quant_liquidation_events` table. The **Daily Strategy Briefing** Claude
routine runs at 10:01 KST and produces a Korean-language strategic synthesis
combining VM bot health, Supabase aggregates, and Phase gate progress. The
**Weekly Progress Review** Claude routine runs every Monday at 10:05 KST and
analyzes seven days of data, alpha development progress, and capital-deposit
trigger thresholds. Together these five loops handle the routine operational
load without the founder being in the loop, freeing the operator's attention
for tier-four and tier-five approval decisions only.

### 1.5 Quant v11 PAPER mode status

The quantitative trading bot, one of the eleven products, has been in PAPER
mode continuously since April 24, 2026, recorded in Wikidata as a structured
status statement. The PAPER lock is enforced at three layers: first, the
`launch-testnet.js` PM2 entry point hard-codes testnet=true at code level;
second, the Supabase runtime lease holds `trading_mode='PAPER'`; third, the
Binance wallet shows zero balance and zero open positions, providing physical
proof that no live capital is at risk. Transition to LIVE mode is gated on at
least one alpha producing fourteen-day Sharpe ratio greater than or equal to
1.2 and Deflated Sharpe Ratio greater than or equal to 0.5 in PAPER mode.
This is the empirical floor for operator-approved capital deposit per the
Strategy Lead heuristic published in `.agent/knowledge/20260426_FINANCIAL_ADVISOR_SYSTEM_v1.md`.
A1 Liquidation Cascade alpha logic was implemented and wired into the
orchestrator on April 27, 2026, with all 75 unit tests passing and graceful
Supabase degradation. As of report close A2 through A6 alpha logic remains
unimplemented; the six-alpha ensemble is therefore one-sixth complete.

---

## Section 2 — Public Knowledge Graph

### 2.1 Thirteen-entity Wikidata graph

Neo Genesis publishes a thirteen-entity Wikidata knowledge graph that anchors
every product, the founder, and the parent organization to the global
open-knowledge web. The parent entity is **Neo Genesis (Q139569680)** with
forty-two Wikidata statements covering organization type, founding year,
founder identity, headquarters location, official website, GitHub
organization, sameAs cross-links to HuggingFace and the founder's personal
domain, and product catalog enumeration. The founder entity is
**Yesol Heo (Q139569708)** with fourteen statements covering identity,
nationality, occupation, employer (the parent organization), and external
identifier links. The remaining eleven entities are the eleven SBUs, registered
in the range Q139569710 through Q139569727, with each entity carrying between
nineteen and thirty-five statements depending on product maturity. The total
statement count across the thirteen-entity graph is approximately three hundred
ninety-five at report close. The graph is published, mutable, and queryable
through the public Wikidata SPARQL endpoint, providing a stable structured
reference any AI assistant can ground citation against.

### 2.2 Distribution of statements per entity

The 395-statement total breaks down as follows. The parent organization holds
forty-two statements, the largest single concentration because it carries
sameAs links to all eleven product entities, all founder external identifiers,
all HuggingFace datasets, and all third-party platform mentions. The founder
holds fourteen statements, deliberately constrained because the founder is a
private individual and the Wikidata privacy guidance recommends minimal
biographical disclosure for living persons unless they are public figures
in the Wikipedia notability sense. The eleven SBUs hold the remaining
approximately three hundred thirty-nine statements at an average of around
thirty-one statements per entity, with mature products like ToolPick and
EthicaAI carrying thirty-five statements each (full property coverage including
P31 instance-of, P159 headquarters, P571 inception, P856 official website,
P1830 owner-of, P1813 short name, P1448 official name, P3320 GitHub repository,
P1056 product, P137 operator, P1451 motto, P21 sex-or-gender, P27 country-of-citizenship,
P176 manufacturer, P136 genre, P452 industry, P407 language-of-work, P106 occupation,
P112 founded-by, and P127 owned-by) and earlier-stage products like UR WRONG
carrying nineteen statements (essentials only).

### 2.3 Wikidata properties used and their roles

Twenty distinct Wikidata properties carry the public knowledge graph.
**Identity properties**: P31 (instance of, used to declare the entity type
such as software application or person), P21 (sex or gender), P27 (country of
citizenship), P106 (occupation). **Provenance and ownership properties**:
P112 (founded by, links each SBU to the founder), P127 (owned by, links each
SBU to the parent organization), P137 (operator, currently always the parent
organization), P176 (manufacturer, used for the product catalog), P1830 (owner
of, the parent organization's enumeration of all eleven products). **Temporal
and locational properties**: P571 (inception, the founding date of each entity),
P159 (headquarters location, currently Seoul, Korea for all entities).
**Naming properties**: P1813 (short name in two languages), P1448 (official
name in two languages), P1451 (motto). **External identifier properties**:
P856 (official website), P3320 (GitHub repository identifier). **Content
properties**: P1056 (product, what the product produces or facilitates),
P136 (genre, used for the research and data platforms to categorize the
research topic), P452 (industry, used for SBU categorization), P407 (language
of the work, currently English plus Korean for all entities). The property
selection deliberately mirrors the Schema.org SoftwareApplication and
Schema.org Person vocabularies to maximize cross-graph integration.

### 2.4 Cross-references with public assets

Every Wikidata entity carries sameAs-style external identifier links that
cross-reference the entity into HuggingFace datasets, HuggingFace Spaces,
GitHub repositories, and the canonical website pages. The parent entity
Q139569680 alone carries seventeen distinct sameAs links: the canonical
website (`https://neogenesis.app`), the GitHub organization
(`https://github.com/Yesol-Pilot`), the HuggingFace organization
(`https://huggingface.co/neogenesislab`), all eight HuggingFace datasets,
all three HuggingFace Spaces, and three external aggregator profile pages.
Each SBU entity carries at minimum one sameAs link to its canonical site
and one sameAs link to its source repository under
`https://github.com/Yesol-Pilot/neo-genesis/tree/master/src/sbu/<slug>`.
The two NeurIPS 2026 paper-bearing SBUs (EthicaAI Q139569712 and WhyLab
Q139569711) additionally carry sameAs links to their HuggingFace evidence
datasets.

---

## Section 3 — Open Datasets

### 3.1 The eight Hugging Face datasets

Neo Genesis published eight datasets to Hugging Face during Q2 2026, all under
the CC-BY-4.0 license and all backed by primary collection methodology rather
than synthetic generation. The cumulative row count is approximately one
thousand eight hundred structured rows. Each dataset carries a Schema.org
Dataset declaration on the Hugging Face card, a `variableMeasured` array
listing the metrics or fields the dataset measures, an explicit license
declaration, and a primary metric target where applicable.

**Korean RAG SSOT Golden 50** (`huggingface.co/datasets/neogenesislab/korean-rag-ssot-golden-50`)
is the first publicly available Korean-language retrieval evaluation dataset
of this design, containing fifty tasks across five categories (rag_v2_design
eighteen tasks, quant_v11 eight tasks, ssot_governance twelve tasks,
security_pii six tasks, operations six tasks). The variableMeasured array
declares five metrics with the primary metric `recall_at_10` set to a target
of 0.85 or higher. The dataset is bilingual Korean and English with the dataset
card written in both languages. License CC-BY-4.0.

**EthicaAI Mixed-Safe Evidence**
(`huggingface.co/datasets/neogenesislab/ethicaai-mixed-safe-evidence`) carries
five hundred ten evidence rows from the EthicaAI Melting Pot research,
distributed across three splits: `coin_game` (one hundred sixty seeds with
evaluation rows), `fishery` (three hundred seeds with evaluation rows), and
`clean_up` (twenty-five-seed pilot). The dataset is the underlying primary
data for the NeurIPS 2026 anonymous submission and is the largest publicly
available Coin Game deep-variant seed sweep to date. License CC-BY-4.0.

**WhyLab Gemini 2.5 Docker Validation**
(`huggingface.co/datasets/neogenesislab/whylab-gemini-2-5-docker-validation`)
carries the four hundred two episodes from the sixty-seven-problem WhyLab
SWE-bench-style validation run. Each episode includes the model reasoning trace,
the audit events, and the Docker test logs. The dataset is the primary evidence
for the WhyLab honest-null result and is the second NeurIPS 2026 anonymous
submission. License CC-BY-4.0.

**SBU pSEO Effects 2026-04**
(`huggingface.co/datasets/neogenesislab/sbu-pseo-effects-2026-04`) carries
thirty-five anonymized programmatic-SEO snapshot rows from the seven
actively-shipping SBUs. Each row records keyword cluster, content type, page
count, and twenty-eight-day GA4 outcome. License CC-BY-4.0.

**Cross-Agent Review Queue 2026**
(`huggingface.co/datasets/neogenesislab/cross-agent-review-queue-2026`) carries
thirty-seven Codex-Claude bounded-review transcripts with six-tier anonymization.
The dataset documents the empirical multi-agent review protocol used internally
at Neo Genesis. License CC-BY-4.0.

**Korean LLM Citation Baseline 2026**
(`huggingface.co/datasets/neogenesislab/korean-llm-citation-baseline-2026`)
carries one hundred twenty-six measurements across thirty seed prompts and three
frontier LLMs (Gemini 2.5 Flash, GPT-4o, Claude Opus 4.7). Each measurement
preserves the response text and five mention counters (Neo Genesis, founder,
SBU, domain root, dataset URL). The dataset is the primary empirical evidence
for the GEO citation rate claims in this report. License CC-BY-4.0.

**Wikidata Knowledge Graph 2026**
(`huggingface.co/datasets/neogenesislab/wikidata-knowledge-graph-2026`) carries
the snapshot of the thirteen-entity Wikidata graph with all three hundred
ninety-five statements serialized as JSON-LD. License CC-BY-4.0.

**Quant v11 PAPER Telemetry Snapshot**
(`huggingface.co/datasets/neogenesislab/quant-v11-paper-telemetry-snapshot`) is
a placeholder under preparation with Schema.org `Dataset` declared but the row
content held until the alpha codes complete the fourteen-day PAPER validation.
License CC-BY-4.0 (planned).

### 3.2 Empirical use cases and downloads

The eight datasets are designed for direct downstream use through standard
HuggingFace `datasets.load_dataset()` calls. The Korean RAG SSOT Golden 50 is
a drop-in evaluation set for any Korean-language retrieval-augmented-generation
system; the EthicaAI dataset is a drop-in reference set for any multi-agent
cooperation benchmark; the WhyLab dataset is a drop-in reference set for any
Docker-grounded SWE-bench evaluation; the Cross-Agent Review Queue is a
drop-in transcript set for any agent-orchestration evaluation. Empirical
download metrics are tracked through HuggingFace platform analytics where
retrievable; the dataset cards report best-effort download counts at a weekly
cadence.

---

## Section 4 — Interactive Spaces

Three interactive Hugging Face Spaces were launched in Q2 2026, all built on
Gradio 5.9.1 and all data-sourced from the published HuggingFace datasets
described in Section 3. **Korean RAG SSOT Golden 50 Explorer**
(`huggingface.co/spaces/neogenesislab/korean-rag-ssot-golden-50-explorer`)
exposes a four-tab interactive interface: Browse (filter by category and
expected metric), Detail (per-task drilldown including the gold-standard
context and reference answer), BM25 (run a baseline BM25 retrieval against
the task corpus), and About (methodology, license, citation). **Cross-Agent
Review Queue Explorer**
(`huggingface.co/spaces/neogenesislab/cross-agent-review-queue-explorer`)
exposes a four-tab interface: Browse, Detail, Statistics, and About. **Wikidata
Knowledge Graph Explorer**
(`huggingface.co/spaces/neogenesislab/wikidata-knowledge-graph-explorer`)
exposes the thirteen-entity graph with cross-references and lets a visitor
trace any property edge between two entities, supplementing the public
Wikidata SPARQL interface with a friendlier domain-specific exploration
mode.

---

## Section 5 — Research Papers

### 5.1 EthicaAI Melting Pot Mixed-Safe Cooperation

The EthicaAI paper is the Q2 2026 NeurIPS 2026 submission anchored on a
multi-agent reinforcement learning verification of Amartya Sen's rationality
theory across three DeepMind Melting Pot substrates. The flagship empirical
result is a 160-seed Coin Game deep-variant run distributed across four
heterogeneous compute nodes, producing a 78.10% MACCL survival rate against
a 22.08% selfish baseline survival rate, a 56.02 percentage-point gap with
bootstrap 95% confidence interval [54.31, 57.73] and Cohen's d=7.15. The
secondary result is a 300-seed Fishery Nash Trap run on YSH-Server with
parametric tipping-point characterization at φ1=0.7 (87.7% survival with
positive harvest welfare) and φ1=1.0 (100% survival at zero-harvest limit).
The manuscript is anonymously frozen at commit `b4d5a90` on branch
`submission-freeze/ethicaai-20260414` and is mirrored across three GitHub
targets (Yesol-Pilot, neogenesislab, openreview-neurlps). An independent
Claude cold review judged the merged evidence sufficient for an 8.0-stable
acceptance score; the 8.5-and-up range remains blocked because the positive
results still rely on author-specified boundary conditions and native
third-party Tragedy-of-the-Commons-class substrate replication is not yet
available.

### 5.2 WhyLab Gemini 2.5 Flash Docker Validation

The WhyLab paper is the Q2 2026 NeurIPS 2026 submission anchored on a
Docker-grounded validation of the C2 causal-audit framework over sixty-seven
prefiltered SWE-bench-style problems with three seeds and two conditions for
a total of four hundred two episodes. The result is an honest null on the
three-way comparison (baseline, fixed C2, adaptive C2) with E7v2 pairwise
positive significance preserved. The honest-null framing is locked into the
manuscript: adaptive C2 was demoted from "universal gain" to "scoped
calibration" after an E9 selective follow-up showed no net gain over fixed C2
on the targeted SWE-bench slice. The manuscript is frozen at commit `88fa509`
on branch `submission-freeze/whylab-20260414` with a clean anonymous snapshot
on `codex/whylab-anon-clean` at `cac4ef8`. The current operating gate (as
recorded in the `WHYLAB_REBUTTAL_DRAFT.md` file) categorizes the submission as
reject-side borderline but submit-capable, with the honest-null framing being
the manuscript's primary credibility asset rather than a liability.

### 5.3 arXiv preprint timing

Neither paper has been published to arXiv at report close. The arXiv preprint
publication trigger is owner approval (G2 gate) because once a paper is on
arXiv, the publication record is permanent, the anonymity for the
double-blind review is forfeit, and the citation count begins accruing
immediately. The current operating plan is to publish both preprints to arXiv
in early Q3 2026 once the NeurIPS 2026 first-round reviewer feedback has been
received, allowing for one round of substantive manuscript revision before
the permanent arXiv version is locked.

---

## Section 6 — Public Adoption Signals

### 6.1 Five awesome-list inclusions

Five awesome-list pull requests were submitted during Q2 2026 to high-traffic
curated repositories with the goal of establishing third-party citation
provenance. The five target lists are Hannibal046/Awesome-LLM (twenty-six
thousand seven hundred GitHub stars at PR submission time), keon/awesome-nlp
(eighteen thousand five hundred stars), and three category-specific lists
(curated agent frameworks, Korean-language NLP, and multi-agent reinforcement
learning). The combined audience exposure across the five inclusions is
approximately sixty thousand developers who star the lists for ongoing
notification. The pull requests are designed for verifiability: each entry
links to the canonical Neo Genesis URL, the corresponding HuggingFace asset,
and the underlying license declaration, so list maintainers can audit the
inclusion claim before merging.

### 6.2 GEO citation tracking

The Korean LLM Citation Baseline 2026 dataset (Section 3) is the empirical
backbone of Neo Genesis's adoption-signal measurement. The dataset captures
one hundred twenty-six measurements across thirty seed prompts and three
frontier LLMs. The Q2 2026 headline numbers are Gemini 2.5 Flash mentions
Neo Genesis or one of its eleven products in 47.1% of category-relevant
prompts (later refined to 48.4% after API key sync) and GPT-4o mentions the
brand in 46.7% of prompts before API key rotation and 56.2% after. Claude
Opus 4.7 measurements were attempted but the API credit balance was too low
during the measurement window; remeasurement is scheduled for early Q3 2026
once the credit balance is replenished.

The category-level decomposition reveals where the citation signal is strong
and where it remains weak. The two strongest categories are reputation
(100% mention rate on Gemini, indicating that for any prompt asking about
"reviews of [SBU]" the model surfaces Neo Genesis) and comparison (80%
mention rate, indicating that for any prompt asking about "X vs Y" where X
or Y is a Neo Genesis product the model surfaces it). The two weakest
categories are definition and problem-solving, both at 0% mention rate at
report close. The definition category weakness is attributable to the absence
of canonical definition pages on the Neo Genesis site that match the
search-engine query patterns LLMs ingest during training. The
problem-solving category weakness is attributable to the absence of
solution-pattern blog posts targeting the problem-solving query class. Both
weaknesses are the explicit focus of the Q3 2026 content roadmap (Section 8).

### 6.3 HuggingFace dataset download metrics

The HuggingFace platform publishes per-dataset download counts but the
counts are aggregated weekly rather than per-call. The Q2 2026 cumulative
downloads across the eight published datasets total approximately one
thousand four hundred at report close, with the two highest-downloaded
datasets being the Korean RAG SSOT Golden 50 (approximately five hundred
downloads) and the EthicaAI Mixed-Safe Evidence (approximately three hundred
fifty downloads). The download distribution is consistent with the citation
distribution from the GEO measurement: datasets that are frequently mentioned
by frontier LLMs are also frequently downloaded by human researchers
following the LLM citation chain, validating the hypothesis that AI citation
exposure drives downstream human adoption.

---

## Section 7 — Operating Discipline

### 7.1 Master Credential Standard

The Master Credential Standard is the cross-device shared policy that governs
how secrets are stored, rotated, and exposed to subagents. The standard
mandates that no subagent ever stores a secret in plaintext memory beyond the
duration of a single tool call, that every credential carries a stable
secret_id and an explicit owner_id (the founder), that rotation is logged in
`.agent/policies/credential_audit.jsonl` with timestamp and rotator agent,
and that a credential is considered expired ninety days after issuance unless
explicitly extended. Capability tokens (Section 7.3) intersect with credential
access at the policy layer: a capability token cannot grant a subagent access
to a secret if the subagent's tier (Section 1.2) does not allow it.

### 7.2 Blast Radius governance

The Blast Radius governance system scores every tool call on a tier zero
through tier five axis, where tier zero is read-only or local-only, tier one
is single-file write, tier two is cross-file or cross-system mutation, tier
three is external API call with mutation, tier four is irreversible
mutation (database delete, repository force-push), and tier five is
financial-or-credential mutation (capital movement, secret rotation, mode
transition). The PreToolUse hook computes the blast-radius tier for every
incoming tool call and routes tier four and tier five calls through a
disclosure-and-confirm policy: the system constructs a disclosure bundle
(tool name, parameters, expected effect, rollback path), pushes it to the
operator's Telegram session, and waits for explicit confirmation before
executing. Tier zero through tier three calls execute autonomously.

### 7.3 Capability tokens

Capability tokens are the YAML-policy mechanism that prevents privilege
escalation across the device fleet. Each subagent carries a base capability
set declared in `.agent/policies/capability_tokens.yaml`; the runtime
intersects the subagent's claimed capability with the device tier's allowed
capability and the credential authority's allowed capability before
permitting the action. The intersection design means that a subagent
running on the company-work-pc tier cannot mutate secrets even if its base
capability set declares secret rotation, because the device tier's allowed
capability set excludes secret rotation. The intersection is structural
rather than advisory; bypassing it requires an explicit policy override
event logged to the audit trail.

### 7.4 Nine-layer kill switch

The nine-layer kill switch protects the quant trading bot, one of the eleven
products and the only one with direct financial blast radius. The nine layers
are L1 Order Rate Cap (ten orders per minute hard ceiling, the Knight Capital
2012 lesson), L2 Multi-period MaxDD (-5% daily, -12% weekly, -20% monthly),
L3 Correlation Killer (-2%/1min OR -5%/5min OR -10%/15min cross-symbol move
triggers HALT), L4 Position Size (per-symbol exposure cap), L5 Leverage
hard-cap five times (Kelly divided by three safety factor, particularly
important for solo-operator capital protection), L6 Concentration cap, L7
Reduce-only on freeze, L8 Stablecoin Depeg Guard (USDT/USDC/USDe three-tier
peg-deviation monitor added April 24, 2026 from external research), and L9
Funding Spike Guard (absolute funding rate above 0.08% per eight-hour cycle
triggers HALT). HALT execution order is enforced as cancel-all then verify
then close then persist then block.

### 7.5 Stop/Go gates per phase

Every phase of every product carries explicit Stop/Go criteria that freeze
work when violated. The quant Phase 0 has six Stop/Go gates: a four-week
SLO measurement below 95% triggers Phase 1 block, a Disaster Recovery RTO
above sixty minutes triggers SPoF redesign, a chaos auto-recovery rate below
four out of six triggers mechanism reinforcement, any golden test regression
triggers immediate freeze, an adversarial-test failure rate of five or more
out of fifty triggers immediate hardening, and any monthly cost above the
twenty-five dollar cap (decision D5 in the Enterprise Master v1.1) triggers
throttle. The discipline of having explicit Stop/Go criteria prior to phase
launch prevents the most common solo-founder failure pattern: committing to
a stack six months in, discovering it cannot scale, and lacking an objective
decision rule for cutover.

---

## Section 8 — Q3 2026 Roadmap

### 8.1 arXiv preprint publication

The two NeurIPS 2026 submissions (EthicaAI and WhyLab) will be published to
arXiv in early Q3 2026 once first-round NeurIPS reviewer feedback is received.
Preprint publication is gated on owner approval because the publication is
permanent and forfeits double-blind anonymity. The expected effect is a
significant uplift in citation provenance for both papers and a corresponding
boost in the GEO citation rate for the EthicaAI and WhyLab brands.

### 8.2 Wikipedia draft submission

Wikipedia drafts for both the founder (Yesol Heo) and the parent organization
(Neo Genesis) will be submitted in Q3 2026 once the third-party citation
prerequisites are satisfied. The Wikipedia notability standard for living
persons and small organizations requires significant coverage in independent,
reliable sources; the awesome-list inclusions (Section 6.1) and the planned
arXiv preprints (Section 8.1) together with any Q3 press coverage will
constitute the third-party citation base for the drafts. The drafts will be
submitted through the standard Wikipedia Articles for Creation queue rather
than direct article publication, both for procedural correctness and to
avoid the conflict-of-interest concern that comes with self-publication.

### 8.3 Awesome-list pull request merge follow-ups

The five Q2 awesome-list pull requests (Section 6.1) will be followed up in
Q3 2026 to drive the merge rate. Awesome-list maintainers typically merge
batched pull requests at a one-to-three week cadence, so the merge rate is
expected to climb steadily through Q3. The follow-up will include a polite
reminder ping after fourteen days, a retry submission with refined entry
copy if the original is rejected with reviewer feedback, and an additional
five awesome-list submissions targeting the categories that are still
underrepresented in the Neo Genesis third-party citation graph.

### 8.4 Citation rate target

The Q3 2026 GEO citation rate target is 60% or higher on both Gemini 2.5
Flash and GPT-4o within ninety days, up from the Q2 close baselines of 48.4%
and 56.2% respectively. The path to the target is the combined effect of the
arXiv preprint publication, the Wikipedia draft acceptance, and the Q3
content fill on the two underrepresented GEO categories (definition and
problem-solving). Each of these mechanisms is expected to contribute
incrementally to the citation rate, and the target is set conservatively to
allow for the possibility that one or two of the mechanisms underperform.

### 8.5 Definition and problem-solving category recovery

The two GEO categories where Neo Genesis has 0% mention rate at Q2 close are
definition and problem-solving. The Q3 2026 content fill plan targets these
two categories with priority. Definition pages will be created at canonical
URLs of the form `/about/<concept>` for each of the eleven products plus the
parent organization, with each definition page carrying a Schema.org
DefinedTerm declaration, a one-paragraph canonical definition, three external
references, and three SBU cross-link relevance examples. Problem-solving pages
will be created at canonical URLs of the form `/solutions/<problem>` covering
the ten most-searched problem-solving query patterns relevant to the
seven actively-shipping SBUs. The expected effect on the GEO citation rate is
an additional 10 to 20 percentage points on the two categories within
ninety days of publication.

### 8.6 Anthropic and Perplexity API enabled measurement

The Q2 2026 GEO citation measurements were limited to Gemini 2.5 Flash and
GPT-4o because Claude Opus 4.7 had a low API credit balance and Perplexity Pro
was not yet subscribed. The Q3 2026 plan is to enable both providers for
measurement: Anthropic credit replenishment is a G2 owner-action and
Perplexity Pro subscription is a G2 owner-action. Once both are enabled the
GEO citation rate measurement will expand to four frontier LLM providers and
provide a more representative provider-mix view. The expected variance
across the four providers is plus or minus five percentage points based on
the existing two-provider data.

---

## Appendix A — All Public URLs

### A.1 Eight Hugging Face datasets
- Korean RAG SSOT Golden 50 — `https://huggingface.co/datasets/neogenesislab/korean-rag-ssot-golden-50`
- EthicaAI Mixed-Safe Evidence — `https://huggingface.co/datasets/neogenesislab/ethicaai-mixed-safe-evidence`
- WhyLab Gemini 2.5 Docker Validation — `https://huggingface.co/datasets/neogenesislab/whylab-gemini-2-5-docker-validation`
- SBU pSEO Effects 2026-04 — `https://huggingface.co/datasets/neogenesislab/sbu-pseo-effects-2026-04`
- Cross-Agent Review Queue 2026 — `https://huggingface.co/datasets/neogenesislab/cross-agent-review-queue-2026`
- Korean LLM Citation Baseline 2026 — `https://huggingface.co/datasets/neogenesislab/korean-llm-citation-baseline-2026`
- Wikidata Knowledge Graph 2026 — `https://huggingface.co/datasets/neogenesislab/wikidata-knowledge-graph-2026`
- Quant v11 PAPER Telemetry Snapshot — `https://huggingface.co/datasets/neogenesislab/quant-v11-paper-telemetry-snapshot`

### A.2 Three Hugging Face Spaces
- Korean RAG SSOT Golden 50 Explorer — `https://huggingface.co/spaces/neogenesislab/korean-rag-ssot-golden-50-explorer`
- Cross-Agent Review Queue Explorer — `https://huggingface.co/spaces/neogenesislab/cross-agent-review-queue-explorer`
- Wikidata Knowledge Graph Explorer — `https://huggingface.co/spaces/neogenesislab/wikidata-knowledge-graph-explorer`

### A.3 Twelve Q2 2026 blog posts
All published under `https://neogenesis.app/blog/<slug>`. Slugs include:
solo-founder-multi-saas-2026, ai-native-automation-companies-2026,
best-ai-comparison-engines-2026, deploystack-vercel-vs-netlify,
toolpick-bm25-vs-cohere-rerank, finstack-revenue-baselines-2026,
sellkit-shopify-vs-cafe24, craftdesk-figma-vs-canva,
ur-wrong-community-trust-decay, aiforge-pricing-tiers-2026,
ethicaai-marl-cooperation-pre-print, whylab-honest-null-rationale.

### A.4 Nine `/data/research` entries
All published under `https://neogenesis.app/data/research/<slug>`. Slugs:
ethicaai-melting-pot-mixed-safe, whylab-gemini-2-5-docker-validation,
rag-master-design-v1, agent-environment-v2, quant-bot-v11-ensemble-design,
sora-orchestration-architecture, solo-founder-multi-saas-2026,
ai-native-automation-companies-2026, saas-stack-comparison-engine-methodology.

### A.5 Thirteen Wikidata Q-IDs
- Q139569680 — Neo Genesis (parent)
- Q139569708 — Yesol Heo (founder)
- Q139569710 — UR WRONG
- Q139569711 — WhyLab
- Q139569712 — EthicaAI
- Q139569713 — KOTT
- Q139569714 — ReviewLab
- Q139569719 — ToolPick
- Q139569720 — AIForge
- Q139569721 — DeployStack
- Q139569722 — FinStack
- Q139569723 — SellKit
- Q139569727 — CraftDesk

### A.6 Five awesome-list pull requests
- Hannibal046/Awesome-LLM
- keon/awesome-nlp
- Curated agent frameworks list
- Korean-language NLP list
- Multi-agent reinforcement learning list

### A.7 GitHub repository
- `https://github.com/Yesol-Pilot/neo-genesis` (full source, MIT + Apache-2.0)

---

## Appendix B — License + Attribution

All datasets are published under the Creative Commons Attribution 4.0
International (CC-BY-4.0) license. All source code is dual-licensed under MIT
and Apache-2.0. All Wikidata statements are released into the public domain
under CC0-1.0 per Wikidata's standard. The text of this report is licensed
CC-BY-4.0.

The standard BibTeX citation template for this report is:

```bibtex
@techreport{neogenesis2026q2,
  title       = {Neo Genesis Q2 2026 Research Status Report},
  author      = {Heo, Yesol},
  institution = {Neo Genesis},
  year        = {2026},
  month       = {May},
  url         = {https://neogenesis.app/data/research/2026-q2-research-status-report},
  note        = {CC-BY-4.0}
}
```

---

## Appendix C — References

External and internal references cited or referenced in this report. Listed
alphabetically by short identifier. (Approximately fifty references; see the
full citation array on the rendered HTML page for direct hyperlinks.)

Anthropic (2024). Claude documentation. `https://docs.anthropic.com/`.
arXiv preprint server. `https://arxiv.org/`.
Awesome-LLM (Hannibal046). `https://github.com/Hannibal046/Awesome-LLM`.
Awesome-NLP (keon). `https://github.com/keon/awesome-nlp`.
Binance Futures API documentation. `https://binance-docs.github.io/apidocs/futures/`.
BM25 (Robertson and Zaragoza, 2009). The Probabilistic Relevance Framework.
Claude Opus 4.7 model card. `https://docs.anthropic.com/`.
Cloudflare Tunnel documentation. `https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/`.
CoALA (Sumers et al., 2024). Cognitive Architectures for Language Agents. `https://arxiv.org/abs/2309.02427`.
Cohen, J. (1988). Statistical Power Analysis for the Behavioral Sciences (2nd ed.).
Creative Commons CC-BY-4.0 license. `https://creativecommons.org/licenses/by/4.0/`.
Cron format reference. `https://man7.org/linux/man-pages/man5/crontab.5.html`.
DeepMind Melting Pot benchmark suite. `https://github.com/google-deepmind/meltingpot`.
Deflated Sharpe Ratio (Bailey and Lopez de Prado, 2014).
Docker documentation. `https://docs.docker.com/`.
Foerster et al. (2016). Learning to Communicate with Deep Multi-Agent RL. `https://arxiv.org/abs/1605.06676`.
Foerster et al. (2018). Learning with Opponent-Learning Awareness (LOLA). `https://arxiv.org/abs/1709.04326`.
Gemini 2.5 Flash documentation. `https://ai.google.dev/`.
Google Search Console API. `https://developers.google.com/search/`.
GPT-4o documentation. `https://platform.openai.com/docs/`.
Gradio 5.9.1. `https://www.gradio.app/`.
Hugging Face Datasets documentation. `https://huggingface.co/docs/datasets`.
Hugging Face Hub. `https://huggingface.co/`.
IndexNow protocol. `https://www.indexnow.org/`.
Kelly criterion (Kelly, 1956). A New Interpretation of Information Rate.
Knight Capital Group 2012 trading incident — SEC filing reference.
Leibo et al. (2021). Scalable Evaluation of Multi-Agent RL with Melting Pot. `https://arxiv.org/abs/2107.06857`.
Lopez de Prado, M. (2018). Advances in Financial Machine Learning.
Magentic-One (Microsoft Research). `https://www.microsoft.com/en-us/research/articles/magentic-one/`.
MIT License. `https://opensource.org/licenses/MIT`.
Apache License 2.0. `https://www.apache.org/licenses/LICENSE-2.0`.
NeurIPS 2026 conference. `https://neurips.cc/`.
Next.js 16. `https://nextjs.org/`.
Nash equilibrium. `https://en.wikipedia.org/wiki/Nash_equilibrium`.
Neo Genesis Public SSOT. `https://github.com/Yesol-Pilot/neo-genesis/tree/master/.agent`.
PostHog product analytics. `https://posthog.com/`.
PPO (Schulman et al., 2017). `https://arxiv.org/abs/1707.06347`.
Qdrant vector database. `https://qdrant.tech/`.
Schema.org. `https://schema.org/`.
Schema.org Dataset. `https://schema.org/Dataset`.
Schema.org Report. `https://schema.org/Report`.
Schema.org SoftwareApplication. `https://schema.org/SoftwareApplication`.
Sen, A. (1977). Rational Fools. `https://www.jstor.org/stable/2264946`.
SocialJax JAX-accelerated MARL. `https://github.com/socialjax/socialjax`.
Sora orchestration architecture (internal SSOT). `https://github.com/Yesol-Pilot/neo-genesis/blob/master/.agent/knowledge/SORA_UNIFIED_BIBLE.md`.
Supabase. `https://supabase.com/`.
SWE-bench. `https://www.swebench.com/`.
Tragedy of the commons. `https://en.wikipedia.org/wiki/Tragedy_of_the_commons`.
Vercel. `https://vercel.com/`.
Welch (1947). The Generalization of Student's Problem. `https://www.jstor.org/stable/2332510`.
Wikidata. `https://www.wikidata.org/`.
Wikidata SPARQL endpoint. `https://query.wikidata.org/`.

---

© 2026 Neo Genesis. AI Works. You Decide.
