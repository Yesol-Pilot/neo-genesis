# OntoClean Subtype Re-Evaluation v0.4

> **Status**: G1 박제 (2026-05-14, Strategy Lead Claude Opus 4.7)
> **Companions**: `ontoclean_metaproperties_v0.1.md` (4 위반 식별), `ontoclean_subtype_evaluation_v0.2.md` (v0.2 deferred)
> **Decision**: v0.4 시점 trigger 조건 재검토 — **4 subtype 모두 v0.2 DEFER 유지**

---

## Re-eval 동기

v0.2 박제 시점 (2026-05-14 첫 라이브) 의 trigger 조건은:

| Subtype | Trigger |
|---|---|
| Artifact split (ImmutableArtifact / MutableArtifactSlot) | competency Q sha-level vs path-level 혼동 발생 시 |
| Service split (ServiceDefinition / ServiceInstance) | Neo4j 이전 + Cypher label inheritance 활용 시 |
| Task split (TaskTemplate / TaskExecution) | 반복 시도 추적 query 필요 시 |
| Agent (이미 G1-12 해소) | n/a |

본 세션 v0.3 final + v0.4 진입 단계 (HippoRAG PPR + LightRAG + Neo4j scaffold + SBU vector + 333 nodes + ActionRun 8건 등) 이후, **각 trigger 발생 여부 검토**.

---

## Trigger 검토 (4 클래스)

### 1. Artifact split — DEFER 유지

**Trigger**: "sha-level vs path-level 혼동 발생"

**현 상태**:
- 20 competency Q PASS — sha-level (CQ-01, CQ-16) 와 path-level (CQ-04, CQ-05, CQ-17) 모두 정상 분리
- ActionRun (ontology_mutation 2건) modify_status 동작 — path-level 변경 시 Artifact id 유지, Revision 만 추가 (예상대로)
- competency_results.json 의 CQ-01 ~ CQ-20 모두 의도된 동작

**판정**: **혼동 미발생** — Revision 클래스가 sha-level cover 중. subtype 분리 불필요. **DEFER 유지**.

---

### 2. Service split — DEFER 유지

**Trigger**: "Neo4j 이전 + Cypher label inheritance 활용"

**현 상태**:
- Neo4j 는 v0.4 scaffold 박제만 — 실 가동은 owner Docker 환경 (`.agent/ontology/neo4j/` README 참조)
- `migrate_to_neo4j.py --dry-run`: 333 nodes / 161 edges / 11 클래스 import-ready
- Cypher schema (`cypher_schema.cql`) 가 단일 `Service` label + status enum 으로 충분
- ServiceInstance vs ServiceDefinition 분리 시 Cypher 의 label inheritance 사용 가능하지만 — 현 status enum 으로 query 표현 가능

**판정**: **Neo4j 실 가동 후 재평가** — scaffold 단계에선 단일 클래스 유지 적정. **DEFER 유지**.

---

### 3. Task split — DEFER 유지

**Trigger**: "반복 시도 추적 query 필요"

**현 상태**:
- 본 세션 mutate.py 의 modify_status: pending → done 1회 시행 — 재실행 패턴 미발생
- ActionRun{kind:ontology_mutation} 2건 — 추적은 ActionRun 으로 충분 (Task 자체 분해 불필요)
- HippoRAG PPR seed=Task 일 경우 ActionRun 경유 발견 가능 (그래프 traversal 통한 추적)

**판정**: **반복 시도 추적은 ActionRun + edge 로 충분** — Task = template 의도 유지. **DEFER 유지**.

---

### 4. Agent identity — v0.1 G1-12 해소됨

**Trigger**: n/a (이미 박제)

**현 검증**:
- 37 Agent 노드 (4 model_instance + 32 persona_spec + 1 strategy lead alias)
- `id` 가 유일 identity, model/tier/label 모두 속성 (validate.py PASS)
- dispatcher self-record 시 ActionRun.triggered_by = `neo://agent/claude-opus-4-7` 일관

**판정**: **유지** — model upgrade 시 alias 추가 패턴 박제됨. 재평가 불필요.

---

## v0.5 / v0.6 새 trigger 후보 (관찰)

v0.4 진입 산출 (Graph RAG + Vector + Neo4j scaffold) 이후 발견된 새 패턴:

1. **HippoRAG PPR seed 의 의미적 모호**: seed=Service vs Service{kind:pm2} 의 PPR 결과 분포 차이 — v0.5 에서 Service kind 별 subtype 필요할 수도
2. **LightRAG dual-level 의 community → entity drilling**: community 가 너무 큼 (c000 59 nodes) — community 자체를 subtype 한 hierarchy 검토
3. **SBU vector index 의 unowned 36건**: Skill 클래스가 SBU 에 owned_by 미연결 — Skill 의 ownership 재설계 (Project vs Agent ownership)

위 3건은 v0.5 이후 평가 항목으로 박제 (현 단계 G1-22~24 매트릭스 외 신규).

---

## 결론

| Subtype | v0.2 결정 | v0.4 재평가 | 누적 거부 단계 |
|---|---|---|---|
| Artifact | v0.3 DEFER | **DEFER 유지** | v0.5+ 재평가 |
| Service | v0.4 DEFER | **DEFER 유지** (Neo4j scaffold 단계) | Neo4j 실 가동 후 |
| Task | v0.3 DEFER | **DEFER 유지** | 반복 시도 패턴 발생 시 |
| Agent | v0.1 G1-12 해소 | n/a | n/a (영구 박제) |

v0.4 진입에도 subtype 분리 0건. 단일 클래스 + Revision/ActionRun 분해 + linkProperties + markings 의 조합이 충분.

`validate.py` 6/6 P0 PASS + `validate_competency.py` 20/20 PASS + Critical 위반 0건 유지.

---

## G1 박제

| ID | 결정 | reversible? |
|---|---|---|
| G1-25 | OntoClean 4 subtype v0.4 재평가 결과 → DEFER 유지, v0.5+ 재평가 | yes |

owner 한 줄로 "Service subtype 분리해" 같은 reverse 가능. 그 경우 `extract_minimal.py` 의 Service 추출 분기 필요 (kind 별 subclass mapping).

---

👤 Strategy Lead Claude Opus 4.7 (G1-25 자율 박제)
