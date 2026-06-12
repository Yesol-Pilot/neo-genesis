# 자율 콘텐츠 엔진 설계 — 세션 없이 도는 생성→게이트→예약→측정 (2026-06-12)

> 설계: Claude Fable 5 (owner "매번 너가 직접하는게 아니고 자율 구동되도록 설계")
> 문제: 부품(pipeline/schedule_planner/publish_queue_runner/monitoring)은 다 있으나 **묶는 무인 오케스트레이터 부재** → 매 턴 Fable이 수동 호출.
> 목표: cron 1개로 생성→게이트→(예약 or 보류)→측정 전 구간 무인.

## 0. 핵심 원리

1. **하루치 자율 실행**: cron이 매일 슬롯별로 콘텐츠를 생성하고 게이트를 돌려, 통과분만 자동 예약. 실패분은 로그+스킵(쓰레기 미게시).
2. **품질 안전판 (양산형 재발 차단)**: `publish_ready` AND `visually_distinct` 둘 다 통과만 예약 후보. 게이트가 자동 문지기.
3. **휴먼 리뷰 게이트 플래그** (`AINO_AUTONOMOUS_PUBLISH`):
   - `false`(현재, 비주얼 안정화 전): 생성·게이트·큐까지 자율, **예약 직전 보류** + 텔레그램으로 "N편 준비됨, storyboard 확인 후 승인" 1회 알림.
   - `true`(비주얼 신뢰 후): 게이트 통과분 자동 예약까지 무인. owner가 플립.
4. **정직 로깅**: 매 실행이 무엇을 생성/게이트결과/취한 액션을 JSON 로그. 거짓 진행 0.

## 1. 오케스트레이터 (W14 구현)

`scripts/revenue_os/autonomous_content_cron.py`:
```
일일 실행:
  1. 오늘 미충족 슬롯 파악 (schedule_planner 3일 플랜 + 기예약 차감)
  2. 슬롯별 포맷 결정 (§주간 믹스: ranking 2 / narrative 2 / briefing ≤2)
  3. 각 슬롯 콘텐츠 생성 (pipeline.run_for_topic, 토픽=뉴스풀 or identity_topic_pool 폴백, 키네틱 카드 비주얼)
  4. 게이트: publish_ready + visually_distinct 검증
  5. 통과분 → publish_queue 빌드
  6. AINO_AUTONOMOUS_PUBLISH==true 면 publish_queue_runner --mode schedule 자동 실행
     false 면 큐 보류 + 텔레그램 "준비됨" 알림 (storyboard 경로 포함)
  7. 실행 로그 → output/tiktok_aino_autonomous/run_<date>.json
  8. 비용: Gemini 페이서 80%+ 면 생성 중단(보수화)
```

## 2. 트리거 체계

- **codex automation `aino-autonomous-content`** 매일 07:00 KST (게시 슬롯 08:10 전 생성 여유).
- 23:30 롤업(기존)이 성과 측정 → 다음날 피드백 루프가 토픽/포맷 가중치 자동 조정 (기존 performance_feedback 연결).
- 즉: 07:00 생성 → 게이트 → 예약/보류 / 08:10·11:20·19:30 게시 / 23:30 측정 → 다음날 반영. **완전 순환.**

## 3. 707 자율 (W15, 별도)

707도 동형: `autonomous_ep_cron.py` — brief 로테이션 → Veo(또는 LTX 폴백) 생성 → 게이트 → @neogenesis5 업로드(전용크롬 9224). 단 707은 EP 서사 연속성이 있어 brief 큐를 미리 박제(EP003~EP010 골격).

## 4. 안전·거버넌스 (불변)

- 휴먼 리뷰 게이트 기본 ON (비주얼 안정화 전). 양산형 사고 재발 시 자동 false 복귀.
- 외부 행위(예약/업로드)는 owner 상시 자율권(2026-06-12 박제) 범위 내 — 단 게이트 통과분만.
- Gemini ₩10만 캡 + 페이서 보수화. Veo 별도 캡.
- 모든 실행 로그 + 주간 리뷰가 "무엇이 자율로 나갔나" 가시화.

## 5. 검증 (수락 기준)

- [ ] 1회 dry-run: 생성→게이트→큐까지 무인 실행, 로그 산출, 예약은 보류(플래그 false)
- [ ] 게이트 실패 콘텐츠가 큐에서 제외되는지 (쓰레기 차단)
- [ ] 페이서 80%+ 시 생성 중단 동작
- [ ] codex automation 등록 (매일 07:00)
- [ ] pytest 회귀 0

## 6. 의미

이게 완성되면 **Fable이 매 턴 워커를 띄울 필요가 없다.** 07:00 cron이 알아서 생성·게이트·예약하고, Fable은 (a) 비주얼 신뢰 확보 전까지 보류분 육안 승인 (b) 주간 리뷰로 전략 조정 (c) 실패·이상 시 개입 — 만 한다. owner 입사(6/29) 후 세션 없는 운영의 기반.
