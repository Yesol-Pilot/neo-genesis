# `.agent/ontology/` — Neo Genesis Operating Ontology

> **Status**: v0.1 (2026-05-14) — contract + PoC extraction 박제
> **Author**: Strategy Lead Claude Opus 4.7
> **포지셔닝**: 관계 인덱스, **NOT** SSOT

---

## 이게 뭔가

Neo Genesis (1인 AI 회사 — 11 SBU + 2 NeurIPS 논문 + multi-device fleet + quant bot + 5 AI agent) 의 운영 가능한 ontology v0.1. Palantir Foundry 의 semantic + kinetic ontology 패턴을 1인 회사 규모로 재구성한 것.

답해야 할 핵심 질문 (`competency_questions.yaml` 20개):
- 이 파일 고치면 어디가 깨지나? (impact analysis)
- shared-brain status 가 24시간 stale 인가? (staleness detection)
- 누가 무엇을 언제 만들었나? (PROV-O provenance)
- 어떤 에이전트가 어떤 권한으로 어떤 실행을 했나? (audit trail)
- Claude / Codex / Sora 가 동시에 같은 SSOT 를 편집하면 충돌 어떻게? (multi-agent governance)

---

## 이게 뭐가 아닌가 (중요)

**SSOT 가 아니다**. SSOT 는 여전히:
- `.agent/NEO_MASTER_RULES.md`
- `.agent/BIBLE.md`
- `.agent/knowledge/`
- `.agent/personas/`
- `.agent/policies/`
- `.agent/shared-brain/`

ontology 본문이 SSOT 와 모순되면 **SSOT 가 항상 이긴다**. ontology 는 그 관계를 인덱싱할 뿐이다.

ontology 가 새 정보를 만들지 않는다. 기존 정보의 관계만 박제한다.

---

## 디렉토리 구조

```
.agent/ontology/
├── README.md                          # 이 파일
├── DESIGN_v0.1.md                     # contract (11 클래스 / 17 관계 / URI 스킴 / anti-patterns)
├── RESEARCH_v0.1.md                   # 6 영역 prior art 종합 (W3C / Palantir / KG / Memory / Methodology / Store)
├── ontology.schema.json               # JSON Schema (nodes + edges 검증)
├── competency_questions.yaml          # 20 질문 + SQL 패턴 (v0.2 acceptance gate)
├── ontoclean_metaproperties_v0.1.md   # 11 클래스 OntoClean 검증 (G1-21)
├── nodes.jsonl                        # 노드 (Artifact, Service, Agent, ...)
├── edges.jsonl                        # 엣지 (PROV-O 관계, owned_by, depends_on, ...)
└── extract_report.json                # 추출 통계
```

추출 스크립트: `scripts/ontology/extract_minimal.py` (v0.2 PoC).

---

## 11 클래스 (DESIGN §3 요약)

| 클래스 | 무엇 | PROV-O 매핑 |
|---|---|---|
| Artifact | 파일·문서·코드·데이터셋·결정 | - |
| Revision | Artifact 의 immutable 스냅샷 | prov:Entity |
| Project | 11 SBU + 2 논문 + Neo Genesis 자체 | - |
| Service | 가동 중인 프로세스 (PM2, container, deploy) | - |
| Device | 물리/가상 머신 (fleet) | - |
| Agent | AI 에이전트 / persona spec | prov:Agent |
| Task | 작업 단위 | - |
| Policy | 규칙·게이트·deny-list | - |
| ActionRun | atomic transaction audit | **prov:Activity** |
| Skill | 재사용 가능 검증된 function/subagent (Voyager) | - |
| Reflection | episodic 기억의 abstraction (Generative Agents) | - |

---

## 17 관계 (DESIGN §4 요약)

`current_revision` / `prov:wasGeneratedBy` / `prov:wasAssociatedWith` / `prov:wasDerivedFrom` / `supersedes` / `owned_by` / `deployed_to` / `depends_on` / `governs` / `allowed_by` / `denied_by` / `affects` / `assigned_to` / `blocks` / `references` / `instantiates` / `composed_of` / `reflects_on`

---

## Memory MCP 와의 경계 (G1-1)

**파일이 원본, memory MCP 는 휘발성 캐시.**
- 원본: `nodes.jsonl` + `edges.jsonl`
- 캐시: `mcp__memory__create_entities` / `create_relations` 로 매 세션 시작 시 rehydrate (선택적)
- write 는 파일에만. memory MCP 에 직접 쓰는 코드 금지.

근거: `.agent/` 패턴 일관성 / git-trackable / MCP disconnect 견딤 / multi-agent (Codex / Sora / Ollama) 호환 / frontmatter rich metadata.

---

## Store / Query paradigm 로드맵 (G1-8)

| 단계 | Store | Query | 트리거 |
|---|---|---|---|
| **v0.1** (현재) | JSONL + **DuckDB** | SQL (+ recursive CTE) | 즉시 — `pip install duckdb` + `SELECT * FROM read_ndjson_auto(...)` |
| v0.4 | **Neo4j Community 5.x** (Docker) | Cypher | RAG 통합 시점 (3-hop 이상 질의 빈번 / 노드 > 10K) |
| v1.0 | Neo4j + `n10s` plugin | Cypher primary + SPARQL export | 외부 federation 필요 시 |

**Full Triple Store (Apache Jena / Stardog / Virtuoso) 거부** — text-to-SPARQL LLM 정확도 3.3% (CypherBench Claude 3.5 EX 61.58% 대비).

---

## 사용법 (v0.1)

### 추출
```bash
python scripts/ontology/extract_minimal.py
# → .agent/ontology/nodes.jsonl, edges.jsonl, extract_report.json
```

### DuckDB query (v0.1 권고)
```python
import duckdb
con = duckdb.connect()
con.execute("CREATE VIEW nodes AS SELECT * FROM read_ndjson_auto('.agent/ontology/nodes.jsonl')")
con.execute("CREATE VIEW edges AS SELECT * FROM read_ndjson_auto('.agent/ontology/edges.jsonl')")
# CQ-08: 24h heartbeat 없는 Device
result = con.execute("""
  SELECT hostname FROM nodes
  WHERE rdf_type = 'Device' AND online = false
""").fetchall()
```

### 검증
```bash
# JSON Schema validation (v0.2 에서 박제)
python scripts/ontology/validate.py
# OntoClean check
cat .agent/ontology/ontoclean_metaproperties_v0.1.md
```

---

## v0.X Roadmap (DESIGN §14)

| 버전 | 핵심 | 게이트 |
|---|---|---|
| **v0.1** (이번) | contract + research + PoC extraction 178 nodes / 91 edges | owner ACK |
| v0.2 | 50→500 노드 / 100→500 엣지 + OntoClean subtype 분리 + competency Q 20/20 PASS | 20/20 PASS |
| v0.3 | Single Writer Queue + nano-graphrag PoC + OAG governed execution | 7일 audit 수집 |
| v0.4 | Neo4j 이전 + LightRAG dual-level + RAG 통합 | retrieval +10% |
| v0.5 | HippoRAG PPR + OWL EL transitive 추론 | multi-hop query 라이브 |
| v1.0 | n10s RDF export + Oxigraph SPARQL endpoint | 외부 federation 1건 |

---

## Personal 절대 금지

`personal/` 디렉토리 (법무·금융·개인회생) 는 ontology 에 **단 한 줄도 들어가지 않는다**. extract 스크립트의 skip-list 에 hardcode.

만약 ontology 노출 시 자동:
- `markings: [personal-forbidden]`
- `allowedAgents: []` (0 agent 접근)

---

## 거버넌스

- 스키마 변경 = RFC (`rfcs/RFC-NNNN.md`) → OOPS! Pitfall scan (Critical 0, Important ≤2) → owner G2 reviewer → merge
- Deprecation 우선: 절대 비파괴 삭제 금지, `owl:deprecated true` + `supersededBy` 한 MINOR 이상 유지
- Migration script 의무: MAJOR bump 시 SPARQL UPDATE + JSON-LD frame 변환

---

## 인용 / Prior Art

90+ citations in `RESEARCH_v0.1.md`. 핵심:
- **W3C**: PROV-O / SKOS / OWL 2 / RDF 1.2 / SHACL
- **Palantir Foundry**: Ontology System / Action Types / Functions / Markings
- **KG 학술**: Hogan et al. 2021 (ACM Comp Surv 54(4))
- **Memory**: MemGPT / Letta / CoALA / Voyager / Generative Agents
- **Graph RAG**: GraphRAG / LightRAG / HippoRAG
- **Methodology**: LOT / METHONTOLOGY / NeOn / OntoClean / OOPS!
- **Store**: Neo4j / DuckDB / Oxigraph; CypherBench EX 61.58% (Claude 3.5)

---

👤 Strategy Lead Claude Opus 4.7
