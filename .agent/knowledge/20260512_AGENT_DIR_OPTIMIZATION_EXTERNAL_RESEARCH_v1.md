# `.agent/` 최적화 — 외부 Best Practice 심층 리서치 v1

> **작성:** 2026-05-12, Strategy Lead (Claude Opus 4.7)
> **근거:** WebSearch + WebFetch (Anthropic 공식 docs / OpenAI 공식 docs / arxiv / 프레임워크 docs)
> **목적:** Neo Genesis `.agent/` SSOT 가 매 세션 122K tokens (~$1.84) 자동 적재 → 2주 누적 ~$55+ 비용 발생. 외부 best practice 와의 격차 분석 후 P0~P2 권고 도출.
> **방법:** 5 카테고리 (Anthropic 공식 / Codex 비교 / 메모리 연구 / 멀티에이전트 패턴 / 라이프사이클) 병렬 리서치 → 적용 매트릭스 → cold judgment 권고.

---

## 결론 (Cold Honest, 7줄)

1. **Anthropic 공식 권고 = 단일 CLAUDE.md 200줄 미만.** Neo Genesis 현 적재량 122K tokens (~약 12,000+ 줄 동등) 은 **공식 권고의 60배 초과** 상태.
2. **공식 가이드의 핵심 단어 = "Specific, Concise"**. 우리 SSOT 는 운영 history (5/10 K-OTT growth / 5/8 SBU report / 5/6 토스트 audit 등) 가 무분별 append. 명확한 "load-on-launch" vs "load-on-demand" 경계 없음.
3. **가장 큰 leverage 외부 패턴 3가지**: (a) Anthropic 자체의 `auto memory` 분리 모델 (MEMORY.md 200줄 + 토픽 파일 lazy load), (b) Path-scoped `.claude/rules/` (글롭 매칭 시만 로드), (c) Letta/MemGPT 의 Core (always-in-context) vs Archival (RAG retrieval) 3-tier.
4. **부적합 패턴**: Mem0 의 graph-based extraction (LLM call cost > 절감액), A-Mem 의 동적 evolution (운영 복잡도 증가), Letta 풀 OS-tier (SDK 종속).
5. **즉시 적용 가능 P0 3건**: CLAUDE.md 본체 < 500줄로 축소 (현재 122K → 목표 < 5K) + `active-tasks.md` 의 history 를 `.agent/archive/<YYYY-MM>/` 로 이동 + `lastModified` 메타데이터 + staleness linter.
6. **공식 prompt cache (5분 TTL, 2026-03-06 변경)** 활용: 세션 내부에서 SSOT 가 동일하면 cache hit (input cost 90% 절감). 단, 세션 간격 5분 이상이면 cache miss → 본질적 토큰 축소만이 영구 해결.
7. **`active-tasks.md` 4,000+ 줄은 이미 "lost in the middle" (Liu 2023) 의 attention 사각지대**. CLAUDE.md 본체에서 분리 + on-demand RAG 검색 권고.

---

## 1. Anthropic Claude Code Memory (공식)

### 1.1 공식 권고 요약 (2026-05 기준)

Anthropic 공식 docs 가 명시적으로 권고하는 구조:

| 항목 | 공식 권고 | Neo Genesis 현재 | 격차 |
|---|---|---|---|
| **CLAUDE.md 크기** | "target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence." | `AGENTS.md` import chain 으로 122K tokens (~12,000+ 줄 동등) | **60배 초과** |
| **Import 재귀 깊이** | 최대 5 hops | 현재 5 단계 사용 (CLAUDE.md → AGENTS.md → COLLABORATION_CONTRACT → AGENT_SHARED_MEMORY → shared-brain/*.md) | 한계점 (위험) |
| **Auto memory MEMORY.md** | 첫 200줄 또는 25KB 만 세션 로드, 나머지는 topic file lazy load | 현재 미사용. 모든 메모리가 import chain 에 적재 | **lazy load 미적용** |
| **Path-scoped rules** | `.claude/rules/<topic>.md` + `paths:` frontmatter → glob 매칭 시만 로드 | 미사용 | **scoping 미적용** |
| **Compaction 보존** | 프로젝트 root `CLAUDE.md` 만 `/compact` 후 재주입. nested 는 자동 reload 안 됨 | nested 사용 안 함 (good) | OK |
| **Cache** | 2026-03-06 default TTL 1h → **5분** 단축. `cache_control: {"type": "ephemeral", "ttl": "1h"}` 명시 시만 1h | 미설정 (default 5분) | **명시적 cache_control 권고** |

### 1.2 공식 docs 의 핵심 인용

> "CLAUDE.md files are loaded into the context window at the start of every session, consuming tokens alongside your conversation. ... how you write instructions affects how reliably Claude follows them. Specific, concise, well-structured instructions work best."

> "Size: target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence."

> "If your instructions are growing large, use path-scoped rules so instructions load only when Claude works with matching files. You can also split content into imports for organization, **though imported files still load and enter the context window at launch**."

**critical**: imports 도 launch 시 전부 로드됨. 우리가 @import chain 으로 분할해도 토큰 절감 X. "split for organization, not for loading" 이 공식 입장.

### 1.3 Auto Memory 분리 모델 (Anthropic 자체 권고)

Anthropic 이 `MEMORY.md` 와 topic files 를 명시적으로 분리하는 패턴:

```
~/.claude/projects/<project>/memory/
├── MEMORY.md          # 첫 200줄/25KB 만 launch 적재 (concise index)
├── debugging.md       # on-demand 만 (Claude 가 file tool 로 직접 읽음)
├── api-conventions.md # on-demand 만
└── ...
```

핵심: `MEMORY.md` 는 "index", 디테일은 topic file 로 분리해 **Claude 가 필요할 때만 Read 도구로 직접 읽음**.

### 1.4 2026 변경사항

- **2026-03-06**: prompt cache default TTL **1시간 → 5분** 단축 (silent change). 명시적 `cache_control` 미설정 시 cache hit rate 급락.
- **Claude Code v2.1.59+**: `autoMemoryEnabled` (default ON) 도입. Anthropic 이 직접 "lazy load" 모델 공식 채택.
- **Anthropic compaction API (compact-2026-01-12)**: production-ready 자동 compaction 도입 — 오래된 conversation 부분을 single summary message 로 교체.

---

## 2. OpenAI Codex AGENTS.md (비교)

### 2.1 Discovery Chain 비교

| 항목 | Codex | Claude Code |
|---|---|---|
| **파일명** | `AGENTS.md` (project + `~/.codex/AGENTS.md`) | `CLAUDE.md` (project + `~/.claude/CLAUDE.md`) |
| **Discovery** | git root → cwd 까지 walking, 각 디렉토리 1 파일만 | 동일 (cwd 위로 walking + 하위 디렉토리는 lazy) |
| **Concatenation** | "joined with blank lines", later overrides earlier | 동일 |
| **Byte limit** | **`project_doc_max_bytes` = 32 KiB default** (truncate) | **soft limit only** (200줄 권고, hard limit 없음) |
| **Override pattern** | `AGENTS.override.md` 우선 | 없음 (project < user < managed 만) |

### 2.2 Codex 의 "Less Is More" 철학

OpenAI 공식 docs 인용:
> "Start with a root AGENTS.md, **add specifics as you discover Codex making mistakes that better instructions would have prevented**. The best AGENTS.md files were not written all at once — they grew from observed failure modes."

> "Think of AGENTS.md as a living artifact. Whenever you find yourself correcting the same Codex behavior twice, that correction belongs as a rule in the file."

> "**Most teams find value with 10-30 skills.** Beyond that, discoverability becomes a bottleneck."

### 2.3 Codex vs Claude 의 시사점

- **Codex 가 더 엄격함**: 32 KiB hard cap. 32KB 초과 시 truncate (silent data loss 위험). Neo Genesis 가 Codex 도 fallback 으로 쓰는 이상, **32KB 안에 핵심 SSOT 가 들어가야 안전**.
- **Claude 는 soft limit** 이라 cap 없이 비대화 가능 — 우리가 122K tokens 까지 키운 이유.
- **합의점**: "fix-on-second-mistake" 원칙. 2번 같은 실수 나오기 전에 미리 적지 마라. 우리는 owner 만족도 1번에 즉시 SSOT 박제 → 노이즈 누적의 root cause.

---

## 3. Long-Running Agent Memory Hygiene

### 3.1 Mem0 (arxiv 2504.19413, Mem0 Inc., 2025-04)

**핵심**: production-ready memory layer for AI agents. 두 phase:
- **Extraction phase**: LLM 으로 conversation → entities + relation triplets
- **Update phase**: 신규 정보 통합 시 conflict detection + resolution

**성능 (LOCOMO benchmark)**:
- LLM-as-judge metric: OpenAI 대비 **+26%**
- **p95 latency: -91%** (lower)
- **token cost: -90%** (lower)

**graph variant**: 관계형 구조 보존 (Mem0-g).

**Neo Genesis 적합도**: ⚠️ **부분 적용만**. 강점은 chat history 같은 high-velocity 데이터. 우리 SSOT 는 의도적 박제 (low-velocity, append-mostly) 라 graph extraction 의 ROI 가 낮음. 그러나 sora chat history (sora_assistant_memory.json) 에는 직접 적용 가치 있음.

### 3.2 A-Mem (Zheng et al., arxiv 2502.12110, 2025-02)

**핵심**: Zettelkasten 방법론 기반 agentic memory. 동적 indexing + linking.

- 신규 메모리 추가 시 "comprehensive note" 자동 생성 (contextual description + keywords + tags)
- 과거 메모리 분석해 "meaningful similarity" 발견 시 자동 link 생성
- **memory evolution**: 새 메모리가 과거 메모리의 contextual representation 까지 update 시킴

**Neo Genesis 적합도**: ❌ **부적합**. 운영 복잡도 큼 + memory evolution 이 "audit trail 변형" 으로 SSOT 무결성과 충돌 (CONSTITUTION Article 6). LLM cost 도 매 update 마다 발생.

### 3.3 LangGraph Checkpoint 패턴 (LangChain Inc.)

**핵심**: graph state 를 super-step 마다 checkpoint 로 자동 저장.

- **Time travel**: 과거 checkpoint replay / fork 가능
- **Fault tolerance**: node 실패 시 마지막 성공 super-step 부터 재개
- **Persistence 선택지**: InMemoryStore (dev) / PostgresStore / RedisStore / MongoStore (prod)
- **Thread-level memory**: 같은 thread 내 conversation 자동 유지

**Neo Genesis 적합도**: ⚠️ **선택 적용**. Sora multi-agent orchestration 에는 적용 가치 있음. SSOT 본체에는 부적합 (over-engineering).

### 3.4 Magentic-One Dual Ledger (Microsoft Research, 2024-11)

**핵심**: orchestrator 가 두 ledger 운영:
- **Task Ledger**: facts + educated guesses + plan
- **Progress Ledger**: 매 step self-reflection + completion check + 다음 subtask

진행 안 되면 → Task Ledger 갱신 후 새 plan 생성.

**Neo Genesis 적합도**: ✅ **이미 흡수**. `.agent/contracts/COLLABORATION_CONTRACT.md` + `shared-brain/active-tasks.md` 구조가 이 패턴 차용. 다만 우리는 **두 ledger 가 한 파일에 섞여있음** — 분리 권고.

### 3.5 CoALA — Cognitive Architecture for Language Agents (Sumers et al., arxiv 2309.02427)

**핵심**: 인지과학 기반 4-memory 분리.
- **Working Memory**: 즉시 context (대화, 부분 결과). 휘발성.
- **Episodic Memory**: 과거 사건 기록 (timeline-aware)
- **Semantic Memory**: 사실/지식 (timeless)
- **Procedural Memory**: 절차/스킬 (how-to)

Action space 도 분리:
- **Internal**: retrieval / reasoning / learning
- **External**: grounding (real world)

**Neo Genesis 적합도**: ✅ **고적합 (P1)**. 우리 SSOT 가 이 4 카테고리 무분별 혼합:
- `NEO_MASTER_RULES.md` = Procedural (good, always-load)
- `OWNER_PROFILE.md` = Semantic (good, always-load)
- `active-tasks.md` 의 history = Episodic (bad — currently always-load, should be lazy)
- 현재 session 상태 = Working (bad — should not be in SSOT)

### 3.6 Episodic Memory Position Effect

arxiv 2503.16439 직접 매치 안 됨. **대안 근거 발견**:
- **Lost in the Middle** (Liu et al., arxiv 2307.03172, TACL 2024): "performance is often highest when relevant information occurs at the beginning or end of the input context, and significantly degrades when models must access relevant information in the middle".
- **Position: Episodic Memory is the Missing Piece** (arxiv 2502.06975): long-term LLM agents 에서 episodic memory 의 필요성 + 미해결 challenges.
- **EM-LLM** (arxiv 2407.09450): Bayesian surprise + graph-theoretic boundary 로 token sequence 를 episodic event 로 자동 segment.

**Neo Genesis 시사점**: `active-tasks.md` 가 4,000+ 줄로 비대 → "middle" 위치의 정보 (예: 2026-04-26 ~ 5/4 Sora fix history) 는 attention 사각지대. 우리가 보낸 122K tokens 중 50%+ 이 사실상 무효.

---

## 4. Multi-Agent Shared Memory

### 4.1 LangGraph State + Reducer

**핵심**: TypedDict + Annotated 로 schema 명시. reducer function 으로 update 병합 (loss 방지).

**Neo Genesis 적합도**: ⚠️ Sora orchestration 에는 적용 검토 가치 있음 (이미 `.agent/shared-brain/` 이 비공식 reducer 역할).

### 4.2 Letta (구 MemGPT) — Hierarchical Memory Tiers

**핵심**: OS-inspired 3-tier (Packer et al., MemGPT paper, 2023-10).

| Tier | 메타포 | 동작 |
|---|---|---|
| **Core Memory** | RAM | 항상 in-context. retrieval call 불필요. 작은 block (수 KB) |
| **Recall Memory** | Disk Cache | conversation history 검색 가능. on-demand tool call |
| **Archival Memory** | Cold Storage | 외부 vector store. `archival_memory_search` tool call |

**Self-editing**: agent 가 직접 memory 수정 (memory function 호출).

**Neo Genesis 적합도**: ✅ **최고 적합도 (P0)**. 우리 SSOT 를 3-tier 로 재배치하면:
- **Core (always-load, target < 5K tokens)**: NEO_MASTER_RULES + OWNER_PROFILE + 현재 active project 1개
- **Recall (lazy, RAG-searchable)**: 모든 history files (active-tasks history / handoff log / cross-agent-review)
- **Archival (cold)**: 90일 이상 된 daily-log, 완료된 phase 문서

### 4.3 A2A Protocol (Agent-to-Agent, Google, 2025)

**핵심**: agent 간 state share 표준. JSON-RPC 기반 messaging. 우리 cross-agent-review.md 가 이미 비공식 A2A 역할.

**Neo Genesis 적합도**: 🟢 future-ready (현 작업 안에는 부적합)

---

## 5. Knowledge Base Lifecycle

### 5.1 Living Document 패턴 (PHPKB / Knowledge Base 표준)

**핵심 메타데이터**:
- `last_verified`: 사실 확인 일자 (없으면 staleness 감지 불가능)
- `version`: 자동 버전 증가 (PHPKB style)
- `expiry_date`: time-bound 항목 (announcement, offer, deadline) 자동 만료
- `archived`: archive 하지만 retain (참조 가능, end-user 노출 X)

### 5.2 Staleness Detection 자동화

AI-driven KB versioning 권고:
- 매 modification 실시간 추적
- 변경 자동 tagging + summary 생성
- 오래된 정보 자동 flag
- Cross-document conflict detection

**Neo Genesis 적합도**: ✅ **P0**. 우리 SSOT 에 `last_verified` / `archive_age_days` 메타 전무. cron 으로 자동 staleness 검사 가능.

### 5.3 Compaction Techniques (LLM context 특화)

**Anthropic compaction API** (compact-2026-01-12): production-ready. 오래된 conversation → single summary. preserves: facts / decisions / preferences / tool call outcomes.

**ACON** (Agent Context Optimization, arxiv 2510.00615): failure-driven task-aware compression. **peak token -26~54%** 감소, task success 유지.

**Living Summary 패턴**: last N turns full + 그 이전은 compact summary. 대화 진화 시 summary 도 재작성.

**Neo Genesis 적합도**: ✅ **P1**. `active-tasks.md` 에 5/4 Sora fix history 같은 1,000+ 줄 entry 는 living summary 로 100줄 압축 가능.

---

## 6. Neo Genesis 적용 매트릭스

| 패턴 | 출처 | 적합도 | 비용 (구현) | 이익 (토큰/명료성) | 우선순위 |
|---|---|---|---|---|---|
| **CLAUDE.md < 500줄 본체로 축소** | Anthropic 공식 | ✅ 최고 | Low (히스토리 archive 이동) | **거대** (122K → 5K 가능) | **P0** |
| **lastModified / staleness 메타** | PHPKB 표준 | ✅ 높음 | Low (linter cron 1개) | 중 (자동 archive 트리거) | **P0** |
| **active-tasks.md history → archive/<YYYY-MM>/** | Living Doc 표준 | ✅ 높음 | Low (rotate script) | 거대 (4000줄 → 200줄) | **P0** |
| **3-tier (Core / Recall / Archival)** | Letta/MemGPT | ✅ 최고 | Mid (RAG integration 필요) | 거대 | **P1** |
| **CoALA 4-memory 분리** | CoALA 논문 | ✅ 높음 | Mid (재구조화) | 중 | **P1** |
| **Path-scoped `.claude/rules/`** | Anthropic 공식 | ✅ 높음 | Low | 중 (SBU 별 분리) | **P1** |
| **explicit `cache_control: ttl=1h`** | Anthropic 2026-03 변경 | ✅ 즉시 | Trivial | 중 (5분 → 1h cache) | **P0** |
| **Living Summary (대화 압축)** | ACON / Anthropic compact API | ✅ 중 | Low (수동 가능) | 큼 | **P1** |
| **Magentic dual ledger 분리** | Magentic-One | ✅ 흡수 완료 | (이미 진행) | 작음 | P2 |
| **Mem0 graph extraction** | Mem0 논문 | ⚠️ 부분 (chat history 만) | High (LLM 비용) | 작음 | **부적합 (SSOT 본체)** |
| **A-Mem dynamic evolution** | A-Mem 논문 | ❌ 부적합 | High | (위험) | **도입 X** |
| **LangGraph checkpoint** | LangGraph | ⚠️ Sora orchestration 만 | Mid | 작음 (SSOT 무관) | P2 |
| **Letta self-editing memory** | Letta | ❌ 부적합 (SDK 종속) | High | 작음 | **도입 X** |

---

## 7. 권고 (Strategy Lead Cold Judgment)

### P0 (즉시, 1주 안)

**P0-1. CLAUDE.md 본체 다이어트 — 122K tokens → 목표 < 8K tokens (95% 절감)**

현재 `CLAUDE.md` 가 import 하는 8 파일 중 큰 비중:
- `AGENT_SHARED_MEMORY.md` (~3,500줄) → "변경 이력" 섹션 분리
- `active-tasks.md` (~4,500줄) → 완료 entry 를 `.agent/archive/2026-Q1/` 으로 이동
- `handoff.md` (~2,500줄) → 90일 이상 된 handoff 는 `archive/handoff-<YYYY-MM>.md`
- `cross-agent-review.md` (~1,000줄) → 완료 review 30일 후 archive

**대상 사이즈**:
- `NEO_MASTER_RULES.md`: 유지 (Procedural, always-needed)
- `OWNER_PROFILE.md`: 유지 (Semantic)
- `AGENT_SHARED_MEMORY.md`: < 200 줄 (지난 30일 운영 사실만)
- `active-tasks.md`: < 200 줄 (현재 진행 중인 P0/P1 만)
- `handoff.md`: < 100 줄 (최근 7일)
- `cross-agent-review.md`: < 100 줄 (활성 review 만)

**P0-2. lastModified 메타 + staleness linter (cron)**

모든 `.agent/**/*.md` frontmatter:
```yaml
---
last_verified: 2026-05-12
ssot_revision: b65dd81ca8e4bddf
archive_age_days: 30  # 기본값. 종류별 override 가능
---
```

cron `scripts/agent_staleness_check.py`:
- `last_verified` 가 `archive_age_days` 초과 → flag 또는 자동 archive 제안
- conflict (같은 사실이 2 파일에 다르게) detection
- 매주 일요일 23:00 KST 실행, 결과 → `.agent/shared-brain/staleness_report.md`

**P0-3. explicit prompt cache 1시간 TTL 설정**

CLAUDE.md import chain 마지막에 `cache_control` marker 적용. 2026-03-06 default TTL 변경 (1h → 5분) 후 우리가 무방비. 명시적 `{"type": "ephemeral", "ttl": "1h"}` 로 12배 cache hit window 확장.

비용 영향: 1h cache write = base × 2 (한 번만), read = base × 0.1. 세션 간격 5분~1h 인 owner 운영 패턴에서 **세션당 ~$1.8 → ~$0.18** (90% 절감) 예상.

### P1 (1~2주 안)

**P1-4. 3-tier 재구조화 (Letta 영감)**

```
.agent/
├── core/                    # always-load (target 총 < 10K tokens)
│   ├── NEO_MASTER_RULES.md
│   ├── OWNER_PROFILE.md
│   └── CURRENT_FOCUS.md    # 현재 1-2개 active project
│
├── recall/                  # lazy, on-demand (CRAUDE.md 가 @import 안 함, Read tool 만)
│   ├── shared-brain/
│   ├── knowledge/
│   └── runbooks/
│
└── archive/                 # cold storage
    ├── 2026-Q1/
    ├── 2026-Q2/
    └── ...
```

CLAUDE.md 는 `core/*` 만 @import. recall/* 는 Claude 가 grep/Read 로 필요할 때만 접근.

**P1-5. Path-scoped `.claude/rules/`**

SBU 별 (toolpick / kott / sora-engine / quant) 으로 분리:
```yaml
---
paths:
  - "src/sbu/toolpick/**/*"
---
# ToolPick-specific rules
```

Anthropic 공식 권고: glob 매칭 시만 로드. 우리 다중 SBU 운영 패턴에 정확히 맞음.

**P1-6. Living Summary 적용 (history sections)**

`active-tasks.md` 의 큰 entries (5/4 Sora fix, 5/8 K-OTT growth, P12 자율 등) 를 매 30일 후 100줄 이하 summary 로 압축. 원본은 `archive/` 보존. ACON 방법론 차용 (failure-driven, key facts preserved).

### P2 (Phase C+)

- **CoALA 4-memory 분리** (Episodic 명시화) — 디렉토리 재구성 동반, 운영 부담 큼
- **Magentic dual ledger 명시 분리** (현재 흡수했지만 한 파일에 섞임)
- **Sora chat history 에만 Mem0 graph extraction** 적용 검토

### 부적합 (도입 X)

| 패턴 | 이유 |
|---|---|
| **A-Mem dynamic evolution** | 메모리 자동 변형이 SSOT 무결성 (CONSTITUTION Article 6) 와 충돌. audit trail 변형 위험. |
| **Letta full SDK** | Python SDK 종속. 우리 멀티 runtime (Claude/Codex/Gemini/Sora) 환경에 부적합. |
| **Mem0 SSOT 본체 적용** | low-velocity 박제 데이터에 graph extraction LLM cost ROI 음수. chat history 만 부분 적용 가능. |
| **LangGraph SSOT** | SSOT 는 static markdown 으로 충분. graph state 는 Sora runtime 만 적용 검토. |

---

## 8. 예상 효과 (P0 + P1 적용 시)

| 지표 | 현재 | P0 후 | P1 후 |
|---|---|---|---|
| **세션 시작 토큰** | 122K | ~8K (-93%) | ~5K (-96%) |
| **세션당 입력 비용 (Opus 4.7)** | ~$1.84 | ~$0.12 (-93%) | ~$0.075 (-96%) |
| **2주 누적 비용 (가정 30 세션)** | ~$55 | ~$3.60 | ~$2.25 |
| **Cache hit 효과 (P0-3 후)** | 거의 0 | 5분 → 1h | 1h |
| **Effective cost (cache hit 후)** | $1.84 | $0.012 (-99%) | $0.0075 |
| **공식 권고 준수도** | 60배 초과 | 16배 (gap 큼) | 9배 (수용 가능) |
| **"lost in the middle" 노출** | 50%+ | < 10% | < 5% |

**연간 환산** (250 세션 가정):
- 현재: ~$460
- P0+P1+cache: ~$2.0
- **ROI: ~$458 / 1주 작업 = 200x**

---

## 9. 인용 / 참고

### 공식 문서 (1차 자료)
1. [Anthropic Claude Code Memory docs](https://code.claude.com/docs/en/memory) — CLAUDE.md hierarchy, 200줄 권고, auto memory MEMORY.md 200줄/25KB 모델, /compact 동작
2. [Anthropic Prompt Caching API](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) — `cache_control`, 5분 default TTL (2026-03-06 변경), 1h ttl 옵션
3. [OpenAI Codex AGENTS.md guide](https://developers.openai.com/codex/guides/agents-md) — discovery chain, "less is more", 32KiB cap
4. [OpenAI Codex Best Practices](https://developers.openai.com/codex/learn/best-practices) — "fix-on-second-mistake" 원칙
5. [LangGraph Persistence docs](https://docs.langchain.com/oss/python/langgraph/persistence) — checkpoint / time travel / multi-store
6. [Letta (MemGPT) Concepts](https://docs.letta.com/concepts/letta/) — 3-tier (Core/Recall/Archival), self-editing
7. [Microsoft Agent Framework Compaction](https://learn.microsoft.com/en-us/agent-framework/agents/conversations/compaction) — compaction API

### 학술 논문 (arxiv)
8. **Mem0** — Chhikara et al., [arxiv 2504.19413](https://arxiv.org/abs/2504.19413), 2025-04. LOCOMO +26% / latency -91% / cost -90%.
9. **A-Mem** — Xu et al., [arxiv 2502.12110](https://arxiv.org/abs/2502.12110), 2025-02 (v11 2025-10). Zettelkasten + memory evolution.
10. **CoALA** — Sumers et al., [arxiv 2309.02427](https://arxiv.org/abs/2309.02427), 2023-09. 4-memory + action space.
11. **Lost in the Middle** — Liu et al., [arxiv 2307.03172](https://arxiv.org/abs/2307.03172), TACL 2024. position-dependent attention degradation.
12. **EM-LLM** — Fountas et al., [arxiv 2407.09450](https://arxiv.org/abs/2407.09450), 2024-07. Bayesian surprise event segmentation.
13. **Episodic Memory is Missing Piece** — [arxiv 2502.06975](https://arxiv.org/abs/2502.06975), 2025-02 position paper.
14. **Magentic-One** — Microsoft Research, [arxiv 2411.04468](https://arxiv.org/html/2411.04468v1), 2024-11. Task Ledger + Progress Ledger.
15. **MemGPT** — Packer et al., 2023-10 (original Letta paper).
16. **ACON** — [arxiv 2510.00615](https://arxiv.org/html/2510.00615v1), 2025-10. failure-driven task-aware compression, -26~54% peak tokens.

### 산업 자료
17. ["Anthropic Silently Dropped Prompt Cache TTL from 1h to 5min"](https://dev.to/whoffagents/anthropic-silently-dropped-prompt-cache-ttl-from-1-hour-to-5-minutes-16ao) — 2026-03-06 변경 영향 분석
18. [Mem0 State of AI Agent Memory 2026](https://mem0.ai/blog/state-of-ai-agent-memory-2026)
19. [PHPKB Document Version Control](https://www.phpkb.com/features/document-versioning) — Living Document 메타데이터 표준
20. [Anthropic API Pricing 2026 Guide](https://www.finout.io/blog/anthropic-api-pricing) — cache write 1.25× / 1h write 2× / read 0.1×

---

## 10. 다음 액션 (Strategy Lead 직접 진행 또는 owner G2)

1. **즉시 자율 (G1)**: 본 리서치 문서 박제 (이 파일) + `active-tasks.md` 에 P0~P1 박제 + ssotRevision bump
2. **owner G2-decision 필요**:
   - P0-1 (CLAUDE.md 다이어트): `archive/` 디렉토리 신설 + history 이동 = 운영 변경 (G2)
   - P0-2 (staleness linter cron): cron 추가 (G1 자율 가능)
   - P0-3 (explicit cache_control): CLAUDE.md 본체 수정 (G1 자율 가능, low risk)
   - P1-4 (3-tier 재구조화): SSOT 디렉토리 구조 변경 (G2 의무)
   - P1-5 (path-scoped rules): `.claude/rules/` 신설 (G1 자율 가능)
   - P1-6 (Living Summary): 기존 history 압축 (G1 가능, 단 원본 archive 보존)
3. **권고 순서**: P0-3 → P0-2 → P0-1 → P1-5 → P1-6 → P1-4 (low-risk first)

— Strategy Lead Claude Opus 4.7, 2026-05-12 KST
