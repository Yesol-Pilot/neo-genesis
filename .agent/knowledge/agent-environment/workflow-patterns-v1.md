# Agent Workflow Internalization Pack v1 (2026-04-24)

> Purpose: convert workflow/orchestration research into repeatable local operating workflows for D:/00.test.
> Scope: Sora, Codex, Claude Code, Antigravity, Ollama, SBU apps, research projects, dashboard operations.
> Rule: prefer auditable, resumable, approval-aware workflows over unchecked autonomy.

## 0. Conclusion

The local default should be a layered workflow system:

| Need | Default Pattern |
|---|---|
| Agent graph with checkpoints and human approval | LangGraph-style state graph |
| Enterprise multi-agent process | Microsoft Agent Framework workflow |
| Deterministic Gemini/Google orchestration | Google ADK workflow agents |
| OpenAI-native handoff, tracing, guardrails | OpenAI Agents SDK |
| Long-running durable backend work | Temporal or Restate |
| TS/serverless background AI jobs | Trigger.dev or Inngest |
| Python data/ML pipeline | Prefect, Dagster, Airflow |
| Declarative event/data orchestration | Kestra or Argo Workflows |
| Operator-visible low-code automation | n8n or Windmill |
| Agent UI workflow | AG-UI event stream plus approval queue |
| Tool/user interaction protocol | MCP tools, roots, elicitation, sampling with policy gates |

Do not pick one workflow engine for every job. Internalize a workflow catalog, then select by durability, side effects, language, operator visibility, and approval requirements.

## 1. Workflow Taxonomy

| Type | Use When | Minimum Gates |
|---|---|---|
| local_checklist | One-session repo tasks, docs, tests | SSOT read, diff review, local test |
| state_graph | Branching agent process, retry, HITL | checkpoint, typed state, approval node |
| durable_execution | Hours/days, crash recovery, idempotent steps | durable log, activity isolation, replay-safe design |
| data_orchestration | ETL, analytics, scheduled reports | schedule/sensor, data lineage, retry, observability |
| low_code_operator | Nondeveloper ops, simple integrations | credential scope, visible approval, exported JSON |
| browser_qa | UI verification, local dashboard, crawler checks | isolated profile, screenshot/DOM evidence |
| external_side_effect | deploy, push, email, finance, DB writes | G4/G5 approval, rollback, audit log |
| agent_handoff | Multi-agent or multi-runtime collaboration | owner goal, role ownership, handoff artifact |
| mcp_tool_workflow | Tool discovery, user input, file roots | server allowlist, schema pinning, root boundaries |

## 2. Internalized Workflow Patterns

### 2.1 Deep Research Refresh

Use for framework, benchmark, security, UX, and workflow source updates.

Required flow:

1. Load SSOT and current registry.
2. Query official docs and primary research sources.
3. Update markdown summary.
4. Update machine-readable registry.
5. Run local freshness/source checks.
6. Persist run summary under `.agent/eval-runs`.
7. Sync runtime adapters after `.agent` changes.

Local command:

```powershell
python scripts/agent_research_refresh.py --json --no-write
python scripts/agent_research_refresh.py --json --no-write --check-urls --url-limit 10
```

### 2.2 Code Change With Regression Gate

Use for any repo code edit.

Required flow:

1. Read applicable AGENTS/SSOT docs.
2. Identify upstream/downstream references.
3. Write side-effect table.
4. Patch only scoped files.
5. Run syntax/unit/build checks.
6. Report changed files, tests, residual risks.

Default engine: local checklist for small tasks, LangGraph/Microsoft workflow for long-running refactors.

### 2.3 MCP Server Onboarding

Use before enabling any new MCP server or local tool bridge.

Required flow:

1. Verify official source and license.
2. Assign authority ceiling G0-G5.
3. Define roots, credentials, network boundary, and schema hash mode.
4. Add server to `.agent/policies/mcp_tool_policy.yaml`.
5. Add red-team cases if new attack surface exists.
6. Run MCP policy check.

Local command:

```powershell
python scripts/agent_mcp_policy_check.py --json --no-write
```

### 2.4 Human Approval Side-Effect Gate

Use for deploy, push, email, Slack, credential, DNS, finance, and irreversible actions.

Required flow:

1. Generate disclosure bundle: action, target, credentials, cost, rollback, blast radius.
2. Queue approval in dashboard or chat.
3. Execute only approved action.
4. Verify externally visible result.
5. Record trace and shared-brain summary.

Default engine: AG-UI approval event plus local policy engine. For long waits, use Temporal/Trigger.dev/Inngest/Restate style durable pause.

### 2.5 Browser And Dashboard QA

Use for local UI, Sora dashboard, public landing pages, and social/SEO previews.

Required flow:

1. Start local service with explicit env.
2. Open isolated browser profile.
3. Verify DOM state, network responses, and critical UI labels.
4. Capture screenshot/trace only when useful.
5. Stop server and remove temporary artifacts.

Default engine: Playwright or Browser Use plugin. Use external sites only with approval when login/payment is involved.

### 2.6 Scheduled Operations And Monitoring

Use for daily/weekly reports, traffic checks, source refresh, and fleet health.

Required flow:

1. Define cron/schedule and timezone.
2. Ensure idempotency and single-run lock.
3. Capture result summary.
4. Alert only on actionable threshold.
5. Store run artifact.

Default engine: local scheduler for Windows tasks, Sora scheduler for agent-visible tasks, Prefect/Dagster/Airflow/Kestra for data pipelines, Trigger.dev/Inngest for TS app background jobs.

### 2.7 Multi-Agent Handoff

Use when Codex, Claude Code, Antigravity, Sora, or subagents collaborate.

Required handoff fields:

| Field | Meaning |
|---|---|
| owner_goal | What the owner actually wants |
| scope | Files/systems/tasks involved |
| authority_tier | G0-G5 ceiling |
| role_owner | Agent responsible for this slice |
| artifacts | Files, logs, tests, dashboards |
| stop_condition | When to stop or escalate |
| validation | How result is verified |

Default engine: shared-brain handoff for local collaboration, A2A-style envelope when cross-runtime messaging is implemented.

### 2.8 Incident Response And Rollback

Use for production errors, broken deploys, security findings, and bot/runtime failures.

Required flow:

1. Freeze scope and preserve logs.
2. Classify severity and side effects.
3. Roll back or mitigate before root-cause refactor.
4. Add regression test or watchdog check.
5. Record incident in shared-brain or project docs.

Default engine: local checklist for one-off incidents, Temporal/Prefect/Dagster/Kestra style workflow for recurring incident pipelines.

## 3. Tool Selection Rules

| Condition | Prefer |
|---|---|
| Need replay-safe long running workflow | Temporal or Restate |
| Need Python-native data job with simple code | Prefect |
| Need data assets, lineage, and materialization | Dagster |
| Need mature DAG scheduling in data stack | Airflow |
| Need Kubernetes-native DAG/steps | Argo Workflows |
| Need declarative event-driven orchestration | Kestra |
| Need scripts plus low-code internal tools | Windmill |
| Need TS background AI jobs and app integration | Trigger.dev or Inngest |
| Need visual integrations with human approval | n8n |
| Need agent state graph inside Python/TS app | LangGraph |
| Need deterministic agent sequencing | Google ADK workflow agents |
| Need enterprise agent/business process blend | Microsoft Agent Framework |
| Need UI event stream for agent actions | AG-UI |
| Need tool/server interaction boundary | MCP |

## 4. Anti-Patterns

| Anti-Pattern | Replacement |
|---|---|
| LLM decides whether approval is needed | Static policy gate decides before execution |
| One giant autonomous loop | Typed state graph with stop conditions |
| Workflow engine runs untrusted shell directly | Sandbox or local policy gate wraps activity |
| Low-code workflow becomes hidden production logic | Export JSON, document owner, add tests |
| Retry without idempotency | Add idempotency key, rollback path, lock |
| Dashboard shows only final answer | Show timeline, tool calls, approvals, artifacts |
| Public leaderboard drives adoption | Local golden task first, public benchmark second |

## 5. Source Index

| Topic | Primary Source |
|---|---|
| LangGraph durable execution | https://docs.langchain.com/oss/python/langgraph/durable-execution |
| Microsoft Agent Framework workflows | https://learn.microsoft.com/en-us/agent-framework/user-guide/workflows/overview |
| OpenAI Agents SDK guardrails | https://openai.github.io/openai-agents-python/guardrails/ |
| Google ADK workflow agents | https://google.github.io/adk-docs/agents/workflow-agents/ |
| CrewAI Flows | https://docs.crewai.com/en/concepts/flows |
| Temporal durable execution | https://temporal.io/ |
| Trigger.dev docs | https://trigger.dev/docs |
| Inngest durable workflows | https://www.inngest.com/uses/durable-workflows |
| Restate workflows | https://docs.restate.dev/use-cases/workflows/ |
| Prefect tasks and flows | https://docs.prefect.io/v3/concepts/tasks |
| Dagster schedules | https://master.dagster.dagster-docs.io/concepts/automation/schedules |
| Airflow scheduler/tasks | https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/scheduler.html |
| Kestra retries | https://kestra.io/docs/workflow-components/retries |
| Windmill flows | https://www.windmill.dev/docs/getting_started/flows_quickstart |
| Argo DAG workflows | https://argo-workflows.readthedocs.io/en/latest/walk-through/dag/ |
| n8n HITL AI tools | https://docs.n8n.io/advanced-ai/human-in-the-loop-tools/ |
| AG-UI overview | https://docs.ag-ui.com/introduction |
| MCP elicitation | https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation |
| MCP roots | https://modelcontextprotocol.io/specification/2025-06-18/client/roots |
| MCP sampling | https://modelcontextprotocol.io/specification/2024-11-05/client/sampling |
| OpenTelemetry GenAI conventions | https://opentelemetry.io/docs/specs/semconv/gen-ai/ |
| OWASP MCP Top 10 | https://owasp.org/www-project-mcp-top-10/ |
| OWASP Agentic Skills Top 10 | https://owasp.org/www-project-agentic-skills-top-10/ |
| Agentproof workflow graph verification | https://arxiv.org/abs/2603.20356 |
| AgentSPEX workflow language | https://arxiv.org/abs/2604.13346 |
| Spec Kit Agents | https://arxiv.org/abs/2604.05278 |
