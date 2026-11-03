from __future__ import annotations

import csv
import json
import re
import urllib.parse
from pathlib import Path

from conftest import run_main

S3 = "[[MICRO/Staph deck (sample)#S3]]"
S2 = "[[MICRO/Staph deck (sample)#S2]]"
P3 = "[[PHARM/Guide#P3]]"
T1 = "[[PHARM/Guide#T1]]"


def write_deck(folder: Path, rows: list[tuple[str, str, str]]) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "flashcards.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["front", "back", "sources", "tags"])
        for front, back, src in rows:
            w.writerow([front, back, src, "case;micro;topic"])
    return path


def page_cards(html_path: Path) -> list[dict]:
    m = re.search(r"const C=(\[.*?\]);let i", html_path.read_text(encoding="utf-8"), re.S)
    return json.loads(m.group(1))


def hrefs(html: str) -> list[str]:
    html = html.replace('\\"', '"')  # card data is embedded as JSON, which escapes quotes
    return re.findall(r'href="([^"]+_sources/[^"]+)"', html)


MIXED = [
    ("Which enzyme separates staph from strep?", "Catalase", S2),
    ("Exfoliative toxin cleaves {{c1::desmoglein-1::protein}}.", "Scalded skin", S3),
]


def test_mixed_deck_writes_basic_and_cloze_files(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    run_main(export, [str(deck)], monkeypatch)
    basic = (tmp_path / "out/flashcards.anki.txt").read_text(encoding="utf-8")
    cloze = (tmp_path / "out/flashcards.cloze.anki.txt").read_text(encoding="utf-8")
    assert "#notetype:Basic" in basic and "#notetype:Cloze" in cloze
    assert "Which enzyme" in basic and "desmoglein" not in basic
    assert "{{c1::desmoglein-1::protein}}" in cloze and "Which enzyme" not in cloze


def test_basic_only_deck_removes_stale_cloze_file(export, tmp_path, monkeypatch):
    out = tmp_path / "out"
    deck = write_deck(out, MIXED[:1])
    (out / "flashcards.cloze.anki.txt").write_text("stale", encoding="utf-8")
    run_main(export, [str(deck)], monkeypatch)
    assert not (out / "flashcards.cloze.anki.txt").exists()


def test_stable_ids_repeat_across_runs(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    run_main(export, [str(deck)], monkeypatch)
    first = (tmp_path / "out/flashcards.cloze.anki.txt").read_text(encoding="utf-8")
    run_main(export, [str(deck)], monkeypatch)
    assert (tmp_path / "out/flashcards.cloze.anki.txt").read_text(encoding="utf-8") == first


def test_duplicate_fronts_warn(export, tmp_path, monkeypatch, capsys):
    deck = write_deck(tmp_path / "out", [MIXED[0], (MIXED[0][0], "Other", S2)])
    run_main(export, [str(deck)], monkeypatch)
    assert "duplicate" in capsys.readouterr().out.lower()


def test_no_notes_keeps_plain_labels(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    run_main(export, [str(deck)], monkeypatch)
    assert not (tmp_path / "out/flashcards_sources").exists()
    assert hrefs((tmp_path / "out/flashcards.html").read_text(encoding="utf-8")) == []


def test_links_resolve_to_anchors_for_slide_paragraph_table(export, notes, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", [("Q1?", "A", S3), ("Q2?", "A", P3), ("Q3?", "A", T1)])
    run_main(export, [str(deck), "--notes", str(notes)], monkeypatch)
    page = tmp_path / "out/flashcards.html"
    links = hrefs(page.read_text(encoding="utf-8"))
    assert len(links) == 3
    expected = {"S3": "desmoglein-1", "P3": "PBP2a", "T1": "Vancomycin"}
    for href in links:
        path, frag = urllib.parse.unquote(href).split("#")
        target = page.parent / path
        assert target.exists(), target
        body = target.read_text(encoding="utf-8")
        m = re.search(rf'id="{frag}"[^>]*>(.*?)(?=<[^/]*id="|\Z)', body, re.S)
        assert m, f"no element with id {frag}"
        assert expected[frag] in m.group(1)
        assert "do not share" in body.lower()


def test_consecutive_paragraph_markers_get_separate_ids(export, notes, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", [("Q?", "A", "[[PHARM/Guide#P2]] [[PHARM/Guide#P3]]")])
    run_main(export, [str(deck), "--notes", str(notes)], monkeypatch)
    body = next((tmp_path / "out/flashcards_sources").rglob("Guide.html")).read_text(encoding="utf-8")
    assert 'id="P2"' in body and 'id="P3"' in body
    assert body.index('id="P2"') < body.index("Beta-lactams") < body.index('id="P3"')


def test_paths_with_spaces_are_percent_encoded(export, notes, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", [("Q?", "A", S3)])
    run_main(export, [str(deck), "--notes", str(notes)], monkeypatch)
    (href,) = hrefs((tmp_path / "out/flashcards.html").read_text(encoding="utf-8"))
    assert " " not in href and "%20" in href


def test_bad_citations_stay_plain_and_warn(export, notes, tmp_path, monkeypatch, capsys):
    deck = write_deck(
        tmp_path / "out",
        [("Q1?", "A", "[[MICRO/Missing#S1]]"), ("Q2?", "A", "[[../../etc/passwd#S1]]"), ("Q3?", "A", "[[MICRO/Staph deck (sample)#S9]]")],
    )
    run_main(export, [str(deck), "--notes", str(notes)], monkeypatch)
    out = capsys.readouterr().out.lower()
    assert out.count("warning") >= 3
    assert hrefs((tmp_path / "out/flashcards.html").read_text(encoding="utf-8")) == []
    written = [p for p in tmp_path.rglob("*.html") if "flashcards_sources" in str(p)]
    assert all(str(tmp_path / "out/flashcards_sources") in str(p) for p in written)


def test_guide_citations_are_linked(export, notes, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", [("Q?", "A", S2)])
    guide = tmp_path / "out/guide.md"
    guide.write_text(f"# Guide\n\n- Desmoglein-1 is cleaved. {S3}\n", encoding="utf-8")
    run_main(export, [str(deck), "--guide", str(guide), "--notes", str(notes)], monkeypatch)
    html = (tmp_path / "out/flashcards.html").read_text(encoding="utf-8")
    assert any(h.endswith("#S3") for h in hrefs(html))


def test_anki_files_never_contain_source_links(export, notes, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    run_main(export, [str(deck), "--notes", str(notes)], monkeypatch)
    for name in ("flashcards.anki.txt", "flashcards.cloze.anki.txt"):
        assert "_sources" not in (tmp_path / "out" / name).read_text(encoding="utf-8")


def test_page_marks_cloze_cards(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    run_main(export, [str(deck)], monkeypatch)
    cards = page_cards(tmp_path / "out/flashcards.html")
    assert [c.get("cloze") for c in cards] == [False, True]
    cloze = cards[1]
    assert "desmoglein-1" not in cloze["front"] and "[protein]" in cloze["front"]
    assert "<mark>desmoglein-1</mark>" in cloze["reveal"]


def test_hintless_cloze_shows_ellipsis(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", [("Toxin cleaves {{c1::desmoglein-1}}.", "", S3)])
    run_main(export, [str(deck)], monkeypatch)
    (card,) = page_cards(tmp_path / "out/flashcards.html")
    assert "desmoglein-1" not in card["front"] and "[\u2026]" in card["front"]


def test_traversal_to_real_file_is_blocked(export, notes, tmp_path, monkeypatch, capsys):
    (tmp_path / "secret.md").write_text("## [S1] secret\n", encoding="utf-8")
    deck = write_deck(tmp_path / "out", [("Q?", "A", "[[../secret#S1]]")])
    run_main(export, [str(deck), "--notes", str(notes)], monkeypatch)
    assert "outside" in capsys.readouterr().out
    assert not list(tmp_path.rglob("secret.html"))
    assert hrefs((tmp_path / "out/flashcards.html").read_text(encoding="utf-8")) == []


def test_refuses_to_delete_unowned_sources_folder(export, notes, tmp_path, monkeypatch):
    out = tmp_path / "out"
    (out / "flashcards_sources").mkdir(parents=True)
    (out / "flashcards_sources" / "mine.txt").write_text("keep me", encoding="utf-8")
    deck = write_deck(out, [("Q?", "A", S3)])
    import pytest
    with pytest.raises(SystemExit):
        run_main(export, [str(deck), "--notes", str(notes)], monkeypatch)
    assert (out / "flashcards_sources" / "mine.txt").exists()


def test_rerun_replaces_own_sources_folder(export, notes, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", [("Q?", "A", S3)])
    run_main(export, [str(deck), "--notes", str(notes)], monkeypatch)
    run_main(export, [str(deck), "--notes", str(notes)], monkeypatch)
    assert (tmp_path / "out/flashcards_sources/.generated-by-export").exists()


def test_raw_html_in_notes_is_escaped_on_source_pages(export, notes, tmp_path, monkeypatch):
    f = notes / "MICRO" / "Staph deck (sample).md"
    f.write_text(f.read_text(encoding="utf-8") + "\nplain <script>alert(1)</script> and <img src=x onerror=alert(2)>\n", encoding="utf-8")
    deck = write_deck(tmp_path / "out", [("Q?", "A", S3)])
    run_main(export, [str(deck), "--notes", str(notes)], monkeypatch)
    body = next((tmp_path / "out/flashcards_sources").rglob("*.html")).read_text(encoding="utf-8")
    assert "<script>alert(1)" not in body and "<img src=x" not in body
    assert "&lt;script&gt;" in body or "&lt;script>" in body


def test_apostrophes_not_double_escaped(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", [("Q?", "Graves' disease", S2)])
    run_main(export, [str(deck)], monkeypatch)
    html_text = (tmp_path / "out/flashcards.html").read_text(encoding="utf-8")
    anki = (tmp_path / "out/flashcards.anki.txt").read_text(encoding="utf-8")
    assert "&#x27;" not in html_text and "&amp;#x27;" not in html_text
    assert "Graves' disease" in anki


def test_tabs_and_newlines_stay_inside_one_anki_record(export, tmp_path, monkeypatch):
    import io as _io
    deck = write_deck(tmp_path / "out", [("Line one\nline two?", "has\ta tab", S2), ("Second card?", "B", S2)])
    run_main(export, [str(deck)], monkeypatch)
    text = (tmp_path / "out/flashcards.anki.txt").read_text(encoding="utf-8")
    body = "".join(l for l in text.splitlines(keepends=True) if not l.startswith("#"))
    rows = [r for r in csv.reader(_io.StringIO(body), delimiter="\t") if r]
    assert len(rows) == 2 and all(len(r) == 4 for r in rows)
    assert rows[0][1] == "Line one<br>line two?"


def test_multiline_cloze_front_uses_html_breaks(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", [("{{c1::first\nsecond}} line", "", S3)])
    run_main(export, [str(deck)], monkeypatch)
    text = (tmp_path / "out/flashcards.cloze.anki.txt").read_text(encoding="utf-8")
    assert "{{c1::first<br>second}}" in text


def test_citation_split_by_newline_still_links_in_anki(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", [("Q?", "See [PMID:\n12345678] for details", S2)])
    run_main(export, [str(deck)], monkeypatch)
    text = (tmp_path / "out/flashcards.anki.txt").read_text(encoding="utf-8")
    assert "pubmed.ncbi.nlm.nih.gov/12345678/" in text


def test_crlf_inside_citation_still_links(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", [("Q?", "See [PMID:\r\n12345678] here", S2)])
    run_main(export, [str(deck)], monkeypatch)
    assert "pubmed.ncbi.nlm.nih.gov/12345678/" in (tmp_path / "out/flashcards.anki.txt").read_text(encoding="utf-8")
