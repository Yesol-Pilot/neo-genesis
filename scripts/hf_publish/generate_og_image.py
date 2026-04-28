"""
FLUX.1-dev OG image generation for neogenesis.app

Output : src/landing/public/assets/og.png (1200x630, OG/Twitter card standard)
Model  : black-forest-labs/FLUX.1-dev via HF Inference Providers

Run:
    PYTHONIOENCODING=utf-8 python scripts/hf_publish/generate_og_image.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_LOCAL = ROOT / ".env.local"
OUT = ROOT / "src" / "landing" / "public" / "assets" / "og.png"

PROMPT = (
    "Single human silhouette in a futuristic AI command center, "
    "overseeing 11 floating holographic dashboards arranged in a wide arc, "
    "each glowing with different real-time data visualizations and autonomous AI agents working in parallel, "
    "dark navy void background, bioluminescent cyan and electric blue accents, "
    "cinematic depth of field, ultra detailed, photorealistic, minimalist composition, "
    "professional editorial style, high contrast, negative space on the right for text overlay, "
    "subtle scan-line texture, no visible text or letters, "
    "wide cinematic 16:9 aspect ratio"
)

NEGATIVE = "text, letters, watermark, logo, signature, low quality, blurry, distorted faces"


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


def main() -> int:
    load_env(ENV_LOCAL)
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("ERROR: HF_TOKEN missing", file=sys.stderr)
        return 1

    from huggingface_hub import InferenceClient

    # Try providers in order of cost/availability
    providers = ["wavespeed", "fal-ai", "replicate", "together", "nebius"]
    last_error: Exception | None = None
    image = None
    chosen = None

    for provider in providers:
        try:
            print(f"trying provider: {provider}")
            client = InferenceClient(provider=provider, api_key=token)
            image = client.text_to_image(
                PROMPT,
                model="black-forest-labs/FLUX.1-dev",
                width=1200,
                height=630,
                negative_prompt=NEGATIVE,
            )
            chosen = provider
            break
        except TypeError:
            # some providers don't accept width/height — retry with default
            try:
                image = client.text_to_image(
                    PROMPT, model="black-forest-labs/FLUX.1-dev"
                )
                chosen = provider + " (default size)"
                break
            except Exception as e:
                last_error = e
                print(f"  fallback failed: {type(e).__name__}: {str(e)[:120]}")
                continue
        except Exception as e:
            last_error = e
            print(f"  failed: {type(e).__name__}: {str(e)[:120]}")
            continue

    if image is None:
        print(f"ERROR: all providers failed. Last: {last_error}", file=sys.stderr)
        return 2

    OUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUT, format="PNG", optimize=True)
    print()
    print(f"PROVIDER : {chosen}")
    print(f"SIZE     : {image.size[0]}x{image.size[1]}")
    print(f"BYTES    : {OUT.stat().st_size:,}")
    print(f"SAVED    : {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
