# SSOT Tier 분류 매트릭스 v1

> 작성: 2026-05-12, Strategy Lead (Claude Opus 4.7)
> 분류 대상: `D:/00.test/neo-genesis/.agent/` 전체
> 자동화: `scripts/agent/classify_ssot.py` 실행 결과
> 원본 데이터: `.agent/registries/tier_classification.yaml` + `.json`

---

## 0. 결론 (요약)

- **현 SSOT 적재량 진단**: `.agent/` 154 파일 / 3.03MB / 추정 1.26M tokens (full scan)
- **현 자동 적재 (Tier 1+2 sum)**: 약 **266K tokens / $4.0 per session**
- **권고 자동 적재 (Tier 1 의 active section + status only, 30%)**: 약 **56K tokens / $0.85 per session**
- **세션당 절감 추정**: **−210K tokens / −$3.15** = **약 −79%**
- **월 30세션 추정 절감**: **약 $94/월** (Opus 4.7 input 단가 기준)
- **핵심 발견 2건**:
  1. `shared-brain/active-tasks.md` (260KB / ~107K tokens) + `handoff.md` (120KB / ~49K tokens) 가 **현 자동 적재 토큰의 60% 이상**을 차지. 분할 필수.
  2. `daily-log.md` (271KB) 는 append-only 사후 분석용으로 **Tier 4 (archive)** 가 적합. 현재 import chain 에 직접 포함되지 않으나 `@import` 추가 시 큰 손실. 영구 차단 권장.

| Tier | 정의 | 파일 수 | 합계 tokens | 적재 정책 |
| --- | --- | ---: | ---: | --- |
| **Tier 1 CRITICAL** | 매 세션 자동 적재 필수 | 7 | 187,922 | `@import` (자동) |
| **Tier 2 IMPORTANT** | 필요 시 lazy load 권장 | 19 | 78,476 | `@import` 제거, 명시 Read |
| **Tier 3 REFERENCE** | RAG 또는 명시 Read 요청 시만 | 99 | 785,907 | RAG indexing |
| **Tier 4 ARCHIVE** | 보존 only, 미적재 | 29 | 206,464 | 적재 금지 (split / 격리) |

---

## 1. Tier 정의

### Tier 1 — CRITICAL (자동 적재 필수)
- **범위**: 규칙 SSOT + live state + active section 만
- **이유**: 세션 시작 즉시 결정 기준이 되며, 미적재 시 안전/운영 사고 직결
- **적재 정책**: `CLAUDE.md` 의 `@import` chain 에 직접 포함
- **캐시 권고**: Anthropic 5분 ephemeral prompt caching (`cache_control: ephemeral`) — 동일 세션 내 재호출 비용 90% 절감
- **변경 빈도**: 일 수 회 (live state 는 매 응답)

### Tier 2 — IMPORTANT (lazy load 권장)
- **범위**: 장기 메모리 / 정책 YAML / 운영 contract / 비상 runbook / persona safety
- **이유**: 매 세션 필요하지 않음. 작업 성격이 해당 영역일 때만 호출
- **적재 정책**: `@import` 제거. 명시 Read 또는 RAG 검색
- **캐시 권고**: 1시간 cache (`cache_control: 1h ttl`) — 변경 빈도 낮음
- **변경 빈도**: 주 수 회

### Tier 3 — REFERENCE (RAG / 명시 Read)
- **범위**: 연구 보고서 / persona body / deep design / wiki draft / cross-publish 원고
- **이유**: 특정 작업 컨텍스트에서만 가치. 평소 적재는 노이즈
- **적재 정책**: Qdrant `neo_ssot` 컬렉션에 인덱스. RAG 검색 또는 owner Read 명시
- **캐시 권고**: cache 없음 (RAG 검색 결과만 caching)
- **변경 빈도**: 월 수 회

### Tier 4 — ARCHIVE (보존 only)
- **범위**: 30일+ stale / 완료된 task / append-only log / backup / eval-runs
- **이유**: LLM 적재 가치 0. 보존만 필요 (감사 / 사후 분석)
- **적재 정책**: **적재 금지**. archive 디렉토리 분리 권장 (`.agent/archive/`)
- **캐시 권고**: exempt
- **변경 빈도**: 0 (immutable) 또는 append-only

---

## 2. Tier 1 — CRITICAL (7 파일 / 188K tokens)

| 파일 | 크기 | 마지막 수정 | 사유 | 비고 |
| --- | ---: | ---: | --- | --- |
| `shared-brain/active-tasks.md` | 260.2KB | 0.0d | active task ledger | **분할 필수** (active section 만 T1, completed 는 T4) |
| `shared-brain/handoff.md` | 120.4KB | 0.0d | 세션 인수인계 | **분할 필수** (최근 7일치만 T1) |
| `shared-brain/cross-agent-review.md` | 38.7KB | 1.2d | cross-agent queue | 분할 권고 (active 만 T1) |
| `NEO_MASTER_RULES.md` | 32.6KB | 1.7d | 규칙 SSOT | 변경 없음 |
| `shared-brain/device_inventory.json` | 3.2KB | 1.1d | fleet live state | 변경 없음 |
| `shared-brain/status.json` | 2.3KB | 0.0d | runtime live state | 변경 없음 |
| `shared-brain/device_heartbeats.json` | 1.3KB | 1.1d | fleet heartbeats | 변경 없음 |

**Tier 1 split 권고 (3 파일)**:
- `active-tasks.md` → `active-tasks.md` (active section, ~30% = ~78KB) + `archive/active-tasks-completed-YYYY-MM.md`
- `handoff.md` → `handoff.md` (최근 7일, ~30% = ~36KB) + `archive/handoff-YYYY-MM.md`
- `cross-agent-review.md` → `cross-agent-review.md` (active queue) + `archive/cross-agent-completed-YYYY-MM.md`

---

## 3. Tier 2 — IMPORTANT (19 파일 / 78K tokens)

| 파일 | 크기 | 마지막 수정 | 사유 |
| --- | ---: | ---: | --- |
| `BIBLE.md` | 26.2KB | 1.2d | 운영 참고서 |
| `knowledge/AGENT_SHARED_MEMORY.md` | 22.9KB | 0.1d | 장기 메모리 |
| `contracts/GRILL_TOAST_PROTOCOL.md` | 21.8KB | 6.2d | 적대적 자기검증 contract |
| `policies/mcp_tool_policy.yaml` | 13.4KB | 1.7d | MCP allowlist |
| `policies/mcp_curation_v1.md` | 13.2KB | 1.7d | MCP curation |
| `knowledge/AGENT_RUNTIME_OPTIMIZATION.md` | 11.8KB | 18.1d | 역할 최적화 매트릭스 |
| `knowledge/CLAUDE_COLLABORATION.md` | 10.3KB | 18.1d | Claude 협업 manual |
| `knowledge/MASTER_CREDENTIAL_ACCESS_STANDARD.md` | 10.0KB | 8.9d | 자격증명 표준 |
| `policies/slo_definitions.yaml` | 9.6KB | 13.0d | SLO 정의 |
| `contracts/COLLABORATION_CONTRACT.md` | 8.2KB | 6.3d | 협업 contract |
| `policies/pipa_data_retention.yaml` | 7.1KB | 8.0d | 한국 PIPA 정책 |
| `policies/persona_safety.yaml` | 5.6KB | 4.0d | persona safety |
| `policies/gitleaks-korean-rules.toml` | 5.3KB | 15.1d | secret scan rules |
| `runbooks/chaos_drill_v1.md` | 5.2KB | 8.0d | chaos drill runbook |
| `runbooks/chaos_drill_dryrun_2026-05-06.md` | 5.0KB | 6.2d | chaos drill dry-run |
| `contracts/AGENT_OUTPUT_ARTIFACT_CONTRACT.md` | 4.5KB | 0.1d | artifact contract |
| `runbooks/hook_audit_isolation.md` | 4.2KB | 1.7d | hook isolation |
| `knowledge/OWNER_PROFILE.md` | 4.1KB | 35.7d | 오너 프로필 |
| `policies/rag_eval_baseline.yaml` | 3.2KB | 8.8d | RAG eval baseline |

**적재 정책 변경**:
- 현재 `CLAUDE.md` 가 `AGENT_SHARED_MEMORY.md` + `AGENT_RUNTIME_OPTIMIZATION.md` + `CLAUDE_COLLABORATION.md` + `COLLABORATION_CONTRACT.md` 를 `@import` 자동 적재 중 → **모두 제거 후 lazy Read 로 전환**
- 명시 Read 트리거: persona 설계 / MCP curation / chaos drill 실행 / 자격증명 변경 등 해당 도메인 작업 시점

---

## 4. Tier 3 — REFERENCE (99 파일 / 786K tokens)

### 4.1 카테고리별 분포

| 디렉토리 | 파일 수 | 합계 | 비고 |
| --- | ---: | ---: | --- |
| `personas/` (tier-s/a/b/c/_schema/dispatcher/INDEX) | 36 | 1.13MB | persona body + embeddings 1MB |
| `knowledge/` (research / blueprint / wiki / cross-publish) | 53 | 415KB | 연구 보고서 + Wikipedia draft |
| `knowledge/agent-environment/` (v2 pack) | 8 | 67KB | OSS 프레임워크 / 벤치마크 / threat model |
| `knowledge/rag-master/` | 0 | 0 | (디렉토리 비어있음, 부록 미적재) |
| `registries/` | 1 | 7KB | judgment adapter registry |
| `schemas/` | 2 | 7KB | JSON schema |
| `shared-brain/` (sub-task / 디바이스 task) | 4 | 19KB | codex-task 기록 |

### 4.2 주요 Tier 3 파일 (상위 30개)

| 파일 | 크기 | 마지막 수정 |
| --- | ---: | ---: |
| `personas/dispatcher/persona_embeddings.json` | 1017.8KB | 1.7d |
| `registries/tier_classification.json` (본 작업 산출) | 53.0KB | 0.0d |
| `knowledge/reports/2026-Q2-research-status-report.md` | 42.7KB | 8.1d |
| `registries/tier_classification.yaml` (본 작업 산출) | 34.5KB | 0.0d |
| `knowledge/20260511_D00TEST_FULL_REORGANIZATION_PLAN.md` | 31.3KB | 0.2d |
| `knowledge/20260512_AGENT_DIR_OPTIMIZATION_EXTERNAL_RESEARCH_v1.md` | 24.1KB | 0.0d |
| `knowledge/20260426_FINANCIAL_ADVISOR_SYSTEM_v1.md` | 23.6KB | 15.9d |
| `knowledge/20260512_AGENT_DIR_OPTIMIZATION_MASTER_v1.md` | 19.3KB | 0.0d |
| `knowledge/20260510_D00TEST_DIRECTORY_REORGANIZATION_POLICY.md` | 18.9KB | 0.1d |
| `knowledge/20260424_Directory_Cleanup_Audit_v1.md` | 17.8KB | 1.2d |
| `knowledge/persona_caching_cost_analysis_v1.md` | 17.1KB | 1.7d |
| `knowledge/20260424_AI_AGENT_ENVIRONMENT_OPTIMIZATION_BLUEPRINT.md` | 15.7KB | 6.3d |
| `knowledge/wikipedia-drafts/yesol_heo_ko.md` | 15.5KB | 8.1d |
| `knowledge/persona_caching_integration_guide.md` | 15.0KB | 1.7d |
| `knowledge/wikipedia-drafts/neo_genesis_ko.md` | 14.7KB | 8.1d |
| `knowledge/wikipedia-drafts/yesol_heo_en.md` | 14.4KB | 8.1d |
| `knowledge/cross-publish/devto-running-11-saas-products.md` | 14.0KB | 8.0d |
| `knowledge/wikipedia-drafts/neo_genesis_en.md` | 13.7KB | 8.1d |
| `knowledge/20260427_AI_TRAFFIC_MAXIMIZATION_MASTER_v1.md` | 13.1KB | 15.0d |
| `personas/tier-s/senior-backend-eng-korean.md` | 10.2KB | 1.7d |
| `personas/INDEX.md` | 9.5KB | 1.7d |
| `personas/tier-a/research-synthesizer.md` | 9.3KB | 4.2d |
| `personas/tier-a/threat-modeler-saas.md` | 9.2KB | 4.2d |
| `personas/tier-a/financial-advisor-personal.md` | 9.1KB | 4.2d |
| `personas/tier-a/growth-experiments-pm.md` | 8.9KB | 4.2d |
| `personas/tier-a/database-architect-postgres.md` | 8.8KB | 4.2d |
| `personas/tier-a/infrastructure-architect-cloud.md` | 8.8KB | 4.2d |
| `personas/tier-s/multi-agent-orchestrator.md` | 6.4KB | 1.7d |
| `personas/tier-s/prompt-injection-auditor.md` | 6.4KB | 1.7d |
| `personas/tier-s/senior-da-pm-korean.md` | 5.9KB | 1.7d |

전체 99 파일 목록은 `.agent/registries/tier_classification.yaml` 참조.

### 4.3 Tier 3 의 default_unclassified 검토
`tier3_reference_path` 매칭 없이 `default_unclassified` 로 fallback 된 파일 (knowledge/ 의 일부 timestamp prefix 문서) 은 모두 **knowledge/ 의 단발성 연구 보고서**. Tier 3 분류 맞음 (RAG indexing 만 하면 됨).

---

## 5. Tier 4 — ARCHIVE (29 파일 / 206K tokens)

### 5.1 즉시 격리 권고

| 패턴 | 파일 수 | 합계 | 처리 |
| --- | ---: | ---: | --- |
| `backups-ssot-merge-20260424-*` | 5 | 26KB | `.agent/archive/backups/` 이동 후 `.gitignore` |
| `eval-runs/` | 15 | 76KB | `.agent/archive/eval-runs/` 이동, RAG indexing 제외 |
| `shared-brain/claude-checkpoints/*.jsonl` | 2 | 2KB | `.agent/archive/claude-checkpoints/` |
| `**/*.jsonl` (append-only logs) | 4 | 142KB | `.agent/archive/logs/` |
| `daily-log.md` | 1 | 265KB | `.agent/archive/daily-log/YYYY-MM.md` 분할 |
| `.bible_hash` | 1 | 16B | exempt (auto-generated) |

### 5.2 주요 Tier 4 파일

| 파일 | 크기 | 마지막 수정 | 사유 |
| --- | ---: | ---: | --- |
| `shared-brain/daily-log.md` | 264.9KB | 0.0d | append-only 사후 분석용 |
| `knowledge/wikidata-entities/statements_added_2026-05-03.jsonl` | 127.2KB | 8.8d | append-only audit log |
| `eval-runs/research_refresh_20260424T075701Z/summary.json` | 34.5KB | 18.0d | 일회성 eval 결과 |
| `knowledge/blog_autogen_log.jsonl` | 24.0KB | 0.2d | append-only blog auto-gen log |
| `eval-runs/research_refresh_20260424T045224Z/summary.json` | 22.6KB | 18.1d | 일회성 eval 결과 |
| `backups-ssot-merge-20260424-094951/NEO_MASTER_RULES.md.v14-backup` | 20.7KB | 18.3d | 18일+ 백업 |
| `knowledge/wikidata-entities/statements_added_2026-05-04.jsonl` | 14.2KB | 8.1d | append-only |
| `eval-runs/run_collector_20260424T075708Z/summary.json` | 4.3KB | 18.0d | 일회성 eval |
| `backups-ssot-merge-20260424-094951/AGENTS.md.before-sync` | 3.2KB | 18.3d | 백업 |
| `shared-brain/credential_audit.jsonl` | 0.7KB | 1.2d | audit log |
| `.bible_hash` | 16B | 7.1d | auto-generated hash |

전체 29 파일은 `.agent/registries/tier_classification.yaml` 참조.

---

## 6. ROI 추정 (정량)

### 6.1 토큰 / 비용 (Opus 4.7 input $15/M tokens)

| 항목 | 현재 | 권고 (Tier 1 split, T2 lazy) | 절감 |
| --- | ---: | ---: | ---: |
| 세션당 자동 적재 tokens | 266,398 | 56,376 | **−210,022 (−79%)** |
| 세션당 비용 ($) | $3.996 | $0.846 | **−$3.150** |
| 월 30세션 비용 ($) | $119.88 | $25.38 | **−$94.50** |
| 연 360세션 비용 ($) | $1,438.56 | $304.56 | **−$1,134** |

### 6.2 가정
- **세션당 자동 적재 baseline**: Tier 1 (188K) + Tier 2 (78K) 합산 — 현 `CLAUDE.md` 의 `@import` chain 이 두 tier 모두 자동 적재한다는 분석 기준
- **권고 적재**: Tier 1 의 split candidate (active-tasks/handoff/cross-agent-review) 를 **30% 만 유지** (active section + recent 7일 만), 나머지 Tier 1 (NEO_MASTER + status + device + cross-agent active) 은 100% 유지, Tier 2 는 lazy load 로 0
- **5min ephemeral cache** 적용 시 동일 세션 내 재호출은 추가 90% 절감 가능 (별도 계산)
- **owner 발화 추정치 (122K tokens / 세션)**: handoff 의 자전적 기록 (5/10 작업 기록) 에서 owner 가 보고한 수치. 본 분석의 266K 와 충돌하지만, 대부분 Tier 3 추가 적재 또는 conversation history (system reminder + tool results) 가 누적된 결과로 추정. 본 분류는 `.agent/` 의 실제 적재 분만 다룬다.

---

## 7. 권고 import chain 재구성

### 7.1 현재 (`D:/00.test/neo-genesis/CLAUDE.md`)

```markdown
@./AGENTS.md
@./infra/agent-runtime/LIVE_STATUS.md
@./infra/agent-runtime/FLEET_STATUS.md
@./.agent/contracts/COLLABORATION_CONTRACT.md         # Tier 2 — 제거 권고
@./.agent/knowledge/AGENT_SHARED_MEMORY.md             # Tier 2 — 제거 권고
@./.agent/knowledge/AGENT_RUNTIME_OPTIMIZATION.md      # Tier 2 — 제거 권고
@./.agent/knowledge/CLAUDE_COLLABORATION.md            # Tier 2 — 제거 권고
@./.agent/shared-brain/active-tasks.md                  # Tier 1 (split 권고)
@./.agent/shared-brain/cross-agent-review.md            # Tier 1 (split 권고)
@./.agent/shared-brain/handoff.md                       # Tier 1 (split 권고)
```

### 7.2 권고 (재설계)

```markdown
# Tier 1 — 자동 적재 (split 적용)
@./AGENTS.md                                            # Codex / runtime
@./infra/agent-runtime/LIVE_STATUS.md                   # runtime live
@./.agent/NEO_MASTER_RULES.md                           # 규칙 SSOT
@./.agent/shared-brain/status.json                      # live state
@./.agent/shared-brain/active-tasks.md                  # active section only (split 후)
@./.agent/shared-brain/handoff.md                       # 최근 7일 (split 후)
@./.agent/shared-brain/cross-agent-review.md            # active queue (split 후)

# Tier 2 — 제거 (lazy Read)
# @./.agent/knowledge/AGENT_SHARED_MEMORY.md            ← 작업 성격에 맞을 때 Read
# @./.agent/knowledge/AGENT_RUNTIME_OPTIMIZATION.md     ← 동일
# @./.agent/knowledge/CLAUDE_COLLABORATION.md           ← Claude 협업 작업 시
# @./.agent/contracts/COLLABORATION_CONTRACT.md         ← 협업 정책 작업 시
```

### 7.3 cache 정책

| Tier | cache_control | 효과 |
| --- | --- | --- |
| Tier 1 (NEO_MASTER + status + device) | `ephemeral` (5min) | 동일 세션 재호출 90% 절감 |
| Tier 1 (active-tasks/handoff/cross-agent) | `ephemeral` (5min) — 변경 시 invalidate | live 변경 빈도 고려 |
| Tier 2 (lazy Read 시) | `ephemeral` 1h ttl | 주 수 회 변경, 1시간 cache OK |
| Tier 3 (RAG 결과) | RAG 캐시 별도 | 검색 결과만 caching |
| Tier 4 | exempt | 미적재 |

---

## 8. Migration plan (요약)

다음 task 에서 상세 설계. 본 매트릭스는 분류만.

### Phase A (즉시, low risk)
1. `.agent/archive/` 디렉토리 신설
2. Tier 4 즉시 격리 (29 파일 → `.agent/archive/`)
3. `.gitignore` 갱신 (`.agent/archive/eval-runs/`, `.agent/archive/backups/` 등 선택적)
4. **검증**: SSOT 적재량 1차 감소 측정

### Phase B (split 필수)
1. `active-tasks.md` 자동 분할 스크립트 (`scripts/agent/split_active_tasks.py`)
   - active section (현재 진행 중 task) 만 유지
   - completed entries → `archive/active-tasks-completed-YYYY-MM.md`
2. `handoff.md` 자동 분할 (`scripts/agent/split_handoff.py`)
   - 최근 7일만 유지
   - 이전 → `archive/handoff-YYYY-MM.md`
3. `cross-agent-review.md` 분할 (active queue / completed 분리)
4. **검증**: Tier 1 토큰 ~188K → ~60K (split 후 active 부분 30%)

### Phase C (CLAUDE.md import chain 재구성)
1. `CLAUDE.md` 의 Tier 2 `@import` 4건 제거
2. owner 명시 Read 패턴 학습 (작업 성격별 lazy Read trigger 정리)
3. **검증**: 세션 자동 적재 ~266K → ~56K (−79%)

### Phase D (cache 정책 도입)
1. Anthropic prompt caching `cache_control` API 적용 (sora client / Claude Code launcher 에)
2. Tier 1 ephemeral 5min, Tier 2 lazy 1h cache
3. **검증**: 동일 세션 재호출 비용 90% 추가 절감

### Phase E (RAG indexing)
1. Tier 3 99 파일 Qdrant `neo_ssot` 컬렉션에 인덱스 (already partially done — RAG v2 Phase 0 완료)
2. owner 발화에 도메인 키워드 검출 시 자동 RAG 검색 (eg. "persona", "rag", "quant")

---

## 9. 검증

### 9.1 자동화 스크립트
```bash
cd D:/00.test/neo-genesis
python scripts/agent/classify_ssot.py --json
# 결과:
# - .agent/registries/tier_classification.yaml
# - .agent/registries/tier_classification.json
# - stdout: tier 카운트 + ROI 추정
```

### 9.2 결과 재현 (2026-05-12 첫 실행)
```
Total files: 154
Total bytes: 3,172,241 (3.03 MB)
Estimated tokens (full scan): 1,258,769

Tier     Count         Bytes      Tokens
1 CRIT       7       469,812     187,922
2 IMP       19       196,210      78,476
3 REF       99     1,964,872     785,907
4 ARCH      29       541,347     206,464
```

### 9.3 누락 0건 검증
- 분류 = 7 + 19 + 99 + 29 = 154 ✅ (전체 파일 수와 일치)
- 자동화 스크립트가 154 → 154 매핑, missing 0

---

## 10. 잔존 이슈 / 다음 작업

1. **`active-tasks.md` 의 active vs completed 자동 구분 알고리즘 설계 필요**
   - 단순 heading 패턴 (`## 완료된 것` / `Recently Completed`) 만으로 충분한지 검증
   - 별도 task: split 알고리즘 설계 + dry-run 검증
2. **Anthropic cache_control API 클라이언트 통합**
   - Sora dashboard / Claude Code launcher 어디서 ephemeral 5min 적용할지 결정
   - 별도 task: persona_caching_integration_guide.md 와 연결
3. **owner 측 122K tokens 추정과 본 분석 266K 의 격차 조사**
   - owner 가 잰 수치는 어디서 측정? (Claude Code internal counter? Anthropic console?)
   - conversation history (system reminder + tool results 누적) 가 별도로 들어왔을 가능성
4. **본 분류 자체가 정적 시점 snapshot** — handoff/active-tasks/status 는 매 응답 변경되므로 분류는 매주 재실행 권고. cron: `0 9 * * 1 python scripts/agent/classify_ssot.py`

---

## 11. 변경 이력

| 일자 | 변경 | 작업자 |
| --- | --- | --- |
| 2026-05-12 | v1 작성. 4-tier 분류 154 파일 자동 매핑 + ROI $94/월 추정 | Strategy Lead (Claude Opus 4.7) |
