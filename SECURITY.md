# Security Policy

Neo Genesis takes security and responsible disclosure seriously. This file documents how to report security issues, what we promise in return, and the scope of what is in-scope versus out-of-scope.

This document is the canonical companion to [`/.well-known/security.txt`](https://neogenesis.app/.well-known/security.txt) (RFC 9116) hosted on the production domain.

## Reporting a vulnerability

Please report security vulnerabilities privately. Do not open a public GitHub issue.

Preferred channels (in order):

1. **GitHub Security Advisory** — [open a private advisory](https://github.com/Yesol-Pilot/neo-genesis/security/advisories/new). This is the preferred path because it integrates with our patch workflow.
2. **Email** — `help@neogenesis.app` with subject prefix `[SECURITY]`.

When reporting, please include:

- A description of the vulnerability and the affected component (subdomain, repository path, dataset, API endpoint).
- Reproduction steps or proof-of-concept (curl, screenshot, or minimal code).
- Suspected impact (data exposure, account takeover, service disruption, supply-chain risk).
- Whether you have already disclosed the issue to any third party.

## What we promise

- **Acknowledgement within 72 hours** of receiving a credible report.
- **Initial triage within 7 days**, including severity assessment using a CVSS-style framework.
- **No legal action** against good-faith security research conducted under this policy.
- **Public credit** in the changelog entry for the fix, unless the reporter prefers anonymity.

## Scope

In-scope assets:

- The `Yesol-Pilot/neo-genesis` repository and its first-party content.
- The `neogenesis.app` production domain and its subdomains operated by Neo Genesis (toolpick, reviewlab, kott, whylab, ethicaai, finstack, aiforge, sellkit, deploystack, craftdesk, ur-wrong).
- Datasets published under [`neogenesislab` on Hugging Face](https://huggingface.co/neogenesislab).
- The Cloudflare Worker, Vercel deployments, and Supabase tables that back the production surfaces above.

Out of scope:

- Third-party services we depend on (please report directly to those vendors).
- Issues that require physical access to the operator's devices.
- Self-XSS that requires the operator to paste attacker-supplied content into their own browser console.
- Denial-of-service via excessive request volume against rate-limited endpoints.
- Reports based purely on theoretical CVE matches with no exploitability path on our deployments.

## Disclosure timeline

The default coordinated disclosure window is **90 days** from the date a fix is shipped. We may publish earlier with the reporter's agreement, or extend if the fix requires a coordinated downstream rollout.

## Hall of fame

Security researchers who report valid vulnerabilities are listed (with consent) in [`CHANGELOG.md`](./CHANGELOG.md) under the corresponding release.

## Cryptographic signing

Releases are signed with the operator's GitHub commit-signing key. The corresponding public key is published on the [operator's GitHub profile](https://github.com/Yesol-Pilot.gpg).

## Last reviewed

2026-05-04 by the project operator. Next review: 2026-08-04.
