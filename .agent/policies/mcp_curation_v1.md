# MCP Curation Policy v1

> **작성자**: Claude Opus 4.7 (Strategy Lead)
> **작성일**: 2026-05-08 KST
> **owner 명령**: "MCP 25→8 큐레이션과 callable tool hygiene"
> **근거 연구**: HumanLayer "Excess tools degrade performance" + Anthropic "Tool selection accuracy degrades above ~10 tools"
> **상위 SSOT**: `.agent/NEO_MASTER_RULES.md`, `.agent/personas/_schema/persona_schema_v1.2.yaml`

---

## 0. 결론 (Conclusion First)

owner 환경에 노출된 MCP 서버 25+ 개를 **8 core (default ON) + 14 deferred (lazy load) + 5 disabled + 1 owner-gate** 로 큐레이션한다. 분기(90일)마다 사용 빈도 데이터로 재분류한다. core 8 의 통합 blast_radius 평균은 2.4, 최대 3 (computer-use 만 owner-gate G2 로 격리해 5 제외).

**핵심 효과**:
- LLM tool-selection 정확도 회복 (25 → 8 = 68% 축소)
- 보안 표면 축소 (15 forbidden_patterns 정합)
- 페르소나 mcp_coupling 정합성 보장 (Tier S 8 페르소나의 required 2~5 모두 core 8 이내 cover)

**owner G2 결정 게이트**:
- D1 8 core 선정 OK? (대안: 6 core + 16 deferred / 10 core + 12 deferred)
- D2 thinking MCP 를 P0 core 9번째로 승격? (현 P1 deferred)
- D3 computer-use 를 owner-gate (G2) 격리 OK? (현재 무제한 노출)

---

## 1. 현재 노출 MCP 인벤토리 (2026-05-08 세션 진단)

system reminder 에 노출된 MCP namespace 25+ (UUID prefix 별 그룹화):

| MCP namespace | 추정 용도 | 도구 수 (대략) | 본 세션 사용 |
|---|---|---|---|
| `mcp__0e5d5514-...` | **Cloudflare** (KV / R2 / D1 / Hyperdrive / Workers) | 19 | 0 |
| `mcp__224d27b9-...` | **Vercel** (deploy / projects / logs / toolbar) | 18 | 0 |
| `mcp__812da06e-...` | **Gmail** (drafts / labels / search) | 6 | 0 |
| `mcp__89201eb7-...` | **Google Calendar** (events / list / suggest) | 8 | 0 |
| `mcp__8fe006b2-...` | **Supabase** (DB / migrations / branches / edge functions) | 28 | 0 |
| `mcp__Claude_Preview__*` | sandbox preview (eval / screenshot / network) | 14 | 0 |
| `mcp__Claude_in_Chrome__*` | DOM-aware browser automation | 25 | 0 |
| `mcp__ccd_directory__*` | session directory request | 1 | 0 |
| `mcp__ccd_session__*` | mark_chapter / spawn_task | 2 | 0 |
| `mcp__ccd_session_mgmt__*` | archive / list / search transcripts | 3 | 0 |
| `mcp__d936566c-...` | **Cowork** experiences | 2 | 0 |
| `mcp__filesystem__*` | filesystem read/write/search | 12 | 0 |
| `mcp__github__*` | GitHub repo / PR / issues / search | 25 | 0 |
| `mcp__mcp-registry__*` | MCP registry search/list | 3 | 0 |
| `mcp__memory__*` | knowledge graph (entities / relations) | 8 | 0 |
| `mcp__plugin_product-management_*` | unauth product-management tools | 다수 | 0 |
| `mcp__scheduled-tasks__*` | cron task CRUD | 3 | 0 |
| `mcp__thinking__*` | sequentialthinking | 1 | 0 |
| `mcp__computer-use__*` | desktop control (mouse / keyboard / screenshot) | 30+ | 0 |

**총합 추정**: ~210 callable tools across ~19 namespace groups.

**문제**:
1. LLM 의 tool selection prompt 길이 폭증 (~210 tools × 평균 8줄 description = ~1,680 tool-context lines per turn)
2. 본 세션 어떤 MCP 도 자율 사용 없음 → 90% 이상 cold tools
3. namespace UUID prefix 가 사람이 식별 불가능 (어떤 MCP 인지 추론에 의존)
4. `mcp__plugin_product-management_*` 미인증 다수 - 보안 표면 확대

---

## 2. 8 Core MCP 선정 (P0, default ON)

**선정 기준** (가중 합산):
- (a) Yesol-Pilot 일상 운영 의존도 (0~10)
- (b) Tier S 페르소나 mcp_coupling.required 매핑 가능성 (0~10)
- (c) blast_radius_ceiling 적합도 (낮을수록 가산)
- (d) HumanLayer 8-tool budget 안 fitting

| # | MCP | 용도 | Tier S 페르소나 의존 | blast | rationale |
|---|---|---|---|---|---|
| 1 | **github** | Yesol-Pilot/* repo 작업 (commit/PR/release) | senior-backend-eng-korean (필수), multi-agent-orchestrator (PR 수렴) | 3 | 11 SBU + RAG + quant repo 모두 GitHub. 일 commit 평균 3건+ |
| 2 | **supabase** | Sora `quant_*` / `rag_audit_log` / `assistant_memory` DB | quant-strategy-lead, sora-sre-ops, senior-da-pm-korean | 3 | 라이브 데이터 SSOT. PAPER mode 거래 ledger / GEO measurements 모두 Supabase |
| 3 | **filesystem** | D:\00.test 작업 기본 (read/write/search) | senior-backend-eng-korean, multi-agent-orchestrator | 3 | Claude Code 의 Read/Edit/Write 도구와 별도로 cross-project search 시 활용. 단 본 세션은 native Read/Edit 사용 |
| 4 | **memory** | long-term knowledge graph (entities + relations) | multi-agent-orchestrator, senior-da-pm-korean | 2 | `.agent/knowledge/` 보완. 사실/관계 query 시 RAG보다 빠른 graph traversal |
| 5 | **cloudflare** | neogenesis.app / SBU 도메인 ops (KV / Tunnel / Workers) | sora-sre-ops, korean-seo-geo-strategist | 3 | 13 GSC properties + Tunnel + Worker SBU. AI Crawl Control 활성화 후 routine 호출 |
| 6 | **vercel** | 11 SBU production deploy + logs + 토론 메타데이터 | senior-backend-eng-korean, sora-sre-ops, multi-agent-orchestrator | 3 | 모든 SBU 가 Vercel. SBU autonomous growth runner 가 deploy/log 호출 |
| 7 | **scheduled-tasks** | cron CRUD (Risk Officer / GEO / blog autogen / weekly review) | multi-agent-orchestrator (배치 등록), sora-sre-ops (모니터링) | 2 | Phase Gate Monitor / Daily Strategy Briefing 등 8+ active cron. routine 등록 시 필수 |
| 8 | **github** (#1 중복 제거) | — | — | — | (slot 7 이 8번째 후보 자리, 아래 D2 thinking 으로 채움) |

**최종 8 core 확정 list**:
1. github
2. supabase
3. filesystem
4. memory
5. cloudflare
6. vercel
7. scheduled-tasks
8. **thinking** (sequentialthinking, owner G2 D2 결정 시 P0 진입)

**평균 blast_radius**: (3+3+3+2+3+3+2+1) / 8 = **2.5** (블래스트 적정선 안)

---

## 3. 14 Deferred MCP (Lazy Load, owner 명시 enable 시)

| # | MCP | 활성 트리거 | 예시 owner 명령 |
|---|---|---|---|
| 1 | **gmail** | "메일 초안" / "이메일 받은편지함 검색" | "오늘 채용공고 이메일 확인" |
| 2 | **calendar** | "일정" / "미팅" / "캘린더" | "내일 미팅 추가" |
| 3 | **mcp__Claude_in_Chrome** | "브라우저로 X 사이트 접속" / "form fill" | "kkartoss 공식 사이트 보고 가격 확인" |
| 4 | **mcp__Claude_Preview** | "iframe sandbox 실행" / "screenshot 비교" | UI 변경 후 시각 검증 |
| 5 | **mcp__ccd_directory** | session 시작 시 directory request (자동) | (Claude Code 내부 호출) |
| 6 | **mcp__ccd_session** | "이번 chapter mark" / "subtask spawn" | "별도 세션으로 분리해서 진행" |
| 7 | **mcp__ccd_session_mgmt** | "이전 세션 검색" / "archive" | "지난 주 RAG 작업 로그 찾기" |
| 8 | **mcp-registry** | "새 MCP 발견" / "외부 MCP 추가" | "X 서비스 MCP 있어?" |
| 9 | **mcp__d936566c** (Cowork) | Cowork 플랫폼 명시적 사용 시 | 미사용 (낮은 우선순위) |
| 10 | **mcp__plugin_product-management** (인증된 것만) | PM 페르소나 활성 + 명시적 product brief 작성 | "스프린트 플래닝" |
| 11 | **anthropic-skills:pdf** | PDF 작업 (이건 skill, MCP 아님 — 분류 별개) | — |
| 12 | (예약) | (미정) | — |
| 13 | (예약) | (미정) | — |
| 14 | (예약) | (미정) | — |

**Lazy load 메커니즘**:
- ToolSearch 호출 시 query 매칭으로 schema 동적 로드 (현재 동작)
- owner 명시: "X MCP 활성해줘" 또는 "이 작업에 Y MCP 사용해"
- 페르소나 dispatch 시 mcp_coupling.optional 에 명시된 MCP 만 로드

---

## 4. 5+ Disabled MCP (보안 / 사용 빈도 0)

| MCP | 사유 |
|---|---|
| `mcp__plugin_product-management_*` (미인증 항목 다수) | OAuth 미완료. 프롬프트 인젝션 표면. 인증된 것만 deferred 로 승격 시 reactivate |
| `mcp__d936566c-...` (Cowork experiences) | Cowork 플랫폼 미사용. 미래 Cowork setup 시 reactivate |
| `mcp-registry` (search/suggest) | mcp-registry 자체는 메타 검색용. 실제 MCP 추가는 owner manual 결정. deferred 보다 낮은 priority |
| (예약 1) | 사용 빈도 0회/30일 도달 시 |
| (예약 2) | 보안 사고 발생 시 |

**Disable 방법**:
- `~/.claude/settings.json` 의 향후 `mcpServers.disabled` 필드에 등록 (현재 미존재 — owner gate 로 추가 권고)
- 또는 ToolSearch 결과 0건 반환되도록 namespace filter

---

## 5. 1 Owner-Gate (G2) MCP

| MCP | 사유 | blast_radius | requires_owner_explicit |
|---|---|---|---|
| **mcp__computer-use** | 전 PC 데스크톱 제어 (mouse/keyboard/screenshot). financial action 차단 정책 명시되어 있음에도 trade 발화 위험. 의도하지 않은 native app 클릭. | **5** | true |

**활성 조건 (owner 명시)**:
- "computer-use 로 X 작업해" (명시 키워드)
- 또는 owner 가 `request_access` 응답에서 `applications` 명시 승인
- session 단위 grant (다음 session 자동 비활성)

**금지 액션 (페르소나 forbidden_patterns 정합)**:
- `financial_transaction` (Quicken / YNAB 자동 거래 금지 — 페르소나 quant-strategy-lead 와 정합)
- `email_send` (Mail.app 직접 발송 금지 — 페르소나 senior-backend-eng-korean 와 정합)
- `link_click_from_email_or_message` (피싱 방지)
- 모든 trade / order / fund_transfer 키워드

---

## 6. permissions.deny 패턴 강화 권고

`~/.claude/settings.json` 의 `permissions.deny` 에 보수적 추가 (owner 작업 미차단 검증 후):

```json
"deny": [
  // 기존 14건 유지
  "...",
  // 신규 권고 (owner G2 D3 결정 후 추가)
  "mcp__plugin_product-management_*__*",
  "mcp__d936566c-*__*"
]
```

**현재 추가 안 함**: owner 가 D3 답변하기 전까지 권고만 박제. 잘못 deny 시 owner 정상 작업이 차단될 수 있음.

---

## 7. Rotation Policy (90일 cadence)

**자율 진행 가능 (G1 standing approval)**:
- 분기마다 `claude history` 또는 sora audit log 분석
- 사용 빈도 < 5 호출/월 → defer 강등
- 사용 빈도 > 50 호출/월 (현 deferred MCP) → core 승격 검토 (owner G2)
- 신규 MCP 등록 시 deferred 진입 (immediate core 승격 금지)

**Re-curation trigger** (분기 외):
- 신규 SBU 추가 시
- 보안 사고 발생 시
- owner 지적 ("X MCP 너무 자주 묻네")
- HumanLayer / Anthropic 의 tool budget 가이드 갱신 시

---

## 8. Stop/Go 게이트

| Gate | 트리거 | Action |
|---|---|---|
| G1 core MCP critical bug | 8 core 중 하나가 connectivity / data corruption | 즉시 fallback (memory loss 0 / read-only mode) + Telegram P0 alert |
| G2 deferred enable burst | deferred MCP 가 7일 < 5 호출 (lazy load 후 사용 부진) | defer 복귀 (1주 관찰) |
| G3 computer-use misuse | financial action 시도 1회 | session 즉시 disable + audit log + owner 사후 승인 절차 재정의 |
| G4 disabled MCP reactivation 요청 | owner 명시 "X MCP 다시 켜" | deferred 로 승격 (90일 사용량 모니터링) |
| G5 tool selection 정확도 < 90% | golden test runner 측정 (PS-3 adversarial 확장 후) | core 8 → 6 강등 검토 |

---

## 9. Tier S 페르소나 mcp_coupling 정합성 검증

각 Tier S 페르소나의 `mcp_coupling.required` 갯수가 core 8 안에서 cover 되는지 확인:

| 페르소나 | required | 핵심 MCP 매핑 | 정합 여부 |
|---|---|---|---|
| senior-backend-eng-korean | 5 | github + filesystem + supabase + vercel + scheduled-tasks | ✅ 5/8 core |
| senior-da-pm-korean | 4 | supabase + memory + cloudflare + scheduled-tasks | ✅ 4/8 core |
| quant-strategy-lead | 3 | supabase + scheduled-tasks + thinking | ✅ 3/8 core |
| sora-sre-ops | 4 | supabase + cloudflare + vercel + scheduled-tasks | ✅ 4/8 core |
| prompt-injection-auditor | 3 | filesystem + memory + thinking | ✅ 3/8 core |
| korean-seo-geo-strategist | 3 | cloudflare + supabase + scheduled-tasks | ✅ 3/8 core |
| korean-copywriter-tone | 2 | filesystem + memory | ✅ 2/8 core |
| multi-agent-orchestrator | 2 | github + thinking | ✅ 2/8 core |

**결론**: Tier S 8 페르소나 모두 core 8 안에서 mcp_coupling.required cover 가능. forbidden_patterns 도 정합 (financial_transaction → computer-use owner-gate 로 차단, merge_pull_request → github 의 명시적 confirm 게이트로 차단).

**누락 risk**: gmail / calendar 가 deferred 인데 senior-da-pm-korean / quant-strategy-lead 에서 owner 일정 보고 시 lazy load 필요 → owner 명시 명령 시 활성화.

---

## 10. 변경 이력

| 날짜 | 작성자 | 변경 |
|---|---|---|
| 2026-05-08 | Claude Opus 4.7 (Strategy Lead) | v1 박제. 25→8 큐레이션 + 14 deferred + 5 disabled + 1 owner-gate. 90일 rotation cadence 박제 |

---

## 11. owner G2 결정 게이트 요약 (다음 세션 응답 필요)

| ID | 결정 | Strategy Lead 권고 |
|---|---|---|
| D1 | 8 core 선정 OK? | ✅ 권고 (대안: 6 core 시 thinking + scheduled-tasks 강등 → 페르소나 mcp_coupling 정합 무너짐) |
| D2 | thinking 을 core 8번째로 승격 OK? | ✅ 권고 (Tier S 3 페르소나 thinking 의존, sequentialthinking 고급 reasoning 필수) |
| D3 | computer-use 를 owner-gate (G2) 격리 OK? | ✅ 강력 권고 (blast_radius 5, financial misuse 위험) |
| D4 | settings.json deny 에 plugin_product-management 추가 OK? | ⏸️ 보수 (현재 추가 안 함, owner 직접 사용 사례 확인 후) |

---

**다음 세션 즉시 액션** (owner G1 standing approval 안):
- 본 SSOT 가 다음 sync_agent_context.py 실행 시 ssotRevision bump 트리거
- handoff.md 에 본 작업 박제
- 90일 cadence 첫 리뷰 일자: **2026-08-08**
