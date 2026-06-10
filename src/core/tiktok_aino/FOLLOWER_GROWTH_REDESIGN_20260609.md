# 올바른 AiNo 팔로우 성장 재설계

작성일: 2026-06-09 KST  
채널: `올바른 AiNo` / `@leftaino`  
상위 기준: `WORKFLOW_DESIGN_SPEC.md`, `PIPELINE_DESIGN.md`, `REFERENCE_BASED_CONTENT_ARCHITECTURE_20260528.md`  
상태: 상세 설계안. 구현 전 이 문서를 기준으로 JSON config와 코드 변경 범위를 확정한다.

## 1. 결론

현재 병목은 팔로우 버튼 전환 이전이다. 최근 7일 Studio 기준 조회수는 약 2K인데 프로필 조회가 2회뿐이다. 프로필 전환율이 약 0.1%라, 팔로우가 늘 수 없는 구조다.

핵심 결함은 세 가지다.

1. 콘텐츠가 추천 피드에서 멈추게는 해도 계정을 팔로우해야 할 이유를 반복 학습시키지 못한다.
2. 품질 점수는 `pinned_comment`의 팔로우 문구를 크게 반영하지만, 실제 업로드 job은 `caption`, `post_title`, `hashtags`만 전달한다.
3. 레퍼런스 QA에서 검증된 `large caption + actor/issue keyword + real context scene + CTA` 문법이 production router에 아직 연결되지 않았다.

새 설계의 목표는 `조회수 증가`가 아니라 `조회 -> 프로필 이동 -> 팔로우 -> 다음 영상 재방문`을 만드는 구독형 숏폼 운영이다.

## 2. 현재 증거

### 2.1 최신 계정/Studio 스냅샷

근거 파일:

- `output/tiktok_aino_performance_reports/profile_snapshot_leftaino_20260609.json`
- `output/tiktok_aino_performance_reports/analytics_snapshot_20260609.json`
- `output/tiktok_aino_performance_reports/follower_analytics_snapshot_20260609.json`
- `output/tiktok_aino_performance_reports/current_studio_visible_rows_20260609.json`

확인값:

| 항목 | 값 | 해석 |
| --- | ---: | --- |
| 팔로워 | 3,439 | 기존 팬층은 존재한다. 신규 전환이 문제다. |
| 최근 7일 조회수 | 2K | 노출 자체도 약하지만 치명 병목은 프로필 전환이다. |
| 최근 7일 프로필 조회 | 2 | 팔로우 가능 모수 자체가 없다. |
| 최근 7일 팔로워 변화 | -1 | 신규 획득보다 이탈/정체가 크다. |
| 트래픽 추천 비중 | 92.6% | 팔로잉 기반 소비가 아니라 추천 피드 일회성 소비다. |
| 검색 비중 | 7.3% | 검색가치가 충분한 시리즈 클러스터가 아직 약하다. |
| 팔로워 55+ | 85.8% | 실제 타깃은 18~49보다 55+ 진보 성향 시청자에 가깝다. |
| 한국 비중 | 86.9% | 국내 정치/시사 문법 최적화가 맞다. |

### 2.2 고성과 게시물 공통점

Studio 목록에서 확인된 상위 게시물:

| 게시물 | 조회 | 좋아요 | 댓글 | 공통점 |
| --- | ---: | ---: | ---: | --- |
| 대한민국 역대 대통령 재평가 | 116K | 2,056 | 322 | 순위/역사/판정/댓글 질문/팔로우 문구 |
| 나는 이재명을 처음엔 좋아하지 않았다 | 35K | 5,189 | 902 | 개인 고백형 훅/이재명 중심/진영 정체성 |
| 거짓은 무너지고, 진실은 남습니다 | 9,905 | 2,394 | 136 | 짧은 결집 문장/팔로우 CTA/함께 지키는 정체성 |

`performance_feedback.json`의 양의 신호는 `정치`, `함께`, `사람`, `당신`, `대선`, `이재명`, `이재명지지`, `대통령`, `대한민국`, `역대`다.

음의 신호는 `이슈`, `사안`, `핵심`, `단정`, `확인된`, `국회`, `교육`, `노동`, `보기`, `다시` 등이다. 최근 예약 콘텐츠는 이 음의 문법을 많이 쓴다.

## 3. 외부 플랫폼 제약

공식 TikTok 기준으로 설계에 반영할 제약은 다음이다.

- Creator Rewards는 직접 제작한 고품질 원본 콘텐츠와 1분 이상 영상을 요구하고, 5초 초과 qualified view, 커뮤니티 가이드라인 준수를 요구한다.  
  Source: https://support.tiktok.com/en/business-and-creator/creator-rewards-program/creator-rewards-program
- For You 추천은 사용자 반응, 캡션/해시태그/사운드 같은 영상 정보, 완주 여부를 중요 신호로 본다. 팔로워 수 자체는 직접 추천 신호가 아니다.  
  Source: https://newsroom.tiktok.com/en-us/how-tiktok-recommends-videos-for-you
- Creator Search Insights는 검색 수요와 content gap topic을 창작 전략에 반영하도록 설계돼 있고, search value는 Creator Rewards와도 연결된다.  
  Source: https://newsroom.tiktok.com/creator-search-insights?lang=en
- 현실적인 AI 이미지/영상/오디오는 AI 생성 표시가 필요하다.  
  Source: https://support.tiktok.com/en/using-tiktok/creating-videos/ai-generated-content
- 선거/시민 절차 오정보, 미확인 선거 결과, 조작적 engagement, spam, 대량 자동 계정 운영, paid political promotion은 금지 또는 FYF 부적합 리스크다.  
  Source: https://www.tiktok.com/community-guidelines/en/integrity-authenticity/

설계 원칙:

- 정치 해설은 가능하지만 투표 절차/선거 결과/후보 자격 미확인 주장은 차단한다.
- 자극성은 댓글 유도용 조작이 아니라 판단 기준을 선명하게 만드는 장치로 제한한다.
- AI 실사 이미지는 `해당 이미지는 생성 이미지입니다` 또는 TikTok AIGC label 경로로 표시한다.
- 팔로우 유도는 허위 보상이나 조작적 약속이 아니라 다음 편/후속 추적 약속이어야 한다.

## 4. 목표 KPI

팔로우 성과는 단일 지표가 아니라 단계별 전환으로 본다.

| 단계 | 지표 | 현재 판단 | 7일 목표 | 30일 목표 |
| --- | --- | --- | --- | --- |
| 노출 | views/post | 최근 약함 | 게시 24h 내 500+ 평균 | 게시 24h 내 1,500+ 평균 |
| 정지 | 5초 이상 조회/초반 이탈 | 미수집 | Studio capture 추가 | 포맷별 기준선 확보 |
| 반응 | like+comment+share/views | 고성과는 강함, 최근은 약함 | 8%+ | 12%+ |
| 프로필 전환 | profile_views/views | 약 0.1% | 0.8%+ | 1.5%+ |
| 팔로우 전환 | followers_gained/views | 게시물별 미수집 | 수집 가능 상태 | 0.2%+ |
| 반복 소비 | following traffic | 0.1% | 0.5%+ | 2%+ |

합격 기준은 `조회수만 높은 영상`이 아니라 `profile_views/views`와 `followers_gained/views`가 같이 오르는 영상이다.

## 5. 새 포지셔닝

### 5.1 한 줄 정의

`진보 지지층이 저장하고, 공유하고, 댓글에서 기준을 놓고 맞붙게 만드는 영화적 정치 판정 채널`

### 5.2 팔로우할 이유

시청자는 이 계정을 팔로우하면 다음을 얻어야 한다.

1. 보수/우파 프레임에 대한 빠른 대응 기준.
2. 이재명/민주진영 이슈의 유리한 해석 프레임.
3. 특검/재판/지지율/대통령 평가/정당 갈등을 짧게 정리한 시리즈.
4. 댓글에서 바로 쓸 수 있는 한 줄 논리.
5. 매일 같은 시간에 올라오는 반복 코너.

### 5.3 실제 타깃 보정

기존 목표가 18~49였더라도, 현재 계정의 실제 팔로워는 55+가 압도적이다. 따라서 제작 기준은 다음으로 바꾼다.

- 자막은 더 크고 짧게.
- 은유보다 직접 판정.
- MZ 밈보다 역사/정의/민주주의/책임/사람/국민/선택 같은 단어.
- `뭘 말하려는지 모르겠는 해설` 금지.
- 첫 3초 안에 인물명, 쟁점명, 판정 질문이 보여야 한다.

## 6. 콘텐츠 포맷 재설계

하루 3개는 같은 템플릿으로 만들지 않는다. 각 슬롯은 서로 다른 역할을 가진다.

| 슬롯 | 포맷 | 목적 | 길이 | 핵심 |
| --- | --- | --- | --- | --- |
| 08:10 | `identity_rally_short` | 팔로우 획득 | 35~50초 | 이재명/노무현/민주주의/지키는 사람들 |
| 11:20 | `accountability_briefing` | 검색/수익화 | 65~90초 | 특검/재판/검찰/국힘 책임선 |
| 19:30 | `ranking_battle_or_comment_war` | 댓글/공유 | 45~75초 | 순위, TOP5, 양자택일, 반론 유도 |

### 6.1 `identity_rally_short`

목적: 추천 피드에서 팔로우 이유를 직접 만든다.

구조:

1. 0~2초: 정체성 훅. `이재명은 왜 아직도 강한가`
2. 2~8초: 감정 선언. `사람들이 지키려는 건 한 사람이 아니다`
3. 8~22초: 이유 3개. `민생`, `버텨낸 시간`, `상대 프레임`
4. 22~36초: 반론 선제. `우파는 팬덤이라 말하겠지만`
5. 36~45초: 팔로우 약속. `팔로우하면 민주진영 프레임을 매일 정리합니다`

제목 예:

- `이재명 지지층이 아직 뜨거운 이유`
- `노무현과 이재명, 왜 같이 소환될까`
- `우파가 싫어하는 건 이 장면입니다`

### 6.2 `accountability_briefing`

목적: 1분 이상, 검색가치, 원본 해설, 보상 적합성.

구조:

1. 0~3초: 책임선 질문. `김건희 특검, 어디까지 올라가나`
2. 3~10초: source card. 보도 제목/기관/일자 요약.
3. 10~25초: 확인된 사실.
4. 25~40초: 보수 반론.
5. 40~55초: 빠진 질문.
6. 55~75초: 민주진영 관점의 판정 기준.
7. 75~90초: 다음 편 팔로우 약속.

제목 예:

- `김건희 특검, 진짜 쟁점은 이겁니다`
- `윤석열 조사 이후 남는 질문 3개`
- `검찰개혁, 우파가 숨기고 싶은 기준`

### 6.3 `ranking_battle_or_comment_war`

목적: 댓글과 공유. 기존 계정의 `역대 대통령 순위` 고성과 패턴을 확장한다.

구조:

1. 0~2초: 순위/대결 훅. `역대 대통령 TOP5, 다시 매기면?`
2. 2~10초: 기준 공개. `민주주의`, `민생`, `위기 대응`
3. 10~45초: 5위부터 2위까지 빠른 전개.
4. 45~60초: 1위 공개 또는 논쟁 유도.
5. 60~70초: 댓글 선택지. `1 노무현 2 이재명 3 김대중`
6. 마지막: 다음 순위 예고와 팔로우 약속.

제목 예:

- `좌파 기준 역대 대통령 TOP5`
- `노무현 vs 이재명, 1위는 누구인가`
- `우파가 인정 못 할 대통령 순위`

## 7. 장면/이미지 설계

기존 실패는 이미지가 배경처럼만 쓰인 점이다. 새 설계에서는 각 장면이 `증거`, `갈등`, `감정`, `선택` 중 하나의 역할을 가져야 한다.

### 7.1 장면 유형

| 유형 | 쓰임 | 이미지 지시 |
| --- | --- | --- |
| `real_context_scene` | 특검/재판/국회/기자회견 | 실제 보도 현장처럼 보이는 복도, 브리핑룸, 법원 앞, 취재진 실루엣 |
| `symbolic_but_specific` | 민주주의/역사/기억 | 촛불, 노란 리본, 투표함 등 단, 반복 남발 금지 |
| `ranking_stage` | 대통령 순위/비교 | 어두운 스튜디오 테이블, 인물 실루엣 없는 명패/연대표 |
| `comment_choice_scene` | 댓글 유도 | 1/2/3 선택 패널을 영상 자막으로 렌더링 |
| `aino_presenter_scene` | 채널 정체성 | AiNo 진행자 실사풍 캐릭터, 단정한 스튜디오/뉴스룸 느낌 |
| `receipt_scene` | 근거/숫자 | 문서 더미가 아니라 출처 카드, 숫자, 타임라인을 편집 레이어로 제공 |

### 7.2 금지 패턴

- 모든 영상이 같은 어두운 종이/복도/마이크/파일 장면.
- 이미지 안 종이에 긴 본문을 넣는 방식.
- 실존 인물 얼굴 생성.
- 정당 로고 생성.
- 가짜 방송 화면/가짜 기사 캡처.
- 주제와 무관한 상징 이미지 반복.

### 7.3 화면 텍스트 원칙

- 첫 화면 핵심 문구: 16자 이내 권장, 최대 22자.
- 본문 자막: 한 줄 11~14자, 2줄 원칙.
- 55+ 시청자 기준으로 작은 설명문 금지.
- `source_card`는 작게라도 3~10초 사이에 노출.
- 마지막 CTA는 영상 내 자막과 캡션 둘 다에 있어야 한다.

## 8. CTA/팔로우 전환 설계

### 8.1 팔로우 CTA 위치

팔로우 문구는 세 곳에 있어야 한다.

1. 영상 마지막 2초.
2. 실제 TikTok 업로드 캡션 본문.
3. 가능할 경우 고정 댓글.

현재 결함은 2번이다. 품질 점수는 고정댓글을 보지만 업로드 job은 고정댓글을 전달하지 않는다.

### 8.2 CTA 문구 템플릿

금지:

- `팔로우 안 하면 손해`
- `좋아요 누르면 복 받음`
- 허위 보상/협박/조작적 engagement

허용:

- `팔로우하면 이 프레임 다음 편에서 이어갑니다.`
- `팔로우하면 특검 흐름을 매일 정리합니다.`
- `이 기준이 맞다면 저장하고, 다음 순위도 팔로우로 확인하세요.`
- `댓글 1/2/3으로 남기면 다음 편에서 반론까지 다룹니다.`

### 8.3 새 품질 게이트

`follower_conversion`은 다음을 모두 봐야 한다.

| 체크 | 현재 | 변경 |
| --- | --- | --- |
| `pinned_comment` 팔로우 문구 | 있음 | 보조 점수만 인정 |
| `caption` 팔로우 문구 | 약함 | 필수 |
| 영상 마지막 CTA | 불확실 | 필수 |
| 시리즈 약속 | 약함 | 필수 |
| 프로필 이동 이유 | 없음 | 필수 |

새 blocker:

- `caption_follow_cta_missing`
- `video_end_follow_promise_missing`
- `series_identity_missing`
- `profile_transition_trigger_missing`

## 9. 주제 선정 재설계

주제는 `핫한 정치 이슈`가 아니라 아래 질문을 통과해야 한다.

### 9.1 주제 선정 질문

1. 좌파 지지층이 보면 분노/자부심/방어 욕구 중 하나가 생기는가?
2. 우파 또는 반대 진영이 댓글로 반박할 명분이 있는가?
3. 인물명/기관명/숫자/판결/특검/지지율처럼 즉시 보이는 키워드가 있는가?
4. 55+ 팔로워가 바로 이해할 수 있는가?
5. 1분 이상으로 늘렸을 때 검색가치와 원본 해설 가치가 있는가?
6. 미확인 선거/범죄 단정 없이 안전하게 말할 수 있는가?
7. 다음 편을 예고할 수 있는가?

### 9.2 주제 점수표

| 항목 | 점수 |
| --- | ---: |
| 계정 정체성 적합성 | 20 |
| 댓글 충돌 가능성 | 15 |
| 팔로우 시리즈화 가능성 | 15 |
| 검색 키워드 가치 | 15 |
| 최근성 | 10 |
| 시각화 가능성 | 10 |
| 출처/근거 안정성 | 10 |
| 정책 리스크 낮음 | 5 |

60점 미만은 생성 금지. 75점 이상만 예약 후보. 85점 이상만 즉시 게시 후보.

## 10. 제작 워크플로우 v2

```text
01_signal_collection
  -> 02_keyword_cluster
  -> 03_audience_reaction_prediction
  -> 04_topic_score
  -> 05_series_fit
  -> 06_fact_pack
  -> 07_reference_pattern_fit
  -> 08_scene_first_plan
  -> 09_script_variants
  -> 10_caption_and_cta_plan
  -> 11_visual_generation_plan
  -> 12_tts_performance_plan
  -> 13_render
  -> 14_mobile_visual_qa
  -> 15_publish_quality_gate
  -> 16_upload_caption_gate
  -> 17_upload_or_schedule
  -> 18_daily_follower_rollup
  -> next topic scoring
```

주요 변경점:

- `03_audience_reaction_prediction`: 좌파 환호/분노, 우파 반박, 55+ 이해도를 점수화한다.
- `05_series_fit`: `오늘의 판정`, `대통령 순위`, `특검 책임선`, `우파 프레임 해체` 중 하나에 묶는다.
- `07_reference_pattern_fit`: `reference_patterns.json`, `format_router.json`, `hook_patterns.json`, `scene_type_library.json`, `cta_patterns.json`를 실제 라우팅에 연결한다.
- `08_scene_first_plan`: 텍스트부터 쓰지 않고 장면 역할부터 정한다.
- `10_caption_and_cta_plan`: 캡션 본문에 팔로우 이유를 강제로 넣는다.
- `16_upload_caption_gate`: TikTok 업로드 직전 렌더링된 캡션과 job 캡션이 일치하고 팔로우 문구가 있는지 검사한다.

## 11. 구현 설계

### 11.1 수정 대상

| 파일 | 변경 |
| --- | --- |
| `config/script_strategy.json` | `caption_follow_template`, `series_identity_templates`, `profile_transition_templates` 추가 |
| `config/publish_quality_strategy.json` | `caption_follow_cta`, `series_identity`, `profile_transition` critical gate 추가 |
| `config/reference_patterns.json` | 상태를 유지하되 production 사용 가능 패턴을 명시 |
| `pipeline.py` | 팔로우 점수를 `pinned_comment` 중심에서 `caption + end_scene + series_identity` 중심으로 변경 |
| `upload_automation.py` | `pinned_comment`는 별도 필드로 보존하고, 캡션에는 필수 follow CTA 포함 |
| `schedule_planner.py` | 슬롯별 포맷 믹스와 중복 제목/중복 썸네일 패널티 강화 |
| `monitoring.py` | profile_views/views, followers_gained/views, following traffic를 별도 지표화 |
| `tests/core/test_tiktok_aino_tts.py` 또는 신규 테스트 | CTA/캡션/게이트 회귀 테스트 추가 |

### 11.2 코드 변경 사이드이펙트

| 변경 | 사이드이펙트 | 대응책 |
| --- | --- | --- |
| 캡션에 팔로우 CTA 강제 | 캡션 길이 초과 가능 | `caption_total_max_chars` 안에서 해시태그보다 CTA 우선 |
| `pinned_comment` 점수 하향 | 기존 후보 점수 하락 | critical gate 전환 후 테스트로 기준 재보정 |
| 레퍼런스 config production 연결 | 특정 포맷 반복 가능 | 최근 7개 게시물의 format/thumbnail 중복 패널티 |
| 55+ 기준 자막 확대 | 정보량 감소 | source card는 짧게, 자세한 설명은 TTS로 이동 |
| 시리즈명 강화 | 양산 느낌 가능 | 시리즈 내 장면/훅/제목은 매번 다르게 생성 |
| 프로필 전환 지표 추가 | Studio 캡처 실패 시 빈 지표 | 없으면 `metric_missing`, 성과 판단에서 제외 |

## 12. 멀티에이전트 태스크 보드

| 담당 | 작업 단위 | 선행조건 | 산출물 | 완료 기준 | 검증 | 리스크 |
| --- | --- | --- | --- | --- | --- | --- |
| PM | 팔로우 KPI 정의 | 최신 Studio 스냅샷 | KPI 표, 실험 설계 | 조회/프로필/팔로우 분리 | daily rollup 비교 | 조회수만 보고 착각 |
| Research | 주제 선정 기준 재정의 | 성과 피드백, 공식 TikTok 문서 | topic scoring rule | 60/75/85점 게이트 | 후보 10개 샘플 채점 | 핫하지만 위험한 주제 |
| Writer | 시리즈/CTA 문법 설계 | 고성과 캡션 분석 | caption/CTA templates | 캡션에 팔로우 이유 필수 | 캡션 lint | 팔로우 스팸 |
| Designer | 장면-first 설계 | reference QA | scene role library | 영상별 장면 5종 이상 | contact sheet QA | 비슷한 이미지 반복 |
| Developer | config/code 연결 | 문서 승인 | JSON/config/code patch | hardcoded copy 없음 | pytest + compileall | 기존 생성 실패 |
| QA | 모바일 가독성/CTA 검수 | 렌더 결과 | QA 리포트 | 390px preview 통과 | screenshot/contact sheet | 작은 자막 |
| Ops | 업로드/예약 게이트 | Chrome session | upload evidence | caption match + CTA present | Studio search verify | 로그인/보안 경고 |
| Analytics | 팔로우 전환 모니터 | Studio capture | daily follower rollup | 하루 1회, 예약 0값 제외 | report diff | fresh metrics 누락 |
| Policy | 정치/AIGC 안전 | fact_pack | risk_flags | 미확인 선거/범죄 단정 차단 | blocker test | FYF 부적합 |

## 13. 7일 실험 설계

하루 3개, 총 21개를 세 가지 축으로 운영한다.

| 축 | 목적 | 예시 |
| --- | --- | --- |
| A. 정체성 결집 | 팔로우 전환 | `이재명 지지층이 아직 뜨거운 이유` |
| B. 책임 추궁 | 검색/댓글 | `김건희 특검, 어디까지 올라가나` |
| C. 순위/대결 | 댓글/공유 | `노무현 vs 이재명, 1위는 누구인가` |

각 영상은 다음 데이터를 남긴다.

```json
{
  "series_id": "identity_rally",
  "topic_score": 0,
  "audience_reaction": {
    "left_supporter_reward": 0,
    "opposition_rebuttal_likelihood": 0,
    "age_55_readability": 0
  },
  "caption_follow_cta": true,
  "video_end_follow_cta": true,
  "profile_transition_trigger": true,
  "metrics": {
    "views": null,
    "profile_views": null,
    "followers_gained": null,
    "comments": null,
    "shares": null
  }
}
```

성과 판단:

- `views`만 높고 `profile_views/views`가 낮으면 훅은 강하지만 구독 이유가 약한 것이다.
- `profile_views`는 높은데 `followers_gained`가 낮으면 프로필/바이오/고정 게시물 설계가 문제다.
- `comments`는 높은데 `followers_gained`가 낮으면 논쟁은 만들었지만 계정 정체성 설계가 약한 것이다.
- `followers_gained`가 높은 포맷은 다음 7일 슬롯 비중을 2배로 늘린다.

## 14. 즉시 적용 우선순위

### P0

1. `caption`에 follow CTA가 없으면 publish 차단.
2. `pinned_comment` 기반 follower score를 보조 점수로 격하.
3. 마지막 장면에 시리즈/팔로우 약속 없으면 publish 차단.
4. 예약/업로드 검증과 성과 측정을 분리하고 예약 0값은 성과에서 제외.

### P1

1. `reference_patterns.json` 계열 candidate config를 production routing에 연결.
2. 장면 역할 다양성 gate 추가.
3. 제목/썸네일/캡션 중복 패널티 강화.
4. `55+ readability` gate 추가.

### P2

1. 프로필 소개/고정 게시물 재정렬.
2. 7일 실험 dashboard 추가.
3. 댓글 반응 기반 후속편 자동 생성.

## 15. 완료 기준

구현 완료 선언은 아래가 모두 통과해야 한다.

- 새로 생성한 1개 샘플의 `manifest.json`에 `caption_follow_cta=true`, `video_end_follow_cta=true`, `series_identity`가 남는다.
- 업로드 job 캡션에 팔로우 문구가 실제 포함된다.
- `verification_report.html` 또는 QA JSON이 모바일 자막 overflow 없음으로 나온다.
- contact sheet에서 첫 3초 문구와 장면이 주제와 직접 대응한다.
- `python -m compileall src/core/tiktok_aino/pipeline.py src/core/tiktok_aino/upload_automation.py src/core/tiktok_aino/schedule_planner.py` 통과.
- CTA/품질 게이트 테스트 통과.
- TikTok Studio 성과 보고는 하루 1회만 수행하며, 예약 0값은 제외한다.

## 16. 다음 구현 순서

1. `script_strategy.json`에 caption follow CTA 템플릿과 시리즈 정체성 템플릿 추가.
2. `publish_quality_strategy.json`에 새 critical gate 추가.
3. `pipeline.py`에서 follower conversion score 산식을 교체.
4. `upload_automation.py`에서 upload job 생성 시 caption follow CTA 보존 여부를 검증.
5. 기존 고성과 게시물 3개를 seed reference로 사용해 신규 샘플 1개 생성.
6. 모바일 storyboard/contact sheet로 텍스트/장면/CTA 검수.
7. 1개 즉시 게시 또는 업로드 준비 후 Studio에서 캡션 일치 확인.

