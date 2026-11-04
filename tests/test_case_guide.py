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


def test_docx_only_build_never_prints_placeholder_page_numbers(tmp_path):
    docx = pytest.importorskip("docx")
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "make_case_guide.py"), "--no-pdf", "--out", str(tmp_path)],
                         capture_output=True, text=True)
    if out.returncode and ("docx" in out.stderr or "PIL" in out.stderr or "pymupdf" in out.stderr):
        pytest.skip("generator dependencies are not installed in this interpreter")
    assert out.returncode == 0, out.stderr
    toc = [p.text for p in docx.Document(str(next(tmp_path.glob("*.docx")))).paragraphs if "\t" in p.text]
    assert toc and not any(t.endswith("\t00") for t in toc)
    if shutil.which("soffice"):  # with LibreOffice, every entry gets a real page number
        assert all(t.rsplit("\t", 1)[1].isdigit() for t in toc)


@pytest.mark.skipif(not shutil.which("soffice"), reason="LibreOffice is not installed")
def test_pdf_flag_converts_with_soffice(tmp_path):
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "make_case_guide.py"), "--pdf", "--out", str(tmp_path)],
                         capture_output=True, text=True)
    if out.returncode and "docx" in out.stderr:
        pytest.skip("python-docx is not installed in this interpreter")
    assert out.returncode == 0, out.stderr
    assert [p.suffix for p in tmp_path.iterdir()] == [".pdf"]


def test_no_table_word_is_split_mid_word_in_the_notes():
    notes = (ROOT / "sample" / "notes" / "GUIDE" / (PDF.stem + ".md")).read_text(encoding="utf-8")
    lines = notes.splitlines()
    assert any(ln.endswith("Transmigration") or "Transmigration" in ln for ln in lines)
    assert not any(ln.strip("- ") in ("n", "ion", "tion") for ln in lines)
    # every long word in the source script's table cells survives extraction intact
    import importlib.util
    spec = importlib.util.spec_from_file_location("mcg", ROOT / "scripts" / "make_case_guide.py")
    text = (ROOT / "scripts" / "make_case_guide.py").read_text(encoding="utf-8")
    words = {w for row in re.findall(r'^\s+\["([^\]]*)\]', text, re.M) for w in re.findall(r"[A-Za-z][A-Za-z-]{11,}", row)}
    flat = re.sub(r"\s+", " ", notes)
    assert words and all(w in flat for w in words), sorted(w for w in words if w not in flat)


def test_default_run_without_soffice_never_writes_a_docx_into_the_input_folder(tmp_path, monkeypatch):
    import importlib.util
    pytest.importorskip("docx")
    spec = importlib.util.spec_from_file_location("mcg2", ROOT / "scripts" / "make_case_guide.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "find_soffice", lambda: None)
    monkeypatch.setattr(sys, "argv", ["make_case_guide.py", "--out", str(tmp_path)])
    with pytest.raises(SystemExit) as e:
        mod.main()
    assert "LibreOffice" in str(e.value) and not list(tmp_path.iterdir())


def test_libreoffice_profile_uri_is_valid_on_windows_paths():
    import importlib.util
    from pathlib import PureWindowsPath
    pytest.importorskip("docx")
    spec = importlib.util.spec_from_file_location("mcg3", ROOT / "scripts" / "make_case_guide.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.profile_uri(PureWindowsPath(r"C:\Users\me\AppData\Local\Temp\lo profile")) == \
        "file:///C:/Users/me/AppData/Local/Temp/lo%20profile"


def test_to_pdf_passes_the_profile_as_a_file_uri(tmp_path, monkeypatch):
    import importlib.util
    pytest.importorskip("docx")
    spec = importlib.util.spec_from_file_location("mcg4", ROOT / "scripts" / "make_case_guide.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        (tmp_path / mod.PDF_FILENAME).write_bytes(b"%PDF")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    mod.to_pdf(tmp_path / "x.docx", tmp_path, "soffice")
    env = [a for a in seen["cmd"] if a.startswith("-env:UserInstallation=")][0]
    assert env.startswith("-env:UserInstallation=file:///")
