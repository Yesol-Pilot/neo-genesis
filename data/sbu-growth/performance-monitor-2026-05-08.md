# SBU Performance Monitor - 2026-05-08

- generatedAt: 2026-05-08T11:45:00+09:00
- scope: ToolPick, UR WRONG, NeoGenesis excluded from action loop; included only where noted as reference.
- sources: GA4 Data API, Google Search Console API, PostHog HogQL, live SEO/GEO/PostHog audit.

## Executive Summary

- Full GA4 reference total: 28d active users 2008, 28d views 2272, 7d active users 258, today active users 17.
- Non-excluded SBU total: 28d active users 144, 28d views 150, 7d active users 40, 7d views 40.
- Live quality: 12/13 passed. The only failure is ToolPick `posthog_capture_missing`, which is excluded from this session because another session owns ToolPick.
- GSC non-excluded scope: 9/9 properties listed, 9/9 live sitemaps 200, 9/9 GSC sitemaps known, 93 search rows fetched.
- Current bottleneck: outside ToolPick, there is not enough sustained traffic yet. The first growth lever is improving already-impressed pages, not adding broad new surface area.

## GA4 Snapshot

| Site | 7d Users | 7d Views | 28d Users | 28d Views | Today |
|---|---:|---:|---:|---:|---:|
| AIForge | 0 | 0 | 3 | 3 | 0 |
| CraftDesk | 15 | 15 | 35 | 39 | 0 |
| SellKit | 0 | 0 | 2 | 2 | 0 |
| FinStack | 1 | 1 | 5 | 5 | 0 |
| DeployStack | 3 | 3 | 9 | 9 | 0 |
| ReviewLab | 3 | 3 | 6 | 6 | 0 |
| K-OTT | 16 | 16 | 77 | 79 | 0 |
| WhyLab | 2 | 2 | 7 | 7 | 0 |
| EthicaAI | 0 | 0 | 0 | 0 | 0 |
| Non-excluded SBU total | 40 | 40 | 144 | 150 | 0 |

Reference-only excluded:

| Site | 7d Users | 7d Views | 28d Users | 28d Views | Today |
|---|---:|---:|---:|---:|---:|
| ToolPick | 203 | 258 | 1793 | 1887 | 17 |
| UR WRONG | 13 | 18 | 59 | 151 | 0 |

## GSC Opportunities

| Priority | Site | Page | Impressions | Clicks | Note |
|---:|---|---|---:|---:|---|
| 1 | SellKit | `/alternatives/printful` | 139 | 0 | Highest non-excluded impression pool; improve title/intro/internal links. |
| 2 | SellKit | `/blog/ecommerce-platform-with-built-in-invoicing` | 80 | 0 | Recently improved; monitor lag before next edit. |
| 3 | SellKit | `/alternatives/gumroad` | 33 | 0 | Striking-distance pricing intent. |
| 4 | DeployStack | `/blog/kubernetes-cost-optimization-tools` | 17 | 0 | Recently improved; monitor lag before next edit. |
| 5 | ReviewLab | BAR300/00 review variants | 11 | 1 | Title cleanup deployed; monitor CTR movement. |
| 6 | CraftDesk | AI/UI design pages | 9 | 0 | Needs design-intent cluster strengthening. |

## PostHog 7d Event Health

| Site | Events | Persons | Pageviews | Autocapture | Web Vitals | AI Search Visits | Rageclick |
|---|---:|---:|---:|---:|---:|---:|---:|
| CraftDesk | 114 | 62 | 65 | 15 | 2 | 8 | 0 |
| K-OTT | 64 | 34 | 34 | 6 | 22 | 0 | 1 |
| ReviewLab | 40 | 31 | 31 | 2 | 1 | 0 | 0 |
| EthicaAI host | 28 | 4 | 4 | 18 | 6 | 0 | 0 |
| DeployStack | 27 | 25 | 24 | 0 | 0 | 0 | 0 |
| WhyLab | 17 | 17 | 17 | 0 | 0 | 0 | 0 |
| EthicaAI site id | 14 | 14 | 14 | 0 | 0 | 0 | 0 |

## Action Queue

1. SellKit `/alternatives/printful`: treat as the next highest-ROI CTR page.
2. SellKit `/alternatives/gumroad`: improve pricing/free-plan snippet and comparison blocks.
3. CraftDesk design-intent cluster: add direct answer blocks for `ui designs ai`, `rapid prototyping user interface`, and `design systems library`.
4. K-OTT engagement: investigate 100% bounce / near-zero average duration before pushing more acquisition.
5. DeployStack Kubernetes page: wait for the recent edit to age, then recheck GSC position and impressions.
