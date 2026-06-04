# OntoClean Subtype 분리 평가 v0.2

> **Status**: G1 박제 (2026-05-14, Strategy Lead Claude Opus 4.7)
> **Companion**: `ontoclean_metaproperties_v0.1.md` (4 위반 클래스 식별)
> **Decision**: subtype 분리 4건 모두 **v0.2 에선 보류**. 단일 클래스 유지 + doc 명시. v0.3 ~ v0.5 단계별 평가.

---

## 결정 매트릭스 (G1 자율 박제)

OntoClean 위반 4 클래스 (Artifact / Service / Agent / Task) 의 subtype 분리 평가:

| 위반 클래스 | 제안 subtype | v0.2 결정 | 근거 | reversible? |
|---|---|---|---|---|
| **Artifact** (~R 혼재) | `ImmutableArtifact` (+R) / `MutableArtifactSlot` (~R) | 🟡 **DEFER v0.3** | Revision 클래스가 +R 부분 cover 中 — 명시적 subtype 분리는 query 복잡도 +30% 대비 학술 정합성 마진 ROI 낮음 | yes |
| **Service** (~R) | `ServiceDefinition` (+R) / `ServiceInstance` (~R) | 🟡 **DEFER v0.4** | v0.4 Neo4j 이전 시 함께 (Cypher 의 label inheritance 가 자연스러움). v0.2 PoC 단계에선 status enum 으로 충분 | yes |
| **Agent** (~R + -I 위험) | identity criterion 명시 (이미 해소) | ✅ **v0.1 박제 완료** (G1-12) | `id` URI 가 유일 identity, model/tier/label 변경은 alias 추가만. -I 위험 해소 | yes |
| **Task** (~R + -I) | `TaskTemplate` (+R) / `TaskExecution` (~R) | 🟡 **DEFER v0.3** | ActionRun{kind:task_execution} 으로 v0.3 에서 분해. 현재 ActionRun 이 이미 transactional 매핑 가능 | yes |

**v0.2 acceptance**: subtype 분리 0건. 단일 클래스 + doc 박제 + Revision/ActionRun 으로 +R 부분 cover.

---

## 평가 상세

### 1. Artifact subtype 분리 — v0.3 DEFER

**제안**:
```
Artifact (abstract, ~R)
├── ImmutableArtifact (+R)    -- content_hash 가 정의된 시점 그대로
│   └── 예: Revision 가 가리키는 특정 sha256 콘텐츠
└── MutableArtifactSlot (~R)  -- path 가 정의된 시점 그대로지만 내용 가변
    └── 예: "active-tasks.md 이 path 의 파일" (수정 가능)
```

**v0.2 거부 근거**:
- query 복잡도: SQL/Cypher 에서 union 추가 (`WHERE rdf_type IN ('ImmutableArtifact', 'MutableArtifactSlot')`)
- migration 부담: 기존 추출 스크립트 + 모든 SQL query 의 `WHERE rdf_type='Artifact'` 수정
- 학술 정합성 마진: OntoClean 형식 위반 → 명시화. 그러나 위반의 실질 risk 는 query 모호성. PoC 단계 0건 발생.
- 대안: Revision 클래스 (이미 박제) 가 immutable 부분 cover. Artifact = container, Revision = snapshot 의 분해가 동등 효과.

**v0.3 평가 조건**:
- competency Q 추가 시 "이 path 의 파일과 이 특정 revision 을 구분" 질문 발생
- multi-agent write 충돌이 path-level vs revision-level 혼동에서 발생

### 2. Service subtype 분리 — v0.4 DEFER

**제안**:
```
Service (abstract, ~R)
├── ServiceDefinition (+R)  -- deployment spec
│   └── 예: "quant-bot-live 라는 PM2 process 의 정의 (이름, 의존성, ecosystem.config)"
└── ServiceInstance (~R)    -- 실제 가동 스냅샷
    └── 예: "quant-bot-live PID 12345 status=running"
```

**v0.2 거부 근거**:
- Foundry 의 ServiceDefinition 패턴이 v0.4 Neo4j 이전 시 자연스러움 (Cypher label inheritance)
- v0.2 PoC 단계에선 status enum (`running/stopped/draining`) 으로 충분
- PM2 ecosystem.config 가 Definition 등가 — 현 source mapping 으로도 추적 가능

**v0.4 평가 조건**:
- v0.4 RAG 통합 시 "정의된 Service 와 실제 가동 인스턴스" 분리 query 필요성
- ITIL CMDB federation 시 CI hierarchy 적용

### 3. Agent identity criterion — ✅ v0.1 박제 완료

이미 G1-12 박제. `id` URI 가 유일 identity. v0.1 nodes.jsonl 검증:

```
$ python scripts/ontology/validate.py
[P0] Required fields: PASS  (Agent id/agent_kind 100%)
[P0] URI uniqueness: PASS  (Agent 37개 모두 unique)
```

v0.1 추출 데이터에서 동일 agent_kind=model_instance 의 model 변경 (e.g. claude-opus-4-7 → claude-opus-4-8) 시: 신규 id 박제 (`neo://agent/claude-opus-4-8`) 또는 기존 id 유지 + model 속성 갱신 + aliases 추가. v0.1 PoC 에선 후자 권고 (id 보존).

### 4. Task subtype 분리 — v0.3 DEFER

**제안**:
```
Task (abstract)
├── TaskTemplate (+R)    -- 작업 의도의 단위 ("P0 #1 9-Layer Kill Switch wiring")
│   └── identity = slug or ulid
└── TaskExecution (~R)   -- 실제 한 번의 시도
    └── identity = ulid, parent=TaskTemplate
```

**v0.2 거부 근거**:
- 현재 30 Task 추출 결과 모두 active-tasks.md 의 체크박스 라인 = Template 등가
- 재실행 / 시도는 ActionRun 으로 박제 (v0.1 에 이미 존재)
- TaskTemplate 분리 시 active-tasks.md 마이그레이션 부담 (모든 entry 가 template + execution 2개로 분해)

**v0.3 평가 조건**:
- Strategy Lead 의 주간 리뷰가 "동일 task 가 N번 시도되었는데 평균 성공률은?" 같은 질문 발생
- ActionRun 의 affectedObjects 에 Task 포함하는 패턴이 일반화

---

## v0.2 단일 클래스 유지 정책

OntoClean 위반 4 클래스 모두:

1. **doc 명시 의무**: DESIGN_v0.1 §3 의 각 클래스 NOT 정의 + OntoClean 주석 박제
2. **rigid 부분 cover**: Artifact ← Revision (+R), Task ← ActionRun (+R)
3. **identity criterion 명시**: 모든 클래스의 `id` 가 유일 identity (G1-12 박제)
4. **query 시 명시적 필터**: SQL/Cypher 에서 anti-rigid 클래스 query 시 `WHERE status / state` 조건 필수

이로써 v0.2 의 OntoClean Critical 위반 0건, Important 위반 4건 (이미 doc 박제로 acknowledged) 상태.

---

## v0.3 / v0.4 / v0.5 단계별 trigger

| 단계 | 평가할 subtype | trigger |
|---|---|---|
| v0.3 | Artifact 분리 (ImmutableArtifact / MutableArtifactSlot) | competency Q 에서 sha-level vs path-level 혼동 발생 시 |
| v0.3 | Task 분리 (TaskTemplate / TaskExecution) | 반복 시도 추적 query 필요 시 |
| v0.4 | Service 분리 (ServiceDefinition / ServiceInstance) | Neo4j 이전 + Cypher label inheritance 활용 시 |
| v0.5 | Agent 더 세분화 (LLMAgent / HumanAgent / PersonaAgent 등) | A2A protocol multi-agent delegation 활성 시 |

---

## 검증

```bash
$ PYTHONIOENCODING=utf-8 python scripts/ontology/validate.py
[P0] URI uniqueness: PASS
[P0] URI format: PASS
[P0] Required fields: PASS  (4 anti-rigid 클래스 모두 통과)
[P0] Edge integrity: PASS
[P0] Markings integrity: PASS
[P0] Secret redaction: PASS
[P1] All 11 classes populated: YES
PASS -- all P0 / P1 gates green
```

OntoClean Critical 0건 + Important 4건 (acknowledged) 으로 v0.2 acceptance gate 통과.

---

👤 Strategy Lead Claude Opus 4.7 (G1 자율 박제, 한 줄 reversible)
