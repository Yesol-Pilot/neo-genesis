# AiNo Editorial OS v2 Design

## 결론

기존 파이프라인의 문제는 업로드 자동화가 아니라 생성 전 단계의 기획 품질과 생성 후 품질 게이트였다. `Editorial OS v2`는 업로드 전에 주제, 각본, 장면 설계, 시각 서명, 비평 점수를 모두 남기고, 반복 썸네일/반복 장면/반복 제목을 자동으로 차단한다.

## 운영 원칙

- 하루 3개 업로드 목표는 유지하되, `publish_ready`와 배치 품질 게이트를 통과하지 못한 슬롯은 업로드하지 않는다.
- 정치 콘텐츠는 공익 해설 톤으로 다룬다. 확인된 사실과 해석을 분리하고, 실존 정치인 얼굴 합성, 정당 로고, 공식 문서처럼 보이는 생성 이미지는 금지한다.
- 콘텐츠는 진보 지지층이 공유할 이유와 반대 의견이 댓글로 들어올 이유를 동시에 설계한다. 단, 투표 방법/일정/자격 같은 선거 참여 정보는 생성하지 않는다.
- 성과 측정은 하루 한 번 정해진 시간에만 실행한다. 개별 게시물 2시간/24시간/72시간 반복 측정 루프는 만들지 않는다.

## 제작 워크플로우

1. 이슈 후보 수집
   - 최신성, 출처 밀도, 갈등 명확성, 해설 가능성, 시각화 가능성, 댓글 유도성, 정책 안전성을 점수화한다.
   - 공식 집계 또는 원문 자료 1개 이상, 서로 다른 검증 가능한 보도 2개 이상이 채워지지 않으면 게시 게이트를 통과할 수 없다.

2. 에디토리얼 브리프
   - 한 문장 thesis, 반대 프레임, 공유 문장, 댓글 질문, TTS 방향, 정책 경계를 만든다.
   - 같은 제목 템플릿을 재사용하지 않고 주제별로 post title, caption, pinned comment를 커스터마이징한다.

3. 장면 설계
   - 최소 9개 장면을 만든다.
   - 첫 장면은 썸네일 역할, 마지막 장면은 선택형 CTA 역할을 맡는다.
   - 각 장면은 `location`, `camera`, `foreground_prop`, `palette`, `treatment`, `layout_id`, `diegetic_text`를 가진다.
   - 텍스트를 단순 오버레이로 덮는 대신, 이미지 생성 프롬프트에 짧은 in-image text를 넣을 수 있게 `diegetic_text`를 별도로 관리한다.

4. 시각 서명 생성
   - 주제 서명, 훅 서명, 첫 프레임 서명, 장소 배열, 카메라 배열, 소품 배열, treatment 배열, layout 배열을 저장한다.
   - 최근 게시물과 첫 프레임 또는 시각 배열이 과도하게 겹치면 폐기한다.

5. 비평 보드
   - editorial, audience, visual, policy 4개 critic이 각각 75점 이상이어야 한다.
   - visual critic은 장소 6개 이상, 카메라 6개 이상, 소품 7개 이상, 레이아웃 5개 이상, treatment 5개 이상을 요구한다.

6. 기존 파이프라인 연동
   - `pipeline._card_layout_quality`는 더 이상 `native_image_text`라는 이유만으로 통과하지 않는다.
   - `generate_from_schedule`은 manifest의 `visual_assets`와 `layout_quality`를 읽어 배치 단위 반복을 잡는다.
   - `ha_publisher`는 `content_fingerprint`와 별도로 `visual_fingerprint`를 저장해 제목이 달라도 같은 시각 템플릿이면 중복으로 차단한다.

## Canary 기준

현재 canary 주제는 `12대4 이후, '졌잘싸'가 안 먹힌 이유`다. 이 산출물은 업로드용 최종 영상이 아니라, 새 워크플로우가 요구하는 브리프/장면/시각 서명/비평/QA 산출물을 검증하기 위한 기준 패키지다.

필수 통과 기준:

- scene_count >= 9
- unique_locations >= 6
- unique_cameras >= 6
- unique_props >= 7
- unique_layouts >= 5
- unique_treatments >= 5
- editorial/audience/visual/policy critic >= 75
- blockers == []

## 업로드 재개 조건

업로드 자동화를 다시 켜기 전에 아래를 모두 만족해야 한다.

- canary 기반 전체 미디어 렌더 1개가 모바일 텍스트, TTS, 장면 다양성, 정책 게이트를 통과한다.
- 최근 게시물과 `content_fingerprint` 및 `visual_fingerprint`가 중복되지 않는다.
- TikTok AIGC 고지와 예약 시간이 manifest에 명시되어 있다.
- 예약 큐에는 하루 3개 이하만 들어가며, 성과 모니터링은 하루 1회만 실행된다.
