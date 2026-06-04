# `archive_ssot.py` 구현 가이드 (SKELETON)

> **상태**: 설계 only. 실 구현은 Phase 1 task.
> **목적**: `.agent/shared-brain/active-tasks.md`, `handoff.md`, `cross-agent-review.md` 의 stale entry 를 archive 디렉토리로 이동
> **본 문서 성격**: 구현자가 따라야 할 패턴 + edge cases + 안전 가드 명세

---

## 1. CLI 인터페이스

```python
parser = argparse.ArgumentParser(description="Archive stale SSOT entries to .agent/shared-brain/archive/")

# 모드 (mutually exclusive)
mode = parser.add_mutually_exclusive_group(required=True)
mode.add_argument("--dry-run", action="store_true", help="Preview only, no changes")
mode.add_argument("--execute", action="store_true", help="Apply changes (requires --confirm)")
mode.add_argument("--rollback", type=str, metavar="TIMESTAMP", help="Restore from backup at TIMESTAMP")
mode.add_argument("--stats", action="store_true", help="Read-only stats")

# 옵션
parser.add_argument("--confirm", action="store_true", help="Required for --execute")
parser.add_argument("--target-file", type=str, choices=["active-tasks.md", "handoff.md", "cross-agent-review.md", "all"], default="all")
parser.add_argument("--age-days", type=int, default=30, help="Archive entries older than N days")
parser.add_argument("--weekly", action="store_true", help="cron mode: append-only audit, no interactive prompt")
parser.add_argument("--root", type=Path, default=Path("D:/00.test/neo-genesis"), help="Repo root")
```

**Exit codes**:
- 0: 성공
- 1: no candidates (정상, 작업 불필요)
- 2: safety abort (backup 실패 / atomic write 실패 등)
- 3: rollback 성공
- 4: 잘못된 인자 (--execute 인데 --confirm 없음)

---

## 2. 디렉토리 레이아웃

```
.agent/shared-brain/
├── active-tasks.md          # 원본 (in-place edit 대상)
├── handoff.md               # 원본
├── cross-agent-review.md    # 원본
├── archive/
│   ├── INDEX.md             # 본 스크립트가 자동 갱신
│   ├── .backup/
│   │   ├── 20260519-090000/
│   │   │   ├── active-tasks.md      # rollback 용
│   │   │   ├── handoff.md
│   │   │   └── cross-agent-review.md
│   │   └── 20260526-090000/
│   │       └── ...
│   ├── 2026-04/
│   │   ├── active-tasks-completed.md
│   │   ├── handoff.md
│   │   └── cross-agent-review.md
│   └── 2026-05/
│       └── ...
```

---

## 3. Parsing 규칙

### 3.1 active-tasks.md (Rule R1)

**Block 단위**: `##` (h2) 또는 `###` (h3) heading 부터 다음 동급 heading 직전까지.

**Archive 후보 식별**:
- block 안에 `[x]` checkmark 가 있고
- block 의 timestamp / 날짜 추출 가능 (heading 또는 본문 내 `YYYY-MM-DD` 패턴)
- timestamp 가 `now() - age_days` 보다 오래된 경우

**유지 대상 (archive 안 함)**:
- block 안에 `[ ]` unchecked 가 1개 이상 남아있는 경우
- block heading 에 "📅 Weekly", "🟣 Strategy Lead", "Phase" 등 운영 marker
- timestamp 가 없거나 7일 이내

**예시**:
```markdown
## ✅ Completed: Sora Telegram 안정화 (2026-04-29, Claude Opus 4.7)
- [x] BOT_MATCHERS self-conflict fix
- [x] OWNER_WHITELIST 동적 11
... (block 끝)
```
→ Archive (all `[x]`, 30일+ 이전)

```markdown
## 🟣 Strategy Lead Weekly Review #5 (2026-05-04)
- [x] 7일 정리
- [ ] 다음 주 우선순위 결정
```
→ 유지 (`[ ]` 1개 + Weekly marker)

### 3.2 handoff.md (Rule R2)

**Section 단위**: `## YYYY-MM-DD ...` 패턴 또는 `# Handoff: ...` heading 부터 다음 같은 패턴 직전까지.

**Archive 후보 식별**:
- section heading 의 timestamp 가 `now() - age_days` 보다 오래된 경우
- 단, 최근 7일치는 무조건 유지 (Tier 1 "recent" 조건)

**유지 대상**:
- 최근 7일 이내 section
- "Pending verification" 또는 "Owner action 대기" 가 있는 section

### 3.3 cross-agent-review.md (Rule R3)

**Entry 단위**: `- [x] \`ccr-...\`` checkmark 부터 다음 `- [x]` 또는 `- [ ]` 직전까지.

**Archive 후보 식별**:
- entry 가 `- [x]` checked
- `result: new_signal | no_new_signal | failed` 가 있음
- timestamp (entry ID `ccr-YYYYMMDD-HHMMSS`) 가 30일+ 이전

**유지 대상**:
- `## Active` section 의 entry (checked 아님)
- 최근 30일 이내 entry

---

## 4. Atomic Write 패턴

원본 파일 수정 시 **반드시 atomic**:

```python
def atomic_write(target: Path, content: str) -> None:
    """Write content to target atomically via temp file + fsync + rename."""
    tmp = target.with_suffix(target.suffix + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        # Windows: target 이 존재하면 rename 실패. 그래서 replace 사용
        os.replace(tmp, target)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise
```

**Archive 파일도 atomic append**:
- 기존 archive 파일 읽기 → 새 content 추가 → atomic write
- 또는 lock file (`.lock`) 으로 동시성 보호

---

## 5. Backup 의무

`--execute` 모드에서 **반드시**:

```python
def create_backup(root: Path, files: list[Path]) -> Path:
    timestamp = datetime.now(KST).strftime("%Y%m%d-%H%M%S")
    backup_dir = root / ".agent/shared-brain/archive/.backup" / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    for f in files:
        shutil.copy2(f, backup_dir / f.name)
    return backup_dir
```

backup 실패 시 → exit 2 (safety abort).

---

## 6. Rollback 동작

```python
def rollback(root: Path, timestamp: str) -> None:
    backup_dir = root / ".agent/shared-brain/archive/.backup" / timestamp
    if not backup_dir.exists():
        raise FileNotFoundError(f"Backup not found: {backup_dir}")
    target_dir = root / ".agent/shared-brain"
    for f in backup_dir.iterdir():
        atomic_write(target_dir / f.name, f.read_text(encoding="utf-8"))
    # archive/YYYY-MM/ 디렉토리의 archived entry 는 유지 (수동 cleanup)
    print(f"[ROLLBACK] Restored from {backup_dir}")
```

archive 디렉토리는 유지 (rollback 후 owner 가 결정).

---

## 7. Audit Log

`~/.claude/audit/ssot_archive_<YYYY-MM-DD>.jsonl` 에 JSONL append:

```python
def audit(action: str, target: str, **kwargs):
    log_file = Path.home() / ".claude/audit" / f"ssot_archive_{datetime.now(KST).date()}.jsonl"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(KST).isoformat(),
        "action": action,
        "target": target,
        **kwargs,
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
```

**기록 의무 필드**:
- `ts` (KST ISO8601)
- `action` (archive / rollback / dry-run-summary / stats)
- `target` (file name)
- `entries` (archive 한 block / section 수)
- `kb_before` / `kb_after`
- `backup` (backup 디렉토리 경로)
- `hash_before` / `hash_after` (sha256, 무결성 검증)

---

## 8. Anchor Marker

원본 파일에서 block 제거 시, **anchor 1줄 보존**:

```markdown
<!-- ARCHIVED: 2026-04 → archive/2026-04/active-tasks-completed.md#L42 (2026-05-19 by archive_ssot.py) -->
```

→ 다음 세션이 "이거 처리했나?" 물을 때 marker 로 fallback 가능.

---

## 9. INDEX.md 자동 갱신

`.agent/shared-brain/archive/INDEX.md`:

```markdown
# Archive INDEX

> Auto-generated by archive_ssot.py. Do not edit by hand.
> Last updated: 2026-05-19T09:00:00+09:00

## 2026-04
- `2026-04/active-tasks-completed.md` (180 KB, 124 entries, archived 2026-05-19)
- `2026-04/handoff.md` (98 KB, 38 sections, archived 2026-05-19)
- `2026-04/cross-agent-review.md` (32 KB, 42 entries, archived 2026-05-19)

## 2026-05
- ... (다음 archive 시 추가)

## Search

- 검색: `grep -r "<keyword>" .agent/shared-brain/archive/`
- 특정 월: `cat .agent/shared-brain/archive/2026-04/*.md | grep "<keyword>"`
- 본 INDEX 재생성: `python scripts/agent/archive_ssot.py --stats`
```

---

## 10. Edge Cases

| Case | 처리 |
|---|---|
| 같은 timestamp 의 backup 디렉토리 이미 존재 | suffix `-2`, `-3` 추가 |
| archive 파일이 1 MB+ 비대화 | quarterly split (Phase 4+ 별도 task) |
| original file 이 lock 됨 (다른 프로세스) | retry 3회 + 60초 timeout, 실패 시 abort |
| age_days 계산 시 timestamp 파싱 실패 | 안전하게 "유지" (archive 안 함) |
| anchor marker 가 이미 있음 | duplicate 추가 안 함 |
| `[x]` 옆에 `[ ]` 도 있음 | 블록 유지 (안전 우선) |
| Weekly marker + `[x]` 만 있음 | 유지 (운영 marker 우선) |
| heading 없는 floating entry | heuristic 으로 timestamp 추정 |
| Windows path / encoding | utf-8 newline="\n" 강제 |
| CRLF 혼재 | LF 로 정규화 (atomic_write 시점) |

---

## 11. 안전 가드 (반드시 구현)

1. **--execute 는 --confirm 필수**: 둘 다 있어야만 실 변경
2. **backup 실패 → abort**: backup 디렉토리 생성 실패 시 즉시 exit 2
3. **atomic write 의무**: temp → fsync → rename 패턴 강제
4. **hash 검증**: before/after sha256 audit log 에 기록
5. **dry-run 자유**: --dry-run 은 항상 read-only, 부작용 0
6. **age_days >= 7 강제**: 7일 미만은 reject (recent 안전선)
7. **Active 블록 보호**: `[ ]` 또는 운영 marker 있으면 archive 후보 제외
8. **anchor marker**: 원본에 archive marker 1줄 추가 (검색 가능성 보존)
9. **rollback 항상 가능**: backup 디렉토리 + atomic restore

---

## 12. 테스트 시나리오 (Phase 1 작성 시)

| Test | Input | Expected |
|---|---|---|
| T1 | active-tasks.md 의 30일+ `[x]` block 1개 | archive 후보 1, 다른 block 영향 0 |
| T2 | handoff.md 의 7일 이내 section | archive 안 함 |
| T3 | ccr.md 의 `## Active` entry | archive 안 함 |
| T4 | `[x]` + `[ ]` 혼재 block | archive 안 함 (안전 우선) |
| T5 | --dry-run | 파일 변경 0 |
| T6 | --execute --confirm | backup + archive + audit 모두 정상 |
| T7 | --rollback <ts> | 원본 복원 + archive/* 는 유지 |
| T8 | --stats | INDEX.md 갱신 + 변경 0 |
| T9 | atomic_write 중간에 crash | temp 파일 정리 + 원본 무결성 보존 |
| T10 | concurrent run 2개 | lock 으로 두 번째 abort |

---

## 13. 다음 작업 (Phase 1 구현 시)

1. 본 SKELETON 기반으로 `archive_ssot.py` 작성 (~500 lines)
2. unit test `tests/agent/test_archive_ssot.py` 작성 (T1~T10)
3. dry-run 라이브 실행 → preview 검토
4. owner gate (Phase 2 진입 승인)
5. --execute --confirm 실 실행 (1회)
6. 다음 세션 token 적재 측정

---

## 14. 참조

- 마스터 설계: `.agent/knowledge/20260512_AGENT_DIR_OPTIMIZATION_MASTER_v1.md`
- 안전 가드 기준: `.agent/contracts/COLLABORATION_CONTRACT.md` §"Sensitive Action Rule"
- backup 저장: `.agent/knowledge/20260510_C_DRIVE_MANAGEMENT_POLICY.md` (D:/agent-cache/ 가능)
- audit log: `~/.claude/audit/` (Claude 표준 audit 디렉토리)
