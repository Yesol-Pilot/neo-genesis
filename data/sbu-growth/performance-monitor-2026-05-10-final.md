# SBU Performance Monitor Final Pass

- generatedAt: `2026-05-10T17:25:00+09:00`
- scope: AIForge, CraftDesk, DeployStack, FinStack, SellKit, ReviewLab, K-OTT, WhyLab, EthicaAI
- excluded by owner instruction: ToolPick, UR WRONG, NeoGenesis main

## Executive State

| Gate | Result | Evidence |
|---|---:|---|
| Live SEO/GEO/GA/PostHog browser audit | PASS 9/9 | `seo-geo-live-latest.*` |
| PostHog API ingestion | PASS 9/9 | `posthog-traffic-latest.*` |
| GSC property + sitemap + 28d search analytics | PASS 9/9 | `gsc-all-sbu-latest.*` |
| Core SBU growth ops suite | PASS 5/5 | `growth-ops-suite-latest.*` |
| Core SBU modeled MAU readiness | 599,900 | AIForge/CraftDesk/DeployStack/FinStack/SellKit |

## Live Fixes Completed

| Site | Fix | Deployment state |
|---|---|---|
| AIForge | 2026-05-10 autonomous post confirmed live; PostHog production key normalized | `https://aiforge.neogenesis.app` aliased |
| CraftDesk | Rewrote 3 GSC opportunity pages for AI UI design, rapid prototyping, remote design collaboration intent | commit `7148360`, production deployed |
| DeployStack | Fly.io/Railway pricing intent and 2026-05-10 post confirmed live | production deployed |
| SellKit | Printful/Gumroad source-backed alternatives intent and 2026-05-10 post confirmed live | production deployed |
| ReviewLab | Korean home/product review CTR layer, FAQ JSON-LD, BAR300/00 intent override | commit `0b00a55`, production deployed |
| WhyLab | Added 10 causal inference crawl pages, sitemap links, analytics fallback | root commits `40afa4c`, `89c05b6`, production deployed |
| EthicaAI | Added 11 AI governance/compliance crawl pages, sitemap links, analytics fallback | root commits `40afa4c`, `89c05b6`, production deployed |

## Current GA4 Traffic

| Site | 7d users | 7d views | 28d users | 28d views |
|---|---:|---:|---:|---:|
| AIForge | 0 | 0 | 3 | 3 |
| CraftDesk | 2 | 2 | 35 | 39 |
| DeployStack | 1 | 1 | 9 | 9 |
| FinStack | 0 | 0 | 5 | 5 |
| SellKit | 0 | 0 | 2 | 2 |
| ReviewLab | 1 | 1 | 6 | 6 |
| K-OTT | 16 | 16 | 77 | 79 |
| WhyLab | 0 | 0 | 7 | 7 |
| EthicaAI | 0 | 0 | 0 | 0 |

## Current PostHog Ingestion

| Site | Events | Pageviews | Users | Last seen |
|---|---:|---:|---:|---|
| AIForge | 3 | 1 | 1 | 2026-05-10T17:14:22+09:00 |
| CraftDesk | 137 | 63 | 59 | 2026-05-10T17:14:34+09:00 |
| DeployStack | 78 | 36 | 35 | 2026-05-10T17:14:41+09:00 |
| FinStack | 3 | 1 | 1 | 2026-05-10T17:14:50+09:00 |
| SellKit | 1 | 1 | 1 | 2026-05-10T17:15:03+09:00 |
| ReviewLab | 69 | 56 | 52 | 2026-05-10T17:15:12+09:00 |
| K-OTT | 73 | 49 | 48 | 2026-05-10T17:15:19+09:00 |
| WhyLab | 27 | 25 | 25 | 2026-05-10T17:15:34+09:00 |
| EthicaAI | 55 | 31 | 31 | 2026-05-10T17:15:26+09:00 |

## Residual Risk

- Instrumentation is now verified; the remaining bottleneck is real acquisition volume, not GA/PostHog/GSC connection.
- GA4 actual users are still far below 100k MAU. The 100k+ status is readiness/modeling, not achieved traffic.
- Core ops suite still uses a lightweight text check for PostHog live status; browser audit and API ingestion are the authoritative checks.
