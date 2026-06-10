"""Editorial planning and quality gates for AiNo short-form packages.

The module is intentionally offline and deterministic. It creates a publish
candidate brief, a scene-level production plan, a content signature, and a
critic report before any expensive media generation or browser upload can run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable


VERSION = "editorial_os_v2.0"
MIN_SCENE_COUNT = 9
MIN_UNIQUE_LOCATIONS = 6
MIN_UNIQUE_CAMERAS = 6
MIN_UNIQUE_PROPS = 7
MIN_UNIQUE_LAYOUTS = 5
MIN_UNIQUE_TREATMENTS = 5
MAX_DIEGETIC_TEXT_CHARS = 18
CRITIC_PASS_SCORE = 75

FORBIDDEN_VISUAL_MARKERS = {
    "real politician likeness",
    "party logo",
    "official election document replica",
    "fake news lower third",
    "fake government seal",
}


def _contains_forbidden_marker(text: str, marker: str) -> bool:
    lower = text.casefold()
    marker_lower = marker.casefold()
    if marker_lower not in lower:
        return False
    negations = (
        f"no {marker_lower}",
        f"without {marker_lower}",
        f"not {marker_lower}",
        f"no {marker_lower}s",
        f"without {marker_lower}s",
        f"not {marker_lower}s",
    )
    return not any(negation in lower for negation in negations)


@dataclass(frozen=True)
class IssueCandidate:
    candidate_id: str
    title: str
    core_question: str
    public_interest_angle: str
    audience_trigger: str
    opposing_trigger: str
    comment_question: str
    source_requirements: list[str]
    trend_inputs: list[str]
    risk_notes: list[str]
    score_axes: dict[str, int]


@dataclass(frozen=True)
class EditorialBrief:
    version: str
    channel_name: str
    issue: IssueCandidate
    thesis: str
    narrative_arc: list[str]
    voice_direction: str
    tts_direction: dict[str, Any]
    policy_boundary: list[str]
    publish_gate: list[str]
    post_title: str
    caption: str
    hashtags: list[str]
    pinned_comment: str


@dataclass(frozen=True)
class SceneDesign:
    scene_id: int
    role: str
    hook_text: str
    narration: str
    visual_prompt: str
    location: str
    camera: str
    foreground_prop: str
    palette: str
    treatment: str
    layout_id: str
    diegetic_text: str
    transition: str
    qa_focus: list[str]


@dataclass(frozen=True)
class ContentSignature:
    version: str
    topic_signature: str
    hook_signature: str
    script_structure: list[str]
    visual_locations: list[str]
    camera_styles: list[str]
    foreground_props: list[str]
    palettes: list[str]
    treatments: list[str]
    layout_ids: list[str]
    first_frame_signature: str
    cta_type: str
    fingerprint: str


@dataclass(frozen=True)
class CriticScore:
    critic: str
    score: int
    passed: bool
    notes: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EditorialCanaryPackage:
    version: str
    generated_at: str
    seed: str
    brief: EditorialBrief
    scenes: list[SceneDesign]
    signature: ContentSignature
    critics: list[CriticScore]
    qa_report: dict[str, Any]


def _stable_hash(*parts: Any, length: int = 16) -> str:
    payload = "|".join(str(part or "").strip().casefold() for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        clean = str(value or "").strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        out.append(clean)
    return out


def _score_candidate(candidate: IssueCandidate) -> int:
    weights = {
        "recency": 1.1,
        "source_density": 1.3,
        "conflict_clarity": 1.2,
        "explainability": 1.0,
        "visual_potential": 1.2,
        "comment_potential": 1.2,
        "policy_safety": 1.1,
    }
    weighted = 0.0
    total_weight = 0.0
    for key, weight in weights.items():
        weighted += int(candidate.score_axes.get(key, 0)) * weight
        total_weight += weight
    return round(weighted / max(1.0, total_weight))


def build_issue_candidates(seed: str = "election_12_4") -> list[IssueCandidate]:
    """Return ranked issue candidates for the canary run.

    The default seed is based on the owner's recent brief, but the candidate
    keeps source verification as a hard publish gate instead of pretending the
    live facts have already been checked.
    """

    candidates = [
        IssueCandidate(
            candidate_id="election_result_frame_12_4",
            title="12대4 이후, 보수의 '졌잘싸' 프레임은 왜 안 먹혔나",
            core_question="숫자 자체보다, 왜 책임 회피 프레임이 지지층 밖에서 설득력을 잃었는가?",
            public_interest_angle="선거 결과를 승패 자랑이 아니라 책임 신호와 여론 해석의 문제로 다룬다.",
            audience_trigger="진보 지지층이 공유하기 쉬운 '심판 여론은 변명이 아니라 숫자다' 프레임",
            opposing_trigger="보수 지지층이 반박하고 싶어지는 '졌잘싸가 아니라 구조적 책임' 프레임",
            comment_question="이 결과를 실력 차로 봐야 하나, 심판 여론으로 봐야 하나?",
            source_requirements=[
                "공식 선거 결과 또는 선관위/공공기관 집계 1개 이상",
                "서로 다른 성향의 검증 가능한 언론 보도 2개 이상",
                "캠프 또는 정당 주장 인용 시 반론과 맥락을 함께 표기",
            ],
            trend_inputs=[
                "선거 결과 숫자 프레임",
                "졌잘싸 논쟁",
                "책임론과 심판론",
                "지지율 해석 댓글전",
            ],
            risk_notes=[
                "실존 정치인 얼굴 합성 금지",
                "정당 로고와 공식 문서처럼 보이는 이미지 금지",
                "투표 방법, 일정, 자격 등 선거 참여 정보 생성 금지",
            ],
            score_axes={
                "recency": 86,
                "source_density": 78,
                "conflict_clarity": 91,
                "explainability": 88,
                "visual_potential": 90,
                "comment_potential": 92,
                "policy_safety": 82,
            },
        ),
        IssueCandidate(
            candidate_id="accountability_frame_gap",
            title="책임론을 피하는 순간, 댓글은 더 거칠어진다",
            core_question="왜 방어형 메시지는 지지층 결집보다 반감을 더 키우는가?",
            public_interest_angle="정치 커뮤니케이션의 실패를 시민 눈높이와 책임 언어로 해설한다.",
            audience_trigger="말보다 책임을 요구하는 진보 감성",
            opposing_trigger="정치 공세라고 반박하고 싶어지는 책임론 프레임",
            comment_question="정치권의 해명은 어디까지가 설명이고 어디부터가 회피일까?",
            source_requirements=[
                "최근 여론조사 또는 선거 결과 공식 수치",
                "해당 발언 원문 또는 전문 링크",
                "해설 기사 2개 이상",
            ],
            trend_inputs=["책임론", "정치 해명", "댓글 여론"],
            risk_notes=["개인 비방 금지", "확인되지 않은 의혹 단정 금지"],
            score_axes={
                "recency": 77,
                "source_density": 76,
                "conflict_clarity": 84,
                "explainability": 84,
                "visual_potential": 78,
                "comment_potential": 86,
                "policy_safety": 86,
            },
        ),
    ]
    if seed != "election_12_4":
        return sorted(candidates, key=_score_candidate, reverse=True)
    return candidates


def select_issue(seed: str = "election_12_4") -> IssueCandidate:
    return max(build_issue_candidates(seed), key=_score_candidate)


def build_editorial_brief(candidate: IssueCandidate | None = None, *, seed: str = "election_12_4") -> EditorialBrief:
    issue = candidate or select_issue(seed)
    return EditorialBrief(
        version=VERSION,
        channel_name="올바른 AiNo",
        issue=issue,
        thesis="결과가 남긴 핵심은 승패 자랑이 아니라, 어떤 프레임이 더 이상 통하지 않는지다.",
        narrative_arc=[
            "첫 장면에서 숫자와 프레임 충돌을 바로 던진다.",
            "상대 진영의 방어 논리를 먼저 제시해 댓글 반응 지점을 만든다.",
            "그 방어 논리가 왜 설득력을 잃었는지 생활감 있는 장면으로 쪼갠다.",
            "반론 가능성을 남기되 책임론의 결론은 선명하게 닫는다.",
            "마지막은 시청자가 해석을 고르게 만드는 질문으로 끝낸다.",
        ],
        voice_direction="차분하지만 날카로운 뉴스 해설 톤. 조롱보다 '숫자가 말한다'는 냉정함을 유지한다.",
        tts_direction={
            "provider_preference": "elevenlabs",
            "voice": "Anna Kim",
            "model_family": "Korean-strong multilingual or Korean-optimized model",
            "speed": 1.06,
            "style": "restrained anger",
            "pronunciation_notes": [
                "12대4는 '십이 대 사'로 읽게 쓴다.",
                "졌잘싸는 첫 언급에 '졌지만 잘 싸웠다'를 풀어 말한다.",
                "짧은 문장과 쉼표를 사용해 모바일 TTS 호흡을 만든다.",
            ],
        },
        policy_boundary=[
            "정치인 실물 얼굴, 정당 로고, 공식 문서처럼 보이는 생성물은 쓰지 않는다.",
            "확인된 결과와 해석을 분리한다.",
            "투표 방법, 일정, 자격 같은 선거 참여 정보는 생성하지 않는다.",
            "AIGC 고지는 업로드 단계에서 확인한다.",
        ],
        publish_gate=[
            "source_requirements가 실제 URL로 충족되어야 한다.",
            "9개 이상 장면, 6개 이상 장소, 6개 이상 카메라, 7개 이상 전경 소품을 통과해야 한다.",
            "최근 게시물과 첫 프레임/제목/시각 서명이 80% 이상 겹치면 폐기한다.",
            "모바일 미리보기에서 텍스트 넘침이 없어야 한다.",
        ],
        post_title="12대4 이후, '졌잘싸'가 안 먹힌 이유",
        caption=(
            "결과를 자랑하려는 게 아닙니다. 숫자가 끝난 뒤에도 책임을 피하려는 프레임이 "
            "왜 설득력을 잃었는지 보자는 겁니다. 여러분은 이걸 실력 차로 보나요, 심판론으로 보나요?"
        ),
        hashtags=["정치", "선거", "지지율", "민심", "책임론", "진보", "뉴스해설", "올바른AiNo"],
        pinned_comment="여러분은 '졌잘싸'라고 보나요, 책임 회피라고 보나요? 반박도 근거 있게 남겨주세요.",
    )


def build_scene_design_plan(brief: EditorialBrief) -> list[SceneDesign]:
    return [
        SceneDesign(
            scene_id=1,
            role="thumbnail",
            hook_text="12대4, 이걸 '졌잘싸'라고?",
            narration="선거가 끝나면, 늘 프레임 싸움이 시작됩니다. 그런데 이번 숫자는 꽤 차갑습니다.",
            visual_prompt=(
                "cinematic realistic election-night analysis room, giant abstract result wall with no party logos, "
                "wet city lights outside, a single paper card in foreground reading 12대4, dramatic but not fake-news UI"
            ),
            location="election-night analysis room",
            camera="low angle close-up with result wall background",
            foreground_prop="paper card marked 12대4",
            palette="cold white, signal red, muted charcoal",
            treatment="cinematic_results_room",
            layout_id="impact_cover",
            diegetic_text="12대4?",
            transition="hard cut on number reveal",
            qa_focus=["thumbnail contrast", "no logo", "diegetic text legible"],
        ),
        SceneDesign(
            scene_id=2,
            role="context",
            hook_text="숫자는 변명보다 빠르다",
            narration="핵심은 누가 웃었냐가 아닙니다. 어떤 설명이 사람들에게 더 이상 먹히지 않았냐입니다.",
            visual_prompt=(
                "realistic newsroom desk with abstract district tiles, verification sticky notes, hands sorting neutral reports, "
                "no real person likeness, no official seals"
            ),
            location="verification newsroom desk",
            camera="top-down sorting shot",
            foreground_prop="district tile board",
            palette="paper white, ink black, muted teal",
            treatment="evidence_desk",
            layout_id="top_split",
            diegetic_text="변명보다 숫자",
            transition="map tiles slide into frame",
            qa_focus=["source-boundary feel", "not official document replica"],
        ),
        SceneDesign(
            scene_id=3,
            role="opposing_frame",
            hook_text="'졌잘싸' 프레임의 약점",
            narration="졌지만 잘 싸웠다. 이 말은 위로가 될 수는 있어도, 책임을 대신할 수는 없습니다.",
            visual_prompt=(
                "satirical debate table, two blank placards labeled 해명 and 책임, empty chair under harsh studio light, "
                "editorial photo realism, no logos"
            ),
            location="empty debate studio",
            camera="center-framed medium shot",
            foreground_prop="two placards: 해명, 책임",
            palette="studio black, warm tungsten, red accent",
            treatment="satirical_debate_table",
            layout_id="side_rule",
            diegetic_text="해명 vs 책임",
            transition="placard snap zoom",
            qa_focus=["satire clear", "no individual likeness"],
        ),
        SceneDesign(
            scene_id=4,
            role="why_now",
            hook_text="샤이 지지층? 아니면 책임 피로감?",
            narration="늘 나오는 설명이 있습니다. 숨은 지지층, 언론 탓, 프레임 탓. 그런데 시민은 생활로 판단합니다.",
            visual_prompt=(
                "campaign war room after midnight, cold coffee cups, abandoned talking-point sheets, city rain reflection, "
                "realistic cinematic still"
            ),
            location="after-midnight campaign room",
            camera="wide shot through glass reflection",
            foreground_prop="abandoned talking-point sheets",
            palette="rain blue, stale beige, neon reflection",
            treatment="abandoned_war_room",
            layout_id="receipt_panel",
            diegetic_text="핑계의 방",
            transition="glass reflection dissolve",
            qa_focus=["distinct from newsroom", "foreground tension"],
        ),
        SceneDesign(
            scene_id=5,
            role="public_cost",
            hook_text="민생은 방어 논리를 기다려주지 않는다",
            narration="정치는 해석 싸움이지만, 장바구니와 월급명세서는 해석을 기다려주지 않습니다.",
            visual_prompt=(
                "realistic convenience store counter at night, receipt roll, grocery basket, muted TV glow in background, "
                "public frustration without showing real politician or network logo"
            ),
            location="night convenience store counter",
            camera="macro foreground receipt with soft background",
            foreground_prop="long receipt roll",
            palette="fluorescent green, receipt white, asphalt gray",
            treatment="life_cost_closeup",
            layout_id="bottom_receipt",
            diegetic_text="민생은 기다리지 않음",
            transition="receipt pull cut",
            qa_focus=["life relevance", "text under 18 chars"],
        ),
        SceneDesign(
            scene_id=6,
            role="comment_trigger",
            hook_text="댓글이 터지는 지점",
            narration="진보 지지층은 심판이라고 읽고, 반대편은 과장이라고 말합니다. 그래서 댓글이 붙습니다.",
            visual_prompt=(
                "phone reflected on cafe window with abstract comment bubbles, no real app UI, split reactions as colored light, "
                "cinematic shallow depth of field"
            ),
            location="cafe window reflection",
            camera="over-shoulder phone reflection",
            foreground_prop="abstract comment bubbles",
            palette="cyan reflection, magenta accent, warm cafe",
            treatment="comment_battle_reflection",
            layout_id="witness_stage",
            diegetic_text="심판? 과장?",
            transition="comment bubbles pop in",
            qa_focus=["engagement trigger", "no real platform UI"],
        ),
        SceneDesign(
            scene_id=7,
            role="share_line",
            hook_text="공유되는 한 문장",
            narration="결과를 축제로만 소비하면 금방 식습니다. 하지만 책임의 언어로 바꾸면 공유할 이유가 생깁니다.",
            visual_prompt=(
                "rainy street billboard with generated civic slogan, pedestrians as silhouettes, cinematic public square, "
                "not a campaign ad, no party colors dominating"
            ),
            location="rainy public square billboard",
            camera="street-level long lens",
            foreground_prop="civic slogan billboard",
            palette="wet asphalt, soft yellow, restrained red",
            treatment="public_slogan_scene",
            layout_id="choice_stack",
            diegetic_text="책임은 숫자다",
            transition="billboard light flicker",
            qa_focus=["shareable line", "not official campaign material"],
        ),
        SceneDesign(
            scene_id=8,
            role="fairness",
            hook_text="반론도 놓고 보자",
            narration="물론 숫자 하나로 모든 걸 설명할 수는 없습니다. 그래서 반론과 원자료를 같이 놓아야 합니다.",
            visual_prompt=(
                "fact-check table with three source folders, red string absent, clean documentary lighting, neutral hands, "
                "source labels as generic A B C only"
            ),
            location="fact-check archive table",
            camera="side dolly still frame",
            foreground_prop="three source folders",
            palette="archive gray, paper cream, blue pencil",
            treatment="balanced_source_table",
            layout_id="top_split",
            diegetic_text="반론도 확인",
            transition="folder open cut",
            qa_focus=["fairness beat", "source labels generic"],
        ),
        SceneDesign(
            scene_id=9,
            role="cta",
            hook_text="당신의 해석은?",
            narration="당신은 이 결과를 실력 차로 봅니까, 아니면 심판 여론으로 봅니까. 근거 있는 댓글로 붙어봅시다.",
            visual_prompt=(
                "cinematic closing shot of neutral archive board with two paths labeled 실력 차 and 심판론, bold generated card text, "
                "no voting instruction, no party symbol"
            ),
            location="neutral archive board",
            camera="symmetrical closing shot",
            foreground_prop="two-path interpretation board",
            palette="black, white, red line, soft amber",
            treatment="choice_board_cta",
            layout_id="choice_stack",
            diegetic_text="실력 차 vs 심판론",
            transition="freeze frame with audio sting",
            qa_focus=["clear CTA", "no voting instruction"],
        ),
    ]


def build_content_signature(brief: EditorialBrief, scenes: list[SceneDesign]) -> ContentSignature:
    visual_locations = [scene.location for scene in scenes]
    camera_styles = [scene.camera for scene in scenes]
    foreground_props = [scene.foreground_prop for scene in scenes]
    palettes = [scene.palette for scene in scenes]
    treatments = [scene.treatment for scene in scenes]
    layout_ids = [scene.layout_id for scene in scenes]
    first_frame_signature = _stable_hash(
        scenes[0].location if scenes else "",
        scenes[0].camera if scenes else "",
        scenes[0].foreground_prop if scenes else "",
        scenes[0].diegetic_text if scenes else "",
    )
    fingerprint = _stable_hash(
        brief.issue.candidate_id,
        brief.post_title,
        first_frame_signature,
        ",".join(_unique(treatments)),
        ",".join(_unique(foreground_props)),
    )
    return ContentSignature(
        version=VERSION,
        topic_signature=_stable_hash(brief.issue.title, brief.issue.core_question),
        hook_signature=_stable_hash(scenes[0].hook_text if scenes else "", brief.post_title),
        script_structure=[scene.role for scene in scenes],
        visual_locations=visual_locations,
        camera_styles=camera_styles,
        foreground_props=foreground_props,
        palettes=palettes,
        treatments=treatments,
        layout_ids=layout_ids,
        first_frame_signature=first_frame_signature,
        cta_type="comment-debate",
        fingerprint=fingerprint,
    )


def _similarity_ratio(left: Iterable[str], right: Iterable[str]) -> float:
    left_set = set(_unique(left))
    right_set = set(_unique(right))
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)


def _recent_signature_blockers(signature: ContentSignature, recent_signatures: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for index, recent in enumerate(recent_signatures, start=1):
        if not isinstance(recent, dict):
            continue
        visual_overlap = _similarity_ratio(signature.visual_locations, recent.get("visual_locations") or [])
        prop_overlap = _similarity_ratio(signature.foreground_props, recent.get("foreground_props") or [])
        layout_overlap = _similarity_ratio(signature.layout_ids, recent.get("layout_ids") or [])
        if (
            str(recent.get("first_frame_signature") or "") == signature.first_frame_signature
            or visual_overlap >= 0.8
            or (prop_overlap >= 0.75 and layout_overlap >= 0.75)
        ):
            blockers.append(f"recent_visual_signature_overlap:{index}")
    return blockers


def critic_board(
    brief: EditorialBrief,
    scenes: list[SceneDesign],
    signature: ContentSignature,
    *,
    recent_signatures: list[dict[str, Any]] | None = None,
) -> list[CriticScore]:
    recent_signatures = recent_signatures or []
    source_score = 92 if len(brief.issue.source_requirements) >= 3 else 66
    arc_score = 92 if len(brief.narrative_arc) >= 5 and len(scenes) >= MIN_SCENE_COUNT else 68
    editorial_score = round((source_score + arc_score + _score_candidate(brief.issue)) / 3)

    audience_score = 82
    if "?" in scenes[0].hook_text:
        audience_score += 5
    if brief.issue.opposing_trigger and brief.issue.comment_question:
        audience_score += 7
    if len(brief.caption) > 180:
        audience_score -= 3
    audience_score = min(100, audience_score)

    unique_locations = len(_unique(signature.visual_locations))
    unique_cameras = len(_unique(signature.camera_styles))
    unique_props = len(_unique(signature.foreground_props))
    unique_layouts = len(_unique(signature.layout_ids))
    unique_treatments = len(_unique(signature.treatments))
    visual_score = 50
    visual_score += min(12, unique_locations * 2)
    visual_score += min(12, unique_cameras * 2)
    visual_score += min(14, unique_props * 2)
    visual_score += min(8, unique_layouts)
    visual_score += min(8, unique_treatments)
    visual_score = min(100, visual_score)

    policy_blockers = []
    all_text = " ".join([scene.visual_prompt for scene in scenes] + brief.policy_boundary)
    for marker in FORBIDDEN_VISUAL_MARKERS:
        if _contains_forbidden_marker(all_text, marker):
            policy_blockers.append(f"forbidden_visual_marker:{marker}")
    if any(len(scene.diegetic_text) > MAX_DIEGETIC_TEXT_CHARS for scene in scenes):
        policy_blockers.append("diegetic_text_too_long")
    if not brief.publish_gate:
        policy_blockers.append("publish_gate_missing")
    recent_blockers = _recent_signature_blockers(signature, recent_signatures)
    policy_blockers.extend(recent_blockers)
    policy_score = 92 - len(policy_blockers) * 15

    return [
        CriticScore(
            critic="editorial",
            score=editorial_score,
            passed=editorial_score >= CRITIC_PASS_SCORE,
            notes=["source-first brief", "narrative arc separates fact from interpretation"],
            blockers=[] if editorial_score >= CRITIC_PASS_SCORE else ["editorial_score_below_pass"],
        ),
        CriticScore(
            critic="audience",
            score=audience_score,
            passed=audience_score >= CRITIC_PASS_SCORE,
            notes=["comment conflict is explicit", "hook is framed as a debate question"],
            blockers=[] if audience_score >= CRITIC_PASS_SCORE else ["audience_score_below_pass"],
        ),
        CriticScore(
            critic="visual",
            score=visual_score,
            passed=visual_score >= CRITIC_PASS_SCORE,
            notes=[
                f"locations={unique_locations}",
                f"cameras={unique_cameras}",
                f"props={unique_props}",
                f"layouts={unique_layouts}",
                f"treatments={unique_treatments}",
            ],
            blockers=[] if visual_score >= CRITIC_PASS_SCORE else ["visual_score_below_pass"],
        ),
        CriticScore(
            critic="policy",
            score=max(0, policy_score),
            passed=policy_score >= CRITIC_PASS_SCORE and not policy_blockers,
            notes=["public-interest commentary", "no voting instruction", "AIGC disclosure required at upload"],
            blockers=policy_blockers,
        ),
    ]


def validate_package(package: EditorialCanaryPackage) -> dict[str, Any]:
    signature = package.signature
    blockers: list[str] = []
    warnings: list[str] = []

    if len(package.scenes) < MIN_SCENE_COUNT:
        blockers.append(f"scene_count_below_{MIN_SCENE_COUNT}:{len(package.scenes)}")
    if len(_unique(signature.visual_locations)) < MIN_UNIQUE_LOCATIONS:
        blockers.append("visual_locations_not_diverse")
    if len(_unique(signature.camera_styles)) < MIN_UNIQUE_CAMERAS:
        blockers.append("camera_styles_not_diverse")
    if len(_unique(signature.foreground_props)) < MIN_UNIQUE_PROPS:
        blockers.append("foreground_props_not_diverse")
    if len(_unique(signature.layout_ids)) < MIN_UNIQUE_LAYOUTS:
        blockers.append("layout_ids_not_diverse")
    if len(_unique(signature.treatments)) < MIN_UNIQUE_TREATMENTS:
        blockers.append("treatments_not_diverse")
    if any(not scene.diegetic_text.strip() for scene in package.scenes):
        blockers.append("diegetic_text_missing")
    if any(len(scene.diegetic_text) > MAX_DIEGETIC_TEXT_CHARS for scene in package.scenes):
        blockers.append("diegetic_text_too_long")
    if not all(critic.passed for critic in package.critics):
        blockers.extend(f"{critic.critic}_critic_failed" for critic in package.critics if not critic.passed)
    if len(_unique(signature.palettes)) < 5:
        warnings.append("palette_variety_low")

    return {
        "version": VERSION,
        "ok": not blockers,
        "blockers": blockers,
        "warnings": warnings,
        "metrics": {
            "scene_count": len(package.scenes),
            "unique_locations": len(_unique(signature.visual_locations)),
            "unique_cameras": len(_unique(signature.camera_styles)),
            "unique_props": len(_unique(signature.foreground_props)),
            "unique_layouts": len(_unique(signature.layout_ids)),
            "unique_treatments": len(_unique(signature.treatments)),
            "unique_palettes": len(_unique(signature.palettes)),
            "critic_scores": {critic.critic: critic.score for critic in package.critics},
        },
    }


def build_canary_package(
    *,
    seed: str = "election_12_4",
    recent_signatures: list[dict[str, Any]] | None = None,
) -> EditorialCanaryPackage:
    brief = build_editorial_brief(seed=seed)
    scenes = build_scene_design_plan(brief)
    signature = build_content_signature(brief, scenes)
    critics = critic_board(brief, scenes, signature, recent_signatures=recent_signatures)
    package = EditorialCanaryPackage(
        version=VERSION,
        generated_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        seed=seed,
        brief=brief,
        scenes=scenes,
        signature=signature,
        critics=critics,
        qa_report={},
    )
    qa_report = validate_package(package)
    return EditorialCanaryPackage(
        version=package.version,
        generated_at=package.generated_at,
        seed=package.seed,
        brief=package.brief,
        scenes=package.scenes,
        signature=package.signature,
        critics=package.critics,
        qa_report=qa_report,
    )


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _storyboard_markdown(package: EditorialCanaryPackage) -> str:
    rows = [
        "# AiNo Editorial OS v2 Canary",
        "",
        f"- seed: {package.seed}",
        f"- title: {package.brief.post_title}",
        f"- fingerprint: {package.signature.fingerprint}",
        f"- qa_ok: {package.qa_report.get('ok')}",
        "",
        "## Scenes",
        "",
    ]
    for scene in package.scenes:
        rows.extend(
            [
                f"### {scene.scene_id}. {scene.role}",
                f"- hook: {scene.hook_text}",
                f"- narration: {scene.narration}",
                f"- visual: {scene.location} / {scene.camera} / {scene.foreground_prop}",
                f"- diegetic_text: {scene.diegetic_text}",
                "",
            ]
        )
    return "\n".join(rows)


def _contact_sheet_color(seed: str) -> tuple[int, int, int]:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return (70 + digest[0] % 100, 70 + digest[1] % 100, 70 + digest[2] % 100)


def _draw_contact_text(draw: Any, xy: tuple[int, int], text: str, *, fill: tuple[int, int, int]) -> None:
    # Keep contact-sheet labels ASCII-first so Windows console/font fallback does not affect QA usefulness.
    try:
        from PIL import ImageFont

        font = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        font = None
    draw.text(xy, text, fill=fill, font=font)


def _draw_contact_scene_icon(draw: Any, scene: SceneDesign, x0: int, y0: int, cell_w: int, cell_h: int) -> None:
    white = (245, 247, 250)
    red = (190, 35, 58)
    dark = (18, 20, 24)
    if scene.role == "thumbnail":
        draw.rectangle((x0 + 48, y0 + 144, x0 + cell_w - 48, y0 + 236), outline=white, width=4)
        draw.rectangle((x0 + 84, y0 + 270, x0 + cell_w - 84, y0 + 344), fill=white)
        draw.line((x0 + 92, y0 + 306, x0 + cell_w - 92, y0 + 306), fill=red, width=6)
    elif scene.role == "context":
        for gx in range(3):
            for gy in range(3):
                draw.rectangle(
                    (x0 + 58 + gx * 72, y0 + 132 + gy * 58, x0 + 112 + gx * 72, y0 + 172 + gy * 58),
                    outline=white,
                    width=3,
                )
        draw.line((x0 + 270, y0 + 150, x0 + cell_w - 58, y0 + 308), fill=white, width=4)
    elif scene.role == "opposing_frame":
        draw.rectangle((x0 + 52, y0 + 164, x0 + 154, y0 + 240), fill=white)
        draw.rectangle((x0 + cell_w - 154, y0 + 164, x0 + cell_w - 52, y0 + 240), fill=white)
        draw.line((x0 + 44, y0 + 285, x0 + cell_w - 44, y0 + 285), fill=dark, width=10)
        draw.ellipse((x0 + cell_w // 2 - 30, y0 + 116, x0 + cell_w // 2 + 30, y0 + 176), outline=white, width=4)
    elif scene.role == "why_now":
        for offset in (0, 38, 76):
            draw.polygon(
                [
                    (x0 + 72 + offset, y0 + 150 + offset // 2),
                    (x0 + 210 + offset, y0 + 128 + offset // 2),
                    (x0 + 232 + offset, y0 + 198 + offset // 2),
                    (x0 + 92 + offset, y0 + 220 + offset // 2),
                ],
                outline=white,
            )
        draw.ellipse((x0 + cell_w - 118, y0 + 118, x0 + cell_w - 66, y0 + 170), outline=white, width=4)
    elif scene.role == "public_cost":
        draw.rectangle((x0 + 118, y0 + 112, x0 + 240, y0 + 344), fill=white)
        for line in range(6):
            y = y0 + 144 + line * 28
            draw.line((x0 + 136, y, x0 + 222, y), fill=dark, width=3)
        draw.arc((x0 + 64, y0 + 270, x0 + 138, y0 + 344), 0, 300, fill=white, width=5)
    elif scene.role == "comment_trigger":
        draw.rectangle((x0 + 116, y0 + 112, x0 + 246, y0 + 330), outline=white, width=4)
        for bubble in range(4):
            bx = x0 + 48 + bubble * 68
            by = y0 + 156 + (bubble % 2) * 64
            draw.rounded_rectangle((bx, by, bx + 96, by + 38), radius=16, outline=white, width=3)
    elif scene.role == "share_line":
        draw.rectangle((x0 + 48, y0 + 130, x0 + cell_w - 48, y0 + 260), outline=white, width=5)
        draw.line((x0 + 76, y0 + 292, x0 + 76, y0 + 374), fill=white, width=5)
        draw.line((x0 + cell_w - 76, y0 + 292, x0 + cell_w - 76, y0 + 374), fill=white, width=5)
        draw.line((x0 + 78, y0 + 206, x0 + cell_w - 78, y0 + 206), fill=red, width=6)
    elif scene.role == "fairness":
        for folder in range(3):
            y = y0 + 132 + folder * 72
            draw.rectangle((x0 + 68, y, x0 + cell_w - 68, y + 48), outline=white, width=4)
            draw.rectangle((x0 + 88, y - 16, x0 + 156, y), fill=white)
        draw.line((x0 + cell_w - 86, y0 + 118, x0 + cell_w - 136, y0 + 316), fill=red, width=5)
    else:
        draw.line((x0 + cell_w // 2, y0 + 120, x0 + cell_w // 2, y0 + 238), fill=white, width=5)
        draw.line((x0 + cell_w // 2, y0 + 238, x0 + 86, y0 + 336), fill=white, width=5)
        draw.line((x0 + cell_w // 2, y0 + 238, x0 + cell_w - 86, y0 + 336), fill=white, width=5)
        draw.ellipse((x0 + 54, y0 + 318, x0 + 118, y0 + 382), outline=white, width=4)
        draw.ellipse((x0 + cell_w - 118, y0 + 318, x0 + cell_w - 54, y0 + 382), outline=white, width=4)


def _write_visual_contact_sheet(package: EditorialCanaryPackage, path: Path) -> bool:
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return False

    width, height = 1080, 1920
    cols, rows = 3, 3
    cell_w, cell_h = width // cols, height // rows
    image = Image.new("RGB", (width, height), (18, 20, 24))
    draw = ImageDraw.Draw(image)
    for index, scene in enumerate(package.scenes[:9]):
        col = index % cols
        row = index // cols
        x0 = col * cell_w
        y0 = row * cell_h
        base = _contact_sheet_color(f"{scene.location}|{scene.camera}|{scene.treatment}")
        draw.rectangle((x0 + 8, y0 + 8, x0 + cell_w - 8, y0 + cell_h - 8), fill=base)
        draw.rectangle((x0 + 8, y0 + 8, x0 + cell_w - 8, y0 + 78), fill=(10, 12, 16))
        draw.rectangle((x0 + 22, y0 + 450, x0 + cell_w - 22, y0 + cell_h - 34), fill=(245, 242, 232))
        draw.line((x0 + 22, y0 + 450, x0 + cell_w - 22, y0 + 450), fill=(190, 35, 58), width=5)
        _draw_contact_scene_icon(draw, scene, x0, y0, cell_w, cell_h)
        _draw_contact_text(draw, (x0 + 24, y0 + 24), f"{scene.scene_id:02d} {scene.role}", fill=(255, 255, 255))
        _draw_contact_text(draw, (x0 + 28, y0 + 468), f"loc: {scene.location[:28]}", fill=(18, 20, 24))
        _draw_contact_text(draw, (x0 + 28, y0 + 500), f"cam: {scene.camera[:28]}", fill=(18, 20, 24))
        _draw_contact_text(draw, (x0 + 28, y0 + 532), f"trt: {scene.treatment[:28]}", fill=(18, 20, 24))
        _draw_contact_text(draw, (x0 + 28, y0 + 564), f"lay: {scene.layout_id[:28]}", fill=(18, 20, 24))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return True


def write_canary_package(package: EditorialCanaryPackage, output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "canary_package": output_dir / "canary_package.json",
        "editorial_brief": output_dir / "editorial_brief.json",
        "scene_design_plan": output_dir / "scene_design_plan.json",
        "content_signature": output_dir / "content_signature.json",
        "critic_report": output_dir / "critic_report.json",
        "qa_report": output_dir / "qa_report.json",
        "storyboard": output_dir / "canary_storyboard.md",
        "visual_contact_sheet": output_dir / "visual_contact_sheet.png",
    }
    _write_json(artifacts["canary_package"], asdict(package))
    _write_json(artifacts["editorial_brief"], asdict(package.brief))
    _write_json(artifacts["scene_design_plan"], [asdict(scene) for scene in package.scenes])
    _write_json(artifacts["content_signature"], asdict(package.signature))
    _write_json(artifacts["critic_report"], [asdict(critic) for critic in package.critics])
    _write_json(artifacts["qa_report"], package.qa_report)
    artifacts["storyboard"].write_text(_storyboard_markdown(package), encoding="utf-8")
    if not _write_visual_contact_sheet(package, artifacts["visual_contact_sheet"]):
        artifacts.pop("visual_contact_sheet", None)
    return {key: str(value) for key, value in artifacts.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build an AiNo Editorial OS v2 canary package.")
    parser.add_argument("--seed", default="election_12_4")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    package = build_canary_package(seed=args.seed)
    artifacts = write_canary_package(package, args.output_dir)
    result = {"ok": package.qa_report["ok"], "artifacts": artifacts, "qa_report": package.qa_report}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if package.qa_report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
