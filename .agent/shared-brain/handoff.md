# Handoff: Claude Code 세션 (2026-04-10 최종, UI/UX 미완 명시)

> **작성자:** Claude Opus 4.6
> **세션 유형:** 전체 Phase 상세설계 + Phase 0~4 구현 + 프론트엔드 완성 + 브라우저 E2E 검증 + Docker v6.3 재빌드

---

## 2026-04-27 RAG Phase 0 라이브 가동 + 디바이스 분산 (Claude Opus 4.7)

**세션 유형**: Owner 지시 "체크" 후 자율 진행 → 의존성 설치 + 인프라 가동 + sol01 몰빵 → 디바이스 분산 재배치

### Phase 0 라이브 가동 — PASS 9 / FAIL 0 / WARN 0 / SKIP 1

| 디바이스 | 역할 | 가속 | endpoint |
| --- | --- | --- | --- |
| **ysh-server** (Linux 16C / 16GB) | Qdrant 1.16 + mcp_gateway 7701 | CPU | http://ysh-server:6333, http://ysh-server:7701 |
| **desktop-sol01** (Win, RTX 4070 SUPER 12GB) | KURE-v1 임베딩 7702 | **CPU mode** (torch CUDA 빌드 부재) | http://localhost:7702 |
| **mac-studio** (macOS, M2 Max 32GB) | BGE Reranker v2-m3 7704 | **MPS True** ✅ | http://100.81.93.118:7704 |
| **Supabase** (sora 프로젝트) | RAG audit/eval/lineage/forgotten/allowlist/jwt_revoke 6 테이블 | — | RLS owner-only |
| **etribe-yesol** (Win work PC) | (예약) BM25 / watchdog Phase 1 | — | host key 정리 필요 |
| **yesol-asus** | (예약) 보조 Phase 1 | — | SSH key 미등록 |

### 가동한 인프라 commands
```bash
# desktop-sol01 (현 PC)
pip install --no-cache-dir qdrant-client blake3 watchdog kiwipiepy
pip install --no-cache-dir sentence-transformers FlagEmbedding pynvml
PYTHONPATH=D:/00.test/neo-genesis nohup python scripts/rag_v2/embedding_service.py --port 7702 > logs/embedding_service.log &

# ysh-server (Tailscale 100.67.221.25)
ssh ysh-server "docker run -d --name qdrant-rag-v2 --restart unless-stopped -p 6333:6333 -p 6334:6334 -v /home/ysh/qdrant_data:/qdrant/storage qdrant/qdrant:v1.16.0"
ssh ysh-server "python3 -m venv ~/rag-v2-runtime/.venv && ~/rag-v2-runtime/.venv/bin/pip install fastapi uvicorn pydantic pyyaml qdrant-client blake3 httpx requests watchdog PyJWT supabase"
# JWT_SECRET 32-byte hex (~/rag-v2-runtime/.env.gateway, mode 600)
ssh ysh-server "cd ~/rag-v2-runtime && ./start-gateway.sh"  # PID 3462842, port 7701

# mac-studio (Tailscale 100.81.93.118)
ssh macstudio "python3 -m venv ~/rag-v2-runtime/.venv && ~/rag-v2-runtime/.venv/bin/pip install fastapi uvicorn pydantic pyyaml httpx PyJWT FlagEmbedding sentence-transformers torch"
ssh macstudio "cd ~/rag-v2-runtime && ./start-rerank.sh"  # PID 49734, port 7704
```

### 분산 의도 (RAG 설계 v1 §06 GPU 충돌 결정 반영)
- 처음에는 sol01 에 embed+rerank 둘 다 띄웠으나 owner 지적: **"인프라좀 나눠서 쓰지 디바이스도 많은데"**
- 분산 정정: rerank 를 mac-studio MPS 로 이전 → sol01 부담 절반 감소
- ysh-server (CPU 16C) + sol01 (12GB GPU, 현재 CPU mode) + mac-studio (M2 Max MPS) 3-way 분산
- diagnose_phase_0.py 의 service check 가 candidate URL list 순회 (RAG_EMBED_URL / RAG_RERANK_URL env override 지원)

### 운영 메모
- **sol01 torch CPU-only 빌드** — RTX 4070 SUPER 활용 못함, 처리량 ~5x 낮음. 향상 원하면:
  ```
  pip uninstall torch
  pip install torch --index-url https://download.pytorch.org/whl/cu124
  # 후 embedding_service 재기동
  ```
- **mac-studio MPS True** — Apple Silicon GPU 활용 정상. BGE Reranker v2-m3 ~2GB, 32GB RAM 여유 풍부
- mcp_gateway 는 현재 reranker URL 직접 호출 안 함 (Phase 1 통합 예정)

### Phase 1 진입 시 잔여 (owner action)
- desktop-sol01 torch CUDA 빌드 재설치 (선택적 성능 향상)
- desktop-sol01 SSH key 등록 (현재 host name `desktop-home`, 자율 SSH 차단 상태 — 본 세션은 sol01 자체에서 작업)
- etribe-yesol host key 정리 (`ssh-keygen -R etribe-yesol`)
- yesol-asus authorized_keys 등록 → BM25 / watchdog 인덱서 분산 candidate

### Pending verification (다음 세션 입장 시)
- KorMTEB Recall@10 baseline 측정 (golden v2 50 tasks → embedding 7702 → BGE Reranker 7704)
- Supabase `rag_audit_log` 첫 row (mcp_gateway 가 첫 query 받았을 때)
- Qdrant 첫 컬렉션 `neo_ssot` dry-run migration

---

## 2026-04-27 RAG Phase 0 Day 7-B 자율 진척 + Phase 1 사전 강화 (Claude Opus 4.7)

**세션 유형**: Owner 지시 "RAG만 진행해 너가 직접 판단해" — quant 작업으로 잘못 분기했던 것을 정정하고 RAG 본 task 자율 진행.

### 산출물 (8 파일)
| 파일 | 변경 | 비고 |
| --- | --- | --- |
| `.agent/policies/gitleaks-korean-rules.toml` | M (8 → 14 rules) | 주민번호 신버전 / 외국인등록 / 운전면허 / 여권 / 신용카드 / KISA / 공인인증서 / Telegram |
| `src/core/rag_v2/credential_redactor.py` | NEW (240) | runtime PII/credential redactor — 23 patterns (한국어 + 글로벌 cloud) + allowlist + critical 게이트 |
| `src/core/rag_v2/pdf_sanitizer.py` | NEW (200) | PDF prompt injection sanitizer — 13 rules + unicode normalize (zero-width 제거) + risk score + quarantine |
| `tests/test_rag_v2_redactors.py` | NEW (190) | 26 tests PASS (credential 14 + injection 12) |
| `tests/rag_golden/ssot_korean_v2.json` | NEW (50 tasks) | v1 supersede, 카테고리 5분 (rag_v2/quant/ssot/security/ops), 신규 metric `credential_leak_rate` + `injection_quarantine_recall` |
| `scripts/rag_v2/diagnose_phase_0.py` | NEW (500) | 9-section 자동 진단 (deps/tokenizer/qdrant/embedding/reranker/gateway/supabase/ssot/files), JSON + ASCII fallback |
| `.agent/shared-brain/active-tasks.md` | M | RAG Phase 0 Day 7-B 자율 진척 + Phase 1 사전 강화 작업 박제 |
| `.agent/shared-brain/handoff.md` | M | 본 섹션 |

### Supabase MCP 직접 액션
- **Migration apply** (sora 프로젝트 `kfoixzebpztikurwqgdr`): `rag_v2_initial_audit_eval_lineage`
  - 6 테이블 생성: `rag_audit_log`, `rag_eval_runs`, `rag_chunk_lineage`, `forgotten_uris`, `rag_source_allowlist`, `rag_jwt_revoke_list`
  - 14 인덱스 (PK 6 + secondary 8) 모두 활성
  - RLS policy `rag_audit_owner_only` (tenant_id='yesol' OR is_admin) 활성
- **rag_source_allowlist seed**: yaml 정책 → DB 31 row (allow=13 / deny=16 / manual_approval=2)

### 잔존 위험 해소 매트릭스
| 위험 | 상태 | 조치 |
| --- | --- | --- |
| **P0-1**: sora_engine backend 분기 부재 | ✅ Day 3 완료 | 기존 |
| **P0-2**: sol01 12GB VRAM OOM | ⏳ 운영 시 모니터링 | 결정 6 채택 (mac primary + sol01 fallback) |
| **P0-3**: LanceDB right-to-be-forgotten | ⏳ Phase 4 진입 시 | `forgotten_uris` 테이블 활성 (이번 세션) |
| **P1-4**: 한국어 credential 미커버 | ✅ 본 세션 해소 | gitleaks v2 14 rules + runtime redactor 23 patterns + 14 회귀 테스트 |
| **P1-5**: PDF prompt injection | ✅ 본 세션 해소 | 13 injection rules + unicode normalize + quarantine + 12 회귀 테스트 |
| **P1-6**: JWT 발급 경로 | ⏳ Phase 3 yesol 격리 시 구현 | `rag_jwt_revoke_list` 테이블 활성 (이번 세션) |
| **P1-7**: 멀티 에이전트 동시 write | ⏳ watchdog Single-writer lock 적용 (Day 6) | 기존 |
| **P2-8~12**: contextual cost / 16GB / mecab Windows / 1주 비현실 / mac offline | ⏳ owner 환경/시간 의존 | RUNBOOK Day 7-B + diagnose_phase_0.py |

### Owner 다음 액션 (RUNBOOK Day 7-B 의 잔여)
1. `pip install qdrant-client blake3 pydantic fastapi uvicorn pyyaml watchdog requests httpx kiwipiepy` (필수 의존성)
2. `pip install sentence-transformers FlagEmbedding torch pynvml` (sol01 GPU only)
3. ysh-server `docker run qdrant/qdrant:v1.16.0 -p 6333:6333` + API key
4. `python scripts/rag_v2/diagnose_phase_0.py` 실행해서 **한 화면에 모든 게이트 상태 확인** (Windows: `set PYTHONIOENCODING=utf-8` 권고)
5. dry-run 마이그 + sol01 embed/rerank 가동 → Phase 1 진입 결정

### 잘못 분기했던 quant A1 작업 (별도 trace, RAG 와 무관)
- `auto-trading` PR #7 (`3c1d3f1`) + PR #8 (`66020a4`) 둘 다 master merged + VM 배포 완료
- 현 VM 상태: PAPER mode, liquidation-stream 이중구독 가동 (5분 145 row, ~41,760/일 추정)
- owner 가 RAG 본 task 가 아니었음을 지적 → 이후 모든 작업 RAG 로 한정
- quant 작업 자체는 코드 정상, 자본 위험 없음 (PAPER), 별도 owner 결정 시 롤백/유지 선택

### Pending verification (다음 세션)
- owner 가 의존성 설치 후 `diagnose_phase_0.py` 결과 — 모든 critical pass 시 Phase 1 진입 가능
- golden v2 50 tasks 의 실제 retrieval recall@10 측정 (Qdrant + KURE-v1 가동 후)
- `rag_audit_log` 첫 row 도착 (MCP gateway 가동 시)

---

## 2026-04-27 v11 Phase 0 A1 Liquidation Cascade 알파 + 이중구독 + Live Wiring (Claude Opus 4.7)

**세션 유형**: P0 자율 실행 (Strategy Lead) — owner 지시 "모든 후속작업 진행해"

### 산출물 (auto-trading repo, 8 파일)
| 파일 | 변경 | 비고 |
| --- | --- | --- |
| `src/core/liquidation-stream.js` | M (+200/-26) | Binance 이중구독 (`!forceOrder@arr` + `<symbol>@forceOrder`) + dedup + cryptofeed `_check_update_id` 갭 감지 + `getRecentClusters()` rolling window |
| `src/core/liquidation-store.js` | NEW (165) | Supabase read-only 어댑터 (30s TTL 캐시 + in-flight dedup + graceful fallback) |
| `src/agents/liquidation-hunter-agent.js` | NEW (320) | A1 알파, BaseAgent 호환 `evaluate(marketData)` + ATR 기반 동적 TP/SL + fallback |
| `src/orchestrator.js` | M | A1 의존성 주입 + `_a1AsyncStore.prefetch()` + `_activateAgents` |
| `src/v6-live-runner.js` | M | LiquidationStore 초기화 + Orchestrator 주입 |
| `test/liquidation-stream.test.js` | M (+151) | buildStreamUrl 4 + combined stream 4 + getRecentClusters 5 + getStats 보강 |
| `test/liquidation-hunter-agent.test.js` | NEW (380) | 32 tests — null cases + signal + scoreConfidence + adapter + ATR + volumeZ |
| `test/liquidation-store.test.js` | NEW (240) | 14 tests — constructor + 쿼리 + cache + degradation + sync |

### 채택된 설계
- **이중구독 dedup**: 글로벌 + 심볼별 stream 동시 구독, `symbol|side|eventTimeMs|quantity` key 로 한 번만 처리
- **데이터 흐름**: PM2 `liquidation-stream` → Supabase `quant_liquidation_events` → orchestrator 프로세스 LiquidationStore (30s 캐시) → A1 sync 조회
- **ATR 기반 TP/SL**: `tp = clamp(0.6×ATR%, [0.005, 0.015])`, `sl = clamp(0.3×ATR%, [0.0025, 0.0075])`, 실패 시 fallback `0.008/0.004`
- **Graceful degradation**: Supabase 미가용/쿼리 에러 → 빈 배열 → A1 자동 WAIT (시스템 다운 없음)

### 검증
- syntax: 6 src/test 파일 ALL_OK
- jest 신규 3 suite: **75/75 PASS** (29 stream + 32 agent + 14 store)
- 전체 jest: **440/466 PASS** (이전 408 → +32 신규, 17 실패는 모두 사전 존재한 unrelated 3 suite — `mae-mfe-tracking`/`supabase-sync`/`profile-drift-audit`)

### Owner 결정 대기 (G2+ 외부 액션)
1. **commit + push + PR** — 로컬 commit 만 자율 실행, push/PR 은 owner approval
2. **VM 배포** — `pm2 restart quant-bot-live` + `liquidation-stream` 봇 두 PM2 모두 재기동 필요. PAPER mode 라 자본 위험 없음
3. **Phase Gate Monitor 검증** — VM 배포 후 24h 관측 (Phase 0 게이트 #3 = 100/일 임계값)

### 잔여 (Phase 0 후속, 별도 태스크)
- `daily-strategy-briefing` cron 이 A1 신호/거래를 보고서에 포함하도록 메트릭 추가
- Phase 0 게이트 #3 통과 시 A2 wiring 착수
- cross-exchange completeness multiplier 정밀화 (Phase 1+)

### Pending verification (다음 세션 입장 시 확인)
- VM 배포 후 Supabase `quant_liquidation_events` row 수 (24h 누적)
- `quant_runtime_leases.runtime.meta` 에 A1 신호 발생 빈도 reflect 되는지
- `quant_trade_ledger` 에 첫 A1 PAPER 거래 발생 시 `agent='liquidationHunter'` 라벨 검증

---

## 2026-04-26 ~ 2026-04-27 RAG 마스터 설계 v1 (Claude Opus 4.7)

**세션 유형**: 멀티에이전트 설계 — owner 지시 "PC 전체 + 플릿 디바이스 RAG화, 다중 병렬 에이전트로 심층 리서치 + 상세 설계서 작성, 시간 무제한"

### 실행 단계
- **Wave 1** (8 병렬 에이전트, ~1시간):
  - Agent A (Explore): D:/ + C:/Users PC 자산 8 카테고리 인벤토리
  - Agent B (Explore): 6대 디바이스 데이터/접근/tier 매핑
  - Agent C (Explore): Sora ChromaDB 현 상태 + 7대 갭 분석
  - Agent D (general-purpose): OSS RAG 프레임워크 15 + 벡터 DB 14 비교 (2026 기준)
  - Agent E (general-purpose): 임베딩 12 + 리랭커 6 + 검색 전략 10
  - Agent F (general-purpose): 고급 RAG 패턴 18 (Graph/Tree/Late interaction/Agentic) + 코드/논문/멀티모달 특화
  - Agent G (general-purpose): 보안/권한/평가/MCP/거버넌스 + 위협 모델 12개
  - Agent H (general-purpose): 분산 5 옵션 + 동기화 + 모바일 + 24주 롤아웃
- **Wave 2** (병렬 2 에이전트, ~30분):
  - neo-architect: 7 충돌 결정 수렴 + 통합 아키텍처 + 24주 plan 검증
  - neo-reviewer: P0~P2 12 잔존 위험 (cold review)
- **Wave 3**: 마스터 + 부록 9개 작성

### 산출물 (10 파일, 총 ~14,000 단어)
- `D:/00.test/neo-genesis/.agent/knowledge/20260426_RAG_MASTER_DESIGN_v1.md` — 마스터 (인덱스 + Executive Summary + 결정 + 24주 롤아웃 + 의사결정 5개)
- `D:/00.test/neo-genesis/.agent/knowledge/rag-master/00_INDEX.md` — 부록 인덱스
- `01_decisions.md` — 7 결정 + 잔존 위험 12개 + Stop/Go 5개
- `02_architecture.md` — 5-plane 아키텍처 + dataflow + failure modes
- `03_domain_stacks.md` — 4 use case stack + 비용 시나리오 A/B/C
- `04_collection_topology.md` — 6 컬렉션 + payload schema + JWT scope 매트릭스
- `05_provenance.md` — ChunkMetadata Pydantic + decay 룰 + 자동 분류
- `06_governance.md` — rag_governance 10 룰 + work_pc_isolation + 위협 매트릭스 + 한국어 credential 정규식
- `07_eval.md` — 5계층 eval + 한국어 golden 50 + 비용 cap
- `08_rollout_24w.md` — Phase 0~6 주차별 작업 + 의존성 + 검증 게이트
- `09_appendix_schemas.md` — 코드 스키마 + JWT YAML + MCP YAML + Supabase DDL

### 채택된 7 핵심 결정 (요약)
1. ChromaDB 마이그: 점진적 컬렉션 단위 cutover + `rag_search`에 `backend` 파라미터
2. Contextual Retrieval: Phase 6 도입 (>100K chunk), Haiku 4.5 + prompt cache
3. SSOT 그래프: LightRAG (Phase 2) → HippoRAG 2 pilot (Phase 6)
4. yesol 격리: read-only + JWT scope (secret/personal endpoint 비공개 404)
5. Provenance: source_type + decay_factor (human=1.0, llm=0.5) + chain depth
6. GPU 충돌: ColQwen2 → mac-studio MLX, sol01 ColQwen2-2B INT4 fallback
7. 컬렉션: 6개 분리 (`neo_ssot/code/paper/notes/quant/secret`)

### 기술 stack 정리
- VDB: Qdrant 1.16+ + LanceDB + pgvector
- 임베딩: KURE-v1 (한국어) / Voyage-Code-3 (코드) / Voyage-3-large + Cohere v4 (논문) / ColQwen2 MLX (멀티모달)
- 리랭커: BGE Reranker v2-m3 자체 호스팅
- 오케스트레이션: LlamaIndex + 단일 MCP 게이트웨이
- Eval: RAGAS + Promptfoo + 한국어 golden 50 + AgentDojo + PoisonedRAG
- 비용: $15~25/월 (시나리오 B 권장)

### 가장 큰 위험 — neo-reviewer 발견
**`sora_engine.py`의 backend 분기 부재** (P0-1) — Phase 0 시작 전 `rag_search` 도구에 `backend` 파라미터 추가 필수. 그렇지 않으면 Qdrant 마이그 중 Sora가 silent degraded 상태로 운영됨. 이 위험을 Phase 0 Day 3 작업으로 차단함.

### 운영자 의사결정 5개 (다음 세션 응답 필요)
- (a) Phase 0 시작 시점 — **권고: 다음 주 시작 가능** (Day 1~2 작업이 quant v11/EthicaAI/SBU 등 기존 워크로드와 충돌 거의 없음)
- (b) Voyage API vs 전부 self-host — **권고: 시나리오 B 혼합**
- (c) desktop-yesol 격리 강도 — **권고: read-only + JWT scope 제한**
- (d) ColQwen2 mac-studio 의존도 — **권고: on-demand + sol01 fallback**
- (e) Contextual Retrieval 비용 cap — **권고: $50/주**

### SSOT 갱신
- `active-tasks.md`: 새 RAG 도입 section 추가 (P0 Phase 0 Day 1~7 체크리스트 포함)
- `handoff.md`: 본 섹션 (이 항목)
- `cross-agent-review.md`: 갱신 안 함 (Claude 단독 multi-agent 진행, Codex 협업 불필요)
- `daily-log.md`: 갱신 안 함 (handoff에 통합)

### 다음 세션 (Claude / Codex / 누구든) 즉시 액션
1. owner 의사결정 5개 응답 받기
2. 응답 후 Phase 0 Day 1 시작 (Qdrant 컨테이너 + rag_governance.yaml 스캐폴드)
3. SSOT 변경 후 `python scripts/sync_agent_context.py --updated-by claude` 실행 권고 (어댑터 재생성)

### Non-goal (이번 세션에서 명시적으로 제외)
- 실제 Qdrant 컨테이너 띄우기 (Phase 0 Day 1)
- 실제 코드 변경 (sora_engine.py 등)
- 실제 SSH 접근 (디바이스 점검)
- 외부 API 호출 (Voyage/Anthropic/Cohere 사전 비용 측정)

### Pending verification
- (없음 — 설계 단계 종료)

### 토큰 사용
- Wave 1 8 에이전트: ~1.4M 합산 (Claude Opus 4.7 1M-ctx)
- Wave 2 2 에이전트: ~280K 합산
- Wave 3 본 세션 작성: ~75K
- 총 ~1.75M tok 추정 (8개 병렬 에이전트가 컨텍스트 효율 극대화)

---

## 2026-04-27 Phase 0 Day 1~7 로컬 작업 완료 (Claude Opus 4.7)

owner 지시 "너가 판단하고 진행해" 에 따라 의사결정 5개 권고안 채택 후 Phase 0 Day 1~7 로컬 작업 자율 진행.

### 채택된 의사결정
- (a) Phase 0 즉시 시작 / (b) 시나리오 B 혼합 (Voyage API + self-host) / (c) yesol read-only + JWT scope 제한 / (d) ColQwen2 mac-studio primary + sol01 INT4 fallback / (e) Contextual Retrieval $50/주 cap (Phase 6 게이트)

### 작성된 자산 (24 파일)
- 정책 8: `.agent/policies/rag_governance.yaml + rag_source_allowlist.yaml + rag_jwt_scopes.yaml + work_pc_rag_isolation.yaml + rag_provenance_overrides.yaml + rag_eval_baseline.yaml + rag_watchdog.yaml + gitleaks-korean-rules.toml`
- 마이그 1: `.agent/migrations/rag_v2/001_initial.sql` (Supabase: rag_audit_log + rag_eval_runs + rag_chunk_lineage + forgotten_uris + rag_source_allowlist + rag_jwt_revoke_list)
- Python 9: `src/core/rag_v2/{__init__, chunk_metadata, provenance_classifier}.py` + `scripts/rag_v2/{__init__, migrate_chromadb_to_qdrant, embedding_service, rerank_service, check_mecab_ko, watchdog_indexer}.py`
- 테스트 1: `tests/rag_golden/ssot_korean_v1.json` (한국어 SSOT golden 10)
- 코드 수정 1: `src/core/rag_engine.py` `backend` 파라미터 추가 (default=chroma, Qdrant lazy + fallback + provenance decay)
- RUNBOOK 1: `.agent/knowledge/rag-master/RUNBOOK_PHASE_0.md` (owner 실행 가이드)

### 검증 결과
- syntax: 9 Python + 7 YAML + 1 JSON + 1 TOML 모두 통과
- provenance 분류기 회귀: 8/8 PASS (handoff heading + LLM 식별 + tool_log + external_citation 모두 정확)
- import/시그니처: `RAGEngine.search()` backward-compatible 확인
- ssotRevision: `ba30bd8fdf3b22e9` → **`d3473c2c2ae51b98`** bump (sync_agent_context.py 실행)

### 발견된 운영자 환경 사실
- 한국어 토크나이저 4개 (kiwipiepy/konlpy/eunjeon/mecab-python3) **모두 미설치** — Phase 0 Day 5 게이트 차단. P2-10 위험 실현됨. owner `pip install kiwipiepy` 필요.

### Owner 실행 대기 항목 (Day 7-B, RUNBOOK 참조)
1. 의존성 설치 (qdrant-client + blake3 + pydantic + FastAPI + uvicorn + sentence-transformers + FlagEmbedding + kiwipiepy 등)
2. ysh-server Qdrant 1.16+ 컨테이너 + API key
3. Supabase 마이그 apply (`001_initial.sql`)
4. dry-run 마이그 (`migrate_chromadb_to_qdrant.py --dry-run`)
5. sol01 embedding + reranker 서비스 가동
6. fleet 동기화 (sol01 / ysh-server / mac-studio 4대 — yesol는 이미 sync)
7. Phase 0 게이트 검증 → Phase 1 진입 결정

---

## 2026-04-24 운영 전환 — Claude primary, Codex fallback

**결정**: 오너 주력 에이전트를 Codex → **Claude Code**로 전환. Codex는 fallback으로 유지.

**배경**:
- 오너가 세션에서 명시적으로 "앞으로 메인으로 클로드를 쓰고 코덱스는 토큰을 다썼을때만 쓸거야"
- 현 Claude Code 2.1.88 + opus-4-7 1M 컨텍스트 조합이 장시간 리팩터·리뷰·수렴 분석에 가장 적합

**Fallback 트리거 (Codex로 전환하는 조건)**:
1. Claude 토큰 소진 (세션 한도 초과)
2. 24시간 이상 autonomous background 실행이 필요한 장기 작업
3. repo-native shell + apply_patch가 더 경제적인 반복 작업 (예: 대량 파일 batch 편집)
4. Claude 가용성 장애 (API 다운 등)

**Handoff 프로토콜** (Claude → Codex):
1. `handoff.md`에 scoped handoff 기록 (goal, scope, files touched, pending verification, non-goals)
2. Codex는 scope 확인 후 SSOT 경계 준수하며 재개
3. 완료 시 같은 섹션에 상태 entry 추가
4. G2+ 파괴적/외부 액션은 실행자 관계없이 오너 승인 유지

**SSOT 반영 파일** (2026-04-24):
- `.agent/contracts/COLLABORATION_CONTRACT.md` — Core Collaboration Shape + Cross-Review Rule + Fallback Handoff 섹션
- `.agent/knowledge/CLAUDE_COLLABORATION.md` — Objective + Best Collaboration Shape
- `.agent/knowledge/AGENT_RUNTIME_OPTIMIZATION.md` — §2 role table + §4 routing table
- `.agent/knowledge/AGENT_SHARED_MEMORY.md` — §5 role table + §6 change history

---

## 2026-04-24 Agent/UX 심층 리서치 내재화

Claude 4병렬 리서치(R1-R4) → Codex 기존 v2 팩(P0~P6 구현 완료)과 갭 매칭.

**추가된 항목** (6개 파일):
- `research-patterns-v2.md`: LATS, Plan-and-Act, GoalAct/HiPlan, Mem0, A-Mem, Episodic Memory Position, Magentic-One dual-ledger, Mixture-of-Agents
- `ux-product-pattern-library-v2.md`: §3.1 (4 UX 원칙: plan-before-execute, 4-layer status, undo-first approval, 3-level uncertainty + AX + anti-workslop + ambient invocation), §4.1 (OSS 라이브러리 picks: AI Elements, assistant-ui, Streamdown, CodeMirror 6, Shiki-stream, react-xtermjs, cmdk, Tremor, Base UI, Motion v12)
- `framework-scorecard-v2.md`: §1.1 Durable Execution (Temporal+OpenAI SDK, Restate, Dapr Agents, Inngest, Trigger.dev, DSPy, Mirascope)
- `security-governance-threat-model-v2.md`: §5.1 Dynamic/Adaptive Red-Team (Attacker Moves Second 경고)
- `benchmark-eval-registry-v2.md`: AgentHarm (ICLR 2025) + Attacker Moves Second 추가
- `README.md`: Watch List (AX, ARLAS, AgentSociety, AI Scientist-v2, BeeAI, Computer-Use 성숙도)

**플릿 영향**: 해시 bump 1회, 4대 재동기화 1회.

---

## 2026-04-14 운영 메모

- 설계/전략/로드맵 요청은 이제 기본적으로 `멀티에이전트 태스크 보드` 방식으로 처리한다.
- 다음 세션 에이전트는 설계 명령을 받으면 바로 답변 초안부터 쓰지 말고, 먼저 `의도 -> 페르소나 -> 태스크 -> QA 게이트`를 잡아야 한다.
- 관련 기준 문서:
  - `.agent/knowledge/20260414_멀티에이전트_설계_실행_프로토콜_v1.md`
  - `.agent/knowledge/20260414_재방문_사용자_중심_성장전략_v1.md`

- `Sora`의 routine Telegram 방문자 보고는 이제 단순 운영 요약이 아니라 `PM/DA 방문자 보고` 형식으로 보낸다.
- 적용 경로:
  - `src/core/proactive_agent.py`
  - `src/core/notifications/traffic_pmda_report.py`
  - `src/core/governance/report_gate.py`
- 대체 대상:
  - `evening_report()` 일일 텔레그램 루틴
  - `weekly_digest()` 주간 텔레그램 루틴
- 유지 대상:
  - `morning_briefing()` 일정/운영 브리핑
  - anomaly/approval/security 계열 알림
- 보고 포맷은 고정:
  - `Executive Summary`
  - `Business Signal`
  - `Intent Analysis`
  - `Quality Diagnosis`
  - `Measurement Integrity`
  - `Action Queue`
- `traffic_pmda_report`는 `report_gate`에서 AI 재작성 없이 HTML 본문을 그대로 통과시킨다. 이유는 대표님용 PM/DA 보고 포맷을 임의 요약으로 망가뜨리지 않기 위해서다.

## 완료된 것

### 백엔드 (전부 서버 배포 완료, Docker v6.3)
| 모듈 | 파일 | 상태 |
|------|------|------|
| 3-Checkpoint 보안/버그 14건 | 10개 파일 | ✅ 코드 수정 + 배포 |
| Fleet API (4 endpoints) | api_fleet.py | ✅ 17 routes 등록 확인 |
| File API (4 endpoints) | api_files.py | ✅ 등록 |
| Git API (5 endpoints) | api_git.py | ✅ 등록 |
| Terminal WebSocket | terminal.py | ✅ 등록 |
| Search API | unified_search.py | ✅ 등록 |
| 자동화 엔진 | workflow_engine.py | ✅ 배포 |
| 알림 매니저 | alert_manager.py | ✅ 배포 |
| CLI 한도 관리 | cli_quota_manager.py | ✅ 배포 |
| RAG 인덱서 | code_indexer.py | ✅ 배포 |
| LiteLLM 프록시 | litellm_proxy.py | ✅ 배포 |
| 관찰성 | tracer.py | ✅ 배포 |
| 프롬프트 관리 | prompt_registry.py | ✅ 배포 |
| 품질 테스트 | golden_tests.py | ✅ 배포 |
| 플러그인 | plugin_manager.py | ✅ 배포 |
| 백업 스크립트 | sora_backup.py | ✅ 배포 |
| 메트릭 수집기 | collect_metrics.py | ✅ 배포 |

### 프론트엔드 (전부 Vercel 배포 완료)
| 컴포넌트 | 파일 | 브라우저 확인 |
|----------|------|------------|
| Fleet Dashboard | devices/page.tsx | ✅ 6대 디바이스 표시 |
| DeviceCard | DeviceCard.tsx | ✅ 역할 태그, 상태 dot |
| Terminal 탭 | TerminalPanel.tsx | ✅ 4대 버튼 표시 |
| Code 탭 | CodeEditor/FileTree/GitPanel | ✅ UI 렌더링 |
| Chat | chat/page.tsx | ✅ AI 응답 |
| Home | home/page.tsx | ✅ KPI |
| 검색 패널 | SearchPanel.tsx | ✅ settings 스크롤 확인 |
| 알림 설정 | AlertSettings.tsx | ✅ 5개 규칙 + 조용한 시간 |
| 자동화 | AutomationPanel.tsx | ✅ 5/6 활성 |
| 관찰성 | ObservabilityPanel.tsx | ✅ 렌더링 |
| 플러그인 | PluginPanel.tsx | ✅ MCP 등록 구조 표시 |
| 원격 데스크톱 | RemoteDesktop.tsx | ✅ 준비 중 표시 |
| 메트릭 | DeviceMetrics.tsx | ✅ 코드 존재 |
| 설정 | DeviceSettings.tsx | ✅ 코드 존재 |

### 설계 문서 (5건)
- `SORA_MASTER_BLUEPRINT_V2.md` — 전체 Phase 설계
- `SORA_GOD_TIER_VISION_REPORT.md` — 비전 보고서
- `SORA_COMPASS_ANALYSIS.md` — Compass 교차 분석
- `feedback_completion_verification.md` — 완료 검증 룰
- `feedback_docker_deployment.md` — Docker 배포 교훈 7건

---

## 남은 것 (다음 세션)

### 🔴 P0: Antigravity 수준 UI/UX 구현 (다음 세션 최우선)

현재 UI는 "기능이 동작하는 프로토타입"이지 "제품 수준"이 아니다. 오너가 명시적으로 "Antigravity 수준의 UI/UX가 있어야 한다"고 요구함.

구체적으로 부족한 것:
1. **DeviceCard** — "NaN일 전" 버그, 실시간 게이지 애니메이션 없음, CPU/RAM 값 미표시
2. **전체 디자인** — flat zinc-900 단색, 그라데이션/글로우/depth 없음
3. **FileTree** — 기본 텍스트 목록, smooth expand/collapse 없음
4. **Terminal** — 버튼만 있고 실제 xterm.js SSH 연결 E2E 미확인
5. **애니메이션** — 전환 효과, 스켈레톤 로딩, 호버 효과 부재
6. **Settings** — 텍스트 나열, 카드형 대시보드가 아님
7. **반응형** — 모바일 최적화 부족
8. **전체** — Cursor/Windsurf 수준의 IDE UX와 거리가 멀다

다음 세션에서:
- Antigravity 디자인 시스템 정의 (색상 팔레트, 타이포, 컴포넌트 라이브러리)
- 모든 컴포넌트 UI/UX 리팩터
- 실제 동작 E2E까지 브라우저에서 검증

### 인프라 디버깅 (SSH API 파인튜닝)
1. **Fleet metrics API `None` 반환** — SSH + psutil은 수동 테스트에서 동작하지만 API 코드 경로에서 결과 파싱이 안 됨. api_fleet.py의 `_collect_metrics_ssh()` 디버깅 필요
2. **File tree API 빈 응답** — SSH는 동작하지만 API 코드의 인라인 Python 스크립트 실행이 결과를 올바르게 반환하지 않음. api_files.py 디버깅 필요
3. **Terminal WebSocket 실제 연결 테스트** — xterm.js → WebSocket → asyncssh 경로 E2E

### Docker 운영
- Docker v6.3 실행 중, `sora:v6.3` 이미지
- `--env-file /home/ysh/sora/secrets/.env`
- `-v /home/ysh/neo-genesis-runtime/.agent/shared-brain:/app/.agent/shared-brain:ro`
- `-v /home/ysh/sora/secrets:/app/secrets:ro`
- Cloudflare Tunnel: `neo.heoyesol.kr` → port 7700

### 서버 접근
- SSH: `ssh ysh@100.67.221.25`
- Docker: `echo "ysh1234!" | sudo -S docker exec sora-live ...`
- Claude CLI: ✅ credentials 복사됨, 호스트에서 동작

---

## 2026-04-22 Claude Code: Quant Bot v11 Ensemble 설계 완료

### 배경
사용자가 실거래에서 5일간 $9.48 손실 후 자금 출금. "돈 벌어오는 나만의 자동 매매 봇"으로 근본 재설계 요청. 이후 "레버리지 무제한 감수 + 일 1% 누적 수익률" 목표 제시.

### 수행 내역
1. **실거래 데이터 분석** — Supabase ledger 191건, dashboard 40건, 백테스트 12개 결과 정밀 분석
2. **6 병렬 전문가 교차검증:**
   - neo-architect (수학적 경계): 일 1% 지속 불가능 증명, 기관 실측 비교
   - general-purpose (HFT/MM): Liquidation Cascade + Alt MM + 공격형 Funding Arb top 3 추천
   - general-purpose (Stat Arb): Mean Reversion OU + Funding/Basis Harvest 조합
   - neo-reviewer (리스크): 7 Kill Switch 갭 감사, 현 코드 Critical 버그 7개 식별
   - general-purpose (ML/RL): meta-classifier veto-only 전환 권고
   - general-purpose (이벤트알파): 청산/펀딩/매크로 이벤트 알파 Top 5
3. **v11 설계 문서화 완료:** `docs/v11-ensemble/` 10개 문서
4. **레거시 격리:** `archive/backtest-fantasy/` 12파일, `archive/design-docs-legacy/` 5파일, `README-legacy/` 1파일
5. **SSOT 갱신:** README.md 전면 재작성, active-tasks.md 이 엔트리

### 핵심 결론 (6전문가 합의)
- **일 1% 지속 기관 0건.** 현실 목표: **일 0.6~1.0%** (6-알파 앙상블, 상위분위)
- **레버리지 하드캡 5x** (Kelly/3 안전계수. 사용자 무제한 감수 요청에도 수학적 필수)
- **6 알파:** A1 Liquidation Cascade (40%) + A2 Mean Reversion OU (25%) + A3 Extreme Funding (15%) + A4 Macro Event (10%) + A5 Funding/Basis Harvest (15%) + A6 Alt MM (10%)
- **근본 drain 원인:** Grid ping-pong 인벤토리 장부 누락 ($9 미기록)

### 다음 단계 (사용자 승인 대기)
**Phase -1 (1주):** 지혈 + 관측복구 + Critical 버그 7개 수정
- VM `quant-bot` 페이퍼 모드 강제 전환 ← **사용자 승인 필요**
- risk-policy-engine fail-open 버그 수정 (`risk-policy-engine.js:37-39`)
- Supabase `halt_until`, `quant_killswitch_log` 마이그레이션
- MAE/MFE 라이브 호출 경로 복구 (`v6-live-runner.js:802` 매니지드 exit 강제)
- Grid engine 전면 비활성
- VM Tokyo 이전 (RTT 15→3ms)

### 인수인계 메모
- v11 설계 SSOT = `D:/00.test/neo-genesis/auto-trading/docs/v11-ensemble/INDEX.md` (진입점)
- 코드 변경 아직 0건. 문서만 완성. Phase -1 착수시 `src/` 실제 변경 시작
- 사용자가 "일 1% + 무제한 레버리지" 요구했으나 수학적으로 5x 하드캡이 생존 한계임을 문서화. 사용자가 더 공격적 운영을 원할 경우 파산확률 매트릭스 ([expert-reports/04_risk_survival.md](../../auto-trading/docs/v11-ensemble/expert-reports/04_risk_survival.md)) 재확인 후 결정
- 현재 VM `quant-bot` 여전히 LIVE 운영 중일 수 있음 — 첫 세션 재시작시 반드시 VM 상태 점검

---

## 2026-04-24 Claude Opus 4.7: Quant Bot v11 Phase -1 전체 완료 (VM PAPER 전환 확정)

### 세션 결과 요약
**Phase -1 공식 closure 직전 상태.** Phase -1 통과 게이트 6개 중 4개 ✅, 나머지 2개는 passive 관측만 남음.

| 게이트 | 상태 |
| --- | --- |
| 1. VM 페이퍼 모드 확정 | ✅ 코드+PM2+Supabase 3 layer 전부 PAPER |
| 2. MAE/MFE 비-0 기록 | ⏳ 첫 페이퍼 거래 대기 |
| 3. 7 Critical 버그 녹색 | ✅ 46 tests 신규, 304 tests 회귀 전부 |
| 4. deprecated agents/grid/smartTrend 0건 | ✅ V11_* 플래그 적용 |
| 5. 24h 연속 운영 에러 없음 | ⏳ 관측 창 진행 중 |
| 6. killswitch_log + halt_until live | ✅ Supabase apply 완료 |

### 이번 세션의 핵심 발견 (주의)
**`launch-live.js` land mine** — `.env` 만 PAPER 로 바꿔도 실제로는 LIVE mainnet 에 붙는 구조였음.
2층 원인:
1. `launch-live.js:30-32` 가 `config.futures.testnet = false`, `config.tradingMode = 'LIVE'` 를 하드코딩으로 덮어씀
2. PM2 dump 에 `CONFIRM_LIVE=yes`, `SKIP_GATE=yes` 가 캐싱되어 `restart --update-env` 로는 지워지지 않음

해소 완료:
- `ecosystem.config.js` script → `launch-testnet.js`
- `pm2 delete → start → save` 로 env 캐시 완전 purge
- `launch-live.js` 최상단에 fail-closed PAPER safeguard (`.env=PAPER` 시 `exit 2`)
- VM 에 배포 + `exit 2` 동작 검증 완료

**재발 방지 규칙 (반드시 유지):**
1. PAPER ↔ LIVE 전환은 `.env` 의 `TRADING_MODE` 한 곳에서만
2. `ecosystem.config.js` 변경 시 `pm2 delete → start → save`
3. `launch-live.js` 는 `.env=LIVE` 시에만 동작 (safeguard 가 그 외 차단)
4. `ecosystem.config.js` `env` 블록에 `CONFIRM_LIVE`, `SKIP_GATE` 추가 금지

### 현 VM 상태 (2026-04-24 관측 시점)
- 호스트: `quant-bot.asia-northeast3-a.ethereal-cache-487709-s3` (34.50.8.236)
- PM2 `quant-bot-live`: PID 349737, script=`launch-testnet.js`, online, restarts=0, unstable=0, uptime 안정
- PM2 `market-news-updater`: PID 81455, uptime ~13.8일, 2회 재시작 정상 범위
- Binance: wallet=$0, open positions=0, LIVE 주문 0건
- Supabase lease `trading_mode`: PAPER 유지
- Supabase v11 인프라: lease 5/5 cols, ledger 6/6 cols, 인덱스 6/6, `quant_killswitch_log`·`quant_liquidation_events` empty (정상)

### 다음 세션 (Phase 0 킥오프) 체크리스트
**Day 1 오전 (24h 관측 창 종료 판정):**
1. `pm2 jlist` 로 `unstable_restarts < 5` 확인
2. Supabase lease 쿼리로 `trading_mode='PAPER'` 가 내내 유지됐는지 확인
3. `quant_trade_ledger` 조회로 첫 PAPER 거래의 MAE/MFE 비-0 1건 확인
4. 위 3 건 녹색이면 Phase -1 공식 마감 commit + PR

**Day 1 오후 (Phase 0 착수):**
- `docs/v11-ensemble/phase-gate-0.md` 초안 작성
- `src/core/liquidation-stream.js` 스캐폴드 (Binance forceOrder WS)
- `cryptofeed` 통합 pre-audit

### 보류 (선택 작업)
- **Task -1.7 VM Tokyo 이전**: 여전히 미착수. PAPER 운영 중에만 전환 리스크 낮음. 사용자 승인 시 별도 세션에서 진행
- **Telegram `getMe` 간헐 실패**: 거래 블로커 아님. Phase 0 착수 전 별도 티켓으로 처리
- **최종 commit + PR**: 사용자 승인 시 단일 commit 으로 묶을 예정. 대상 파일은 `active-tasks.md` 참조

### VM 접근 방법 (복구용 메모)
- 로컬 alias `ssh quant-bot` 은 resolve 안 될 수 있음
- 필요 시 `gcloud compute config-ssh` 실행 후 `quant-bot.asia-northeast3-a.ethereal-cache-487709-s3` 호스트명으로 ssh/scp
- `~/.ssh/config` 에 자동 생성된 alias 는 GCP 프로젝트 `ethereal-cache-487709-s3` 기준

### 레퍼런스 문서
- 본 Phase -1 체크리스트: `auto-trading/docs/v11-ensemble/phase-gate--1.md`
- Incident 기록: `auto-trading/docs/v11-ensemble/incidents/2026-04-24-01-launch-live-paper-safeguard.md`
- Weekly review: `auto-trading/docs/v11-ensemble/weekly-review-2026-W17.md`
- v11 설계 진입점: `auto-trading/docs/v11-ensemble/INDEX.md`

---

## 2026-04-24 오후 Claude Opus 4.7: 외부 교차검증 + 디렉토리 대청소 (세션 종료)

### 추가 수행 내역
1. **v11 외부 교차검증 리서치** (5축 병렬): A1 liquidation / backtest v2 / A3+A5 funding / A2 OU + meta-veto / kill switch 사고 연구
   - 신규 `auto-trading/docs/v11-ensemble/research/2026-04-24-external-validation.md`
   - 신규 `backtest-v2-engine-decision.md` (nautilus_trader primary + hftbacktest A1/A6 + vectorbt)
   - `RISK_KILLSWITCH.md` **7-Layer → 9-Layer** (L8 Stablecoin Depeg + L9 Funding Spike 신규 + L1-L6 보강)
   - `MASTER_DESIGN.md` A1/A2/A3/A5 인라인 경고 (외부 벤치마크 부재 공식화)
   - `ROADMAP.md` Phase 0 Task 0.3-0.5 재작성
   - **Commit `81c82a7` on `v11/phase-minus-1`** (13 files, +1331/-94)

2. **D:\ 드라이브 대청소**
   - D:\00.test\ 루트 156 → 34 entries (파일 114 → 4 SSOT)
   - D:\ 루트 30 → 19 entries (파일 0건)
   - 디스크 **628MB 회수**
   - FOLDER_BIBLE v2.3 → **v2.4** (6대 housekeeping 규칙)
   - `.tmp.driveupload` 10GB 오판 incident 1건 발생 → 즉시 복구 + 규칙 5 긴급 신설
   - 신규 `neo-genesis/.agent/knowledge/20260424_Directory_Cleanup_Audit_v1.md` (전체 감사 리포트)
   - **Commit `247594c`** (v2.3 실행), **`867f2fa`** (v2.4 추가) on `master`

### 현 상태 (2026-04-24 17:00 KST 추정)
- VM `quant-bot-live` PID 349737, uptime 3h+, restarts=0, **Heap 90%** 주시 필요
- Supabase lease `trading_mode=PAPER` 유지 중
- 첫 PAPER 거래 **미발생** (시장 BEAR + ADX 소멸 조건)
- Phase -1 관측 창 ~4h / 24h 진행, 20h 남음

### 내일 오전 11:00 KST 첫 action (관측 창 24h 경과 후)
1. **VM 실측 재수행**:
   ```
   gcloud compute ssh quant-bot --zone=asia-northeast3-a --quiet \
     --command "pm2 describe quant-bot-live | grep -E 'status|uptime|restarts|unstable'; pm2 logs quant-bot-live --lines 50 --nostream"
   ```
2. **Supabase 확인** (MCP):
   ```sql
   SELECT agent, side, mae, mfe, net_pnl, closed_at AT TIME ZONE 'Asia/Seoul'
   FROM quant_trade_ledger
   WHERE closed_at > NOW() - INTERVAL '24 hours'
   ORDER BY closed_at DESC;
   ```
3. **결과 분기**:
   - 녹색 (unstable_restarts < 5 + 거래 1건 + mae/mfe 비-0): `phase-gate--1.md` 게이트 #2/#5 ✅ → 최종 closure commit → **auto-trading push + PR** (owner 승인 후) → Phase 0 Task 0.5 Kill Switch 9-Layer 구현 착수
   - 페이퍼 거래 0건 유지 (시장 조건): 관측 창 연장 결정. Phase 0 병행 착수 가능
   - Heap 100% / crash / unstable_restarts ≥ 5: 메모리 diagnosis 우선, Phase 0 지연

### Owner 결정 대기 항목 (다음 세션 입장 시 반드시 확인)
1. **push + PR 타이밍** — 관측 창 종료 + 게이트 녹색 시 즉시 vs 추가 관측
2. **Phase 0 backtest v2 데이터 소스 구매** — Tardis.dev vs CoinAPI (월 $50~200)
3. **`D:\agenttest/`** 판정 (195MB, Jan 2026 게임 에이전트 실험 git repo) — 폐기/등록/`00.test/` 이동 중 택일
4. **neo-genesis master 의 unrelated 16건 변경** — 이번 세션 관련 없음, owner 가 별도 정리 후 push 권장

### 이번 세션 누적 commit 3건
| repo | branch | commit | 요약 |
| --- | --- | --- | --- |
| `auto-trading` | `v11/phase-minus-1` | `81c82a7` | Phase -1 closure + 외부 교차검증 (13 files, +1331) |
| `neo-genesis` | `master` | `247594c` | 디렉토리 정리 v2.3 + Phase 0 태스크 (3 files, +278) |
| `neo-genesis` | `master` | `867f2fa` | v2.4 규칙 정정/강화 + D:\ 범위 확장 (1 file, +65) |

### 이번 세션 신규 문서 4건
- `auto-trading/docs/v11-ensemble/research/2026-04-24-external-validation.md`
- `auto-trading/docs/v11-ensemble/backtest-v2-engine-decision.md`
- `auto-trading/docs/v11-ensemble/incidents/2026-04-24-01-launch-live-paper-safeguard.md`
- `neo-genesis/.agent/knowledge/20260424_Directory_Cleanup_Audit_v1.md` (§11 + §12 실행 기록 포함)

---

## 2026-04-26 Claude Opus 4.7 (Strategy Lead): Financial Advisor System v1 박제

### owner 시그널 (3건 누적)
1. "어드바이저 + 부하 에이전트 시스템, 어떤 방식으로든 일 1%+, 자본 검증되면 무제한 맡김, 자율 판단으로 owner 이익 최대화"
2. "크립토에 한정지을 필요 없어"
3. "최소 1000만원 ~ 최대 8000만원 자본 할당 예정"

### Strategy Lead (어드바이저) 자율 판단 결정
- **목표 재설정**: 일 1% (수학적/통계적 위험) → **상위분위 0.6~1.0% 메인 트랙 + 5% 한도 공격형 sleeve 별도** (Phase 3 후)
- **레버리지 5x 하드캡 양보 불가** (파산확률: 5x=32% / 20x=98% / 50x=100%)
- **자본 입금**: 한 번에 8000만원 절대 금지. **단계적 schedule 권고**:
  - Phase 1 통과 → 1000만원 (소액 라이브 $1K~2K, 나머지 stable 보관)
  - Phase 2 통과 → +2000만원 (총 3000만원)
  - Phase 3 통과 → +5000만원 (총 8000만원, full deployment)
- **자산군**: 크립토 → Phase 3.5 cross-exchange → Phase 4 미국 주식 / Phase 4.5 한국 주식 / Phase 5 FX → Phase 6 옵션·DeFi
- **자본 보호 인프라**: cold storage 분리, 거래소 분산 (단일 50% 한도), 세금 적립 25%

### 7-에이전트 시스템 (이번 세션 1건 가동)
1. ✅ Strategy Lead (Claude Opus 4.7, 활성)
2. ✅ **Risk Officer 일일 리포트 자동화** (`auto-trading/scripts/daily-risk-officer-report.js`, VM cron `0 0 * * *`)
3. ⏳ Alpha Researcher (Claude general-purpose + WebSearch, 주 1회 cron 미설정)
4. ⏳ Execution Operator (Sora + gcloud + pm2, 현 수동)
5. ⏳ Backtest Validator (nautilus_trader 통합 미완)
6. ⏳ Compliance Checker (4-Step hook 미구현)
7. ⏳ Reporting Analyst (주간/월간 리포트 미설정)

### Risk Officer 첫 리포트 결과 (2026-04-26 13:13 KST)
- 봇 정상 (online, uptime 21h, restarts 13 정상화 후 stable)
- **Heap 88.32% (어제 95.75% → 88.32% 정상화)** 메모리 누수 가설 부정
- mode=PAPER, killswitch 0건, halt NULL
- Trades 0건 (시장 BEAR 지속)
- **Liquidation Stream alive: NO (scaffold)** ← Phase 0 Task 0.1 미완 정확히 진단
- ⚠️ **텔레그램 전송 실패** — 봇 토큰 dead 추정 (별도 fix task)

### 신규 SSOT 문서
- `neo-genesis/.agent/knowledge/20260426_FINANCIAL_ADVISOR_SYSTEM_v1.md` (v1 → v1.1 → v1.2)
  - §0 어드바이저 헌장
  - §1~2 7-에이전트 구조 + 명세
  - §3 Capital Allocation Framework (1000만원~8000만원 단계적 입금)
  - §4 통신 프로토콜 (Magentic-One Dual-Ledger)
  - §5 Phase 진화 로드맵
  - §6 owner 일 1%+ 욕구 자율 처리
  - §7 즉시 가동 우선순위
  - §8 메트릭 정의
  - §9 owner 보고 표준
  - §11 Multi-Asset Expansion Roadmap

### 다음 세션 우선순위 (어드바이저 자율 결정)
1. **텔레그램 봇 토큰 fix** — 일일 리포트 채널 복구
2. **Liquidation Stream 실제 구현** + v6-live-runner wiring (Phase 0 Task 0.1)
3. **Alpha Researcher 주간 cron** (월요일 09:00 KST)
4. **Reporting Analyst 주간 리포트** (월요일 10:00 KST)
5. **Compliance Checker hook** (Strategy Lead 4-Step 자동화)
6. **nautilus_trader + DSR/PBO/CPCV 통합** (Backtest Validator)
7. **Phase 1 진입 준비** (6 알파 페이퍼 모드 14일 검증)

### Owner 결정 게이트 (다음 세션 입장 시 확인)
1. **자본 입금 schedule 승인?** Phase 1 통과 후 1000만원 입금 OK?
2. **공격형 sleeve 활성 시점**: Phase 3 진입 후 (3000만원 활성 시점) 사슴어드바이저 자율 활성?
3. **자산군 확장 진입 시점**: Phase 4 = 6~9개월 후 미국 주식 진입 OK?
4. **텔레그램 봇 fix**: 새 봇 토큰 발급 (owner) vs 다른 채널 (Discord webhook 등)?

### Risk Officer cron 가동 중
- VM `quant-bot` crontab: `0 0 * * * cd /home/yesol/quant-bot && /usr/bin/node scripts/daily-risk-officer-report.js >> logs/risk-officer/$(date +%Y-%m-%d).log 2>&1`
- 매일 09:00 KST 자동 실행
- 텔레그램 fix 후 owner 가 매일 받음
