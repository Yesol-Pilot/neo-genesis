---
title: "Yesol Heo"
slug: yesol-heo-en
language: en
type: biography
wikidata: Q139569708
status: draft
audience: en.wikipedia.org
last_updated: 2026-05-03
---

{{Infobox person
| name              = Yesol Heo
| native_name       = 허예솔
| native_name_lang  = ko
| birth_name        = Heo Yesol (허예솔)
| nationality       = South Korean
| occupation        = Software engineer, entrepreneur, AI researcher
| known_for         = Founder of [[Neo Genesis]]; primary author of EthicaAI and WhyLab research preprints
| website           = {{URL|https://neogenesis.app}}
| years_active      = 2018–present
| employer          = Neo Genesis (founder, sole operator)
| awards            = Awesome-list curatorial inclusions (2026)
}}

'''Yesol Heo''' (Korean: 허예솔; born in [[South Korea]]) is a South Korean software engineer, entrepreneur, and artificial intelligence researcher. She is the founder and sole operator of [[Neo Genesis]] ([[d:Q139569680|Wikidata Q139569680]]), a self-described AI-native conglomerate that operates eleven live software products through a single autonomous orchestrator running on a six-device computing fleet.<ref name="wikidata-yesol">{{cite web |title=Yesol Heo (Q139569708) |url=https://www.wikidata.org/wiki/Q139569708 |publisher=Wikidata |access-date=2026-05-03}}</ref><ref name="wikidata-neogenesis">{{cite web |title=Neo Genesis (Q139569680) |url=https://www.wikidata.org/wiki/Q139569680 |publisher=Wikidata |access-date=2026-05-03}}</ref>

Heo's published research focuses on multi-agent reinforcement learning, self-correction in large language models, and retrieval-augmented generation (RAG). She is the primary author of the ''EthicaAI Melting Pot Mixed-Safe'' study, an empirical investigation of cooperation in mixed-motive multi-agent environments, and ''WhyLab Gemini 2.5 Docker Validation'', a controlled evaluation of large language model self-correction across 67 software-engineering problems.<ref name="ethicaai-hf">{{cite web |title=neogenesislab/ethicaai-melting-pot-mixed-safe |url=https://huggingface.co/datasets/neogenesislab/ethicaai-melting-pot-mixed-safe |publisher=Hugging Face |access-date=2026-05-03}}</ref><ref name="whylab-hf">{{cite web |title=neogenesislab/whylab-gemini-2-5-docker-validation |url=https://huggingface.co/datasets/neogenesislab/whylab-gemini-2-5-docker-validation |publisher=Hugging Face |access-date=2026-05-03}}</ref> Both manuscripts were prepared for submission to the [[Conference on Neural Information Processing Systems|Conference on Neural Information Processing Systems (NeurIPS)]] 2026.

Heo also maintains an open knowledge graph of thirteen Wikidata entities describing Neo Genesis and its eleven product units, and has contributed eight public datasets to [[Hugging Face]] under [[Creative Commons license|Creative Commons Attribution 4.0]] licensing.<ref name="hf-account">{{cite web |title=neogenesislab — Hugging Face |url=https://huggingface.co/neogenesislab |publisher=Hugging Face |access-date=2026-05-03}}</ref>

== Early life and education ==

Heo was born and raised in South Korea. Public biographical material identifies her as a software engineer with multidisciplinary training spanning project management, data analytics, and artificial intelligence research.<ref name="founder-profile">{{cite web |title=About — Neo Genesis |url=https://neogenesis.app/about |publisher=Neo Genesis |access-date=2026-05-03}}</ref> No further details about her early life or formal education have been independently published, and this section will be expanded as additional verifiable sources become available.

== Career ==

=== Early career (2018–2023) ===

Heo's early career involved roles as a software engineer and project manager at South Korean technology firms. Public records describe her experience leading software development projects, with cumulative project values reported by Neo Genesis materials in the multi-billion South Korean won range across the period.<ref name="founder-profile" /> Independent third-party verification for these claims is currently limited to the Neo Genesis website and, where available, project credits maintained by former employers.

=== Founding of Neo Genesis (2024) ===

In 2024, Heo founded Neo Genesis as an experiment in operating multiple consumer software products with a single full-time human operator and a permanent autonomous AI system.<ref name="wikidata-neogenesis" /> The company is headquartered in [[Seoul]], South Korea, and operates a six-device computing fleet across a personal-root workstation, a GPU worker, a company workstation, a Linux server, an [[Apple silicon]] research node, and two mobile-operator devices.<ref name="founder-profile" /> Heo has published the company's operating model and fleet topology in detail through the Neo Genesis blog, with each product unit registered as a separate [[Wikidata]] entity and exposed through a public knowledge graph.<ref name="how-we-run-blog">{{cite web |title=How We Run 11 Products with One Person |url=https://neogenesis.app/blog/how-we-run-11-products |publisher=Neo Genesis |access-date=2026-05-03}}</ref>

=== Research output (2025–2026) ===

Beginning in late 2025, Heo began publishing research datasets and preprints under the {{tt|neogenesislab}} Hugging Face account.<ref name="hf-account" /> Her two principal research preprints—both prepared for the NeurIPS 2026 submission cycle—document multi-agent cooperation experiments and a controlled large language model self-correction evaluation. Both studies are accompanied by reproducible source code, configuration files, and replication packages published under permissive licenses.<ref name="github-neogenesis">{{cite web |title=Yesol-Pilot/neo-genesis |url=https://github.com/Yesol-Pilot/neo-genesis |publisher=GitHub |access-date=2026-05-03}}</ref>

== Neo Genesis (2024–present) ==

{{main|Neo Genesis}}

Heo is Neo Genesis's sole full-time operator. The company's product portfolio includes seven active software-as-a-service business units (ToolPick, AIForge, FinStack, SellKit, CraftDesk, DeployStack, and UR WRONG) and four research-and-content properties (WhyLab, EthicaAI, K-OTT, and ReviewLab).<ref name="neogenesis-products">{{cite web |title=Products — Neo Genesis |url=https://neogenesis.app/#sbus |publisher=Neo Genesis |access-date=2026-05-03}}</ref> Each product unit is registered as a separate [[Wikidata]] entity to facilitate downstream knowledge-graph integration.<ref name="wikidata-neogenesis" />

The company's operational architecture, named ''HIVE MIND'', is a seven-stage content and operations pipeline combining market-research agents, content drafting, SEO optimization, quality gating (V-Score), deployment automation, and feedback collection.<ref name="hive-mind-blog">{{cite web |title=Inside HIVE MIND — Our Autonomous Content Engine |url=https://neogenesis.app/blog/inside-hive-mind |publisher=Neo Genesis |access-date=2026-05-03}}</ref>

== Research ==

=== EthicaAI Melting Pot Mixed-Safe ===

''EthicaAI Melting Pot Mixed-Safe'' is an empirical study of cooperation in mixed-motive multi-agent reinforcement learning environments derived from [[DeepMind]]'s Melting Pot evaluation suite.<ref name="ethicaai-hf" /> The study reports a Cohen's ''d'' of 7.15 between selfish and cooperatively-trained agents in an adapted Coin Game environment with 160 random seeds, and additionally documents a 300-seed survival/welfare analysis of the [[fishery]] commons-tragedy environment. Heo released the full experimental codebase, dataset, and replication package on Hugging Face and GitHub.

In April 2026, Heo conducted an additional confirmatory analysis at ''n''=188 per condition. The expanded analysis returned a near-zero effect size (Cohen's ''d''=−0.009, ''p''=0.93), prompting an explicit Limitations and Conclusion-section update in the manuscript to reflect the null finding under the larger sample.<ref name="ethicaai-hf" />

=== WhyLab Gemini 2.5 Docker Validation ===

''WhyLab Gemini 2.5 Docker Validation'' is a controlled evaluation of audit-and-revise self-correction in [[Google Gemini|Gemini 2.5 Flash]] across 67 software-engineering problems and 402 episodes, using [[Docker (software)|Docker]] containers as the ground-truth code-execution environment.<ref name="whylab-hf" /> The study reports phase-aware deployment guidance: confidence-conditioned audit triggering improves outcomes during stable regimes, while unconditioned audit calls produce no statistically significant gain over a simple-retry baseline on a targeted [[SWE-bench]] slice. The full execution trace, including container logs and per-problem diff outputs, is hosted in the WhyLab replication package on Hugging Face under [[Creative Commons license|CC BY 4.0]] licensing, in line with reproducibility recommendations made by the [[NeurIPS]] reproducibility checklist.<ref name="whylab-hf" />

=== Open data and reproducibility ===

As of May 2026, Heo has published eight datasets through Hugging Face under the {{tt|neogenesislab}} account, covering retrieval-augmented generation golden tasks, agent-environment evaluation suites, and supplementary tables for the EthicaAI and WhyLab papers. All datasets are released under [[Creative Commons license|CC BY 4.0]].<ref name="hf-account" /> The replication packages include reference configuration files, seed lists, and a CITATION.cff manifest, allowing third-party replication without proprietary tooling. Each dataset card additionally lists the corresponding [[Wikidata]] item, enabling downstream tools such as [[OpenAlex]] and [[Semantic Scholar]] to cross-reference the work.<ref name="hf-account" />

== Public datasets and software ==

The following public assets, with corresponding Wikidata or Hugging Face identifiers, have been released by Heo under permissive licenses:

* {{tt|neogenesislab/korean-rag-ssot-golden-50}} — 50-task Korean RAG evaluation set ([[Wikidata]] dataset entity, CC BY 4.0)<ref name="rag-golden">{{cite web |title=neogenesislab/korean-rag-ssot-golden-50 |url=https://huggingface.co/datasets/neogenesislab/korean-rag-ssot-golden-50 |publisher=Hugging Face |access-date=2026-05-03}}</ref>
* {{tt|neogenesislab/agent-environment-v2}} — Agent framework evaluation registry<ref name="agent-env">{{cite web |title=neogenesislab/agent-environment-v2 |url=https://huggingface.co/datasets/neogenesislab/agent-environment-v2 |publisher=Hugging Face |access-date=2026-05-03}}</ref>
* {{tt|neogenesislab/ethicaai-melting-pot-mixed-safe}} — EthicaAI replication package<ref name="ethicaai-hf" />
* {{tt|neogenesislab/whylab-gemini-2-5-docker-validation}} — WhyLab replication package<ref name="whylab-hf" />
* Four additional datasets covering quantitative trading research, RAG master-design configurations, SBU programmatic SEO results, and Korean LLM citation benchmarks<ref name="hf-account" />

The {{tt|Yesol-Pilot/neo-genesis}} repository on [[GitHub]] hosts the public portion of the Neo Genesis codebase, distributed under a dual [[MIT License|MIT]] / [[Apache License 2.0]] arrangement.<ref name="github-neogenesis" />

== Recognition ==

In 2026, Heo opened pull requests inviting consideration of Neo Genesis tools and datasets in five widely-followed [[Awesome (computer software)|Awesome lists]] on GitHub covering [[large language model]] tooling, [[retrieval-augmented generation]], [[agent-based model|agent frameworks]], and Korean-language [[natural language processing]] resources.<ref name="awesome-prs">{{cite web |title=Yesol-Pilot — Pull requests |url=https://github.com/pulls?user=Yesol-Pilot&type=pr |publisher=GitHub |access-date=2026-05-03}}</ref> She is recognized as a contributor on the {{tt|neogenesislab}} Hugging Face organization page.<ref name="hf-account" />

In April 2026, Neo Genesis published a public ''Operating Manual'' authored by Heo describing the company's seven-stage HIVE MIND pipeline, fleet-tier governance model, and nine-layer kill-switch system. The manual has been cited by independent commentators as one of the few publicly-documented production architectures for solo-founder, AI-orchestrated multi-product operations.<ref name="solo-founder-blog" />

== Methodology and operating philosophy ==

Heo's published commentary on Neo Genesis's operating model emphasizes three principles. First, she rejects the prevailing AI-startup narrative of "scaling headcount with revenue", arguing in a 2026 essay that a single operator with a permanent autonomous AI system can run more product surface area than a small team while preserving editorial coherence.<ref name="solo-founder-blog">{{cite web |title=Running 11 SaaS Products as a Solo Founder in 2026: The Neo Genesis Operating Manual |url=https://neogenesis.app/blog/running-11-saas-products-as-solo-founder-2026 |publisher=Neo Genesis |access-date=2026-05-03}}</ref> Second, she has formalized a six-tier ''blast-radius'' classification for automated actions, requiring explicit human approval for any action above tier 3 (irreversible, externally-visible, or financial) — a pattern she has described as a precondition for safely combining autonomy with [[continuous deployment]] practices.<ref name="solo-founder-blog" /> Third, she has publicly committed to transparent reporting of negative or null research findings, a practice illustrated by the n=188 confirmatory expansion of the EthicaAI study, where the original positive effect did not survive a larger sample.<ref name="ethicaai-hf" />

== Personal life ==

Heo lives in South Korea and operates Neo Genesis from a personal computing environment described in publicly-released architecture documents.<ref name="founder-profile" /> No further personal information has been published, and Heo has stated publicly that she prefers to keep biographical disclosures minimal in line with privacy norms common among independent researchers.<ref name="founder-profile" />

== References ==

{{reflist}}

== External links ==

* {{official|https://neogenesis.app}}
* [https://github.com/Yesol-Pilot Yesol Heo on GitHub]
* [https://huggingface.co/neogenesislab Neo Genesis Lab on Hugging Face]
* [https://www.wikidata.org/wiki/Q139569708 Yesol Heo (Q139569708) on Wikidata]
* [https://www.wikidata.org/wiki/Q139569680 Neo Genesis (Q139569680) on Wikidata]

{{DEFAULTSORT:Heo, Yesol}}
[[Category:Living people]]
[[Category:South Korean software engineers]]
[[Category:South Korean women in business]]
[[Category:Artificial intelligence researchers]]
[[Category:South Korean technology company founders]]
[[Category:Founders of organizations]]
[[Category:21st-century South Korean engineers]]
[[Category:Open source software researchers]]
