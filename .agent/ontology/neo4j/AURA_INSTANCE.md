# Neo4j AuraDB Instance — Live State

> v0.4 라이브 박제 (2026-05-14, Strategy Lead Claude Opus 4.7)
> **password 미박제** (보안 — `CREDENTIAL_BIBLE.md` 또는 owner env var 보관)

## Instance 정보

| 필드 | 값 |
|---|---|
| AURA_INSTANCEID | `394b2602` |
| Instance Name | `My instance` |
| NEO4J_URI | `neo4j+s://394b2602.databases.neo4j.io` |
| NEO4J_USERNAME | `neo4j` |
| NEO4J_DATABASE | `neo4j` |
| NEO4J_PASSWORD | **REDACTED** — `CREDENTIAL_BIBLE.md` 또는 owner env var 참조 |
| Tier | **AuraDB Free** (50K nodes / 175K relationships) |
| Edition | Enterprise (Aura managed) |
| Server | Neo4j Kernel 5.27-aura |

## 박제된 schema (12 constraints + 25 indexes)

```
12 unique constraints (id 필드 per 11 classes + n10s_unique)
25 indexes (실제 적용: 11 — 직접 CREATE INDEX 11 + 자동 14 from constraint)
```

자세히는 `cypher_schema.cql` 참조. AuraDB Free 는 n10s/apoc plugin 미지원 → 해당 statement 자동 skip (v1.0 전환 시 self-host 검토).

## Live state (2026-05-14 첫 박제)

```
nodes: 333 (node_parity TRUE vs JSONL)
  Artifact 94 / Revision 52 / Agent 37 / Skill 36 / Reflection 31 / Task 31 /
  Project 14 / Service 13 / Device 11 / ActionRun 8 / Policy 6

edges: 160 (1건 차이 — references 1건 MATCH 실패, owned_by 또는 target node 미박제)
  prov:wasGeneratedBy 32 / owned_by 58 / references 34 / governs 18 /
  deployed_to 13 / depends_on 4 / prov:wasAssociatedWith 1
```

## 사용 (env var 설정 후)

```powershell
# PowerShell
$env:NEO4J_BOLT_URI = "neo4j+s://394b2602.databases.neo4j.io"
$env:NEO4J_USER = "neo4j"
$env:NEO4J_PASSWORD = "<from credential bible>"

# Migration (idempotent — 재실행 안전)
python scripts/ontology/migrate_to_neo4j.py --import-nodes --import-edges --verify

# Schema 재적용 (idempotent — IF NOT EXISTS 박제)
python scripts/ontology/apply_neo4j_schema.py

# Cypher query (browser: https://console.neo4j.io)
# MATCH (s:Service)-[:DEPENDS_ON*1..3]->(t:Service) RETURN s.name, t.name
```

## Live Cypher 검증 (라이브 첫 박제)

| Query | Result |
|---|---|
| CQ-06 quant-bot-live host | ysh-server |
| CQ-07 ysh-server services | 8건 (sora-live running 외 7건) |
| CQ-08 offline devices | heejin / mx-macbuild / s26-ultra / tab-s10-ultra (4건) |
| Impact 2-hop from supabase-api | quant-bot-live (1-hop) / neo_genesis_daemon (1-hop) / sora-live (2-hop) |
| Tier S personas | 8 (korean-copywriter-tone / korean-seo-geo-strategist / multi-agent-orchestrator / prompt-injection-auditor / quant-strategy-lead / senior-backend-eng-korean / senior-da-pm-korean / sora-sre-ops) |
| ActionRun by kind | 6종 (dispatcher_route 2, ontology_mutation 2, extract/killswitch/deploy/heartbeat 각 1) |

## 보안 정책

### Password rotation — owner declined (2026-05-14)
owner 결정: 본 instance password 회전 불필요 (AuraDB Free + non-production + 본 chat scope risk acceptable). 본 README 의 password 필드는 영구 **REDACTED** 유지. `.env` 또는 env var 로 owner 가 사용.

### P1 — AuraDB Free 3-day auto-pause
Free tier 는 3일 inactivity 후 auto-pause. owner 가 console 에서 resume 클릭 시 1~2분 후 가용.
- 회피: 매일 1회 `python scripts/ontology/migrate_to_neo4j.py --verify` cron (heartbeat 등가)
- 또는: Pro upgrade ($65/월) — over-spec, 비권고

### P2 — RDF export 불가
n10s plugin AuraDB Free 미지원. RDF/SPARQL export 필요 시:
- v1.0 까지 self-host Neo4j Community + n10s 전환
- 또는 Oxigraph (Rust, MIT) 별도 endpoint

## 다음 단계

1. **password 회전 + .env 박제** (owner P0)
2. **LangChain Neo4j 통합** (`langchain-neo4j` + `GraphCypherQAChain`)
3. **MCP server 의 query.py 가 Neo4j 옵션 지원하도록 확장** (v0.5)
4. **dual-write hook**: mutate.py 의 변경 사항을 JSONL + Neo4j 동시 반영
