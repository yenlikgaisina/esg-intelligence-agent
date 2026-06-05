"""
report.py — Render a markdown report to PDF.

Uses reportlab (pure-python, no system deps). Supports the subset of markdown
the agent produces: # / ## / ### headings, **bold**, bullet lists ("- "),
and pipe tables. If reportlab isn't installed, it degrades gracefully and the
caller keeps the markdown file.
"""

import os
import re


def _inline(text: str) -> str:
    """Convert a little inline markdown to reportlab's mini-HTML."""
    text = (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r"<font face='Courier'>\1</font>", text)
    # strip leftover emphasis markers
    return text


def markdown_to_pdf(markdown_text: str, pdf_path: str) -> bool:
    """Render markdown_text to pdf_path. Returns True on success, False if reportlab missing."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
        )
    except ImportError:
        return False

    BRAND = colors.HexColor("#0B6E4F")   # deep sustainability green
    ACCENT = colors.HexColor("#1F2937")

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("H1x", parent=styles["Heading1"], textColor=BRAND, fontSize=20, spaceAfter=8))
    styles.add(ParagraphStyle("H2x", parent=styles["Heading2"], textColor=ACCENT, fontSize=14, spaceBefore=10, spaceAfter=4))
    styles.add(ParagraphStyle("H3x", parent=styles["Heading3"], textColor=ACCENT, fontSize=11, spaceBefore=6, spaceAfter=2))
    styles.add(ParagraphStyle("Bodyx", parent=styles["BodyText"], fontSize=9.5, leading=14))
    styles.add(ParagraphStyle("Bulletx", parent=styles["BodyText"], fontSize=9.5, leading=14, leftIndent=12, bulletIndent=2))

    story = []
    lines = markdown_text.splitlines()
    i = 0
    table_buffer = []

    def flush_table():
        nonlocal table_buffer
        if not table_buffer:
            return
        rows = []
        for r in table_buffer:
            cells = [c.strip() for c in r.strip().strip("|").split("|")]
            rows.append(cells)
        # drop separator row like |---|---|
        rows = [r for r in rows if not all(set(c) <= set("-: ") for c in r)]
        if rows:
            data = [[Paragraph(_inline(c), styles["Bodyx"]) for c in row] for row in rows]
            tbl = Table(data, repeatRows=1, hAlign="LEFT")
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), BRAND),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F6F4")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(Spacer(1, 4))
            story.append(tbl)
            story.append(Spacer(1, 6))
        table_buffer = []

    while i < len(lines):
        line = lines[i].rstrip()

        if line.strip().startswith("|"):
            table_buffer.append(line)
            i += 1
            continue
        else:
            flush_table()

        if not line.strip():
            story.append(Spacer(1, 4))
        elif line.startswith("### "):
            story.append(Paragraph(_inline(line[4:]), styles["H3x"]))
        elif line.startswith("## "):
            story.append(Paragraph(_inline(line[3:]), styles["H2x"]))
        elif line.startswith("# "):
            story.append(Paragraph(_inline(line[2:]), styles["H1x"]))
            story.append(HRFlowable(width="100%", thickness=1, color=BRAND, spaceAfter=6))
        elif line.strip() in ("---", "***", "___"):
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D1D5DB"), spaceBefore=4, spaceAfter=4))
        elif line.lstrip().startswith(("- ", "* ")):
            txt = line.lstrip()[2:]
            story.append(Paragraph(_inline(txt), styles["Bulletx"], bulletText="•"))
        else:
            story.append(Paragraph(_inline(line), styles["Bodyx"]))
        i += 1

    flush_table()

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#9CA3AF"))
        canvas.drawString(20 * mm, 12 * mm, "ESG Intelligence Agent — indicative estimates, verify with product-specific EPDs.")
        canvas.drawRightString(190 * mm, 12 * mm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        pdf_path, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=20 * mm,
        title="ESG Intelligence Briefing",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return True
