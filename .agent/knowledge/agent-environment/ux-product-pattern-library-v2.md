# Agent UX And Product Pattern Library v2 (2026-04-24)

> Principle: agent UX는 채팅창이 아니라 작업 제어 시스템이다.
> Default: AG-UI event stream + run timeline + approval queue + provenance + rollback.

## 0. Protocol Map

| Protocol/Guideline | Role | Use For | Source |
|---|---|---|---|
| AG-UI | agent backend와 user-facing app 사이의 event protocol | streaming, tool cards, state sync, HITL, custom UI | https://docs.ag-ui.com/ |
| MCP | agent와 외부 tools/data/workflows 연결 | tool gateway, app extension, data access | https://modelcontextprotocol.io/ |
| MCP Apps | MCP response가 interactive UI를 렌더링 | charts, maps, selectors, rich widgets | https://modelcontextprotocol.io/docs/extensions/apps |
| A2A | agent-to-agent interoperability | agent discovery, Agent Cards, delegation | https://a2a-protocol.org/dev/ |
| Microsoft HAX | human-AI interaction guidelines | AI UX lifecycle and failure handling | https://www.microsoft.com/en-us/haxtoolkit/ |
| Google PAIR | people-centered AI design | user needs, feedback, mental models | https://pair.withgoogle.com/guidebook-v2/ |
| Apple HIG ML | ML feature design | confidence, attribution, mistakes, privacy | https://developer.apple.com/design/human-interface-guidelines/machine-learning/ |
| IBM Carbon for AI | enterprise AI UI language | AI labeling, explainability, product consistency | https://carbondesignsystem.com/guidelines/carbon-for-ai/ |

## 1. Required Agent UI Components

| Component | Required Behavior |
|---|---|
| Run timeline | plan, tool call, approval, result, retry, failure, rollback을 시간순으로 표시 |
| Tool card | tool name, purpose, inputs, outputs, authority tier, duration, status 표시 |
| Approval queue | external/destructive action을 pending state로 표시하고 approve/deny/edit 제공 |
| State panel | current task, assumptions, constraints, memory used, active files 표시 |
| Source/provenance panel | URL, file, API, model, benchmark, generated artifact 연결 |
| Diff viewer | file edit 전후 비교와 rollback path 표시 |
| Error recovery panel | failure reason, retry option, manual fallback 표시 |
| Memory viewer | saved preference/project memory를 열람, 수정, 삭제 가능 |
| Multi-agent attribution | 어떤 agent가 어떤 artifact/decision을 만들었는지 표시 |
| Budget meter | tokens, tool calls, wall time, external actions, retry count 표시 |

## 2. AG-UI Event Mapping

| Agent Event | UI Display |
|---|---|
| run_started | new timeline run |
| plan_created | collapsible plan card |
| tool_call_start | pending tool card |
| tool_call_delta | streaming args/progress |
| tool_call_result | result card with source and output summary |
| state_snapshot | state panel refresh |
| state_delta | inline state update |
| approval_required | approval queue item |
| approval_resolved | approved/denied badge |
| memory_read | memory provenance badge |
| memory_write_proposed | memory write approval |
| run_failed | failure panel with retry/rollback |
| run_completed | final summary with tests and residual risk |

## 3. HAX/PAIR/Apple/Carbon Derived Rules

| Rule | Product Requirement |
|---|---|
| Set expectations | agent capability and limitation are visible before task starts |
| Show context | user can see what information the agent is using |
| Support correction | user can edit plan/tool args/memory before execution |
| Time services based on context | interrupt only when risk or uncertainty justifies it |
| Explain failures | failure message includes cause, impact, next action |
| Learn over time | feedback is captured but memory writes are transparent |
| Privacy by design | sensitive data collection is minimized and explained |
| Confidence and attribution | generated output distinguishes verified facts, inference, recommendation |
| AI labeling | AI-generated sections and automated actions are visible |
| Accessibility | status, errors, progress are not color-only; keyboard access required |

## 3.1 2026 Agentic UX Principles (Anthropic / NN/g / Notion / hoop.dev convergence)

| Principle | Source | Product Requirement |
|---|---|---|
| Plan-before-execute | Anthropic "Building Effective Agents" (Schluntz/Zhang, Dec 2024) | every multi-step run renders the step plan card BEFORE any external tool call; owner can edit the plan before approving |
| 4-layer status | Notion 3.0 Agents (2025-09) | ambient badge → glanceable progress → attention notification → completion summary. No push per step |
| Undo-first approval | hoop.dev / permit.io HITL 2025 | destructive/external actions show preview-diff + one-click undo path BEFORE approve; "OK/Cancel" modal alone is insufficient |
| 3-level uncertainty label | NN/g 2025 "Research Agenda for GenAI UX" | label claims as `verified` / `inferred` / `no source` instead of exposing numeric confidence scores (avoids automation bias) |
| AX (Agentic Experience) readable output | Mathias Biilmann (Netlify 2025) | product surfaces expose machine-readable endpoints and agent-friendly discovery; human-first is not the only mode |
| Anti-workslop gate | HBR / The Deep View 2025 | "completion" is not declared until tests/diffs/sources are attached; prevents low-quality output forcing human repair labor |
| Ambient vs intentional invocation (gap) | R4 opportunity gap | voice/hotkey/screen-capture invocations are normalized into one prompt envelope with a single privacy indicator |

## 4. Anti-Patterns

| Anti-Pattern | Why It Fails | Replacement |
|---|---|---|
| "Just a chatbot" | hides actions, state, and risk | control plane with timeline |
| invisible tool calls | user cannot audit external effects | tool cards and trace |
| automatic deploy/push | high blast radius | approval queue |
| fake confidence | erodes trust | confidence + verification status |
| memory without UI | feels creepy and causes stale personalization | memory viewer |
| LLM judge only | unreliable and gameable | deterministic checks + human review |
| all agents in one stream | attribution lost | per-agent lanes and handoff artifacts |
| no cancel button | long-running agents trap user | pause/resume/cancel |
| no rollback preview | users fear applying changes | rollback plan before action |

## 4.1 2026 OSS Library Picks For Sora Dashboard v4

> Principle: 이 문서 §1의 10 required components를 Next.js 16 / React 19 / Tailwind 4 / shadcn 스택에서 실제로 구현할 때의 default pick.
> Rule: 공식 docs와 repo를 채택 직전 재확인한다. 아래 picks는 2026-04-24 시점 베스트.

| Required Component | 2026 Default Pick | Notes / Source |
|---|---|---|
| Run timeline, Message, Reasoning, Tool card | **Vercel AI Elements** (shadcn 기반 20+ 컴포넌트) + **assistant-ui** primitives | https://github.com/vercel/ai-elements / https://www.assistant-ui.com |
| Streaming markdown | **Streamdown v2.5** (Vercel) | react-markdown은 AI 스트리밍 용도로 2025년부터 사실상 obsolete; https://vercel.com/changelog/streamdown-v2 |
| Diff viewer | **git-diff-view** (크로스 프레임워크) or **react-diff-viewer-continued (Aeolun fork)** | 원본 praneshr/react-diff-viewer는 유지 중단 |
| Code editor | **CodeMirror 6** (default) / **Monaco** (풀 IDE 필요 시에만) | Sourcegraph Monaco→CodeMirror 마이그레이션 완료 사례 |
| Syntax highlight (streaming) | **Shiki** + **shiki-stream** (antfu) | react-syntax-highlighter는 deprecating 흐름 |
| Terminal | **react-xtermjs** (Qovery) + addon-attach WebSocket | `xterm-for-react`, `react-xterm`은 deprecated |
| Command palette | **cmdk** (pacocoursey) | Linear/Raycast/Vercel 실사용, shadcn Command의 기반 |
| Dashboard KPI / charts | **Tremor** + **shadcn charts v2 (Recharts)**; 커스텀 토폴로지는 **visx** | react-vis(Uber)는 유지 중단 |
| UI primitives (new code) | **Base UI 1.0** (MUI팀, 2026-02, Radix 공식 후계) | 기존 코드는 Radix 유지, 신규는 Base UI |
| Motion / depth | **Motion v12** (`motion/react`, React 19 Compiler 호환) + **tailwindcss-motion** + **@formkit/auto-animate** | `framer-motion` 이름/패키지 deprecated → `motion` |
| Agent backend↔UI protocol | **AG-UI adapter only** (CopilotKit 전체 런타임 종속 X) | Sora 자체 런타임 유지; AG-UI 어댑터만 선택적 도입 |

**Phase 1 구현 우선순위** (Sora Dashboard v4 kickoff):
1. Streamdown + AI Elements Message/Reasoning으로 ThinkingBlock·ToolCard 교체
2. Motion v12 + tailwindcss-motion으로 DeviceCard 재작업 (NaN 버그 해소 + 실시간 게이지)
3. cmdk로 전역 command palette (디바이스/파일/에이전트 전환)
4. Tremor로 플릿 KPI 대시보드
5. CodeMirror 6 + react-xtermjs 실연결 (xterm.js SSH 경로 E2E)

## 5. Sora Dashboard vNext Pattern

| Panel | Purpose |
|---|---|
| Mission Console | current owner goal, plan, status, budget |
| Agent Lanes | Codex/Claude/Gemini/Sora/Ollama contribution and state |
| Tool Gateway | all tool calls with authority tier and approval state |
| Evidence Board | files, URLs, logs, screenshots, benchmark results |
| Risk Board | side effects, security flags, unresolved risks |
| Memory Board | proposed and accepted long-term memory |
| Eval Board | golden tasks, tests, regression, adversarial checks |
| Handoff Board | what is accepted, pending, blocked, delegated |

