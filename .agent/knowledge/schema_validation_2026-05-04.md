# Schema Validation Report — 2026-05-04

Validator: `D:/00.test/tmp_validator.py` (custom Python; rules drawn from Schema.org required-property contracts and Google rich-result eligibility checks). Methodology: HTTPS GET each URL, extract every `<script type="application/ld+json">` block, JSON-parse, recursively validate each typed node against required-property table, with skip-rules for `@id` reference nodes and short-form nested `Organization` / `Person`.

## Summary

| Metric | Pre-fix | Post-fix |
|---|---|---|
| URLs validated | 48 | 48 |
| HTTP 200 | 48 | 48 |
| JSON-LD blocks | 404 | 404 |
| JSON parse errors | 0 | 0 |
| **Errors (real, post-filter)** | **200** | **0** |
| Warnings | 57 | 57 |

All 48 live URLs return HTTP 200 and parse cleanly. After fixes, **zero errors remain**.

## Critical errors fixed

| URL pattern | Schema | Issue | Fix |
|---|---|---|---|
| `/` (homepage) | `Organization.publication[]` `ScholarlyArticle` × 2 | Missing `headline`, `datePublished`, `publisher` | Added `headline` + `datePublished: 2026-04-15` + `publisher: {@id ref}` to both NeurIPS submissions. (`src/landing/src/app/layout.tsx:265–292`) |
| `/wikipedia-drafts/{4 slugs}` | `Article` (block 6) | Missing `datePublished`, `image` | Added `datePublished` (= `lastUpdated`) + `image` (1200×630 og.png ImageObject). (`src/landing/src/app/wikipedia-drafts/[slug]/page.tsx:120–139`) |

## Warnings (acceptable, not blocking rich results)

- 57 × `Person.sameAs <3 entries` — these are **nested** Person nodes (e.g., `Article.author`, `award.recipient`) that intentionally carry only `name` because they reference a fully-defined `#founder` Person elsewhere via context. Schema.org allows short-form nested entities; only the canonical `#founder` node needs full `sameAs`. **No action.**

## URL inventory (48)

- `/`, `/about`, `/blog`, `/data/research`, `/press`, `/awards`, `/wikipedia-drafts`, `/faq` (8 surfaces)
- 10 blog posts under `/blog/<slug>`
- 10 research papers under `/data/research/<slug>`
- 11 SBUs under `/sbu/<slug>`
- 5 press releases under `/press/<slug>`
- 4 wikipedia drafts under `/wikipedia-drafts/<slug>`

## Per-surface breakdown (post-fix)

| Surface | Blocks | Errors | Warnings | Notes |
|---|---|---|---|---|
| Homepage | 11 | 0 | 0 | 13 sameAs URLs on `Organization` |
| /about | 10 | 0 | 0 | Person + Organization full schema |
| /awards | 8 | 0 | 16 | Multiple awards with award-recipient Person stubs (warning only) |
| /blog | 6 | 0 | 0 | CollectionPage + ItemList |
| /blog/<slug> × 10 | 8–9 | 0 | 1 | Each: BlogPosting + BreadcrumbList + sidebar refs |
| /data/research | 7 | 0 | 0 | ItemList |
| /data/research/<slug> × 10 | 8 | 0 | 1 | ScholarlyArticle + Dataset + BreadcrumbList |
| /faq | 7 | 0 | 0 | FAQPage + Question/acceptedAnswer pairs valid |
| /press | 8 | 0 | 0 | CollectionPage |
| /press/<slug> × 5 | 8 | 0 | 1 | NewsArticle/PressRelease |
| /sbu/<slug> × 11 | 9 | 0 | 0 | SoftwareApplication / Organization |
| /wikipedia-drafts | 8 | 0 | 0 | ItemList + WebPage |
| /wikipedia-drafts/<slug> × 4 | 9 | 0 | 2 | Article (after fix) + WebPage with Person/Org mainEntity |

## Validation rules applied

- Required-property contracts: `Article`/`BlogPosting`/`ScholarlyArticle` (headline, datePublished, author, publisher, image), `FAQPage` (mainEntity), `Organization` (name, url), `WebSite` (name, url), `BreadcrumbList` (sequential positions), `Dataset` (name, description), `PressRelease` (headline, datePublished), `WebPage` (name, url), `ItemList` (itemListElement), `CollectionPage` (name, url).
- Date format: ISO 8601 (`^\d{4}-\d{2}-\d{2}(T...)?$`) with optional time/zone.
- Image dimensions: warn if `<1200×630` on Article-like.
- BreadcrumbList: positions must start at 1 and increment.
- `@context`: must be `https://schema.org`.
- `@id`-reference shortcut: nodes with `@id` and only `{name, url, sameAs, image}` are treated as references, not redeclarations.

## Files modified

1. `src/landing/src/app/layout.tsx` — added `headline`, `datePublished`, `publisher` to `Organization.publication[]` ScholarlyArticles.
2. `src/landing/src/app/wikipedia-drafts/[slug]/page.tsx` — added `datePublished` + `image` (ImageObject 1200×630) to `Article` schema.

## Build + deploy verification

- `npm run build` passed (Next.js 16.1.6, all 39 SSG routes prerendered).
- `npx vercel --prod --yes` deployed to production; aliased to `https://neogenesis.app` (29 s).
- Post-deploy re-validation: **0 errors / 0 parse errors / 48 URLs HTTP 200** across all surfaces and nested types.

## Recommended follow-ups (low priority)

- Optionally enrich nested `Person` nodes inside `Article.author` and `Award.recipient` with one `sameAs` URL (Wikidata `#founder` Q-ID) to silence the 57 warnings — **purely cosmetic**, no rich-result impact.
- The Yandex IndexNow ping succeeds (202) but Bing/IndexNow.org return 403 (`UserForbiddedToAccessSite`); track separately under indexing-key validation, unrelated to Schema.org.
