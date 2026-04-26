# Financial Advisor System v1 — 7-에이전트 자율 운영 체계

> **버전**: v1 (2026-04-26)
> **작성**: Claude Opus 4.7 (Strategy Lead 자격)
> **owner 지시**: "어드바이저 + 부하 에이전트, 어떤 방식으로든 일 1%+, 자본 검증되면 무제한 맡김, 자율 판단으로 owner 이익 최대화"
> **owner 의 진짜 이익 (어드바이저 해석)**: 자금 보존 + 점진적 성장 + 학습형 시스템 + 검증된 알파에만 자본 투입

---

## 0. 어드바이저 헌장 (Advisor Charter)

### 0.1 거부할 것 (어드바이저 거부권)
1. **무책임한 yes-man**: "일 1% 보장합니다" 같은 잘못된 약속
2. **검증 없는 자본 투입**: 페이퍼 검증 미통과 알파에 LIVE 자금
3. **하드캡 양보**: 레버리지 5x 양보 = 파산확률 매트릭스 위반 (5x 32% / 20x 98% / 50x 100%)
4. **CLAUDE.md `prohibited_actions` 위반**: 자금 직접 트레이드, 패스워드 접근 등

### 0.2 핵심 원칙 (양보 불가)
1. **자금 보존 > 수익**: 1년 파산확률 < 35% 유지
2. **레버리지 5x 하드캡** (Kelly/3 안전계수)
3. **검증 → 자본 → 확장** 단계적 게이트
4. **모든 결정에 Reality Check** (수학적/통계적 가능성 게이트)
5. **owner 의 G2+ 결정 권한 유지** (자금 이동 / LIVE 전환 / 외부 발송)

### 0.3 owner 의 진짜 이익 정의 (어드바이저 해석)
- **단기 (Phase 0~1)**: 인프라 안정성 + 알파 검증 게이트 통과
- **중기 (Phase 2~3)**: 검증된 알파 only → 단계적 자본 투입 → 일 0.6~1.0% 상위분위 진입
- **장기 (Phase 4+)**: 알파 포트폴리오 진화 + 자본 확장 + Tier 졸업 (micro → small → standard)

### 0.4 owner 목표 vs 어드바이저 권고 (정렬)
| owner 명시 목표 | 어드바이저 권고 | 정렬 방식 |
| --- | --- | --- |
| "어떤 방식으로든 하루 1%+" | 일 0.6~1.0% 상위분위 (5x 캡 내) | 메인 트랙 |
| "자본 검증 시 무제한 입금" | 검증 게이트 통과 알파별 capital allocation | 단계적 입금 권고 |
| (암묵: 공격적 시도) | "공격형 trial sleeve" — 전체 자본의 5% 분리 | 별도 sleeve |
| (암묵: 빠른 결과) | Phase 0 Liquidation Stream → Phase 1 알파 검증 → Phase 2 라이브 | 진화 가속 |

---

## 1. 7-에이전트 시스템 구조

```
                    ┌─────────────────────────────┐
                    │  STRATEGY LEAD (이 어드바이저)  │
                    │  (Architect, Claude Opus 4.7)  │
                    │   • 우선순위 결정              │
                    │   • 자본 배분 권고             │
                    │   • Phase 게이트 판정          │
                    │   • owner 직접 보고            │
                    └────┬────────────────────────┬─┘
                         │                        │
        ┌────────────────┼────────────┬───────────┼───────────────┐
        │                │            │           │               │
        ▼                ▼            ▼           ▼               ▼
 ┌──────────────┐ ┌─────────────┐┌──────────┐┌──────────────┐┌─────────────┐
 │ RISK OFFICER │ │   ALPHA     ││EXECUTION ││   BACKTEST   ││ COMPLIANCE  │
 │              │ │ RESEARCHER  ││ OPERATOR ││  VALIDATOR   ││  CHECKER    │
 │ CVaR/VaR     │ │             ││          ││              ││             │
 │ 파산확률     │ │ 신규 알파   ││ VM/PM2/  ││ nautilus/    ││ 수학적 한계 │
 │ MaxDD       │ │ 발굴+검증   ││ PAPER/   ││ DSR/PBO/    ││ 게이트      │
 │ killswitch   │ │ 외부 리서치 ││ LIVE 운영││ CPCV harness ││ Hidden risk │
 │ 모니터       │ │ 수렴        ││          ││              ││             │
 └──────────────┘ └─────────────┘└──────────┘└──────────────┘└─────────────┘
        ▲                ▲            ▲           ▲               ▲
        └────────────────┴────────────┴───────────┴───────────────┘
                                      │
                          ┌───────────┴───────────┐
                          ▼                       ▼
                 ┌────────────────────────────────────┐
                 │   REPORTING ANALYST (PM/DA)         │
                 │   • 일일 09:00 KST 텔레그램 리포트  │
                 │   • 주간 리뷰 (월요일 오전)         │
                 │   • 월간 게이트 통과 보고서         │
                 │   • 자본 입금 권고 알림             │
                 └────────────────────────────────────┘
```

---

## 2. 에이전트별 상세 명세

### 2.1 Strategy Lead (어드바이저)
- **역할**: 7-에이전트 오케스트레이터. owner 의 직접 카운터파트.
- **모델**: Claude Opus 4.7 (1M context)
- **책임**:
  - Phase 게이트 판정 (Phase 0 → 1 → 2 → 3 → 4)
  - 자본 배분 권고 (검증 통과 알파별 비중)
  - Reality Check 의무 (모든 owner 요청 4-Step 분석)
  - 부하 에이전트 결과 통합 → owner 직접 보고
- **소통 채널**: Claude Code 세션 (직접 대화) + 텔레그램 알림 (위임 시)
- **결정권**:
  - G0 (자율): 페이퍼 모드 운영, 알파 백테스트, 코드 변경
  - G1 (자율): 인프라 변경, PR 생성, 코드 push
  - G2 (owner 승인): 자본 입금/출금, LIVE 전환, 외부 거래소 변경
  - G3 (owner 승인): 자금 직접 이체 (실제로는 prohibited)

### 2.2 Risk Officer
- **역할**: 일일 리스크 모니터 + killswitch 발동 권한
- **자동화 위치**: VM cron (`auto-trading/scripts/daily-risk-officer-report.js`)
- **출력**: 텔레그램 일일 09:00 KST + 위급 시 즉시 알림
- **모니터 항목**:
  - PM2 status (online / restarts / unstable_restarts)
  - Heap Usage (≥ 95% 경고, ≥ 98% 긴급)
  - Supabase lease (`trading_mode`, `halt_until`)
  - Recent killswitch_log (24h 발동 횟수)
  - Liquidation events 수집량 (Phase 0 Task 0.1 게이트 #3)
  - Trade ledger MAE/MFE (Phase -1 게이트 #2)
  - 일/주/월 MaxDD (다주기)
- **알림 등급**:
  - 🟢 정상: 일일 리포트만
  - 🟡 경고: 텔레그램 즉시 알림 (Heap 95%+, restart 5+/24h, killswitch 발동, BEAR 7일+)
  - 🔴 긴급: 즉시 알림 + Strategy Lead 자동 호출 (Heap 98%+, restart 10+/24h, halt 발동, 자금 손실 1%+)

### 2.3 Alpha Researcher
- **역할**: 신규 알파 후보 발굴 + 외부 리서치 수렴
- **자동화 위치**: 주 1회 (월요일 09:00 KST) cron 또는 수동 트리거
- **자료 수집**:
  - Twitter/X quant 리서처 핸들 (Robot Wealth, Curupira 등)
  - Crypto quant 블로그 (Amberdata, Coin Metrics, Hudson & Thames)
  - arXiv / SSRN 신규 논문 (`crypto perpetual`, `liquidation cascade`, `funding rate`)
  - GitHub trending (cryptofeed, hummingbot, nautilus_trader)
- **출력**: 주간 알파 후보 리스트 + Strategy Lead 검토 큐
- **위임 모델**: Claude `general-purpose` agent + WebSearch + WebFetch

### 2.4 Execution Operator
- **역할**: VM/PM2/PAPER/LIVE 운영. 배포 자동화. 장애 대응.
- **자동화 위치**: Sora + gcloud + pm2
- **작업 패턴**:
  - 배포: `git archive | scp | tar -x | npm ci | pm2 delete/start/save`
  - 헬스체크: 1분 단위 PM2 상태 + 5분 단위 Supabase lease
  - 장애 복구: `pm2 restart` → 실패 시 `pm2 delete + start + save` → 실패 시 백업 src 롤백
- **권한**:
  - G0 (자율): pm2 restart, log tail, status 확인
  - G1 (자율): VM scp + 코드 배포 + npm install
  - G2 (owner 승인): VM 인스턴스 변경 (Tokyo 이전 등)

### 2.5 Backtest Validator
- **역할**: nautilus_trader 통합 + DSR/PBO/CPCV 검증
- **자동화 위치**: Python harness `auto-trading/src/backtest/v2/validation/`
- **알파 승격 게이트**:
  - DSR ≥ 0.5 (Bailey & López de Prado)
  - PBO ≤ 0.3 (Probability of Backtest Overfitting)
  - CPCV walk-forward 6 splits 통과
  - 4 crash tick stress test (2020-03-13, 2022-05-12 LUNA, 2022-11-08 FTX, 2025-10-10 Hyperliquid)
- **출력**: 알파별 승격/거부 판정 + Strategy Lead 보고
- **위임 모델**: Codex agent (Python heavy) + Backtest harness 직접 실행

### 2.6 Compliance Checker
- **역할**: 모든 owner 요청 + 시스템 결정의 수학적/통계적 게이트
- **자동화 위치**: Strategy Lead 의 4-Step 분석 hook
- **체크리스트**:
  1. 사실 검증 (수치/공개 자료 교차검증)
  2. ROI 분석 (기대값 vs 파산확률)
  3. 설계 타당성 (FOLDER_BIBLE / RISK_KILLSWITCH 정합성)
  4. 대안 비교 (최소 1개 대안)
- **거부 트리거**:
  - 일 1%+ 무조건 강행 (수학적 불가능)
  - 레버리지 5x 초과
  - 미검증 알파 LIVE 전환
  - 자금 이동 owner 승인 없음
- **위임 모델**: Claude `neo-reviewer` (read-only)

### 2.7 Reporting Analyst (PM/DA)
- **역할**: 일/주/월 운영 리포트 + 자본 입금 권고
- **자동화 위치**: VM cron (`scripts/daily-pm-da-report.js`) + Sora `traffic_pmda_report` 패턴
- **리포트 포맷**:
  - **일일 (09:00 KST)**: Executive Summary / Bot Health / Trading Activity / Risk Indicators / Tomorrow's Action Queue
  - **주간 (월요일)**: Weekly P&L / Alpha Performance / Phase Progress / Capital Allocation Recommendation
  - **월간**: 게이트 통과 알파 리스트 / 자본 입금 권고 (또는 회수 권고) / Phase 진화 결정
- **자본 입금 권고 트리거**:
  - 알파 1개 이상 페이퍼 30일 통과 + DSR ≥ 0.7 + Sharpe ≥ 1.5
  - 권고 금액: 통과 알파별 Kelly 10% (안전계수)
  - owner 입금 결정 → Strategy Lead 가 capital allocation 자동 적용

---

## 3. Capital Allocation Framework

### 3.1 자본 입금 게이트 (owner 1000만원~8000만원 할당 의사 반영, v1.2)

**owner 할당 가능 범위**: 최소 1000만원 (~$7,000) ~ 최대 8000만원 (~$56,000)

| 단계 | 권고 활성 자본 | 권고 보유 자본 (대기) | 조건 (모두 충족) |
| --- | ---:| ---:| --- |
| Phase 0 | $29 (현재) | — | 인프라 안정 + Liquidation Stream 실제 구현 |
| Phase 1 (페이퍼 검증) | $0 (PAPER only) | — | 1+ 알파 페이퍼 14일 Sharpe ≥ 1.2, DSR ≥ 0.5 |
| Phase 2 첫 진입 (소액 라이브) | **$1,000~2,000** (1000만원의 10~20%) | $5,000~6,000 (high-yield/stable 대기) | 2+ 알파 라이브 14일 net 수익 양수, MaxDD < 15% |
| Phase 2 통과 | **$5,000~10,000** (1000만원 전체) | $0 (전부 활성) | 30일 누적 +5% 이상 net 수익 |
| Phase 3 진입 | **$10,000~28,000** (~3000만원) | 나머지 owner 보유 | 90일 누적 +20%, 9-Layer 무발동, Sharpe ≥ 1.5 |
| Phase 4 (full deployment) | **$28,000~56,000** (~8000만원) | $0 또는 5% sleeve | 분기 누적 +30%, 다자산 알파 1+ 검증 |

### 3.2 어드바이저 권고 — 자본 입금 전략 (CRITICAL)
**한 번에 8000만원 풀 입금은 절대 비추.** 이유:
- **통계적 자살**: 미검증 단계에서 큰 자본 = 첫 1주 손실로 owner 신뢰 상실
- **심리 효과**: 큰 자본 손실 = 합리적 의사결정 마비 (owner 가 시스템 종료 명령 가능성)
- **capacity 한계**: $50K+ 활성 시 A1/A6 같은 capacity-bound 알파 슬리피지 폭증
- **세금 노출**: 한 번에 진입 = 분기 결산 시 세금 고지 큼

**권고 입금 스케줄** (Phase 단계 통과 후):
1. **1000만원** → Phase 1 통과 시 (예상 Phase 0 마감 + 2주 = ~2026-05-10)
2. **+2000만원 (총 3000만원)** → Phase 2 통과 시 (예상 +30일 = ~2026-06-10)
3. **+5000만원 (총 8000만원)** → Phase 3 통과 시 (예상 +90일 = ~2026-09-10)

### 3.3 자본 보호 인프라 (8000만원 규모 대비)
- **Cold storage 분리**: 활성 자본 외 나머지는 거래소가 아닌 cold wallet / 은행 계좌
- **거래소 분산**: 단일 거래소 50% 한도 (Binance / Bybit / OKX 분산)
- **Insurance fund 모니터링**: Binance USDM insurance fund 잔액 추적, 위험 시 자본 회수 권고
- **세금 적립**: 활성 자본의 25% 별도 적립 (한국 가상자산 양도세 2027년 시행 + 양도소득 분리과세 22% 대비)

### 3.4 알파별 자본 비중 (Phase 2 이후, 8000만원 기준 예시)

검증 통과 알파 N 개 → 자본 = 합계 100%
- A1 Liquidation Cascade: 40% ≈ 3,200만원
- A2 Mean Reversion OU: 25% ≈ 2,000만원 (A1 동조 게이트 통과 시)
- A3 Extreme Funding: 15% ≈ 1,200만원 (임계 0.08%+ 통과)
- A4 Macro Event: 10% ≈ 800만원 (이벤트일만)
- A5 Funding/Basis Harvest: 15% ≈ 1,200만원 (capacity 게이트 통과)
- A6 Alt Market Making: 10% ≈ 800만원 (Phase 3 이후 검토)

### 3.5 "공격형 Trial Sleeve" 재정의 (8000만원 규모 기준)
- **위치**: 전체 자본의 **5% = 400만원 ($2,800)** 별도 sleeve
- **운영**: 레버리지 10~20x 허용 (캡 양보), 알파 1개 (가장 best Sharpe) 만 사용
- **목표**: 일 1%+ 시도. 박멸 시 즉시 종료 (재충전 없음)
- **트래킹**: 메인 자본과 격리 (별도 lease, 별도 ledger, 별도 지갑/계좌)
- **owner 결정**: Phase 3 진입 (3000만원 활성) 후 옵션 활성

### 3.2 알파별 자본 비중 (Phase 2 이후)

검증 통과 알파 N 개 → 자본 = 합계 100%
- A1 Liquidation Cascade: 40% (Sharpe 통과 시)
- A2 Mean Reversion OU: 25% (A1 동조 게이트 통과 시)
- A3 Extreme Funding: 15% (임계 0.08% 이상 통과 시)
- A4 Macro Event: 10% (이벤트일만)
- A5 Funding/Basis Harvest: 15% (capacity 게이트 통과 시)
- A6 Alt Market Making: 10% (Phase 3 이후 검토)

### 3.3 "공격형 Trial Sleeve" 옵션 (owner 1%+ 욕구 분리 충족)

- **위치**: 전체 자본의 **5% 한도** 별도 sleeve
- **운영**: 레버리지 10~20x 허용 (캡 양보), 알파 1개 (가장 best Sharpe) 만 사용
- **목표**: 일 1%+ 시도, 단 sleeve 자본 박멸 시 즉시 종료 (재충전 없음)
- **트래킹**: 메인 자본과 격리 (별도 lease, 별도 ledger)
- **owner 결정**: Phase 2 진입 후 메인 자본 100% 전환 후 옵션 활성

---

## 4. 통신 프로토콜 (Magentic-One Dual-Ledger 기반)

### 4.1 SSOT 파일
- **Task Ledger**: `.agent/shared-brain/active-tasks.md`
- **Progress Ledger**: `.agent/shared-brain/progress-ledger.md` (이미 존재)
- **Decision Log** (신규): `.agent/shared-brain/decision-log.md`
- **Daily Briefing** (신규): `.agent/shared-brain/daily-briefings/YYYY-MM-DD.md`

### 4.2 에이전트 간 메시지
- **방향**: Strategy Lead ⇄ 부하 에이전트 (수직)
- **형식**: 구조화된 JSON 또는 YAML (Pydantic contracts 활용)
- **저장**: `.agent/shared-brain/agent-messages/YYYYMMDD/<agent>-<seq>.yaml`

### 4.3 owner 알림 채널
- **일일 리포트**: 텔레그램 09:00 KST (Reporting Analyst)
- **위급 알림**: 텔레그램 즉시 (Risk Officer)
- **세션 로그**: Claude Code 직접 대화 (Strategy Lead)
- **자본 권고**: 텔레그램 + Claude Code 세션 동시

---

## 5. Phase 진화 로드맵

### Phase 0 (현재 ~ 이번 주 마감)
- **상태**: 9-Layer Kill Switch 단위 테스트 ✅, backtest v2 scaffold ✅, Liquidation Stream **scaffold only** (실제 구현 필요)
- **남은 Task**:
  - Liquidation Stream 실제 구현 + v6-live-runner wiring
  - 9-Layer Kill Switch 실제 wiring (orchestrator/runner 통합)
  - nautilus_trader 통합 + Validation harness
  - 4 crash tick stress 자산 확보

### Phase 1 (2주, 알파 개별 페이퍼 검증)
- 6 알파 각각 페이퍼 14일 운영
- 통과 게이트: Sharpe ≥ 1.2, DSR ≥ 0.5, MaxDD < 15%
- 통과 알파만 Phase 2 진입

### Phase 2 (2주, 소액 라이브)
- 자본 권고 $100~500 (owner 입금 결정)
- 통과 알파 묶어서 라이브 운영
- 9-Layer kill switch 활성

### Phase 3 (분기, 자본 확장)
- $5,000~50,000 단계적 입금
- 분기 누적 ≥ +20% 확인 후 Phase 4

### Phase 4 (지속)
- $50,000+ 운영
- micro → small tier 졸업
- 알파 포트폴리오 진화

---

## 6. owner 의 일 1%+ 욕구 자율 처리

### 6.1 기본 트랙 (자율 결정)
- **메인 자본**: 일 0.6~1.0% 상위분위 + 5x 캡 + 단계적 진화
- **공격형 sleeve** (Phase 2 이후 자율 활성): 5% 한도 + 10~20x + 실험 알파 only

### 6.2 owner 가 "안전 트랙 거부 + 100% 공격" 명시 요청 시
- Compliance Checker 가 4-Step 분석 자동 발동
- 결과 텔레그램 + 세션 동시 보고
- owner 가 명시적 재확인 시 → Strategy Lead 가 책임 한도 명시 + 진행 (단, 박멸 시 시스템 자체 종료)

### 6.3 어드바이저 거부권 (양보 불가)
- 일 5%+ 또는 레버리지 100x+ 같은 명백한 자살 요청
- Compliance Checker 자동 거부 + Strategy Lead 가 owner 에게 거부 사유 명시

---

## 7. 즉시 가동 우선순위 (자율 결정)

### 7.1 이번 세션 (오늘)
1. ✅ 본 SSOT 작성 (시스템 설계 박제)
2. **Risk Officer 일일 리포트 자동화 스크립트** (텔레그램 + Supabase 모니터)
3. **첫 일일 리포트 즉시 1회 발행** (수동 트리거 + 검증)

### 7.2 다음 세션
1. Liquidation Stream 실제 구현 + wiring (Phase 0 마감)
2. Reporting Analyst 주간 리포트 cron
3. Alpha Researcher 첫 주간 리서치 (월요일 09:00)

### 7.3 1주 내
1. nautilus_trader 통합 (Backtest Validator)
2. Compliance Checker hook (Strategy Lead 의 4-Step 자동화)
3. Phase 1 알파 개별 페이퍼 모드 진입 준비

### 7.4 2주 내 (Phase 1 진입)
1. 6 알파 개별 페이퍼 운영 (14일)
2. 일/주간 리포트 정착
3. 자본 입금 권고 첫 발생 가능 시점

---

## 8. 메트릭 정의 (운영 KPI)

| 메트릭 | 정의 | 목표 |
| --- | --- | --- |
| 일 누적 수익률 | 24h 실현 + 미실현 PnL / 자본 | 0.6~1.0% (상위분위) |
| 30일 Sharpe | 30일 일별 수익률의 Sharpe | ≥ 1.5 |
| MaxDD | 최근 60일 최대 누적 손실 | < 15% |
| 알파 firing rate | 일평균 신호 발생 횟수 | A1: 5+, A2: 10+, A3: 1+, etc |
| Capital efficiency | 활성 자본 / 전체 자본 | ≥ 60% |
| Killswitch false positive | HALT 발동 중 실제 위험 미존재 비율 | < 1% |

---

## 9. owner 보고 표준 (Reporting Analyst)

### 9.1 일일 리포트 포맷 (텔레그램, 09:00 KST)
```
📊 Quant Bot Daily Briefing — YYYY-MM-DD
═══════════════════════════════════════

✅ Bot Health
  • Status: online (uptime XXh)
  • PID: XXXXXX
  • Restarts (24h): X
  • Heap: XX% (trend: ±X.Xpp)

💰 Trading Activity (24h)
  • Trades opened: X
  • Trades closed: X
  • Net PnL: +X.XX% (KRW XX,XXX)
  • MaxDD: -X.XX%
  • Win rate: XX% (X/X)

⚠️ Risk Indicators
  • Killswitch events: X
  • Liquidation events received: X
  • Lease trading_mode: PAPER/LIVE
  • Halt_until: NULL/YYYY-MM-DD

🎯 Tomorrow's Action Queue
  1. ...
  2. ...

🔔 Alerts (if any):
  ...
```

### 9.2 주간 리포트 (월요일 10:00 KST)
- Weekly P&L (alpha-별 분리)
- 알파 firing pattern
- Phase 진척도
- 자본 입금 권고 (트리거 충족 시)

### 9.3 월간 리포트 (월 1일 10:00 KST)
- 게이트 통과 알파 리스트
- 누적 수익 / 파산확률 / Sharpe
- Phase 진화 결정
- 자본 회수 권고 (성과 미달 시)

---

## 11. Multi-Asset Expansion Roadmap (2026-04-26 v1.1 추가)

### 11.1 owner 시그널
"크립토에 한정지을 필요 없어" — 자산군 확장 권한 위임.

### 11.2 어드바이저 자율 판단
**즉시 확장 금지, 단계적 진입.** 이유:
- v11 인프라는 **Binance USDM perpetuals 전용** 으로 6개월 이상 구축됨
- 자산군마다 거래소/규제/세금/상품 구조 전혀 다름 — 인프라 재구축 필요
- 검증되지 않은 자산군 즉시 진입 = Phase 0 의 실패 패턴 (LIVE 시 -$9 drain) 재현 위험

### 11.3 Phase 별 자산군 진화

| Phase | 자산군 | 거래소/API | 비고 |
| --- | --- | --- | --- |
| Phase 0~3 (현재~6개월) | **Crypto Futures** (BTC/ETH/Alt USDM) | Binance Futures | 현 인프라 |
| Phase 3.5 (병렬, Phase 3 안정 후) | **Crypto Spot** + **Cross-exchange** | Binance Spot, Bybit, OKX, Hyperliquid | A5 (Funding/Basis Harvest) 가 spot 필요 |
| Phase 4 (6~9개월) | **미국 주식 + ETF** | Alpaca (commission-free, paper account), IBKR | 24/5 → market hours 한정, 다른 시간프레임 |
| Phase 4.5 | **한국 주식** | KIS Open API (한국투자증권 무료) | 세금/규제 한국 적용 |
| Phase 5 (12개월+) | **FX (Forex)** | OANDA REST v20, IBKR | 24/5, 매크로 알파 풀 |
| Phase 5.5 | **상품 (Gold/Oil)** | IBKR, CME futures | 매크로 헤지 |
| Phase 6+ (검증 후) | **옵션** (crypto + equity) | Deribit, IBKR | 변동성 알파 (Black-Scholes-Merton 부족, 머신러닝 vol surface 필요) |
| Phase 6+ (검증 후) | **DeFi** (이자 farming, LP) | Aave V3, Uniswap V4 | 자본 효율 + DeFi 리스크 |

### 11.4 다자산 알파 카테고리 (Alpha Researcher 확장 범위)

| 카테고리 | 자산군 적용 | 알파 예시 |
| --- | --- | --- |
| Trend Following | 모든 자산 | Donchian, Keltner, ADX |
| Mean Reversion | Equities, FX | OU process, pairs trading, sector rotation |
| Statistical Arbitrage | Equity sectors, FX pairs, crypto pairs | Cointegration, Kalman filter |
| Event-Driven | Equities, Crypto | Earnings, FOMC, CPI, M&A |
| Carry Trade | FX, Crypto Funding | Funding rate harvest, FX carry |
| Volatility | Options | Vol surface skew, gamma scalping |
| Momentum | Equities, FX | Cross-sectional momentum, time-series momentum |
| Microstructure | All liquid | Order flow imbalance, queue position, liquidation cascade |

### 11.5 거래소/API 인프라 우선순위 (어드바이저 자율 판단)

**Phase 4 진입 시 권고 순서:**
1. **Alpaca** (미국 주식) — paper account 무료, REST + WebSocket, commission-free, Python SDK 안정적
2. **OANDA v20** (FX) — paper account 무료, 24/5, REST + Streaming, spread 좁음
3. **KIS Open API** (한국 주식) — 무료, REST, 세제 혜택 자동 (ISA 가능), 한국 owner 적합
4. **IBKR** (Multi-asset) — 전문가급, IB Gateway 필요, 모든 자산군 한 계좌

### 11.6 다자산 Risk Officer 보강 (v2 예정)
- **자산군별 lease + ledger 분리** (테이블 multi-tenant 화)
- **Cross-asset correlation killer** (crypto crash 시 equity 헤지 자동 발동 등)
- **거래소별 health check** (Alpaca / OANDA / Binance / IBKR 동시 모니터)

### 11.7 어드바이저 거부권 유지
- 다자산 확장이 어드바이저 헌장 (§0.1) 의 거부 영역을 면제하지 않음
- 미검증 알파 LIVE 진입 = 자산군 무관 거부
- 레버리지 5x 하드캡 = 자산군별 적용 (FX 50:1 같은 관행 거부)
- Phase 단계 게이트 = 자산군별 독립 적용 (crypto 통과 ≠ equity 통과)

---

## 변경 이력
- v1 (2026-04-26): owner "어드바이저 + 부하 에이전트 + 자본 무제한 + 자율 판단" 지시 기반 초안
- v1.1 (2026-04-26): owner "크립토 한정 X" 추가 시그널 → §11 Multi-Asset Expansion Roadmap 신설
- v1.2 (2026-04-26): owner "1000만원~8000만원 할당 예정" 시그널 → §3 Capital Allocation v1.2 (단계적 입금 권고 + 자본 보호 인프라)
