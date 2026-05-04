"""
FLUX.1-dev OG image generation for P9 content gap pages + /about.

Output directory : src/landing/public/assets/research/ + public/
Targets          :
  - solo-founder-multi-saas-2026.png/.webp     (1200x630)
  - ai-native-automation-companies-2026.png/.webp
  - saas-stack-comparison-engine-methodology.png/.webp
  - about.png/.webp (page-level OG for /about)
Model            : black-forest-labs/FLUX.1-dev via HF Inference Providers
Provider order   : wavespeed -> fal-ai -> replicate -> together -> nebius

Run:
    PYTHONIOENCODING=utf-8 python scripts/hf_publish/generate_p9_og_images.py
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path("D:/00.test/neo-genesis")
ENV_LOCAL = ROOT / ".env.local"
ENV = ROOT / ".env"

RESEARCH_DIR = ROOT / "src/landing/public/assets/research"
PUBLIC_DIR = ROOT / "src/landing/public"

NEGATIVE = (
    "text, letters, watermark, logo, signature, low quality, blurry, "
    "distorted faces, cluttered, busy composition, readable words, "
    "specific company logos"
)
TARGET_W = 1200
TARGET_H = 630


def _load_env() -> None:
    for ef in [ENV_LOCAL, ENV]:
        if not ef.exists():
            continue
        for line in ef.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if not v:
                continue
            if not os.environ.get(k):
                os.environ[k] = v


_load_env()


@dataclass(frozen=True)
class OGSpec:
    out_path: Path
    label: str
    prompt: str


OGS: list[OGSpec] = [
    OGSpec(
        out_path=RESEARCH_DIR / "solo-founder-multi-saas-2026.png",
        label="Solo Founder + 11 SaaS + 1 AI Orchestrator",
        prompt=(
            "Cinematic futuristic mission-control cockpit view, single "
            "human silhouette at the center of a circular array of 11 "
            "holographic product panels arranged like a planetarium dome, "
            "each panel emitting subtle cyan glow, central AI orchestrator "
            "core radiating soft blue light, dark navy void background with "
            "thin grid overlay, ultra detailed photorealistic, editorial "
            "tech magazine cover style, depth of field, wide cinematic 16:9"
        ),
    ),
    OGSpec(
        out_path=RESEARCH_DIR / "ai-native-automation-companies-2026.png",
        label="AI-Native Automation Companies 2026 reference list",
        prompt=(
            "Editorial constellation of stylized abstract company silhouette "
            "cards floating in 3D space, central focal point glowing with "
            "soft amber and cyan accents, dark navy gradient background, "
            "thin connecting lines between cards forming a knowledge graph, "
            "modern editorial infographic, technical poster aesthetic, "
            "ultra detailed, no readable text, wide cinematic 16:9"
        ),
    ),
    OGSpec(
        out_path=RESEARCH_DIR / "saas-stack-comparison-engine-methodology.png",
        label="SaaS comparison 4-factor framework",
        prompt=(
            "Isometric 3D abstract scoring matrix with four distinct "
            "quadrants in cyan, emerald, purple, and gold, weighted spheres "
            "of different sizes positioned across the quadrants, dark navy "
            "void background, technical diagram editorial illustration, "
            "ultra detailed, clean lines, no readable text, wide cinematic 16:9"
        ),
    ),
    OGSpec(
        out_path=PUBLIC_DIR / "about-og.png",
        label="Founder /about page",
        prompt=(
            "Minimalist futuristic biographical poster, single anonymous "
            "human silhouette in profile (no facial features visible), "
            "11 SaaS product orbits encircling the silhouette like planetary "
            "rings, Wikidata knowledge graph nodes interconnecting in the "
            "background, dark navy gradient with cyan accent lighting, "
            "ultra detailed, photorealistic editorial portrait, "
            "no readable text, wide cinematic 16:9"
        ),
    ),
]


def _ensure_pil():
    try:
        from PIL import Image  # noqa: F401
        return True
    except ImportError:
        sys.stderr.write("PIL missing. pip install Pillow\n")
        return False


def _hf_infer(prompt: str) -> Optional[bytes]:
    try:
        from huggingface_hub import InferenceClient
    except ImportError:
        sys.stderr.write("huggingface_hub missing.\n")
        return None

    token = os.environ.get("HF_TOKEN")
    if not token:
        sys.stderr.write("HF_TOKEN missing.\n")
        return None

    providers = ["wavespeed", "fal-ai", "replicate", "together", "nebius"]
    last_err = None
    for provider in providers:
        try:
            client = InferenceClient(provider=provider, token=token)
            print(f"  trying provider={provider}...")
            img = client.text_to_image(
                prompt=prompt,
                model="black-forest-labs/FLUX.1-dev",
                negative_prompt=NEGATIVE,
                width=1024,
                height=1024,
            )
            # InferenceClient returns PIL.Image
            from io import BytesIO
            buf = BytesIO()
            img.save(buf, format="PNG")
            print(f"    [OK] provider={provider} returned image {img.size}")
            return buf.getvalue()
        except Exception as e:
            last_err = e
            err_str = str(e)[:120]
            print(f"    [{provider}] failed: {err_str}")
            continue
    sys.stderr.write(f"All providers failed. last={last_err}\n")
    return None


def _letterbox_to_target(png_bytes: bytes, out_path: Path) -> None:
    """1024x1024 -> 1200x630 cinematic crop using PIL."""
    from PIL import Image
    from io import BytesIO

    img = Image.open(BytesIO(png_bytes))
    src_w, src_h = img.size

    # Target aspect 1200:630 = ~1.905
    target_aspect = TARGET_W / TARGET_H

    # Scale to width=TARGET_W
    scaled_w = TARGET_W
    scaled_h = int(src_h * (scaled_w / src_w))
    img2 = img.resize((scaled_w, scaled_h), Image.LANCZOS)

    # Center-crop top portion (cinematic letterbox: keep top 70%)
    if scaled_h > TARGET_H:
        # crop from y_offset, leave more sky/top
        y_offset = max(0, (scaled_h - TARGET_H) // 3)
        img2 = img2.crop((0, y_offset, scaled_w, y_offset + TARGET_H))
    elif scaled_h < TARGET_H:
        # pad letterbox
        canvas = Image.new("RGB", (TARGET_W, TARGET_H), (10, 14, 26))
        canvas.paste(img2, (0, (TARGET_H - scaled_h) // 2))
        img2 = canvas

    # Save PNG
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img2.save(out_path, format="PNG", optimize=True)
    print(f"    [PNG] saved {out_path.name} {img2.size} ({out_path.stat().st_size:,} bytes)")

    # Save WebP
    webp_path = out_path.with_suffix(".webp")
    img2.save(webp_path, format="WebP", quality=90, method=6)
    print(f"    [WebP] saved {webp_path.name} ({webp_path.stat().st_size:,} bytes)")


def main() -> int:
    if not _ensure_pil():
        return 1

    success = 0
    for spec in OGS:
        print(f"\n=== {spec.label} ===")
        if spec.out_path.exists():
            print(f"  [SKIP] already exists: {spec.out_path}")
            success += 1
            continue
        png = _hf_infer(spec.prompt)
        if png is None:
            print(f"  [FAIL] no provider returned image")
            continue
        _letterbox_to_target(png, spec.out_path)
        success += 1

    print(f"\n=== Summary ===")
    print(f"  Generated/preserved: {success}/{len(OGS)}")
    return 0 if success == len(OGS) else 2


if __name__ == "__main__":
    sys.exit(main())
