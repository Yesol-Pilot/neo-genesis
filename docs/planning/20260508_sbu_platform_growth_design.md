# Neo Genesis SBU Platform Improvement Design

- Date: 2026-05-08
- Owner goal: make all commercial live sites capable of sustained growth, with ReviewLab and K-OTT optimized for Korean users and the remaining SBU properties optimized for global users.
- Current evidence: `data/sbu-growth/performance-monitor-2026-05-08.md`, `data/sbu-growth/gsc-all-sbu-latest.md`, `data/sbu-growth/seo-geo-live-latest.md`
- Official reference baseline:
  - Google Search Central people-first content: https://developers.google.com/search/docs/fundamentals/creating-helpful-content
  - Google Search Central product snippets: https://developers.google.com/search/docs/appearance/structured-data/product-snippet
  - Google Search Central ecommerce structured data: https://developers.google.com/search/docs/specialty/ecommerce/include-structured-data-relevant-to-ecommerce
  - Naver Search Advisor structured data: https://searchadvisor.naver.com/guide/structured-data-intro
  - Naver Search Advisor robots/sitemap: https://searchadvisor.naver.com/guide/seo-basic-robots
  - Naver Search Advisor review structured data: https://searchadvisor.naver.com/guide/structured-data-review
  - PostHog events: https://posthog.com/docs/data/events
  - PostHog funnels: https://posthog.com/docs/product-analytics/funnels

## 1. Diagnosis

The platform has a working technical distribution layer, but only one property has real traffic scale.

| Area | Current State | Platform Risk |
|---|---|---|
| Traffic distribution | ToolPick carries most traffic. Non-excluded SBU total is 144 active users over 28 days. | Portfolio risk: one-site dependency. |
| Indexing | Current live sitemaps and GSC properties are broadly healthy. | Technical SEO is not the bottleneck anymore. |
| Content quality | Many pages exist, but only a few get impressions. | Programmatic volume can look thin or duplicated without stronger page-level value. |
| Conversion | PostHog shows pageviews, but CTA and affiliate events are near zero. | Traffic cannot become revenue without explicit conversion surfaces. |
| Localization | ReviewLab and K-OTT need Korean search/user behavior. Other SBU sites need global English positioning. | One global template will underperform in Korean review/OTT contexts. |
| Observability | GA4/GSC/PostHog are available, but action decisions are not yet bound to thresholds. | Reporting can become noise without kill/keep/scale rules. |

## 2. Strategic Split

### Korean User SBU Group

ReviewLab and K-OTT should be operated as Korean user products, not translated versions of global templates.

| Site | Primary Audience | Core Search Surfaces | Primary Conversion |
|---|---|---|---|
| ReviewLab | Korean shoppers comparing consumer products | Google Korea, Naver web search, product/review snippets | Affiliate click, price-check click, comparison-card click |
| K-OTT | Korean OTT viewers deciding what to watch or subscribe to | Google Korea, Naver web search, topical entertainment queries | Watch-provider click, subscription guide click, recommendation filter use |

### Global SBU Group

AIForge, CraftDesk, DeployStack, FinStack, SellKit, WhyLab, EthicaAI, ToolPick, UR WRONG, and NeoGenesis should be optimized around global English search intent. ToolPick, UR WRONG, and NeoGenesis can remain in separate execution ownership if another session owns them, but their telemetry and design principles should stay compatible with the common platform.

| Site | Global Positioning | Current Priority |
|---|---|---|
| SellKit | Ecommerce software decision engine | Highest non-ToolPick GSC opportunity: Printful/Gumroad/invoicing pages. |
| CraftDesk | Design workflow and creative tool decision engine | Cluster strengthening around AI UI, prototyping, design systems. |
| DeployStack | DevOps and cloud infrastructure decision engine | Kubernetes and pricing-intent pages. |
| AIForge | AI tool and security automation decision engine | Low data, but clear AI security/API testing impressions. |
| FinStack | Fintech tools and finance workflow decision engine | Needs first meaningful content moat and KYC/API pricing consolidation. |
| WhyLab | Causal inference and decision intelligence | Small branded demand; needs clearer product proof. |
| EthicaAI | AI ethics/research surface | Currently negligible traffic; needs either authoritative research moat or deprioritization. |

## 3. North Star Metrics

The system should stop treating "live and indexable" as success. The new funnel is:

`indexed page -> search impression -> click -> engaged session -> decision interaction -> outbound/revenue event`

| Stage | Metric | Minimum Gate | Scale Gate |
|---|---|---:|---:|
| Coverage | Sitemap 200, canonical, schema, llms.txt, GA, PostHog | 100 percent for active sites | Continuous |
| Search demand | GSC impressions per priority page | 30 impressions / 28d | 500 impressions / 28d |
| CTR | GSC clicks / impressions | 1 percent when avg position <= 30 | 3 percent plus |
| Engagement | GA4 engagement rate, avg duration, PV/session | No 100 percent bounce on active pages | 20 percent plus engaged sessions |
| Product action | comparison, filter, CTA, affiliate, outbound events | At least 1 action / 100 pageviews | 5 actions / 100 pageviews |
| Revenue proof | affiliate/outbound monetizable click | At least 1 per active SBU / week | 3 percent pageview-to-revenue-click |

## 4. Common Platform Design

### 4.1 Content Operating System

Every page belongs to one of five page classes.

| Page Class | Purpose | Required Blocks | Example |
|---|---|---|---|
| Money page | Capture high-intent buyer/searcher demand | Quick answer, comparison table, decision matrix, CTA, FAQ, source notes | SellKit Printful alternatives |
| Support page | Build topical authority and internal links | Definition, use cases, pitfalls, links to money pages | CraftDesk design systems library |
| Hub page | Organize a topic cluster | Cluster intro, latest posts, best pages, glossary, related decisions | `/blog/topics/e-commerce-platforms` |
| Data page | Provide original or semi-original value | Dataset, scoring model, timestamp, methodology | DeployStack pricing/resource tables |
| Product page | Convert and explain owned product | Positioning, proof, demo, CTA, FAQ | WhyLab homepage |

No page should ship without:

- One clear target query group.
- One primary user job.
- One next action.
- At least three internal links: hub, adjacent comparison, conversion page.
- A visible update date or evidence timestamp if the topic is volatile.
- A measurement contract: page type, intent cluster, and expected conversion event.

### 4.2 Page Template for Global SBU Sites

Global commercial pages should use this structure:

1. H1 that exactly matches the decision category, not a vague editorial title.
2. First 120 words: direct answer, who it is for, what trade-off it solves.
3. "Best fit by use case" matrix.
4. "What to compare before buying" checklist.
5. Pricing or risk caveat if the page touches costs.
6. Competitor or alternative table when relevant.
7. Internal path block:
   - Topic hub
   - Related comparison
   - Review/pricing page
8. CTA block:
   - Official/vendor click
   - Calculator or comparison filter
   - Newsletter or saved shortlist when affiliate is not available.
9. FAQ with real query language.

### 4.3 Page Template for ReviewLab

ReviewLab must prioritize Korean buyer trust.

Required page blocks:

1. Korean H1 with product name, model number, and review intent.
2. Buyer snapshot above the fold:
   - price observed
   - delivery/shipping signal
   - rating/review count if available
   - best fit
   - check before buying
3. Pros/cons table written in natural Korean.
4. "Who should buy / who should skip" block.
5. Price-check CTA with affiliate event.
6. Product schema with one reviewed product per page.
7. Review/AggregateRating schema only when rating data is valid and traceable.
8. Korean disclosure:
   - AI-assisted content if applicable
   - affiliate commission if applicable
   - source freshness.

Hard rules:

- Do not publish mojibake or broken Korean frontmatter.
- Do not duplicate review pages for the same model unless canonical consolidation is explicit.
- Keep page HTML size under control. The homepage should not ship multi-megabyte HTML.
- Product images must be real product images or clearly marked placeholders.

### 4.4 Page Template for K-OTT

K-OTT must serve Korean entertainment decisions, not generic OTT text.

Required page blocks:

1. Korean H1 focused on the viewer job:
   - "어디서 볼 수 있나"
   - "요금제 비교"
   - "이번 주 추천"
   - "가족/1인/학생에게 맞는 OTT"
2. Above-fold answer:
   - provider
   - availability
   - price tier
   - who it fits
3. Filterable recommendation block:
   - genre
   - provider
   - price sensitivity
   - device/family use
4. Comparison table:
   - Netflix, Disney+, TVING, Wavve, Coupang Play, Watcha, Apple TV+ where relevant.
5. Korean FAQ:
   - subscription cancellation
   - simultaneous screens
   - ad tier
   - offline download
6. CTA:
   - provider click
   - "내 조건으로 추천 보기"
   - newsletter/weekly watchlist.

K-OTT should not optimize only for pageviews. The product action is filter use and provider click.

## 5. Analytics and Event Taxonomy

PostHog events should measure decisions, not just pageviews. The current zero CTA/affiliate signal means the platform cannot prove commercial value.

### Required Events

| Event | Fires When | Required Properties |
|---|---|---|
| `content_answer_seen` | First answer block enters viewport | `site_id`, `audience_locale`, `page_type`, `intent_cluster`, `content_id` |
| `comparison_table_seen` | Primary comparison table enters viewport | same plus `table_id` |
| `comparison_filter_change` | User changes a filter | same plus `filter_name`, `filter_value` |
| `cta_viewport_reached` | Primary CTA enters viewport | same plus `cta_id`, `cta_type` |
| `cta_click` | CTA clicked | same plus `cta_id`, `cta_type`, `destination_type` |
| `affiliate_click` | Monetizable outbound clicked | same plus `merchant`, `product_id`, `destination_url_hash` |
| `outbound_official_click` | Official vendor/provider clicked | same plus `vendor`, `destination_url_hash` |
| `internal_next_click` | User clicks a recommended next page | same plus `target_page_type` |
| `source_expand` | User opens source/methodology details | same plus `source_type` |

### Required Properties

| Property | Example | Reason |
|---|---|---|
| `site_id` | `sellkit` | Cross-site grouping. Trim whitespace at source. |
| `audience_locale` | `ko-KR`, `en-US` | Separates Korean and global behavior. |
| `market` | `kr`, `global` | Business reporting. |
| `page_type` | `alternative`, `review`, `pricing`, `hub` | Funnel comparison. |
| `intent_cluster` | `printful_alternatives`, `ott_pricing` | Search-to-action mapping. |
| `content_id` | slug | Durable page identity. |
| `experiment_id` | `sellkit-printful-hero-v1` | Before/after measurement. |

### Funnel Design

Create one shared funnel per page class:

1. `$pageview`
2. `content_answer_seen`
3. `comparison_table_seen` or `source_expand`
4. `cta_viewport_reached`
5. `cta_click` or `affiliate_click`

Korean-specific funnels:

- ReviewLab: `$pageview -> buyer_snapshot_seen -> pros_cons_seen -> affiliate_click`
- K-OTT: `$pageview -> recommendation_filter_change -> provider_click`

## 6. Search Growth Design

### 6.1 Opportunity Scoring

Each candidate page receives a score:

`score = impressions * intent_value * page_type_value * freshness_need / max(position, 1)`

Intent value:

- 5: pricing, alternative, review, buy, compare
- 4: best, tools, software, platform
- 3: how-to with product fit
- 2: definition or broad topic
- 1: ambiguous or branded with no product fit

Page type value:

- 5: money page
- 4: product page
- 3: hub page
- 2: support page
- 1: thin informational page

### 6.2 Current Priority Queue

| Priority | Site | Page | Why |
|---:|---|---|---|
| 1 | SellKit | `/alternatives/printful` | 139 impressions, 0 clicks. Highest non-ToolPick opportunity. |
| 2 | SellKit | `/alternatives/gumroad` | Pricing/free-plan query has stronger buyer intent. |
| 3 | ReviewLab | BAR300/00 variants | Korean product review queries already near click range. |
| 4 | CraftDesk | AI UI/design cluster | Low volume, but clear topical direction. |
| 5 | K-OTT | Homepage and content funnels | 77 28d users but weak engagement. |
| 6 | DeployStack | Kubernetes cost page | Recent edit needs aging before further edits. |
| 7 | FinStack | KYC API pricing and homepage | New page needs indexing and internal links. |

## 7. SBU-Specific Redesign Backlog

### ReviewLab, Korean

P0:

- Fix any remaining mojibake in content/frontmatter.
- Consolidate duplicate product-model pages with canonical rules.
- Add buyer snapshot component to all top 50 product pages.
- Add valid Product/Review/AggregateRating markup only where data is traceable.
- Reduce homepage HTML payload by pagination or server-side slicing.

P1:

- Create Korean product category hubs:
  - 커피머신
  - 노트북
  - 태블릿
  - 무선이어폰
  - 로봇청소기
- Add model-number comparison blocks for pages with GSC impressions.
- Add `affiliate_click`, `price_check_click`, `pros_cons_seen`.

Success gate:

- Top 20 GSC product pages reach 2 percent CTR when average position <= 20.
- Affiliate click rate above 3 percent of product pageviews.

### K-OTT, Korean

P0:

- Diagnose 100 percent bounce / near-zero duration behavior.
- Replace generic homepage with a practical Korean decision UI:
  - provider selector
  - genre selector
  - price-sensitive plan table
  - weekly watchlist.
- Add `provider_click` and `recommendation_filter_change`.

P1:

- Build Korean search pages:
  - "넷플릭스 요금제 비교"
  - "쿠팡플레이 볼만한 것"
  - "디즈니플러스 한국 추천"
  - "OTT 가족 요금제 비교"
- Add FAQPage schema where the page contains visible Korean Q&A.

Success gate:

- Engagement rate above 20 percent.
- Filter interaction in at least 5 percent of sessions.

### SellKit, Global

P0:

- Redesign `/alternatives/printful` first screen and meta:
  - current problem: high impressions, no clicks.
  - add title variants focused on "Printful Alternatives for POD Sellers".
  - add use-case matrix: Shopify, Etsy, apparel margin, global fulfillment, branding.
- Add CTA events to alternative pages.

P1:

- Repeat for Gumroad and ecommerce invoicing.
- Add calculators: platform fee, payment fee, POD margin.

Success gate:

- `/alternatives/printful` gets first 5 organic clicks within the next GSC window.
- Alternative page CTA click rate above 2 percent.

### CraftDesk, Global

P0:

- Create a design-intent hub:
  - AI UI design tools
  - rapid prototyping tools
  - design system libraries
  - real-time design collaboration.
- Add visual comparison blocks and screenshots where possible.

Success gate:

- At least 50 GSC impressions / 28d across the cluster.
- At least one `ai_search_visit` or comparison interaction per 20 pageviews.

### DeployStack, Global

P0:

- Wait for the Kubernetes page update to age.
- Add pricing pages with strong snippets where impressions are near position 3, especially Railway.
- Maintain redirects for misplaced fintech pages.

Success gate:

- Pricing pages achieve CTR above 3 percent when average position <= 10.

### FinStack, Global

P0:

- Internal-link KYC API pricing from fintech/KYC automation pages.
- Convert homepage query "fullstack finance" into an explicit FinStack positioning block to avoid brand/query confusion.

Success gate:

- KYC API pricing enters GSC rows within 14 days.

### AIForge, Global

P0:

- Expand AI security and API testing cluster.
- Add security decision checklists with developer release triggers.

Success gate:

- AI security cluster reaches 30 impressions / 28d.

### WhyLab and EthicaAI, Global

P0:

- Decide whether each is a product, research lab, or authority publication.
- If product: add demo/proof/action.
- If research: add explainers, citations, and methodology pages.
- If neither can be supported, deprioritize from MAU growth target until a clearer offer exists.

Success gate:

- Branded and non-branded GSC rows both present.

## 8. Governance and Agent Workflow

### Roles

| Role | Responsibility | Output |
|---|---|---|
| PM | Prioritize SBU/page queue by score and business value | Weekly action board |
| DA | GA4/GSC/PostHog analysis and anomaly detection | Daily monitor |
| SEO/GEO | Query mapping, schema, snippets, internal links | Page brief |
| Content Editor | Rewrite first screen, evidence, FAQs, Korean/global tone | Page patch |
| UX/Conversion | CTA, comparison UI, filter and affiliate surfaces | Component brief |
| Engineer | Implement templates, events, redirects, performance fixes | PR/commit |
| QA | Build, browser, live, schema, analytics verification | Gate report |

### Execution Loop

1. Daily monitor:
   - GA4 7d/28d users and pageviews
   - GSC rows, impressions, clicks, position
   - PostHog pageviews and action events
   - live quality audit
2. Page selection:
   - pick top 3 pages by opportunity score
   - exclude pages edited within the last 7 days unless technically broken
3. Brief:
   - target audience
   - target query
   - current title/description
   - above-fold rewrite
   - internal links
   - conversion event
4. Implement:
   - content rewrite
   - CTA/event wiring
   - schema and performance fix if needed
5. Verify:
   - local build
   - production deploy
   - live status 200
   - sitemap presence
   - title/meta/schema check
   - PostHog event smoke
6. Monitor:
   - 48h: live event health
   - 7d: GA4 user movement
   - 14d/28d: GSC CTR and position movement

## 9. Quality Gates

### Release Gate

Every changed SBU must pass:

- `npm run build` or site equivalent.
- `curl/fetch` live 200 for changed URL.
- sitemap includes new canonical URL or legacy URL redirects correctly.
- title and description do not duplicate brand suffixes.
- JSON-LD parses and does not mark up invisible content.
- GA and PostHog both present.
- At least one meaningful action event is wired for money pages.

### Korean Quality Gate

ReviewLab and K-OTT must additionally pass:

- No mojibake in title, meta, H1, FAQ, or visible body.
- Korean wording reads naturally.
- Korean search intent is reflected in title and first answer block.
- Naver robots/sitemap basics remain valid.
- Review/product structured data follows one-review-target-per-page logic.

### Global Quality Gate

Global SBU pages must additionally pass:

- Clear English page purpose.
- Query-matching title without clickbait.
- Original decision framework, matrix, calculator, dataset, or workflow advice.
- No generic AI filler.
- Internal links connect the cluster.

## 10. 30/60/90 Day Plan

### First 30 Days

- Instrument common action events across active SBU templates.
- Rewrite highest opportunity pages:
  - SellKit Printful
  - SellKit Gumroad
  - ReviewLab BAR300/00
  - CraftDesk AI UI/design cluster
  - K-OTT homepage/recommendation flow
- Add Korean quality cleanup pass for ReviewLab.
- Add dashboard view that separates Korean and global SBU performance.

### Days 31-60

- Scale the winning template across 20 pages per SBU.
- Add calculators/filters to money pages.
- Build Korean category hubs for ReviewLab and K-OTT.
- Add weekly kill/keep/scale decision table:
  - kill: no impressions after 28 days and no internal strategic reason
  - keep: impressions but no clicks
  - scale: clicks or action events appear

### Days 61-90

- Consolidate duplicate/weak pages.
- Build backlink/distribution assets for the strongest pages.
- Expand only SBU clusters that have proven impressions and engagement.
- Start revenue optimization only after action events are non-zero.

## 11. Immediate Implementation Order

1. Add shared event taxonomy helper to reusable SBU template code.
2. SellKit Printful alternatives CTR/CTA rewrite.
3. K-OTT Korean engagement diagnosis and homepage decision UI redesign.
4. ReviewLab Korean product quality pass and homepage payload reduction.
5. CraftDesk design-intent hub and internal link loop.
6. FinStack KYC internal-link reinforcement.
7. DeployStack pricing-intent pages and delayed Kubernetes recheck.
8. AIForge AI security cluster expansion.
9. WhyLab/EthicaAI positioning decision.
10. Weekly monitor automation that writes Korean/global split reports.

## 12. Stop Conditions

Pause broad content generation for a site if:

- 28d GSC impressions are flat for three cycles.
- CTA/action events remain zero after page-level event wiring.
- Content QA finds recurring duplicate, mojibake, or generic filler.
- The site lacks a clear audience and monetizable next action.

Continue or scale if:

- GSC impressions grow for two consecutive cycles.
- Any money page gets organic clicks.
- Action events appear and can be tied to a page class.
- A page type repeatedly beats the SBU median engagement.
