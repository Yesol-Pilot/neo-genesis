# Agent Environment Deep Research Pack v2 (2026-04-24)

> Purpose: 모든 프로젝트의 agent 결과물 품질을 끌어올리기 위한 심층 리서치 기반 운영 팩.
> Canonical summary: `.agent/knowledge/20260424_AI_AGENT_ENVIRONMENT_OPTIMIZATION_BLUEPRINT.md`
> Use rule: 이 폴더는 긴 컨텍스트용이다. 매번 전부 읽지 말고 작업 성격에 맞는 파일만 선택한다.

## Conclusion

v1은 운영 기본 골격이고, 이 v2 팩은 실제 선택과 검증을 위한 레지스트리다. 기본 전략은 다음과 같다.

| Decision | Default |
|---|---|
| 장기 상태/승인/롤백 workflow | LangGraph 또는 Microsoft Agent Framework workflow |
| OpenAI 중심 coding/file/sandbox workflow | OpenAI Agents SDK |
| Google/Gemini 중심 엔터프라이즈 agent | Google ADK |
| RAG/문서/검색 agent | LlamaIndex 또는 Haystack |
| TS/Next.js agent app | Mastra, Vercel AI SDK, AG-UI/CopilotKit |
| Python typed agent | Pydantic AI 또는 Agno |
| 개발자 agent evaluation | SWE-bench, Terminal-Bench, BFCL, local repo golden tasks |
| browser/computer agent evaluation | OSWorld, WebArena, BrowserGym, WorkArena |
| security evaluation | OWASP LLM Top 10, AgentDojo, MCP security bench family |
| product UX | AG-UI event stream, MCP Apps, HAX, PAIR, Apple HIG, Carbon for AI |

## Files

| File | Use When |
|---|---|
| `research-patterns-v2.md` | 논문과 연구 패턴을 runtime/eval/security 규칙으로 변환할 때 |
| `framework-scorecard-v2.md` | framework를 고르거나 새 라이브러리 추가를 검토할 때 |
| `benchmark-eval-registry-v2.md` | agent 품질, 모델, tool-use, browser, coding 평가를 설계할 때 |
| `security-governance-threat-model-v2.md` | tool 권한, MCP, A2A, prompt injection, secret, 배포 리스크를 다룰 때 |
| `ux-product-pattern-library-v2.md` | Sora dashboard, control plane, agent UI, approval UX를 설계할 때 |
| `local-adoption-roadmap-v2.md` | D:/00.test 전체에 실제 자동화와 체크리스트를 배포할 때 |

## Operating Rule

1. 새 agent 기능은 framework scorecard에서 먼저 분류한다.
2. 외부 action이 있으면 security/governance 문서의 tier를 먼저 적용한다.
3. 제품 UI가 있으면 UX pattern library에서 최소 5개 패턴을 적용한다.
4. 평가가 없으면 완료가 아니다. benchmark registry에서 최소 local golden task를 만든다.
5. 반복될 지식은 `.agent/` SSOT로 승격한다.
6. 정적 AgentDojo 통과 = 안전 아님. adaptive red-team은 별도로 돌린다 (security-governance §5.1).

## Watch List (2026-04-24 추가, 도입은 별도 결정)

| Topic | 이유 | 추적 위치 |
|---|---|---|
| AX (Agentic Experience) 용어 · a16z "Agentic Interface" 2026 | SBU 제품이 machine-readable endpoint로 재편될 때 기준 | ux-product-pattern-library §3.1 |
| ARLAS (attacker-defender co-training) | 정적 방어의 한계 극복 R&D | security §5.1 |
| AgentSociety (1,052명 개인 복제 85%) | 사회 시뮬레이션/연구 도구 | research-patterns §1 (참고만) |
| AI Scientist-v2 (Sakana) | 자동 peer-reviewed 논문 파이프라인 | PAPER 실험의 상위 개념 비교만 |
| BeeAI (ACP) ↔ A2A interop | LF 표준 간 경쟁 시점 주시 | framework-scorecard §5 |
| Computer-Use 에이전트 성숙 (Claude 3.7 / Operator / Mariner) | WebVoyager 83~87%, Sora 디바이스 제어 경로 | framework-scorecard §6 + benchmark §3 |
