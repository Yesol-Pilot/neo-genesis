# @leftaino 팔로우 성장 — Codex 즉시 실행 스펙 (기획·설계·구현·감사)

작성: 2026-06-10 Claude (owner 지시: "코덱스가 바로 실행할 수 있도록 완벽한 방향으로 기획·설계·구현·감사까지")
상위 문서: `FOLLOWER_GROWTH_REDESIGN_20260609.md`(설계 원본, 이하 REDESIGN) — 본 스펙은 그 설계를 **실측 데이터로 보정**하고 **실행 단위로 분해**한 최종본. 충돌 시 본 스펙 우선.
근거 데이터: `output/tiktok_aino_performance_reports/performance_report_20260610_154723.json`(35행 포렌식) + `performance_feedback.json` + `follower_analytics_snapshot_20260609.json`. 4각도 분석 전문: `D:\005.output\tmp\claude\D--00-test\f2596fb6-4a7f-484a-98c5-b131c42a8555\tasks\wzr4gy519.output`.

---

## 0. 미션 한 줄

조회수가 아니라 **프로필 전환(0.1%→0.8%)과 팔로우 전환**을 만드는 구독형 채널로 전환한다. 죽는 포맷을 멈추고, 검증된 포맷에 슬롯을 몰고, 측정을 실험보다 먼저 깐다.

## 1. 실측 근거 (이 표가 모든 결정의 근거)

| 사실 | 수치 | 함의 |
|---|---|---|
| 7일 조회 2K, 프로필 조회 2 (전환 0.1%) | follower snapshot 6/9 | 병목 = 조회수가 아니라 프로필 전환 |
| 추천 92.6% / 팔로잉 0.1% | 〃 | 일회성 소비, 구독 관계 0 |
| 시청자 55+ 85.8%, 여성 58%, KR 86.9%, 최활동 08시 | 〃 | 타깃 보정: 큰 자막·직접 판정·아침 슬롯 |
| 보도제목 인용형: 중앙뷰 84, 좋아요 0~1, 댓글 0 | 6/10 롤업 | **즉시 폐기** |
| "X, 왜 ~나?" 질문 템플릿 15편(생산량 54%): 평균 178뷰 박스 | 〃 | 템플릿 피로 — 중단 |
| 정서 서사("조국의 겨울") 738뷰·좋아요율 3.5% / 랭킹 392 / 숫자도발 질문 338 | 〃 | 살릴 포맷 |
| 레거시: 1인칭 고백 35K(좋아요율 14.8%, 댓글 902) / 랭킹 116K / 결집문장 좋아요율 24.2% | 고정 3 | 팔로우 전환 자산의 원형 |
| 명사구/선언 훅 평균 299뷰 > 질문 훅 172뷰 (1.7배) | 〃 | 훅 기본값 = 선언 |
| feedback 양(+): 정치·함께·사람·당신·이재명·대한민국·역대 / 음(−): 이슈·사안·핵심·단정·확인된·국회 | performance_feedback.json | 어휘 가이드 |

프로필(이름·bio·고정3) 단장은 2026-06-10 Claude가 적용 완료 — 본 스펙 범위 아님. 아바타 1건만 잔여(owner 수동, memory 참조).

## 2. 변경 원칙 (죽일 것 / 살릴 것)

**죽인다**: ① "○○ 보도 제목 기준:" 인용형 전면 폐기(훅·본문·캡션 모두) ② "X, 왜 먹히나/흔들리나?" 템플릿 ③ 양쪽 다 열어두는 중립 화법("~일 수도, ~일 수도") ④ 음(−) 어휘(이슈/사안/핵심/단정/확인된/국회)를 훅·캡션 첫 문장에 쓰는 것.

**살린다(주간 믹스)**: 랭킹/판정형 2 + 1인칭·정서 서사형 2 + 개량 해설형 1~2(선언 훅 + 입장 명시 + 책임선 + 정서 결말). `accountability_briefing`(인용형 직계)은 **주 2~3회 이하로 축소·리모델** — REDESIGN §6의 "매일 1슬롯 briefing" 배분을 본 스펙이 명시 변경한다(현 규모에서 Creator Rewards 명분 시기상조, §1 실측 근거).

**훅 규칙**: 기본 = 명사구/선언("조국의 겨울," / "12대4."). 질문 훅은 **숫자+당파적 펀치가 있을 때만**("12대4, 이걸 아직도 우연이라 부르나?"). 첫 3초에 인물명 또는 쟁점명 필수(55+ 가독: 훅 ≤16자, 본문 줄당 11~14자 — REDESIGN §7 유지).

## 3. 구현 작업 (T1~T7, 순서대로. 각 작업 = 변경→검증→다음)

> 모든 config 는 `src/core/tiktok_aino/config/` 아래 실재 파일. **키 이름은 단정하지 않는다** — 각 작업의 "탐색" 지시대로 현재 스키마를 먼저 읽고 그 구조에 맞춰 추가/수정할 것(거짓 키 발명 금지). 모든 변경은 git 단위 커밋 + 기존 pytest 회귀.
>
> **앵커 감사 결과 (2026-06-11, grep 전수 검증)**: `format_router.json` 키 = `routing_rules`+`blockers` / `publish_quality_strategy.json` 키 = `search_value`·`safe_provocation`·`policy_gate`·`content_review`·`rendering`·`script_quality` / `cta_patterns.json` 키 = `cta_patterns`+`forbidden_cta` / `monitoring_strategy.json` 키 = `windows`·`score_weights`·`metric_aliases`·`response_rules`·`reporting` / `planning_strategy.json` 에 `rolling_schedule`·`narrative_arc_by_format` 실재 / `pipeline.py` pinned_comment 참조 = lines 840·1304·4440·4465·4748 / 롤업 자동화 앵커 = `schedule_planner.py`. T1~T7 의 모든 파일 앵커 실재 확인됨.

### T1. 보도제목 인용형 폐기 (P0)
- 탐색(감사 검증 완료, 2026-06-11): "보도 제목" 류 문자열의 실제 위치 = **`config/hot_topic_strategy.json`·`config/planning_strategy.json`·`config/script_strategy.json` + `pipeline.py`(생성 경로)**. format_router.json·hook_patterns.json 에는 해당 문자열 없음 — 거기서 찾지 말 것.
- 변경: ① 위 3 config + pipeline.py 의 해당 포맷/훅 패턴을 라우팅·생성 후보에서 제거(또는 weight 0 + deprecated 표기) ② **critical blocker** 추가: 생성 산출물의 훅/캡션에 `보도 제목 기준` 또는 `뉴스 보도 제목` 문자열 포함 시 publish 차단(blocker id 예: `headline_quote_format_banned`). 위치는 `format_router.json`의 기존 `blockers` 배열 또는 `publish_quality_strategy.json`의 `policy_gate`/`content_review` 구조 중 게이트 실행 경로에 실제로 물리는 쪽(둘 다 실재 키 — 감사 확인).
- 수락 기준: 해당 문자열이 포함된 fixture로 게이트를 돌리면 차단되고, 기존 정상 fixture는 통과. 회귀: 관련 pytest 전부 green.

### T2. "X, 왜 ~나?" 질문 템플릿 중단 (P0)
- 탐색: hook_patterns/script_strategy에서 `왜 먹히나|왜 흔들리나|왜 ~나` 계열 템플릿.
- 변경: 템플릿 비활성 + quality gate에 **soft blocker**(같은 훅 골격 7일 내 2회 이상 재사용 시 차단 — 템플릿 피로 방지 일반 규칙으로 구현 가능하면 그쪽 우선).
- 수락 기준: 신규 스케줄 플랜 7일치 시뮬레이션에서 해당 훅 골격 0건.

### T3. 슬롯 믹스 재배분 (P0)
- 탐색: `planning_strategy.json`·`hot_topic_strategy.json`·`schedule_planner.py`의 슬롯/포맷 배분 로직.
- 변경: 주간 목표 믹스 = `ranking_battle 2 / narrative_confession 2 / reformed_briefing 1~2` (§4 포맷 스펙). REDESIGN §9 주제 점수표(정체성 20·댓글충돌 15·시리즈 15·검색 15, 60점 미만 생성 금지)는 그대로 채택하되, **briefing 계열에는 일일 상한(주 3회) 추가**.
- 수락 기준: `schedule_planner` 3일 플랜 산출물에서 믹스 비율이 목표와 일치(briefing ≤ 1/일·3/주).

### T4. 캡션 CTA 게이트 — REDESIGN 핵심결함 2 해소 (P0)
- 문제(원본 문서 명시): 품질 점수는 `pinned_comment`의 팔로우 문구를 반영하지만 실제 업로드 job은 `caption/post_title/hashtags`만 전달 → 시청자에게 CTA가 안 보임.
- 변경: ① `pipeline.py` 점수 산식에서 pinned_comment 가중 → caption 내 CTA 존재 기준으로 교체(REDESIGN §11 그대로) ② `upload_automation.py`에 업로드 직전 검증: caption에 팔로우 CTA(시리즈 약속형: "팔로우하면 다음 ○○도 이어갑니다" 계열) 부재 시 **blocker `caption_follow_cta_missing`** ③ CTA 문구는 `cta_patterns.json`에 시리즈 약속형 3종 이상 등록(조작적 보상 약속 금지 — §5 가드).
- 수락 기준: CTA 없는 캡션 fixture → 차단 / 있는 fixture → 통과. 기존 publish_queue_runner 테스트(14개) green 유지.

### T5. 검증된 레퍼런스 문법 production 연결 — REDESIGN 핵심결함 3 해소 (P1)
- 변경: `reference_patterns.json`의 `large caption + actor/issue keyword + real context scene + CTA` 문법을 `format_router.json` 기본 경로로 연결(REDESIGN §11). `scene_type_library.json`의 금지 패턴 6종(동일 어두운 종이·복도 반복 등, §7) 활성 확인.
- 수락 기준: 신규 렌더 1건 dry-run에서 장면 타입이 reference 문법을 따르고 금지 패턴 0.

### T6. 측정 선행 — 실험 판정 가능 상태 만들기 (P0, T7보다 먼저)
- 문제: 실험 합격 기준 지표(`profile_views/views`, `followers_gained/views`)가 현재 **미수집**.
- 변경: ① Studio capture 확장 — 일일 23:30 롤업 시 `analytics/overview`의 profile_views·followers와 게시물별 지표를 스냅샷에 포함(기존 `current_studio_visible_rows_*` 캡처 경로 확장; 게시물별 분해가 Studio UI상 불가하면 **일 단위 계정 레벨로 수집하고 그 한계를 리포트에 명시** — 거짓 분해 금지) ② `monitoring.py`·`monitoring_strategy.json`에 `profile_conversion = profile_views/views` 지표·임계(7일 0.8% 목표) 추가 ③ 23:30 롤업이 6일 끊겼던 전철 방지: 롤업 실행을 자동화(기존 스케줄 체계에 등록)하고 누락 시 다음 실행에서 `rollup_gap_detected` 경고를 리포트에 박을 것.
- 수락 기준: 1회 롤업 산출물에 profile_conversion 필드가 실값 또는 명시적 `not_capturable` 로 존재. 날조 금지.

### T7. 7일 실험 가동 (T1~T6 완료 후)
- REDESIGN §13의 21실험 설계를 채택하되 초기 배분은 본 스펙 §2 믹스. 합격 기준: 24h 500뷰+ 평균, 반응률 8%+, profile_conversion 0.8%+ (REDESIGN §4 표).
- 판정 룰: `followers_gained`(또는 proxy: 일일 팔로워 증분) 높은 포맷의 다음 주 비중 2배 / 미달 포맷 제거. `metric_missing` 인 실험은 성과 판정에서 제외하고 재실행.

## 4. 포맷 스펙 3종 (생성 프롬프트/구성에 그대로 반영)

### 4a. `ranking_battle` (랭킹/판정형 — 116K 원형)
- 구성: 선언 훅("역대 ○○ TOP5.") → 기준 선언(민주주의·책임·위기회복 등 2~3개) → 순위 공개(5→1 역순, 항목당 1장면) → 엔딩 질문("당신의 1위는? 댓글로") + 시리즈 약속 CTA.
- 길이 45~75초. **캡션에 순위 결과 스포일러 금지**(궁금증=시청 지속 엔진. 6/9 TOP5 캡션이 1~5위를 전부 적은 것이 반례). 변주: 대통령 외 사건·연설·장면·프레임 랭킹.

### 4b. `narrative_confession` (1인칭·정서 서사형 — 35K/902댓글 원형)
- 구성: 고백 훅("나는 ○○를 처음엔 ―") → 전환점 서사(구체 장면 2~3) → 입장 선언 → **결집 문장 엔딩 1줄**(좋아요율 24.2% 검증: "거짓은 무너지고 진실은 남습니다" 계열 신규 변주) + 팔로우 CTA.
- 길이 50~80초. 양(+) 어휘(사람·함께·당신·나는) 우선. 주 2회 중 1회는 "조국의 겨울"형 3인칭 정서 서사 허용.

### 4c. `reformed_briefing` (개량 해설형 — 기존 briefing 리모델)
- 구성: 선언/숫자도발 훅(보도 인용 금지) → 확인된 사실 2개(출처는 **음성·자막 본문에서 자연 언급**, "보도 제목 기준:" 패턴 금지) → 보수 반론 1개 → **입장 명시 결말**("판단 기준은 ○○입니다") + 책임선 질문.
- 길이 65~90초(검색·1분+ 자산 유지). 주 2~3회 한정.

공통: AI 고지 유지("생성형 이미지·AI 음성 활용"), 첫 3초 인물/쟁점명, 자막 가독(훅 ≤16자), CTA 3중(영상 끝 2초 + 캡션 + 고정댓글), 댓글 운영 — 게시 후 24h 내 상위 댓글 3개에 크리에이터 답글(55+는 댓글로 관계 맺음. 자동화 불가 시 수동 운영 항목으로 보고만).

## 5. 가드 (위반 시 작업 중단 — 협상 불가)

1. 선거 절차/결과/후보 자격에 대한 미확인 주장 금지, 투표 오정보 금지 (TikTok Integrity 정책).
2. AI 생성물 고지 유지(캡션 + AIGC 라벨 경로).
3. 조작적 engagement 금지: 허위 보상 약속·업보트성 유도 금지. CTA는 "다음 편/후속 추적 약속"만.
4. 자극성은 판단 기준을 선명하게 만드는 장치까지만 — 혐오·인신 모욕 콘텐츠 금지.
5. 거짓 메트릭/거짓 분해 금지: 수집 불가 지표는 `not_capturable` 로 정직 표기.
6. 외부 공개 행위(신규 채널 게시 외 다른 플랫폼 게시·계정 설정 변경)는 owner 승인 게이트 유지.

## 6. 감사 (Codex 자가검증 — 완료 선언 전 의무)

**A. 기계 검증**
- [ ] 관련 pytest 전체 green (`tests/core/test_tiktok_aino_*` — 최소: publish_queue_runner 14, tts/render 스위트)
- [ ] `python -m compileall src/core/tiktok_aino` 통과
- [ ] config JSON 전부 `python -m json.tool` 파싱 통과
- [ ] 차단 fixture 2종(인용형 훅 / CTA 누락 캡션) → 게이트가 실제로 차단함을 로그로 증빙

**B. 산출물 검증**
- [ ] 신규 3일 스케줄 플랜: 믹스 비율 §2 일치, "보도 제목 기준" 0건, "왜 ~나" 템플릿 0건
- [ ] 첫 렌더 1건 publish_ready + 캡션에 CTA 존재 + AI 고지 존재
- [ ] 롤업 1회: profile_conversion 필드 존재(실값 또는 not_capturable)

**C. cold-grill 질문 (전부 답해야 DONE)**
- [ ] "이 변경으로 죽는 기존 기능은?" (예: briefing 의존 테스트/수익화 가정) — 영향 명시했는가
- [ ] "점수는 올렸는데 시청자에게 안 보이는 요소가 또 있는가?" (핵심결함 2의 일반화 점검)
- [ ] "실험 7일 후 무엇으로 합격/불합격을 판정하는가?" — 지표가 실제로 수집되는가
- [ ] 완료 보고에 측정 한계(게시물별 팔로우 전환 분해 불가 등)를 정직하게 적었는가

**완료 보고 위치**: `.agent/shared-brain/daily-log.md` + active-tasks.md (T1~T7 체크박스 + 증빙 경로). 첫 주 실측은 23:30 롤업 리포트로 자동 누적.

## 7. 하지 말 것 (스코프 밖)

- 프로필(이름/bio/고정) 재변경 — 이미 적용됨, 이름은 6/17까지 잠금.
- 신규 플랫폼 확장, 광고/프로모션 집행, 계정 설정 변경.
- 고성과 미검증 가설로 4번째 신규 포맷 발명(7일 실험 결과 전까지 3종 고정).
