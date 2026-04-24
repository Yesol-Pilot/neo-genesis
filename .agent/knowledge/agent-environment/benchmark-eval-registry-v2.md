# AI Agent Benchmark And Evaluation Registry v2 (2026-04-24)

> Rule: benchmark score는 제품 품질의 대체물이 아니다. benchmark는 실패 모드를 찾는 도구다.
> Local default: public benchmark + project golden task + adversarial task + regression test를 함께 쓴다.

## 0. Evaluation Stack

| Layer | What To Measure | Default Tooling |
|---|---|---|
| Unit | tool schema, parser, guardrail, policy decision | pytest, vitest, schema tests |
| Integration | MCP/API/browser/shell round trip | local scripts, Playwright, docker |
| Agent Task | multi-step task success | golden task harness |
| Security | prompt injection, exfiltration, excessive agency | AgentDojo, OWASP LLM checks |
| UX | visibility, approval clarity, recoverability | checklist + task observation |
| Cost/Reliability | retries, tool calls, tokens, latency, failure recovery | trace.jsonl, OpenTelemetry |

## 1. Coding And Terminal Agents

| Benchmark | Evaluates | Use For | Local Adoption | Source |
|---|---|---|---|---|
| SWE-bench Full/Verified/Lite | real GitHub issue resolution | coding agent capability | sample 5 local repo issues into SWE-style tasks | https://www.swebench.com/ |
| SWE-bench Pro or uncontaminated local issues | frontier coding capability | public Verified contamination/underspecified-test risk 대응 | local hidden tasks를 더 신뢰하고 public Verified는 참고 지표로만 사용 | https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/ |
| SWE-bench Multilingual | coding across languages | polyglot repos | use for Python/TS/Go split evaluation | https://www.swebench.com/ |
| SWE-bench Multimodal | issues with visual elements | UI/code mixed tasks | use for frontend bugs with screenshots | https://www.swebench.com/ |
| SWE-agent / mini-SWE-agent | coding agent scaffolds | baseline agent loop | compare Codex-like workflow against lightweight baseline | https://www.swebench.com/ |
| Terminal-Bench 2.0 | hard terminal tasks in realistic environments | shell competence, dependency install, debugging | create `terminal_tasks/` for Sora/Codex local task suites | https://www.tbench.ai/ |
| BFCL V4 | function/tool calling accuracy and agentic tool use | model/tool-call selection | run before adopting new model for tool-heavy agent | https://gorilla.cs.berkeley.edu/leaderboard |

## 2. Tool-Use, Conversational, And Assistant Agents

| Benchmark | Evaluates | Use For | Local Adoption | Source |
|---|---|---|---|---|
| tau-bench | tool-agent-user interaction in real domains | customer support, policy compliance | create SBU support tasks with simulated user and policy docs | https://arxiv.org/abs/2406.12045 |
| tau2-bench | dual-control environment with user and agent tools | coordination/communication under dynamic state | use for high-risk ops where user state changes during task | https://github.com/sierra-research/tau2-bench |
| GAIA | general assistant tasks requiring reasoning/tools/web | deep research agent | use small curated local equivalent for research tasks | https://huggingface.co/gaia-benchmark |
| ToolBench/API-Bank | real-world API/tool use | API-rich agents | use as conceptual model for MCP/API tool registry eval | https://arxiv.org/abs/2307.16789 |
| AgentBench | multi-environment LLM-as-agent tasks | broad agent behavior | use only as supplementary, not production gate | https://arxiv.org/abs/2308.03688 |

## 3. Browser, Web, And Computer-Use Agents

| Benchmark | Evaluates | Use For | Local Adoption | Source |
|---|---|---|---|---|
| WebArena | realistic web task completion | browser automation | mirror local admin/SBU web tasks with deterministic assertions | https://webarena.dev/ |
| VisualWebArena | visual web navigation | multimodal browser agents | use for screenshot-heavy frontend QA | https://jykoh.com/vwa |
| BrowserGym | standard interface for web agent research | browser agent harness | integrate with local browser tasks later | https://github.com/ServiceNow/BrowserGym |
| WorkArena | enterprise ServiceNow knowledge work | enterprise web apps | use patterns for Sora dashboard/admin workflows | https://www.servicenow.com/blogs/2024/introducing-workarena-benchmark |
| OSWorld / OSWorld-Verified | real computer tasks across OS/apps | desktop/computer control | use only in isolated VM, never on owner personal workspace | https://os-world.github.io/ |
| CRAB | cross-environment multimodal tasks | Ubuntu/Android automation | reference for game/mobile/desktop experiments | https://arxiv.org/abs/2407.01511 |

## 4. Security, Robustness, And Agent Safety

| Benchmark | Evaluates | Use For | Local Adoption | Source |
|---|---|---|---|---|
| AgentDojo | prompt injection attacks and defenses for tool agents | security gate for MCP/tool agents | add workspace, email, browser, file exfiltration scenarios | https://agentdojo.spylab.ai/ |
| AgentHarm (ICLR 2025) | harmful tool-execution elicitation for agents | post-adversarial safety gate for G2+ tools | include at least one AgentHarm-style case per G2+ tool in local golden tasks | https://arxiv.org/pdf/2410.09024 |
| Attacker Moves Second (2025) | adaptive attacker search effectiveness (static 2% → adaptive 96% ASR) | MANDATORY adaptive red-team before new MCP/tool/external API | run ≥50 adaptive attacks against new defense surface before production rollout | https://arxiv.org/html/2510.09023v1 |
| OWASP LLM Top 10 | LLM app risk taxonomy | governance checklist | map each agent tool to OWASP risk items | https://owasp.org/www-project-top-10-for-large-language-model-applications/ |
| MCPSecBench / MCP security bench family | MCP server/client attacks | MCP gateway hardening | run when adding third-party MCP server | https://arxiv.org/abs/2508.13220 |
| AgentDyn | dynamic prompt-injection attacks | adaptive red-team | use for high-risk browser/RAG agents | https://arxiv.org/abs/2602.03117 |
| AgentSentry / ClawGuard papers | indirect prompt injection defenses | defense patterns | reference for context purification and runtime monitors | https://arxiv.org/abs/2602.22724 |

## 5. Local Golden Task Format

Every important agent path should have at least one local golden task.

```yaml
id: ng-agent-001
project: neo-genesis
task_type: coding|research|browser|ops|rag|security
prompt: "User-visible task"
allowed_tools:
  - read
  - shell
  - browser
forbidden_tools:
  - external_write
  - credential_read
success_checks:
  - type: command
    value: "npm test"
  - type: file_contains
    path: "..."
    value: "..."
safety_checks:
  - no_secret_output
  - no_personal_dir_read
  - approval_required_for_external_write
trace_required: true
max_budget:
  tool_calls: 60
  wall_minutes: 20
```

## 6. Minimum Eval Policy

| Change Type | Required Eval |
|---|---|
| prompt/rule change | golden task + regression prompt |
| tool schema change | schema unit test + one happy path + one invalid input |
| MCP server add | security checklist + least privilege review + malicious tool output test |
| browser agent change | deterministic Playwright check + screenshot/trace review |
| coding agent change | local issue task + test command + diff review |
| deploy/ops agent change | dry run + approval path + rollback proof |
