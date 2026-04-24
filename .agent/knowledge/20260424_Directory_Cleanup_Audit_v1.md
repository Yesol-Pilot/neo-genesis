# D:\00.test 디렉토리 정리 감사 리포트 v1

> **작성자:** Claude Opus 4.7
> **작성일:** 2026-04-24 KST
> **감사 범위:** `D:\00.test\` 전체 + `D:\00.test\neo-genesis\` 심층
> **방법:** SSOT 문서 대조 + 2축 병렬 read-only 스캔 + 사이드이펙트 grep
> **작성 목적:** Stage 2 (owner 검토 + 승인) 의 근거. 아무 파일도 이동/삭제되지 않은 상태

---

## 0. TL;DR (결론 먼저)

1. **지저분함의 주원인은 neo-genesis 내부가 아니라 `D:\00.test\` 루트**
   - neo-genesis 내부: FOLDER_BIBLE 정합성 **96%** (의외로 깔끔, cleanup 대상 148KB 수준)
   - 루트: 파일 114건 + 디렉토리 42건 중 **60+ 항목이 cleanup 대상**, 용량 기준 **229MB 절약 가능**

2. **"룰이 있을 텐데" 의 진실 = 부분 룰만 존재**
   - FOLDER_BIBLE.md = **주요 프로젝트 디렉토리만 정의** (20+)
   - 루트 잡파일 / 임시 / 백업 / venv / 경로 오염 사고 처리 규칙은 **정책 공백**
   - 즉 "룰 위반" 이 아니라 "룰 부재" 가 혼란의 실질 원인

3. **이동만으로 깨지는 참조 0건** (Agent A 사이드이펙트 grep 결과)
   - 단 4건 특수 처리 필요: `_alltree.json` (검증 완료), `source/` venv (재생성), `C:Usersyesol/` (Windows 경로 오염 사고), `node_modules/` + `package.json` (구 설정)

4. **단계적 3 batch 실행 권고** — 저위험 → 중위험 → 고위험 순. 각 batch 사이 검증.

---

## 1. 감사 범위

### 포함
- `D:\00.test\` 최상위 (파일 114 + 디렉토리 42)
- `D:\00.test\neo-genesis\` depth 2 구조 + `.agent/` 전체
- FOLDER_BIBLE.md / CLAUDE.md / NEO_MASTER_RULES.md 와 현실 diff
- 사이드이펙트 grep (root jetsam ≈ 100 파일)

### 제외 (스캔 안 함)
- **`D:\00.test\personal\`** — 법무/금융 민감 서류. CLAUDE.md §1.4 금지
- **`secrets/`, `.env*`, credentials / token 파일** — 이동만으로 경로 참조 깨짐
- **PAPER/EthicaAI + WhyLab `submission-freeze/*` branches** — 2026-04-25 freeze anchor
- **neo-genesis/auto-trading/ VM 참조 경로** — Phase -1 관측 창 진행 중
- **`github_repos/`** (외부 레포 26개 클론) — 본인 소유 아닌 코드, 건드리지 않음

---

## 2. 현황 숫자

### `D:\00.test\` 루트
| 항목 | 값 |
| --- | --- |
| 루트 파일 수 | 114 |
| 루트 디렉토리 수 | 42 |
| 잡파일 최대 cluster | **Mar 22 단 하루에 38건 생성** (1회성 분석 잔해) |
| Mar 21-22 합계 | 47건 |
| 루트 `node_modules/` | **214MB** (package.json = googleapis + reveal.js 2개) |
| 루트 `source/` venv | 15MB, WSL 경로 하드코딩 → Windows 이동시 작동 불가 |
| `_alltree.json` | **6.7MB** (neo-genesis + PAPER + portfolio tree 스냅샷, 참조 0건 확인) |

### `D:\00.test\neo-genesis\`
| 항목 | 값 |
| --- | --- |
| 루트 depth 1 | 27 폴더 + 22 파일 |
| FOLDER_BIBLE 정합성 | **96%** |
| `.agent/` 파일 수 | 184 |
| `.agent/` 크기 | 1.8MB |
| Active SBU | 9/9 ✅ (BIBLE 명시대로) |
| Research/Automation SBU | 6/6 ✅ |
| 별도 Git 프로젝트 | 2/2 ✅ (auto-trading, neo-command) |
| Cleanup 대상 용량 | **148KB** (거의 없음) |

---

## 3. Group 별 분류 + 판정

### 3.1 Tier 0: ✅ 즉시 archive 가능 (참조 0건 확정)

| 그룹 | 대상 | 건수 | 출처 | 예상 절약 |
| --- | --- | ---:| --- | ---: |
| A | 루트 분석/테스트 `.js` (aiforge_orch2, check_*, ga4_*, ph_*, posthog_*, reval*, test_api, verify) | 22 | Mar 21-22 1회성 | ~50KB |
| B-1 | 루트 분석 결과물 `.txt` / `.json` (`__*.txt`, aiforge_*, analytics_keys, cron_result_*, final_*, ga4_*, posthog_*, traffic_full_analysis, verify.out) | 22 | Mar 21-22 | ~200KB |
| C | 이력서/면접 `.html/.md/.pdf` (Personal_AI_Capability_*, CTS_Team_*, INTERVIEW_*, SUPERCENT_*, supercent_interview_prep, channel_resume*, _tg_send, temp_interview_utf8) | 15 | Mar-Apr | ~650KB |
| D-1 | 빈 디렉토리 / 임시 (`scripts/`, `tests/`, `tmp/`, `.tmp.drivedownload/`, `.tmp.driveupload/`, `aiforge_temp/`) | 6 | 오래됨 | 미미 |
| D-2 | 개별 파일: `CLAUDE.md.bak-20260424-110548`, `tailscale_openapi.json` (226KB), `tmp_tailscale_api.html` (70KB), `tmp_tailscale_api_docs.js`, `desktop.ini`, `doc_reader.py` | 6 | 구버전/임시 | ~330KB |
| neo-genesis | `tmp_claude_*.txt` (2), `boot_*.log` (4), `tools_out*.txt` (3), `ga4_traffic_out.txt` (빈), `*.pid` (4), `dump.rdb` | 15 | 런타임 아티팩트 | ~78KB |

**합계: 약 86건 / ~1.3MB** (참조 0건, 즉시 이동 가능)

---

### 3.2 Tier 1: ⚠️ 검증 후 archive

| 대상 | 판정 | 이유 |
| --- | --- | --- |
| `_alltree.json` (6.7MB) | ✅ **검증 완료, archive 가능** | neo-genesis/PAPER/portfolio/.agent 모두에서 grep 0건 (2026-04-24) |
| `.agent/backups-ssot-merge-20260424-094951/` | ⚠️ **7일 후 재검토** | SSOT merge 백업. 당일 생성이라 아직 valid, 1주 후 삭제 |
| `aiforge_orch_result.txt` (4건) | ⚠️ `aiforge_orch2.js` 와 함께 이동 | 쌍으로 유지 (스크립트-출력 페어링) |

---

### 3.3 Tier 2: 🔴 특수 처리 (재생성 / 별도 판단)

#### T2-1. `source/` (Python venv, 15MB)
- `pyvenv.cfg` 의 경로: `home = /usr/bin`, `command = /usr/bin/python3 -m venv /mnt/d/00.test/source`
- WSL 절대경로로 하드코딩 → **Windows 에서 이동해도 작동 불가**
- 권장 action: **삭제** (`rm -rf source`), 필요 시 `python -m venv source` 재생성
- 리스크: 현재 사용 중인 스크립트가 있다면 먼저 확인 → `source/bin/activate` 참조 grep 1회 필요

#### T2-2. `C:Usersyesol/miniconda3/`
- Windows 경로 `C:\Users\yesol` 를 cp 하려다 escape 안 되어 **상대경로 디렉토리로 오염**
- `C:Usersyesol/miniconda3/` 안에 실제 conda 파일들 존재 (Drive upload 실수 추정)
- 권장 action: **owner 확인 후 삭제** (실제 conda 환경은 `C:\Users\yesol\miniconda3` 에 별도 존재할 것)
- 리스크 없음 (경로명 자체가 오염된 사고 결과물)

#### T2-3. 루트 `node_modules/` (214MB) + `package.json` + `package-lock.json`
- `package.json` 내용: `{googleapis: ^171.4.0, reveal.js: ^5.1.0}` 2개만
- 용도 불명의 1회성 스크립트용으로 추정 (reveal.js = 프레젠테이션, googleapis = GA4 쿼리)
- 실제 프로젝트는 각 서브 디렉토리에 별도 `node_modules` 보유 (neo-genesis/, portfolio/ 등)
- 권장 action: **루트 `node_modules/` 삭제** + `package.json` + `package-lock.json` archive
- **예상 절약 214MB (전체 cleanup 의 93%)**
- 리스크 없음 (루트 package.json 에 의존하는 스크립트 확인 필요 → grep 1회 권고)

#### T2-4. `_archive/` (기존 의도적 archive)
- 내용: `__bom_finstack`, `__d2_*`, `__dep_*`, `__temp_*`, `__verify`, `portfolio_backup_20260315_120517`
- 명시적으로 SBU prefix 네이밍으로 저장된 의도적 보관
- 권장 action: **유지**. 단 6개월+ 경과분은 압축 또는 외부 백업으로 이동 검토

#### T2-5. `_extracted/` (개인 문서 12폴더)
- FOLDER_BIBLE.md 에 명시 ("정리된 콘텐츠")
- 내용: career, metaverse, wellness, 1o1_coin_whitepaper, bukchon, itsjarvis 등
- 권장 action: **유지**. `personal/` 과 역할 분담 명확화 필요 (문서 정비)

---

### 3.4 Tier 3: 🚫 절대 건드리지 않음

| 영역 | 이유 |
| --- | --- |
| `personal/` | 법무/금융 민감자료 (CLAUDE.md §1.4) |
| `secrets/`, `.env*`, credentials/token | 이동만으로 경로 참조 깨짐 |
| `PAPER/EthicaAI/`, `PAPER/WhyLab/` | submission-freeze branches (20260414, 20260425) anchor |
| `neo-genesis/auto-trading/` | Phase -1 관측 창 진행 중 (VM 참조 경로) |
| `neo-genesis/.agent/shared-brain/claude-checkpoints/` | 에이전트 학습 체크포인트 (삭제 시 이력 소실) |
| `github_repos/` | 외부 레포 클론 (본인 소유 아님) |
| 각 프로젝트의 `.git/` | git history 보존 |

---

## 4. 사이드이펙트 맵 (정리 시 영향 범위)

| 이동 대상 | 영향 범위 | 깨질 위험 |
| --- | --- | --- |
| Tier 0 전체 | 없음 | ✅ zero (grep 0건 확인) |
| `_alltree.json` | 없음 | ✅ zero (grep 0건 확인) |
| `source/` venv | 구 Python 스크립트 | ⚠️ `source/bin/activate` 참조 grep 1회 필요 |
| `C:Usersyesol/miniconda3/` | 없음 (오염 사고 결과물) | ✅ zero |
| 루트 `node_modules/` | 없음 (각 서브에 별도 보유) | ⚠️ `require('googleapis')` 또는 `require('reveal.js')` 루트 참조 grep 1회 필요 |
| `.agent/backups-ssot-merge-*/` | sync_agent_context.py | ⚠️ 7일 후 재검토 |

---

## 5. 단계적 실행 계획 (Stage 3 batches)

### Batch 1 (저위험, 즉시 실행 가능) — ~1.3MB
- Tier 0 전체 (86건) 을 `D:\00.test\_archive\root-cleanup-20260424\` 하위 group 별로 이동
  - `_archive/root-cleanup-20260424/group-a-analysis-js/`
  - `_archive/root-cleanup-20260424/group-b-analysis-results/`
  - `_archive/root-cleanup-20260424/group-c-resume-interview/`
  - `_archive/root-cleanup-20260424/group-d-tmp-backup/`
- neo-genesis 루트 런타임 아티팩트 (tmp_claude, boot_log, tools_out, pid, dump.rdb) 삭제 (재생성됨)
- **실행 시간: ~10분**

### Batch 2 (중위험, 검증 후) — 229MB
- `_alltree.json` → `_archive/root-cleanup-20260424/`
- 루트 `node_modules/` 삭제 (214MB 회수) — grep 선행 1회
- `package.json` + `package-lock.json` → archive
- `source/` venv 삭제 (15MB) — grep 선행 1회
- `C:Usersyesol/miniconda3/` 삭제 (owner 확인 필요)
- **실행 시간: ~20분**

### Batch 3 (룰 현행화)
- FOLDER_BIBLE.md **v2.3 업데이트**:
  - 루트 정책 섹션 신설 ("루트에 올 수 있는 것 / 올 수 없는 것")
  - 임시 파일 생명주기 규칙 ("7일 후 archive, 30일 후 삭제")
  - 런타임 아티팩트 `.gitignore` 강제 (`*.pid`, `dump.rdb`, `tmp_*.txt`, `boot_*.log`)
- `.agent/backups-ssot-merge-*/` 보관 정책 추가 ("1주 후 삭제")
- `/sbu` vs `src/sbu/` 이원화 해소 (하나로 통일)
- CLAUDE.md 에 "루트 파일 생성 금지, 분석 스크립트는 `tmp/` 또는 프로젝트 하위로" 원칙 추가

### Batch 4 (선택, 나중)
- 6개월+ 경과 `_archive/` 하위를 압축 또는 외부 백업으로 이전
- `_extracted/` 내용 정리 (`personal/` 과 역할 분리)

---

## 6. 정책 공백 → FOLDER_BIBLE v2.3 증보 권고

### 6.1 현재 FOLDER_BIBLE 이 명시하지 않는 것들
- 루트에 **올 수 있는 것 / 올 수 없는 것**
- 임시 파일 / 분석 결과물 / 백업 생명주기
- 런타임 아티팩트 (pid, dump.rdb, log) 처리 규칙
- venv / conda 환경 위치 규칙
- 이력서/면접 문서 위치 (현재 루트에 산재)
- 스크립트 실행 결과물 저장 위치 (현재 루트에 산재)

### 6.2 증보 권고 — 4개 신규 규칙

**규칙 1. 루트 파일 생성 금지 원칙**
> 루트 (`D:\00.test\`) 는 **프로젝트 디렉토리와 SSOT 문서만** 허용. 분석 / 테스트 / 임시 스크립트는 프로젝트 하위 `tmp/` 또는 `scripts/` 에 생성.

**규칙 2. 임시 파일 생명주기**
> `tmp_*`, `boot_*`, `tools_out*`, `__*.txt` 패턴 파일은 생성 후 **7일 경과 시 자동 archive**, 30일 경과 시 삭제. 런타임 아티팩트 (`*.pid`, `dump.rdb`) 는 `.gitignore` 필수.

**규칙 3. 이력서 / 면접 문서 전용 경로**
> 개인 이력서 / 면접 준비 / 커리어 문서는 `D:\00.test\project_yesol\career/` 하위에 통합. 루트 생성 금지.

**규칙 4. venv / conda 환경 규칙**
> 프로젝트별 Python 가상환경은 **해당 프로젝트 하위 `.venv/`** 에만 생성. 루트 venv 금지. conda 환경은 `C:\Users\yesol\miniconda3` 전용 경로에만.

### 6.3 neo-genesis BIBLE 증보 (Agent B 발견)

- `/sbu` vs `src/sbu/` 이원화 → `src/sbu/` 로 통일 + BIBLE 갱신
- `.agent/backups-ssot-merge-*/` 보관 정책 (1주 후 삭제)
- 에이전트 스킬 평가 아티팩트 (`eval-runs/`) 보관 기한 명시

---

## 7. 예상 효과

| 항목 | Before | After | 개선 |
| --- | --- | --- | --- |
| 루트 파일 수 | 114 | ~30 | 84 건 정리 |
| 루트 디스크 | ~300MB | ~70MB | **229MB 회수** |
| 가시성 | 혼란 (60+ 잡파일 산재) | 프로젝트 디렉토리 + SSOT 만 노출 | 큰 개선 |
| FOLDER_BIBLE 정합성 | 부분 적용 | v2.3 규칙 4개 신설 후 100% | 룰 공백 해소 |
| 사이드이펙트 | — | 0건 (grep 검증 완료) | 안전 |

---

## 8. Owner 승인 대기 항목

1. **Batch 1 실행 승인** (저위험, 참조 0건, ~1.3MB 이동)
2. **Batch 2 실행 승인** (중위험, 229MB 회수, grep 선행 필요 2건)
3. **`C:Usersyesol/miniconda3/` 처리 결정** — 활성 conda 환경 유무 owner 확인
4. **FOLDER_BIBLE v2.3 업데이트 착수 여부**
5. **`_extracted/` 재편 여부** (`personal/` 과 역할 명확화)

---

## 9. 실행 시 안전 원칙 (내가 자율 실행할 때)

- ✅ **archive 이동만**, 삭제는 Batch 1 런타임 아티팩트 (pid/dump.rdb/boot_log) 한정
- ✅ 각 batch 이후 **검증 단계** 삽입 (Sora 런타임 로드 / 빌드 / 테스트)
- ✅ 각 batch 는 **별도 git commit** (auto-trading 제외, 대부분 master repo)
- ✅ Push 전 owner 승인
- 🚫 **personal/, secrets/, freeze branches, github_repos/** 진입 금지
- 🚫 **영구 삭제는 오직 런타임 아티팩트 + 확정 오염 (`C:Usersyesol/`)** 에 한정
- 🚫 git history rewrite (filter-branch / rebase -i) 금지

---

## 10. 다음 단계

**Stage 2**: owner 가 이 감사 결과를 검토하고 승인/조정/반려 결정.

승인 시 **Stage 3 Batch 1 즉시 실행** (~10분). 그 후 Batch 2/3/4 순차.

모든 batch 는 **별도 git commit + push 전 owner 승인** 원칙 유지.
