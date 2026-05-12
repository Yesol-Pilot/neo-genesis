# Real User Acquisition Research - 2026-05-12

## Executive Conclusion

Indexing and sitemap plumbing are mostly not the primary growth blocker anymore. The blocker is demand-to-page fit plus external discovery. Generic autonomous blog volume will not create MAU 100k. The fleet needs fewer, stronger acquisition assets: high-intent comparison/pricing/alternatives pages, free tools/templates/calculators, and explicit launch/distribution loops.

Execution excludes ToolPick, UR WRONG, and NeoGenesis. ToolPick may remain a benchmark only.

## Current Evidence

### PostHog, last 7 days

PostHog sees events on 9/9 commercial SBU sites, but total pageviews remain small.

| Site | Pageviews | Users | Note |
|---|---:|---:|---|
| craftdesk | 54 | 50 | Best non-Korean global signal after excluding benchmark sites |
| deploystack | 39 | 42 | Real visits, but almost no search demand yet |
| reviewlab | 55 | 51 | Korean target, real visit signal |
| kott | 60 | 49 | Korean target, real visit signal |
| ethicaai | 29 | 29 | Needs productization before growth spend |
| whylab | 25 | 25 | Needs positioning/product proof |
| aiforge | 3 | 3 | Very weak acquisition signal |
| finstack | 4 | 4 | Very weak acquisition signal |
| sellkit | 2 | 2 | Low recent users, but strongest GSC intent signal |

### GA4, latest local probe

GA4 and PostHog disagree on several host-level 7-day counts. K-OTT has a dedicated property with 14 users / 19 views / 15 sessions over 7 days and 69 users over 28 days. Shared subdomain host filters show mostly 0 users over 7 days but non-zero 28-day users for CraftDesk, DeployStack, ReviewLab, SellKit, FinStack, WhyLab, and AIForge.

Action: acquisition reporting must use a normalized view: PostHog pageviews/users, GA4 dedicated property or hostname rows, GSC impressions/clicks, and UTM-tagged launch traffic.

### GSC, full fleet snapshot from 2026-05-12 11:48 KST

The latest rolling GSC report has been overwritten by a single-site UR WRONG run, so this study uses the last full all-SBU snapshot.

| Site | GSC Signal | Interpretation |
|---|---|---|
| SellKit | 10 opportunities. Printful alternatives, Stripe pricing, Printful pricing, Gumroad review, ecommerce invoicing. | Highest demand-capture priority. Searchers show buying/comparison intent. |
| ReviewLab | 10 opportunities. Korean product/review pages and homepage impressions. | Real Korean review demand exists, but needs Naver/Google Korea title-snippet discipline. |
| CraftDesk | 1 opportunity around rapid prototyping UI tools. | Thin search signal, but PostHog users imply external/referral or bot-like traffic worth validating. |
| K-OTT | 0 opportunities, but GA4/PostHog live users. | Needs Korean OTT keyword architecture and Naver setup. |
| DeployStack | 0 GSC opportunities, PostHog users. | Must grow through developer distribution first, not wait for search. |
| AIForge | 0 GSC opportunities, low users. | Needs a tangible tool/demo before broad content. |
| FinStack | 0 GSC opportunities, low users. | Needs narrow finance-ops utility. |
| WhyLab / EthicaAI | Minimal or zero search opportunity. | Treat as credibility/productization assets until clear commercial audience exists. |

## Official Research Takeaways

1. Google discovery still depends heavily on useful content and links. Sitemaps help, but Google explicitly says site promotion and people knowing about the site matter.
2. Helpful content must be people-first, unique, up to date, and written for an intended audience. Large-scale automated content on broad topics is a warning sign if it lacks original value.
3. Structured data should be visible-page-aligned JSON-LD and tested. It can improve search result presentation, but it is not a substitute for useful pages.
4. IndexNow should be automated on publish/update/delete. It accepts up to 10,000 URLs per POST after host ownership verification.
5. AI search visibility requires crawl policy clarity:
   - Allow OAI-SearchBot for ChatGPT search visibility.
   - Allow PerplexityBot and Perplexity-User where AI search visibility is desired.
   - Allow Claude-SearchBot and Claude-User where Claude search/user fetch visibility is desired.
   - Google-Extended controls Gemini training/grounding use and does not affect Google Search ranking.
6. Product Hunt and Show HN are not blog syndication channels. They need a product or usable interactive artifact. HN explicitly rejects blog posts, newsletters, lists, sign-up pages, and landing pages as Show HN.
7. Figma Community is a strong CraftDesk channel only if there is a real template/UI kit/resource file with good name, description, category, tags, thumbnail, support link, and updates.
8. DEV can be used for developer SBUs with canonical links, tags, and series, but it should amplify useful technical artifacts, not duplicate thin posts.

## Acquisition Strategy

### Fleet Principle

Stop optimizing for "posts generated." Optimize for:

- real users by channel
- search impressions and clicks by page type
- tool/template usage
- returning users
- qualified CTA clicks
- backlinks/referrals from relevant communities

### Page Types That Should Dominate

| Page type | Why it matters |
|---|---|
| `/alternatives/{brand}` | Commercial comparison intent, proven by SellKit Printful signal |
| `/pricing/{brand}` | High-intent decision research, proven by Stripe/Printful signal |
| `/reviews/{brand}` | Review intent, useful for SellKit/ReviewLab |
| `/compare/{a}-vs-{b}` | Bottom-funnel choice intent |
| `/tools/{calculator-or-generator}` | Tryable asset for HN/Product Hunt/community launches |
| `/templates/{asset}` | Backlink/share asset, especially CraftDesk/DeployStack |
| `/guides/{job-to-be-done}` | Mid-funnel evergreen education |
| Korean `/posts` and `/compare` pages | ReviewLab/K-OTT need Korean query syntax and Naver-friendly snippets |

## SBU Priority

### Wave 1 - Immediate

1. SellKit global
   - Reason: strongest GSC signal.
   - Build: Printful alternatives expansion, Stripe fee calculator, POD margin calculator, Gumroad/Shopify/Payhip comparison pages.
   - Channels: Google, Bing/IndexNow, Shopify/WooCommerce/Etsy/POD communities, Product Hunt only after calculator/demo is polished.
   - 14-day target: 50+ GSC impressions/day, 20+ real users/day, first non-owned referral sources.

2. CraftDesk global
   - Reason: strongest PostHog global user count.
   - Build: Figma/UX rapid prototyping checklist, UI review template, prototype brief generator.
   - Channels: Figma Community, design communities, LinkedIn/X design threads, Google.
   - 14-day target: 100+ template duplicates/clicks or equivalent, 30+ real users/day from non-owned sources.

3. ReviewLab Korea
   - Reason: PostHog users plus Korean review GSC impressions.
   - Build: Korean product comparison/review pages with exact unique title, description, H1, FAQ schema, visible pros/cons, price/spec tables.
   - Channels: Google Korea, Naver Search Advisor, Korean product query surfaces.
   - 14-day target: indexed Korean long-tail pages, 30+ real users/day, first Korean query click.

4. K-OTT Korea
   - Reason: dedicated GA4 property shows recent users.
   - Build: OTT price comparison hub, "this month on OTT" guide, plan calculator, title/genre landing pages only if legally sourced.
   - Channels: Naver/Google Korea, Korean entertainment communities, weekly fresh pages.
   - 14-day target: 30+ real users/day, measurable branded/non-branded query split.

### Wave 2 - Distribution-First

5. DeployStack global
   - Build: CI/CD YAML generator, preview environment cost checklist, Vercel/Cloudflare/Render comparison.
   - Channels: DEV, HN regular submission or Show HN only if generator is usable without signup, GitHub templates.

6. AIForge global
   - Build: agent stack selector, evaluation checklist, small demo repo.
   - Channels: GitHub, Product Hunt, AI builder communities, newsletter outreach.

### Wave 3 - Productize Before Scaling

7. FinStack global
   - Build: Stripe reconciliation template, invoice/payment calculator, SaaS finance ops checklist.

8. WhyLab / EthicaAI global
   - Use as authority/credibility assets until a concrete user job exists. Do not spend volume-growth cycles yet.

## 30-Day Execution Loop

### Week 1

1. Fix analytics reporting so all-SBU GSC output cannot be overwritten by single-site sessions.
2. Add acquisition dashboard excluding ToolPick, UR WRONG, and NeoGenesis.
3. Ship SellKit calculator and 10 bottom-funnel pages.
4. Ship CraftDesk Figma/resource landing page and 5 intent pages.
5. Complete ReviewLab/K-OTT Korean title-description-H1 cleanup and Naver checks.

### Week 2

6. Launch CraftDesk template on Figma Community.
7. Launch SellKit calculator to relevant ecommerce/POD communities.
8. Ship DeployStack generator/template and post one canonical DEV article.
9. Build AIForge stack selector MVP and GitHub README.
10. Automate IndexNow on every publish/update/delete.

### Weeks 3-4

11. Run one public launch per SBU per week, but only for tryable artifacts.
12. Refresh pages that gain impressions but no clicks: title, intro answer block, comparison table, FAQ.
13. Kill or rewrite pages with zero impressions and weak user value.
14. Add internal links from successful pages to adjacent commercial pages.
15. Report weekly by channel, not just total traffic.

## Measurement Contract

Required events:

- `acq_landing_view`
- `answer_block_seen`
- `tool_used`
- `template_download_click`
- `external_source_click`
- `comparison_table_interaction`
- `cta_click`
- `returning_visit`

Required UTM policy:

- `utm_source`: producthunt, hn, devto, figma, reddit, naver, google, newsletter, community-name
- `utm_medium`: launch, post, template, tool, referral
- `utm_campaign`: `{sbu}-{asset}-{yyyyww}`

Weekly report must include:

- users by channel
- GSC impressions/clicks by page type
- PostHog activation events
- returning users
- top 10 pages by assisted CTA
- dead pages to prune or rewrite
- next experiments and stop conditions

## Sources

- Google SEO Starter Guide: https://developers.google.com/search/docs/fundamentals/seo-starter-guide
- Google Helpful Content: https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- Google Structured Data: https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data
- Google Crawlers / Google-Extended: https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers
- OpenAI Crawlers: https://developers.openai.com/api/docs/bots
- Anthropic Crawlers: https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler
- Perplexity Crawlers: https://docs.perplexity.ai/docs/resources/perplexity-crawlers
- IndexNow Documentation: https://www.indexnow.org/documentation
- Naver Search Advisor SEO Guide: https://searchadvisor.naver.com/guide/seo-help
- Product Hunt Launch Guide: https://www.producthunt.com/launch
- Product Hunt Posting Help: https://help.producthunt.com/en/articles/479557-how-to-post-a-product
- Show HN Guidelines: https://news.ycombinator.com/showhn.html
- Figma Community Publishing: https://help.figma.com/hc/en-us/articles/360040035974-Publish-files-to-the-Figma-Community
- DEV Writing Help: https://dev.to/help/writing-editing-scheduling

