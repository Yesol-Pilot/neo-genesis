# ToolPick 심층 분석 + 라이브 검증 + Strategy Lead 판단 (2026-06-04, Claude Opus 4.8)

> 방법: 2-phase 워크플로 (28 에이전트 / ~5.6M 토큰) — Phase1 6차원+적대적검증+비평, Phase2 4 포렌식+4 외부리서치(웹)+종합 — **이후 9건 라이브 검증**(Supabase MCP / Vercel MCP / gh / git / lockfile / gitleaks / robots / npm audit / 404).
> 코드베이스: `src/sbu/toolpick` (Yesol-Pilot/https-www.toolpick.dev-, PRIVATE, master). Next 16.2.6 / React 19.2.3 / Vercel / Supabase(neogenesis-main 공유) / MDX.

## 한 줄 판정
ToolPick은 **엔지니어링 A급 / 전략 범주오류**. "대량 AI 콘텐츠로 100k MAU"는 2026 Google이 처벌(회복<1%)하는 방법, AI-도구-디렉토리 범주는 정점 지남. **결론: 100k 성장 베팅 중단 → 자율 발행기 무장해제 → 유지 모드 강등. 추가 성장 투자는 owner가 단일 버티컬에 사람-손 편집을 약속할 때만.**

## 정체 (라이브 확정)
- 프리트랙션·프리레비뉴: ~47세션/일(완전한날 7일평균, 하향 ~-25~30%), 실 추적 제휴링크 **1/83**, AdSense 거부, 구독자 **0**, 매출행 **0** (financial_ledger 17,838행 전부 cost).
- 자율 엔진: 진짜 배선(cron 6h → 부서회의→이사회→4단계 파이프라인→Octokit+Supabase)이나 **피드백 끊긴 닫힌 루프**. 코드 직접 확인: `model-router.ts:15-19` 전 티어 = MODEL.DEFAULT(gemini-2.5-flash), `kpi-tracker.ts:130` costPerPost:0/roi:0 → CFO veto 영구 미발화.
- **the open loop**: `seo-meeting.ts`가 GSC 기회(1591행→29) 0회 읽음, 하드코딩 폴백(#1=best-ai-coding)으로 주제 생성 → 760 재발행·드리프트의 구조적 원인.
- 자산: software.json(83도구) + 큐레이션 ~91글 + 프로덕션급 SEO 배관. 대량 hive-mind 콘텐츠는 부채.

## 라이브 검증이 교정한 것 (repo-기반 분석 → 실제)
| 분석 주장(과장) | 라이브 검증 |
|---|---|
| Next 16.2.4 High 6건 P0 | **lockfile next@16.2.6 패치됨 + npm audit 0**. react@19.2.3<19.2.6(RSC DoS)만 P1 |
| GA4 키 public P0 | **repo PRIVATE 확정** (gh: isPrivate:true) → 공개노출 X |
| Hive-mind RLS off 실위험 | **라이브 neogenesis-main 68테이블 전부 rls_enabled:true** (5/20 작업) → stale/거짓 |
| 폭주 48/일 활발 | 5/14 6h cron throttle, 마지막 GH발행 06-01 21:02; **+ Vercel이 HIVE-MIND 작성 배포 전부 BLOCKED** (사람 커밋만 READY, 마지막 prod 06-04) → production 봉쇄됨 |
| 적극 유해 20~25% | **날조후기 1편(ai-cybersecurity-saas.mdx) 국한**, stale-2024 12편(경미) |
| 시크릿 2파일 | **gitleaks 8건/5파일** (GA4 SA b64+json 히스토리 + scripts/ 3개), 전부 PRIVATE repo. code-health "0 secret"은 src/만 스캔 |
| 100k 격차 230~5000배 | **~66~71배** (월 ~1,419 vs 100k; 글당 필요 336 vs 현재 ~5) |
| deploy.yml=CI | **APC(reviewlab) Python cron**, toolpick 테스트/감사 CI는 없음 |

## 검증을 견딘 전략 결론 (외부근거 기반, 유효)
- 100k via SEO 비현실 (TAAFT 4.9M/Toolify 2M 해자, Futurepedia −80%, 16개월 AI실험 붕괴, AI인용엔 32K+ referring domain). → 5~15k 수익화 니치 재정의.
- 품질이 유통 아래 병목(~15~20% 경쟁력). 수익화 동결(premature 8~12x). 88 쿠팡글=site-reputation-abuse #1 위험(현 렌더404+VercelBLOCK로 라이브 위험↓, repo/히스토리 잔존).
- llms.txt 효과 0(Google Search 무시), AI유입 ~1%. agent-readability 과투자 중단.

## 권고 (Strategy Lead 판단)
owner=11+ SBU 1인, 5/12 매출연구도 저수율 콘텐츠 후순위. **C(웨지 피벗)는 지속 사람-편집 대역폭 요구 → 현실적 부족.** ∴ **1순위: A(안전)+B(목표폐기·자율중단·쿠팡격리)로 유지 모드, 에너지는 고수율 SBU(koreanllm 등)로 재배분.** C는 owner가 ToolPick 집중 결심 시만.

## Patch-ready 수정 명세 (별도 집중 실행 — 이 분석세션서 prod push 안 함: dormant+Vercel봉쇄라 비긴급)
- **A1 publisher skip-guard** `src/lib/hive-mind/pipelines/publisher.ts` publishContent 상단: slug 존재+content-hash 무변경 시 `status:'skipped_duplicate'` early-return (upsert/commit 전). 또는 `vercel.json` hive-mind orchestrate cron(0 */6) 제거가 더 안전한 source-level 무장해제.
- **A2** `react`/`react-dom` 19.2.3→19.2.7 + lockfile 재생성.
- **A3** `content/blog/ai-cybersecurity-saas.mdx` 날조 후기/케이스 제거 or 재작성 + stale "2024" 12편 날짜 수정.
- **A4 (G2)** GA4 SA키 회전(GCP ethereal-cache-487709-s3 — 5/18 사고 때 회전됐는지 확인) + 미러 `008.mirrors-external/.../ga4-key-b64.txt` 삭제 + `scripts/set_toolpick_env_api.py` 키 검증 + git history rewrite(force-push).

## G1(가역) vs G2(비가역·콘솔)
- G1: A1~A3 코드(`git checkout` 복구), 유지모드 판단, SSOT 박제.
- G2: A4 키회전/history rewrite, 88글 도메인 이전, KPI 공식 변경, Vercel/GCP 콘솔.

## 잔존 미확인 (owner 콘솔 전용)
1. Vercel이 HIVE-MIND 배포를 왜 BLOCK하나(보호규칙 vs 한도). 2. GA4/AdSense env(Vercel prod)=revenue0 근본. 3. GCP SA키 현재 활성. 4. scripts/ 3키 실값(R3로 미열람). 5. CWV(PSI 429, 키 필요 — 단 병목 아님).

## 실행됨 (2026-06-04)
- SSOT 박제 (이 파일 + active-tasks.md 포인터).
- 브랜치 `fix/toolpick-maintenance-disarm` 커밋 `2c632db`: A1 vercel.json hive-mind cron 제거 + A2 react/react-dom 19.2.7 + A3 ai-cybersecurity-saas.mdx 날조 제거. **미배포** (master 미머지). 더러운 audit 아티팩트 6개는 미스테이지(의도).
- 배포하려면: 브랜치 master 머지 → Vercel prod 자동 배포 (owner 결정).

## Reversibility
- SSOT: `git checkout .agent/knowledge/20260604_TOOLPICK_DEEP_ANALYSIS_v1.md .agent/shared-brain/active-tasks.md`
- 코드 브랜치: `git branch -D fix/toolpick-maintenance-disarm` (미머지라 master 무영향)

👤 Claude Opus 4.8 (ToolPick 심층분석 + 라이브검증 + 유지모드 판정)
