# W2 작업지시서 — 정체성 토픽 풀 (스케줄 플래너 뉴스 의존 탈피, Codex 실행용)

> 설계: Claude. 배경: 2026-06-11 실측 — 뉴스 풀 12건 전부 `negative_performance_feedback` 스킵 → 3일 플랜 전 슬롯 `candidate_pool_exhausted` (정직 동작이나 ranking/narrative 슬롯까지 굶음).
> 문제 정의: ranking_battle·narrative_confession은 §4 스펙상 **정체성/에버그린 포맷**이라 당일 뉴스가 필요 없는데, 플래너 토픽 공급이 google_news_rss 단일 경로다.

## 1. 설계 (확정)

1. **신규 config**: `src/core/tiktok_aino/config/identity_topic_pool.json`
   ```json
   {
     "version": "identity_topic_pool_v1",
     "topics": [
       {"topic_id": "identity_001", "title": "역대 대통령 순위 TOP5 — 기준을 바꾸면 1위가 바뀝니다", "format_hint": "ranking_battle_65", "angle": "민주주의·위기 회복·유산 3기준 선언 후 5→1 역순 공개", "status": "used_20260611"},
       {"topic_id": "identity_002", "title": "나는 정치를 멀리했던 사람입니다 — 어느 기록자의 고백", "format_hint": "narrative_confession", "angle": "고백 훅 → 전환점 서사 → 입장 선언 → 결집 엔딩", "status": "in_progress_w1"},
       {"topic_id": "identity_003", "title": "역대 대통령 연설 순위 TOP5 — 한 문장이 시대를 바꿨다", "format_hint": "ranking_battle_65", "angle": "연설 한 문장 기준 랭킹 (§4a 변주: 연설)", "status": "ready"},
       {"topic_id": "identity_004", "title": "민주주의가 무너질 뻔한 순간 TOP5 — 그리고 막아낸 사람들", "format_hint": "ranking_battle_65", "angle": "위기 장면 랭킹 + 시민 서사 (§4a 변주: 장면)", "status": "ready"},
       {"topic_id": "identity_005", "title": "댓글로 가장 싸운 주제 TOP5 — 우리 계정 기록 공개", "format_hint": "ranking_battle_65", "angle": "계정 자체 데이터 랭킹 (시리즈 정체성 강화)", "status": "ready"}
     ]
   }
   ```
2. **플래너 폴백 배선** (`schedule_planner.py`): 슬롯의 format이 `ranking_battle_65` 또는 `narrative_confession`이고 뉴스 후보 풀이 소진(`candidate_pool_exhausted` 직전)이면, identity_topic_pool에서 `status=="ready"` && format_hint 일치 첫 토픽을 사용. **reformed_briefing 슬롯은 폴백 금지** (뉴스 기반 포맷 — 정직 공백 유지).
3. 사용 시 plan 산출물에 `topic_source: "identity_topic_pool"` 명시 (거짓 디스커버리 금지 — 뉴스에서 나온 척 금지).
4. status 갱신은 하지 않음 (read-only 소비; used 마킹은 후속 작업).

## 2. 수락 기준

- [ ] 신규 pytest 2개 이상 (tests/core/test_tiktok_aino_tts.py에 추가): ① 뉴스 풀 전멸 시 ranking/narrative 슬롯이 identity 풀로 채워지고 `topic_source` 명시 ② briefing 슬롯은 여전히 `candidate_pool_exhausted` (폴백 안 함)
- [ ] 기존 스위트 회귀 0: `pytest tests/core/test_tiktok_aino_tts.py -q` 전체 green (특히 `test_schedule_plan_does_not_fallback_to_default_topic_when_candidates_exhausted` 보존 — identity 폴백은 명시적 출처 표기가 있으므로 "default topic 날조"와 다름을 테스트 의도 주석으로 구분)
- [ ] 라이브 검증: `python -m src.core.tiktok_aino.schedule_planner --days 3 --output-dir output/tiktok_aino_schedule_plans` 실행 → ranking/narrative 슬롯 ready_for_generation 또는 최소 topic 채움 확인, 결과를 `D:\005.output\tmp\w2_identity_pool_result.md`에 기록
- [ ] config JSON `python -m json.tool` 파싱 통과

## 3. 금지

게시/예약, git commit/push, pipeline.py·hot_topic_strategy.json 수정 금지 (W1과 파일 충돌 방지 — W2는 schedule_planner.py + planning_strategy.json(필요시) + 신규 config + 테스트 파일만).
python은 `C:\Users\yesol\miniconda3\python.exe` 사용.
