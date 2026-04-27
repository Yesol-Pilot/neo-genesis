# neogenesis.app — 전세계 AI 트래픽 극대화 마스터 전략 v1

> **작성일**: 2026-04-27 KST
> **작성**: Claude Opus 4.7 (Strategy Lead, owner 대리인)
> **승인**: owner 자율 위임 (SBU Autonomous Growth Standing Approval, 2026-04-26)
> **근거 리서치**: 8 트랙 병렬 심층 web research (LLM 인용 메커니즘 / 콘텐츠 구조 / 권위 빌드 / 콘텐츠 양산 / 측정 / 회색지대 / 경쟁 / 인덱싱)
> **대상 도메인**: `neogenesis.app` (Cloudflare Zone `85380cbe940510fc1cf2620b1f24c707`)
> **현재 코드 위치**: `D:/00.test/neo-genesis/src/landing/` (Next.js + TypeScript + Vercel)
> **owner 의도**: "겉으로는 네오제네시스 기업 소개, 실체는 전세계 모든 AI 들의 트래픽을 확보하는 플랫폼. 어떤 방법으로든. 도메인이고 뭐가 중요하지 않다."

---

## 0. 결론 (Top-Line)

AI 트래픽 극대화는 **"학습 데이터 진입" + "라이브 검색 인덱싱" + "권위 시그널" 3축의 곱**. 단일 전술로는 절대 불가능. 2026 winner-take-all 구조에서 신생 진입자 유일 경로는 **niche 진입 + unique citable asset + 12개월 일관 운영**.

**핵심 정량 사실 7개**:
1. AI bot 트래픽 80%가 학습 / 17%가 검색 (Cloudflare Radar). 두 채널 동시 공략 필수.
2. 인용 도메인 분포가 플랫폼별 극단 분화 — Reddit Google AI Mode 44% / Perplexity 47% / ChatGPT 1.8%, Wikipedia ChatGPT 47.9% / Perplexity 0.8%.
3. 2026-1 Gemini 3 전환 후 organic top10 ↔ AI Overview 일치율 76% → 38% 폭락. 인용 URL 46.5%가 SERP top 50 밖.
4. Comparison content가 AI 인용의 32.5% (1위 콘텐츠 유형). Statistics 추가 +41% / 인용문 +28% / 출처 +115%.
5. Fact density 500단어당 통계 3개 이상 = citation 2.7배. Schema 적용 시 GPT-4 추출 정확도 16% → 54%.
6. Source churn 매월 40-60% (ChatGPT 54.1% / Perplexity 40.5% / AI Overviews 59.3%) — 1회성 인용 무의미.
7. AI 트래픽 전환율은 organic search의 4.4배.

**결정 (자율, Strategy Lead 권한)**: **옵션 B — Aggressive Data Hub 채택**. "기업 소개 표면 + Data Hub 실체" 듀얼 구조. neogenesis.app 은 이미 8개 unique citable asset 보유 (quant-bot 라이브 telemetry / EthicaAI / WhyLab / RAG Master Design v1 / 6 SBU 운영 메트릭 / 9-Layer Kill Switch / Sora fleet / Agent Environment v2). 진입 자격 충분, publish 인프라만 필요.

**비용**: P0~P2 (M1~M6) 사실상 **$0** — 모두 코드 변경 + 기존 인프라 활용. 유료 측정 SaaS (Profound/Otterly) default 안 씀, ROI 입증 후에만 검토. 외부 commitment (Korea Newswire / Tier 1 PR) 만 G2 게이트.

---

## 1. AI 인용 메커니즘

### 1.1 학습 vs 검색 구분 (가장 중요한 단일 사실)

| 채널 | 메커니즘 | Lag time | 영향 LLM |
|---|---|---|---|
| 학습 데이터 baked-in | GPTBot/ClaudeBot/CCBot/Google-Extended 크롤 → 다음 학습 cycle | 3-12개월 + 모델 업데이트 | 모든 base LLM |
| 라이브 RAG 검색 | OAI-SearchBot/Claude-SearchBot/PerplexityBot/Bingbot/Googlebot 인덱싱 → 사용자 질문 시 retrieval | 분~일 | ChatGPT Search, Perplexity, AI Overviews, Copilot |
| 사용자 직접 fetch | ChatGPT-User/Claude-User/Perplexity-User 사용자 트리거 즉시 fetch | 즉시 | 모두 |

**핵심**: 학습 차단 (`GPTBot Disallow`) 해도 검색 인덱싱 (`OAI-SearchBot Allow`) 가능. 둘 다 차단이 가장 흔한 실수.

### 1.2 플랫폼별 인용 도메인 Top 5

| 플랫폼 | 1위 | 2위 | 3위 | 4위 | 5위 |
|---|---|---|---|---|---|
| ChatGPT | Wikipedia 12-13% | Reddit 12-13% | Forbes | TechRadar | LinkedIn |
| Perplexity | Reddit 24-46.7% | YouTube | LinkedIn | Wikipedia | G2 |
| Gemini | Reddit | YouTube | Wikipedia | Medium | PCMag |
| Google AI Overviews | YouTube 18-23% | Reddit 21% | Wikipedia | Quora 14% | Forbes |
| Phind (코딩) | Stack Overflow 30%+ | GitHub | MDN | 공식 docs | — |
| HyperCLOVA X | Naver 블로그 | namu.wiki | 다음 카페 | 연합뉴스 | 한경 |

### 1.3 Top 10 인용 신호 우선순위

1. Referring domains 32K+ 권위 → 인용 3.5배
2. Semantic completeness (134-167단어 self-contained) → r=0.87, 4.2배
3. OAI-SearchBot/Claude-SearchBot/PerplexityBot Allow → 차단 = 0%
4. Entity density 15+ + Wikidata sameAs → 4.8배
5. Earned media (Tier-1) → top10 60% overlap
6. Freshness 30일 sweet spot → +40% citation
7. 3rd-party 권위 (Trustpilot/G2) → 인용 3배
8. Original data 3+ unique points → 인용 4배
9. YouTube/Reddit/GitHub (플랫폼별 분기) → 18.2%/44%/30%+
10. GPTBot/ClaudeBot Allow (학습 진입) → mention 채널

---

## 2. 액션 매트릭스 (효과 × 위험)

### 2.1 Strong White Hat (즉시 시작)

- Original Benchmark publish ★★★★★
- Dataset publish (HuggingFace/Zenodo) ★★★★★
- Wikidata Q-item + sameAs ★★★★★
- Citation laundering (podcast/conference) ★★★★
- Schema.org JSON-LD (Article/Organization/Person) ★★★★
- Semantic HTML5 (h1→h2→h3 + answer-first 40-75단어) ★★★★
- Living Documents (단일 URL 누적) ★★★★
- Awesome-list PR ★★★
- Programmatic fact pages (측정값 기반) ★★★
- robots.txt 정비 ★★★ (필수, 차단 = 0)
- IndexNow + Bing Webmaster + Google Search Console ★★★

### 2.2 Cautious Grey Hat (조건부)

- Reddit 1계정 disclosure 답변 (sock puppet 절대 금지)
- Disclosed sponsored content (FTC 의무 라벨)
- AI 보조 콘텐츠 + 인간 EEAT 30% 보강
- Wikipedia COI 공개 후 talk page 제안

### 2.3 Black Hat / Illegal (절대 금지)

| 전술 | 위험 |
|---|---|
| Prompt injection in published content | OpenAI/Anthropic ToS 명백 위반, 도메인 영구 제외, detection 모델 학술 입증. **단기 1-3개월 효과를 위해 12개월 자산 폐기** |
| Training data poisoning | 학술적 위험성 입증 (Carlini 2024-2025), 잠재 형사 처벌 |
| Wikipedia 미공개 paid editing | Wikimedia ToU 위반, 영구 차단 (2025년 400+ 계정 차단) |
| PBN / 매수 backlink | Google Penguin 실시간 deindexing, 발각 거의 100% |
| Astroturfing | FTC 2024 위반당 $51,744 |
| GitHub fake stars | StarScout 90.42% 자동 삭제, FTC 위반 |
| Sock puppet content network | 효과 감소 + 영구 ban |

---

## 3. neogenesis.app 특화 — 보유 자산 + 듀얼 구조

### 3.1 Unique citable asset 인벤토리 (8개)

| 자산 | 1차 자료성 | 인용 잠재력 | publish 가능? |
|---|---|---|---|
| quant-bot v11 라이브 PAPER mode telemetry | ★★★★★ | 매우 높음 (대체 불가) | Phase 0 통과 후 |
| EthicaAI Melting Pot mixed-safe 결과 | ★★★★★ | 학술 인용 자산 | 이미 publish |
| WhyLab Gemini 2.5 Docker 결과 | ★★★★★ | 학술 인용 자산 | 이미 publish |
| RAG Master Design v1 (이번 주 작성) | ★★★★★ | GEO/LLMO 1차 자료 | 즉시 |
| 6 SBU 운영 메트릭 (traffic/conversion/refresh) | ★★★★ | B2B aggregator 진입 | 익명화 후 |
| 9-Layer Kill Switch 데이터 | ★★★★★ | 외부 벤치마크 부재 | Phase 0 후 |
| AI fleet management 운영 패턴 (Sora 6대) | ★★★★ | early adopter 가치 | 즉시 |
| Agent Environment v2 pack | ★★★ | 합성 분석 | 즉시 |

**결론**: 이미 진입 자격 보유. 문제는 publish 인프라뿐.

### 3.2 도메인 듀얼 레이어 권장 구조

```
neogenesis.app/
├── /                      ← 기업 소개 (현재) — trust signal layer
├── /data/                 ← Neo Genesis Data Hub — 1차 자료 publish
│   ├── /quant/            ← finstack 라이브 telemetry
│   ├── /research/         ← EthicaAI/WhyLab + RAG 설계 + Agent Env v2
│   ├── /benchmarks/       ← State of X 분기 보고서
│   ├── /datasets/         ← HuggingFace 미러
│   ├── /agents/           ← Sora fleet 운영 인사이트
│   └── /sbu-metrics/      ← 6 SBU 운영 데이터 (익명화)
├── /llms.txt              ← 사이트 구조 hint
├── /llms-full.txt         ← 전체 콘텐츠 컴파일
├── /sitemap.xml
├── /.well-known/mcp.json  ← MCP server 자동 발견
└── /.well-known/security.txt
```

**규칙**:
- 모든 페이지 `Article` schema + Wikidata Q-ID `sameAs` 연결
- Markdown 동시 제공 (`/data/quant.md`)
- 30일 주기 의미 있는 갱신 (가짜 freshness 금지)
- `<time datetime="ISO">` 명시
- Statistics 3개+/500단어 강제 (publish 차단 룰)

### 3.3 진입 가능 niche Top 5 (12개월)

| Rank | Niche | SBU/자산 | ROI |
|---|---|---|---|
| 1 | 라이브 quant telemetry "1차 자료" | finstack + quant-bot | ★★★★★ |
| 2 | AI 윤리/안전 1차 연구 publish | aiforge + EthicaAI/WhyLab | ★★★★★ |
| 3 | AI 도구 비교 (Comparison) | toolpick | ★★★★ |
| 4 | GEO/LLMO 1차 측정 데이터 | RAG Master Design | ★★★★ |
| 5 | 한국어 AI dual-track | craftdesk + toolpick | ★★★ |

---

## 4. 12개월 롤아웃 (Phase 0~4)

### Phase 0 — Foundation (Week 1-4, 비용 $0)

- [ ] robots.txt 정비 (학습 + 검색 정책 결정)
- [ ] Schema.org JSON-LD (Organization + Article + Person, sameAs 연결)
- [ ] Wikidata Q-item 6개 (Neo Genesis 본체 + 6 SBU)
- [ ] sitemap.xml + lastmod ISO 8601 + RSS feed
- [ ] IndexNow API key + Vercel revalidate hook
- [ ] llms.txt + llms-full.txt 생성
- [ ] Cloudflare AI Crawl Control 활성화
- [ ] DIY 측정 protocol 구축 + 30일 baseline
- [ ] GA4/PostHog AI 채널 regex 분리
- [ ] Bing Webmaster + Google Search Console 등록

**Stop/Go**: 30일 baseline 확보 + 4 플랫폼 인용 1건 이상

### Phase 1 — Content Foundation (M2-3, 비용 $0)

- [ ] toolpick alternatives/comparisons/pricing 5개 허브 fact unit 강화
- [ ] `/data/research/` 에 EthicaAI/WhyLab/RAG Master Design publish
- [ ] HuggingFace dataset 1건 publish (RAG golden 50 또는 Korean LLM Citation)
- [ ] GitHub awesome-list 1개 PR (quant-bot v11 또는 Agent Env v2)
- [ ] Korea Newswire 보도자료 1건 (선택, owner 게이트)

### Phase 2 — Authority Building (M4-6, 비용 $0~)

- [ ] 첫 "State of X 2026" 분기 보고서 publish
- [ ] arXiv 프리프린트 1편
- [ ] Tier 1 영문 매체 1건 시도 (선택, owner 게이트)
- [ ] Podcast 출연 3-5회 + 트랜스크립트 publish
- [ ] G2/Capterra/TrustRadius SBU 등록

### Phase 3 — Scaling (M7-9)

- [ ] Programmatic fact pages 200+ (toolpick 자동 생성)
- [ ] MCP server publishing (`.well-known/mcp.json`)
- [ ] 분기 보고서 2편째
- [ ] Living Documents 정책 (URL 영구화)
- [ ] 한국어/영어 dual-track

### Phase 4 — Compound (M10-12)

- [ ] Wikipedia 영문 페이지 시도 (third-party 출처 충분 시)
- [ ] 분기 보고서 3편째
- [ ] AI 채널 LTV 측정 + 매출 attribution
- [ ] 유료 측정 도구 (Profound 등) ROI 입증 후 검토

---

## 5. 측정 KPI (12개월)

| Phase | 기간 | KPI | 임계값 |
|---|---|---|---|
| 0 | M1 | Citation Frequency baseline | prompt 30개 × 4 플랫폼, 30일 |
| 1 | M2-3 | SoV (자사 / 경쟁사 5개) | ≥ 카테고리 평균 |
| 2 | M4-6 | Sentiment + Hallucination | Negative ≤ 5%, Hallucination ≤ 2% |
| 3 | M7-9 | AI referral 전환율 | ≥ 4x organic |
| 4 | M10-12 | 12개월 SoV CAGR | ≥ 15% |
| 5+ | M12+ | AI 채널 LTV | ≥ organic LTV |

---

## 6. Stop/Go 게이트 5개

1. Phase 0 끝에 4 플랫폼 인용 0건 → DIY 측정 protocol 재설계
2. SoV 6개월간 카테고리 평균 미달 → niche 재선정
3. AI referral 전환율 < organic 1x → 듀얼 구조 재검토
4. 12개월 SoV CAGR < 5% → Phase 4 진입 보류, Phase 1-3 재실행
5. Black Hat 라벨 전술 발각 1회 → 즉시 도메인 자산 회수 비상 운영

---

## 7. owner 결정 게이트 (G2+ 만)

자율 진행 (G1, Standing Approval 범위):
- robots.txt / Schema / Wikidata / sitemap / IndexNow / llms.txt
- DIY 측정 (기존 API key)
- HuggingFace / arXiv / GitHub publish
- 콘텐츠 양산 + freshness refresh
- Cloudflare AI Crawl Control 정책
- G2/Capterra 등록

owner 게이트 (G2):
- Korea Newswire 보도자료 ($300-500/회) — Phase 1 시점
- Tier 1 영문 매체 PR (founder 시간 + 평판) — Phase 2 시점
- 유료 측정 SaaS 결제 (Profound $399+/월) — Phase 4 시점, ROI 입증 후
- Wikipedia 컨설턴트 ($2,500-5,000) — Phase 4 시점
- 자본 위험 동반 publication (quant 알파 디테일) — 절대 보류

---

## 8. 후속 자료

- 8 트랙 리서치 원본: 본 보고서 작성 시점 Claude Opus 4.7 세션 기록
- 관련 SSOT:
  - `.agent/knowledge/20260426_RAG_MASTER_DESIGN_v1.md` — 내부 RAG 인프라 (publish 인프라로 일부 활용)
  - `.agent/knowledge/20260426_FINANCIAL_ADVISOR_SYSTEM_v1.md` — quant 자산 publish 정책 의존
  - `.agent/knowledge/20260426_SBU_AUTONOMOUS_GROWTH_RULE.md` — Standing Approval 근거
  - `.agent/knowledge/AGENT_RUNTIME_OPTIMIZATION.md` — Agent Env v2 publish 자산
- 기술 stack 참조:
  - GEO 논문 arXiv 2311.09735, 2603.29979 (GEO-SFE), 2506.07446 (AFEV)
  - Profound / Otterly / Peec / Ahrefs Brand Radar 측정 도구 비교
  - 8 트랙 모든 출처는 Claude Opus 4.7 세션 reasoning context

## 9. 변경 이력

| 날짜 | 작성 | 변경 |
|---|---|---|
| 2026-04-27 | Claude Opus 4.7 (Strategy Lead) | v1 초안 작성. owner 자율 위임 + Standing Approval 근거 |
