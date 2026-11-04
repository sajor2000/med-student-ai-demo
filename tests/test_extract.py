"""extract.py: PDFs, plain text, and lecture transcripts become citable Markdown."""
from __future__ import annotations

import json
import re

import pytest

fitz = pytest.importorskip("pymupdf")  # pymupdf builds the PDF fixtures

ANCHOR = re.compile(r"^(?:## )?\[([SPT]\d+)\]", re.M)


def make_pdf(path, pages):
    """pages: list of text (str) or None for an image-only page."""
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        if text is None:
            pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 40, 40), False)
            pix.clear_with(200)
            page.insert_image(fitz.Rect(50, 50, 200, 200), pixmap=pix)
        else:
            page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


def run(extract, src, out):
    assert extract.main([str(src), "--out", str(out)]) == 0
    return json.loads((out / "manifest.json").read_text())


def test_pdf_one_slide_anchor_per_page(extract, tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    make_pdf(src / "Renal clearance.pdf", ["Clearance equals U times V over P", "GFR is about 125 mL/min"])
    m = run(extract, src, tmp_path / "out")
    md = (tmp_path / "out" / "Renal clearance.md").read_text()
    assert re.findall(r"^## \[(S\d+)\]", md, re.M) == ["S1", "S2"]
    assert "Clearance equals U times V over P" in md
    assert m["files"][0]["kind"] == "slides"
    assert m["files"][0]["units"] == 2


def test_pdf_image_only_page_is_flagged_and_counted(extract, tmp_path, capsys):
    src = tmp_path / "in"
    src.mkdir()
    make_pdf(src / "scan.pdf", ["Text page", None])
    m = run(extract, src, tmp_path / "out")
    md = (tmp_path / "out" / "scan.md").read_text()
    assert "[no text on this page — scanned slide]" in md
    assert m["files"][0]["image_only_pages"] == 1
    assert "1 image-only" in capsys.readouterr().out


def test_txt_and_md_get_paragraph_anchors(extract, tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    (src / "notes.txt").write_text("First paragraph.\n\nSecond\nwrapped paragraph.\n\n\nThird.")
    (src / "guide.md").write_text("# Guide\n\nBody text here.")
    m = run(extract, src, tmp_path / "out")
    txt = (tmp_path / "out" / "notes.md").read_text()
    assert re.findall(r"^\[(P\d+)\]", txt, re.M) == ["P1", "P2", "P3"]
    assert "Second wrapped paragraph." in txt
    assert {f["kind"] for f in m["files"]} == {"text"}
    assert (tmp_path / "out" / "guide.md").exists()


def test_vtt_chunks_by_minute_with_timestamp(extract, tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    (src / "lec.vtt").write_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nWelcome to renal physiology.\n\n"
        "00:00:30.000 --> 00:00:40.000\n<v Dr Lee>Nephron basics.</v>\n\n"
        "00:01:10.000 --> 00:01:20.000\nFiltration next.\n"
    )
    (src / "talk.srt").write_text(
        "1\n00:00:02,000 --> 00:00:04,000\nHello class.\n\n2\n00:02:05,000 --> 00:02:09,000\nLater point.\n"
    )
    m = run(extract, src, tmp_path / "out")
    vtt = (tmp_path / "out" / "lec.md").read_text()
    assert re.findall(r"^\[(P\d+)\] \[(\d\d:\d\d)\]", vtt, re.M) == [("P1", "00:01"), ("P2", "01:10")]
    assert "Welcome to renal physiology. Nephron basics." in vtt
    assert "<v" not in vtt
    srt = (tmp_path / "out" / "talk.md").read_text()
    assert re.findall(r"^\[(P\d+)\] \[(\d\d:\d\d)\]", srt, re.M) == [("P1", "00:02"), ("P2", "02:05")]
    assert {f["kind"] for f in m["files"]} == {"transcript"}


def test_anchors_match_check_py_regex(extract, check, tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    make_pdf(src / "d.pdf", ["x"])
    run(extract, src, tmp_path / "out")
    md = (tmp_path / "out" / "d.md").read_text()
    assert check.COURSE.search("[[d#S1]]")
    assert "[S1]" in md


def test_unsupported_file_is_skipped(extract, tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    (src / "clip.mp4").write_bytes(b"x")
    m = run(extract, src, tmp_path / "out")
    assert m["files"] == [] and m["skipped"] == ["clip.mp4"]


def test_prints_policy_reminder(extract, tmp_path, capsys):
    src = tmp_path / "in"
    src.mkdir()
    (src / "a.txt").write_text("x")
    run(extract, src, tmp_path / "out")
    assert "Follow your school's AI policy" in capsys.readouterr().out


def test_same_stem_files_do_not_overwrite(extract, tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    make_pdf(src / "Renal.pdf", ["Slide text"])
    (src / "Renal.vtt").write_text("WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nSpoken text.\n")
    (src / "Renal.txt").write_text("Typed text.")
    m = run(extract, src, tmp_path / "out")
    notes = {f["source"]: f["notes"] for f in m["files"]}
    assert len(set(notes.values())) == 3
    assert "Slide text" in (tmp_path / "out" / "Renal.md").read_text()
    assert "Spoken text." in (tmp_path / "out" / "Renal (vtt).md").read_text()
    assert "Typed text." in (tmp_path / "out" / "Renal (txt).md").read_text()


def test_literal_comparisons_survive_but_subtitle_tags_go(extract, tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    (src / "a.vtt").write_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:05.000\n<v Dr Lee><i>GFR < 60 indicates CKD; GFR > 90 is normal.</i></v>\n\n"
        "00:00:06.000 --> 00:00:08.000\n<c.yellow>Hello</c> <00:00:07.000>there <b>bold</b>\n"
    )
    (src / "b.srt").write_text("1\n00:00:01,000 --> 00:00:03,000\n<font color=\"red\">Na < 135 is low</font>\n")
    run(extract, src, tmp_path / "out")
    a = (tmp_path / "out" / "a.md").read_text()
    assert "GFR < 60 indicates CKD; GFR > 90 is normal." in a
    assert "Hello there bold" in a
    assert "<" not in a.split("Source:")[1].replace("< 60", "").replace("<br", "")
    assert "Na < 135 is low" in (tmp_path / "out" / "b.md").read_text()


def test_utf16_bom_text_and_transcript_are_decoded(extract, tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    (src / "notes.txt").write_bytes("First paragraph.\n\nSecond.".encode("utf-16"))
    (src / "talk.vtt").write_bytes(
        "WEBVTT\n\n00:00:01.000 --> 00:00:04.000\nHello class.\n".encode("utf-16")
    )
    (src / "bom8.txt").write_bytes(b"\xef\xbb\xbfAlpha.\n\nBeta.")
    run(extract, src, tmp_path / "out")
    txt = (tmp_path / "out" / "notes.md").read_text()
    assert "\x00" not in txt and "�" not in txt
    assert "[P2] Second." in txt
    assert "Hello class." in (tmp_path / "out" / "talk.md").read_text()
    assert "﻿" not in (tmp_path / "out" / "bom8.md").read_text()


def test_undecodable_file_fails_loudly(extract, tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    (src / "bad.txt").write_bytes(b"ok \xff\xfe\xfa bad bytes \x80")
    m = run(extract, src, tmp_path / "out")
    assert m["files"] == [] and "UnicodeDecodeError" in m["skipped"][0]


def test_ingest_skill_links_resolve():
    from pathlib import Path

    skill = Path(__file__).resolve().parent.parent / ".claude/skills/ingest/SKILL.md"
    for target in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", skill.read_text()):
        if "://" not in target:
            assert (skill.parent / target).resolve().exists(), target


def test_fallback_names_never_collide(extract, tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    make_pdf(src / "report.pdf", ["slide text"])
    (src / "report.md").write_text("Markdown body.")
    (src / "report (md).txt").write_text("Text body.")
    m = run(extract, src, tmp_path / "out")
    notes = [f["notes"] for f in m["files"]]
    assert len(notes) == 3 and len(set(notes)) == 3
    for f in m["files"]:
        assert (tmp_path / f["notes"] if not f["notes"].startswith("/") else __import__("pathlib").Path(f["notes"])).exists()


def test_output_inside_input_is_rejected_and_inputs_survive(extract, tmp_path, capsys):
    src = tmp_path / "in"
    src.mkdir()
    (src / "guide.md").write_text("Original body.")
    assert extract.main([str(src), "--out", str(src)]) == 2
    assert (src / "guide.md").read_text() == "Original body."
    assert extract.main([str(src), "--out", str(src / "sub")]) == 2


def test_vtt_note_style_region_blocks_are_not_transcript(extract, tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    (src / "t.vtt").write_text(
        "WEBVTT\n\nNOTE\n00:00:05.000 --> 00:00:06.000 leaked note\n\n"
        "STYLE\n::cue { color: red }\n00:00:07.000 --> 00:00:08.000\nleaked style\n\n"
        "REGION\nid:r1\n\n"
        "00:00:01.000 --> 00:00:04.000\nReal cue.\n"
    )
    run(extract, src, tmp_path / "out")
    txt = (tmp_path / "out" / "t.md").read_text()
    assert "Real cue." in txt and "leaked" not in txt


def test_output_check_and_collisions_ignore_case(extract, tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    (src / "guide.md").write_text("Original body.")
    shouty = tmp_path / "IN"  # same folder on a case-insensitive filesystem
    assert extract.main([str(src), "--out", str(shouty)]) == 2
    assert extract.main([str(src), "--out", str(shouty / "sub")]) == 2
    assert (src / "guide.md").read_text() == "Original body."

    src2 = tmp_path / "in2"
    src2.mkdir()
    (src2 / "Renal.txt").write_text("Upper.")
    (src2 / "renal.md").write_text("Lower.")
    m = run(extract, src2, tmp_path / "out2")
    notes = [f["notes"].casefold() for f in m["files"]]
    assert len(notes) == 2 and len(set(notes)) == 2


def make_banner_pdf(path, bodies, banner="FICTIONAL SAMPLE banner for every page", footer="Page footer notice"):
    """Every page opens with the same running banner and closes with the same footer."""
    doc = fitz.open()
    for body in bodies:
        page = doc.new_page()
        page.insert_text((72, 60), banner)
        page.insert_text((72, 120), body)
        page.insert_text((72, 780), footer)
    doc.save(str(path))
    doc.close()


def test_pdf_heading_skips_running_banner(extract, tmp_path):
    """A banner repeated on every page must not become every page's identical heading."""
    src = tmp_path / "in"
    src.mkdir()
    make_banner_pdf(src / "Guide.pdf", ["Course Director Notes", "Case Presentation", "Immunology"])
    run(extract, src, tmp_path / "out")
    md = (tmp_path / "out" / "Guide.md").read_text()
    assert re.findall(r"^## \[S\d+\] (.*)$", md, re.M) == ["Course Director Notes", "Case Presentation", "Immunology"]
    # nothing is dropped: the banner text is still in the page body
    assert md.count("FICTIONAL SAMPLE banner for every page") == 3


def test_pdf_heading_unchanged_for_short_documents(extract, tmp_path):
    """Two pages cannot establish a running header, so the first line stays the heading."""
    src = tmp_path / "in"
    src.mkdir()
    make_banner_pdf(src / "Two.pdf", ["Alpha", "Beta"])
    run(extract, src, tmp_path / "out")
    md = (tmp_path / "out" / "Two.md").read_text()
    assert re.findall(r"^## \[S\d+\] (.*)$", md, re.M) == ["FICTIONAL SAMPLE banner for every page"] * 2


def test_pdf_leading_bullet_glyphs_are_dropped(extract):
    """Word bullets (U+F0B7, Symbol font) extract as lone private-use characters, not text."""
    raw = "\uf0b7\n\uf0b7 Bullet text kept\n  \uf0a7  \nReal fact"
    assert extract.pdf_page_lines(raw) == ["Bullet text kept", "Real fact"]


def test_pdf_symbol_font_letters_are_kept(extract):
    """Symbol-font Greek letters also live in the private-use area: only bullet markers may go."""
    raw = "\uf062-lactams bind PBP\nthe \uf061 chain and \uf0b7 inline"
    assert extract.pdf_page_lines(raw) == ["\uf062-lactams bind PBP", "the \uf061 chain and \uf0b7 inline"]


def test_running_lines_only_come_from_page_edges(extract):
    """A line repeated mid-page (a table heading) is content; only top/bottom lines can be a banner."""
    body = ["a", "b", "c", "d", "e", "Table of results", "f", "g", "h", "i", "j"]
    pages = [[f"p{n}-{x}" if x != "Table of results" else x for x in body] for n in range(3)]
    banner = [["BANNER"] + p + ["FOOTER"] for p in pages]
    assert extract.running_lines(pages) == set()
    assert extract.running_lines(banner) == {"BANNER", "FOOTER"}


def test_numbered_page_footers_count_as_running_lines(extract):
    """'N of M - Guide' differs on every page only by its page number, so it is still a running footer."""
    body = [[f"p{n}-a", f"p{n}-b", f"p{n}-c", f"p{n}-d", f"p{n}-e"] for n in range(4)]
    pages = [p + [f"{n + 1} of 4 - Self Study Guide: Case 2"] for n, p in enumerate(body)]
    assert extract.running_lines(pages) == {f"{n} of 4 - Self Study Guide: Case 2" for n in range(1, 5)}
    # Content lines that merely contain digits ("p0-a", "p1-a") are not page numbers and stay content.
    assert not any(line.startswith("p") for line in extract.running_lines(pages))
