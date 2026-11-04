# /// script
# requires-python = ">=3.10"
# dependencies = ["python-docx>=1.1", "pillow>=10", "pymupdf>=1.24"]
# ///
"""Build a FICTIONAL case-based self-study guide for practice.

The layout mirrors the common case-guide format used in integrated M1/M2
curricula (course director notes, case presentation with labs, then one
section per discipline with topics, objectives, notes, and self-study
questions). The school, course, faculty, and patient are invented. Nothing
here is copied from any real course.

    uv run scripts/make_case_guide.py [--out sample/curriculum/GUIDE] [--pdf | --no-pdf] [--docx DIR]

It looks like a typical case-guide handout: a cover page (director band, course title, cover art, school
band), a detailed table of contents with page numbers, and an "N of M - Self Study Guide" footer. The cover art
and avatar are drawn in code (Pillow); the TOC page numbers come from a first PDF pass (PyMuPDF).

The demo input is a PDF (a fictional M1 class handout). The .docx is built in a temp folder and converted
with LibreOffice (`soffice --headless --convert-to pdf`), so the PDF keeps the fictional footer on every page.
--pdf is the default and needs `soffice` (PATH or the macOS app bundle); --docx DIR also keeps the editable
.docx there. --no-pdf builds only the .docx, into --docx DIR (or --out when no --docx is given).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

SCHOOL = "Meridian College of Medicine (fictional)"
COURSE = "BMS 501"
COURSE_TITLE = "Foundations of Infection and Immunity"
CASE = "Case 2: Jordan Rivera"
STEM = "BMS 501 Self-Study Guide 02 Jordan Rivera (fictional sample)"
FILENAME = STEM + ".docx"
PDF_FILENAME = STEM + ".pdf"
NOTICE = (
    "Educational demo. AI supports learning, it does not replace it. Real course materials belong to "
    "your institution: follow its AI policy before uploading anything."
)
SOFFICE_APP = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
DISCLAIMER = (
    "FICTIONAL SAMPLE for practice with the Med Student AI Study Agent. "
    "Invented school, faculty, and patient. Not affiliated with any medical school."
)
DIRECTOR = ("Dr. Morgan Hale (fictional)", "morgan.hale@meridian.example")
VERSION = "v. 11/2026"
RUNNING = f"Self Study Guide: Jordan Rivera ({COURSE_TITLE}) ({VERSION})"
FONT = "Arial"  # a plain sans that LibreOffice maps to Liberation Sans where Arial is missing
BAND = "2F6B2F"  # dark green bands and table headers
GREEN = RGBColor(0x5C, 0x9E, 0x3C)  # cover title green
HEAD = RGBColor(0x2F, 0x6B, 0x2F)  # heading green
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

# One self-study topic per discipline, in the guide's "Topic (TO-code) > Videos / Slides / Notes" layout.
TOPICS = {
    "Immunology": ("Innate Defenses Against Skin Infection", "TO-2101",
                   ["Barriers and Pattern Recognition (TO-2101) (14:20)",
                    "Neutrophil Recruitment and Extravasation (TO-2101) (12:05)",
                    "Phagocytosis and Oxidative Killing (TO-2101) (10:42)"],
                   ["Innate Immunity: Barriers, Recognition, and Neutrophils (TO-2101)"],
                   "See Below"),
    "Microbiology": ("Staphylococci and Methicillin Resistance", "TO-2205",
                     ["Staphylococci: Identification (TO-2205) (9:40)",
                      "S. aureus Virulence Factors and Toxins (TO-2205) (16:15)",
                      "MRSA: Mechanism and Epidemiology (TO-2205) (8:30)"],
                     ["Staphylococcus aureus (TO-2205)"],
                     "See Below"),
    "Pharmacology": ("Antibiotics for Gram-Positive Infections", "TO-2312",
                     ["Cell Wall Inhibitors I: Beta-lactams (TO-2312) (13:10)",
                      "Cell Wall Inhibitors II: Vancomycin (TO-2312) (7:55)",
                      "Folate Antagonists and Tetracyclines (TO-2312) (11:20)"],
                     ["Antibiotics for Gram-Positive Infections (TO-2312)"],
                     "No Written Notes"),
}


def toc_entries() -> list[tuple[int, str]]:
    """(indent level, text) for the table of contents; each text also appears, in order, in the body."""
    out = [(0, "Course Director Notes"), (0, "Case Presentation")]
    for discipline, (title, code, videos, slides, notes) in TOPICS.items():
        out += [(0, discipline), (1, "Self-Study Topics:"), (2, f"{title} ({code}):"), (3, "Videos:")]
        out += [(4, v) for v in videos] + [(3, "Slides:")] + [(4, sl) for sl in slides] + [(3, f"Notes: {notes}")]
        out += [(1, "Learning Objectives:"), (1, f"{discipline}: Self-Study Questions"),
                (1, f"{discipline}: Self-Study Questions + Answers")]
    return out + [(0, "Selected References")]


# ---------------------------------------------------------------- helpers
def shade(cell, hex_fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tc_pr.append(shd)


def para(doc, text: str = "", *, bold=False, italic=False, size=None, align=None, color=None):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold, run.italic = bold, italic
    if size:
        run.font.size = Pt(size)
    if color:
        run.font.color.rgb = color
    if align is not None:
        p.alignment = align
    return p


def bullets(doc, items: list[str], level: int = 0) -> None:
    style = "List Bullet" if level == 0 else "List Bullet 2"
    for item in items:
        doc.add_paragraph(item, style=style)


def boxed(doc, title: str, lines: list[str]) -> None:
    """One-cell shaded box, like the director-notes callouts."""
    table = doc.add_table(rows=1, cols=1)
    table.style = "Table Grid"
    cell = table.rows[0].cells[0]
    shade(cell, "E8EEF6")
    cell.paragraphs[0].add_run(title).bold = True
    for line in lines:
        cell.add_paragraph(line)
    doc.add_paragraph()


def grid(doc, header: list[str], rows: list[list[str]], fill="1F3A5F") -> None:
    width = max(i + 1 for r in [header, *rows] for i, c in enumerate(r) if c)
    header, rows = header[:width], [r[:width] for r in rows]
    table = doc.add_table(rows=1, cols=len(header))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for cell, text in zip(table.rows[0].cells, header):
        shade(cell, BAND if fill == "1F3A5F" else fill)
        run = cell.paragraphs[0].add_run(text)
        run.bold = True
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    for row in rows:
        new_row = table.add_row()
        new_row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))  # a row never straddles two pages
        cells = new_row.cells
        for col, (cell, text) in enumerate(zip(cells, row)):
            # Every value after the first column carries its column name ("Result: 14.2"). A PDF has no table
            # structure, so text extraction reads cells one per line; the label keeps each value attached to
            # its column even when a cell (such as an empty Flag) is blank.
            cell.text = text if col == 0 else f"{header[col]}: {text or 'none'}"
    # Keep the whole table on one page: with PDF page anchors, a citation to a table must name the page that
    # holds all of it.
    for row in table.rows[:-1]:
        for cell in row.cells:
            for p in cell.paragraphs:
                p.paragraph_format.keep_with_next = True
    # Column widths follow the longest cell, but never narrower than the longest word (10 pt Arial body text is about
    # 0.12 inch per character, plus cell padding), so no word breaks mid-word in the extracted text.
    labelled = [[row[0]] + [f"{header[c]}: {row[c] or 'none'}" for c in range(1, len(row))] for row in rows]
    cells_by_col = [[r[c] for r in [header, *labelled] if c < len(r)] for c in range(len(header))]
    longest = [max(max(len(t) for t in col), 8) for col in cells_by_col]
    need = [max(len(w) for t in col for w in t.split()) * 0.13 + 0.3 for col in cells_by_col]
    total = 7.3  # usable page width in inches
    widths = [total * n / sum(longest) for n in longest]
    for _ in range(len(widths)):
        short = [c for c, w in enumerate(widths) if w < need[c]]
        if not short:
            break
        for c in short:
            widths[c] = need[c]
        spare = [c for c in range(len(widths)) if c not in short and widths[c] > need[c]]
        excess = sum(widths) - total
        room = sum(widths[c] - need[c] for c in spare)
        if excess > 0 and room > 0:
            for c in spare:
                widths[c] -= excess * (widths[c] - need[c]) / room
    table.autofit = False
    for c, col in enumerate(table.columns):
        col.width = Inches(widths[c])
        for cell in col.cells:
            cell.width = col.width
    doc.add_paragraph()


def topics(doc, discipline: str) -> None:
    title, code, videos, slides, notes = TOPICS[discipline]
    doc.add_heading("Self-Study Topics:", level=2)
    doc.add_heading(f"{title} ({code}):", level=3)
    doc.add_heading("Videos:", level=4)
    for v in videos:
        doc.add_heading(v, level=5)
    doc.add_heading("Slides:", level=4)
    for s in slides:
        doc.add_heading(s, level=5)
    doc.add_heading(f"Notes: {notes}", level=4)


def objectives(doc, items: list[str]) -> None:
    doc.add_heading("Learning Objectives:", level=2)
    for i, item in enumerate(items, 1):
        doc.add_paragraph(f"{i}. {item}")


def questions(doc, discipline: str, qs: list[tuple[str, list[str], str, str]]) -> None:
    doc.add_heading(f"{discipline}: Self-Study Questions", level=3)
    for n, (stem, options, _, _) in enumerate(qs, 1):
        para(doc, f"{n}. {stem}")
        for letter, opt in zip("ABCDE", options):
            doc.add_paragraph(f"{letter}. {opt}", style="List Bullet 2")
    doc.add_heading(f"{discipline}: Self-Study Questions + Answers", level=3)
    for n, (stem, options, answer, why) in enumerate(qs, 1):
        para(doc, f"{n}. {stem}")
        for letter, opt in zip("ABCDE", options):
            doc.add_paragraph(f"{letter}. {opt}", style="List Bullet 2")
        para(doc, f"Answer: {answer}", bold=True)
        para(doc, why, italic=True)


def faculty(doc, director: str, email: str, office: str) -> None:
    para(doc, director, bold=True)
    para(doc, email)
    para(doc, office)


def discipline_notes(doc, lines: list[str]) -> None:
    para(doc, "Discipline Director Notes:", bold=True)
    bullets(doc, lines)


def page_break(doc) -> None:
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def field(paragraph, instr: str) -> None:
    """A Word field (PAGE, NUMPAGES) that LibreOffice fills in when it renders the PDF."""
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), instr)
    run, text = OxmlElement("w:r"), OxmlElement("w:t")
    size = OxmlElement("w:sz")
    size.set(qn("w:val"), "16")  # 8 pt, like the rest of the running footer
    props = OxmlElement("w:rPr")
    props.append(size)
    run.append(props)
    text.text = "1"
    run.append(text)
    fld.append(run)
    paragraph._p.append(fld)


def draw_avatar(path: Path) -> Path:
    """A generic gray head-and-shoulders placeholder (no real person)."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (240, 240), (205, 210, 214))
    d = ImageDraw.Draw(img)
    d.ellipse((80, 40, 160, 120), fill=(140, 146, 152))
    d.ellipse((35, 135, 205, 300), fill=(140, 146, 152))
    img.save(path)
    return path


def draw_cover(path: Path) -> Path:
    """Original cover art: grape-like clusters of golden cocci beside a neutrophil, on a soft tissue background."""
    import math
    import random
    from PIL import Image, ImageDraw, ImageFilter
    rng = random.Random(501)
    w, h = 1500, 1500
    img = Image.new("RGB", (w, h))
    bg = ImageDraw.Draw(img)
    for y in range(h):  # warm tissue-colored vertical gradient
        t = y / h
        bg.line([(0, y), (w, y)], fill=(int(120 + 70 * t), int(70 + 40 * t), int(78 + 30 * t)))
    blobs = Image.new("RGB", (w, h), (0, 0, 0))
    bd = ImageDraw.Draw(blobs)
    for _ in range(40):
        x, y, r = rng.randrange(w), rng.randrange(h), rng.randrange(60, 220)
        bd.ellipse((x - r, y - r, x + r, y + r), fill=rng.choice([(190, 130, 130), (150, 90, 100), (210, 170, 160)]))
    img = Image.blend(img, blobs.filter(ImageFilter.GaussianBlur(70)), 0.45)

    def sphere(layer, cx, cy, r, base, hi):
        dd = ImageDraw.Draw(layer)
        for k in range(r, 0, -2):  # radial shading, highlight toward the upper left
            f = k / r
            col = tuple(int(b * f + hc * (1 - f)) for b, hc in zip(base, hi))
            off = int((r - k) * 0.35)
            dd.ellipse((cx - k - off, cy - k - off, cx + k - off, cy + k - off), fill=col)

    # neutrophil: a large gray-blue cell with long pseudopods
    cell = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    cd = ImageDraw.Draw(cell)
    ncx, ncy, nr = 960, 700, 320
    for a in range(0, 360, 9):
        ang = math.radians(a + rng.uniform(-3, 3))
        length = nr + rng.randrange(60, 260)
        pts = [(ncx + math.cos(ang) * nr * 0.8, ncy + math.sin(ang) * nr * 0.8)]
        for step in range(1, 7):
            rr = nr * 0.8 + (length - nr * 0.8) * step / 6
            wob = math.radians(rng.uniform(-6, 6))
            pts.append((ncx + math.cos(ang + wob) * rr, ncy + math.sin(ang + wob) * rr))
        cd.line(pts, fill=(150, 160, 178, 255), width=rng.randrange(10, 22), joint="curve")
    sphere(cell, ncx, ncy, nr, (165, 175, 192), (235, 240, 248))
    for _ in range(26):  # cell-surface ruffles
        x, y = ncx + rng.uniform(-0.65, 0.55) * nr, ncy + rng.uniform(-0.65, 0.55) * nr
        cd.ellipse((x - 18, y - 10, x + 18, y + 10), outline=(130, 140, 160, 255), width=4)
    img.paste(cell, (0, 0), cell)

    # gram-positive cocci in grape-like clusters
    cocci = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for cx, cy, n in ((330, 1130, 34), (430, 380, 22), (1220, 1300, 18)):
        for _ in range(n):
            x, y = cx + rng.gauss(0, 85), cy + rng.gauss(0, 70)
            sphere(cocci, int(x), int(y), rng.randrange(34, 44), (196, 150, 40), (255, 236, 150))
    img.paste(cocci, (0, 0), cocci)
    img.filter(ImageFilter.SMOOTH).save(path, quality=88)
    return path


def band(doc, text_lines: list[tuple[str, bool]], picture: Path | None = None, align=WD_ALIGN_PARAGRAPH.LEFT):
    """A full-width dark-green band (borderless table) with white text and an optional picture on the left."""
    table = doc.add_table(rows=1, cols=2 if picture else 1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cells = table.rows[0].cells
    for cell in cells:
        shade(cell, BAND)
    if picture:
        cells[0].paragraphs[0].add_run().add_picture(str(picture), width=Inches(0.85))
        table.autofit = False
        for col, width in zip(table.columns, (Inches(1.05), Inches(6.25))):  # LibreOffice reads column widths
            col.width = width
            for cell in col.cells:
                cell.width = width
    else:
        cells[0].width = Inches(7.3)
    target = cells[-1]
    for i, (line, bold) in enumerate(text_lines):
        p = target.paragraphs[0] if i == 0 else target.add_paragraph()
        p.alignment = align
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(line)
        run.bold, run.font.color.rgb, run.font.size = bold, WHITE, Pt(12)
    return table


def cover(doc, art_dir: Path) -> None:
    band(doc, [("Course Director:", True), (DIRECTOR[0], True), (DIRECTOR[1], True)],
         picture=draw_avatar(art_dir / "avatar.png"))
    para(doc, COURSE, bold=True, size=30, align=WD_ALIGN_PARAGRAPH.CENTER, color=GREEN)
    para(doc, COURSE_TITLE, bold=True, italic=True, size=24, align=WD_ALIGN_PARAGRAPH.CENTER, color=GREEN)
    para(doc, CASE, bold=True, size=18, align=WD_ALIGN_PARAGRAPH.CENTER, color=GREEN)
    pic = doc.add_paragraph()
    pic.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pic.add_run().add_picture(str(draw_cover(art_dir / "cover.jpg")), width=Inches(5.6))
    band(doc, [(SCHOOL, True)], align=WD_ALIGN_PARAGRAPH.CENTER)
    page_break(doc)


def table_of_contents(doc, pages: dict[int, int] | None) -> None:
    doc.add_heading("Table of Contents", level=1)
    for i, (level, text) in enumerate(toc_entries()):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.22 * level)
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.tab_stops.add_tab_stop(Inches(7.3), WD_TAB_ALIGNMENT.RIGHT)
        # Without computed pages (first pass, or a .docx-only build with no LibreOffice) the number is left blank.
        p.add_run(f"{text}\t{pages.get(i, '') if pages else ''}").font.size = Pt(9.5)
    page_break(doc)


def toc_pages(pdf: Path) -> dict[int, int]:
    """Page of each TOC entry in a rendered PDF: search the body in order, starting after the TOC."""
    import pymupdf
    with pymupdf.open(str(pdf)) as d:
        texts = [" ".join(page.get_text().split()) for page in d]
    start = next(i for i, t in enumerate(texts) if "Welcome to Case 2" in t)
    found, cursor = {}, start
    for i, (_, text) in enumerate(toc_entries()):
        hit = next((k for k in range(cursor, len(texts)) if text in texts[k]), None)
        if hit is None:
            raise SystemExit(f"table of contents: {text!r} not found in the rendered PDF")
        found[i], cursor = hit + 1, hit
    return found


# ---------------------------------------------------------------- content
def build(out_dir: Path, pages: dict[int, int] | None = None) -> Path:
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.5), Inches(11)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Inches(0.6))
    doc.styles["Normal"].font.name = FONT
    doc.styles["Normal"].font.size = Pt(10)
    doc.styles["Normal"].paragraph_format.space_after = Pt(3)
    for name, size in (("Heading 1", 16), ("Heading 2", 12), ("Heading 3", 12), ("Heading 4", 10.5), ("Heading 5", 10)):
        doc.styles[name].font.size = Pt(size)
        doc.styles[name].paragraph_format.space_before = Pt(6)
        doc.styles[name].paragraph_format.space_after = Pt(2)
    for level in range(1, 6):
        doc.styles[f"Heading {level}"].font.color.rgb = HEAD
        doc.styles[f"Heading {level}"].font.name = FONT
        fonts = doc.styles[f"Heading {level}"].element.rPr.rFonts
        for theme in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):  # theme fonts beat FONT
            fonts.attrib.pop(qn(theme), None)
    doc.styles["Heading 1"].font.size = Pt(20)

    # Footer on every page: "N of M - Self Study Guide: ...", then the fictional notice in small print.
    doc.styles["Footer"].font.size = Pt(8)  # the PAGE and NUMPAGES field results take the paragraph size
    running = sec.footer.paragraphs[0]
    field(running, "PAGE")
    running.add_run(" of ")
    field(running, "NUMPAGES")
    running.add_run(f" - {RUNNING}")
    for run in running.runs:
        run.font.size = Pt(8)
    for line in (DISCLAIMER, NOTICE):
        small = sec.footer.add_paragraph(line)
        small.alignment = WD_ALIGN_PARAGRAPH.CENTER
        small.runs[0].font.size = Pt(6.5)
        small.paragraph_format.space_after = Pt(0)

    with tempfile.TemporaryDirectory() as art:
        cover(doc, Path(art))
        table_of_contents(doc, pages)
        _body(doc)
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / FILENAME
        doc.save(out)  # pictures are embedded on save, so the temp art folder can go afterwards
    return out


def _body(doc) -> None:
    doc.add_heading("Course Director Notes", level=1)
    boxed(doc, "Welcome to Case 2", [
        "This week follows Jordan Rivera, a college athlete with a painful skin infection. "
        "The case connects innate immunity, the virulence of Staphylococcus aureus, and how "
        "we choose antibiotics when resistance is possible.",
        "Work through the case presentation first, then each discipline in order. "
        "Try every self-study question before you look at the answers.",
        "Small-group session: Thursday, 9:00-11:00 (fictional).",
        "This guide demonstrates AI-assisted study; follow your own school's AI policy for real course materials.",
    ])

    doc.add_heading("Case Presentation", level=1)
    para(doc, "Chief complaint", bold=True)
    para(doc, "“There’s a painful bump on my arm that keeps getting bigger.”")
    para(doc, "History of present illness", bold=True)
    para(doc, (
        "Jordan Rivera is a 19-year-old college wrestler who presents to student health with a "
        "4-day history of a red, swollen, painful lesion on the ulnar (medial) side of the right forearm. It began as what "
        "Jordan thought was a spider bite after practice. Over 48 hours it became firm and warm, "
        "and this morning it felt soft in the center. Jordan reports subjective fevers and "
        "fatigue. Two teammates had similar “boils” this season."
    ))
    para(doc, "Past history", bold=True)
    bullets(doc, [
        "No chronic illnesses; no prior hospitalizations",
        "Medications: none. Allergies: no known drug allergies",
        "Social: shares mats and towels at practice; no injection drug use",
    ])
    para(doc, "Vital signs", bold=True)
    grid(doc, ["Measure", "Value", "Reference"], [
        ["Temperature", "38.4 °C", "36.1-37.2 °C"],
        ["Heart rate", "104 /min", "60-100 /min"],
        ["Blood pressure", "118/72 mmHg", "<120/80 mmHg"],
        ["Respiratory rate", "16 /min", "12-20 /min"],
        ["SpO2", "99% room air", "≥95%"],
    ])
    para(doc, "Physical examination", bold=True)
    para(doc, (
        "A 4 cm erythematous, warm, tender nodule on the ulnar side of the right volar forearm with a fluctuant "
        "center and 2 cm of surrounding erythema. No lymphangitic streaking. Small, tender right "
        "epitrochlear node. The rest of the exam is normal."
    ))
    para(doc, "Laboratory results", bold=True)
    grid(doc, ["Test", "Result", "Flag", "Reference range", "Units"], [
        ["WBC", "14.2", "H", "4.0-11.0", "×10³/µL"],
        ["Neutrophils", "82", "H", "40-70", "%"],
        ["Band forms", "6", "H", "0-5", "%"],
        ["Lymphocytes", "11", "L", "20-40", "%"],
        ["Hemoglobin", "14.6", "", "13.5-17.5", "g/dL"],
        ["Platelets", "268", "", "150-400", "×10³/µL"],
        ["C-reactive protein", "48", "H", "<10", "mg/L"],
        ["Creatinine", "0.9", "", "0.7-1.3", "mg/dL"],
        ["Glucose (random)", "94", "", "70-125", "mg/dL"],
    ])
    para(doc, "Reference ranges are typical adult values (hemoglobin and creatinine shown for an adult male); they vary by laboratory.", italic=True, size=9)
    para(doc, "Procedure and microbiology", bold=True)
    para(doc, (
        "Bedside incision and drainage released 6 mL of thick yellow pus. Gram stain showed "
        "many neutrophils and gram-positive cocci in clusters. Culture grew large golden "
        "colonies with beta-hemolysis on blood agar."
    ))
    grid(doc, ["Test", "Result", "Interpretation", "", ""], [
        ["Catalase", "Positive", "Staphylococcus", "", ""],
        ["Coagulase", "Positive", "S. aureus", "", ""],
        ["Cefoxitin disk screen", "Resistant", "mecA / PBP2a likely (MRSA)", "", ""],
        ["Trimethoprim-sulfamethoxazole", "Susceptible", "", "", ""],
        ["Doxycycline", "Susceptible", "", "", ""],
        ["Clindamycin (D-test)", "Negative D-test; susceptible", "", "", ""],
    ])
    para(doc, (
        "Review the results above. Before reading on, write down: (1) the organism, "
        "(2) the host cells doing most of the work, and (3) what you would treat with and why."
    ), italic=True)

    # ---------------- Immunology
    doc.add_heading("Immunology", level=1)
    faculty(doc, "Discipline Director: Dr. Avery Lin (fictional)",
            "avery.lin@meridian.example", "Office hours: Tuesday 3:00-4:00 (fictional)")
    discipline_notes(doc, [
        "Focus on the first hours of infection: barriers, recognition, recruitment, and killing.",
        "Be able to trace a neutrophil from the bloodstream to the abscess.",
    ])
    topics(doc, "Immunology")
    objectives(doc, [
        "Describe how skin acts as a physical, chemical, and microbial barrier.",
        "Explain how pattern recognition receptors (TLR2) detect gram-positive bacteria.",
        "Outline the steps of neutrophil recruitment: rolling, activation, adhesion, transmigration.",
        "Explain how neutrophils kill bacteria with the respiratory burst.",
        "Predict how S. aureus virulence factors interfere with each step.",
    ])
    doc.add_heading("Neutrophil Recruitment and Killing (LO-1102, LO-1103)", level=3)
    para(doc, "Recognition", bold=True)
    bullets(doc, [
        "Bacterial lipoproteins are the main ligands for TLR2 (with TLR1 or TLR6); whether lipoteichoic acid also signals through TLR2 is debated [PMID:18406368].",
        "Tissue macrophages release IL-1, TNF-α, and IL-8 (CXCL8).",
    ])
    para(doc, "Recruitment (the leukocyte adhesion cascade)", bold=True)
    grid(doc, ["Step", "Endothelial molecule", "Neutrophil molecule", "", ""], [
        ["Rolling", "E-selectin, P-selectin", "Sialyl-Lewis X", "", ""],
        ["Activation", "Chemokines (IL-8)", "Chemokine receptors", "", ""],
        ["Tight adhesion", "ICAM-1", "Integrins (LFA-1, Mac-1)", "", ""],
        ["Transmigration", "PECAM-1 (CD31)", "PECAM-1 (CD31)", "", ""],
    ])
    para(doc, "Killing", bold=True)
    bullets(doc, [
        "Opsonized bacteria (IgG, C3b) are phagocytosed and the phagosome fuses with lysosomes.",
        "NADPH oxidase produces superoxide (the respiratory burst); myeloperoxidase makes hypochlorite.",
        "Pus is mostly dead neutrophils, bacteria, and tissue debris.",
    ])
    para(doc, "Clinical correlation", bold=True)
    bullets(doc, [
        "Chronic granulomatous disease (NADPH oxidase defect): recurrent S. aureus, Aspergillus, and other infections. Often taught as 'catalase-positive organisms', but in a mouse model catalase-negative S. aureus was equally virulent [PMID:11997027].",
        "Leukocyte adhesion deficiency type 1 (CD18 defect): little or no pus with marked neutrophilia; delayed umbilical cord separation is classic but not universal.",
    ])
    questions(doc, "Immunology", [
        ("A neutrophil rolling along the endothelium near Jordan’s abscess is slowed by which endothelial molecule?",
         ["ICAM-1", "E-selectin", "PECAM-1", "VCAM-1", "MHC class II"], "B",
         "Selectins mediate rolling; ICAM-1 binding to integrins mediates tight adhesion."),
        ("A child has recurrent S. aureus abscesses and absent superoxide production on a nitroblue tetrazolium (NBT) test. Which enzyme is defective?",
         ["Myeloperoxidase", "NADPH oxidase", "Superoxide dismutase", "Catalase", "Lysozyme"], "B",
         "No superoxide on NBT = absent respiratory burst = chronic granulomatous disease (NADPH oxidase defect). Myeloperoxidase deficiency spares superoxide production."),
    ])

    # ---------------- Microbiology
    doc.add_heading("Microbiology", level=1)
    faculty(doc, "Discipline Director: Dr. Morgan Patel (fictional)",
            "morgan.patel@meridian.example", "Office hours: Wednesday 1:00-2:00 (fictional)")
    discipline_notes(doc, [
        "Know how to identify S. aureus in the lab and link each virulence factor to a disease.",
        "Practice the sample deck: sample/curriculum/MICRO/Staphylococcus aureus (sample lecture).pptx",
    ])
    topics(doc, "Microbiology")
    objectives(doc, [
        "Identify S. aureus using Gram stain, catalase, and coagulase.",
        "Match surface factors (protein A, capsule, coagulase) to how they evade the host.",
        "Distinguish toxin-mediated diseases: TSS, scalded skin syndrome, food poisoning.",
        "Explain the mechanism of methicillin resistance (mecA, PBP2a).",
        "Contrast community-associated and hospital-associated MRSA.",
    ])
    doc.add_heading("Staphylococcus aureus (LO-1201, LO-1202, LO-1203)", level=3)
    grid(doc, ["Factor", "Type", "Action", "Disease link", ""], [
        ["Protein A", "Surface", "Binds Fc of IgG; blocks opsonization", "Immune evasion", ""],
        ["Coagulase", "Enzyme", "Activates prothrombin, forming fibrin", "Fibrin wall around the abscess", ""],
        ["Panton-Valentine leukocidin", "Toxin", "Pore-forming; kills leukocytes", "Associated with CA-MRSA skin infection and necrotizing pneumonia (causal role debated)", ""],
        ["TSST-1", "Superantigen", "Cross-links MHC II and TCR", "Toxic shock syndrome", ""],
        ["Exfoliative toxin", "Protease", "Cleaves desmoglein-1", "Scalded skin syndrome", ""],
        ["Enterotoxin", "Superantigen; heat-stable", "Preformed toxin in food", "Vomiting 30 min-8 h after eating (mean about 3 h)", ""],
    ])
    para(doc, "Methicillin resistance", bold=True)
    bullets(doc, [
        "mecA (on SCCmec) encodes PBP2a, a penicillin-binding protein with low affinity for beta-lactams.",
        "MRSA is resistant to nearly all beta-lactams (exception: anti-MRSA cephalosporins such as ceftaroline).",
        "Community-associated strains often carry PVL (its role in virulence is debated) and cause skin abscesses "
        "in healthy young people, especially with shared equipment and skin contact (athletes, dormitories) "
        "[PMID:17146447][PMID:22759601].",
    ])
    questions(doc, "Microbiology", [
        ("Which test distinguishes S. aureus from coagulase-negative staphylococci?",
         ["Catalase", "Coagulase", "Optochin", "Bacitracin", "Bile solubility"], "B",
         "All staphylococci are catalase positive; among human isolates, S. aureus is the coagulase-positive species."),
        ("Jordan’s isolate is cefoxitin-resistant. What is the molecular basis?",
         ["Beta-lactamase hyperproduction", "Altered PBP (PBP2a) encoded by mecA",
          "Efflux pump", "D-Ala-D-Lac cell wall precursor", "Decreased porin expression"], "B",
         "PBP2a binds beta-lactams poorly, so cell-wall synthesis continues."),
    ])

    # ---------------- Pharmacology
    doc.add_heading("Pharmacology", level=1)
    faculty(doc, "Discipline Director: Dr. Riley Okafor (fictional)",
            "riley.okafor@meridian.example", "Office hours: Friday 10:00-11:00 (fictional)")
    discipline_notes(doc, [
        "Know how each anti-staphylococcal drug works and when MRSA changes the choice.",
        "Incision and drainage is the main treatment for an abscess. Jordan has fever and tachycardia "
        "(two SIRS criteria), so an MRSA-active antibiotic is indicated [PMID:24973422]. In a large trial, "
        "TMP-SMX after drainage also raised the cure rate of uncomplicated abscesses "
        "(80.5% vs 73.6% with placebo, modified intention-to-treat) [PMID:26962903].",
    ])
    para(doc, "Summary of Important Symbols and Parameters", bold=True)
    grid(doc, ["Symbol", "Meaning", "Formula", "", ""], [
        ["Vd", "Volume of distribution", "Dose / C0", "", ""],
        ["CL", "Clearance", "Rate of elimination / plasma concentration", "", ""],
        ["t½", "Half-life", "0.693 × Vd / CL", "", ""],
        ["Css", "Steady-state concentration", "Dosing rate / CL", "", ""],
        ["LD", "Loading dose", "Css × Vd / F", "", ""],
    ])
    topics(doc, "Pharmacology")
    objectives(doc, [
        "Explain how beta-lactams and vancomycin inhibit cell-wall synthesis, and why each fails against resistant organisms.",
        "Choose an oral agent for uncomplicated CA-MRSA skin infection and justify it.",
        "Name key adverse effects of vancomycin, TMP-SMX, and doxycycline.",
        "Calculate a loading dose from Vd and a target concentration.",
    ])
    grid(doc, ["Drug", "Target", "Covers MRSA?", "Key adverse effects", ""], [
        ["Nafcillin / oxacillin", "PBPs (beta-lactamase resistant)", "No", "Neutropenia; interstitial nephritis (rare)", ""],
        ["Cefazolin", "PBPs", "No", "Hypersensitivity", ""],
        ["Vancomycin", "Binds D-Ala-D-Ala", "Yes", "Nephrotoxicity; infusion reaction (flushing)", ""],
        ["TMP-SMX", "DHFR + dihydropteroate synthase", "Yes", "Hyperkalemia, rash, bone marrow suppression", ""],
        ["Doxycycline", "30S ribosome", "Yes", "Photosensitivity, esophagitis; avoid in pregnancy", ""],
    ])
    questions(doc, "Pharmacology", [
        ("After drainage, Jordan is sent home on an oral antibiotic. Which is most appropriate given the susceptibilities?",
         ["Dicloxacillin", "Cephalexin", "Trimethoprim-sulfamethoxazole", "Amoxicillin", "Penicillin V"], "C",
         "The isolate is MRSA and TMP-SMX susceptible; beta-lactams do not cover MRSA."),
        ("A drug has Vd = 50 L and target concentration 20 mg/L with F = 1. What loading dose is needed?",
         ["100 mg", "250 mg", "1,000 mg", "2,500 mg", "5,000 mg"], "C",
         "LD = Css × Vd / F = 20 mg/L × 50 L = 1,000 mg."),
    ])

    doc.add_heading("Selected References", level=1)
    para(doc, "Every reference below was checked in PubMed. A citation shows a source exists; open it to see whether it supports the claim.", italic=True)
    bullets(doc, [
        "Stevens DL, et al. IDSA practice guidelines for skin and soft tissue infections, 2014 update. [PMID:24973422]",
        "Talan DA, et al. Trimethoprim-sulfamethoxazole versus placebo for uncomplicated skin abscess. N Engl J Med 2016. [PMID:26962903]",
        "Malachowa N, Kobayashi SD, DeLeo FR. Community-associated MRSA and athletes. Phys Sportsmed 2012. [PMID:22759601]",
        "Amagai M, et al. Toxin in bullous impetigo and staphylococcal scalded-skin syndrome targets desmoglein 1. Nat Med 2000. [PMID:11062541]",
        "Boyle-Vavra S, Daum RS. Community-acquired MRSA: the role of Panton-Valentine leukocidin. Lab Invest 2007. [PMID:17146447]",
        "Zähringer U, et al. TLR2 - promiscuous or specific? Immunobiology 2008. [PMID:18406368]",
        "Messina CG, et al. Catalase negative S. aureus retain virulence in a mouse model of CGD. FEBS Lett 2002. [PMID:11997027]",
    ])



def find_soffice() -> str | None:
    return shutil.which("soffice") or (SOFFICE_APP if Path(SOFFICE_APP).exists() else None)


def profile_uri(path) -> str:
    """file:// URI for a LibreOffice profile folder; as_uri() is also right for Windows drive paths."""
    return path.as_uri()


def to_pdf(docx: Path, out_dir: Path, soffice: str) -> Path:
    """Convert with LibreOffice into out_dir; the PDF is named like the .docx."""
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as profile:  # private profile: no clash with a running LibreOffice
        cmd = [soffice, f"-env:UserInstallation={profile_uri(Path(profile))}", "--headless", "--convert-to", "pdf",
               "--outdir", str(out_dir), str(docx)]
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    pdf = out_dir / PDF_FILENAME
    if done.returncode != 0 or not pdf.exists():
        raise SystemExit(f"soffice could not convert {docx.name} to PDF: {done.stderr.strip() or done.stdout.strip()}")
    return pdf


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path("sample/curriculum/GUIDE"))
    ap.add_argument("--pdf", action=argparse.BooleanOptionalAction, default=None,
                    help="write the demo input as a PDF (default; needs soffice). --no-pdf builds the .docx only")
    ap.add_argument("--docx", type=Path, metavar="DIR", help="also keep the editable .docx in DIR")
    args = ap.parse_args()
    soffice = find_soffice()
    if args.pdf is False:  # explicit --no-pdf: the .docx goes to --docx if given, else --out
        pages = None
        if soffice:  # fill the table of contents from a throwaway PDF pass when LibreOffice is available
            with tempfile.TemporaryDirectory() as tmp:
                pages = toc_pages(to_pdf(build(Path(tmp)), Path(tmp), soffice))
        print(f"Saved {build(args.docx or args.out, pages)}")
        return 0
    if not soffice:  # never fall back to a .docx beside the PDF fixture (the demo input is PDF only)
        raise SystemExit("PDF output needs LibreOffice: install it (brew install --cask libreoffice), "
                         "or pass --no-pdf --docx DIR to build only the editable .docx")
    with tempfile.TemporaryDirectory() as tmp:
        # Two passes: render once to find where each heading lands, then rebuild with those TOC page numbers.
        pages = toc_pages(to_pdf(build(Path(tmp)), Path(tmp), soffice))
        docx = build(Path(tmp), pages)
        pdf = to_pdf(docx, args.out, soffice)
        if toc_pages(pdf) != pages:
            raise SystemExit("table of contents page numbers moved between passes")
        print(f"Saved {pdf}")
        if args.docx:
            args.docx.mkdir(parents=True, exist_ok=True)
            print(f"Saved {shutil.copy(docx, args.docx / docx.name)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
