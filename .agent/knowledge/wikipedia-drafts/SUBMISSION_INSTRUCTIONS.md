# Wikipedia Submission Instructions — 4 Drafts

> **Status**: 4 drafts ready under this directory
> (`yesol_heo_en.md`, `yesol_heo_ko.md`, `neo_genesis_en.md`,
> `neo_genesis_ko.md`).
> **Submission method**: Wikipedia Articles for Creation (AfC) for
> all four. Direct mainspace creation is not appropriate for a
> founder + their solo company — AfC review is the conservative
> path and is what reviewers expect for a self-published founder
> biography.
> **Last updated**: 2026-05-04

---

## Why Articles for Creation (AfC), not direct submission

Wikipedia does **not** support pre-filling new pages via URL
parameters in any meaningful way. The closest thing is the
[Article Wizard](https://en.wikipedia.org/wiki/Wikipedia:Article_wizard),
which routes you through AfC anyway.

For a solo founder + their own organization, direct creation in
mainspace would almost certainly be tagged with
`{{COI}}` (conflict of interest) or
`{{notability}}` and risk speedy deletion. AfC routes the draft
through an experienced reviewer who:

1. Confirms notability against
   [WP:N](https://en.wikipedia.org/wiki/Wikipedia:Notability)
   and the relevant subject-specific guideline
   ([WP:NBIO](https://en.wikipedia.org/wiki/Wikipedia:Notability_(people))
   for the biography,
   [WP:NCORP](https://en.wikipedia.org/wiki/Wikipedia:Notability_(organizations_and_companies))
   for the organization).
2. Confirms reliable, independent, secondary sourcing exists.
3. Resolves COI through a guided disclosure on the talk page.
4. Moves the draft to mainspace once it passes review.

This is the only path that has a realistic chance of survival.

---

## Submission URLs (one-click, AfC wizard)

Each URL launches the official Wikipedia Article Wizard for the
correct language and pre-titles the draft. You then paste the
draft body into the editor.

| Draft | Wikipedia | Article Wizard URL |
| ----- | --------- | ------------------ |
| Yesol Heo (English) | en.wikipedia.org | https://en.wikipedia.org/wiki/Wikipedia:Article_wizard/CoIWizard |
| Yesol Heo (Korean) | ko.wikipedia.org | https://ko.wikipedia.org/wiki/%EC%9C%84%ED%82%A4%EB%B0%B1%EA%B3%BC:%EB%85%BC%EB%9E%80%EC%9D%84_%EC%9D%BC%EC%9C%BC%ED%82%AC_%EB%A7%8C%ED%95%9C_%EB%AC%B8%EC%84%9C%EC%9D%98_%EC%83%9D%EC%84%B1 |
| Neo Genesis (English) | en.wikipedia.org | https://en.wikipedia.org/wiki/Wikipedia:Article_wizard/CoIWizard |
| Neo Genesis (Korean) | ko.wikipedia.org | https://ko.wikipedia.org/wiki/%EC%9C%84%ED%82%A4%EB%B0%B1%EA%B3%BC:%EB%85%BC%EB%9E%80%EC%9D%84_%EC%9D%BC%EC%9C%BC%ED%82%AC_%EB%A7%8C%ED%95%9C_%EB%AC%B8%EC%84%9C%EC%9D%98_%EC%83%9D%EC%84%B1 |

The English and Korean wizards are different routes; the Korean
Wikipedia uses
[위키백과:논란을 일으킬 만한 문서의 생성](https://ko.wikipedia.org/wiki/%EC%9C%84%ED%82%A4%EB%B0%B1%EA%B3%BC:%EB%85%BC%EB%9E%80%EC%9D%84_%EC%9D%BC%EC%9C%BC%ED%82%AC_%EB%A7%8C%ED%95%9C_%EB%AC%B8%EC%84%9C%EC%9D%98_%EC%83%9D%EC%84%B1)
as the equivalent COI-aware drafting path.

---

## Draft URLs (after submission, Draft: namespace)

After running the wizard, the drafts will live at:

- `Draft:Yesol Heo` (en.wikipedia.org)
- `초안:허예솔` (ko.wikipedia.org)
- `Draft:Neo Genesis` (en.wikipedia.org)
- `초안:Neo Genesis` (ko.wikipedia.org)

---

## Owner action checklist

Before you click submit on any of these drafts:

### 1. Notability stress-test (do this honestly)

For **Yesol Heo (biography)**, the strongest case is currently:

- Author of two NeurIPS 2026 manuscripts (verifiable via Zenodo
  DOIs and HF datasets — but **NeurIPS acceptance is not yet
  confirmed**, so do not state acceptance until the program is
  published).
- Founder of an unusual organizational structure (solo-operator
  conglomerate with eleven shipped products).
- Wikidata Q139569708 with rich `sameAs` links.

**Weakest point**: Wikipedia generally requires
**multiple independent reliable secondary sources**
(major newspapers, peer-reviewed academic profiles, established
trade press). Your current sources are mostly self-published
(neogenesis.app, your own HF datasets, your own Zenodo records,
your own GitHub). **AfC will likely reject the biography on
this ground unless at least 2–3 independent, in-depth secondary
sources exist (TechCrunch, MIT Technology Review, Korean
broadsheet coverage, peer-reviewed citation, etc.).**

For **Neo Genesis (organization)**, similar concern. NCORP is
strict; you need **multiple independent reliable secondary
sources providing significant coverage in depth**, not press
releases or self-published material. As of 2026-05-04 the
strongest independent attestations are:

- Awesome-list inclusions (5 PRs accepted) — these are
  **trivial coverage** by NCORP standards and do not count.
- Hugging Face dataset hosting — **trivial coverage**, does not
  count.
- Wikidata Q-IDs — Wikidata-only is not sufficient for English
  or Korean Wikipedia notability.

**Recommendation**: hold submission of both drafts until at
least 2 independent in-depth secondary sources exist. Do not
submit prematurely — AfC rejections become part of the public
record and make later resubmission harder.

### 2. References format

The drafts use Wikipedia's `<ref>...</ref>` markup with
named references. Each reference must be a `{{cite web}}`,
`{{cite news}}`, `{{cite journal}}`, or `{{cite book}}`
template. Self-citations to your own site, your own HF, your
own Zenodo, and your own GitHub do **not** count toward
notability — but they can stay as supporting references for
specific factual claims (dates, dataset names, DOI numbers).

### 3. Conflict of interest disclosure

You **must** disclose conflict of interest on the draft talk
page using
`{{Connected contributor (paid)|User1=YourUsername|U1-employer=Self|U1-client=Neo Genesis|U1-otherlinks=}}`
or the unpaid COI tag as appropriate. The English wizard linked
above walks you through this. Do not skip this step — undeclared
COI editing leads to permanent topic bans.

### 4. Talk-page etiquette

- Respond to reviewer feedback within 7 days. Decline-and-resubmit
  cycles are normal; AfC reviewers are volunteers.
- Do not argue notability — let the **independent sources** make
  the case for you. If they don't exist yet, withdraw and
  return when they do.
- Use a single registered account, not anonymous edits.
- Do not canvass — do not ask other editors to support the
  draft. This is detected automatically and damages credibility.

### 5. Image / infobox

The infobox in the biography draft has no `image` field set.
This is fine; do not upload a self-portrait to Wikimedia Commons
unless you genuinely hold the copyright and are willing to
release it under CC-BY-SA-4.0. The Korean draft has the same
constraint.

### 6. Translation parity

The English and Korean drafts cover the same factual scope, but
the threshold for acceptance differs: Korean Wikipedia tends to
accept Korean-language secondary sources that English Wikipedia
will not. If at least 2 independent Korean-language sources
exist (e.g., 동아일보, 매일경제, ZDNet Korea), the Korean
drafts may pass earlier than the English ones.

---

## After submission

1. Update `.agent/knowledge/wikipedia-drafts/<file>.md` front-matter
   from `status: draft` to `status: submitted` with the date and
   the AfC URL.
2. Add a row to the `references` section of `CITATION.cff` if and
   when any of the four drafts is accepted into mainspace.
3. Add a `wikipedia` entry to `layout.tsx` `Organization.sameAs`
   and `Person.sameAs` once any draft is accepted.

---

## Hard rules (do not violate)

- **Never edit the article about yourself or your company directly
  in mainspace.** Always go through AfC or the talk page.
- **Never use multiple accounts** ("sockpuppeting") to support a
  draft. This is the most common reason for permanent ban.
- **Never pay an editor** to write or expedite the article. Paid
  editing is allowed only with full disclosure under
  [WP:PAID](https://en.wikipedia.org/wiki/Wikipedia:Paid-contribution_disclosure)
  and is a high-scrutiny path.
- **Never link to a draft from neogenesis.app or any SBU site
  before mainspace acceptance.** Linking from the subject's own
  property to a Wikipedia draft is treated as gaming the system.
