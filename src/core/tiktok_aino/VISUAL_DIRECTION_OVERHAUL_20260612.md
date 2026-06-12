# 비주얼 방향 전환 스펙 — 양산형 실사 → 텍스트·키네틱 (2026-06-12)

> 설계: Claude Fable 5 (owner 시각검증 지적: "양산형, 틱톡 최적화 안 됨, 이미지 생성 가치 없음")
> 구현: Codex 워커 / 근거: reference_benchmark_url_first_playback_verified_20260529.md + 실 프레임 육안 검증

## 0. 진단 (확정)

**owner 정확함.** 6/11~12 생성 2영상 실 프레임 육안 검증 결과:
- ranking 10장 중 6장이 동일 구성(어두운 회의실+익명 군중+갈색 톤). "5위 문재인/4위 박정희" 리빌에 인물·시대·단서 0 → **텍스트 카드와 차이 없음**.
- narrative 10장 거의 전부 어두운 실루엣 단색 — 장면 구분 불가.
- 게이트 `actual_visual_diversity`(87)는 픽셀/팔레트만 측정, "주제별 비트·텍스트 대비 우위" 미측정 → 양산형 통과.

**근본 원인 (config가 거꾸로 잠김)**:
1. `scene_type_library.json` 전 장면이 법적 제약(no real politician likeness)으로 `generic 회의실/군중/외관` 하드코딩 → 정치 주인공을 못 보여주니 익명 방으로 귀결.
2. `visual_strategy.json:1249` 가 `text card, placard, poster 금지` → 틱톡 네이티브의 핵심(타이포·그래픽)을 차단.
3. 결과: 합법적으로 가치 있는 유일 매체를 금지하고, 가치 없는 실사를 강제.

**레퍼런스 증거**: 51만/31만 조회 원형 전부 `real_clip_with_large_caption_overlay` + 고밀도 자막(12~22자/줄). 우리는 real clip/face 불가 → **"큰 자막 + 디자인"이 곧 원형의 작동 엔진**.

## 1. 새 비주얼 방향 (포맷별)

### ranking_battle → **kinetic_ranking_card** (디자인이 주인공)
- 매체: 실사 사진 폐기. 풀스크린 그래픽 카드 — 대형 순위 숫자(5→1), 항목명 대형 타이포, 기준 3개 색상 코딩(민주주의=청 / 위기회복=주황 / 유산=크림), 강한 대비.
- 배경: AI 이미지는 **저대비 텍스처/그라데이션 배경으로만** (서브, 주인공 아님). 또는 순수 그래픽 배경.
- 각 순위 리빌 = 시각적으로 명확히 다른 카드 (숫자·색·항목명이 비트를 만듦, 익명 방 아님).
- 훅(scene1): 대형 "역대 대통령 TOP5" 타이포 + 기준 미리보기. 첫 1초 가독.

### narrative_confession → **kinetic_quote** (자막 강조 + 무드 1~2장)
- 고백 서사는 강한 무드 배경 1~2종(어두운 새벽/촛불 톤)으로 충분 — **10장 실사 생성 폐기**.
- 핵심 문장(결집 엔딩 "거짓은 무너지고…")을 대형 타이포로 강조하는 모션 카드.
- 비용 절감 동시 달성: 실이미지 10→2.

### reformed_briefing → 기존 유지 (뉴스 기반, 별도 판단)

## 2. config 변경 (Codex 구현)

1. `visual_strategy.json`: `controlled_kinetic_still` 모드를 ranking/narrative 기본 경로로 승격. line 1249 금지목록에서 정치 랭킹·서사 한정 `text card/placard` 해제 (단 fake broadcast UI·party logo·real-person synthesis 금지는 유지). 신규 디자인 토큰: rank_number_typography, criteria_color_code, hero_caption_layout.
2. `scene_type_library.json`: ranking/narrative용 신규 layout type 추가 — `kinetic_ranking_card`, `kinetic_quote_card`, `criteria_legend_card`. 기존 generic 실사 타입은 reformed_briefing 전용으로 격하.
3. `pipeline.py` 렌더: 위 카드 타입을 실제 렌더하는 경로 (대형 숫자·항목 타이포 합성). 기존 실사 합성 코드는 reformed_briefing 분기로 보존.

## 3. 신규 품질 게이트 (양산형 재발 차단)

- **frame_distinctiveness 게이트 추가**: 인접 장면 간 "주제 단서 차이" 측정 — 같은 layout_type 3연속 금지 강화 + 랭킹은 각 카드의 순위 숫자/항목명이 실제로 다른지 검증.
- **owner 시각검증 게이트 (P0, 일시적)**: 비주얼 방향 전환 후 **첫 3편은 Fable이 storyboard.png 육안 검증 + owner 1회 승인** 후에만 예약. 안정화되면 자동화로 복귀.
- 게이트 통과 = "publish_ready" 외에 "visually_distinct" 추가 플래그.

## 4. 검증 (수락 기준)

- [ ] 새 방향으로 ranking 1편 재생성 → storyboard 육안: 10장이 시각적으로 명확히 구별 (순위별 다른 숫자·색·항목), 어두운 방 반복 0
- [ ] narrative 1편 → 무드 1~2장 + 자막 강조 카드, 실이미지 ≤2장 (비용 절감)
- [ ] pytest tts 스위트 회귀 0
- [ ] Fable 육안 + owner 승인 전까지 예약 금지

## 5. 금지 (불변)

real-person face synthesis / 실제 클립 재사용 / party logo / fake broadcast lower-third / 선거 오정보. AI 고지 유지.
