# Phase A Closure + Phase B Launch v1

> **작성:** 2026-05-10, Strategy Lead Claude Opus 4.7
> **목적:** Persona Library v1.2 Phase A 종결 + Phase B 진입 SSOT 박제
> **선행 SSOT:** `.agent/personas/INDEX.md`, `.agent/personas/_schema/persona_schema_v1.2.yaml`, `.agent/policies/persona_safety.yaml`, `.agent/policies/mcp_curation_v1.md`
> **owner 명령 흐름:** "전부 병렬진행해" → "전부 진행해 그리고 에이전트들이 에이전트 호출 시 활용안하고 있는거 같네" → "계속해"

---

## 결론 (Cold Honest)

Phase A 는 27 task 계획 → 40+ 완료 (**150% 오버 달성**). 32/32 페르소나 valid + Claude Code subagent surface 라이브 wiring + 9 hooks + 180 adversarial cases + MCP 8 core 큐레이션. Phase B 진입 가능. owner G2 결정 5건만 응답 받으면 P1 자율 unblock.

가장 큰 발견: 직전 세션의 Wiring 갭. 32 v1.2 페르소나가 `.agent/personas/tier-*/` 에 있어도 Claude Code Agent tool 은 `~/.claude/agents/*.md` frontmatter `name` 만 인식. owner 지적 ("에이전트들이 에이전트 호출 시 활용안하고 있는거 같네") 직접 반응으로 Generator + 32 mirror agents 박제 완료.

---

## Phase A 누적 산출 매트릭스

| 카테고리 | 파일 수 | 라이브 검증 |
|---|---|---|
| v1.2 Schema (persona_schema + framework_mapping) | 2 | constitutional_injector 32/32 valid |
| Tier S 페르소나 | 8 | 8/8 OK |
| Tier A 페르소나 | 9 | 9/9 OK |
| Tier B 페르소나 | 10 | 10/10 OK |
| Tier C 페르소나 (minimal enforcement) | 5 | 5/5 OK |
| Dispatcher infra (dispatcher.py / injector.py / keyword_rules.yaml / persona_safety.yaml) | 4 | live test PASS (G2 detect + L2 routing) |
| Claude Code subagents (~/.claude/agents/) | 32 generated + 4 reserved | 36 active agents 박제 (subagent_type 호출 가능) |
| Generator (scripts/persona/generate_claude_agents.py) | 1 | idempotent / dry-run / verbose / backup / force 옵션 검증 |
| Hooks (PowerShell ~/.claude/hooks/) | 9 (5 기존 + 4 신규) | 20/20 regression PASS |
| Adversarial suite (tests/sora_adversarial/persona_v1.json) | 180 cases | JSON contract 박제 (5/5 contract PASS) |
| Hook regression test (tests/hooks_golden/core_v1.json + runner) | 20 cases + 1 runner | 20/20 PASS |
| PT-1 caching SSOT (`persona_caching_*.md` 2 docs + 5 페르소나 보강) | 7 | $32/월 절감 추정 |
| MCP curation (mcp_curation_v1.md + mcp_tool_policy.yaml) | 2 | 8 core / 16 deferred / 5 disabled / 1 owner-gate |
| 운영 fix (sync + handoff + active-tasks) | 3 | ssotRevision bump 트리거 (다음 sync 시) |

---

## G2 자율 결정 박제 (4건)

### G2-1 (직전 세션, persona_schema_v1.2)
- **결정:** citation_required = persona별 차등 (Tier S: 4 ON / 3 OFF / 1 HYBRID)
- **근거:** blanket ON 시 over-caution + creative tone 페르소나(copywriter) 마비. fact 기반 페르소나만 강제.

### G2-2 (직전 세션, persona_schema_v1.2)
- **결정:** pre_mortem = `blast_radius_ceiling >= 3` 자동 ON
- **근거:** trivial fix(regex / commit message) 노이즈 회피.

### G2-3 (직전 세션, Tier C 정책)
- **결정:** Tier C v1.2 schema 적용 + enforcement 최소화 (citation OFF / pre_mortem OFF / blast_radius 1)
- **근거:** Tier C는 정적 보조 도구. framework 비용 대비 효과 낮음.

### G2-4 (이번 세션, validation gate)
- **결정:** `python scripts/persona/constitutional_injector.py --validate-all` must return 32/32 valid before runtime adapter sync (sync_agent_context.py 실행 전제 조건)
- **근거:** drift 차단 + Phase A → B 진입 게이트화

---

## owner G2 결정 대기 매트릭스 (5건)

| ID | 결정 | Strategy Lead 권고 | 자율 진행 차단 영역 | 영향 |
|---|---|---|---|---|
| D1 | PT-1 Tier S 5 페르소나 prompt caching 적용 | ✅ ACCEPT (Sora engine path 한정, $32/월 절감) | 실 코드 변경 (sora_engine.py prompt prefix) | latency p50 -2~4s 추정 |
| D2 | MCP 8 core 선정 OK? | ✅ ACCEPT (github / supabase / filesystem / memory / cloudflare / vercel / scheduled-tasks / thinking) | settings.json deny pattern 수정 | tool surface 25→8 |
| D3 | thinking core 승격 OK? | ✅ ACCEPT (Tier S 3 페르소나 mcp_coupling.required 의존) | settings.json | sequentialthinking 가용 |
| D4 | computer-use owner-gate 격리 OK? | ✅ STRONG ACCEPT (blast 5, financial action / unauthorized email_send / link_click_from_email 위험) | settings.json deny pattern + session 단위 grant | 보안 |
| D5 | plugin_product-management deny 추가 | ⏸️ DEFER (실 사용 사례 1주 모니터링 후 결정) | settings.json deny | 회피 |

owner 결정 후 자율 진행 가능. **결정 없으면 운영 영향 0건** (현 상태 안정).

---

## Phase B 우선순위 매트릭스

### P0 (즉시, 자율 가능 — owner 결정 무관)
1. **Live routing audit aggregator** — `~/.claude/audit/persona_routing_*.jsonl` 누적 분석 → 실제 어떤 페르소나가 라우팅되는지 통계 + 오라우팅 비율 + fallback rate 측정
2. **CLAUDE_AUDIT_DIR env 통합 (9 hooks 일괄)** — test isolation 활성화 (현재 production 디렉토리 hardcoded)
3. **Dispatcher Layer 3 (KURE-v1 cosine)** — embedding cosine 라이브 (Phase B 핵심 — 직전 세션의 stub 구현 부분)
4. **Adversarial 180 live harness** — JSON contract → 실 호출 검증 (P0 보안, 현재는 contract gate 까지만)

### P1 (1-2 주, owner G2 결정 후)
5. **MCP 8 core 적용** (owner D2/D3 결정 후) — settings.json 패치 + computer-use deny 추가
6. **PT-1 caching 실 적용** (owner D1 결정 후) — Sora engine prompt prefix 통합
7. **Hook regression CI 자동 trigger** (Windows runner ROI 검토 후) — github actions 매트릭스
8. **Persona library v1.2 → v1.3 design** (Phase B 진입 시 신 학습 반영, 라이브 routing audit 결과 의존)

### P2 (Phase C, 별도 design 필요)
9. **MCP server publishing** — Anthropic MCP registry 진입 (Neo Genesis own MCP server)
10. **arXiv preprint submission** (EthicaAI / WhyLab) — owner action 5분 작업 (separate task track)
11. **Wikipedia notability** — Q3-Q4 2026 (third-party citation 누적 후, WP:NBIO/WP:NCORP gate)

---

## Stop/Go 게이트 (Phase B 진입)

- **Stop**: 32 페르소나 중 1건이라도 invalid → 즉시 차단 + cold review (current: 32/32 valid ✅)
- **Go**: 32/32 valid + 9 hooks 정상 + dispatcher 라이브 + Claude Code subagent surface 활성 → Phase B 진입 (현재 충족)
- **Pause**: live routing audit 결과 fallback rate > 50% → dispatcher 정합성 재진단 (P0-1 작업의 입력)

---

## 알려진 한계 (별도 task 로 closure 가능)

1. **PowerShell stdin 한국어 mojibake** — 영문 키워드 query는 정상. cosmetic only, 라우팅 로직 영향 없음
2. **audit log 격리 미구현** → CLAUDE_AUDIT_DIR env 통합 별도 task (P0-2)
3. **Adversarial JSON contract 만** → live execution harness 별도 task (P0-4)
4. **KURE-v1 dispatcher Layer 3 stub** → 별도 task (P0-3, Phase B 핵심)
5. **Hook CI Windows runner 가격 미검토** — github actions Windows minute cost 분석 필요 (P1-7)
6. **MCP 8 core 적용 보류** — owner D1~D4 결정 후 settings.json 패치 (P1-5/6)

---

## 변경 이력

- **2026-05-08**: Phase A 시작 (27 task 계획)
- **2026-05-08 ~ 2026-05-10 (3일)**: 11 병렬 에이전트 누적 (1차 6 + 2차 5)
  - 1차 (5/8): v1.2 schema + Tier S 8 페르소나 + dispatcher infra + injector
  - 2차 (5/8 후속): Tier A 9 + Tier B 10 + Tier C 5 (minimal)
  - 3차 (5/8 evening): adversarial 180 cases JSON contract + hook regression 20 + Tier C runner
  - 4차 (5/9): Wiring fix Generator + 32 Claude Code subagents
  - 5차 (5/9~10): PT-1 caching SSOT + MCP 25→8 curation + ASUS/etribe Tailscale rollout (blocked)
  - 6차 (5/10): Phase A 150% 오버 달성 + Phase B 진입 SSOT 박제 (이 문서)
- **2026-05-10**: Phase A → B 진입 SSOT 박제 + ssotRevision bump 트리거 (다음 sync_agent_context.py 실행 시)

---

## 다음 세션 즉시 액션

1. **owner G2 결정 5건 응답 받기** (D1-D5)
2. **Phase B P0 작업 진행** (live routing audit / CLAUDE_AUDIT_DIR / KURE-v1 dispatcher Layer 3 / Adversarial 180 live harness)
3. **첫 라이브 owner 명령 시 dispatcher surface 확인** + audit log 24-48h 누적 분석 → P0-1 aggregator 입력 데이터 확보
4. owner 결정 도착 시 P1 자율 진행 unblock

---

👤 Strategy Lead Claude Opus 4.7
