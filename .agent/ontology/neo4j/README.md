# `.agent/ontology/neo4j/` — v0.4 Neo4j Migration Scaffold

> v0.4 진입 게이트. G1-8 (Store paradigm: DuckDB → Neo4j → +n10s).
> 박제: 2026-05-14 (Strategy Lead Claude Opus 4.7)
> Status: **scaffold 만 박제** — 실 가동은 owner Docker 환경 필요

---

## Bootstrap 순서

### 1. Docker Desktop 가동
- Windows: Docker Desktop 4.x+
- 메모리 할당 권장: ≥ 2GB
- 디스크 권장: ≥ 5GB free

### 2. Password 설정
```bash
# .agent/ontology/neo4j/.env (gitignore 됨)
NEO4J_PASSWORD=<강력한_password_여기에>
```

또는 환경변수로:
```bash
export NEO4J_PASSWORD=<...>  # bash
$env:NEO4J_PASSWORD = "<...>" # PowerShell
```

### 3. Neo4j 컨테이너 가동
```bash
cd .agent/ontology/neo4j
docker compose up -d
# Healthcheck 대기 (~20초)
docker ps --filter "name=neo-genesis-neo4j"
```

### 4. Schema 적용
```bash
docker exec -i neo-genesis-neo4j cypher-shell \
  -u neo4j -p "$NEO4J_PASSWORD" < cypher_schema.cql
```

13 constraints + 11 indexes 박제.

### 5. JSONL → Neo4j Migration
```bash
export NEO4J_PASSWORD=<...>
python scripts/ontology/migrate_to_neo4j.py --import-nodes --import-edges --verify
```

Expected: `node_parity=true, edge_parity=true` (current: 330 nodes / 161 edges).

### 6. Browser 검증
- URL: http://localhost:7474
- Login: neo4j / `$NEO4J_PASSWORD`
- Test query:
  ```cypher
  MATCH (a:Service)-[:DEPENDS_ON]->(b:Service)
  RETURN a.name, b.name
  ```

---

## Dual-write phase (v0.4 ~ v0.5)

v0.4 의 핵심: **JSONL 이 여전히 authoritative**.
- `extract_minimal.py` / `mutate.py` / `auto_record.py` 모두 JSONL 에 쓴다
- `migrate_to_neo4j.py` 는 주기적으로 Neo4j 를 sync (cron 권고)
- Neo4j 는 query-only (Cypher / multi-hop / Graph RAG)

v0.5 에서 권한 이양 평가 — Neo4j primary + JSONL backup.

---

## n10s (RDF export, v1.0 준비)

`cypher_schema.cql` 의 첫 블록이 n10s constraint. 활성화:

```cypher
CALL n10s.graphconfig.init();
CALL n10s.nsprefixes.add('neo', 'https://neo.genesis/ontology/');
CALL n10s.nsprefixes.add('prov', 'http://www.w3.org/ns/prov#');
```

이후 RDF export:
```cypher
CALL n10s.rdf.export.cypher('MATCH (n) RETURN n LIMIT 100');
```

v1.0 에서 Oxigraph SPARQL endpoint 연동 평가.

---

## Rollback

```bash
docker compose down
# JSONL 은 손상 없음 (primary 유지)
# 다시 DuckDB query 로 회귀:
python scripts/ontology/query.py --object-set neo://object-set/services-by-status
```

---

## v0.4 진입 트리거 (Strategy Lead 자율 결정 후 활성)

다음 중 1건 이상 발생 시 v0.4 활성:
- 노드 > 10K 또는 엣지 > 50K (현재 330 / 161)
- 3-hop 이상 transitive query 빈번 (현재 HippoRAG PPR 로 충분)
- LangChain / GraphRAG 공식 통합 필요성 (v0.4 RAG 결합 시)
- text-to-Cypher LLM agent 검증 작업 발생

현재는 DuckDB 로 충분 — 가동은 owner G2.
