# 에이전트 런타임 최적화 매트릭스

> **목적:** Codex, Claude Code, Gemini/Antigravity, Sora, Ollama가 하나의 SSOT를 공유하면서도 각자 가장 잘하는 역할에 집중하도록 운영 기준을 정리한다.
> **최종 갱신:** 2026-04-06
> **원본 SSOT:** `D:/00.test/neo-genesis/.agent/NEO_MASTER_RULES.md`
> **연결 어댑터:** `D:/00.test/neo-genesis/AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `infra/agent-runtime/ollama/Modelfile`

---

## 1. 전체가 공유해야 할 사항

### 1.1 공통 규칙 계층

모든 런타임은 아래 순서를 동일하게 따른다.

1. `NEO_MASTER_RULES.md`
2. `BIBLE.md`
3. `knowledge/AGENT_SHARED_MEMORY.md`
4. `shared-brain/status.json`, `active-tasks.md`, `handoff.md`, `daily-log.md`

### 1.2 공통 운영 원칙

- **언어/보고:** 사용자-facing 응답은 한국어, 결론 우선, 사실/근거 분리
- **Doc-First:** 구현 전에 SSOT와 프로젝트 문서를 먼저 읽기
- **사이드이펙트 점검:** 변경 범위, 영향 대상, 롤백 경로를 먼저 확인
- **안전 우선:** 삭제, 배포, 외부 발송, 권한/크레덴셜 변경은 확인 게이트 유지
- **최신성 검증:** 변할 수 있는 사실은 공식 문서 또는 라이브 상태로 재검증
- **공유 상태 기록:** 중요한 결정은 `.agent/shared-brain/` 또는 `.agent/knowledge/`에 남기기
- **원본/어댑터 분리:** `.agent/`만 직접 수정, 루트/`infra/agent-runtime`은 생성물로 취급

### 1.3 공통 데이터 모델

모든 런타임이 최소한 아래 컨텍스트를 공통으로 참조해야 한다.

- **오너/정체성:** `OWNER_PROFILE.md`
- **장기 지식:** `AGENT_SHARED_MEMORY.md`
- **실시간 상태:** `shared-brain/status.json`
- **진행 작업:** `shared-brain/active-tasks.md`
- **세션 전환:** `shared-brain/handoff.md`
- **운영 로그:** `shared-brain/daily-log.md`

### 1.4 공통 동기화 규칙

1. 원본은 `.agent/`를 먼저 수정
2. `python scripts/sync_agent_context.py` 실행
3. 필요 시 각 디바이스에서 `python scripts/sync_agent_context.py --install-home`
4. Ollama는 `ollama create neo-genesis-shared -f infra/agent-runtime/ollama/Modelfile` 재실행

---

## 2. 역할별 최적화 대상

> 2026-04-24 갱신: 오너 직접 사용 주력 에이전트가 Codex → **Claude Code**로 전환. Codex는 fallback/장기 background/shell-patch economical 경로로 유지.

| 런타임 | 1순위 용도 | 최적화 포인트 | 비최적 용도 |
|-------|------------|--------------|------------|
| **Claude Code (primary)** | 오너 대화형 세션, 대규모 리팩터, 코드 리뷰, SSOT 편집, 아키텍처/연구 수렴 | 다파일 변경, 리뷰 품질, 긴 세션 메모리, 세부 구현 추적, 1M-context 장기 컨텍스트 | 실시간 오케스트레이션, 라이브 서버 총괄 |
| **Codex (fallback)** | Claude 토큰 소진 시 대체 실행, 장시간 autonomous background, repo-native shell/patch | 저장소 탐색 속도, 안전한 패치, 로컬 검증, SSOT 정합성 유지 | 오너 대화형 주력 세션(이제 Claude 우선) |
| **Gemini / Antigravity** | 딥리서치, 비교 분석, 전략 문서화 | 최신 자료 교차검증, 대안 비교, ROI/설계 분석, 문서 내재화 | 직접적인 대규모 코드베이스 수정 |
| **Sora** | 실시간 비서, 도구 오케스트레이션, 디바이스 제어 | 빠른 상태 인지, 원격 실행, 작업 라우팅, 짧고 명확한 보고 | 장시간 수동 코드 리팩터, 대규모 배치 문서 정리 |
| **Ollama** | 로컬/오프라인 보조 추론, 프라이빗 초안 생성, 저비용 반복 작업 | 비용 절감, 오프라인 가용성, 빠른 초안/요약, 사내 프롬프트 고정 | 최신성 요구 작업, 법무/배포/권한 판단, 권위 있는 최종 결정 |

---

## 3. 런타임별 세부 최적화

### 3.1 Codex

**강하게 최적화할 것**
- 저장소 루트 `AGENTS.md` 기준 작업
- `apply_patch` 중심의 안전한 수정 흐름
- 로컬 검증: 문법 체크, 테스트, 빌드, 로그 확인
- `.agent` 문서와 코드 상태의 불일치 탐지

**과도하게 싣지 말 것**
- 불필요하게 긴 철학/배경 설명
- 실시간 운영 상태를 `shared-brain` 없이 추측하는 것
- 공식 문서 확인이 필요한 최신 사실을 기억에 의존하는 것

### 3.2 Claude Code

**강하게 최적화할 것**
- `CLAUDE.md` import 체인으로 프로젝트 메모리 자동 적재
- 코드 리뷰 모드에서 버그/회귀/테스트 누락 우선 보고
- 대규모 리팩터 시 파일 소유권과 변경 범위 명확화
- 세션 종료 전 `handoff` 또는 `daily-log` 반영

**과도하게 싣지 말 것**
- 모든 의사결정을 Claude 로컬 메모리에만 의존하는 것
- shared-brain 갱신 없이 “최근 상태”를 단정하는 것

### 3.3 Gemini / Antigravity

**강하게 최적화할 것**
- `GEMINI.md` 기반의 프로젝트/전역 메모리 적재
- 시장/기술/법규/벤더 비교 분석
- 사용자 지시를 무비판적으로 수용하지 않는 4-step 분석
- 최신 공식 문서 기반의 근거형 제안

**과도하게 싣지 말 것**
- 코드 변경의 최종 실행 주체 역할
- 로컬 파일 수정만으로 해결할 문제에 과도한 리서치 투입

### 3.4 Sora

**강하게 최적화할 것**
- `status.json` 기반의 현재 상태 인지
- 연결 디바이스/서버/작업 큐 오케스트레이션
- 짧고 빠른 보고, 작업 위임, 승인 게이트 유지
- 공용 규칙을 프롬프트에 직접 포함하지 말고 `.agent` + generated runtime 경로 참조

**과도하게 싣지 말 것**
- 장문 아키텍처 변경을 채팅 프롬프트 안에 전부 내장하는 것
- 실시간성이 중요한데 오래된 RAG 결과만 믿는 것

### 3.5 Ollama

**강하게 최적화할 것**
- 반복 요약, 초안 생성, 로컬 코드 패턴 보조
- 인터넷 없이도 유지되어야 하는 최소 공통 규칙 탑재
- 비용 민감 작업의 1차 초안 생성

**과도하게 싣지 말 것**
- 법적/금융/배포/보안 최종 판단
- 최신 벤더 문서나 현재 서비스 상태 검증
- shared-brain 없이 독립 SSOT처럼 행동하는 것

---

## 4. 용도별 라우팅 규칙

| 작업 유형 | 기본 주관 | 보조 | 이유 |
|----------|----------|------|------|
| 코드 수정/버그 픽스 | **Claude Code** | Codex (fallback) | 오너 주력 + 긴 컨텍스트 리뷰 품질 |
| 대규모 리팩터/코드 리뷰 | **Claude Code** | Codex (fallback) | 1M-context + 리뷰 품질 |
| 딥리서치/전략/시장 분석 | Gemini / Antigravity | **Claude Code** | 외부 자료 검증과 대안 비교 (Claude 수렴 분석 병용) |
| 실시간 비서/원격 명령/상태 관제 | Sora | **Claude Code** | 실시간성, 디바이스 제어, 라우팅 중심 |
| 로컬 프라이빗 초안/저비용 반복 작업 | Ollama | Codex (fallback) | 오프라인/저비용 보조 역할 |
| SSOT 정리/문서 계층 관리 | **Claude Code** | Codex (fallback) | 오너 주력 + SSOT 정합성 유지 |
| 장시간 autonomous background run | Codex | Claude Code (감독) | Claude 토큰 보존, shell/patch economical |

---

## 5. 소유권 분리

### 5.1 전체 공유층

- 규칙 SSOT: `.agent/NEO_MASTER_RULES.md`
- 운영 참고: `.agent/BIBLE.md`
- 장기 지식: `.agent/knowledge/AGENT_SHARED_MEMORY.md`
- 라이브 상태: `.agent/shared-brain/*`

### 5.2 런타임 특화층

- Codex: `AGENTS.md`
- Claude Code: `CLAUDE.md`
- Gemini CLI: `GEMINI.md`
- Ollama: `infra/agent-runtime/ollama/*`
- Sora: `src/core/data/sora_context.json`

### 5.3 디바이스 로컬층

- `~/.codex/AGENTS.md`
- `~/.claude/CLAUDE.md`
- `~/.gemini/GEMINI.md`
- 각 장치의 Ollama 로컬 모델 레지스트리

디바이스 로컬층은 **프로젝트 SSOT를 가리키는 얇은 포인터**만 두고, 실제 규칙 내용은 프로젝트에 둔다.

---

## 6. 운영 권장안

### 반드시 공용으로 묶을 것

- 언어/톤/결론 우선 구조
- 오너 프로필과 호칭
- 승인 게이트 기준
- shared-brain 실시간 상태
- 장기 기억 문서
- 동기화 명령과 생성 어댑터 목록

### 디바이스 배치 최적화

- `YSH-Server`는 `소라 코어 / 오케스트레이터 / Redis / scheduler / tunnel`에 집중한다.
- `DESKTOP-SOL01`은 `Ollama / ComfyUI / GPU 워커`를 전담한다.
- `MX Mac Studio`는 `상시 execution plane`이 아니라 `Apple 빌드 / 격리 연구 / 필요 시 보조 추론`에만 투입한다.
- `S26 Ultra`는 즉시성 중심 승인 장치, `Tab S10 Ultra`는 가시성 중심 운영 콘솔로 유지한다.

### 각 런타임에 맞춰 따로 최적화할 것

- 프롬프트 길이와 형식
- 가져올 파일 수와 깊이
- 검증 루틴의 강도
- 인터넷/공식 문서 의존도
- 디바이스/서버 접근 권한 범위

---

## 7. 공식 참고 문서

- OpenAI Codex AGENTS.md: https://developers.openai.com/codex/guides/agents-md
- Anthropic Claude Code memory / `CLAUDE.md`: https://docs.anthropic.com/ko/docs/claude-code/memory
- Gemini CLI `GEMINI.md`: https://google-gemini.github.io/gemini-cli/docs/cli/gemini-md.html
- Ollama Modelfile: https://docs.ollama.com/modelfile

---

## 8. AI Agent Environment Optimization Standard (2026-04-24)

Canonical blueprint: `.agent/knowledge/20260424_AI_AGENT_ENVIRONMENT_OPTIMIZATION_BLUEPRINT.md`

모든 프로젝트의 에이전트 작업은 "강한 모델 하나"가 아니라 다음 운영 레이어를 기본 품질 기준으로 본다.

| Layer | Standard |
|---|---|
| Runtime | 상태 머신, 체크포인트, 재시도, 롤백 |
| Tool Plane | MCP 우선, 권한 분리, 스키마 검증 |
| Agent Plane | A2A 또는 명시적 handoff, 역할별 책임 분리 |
| UX Plane | AG-UI 스타일 control plane, 실행 타임라인, 승인 큐 |
| Memory | SSOT, 장기 메모리, 작업 메모리, 감사 로그 분리 |
| Evaluation | golden task, regression, adversarial, UX 품질 평가 |
| Security | least privilege, sandbox, prompt injection 방어, credential isolation |
| Governance | 사람 승인, 정책 엔진, 변경 이력, 출처 추적 |

기본 선택 기준:

| 상황 | 우선 패턴 |
|---|---|
| 복잡한 장기 작업 | LangGraph 스타일 state graph |
| OpenAI tool calling 제품 | OpenAI Agents SDK 패턴 |
| 엔터프라이즈 멀티에이전트 | Microsoft Agent Framework 패턴 |
| 역할 기반 협업 자동화 | CrewAI 또는 AutoGen 스타일 orchestration |
| RAG/지식 서비스 | LlamaIndex 또는 Haystack |
| 타입 안전 Python agent | Pydantic AI |
| 개발자 에이전트 | OpenHands, Codex, SWE-bench 기반 eval |
| 비개발자 워크플로 | Dify, Flowise, n8n |
| agent UI | AG-UI/CopilotKit 스타일 event stream |

상시 품질 게이트:

1. 작업 전 goal, scope, side effect, authority, official source를 확인한다.
2. 작업 중 plan, tool call, approval, checkpoint, failure를 trace로 남긴다.
3. 작업 후 tests, logs, diff, source attribution, residual risk를 보고한다.
4. 반복 지식은 SSOT 또는 shared memory에 반영한다.
5. deploy, push, email, DB write, credential 변경은 외부 사이드이펙트로 보고 사전 범위 확인을 한다.

Deep research pack v2:

| Registry | Path |
|---|---|
| Research patterns | `.agent/knowledge/agent-environment/research-patterns-v2.md` |
| Framework scorecard | `.agent/knowledge/agent-environment/framework-scorecard-v2.md` |
| Benchmark/eval registry | `.agent/knowledge/agent-environment/benchmark-eval-registry-v2.md` |
| Security/governance threat model | `.agent/knowledge/agent-environment/security-governance-threat-model-v2.md` |
| UX/product pattern library | `.agent/knowledge/agent-environment/ux-product-pattern-library-v2.md` |
| Local adoption roadmap | `.agent/knowledge/agent-environment/local-adoption-roadmap-v2.md` |

Default stack is `LangGraph + Pydantic AI + Mastra`, with `OpenAI Agents SDK` as the OpenAI-native sandbox/trace/handoff layer and `Microsoft Agent Framework` for enterprise graph workflows.
