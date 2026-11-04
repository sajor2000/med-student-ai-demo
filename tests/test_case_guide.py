"""The fictional case guide is the demo input: a PDF only, footer on every page, page-anchored citations."""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GUIDE_DIR = ROOT / "sample" / "curriculum" / "GUIDE"
PDF = GUIDE_DIR / "BMS 501 Self-Study Guide 02 Jordan Rivera (fictional sample).pdf"


def test_demo_input_is_the_pdf_only():
    assert PDF.exists()
    assert sorted(p.suffix for p in GUIDE_DIR.iterdir()) == [".pdf"]
    assert list((ROOT / "docs" / "sample-case").glob("*.docx"))


def test_every_pdf_page_carries_the_fictional_footer_and_notice():
    fitz = pytest.importorskip("pymupdf")
    with fitz.open(str(PDF)) as doc:
        assert len(doc) >= 5
        for n, page in enumerate(doc, 1):
            text = re.sub(r"\s+", " ", page.get_text())
            assert "FICTIONAL SAMPLE" in text, n
            assert "AI supports learning, it does not replace it" in text, n


def test_notes_have_one_anchor_per_page_and_table_values_stay_with_their_labels():
    notes = (ROOT / "sample" / "notes" / "GUIDE" / (PDF.stem + ".md")).read_text(encoding="utf-8")
    assert len(re.findall(r"^## \[S\d+\]", notes, re.M)) >= 5
    assert "- Result: 14.2" in notes and "- Flag: H" in notes  # labs read as labelled values
    assert "- Result: Positive" in notes and "- Target: Binds D-Ala-D-Ala" in notes


def test_case2_guide_citations_use_pdf_page_anchors():
    for name in ("study-guide.md", "flashcards.csv"):
        text = (ROOT / "examples" / "case2" / name).read_text(encoding="utf-8")
        cites = re.findall(r"\[\[GUIDE/[^\]]*#([A-Z]\d+)\]\]", text)
        assert cites and all(c.startswith("S") for c in cites), (name, cites)


def test_no_pdf_flag_writes_docx_without_soffice(tmp_path):
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "make_case_guide.py"), "--no-pdf", "--out", str(tmp_path)],
                         capture_output=True, text=True)
    if out.returncode and "docx" in out.stderr:
        pytest.skip("python-docx is not installed in this interpreter")
    assert out.returncode == 0, out.stderr
    assert [p.suffix for p in tmp_path.iterdir()] == [".docx"]


@pytest.mark.skipif(not shutil.which("soffice"), reason="LibreOffice is not installed")
def test_pdf_flag_converts_with_soffice(tmp_path):
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "make_case_guide.py"), "--pdf", "--out", str(tmp_path)],
                         capture_output=True, text=True)
    if out.returncode and "docx" in out.stderr:
        pytest.skip("python-docx is not installed in this interpreter")
    assert out.returncode == 0, out.stderr
    assert [p.suffix for p in tmp_path.iterdir()] == [".pdf"]
