# `.agent/shared-brain/archive/` Index

> 작성: 2026-05-12, Strategy Lead Claude Opus 4.7
> 목적: archive 디렉토리 사용 가이드 + rollback 절차

## 구조

```
archive/
├── INDEX.md                       (이 파일)
├── backup-20260512-archive/       (2026-05-12 archive 직전 원본 백업)
│   ├── handoff.md.bak             (123 KB, 2,193 lines)
│   ├── active-tasks.md.bak        (266 KB, 3,643 lines)
│   └── cross-agent-review.md.bak  (39 KB, 594 lines)
└── 2026-04/                       (2026-04 archived entries)
    ├── handoff.md                 (75 KB, 1,335 lines, 4/14~4/28)
    ├── active-tasks-history.md    (198 KB, 2,598 lines, Sora Enterprise / RAG / FA / Codex Rollout)
    └── cross-agent-review.md      (39 KB, 594 lines, 85 ccr checkpoints, 4/8~4/24)
```

## Rollback 절차

### 부분 rollback (특정 SSOT 만 복원)

```bash
cd D:/00.test/neo-genesis/.agent/shared-brain

# 예: handoff.md 복원
cp archive/backup-20260512-archive/handoff.md.bak handoff.md

# 예: active-tasks.md 복원
cp archive/backup-20260512-archive/active-tasks.md.bak active-tasks.md

# 예: cross-agent-review.md 복원
cp archive/backup-20260512-archive/cross-agent-review.md.bak cross-agent-review.md
```

### 전체 rollback

```bash
cd D:/00.test/neo-genesis/.agent/shared-brain
for f in handoff active-tasks cross-agent-review; do
    cp "archive/backup-20260512-archive/${f}.md.bak" "${f}.md"
done

# CLAUDE.md / GEMINI.md import chain v1 복원
cd D:/00.test/neo-genesis
git diff scripts/sync_agent_context.py  # 변경 확인
git checkout scripts/sync_agent_context.py  # v1 복원
python scripts/sync_agent_context.py --updated-by claude  # regenerate
```

## Archive Policy (2026-05-12 적용)

### Trigger
- **30일+ stale entries**: 자동 archive 후보 (현 수동, 향후 cron)
- **종료된 SSOT 그룹**: completed 100% 인 cross-agent-review 같은 경우 즉시 archive
- **size 임계값**: 단일 파일 100KB+ 이고 70%+ 가 historical → archive 검토

### Frequency
- **현 (수동)**: owner 명시 결정 시
- **목표 (자동)**: 매월 1일 00:00 KST (Phase 4 cron)

### Storage
- Format: 원본 markdown 그대로 (parsing 가능)
- Location: `archive/<YYYY-MM>/` 월별 디렉토리
- Backup: `archive/backup-<YYYYMMDD>-archive/` 직전 archive 시점 원본

### Retention
- archive 자체는 영구 보존 (디스크 비용 무시 가능)
- backup 은 90일 후 정리 (rollback window 보장)

## ROI 측정 (2026-05-12 archive 결과)

| 항목 | Before | After | 절감 |
|---|---|---|---|
| 3 SSOT 합산 size | 429 KB | 117 KB | **-72%** |
| CLAUDE.md import chain tokens | 122,593 | 30,398 | **-76%** |
| 세션당 비용 (Opus 4.7 input) | $1.84 | $0.46 | **-$1.38** |
| 월 30 세션 추정 절감 | — | — | **-$41.40** |
| 연 추정 절감 | — | — | **-$497** |

## 검증

```bash
# archive 디렉토리 정합
ls .agent/shared-brain/archive/
# 기대: INDEX.md + backup-20260512-archive/ + 2026-04/

# backup 무결성
md5sum archive/backup-20260512-archive/handoff.md.bak
md5sum archive/backup-20260512-archive/active-tasks.md.bak
md5sum archive/backup-20260512-archive/cross-agent-review.md.bak

# 본체 + archive 합산 ≈ 원본 (allowing for split overhead)
wc -c handoff.md archive/2026-04/handoff.md archive/backup-20260512-archive/handoff.md.bak
# 본체 47 KB + archive 75 KB ≈ backup 123 KB ✓
```

## 향후 archive cycle 권고

| 시점 | 작업 | 자동화 |
|---|---|---|
| 2026-06-12 (1개월 후) | 5월 entries → `archive/2026-05/` | 수동 (현 인프라) |
| 2026-07-12 | 6월 entries → `archive/2026-06/` | scripts/agent/archive_ssot.py 본 구현 후 자동 |
| 2026-08-01 (2개월 후 첫 자동) | cron `0 0 1 * *` 매월 1일 자동 archive | Phase 4 활성 |

## owner action

- archive 가 잘못됐다고 판단되면 즉시 `Rollback 절차` 수행
- archive 누락된 entry 가 본체 에 있다면 수동 split 권고
- 자동화 trigger (cron) 활성화는 owner G2 결정 (Phase 4)

👤 Strategy Lead Claude Opus 4.7
