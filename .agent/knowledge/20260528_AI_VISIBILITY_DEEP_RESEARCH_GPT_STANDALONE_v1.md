# [GPT Deep Research 프롬프트] Neo Genesis — AI 가시성/인용 실현가능성 심층연구 (자기완결판 v1)

> **이 문서는 GPT Deep Research에 그대로 붙여넣는 단일 입력이다.** 외부 파일/내부 DB 참조 없이 자기완결적으로 작성되었다. (NG 내부 index 버전: `20260528_AI_VISIBILITY_FEASIBILITY_DEEP_RESEARCH_REQUEST_v1.md`)
> Date: 2026-05-28 · 작성: Neo Genesis Strategy Lead

---

## 0. 당신의 임무 (READ FIRST)

당신은 **Neo Genesis**라는 회사를 위한 독립 전략 심층연구자다. 다음을 지켜라:

1. 당신은 이 회사의 내부 파일·데이터베이스에 접근할 수 없다. **필요한 모든 맥락은 이 문서에 인라인으로 제공**되어 있다.
2. §3의 연구질문(RQ1–RQ6)에 답하기 위해 **영어권 1차 자료를 직접 웹 리서치**하라(엔진 공식 문서, 학술/측정 연구, 검증 가능한 사례). 마케팅·벤더 블로그는 이해관계 bias가 있으니 교차검증하고 가중치를 낮춰라.
3. §2.4의 "예비 판정"은 **확정이 아니라 당신이 stress-test(검증/반증)할 가설**이다. confirm이든 refute든 증거로 답하라.
4. **보고서는 한국어로**, 단 출처는 URL과 함께 명시하라. 추측과 사실을 구분하라.
5. 최종 산출은 §6의 출력 형식을 따르라.

---

## 1. Neo Genesis란? (회사 primer — 당신은 이 회사를 모른다고 가정한다)

- **정체**: AI-native 자동화 회사. **1명의 인간 창업자 + 자율 AI 시스템("HIVE MIND")**이 다수의 SaaS 제품을 동시 운영하는 "1인 멀티-프로덕트" 모델. 한국 소재. 개인사업자, **pre-revenue(매출 ~$0), 마케팅 예산 $0**.
- **메인 사이트**: neogenesis.app. **GitHub org**: Yesol-Pilot. **창업자**: 공개 인물(개인).
- **운영 제품(SBU) 11개** (전부 라이브 배포):
  1. ToolPick (toolpick.dev) — AI/SaaS 도구 비교 엔진
  2. ReviewLab — 데이터 기반 제품 리뷰
  3. K-OTT (kott.kr) — 한국 OTT 추천
  4. UR WRONG (ur-wrong.com) — AI 토론/논쟁 플랫폼
  5. WhyLab — 인과추론(causal inference) 도구/리서치
  6. EthicaAI — AI 윤리/멀티에이전트 안전 리서치
  7. FinStack — 핀테크 인프라
  8. AIForge — AI 개발 도구
  9. CraftDesk — 크리에이티브 오퍼레이션
  10. DeployStack — DevOps 플랫폼 비교
  11. SellKit — 이커머스 성장 스택
  - (+ koreanllm.org — 한·영·일 trilingual LLM/임베딩/리랭커 리더보드, 신규 출시 준비 중)
- **연구 자산**: NeurIPS 2026 제출 논문 2편(① EthicaAI: 멀티에이전트 mixed-safe 협력; ② WhyLab: Docker 기반 코드검증) + **HuggingFace CC-BY-4.0 공개 데이터셋 9개**(org: neogenesislab) + **Wikidata 엔티티 2개**(회사 Q139569680, 창업자 Q139569708) + Zenodo DOI.
- **목표(원래 가설)**: 우수한 구조화 데이터(Schema.org)·콘텐츠로 **AI(ChatGPT/Gemini/Claude/Perplexity)에 권위 있는 출처로 인용**되게 만들어 → 트래픽·신뢰 → (장기) 매출.

---

## 2. 현재 상황 — 내부 측정·자산 (외부에서 구할 수 없는 데이터; 사실로 받아들이되 해석은 검증하라)

### 2.1 AI 인용 측정 데이터 (자체 telemetry, 약 1개월, 2026-04-28 ~ 05-28)

4개 AI 엔진에 동일한 30개 시드 프롬프트를 반복 질의하고 응답에 NG 브랜드/도메인이 등장하는지 측정.

| 엔진 | 유효 응답 수 | organic 브랜드 언급 | NG 도메인 URL 인용 |
|---|---|---|---|
| OpenAI (gpt-4o) | 658 | **0 / 570 = 0%** | **0.00%** |
| Google Gemini (2.5-flash) | 606 | **0 / 518 = 0%** | **0.00%** |
| Perplexity (web) | 12 | ~0 | 0% |
| Anthropic Claude | 0 (API키 없음) | — | — |
| **합계** | **1,276 유효** | **0 / 1,088** | **0 / 1,276** |

- **organic 브랜드 언급 0/1,088**: 프롬프트가 "Neo Genesis"를 명시하지 *않은* 응답에서 NG가 등장한 적 0건. (NG를 명명한 프롬프트에서만 echo로 등장 → 그건 organic 픽업이 아님.)
- **도메인 인용 0/1,276**: neogenesis.app가 출처로 인용된 적 0건.
- 라이브 관찰: 프롬프트가 NG 제품명을 명시하면(예 "ToolPick vs G2") AI가 그 제품을 *서술*하긴 하나(가끔 호의적), **출처는 항상 제3자 사이트**(billionverify, voxarena 등)이고 **NG 자체 도메인은 인용 안 함**. "EthicaAI" "K-OTT"는 동명의 다른 엔티티로 오인되기도 함(name collision).

### 2.2 자산 상태

- **온사이트 인프라 = 최상급**: 11개 사이트 라이브(HTTP 200 100%), Schema.org(BlogPosting/Organization/Dataset 등) 풍부, llms.txt(114 링크)·llms-full.txt(11K단어)·sitemap(90 URL)·robots.txt(AI 봇 24종 허용). 즉 **AI가 읽기 좋은 형태는 완비**.
- **off-site(외부 권위) = 거의 0**: 언론/편집 보도 0, Reddit·HN·dev.to 등 커뮤니티 organic 언급 0, 제3자 백링크 미미(자사 GitHub repo 3곳 cross-ref만).
- **논문 2편 = double-blind 심사 hold**: 익명 심사 중이라 arXiv 공개·저자 신원 노출 불가(심사 종료 전까지). → 잠재적 권위자산이 동결 상태.
- **무명**: 브랜드 인지도 ~0 → 뉴스가치(newsworthiness) 부재.

### 2.3 우리가 외부에서 미리 확인한 메커니즘 (당신이 정밀 검증·갱신할 출발점)

2026년 AI 인용/가시성 관련 외부 데이터(검증 필요):
- earned media(편집·기사·"best of")가 AI 인용의 **~48%**, 자사 콘텐츠 대비 **~6.5배** 더 인용됨. 자사 콘텐츠는 **~23%**뿐.
- **Reddit이 #1 소스(~40% 빈도)**, top-15 도메인이 전체 AI 인용의 **~68%** 차지(극단적 집중).
- Perplexity는 실시간 retrieval, 인용의 **~82%가 최근 30일** 콘텐츠.
- 4개 이상 플랫폼에 존재 시 ChatGPT 추천 확률 **~2.8배**.
- Google 검색 랭킹과 AI 인용 출처의 중첩이 70% → **<20%로 붕괴**(별개의 게임).
- 외부 진단(Common Crawl 관계자): NG의 핵심 gap은 **"incoming links 부재"**.

### 2.4 우리의 예비 판정 (= 당신이 stress-test 할 핵심 가설)

> **가설**: AI 인용은 의도적으로 당길 수 있는 *leading lever*가 아니라 **real traction(시장 관심·사용자·매출)의 trailing indicator**다. 무명·pre-revenue·1인 기업이 온사이트 최적화나 측정 자동화로 AI 인용을 "만들" 수는 없다. 인용은 earned media·커뮤니티 언급(=제3자가 너를 얘기함)에서 오는데, 그건 회사가 먼저 시장에서 의미를 가져야 발생한다. 단 하나의 NG-고유 예외 경로는 **original research(논문·데이터셋)를 citation magnet으로 쓰는 것**인데, 이는 블라인드 심사 unhold + 배포 노력에 의존한다.

이 가설이 맞다면 → NG는 AI 인용 추구를 (중단/passive화)하고 traction에 집중해야 함. 틀리거나 부분적이면 → 정확히 무엇을 바꿔야 하는지.

---

## 3. 연구 질문 (RQ1–RQ6) — 이 연구가 답해야 할 것

- **RQ1 (사례·반증)**: 무명·소규모·저예산(<$1k/mo) 주체가 **AI 인용/가시성을 의도적으로 획득한 검증 가능한 실제 사례**가 존재하는가? 존재한다면 정확히 *무엇을* 했고(채널·시간·비용), **$0·1인 Neo Genesis가 복제 가능한가?** 실패·정체 사례도 포함하라. (가설 §2.4를 confirm/refute)
- **RQ2 (엔진별 정량 임계)**: ChatGPT/Gemini/Claude/Perplexity 각각에서 **NG 유형(B2B SaaS 비교엔진 + 소규모 research lab)**이 인용되기 위한 **정량적 임계 조건**은? (몇 개의 제3자 언급/어떤 도메인 티어/신규 콘텐츠→인용 리드타임/training vs retrieval 차이)
- **RQ3 (연구자산 경로)**: NG의 논문·데이터셋이 **블라인드 심사 종료 후** 인용 권위로 전환되도록 하는 **최대화 전략**은? (arXiv, Wikipedia notability 충족 기준, HuggingFace, Papers with Code, Semantic Scholar/OpenAlex, awesome-lists 등 — 각 채널의 실제 인용 기여도)
- **RQ4 (대안: traction-first)**: AI 인용이 현 시점 premature라면, NG의 11개 SBU + 연구자산 중 **실제 traction/매출 경로가 가장 현실적인 자산**은 무엇이며 그 이유는? (집중 vs 분산; 1인 운영 한계 고려)
- **RQ5 (ROI·시간배분)**: **$0 예산 + 1인(시간이 진짜 병목)** 제약에서, owner 시간의 **최고 ROI 배분**은? "AI 가시성에 쓸 시간" vs "매출 직결 작업"의 기회비용을 정량/정성 비교하라.
- **RQ6 (재개 트리거)**: 어떤 **측정 가능한 조건**이 충족되면 "AI 인용 적극 추구 재개"가 정당화되는가? (re-entry trigger 설계 — 예: 특정 traction 지표, 블라인드 unhold, 특정 백링크 임계)

---

## 4. 범위·방법·권장 단계

- **P1 메커니즘 정밀화**: 4개 엔진의 source-selection을 1차 자료로 확정(RQ2). 벤더 통계는 교차검증.
- **P2 사례 매트릭스**: 무명→AI 가시성 달성/실패 케이스 수집·분해(RQ1). "복제 가능성(NG 제약 하)" 컬럼 필수.
- **P3 NG 자산 적합성**: 각 SBU/연구자산을 P1 임계조건에 대입한 feasibility 스코어(RQ3–4).
- **P4 대안 ROI 모델링**: traction-first vs AI-가시성 경로의 시간·비용·기대효과 비교(RQ4–5).
- **P5 의사결정 권고**: 아래 §6 형식의 권고 + re-entry trigger(RQ6).
- **방법 원칙**: 1차 자료 우선 / 마케팅 hype 배제 / 추측과 사실 구분 / NG의 실제 측정(§2.1)과 정합.

---

## 5. 절대 제약 (위반하는 권고는 무효)

1. **$0 예산** — 유료 PR wire·SaaS·API를 *전제*로 한 권고는 별도 표기하고 무료 대안을 우선 제시.
2. **1인 owner 시간 = 병목** — 모든 권고를 "owner가 주당 몇 시간 써야 하나"로 환산.
3. **블라인드 심사 hold** — 논문 2편의 저자 신원·소속을 노출하거나 심사 중 arXiv 공개를 권하는 등 **double-blind 익명성을 깨는 행위 권고 금지**. unhold *이후* plan만 설계.
4. **TOS·윤리 준수** — 가짜 Reddit/리뷰 시딩, 자동 스크레이핑 스팸, 매수 백링크 등 **조작적/규정위반 전술 권고 금지**(계정 ban·평판 훼손 위험).
5. 개인(창업자) 사생활·법무·금융 정보는 연구 범위 밖.

---

## 6. 기대 산출물 / 출력 형식

다음을 포함한 한국어 보고서:
1. **Executive verdict** — 가설 §2.4를 confirm/refute (증거 요약).
2. **엔진별 인용 임계조건 표** (RQ2).
3. **무명→가시성 사례 매트릭스** (사례 / 무엇을 했나 / 비용·시간 / NG 복제가능성 / 결과) (RQ1).
4. **NG 자산 feasibility 스코어카드** (자산 / 인용 가능성 / traction 가능성 / 권고) (RQ3–4).
5. **의사결정 권고** — 3개 결정에 명확히 답:
   - D1: AI 인용 전략 = 적극 지속 / passive 유지 / 완전 폐기?
   - D2: (passive·폐기 시) owner 시간을 어느 자산/경로에 집중?
   - D3: 연구자산(논문·데이터셋) 경로 — 블라인드 unhold 시 즉시 발동할 plan?
6. **re-entry trigger** — 측정 가능한 재개 조건 (RQ6).
7. **출처 목록** — 모든 핵심 주장에 URL.

## 7. 성공 기준

- 예비 가설이 **1차 자료 + 검증 가능한 사례**로 confirm 또는 refute된다(어느 쪽이든 valuable).
- 권고가 **$0·1인·blind-hold 제약 안에서 즉시 실행 가능**하다.
- vendor hype가 아니라 NG의 실제 측정(§2.1)·자산(§2.2)에 정합한다.
- owner가 D1–D3를 **자신 있게 결정**할 수 있는 근거를 제공한다.
