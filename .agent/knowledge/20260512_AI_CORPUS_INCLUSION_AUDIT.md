# AI Training Corpus Inclusion Audit — 2026-05-12

> 작성자: Strategy Lead Claude Opus 4.7
> 출처: Week 1 #6 — Strategy v1 §2.C.C1+C2+C3
> 목적: neogenesis.app 이 주요 AI 학습 corpus 에 진입했는지 확인

---

## §0 결론 (Cold Honest)

**neogenesis.app 은 Common Crawl 최근 3 snapshot (CC-MAIN-2026-08, 2026-12, 2026-17) 모두 미인덱싱**. 즉:
- FineWeb / FineWeb-Edu (CC derivative) → **미포함 확정**
- Dolma v1.7 (CC + Reddit + StackExchange) → **CC 부분 미포함, Reddit 부분 미포함 (자체 monitor 검증: Reddit 매치 모두 false positive)**
- RedPajama / SlimPajama (CC + Wikipedia + arXiv 등) → **CC 부분 미포함**
- C4 / mC4 (CC clean version) → **미포함**

**이것이 brand mention 45% vs canonical URL citation 0% 의 진짜 근본 원인**: 학습 데이터에 우리 URL 자체가 부재.

---

## §1 측정 detail

### CC 직접 lookup (2026-05-12 측정)
```bash
curl "https://index.commoncrawl.org/CC-MAIN-2026-17-index?url=neogenesis.app/*&output=json&limit=10"
# → {"message": "No Captures found for: neogenesis.app/"}

curl "https://index.commoncrawl.org/CC-MAIN-2026-12-index?url=neogenesis.app/*&output=json&limit=10"
# → {"message": "No Captures found for: neogenesis.app/"}

curl "https://index.commoncrawl.org/CC-MAIN-2026-08-index?url=neogenesis.app/*&output=json&limit=10"
# → {"message": "No Captures found for: neogenesis.app/"}
```

### CCBot 접근성 확인 (정상)
- `curl -A "CCBot/2.0 ..." https://neogenesis.app/` → **HTTP 200** ✅
- robots.txt 에 `User-agent: CCBot \n Allow: /` 명시 ✅
- Cloudflare WAF 차단 없음 ✅
- Vercel server 응답 정상 ✅

→ 즉 CCBot 이 와도 받을 준비 완료, **CCBot 이 아직 안 온 상태**.

---

## §2 진단 — 왜 CC 미인덱싱?

### 가능한 원인 (우선순위)

1. **사이트 신규성** (가장 가능성 높음): neogenesis.app 은 2026-04-27 publish. CC-MAIN-2026-17 은 4-5월 첫 주 크롤. 시점 불일치 가능.
2. **Inbound link 부족**: CC 는 webgraph 따라가며 새 URL 발견. 신규 도메인이 인지될 backlink 가 필요.
3. **Tranco / Majestic / Quantcast 순위 미진입**: CC 가 사용하는 도메인 priority list 에 미진입 (월 1회 갱신).
4. **Cloudflare 의 일시적 challenge**: 다른 시점에 CCBot 이 와서 challenge 받았을 수도. 현 응답은 정상.

### Inbound backlink 점검 (CC-indexed 사이트 中)
- ✅ `github.com/Yesol-Pilot/neo-genesis` — README 에 neogenesis.app 직접 링크 (CC index 대상)
- ✅ `huggingface.co/neogenesislab` (9 datasets) — README + dataset cards 에 neogenesis.app 링크
- ✅ `wikidata.org/wiki/Q139569680` — P856 (official website) 에 neogenesis.app 명시
- ⚠️ `wikipedia.org` — Wikipedia 본문 인용 0건 (NCORP gate unmet)
- ⚠️ `reddit.com` / `news.ycombinator.com` — 인용 0건 (organic only)

→ Inbound link 3개 (HF + GitHub + Wikidata) 가 CC-indexed 영역에 존재. **다음 CC snapshot (예상 2026-MAIN-22 또는 23) 에서 진입할 가능성 높음**.

---

## §3 FineWeb / Dolma 직접 진입 가능성

### FineWeb (HuggingFaceFW/fineweb-edu)
- CC-MAIN snapshot 직접 derivative
- CC 진입 → 1-3개월 후 FineWeb 신 revision 에 자동 포함
- HuggingFace dataset search 로 직접 grep 시 large parquet 다운로드 필요 → 별도 cron 권고 (월 1회)

### Dolma (allenai/dolma)
- v1.7 = CC + Reddit + Wikipedia + The Stack + arXiv + Project Gutenberg
- Reddit 부분 가능성도 있지만 현재 Reddit 인용 0건 확인 (L1 monitor)
- CC 진입 시 자동 포함

### Recommendation
**Week 1 영역 외 작업**: parquet stream grep 으로 monthly FineWeb / Dolma 모니터링 cron 박제. ROI 낮음 (CC 진입이 우선).

---

## §4 단기 / 중기 권고 (Strategy Lead 자율)

### 단기 (1-3개월, 자율 G1)
1. **추가 inbound backlink 가속**:
   - HF datasets README 에서 neogenesis.app 명시적 4-layer 인용 (current: 1-layer) — 9개 dataset 모두 보강
   - GitHub repo 신규 release notes 에 canonical URL 첫 줄 명시
   - Wikidata 13 entities 모두 P856 + sameAs neogenesis.app 검증
2. **Common Crawl 발견 가능성 가속**:
   - Cloudflare AI Crawl Control 활성화 (owner G2 action — 5분, 무료)
   - sitemap.xml 60 URLs → CC sitemap-aware crawler 가 직접 인지
3. **Lobste.rs / HN warm-up**: organic posting (Strategy v1 §2.F.F2-F5)

### 중기 (3-6개월)
1. **CC-MAIN-2026-22 또는 23 진입 모니터링** (월 1회 manual check 또는 cron 박제)
2. **FineWeb / Dolma 진입 확인**: CC 진입 후 1-3개월 lag
3. **Wikipedia notability gate 재시도** (Strategy v1 §2.D.D1): N=0 → N=1-3 secondary coverage 누적 후

### 장기 (6-12개월)
1. **AI corpus refresh cycle 적응**: frontier model 6-18개월 cadence 감안
2. **HF dataset 9 monthly refresh 누적 데이터** 로 delta tracking

---

## §5 측정 cadence

### 신설 cron (G1 자율, 본 세션 박제)
- `scripts/citation_monitor/monitor_3rd_party_citations.py` — 주간 cron (월요일 09:30 KST)
- `scripts/hf_publish/refresh_geo_baseline_monthly.py` — 월간 cron (1일 09:00 KST)

### 추가 cron 권고 (다음 세션)
- `scripts/citation_monitor/monitor_cc_inclusion.py` — 월간 (CC 신 snapshot 발견 시 자동 alert)
- `scripts/citation_monitor/monitor_fineweb_inclusion.py` — 월간 (HF dataset search API)

---

## §6 owner action queue (G2)

1. **Cloudflare AI Crawl Control 활성화** — neogenesis.app Zone (`85380cbe940510fc1cf2620b1f24c707`), 5분, **무료**
2. (선택) Cloudflare Web Analytics → CC crawler 활동 직접 모니터링

---

## §7 박제

본 audit 의 baseline:
- 2026-05-12 측정: CC 3 snapshot 미인덱싱
- 다음 CC snapshot 진입 시점 (예상 2026-22 / 23) 까지 wait + accelerate

다음 wake-up 시 본 문서 § 5 cron 결과 + §6 owner action 진행 상태 확인.

작성: 2026-05-12, Strategy Lead Claude Opus 4.7
