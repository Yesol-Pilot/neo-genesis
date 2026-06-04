# `.agent/` 최적화 마스터 설계 v1

> **작성**: 2026-05-12, Strategy Lead Claude Opus 4.7
> **owner 명령**: `.agent/` import chain 비용 최적화 + lifecycle 자동화 + tier 분류
> **근거**: 외부 리서치 (별도 doc, 4 병렬 에이전트) + 내부 정밀 진단 (별도 doc) + SSOT tier 분류 (별도 doc)
> **본 문서 성격**: 설계 only. 실 archive 실행 / CLAUDE.md 변경은 owner 결정 + 후속 Phase 작업

---

## 0. 결론 (TL;DR)

| 항목 | 현재 | v2 목표 | 감축 |
|---|---|---|---|
| 매 세션 적재 토큰 | 122K tokens | ~30K tokens | **-75%** |
| 세션당 비용 | $1.84 | $0.45 | -$1.39 |
| 월 비용 (30 세션) | $55.20 | $13.50 | **-$41.70** |
| `.agent/shared-brain/active-tasks.md` | 266 KB / 3,549 lines | < 50 KB | -80% |
| `.agent/shared-brain/handoff.md` | 123 KB / 2,193 lines | recent 7d only (~15 KB) | -88% |
| `.agent/shared-brain/cross-agent-review.md` | 39 KB / 594 lines | active only (~5 KB) | -87% |

**전략**: 4-Phase migration (4주, rollback-safe). 첫 Phase 는 dry-run only, 라이브 영향 0.

**핵심 invariants**:
- archive 는 **delete 가 아니라 move**. 모든 entry 는 `.agent/shared-brain/archive/YYYY-MM/` 에 보존
- audit log 의무 (`~/.claude/audit/ssot_archive_<date>.jsonl`)
- 모든 phase 에 timestamp backup + rollback 가능
- Phase 2 실 archive 직전 owner gate 1회 (dry-run diff 검토)

---

## 1. Archive 디렉토리 구조 (옵션 A 채택)

**채택안**: month-based (시간 기반)

```
.agent/shared-brain/archive/
├── INDEX.md                          # archive 가이드 + 디렉토리 인덱스
├── 2026-04/
│   ├── active-tasks-completed.md     # active-tasks.md 의 [x] 완료 entry archive
│   ├── handoff.md                    # 30일+ 이전 handoff section
│   └── cross-agent-review.md         # closed CCR entry
├── 2026-05/
│   ├── active-tasks-completed.md
│   ├── handoff.md
│   └── cross-agent-review.md
└── 2026-06/
    └── ...
```

**채택 근거 (vs 옵션 B topic-based)**:
- 자동화 단순 (date-based partitioning)
- cron weekly 가 자연스럽게 month 디렉토리 결정
- 검색: `grep -r "v11 Phase 0" .agent/shared-brain/archive/` 단일 명령
- topic-based 는 분류 정책 필요 (사람 손 필수) → 자동화 차단

**옵션 A 단점 + 완화**:
- 단점: month 경계에 걸친 작업이 분할됨
- 완화: 각 archive file 상단에 "포함 기간" + "키워드 INDEX" 자동 생성

**파일별 anchor 유지**:
- 원본 (`active-tasks.md` 등) 에 archive 된 entry block 마다 `<!-- ARCHIVED: 2026-04 → archive/2026-04/active-tasks-completed.md#L42 -->` marker 1줄 보존
- → 다음 세션이 "이거 처리했나?" 물을 때 marker 로 fallback 가능

---

## 2. Lifecycle Automation

### 2.1 Archive 정책 (rules)

| Rule ID | 대상 | 조건 | Archive 시점 |
|---|---|---|---|
| R1 | `active-tasks.md` | `[x] Completed` checkmark 가 있는 block | 30일 후 |
| R2 | `handoff.md` | timestamp 가 30일+ 이전 entry section | 30일 후 |
| R3 | `cross-agent-review.md` | `result: new_signal | no_new_signal | failed` 처리된 CCR | 30일 후 |
| R4 | `knowledge/*.md` | 90일+ stale + 최근 reference 없음 | metadata `status: archived` 추가만 (이동 X) |
| R5 | `daily-log.md` | 60일+ 이전 일자 | quarterly archive 별도 task |

**Active 유지 규칙 (archive 안 함)**:
- `[ ]` unchecked task
- 최근 7일 handoff
- `## Active` section 의 CCR
- "📅 Weekly Progress Review", "🟣 Strategy Lead" 등 lead-by-lead 운영 entry
- 모든 Phase header / decision header

### 2.2 Archive 실행 시점

| 모드 | trigger | gate |
|---|---|---|
| **manual dry-run** | `python scripts/agent/archive_ssot.py --dry-run` | 자유 실행 |
| **manual execute** | `python scripts/agent/archive_ssot.py --execute` | owner 확인 후 |
| **weekly cron** | 매주 월요일 09:00 KST | Phase 4 이후 자동 |
| **emergency rollback** | `--rollback <backup_timestamp>` | 즉시 |

### 2.3 Archive 도구 (`scripts/agent/archive_ssot.py`)

**CLI 인터페이스**:
```bash
# 미리보기 (안전)
python scripts/agent/archive_ssot.py --dry-run [--target-file active-tasks.md] [--age-days 30]

# 실제 archive (gated)
python scripts/agent/archive_ssot.py --execute --confirm

# 특정 파일만
python scripts/agent/archive_ssot.py --execute --target-file handoff.md --age-days 30

# rollback (backup timestamp 로)
python scripts/agent/archive_ssot.py --rollback 20260519-090000

# 통계만 (read-only)
python scripts/agent/archive_ssot.py --stats
```

**핵심 동작**:
1. `.agent/shared-brain/active-tasks.md` / `handoff.md` / `cross-agent-review.md` line-by-line parsing
2. archive 후보 식별 (date stamp 또는 `[x]` 또는 `result:` 패턴)
3. backup 생성: `.agent/shared-brain/archive/.backup/<timestamp>/<original_file>`
4. archive 디렉토리에 append: `.agent/shared-brain/archive/YYYY-MM/<file>.md`
5. 원본 파일에서 archive block 제거 (atomic edit: temp file → fsync → rename)
6. 원본에 anchor marker 1줄 추가 (`<!-- ARCHIVED: ... -->`)
7. audit log 작성: `~/.claude/audit/ssot_archive_<date>.jsonl`
8. rollback 가능: backup → 원본 위치 복원

**안전 가드**:
- `--execute` 는 `--confirm` 또는 stdin 동의 없으면 거부
- atomic 쓰기 (temp → rename)
- backup 의무 (없으면 abort)
- archive file 도 atomic append
- audit log 에 line count / file hash before/after 기록
- exit code: 0 (성공) / 1 (no candidates) / 2 (safety abort) / 3 (rollback)

---

## 3. CLAUDE.md Import Chain v2

### 3.1 현 chain (총 483 KB / ~122K tokens / $1.84)

```markdown
@./AGENTS.md                                          # 7 KB
@./infra/agent-runtime/LIVE_STATUS.md                 # 1 KB
@./infra/agent-runtime/FLEET_STATUS.md                # 0.5 KB
@./.agent/contracts/COLLABORATION_CONTRACT.md         # 8 KB
@./.agent/knowledge/AGENT_SHARED_MEMORY.md            # 16 KB
@./.agent/knowledge/AGENT_RUNTIME_OPTIMIZATION.md     # 12 KB
@./.agent/knowledge/CLAUDE_COLLABORATION.md           # 11 KB
@./.agent/shared-brain/active-tasks.md                # 266 KB ⚠️
@./.agent/shared-brain/cross-agent-review.md          # 39 KB
@./.agent/shared-brain/handoff.md                     # 123 KB ⚠️
```

매 세션 무조건 122K tokens 적재. 그러나 실제 사용률은 < 15% (90% 가 historical context).

### 3.2 v2 chain (slim, Tier 1 only)

```markdown
# Neo Genesis Claude Adapter v2 (slim, 2026-05-12)

# === Tier 1: 매 세션 적재 (필수) ===
@./AGENTS.md                                          # Master rules
@./infra/agent-runtime/LIVE_STATUS.md                 # Live runtime snapshot
@./.agent/shared-brain/active-tasks.md                # Active section only (after Phase 2 archive)
@./.agent/shared-brain/handoff.md                     # Recent 7 days only (after Phase 2 archive)

# === Tier 2: Lazy load (Read tool 필요 시) ===
# - .agent/contracts/COLLABORATION_CONTRACT.md       (협업 룰 — 새 협업 작업 시)
# - .agent/knowledge/AGENT_SHARED_MEMORY.md          (장기 메모리 — 운영 사실 조회 시)
# - .agent/knowledge/AGENT_RUNTIME_OPTIMIZATION.md   (역할 매트릭스 — 라우팅 결정 시)
# - .agent/knowledge/CLAUDE_COLLABORATION.md         (Claude 운영 매뉴얼 — checkpoint 작업 시)
# - .agent/shared-brain/cross-agent-review.md        (CCR queue — review 작업 시)
# - infra/agent-runtime/FLEET_STATUS.md              (fleet 상태 — device 작업 시)
# - .agent/shared-brain/archive/                     (historical lookup — 과거 작업 조회 시)
```

**추정 적재 (Phase 2 archive 후 + Phase 3 chain v2 적용)**:
- Tier 1 합산: ~25-30 KB / ~7-8K tokens
- 비용: $0.45 / 세션 (Sonnet 기준)
- 월 절감 (30 세션): ~$42

### 3.3 Tier 분류 근거

| 파일 | Tier | 사용률 | 근거 |
|---|---|---|---|
| AGENTS.md | 1 | 100% | 모든 세션 시작 시 룰 |
| LIVE_STATUS.md | 1 | 100% | 모델/버전/디바이스 검증 |
| active-tasks.md (active only) | 1 | 80%+ | 진행 중인 task 확인 빈번 |
| handoff.md (recent 7d) | 1 | 60%+ | 이전 세션 컨텍스트 |
| COLLABORATION_CONTRACT.md | 2 | < 20% | 협업 룰 변경 드뭄 |
| AGENT_SHARED_MEMORY.md | 2 | < 30% | 장기 사실 조회 시만 |
| AGENT_RUNTIME_OPTIMIZATION.md | 2 | < 15% | 라우팅 의사결정 시만 |
| CLAUDE_COLLABORATION.md | 2 | < 20% | checkpoint 작업 시만 |
| cross-agent-review.md | 2 | < 25% | review request 시만 |
| FLEET_STATUS.md | 2 | < 10% | device 운영 시만 |
| archive/* | 3 | < 5% | 과거 조회 시만 |

**중요**: Tier 2 가 사용률 < 30% 라도 **검색 가능성** 은 100% 유지. Read tool 또는 Grep 으로 즉시 접근.

---

## 4. 점진 Migration Plan (rollback-safe, 4 Phase / 4주)

### Phase 1 (Week 1, 2026-05-12 ~ 2026-05-19): MEASURE + DESIGN

**목표**: 측정 baseline 확보, 도구 작성, owner gate

**산출물**:
- ✅ 본 마스터 문서 (`.agent/knowledge/20260512_AGENT_DIR_OPTIMIZATION_MASTER_v1.md`)
- ✅ archive_ssot.py SKELETON (`scripts/agent/archive_ssot.py.SKELETON.md`)
- archive_ssot.py 첫 구현 (dry-run only, --execute 막힘)
- baseline 측정 (현 토큰 적재 / 비용 / 파일 크기)
- owner 30분 review

**라이브 영향**: 0 (도구만 작성, 실 archive 없음)

**Gate**:
- owner 가 본 마스터 + skeleton 검토
- archive 정책 (30일 기준) 동의
- 다음 phase 진입 승인

**Rollback**: 불필요 (도구만 추가, 기존 SSOT 무변경)

### Phase 2 (Week 2, 2026-05-19 ~ 2026-05-26): ARCHIVE first execution

**목표**: 첫 archive 실행 + 효과 측정

**작업**:
1. `python scripts/agent/archive_ssot.py --dry-run` 실행 → diff preview 생성
2. owner 가 diff 검토 (예상: ~500 entries, 200 KB 가 archive 대상)
3. owner approve 후 `--execute --confirm`
4. archive 결과 검증:
   - `.agent/shared-brain/active-tasks.md` < 50 KB ✅
   - `.agent/shared-brain/handoff.md` < 20 KB ✅
   - `.agent/shared-brain/cross-agent-review.md` < 10 KB ✅
   - `archive/2026-04/`, `archive/2026-05/` 디렉토리 생성 확인
   - audit log 정상 기록
5. 다음 세션 진입 시 token 적재 측정

**라이브 영향**: 다음 세션부터 SSOT 적재 ~70% 감축

**Gate**:
- 첫 archive 실행 후 owner 확인 (1 세션)
- token 적재 측정 결과 vs 예상 비교
- archive entry 검색 가능성 검증 (Grep test 3-5건)

**Rollback** (필요 시):
```bash
python scripts/agent/archive_ssot.py --rollback <backup_timestamp>
```
backup 디렉토리 → 원본 위치 복원, ~30초 작업

### Phase 3 (Week 3, 2026-05-26 ~ 2026-06-02): IMPORT CHAIN v2

**목표**: CLAUDE.md import chain slim 화 + Tier 2 lazy load 검증

**작업**:
1. `D:/00.test/neo-genesis/CLAUDE.md` backup → `CLAUDE.md.bak-v1`
2. `~/.claude/CLAUDE.md` backup
3. v2 chain 적용 (Tier 1 4개만 @import, Tier 2 6개는 주석 처리)
4. `python scripts/sync_agent_context.py --updated-by claude` 실행 (어댑터 재생성)
5. 다음 세션 진입 시 라이브 검증:
   - token 적재 측정 (목표: < 30K)
   - SSOT 인지 정상 (active-tasks / handoff 조회 가능)
   - Tier 2 검색 가능 (Grep 또는 Read 로 접근 가능)
6. 1 세션 동안 owner 가 정상성 검증

**라이브 영향**: 매 세션 적재 -75%, 비용 -$1.39/세션

**Gate**:
- 다음 세션에서 owner intent 손실 0건
- Tier 2 lookup 시 Read 가 정상 동작
- token 적재가 예상 범위 (< 30K)

**Rollback** (필요 시):
```bash
cp CLAUDE.md.bak-v1 CLAUDE.md
python scripts/sync_agent_context.py --updated-by claude
```
즉시 원복, 5초 작업

### Phase 4 (Week 4+, 2026-06-02 ~): AUTOMATION

**목표**: weekly cron 등록 + 측정 dashboard + 안정화

**작업**:
1. Windows Scheduled Task 등록:
   - 이름: `NeoGenesis-SSOT-Archive-Weekly`
   - cron: `0 9 * * MON` (매주 월요일 09:00 KST)
   - 명령: `python D:/00.test/neo-genesis/scripts/agent/archive_ssot.py --execute --confirm --weekly`
2. audit log dashboard:
   - `scripts/agent/archive_dashboard.py` (별도 작업)
   - 주간 archive 통계 (entries / KB / age 분포)
3. Tier 3 RAG 통합 검토 (선택, 별도 task):
   - archive/* 를 Qdrant 인덱싱
   - 다음 세션 archive 조회 자동 fallback

**라이브 영향**: 점진 누적, 자동 유지

**Gate**:
- 첫 weekly run 후 owner 확인
- 4주 누적 후 안정성 확인

**Rollback** (필요 시):
- Scheduled Task 삭제
- 수동 모드 복귀

---

## 5. Stop/Go 게이트

| Gate | 조건 | Action |
|---|---|---|
| G1 (Phase 2) | archive 실행 후 active-tasks.md > 100 KB | 정책 재조정 (age-days 15 로 단축) |
| G2 (Phase 2) | active-tasks.md 의 `[x]` entry < 30% archived | `[x]` 파싱 로직 버그 진단 |
| G3 (Phase 3) | import v2 후 token 적재 > 50K | Tier 분류 재검토 |
| G4 (Phase 3) | owner intent 손실 1건+ 발생 | 즉시 rollback + 원인 분석 |
| G5 (Phase 3) | Tier 2 Read fallback 실패 1건+ | lazy load 가이드 보강 |
| G6 (Phase 4) | weekly cron 후 archive 실수 (active entry 가 archived) | 자동 rollback + 정책 정정 |
| G7 (전체) | 다음 세션에서 Claude 가 archive 파일 찾기 못함 | INDEX.md 보강 + grep 가이드 |

각 G 발생 시:
- 즉시 rollback (필요 시)
- audit log 검토
- 원인 분석 → 정책 v1.1 로 업데이트
- owner 보고

---

## 6. 측정 Dashboard

### 6.1 Baseline (Phase 1 측정)

| Metric | Baseline (2026-05-12) | Phase 2 후 | Phase 3 후 | Phase 4 (4주 후) |
|---|---|---|---|---|
| 적재 토큰 / 세션 | 122K | ~80K | ~30K | ~30K 유지 |
| 비용 / 세션 | $1.84 | $1.20 | $0.45 | $0.45 |
| active-tasks.md KB | 266 | < 50 | < 50 | < 50 |
| handoff.md KB | 123 | < 20 | < 20 | < 20 |
| ccr.md KB | 39 | < 10 | < 10 | < 10 |
| archive/ KB | 0 | ~300 | ~300 | 증가 |
| audit log entries | 0 | ~500 | ~500 | 증가 |

### 6.2 Owner-facing 보고

매 phase 종료 시 보고:
```
Phase X 완료 (날짜)
- 적재 토큰: <before> → <after> (-<delta>%)
- 비용: $<before> → $<after>
- archive entries: <count>
- archive KB: <KB>
- rollback 가능: <backup_timestamp>
- 다음 phase: <description>
- Stop/Go: G<id> <triggered/clear>
```

### 6.3 audit log 형식

`~/.claude/audit/ssot_archive_<YYYY-MM-DD>.jsonl`:
```json
{"ts":"2026-05-19T09:00:00+09:00","action":"archive","target":"active-tasks.md","entries":120,"kb_before":266,"kb_after":48,"backup":"archive/.backup/20260519-090000","hash_before":"sha256:...","hash_after":"sha256:..."}
{"ts":"2026-05-19T09:00:02+09:00","action":"archive","target":"handoff.md","entries":35,"kb_before":123,"kb_after":18,"backup":"archive/.backup/20260519-090000","hash_before":"sha256:...","hash_after":"sha256:..."}
```

---

## 7. 알려진 위험 + Mitigation

| Risk ID | 위험 | 가능성 | 영향 | Mitigation |
|---|---|---|---|---|
| R1 | archive 실수로 active entry 가 archived | 중 | 고 | dry-run 첫 1회 강제 + owner gate + rollback 즉시 가능 |
| R2 | Claude 가 archive 파일 찾기 못함 | 중 | 중 | anchor marker (`<!-- ARCHIVED: ... -->`) + INDEX.md + Grep 가이드 |
| R3 | Tier 2 lazy load 시 Read 실패 | 저 | 중 | 경로 절대 표기 + sync_agent_context.py 어댑터 재생성 |
| R4 | cron 가 weekly 실행 안 됨 | 저 | 저 | manual fallback 항상 가능 |
| R5 | audit log 누락 | 저 | 중 | logger 의무화 + try/except 안에서도 audit 보존 |
| R6 | archive 디렉토리 자체 비대화 | 저 | 저 | Phase 4 + RAG 통합 시점에 quarterly archive 별도 정책 |
| R7 | owner 가 archived entry 보고 싶을 때 마찰 | 중 | 저 | INDEX.md + month 디렉토리 검색 가이드 + 향후 RAG |
| R8 | Phase 3 chain v2 적용 후 token 측정 어려움 | 저 | 저 | `/context` 명령 + audit log 측정 |
| R9 | sync_agent_context.py 가 v2 chain 호환 안 됨 | 저 | 중 | Phase 3 전에 sync 스크립트 1회 검증 + 어댑터 생성 결과 확인 |
| R10 | Phase 2 backup 디스크 비용 | 매우 저 | 매우 저 | C drive policy 적용 (D:/agent-cache/ 활용) |

---

## 8. 다음 세션 즉시 액션 (owner gate 후)

**Phase 1 → Phase 2 진입 조건**:
1. owner 가 본 마스터 문서 검토 완료
2. archive 정책 (R1~R5) 동의
3. month-based 구조 (옵션 A) 동의
4. dry-run 결과 검토 후 --execute 승인

**즉시 가능 (owner gate 없이)**:
- `python scripts/agent/archive_ssot.py --dry-run` 실행 (preview 만)
- `python scripts/agent/archive_ssot.py --stats` (read-only)

**Phase 2 진입 시 첫 명령**:
```bash
cd D:/00.test/neo-genesis
python scripts/agent/archive_ssot.py --dry-run --target-file active-tasks.md --age-days 30 > /tmp/archive_preview.txt
# owner review
python scripts/agent/archive_ssot.py --execute --confirm --target-file active-tasks.md --age-days 30
# verify
ls -la .agent/shared-brain/active-tasks.md  # < 100 KB 예상
ls -la .agent/shared-brain/archive/
```

---

## 9. 변경 이력

| 날짜 | 작성자 | 변경 |
|---|---|---|
| 2026-05-12 | Claude Opus 4.7 (Strategy Lead) | v1 초안. 4-Phase migration + month-based archive + Tier 분류 + Stop/Go 게이트 7개 |

## 10. 참조 문서

- 외부 리서치 (별도 doc, 4 병렬 에이전트 산출)
- 내부 정밀 진단 (별도 doc, 본 세션 사전 분석)
- SSOT tier 분류 (별도 doc)
- `.agent/contracts/COLLABORATION_CONTRACT.md` — 협업 룰
- `.agent/knowledge/AGENT_RUNTIME_OPTIMIZATION.md` — 역할 매트릭스
- `.agent/knowledge/20260510_C_DRIVE_MANAGEMENT_POLICY.md` — backup 저장 위치 정책
- `scripts/sync_agent_context.py` — 어댑터 재생성 도구

---

## 부록 A: archive_ssot.py 사용 예시

### Dry-run (모든 SSOT 파일 archive 후보 미리보기)
```bash
$ python scripts/agent/archive_ssot.py --dry-run

[DRY-RUN] active-tasks.md
  candidates: 124 blocks (180 KB / 266 KB total → reduce to 86 KB)
  by rule:
    R1 ([x] completed, age >= 30d): 98 blocks
    R3 (closed CCR ref): 26 blocks
  target archive: .agent/shared-brain/archive/2026-04/active-tasks-completed.md (new)

[DRY-RUN] handoff.md
  candidates: 38 sections (98 KB / 123 KB total → reduce to 25 KB)
  by rule:
    R2 (age >= 30d, no recent reference): 38 sections
  target archive: .agent/shared-brain/archive/2026-04/handoff.md (new)

[DRY-RUN] cross-agent-review.md
  candidates: 42 entries (32 KB / 39 KB total → reduce to 7 KB)
  by rule:
    R3 (result: new_signal | no_new_signal | failed, age >= 30d): 42 entries
  target archive: .agent/shared-brain/archive/2026-04/cross-agent-review.md (new)

[SUMMARY]
  total candidates: 204
  total to archive: 310 KB
  total after: 118 KB (-62%)
  backup target: .agent/shared-brain/archive/.backup/20260519-090000/
  audit log: ~/.claude/audit/ssot_archive_2026-05-19.jsonl

Run with --execute --confirm to apply.
```

### Execute (실제 archive)
```bash
$ python scripts/agent/archive_ssot.py --execute --confirm

[EXECUTE] Creating backup at .agent/shared-brain/archive/.backup/20260519-090000/
[EXECUTE] Archiving active-tasks.md: 124 blocks → 2026-04/active-tasks-completed.md
[EXECUTE] Archiving handoff.md: 38 sections → 2026-04/handoff.md
[EXECUTE] Archiving cross-agent-review.md: 42 entries → 2026-04/cross-agent-review.md
[EXECUTE] Audit log: ~/.claude/audit/ssot_archive_2026-05-19.jsonl (3 entries)
[EXECUTE] Done. Rollback: python scripts/agent/archive_ssot.py --rollback 20260519-090000
```

### Rollback
```bash
$ python scripts/agent/archive_ssot.py --rollback 20260519-090000

[ROLLBACK] Restoring from .agent/shared-brain/archive/.backup/20260519-090000/
[ROLLBACK] Restored active-tasks.md (266 KB)
[ROLLBACK] Restored handoff.md (123 KB)
[ROLLBACK] Restored cross-agent-review.md (39 KB)
[ROLLBACK] Done. Archive files at 2026-04/ retained (manual cleanup if needed).
```
