"""Audit blog posts for locale consistency. Counts Korean vs Latin letters
in the actual rendered prose (paragraph text + headings only - excludes
keywords, citation labels, slug strings, URLs, schema metadata).

A KO-suffixed slug should be > 70% Korean. An EN-suffixed slug should be
< 10% Korean. Anything outside those bands gets flagged.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "src/landing/src/lib/data/blog-content.ts"


def is_korean(c: str) -> bool:
    o = ord(c)
    return 0xAC00 <= o <= 0xD7A3 or 0x3130 <= o <= 0x318F


def is_latin(c: str) -> bool:
    return c.isalpha() and ord(c) < 0x0300


def main() -> int:
    text = PATH.read_text(encoding="utf-8")

    # Anchor on slug occurrences
    slug_pattern = re.compile(r'slug:\s*"([^"]+)",')
    matches = list(slug_pattern.finditer(text))

    print(f"{'slug':<70} {'prose_len':>10} {'KO%':>6}")
    print("-" * 95)
    issues: list[tuple[str, str, float]] = []

    for i, m in enumerate(matches):
        slug = m.group(1)
        # Body of this entry up to the next slug (or end)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section = text[start:end]

        # Pull only paragraph text fields and section headings (h2/h3/p inside sections)
        # and the lead. Keywords/citations/articleSection are excluded.
        prose_parts: list[str] = []

        # lead: "..."
        for lm in re.finditer(r'\blead:\s*"([^"]*)"', section):
            prose_parts.append(lm.group(1))

        # text: "..."  (inside sections array)
        for tm in re.finditer(r'\btext:\s*"([^"]*)"', section):
            prose_parts.append(tm.group(1))

        # FAQ question and answer
        for qa in re.finditer(r'\b(question|answer):\s*"([^"]*)"', section):
            prose_parts.append(qa.group(2))

        prose = " ".join(prose_parts)
        # Strip URLs and code/markdown anchors so we are only measuring readable prose
        prose = re.sub(r"https?://\S+", " ", prose)
        prose = re.sub(r"`[^`]+`", " ", prose)

        ko = sum(1 for c in prose if is_korean(c))
        lat = sum(1 for c in prose if is_latin(c))
        total = ko + lat
        pct = (ko / total * 100) if total else 0

        expected = "KO" if slug.endswith("-ko") else "EN"
        flag = ""
        if expected == "EN" and pct > 10:
            flag = f" <-- EN slug but {pct:.0f}% Korean prose"
            issues.append((slug, "EN_with_KO_content", pct))
        elif expected == "KO" and pct < 70:
            flag = f" <-- KO slug but only {pct:.0f}% Korean prose"
            issues.append((slug, "KO_with_EN_content", pct))
        print(f"{slug:<70} {len(prose):>10} {pct:>5.1f}%{flag}")

    print()
    print(f"Total scanned: {len(matches)}")
    print(f"Locale issues: {len(issues)}")
    for slug, kind, pct in issues:
        print(f"  - {slug} [{kind}] {pct:.0f}%")
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
