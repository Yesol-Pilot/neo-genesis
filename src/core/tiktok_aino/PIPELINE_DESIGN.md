# AiNo TikTok Content Pipeline Design

Workflow SSOT: `WORKFLOW_DESIGN_SPEC.md`

This file describes the current implementation and operational behavior. New workflow decisions must be made against `WORKFLOW_DESIGN_SPEC.md` first, then reflected here and in JSON config.

## Goal

`@leftaino` / `올바른 AiNo` 계정의 하루 3개 숏폼 운영을 자동화한다.

자동화 범위는 다음으로 제한한다.

- 자동 생성: 주제 선정, 대본, 카드 구성, 시네마틱 이미지, ElevenLabs TTS, MP4, 캡션, 해시태그, 고정 댓글, 검수 리포트
- 반자동 업로드: Chrome Extension이 TikTok 업로드 화면에 파일과 메타데이터를 채워 넣고, 최종 공개 버튼은 사람이 확인한다
- 자동 수집: Extension이 TikTok Studio 지표를 로컬 브리지로 수집해 다음 주제/포맷 선택에 반영한다

직접 API 게시를 기본값으로 두지 않는다. TikTok Content Posting API는 심사되지 않은 클라이언트의 공개 게시가 제한되고 `video.publish` 권한과 사용자 동의가 필요하므로, 현재 계정 운영에는 Chrome Extension 보조 업로드가 현실적인 경로다.

## Official Policy Inputs

- TikTok Creator Rewards는 1분 이상, 고품질, 원본성, play duration, search value, audience engagement를 중시한다.
- TikTok Creator Rewards의 보상 신호는 watch time, finish rate, search value, engagement, ad value를 함께 보므로 `reward_deep`는 1분 이상 해설, 검색 의도가 있는 실명/기관/쟁점 키워드, 댓글 재방문 구조를 필수로 둔다.
- TikTok Creator Search Insights의 content gap/search topic 접근을 반영해 `--topic-mode hot`은 최근 보도 후보에서 검색가치가 남는 주제를 우선한다.
- TikTok creative guidance의 초반 3~6초 hook 원칙을 반영해 훅은 질문형/대조형/책임형이어야 하며, 단정적 비방 대신 “보도·기록·기준·확인” 프레임으로 제한한다.
- TikTok AIGC 정책은 현실처럼 보이는 AI 이미지, 영상, 오디오에 라벨 또는 명확한 공개 고지를 요구한다.
- TikTok Creative guidance는 초반 6초 hook, 본문 자극 요소, 마지막 CTA를 강조한다.

## Research-Based Redesign v2 — 2026-05-14

### Inputs

- 공식 기준: Creator Rewards의 원본성, 1분 이상, play duration, search value, audience engagement.
- 공식 안전 기준: AIGC 라벨, 시민/선거 오정보, 유료 정치 홍보, 인위적 지표 조작 금지.
- 계정 기준: `올바른 AiNo`는 유료 정치 광고나 선거 행동 설득이 아니라, 공개 보도 기반의 시민/시사 해설 채널로 운영한다.
- 레퍼런스 분석: `output/tiktok_aino_reference_reports/category_reference_analysis_20260514_151756.md`.

### Findings

상위 카테고리 표본은 차분한 기록형보다 즉시 갈등을 여는 문법이 강했다.

- `48시간 전말`
- `오해와 진실`
- `진짜 이유`
- `왜 침묵했나`
- `기준 3개`
- `A와 B의 차이`

따라서 기존의 “기록으로 다시 보기” 중심 구조는 보존하되, 첫 카드와 썸네일은 `전말 / 근거 / 빈칸 / 책임`으로 재구성한다. 자극성은 조회수 확보용으로 쓰지 않고, 검증 가능한 질문을 만들기 위한 장치로만 쓴다.

### Persona Task Board

| Persona | Work Unit | Output | Done Criteria | Verification |
| --- | --- | --- | --- | --- |
| PM | 수익화 친화 포맷 재정의 | 65~95초 `reward_deep`, 35~45초 `growth_short`, 45~75초 `debate_followup` 유지 | 1분 이상 후보는 검색가치/원본성/완주 구조 포함 | `PublishQualityResult`와 format duration gate |
| Research | 상위 카테고리 문법 추출 | `48시간 전말`, `오해와 진실`, `기준 3개` 훅 문법 | 공개 표본과 공식 정책 모두 추적 가능 | reference report + source registry |
| Architect | 설정 SSOT 재배치 | 문구/점수/위험어는 JSON config에 둠 | `pipeline.py`에 제작 문구 하드코딩 없음 | `test_script_generation_language_is_config_owned_not_pipeline_hardcoded` |
| Writer | 카드 구조 재설계 | 도화선 -> 갈림길 -> 근거 -> 빈칸 -> 오해/진실 -> 반론 -> 책임 -> CTA | 첫 화면 24자 안팎, 본문 84자 이하로 normalize 가능 | readability gate |
| Designer | 시각 문법 재설계 | 카드별 사건 재구성/풍자 테이블로/AiNo 진행자 컷, controlled kinetic still, 컷 전환 | 반복된 어두운 책상/파일 금지, 역할별 구도와 treatment 분리 | visual quality + actual diversity gate |
| Voice | TTS 구조 | 카드당 7~10초, 한국어 발음 사전 선적용 | ElevenLabs 실패 시 업로드 후보 차단 | audio asset provider gate |
| QA/Policy | 업로드 전 차단 기준 | 루머/건강/사생활/폭력 표현/가짜 뉴스 화면/AIGC 누락 차단 | 정책, 가독성, 이미지, TTS, 원본성 모두 통과 | `review_content` blockers |

### Side Effects

| 변경 | 사이드이펙트 | 대응책 |
| --- | --- | --- |
| 훅을 더 강하게 변경 | 과격/루머성 정치 콘텐츠로 기울 위험 | `unsafe_provocation_terms`, `risk_terms`, `policy_gate`로 건강/사생활/폭력 표현 감점 및 차단 |
| 검색가치 키워드 강화 | 해시태그 스팸 또는 제목 반복 위험 | metadata gate의 해시태그 수, caption 길이, title 중복 검수 유지 |
| 상위 레퍼런스 문법 반영 | 타 계정/뉴스 클립 복제 위험 | 뉴스 클립 단순 재업로드 금지, 자체 이미지/TTS/편집 원본성 유지 |
| AI 실사 이미지 강화 | 실제 사건 사진처럼 오해될 위험 | AIGC 공개 고지, 실존 인물 얼굴/정당 로고/읽히는 텍스트 금지 |
| 이미지 장면 다양화 | 생성 비용/실패 가능성 증가 | Codex image CLI 우선, Gemini fallback, 로컬 fallback은 업로드 후보 차단 |

### New Generation Contract

각 콘텐츠는 먼저 포맷을 고른다.

1. `1분 전말형`: 특검, 검찰개혁, 정부 조치, 수사/재판 이슈.
2. `비교형`: 토론, 기자회견, 국회 질의, 정책 발표.
3. `기준 3개형`: 경제, 민생, 행정, 공정성 논란.
4. `오해와 진실형`: 가짜뉴스 반박, 보수 프레임 대응, 발언 검증.
5. `감정-증거형`: 시민 안전, 노동, 참사, 공교육, 복지.

핫토픽 영상의 기본 구조는 다음으로 고정한다.

1. Hook: `{hook_headline}`
2. 도화선: 무엇이 보도됐나
3. 갈림길: 왜 사람들이 멈춰 보나
4. 근거: 어떤 출처에서 반복됐나
5. 빈칸: 아직 설명되지 않은 부분
6. 오해와 진실: 확인된 것과 확인 필요 주장 분리
7. 반론 가능성: 단정 전 확인할 것
8. 책임 기준: 왜 남겨야 하는가
9. CTA: `1 전말 / 2 근거 / 3 책임`

### Updated Config Ownership

- `hot_topic_strategy.json`: 레퍼런스 기반 쿼리, 위험어, 훅 규칙, provocation terms.
- `script_strategy.json`: 전말/근거/빈칸/책임형 hot-topic scene copy.
- `publish_quality_strategy.json`: `전말`, `오해`, `진실`, `침묵`, `특검`, `팩트체크`를 hook/retention/search scoring에 반영.
- `policy/source_registry.json`: 2026-05-14 카테고리 레퍼런스 리포트 등록.

### Acceptance Gate

업로드 후보가 되려면 아래가 모두 참이어야 한다.

- 첫 카드가 질문형 또는 기준형 훅이어야 한다.
- 영상 길이는 포맷별 목표 범위 안에 있어야 한다.
- `reward_deep`는 60초 이상, 2개 이상 출처, 검색가치 80점 이상이어야 한다.
- 모든 이미지는 주제와 카드 문구에 대응하는 실생성 이미지여야 한다.
- TTS는 ElevenLabs 생성본이어야 하며, fallback 음성은 업로드 후보가 아니다.
- AIGC 공개가 필요한 현실형 AI 이미지/오디오를 누락하면 차단한다.
- 건강/사생활/폭력/확정 비방/선거 절차 미검증 주장은 차단 또는 감점한다.

## Daily Format Mix

하루 3개를 모두 같은 구조로 만들지 않는다. 목적이 다르기 때문이다.

| Slot | Format | Target | Length | Purpose |
| --- | --- | --- | --- | --- |
| 08:10 | `growth_short` | 신규 유입 | 25-45s | 강한 질문형 hook으로 팔로우 전환 |
| 11:20 | `reward_deep` | 근거/팩트/정책 검증 | 65-95s | 1분 이상, 근거형 설명, 보상 프로그램 신호 최적화 |
| 19:30 | `debate_followup` | 감성/결집/참여 유도 | 45-75s | 댓글 반박, 추가 근거, 공유 유도 |

현재 CLI는 `--format auto|growth_short|reward_deep|debate_followup`을 지원한다.

하루 3개 전체 생성은 다음 실행기로 묶는다.

```powershell
python -m src.core.tiktok_aino.daily_runner --slot all --image-mode auto --real-image-limit 9
```

개별 슬롯만 생성할 때는 `--slot growth_short`, `--slot reward_deep`, `--slot debate_followup`을 사용한다.

최근성 기반 주제선정이 필요할 때는 명시적으로 hot discovery를 켠다.

```powershell
python -m src.core.tiktok_aino.daily_runner --slot growth_short --topic-mode hot --image-mode auto --real-image-limit 6
```

`--topic-mode hot`은 바로 고정 쿼리를 검색하지 않는다. 먼저 `keyword_strategy.json`의 넓은 `base_queries`로 최근 48시간 공개 보도 후보를 수집하고, 제목에서 함께 터지는 인물·기관·행동어를 뽑아 `keyword_plan.json`을 만든다. 그 결과로 `이재명/더불어민주당/민주당`, `윤석열/김건희/국민의힘/특검`, `선거/대선/여론조사` 같은 관심면을 구체 키워드로 확장한 뒤 Google News RSS를 다시 검색한다. 이후 최근성, 공개 이슈 키워드, TikTok 검색 수요에 가까운 인물·정당·선거 클러스터, 출처 신뢰도, 위험어 감점을 합산해 하나의 주제를 고른다. 보조 소스는 같은 인물명만 공유한다고 붙이지 않고, 공천개입/명태균/관저 이전/압수수색처럼 같은 세부 쟁점 토큰을 공유할 때만 붙인다. RSS 수집이 실패하면 기존 정적 참고 주제로 폴백하고 manifest의 `topic_discovery.reason`에 사유를 남긴다.

## Strategy Config SSOT

Documentary realism is also config-owned: `visual_strategy.json` defines `realism_principles`, `role_reality_beats`, and `documentary_realism` gates so generated images stay closer to photographed civic scenes with real texture, practical lighting, anonymous human traces, and clean overlay space.

Visual intensity is config-owned too. `drama_principles`, `role_intensity_beats`, `foreground_tension`, and `thumbnail_drama` prevent the image generator from drifting into polite empty backgrounds. Hook and why-now cards must use a dominant foreground object, compressed depth, hard shadow/reflection, and a readable first-second visual question while keeping real-person/logo/text safety constraints.

Scene treatment is config-owned as well. `visual_treatment_sequence`, `visual_treatments`, and `action_beats_by_role` force the generator to choose between realistic reconstruction, satirical tableau, fictional AiNo character scene, accountability stage, evidence action, and comment-choice scene. This prevents every card from becoming the same empty classroom, corridor, or document-table background.

No production strategy language belongs in `pipeline.py`. Prompt templates, script copy, fallback topic copy, hot-topic candidate wording, Codex image CLI style arguments, TTS pronunciation lexicon, policy/review messages, disclosure labels, quality marker strings, scoring thresholds, role beats, and safety wording must stay in JSON config; code should only render templates, load config, and evaluate configured markers.

운영 전략은 코드에 박지 않고 `src/core/tiktok_aino/config/` 아래 JSON을 SSOT로 둔다.

| File | Purpose |
| --- | --- |
| `keyword_strategy.json` | 넓은 seed query, seed basket, modifier, keyword scoring, query expansion, stopword, 선정/탈락 키워드 기록 기준 |
| `hot_topic_strategy.json` | RSS 검색 쿼리, 우선 쿼리, 신뢰 출처, 정치·사회 타깃 키워드, 리스크 키워드, hook 제목 규칙, 핫토픽 후보 title/angle/claim 템플릿, 핫토픽 점수표 |
| `editorial_strategy.json` | 토픽별 각도 선택, core question, viewer promise, must include/avoid 기준 |
| `planning_strategy.json` | script-first 기획 프레임, 장면별 viewer question/evidence need, narrative arc, 이미지 필요조건 템플릿, 선거·실존인물 안전규칙 |
| `script_strategy.json` | fallback topic, default/static script, hot-topic scene templates, caption/post/pinned comment, variant별 copy update, 짧거나 긴 문구 normalize 규칙 |
| `publish_quality_strategy.json` | search value, safe provocation, hook strength, retention, comment/follow CTA, policy gate terms, review blocker/note messages, disclosure label, publish score weight와 minimum |
| `tts_strategy.json` | 한국어 TTS 숫자 읽기, 단위 읽기, URL/해시태그/멘션/기호 발음 치환 |
| `visual_strategy.json` | issue/role 분류 키워드, role별 장소·카메라·앵커·팔레트, treatment/action beat, controlled motion, 색감 그레이딩, 반복 방지 문구, visual quality minimum |

코드는 위 설정을 읽어 판정과 렌더링을 수행한다. 따라서 핫한 주제 기준, 자극성 수위, 팔로우 유도 점수, 이미지 다양성 기준, 카드별 영화적 연출 톤, 대본 문구, 고지 문구, TTS 발음은 JSON을 수정해 조정한다. `pipeline.py`에 남는 값은 캔버스 크기, 모바일 safe zone, 폰트 최소값, 정규식/파일 처리처럼 렌더링 엔진 자체의 기술 상수만 허용한다.

## Production Flow

1. `build_signal_snapshot`
   - 넓은 베이스 쿼리로 수집한 최근 공개 보도 신호 원본, 감지된 seed/modifier/high-intent/risk terms를 `signal_snapshot.json`에 남긴다.
2. `build_keyword_plan`
   - 넓은 베이스 쿼리로 최근 공개 보도 신호를 모으고, 인물·기관·행동어 조합을 점수화한다.
   - 선정/탈락 키워드, 확장 검색 쿼리, 리스크 근거를 `keyword_plan.json`에 남긴다.
3. `build_topic_pool`
   - 확장 검색 결과를 쟁점 후보로 묶고 `topic_pool.json`에 후보별 키워드, 지원 출처, 리스크, 포맷 힌트를 남긴다.
4. `build_topic_plan`
   - 최근성, 출처 지원, 검색가치, 시각화 가능성, 정책 안전성을 점수화해 `topic_plan.json`에 선택 근거를 남긴다.
5. `route_content_format`
   - 근거가 충분하면 `reward_deep`, 댓글/반박 신호가 있으면 `debate_followup`, 빠른 발견형이면 `growth_short`를 선택한다.
6. `build_editorial_plan`
   - 토픽 제목과 포맷에 맞는 기본 각도, core question, viewer promise, must include/avoid를 `editorial_plan.json`에 남긴다.
7. `build_fact_pack`
   - 출처를 primary/support/official/counterpoint로 나누고, 확인된 사실·보도된 주장·반론·빈칸·금지 표현을 `fact_pack.json`에 고정한다.
   - `fact_pack`이 통과하지 않으면 이후 workflow contract에서 publish 후보가 차단된다.
8. `build_angle_brief`
   - viewer promise, 한 문장 논지, 타깃 감정, 공유 이유, 댓글 질문, 팔로우 이유, 안전한 자극 훅, 금지 프레임을 `angle_brief.json`에 고정한다.
   - 각본은 이 브리프 값을 topic discovery context로 받아 후속 문구와 CTA를 만든다.
9. `generate_script_variants`
   - `strong_hook`, `fact_pressure`, `empathy_parent`, `evidence_expose` 후보를 만든다.
10. `select_publish_script`
   - hook, safe provocation, search value, retention, comment trigger, follower conversion, monetization fit, policy safety, readability를 점수화해 1개만 선택한다.
11. `build_storyboard_brief`
   - 선택된 각본의 9장 각각에 narrative job, evidence id, visual job, TTS job, risk controls, overlay lane을 붙여 `storyboard_brief.json`에 고정한다.
12. `build_selected_script_plan`
   - 선택된 각본, 선택 이유, 품질 점수, gate 결과를 `selected_script.json`에 고정한다.
13. `build_content_plan`
   - 최종 각본을 장면별 `viewer_question`, `evidence_need`, `image_need`, `required_anchors`, `risk_controls`로 풀어 `content_plan.json`을 만든다.
   - 이미지 생성은 이 기획서의 장면 목적과 앵커를 기준으로만 진행한다.
14. `generate_visual_assets`
   - 1순위 Codex image CLI, 2순위 Gemini image API, 마지막 로컬 preview fallback 순서로 생성한다.
   - 로컬 fallback은 검수용일 뿐 업로드 후보로 인정하지 않는다.
15. `build_visual_plan`
   - `content_plan.image_need`와 실제 생성 asset/prompt를 연결해 `visual_plan.json`에 prompt lineage를 남긴다.
16. `build_tts_performance_plan`
   - ElevenLabs 호출 전에 장면별 pacing, 호흡, 강조어, 발음 alias 후보, pause를 `tts_performance_plan.json`에 고정한다.
17. `write_scene_synced_tts_audio`
   - ElevenLabs `Anna Kim` 계열 설정을 사용한다.
   - 카드별 TTS 길이에 맞춰 scene duration을 보정하고, 실패 시 Windows TTS preview로 떨어뜨리되 업로드 후보는 차단한다.
18. `render_artifacts`
   - Emits `tts_plan.json`, `render_manifest.json`, and `upload_plan.json` so upload automation can audit provider, render, and schedule decisions before touching TikTok.
   - 1080x1920 MP4, storyboard, manifest, verification report, signal/keyword/topic/editorial/script/content/visual plans, visual beats, TTS lint를 만든다.
19. `review_content`
   - 정책, 가독성, 이미지 실생성 여부, TTS provider, CTA, 수익화 적합성을 최종 차단한다.
20. Chrome Extension
   - `local_bridge.py`에서 최신 package를 가져와 TikTok 업로드 화면에 파일/캡션을 채운다.
   - CAPTCHA, 보안 경고, 로그인, 의심 활동 문구가 보이면 중단한다.
   - AIGC 라벨 후보를 클릭하되, 최종 public post는 사람이 확인한다.

## Visual Direction

- 실사에 가까운 영화적 다큐멘터리 스틸
- 한국 교실, 복도, 문서, 공공기관 분위기
- 실존 정치인 얼굴, 정당 로고, 읽을 수 있는 텍스트, 선거운동물, 아동 얼굴 금지
- 카드 텍스트는 이미지에 직접 생성하지 않고 렌더러가 안전영역에 얹는다
- 각 장면은 타이밍 관리를 위해 2-3개 visual beat로 나누고, 기본값은 `controlled_kinetic_still`이다. 미세한 pan/zoom과 일부 light sweep만 허용해 흔들림은 줄이되 완전 정지 화면처럼 보이지 않게 한다.
- 장면 사이에는 wipe, push, flash, dip, crossfade 전환을 넣어 컷 감각을 만든다.

### Visual Brief Gate

이미지는 단순 배경판이 아니라 카드별 의미를 시각화해야 한다. 최종 각본은 먼저 `content_plan.json`으로 풀리고, 각 scene은 이미지 생성 전에 `VisualBrief`로 변환된다.

`VisualBrief`는 다음 항목을 포함한다.

- `role`: hook, why_now, evidence, criteria, responsibility, verification, cta
- `issue_type`: court_case, investigation, national_assembly, education, labor, civic_fact_check
- `visual_intent`: 카드 문구를 어떤 시각 은유로 번역할지
- `visual_anchor`: 반드시 보일 소품/공간/구도
- `location`: 장면 장소
- `camera`: 카메라 거리와 앵글
- `emotion`: 장면 감정
- `palette`: 색감
- `treatment_id`: real_scene_reconstruction, satirical_tableau, aino_character_scene 등 장면 처리 방식
- `action_beat`: 문이 열림, 자료를 나눔, 빈 의자가 당겨짐처럼 이미지 안에서 보여야 하는 사건 순간
- `relevance_terms`: 주제/카드에서 추출한 핵심어
- `safety_constraints`: 실존 인물, 정당 로고, 읽히는 텍스트 등 금지 조건

업로드 후보가 되려면 `visual_quality`가 통과해야 한다.

| Gate | Minimum |
| --- | ---: |
| topic_relevance | 80 |
| scene_relevance | 78 |
| visual_metaphor | 80 |
| visual_variety | 75 |
| actual_visual_diversity | 84 |
| actual_palette_diversity | 78 |
| text_safe_space | 90 |
| policy_safety | 100 |
| cinematic_quality | 80 |

예를 들어 김건희/윤석열 의혹 클러스터에서는 같은 “어두운 사무실”을 반복하지 않고, 항소심 장면은 법원 복도와 봉인된 기록철, 무혐의/송치 장면은 분리된 수사 파일 트레이, 책임 장면은 빈 공청회장, CTA 장면은 댓글 카드가 놓인 편집 데스크로 분화한다.

실제 이미지 파일이 생성된 뒤에는 평균 해시, 색상 히스토그램, 평균 밝기, 평균 RGB 거리, 채도를 분리해 검사한다. `actual_visual_diversity`는 같은 구도/오브젝트 반복을 막고, `actual_palette_diversity`는 모든 장면이 같은 어두운 책상/문서 톤으로 수렴하는 문제를 막는다.

## Mobile Typography

폰트 크기는 1080x1920 원본 기준이 아니라 TikTok 모바일 표시 폭까지 환산해서 잡는다.

| Element | 1080px Render | 390px Preview Equivalent | Gate |
| --- | ---: | ---: | --- |
| Headline | 78px initial, 54px minimum | 19.5px minimum | 2 lines max |
| Body | 46px initial, 40px minimum | 14.4px minimum | 4 lines max, 84 chars max |
| Brand / Scene Number | 30px | 10.8px | non-critical |
| Footer / Duration | 24px | 8.7px | non-critical |

Critical text uses `x=104..936`, leaving at least 144px right margin. This avoids the TikTok right-side button rail. The critical text block must end above `y=1558`; TikTok bottom UI is modeled from `y=1660`, so progress/footer can sit lower because they are not needed for comprehension.

Every render now creates a TikTok mobile overlay preview:

- `mobile_previews/scene_XX_tiktok_mobile.png`: 390px-width phone preview with simulated right rail and bottom caption UI.
- `mobile_preview_storyboard.png`: all scenes with app overlay applied.
- `mobile_visual_checks.json`: pass/fail checks for right rail, bottom UI, and mobile font minimums.

Text length is normalized before rendering:

### Card News UI v3

카드뉴스 UI는 `publish_quality_strategy.json`의 `rendering.card_ui`가 관리한다. 렌더러는 이미지 위에 단순 검정 박스를 얹지 않고 아래 구조를 유지한다.

- 상단: 얇은 accent bar, 채널명, `01/09` 진행 번호, 공개 보도 기반 라벨만 남겨 이미지 몰입을 방해하지 않는다.
- 중단: 시네마틱 이미지가 주인공이 되도록 비워두고, 안전 영역 밖에는 TikTok UI 회피용 그라데이션만 둔다.
- 하단: 한 개의 어두운 editorial lower-third 패널 안에 역할/이슈 라벨, 헤드라인, 본문을 계층화한다.
- 헤드라인: 최대 2줄, 모바일 390px 기준 후킹 문구가 먼저 보이도록 동적 폰트 피팅을 적용한다.
- 본문: 최대 4줄, 흰색 박스 없이 같은 패널 안에서 구분선을 통해 읽히게 한다.
- 푸터: 장면 길이, AI 생성 이미지·시사 해설 라벨, segmented progress, AIGC 고지를 하단 안전 영역에 배치한다.
- 색상과 역할/이슈 라벨은 JSON 설정에서 조정하고, `pipeline.py`에는 렌더링 엔진 로직만 둔다.

- Headline shorter than 8 chars is expanded with context.
- Headline longer than 34 chars is compressed before font fitting.
- Non-hook/non-CTA headlines are tightened toward 24 chars where possible.
- Body shorter than 32 chars is expanded with evidence/CTA context.
- Body longer than 84 chars is sentence-compressed; if it still cannot fit, it is truncated and the readability gate blocks weak output in later checks.

## Quality Gates

업로드 후보가 되려면 모두 통과해야 한다.

- `GateResult.passed`: 정책, 출처, AIGC 공개, paid political ad 회피
- `ReadabilityResult.passed`: 장면 수, 장면 길이, 34자 이하 화면 문구, 84자 이하 모바일 본문, 95자 이하 장면 내레이션, 모바일 환산 제목 19px 이상, 본문 14px 이상, TikTok 오른쪽 레일/하단 UI 회피
- `PublishQualityResult.passed`: publish score 85 이상, 하위 점수 70 이상. `safe_provocation`은 자극적이되 단정적 비방이 아닌 질문형/기준형 훅을 요구하고, `search_value`는 Creator Rewards 검색가치 신호를 위해 실명·기관·사건·정책 키워드가 제목/캡션/본문에 살아 있어야 통과한다.
- `ContentReview.passed`: 모든 장면 실생성 이미지, ElevenLabs generated audio, 수익화/브랜드/시각 준비도 통과

## Tight Production Strategy

하루 3개는 같은 구조를 반복하지 않는다.

- 08:10 `growth_short`: 35~45초. 목표는 유입이다. 첫 장은 “무혐의면 끝인가?”, “누가 교실로 보냈나?”처럼 검색 키워드와 감정 대조가 같이 있어야 한다. 단, 단정형 비난은 차단한다.
- 11:20 `reward_deep`: 65~95초. 목표는 근거/팩트/정책 검증과 저장/완주다. 2개 이상 출처, 9~12장, 장면당 2개 이상 visual beat, 검색가치 80점 이상을 요구한다.
- 19:30 `debate_followup`: 45~75초. 목표는 감성/결집/참여 유도와 댓글 재점화다. 낮 콘텐츠의 댓글/반론을 다시 검증하는 구조로 이어간다.

새 게이트는 “괜찮은 말”을 막고 “클릭할 이유가 있는 질문 + 검색될 키워드 + 장면별 의미가 보이는 이미지”만 upload candidate로 보낸다.

## Performance Monitoring Loop

TikTok API 승인 없이 운영하므로 성과 데이터는 Chrome Extension이 TikTok Studio/Analytics 화면에서 로컬 브릿지로 저장한 `studio_metrics_*.jsonl`을 기준으로 분석한다. 이 데이터는 외부로 전송하지 않는다.

1. 업로드 또는 예약에 사용한 패키지를 `/job?run_id=<run_id>`로 로드한다.
2. 해당 영상의 TikTok Studio 상세/분석 화면에서 `Studio 지표 수집`을 실행한다.
3. `src.core.tiktok_aino.monitoring`이 manifest와 Studio 지표를 결합한다.
4. `early_2h`, `first_24h`, `day_3` 기준으로 조회수, 참여율, 댓글률, 공유율, 평균시청비율, 완주율, 팔로워 전환율을 점수화한다.
5. 결과는 다음 생성 큐에 반영한다. 이미 게시된 영상의 과격한 수정이나 재업로드는 기본 대응이 아니다.

대응 룰은 `config/monitoring_strategy.json`이 SSOT다.

- `strong_performer`: 24시간 내 후속편, 댓글 질문 기반 `debate_followup`, winning pattern 기록
- `low_views`: 새 핫이슈 교체, 첫 카드 질문 강화, 다른 키워드 클러스터 테스트
- `low_retention`: 첫 3초 결론형 질문, 카드 문장 축소, 25~35초 테스트
- `weak_comment_signal`: 고정 댓글을 기준 선택형 질문으로 전환
- `weak_share_signal`: 타임라인/기준표 구조로 저장·공유 가치 강화

### Feedback Into Scheduling

`monitoring.py` now emits canonical `performance_feedback.json` plus timestamped `performance_feedback_*.json` files from Studio snapshots or run-level metrics. `schedule_planner.py` and hot-topic discovery read that canonical feedback first, then apply term and format deltas to keyword ranking, topic candidate scoring, and daily format ordering. If Studio metrics are missing, `enabled=false` and planning remains unchanged.

`schedule_planner.py`는 최신 `performance_report_*.json`의 `feedback`을 읽어 다음 3일 큐에 반영한다. 실제 Studio 지표가 없는 상태에서는 `sample_count=0`이므로 플랜을 바꾸지 않는다. 지표가 쌓이면 strong 영상의 주제어와 포맷은 가점, respond 영상의 주제어와 포맷은 감점한다.

각 슬롯에는 아래 필드가 남는다.

- `performance_feedback`: 사용한 성과 리포트와 샘플 수
- `feedback_adjustment`: 해당 주제/포맷이 받은 가감점
- `source_count`: reward_deep의 보조 출처 수 확인용

### Reward Deep Upgrade

`reward_deep`은 Creator Rewards 후보 슬롯이므로 일반 카드뉴스보다 강한 조건을 갖는다.

- 최소 2개 출처를 요구한다.
- hot discovery 후보 중 같은 쿼리나 같은 세부 쟁점 클러스터의 보조 보도를 붙인다.
- 첫 장은 1분 전말 정리 프레임으로 시작한다.
- 중간 장면은 `사실 / 주장 / 책임` 분리 구조를 명시한다.
- 고정 댓글은 `1 전말 / 2 근거 / 3 책임`처럼 답하기 쉬운 번호형 질문으로 바꾼다.

## Current Known Constraint

Codex image CLI는 설치되어 있으나 현재 OpenAI 조직 검증 문제로 `gpt-image-2` 접근이 403 처리될 수 있다. 이 경우 같은 실행 안에서는 Codex provider를 unavailable로 표시하고 Gemini image API로 fallback한다.
