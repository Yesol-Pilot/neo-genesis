# Jarvis Owner 주요 명령 100선 (2026-05-29)

> owner 텔레그램 → desktop-home WSL2 sora → (governor) → WSL interop / sora 도구
> **실행 상태 범례**:
> - ✅ **즉시** — WSL interop (powershell 직접) 또는 sora 기존 도구로 지금 작동
> - 🟢 **도구 있음** — sora ALL_TOOLS 에 등록된 기능 (GA4/GSC/git/ontology/RAG/calendar 등), 단 일부는 자격증명/재배선 필요
> - 🔶 **warn-then-obey** — governor 위험 분류 → 경고+권고 후 "진행" 시 실행
> - ⏸️ **배선 필요** — secondary 도구 로컬 미구현 (claude_run/docker/web 등) 또는 신규 개발

---

## A. PC 제어·상태 (✅ WSL interop 즉시)
1. 집 pc 상태 알려줘 (CPU/RAM/디스크) ✅
2. C드라이브 남은 용량 얼마야 ✅
3. 메모리 제일 많이 먹는 프로세스 top 10 ✅
4. node 프로세스 다 죽여줘 🔶
5. python 좀비 프로세스 정리해줘 🔶
6. 다운로드 폴더에 오늘 받은 파일 뭐 있어 ✅
7. D:\00.test 폴더 용량 알려줘 ✅
8. 지금 실행 중인 주요 프로그램 목록 ✅
9. temp 폴더 용량 큰 거 알려줘 ✅
10. 집 pc IP/네트워크 상태 (ipconfig) ✅
11. 집 pc 재부팅해줘 🔶 (governor WARN)
12. 특정 포트(3000 등) 누가 쓰는지 ✅
13. 휴지통 비워줘 🔶
14. 지금 몇 시야 / 오늘 며칠이야 ✅
15. 어떤 디스크가 꽉 차가고 있어 ✅

## B. SBU 운영·배포 (11 SBU)
16. 11개 SBU 사이트 다 살아있어? (헬스체크) ✅
17. kott.kr 지금 접속돼? ✅
18. ur-wrong.com 응답 정상이야? ✅
19. toolpick 프로덕션 배포해줘 🔶 (production WARN)
20. SBU sitemap 다 정상이야? ✅
21. kott 로컬 빌드 한번 돌려줘 🟢
22. reviewlab 빌드 에러 있나 확인 🟢
23. 어제 Vercel 배포 실패한 거 있어? 🟢
24. neogenesis.app 서브도메인 5개 다 떠있어? ✅
25. quant.heoyesol.kr 대시보드 살아있어? ✅
26. SBU 중에 지금 다운된 거 있어? ✅
27. heoyesol.kr 메인 정상이야? ✅
28. kott 커밋하고 배포까지 해줘 🔶

## C. 분석·지표 (GA4/PostHog/GSC)
29. 오늘 kott 방문자 몇 명이야 🟢
30. 이번주 11 SBU 총 방문자 🟢
31. toolpick 재방문율(returning) 어때 🟢
32. GA4 어제 전체 세션 수 🟢
33. PostHog 오늘 이벤트 몇 건 🟢
34. GSC 이번주 노출수/클릭수 🟢
35. 어느 SBU가 트래픽 제일 많아 🟢
36. returning users 7일/28일 🟢
37. 지난주 대비 방문자 증감 🟢
38. 검색 유입 키워드 top 10 🟢
39. CTA 클릭(전환) 추이 🟢
40. 트래픽 0인 죽은 SBU 찾아줘 🟢

## D. 개발·코드
41. neo-genesis git 상태 알려줘 ✅
42. 오늘 커밋한 거 정리해줘 ✅
43. 변경된 파일 목록 보여줘 ✅
44. 이거 커밋하고 푸시해줘 🔶 (push WARN)
45. sora_engine.py에서 governor 함수 찾아줘 ✅
46. 최근 커밋 5개 로그 ✅
47. jarvis safety 테스트 돌려줘 ✅
48. Claude한테 이 버그 고치라고 시켜줘 ⏸️ (claude_run 로컬 배선)
49. Codex한테 이 리팩터 맡겨줘 ⏸️
50. 이 파일 문법 오류 있나 확인 ✅
51. TODO/FIXME 주석 남은 거 찾아줘 ✅
52. 어제 작업한 파일 뭐였어 ✅
53. 이 함수 어디서 쓰는지 grep ✅

## E. 인프라·보안
54. Supabase RLS 비활성 테이블 있어? 🟢
55. 평문 API 키 노출 파일 스캔 (gitleaks) ✅
56. Cloudflare DNS 레코드 확인 🟢
57. Vercel 환경변수 목록 (ur-wrong) 🟢
58. GCP 활성 프로젝트 + Gemini API 상태 🟢
59. .env 파일 git 추적되는지 확인 ✅
60. 이 PC 보안 점검 ✅
61. 최근 GitGuardian/보안 알림 있어? 🟢
62. credential 만료 임박한 거 있어? 🟢
63. 의심스러운 외부 포트 열려있나 ✅

## F. 온톨로지
64. 온톨로지 validate 돌려줘 ✅
65. SBU별 매출 경로 query ✅
66. live KPI 16개 값 보여줘 ✅
67. provenance none 노드 있어? ✅
68. 어제 ActionRun 기록 ✅
69. desktop-home 디바이스 노드 상태 ✅
70. 온톨로지 competency 12개 통과해? ✅
71. 온톨로지 daily cron 돌았어? ✅

## G. 콘텐츠·SEO
72. kott 블로그 이번달 발행 몇 건 🟢
73. toolpick SEO 점검 🟢
74. "X" 주제 블로그 초안 써줘 🟢
75. 메타태그 빠진 페이지 찾아줘 🟢
76. llms.txt 최신이야? ✅
77. 키워드 cannibalization 점검 🟢
78. GSC 색인 요청 큐 상태 🟢

## H. 일정·메일
79. 오늘 일정 뭐 있어 🟢 (calendar)
80. 내일 미팅 알려줘 🟢
81. 안 읽은 중요 메일 있어? 🟢 (gmail)
82. 캘린더에 일정 추가해줘 🟢
83. 보안 관련 메일 요약해줘 🟢
84. 슈퍼센트에서 온 메일 있어? 🟢

## I. 지식·메모리·연구
85. RAG에서 "X" 검색해줘 🟢
86. 지난주 한 작업 요약해줘 ✅
87. 이거 기억해둬 (메모) 🟢
88. 내 강점/약점 뭐였지 (프로필) ✅
89. "X" 웹 검색해줘 ⏸️ (web_search 로컬 배선)
90. 최신 "X" 뉴스 찾아줘 ⏸️

## J. 자비스 자체
91. 자비스 상태 알려줘 ✅ (get_jarvis_status)
92. 오늘 자비스가 실행한 명령 ✅ (audit summary)
93. 보류 중인 위험 명령 있어? ✅
94. governor 위험 패턴 목록 ✅
95. (위험 경고 후) 진행 ✅ (confirm)
96. 자비스 재시작해줘 🔶

## K. 커리어·개인
97. heoyesol.kr 포트폴리오 살아있어? ✅
98. 슈퍼센트 입사 D-day 며칠 남았어 ✅ (2026-06-29 기준)
99. 내 GitHub 계정/도메인 알려줘 ✅ (프로필)
100. 이번주 한 일 주간 보고 만들어줘 🟢 (git+지표 종합)

---

## 라이브 검증 결과 (2026-05-29) — 도구 직접 호출 ground truth

| 카테고리 | 검증 | 결과 |
|---|---|---|
| A PC제어 | remote_pc_status / command / process | ✅ DESKTOP-HOME/Win11/25GB, 실제 실행 |
| A 날짜 | Get-Date -Format | ✅ (버그 수정 후 — 아래) |
| B SBU헬스 | 6 SBU curl | ✅ **6/6 200** |
| D git | git status/log | ✅ 실제 출력 |
| E gitleaks | which gitleaks | ✅ win 설치됨 |
| F 온톨로지 | validate.py | ✅ PASS |
| J 자비스 | get_jarvis_status / audit | ✅ DEGRADED/14패턴, audit executed3/warned7 |
| H 캘린더/메일 | secrets token | ✅ 8 token files (gcal_token/google_credentials 등) |
| **C 분석** | GA4/GSC/PostHog | 🔴 **갭** (아래) |

### 🔴 검증이 잡은 버그 2건 (수정 완료)
1. **governor format false-positive** — `\bformat\b` 가 PowerShell `-Format`/`Format-Table`/`Format-List` 오매치 → "Get-Date -Format" 이 위험 WARN. 디스크 컨텍스트만(`format C:`/`Format-Volume`/`diskpart`) 매치하도록 수정. 단위 17/17 PASS. "Get-Date -Format" → "2026-05-29" 정상.
2. **GA4 경로 Windows식** — `GA4_SERVICE_ACCOUNT_PATH=D:\00...` (WSL2 Linux 미해석) → `/app/secrets/ga4_service_account.json` 로 수정. SA 자체는 유효(project ethereal-cache).

### 🔴 분석(C 카테고리 ~12개) 실제 갭 — 100선 과대평가 정정
- **분석은 sora brain 도구(ALL_TOOLS)가 아님** — `scripts/ga4_traffic_report.py` 등 standalone 스크립트. 텔레그램 "오늘 방문자" → 라우팅할 brain 도구 없음
- **WSL2 venv 에 `google-analytics-data` 미설치** (5/29 slim venv)
- 자격증명(ga4_service_account.json)은 존재 + 경로 수정됨
- **→ 필요: (a) GA4/GSC/PostHog brain 도구 wrapper 작성 + (b) `pip install google-analytics-data google-api-python-client` + (c) PostHog HogQL 도구.** "자격증명만 확인"이 아니라 도구 배선 작업

## 실행 가능성 요약 (검증 후 정정)
| 상태 | 개수 | 의미 |
|---|---|---|
| ✅ 즉시 | ~50 | WSL interop / 검증된 도구로 지금 작동 (A/B헬스/D/E/F/J/K 다수) |
| 🔶 warn-then-obey | ~8 | 위험 분류 → 경고 후 "진행" |
| ⏸️ 배선 필요 | ~18 | **분석 C(~12)** + 개발위임/web(~6). brain 도구 wrapper + venv deps |
| 🟢 토큰 있음 미검증 | ~24 | calendar/gmail/RAG/SBU빌드 — 토큰/스크립트 존재, brain 라우팅 미검증 |

## 🟢 분석 도구 배선 완료 (2026-05-29) — C 카테고리 LIVE
- 신규 `src/core/tools/analytics_tools.py` — GA4 SBU 트래픽(REST/JWT, 무거운 SDK 불요) + PostHog DAU(HogQL). `ANALYTICS_TOOLS` → `tools/__init__.py` ALL_TOOLS 등록 (owner-relevant 상위, memory 다음)
- SBU property 맵: kott 525765817 / toolpick 524659689 / ur-wrong 524964770 / heoyesol 524705454 / 공유 526345390+host (aiforge/reviewlab 등)
- **brain e2e 라이브 (텔레그램 경로, Gemini 라우팅)**:
  - "이번주 toolpick 방문자?" → 478명/481세션/497뷰 ✅
  - "이번주 SBU 요약" → kott16·toolpick478·ur-wrong3·heoyesol21·reviewlab64 ✅
  - "오늘 PostHog DAU?" → 152명/472건 ✅
- 버그 수정: `from __future__ import annotations` 제거 (Gemini AFC isinstance 인자검증 깨짐). GA4 경로 Windows→WSL2.
- TOOLS 110개. owner "오늘/이번주 방문자" 류 daily 명령 이제 작동.

## 🟢 잔존 갭 "전부 진행" (2026-05-29) — 결과
| 갭 | 결과 |
|---|---|
| **#100 주간보고** | ✅ `get_weekly_report()` — GA4 SBU + PostHog 7일 DAU + git 커밋 + audit. brain e2e 라이브 (kott16/toolpick478/PostHog DAU 154·133·162...) |
| **claude 위임** | ✅ `claude_run`/`claude_chat` WSL interop → claude.exe (구독 $0). "2+2" → "4" 검증 |
| **web_search** | ✅ `jarvis_web_search` 무키 DuckDuckGo (lite POST). "GPT-5" → OpenAI/Wikipedia/TechCrunch 4건 |
| **gmail** | ✅ 검증 (gmail_list_unread → 0 unread, 토큰 유효) |
| **RAG** | ✅ 검증 (rag_search → 실제 문서, 로컬 chroma) |
| **calendar** | 🔴 **owner OAuth 필요** — 토큰 만료, 텔레그램 `/setup_google` 재인증 (브라우저 OAuth = 자율 불가) |
| **GSC** | 🔴 **owner OAuth 필요** — refresh token 없음 (oauth_flow.pkl만). 브라우저 OAuth 필요 |

### 자율 완료 vs owner-blocked
- ✅ **자율 완료**: analytics(GA4/PostHog) / 주간보고 / claude·codex 위임 / web_search / gmail / RAG / device 전체 / 온톨로지 / gitleaks
- 🔴 **owner OAuth 2건만 남음** (브라우저 인증 = 내가 못 함): calendar 재인증 + GSC refresh token. owner 텔레그램 `/setup_google` 또는 GSC OAuth 1회

👤 Strategy Lead Claude Opus 4.8
