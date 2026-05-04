# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

For citation, see [`CITATION.cff`](./CITATION.cff). The canonical Wikidata entity is [Q139569680](https://www.wikidata.org/wiki/Q139569680).

## [Unreleased]

### Planned
- GitHub topics on `Yesol-Pilot/neo-genesis` for discoverability (owner action).
- Bing Webmaster Tools verification (5 min owner G2).
- Show HN post for EthicaAI Melting Pot evidence (owner G2).

## [0.13.0] - 2026-05-04

P13: Multilingual translation, cross-publish, and community engagement infrastructure.

### Added
- **Agent YY (multilingual)**: 17 glossary terms x 3 locales (ko/ja/zh) = 51 new locale definitions, 136 `DefinedTerm` Schema.org instances. 3 new Korean blog posts (`how-we-run-11-products-ko`, `inside-hive-mind-ko`, `running-11-saas-products-as-solo-founder-2026-ko`, ~6,100 native Korean words). About page Korean section expanded to ~600 native words. Sitemap 14 to 17 blog URLs. Cost: \$0 (native authored).
- **Agent AAA (cross-publish)**: GitHub Discussion #2 (Inside HIVE MIND) and #3 (Solo founder) published with explicit canonical URL attribution (top blockquote and closing link). 4 ready-to-paste markdown files for dev.to and Hashnode (front-matter `canonical_url` set), pending owner API key generation.
- **Direct work**: GitHub Discussions enabled, Discussion #1 (Q2 Status Report) posted, Yandex Webmaster sitemap ping HTTP 200.
- **Community files**: `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1 reference), `SECURITY.md` (RFC 9116 aligned), `.github/FUNDING.yml`, issue templates (bug report, feature request, dataset use, blank issues disabled), PR template with schema and citation impact checklist.
- **Schema enrichment**: 3 GitHub Discussion URLs added to `ORGANIZATION_SCHEMA.sameAs`. Community Discussions section added to `llms.txt` and `llms-full.txt` (canonical attribution policy documented).
- **Bidirectional translation linking**: `BlogPostSchemas` helper auto-detects `<slug>-ko` siblings and emits `workTranslation` `BlogPosting` node, mirroring the Korean side's `translationOfWork`. Fixes the known limitation that the 2 static English blog pages did not auto-emit locale alternates.

## [1.0.0] - 2026-05-04

First public source release. Foundation of the project's source-of-truth, infrastructure, and citable assets.

### Added
- Public source release of `Yesol-Pilot/neo-genesis` under MIT + Apache-2.0 dual license.
- 8 published Hugging Face datasets under [`neogenesislab`](https://huggingface.co/neogenesislab) (Korean RAG SSOT Golden 50, EthicaAI Mixed-Safe Evidence, WhyLab Gemini 2.5 Docker Validation, SBU pSEO Effects 2026-04, Cross-Agent Review Queue, Korean LLM Citation Baseline 2026, Sora Multi-Device Orchestration, Quant v11 Ensemble 6-Alpha Specs).
- 9 Zenodo software/dataset DOIs anchoring all published artifacts.
- 13 Wikidata Q-items registered (parent organization Q139569680, founder Q139569708, 11 SBU entities) with 439 statements.
- GitHub release `v1.0.0` tagged.
- [`CITATION.cff`](./CITATION.cff) for the GitHub "Cite this repository" surface.

### Changed
- Repository visibility set to PUBLIC.

## [0.12.0] - 2026-05-04

P12: Knowledge base, PWA, and Search Console submission.

### Added
- `/docs` knowledge base on `neogenesis.app` with glossary, architecture documentation, and contributor-facing references.
- Progressive Web App (PWA) manifest and service-worker layer.
- Google Search Console submission (HTTP 204 confirmation).
- 5-agent autonomous content loop fully integrated.

### Fixed
- Telegram polling conflict (permanent resolution) and Sora answer-quality regression.

## [0.11.0] - 2026-05-04

P11: Blog auto-generation pipeline and 9 infrastructure surfaces.

### Added
- Blog auto-gen pipeline (`scripts/blog_autogen/run_pipeline.py`) producing draft → V-Score gate → publish flow.
- 9 new infrastructure surfaces closing prior gap audit (owner gap fix).
- 6 parallel agents coordinating content generation, schema enforcement, and citation HEAD verification.

## [0.10.0] - 2026-05-04

P10: Trust Manufacturing — DOIs, Wikipedia drafts, and OpenAlex linkage.

### Added
- 9 Zenodo DOIs covering software releases and datasets.
- 4 Wikipedia draft articles.
- Q2 Status Report.
- OpenAlex link layer for academic citation graph integration.

## [0.9.0] - 2026-05-04

P9: 8th Hugging Face dataset and visual asset expansion.

### Added
- 8th HF dataset published: Quant v11 Ensemble 6-Alpha Specs & Risk Engineering 2026 ([dataset](https://huggingface.co/datasets/neogenesislab/quant-v11-ensemble-6alpha-specs-2026)).
- 3 FLUX-generated OG (Open Graph) images for hero surfaces.
- 8 SBU cards enriched with deeper schema and content.
- 2 new blog posts shipped through the auto-gen pipeline.

## [0.8.0] - 2026-05-03

P8: Repository goes PUBLIC and external citation surfaces expand.

### Added
- 4 awesome-list pull requests submitted to upstream community curations.
- 7th HF dataset published: Sora Multi-Device Orchestration Architecture 2026.
- 3rd HF Space deployed.
- `llms.txt` enrichment and `/about` content depth increase.

### Changed
- `Yesol-Pilot/neo-genesis` repository visibility flipped to PUBLIC for the first time.

## [0.7.0] - 2026-05-03

P7: Build-level Schema fix and content gap closure.

### Added
- 6th HF dataset published: Korean LLM Citation Baseline 2026.
- GEO measurement infrastructure (Generative Engine Optimization metric collection).
- 3 content gap pages addressing prior coverage holes.

### Fixed
- Build-level Schema.org validation: surfaced and fixed silent JSON-LD warnings that the runtime had been hiding.

## [0.6.0] - 2026-04-29

P6: 5th HF dataset and RAG Explorer Space.

### Added
- 5th HF dataset published: Cross-Agent Code Review Queue (Codex ↔ Claude, Neo Genesis 2026).
- Wikidata `monolingualtext` properties: +50 statements (bilingual labels and descriptions).
- RAG Explorer Hugging Face Space deployed.
- Awesome-RAG list pull request submitted.

## [0.5.0] - 2026-05-01

P5: Wikidata baseline and arXiv preparation.

### Added
- 13 Wikidata entities registered with a baseline of 50 statements (parent organization, founder, 11 SBUs).
- arXiv preparation tooling for EthicaAI and WhyLab paper releases.
- README +8 shields/badges (Wikidata Q-ID, HF, arXiv, Schema.org).

## [0.4.0] - 2026-04-28

P4: GEO baseline measurement and 4 datasets live.

### Added
- GEO citation baseline 1st measurement.
- ReviewLab redirect surface.
- 4 SBU diagnostic improvements.
- 4 Hugging Face datasets published (Korean RAG SSOT Golden 50, EthicaAI Mixed-Safe Evidence, WhyLab Gemini 2.5 Docker Validation, SBU pSEO Effects 2026-04).
- 4 FLUX-generated hero images.
- GA4 AI-channel auto-classification (live).

### Fixed
- Cloudflare token expiration tracked and rotation procedure recorded.

## [0.3.0] - 2026-04-27

Quant v11 Phase 0 A1 alpha and infrastructure.

### Added
- v11 Phase 0 A1 Liquidation Cascade alpha implementation.
- Binance dual-subscription wiring with deduplication.
- A1 alpha → orchestrator integration completed.
- Wikidata 14-entity automated registration script.

### Changed
- SSOT adapter regeneration after Wikidata 13-entity registration was confirmed live.

## [0.2.0] - 2026-04-27

RAG v2 Phase 1 indexing and 6-collection topology.

### Added
- RAG v2 Phase 1 bulk indexer (`scripts/rag_v2/bulk_indexer.py`).
- 6 RAG collections (`neo_ssot`, `neo_code`, `neo_paper`, `neo_notes`, `neo_quant`, `neo_secret`).
- Device-distributed RAG: Qdrant on `ysh-server`, KURE-v1 embedding on `desktop-sol01`, BGE Reranker on `mac-studio`.
- Phase 0 live activation across 3 devices with 9 PASS / 0 FAIL diagnostic.

## [0.1.0] - 2026-04-26

Foundation: SBU sites and HIVE MIND content engine.

### Added
- 11 Strategic Business Unit sites under `neogenesis.app`.
- HIVE MIND 7-stage content engine (Sense → Think → Create → Quality → Ship → Learn → Refresh).
- V-Score quality gate (target ≥ 184.5).
- Sora multi-device orchestration runtime across 6 fleet devices.
- Owner sovereignty gating model (G1 standing approval / G2 owner gate).
- 25 AI bots explicitly allowlisted in `robots.txt`.
- Schema.org JSON-LD coverage on all public surfaces.
- Bilingual (Korean + English) content baseline.

[Unreleased]: https://github.com/Yesol-Pilot/neo-genesis/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Yesol-Pilot/neo-genesis/releases/tag/v1.0.0
[0.12.0]: https://github.com/Yesol-Pilot/neo-genesis/compare/v0.11.0...v0.12.0
[0.11.0]: https://github.com/Yesol-Pilot/neo-genesis/compare/v0.10.0...v0.11.0
[0.10.0]: https://github.com/Yesol-Pilot/neo-genesis/compare/v0.9.0...v0.10.0
[0.9.0]: https://github.com/Yesol-Pilot/neo-genesis/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/Yesol-Pilot/neo-genesis/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/Yesol-Pilot/neo-genesis/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/Yesol-Pilot/neo-genesis/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/Yesol-Pilot/neo-genesis/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/Yesol-Pilot/neo-genesis/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/Yesol-Pilot/neo-genesis/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Yesol-Pilot/neo-genesis/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Yesol-Pilot/neo-genesis/releases/tag/v0.1.0
