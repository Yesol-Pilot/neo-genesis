# neogenesis.app Main Site Audit (2026-05-16)

- Date: 2026-05-16
- Scope: **neogenesis.app 본 사이트만** (SBU subdomains 제외)
- Method: Sitemap parse → 90 URLs → AI agent surface + core pages audit
- Companion doc: `20260516_blog_performance_audit.md` (26 blog posts)

## TL;DR

✅ **Site의 on-page/markup 측면 100% 최적**. 24 AI bots allowed, llms.txt 152 lines + 114 links, llms-full.txt 11K words, 90 URL sitemap, BlogPosting Schema 26/26, FAQ Schema 25 blocks.
❌ **URL pickup gap = 외부 incoming links 결핍**. on-site 만으로는 해소 불가능. Greg Lindahl 진단 ("lack of incoming links") 직접 확인.

## Sitemap inventory (90 URLs)

| Category | Count |
|---|---|
| Blog posts | 28 (26 + index + markdown) |
| Data (research / quant) | 13 |
| SBU landing | 11 |
| Press | 7 |
| Docs | 5 |
| Wikipedia drafts | 5 (4 사이드 + 인덱스) |
| Intent routes (/tools, /sales, /devops, /finance, /ai, /ops, /kr, /labs) | 8 |
| Core (/about, /faq, /cite, /press, /awards, /privacy, /terms, /blog, /docs, /data) | 10 |
| AI agent files | 6 (llms.txt, llms-full.txt, rss, feed, humans, security) |

## 🤖 AI Agent surface health (8/8 OK)

| File | Status | Size | Content |
|---|---|---|---|
| `/robots.txt` | 200 | 1.9KB | **24 AI bots** explicitly listed |
| `/llms.txt` | 200 | 30.8KB | 152 lines, 13 sections, **114 links** |
| `/llms-full.txt` | 200 | 87.1KB | **11,024 words**, ~17K tokens, 80% token reduction vs HTML |
| `/sitemap.xml` | 200 | 15.6KB | **90 URLs** |
| `/rss.xml` | 200 | 18.5KB | RSS feed |
| `/feed.json` | 200 | 50.4KB | JSON feed |
| `/humans.txt` | 200 | 1.1KB | — |
| `/.well-known/security.txt` | 200 | 1.0KB | Security contact |

### 24 AI bots in robots.txt

GPTBot · ClaudeBot · Claude-SearchBot · Claude-User · PerplexityBot · Perplexity-User · OAI-SearchBot · OAI-AdsBot · ChatGPT-User · Google-Extended · GoogleOther · GoogleOther-Image · GoogleOther-Video · Googlebot · Applebot · Applebot-Extended · Bingbot · Bingbot-Mobile · NaverBot · CCBot · Bytespider · FacebookBot · anthropic-ai · cohere-ai

→ **Coverage best-in-class**. Every major AI corpus crawler explicitly allowed.

## 📄 Core pages (20/20 OK)

| Path | HTTP | RTT | JSON-LD | Title |
|---|---|---|---|---|
| `/` | 200 | 49ms | **11** | Neo Genesis (NeoGenesis) - AI-Native... |
| `/about` | 200 | 48ms | 10 | Yesol Heo - Founder | About |
| `/faq` | 200 | 597ms | **25** | FAQ |
| `/cite` | 200 | 604ms | 9 | How to Cite Neo Genesis |
| `/press` | 200 | 795ms | 8 | Press |
| `/awards` | 200 | 668ms | 8 | Awards & Recognition |
| `/data` | 200 | 645ms | 7 | Data Hub - Open Research |
| `/data/research` | 200 | 573ms | 7 | Research |
| `/data/quant` | 200 | 660ms | 7 | Quant |
| `/blog` | 200 | 46ms | 9 | Blog |
| `/docs` | 200 | 577ms | 8 | Documentation |
| `/wikipedia-drafts` | 200 | 650ms | 8 | Wikipedia Drafts |
| `/tools` | 200 | 560ms | 8 | SaaS Tool Comparison Hub |
| `/sales` | 200 | 661ms | 8 | Ecommerce Growth Stack Hub |
| `/devops` | 200 | 639ms | 8 | DevOps Platform Hub |
| `/finance` | 200 | 574ms | 8 | Fintech Infrastructure Hub |
| `/ai` | 200 | 608ms | 8 | AI Tool ROI Hub |
| `/ops` | 200 | 669ms | 8 | Creative Operations Hub |
| `/kr` | 200 | 572ms | 8 | Korea Consumer Decision Hub |
| `/labs` | 200 | 571ms | 8 | Research and Product Lab Hub |

→ 100% 가용. Schema density 평균 9 JSON-LD blocks/page. **/faq 가 25 blocks 로 최고** (FAQ Schema rich).

## 🌐 Wikipedia drafts (notability seed strategy)

4 drafts present + 200 OK:
- `/wikipedia-drafts/neo-genesis-en` — Neo Genesis 영문 draft
- `/wikipedia-drafts/neo-genesis-ko` — Neo Genesis 한글 draft
- `/wikipedia-drafts/yesol-heo-en` — Yesol Heo 영문 draft (블라인드 unhold 후)
- `/wikipedia-drafts/yesol-heo-ko` — Yesol Heo 한글 draft

→ **Wikipedia 등록 준비 완료**. 블라인드 심사 unhold 시점에 즉시 submission 가능.

## 진단: 진짜 gap은 OFF-SITE

| Layer | Status | 진짜 bottleneck? |
|---|---|---|
| Schema.org markup | ✅ Best-in-class | NO |
| AI agent surfaces (robots/llms.txt) | ✅ 24 bots, 11K words | NO |
| Sitemap completeness | ✅ 90 URLs | NO |
| Site performance | ✅ 49-800ms | NO |
| HTTP 200 rate | ✅ 100% | NO |
| **Incoming external links** | ❌ **확인된 핵심 gap** | **YES** |

Greg Lindahl (Common Crawl maintainer) 답신 그대로:
> "lack of incoming links"

= **모든 on-site 최적화 작업은 끝났음. 더 할 게 없음.**

남은 progress는 다 **외부 backlinks**에서 옴:
- Phase 1 (오늘 완료): 3 GitHub repos cross-reference (18 backlinks)
- Phase 2 (drafts ready): HN show + dev.to + awesome-list + Reddit
- 블라인드 unhold 후: Wikipedia 첫 article (notability seed)
- arXiv unhold 시: paper 인용 시작

## Monthly monitoring (neogenesis.app standalone)

### 매월 1st Monday (09:00 KST)

```bash
python scripts/neogenesis_app_audit.py > data/site-audit/$(date +%Y-%m-%d).txt
python scripts/blog_performance_monitor.py > data/blog-performance/$(date +%Y-%m-%d).txt
python scripts/blog_ai_citation_check.py > data/ai-citation/$(date +%Y-%m-%d).txt
```

### Tracked metrics (month-over-month)

| Metric | Target | 2026-05-16 |
|---|---|---|
| AI agent files 200 OK | 8/8 | **8/8** ✅ |
| Core pages 200 OK | 20/20 | **20/20** ✅ |
| Blog 200 OK | 26/26 | **26/26** ✅ |
| Sitemap URLs | grow 5-10/month | **90** |
| robots.txt AI bots | ≥ 20 | **24** ✅ |
| llms.txt links | ≥ 100 | **114** ✅ |
| llms-full.txt words | ≥ 10K | **11,024** ✅ |
| Brand NAME pickup (Neo Genesis) | ≥ 15% | 12.3% (close) |
| URL citation pickup | **≥ 1** per month | **0** ❌ |
| HF dataset citation | **≥ 1** per month | **0** ❌ |

### Owner monthly review actions

1. **Site health** = pass/fail one-shot view (자동 audit script 결과)
2. **Brand pickup trend** (citations.sqlite3 누적 데이터)
3. **External link 진척**: GitHub repos / awesome-list PRs / Wikipedia drafts 상태
4. **Wikipedia submission decision**: 블라인드 unhold 시점 알림

## 최종 결론

**neogenesis.app 본 사이트 = 완벽한 상태**. 더 깎을 게 없음.

진척은 **외부 활동 (backlinks, citations, paper publish, Wikipedia)** 에서만 옴.

월간 audit script로 regression 만 모니터링하면 됨. on-site 최적화는 더 이상 ROI 없음.

---

**Files**:
- `scripts/neogenesis_app_audit.py` (site audit)
- `scripts/blog_performance_monitor.py` (blog detail)
- `scripts/blog_ai_citation_check.py` (citation cross-ref)
- This SSOT: `.agent/knowledge/20260516_neogenesis_app_site_audit.md`
- Companion: `.agent/knowledge/20260516_blog_performance_audit.md`
