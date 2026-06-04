# [GPT Deep Research 프롬프트] Neo Genesis — 글로벌 AI 유입 트래픽 극대화 전략 심층연구 (자기완결판 v1)

> **이 문서는 GPT Deep Research에 그대로 붙여넣는 단일 입력이다.** 외부 파일/내부 DB 참조 없이 자기완결적이다.
> Date: 2026-05-28 (KST) · 작성: Neo Genesis Strategy Lead

---

## 0. 당신의 임무 (READ FIRST)

당신은 **Neo Genesis(이하 NG)**를 위한 독립 전략 심층연구자다.

1. 당신은 NG의 내부 파일·DB에 접근할 수 없다. **필요한 모든 맥락은 이 문서에 인라인**되어 있다.
2. **목표**: NG가 **"AI 시스템으로부터 유입되는 트래픽(AI-referral traffic)을 극대화"**하는 현실적 경로를 도출하라. 야망은 **"글로벌에서 AI 유입 트래픽을 가장 많이 확보하는 사이트"**이지만, **그 #1이 실제로 가능한지부터 정직하게 평가**하고, 불가능하면 *현실적으로 도달 가능한 최대치와 경로*를 제시하라.
3. §3의 연구질문(RQ1–RQ7)에 답하기 위해 **영어권 1차 자료를 직접 웹 리서치**하라(엔진/플랫폼 공식 문서, 트래픽·referral 분석 연구, 검증 가능한 사례). 마케팅·벤더 블로그는 이해관계 bias가 있으니 교차검증하고 가중치를 낮춰라.
4. **필수 가드레일** (반드시 준수):
   - **Falsify-first**: "$0·1인·무명도 AI 트래픽 선두가 될 수 있다"는 낙관 가설을 *먼저 깨려고* 증거를 찾은 뒤, 못 깨면 그때 인정하라.
   - **생존편향 차단**: 성공담만 모으지 말고 실패·정체 사례를 반드시 포함. 비교 대상은 **무명·$0~저예산·1인/소규모만** 채택(자금력 있는 브랜드 제외). 사례가 희소하면 *억지로 채우지 말고 실제 건수를 보고*하라 — 희소성 자체가 증거다.
   - 추측과 사실을 구분하고, 점추정이 불가하면 범위로 답하라.
5. 보고서는 **한국어**로, 모든 핵심 주장에 **출처 URL**을 붙여라. 최종 산출은 §7 형식을 따르라.

---

## 1. 핵심 용어 정의 (혼동 방지 — 반드시 이 정의로 분석)

**AI-referral traffic** = AI 제품/표면에서 NG 사이트로 *유입되는 실제 방문*. 두 종류로 분리해 분석하라:

- **(경로 A) Citation-click 트래픽**: 사람이 ChatGPT/Perplexity/Gemini/Google AI Overviews/Copilot 등의 **답변 안 출처 링크를 클릭**해 사이트로 들어옴. (전제: 인용 + 클릭 둘 다 필요)
- **(경로 B) Agent/bot 트래픽**: AI 에이전트·봇이 NG의 **API/데이터/페이지를 프로그램적으로 fetch**(도구 호출·데이터 수집·작업 수행). (전제: 에이전트가 NG를 *쓸 이유*가 있어야)

이는 "AI가 NG를 *인용*하는가"(가시성/vanity)와 다른, **측정 가능한 비즈니스 outcome(방문 수)**다. 두 경로의 메커니즘·feasibility·ROI가 다르므로 **항상 분리**해서 다뤄라.

---

## 2. Neo Genesis란? (primer — 당신은 이 회사를 모른다고 가정)

- **정체**: AI-native 자동화 회사. **1명의 인간 창업자 + 자율 AI 시스템("HIVE MIND")**이 다수 SaaS를 동시 운영. 한국 소재. **pre-revenue(매출 ~$0), 마케팅 예산 $0**.
- **메인 도메인**: neogenesis.app. **GitHub org**: Yesol-Pilot. 창업자는 공개 인물.
- **운영 제품(SBU) 11개** (대부분 neogenesis.app **서브도메인** → AI 트래픽이 NG 패밀리로 집계됨):
  | 제품 | 도메인 | 분야 |
  |---|---|---|
  | ToolPick | toolpick.dev (독립) | B2B SaaS 비교 엔진 (이미 `/api/tools` 에이전트-호출 엔드포인트 존재) |
  | UR WRONG | ur-wrong.com (독립) | AI 토론 플랫폼 |
  | K-OTT | kott.kr (독립) | 한국 OTT 추천 |
  | ReviewLab | review.neogenesis.app | AI 제품 리뷰 |
  | WhyLab | whylab.neogenesis.app | 인과추론 SaaS/리서치 |
  | EthicaAI | ethica.neogenesis.app (BETA) | AI 윤리 리서치 |
  | FinStack | finstack.neogenesis.app | 핀테크 도구 리뷰 |
  | AIForge | aiforge.neogenesis.app | AI 도구 분석 |
  | SellKit | sellkit.neogenesis.app | 이커머스 도구 리뷰 |
  | DeployStack | deploystack.neogenesis.app | DevOps 도구 리뷰 |
  | CraftDesk | craftdesk.neogenesis.app | 디자인 도구 리뷰 |
  | (+ koreanllm.org) | 독립 | 한·영·일 LLM 리더보드 (출시 준비) |
- **연구 자산**: NeurIPS 2026 제출 논문 2편(EthicaAI 멀티에이전트 안전; WhyLab Docker 검증) + **HuggingFace CC-BY-4.0 데이터셋 9개**(org: neogenesislab) + **Wikidata 엔티티 다수**(회사 Q139569680 외 SBU별 Q-ID).
- **온사이트 인프라 = 최상급**: Schema.org 풍부, llms.txt/llms-full.txt, sitemap(90 URL), robots.txt(AI 봇 24종 허용), 100% 200 OK.

---

## 3. 현재 상황 (내부 사실 + 이번 사전조사 — 사실로 받되 해석은 검증)

### 3.1 NG 현재 AI 트래픽 ≈ 0
- 자체 telemetry(약 1개월, 4개 엔진, 1,276 유효응답): **비보조 브랜드 언급 0 / 도메인 인용 0** → citation 0 → **citation-click 트래픽도 사실상 0**.
- **측정 caveat(중요)**: 위 telemetry는 OpenAI/Gemini **raw API(검색·그라운딩 OFF)**로 측정 → *원래 citation이 안 나오는 표면*이었다. 즉 "URL 인용 0"의 1/3은 표면 선택 artifact. **search/grounding-enabled 표면에서 재측정 전에는 절대화 금지.** (단 organic 브랜드 기억 0과 Perplexity(grounded, n=12) 0은 유효.)

### 3.2 사전조사한 메커니즘 (당신이 정밀 검증·갱신할 출발점)
- earned media(편집/기사/"best of")가 AI 인용의 **~48%**, owned 대비 **~6.5배**. owned 콘텐츠는 **~23%**뿐.
- **Reddit이 #1 소스(~40%)**, top-15 도메인이 AI 인용의 **~68%** 차지(극단적 집중).
- Perplexity는 실시간 retrieval, 인용의 **~82%가 최근 30일** 콘텐츠 → **클릭 링크를 가장 잘 보내는 엔진** 후보.
- 4개+ 플랫폼 존재 시 추천 확률 **~2.8배**. Google 검색랭킹↔AI 인용 출처 중첩 70%→**<20%**(별개 게임).

### 3.3 강점/약점
- **강점**: 인프라 최상급 / 차별 연구자산(논문·데이터셋) / **agent-readability 씨앗**(ToolPick `/api/tools`) / 서브도메인 다수(트래픽 집계 유리).
- **약점**: 무명(브랜드 인지 ~0) / **외부 권위·earned media·커뮤니티 언급 0** / 매출 0 / 논문 2편 **double-blind 심사 hold**(arXiv·저자노출 불가).

### 3.4 사전 판정 (= 당신이 stress-test 할 가설)
> citation(경로 A)으로 무명 NG가 AI 트래픽을 *직접* 끌어오는 건 현 시점 premature(외부 권위 필요, traction의 후행). 반면 agent-utility(경로 B)는 "유명함"이 아니라 "유용함"의 게임이라 *만들 수 있어* 더 현실적이다. 단 두 경로 다 **발견·채택(distribution)**이 필요하고, "글로벌 #1"은 stretch일 가능성이 높다. 또한 연구자산 경로의 인용·트래픽 크레딧은 대체로 **arXiv/HuggingFace가 가져가지 neogenesis.app이 아닐 수 있다**(간접 유입).

---

## 4. 연구 질문 (RQ1–RQ7)

| RQ | 질문 |
|---|---|
| **RQ1 (메커니즘·클릭률)** | AI 제품별(ChatGPT search·Perplexity·Gemini·Google AI Overviews·Copilot·AI agents)로 *클릭 가능한* referral 트래픽을 실제로 얼마나 보내는가? **zero-click(답변 내 완결) 비율**은? 어떤 콘텐츠 유형이 zero-click을 깨고 클릭/방문을 유발하는가? (경로 A·B 분리) |
| **RQ2 (벤치마크·사례)** | 현재 AI-referral 트래픽을 *가장 많이* 받는 사이트 유형과 공통점은? **무명·$0~저예산·1인/소규모** 중 의미있는 AI 트래픽을 확보한 사례가 존재하는가? 있다면 *정확히 무엇을 했고* $0·1인 NG가 복제 가능한가? (실패·정체 사례 포함, 생존편향 차단, 성공률 범위 추정) |
| **RQ3 (천장·현실 목표)** | $0·1인·무명 신규 진입자가 현실적으로 도달 가능한 AI-referral 트래픽 **상한**은? **"글로벌 #1"은 가능한가**, 아니면 어떤 **니치/버티컬**에서만 의미있는 점유가 가능한가? 현실적 목표선을 제시하라. |
| **RQ4 (경로 B: agent/utility)** | 에이전트가 호출하는 **API/MCP/구조화 데이터**로 "agent 트래픽"을 확보하는 게 citation-click보다 NG에 현실적인가? 에이전트는 이런 유틸리티를 **어떻게 발견·채택**하는가(MCP 레지스트리·도구 디렉토리·통합)? 무명 주체의 검증 가능한 사례는? |
| **RQ5 (NG 자산 적합성)** | NG의 11 SBU + 연구자산 + agent-utility 후보 중, **AI 트래픽 유치에 가장 현실적인 자산**은? 1인 체제에서 집중할 최대 묶음은? (자산별 feasibility 스코어카드) |
| **RQ6 (측정·트리거)** | AI-referral 트래픽을 **어떻게 측정**하는가(GA4 referrer 분석, 서버 로그의 AI user-agent, 엔진별 추적 한계)? 어떤 **측정 가능한 임계**가 "이 경로가 작동한다"의 증거이고, 재투자/중단 규칙(트리거)은? |
| **RQ7 (ROI·시간배분)** | $0·1인 시간 기준, **경로 A(citation-click) vs 경로 B(agent-utility) vs 비-AI 채널**의 상대 ROI는? owner 주당 시간을 어디에 배분해야 기대 트래픽이 최대인가? |

---

## 5. 권장 단계

- **P1 메커니즘**: 엔진별 referral 송출·zero-click·클릭 유발 요인 정밀화(RQ1). 공식 문서 + 트래픽 분석 1차 자료 우선.
- **P2 벤치마크·사례 매트릭스**: AI 트래픽 상위 사이트 + 무명·소규모 사례(성공/실패)(RQ2). "복제가능성(NG 제약 하)" 컬럼 필수.
- **P3 천장 산정 + 경로 B 조사**: 현실적 상한 + agent-utility 채택 경로(RQ3–4).
- **P4 NG 자산 적합성 스코어카드**(RQ5).
- **P5 측정 plan + ROI + 의사결정 권고 + 트리거**(RQ6–7).

---

## 6. 절대 제약 (위반하는 권고는 무효)

1. **$0 예산** — 유료 PR/SaaS/광고를 전제한 권고는 별도 표기 + 무료 대안 우선.
2. **1인 owner 시간 = 진짜 병목** — 모든 권고를 "주당 몇 시간"으로 환산.
3. **블라인드 심사 hold** — 논문 2편의 저자 신원·소속 노출 또는 심사 중 arXiv 공개 권고 금지. unhold *이후* plan만.
4. **TOS·윤리 준수** — 가짜 Reddit/리뷰 시딩, 봇 트래픽 조작, 매수 백링크, 클로킹 등 **조작/규정위반 전술 권고 금지**.
5. **vanity 금지** — "봇이 크롤만 많이 함"은 트래픽 성과 아님. *사람 방문 또는 에이전트의 의미있는 호출*만 outcome으로 인정.
6. 창업자 개인 사생활·법무·금융 정보는 범위 밖.

---

## 7. 기대 산출물 / 출력 형식 (한국어 보고서)

1. **Executive verdict** — §3.4 가설 confirm/refute + "글로벌 #1 가능한가"에 직답 + 현실적 목표선.
2. **엔진별 referral·zero-click·클릭유발 표** (RQ1, 경로 A/B 분리).
3. **AI 트래픽 사례 매트릭스** (사이트/유형 / 무엇을 했나 / 비용·시간 / NG 복제가능성 / 결과 / 성공률 범위) (RQ2).
4. **현실적 천장 + 경로 B(agent-utility) 채택 경로** (RQ3–4).
5. **NG 자산 feasibility 스코어카드** (자산 / 경로 A 점수 / 경로 B 점수 / traction ROI / 권고) (RQ5).
6. **AI 트래픽 측정 plan** (GA4 referrer + AI user-agent 로그 + 한계) (RQ6).
7. **의사결정 권고 + 측정 가능한 재투자/중단 트리거 + owner 시간배분(주당)** (RQ6–7).
8. **출처 목록** — 모든 핵심 주장에 URL.

## 8. 성공 기준

- §3.4 가설이 **1차 자료 + 검증 가능한 사례**로 confirm/refute된다(어느 쪽이든 valuable).
- "글로벌 #1 가능?"에 **정직한 직답** + 현실적 목표·경로 제시.
- 권고가 **$0·1인·blind-hold 제약 안에서 즉시 실행 가능**.
- vanity(봇 크롤 수)가 아니라 **실제 유입(사람 클릭 / 에이전트 의미있는 호출)** 기준.
- owner가 "어디에 주당 시간을 쓸지" 자신 있게 결정할 근거 제공.
