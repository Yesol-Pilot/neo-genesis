# SBU Autonomous Growth Rule

> Effective: 2026-04-26
> Owner instruction: "모두 자율주행되도록 규칙 변경 하고 진행해"
> Scope: Neo Genesis SBU content, SEO, analytics, GitHub, Vercel, sitemap, indexing, and live verification operations.

## Decision

SBU growth operations run in autonomous mode by default. Agents do not stop for repeated confirmation when the work is needed to keep SBU sites publishing, deployable, measurable, indexable, and recoverable.

## Standing Approval

The owner grants standing approval for agents to perform the following SBU operations when they pass the gates below:

1. Generate, edit, commit, and push SBU content files, SEO files, sitemap/LLM files, analytics code, and publishing pipeline code.
2. Run builds, tests, lint checks, growth audits, live smoke checks, sitemap checks, and browser/API verification.
3. Deploy SBU sites to Vercel production.
4. Update SBU-scoped Vercel environment variables required for autonomous growth operations.
5. Rotate or replace broken SBU-scoped automation credentials when the credential source is already owned by the owner and the target scope is limited to the intended SBU or `Yesol-Pilot` repository.
6. Trigger scheduled or manual publishing routes, indexing hooks, revalidation routes, and internal SBU automation endpoints.
7. Repair SBU cron, GitHub commit, content generation, sitemap, and live publishing pipelines.

## Required Gates

Autonomous SBU operations must satisfy all relevant gates:

1. Confirm the target repository remote is under `Yesol-Pilot/`.
2. Confirm `git config user.email` is `dpthf1537@gmail.com`.
3. Confirm Vercel `.vercel/project.json` projectId/orgId/projectName before production deploys or env changes.
4. Never print, log, commit, or paste secret values. Report only sanitized presence, length, status, and validation result.
5. Do not commit `.env*`, service-account key files, token files, password files, or downloaded Vercel env files.
6. Prefer project-scoped or repo-scoped tokens over broad tokens.
7. After any credential or env update, verify with the real operation it was meant to fix.
8. After deploy, verify public URL, critical API route, blog listing, article detail, sitemap, and analytics/indexing surface where applicable.
9. Leave a commit hash, deployment URL/ID, and residual risk summary.

## Boundaries

This rule does not authorize:

1. Spending money, changing billing, changing legal contracts, changing owner identity, or changing organization-level account ownership.
2. Deleting production data, truncating tables, destroying backups, deleting repositories, or deleting branches.
3. Sending bulk external messages to users/customers.
4. Moving personal/legal/financial documents.
5. Publishing knowingly false claims, fake E-E-A-T, fake reviews, or non-disclosed paid/affiliate claims.

## SBU Publishing Success Definition

A file-based SBU blog publish is successful only when all are true:

1. The new content exists in the repository under the live content source, usually `content/blog/*.mdx`.
2. The content is committed and pushed to the correct `Yesol-Pilot` SBU repository.
3. The Vercel production deployment includes the new route.
4. The live blog listing shows the new date/slug.
5. The live article returns HTTP 200 and contains the expected title/date.
6. The live sitemap contains the new URL.

DB-only success is not sufficient for file-based SBU blogs.

## Recovery Priority

When an SBU falls behind:

1. Restore live content freshness first with a valid MDX commit and production deploy.
2. Fix the automation path so future posts are not manual.
3. Validate credentials and env variables without exposing secrets.
4. Add monitoring or a scheduled check that alerts when the latest live post is stale.
