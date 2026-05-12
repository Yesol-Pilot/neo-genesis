# Revenue Path Research v1 — Post v11 PoC Closure

> **작성:** 2026-05-12, Strategy Lead Claude Opus 4.7 (Financial Advisor 자율 G1).
> **트리거:** owner 명령 "돈 벌 수 있는 방법을 찾아오고 연구하라고 지금하던건 다 중단시켜"
> **상태:** v11 quant-bot PoC closure (5/12 PM2 stop 완료, 5 process 모두 stopped)

---

## 0. Executive Summary

### v11 PoC 결과 (38일 검증)
- **옛 알파 7개**: 191 trades, WR 37.7%, **-15.1%** PAPER PnL
- **신규 알파 5개 (A1/A2/A3/A4/A6)**: 19일 거래 **0건**
- **A2 OU sensitivity sweep**: 0/108 셀 통과
- **A1 데이터 풍부 (OKX 10K+/일)** 에도 거래 0건
- **결론**: 1인 retail crypto quant strategy fit market 못 찾음

### 본 연구 범위
1인 retail 자본 **1,000~8,000만원** 기준으로 **honest 수익 가능 path** 7개 객관적 평가:
- **A. Quant 재시도** (4 sub-path)
- **B. 본업 가속** (3 sub-path, 이미 가동 중 매출 발생)
- **C. AI agentic 신규 사업** (3 sub-path)
- **D. 패시브 자본 보호** (3 sub-path)

### Strategy Lead 권고 — 가장 honest 우선순위
1. **B. 본업 가속** (Neo Genesis 11 SBU + CTS 이트라이브 + AI consulting)
2. **C1. Agentic AI 컨설팅 / SaaS** (38일 PoC 학습 자체가 자산)
3. **D2. 미국 주식 인덱스 ETF** (자본 보호, 연 7~10% 패시브)
4. **A4. 위탁 운용 (자동 매매 SaaS)** (선택적, 자본 일부)
5. ❌ **A1~A3 quant 직접 재시도** (38일 학습으로 부적합 입증)
6. ❌ **C4 NFT/Web3** (변동성 + 사기 위험)

---

## 1. v11 PoC 38일 학습 cold honest

### 1.1 학습한 것 (자산)
- **Crypto retail quant 어려움 입증** — alpha decay 빠름 + 1인 자본 규모 한계
- **Multi-alpha ensemble 운영 경험** — 6 알파 + 9-Layer Kill Switch + Supabase + PM2 + cross-exchange
- **AI agentic 자율 운영 노하우** — Strategy Lead Claude + Codex + multi-device + 36+ commits
- **Backtest infrastructure** — sensitivity sweep + DSR + regime breakdown

### 1.2 실패한 것
- 12 알파 모두 sustainable edge 없음
- BULL 박스권에서 모든 알파 standby
- 시장 조건 변화 시 빠른 alpha decay
- 1인 운영 한계 (24/7 모니터링 + 알파 재설계 cycle)

### 1.3 quantify
- **자본 ROI**: 38일 × PAPER + 0 wallet → 0%
- **시간 ROI**: 38일 owner 시간 + 본 세션 token 비용 → 학습 가치만
- **opportunity cost**: 같은 38일 본업 (11 SBU) 가속 → 추정 수익 발생

---

## 2. Path A — Quant 재시도 (4 sub-path)

### A1. 다른 자산군 (US 주식 / FX / 옵션)
**가설**: crypto 외 자산군은 alpha decay 다를 수 있다.

**검증 어려움**:
- US 주식: 27% 시간만 거래 (장중) → crypto 24/7 운영 노하우 손실
- 규제: 한국 retail 미국 주식 옵션 = 1억 양도세 (큰 진입 비용)
- FX: 변동성 ↓ → 큰 자본 필요 (5~10x 레버리지 위험)

**기대**: 동일 패턴 (12 알파 시도 → 실패) 반복 가능성 60%+

**ROI 추정**: 1년 +5~15% (최선) / -20% (alpha decay)

**시간 투입**: 2~3개월 PoC 추가

**자본 요구**: 1,000~3,000만원

**Strategy Lead 권고**: ❌ **비추** (crypto 38일 학습이 직접 통하지 않음)

### A2. 위탁 운용 (외부 펀드 매니저)
**가설**: 직접 quant 안 하고 정상 펀드 매니저에게 위탁.

**옵션**:
- 한국 ETF / 펀드: 한투 / KB / NH 등 (수수료 1.5~2.5%, 알파 거의 없음)
- 헤지펀드 (해외): 최소 투자액 보통 $1M+ → 자본 부족
- 자산운용사 일임투자: 1억+ 진입

**기대 수익**: 연 5~12% (수수료 차감 후)

**위험**: 매니저 운용 능력 변동 + 수수료 drag

**Strategy Lead 권고**: 🟡 **자본 1억+ 가능 시 검토** (현 자본 규모 1,000~8,000만원 에선 비효율)

### A3. Algo MM Hummingbot 위탁
**가설**: Hummingbot Foundation 또는 Botfolio 등 SaaS 가입.

**옵션**:
- Hummingbot Foundation 자체: open source, 자가 운영 (38일 PoC 같은 패턴 반복)
- 3rd party SaaS: Kryll, 3Commas, Cryptohopper (수수료 + alpha decay 동일)

**기대**: 1~3% / 월 (광고 수치, 실측 0~1%)

**위험**: SaaS 사기 빈도 높음, 실 운영 시 38일 PoC 와 동일 패턴

**Strategy Lead 권고**: ❌ **비추** (학습 가치 0)

### A4. 자동 매매 SaaS (수동 인덱스 알고)
**가설**: 한국 retail 친화적 robo-advisor (불리오, 핀트, 에임 등).

**기대**: 연 5~10% (보수적)

**수수료**: 0.5~1.5% / 년 + 거래 수수료

**규제 안전**: 한국 금감원 등록, 안전

**Strategy Lead 권고**: 🟡 **자본 일부 (10~20%) 검토 가능** (D2 ETF 와 유사)

---

## 3. Path B — 본업 가속 (가장 honest, 이미 가동 중)

### B1. Neo Genesis 11 SBU 매출 가속
**현 상태** (active-tasks.md 검토 기준):
- **운영 SBU 11개**: ToolPick / ReviewLab / kott / whylab / ethicaai / aiforge / sellkit / craftdesk / deploystack / finstack / UR WRONG
- **실제 매출 발생** (구체 수치 owner 만 알지만, 일부 SBU GSC organic 트래픽 진행)
- **HIVE MIND 자동 발행** + 콘텐츠 자동화
- **AI agentic 운영 노하우** = 38일 PoC 자산 활용 가능

**가속 path**:
1. **SBU 별 매출 분석 + 우선순위 재정의** — 어떤 SBU 가 ROI 높은지 ranking
2. **고매출 SBU 2~3개 집중 투자** (기능 + 콘텐츠 + 마케팅)
3. **저매출 SBU sunset** (시간 낭비 차단)
4. **신규 monetization** (ad / affiliate / subscription / SaaS plan)

**기대 매출**: 본업 매출 + α (sub linear, but compounding)

**자본 요구**: 거의 0 (시간 투입 위주) + 광고비 옵션

**시간**: 1주~3개월 (SBU 별)

**Strategy Lead 권고**: ✅ **가장 honest** — 이미 매출 발생 + agentic 자산 활용

### B2. CTS-AI 본업 확장 (이트라이브)
**현 상태**: owner 가 회사 PC (CTS_Sol) 에서 본업 수행, 11 사내 프로젝트 박제 (cts-projects.json).

**가속 path**:
1. 본업 성과 가속 → 연봉 + 보너스 증가
2. 사내 영향력 확대 → 승진 / 신규 R&D 권한
3. CTS-AI 의 quant / agentic 노하우 내부 PoC → 회사 차원 매출 가능성

**기대**: 연봉 인상 5~15% / 년 + 보너스

**시간**: 매일 9~6 본업 (이미 투입 중)

**자본 요구**: 0

**Strategy Lead 권고**: ✅ **가장 안전 + 안정** (이미 진행 중인 안정 수입)

### B3. AI Consulting / SaaS (Neo Genesis 노하우 외부 판매)
**가설**: 38일 PoC 학습 + Multi-device agentic 운영 + Claude Code 노하우 = 외부 컨설팅 가치.

**target client**:
- 중소 SaaS 회사 (AI agentic 워크플로 도입 컨설팅)
- 1인 사업자 (multi-product 운영 자동화)
- 학습 / 강의 (AI agent 활용 교육)

**revenue model**:
- 1회성 컨설팅: 시간당 10~30만원
- 프로젝트 기반: 500~3,000만원 / 프로젝트
- SaaS subscription: 월 5~50만원 / 고객

**기대**: 첫 6개월 0~500만원 / 월 (불확실)

**시간**: 5~20시간 / 주

**자본 요구**: 0 (도구 이미 보유)

**Strategy Lead 권고**: 🟢 **검토 가치 ↑** (PoC 학습 자체가 자산)

---

## 4. Path C — AI Agentic 신규 사업 (3 sub-path)

### C1. Agentic AI 자동화 SaaS
**가설**: 본 PoC 의 agentic 운영 패턴 (Strategy Lead + Codex + 12 alpha + Kill Switch + multi-device) 을 SaaS 화.

**target**:
- E-commerce 자동화 (sell + customer + ad + analytics)
- 콘텐츠 운영 자동화 (HIVE MIND 패턴 외부 판매)
- 금융 데이터 모니터링 (본 PoC 의 monitoring stack)

**revenue**: 월 5~100만원 / 고객 × 10~50 고객 = 50만 ~ 5,000만원 / 월

**자본 요구**: 5,000만원 (개발 + 마케팅, 6개월)

**시간**: 6~12개월 PoC + go-to-market

**Strategy Lead 권고**: 🟡 **자본 5,000만원 가능 시 검토** (큰 시간 투자)

### C2. 정보재 / 강의 / 콘텐츠 (passive income)
**가설**: AI agentic 운영 노하우 → 책 / 강의 / 유튜브 / Substack.

**예시**:
- "Claude Code 로 1인 11 사업 운영하는 법" 강의
- "Agentic AI 자동화 PoC 실패와 학습" Substack
- 유튜브 / 블로그 (heoyesol.kr 활용)

**revenue**:
- 강의: 30~100만원 / 강의 × 50~500명 = 1,500만 ~ 5억 누적
- 책: 2,000만원 ~ 5,000만원 (1~2년)
- Substack / Patreon: 월 50~300만원 (1~2년 build)

**자본 요구**: 0~500만원 (편집 / 호스팅)

**시간**: 2~6개월 build

**Strategy Lead 권고**: 🟢 **passive income compounding 가능** (장기 ROI ↑)

### C3. Affiliate / 광고 (11 SBU 활용)
**가설**: 11 SBU 트래픽 + AI affiliate 광고 매칭.

**revenue**: 트래픽 비례, 월 0~500만원 (현재 GSC organic 가속 중)

**자본 요구**: 0

**Strategy Lead 권고**: ✅ **B1 와 결합 권고**

---

## 5. Path D — 패시브 자본 보호 (3 sub-path)

### D1. 정기예금 / CMA / 단기채권
**기대**: 연 3~4% (한국 은행)

**위험**: 0 (예금보호공사 보장)

**Strategy Lead 권고**: ✅ **자본의 20~30% 비상자금**

### D2. 미국 주식 인덱스 ETF (S&P 500, Nasdaq 100)
**기대**: 연 7~10% (10년 평균 8~9%)

**위험**: 단기 -20~30% drawdown 가능, but 10년+ 보유 시 positive 거의 확실

**예시**:
- SPY / VOO (S&P 500)
- QQQ (Nasdaq 100)
- VTI (Total Stock Market)

**한국 retail 진입**:
- 미래에셋 / 삼성 / 한국 자산운용 의 미국 ETF (TIGER 미국 S&P500 등) — 한국 ETF 형식
- 또는 키움 / 삼성 미국주식 직투 (양도세 22% over 250만원 / 년)

**자본 요구**: 1,000만원 ~ 무제한

**시간**: 0 (매수 후 보유)

**Strategy Lead 권고**: ✅ **자본의 40~60% 권고** (장기 우상향 + 자본 보호)

### D3. 부동산 / REITs
**기대**: 연 4~7% (배당 + 시세 차익)

**위험**: 한국 부동산 = 자본 규모 부족, REITs = 단기 변동성 ↑

**Strategy Lead 권고**: 🟡 **자본 1억+ 가능 시 검토** (현 규모 부족)

---

## 6. 비교 매트릭스 (객관적)

| Path | 기대 ROI | 위험 | 시간 | 자본 | 권고 |
|---|---|---|---|---|---|
| **A1 다른 자산군 quant** | -20% ~ +15% | 🔴 alpha decay | 2~3개월 | 1,000~3,000 | ❌ |
| A2 위탁 운용 | 연 5~12% | 🟡 매니저 의존 | 0 | **1억+** | 🟡 자본 부족 |
| A3 Hummingbot SaaS | 0~1% / 월 | 🔴 사기 / decay | 1~2개월 | 500~2,000 | ❌ |
| A4 robo-advisor | 연 5~10% | 🟢 안전 | 0 | 100+ | 🟡 D2 대안 |
| **B1 11 SBU 가속** | 본업 + α (compounding) | 🟢 이미 매출 | 1주~3개월 | 0~500 | ✅ **최우선** |
| **B2 CTS-AI 본업** | 연봉 5~15% | 🟢 안정 | 매일 9~6 | 0 | ✅ 진행 중 |
| **B3 AI Consulting** | 0~500/월 (6개월) | 🟢 학습 자산 | 5~20h/주 | 0 | 🟢 검토 |
| C1 Agentic SaaS | 50만 ~ 5,000만/월 | 🔴 PoC 위험 | 6~12개월 | 5,000+ | 🟡 큰 투자 |
| **C2 정보재 / 강의** | 1,500만 ~ 5억 누적 | 🟢 passive | 2~6개월 | 0~500 | 🟢 검토 |
| C3 Affiliate / 광고 | 0~500만/월 | 🟢 B1 보조 | B1 일부 | 0 | ✅ B1 결합 |
| D1 예금 / CMA | 연 3~4% | 🟢 0 | 0 | 100+ | ✅ 20~30% |
| **D2 미국 ETF** | 연 7~10% | 🟢 장기 안전 | 0 | 1,000+ | ✅ **40~60%** |
| D3 부동산 / REITs | 연 4~7% | 🟡 자본 규모 | 0 | **1억+** | 🟡 자본 부족 |

---

## 7. Strategy Lead 권고 (cold honest)

### 7.1 자본 1,000~8,000만원 분산 권고 (위험 차등)

```
보수 (자본 보호 60~70%)
├─ D2 미국 ETF (S&P 500 / QQQ)  — 40~60%  (장기 우상향, 연 7~10%)
├─ D1 예금 / CMA                  — 10~20%  (비상자금, 연 3~4%)
└─ A4 robo-advisor (선택적)       — 0~10%   (보수 운용)

성장 (자본 활용 30~40%)
├─ B3 AI Consulting / 강의       — 0 (자본 안 듦, 시간 투입)
├─ C2 정보재 / 강의 (passive)    — 0~500    (1~6개월 build, compounding)
└─ B1 11 SBU 가속 광고비          — 500~3,000 (월별 분산, ROI 검증 후 확장)
```

### 7.2 비추 path (38일 학습 기반)
- ❌ A1 다른 자산군 quant (alpha decay 동일 패턴 반복)
- ❌ A3 Hummingbot / 3rd party SaaS (사기 위험 + decay)
- ❌ NFT / Web3 (변동성 + 사기)

### 7.3 시간 우선순위 (다음 30일)

**Week 1 (5/12~5/18)** — 본업 + 자본 보호
- B1 11 SBU 매출 분석 + 우선순위 재정의 (3~5일)
- D2 미국 ETF 매수 plan + 분할 매수 schedule (1일)

**Week 2~3 (5/19~6/1)** — passive income build 시작
- C2 정보재 첫 콘텐츠 제작 (Substack / 강의 outline)
- B3 AI Consulting target client 리스트 + outreach 5건

**Week 4 (6/2~6/8)** — 검증 + 확장
- B1 + C2 + B3 ROI 측정
- 효과 있는 path 자본 추가 투입 결정 (G2 owner)

### 7.4 4주 후 (6/8) 재평가

**평가 metric**:
- B1: SBU 매출 변화 (절대 + ROI %)
- C2: 정보재 첫 subscriber / 강의 등록 / 책 outline
- B3: AI Consulting 첫 paid contract 또는 lead 5+
- D2: ETF 매수 진행 + 시장 평균 대비

**결정 게이트**:
- 1+ path positive ROI → 추가 자본 투입
- 0 path positive → path 재정의 (이번 v11 PoC 같은 무한 반복 차단)

---

## 8. 자본 입금 권고 — quant-bot 영구 ❌

본 PoC closure 확정. quant-bot 자본 입금 권고 = **영구 0원**.

5/12 PM2 stop 완료:
- quant-bot-live: stopped
- liquidation-stream (Binance / Bybit / OKX): stopped
- market-news-updater: stopped

코드 아카이브 권고 (별도 작업):
- master `v11-poc-closure-20260512` tag
- 38일 학습 인벤토리 박제 (본 doc + active-tasks.md + sweep 결과)

---

## 9. owner 한 줄 결정 매트릭스

| ID | 결정 | 권고 |
|---|---|---|
| **R1** | 본 연구 path 채택 우선순위 | **B1 + D2 + C2 + B3 결합** |
| R2 | quant-bot closure 영구 확정 | ✅ (PM2 stopped, master tag 옵션) |
| R3 | 자본 1,000~8,000만원 분산 | **40~60% D2 + 10~20% D1 + 0~10% 성장 path** |
| R4 | 6/8 (4주) 재평가 | ✅ |
| R5 | A1~A3 quant 재시도 | ❌ |
| R6 | NFT / Web3 | ❌ |

**owner 한 줄 결정** 시 즉시 다음 작업 진행 (B1 SBU 분석 / D2 ETF plan / C2 콘텐츠 outline / B3 outreach).

---

## 10. 가장 honest 한 한 줄

**38일 quant PoC 학습 자체가 자산. 그 학습으로 1인 retail crypto quant 가 안 통한다는 것을 입증함. 이제 본업 + AI Consulting + 미국 ETF 결합이 가장 honest 한 수익 path. 자본 보호 60%+ 우선, 성장 path 30%+ 시간 투입, 무한 quant PoC 반복 차단.**

---

**작성 책임**: Strategy Lead Claude Opus 4.7 (Financial Advisor 자율 G1, 2026-05-12).
**다음 작업**: owner R1~R6 결정 후 가장 우선순위 path 즉시 진행.
