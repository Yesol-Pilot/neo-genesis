# Neo Genesis Ontology — RESEARCH v0.1

> **Status**: synthesis (2026-05-14)
> **Author**: Strategy Lead Claude Opus 4.7
> **Method**: 6 병렬 research agents (Sonnet, WebSearch + WebFetch) — 각각 한 영역. 본 문서는 cold synthesis.
> **Scope**: prior art / external standards / comparable systems / methodologies / store paradigm 의 정밀 조사 결과를 DESIGN_v0.1.md 갱신에 반영하기 위한 근거 자료.
> **관련 SSOT**: `DESIGN_v0.1.md` (이 문서의 상위 산출). 두 문서를 같이 읽어야 함.

---

## §1. Executive Summary — 10 critical findings

본 연구가 DESIGN_v0.1 (직전 박제) 에 미친 핵심 영향 10건. 각 finding 은 §3 ~ §8 에서 상세 근거.

| # | finding | severity | DESIGN_v0.1 영향 |
|---|---|---|---|
| F1 | **PROV-O 정합성 위반**: `prov:wasGeneratedBy` 의 range 는 `prov:Activity` 인데 v0.1 은 Revision→Agent/Service 로 매핑 — W3C spec 위반 | P0 | §3 객체 모델 — Activity 의미를 ActionRun 에 명시적 매핑 |
| F2 | **OntoClean 위험 4 클래스**: Artifact / Service / Agent / Task 가 rigidity 또는 identity criterion 부족 | P0 | §3 — Agent 에 identity criterion 명시, Artifact subtype 분리 검토 |
| F3 | **Markings vs 단일 sensitivity**: 단일 enum 은 multi-agent 환경에서 leak 위험. Palantir Mandatory Markings + Discretionary Roles 이분법 흡수 권고 | P0 | §3 Artifact — `sensitivity` → `markings[]` + `allowedAgents[]` 분리 |
| F4 | **Link Properties 부재**: 15 관계가 모두 binary, 링크 자체의 메타 (예: `deployed_by` 의 `deployedAt`/`version`) 표현 불가 | P1 | §4 — 모든 관계에 optional `linkProperties` block 허용 |
| F5 | **ActionRun = atomic transaction (Foundry 패턴)**: 현 ActionRun 은 event log 수준. `affectedObjects[]` / `status(pending/committed/failed)` / `sideEffects[]` 필요 | P1 | §3.9 ActionRun — 필드 보강 |
| F6 | **Identity stability — Opaque IRI 권고**: `neo://agent/<slug>` 는 slug 변경 시 ID 깨짐. Wikidata Q-ID 패턴 (opaque numeric + mutable label) 흡수 | P1 | §5 — `neo://A001` (opaque) + `label:` 분리 |
| F7 | **Multi-agent write conflict 해결책 부재**: 5 agents (Claude/Codex/Sora/Antigravity/Ollama) 가 동일 SSOT 동시 write. CRDT vs single-writer queue vs branching 중 single-writer queue 권고 | P0 | §10 + 신규 §15 거버넌스 — Supabase `agent_write_queue` |
| F8 | **CoALA 4-tier memory + 누락 클래스 2개**: `Skill` (procedural memory, Voyager pattern) + `Reflection` (episodic abstraction, Generative Agents pattern) 필요 | P1 | §3 — 클래스 9 → 11 확장 검토 |
| F9 | **Store paradigm — 단계별**: v0.1 DuckDB SQL upgrade → v0.4 Neo4j Community Cypher → v1.0 Neo4j + n10s RDF export. **Full Triple Store 거부** (text-to-SPARQL 3.3% 정확도) | P0 | §14 Roadmap — store/query 단계 명시 박제 |
| F10 | **Methodology — LOT primary + OntoClean validation gate + NeOn Scenario 1+4**: 산업지향 경량 LOT + Tier S 검증 도구 OntoClean 조합 | P1 | §13 Quality Gates — OntoClean metaproperty 검증 자동화 |

---

## §2. 6 영역 sub-conclusion 매트릭스

| 영역 | 핵심 conclusion 1 | 핵심 conclusion 2 | 핵심 conclusion 3 |
|---|---|---|---|
| **W3C 표준** | PROV-O 즉시 채택 (단 Activity 클래스 필수) | SHACL/SKOS/OWL/RDF-star 모두 deferred (v0.3~v0.5) | R2RML 영구 거부 (SQL 전용), RML 도 v0.3 평가 |
| **Palantir Foundry** | 우리 v0.1 의 chassis 는 옳음 (anti-pattern 7개 박제는 정합) | 빼놓은 5개 중 Action transaction / Object Set / Link Properties / Markings / Interfaces 흡수 권고 | Foundry 의 절반은 우리 규모에 over-engineering (Global Branching, CBAC, OSDK 자동 빌드, Functions, Pipeline Builder GUI 거부) |
| **KG 학술 / 비교 시스템** | Context (provenance) 차원이 가장 취약 — Wikidata qualifier+rank, Schema.org pending tier 흡수 | Cyc 의 5 실패 패턴 중 2개 (knowledge acquisition bottleneck, microtheory fragmentation) 가 우리에게 현실 위험 | Opaque IRI + label 분리, schema 진화 거버넌스 (pending → stable → deprecated, 비파괴) 필수 |
| **LLM Agent Memory + Graph RAG** | CoALA 4-tier 채택 + 누락 클래스 2개 (Skill, Reflection) 추가 | Graph RAG: nano-graphrag (v0.3) → LightRAG (v0.4) → HippoRAG (v0.5) 단계 | Multi-agent write: 단일 writer + queue (Supabase) 권고. CRDT 는 over-engineering |
| **Ontology Engineering Methodology** | LOT (2022) 주 골격 + OntoClean Tier S 검증 + NeOn Scenario 1+4 | OntoClean 위반 4 클래스 (Artifact / Service / Agent / Task) 교정 필요 | 거버넌스: SEMVER + `owl:deprecated` 영구 보존 + RFC 절차 + OOPS! Critical 0건 머지 게이트 |
| **Store / Query paradigm** | v0.1 → DuckDB SQL (마이그레이션 0, JSONL 직독) | v0.4 → Neo4j Community + Cypher (LangChain + GraphRAG + MCP 공식 통합) | v1.0 → Neo4j 유지 + n10s RDF export. Full Triple Store (Jena/Stardog) 거부 — LLM text-to-SPARQL 정확도 3.3% |

---

## §3. P0 변경 사항 (DESIGN_v0.1 즉시 patch)

### F1 — PROV-O Activity 정합성 (Critical)

**문제**:
W3C PROV-O 스펙은 명시한다:
> "wasGeneratedBy — Domain: prov:Entity, Range: prov:Activity"

직전 DESIGN_v0.1 §4 의 관계 #2 는 `prov:wasGeneratedBy` 를 `Revision → Agent/Service` 로 매핑. 이는 PROV-O 위반 — range 는 **prov:Activity** 여야 함.

**수정**:
- `ActionRun` 을 명시적으로 `prov:Activity` 로 선언 (rdf:type 박제)
- `Revision (= prov:Entity) --prov:wasGeneratedBy--> ActionRun (= prov:Activity) --prov:wasAssociatedWith--> Agent (= prov:Agent)`
- 신규 관계 추가: `prov:wasAssociatedWith` (ActionRun → Agent)
- 부수 효과: 모든 Revision 생성에 대응하는 ActionRun 박제 강제 (의도적 제약, audit trail 강화)

### F2 — OntoClean 위험 4 클래스 (Critical)

OntoClean 분석 (Methodology agent §3):

| 클래스 | Rigidity | Identity | 위험 | 권고 |
|---|---|---|---|---|
| `Artifact` | ~R (anti-rigid) | +I | rigidity 혼재 — `ImmutableArtifact(+R)` vs `MutableArtifactSlot(~R)` 분리 검토. **현재 Revision 으로 보완 중** | v0.2: 명시적 도큐먼테이션. v0.1 그대로 유지 OK (Revision 이 +R 부분 cover) |
| `Service` | ~R | +I | status 가변 → anti-rigid. ITIL CI 와 동일 논쟁 | v0.2: `ServiceDefinition(+R)` vs `ServiceInstance(~R)` 분리 |
| `Agent` | ~R | **-I** | 가장 위험. AI Agent 의 identity criterion 미정 | **v0.1 즉시**: identity criterion = `id` URI 만, model/tier/frontmatter_revision 은 속성 |
| `Task` | ~R | -I | 재실행 = 동일 task 인지 다른 task 인지 모호 | v0.2: Task = template(+R) + 재실행 = 신규 ActionRun |

**v0.1 즉시 박제**: Agent 클래스의 `id` 필드 만이 identity criterion 임을 명시 (다른 속성은 변경 가능).

### F3 — Markings + AllowedAgents (Critical)

**문제**:
직전 DESIGN_v0.1 §3.1 의 `Artifact.sensitivity: enum [public/internal/restricted/personal_forbidden]` 은 단일 enum. 에이전트가 판단을 자체 수행하므로 multi-agent leak 위험.

**수정** (Palantir Mandatory + Discretionary 이분법):
- `sensitivity: enum` 제거
- `markings: string[]` 추가 — 제한적 (AND-logic). 모든 marking 충족해야 read.
  - 예: `["confidential", "personal-forbidden"]`
- `allowedAgents: URI[]` 추가 — 허용적 (additive). 기본 차단된 객체에 특정 에이전트 허용.
  - 예: `["neo://agent/claude-opus-4-7"]`

**부수 효과**:
- `personal/` 디렉토리 자동 skip 강제 (markings 에 `personal-forbidden` 박제 + allowedAgents 빈 배열)
- multi-agent 호출 체인에서 markings 검사 hook 추가 (v0.3)

### F7 — Single Writer + Queue 패턴 (Critical)

**문제**:
5 에이전트가 `.agent/shared-brain/active-tasks.md` 등 동일 SSOT 동시 write. 현재 git commit 이 직렬화 역할이지만 동일 세션 내 concurrent write 는 last-write-wins.

**3 선택지 평가** (Memory agent §5):
- A. **CRDT** — eventual consistency 완벽, but sequence CRDT (RGA/Yjs) 구현 부담 매우 큼. 현 규모 over-engineering. **거부**.
- B. **Single Writer + Queue** — Supabase `agent_write_queue` 테이블 + Neo Genesis Daemon consumer. Git commit log = audit trail. **권고**.
- C. **Branching (Git worktree per agent)** — large schema change 에만 제한 적용.

**v0.2 박제** (Strategy Lead 자율 결정 — G1, 한 줄 reversible):
- Supabase 신규 테이블 `agent_write_queue` (id / agent_id / target_file / diff_content / priority / created_at / status)
- daemon poll interval 10초
- 에이전트는 `propose_write(target, diff)` API 만 호출
- daemon 이 순서대로 merge + git commit 수행

### F9 — Store paradigm 결정 (Critical)

직전 DESIGN_v0.1 의 §14 Roadmap 은 "v1.0 SPARQL / RDF export / OWL reasoning" 만 명시하고, 그 이전 단계의 store paradigm 을 명시 안 했음. **Store agent §5 의 단계별 권고 박제**:

| 단계 | Store | Query Language | Migration |
|---|---|---|---|
| **v0.1** | JSONL + **DuckDB** (`SELECT * FROM read_ndjson_auto('nodes.jsonl')`) | SQL | 비용 0, `pip install duckdb` |
| **v0.4** | **Neo4j Community 5.x** (Docker) + Vector Index | **Cypher** (CypherBench EX 61.58% with Claude 3.5 Sonnet) | DuckDB → Neo4j 적재 스크립트 ~100 lines |
| **v1.0** | Neo4j primary **유지** + `n10s` (Neosemantics) plugin | Cypher primary + SPARQL export only | n10s plugin 활성화. Oxigraph 가벼운 SPARQL endpoint 옵션 |

**Full Triple Store (Apache Jena / Stardog) 거부 근거**:
- SM3-Text-to-Query (NeurIPS 2024) 기준 zero-shot text-to-SPARQL **3.3%**, 5-shot **30%**
- 동일 벤치마크 text-to-Cypher zero-shot 34.45%, CypherBench (Claude 3.5) 61.58%
- LLM agent 가 SPARQL 생성 시 hallucination 위험 극심

**Blazegraph 영구 거부**: Wikidata 가 2024~2026 Blazegraph → QLever/Virtuoso 마이그레이션 중 (유지보수 종료).

---

## §4. P1 변경 사항 (DESIGN_v0.1 v0.2 patch)

### F4 — Link Properties

15 관계 중 다음에 `linkProperties` 권고:
- `deployed_to` (Service → Device): `deployedAt`, `version`, `rollbackAvailable`
- `governs` (Policy → ...): `governanceStartedAt`, `enforcement` (이미 Policy 클래스 속성이지만 link-level override 가능)
- `prov:wasGeneratedBy` (Revision → ActionRun): `confidence`, `model_temperature`

**YAML 예시**:
```yaml
# .agent/ontology/edges.jsonl 항목 예시
{
  "id": "neo://relation/deployed_to/svc-toolpick--dev-vercel",
  "type": "deployed_to",
  "from": "neo://service/toolpick",
  "to": "neo://device/vercel-edge",
  "linkProperties": {
    "deployedAt": "2026-05-12T14:30:00+09:00",
    "version": "634a90e",
    "rollbackAvailable": true
  },
  "observed_at": "2026-05-12T14:30:05+09:00"
}
```

### F5 — ActionRun atomic transaction

DESIGN_v0.1 §3.9 의 ActionRun 에 다음 필드 추가:
- `affectedObjects: URI[]` — 트랜잭션이 변경한 객체들
- `status: pending | committed | failed` (현 `result` 와 별도, transaction lifecycle)
- `sideEffects: object[]` — webhook 호출, 알림, 후속 스케줄 등

규칙:
- ontology write 시 (1) ActionRun pending 박제 → (2) 모든 관련 객체 update → (3) ActionRun committed 박제 순서 강제
- 실패 시 (3) failed 박제 — rollback 은 not always possible (file-based) but audit trail 보존

### F6 — Opaque IRI + Label 분리

**문제**:
`neo://agent/claude-opus-4-7` 는 model 변경 시 IRI 깨짐. KG agent §5 발견 2: "opaque URIs are less user-friendly but much more likely to be permanent."

**수정 권고** (v0.2 부터 신규 객체, v0.3 부터 기존 객체 migration):
- Primary ID: `neo://A001`, `neo://S042`, `neo://D003` 형태 (kind prefix + numeric, opaque)
- Human label: 별도 속성 `label: "claude-opus-4-7"` (mutable)
- alias: `aliases: ["claude-opus-4-7", "claude-code"]` (이름 변경 시 alias 추가, primary ID 유지)

**호환성**:
- v0.1 의 `neo://agent/claude-opus-4-7` 형태는 v0.5 까지 alias 로 보존
- 신규 추출 스크립트 부터 opaque ID 발급

### F8 — 누락 클래스 2개 (Skill + Reflection)

CoALA 4-tier (Memory agent §6):

| Tier | 우리 현 매핑 | 누락 클래스 |
|---|---|---|
| working | context window (transient) | - |
| episodic | `active-tasks.md`, `handoff.md` | - |
| semantic | `AGENT_SHARED_MEMORY.md`, `OWNER_PROFILE.md` | - |
| **procedural** | `~/.claude/agents/*.md` (비정형) | **`Skill` 클래스 신설** |
| episodic 파생 | 주간 리뷰 (수동) | **`Reflection` 클래스 신설** |

**Skill 클래스** (Voyager pattern):
```yaml
id: neo://skill/<slug>
kind: enum [subagent_spec / function / persona_instance / pipeline_step]
source_artifact: URI (Artifact) — 코드/스펙 본문
success_rate: float (검증 게이트 통과율)
last_used_at: ISO8601
composed_of: URI[] (Skill, 재사용 sub-skill)
```

**Reflection 클래스** (Generative Agents pattern):
```yaml
id: neo://reflection/<ulid>
trigger: enum [scheduled / importance_threshold / manual]
reflects_on: URI[] (Task | Decision | Artifact)
insight_text: string
generated_at: ISO8601
generated_by: URI (Agent)
```

**관계 추가** (15 → 17):
- `composed_of` (Skill → Skill, transitive)
- `reflects_on` (Reflection → Task/Decision/Artifact, n:m)

---

## §5. 영역별 상세 — W3C 표준

### 채택 매트릭스 (W3C agent §4)

| 표준 | v0.1 채택 | 근거 | 다음 단계 |
|---|---|---|---|
| **PROV-O** | ✅ 즉시 (Activity 필수) | F1 — 정합성 위반 수정 | v0.2: Qualified Patterns (prov:Generation 등) |
| **SKOS** | ❌ 거부 | 50~5K 노드 + enum 4개 (tier S/A/B/C) 만으론 SKOS Scheme 과잉 | v0.3: 다국어 label / 분류 체계 확장 시 |
| **OWL 2** | ❌ 거부 | OWL reasoner (ELK, HermiT) 운영 비용 + cold-start latency | v0.5: EL profile 한정 (transitive 추론) |
| **RDF-star / RDF 1.2** | ❌ 거부 | Candidate Recommendation 단계 — `rdf:reifies` toolchain 미숙성 | v0.5: 최종 Recommendation 안정화 후 |
| **SHACL** | ❌ 거부 | SPARQL endpoint 없는 v0.1 에서 ValidationReport 오버헤드 | v0.3: store 가 Neo4j 또는 Triple Store 일 때 |
| **R2RML** | ❌ **영구 거부** | Core SQL 2008 전용 — YAML/Markdown 소스와 근본 불일치 | NEVER |
| **RML** | ❌ 거부 | Unofficial Draft + YAML 미지원 | v0.3 평가 |

### PROV-O Qualified Patterns 권고 (v0.2)

W3C agent 발견 5 + 발견 2:
- `prov:Generation` reification — Revision 생성 시 timestamp / model / temperature 부착
- `prov:qualifiedDelegation` — `Claude → Codex` delegation 시 누가 언제 누구에게 위임
- `prov:wasAssociatedWith` — ActionRun → Agent 의 association role 명시

---

## §6. 영역별 상세 — Palantir Foundry

### 우리가 빼놓은 5건 (Foundry agent §3)

| # | Foundry 개념 | v0.1 채택 권고 |
|---|---|---|
| 1 | **Action Type = atomic transaction** | v0.1 즉시 (F5) — `affectedObjects[] / status / sideEffects[]` 추가 |
| 2 | **Object Set = first-class named query** | v0.1 즉시 — 5개 핵심 set 박제 (active-agents / live-sbus / fleet-online / pending-tasks / failing-audits) |
| 3 | **Link Properties** | v0.1 즉시 (F4) — optional block |
| 4 | **Mandatory Markings + Discretionary Roles** | v0.1 즉시 (F3) — markings[] + allowedAgents[] |
| 5 | **Interfaces (polymorphism)** | v0.2 — 4 공통 interface (`HasLifecycle / HasOwner / HasSensitivity / HasRevision`) |

### Foundry over-engineering 5건 (Foundry agent §4) — 명시적 거부

| # | Foundry 개념 | 거부 근거 |
|---|---|---|
| 1 | Global Branching (멀티 앱 통합 브랜치) | 11 SBU 각자 독립 Vercel — git commit + ssotRevision 으로 충분 |
| 2 | Classification-Based Access Controls (CBAC) | 정부 기밀 분류 시스템 — 우리는 markings[] 로 충분 |
| 3 | Ontology SDK 자동 빌드 (NPM/Maven/Pip 패키지 배포) | Pydantic auto-gen 스크립트로 경량 대체 (v0.3) |
| 4 | Functions (서버리스 compute layer) | Derived Property 개념만 차용, 전체 Functions 시스템 v1.0 까지 거부 |
| 5 | Pipeline Builder GUI (no-code) | extract 스크립트로 충분 |

### Foundry anti-patterns cross-check (Foundry agent §5)

8개 중 우리 박제 7개와 5개 완전 교집합 (System Silos / Department Silos / God Object / Action Sprawl / Time Machine). 미박제 1건: **Golden Hammer** (단일 도구 모든 문제에 사용) — v0.1 의 Action transaction (F5) 도입으로 해결.

### OAG (Ontology-Augmented Generation) 패턴 (Foundry agent §6)

Palantir AIP 의 governed execution:
> "LLMs do not have direct access to tools; LLMs can only ask to use tools, and these tool calls are then executed by AIP Logic within the invoking user's permissions."

**우리 적용**:
- Claude/Codex/Sora 가 ontology 직접 편집 금지
- `scripts/ontology/query.py --object-set active-agents --agent claude-code` (Data Tool 등가, markings 검사 포함)
- `scripts/ontology/mutate.py --action update-task-status --params '{...}'` (Action Tool 등가, transaction 박제)
- 위 두 스크립트를 MCP tool 로 노출 (v0.3)

---

## §7. 영역별 상세 — KG 학술 + 비교 시스템

### KG 4 차원 (Hogan 2021) 매핑 (KG agent §2)

| 차원 | 우리 v0.1 현황 | 가장 취약 |
|---|---|---|
| Data | 9 클래스 / 15 관계 / file-based SSOT | - |
| Schema | 암묵적 (yaml frontmatter) | OWL 공리 / domain-range 미선언 |
| Identity | `neo://` 스킴 정의 | **opaque IRI 부재 — F6** |
| **Context** (provenance) | 마크다운 텍스트 + ssotRevision 만 | **가장 취약 — F1 + F8** |

### Wikidata 패턴 흡수 (KG agent §3)

- **Qualifier**: 관계에 시간/출처/조건 메타 → 우리 `linkProperties` (F4) 와 정합
- **Rank** (preferred/normal/deprecated): 동일 사실 충돌 시 우선순위 → 우리 multi-agent write 시 deprecation 정책 (F7 의 보완)
- **Reference 필수 권고**: 모든 statement 에 출처 → 우리 `prov:wasDerivedFrom` 와 정합

### Schema.org 패턴 흡수 (KG agent §3)

- **Pending tier**: 신규 스키마 즉시 core 격상 안 함 — staging 검증 → 우리 v0.X 진화 거버넌스 (§15)
- **`supersededBy`**: deprecated 영구 보존, 비파괴 변경 → 우리 schema 진화 정책

### Cyc 의 5 실패 패턴 (KG agent §4) — 우리 risk

| Cyc 패턴 | 우리 risk | 회피 |
|---|---|---|
| Knowledge Acquisition Bottleneck | **High** — active-tasks 400KB+, handoff 120KB+ (수동 갱신 의존) | **archive TTL (2026-05-12 도입은 옳음)** + 자동 추출 + append-only log |
| Microtheory Fragmentation | **High** — 5 에이전트 동일 SSOT 동시 편집 | F7 — 단일 writer + queue, 또는 namespace 분리 |
| Deterministic-Only Reasoning | **Medium** — boolean status 만, confidence 부재 | ActionRun 에 `confidence: 0.0~1.0` 추가 (F5 보완) |
| Validation Isolation (외부 검증 부재) | **Medium** — Strategy Lead 단독 판단 | SSOT 변경에 `changed_by` / `reason` / `evidence_url` 의무화 |
| Commercialization-Driven Distortion | **Low** (현재) — Revenue Path Research 이미 분리 인식 | Core schema + application layer 분리 정책 |

---

## §8. 영역별 상세 — LLM Agent Memory + Graph RAG

### CoALA 4-tier 매핑 (Memory agent §6)

`.agent/` 현 구조를 4-tier 로 재분류:

| Tier | 우리 파일/클래스 | retrieval | write 규칙 |
|---|---|---|---|
| working | context window | 직접 | immediate, no persist |
| episodic | `active-tasks.md`, `handoff.md`, weekly review | recency + importance score | append-only + reflection trigger |
| semantic | `AGENT_SHARED_MEMORY.md`, `OWNER_PROFILE.md`, `NEO_MASTER_RULES.md` | KURE-v1 embedding ANN | slow-write, owner G2 권장 |
| **procedural** | `~/.claude/agents/*.md`, sora_engine functions, `scripts/persona/*` | embedding + keyword + validation gate | **validation 통과 후만 commit** (F8 의 Skill 클래스) |

### Graph RAG 단계별 권고 (Memory agent §3, §4)

| 단계 | 패턴 | 근거 |
|---|---|---|
| **v0.3** | **nano-graphrag** (~1,100 lines, async, fully typed) PoC | Microsoft GraphRAG 대비 가벼움. Sora engine 임베드 가능 |
| **v0.4** | **LightRAG** dual-level (low-level entity + high-level concept) + KURE-v1 한국어 entity | GraphRAG (community detection) 은 수백만 토큰 전제. 우리 규모엔 LightRAG fit |
| **v0.5** | **HippoRAG** Personalized PageRank subgraph retrieval | multi-hop QA (예: "A1 알파 실패 근본 원인?") 에 single retrieval step |

GraphRAG (Microsoft) 자체는 v0.4 통합 안 함 — Leiden community detection 이 우리 규모 (50K 노드) 에 과도. LightRAG 가 incremental update 도 내장.

### Multi-agent write conflict — 3 선택지 (Memory agent §5)

이미 F7 에서 박제. **단일 writer + queue 권고 확정**.

추가 디테일:
- 단기 (v0.2): 에이전트별 namespace 분리 + merger agent (`neo://namespace/claude/`, `neo://namespace/codex/` 등)
- 중기 (v0.3): event-sourcing 전환 — `neo://events/` append-only, state 는 replay

---

## §9. 영역별 상세 — Ontology Engineering Methodology

### LOT 주 채택 (Methodology agent §2)

LOT (Linked Open Terms, Poveda-Villalón et al. 2022, Engineering Applications of AI 111:104755):
- 산업 지향, 1인 팀 적합
- 4 단계: Requirements (ORSD) → Implementation sprint → Publication → Maintenance
- FAIR 원칙 native

**우리 매핑**:
- v0.1 = Requirements (이번 DESIGN + RESEARCH 가 ORSD 등가)
- v0.2 = Implementation sprint 1 (OWL Turtle 형식화 + OntoClean 교정)
- v0.3 = Publication (content negotiation URI, GitHub 공개)
- v1.0 = Maintenance cron 정례화

### OntoClean Tier S 검증 (Methodology agent §3)

v0.2 진입 전 9 클래스 metaproperty 표 작성 의무 — F2 에 박제.

### NeOn Scenario 1+4 (Methodology agent §2)

- Scenario 1 (from scratch): 신규 클래스 정의 (Artifact, Service 등)
- Scenario 4 (reuse + re-engineer): PROV-O, OpenTelemetry, SPDX 패턴 흡수

### 거버넌스 4단계 절차 (Methodology agent §6.2)

```
1. RFC (Request For Change)
   - `.agent/ontology/rfcs/RFC-NNNN.md` 박제
   - OntoClean metaproperty 영향 검토

2. OOPS! 자동 검증 (oops.linkeddata.es)
   - Critical 0건, Important <= 2건 시 merge 허용

3. Deprecation 우선
   - `owl:deprecated true` + `supersededBy` 한 MINOR 이상 유지
   - 절대 비파괴 삭제

4. Migration Script 의무
   - MAJOR bump 시 SPARQL UPDATE + JSON-LD frame 변환 스크립트
```

### 흡수해야 할 운영 ontology 5 패턴 (Methodology agent §5)

| 패턴 | 출처 | 우리 v0.X 적용 |
|---|---|---|
| Resource-Signal 직교 분리 | OpenTelemetry | v0.2 — Service annotation 에 `service.name`, `host.id` 등 |
| 4-Level Provenance Grade | SLSA | v0.3 — Revision 에 `slsa:level (0~3)` |
| Relationship Type Vocabulary | SPDX / CycloneDX | v0.3 — Artifact 간 의존 관계 `DEPENDS_ON` / `CONTAINS` / `BUILD_TOOL_OF` 어휘 |
| Predicate-based CI | ITIL CMDB | v0.3 — 핵심 관계에 ITIL predicate label 병기 |
| Qualified Patterns | PROV-O | v0.2 (F1 의 자연스러운 다음 단계) |

---

## §10. 영역별 상세 — Store / Query Paradigm

### v0.1 — DuckDB SQL upgrade (Store agent §5)

```python
# 마이그레이션 (5 줄)
import duckdb
con = duckdb.connect('.agent/ontology/ontology.duckdb')
con.execute("CREATE TABLE nodes AS SELECT * FROM read_ndjson_auto('.agent/ontology/nodes.jsonl')")
con.execute("CREATE TABLE edges AS SELECT * FROM read_ndjson_auto('.agent/ontology/edges.jsonl')")
con.execute("SELECT * FROM nodes WHERE kind='Service' AND status='running'").fetchall()
```

**근거**:
- `pip install duckdb` 단일 의존성, Docker 불필요
- 50K 노드/100K 엣지 sub-second
- JSONL 직독 — 기존 파일 형식 유지
- SQL aggregation SQLite 대비 10~100배 빠름
- text-to-SQL LLM 정확도 47%+ (zero-shot, schema 제공 시 88.55%)
- multi-hop graph traversal 은 SQL CTE recursive query 로 표현 가능

### v0.4 — Neo4j Community + Cypher (Store agent §5)

**Docker compose**:
```yaml
neo4j:
  image: neo4j:5-community
  ports: ["7474:7474", "7687:7687"]
  environment:
    - NEO4J_AUTH=neo4j/<password>
    - NEO4JLABS_PLUGINS=["apoc", "n10s"]
  volumes:
    - ./neo4j_data:/data
```

**근거**:
- LangChain / LangGraph 공식 통합 (`GraphCypherQAChain`, `Neo4jVector`, `Neo4jSaver`)
- 공식 MCP 서버 (`mcp-neo4j-memory`, `mcp-neo4j-cypher`) — Claude Code 직결
- CypherBench (Edge et al. 2024) — Claude 3.5 Sonnet EX **61.58%**, PSJS 80.85%
- ISO/IEC 39075:2024 GQL 표준 발행 (2024-04-12) — vendor lock-in 위험 대폭 감소
- Community Edition 단일 노드 — 1인 회사 / 5K~100K 노드 규모에 충분

### v1.0 — n10s RDF export, NOT full Triple Store (Store agent §5)

- Neo4j primary 유지
- `n10s` (Neosemantics) plugin 으로 RDF 1.1 / OWL / SKOS export
- Oxigraph (MIT, Rust, `pip install pyoxigraph`) 가벼운 SPARQL read endpoint 옵션
- Apache Jena / Stardog 완전 이전 거부

### text-to-Query LLM 정확도 (Store agent §4)

| 언어 | zero-shot | 5-shot ICL | 최신 모델 |
|---|---|---|---|
| SQL | 47.05% | ~50% | (Schema+ICL 88.55%) |
| Cypher | 34.45% | ~45% | **CypherBench Claude 3.5 Sonnet 61.58%** |
| SPARQL | **3.3%** | ~30% | (벤치마크 부족) |
| MQL (MongoDB) | 21.55% | - | - |

**결론**: SPARQL = LLM agent 실 사용 불가능 수준. Cypher 가 압도적 fit.

---

## §11. 누적 인용 (90+, 영역별 정리)

### W3C 표준 (14건)
1. [PROV-O W3C Rec (2013)](https://www.w3.org/TR/prov-o/)
2. [PROV-O actedOnBehalfOf](https://www.w3.org/TR/prov-o/#actedOnBehalfOf)
3. [SKOS Reference W3C Rec (2009)](https://www.w3.org/TR/skos-reference/)
4. [OWL 2 Overview (2012)](https://www.w3.org/TR/owl2-overview/)
5. [OWL 2 Profiles](https://www.w3.org/TR/owl2-profiles/)
6. [RDF 1.2 Concepts CR](https://www.w3.org/TR/rdf12-concepts/)
7. [RDF 1.2 Primer](https://www.w3.org/TR/rdf12-primer/)
8. [SHACL W3C Rec (2017)](https://www.w3.org/TR/shacl/)
9. [R2RML W3C Rec (2012)](https://www.w3.org/TR/r2rml/)
10. [RML Spec Unofficial Draft](https://rml.io/specs/rml/)
11. Ke et al. (VLDB 2024). "Efficient Validation of SHACL Shapes with Reasoning"
12. K-CAP 2025. "Lessons Learned from the Combined Development of OWL and SHACL"
13. Herron et al. (SAGE 2025). "Logic and Reasoning in Neurosymbolic Systems Using OWL-Based KG"
14. arXiv 2604.00555. "Ontology-Constrained Neural Reasoning"

### Palantir Foundry (18건)
1. [Foundry Ontology Overview](https://www.palantir.com/docs/foundry/ontology/overview)
2. [Best Practices and Anti-Patterns](https://www.palantir.com/docs/foundry/ontology/ontology-best-practices-and-anti-patterns)
3. [Object Types Overview](https://www.palantir.com/docs/foundry/object-link-types/object-types-overview)
4. [Link Types Overview](https://www.palantir.com/docs/foundry/object-link-types/link-types-overview)
5. [Action Types Overview](https://www.palantir.com/docs/foundry/action-types/overview)
6. [Action Types Write-back](https://www.palantir.com/docs/foundry/action-types/overview)
7. [Foundry Core Concepts](https://www.palantir.com/docs/foundry/ontology/core-concepts) (Interfaces)
8. [Foundry Functions Overview](https://www.palantir.com/docs/foundry/functions/overview)
9. [Ontology SDK Overview](https://www.palantir.com/docs/foundry/ontology-sdk/overview)
10. [Markings](https://www.palantir.com/docs/foundry/security/markings)
11. [Foundry Branching](https://www.palantir.com/docs/foundry/foundry-branching/overview)
12. [Object Set Service](https://www.palantir.com/docs/foundry/ontologies/query-compute-usage)
13. [AIP Logic Blocks](https://www.palantir.com/docs/foundry/logic/blocks)
14. [AIP Logic Overview](https://www.palantir.com/docs/foundry/logic/overview)
15. [Pipeline Builder Ontology Output](https://www.palantir.com/docs/foundry/pipeline-builder/outputs-add-ontology-output)
16. [Palantir Blog: RAG/OAG with AIP Logic](https://blog.palantir.com/building-with-palantir-aip-logic-tools-for-rag-oag-fdaf8938d02e)
17. [Properties Overview](https://www.palantir.com/docs/foundry/object-link-types/properties-overview)
18. [Foundry Ontology System (Architecture Center)](https://palantirfoundation.org/docs/foundry/architecture-center/ontology-system)

### KG 학술 + 비교 시스템 (17건)
1. Hogan et al. (2021). KG ACM Comput Surv. DOI: [10.1145/3447772](https://dl.acm.org/doi/10.1145/3447772). arXiv:2003.02320
2. Paulheim (2017). KG refinement. [10.3233/SW-160218](https://journals.sagepub.com/doi/full/10.3233/SW-160218)
3. Ji et al. (2022). KG Survey IEEE TNNLS. [10.1109/TNNLS.2021.3070843](https://ieeexplore.ieee.org/document/9416312/)
4. [Wikidata Statistics](https://www.wikidata.org/wiki/Wikidata:Statistics)
5. [Wikidata Data Model](https://www.wikidata.org/wiki/Wikidata:Data_model)
6. [Wikidata Qualifiers](https://www.wikidata.org/wiki/Help:Qualifiers)
7. [Wikidata Ranks](https://www.wikidata.org/wiki/Help:Ranks)
8. [DBpedia Semantic Web Journal (2014)](https://www.semantic-web-journal.net/system/files/swj499.pdf)
9. [Schema.org How We Work](https://schema.org/docs/howwework.html)
10. [YAGO Suchanek et al. (WWW 2007)](https://suchanek.name/work/publications/www2007.pdf)
11. ConceptNet 5.5 (AAAI 2017). arXiv:1612.03975
12. Lenat & Guha (1990). Building Large KBS. Cyc 초기 설계.
13. [Bergman (2017): Fare Thee Well OpenCyc](https://www.mkbergman.com/2034/fare-thee-well-opencyc/)
14. [Fisher (2024): Cyc's Forgotten AI](https://outsiderart.substack.com/p/cyc-historys-forgotten-ai-project)
15. Shapiro et al. (2011). CRDT. INRIA [inria-00609399](https://inria.hal.science/inria-00609399v1/document)
16. Garijo et al. (2020). FAIR Vocabularies. arXiv:2003.13084
17. [Graphiti getzep/graphiti](https://github.com/getzep/graphiti) — bi-temporal KG

### LLM Agent Memory + Graph RAG (18건)
1. Packer et al. (2023). MemGPT. arXiv:2310.08560
2. Sumers et al. (2023). CoALA. arXiv:2309.02427
3. Park et al. (2023). Generative Agents. arXiv:2304.03442 (UIST'23)
4. Wang et al. (2023). Voyager. arXiv:2305.16291
5. Xu et al. (2025). A-MEM. arXiv:2502.12110 (NeurIPS 2025)
6. Mem0 (2025). arXiv:2504.19413
7. [Mem0: State of AI Agent Memory 2026](https://mem0.ai/blog/state-of-ai-agent-memory-2026)
8. Edge et al. (2024). GraphRAG. arXiv:2404.16130
9. [Microsoft GraphRAG GitHub](https://github.com/microsoft/graphrag)
10. Guo et al. (2024). LightRAG. arXiv:2410.05779
11. [nano-graphrag](https://github.com/gusye1234/nano-graphrag)
12. Jimenez Gutierrez et al. (2024). HippoRAG. arXiv:2405.14831 (NeurIPS'24)
13. Shu et al. (2024). Think-on-Graph 2.0. arXiv:2407.10805
14. [Letta Docs](https://www.letta.com/)
15. [Google A2A Protocol Announcement (2025)](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/)
16. [A2A Protocol Spec](https://a2a-protocol.org/latest/specification/)
17. Meng et al. (2022). ROME.
18. Meng et al. (2022). MEMIT.

### Ontology Engineering Methodology (17건)
1. [METHONTOLOGY (1997)](https://aaai.org/papers/0005-ss97-06-005-methontology-from-ontological-art-towards-ontological-engineering/)
2. NeOn Methodology (2012). Suárez-Figueroa et al. Springer.
3. Guarino & Welty (2002). OntoClean. CACM 45(2).
4. Guarino & Welty (2004). OntoClean Overview. Springer.
5. Poveda-Villalón et al. (2022). LOT. Engineering Applications of AI 111:104755.
6. Poveda-Villalón et al. (2014). [OOPS!](https://oops.linkeddata.es/) IJSWIS.
7. [PROV-O](https://www.w3.org/TR/prov-o/) (재사용)
8. [OpenTelemetry Spec](https://opentelemetry.io/docs/specs/otel/overview/)
9. [SLSA v1.0 Levels](https://slsa.dev/spec/v1.0/levels)
10. [SPDX 3.0](https://spdx.dev/)
11. [CycloneDX 1.6](https://cyclonedx.org/)
12. Ruy et al. (2016). SEON. LNCS 10024.
13. [ITIL 4 Service Configuration Management](https://wiki.en.it-processmaps.com/index.php/Service_Asset_and_Configuration_Management)
14. [Atlassian CMDB](https://www.atlassian.com/itsm/it-asset-management/cmdb)
15. [Keet OE Book](https://people.cs.uct.ac.za/~mkeet/OEbook/ontocleantutorialOE19.pdf)
16. [Enterprise Knowledge Ontology Versioning](https://enterprise-knowledge.com/top-5-tips-for-managing-and-versioning-an-ontology/)
17. [OBO Foundry Versioning Principle](http://obofoundry.org/principles/fp-004-versioning.html)

### Store / Query Paradigm (25건)
1. SM3-Text-to-Query (NeurIPS 2024). [PDF](https://proceedings.neurips.cc/paper_files/paper/2024/file/a182a8e6ebc91728b6e6b6382c9f7b1e-Paper-Datasets_and_Benchmarks_Track.pdf)
2. CypherBench. arXiv:2412.18702 (2024-12).
3. Text2GQL-Bench. arXiv:2602.11745 (2026-02).
4. Text2Cypher (ACL 2025).
5. ScienceDirect Text-to-Cypher Pipeline (2025).
6. ArangoDB vs Neo4j Benchmark Analysis. arXiv:2401.17482.
7. Fürst (TDS). "Can LLMs talk SQL, SPARQL, Cypher, MQL equally well?"
8. Instruct-to-SPARQL (ACM SIGIR 2025).
9. [GQL ISO/IEC 39075:2024](https://www.gqlstandards.org/)
10. [ISO/IEC 39075:2024](https://www.iso.org/standard/76120.html)
11. AWS Blog: GQL Standard Arrived.
12. [Neo4j Community Edition](https://neo4j.com/product/community-edition/)
13. [Neo4j MCP](https://neo4j.com/developer/genai-ecosystem/model-context-protocol-mcp/)
14. [LangChain Neo4j Integration](https://neo4j.com/labs/genai-ecosystem/langchain/)
15. [Microsoft GraphRAG Docs](https://microsoft.github.io/graphrag/)
16. [Oxigraph GitHub](https://github.com/oxigraph/oxigraph)
17. [pyoxigraph](https://pyoxigraph.readthedocs.io/)
18. [Apache Jena/Fuseki](https://jena.apache.org/documentation/fuseki2/)
19. ArangoDB 2024 Benchmark (자체).
20. Memgraph vs Neo4j Benchmark (자체).
21. [Wikidata WDQS Backend Update](https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service/WDQS_backend_update)
22. [Wikidata Graph DB Reload 2025](https://techblog.wikimedia.org/2025/04/08/wikidata-query-service-graph-database-reload-at-home-2025-edition/)
23. [Neo4j MCP GitHub](https://github.com/neo4j-contrib/mcp-neo4j)
24. [Neo4j Blog: RDF vs Property Graphs](https://neo4j.com/blog/knowledge-graph/rdf-vs-property-graphs-knowledge-graphs/)
25. [Microsoft GraphRAG Get Started](https://microsoft.github.io/graphrag/get_started/) (Parquet storage)

---

## §12. Rejected alternatives (Strategy Lead 자율 결정 박제)

| 거부 항목 | 거부 단계 | 거부 근거 (단어 한 줄) | reversible? |
|---|---|---|---|
| R2RML | 영구 | SQL 전용 — 우리 source 와 근본 불일치 | no |
| Blazegraph | 영구 | Wikidata 마이그레이션 진행 — 유지보수 종료 | no |
| Cyc-style 수작업 ontology | 영구 | 30+ 년 실패 사례 | no |
| Apache Jena / Stardog / Virtuoso (full Triple Store) | v1.0 까지 | text-to-SPARQL 3.3% LLM 정확도 | yes (LLM 정확도 향상 시) |
| OWL DL reasoning (full) | v0.5 까지 | reasoner cold-start + 운영 비용 | yes |
| RDF-star (`rdf:reifies`) | v0.5 까지 | Candidate Recommendation 미확정 | yes (final Rec 후) |
| SHACL | v0.3 까지 | SPARQL endpoint 부재 + ValidationReport 오버헤드 | yes |
| Foundry Global Branching | v1.0 까지 | 11 SBU 각자 독립 — ssotRevision 충분 | yes |
| Foundry CBAC (정부 기밀 분류) | 영구 | 우리 markings 으로 충분 | no |
| Foundry Functions (서버리스 compute) | v1.0 까지 | Derived Property 만 차용, 전체 시스템 비용 과대 | yes |
| Foundry Pipeline Builder GUI | 영구 | extract 스크립트 충분 | no |
| CRDT (Yjs / RGA sequence CRDT) | v1.0 까지 | 구현 부담 매우 큼, single-writer queue 로 충분 | yes |
| GraphRAG (Microsoft, Leiden community detection) | v0.4 | 수백만 토큰 전제 — 우리 규모 (50K) 과도. LightRAG 가 더 fit | yes (규모 확장 시) |
| TigerGraph / JanusGraph / Amazon Neptune | v1.0 까지 | 인프라 부담 (distributed) — Neo4j Community 로 충분 | yes |
| Foundational ontology (DOLCE / BFO / SUMO) align | v1.0 까지 | 1인 팀 overhead 과대. v1.0 DOLCE-Lite 선택적 평가 | yes |

---

## §13. Validation — 본 RESEARCH 가 답한 G1 결정 7건

직전 DESIGN_v0.1 Appendix A 의 G1 결정 7건이 본 RESEARCH 로 어떻게 정당화 / 갱신되는지:

| G1 | 직전 결정 | RESEARCH 검증 | 갱신? |
|---|---|---|---|
| G1-1 Memory MCP 경계 (옵션 A 파일 원본) | 권고 유지 | 정합 — multi-agent + git-trackable | 유지 |
| G1-2 SBU = Project subtype | 권고 유지 | OntoClean 정합 (Project rigid, +I, +U) | 유지 |
| G1-3 OWL reasoning v1.0 | 권고 유지 | W3C agent 발견 4: EL profile v0.5 까지 deferred | **갱신** → v0.5 EL profile |
| G1-4 Action 자동 실행 v0.4 + owner G2 | 권고 유지 | Foundry OAG: Data/Logic/Action tools 분리. v0.3 부터 governed execution scaffolding | **갱신** → v0.3 scaffolding, v0.4 owner G2 |
| G1-5 personal/ in-scope | NEVER | 정합. markings:[personal-forbidden] + allowedAgents:[] 강제 | 유지 + 메커니즘 강화 (F3) |
| G1-6 객체 9개 (SBU merged) | 권고 유지 | F8: Skill + Reflection 누락 → **11 클래스 확장 권고** | **갱신** → 9 → 11 |
| G1-7 Decision = Artifact subtype | 권고 유지 | God Object anti-pattern 회피 정합 | 유지 |

---

## §14. v0.X Roadmap 갱신 (DESIGN_v0.1 §14 → 본 RESEARCH 후 final)

| Version | 작업 | Store | Query | 외부 표준 통합 | 산출 |
|---|---|---|---|---|---|
| **v0.1** (현재) | contract + research | JSONL → **DuckDB** | SQL | PROV-O 핵심 (Activity 정합) | DESIGN + RESEARCH 박제 |
| **v0.2** | PoC extraction 50N/100E + OntoClean 교정 + Skill/Reflection 신설 | DuckDB | SQL + CTE | PROV-O Qualified Patterns | 20 competency Q PASS |
| **v0.3** | Single Writer Queue + nano-graphrag PoC + OAG 인터페이스 + SHACL/RML 평가 | DuckDB + Supabase queue | SQL | SHACL (v0.3 평가), SKOS (등록), SPDX (relationship type) | 한국어 KG triple 추출기 |
| **v0.4** | Neo4j 이전 + LightRAG dual-level + RAG 통합 + KURE-v1 결합 | **Neo4j Community** | **Cypher** | OpenTelemetry annotation, SLSA level | retrieval 정확도 +10%↑ |
| **v0.5** | HippoRAG PPR + OWL EL transitive + RDF-star (안정화 시) | Neo4j | Cypher + 한정 OWL EL | OWL EL transitive, RDF-star (cond) | multi-hop query 라이브 |
| **v1.0** | n10s RDF export + Oxigraph SPARQL endpoint + DOLCE-Lite 평가 | Neo4j + Oxigraph | Cypher primary + SPARQL export | Full PROV-O / SKOS / OWL 2 EL / SHACL / SPDX / CMDB / OpenTelemetry / SLSA | 외부 federation 1건 이상 |

---

## §15. v0.1 → v0.2 Promotion Gate (final)

owner ACK 필요 항목:
1. F1 ~ F10 P0 변경 사항 DESIGN_v0.1 patch 승인
2. §14 Roadmap (DuckDB → Neo4j → +n10s) 승인
3. §12 Rejected alternatives 박제 승인
4. 20 competency questions final 확정 (DESIGN_v0.1 §12, 이번 RESEARCH 에서 갱신 없음)

owner ACK 시 v0.2 작업 unblock:
- DuckDB 마이그레이션 스크립트 박제
- OntoClean metaproperty 표 박제
- Skill / Reflection 클래스 추가
- 5 Object Set named query 박제
- extract 스크립트 (Artifact / Service / Device / Agent) 박제
- 20 competency Q `tests/ontology/competency_q*.py` 박제 + PASS

---

## Appendix A. 변경 이력

| 일자 | 버전 | 작성자 | 변경 |
|---|---|---|---|
| 2026-05-14 | v0.1 synthesis | Strategy Lead Claude Opus 4.7 | 6 병렬 research agent 결과 종합 박제 |

---

👤 Strategy Lead Claude Opus 4.7
