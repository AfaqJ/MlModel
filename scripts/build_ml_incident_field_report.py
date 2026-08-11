#!/usr/bin/env python3
"""Render the project incident/recovery field report as a polished local PDF.

The Markdown source is the editable truth. This builder intentionally uses a
small supported Markdown subset so report generation stays local, deterministic,
and easy to review. It does not read or change model/data files.
"""
from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    HRFlowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    LongTable,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.platypus.xpreformatted import XPreformatted


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "docs/ML_MODEL_INCIDENT_RECOVERY_FIELD_REPORT.md"
DEFAULT_OUTPUT = ROOT / "output/pdf/AI-Collaboration-Field-Guide-ML-Model-Incident-Edition.pdf"

PAGE_W, PAGE_H = A4
BLACK = colors.HexColor("#111111")
INK = colors.HexColor("#202020")
IVORY = colors.HexColor("#F4F1E8")
PAPER = colors.HexColor("#FBFAF6")
YELLOW = colors.HexColor("#FFD400")
RED = colors.HexColor("#FF3B30")
PINK = colors.HexColor("#F35AAF")
BLUE = colors.HexColor("#64B9EA")
GREEN = colors.HexColor("#56B870")
MUTED = colors.HexColor("#69655D")
GRID = colors.HexColor("#CFC9BC")


def register_fonts() -> tuple[str, str, str, str]:
    candidates = [
        (
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Italic.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold Italic.ttf",
        ),
        (
            "/Library/Fonts/Arial.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "/Library/Fonts/Arial Italic.ttf",
            "/Library/Fonts/Arial Bold Italic.ttf",
        ),
    ]
    for regular, bold, italic, bold_italic in candidates:
        if all(Path(path).exists() for path in (regular, bold, italic, bold_italic)):
            pdfmetrics.registerFont(TTFont("FieldSans", regular))
            pdfmetrics.registerFont(TTFont("FieldSans-Bold", bold))
            pdfmetrics.registerFont(TTFont("FieldSans-Italic", italic))
            pdfmetrics.registerFont(TTFont("FieldSans-BoldItalic", bold_italic))
            pdfmetrics.registerFontFamily(
                "FieldSans",
                normal="FieldSans",
                bold="FieldSans-Bold",
                italic="FieldSans-Italic",
                boldItalic="FieldSans-BoldItalic",
            )
            return "FieldSans", "FieldSans-Bold", "FieldSans-Italic", "FieldSans-BoldItalic"
    return "Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Helvetica-BoldOblique"


FONT, FONT_BOLD, FONT_ITALIC, FONT_BOLD_ITALIC = register_fonts()
MONO = "Courier"
MONO_BOLD = "Courier-Bold"


def inline_markup(text: str) -> str:
    """Escape text and add minimal bold/code Markdown support."""
    chunks = re.split(r"(`[^`]*`|\*\*[^*]+\*\*)", text)
    rendered: list[str] = []
    for chunk in chunks:
        if chunk.startswith("`") and chunk.endswith("`"):
            rendered.append(
                f'<font name="{MONO}" color="#6A1747">{escape(chunk[1:-1])}</font>'
            )
        elif chunk.startswith("**") and chunk.endswith("**"):
            rendered.append(f"<b>{escape(chunk[2:-2])}</b>")
        else:
            rendered.append(escape(chunk))
    return "".join(rendered).replace("  ", " &nbsp;")


def make_styles():
    base = getSampleStyleSheet()
    styles = {}
    styles["body"] = ParagraphStyle(
        "Body",
        parent=base["BodyText"],
        fontName=FONT,
        fontSize=9.2,
        leading=13.2,
        textColor=INK,
        spaceAfter=7,
        allowWidows=0,
        allowOrphans=0,
    )
    styles["small"] = ParagraphStyle(
        "Small",
        parent=styles["body"],
        fontSize=7.8,
        leading=10.5,
        textColor=MUTED,
    )
    styles["h1"] = ParagraphStyle(
        "Heading1",
        parent=base["Heading1"],
        fontName=FONT_BOLD,
        fontSize=20,
        leading=23,
        textColor=YELLOW,
        backColor=BLACK,
        borderPadding=(9, 10, 8, 10),
        spaceBefore=0,
        spaceAfter=14,
        keepWithNext=True,
    )
    styles["h2"] = ParagraphStyle(
        "Heading2",
        parent=base["Heading2"],
        fontName=FONT_BOLD,
        fontSize=13.5,
        leading=16,
        textColor=BLACK,
        spaceBefore=10,
        spaceAfter=7,
        keepWithNext=True,
    )
    styles["h3"] = ParagraphStyle(
        "Heading3",
        parent=base["Heading3"],
        fontName=FONT_BOLD,
        fontSize=10.5,
        leading=13,
        textColor=colors.HexColor("#7A164C"),
        spaceBefore=8,
        spaceAfter=5,
        keepWithNext=True,
    )
    styles["quote"] = ParagraphStyle(
        "Quote",
        parent=styles["body"],
        fontName=FONT_BOLD,
        fontSize=9.2,
        leading=13.5,
        textColor=BLACK,
        backColor=colors.HexColor("#FFF0A8"),
        borderColor=BLACK,
        borderWidth=1.2,
        borderPadding=10,
        spaceBefore=4,
        spaceAfter=10,
    )
    styles["code"] = ParagraphStyle(
        "Code",
        fontName=MONO,
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#F7F4E9"),
        backColor=BLACK,
        borderPadding=9,
        spaceBefore=4,
        spaceAfter=10,
    )
    styles["bullet"] = ParagraphStyle(
        "Bullet",
        parent=styles["body"],
        leftIndent=0,
        firstLineIndent=0,
        spaceAfter=2,
    )
    styles["table_header"] = ParagraphStyle(
        "TableHeader",
        fontName=FONT_BOLD,
        fontSize=7.5,
        leading=9.4,
        textColor=colors.white,
    )
    styles["table_cell"] = ParagraphStyle(
        "TableCell",
        fontName=FONT,
        fontSize=7.25,
        leading=9.3,
        textColor=INK,
    )
    styles["toc_title"] = ParagraphStyle(
        "TOCTitle",
        fontName=FONT_BOLD,
        fontSize=24,
        leading=28,
        textColor=BLACK,
        spaceAfter=14,
    )
    return styles


STYLES = make_styles()


class ColorBand(Flowable):
    def __init__(self, width: float, height: float = 8 * mm):
        super().__init__()
        self.width = width
        self.height = height

    def draw(self):
        widths = [0.48, 0.18, 0.17, 0.17]
        palette = [YELLOW, RED, PINK, BLUE]
        x = 0
        for fraction, color in zip(widths, palette):
            self.canv.setFillColor(color)
            self.canv.rect(x, 0, self.width * fraction, self.height, stroke=0, fill=1)
            x += self.width * fraction


class FieldGuideDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str, **kwargs):
        super().__init__(filename, **kwargs)
        self._have_h1 = False

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            style_name = flowable.style.name
            if style_name in {"Heading1", "Heading2"}:
                level = 0 if style_name == "Heading1" else 1
                text = flowable.getPlainText()
                key = "heading-" + hashlib.sha1(
                    f"{style_name}\0{text}".encode("utf-8")
                ).hexdigest()[:16]
                self.canv.bookmarkPage(key)
                if style_name == "Heading1":
                    self._have_h1 = True
                    self.canv.addOutlineEntry(text, key, level=0, closed=False)
                if style_name == "Heading1":
                    self.notify("TOCEntry", (0, text, self.page, key))


def cover_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(YELLOW)
    canvas.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    canvas.setStrokeColor(BLACK)
    canvas.setLineWidth(2.2)
    canvas.rect(15 * mm, 15 * mm, PAGE_W - 30 * mm, PAGE_H - 30 * mm, stroke=1, fill=0)
    canvas.restoreState()


def content_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    if doc.page > 2:
        canvas.setFillColor(BLACK)
        canvas.rect(0, PAGE_H - 12 * mm, PAGE_W, 12 * mm, stroke=0, fill=1)
        canvas.setFont(FONT_BOLD, 7.5)
        canvas.setFillColor(YELLOW)
        canvas.drawString(17 * mm, PAGE_H - 7.6 * mm, "TRACE THE DATA. TRACE THE DECISION.")
        canvas.setFillColor(colors.white)
        canvas.drawRightString(
            PAGE_W - 17 * mm,
            PAGE_H - 7.6 * mm,
            "ML-MODEL INCIDENT AND RECOVERY - LOCAL ONLY",
        )
    canvas.setStrokeColor(GRID)
    canvas.setLineWidth(0.5)
    canvas.line(17 * mm, 13 * mm, PAGE_W - 17 * mm, 13 * mm)
    canvas.setFont(FONT, 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(17 * mm, 8.5 * mm, "Commit 9776523 - branch codex/milk-fix-clean - 11 Aug 2026")
    canvas.drawRightString(PAGE_W - 17 * mm, 8.5 * mm, f"PAGE {doc.page:02d}")
    canvas.restoreState()


def cover_story() -> list:
    available = PAGE_W - 44 * mm
    title = Paragraph(
        "DO NOT JUST<br/>TRUST THE MODEL.<br/>TRACE IT.",
        ParagraphStyle(
            "CoverTitle",
            fontName=FONT_BOLD,
            fontSize=30,
            leading=28,
            textColor=BLACK,
            spaceAfter=12,
        ),
    )
    subtitle = Paragraph(
        "ML-Model incident, Claude work,<br/>independent audit, and local recovery",
        ParagraphStyle(
            "CoverSubtitle",
            fontName=FONT_BOLD,
            fontSize=15,
            leading=19,
            textColor=BLACK,
        ),
    )
    answer = Paragraph(
        "The milk failure began in data promotion: 47 valid milk lines became one gold example, "
        "then training silently removed the class. This report traces every data stream, Claude-era "
        "detour, independent audit, full-SetFit memory repair, metric, remaining risk, and rollback point.",
        ParagraphStyle(
            "CoverAnswer",
            fontName=FONT_BOLD,
            fontSize=10.2,
            leading=14,
            textColor=colors.white,
            backColor=BLACK,
            borderPadding=10,
        ),
    )
    control_data = [
        ["STATUS", "LOCAL CANDIDATE"],
        ["DEPLOYED", "NO"],
        ["PUSHED", "NO"],
        ["RECOVERY", "9776523"],
        ["ROLLBACK", "d3e2360 / a60e43f"],
    ]
    control = Table(control_data, colWidths=[38 * mm, available - 38 * mm])
    control.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), BLACK),
                ("TEXTCOLOR", (0, 0), (0, -1), YELLOW),
                ("FONTNAME", (0, 0), (0, -1), FONT_BOLD),
                ("FONTNAME", (1, 0), (1, -1), FONT_BOLD),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.8, BLACK),
                ("BACKGROUND", (1, 0), (1, -1), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return [
        Spacer(1, 30 * mm),
        Paragraph(
            'PROJECT INCIDENT FIELD REPORT <font color="#FFFFFF">/</font> 2026.08.11',
            ParagraphStyle(
                "CoverKicker",
                fontName=FONT_BOLD,
                fontSize=7.5,
                textColor=colors.white,
                backColor=BLACK,
                borderPadding=(4, 6, 4, 6),
                leading=10,
            ),
        ),
        Spacer(1, 11 * mm),
        title,
        Spacer(1, 4 * mm),
        subtitle,
        Spacer(1, 12 * mm),
        answer,
        Spacer(1, 12 * mm),
        control,
        Spacer(1, 14 * mm),
        ColorBand(available, 7 * mm),
        Spacer(1, 6 * mm),
        Paragraph(
            "A beginner-friendly, evidence-backed reconstruction. The supplied Field Guide PDF was "
            "used as the documentation framework and left unchanged.",
            ParagraphStyle(
                "CoverFoot",
                fontName=FONT_BOLD,
                fontSize=8,
                leading=11,
                textColor=BLACK,
                alignment=TA_CENTER,
            ),
        ),
        NextPageTemplate("content"),
        PageBreak(),
    ]


def toc_story() -> list:
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(
            "TOCLevel1",
            fontName=FONT_BOLD,
            fontSize=10,
            leading=14,
            textColor=BLACK,
            leftIndent=0,
            firstLineIndent=0,
            spaceBefore=5,
        ),
    ]
    return [
        Paragraph("CONTENTS", STYLES["toc_title"]),
        Paragraph(
            "Read Parts I-IV for the full story. Parts V-XI explain the current system, risks, "
            "rollback, Field Guide audit, safe claims, and next work. Appendices are the evidence map.",
            STYLES["body"],
        ),
        ColorBand(PAGE_W - 34 * mm, 5 * mm),
        Spacer(1, 8 * mm),
        toc,
        PageBreak(),
    ]


def table_widths(rows: list[list[str]], available: float) -> list[float]:
    cols = len(rows[0])
    weights = []
    for col in range(cols):
        longest = max(len(re.sub(r"[`*]", "", row[col])) for row in rows)
        weights.append(max(6.0, min(34.0, longest ** 0.62)))
    total = sum(weights)
    return [available * weight / total for weight in weights]


def make_table(rows: list[list[str]], available: float):
    converted = []
    for row_index, row in enumerate(rows):
        style = STYLES["table_header"] if row_index == 0 else STYLES["table_cell"]
        converted.append([Paragraph(inline_markup(cell.strip()), style) for cell in row])
    table = LongTable(converted, colWidths=table_widths(rows, available), repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BLACK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, IVORY]),
                ("LINEBELOW", (0, 0), (-1, 0), 1.2, YELLOW),
                ("LINEBELOW", (0, 1), (-1, -1), 0.25, GRID),
                ("BOX", (0, 0), (-1, -1), 0.65, BLACK),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def parse_markdown(source: str, available: float) -> list:
    lines = source.splitlines()
    # Cover content is generated separately. Start after the first divider.
    try:
        start = lines.index("---") + 1
    except ValueError:
        start = 0
    lines = lines[start:]
    story: list = []
    paragraph: list[str] = []
    code_lines: list[str] = []
    in_code = False
    table_rows: list[list[str]] = []
    bullets: list[str] = []
    numbered: list[str] = []
    seen_h1 = False

    def flush_paragraph():
        nonlocal paragraph
        if paragraph:
            text = " ".join(part.strip() for part in paragraph)
            story.append(Paragraph(inline_markup(text), STYLES["body"]))
            paragraph = []

    def flush_code():
        nonlocal code_lines
        if code_lines:
            story.append(XPreformatted(escape("\n".join(code_lines)), STYLES["code"]))
            code_lines = []

    def flush_table():
        nonlocal table_rows
        if table_rows:
            clean_rows = [
                row
                for row in table_rows
                if not all(
                    re.fullmatch(r":?-{3,}:?", c.replace(" ", ""))
                    for c in row
                )
            ]
            if len(clean_rows) >= 2:
                story.append(make_table(clean_rows, available))
                story.append(Spacer(1, 7))
            table_rows = []

    def flush_list():
        nonlocal bullets, numbered
        if bullets:
            items = [ListItem(Paragraph(inline_markup(item), STYLES["bullet"]), leftIndent=8) for item in bullets]
            story.append(ListFlowable(items, bulletType="bullet", start="circle", leftIndent=16, bulletFontName=FONT_BOLD, bulletColor=BLACK, spaceAfter=7))
            bullets = []
        if numbered:
            items = [ListItem(Paragraph(inline_markup(item), STYLES["bullet"]), leftIndent=8) for item in numbered]
            story.append(ListFlowable(items, bulletType="1", leftIndent=18, bulletFontName=FONT_BOLD, bulletColor=BLACK, spaceAfter=7))
            numbered = []

    def flush_all():
        flush_paragraph()
        flush_table()
        flush_list()

    for raw_line in lines:
        line = raw_line.rstrip()
        if line.startswith("```"):
            flush_paragraph()
            flush_table()
            flush_list()
            if in_code:
                flush_code()
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not line.strip():
            flush_all()
            continue
        if line == "---":
            flush_all()
            story.append(Spacer(1, 3))
            story.append(HRFlowable(width="100%", thickness=1.2, color=BLACK, spaceBefore=3, spaceAfter=8))
            continue
        if line.startswith("# "):
            flush_all()
            heading_text = line[2:].strip()
            if seen_h1 and not heading_text.startswith("APPENDIX"):
                story.append(PageBreak())
            seen_h1 = True
            story.append(Paragraph(inline_markup(heading_text), STYLES["h1"]))
            continue
        if line.startswith("## "):
            flush_all()
            story.append(Paragraph(inline_markup(line[3:].strip()), STYLES["h2"]))
            continue
        if line.startswith("### "):
            flush_all()
            story.append(Paragraph(inline_markup(line[4:].strip()), STYLES["h3"]))
            continue
        if line.startswith("> "):
            flush_all()
            story.append(Paragraph(inline_markup(line[2:].strip()), STYLES["quote"]))
            continue
        if line.startswith("|") and line.endswith("|"):
            flush_paragraph()
            flush_list()
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            table_rows.append(cells)
            continue
        bullet_match = re.match(r"^-\s+(.*)$", line)
        if bullet_match:
            flush_paragraph()
            flush_table()
            if numbered:
                flush_list()
            bullets.append(bullet_match.group(1))
            continue
        number_match = re.match(r"^\d+\.\s+(.*)$", line)
        if number_match:
            flush_paragraph()
            flush_table()
            if bullets:
                flush_list()
            numbered.append(number_match.group(1))
            continue
        flush_table()
        flush_list()
        paragraph.append(line)

    flush_all()
    flush_code()
    return story


def build(source_path: Path, output_path: Path) -> None:
    source = source_path.read_text(encoding="utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    left = right = 17 * mm
    top = 18 * mm
    bottom = 17 * mm
    frame = Frame(left, bottom, PAGE_W - left - right, PAGE_H - top - bottom, id="main")
    cover_frame = Frame(22 * mm, 22 * mm, PAGE_W - 44 * mm, PAGE_H - 44 * mm, id="cover")
    doc = FieldGuideDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=left,
        rightMargin=right,
        topMargin=top,
        bottomMargin=bottom,
        title="ML-Model Incident and Recovery Field Report",
        author="Codex for Afaq",
        subject="Evidence-backed local reconstruction of the invoice classifier incident and recovery",
    )
    doc.addPageTemplates(
        [
            PageTemplate(id="cover", frames=[cover_frame], onPage=cover_page),
            PageTemplate(id="content", frames=[frame], onPage=content_page),
        ]
    )
    available = PAGE_W - left - right
    story = cover_story() + toc_story() + parse_markdown(source, available)
    doc.multiBuild(story)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build(args.source, args.output)
    print(args.output)


if __name__ == "__main__":
    main()
