# Neo Genesis Business Ontology — DESIGN v0.1

> **Status**: DRAFT (2026-05-14, Strategy Lead Claude Opus 4.7)
> **Companion**: `.agent/ontology/DESIGN_v0.1.md` (meta-ontology, agent runtime)
> **Scope**: Neo Genesis 본질 — 1인 founder + AI multi-agent → 12 product portfolio → 잠재 매출
> **NOT scope**: owner 의 다른 context (CTS-AI 직원 / JD 구직 / 가족·법무·금융)
> **G1-32 박제**: business ontology 분리 신설. meta 와 인프라 공유, namespace 분리

---

## §1. 포지셔닝 (meta 와의 관계)

```
┌─────────────────────────────────────────────────┐
│  Meta-ontology (v0.5, neo://artifact/agent/...)│   agent runtime audit
│  답하는 것: "누가 무엇을 언제 했나"             │   AI ops 자기 박제
└──────────────┬──────────────────────────────────┘
               │ 공유: JSONL + AuraDB + tools + cron
               │ cross-link: shared URIs
┌──────────────▼──────────────────────────────────┐
│  Business ontology (v0.1, neo://biz/...)       │   Neo Genesis 본질
│  답하는 것: "어떤 product 가 어떤 매출 path 로  │   실 비즈니스 의사결정
│   어디까지 성장 가능한가"                       │
└─────────────────────────────────────────────────┘
```

**Meta 와 Biz 의 본질적 차이**:

| 측면 | Meta-ontology | Business ontology |
|---|---|---|
| 주체 | Agent / Action / Artifact | Founder / Product / Strategy |
| 시간 척도 | second ~ day (ActionRun) | week ~ year (RevenueStream) |
| 답변 가치 | "이 commit 누가 했나" | "이 SBU 가 D-27 안에 launch 가능한가" |
| owner 사용 | indirect (agent 가 자기 audit) | direct (매일 의사결정 도움) |

---

## §2. Scope

### In-scope
- **Founder**: 허예솔 (1 entity, only natural person)
- **Product**: 12 SBU + 2-3 논문 + 1 게임 + heoyesol.kr 브랜드 (~16)
- **Domain**: 사업자 등록 명의 도메인 (~15)
- **Strategy**: Revenue Path Research v1 의 13 path framework
- **RevenueStream**: 매출 source (B1~D3)
- **Investment**: 자본 배분 (D2 ETF / D1 예금)
- **ResearchIP**: KoreanLLM AO-1 / EthicaAI / WhyLab manuscript
- **Lead**: 잠재 고객 (koreanllm.org B2B target / B3 consulting potential)
- **KPI**: per Product metric (MAU / ARR / retention)
- **Decision**: G1/G2 박제 (Strategy Lead 박제)
- **ExternalFederation**: Cloudflare / Vercel / Supabase / AuraDB / GA4 — 운영 의존

### Out-of-scope (별도 ontology 또는 ontology 외)
- **CTS-AI Engagement**: owner = CTS 직원. employer 도메인, Neo Genesis 아님
- **JD Application**: owner = 구직자. Neo Genesis 운영 시간 vs 구직 시간 trade-off
- **9 master resume PDF**: owner career asset (Neo Genesis founder 가 가진 personal asset 으로 reference 가능, 자산은 아님)
- **가족 / 법무 / 금융 / 개인회생**: 절대 외 (CLAUDE.md §1.4)
- **CTS 11 클라이언트 정보**: employer 의 고객, Neo Genesis 와 무관

---

## §3. Object Model (19 classes — v0.1 final 라이브)

**v0.1 첫 라이브 (10 classes)**: Founder / Product / Domain / Strategy / RevenueStream / Investment / ResearchIP / Lead / KPI / Decision.

**v0.1 추가 P0 batch 1 (4 classes)**: Capability / ExternalFederation / TemporalEvent / MonthlyCost.

**v0.1 추가 P0 batch 2 (5 classes)**: Workflow / ContentCorpus / BrandAsset / Risk / AgentContribution. → AI-native operating company 의 본질 layer (운영 절차 / IP corpus / 정체성 / 컴플라이언스 / 협업 측정).

**Active surfacing engine**: `scripts/ontology/business/daily_digest.py` — 매일 ontology state 분석 → owner attention 자동 박제 (URGENT 시점 / RISK / BURN / CAPABILITY GAP / PRODUCT 전환 / DECISION VELOCITY / AGENT LOAD). 단순 record 가 아니라 **decision-surfacing**.



공통: `id`, `rdf_type`, `label`, `created_at`, `updated_at`. 모든 비즈니스 객체는 `domain: "biz"` 마킹.

### 3.1 `biz:Founder`

| 속성 | type | required | 정의 |
|---|---|---|---|
| `id` | URI | ✅ | `neo://biz/founder/yesol-heo` (영구 불변) |
| `name` | string | ✅ | 한국명 + 영문명 alias |
| `business_registration` | string | optional | 사업자등록번호 partial (영구 redact, full 은 personal-forbidden) |
| `role` | string[] | ✅ | `["founder", "strategy_lead", "developer"]` |
| `capabilities` | string[] | optional | broad domain (PM/PO/AI/quant 등 — career profile 참조) |

**NOT 정의**: Founder 의 CTS-AI 직원 역할은 별도 ontology 또는 외. 본 ontology 의 founder = Neo Genesis 대표 role.

### 3.2 `biz:Product`
12 SBU + papers + game + brand.

| 속성 | type | required | 정의 |
|---|---|---|---|
| `id` | URI | ✅ | `neo://biz/product/<slug>` (kott / toolpick / etc.) |
| `kind` | enum | ✅ | `sbu_saas / sbu_blog / paper / game / brand_site` |
| `stage` | enum | ✅ | `idea / mvp / live / paused / archived` |
| `domains` | URI[] | optional | `neo://biz/domain/...` |
| `meta_project` | URI | optional | cross-link → `neo://project/<slug>` (meta) |
| `north_star_kpi` | URI | optional | `neo://biz/kpi/...` |
| `revenue_path` | URI | optional | `neo://biz/revenue_stream/...` (어떤 path 로 매출 발생) |
| `launched_at` | ISO8601 | optional | |

### 3.3 `biz:Domain`
사업자 등록 명의 도메인.

| 속성 | type | required | 정의 |
|---|---|---|---|
| `id` | URI | ✅ | `neo://biz/domain/<host>` (kott.kr / toolpick.dev / ...) |
| `host` | string | ✅ | |
| `registrar` | string | optional | Cloudflare / Namecheap 등 |
| `expires_at` | ISO8601 | optional | |
| `owned_by_business` | bool | ✅ | true = 사업자 명의 (Neo Genesis) |

### 3.4 `biz:Strategy`
Strategic framework 박제 (Revenue Path Research 등).

| 속성 | type | required | 정의 |
|---|---|---|---|
| `id` | URI | ✅ | `neo://biz/strategy/<slug>` (e.g. `revenue-path-v1`) |
| `source_artifact` | URI | ✅ | meta `neo://artifact/...` (실 문서) |
| `framework_type` | string | ✅ | `revenue_path / growth_loop / capital_allocation / pricing` |
| `effective_from` | ISO8601 | ✅ | 박제 시점 |
| `effective_until` | ISO8601 | optional | superseded 시점 (open-ended = 활성) |

### 3.5 `biz:RevenueStream`
매출 source.

| 속성 | type | required | 정의 |
|---|---|---|---|
| `id` | URI | ✅ | `neo://biz/revenue_stream/<slug>` (e.g. `b1-sbu-acceleration`, `d2-etf`, `c2-info-product`) |
| `path_id` | string | ✅ | Revenue Path Research v1 분류 (A1~D3) |
| `category` | enum | ✅ | `quant / saas / paper / consulting / info_product / affiliate / index_fund / dividend / real_estate / personal_brand` |
| `expected_monthly_revenue` | string | optional | range (e.g. `"0~500만"` 또는 `"1500만~5억 누적"`) |
| `status` | enum | ✅ | `recommended / active / pilot / deferred / rejected / closed` |
| `decision_log` | URI[] | optional | `neo://biz/decision/...` (왜 선택/거부) |

### 3.6 `biz:Investment`
자본 배분.

| 속성 | type | required | 정의 |
|---|---|---|---|
| `id` | URI | ✅ | `neo://biz/investment/<slug>` |
| `kind` | enum | ✅ | `etf / deposit / cash / sbu_ad_budget / paper_compute / equipment` |
| `target_share_pct` | float | optional | 자본 중 % (e.g. D2 = 40~60%) |
| `current_balance_status` | enum | optional | `planned / partial / fully_allocated` |
| `rationale_artifact` | URI | optional | meta `neo://artifact/...` (Revenue Path 박제) |

### 3.7 `biz:ResearchIP`
Neo Genesis 가 보유한 IP / 연구 산출물.

| 속성 | type | required | 정의 |
|---|---|---|---|
| `id` | URI | ✅ | `neo://biz/research_ip/<slug>` |
| `kind` | enum | ✅ | `paper_manuscript / dataset / model / leaderboard / corpus / methodology` |
| `status` | enum | ✅ | `wip / submitted / blind_review / accepted / published / deferred` |
| `total_word_count` | int | optional | 추정 (e.g. KoreanLLM 287K) |
| `meta_artifact_root` | URI | optional | meta `neo://artifact/...` (manuscript root) |
| `venue` | string | optional | NeurIPS / ICML / arXiv / etc. |

### 3.8 `biz:Lead`
잠재 고객 (paying customer 후보).

| 속성 | type | required | 정의 |
|---|---|---|---|
| `id` | URI | ✅ | `neo://biz/lead/<slug>` |
| `lead_type` | enum | ✅ | `b2b_enterprise / academic_partner / individual_buyer / affiliate_user / consulting_client` |
| `target_revenue_stream` | URI | ✅ | `neo://biz/revenue_stream/...` |
| `engagement_stage` | enum | ✅ | `prospect / contacted / negotiating / converted / lost` |
| `target_product` | URI | optional | `neo://biz/product/...` |
| `expected_value_usd` | string | optional | range (e.g. "$30K~$80K") |

### 3.9 `biz:KPI`
Per Product metric.

| 속성 | type | required | 정의 |
|---|---|---|---|
| `id` | URI | ✅ | `neo://biz/kpi/<product>/<metric>` |
| `product` | URI | ✅ | `neo://biz/product/...` |
| `metric_name` | string | ✅ | `monthly_active_users / arr / retention_d28 / nps / conversion_rate` |
| `source` | enum | ✅ | `ga4 / posthog / supabase / gsc / manual` |
| `target_value` | string | optional | (e.g. "1M MAU" or "$350K ARR") |
| `current_value_observed_at` | ISO8601 | optional | |
| `current_value` | string | optional | latest snapshot |

### 3.10 `biz:Decision`
G1/G2 박제된 strategic decision.

| 속성 | type | required | 정의 |
|---|---|---|---|
| `id` | URI | ✅ | `neo://biz/decision/<slug>` (e.g. `g1-26-auradb-free`) |
| `g_level` | enum | ✅ | `G1 / G2` (G1 = Strategy Lead 자율, G2 = owner) |
| `decided_by` | URI (Founder or Agent) | ✅ | |
| `decided_at` | ISO8601 | ✅ | |
| `reversible` | bool | ✅ | |
| `source_artifact` | URI | ✅ | meta `neo://artifact/<handoff section>` |
| `affects` | URI[] | optional | `neo://biz/...` (영향 받은 비즈니스 객체) |
| `superseded_by` | URI | optional | 새 decision 시 |

### 3.11 (선택) `biz:ExternalFederation`
운영 의존하는 external system. 별도 클래스 vs meta `Service` 로 cover 가능 — v0.1 에선 **meta `Service` 로 cover, 별도 클래스 안 만듦**.

---

## §4. Relation Model (10 relations)

| # | 관계 | domain → range | cardinality |
|---|---|---|---|
| 1 | `biz:owns` | Founder → Product | 1:n |
| 2 | `biz:deployed_at` | Product → Domain | n:m |
| 3 | `biz:targets_lead` | Product → Lead | n:m |
| 4 | `biz:projected_revenue` | RevenueStream → Product | n:m |
| 5 | `biz:allocates` | Founder → Investment | 1:n |
| 6 | `biz:decided` | Founder/Agent → Decision | 1:n |
| 7 | `biz:measures` | KPI → Product | n:1 |
| 8 | `biz:produced` | Founder → ResearchIP | n:m (with AI agents co-produce) |
| 9 | `biz:supersedes` | Decision → Decision | n:1 (transitive) |
| 10 | `biz:cross_ref_meta` | biz:* → meta `neo://artifact/...` etc. | n:m |

---

## §5. URI Namespace

| 객체 | 패턴 |
|---|---|
| Founder | `neo://biz/founder/yesol-heo` |
| Product | `neo://biz/product/kott`, `neo://biz/product/toolpick`, ... |
| Domain | `neo://biz/domain/kott.kr` |
| Strategy | `neo://biz/strategy/revenue-path-v1` |
| RevenueStream | `neo://biz/revenue_stream/b1-sbu-acceleration` |
| Investment | `neo://biz/investment/d2-us-etf` |
| ResearchIP | `neo://biz/research_ip/koreanllm-ao1` |
| Lead | `neo://biz/lead/koreanllm-enterprise-1` |
| KPI | `neo://biz/kpi/kott/monthly_active_users` |
| Decision | `neo://biz/decision/g1-26-auradb-free` |

---

## §6. Source Mapping

| Source | Entity | Method |
|---|---|---|
| Hardcoded (founder identity) | Founder × 1 | manual seed |
| `D:\00.test\FOLDER_BIBLE.md` + `.agent/shared-brain/active-tasks.md` | Product × 16 | section parse |
| `.agent/knowledge/20260512_REVENUE_PATH_RESEARCH_v1.md` | Strategy + RevenueStream × 13 | structured table parse |
| 같은 doc | Investment × 5 (D2 / D1 / B1 광고비 / B3 / C2) | section parse |
| `D:\00.test\002.products-sbu\009.koreanllm\` + `PAPER/` | ResearchIP × 3 | dir walk + status |
| KoreanLLM B2B target section (handoff) | Lead × 10 | enumeration |
| (수동 seed initial) | KPI × ~10 | per SBU manual (MAU / ARR / retention) |
| `handoff.md` G1-1 ~ G1-31 박제 sections | Decision × 31 | regex `G1-\d+` parse |
| `business_domain_inventory.md` (gitignored) | Domain × 15 | read but redact secrets |

---

## §7. Cross-link Meta ↔ Biz

| Biz | Meta link |
|---|---|
| `biz:Product` | meta `Project` (same slug) — `meta_project: neo://project/kott` |
| `biz:Strategy.source_artifact` | meta `Artifact` (실 문서) |
| `biz:ResearchIP.meta_artifact_root` | meta `Artifact` |
| `biz:Decision.source_artifact` | meta `Artifact{kind:decision}` |
| `biz:Founder` | 1:1 meta `Agent{agent_kind:human}` (1 instance 만 추가) |
| `biz:KPI.source` | meta `Service` (GA4 / PostHog) |

---

## §8. Boundary 원칙 (재명시)

- **owner ≠ Founder 가 다른 context**: 본 ontology 는 founder = Neo Genesis 대표 역할만. CTS-AI 직원 / JD 구직자 / 가족 = 별도 context.
- **Customer 어휘 회피**: 현재 paying customer 0. `Lead` 만 사용. 매출 발생 시 `Customer` 추가 클래스 신설 (v0.2).
- **Personal forbidden 절대**: 사업자등록번호 full / 주민번호 / 가족 / 법무 → ontology 외.

---

## §9. Quality Gates (meta 와 공유)

기존 validate.py 가 nodes.jsonl 전체 검증 — biz 노드도 `rdf_type` 만 valid 면 PASS. P0 gates 동일 적용:
- URI uniqueness
- URI format (`neo://biz/...` regex 추가)
- Required fields per type
- Edge integrity
- Markings (personal-forbidden 0건)
- Secret redaction

---

## §10. Roadmap

| Version | 작업 | Acceptance |
|---|---|---|
| **v0.1** (이 문서) | contract + initial extraction | Founder 1 + Product 16 + RevenueStream 13 + Decision 31 박제 |
| v0.2 | KPI 갱신 cron (GA4 / PostHog daily fetch) | per Product KPI latest snapshot |
| v0.3 | Lead pipeline tracking (engagement_stage 진행) | koreanllm.org W0 launch (2026-06-10) 후 |
| v0.4 | Customer 클래스 신설 (첫 paying 발생 시) | 매출 0 → 1 trigger |
| v0.5 | Strategic dashboard (HippoRAG PPR seed=Founder) | "Founder 의 시간 / 자본 어디로 흐르는가" 즉답 |
| v1.0 | revenue model 자동 추론 (Lead × probability × value) | quarterly forecast |

---

## §11. G1 박제

| ID | 결정 | reversible? |
|---|---|---|
| G1-32-v2 | Business ontology 분리 신설 (`neo://biz/...` namespace) | yes |
| G1-33 | CTS / JD / personal 분리 — 본 ontology 외 | yes |
| G1-34 | Customer 어휘 회피, Lead 만 사용 (매출 0 단계) | yes |
| G1-35 | meta 와 biz 인프라 공유 (JSONL + AuraDB + tools + cron) | yes |

---

👤 Strategy Lead Claude Opus 4.7
