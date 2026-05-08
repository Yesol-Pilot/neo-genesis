# Persona Library Index v1.2

> 작성: 2026-05-08, Strategy Lead Claude Opus 4.7
> SSOT: `.agent/personas/_schema/persona_schema_v1.2.yaml`
> Schema: v1.2 (역할극 → 방법론 + verification gates + adversarial hooks)

## Catalog 32 페르소나

### Tier S — 8 핵심 페르소나 (v1.2 완성)
| ID | display | primary framework | model | blast | citation | pre_mortem |
|---|---|---|---|---|---|---|
| senior-backend-eng-korean | Senior Korean Backend Eng (10yr) | PEV + Side-Effect Matrix | sonnet | 3 | OFF | ON |
| senior-da-pm-korean | Senior Korean DA + PM (20yr) | JTBD + AARRR + Pre-mortem | sonnet | 3 | ON | ON |
| quant-strategy-lead | Quant Strategy Lead (15yr) | DSR/PBO + CPCV + Stop/Go | opus | 4 | ON | ON |
| sora-sre-ops | Sora SRE / Operations (12yr) | OODA + Google SRE Postmortem | sonnet | 4 | HYBRID | ON |
| prompt-injection-auditor | Security Auditor (8yr) | STRIDE + DREAD + AgentDojo | opus | 5 | ON | ON |
| korean-seo-geo-strategist | Korean SEO + GEO (10yr) | Pirate Funnel + GEO citation | sonnet | 2 | ON | OFF |
| korean-copywriter-tone | Korean Copywriter (10yr) | AIDA + 4U + Tone Matrix | sonnet | 1 | OFF | OFF |
| multi-agent-orchestrator | Magentic-One Lead | Magentic Dual-Ledger + LATS | opus | 4 | OFF | ON |

### Tier A — 9 specialist 페르소나 (v1.2 완성)
| ID | primary framework | status |
|---|---|---|
| database-architect-postgres | Normal Form (1NF~BCNF) + ACID + RLS audit | ✅ valid |
| infrastructure-architect-cloud | AWS Well-Architected 5 pillars | ✅ valid |
| api-design-restful | OpenAPI 3.1 + REST maturity (Richardson) | ✅ valid |
| frontend-architect-react | Component Composition + State Machine | ✅ valid |
| content-strategist-saas | Topic Cluster + Hub-and-Spoke | ✅ valid |
| financial-advisor-personal | Modern Portfolio Theory + Kelly/3 | ✅ valid |
| research-synthesizer | Systematic Review (PRISMA) | ✅ valid |
| threat-modeler-saas | STRIDE-LINDDUN + PIA | ✅ valid |
| growth-experiments-pm | North Star + ICE + Statistical Power | ✅ valid |

### Tier B — 10 generalist 페르소나 (v1.2 완성)
| ID | primary framework | status |
|---|---|---|
| accessibility-auditor | WCAG 2.2 + POUR | ✅ valid |
| ai-safety-researcher-constitutional | Constitutional AI + harm taxonomy | ✅ valid |
| data-engineer-pipeline | Data Contract + lineage + idempotency | ✅ valid |
| devops-cicd-engineer | DORA + progressive delivery + rollback | ✅ valid |
| i18n-l10n-specialist | Locale matrix + translation QA | ✅ valid |
| ml-ops-engineer | Model lifecycle + drift monitoring | ✅ valid |
| mobile-app-architect | Platform guidelines + release gates | ✅ valid |
| neo-orchestrator-magentic | Magentic ledger + cascade guard | ✅ valid |
| qa-test-strategist | Risk-based testing + coverage matrix | ✅ valid |
| technical-writer | Diataxis + API docs structure | ✅ valid |

### Tier C — 5 utility 페르소나 (v1.2 완성, minimal enforcement)
| ID | primary framework | status |
|---|---|---|
| dockerfile-optimizer | Multi-stage build + container hardening | ✅ valid |
| git-commit-message-writer | Conventional Commits | ✅ valid |
| json-schema-validator | JSON Schema Draft 2020-12 | ✅ valid |
| regex-builder | Regex safety + test cases | ✅ valid |
| sql-query-optimizer | EXPLAIN-first query tuning | ✅ valid |

## v1.2 신규 features

### 1. Methodology Embedding (역할극 → 방법론)
모든 페르소나에 **명시 framework 이름 + 출처** 의무. 기존 v1.1 의 추상 DOMAIN PRINCIPLES 를 STRIDE / JTBD / OODA 등 구체적 framework 으로 대체.

### 2. Verification Gates (PEV 단계 간 검증)
`step_1_output → schema check → step_2 진입` 강제. Augment Code Layer 3 Quality Gate 패턴.

### 3. Mandatory Tools (G2-1 결정: persona별 차등)
- 4/8 Tier S: citation_required ON (senior-da-pm / quant / auditor / SEO-GEO)
- 3/8 Tier S: OFF (backend-eng / copywriter / orchestrator)
- 1/8 Tier S: HYBRID (sora-sre-ops, empirical 만)

### 4. Adversarial Hooks (G2-2 결정: blast >= 3 자동)
- pre_mortem: blast_radius_ceiling >= 3 시 자동 ON (6개월 후 실패 5 시나리오)
- devils_advocate: high_stakes_auto 또는 always (보안/자본/오케스트레이션)

## Dispatcher v1.2 (4-tier hybrid)

```
L1 Slash:    /persona <name> | /ensemble | /critic | /devils-advocate
L2 Keyword:  regex priority desc 매칭, 3+ 도메인 시 multi-agent-orchestrator
L3 Embed:    KURE-v1 cosine (Phase B stub)
L4 Bandit:   Thompson Sampling (Phase D stub)
```

## G2 Detection (CONSTITUTION Article 0)

다음 패턴 자동 감지 → owner 직접 승인 게이트 표시:
- 자본 이동 (1000만원, 입금, capital transfer)
- production deploy / force push / git push --force
- credential 회전 / secret rotation
- DROP TABLE / TRUNCATE / rm -rf
- LIVE 모드 전환
- main 브랜치 머지

## 검증 명령
```bash
# 단일
python scripts/persona/constitutional_injector.py --validate .agent/personas/tier-s/<persona>.md

# 전체
python scripts/persona/constitutional_injector.py --validate-all

# 디스패치 테스트
python scripts/persona/dispatcher.py --query "이번 주 ToolPick 방문자 분석해줘"
python scripts/persona/dispatcher.py --slash "/persona quant-strategy-lead"
```

## 진행 상태
- ✅ Tier S 8/8 v1.2 변환 + 검증 PASS (2026-05-08)
- ✅ Tier A 9/9 v1.2 변환 + 검증 PASS (2026-05-08)
- ✅ Tier B 10/10 v1.2 변환 + 검증 PASS (2026-05-08)
- ✅ Tier C 5/5 v1.2 변환 + 검증 PASS (2026-05-08, enforcement 최소화)
- ✅ Persona adversarial suite 180 cases JSON contract PASS (2026-05-08)
- ⏳ Dispatcher Layer 3 (Embedding) — Phase B
- ⏳ Dispatcher Layer 4 (Bandit) — Phase D

## 누적 산출 (이번 세션, 2026-05-08)
| 파일 | 카테고리 |
|---|---|
| `.agent/personas/_schema/persona_schema_v1.2.yaml` | schema |
| `.agent/personas/_schema/framework_mapping_v1.2.md` | mapping |
| `.agent/personas/tier-s/*.md` (8 파일) | Tier S v1.2 |
| `.agent/personas/tier-a/*.md` (9 파일) | Tier A v1.2 |
| `.agent/personas/tier-b/*.md` (10 파일) | Tier B v1.2 |
| `.agent/personas/tier-c/*.md` (5 파일) | Tier C v1.2 |
| `.agent/personas/dispatcher/keyword_rules.yaml` | dispatcher rules |
| `.agent/policies/persona_safety.yaml` | safety policy |
| `scripts/persona/dispatcher.py` | 4-tier dispatcher |
| `scripts/persona/constitutional_injector.py` | v1.2 validator |
| `tests/sora_adversarial/persona_v1.json` | persona adversarial 180 cases |
| `.agent/personas/INDEX.md` | catalog (이 파일) |
