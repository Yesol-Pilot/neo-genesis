// Neo Genesis Ontology v0.4 -- Neo4j Cypher schema
// Per DESIGN §3 (11 classes) + §4 (17+ relations) + n10s (RDF export prep)
//
// Apply via:
//   docker exec -i neo-genesis-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD < cypher_schema.cql

// ============================================================
// n10s (Neosemantics) RDF prep — v1.0 SPARQL export ready
// ============================================================
CREATE CONSTRAINT n10s_unique IF NOT EXISTS
FOR (r:Resource) REQUIRE r.uri IS UNIQUE;

// Init n10s graph config (run once before any RDF import/export)
// CALL n10s.graphconfig.init();
// (commented — owner action; activate after first deploy)

// ============================================================
// Unique constraints per class (URI = primary key)
// ============================================================
CREATE CONSTRAINT artifact_id IF NOT EXISTS
FOR (a:Artifact) REQUIRE a.id IS UNIQUE;

CREATE CONSTRAINT revision_id IF NOT EXISTS
FOR (r:Revision) REQUIRE r.id IS UNIQUE;

CREATE CONSTRAINT project_id IF NOT EXISTS
FOR (p:Project) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT service_id IF NOT EXISTS
FOR (s:Service) REQUIRE s.id IS UNIQUE;

CREATE CONSTRAINT device_id IF NOT EXISTS
FOR (d:Device) REQUIRE d.id IS UNIQUE;

CREATE CONSTRAINT agent_id IF NOT EXISTS
FOR (a:Agent) REQUIRE a.id IS UNIQUE;

CREATE CONSTRAINT task_id IF NOT EXISTS
FOR (t:Task) REQUIRE t.id IS UNIQUE;

CREATE CONSTRAINT policy_id IF NOT EXISTS
FOR (p:Policy) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT actionrun_id IF NOT EXISTS
FOR (a:ActionRun) REQUIRE a.id IS UNIQUE;

CREATE CONSTRAINT skill_id IF NOT EXISTS
FOR (s:Skill) REQUIRE s.id IS UNIQUE;

CREATE CONSTRAINT reflection_id IF NOT EXISTS
FOR (r:Reflection) REQUIRE r.id IS UNIQUE;

// ============================================================
// Existence constraints (Enterprise Edition only — Community: 주석 처리)
// ============================================================
// CREATE CONSTRAINT artifact_markings IF NOT EXISTS
//   FOR (a:Artifact) REQUIRE a.markings IS NOT NULL;
// CREATE CONSTRAINT service_status IF NOT EXISTS
//   FOR (s:Service) REQUIRE s.status IS NOT NULL;

// ============================================================
// Indexes for common queries (per object_sets.yaml + competency Q)
// ============================================================
CREATE INDEX artifact_kind IF NOT EXISTS
FOR (a:Artifact) ON (a.kind);

CREATE INDEX service_status IF NOT EXISTS
FOR (s:Service) ON (s.status);

CREATE INDEX service_name IF NOT EXISTS
FOR (s:Service) ON (s.name);

CREATE INDEX device_hostname IF NOT EXISTS
FOR (d:Device) ON (d.hostname);

CREATE INDEX device_online IF NOT EXISTS
FOR (d:Device) ON (d.online);

CREATE INDEX task_status_priority IF NOT EXISTS
FOR (t:Task) ON (t.status, t.priority);

CREATE INDEX project_kind_stage IF NOT EXISTS
FOR (p:Project) ON (p.kind, p.stage);

CREATE INDEX agent_kind IF NOT EXISTS
FOR (a:Agent) ON (a.agent_kind);

CREATE INDEX actionrun_kind IF NOT EXISTS
FOR (a:ActionRun) ON (a.kind);

CREATE INDEX actionrun_started_at IF NOT EXISTS
FOR (a:ActionRun) ON (a.started_at);

CREATE INDEX policy_kind IF NOT EXISTS
FOR (p:Policy) ON (p.kind);

// ============================================================
// Schema check (post-apply, should return all constraints)
// ============================================================
// SHOW CONSTRAINTS;
// SHOW INDEXES;
