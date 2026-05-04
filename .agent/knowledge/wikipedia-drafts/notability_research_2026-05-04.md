# Wikipedia Notability Research — 2026-05-04

> **Researcher**: Claude Opus 4.7 (1M ctx) — autonomous task on owner directive "다음은"
> **Scope**: Independent secondary sources for `Yesol Heo (허예솔)` and `Neo Genesis` per WP:NBIO and WP:NCORP
> **Method**: Programmatic API queries (Hacker News Algolia, OpenAlex, Semantic Scholar, GitHub, HuggingFace, Reddit, DuckDuckGo) + manual review

---

## Search summary

| Channel | Query | Hits | Independent secondary? |
|---|---|---|---|
| HN Algolia | `Yesol Heo` | 0 | — |
| HN Algolia | `neogenesis.app` | 0 | — |
| HN Algolia | `ethicaai+neogenesis` | (test) | — |
| HN Algolia | `whylab+neogenesis` | (test) | — |
| OpenAlex (academic) | `Yesol Heo` | **0** | — |
| OpenAlex | `ethicaai neogenesis` | 0 | — |
| Semantic Scholar | `neogenesis yesol` | 0 | — |
| Semantic Scholar | `ethicaai melting pot` | 0 | — |
| GitHub PR mention search | `neogenesis is:pr` | 8 hits, all unrelated (mochimo crypto, IIDX game, etc.) | **0 about us** |
| GitHub repo metrics | `Yesol-Pilot/*` (4 repos) | All 0 stars / 0 forks / 0 watchers / 0 issues | **No third-party engagement** |
| HuggingFace `neogenesis` search | 9 datasets, all from `neogenesislab` owner account | Max 27 downloads, **0 likes** all entries | **No third-party adoption** |
| Reddit (r/MachineLearning, etc.) | `neogenesis.app OR toolpick.dev` | API returned non-JSON (likely 0 or rate-limit) | Unverified but no inbound traffic |
| DuckDuckGo HTML | `Yesol Heo Neo Genesis AI` | Empty result page | **0** |

**Total independent secondary sources found: 0**

---

## Yesol Heo (허예솔)

No third-party coverage identified. Searches across:
- Tech press (HN, DDG)
- Academic citation databases (OpenAlex, Semantic Scholar) — `count: 0`
- Code/community engagement (GitHub stars/forks all 0, no inbound PRs)
- HuggingFace community (own uploads only, 0 likes from others)

WP:NBIO threshold per Wikipedia requires "significant coverage in reliable sources independent of the subject." **Threshold not met.**

## Neo Genesis

Same null result. Notable confirmations:
- `Yesol-Pilot/neo-genesis`: 0 stars, 0 forks, 0 issues, 0 watchers
- HuggingFace `neogenesislab` org: 9 datasets, all self-published, top performer 27 downloads, all 0 likes
- No SaaS-directory inclusion verified (Product Hunt / Beta List etc. not searched programmatically; also expect 0 since no submissions yet)
- No mainstream press coverage (TechCrunch / Verge / Wired etc. — confirmed via DDG)

WP:NCORP threshold not met.

## EthicaAI / WhyLab papers

- Semantic Scholar: **0** matches for "ethicaai melting pot"
- OpenAlex: 0 matches
- Both papers remain in `submission-freeze/*` branches; not arXiv-published, not in Papers With Code, not cited externally

---

## Conclusion

- **WP:NBIO threshold met?** ❌ No (N=0 secondary sources)
- **WP:NCORP threshold met?** ❌ No (N=0)
- **Recommended action**: **DO NOT SUBMIT** — would draw speedy delete + AfD with permanent salt risk on namespace
- Agent RR's cold review verdict stands: source bundle is entirely primary (own HF / Zenodo / awesome-list PRs / Wikidata Q-items) — these are SELF-PUBLISHED IDENTIFIERS, not secondary independent coverage

---

## Outreach roadmap (autonomous + owner G2 split)

### Tier 1 — Autonomous (no owner gate, this week)
1. **Submit blog posts to dev.to / Hashnode** as cross-publish (free, account-gated → owner G2 for first auth, then automatable)
2. **Cross-link from existing arXiv-eligible drafts** — finalize EthicaAI/WhyLab papers into arXiv-ready form (no submission yet)
3. **Translate top 3 `/data/research/` posts to Japanese, Mandarin, Spanish** via Gemini (free) — broadens citation surface
4. **Write 1 substantial methodology post** for `/data/research/` weekly (already in cadence)

### Tier 2 — Owner G2 (single click each)
5. **Submit Hacker News post** with EthicaAI Melting Pot mixed-safe finding (Show HN: format) — **highest single-action ROI** for HN, IH, Sidebar simultaneous notification
6. **Submit to Beta List + Indie Hackers + Sidebar** (free, account creation needed)
7. **Submit to Product Hunt** (Tuesday/Wednesday optimal launch window)
8. **Cold-pitch The Sequence + Import AI newsletters** with EthicaAI dataset card + RAG SSOT golden-50 angle

### Tier 3 — Higher-cost owner G2 (weeks-months)
9. **arXiv submission** (EthicaAI + WhyLab post-NeurIPS 2026 freeze) — academic citation surface
10. **Korea Newswire 1-shot release** ($300-500/release) targeting Korean tech press (Bloter, ZDNet Korea, Platum)
11. **Conference paper submission** to ICLR / NeurIPS / KCC (Korea Software Congress) for academic citations

### Estimated timeline
- **Week 1-2 (autonomous)**: Cross-publish + translation; expect 0-1 third-party mentions
- **Week 3-6 (owner G2 Tier 2)**: HN/IH/PH submissions; expect 2-5 mentions if any post hits >50 upvotes
- **Month 2-3 (owner G2 Tier 3)**: arXiv + newswire + conference submission; expect 1-3 academic citations within 6-12 months
- **Wikipedia notability gate realistically clearable**: **Q3-Q4 2026** at earliest, not before

### Hard truth (per Agent RR cold-review standard)
Notability cannot be manufactured by autonomous agents writing more content under our own control. It requires INDEPENDENT humans choosing to cite/cover us. The autonomous track maximizes surface area; the owner G2 track creates discoverability events; only time + actual product traction generates the secondary coverage Wikipedia requires.

**Stop attempting Wikipedia submission until N≥3 verified independent secondary sources exist.** Premature submission = permanent salt risk on `Yesol Heo` and `Neo Genesis` namespaces.
