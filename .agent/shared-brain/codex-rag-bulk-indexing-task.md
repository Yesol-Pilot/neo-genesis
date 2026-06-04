# Codex CLI 핸드오프 — RAG v2 추가 인덱싱 (2026-05-10)

> **위임자**: Claude (sonnet)
> **수임자**: Codex CLI
> **owner**: 허예솔
> **owner 지시**: "자동화 및 오래걸리는 작업은 codex cli에게 위임하고 너는 공고 선별 계속해" (2026-05-10)

## owner 의도 (정확)

"내 모든 디바이스 RAG화 되어있을텐데" — 사용자 8대 디바이스 중 본인 본업 자료 (회사 PC = etribe-yesol Google Drive 미러 = H:/)와 본인 서버 자료 (ysh-server)가 RAG에 충분히 안 들어가 있음. 인사담당자에게 어필 가능한 사내 본업 자산 RAG 검색 가능 상태로 만드는 것이 목표.

## 현재 RAG v2 상태 (Tailscale 검증, 2026-05-10)

### 가동 중
- **Qdrant 6333** (ysh-server, 100.67.221.25): 6 컬렉션 / 205,619 points / status=green
- **mcp_gateway 7701** (ysh-server): health=ok, **단 `engine_ready=false`** (활성화 필요)
- **BGE Reranker 7704** (mac-studio, 100.81.93.118): 가동 중 (PID 49734)

### 차단 요인
- **KURE-v1 embedding 7702** (desktop-home, 100.96.186.7): **꺼짐** → curl 응답 없음
- 이게 켜져야 bulk_indexer가 H:/ + ysh-server 자료 인덱싱 가능

### Tailscale 디바이스 매트릭스 (정확)
| Hostname | IP | OS | SSH | 상태 |
|---|---|---|---|---|
| desktop-home (현 PC, RTX 4070 SUPER, conda base GPU) | 100.96.186.7 | Windows | self | KURE-v1 자리 — 재가동 필요 |
| ysh-server (본인 서버, Linux 6.17.9) | 100.67.221.25 | Linux | ✅ `ssh ysh-server` (ysh user) | Qdrant + mcp_gateway 가동 |
| mac-studio (M2 Max) | 100.81.93.118 | Darwin 25.2 arm64 | ✅ `ssh macstudio` (ysh user) | BGE Reranker 가동 |
| etribe-yesol (회사 PC, H:/ 동기화 원본) | 100.71.28.36 | Windows | ❌ Permission denied | 본업 원본 (현 PC H:/ 미러로 처리) |
| yesol-asus (노트북) | 100.106.84.87 | Windows | ❌ Permission denied | 미파악 |
| desktop-b7g8aq6 | 100.108.143.89 | Windows | offline 1d | 미상 |
| s26-ultra | 100.94.37.23 | Android | N/A | 모바일 (RAG 무관) |
| tab-s10-ultra | 100.106.139.13 | Android | N/A | 태블릿 (RAG 무관) |

## 인덱싱 목표 매트릭스

### P0 — 본업 자료 (가장 중요, 사용자 자기소개서/면접 준비 직결)
- **H:/다른 컴퓨터/내 컴퓨터/이트라이브_CTS/** (회사 PC Google Drive 미러)
  - 본업 사내 자료: SSIF 위캔버스 / DST 간호 VR / 한국학호남 / 경상남도교육청 / TIPA 심리메타 / NIPA / 회의록 / 주간보고 / 제안서 등
  - 단 회의록/정산/메일백업/카카오톡 받은파일 = 제외 (allowlist 룰 적용)
- **H:/다른 컴퓨터/내 컴퓨터/이트라이브_AI/** (회사 PC Google Drive 미러)
  - 사내 + 사이드 통합 코드베이스 40+ 프로젝트 (internal-ir-report-generator / agentic-cro / secur-pilot-engine / WebPilot-Engine / quant-bot / EthicaAI / WhyLab / 11 SBU 등)
- **H:/다른 컴퓨터/내 컴퓨터/CTS-AI/** (회사 PC Google Drive 미러)
  - SSOT 11건 + 신규 8건 = 19건 프로젝트 자산
  - `_admin/`, `docs/`, `projects/`, `.claude/rules/`, `.claude/commands/`

### P0 — ysh-server 잔여 (이미 일부 인덱싱)
- **~/sora/** (94MB, 1,414 파일, 현재 neo_notes 306건만)
- **~/neurips2026/** (1.2GB, 31,938 파일, 현재 neo_paper 7,694건만 = 24%)

### P1 — 디바이스 SSH 작업 후
- etribe-yesol / yesol-asus SSH key 등록 (owner 작업)
- 그 후 디바이스별 직접 인덱싱 (시간 여유 시)

## 작업 단계 (Codex 실행)

### Step 1: KURE-v1 재가동 (desktop-home, 5분)
```powershell
# 위치: D:/00.test/neo-genesis/scripts/rag_v2/embedding_service.py
# 가동 명령 (기존 active-tasks.md 4/27 참조):
# 환경: conda base (CUDA torch 또는 CPU torch)
cd D:/00.test/neo-genesis
python scripts/rag_v2/embedding_service.py --port 7702 --host 0.0.0.0 > logs/rag_v2/embedding_service.log 2>&1 &

# 검증:
curl http://localhost:7702/health
# 기대: {"status":"ok","model":"KURE-v1","device":"cuda"|"cpu"}
```

만약 conda env가 깨졌으면:
```bash
pip install --no-cache-dir sentence-transformers FlagEmbedding torch fastapi uvicorn
```

### Step 2: bulk_indexer로 H:/ 인덱싱 (P0)
```bash
# 위치: D:/00.test/neo-genesis/scripts/rag_v2/bulk_indexer.py
# 컬렉션 매핑 (allowlist):
#   - H:/.../이트라이브_CTS/ → neo_notes (회의록 제외, _admin/proposals + meetings 메타)
#   - H:/.../이트라이브_AI/ → neo_code (코드 + README) + neo_notes (docs)
#   - H:/.../CTS-AI/ → neo_notes (projects/ 안 PRD/proposals/meetings) + neo_code (코드)

# 실행 예시 (project_tag = etribe-cts / etribe-ai / cts-ai):
python scripts/rag_v2/bulk_indexer.py \
  --target "H:/다른 컴퓨터/내 컴퓨터/이트라이브_CTS" \
  --project-tag "etribe-cts" \
  --device-origin "etribe-yesol-mirror" \
  --collection auto \
  --exclude "회의록,주간보고,법인카드정산,다우오피스,메일백업,카카오톡 받은파일,스캔백업20251113,새 폴더,샘플,tmp,test-results"

python scripts/rag_v2/bulk_indexer.py \
  --target "H:/다른 컴퓨터/내 컴퓨터/이트라이브_AI" \
  --project-tag "etribe-ai" \
  --device-origin "etribe-yesol-mirror" \
  --collection auto

python scripts/rag_v2/bulk_indexer.py \
  --target "H:/다른 컴퓨터/내 컴퓨터/CTS-AI" \
  --project-tag "cts-ai" \
  --device-origin "etribe-yesol-mirror" \
  --collection auto
```

**예상 시간**: 2-4시간 (총 ~1.5GB 추정, KURE-v1 GPU 가동 시 2시간, CPU 4시간)

### Step 3: bulk_indexer로 ysh-server 잔여 인덱싱
ssh ysh-server 안에서 실행 (KURE-v1은 desktop-home 7702 사용 — reverse SSH tunnel 또는 직접 호출):

```bash
ssh ysh-server bash -c "
cd ~/neo-genesis-runtime
source ~/rag-v2-runtime/.venv/bin/activate

# Reverse tunnel: ysh-server localhost:7702 → desktop-home KURE-v1
# (desktop-home에서 ssh -fN -R 7702:localhost:7702 ysh-server 먼저 가동)

# ~/sora/ 인덱싱
python scripts/rag_v2/bulk_indexer.py \
  --target ~/sora \
  --project-tag sora-prod \
  --device-origin ysh-server \
  --collection neo_notes \
  --exclude 'logs/.*\.log,backups,build,secrets,\.cache'

# ~/neurips2026/ 잔여 인덱싱
python scripts/rag_v2/bulk_indexer.py \
  --target ~/neurips2026 \
  --project-tag neurips2026-server \
  --device-origin ysh-server \
  --collection neo_paper \
  --exclude '\.log,monitor.*'
"
```

### Step 4: mcp_gateway engine_ready=true 만들기
현재 `curl localhost:7701/health` = `engine_ready: false`. 인덱싱 끝나면 활성화 필요.

```bash
ssh ysh-server bash -c "
cd ~/rag-v2-runtime
# mcp_gateway 재기동 (KURE-v1 + BGE Reranker 모두 가동 후)
pm2 restart mcp_gateway || ./start-gateway.sh
curl http://localhost:7701/health
# 기대: {\"status\":\"ok\",\"engine_ready\":true,\"jwt_enabled\":true}
"
```

### Step 5: 검증
```bash
ssh ysh-server bash -c "
for c in neo_ssot neo_code neo_paper neo_notes neo_quant neo_secret; do
  echo -n \"\$c: \"
  curl -s http://localhost:6333/collections/\$c | grep -o 'points_count[^,]*'
done
"
```

기대 결과 (인덱싱 완료 후):
- neo_code: 88,971 → 130,000+ (이트라이브_AI 코드 추가)
- neo_notes: 49,283 → 80,000+ (이트라이브_CTS docs + sora + CTS-AI projects)
- neo_paper: 64,595 → 90,000+ (neurips2026 잔여)
- neo_ssot: 2,290 → 5,000+ (.claude/rules + AGENTS.md + CLAUDE.md)

### Step 6: 완료 보고
- `.agent/shared-brain/active-tasks.md`에 RAG Phase 1.5 완료 entry 추가
- 텔레그램 알림 (sora-watchdog 통해): "[Codex] RAG v2 인덱싱 완료, neo_notes/code/paper +X건"
- `.agent/shared-brain/handoff.md`에 Codex → Claude 완료 reverse handoff

## 차단/실패 시 fallback

| 차단 | 대처 |
|---|---|
| KURE-v1 모델 다운로드 실패 (네트워크) | mac-studio (BGE) 만 사용해서 일부 진행 또는 대기 |
| H:/ 권한 문제 | 회의록 폴더 등 제외, 접근 가능한 폴더만 |
| GPU OOM | --batch-size 16 → 8 → 4 줄이기 |
| 시간 초과 | 컬렉션별 분할 (neo_notes 먼저, neo_code 나중) |
| Qdrant 디스크 부족 | 컬렉션별 사이즈 확인, oldest archive |

## 절대 하지 말 것

- ❌ 회의록 본문 / 메일 / 정산 자료 인덱싱 (PII + 무가치)
- ❌ secrets/ 폴더 인덱싱 (이미 .gitignore + allowlist)
- ❌ NIPA 폴더 인덱싱 (owner 명시 제외)
- ❌ etribe-yesol / yesol-asus SSH 접속 시도 (이미 Permission denied 확인)
- ❌ desktop-b7g8aq6 (미상 디바이스, 1일 offline)

## 결과물

성공 시:
1. 본업 자료 RAG 검색 가능 (사용자가 자기소개서 작성 시 SSIF/DST/HIKS/블루벤트/HLB/나인벨 키워드로 정확한 사내 사례 인용 가능)
2. mcp_gateway engine_ready=true 활성화
3. neo_notes/code/paper points 50~100% 증가 추정
4. Phase 1.5 완료 + Phase 2 (LightRAG / Contextual Retrieval) 다음 단계 가능

## 참조 SSOT
- `.agent/knowledge/20260426_RAG_MASTER_DESIGN_v1.md` — 마스터 설계
- `.agent/policies/rag_governance.yaml` — 거버넌스
- `.agent/policies/rag_source_allowlist.yaml` — allowlist (회의록 등 제외 룰)
- `.agent/shared-brain/active-tasks.md` Phase 0 / Phase 1 entry — 이전 인덱싱 기록
- `D:/00.test/jobsearch/data/v3/` — Claude가 동시에 진행 중인 공고 매칭 작업

---

**Claude는 동시에 verified asset (28건) 기반 공고 매칭 재실행 진행 중**. RAG 인덱싱은 자기소개서 작성 시점에 활용 가능 상태로 만들면 충분.

**완료 시간 예상**: KURE-v1 가동 5분 + H:/ 인덱싱 2-4h + ysh-server 잔여 1-2h = 총 4-7시간 BG.
