# 올바른 AiNo URL 기반 레퍼런스 벤치마크 재요청서

작성일: 2026-05-28 KST  
목적: 2차 보완 보고서의 부족분 재요청  
직전 검토: `DEEP_RESEARCH_FOLLOWUP_REVIEW_20260528.md`  
이전 보고서: `output\tiktok_aino_reference_research\deep-research-reportaino2_20260528.md`

## 1. 재요청 사유

직전 보고서는 포맷 코드북은 일부 유용했지만, 핵심 요구였던 실제 게시물 URL 기반 20~30개 벤치마크 표를 완성하지 못했다. 다음 연구는 일반론, 후보 채널, 사건 설명보다 **실제 게시물 URL 수집**을 우선한다.

## 2. 붙여넣기용 요청문

```text
이전 보완 보고서는 포맷 코드북은 유용했지만, 핵심 요구인 실제 게시물 URL 20~30개 전수 코딩표를 완성하지 못했다. 이번에는 설명형 보고서를 쓰지 말고, 먼저 URL 수집표를 만들어라.

절대 규칙:
- 실제 공개 게시물 URL이 없는 행은 벤치마크 표에 넣지 않는다.
- 채널명, 기사, 사건 설명만 있는 후보는 별도 후보표에도 넣지 말고 제외한다.
- 조회수, 좋아요, 댓글, 게시일, 길이가 보이지 않으면 `확인 불가`라고 적어도 된다.
- 그러나 `url`은 절대 `확인 불가`가 될 수 없다.
- 직접 URL 20개 미만이면 긴 설명을 하지 말고 최상단에 `FAILED_URL_COLLECTION`이라고 쓰고, 확보한 URL만 표로 제시하라.
- `@leftaino` 자체 게시물은 제외한다.
- 특정 정당·후보 투표 설득, 선거운동 권장, 허위정보 확산, 실존 인물 얼굴·음성 합성 권장은 금지한다.

수집 대상:
- 한국어 정치/시사/뉴스/풍자/권력 감시/공익 해설 숏폼.
- TikTok 8개 이상, YouTube Shorts 8개 이상을 우선한다.
- Instagram Reels는 4개 이상을 시도하되, 공개 URL/지표 접근이 어렵다면 TikTok/Shorts로 보강한다.
- 최근 6개월 이내를 우선하되, 구조적으로 중요한 스테디 고성과 사례는 `steady_reference`로 표시한다.
- `뉴스공장`, `매불쇼`, `제이컴퍼니`, `이재명TV`, 주요 방송사 Shorts, 정치 풍자 계정, 보수 고성과 채널도 비교 대상으로 포함하라. 단, `올바른 AiNo` 적용성은 별도 평가하라.

먼저 아래 표부터 작성하라. 표를 만들기 전 긴 해설을 쓰지 마라.

| id | platform | url | channel_name | post_date | topic | political_context | format_type | duration_sec | views | likes | comments | first_1s_hook | first_3s_hook | first_5s_hook | source_card_position | evidence_type | scene_types | cut_count_estimate | caption_density | visual_style | voice_style | cta_type | trust_signal | risk_signal | why_it_worked | aino_applicability | pipeline_rule |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

코딩 규칙:
- `format_type`: news_clip / evidence_briefing / timeline_explainer / satire_character / comment_battle / fact_check / hybrid 중 하나.
- `caption_density`: 낮음 / 중간 / 높음 + 가능하면 한 줄 글자 수.
- `voice_style`: 실제 음성 / 진행자 / TTS 추정 / 자막만 / 확인 불가.
- `source_card_position`: 0~2초 / 3~5초 / 중반 / 후반 / 없음 / 확인 불가.
- `aino_applicability`: 적용 가능 / 수정 후 가능 / 부적합.

표 이후에만 다음을 요약하라.
1. 상위 포맷별 평균 길이와 컷 수.
2. 첫 3초 훅 패턴 5개.
3. 출처 카드 위치 패턴.
4. 자막 밀도와 모바일 가독성 패턴.
5. 장면 유형 라이브러리.
6. CTA 패턴.
7. `올바른 AiNo`에 적용 금지할 패턴.
8. 다음 JSON 코드북 초안:
   - `reference_patterns.json`
   - `format_router.json`
   - `hook_patterns.json`
   - `scene_type_library.json`
   - `cta_patterns.json`

성공 기준:
- URL 있는 행 20개 이상.
- TikTok 8개 이상과 YouTube Shorts 8개 이상.
- 각 행의 첫 1초/3초/5초 구조 기록.
- 각 행의 pipeline_rule 기록.
- URL 없는 사례나 후보 채널 일반론으로 분량을 채우면 실패다.
```

## 3. 검수 기준

| 항목 | 통과 | 실패 |
| --- | --- | --- |
| URL 수 | 직접 게시물 URL 20개 이상 | 채널명, 사건명, 기사만 있음 |
| 플랫폼 분산 | TikTok 8+, Shorts 8+ | 한 플랫폼 또는 일반론 중심 |
| 코딩 밀도 | 훅, 장면, 자막, 음성, CTA가 행별로 있음 | 포맷별 설명만 있음 |
| 자동화 변환 | JSON 코드북이 URL 테이블에서 파생됨 | 코드북이 추론형 일반론 |
| 정직성 | 부족하면 `FAILED_URL_COLLECTION` | 부족한데 완성판처럼 서술 |
