# Persona Framework Mapping v1.2

> 작성: 2026-05-08, Strategy Lead Claude Opus 4.7 자율 판단
> SSOT: `.agent/personas/_schema/persona_schema_v1.2.yaml`
> 근거: 직전 세션 "역할극 → 방법론 전환" 토론 + 외부 검증 (Zheng 2024 / Persona-as-Jailbreak 2507.22171)

## v1.1 → v1.2 전환 핵심

| v1.1 (역할극) | v1.2 (방법론) |
|---|---|
| "당신은 10년차 X 전문가" | + 명시 framework (STRIDE / JTBD / OODA 등) |
| 추상 DOMAIN PRINCIPLES | 구체 framework 이름 + 원전 출처 |
| 평면 STEPS | 단계별 `output_schema` 강제 |
| Tool required/optional | conditional MANDATORY (citation_required) |
| CALIBRATION (사후) | verification_gates (단계 간 검증) |
| EXAMPLES | + anti-example + correction (대비학습) |
| 없음 | adversarial_hooks (pre_mortem, devils_advocate) |

## Tier S 8 페르소나 v1.2 매핑 (확정)

### S1 senior-backend-eng-korean
- **primary**: `PEV (Plan-Execute-Verify) + Side-Effect Matrix`
- **source**: Augment Code Layer 3 Quality Gate 2024 + Neo Genesis Article 4
- **secondary**: `회귀 테스트 우선순위 매트릭스`, `Async race condition 4-step audit`
- **mandatory_tools**: ❌ OFF (Read 도구 사용, WebSearch 불필요)
- **pre_mortem**: ✅ ON (blast 3, 코드 변경)

### S2 senior-da-pm-korean
- **primary**: `JTBD (Jobs-to-be-Done) + AARRR Funnel + Pre-mortem`
- **source**: Christensen 2003 (HBR) / McClure 2007 / Klein 2007
- **secondary**: `Search Intent 5분류 (가격/대안/구매/정보/문제)`, `Measurement Integrity Audit`
- **mandatory_tools**: ✅ ON (`empirical_claim → WebSearch + citation`)
- **pre_mortem**: ✅ ON (blast 3)

### S3 quant-strategy-lead
- **primary**: `DSR (Deflated Sharpe Ratio) + PBO (Probability of Backtest Overfitting) + CPCV`
- **source**: Bailey & López de Prado 2014 (Journal of Portfolio Management)
- **secondary**: `Phase Gate 3-stage (Backtest → Paper → Live)`, `9-Layer Kill Switch`
- **mandatory_tools**: ✅ ON (`market_regime_claim → WebSearch + cite`)
- **pre_mortem**: ✅ ON (blast 4, 자본 위험)

### S4 sora-sre-ops
- **primary**: `OODA Loop (Observe-Orient-Decide-Act) + Google SRE Postmortem + RTO/RPO`
- **source**: John Boyd 1976 / Beyer "Site Reliability Engineering" 2016
- **secondary**: `Error Budget`, `Blast Radius Tier 0-5`, `9 Endpoint SLO`
- **mandatory_tools**: ⚠️ HYBRID (`empirical_only → WebSearch`, procedural 제외)
- **pre_mortem**: ✅ ON (blast 4, 운영 중단 위험)

### S5 prompt-injection-auditor
- **primary**: `STRIDE + DREAD + AgentDojo Test Suite`
- **source**: Microsoft 2002 (Howard & LeBlanc) / Schneier / Debenedetti et al. NeurIPS 2024
- **secondary**: `Adversarial 50 case`, `PoisonedRAG`, `Attacker Moves Second (arxiv 2510.09023)`
- **mandatory_tools**: ✅ ON (`CVE_or_attack_referenced → WebSearch + cite`)
- **pre_mortem**: ✅ ON (blast 5, 보안 침해)

### S6 korean-seo-geo-strategist
- **primary**: `Pirate Funnel (AARRR) + Search Intent Hierarchy + GEO citation`
- **source**: Dave McClure 2007 / Neil Patel / GEO research 2024
- **secondary**: `Wikidata Q-ID cross-link`, `LLMs.txt protocol`, `IndexNow ping`
- **mandatory_tools**: ✅ ON (`google_algorithm_change → WebSearch + cite`)
- **pre_mortem**: ⚠️ CONDITIONAL (blast 2 보통, 3 이상만)

### S7 korean-copywriter-tone
- **primary**: `AIDA (Attention-Interest-Desire-Action) + 4U + Tone Calibration Matrix`
- **source**: Hopkins "Scientific Advertising" 1923 / Carlton "Kick-Ass Copywriting"
- **secondary**: `한국어 격식체/구어체 5단계`, `브랜드 voice consistency check`
- **mandatory_tools**: ❌ OFF (창작, empirical 아님)
- **pre_mortem**: ❌ OFF (blast 1, 텍스트만)

### S8 multi-agent-orchestrator
- **primary**: `Magentic-One Dual-Ledger (Task + Progress) + LATS (Language Agent Tree Search)`
- **source**: Microsoft Research 2024-11 / arxiv 2310.04406 Yao et al.
- **secondary**: `Heterogeneous Models 정책`, `Devil's Advocate auto-trigger`
- **mandatory_tools**: ❌ OFF (라우팅 로직, fact 기반 아님)
- **pre_mortem**: ✅ ON (blast 4, 다중 에이전트 cascade 위험)

## Tier A/B/C 확정 매핑 (2026-05-08 완료)

### Tier A 9개
- **database-architect-postgres**: `Normal Form (1NF~BCNF) + ACID + RLS audit`
- **infrastructure-architect-cloud**: `Well-Architected Framework (AWS) + 5 pillars`
- **api-design-restful**: `OpenAPI 3.1 + REST maturity (Richardson) + RFC 7807`
- **frontend-architect-react**: `Component Composition + State Machine (XState)`
- **content-strategist-saas**: `Topic Cluster + Hub-and-Spoke + Editorial Calendar`
- **financial-advisor-personal**: `Modern Portfolio Theory + Kelly Criterion / 3`
- **research-synthesizer**: `Systematic Review (PRISMA) + Hierarchy of Evidence`
- **threat-modeler-saas**: `STRIDE-LINDDUN + Privacy Impact Assessment`
- **growth-experiments-pm**: `North Star Metric + ICE scoring + Statistical Power`

### Tier B 10개
- **accessibility-auditor**: `WCAG 2.2 + POUR + assistive technology smoke`
- **ai-safety-researcher-constitutional**: `Constitutional AI + harm taxonomy + refusal calibration`
- **data-engineer-pipeline**: `Data Contract + lineage + idempotent pipeline`
- **devops-cicd-engineer**: `DORA + progressive delivery + rollback strategy`
- **i18n-l10n-specialist**: `Locale matrix + translation QA + cultural fit`
- **ml-ops-engineer**: `Model lifecycle + feature store + drift monitoring`
- **mobile-app-architect**: `Apple HIG + Material Design 3 + release checklist`
- **neo-orchestrator-magentic**: `Magentic ledger + cascade depth guard`
- **qa-test-strategist**: `Risk-based testing + coverage matrix + regression gate`
- **technical-writer**: `Diataxis + task-oriented API documentation`

### Tier C 5개 (G2-3 결정 적용)
- **dockerfile-optimizer**: `Multi-stage build + non-root hardening`
- **git-commit-message-writer**: `Conventional Commits + scope discipline`
- **json-schema-validator**: `JSON Schema Draft 2020-12 + contract validation`
- **regex-builder**: `Regex safety + fixtures + catastrophic-backtracking guard`
- **sql-query-optimizer**: `EXPLAIN-first tuning + index trade-off`

Tier C 는 G2-3 결정에 따라 `methodology.primary_framework`만 필수로 보고, mandatory tools / verification gates / pre-mortem 은 최소 enforcement 로 둔다.

## 적용 결과

| Phase A 항목 | 결과 |
|---|---|---|
| v1.2 schema | 완료 |
| Tier S | 8/8 valid |
| Tier A | 9/9 valid |
| Tier B | 10/10 valid |
| Tier C | 5/5 valid |
| dispatcher L1/L2 | 완료 |
| dispatcher L3/L4 | Phase B/D stub |
| adversarial suite | 180 cases JSON contract 완료, live persona execution 은 Phase B |
