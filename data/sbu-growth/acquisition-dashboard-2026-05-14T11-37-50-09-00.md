# SBU Real User Acquisition Dashboard

Generated: 2026-05-14T11:37:50+09:00
Excluded: neogenesis, toolpick, ur-wrong

## Source Integrity

- GSC source: data\sbu-growth\gsc-all-sbu-latest.json
- GSC generatedAt: 2026-05-14T11:30:13+09:00
- PostHog source: data\sbu-growth\posthog-traffic-latest.json
- GA4 source: logs\ga4_result.json

## Priority Table

| Rank | Site | Market | Stage | Score | PH Users | PH PV | GA4 7d Users | GSC Opps | GSC Impr | Top Query |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | SellKit | global | capture-now | 704.3 | 17 | 16 | 0 | 10 | 281 | printful alternatives |
| 2 | ReviewLab | korea | capture-now | 388.9 | 51 | 62 | 0 | 10 | 74 | tabwee 태블릿 후기 |
| 3 | K-OTT | korea | distribution-validation | 156.7 | 40 | 55 | 11 | 0 | 0 | - |
| 4 | CraftDesk | global | distribution-validation | 148.5 | 43 | 42 | 0 | 2 | 4 | rapid prototyping user interface |
| 5 | DeployStack | global | distribution-validation | 120.1 | 37 | 33 | 0 | 2 | 4 | kubernetes resource optimization platforms |
| 6 | WhyLab | global | productize-before-growth | 67.9 | 15 | 15 | 0 | 2 | 4 | whylab |
| 7 | EthicaAI | global | productize-before-growth | 62.5 | 25 | 25 | 0 | 0 | 0 | - |
| 8 | AIForge | global | productize-before-growth | 40.2 | 6 | 6 | 0 | 2 | 2 | ai security for dev |
| 9 | FinStack | global | productize-before-growth | 16 | 6 | 5 | 0 | 0 | 0 | - |

## Action Queue

### SellKit

- lane: ecommerce sellers
- stage: capture-now
- action: Exploit proven GSC intent: Printful alternatives, Stripe pricing, Printful pricing, and Gumroad review.
- action: Add Stripe fee and POD margin calculators, then seed ecommerce/POD communities with tracked URLs.

### ReviewLab

- lane: Korean product review
- stage: capture-now
- action: Rewrite Korean title/description/H1 for comparison and purchase-review intent.
- action: Prioritize Naver Search Advisor checks and Korean FAQ/pros-cons/spec tables.
- measurement warning: PostHog shows recent users but GA4 7d is zero; verify property/hostname filtering and data freshness.

### K-OTT

- lane: Korean OTT decision
- stage: distribution-validation
- action: Build OTT price, plan, and monthly-watch decision hubs in Korean.
- action: Track Naver/Google Korean queries separately from owned/direct traffic.
- measurement warning: Traffic exists without search opportunity; validate referral/direct source and bot filtering.

### CraftDesk

- lane: design/product workflow
- stage: distribution-validation
- action: Publish a Figma Community template or UX rapid-prototyping checklist.
- action: Create search pages around rapid prototyping, UI review, and design QA workflows.
- measurement warning: PostHog shows recent users but GA4 7d is zero; verify property/hostname filtering and data freshness.

### DeployStack

- lane: developer/devops
- stage: distribution-validation
- action: Ship a CI/CD YAML generator or preview-environment cost checklist.
- action: Distribute via DEV, GitHub templates, and HN only when the artifact is directly usable.
- measurement warning: PostHog shows recent users but GA4 7d is zero; verify property/hostname filtering and data freshness.

### WhyLab

- lane: research/product proof
- stage: productize-before-growth
- action: Treat current pages as credibility assets until a concrete user job is defined.
- action: Avoid broad MAU acquisition spend before a repeatable tool or decision workflow exists.

### EthicaAI

- lane: AI ethics research
- stage: productize-before-growth
- action: Productize one practical artifact such as an AI risk checklist or model evaluation worksheet.
- action: Use research pages for authority, not direct MAU scaling, until activation is measurable.
- measurement warning: PostHog shows recent users but GA4 7d is zero; verify property/hostname filtering and data freshness.

### AIForge

- lane: AI builders
- stage: productize-before-growth
- action: Ship an agent stack selector or evaluation checklist as a tryable tool.
- action: Distribute through GitHub, AI builder communities, and Product Hunt only after the demo is usable.

### FinStack

- lane: finance ops
- stage: productize-before-growth
- action: Narrow the product promise to Stripe reconciliation, invoice ops, or SaaS finance templates.
- action: Publish one practical calculator/template before adding more generic finance posts.

