# Project Continuity Protocol (PCP) v1 — 전역 규칙

> **상태:** 정본 (canonical). 모든 디바이스 · 모든 AI · 모든 에이전트가 추종한다.
> **작성:** 2026-06-14, Claude Opus 4.8 (owner 명령 기반)
> **owner 명령:** "전역설정 — 모든 프로젝트는 모든 AI가 작업을 이어서 진행할 수 있도록 반드시 저장소를 생성하고 기록하고 추적한다. 작업 시작 시 git pull로 최신화 먼저 한 후 진행한다. 안전하고 무결한 방법으로 복잡한 프로젝트에도 적용."
> **상위 SSOT:** `.agent/NEO_MASTER_RULES.md` (이 문서는 그 하위 운영 규칙)
> **머신리더블:** `.agent/policies/project_continuity_registry.json`
> **실행 도구:** `scripts/agent_session_sync.py`

---

## 0. 왜 무지성 "git pull 먼저"는 위험한가 (설계 동기)

2026-06-14 실측으로 드러난 지형:

| 프로젝트 | 상태 | 무지성 pull 시 결과 |
|---|---|---|
| `neo-genesis` | git, **dirty 17,018** | 미커밋 17K 파일 충돌/소실 위험 — **대참사** |
| `002.products-sbu/012.finite` | git, owner WIP 브랜치 dirty 11 | owner 미커밋 결제/리텐션 작업 소실 |
| `jobsearch` | git, dirty 106 | 충돌 |
| `portfolio` | git, dirty 85 | 충돌 |
| `001.ssot-agent-runtime` (SSOT 본체) | **git 아님** | pull 대상 자체가 없음 — 더 큰 문제: 버전관리·동기화 부재 |
| `_secrets`, `personal` | git 아님 (의도적) | **절대 저장소화/푸시 금지** (개인회생·법무·크레덴셜) |

**결론:** owner 의도("최신 상태에서 이어 작업")는 옳지만, 실행은 `git pull`이 아니라 **Safe-Sync**여야 한다. dirty 트리에서 pull/reset/clean을 금지하고, fetch + 안전 rebase(autostash) + 충돌 시 즉시 복원·중단·보고로 구현한다. "안전·무결"은 이 프로토콜의 1순위 제약이다.

---

## 1. 프로젝트 3-Tier 분류 (모든 프로젝트는 반드시 하나에 등록)

"저장소 생성"을 모든 디렉토리에 무차별 적용하지 않는다. 민감 자산을 공개 저장소로 만드는 것이 더 큰 사고다. 대신 **모든 프로젝트는 반드시 registry에 분류 등록**한다 — "우연히 추적 안 됨" 상태를 0으로 만든다.

### Tier 1 — Tracked (private git + Yesol-Pilot 리모트)
- 대상: 활성 소스 프로젝트 (finite, neo-genesis, portfolio, sora-app, jobsearch, room-707, koreanllm, ait-factory 등)
- 규칙: `github.com/Yesol-Pilot/*` 리모트 보유, **기본 private**, 세션 시작 시 Safe-Sync, 논리적 종료마다 commit+push.
- 리모트 없는 활성 프로젝트(koreanllm/ait-factory 등) = `track: needs_repo` → **owner 게이트(G2)로 private repo 생성**.

### Tier 2 — Local-Vault (로컬 전용, 리모트 금지)
- 대상: 민감 자산 — `_secrets`, `personal`, `project_yesol/master-data`(PII·고객 데이터 포함 가능), 사업자/법무 문서.
- 규칙: **외부 리모트 절대 금지**. 연속성은 로컬 git(리모트 없음) 스냅샷 + 로컬 암호화 백업으로만. 추적은 registry 등록으로 충족(내용 푸시 아님).

### Tier 3 — Ephemeral (추적 제외)
- 대상: `010.tmp-output`, `output`, `008.mirrors-external`(라이브 소스 아님), `009.archive`, 빌드 산출물, `node_modules`.
- 규칙: `track: never`로 명시 등록. git 생성하지 않음. (명시 제외 = "우연한 미추적"과 구분)

---

## 2. 불변 안전 규칙 (Safety Invariants) — 위반 시 즉시 중단

1. **Safe-Sync, never blind pull.** 세션 시작 동기화는 `git fetch` → 트리 clean이면 `pull --rebase` → 트리 dirty면 **report-only(동기화 보류)**. `--autostash` 명시 시에만 stash→rebase→pop, 충돌 시 자동 복원+중단+보고. **dirty 트리에서 `git pull`·`git reset --hard`·`git clean` 금지.**
2. **Remote allowlist.** push/clone는 `github.com/Yesol-Pilot/*`만. `neogenesislab`·`etribe`로의 push는 도구가 거부한다(기존 하드룰과 정합).
3. **Sensitivity gate.** `_secrets/**`, `personal/**`, `**/.env*`, `**/*.key`, `**/credentials*`, master-data PII는 commit/push 대상에서 영구 제외. 기존 `gitleaks-korean-rules.toml` 재사용으로 pre-commit 스캔.
4. **WIP 보호.** 미커밋 변경은 절대 폐기하지 않는다. owner WIP 브랜치(예: finite `feat/finite-mvp-launch`)는 fetch+report만, rebase는 clean일 때만.
5. **Visibility 기본 private.** 비즈니스/PII 가능성이 있는 모든 신규 repo는 private 기본. public 전환은 owner 명시 승인(G2).
6. **Idempotent + reversible.** 모든 동작은 registry 기반·재실행 안전. repo 생성/push는 프로젝트별 owner 게이트(가시성·민감도 판단이 owner 몫).

---

## 3. 세션 시작 프로토콜 (모든 AI가 작업 전 실행)

```
1. 현재 프로젝트 식별 (cwd → registry 조회)
2. registry 미등록이면 → 등록 먼저 (tier 분류). "우연한 미추적" 금지.
3. Tier 1 → python scripts/agent_session_sync.py <path>
      = fetch + (clean이면 rebase / dirty면 report-only) + remote allowlist 검증 + ledger 기록
   Tier 2/3 → 리모트 동기화 스킵, 로컬 연속성 기록만 읽음
4. SSOT shared-brain 읽기 (handoff.md / active-tasks.md) — 크로스-AI 상태 인계
5. 작업 수행. 논리적 종료마다: Tier1 commit+push / Tier2 로컬 스냅샷 + WORKLOG 갱신
6. 세션 종료 시 handoff.md 작성 (토큰 소진/전환 대비)
```

**핵심:** "git pull 먼저"는 3단계의 `agent_session_sync.py`로 구현된다. AI는 직접 `git pull`을 치지 않고 이 도구를 호출한다 — 안전 분기가 도구에 내장돼 있기 때문.

---

## 4. 기록·추적 (Record & Track)

연속성 = "다음 AI가 끊긴 지점을 정확히 이어받을 수 있는가". 두 계층:

- **전역 상태 (cross-AI):** `.agent/shared-brain/handoff.md`(세션 인계) + `active-tasks.md`(작업 보드). 모든 AI 공통.
- **프로젝트 로컬:** Tier1은 git history + (옵션) `.continuity/WORKLOG.md`. 커밋 메시지에 "무엇을/왜/다음 단계" 포함.

기록 최소 스키마(handoff entry): `목표 · 범위 · 만진 파일 · 검증 상태 · 명시적 non-goal · 다음 단계`.

---

## 5. 복잡한 기존 프로젝트 적용 (마이그레이션, 안전 순서)

**무결성 우선 — 한 번에 다 하지 않는다. 단계적·가역적.**

- **Phase 0 (즉시, 자율):** registry 작성 — 모든 프로젝트 분류 등록 (이 PR). 코드 변경 0, 외부 액션 0. "현재 무엇이 추적/미추적인지" 가시화.
- **Phase 1 (즉시, 자율):** `agent_session_sync.py` 배포 + **dry-run 검증** — neo-genesis(17K dirty)·finite(WIP)에서 도구가 pull을 **거부하고 report만** 하는지 라이브 확인. 안전 분기 입증.
- **Phase 2 (owner 게이트 G2, 프로젝트별):** Tier1 nogit 프로젝트(koreanllm/ait-factory 등) **private repo 생성 + 초기 커밋 + push**. 프로젝트별로 민감 파일 .gitignore 확정 후 1개씩. SSOT 본체(`001.ssot-agent-runtime`)는 **최우선 private repo** — 단, 내부 크레덴셜 참조·전략 문서 포함이므로 gitleaks 스캔 통과 후에만.
- **Phase 3 (자율):** 세션 시작 훅에 sync 연결 (CLAUDE.md/AGENTS.md 전역 로더). 디바이스별 cron/hook 배포는 기존 `sync_agent_context.py` 경로 재사용.
- **Phase 4 (자율):** dirty 거대 트리(neo-genesis 17K) 정리 — owner와 함께 commit/stash/.gitignore 재정비. pull 가능 상태로 회복.

각 Phase는 독립적으로 롤백 가능. Phase 2/4만 owner 게이트.

---

## 6. owner 결정 필요 (G2)

1. **SSOT 본체(`001.ssot-agent-runtime`) private repo 생성 여부** — 권고: 생성(연속성 최우선). 단 gitleaks 스캔 + `.env*`/크레덴셜 제외 후. Yesol-Pilot/neo-genesis-ssot (private).
2. **nogit Tier1 프로젝트 repo 생성 순서** — 권고: koreanllm → ait-factory → project_yesol(민감, Tier2 검토). 1개씩.
3. **neo-genesis 17K dirty 처리 방침** — 권고: 별도 정리 세션. 지금은 Safe-Sync가 자동 보호.

자율(G1): registry 작성, sync 도구 배포·dry-run, 전역 규칙 주입, 기존 git repo의 Safe-Sync 적용.

---

## 7. Anti-goals (하지 않는 것)

- 무지성 `git pull`/`reset --hard`/`clean` (dirty 트리 파괴).
- `_secrets`/`personal`/PII의 저장소화·푸시.
- `neogenesislab`/`etribe`로의 push.
- 모든 디렉토리 무차별 public repo화.
- owner WIP 폐기.
