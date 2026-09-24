"""
Assembles agent outputs into an executive-grade Microsoft Word (.docx) report.

Key capabilities:
- Strictly single-file Word (.docx) output.
- Executive styling: Corporate Navy & Slate color palette, Calibri typography.
- Markdown engine: Converts tables, headings, bold/italics, and lists into native Word objects.
- High-resilience: Sanitizes XML control characters, cleans HTML tags (<br>) and informal emojis,
  handles file-locking permission conflicts, and ensures directories exist.
"""

import os
import re
from datetime import datetime
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from config import MIN_REPORT_WORDS, REPORTS_DIR

SECTION_ORDER = [
    "executive_summary",
    "product_idea",
    "market_and_competitor_research",
    "comparative_analysis",
    "risk_factors",
    "recommendation",
]

SECTION_TITLES = {
    "executive_summary": "1. Executive Summary",
    "product_idea": "2. Product & Business Vision",
    "market_and_competitor_research": "3. Market Landscape & Competitor Intelligence",
    "comparative_analysis": "4. Comparative Differentiation & Advantage",
    "risk_factors": "5. Comprehensive Risk Assessment",
    "recommendation": "6. Strategic Recommendations & Action Plan",
}

# Regex to match bullet lines (dashes, asterisks not followed by bold, or unicode bullets)
BULLET_PATTERN = re.compile(r"^(?:[•\u2022\u25cf\u25aa]|-(?!-)\s*|\*(?!\*)\s*)\s*")


def slugify(text: str) -> str:
    """Generates a clean, filesystem-safe slug from arbitrary text."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", (text or "").strip().lower())
    return slug.strip("_")[:40] or "business_research_report"


def sanitize_xml(text: str) -> str:
    """
    Strips XML 1.0 invalid control characters to prevent python-docx crashes.
    OpenXML forbids characters \x00-\x08, \x0B-\x0C, \x0E-\x1F, \x7F.
    """
    if not text:
        return ""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)


def clean_executive_text(text: str) -> str:
    """
    Transforms raw HTML tags, informal emojis, and bracketed footnotes
    into clean, executive-grade corporate prose.
    """
    if not text:
        return ""

    # Strip HTML tags
    text = re.sub(r"</?[a-zA-Z][^>]*>", "", text)

    # Convert informal tick marks & crosses into professional corporate indicators
    text = re.sub(r"[✅✔☑]|\[x\]|\[X\]", "Yes", text)
    text = re.sub(r"[❌✖☒]", "No", text)

    # Clean full-width Chinese/Japanese citation brackets e.g. 【1】【2】 -> [1][2]
    text = text.replace("【", "[").replace("】", "]")

    # Sanitize invalid XML control codes
    return sanitize_xml(text)


def _total_words(sections: dict[str, str]) -> int:
    return sum(len(s.split()) for s in sections.values())


def _set_cell_background(cell, fill_hex: str) -> None:
    """Set shading color for a table cell."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    tc_pr.append(shd)


def _set_table_borders(table, color: str = "CBD5E1", sz: str = "4") -> None:
    """Applies clean, subtle borders to a table."""
    tblPr = table._tbl.tblPr
    tblBorders = OxmlElement("w:tblBorders")
    for border_name in ["top", "left", "bottom", "right", "insideH", "insideV"]:
        border = OxmlElement(f"w:{border_name}")
        border.set(qn("w:val"), "single")
        border.set(qn("w:sz"), sz)
        border.set(qn("w:space"), "0")
        border.set(qn("w:color"), color)
        tblBorders.append(border)
    tblPr.append(tblBorders)


def _set_cell_margins(cell, top: int = 100, bottom: int = 100, left: int = 120, right: int = 120) -> None:
    """Sets internal padding (margins) for a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for margin_name, val in [("top", top), ("bottom", bottom), ("left", left), ("right", right)]:
        node = OxmlElement(f"w:{margin_name}")
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)


def add_formatted_runs(
    paragraph,
    text: str,
    font_name: str = "Calibri",
    font_size_pt: float = 11,
    font_color_rgb: RGBColor | None = None,
    base_bold: bool = False,
    base_italic: bool = False,
) -> None:
    """
    Parses inline Markdown (**bold**, *italic*, `code`) and appends formatted runs to paragraph.
    """
    cleaned = clean_executive_text(text)
    if not cleaned:
        return

    tokens = re.split(r"(\*\*\*.*?\*\*\*|\*\*.*?\*\*|\*.*?\*|`.*?`)", cleaned)
    for token in tokens:
        if not token:
            continue
        is_bold = base_bold
        is_italic = base_italic
        content = token

        if token.startswith("***") and token.endswith("***") and len(token) >= 6:
            is_bold = True
            is_italic = True
            content = token[3:-3]
        elif token.startswith("**") and token.endswith("**") and len(token) >= 4:
            is_bold = True
            content = token[2:-2]
        elif token.startswith("*") and token.endswith("*") and len(token) >= 2:
            is_italic = True
            content = token[1:-1]
        elif token.startswith("`") and token.endswith("`") and len(token) >= 2:
            content = token[1:-1]

        sub_lines = content.split("\n")
        for i, sub in enumerate(sub_lines):
            if i > 0:
                paragraph.add_run().add_break()
            run = paragraph.add_run(sub)
            run.font.name = font_name
            run.font.size = Pt(font_size_pt)
            if is_bold:
                run.font.bold = True
            if is_italic:
                run.font.italic = True
            if font_color_rgb:
                run.font.color.rgb = font_color_rgb


def add_markdown_table(doc: Document, table_lines: list[str]) -> None:
    """
    Parses Markdown table lines and builds a styled, native Microsoft Word table.
    """
    parsed_rows = []
    for line in table_lines:
        line = line.strip()
        if not line or not ("|" in line):
            continue
        raw_cells = line.split("|")
        if raw_cells and raw_cells[0].strip() == "":
            raw_cells = raw_cells[1:]
        if raw_cells and raw_cells[-1].strip() == "":
            raw_cells = raw_cells[:-1]

        cells = [c.strip() for c in raw_cells]
        # Skip markdown separator row like |---|---|
        if all(re.match(r"^:?-+:?$", c) for c in cells if c):
            continue
        parsed_rows.append(cells)

    if not parsed_rows:
        return

    num_cols = max(len(r) for r in parsed_rows)
    for r in parsed_rows:
        while len(r) < num_cols:
            r.append("")

    num_rows = len(parsed_rows)
    table = doc.add_table(rows=num_rows, cols=num_cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(table, color="CBD5E1", sz="4")

    # 6.5 inches printable width divided across columns
    col_width = Inches(6.5 / num_cols)
    for col in table.columns:
        col.width = col_width

    for row_idx, row_data in enumerate(parsed_rows):
        row = table.rows[row_idx]
        is_header = (row_idx == 0)

        for col_idx, cell_text in enumerate(row_data):
            cell = row.cells[col_idx]
            cell.width = col_width
            _set_cell_margins(cell, top=100, bottom=100, left=120, right=120)

            if is_header:
                _set_cell_background(cell, "1E3A8A")  # Deep Corporate Navy
            else:
                bg_color = "F8FAFC" if (row_idx % 2 == 1) else "FFFFFF"
                _set_cell_background(cell, bg_color)

            # Convert <br> to newlines inside the cell
            cell_text = re.sub(r"<\s*br\s*/?\s*>", "\n", cell_text, flags=re.IGNORECASE)
            cleaned_text = clean_executive_text(cell_text)
            lines = [l.strip() for l in cleaned_text.split("\n") if l.strip()]

            if not lines:
                cell.paragraphs[0].text = ""
                continue

            for l_idx, line in enumerate(lines):
                if l_idx == 0:
                    p = cell.paragraphs[0]
                else:
                    p = cell.add_paragraph()

                p.paragraph_format.space_before = Pt(1)
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.line_spacing = 1.05

                is_bullet = bool(BULLET_PATTERN.match(line))
                if is_bullet:
                    line_clean = BULLET_PATTERN.sub("", line).strip()
                    brun = p.add_run("• ")
                    brun.font.name = "Calibri"
                    brun.font.size = Pt(9.5 if not is_header else 10)
                    brun.font.bold = is_header
                    brun.font.color.rgb = (
                        RGBColor(0xFF, 0xFF, 0xFF) if is_header else RGBColor(0x25, 0x63, 0xEB)
                    )
                    line_to_add = line_clean
                else:
                    line_to_add = line

                font_color = (
                    RGBColor(0xFF, 0xFF, 0xFF) if is_header else RGBColor(0x1F, 0x29, 0x37)
                )
                add_formatted_runs(
                    p,
                    line_to_add,
                    font_name="Calibri",
                    font_size_pt=10 if is_header else 9.5,
                    font_color_rgb=font_color,
                    base_bold=is_header,
                )

    sp = doc.add_paragraph()
    sp.paragraph_format.space_before = Pt(4)
    sp.paragraph_format.space_after = Pt(6)


def add_section_content(doc: Document, raw_content: str) -> None:
    """
    Parses section markdown text and writes headings, lists, tables,
    and formatted paragraphs into the Word document.
    """
    # Keep <br> intact for line splitting so tables don't break row-boundaries
    lines = raw_content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # 1. Skip markdown horizontal rules (---, ***, ___)
        if re.match(r"^[-*_]{3,}$", line):
            i += 1
            continue

        # 2. Markdown Table Detection
        if line.startswith("|") or (line.count("|") >= 2 and i + 1 < len(lines) and "|" in lines[i + 1]):
            table_lines = []
            while i < len(lines) and ("|" in lines[i] or re.match(r"^\s*[-| :]+\s*$", lines[i])):
                if lines[i].strip():
                    table_lines.append(lines[i])
                i += 1
            if table_lines:
                add_markdown_table(doc, table_lines)
            continue

        # 3. Headings (#, ##, ###, ####)
        heading_match = re.match(r"^(#{1,4})\s+(.+)$", line)
        if heading_match:
            hashes, heading_text = heading_match.groups()
            level = len(hashes)
            doc_level = min(level + 1, 4)
            h = doc.add_heading(level=doc_level)
            h_size = 14 if doc_level == 2 else (12.5 if doc_level == 3 else 11.5)
            h_color = (
                RGBColor(0x1E, 0x3A, 0x8A) if doc_level <= 2 else RGBColor(0x25, 0x63, 0xEB)
            )
            add_formatted_runs(
                h,
                heading_text.strip(),
                font_name="Calibri",
                font_size_pt=h_size,
                font_color_rgb=h_color,
                base_bold=True,
            )
            i += 1
            continue

        # 4. Bullet List Items
        if BULLET_PATTERN.match(line):
            item_text = BULLET_PATTERN.sub("", line).strip()
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            add_formatted_runs(p, item_text)
            i += 1
            continue

        # 5. Numbered List Items
        num_match = re.match(r"^\d+\.\s+", line)
        if num_match:
            item_text = line[num_match.end():].strip()
            p = doc.add_paragraph(style="List Number")
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            add_formatted_runs(p, item_text)
            i += 1
            continue

        # 6. Regular Paragraph (accumulate until blank line or structural block)
        para_lines = [line]
        i += 1
        while i < len(lines):
            next_line = lines[i].strip()
            if not next_line:
                i += 1
                break
            if (
                next_line.startswith("|")
                or re.match(r"^#{1,4}\s+", next_line)
                or BULLET_PATTERN.match(next_line)
                or re.match(r"^\d+\.\s+", next_line)
                or re.match(r"^[-*_]{3,}$", next_line)
            ):
                break
            para_lines.append(next_line)
            i += 1

        p_text = " ".join(para_lines)
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15
        add_formatted_runs(p, p_text)


def save_report_docx(idea: str, sections: dict[str, str], run_id: str) -> str:
    """Builds a high-impact, professional Word (.docx) document."""
    total_words = _total_words(sections)
    generated_at = datetime.now().strftime("%B %d, %Y - %H:%M UTC")

    doc = Document()

    # Page Margins (1.0 inch standard executive margins)
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # Base typography
    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Calibri"
    normal_style.font.size = Pt(11)
    normal_style.font.color.rgb = RGBColor(0x1F, 0x29, 0x37)

    # Header Title
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(4)
    title_run = title_p.add_run("STRATEGIC BUSINESS RESEARCH REPORT")
    title_run.font.size = Pt(22)
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)

    subtitle_p = doc.add_paragraph()
    subtitle_p.paragraph_format.space_before = Pt(0)
    subtitle_p.paragraph_format.space_after = Pt(8)
    sub_run = subtitle_p.add_run(f"Evaluation & Market Assessment: {clean_executive_text(idea)}")
    sub_run.font.size = Pt(13)
    sub_run.font.bold = True
    sub_run.font.color.rgb = RGBColor(0x3B, 0x82, 0xF6)

    # Metadata Summary Box
    meta_table = doc.add_table(rows=1, cols=1)
    meta_table.autofit = False
    meta_table.columns[0].width = Inches(6.5)
    cell = meta_table.cell(0, 0)
    _set_cell_background(cell, "F1F5F9")
    _set_cell_margins(cell, top=120, bottom=120, left=150, right=150)
    _set_table_borders(meta_table, color="E2E8F0", sz="4")

    cp = cell.paragraphs[0]
    cp.paragraph_format.space_before = Pt(0)
    cp.paragraph_format.space_after = Pt(0)
    target_status = "Target Met" if total_words >= MIN_REPORT_WORDS else "Compact Brief"
    safe_run_id = re.sub(r"[^a-zA-Z0-9_-]+", "_", (run_id or "").strip()) or "run"
    meta_text = (
        f"Generated: {generated_at}  |  Run ID: {safe_run_id}\n"
        f"Document Volume: ~{total_words:,} words ({target_status})  |  Format: Microsoft Word (.docx)"
    )
    c_run = cp.add_run(meta_text)
    c_run.font.size = Pt(9.5)
    c_run.font.italic = True
    c_run.font.color.rgb = RGBColor(0x47, 0x55, 0x69)

    doc.add_paragraph()

    # Track processed keys to ensure no sections are missed
    processed_keys = set()

    for key in SECTION_ORDER:
        if key not in sections:
            continue
        processed_keys.add(key)
        title_text = SECTION_TITLES.get(key, key.replace("_", " ").title())
        h = doc.add_heading(level=1)
        h.paragraph_format.space_before = Pt(14)
        h.paragraph_format.space_after = Pt(6)
        h_run = h.add_run(title_text)
        h_run.font.size = Pt(15)
        h_run.font.bold = True
        h_run.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)

        add_section_content(doc, sections[key])

    # Include any extra sections not in SECTION_ORDER
    for key, content in sections.items():
        if key in processed_keys or not content:
            continue
        title_text = key.replace("_", " ").title()
        h = doc.add_heading(level=1)
        h.paragraph_format.space_before = Pt(14)
        h.paragraph_format.space_after = Pt(6)
        h_run = h.add_run(title_text)
        h_run.font.size = Pt(15)
        h_run.font.bold = True
        h_run.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)
        add_section_content(doc, content)

    # Ensure reports directory exists
    os.makedirs(REPORTS_DIR, exist_ok=True)

    safe_slug = slugify(idea)
    filename = f"{safe_slug}_{safe_run_id}.docx"
    path = os.path.join(REPORTS_DIR, filename)

    # Resilient file saving with file-lock handling
    try:
        doc.save(path)
    except PermissionError:
        # File may be open in MS Word on Windows; save to timestamped fallback
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        alt_filename = f"{safe_slug}_{safe_run_id}_{timestamp}.docx"
        path = os.path.join(REPORTS_DIR, alt_filename)
        doc.save(path)

    return path


def save_report(idea: str, sections: dict[str, str], run_id: str, output_format: str = "docx") -> str:
    """
    Unified entry point: Strictly outputs only one Microsoft Word (.docx) file.
    Includes emergency fallback so research is never lost if an unexpected OS error occurs.
    """
    try:
        return save_report_docx(idea, sections, run_id)
    except Exception as exc:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        safe_run_id = re.sub(r"[^a-zA-Z0-9_-]+", "_", (run_id or "").strip()) or "run"
        fallback_path = os.path.join(REPORTS_DIR, f"{slugify(idea)}_{safe_run_id}_backup.txt")
        with open(fallback_path, "w", encoding="utf-8") as f:
            f.write(f"EMERGENCY BACKUP REPORT: {idea}\nRun ID: {run_id}\n\n")
            for k, v in sections.items():
                f.write(f"\n\n=== {k.upper()} ===\n\n{v}\n")
        raise RuntimeError(
            f"Failed to generate Word document ({exc}). Emergency backup saved to: {fallback_path}"
        ) from exc
