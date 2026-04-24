# AI Agent OSS Framework Scorecard v2 (2026-04-24)

> Principle: framework는 유행이 아니라 실패 비용, 상태 관리, 보안, 평가, 팀 스택에 맞춰 고른다.
> Source policy: 최신 버전, license, API는 사용 직전 공식 문서와 repository에서 재확인한다.

## 0. Selection Tiers

| Tier | Meaning | Rule |
|---|---|---|
| Default | Neo Genesis 기본 후보 | 새 프로젝트에서 우선 검토 |
| Candidate | 상황별 강한 후보 | 특정 stack/use case일 때 채택 |
| Watch | 연구/실험/보조 후보 | production 핵심 경로에 바로 넣지 않음 |
| Avoid By Default | 기본 비권장 | 기존 의존성 또는 명확한 이유가 있을 때만 |

## 1. Production Runtime And Orchestration

| Framework | Tier | Best For | Strengths | Weaknesses | Neo Genesis Rule | Sources |
|---|---|---|---|---|---|---|
| LangGraph | Default | 장기 stateful workflow, HITL, checkpoint, agent graph | durable execution, streaming, human-in-the-loop, memory, LangSmith tracing | low-level이라 설계 책임이 큼, LangChain 생태계 결합 리스크 | Sora long-running workflow와 승인/롤백이 필요한 작업의 1순위 패턴 | https://docs.langchain.com/oss/python/langgraph |
| OpenAI Agents SDK | Default | OpenAI 중심 tool/handoff/guardrail/tracing/sandbox | agents, handoffs, guardrails, tracing, MCP, sandbox, file/shell/apply_patch primitives | OpenAI 모델 최적화 중심, hosted/built-in tool guardrail 제약 확인 필요 | Codex-like file 작업과 OpenAI 기반 제품 agent의 기본 SDK | https://openai.github.io/openai-agents-python/ |
| Microsoft Agent Framework | Default | enterprise workflow, graph, telemetry, MCP, A2A, state | AutoGen+Semantic Kernel 계승, workflows, type-safe routing, checkpointing, HITL, middleware | preview/버전 변화 가능성, .NET/Foundry 계열 이해 필요 | regulated/enterprise SBU 또는 Azure/Microsoft connector 필요 시 기본 | https://learn.microsoft.com/en-us/agent-framework/overview/ |
| Google ADK | Candidate | Gemini/Google Cloud 중심 production agent | Python/TS/Go/Java, graph workflows, evaluation, deployment, Google Cloud integration | Google ecosystem bias, model/version naming 재확인 필요 | Gemini/Antigravity/Google Cloud 연동 agent의 기본 후보 | https://adk.dev/ |
| AutoGen | Avoid By Default | research-grade multi-agent conversation, Magentic-One style | multi-agent teams, web/code/file handling examples, Microsoft lineage | Microsoft Agent Framework로 migration 흐름, 신규 production은 MAF 우선 | 기존 AutoGen 자산 유지 또는 migration reference로만 사용 | https://github.com/microsoft/autogen |
| Semantic Kernel Agent Framework | Candidate | existing Semantic Kernel apps | Microsoft plugin/connectors ecosystem, agent patterns | MAF로 통합되는 방향 | 기존 SK 기반 프로젝트만 유지 | https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/ |

## 1.1 Durable Execution / Background Workflow Layer

> Rule: agent runtime 위에 올릴 durable layer는 프로젝트의 failure cost와 언어 스택으로 선택한다. Temporal/Restate/Dapr Agents/Inngest/Trigger.dev는 agent runtime과 경쟁하지 않고 보완한다.

| Framework | Tier | Best For | Strengths | Weaknesses | Neo Genesis Rule | Sources |
|---|---|---|---|---|---|---|
| Temporal + OpenAI Agents SDK integration | Candidate | durable long-running agent workflow, crash recovery, retries, scheduling | 언어 중립 Event History, 재시작/크래시 복구 표준, 2025 OpenAI Agents SDK 공식 통합 | 별도 인프라 운영 비용, 학습 곡선 | Sora 텔레그램 장시간 작업(이미지 생성, 크론, 재시도, 디바이스 페일오버)에 durable execution 얹기 후보 | https://temporal.io/blog/announcing-openai-agents-sdk-integration |
| Restate | Watch | 경량 durable execution, 서버리스/엣지 친화 | 작은 footprint, TS/Python/Java 지원 | 생태계 Temporal보다 작음 | Temporal 대안 비교 용도로 추적만 | https://docs.restate.dev/ai/patterns/durable-agents |
| Dapr Agents | Watch | CNCF, 분산 actor, 멀티 디바이스 플릿 | actor model과 멀티 디바이스 오케스트레이션 이론상 적합 | 2025-03 공개, 프로덕션 evidence 아직 미약 | 멀티 디바이스 에이전트 분산 실험 R&D 후보 | https://www.cncf.io/blog/2025/03/12/announcing-dapr-ai-agents/ |
| Inngest | Candidate | step function + MCP server 통합 (2025-10) | TypeScript 친화, 서버리스 integration | agent reasoning/eval은 별도 | SBU/Next.js 측 ops automation glue에 적합 | https://www.inngest.com/ |
| Trigger.dev | Watch | background job, workflow scheduling | OSS, self-hosted 가능 | agent-centric 기능은 Inngest 대비 간접적 | 배치/스케줄링 workload가 주가 되면 재평가 | https://github.com/triggerdotdev/trigger.dev |
| DSPy 3.x | Watch | 자기최적화 prompt, declarative optimization | 프롬프트 자동 튜닝, 평가 기반 개선 | 운영 복잡도, production 경로보다 연구 경로 | 프롬프트 최적화가 명시적 bottleneck이 되면 꺼낼 카드 | https://github.com/stanfordnlp/dspy |
| Mirascope | Watch | anti-framework Python LLM helper | 교체 비용 낮은 얇은 래퍼 | 프레임워크급 보장 X | Pydantic AI 보완용 라이트 옵션 | https://github.com/Mirascope/mirascope |

## 2. Data, RAG, And Knowledge Agents

| Framework | Tier | Best For | Strengths | Weaknesses | Neo Genesis Rule | Sources |
|---|---|---|---|---|---|---|
| LlamaIndex | Default | document/RAG/query planning/data agents | routing, sub-questions, query transforms, tool use, workflows, agent microservices | app orchestration보다 data/RAG 중심 | BIBLE, docs, project memory RAG의 기본 후보 | https://docs.llamaindex.ai/en/stable/use_cases/agents/ |
| Haystack | Candidate | production RAG pipelines, document stores, search | components/pipelines, agents/tools, multimodal/search, enterprise-friendly | multi-agent orchestration은 LangGraph/MAF보다 약함 | retrieval pipeline이 핵심이면 LlamaIndex와 비교 | https://docs.haystack.deepset.ai/docs |
| Dify | Candidate | no-code/low-code LLM apps, ops workflows | app builder, dataset/RAG/workflow UI | 코드 레벨 제어와 repo-integrated eval은 제한 | 비개발자 운영자용 workflow prototype에 한정 | https://docs.dify.ai/ |
| Flowise | Watch | visual LangChain/LangGraph workflows | 빠른 visual prototype | production governance/eval은 별도 필요 | 데모/실험용, core runtime으로 고정 금지 | https://docs.flowiseai.com/ |

## 3. Python And Type-Safe Agent Frameworks

| Framework | Tier | Best For | Strengths | Weaknesses | Neo Genesis Rule | Sources |
|---|---|---|---|---|---|---|
| Pydantic AI | Default | typed Python agents, FastAPI, structured output | Pydantic ecosystem, type safety, validation-first | orchestration infra는 별도 필요 | FastAPI backend agent와 structured response 기본 후보 | https://ai.pydantic.dev/ |
| Agno | Candidate | lightweight Python agent with memory/storage/guardrails | stateful control loop, memory, knowledge, guardrails, metrics hooks | ecosystem maturity를 repo별 확인해야 함 | 작은 Python agent prototype과 local tools에 적합 | https://docs.agno.com/agents/overview |
| smolagents | Candidate | lightweight code agents, HF ecosystem, education | ReAct loop, CodeAgent, ToolCallingAgent, simple API | docs가 experimental API warning, production guardrails 별도 | local/offline 실험과 빠른 tool-use baseline에 적합 | https://huggingface.co/docs/smolagents/reference/agents |

## 4. TypeScript, App, And Workflow Frameworks

| Framework | Tier | Best For | Strengths | Weaknesses | Neo Genesis Rule | Sources |
|---|---|---|---|---|---|---|
| Mastra | Default for TS | TS/Node agent apps, workflows, MCP, observability | MCP server/client, workflows, HITL, OTEL tracing, eval/scorers, Next/Vite integrations | API surface 변화 가능, production evidence 확인 필요 | Next.js SBU agent app의 TS 후보 | https://mastra.ai/docs/mcp/overview |
| Vercel AI SDK | Candidate | Next.js streaming AI UX | streaming, tool calling, UI integration | full agent governance는 별도 필요 | frontend streaming layer로 사용, runtime source of truth는 별도 | https://sdk.vercel.ai/docs |
| n8n | Candidate | ops automation, integrations, scheduled workflow | 많은 connector, human ops workflows | agent reasoning/eval은 약함 | Telegram/ops automation glue layer로만 사용 | https://docs.n8n.io/ |

## 5. Multi-Agent, Interop, And Research Ecosystems

| Framework | Tier | Best For | Strengths | Weaknesses | Neo Genesis Rule | Sources |
|---|---|---|---|---|---|---|
| CrewAI | Candidate | role-based crews, business/content/research automation | crews, flows, guardrails, memory, observability | strict state/control은 LangGraph/MAF보다 약함 | 콘텐츠/리서치/마케팅 multi-agent에 적합 | https://docs.crewai.com/ |
| BeeAI Platform | Watch | framework-agnostic multi-agent interop via ACP | Linux Foundation/open governance, ACP-based communication | ACP adoption은 MCP/A2A보다 아직 작음 | A2A/ACP interoperability research로 추적 | https://research.ibm.com/projects/bee-ai-platform |
| CAMEL-AI | Watch | multi-agent research, societies, synthetic data, simulation | societies, interpreters, memory, RAG, CRAB/OASIS ecosystem | production governance는 별도 설계 필요 | 연구, synthetic data, simulation task에 활용 | https://docs.camel-ai.org/ |
| MetaGPT | Watch | software company style multi-agent generation | role-based software process automation | 유지보수/현대 stack fit 재확인 필요 | legacy research reference로만 사용 | https://github.com/geekan/MetaGPT |

## 6. Developer Agents And Coding Automation

| Tool/Framework | Tier | Best For | Strengths | Weaknesses | Neo Genesis Rule | Sources |
|---|---|---|---|---|---|---|
| Codex | Default | repo-native coding, diff/test workflow | local shell, patch, code review, AGENTS.md | external actions need explicit gates | code edit 기본 실행자 | https://developers.openai.com/codex |
| OpenHands | Candidate | autonomous SWE agent, OSS coding agent | browse/edit/run agent environment | security/sandbox and repo risk 관리 필요 | isolated repo issue solving 실험에 사용 | https://docs.openhands.dev/ |
| SWE-agent / mini-SWE-agent | Candidate | SWE-bench style coding agent evaluation | benchmark-aligned agent baseline | production UX/control plane은 별도 | coding eval baseline으로 사용 | https://www.swebench.com/ |

## 7. Final Default Stack

| Project Type | Runtime | Tool Plane | UX Plane | Eval |
|---|---|---|---|---|
| Sora core | LangGraph or MAF workflow | MCP gateway | AG-UI style dashboard | local golden + AgentDojo + OSWorld slice |
| Next.js SBU | Mastra or OpenAI Agents SDK | MCP + app APIs | Vercel AI SDK + AG-UI/CopilotKit | Playwright + local golden + BFCL slice |
| RAG/docs | LlamaIndex or Haystack | MCP docs/search | source/provenance UI | retrieval eval + citation checks |
| Coding agent | Codex/OpenAI Agents SDK | shell/apply_patch sandbox | diff/test timeline | SWE-bench/Terminal-Bench/local issues |
| Enterprise workflow | Microsoft Agent Framework | MCP/A2A/OpenAPI | approval queue | tau-bench style policy tasks |
| Local/private/offline | Ollama + smolagents/Agno | local-only tools | minimal terminal UI | deterministic local tasks |
