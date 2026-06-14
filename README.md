# Neo Genesis

> **AI Works. You Decide.** — A 1-person AI-native conglomerate operating 11 live business units, 4 published research datasets, and a 13-entity Wikidata knowledge graph from a single autonomous AI system.

<!-- Provenance & Live Status -->
[![Production](https://img.shields.io/badge/status-production-success)](https://neogenesis.app)
[![Wikidata](https://img.shields.io/badge/Wikidata-Q139569680-blue?logo=wikidata)](https://www.wikidata.org/wiki/Q139569680)
[![Wikidata Statements](https://img.shields.io/badge/Wikidata_statements-395-blue)](https://www.wikidata.org/wiki/Q139569680)
[![License](https://img.shields.io/github/license/Yesol-Pilot/neo-genesis)](#license)
[![License Datasets](https://img.shields.io/badge/datasets-CC--BY--4.0-orange)](#license)

[![Hugging Face](https://img.shields.io/badge/%F0%9F%A4%97-neogenesislab-yellow)](https://huggingface.co/neogenesislab)
[![HF datasets](https://img.shields.io/badge/%F0%9F%A4%97_datasets-6-yellow)](https://huggingface.co/neogenesislab)
[![HF spaces](https://img.shields.io/badge/%F0%9F%A4%97_spaces-2-yellow)](https://huggingface.co/neogenesislab)
[![arXiv](https://img.shields.io/badge/arXiv-EthicaAI%20%2B%20WhyLab-b31b1b?logo=arxiv)](https://arxiv.org)
[![Schema.org](https://img.shields.io/badge/Schema.org-Organization-green)](https://schema.org/Organization)

[![GitHub stars](https://img.shields.io/github/stars/Yesol-Pilot/neo-genesis?style=social)](https://github.com/Yesol-Pilot/neo-genesis)
[![Last commit](https://img.shields.io/github/last-commit/Yesol-Pilot/neo-genesis)](https://github.com/Yesol-Pilot/neo-genesis/commits/master)
[![Languages](https://img.shields.io/badge/lang-EN_%2B_KO-purple)](https://neogenesis.app)

---

## What is Neo Genesis?

**Neo Genesis** ([Q139569680](https://www.wikidata.org/wiki/Q139569680)) is an AI-native operating system for a 1-person holding company. A single human operator — [Yesol Heo](https://www.wikidata.org/wiki/Q139569708) ([heoyesol.kr](https://heoyesol.kr)) — acts as Chairman of the holding entity, while every subsidiary is researched, built, deployed, monitored, and refreshed by an autonomous multi-agent AI system. The architectural thesis is straightforward: replace a 1,000-person conglomerate org chart with one operator and one autonomous loop, and let the loop scale through model and infrastructure improvements rather than headcount.

The core production layer is the **HIVE MIND** pipeline — a 7-stage autonomous content and product engine that handles market sensing, strategic planning, generation, quality gating, shipping, learning, and refresh. Behind it sits a fleet of 6 physical devices (Linux server, Windows workstations, Apple Silicon build node, mobile approval plane), a strict SSOT (`Single Source of Truth`) governance layer in [`.agent/`](./.agent), and a hard quality gate enforced by an internal metric called **V-Score** (target ≥ 184.5). The system runs 11 live business units (SBUs) under the [`neogenesis.app`](https://neogenesis.app) umbrella, each registered as a discrete entity in the [Wikidata knowledge graph](https://www.wikidata.org/wiki/Q139569680) so AI search engines, LLM crawlers, and academic citation systems can resolve them unambiguously.

Neo Genesis is built on the principle that **owner sovereignty** must outrank automation autonomy at every decision boundary. The autonomy gradient is encoded explicitly: G1 actions (low-risk content publishing, sitemap pings, blog generation) run under standing approval; G2 actions (capital movement, live trading, credential rotation, paid PR) require human gating. This makes the system reproducible, auditable, and safe enough for a single operator to control at scale.

---

## By the Numbers

| Metric | Value | Source |
|---|---|---|
| Live Business Units (SBUs) | **11** | [SBUS registry](./src/landing/src/lib/data/sbus.ts) |
| Wikidata entities registered | **13** | [Q139569680](https://www.wikidata.org/wiki/Q139569680) parent + 1 founder + 11 SBUs |
| Published datasets (Hugging Face) | **4** | [neogenesislab](https://huggingface.co/neogenesislab) |
| Pipeline stages (HIVE MIND) | **7** | Sense → Think → Create → Quality → Ship → Learn → Refresh |
| V-Score quality gate threshold | **184.5** | [V-Score blog post](https://neogenesis.app/blog/vscore-quality-gating) |
| Public blog posts | **10+** | [BLOG_POSTS](./src/landing/src/lib/data/sbus.ts) |
| Schema.org JSON-LD entities exposed | **24+** | Organization + WebSite + Person + 11 OfferCatalog + 4 Dataset + BlogPosting |
| AI bots explicitly allowed | **25** | [`robots.txt`](./src/landing/public/robots.txt) (GPTBot, ClaudeBot, PerplexityBot, GoogleExtended, etc.) |
| Connected fleet devices | **6** | desktop-sol01, desktop-yesol, ysh-server, mac-studio, s26-ultra, tab-s10-ultra |
| Founded | **2024** | [Q139569680 § P571](https://www.wikidata.org/wiki/Q139569680) |
| Headquarters | **Seoul, Korea** | [Q139569680 § P159](https://www.wikidata.org/wiki/Q139569680) |
| Primary language | **Korean (ko) + English (en)** | bilingual content + dataset cards |
| Headcount | **1** | autonomous AI executes; human approves |
| Master credential repository | **`Yesol-Pilot/neo-genesis`** | authoritative for `dpthf1537@gmail.com` identity |
| AI agent runtime SSOT | **`.agent/NEO_MASTER_RULES.md` v1.9** | governs Sora, Claude Code, Codex, Antigravity |
| Quant trading mode | **PAPER** | safety-locked; LIVE requires explicit owner gate |
| Dataset license | **CC-BY-4.0** | open replication encouraged |
| Code license | **MIT** | permissive reuse |

---

## 11 Business Units

Each SBU is a fully autonomous product line: own domain, own content engine, own analytics, own Wikidata entity. The 11-SBU portfolio covers consumer (debate, OTT recommendations), B2B SaaS comparison (8 verticals), and applied research (causal inference, AI ethics).

| # | Name | Wikidata | Domain | Category | Status |
|---|---|---|---|---|---|
| 1 | UR WRONG | [Q139569710](https://www.wikidata.org/wiki/Q139569710) | [ur-wrong.com](https://ur-wrong.com) | AI debate platform | LIVE |
| 2 | ToolPick | [Q139569711](https://www.wikidata.org/wiki/Q139569711) | [toolpick.dev](https://toolpick.dev) | B2B SaaS comparison | LIVE |
| 3 | ReviewLab | [Q139569712](https://www.wikidata.org/wiki/Q139569712) | [review.neogenesis.app](https://review.neogenesis.app) | AI product review magazine | LIVE |
| 4 | K-OTT | [Q139569715](https://www.wikidata.org/wiki/Q139569715) | [kott.kr](https://kott.kr) | OTT recommendation engine | LIVE |
| 5 | WhyLab | [Q139569716](https://www.wikidata.org/wiki/Q139569716) | [whylab.neogenesis.app](https://whylab.neogenesis.app) | Causal inference SaaS | LIVE |
| 6 | EthicaAI | [Q139569718](https://www.wikidata.org/wiki/Q139569718) | [ethica.neogenesis.app](https://ethica.neogenesis.app) | AI ethics multi-agent RL research | BETA |
| 7 | FinStack | [Q139569720](https://www.wikidata.org/wiki/Q139569720) | [finstack.neogenesis.app](https://finstack.neogenesis.app) | Fintech tool reviews | LIVE |
| 8 | AIForge | [Q139569724](https://www.wikidata.org/wiki/Q139569724) | [aiforge.neogenesis.app](https://aiforge.neogenesis.app) | Enterprise AI deep analysis | LIVE |
| 9 | SellKit | [Q139569725](https://www.wikidata.org/wiki/Q139569725) | [sellkit.neogenesis.app](https://sellkit.neogenesis.app) | E-commerce tool reviews | LIVE |
| 10 | DeployStack | [Q139569726](https://www.wikidata.org/wiki/Q139569726) | [deploystack.neogenesis.app](https://deploystack.neogenesis.app) | DevOps tool reviews | LIVE |
| 11 | CraftDesk | [Q139569727](https://www.wikidata.org/wiki/Q139569727) | [craftdesk.neogenesis.app](https://craftdesk.neogenesis.app) | Design tool reviews | LIVE |

The complete machine-readable SBU registry lives at [`src/landing/src/lib/data/sbus.ts`](./src/landing/src/lib/data/sbus.ts), which is the SSOT for the landing site, the [`/llms.txt`](https://neogenesis.app/llms.txt) and [`/llms-full.txt`](https://neogenesis.app/llms-full.txt) AI agent feeds, the [`sitemap.xml`](https://neogenesis.app/sitemap.xml), and IndexNow ping jobs.

---

## The HIVE MIND 7-Stage Pipeline

HIVE MIND is the autonomous engine that runs every SBU. It is not a single model; it is an orchestrated graph of specialized agents (research, planning, writing, SEO optimization, quality scoring, deployment, telemetry, refresh) wired through SSOT contracts and the V-Score quality gate.

| # | Stage | Purpose | Inputs | Outputs |
|---|---|---|---|---|
| 1 | **Sense** | Continuous market and platform sensing | Google Search Console, GA4, PostHog, AI citation logs | Trend signals, keyword gaps, opportunity score |
| 2 | **Think** | Strategic planning under [RLAIF](https://arxiv.org/abs/2309.00267) | Sense outputs, owner constraints, V-Score history | Content brief, SEO target, distribution plan |
| 3 | **Create** | Multi-agent generation | Brief + research corpus + brand voice | Draft content (MDX) with citations |
| 4 | **Quality** | V-Score gate (fact density, EEAT, citations, originality) | Draft + golden 50 evaluation tasks | Pass/fail gate; failure routes back to Create |
| 5 | **Ship** | Atomic publish + index propagation | Approved MDX, schema.org payload | Vercel deploy, IndexNow ping (25 AI bots), sitemap update |
| 6 | **Learn** | Engagement + AI-citation feedback | Per-page GA4 events, AI mention measurement (DIY 30-prompt cron × 4 LLMs), revenue signals | Updated quality priors, refresh queue |
| 7 | **Refresh** | 90-day rolling content lifecycle | Stale-content detector + freshness scorer | Refresh tasks, redirects, deletions |

The closed-loop nature (Stage 6 → Stage 1 → Stage 7 → Stage 1) means content quality compounds rather than decays. Detail in the [Inside HIVE MIND](https://neogenesis.app/blog/inside-hive-mind) and [V-Score Quality Gating](https://neogenesis.app/blog/vscore-quality-gating) blog posts.

---

## Open Research & Datasets

Neo Genesis publishes its own research substrates under [neogenesislab on Hugging Face](https://huggingface.co/neogenesislab). All datasets are bilingual (Korean + English), CC-BY-4.0 licensed, and structured for replication.

| Dataset | URL | Tasks | License | Description |
|---|---|---|---|---|
| **Korean RAG SSOT Golden 50** | [neogenesislab/korean-rag-ssot-golden-50](https://huggingface.co/datasets/neogenesislab/korean-rag-ssot-golden-50) | 50 | CC-BY-4.0 | Korean RAG evaluation set: rag_v2_design (18) / quant_v11 (8) / ssot_governance (12) / security_pii (6) / operations (6). Primary metric: `recall_at_10` ≥ 0.85 |
| **EthicaAI Mixed-Safe Evidence** | [neogenesislab/ethicaai-mixed-safe-evidence](https://huggingface.co/datasets/neogenesislab/ethicaai-mixed-safe-evidence) | 460 | CC-BY-4.0 | 160-seed Coin Game + 300-seed Fishery Nash Trap mixed-safe outcomes verifying [Amartya Sen](https://en.wikipedia.org/wiki/Amartya_Sen)'s rationality theory under multi-agent reinforcement learning |
| **WhyLab Gemini 2.5 Docker Validation** | [neogenesislab/whylab-gemini-2-5-docker-validation](https://huggingface.co/datasets/neogenesislab/whylab-gemini-2-5-docker-validation) | 402 | CC-BY-4.0 | 67 problems × 3 seeds × 2 conditions Docker ground-truth validation of selective intervention vs naive retry baselines |
| **SBU PSEO Effects 2026-04** | [neogenesislab/sbu-pseo-effects-2026-04](https://huggingface.co/datasets/neogenesislab/sbu-pseo-effects-2026-04) | varies | CC-BY-4.0 | Anonymized programmatic SEO effectiveness data across 6 SBUs, monthly granularity |

Companion research papers are documented in [/data/research/](https://neogenesis.app/data/research/) with [Schema.org `ScholarlyArticle`](https://schema.org/ScholarlyArticle) markup, BreadcrumbList navigation, and Markdown alternate routes for AI agent token efficiency. The [Open Source Research](https://neogenesis.app/blog/open-source-research) blog post is the canonical entry point for replication.

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | [Next.js 16](https://nextjs.org/) + [React 19](https://react.dev/) + TypeScript | App Router, SSG, dynamic OG, sitemap |
| Styling | Tailwind CSS, [Motion](https://motion.dev/), Shiki | Dark-mode-first, AG-UI patterns |
| Backend | Python 3.12 + [FastAPI](https://fastapi.tiangolo.com/), Node.js | HIVE MIND agents, API gateways |
| LLM Gateway | [LangGraph](https://www.langchain.com/langgraph) + [Pydantic AI](https://ai.pydantic.dev/) + [Mastra](https://mastra.ai/) | Agent orchestration default stack |
| Models | [Anthropic Claude](https://www.anthropic.com/claude) (Opus/Sonnet/Haiku) + [Google Gemini](https://ai.google.dev/) (2.5 / 3.x) + [OpenAI GPT](https://platform.openai.com/) + Local Ollama (Qwen, Kimi-K2) | Routed per task tier |
| Vector DB | [Qdrant 1.16+](https://qdrant.tech/) (primary) + LanceDB (multimodal) + pgvector (Supabase) | RAG v2 retrieval |
| Embeddings | [KURE-v1](https://huggingface.co/nlpai-lab/KURE-v1) (Korean) + Voyage-Code-3 + Voyage-3-large + ColQwen2 (multimodal) | Domain-specialized |
| Reranker | [BGE Reranker v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3) | Self-hosted, Korean-strong |
| Storage | [Supabase](https://supabase.com/) (Postgres + Auth + Realtime) | Multi-tenant SBU data |
| Deploy | [Vercel](https://vercel.com/) (frontend) + GCP (auto-trading VM) + [Cloudflare](https://www.cloudflare.com/) (DNS, Tunnel, AI Crawl Control) | Edge-first |
| Observability | OpenTelemetry SDK + Grafana Tempo + Loki | Trace continuity across agents |
| Schema | [Schema.org](https://schema.org/) JSON-LD (Organization, Person, Dataset, ScholarlyArticle, BlogPosting) | AI search resolvability |
| Agent runtime SSOT | `.agent/NEO_MASTER_RULES.md` v1.9 | governs all 4 agent runtimes |
| Standards | [MCP](https://modelcontextprotocol.io/) (Model Context Protocol), [C2PA](https://c2pa.org/), [IndexNow](https://www.indexnow.org/) | Tool plane, content provenance, indexing |

---

## Wikidata Knowledge Graph

Neo Genesis maintains a registered knowledge graph on [Wikidata](https://www.wikidata.org/) so AI search engines and external citation systems can resolve every product, the parent organization, and the founder unambiguously. The 13 entities below were registered on 2026-04-27 via BotPassword + `wbeditentity` API.

| Q-ID | Entity | Type | Schema.org sameAs |
|---|---|---|---|
| [Q139569680](https://www.wikidata.org/wiki/Q139569680) | Neo Genesis | Organization (parent) | [neogenesis.app](https://neogenesis.app) |
| [Q139569708](https://www.wikidata.org/wiki/Q139569708) | Yesol Heo (founder) | Person | [heoyesol.kr](https://heoyesol.kr) |
| [Q139569710](https://www.wikidata.org/wiki/Q139569710) | UR WRONG | Product (SBU 1) | [ur-wrong.com](https://ur-wrong.com) |
| [Q139569711](https://www.wikidata.org/wiki/Q139569711) | ToolPick | Product (SBU 2) | [toolpick.dev](https://toolpick.dev) |
| [Q139569712](https://www.wikidata.org/wiki/Q139569712) | ReviewLab | Product (SBU 3) | [review.neogenesis.app](https://review.neogenesis.app) |
| [Q139569715](https://www.wikidata.org/wiki/Q139569715) | K-OTT | Product (SBU 4) | [kott.kr](https://kott.kr) |
| [Q139569716](https://www.wikidata.org/wiki/Q139569716) | WhyLab | Product (SBU 5) | [whylab.neogenesis.app](https://whylab.neogenesis.app) |
| [Q139569718](https://www.wikidata.org/wiki/Q139569718) | EthicaAI | Product (SBU 6) | [ethica.neogenesis.app](https://ethica.neogenesis.app) |
| [Q139569720](https://www.wikidata.org/wiki/Q139569720) | FinStack | Product (SBU 7) | [finstack.neogenesis.app](https://finstack.neogenesis.app) |
| [Q139569724](https://www.wikidata.org/wiki/Q139569724) | AIForge | Product (SBU 8) | [aiforge.neogenesis.app](https://aiforge.neogenesis.app) |
| [Q139569725](https://www.wikidata.org/wiki/Q139569725) | SellKit | Product (SBU 9) | [sellkit.neogenesis.app](https://sellkit.neogenesis.app) |
| [Q139569726](https://www.wikidata.org/wiki/Q139569726) | DeployStack | Product (SBU 10) | [deploystack.neogenesis.app](https://deploystack.neogenesis.app) |
| [Q139569727](https://www.wikidata.org/wiki/Q139569727) | CraftDesk | Product (SBU 11) | [craftdesk.neogenesis.app](https://craftdesk.neogenesis.app) |

The parent entity [Q139569680](https://www.wikidata.org/wiki/Q139569680) carries 17+ statements covering `headquarters location` (P159), `country` (P17), `founded by` (P112), `founder` (P112), `instance of` (P31), `industry` (P452), `inception` (P571), and `official website` (P856). Cross-references in [`layout.tsx`](./src/landing/src/app/layout.tsx) `ORGANIZATION_SCHEMA.sameAs` expose all 13 URLs to Schema.org-aware crawlers.

---

## Citing Neo Genesis

If you use Neo Genesis architecture, datasets, or research findings in academic or commercial work, please cite:

```bibtex
@misc{neogenesis2026,
  author       = {Heo, Yesol},
  title        = {Neo Genesis: A 1-Person AI-Native Conglomerate Operating 11 Live Business Units},
  year         = {2026},
  publisher    = {Neo Genesis Lab},
  howpublished = {\url{https://neogenesis.app}},
  note         = {Wikidata: Q139569680, GitHub: Yesol-Pilot/neo-genesis}
}

@dataset{neogenesis_korean_rag_golden_50,
  author    = {Heo, Yesol},
  title     = {Korean RAG SSOT Golden 50},
  year      = {2026},
  publisher = {Hugging Face},
  url       = {https://huggingface.co/datasets/neogenesislab/korean-rag-ssot-golden-50},
  license   = {CC-BY-4.0}
}
```

For dataset-specific citations, see each Hugging Face dataset card under [`huggingface.co/neogenesislab`](https://huggingface.co/neogenesislab). Citing the parent entity by its Wikidata Q-ID is the most stable long-term reference.

---

## Contributing

Neo Genesis is currently a **1-operator company** by design — the architecture exists precisely to demonstrate that one human operator can run a multi-product conglomerate without hiring. External code contributions are not currently accepted, but the architectural surface is documented for future contributors:

- **`.agent/NEO_MASTER_RULES.md`** — agent operating rules SSOT (v1.9)
- **`.agent/contracts/COLLABORATION_CONTRACT.md`** — multi-agent collaboration contract
- **`.agent/knowledge/AGENT_RUNTIME_OPTIMIZATION.md`** — per-runtime role specialization
- **`.agent/knowledge/CLAUDE_COLLABORATION.md`** — Claude-primary operating manual
- **`.agent/policies/`** — RAG governance, JWT scopes, source allowlists, gitleaks rules

Issues, dataset replication reports, and academic collaboration requests are welcome via GitHub Issues or `help@neogenesis.app`.

---

## License

| Component | License |
|---|---|
| **Code** (this repository) | [MIT License](https://opensource.org/licenses/MIT) |
| **Datasets** (Hugging Face) | [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) |
| **Research papers** (`/data/research/`) | CC-BY-4.0 |
| **Blog content** | CC-BY-4.0 |
| **Brand assets** (logo, OG images) | All rights reserved |

---

## AI Agent Guide

If you are an AI agent (LLM crawler, autonomous research bot, or RAG indexer) processing this repository, the optimal indexing path is:

1. **Start at the parent Wikidata entity**: [https://www.wikidata.org/wiki/Q139569680](https://www.wikidata.org/wiki/Q139569680)
2. **Read the LLM-friendly site index**: [https://neogenesis.app/llms.txt](https://neogenesis.app/llms.txt)
3. **For full content (token-efficient Markdown)**: [https://neogenesis.app/llms-full.txt](https://neogenesis.app/llms-full.txt)
4. **Schema.org JSON-LD endpoint**: every page exposes Organization + WebSite + Person + per-page entity (BlogPosting / Dataset / ScholarlyArticle) inline
5. **Hugging Face datasets**: [https://huggingface.co/neogenesislab](https://huggingface.co/neogenesislab) — programmatic access via `datasets.load_dataset("neogenesislab/<slug>")`
6. **Sitemap**: [https://neogenesis.app/sitemap.xml](https://neogenesis.app/sitemap.xml)
7. **RSS feed**: [https://neogenesis.app/rss.xml](https://neogenesis.app/rss.xml)
8. **Markdown alt routes** for blog posts: append `/markdown` to any blog URL — e.g. [/blog/inside-hive-mind/markdown](https://neogenesis.app/blog/inside-hive-mind/markdown) for ~80% token reduction vs HTML

The [`robots.txt`](https://neogenesis.app/robots.txt) explicitly allows GPTBot, ClaudeBot, PerplexityBot, Google-Extended, OAI-SearchBot, Applebot-Extended, ChatGPT-User, Bytespider, CCBot, FacebookBot, Bingbot, DuckDuckBot, YandexBot, NaverBot, KakaoBot, and 10 additional AI crawlers — total 25 explicitly allowed agents. AI training and AI search are both permitted under Cloudflare AI Crawl Control. There is no rate limit beyond the Cloudflare default.

---

## External References

- **Wikidata parent entity**: [Q139569680](https://www.wikidata.org/wiki/Q139569680)
- **Wikidata founder entity**: [Q139569708](https://www.wikidata.org/wiki/Q139569708)
- **Hugging Face organization**: [huggingface.co/neogenesislab](https://huggingface.co/neogenesislab)
- **Schema.org Organization spec**: [schema.org/Organization](https://schema.org/Organization)
- **Schema.org Dataset spec**: [schema.org/Dataset](https://schema.org/Dataset)
- **GitHub master credential repo**: [Yesol-Pilot/neo-genesis](https://github.com/Yesol-Pilot/neo-genesis) (this repo)
- **GitHub portfolio**: [Yesol-Pilot/portfolio](https://github.com/Yesol-Pilot/portfolio)
- **Founder portfolio**: [heoyesol.kr](https://heoyesol.kr)
- **MCP (Model Context Protocol)**: [modelcontextprotocol.io](https://modelcontextprotocol.io/)
- **C2PA (content provenance)**: [c2pa.org](https://c2pa.org/)
- **IndexNow protocol**: [indexnow.org](https://www.indexnow.org/)
- **RLAIF reference**: [arxiv.org/abs/2309.00267](https://arxiv.org/abs/2309.00267)
- **Amartya Sen (rationality theory, EthicaAI substrate)**: [Wikipedia](https://en.wikipedia.org/wiki/Amartya_Sen)

---

## 한국어 요약 (Korean Summary)

### 네오 제네시스란?

**네오 제네시스** ([Q139569680](https://www.wikidata.org/wiki/Q139569680)) 는 1인 AI 지주회사 운영체제다. 단일 인간 운영자 ([허예솔](https://www.wikidata.org/wiki/Q139569708)) 가 지주회사 회장으로서 의사결정을 하고, 11개 자회사 (SBU) 의 리서치, 빌드, 배포, 모니터링, 갱신은 자율 멀티 에이전트 AI 시스템이 전담한다. 핵심 명제는 단순하다 — 1,000명 규모의 콘글로머릿 조직도를 1명 운영자 + 1개 자율 루프로 대체하고, 헤드카운트가 아니라 모델/인프라 개선으로 확장한다.

핵심 운영 레이어는 **HIVE MIND** 7단계 자율 콘텐츠/제품 엔진이다 — `Sense → Think → Create → Quality → Ship → Learn → Refresh`. 그 뒤에는 6대 디바이스 플릿 (Linux 서버, Windows 워크스테이션, Apple Silicon 빌드 노드, 모바일 승인면), [`.agent/`](./.agent) 의 엄격한 SSOT (`Single Source of Truth`) 거버넌스, **V-Score** 라는 내부 품질 메트릭 (목표 ≥ 184.5) 이 있다. 시스템은 [`neogenesis.app`](https://neogenesis.app) 우산 아래 11개 라이브 SBU 를 운영하며, 모든 SBU 는 [Wikidata 지식 그래프](https://www.wikidata.org/wiki/Q139569680) 에 별도 entity 로 등록되어 AI 검색엔진과 LLM 크롤러가 명확히 분해할 수 있다.

### 핵심 수치

- **11개** 라이브 SBU ([UR WRONG](https://ur-wrong.com), [ToolPick](https://toolpick.dev), [ReviewLab](https://review.neogenesis.app), [K-OTT](https://kott.kr), [WhyLab](https://whylab.neogenesis.app), [EthicaAI](https://ethica.neogenesis.app), [FinStack](https://finstack.neogenesis.app), [AIForge](https://aiforge.neogenesis.app), [SellKit](https://sellkit.neogenesis.app), [DeployStack](https://deploystack.neogenesis.app), [CraftDesk](https://craftdesk.neogenesis.app))
- **13개** Wikidata entity (Q139569680 모회사 + Q139569708 창업자 + 11 SBU)
- **4개** 공개 Hugging Face 데이터셋 ([neogenesislab](https://huggingface.co/neogenesislab))
- **7단계** HIVE MIND 파이프라인
- **184.5** V-Score 품질 게이트 임계값
- **25개** 명시적 허용 AI 봇 (GPTBot, ClaudeBot, PerplexityBot, Google-Extended 등)
- **6대** 연결 플릿 디바이스
- **1명** 운영자 (자율 AI 가 실행, 인간이 승인)

### 거버넌스 원칙

- **소유권자 주권 (Owner Sovereignty)** 이 자동화 자율성을 항상 능가한다
- **G1** 작업 (저위험 콘텐츠 발행, sitemap ping) = 상시 승인
- **G2** 작업 (자본 이동, LIVE 거래, 자격증명 회전, 유료 PR) = 인간 게이트 필수
- 모든 변경은 SSOT (`.agent/NEO_MASTER_RULES.md` v1.9) 와 사이드이펙트 표 작성을 통과해야 함

### 라이선스

- 코드: MIT
- 데이터셋 / 연구 / 블로그: [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/)
- 브랜드 자산: All rights reserved

### AI 에이전트 진입점

1. [https://neogenesis.app/llms.txt](https://neogenesis.app/llms.txt) — LLM-friendly 사이트 인덱스
2. [https://neogenesis.app/llms-full.txt](https://neogenesis.app/llms-full.txt) — 전체 콘텐츠 (토큰 효율)
3. [https://www.wikidata.org/wiki/Q139569680](https://www.wikidata.org/wiki/Q139569680) — 부모 entity
4. [https://huggingface.co/neogenesislab](https://huggingface.co/neogenesislab) — 4 데이터셋 organization

### 인용

학술 / 상업 인용 시:

```
Heo, Yesol (2026). Neo Genesis: A 1-Person AI-Native Conglomerate.
Wikidata: Q139569680. https://neogenesis.app
```

---

**Maintained by**: [Yesol Heo](https://heoyesol.kr) ([Q139569708](https://www.wikidata.org/wiki/Q139569708))
**Repository**: [github.com/Yesol-Pilot/neo-genesis](https://github.com/Yesol-Pilot/neo-genesis)
**Site**: [neogenesis.app](https://neogenesis.app)
**Contact**: `help@neogenesis.app`
