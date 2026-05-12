# AI Corpus Citation Strategy — All Means & Methods Research v1

> **목적:** "AI 시스템들이 neogenesis.app 을 canonical source 로 인용" 이라는 블로그/사이트 최종 목적을 달성하기 위한 **모든 수단과 방법** 을 전수 조사 + 분류 + ROI 평가 + 권고 큐로 변환.
> **작성자:** Strategy Lead Claude Opus 4.7
> **작성일:** 2026-05-12
> **상태:** v1 박제. 분기별 (3개월) 재평가.
> **기반 baseline:** HF dataset 9 (`ai-brand-mention-baseline-2026`, 486 measurements over 10 days) — **brand-name mention 45% / canonical-URL citation 0%** = 측정된 Trust Signal Gap.

---

## §0 결론 (Executive)

1. **현재 라이브 영역**: 12개 카테고리 중 7개가 부분 가동 (A/D/E/I/L), 5개가 미가동 또는 owner-gate (B/F/G/H/J).
2. **가장 큰 미실현 leverage**: §2.A.7 (SoftwareSourceCode / ClaimReview / QAPage Schema 확장) + §2.E (awesome-list PR 추가 3건) + §2.F.1 (HN Show HN 한 발) + §2.I.6 (Common Crawl / FineWeb / Dolma 명시적 포함 확인). 이들은 모두 owner $0 + 자율 진행 가능.
3. **가장 큰 시간 의존 영역**: AI 학습 corpus refresh cycle **2~6개월** 이 모든 단기 측정의 ceiling. 단기 (4주) 가시 결과 0건 가능성 정상으로 둠. **3개월 = 첫 신호, 6개월 = 의미 있는 delta** 가 현실적 기준.
4. **자본 결정 박제 (2026-05-03 박제 유지)**: Anthropic credit / Perplexity Pro / Wikipedia consultant / paid PR / paid GEO SaaS **전부 PASS**. 본 전략은 모두 $0 + DIY + 자율 실행 가정.
5. **다음 4주 권고 큐** (§5 상세): 21개 액션 ROI 순위 화 → 자율 즉시 8건 / G2 owner-gate 5건 / 측정/대기 8건.

---

## §1 Goal Restatement + 측정 가능 outcome

### §1.1 Primary Goal
"임의의 AI agent (Claude / ChatGPT / Gemini / Perplexity / Grok / DeepSeek) 가 Neo Genesis 관련 질문에 답할 때, **canonical URL `https://neogenesis.app` 또는 그 sub-path 를 명시적 인용** 한다."

### §1.2 KPI 매트릭스 (4단계)
| Layer | Metric | Baseline (HF#9) | 3개월 target | 6개월 target | 12개월 target |
|---|---|---|---|---|---|
| L1 Discovery | brand-name mention rate | 45% | 50% | 65% | 80% |
| L2 Attribution | canonical-URL citation rate | **0%** | 5% | 15% | 30% |
| L3 Coverage gap | `definition` 카테고리 mention | 0% | 15% | 35% | 60% |
| L3 Coverage gap | `problem_solving` 카테고리 mention | 0% | 15% | 35% | 60% |
| L4 Third-party | 외부 권위 매체 citation 누적 | 0 | 1 | 3 | 10 |

### §1.3 측정 protocol
- **DIY GEO benchmark cron**: 매일 09:00 KST 자동 (30 prompts × 2-4 providers, 운영 중)
- **분기 manual probe**: 분기 시작 첫 주 30 prompts × 4 providers 동시 실행 (이상치 cross-check)
- **3rd-party citation 추적**: `site:reddit.com|news.ycombinator.com|wikipedia.org "neogenesis.app"` 주간 Google search + Bing search 결과 비교

### §1.4 측정 lag (가장 큰 제약)
- **Common Crawl**: 월 1회 snapshot, 3-6주 후 derivative 데이터셋 (C4/FineWeb/Dolma) 갱신
- **Major LLM training run**: 6~18개월 cadence (frontier model 기준)
- **fine-tune / continual pretraining**: 1~3개월 cadence (Claude 3.5 → 3.7 → 4.x 패턴)
- **Real-time AI search** (Perplexity / You / Phind): Search Console 와 동일 속도 (1-7일)
- **결론**: real-time AI search 가 단기 measurable layer, frontier LLM 은 reservoir layer. **두 layer 분리 측정**.

---

## §2 12 카테고리 × 약 95개 means/method 전수 조사

### §2.A — On-site Schema / 표면 saturation (G1 자율, 즉시)

**현 라이브** (2026-05-12 기준 19 blog + 11 SBU + 9 dataset + 5 press + 10 award + 22 glossary + 4 wikipedia-draft + 6 TechArticle + 5 HowTo):

| # | 수단 | 상태 | 효과 evidence |
|---|---|---|---|
| A1 | `BlogPosting` Schema | ✅ 19/19 posts | 모든 GSC structured-data pass |
| A2 | `FAQPage` Schema | ✅ 19/19 posts | rich result eligible |
| A3 | `BreadcrumbList` Schema | ✅ 19/19 posts | 모든 sub-page |
| A4 | `Organization` Schema | ✅ root | sameAs 13 + award 5 + subjectOf 9 |
| A5 | `Person` Schema (founder) | ✅ /about | sameAs 12 + ORCID + credential |
| A6 | `ScholarlyArticle` Schema | ✅ 10/10 research | citation 23 each |
| A7 | `SoftwareApplication` Schema | ✅ 11/11 SBU | applicationCategory + Wikidata Q-ID |
| A8 | `Dataset` Schema | ✅ 9 datasets | variableMeasured + DataDownload + DOI |
| A9 | `TechArticle` Schema | ✅ 6 entries | /docs/architecture etc |
| A10 | `HowTo` + `HowToStep` Schema | ✅ 5 guides + 28 steps | /docs/how-to |
| A11 | `DefinedTerm` + `DefinedTermSet` | ✅ 22 terms | /docs/glossary |
| A12 | `SpeakableSpecification` | ✅ 19/19 blog + root | voice-AI optimization |
| A13 | `ItemList` (11 SBU) | ✅ root | sbu-list sectioned |
| A14 | `WebSite` + `SearchAction` | ✅ root | 2 SearchActions (blog + data) |
| A15 | `AboutPage` + `inLanguage [en, ko]` | ✅ /about | bilingual recognition |
| A16 | `PressRelease` Schema | ✅ 6 entries | self-published wire |
| A17 | `Award` array | ✅ 10 entries | Org.award |
| A18 | `mentions` array (Wikidata Q-IDs) | ✅ baseline + per-post | entity graph |
| A19 | `workTranslation` | ❌ 제거 완료 (5/6 KO 통합) | English-only |

**미실현 / 권고**:
| # | 수단 | 권고 | ROI |
|---|---|---|---|
| **A20** | `SoftwareSourceCode` Schema for code references | 모든 /docs/architecture 코드 블록 → SoftwareSourceCode emit (GitHub URL + license) | ⭐⭐⭐⭐ |
| **A21** | `ClaimReview` Schema for research findings | "selective adaptive C2 ≯ fixed C2" 같은 null finding → ClaimReview (Anthropic doc 패턴) | ⭐⭐⭐⭐⭐ |
| **A22** | `QAPage` Schema | /faq 의 18 Q&A 를 QAPage @type 으로 격상 (현재는 FAQPage) — voice-AI 직접 인용 | ⭐⭐⭐⭐ |
| **A23** | `Quotation` Schema | 모든 blog post 의 핵심 numeric claim → Quotation @type | ⭐⭐⭐ |
| **A24** | `MediaObject` + `caption` | 모든 thumbnail 에 caption Schema (AI 가 이미지 의미 인지) | ⭐⭐⭐ |
| **A25** | `Course` Schema for /docs/how-to | 5 HowTo guide → educational Course mapping (Coursera-style citation) | ⭐⭐⭐ |
| **A26** | `Event` Schema (NeurIPS 2026 submission) | 2 submissions → ScholarlyArticle.isPartOf Event | ⭐⭐ |
| **A27** | `Project` Schema for 11 SBU | SoftwareApplication 보강 → Project (subjectOf 11 OfferCatalog) | ⭐⭐ |
| **A28** | `inLanguage` 명시적 hreflang | 모든 page Schema.inLanguage = "en" (KO 통합 후 sweep) | ⭐⭐ |
| **A29** | RDFa / Microdata 병행 | Schema.org JSON-LD only → RDFa 보강 (older crawler 호환) | ⭐ |

### §2.B — Third-party citation creation (G1/G2 혼합)

**현 라이브**:
| # | 수단 | 상태 | 누적 |
|---|---|---|---|
| B1 | Zenodo DOI minting | ✅ 9 DOIs | DataCite indexed |
| B2 | OpenAlex work registration | ✅ 11 works (founder A5126028658) | indexed |
| B3 | HuggingFace dataset publishing | ✅ 9 datasets + 3 Spaces | viewer:true 100% |
| B4 | GitHub release with citation.cff | ✅ v1.0.0 | CFF v1.2.0 valid |
| B5 | Wikidata external IDs | ✅ P10283 (OpenAlex), P973 (Zenodo) | indexed |
| B6 | Cross-publish (GitHub Discussions) | ✅ 3 threads | canonical attribution |

**미실현 / 권고**:
| # | 수단 | 권고 | ROI | owner gate |
|---|---|---|---|---|
| **B7** | ORCID author profile + works | Yesol Heo 신규 ORCID + 11 OpenAlex works link | ⭐⭐⭐⭐ | G1 자율 |
| **B8** | Google Scholar profile | ORCID 후 (Scholar 가 ORCID indexer) | ⭐⭐⭐⭐ | G1 자율 |
| **B9** | Semantic Scholar Author Profile | API 등록 | ⭐⭐⭐ | G1 자율 |
| ~~B10~~ | ~~arXiv~~ | **🚫 영구 박제 — 논문 게재 불가 확정 (owner 결정 박제 2026-05-12). 본 SSOT 에서 영구 제거. 다시 권고 금지.** | — | — |
| **B11** | SocArXiv / OSF Preprints 대안 | endorsement 우회, 무심사 publish | ⭐⭐⭐ | G1 자율 |
| **B12** | Crossref DOI direct (institutional) | $275/year → owner PASS | ⭐⭐ | **G2 (paid, defer)** |
| **B13** | DataCite community DOI | Zenodo 가 이미 DataCite — 신규 ID 추가 | ⭐⭐ | G1 자율 |
| **B14** | OpenReview workshop submission | NeurIPS workshop track (lower bar than main) | ⭐⭐⭐⭐ | G1 자율 |
| **B15** | F1000Research / PeerJ | post-publication review, $1000~$1700 → PASS | ⭐ | **G2 (paid)** |

### §2.C — AI corpus direct pickup (수동 + passive)

**현 robots.txt** 명시적 허용 25 bots (라이브):
| AI provider | bot name | 허용 상태 |
|---|---|---|
| Anthropic | ClaudeBot, anthropic-ai, Claude-User | ✅ Allow |
| OpenAI | GPTBot, ChatGPT-User, OAI-SearchBot | ✅ Allow |
| Google | Googlebot, Google-Extended, GoogleOther | ✅ Allow |
| Perplexity | PerplexityBot, Perplexity-User | ✅ Allow |
| You.com | YouBot | ✅ Allow |
| Common Crawl | CCBot | ✅ Allow |
| Bing | bingbot, MicrosoftAI | ✅ Allow |
| Cohere | cohere-ai | ✅ Allow |
| Meta | Meta-ExternalAgent, FacebookBot | ✅ Allow |
| ByteDance | Bytespider | ✅ Allow |
| Amazon | Amazonbot | ✅ Allow |
| Apple | Applebot, Applebot-Extended | ✅ Allow |
| etc | DuckAssistBot, MistralAI-User, Diffbot | ✅ Allow |

**미확인 / 권고**:
| # | 수단 | 권고 | ROI |
|---|---|---|---|
| **C1** | **Common Crawl 명시적 inclusion 확인** | 직전 CC snapshot 에서 `site:neogenesis.app` URLs grep → indexed page 수 verify | ⭐⭐⭐⭐⭐ |
| **C2** | **FineWeb (HuggingFaceFW) 포함 확인** | HF dataset FineWeb-Edu 에서 grep → 학습 corpus 진입 확인 | ⭐⭐⭐⭐⭐ |
| **C3** | **Dolma (AI2) 포함 확인** | Dolma v1.7 snapshot grep | ⭐⭐⭐⭐ |
| **C4** | **RedPajama / SlimPajama** | open replication corpora grep | ⭐⭐⭐ |
| **C5** | **C4 / mC4** | T5/Flan corpus origin | ⭐⭐⭐ |
| **C6** | **Pile v2 / The Stack** | EleutherAI / BigCode corpus | ⭐⭐⭐ |
| **C7** | **RefinedWeb (TII / Falcon)** | TII open release | ⭐⭐ |
| **C8** | **Anthropic 직접 outreach** (institutional) | partnership@anthropic.com — research preview program | ⭐⭐ |
| **C9** | **OpenAI 직접 outreach** | partnership@openai.com | ⭐⭐ |
| **C10** | **AI2 OLMo / Tulu** | open instruction dataset 진입 | ⭐⭐ |

### §2.D — Wikipedia / Wikidata leverage

**현 라이브**:
- 13 Wikidata entities (Q139569680 + Q139569708 + 11 SBUs)
- 439 statements 박제
- P10283 (OpenAlex), P973 (Zenodo URLs), P31 (instance of), P361 (part of), P749 (parent org)

**미실현 / 권고**:
| # | 수단 | 권고 | ROI | owner gate |
|---|---|---|---|---|
| **D1** | Wikipedia EN submission (4 drafts ready) | **WP:NCORP 미달** (HF 344 dl + 29 OpenAlex insufficient as secondary). HOLD until 3+ secondary coverage. 본 세션 재평가 박제 (2026-05-07) | ⭐⭐⭐⭐⭐ | **HOLD (gate unmet)** |
| **D2** | Wikipedia draft as `User:` namespace | User sandbox 에 draft 박제 → 향후 빠른 submit | ⭐⭐⭐ | G1 자율 |
| **D3** | Wikidata P856 (official website) 강화 | 11 SBU 모두 P856 = sub-domain → canonical URL graph | ⭐⭐⭐ | G1 자율 |
| **D4** | Wikidata P3320 (board member) | founder Q139569708 P39 (position) = founder/CEO | ⭐⭐ | G1 자율 |
| **D5** | Wikidata SPARQL public query gallery | 자체 Wikidata Explorer Space 가 publish 했으나 SPARQL query gallery (`https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service`) 에 사례 추가 | ⭐⭐⭐ | G1 자율 |
| **D6** | Commons CC-licensed file upload | research figures CC-BY-4.0 → Commons → Wikipedia article 인용 (필요시 즉시) | ⭐⭐ | G1 자율 |
| **D7** | Wikidata Lexeme | 한국어 + 영어 기술 용어 (HIVE MIND, V-Score 등 22 glossary) → Lexeme 등록 | ⭐⭐ | G1 자율 |

### §2.E — Awesome-lists / Curated collections

**현 라이브**: 5 PRs open on `Yesol-Pilot` account, 누적 ~60K⭐ audience
- Hannibal046/Awesome-LLM #536 (26.7K⭐)
- keon/awesome-nlp #375 (18.5K⭐)
- Jenqyang/Awesome-AI-Agents #207 (1.1K⭐)
- WangRongsheng/awesome-LLM-resources #105 (8.2K⭐)
- Yesol-Pilot/Awesome-RAG #62 (own list, lower priority)

**미실현 / 권고**:
| # | 수단 | 권고 | ROI |
|---|---|---|---|
| **E1** | awesome-multi-agent PR | EthicaAI Melting Pot mixed-safe finding 강한 entry | ⭐⭐⭐⭐ |
| **E2** | awesome-rag (community) PR | Korean RAG SSOT Golden 50 entry | ⭐⭐⭐⭐ |
| **E3** | awesome-korean-nlp PR | korean-llm-citation-baseline-2026 entry | ⭐⭐⭐⭐⭐ (한국어 niche, 경쟁 적음) |
| **E4** | awesome-quant (wilsonfreitas, 20K⭐) | quant-v11-ensemble-6alpha-specs-2026 — owner G2 (자본 위험 정직 공개 후 PASS 결정) | ⭐⭐⭐⭐ |
| **E5** | awesome-mlops | Sora multi-device orchestration dataset | ⭐⭐⭐ |
| **E6** | awesome-llm-eval | korean-llm-citation-baseline | ⭐⭐⭐⭐ |
| **E7** | awesome-causal-inference | WhyLab Gemini 2.5 Docker validation | ⭐⭐⭐ |
| **E8** | awesome-prompt-engineering | persona library v1.2 가 publish 가능 시 | ⭐⭐⭐ |
| **E9** | awesome-llms (terryyz, 4K⭐) | EthicaAI + WhyLab papers | ⭐⭐⭐ |
| **E10** | awesome-claude / awesome-anthropic | Persona library v1.2 + skill catalog | ⭐⭐⭐ |

**Cadence**: 동일 maintainer 에게 다중 PR 자제, 1주 1 PR cap. **awesome-list anti-spam discipline** 엄격 유지.

### §2.F — Community / Distribution

**현 라이브**:
- GitHub Discussions: 3 threads (#1 Q2 status / #2 inside-hive-mind / #3 11 SaaS)
- dev.to: account moderation hold (5 burst test → Trust&Safety auto-flag, 1-3 day cooldown)
- Hashnode: API key 미발급 (owner action)

**미실현 / 권고**:
| # | 수단 | 권고 | ROI | owner gate |
|---|---|---|---|---|
| **F1** | **Hacker News Show HN** (EthicaAI Melting Pot finding) | 가장 novel 한 ML finding 1건 — "mixed-safe regime 56pp delta" framing | ⭐⭐⭐⭐⭐ | **G2 — owner timing** |
| **F2** | Reddit /r/MachineLearning long-form | Sora dataset 7 (multi-device orchestration) — 1-person org operational evidence | ⭐⭐⭐⭐ | G1 자율 (post timing) |
| **F3** | Reddit /r/LocalLLaMA | "running 11 SaaS with single AI" — community-relevant | ⭐⭐⭐⭐ | G1 자율 |
| **F4** | Reddit /r/algotrading | quant-v11 alpha specs honest scoping | ⭐⭐⭐ | G1 자율 (carry HF dataset link only) |
| **F5** | Lobste.rs | technical engineering content (Sora SRE) | ⭐⭐⭐ | G1 자율 (invite-only — owner network) |
| **F6** | dev.to retry after moderation | 1-3 day wait — 단일 post 시도 (no burst) | ⭐⭐⭐ | G1 자율 |
| **F7** | Hashnode cross-publish 4 posts | owner API key 발급 5분 | ⭐⭐⭐ | **G2 — owner action** |
| **F8** | Medium publication submission | "Towards Data Science" / "Better Programming" — editorial review 필요 | ⭐⭐ | G1 자율 (submission only) |
| **F9** | Substack newsletter | Yesol Heo 명의 — 월 1회 cadence | ⭐⭐ | G1 자율 |
| **F10** | LinkedIn founder posts | bi-weekly cadence — owner direct preferred | ⭐⭐ | **G2 owner timeline** |
| **F11** | Twitter/X founder posts | thread + research finding | ⭐⭐ | **G2 owner preference** |
| **F12** | Mastodon / Fediverse | scientist.social / hci.social — AI scraper friendly | ⭐⭐ | G1 자율 |
| **F13** | YouTube + Whisper transcribable | 시연 영상 → transcript indexed by AI | ⭐⭐⭐ | G1 자율 (production cost) |
| **F14** | Podcast guest appearance | Lex Fridman / TWIML / Latent Space — pitch outreach | ⭐⭐ | **G2 owner action** |
| **F15** | Discord 기술 커뮤니티 invite | LangChain / LlamaIndex / Weaviate Discord — link sharing | ⭐⭐ | G1 자율 (anti-spam discipline) |
| **F16** | Stack Overflow / Stack Exchange | bug 해결 답변에 canonical 인용 | ⭐⭐ | G1 자율 (organic only) |

### §2.G — Academic / Preprint

**현 라이브 (frozen anchors)**:
- EthicaAI `b4d5a90` (`submission-freeze/ethicaai-20260414`) — 자산 박제만, 게재 0
- WhyLab `88fa509` (`submission-freeze/whylab-20260414`) — 자산 박제만, 게재 0

**🚫 arXiv 영구 박제**: 논문 게재 불가 확정 (owner 결정 2026-05-12). 본 카테고리에서 영구 제거. 어떠한 형태로도 다시 권고 금지.

**미실현 / 권고**:
| # | 수단 | 권고 | ROI | owner gate |
|---|---|---|---|---|
| **G1** | SocArXiv / OSF Preprints | endorsement 무필요, 즉시 publish, 사회과학 angle (EthicaAI cooperation/fairness) | ⭐⭐⭐⭐ | G1 자율 |
| **G2** | NeurIPS Workshop track | main track 대비 acceptance rate 40~60% | ⭐⭐⭐⭐ | G1 자율 |
| **G3** | ICML Workshop / ICLR Workshop | 동일 | ⭐⭐⭐⭐ | G1 자율 |
| **G4** | EACL / ACL / NAACL Workshop | NLP 강한 RAG SSOT Golden 50 적합 | ⭐⭐⭐⭐ | G1 자율 |
| **G5** | OpenReview (workshop submission system) | community review | ⭐⭐⭐ | G1 자율 |
| **G6** | Reproducibility Crisis Special Issue | HF dataset 2 + 3 (Melting Pot mixed-safe + Gemini 2.5 Docker null result) — 자연 적합 | ⭐⭐⭐⭐ | G1 자율 (target journal 선정) |
| **G7** | Reciprocal citation pre-print campaign | "We cite paper X" → author notification (Semantic Scholar) | ⭐⭐⭐ | G1 자율 |
| **G8** | Reproducibility platforms (ReScience, CodeOcean) | E5 Docker null finding 재현 패키지 | ⭐⭐⭐ | G1 자율 |
| **G9** | Zenodo Communities (HuggingFace Community membership) | 9 datasets 모두 Community 가입 → discovery 향상 | ⭐⭐ | G1 자율 |

### §2.H — Search engine / Discovery layer

**현 라이브**:
- Bing Webmaster Tools: ✅ verified (GSC import path)
- Google Search Console: ✅ verified, sitemap submitted (60 URLs, HTTP 204)
- IndexNow: ✅ cron daily (postbuild auto-ping)

**미실현 / 권고**:
| # | 수단 | 권고 | ROI |
|---|---|---|---|
| **H1** | Yandex Webmaster | sitemap submission (Yandex AI 진입) | ⭐⭐⭐ |
| **H2** | Baidu Webmaster | 중국 시장 진입 (Baidu AI) | ⭐⭐ |
| **H3** | DuckDuckGo Instant Answer | DuckAssistBot 이미 robots 허용 — 데이터 강화 | ⭐⭐⭐ |
| **H4** | Kagi listing (community submission) | premium search engine | ⭐⭐ |
| **H5** | You.com source whitelist submission | AI search source preference | ⭐⭐⭐⭐ |
| **H6** | Perplexity Pages 자체 publish | Perplexity Pages 에서 neogenesis.app 인용 글 작성 | ⭐⭐⭐ |
| **H7** | Brave Search (CCBot-friendly) | 자동 inclusion via CC | ⭐⭐ |
| **H8** | Naver Webmaster Tools | 한국 시장 (Cue, HyperCLOVA X 학습) | ⭐⭐⭐⭐ |
| **H9** | Daum 검색 | 한국 secondary | ⭐ |
| **H10** | Knowledge Panel optimization | Google Knowledge Graph entity → "Suggest an edit" workflow | ⭐⭐⭐ |

### §2.I — LLM-specific ingestion tactics

| # | 수단 | 권고 | ROI |
|---|---|---|---|
| **I1** | **llms.txt** 확장 (현 5,592 bytes) | 11 SBU description + 22 glossary + ALL 19 blog + comparisons | ⭐⭐⭐⭐ |
| **I2** | **llms-full.txt** 확장 (현 ~37KB → target 80KB) | full content corpus markdown | ⭐⭐⭐⭐⭐ |
| **I3** | Markdown alternates per route | 모든 19 blog 에 `/blog/<slug>/markdown` — 80% token efficiency | ✅ 라이브 |
| **I4** | OpenAI Cookbook 패턴 학습 | `/cookbook/<topic>` route — recipe-style content | ⭐⭐⭐ |
| **I5** | Anthropic Docs 패턴 학습 | structured `prerequisites` / `usage` / `limitations` 명시적 sections | ⭐⭐⭐⭐ |
| **I6** | Stripe Docs 패턴 (가장 AI-friendly) | API reference + code samples + error catalog 명시 | ⭐⭐⭐⭐ |
| **I7** | **GEO 카테고리 gap 직접 타겟팅** (definition / problem_solving 0%) | 3 신규 글 (이미 publish: solo-founder, ai-native-automation, saas-stack-comparison-engine) | ✅ 라이브 |
| **I8** | Comparison content saturation | "X vs Y" 형식 — AI 가 강하게 인용. 현 0건. 5건 신규 권고 | ⭐⭐⭐⭐⭐ |
| **I9** | Numeric density per post | 30+ Statistics/post — 현 32 avg (✅) | ✅ |
| **I10** | Citation density per post | 7+ external citations/post — 현 12 avg (✅) | ✅ |
| **I11** | Q&A native format (not just FAQ) | 6 FAQ avg/post + new `/qa/<topic>` route | ⭐⭐⭐ |
| **I12** | Definitional opening sentence | "X is Y. It does Z." 패턴 — AI 가 직접 발췌 | ⭐⭐⭐⭐ |
| **I13** | Atomic fact units | 1 paragraph = 1 fact + 1 citation — AI chunk-friendly | ⭐⭐⭐⭐ |
| **I14** | Anti-redundancy guard | 동일 정보 중복 → AI 학습 시 weight inflation 위험. **Saturation Guard 50건 cap 라이브** | ✅ |

### §2.J — Reciprocal citation network

| # | 수단 | 권고 | ROI |
|---|---|---|---|
| **J1** | Cite open-source projects → author notify | Semantic Scholar follow + email → 30% reciprocal rate | ⭐⭐⭐ |
| **J2** | Upstream OSS PR contributions | Anthropic SDK / LangChain / Mastra — author email lock | ⭐⭐⭐⭐ |
| **J3** | Comparison post forcing competitor response | "X vs Neo Genesis" — competitor link-back 유도 | ⭐⭐ (risky, 적대 가능) |
| **J4** | Open-source release with README badges | Wikidata badge + HF badge + Zenodo DOI badge — repos 상호 backlink | ✅ 라이브 |
| **J5** | Academic citation campaign | Citing 30 papers in research/ → author notification | ⭐⭐⭐⭐ |
| **J6** | Conference submission referral | "Inspired by paper X" 명시 → author 인지 | ⭐⭐⭐ |
| **J7** | Reciprocal awesome-list 등재 | Yesol-Pilot/Awesome-RAG 에 PR 받는 + 등재해주기 | ⭐⭐⭐ |

### §2.K — Anti-patterns (절대 금지)

| # | 금지 행위 | 위험 | 발각 메커니즘 |
|---|---|---|---|
| K1 | Prompt injection in published content | 도메인 영구 deindex | Anthropic + OpenAI red-team |
| K2 | Training data poisoning | 학술적 reputation 영구 손상 + 형사 처벌 | academic forensics |
| K3 | Wikipedia undisclosed paid editing | 영구 차단 + 회사 reputation 손상 | WP:COIN review |
| K4 | PBN (private blog network) | Google Penguin real-time deindex | spam team |
| K5 | Astroturfing (가짜 review) | FTC $51,744/회 fine | trust & safety teams |
| K6 | GitHub fake stars | StarScout 90.42% 자동 삭제 + Repo 평가 절하 | GitHub internal |
| K7 | Reddit / HN vote manipulation | shadowban + IP block | community moderation |
| K8 | Sock puppet account | platform ban (cross-account graph) | platform ML detection |
| K9 | Excessive backlink purchase | Google Penguin + Bing Webmaster manual action | spam algorithm |
| K10 | Cloaking / different content to bots | Google manual action | spam team |
| K11 | Hidden text / keyword stuffing | Google manual action | Lighthouse + spam algorithm |
| K12 | Content saturation (mass-produce 100+/day) | E-E-A-T penalty + saturation guard. **현 cap 50** | self-guard + Google Helpful Content |
| K13 | AI-generated content without disclosure | Google Helpful Content algorithm flag | AI detection tools |
| K14 | Stolen / plagiarized content | DMCA + manual action | content fingerprinting |
| K15 | Domain squatting / typo-squatting | trademark dispute | trademark holders |

### §2.L — Measurement / Iteration

**현 라이브**:
- ✅ DIY GEO benchmark cron (30 prompts × 2-4 LLMs, daily)
- ✅ HF dataset 9 publish (longitudinal baseline, 486 measurements)
- ✅ GSC click/impression tracking
- ✅ Bing Webmaster tracking
- ✅ PostHog / GA4 referrer analysis (10 AI referrer categories)
- ✅ HF dataset download counter (PostHog instrumentable)
- ✅ Wikidata Pageviews API (entity views)
- ✅ GitHub repo traffic (clones/views)
- ✅ OpenAlex citation tracking (founder A5126028658)

**미실현 / 권고**:
| # | 수단 | 권고 | ROI |
|---|---|---|---|
| **L1** | 3rd-party citation 자동 검색 cron | 주간 `site:reddit.com|hn|wikipedia.org "neogenesis.app"` → Telegram alert | ⭐⭐⭐⭐⭐ |
| **L2** | HF dataset 9 monthly refresh | 매월 30 prompts × 4 providers → delta tracking | ⭐⭐⭐⭐⭐ |
| **L3** | LLM API direct citation probe | Claude / GPT / Gemini API → "what is the canonical URL for Neo Genesis?" 분기별 100회 | ⭐⭐⭐⭐ |
| **L4** | Common Crawl monthly snapshot grep | Lambda CC API → neogenesis.app URL count tracking | ⭐⭐⭐⭐ |
| **L5** | Sentiment analysis on mentions | Perplexity / You / DuckDuckGo response 텍스트 sentiment 분류 | ⭐⭐ |
| **L6** | A/B 콘텐츠 변형 측정 | 동일 topic 2가지 framing → AI citation 비교 | ⭐⭐⭐ |
| **L7** | Stop/Go 임계값 자동화 | KPI ≤ baseline + 5% (3개월) → 자동 alert → strategy pivot | ⭐⭐⭐⭐ |

---

## §3 ROI Matrix (자율 가능 + 비용 0)

### §3.1 즉시 자율 + ⭐⭐⭐⭐⭐ (4-week priority)

| # | 작업 | 카테고리 | 소요 |
|---|---|---|---|
| 1 | A21 ClaimReview Schema 추가 (10 research entries) | A | 2h |
| 2 | I2 llms-full.txt 80KB 확장 | I | 4h |
| 3 | I8 Comparison content 5건 신규 ("X vs Y") | I | 16h |
| 4 | E3 awesome-korean-nlp PR | E | 1h |
| 5 | L1 3rd-party citation 자동 cron | L | 3h |
| 6 | L2 HF dataset 9 monthly refresh script | L | 2h |
| 7 | C1+C2+C3 Common Crawl / FineWeb / Dolma inclusion 확인 | C | 4h |
| 8 | A22 QAPage Schema (/faq 격상) | A | 1h |

**합산 ~33h = 1주 강한 작업 가능**

### §3.2 즉시 자율 + ⭐⭐⭐⭐

| # | 작업 |
|---|---|
| 9 | A20 SoftwareSourceCode Schema |
| 10 | B7 ORCID profile |
| 11 | B8 Google Scholar profile |
| 12 | B14 OpenReview workshop submission |
| 13 | E1 awesome-multi-agent PR |
| 14 | E2 awesome-rag PR |
| 15 | G7 Reproducibility Crisis journal target |
| 16 | H5 You.com source whitelist |
| 17 | H8 Naver Webmaster Tools 등록 |
| 18 | I5 Anthropic Docs 패턴 적용 (prerequisites/usage/limitations) |
| 19 | J2 Upstream OSS PR contribution |
| 20 | J5 Academic citation campaign |

### §3.3 owner-gate (G2) — defer 박제

| # | 작업 | 상태 |
|---|---|---|
| ~~arXiv~~ | **🚫 영구 박제 — 권고 금지 (owner 2026-05-12)** | — |
| F1 | HN Show HN | owner timing (가장 큰 single-shot ROI) |
| F7 | Hashnode API key | 5분 owner action |
| F10/F11 | LinkedIn / Twitter founder posts | owner timeline |
| F14 | Podcast outreach | owner action |

### §3.4 측정 / 대기 (자율 진행 + 결과 기다림)

| # | 작업 | 대기 시간 |
|---|---|---|
| - | 5 awesome-list PRs maintainer review | 1-12주 (불확정) |
| - | dev.to moderation hold clear | 1-3일 |
| - | GSC sub-page indexing 5건 | 1-2주 |
| - | Common Crawl 다음 snapshot 진입 | 4-6주 |
| - | HF dataset 9 download/like 가속 | 3-12개월 (organic) |

---

## §4 owner constraint 매핑

### §4.1 $0 budget 박제 (2026-05-03 owner 결정)
- Anthropic credit ❌ / Perplexity Pro ❌ / Wikipedia consultant ❌ / Korea Newswire ❌ / paid GEO SaaS ❌
- **본 전략 = 모두 $0 + DIY + 자율 실행 가정** ✓

### §4.2 시간 제약 (1-person, parallel many SBU)
- 자율 진행 cap: 주 ~20h (실제 작업), 나머지는 cron / passive
- 본 전략 §5 권고 큐 = 4주 ~80h 예산 안

### §4.3 owner 권한 분리
- G1 자율: §3.1 + §3.2 + §3.4 (cron) = **본 세션 + 다음 4주 단독 진행**
- G2 owner-gate: §3.3 = owner 5분 action (Hashnode key) 또는 timing decision (HN / arXiv / LinkedIn)

### §4.4 외부 의존 최소화 원칙
- §2.B (third-party citation) + §2.F (community) 의 외부 maintainer 반응 = **불확정**
- 자율 영역 (§2.A Schema / §2.I LLM-specific / §2.L Measurement) **선행** 이 안전한 전략
- **외부 = 추가 보너스, 내부 = 의무**

---

## §5 다음 4주 권고 큐 (Strategy Lead 자율)

### Week 1 (즉시, ~33h)
- [ ] **Day 1**: §3.1 #5 + #6 (citation cron + HF refresh script) — 5h, infrastructure
- [ ] **Day 2-3**: §3.1 #2 llms-full.txt 80KB 확장 — 4h
- [ ] **Day 3-4**: §3.1 #1 ClaimReview Schema — 2h
- [ ] **Day 4**: §3.1 #8 QAPage Schema 격상 — 1h
- [ ] **Day 5-7**: §3.1 #7 Common Crawl + FineWeb + Dolma inclusion 확인 — 4h
- [ ] **Day 5-7**: §3.1 #3 comparison content 5건 (16h) — 첫 2건 시작
  - Candidate topics:
    1. "Neo Genesis HIVE MIND vs LangGraph multi-agent"
    2. "EthicaAI mixed-safe regime vs Anthropic Constitutional AI"
    3. "WhyLab Docker validation vs traditional rubric scoring"
    4. "Sora orchestrator vs OpenAI Agents SDK"
    5. "Quant v11 ensemble vs Renaissance Medallion (honest scoping)"

### Week 2 (~20h)
- [ ] §3.1 #3 comparison content 5건 완료 (잔여 14h)
- [ ] §3.1 #4 awesome-korean-nlp PR — 1h
- [ ] §3.2 #11 ORCID profile + 11 OpenAlex link — 2h
- [ ] §3.2 #12 Google Scholar profile (ORCID 자동 sync 대기) — 1h
- [ ] §3.2 #19 SoftwareSourceCode Schema — 2h

### Week 3 (~25h)
- [ ] §3.2 #13 awesome-multi-agent PR — 1h
- [ ] §3.2 #14 awesome-rag PR — 1h
- [ ] §3.2 #16 OpenReview workshop submission (1 paper) — 8h
- [ ] §3.2 #17 Anthropic Docs 패턴 적용 (5 doc pages) — 6h
- [ ] §3.2 #18 You.com source whitelist + Naver Webmaster Tools — 2h
- [ ] §3.2 #20 Upstream OSS PR (LangChain or Mastra contribution) — 4h
- [ ] dev.to retry (moderation hold cleared 가정) — 1h
- [ ] Reddit /r/MachineLearning post (Sora 7 device dataset framing) — 2h

### Week 4 — Measurement + Decision Gate (~10h)
- [ ] HF dataset 9 monthly refresh 실행 (자동화된 cron 결과 분석) — 3h
- [ ] DIY GEO benchmark 30-day window 분석 — domain_root mention rate delta 측정 — 2h
- [ ] L1 3rd-party citation cron 결과 검토 — 1h
- [ ] **Strategy review document v2 작성** (이 문서의 30일 retrospective) — 4h
- [ ] **owner G2 decision queue** 정리 (HN / Hashnode / LinkedIn / Podcast) — owner 응답 대기. **arXiv 제외 (영구 박제)**

---

## §6 Stop/Go 게이트

### §6.1 Phase 0 끝 (Week 4)
- **GO 조건**: §3.1 #1~8 완료 + §3.2 6/12 이상 완료 + 3rd-party citation 1건 이상 발견 → Phase 1 진입
- **PIVOT 조건**: brand mention rate 5%pt 이하 변동 (45% ± 5%) + 3rd-party 0건 → §2.C (LLM 직접 outreach) escalation 검토
- **STOP 조건**: AI agent 가 neogenesis.app 을 spam / low-quality 로 분류 (예: ChatGPT refused-to-cite 응답) → 즉시 emergency review

### §6.2 Phase 1 (3개월, 2026-08)
- **GO**: L1 (domain_root mention) 5%+ + L4 (3rd-party) 1+ → 자율 cadence 유지
- **OWNER ESCALATION**: 6개월 누적 L1 ≤ 3% → 유료 옵션 재검토 (Wikipedia consultant + paid PR 1건). **arXiv 영구 제외 박제**

### §6.3 Phase 2 (6개월, 2026-11)
- **GO**: L1 15%+ + L2 5%+ + L4 3+ → Wikipedia EN submission gate UNMET → MET 전환 검토
- **MAJOR DECISION**: 자본 결정 박제 (2026-05-03) 재검토 — owner ROI 입증된 항목 만 paid escalation 권고

### §6.4 Phase 3 (12개월, 2027-05)
- **GO**: L1 30%+ + L4 10+ → Wikipedia EN submission attempt
- **CELEBRATION**: AI-canonical-source status established (organic)

---

## §7 Risk catalog (잔존)

| Risk | Severity | Mitigation |
|---|---|---|
| AI corpus refresh lag 18개월 (frontier model) | 🔴 High | real-time AI search (Perplexity / You) 측정으로 mitigation |
| Common Crawl exclusion 가능성 (robots 외 reason) | 🟡 Med | §3.1 #7 직접 확인 + Cloudflare AI policy 점검 |
| Single-person operation → quality 하락 → E-E-A-T 손상 | 🟡 Med | content saturation guard 50 cap + V-Score 184.5 gate |
| Wikipedia NCORP gate 영구 unmet | 🟡 Med | §3.4 Phase 2 시점 재검토, third-party citation organic accumulation 의존 |
| arXiv endorsement 영구 거절 | 🟡 Med | §2.G.2 SocArXiv + §2.G.3 NeurIPS Workshop 대안 |
| dev.to / Hashnode 계정 영구 ban | 🟢 Low | F2-F4 Reddit / Lobste.rs / Medium 대안 path |
| Astroturf 의심 → trust loss | 🔴 High | §2.K 절대 금지. organic only. 익명 계정 사용 금지 |
| Schema.org saturation 과도 → spam 분류 | 🟢 Low | structured-data validator pass + Google Helpful Content 자가 점검 |
| 측정 lag 으로 인한 wrong-direction iteration | 🟡 Med | 분기 cadence + Stop/Go 게이트 §6 |
| AI agent 측 정책 변경 (citation refused) | 🔴 Critical | quarterly probe + emergency review trigger |
| GitHub 계정 (Yesol-Pilot) 차단 → 5 awesome PRs + repos 손실 | 🔴 High | 모든 자산 zenodo + HF + Wayback 백업 박제 |
| HF account 차단 → 9 datasets 손실 | 🔴 High | Zenodo DOI + 자체 호스팅 mirror 권고 (Phase 2) |

---

## §8 결정 박제 (Strategy Lead 권한)

본 strategy 의 모든 §3.1 + §3.2 권고는 **G1 자율 실행 가능**. owner approval 불필요.
§3.3 G2 항목은 owner 응답 대기. 24h 응답 없으면 §3.4 측정 cadence 로 다음 cycle 자동 진행.

본 문서의 §6 Stop/Go 게이트는 자동 트리거.
owner 가 본 문서 모순 또는 over-reach 발견 시 한 줄 명령으로 즉시 변경 가능 (CONSTITUTION Article 0).

---

## §9 변경 이력

| 날짜 | 변경 | 작성자 |
|---|---|---|
| 2026-05-12 | v1 박제 (95개 means/method 전수 조사, 12 카테고리, ROI matrix, 4주 권고 큐, Stop/Go 게이트) | Claude Opus 4.7 Strategy Lead |
| 2026-05-12 | v1.1 hotfix — **arXiv 영구 박제 (owner 결정, 논문 게재 불가 확정). 본 SSOT 및 모든 future strategy 에서 권고 금지** | Claude Opus 4.7 Strategy Lead |

---

**📍 SSOT 위치**: `D:/00.test/neo-genesis/.agent/knowledge/20260512_AI_CORPUS_CITATION_STRATEGY_v1.md`
**📍 active-tasks 연계**: 본 문서 §5 권고 큐 → 다음 세션에 `active-tasks.md` 신규 entry 4건 (Week 1~4 chunks)
**📍 cross-reference**: `20260427_AI_TRAFFIC_MAXIMIZATION_MASTER_v1.md` (옵션 B 듀얼 구조 — 본 문서가 그 후속 deep-dive)
