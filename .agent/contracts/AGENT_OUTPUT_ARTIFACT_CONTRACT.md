# Agent Output Artifact Contract v1

> Canonical scope: Neo Genesis agent runs that produce owner-facing status,
> review, deployment, research, or operational reports.
> Principle: keep machine handoff artifacts small and structured; render HTML
> only as a human judgment interface.

## 1. Artifact Roles

| Artifact | Audience | Canonical? | Purpose |
|---|---|---:|---|
| `result.md` | agents and humans | yes | concise narrative result and handoff context |
| `decision.json` | agents, gates, dashboards | yes | structured verdict, evidence, risk, approval, and next action |
| `trace.jsonl` | audit and debugging | yes | tool calls, timings, failures, approvals, and retries |
| `evidence/` | audit and review | yes | logs, screenshots, diffs, test output, source snippets |
| `judgment.html` | owner | no | rendered control surface for quick proceed/review/block decisions |

`judgment.html` must be reproducible from `decision.json` and evidence
references. Do not use HTML as the source of truth for agent-to-agent handoff.

## 2. Required Decision Artifact

Every substantial run should produce or be convertible into a
`decision.json` with this top-level shape:

```json
{
  "schemaVersion": "ng.judgment.v1",
  "generatedAt": "2026-05-12T13:00:00+09:00",
  "run": {
    "id": "sbu-growth-20260512",
    "kind": "sbu_growth",
    "sourceArtifacts": []
  },
  "mission": {
    "goal": "Owner-visible task goal",
    "successCriteria": [],
    "constraints": []
  },
  "verdict": {
    "status": "green",
    "decision": "proceed",
    "label": "Proceed",
    "reason": "All blocking gates passed."
  },
  "summary": {
    "conclusion": "Short conclusion first.",
    "topAction": "One immediate action.",
    "residualRisk": "Known remaining risk."
  },
  "metrics": [],
  "lanes": [],
  "evidence": [],
  "risks": [],
  "approvals": [],
  "memory": [],
  "nextActions": []
}
```

## 3. Verdict Semantics

| Status | Decision | Meaning |
|---|---|---|
| `green` | `proceed` | No blocker remains; normal follow-up can continue. |
| `yellow` | `review` | Work is usable, but at least one warning or owner judgment point remains. |
| `red` | `block` | A critical gate failed or external side effect must not proceed. |

Do not mark a run `green` unless tests, diffs, sources, or equivalent evidence
are attached or referenced.

## 4. Authority And Approval

Use the existing Neo Genesis governance tiers:

| Tier | Examples | Default handling |
|---|---|---|
| `G0` | read public docs, inspect code | allowed with trace |
| `G1` | local file edit, local test | allowed with diff and verification |
| `G2` | local destructive action | ask or prove rollback before action |
| `G3` | deploy, push, email, DB write, Slack | explicit scope confirmation |
| `G4` | credential, IAM, billing, DNS, security policy | owner confirmation and official procedure |
| `G5` | personal, legal, financial data | do not read or use unless explicitly authorized |

Approval items must include `authorityTier`, `action`, `scope`,
`rollbackPath`, and `state`.

## 5. Evidence Requirements

Evidence entries should use one of:

- `file`
- `url`
- `command`
- `test`
- `diff`
- `screenshot`
- `log`
- `artifact`

Each entry needs a `label`, `status`, and `reference`. The reference should be
a path, URL, command name, or artifact id. Evidence can summarize outputs, but
must not include secrets.

## 6. HTML Rendering Rules

`judgment.html` is only for fast human review. It should:

- show conclusion first;
- show `green/yellow/red` status visibly;
- keep raw JSON hidden behind a `<script type="application/json">` block;
- escape all untrusted text;
- link to evidence rather than embedding large logs;
- show approval and rollback before external actions;
- show verified/inferred/no-source labels when factual claims are present.

The HTML renderer must not execute project-provided JavaScript from inputs.

## 7. Initial Adoption Targets

1. SBU growth control tower and regression gate.
2. Sora execution results.
3. RAG and memory verification.
4. Frontend/browser QA.
5. Dependency, MCP, and security gate reviews.

Each target must have an entry in
`.agent/registries/judgment_adapter_registry.json` before it is wired into an
automation. The registry records source artifacts, required evidence, approval
rules, and success semantics for that run kind.

## 8. Compatibility

This contract complements `.agent/knowledge/agent-environment/*`.
If this file conflicts with `.agent/NEO_MASTER_RULES.md`, the master rules win.
After changes under `.agent/`, regenerate runtime adapters with:

```powershell
python scripts/sync_agent_context.py
```
