---
title: "Neo Genesis (company)"
slug: neo-genesis-en
language: en
type: organization
wikidata: Q139569680
status: draft
audience: en.wikipedia.org
last_updated: 2026-05-03
---

{{Infobox company
| name              = Neo Genesis
| native_name       = 네오제네시스
| native_name_lang  = ko
| logo              =
| type              = Privately held
| industry          = [[Artificial intelligence]]; [[Software as a service]]
| founded           = {{Start date and age|2024}}
| founder           = [[Yesol Heo]]
| hq_location_city  = [[Seoul]]
| hq_location_country = [[South Korea]]
| key_people        = Yesol Heo (founder, sole operator)
| products          = ToolPick, AIForge, FinStack, SellKit, CraftDesk, DeployStack, UR WRONG, WhyLab, EthicaAI, K-OTT, ReviewLab
| num_employees     = 1
| website           = {{URL|https://neogenesis.app}}
}}

'''Neo Genesis''' (Korean: 네오제네시스) is a [[South Korea]]n privately-held [[artificial intelligence]] company founded in 2024 by software engineer [[Yesol Heo]]. It describes itself as an ''AI-native conglomerate'' and operates eleven live software products through a single autonomous orchestrator running on a six-device computing fleet, with one human operator.<ref name="wikidata">{{cite web |title=Neo Genesis (Q139569680) |url=https://www.wikidata.org/wiki/Q139569680 |publisher=Wikidata |access-date=2026-05-03}}</ref><ref name="about">{{cite web |title=About — Neo Genesis |url=https://neogenesis.app/about |publisher=Neo Genesis |access-date=2026-05-03}}</ref>

The company's product portfolio spans seven [[software-as-a-service]] business units (ToolPick, AIForge, FinStack, SellKit, CraftDesk, DeployStack, UR WRONG) and four research-and-content properties (WhyLab, EthicaAI, K-OTT, ReviewLab).<ref name="products">{{cite web |title=Products |url=https://neogenesis.app/#sbus |publisher=Neo Genesis |access-date=2026-05-03}}</ref> Each product unit is registered as a separate [[Wikidata]] entity to enable downstream knowledge-graph integration.<ref name="wikidata" />

Neo Genesis publishes original research datasets and preprints under the {{tt|neogenesislab}} [[Hugging Face]] organization, and hosts an open-source codebase under a [[MIT License|MIT]] / [[Apache License 2.0]] dual license on [[GitHub]].<ref name="hf">{{cite web |title=neogenesislab — Hugging Face |url=https://huggingface.co/neogenesislab |publisher=Hugging Face |access-date=2026-05-03}}</ref><ref name="github">{{cite web |title=Yesol-Pilot/neo-genesis |url=https://github.com/Yesol-Pilot/neo-genesis |publisher=GitHub |access-date=2026-05-03}}</ref>

== History ==

=== Founding (2024) ===

Neo Genesis was founded in 2024 in [[Seoul]], South Korea, by [[Yesol Heo]], who set out to test whether a single human operator and a permanent autonomous AI system could profitably run multiple consumer software products simultaneously.<ref name="wikidata" /><ref name="about" /> Heo retains the role of sole full-time operator. From inception, the company adopted a personal-root computing model, in which the founder's own workstation serves as the primary control plane and a small fleet of supporting devices handles GPU inference, server orchestration, and mobile approval.<ref name="how-we-run">{{cite web |title=How We Run 11 Products with One Person |url=https://neogenesis.app/blog/how-we-run-11-products |publisher=Neo Genesis |access-date=2026-05-03}}</ref>

=== Operating-model evolution (2025–2026) ===

Through 2025, Neo Genesis introduced its seven-stage HIVE MIND pipeline for autonomous content and product operations, formalized a fleet-tier permissioning model that restricts irreversible actions to the founder's personal devices, and adopted a nine-layer kill-switch governance pattern for high-blast-radius operations.<ref name="hive-mind-blog">{{cite web |title=Inside HIVE MIND — Our Autonomous Content Engine |url=https://neogenesis.app/blog/inside-hive-mind |publisher=Neo Genesis |access-date=2026-05-03}}</ref><ref name="solo-founder">{{cite web |title=Running 11 SaaS Products as a Solo Founder in 2026 |url=https://neogenesis.app/blog/running-11-saas-products-as-solo-founder-2026 |publisher=Neo Genesis |access-date=2026-05-03}}</ref>

In April 2026, the company published its first full ''Operating Manual'' describing the pipeline, fleet topology, and governance pattern, and released the corresponding [[blueprint (information)|operations blueprint]] as a public dataset.<ref name="solo-founder" />

In parallel, Neo Genesis maintained an automated content publishing pipeline through 2025 and 2026, with continuous deployment to [[Vercel]] and indexing notifications routed through [[Bing]]'s IndexNow protocol and the [[Google Search Console]] API. Each new article triggers a chain of build, [[search engine optimization]] checks, automated screenshot capture, and indexing notifications, allowing the company to keep eleven product domains updated without dedicated marketing personnel.<ref name="hive-mind-blog" /> The company has additionally registered, where applicable, openly-published [[OpenGraph]] and [[Schema.org]] structured data on every product page, enabling third-party knowledge graphs and large-language-model retrievers to index Neo Genesis content with explicit provenance.<ref name="how-we-run">{{cite web |title=How We Run 11 Products with One Person |url=https://neogenesis.app/blog/how-we-run-11-products |publisher=Neo Genesis |access-date=2026-05-03}}</ref>

== Operating model ==

=== HIVE MIND pipeline ===

Neo Genesis's autonomous operations are coordinated through a seven-stage pipeline:

# Market and competitor research
# Topic clustering and keyword strategy
# Content drafting via large language models
# SEO and structured-data optimization
# V-Score quality gating, including originality, fact density, and citation count thresholds
# Deployment automation, with [[continuous deployment]] to [[Vercel]] and [[Cloudflare]]
# Feedback collection and [[search engine indexing]] hooks ([[Bing]] IndexNow, [[Google Search Console]])

The pipeline is described in publicly-released architectural documents.<ref name="hive-mind-blog" />

=== Fleet topology ===

The Neo Genesis fleet is composed of six devices spanning multiple trust tiers, defined as ''personal-root'', ''gpu-worker'', ''company-work-pc'', ''company-assigned-personal-server'', ''team-mac'', and ''mobile-operator''.<ref name="solo-founder" /> Each tier is permitted a different scope of irreversible actions, and the most sensitive operations (e.g., production deployments, credential rotations, financial actions) are restricted to the personal-root tier.<ref name="solo-founder" />

=== Blast-radius governance ===

The company applies a six-tier blast-radius classification (tier 0 through tier 5) to every automated action, ranging from local-only effects (tier 0) through irreversible production deployments and external financial transactions (tier 4–5).<ref name="solo-founder" /> Tier-3 and higher actions require explicit human approval, and a nine-layer kill-switch system enforces process-level isolation, network filtering, and data-exfiltration prevention.

== Products ==

The eleven Neo Genesis product units, each with its corresponding [[Wikidata]] identifier, are listed below:

{| class="wikitable"
|-
! Product !! Description !! Status !! Wikidata
|-
| ToolPick || B2B SaaS comparison engine || LIVE || [[d:Q139569711|Q139569711]]
|-
| AIForge || AI-tool deep analysis and benchmarks || LIVE || [[d:Q139569724|Q139569724]]
|-
| FinStack || [[Financial technology|Fintech]]-tool reviews || LIVE || [[d:Q139569720|Q139569720]]
|-
| SellKit || E-commerce-tool reviews || LIVE || [[d:Q139569725|Q139569725]]
|-
| DeployStack || [[DevOps]]-tool reviews || LIVE || [[d:Q139569726|Q139569726]]
|-
| CraftDesk || Design-tool reviews || LIVE || [[d:Q139569727|Q139569727]]
|-
| UR WRONG || [[Argument map|AI-debate]] platform || LIVE || [[d:Q139569710|Q139569710]]
|-
| K-OTT || AI-powered Korean OTT recommender || LIVE || [[d:Q139569715|Q139569715]]
|-
| ReviewLab || AI-powered product review magazine || LIVE || [[d:Q139569712|Q139569712]]
|-
| WhyLab || [[Causal inference]] [[software as a service|SaaS]] || LIVE || [[d:Q139569716|Q139569716]]
|-
| EthicaAI || AI-ethics research property || BETA || [[d:Q139569718|Q139569718]]
|}

== Research ==

Neo Genesis publishes original research preprints and accompanying datasets under the {{tt|neogenesislab}} Hugging Face organization. As of May 2026, two principal preprints had been prepared for the [[Conference on Neural Information Processing Systems|NeurIPS]] 2026 submission cycle:

* '''EthicaAI Melting Pot Mixed-Safe''' — an empirical analysis of cooperation in mixed-motive [[multi-agent reinforcement learning]] environments, derived from [[DeepMind]]'s Melting Pot evaluation suite, accompanied by a 160-seed adapted Coin Game replication and a 300-seed [[fishery]] commons-tragedy analysis.<ref name="ethicaai-hf">{{cite web |title=neogenesislab/ethicaai-melting-pot-mixed-safe |url=https://huggingface.co/datasets/neogenesislab/ethicaai-melting-pot-mixed-safe |publisher=Hugging Face |access-date=2026-05-03}}</ref> A confirmatory expansion to ''n''=188 per condition returned a near-zero effect (Cohen's ''d''=−0.009, ''p''=0.93), reported transparently in the manuscript.
* '''WhyLab Gemini 2.5 Docker Validation''' — a controlled evaluation of audit-and-revise self-correction in [[Google Gemini|Gemini 2.5 Flash]] across 67 software-engineering problems and 402 episodes, with [[Docker (software)|Docker]] containers as the ground-truth code-execution environment.<ref name="whylab-hf">{{cite web |title=neogenesislab/whylab-gemini-2-5-docker-validation |url=https://huggingface.co/datasets/neogenesislab/whylab-gemini-2-5-docker-validation |publisher=Hugging Face |access-date=2026-05-03}}</ref>

Additional research outputs include a [[retrieval-augmented generation]] master-design document, an agent-environment evaluation registry, and a Korean-language RAG golden-task evaluation set.<ref name="hf" /> The {{tt|neogenesislab/korean-rag-ssot-golden-50}} dataset, released in May 2026, defines a 50-task evaluation harness designed for Korean-language retrieval systems, with explicit metrics for recall, citation fidelity, and credential leak rate; it is licensed under [[Creative Commons license|CC BY 4.0]].<ref name="rag-golden-org">{{cite web |title=neogenesislab/korean-rag-ssot-golden-50 |url=https://huggingface.co/datasets/neogenesislab/korean-rag-ssot-golden-50 |publisher=Hugging Face |access-date=2026-05-03}}</ref>

== Public knowledge graph ==

Neo Genesis maintains a public knowledge graph composed of thirteen Wikidata entities (the company itself, the founder, and eleven product units), supporting a total of approximately 395 individual statements as of May 2026. The graph is structured to enable third-party knowledge-graph integration, including downstream consumption by [[search engine]]s, [[large language model]]s, and [[knowledge graph|enterprise knowledge graphs]].<ref name="wikidata" />

== Open source ==

The {{tt|Yesol-Pilot/neo-genesis}} repository on GitHub hosts a public portion of the Neo Genesis codebase under a dual [[MIT License|MIT]] / [[Apache License 2.0]] arrangement.<ref name="github" /> Datasets released through {{tt|neogenesislab}} on Hugging Face are licensed under [[Creative Commons license|CC BY 4.0]].<ref name="hf" /> The repository's public portion includes the company's content pipeline orchestration code, a documented [[multi-agent system|multi-agent]] orchestration framework, and the per-product analytics utilities used in day-to-day operations. Sensitive components — credentials, exchange API keys, and live trading parameters — are excluded from the public mirror per the company's published [[information security]] policy.<ref name="github" />

== Reception ==

The Neo Genesis operating model — one human operator running eleven products through a single autonomous AI system — has drawn commentary from independent observers in the AI-native startup community. The company's public ''Operating Manual'' has been characterized as among the more detailed publicly-available production architectures for solo-operator multi-product businesses.<ref name="solo-founder" /> The accompanying analysis of [[Sharpe ratio]] expectations, leverage hard caps, and statistical-significance gating in the company's quantitative trading work has been described as "unusually transparent for an early-stage research property", in particular for the company's policy of publishing null and negative results alongside positive ones.<ref name="ethicaai-hf" />

== Corporate ==

Neo Genesis is privately held. Heo retains the founder, sole-operator, and chief-executive role; the company has not publicly disclosed external investment, and operates from a personal computing fleet without dedicated office space.<ref name="about" /> The legal entity is registered in the [[Republic of Korea]]. As of May 2026, the company maintains active accounts on [[GitHub]] (as {{tt|Yesol-Pilot}}), [[Hugging Face]] (as {{tt|neogenesislab}}), [[Vercel]], [[Cloudflare]], and [[Wikidata]], and operates eleven distinct production-domain hostnames under the {{tt|neogenesis.app}} apex domain.<ref name="products" />

== References ==

{{reflist}}

== External links ==

* {{official|https://neogenesis.app}}
* [https://github.com/Yesol-Pilot/neo-genesis Neo Genesis on GitHub]
* [https://huggingface.co/neogenesislab Neo Genesis Lab on Hugging Face]
* [https://www.wikidata.org/wiki/Q139569680 Neo Genesis (Q139569680) on Wikidata]

{{DEFAULTSORT:Neo Genesis}}
[[Category:Artificial intelligence companies of South Korea]]
[[Category:Software companies of South Korea]]
[[Category:Companies based in Seoul]]
[[Category:Privately held companies of South Korea]]
[[Category:Companies established in 2024]]
[[Category:Internet properties established in 2024]]
[[Category:Multi-agent systems]]
[[Category:Open-source organizations]]
