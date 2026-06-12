# Neo Genesis 자율 수익 기업 OS v1 (2026-06-12)

> 설계: Claude Fable 5 (owner 지시: "전체 통합, Gemini API 월 10만원 한도, CLI 적극 활용, 자율 수익 기업 설계·구현. 단순 작업은 하위 모델·Codex 위임. 6/22까지 메인=Fable, 수행=하위 에이전트")
> 구현: Codex CLI 워커 (병렬) + Claude 하위 모델 서브에이전트
> 선행 정본: `20260512_REVENUE_PATH_RESEARCH_v1.md` (B1+C2 경로) / `20260611_OPEX_BUDGET_5M_PLAN_v1.md` (트리거형 집행)

## 0. 결론 (한 문단)

Neo Genesis 의 LLM 비용 구조를 **"종량 = Gemini 단일 채널 월 ₩100,000 hard cap / 나머지 전부 구독 CLI(한계비용 0)"** 로 고정하고, 수익 엔진 4개(AIT 팩토리 → TikTok 성장 → FINITE 결제 배선 → SBU 패시브)를 cron 기반 자율 루프로 묶는다. 6/22(owner 입사 D-7)까지 Fable 이 설계·감사 메인, Codex/하위 모델이 전 구현을 수행하며, 그 이후는 **세션 없이도 도는 자율 루프 + 주간 수익 리뷰**가 기본 운영 모드가 된다. 한도는 캡이지 목표가 아니다 — 실사용은 페이서가 일일 추적하고 80%에서 경보한다.

## 1. 모델·실행 계층 (비용 아키텍처)

| 계층 | 자원 | 비용 | 용도 |
|---|---|---|---|
| L3 오케스트레이터 | **Claude Fable 5 (1M)** — 본 세션 | Max 구독 (0 추가) | 설계·감사·G1 판단·커밋 (6/22까지 메인) |
| L2 실행 워커 | **Codex CLI** (gpt-5.5) + **Gemini CLI** (Ultra 구독) + Claude 하위 서브에이전트 (sonnet/haiku) | 구독 (0 추가) | 구현·테스트·반복 작업·조사 |
| L1 서비스 런타임 | **Gemini API** (flash 계열 기본) | **월 ₩100,000 hard cap** | 제품 안에서 도는 LLM: sora 어시, tiktok 파이프라인 discovery/이미지(gemini_api 모드), 향후 제품 기능 |
| L0 로컬 | Ollama (qwen 등) | 0 | 비민감 보조·분류·임베딩 폴백 |

**라우팅 룰 (박제)**:
1. 에이전트 개발·운영 작업에 API 종량 호출 금지 — CLI 만 사용 (기존 sora_subscriptions 룰 확대 적용).
2. 서비스 런타임 Gemini 호출은 **flash 계열 기본** (pro 는 명시 사유 + 페이서 여유 확인 시만). 모델명은 ListModels 실측 후 config 화 (하드코딩 금지).
3. 단순·반복·대량 작업 = Codex CLI 또는 haiku/sonnet 서브에이전트. Fable 은 설계·감사·통합 판단만.
4. 일일 페이스 = ₩3,300/일. 페이서가 80%(월 ₩80K) 도달 시 텔레그램 경보 + 비필수 런타임 호출 자동 보수화(이미지 local 모드 폴백 등).
5. 기존 안전망 유지: GCP billing budget ₩100K + AI Studio auto-pause (battlefield 사후 검증됨) = 이중 방어.

OPEX 플랜과의 정합: 5M 플랜의 "AI API 버퍼 월 5만 cap"은 owner 신규 지시(Gemini 월 10만)로 **상향 대체**. 트리거형 정신(쓰는 게 목표가 아님)은 유지.

## 2. 수익 엔진 포트폴리오 (30일 내 첫 수익 가능성 순)

| # | 엔진 | 수익 모델 | 상태 | 다음 게이트 | 담당 |
|---|---|---|---|---|---|
| R1 | **AIT 팩토리 (SBU13)** | Toss 미니앱 광고 (수취 59.5%) | 이사체크봇 콘솔 업로드됨, 쿠폰만료봇 88·구독정리봇 85 ready | 콘솔 앱 생성(owner 1분/개) → 빌드·업로드(자동) → 심사 제출(owner) | Codex 양산 + Claude 품질게이트 |
| R2 | **TikTok @leftaino** | Creator Rewards (1분+ 영상 — 새 포맷 60~78s 충족) | 새 파이프라인 라이브, ranking 1호 publish_ready | 팔로워 10K + 30일 조회 10만 (KR 조건) → T7 실험으로 성장 우선, 수익은 후행 | 파이프라인 자율 + 주간 리뷰 |
| R3 | **FINITE (daysleft.io)** | 구독/결제 (RevenueCat placeholder 해소) | 트래픽 P0 별도 세션 진행 중 — **충돌 방지: 본 OS 는 결제 배선 설계만, 코드 변경은 그 세션 종료 후** | 결제 수단 결정(web=Stripe 류, owner G2) | 보류 슬롯 |
| R4 | **SBU 패시브** (toolpick 쿠팡 88글, AdSense, kott) | 어필리에이트/광고 | 유지 모드 (100k 폐기 판정 유지) | 쿠팡 글 도메인 이전(기존 펜딩) + AdSense 상태 점검 (저노력) | 하위 에이전트 점검만 |
| R5 | **ROOM707** (@neogenesis5) | TikTok 숏폼 IP (장기: Creator Rewards 2계정째) | EP002 완성 (P0 5결함 수리, 18s) — **로컬 LTX = 한계비용 ₩0** | EP002 업로드(owner 모바일 — 팩 전송됨) → 반응 보고 EP003 자율 생산 | brief-driven 파이프라인 (gen_ep_ltx_v2) |
| — | koreanllm B2B | 영업 중량급 | idea 단계 | **6/22까지 스코프 아웃** | — |

## 3. 자율 루프 (cron 스택 — 세션 없이 도는 것)

기존 가동: 온톨로지 daily (Task Scheduler) / SBU sitemap 09:00 (oracle-worker-1) / TikTok 롤업 23:30 (codex automation, 실발화 검증됨) / 주간 Telegram 리포트.

신규 (이번 구현 wave):
- **gemini-budget-pacer** (일일): 사용량 수집 → 페이스 판정 → 80% 경보 (W4)
- **revenue-telemetry** (일일): 수익·프록시 신호 통합 JSON — 수집 불가 항목은 `no_data` 정직 표기 (W5)
- **weekly-revenue-review** (월 09:00): 엔진별 게이트 진척 + 다음 주 우선순위 — 기존 주간 리포트에 통합

## 4. 거버넌스 (불변)

- 외부 공개 행위(게시·심사 제출·결제·계정 변경) = owner 명시 게이트. 자율 루프는 준비까지만.
- 거짓 메트릭 금지: 수집 불가 = `no_data`/`not_capturable`. 날조 fallback 금지.
- 워커 커밋 금지 — Fable 감사 후 커밋 (git 충돌 + 품질 게이트 단일화).
- 6/22 이후: owner 입사 → 세션 작업은 야간/주말, 주간 루프가 기본. Fable 메인 룰은 6/22 까지 (이후 재지정 대기).

## 5. 구현 웨이브 (위임 현황)

- W1 (Codex, 진행 중): narrative_confession 1호 — R2 콘텐츠 볼륨
- W2 (Codex, ✅ 커밋): 정체성 토픽 풀 — R2 자율성
- W3 (Codex, ✅): 롤업 자동화 감사 — R2 측정
- **W4 (Codex, 신규): Gemini 예산 페이서** — `scripts/revenue_os/gemini_budget_pacer.py` + codex automation 등록 제안
- **W5 (Codex, 신규): 수익 텔레메트리** — `scripts/revenue_os/revenue_telemetry.py` + `output/revenue_os/revenue_telemetry_latest.json`
- W6 (예약): AIT 쿠폰만료봇 양산 (R1 — owner 콘솔 앱 생성 후 트리거)

## 6. 리스크 (정직)

- Creator Rewards 는 팔로워 10K 선행 — R2 수익은 빨라야 수주 뒤. 단기 실수익은 R1 이 유일한 현실 경로.
- Gemini 사용량의 정확한 원화 환산은 GCP 청구 지연(수시간~1일) 있음 — 페이서는 추정치 + 청구 대조 이중 트랙.
- sora 어시는 brain worker 고장으로 다운 (6/8~) — L1 수요의 큰 축이 현재 0. 수리는 별도 결정(WSL 재기동 보류 판정 유지).

## 7. 개정 이력

- **v1.1 (2026-06-12 13:28)**: owner 명시 지시로 §4 외부 행위 게이트에 예외 신설 — **TikTok @leftaino 채널 운영(업로드·예약·프로필 변경·채널 관리)은 상시 자율**. 콘텐츠 가드(§5 정신: 선거 오정보 금지·AI 고지·publish_ready 게이트)는 불변. 신규 플랫폼·결제·심사 제출은 여전히 owner 게이트.
