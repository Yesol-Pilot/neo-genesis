"""Build PDF for the Neo Genesis Q2 2026 Research Status Report.

Uses reportlab Platypus. Reads the markdown SSOT and renders a multi-page
A4 PDF with cover, TOC, body sections (heading/paragraph), and appendix.

This is a one-shot reporter. For ongoing reports, generalize the
markdown -> Platypus mapping in scripts/markdown_to_pdf.py.
"""
from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    PageBreak,
    KeepTogether,
)


SRC = Path(r"D:/00.test/neo-genesis/.agent/knowledge/reports/2026-Q2-research-status-report.md")
DST = Path(r"D:/00.test/neo-genesis/src/landing/public/assets/reports/neo-genesis-2026-q2-research-status-report.pdf")


def html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def parse_markdown(md_text: str):
    """Parse the report markdown into a sequence of (kind, content) blocks.

    kinds: 'cover_h1', 'h1', 'h2', 'h3', 'p', 'ul', 'meta'.
    """
    # Strip yaml front matter (between leading --- and next ---)
    body = md_text
    if body.startswith("---"):
        end = body.find("\n---", 3)
        if end != -1:
            body = body[end + 4:]

    blocks = []
    buf: list[str] = []
    in_list = False
    list_items: list[str] = []
    in_code = False

    def flush_para():
        if buf:
            text = " ".join(line.strip() for line in buf).strip()
            if text:
                blocks.append(("p", text))
            buf.clear()

    def flush_list():
        nonlocal in_list, list_items
        if list_items:
            blocks.append(("ul", list_items[:]))
            list_items.clear()
        in_list = False

    for raw in body.splitlines():
        line = raw.rstrip()
        # code fences -> skip block contents but render inline
        if line.startswith("```"):
            in_code = not in_code
            if not in_code:
                flush_para()
            continue
        if in_code:
            buf.append(line)
            continue
        if not line.strip():
            flush_para()
            flush_list()
            continue
        if line.startswith("# "):
            flush_para(); flush_list()
            blocks.append(("h1", line[2:].strip()))
            continue
        if line.startswith("## "):
            flush_para(); flush_list()
            blocks.append(("h2", line[3:].strip()))
            continue
        if line.startswith("### "):
            flush_para(); flush_list()
            blocks.append(("h3", line[4:].strip()))
            continue
        if line.startswith("> "):
            flush_para(); flush_list()
            blocks.append(("blockquote", line[2:].strip()))
            continue
        if line.startswith("- "):
            flush_para()
            in_list = True
            list_items.append(line[2:].strip())
            continue
        if in_list and (line.startswith("  ") or line.startswith("\t")):
            list_items[-1] += " " + line.strip()
            continue
        # ordered list "1. " etc
        m = re.match(r"^\d+\.\s+", line)
        if m:
            flush_para()
            in_list = True
            list_items.append(line[m.end():].strip())
            continue
        # Horizontal rule
        if line.strip() == "---":
            flush_para(); flush_list()
            blocks.append(("hr", ""))
            continue
        if in_list:
            flush_list()
        buf.append(line)
    flush_para()
    flush_list()
    return blocks


def inline(text: str) -> str:
    """Convert minimal Markdown inline markup to reportlab markup.

    Order matters: code first (so ** inside doesn't break), then bold/italic, then escape stray <.
    """
    # Inline code `x` -> <font face="Courier">x</font>
    def code_repl(m):
        return f'<font face="Courier">{html_escape(m.group(1))}</font>'

    # Escape pre-existing < > first to avoid interfering with reportlab tags
    out = text.replace("&", "&amp;")
    # Build placeholders for code spans first so we don't escape angle brackets in tags later
    code_spans: list[str] = []

    def store_code(m):
        code_spans.append(m.group(1))
        return f"\x00CODE{len(code_spans) - 1}\x00"

    out = re.sub(r"`([^`]+)`", store_code, out)
    # Now escape angle brackets
    out = out.replace("<", "&lt;").replace(">", "&gt;")
    # Bold ** **
    out = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", out)
    # Italic _x_ or *x*
    out = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", out)
    # Links [label](url)
    out = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<link href="{m.group(2)}"><font color="#0a66c2">{m.group(1)}</font></link>',
        out,
    )
    # Restore code spans
    for i, code in enumerate(code_spans):
        out = out.replace(f"\x00CODE{i}\x00", f'<font face="Courier">{html_escape(code)}</font>')
    return out


def build_styles():
    base = getSampleStyleSheet()
    styles = {}
    styles["title"] = ParagraphStyle(
        "title",
        parent=base["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=30,
        spaceAfter=8,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#0a1f44"),
    )
    styles["subtitle"] = ParagraphStyle(
        "subtitle",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        spaceAfter=12,
        textColor=colors.HexColor("#444"),
    )
    styles["meta"] = ParagraphStyle(
        "meta",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#555"),
    )
    styles["h1"] = ParagraphStyle(
        "h1",
        parent=base["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        spaceBefore=14,
        spaceAfter=8,
        textColor=colors.HexColor("#0a1f44"),
    )
    styles["h2"] = ParagraphStyle(
        "h2",
        parent=base["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor("#0a1f44"),
    )
    styles["h3"] = ParagraphStyle(
        "h3",
        parent=base["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        spaceBefore=8,
        spaceAfter=4,
        textColor=colors.HexColor("#1a3a6e"),
    )
    styles["body"] = ParagraphStyle(
        "body",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=6,
    )
    styles["blockquote"] = ParagraphStyle(
        "blockquote",
        parent=base["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=10.5,
        leading=14,
        leftIndent=10,
        textColor=colors.HexColor("#333"),
        spaceAfter=10,
    )
    styles["bullet"] = ParagraphStyle(
        "bullet",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        leftIndent=14,
        bulletIndent=4,
        spaceAfter=2,
    )
    styles["footer"] = ParagraphStyle(
        "footer",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=8,
        textColor=colors.HexColor("#888"),
        alignment=TA_CENTER,
    )
    return styles


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#888"))
    page_num = canvas.getPageNumber()
    canvas.drawString(15 * mm, 10 * mm, "Neo Genesis | Q2 2026 Research Status Report")
    canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"Page {page_num}")
    canvas.drawCentredString(A4[0] / 2, A4[1] - 10 * mm, "https://neogenesis.app/data/research/2026-q2-research-status-report")
    canvas.restoreState()


def main():
    md_text = SRC.read_text(encoding="utf-8")
    blocks = parse_markdown(md_text)
    styles = build_styles()

    DST.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(DST),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=22 * mm,
        bottomMargin=18 * mm,
        title="Neo Genesis Q2 2026 Research Status Report",
        author="Yesol Heo",
        subject="Quarterly research status disclosure",
        keywords="Neo Genesis, Q2 2026, research, AI-native, autonomous, solo-founder",
    )

    flow = []

    # Cover
    flow.append(Paragraph("Neo Genesis", styles["subtitle"]))
    flow.append(Paragraph("Q2 2026 Research Status Report", styles["title"]))
    flow.append(Paragraph(
        "Self-published, citation-grade quarterly disclosure covering February 1, 2026 through May 3, 2026.",
        styles["subtitle"],
    ))
    flow.append(Spacer(1, 6 * mm))
    cover_meta = (
        "<b>Publisher:</b> Neo Genesis (Wikidata Q139569680)<br/>"
        "<b>Author:</b> Yesol Heo (Wikidata Q139569708)<br/>"
        "<b>Canonical URL:</b> https://neogenesis.app/data/research/2026-q2-research-status-report<br/>"
        "<b>License:</b> CC-BY-4.0 (text), MIT + Apache-2.0 dual (code)<br/>"
        "<b>Published:</b> 2026-05-03<br/>"
        "<b>Word count:</b> ~6,100 words (body) + ~1,200 words (appendices)"
    )
    flow.append(Paragraph(cover_meta, styles["meta"]))
    flow.append(Spacer(1, 6 * mm))
    flow.append(Paragraph(
        "<b>Headline at a glance.</b> Eight Hugging Face datasets, three interactive Spaces, "
        "five awesome-list inclusions reaching ~60K developers, 395 Wikidata statements across "
        "13 entities, two NeurIPS 2026 paper submissions, twelve blog posts, nine /data/research "
        "entries. All autonomous, single-operator, $0 infrastructure cost.",
        styles["body"],
    ))
    flow.append(PageBreak())

    # Body
    skip_first_h1 = True
    for kind, content in blocks:
        if kind == "h1":
            if skip_first_h1:
                # the cover h1 from the markdown is already rendered above
                skip_first_h1 = False
                continue
            flow.append(Paragraph(inline(content), styles["h1"]))
        elif kind == "h2":
            flow.append(Paragraph(inline(content), styles["h2"]))
        elif kind == "h3":
            flow.append(Paragraph(inline(content), styles["h3"]))
        elif kind == "p":
            flow.append(Paragraph(inline(content), styles["body"]))
        elif kind == "blockquote":
            flow.append(Paragraph(inline(content), styles["blockquote"]))
        elif kind == "ul":
            for item in content:
                flow.append(Paragraph("• " + inline(item), styles["bullet"]))
            flow.append(Spacer(1, 4))
        elif kind == "hr":
            flow.append(Spacer(1, 6))
        # other kinds skipped
    doc.build(flow, onFirstPage=on_page, onLaterPages=on_page)
    size = DST.stat().st_size
    print(f"OK pdf={DST} size={size} bytes ({size/1024:.1f} KB)")


if __name__ == "__main__":
    main()
