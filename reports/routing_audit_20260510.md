# Routing Audit Report

- generated: 2026-05-10T22:42:41+09:00
- audit dir: `C:\Users\yesol\.claude\audit`
- window since: `2026-05-03T22:42:41+09:00`
- persona files: persona_routing_2026-05-10.jsonl
- agent files: agent_tool_use_2026-05-10.jsonl

## 1. Persona routing summary

- total persona events: **3**
- G2 detection events: **2**
- fallback rate (explicit only): **0.0%** (0 / 0 classified)
- unspecified layer rows (legacy schema): 3 / 3

### Top personas

| persona_id | count | share |
| --- | ---: | ---: |
| `prompt-injection-auditor` | 2 | 66.7% |
| `senior-da-pm-korean` | 1 | 33.3% |

### Layer distribution

| matched_layer | count | share |
| --- | ---: | ---: |
| `(unspecified)` | 3 | 100.0% |

### Confidence

- avg: 0.850 / p50: 0.850 / p95: 0.850 / max: 0.850

### G2 detected events

| ts | persona_id | framework | query_hash |
| --- | --- | --- | --- |
| `2026-05-10T22:12:57+09:00` | `prompt-injection-auditor` | `STRIDE + DREAD + AgentDojo` | `257c554db37f` |
| `2026-05-10T22:14:54+09:00` | `prompt-injection-auditor` | `STRIDE + DREAD + AgentDojo` | `257c554db37f` |

### Framework distribution

| framework | count | share |
| --- | ---: | ---: |
| `STRIDE + DREAD + AgentDojo` | 2 | 66.7% |
| `JTBD + AARRR + Pre-mortem` | 1 | 33.3% |

## 2. Agent tool usage

- total agent tool events: **9**
- general-purpose share: **11.1%** (1 / 9)
- persona-named subagent share: **44.4%** (4 / 9)
- agent_file missing warnings: 0

### subagent_type distribution

| subagent_type | count | share |
| --- | ---: | ---: |
| `(empty)` | 4 | 44.4% |
| `fake-not-exists` | 2 | 22.2% |
| `neo-architect` | 1 | 11.1% |
| `senior-da-pm-korean` | 1 | 11.1% |
| `general-purpose` | 1 | 11.1% |

## 3. Honest data note

- persona events scanned: 3
- agent events scanned: 9
- Sample is small and skewed toward synthetic/regression probes if the hook integration is recent; treat percentages as directional, not statistical.

