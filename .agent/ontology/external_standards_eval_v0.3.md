# External Standards Evaluation v0.3 — SHACL / SKOS / RML

> **Status**: G1 박제 (2026-05-14, Strategy Lead Claude Opus 4.7)
> **Companion**: `RESEARCH_v0.1.md §5` (W3C agent 평가표), `DESIGN_v0.1.md §7` (External Standards Integration)
> **Decision**: 3건 모두 v0.3 에선 **DEFER**, v0.4 / v0.5 trigger 조건 명시 박제

W3C 표준 3건의 v0.3 채택 여부를 cold judgment 로 박제한다. DESIGN §7 의 채택 매트릭스에서 "v0.3 평가" 로 deferred 됐던 항목들.

---

## 1. SHACL (Shapes Constraint Language)

**W3C Recommendation**: 2017-07-20 / https://www.w3.org/TR/shacl/

### 핵심 기능
- `sh:NodeShape` + `sh:PropertyShape` 로 RDF 그래프 제약 표현
- `sh:targetClass` 로 타입 단위 검증
- SPARQL-based constraint (`sh:select`, `sh:sparql`)
- `sh:Severity` (Info / Warning / Violation) 3-tier
- `sh:ValidationReport` RDF 그래프 반환 (machine-readable)

### v0.3 도입 ROI 분석

| 항목 | 현재 (validate.py) | SHACL 도입 시 |
|---|---|---|
| 검증 표현 | Python imperative | RDF declarative |
| Class hierarchy 추론 | 수동 (`VALID_KINDS` set) | 자동 (`rdfs:subClassOf`) |
| Cross-property constraint | 가능 (Python if/else) | 가능 (SPARQL-based) |
| Severity level | 단일 (P0/P1 분리만) | 3-tier (Info/Warning/Violation) |
| ValidationReport 표준 | JSON 자체 포맷 | RDF/Turtle 표준 |
| LLM ergonomics | text-to-SQL 47% (DuckDB query 직접) | text-to-SHACL 정확도 미측정 (낮을 것으로 추정) |
| 운영 비용 | `pip install jsonschema` (이미 됨) | SHACL engine 추가 (pySHACL, TopBraid 등) — Java/Python 둘 다 가능 |

### v0.3 결정: **DEFER**

**근거**:
1. 현 `validate.py` 가 6/6 P0 gate 를 0건 violation 으로 PASS — 검증 표현력 부족 미발견.
2. SHACL 의 핵심 가치는 RDF Triple Store 와 결합할 때 — 우리 v0.3 은 여전히 DuckDB (JSONL on relational) 단계.
3. text-to-SHACL LLM 정확도 부족 — agent 가 동적으로 새 constraint 작성 시 정확도 미보장.
4. ValidationReport RDF 출력은 우리 owner 가 텍스트로 읽는 패턴과 mismatch.

**v0.4 trigger**: Neo4j 이전 + n10s RDF export 활성 후, **SHACL constraint 5건 이상 작성 필요성** 발생 시 평가. 후보:
- `Artifact{kind:persona}` 는 `tier` ∈ {S,A,B,C} 강제 (cross-property)
- `Service` 의 `host_device` 가 실존 Device 인지 graph-level 검증
- `markings: [personal-forbidden]` 는 항상 `allowedAgents: []` 강제 (mutual exclusion)
- transitive `depends_on` 의 cycle 검출 (recursive shape)
- `ActionRun.affectedObjects` 가 모두 실존 노드 (deep referential integrity)

**예비 SHACL shape 예시** (v0.4 작성 예정):
```turtle
neo:PersonaShape a sh:NodeShape ;
    sh:targetClass neo:Agent ;
    sh:property [
        sh:path neo:agent_kind ;
        sh:hasValue "persona_spec" ;
        sh:property [
            sh:path neo:tier ;
            sh:in ( "S" "A" "B" "C" ) ;
            sh:minCount 1 ;
        ] ;
    ] .
```

---

## 2. SKOS (Simple Knowledge Organization System)

**W3C Recommendation**: 2009-08-18 / https://www.w3.org/TR/skos-reference/

### 핵심 기능
- `skos:Concept` — 분류 체계의 원자 단위
- `skos:ConceptScheme` — 분류 체계 그룹
- `skos:broader` / `skos:narrower` / `skos:related` — 계층 + 연관
- `skos:prefLabel` / `skos:altLabel` — 다국어 label
- `skos:notation` — 코드 표현 (P0/P1/P2/P3 같은)

### v0.3 도입 ROI 분석

우리 v0.1 의 controlled vocabulary 후보:

| Vocabulary | 현재 표현 | SKOS 표현 시 |
|---|---|---|
| Tier (S/A/B/C) | Agent.tier enum | `neo:TierScheme` + 4 Concept + broader 관계 (S > A > B > C) |
| Priority (P0~P3) | Task.priority enum | `neo:PriorityScheme` + 4 Concept + `skos:notation` |
| Markings (personal-forbidden 등) | Artifact.markings string[] | `neo:MarkingsScheme` + Concept 계층 |
| Kind enum (Artifact.kind 11종) | enum | `neo:ArtifactKindScheme` 11 Concept |
| SBU 분류 | Project.kind enum | `neo:ProjectKindScheme` |

### v0.3 결정: **DEFER**

**근거**:
1. 현 enum (Python set / JSON Schema) 만으로 5K~50K 노드 규모에서 충분 — SKOS 의 ROI 는 수십~수백 Concept 의 분류 체계에서 발생.
2. 다국어 label 수요 부재 — owner 는 한국어 단일, agent 는 영문 slug 단일 사용.
3. `skos:broader` 의 transitive 추론은 OWL EL 활성 (v0.5) 후 자연스러움.
4. SKOS Concept 와 OWL Class 혼용 시 의미 충돌 위험 (RESEARCH §3 발견 #3).

**v0.5 trigger**: 분류 체계가 다음 중 1건 이상 발생 시 평가:
- Tier 4-tier → 8-tier 확장 (S+/S/A+/A/B+/B/C+/C)
- markings 가 hierarchical (`confidential ⊂ restricted`) 필요
- SBU 분류가 sub-category 갖춤 (`sbu/saas`, `sbu/blog`, `sbu/game`)
- 다국어 label 필요 (외부 federation, schema.org JSON-LD export)

---

## 3. RML (RDF Mapping Language)

**Unofficial Draft**: v1.1.2 (2024-06-20) / https://rml.io/specs/rml/

### 핵심 기능
- 비-relational source (JSON / CSV / XML) → RDF triple 매핑
- `rml:LogicalSource` + `rml:referenceFormulation` (JSONPath / XPath)
- R2RML 의 확장 — SQL 외 source 지원
- W3C Knowledge Graph Construction Community Group 개발 중

### v0.3 도입 ROI 분석

우리 현 source 매핑:

| Source | 현재 방식 | RML 매핑 시 |
|---|---|---|
| `.agent/knowledge/*.md` (YAML frontmatter) | Python walk + `pyyaml` parse | RML map → RDF triple (그러나 YAML 직접 지원 없음 — 커스텀 referenceFormulation 필요) |
| `.agent/policies/*.yaml` | Python walk + parse | 동일 |
| `~/.claude/agents/*.md` | Python walk | 동일 |
| `Yesol-Pilot/<repo>` (git remote) | Python git API | RML 지원 외 |
| Supabase `quant_*` 테이블 | (out-of-scope v0.1) | R2RML (Triple Store + SQL endpoint 필요) |

### v0.3 결정: **DEFER 강함**

**근거**:
1. **Unofficial Draft 상태**: "This document is a draft of a potential specification. It has no official standing of any kind." — production 의존 불가.
2. **YAML / Markdown source 미지원**: 핵심 source 모두 커스텀 확장 필요 — 사실상 자체 ETL 과 동일 비용.
3. **현 Python extract_minimal.py 가 충분**: 12 sub-extractor + relation 추론으로 325 nodes / 161 edges 추출 라이브. RML 도입은 ETL 표준화 마진 < 학습 곡선 비용.
4. **R2RML 영구 거부 (DESIGN §15)**: SQL 전용이라 우리와 부적합. RML 은 R2RML 의 확장이지만 같은 한계 상속.

**v1.0 trigger**: 다음 중 2건 이상 발생 시 평가:
- Triple Store (Apache Jena / Stardog) 도입
- External SBOM (SPDX) / SLSA provenance feed 추출 → 표준 ETL 필요
- 외부 federation 1건 이상 (DBpedia / Wikidata)
- RML 1.2 W3C Recommendation 승격 (현 timeline 미정)

---

## 4. 본 평가의 v0.3 closure 정합성

DESIGN_v0.1 §7 External Standards 표 갱신:

| 표준 | 직전 (v0.1) | 본 평가 (v0.3) | 다음 단계 |
|---|---|---|---|
| SHACL | "v0.3 거부" (deferred to evaluate) | ✅ **v0.4 trigger 조건 박제** | Neo4j + n10s 활성 + constraint 5건 |
| SKOS | "v0.3 거부" | ✅ **v0.5 trigger 조건 박제** | controlled vocabulary 8-tier 이상 / 다국어 / hierarchical markings |
| RML | "v0.3 평가" | ✅ **v1.0 trigger 조건 박제 (강한 DEFER)** | Triple Store + RML 1.2 Rec |

---

## 5. owner 한 줄 reversible

| ID | 결정 | reversible? |
|---|---|---|
| G1-22 | SHACL v0.3 deferred → v0.4 trigger | yes |
| G1-23 | SKOS v0.3 deferred → v0.5 trigger | yes |
| G1-24 | RML v0.3 강한 deferred → v1.0 trigger | yes |

owner 가 "지금 SHACL 도입해" 같은 한 줄로 reverse 가능. 그 경우 SHACL engine (pySHACL) install + shape 작성 + ValidationReport 통합 → v0.4 Neo4j 이전 전이라도 강제 가능.

---

## 6. 결론

3건 모두 **현 단계 ROI < 학습 + 운영 비용**. trigger 조건 명시 박제로 자율 진행 가능. v0.3 의 W3C 평가 항목 closure.

기존 `validate.py` 6/6 P0 gate + `validate_competency.py` 20/20 PASS + auto_record.py PROV-O Activity 패턴이 **현 표현력의 한계 미발견** 상태 유지.

---

👤 Strategy Lead Claude Opus 4.7 (G1-22 ~ G1-24 자율 박제)
