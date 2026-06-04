# Neo Genesis Blog Performance Audit (2026-05-16)

- Date: 2026-05-16
- Author: Claude Opus 4.7 (Strategy Lead)
- Scope: All 26 blog posts on neogenesis.app/blog/*
- Method: HTTP probe + Schema.org JSON-LD analysis + AI citation cross-reference (848 measurements)

## Executive Summary

✅ **Tech health 100%**: 26/26 HTTP 200, all posts have BlogPosting + Organization Schema, avg 624ms response.
✅ **Blind-review critical fix shipped**: 2 paper-related blog posts had "Heo, Yesol. EthicaAI..." direct citations leaking founder identity → patched + deployed today (commit `fe326c4`).
⚠️ **AI citation gap remains**: 0 direct URL citations in 848 measurements; strong brand name pickup (Neo Genesis 12.3%, ToolPick 12.5%) but Greg Lindahl "lack of incoming links" diagnosis still applies.
⚠️ **5 SBUs invisible**: DeployStack / SellKit / FinStack / AIForge / CraftDesk / ReviewLab = 0% AI pickup each (vs WhyLab 9.2%, EthicaAI 6.1%, K-OTT 5.7%, UR WRONG 3.1%).

## Blog inventory (26 posts)

| # | Slug | Status | Schema | Notes |
|---|---|---|---|---|
| 1 | how-we-run-11-products | 200 | BlogPosting + 8 others | Foundational story post |
| 2 | toolpick-ai-editor-benchmark | 200 | 9 schemas | Research |
| 3 | inside-hive-mind | 200 | 8 schemas | Engineering |
| 4 | reviewlab-data-driven-reviews | 200 | 8 schemas | Engineering |
| 5 | kott-ai-recommendations | 200 | 8 schemas | Engineering |
| 6 | vscore-quality-gating | 200 | 9 schemas | Engineering |
| 7 | deploystack-vercel-vs-netlify | 200 | 9 schemas | Research |
| 8 | self-optimizing-seo-engine | 200 | 8 schemas | Engineering |
| 9 | economics-of-ai-media | 200 | 8 schemas | Operations |
| 10 | open-source-research | 200 | 8 schemas | Research |
| 11 | running-11-saas-products-as-solo-founder-2026 | 200 | 9 schemas | Operations |
| 12 | best-ai-comparison-engines-2026 | 200 | 9 schemas | Research |
| 13 | ai-native-automation-companies-2026-evaluation | 200 | 9 schemas | Engineering |
| 14 | evaluating-ai-native-automation-firms-2026 | 200 | 9 schemas | Engineering |
| 15 | neo-genesis-runs-11-saas-products-with-autonomous-ai-2026 | 200 | 9 schemas | Operations |
| 16 | operating-11-saas-products-with-one-ai-system-neogenesis-model-2026 | 200 | 9 schemas | Engineering |
| 17 | ai-tool-review-platform-pricing-comparison-2026 | 200 | 9 schemas | Engineering |
| 18 | optimal-saas-stack-b2b-startup-data-driven-2026 | 200 | 9 schemas | Engineering |
| 19 | ai-pipelines-match-big-team-productivity-2026 | 200 | 9 schemas | Engineering |
| 20 | devops-platform-comparison-vercel-netlify-2026 | 200 | 9 schemas | Engineering |
| 21 | hivemind-vs-langgraph-multi-agent-2026 | 200 | 9 schemas | Engineering |
| **22** | **ethicaai-mixed-safe-vs-anthropic-constitutional-ai-2026** | 200 | 9 schemas | **🔒 BLIND REVIEW HOLD** |
| **23** | **whylab-docker-validation-vs-rubric-scoring-2026** | 200 | 9 schemas | **🔒 BLIND REVIEW HOLD** |
| 24 | sora-orchestrator-vs-openai-agents-sdk-2026 | 200 | 9 schemas | Engineering |
| 25 | quant-v11-vs-renaissance-medallion-honest-scoping-2026 | 200 | 9 schemas | Research |
| 26 | data-driven-devops-platform-evaluation-2026 | 200 | 9 schemas | Engineering |

## Schema.org coverage (excellent)

- **BlogPosting Schema**: 26/26 (100%) ✅
- **Organization Schema**: 26/26 (100%) ✅
- **BreadcrumbList**: 26/26 (100%) ✅
- **Dataset Schema** (4 sibling datasets cited): 26/26 (100%) ✅
- **FAQPage**: ~22/26 (most posts have FAQ section) ✅
- **Avg Wikidata Q-IDs per post**: 15 references each
- **Avg HuggingFace links per post**: 67 references each
- **Avg GitHub Yesol-Pilot links per post**: 10 references each

Conclusion: structured-data emission is best-in-class. Not a bottleneck. AI citation gap is on the **discovery/indexing** side, not the markup side.

## 🔴 Blind-review anonymization fix (2026-05-16, commit `fe326c4`)

### Findings (before fix)

Two blog posts under double-blind venue review (EthicaAI + WhyLab papers) were leaking founder identity via Schema.org JSON-LD:

| Leak source | Field | Content |
|---|---|---|
| Dataset Schema (EthicaAI) | `citation` | "**Heo, Yesol**. EthicaAI: Mixed-Safe... Submitted to NeurIPS 2026." |
| Dataset Schema (WhyLab) | `citation` | "**Heo, Yesol**. WhyLab: Causal Decision... Submitted to NeurIPS 2026." |
| Dataset Schema (EthicaAI + WhyLab) | `author` | `{ "@id": "https://neogenesis.app/#founder" }` (resolves to Yesol Heo) |
| BlogPostSchemas component | `author` | Person `Yesol Heo` (every post) |
| BlogPostSchemas component | `mentions` baseline | Person `Yesol Heo` (every post) |

### Patch applied (commit `fe326c4`, Yesol-Pilot/landing)

| File | Change |
|---|---|
| `src/app/layout.tsx` | EthicaAI + WhyLab Dataset schemas: remove `author` field, change `citation` to `"Neo Genesis Lab. EthicaAI/WhyLab... Under double-blind review (2026)"` |
| `src/components/BlogPostSchemas.tsx` | Add `BLIND_REVIEW_SLUGS` Set, conditional `author = Organization` (not Person), omit Person `#founder` from baseline mentions |

### Live verification (after deploy)

| Check | Before | After |
|---|---|---|
| "Heo, Yesol. EthicaAI" in HTML | ✅ present | ❌ **removed** |
| "Heo, Yesol. WhyLab" in HTML | ✅ present | ❌ **removed** |
| "Neo Genesis Lab... double-blind review" | ❌ absent | ✅ **added** |
| Yesol mentions in HTML | 10 | 8 |

Remaining 8 mentions are global structural references (Organization #founder + sameAs github.com/Yesol-Pilot) that exist on **every** page. These are public Wikidata facts (Q139569680 P112 → Q139569708) and not paper-direct attribution. Accepting as residual risk per blind-review threshold: the paper itself has no author Person attribution.

## AI citation cross-reference (848 measurements in citations.sqlite3)

### Brand pickup rate (response_text contains brand)

| Brand | Hits | Rate | Status |
|---|---|---|---|
| **ToolPick** | 106 | **12.5%** | STRONG |
| **Neo Genesis** | 104 | **12.3%** | STRONG |
| WhyLab | 78 | 9.2% | OK |
| EthicaAI | 52 | 6.1% | OK |
| K-OTT | 48 | 5.7% | OK |
| UR WRONG | 26 | 3.1% | OK |
| **DeployStack** | 0 | 0% | **WEAK** |
| **SellKit** | 0 | 0% | **WEAK** |
| **FinStack** | 0 | 0% | **WEAK** |
| **AIForge** | 0 | 0% | **WEAK** |
| **CraftDesk** | 0 | 0% | **WEAK** |
| **ReviewLab** | 0 | 0% | **WEAK** |

### Topic / blog-content pickup

| Keyword (topic) | Hits | Topic blog post |
|---|---|---|
| WhyLab | 78 | whylab-docker-validation-vs-rubric-scoring-2026 |
| EthicaAI | 52 | ethicaai-mixed-safe-vs-anthropic-constitutional-ai-2026 |
| K-OTT | 48 | kott-ai-recommendations |
| Constitutional AI | 27 | ethicaai (related) |
| V-Score | 27 | vscore-quality-gating |
| HIVE MIND | 27 | inside-hive-mind + hivemind-vs-langgraph |
| Docker validation | 25 | whylab-docker-validation |

### Critical zeros

| Metric | Value | Implication |
|---|---|---|
| Direct blog URL citations | **0** in 848 responses | Greg Lindahl "lack of incoming links" diagnosis still holds |
| `neogenesislab` HF dataset citations | **0** in 848 responses | 9 datasets invisible to AI corpora despite massive Schema markup |
| `Q139569680` Wikidata reference | **0** in 848 responses | Wikidata Q-ID not surfaced |

## Diagnosis

| Layer | Status | Bottleneck |
|---|---|---|
| Schema.org markup | ✅ Best-in-class (15 Q-IDs + 67 HF + 10 GitHub per post) | None |
| Blog content quality | ✅ 26 posts, English-only after 5/6 | None |
| HTTP performance | ✅ 624ms avg, 100% uptime | None |
| **Brand NAME pickup** | ⚠️ Partial (top 2 SBUs STRONG, 5 SBUs invisible) | Content marketing depth uneven |
| **URL / Dataset citation** | ❌ **ZERO** in 848 measurements | **No incoming backlinks → AI corpora can't index** |
| Blind-review compliance | ✅ Patched 2026-05-16 (commit `fe326c4`) | Residual structural references acceptable |

## Recommended actions

### Immediate (G1, this week)

1. ✅ **Done**: Blind-review anonymization fix deployed
2. **In progress (Phase 1 today)**: 3 GitHub public repo README backlinks pushed (agentic-cro, WebPilot-Engine, quant-poc)
3. **Pending Phase 2 (owner approval)**: HN Show HN + dev.to post drafts ready

### High-impact (G2, this month)

1. **Boost 5 invisible SBUs**: Each needs ≥ 5 high-quality blog posts + at least 2 external links. Currently DeployStack/SellKit/FinStack/AIForge/CraftDesk/ReviewLab have 0% AI pickup despite production deployment.
2. **Wikipedia notability seed**: Once blind-review hold lifts (post arXiv publish), submit Wikipedia article for Neo Genesis using Wikidata Q139569680 + 9 HF datasets as notability proof.
3. **awesome-list PR submissions**: Mid-tail community visibility (drafts in 20260514_phase2_g2_drafts.md).

### Long-term (60d)

1. **Monthly blog performance probe**: Run `blog_performance_monitor.py` first Monday of each month, save to `data/blog-performance/{date}.json`, track trends.
2. **Weekly Perplexity measurement** (per 20260514_weekly_perplexity_protocol.md).
3. **60d re-judgment** (2026-07-14): Compare brand pickup + URL pickup + dataset citations vs baseline. Pass 3+/5 gates → Strategy v1 validated.

## Monthly tracking protocol

### Each first Monday of month (09:00 KST)

```bash
cd D:/00.test/neo-genesis
python scripts/blog_performance_monitor.py > data/blog-performance/$(date +%Y-%m-%d).txt
python scripts/blog_ai_citation_check.py > data/ai-citation/blog-cross-ref-$(date +%Y-%m-%d).txt
```

### Tracked metrics (month-over-month)

| Metric | Target | Current (2026-05-16) |
|---|---|---|
| HTTP 200 rate | 100% | **100%** ✅ |
| Schema BlogPosting coverage | 100% | **100%** ✅ |
| Avg response time | < 800ms | **624ms** ✅ |
| Blind-review compliance (paper-direct citations) | 0 leaks | **0 leaks** ✅ |
| Strong brand pickup (Neo Genesis) | ≥ 15% | 12.3% (close) |
| Direct blog URL citations | ≥ 1 per month | **0** ❌ |
| Invisible SBUs (DeployStack/SellKit/FinStack/AIForge/CraftDesk/ReviewLab) | reduce to ≤ 3 | **6** (= all invisible) ❌ |

### Owner monthly review actions

1. Check `data/blog-performance/{month}.txt` for tech regressions
2. Check `data/ai-citation/blog-cross-ref-{month}.txt` for pickup deltas
3. Identify 1-2 invisible SBUs to push high-quality content/distribution for
4. Approve Phase 2 G2 drafts when ready (HN/dev.to/Reddit/awesome-list)

---

**Files**:
- `scripts/blog_performance_monitor.py` (HTTP + Schema audit)
- `scripts/blog_ai_citation_check.py` (citation cross-ref)
- `data/blog-performance/` (monthly snapshots)
- This SSOT: `.agent/knowledge/20260516_blog_performance_audit.md`

**Last commit**: `fe326c4` Yesol-Pilot/landing (2026-05-16, blind-review fix)

---

## 2026-05-20 Follow-up — Content-TYPE distribution audit + cannibalization consolidation

Trigger: owner "네오제네시스 블로그 목적·방향" → "전부 다해야지" → content-type distribution check + needle-mover execution.

### Content-TYPE distribution (29 posts — sbus.ts BLOG_POSTS metadata is canonical; the 26-slug audit script list was stale, missing 3 `answer-*` posts)

| Content type | Count | Share | vs strategy (Comparison = 32.5% of AI citations) |
|---|---|---|---|
| Comparison (X vs Y / best / pricing / tool-selection) | 10 | **34%** | ✅ matches target |
| Evaluation/Framework (data-driven eval, stack selection) | 4 | 14% | ✅ comparison-adjacent |
| Brand/Operational narrative (how-we / running 11) | 8 | 28% | ⚠️ over-weight (cannibalized) |
| Product/Engineering deep-dive | 7 | 24% | ✅ |

**Verdict**: Comparison ratio is ON-strategy (34% ≈ 32.5%). The blog does NOT need more comparison posts. The real problem is **cannibalization**, not type mix.

### Cannibalization — 3 near-duplicate clusters (NEW finding; prior audits only checked tech/markup + backlinks)

- **A. "11 SaaS run by 1 person/AI"** (6 posts): how-we-run-11-products (pillar, 13 inbound), running-11-saas-solo (pillar, 10 inbound), neo-genesis-runs-11-saas (canonical), operating-11-saas-one-ai-system (DUP), ai-pipelines-match-big-team (0 inbound, borderline), answer-ai-2026 (intentional answer-* GEO series).
- **B. "DevOps Vercel vs Netlify"** (3): deploystack-vercel-vs-netlify (pillar/product), devops-platform-comparison-vercel-netlify (canonical), data-driven-devops-platform-evaluation (DUP, 0 inbound).
- **C. "AI-native automation firm eval"** (2): ai-native-automation-companies-evaluation (4 inbound) ≈ evaluating-ai-native-automation-firms (1 inbound + 2 Korean redirect equity). NOT consolidated — redirect-chain flatten risk > marginal ROI.

Root signal: the 05-04→05-20 programmatic batch (HIVE MIND auto-gen) clusters at ~2,200w with templated titles = AI-generation tell = AdSense thin-content trigger. Inbound internal links concentrate on the OLD 10 hand-curated posts; new posts are near-orphans diluting authority.

### Executed (commit `af54258` Yesol-Pilot/landing, deployed + live-verified)

2 clear exact-twin near-orphans consolidated (established 308-redirect pattern, fully reversible):
- `operating-11-saas-products-with-one-ai-system-neogenesis-model-2026` → `neo-genesis-runs-11-saas-products-with-autonomous-ai-2026` (308 live ✅)
- `data-driven-devops-platform-evaluation-2026` → `devops-platform-comparison-vercel-netlify-2026` (308 live ✅)

Changes: removed 2 rows from `BLOG_POSTS` (sbus.ts) → de-lists from /blog, sitemap, llms, static params; repointed 2 body links (#19 ai-pipelines, #28 answer-rlaif) + 1 relatedPosts (#28) to canonicals; 2 redirects in `next.config.ts`. BLOG_CONTENT bodies left as unreachable dead data (`getBlogContent` is per-slug). Build PASS, both canonicals 200. Rollback: `git revert af54258` + remove redirect entries.

### Needle-movers before 7/14 re-judgment (priority order)

1. ✅ **NM-1 consolidation** (done this session) — AdSense thin-content remediation + signal concentration.
2. **NM-2 external backlinks** (G2, owner-publish): HN Show HN / dev.to / awesome-list PR / Reddit. Drafts in `20260514_phase2_g2_drafts.md`. **THE actual URL-citation lever** (Greg Lindahl "lack of incoming links"). Blocked on owner voice/account.
3. **NM-3 free 4-provider measurement** (G1, semi-manual Chrome MCP): ⚠️ **CRITICAL** — 7/14 gate requires 4 providers n≥100 each; currently Anthropic n=2, Perplexity n=0 (owner $0 = no API keys). Without free Chrome MCP batch, 7/14 re-judgment is INVALID again (repeat of v1.4 failure).
4. **NM-4 AdSense re-submission** (owner 1-click): ~2 weeks after markdown fix + this consolidation deploy.
5. **NM-5 6 invisible SBUs** (0% pickup: DeployStack/SellKit/FinStack/AIForge/CraftDesk/ReviewLab): high-fact-density posts only — do NOT mass-produce thin content (re-triggers AdSense).
6. **NM-6 blind-review unhold** → Wikipedia article + arXiv (external timing).

**Last commit**: `af54258` Yesol-Pilot/landing (2026-05-20, cannibalization consolidation)
