# Neo Genesis 사업 전면 감사 + 수익 전환 전략 v1 (2026-06-11)

> **작성:** Claude (Fable 5, Strategy Lead) — etribe-yesol에서 집PC 원격 감사
> **방법:** 멀티에이전트 워크플로우 (감사 5 병렬: repo/live/PostHog/quant/Vercel → 3인 심사단: 냉정한 투자자·PM/DA·1인 운영 전문가 → 수렴 → 완전성 비평)
> **owner 명령:** "집pc 네오제네시스 기업 분석하고 고도화 및 개선해 정말 1인 자율 ai native 기업으로서 성공하고 돈을 벌수 있도록"

---

## 0. Executive Summary

**3인 심사단 만장일치: 현재 Neo Genesis는 "14개 제품 · 16개 라이브 표면 · 실작동 결제 장치 0건" — 만드는 능력은 입증됐으나 파는 행위를 한 번도 완결하지 못했다.** 인프라(SSOT·멀티에이전트·GEO)에 들어간 공수가 시장 접점 공수를 압도했고, 그 SSOT 운영 루프조차 5/11 이후 동결됐다.

데이터가 지지하는 신호는 단 셋:
1. **finite (DaysLeft, daysleft.io)** — 6월 43커밋의 압도적 모멘텀, 결제 직전 단계. **포트폴리오 유일 주력.**
2. **toolpick.dev** — 유일하게 검증된 오가닉 수요 (실인간 125~150명/월, 90일 7배 성장, ChatGPT referral 14건).
3. **앱인토스 트랙 (mintlab + ait)** — 유일하게 유통이 플랫폼에 내장된 트랙, 병목이 코드가 아닌 서류.

**다음 90일의 유일한 KPI = 첫 결제 1건.** 신규 제품 착수 전면 금지.

---

## 1. 감사 사실 스냅샷 (2026-06-11 라이브 검증)

### 제품 포트폴리오 (D:\00.test\002.products-sbu + 006.games-labs)
| 제품 | 상태 | 수익화 | 판정 |
|---|---|---|---|
| **012.finite (DaysLeft)** | 6월 43커밋, daysleft.io 라이브, `feat/finite-mvp-launch` 브랜치에서 MVP 작업 중 (6/11 retention/viral loop 설계 진행) | 구독 페이지 있음, 결제 TODO. 계측은 `finite-min` 커스텀 lib 라이브 (6/9 618 이벤트) | 🟢 **주력** |
| **mintlab + 013.ait (앱인토스)** | 게임 3종 완성 (G-Score 100/100), 6/10-11 활발 | Phase 0 행정 게이트 (사업자등록·등급분류·정산 실측) 대기 | 🟢 keep (행정 병행) |
| toolpick.dev | 6/10 배포, 콘텐츠 가동 | AdSense 마커, 제휴 없음 | 🟢 keep (전환 루프) |
| 011.room-707 | 6/11 수익 목적 공식 폐기 (TikTok 구조적 ₩0) | 없음 | 🔴 6/25 kill-gate 그대로 집행 |
| 004.quant-bot v11 | 5/10 마지막 커밋, **VM TERMINATED 확인됨**, 5/12 이후 모든 테이블 쓰기 0 | PAPER 0거래, 실수익 0 | 🔴 아카이브 |
| quant-poc-multi-asset | 5/20 이후 22일 커밋 0 (12주 계획 W1 정지) | 없음 | 🔴 아카이브 |
| 005/006 Sora 앱·안드로이드 | 4/11 이후 정지 | 없음 (내부 도구) | 🟡 동결 (신규 투입 0) |
| 007/008 why-engine | Cloud Run **이미 제거됨 확인** | 없음 | 🔴 레포 아카이브 |
| 001/003/009/010 (ably·chatbot·koreanllm·healthcare) | 스캐폴드/미러/정지 | 없음 | 🔴 아카이브 |
| 구 11 SBU 롱테일 (sellkit/deploystack/finstack/craftdesk/aiforge/ur-wrong/reviewlab/whylab/ethica) | 라이브지만 30일 실트래픽 합계 <150명 | 광고 마커만 | 🟡 정적 방치 (투입 0) |

### 인프라/비용 사실 (이번 세션 직접 검증)
- **GCP VM 2대 (quant-bot, sora-vm) 모두 TERMINATED** — 컴퓨트 비용 누수 없음 (감사 우려 해소). 잔존 디스크 보관비 소액 (~$5-10/월 추정, 삭제는 owner G2).
- **Cloud Run에 why-engine 없음** (internal-ir-tool만 존재) — 비용 우려 해소.
- **Vercel 30 프로젝트**: 커스텀 도메인 13개 운영 + 방치 ~12개 + 중복 2개. reviewlab production CANCELED. finite 최신 배포는 preview (`feat/finite-mvp-launch` 브랜치 — main 머지 시 자동 해소, **임의 promote 금지**).
- **집PC SSOT(shared-brain) 5/11 동결** — 회사 운영 기록 루프 사망. 작업은 제품별 repo로 분산됨.

### Business Signal (PostHog, 30일, 합성 제거 기준)
- 실인간 수요 존재처는 **toolpick 1곳** (오가닉 125~150명/월, 90일 7배 성장) + review.neogenesis.app 142명.
- **AI referral 첫 실측**: ChatGPT 14건 + Claude 1건 — GEO 전략 첫 증거.
- 재방문(North Star) 30일 8명 = 사실상 0. "발견은 시작, 사용자화는 0" 단계.
- finite `finite-min` 계측 가동 중 (6/9 618 이벤트) — MVP 브랜치에서 추가 계측 작업 진행 중.

### Measurement Integrity (경고)
1. **[심각] `neo-sbu-direct` 합성 캡처가 현재도 매일 14~149건 유입 중** (30일 누적 2,947건 = 전체 70%). 발생원 차단 필요.
2. **[심각] toolpick `follow_intent` 이벤트가 사용자 94%에서 자동 발화** — 페이지 로드 발화 버그 의심. engagement 지표로 사용 금지.
3. toolpick $direct 84%가 CN/SG 봇 시그니처 — 실인간 판단은 오가닉 referral 기준만 사용.
4. 11개 사이트가 단일 PostHog 프로젝트 공유 — 모든 집계에 `$host` 필터 필수.
5. AdSense **실수익은 미조회** (계정 승인 상태 미확인) — "매출 0" 단정의 잔존 불확실성.

---

## 2. 최종 판정 (3인 심사단 수렴 + 비평 반영)

### Kill (만장일치)
1. **퀀트 트랙 전체** (quant-bot v11 + quant-poc-multi-asset) — 데이터가 두 번 사망 증명 (A2 0/108 sweep 전멸 + 30일 0거래 + W1 정지). 아카이브. heoyesol.kr/quant 좀비 대시보드(4/10 정지)는 제거 또는 "운영 종료" 표기.
2. **스캐폴드 5종 아카이브**: ably-ai-closet(빈 템플릿 라이브 — 평판 마이너스), nextjs-ai-chatbot, sora-android, healthcare-app, koreanllm(제품 아님 — 워크스페이스 미러).
3. **why-engine 레포 아카이브** (Cloud Run은 이미 제거됨).
4. **room-707 — 6/25 kill-gate 그대로 집행, 연장 금지.** 단 비평 반영: 6/25 시점 게이트 수치(followers/episodes/lore댓글) 측정 주체를 지정해야 함.
5. **SBU 롱테일 신규 투입 전면 중단** — 정적 방치 (비용 0이므로 라이브 유지, 공수 1원도 금지).
6. ~~Vercel 방치 12개 일괄 삭제~~ → **[비평 정정] 식별 후 삭제**: `one-pyeong-store-privacy`(6/9 배포 — 앱인토스 앱의 개인정보처리방침일 가능성 높음, 삭제 금지), `frontend`(5/29, 정체 확인 필요), `analytics-cron-daemon`(실동작 확인 필요). 나머지(toss-portfolio/sol/forte/est-minigame/002-personal-scheduler/jobsearch-pipeline 등)는 삭제 후보 확정.

### Keep
- **앱인토스 패밀리** — [비평 정정] kill 트리거는 "D+30 행정 통과"가 아니라 **"오너 액션 완료"(서류 제출 완료 = 게이트 통과)** 기준. 관청 리드타임은 오너 통제 밖.
- **neogenesis.app + heoyesol.kr** — 정적 유지. 이것은 제품이 아니라 이력서/GEO 인용 허브. 개발 시간 투입 금지.
- **kott.kr / review.neogenesis.app** — 패시브 유지, GSC 인덱싱·발행 워커 생사 확인 후 재평가.
- **AdSense 계정 자산** (pub-5874227298630347) — 승인 상태 확인 후 toolpick 등 실트래픽 도메인 재연결 검토.

### Double-down (만장일치 2건)
1. **finite (DaysLeft)** — 계측→결제→유통 순서. 오너가 이미 retention/viral loop 작업 중 (6/11 설계 문서 확인) → 방향 정확함. 다음 병목은 **결제 레일**.
2. **toolpick 오가닉→전환 루프** — follow_intent 버그 수정 + 상위 비교/대안 페이지 10개에 SaaS 제휴 링크 + 재방문 구조.

---

## 3. 90일 머니 패스 (결제 제공자 정정 반영)

**주력: finite 결제 개통.**
- **[v1.1 정정 — owner 지적 반영] 네오제네시스 사업자등록 이미 보유** (2026-06-10 집PC 실사 박제: 앱인토스 파트너 등록 + 사업자 검수 ✅). 초판의 "사업자등록 = 미래 관문" 판정은 감사 오류였음. 정정된 경로:
  - **한국 결제: 토스페이먼츠/포트원 가맹 신청 즉시 가능** (사업자 요건 충족 상태) — 관문 없음, 가맹 심사 리드타임(~수일)만 존재.
  - **글로벌 결제 (daysleft.io EN 기본 타깃): Paddle 또는 Lemon Squeezy (MoR)** — 사업자 자격으로 가입, 글로벌 카드+세금(VAT/Sales tax) 대행. Stripe 한국 직접 발급 불가 정정은 유지.
  - 권고: **글로벌 MoR + 토스페이먼츠 동시 신청** (둘 다 차단 요인 없음) → 둘 중 먼저 승인되는 쪽으로 W1 내 첫 결제 레일 개통.
- W1: (오너) 결제사 가맹/가입 신청 (~30분×2) → (에이전트) subscribe/upgrade TODO를 checkout 연동으로 교체.
- W2: 가격 단일 SKU(lifetime 또는 연구독) + Product Hunt/Reddit(r/InternetIsBeautiful, r/productivity)/Show HN 런칭 1회 — memento mori 카운트다운은 WeCroak류로 검증된 바이럴 카테고리.
- W3~12: 오너의 retention/viral loop(이미 진행 중) × 퍼널 데이터 → 주 1회 개선.
- 목표: 90일 내 유료 전환 10~50건 + toolpick 제휴 커미션 1~2건. **금액이 아니라 0→1 증명이 목적.**

**병행 1: 앱인토스 트랙** — [v1.1 정정] 행정 게이트 대부분 이미 통과: 사업자등록 보유 ✅ + 앱인토스 파트너 등록·사업자 검수 ✅ (6/10) + 등급분류 경로 H1 확정(Play 조직계정→IARC). 잔여 = DUNS 발급(진행 중) + 게임제작업 등록(상태 확인 필요) + 심사 제출. 토스 광고 리워드 정산이 예상보다 가까움 — 90일 내 1차 수익 경로로 승격 검토.

**병행 2: toolpick 제휴 수익화** — 구매 의도 트래픽 125~150명/월 × SaaS 제휴 (광고 단가의 수십 배). 제휴 프로그램 가입은 owner G2.

**[비평 반영 보완] 클라이언트 워크/수탁 옵션**: 1인 개발자의 가장 빠른 0→1은 통상 수탁 1건이다. 구직 활동과 병행 평가 권고 — 제품 결제 개통(기대값 낮음·자산 축적형) vs 수탁(기대값 높음·시간 소모형)은 상충이 아니라 포트폴리오 배분 문제.

---

## 4. 이번 세션 실행 내역 (2026-06-11, etribe-yesol에서 원격)

| 항목 | 결과 |
|---|---|
| 멀티에이전트 전면 감사 (10 에이전트) | ✅ repo 14제품 + 라이브 18표면 + PostHog 30/90일 + Supabase quant + Vercel 30프로젝트 |
| GCP VM 비용 누수 확인 | ✅ 2대 모두 TERMINATED — 액션 불필요 (감사 우려 해소) |
| Cloud Run why-engine | ✅ 이미 제거됨 확인 |
| finite 작업 충돌 방지 | ✅ `feat/finite-mvp-launch` 미커밋 WIP(retention loop) 확인 → 레포 불간섭 결정 |
| PostHog 합성 트래픽 현재진행 확인 | ✅ neo-sbu-direct 일 14~149건 유입 중 — 발생원 차단 작업 진행 |
| PostHog test_account_filters 갱신 | ⚠️ MCP 직렬화 제약으로 실패 — PostHog UI에서 owner 1분 작업 또는 발생원 차단으로 대체 |
| 본 전략 보고서 SSOT 박제 | ✅ 이 파일 + handoff 갱신 |

## 5. Owner 결정 게이트 (G2)

| ID | 결정 | 권고 |
|---|---|---|
| D1 | finite 결제 제공자: 글로벌 MoR(Paddle/Lemon Squeezy) + 토스페이먼츠 동시 신청 | **ACCEPT — 둘 다 차단 요인 없음 (사업자등록 보유)** |
| D2 | ~~사업자등록 착수~~ | **[v1.1 무효] 사업자등록 이미 보유 — 감사 오류 정정** |
| D3 | Kill 리스트 집행 (퀀트 2 + 스캐폴드 5 + why-engine 아카이브, 코드 삭제 아님 — 009.archive 이동) | ACCEPT |
| D4 | Vercel 정리 (식별 완료된 ~10개 삭제, one-pyeong-store-privacy/frontend/analytics-cron-daemon 제외) | ACCEPT |
| D5 | GCP 잔존 디스크 2개 삭제 (VM 영구 폐기) | 권고 ACCEPT (스냅샷 후) |
| D6 | room-707 6/25 게이트 측정 주체 지정 (집PC 에이전트 cron) | ACCEPT |
| D7 | toolpick SaaS 제휴 프로그램 가입 (PartnerStack 등) | 검토 |

## 5.5 정정 이력 (v1.1, 2026-06-11)
- **owner 지적 "사업자등록은 되어있잖아" → 검증 결과 사실**: 2026-06-10 집PC 실사 기록(mintlab 메모리)에 "앱인토스 파트너 등록 + 사업자 검수 ✅ / 네오제네시스 사업자등록 보유 / DUNS 발급 진행 중" 박제 확인.
- **감사 오류 원인**: 심사단 3인이 5월 mintlab SSOT의 "Phase 2 졸업 게이트 (사업자등록 + 게임제작업 등록)" 문구를 현재 미보유로 오독 + 등록 상태 라이브 검증 절차 누락. 완전성 비평가도 미탐지.
- **정정 반영**: §3 결제 경로 (토스페이먼츠 즉시 가능), 병행 1 앱인토스 (행정 게이트 대부분 통과), §5 D1/D2.
- **재발 방지**: 향후 감사에서 "법인/사업자/계정 등록 상태"는 SSOT 문구가 아니라 실사 기록·credential·콘솔 상태로 검증할 것.

## 6. Stop/Go 게이트
1. **7/11까지 결제 레일 미개통** → 머니 패스 재설계 (수탁 우선 전환 검토).
2. **finite 런칭 후 30일 유료 0건 + 방문 1,000명 미만** → 가격/포지셔닝 피벗 또는 채널 재선정.
3. **앱인토스 서류 제출 완료 후 60일 무응답** → 트랙 보류 (오너 귀책 아님).
4. **room-707 6/25 게이트 미달** → 즉시 종료 (연장 금지).
5. **신규 제품 아이디어 발생 시** → 첫 결제 1건 전까지 자동 거부.

👤 Claude (Fable 5) — 감사 워크플로우 wf_3e4f03a4-7da, 10 agents / 3.5M tokens
