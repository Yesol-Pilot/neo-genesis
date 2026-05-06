# Show HN Warm-Up Strategy

> Created: 2026-05-06
> Owner: Yesol Heo (HN account: yesol-pilot or whatever you registered)
> Goal: Earn enough HN trust signal to post a successful Show HN within 1-2 weeks
> Trigger that fired this doc: HN community-norm message after first Show HN attempt
> ("become a good contributor, and then it will be fine to post an occasional Show HN")

---

## Why HN Gates New Show HN Posts

Hacker News uses a community-norm gate for Show HN from new accounts. The gate
combines several signals:

- **Account age**: less than 1-2 weeks of activity is suspicious
- **Karma score**: < 10 reads as spam-vector candidate
- **Comment history**: zero substantive comments before a Show HN looks like
  drive-by promotion
- **Submission/comment ratio**: too many submissions, no comments triggers
  the spam filter
- **Domain reputation**: brand-new domains (neogenesis.app, registered weeks
  ago) have no prior HN signal

A new account with all six signals weak gets the polite redirect message.
This is normal HN behavior. The fix is to build the missing signals before
re-attempting.

---

## Two-Week Warm-Up Plan

### Week 1: Read + Comment Only (no submissions)

**Daily 5-10 minutes**:

1. Open https://news.ycombinator.com/news (front page)
2. Pick 2-3 stories that match your real expertise:
   - Multi-agent RL papers
   - LLM tooling, agent frameworks (LangGraph, Mastra, OpenAI Agents SDK)
   - Programmatic SEO / GEO
   - Solo founder economics
   - Cloudflare / Vercel / HuggingFace operations
   - Causal inference, observational studies
   - Korean tech industry (rare on HN, instant signal if you have insight)
3. Read the full submission (not just title)
4. Read the existing top comments
5. Add ONE substantive comment per story:
   - Either a concrete technical point the existing comments missed
   - OR a real-world data point from your operations
   - OR a respectful disagreement with citation

**What counts as substantive**:
- Specific numbers / measurements
- Links to docs, repos, or papers
- A counter-example from production
- Personal experience that adds new info

**What does NOT count** (and may flag your account):
- "Great post!" / "Thanks for sharing"
- Self-promotion in disguise ("we do this at neogenesis.app...")
- Copy-paste from blog posts
- Pure opinion without evidence

**Target by end of Week 1**: 15-25 substantive comments, 30-60 karma.

### Week 2: Selective Submissions (non-Show HN)

Continue commenting daily. Add 2-3 regular submissions.

**Submission strategy**:
- Submit OTHER PEOPLE'S work that you genuinely found valuable
- Examples: a paper you read, a tool you tried, an essay you liked
- This proves you can identify quality content (the same skill HN expects
  from a Show HN curator)

**Do NOT submit**:
- Anything from neogenesis.app
- Anything that benefits Neo Genesis directly
- Reposts of recently-submitted items (search HN first)

**Target by end of Week 2**: 35-50 comments total, 75-150 karma, 2-3
respectable submissions.

### Week 3: Show HN

By now your account profile reads like a real engineer who participates in
the community. The Show HN gate should pass.

**Recommended Show HN candidates** (in order of expected reception):

1. **Best**: a working open-source repo with novel value
   - Example: `Yesol-Pilot/neo-genesis` (RAG v2 + agent runtime + 8 datasets)
   - Title format: `Show HN: Neo-Genesis - 11 SaaS products run by one human + autonomous AI`
   - Length: 70 chars

2. **Good**: an open dataset with measurable insights
   - Example: EthicaAI Mixed-Safe (Sen rationality test, 510 evidence rows)
   - Title format: `Show HN: 510-seed Melting Pot test of Sen's rationality theory`
   - Length: 64 chars

3. **Good**: a tool / engine demo (interactive)
   - Example: HuggingFace Space (Wikidata Knowledge Graph Explorer)
   - Title format: `Show HN: Wikidata knowledge graph explorer for solo-founder companies`
   - Length: 68 chars

4. **Acceptable**: a deep-dive write-up
   - Example: `/data/research/agent-environment-v2`
   - Title format: `Show HN: Framework scorecard - LangGraph vs Pydantic AI vs Mastra (2026)`
   - Length: 71 chars

**Always** keep title under 80 chars (HN hard limit).

**Always** be ready to answer the first comment within 1 hour. The author
showing up matters for HN ranking algorithm.

---

## Comment Targeting (Specific Threads to Watch)

The HN front page has consistent topic clusters where your expertise lands well:

### High-fit topics (comment on these whenever they appear)

- **Multi-agent RL / agentic systems**: link to your agent runtime work,
  but ONLY if it adds technical detail (e.g., "we use a Magentic-One dual
  ledger pattern; the trade-off vs vanilla CrewAI is...")
- **Programmatic SEO**: real ROI numbers from running 11 SBUs
- **AI cost economics for solo founders**: $0/month operations on Vercel +
  HuggingFace free tiers
- **Schema.org / structured data / GEO**: your Schema citation chain
  pattern (Org → Person → Article → Dataset) is rare and useful
- **Korean tech / Korean LLMs**: KURE-v1 embeddings, mecab-ko tokenizer,
  Korean RAG evaluation (you have unique perspective here)
- **NeurIPS / academic publishing for solo researchers**: your two NeurIPS
  2026 submissions + 9 Zenodo DOIs are real signal
- **Cloudflare AI Crawl Control / robots.txt for AI bots**: you have an
  explicit allow-list for 25+ AI crawlers, can speak from operational
  experience
- **Wikipedia notability for new orgs**: your Wikipedia drafts research
  (cold-honest N=0 secondary sources finding) is unusually candid

### Low-fit topics (skip)

- Politics, US-Korea trade
- Crypto pump/dump cycles
- Apple vs Google fanboy debates
- "Junior dev hates Tailwind" rants

---

## Anti-Patterns That Will Get Your Account Flagged

1. **Commenting "this matches what we built at neogenesis.app, see [link]"**
   on every thread — this is the textbook spam pattern. HN dang
   (moderator) will email-warn first, then shadowban.
2. **Voting only your own submissions** — HN tracks per-account vote
   patterns. Voting your own stuff and nothing else flags you.
3. **Multiple accounts coordinating** — never. HN catches this immediately.
4. **Copying comment text from blog posts** — every comment must be
   originally written for that thread.
5. **Ignoring your own thread after submission** — if you Show HN and
   then disappear for 3 hours, the thread dies. Must engage in first 1-2h.

---

## Tools to Track Your Warm-Up Progress

1. **HN profile**: https://news.ycombinator.com/user?id=YOUR_USERNAME
   - Check daily: karma score, comment count, submission count
2. **HN Algolia search**: https://hn.algolia.com/?q=YOUR_USERNAME
   - Find which of your comments got upvotes / replies
3. **Stop-go signal**: if karma > 100 + comment count > 30 by end of
   Week 2, Show HN is safe. If karma still < 30, extend warm-up by 1 week.

---

## Backup Plans (if HN warm-up takes longer than 2 weeks)

If you cannot get HN to a friendly state in time, the following channels
have lower bars and similar tech audience overlap:

| Channel | Account age req | Karma req | Audience size |
|---|---|---|---|
| Reddit /r/MachineLearning | 1 week + email verified | minimal | ~3M subs |
| Reddit /r/programming | 1 week | minimal | ~5M subs |
| Lobste.rs | invite required | n/a | ~50K active |
| dev.to | account verified | minimal | ~1M monthly |
| Hashnode | account verified | minimal | ~500K monthly |
| Indie Hackers | account verified | minimal | ~200K |
| Sidebar.io | submission only | n/a | curator-gated |
| Beta List | submission + payment | n/a | early-adopter aud |
| Product Hunt | follower req | minimal | tech audience |

**Recommended order if HN warm-up stalls**:

1. Reddit /r/MachineLearning (single high-quality post about EthicaAI)
2. dev.to + Hashnode cross-publish (already prepared, awaiting API keys)
3. Indie Hackers introduction post (solo-founder narrative is strong here)
4. Product Hunt (only after item 1-3 generate some baseline traction)

---

## Owner-Facing Action Today

If you are reading this and wondering "what should I do right now":

1. Check your HN account: https://news.ycombinator.com/user?id=YOUR_USERNAME
2. Note current karma + comment count
3. Pick 2-3 front-page stories matching the high-fit topics list above
4. Write 1 substantive comment on each
5. Tomorrow: repeat
6. Day 14: re-attempt Show HN with the title-under-80 candidates

That is the entire warm-up. The plan trades 5-10 min/day for a Show HN that
will not get throttled.

---

## Last Reviewed

2026-05-06 by Claude Opus 4.7. Next review: 2026-05-20 (after warm-up
window completes).
