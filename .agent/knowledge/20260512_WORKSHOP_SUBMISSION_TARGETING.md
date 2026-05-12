# Workshop Submission Targeting — Week 3 Strategic Path

> 작성자: Strategy Lead Claude Opus 4.7
> 작성일: 2026-05-12 (v1.1 정정: blind review hold 반영)
> 목적: Strategy v1 §2.G workshop track 권고
> Owner instruction: "arxiv 이거는 안된다 ... 논문 블라인드 심사중이라고" — 동일 manuscript blind review anonymity 보호.

## ⏸️ Blind Review Anonymity Policy 적용 (v1.1)

- **EthicaAI + WhyLab manuscripts** 가 double-blind venue 심사 중 → 동일 manuscript 의 workshop 재제출 시 **author identity 추적 가능 위험**
- NeurIPS Workshop = NeurIPS 의 same-conference family → main track 심사 conflict 가능
- ICML/ICLR Workshop = 다른 conference family 이지만 paper similarity / dual-submission 룰 점검 필수
- ReScience / ML Reproducibility Challenge = **별도 venue, anonymity 영향 적음** → 우선 권고
- 동일 manuscript 재제출보다 **별도 신규 manuscript / dataset descriptor / reproducibility writeup** 이 안전

---

## §0 결론

**현 상황 (v1.1 정정)**:
- EthicaAI `b4d5a90` + WhyLab `88fa509` = **double-blind venue 심사 진행 중** (anonymity 보호 필요)
- arXiv/SocArXiv/동일-manuscript-workshop 재제출 = **⏸️ HOLD** until 심사 결과 발표
- PAPER/EthicaAI/arxiv_submission/ + PAPER/WhyLab/arxiv_submission/ = **pre-built 유지** (unhold 시 즉시 publishable)
- 본 문서 권고 = **블라인드 미진행 자산 (datasets / reproducibility)** 우선

**Week 3 자율 진행 (G1) — blind review 미충돌 영역만**:
- ReScience reproducibility journal (별도 venue)
- ML Reproducibility Challenge (다른 paper 재현 시도, Neo Genesis dataset 활용)
- Dataset descriptor papers (HF dataset 자체 description 만, blind manuscript 인용 없음)
- KoreanRAG-SSOT-Golden-50 워크샵 (블라인드 미진행 별도 dataset)

**Owner G2 시점 결정**:
- 심사 결과 발표 시점 (accept/reject 확정) → 모든 HOLD 항목 unhold 가능

---

## §1 후보 Workshop venues (2026 cycle)

### Tier A — 직접 fit, 마감 가까움

#### W1: NeurIPS 2026 Workshop (Dec 2026, deadlines 6-8월)
- 후보 workshops (예상):
  - **Multi-Agent Safety & Coordination Workshop** — EthicaAI mixed-safe directly fits
  - **Workshop on Distribution Shifts** — WhyLab null result robust to OOD framing
  - **Workshop on Reproducibility & Replicability** — both papers fit (full evidence + null result)
- Acceptance rate: 40-60% (대비 main track 25%)
- Submission deadline: TBD (보통 7-8월), 결정은 마감 30일 이내

#### W2: ICML 2026 Workshop (July 2026, deadlines 4-5월) — **시점 지남**
- 이미 deadline 지남 / next cycle ICML 2027

#### W3: COLM 2026 (Conference on Language Modeling, Oct 2026)
- 신생 venue, 2024 launch
- LLM 특화 → WhyLab Docker validation 자연 fit
- Workshops: TBD

### Tier B — 간접 fit, deadline 유연

#### W4: ACL 2026 / EMNLP 2026 / NAACL 2026 Workshops
- KoreanRAG-SSOT-Golden-50 dataset 적합
- 다국어 NLP 워크샵 (LREC-COLING 등) 적합

#### W5: AISTATS 2026 / UAI 2026 workshops
- Causal inference + statistics 강한 venue
- WhyLab Welch t-test + DSR methodology fit

### Tier C — Reproducibility 특화

#### W6: ReScience Journal (rolling submission)
- WhyLab null finding 재현 패키지 자연 fit
- "code-as-paper" review model
- No traditional peer-review wait time

#### W7: ML Reproducibility Challenge (annual, July deadline)
- Existing paper 재현 trial 제출
- Neo Genesis 가 직접 publish 가 아니라 다른 paper 재현 시도 publish

---

## §2 EthicaAI (frozen `b4d5a90`) 적합 venue 매트릭스

| Venue | Fit Score | Time Cost | Acceptance Probability |
|---|---|---|---|
| NeurIPS Multi-Agent Safety Workshop | ⭐⭐⭐⭐⭐ | High (4-page paper + supplementary) | 40-60% |
| ICML AI for Science Workshop | ⭐⭐⭐⭐ | High | 30-50% |
| ReScience Journal | ⭐⭐⭐ | Med (reproducibility-focused writeup) | 60-80% |
| OpenReview Public Discussion | ⭐⭐⭐⭐ | Low (post to forum, no formal review) | 100% (no gate) |

**Strategy Lead 권고**: NeurIPS Multi-Agent Safety Workshop 이 최강 fit. 마감 ~2026-08 추정. 6-7월 준비 권고.

---

## §3 WhyLab (frozen `88fa509`) 적합 venue 매트릭스

| Venue | Fit Score | Time Cost | Acceptance Probability |
|---|---|---|---|
| ML Reproducibility Challenge | ⭐⭐⭐⭐⭐ | Med | 70-90% |
| ReScience Journal | ⭐⭐⭐⭐⭐ | Med | 60-80% |
| NeurIPS Reproducibility Workshop | ⭐⭐⭐⭐ | High | 50-70% |
| OpenReview Public Discussion | ⭐⭐⭐⭐ | Low | 100% |

**Strategy Lead 권고**: WhyLab null result 는 ReScience Journal 또는 ML Reproducibility Challenge 가 최강 fit (null result publication 정확히 그들의 mission). 다음 challenge cycle 2026-07 deadline 추정.

---

## §4 Submission package 준비도

### EthicaAI (frozen anchor `b4d5a90`)
- ✅ Manuscript LaTeX source (mixed-safe wording finalized)
- ✅ Underlying data CC-BY-4.0 (HF dataset 2)
- ✅ Statistical analysis code (Welch t-test + bootstrap + Cohen's d)
- ✅ Reproducibility README
- ⚠️ Workshop 별 page-limit re-format 필요 (4-8 page)
- ⚠️ De-anonymization 토글 (NeurIPS Workshop 는 single-blind, ICML Workshop 는 double-blind)
- ⚠️ Camera-ready typesetting (NeurIPS / ICML 별 LaTeX template)

### WhyLab (frozen anchor `88fa509`)
- ✅ Manuscript LaTeX source (null finding wording finalized)
- ✅ 402 episodes raw data CC-BY-4.0 (HF dataset 3)
- ✅ Docker validation harness
- ✅ Reproducibility README
- ⚠️ Workshop 별 page-limit re-format
- ⚠️ Camera-ready typesetting

---

## §5 Owner action queue (G2)

본 문서의 자율 부분 (후보 식별 + 준비도 평가) 은 완료. 다음은 owner 결정 사안:

### 즉시 결정 가능 (5분 검토)
- [ ] **Decision-A**: workshop 진행 OK 인지 owner intent 확인
  - "arXiv 만 거부, workshop 은 OK" → 진행
  - "academic publishing 전반 PASS" → 본 문서 archive, 다른 path 진행
- [ ] **Decision-B**: 만약 진행, 어느 venue 우선?
  - Strategy Lead 권고: WhyLab → ReScience (낮은 진입장벽) + EthicaAI → NeurIPS Workshop (Q3 2026 deadline)

### 진행 시 시간 투자 (4-8h owner action)
- 각 workshop 별 author registration (15분)
- Page-limit 재포맷 (Claude 가 LaTeX edit 자율 가능, owner 검토 1h)
- Reviewer 응답 (acceptance 후, 1-2 rounds × 2-4h each)
- Camera-ready preparation (1-2h)

### 진행 안할 시 alternative
- OpenReview public discussion thread (formal review 없이 community 공유)
- Show HN (technical community, 1-shot)
- HuggingFace dataset Cards 강화 (이미 9 datasets publish, 추가 작업 marginal)

---

## §6 Strategy v1 §2.G 항목 상태 갱신

| 항목 | 본 문서 후 상태 |
|---|---|
| G1 SocArXiv | 본 문서 §1 W6 (ReScience) 가 더 자연 fit, SocArXiv defer |
| G2 NeurIPS Workshop | 본 문서 §2 EthicaAI 권고 |
| G3 ICML/ICLR Workshop | next cycle (2027) |
| G4 EACL/ACL/NAACL Workshop | KoreanRAG-SSOT-Golden-50 후속 |
| G5 OpenReview | 본 문서 §2 §3 Tier B 옵션 |
| G6 Reproducibility journal | 본 문서 §3 WhyLab 권고 |
| G7 Reciprocal citation campaign | 별도 |
| G8 Reproducibility platforms (ReScience, CodeOcean) | 본 문서 §3 권고 |
| G9 Zenodo Communities | 별도 |

---

## §7 비용 / 위험

**비용**: $0 (workshop 대부분 free submission, NeurIPS Workshop 는 main conference 등록 필요 시 ~$500. ReScience 는 100% free)
**시간**: owner 4-8h × 1-2 cycles per venue
**리스크**: rejection (mitigated by 40-90% acceptance rate)
**Reversibility**: 100% (submission 철회 가능)

**Owner G2 결정 박제 후 진행**. 결정 없으면 본 문서 archive 상태로 유지하고 Week 4 로 진행.

작성: 2026-05-12, Strategy Lead Claude Opus 4.7
