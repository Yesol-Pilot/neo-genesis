# Active Tasks — 에이전트 공유 작업 목록

> **규칙:** 작업 시작/완료 시 갱신. 담당 에이전트와 상태를 명시.  
> **최종 갱신:** 2026-04-27 by Claude Opus 4.7 (Strategy Lead — Weekly Progress Review #2)

---

## 📅 Weekly Progress Review #2 (2026-04-27 Mon 10:05 KST, Strategy Lead)

**기준 기간**: 지난 7일 (2026-04-20 ~ 2026-04-27)

### 진척 카운트
- **Commits (auto-trading)**: 10건 (4/26 텔레그램 fix + Phase Gate Monitor + Liquidation Stream 실제 구현 / 4/25 Phase -1 공식 closure / 4/24 dispatcher + backtest v2 + 9-Layer Kill Switch tests)
- **Phase 0 게이트**: 2/8 ✅ (#4 9-Layer Kill Switch tests, #6 PAPER 회귀 없음) — Week #1 대비 변동 없음
- **Liquidation Stream**: PM2 online (uptime 8.2h, restarts=0), **received 7일 합계 = 0건** (Phase 0 gate#3 임계 100/일 vs 0). 핸드오프 진단: Binance `!forceOrder@arr` aggregated stream 한계 (코드 버그 아님). **이중구독 패치 미완**
- **거래 (7일)**: open=0 / close=0 / pnl=$0 (PAPER mode, 알파 코드 0개)
- **Killswitch (7일)**: 0건 발동
- **VM 메모리**: quant-bot-live 216MB / liquidation-stream 84MB / market-news-updater 75MB — 안정. **Heap 92.45%** (Week #1 88.32% 대비 +4.13%pt 상승, 90~95% 박스권 재진입 — 추세 주시 필요)
- **Lease**: PAPER mode 유지 (Risk Officer 09:00 로그 확증)

### 알파 진행 (v11 6 알파) — Week #1 대비 변동 없음 (2026-04-27 갱신: A1 wiring 완료)
- **A1 Liquidation Cascade**: 인프라 ✅ (이중구독 패치) / 알파 로직 ✅ / orchestrator wiring ✅ / VM 배포 ⏳ (owner gate)
- **A2 Mean Reversion OU**: 코드 ❌
- **A3 Extreme Funding**: 인프라 ✅ / 알파 ❌
- **A4 Macro Event**: 코드 ❌
- **A5 Funding/Basis Harvest**: 인프라 ✅ / v11 알파 wiring ❌
- **A6 Alt MM**: 코드 ❌
- **결론**: **A1 페이퍼 14일 검증 가능 상태** (VM 배포 후 데이터 흐를 때)

### 자본 입금 권고
- **트리거**: 1+ 알파 페이퍼 14일 Sharpe ≥ 1.2 + DSR ≥ 0.5 → Phase 1 통과 → 1000만원
- **현재 상태**: ❌ 알파 코드 0개, 14일 검증 시작 불가
- **권고**: **🚫 아직 입금 미권고** (Week #1 동일 — 이번 주 알파 진척 0건)

### 다음 주 우선순위 (Strategy Lead 자율 결정 — Week #1 우선순위 재확인 + 보강)
1. **A1 Liquidation Cascade 알파 로직 + Binance 이중구독 패치 동시 진행 (P0)** — 둘은 분리 불가능. 알파 로직만 만들고 stream에서 데이터가 0이면 검증 불가. cryptofeed `_check_update_id` 패턴 차용 + symbol-level `<symbol>@forceOrder` (BTC/ETH/SOL) + dedup
2. **A3 Extreme Funding 알파 wiring** — 인프라 ✅ 활용, 임계 `|F| > 0.08%` (외부 검증 결과)
3. **Heap 92.45% 추세 모니터링** — 7일 연속 90%+ 시 메모리 누수 가설 재진단 필요
4. **nautilus_trader Python 통합** — Backtest Validator (Phase 0 Task 0.3)
5. **Phase 0 Task 0.5 production 배선** — 9-Layer Kill Switch dispatcher → orchestrator/runner wiring

### 주간 변동 정리 (Week #1 → Week #2)
| 항목 | Week #1 (4/26) | Week #2 (4/27) | 변동 |
| --- | --- | --- | --- |
| Phase 0 게이트 | 2/8 ✅ | 2/8 ✅ | 변동 없음 |
| 알파 코드 | 0/6 | 0/6 | 변동 없음 |
| Liquidation 7일 합계 | 0건 | 0건 | 그대로 (이중구독 미패치) |
| Heap | 88.32% | 92.45% | +4.13%pt (90~95% 박스권 재진입) |
| 거래 7일 | 0건 | 0건 | 변동 없음 |
| Killswitch 7일 | 0건 | 0건 | 변동 없음 |
| 자본 입금 권고 | 미권고 | 미권고 | 변동 없음 |

**판정**: Week #1 → Week #2 사이 1일 차이 + RAG 마스터 설계 v1에 인지적 자원 집중되어 quant 알파 진척 0. **다음 주 (Week #3, 5/4) 까지 A1 알파 로직 + 이중구독 패치 1건 이상 commit 권고**.

### owner 결정 대기 (Week #1 carry-over)
- **4 crash tick 데이터 구매** (Tardis.dev $99/월 또는 CoinAPI) — Phase 0 backtest v2 검증 필수
- **A1 알파 PAPER 진입 시점** — 코드 완성 후 즉시 vs 추가 검증

(다음 주간 리뷰: 2026-05-04 Mon 10:05 KST — cron `5 10 * * 1`)

---

## 📅 Weekly Progress Review #1 (2026-04-26, Strategy Lead)

**기준 기간**: 지난 7일 (2026-04-19 ~ 2026-04-26)

### 진척 카운트
- **Commits**: 14건 (PR #3 Phase -1 closure / PR #4 Liquidation Stream 실제 구현 / PR #5 Phase Gate Monitor + 텔레그램 fix / Phase 0 dispatcher + backtest v2 scaffold + 9-Layer Kill Switch unit tests)
- **Phase 0 게이트 통과**: 2/8 (#4 9-Layer Kill Switch tests ✅, #6 PAPER 회귀 없음 ✅) + 진행 중 4건
- **Liquidation Stream**: PM2 id 4 online (uptime 3.7h), **received=0** (7일 합계 0건, 시장 조용 또는 URL 검증 필요)
- **거래 (7일)**: open=0 / close=0 / pnl=$0 (PAPER mode, 알파 코드 0개)
- **Killswitch (7일)**: 0건 발동
- **VM 메모리**: quant-bot-live 215MB / liquidation-stream 77MB / market-news-updater 75MB — 안정

### 알파 진행 (v11 6 알파)
- **A1 Liquidation Cascade**: 인프라 ✅ (`liquidation-stream.js` PM2 가동 중) / 알파 로직 ❌
- **A2 Mean Reversion OU**: 코드 ❌ (legacy `mean-revert-agent.js` 별개)
- **A3 Extreme Funding**: 인프라 ✅ (`funding-rate.js` / `funding-spike-guard.js` L9) / 알파 ❌
- **A4 Macro Event**: 코드 ❌
- **A5 Funding/Basis Harvest**: 인프라 ✅ (`funding-harvester.js` / `funding-harvest-manager.js`) / v11 알파 wiring ❌
- **A6 Alt MM**: 코드 ❌
- **결론**: **0/6 페이퍼 모드 14일 검증 가능**

### 자본 입금 권고
- **트리거**: 1+ 알파 페이퍼 14일 Sharpe ≥ 1.2 + DSR ≥ 0.5 → Phase 1 통과 → 1000만원
- **현재 상태**: ❌ 알파 코드 0개, 14일 페이퍼 검증 시작 불가
- **권고**: **🚫 아직 입금 미권고** (이유: Phase 0 미완 + v11 알파 코드 미구현)

### 다음 주 우선순위 (Strategy Lead 자율 결정)
1. **A1 Liquidation Cascade 알파 로직 구현** — 가장 진척 가까움 (인프라 가동 중)
2. **Liquidation Stream live URL 검증** — received=0 원인 진단 (시장 조용 vs URL 오작동)
3. **A3 Extreme Funding 알파 wiring** — 인프라 ✅ 활용
4. **nautilus_trader Python 통합** — Backtest Validator
5. **Heap 추세 24h 관측** (88.32% 박스권 유지 여부)

### owner 결정 대기
- **4 crash tick 데이터 구매** (Tardis.dev $99/월 또는 CoinAPI) — Phase 0 backtest v2 검증 필수
- **A1 알파 PAPER 진입 시점** — 코드 완성 후 즉시 vs 추가 검증

(다음 주간 리뷰: 2026-05-04 Mon 10:05 KST — cron `5 10 * * 1`)

---

## 🟣 RAG Master Design v1 — PC + 플릿 통합 RAG 도입 (2026-04-26 신설)

기반: [`.agent/knowledge/20260426_RAG_MASTER_DESIGN_v1.md`](../knowledge/20260426_RAG_MASTER_DESIGN_v1.md) + 부록 9개 (`.agent/knowledge/rag-master/`)
owner 지시: "PC 전체 통합 RAG + 카테고리별 최적화 RAG 구성 + 플릿 디바이스 RAG화, 다중 병렬 에이전트로 심층 리서치 + 상세 설계서 작성"
세션: Wave 1 (8 병렬 리서치) + Wave 2 (architect 수렴 + reviewer 적대 검증) → 마스터 + 부록 10개 작성 완료 (2026-04-26 ~ 2026-04-27 KST)

### 채택된 7 핵심 결정 (요약)
- **1. ChromaDB 마이그**: 점진적 컬렉션 단위 cutover + `rag_search`에 `backend` 파라미터 (Sora rag_search 단절 P0 차단)
- **2. Contextual Retrieval**: Phase 6 도입 (>100K chunk), Phase 1은 인프라만, Haiku 4.5 + prompt cache 강제
- **3. SSOT 그래프**: LightRAG (Phase 2) → HippoRAG 2 pilot (Phase 6 paper 한정)
- **4. yesol 격리**: read-only + JWT scope 제한 (secret/personal-notes endpoint 비공개 404)
- **5. Provenance**: source_type + decay_factor (human=1.0, llm_output=0.5) + provenance_chain depth 추적
- **6. GPU 충돌**: ColQwen2 → mac-studio MLX primary, sol01 ColQwen2-2B INT4 fallback, KURE+BGE 상시 상주
- **7. 컬렉션**: 6 컬렉션 분리 (`neo_ssot/code/paper/notes/quant/secret`) + `neo_chat` Phase 5 추가

### 기술 stack
- VDB: **Qdrant 1.16+** (primary, ysh-server) + LanceDB (multimodal/edge) + pgvector (Supabase 통합)
- 임베딩: **KURE-v1** (한국어) + **Voyage-Code-3** (코드) + **Voyage-3-large** + **Cohere embed-v4 128K** (논문) + **ColQwen2 MLX** (멀티모달)
- 리랭커: **BGE Reranker v2-m3** (sol01 자체 호스팅, 무료, 한국어 강)
- 검색: Hybrid (BM25 mecab-ko + dense + RRF k=60) + cross-encoder rerank → recall@10 65~78% → 91%+
- 오케스트레이션: **LlamaIndex + 단일 MCP 게이트웨이 (ysh-server:7701)**
- Eval: RAGAS + Promptfoo + 한국어 자체 golden 50 + AgentDojo + PoisonedRAG/GASLITE 회귀
- 비용: 시나리오 B (권장) **$15~25/월** (Phase 0~5: $5~10, Phase 6 이후 $15~25)

### 24주 롤아웃
- **Phase 0** (Week 1~2): Qdrant + watchdog + provenance 인프라
- **Phase 1** (Week 3~4): sol01 GPU 임베딩 분리 + KorMTEB Recall@10 > 85%
- **Phase 2** (Week 5~6): 6 컬렉션 분리 + LightRAG + secret 격리
- **Phase 3** (Week 7~9): yesol read-only + ChromaDB 완전 cutover
- **Phase 4** (Week 10~12): mac-studio ColQwen2 MLX + 멀티모달 인덱싱
- **Phase 5** (Week 13~18): 모바일 PWA + Contextual Retrieval 인프라
- **Phase 6** (Week 19~24): HippoRAG 2 pilot + Contextual Retrieval 실제 도입 + 선택적 hot-standby

### 운영자 의사결정 5개 (다음 세션 응답 필요)
- [ ] (a) Phase 0 시작 시점 (즉시 / 다음주 / quant v11 Phase 0 완료 후 — **권고: 다음주**)
- [ ] (b) Voyage API 사용 vs 전부 self-host (**권고: 시나리오 B = API + self-host 혼합**)
- [ ] (c) desktop-yesol 격리 강도 (**권고: read-only + JWT scope 제한**)
- [ ] (d) ColQwen2 mac-studio 의존도 (**권고: on-demand + sol01 fallback, Phase 4 후 6개월 데이터로 재결정**)
- [ ] (e) Contextual Retrieval 비용 cap (**권고: $50/주, Phase 6 진입 시점 Stop/Go #5**)

### Phase 0 Day 1~7 작업 진행 상태 (2026-04-27 갱신)
- [x] **Day 1** ✅ 정책 8개 파일 (`.agent/policies/rag_governance.yaml`, `rag_source_allowlist.yaml`, `rag_jwt_scopes.yaml`, `work_pc_rag_isolation.yaml`, `rag_provenance_overrides.yaml`, `rag_eval_baseline.yaml`, `rag_watchdog.yaml`, `gitleaks-korean-rules.toml`)
- [x] **Day 2** ✅ Pydantic 스키마 (`src/core/rag_v2/chunk_metadata.py`) + provenance 분류기 (`src/core/rag_v2/provenance_classifier.py`) + Supabase DDL (`.agent/migrations/rag_v2/001_initial.sql`) + golden 10 (`tests/rag_golden/ssot_korean_v1.json`)
- [x] **Day 3** ✅ migrate 스크립트 (`scripts/rag_v2/migrate_chromadb_to_qdrant.py`) + `rag_engine.py`에 `backend` 파라미터 추가 (default=chroma, syntax/import/signature 검증 통과, provenance decay + Qdrant fallback 통합)
- [x] **Day 4** ✅ sol01 KURE-v1 FastAPI (`scripts/rag_v2/embedding_service.py`, port 7702, GPU VRAM 가드 4GB)
- [x] **Day 5** ✅ BGE Reranker v2-m3 FastAPI (`scripts/rag_v2/rerank_service.py`, port 7704) + mecab-ko 검증 (`scripts/rag_v2/check_mecab_ko.py`, silent fallback 차단)
- [x] **Day 6** ✅ watchdog 스캐폴드 (`scripts/rag_v2/watchdog_indexer.py`, Blake3 + SQLite 캐시 + Single-writer lock)
- [x] **Day 7-A (로컬)** ✅ syntax check 9 Python + 7 YAML + 1 JSON + 1 TOML 모두 통과 / provenance 회귀 8/8 통과 / `python scripts/sync_agent_context.py --updated-by claude` 실행 → ssotRevision `ba30bd8fdf3b22e9` → **`d3473c2c2ae51b98`** bump
- [ ] **Day 7-B (Owner 실행 대기)** — `.agent/knowledge/rag-master/RUNBOOK_PHASE_0.md` 참조
  - 의존성 설치 (`qdrant-client / blake3 / pydantic / FastAPI / uvicorn / kiwipiepy`)
  - ysh-server Qdrant 1.16+ 컨테이너 + API key 설정
  - Supabase 마이그 apply (`001_initial.sql`)
  - dry-run 마이그 검증 (`migrate_chromadb_to_qdrant.py --dry-run`)
  - sol01 임베딩 + reranker 서비스 가동
  - kiwipiepy 설치 (현재 한국어 토크나이저 0개 — `check_mecab_ko.py` 검증 결과)
  - fleet 동기화 (sol01 / ysh-server / mac-studio 4대 — desktop-yesol는 이미 sync됨)
  - Phase 0 게이트 검증 → Phase 1 진입 결정

### Phase 1 Tasks 완료 (2026-04-27, 컨텍스트 재개 후 — Claude Opus 4.7)
- [x] **Task 1: mcp_tool_policy.yaml RAG 항목 추가** ✅ — `.agent/policies/mcp_tool_policy.yaml`에 RAG 서버 3개 엔트리 추가 (ysh-server MCP gateway G1 / sol01 embedding service G1 / read-only blast_radius_ceiling=1)
- [x] **Task 2: run_golden_eval.py** ✅ — `scripts/rag_v2/run_golden_eval.py` (RAGAS eval runner, 비동기, $5/day 예산 캡, YAML baseline 출력)
- [x] **Task 3: bm25_indexer.py** ✅ — `scripts/rag_v2/bm25_indexer.py` (BM25 + 한국어 토크나이저 브리지: kiwipiepy → konlpy_mecab → whitespace, Tantivy primary → rank_bm25 fallback, Blake3 캐시)
- [x] **Task 4: mcp_gateway.py** ✅ — `scripts/rag_v2/mcp_gateway.py` (FastAPI port 7701, JWT scope 검증, Supabase `rag_audit_log` + 로컬 JSONL fallback, LlamaIndex FunctionTool, score×decay 정렬)
- [x] **Task 5: router.py** ✅ — `src/core/rag_v2/router.py` (LangGraph 스타일 RouterState TypedDict, 키워드 분류, RRF k=60, top-50%-of-top-score fan-out 최대 3컬렉션, httpx gateway fallback)
- syntax: 신규 5 Python 파일 ALL_PYTHON_OK

### 작성된 자산 (총 28 파일)
- 마스터 + 부록 11개 (`.agent/knowledge/20260426_RAG_MASTER_DESIGN_v1.md` + `rag-master/`)
- 정책 8개 (`.agent/policies/rag_*.yaml` + `gitleaks-korean-rules.toml`) + mcp_tool_policy.yaml 수정 (RAG 3 엔트리)
- 마이그레이션 1개 (`.agent/migrations/rag_v2/001_initial.sql`)
- Python 모듈 13개 (`src/core/rag_v2/__init__.py + chunk_metadata.py + provenance_classifier.py + router.py` / `scripts/rag_v2/__init__.py + migrate + embedding + rerank + check_mecab + watchdog + run_golden_eval + bm25_indexer + mcp_gateway`)
- 테스트 데이터 1개 (`tests/rag_golden/ssot_korean_v1.json`)
- 코드 변경 1건 (`src/core/rag_engine.py` backend 파라미터 추가, default=chroma 유지)
- RUNBOOK 1개 (`.agent/knowledge/rag-master/RUNBOOK_PHASE_0.md`)

### Day 7-A 검증 결과 (2026-04-27)
- 9 Python 파일 syntax: ALL_PYTHON_OK
- 7 YAML 정책 parse: YAML_OK
- 1 JSON golden + 1 TOML rules: JSON_OK / TOML_loaded 2733 chars
- provenance 분류기 회귀: 8/8 PASS (handoff heading 분기 + LLM 자동 식별 + tool_log 일반 + external_citation PDF/TeX 모두 정확)
- rag_engine.py 시그니처: `RAGEngine.search(self, query: str, n_results: int = 5, file_filter: str = None, backend: Optional[str] = None) -> list[dict]`
- 운영자 환경 사실: 한국어 토크나이저 4개 모두 미설치 (kiwipiepy / konlpy / eunjeon / mecab-python3) — Phase 0 Day 5 게이트 차단됨, owner kiwipiepy 설치 필요

### 잔존 위험 (Wave 2 reviewer가 P0~P2로 분류, 12개)
- **P0-1**: `sora_engine.py` backend 분기 부재 (가장 큰 가정 위반) → Day 3 작업으로 차단
- **P0-2**: sol01 12GB VRAM OOM (ColQwen2 + KURE + BGE + ComfyUI 동시) → 결정 6 채택안
- **P0-3**: LanceDB versioning이 right-to-be-forgotten 미보장 → `cleanup_old_versions()` + `compact_files()` 의무화
- **P1-4~7**: 한국어 credential 미커버 / PDF prompt injection / JWT 발급 경로 / 멀티 에이전트 동시 write
- **P2-8~12**: Contextual Retrieval 토큰 폭발 / ysh-server 16GB / mecab-ko Windows 설치 / Phase 0 1주 비현실적 / mac-studio offline

### Stop/Go 게이트 5개
1. NDCG@10 < 0.65 (golden 50, Phase 1 후) → Phase 2 차단
2. Qdrant cutover NDCG Delta < -5% → 해당 컬렉션 cutover 차단
3. sol01 VRAM 여유 < 4GB → ColQwen2 강제 mac-studio 라우팅
4. desktop-yesol에서 `neo_secret` 접근 1회 성공 → 전체 JWT 시스템 즉시 재감사
5. Contextual Retrieval 7일 비용 > $50/주 → 즉시 비활성화

👤 owner 결정 → Claude Opus 4.7 / Sora 협업 / Codex fallback

---

## 🟣 Financial Advisor System v1 — 7-에이전트 자율 운영 (2026-04-26 신설)

기반: `.agent/knowledge/20260426_FINANCIAL_ADVISOR_SYSTEM_v1.md`
owner 지시: "어드바이저 + 부하 에이전트 + 자본 검증 시 무제한 입금 + 자율 판단으로 owner 이익 최대화"

### 어드바이저 핵심 결정 (자율, owner 위임)
- **목표 재설정**: 일 1% (owner 명시) → **상위분위 0.6~1.0% 메인 트랙 + 5% 한도 공격형 sleeve 별도** (Phase 3 진입 후)
- **레버리지 5x 하드캡 양보 불가** (파산확률 매트릭스 근거)
- **검증 → 자본 → 확장 단계 게이트** 의무 (Phase 0/1/2/3/4)
- **자산군 확장**: 크립토 → Phase 3.5 부터 cross-exchange / Phase 4 부터 미국 주식·FX·한국 주식 (SSOT §11)
- **자본 입금 (1000만원~8000만원 할당 예정)**:
  - 한꺼번에 풀 입금 절대 비추 (통계적 자살)
  - 권고 입금 schedule: Phase 1 통과 → 1000만원 / Phase 2 통과 → +2000만원 / Phase 3 통과 → +5000만원
  - 활성 자본 vs 보유 자본 분리 (cold storage, 거래소 분산, 세금 적립 25%)

### 7-에이전트 구현 진행 상태

- [x] **Strategy Lead (Claude Opus 4.7)** ✅ 활성 (이 세션)
- [x] **Risk Officer 일일 리포트 자동화** ✅ (2026-04-26 13:13 KST)
  - 📍 `auto-trading/scripts/daily-risk-officer-report.js`
  - 📍 VM cron: `0 0 * * * /usr/bin/node /home/yesol/quant-bot/scripts/daily-risk-officer-report.js` (매일 09:00 KST)
  - 📍 로그: `/home/yesol/quant-bot/logs/risk-officer/YYYY-MM-DD.log`
  - 첫 실행 결과: 봇 정상, Heap 88.32%, mode=PAPER, killswitch 0건, liquidation 0건 (scaffold)
  - ⚠️ 텔레그램 전송 실패 — 봇 토큰 dead 추정. **별도 fix task 필요**
- [ ] **Alpha Researcher** — Claude general-purpose subagent + WebSearch, 주 1회 cron 미설정
- [ ] **Execution Operator** — Sora + gcloud + pm2 (현 수동 운영)
- [ ] **Backtest Validator** — nautilus_trader 통합 미완 (Phase 0 Task 0.3)
- [ ] **Compliance Checker** — Strategy Lead 의 4-Step 자동 hook 미구현
- [ ] **Reporting Analyst** — 주간/월간 리포트 cron 미설정 (일일은 Risk Officer 가 일부 커버)

### 후속 (오늘 세션 외)
- [x] **텔레그램 봇 owner /start 완료** ✅ (chat_id 1566967334 활성 확인, getUpdates 로 검증)
- [x] **Risk Officer Telegram 메시지 fix** ✅ (parse_mode 제거 + UTF-8 buffer + chat_id integer cast). 영문/이모지 plain text 안전 모드. 다음 cron 실행 시 자동 검증
- [x] **Liquidation Stream 실제 구현 + VM 가동** ✅ (PR #4 MERGED, 304줄, 13 tests, PM2 id 4 online)
- [ ] **Liquidation 첫 row 도착 검증** — 24h+ 누적 0건 + raw 30초 WS probe 0건 (2026-04-26 22:11 KST Strategy Lead 진단). **Root cause: Binance `!forceOrder@arr` aggregated stream 한계** (코드 버그 아님). 봇 재시작 의미 없음. **이중구독 패치 필수** — `<symbol>@forceOrder` (BTC/ETH/SOL 등) + dedup, cryptofeed `_check_update_id` 패턴 차용. Phase 0 Task 0.1 미완 부분, 다음 코딩 세션 최우선
- [ ] **Heap 메모리 누수 추적** — 90% → 95% → 88% 박스권 변동. 메모리 누수 가설 잠정 부정. 24h 추세 더 보기
- [ ] **9-Layer Kill Switch wiring 검증** (orchestrator/runner 통합)
- [ ] **nautilus_trader + DSR/PBO/CPCV 통합** (Backtest Validator)
- [ ] **Alpha Researcher 주간 cron 설정** (월요일 09:00) — 다자산 리서치 범위로 즉시 확장 (어드바이저 결정)
- [ ] **Reporting Analyst 주간 리포트** (월요일 10:00)
- [ ] **Compliance Checker hook 자동화** (Strategy Lead 의 4-Step 게이트)

### 어드바이저 자율 결정 (2026-04-26, 4 게이트)

| Gate | 결정 | 트리거 |
| --- | --- | --- |
| 1. 자본 입금 schedule | ✅ **승인** (1000만원 → 3000만원 → 8000만원 단계적) | Phase 1 통과 (1+ 알파 페이퍼 14일 Sharpe ≥ 1.2 + DSR ≥ 0.5) → 1000만원 |
| 2. 공격형 sleeve 활성 | ⏸️ **defer to Phase 3** | 메인 자본 3000만원 활성 + 90일 누적 +20% 후 재평가 |
| 3. 자산군 확장 진입 | ⏸️ **Phase 4 시점 재평가** + Alpha Researcher 다자산 리서치 범위 즉시 확장 | crypto 알파 1+ 라이브 90일 통과 후 미국 주식 진입 |
| 4. 텔레그램 봇 fix | ✅ owner /start 완료 (chat_id 1566967334) + 스크립트 UTF-8 fix | — |

### Auto-Progression 시스템 (2026-04-26 가동, PR #4 #5 MERGED + 2 Claude routines)

**자동 운영 루프 5종 (owner 수동 개입 최소화):**

| # | 루프 | 위치 | 주기 | 상태 |
| --- | --- | --- | --- | --- |
| 1 | Risk Officer cron | VM cron | 매일 09:00 KST | ✅ |
| 2 | Phase Gate Monitor cron | VM cron | 매시간 정각 | ✅ |
| 3 | Liquidation Stream | VM PM2 | 24/7 | ✅ (received 시장 의존) |
| 4 | **Daily Strategy Briefing** | **Claude routine** | **매일 10:01 KST** | ✅ **신규** |
| 5 | **Weekly Progress Review** | **Claude routine** | **매주 월요일 10:05 KST** | ✅ **신규** |

#### Claude routine 2종 (2026-04-26 등록)
- `quant-bot-daily-strategy-briefing` (cron `0 10 * * *` KST):
  - VM 봇 헬스 + Supabase 종합 + Phase 게이트 진척 + 자율 액션 + 한국어 텔레그램 발송
  - SKILL.md: `C:\Users\yesol\.claude\scheduled-tasks\quant-bot-daily-strategy-briefing\SKILL.md`
- `quant-bot-weekly-progress-review` (cron `5 10 * * 1` KST):
  - 7일 데이터 분석 + 알파 진행 + 자본 입금 권고 트리거 검토 + 다음 주 우선순위
  - SKILL.md: `C:\Users\yesol\.claude\scheduled-tasks\quant-bot-weekly-progress-review\SKILL.md`

**자동 트리거 흐름:**
1. Risk Officer 09:00 → 봇 + Supabase 일일 데이터
2. Phase Gate Monitor (매시간) → 게이트 통과/임박 즉시 알림
3. Daily Strategy Briefing 10:01 → Strategy Lead 종합 분석 + 자율 액션
4. (월요일만) Weekly Progress Review 10:05 → 자본 입금 권고 트리거 검토
5. Phase 0 전체 통과 → Phase 1 진입 권고 + 1000만원 입금 권고 자동
6. PR auto-merge (별도 owner action: `auto-merge.yml.pending` + workflow PAT scope)

**G2 자율 진입 금지 영역** (어드바이저 헌장):
- 자본 이동 / 입금 / 출금
- LIVE 모드 전환
- 외부 거래소 변경
- 4 crash tick 데이터 구매 (Tardis.dev / CoinAPI)

**Auto-Progression 가동 검증 (2026-04-26):**
- Phase Gate Monitor 첫 실행: Phase 0 = 2 ✅ + 1 ⏳ + 4 ✋ + 1 ⚠️
- Telegram alerts sent: 2 (텔레그램 fix + 봇 활성 동시 검증)
- Liquidation Stream PM2 id 4 online (received=0, 시장 의존)
- Risk Officer cron 등록 (0 0 * * *)
- Phase Gate Monitor cron 등록 (0 * * * *)

---

---

## ✅ 완료 — AI Agent Environment Optimization 내재화 (2026-04-24, Codex)

- [x] OSS 프레임워크, 핵심 연구, UX/제품 패턴, 평가, 보안, 거버넌스 기준을 `.agent/knowledge/20260424_AI_AGENT_ENVIRONMENT_OPTIMIZATION_BLUEPRINT.md`로 정리
- [x] `.agent/NEO_MASTER_RULES.md`, `.agent/BIBLE.md`, `.agent/knowledge/AGENT_RUNTIME_OPTIMIZATION.md`, `.agent/knowledge/AGENT_SHARED_MEMORY.md`에 참조 반영
- [x] `D:/00.test/AGENTS.md`, `D:/00.test/CLAUDE.md`에 PC 전체 기본값 반영
- [x] `python scripts/sync_agent_context.py --updated-by codex` 실행으로 runtime adapter 재생성
- [x] v2 심층팩 추가: `research-patterns`, `framework-scorecard`, `benchmark-eval-registry`, `security-governance-threat-model`, `ux-product-pattern-library`, `local-adoption-roadmap`
- [x] local golden task 30개 정의: `tests/agent_golden/tasks/core_v1.json`
- [x] initial eval runner 구현: `scripts/agent_eval_runner.py`
- [x] machine-readable framework registry added: `.agent/registries/agent_frameworks.json`
- [x] machine-readable benchmark registry added: `.agent/registries/agent_benchmarks.json`
- [x] machine-readable security controls registry added: `.agent/registries/agent_security_controls.json`
- [x] registry validation runner and pytest coverage added: `scripts/agent_registry_check.py`, `tests/test_agent_registries.py`
- [x] MCP/tool allowlist policy added: `.agent/policies/mcp_tool_policy.yaml`
- [x] MCP/tool policy validation runner and pytest coverage added: `scripts/agent_mcp_policy_check.py`, `tests/test_agent_mcp_policy.py`
- [x] Agent control-plane snapshot added: `src/core/governance/agent_control_plane.py`
- [x] Sora dashboard API and UI panels added: `/api/v2/agent-control`, Agent Timeline, Approval Queue, Eval Runs, MCP Policy
- [x] Dashboard control-plane pytest coverage added: `tests/test_agent_control_plane.py`
- [x] Continuous research refresh checker added: `scripts/agent_research_refresh.py`
- [x] Research refresh pytest coverage added: `tests/test_agent_research_refresh.py`
- [x] Workflow internalization pack added: `.agent/knowledge/agent-environment/workflow-patterns-v1.md`
- [x] Workflow/orchestration registry added: `.agent/registries/agent_workflows.json`
- [x] Workflow registry validation and pytest coverage added: `scripts/agent_workflow_check.py`, `tests/test_agent_workflows.py`
- [x] Workflow dry-run execution layer added: `scripts/agent_workflow_runner.py`
- [x] Workflow runner pytest coverage added: `tests/test_agent_workflow_runner.py`
- [x] Sora control-plane eval inventory updated to surface workflow dry-run manifests.
- [x] Approved Codex app cron binding created: `neo-genesis-agent-environment-weekly-check`
- [x] Schedule binding registry added: `.agent/registries/agent_schedule_bindings.json`
- [x] Schedule binding validation and pytest coverage added: `scripts/agent_schedule_check.py`, `tests/test_agent_schedule_bindings.py`
- [x] Alert route registry added: `.agent/registries/agent_alert_routes.json`
- [x] Alert route validation and pytest coverage added: `scripts/agent_alert_route_check.py`, `tests/test_agent_alert_routes.py`
- [x] Eval-run collector added: `scripts/agent_run_collector.py`, `tests/test_agent_run_collector.py`
- [x] External alert sends remain paused; local dashboard/file candidates only until separate owner approval.

---

## 🟣 Sora Unified Bible 이행 — Tier S (즉시, 1주 내)

기반: `.agent/knowledge/SORA_UNIFIED_BIBLE.md` §13, `.agent/SORA_CONSTITUTION.md`

- [x] **Bible 작성 + 오너 주권 원칙 반영** — v1 완료 (2026-04-09, Claude)
  📍 `.agent/knowledge/SORA_UNIFIED_BIBLE.md`

- [x] **SORA_CONSTITUTION.md 분리** — 8개 Article, Owner Sovereignty Article 0 (2026-04-09, Claude)
  📍 `.agent/SORA_CONSTITUTION.md`

- [x] **permissions.yaml 스캐폴드** — deny는 자기보호 루프만, ask는 고지-확인 트리거 (2026-04-09, Claude)
  📍 `.agent/policies/permissions.yaml`

- [x] **blast_radius.yaml 스캐폴드** — tier 0-5 + 고지 템플릿 (2026-04-09, Claude)
  📍 `.agent/policies/blast_radius.yaml`

- [x] **capability_tokens.yaml 스캐폴드** — subagent별 base capability (2026-04-09, Claude)
  📍 `.agent/policies/capability_tokens.yaml`

- [x] **progress-ledger.md 스캐폴드** — Magentic-One 2-Ledger 패턴 (2026-04-09, Claude)
  📍 `.agent/shared-brain/progress-ledger.md`

- [x] **Pydantic contracts v1** — SideEffectBudget, DisclosureBundle, ToolCallEnvelope 등 (2026-04-09, Claude)
  📍 `src/core/contracts/sora_contracts.py`

- [x] **Hook pipeline 실제 구현** — SessionStart, UserPromptSubmit, PreToolUse, PostToolUse 4종 (2026-04-09, Claude)
  📍 `src/core/hooks/*.py` (5파일, 11/11 syntax OK)

- [x] **permissions.yaml 로더 + 평가기** — deny>ask>allow, owner_override, device_constraints (2026-04-09, Claude)
  📍 `src/core/governance/policy_engine.py`

- [x] **의도 분류기 (OwnerIntent 생성)** — 키워드 기반 + 엔티티 추출 (2026-04-09, Claude)
  📍 `src/core/nlu/intent_classifier.py`

- [x] **Uncertainty-triggered HITL** — confidence + device tier별 임계값 (2026-04-09, Claude)
  📍 `src/core/governance/hitl_gate.py`

- [x] **progress-ledger 자동 동기화** — PostToolUse → events.jsonl 이벤트 기록 (2026-04-09, Claude)
  📍 `src/core/hooks/post_tool_use.py`

## 🟣 Sora Dashboard v4 — Antigravity-Grade + CLI Code Agent

기반: `.agent/knowledge/SORA_DASHBOARD_V4_SPEC.md`
구현: Codex CLI + Claude CLI (소라가 이 둘을 subprocess로 소환)

### Phase 1: 스트리밍 기반
- [ ] `gemini_stream.py` + `ollama_stream.py` — 스트리밍 어댑터
- [ ] `chat_stream.py` — `/api/v2/chat/stream` SSE
- [ ] `sora_engine.py` — `process_stream()` 추가
- [ ] 프론트엔드 SSE 스트리밍

### Phase 2: Claude CLI + Codex CLI 코딩 에이전트
- [ ] `cli_code_agent.py` — subprocess + stdout 파싱 (Claude CLI `--print --output-format stream-json`)
- [ ] `code_execute.py` — `/api/v2/code/execute` SSE
- [ ] `model_router_v4.py` — intent→model/cli 라우팅
- [ ] `intent_classifier.py` — 코딩 서브 의도

### Phase 3: 프론트엔드 + 마무리
- [ ] `ThinkingBlock` + `ToolCard` + `DiffViewer` + `ModelBadge`
- [ ] `ApprovalDialog` — DisclosureBundle 대시보드 렌더링
- [ ] E2E 테스트

---

## 🟣 3-Checkpoint 이행 완료 (2026-04-10, Claude Code)

기반: `ccr-20260408-122805`, `ccr-20260408-145435`, `ccr-20260408-152816`

- [x] **P0: 텔레그램 봇 SoraEngine.process() 직접 호출 기본 경로화** — Redis brain worker 의존 제거, direct engine을 기본으로 전환, Redis는 선택적 성능 강화로 변경
  📍 `src/core/neo_assistant_bot.py`
  👤 Claude Code

- [x] **Phase 2: 복합 요청 결과 재조립 + 체크리스트 응답** — `reconciliation.py` 신규 생성, `sora_engine.py` 통합. 다건 도구 호출 시 ✅/❌ 체크리스트 자동 생성
  📍 `src/core/reconciliation.py`, `src/core/sora_engine.py`
  👤 Claude Code

- [x] **C1: polyglot_executor sandbox 보안 강화** — `os`, `subprocess` 제거, `__builtins__` 제한 (exec/eval/compile/open/__import__ 차단)
  📍 `src/core/agents/polyglot_executor.py`
  👤 Claude Code

- [x] **C2: gmail_send confirm gate** — 즉시 발송 → `confirmation_required` 반환으로 변경, `gmail_send_confirmed()` 분리
  📍 `src/core/tools/gmail_tools.py`
  👤 Claude Code

- [x] **C3: auth middleware PC Agent 인증 추가** — `/api/pc-agents` 경로에 EXECUTE 인증 레벨 적용
  📍 `src/core/auth_middleware.py`
  👤 Claude Code

- [x] **C4: 약한 대시보드 시크릿 경고** — 시작 시 32자 미만/패턴 매칭으로 보안 경고 출력
  📍 `src/core/sora_dashboard.py`
  👤 Claude Code

- [x] **H1: mission_controller 환경변수 수정** — `TELEGRAM_BOT_TOKEN` → `NEO_ALERT_BOT_TOKEN`
  📍 `src/core/mission_controller.py`
  👤 Claude Code

- [x] **H2: mission_controller dead code 제거** — `_notify_telegram()` 내 unreachable try/except 삭제
  📍 `src/core/mission_controller.py`
  👤 Claude Code

- [x] **H3: agent_router knowledge 키 중복 해소** — 두 정의 병합, 전체 키워드 통합
  📍 `src/core/brain/agent_router.py`
  👤 Claude Code

- [x] **H4: LLM 의도 분류기에 누락 에이전트 추가** — calendar, image, knowledge, governance 포함 전체 에이전트 목록으로 분류 프롬프트 갱신
  📍 `src/core/brain/agent_router.py`
  👤 Claude Code

- [x] **H7: Ollama 하드코딩 IP 제거** — `os.getenv("OLLAMA_HOST")` 패턴으로 교체
  📍 `src/core/brain/agent_router.py`
  👤 Claude Code

- [x] **M2: AssistantMemory._save() 예외 로깅** — bare `pass` → `logger.warning` 추가
  📍 `src/core/sora_engine.py`
  👤 Claude Code

- [x] **M4: telemetry.py DB 비밀번호 하드코딩 제거** — `os.getenv("TELEMETRY_DB_PASSWORD", "")` 패턴으로 교체 + 경고 로깅
  📍 `src/core/telemetry.py`
  👤 Claude Code

- [x] **SSOT: sora_context.json 드리프트 수정** — 하드웨어 스펙, 모델명, Windows 절대경로 정리
  📍 `src/core/data/sora_context.json`
  👤 Claude Code

- [x] **전체 syntax check 12/12 통과**

---

## 🔴 Critical (즉시 처리)

- [ ] **whylab CI/CD 56회 연속 실패** — 스키마 불일치 해결  
  📍 `neo-genesis/src/sbu/whylab`  
  👤 Claude Code (토큰 리셋 후)

- [ ] **whylab integrity_hashes.jsonl 22회 실패**  
  📍 `neo-genesis/src/sbu/whylab`  
  👤 Claude Code (토큰 리셋 후)

---

## 🟡 High (이번 주 내)

- [ ] **원프롬프트 멀티모달 에이전트 시스템 P0 설계/실행** — `내 PC 전체`를 하나의 실행면으로 묶기 위한 P0 범위를 `Session Manager`, `NormalizedInput/SoraResponse`, `live state 분리`, `routing chain 단일화`로 고정하고 구현 계획까지 세분화해야 한다.  
  📍 `.agent/knowledge/20260414_원프롬프트_멀티모달_에이전트_시스템_설계_v1.md`, `src/core/sora_engine.py`, `neo_genesis_daemon.py`, `.agent/knowledge/SORA_UNIFIED_BIBLE.md`, `.agent/knowledge/SORA_MASTER_BLUEPRINT_V2.md`  
  👤 Codex / Claude Code / Antigravity / Sora
  🗓️ 기준일 재확인: `2026-04-24 KST` — 여전히 P0 착수 전이며, 다음 실제 구현 시작점은 `Session Manager`와 `NormalizedInput/SoraResponse`다.

- [x] **설계 명령 멀티에이전트 프로토콜 내재화** — 앞으로 모든 설계/기획/전략/로드맵 명령을 `의도 해석 -> 페르소나 배정 -> 태스크 보드 -> 협업 실행 -> 검증/QA -> 최종 보고` 순서로 처리하는 규칙을 SSOT와 장기 메모리에 반영 완료 (`2026-04-14, Codex`)  
  📍 `.agent/knowledge/20260414_멀티에이전트_설계_실행_프로토콜_v1.md`, `.agent/NEO_MASTER_RULES.md`, `.agent/BIBLE.md`, `.agent/knowledge/AGENT_SHARED_MEMORY.md`  
  👤 Codex

- [x] **소라 Watchdog 오탐지 수정 및 라이브 반영 완료** — `2026-04-08 10:06 KST` maintenance cleanup 이후 stale daemon/dashboard/tunnel을 정리하고 clean rotation을 완료했다. 현재 기준 watchdog 재경고는 보이지 않는다.  
  📍 `neo-genesis/src/core/healer/watchdog.py`, `scripts/start_daemon.ps1`, `logs/daemon_wrapper.log`  
  👤 Codex / Claude Code

- [x] **소라 텔레그램 중복 polling 충돌 정리 완료** — stale bot 인스턴스를 정리한 뒤 현재 로그에는 `getUpdates 200 OK`만 남고 `409 Conflict`는 재발하지 않았다.  
  📍 `neo-genesis/src/core/neo_assistant_bot.py`, `scripts/start_daemon.ps1`, `logs/daemon_stderr.log`  
  👤 Codex / Claude Code

- [ ] **소라 런타임 24~48시간 안정성 관측** — `2026-04-08 10:06 KST` clean rotation 이후 watchdog 오탐지, `409 Conflict`, 대시보드 timeout 재발 여부를 관측해야 한다.  
  📍 `logs/daemon_stderr.log`, `logs/daemon_wrapper.log`  
  👤 Codex / Claude Code

- [x] **GA4 공용 속성 기준 방문자 통계 경로 정리** — `AIForge`, `CraftDesk`, `DeployStack`, `FinStack`, `SellKit`는 개별 property가 아니라 `NeoGenesis - Production (526345390)`의 `hostName` 필터 기준으로 조회해야 함을 확인했고 자동 보고 스크립트에 반영 완료 (`2026-04-09, Codex`)  
  📍 `.agent/knowledge/20260408_GA4_SHARED_PROPERTY_LEARNING.md`, `scripts/ga4_traffic_report.py`, `scripts/ga4_check_streams.py`, `scripts/ga4_traffic_json.py`, `scripts/ga4-all-report.mjs`, `scripts/traffic_alert.py`  
  👤 Codex

- [ ] **Hive Mind 콘텐츠 발행 재개** — 이번달 발행 0건  
  📍 크론 실행 중이나 실제 발행 중단  
  👤 Claude Code / Antigravity

- [ ] **소라 Gmail OAuth 완료** — Calendar scope만 보유  
  📍 서버 `/home/ysh/sora/secrets/`  
  👤 사용자 직접 (소라 `/setup_google` → `/google_code`)

- [ ] **GCP sora-vm 인스턴스 중지** — 비용 절감  
  📍 ethereal-cache-487709-s3  
  👤 미정

- [ ] **플릿 장비 역할/설치 롤아웃** — YSH-Server / home-pc / work-pc / Mac Studio / s26-ultra에 역할별 설치 적용  
  📍 `.agent/knowledge/20260406_Device_Assignment_Plan_v1.md`  
  👤 Codex / Claude Code / 사용자

- [ ] **퀀트 대시보드 스냅샷 갱신 복구** — 실운영 로그는 `launch-live.js` 기준으로 더 최근인데 `portfolio/public/quant/data.json`은 2026-04-02, `neo-genesis/logs/quant_cron.log`는 2026-04-03에서 멈춤  
  📍 `neo-genesis/scripts/update_quant_dashboard.js`, `neo-genesis/scripts/cron_quant_supabase.sh`, `portfolio/public/quant/data.json`, `neo-genesis/logs/quant_cron.log`  
  👤 Codex

- [ ] **퀀트 실운영 오류 패턴 정리 및 대응** — 최근 오류 로그에 Binance `-2019`(margin insufficient), `-4045`(max stop order limit), `-4164`(min notional) 및 Supabase ledger 실패가 반복됨  
  📍 `neo-genesis/auto-trading/logs/error.log`, `neo-genesis/auto-trading/src/scripts/launch-live.js`, `neo-genesis/auto-trading/src/v6-live-runner.js`  
  👤 Codex / Claude Code

- [ ] **Returning Users 중심 일일/주간 보고 전환** — 수익 전 단계의 방문자 보고 North Star를 `7일/28일 Returning Users`와 `Returning User Rate`로 전환하고, 텔레그램 요약/보고서 생성 로직도 같은 기준으로 맞춘다.  
  📍 `.agent/knowledge/20260414_재방문_사용자_중심_성장전략_v1.md`, `.agent/knowledge/20260414_PM_DA_방문자_통계_보고_워크플로우.md`, `src/core/notifications/traffic_pmda_report.py`, `src/core/proactive_agent.py`  
  👤 Codex / Sora

- [ ] **재방문 KPI 매핑표 작성** — `GA4`, `PostHog`, `Search Console` 기준으로 `Returning Users`, `Returning User Rate`, `2페이지 이동`, `허브 재진입`, `CTA click`의 출처와 계산식을 고정한다.  
  📍 `.agent/knowledge/20260414_재방문_사용자_중심_성장전략_v1.md`  
  👤 Codex / Antigravity

- [ ] **재방문 관점 계측 신뢰도 복구 대상 정리** — `CraftDesk`, `DeployStack`, `ReviewLab`의 공식 property, 라이브 태그, 중복 삽입 여부, GA4/PostHog 정합성을 표로 정리해 성장 판단 전 계측 복구 범위를 확정한다.  
  📍 `scripts/ga4_traffic_report.py`, `scripts/posthog_traffic.py`, `.agent/knowledge/20260408_GA4_SHARED_PROPERTY_LEARNING.md`  
  👤 Codex

- [x] **ToolPick 상위 랜딩 5개 재방문 구조 개편** — `/alternatives/*`, `/comparisons/*`, `/pricing/*`, `/reviews/*`, `/calculator`에 `관련 글 2개 + 허브 1개 + 다음 읽을 글 1개` 구조를 공통 적용한다.  
  📍 `src/sbu/toolpick`  
  👤 Codex / Claude Code

- [x] **ToolPick `이번 주 업데이트` 허브 페이지 신설** — 반복 방문 이유를 제공하는 고정 URL을 만들고 홈/상위 랜딩에서 연결한다.  
  📍 `src/sbu/toolpick`  
  👤 Codex / Claude Code

- [x] **재방문 이벤트 4종 추가** — `hub_click`, `series_continue_click`, `weekly_update_visit`, `return_visit`를 PostHog 스키마와 런타임에 반영한다.  
  📍 `src/sbu/toolpick`, `scripts/posthog_traffic.py`  
  👤 Codex / Claude Code

- [x] **시리즈형 콘텐츠 템플릿 확정** — 신규 콘텐츠가 단발성으로 끝나지 않도록 전편/후속편/허브 링크를 포함한 템플릿을 정의하고 실제 게시물에 1건 이상 적용한다.  
  📍 `src/sbu/toolpick/content`, `.agent/knowledge/20260414_재방문_사용자_중심_성장전략_v1.md`  
  👤 Antigravity / Codex

---

- [x] **EthicaAI Melting Pot shard merge + final SSOT 정리**  
   📌 `2026-04-10 10:00 KST` 기준 Mac Studio `24/24`, Linux server `26/26` 완료를 확인한 뒤 `finalize_meltingpot_results.py`로 remote snapshot fetch, JSON 병합, 통계 재계산까지 완료  
   📁 `PAPER/EthicaAI/NeurIPS2026_final_submission/code/scripts/finalize_meltingpot_results.py`, `PAPER/EthicaAI/NeurIPS2026_final_submission/code/outputs/meltingpot/meltingpot_final_results_merged.json`  
   🤖 Codex

- [x] **EthicaAI Melting Pot 최종 원고 반영**  
  📌 merged JSON 기준 `mixed` branch를 확정하고 `unified_paper.tex`의 Melting Pot 문단과 appendix `clean_up` 25-seed 행을 교체했으며 `pdflatex -interaction=nonstopmode -halt-on-error unified_paper.tex` 컴파일도 통과  
  📁 `PAPER/EthicaAI/NeurIPS2026_final_submission/code/outputs/meltingpot/meltingpot_paper_update.json`, `PAPER/EthicaAI/NeurIPS2026_final_submission/paper/unified_paper.tex`, `PAPER/EthicaAI/NeurIPS2026_final_submission/paper/unified_paper.pdf`  
  🤖 Codex

- [ ] **PAPER server 모니터링 채널 근본 복구 적용**  
  📌 user가 회사망에서 `tailscaled --tun=userspace-networking`으로 `ysh-server` tailnet 복구를 완료했고, 접근 표준은 `tailscale ssh ysh@ysh-server` 또는 각 PC별 `%USERPROFILE%\.ssh\config` + `id_ed25519_ysh` 기반 `ssh ysh-server`다. 다음 단계는 Codex 제어 노드에서도 이 device-specific alias/key 경로를 실제로 맞춰서 live monitor fetch를 복구하는 것이다.  
  📁 `PAPER/monitor_experiments.py`, `CREDENTIAL_BIBLE.md`, `%USERPROFILE%\\.ssh\\config`, `%USERPROFILE%\\.ssh\\id_ed25519_ysh`  
  🤖 Codex / 사용자

- [ ] **YSH-Server 증설 후 live 재실측**  
  📌 `DESKTOP-YESOL`을 점프 호스트로 사용해 `hostname=YSH-Server`, `whoami=ysh`, `nproc=16`, `free -h => Mem 16Gi / used 1.2Gi / free 14Gi`까지 재실측을 마쳤다. 남은 일은 이 값을 기반으로 local direct monitor도 같은 수준으로 복구하는 것이다.  
  📁 `.agent/shared-brain/device_inventory.json`, `.agent/knowledge/20260406_Project_Device_Resource_Distribution_Report_v1.md`, `.agent/knowledge/20260406_Device_Assignment_Plan_v1.md`  
  🤖 Codex

- [ ] **Linux server monitor 직결 경로 복구**  
  📌 tailnet은 이미 살아 있고 `tailscale ping ysh-server`는 성공한다. 하지만 이 제어 노드에서 `ssh ysh@100.67.221.25`와 `tailscale ssh ysh@ysh-server`는 여전히 비대화형 실행에서 timeout 된다. 점프 호스트 기준 live 스펙과 실험 상태는 확인 가능하지만, `PAPER/monitor_experiments.py`의 직결 live fetch는 아직 unavailable이다.  
  📁 `PAPER/monitor_experiments.py`, `%USERPROFILE%\\.ssh\\config`, `%USERPROFILE%\\.ssh\\id_ed25519_ysh`  
  🤖 Codex

## 🔵 Normal (여유 있을 때)

- [ ] **소라 PC Agent 설치** — home-pc → sora-pc-agent systemd  
  📍 `scripts/install_pc_agent.sh`  
  👤 Claude Code

- [ ] **2dlivegame P0 블로커 5건** — 서버/IAP/가챠 확률 미구현  
  📍 `D:\00.test\2dlivegame`  
  👤 보류

- [ ] **deploy 스크립트 자동화** — `deploy-linux-server.sh` 미생성  
  📍 neo-genesis `scripts/`  
  👤 Claude Code

---

## ✅ Recently Completed

- [x] **Sora 텔레그램 방문자 보고를 PM/DA 형식으로 교체** — 일일 `evening_report()`와 주간 `weekly_digest()`가 이제 `Executive Summary → Business Signal → Intent Analysis → Quality Diagnosis → Measurement Integrity → Action Queue` 구조의 방문자 보고를 보낸다. `traffic_pmda_report`는 `report_gate`에서 HTML 본문을 그대로 전달하도록 분기 추가.  
  📍 `src/core/proactive_agent.py`, `src/core/notifications/traffic_pmda_report.py`, `src/core/governance/report_gate.py`, `scripts/traffic_alert.py`, `.agent/shared-brain/handoff.md`  
  👤 Codex
- [x] GA4 shared-property reporting 기준 내재화 + 자동 보고 스크립트 일괄 정리 (`NeoGenesis - Production`, `hostName` 필터, Windows 콘솔 ASCII alert 출력) — 4/9, Codex
- [x] EthicaAI Melting Pot sharding support 추가 + Linux server tail shard launch + Mac overlap guard 설정 — 4/6, Codex
- [x] EthicaAI 모니터 false stall 판정 수정 + paper-update scaffold 구축 — 4/6, Codex
- [x] WhyLab Docker E5 appendix TODO 제거 + 실결과 반영/compile check — 4/6, Codex
- [x] PAPER monitor resilient fallback 추가 (`live/cached/unavailable`, SSH port probe, last-good cache) — 4/7, Codex
- [x] PAPER monitor root-cause isolation + repair assets 준비 (`tailscale ping`, `ssh_diag`, 포트 가변 credential parsing, `server_enable_monitoring_sshd.sh`) — 4/7, Codex

- [x] 퀀트봇 버그 4건 수정 (Ghost Position, -4045, Health, Supabase 키) — 4/5, Claude Code
- [x] Gemini LLM 트레이더 영구 삭제 — 4/5, Claude Code
- [x] 소라 God Mode Phase 1-3 완료 — 4/5, Claude Code
- [x] ComfyUI 이미지 생성 체인 구축 — 4/5, Claude Code
- [x] NEO_MASTER_RULES.md v1.0 작성 — 4/5, Claude Code
- [x] NeurIPS 자가 감사 — 4/5, Antigravity
- [x] Shared Brain 시스템 구축 — 4/6, Antigravity
- [ ] **퀀트봇 VM cutover + runtime lease 활성화**  
  - `auto-trading/src/scripts/setup-runtime-coordination.sql`를 Supabase에 적용하고 VM `.env`에 `RUNTIME_COORDINATION_REQUIRED=true` 설정 필요  
  - 이후 primary를 PC가 아니라 VM 하나로 고정하고 dashboard를 `quant_runtime_leases` 기준 heartbeat로 개편  
  - 경로: `neo-genesis/auto-trading/docs/RESILIENCE-v8.4-pc-down.md`, `neo-genesis/auto-trading/src/core/runtime-coordinator.js`  
  - 담당: Codex / Claude Code
---

## Codex Rollout Update (2026-04-06 22:25)

- Completed: `DESKTOP-SOL01`, `YSH-Server`, `MX Mac Studio`
- Applied:
  - shared runtime bundle copied to remote runtime path
  - home-level `CLAUDE.md`, `GEMINI.md`, `Codex AGENTS.md` pointers installed
- Pending: `DESKTOP-YESOL`, `S26 Ultra`, `Tab S10 Ultra`
- Blockers:
  - `DESKTOP-YESOL`: no `SSH`, `WinRM`, or `PC Agent`
  - `S26 Ultra`, `Tab S10 Ultra`: no remote shell / automation channel
- [x] **퀀트봇 VM baseline cutover 완료**
  - 전용 VM `quant-bot` 생성, Supabase runtime lease SQL 적용, 원격 배포/PM2/systemd 구성 완료
  - 현재 VM은 `asia-northeast3-a`, `e2-medium`, host maintenance `MIGRATE`, automatic restart 활성화 상태
  - 경로: `neo-genesis/auto-trading/docs/RESILIENCE-v8.4-pc-down.md`, `neo-genesis/auto-trading/src/core/runtime-coordinator.js`
  - 담당: Codex

- [x] **퀀트봇 Binance API 화이트리스트 반영 후 재기동 완료**
  - 신규 VM 공인 IP `34.50.8.236` 반영 후 원격 `quant-bot-live` 재기동 성공
  - 현재 PM2 `online`, runtime lease 획득, exchange init/Private WS/오케스트레이터 루프 시작 확인
  - 담당: 사용자 + Codex

- [ ] **퀀트봇 Telegram 채널 실패 원인 점검**
  - 원격 로그: `Telegram 봇 실행 실패: ... getMe failed`
  - 거래 코어는 동작하지만 원격 제어/알림 채널은 불안정할 수 있음
  - 담당: Codex

- [ ] **퀀트봇 grid margin insufficient 튜닝**
  - 원격 로그: `GRID-MGR ... -2019 Margin is insufficient`
  - 그리드 일부 주문이 자금 제약으로 거절되고 있어 배치 수량/레벨 재조정 필요
  - 담당: Codex / Claude Code

## Codex Rollout Update (2026-04-07 00:12)

- `DESKTOP-YESOL`: user-reported installed, OpenSSH enabled, host `100.71.28.36`, user `CTS_Sol`
- `DESKTOP-YESOL`: direct Codex login verification still pending because current SSH auth from this machine failed
- `S26 Ultra`, `Tab S10 Ultra`: remain in mobile operator mode, not remote shell targets
- Fleet rollout status:
  - `DESKTOP-SOL01`, `YSH-Server`, `MX Mac Studio`: verified installed
  - `DESKTOP-YESOL`: user-reported installed, auth verification pending
  - `S26 Ultra`, `Tab S10 Ultra`: network-online operator devices

## Codex Rollout Update (2026-04-07 00:22)

- `DESKTOP-YESOL`: direct Codex SSH verification completed
- Verified on host `100.71.28.36` as user `CTS_Sol`
- Verified files:
  - `C:\Users\CTS_Sol\.claude\CLAUDE.md`
  - `C:\Users\CTS_Sol\.gemini\GEMINI.md`
  - `C:\Users\CTS_Sol\.codex\AGENTS.md`
  - `C:\Users\CTS_Sol\neo-genesis-runtime\AGENTS.md`
  - `C:\Users\CTS_Sol\neo-genesis-runtime\infra\agent-runtime\LIVE_STATUS.md`
- Fleet rollout status:
  - `DESKTOP-SOL01`, `DESKTOP-YESOL`, `YSH-Server`, `MX Mac Studio`: verified installed
  - `S26 Ultra`, `Tab S10 Ultra`: network-online operator devices

## Codex Fleet Status Tracking (2026-04-07 11:15)

- [x] Added central device inventory and heartbeat ledger
  - `.agent/shared-brain/device_inventory.json`
  - `.agent/shared-brain/device_heartbeats.json`
- [x] Added rollout/status manager
  - `scripts/fleet_runtime_manager.py`
  - `infra/agent-runtime/runtime_heartbeat.py`
- [x] Updated Windows and Unix rollout installers to refresh runtime adapters and heartbeat support
- [x] Re-synced and verified `DESKTOP-SOL01`, `DESKTOP-YESOL`, `MX Mac Studio`
- [ ] Recover `YSH-Server` SSH path from this control node
  - current state: `ssh ysh@100.67.221.25` timeout
- [ ] Bring `Tab S10 Ultra` back online in Tailscale operator mode when needed

## Codex Remote Access Update (2026-04-08 12:05)

- [x] **`desktop-sol01` 관리자 SSH 키 마감 + 키 기반 접속 검증 완료**
  - `desktop-sol01`의 `C:\\ProgramData\\ssh\\administrators_authorized_keys`에 `desktop-yesol` 운영 키를 반영하고 `sshd` 재시작 완료
  - `desktop-yesol`에서 `ssh -i %USERPROFILE%\\.ssh\\id_ed25519_ysh -o IdentitiesOnly=yes yesol@desktop-sol01 hostname` 검증 성공
  - 현재 운영 표준은 `ssh desktop-sol01`
  - 담당: 사용자 + Codex

- [x] **`desktop-yesol` 운영 점프 호스트 기준 원격 접근 표준 고정**
  - `ysh-server`: `ssh ysh-server`
  - fallback: `tailscale ssh ysh@ysh-server`
  - `desktop-sol01`: `ssh desktop-sol01`
  - 운영 메모는 `.agent/shared-brain/handoff.md`에 반영 완료
  - 담당: 사용자 + Codex

- [x] **비모바일 4대 runtime 재수렴 완료**
  - `desktop-sol01`, `desktop-yesol`, `ysh-server`, `mx-macbuild-mac-studio` 모두 `verified_installed`
  - 현재 canonical runtime revision: `1c848a59e10557fb`
  - 담당: Codex

## Codex Experiment Follow-up (2026-04-07 12:04)

- [ ] **YSH-Server EthicaAI tail shard 재기동**
  - 원인확인 완료: `last reboot` 기준 `2026-04-07 11:00` 리붓이 `server_tail.log`의 `context canceled` 시각과 일치
  - 현재 상태: 서버에는 `meltingpot_final.py` 프로세스가 없고 tail shard는 부팅 후 자동 복구되지 않음
  - 재개 지점: `meltingpot_final_results_server_tail.json`의 기존 완료분을 유지한 채 shard resume 필요
  - 담당: Codex

- [ ] **YSH-Server Melting Pot 감시/복구 설계 보강**
  - 현재 `monitor_meltingpot_final.sh`는 재시작 스크립트가 아니라 종료 감시 + 텔레그램 알림만 수행
  - 현재 crontab에는 Melting Pot 재기동 엔트리가 없고, reboot 후 자동 복구 경로가 없음
  - 추가 이슈: 감시 스크립트가 `running`이 아니면 모두 `completed`로 알리므로 reboot/crash도 완료로 오탐 가능
  - 담당: Codex

## Codex Experiment Recovery (2026-04-07 12:28)

- [x] **YSH-Server EthicaAI tail shard 재기동**
  - `/home/ysh/neurips2026/EthicaAI/NeurIPS2026_final_submission/code/scripts/server_launch_meltingpot_tail.sh` 배포 완료
  - `meltingpot_tail.env` + `@reboot` crontab 등록 완료
  - 재기동 직후 상태: `completed_pairs=4/26`, `new_state=running`
  - 담당: Codex

- [x] **모니터 live 경로 복구**
  - `PAPER/monitor_experiments.py`에 `ProxyJump(CTS_Sol@100.71.28.36)` fallback 추가
  - 2026-04-07 12:28 KST 기준 `monitor_status=live`, `probe_pid=49863`, `cpu_tick_delta_5s=4741` 확인
  - 담당: Codex

- [ ] **YSH-Server Telegram 완료 알림 스크립트 정정**
  - 기존 `/home/ysh/neurips2026/monitor_meltingpot_final.sh`는 reboot/crash도 `completed`로 오탐 가능
  - 현재 auto-recovery는 해결됐지만 알림 문구/조건 보정은 별도 후속 작업
  - 담당: Codex

## Codex Quant Monitoring (2026-04-07 12:34)

- [x] **퀀트봇 모니터링 SSOT 복구**
  - `quant_dashboard.runtime` 컬럼 실적용 완료
  - VM `quant-bot` 재배포 후 `quant_dashboard.updated_at`와 `runtime.heartbeatAt`가 60초 주기로 갱신되는 것 확인
  - 담당: Codex

- [x] **공개 Quant 대시보드 런타임 표시 반영**
  - `portfolio/public/resume/projects/quant.html`이 JSON string/JSONB 혼합 응답과 `runtime` 필드를 모두 처리하도록 수정
  - `portfolio` commit `7f11448` push 완료
  - 담당: Codex
## Codex Quant Fee Edge (2026-04-07 17:20)

- [x] **퀀트봇 fee-adjusted execution policy 배포**
  - `src/core/trade-edge-policy.js` 추가, `config.js` 전략별 leverage cap / TP-SL / fee buffer 정책 반영, `v6-live-runner.js` 실주문 직전 skip + leverage override 연결
  - `quant-bot` VM에 최소 파일 배포 후 lease TTL 경과 뒤 `pm2 restart quant-bot-live --update-env`로 정상 기동 복구
  - 담당: Codex

- [ ] **퀀트봇 24~48h 수수료 효율 관측**
  - 새 정책 배포는 완료됐지만 아직 `edge ->` / `skip:` 실거래 로그 표본이 부족함
  - 다음 점검 때 `commission / realized pnl / net income` 기준으로 pre/post 비교 필요
  - 담당: Codex

## Codex Paper Claim Audit (2026-04-07 18:05)

- [x] **Claude 협업구조 기반 논문 점검**
  - `claude_collab.py --mode review`로 EthicaAI/WhyLab 원고 리스크를 재검토했고, EthicaAI Melting Pot overclaim이 현재 가장 큰 blocker라는 결론을 재확인했다.
  - `claude_collab.py --mode architecture`로 8.0+ 기준 실행 순서를 재검토했고, 결과 대기 전에는 claim calibration과 branch-ready rewrite를 먼저 끝내는 것이 최적이라는 결론을 반영했다.
  - 담당: Codex

- [x] **EthicaAI Melting Pot claim audit / branch rewrite 초안 준비**
  - `PAPER/EthicaAI/NeurIPS2026_final_submission/paper/MELTINGPOT_CLAIM_AUDIT.md`
  - `PAPER/EthicaAI/NeurIPS2026_final_submission/paper/MELTINGPOT_BRANCH_REWRITE.md`
  - 현재 `clean_up`은 merged result 전까지 `flagship positive result`가 아니라 `boundary-condition check`로만 취급한다.
  - 담당: Codex

- [x] **WhyLab 8.0+ framing note 준비**
  - `PAPER/WhyLab/paper/WHYLAB_8PLUS_NOTES.md`
  - E5 Docker 결과는 gain claim이 아니라 `transparent inactivity`와 `proxy calibration` 중심으로 해석하도록 고정했다.
  - 담당: Codex

- [ ] **EthicaAI merged result 반영**
  - Melting Pot head/tail 완료 후 `merge_meltingpot_results.py` 실행
  - `integrate_meltingpot_results.py` 결과로 본문/appendix/abstract/conclusion 문구를 동시 교체
  - 담당: Codex

- [x] **EthicaAI finalization 경로 준비**
  - `PAPER/EthicaAI/NeurIPS2026_final_submission/code/scripts/finalize_meltingpot_results.py` 추가
  - 현재 상태에서 `--allow-partial --sync-only`로 Mac `21`, server `13` 결과 스냅샷 fetch 성공
  - 기본 실행은 shard 미완료 시 `Melting Pot shards are not complete yet`로 안전 차단됨
  - 담당: Codex

- [x] **Stable acceptance plan 수립 + 선제 claim calibration**
  - `PAPER/STABLE_ACCEPTANCE_PLAN.md` 추가
  - EthicaAI `unified_paper.tex`의 Melting Pot overclaim을 mixed-safe wording으로 낮춤
  - WhyLab `main.tex`의 우선성/효과 과장을 보수적으로 조정
  - `pdflatex` 1회 빌드 기준 두 원고 모두 컴파일 성공
  - 담당: Codex

- [ ] **WhyLab 안정권 보강 실험/서술**
  - 현재 null-result framing만으로는 significance가 약하므로, 가능하면 unstable slice 추가 증거나 rebuttal-ready discussion 강화가 필요
  - 담당: Codex / Claude Code

## Codex Quant Runtime Review (2026-04-08 10:45)

- [x] **Capital tier + shadow telemetry hardening**
  - Runtime profile now carries shadow promotion candidates, tier transition state, and skip-audit telemetry for owner-facing monitoring.
  - Owner can inspect why signals were skipped and which shadow symbols are ready for manual promotion review.
  - Owner: Codex

- [x] **Claude re-review after implementation**
  - `claude_collab.py --mode review` and `--mode architecture` were re-run on the patched workspace.
  - Claude judged the prior blockers mostly resolved and converged on one next high-value step: wire SmartTrend trailing/partial TP into the real execution path.
  - Owner: Codex / Claude Code

- [x] **SmartTrend trailing / partial TP execution wiring**
  - Live path now uses exchange STOP protection plus bot-managed partial TP / trailing ratchet with tier-aware partial gating, remaining-amount sync, rollback handling, and emergency-close retry control.
  - Claude final reviewer result after hardening: `NO_NEW_SIGNAL`.
  - Owner: Codex

- [ ] **Managed-exit VM rollout decision**
  - Local code and tests are complete, but VM/live deployment has not been executed in this round.
  - Next owner decision: deploy the managed-exit hardening to `quant-bot` VM now, or hold for another data review window.
  - Owner: Codex / Owner

- [x] **Master orchestrator runtime hardening**
  - Fixed the undefined `balResp` branch, removed the bad `this.exchange` timeout-close reference, normalized recovered live-position metadata, and clamped orchestrator confidence to `0..100`.
  - Added `test/orchestrator-confidence.test.js`; Claude re-review result was `NO_NEW_SIGNAL`.
  - Owner: Codex

- [ ] **ExecutionPlanner real-path integration decision**
  - The orchestrator runtime is now stable, but `ExecutionPlanner` still remains a design-only module rather than the live execution path.
  - Next decision: keep the current direct `futuresExecutor` path, or promote `ExecutionPlanner` into the real signal-to-order pipeline as a separate structural refactor.
  - Owner: Codex / Owner

- [x] **Shadow promotion threshold hardening**
  - `capital-tier-router.js` default gate raised to `20 trades / 60% win rate / 3% pnlPct`
  - Promotion status now distinguishes `collecting_data`, `below_edge_threshold`, and `under_observation`
  - Backward-compatible aliases remain in place so runtime/dashboard consumers do not break immediately
  - Claude final re-review result on this patch: `NO_NEW_SIGNAL`
  - Owner: Codex / Claude Code

- [ ] **Quant latest local changes VM rollout decision**
  - Managed-exit hardening, orchestrator runtime fixes, and shadow promotion threshold tightening are all local-only right now
  - Next owner decision: deploy this combined patch set to `quant-bot` VM now, or hold for another local review window
  - Owner: Codex / Owner

- [x] **Quant dashboard telemetry exposure**
  - `scripts/update_quant_dashboard.js` now writes `skip_audit` and `shadow_candidates` into the static fallback JSON
  - `portfolio/public/resume/projects/quant.html` now renders `Skip Audit (24h)` and `Shadow Promotion Watch`
  - Claude architect chose this over immediate VM rollout as the next safest high-value step
  - Owner: Codex / Claude Code

- [ ] **Quant telemetry live-population rollout**
  - UI and mirror path are ready, but current runtime payload on the VM does not yet populate the new telemetry fields with live values
  - Next owner decision: roll out the latest quant runtime patch set to `quant-bot` VM, then observe 24-48h of skip/promotion data before larger structural changes
  - Owner: Codex / Owner

- [x] **Managed-exit VM rollout**
  - Latest runtime patch set was synced to `quant-bot` VM and `npm ci --omit=dev` completed successfully
  - First restart failed on a stale runtime lease; PM2 was stopped and the stuck `quant_runtime_leases` row was manually cleared after process-state verification
  - Second start succeeded; current instance `quant-bot:42859:25439af1` is online and publishing runtime telemetry
  - Owner: Codex

- [x] **Quant latest local changes VM rollout**
  - Managed-exit hardening, orchestrator fixes, shadow promotion thresholds, and telemetry-oriented runtime payload changes are now live on the VM
  - PM2 state was re-saved after rollout
  - Owner: Codex

- [x] **Quant telemetry live-population rollout**
  - `quant_runtime_leases` and `quant_dashboard.runtime` now contain live `skipAudit`, `runtimeProfile`, and shadow promotion threshold data
  - Static fallback JSON mirror was refreshed after the successful rollout
  - Owner: Codex

- [x] **Quant portfolio public telemetry deployment**
  - Staged only `public/quant/data.json`, `public/resume/projects/quant-data.json`, and `public/resume/projects/quant.html` in `D:\00.test\portfolio`
  - Committed as `1061dec feat: expose quant runtime telemetry`, pushed to `Yesol-Pilot/portfolio main`, then published `dist` with `npm run deploy`
  - Live verification passed: `https://heoyesol.kr/resume/projects/quant.html` now exposes `Skip Audit (24h)` and `Shadow Promotion Watch`
  - Owner: Codex

- [ ] **Quant 24-48h telemetry observation**
  - Rollout is complete, but current `skipAudit.total` and shadow candidate trade counts are still near zero because only the first live cycles have elapsed
  - Next step: observe 24-48h for real skip reasons, `collecting_data -> below_edge_threshold / under_observation` transitions, and any stale-lease recurrence on restart
  - Owner: Codex / Owner

## Codex Paper 8.5 Push (2026-04-08 10:58)

- [x] **WhyLab 8.5 route audit from existing results**
  - Added `PAPER/WhyLab/experiments/analyze_85_path.py`
  - Generated `PAPER/WhyLab/experiments/results/why85_path.json`
  - Generated `PAPER/WhyLab/paper/WHYLAB_85_EXECUTION.md`
  - Conclusion: fixed C2 is not 8.5-ready; the only remaining high-value path is a targeted real-task comparison on the E9 baseline-fail slice (`baseline vs fixed C2 vs adaptive C2`)
  - Owner: Codex

- [x] **EthicaAI residual paper blocker removal**
  - Updated `PAPER/EthicaAI/NeurIPS2026_final_submission/paper/unified_paper.tex` to replace stale `3 seeds` table wording with `pilot rerun` / `clean_up (pilot)`
  - Verified `pdflatex` build success and `python PAPER/monitor_experiments.py` now reports `Paper blockers: none`
  - Owner: Codex

- [x] **WhyLab selective adaptive real-task follow-up completed**
  - Added `PAPER/WhyLab/experiments/e9_swebench_selective.py` and `PAPER/WhyLab/experiments/launch_e9_selective_background.ps1`
  - Added runbooks / result notes:
    - `PAPER/WhyLab/paper/WHYLAB_85_SELECTIVE_RUNBOOK.md`
    - `PAPER/WhyLab/paper/WHYLAB_85_SELECTIVE_RESULT.md`
  - Ran the full top-cell selective follow-up on `E9 baseline-fail slice` (`T=0.7`, `max_attempts=3`, `n=92`)
  - Result: `adaptive C2` showed no net gain over `fixed C2` on pass / oscillation / regression; only mean rejection count decreased
  - Current implication: WhyLab `8.5` route is closed on the current model/policy; keep WhyLab on the stable-accept track unless a materially different setup is approved
  - Owner: Codex

- [x] **WhyLab manuscript recalibrated to match the selective follow-up**
  - Updated `PAPER/WhyLab/paper/main.tex` to state that adaptive C2 helps in `E7v2` but does not beat fixed C2 on the targeted SWE-bench slice
  - Added the selective-result caveat to the abstract, E7v2 discussion, cross-environment analysis, conclusion, limitations, and future-work sections
  - Reframed the paper-level message around `phase-aware deployment` / `selective intervention`, not universal gain
  - Hardened figure/table captions to make the same message readable without relying on body text
  - Added `PAPER/WhyLab/paper/WHYLAB_REBUTTAL_READY.md` for reviewer-facing defense points
  - Added `PAPER/WhyLab/paper/WHYLAB_REBUTTAL_DRAFT.md` with reviewer 1/2/3/4/5 expected comments and answer drafts
  - Verified with `pdflatex -interaction=nonstopmode -halt-on-error main.tex` five times
  - Final git state captured on branch `codex/whylab-final-state` at commit `88fa509`
  - Owner: Codex

- [ ] **WhyLab detailed remediation execution**
  - Fresh Codex + Claude Opus review consensus says the remaining blockers are significance framing, adaptive-C2 demotion, deployment-rule operationalization, theory-practice quantification, and baseline/robustness evidence surfacing
  - Detailed plan captured in `PAPER/WhyLab/paper/WHYLAB_DETAILED_REMEDIATION_PLAN.md`
  - Immediate no-new-experiment path:
    - patch abstract / intro / E7v2 / E5 / cross-env / conclusion / limitations to remove residual overclaim
    - add an experiment map table and a deployment checklist subsection
    - surface `E10` simple baselines and permutation E-value evidence in the main text
  - Low-cost analysis path:
    - quantify `(A1)` violation rate from E6 traces
    - pull a concise Docker per-tier calibration summary
    - improve figure readability where the caption currently carries more signal than the plot
  - Owner: Codex

- [x] **Quant market/news-aware control-plane P0**
  - Added `src/core/market-context.js` and `src/core/event-risk-gate.js`
  - Orchestrator confidence now consumes soft market/news caution modifiers, while `v6-live-runner.js` applies hard event/news shock entry blocks and size/confidence reductions right before execution
  - Shadow execution now also respects the same hard block logic so promotion stats stay aligned with live gating
  - Local validation passed with `27 suites / 232 tests`; Claude re-review returned `NO_NEW_SIGNAL`
  - Owner: Codex / Claude Code

- [ ] **Quant market/news gate VM rollout decision**
  - The market/news-aware gate is local-only right now; the VM runtime still runs the previous live patch set
  - Next owner decision: deploy this control-plane patch to `quant-bot` VM and observe 24-48h of `marketContext` / `event_risk` skips before tuning thresholds further
  - Owner: Codex / Owner

- [ ] **WhyLab 8.0 feasibility gate**
  - `Claude Opus` plus Codex consensus: `8.0` is not feasible with the current evidence bundle
  - Current governing note is `PAPER/WhyLab/paper/WHYLAB_80_FEASIBILITY_PLAN.md`
  - Decision rule:
    - default path = `stable accept` via manuscript/analysis hardening
    - `8.0` path only reopens if one new real-task experiment produces a statistically defensible positive gain
  - Explicit no-go:
    - do not treat same-family adaptive reruns, more E5 Docker expansion, or writing polish alone as an `8.0` route
  - Owner: Codex

- [ ] **WhyLab 8.0 conditional action-plan execution**
  - Owner requested an explicit `8.0-targeted` roadmap rather than only a feasibility verdict
  - Governing docs:
    - `PAPER/WhyLab/paper/WHYLAB_80_FEASIBILITY_PLAN.md`
    - `PAPER/WhyLab/paper/WHYLAB_80_ACTION_PLAN.md`
  - Execution rule:
    - Phase 0 = manuscript hardening
    - Phase 1 = low-cost analyses from existing assets
    - Phase 2 = exactly one decisive real-task experiment only if the route is materially different from the exhausted adaptive path
  - Stop/go rule:
    - if Phase 2 does not yield a statistically defensible real-task gain, the 8.0 route closes and the paper returns to the stable-accept track
  - Owner: Codex

- [ ] **WhyLab 8.0 action-plan Phase 1 analyses**
  - Phase 0 manuscript hardening is complete in `PAPER/WhyLab/paper/main.tex`
  - Added:
    - deployment checklist subsection
    - experiment map table
    - E10 simple-baseline comparison table
  - Reframed:
    - `E7v2` significance as pairwise-positive / 3-way-underpowered
    - `adaptive C2` as scoped calibration
    - `E5` as stable-regime calibration sanity check
  - Next step is Phase 1:
    - quantify `(A1)` violation rate from E6 traces
    - summarize Docker per-tier calibration
    - clean up any figure/readability issues that remain after the manuscript patch
  - Owner: Codex

- [ ] **WhyLab 8.0 reopen follow-up: Gemini 2.5 Flash Docker confirmatory run**
  - Direct Claude reviewer pass confirmed that 8.0 cannot reopen without a new Docker-ground-truth positive result on a materially different setup.
  - Locked protocol:
    - `PAPER/WhyLab/paper/WHYLAB_80_REOPEN_PROTOCOL.md`
    - materially different setup = `gemini-2.5-flash` + Docker ground-truth + existing 67-problem prefilter + `baseline` vs `whylab_c2`
  - Infra validation:
    - `/home/ysh/whylab_docker_g25_smoke` completed one `baseline` and one `whylab_c2` episode successfully under Docker
    - `whylab_c2` recorded real audit rejections, so the code path is live
  - Active full run:
    - host: `YSH-Server`
    - workdir: `/home/ysh/whylab_docker_g25_full`
    - launch time: `2026-04-08 16:19:29 KST`
    - scope: `67 problems x 3 seeds x 2 conditions = 402 episodes`
  - Stop/go rule:
    - if this run is null or ambiguous, close the 8.0 route and return WhyLab to the stable-accept track
    - if this run is positive and defensible, rerun cold Claude review before touching the paper narrative
  - Owner: Codex

- [x] **Quant market/news gate VM rollout**
  - The live `quant-bot` VM now runs the market/news-aware control-plane patch set.
  - Rolled files:
    - `src/config.js`
    - `src/orchestrator.js`
    - `src/v6-live-runner.js`
    - `src/core/market-context.js`
    - `src/core/event-risk-gate.js`
  - Validation:
    - remote `node --check` passed on all touched runtime files
    - `pm2 restart quant-bot-live --update-env` recovered successfully after one stale-lease retry
    - current live instance recovered as `quant-bot:44219:a2f6676b`
    - live logs confirm `Lease acquired`, `small-account safe mode`, `capital tier=micro`, and 60-second loop start
  - Owner: Codex

- [ ] **Quant market/news telemetry observation window**
  - The structural rollout is complete; the next step is to observe real live behavior for `24-48h`
  - Watch items:
    - actual `marketContext` / `event_risk` skip accumulation
    - whether the live news snapshot meaningfully changes gating versus the previous neutral fallback
    - recurring stale-lease churn during PM2 restarts
    - intermittent Telegram `getMe` failure during startup
    - partial upstream feed failure (`bls_cpi fetch failed`) on the VM
  - Tuning should happen only after live skip data accumulates
  - Owner: Codex

- [x] **EthicaAI final mirror sync across all three GitHub targets**
  - Final submission branch: `codex/ethicaai-final-submission` at `b4d5a90`
  - Reflected targets:
    - `Yesol-Pilot/EthicaAI`
    - `neogenesislab/EthicaAI-NeurIPS2026`
    - `openreview-neurlps/EthicaAI`
  - Credential resolution:
    - `GITHUB_TOKEN`, `GITHUB_PAT` in `neo-genesis/.env` authenticate as `neogenesislab`
    - `OPENREVIEW_GITHUB_PAT` in `neo-genesis/.env` authenticates as `openreview-neurlps`
  - Local prep:
    - `PAPER/EthicaAI_anon2` is synced to `codex/ethicaai-final-submission` (`b4d5a90`)
  - Owner: Codex

- [ ] **Quant live news updater hardening**
  - `market-news-updater` is now online under PM2 and persisted with `pm2 save`
  - Current live path:
    - `fed_press` and `coindesk` succeeded
    - `bls_cpi` failed on the VM during the first live run
  - Next step:
    - determine whether `bls_cpi` is a transient TLS/network issue or a persistent source incompatibility on the VM
    - if persistent, either adjust the fetch path or demote/remove that source from the default live set
  - Owner: Codex

- [x] **Quant runtime governor P0: Claude-gated design + implementation + review closure**
  - Scope delivered:
    - live-order-time enforcement for `runtimeProfile.liveUniverse` / `liveStrategies`
    - grid/funding teardown with tracked-symbol cleanup when tier or guardrails disallow them
    - fee-budget gate that freezes new entries when fee drag dominates realized pnl
  - Claude checkpoints:
    - design: `ccr-20260410-113847`
    - review fixes: `ccr-20260410-115442`, `ccr-20260410-120255`
    - final closure: `ccr-20260410-120847 = NO_NEW_SIGNAL`
  - Validation:
    - `npm test -- --runInBand` passed (`30 suites / 242 tests`)
  - Owner: Codex

- [x] **Quant runtime governor P1: profile drift audit**
  - Scope delivered:
    - live-signal drift is derived from existing `skipAudit.runtime_profile` events instead of double-recorded
    - manager drift is recorded immediately before runtime teardown
    - active and recovered position drift are recorded from `positionRegistry.dump()`
    - merged drift telemetry is exposed through `runtime.meta.profileDrift` and static dashboard mirror JSON
  - Claude checkpoints:
    - design: `ccr-20260410-124835`
    - review: `ccr-20260410-125631`
    - final closure: `ccr-20260410-125939 = NO_NEW_SIGNAL`
  - Validation:
    - `npm test -- --runInBand` passed (`31 suites / 247 tests`)
  - Owner: Codex

- [x] **Quant runtime governor P2: live rollout and dashboard UI exposure**
  - Runtime-governor + profile-drift patch set is now live on the `quant-bot` VM.
  - Validation:
    - live lease recovered as `quant-bot:79149:fecdd911`
    - Supabase `runtime.meta.profileDrift` is populated
    - fallback JSON mirror refreshed
    - public `quant.html` renders `Profile Drift (24h)`
    - `heoyesol.kr/quant/data.json` exposes the live runtime and drift summary
    - portfolio telemetry exposure committed as `f34f972` on `Yesol-Pilot/portfolio` `main`
  - Residual note:
    - current `profileDrift` rows are `exchange_bootstrap` recovery noise for the recovered ETH/SOL positions, not a live policy-violation drift
  - Claude checkpoint:
    - `ccr-20260410-132616`
  - Owner: Codex

- [x] **EthicaAI 8.5 reopen: external evidence package**
  - Goal:
    - test whether stronger non-PGG / externally grounded evidence can honestly reopen the score ceiling above the current `7.5~8.0` range
  - Completed package:
    - local `desktop-sol01` GPU:
      - completed `run_coin_game_deep.py --seeds 40 --seed-start 0 --episodes 200`
      - output saved successfully despite a trailing `cp949` console-print error after JSON write
    - `mx-macbuild-mac-studio`:
      - completed `seed 40..79`, `80..119`, and `120..159` shards
    - `ysh-server`:
      - completed `fishery_nash_trap.py --seeds 300 --seed-start 0 --episodes 300`
      - fixed missing dependency by installing `gymnasium` into `/home/ysh/neurips2026/EthicaAI/.venv`
    - `desktop-yesol`:
      - staged a minimal fishery execution tree and verified smoke execution, but this lane was not used as a trusted background worker
  - Final evidence summary:
    - merged adapted Coin Game result (`160` seeds total): selfish survival `22.08%` vs `MACCL 78.10%`, delta `+56.02` points, bootstrap CI95 `[54.31, 57.73]`, Cohen's `d=7.15`
    - fishery rerun (`300` seeds): `phi1=0.7` reaches `87.7%` survival with positive harvest welfare, while `phi1=1.0` reaches `100.0%` survival only at the zero-harvest limit
  - Paper integration:
    - updated `PAPER/EthicaAI/NeurIPS2026_final_submission/paper/unified_paper.tex`
    - updated `PAPER/EthicaAI/NeurIPS2026_final_submission/paper/tables/tab_coin_game_deep.tex`
    - rebuilt `paper/unified_paper.pdf` successfully
  - Cold reassessment:
    - fresh Claude review now judges `8.0 stable` as defensible
    - `8.5` remains blocked because positive results still rely on author-imposed or author-specified tipping-point environments; native third-party TPSD replication is still missing
  - Owner: Codex

- [ ] **Paper 1-month recovery execution**
  - Scope:
    - `PAPER/PAPER_1MONTH_RECOVERY_PLAN.md`
    - `EthicaAI` + `WhyLab`
  - Operating rules:
    - maintain separate `submission-freeze` and `research-next` states for each paper
    - do not accept paper score claims unless manuscript state, result files, and shared-brain are aligned
    - prohibit repeated micro-reruns without preregistered stop/go criteria
  - Current priority split:
    - `EthicaAI`: primary score-upside track, centered on decisive external/native validation and strict claim calibration
    - `WhyLab`: stabilization track, centered on honest significance framing and stable-accept readiness
  - Progress update (`2026-04-14 15:02`):
    - `EthicaAI`: unsupported appendix evidence (`extended escape`, `power analysis`, `Allee validation`) removed from live manuscript; PDF rebuild passed
    - `WhyLab`: unsupported `GPT-4o Docker` claims removed; Gemini 2.5 Docker / A1 / Pareto-backed changes retained; PDF rebuild passed
  - Progress update (`2026-04-14 15:08`):
    - freeze anchors re-verified unchanged (`EthicaAI=b4d5a90`, `WhyLab=88fa509`)
    - `EthicaAI` live run gate re-verified: keep only server-side `Melting Pot n80` expansion open
    - both per-paper `SUBMISSION_FREEZE_STATE.md` files refreshed with latest build times and current keep/drop decisions
    - added explicit live-delta guardrail doc: `PAPER/PAPER_DELTA_KEEP_DROP_20260414.md`
  - Progress update (`2026-04-14 15:31`):
    - corrected the live `EthicaAI` n80 progress source from stale head artifacts to the actual active output `meltingpot_n80_newseeds.json`
    - current checked state is `1 / 54`, not `26 / 56`
    - patched `finalize_when_ready.py` and `poll_and_finalize.ps1` to derive completion from the active file's `config` instead of hardcoding `56`
    - switched default finalization transport to `ysh@ysh-server` because this node does not currently have a working `ssh ysh-server` alias
  - Progress update (`2026-04-14 16:08`):
    - patched `meltingpot_final.py` for explicit device auto-selection (`cuda > mps > cpu`) plus env-driven smoke overrides
    - brought up local WSL GPU runtime at `/root/mp311_env` with `torch 2.6.0+cu124`, `meltingpot`, and `dm_env`
    - direct local smoke/mini-benchmarks show no current GPU advantage for this script:
      - tiny smoke: `cuda ~19s` vs `cpu ~16s`
      - medium smoke: `cuda ~29s` vs `cpu ~27s`
    - current conclusion: the live `Melting Pot` implementation is environment-step bound, so GPU is not yet a proven acceleration path
  - Progress update (`2026-04-14 17:05`):
    - replaced the slow monolithic `ysh-server` `n80` container with two shard containers:
      - `meltingpot_n80_left` -> `seed-indices 53-65`, output `meltingpot_n80_newseeds.json`
      - `meltingpot_n80_right` -> `seed-indices 66-79`, output `meltingpot_n80_right.json`
    - server allocation: `6 CPU / 6 GB / 6 threads` per shard on the `16c / 16 GB` host
    - backed up the active `meltingpot_n80_newseeds.json` before restart
    - verified both shard logs are live:
      - left shard resumed from the saved checkpoint and is running `seed_idx=53, floor=0.2`
      - right shard started at `seed_idx=66, floor=0.0`
    - patched finalization scripts for multi-shard completion/merge tracking so the next close event will not miscount stale n80 artifacts
  - Immediate next actions:
    - keep both `EthicaAI` `n80` shards running and wait for the first write into `meltingpot_n80_right.json`
    - revise ETA after the first right-shard save confirms the new per-pair runtime
    - finish classifying the remaining `EthicaAI` live delta after the server-side `Melting Pot n80` shards close
    - decide by end of Week 2 whether WhyLab gets one materially different decisive experiment or exits the 8.0 chase completely
  - Owner: Codex

- [ ] **Paper multi-agent command execution**
  - Scope:
    - `PAPER/PAPER_MULTI_AGENT_COMMAND_SYSTEM_20260415.md`
    - `EthicaAI` + `WhyLab`
  - Command structure:
    - `Codex`: single orchestrator and final integrator
    - `Galileo`: EthicaAI finalization worker
    - `Singer`: EthicaAI manuscript reviewer
    - `Beauvoir`: WhyLab snapshot hardener
    - `Bacon`: paper strategy meta reviewer
  - Guardrails:
    - specialists only edit declared write scopes
    - no paper-state conclusion is accepted until result files, manuscript impact, freeze/research state, and shared-brain are aligned
    - WhyLab remains in manuscript-hardening mode unless Codex explicitly opens one materially different preregistered experiment
  - Progress update (`2026-04-15`):
    - multi-agent paper command system document created
    - `Bacon` returned first-pass score-lever guidance:
      - `EthicaAI`: decisive native validation + theory/claim calibration remain the main score levers
      - `WhyLab`: strongest honest snapshot freeze and appendix-to-main evidence promotion remain the main score levers
    - `Singer` returned EthicaAI findings-first manuscript risk memo:
      - main risk remains overstating Melting Pot as validation rather than boundary-consistent evidence
      - manuscript should separate `author-designed`, `adapted external`, `ecological model`, and `native third-party boundary` evidence classes more explicitly
    - `Beauvoir` hardened WhyLab snapshot:
      - `paper/main.tex` wording lowered toward null-consistent, inactive-as-predicted framing
      - `WhyLab/SUBMISSION_FREEZE_STATE.md` refreshed
      - `paper/main.pdf` rebuilt successfully
    - `Galileo` completed first-pass EthicaAI finalize work:
      - shard-aware local merge/stat generation succeeded
      - current blocker is remote reconciliation showing `114/130`, i.e. `16` missing pairs
      - next subtask is deciding whether the missing `16` pairs are true unfinished remote results or stale-target contamination
    - independent reconciliation audit concluded `stale contamination`:
      - active target set is `meltingpot_n80_newseeds.json + meltingpot_n80_right.json`
      - stale `server_head*` / `expansion` files are inflating the count to `114/130`
      - active-run reality is `54/54`; finalize counting must now be restricted to the active shard files
    - EthicaAI finalize path is now aligned with the active target set:
      - `finalize_n80.py` reads only the active shard files for n80 merge inputs
      - `finalize_when_ready.py` and `poll_and_finalize.ps1` count only the active shard pair set
      - next step is freeze integration, not more target reconciliation
    - anon submission gate is now aligned:
      - `EthicaAI_anon` and `EthicaAI_anon2` are both clean and aligned to the `b4d5a90` freeze anchor
      - `WhyLab_anon` is clean on `codex/whylab-anon-clean` at `cac4ef8`
      - anonymous metadata and packaging paths were scrubbed from `WhyLab_anon`
    - next subtask:
      - completed specialist re-review on anon-ready snapshots
      - completed Claude review on the same snapshots
      - final current judgment:
        - `EthicaAI_anon2` -> `borderline accept`, submit-capable
        - `WhyLab_anon` -> `reject-side borderline`, honest but not stable-accept
      - remaining decision:
        - whether to submit `WhyLab_anon` as-is or spend more time on an additional strategic improvement path
  - Owner: Codex

- [ ] **Paper stable-accept blueprint execution**
  - Scope:
    - `PAPER/PAPER_STABLE_ACCEPT_BLUEPRINT_20260415.md`
    - `EthicaAI_anon2`
    - `WhyLab_anon`
  - Goal:
    - maximize acceptance probability over the next month with explicit stop/go rules
    - `EthicaAI`: attack track toward stable `8.0`
    - `WhyLab`: honest rescue track with one decisive experiment gate
  - Week 1 required deliverables:
    - `EthicaAI`: native third-party shortlist, pilot triage prereg, claim/provenance patch list
    - `WhyLab`: baseline-only screening rule, decisive experiment prereg, comparator audit
  - Hard rules:
    - `EthicaAI`: no more `clean_up` extension, no more adapted Coin Game/fishery seed inflation, no new custom env
    - `WhyLab`: no more stable-regime Docker, no same-family adaptive reruns, no wording-only score chase
    - if `EthicaAI` fails to find a positive native substrate within 7 days, end the stable `8.0` chase
    - if `WhyLab` cannot beat `simple_retry` in the decisive route, end the `8.0` chase
  - Owner: Codex

- [x] **Responsibility-agent Week 1 artifact lock**
  - Scope:
    - `PAPER/ops/ethicaai_validation/ETHICAAI_VALIDATION_LEAD_CHARTER_20260415.md`
    - `PAPER/ops/ethicaai_claims/ETHICAAI_CLAIM_CALIBRATOR_CHARTER_20260415.md`
    - `PAPER/ops/whylab_realtask/WHYLAB_REALTASK_LEAD_CHARTER_20260415.md`
    - `PAPER/ops/whylab_audit/WHYLAB_BASELINE_AUDITOR_CHARTER_20260415.md`
    - `PAPER/ops/portfolio_pm/PORTFOLIO_PM_CHARTER_20260415.md`
    - `PAPER/ops/infra_scheduler/INFRA_SCHEDULER_CHARTER_20260415.md`
    - `PAPER/ops/submission_gatekeeper/SUBMISSION_GATEKEEPER_CHARTER_20260415.md`
  - Current status:
    - all responsibility leads created charters and named sub-researchers
    - all Week-1 artifact files are now created
    - no paper text was edited and no new experiments were launched in this artifact-lock phase
  - Owner: Codex

- [ ] **Week 1 artifact integration and Week 2 authorization**
  - Scope:
    - `PAPER/PAPER_MULTI_AGENT_COMMAND_SYSTEM_20260415.md`
    - `PAPER/PAPER_STABLE_ACCEPT_BLUEPRINT_20260415.md`
    - `PAPER/ops/`
  - Required decisions:
    - `EthicaAI`
      - verify installed untouched native substrates against shortlist
      - approve or reject triage launch
      - approve claim/provenance patch order
    - `WhyLab`
      - approve baseline-only screening rule
      - approve decisive experiment prereg
      - lock forbidden claims into manuscript-integration constraints
    - `Global`
      - confirm host assignment and watchdog readiness
      - confirm final review gate order
  - Hard rule:
    - no Week-2 launch until Codex signs off on the integrated artifact set
  - Owner: Codex

- [x] **Paper freeze/ref separation**
  - `EthicaAI`
    - freeze ref: `submission-freeze/ethicaai-20260414` -> `b4d5a90`
    - research ref: `research-next/ethicaai-20260414`
  - `WhyLab`
    - freeze ref: `submission-freeze/whylab-20260414` -> `88fa509`
    - research ref: `research-next/whylab-20260414`
  - State docs added:
    - `PAPER/EthicaAI/SUBMISSION_FREEZE_STATE.md`
    - `PAPER/WhyLab/SUBMISSION_FREEZE_STATE.md`
  - Owner: Codex

## Quant Bot v11 Ensemble Design (2026-04-22, Claude Code Opus 4.7 1M)

- [x] **v11 마스터 설계 문서화 완료** — 6 병렬 전문가 교차검증 (수학·HFT/MM·Stat Arb·리스크·ML/RL·이벤트알파) 수렴된 6-알파 앙상블 아키텍처
  📍 `D:/00.test/neo-genesis/auto-trading/docs/v11-ensemble/`
    - `INDEX.md` (진입점)
    - `MASTER_DESIGN.md`
    - `ROADMAP.md`
    - `RISK_KILLSWITCH.md` (7 Layer 방어)
    - `CURRENT_CODE_AUDIT.md` (유지/삭제/신규)
    - `alpha-specs/` (A1~A6 6개 알파 스펙)
    - `expert-reports/` (6명 전문가 보고서 원본)
  👤 Claude Code

- [x] **레거시 산출물 archive 격리 완료** — 판타지 백테스트 12개 + 구 설계문서 5개
  📍 `archive/backtest-fantasy/`, `archive/design-docs-legacy/`, `archive/README-legacy/`
  📍 `archive/README.md` (설명서)
  👤 Claude Code

- [x] **v11 Phase -1 실행 완료 (지혈 + 관측복구 + VM PAPER 전환)** — 2026-04-24, Claude Opus 4.7
  📍 `auto-trading/docs/v11-ensemble/phase-gate--1.md`, `incidents/2026-04-24-01-*.md`, `weekly-review-2026-W17.md`
  완료:
    - Task -1.2 Supabase 마이그레이션 apply (프로젝트 `zdfvfisfcocttrfsznwd`, lease 5/5·ledger 6/6·인덱스 6/6·신규 2종 live)
    - Task -1.3 Critical 버그 7건 ✅ + Task -1.4 MAE/MFE 경로 복구 ✅ + Task -1.5 레거시 agent/engine gating ✅
    - Task -1.6 VM PAPER 전환 ✅ — ecosystem.config.js `launch-testnet.js` 전환, PM2 env 캐시 purge, Supabase lease PAPER 고정, Binance wallet=$0, positions=0, PID 349737 uptime 안정
    - Task -1.8 단위 테스트 3종 46개 신규 + 기존 35 suites / 304 tests 전체 녹색
    - Task -1.9 문서화 (phase-gate--1.md 갱신, incidents/ 디렉토리 + 첫 기록, weekly-review 작성)
  발견/해소한 Critical Incident:
    - `launch-live.js` land mine (hardcoded `config.tradingMode='LIVE'` + `testnet=false` + PM2 env 캐시 `CONFIRM_LIVE/SKIP_GATE`)
    - 2층 구조 해소: 진입점 교체 + PM2 delete/start/save + fail-closed PAPER safeguard + 중복 라인 제거 + VM 배포 `exit 2` 검증 완료
  관측 창 (passive, 다음 세션 확인):
    - Phase -1 통과 게이트 #2 MAE/MFE 비-0 — 첫 페이퍼 거래 발생 대기
    - Phase -1 통과 게이트 #5 24h 연속 운영 에러 없음 — 관측 창 진행 중
  👤 Claude Code Opus 4.7

- [ ] **v11 Phase -1 closure + 외부 교차검증 반영 단일 commit + PR** — 사용자 승인 시 일괄 묶음
  📍 브랜치 `v11/phase-minus-1`
  범위:
    - `auto-trading/ecosystem.config.js` (launch-testnet.js 전환)
    - `auto-trading/src/scripts/launch-live.js` (fail-closed PAPER safeguard)
    - `auto-trading/docs/v11-ensemble/phase-gate--1.md`
    - `auto-trading/docs/v11-ensemble/incidents/2026-04-24-01-*.md`
    - `auto-trading/docs/v11-ensemble/weekly-review-2026-W17.md`
    - `auto-trading/docs/v11-ensemble/research/2026-04-24-external-validation.md` (신규)
    - `auto-trading/docs/v11-ensemble/backtest-v2-engine-decision.md` (신규)
    - `auto-trading/docs/v11-ensemble/RISK_KILLSWITCH.md` (9-Layer 확장)
    - `auto-trading/docs/v11-ensemble/MASTER_DESIGN.md` (알파별 외부 경고 인라인)
    - `auto-trading/docs/v11-ensemble/ROADMAP.md` (Phase 0 Task 0.3-0.5 재작성)
    - `auto-trading/docs/v11-ensemble/INDEX.md` (research/ + backtest-v2-engine-decision 링크)
  👤 사용자 승인 후 Claude Code

- [x] **v11 Phase 0 외부 교차검증 리서치 완료 (2026-04-24)** — 5축 병렬 리서치 + 설계 수정 반영
  📍 `auto-trading/docs/v11-ensemble/research/2026-04-24-external-validation.md`
  결과:
    - A1/A2/A5 공개 벤치마크 부재 공식화 (팀 과소평가 항목)
    - Kill Switch 3대 공백 발견 (Order Rate Cap / Stablecoin Depeg / ADL Queue Rank)
    - Backtest v2 엔진 = nautilus_trader primary + hftbacktest (A1/A6) + vectorbt pro (검증) 결정
    - A3 임계 상향 (`|F| > 0.08%`) / A5 capacity guard (`30일 median funding < 0.007% → zero-alloc`)
    - 순수 OU mean reversion post-2022 사멸 증거 → A2 A1-동조 게이트 필수
  반영 문서:
    - RISK_KILLSWITCH.md 7-Layer → 9-Layer (L8 Stablecoin Depeg, L9 Funding Spike 추가)
    - backtest-v2-engine-decision.md 신규 (Phase 0 스캐폴드 구체화 + 127k/0 버그 8대 안티패턴 CI guard)
    - MASTER_DESIGN.md 알파별 외부 경고 인라인
    - ROADMAP.md Phase 0 Task 0.3-0.5 재작성
  👤 Claude Code Opus 4.7

- [ ] **v11 Phase 0 Task 0.5 Kill Switch 9-Layer 구현 (P0, Phase 0 첫 주)**
  📍 `auto-trading/src/core/` + `auto-trading/test/killswitch/`
  대상:
    - `order-rate-governor.js` 신규 (L1 보강, Knight 교훈)
    - `correlation-killer.js` 신규 (L3, 임계값 `-2%/1min OR -5%/5min OR -10%/15min`)
    - `stablecoin-depeg-guard.js` 신규 (L8, USDT/USDC/USDe 3-tier)
    - HALT 실행 순서 강제 (cancel-all → verify → close → persist → block)
    - 다주기 MaxDD (일 -5% / 주 -12% / 월 -20%)
    - 4개 과거 crash tick (2020-03-13 / 2022-05-12 LUNA / 2022-11-08 FTX / 2025-10-10 Hyperliquid) stress test asset 확보
  🎯 완료 기준:
    - 단위 테스트 + 4개 tick 재생 최소 1개 이상 탐지
    - False positive HALT < 1% (페이퍼 7일 관측)
  👤 Claude Code

- [ ] **v11 Phase 0 Task 0.3 Backtest v2 스캐폴드 (P0, Phase 0 둘째 주)**
  📍 `auto-trading/src/backtest/v2/`
  대상:
    - `engine/nautilus_adapter.py` — Primary engine (nautilus_trader 기반)
    - `data/tardis_loader.py` — tick + L2 + funding + forceOrder 로더
    - `fill_models/conservative.py` — bar-crossing 완전 삭제, tick-touch 기반
    - `universe/as_of.py` — survivorship-safe universe
    - `validation/deflated_sharpe.py` + `validation/pbo.py`
    - `test/backtest/antipattern-guard.test.js` — 8대 안티패턴 CI 차단
  🎯 완료 기준:
    - 현 v6 SmartTrend "127k 승 / 0 패" 가 v2 에서 40-60% 승률로 붕괴 (공식 비교 리포트)
    - DSR < 0 시 CI 실패
  🚫 보류 (Phase 1):
    - `hftbacktest` 통합 (A1/A6 구현 시점)
    - `queue_aware` fill model
    - `forceorder_replay.py` (A1 전용)
  👤 Claude Code

- [x] **v11 Phase 0 Task 0.1 Liquidation Stream 이중 구독 + dedup** ✅ (2026-04-27, Claude Opus 4.7)
  📍 `auto-trading/src/core/liquidation-stream.js` (modified, +200/-26)
  📍 `auto-trading/test/liquidation-stream.test.js` (extended, +151)
  외부 근거: [research/2026-04-24-external-validation.md](../../auto-trading/docs/v11-ensemble/research/2026-04-24-external-validation.md) §1
  완료:
    - `!forceOrder@arr` (글로벌) + 심볼별 `<symbol>@forceOrder` (BTC/ETH/SOL) combined stream 이중 구독
    - `buildStreamUrl(symbols)` static helper + `wss://fstream.binance.com/stream?streams=...` URL 생성
    - combined stream wrapper `{ stream, data }` unwrap 처리 + 직접 event backward-compat 유지
    - cryptofeed `_check_update_id` 패턴 차용 (`_lastSeenMs` 심볼별 + `gapThresholdMs=5min` 초과 시 reconnect)
    - dedup key `symbol|side|eventTimeMs|quantity` 로 양쪽 stream 동일 이벤트 1회만 처리 검증 (test 추가)
    - `getRecentClusters(symbol, windowMs)` rolling window API 추가 (A1 알파 인터페이스)
    - `_recentClusters` Map + `_gcRecentClusters()` GC + binary-search lookup
    - `completenessMultiplier=1.4` stats 기록 (Binance truncation 헤어컷)
    - 신규 stats: `gapReconnects`, `clusterSizes`, `symbols`, `completenessMultiplier`
  검증:
    - 신규 17개 test 추가 (`buildStreamUrl` 4 + `combined stream` 4 + `getRecentClusters` 5 + `_gcRecentClusters` 1 + `getStats` 보강 + 기존 12 회귀)
    - jest 29/29 PASS (liquidation-stream.test.js)
  👤 Claude Code Opus 4.7

- [x] **v11 Phase 0 A1 Liquidation Cascade 알파 로직 구현 + 라이브 wiring** ✅ (2026-04-27, Claude Opus 4.7)
  📍 `auto-trading/src/agents/liquidation-hunter-agent.js` (new → BaseAgent 호환 refactor, 320 lines)
  📍 `auto-trading/src/core/liquidation-store.js` (new, 165 lines — Supabase read-only 어댑터)
  📍 `auto-trading/src/orchestrator.js` (modified — A1 의존성 주입 + prefetch + activate)
  📍 `auto-trading/src/v6-live-runner.js` (modified — LiquidationStore 초기화 + Orchestrator 주입)
  📍 `auto-trading/test/liquidation-hunter-agent.test.js` (new + 어댑터/ATR/volumeZ 추가, 32 tests)
  📍 `auto-trading/test/liquidation-store.test.js` (new, 14 tests)
  외부 근거: [research/2026-04-24-external-validation.md](../../auto-trading/docs/v11-ensemble/research/2026-04-24-external-validation.md) §1, [alpha-specs/A1_*.md](../../auto-trading/docs/v11-ensemble/alpha-specs/)

  ### 진입 4조건 (Curupira 2단 필터)
  - notional 5min 합계 ≥ threshold (BTC $20M / ETH $10M / others $5M)
  - longLiqRatio ≥ 0.75 (롱 청산 집중) 또는 ≤ 0.25 (숏 청산 집중)
  - 현재가가 청산 클러스터 WAP ±0.5% 이내 (sweep 확인)
  - volumeZ1m ≥ 3.0 (1분 거래량 Z, Curupira volume 확증)

  ### 방향 (역추세)
  - SELL heavy (롱 청산) → LONG
  - BUY heavy (숏 청산) → SHORT

  ### 신호 페이로드 (BaseAgent 호환)
  - `{ action: 'LONG'|'SHORT'|'WAIT', confidence(0-100), tp, sl, timeout:30min, trailingActivate:0.004, trailingOffset:-0.002, meta }`
  - **ATR 기반 동적 TP/SL** — `tp = clamp(0.6×ATR%, [0.005, 0.015])`, `sl = clamp(0.3×ATR%, [0.0025, 0.0075])`
    - ATR 계산 실패 시 fallback `tp=0.008 / sl=0.004`
    - `meta.tpSource = 'atr' | 'fallback'` 진단 노출

  ### Wiring 구조 (라이브 실행 경로)
  ```
  PM2 liquidation-stream  →  Supabase quant_liquidation_events  ←──┐
  (이중구독 + Binance WS)              ▲                          │
                                       │ insert                    │ select (cache 30s)
                                       │                           │
  v6-live-runner  →  LiquidationStore (sync getRecentClustersSync) │
                            ↓                                      │
                     Orchestrator (prefetch + activate)            │
                            ↓                                      │
                     LiquidationHunterAgent ──→ rawSignals → RiskGovernor
  ```
  - LiquidationStore: 30s TTL 캐시 + in-flight dedup + graceful fallback (Supabase 에러 시 stale/empty)
  - Orchestrator: `evaluateAll()` 시작 시 `await prefetch(universe)` → A1 sync 조회
  - Orchestrator constructor: `liquidationStream` 옵션 누락 시 A1 disabled (graceful)

  ### V11_DEPRECATED_AGENTS_DISABLED=true 환경 (기본)
  - `agents.meanRevert` (A2 일부) + `agents.liquidationHunter` (A1) 활성
  - 시장편향 패널티(`marketBiasPenalty`)는 의도적으로 우회되지 않음 — A1 이 BEAR + LONG 일 때 0.2× 받지만 confidence 가 충분히 높으면 RiskGovernor 통과

  ### 검증
  - syntax: 6 파일 (3 src + 3 test) ALL_OK
  - jest liquidation-hunter-agent.test.js: **32/32 PASS** (constructor 4 + _evaluateContext null 9 + signal 6 + scoreConfidence 4 + thresholds 5 + evaluate(marketData) 6 + _resolveTpSl 5 + _computeVolumeZ 3)
  - jest liquidation-store.test.js: **14/14 PASS** (constructor 2 + getRecentClusters 4 + cache 4 + degradation 2 + sync 2)
  - jest liquidation-stream.test.js: **29/29 PASS** (회귀 없음)
  - 전체 jest: **440/466 PASS** (이전 408 → +32 신규, 17 실패는 모두 사전 존재한 unrelated test)

  ### 잔여 (별도 owner-gate task)
  - VM 배포 (`pm2 restart liquidation-stream` + `pm2 restart quant-bot-live` + Phase Gate Monitor 검증) — owner approval
  - commit/push/PR — owner approval
  - cross-exchange completeness multiplier 정밀화 (Phase 1 별도)
  👤 Claude Code Opus 4.7

- [ ] **v11 Phase 0 페이퍼 데이터 스키마에 "A1 firing 여부" 컬럼 추가**
  📍 Supabase `quant_trade_ledger`
  목적: A2/A5 가중치 재정의 게이트의 공식 근거 생성
    - `a1_firing_at_entry BOOLEAN` — 진입 시점 A1 이 active 였는지
    - `a1_firing_recent_24h BOOLEAN` — 최근 24h 내 A1 이벤트 발생했는지
    - `primary_alpha TEXT` — 어떤 알파가 이 trade 의 primary 신호였는지
  🎯 활용: A2 를 A1-동조 vs A1-독립으로 분리해 Sharpe 계측 (재정의 게이트)
  👤 Claude Code

- [ ] **v11 Oct 10-11 2025 Hyperliquid $19B 캐스케이드 tick 데이터 확보**
  📍 `auto-trading/data/stress/2025-10-10-hyperliquid/`
  목적: backtest v2 stress scenario 기본 자산 박제
    - Binance Futures BTC/ETH 2025-10-10 ~ 2025-10-11 48h tick
    - 소스: Tardis.dev flat file 또는 Amberdata
    - Correlation killer 재보정 (`-2%/1min OR -5%/5min OR -10%/15min`) 의 검증 데이터
  🎯 활용: Phase 0 phase-gate-0 체크리스트 "4개 crash tick stress test" 의 1개
  👤 Claude Code + 사용자 (데이터 구매 승인)

- [ ] **v11 Phase 0 페이퍼 후 A2/A5 가중치 공식 재정의 (재정의 게이트)**
  📍 `MASTER_DESIGN.md` §3 자본 배분 + alpha-specs/A2_*.md + alpha-specs/A5_*.md
  트리거: Phase 0 페이퍼 모드 2-4주 데이터 수집 완료
  재정의 대상:
    - A2 25% → "A1-동조 비율 × α + A1-독립 비율 × β" 조건부 구조. A1-독립 Sharpe < 0.3 이면 β = 0
    - A5 15% → "aggregated 30일 median funding > 0.007%/8h 일 때만 활성, 그 외 0" capacity 게이트
    - A3 진입 임계 `|F| > 0.08%` 로 상향
  근거: [research/2026-04-24-external-validation.md](../../auto-trading/docs/v11-ensemble/research/2026-04-24-external-validation.md) §3 §4
  👤 Claude Code (페이퍼 데이터 확보 후)

- [ ] **v11 Phase 0 인프라 대수술 (통합)** — Phase -1 완료 후, 위 개별 subtask 로 분해됨
  상위 체크리스트 역할만. 개별 실행은 위 Task 0.1 / 0.3 / 0.5 / 페이퍼 스키마 / tick 데이터 / 가중치 재정의 태스크를 참조
  🎯 전체 완료 기준:
    - Backtest v2로 BTC 2년 재실행시 현실 샤프 (0.5~1.5)
    - Liquidation stream 일 100+ 이벤트 수집
    - 9 Kill Switch 단위테스트 통과 (L8/L9 포함)
  👤 Claude Code

- [ ] **v11 핵심 합의사항 (6전문가 공통)**
  - 일 1% 지속 기관 0건 (Medallion의 58배 속도)
  - 현실 목표: 일 0.6~1.0% (6-알파 앙상블)
  - 레버리지 상한 5x (Kelly/3, 무제한 요청에도)
  - 365일 파산확률 5x=32%, 20x=98%, 50x=100%
  - 백테스트 tick-level 재작성 필수
  - 페이퍼 2주 알파별 + 30일 통합 전 라이브 금지

- [x] **실거래 근본 원인 확정 (5일 -$9.48 drain)**
  - Grid ping-pong 인벤토리 장부 누락 (주범)
  - MAE/MFE 전 거래 0 기록 (진단 불능)
  - SmartTrend 76건 40.8% WR = 통계적 무의미
  - 백테스트 127k승 0패 = fill 로직 버그
  - 리스크 거버너 1x 전제에 가변 레버리지 모순
