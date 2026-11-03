"""U2: occlusion boxes, masked cards, Image Occlusion fields, offline deck.

Chromium-dependent tests skip when Chromium is missing.
Run: uv run --with pytest --with markdown --with genanki --with pillow --with playwright pytest tests -q
"""
from __future__ import annotations

import io
import json
import re
import shutil
import sqlite3
import zipfile
from pathlib import Path

import pytest

from conftest import load_script, run_main

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")
FIX = Path(__file__).parent / "fixtures"
SKIP = "Chromium not installed: uv run --with playwright playwright install chromium"


@pytest.fixture(scope="module")
def occ():
    return load_script("occlude")


@pytest.fixture(scope="module")
def chromium_ok(occ):
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            occ.launch_chromium(p).close()
    except Exception:
        return False
    return True


@pytest.fixture
def need_chromium(chromium_ok):
    if not chromium_ok:
        pytest.skip(SKIP)


@pytest.fixture
def work(tmp_path):
    d = tmp_path / "output" / "case-a" / "diagrams"
    d.mkdir(parents=True)
    shutil.copy(FIX / "diagram.html", d / "staph-toxins.html")
    shutil.copy(FIX / "diagram-spec.json", d / "staph-toxins.json")
    return d


def run(occ, monkeypatch, d, slug="staph-toxins", case="case-a"):
    return run_main(occ, [str(d / f"{slug}.html"), "--spec", str(d / f"{slug}.json"), "--case", case], monkeypatch)


def load(d, slug="staph-toxins"):
    return json.loads((d / f"{slug}.occlusion.json").read_text(encoding="utf-8"))


# ---- pure functions (no browser) ----

def test_occlusion_string_matches_pinned_anki_format(occ):
    pin = json.loads((FIX / "io-note-fields.json").read_text(encoding="utf-8"))
    assert "rslib/src/cloze.rs" in pin["source"] and "imageocclusion.rs" in pin["source"]
    i = pin["input"]
    fields = occ.io_fields(i["title"], i["image"], i["label"], i["cite"], i["box"])
    assert list(fields) == pin["field_order"]
    assert fields == pin["fields"]


def test_norm_number_format(occ):
    assert occ.fmt_norm(0.2325) == ".2325"
    assert occ.fmt_norm(0.202) == ".202"
    assert occ.fmt_norm(0.0975) == ".0975"
    assert occ.fmt_norm(0.2) == ".2"
    assert occ.fmt_norm(0) == "0"
    assert occ.fmt_norm(1) == "1"


def test_note_id_scheme(occ):
    import hashlib
    assert occ.note_id("staph-toxins", "n1") == "msad-" + hashlib.sha1(b"staph-toxins:n1").hexdigest()[:12]


@pytest.mark.parametrize("bad", ["../x", "a/b", "Up", "a b", "x.y"])
def test_bad_case_rejected_before_writing(occ, monkeypatch, tmp_path, bad):
    d = tmp_path / "output" / "case-a" / "diagrams"
    d.mkdir(parents=True)
    shutil.copy(FIX / "diagram.html", d / "ok.html")
    shutil.copy(FIX / "diagram-spec.json", d / "ok.json")
    before = {p.name for p in tmp_path.rglob("*")}
    assert run_main(occ, [str(d / "ok.html"), "--spec", str(d / "ok.json"), "--case", bad], monkeypatch) != 0
    assert {p.name for p in tmp_path.rglob("*")} == before


def test_dotdot_slug_from_html_name_rejected(occ, monkeypatch, tmp_path):
    d = tmp_path / "diagrams"
    d.mkdir()
    shutil.copy(FIX / "diagram.html", d / "Bad..Name.html")
    shutil.copy(FIX / "diagram-spec.json", d / "spec.json")
    before = {p.name for p in tmp_path.rglob("*")}
    rc = run_main(occ, [str(d / "Bad..Name.html"), "--spec", str(d / "spec.json"), "--case", "case-a"], monkeypatch)
    assert rc != 0
    assert {p.name for p in tmp_path.rglob("*")} == before


# ---- browser tests ----

def test_boxes_for_nodes_and_edge(occ, monkeypatch, work, need_chromium):
    assert run(occ, monkeypatch, work) == 0
    data = load(work)
    assert data["case"] == "case-a" and data["slug"] == "staph-toxins"
    assert data["image"] == "staph-toxins.card.png"
    labs = {l["id"]: l for l in data["labels"]}
    assert set(labs) == {"n1", "n2", "n3", "n4", "e1"}
    assert labs["e1"]["kind"] == "edge" and labs["n1"]["kind"] == "node"
    for l in labs.values():
        b = l["box"]
        assert 0 <= b["left"] and 0 <= b["top"] and b["width"] > 0 and b["height"] > 0
        assert b["left"] + b["width"] <= 1 and b["top"] + b["height"] <= 1
        assert l["note_id"] == occ.note_id("staph-toxins", l["id"])
        assert l["cite"]
    assert labs["n1"]["label"] == "Exfoliative toxin"
    # group transform (translate 10,10) is applied: n1 text starts at x=20+10 of 600
    assert abs(labs["n1"]["box"]["left"] - 30 / 600) < 0.01


def test_occlusion_string_in_output_matches_format(occ, monkeypatch, work, need_chromium):
    run(occ, monkeypatch, work)
    for l in load(work)["labels"]:
        b = l["box"]
        expect = ("{{c1::image-occlusion:rect:left=%s:top=%s:width=%s:height=%s:oi=1}}"
                  % (occ.fmt_norm(b["left"]), occ.fmt_norm(b["top"]), occ.fmt_norm(b["width"]), occ.fmt_norm(b["height"])))
        assert l["occlusion"] == expect
        assert re.fullmatch(r"\{\{c1::image-occlusion:rect:left=\.?\d+:top=\.?\d+:width=\.?\d+:height=\.?\d+:oi=1\}\}", l["occlusion"])


def test_mask_covers_label_pixels_despite_page_margins(occ, monkeypatch, work, need_chromium):
    from PIL import Image
    run(occ, monkeypatch, work)
    data = load(work)
    card = Image.open(work / data["image"]).convert("RGB")
    assert card.getpixel((0, 0)) == (245, 245, 245) or card.getpixel((0, 0)) != (255, 255, 255, 0)
    W, H = card.size
    for l in data["labels"]:
        b = l["box"]
        masked = Image.open(work / l["masked"]).convert("RGB")
        assert masked.size == card.size
        x0, y0 = round(b["left"] * W), round(b["top"] * H)
        x1, y1 = round((b["left"] + b["width"]) * W), round((b["top"] + b["height"]) * H)
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        assert masked.getpixel((cx, cy)) == occ.MASK_COLOR
        # the label's own pixels differ from the card (text rendered there)
        crop = (x0 + 1, y0 + 1, x1 - 1, y1 - 1)
        assert list(masked.crop(crop).getdata()) != list(card.crop(crop).getdata())
        assert set(masked.crop(crop).getdata()) == {occ.MASK_COLOR}
        # the card has ink inside the box (the mask is covering real label pixels)
        assert len(set(card.crop(crop).getdata())) > 1
        hl = Image.open(work / l["highlight"]).convert("RGB")
        assert hl.size == card.size and list(hl.getdata()) != list(card.getdata())


def test_card_png_is_opaque_and_svg_only(occ, monkeypatch, work, need_chromium):
    from PIL import Image
    run(occ, monkeypatch, work)
    im = Image.open(work / "staph-toxins.card.png")
    assert im.mode in ("RGB", "L") or im.convert("RGBA").getextrema()[3] == (255, 255)
    # corner is the paper color, not the white page margin
    assert im.convert("RGB").getpixel((0, 0)) == occ.PAPER_COLOR


def test_script_in_fixture_never_runs(occ, monkeypatch, work, need_chromium):
    assert "TAMPERED BY SCRIPT" in (work / "staph-toxins.html").read_text()
    assert run(occ, monkeypatch, work) == 0  # would fail the text check if script ran
    labs = {l["id"]: l for l in load(work)["labels"]}
    assert labs["n1"]["label"] == "Exfoliative toxin"


def test_missing_element_fails_naming_id(occ, monkeypatch, work, need_chromium, capsys):
    p = work / "staph-toxins.html"
    p.write_text(p.read_text().replace('data-node="n3"', 'data-nodeX="n3"'), encoding="utf-8")
    assert run(occ, monkeypatch, work) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out and "n3" in out
    assert not (work / "staph-toxins.occlusion.json").exists()


def test_extra_text_without_spec_id_fails(occ, monkeypatch, work, need_chromium, capsys):
    p = work / "staph-toxins.html"
    p.write_text(p.read_text().replace("</svg>", '<text x="5" y="250">Stray</text></svg>'), encoding="utf-8")
    assert run(occ, monkeypatch, work) == 1
    assert "Stray" in capsys.readouterr().out


def test_unknown_data_node_id_fails_naming_id(occ, monkeypatch, work, need_chromium, capsys):
    p = work / "staph-toxins.html"
    p.write_text(p.read_text().replace("</svg>", '<text data-node="zz9" x="5" y="250">Extra</text></svg>'), encoding="utf-8")
    assert run(occ, monkeypatch, work) == 1
    assert "zz9" in capsys.readouterr().out


def test_changed_label_fails_naming_id(occ, monkeypatch, work, need_chromium, capsys):
    p = work / "staph-toxins.html"
    p.write_text(p.read_text().replace(">Desmoglein-1<", ">Desmoglein-3<"), encoding="utf-8")
    assert run(occ, monkeypatch, work) == 1
    out = capsys.readouterr().out
    assert "n2" in out and "Desmoglein" in out


def test_whitespace_normalized_label_passes(occ, monkeypatch, work, need_chromium):
    p = work / "staph-toxins.html"
    p.write_text(p.read_text().replace(">Exfoliative toxin<", ">\n   Exfoliative   toxin \n<"), encoding="utf-8")
    assert run(occ, monkeypatch, work) == 0


def test_non_string_label_spec_fails_cleanly(occ, monkeypatch, work, capsys):
    spec = json.loads((work / "staph-toxins.json").read_text())
    spec["nodes"][0]["label"] = 123
    (work / "staph-toxins.json").write_text(json.dumps(spec), encoding="utf-8")
    assert run(occ, monkeypatch, work) == 1
    out = capsys.readouterr()
    assert "must be a string" in out.out and spec["nodes"][0]["id"] in out.out
    assert "Traceback" not in out.out + out.err


def test_spec_string_validation_unit(occ):
    assert occ.spec_type_problems({"nodes": [{"id": "n1", "label": "ok", "cite": "c"}], "edges": []}) == []
    probs = occ.spec_type_problems({"nodes": [{"id": "n1", "label": 5, "cite": "c"}],
                                    "edges": [{"id": "e1", "label": "x", "cite": 7}]})
    assert any("n1" in p and "label" in p for p in probs) and any("e1" in p and "cite" in p for p in probs)


class _Counter:
    hits = 0


@pytest.fixture
def counting_server():
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import threading

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            _Counter.hits += 1
            self.send_response(404)
            self.end_headers()

        def log_message(self, *a):
            pass

    _Counter.hits = 0
    srv = HTTPServer(("127.0.0.1", 0), H)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield srv.server_address[1], _Counter
    srv.shutdown()
    srv.server_close()


def test_network_requests_blocked(occ, monkeypatch, work, need_chromium, counting_server):
    port, counter = counting_server
    base = f"http://127.0.0.1:{port}"
    p = work / "staph-toxins.html"
    html = p.read_text()
    assert "<svg" in html and "</svg>" in html
    html = html.replace("</svg>", f'<image href="{base}/svg.png"/><style>svg{{background:url({base}/bg.png)}}</style></svg>', 1)
    html = html.replace("</body>", f'<img src="{base}/x.png"></body>')
    p.write_text(html, encoding="utf-8")
    assert run(occ, monkeypatch, work) == 0
    assert counter.hits == 0


# ---- apkg ----

def apkg_notes(path: Path):
    with zipfile.ZipFile(path) as z:
        db = Path(path.parent / "col.tmp")
        names = z.namelist()
        dbname = "collection.anki21" if "collection.anki21" in names else "collection.anki2"
        db.write_bytes(z.read(dbname))
        media = json.loads(z.read("media"))
    con = sqlite3.connect(db)
    rows = con.execute("select guid, flds from notes").fetchall()
    decks = con.execute("select decks from col").fetchone()[0]
    con.close()
    db.unlink()
    return rows, media, decks


def make_apkg(occ, monkeypatch, d):
    assert run(occ, monkeypatch, d) == 0
    assert run_main(occ, ["--apkg", str(d), "--case", "case-a"], monkeypatch) == 0
    return d.parent / "diagrams.apkg"


def test_apkg_one_note_per_label_stable_guids(occ, monkeypatch, work, need_chromium, tmp_path):
    out = make_apkg(occ, monkeypatch, work)
    rows, media, decks = apkg_notes(out)
    ids = {l["id"]: l["note_id"] for l in load(work)["labels"]}
    assert sorted(g for g, _ in rows) == sorted(ids.values())
    assert "AI Study::case-a::diagrams-offline" in decks
    flds = {g: f for g, f in rows}
    n1 = flds[ids["n1"]]
    assert "Exfoliative toxin" in n1 and "#S4" in n1
    assert len(media) >= 2 * len(ids)
    first = sorted(g for g, _ in rows)
    out2 = make_apkg(occ, monkeypatch, work)
    assert sorted(g for g, _ in apkg_notes(out2)[0]) == first


def test_adding_a_node_leaves_other_ids_unchanged(occ, monkeypatch, work, need_chromium):
    out = make_apkg(occ, monkeypatch, work)
    before = {g for g, _ in apkg_notes(out)[0]}
    spec = json.loads((work / "staph-toxins.json").read_text())
    spec["nodes"].append({"id": "n5", "label": "Bullous impetigo", "cite": "[[MICRO/Staphylococcus aureus (sample lecture)#S4]]"})
    (work / "staph-toxins.json").write_text(json.dumps(spec))
    p = work / "staph-toxins.html"
    p.write_text(p.read_text().replace("</g>", '<text data-node="n5" x="20" y="140">Bullous impetigo</text></g>'), encoding="utf-8")
    after = {g for g, _ in apkg_notes(make_apkg(occ, monkeypatch, work))[0]}
    assert before < after and len(after - before) == 1


def test_chromium_missing_exits_2(occ, monkeypatch, work, capsys):
    def boom(p):
        raise occ.ChromiumUnavailable("no chromium")
    monkeypatch.setattr(occ, "launch_chromium", boom)
    assert run(occ, monkeypatch, work) == 2
    assert "playwright install chromium" in capsys.readouterr().out
