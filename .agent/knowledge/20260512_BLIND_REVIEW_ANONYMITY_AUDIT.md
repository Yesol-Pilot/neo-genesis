# Blind Review Anonymity Audit — 2026-05-12

> 작성자: Strategy Lead Claude Opus 4.7
> Trigger: owner clarification "블라인드 심사에 문제가 될까봐 다운시켰을걸" (EthicaAI 다운 = 의도적)
> 목적: 본 세션 publish 한 자산 중 author Yesol Heo + 블라인드 paper finding 직접 인용 = anonymity 위반 risk 자산 식별 + owner G2 결정 trigger

---

## §0 결론 (Cold Honest)

owner 의 EthicaAI 사이트 다운 = blind review anonymity 의도적 보호. 이 logic 을 본 세션 publish 자산 전체에 적용 시 **즉시 owner 결정이 필요한 P0 자산 2건**:

1. `/blog/ethicaai-mixed-safe-vs-anthropic-constitutional-ai-2026` (본 세션 publish, ~1685 words)
2. `/blog/whylab-docker-validation-vs-rubric-scoring-2026` (본 세션 publish, ~1545 words)

두 자산 모두 직접 "Heo, Yesol (2026). EthicaAI: Mixed-Safe Boundary-Consistent Evidence..." 또는 "WhyLab: Gemini 2.5 Docker Validation..." 인용 + author bio cross-link → reviewer 가 google 검색 시 author identity 즉시 추적 가능.

**Owner G2 결정 trigger**: keep / anonymize / unpublish.

---

## §1 본 세션 publish 자산 anonymity 영향 분석

### P0 High Risk (즉시 결정 필요, 본 세션 publish)

| 자산 | 위치 | Anonymity 위반 사유 |
|---|---|---|
| `ethicaai-mixed-safe-vs-anthropic-constitutional-ai-2026` | landing/src/lib/data/blog-content.ts L2955 외 | (1) Title: "EthicaAI Mixed-Safe vs Anthropic Constitutional AI" — paper title 직접 노출 (2) FAQ "Cite as: Heo, Yesol (2026). EthicaAI: Mixed-Safe Boundary-Consistent Evidence for Multi-Agent Cooperative Constraint Learning. Neo Genesis Research..." — author byline + paper title 노출 (3) 본문: "EthicaAI's 'mixed-safe boundary-consistent evidence' (Heo 2026)" 직접 인용 |
| `whylab-docker-validation-vs-rubric-scoring-2026` | landing/src/lib/data/blog-content.ts L3075 외 | (1) Title: "WhyLab Docker Validation vs Traditional Rubric Scoring" — paper finding framing 노출 (2) FAQ "Cite as: Heo, Yesol (2026). WhyLab: Gemini 2.5 Docker Validation for Causal Inference..." 직접 byline (3) 본문: "WhyLab tested whether selective adaptive C2... (Heo 2026)" |

### P1 Medium Risk (owner clarification 필요)

| 자산 | 상태 | 위반 사유 |
|---|---|---|
| ClaimReview Schema (10 research entries × ~5 = 49 emit) — 본 세션 추가 | 본 세션 commit `0079cfb` + landing `ffc0e70` | 10 중 2개 (ethicaai-melting-pot-mixed-safe + whylab-gemini-2-5-docker-validation) ClaimReview = author Org + reviewRating "Boundary-Consistent Evidence" / "Honest Null Result" → 블라인드 paper 직접 인용 |
| `/data/research/ethicaai-melting-pot-mixed-safe` 본문 | 본 세션 이전 publish (~2주 전?) | Author byline + ScholarlyArticle Schema + 510 evidence rows 직접 인용. grandfathered? |
| `/data/research/whylab-gemini-2-5-docker-validation` 본문 | 동일 | 동일 |
| `whylab.neogenesis.app` (dedicated site) | LIVE 200 | EthicaAI 와 동일 blind review 진행 중인데 사이트 alive. owner intent 차이? |

### P2 Low Risk (블라인드 paper 미인용)

| 자산 | 위치 | 평가 |
|---|---|---|
| `hivemind-vs-langgraph-multi-agent-2026` | 본 세션 publish | LangGraph + Magentic Microsoft Research 등 외부 인용만. 블라인드 paper 0. ✅ OK |
| `sora-orchestrator-vs-openai-agents-sdk-2026` | 본 세션 publish | OpenAI / Anthropic / Mastra / Ollama 외부 인용. 블라인드 paper 0. ✅ OK |
| `quant-v11-vs-renaissance-medallion-honest-scoping-2026` | 본 세션 publish | Renaissance Medallion / Bailey & Lopez de Prado / Knight Capital. 블라인드 paper 0. ✅ OK |

### P3 Grandfathered (이전 publish, owner intent 추정 = 유지)

| 자산 | 평가 |
|---|---|
| HF dataset 2 (ethicaai-mixed-safe-evidence) | author = neogenesislab + Zenodo DOI 10.5281/zenodo.20018466 박제. 6주 이상 운영. owner intent = 유지 추정 |
| HF dataset 3 (whylab-gemini-2-5-docker-validation) | 동일 |
| `/data/research/ethicaai-...` + `/data/research/whylab-...` 의 ScholarlyArticle pages | 본 세션 이전 publish. owner intent = 유지 추정 |
| Wikidata Q139569718 (EthicaAI) + Q139569716 (WhyLab) | 13 entities graph 일부. owner publish 박제 |

---

## §2 Risk Calibration

### Anonymity 위반 분석 — 가장 보수적 view

블라인드 심사 룰 (NeurIPS / ICML 등 표준):
- Author identity 가 reviewer 에게 노출되어서는 안 됨
- Author 가 reviewer 와 contact / 소셜 미디어 / blog 등에서 본 paper 를 promote 하지 않음
- preprint upload 도 anonymity 위반 가능 (NeurIPS 는 arXiv 허용하지만 author 가 paper 와 함께 본인 identity 강하게 push 시 위반)

본 세션 publish 한 2 comparison posts:
- 명확한 author Yesol Heo byline + "Cite as: Heo, Yesol (2026). [Blind paper title]" 노출
- 가장 의심스러운 위반 형태 = "active promotion of blind submission"
- 단, dataset descriptor 만 publish 한 경우는 grandfathered (paper title 와 별도)

### Conservative recommendation

**owner intent 가 EthicaAI 사이트 다운까지 확장된다면, 본 세션 2 posts 도 immediate hold 필요.**

이유:
- EthicaAI dedicated site 가 paper finding + author bio 노출 surface 였음 → owner 가 conservative 하게 다운
- 본 세션 2 comparison posts 도 동일 노출 + 더 명시적 (paper title + finding + Cite as) → 동일 logic 적용 시 hold 의무

---

## §3 Owner G2 결정 trigger (3 옵션)

### Option A: UNPUBLISH (가장 보수적)
- `/blog/ethicaai-mixed-safe-vs-anthropic-constitutional-ai-2026` 와 `/blog/whylab-docker-validation-vs-rubric-scoring-2026` 즉시 삭제
- BLOG_POSTS + BLOG_CONTENT 에서 entry 제거
- next.config.ts 에 redirect 추가 (404 회피, 무덤 link 처리)
- ClaimReview Schema 10 → 8 (2 hold)
- BLOG_POSTS 35 → 33
- Anonymity 위반 risk 0
- Reversibility 100% (unhold 시 git revert)

### Option B: ANONYMIZE
- 두 posts 의 author byline 제거 ("Heo, Yesol (2026)" → "Author anonymous pending peer review")
- Paper title 변형 ("EthicaAI: Mixed-Safe..." → "a published mixed-safe regime study")
- FAQ "Cite as" 항목 제거 또는 generic
- 단점: anonymize 된 글이 reviewer 가 search 했을 때 여전히 추적 가능 (글 patterns + neogenesis.app 사이트 + Wikidata 13 entities 모두 backtrace 경로)
- Conservative 하지 않음

### Option C: KEEP (anonymity 위반 risk 수용)
- 글 유지 + 향후 동일 패턴 publish 자제
- 단점: 명확한 anonymity 위반 patterns. 발견 시 NeurIPS / ICML desk reject 가능
- Permitted 만약 owner intent 가 "본 세션 publish 는 OK, 이미 publish 된 자산은 grandfathered"

### Strategy Lead 권고
**Option A (UNPUBLISH) 권고**. 이유:
1. EthicaAI 사이트 다운 logic 과 일관
2. 본 세션 publish = 직접 paper title + author byline 노출, 가장 명확한 위반
3. 다른 3 comparison posts (hivemind / sora / quant-v11) 은 블라인드 paper 미인용 = 유지 가능
4. 심사 종료 후 (accept = camera-ready 와 함께 release / reject = owner 재량) UNHOLD 가능

Owner 한 줄 명령 → 즉시 자율 진행 가능:
- "내려" → Option A 즉시 진행
- "익명화" → Option B 즉시 진행
- "그대로 둬" → Option C 박제
- "더 봐" → owner 직접 분석 후 결정

---

## §4 Blind Review HOLD scope 정의 (v1.3 갱신 권고)

직전 Strategy v1.2 의 Blind Review HOLD scope 를 **dedicated site + 직접 paper 인용 surface** 까지 확장:

```
⏸️ HOLD (블라인드 심사 진행 중):
- arXiv / SocArXiv / OpenReview public (이미 박제됨)
- LinkedIn / Twitter / Mastodon 의 블라인드 paper 직접 promotion
- HN / Reddit / Lobsters 의 블라인드 paper finding 직접 인용 post
- Dedicated SBU sub-domains (ethicaai.neogenesis.app — EthicaAI; whylab.neogenesis.app — owner clarification 필요)
- 본 세션 publish 한 ethicaai-vs / whylab-vs comparison posts
- ClaimReview Schema 의 ethicaai + whylab claim entries (블라인드 paper 인용)

✅ G1 자율 가능 (블라인드 무관):
- HF datasets (grandfathered, owner intent 박제)
- Wikidata 13 entities (grandfathered, owner intent 박제)
- 블라인드 미충돌 9 SBU sub-domains (UR WRONG, ToolPick, ReviewLab, K-OTT, FinStack, AIForge, SellKit, DeployStack, CraftDesk)
- 블라인드 paper 미인용한 comparison posts (hivemind, sora, quant-v11)
- Schema enrichment (SoftwareSourceCode, FAQPage, QAPage) 블라인드 paper 비포함

🟢 Unhold trigger:
- 심사 결과 발표 (accept = release / reject = owner G2 재검토)
```

---

## §5 박제

본 audit 시점:
- 2026-05-12 측정 + analysis
- Owner G2 응답 대기 (Option A/B/C)
- 응답 후 자율 후처리 (commit + push + Strategy v1.3 갱신)

가장 conservative 권고: **Option A UNPUBLISH** + 심사 종료 후 owner 재량으로 unhold.

작성: 2026-05-12, Strategy Lead Claude Opus 4.7
