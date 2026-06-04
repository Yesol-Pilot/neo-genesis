# 올바른 AiNo 추가 심층 리서치 요청서

작성일: 2026-05-28 KST  
목적: 1차 Deep Research 보고서의 부족분 보완  
대상 원문: `output\tiktok_aino_reference_research\deep-research-report_aino_20260528.md`  
검토 문서: `DEEP_RESEARCH_REPORT_REVIEW_20260528.md`

## 1. 추가 요청 사유

1차 보고서는 정책, 플랫폼 경제성, 운영 모델은 유용했지만, 실제 콘텐츠 제작 품질을 높이는 데 필요한 **게시물 단위 레퍼런스 벤치마크**가 부족했다.

부족한 항목:

- 실제 상위 게시물 URL 20~30개.
- 게시일, 길이, 조회수, 좋아요, 댓글 등 공개 성과 지표.
- 첫 1초/3초/5초 훅 구조.
- 소스 카드 또는 근거 노출 위치.
- 자막 밀도, 컷 수, 장면 유형.
- 음성/TTS/진행 톤.
- CTA와 고정댓글 구조.
- AI 생성물처럼 보이는 요소와 신뢰를 주는 요소.
- `올바른 AiNo` 자동 생성 파이프라인에 넣을 수 있는 규칙화된 코드북.

이번 추가 리서치는 일반론을 금지하고, 실제 공개 게시물 코딩 테이블을 만드는 것이 목적이다.

## 2. 붙여넣기용 Deep Research 추가 요청문

아래 내용을 그대로 GPT Deep Research에 넣어라.

```text
이전 보고서는 정책·운영 모델은 유용했지만, 실제 상위 숏폼 레퍼런스의 게시물 단위 분석이 부족했다. 이번 추가 리서치에서는 일반론을 최소화하고, 공개 URL 기반의 벤치마크 테이블을 작성하라.

목표:
한국어 정치/시사/공익 해설 숏폼 채널 `올바른 AiNo`의 자동 생성 파이프라인에 직접 반영할 수 있도록, TikTok·YouTube Shorts·Instagram Reels의 실제 상위 레퍼런스 게시물 20~30개를 수집하고 구조적으로 코딩하라.

중요 범위:
- `@leftaino` 자체 게시물은 제외한다.
- 특정 후보·정당 투표 설득, 선거운동, 유권자 조작, 허위정보 확산, 실존 인물 얼굴·음성 합성 권장은 금지한다.
- 연구 대상은 공개 정치/시사/뉴스/풍자/권력 감시/공익 해설 숏폼의 형식과 제작 문법이다.
- 조회수나 좋아요 등 공개 성과 지표가 보이지 않는 경우 임의 추정하지 말고 `확인 불가`라고 적는다.
- 출처 URL이 없거나 실제 게시물을 확인할 수 없는 사례는 표에 넣지 않는다.
- 이미 알려진 플랫폼 정책 일반론은 반복하지 말고, 실제 게시물 분석과 자동화 규칙 도출에 집중하라.

수집 기준:
1. 한국어 중심 정치/시사/뉴스/풍자/공익 해설 숏폼 20~30개.
2. 플랫폼별 최소 수량:
   - TikTok: 최소 8개.
   - YouTube Shorts: 최소 8개.
   - Instagram Reels: 가능하면 4개 이상. 공개 확인이 어려우면 사유를 적고 TikTok/Shorts를 보강한다.
3. 유형별 최소 포함:
   - 뉴스 클립형.
   - 증거형 브리핑.
   - 타임라인 해설형.
   - 풍자/캐릭터형.
   - 댓글 배틀형.
   - 팩트체크/오해 바로잡기형.
4. 정치 성향은 진보 성향, 보수 성향, 중립 뉴스형을 모두 포함하되, `올바른 AiNo` 적용 가능성은 진보 공익 해설형 관점에서 따로 평가한다.
5. 가능하면 최근 6개월 이내 게시물을 우선하되, 구조적으로 중요한 오래된 고성과 사례는 `스테디 레퍼런스`로 표시한다.

각 게시물별 필수 코딩 필드:

| 필드 | 설명 |
|---|---|
| id | R001 형식 |
| platform | TikTok / YouTube Shorts / Instagram Reels |
| url | 실제 공개 URL |
| channel_name | 채널명 |
| post_date | 게시일. 확인 불가면 `확인 불가` |
| topic | 다룬 이슈 |
| political_context | 진보 / 보수 / 중립뉴스 / 풍자 / 기타 |
| format_type | news_clip / evidence_briefing / timeline_explainer / satire_character / comment_battle / fact_check / hybrid |
| duration_sec | 영상 길이. 확인 불가면 `확인 불가` |
| views | 공개 조회수. 확인 불가면 `확인 불가` |
| likes | 공개 좋아요. 확인 불가면 `확인 불가` |
| comments | 공개 댓글 수. 확인 불가면 `확인 불가` |
| engagement_notes | 댓글/공유/저장 유도 신호 |
| first_1s_hook | 첫 1초에 무엇이 보이거나 들리는가 |
| first_3s_hook | 첫 3초 문장/화면 구조 |
| first_5s_hook | 첫 5초까지의 전개 |
| source_card_position | 출처/문서/방송/근거가 언제 보이는가 |
| evidence_type | 공식문서 / 언론보도 / 영상클립 / 발언 / 데이터 / 없음 |
| scene_types | 법정, 국회, 뉴스룸, 거리, 데이터카드, 얼굴 클립, 캐릭터 등 |
| cut_count_estimate | 컷 수 추정 |
| caption_density | 낮음 / 중간 / 높음 + 한 줄당 글자 수 추정 |
| visual_style | 실사뉴스 / 방송클립 / AI이미지풍 / 일러스트 / 캐릭터 / 혼합 |
| voice_style | 실제 음성 / 진행자 / TTS 추정 / 자막만 / 확인 불가 |
| tts_naturalness | 해당 시 TTS 자연스러움 평가 |
| cta_type | 댓글질문 / 팔로우 / 저장 / 공유 / 다음편 / 없음 |
| pinned_comment_pattern | 확인 가능하면 고정댓글 구조 |
| trust_signal | 출처, 문서, 날짜, 인용, 정정, 전문성 신호 |
| risk_signal | 선동, 미확인 단정, 저작권, 실존 인물 합성 오인, 댓글 독성 |
| why_it_worked | 성과 원인 분석 |
| aino_applicability | 올바른 AiNo에 적용 가능 / 수정 후 가능 / 부적합 |
| pipeline_rule | 자동 생성 파이프라인에 넣을 규칙 |

분석 요구:

1. 레퍼런스 표를 먼저 작성하라.
2. 그 다음 형식별 평균/패턴을 요약하라.
   - 평균 길이.
   - 첫 3초 훅 유형.
   - 출처 카드 노출 시점.
   - 자막 밀도.
   - 장면 유형.
   - CTA 유형.
   - 댓글 유도 방식.
3. `올바른 AiNo`에 적용할 수 있는 포맷 5개를 선정하라.
   - `evidence_briefing_75`
   - `moment_short`
   - `timeline_explainer`
   - `misread_correction`
   - `satire_character_safe`
4. 각 포맷별 제작 규칙을 수치화하라.
   - 권장 길이.
   - 컷 수.
   - 컷당 자막 글자 수.
   - 첫 3초 문장 구조.
   - source card 위치.
   - 이미지/장면 유형.
   - TTS 톤.
   - CTA 구조.
5. AI 생성 파이프라인에 들어갈 코드북을 작성하라.
   - `reference_patterns.json` 스키마.
   - `format_router.json` 스키마.
   - `hook_patterns.json` 스키마.
   - `scene_type_library.json` 스키마.
   - `cta_patterns.json` 스키마.
6. 반드시 `적용 금지 패턴`을 따로 정리하라.
   - 실존 인물 오인 유발.
   - 정당/후보 광고처럼 보이는 표현.
   - 출처 없는 범죄 단정.
   - 가짜 뉴스 화면/가짜 공문서.
   - 같은 카드 레이아웃 반복.
   - AI 양산형 이미지 반복.

최종 산출물 형식:

1. 핵심 결론 5줄.
2. 수집 방법과 한계.
3. 20~30개 게시물 레퍼런스 코딩 테이블.
4. 형식별 패턴 요약.
5. `올바른 AiNo` 적용 가능성 평가.
6. 자동 생성 파이프라인용 코드북.
7. 포맷별 제작 규칙.
8. 적용 금지 패턴.
9. 바로 다음 구현 우선순위 P0/P1/P2.

품질 기준:
- URL 없는 사례는 제외한다.
- 공개 성과 지표가 없는 항목은 `확인 불가`로 표시한다.
- 출처 URL을 각 행에 반드시 포함한다.
- 일반론보다 게시물 코딩 테이블을 우선한다.
- 결과가 다시 일반론 위주라면 실패한 리서치로 간주한다.
```

## 3. 결과물 검수 기준

| 항목 | 통과 기준 | 실패 기준 |
| --- | --- | --- |
| 게시물 수 | URL 있는 20개 이상 | URL 없는 사례 또는 채널명만 나열 |
| 플랫폼 분산 | TikTok 8+, Shorts 8+, Reels 가능 범위 | 한 플랫폼 일반론 위주 |
| 성과 지표 | 조회수/좋아요/댓글 중 공개 값 기록 | 성과 원인만 추정 |
| 첫 3초 분석 | 각 게시물별 훅 문장/화면 구조 기록 | "강한 훅" 같은 추상 표현 |
| 장면 분석 | scene_types, cut_count, visual_style 기록 | 분위기 설명만 있음 |
| 자동화 변환 | JSON 코드북 스키마 포함 | 사람이 감으로 참고하는 수준 |
| 안전성 | 적용 금지 패턴 분리 | 자극성만 강조 |

## 4. 이 결과가 들어갈 위치

추가 리서치 결과를 받으면 다음으로 변환한다.

1. `output\tiktok_aino_reference_research\reference_benchmark_YYYYMMDD.md`
2. `src\core\tiktok_aino\config\reference_patterns.json`
3. `src\core\tiktok_aino\config\format_router.json`
4. `src\core\tiktok_aino\config\hook_patterns.json`
5. `src\core\tiktok_aino\config\scene_type_library.json`
6. `src\core\tiktok_aino\config\cta_patterns.json`

이 벤치마크가 생기기 전까지는 비주얼/훅/CTA 최적화를 확정하지 않는다.
