from __future__ import annotations

import argparse
import datetime as dt
import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter


REPO_DIR = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = REPO_DIR / "output" / "receipt_room_veo_prototypes"


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return data


def _select_plan(report: dict[str, Any], index: int | None) -> dict[str, Any]:
    plans = report.get("plans")
    if not isinstance(plans, list) or not plans:
        raise ValueError("trend report has no plans")
    if index is not None:
        selected = plans[index]
        if not isinstance(selected, dict):
            raise ValueError(f"plan at index must be an object: {index}")
        return selected
    for plan in plans:
        if isinstance(plan, dict) and plan.get("decision") == "greenlight":
            return plan
    for plan in plans:
        if isinstance(plan, dict):
            return plan
    raise ValueError("trend report has no valid plan objects")


def _character_names(plan: dict[str, Any]) -> list[str]:
    characters = plan.get("characters") if isinstance(plan.get("characters"), list) else []
    names = []
    for row in characters:
        if isinstance(row, dict) and row.get("screen_character"):
            names.append(str(row["screen_character"]))
    return names or ["The Spotlight Figure", "The Internet Jury"]


def _first_motion_shot(plan: dict[str, Any]) -> dict[str, Any]:
    shots = plan.get("shot_list") if isinstance(plan.get("shot_list"), list) else []
    preferred = ["microdrama_scene", "cold_open", "fan_theory", "verified_fact"]
    for beat in preferred:
        for shot in shots:
            if isinstance(shot, dict) and shot.get("beat") == beat:
                return shot
    for shot in shots:
        if isinstance(shot, dict):
            return shot
    return {
        "beat": "cold_open",
        "caption": "The internet brought receipts.",
        "motion": "camera pushes through a symbolic red carpet courtroom while comment bubbles flood the screen",
        "visual_prompt": "symbolic tabloid animation with red carpet courtroom, evidence board, and anonymous silhouettes",
    }


def _draw_soft_rect(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], fill: tuple[int, int, int, int], radius: int = 24) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def render_symbolic_keyframe(plan: dict[str, Any], output_path: Path) -> None:
    width, height = 1080, 1920
    image = Image.new("RGB", (width, height), (12, 14, 20))
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow, "RGBA")

    # Stage and red-carpet depth.
    for y in range(height):
        t = y / height
        base = int(18 + 36 * t)
        ImageDraw.Draw(image).line([(0, y), (width, y)], fill=(base, max(12, base - 8), max(22, base + 14)))
    g.ellipse((-240, 120, 1320, 1540), fill=(150, 36, 72, 42))
    g.ellipse((130, 140, 950, 1180), fill=(240, 220, 180, 38))
    g.rectangle((430, 720, 650, 1920), fill=(168, 20, 38, 178))
    g.polygon([(320, 1920), (760, 1920), (650, 720), (430, 720)], fill=(190, 24, 44, 180))

    # Courtroom columns / tabloid set.
    for x in [96, 884]:
        g.rounded_rectangle((x, 360, x + 100, 1540), radius=28, fill=(58, 64, 82, 215))
        g.rounded_rectangle((x - 24, 328, x + 124, 390), radius=16, fill=(96, 96, 112, 230))
        g.rounded_rectangle((x - 34, 1516, x + 134, 1594), radius=18, fill=(92, 86, 102, 230))

    # Evidence board, deliberately no readable text.
    g.rounded_rectangle((210, 260, 870, 610), radius=30, fill=(32, 37, 49, 230), outline=(216, 184, 112, 180), width=3)
    for idx, (x, y) in enumerate([(270, 326), (462, 302), (654, 342), (376, 448), (574, 462)]):
        g.rounded_rectangle((x, y, x + 142, y + 86), radius=12, fill=(228, 222, 202, 230))
        g.ellipse((x + 58, y + 28, x + 82, y + 52), fill=(150, 32, 52, 230))
        if idx:
            g.line((340, 370, x + 70, y + 44), fill=(210, 38, 58, 190), width=4)

    # Character silhouettes.
    characters = _character_names(plan)
    character_x = [385, 695, 535]
    for index, name in enumerate(characters[:3]):
        cx = character_x[index]
        scale = 1.12 if index == 0 else 0.98
        color = [(23, 25, 34, 245), (31, 27, 37, 238), (37, 26, 46, 230)][index]
        g.ellipse((cx - 55, 670, cx + 55, 780), fill=color)
        g.rounded_rectangle((int(cx - 70 * scale), 770, int(cx + 70 * scale), 1115), radius=50, fill=color)
        g.polygon([(cx - 140, 870), (cx - 70, 820), (cx - 70, 930)], fill=color)
        g.polygon([(cx + 140, 870), (cx + 70, 820), (cx + 70, 930)], fill=color)
        g.ellipse((cx - 140, 640, cx + 140, 920), outline=(245, 214, 154, 74), width=8)

    # Paparazzi flashes and phones.
    for idx in range(18):
        angle = (idx / 18) * math.pi * 2
        x = int(width / 2 + math.cos(angle) * (360 + (idx % 3) * 60))
        y = int(950 + math.sin(angle) * 450)
        g.rectangle((x - 32, y - 18, x + 32, y + 18), fill=(24, 28, 38, 230))
        g.ellipse((x - 10, y - 10, x + 10, y + 10), fill=(245, 236, 178, 210))
        if idx % 4 == 0:
            g.line((x, y, width // 2, 900), fill=(255, 236, 180, 70), width=3)

    # Comment storm bubbles without readable text.
    for idx in range(20):
        col = idx % 4
        row = idx // 4
        x = 72 + col * 250 + (row % 2) * 42
        y = 1220 + row * 92
        fill = (244, 244, 250, 210) if idx % 3 else (255, 218, 132, 214)
        _draw_soft_rect(g, (x, y, x + 170, y + 54), fill, radius=24)
        g.ellipse((x + 24, y + 19, x + 42, y + 37), fill=(120, 125, 145, 150))
        g.rounded_rectangle((x + 52, y + 20, x + 142, y + 34), radius=6, fill=(120, 125, 145, 92))

    image = Image.alpha_composite(image.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(0.4)))
    vignette = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    v = ImageDraw.Draw(vignette, "RGBA")
    v.rectangle((0, 0, width, 180), fill=(0, 0, 0, 120))
    v.rectangle((0, height - 210, width, height), fill=(0, 0, 0, 135))
    image = Image.alpha_composite(image, vignette)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output_path, quality=95)


def build_veo_manifest(plan: dict[str, Any], output_dir: Path) -> Path:
    run_dir = output_dir / dt.datetime.now().strftime("receipt_room_%Y%m%d_%H%M%S")
    keyframe_path = run_dir / "keyframes" / "scene_01_symbolic.png"
    render_symbolic_keyframe(plan, keyframe_path)

    characters = _character_names(plan)
    selected_shot = _first_motion_shot(plan)
    motion = str(selected_shot.get("motion", "camera pushes through a symbolic tabloid set"))
    manifest = {
        "topic": {
            "title": "symbolic pop-culture red carpet rumor trial",
            "original_title": plan.get("episode_title"),
            "brand": plan.get("brand", "Receipt Room 11:59"),
        },
        "receipt_room": {
            "decision": plan.get("decision"),
            "scorecard": plan.get("scorecard"),
            "risk_labels": plan.get("risk_labels"),
            "characters": plan.get("characters"),
            "source_url": plan.get("source_url"),
            "generation_ready": False,
            "generation_blockers": [
                "storyboard_placeholder_keyframe",
                "character_reference_quality_not_verified",
                "silhouette_only_visual_style"
            ],
            "minimum_required_before_paid_video": [
                "high_quality_character_reference",
                "expressive_non_likeness_faces",
                "scene_specific_action_keyframe",
                "manual_or_vision_quality_approval"
            ],
        },
        "script": {
            "scenes": [
                {
                    "scene_id": 1,
                    "title": "Receipt Room Cold Open",
                    "visual": "symbolic red carpet courtroom with evidence board, anonymous silhouettes, paparazzi flashes, and comment storm",
                    "body": plan.get("hook", "The internet brought receipts."),
                }
            ]
        },
        "visual_assets": [
            {
                "scene_id": 1,
                "provider": "receipt_room_storyboard_placeholder",
                "status": "storyboard_placeholder",
                "path": str(keyframe_path.resolve()),
                "prompt": str(selected_shot.get("visual_prompt", "")),
                "visual_brief": {
                    "role": "cold_open",
                    "location": "non-realistic red carpet courtroom inside a tabloid evidence room",
                    "camera": "fast push through paparazzi flashes, then a parallax sweep across the evidence board and symbolic characters",
                    "palette": "black lacquer, deep red carpet, gold flash, cool blue comment light",
                    "visual_intent": (
                        "Create an energetic symbolic gossip microdrama opener. "
                        f"Show {characters[0]} facing a public rumor trial while "
                        f"{characters[1] if len(characters) > 1 else 'The Internet Jury'} turns away under flashbulbs. "
                        f"Motion requirement: {motion}."
                    ),
                    "visual_anchor": [
                        "red carpet courtroom",
                        "receipt evidence board",
                        "expressive symbolic leads",
                        "paparazzi flash wall",
                        "comment bubbles rushing toward camera",
                        "verdict meter implied without readable text"
                    ],
                    "creative_contract": "fictionalized luxury tabloid microdrama; backend risk gates already passed before this manifest is eligible for paid generation",
                },
            }
        ],
    }
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a Veo image-to-video manifest from a Receipt Room trend scout plan.")
    parser.add_argument("--trend-report", type=Path, required=True)
    parser.add_argument("--plan-index", type=int, help="Zero-based plan index. Defaults to first greenlight plan.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    report = _read_json(args.trend_report)
    plan = _select_plan(report, args.plan_index)
    manifest_path = build_veo_manifest(plan, args.output_dir.resolve())
    print(json.dumps({"manifest": str(manifest_path), "episode_title": plan.get("episode_title")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
