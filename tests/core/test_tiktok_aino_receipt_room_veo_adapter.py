import json
from pathlib import Path

from src.core.tiktok_aino import receipt_room_veo_adapter as adapter


def _plan() -> dict:
    return {
        "brand": "Receipt Room 11:59",
        "episode_title": "Alex Cooper, Matt Kaplan walk red carpet together amid rumors",
        "decision": "greenlight",
        "hook": "This two-second run-in made the internet split into juries.",
        "scorecard": {"total": 74},
        "risk_labels": ["AI-generated symbolic pop-culture parody."],
        "source_url": "https://example.com/story",
        "characters": [
            {"screen_character": "The Podcast Queen", "real_world_reference": "Alex Cooper"},
            {"screen_character": "The Producer Husband", "real_world_reference": "Matt Kaplan"},
        ],
        "shot_list": [
            {
                "beat": "microdrama_scene",
                "visual_prompt": "The Podcast Queen and The Producer Husband face each other across a symbolic red carpet courtroom.",
                "motion": "two symbolic figures turn away from each other; flashbulbs pop",
            }
        ],
    }


def test_build_veo_manifest_keeps_real_names_out_of_veo_prompt_fields(tmp_path: Path) -> None:
    manifest_path = adapter.build_veo_manifest(_plan(), tmp_path)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    asset = manifest["visual_assets"][0]
    brief_text = json.dumps(asset["visual_brief"], ensure_ascii=False)
    prompt_text = json.dumps({"topic": manifest["topic"], "asset": asset}, ensure_ascii=False)

    assert Path(asset["path"]).exists()
    assert manifest["topic"]["title"] == "symbolic pop-culture red carpet rumor trial"
    assert "original_title" in manifest["topic"]
    assert manifest["receipt_room"]["generation_ready"] is False
    assert asset["status"] == "storyboard_placeholder"
    assert "Alex Cooper" not in brief_text
    assert "Matt Kaplan" not in brief_text
    assert "Alex Cooper" not in prompt_text.replace(str(manifest["topic"]["original_title"]), "")
    assert "fictionalized luxury tabloid microdrama" in brief_text
    assert "no real face likeness" not in brief_text
