# W1 작업지시서 — narrative_confession 1호 생성 (Codex 실행용)

> 설계: Claude (EXECUTION_SPEC_FOLLOW_GROWTH_20260610.md §4b 기반)
> 목표: 주간 믹스의 narrative_confession 1호를 **publish_ready**까지. 게시/예약/푸시/커밋 금지.

## 0. 검증된 실행 레시피 (오늘 ranking 1호에서 확립 — 그대로 따를 것)

- python: `C:\Users\yesol\miniconda3\python.exe`, cwd = `D:\00.test\neo-genesis`
- 크레덴셜: `infra/agent-runtime/credential_loader.py` 의 `load_credentials(verbose=False)` 를 **반드시 먼저** 호출 (안 하면 ElevenLabs/실이미지 fallback)
- 프라이버시: `os.environ["AINO_PRIVACY_MODE"]="cloud_explicit"` (기본 local_only는 외부 생성 차단)
- 생성: `pipeline.run_for_topic(topic, sources, output_dir=..., image_mode="auto", real_image_limit=<장면수>, content_format="narrative_confession", topic_discovery={...})`
- 참고 러너: `D:\005.output\tmp\run_first_ranking.py` (구조 복사 권장)

## 1. 게이트 수치 (오늘 7회 반복으로 실측 확립 — 설계에 선반영할 것)

| 게이트 | 임계 | 설계 규칙 |
|---|---|---|
| body_text_under_format_limit | narrative=72자 | 행 body ≤66자, **마지막(CTA)행 ≤26자** (appendix +29~46자 자동 부착) |
| onscreen_text 8~24자 | 전 행 | screen 8~24자 |
| has_final_question | 최종 장면 | 마지막 행 body에 "?" 포함 |
| hook_strength ≥70 | scene1 | screen ≤24자(+20) + "?" in screen/body(+18) + hook_terms 포함(개당+9): 누가/진짜/이유/전말/진실/침묵/순위/숫자 등 (publish_quality_strategy.json script_quality.hook_terms) |
| duration ≤ 포맷 상한 | ElevenLabs 실측 | **내레이션 총 ≤450자** (78초 기준 실측: 507자→98s, 449자→78s). narrative 포맷 상한은 FORMAT_SPECS 확인 후 비례 적용 |
| actual_visual_diversity ≥80 | 이미지 픽셀 다양성 | 장면별 구체 장소/행동이 다르도록 body·역할 차별화 (회차 변동 있음) |
| 실이미지 | 일일예산 48, 오늘 ~29 사용 | **대본 게이트 통과 전까지 cloud 실행 금지** — 기본 local로 반복, 전 게이트 green 후 cloud_explicit 1회 (예산 ≤19장) |

## 2. 콘텐츠 설계 (Claude 확정 — 이 문안 기반, 게이트 맞춤 미세수정만 허용)

토픽(TopicCandidate): title="나는 정치를 멀리했던 사람입니다 — 어느 기록자의 고백", angle="고백 훅 → 전환점 서사(구체 장면) → 입장 선언 → 결집 문장 엔딩", slot="11:20 narrative", target_duration_sec=68
claims/source_ids: ranking 1호와 동일하게 `leftaino_public_analysis` + `tiktok_category_reference_analysis_20260514` (계정 성과·레퍼런스 사실 주장만)

행 설계 (10행, reference_storyboard_rules에 신규 rule로 추가 — rule[5] 구조 모방, match 조건은 "고백"/"기록자"/"멀리했던" 등 title 용어):

1. hook | screen "나는 정치를 멀리했다" | body "나는 정치를 멀리했던 사람입니다. 진짜 이유요? 바꿀 수 없다고 믿었으니까. 그런데 그날, 멈췄습니다." (질문+진짜=훅용어)
2. turning1 | screen "멈춰 선 그날 밤" | body "한밤 뉴스 속보. 거리로 나온 사람들. 나는 화면 앞에서 처음으로 부끄러웠습니다."
3. turning2 | screen "첫 기록의 시작" | body "다음 날부터 기록을 시작했습니다. 누가 무엇을 말했고, 무엇을 뒤집었는지."
4. turning3 | screen "기록이 쌓이자" | body "기록이 쌓이자 보였습니다. 말은 사라져도 기록은 남는다는 것."
5. stance | screen "그래서 입장을 정했다" | body "그래서 입장을 정했습니다. 기록하는 쪽. 기억하는 쪽. 침묵하지 않는 쪽."
6. tension | screen "불편한 질문 하나" | body "정치를 멀리하면 편합니다. 그 편안함의 값은 누가 치르고 있었을까요."
7. evidence | screen "기록이 증명한 것" | body "탄핵도 촛불도, 시작은 평범한 사람들의 기록과 기억이었습니다."
8. rally | screen "거짓은 무너진다" | body "거짓은 시간이 길어도 무너지고, 기록된 진실은 끝내 남습니다." (결집 문장 — 24.2% 좋아요율 검증 계열 신규 변주)
9. identity | screen "우리는 기록하는 사람들" | body "이 계정은 그 기록을 함께 쌓는 곳입니다. 당신의 그날은 언제였습니까?"
10. cta | screen "당신의 그날은?" | body "당신의 그날을 댓글로 남겨주세요?" (≤26자, "?" 포함)

## 3. 수락 기준 (전부 충족 시에만 DONE)

- [ ] manifest `status: publish_ready` + `upload_validation.upload_ready: true` + review blockers []
- [ ] 실이미지 = 전 장면 codex_cli/gemini (local_pillow 0) + audio = elevenlabs generated
- [ ] §5 가드 위반 0 (AI 고지 자동 포함 확인 / 선거 오정보 무관 주제)
- [ ] `pytest tests/core/test_tiktok_aino_tts.py -q` green (기준 148개+)
- [ ] 산출 경로·게이트 수치를 `D:\005.output\tmp\w1_narrative_result.md`에 기록

## 4. 금지

게시/예약/업로드 클릭, git commit/push, 다른 워크스트림 파일(schedule_planner.py, planning_strategy.json) 수정 금지. config 수정은 hot_topic_strategy.json의 신규 rule 추가 + (필요시) 본 지시서 행 문안 미세수정만.
