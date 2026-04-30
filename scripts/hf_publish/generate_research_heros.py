"""
FLUX.1-dev research-page hero image generation for neogenesis.app

Output directory : src/landing/public/assets/research/
Targets          : 4 hero images (PNG 1200x630 + WebP) for /data/research/[slug] pages
Model            : black-forest-labs/FLUX.1-dev via HF Inference Providers
Provider order   : wavespeed -> fal-ai -> replicate -> together -> nebius
Letterbox        : 1024x1024 -> 1200x630 cinematic crop with PIL fallback if provider
                   does not honor explicit width/height kwargs.

Run:
    PYTHONIOENCODING=utf-8 python scripts/hf_publish/generate_research_heros.py
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]
ENV_LOCAL = ROOT / ".env.local"
OUT_DIR = ROOT / "src" / "landing" / "public" / "assets" / "research"

NEGATIVE = (
    "text, letters, watermark, logo, signature, low quality, blurry, "
    "distorted faces, cluttered, busy composition"
)

TARGET_W = 1200
TARGET_H = 630


@dataclass(frozen=True)
class HeroSpec:
    slug: str          # output stem (matches research-assets visual concept, not the slug)
    label: str         # display label for log
    prompt: str


HEROS: list[HeroSpec] = [
    HeroSpec(
        slug="ethicaai-melting-pot",
        label="EthicaAI Melting Pot (mixed-safe cooperation)",
        prompt=(
            "Multiple humanoid AI agents in a circular arena, "
            "cooperating and competing in a stylized abstract environment, "
            "soft cyan and emerald glow, network of trust connecting some agents, "
            "isolation indicating defectors, dark navy void background, "
            "cinematic depth of field, ultra detailed, photorealistic, "
            "scientific publication aesthetic, no visible text or letters, "
            "wide cinematic 16:9"
        ),
    ),
    HeroSpec(
        slug="whylab-docker",
        label="WhyLab Gemini 2.5 Docker validation",
        prompt=(
            "Stylized debugging laboratory with floating Docker containers as "
            "luminous boxes, code trajectory paths shown as flowing data ribbons "
            "in cyan and orange, scientific causal-inference diagrams in the background, "
            "dark navy with bioluminescent accents, photorealistic editorial style, "
            "ultra detailed, no visible text or letters, wide cinematic 16:9"
        ),
    ),
    HeroSpec(
        slug="rag-master-design",
        label="RAG Master Design v1",
        prompt=(
            "Architectural blueprint of a vector retrieval system, "
            "glowing neural network nodes connected by data streams, "
            "multiple specialized index columns rising like crystalline structures, "
            "dark navy void with electric blue and emerald accents, "
            "cinematic depth of field, ultra detailed, technical illustration aesthetic, "
            "no visible text or letters, wide cinematic 16:9"
        ),
    ),
    HeroSpec(
        slug="agent-environment",
        label="Agent Environment v2",
        prompt=(
            "Multiple AI agent silhouettes connected by data streams in a layered "
            "architecture diagram (8 horizontal layers stacked), each agent representing "
            "a different framework, dark navy backdrop with cyan and electric purple accents, "
            "cinematic depth of field, technical illustration aesthetic, ultra detailed, "
            "no visible text or letters, wide cinematic 16:9"
        ),
    ),
]


def load_env(path: Path) -> None:
    if not path.exists():
        return
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)


def letterbox_to_target(image, target_w: int = TARGET_W, target_h: int = TARGET_H):
    """Crop a square (or off-aspect) PIL image to the cinematic target.

    Strategy: scale so the image fully covers the target, then center-crop.
    This keeps the subject at full visual scale and avoids black bars.
    """
    src_w, src_h = image.size
    if src_w == target_w and src_h == target_h:
        return image

    src_ratio = src_w / src_h
    target_ratio = target_w / target_h

    if src_ratio > target_ratio:
        # source is wider — fit by height, crop horizontally
        scale = target_h / src_h
    else:
        # source is taller — fit by width, crop vertically
        scale = target_w / src_w

    new_w = int(round(src_w * scale))
    new_h = int(round(src_h * scale))

    try:
        from PIL import Image as PILImage  # noqa: F401
        resample = getattr(__import__("PIL").Image, "LANCZOS", 1)
    except Exception:
        resample = 1

    resized = image.resize((new_w, new_h), resample=resample)

    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    right = left + target_w
    bottom = top + target_h
    return resized.crop((left, top, right, bottom))


def generate_one(spec: HeroSpec, token: str) -> tuple[Optional[str], Optional[Exception]]:
    """Generate a single hero image. Returns (provider_used, error).

    Provider/model fallback chain (in order):
      1. wavespeed   + FLUX.1-dev      (highest fidelity, may hit 402 quota)
      2. fal-ai      + FLUX.1-dev      (402 fallback)
      3. replicate   + FLUX.1-dev      (402 fallback)
      4. together    + FLUX.1-schnell  (FLUX.1-dev unsupported on together)
      5. nebius      + FLUX.1-dev      (often unsupported, kept as last resort)
      6. replicate   + FLUX.1-schnell  (last-ditch)
      7. together    + FLUX.1-schnell  (already tried, but harmless)
    """
    from huggingface_hub import InferenceClient

    # (provider, model, native_w, native_h)  — order matters: dev first, then schnell.
    # Some providers (together) require width/height to be multiples of 16; for those
    # we ask for a 16:9-ish 1024x576 and letterbox afterwards.
    attempts: list[tuple[str, str, int, int]] = [
        ("wavespeed", "black-forest-labs/FLUX.1-dev", TARGET_W, TARGET_H),
        ("fal-ai", "black-forest-labs/FLUX.1-dev", TARGET_W, TARGET_H),
        ("replicate", "black-forest-labs/FLUX.1-dev", TARGET_W, TARGET_H),
        ("nebius", "black-forest-labs/FLUX.1-dev", TARGET_W, TARGET_H),
        # together requires multiples of 16 — 1024x576 is true 16:9 and divisible by 16
        ("together", "black-forest-labs/FLUX.1-schnell", 1024, 576),
        ("replicate", "black-forest-labs/FLUX.1-schnell", TARGET_W, TARGET_H),
        # last-resort: any provider, any FLUX, default size
        ("replicate", "black-forest-labs/FLUX.1-schnell", 1024, 1024),
    ]
    last_error: Optional[Exception] = None

    for provider, model, req_w, req_h in attempts:
        label = f"{provider}/{model.split('/')[-1]} ({req_w}x{req_h})"
        try:
            print(f"  trying provider: {label}")
            client = InferenceClient(provider=provider, api_key=token)

            # First try the requested dimensions directly
            try:
                image = client.text_to_image(
                    spec.prompt,
                    model=model,
                    width=req_w,
                    height=req_h,
                    negative_prompt=NEGATIVE,
                )
                chosen = label
            except TypeError:
                # provider doesn't accept width/height — fall back to default size
                image = client.text_to_image(
                    spec.prompt,
                    model=model,
                )
                chosen = label + " (default size, will letterbox)"

            # Always normalize to TARGET_W x TARGET_H so output is consistent.
            if image.size != (TARGET_W, TARGET_H):
                print(f"    provider returned {image.size}, letterboxing to {TARGET_W}x{TARGET_H}")
                image = letterbox_to_target(image)

            png_path = OUT_DIR / f"{spec.slug}.png"
            webp_path = OUT_DIR / f"{spec.slug}.webp"

            png_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(png_path, format="PNG", optimize=True)
            # WebP at quality 82 strikes ~50KB target with FLUX-style content.
            image.save(webp_path, format="WEBP", quality=82, method=6)

            png_size = png_path.stat().st_size
            webp_size = webp_path.stat().st_size
            print(f"    PNG  : {png_size:>9,} bytes  -> {png_path.name}")
            print(f"    WEBP : {webp_size:>9,} bytes  -> {webp_path.name}")
            return chosen, None
        except TypeError as e:
            # Already handled inside, but in case the fallback also TypeErrors.
            last_error = e
            print(f"    failed (TypeError): {str(e)[:120]}")
            continue
        except Exception as e:
            last_error = e
            print(f"    failed: {type(e).__name__}: {str(e)[:120]}")
            continue

    return None, last_error


def main() -> int:
    load_env(ENV_LOCAL)
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("ERROR: HF_TOKEN missing in env (.env.local)", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # If --force is passed, regenerate everything; otherwise skip slugs whose
    # PNG+WebP both already exist with non-trivial size.
    force = "--force" in sys.argv

    print(f"OUT_DIR : {OUT_DIR}")
    print(f"COUNT   : {len(HEROS)}")
    print(f"FORCE   : {force}")
    print()

    succeeded: list[tuple[HeroSpec, str]] = []
    failed: list[tuple[HeroSpec, Optional[Exception]]] = []
    skipped: list[HeroSpec] = []

    for idx, spec in enumerate(HEROS, 1):
        png_path = OUT_DIR / f"{spec.slug}.png"
        webp_path = OUT_DIR / f"{spec.slug}.webp"
        if (
            not force
            and png_path.exists()
            and webp_path.exists()
            and png_path.stat().st_size > 100_000
            and webp_path.stat().st_size > 10_000
        ):
            print(f"[{idx}/{len(HEROS)}] {spec.label}")
            print(
                f"  SKIP (already exists): "
                f"PNG={png_path.stat().st_size:,}  WEBP={webp_path.stat().st_size:,}"
            )
            print()
            skipped.append(spec)
            continue

        print(f"[{idx}/{len(HEROS)}] {spec.label}")
        provider, err = generate_one(spec, token)
        if provider is None:
            failed.append((spec, err))
            print(f"  ALL PROVIDERS FAILED for {spec.slug}")
        else:
            succeeded.append((spec, provider))
            print(f"  PROVIDER: {provider}")
        print()

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    total_png = 0
    total_webp = 0
    for spec, provider in succeeded:
        png_path = OUT_DIR / f"{spec.slug}.png"
        webp_path = OUT_DIR / f"{spec.slug}.webp"
        png_size = png_path.stat().st_size if png_path.exists() else 0
        webp_size = webp_path.stat().st_size if webp_path.exists() else 0
        total_png += png_size
        total_webp += webp_size
        print(f"  OK   {spec.slug:<28} provider={provider}")
        print(f"           PNG={png_size:>9,}  WEBP={webp_size:>9,}")

    for spec in skipped:
        png_path = OUT_DIR / f"{spec.slug}.png"
        webp_path = OUT_DIR / f"{spec.slug}.webp"
        png_size = png_path.stat().st_size if png_path.exists() else 0
        webp_size = webp_path.stat().st_size if webp_path.exists() else 0
        total_png += png_size
        total_webp += webp_size
        print(f"  SKIP {spec.slug:<28} (already on disk)")
        print(f"           PNG={png_size:>9,}  WEBP={webp_size:>9,}")

    for spec, err in failed:
        err_msg = f"{type(err).__name__}: {str(err)[:120]}" if err else "no provider succeeded"
        print(f"  FAIL {spec.slug:<28} {err_msg}")

    print()
    print(f"Generated  : {len(succeeded)}/{len(HEROS)}")
    print(f"Skipped    : {len(skipped)}/{len(HEROS)}")
    print(f"Failed     : {len(failed)}/{len(HEROS)}")
    print(f"Total PNG  : {total_png:,} bytes")
    print(f"Total WEBP : {total_webp:,} bytes")
    print(f"Total      : {total_png + total_webp:,} bytes")

    return 0 if not failed else 2


if __name__ == "__main__":
    sys.exit(main())
