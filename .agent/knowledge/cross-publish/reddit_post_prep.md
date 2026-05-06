# Reddit Submission Pack — /r/MachineLearning + /r/programming

> Created: 2026-05-06
> Owner action time: 15-20 min total
> Backup channel for HN warm-up window (HN Show HN gated for new accounts)

---

## Why Reddit (vs HN right now)

- HN gated owner's account on first Show HN (warm-up needed, see `hn_warmup_strategy.md`)
- /r/MachineLearning has minimal account-age gate (1 week + email verified)
- /r/MachineLearning audience: ~3M subscribers, weighted toward research, dataset releases, methodology
- Single post can drive 10K+ traffic in 24-48h if it lands

---

## Recommended Post 1 (HIGHEST PRIORITY)

### Subreddit: /r/MachineLearning

### Flair: `[R] Research`

### Title (max 300 chars):
```
[R] EthicaAI: 510-seed Melting Pot test of Sen's rationality theory across multi-agent RL substrates (NeurIPS 2026 submission, CC-BY-4.0 dataset)
```

### Body:
```
TL;DR: Solo-operator NeurIPS 2026 submission. We ran 510 evidence rows
across DeepMind Melting Pot multi-agent RL substrates to test whether
Amartya Sen's rationality theory (specifically the "boundary-consistent"
formulation) survives non-cooperative game-theoretic pressure.

Methodology
- Mixed-Safe Coin Game: 160 seeds × 200 episodes (selfish agents vs.
  MACCL-equipped agents)
- Fishery Nash Trap: 300 seeds × 300 episodes (commons depletion)
- Statistics: Welch's t-test (unequal variance), bootstrap 95% CI,
  Cohen's d effect size, per-shard provenance tracking

What we found (honestly):
- Coin Game: 22.08% selfish survival vs 78.10% MACCL survival,
  delta +56 points, CI95 [54.31, 57.73], d=7.15
- Fishery: phi1=0.7 reaches 87.7% survival with positive harvest
  welfare; phi1=1.0 reaches 100% only at zero-harvest limit (Pareto
  trade-off documented)
- Parallel WhyLab causal inference substrate hit a null result on
  SWE-bench-style problems (67 problems × 402 Docker ground-truth
  episodes) - we report this honestly in the writeup

Framing (please read before commenting "this isn't validation"):
We do NOT claim Sen's theory is validated by this. We frame the
results as "boundary-consistent evidence" - the theory survives
specific substrates we tested, but the substrate set is not native
third-party (DeepMind designed Melting Pot for cooperation research,
which biases toward cooperative solutions). Independent replication
across native third-party TPSD substrates remains future work.

Open data (CC-BY-4.0):
- HuggingFace: huggingface.co/datasets/neogenesislab/ethicaai-mixed-safe-evidence
- Zenodo DOI: doi.org/10.5281/zenodo.20018466
- Full writeup: neogenesis.app/data/research/ethicaai-melting-pot-mixed-safe

Built solo. $0 infrastructure cost on Vercel + HuggingFace free tiers
+ DeepMind Melting Pot open source + Cloudflare. Happy to discuss
substrate selection critiques, the Sen-mapping formulation, the
parallel WhyLab null result, or the Pareto-frontier framing.
```

### When to post:
- Tuesday 09:00-11:00 EST (research community most active)
- Avoid weekends (low engagement)

### First comment to add (within 30 min):
```
Author here. Quick FAQ for what people are likely to ask:

Q: Why "boundary-consistent" instead of "validated"?
A: Because all three substrates were either author-designed or
adapted from existing research, which means the substrate selection
itself biases toward outcomes consistent with the hypothesis. Native
third-party TPSD replication is the proper validation step - we just
don't have it yet.

Q: Why is the WhyLab null result here?
A: Same author, same operating model. Including the null result is
honest - we're not pre-selecting positive findings.

Q: How is this funded?
A: Solo operator, no external funding. The compute came from a single
GCP VM + a 16-core home server + a Mac Studio. Total monthly cost
approximately $50.

Q: Can I reproduce this?
A: Yes, the dataset is CC-BY-4.0 and the code is on GitHub at
github.com/Yesol-Pilot/neo-genesis. The reproduction guide is in
docs/how-to.
```

---

## Recommended Post 2 (Secondary)

### Subreddit: /r/programming

### Title:
```
Running 11 SaaS products as a solo founder with one autonomous AI system (HIVE MIND, 2026 operations)
```

### Body:
```
Solo-operator running 11 live SaaS products simultaneously through a
single autonomous AI pipeline called HIVE MIND. This is a writeup
of the actual operating model with real numbers.

Stack
- Vercel (free tier) for 11 product fronts
- HuggingFace (free) for datasets and demos
- Cloudflare (free) for CDN + DNS + AI bot policy
- Supabase (free tier) for state
- One GCP VM at $25/month for the quant backend
- A few personal devices (1 PC + 1 home server + 1 Mac Studio)

Pipeline (Sense -> Think -> Create -> Quality -> Ship -> Learn ->
Refresh) with V-Score gate at 184.5 / 200. Auto-publishes content
across all 11 properties from a single SSOT.

Numbers
- 11 live products
- 1 human operator
- 8 published HuggingFace datasets (CC-BY-4.0)
- 9 Zenodo DOIs (DataCite-grade citation)
- 13-entity Wikidata knowledge graph (395 statements)
- 5 awesome-list GitHub PRs accepted
- 2 NeurIPS 2026 paper submissions
- ~$50/month total infrastructure

Honest gotchas
- AI agents mention us by name 90% of the time but cite our URL 0
  times across 426 measurements - we are still working on the trust
  signal gap (added an explicit /cite page recently)
- Dev.to blocked our account on first cross-publish attempt due to
  burst rate limit + new domain spam check - 2-3 day moderation hold
- HN gated our first Show HN, currently building karma via the warm-up
  pattern

Repo: github.com/Yesol-Pilot/neo-genesis (MIT + Apache-2.0)
Public surface: neogenesis.app
Operating manual: neogenesis.app/blog/inside-hive-mind
```

---

## Pre-flight Checklist (before posting)

- [ ] Reddit account is at least 1 week old + email verified
- [ ] Posted in any subreddit at least once before (any low-stakes
      thread; helps spam detection skip you)
- [ ] At least 5 substantive comments on /r/MachineLearning or
      /r/programming in the past 7 days
- [ ] Not posting from a VPN (Reddit flags VPN posts hard)
- [ ] Title under 300 chars (Reddit limit)
- [ ] Body has a clear methodology + clear honest framing + open data
      links + invitation to discuss

---

## After Posting

1. Reply to first 3 comments within 1 hour (this signals legitimacy
   to Reddit's ranking algorithm)
2. Do NOT delete the post if it gets downvoted in the first hour;
   wait 24h
3. Cross-post to /r/datasets ONLY if /r/MachineLearning post
   accumulates >50 upvotes (early traction is the signal)
4. Save the post URL to canonical_links.json under "Reddit"

---

## What to do if both posts get removed

- Most likely cause: subreddit-specific self-promotion rule
- Read the auto-mod removal message carefully (Reddit usually tells
  you the exact rule violated)
- Adjust:
  - If "self-promotion": rewrite to lead with the methodology, not
    the brand. Move the URL to the very end as a single line.
  - If "low effort": expand to 800-1200 words with explicit code
    snippets + figures
- Wait at least 7 days before resubmitting any version

---

## Last Reviewed

2026-05-06 by Claude Opus 4.7. Next review when warm-up plan
returns this doc as a candidate for Reddit re-attempt or after
Reddit campaign concludes.
