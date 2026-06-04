# `.agent/ontology/write_queue/` — Single Writer + Queue (G1-19)

> Per G1-10 (Multi-agent write conflict) + G1-19 (v0.2 = file-based, Supabase v0.3 평가).

## Architecture

```
agents (Claude / Codex / Sora / Antigravity / Ollama)
        |
        v
  scripts/ontology/write_queue.py --propose
        |
        v
  .agent/ontology/write_queue/pending/<timestamp>__<priority>__<agent>__<name>.json
        |
        v (single writer daemon, v0.2 manual / v0.3 cron)
  scripts/ontology/write_queue.py --consume
        |
        v
  .agent/ontology/write_queue/processed/  OR  failed/
        |
        v (v0.3 add: actual apply to nodes.jsonl + edges.jsonl)
  ActionRun{kind:ontology_mutation, status:committed} 박제
        |
        v
  git commit (audit trail)
```

## Directories

- `pending/` — proposed writes, not yet consumed
- `processed/` — successfully applied
- `failed/` — apply failed (manual review needed)

## File format (proposal)

```json
{
  "proposed_at": "2026-05-14T10:50:00+00:00",
  "agent_id": "claude-opus-4-7",
  "name": "add-skill-foo",
  "priority": 5,
  "status": "pending",
  "diff": {
    "add_nodes": [...],
    "add_edges": [...],
    "remove_node_ids": [],
    "remove_edge_ids": []
  }
}
```

## v0.2 → v0.3 plan

v0.2 (current): proposals + consume moves file (no actual apply)
v0.3: actual nodes.jsonl / edges.jsonl mutation + ActionRun 박제 + git commit
v0.3+: Supabase `agent_write_queue` 평가 (multi-machine fleet 필요 시)

## Why not CRDT

CRDT (Yjs / RGA sequence) — 구현 부담 매우 큼, single-writer queue 로 충분. v1.0 까지 deferred (DESIGN §15 / RESEARCH §12).
