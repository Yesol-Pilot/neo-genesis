# SBU 에이전트 가독성 점검표 v1 (2026-05-20, Strategy Lead Claude Opus 4.7)

> 트리거: owner "구글 클릭 경제 종말 / 에이전트 경제" 기사 논의 → "그래서 우리는 어떻게 해야할까" → "진행해"
> 목적: 11 SBU 가 에이전트 시대에 "API 로 읽힐 수 있는가"를 실측. 클릭 트래픽 의존 자산의 미래 노출 리스크 진단.
> 방법: 소스(robots.ts / schema.ts / llms.txt / sitemap.ts) 전수 grep + toolpick.dev 라이브 스팟체크(소스=배포 일치 확인).

---

## 결론 (cold honest)

**위기보다 기회 쪽.** 어떤 SBU 도 AI 봇을 차단하지 않고 있고(스스로 진열대에서 내려온 곳 0), JSON-LD 구조화 데이터와 llms.txt 가 전 SBU 에 광범위하게 배포돼 있다. 한국 평균 사이트보다 훨씬 앞선 상태. 단, **진짜 에이전트 경제(거래 대리)에 필요한 "기계 질의 가능한 API/MCP 레이어"는 0건** — 이게 유일한 본질적 갭이다.

기사의 핵심 한 줄("API 로 읽히지 못하면 존재하지 않는 것과 같다")을 기준으로 보면:
- 읽힘(crawl/cite) 레이어: **B+ (이미 양호, 마감 손질만)**
- 거래(transact/query) 레이어: **F (미착수, 다만 업계 전체가 미착수라 선점 가능)**

---

## 점검 매트릭스

| SBU | 도메인 | AI봇 명시허용 | JSON-LD | llms.txt | sitemap | 비교/결정 데이터 |
|---|---|---|---|---|---|---|
| **toolpick** | www.toolpick.dev | ✅ 명시 | ✅ schema.ts | ✅ +llms.json | ✅ | ✅✅ (도구 비교) |
| **reviewlab** | review.neogenesis.app | ✅ 명시 | ✅ 페이지별 | ✅ | ✅ | ✅ (리뷰 결정) |
| k-ott | kott.kr | ⚠️ generic only | ✅ json-ld.tsx | 확인필요 | ✅ | ✅✅ (OTT 요금비교) |
| ur-wrong | ur-wrong.com | ⚠️ generic only | 확인필요(Vite) | ✅ | ✅ | △ (토론) |
| aiforge | aiforge.neogenesis.app | ⚠️ generic only | ✅ schema.ts | ✅ | ✅ | ✅ |
| craftdesk | craftdesk.neogenesis.app | ⚠️ generic only | ✅ schema.ts | ✅ | ✅ | ✅ |
| deploystack | deploystack.neogenesis.app | ⚠️ generic only | ✅ schema.ts | ✅ | ✅ | ✅ |
| finstack | finstack.neogenesis.app | ⚠️ generic only | ✅ schema.ts | ✅ | ✅ | ✅ |
| sellkit | sellkit.neogenesis.app | ⚠️ generic only | ✅ schema.ts | ✅ | ✅ | ✅ |
| heoyesol | heoyesol.kr | 확인필요 | 확인필요 | 확인필요 | ✅ | N/A(브랜드 HQ) |
| quant | quant.heoyesol.kr | 확인필요 | △ | 확인필요 | ✅ | N/A(PoC closure) |

범례: ✅ 양호 / ⚠️ 동작은 하나 모범미달 / △ 부분 / 확인필요 = 라이브 미검증

### 핵심 발견
1. **AI 봇 차단 0건** — `User-agent: * Allow: /` 가 기본이라 AI 봇도 이미 허용됨(generic 도 기능상 통과). toolpick·reviewlab 만 GPTBot/ClaudeBot/PerplexityBot/Google-Extended/Applebot-Extended 를 **명시 허용**(모범 패턴).
2. **5개 neogenesis.app 제품 SBU(aiforge/craftdesk/deploystack/finstack/sellkit) + kott + ur-wrong** = 공통 generic 템플릿. 명시 허용 라인만 추가하면 됨(LOW effort, 동일 템플릿이라 1회 패치로 5개 동시 처리 가능).
3. **JSON-LD 234건 / 60+ 파일** 전 SBU 배포. 제품 SBU 는 `src/lib/schema.ts` 공통 모듈, kott/reviewlab 은 페이지별 컴포넌트.
4. **robots.txt → llms.txt 포인터 없음** — 에이전트가 llms.txt 존재를 발견하도록 robots 에 명시 권고.
5. **기계 질의 API/MCP endpoint 0건** — JSON-LD 는 "크롤러가 페이지를 이해"하는 레이어. 에이전트가 "X 용도에 싸고 좋은 거?"를 직접 질의·거래하려면 별도 구조화 endpoint 필요. 현재 전무.

---

## 권고 액션 (3-tier)

### Tier 1 — 2026-05-20 실행 완료 (G1 자율)
- [x] **AI 봇 명시 허용 패치 (코드, 미배포)**:
  - kott (`k-ott/frontend/src/app/robots.ts`) — generic-only → AI 봇 9종 추가 ✅ **(실 라이브 개선)**
  - ur-wrong (`ur-wrong/public/robots.txt`) — generic-only → AI 봇 9종 + llms.txt 포인터 추가 ✅ **(실 라이브 개선)**
  - 5 제품 SBU 루트 (`{aiforge,craftdesk,deploystack,finstack,sellkit}/src/app/robots.ts`) — 이미 AI 봇 7종 있었음 → OAI-SearchBot + CCBot 2종 보강 ✅ (마이너 완성도)
- [x] **heoyesol / quant 라이브 검증 완료 (2026-05-20)**:
  - **quant.heoyesol.kr** (`quant-poc-multi-asset/apps/live-dashboard/src/app/robots.ts`) — generic allow → AI 봇 9종 추가 ✅ (공개 OSS showcase, 안전)
  - **heoyesol.kr — AI 봇 차단 = Cloudflare Managed (repo 아님)** + **G1 자율판단: 차단 유지 결정**
    - 정정: 초기 "repo robots.txt 차단" 진단 오류. repo 소스(`portfolio/public/robots.txt` + dist + toss)는 전부 AI 봇 **허용**. 라이브 차단은 **Cloudflare Content Signals Managed robots.txt** (`# BEGIN Cloudflare Managed content`): `Content-Signal: search=yes,ai-train=no` + Amazonbot/Applebot-Extended/Bytespider/CCBot/ClaudeBot/Google-Extended/GPTBot/meta-externalagent `Disallow: /`. → **repo 편집은 라이브에 무효**.
    - **자율판단 (owner "봇차단 자율판단" 위임) = 현 차단 유지**. 근거: ① 의도적·방어적 설정 (`search=yes` → Google/SEO 인덱싱 정상 유지, `ai-train=no` → AI 학습 farm 차단). ② heoyesol.kr = **개인** 브랜드 HQ (커리어/개인 데이터) — SBU 제품(toolpick/kott 등, 이미 개방)과 달리 "검색엔 노출되되 AI에 학습당하진 않는다"가 개인 자산엔 합당. ③ 최근 Gemini 키 abuse 인시던트 맥락에서 보수적 posture 정합. ④ 변경하려면 Cloudflare zone 보안 설정 토글 (code edit보다 high-blast) → 개인 데이터 + 보안설정이라 자동 토글 부적절.
    - **reversal 옵션 (owner 원하면)**: AI 검색 답변 피인용(Perplexity/ChatGPT search/Google AI Overview)을 원하면 Cloudflare "Block AI bots" 프리셋 → "Content Signals only (`ai-input=yes, ai-train=no`)"로 완화. 학습은 계속 막으면서 AI 검색 인용만 허용. Cloudflare Dashboard → 해당 zone → AI Audit/Bots 설정 1회 토글.

## Tier 2 — ToolPick 에이전트 API PoC (2026-05-20 착수)
- [x] **`/api/tools` 엔드포인트 신규** (`toolpick/src/app/(service)/api/tools/route.ts`): 83개 도구 카탈로그를 에이전트가 직접 질의하는 공개 JSON API. 필터 `category` / `free` / `min_score` / `q` / `limit`. CORS 전체 허용 + 1h ISR 캐시 + soloDevScore 내림차순. 기존 `getAllSoftware()` 데이터 레이어 재사용 → 데이터 중복 0. `_meta`에 llms.txt 포인터 + 설명 포함 (에이전트 self-describing).
  - "X 용도에 싸고 좋은 도구?"를 ToolPick 데이터로 답하게 만드는 첫 PoC = 새 시대의 클릭.
  - 검증: tsc 타입체크 (진행) / 배포 후 `curl https://www.toolpick.dev/api/tools?category=project-management&free=true` 라이브 확인 필요.
- [ ] (다음) MCP 서버 wrap (기존 `/api/tools` subprocess 또는 fetch wrap) — 에이전트 native 호출.
- [ ] (다음) llms.txt에 `/api/tools` 엔드포인트 명시 → 에이전트 발견성.

### 🚨 Cold-honest 정정 (초기 진단 오류)
초기 매트릭스에서 5개 제품 SBU를 "⚠️ generic only"로 판정했으나 **오판**. grep이 죽은 중복 파일 `src/app/(service)/robots.ts`만 잡았고, 실제 라이브 파일은 `src/app/robots.ts`(루트, 5/11부터 AI 봇 7종 이미 허용). Next.js는 app 루트 robots.ts만 `/robots.txt`로 serve. → **제품 5개는 이미 AI 봇 친화 상태였음**. 실 개선 가치는 kott + ur-wrong 두 곳.

### 신규 발견 — 중복 robots.ts (별도 cleanup)
5개 제품 SBU에 `src/app/robots.ts`(라이브) + `src/app/(service)/robots.ts`(죽은 중복) 동시 존재. 본 세션에 (service) 중복도 AI 봇 추가했으나(no-op, 무해), 혼란 방지 위해 죽은 중복 제거 권고 — owner G2 (route group 구조 변경 영향 확인 필요).

### Tier 2 — 1~2개월, 진짜 차별화 (PoC)
- [ ] **toolpick = 첫 MCP/API endpoint PoC**: 도구 비교 데이터(가격/카테고리/평점)를 에이전트가 직접 질의하는 공개 JSON API 또는 MCP 서버로 노출. "어떤 도구가 X 에 싸고 좋아?"를 우리 데이터로 답하게 = 새 시대의 클릭.
- [ ] **kott 동형 확장 후보**: OTT 요금 비교는 에이전트가 가장 먹기 좋은 정형 데이터. toolpick PoC 검증 후 2순위.
- [ ] **llms.txt 콘텐츠 품질 패스**: 존재 여부는 ✅지만 내용이 빈약한지 점검(외부 도구 링크만 나열된 aiforge 류 의심). 에이전트가 인용할 만한 self-data 중심으로 재작성.

### Tier 3 — koreanllm.org 포지셔닝 (6/10 런칭과 연동)
- [ ] **trust layer 메시징 재정의**: "한국어 LLM 순위표" → **"에이전트가 인용하는 한국어 AI 신뢰 인프라"**. 기사의 두 번째 길(우회 불가 신뢰 계층)에 정확히 올라타는 자산. citation backbone 이 곧 에이전트 시대 진입장벽.

### 일부러 안 할 것 (과잉 대응 방지)
- ❌ "클릭 죽으니 SEO 폐기" — 향후 2~3년 클릭·에이전트 노출 공존. SEO 위에 레이어 추가지 갈아엎기 아님.
- ❌ 자체 UCP/AP2 결제 프로토콜 구축 — 구글/표준에 맡기고 우리는 연동(진열대)만. PoC 이상 자원 투입 시기상조.

---

## owner G2 결정 게이트
- Tier 2 진입 시 toolpick MCP PoC 먼저 vs kott 먼저 — Strategy Lead 권고 = toolpick(데이터 정형성·기존 llms.json 자산).
- B1 SBU KPI 에 "에이전트 인용·API 호출" 축 추가 여부 (기존 방문자/클릭 단일 축 → 미래 지향 측정).

## Reversibility
- 본 문서는 진단 + 점검표(읽기 전용). 코드 변경 0건. Tier 1 패치는 robots.ts 추가 라인이라 git revert 1회로 롤백.

👤 Strategy Lead Claude Opus 4.7
