# SBU Performance Monitoring - 2026-05-10 KST

Scope excludes ToolPick, UR WRONG, and NeoGenesis because they are handled in separate sessions.

## Executive Summary

- Overall status: not ready to call perfect. Measurement is connected, but acquisition is still too thin.
- GA4 28d included-scope total: 144 active users, 150 sessions, 150 pageviews.
- GA4 7d included-scope total: 20 active users.
- GSC fetch: 9/9 properties listed, 9/9 live sitemaps OK, 9/9 GSC sitemaps known, 9/9 Search Analytics fetch OK.
- Growth ops gate: failed because AIForge has a generated 2026-05-10 post that is not live yet.
- Immediate owner action is not more dashboard watching. Fix AIForge publish/deploy lag, then apply GSC opportunity pages for SellKit, ReviewLab, DeployStack, CraftDesk, and AIForge.

## Measurement Integrity

| Source | Result | Note |
|---|---:|---|
| GA4 Data API | PASS | Latest pull succeeded on 2026-05-10. Shared property host filters are working for NeoGenesis subdomains. |
| Search Console API | PASS | Refresh token source, 9 properties readable as siteOwner. |
| Live sitemap | PASS | 9/9 live sitemaps returned 200. |
| GSC sitemap registry | PASS | 9/9 sitemaps known by Search Console. |
| PostHog code readiness | PASS for audited 5 blog SBUs | AIForge, CraftDesk, DeployStack, FinStack, SellKit have event taxonomy readiness green. |
| Growth pipeline | FAIL | AIForge latest local post missing from live blog, detail URL, and sitemap. |

## GA4 Traffic

Window: GA4 script pulled `7daysAgo..yesterday`, `28daysAgo..yesterday`, and today on 2026-05-10 KST.

| Site | 7d Users | 28d Users | 28d Sessions | 28d Views | Today Users | Diagnosis |
|---|---:|---:|---:|---:|---:|---|
| K-OTT | 16 | 77 | 80 | 79 | 0 | Korean target has the strongest included traffic, but page depth is weak. |
| CraftDesk | 2 | 35 | 38 | 39 | 0 | Some traffic exists; still mostly one-page visits. |
| DeployStack | 1 | 9 | 9 | 9 | 0 | Indexing exists, acquisition weak. |
| WhyLab | 0 | 7 | 7 | 7 | 0 | Long-duration 30d signal exists in GA console output, but traffic is sparse. |
| ReviewLab | 1 | 6 | 6 | 6 | 0 | Korean review pages are showing in GSC; GA volume is still tiny. |
| FinStack | 0 | 5 | 5 | 5 | 0 | Recent hardening not yet reflected in traffic. |
| AIForge | 0 | 3 | 3 | 3 | 0 | Pipeline lag is suppressing freshness. |
| SellKit | 0 | 2 | 2 | 2 | 0 | GSC demand exists but GA clicks are not converting yet. |
| EthicaAI | 0 | 0 | 0 | 0 | 0 | Measurement is connected, but there is no observed GA traffic. |

## Search Console

Window: 2026-04-10 to 2026-05-08.

| Site | GSC Rows | Opportunities | Live Sitemap URLs | Priority |
|---|---:|---:|---:|---|
| SellKit | 52 | 10 | 458 | P0: already has demand, zero-click opportunity pages. |
| ReviewLab | 35 | 10 | 1003 | P0: Korean impressions exist; encoding/query quality and CTR need cleanup. |
| DeployStack | 8 | 3 | 450 | P1: Railway pricing and Kubernetes cost pages are the best hooks. |
| CraftDesk | 6 | 3 | 500 | P1: AI UI/design workflow pages need better titles/snippets. |
| AIForge | 3 | 2 | 645 | P0 technical: publish lag first, then AI security/dev pages. |
| WhyLab | 3 | 1 | 4 | P2: brand query only; needs more research pages. |
| FinStack | 1 | 1 | 442 | P2: early signal only. |
| K-OTT | 0 | 0 | 448 | P1 Korean site has GA traffic but GSC page/query rows not yet populated. |
| EthicaAI | 0 | 0 | 3 | P2: needs expanded crawlable surface. |

Top actionable opportunities:

- SellKit: `/alternatives/printful`, ecommerce billing/invoicing pages, `/alternatives/gumroad`.
- ReviewLab: home, BAR30000 posts, HP 2026 notebook post, Bluetooth earphone review pages.
- DeployStack: `/blog/kubernetes-cost-optimization-tools`, `/pricing/railway`, `/pricing/fly-io`.
- CraftDesk: AI UI design tools, rapid prototyping, remote design workflow pages.
- AIForge: AI cybersecurity and AI-powered API security testing pages, after fixing live publish lag.

## Quality Diagnosis

- The sites are technically measurable, but most included SBUs are below a meaningful user baseline. 144 active users over 28 days across 9 sites is not enough to validate product-market pull.
- GSC is ahead of GA for SellKit and ReviewLab. That means pages are being seen but not clicked enough, so titles/snippets and intent matching matter more than adding generic volume.
- K-OTT is the inverse: GA has users but GSC rows are empty in the pulled window, so social/direct/referral or delayed Search Console reporting is likely. It needs a 24-72h GSC follow-up.
- AIForge has the clearest operational defect: the content pipeline generated `2026-05-10-ai-workflow-automation-stack`, but live coverage is missing.
- EthicaAI and WhyLab have too little crawlable surface for MAU growth; they are research landing pages, not yet search inventory businesses.

## Action Queue

1. Fix AIForge publish/deploy lag and verify the latest post appears on `/blog`, detail URL, and sitemap.
2. Rewrite and internally route SellKit Printful/Gumroad/ecommerce billing pages around exact GSC query intent.
3. Clean ReviewLab Korean query/title encoding quality and strengthen CTR on pages already ranking positions 7-21.
4. Expand DeployStack Railway/Fly.io pricing pages with fresher comparison hooks and official-source freshness notes.
5. Add CraftDesk AI UI design/prototyping snippets and comparison blocks for the specific queries now appearing.
6. Add K-OTT GSC indexing follow-up after 24-72h and compare GA users to GSC rows.
7. Expand WhyLab from 4 sitemap URLs to at least 20 crawlable use-case pages.
8. Expand EthicaAI from 3 sitemap URLs to at least 20 crawlable compliance/evaluation pages.
9. Add a PostHog live-ingestion verification script, not just code-presence checks.
10. Re-run this monitor after AIForge deploy fix and after Search Console data catches up.

## Source Artifacts

- GA4 JSON: `logs/ga4_result.json`
- GSC latest: `data/sbu-growth/gsc-all-sbu-latest.json`
- GSC latest markdown: `data/sbu-growth/gsc-all-sbu-latest.md`
- Growth ops latest: `data/sbu-growth/growth-ops-suite-latest.json`
- Growth flywheel latest: `data/sbu-growth/search-growth-flywheel-custom-cb1a6d941ace-latest.json`
