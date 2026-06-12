# Neo Genesis AI-Native 자율 운영 아키텍처 v1 (2026-06-12)

> 설계: Claude Fable 5 (owner "매번 너가/owner가 하면 의미없다. 테스트 후 문제없으면 완벽한 파이프라인으로 구축, AI-native 자율 구동. API·CLI 자동화 효율적으로")
> 상위: 20260612_AUTONOMOUS_REVENUE_OS_v1.md (비용·엔진) / 본 문서 = **실행 자율화** 레이어

## 0. 결론 — 갭의 정확한 위치

이미 자율인 것(✅): 비용 페이서·수익 텔레메트리·주간리뷰·SBU 모니터 (cron 8종). **관측·거버넌스는 무인.**
아직 수동인 것(🔴): 콘텐츠 **생성·게이트·게시** / AIT **콘솔 입력·제출** / 707 **EP 생성·업로드**. = **실행(action)이 사람 루프.**

원인: 부품은 다 있는데 **(a) 묶는 오케스트레이터 부재 (b) 외부행위 자동화(브라우저)가 무인 신뢰성 부족.** 그래서 Fable이 매 턴 워커 띄우고 owner가 매번 콘솔 클릭.

## 1. 3-Plane 아키텍처 (각 계층 = 적합한 자동화 수단)

| Plane | 역할 | 자동화 수단 | 신뢰성 |
|---|---|---|---|
| **Control** (관측·판단) | 예산·수익·게이트·이상감지 | cron + Gemini API(분류/요약, 캡 내) | ✅ 가동 |
| **Generation** (콘텐츠 제작) | 영상·이미지·대본 생성 | pipeline(키네틱카드/Veo/LTX) + Codex CLI(코드변경) + Gemini API(discovery, 캡 내) | 🟡 W14 구축 중 |
| **Action** (외부 실행) | TikTok 게시·예약·프로필 / 콘솔 제출 | **인증 세션 + CDP 브라우저 자동화** / 가능시 API | 🔴 무인 신뢰성 = 핵심 갭 |

**효율 원칙 (API·CLI 분담)**:
- 코드/구현/반복 = **Codex CLI** (구독, 0). 무인 작업은 codex automation.
- 런타임 LLM(discovery·분류) = **Gemini API flash** (₩10만 캡, 페이서 가드).
- 영상 = Veo(707, Vertex 별도캡) / 키네틱카드(leftaino, 0) / LTX(폴백, 0).
- 관측·스케줄 = cron automation.
- **사람 = 법적 게이트(심사제출·결제·계정생성)만.** 그 외 0.

## 2. 자율 파이프라인 (구축 순서 — 각 단계 "Fable 테스트 → 무인화")

### P1. 콘텐츠 자율 (W14, 진행 중)
07:00 cron: 생성→게이트(publish_ready+visually_distinct)→예약/보류→23:30 측정→다음날 피드백. 휴먼리뷰 플래그(비주얼 안정화 전 ON). **검증: Fable이 dry-run으로 무인 동작 확인 후 cron 등록.**

### P2. 외부행위 무인 신뢰성 (W16, P1 다음 = 핵심)
문제: 오늘 콘솔 자동입력(W6/W10)이 카테고리 팝업 등에서 부분 실패 → 무인 불가 원인. 해결:
- **인증 세션 영구화**: leftaino(크롬9222)·707(9224) 전용 프로파일을 로그인 유지 + cron이 CDP attach. 세션 만료 감지 시 텔레그램 1회 재로그인 요청(사람 최소개입).
- **브라우저 자동화 견고화**: 셀렉터 폴백·재시도·실패시 정직 로그(거짓 성공 금지). TikTok 게시는 publish_queue_runner가 이미 검증됨(오늘 schedule 성공) → 이걸 cron이 호출.
- **API 우선**: TikTok Content Posting API / Apps in Toss API 존재분은 브라우저 대신 API (더 신뢰). 조사 후 가능분 전환.

### P3. 자가 치유·감지 (W17)
- 게이트 연속 실패·페이서 초과·세션 만료·cron 미발화 = 자동 감지 + 텔레그램 경보 (기존 모니터 확장).
- 양산형 재발(visually_distinct 하락) = 휴먼리뷰 플래그 자동 ON 복귀.

### P4. 707 자율 (W15)
EP brief 큐(EP003~010 골격) → Veo/LTX 생성 → 게이트 → @neogenesis5 업로드. P2 외부행위 레이어 재사용.

## 3. 거버넌스 (불변)

- 사람 게이트 = 심사제출·결제·신규계정·정책위반판단. 그 외 자율.
- 거짓 메트릭/거짓 성공 0. 실패는 로그+경보.
- Fable 역할: **구축·검증·전략조정·이상개입.** 정상 운영은 무인.
- 6/29 owner 입사 후 = 본 파이프라인이 기본 운영자. Fable은 주간 개입.

## 4. 성공 기준 (이게 되면 "AI-native 자율")

- [ ] 하루 동안 Fable 0개입으로: 콘텐츠 생성·게이트·예약·게시·측정 완주 (P1+P2)
- [ ] owner 0개입으로: 정상일 운영 (법적 게이트일만 알림)
- [ ] 이상 시에만 사람 호출 (세션만료·심사반려·정책)
- [ ] 비용 캡 내 자동 보수화

## 5. 빌드 현황

- ✅ Control plane (cron 8종)
- 🟡 P1 콘텐츠 자율 (W14)
- ⬜ P2 외부행위 견고화 (W16) ← 핵심
- ⬜ P3 자가치유 (W17)
- ⬜ P4 707 자율 (W15)

## 6. 오라클 24/7 plane (owner "오라클 서버도 24시간용으로", 2026-06-12)

**실측 제약**: oracle-worker-1 = 2vCPU burst / RAM 954MB(가용 ~520MB) / Python3.12 / git O, node X / GPU X / gcloud·GCP SA X / 크레덴셜 최소(96B). → 영상생성·브라우저자동화·GCP호출·node빌드 **불가**. 경량 API cron·stdlib·watchdog **가능**.

**역할 분담 (확정)**:
| 호스트 | 담당 | 이유 |
|---|---|---|
| **oracle-worker-1** (always-on) | ① 트래픽 텔레메트리(PostHog, urllib stdlib) ② **cron-health 워치독**(데스크탑 cron 발화·산출 검증, 미발화 시 경보) ③ 알림 릴레이 ④ SBU sitemap(기존) | PC 꺼져도 도는 24/7 안전망. self-monitor는 죽을 수 있는 데스크탑이 아닌 always-on에서만 유효 |
| **desktop-home** (GPU·세션) | 콘텐츠 생성(Veo/키네틱/LTX) / 브라우저 액션(TikTok·콘솔 CDP) / GCP 예산페이서(gcloud) / pytest | GPU + 로그인 크롬세션 + GCP 인증 필요 |

**핵심 가치**: 오라클 워치독이 "데스크탑 자율 파이프라인이 실제로 돌았나"를 24/7 감시 → PC 꺼짐·cron 실패·세션 만료를 always-on에서 잡아 경보. = P3 자가치유의 토대. 데스크탑이 자기 자신 죽음을 못 알리는 문제 해결.

**셋업 (W18)**: 오라클에 (a) telemetry 스크립트 + PostHog/Telegram 키 배치 (b) cron-health 워치독 스크립트 (데스크탑 output/revenue_os/*.json mtime + git 최신커밋 시각 원격 점검, stale 시 NEO_ALERT DM) (c) crontab 등록 (텔레메트리 09:35 / 워치독 매시). 키는 credentials.env 600 권한, 원문 비노출.
