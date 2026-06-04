# Neo Genesis Ontology — DESIGN v0.1

> **Status**: v0.5 라이브 + v0.4 Neo4j AuraDB sync + business layer v0.1 분리 (2026-05-14)
> **Author**: Strategy Lead Claude Opus 4.7
> **Companion doc**: [`RESEARCH_v0.1.md`](./RESEARCH_v0.1.md) (prior art), [`business/DESIGN_business_v0.1.md`](./business/DESIGN_business_v0.1.md) (Neo Genesis 본질)
> **Layer 분리**: 본 문서 = **meta-ontology** (agent runtime audit, `neo://artifact/agent/service/...`). business layer 는 별도 `.agent/ontology/business/` (`neo://biz/...`).
> **Reversibility**: 모든 G1 결정은 owner 한 줄 명령으로 뒤집힘
> **SSOT 위치**: 이 문서는 `.agent/ontology/` 의 contract. SSOT 는 여전히 `.agent/NEO_MASTER_RULES.md` + `.agent/BIBLE.md`.

---

## §1. 포지셔닝

이 온톨로지는 **관계 인덱스**다. SSOT 가 아니다.

- **SSOT 는 여전히 `.agent/`** (NEO_MASTER_RULES, BIBLE, knowledge/, personas/, policies/, contracts/, runbooks/).
- 이 온톨로지는 SSOT 의 파일·객체·실행을 **"무엇이 무엇과 어떻게 연결되는가"** 만 박제한다.
- 새 정보를 만들지 않는다. 기존 정보의 관계를 인덱싱한다.
- ontology 본문이 SSOT 와 모순될 경우 **SSOT 가 항상 이긴다**. 모순 발견 시 ontology 를 갱신한다.

### 왜 만드는가
- 작업 영향 범위 즉답 ("이 파일 고치면 어디가 깨지나")
- stale 데이터 즉시 식별 ("shared-brain status 가 24시간 stale 인가")
- 다중 에이전트 인계 시 cold context 복원 단축
- audit trail 기계 가독 (PROV-O)
- 향후 RAG v2 의 retrieval 정확도 향상 (semantic + graph 결합)

### 왜 *지금* 만드는가
직전 1주일 동안 archive/ 마이그레이션 · persona v1.2 박제 · routing audit · MCP curation 등으로 `.agent/` 규모가 critical mass 통과 (122K → 30K 토큰 import chain 절감). 이제 관계 인덱스의 ROI 가 구축 비용 초과.

### 연구 근거
본 문서의 모든 P0 결정은 6 병렬 research agent 의 prior art 조사 (RESEARCH_v0.1.md) 로 정당화된다:
- W3C 표준 (PROV-O / SKOS / OWL 2 / RDF-star / SHACL / R2RML / RML)
- Palantir Foundry Ontology (Object Types / Link Types / Actions / Functions / Markings / Branching)
- KG 학술 (Hogan 2021 ACM Surv) + 비교 시스템 (Wikidata / DBpedia / Schema.org / YAGO / Cyc 실패 교훈)
- LLM Agent Memory (MemGPT / Letta / Mem0 / A-MEM / CoALA / Voyager / Generative Agents)
- Graph RAG (GraphRAG / LightRAG / HippoRAG / nano-graphrag)
- Ontology Engineering (METHONTOLOGY / NeOn / LOT / OntoClean / OOPS! / OpenTelemetry / SLSA / SPDX / CMDB)
- Store / Query Paradigm (Neo4j / DuckDB / Oxigraph / Cypher / SPARQL / SQL LLM 정확도 벤치마크)

---

## §2. Scope

### In-scope (v0.1)

| 영역 | 포함 |
|---|---|
| `.agent/` 자산 | knowledge/, personas/, contracts/, policies/, runbooks/ 의 파일 → Artifact |
| Fleet | `infra/agent-runtime/FLEET_STATUS.md` 의 디바이스 → Device |
| Service | quant-bot live, sora-live, neo_genesis_daemon, PM2 process → Service |
| Project | `Yesol-Pilot/*` 11 SBU + Neo Genesis 자체 + 2 NeurIPS 논문 → Project |
| Agent | Claude / Codex / Sora / Antigravity / Ollama / 32 persona spec → Agent |
| Skill | `~/.claude/agents/*.md` / `sora_engine.py` functions / persona dispatcher → Skill |
| Reflection | 주간 리뷰 / handoff 의 reflection entry → Reflection |
| Action audit | dispatcher routing, killswitch event, deploy event → ActionRun (prov:Activity) |
| Decision 박제 | active-tasks.md / handoff.md 의 owner G2 결정 → Artifact{kind:decision} |

### Out-of-scope (v0.1)

| 영역 | 이유 | 통합 시점 |
|---|---|---|
| RAG vector store | 별도 표현 모델 (embedding) | v0.4 (LightRAG dual-level) |
| Secret store (CREDENTIAL_BIBLE) | 보안 격리 — ontology 에 ID 만 reference | v0.3 |
| Quant 알파 객체 (A1~A6) | 도메인 특화 | v0.4 |
| Live `quant_*` Supabase 테이블 | external system, mirror 만 두기 | v0.3 |
| Personal / 법무 / 금융 자료 | CLAUDE.md §1.4 절대 금지 | **NEVER** |
| 2dlivegame, multiverse | 본 작업 단위 외 | TBD |

### Boundary 원칙
- 객체는 **자기 정의** 하나, **NOT 정의** 둘 (모호 명사 anti-pattern 방지).
- 한 객체가 두 카테고리에 동시 속하면 ontology 가 잘못된 것. 한 쪽 subtype 으로 분해.
- **Business value 정당화 의무** (Kitchen Sink anti-pattern 방어): 모든 속성 필드는 "왜 이게 필요한가" 한 줄 justification.

---

## §3. Object Model 완전판

**11 클래스** (v0.1-pre-research 의 9 + Skill + Reflection — CoALA 4-tier 의 procedural / episodic 파생 누락 보완).

공통 속성: `id`, `kind`, `created_at`, `updated_at`, `provenance`.

### 3.1 `Artifact`
파일·문서·코드·데이터셋·결정 등 **"내용물"**.

| 속성 | type | required | 정의 |
|---|---|---|---|
| `id` | URI | ✅ | `neo://artifact/<sha256_of_canonical_path>` (v0.1) → `neo://A<num>` opaque (v0.2~, F6) |
| `kind` | enum | ✅ | `knowledge / persona / policy / runbook / contract / decision / code / data / report / doc / log` |
| `path` | string | ✅ | repo-relative path 또는 `external://<source>/<id>` |
| `current_revision` | URI (Revision) | ✅ | 현재 head |
| `title` | string | ✅ | 사람 읽는 이름 |
| `label` | string | optional | mutable human-readable label (v0.2~, F6) |
| `aliases` | string[] | optional | 이름 변경 시 alias 누적 (v0.2~, F6) |
| `language` | enum | optional | `ko / en / code / yaml / json / mdx / ...` |
| `tags` | string[] | optional | SKOS concept refs (v0.3~) |
| `markings` | string[] | ✅ | **mandatory restrictive** (AND-logic). 모든 marking 충족해야 read. 예: `["confidential", "personal-forbidden"]`. (F3 — 직전 `sensitivity` enum 대체) |
| `allowedAgents` | URI[] | optional | **discretionary additive**. 기본 차단된 객체에 특정 에이전트만 허용. 예: `["neo://agent/claude-opus-4-7"]` |

**NOT 정의**:
- Artifact 는 **프로세스가 아니다** (Service 가 그것).
- Artifact 는 **사람/에이전트가 아니다** (Agent 가 그것).

**OntoClean 주석** (F2): Artifact 는 anti-rigid (~R) — "특정 revision 으로 본 파일" 은 rigid 지만 "이 파일" 자체는 status 가변. Revision 이 +R 부분 cover. v0.2 에서 `ImmutableArtifact` vs `MutableArtifactSlot` subtype 명시 검토.

### 3.2 `Revision`
Artifact 의 immutable 시점 스냅샷. **prov:Entity** 로 RDF type 박제.

| 속성 | type | required | 정의 |
|---|---|---|---|
| `id` | URI | ✅ | `neo://revision/<artifact_id_short>/<sha256_of_content>` |
| `rdf:type` | URI | ✅ | `prov:Entity` (PROV-O 정합) |
| `artifact` | URI (Artifact) | ✅ | parent |
| `content_hash` | sha256 | ✅ | bytes hash |
| `git_commit` | sha | optional | git-tracked 일 경우 |
| `prov:wasGeneratedBy` | URI (**ActionRun**) | optional | 생성 Activity (F1 — 직전 Agent/Service 매핑 PROV-O 위반 수정) |
| `prov:wasDerivedFrom` | URI[] (Revision) | optional | 파생 출처 |
| `slsa:level` | int (0~3) | optional | SLSA provenance grade (v0.3~) |
| `created_at` | ISO8601 | ✅ | |

**NOT 정의**: Revision 은 diff 가 아니다. 완전 스냅샷이다. diff 는 별도 도구.

### 3.3 `Project`
논리적 제품 라인.

| 속성 | type | required | 정의 |
|---|---|---|---|
| `id` | URI | ✅ | `neo://project/<slug>` |
| `kind` | enum | ✅ | `sbu / paper / infra / personal_career / org_root` |
| `repo` | string | optional | `Yesol-Pilot/<name>` |
| `domain` | string[] | optional | `kott.kr`, `toolpick.dev` 등 |
| `stage` | enum | optional | `idea / mvp / live / paused / archived` |

**NOT 정의**: Project 는 코드베이스 아니다. 코드는 Artifact{kind:code}.

### 3.4 `Service`
가동 중인 프로세스 또는 배포 단위.

| 속성 | type | required | 정의 |
|---|---|---|---|
| `id` | URI | ✅ | `neo://service/<device>/<name>` |
| `kind` | enum | ✅ | `pm2 / container / vercel_deploy / cron / systemd / cloudflare_worker` |
| `name` | string | ✅ | e.g. `quant-bot-live`, `sora-live`, `kott-frontend` |
| `current_artifact_revision` | URI (Revision) | optional | 실행 중 코드 버전 |
| `status` | enum | ✅ | `running / stopped / unknown / draining` |
| `last_observed_at` | ISO8601 | ✅ | |
| `host_device` | URI (Device) | ✅ | |
| `otel:resource` | object | optional | OpenTelemetry Resource attributes (`service.name`, `service.namespace`, `deployment.environment`, v0.3~) |

**NOT 정의**: Service 는 코드 아니다. 코드의 *실행 인스턴스*다.

**OntoClean 주석** (F2): Service 는 anti-rigid (~R) — status 가변. v0.2 에서 `ServiceDefinition` (+R) vs `ServiceInstance` (~R) subtype 분리 검토.

### 3.5 `Device`
물리/가상 머신.

| 속성 | type | required | 정의 |
|---|---|---|---|
| `id` | URI | ✅ | `neo://device/<hostname>` |
| `hostname` | string | ✅ | |
| `kind` | enum | ✅ | `pc_desktop / pc_laptop / server / mobile / cloud_vm` |
| `online` | bool | ✅ | latest heartbeat 기준 |
| `last_heartbeat_at` | ISO8601 | ✅ | |
| `tailscale_ip` | string | optional | |

### 3.6 `Agent`
AI 에이전트 또는 persona 스펙. **prov:Agent** 로 RDF type 박제.

| 속성 | type | required | 정의 |
|---|---|---|---|
| `id` | URI | ✅ | **유일한 identity criterion** (F2 — Agent 의 -I 위험 해소). v0.1: `neo://agent/<slug>`. v0.2~: `neo://A<num>` opaque. |
| `rdf:type` | URI | ✅ | `prov:Agent` |
| `agent_kind` | enum | ✅ | `model_instance / persona_spec / human` |
| `label` | string | ✅ | mutable human-readable label |
| `aliases` | string[] | optional | rename 시 누적 |
| `model` | string | optional | `claude-opus-4-7`, `gpt-5-codex`, `qwen2.5-coder:14b` (변경 가능 속성, identity 아님) |
| `tier` | enum | optional | `S / A / B / C` (persona only) |
| `frontmatter_revision` | URI (Revision) | optional | persona 스펙 시 |

**Identity 규칙** (F2 박제): id 만이 identity criterion. model/tier/label 변경은 새 Agent 가 아님 — alias 추가로 처리.

**NOT 정의**: Agent 는 실행 process 아니다. process 는 Service.

### 3.7 `Task`
작업 단위.

| 속성 | type | required | 정의 |
|---|---|---|---|
| `id` | URI | ✅ | `neo://task/<slug_or_ulid>` |
| `title` | string | ✅ | |
| `status` | enum | ✅ | `pending / in_progress / blocked / done / cancelled` |
| `priority` | enum | ✅ | `P0 / P1 / P2 / P3` |
| `created_at` | ISO8601 | ✅ | |
| `due_at` | ISO8601 | optional | |
| `source_artifact` | URI (Artifact) | optional | active-tasks.md 의 entry 등 |

**OntoClean 주석** (F2): Task 는 anti-rigid + identity carrier 미정. v0.2 에서 Task = template(+R), 재실행 = 신규 ActionRun 으로 분해 검토.

### 3.8 `Policy`
규칙·게이트·임계값·deny-list. **+R rigid**.

| 속성 | type | required | 정의 |
|---|---|---|---|
| `id` | URI | ✅ | `neo://policy/<slug>` |
| `kind` | enum | ✅ | `deny_list / threshold / gate / governance / safety / mcp_curation` |
| `enforcement` | enum | ✅ | `hard_block / soft_warn / log_only` |
| `source_artifact` | URI (Artifact) | ✅ | 정책 본문이 있는 SSOT |
| `owl:versionInfo` | string | ✅ | semver 버전 (v0.3~) |

### 3.9 `ActionRun` ⭐ (F1 + F5 — 가장 큰 변경)
실행된 액션의 atomic transaction. **prov:Activity** 로 RDF type 박제.

| 속성 | type | required | 정의 |
|---|---|---|---|
| `id` | URI | ✅ | `neo://action_run/<ulid>` |
| `rdf:type` | URI | ✅ | `prov:Activity` (F1 — PROV-O 정합) |
| `kind` | enum | ✅ | `dispatcher_route / killswitch_fire / deploy / commit / mcp_tool_call / persona_invocation / external_api_call / ontology_mutation` |
| `triggered_by` | URI (Agent) | ✅ | (= `prov:wasAssociatedWith` Agent) |
| `affectedObjects` | URI[] | ✅ | **transaction 이 변경한 객체들** (F5 — Foundry Action Type pattern) |
| `status` | enum | ✅ | `pending / committed / failed` (F5 — transaction lifecycle, `result` 와 별도) |
| `sideEffects` | object[] | optional | webhook 호출 / 알림 / 후속 스케줄 (F5) |
| `policy_decisions` | URI[] (Policy) | optional | allow/deny 출처 |
| `result` | enum | ✅ | `success / failure / partial / blocked` |
| `confidence` | float | optional | 0.0~1.0 (Cyc anti-pattern #3 해소 — deterministic-only reasoning) |
| `trace_id` | string | optional | OpenTelemetry trace_id (v0.3~) |
| `span_id` | string | optional | OpenTelemetry span_id (v0.3~) |
| `started_at` | ISO8601 | ✅ | |
| `finished_at` | ISO8601 | optional | |

**Transaction 규칙** (F5 박제):
ontology write 시 강제 순서:
1. ActionRun pending 박제
2. affectedObjects 의 모든 객체 update
3. ActionRun committed 박제 (성공) 또는 failed 박제 (실패)

실패 시 file-based 환경에서 rollback 은 best-effort, but audit trail 은 보존.

### 3.10 `Skill` ⭐ (F8 신규)
Voyager pattern — 재사용 가능한 검증된 function / subagent.

| 속성 | type | required | 정의 |
|---|---|---|---|
| `id` | URI | ✅ | `neo://skill/<slug>` |
| `kind` | enum | ✅ | `subagent_spec / function / persona_instance / pipeline_step` |
| `source_artifact` | URI (Artifact) | ✅ | 코드/스펙 본문 |
| `success_rate` | float | optional | 검증 게이트 통과율 (0.0~1.0) |
| `last_used_at` | ISO8601 | optional | |
| `composed_of` | URI[] (Skill) | optional | 재사용 sub-skill |

**Source mapping**:
- `~/.claude/agents/*.md` → Skill{kind:subagent_spec}
- `sora_engine.py` functions → Skill{kind:function}
- `scripts/persona/dispatcher.py` 의 페르소나 routing → Skill{kind:persona_instance}

**검증 게이트** (Voyager pattern): 신규 Skill 은 test PASS + dry-run validation 통과 후만 commit.

### 3.11 `Reflection` ⭐ (F8 신규)
Generative Agents pattern — 여러 episodic 기억에서 추출한 고차원 insight.

| 속성 | type | required | 정의 |
|---|---|---|---|
| `id` | URI | ✅ | `neo://reflection/<ulid>` |
| `trigger` | enum | ✅ | `scheduled / importance_threshold / manual` |
| `reflects_on` | URI[] | ✅ | Task / Decision / Artifact (참조한 episodic 기억) |
| `insight_text` | string | ✅ | reflection 본문 |
| `generated_at` | ISO8601 | ✅ | |
| `generated_by` | URI (Agent) | ✅ | |

**Source mapping**:
- 주간 리뷰 (Strategy Lead) → Reflection{trigger:scheduled}
- handoff.md 의 "다음 세션 우선순위" → Reflection{trigger:importance_threshold}

---

## §4. Relation Model 완전판

**17 관계** (v0.1-pre-research 의 15 + `prov:wasAssociatedWith` + `composed_of` + `reflects_on` — 신규 클래스 2개 대응). 각 관계는 `domain`, `range`, `cardinality`, `inverse`, `transitivity` 명시.

| # | 관계 | domain → range | cardinality | inverse | transitive |
|---|---|---|---|---|---|
| 1 | `current_revision` | Artifact → Revision | 1:1 | `is_current_of` | - |
| 2 | `prov:wasGeneratedBy` | Revision → **ActionRun** (F1 수정) | n:1 | `generated` | - |
| 3 | `prov:wasAssociatedWith` ⭐ | ActionRun → Agent | n:m | `participated_in` | - |
| 4 | `prov:wasDerivedFrom` | Revision → Revision | n:m | `derived_into` | ✅ |
| 5 | `supersedes` | Revision → Revision | n:1 | `superseded_by` | ✅ |
| 6 | `owned_by` | Artifact/Service/Task → Project | n:1 | `owns` | - |
| 7 | `deployed_to` | Service → Device | n:1 | `hosts` | - |
| 8 | `depends_on` | Service → Service / Artifact → Artifact | n:m | `depended_on_by` | ✅ |
| 9 | `governs` | Policy → Artifact/Service/Agent | n:m | `governed_by` | - |
| 10 | `allowed_by` | ActionRun → Policy | n:m | `allows` | - |
| 11 | `denied_by` | ActionRun → Policy | n:m | `denies` | - |
| 12 | `affects` | ActionRun → Service/Artifact | n:m | `affected_by` | - |
| 13 | `assigned_to` | Task → Agent | n:1 | `assigned_tasks` | - |
| 14 | `blocks` | Task → Task | n:m | `blocked_by` | ✅ |
| 15 | `references` | Artifact → Artifact | n:m | `referenced_by` | - |
| 16 | `instantiates` | Agent{model_instance} → Agent{persona_spec} | n:1 | `instantiated_as` | - |
| 17 | `composed_of` ⭐ | Skill → Skill | n:m | `composes` | ✅ |
| 18 | `reflects_on` ⭐ | Reflection → Task/Decision/Artifact | n:m | `reflected_by` | - |

**Link Properties block** (F4 — Foundry pattern):
모든 관계는 optional `linkProperties: {}` block 허용. 예:

```yaml
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

**Notes**:
- `prov:*` prefixed 는 PROV-O 정합.
- transitive 관계는 query 시 closure 계산 필요. v0.1 에서는 explicit edges 만 박제, closure 는 reader 가 계산. v0.5 OWL EL profile 활성 시 reasoner 가 closure 자동 추론.
- 모든 edge 는 `observed_at` (ISO8601) 속성을 가짐 — staleness 검출용.

---

## §5. Identity / URI 스킴 (F6 갱신)

### 5.1 v0.1 — Path-based (compat)
```
neo://<kind>/<segment>(/<sub_segment>)*
```

| 객체 | 패턴 | 예 |
|---|---|---|
| Artifact | `neo://artifact/<sha256_of_canonical_path>` | `neo://artifact/8f3a...` |
| Project | `neo://project/<slug>` | `neo://project/kott` |
| Agent | `neo://agent/<slug>` | `neo://agent/senior-da-pm-korean` |
| ... | ... | ... |

### 5.2 v0.2~ — Opaque IRI (F6 권고)
KG agent §5 발견 2 — Wikidata Q-ID 패턴:

| 객체 | Primary ID (immutable) | Label (mutable) |
|---|---|---|
| Artifact | `neo://A001` | `label: "active-tasks.md"` |
| Project | `neo://P042` | `label: "toolpick"` |
| Agent | `neo://G003` | `label: "senior-da-pm-korean"` |
| Service | `neo://S015` | `label: "quant-bot-live"` |
| Device | `neo://D002` | `label: "ysh-server"` |
| Task | `neo://T<ulid>` | `label: "v0.2 extraction"` |
| Policy | `neo://Pol007` | `label: "mcp_curation_v1"` |
| ActionRun | `neo://AR<ulid>` | - |
| Skill | `neo://Sk012` | `label: "claude-code-guide subagent"` |
| Reflection | `neo://Rf<ulid>` | - |
| Revision | `neo://Rv<short>/<sha>` | - |

### 5.3 원칙
- ID 는 **stable**. 이름 변경 시 새 ID 가 아니라 alias 추가.
- ID 충돌 감지: 빌드 시 unique constraint 검증.
- 외부 식별자 (git sha, docker digest, supabase row id) 는 별도 속성으로 가지되 primary ID 는 아님.
- v0.1 path-based ID 는 v0.5 까지 alias 로 보존 (backward compat).

---

## §6. Source Mapping

기존 자산 → 객체 매핑. v0.2 의 추출 스크립트가 이 표를 따른다.

| 자산 | 객체 | 추출 방법 |
|---|---|---|
| `.agent/knowledge/*.md` | Artifact{kind:knowledge} | walk + frontmatter parse |
| `.agent/personas/tier-*/*.md` | Artifact{kind:persona} + Agent{agent_kind:persona_spec} | walk + frontmatter |
| `.agent/policies/*.yaml` | Artifact{kind:policy} + Policy | walk + yaml parse |
| `.agent/runbooks/*.md` | Artifact{kind:runbook} | walk |
| `.agent/contracts/*.md` | Artifact{kind:contract} | walk |
| `.agent/shared-brain/active-tasks.md` | Artifact + 다수 Task 추출 | markdown checkbox parse |
| `.agent/shared-brain/handoff.md` | Artifact{kind:report} + 다수 Decision 추출 + Reflection (주간 리뷰) | section parse |
| `.agent/shared-brain/status.json` | Service status snapshots + Device heartbeats | json parse |
| `infra/agent-runtime/FLEET_STATUS.md` | 다수 Device | parse |
| `infra/agent-runtime/<host>/Modelfile` | Agent{agent_kind:model_instance} | parse |
| `~/.claude/agents/*.md` | Agent + Skill{kind:subagent_spec} | walk |
| `scripts/persona/dispatcher.py` 페르소나 routing | Skill{kind:persona_instance} | code AST parse |
| `sora_engine.py` 의 function 모음 | Skill{kind:function} | code AST parse |
| `Yesol-Pilot/<repo>` | Project{kind:sbu} | git remote enumeration |
| quant-bot PM2 list | Service + ActionRun (start/stop events) | `pm2 jlist` |
| Supabase `quant_*` tables | external mirror (out-of-scope v0.1) | - |
| `CREDENTIAL_BIBLE.md` | Policy{kind:safety}, secret 본문은 in-scope 아님 | parse |
| `~/.claude/settings.json` deny list | Policy{kind:deny_list, enforcement:hard_block} | json parse |
| `MEMORY.md` (auto-memory) | Artifact{kind:knowledge, markings:[internal]} | walk |

추출 스크립트는 v0.2 에서 박제: `scripts/ontology/extract_*.py`.

---

## §7. External Standards Integration (Research-grounded)

RESEARCH_v0.1 §3 + §5 의 채택 매트릭스 박제:

| 표준 | v0.1 채택 | 다음 단계 | 근거 |
|---|---|---|---|
| **PROV-O** | ✅ **즉시** (Activity 클래스 정합 필수) | v0.2: Qualified Patterns | F1 — `wasGeneratedBy` range 정합 |
| **SKOS** | ❌ 거부 (v0.3 평가) | v0.3 — 다국어 / 분류 확장 시 | enum 4개에 SKOS Scheme 과잉 |
| **OWL 2** | ❌ 거부 (v0.5 EL 한정) | v0.5 EL profile transitive | reasoner cold-start 비용 |
| **RDF-star** | ❌ 거부 (v0.5 조건부) | RDF 1.2 final Rec 안정화 후 | Candidate Recommendation 미확정 |
| **SHACL** | ❌ 거부 (v0.3) | Store 가 Neo4j / Triple Store 일 때 | SPARQL endpoint 부재 |
| **R2RML** | ❌ **영구 거부** | NEVER | Core SQL 2008 전용 |
| **RML** | ❌ 거부 (v0.3 평가) | YAML 지원 확장 후 | Unofficial Draft |
| **OpenTelemetry semantic conventions** | optional (v0.1) | v0.3 full | Service annotation `service.name` 등 |
| **SLSA provenance levels** | ❌ (v0.3) | v0.3 — Revision `slsa:level` | 4-level grade |
| **SPDX relationship vocabulary** | ❌ (v0.3) | v0.3 — Artifact 간 의존 어휘 | DEPENDS_ON / CONTAINS / BUILD_TOOL_OF |
| **CMDB / ITIL CI predicate** | optional (v0.1 label) | v0.3 — 핵심 관계 predicate label 병기 | 외부 federation 가능성 |

### PROV-O Qualified Patterns (v0.2 권고)
- `prov:Generation` reification — Revision 생성 시 timestamp / model / temperature 부착
- `prov:qualifiedDelegation` — `Claude → Codex` delegation 시 누가 언제 누구에게 위임
- `prov:wasAssociatedWith` (이미 v0.1 박제 — §4 #3) — ActionRun → Agent association role

---

## §8. Memory MCP 와의 경계 (D1 결정 유지)

**결정**: **옵션 A — 파일 원본, MCP 캐시** (Strategy Lead 자율 결정, owner 한 줄 reversible).

### 근거 (5건)
1. `.agent/` 패턴 일관성 — 모든 다른 SSOT 가 파일 기반
2. git-trackable — audit log 자동
3. MCP server 재기동/disconnect 견딤 — file 은 항상 존재
4. multi-agent 호환 — Codex / Sora / Ollama 도 파일 읽음, memory MCP 는 Claude 전용
5. frontmatter / yaml 의 rich metadata — memory MCP entities 보다 표현력 좋음

### 구현 합의
- **원본**: `.agent/ontology/nodes.jsonl`, `.agent/ontology/edges.jsonl`
- **v0.1 store upgrade**: DuckDB embedded — `pip install duckdb` + `SELECT * FROM read_ndjson_auto('nodes.jsonl')` (F9, §14 Roadmap 참조)
- **캐시**: 첫 ontology 활용 코드 path 에서 `mcp__memory__create_entities` / `create_relations` 로 매 세션 시작 시 rehydrate (선택적)
- **write 는 파일에만**. memory MCP 에 직접 쓰는 코드 금지. (소프트 규칙)

---

## §9. Action Layer 설계 (OAG governed execution, F5 + Foundry agent §6)

v0.1 에서는 **hook point 만** 박제. v0.3 부터 governed execution scaffolding (Foundry AIP Logic pattern).

### 9.1 hook points (v0.1)

| Action 종류 | trigger | enforce 시점 |
|---|---|---|
| `record_action` | dispatcher / killswitch / deploy 가 발생 → ActionRun 자동 박제 | v0.3 |
| `impact_query` | "이 Artifact 고치면 어디 영향?" 질의 → graph traversal (`affects` reverse closure) | v0.2 |
| `staleness_check` | `last_observed_at` 가 threshold 초과 → Policy{kind:threshold} 위반 | v0.3 |
| `policy_gate` | Action 실행 전 Policy{governs} 평가 → allow/deny | v0.4 (위험, 신중) |

### 9.2 OAG Governed Execution Pattern (v0.3 박제 권고)

Palantir AIP 의 원칙 (RESEARCH §6):
> "LLMs do not have direct access to tools; LLMs can only ask to use tools, and these tool calls are then executed within the invoking user's permissions."

**우리 적용**:
- 에이전트는 ontology 직접 편집 금지
- `scripts/ontology/query.py --object-set active-agents --agent claude-code` (Data Tool 등가, markings 검사)
- `scripts/ontology/mutate.py --action update-task-status --params '{...}'` (Action Tool 등가, transaction 박제)
- 두 스크립트를 MCP tool 로 노출 (v0.3)

### 9.3 원칙
- ontology 가 자동 액션 트리거 하면 안 됨 (Action Sprawl). human-in-the-loop 또는 별도 orchestrator.
- v0.4 의 `policy_gate` 는 owner G2 결정 후 라이브.

---

## §10. Security / Audit / Provenance (F3 + F7 강화)

### 10.1 Markings (F3 — 직전 sensitivity enum 대체)
- `markings: string[]` (mandatory restrictive, AND-logic)
- `allowedAgents: URI[]` (discretionary additive)
- Marking 예시: `confidential`, `personal-forbidden`, `internal`, `public`
- 모든 marking 충족 + allowedAgents 빈 배열이 아니면 read 허용

### 10.2 Personal 절대 금지
- `personal/` 디렉토리 (법무·금융·개인회생) 는 ontology 에 **단 한 줄도 들어가지 않는다**. extract 스크립트의 skip-list 에 hardcode.
- 만약 ontology 노출 시 자동 markings=[`personal-forbidden`] + allowedAgents=[] (즉 0 agent 접근).

### 10.3 Multi-Agent Write — Single Writer + Queue (F7)
- v0.2 부터 Supabase `agent_write_queue` 테이블
- daemon poll 10초 interval, 순서 merge + git commit
- 에이전트는 `propose_write(target, diff)` API 만 호출
- 충돌 시 fail-fast — owner 수동 해소
- Audit trail = git log

### 10.4 Read 권한
- `markings` 또는 `allowedAgents` 위반 시 ontology 본문 반환 거부
- 메타데이터 (path, hash, kind) 만 노출 가능

### 10.5 Write 권한
- ontology nodes/edges 작성은 `scripts/ontology/*.py` (transaction 박제) 만
- 작성 시마다 ssotRevision bump 트리거 (`sync_agent_context.py`)

### 10.6 Audit
- 모든 추출 / 변환 / 박제 작업은 ActionRun 으로 자기-기록
- ssotRevision 변경에 `changed_by` / `reason` / `evidence_url` 의무화 (Cyc 의 Validation Isolation 회피)

### 10.7 Redaction
- secret pattern (Anthropic / OpenAI / Google / GitHub / JWT / AWS / Telegram bot token) 추출 시 자동 redact
- `tools/ontology_redact.py` 박제 (v0.2)

---

## §11. Anti-patterns (Palantir + Cyc 정합)

명시적으로 회피하는 **10가지** (v0.1-pre-research 7개 + Foundry/Cyc cross-check 추가 3개):

### 직전 박제 7
1. **God Object** — `Everything` 클래스 금지. Decision = Artifact subtype.
2. **Action Sprawl** — ontology 가 직접 액션 실행 금지 (§9 참조).
3. **System-Specific Duplication** — quant-bot, kott, toolpick 각각 별도 "Project" 만들지 않음.
4. **Ambiguous Names** — `Item`, `Thing`, `Entity` 같은 모호 명사 금지.
5. **Premature Reasoning** — OWL reasoning 을 v0.5 전 활성화하지 않음.
6. **SSOT Drift** — ontology 가 SSOT 와 모순될 경우 SSOT 항상 우선 (§1 참조).
7. **Schema-First Trap** — 스키마를 먼저 완벽하게 짜지 않음. competency questions 먼저 (§12).

### Research 추가 3 (F2 + Cyc 1, 2)
8. **Kitchen Sink** (Foundry) — 비즈니스 가치 없는 기술적 컬럼 금지. 모든 속성에 justification 의무.
9. **Knowledge Acquisition Bottleneck** (Cyc) — 수작업 ontology 박제 confined. extract 자동화 + archive TTL 의무.
10. **Microtheory Fragmentation** (Cyc) — 다중 에이전트 동시 write 시 namespace 분리 + single writer queue (F7).

### Foundry anti-pattern Golden Hammer 해소 (RESEARCH §6)
Action Type as atomic transaction 도입 (F5) 으로 단일 도구(스크립트) 의 모든 mutation 처리 패턴 해소.

---

## §12. Competency Questions (20)

ontology v0.1 이 답해야 하는 질문들. 못 답하면 schema 부족 = 작업 미완. 각 질문은 v0.2 에서 `tests/ontology/competency_q*.py` 로 박제. **20/20 PASS 가 v0.2 acceptance gate.**

### Artifact / Provenance
1. `.agent/knowledge/foo.md` 의 현재 revision 의 sha256 은?
2. 이 Artifact 의 최신 작성자 (Agent) 는? (via ActionRun)
3. 이 Artifact 가 derive 한 출처 Artifact 들은?
4. 지난 7일간 변경된 Artifact 목록은?
5. markings 에 `confidential` 포함된 Artifact 목록은?

### Service / Device
6. quant-bot-live 가 가동 중인 Device 는?
7. ysh-server 에 떠 있는 모든 Service 는?
8. 지난 24시간 heartbeat 없는 Device 는?
9. sora-live 가 의존하는 다른 Service 들은?
10. 한 Service 가 stop 되면 영향받는 다른 Service 들은? (transitive `depends_on`)

### Agent / Task / Skill / Policy
11. `senior-da-pm-korean` persona 의 frontmatter 의 현재 revision 은?
12. P0 status=`in_progress` 인 Task 목록은?
13. owner 결정 (Decision Artifact) 중 최근 7일치는?
14. MCP curation policy 가 governs 하는 Service 목록은?
15. Killswitch 가 fire 됐을 때 affects 된 Artifact 들은?

### Audit / Impact / Reflection
16. 어떤 ActionRun 이 이 Artifact 의 마지막 revision 을 생성했나?
17. 한 Artifact 를 수정하면 references 로 영향받는 다른 Artifact 들은?
18. 지난 24시간 `denied_by` Policy 가 발생한 ActionRun 들은?
19. 한 Project 의 모든 (Service + Artifact + Task + Skill) 를 한 번에 조회 가능한가?
20. archive 됐던 Artifact 가 `referenced_by` 활성 Artifact 에 의해 참조되고 있나? (orphan / dangling 검출)

---

## §13. Quality Gates

| Gate | 적용 시점 | 도구 |
|---|---|---|
| JSON Schema strict | extract 시 매번 | `jsonschema` lib + custom unique-id check |
| Edge integrity | extract 시 | edge 의 domain/range 가 실존 node 인지 |
| URI uniqueness | extract 시 | `neo://...` ID 충돌 0건 |
| **OntoClean metaproperty 검증** | v0.2 진입 전 | 9 클래스 rigidity/identity/unity 표 박제 |
| **OOPS! pitfall scan** | RFC 머지 전 | http://oops.linkeddata.es/ — Critical 0건, Important ≤2건 |
| Competency Q PASS | v0.2 release | 20/20 통과 |
| Regression | weekly | snapshot diff + 의도 외 drift detect |
| Redaction | extract 시 | secret pattern 0건 노출 |
| ssotRevision bump | write 시 매번 | `sync_agent_context.py` |
| **markings 무결성** | extract 시 | personal_forbidden 객체 ontology 미들어가는지 |

---

## §14. Roadmap (Store + RAG + Standards 통합, F9 박제)

| Version | 작업 | Store | Query | 외부 표준 통합 | 완료 기준 |
|---|---|---|---|---|---|
| **v0.1** (이 문서) | contract + research 박제 | JSONL → **DuckDB** | SQL (with JSON ops + CTE) | PROV-O (Activity 정합 F1), OpenTelemetry annotation optional | DESIGN + RESEARCH 박제 + owner ACK |
| **v0.2** | PoC 추출 — 50 node / 100 edge + OntoClean 교정 + Skill/Reflection 신설 + Single Writer Queue | DuckDB | SQL + recursive CTE | PROV-O Qualified Patterns | 20 competency Q PASS / OntoClean Critical 0건 |
| **v0.3** | ActionRun 자동 박제 + nano-graphrag PoC + OAG governed execution + SHACL/SKOS/RML 평가 | DuckDB + Supabase queue | SQL | SHACL (Triple Store 도입 시), SKOS Scheme, SPDX relationship type, SLSA level | Korean KG triple 추출기 + 7일 audit 수집 |
| **v0.4** | **Neo4j 이전** + LightRAG dual-level + RAG 통합 + KURE-v1 한국어 결합 + Quant 알파 객체 도입 | **Neo4j Community 5.x** | **Cypher** (CypherBench EX 61.58%) | OpenTelemetry full annotation, n10s 준비 | retrieval 정확도 +10%↑ |
| **v0.5** | HippoRAG PPR + OWL EL transitive 추론 + RDF-star (안정화 시) + ImmutableArtifact/MutableArtifactSlot subtype | Neo4j | Cypher + OWL EL reasoner (cond.) | OWL EL transitive, RDF-star (cond.) | multi-hop query 라이브 |
| **v1.0** | n10s RDF export + Oxigraph SPARQL endpoint + DOLCE-Lite alignment 평가 + SPARQL federation 1건 | Neo4j + Oxigraph | Cypher primary + SPARQL export only | Full PROV-O / SKOS / OWL 2 EL / SHACL / SPDX / CMDB / OpenTelemetry / SLSA | 외부 federation 1건 + Palantir Foundry-class 핵심 query cover |

**v0.1 → v0.2 promotion gate**: owner ACK (DESIGN + RESEARCH + Rejected alternatives §15)

---

## §15. Rejected Alternatives (Strategy Lead 자율 결정 박제, F-detail RESEARCH §12)

| 거부 항목 | 거부 단계 | 거부 근거 | reversible? |
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
| GraphRAG (Microsoft, Leiden community detection) | v0.4 | 수백만 토큰 전제 — 우리 규모 과도. LightRAG fit | yes (규모 확장 시) |
| TigerGraph / JanusGraph / Amazon Neptune | v1.0 까지 | distributed 인프라 부담 — Neo4j Community 로 충분 | yes |
| Foundational ontology (DOLCE / BFO / SUMO) align | v1.0 까지 | 1인 팀 overhead 과대. v1.0 DOLCE-Lite 선택적 평가 | yes |

---

## Appendix A. 한 줄 결정 매트릭스 (Strategy Lead 자율 G1)

| ID | 결정 | 권고 | reversible? | 근거 |
|---|---|---|---|---|
| G1-1 | Memory MCP 경계 | 옵션 A (파일 원본 + MCP 캐시) | yes | §8 |
| G1-2 | SBU 별도 클래스 vs Project subtype | Project subtype | yes | §3.3, OntoClean +R |
| G1-3 | OWL reasoning 활성 시점 | **v0.5 EL profile** (직전 v1.0 → 갱신) | yes | RESEARCH §3 F-A4 |
| G1-4 | Action 자동 실행 시점 | v0.3 scaffolding + v0.4 owner G2 (직전 v0.4 만 → 갱신) | yes | RESEARCH §6 OAG |
| G1-5 | personal/ in-scope | NEVER | yes (but won't) | §10.2 |
| G1-6 | 객체 클래스 수 | **11 (직전 9 → Skill + Reflection 신설)** | yes | F8, RESEARCH §8 |
| G1-7 | Decision 별도 클래스 vs Artifact subtype | Artifact subtype | yes | God Object 회피 |
| G1-8 ⭐ | Store paradigm 단계 | **v0.1 DuckDB → v0.4 Neo4j → v1.0 +n10s (RDF export)**. Full Triple Store 거부 | yes | F9, RESEARCH §10 |
| G1-9 ⭐ | Methodology | LOT primary + OntoClean Tier S 검증 + NeOn Scenario 1+4 | yes | RESEARCH §9 |
| G1-10 ⭐ | Multi-agent write conflict | Single Writer + Queue (Supabase) — CRDT 거부 | yes | F7, RESEARCH §8 |
| G1-11 ⭐ | sensitivity → markings 전환 | F3 — `markings[]` + `allowedAgents[]` (직전 단일 enum → 갱신) | yes | Foundry Mandatory + Discretionary |
| G1-12 ⭐ | PROV-O Activity 매핑 | F1 — ActionRun = `prov:Activity`, Revision → ActionRun → Agent (직전 Revision → Agent → 갱신) | yes | W3C PROV-O spec |
| G1-13 ⭐ | Opaque IRI 전환 | F6 — v0.2 부터 `neo://A001` opaque, path-based 는 v0.5 까지 alias | yes | Wikidata Q-ID pattern |

owner 가 한 줄로 ("G1-8 옵션 B 로 바꿔") 어느 결정이든 뒤집을 수 있다.

---

## Appendix B. G1 박제 (2026-05-14 추가, 직전 G2 8건을 자율 결정으로 전환)

owner 지적 (2026-05-14): "너가 책임지고 직접 판단해 — 의견 묻는 이유는 제대로 파악 못함". 직전 G2 8건 모두 자본 위험 0 / personal 0 / 영구 비가역 0 — G1 자율 박제 범위. 다음과 같이 박제하고 실행한다.

| ID | 결정 | 박제 근거 | reversible? |
|---|---|---|---|
| G1-14 | v0.1 (DESIGN + RESEARCH) 자체 ACK — v0.2 즉시 진행 | 6 research agent prior art 정합 검증 완료 | yes (git revert + ssotRevision rollback) |
| G1-15 | extract 스크립트 G1 자율 진행 | 자본 위험 0, 라이브 인프라 미접촉 | yes |
| G1-16 | 라이브 후 monitoring 빈도 = 일일 status + 주간 reflection | Generative Agents pattern + Strategy Lead 주간 리뷰 정합 | yes |
| G1-17 | competency Q 20개 §12 final 확정 | v0.3 에서 RAG 통합 후 +5개 추가 가능 (extend 가능, breaking 아님) | yes |
| G1-18 | DuckDB 마이그레이션 G1 자율 진행 | 마이그레이션 비용 0 (`pip install duckdb`), JSONL 직독, 원본 보존 | yes |
| G1-19 | v0.2 write queue = **파일 기반** (`.agent/ontology/write_queue/*.json`), Supabase agent_write_queue 는 v0.3 평가 | Supabase 신규 테이블 = 외부 자산 변경. v0.2 PoC 단계엔 파일 queue 로 충분. v0.3 라이브 traffic 후 Supabase 평가 | yes |
| G1-20 | Skill / Reflection 클래스 §3.10 / §3.11 박제 | F8 root cause = CoALA procedural / episodic 파생 누락 | yes |
| G1-21 | OntoClean Tier S 검증 v0.2 진입 전 의무화 | Methodology agent F2 — 4 클래스 위험 식별 후 진행해야 v0.3 에서 schema 재작성 회피 | yes |

**G2 잔존 = 0건.** 모든 결정은 박제됨. owner 가 한 줄로 ("G1-19 supabase 로 가" 같은) reverse 가능.

---

## Appendix C. 변경 이력

| 일자 | 버전 | 작성자 | 변경 |
|---|---|---|---|
| 2026-05-14 | v0.1 DRAFT (pre-research) | Strategy Lead Claude Opus 4.7 | 최초 박제 (D1=옵션A, 14 섹션 full) |
| 2026-05-14 | v0.1 DRAFT (post-research) | Strategy Lead Claude Opus 4.7 | 6 병렬 research agent 결과 반영: F1~F10 적용, 클래스 9→11, 관계 15→17, store paradigm 박제, anti-pattern 7→10, Rejected alternatives 신설, G1 7→13 |
| 2026-05-14 | **v0.2 라이브** | Strategy Lead Claude Opus 4.7 | G1 14건 추가 박제 (Appendix B), full extraction 325 nodes / 161 edges (11/11 classes), validate.py + validate_competency.py + write_queue.py 라이브, **competency Q 20/20 PASS**, OntoClean subtype evaluation (4 클래스 단일 유지 + doc 박제), ssotRevision `06840d30fc676bdf` propagate |
| 2026-05-14 | **v0.3 OAG governed execution 라이브** | Strategy Lead Claude Opus 4.7 | OAG read/write API 완성: `scripts/ontology/query.py` (Object Set + impact + staleness + markings enforcement), `mutate.py` (add_task / modify_status / add_edge + diff_file), `write_queue.py` 실 mutation apply 패치 (consume → nodes/edges 갱신 + ActionRun 자동 박제). `object_sets.yaml` 10 named queries 박제. E2E smoke test: Task 30→31 + ActionRun 1→3 + status 변경 + validate 6/6 P0 PASS + competency 20/20 PASS 유지. dispatcher `matched_layer` payload patch 는 5/12 hook 박제로 이미 완료 확인. |
| 2026-05-14 | **v0.3 auto_record + standards eval closure** | Strategy Lead Claude Opus 4.7 | `scripts/ontology/auto_record.py` (fast-path ActionRun append, file-locked, idempotent SHA ID, write_queue 우회) 박제. `scripts/persona/dispatcher.py` 통합 — `--query` 호출마다 ActionRun{kind:dispatcher_route, prov:Activity} 자동 박제 (best-effort, dispatcher 결과에 영향 없음). E2E: dispatcher 2회 → 2건 박제 ✅, validate 6/6 P0 PASS / competency 20/20 PASS 회귀 PASS. ActionRun kind 3종 라이브 (dispatcher_route:2, ontology_mutation:2, extract:1). `external_standards_eval_v0.3.md` 박제 — SHACL/SKOS/RML 모두 DEFER + trigger 조건 명시 (G1-22/23/24). |
| 2026-05-14 | **v0.3 final closure (hooks + nano-graphrag + MCP)** | Strategy Lead Claude Opus 4.7 | (1) **Event hooks** (`scripts/ontology/hooks/`): `killswitch_hook.py` (kind:killswitch_fire) + `deploy_hook.py` (kind:deploy) + README (PM2/Vercel/GitHub Actions wiring 가이드). (2) **nano-graphrag PoC** (`scripts/ontology/graphrag.py`): NetworkX Louvain community detection + 한국어 cluster summary, `communities.json` 박제. Top cluster: c000 (59 nodes, persona+knowledge+policy Artifact 통합), c001 (33 nodes, Revision provenance chain), c002 (17 nodes, Service deploy/depend/governs cluster). Korean query 검증 ("toolpick"→c080, "persona"→c012+c000). (3) **MCP server** (`scripts/ontology/mcp_server.py`): FastMCP 기반 13 tools (read 6 + write 4 + stats 3) 박제 — Claude/Codex/Sora 가 native MCP protocol 로 ontology 호출 가능 (Bash subprocess wrapping). 회귀: 6/6 P0 + 20/20 competency PASS, ActionRun kind 6종 라이브 (dispatcher_route:2, ontology_mutation:2, extract:1, deploy:1, heartbeat:1, killswitch_fire:1). |
| 2026-05-14 | **v0.4 진입 5건 라이브** | Strategy Lead Claude Opus 4.7 | (1) **HippoRAG PPR** (`graphrag.py --hipporag`): NetworkX `pagerank()` personalization 기반 multi-hop reasoning. seed=sora-live → top 8 PPR (ysh-server 0.106 / neo_genesis_daemon 0.099 / supabase-api 0.026 etc.) 라이브. (2) **LightRAG dual-level** (`graphrag.py --dual-level`): low-level entity match + high-level community summary match + edge type pattern (3-way). Korean query "depends_on" / "kott" / "persona" 모두 정상. (3) **Neo4j migration scaffold** (`.agent/ontology/neo4j/` + `scripts/ontology/migrate_to_neo4j.py`): docker-compose (5-community + apoc + n10s) + cypher_schema.cql (13 constraints + 11 indexes) + migrate script (UNWIND batch MERGE, 333 nodes / 161 edges import-ready, dry-run PASS) + README (bootstrap + dual-write + n10s + rollback). (4) **SBU vector index** (`scripts/ontology/vector_index.py`): scikit-learn TF-IDF char_wb (2,4) n-gram, Korean morphology friendly, sparse matrix + pickle vectorizer + JSON meta. 2 SBU bucket 라이브 (Neo Genesis 58 artifacts × 10K features / unowned 36 artifacts × 1.2K features). 글로벌 query "persona dispatcher 라우팅" → top 5 cosine sim 0.11~0.16. (5) **OntoClean v0.4 재평가** (`ontoclean_reeval_v0.4.md`): 4 subtype trigger 재검토, 모두 DEFER 유지 (Artifact/Service/Task) + Agent G1-12 유지. G1-25 자율 박제. **회귀**: validate 6/6 P0 + competency 20/20 PASS. 누적 G1 25건, ActionRun 8건, 11/11 클래스 유지. |
| 2026-05-14 | **Business ontology v0.1 분리 신설** | Strategy Lead Claude Opus 4.7 | owner cold 지적 — meta-ontology 가 답할 수 없는 Neo Genesis 본질 (1인 founder + AI multi-agent → 12 product → 잠재 매출) 별도 layer 신설. CTS-AI 클라이언트 / JD 9건 / personal 모두 본 ontology 외 (owner 다른 context). 신규 `.agent/ontology/business/DESIGN_business_v0.1.md` + `nodes.jsonl` (88) + `edges.jsonl` (98) 박제. **10 classes**: Founder(1) / Product(16) / Domain(6) / Strategy(1) / RevenueStream(13) / Investment(5) / ResearchIP(3) / Lead(15) / KPI(5) / Decision(23). **AuraDB 사이드 sync**: 88/88 node parity, 9 Biz rel types active, 10 cross-link biz↔meta (Product↔Project). daily_maintain 통합 9/9 step PASS (extract_business + sync_business_to_neo4j 추가). G1-32-v2/33/34/35 박제. |
| 2026-05-14 | **v0.4 Neo4j AuraDB 라이브** | Strategy Lead Claude Opus 4.7 | owner 가 AuraDB Free 인스턴스 (`394b2602.databases.neo4j.io`, Neo4j 5.27-aura Enterprise) 제공. Docker self-host 우회 (admin 차단 회피). 신규 `scripts/ontology/apply_neo4j_schema.py` (cypher-shell 대체, AuraDB Bolt 전용). **schema 적용**: 23/23 statement OK (12 unique constraints + 11 explicit indexes + 14 auto from constraint = 25 total). **migration**: `migrate_to_neo4j.py` 에 `flatten_for_neo4j()` 추가 (nested dict → JSON string, Neo4j primitive 한계 회피). 결과 — **node parity TRUE** (333/333), **edges 160/161** (references 1건 MATCH 실패, target node missing). **Cypher live 검증 7/7 PASS**: CQ-06 (quant-bot-live host=ysh-server) / CQ-07 (ysh-server 8 services) / CQ-08 (4 offline devices) / **Impact 2-hop from supabase-api** (quant-bot-live + neo_genesis_daemon 1-hop, sora-live 2-hop via 체인) / Tier S 8 personas / ActionRun 6종 분포. `AURA_INSTANCE.md` 박제 (password redacted, 회전 owner declined). G1-26 자율 박제 (AuraDB Free 채택, Docker self-host v1.0 deferred until RDF export 필요). |
| 2026-05-14 | **v0.5 진입 4건 라이브 (OWL closure + LangChain QA + dual-write + KURE hook)** | Strategy Lead Claude Opus 4.7 | (1) **OWL EL transitive closure** (`query.py --closure`): 5 transitive relations (depends_on / blocks / supersedes / prov:wasDerivedFrom / composed_of) DuckDB recursive CTE 기반 forward/reverse closure + cycle protection (NOT list_contains path) + max_depth 10. 검증: reverse closure to supabase-api → sora-live (depth 2 inferred:true via neo_genesis_daemon). (2) **LangChain GraphCypherQAChain** (`scripts/ontology/langchain_qa.py`): AuraDB Bolt 통합 + 4 LLM provider 추상 (anthropic / openai / ollama / mock) + schema auto-introspection. mock LLM E2E PASS — 자연어 query "ysh-server services" → Cypher 생성 → AuraDB 실행 → 8 service rows. Live LLM 은 ANTHROPIC_API_KEY/OPENAI_API_KEY 필요. (3) **dual-write hook** (`write_queue.py _sync_to_neo4j`): apply_diff() 가 JSONL 적용 후 best-effort Neo4j MERGE 호출. NEO4J_BOLT_URI env var 설정 시 자동 활성. E2E: mutate.py --add-task → JSONL 33 + Neo4j 33 parity sync 성공 (neo4j_sync.status=synced). non-fatal — Neo4j 실패해도 JSONL primary 무영향. (4) **KURE-v1 client hook** (`vector_index.py`): KURE_BASE_URL env var (default http://desktop-sol01:7702) ping → kure_available() → 가용 시 1024-dim dense embedding, 실패 시 TF-IDF char_wb fallback. 자동 vectorizer 선택 + meta.vectorizer_type 박제 (kure-v1 / tfidf_char_wb_2-4). G1-27/28/29/30 박제 (4 v0.5 자율 결정 한 줄 reversible). **회귀**: validate 6/6 P0 PASS + competency 20/20 PASS + AuraDB parity 337/337 (JSONL과 sync) 유지. |

---

👤 Strategy Lead Claude Opus 4.7
