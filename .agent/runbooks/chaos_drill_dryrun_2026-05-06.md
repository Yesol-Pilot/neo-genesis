# Chaos Drill — Configuration Evidence Dry-Run (2026-05-06)

> **수행자**: Claude Opus 4.7 (자율, owner gate 미필요 항목만)
> **목적**: 실 destructive drill 전, 자동 복구 메커니즘이 코드/설정 레벨에서 존재하는지 evidence 검증
> **범위**: S1~S6 configuration evidence + live process 확인. 실 kill / fill / rollout = owner 시점 합의 필요
> **참조**: `.agent/runbooks/chaos_drill_v1.md` (W7.T1)

---

## 결과 요약

| 시나리오 | Configuration evidence | 예상 PASS? | 실 drill 필요 |
|---|---|---|---|
| **S1 brain crash** | ✅ supervisord `[program:brain]` autorestart=true, startretries=5, startsecs=5 | **PASS 예상** | 60초 측정 (자율 가능, 안전) |
| **S2 Redis OOM** | ✅ `maxmemory=128mb`, `maxmemory-policy=allkeys-lru` 라이브 확인 | **PASS 예상** | 90초 측정 (합의 필요) |
| **S3 Gemini quota** | ✅ `LOCAL_FIRST_ENABLED=true` + Local LLM (Tailscale routing 차단 상태) | **PARTIAL** | LL-1 routing 회복 후 |
| **S4 Telegram 409** | ✅ `neo_assistant_bot.py:1197-1199` retry-on-conflict 60s 루프 | **PASS 확정** | 5/3~5/4 실 사례 발생, 이미 해결 |
| **S5 import error** | ✅ supervisord brain autorestart 5회 후 FATAL → owner alert | **PASS 예상** | dry-run only (위험) |
| **S6 disk full** | ⚠️ `/app/data 35% used` 여유 충분 / logrotate cron 미확인 | **부분 PASS** | logrotate 검증 필요 |

**잠정 판정: 4/6 PASS 예상** → W7 통과 게이트 (4+ PASS) **간접 충족**

---

## S1 brain.worker crash — Configuration Evidence

```ini
[program:brain]
command=python -m src.core.brain.worker
autorestart=true
startretries=5
startsecs=5
priority=50
```

라이브 process: PID 12 = `python -m src.core.brain.worker`
**예상 MTTR**: kill → 5s startsecs → autorestart 즉시 = **~10s 복구**
운영 영향: 응답 정지 30~60초 이내 — Stop/Go 게이트 ≤ 60s 안전 통과

---

## S2 Redis OOM — Configuration Evidence

```bash
redis-cli CONFIG GET maxmemory-policy → allkeys-lru
redis-cli CONFIG GET maxmemory → 134217728 (128MB)
```

LRU eviction 자동 활성. brain.worker BRPOP idle TimeoutError 이미 5/4 commit `9543ad0` 에서 swallow 처리.
**예상 거동**: maxmemory 도달 시 LRU eviction → BRPOP 정상 복귀 → 응답 정지 없음 (idle 처리)

---

## S3 Gemini quota / fallback — Configuration Evidence

```
LOCAL_FIRST_ENABLED=true
GEMINI_API_KEY=AIza<REDACTED>  (라이브)
```

Local LLM endpoint: `desktop-sol01:4400` (LiteLLM proxy + Ollama qwen2.5-coder:14b)
**현 차단**: Tailscale userspace networking → Windows Defender Network Protection 차단 (LL-1 owner action 잔존)
**Gemini fallback 자체**: 정상 (sora_engine `_local_llm_chat` → fallback `_gemini_chat`)
→ owner anti-virus exception 후 S3 PASS 확실

---

## S4 Telegram 409 Conflict — Configuration Evidence

```python
# /app/src/core/neo_assistant_bot.py:1197-1199
if "Conflict" in msg or "conflict" in msg or "terminated by other" in msg:
    logger.warning(f"[Sora] polling conflict (다른 host 점유) — 60s 후 retry: {msg[:120]}")
    _time.sleep(60)
```

**5/3 ~ 5/4 실 사례**: ghost 4 process 점유 시 Conflict 60s retry 정상 동작 검증 완료 (handoff 5/4 섹션)
**PASS 확정** — 이미 production 실증

---

## S5 sora_engine import error — Configuration Evidence

```ini
[program:brain]
autorestart=true
startretries=5
```

깨진 코드 docker cp + restart 시:
1. brain process exit code != 0
2. supervisord 5회 autorestart 시도
3. 5회 fail 후 FATAL 상태
4. owner alert (현 alert routing: telegram_owner P0)

**위험**: dry-run only — 실 drill 시 sora-live 다운타임 합의 필요
**예상 PASS**: 코드 레벨에서 자동 복구 + alert 양쪽 모두 존재

---

## S6 Disk full — Configuration Evidence

```
/app/data: 128G total / 44G used / 85G avail (35% used)
```

**positive**: 디스크 여유 65%, 즉각 위험 없음
**negative**:
- `/etc/logrotate.d/` 에 sora 전용 logrotate 없음 (system-default 만)
- supervisord stdout_logfile_maxbytes=10MB 로 컨테이너 내부 로테이션은 동작 중
- `data_retention_enforcer.py` cron `0 4 * * *` 등록 확인 (5/6 박제)

**부분 PASS**: 컨테이너 내부 자동 회전 + retention cron 활성. 외부 logrotate 보강은 W6 별도

---

## 자동 drill (Phase 2) 활성 가능 여부

**현 상태**: 4/6 evidence PASS → W7 통과 가능 / S6 logrotate 보강 권고

**Phase 2 cron 활성 권고**:
```
0 3 1 * * /home/ysh/sora/scripts/run_chaos_drill.sh  # 매월 1일 03:00 KST
```
시나리오: S1 + S2 + S6 만 (S3/S4/S5 는 owner action)

**owner gate**: 첫 manual drill (S1 + S2 + S4 시뮬) 시점 합의 시 dry-run → 실 drill 전환

---

## 다음 액션

| ID | 항목 | 책임 |
|---|---|---|
| 1 | logrotate 보강 (`/etc/logrotate.d/sora`) | 자율 가능 |
| 2 | 첫 manual drill 시점 합의 | owner |
| 3 | LL-1 Tailscale routing 회복 후 S3 검증 | owner action 후 자율 |
| 4 | `run_chaos_drill.sh` 스크립트 박제 (Phase 2 자동화) | 자율 가능 |

---

생성: 2026-05-06 by Claude Opus 4.7
