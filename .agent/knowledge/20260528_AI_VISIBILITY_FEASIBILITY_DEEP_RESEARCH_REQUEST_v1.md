# Neo Genesis — AI 가시성/인용 실현가능성 심층연구 요청서 (v1)

> **Date**: 2026-05-28 (KST)
> **Author**: Strategy Lead Claude Opus 4.7
> **Status**: DRAFT — owner 승인 시 Phase 1 착수
> **Type**: Deep Research Request (현황분석 + 연구설계)
> **이 연구가 답할 결정**: AI 인용/가시성 전략을 (지속 / passive 유지 / 완전 폐기) 중 무엇으로 할 것인가, 그리고 1인·$0 자원을 어디에 쓸 것인가.
> **관련 SSOT**: `20260514_AI_CORPUS_CITATION_STRATEGY_v1.5.md`, `20260516_neogenesis_app_site_audit.md`, `20260516_blog_performance_audit.md`, `20260514_weekly_perplexity_protocol.md`

---

## 0. 요청 한 줄 (TL;DR)

무명·pre-revenue·1인 기업인 Neo Genesis가 **"AI(ChatGPT/Gemini/Claude/Perplexity)에 인용·노출되는 회사"가 되는 것이 실현 가능한 목표인지** 증거 기반으로 확정하고, 만약 현 시점에 비현실적(premature)이라면 **traction-first 대안 경로**를 도출하는 심층연구. 한 세션의 예비 검토(아래 §2.4)로 v2.0 pivot을 결정하기엔 무게가 커서 정식 심층연구로 확정한다.

---

## 1. 배경 — 왜 이 연구가 필요한가

1. NG는 ~2026-04-28부터 약 1개월간 "온사이트 최적화(Schema/llms.txt/blog)로 AI에 인용되자"는 v1 전략을 실행했다.
2. 측정 결과(2026-05-28 실쿼리): **organic AI 인용 0, 도메인 URL 인용 0** (§2.1).
3. 예비 feasibility 검토(2026-05-28): AI 인용은 *traction의 trailing indicator*이며, 무명 pre-revenue가 최적화로 만들 수 있는 leading lever가 아니라는 **"premature" 판정**(§2.4).
4. 이 판정이 맞으면 → AI 인용 전략 폐기/passive화 + 자원 재배치(v2.0 pivot). 틀리거나 부분적이면 → 정확히 어디를 고쳐야 하는지.
5. 이 결정은 owner의 향후 수개월 시간배분을 좌우하므로, **추측이 아닌 1차 자료 + 사례 + NG 자산 적합성**으로 확정해야 한다.

---

## 2. 현황 분석 (측정된 사실)

### 2.1 NG 측정 데이터 (`citations.sqlite3`, 2026-05-28 실쿼리)

| Provider | 유효응답 | 최근 8일 | organic 브랜드언급 | 도메인 URL 인용 | 채널 |
|---|---|---|---|---|---|
| openai (gpt-4o, daily cron) | 658 | +236 | **0 / 570 = 0%** | **0.00%** | training corpus |
| gemini (2.5-flash, daily cron) | 606 | +178 | **0 / 518 = 0%** | **0.00%** | training corpus |
| perplexity (web, 수동) | 12 | +10 | ~0 | 0% | live search |
| anthropic | 0 (키 없음) | — | — | — | — |
| **합계** | **1,276 유효** | +424 | **0 / 1,088** | **0 / 1,276** | |

- **organic 브랜드 언급 0/1,088**: 프롬프트가 "Neo Genesis"를 명명하지 *않은* 응답에서 우리 브랜드가 등장한 적 0건. (과거 SSOT의 "브랜드 픽업 12% STRONG"은 self-naming 프롬프트의 echo였음 — 2026-05-28 실측으로 정정됨.)
- **도메인 URL 인용 0/1,276**: neogenesis.app가 인용된 응답 0건 (전 기간).
- 측정 기간 1개월. cron(openai+gemini)은 건강하게 누적 중(8일 +424).

### 2.2 AI 인용 메커니즘 (2026 외부 실증 데이터)

| 인용을 만드는 요인 | 비중 / 배수 | 출처 |
|---|---|---|
| Earned media (편집/기사/"best of") | AI 인용의 **48%**, owned 대비 **6.5×** | Omniscient (23,000 인용 분석) |
| Reddit / 포럼 | **#1 소스, ~40% 빈도** | 5W Index 2026 |
| Top-15 도메인 집중 | 전체 AI 인용의 **68%** | 5W Index 2026 |
| Perplexity 최신성 | 인용의 **82%가 최근 30일** 콘텐츠 | authoritytech 2026 |
| 멀티플랫폼 (4+) | ChatGPT 추천 확률 **2.8×** | Omnibound GEO 통계 |
| owned content | AI 인용의 **23%뿐** | Omniscient |
| Google 랭킹↔AI 인용 중첩 | 70% → **<20%로 붕괴** (별개 게임) | 5W 2026 |

→ 핵심: AI 인용은 압도적으로 **"제3자가 너를 언급"**하는 신호(earned 48% + 커뮤니티)로 결정된다. owned 채널은 23%뿐이고, NG는 거의 100% owned에 의존.

### 2.3 NG 자산 인벤토리

**강점 (input은 우수)**
- 인프라: 11 SBU 라이브 + neogenesis.app (Schema best-in-class, llms.txt 114 links, 24 AI bots, 90-URL sitemap, 100% 200 OK).
- 연구자산: NeurIPS 제출 논문 2편(EthicaAI, WhyLab) + CC-BY-4.0 데이터셋 9개(HF) + Wikidata Q139569680/Q139569708 + Zenodo DOI.
- koreanllm AO-1 (W0 launch 준비, trilingual leaderboard).
- 측정 인프라(citation telemetry cron + 무료 Perplexity 채널 검증됨).

**약점 (output을 막는 구조)**
- Earned media 0, 커뮤니티(Reddit/HN/dev.to) presence 0.
- 매출 $0, 유료 고객 0, 트래픽 미미.
- 논문 2편 블라인드 심사 hold → arXiv/저자노출 금지 → 권위신호 동결.
- 무명(브랜드 인지도 ~0) → newsworthiness 부재 → PR 트리거 없음.

### 2.4 예비 판정 (한 세션 검토 — 본 심층연구가 stress-test 할 대상)

- AI 인용은 당길 수 있는 leading lever가 아니라 **real traction의 trailing indicator**.
- 무명 pre-revenue가 인용을 "최적화"로 만드는 것은 말 앞에 마차 두기. 시장 관심(사용자/매출/buzz) → earned media → 인용 순.
- **단 하나의 NG-고유 가능 경로**: original research(논문/데이터셋) = citation magnet. 블라인드 unhold 시 arXiv + Wikipedia notability로 진짜 권위 전환 가능. 단 timing은 외부(심사) 의존.
- **이 예비 판정은 web search 3건 + 1개월 측정에 기반** → 정식 심층연구로 confirm/refute 필요.

---

## 3. 핵심 연구 질문 (Research Questions)

| RQ | 질문 | 결정 연결 |
|---|---|---|
| **RQ1** | 예비 "premature" 판정이 맞나? **무명/소규모/저예산 주체가 AI 인용을 의도적으로 획득한 실제 사례**가 존재하나? 있다면 정확히 무엇을 했고, $0·1인 NG에 복제 가능한가? (실패 사례 포함) | D1 |
| **RQ2** | 4개 엔진별로 **NG 유형**(B2B SaaS + research lab)이 인용되는 **정량 임계 조건**은? (몇 개의 third-party 언급? 어떤 도메인 티어? 신규→인용 리드타임?) | D1 |
| **RQ3** | NG의 논문/데이터셋이 **블라인드 unhold 후** 인용 권위로 전환되는 **최대화 전략**은? (arXiv, Wikipedia notability 기준, HF, Papers-with-Code, Semantic Scholar, ar5iv, awesome-lists, ODML) | D3 |
| **RQ4** | AI 인용이 premature라면, NG의 **11 SBU + 연구자산 중 실제 traction/매출 경로가 가장 현실적인 자산**은? (집중 vs 분산; koreanllm/EthicaAI/WhyLab/ToolPick 등 비교) | D2 |
| **RQ5** | **$0 + 1인** 제약에서 owner 시간의 **최고 ROI 배분**은? AI 가시성에 쓸 시간 vs 매출 직결 작업의 기회비용. | D2 |
| **RQ6** | 어떤 **측정 가능한 조건**이 충족되면 "AI 인용 추구 재개"가 정당화되나? (re-entry trigger 설계) | D1/D3 |

---

## 4. 연구 범위 & 단계 (Phases)

| Phase | 내용 | 산출 | RQ |
|---|---|---|---|
| **P1 메커니즘 정밀화** | 2026 GEO/LLMO 1차 실증연구 + 엔진별 공식 source-selection 문서 + 인용 벤치마크 정량화 | 메커니즘 종합 md + 엔진별 임계조건 표 | RQ1-2 |
| **P2 사례 연구** | 무명→AI 가시성 달성/실패 케이스 매트릭스 (indie SaaS, 소규모 research lab, solo founder, 오픈소스 프로젝트). "무엇을 했나" 분해 | 사례 매트릭스 + 복제가능성 평가 | RQ1 |
| **P3 NG 자산 적합성 매핑** | 각 SBU/연구자산을 P1 임계조건에 대입 → feasibility 스코어카드 | feasibility 스코어카드 | RQ3-4 |
| **P4 대안 경로 모델링** | traction-first 경로 + AI-가시성 경로 ROI/시간 비교 (SSOT Revenue Path Research B1/C2/B3/D2와 정합) | ROI 비교표 + 시간배분 plan | RQ4-5 |
| **P5 의사결정 권고** | D1-D3 권고 + re-entry trigger + 90일 실행 plan | 의사결정 권고서 | RQ6 + 전체 |

### 방법론
- **1차 자료 우선**: 엔진 공식 문서 / 학술 / 측정 데이터. GEO 벤더 마케팅 글은 이해관계(self-interest) bias 주의 — 교차검증.
- **NG 측정 데이터 재분석**: `citations.sqlite3` 1,276행을 RQ2 임계조건에 비추어 재해석.
- **사례는 검증 가능한 것만**: 추정/일화 배제, 추적 가능한 증거 기반.
- **통제 실험(선택)**: 단일 고가치 페이지/자산에 최소 third-party 신호를 의도 투입 후 인용 변화 추적 (TOS·blind-review 준수 범위).

---

## 5. 제약 (연구가 반드시 준수)

1. **$0 예산** — 유료 API/SaaS/PR wire 불가. 무료·DIY 채널만 권고 대상.
2. **1인 owner 시간 = 진짜 병목** — 모든 권고는 시간 기회비용으로 평가.
3. **블라인드 심사 hold** — EthicaAI/WhyLab 논문·저자 신원 노출 권고 금지. unhold 트리거 이후 plan만 설계.
4. **TOS 준수** — 자동화 스크레이핑/스팸 시딩(가짜 Reddit/리뷰) 권고 금지 (계정 ban + 평판 위험).
5. **개인정보 분리** — owner 개인 법무/금융 컨텍스트 연구 입력 금지.

---

## 6. 산출물 (Deliverables)

1. 메커니즘 + 엔진별 임계조건 종합 (P1)
2. 무명→가시성 사례 매트릭스 + 복제가능성 평가 (P2)
3. NG 자산 feasibility 스코어카드 (P3)
4. traction-first vs AI-가시성 ROI/시간 비교 + 90일 plan (P4)
5. **의사결정 권고서**: D1(지속/passive/폐기) + D2(자원 재배치) + D3(research-asset 경로) + re-entry trigger (P5)
6. 각 Phase별 `.agent/knowledge/` md 박제 + 본 요청서 v2 업데이트

---

## 7. 의사결정 게이트 (이 연구가 owner에게 줄 결정)

- **D1**: AI 인용/가시성 전략 — 지속(active 투자) / passive 유지(무료 자동) / 완전 폐기?
- **D2**: passive·폐기 시 owner 시간을 어디로? (어느 SBU/연구자산 집중, B1/C2/B3 중)
- **D3**: research-asset 경로 — 블라인드 unhold 시 즉시 발동할 arXiv+Wikipedia+HF plan 확정?

---

## 8. 성공 기준

- 예비 "premature" 판정이 **1차 자료 + 사례로 confirm 또는 refute** (어느 쪽이든 valuable).
- owner가 D1-D3를 **confident하게 결정**할 수 있는 증거 제공.
- 권고가 **$0·1인·blind-hold 제약 안에서 실행 가능**.
- vendor 마케팅 hype가 아닌, NG의 실제 측정·자산에 정합.

---

## 9. 실행 메모 (다음 단계)

- 본 요청서 owner 승인 → **Phase 1부터 research agent 디스패치** (general-purpose/Explore 병렬) 또는 owner 외부 deep-research 툴 입력.
- Phase별 결과는 본 문서와 같은 폴더에 박제하고, 본 요청서를 index로 유지.
- **Reversibility**: 본 문서는 분석/요청서일 뿐 코드·운영 변경 0. 폐기 시 파일 삭제로 무영향.

---

### 부록 A — 출처 (메커니즘 §2.2)

- Omniscient Digital, "How LLMs Source Brand Information: 23,000+ AI Citations" — earned media 48% / owned 23% / 6.5×
- 5W "AI Platform Citation Source Index 2026" — top-15 도메인 68%, Reddit #1, Google↔AI 중첩 <20%
- authoritytech.io, "How to Get Cited in Perplexity AI 2026" — 실시간 retrieval, 최근 30일 82%
- Omnibound, "Generative Engine Optimization Statistics 2026" — 4+ 플랫폼 2.8×, 60일 내 near-zero→double-digit (단 earned-media 전제)

### 부록 B — NG 측정 재현 명령

```bash
cd D:/00.test/neo-genesis/scripts/geo_measure
python -c "import sqlite3; c=sqlite3.connect('citations.sqlite3'); print(c.execute('SELECT provider,COUNT(*) FROM measurements WHERE error IS NULL GROUP BY provider').fetchall())"
```
