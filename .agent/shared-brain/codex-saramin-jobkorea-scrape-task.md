# Codex CLI 핸드오프 — Saramin / Jobkorea JD 스크래핑 (2026-05-10)

> **위임자**: Claude (sonnet)
> **수임자**: Codex CLI
> **owner**: 허예솔
> **owner 명령**: 옵션 B 선택 (Playwright + 자동 스크래핑)

## 목적

Top 30 추천 공고 중 saramin/jobkorea = WebFetch 로그인 벽. **연차 요구사항 + 자격요건 + 우대사항 정확 추출 필요**.

## 대상 공고 6+건

### Saramin (rec_idx)
| # | 회사 | 직무 | URL |
|---|---|---|---|
| 1 | 한화시스템(주) | ICT부문 AX 대규모 채용 (AX 전략기획) | https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=53744816 |
| 2 | 이스트소프트 | [ESTsoft] AI 사업개발 + Product PM | https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=53827411 |
| 3 | 뉴셀렉트(주) | [AX센터] AI Agent Product Manager | https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=53699608 |
| 4 | 크림(주) | [KREAM] AI 검수 Product Manager | https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=53789184 |
| 5 | (주)아이벡스 | 서비스 기획자 (AI/데이터 B2BSaaS) | https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=53660693 |
| 6 | (주)카카오페이증권 | 워크플랫폼 AI Agent 기획자 (참조용 — 이미 5년+ 확인됨) | https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=53756679 |

### 추가 후보 (확인 가능 시)
- 링코스튜디오 AI 콘텐츠 Product Manager (saramin)
- 매드업 AI 프로덕트 오너(PO) (saramin)
- 리빌더에이아이 프로덕트 매니저 (saramin)
- 씨에스쉐어링 전략기획본부 AI PM (saramin + jobkorea)

### Jobkorea (Recruit GI Read)
대부분 saramin과 동일 공고. saramin이 안 되면 jobkorea로 우회 시도:
| # | 회사 | URL |
|---|---|---|
| 7 | 잡코리아/뉴셀렉트 | https://www.jobkorea.co.kr/Recruit/GI_Read/49083347 |
| 8 | 잡코리아/플레어랩스 | https://www.jobkorea.co.kr/Recruit/GI_Read/49075740 |

## 추출 필드 (각 공고당)

```json
{
  "rec_idx": "53744816",
  "company": "한화시스템(주)",
  "title": "한화시스템 ICT부문 AX 대규모 채용 (AX 전략기획)",
  "years_required": "관련 업무경력 X년 이상" 또는 정확 인용,
  "years_min": 정수 또는 null,
  "years_max": 정수 또는 null,
  "required_qualifications": ["..."],
  "preferred_qualifications": ["..."],
  "english_required": true/false,
  "english_quote": "정확 인용 또는 null",
  "b2c_b2b": "B2C" | "B2B" | "혼합",
  "deadline": "YYYY-MM-DD" 또는 "채용 시 마감",
  "work_location": "...",
  "credit_check_required": true/false (특히 금융권),
  "fetched_at": "ISO timestamp"
}
```

## 시도 순서 (Codex 자율)

### Step 1: 비로그인 직접 접근 시도
일부 saramin 공고는 비로그인 상태에서도 본문 일부 보임. 시도:
- `playwright` 또는 `requests` + `BeautifulSoup`
- User-Agent: `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36`
- Referer: `https://www.saramin.co.kr/`
- 본문 selector: `.user_content`, `.cont`, `.recruit-detail`, `.wrap_jview`

### Step 2: 모바일 URL 우회
saramin 모바일 (`m.saramin.co.kr`) 또는 jobkorea 모바일 (`m.jobkorea.co.kr`) 접근 시도.

### Step 3: Google 캐시 / Wayback Machine
- `https://webcache.googleusercontent.com/search?q=cache:{URL}`
- `https://web.archive.org/web/*/{URL}`

### Step 4 (최후): 사용자 saramin/jobkorea 로그인 ID/PW 요청
위 3단계 모두 실패 시:
- `D:/00.test/jobsearch/.env`에 다음 추가 요청:
  ```
  SARAMIN_USER_ID=<owner_input>
  SARAMIN_USER_PW=<owner_input>
  JOBKOREA_USER_ID=<owner_input>
  JOBKOREA_USER_PW=<owner_input>
  ```
- Playwright headless로 로그인 → 공고 페이지 접근 → 추출

## 출력

```
D:/00.test/jobsearch/data/v3/saramin_jobkorea_jds_v1.json
```

각 공고당 위 schema. 모든 6건 시도 완료 후 저장.

## 차단 시 대처

| 차단 | 대처 |
|---|---|
| Saramin 로그인 벽 + 우회 안 됨 | 사용자에게 `.env`에 ID/PW 추가 요청 (옵션 4) |
| Jobkorea 동일 | jobkorea 로그인 정보 요청 |
| Captcha | 사용자 직접 처리 (Codex 자동화 불가) |
| 공고 마감 (페이지 404) | 결과에 `status: closed` 표시, 다음 공고 진행 |
| Bot detection (User-Agent 차단) | 다양한 User-Agent rotation, 5초 sleep, 단 saramin ToS 위반 X 범위 내 |

## 절대 하지 말 것

- ❌ saramin/jobkorea ToS 위반하는 대량 자동 요청 (rate limit 5-10초 sleep 필수)
- ❌ 사용자 사전 동의 없이 ID/PW 환경변수 기록
- ❌ 추출한 JD 본문을 외부 publish/공유
- ❌ 잘못 추출한 데이터로 환각 ("연차 미상" 솔직히 표시)

## 완료 보고

성공 시 `.agent/shared-brain/handoff.md`에 reverse handoff:
```
## Codex → Claude 완료 (saramin scraping)
- 6건 중 X건 성공 / Y건 실패
- 결과: jobs_with_real_years.json
- 차단: ...
```

## 참조

- 마스터 자격증명 SSOT: `~/.neo-genesis/credentials.env` (대부분 비어있음, saramin = 미설정)
- 이전 잡서치 코드: `D:/00.test/jobsearch/src/acquisition/saramin.py` (참고용)
- 사용자 본업 saramin 계정: 미보유 추정 (로그인 정보 X)

---

**Claude는 동시에 비금융 IT Top 12 자기소개서 작성 준비 진행 중**. saramin 결과는 자기소개서에 추가 fit 정보로 활용.
