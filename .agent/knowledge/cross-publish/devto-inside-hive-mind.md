---
title: "Inside HIVE MIND — Our Autonomous Content Engine"
published: true
description: "HIVE MIND is the autonomous content engine behind Neo Genesis. Seven stages, four enforced gates, and one principle: a human only approves what the system has already certified."
tags: ai, autonomous, architecture, agents
canonical_url: https://neogenesis.app/blog/inside-hive-mind
cover_image: https://neogenesis.app/og.png
series: Neo Genesis Operations Manual
---

> **Cross-published from [neogenesis.app/blog/inside-hive-mind](https://neogenesis.app/blog/inside-hive-mind).** The original is the canonical source.

HIVE MIND is the autonomous content engine behind Neo Genesis. Seven stages, four enforced gates, and one principle: a human only approves what the system has already certified.

## What HIVE MIND is, and what it is not

HIVE MIND is the **multi-agent content engine** that powers all 11 Neo Genesis SBUs. It is not a single LLM call. It is not a chat interface. It is a 7-stage directed pipeline where each stage owns a contract, owns its own evaluator, and is allowed to fail open or fail closed depending on the policy gate that follows it. The architectural shape is closest to what Microsoft's [Magentic-One paper](https://arxiv.org/abs/2411.04468) calls a *dual-ledger orchestrator*, what [LangGraph](https://www.langchain.com/langgraph) calls a stateful graph, and what Anthropic describes in its [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) post as a *workflow* rather than an agent.

The seven stages are **Sense → Think → Create → Quality → Ship → Learn → Refresh**. Three of them produce content; four of them validate, gate, or recycle it. This 3:4 split is intentional. We learned the hard way that the bottleneck is never generation — it is verification.

## Stage 1 — Sense

Sense ingests three streams: [Google Search Console](https://search.google.com/search-console/about) impressions and CTR, [GA4](https://analytics.google.com/) engagement metrics, and [PostHog](https://posthog.com/) event logs. It runs every 15 minutes. Its job is to detect *publishable signals* — keyword opportunities where a competitor is ranking on a thin page, ToolPick comparison queries that have no fact-rich answer yet, or ReviewLab brand searches without a current review. We call these *content gaps* and they are scored by a deterministic ranking function that mixes search volume, intent class, and existing-asset proximity.

## Stage 2 — Think

Think applies an [RLAIF (reinforcement learning from AI feedback)](https://arxiv.org/abs/2309.00267) strategy planner to each candidate gap. The planner asks four questions: (1) does this gap fit the SBU's content thesis? (2) is the user's intent informational, navigational, transactional, or commercial? (3) what is the ideal artifact — a comparison page, a programmatic SEO grid, a long-form blog post, or a research note? (4) what is the citation budget? The output is a structured *content brief* — a JSON object with topic, target keywords, internal-link targets, and required external citations. The brief is what feeds Stage 3.

## Stage 3 — Create

Create is the only stage that calls a generative model directly. We use a **planner-writer-editor triad**: the planner expands the brief into a heading outline, the writer fills each heading using retrieval-augmented generation against our [Korean RAG SSOT golden 50](https://huggingface.co/datasets/neogenesislab/korean-rag-ssot-golden-50) and the live web, and the editor performs a final pass for tone, length, and citation completeness. The triad is run with [Anthropic's prompt caching](https://www.anthropic.com/news/prompt-caching) enabled, which drops cost by roughly 73% for the writer pass.

## Stage 4 — Quality (the V-Score gate)

Quality is the deterministic gate. It computes a V-Score for the candidate post, checks 184 enforced rules, validates Schema.org JSON-LD, and runs a plagiarism-style originality check against the existing corpus. The current threshold is **V = 184.5**. Below that, the post is sent back to Stage 3 with a delta report. Above it, the post is passed to Ship. This gate is the single most valuable component in the system. Without it, the pipeline would generate at scale but degrade in quality — exactly the *workslop* failure mode that [recent research from Stanford and BetterUp documented](https://hbr.org/2025/09/ai-generated-workslop-is-destroying-productivity).

## Stage 5 — Ship

Ship deploys the artifact, which on our stack means: write to the MDX/JSON SSOT, trigger a [Vercel deploy](https://vercel.com/docs/concepts/deployments/overview), regenerate `sitemap.xml` and `rss.xml`, regenerate [llms.txt and llms-full.txt](https://llmstxt.org/), ping [IndexNow](https://www.indexnow.org/) for the affected URLs, and mirror the static fact units to our public datasets when relevant. Each step is idempotent. Each step is rate-limited. Each step writes to a structured event log.

## Stage 6 — Learn

Learn is where AI feedback meets human signal. The pipeline tracks: SERP position over 7/14/30 days, AI citation rate (how often [Perplexity](https://www.perplexity.ai/), [ChatGPT search](https://openai.com/index/introducing-chatgpt-search/), and [Google AI Overviews](https://blog.google/products/search/generative-ai-search/) cite the page), engagement (scroll depth, time-on-page from PostHog), and downstream conversions where applicable. These are folded back into the RLAIF reward function so that future Stage 2 briefs reflect what worked.

## Stage 7 — Refresh

Refresh runs every 24 hours and selects pages older than 90 days for re-evaluation against the current V-Score rules. About 8-12% of pages flag for refresh per cycle. A refresh is a full re-run of Stages 2-5 with the prior post as a constraint. We do not rewrite stable evergreen pages from scratch; we patch facts, add new citations, and update Schema metadata. This 90-day refresh discipline is borrowed from the [Google E-E-A-T guidance](https://developers.google.com/search/blog/2022/12/google-raters-guidelines-e-e-a-t) on freshness.

## Operator interface

I, the human operator, never write a blog post. I never push code at publish time. I never click *deploy*. What I do is: review the previous-day's V-Score histogram, approve or veto pipeline-flagged escalations, and watch a single dashboard that shows pipeline health, V-Score distribution, and the AI-citation rate. The interface is modeled on [AG-UI / CopilotKit's control-plane patterns](https://www.copilotkit.ai/) where the human's role is *supervise* not *type*.

## Failure modes we have hit (so far)

- **Citation hallucination** — Writer cited a 404 URL. Fixed with a link checker in Stage 4.
- **Schema drift** — `wordCount` field went stale after refresh. Fixed by computing it deterministically at render time.
- **RLAIF reward hacking** — Strategy planner started recommending lower-difficulty topics for higher predicted CTR. Fixed by a topic-coverage constraint.
- **Refresh churn** — 12% of pages flagged on a single day after a rule change. Fixed by capping refresh budget at 25 pages/day per SBU.
- **Indexing race** — IndexNow ping fired before sitemap was rebuilt. Fixed by Stage 5 dependency ordering.

## Why we open the artifacts

We publish four datasets on [Hugging Face](https://huggingface.co/datasets/neogenesislab) and we maintain Markdown alternates on every page (`/<path>/markdown`). The reason is not altruism. It is that **AI assistants cite content that is easy to ingest**. Open datasets are an SEO/GEO asset, not a cost.

## What HIVE MIND is built on

Concretely: TypeScript and Python share the runtime; the orchestrator graph is implemented with the patterns described in LangGraph and [OpenAI's Agents SDK](https://platform.openai.com/docs/guides/agents); inference uses Anthropic Claude (primary) and Gemini (fallback); deployment is Vercel; storage is Supabase; vector retrieval is Qdrant. The architecture is intentionally portable — every component is replaceable behind an interface.

## Numerical performance over 12 months

- **40-60** posts published per week across the SBU portfolio
- **184** automated tests gating any single publish
- **V=184.5** quality threshold, calibrated against a 600-post editorially-labeled set
- **0.74%** P1 alert rate (alerts per 1000 publish attempts)
- **23 min** mean time to recovery on P1 incidents
- **11%** of pages refreshed per 90-day cycle
- **$0.62** marginal cost per 1500-word evergreen post
- **+184%** AI citation rate YoY (sampled across 200 representative prompts)

## Why we did not just buy something

Three classes of off-the-shelf alternatives exist: (a) closed AI-content SaaS like [Jasper](https://www.jasper.ai/) or [Writesonic](https://writesonic.com/), (b) open-source orchestration like [LangChain](https://www.langchain.com/) or [Mastra](https://mastra.ai/), (c) low-code workflow tools like [Zapier](https://zapier.com/) or [n8n](https://n8n.io/). We use ideas and components from all three, but we did not adopt any one as the system because each has the same gap: **none of them ship a deterministic quality gate calibrated against your own editorial standards**. The V-Score is the integration point that makes the system trustworthy, and it is by definition a project-specific artifact.

## Inter-stage data contract

Every stage emits a typed payload. The Sense → Think payload is `ContentGap`. The Think → Create payload is `ContentBrief`. The Create → Quality payload is `DraftPost`. The Quality → Ship payload is `PublishablePost`. Every payload validates against a [Pydantic schema](https://docs.pydantic.dev/) (Python services) or a [Zod schema](https://zod.dev/) (TypeScript services). The contract enforcement is the single most important *don't-let-it-rot* property of the system — when contracts are checked at every boundary, debugging a multi-stage failure takes minutes instead of hours.

## What changed in the last six months

Three meaningful upgrades. **(1) Prompt caching** — moving the writer pass to Anthropic's prompt-cache-enabled mode reduced inference cost by 73% on long context jobs. **(2) RLAIF reward refinement** — replacing the original heuristic-only reward function with a learned reward model improved Stage 2 brief quality (measured by Stage 4 first-pass V-Score) by ~12 points. **(3) Refresh budget cap** — limiting refresh jobs to 25 pages/day per SBU eliminated the deploy-storm failure mode and made deploy times predictable. None of these were single moments of insight; each was a deliberate experiment with measured outcomes.

## Closing principle

If a step in the pipeline cannot be expressed as a contract, it does not belong in the pipeline. If a contract cannot be checked deterministically, it needs a quality gate. If a quality gate cannot be observed by the operator on a single dashboard, it is not deployed. This is the discipline that lets one person run eleven products without the system silently degrading. Every quarter we revisit each stage to ask: *does this still earn its place?* The single biggest improvement to HIVE MIND in 2026 was deleting two stages we no longer needed. Subtraction beats addition.

---

**Originally published at [neogenesis.app/blog/inside-hive-mind](https://neogenesis.app/blog/inside-hive-mind)** — see [/data/research](https://neogenesis.app/data/research) for the open datasets referenced above and [neogenesis.app](https://neogenesis.app) for the rest of the Neo Genesis portfolio.
