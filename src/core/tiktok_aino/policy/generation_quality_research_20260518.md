# 올바른 AiNo 생성 품질 심층 연구 및 재설계

작성일: 2026-05-18  
대상: `올바른 AiNo` / TikTok `@leftaino`  
목적: 성과 피드백 이전 단계에서 콘텐츠 생성 품질 자체를 끌어올리기 위한 기준서

## 결론

현재 병목은 모니터링이나 피드백 빈도가 아니라, 생성 전에 주제, 근거, 각본, 이미지, TTS, 가독성의 품질을 충분히 잠그지 않는 구조다.

성과 피드백은 이미 올라간 결과를 보고 다음 배포 비중을 조절하는 장치일 뿐이다. 생성 품질은 사전에 `topic_signal_pack -> fact_pack -> content_brief -> storyboard -> visual_brief -> tts_plan -> render_plan -> qa_report`가 순서대로 통과되어야 만들어진다.

따라서 다음 개편의 핵심은 스크립트를 먼저 쓰는 방식에서 벗어나, `팩트팩과 콘텐츠 브리프가 각본을 지배하고, 각본이 이미지와 TTS를 지배하는 구조`로 바꾸는 것이다.

## 연구 근거

### TikTok 수익화/추천 기준에서 도출한 생성 조건

TikTok Creator Rewards Program은 1분 이상 고품질 원본 콘텐츠를 대상으로 하며, 핵심 신호는 독창성, 재생 지속, 검색 가치, 참여다.

생성 조건:

- 60초 이상은 길이만 맞추는 게 아니라, 끝까지 볼 이유가 있는 구조여야 한다.
- 단순 기사 요약은 원본성이 약하다. AiNo만의 기준, 질문, 장면화, 후속 추적 약속이 있어야 한다.
- 검색 가치는 제목, 화면 문구, 캡션, 해시태그가 같은 검색 의도에 묶여야 생긴다.
- 참여는 마지막 CTA만으로 만들 수 없다. 중간 장면부터 댓글로 답할 수 있는 판단 축이 누적되어야 한다.

Creator Search Insights는 많이 검색되지만 콘텐츠가 부족한 주제, 인기 점수, 추천 주제를 활용하라고 한다.

생성 조건:

- `이재명`, `김건희`, `윤석열`, `민주당`, `국민의힘` 같은 엔티티만으로는 부족하다.
- 좋은 주제는 `엔티티 + 행위 + 쟁점 + 지금성` 구조여야 한다.
- 예: `김건희 특검 압수수색`, `대통령실 대응 문건 공개`, `검찰개혁 법안 충돌`, `이재명 민생 정책 논쟁`.

For You 추천 설명에서 TikTok은 상호작용, 캡션/사운드/해시태그 같은 영상 정보, 긴 영상의 완주를 주요 신호로 설명한다. 또한 반복/중복 콘텐츠를 피하고 다양성을 유지한다고 밝힌다.

생성 조건:

- 같은 배경, 같은 템플릿, 같은 논리 전개를 반복하면 추천 관점에서도 약하다.
- 하루 3개를 만들더라도 세 개는 서로 다른 긴장 축이어야 한다.
- 영상 안에서도 장면, 색, 카메라, 소품, 문장 리듬이 반복되면 안 된다.

### 정책/안전 기준에서 도출한 생성 조건

TikTok은 정치 콘텐츠의 유기적 공유는 허용하지만, 유료 정치 광고와 보상성 정치 브랜디드 콘텐츠는 금지한다.

생성 조건:

- 채널은 공익 뉴스 해설과 비평으로 유지한다.
- 특정 정당/후보를 찍으라, 반대하라, 행동하라는 CTA는 금지한다.
- 캡션/고정댓글은 `판단 기준`, `근거`, `책임`, `후속 검증`으로 유도한다.

TikTok AIGC 정책은 사실처럼 보이는 AI 이미지/음성/영상에 라벨을 요구하고, 가짜 권위 출처, 실제 뉴스처럼 보이는 조작 화면, 공적 인물을 범죄와 연결하는 오해성 합성 등을 금지한다.

생성 조건:

- 실사형 이미지는 `생성 이미지` 고지가 필요하다.
- 실존 정치인 얼굴, 정당 로고, 선거 포스터, 읽히는 가짜 문서, 가짜 뉴스 화면은 금지한다.
- 이미지가 현실감을 가져야 하지만, 실제 사건 사진처럼 오인되면 안 된다. 장면은 `다큐멘터리풍 재연 이미지`로 설계한다.

### ElevenLabs/TTS 기준에서 도출한 생성 조건

ElevenLabs는 `eleven_multilingual_v2`를 한국어 포함 다국어 고품질 모델로 제공하고, 음성 설정에서 안정성, 유사성, 스타일, 속도, speaker boost를 조절한다. 발음 사전은 이름, 장소, 전문 용어의 발음을 고정하는 용도로 쓰며, 한국어는 IPA보다 alias 방식이 현실적이다.

생성 조건:

- 화면 문구와 TTS 문구는 분리한다. 화면은 짧고 세게, TTS는 자연스럽게 말한다.
- 장면별 TTS는 6~10초 단위의 짧은 호흡이어야 한다.
- 숫자, 날짜, 퍼센트, 영문 약어, 해시태그, URL은 읽는 방식으로 변환한다.
- 정치인이나 공인의 목소리를 흉내 내지 않고, 일반 내레이터 음성만 쓴다.
- 한국어 고유명사 발음은 `ko_tts_pronunciation.json` 또는 ElevenLabs pronunciation dictionary alias로 관리한다.

### 모바일 가독성 기준에서 도출한 생성 조건

WCAG 2.2의 대비 기준은 일반 텍스트 4.5:1, 큰 텍스트 3:1 이상을 요구한다. TikTok 크리에이티브 기준은 9:16 세로, UI safe zone, 첫 3초 제안, 첫 6초 훅, 5~10단어/초 수준의 텍스트 오버레이를 권한다.

생성 조건:

- 카드뉴스 화면 문구는 한 카드당 핵심 문장 1개, 보조 문장 1개가 상한이다.
- 썸네일 문구는 12~18자 한국어 구간이 가장 안정적이다.
- 본문은 2줄 이하, 줄당 13~16자 전후를 기본으로 한다.
- 바쁜 배경 위에는 반드시 어두운 스크림/텍스트 박스/그라데이션 마스크가 필요하다.
- TikTok 우측 인터랙션 영역과 하단 캡션 영역에는 핵심 텍스트를 두지 않는다.

## 생성 요소별 품질 기준

### 1. 주제 선정

현재 문제:

- 기사 제목의 화제성은 잡지만, 시청자가 멈출 만한 `약속`과 `갈등 축`이 약하다.
- 단일 출처 또는 연결이 약한 기사도 품질 점수만 높으면 후보가 된다.
- `이재명`, `민주당`, `윤석열`, `김건희`, `국민의힘`, `특검`, `선거` 같은 핵심 관심 키워드가 단순 쿼리로만 쓰이고, 좌파 지지층의 감정/관심 축으로 재구성되지 않는다.

필수 판단 축:

- 지금성: 최근 24~48시간 안에 왜 다시 커졌는가?
- 검색성: 사람들이 실제로 어떤 단어로 찾을 만한가?
- 진영 적합성: 진보 성향 시청자가 분노, 방어, 공유, 댓글 중 어떤 행동을 할 이유가 있는가?
- 근거 밀도: 최소 2개 이상의 공개 출처가 같은 쟁점을 지지하는가?
- 갈등 명료성: `누가 무엇을 했나`보다 `무엇이 확인됐고 무엇이 비어 있나`가 보이는가?
- 장면화 가능성: 9장 모두 서로 다른 현실 장면으로 만들 수 있는가?
- 정책 안전성: 선거 절차, 투표 독려, 미확인 범죄 단정, 실존 인물 합성을 피할 수 있는가?

새 게이트:

- `topic_heat_score >= 70`
- `source_count >= 2`, reward_deep는 가능하면 3 이상
- `specificity_score >= 75`: 엔티티 단독 금지
- `audience_charge_score >= 70`: 좌파 지지층이 댓글/공유할 명분
- `visual_sceneability_score >= 80`
- `policy_risk != high`

### 2. 팩트팩

현재 문제:

- `claims`는 있지만, 사실/주장/반론/빈칸이 명확히 분리되지 않는다.
- deep research의 research question이 다른 주제에서 새는 현상이 있다. 예: 이재명/통일백서 슬롯에 윤석열 특검 질문이 붙는 식이다.

필수 산출물:

```json
{
  "confirmed_facts": [],
  "reported_claims": [],
  "counterpoints": [],
  "unanswered_questions": [],
  "risk_phrases_to_avoid": [],
  "source_roles": {
    "primary_report": "",
    "supporting_report": "",
    "official_or_original": "",
    "counterpoint_or_response": ""
  }
}
```

새 게이트:

- 모든 장면의 핵심 주장에는 `fact_pack`의 항목 id가 붙어야 한다.
- `reported_claims`를 `confirmed_facts`처럼 말하면 차단한다.
- 반론이 없는 의혹형 주제는 단정형이 아니라 `빈칸형` 각본으로만 허용한다.

### 3. 콘텐츠 브리프

현재 문제:

- `editorial_plan`은 있지만 너무 얕다. 주제 선택 후 바로 각본 템플릿으로 넘어가므로 콘텐츠의 약속, 감정, 시청자 행동이 잠기지 않는다.

필수 산출물:

```json
{
  "viewer_promise": "1분 안에 무엇을 얻는가",
  "one_sentence_thesis": "이 영상의 주장",
  "audience_emotion": "분노/찜찜함/방어/확인 욕구/생활 불안",
  "share_reason": "왜 공유하는가",
  "comment_question": "숫자로 답할 수 있는 질문",
  "follow_reason": "후속편을 왜 기다리는가",
  "safe_provocation": "자극적이지만 단정/선동이 아닌 훅",
  "forbidden_angle": "하면 안 되는 프레임"
}
```

새 게이트:

- viewer promise가 없으면 각본 생성 금지.
- comment question이 숫자 선택지로 정리되지 않으면 게시 후보 제외.
- follow reason이 `다음 검증`과 연결되지 않으면 팔로우 전환 후보 제외.

### 4. 각본/스토리보드

현재 문제:

- 장면별 문장이 템플릿 냄새가 난다.
- `전말/근거/책임` 같은 단어가 반복되어 생동감이 떨어진다.
- 주제별 고유한 드라마가 아니라 모든 이슈가 비슷한 시민 기준 해설로 수렴한다.

권장 9장 구조:

1. 썸네일: 멈추게 하는 질문. 12~18자.
2. 도화선: 오늘 왜 이 얘기가 다시 나왔는가.
3. 갈라지는 지점: 시청자가 편을 들기 전에 봐야 할 기준.
4. 영수증: 확인된 근거 1개.
5. 빈칸: 아직 설명되지 않은 지점.
6. 반론/주의: 단정하면 안 되는 지점.
7. 책임선: 누가 어떤 설명을 해야 하는가.
8. 시청자 기준: 이 사안을 어떻게 판단할 것인가.
9. 정리/CTA: 댓글 선택지 + 팔로우 이유.

문장 기준:

- 화면 문구: 1문장, 12~26자. 긴 경우 2줄.
- TTS 문구: 40~85자. 1장당 1호흡 또는 2호흡.
- 각 장면은 `새 정보`가 있어야 한다. 같은 말을 바꿔 말하는 장면은 실패.
- 첫 3초에는 주제, 첫 6초에는 볼 이유가 나와야 한다.

### 5. 이미지/비주얼

현재 문제:

- 실감나는 이미지 방향은 잡았지만, 장면 설계가 각본 이후 자동 추론이라 주제 특화도가 부족하다.
- 같은 책상, 같은 서류, 같은 공공기관 톤이 반복될 수 있다.
- 이미지가 `주제별 증거 장면`이 아니라 `정치 뉴스 느낌 배경`에 머무는 순간 생성 이미지의 의미가 사라진다.

이미지 브리프 필수 필드:

```json
{
  "scene_id": 1,
  "visual_job": "이 장면이 전달해야 할 정보",
  "location": "",
  "foreground_object": "",
  "human_presence": "none/silhouette/cropped hands",
  "camera": "",
  "lighting": "",
  "palette": "",
  "overlay_lane": "top/middle/bottom",
  "must_imply": [],
  "must_not_show": []
}
```

장면 다양성 규칙:

- 9장 중 같은 장소 유형은 최대 2회.
- `서류 책상`은 최대 2회.
- hook은 책상 금지. 공공장소, 복도, 계단, 프레스라인, 비 오는 입구 등 공간감이 있어야 한다.
- evidence는 손, 봉투, 기록, 분류 행위가 있어야 한다.
- responsibility는 빈 의자, 마이크, 청문 공간처럼 답변 부재가 보여야 한다.
- CTA는 따뜻한 편집 데스크/댓글 카드로 마무리한다.

생성 기준:

- 1순위: Codex CLI 이미지 생성.
- fallback: Gemini API.
- 로컬 추상 fallback은 미리보기 전용이며 게시 후보를 차단한다.
- 실존 인물 얼굴, 정당 로고, 읽히는 문서, 가짜 뉴스 화면, 선거 포스터, 실제 기관 로고 금지.

### 6. 디자인/가독성

현재 문제:

- 텍스트 길이 검수는 있지만, `눈에 꽂히는 짧은 문장`인지와 `모바일에서 읽는 리듬`까지 보지 못한다.

카드 레이아웃 기준:

- 캔버스: 1080x1920.
- 핵심 텍스트 안전 영역: 좌우 96px 이상, 상단 160px 이상, 하단 360px 이상.
- 썸네일 헤드라인: 76~92px, 최대 2줄.
- 일반 카드 헤드라인: 58~72px.
- 보조 문장: 38~48px, 최대 2줄.
- 대비: 일반 텍스트 4.5:1 이상, 큰 텍스트 3:1 이상. 실제 모바일 영상은 압축을 고려해 6:1 이상을 목표로 한다.
- 배경이 복잡하면 35~55% 어두운 스크림 또는 반투명 패널을 적용한다.

텍스트 길이 대응:

- 너무 길면 요약하지 말고 역할을 나눈다. 화면은 질문, TTS는 설명.
- 너무 짧으면 추상어를 늘리지 말고 구체어를 넣는다.
- 금지: `이게 맞나요?`, `충격입니다`, `진실은?`처럼 주제가 없는 낚시.
- 권장: `대응 문건, 왜 공개됐나`, `무혐의면 끝인가`, `공천개입, 빈칸은 여기`.

### 7. TTS

현재 문제:

- TTS 전처리는 있지만, `말하기용 원고`가 별도 창작물로 관리되지 않는다.
- 장면별 감정/속도/호흡을 설계하지 않으면 좋은 모델을 써도 어색하다.

TTS 원고 기준:

- 화면 문구와 별도 저장.
- 문장당 18~32자 단위로 쉼표/마침표를 둔다.
- 한 장면은 6~10초. 보통 한국어 기준 35~70자.
- 외래어, 영어 약어, 숫자, 날짜는 읽는 말로 변환한다.
- 고유명사는 alias 사전으로 고정한다.
- ElevenLabs는 `Anna Kim`, `eleven_multilingual_v2`를 기본 publish voice로 둔다. 새 모델 테스트는 별도 A/B로 한다.
- 사용자 기존 선호값은 참고하되, 정치 해설형은 너무 낮은 stability가 흔들릴 수 있으므로 장면별 샘플 비교가 필요하다.

권장 기본값:

- model: `eleven_multilingual_v2`
- speed: `1.04~1.09`
- stability: `0.18~0.35`
- similarity_boost: `0.20~0.45`
- style: `0.05~0.12`
- speaker_boost: true

장면별 톤:

- 1장: 낮고 단정하게, 속도 빠르게.
- 2~4장: 정보 밀도 있게.
- 5~7장: 잠깐 느리게, 빈칸/반론을 분리.
- 8~9장: 정리와 참여 유도, 과한 감정 금지.

### 8. 편집/모션/렌더

현재 문제:

- 사용자는 지속적인 흔들림/움직임을 싫어한다.
- 따라서 모션은 `영상이 살아 있음`을 위해 쓰는 게 아니라, 장면 전환과 시선 유도에만 써야 한다.

렌더 기준:

- 기본은 `controlled_kinetic_still`이다.
- 장면 전환은 0.15~0.25초 컷/디졸브.
- 흔들림, 과한 Ken Burns, 지속 확대는 금지한다.
- 각 장면은 2~3개 visual beat로 나누고, 미세 pan/zoom과 일부 light sweep만 허용한다.
- 훅/전환 카드에서만 시선 유도용 1~3% 수준의 아주 약한 push-in을 허용한다.
- TTS 길이에 맞춰 카드 길이를 조정하되 5초 미만, 12초 초과는 피한다.

### 9. 캡션/해시태그/고정댓글

현재 문제:

- 메타데이터가 콘텐츠 브리프가 아니라 템플릿에서 파생되어 제목/설명/해시태그가 약해진다.

생성 기준:

- 제목: 18~34자. 검색어 + 긴장 축.
- 캡션: 120~220자. 사실/빈칸/댓글 질문.
- 해시태그: 8~12개. 엔티티 2~3, 쟁점 2~3, 형식 2, 브랜드 1.
- 고정댓글: 숫자 선택지로 답하게 한다.

예시 형식:

```text
대통령실 문건, 왜 지금 공개됐나

보도된 문건, 반론 가능성, 아직 비어 있는 책임선을 분리했습니다.
1 전말 2 근거 3 책임 중 무엇부터 봐야 한다고 보나요?

#대통령실 #민주당 #특검 #정치뉴스 #팩트체크 #시사 #공정 #올바른AiNo
```

### 10. QA 게이트

게시 전 필수 게이트:

- Topic gate: 구체 쟁점, 출처 2개 이상, 검색 의도, 시청자 감정, 장면화 가능성.
- Fact gate: 사실/주장/반론/빈칸 분리, 소스 id 연결.
- Brief gate: viewer promise, one-sentence thesis, safe provocation, comment/follow reason.
- Script gate: 9장 모두 새 정보, 첫 3초 주제, 첫 6초 볼 이유, 마지막 CTA.
- Visual gate: 장면별 이미지 브리프, 실제 생성 이미지 9장, 반복/유사도 검사.
- Readability gate: safe zone, 글자수, 대비, OCR/렌더 확인.
- TTS gate: ElevenLabs publish audio, 장면별 lint, 발음 사전, 길이 동기화.
- Policy gate: 정치광고/투표 설득/미확인 선거 정보/AIGC/실존 인물 합성 차단.
- Render gate: 흔들림 없음, 전환 정상, TTS 싱크, mp4/스토리보드/모바일 미리보기.

## 현재 구현과의 차이

이미 구현된 강점:

- 신호 수집, 키워드 플랜, 토픽 풀, 토픽 플랜, deep research report, editorial plan, selected script, content plan, visual plan, tts plan, render manifest가 있다.
- 실사형 이미지 안전 제약, 장면 다양성 점수, TTS 전처리, ElevenLabs 게이트가 있다.
- 최근 패치로 deep research 점수를 스케줄 선정에 연결했다.

핵심 결함:

- 스크립트가 여전히 `기사 제목 + 템플릿` 중심으로 먼저 만들어진다.
- `content_plan`은 각본 전 설계가 아니라, 각본 후 설명 아티팩트에 가깝다.
- `fact_pack`이 독립 산출물이 아니라 claim/source 목록에 흩어져 있다.
- `deep_research_report`의 선택 질문이 다른 후보로 새는 문제가 있다.
- 비주얼 브리프는 좋지만 각본 전 단계에서 `장면으로 증명 가능한가`를 차단하지 못한다.
- 품질 점수는 통과해도, 실제 시청자가 “이걸 왜 봐야 하지?”라는 질문에 답하지 못하는 경우가 있다.

## 재설계 워크플로우

```text
01_signal_collection
  -> 02_topic_signal_pack
  -> 03_fact_pack
  -> 04_content_brief
  -> 05_storyboard
  -> 06_script_package
  -> 07_visual_brief
  -> 08_image_generation
  -> 09_tts_performance_plan
  -> 10_render_plan
  -> 11_quality_review
  -> 12_upload_plan
```

변경 원칙:

- `content_brief` 없이는 `script_package` 생성 금지.
- `fact_pack` 없이는 `content_brief` 생성 금지.
- `visual_brief` 없이는 이미지 생성 금지.
- `tts_performance_plan` 없이는 ElevenLabs 호출 금지.
- `quality_review`가 `publish_ready`를 내기 전에는 업로드/예약 금지.

## 구현 우선순위

1. `content_brief_builder.py` 추가  
   주제마다 viewer promise, thesis, safe provocation, comment/follow reason을 만든다.

2. `fact_pack_builder.py` 추가  
   source를 primary/support/counterpoint/official로 나누고, 사실/주장/반론/빈칸을 분리한다.

3. `generate_script()` 입력 변경  
   `topic + topic_discovery`가 아니라 `content_brief + fact_pack + format_plan`을 입력으로 받게 한다.

4. `storyboard_plan.json` 추가  
   9장 각각의 narrative job, evidence id, visual job, TTS job을 먼저 고정한다.

5. `visual_brief`를 storyboard 기반으로 재작성  
   장면마다 location, foreground object, camera, palette, overlay lane, must_not_show를 고정한다.

6. `tts_performance_plan.json` 추가  
   장면별 호흡, 속도, 강조어, 발음 alias, 예상 길이를 저장한다.

7. QA 게이트 강화  
   텍스트 가독성뿐 아니라 `콘텐츠 약속`, `새 정보`, `장면 다양성`, `TTS 자연성`, `시청자 행동 이유`를 점수화한다.

## 운영 원칙

- 성과 피드백은 하루 1회면 충분하다.
- 생성 품질은 매 콘텐츠마다 사전에 검수한다.
- 하루 3개 예약은 가능하지만, 3개 모두 topic/fact/brief/storyboard가 다른 결을 가져야 한다.
- 중복 콘텐츠는 성과가 좋았던 경우의 후속/반론/업데이트가 아니면 금지한다.
- `올바른 AiNo`의 차별점은 더 센 말이 아니라, 진보 시청자가 공유하고 싶을 만큼 선명한 기준과 장면화다.

## 참조 문서

- TikTok Creator Rewards Program: https://newsroom.tiktok.com/introducing-the-new-creator-rewards-program/?lang=en
- TikTok Creator Search Insights: https://newsroom.tiktok.com/creator-search-insights?lang=en
- TikTok For You recommendations: https://newsroom.tiktok.com/how-tiktok-recommends-videos-for-you?lang=en
- TikTok AIGC support: https://support.tiktok.com/en/using-tiktok/creating-videos/ai-generated-content
- TikTok Integrity and Authenticity: https://www.tiktok.com/community-guidelines/en/integrity-authenticity/
- TikTok Political Ads Policy: https://ads.tiktok.com/help/article/tiktok-ads-policy-politics-government-and-elections
- TikTok Creative Codes: https://ads.tiktok.com/business/en-US/creative-codes
- TikTok Creative Best Practices: https://ads.tiktok.com/help/article/creative-best-practices?lang=en
- ElevenLabs Models: https://elevenlabs.io/docs/overview/models
- ElevenLabs Voice Settings: https://elevenlabs.io/docs/api-reference/voices/settings/get-default/
- ElevenLabs Pronunciation Dictionaries: https://elevenlabs.io/docs/eleven-api/guides/how-to/text-to-speech/pronunciation-dictionaries
- WCAG 2.2: https://www.w3.org/TR/WCAG22/
