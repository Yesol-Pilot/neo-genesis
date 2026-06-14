# PCP 교정 Runbook v1 — 보안 + 중복 정리 + 저장소 생성

> **상태:** 실행 runbook. PCP v1(`20260614_PROJECT_CONTINUITY_PROTOCOL_v1.md`)의 Phase 2~4 집행 절차.
> **작성:** 2026-06-14, Claude Opus 4.8. 실측 46 repo root 기반 (`010.tmp-output/pcp_repo_inventory.json`, `pcp_families.json`).
> **원칙:** 가역(MOVE-first) · 시크릿 값 미노출 · G1(자율)/G2(owner) 명확 구분.

---

## 0. 실측 요약

- git repo root **46개** = **27 패밀리**(고유 리모트). 즉 **19벌이 중복 클론**(5/11 numbered 마이그레이션 잔재).
- 보안 교정 필요 **5 패밀리**:
  - 🔴 **embedded PAT** 3 패밀리(클론 6벌): `clash_of_myths`, `internal-ir-report-generator`, `secur-pilot-engine` — 동일 PAT 1개가 `.git/config` origin URL에 하드코딩.
  - 🔴 **etribe(blocklist)** 1 패밀리(2벌): `webpilot-engine` → `code.etribe.co.kr`.
  - 🟠 **wrong-account** 1 패밀리(2벌): `profile-repo` → `github.com/ysh1537`(Yesol-Pilot 아님).

---

## 1. 🔴 P0 보안 — embedded PAT 제거 (즉시)

**위험:** GitHub PAT가 평문으로 `.git/config`에 저장 → 디스크/백업/화면 공유 시 누출. 6개 클론에 동일 토큰.

### 1-A. 리모트 URL sanitize (G1 자율 — 가역, 토큰값 미사용)
각 repo의 origin을 토큰 없는 URL로 교체(자격증명은 git credential manager/SSH가 담당):
```
git -C "<repo>" remote set-url origin https://github.com/Yesol-Pilot/<repo-name>.git
```
대상 6벌:
- `006.games-labs/002.clash-of-myths`, `006.games-labs/clash_of_myths` → `Yesol-Pilot/clash_of_myths.git`
- `007.infra-tools/003.internal-ir-report-generator`, `007.infra-tools/internal-ir-report-generator` → `Yesol-Pilot/internal-ir-report-generator.git`
- `007.infra-tools/004.secur-pilot-engine`, `007.infra-tools/secur-pilot-engine` → `Yesol-Pilot/secur-pilot-engine.git`
검증: `git -C "<repo>" remote get-url origin` 에 `ghp_`/`@` 없음.

### 1-B. 코드/문서 내 동일 토큰 잔존 점검 (G1 자율)
`.git/config` 외에도 박혔는지 — gitleaks 또는 `git grep -nI "ghp_"` (파일명만 보고, 값 출력 금지). 발견 시 제거 + 히스토리 오염이면 BFG/ filter-repo 검토(G2).

### 1-C. PAT 회전 (G2 owner — 크레덴셜 변경)
- GitHub Settings → Developer settings → Personal access tokens → 해당 `ghp_...` **Revoke**.
- 새 토큰 발급 필요 시 fine-grained + 최소 scope. `.env.local` + CREDENTIAL_BIBLE 동시 갱신([[credential-upkeep]] 규칙).
- ⚠️ 이 토큰은 채팅/스캔에 노출됐으므로 **회전 권장**(1회 권고, owner 판단).

---

## 2. 🔴 P0 보안 — etribe(blocklist) 격리

**위험:** `webpilot-engine` 2벌이 회사 GitLab(`code.etribe.co.kr`). 하드룰상 etribe push 금지. 회사 자산일 가능성(이트라이브 본업).

### 절차 (G2 owner 판정 필요)
- **회사 자산이면**: `005.client-work` usagePolicy 적용 → **Tier 2 vault**(외부 리모트 동기화 금지). Yesol-Pilot로 옮기지 말 것. PCP 도구가 이미 `REMOTE_REFUSED` 처리(검증됨).
- **개인 자산이면**: origin을 `Yesol-Pilot/webpilot-engine`(private)로 재설정 후 push.
- 판정 전까지: 도구가 자동 차단하므로 안전. owner가 자산 귀속만 확정하면 됨.

---

## 3. 🟠 P1 — wrong-account(ysh1537)

`profile-repo` 2벌 → `github.com/ysh1537/ysh1537`. ysh1537이 owner 구계정이면 유지(push 게이트), Yesol-Pilot 이관 원하면 remote 재설정. **G2 owner 확인.** 그 전까지 push 자동 차단(non-allowlist).

---

## 4. 🟡 중복 클론 19벌 정리 (canonical 유지 + 나머지 archive)

**원칙:** numbered 버킷 경로를 canonical로(마이그레이션 목적지 규칙). 나머지는 삭제 아닌 **MOVE → `009.archive/dedupe-20260614/`**(가역). dirty 작업본이 있으면 먼저 commit/stash.

주요 중복(전체 19벌은 `010.tmp-output/pcp_families.json`):
| 패밀리 | canonical 유지 | archive 대상(중복) |
|---|---|---|
| neo-genesis | `001.ssot-agent-runtime/002.neo-genesis-sbu-autogrowth` (SSOT 브랜치) + `neo-genesis`(master, 17K작업본) **둘 다 유지** | `neo-genesis__sbu_autogrowth`, `001.ssot.../neo-genesis__sbu_autogrowth` (2벌) |
| sora-app | `002.products-sbu/005.sora-app` | `002.products-sbu/sora-app`, 루트 `sora-app` (2벌) |
| jobsearch | `003.portfolio-career/003.jobsearch` | 루트 `jobsearch`, `003.portfolio-career/jobsearch` (2벌) |
| 2dlivegame / clash / game-pipeline / cts / agentic-cro / multiverse / webpilot / internal-ir / secur-pilot / landing / profile | numbered 경로 | unnumbered 1벌씩 |

⚠️ **주의:** neo-genesis 계열은 **같은 리모트의 다른 브랜치 작업본**(master 17K dirty vs sbu/autogrowth)이라 단순 중복 아님 — 둘 다 의미 있는 작업본. archive 전 owner 확인(G2). 나머지 순수 클론 중복만 자율 정리 후보.

---

## 5. nogit Tier1 저장소 생성 (owner 명령 "반드시 저장소 생성")

`--init-repo`로 **로컬 git 자율 생성**(리모트 미생성·미푸시 — 외부 액션 0, 가역). 대상: `koreanllm`, `ait-factory`, `veo-shorts`, `PAPER`(대용량 → LFS 검토). `.env` 자동 제외 검증됨.
```
python scripts/agent_session_sync.py D:/00.test/002.products-sbu/009.koreanllm --init-repo --apply
```
이후 **private repo 생성 + remote 연결 + push**만 G2(가시성·민감도 owner 판단).
- `_secrets`/`personal`/`project_yesol`(PII)/`005.client-work`(회사) = **저장소화 금지**(Tier2 vault, registry에 박제됨).

---

## 6. neo-genesis 17K dirty 회복 (별도 세션, G2)

루트 `neo-genesis`(master) 미커밋 17,018개. 무지성 pull 금지(PCP가 자동 보호). 회복: owner와 함께 ① `.gitignore` 재정비(로그/빌드/캐시 대량 제외) → dirty 급감 ② 의미있는 변경만 선별 commit ③ 나머지 stash/정리. 별도 정리 세션 권장.

---

## 실행 우선순위 (요약)

| 순 | 작업 | 게이트 | 가역 |
|---|---|---|---|
| 1 | PAT sanitize(remote set-url) 6벌 | G1 자율 | ✅ |
| 2 | PAT 회전 | G2 owner | — |
| 3 | etribe 자산 귀속 판정 | G2 owner | ✅ |
| 4 | nogit Tier1 `--init-repo` | G1 자율 | ✅ |
| 5 | 순수 중복 클론 archive(MOVE) | G1 자율(neo-genesis 제외) | ✅ |
| 6 | private repo 생성·push | G2 owner | ✅ |
| 7 | neo-genesis 17K 정리 | G2 owner | ✅ |

관련: [[project-continuity-protocol]] · 도구 `scripts/agent_session_sync.py` · 레지스트리 `.agent/policies/project_continuity_registry.json`
