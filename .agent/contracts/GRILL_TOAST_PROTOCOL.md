# Grill & Toast Protocol (GTP)

> **Status**: v2.0 — re-canonicalized 2026-05-06 KST after disk loss (v1.0~v1.4 박제 untracked, manual deletion 또는 system cleanup 으로 손실)
> **Honest disclaimer**: 본 v2.0 은 v1.0~v1.4 의 substance (3 layers + 5+7 dimensions + 4 lesson entries) 를 컨텍스트 summary + handoff.md + Charter ledger references 로 복원. 일부 v1.0 본문 wording 의 정확 복원은 어려움. **이번 재박제 후 즉시 git commit 의무** (untracked 재발 방지).
> **Subordinate to**:
> 1. `.agent/NEO_MASTER_RULES.md` (top SSOT)
> 2. `.agent/contracts/COLLABORATION_CONTRACT.md`
> 3. Direct owner instructions

---

## §0 Owner mandate (2026-05-04 KST)

> "내 명령이나 너의 답변을 객관적이고 독립적으로 그릴링, 토스팅 해주는 프로세스가 필요"

**Motivating example**: 2026-05-04 NeurIPS 2026 + TMLR paper submission 직후 owner 가 "논문 내 도표들도 시각적으로 확인했어?" 질문 → Director 가 visual scan 안 하고 "READY" 박제 → 7건 P0/P1 visual defect 발견 (WhyLab Fig 1 TikZ z-order / WhyLab Fig 2 phase diagram colorbar / WhyLab Fig 4 Docker p=1.000 / WhyLab Appendix H 빈 section / EthicaAI Fig 2(a) "Indi" label truncation / EthicaAI Fig 4 spider chart "Fig 22" mismatch / EthicaAI Section U.1 path truncation). Re-upload 필요 + owner trust impact.

**Lesson**: Director 의 self-consistent claim (LaTeX compile 통과, syntax OK, regression test PASS) 만으로는 fundamental defect catch 불가. **객관적 + 독립 + 적대적** 3-layer audit 필수.

---

## §1 Layer 1 — Self-Grill (default, every claim)

### §1.1 Trigger
모든 다음 claim 전 의무:
- "READY" / "DONE" / "VERIFIED" / "통과" / "완료"
- Phase boundary transition (e.g., Phase 0 → Phase 1)
- SSOT 박제 (immutable 영역)
- Owner-facing summary 보고
- External submission (paper, PR, deployment)

### §1.2 Self-Grill 5 base dimensions (general decisions)

모든 결정 / claim 에 대해:

1. **사실 (Facts)** — claim 의 사실 근거가 무엇인가? Verifiable / cited / self-derived 분류. Hallucination 가능 영역 명시.
2. **사이드이펙트 (Side effects)** — 변경의 영향 범위. Upstream / downstream 양쪽. Reversible 여부.
3. **환경 (Environment)** — 제약 조건 (budget / device / OS / time). Constraint 위반 가능성.
4. **리스크 (Risk)** — fail mode + likelihood + impact + mitigation.
5. **가정 (Assumption)** — implicit assumption 명시화. 미검증 가정 catch.

### §1.3 v1.3 lesson — Owner ambition fit (mandatory dimension 6 for owner-mandate-driven decisions)

추가 dimension (owner 가 explicit ambition mandate 명시 시):

6. **Owner ambition fit** — 권고안이 owner 의 명시 mandate (e.g., "역사에 이름", "압도적", "세계최고") 의 ambition 차원과 align 되는가?
   - **Mandate decay check**: Director 가 honest reporting 압박으로 ambition 을 점진적으로 후퇴시키고 있지 않은가? (e.g., NeurIPS main → workshop → TMLR → 합류 형태)
   - **Pattern-aware redesign**: ambition mandate 와 honest 평가가 충돌 시, "재설계로 ambition 살리기" 옵션 검토했는가? (e.g., "10번째 mechanism 추가" 패턴 → "paradigm-shift" 패턴)
   - **Outstanding pattern check**: owner 가 "역사적" mandate 명시 시, 권고안이 NeurIPS Outstanding Paper 단골 패턴 (clean theoretical framework / surprising empirical finding / theory-empirics bridge / cross-field pollination / sharp answer to open question) 중 하나 이상에 부합하는가?

### §1.4 v1.4 lesson — Paper review 7 dimensions (mandatory for manuscript review)

Paper review (manuscript v1, 4-Opus blind, pre-submission scan) 시 §1.2 의 5 dimension + 다음 7 dimension 의무:

7. **Mathematical Forensic Audit** — theorem proof reverse-engineering / inequality direction / variance substitution validity / convexity assumption / Hessian decomposition / quotient rule fixed-point cancellation / Lagrangian dual update direction / asymptotic vs finite-horizon
8. **Cross-section Consistency Audit** — 같은 condition 의 numbers 가 모든 table/figure/text 에서 일치 / metric definition vs reported scale / compute parity / algorithm description prose vs pseudocode 일관성
9. **Reference Integrity Audit** — 모든 cross-ref 실제 위치 존재 / appendix numbering scheme 통일 / forward reference inline definition
10. **Notation/Symbol Audit** — symbol overload / Lagrangian sign convention / unit consistency / coefficient typo
11. **Empirical Evaluation Audit** — comparable scales / welfare scale change explicit note / Gini full-population vs honest-only / standard deviation reporting / asymptotic prediction vs finite N
12. **Algorithmic Audit** — optimization method consistency / pseudocode subroutine definition / computational complexity / method nomenclature consistency
13. **Reproducibility Audit** — hyperparameter table / seed disclosure / code/data availability / compute disclosure

상세 protocol: `D:/00.test/PAPER/INDEPENDENT_PAPER_REVIEW_PROTOCOL.md`

### §1.5 Output format

Self-grill 결과는 owner-facing message 의 첫 부분에 surface:

```
**Self-grill 결과** (5 dimension + applicable extras 검증):
- 사실: [claim 의 verifiable basis]
- 사이드이펙트: [범위 + reversibility]
- 환경: [제약 조건 + violation risk]
- 리스크: [fail mode + likelihood + impact + mitigation]
- 가정: [explicit + implicit assumption]
- (if applicable) Owner ambition fit: [mandate alignment]
- (if applicable) Paper review 7 dim: [§3.1-§3.7 of INDEPENDENT_PAPER_REVIEW_PROTOCOL]
```

만약 self-grill 에서 BLOCKER 발견 → claim 전에 fix 필수. **No "READY" without clean self-grill.**

---

## §2 Layer 2 — Owner-Toast (irreversible action)

### §2.1 Trigger
다음 action 전 의무:
- 외부 communication (email, social media, GitHub, paper submission)
- 자본 위험 동반 action
- Permanent record (arXiv, GitHub commit to public, public dashboard)
- HIGH-stake reversibility-low decision (e.g., venue 변경, scope abort)
- Owner 의 자율 위임 명시 후라도 LARGE-stake 시 light toast

### §2.2 Output format

```
**Toast (Layer 2)**: [action 요약]
- Stake: LOW / MEDIUM / HIGH
- Reversibility: HIGH (즉시 회수 가능) / MEDIUM (review window 내 회수) / LOW (영구 record, public 노출)
- Self-grill v1.3 ambition fit: [mandate alignment status]
- Owner action 필요: [explicit owner confirm / 자율 진행 OK]
```

만약 owner 가 사전 자율 위임 ("알아서 진행", "자율 판단해", "전부진행") 했더라도 LARGE-stake 시 explicit toast 한 번 더. owner 가 1초 confirm 으로 진행, 또는 redirect.

### §2.3 Reverse-toast cycle (3-tier safety check)

특히 LARGE-stake 시:
1. **1차 toast**: 표면적 risk surface ("X 안 가려도 돼?")
2. **Owner reaction**: implicit 우려 가능 ("Y 가 진짜 우려") → 진짜 의도 catch
3. **2차 toast**: re-frame ("진짜 우려가 Y 라면 Z 가 더 중요한 risk")
4. **3차 reframe**: final decision ("Y 우려 catch 하려면 conservative 옵션 채택")
5. **Owner final confirm**: "그렇지" 등 simple confirm

이 cycle 은 single toast 로는 catch 못하는 implicit owner 의도 발견.

### §2.4 v1.1 lesson — Default-conservative for permanent records

Permanent record (arXiv, public GitHub, public dashboard, 학회 submission) 의 reversibility 가 표면적으로는 immediate (delete 가능) 이지만 실제로는 search engine indexed (Google Scholar / Semantic Scholar / arXiv permanent record).

**Rule**: Permanent record 시 default-conservative.
- 단독저자 + niche 분야 + review 진행 중 = unconscious bias 위험 (Tomkins et al 2017 PNAS 114(48):12708-12713: famous author 1.76× / top institution 1.67× odds ratio = ~25-35% absolute lift)
- 따라서 review 진행 중 arXiv preprint 노출은 default-conservative (defer)
- Owner override 시 "시간 cost (4-7개월 지연) vs review fairness 가치" 명시 비교

**Canonical example**: 2026-05-04 EthicaAI + WhyLab arXiv defer case (3 reverse-toasts cycle, owner final confirm "올리지 않는게 낫다는 거지?").

---

## §3 Layer 3 — Cross-Agent Devil's Advocate

### §3.1 Trigger
다음 decision 시 의무:
- Long-horizon strategic decision (12-month+ commitment 변경)
- α / β / γ paper concept lock 또는 abort
- Major scope pivot (e.g., venue 변경, theme 전환)
- 외부 collaboration outreach (academic / commercial)
- Architecture decision (시스템 layer 단위 변경)

### §3.2 Cold parallel agent dispatch

**Method**: 5 cold-context general-purpose agents 동시 dispatch (no shared session memory)

**Agent prompt 의무 요소**:
- "You are a cold-context reviewer. NO knowledge of any prior session."
- 결정 context 자세히 박제 (self-contained)
- "Be cold. Be skeptical."
- Honest gap analysis 의무
- Critical fact-check obligation (모든 cited venue / paper / theorem / dataset 의 verifiable URL/DOI/arXiv ID)

**Background mode 권장** (rate limit 회피, 5 agents 동시 launch 시):
```
run_in_background: true
```

### §3.3 Synthesis (Director 책임)

5 agent return 후:
1. 5 reports 모두 read
2. Combined verdict 도출 (모두 GREEN / 일부 YELLOW / 누구라도 RED 시 escalate)
3. Pattern recognition (모두 같은 issue catch → high confidence; 다양한 issue → broad coverage)
4. Owner-facing combined report (3-tier: GREEN lock / YELLOW pivot / RED abort)

### §3.4 v1.2 lesson — Self-grill must verify factual claims (not just internal consistency)

**Triggered by**: 2026-05-04 α paper Phase 0 박제 self-grill round 1 결과. Director 가 "NeurIPS 2026 Cooperative AI Workshop" 을 3 SSOT 위치에서 사실처럼 박제했지만, cold-grill agent 가 Web 검증 (cooperativeai.com/workshop/neurips-2021 마지막 확인, 2024 는 Concordia Contest, NeurIPS 2026 workshop list 미확정) 으로 unverified 임을 발견. Internal consistency 검증만으로는 잡히지 않는 종류의 오류.

**New rule**: Self-grill (Layer 1) 가 다음 dimension 도 의무 검증:
- **Factual existence**: 인용한 venue / paper / theorem / dataset / institution 이 실제 존재하는지 (Web search 1회 spot-check)
- **Number provenance**: 인용한 통계 (e.g., "25-35% bias", "5-10% short-list probability") 가 source 에서 직접 보고된 것인지, agent 의 변환/추정인지 명시
- **Schedule feasibility**: 제안한 timeline 이 owner concurrent load 와 양립 가능한지 (multi-project workload 고려)
- **Measurable vs unmeasurable gate**: "measurable gate" 라 라벨한 것이 실제 사전 측정 가능한지, 아니면 outcome metric (post-event only) 인지 분리

**Failure mode prevented**: agent 가 plausible-sounding 하지만 unverified factual claim 을 SSOT 에 박제 → 향후 Phase 4 같은 작업이 fictional foundation 위에 쌓임.

**Canonical example added to §7**: 2026-05-04 α paper 박제 self-grill 의 BLOCKER 1 (workshop existence) + BLOCKER 3 (G4 unmeasurable disguise).

---

## §4 Layer interaction

| 시점 | Layer 적용 |
|------|-----------|
| 모든 claim/decision | Layer 1 Self-Grill (mandatory) |
| Irreversible action / external comm | Layer 1 + Layer 2 Toast |
| Long-horizon strategic / major pivot | Layer 1 + Layer 2 + Layer 3 Devil's Advocate |
| Paper review (manuscript v1/G2/pre-submit) | Layer 1 (5 base + 7 paper-review dim) + Layer 2 + (G2 시) Layer 3 |
| Owner direct order ("진행해" 등) | Self-grill 반드시 통과 후 진행. Toast 는 LARGE-stake 시. |
| Owner override ("grill 끄고 진행") | Layer 1 disable. Audit log entry. Override > 5 in day → re-discuss. |

### Self-grill 우선순위 (multiple dimension 충돌 시)
- 사실 > 사이드이펙트 > 리스크 > 가정 > 환경 > Owner ambition fit > Paper review 7 dim
- 이는 priority 의미 (모두 satisfied 해야 PASS)

---

## §5 Documentation expectations

GTP audit 결과는 다음 위치에 박제:
- Owner-facing message: self-grill 결과 surface
- SSOT change: Charter ledger entry (해당 phase 의 Director ledger)
- Repeat lesson: 본 GTP file §8 version history 추가
- Canonical example: 본 GTP file §7 추가

---

## §6 Application matrix

| Decision class | Layer 1 dim 적용 | Layer 2 | Layer 3 |
|----------------|-----------------|---------|---------|
| 일반 코드 수정 (low risk) | 5 base | optional | no |
| External communication (email, PR) | 5 base | mandatory | no |
| Paper claim 박제 (manuscript) | 5 base + 7 paper review dim | mandatory | optional |
| Phase boundary transition | 5 base + ambition fit | mandatory | mandatory |
| α/β paper concept lock/abort | 5 base + ambition fit | mandatory | mandatory (5 cold agents) |
| Public-record action (arXiv, social media) | 5 base | mandatory + reverse-toast | optional |
| Owner mandate 충돌 가능 권고 | 5 base + ambition fit | mandatory | optional |

---

## §7 Canonical examples

### §7.1 (v1.0) 2026-05-04 paper visual-defect retrospective
- **Failure**: Director 가 LaTeX compile 통과 + syntax OK 만으로 "submission READY" 박제
- **Owner question**: "논문 내 도표들도 시각적으로 확인했어?"
- **Discovery**: 7 P0/P1 visual defects (figure label "Indi"/spider chart "Fig 22" mismatch/path truncation/empty appendix section/TikZ z-order/colorbar range)
- **Cost**: Re-upload 필요, owner trust impact
- **Lesson**: Self-consistent claim ≠ defect-free. Visual / forensic audit 별도 필수.

### §7.2 (v1.1) 2026-05-04 arXiv defer case
- **Initial draft**: arXiv 즉시 업로드 권고 ("submission complete = arXiv OK")
- **1차 toast**: "GitHub URL 안 가려도 돼?" → owner: "노출하면 안되는거 아니냐고"
- **Discovery**: Yesol-Pilot/EthicaAI = PRIVATE repo (anonymous review 영향)
- **2차 toast**: "이름 안 가려도 돼?" → owner: "내가 프라이버시를 계속 물어보는 이유는 오픈리뷰에 영향이 갈까봐야"
- **Discovery**: Real concern = OpenReview unconscious bias (단독저자 + 한국 + niche → reviewer Google search → 100% identification)
- **3차 reframe**: arXiv = permanent record, indexed by Google Scholar / Semantic Scholar / arXiv. Tomkins et al 2017 (PNAS 114(48):12708-12713): single-blind 시 famous author 1.76× / top institution 1.67× odds ratio = ~25-35% absolute lift.
- **Final**: arXiv 업로드 보류 (review decision 후 4-7개월 지연 OK, ZIPs 보존). Owner confirm: "올리지 않는게 낫다는 거지?"
- **Lesson**: Permanent record default-conservative. 3-tier reverse-toast cycle 가 implicit owner 우려 catch.

### §7.3 (v1.2) 2026-05-04 α paper Phase 0 박제 self-grill BLOCKER
- **Initial draft**: α paper 박제 (3 SSOT 박제) + workshop precursor "NeurIPS 2026 Cooperative AI Workshop" 사실처럼 명시
- **Self-grill round 1 (cold-grill agent)**: 3 BLOCKER + 3 WARN 발견
  - BLOCKER 1: NeurIPS 2026 Cooperative AI Workshop existence unverified (last confirmed 2021, 2024 was Concordia Contest)
  - BLOCKER 2: 4-month Phase 0~3 timeline incompatible with owner concurrent 11-SBU/RAG/Sora load
  - BLOCKER 3: "G4 5-10% Outstanding Paper" disguised as measurable gate (실제로는 committee post-event judgment, unmeasurable)
  - WARN 1: Tomkins citation imprecise (raw odds ratio vs absolute lift conversion)
  - WARN 2: TMLR timeline imprecise (review round vs full decision)
  - WARN 3: Roadmap §6 May section stale (already SUBMITTED reflect 안 함)
- **Fix applied**: Workshop PROVISIONAL + slack gate + scope reduce 100→30-50 papers + G1/G2/G3/Stretch 3-tier separation + Tomkins precision + TMLR timeline correction + Roadmap update
- **Lesson**: Self-grill must verify factual claims (existence) + number provenance + schedule feasibility + measurable vs unmeasurable disguise.

### §7.4 (v1.3) 2026-05-04 α paper Phase 0 closure 후 보수적 trap
- **Initial Director recommendation**: α-omega 보수적 B+D+A hybrid (CoopEval 합류 + β path D + TMLR fallback)
- **Self-grill 5-dimension PASS**: 사실 / 사이드이펙트 / 환경 / 리스크 / 가정 모두 honest 평가에 충실
- **Owner reject**: "나는 압도적인 결과물을 원해 참신하고 개성있고 뛰어나고 역사에 이름이 남을"
- **Discovery**: Director 의 "honest = conservative trap" — Self-grill 의 5 dimension 이 모두 "안전 측면", "ambition fit" 차원 부재. 보수적 권고로 후퇴.
- **Owner 자율 위임 2차**: "알아서 책임지고 진행해"
- **Director α-omega ambition redesign**: Hard Separation Theorem (Pillar A) + Universal Phase Diagram (Pillar B) + Theory-Empirics Cross-Validation (Pillar C). 12-month → 24-month, NeurIPS 2027 → 2028 main + Outstanding shortlist 노림.
- **Lesson**: Self-grill 의 6번째 dimension (Owner ambition fit) 추가. Mandate decay check + Pattern-aware redesign + Outstanding pattern check.

### §7.5 (v1.4) 2026-05-06 NeurIPS 2026 PAT feedback on EthicaAI TPSD
- **Trigger**: Owner 가 NeurIPS 2026 의 Google Paper Assistant Tool (PAT) feedback (~80 specific issues, 4-section structured) 수신 후 "피드백 방식을 내재화" 명령
- **PAT catch 한 우리 GTP 의 weak spot 5 대표**:
  1. Theorem 5 의 PoA divergence claim 이 fixed-horizon T 에서 O(1) constant (collapsed trajectory 가 pre-collapse rewards 유지 → welfare $\Theta(T)$ scaling)
  2. Lemma 2 의 Azuma-Hoeffding 에서 $c^2 \to \sigma^2$ substitution invalid (Bernstein 별도 필요)
  3. Proposition 4 의 stability proof 에서 first-derivative cross-terms 가 fixed point 에서 cancel → "curvature from cost-survival tradeoff" claim 무효
  4. Tables 2/38/39 의 같은 condition (PGG MACCL Byz=30%) 가 85.5% vs 100% 모순 (cross-table grep 자동화 부재)
  5. MACCL optimization 이 "PPO" (Section 5.1) vs "finite-difference" (Appendix B.5/Z/32.1) 모순
- **New rule**: Paper review 시 Self-grill (Layer 1) 의 5 base dimension + 다음 7 dimension 의무:
  - §3.1 Mathematical Forensic Audit
  - §3.2 Cross-section Consistency Audit
  - §3.3 Reference Integrity Audit
  - §3.4 Notation/Symbol Audit
  - §3.5 Empirical Evaluation Audit
  - §3.6 Algorithmic Audit
  - §3.7 Reproducibility Audit
- **Detail protocol SSOT**: `D:/00.test/PAPER/INDEPENDENT_PAPER_REVIEW_PROTOCOL.md`
- **Lesson**: Paper review 의 mathematical rigor 가 우리 GTP base 5 dim 의 weak spot. PAT-class reviewer 가 fundamental math error catch 가능. Manuscript v1 G1 통과 전 self-correction 의무.
- **Scope clarification**: 7 paper-review dim 은 paper review 전용. General decision review 는 5 base + ambition fit 만 적용.
- **Validity audit outcome (2026-05-06)**: Cold-context independent audit of all 10 PAT claims → **8/10 fully VALID + 2/10 partially VALID + 0/10 invalid hallucination**. PAT substance accuracy ~80%, citation accuracy ~60% (specific table/line numbers sometimes mis-cited, underlying defects real). Actual fix outcome within 35h revision window: 9 patches applied (P0 6 text-only + P1 3 proof rewrite + new appendix paragraph), pdflatex 3-pass clean compile (57 pages, 2.13MB), all 7 broken "Appendix 6" cross-refs resolved, 0 BibTeX warnings. **Confirms 7 forensic audit dimensions necessity** — every dimension caught ≥1 valid issue that base 5 dim + ambition fit alone would miss. Strengthened lesson: **PAT-class audit must run before any manuscript v1 G1 sign-off**, not just at G2 4-Opus blind stage.

---

## §8 Version history

- **v1.0** (2026-05-04 KST 박제, motivating example: 2026-05-04 paper submission visual defect): 3 layers (Self-Grill / Owner-Toast / Cross-Agent Devil's Advocate) + 5 base dimensions + Trigger 정의 + §9 Owner override + §10 Director 박제. Master SSOT canonical, project adapter (PAPER/CLAUDE.md), global skill (~/.claude/skills/grill-toast-protocol/SKILL.md).
- **v1.1** (2026-05-04 ~22:30 KST, arXiv defer case): Default-conservative for permanent records + 3-tier reverse-toast cycle + Tomkins et al 2017 PNAS reference (~25-35% absolute lift conversion).
- **v1.2** (2026-05-04 ~23:00 KST, α paper 박제 BLOCKER): Self-grill must verify factual existence + number provenance + schedule feasibility + measurable vs unmeasurable disguise.
- **v1.3** (2026-05-04 ~25:00 KST, α paper Phase 0 closure 보수적 trap): Self-grill 6th dimension "Owner ambition fit" + Mandate decay check + Pattern-aware redesign + Outstanding pattern check.
- **v1.4** (2026-05-06 KST, NeurIPS 2026 PAT feedback internalization): Paper review 시 7 dimension forensic audit (Mathematical / Cross-section / Reference / Notation / Empirical / Algorithmic / Reproducibility). Detail: `D:/00.test/PAPER/INDEPENDENT_PAPER_REVIEW_PROTOCOL.md`.
- **v2.0 re-canonicalization** (2026-05-06 KST): v1.0~v1.4 박제 disk loss 후 재박제. Honest disclaimer: 일부 wording 정확 복원 어려움. **즉시 git commit 의무** (untracked 재발 방지).

---

## §9 Owner override

Owner can disable any layer for specific session by saying:
- `grill 끄고 진행` → disable Layer 1 for this session
- `toast 없이 진행` → disable Layer 2 for this command
- `devil's advocate 생략` → disable Layer 3 for this decision

All overrides logged in audit log entry. Override > 5 times in a day prompts agent to re-discuss whether GTP threshold is correctly tuned.

---

## §10 Director 박제

본 contract 는 owner 의 "내 명령이나 너의 답변을 객관적이고 독립적으로 그릴링, 토스팅 해주는 프로세스가 필요" (2026-05-04 KST) 명령에 대한 직접적 응답.

**v2.0 re-canonicalization 의 lesson**:
- v1.0~v1.4 박제가 untracked file 상태 → disk loss 시 git 으로 복구 불가
- 본 v2.0 즉시 git add + commit 으로 untracked 재발 차단
- 향후 GTP version 추가 시 ledger entry + git commit 한 cycle 로 묶기

**v1.4 lesson 의 가치**: NeurIPS 2026 PAT feedback 가 우리 GTP base 5 dim 으로는 catch 못한 ~80 issues 발견. 이는 GTP 가 "general decision review" 에는 충분하지만 "paper-class technical review" 에는 부족함을 입증. INDEPENDENT_PAPER_REVIEW_PROTOCOL.md 가 paper-review 전용 7 dim cover.

**다음 세션 적용**: 모든 Neo Genesis 에이전트가 본 GTP v2.0 자동 적용. owner 가 효과 평가 후 v2.x 또는 v3.0 fine-tune 가능.
