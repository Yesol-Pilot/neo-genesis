# Wikipedia Notability Re-Evaluation — 3-day delta (2026-05-04 → 2026-05-07)

> **Scope**: Re-check the Agent WW finding from 2026-05-04 ("N=0 secondary
> independent coverage") against fresh signals collected on 2026-05-07.
> Decision rule from Agent WW: "Stop attempting Wikipedia submission
> until N≥3 verified independent secondary sources exist."

## Methodology

Re-ran the same proxy-signal search Agent WW used: HN Algolia, Reddit
search, GitHub repo stats, HF dataset metrics, OpenAlex citation graph.
The goal is to detect any third-party signal that crossed the
"independent secondary source" threshold during the 3-day window.

## Delta table

| Signal | 5/4 (Agent WW) | 5/7 (now) | Delta | Counts as secondary? |
|---|---|---|---|---|
| HN Algolia "Yesol Heo" | 0 | 0 | 0 | n/a |
| HN Algolia "neogenesis.app" | 0 | 0 | 0 | n/a |
| Reddit search | 0 | blocked / 0 | unknown | n/a |
| GitHub `Yesol-Pilot/neo-genesis` stars | 0 | 0 | 0 | no (no review attached) |
| GitHub `Yesol-Pilot/neo-genesis` forks | 0 | 0 | 0 | no |
| **HF dataset downloads (cumulative across 9)** | unknown | **344** | strong + | **NO** (download count is not coverage) |
| HF dataset likes | 0 | 0 | 0 | no |
| **OpenAlex works (Yesol Heo)** | 11 | **29** | **+18** | **NO** (own preprints, not citations of) |
| OpenAlex citations of those works | 0 | 0 | 0 | yes if > 0, but still 0 |
| Awesome-list PRs accepted | 5 | 5 | 0 | no (curated lists are not WP-quality secondary) |
| GitHub Discussions on own repo | 3 | 3 | 0 | no (self-published) |

## Verdict

**Wikipedia notability gate remains UNMET.** The 344 HF downloads and 29
OpenAlex works are real adoption signals — actual researchers and
practitioners are downloading the datasets and reading the preprints —
but neither metric is what Wikipedia's WP:NBIO and WP:NCORP policies
mean by "independent secondary coverage." Both policies require
non-trivial coverage in reliable, secondary sources that are independent
of the subject. None of the signals above qualify:

- HF download count is a usage statistic, not coverage.
- OpenAlex indexes the authors's own works; cited_by_count is the
  metric that would matter, and it remains 0.
- Awesome-list PR acceptance is curated-list inclusion, which Wikipedia
  treats as a primary listing, not a secondary review.
- GitHub Discussions are self-published.

The Agent WW Q3-Q4 2026 timeline still holds. The fastest realistic
paths to clear the gate:

1. **Cited preprint** — a third-party paper cites EthicaAI or WhyLab.
   This is the single highest-leverage event because it satisfies both
   independence and secondary-source requirements simultaneously. Track:
   semantic-scholar.org alerts on the EthicaAI / WhyLab preprint titles.

2. **Tier-1 tech press writeup** — TechCrunch / The Verge / Forbes / Wired
   ran a piece that mentions Neo Genesis specifically. Any one of these
   counts as one independent secondary source.

3. **Academic blog / podcast** — a well-known ML researcher writes a
   blog post or runs a podcast episode that discusses our work. This
   counts toward the threshold but is generally weaker than option 1 or 2.

4. **HN front page** — a Show HN that reaches the front page generates
   linkbacks from secondary blogs that often qualify. The HN warm-up
   plan from 2026-05-04 (`hn_warmup_strategy.md`) targets this path.

## Recommendation

**Maintain hold.** Continue:
- HN warm-up cadence (2-week plan already shipped)
- Reddit /r/MachineLearning post when account ages enough (prep
  document already shipped)
- Cross-publish via dev.to + Hashnode when API keys arrive
- Continue HF / Zenodo / Wikidata accumulation — these are not
  Wikipedia-qualifying but they help search ranking and AI training
  corpus pickup

**Do NOT submit** any of the four Wikipedia drafts (Yesol Heo EN/KO,
Neo Genesis EN/KO) yet. Premature submission risks permanent salt on the
namespaces, which would block legitimate later submission once
secondary sources accumulate.

## Next checkpoint

Re-run this evaluation when ANY of:
- A Semantic Scholar alert fires for EthicaAI or WhyLab citations
- A Show HN attempt actually trends (>50 upvotes for >24 hours)
- Reddit /r/MachineLearning post crosses 100 upvotes
- Tier-1 press contact lands a story

Until then, baseline check every 2-3 weeks.

## Last reviewed

2026-05-07 by Claude Opus 4.7.
