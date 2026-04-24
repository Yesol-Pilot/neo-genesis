# AI Agent Research Patterns v2 (2026-04-24)

> Principle: 논문은 이름만 저장하지 않는다. 로컬 runtime, memory, eval, UX, governance 규칙으로 변환한다.

## 0. Core Reasoning And Tool-Use Patterns

| Pattern | What It Adds | Failure Mode It Addresses | Local Rule | Source |
|---|---|---|---|---|
| ReAct | reasoning/action/observation loop | tool use 없는 추측, 관찰 없는 계획 | trace는 최소 `plan/action/observation/result` 구조를 가진다 | https://arxiv.org/abs/2210.03629 |
| Reflexion | 실패 후 언어적 자기 피드백 | 같은 실패 반복 | 실패 로그는 원인, 금지할 다음 행동, 재시도 전략으로 저장 | https://arxiv.org/abs/2303.11366 |
| Tree of Thoughts | 여러 후보 추론 경로 탐색 | 단일 계획 고착 | 큰 변경 전 대안 3개와 검증법을 비교한다 | https://arxiv.org/abs/2305.10601 |
| Graph of Thoughts | thought를 그래프로 병합/변환/평가 | 다중 에이전트 산출물 충돌 | shared-brain task, handoff, review를 의존성 그래프로 본다 | https://arxiv.org/abs/2308.09687 |
| Toolformer | tool 호출 여부와 인자 선택 학습 | tool overuse/underuse, 인자 오류 | tool call eval은 "호출해야 함/호출하면 안 됨"을 모두 테스트한다 | https://arxiv.org/abs/2302.04761 |
| Gorilla/APIBench | API hallucination과 tool selection | 잘못된 도구 선택 | MCP/tool registry는 BFCL/APIBench식 schema eval을 붙인다 | https://arxiv.org/abs/2305.15334 |
| Self-RAG | 검색 필요 판단, 검색 결과 비판 | 출처 없는 답변, 최신성 오류 | 시간 민감 정보는 source attribution 없으면 실패 처리한다 | https://arxiv.org/abs/2310.11511 |
| LATS (2024) | MCTS + value fn + self-reflection으로 ReAct/Reflexion/ToT 통합 | 단일 경로 실패, 탐색/검증 분리 부재 | `neo-architect` 고위험 결정은 LATS-식 후보 경로 탐색을 사용한다 | https://arxiv.org/abs/2310.04406 |
| Plan-and-Act (2025) | Planner/Executor 분리, WebArena 57.58% | 거대 컨텍스트 단일 에이전트의 long-horizon 실패 | 긴 작업은 Planner(claude-architect) + Executor(claude-implementer/codex) 로 분리한다 | https://arxiv.org/abs/2503.09572 |
| GoalAct / HiPlan (2025) | global milestone + step-wise hint 계층 plan | 10+ 스텝 작업의 경로 이탈/drift | paper n80, quant v11, GA4 리포트류는 macro milestone + micro hint로 계층화한다 | https://arxiv.org/abs/2504.16563 |
| MemGPT (2023) | working/archival memory 분리 | context overflow, memory drift | SSOT, 장기 memory, 작업 memory, audit log를 분리한다 | https://arxiv.org/abs/2310.08560 |
| Mem0 (2025) | 프로덕션급 장기 메모리, LangMem/OpenAI baseline 상회 | 세션 간 개인화 손실, ad-hoc 메모리 | `.agent/shared-brain/`을 "raw episode + derived summary" 이중 레이어로 구성한다 | https://arxiv.org/abs/2504.19413 |
| A-Mem (2025) | 동적 재조직 agentic memory | 오래된 메모리 정체, 관계 미갱신 | daily-log 기반 자동 재구조화 실험 (R&D 우선순위) | https://arxiv.org/abs/2502.12110 |
| Episodic Memory Position (2025) | episodic memory가 장기 에이전트의 결정적 공백 | semantic/state 두 층만으로는 장기 수평 실패 | shared-brain에 episodic 층을 semantic(SSOT) + state(status.json)와 별도로 분리한다 | https://arxiv.org/abs/2502.06975 |

## 1. Multi-Agent And Workflow Patterns

| Pattern | Use For | Local Rule | Source |
|---|---|---|---|
| CAMEL role-play | 역할 기반 협업과 social simulation | 역할은 명시하되 권한과 종료 조건 없이는 실행하지 않는다 | https://arxiv.org/abs/2303.17760 |
| AutoGen/Magentic-One | manager-led multi-agent task ledger | task ledger, acceptance criteria, handoff artifact를 남긴다 | https://github.com/microsoft/autogen |
| Magentic-One dual-ledger (2024) | Orchestrator의 outer task ledger + 각 specialist의 inner progress ledger | 단일 progress 스트림에서 attribution/재계획 손실 | `.agent/shared-brain/progress-ledger.md`(inner) 외에 outer task ledger(전체 계획/수락 기준)를 분리 유지한다 | https://arxiv.org/abs/2411.04468 |
| Mixture-of-Agents (2024) | 다층 LLM 팀 합의로 단일 최강 모델 초과 | 단일 모델 편향, 라우팅 고정 | Claude/Codex/Gemini/Ollama 간 MoA 스타일 "층간 합의" 실험 (우선순위 낮음, 실험 전용) | https://arxiv.org/abs/2406.04692 |
| MetaGPT SOP | PM/Architect/Engineer/QA-style software process | 설계 산출물은 책임자와 QA 기준을 포함한다 | https://github.com/FoundationAgents/MetaGPT |
| Agent Workflow Memory | 반복 workflow를 skill로 저장 | 성공 workflow만 승격하고 실패 workflow는 금지 패턴으로 저장 | https://arxiv.org/abs/2409.07429 |
| Spec-driven agents | context-grounded coding | 대규모 repo에서는 spec/context hooks 없으면 구현 금지 | https://arxiv.org/abs/2604.05278 |

## 2. Security Research Patterns

| Pattern | Use For | Local Rule | Source |
|---|---|---|---|
| Instruction hierarchy | privileged instruction 우선순위 | SSOT/user/tool output 권한을 runtime policy에 명시 | https://openai.com/index/the-instruction-hierarchy/ |
| Spotlighting | external content를 data로 표시 | retrieved/web/file content는 delimiter와 source label로 감싼다 | https://www.microsoft.com/en-us/research/publication/defending-against-indirect-prompt-injection-attacks-with-spotlighting/ |
| CaMeL-style capability layer | prompt injection 피해 제한 | 파일/네트워크/배포/credential은 capability token 없으면 실행 불가 | https://arxiv.org/abs/2503.18813 |
| AgentDojo | prompt injection attack/defense utility tradeoff | security score와 task success를 같이 본다 | https://agentdojo.spylab.ai/ |
| AgentSentry/ClawGuard family | indirect prompt injection runtime defense | context purification, causal trace, runtime monitor를 참고한다 | https://arxiv.org/abs/2602.22724 |

## 3. Benchmark Integrity Lessons

| Lesson | Local Rule | Source |
|---|---|---|
| public benchmark can saturate or be contaminated | 공개 점수는 참고만 하고 local hidden golden task를 둔다 | https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/ |
| LLM judge can be prompt-injected | deterministic checks와 isolated judge prompt를 우선한다 | https://agentdojo.spylab.ai/ |
| terminal/browser tasks need execution-based grading | file/DOM/screenshot/command assertions로 채점한다 | https://www.tbench.ai/ |
| computer-use benchmark must be sandboxed | OSWorld류는 VM 전용으로만 실행한다 | https://os-world.github.io/ |

## 4. Local Runtime Translation

| Research Idea | D:/00.test Implementation |
|---|---|
| ReAct | `trace.jsonl` event taxonomy: plan, action, observation, result |
| Reflexion | failed run summary in `.agent/shared-brain/daily-log.md` or future eval DB |
| ToT/GoT | important decisions require alternatives, risk, validation path |
| LATS | `neo-architect` high-stakes decisions explore ≥3 candidate paths with value scoring |
| Plan-and-Act | long-horizon tasks split into planner (claude-architect) + executor (claude-implementer/codex) phases |
| GoalAct/HiPlan | paper/quant/GA4 workflows carry macro milestone header + micro step hints in task board |
| Self-RAG | official docs verification flag for unstable facts |
| MemGPT | SSOT/long-term/working/audit memory separation |
| Mem0 / A-Mem / Episodic Memory | shared-brain gains an episodic layer with "raw episode + derived summary" dual format |
| Magentic-One dual-ledger | outer task ledger (plan+acceptance) + inner progress ledger (step execution) maintained separately |
| MoA (experimental) | multi-model consensus only for clearly ambiguous judgment tasks, not production path |
| Toolformer/Gorilla | tool call schema tests and negative-call tests |
| AgentDojo | prompt injection/security cases in local golden tasks |
| HAX/PAIR | control plane UX, correction, expectation, feedback loops |

