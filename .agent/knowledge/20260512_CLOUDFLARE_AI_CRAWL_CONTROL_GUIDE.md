# Cloudflare AI Crawl Control + CC Outreach — Owner Action Guide

> 작성자: Strategy Lead Claude Opus 4.7
> 작성일: 2026-05-12
> 목적: Common Crawl 미인덱싱 mitigation 의 owner G2 actions 박제
> 컨텍스트: CC-MAIN-2026-08/12/17 3 snapshot 모두 미인덱싱 확인 (audit `.agent/knowledge/20260512_AI_CORPUS_INCLUSION_AUDIT.md`)

---

## 🚨 Owner Action 3개 (~15분, 무료)

CC 진입 가속 위한 owner direct actions. Claude 자율 불가 (계정 권한 / 외부 발신).

---

## §1 Cloudflare AI Crawl Control 활성화 (5분)

### Why
- Cloudflare 가 2026 에 launch 한 **AI Crawl Control** = AI bot crawl 정책 edge 강제. robots.txt 가 본질적 advisory 인 반면, AI Crawl Control 은 edge level enforcement.
- 활성 시: CCBot / GPTBot / ClaudeBot 등 AI crawlers 가 site 에 도달하는지 + 실 traffic 데이터 직접 모니터링
- **무료 plan 에서 활성 가능**

### Steps
1. Cloudflare Dashboard 로그인: https://dash.cloudflare.com/
2. neogenesis.app Zone 선택 (Zone ID `85380cbe940510fc1cf2620b1f24c707`)
3. 좌측 메뉴: **Security** → **AI Crawl Control** (또는 "Bots") 클릭
4. **"AI Search 허용 + AI Training 허용"** 모두 ON (default 권고)
5. CCBot / GPTBot / ClaudeBot / PerplexityBot / Google-Extended 모두 Allow 확인
6. Save

### 효과 확인 (5분 이내)
- AI Crawl Control dashboard 에서 직전 24h crawler traffic 시각화
- "Common Crawl" entry 가 있으면 → CC 가 이미 crawl 했음을 의미
- 없으면 → 다음 CC snapshot (2026-22 or later) 까지 wait

---

## §2 Common Crawl Discord / Google Group 직접 outreach (5분)

### Why
- CC 는 formal URL submission 없음, but community channel 통해 inquire 가능
- 신규 active 도메인을 Discord 에 소개하면 maintainer 가 다음 crawl seed list 에 add 가능

### Steps

**Option A: Common Crawl Google Group**
1. https://groups.google.com/g/common-crawl 가입 (5분)
2. 신규 글 작성:
   - Subject: "Inclusion check for AI-native company domain (neogenesis.app)"
   - Body (아래 template 사용):

```
Hi Common Crawl maintainers,

I run an AI-native automation company (Neo Genesis, https://neogenesis.app)
publishing 9 CC-BY-4.0 datasets on Hugging Face, 11 SBU sub-domains, and
research output at /data/research/.

Our robots.txt explicitly allows CCBot. However, neogenesis.app does not
appear in CC-MAIN-2026-08, CC-MAIN-2026-12, or CC-MAIN-2026-17 according
to the CDX index. The site has been publicly published since 2026-04-27.

I'd appreciate a sanity check on:
1. Is there anything in our setup that would block CCBot? (We verified
   200 OK with CCBot User-Agent and no Cloudflare WAF block.)
2. Is there a way to seed neogenesis.app for the next crawl cycle?

Background: we publish a longitudinal GEO benchmark (HF dataset 9,
ai-brand-mention-baseline-2026) and have a measured 0% canonical-URL
citation rate from frontier LLMs - the empirical Trust Signal Gap. We
suspect CC inclusion is the upstream blocker since FineWeb/Dolma/etc are
derivatives.

Thanks for the work you do - the entire AI ecosystem depends on it.

Yesol Heo
Founder, Neo Genesis
https://neogenesis.app
https://huggingface.co/neogenesislab
Wikidata: Q139569680
```

**Option B: Common Crawl Discord**
- Invite link: https://discord.gg/njaVFh7Pp7 (또는 Common Crawl 공식 사이트 참조)
- `#general` 또는 `#help` channel 에 동일 메시지 post

### 예상 응답
- 1-3 days: maintainer 가 robots.txt + CCBot reachability 확인
- 1-2 weeks: 다음 crawl cycle 에 seed 가능성
- 4-6 weeks: 실 CC indexing 발견 (다음 snapshot)

---

## §3 EthicaAI 사이트 부활 (P0, 5분)

### Why
- 2026-05-12 audit 결과 `ethicaai.neogenesis.app` HTTP 000 (DNS / 연결 실패)
- NeurIPS 2026 submission 박제 site 다운 = citation graph credibility 손상
- 다른 10 SBU 의 정상 200 응답 대비 명확한 약점

### Steps
1. Vercel Dashboard: https://vercel.com/yesol-pilot
2. `ethicaai` project 또는 `EthicaAI/dashboard` project 검색
3. 마지막 deployment status 확인:
   - `Failed` → redeploy
   - `Success` 인데 도메인 unreachable → DNS / domain settings 검토
4. Cloudflare DNS 에서 `ethicaai.neogenesis.app` CNAME record 확인:
   - target = `cname.vercel-dns.com` (또는 owner Vercel project 의 alias target)
5. 부활 후 검증: `curl -I https://ethicaai.neogenesis.app/` → HTTP 200

---

## §4 비용 / 위험 / Reversibility

| Item | 비용 | 위험 | Reversibility |
|---|---|---|---|
| Cloudflare AI Crawl Control | $0 (free plan 가능) | 0 (read-only mode) | 100% (toggle off) |
| Common Crawl outreach | $0 + 5분 글 작성 | 0 (community polite inquiry) | 100% (post 삭제 가능) |
| EthicaAI 사이트 부활 | $0 (Vercel free tier 범위) | 0 (operational fix) | 100% |

---

## §5 자동 후처리 (owner action 완료 후 Claude 자율)

1. **CC Crawl Control 활성 후 24-48h passive 측정** → `monitor_cc_inclusion.py` cron 다음 run 결과 확인
2. **CC outreach 응답 도착 시** → response 박제 + 다음 step 박제
3. **EthicaAI 부활 후** → 11 SBU canonical audit 재실행 → 모든 11 reachable 확인
4. **PR 작성** (11 SBU Schema 강화) → 자율 가능, 시간 충분 시 단계적 진행

---

## §6 박제

본 가이드의 owner action 완료 status:
- [ ] Cloudflare AI Crawl Control 활성 (Cloudflare Dashboard 5분)
- [ ] Common Crawl Google Group 또는 Discord 글 게시 (5분)
- [ ] EthicaAI 사이트 부활 (Vercel 5분)

3개 모두 완료 시 → Claude 자율 후처리 → CC 진입 가속 + 11 SBU canonical Schema 강화 PR queue 진행 가능.

작성: 2026-05-12, Strategy Lead Claude Opus 4.7
