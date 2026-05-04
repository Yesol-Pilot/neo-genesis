# Sora Chaos Drill — 6 시나리오 v1

> **Master**: `20260428_SORA_ENTERPRISE_GRADE_MASTER_v1.md` (W7.T1)
> **Decision**: D3 — 첫 manual drill + 2회차부터 매월 1일 03:00 자동
> **목적**: sora-live 의 자동 복구 메커니즘 검증 (4/6 이상 PASS 시 운영 합격)
> **owner gate**: 실 drill 은 owner 시점 합의. dry-run 분석은 자율 가능.

---

## 시나리오 카탈로그

### S1. brain.worker crash
**유발**: `docker exec sora-live kill -9 <brain.worker pid>`
**기대 복구**:
1. supervisord 가 brain process autorestart (priority=20, startretries=5)
2. 30초 안에 `python -m src.core.brain.worker` 재기동
3. Redis 큐 재연결 + `[Brain] worker-N 가동` 로그
**측정**: kill 시각 → 정상 응답 복구 시각 (`/api/v2/chat` 200 응답) ≤ 60초
**runbook**: `.agent/runbooks/brain_crash.md`

### S2. Redis OOM
**유발**: redis 의 maxmemory 강제 fill (key 1만개 대량 SET)
**기대 복구**:
1. Redis maxmemory-policy=allkeys-lru → 자동 eviction
2. brain.worker 의 BRPOP 가 일시 stall 후 idle 정상 복귀
3. owner alert: 5분 이상 stall 시 P1 (없으면 무알림)
**측정**: 대량 SET 후 정상 큐 처리 복구 ≤ 90초
**runbook**: `.agent/runbooks/redis_oom.md`

### S3. Gemini API quota exceed (cloud fallback 차단)
**유발**: 환경변수 `GEMINI_API_KEY=invalid` 임시 변경 + sora-live restart
**기대 복구**:
1. Gemini 호출 실패 → Local LLM (qwen2.5-coder:14b) 로 자동 routing
2. 응답 quality 유지 (메모리 cross-turn / fastpath 정상)
3. 30분 후 quota 회복 가정으로 다시 Gemini 시도
**측정**: Gemini 차단 후 첫 응답 도착 시간 ≤ 30초
**runbook**: `.agent/runbooks/gemini_quota.md`
**주의**: Local LLM 도 down 이면 sora 사실상 정지 — 이 시나리오는 Local LLM 가동 전제

### S4. Telegram 409 Conflict (다른 host polling 충돌)
**유발**: 다른 host 에서 같은 token 으로 getUpdates 호출 (시뮬: 별도 docker container 에서)
**기대 복구**:
1. NeoAssistant.run() 의 retry-on-conflict 60s 루프 발동
2. 다른 host stop 시 즉시 polling 우승
**측정**: 다른 host 점유 시작 → owner 메시지 응답 도달 ≤ 90초 (다른 host stop 후)
**runbook**: `.agent/runbooks/telegram_409.md` ← 5/3 ~ 5/4 세션에서 실 사례 발생, 이미 해결

### S5. sora_engine import error (코드 배포 회귀)
**유발**: 깨진 코드 (예: SyntaxError) 를 sora_engine.py 에 docker cp + restart
**기대 복구**:
1. supervisord brain process exit code != 0 → autorestart (5회까지)
2. 5회 fail 시 supervisord 가 brain process FATAL 상태로 stop
3. owner alert: brain FATAL → telegram P0 alert
4. owner 가 git revert + docker cp 로 복구
**측정**: import error 발생 → owner alert 도달 ≤ 5분 / 정상 복구 = owner action 시간
**runbook**: `.agent/runbooks/sora_import_error.md`
**주의**: dry-run 만 가능 — 실 drill 은 sora-live 다운타임 허용 합의 필요

### S6. Disk full (logs / data 폭증)
**유발**: `dd if=/dev/zero of=/app/data/logs/fill.bin bs=1M count=10000` (10GB fill)
**기대 복구**:
1. logrotate (size_based) 가 brain.log 자동 회전
2. data_retention_enforcer (cron 04:00) 가 expired log 자동 purge
3. owner alert: 디스크 사용률 > 85% 시 telegram P1
**측정**: fill 시각 → 정상 사용률 (<70%) 복구 ≤ 1시간
**runbook**: `.agent/runbooks/disk_full.md`

---

## 첫 drill 체크리스트 (owner manual, ~30분)

- [ ] **준비**: ysh-server 의 sora-live container backup 확인 (`docker commit sora-live sora-live-pre-chaos:$(date +%Y%m%d)`)
- [ ] **공지**: telegram alert "🧪 Chaos Drill 시작 — 약 30분간 sora 응답 불안정 가능"
- [ ] **S1 실행**: brain kill → 60초 측정
- [ ] **S2 실행**: Redis fill → 90초 측정
- [ ] **S4 실행**: ghost simulation (이미 실 사례 발생, 우회 가능)
- [ ] **S6 실행**: disk fill → 정리 후 ≤ 1시간
- [ ] **S3 / S5 보류**: 운영 영향 큼, 별도 시점 합의
- [ ] **결과 기록**: `.agent/shared-brain/chaos_drill_results.jsonl` (timestamp / scenario / mttr_seconds / pass)
- [ ] **owner 보고**: telegram "🧪 Drill 완료 — N/6 PASS"

---

## 자동 drill (Phase 2, 매월 1일 03:00 KST)

- ysh-server crontab: `0 3 1 * * /home/ysh/sora/scripts/run_chaos_drill.sh`
- 시나리오: S1 + S2 + S6 만 (S3/S4/S5 는 owner action 필요)
- 결과 자동 telegram alert (P1 규모 PASS 알림 / P0 FAIL 즉시 alert)

---

## 위험 통제

| 시나리오 | 운영 영향 | 자율 drill 가능? | owner gate? |
|---|---|---|---|
| S1 brain crash | 30~60초 응답 정지 | ✅ dry-run 분석만 | 실 drill = 합의 필요 |
| S2 Redis OOM | Redis stall ~90초 | ✅ | 합의 필요 |
| S3 Gemini quota | LLM fallback 검증 | ⚠️ Local LLM 가동 전제 | 합의 필요 |
| S4 Telegram 409 | polling 정지 | ✅ 이미 실 사례 | 자율 가능 (시뮬) |
| S5 import error | brain FATAL | ❌ 위험 | owner-only |
| S6 disk full | 디스크 IO 부하 | ⚠️ 다른 service 영향 | 합의 필요 |

---

## Stop/Go 게이트 (W7 통과 기준)

- 6 시나리오 중 4+ PASS → W7 통과, Phase 2 자동 drill 활성
- 3 이하 PASS → 미통과, 자동 복구 매커니즘 보강 + 재 drill
- S1/S4 가 둘 다 FAIL → P0 (가장 자주 발생하는 incident, 자동 복구 필수)
