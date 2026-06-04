# TikTok AiNo Pipeline MVP

`@leftaino` / `올바른 AiNo`용 로컬 콘텐츠 생성 파이프라인입니다.
실제 TikTok 업로드는 하지 않고, 업로드 전 검토 가능한 영상 패키지와 리포트를 생성합니다.

## 문서 기준

- 전체 워크플로우 SSOT: `WORKFLOW_DESIGN_SPEC.md`
- 현재 구현/운영 설계: `PIPELINE_DESIGN.md`
- HA 게시 운영: `HA_RUNBOOK.md`

새 기능은 먼저 `WORKFLOW_DESIGN_SPEC.md`의 플로우와 artifact contract에 맞춰 설계하고, 그 다음 JSON config와 코드로 구현합니다.

## 레퍼런스 벤치마크 검수

Deep Research가 반환한 상위 숏폼 레퍼런스는 사람이 바로 설계에 섞지 않고, 먼저 URL 기반 검증을 통과해야 합니다.

```powershell
python -m src.core.tiktok_aino.reference_benchmark path\to\reference_benchmark.md --json
```

통과 기준:

- 직접 게시물 URL 20개 이상
- TikTok 8개 이상, YouTube Shorts 8개 이상
- URL은 `확인 불가` 불가
- 첫 1초/3초/5초 훅, 장면, 자막, 음성, CTA, pipeline rule이 행별로 존재

통과 전까지 `config/reference_codebook_provisional.json`은 비활성 참고자료이며, 최종 `reference_patterns.json`, `format_router.json`, `hook_patterns.json`, `scene_type_library.json`, `cta_patterns.json`로 승격하지 않습니다.

## 생성물

- 최소 9장 카드뉴스 기반 9:16 영상
- 1장 썸네일, 마지막 장 정리 + 댓글/팔로우/공유 CTA
- 1080x1920 MP4, storyboard, manifest, verification report
- 실감나는 영화 스틸형 배경 이미지
  - 1순위: Codex system image CLI
  - 2순위: Gemini image API
  - 로컬 Pillow 이미지는 비상 preview fallback이며 `upload_ready`를 차단
- TTS
  - 1순위: ElevenLabs API
  - Windows System.Speech는 비상 preview fallback이며 `upload_ready`를 차단
- 정책 게이트, 가독성 게이트, 에디토리얼 리뷰, 시각자료/TTS provider manifest
- `upload_ready`와 별도로 `publish_ready` 품질 게이트
- TikTok Studio 지표 기반 성과 리포트와 대응 플랜

## Publish Ready 품질 게이트

파이프라인은 같은 주제에서 여러 원고 후보를 먼저 만들고, 가장 점수가 높은 1개만 렌더링합니다.
현재 기본 후보는 `strong_hook`, `fact_pressure`, `empathy_parent`, `evidence_expose`입니다.

평가 축:

- `hook_strength`: 첫 카드가 1초 안에 멈춰 세우는지
- `retention_design`: 다음 장을 보게 만드는 질문/전개가 있는지
- `comment_trigger`: 댓글과 논쟁을 자연스럽게 유도하는지
- `follower_conversion`: 팔로우/다음 검증 CTA가 있는지
- `target_fit`: 좌파 성향 타겟과 교육/공정/기록 감성에 맞는지
- `monetization_fit`: 60초 이상, 카드 수, 해시태그 수익화 적합성
- `policy_safety`: 정책 게이트와 미검증/조작 위험
- `readability`: 모바일 가독성

상태 의미:

- `needs_revision`: 기술 또는 품질 게이트 미통과
- `upload_ready`: 기술적으로 업로드 가능하지만 publish 점수 미달
- `publish_ready`: 기술 게이트와 품질 게이트 모두 통과

기본 통과 기준은 `publish_ready_score >= 85`이며, 핵심 하위 점수는 70점 이상이어야 합니다.
모든 후보 점수는 `manifest.json`의 `quality.variant_scores`에 남습니다.

## HA 게시 운영

HA 운영은 `ha_publisher.py` 계층에서 관리합니다. `ysh-server`는 폐기 대상이고 회사 관련 자산은 사용할 수 없으므로, 중앙 큐/SSH/SCP/자격증명 동기화 대상에서 제외합니다. 현재 기본 운영은 `desktop-home`의 로컬 HA 상태와 로컬 Chrome/TikTok 세션을 사용합니다.

- 중앙 상태: `D:\00.test\neo-genesis\output\tiktok_aino_ha_state`
- 원격 업로드: 기본 비활성 (`AINO_REMOTE_UPLOAD_ENABLED=false`)
- 대체 후보: 개인 `yesol-asus`, 개인 Oracle Cloud control VM, 개인 Vertex AI 생성 backend
- Windows 예약 워커: `scripts/tiktok_aino_ha_worker.ps1 -Role upload`
- 운영 절차: `HA_RUNBOOK.md`

## ElevenLabs 기본 정책

기본 음성은 사용자가 기존에 쓰던 `Anna Kim`으로 고정합니다.
한국어 전용 단일 모델은 ElevenLabs API 모델 목록에 별도로 노출되지 않으므로, 기본 모델은 한국어와 `style`/`speaker boost` 설정을 함께 지원하는 `eleven_multilingual_v2`로 둡니다.

`eleven_v3`, `eleven_flash_v2_5`, `eleven_turbo_v2_5`도 한국어 TTS를 지원하지만, 현재 파이프라인의 기본값은 다음 이유로 `eleven_multilingual_v2`입니다.

- `Anna Kim` + 기존 슬라이더 설정과 가장 호환적임
- 긴 내레이션 안정성이 높음
- `stability`, `similarity_boost`, `style`, `use_speaker_boost`, `speed`를 요청 단위로 제어 가능

히스토리 저장을 피하려면 `ELEVENLABS_ENABLE_LOGGING=false`를 사용합니다.
ElevenLabs 공식 API 기준으로 이 옵션은 zero retention 요청이며, 계정 플랜이 허용하지 않으면 파이프라인은 기록 저장 재시도를 하지 않고 TTS를 실패 처리합니다.

## 한국어 TTS 전처리

파이프라인은 화면용 `script.narration`을 그대로 읽히지 않고, TTS 전용 원고를 새로 만듭니다.
생성 결과는 매 실행마다 `narration_tts_ko.txt`와 `narration_tts_lint.json`으로 저장됩니다.

전처리 우선순위:

1. `account/ko_tts_pronunciation.json`의 로컬 alias를 적용합니다.
2. URL, 멘션, 해시태그, 슬래시, 괄호, 특수기호를 읽기 쉬운 한국어 표현으로 바꿉니다.
3. 날짜, 시간, 퍼센트, 숫자+단위, 범위를 한국어 발음 원고로 풀어 씁니다.
4. 영문 약어, 숫자, 위험 기호, 긴 문장 잔존 여부를 lint로 남깁니다.

작성 기준:

- 화면 문구: `올바른 AiNo가 3개 플랫폼에 자동 업로드`
- TTS 문구: `에이아이 봇이 세 개 플랫폼에 자동으로 올립니다.`
- `18~49세`: `십팔 세에서 사십구 세`
- `2026.05.11`: `이천이십육년 오월 십일`
- `12%`: `십이 퍼센트`
- `@leftaino`: `레프트 아이노 계정`

## 카드별 음성 싱크

기본 렌더링은 `AINO_SCENE_AUDIO_SYNC=true`로 동작합니다.
각 카드의 `scene.body`를 별도 TTS로 생성하고, 실제 오디오 길이에 맞춰 카드 duration을 자동으로 재계산합니다.

산출물:

- `scene_audio/scene_XX.mp3`: 카드별 ElevenLabs 원본 오디오
- `scene_tts_text/scene_XX.txt`: 카드별 TTS 전용 원고
- `scene_audio_padded/scene_XX.wav`: 카드 duration에 맞춘 패딩 오디오
- `narration_scene_synced.wav`: 전체 영상용 합성 오디오
- `narration_tts_lint.json`: 카드별 실제 오디오 길이, 카드 duration, 패딩 길이, lint 결과

duration 정책:

- 카드 최소 체류 시간은 7초
- 카드 duration은 `ceil(실제 음성 길이 + 0.55초)` 기준
- 영상은 `synced_scenes` 기준으로 렌더링되며, manifest에 원본 duration과 보정 duration을 모두 남김

## 실행

```powershell
python -m src.core.tiktok_aino.pipeline
```

9장 전체를 실제 이미지 우선으로 생성합니다.

```powershell
python -m src.core.tiktok_aino.pipeline --image-mode auto --real-image-limit 9
```

비용/시간 절약용 로컬 미리보기입니다. 이 결과는 업로드 후보가 아닙니다.

```powershell
python -m src.core.tiktok_aino.pipeline --image-mode local --real-image-limit 0
```

## 성과 모니터링

`monitoring.py` writes both `performance_report_*.json` and canonical `performance_feedback.json`. The next hot-topic discovery and schedule plan use `performance_feedback.json` first, then apply term and format deltas to keyword ranking, topic scoring, and slot ordering.

확장 프로그램에서 해당 `run_id`를 로드한 뒤 TikTok Studio 영상 상세/분석 화면에서 `Studio 지표 수집`을 실행한다. 로컬 브릿지는 `studio_metrics_*.jsonl`에 원본 지표 텍스트와 `run_id`를 저장한다.

```powershell
python -m src.core.tiktok_aino.monitoring --output-dir output\tiktok_aino_scheduled_packages --run-id <run_id>
```

리포트는 `views`, `likes`, `comments`, `shares`, `saves`, `average_watch_time_sec`, `completion_rate`, `followers_gained`를 정규화하고, `early_2h`, `first_24h`, `day_3` 기준으로 다음 콘텐츠 대응 액션을 만든다.

성과 리포트가 생성되면 다음 스케줄 플랜은 자동으로 최신 리포트의 `feedback`을 읽는다. 실제 Studio 지표가 아직 없으면 `sample_count=0`으로 남고 플랜에는 영향을 주지 않는다.

```powershell
python -m src.core.tiktok_aino.schedule_planner --days 3 --output-dir output\tiktok_aino_schedule_plans
```

`reward_deep` 슬롯은 최소 2개 출처를 요구하며, 같은 쿼리나 같은 쟁점 클러스터의 보조 보도를 자동으로 붙인다. 부족하면 `reward_deep_source_count_lt_2` blocker가 생긴다.

## Operational Hardening

- Chrome Extension Studio capture writes `studio_metrics_capture_v2` payloads with body text, structured metric nodes, snapshots, capture quality, and warnings.
- The local bridge enriches `/metrics` payloads with `normalizedMetrics` and `capture_quality` before appending `studio_metrics_*.jsonl`.
- External image generation follows `image_budget_strategy.json`: policy gate, readability, publish quality, `publish_ready_score >= 85`, per-run cap, and daily cap must pass before `codex_cli` or `gemini_api` is called.
- `AINO_PRIVACY_MODE=local_only` or `--image-mode local` forces local fallback images. Preview artifacts may render, but upload remains blocked.
- HA monitoring claims jobs only on the 2h, 24h, and 72h cadence after the publish/schedule reference time. Each monitor run records report paths, feedback paths, completed windows, and `next_monitor_at` in job evidence.

## 환경변수

```powershell
$env:ELEVENLABS_API_KEY="..."
$env:ELEVENLABS_VOICE_ID="..."
$env:ELEVENLABS_VOICE_NAME="Anna Kim"
$env:ELEVENLABS_MODEL_ID="eleven_multilingual_v2"
$env:ELEVENLABS_LANGUAGE_CODE="ko"
$env:ELEVENLABS_OUTPUT_FORMAT="mp3_44100_128"
$env:ELEVENLABS_SPEED="1.09"
$env:ELEVENLABS_STABILITY="0.12"
$env:ELEVENLABS_SIMILARITY_BOOST="0.18"
$env:ELEVENLABS_STYLE="0.07"
$env:ELEVENLABS_USE_SPEAKER_BOOST="true"
$env:ELEVENLABS_ENABLE_LOGGING="false"
$env:GEMINI_API_KEY="..."
```

## 주의

- 실제 업로드 전에는 보도 링크, 공식 반론, 후속 보도를 추가 확인해야 합니다.
- 실존 정치인 얼굴, 정당 로고, 읽히는 텍스트는 AI 이미지로 생성하지 않습니다.
- 유료 정치 광고, 미검증 선거 정보, 실제 발언처럼 보이는 AI 음성/영상 조작은 정책 게이트에서 차단합니다.
