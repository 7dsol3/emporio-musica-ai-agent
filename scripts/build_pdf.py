"""Build the English submission from committed Markdown, using ReportLab."""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import textwrap
from pathlib import Path
from urllib.parse import quote

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph,
                               SimpleDocTemplate, Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parent.parent
REPO = "https://github.com/7dsol3/emporio-musica-ai-agent"
DEFAULT_OUTPUT = ROOT / "output" / "pdf" / "Adilson Oliveira - AI Engineer - Full-Stack for Generative AI Applications.pdf"
INK = colors.HexColor("#193c39")
MUTED = colors.HexColor("#67756b")
ACCENT = colors.HexColor("#b7754d")
LINE = colors.HexColor("#dce3d4")
WIDTH = A4[0] - 94


def clean(value: str) -> str:
    for old, new in {"–": "-", "—": "-", "−": "-", "‑": "-", "→": "->", "↗": "", "’": "'", "‘": "'", "“": '"', "”": '"', "…": "...", "▸": "-", "✓": "OK"}.items():
        value = value.replace(old, new)
    return value


def inline(value: str, source: Path) -> str:
    value = html.escape(clean(value))

    def link(match):
        label, target = match.groups()
        if not target.startswith(("https://", "http://")):
            relative = (source.parent / target.split("#")[0]).resolve().relative_to(ROOT).as_posix()
            target = REPO + "/blob/main/" + quote(relative)
        return f'<link href="{target}" color="#47735c"><u>{label}</u></link>'

    value = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, value)
    value = re.sub(r"&lt;(https?://[^&]+)&gt;", r'<link href="\1" color="#47735c">\1</link>', value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"`([^`]+)`", r'<font name="Courier" size="8">\1</font>', value)
    return value


def styles():
    fonts = Path(reportlab.__file__).resolve().parent / "fonts"
    for name, filename in (("Body", "Vera.ttf"), ("Body-Bold", "VeraBd.ttf"), ("Body-Italic", "VeraIt.ttf")):
        pdfmetrics.registerFont(TTFont(name, fonts / filename))
    pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body-Italic", boldItalic="Body-Bold")
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(name="Text", fontName="Body", fontSize=9.1, leading=14, textColor=INK, spaceAfter=8, splitLongWords=True))
    s.add(ParagraphStyle(name="H1x", parent=s["Text"], fontName="Body-Bold", fontSize=19, leading=24, spaceBefore=14, spaceAfter=13, keepWithNext=True))
    s.add(ParagraphStyle(name="H2x", parent=s["Text"], fontName="Body-Bold", fontSize=12, leading=17, spaceBefore=13, spaceAfter=8, keepWithNext=True))
    s.add(ParagraphStyle(name="H3x", parent=s["Text"], fontName="Body-Bold", fontSize=10.1, leading=15, spaceBefore=10, spaceAfter=6, keepWithNext=True))
    s.add(ParagraphStyle(name="Smallx", parent=s["Text"], fontSize=7.8, leading=11.5, textColor=MUTED))
    s.add(ParagraphStyle(name="Codex", parent=s["Text"], fontName="Courier", fontSize=7.3, leading=10.5, backColor=colors.HexColor("#f0f3ec"), borderPadding=8, spaceBefore=4, spaceAfter=11))
    s.add(ParagraphStyle(name="Cellx", parent=s["Text"], fontSize=8.1, leading=12, spaceAfter=0))
    s.add(ParagraphStyle(name="CoverTitlex", parent=s["Text"], fontName="Times-Roman", fontSize=38, leading=43, spaceAfter=20))
    return s


def markdown(path: Path, s) -> list:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    result, paragraph = [], []

    def flush():
        if paragraph:
            result.append(Paragraph(inline(" ".join(paragraph), path), s["Text"]))
            paragraph.clear()

    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if line.startswith("```"):
            flush()
            language = line[3:].strip()
            block = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                block.append(lines[index])
                index += 1
            if language == "mermaid":
                result.append(Paragraph("Chat / CLI -&gt; session boundary -&gt; planner -&gt; validated tools -&gt; SQLite and policy retrieval -&gt; evidence renderer -&gt; answer and audit.", s["Codex"]))
            elif language == "json" and path.parent.name == "examples":
                receipt = json.loads("\n".join(block))
                names = ", ".join(item["tool"] for item in receipt) or "No tool call"
                result.append(Paragraph("Recorded checks: " + html.escape(names) + ". Full argument receipts remain in the repository.", s["Smallx"]))
            else:
                wrapped = []
                for original in block:
                    wrapped.extend(textwrap.wrap(clean(original), width=100, replace_whitespace=False, drop_whitespace=False) or [""])
                result.append(Paragraph("<br/>".join(html.escape(x).replace(" ", "&#160;") for x in wrapped), s["Codex"]))
        elif line.startswith("|"):
            flush()
            rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                cells = [c.strip() for c in lines[index].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    rows.append([Paragraph(inline(c, path), s["Cellx"]) for c in cells])
                index += 1
            index -= 1
            count = len(rows[0])
            widths = [WIDTH * .29, WIDTH * .71] if count == 2 else [WIDTH * .25, WIDTH * .38, WIDTH * .37] if count == 3 else [WIDTH/count]*count
            table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eaf0e5")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("LINEBELOW", (0, 0), (-1, -1), .4, LINE)]))
            result.extend([table, Spacer(1, 12)])
        elif line.startswith("!["):
            flush()
            match = re.match(r"!\[([^]]*)\]\(([^)]+)\)", line)
            image_path = (path.parent / match[2]).resolve()
            picture = Image(str(image_path))
            ratio = WIDTH / picture.imageWidth
            picture.drawWidth, picture.drawHeight = WIDTH, picture.imageHeight * ratio
            result.extend([picture, Spacer(1, 5), Paragraph(html.escape(match[1]), s["Smallx"]), Spacer(1, 10)])
        elif line.startswith("#"):
            flush()
            level = len(line)-len(line.lstrip("#"))
            result.append(Paragraph(inline(line.lstrip("# "), path), s["H1x" if level == 1 else "H2x" if level == 2 else "H3x"]))
        elif re.match(r"^(?:[-*•]|\d+\.)\s", line):
            flush()
            marker, content = re.match(r"^([-*•]|\d+\.)\s+(.*)$", line).groups()
            # Include continuation lines belonging to the same list item.
            while index+1 < len(lines) and lines[index+1].startswith("  ") and lines[index+1].strip():
                index += 1
                content += " " + lines[index].strip()
            result.append(Paragraph((marker if marker[0].isdigit() else "-") + " " + inline(content, path), s["Text"]))
        elif not line:
            flush()
        else:
            paragraph.append(line)
        index += 1
    flush()
    return result


def decoration(canvas, doc):
    canvas.saveState()
    page_width, page_height = A4
    canvas.setFillColor(MUTED)
    canvas.setFont("Body", 7)
    if doc.page > 1:
        canvas.drawString(47, page_height-29, "EMPÓRIO DA MÚSICA / TECHNICAL CASE")
        canvas.setStrokeColor(LINE)
        canvas.line(47, page_height-36, page_width-47, page_height-36)
    canvas.drawString(47, 27, "Adilson Oliveira  |  AI Engineer  |  English submission")
    canvas.drawRightString(page_width-47, 27, f"{doc.page:02}")
    canvas.restoreState()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    s = styles()
    revision = subprocess.check_output(["git", "rev-parse", "--short=12", "HEAD"], cwd=ROOT, text=True).strip()
    live = json.loads((ROOT / "docs" / "live-evaluation.json").read_text())
    ui = json.loads((ROOT / "docs" / "ui-check.json").read_text())
    if live["status"] != "PASS" or ui["status"] != "PASS":
        raise SystemExit("Evaluation and browser checks must pass before the submission is built")
    story = [Spacer(1, 45), Paragraph("ARTEFACT / AI ENGINEER TECHNICAL CASE", s["Smallx"]), Spacer(1, 25),
             Paragraph("Empório da Música<br/><font color='#b7754d'>Evidence before answers.</font>", s["CoverTitlex"]),
             Paragraph("A bilingual customer service agent with Python tools, local function calling, policy retrieval and verified order access.", s["H2x"]),
             Spacer(1, 25), Paragraph("Prepared for Adilson Oliveira", s["H2x"]),
             Paragraph("AI Engineer - Full-Stack for Generative AI Applications", s["Text"]),
             Paragraph("English technical submission | Case date: 31 October 2026", s["Smallx"]),
             Spacer(1, 28), Paragraph(f'<link href="{REPO}" color="#47735c"><u>{REPO}</u></link>', s["Text"]),
             Paragraph("Source revision: " + revision, s["Smallx"]),
             Spacer(1, 24), Paragraph("Included in this document", s["H2x"]),
             Paragraph("README and execution instructions; architecture; data and policy decisions; validation evidence; component/model provenance; attribution; five observed English conversations.", s["Text"]),
             Paragraph("The public repository contains source, incremental commits, full tool receipts and an optional interview preparation guide. This PDF is generated from its project documentation. No form submission or recruitment email is performed by the project.", s["Smallx"])]
    sources = [ROOT / "README.md", ROOT / "docs" / "ARCHITECTURE.md", ROOT / "docs" / "DATA_DECISIONS.md",
               ROOT / "docs" / "VALIDATION.md", ROOT / "docs" / "PROVENANCE.md", ROOT / "THIRD_PARTY_NOTICES.md",
               *sorted((ROOT / "examples").glob("*.md"))]
    for source in sources:
        story.append(PageBreak())
        story.extend(markdown(source, s))
    document = SimpleDocTemplate(str(args.output), pagesize=A4, rightMargin=47, leftMargin=47,
                                 topMargin=52, bottomMargin=48, title="Empório da Música - AI Engineer Technical Case",
                                 author="Adilson Oliveira", subject="README, project documentation and observed conversations")
    document.build(story, onFirstPage=decoration, onLaterPages=decoration)
    print(str(args.output))


if __name__ == "__main__":
    main()
