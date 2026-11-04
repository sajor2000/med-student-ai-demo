from __future__ import annotations

import csv
import json
import re
import urllib.parse

import pytest
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


# --- diagrams and memory aids ---------------------------------------------

LECT = "MICRO/Staph deck (sample)"


def make_png(path: Path, color: str = "white") -> None:
    from PIL import Image

    Image.new("RGB", (8, 8), color).save(path, "PNG")


def make_diagrams(folder: Path, labels: list[tuple[str, str]], slug: str = "staph-toxins", title: str = "S. aureus toxins") -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    make_png(folder / f"{slug}.card.png")
    spec = {
        "case": "demo", "slug": slug, "title": title, "image": f"{slug}.card.png",
        "labels": [{"id": f"n{i}", "kind": "node", "label": lab, "cite": cite} for i, (lab, cite) in enumerate(labels, 1)],
    }
    (folder / f"{slug}.occlusion.json").write_text(json.dumps(spec), encoding="utf-8")
    return folder


def test_no_flags_page_is_unchanged(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    run_main(export, [str(deck)], monkeypatch)
    page = (tmp_path / "out/flashcards.html").read_text(encoding="utf-8")
    assert "Diagrams" not in page and "Memory aids" not in page and "<img" not in page
    assert page.count("<button") == 5  # 2 tabs + prev/flip/next, no extra tabs
    assert not (tmp_path / "out/flashcards_media").exists()


def test_diagrams_tab_shows_png_and_escaped_labels(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    diagrams = make_diagrams(tmp_path / "diagrams", [("Exfoliative toxin", S3), ("A & B <i>", S3)])
    run_main(export, [str(deck), "--diagrams", str(diagrams)], monkeypatch)
    page = (tmp_path / "out/flashcards.html").read_text(encoding="utf-8")
    assert 'id="td"' in page and "Diagrams" in page
    (src,) = re.findall(r'<img class="diagram" src="([^"]+)"', page)
    assert (tmp_path / "out" / urllib.parse.unquote(src)).read_bytes()[:4] == b"\x89PNG"
    assert "S. aureus toxins" in page
    assert "Exfoliative toxin" in page and "A &amp; B &lt;i&gt;" in page
    assert "<svg" not in page.lower() and ".html" not in src


def test_diagram_label_markup_renders_as_text(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    evil = "<img src=x onerror=alert(1)>"
    diagrams = make_diagrams(tmp_path / "diagrams", [(evil, S3)], title="<script>alert(2)</script>")
    run_main(export, [str(deck), "--diagrams", str(diagrams)], monkeypatch)
    page = (tmp_path / "out/flashcards.html").read_text(encoding="utf-8")
    assert evil not in page and "<script>alert(2)" not in page
    assert "&lt;img src=x onerror=alert(1)&gt;" in page


def test_diagram_citations_link_to_sources_with_notes(export, notes, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    diagrams = make_diagrams(tmp_path / "diagrams", [("Exfoliative toxin", S3)])
    run_main(export, [str(deck), "--notes", str(notes), "--diagrams", str(diagrams)], monkeypatch)
    page = (tmp_path / "out/flashcards.html").read_text(encoding="utf-8")
    section = page.split('id="diagrams"')[1].split("</section>")[0]
    (href,) = re.findall(r'href="([^"]+_sources/[^"]+)"', section)
    path, frag = urllib.parse.unquote(href).split("#")
    assert frag == "S3" and (tmp_path / "out" / path).exists()


def test_diagram_citations_stay_plain_without_notes(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    diagrams = make_diagrams(tmp_path / "diagrams", [("Exfoliative toxin", S3)])
    run_main(export, [str(deck), "--diagrams", str(diagrams)], monkeypatch)
    page = (tmp_path / "out/flashcards.html").read_text(encoding="utf-8")
    assert hrefs(page) == [] and "Staph deck (sample)" in page


def test_art_tab_lists_images_under_not_a_reference_heading(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    art = tmp_path / "art"
    art.mkdir()
    make_png(art / "scalded-skin.png")
    make_png(art / "catalase.png")
    (art / "catalase.json").write_text(json.dumps({"caption": "<b>Cat</b> & ase"}), encoding="utf-8")
    run_main(export, [str(deck), "--art", str(art)], monkeypatch)
    page = (tmp_path / "out/flashcards.html").read_text(encoding="utf-8")
    assert 'id="ta"' in page and "Memory aids" in page
    assert "AI illustrations — memory aids, not references" in page
    srcs = re.findall(r'<img class="art" src="([^"]+)"', page)
    assert len(srcs) == 2
    for s in srcs:
        assert (tmp_path / "out" / urllib.parse.unquote(s)).exists()
    assert "&lt;b&gt;Cat&lt;/b&gt; &amp; ase" in page and "<b>Cat</b>" not in page
    assert "Diagrams" not in page


def test_empty_or_missing_folders_add_no_tab(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    (tmp_path / "empty").mkdir()
    run_main(export, [str(deck), "--diagrams", str(tmp_path / "empty"), "--art", str(tmp_path / "empty")], monkeypatch)
    page = (tmp_path / "out/flashcards.html").read_text(encoding="utf-8")
    assert 'id="td"' not in page and 'id="ta"' not in page


def _bad_image_case(tmp_path, image, outside=False):
    folder = tmp_path / "diagrams"
    folder.mkdir()
    make_png(tmp_path / "outside.png")  # exists, but outside the diagrams folder
    make_png(folder / "x.txt")  # PNG bytes under a non-.png name
    spec = {"case": "demo", "slug": "bad", "title": "Bad", "image": image,
            "labels": [{"id": "n1", "kind": "node", "label": "L", "cite": S3}]}
    (folder / "bad.occlusion.json").write_text(json.dumps(spec), encoding="utf-8")
    return folder


@pytest.mark.parametrize("image", ["../outside.png", "x.txt"])
def test_bad_diagram_image_is_skipped_with_warning(export, tmp_path, monkeypatch, capsys, image):
    deck = write_deck(tmp_path / "out", MIXED)
    folder = _bad_image_case(tmp_path, image)
    run_main(export, [str(deck), "--diagrams", str(folder)], monkeypatch)
    assert "warning" in capsys.readouterr().out
    assert not (tmp_path / "out/flashcards_media").exists()
    page = (tmp_path / "out/flashcards.html").read_text(encoding="utf-8")
    assert 'id="td"' not in page and "Diagrams" not in page


def test_nonexistent_diagrams_folder_exits(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    with pytest.raises(SystemExit):
        run_main(export, [str(deck), "--diagrams", str(tmp_path / "nope")], monkeypatch)


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


def test_media_never_overwrites_unowned_file(export, tmp_path, monkeypatch, capsys):
    deck = write_deck(tmp_path / "out", MIXED)
    art = tmp_path / "art"
    art.mkdir()
    make_png(art / "foo.png", "red")
    mine = tmp_path / "out/flashcards_media/art/foo.png"
    mine.parent.mkdir(parents=True)
    mine.write_bytes(b"user file, not ours")
    run_main(export, [str(deck), "--art", str(art)], monkeypatch)
    assert mine.read_bytes() == b"user file, not ours"
    assert "warning" in capsys.readouterr().out
    page = (tmp_path / "out/flashcards.html").read_text(encoding="utf-8")
    assert 'class="art"' not in page


def test_media_rerun_replaces_own_file_and_adopts_identical(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    art = tmp_path / "art"
    art.mkdir()
    make_png(art / "foo.png", "red")
    run_main(export, [str(deck), "--art", str(art)], monkeypatch)
    make_png(art / "foo.png", "blue")
    run_main(export, [str(deck), "--art", str(art)], monkeypatch)
    dest = tmp_path / "out/flashcards_media/art/foo.png"
    assert dest.read_bytes() == (art / "foo.png").read_bytes()


# --- vignettes tab ----------------------------------------------------------

OPT_TEXTS = ["Alpha opt", "Bravo opt", "Charlie opt", "Delta opt", "Echo opt"]


def make_vignettes(path: Path, stem: str = "A 4-year-old has honey-crust lesions. Next step?", texts=None, explanations=None) -> Path:
    texts = texts or OPT_TEXTS
    explanations = explanations or [f"Why {k}. {S3} [PMID: 12345678]" for k in "ABCDE"]
    vg = {"vignettes": [{
        "id": "staph-1", "objective": 1, "discipline": "micro", "stem": stem,
        "options": [{"key": k, "text": t, "correct": k == "B", "explanation": e}
                    for k, t, e in zip("ABCDE", texts, explanations)],
    }]}
    path.write_text(json.dumps(vg), encoding="utf-8")
    return path


def outside_templates(page: str) -> str:
    return re.sub(r"<template.*?</template>", "", page, flags=re.S)


def test_vignettes_tab_added_only_with_flag_and_page_otherwise_identical(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    run_main(export, [str(deck)], monkeypatch)
    before = (tmp_path / "out/flashcards.html").read_bytes()
    assert b"Vignettes" not in before
    vg = make_vignettes(tmp_path / "vignettes.json")
    run_main(export, [str(deck), "--vignettes", str(vg)], monkeypatch)
    page = (tmp_path / "out/flashcards.html").read_text(encoding="utf-8")
    assert 'id="tv"' in page and "Vignettes" in page and 'id="vignettes"' in page
    run_main(export, [str(deck)], monkeypatch)
    assert (tmp_path / "out/flashcards.html").read_bytes() == before


def test_diagrams_only_page_unchanged_by_vignette_support(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    diagrams = make_diagrams(tmp_path / "diagrams", [("X", S3)])
    run_main(export, [str(deck), "--diagrams", str(diagrams)], monkeypatch)
    page = (tmp_path / "out/flashcards.html").read_text(encoding="utf-8")
    assert "vignette" not in page.lower() and "'tv'" not in page


def test_option_text_only_inside_template(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    vg = make_vignettes(tmp_path / "vignettes.json")
    run_main(export, [str(deck), "--vignettes", str(vg)], monkeypatch)
    page = (tmp_path / "out/flashcards.html").read_text(encoding="utf-8")
    visible = outside_templates(page)
    assert "honey-crust" in visible and "<textarea" in visible and "disabled" in visible
    for t in OPT_TEXTS:
        assert t not in visible and t in page
    assert "Why B" not in visible and "Why B" in page
    assert page.count("<template") == 1


def test_vignette_text_is_escaped(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    evil = "<script>alert(1)</script>"
    vg = make_vignettes(tmp_path / "vignettes.json", stem=evil,
                        texts=[evil] + OPT_TEXTS[1:], explanations=["<img src=x onerror=alert(2)>"] * 5)
    run_main(export, [str(deck), "--vignettes", str(vg)], monkeypatch)


def test_anki_rows_carry_msad_tag(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    run_main(export, [str(deck)], monkeypatch)
    for name in ("flashcards.anki.txt", "flashcards.cloze.anki.txt"):
        rows = [l for l in (tmp_path / "out" / name).read_text(encoding="utf-8").splitlines() if not l.startswith("#")]
        assert rows
        for row in rows:
            assert "msad" in row.split("\t")[3].split()
            assert "micro" in row.split("\t")[3].split()


def test_anki_row_without_csv_tags_still_gets_msad(export, tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    (out / "flashcards.csv").write_text("front,back,sources,tags\nQ?,A,,\n", encoding="utf-8")
    run_main(export, [str(out / "flashcards.csv")], monkeypatch)
    row = [l for l in (out / "flashcards.anki.txt").read_text(encoding="utf-8").splitlines() if not l.startswith("#")][0]
    assert row.split("\t")[3] == "msad"


def make_deepen(folder: Path, files: dict[str, str]) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (folder / name).write_text(text, encoding="utf-8")
    return folder


def test_deepen_tab_renders_explainer_with_linked_citation(export, notes, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    deepen = make_deepen(tmp_path / "deepen", {
        "scalded-skin.md": f"# Scalded skin\n\n- Exfoliative toxin cleaves desmoglein-1. {S3} [PMID: 123456]\n"})
    run_main(export, [str(deck), "--notes", str(notes), "--deepen", str(deepen)], monkeypatch)
    page = (tmp_path / "out/flashcards.html").read_text(encoding="utf-8")
    assert 'id="te"' in page and "Deep dives" in page and 'id="deepen"' in page
    section = page.split('id="deepen"')[1].split("</section>")[0]
    assert "<h1>Scalded skin</h1>" in section and "<li>" in section
    (href,) = re.findall(r'href="([^"]+_sources/[^"]+)"', section)
    assert urllib.parse.unquote(href).endswith("#S3")
    assert "pubmed.ncbi.nlm.nih.gov/123456/" in section


def test_deepen_citations_stay_plain_without_notes(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    deepen = make_deepen(tmp_path / "deepen", {"a.md": f"- Fact. {S3}\n"})
    run_main(export, [str(deck), "--deepen", str(deepen)], monkeypatch)
    page = (tmp_path / "out/flashcards.html").read_text(encoding="utf-8")
    assert 'id="te"' in page and hrefs(page) == []


def test_no_deepen_flag_page_is_unchanged(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    run_main(export, [str(deck)], monkeypatch)
    page = (tmp_path / "out/flashcards.html").read_text(encoding="utf-8")
    assert "Deep dives" not in page and 'id="deepen"' not in page and page.count("<button") == 5


def test_empty_deepen_folder_adds_no_tab(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    (tmp_path / "empty").mkdir()
    run_main(export, [str(deck), "--deepen", str(tmp_path / "empty")], monkeypatch)
    page = (tmp_path / "out/flashcards.html").read_text(encoding="utf-8")
    assert 'id="te"' not in page and "Deep dives" not in page


def test_raw_html_in_deepen_file_is_escaped(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    deepen = make_deepen(tmp_path / "deepen", {"x.md": "<script>alert(1)</script>\n\n<img src=x onerror=alert(2)>\n"})
    run_main(export, [str(deck), "--deepen", str(deepen)], monkeypatch)
    page = (tmp_path / "out/flashcards.html").read_text(encoding="utf-8")
    assert "<script>alert(1)" not in page and "<img src=x" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page


def test_vignette_citations_link_like_cards(export, notes, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    vg = make_vignettes(tmp_path / "vignettes.json")
    run_main(export, [str(deck), "--notes", str(notes), "--vignettes", str(vg)], monkeypatch)
    page = (tmp_path / "out/flashcards.html").read_text(encoding="utf-8")
    tpl = re.search(r"<template.*?</template>", page, re.S).group(0)
    assert "pubmed.ncbi.nlm.nih.gov/12345678/" in tpl
    links = hrefs(tpl)
    assert links and all(urllib.parse.unquote(h).endswith("#S3") for h in links)
    # without --notes the course citation stays a label, PMID still links
    run_main(export, [str(deck), "--vignettes", str(vg)], monkeypatch)
    tpl = re.search(r"<template.*?</template>", (tmp_path / "out/flashcards.html").read_text(encoding="utf-8"), re.S).group(0)
    assert hrefs(tpl) == [] and "pubmed.ncbi.nlm.nih.gov/12345678/" in tpl


def test_page_has_no_storage_or_network_calls(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    vg = make_vignettes(tmp_path / "vignettes.json")
    run_main(export, [str(deck), "--vignettes", str(vg)], monkeypatch)
    page = (tmp_path / "out/flashcards.html").read_text(encoding="utf-8")
    for bad in ("localStorage", "sessionStorage", "indexedDB", "fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket", "document.cookie"):
        assert bad not in page


@pytest.mark.parametrize("content", ["{not json", "[]", '{"vignettes": "x"}', '{"vignettes": [{"stem": "s"}]}',
                                     '{"vignettes": [{"stem": "s", "options": ["x"]}]}', '{"vignettes": ["x"]}'])
def test_malformed_vignettes_file_exits_readably(export, tmp_path, monkeypatch, content):
    deck = write_deck(tmp_path / "out", MIXED)
    bad = tmp_path / "bad.json"
    bad.write_text(content, encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        run_main(export, [str(deck), "--vignettes", str(bad)], monkeypatch)
    assert "--vignettes" in str(e.value)


def test_missing_vignettes_file_exits_readably(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    with pytest.raises(SystemExit) as e:
        run_main(export, [str(deck), "--vignettes", str(tmp_path / "nope.json")], monkeypatch)
    assert "--vignettes" in str(e.value)


def _chromium_page():
    sync_api = pytest.importorskip("playwright.sync_api", reason="playwright is not installed")
    pw = sync_api.sync_playwright().start()
    try:
        browser = pw.chromium.launch()
    except Exception as exc:  # browser binary not installed
        pw.stop()
        pytest.skip(f"Chromium unavailable for Playwright: {str(exc).splitlines()[0]}")
    return pw, browser


def test_vignette_flow_in_browser(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    vg = make_vignettes(tmp_path / "vignettes.json")
    run_main(export, [str(deck), "--vignettes", str(vg)], monkeypatch)
    pw, browser = _chromium_page()
    try:
        page = browser.new_page()
        page.goto((tmp_path / "out/flashcards.html").as_uri())
        page.click("#tv")
        btn = page.locator("#vignettes button.vshow")
        assert btn.is_disabled()
        assert page.locator("#vignettes .vopt").count() == 0
        page.fill("#vignettes textarea", "   ")
        assert btn.is_disabled()
        page.fill("#vignettes textarea", "Impetigo; give mupirocin")
        assert btn.is_enabled()
        assert page.locator("#vignettes .vopt").count() == 0
        btn.click()
        assert page.locator("#vignettes .vopt").count() == 5
        assert page.locator("#vignettes .vexp:visible").count() == 0
        page.locator("#vignettes .vopt", has_text="Alpha opt").click()
        assert page.locator("#vignettes .vexp:visible").count() == 5
        assert page.locator("#vignettes .vopt.correct").count() == 1
        assert "Bravo opt" in page.locator("#vignettes .vopt.correct").inner_text()
        assert page.locator("#vignettes .vopt.incorrect").count() == 1  # the chosen wrong one
    finally:
        browser.close()
        pw.stop()


def _vignette_with(tmp_path, mutate):
    vg = make_vignettes(tmp_path / "vignettes.json")
    data = json.loads(vg.read_text(encoding="utf-8"))
    mutate(data["vignettes"][0])
    vg.write_text(json.dumps(data), encoding="utf-8")
    return vg


@pytest.mark.parametrize("mutate", [
    lambda v: v.__setitem__("options", v["options"][:4]),
    lambda v: v["options"][0].__setitem__("key", "Z"),
    lambda v: [o.__setitem__("correct", False) for o in v["options"]],
    lambda v: v["options"][2].__setitem__("explanation", ""),
    lambda v: v["options"][1].pop("explanation"),
], ids=["four-options", "bad-key", "no-correct", "empty-explanation", "missing-explanation"])
def test_incomplete_vignette_schema_exits_readably(export, tmp_path, monkeypatch, mutate):
    deck = write_deck(tmp_path / "out", MIXED)
    vg = _vignette_with(tmp_path, mutate)
    with pytest.raises(SystemExit) as e:
        run_main(export, [str(deck), "--vignettes", str(vg)], monkeypatch)
    assert "--vignettes" in str(e.value)


@pytest.mark.parametrize("content", ['{"vignettes": []}'], ids=["empty-list"])
def test_empty_vignette_list_exits_readably(export, tmp_path, monkeypatch, content):
    deck = write_deck(tmp_path / "out", MIXED)
    bad = tmp_path / "bad.json"
    bad.write_text(content, encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        run_main(export, [str(deck), "--vignettes", str(bad)], monkeypatch)
    assert "--vignettes" in str(e.value)


def test_blank_stem_exits_readably(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    vg = make_vignettes(tmp_path / "vignettes.json", stem="   ")
    with pytest.raises(SystemExit) as e:
        run_main(export, [str(deck), "--vignettes", str(vg)], monkeypatch)
    assert "--vignettes" in str(e.value)


def test_vignettes_tab_has_running_score(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    vg = make_vignettes(tmp_path / "vignettes.json")
    run_main(export, [str(deck), "--vignettes", str(vg)], monkeypatch)
    page = (deck.parent / "flashcards.html").read_text(encoding="utf-8")
    assert 'id="vscore"' in page and "Score: 0 / 0" in page
    assert "getElementById('vscore')" in page and "'Score: '+sc" in page


@pytest.mark.parametrize("md", [
    "[x](javascript:alert(1))",
    "[x](JaVaScRiPt:alert(1))",
    "[x](  javascript:alert(1))",
    "[x](data:text/html;base64,PHNjcmlwdD4=)",
    "[x](vbscript:msgbox(1))",
    "![x](javascript:alert(1))",
    "<javascript:alert(1)>",
])
def test_deepen_unsafe_link_schemes_never_emitted(export, tmp_path, monkeypatch, md):
    deck = write_deck(tmp_path / "out", MIXED)
    deepen = make_deepen(tmp_path / "deepen", {"x.md": f"{md}\n"})
    run_main(export, [str(deck), "--deepen", str(deepen)], monkeypatch)
    section = (tmp_path / "out/flashcards.html").read_text(encoding="utf-8").split('id="deepen"')[1].split("</section>")[0]
    assert not re.search(r"(?i)(?:href|src)=\"\s*(?:javascript|data|vbscript):", section)


def test_deepen_safe_links_survive(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    deepen = make_deepen(tmp_path / "deepen", {"x.md": "[a](https://example.org/p) [b](mailto:a@b.co) [c](#top) [d](other.md)\n"})
    run_main(export, [str(deck), "--deepen", str(deepen)], monkeypatch)
    section = (tmp_path / "out/flashcards.html").read_text(encoding="utf-8").split('id="deepen"')[1].split("</section>")[0]
    for h in ("https://example.org/p", "mailto:a@b.co", "#top", "other.md"):
        assert f'href="{h}"' in section


def test_committed_example_imports_carry_ownership_tag():
    root = Path(__file__).resolve().parent.parent / "examples"
    for name in ("flashcards.anki.txt", "flashcards.cloze.anki.txt"):
        rows = [ln for ln in (root / name).read_text(encoding="utf-8").splitlines() if ln.startswith("msad-")]
        assert rows and all("msad" in ln.rsplit("\t", 1)[-1].split() for ln in rows), name


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_option_text_exits_readably(export, tmp_path, monkeypatch, blank):
    deck = write_deck(tmp_path / "out", MIXED)
    vg = make_vignettes(tmp_path / "vignettes.json", texts=["Alpha", blank, "Charlie", "Delta", "Echo"])
    with pytest.raises(SystemExit) as e:
        run_main(export, [str(deck), "--vignettes", str(vg)], monkeypatch)
    assert "--vignettes" in str(e.value)


def test_page_shortcuts_ignore_typing_in_form_fields(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", MIXED)
    vg = make_vignettes(tmp_path / "vignettes.json")
    run_main(export, [str(deck), "--vignettes", str(vg)], monkeypatch)
    page = (tmp_path / "out" / "flashcards.html").read_text(encoding="utf-8")
    handler = page.split("document.onkeydown=", 1)[1].split("\n", 1)[0]
    assert "textarea" in handler and "return" in handler.split("textarea")[0] + handler.split("textarea")[1]
    assert handler.index("textarea") < handler.index("preventDefault")


@pytest.mark.parametrize("flag, make_bad", [
    ("--vignettes", lambda p: p.write_text("{not json", encoding="utf-8")),
    ("--diagrams", lambda p: None),   # path that is not a folder
    ("--art", lambda p: None),
    ("--deepen", lambda p: None),
])
def test_bad_optional_input_leaves_existing_sources_and_page_intact(export, notes, tmp_path, monkeypatch, flag, make_bad):
    deck = write_deck(tmp_path / "out", [("Q?", "A", S3)])
    run_main(export, [str(deck), "--notes", str(notes)], monkeypatch)
    sources = tmp_path / "out/flashcards_sources"
    before = sorted(p.name for p in sources.rglob("*") if p.is_file())
    page_before = (tmp_path / "out/flashcards.html").read_text(encoding="utf-8")
    assert before
    bad = tmp_path / "bad"
    make_bad(bad) if flag == "--vignettes" else None
    if flag == "--vignettes":
        pass
    else:
        bad.write_text("not a folder", encoding="utf-8")
    with pytest.raises(SystemExit):
        run_main(export, [str(deck), "--notes", str(notes), flag, str(bad)], monkeypatch)
    assert sorted(p.name for p in sources.rglob("*") if p.is_file()) == before
    assert (tmp_path / "out/flashcards.html").read_text(encoding="utf-8") == page_before


def test_flashcards_skill_lists_every_export_flag():
    text = (Path(__file__).resolve().parent.parent / ".claude" / "skills" / "flashcards" / "SKILL.md").read_text(encoding="utf-8")
    for flag in ("--guide", "--notes", "--diagrams", "--art", "--deepen", "--vignettes"):
        assert flag in text, flag


def test_unreadable_deepen_file_exits_before_any_output_changes(export, notes, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", [("Q?", "A", S3)])
    run_main(export, [str(deck), "--notes", str(notes)], monkeypatch)
    anki = deck.with_suffix(".anki.txt")
    anki_before = anki.read_text(encoding="utf-8")
    deck.write_text(deck.read_text(encoding="utf-8") + 'Q2?,A2,"' + S3 + '",\n', encoding="utf-8")  # a new card
    dd = tmp_path / "deepen"
    dd.mkdir()
    (dd / "bad.md").write_bytes(b"\xff\xfe\x00bad")
    with pytest.raises(SystemExit) as e:
        run_main(export, [str(deck), "--notes", str(notes), "--deepen", str(dd)], monkeypatch)
    assert "--deepen" in str(e.value)
    assert anki.read_text(encoding="utf-8") == anki_before


def test_course_label_with_ampersand_is_escaped_exactly_once(export):
    """Callers escape text before linkify; the label must not be escaped a second time."""
    cite = "[[GUIDE/Self Study Guide 01 Smith & Lee#P561]]"
    out = export.linkify(export.html.escape(f"see {cite}", quote=False))
    assert "Smith &amp; Lee" in out and "&amp;amp;" not in out


def test_course_label_ampersand_on_study_page(export, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "out", [("Q?", "A", "[[GUIDE/Smith & Lee#P5]]")])
    run_main(export, [str(deck)], monkeypatch)
    page = (tmp_path / "out/flashcards.html").read_text(encoding="utf-8")
    assert "Smith &amp; Lee" in page and "&amp;amp;" not in page


def test_vignette_stem_keeps_line_breaks(export):
    assert ".vstem{white-space:pre-wrap}" in export.VIGNETTE_CSS


@pytest.mark.parametrize("url", [
    "javascript:alert(1)", "JaVaScRiPt:alert(1)", " javascript:alert(1)", "java\tscript:alert(1)",
    "data:text/html;base64,PHNjcmlwdD4=", "DATA:text/html,x", "vbscript:msgbox(1)", "\x01javascript:alert(1)",
])
def test_source_pages_drop_unsafe_link_schemes(export, notes, tmp_path, monkeypatch, url):
    src = notes / "MICRO" / "Staph deck (sample).md"
    src.write_text(src.read_text(encoding="utf-8") + f"\nLink [x]({url}) and ![i]({url})\n"
                   f"\n[good](https://example.org/a) [rel](#S1) [mail](mailto:a@b.org)\n", encoding="utf-8")
    deck = write_deck(tmp_path / "out", [("Q?", "A", S3)])
    run_main(export, [str(deck), "--notes", str(notes)], monkeypatch)
    page = next((tmp_path / "out/flashcards_sources").rglob("Staph deck (sample).html")).read_text(encoding="utf-8")
    low = page.lower()
    assert "javascript:" not in low.replace("\t", "") and "vbscript:" not in low and 'href="data:' not in low
    assert 'src="data:' not in low
    assert 'href="https://example.org/a"' in page and 'href="#S1"' in page and 'href="mailto:a@b.org"' in page
