"""anki_sync tests run against a fake AnkiConnect served from a thread on 127.0.0.1."""
from __future__ import annotations

import base64
import csv
import hashlib
import html
import json
import re
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from conftest import load_script, run_main

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
S3 = "[[MICRO/Staph deck (sample)#S3]]"
S2 = "[[MICRO/Staph deck (sample)#S2]]"
ALLOWED = {
    "version", "deckNames", "createDeck", "modelNames", "findNotes", "findCards",
    "notesInfo", "cardsInfo", "addNote", "updateNoteFields", "addTags", "storeMediaFile",
}
IO_ID = "msad-aaaaaaaaaaaa"


class FakeAnki:
    """Just enough AnkiConnect: decks, models, notes, cards, media, and a request log."""

    def __init__(self, version: int = 6, models=("Basic", "Cloze", "Image Occlusion")):
        self.version = version
        self.models = list(models)
        self.decks = {"Default"}
        self.notes: dict[int, dict] = {}
        self.cards: dict[int, dict] = {}
        self.media: dict[str, bytes] = {}
        self.requests: list[dict] = []
        self._id = 1000

    def next_id(self) -> int:
        self._id += 1
        return self._id

    def put_note(self, model, fields, tags, deck, lapses=0, extra_decks=()):
        nid = self.next_id()
        cids = []
        for d in (deck, *extra_decks):
            cid = self.next_id()
            self.cards[cid] = {"deck": d, "lapses": lapses, "note": nid}
            cids.append(cid)
        self.notes[nid] = {"model": model, "fields": dict(fields), "tags": list(tags), "cards": cids}
        return nid

    def deck_of(self, nid):
        return {self.cards[c]["deck"] for c in self.notes[nid]["cards"]}

    def _match(self, nid, query):
        n = self.notes[nid]
        deck = re.search(r'deck:"(.*?)"', query)
        if deck:
            d = deck.group(1)
            if not any(x == d or x.startswith(d + "::") for x in self.deck_of(nid)):
                return False
        tag = re.search(r"tag:(\S+)", query)
        if tag and tag.group(1) not in n["tags"]:
            return False
        return True

    def handle(self, body: dict):
        a, p = body["action"], body.get("params") or {}
        self.requests.append(body)
        if a == "version":
            return self.version
        if a == "deckNames":
            return sorted(self.decks)
        if a == "createDeck":
            self.decks.add(p["deck"])
            return 1
        if a == "modelNames":
            return self.models
        if a == "findNotes":
            return [n for n in self.notes if self._match(n, p["query"])]
        if a == "findCards":
            return [c for c, v in self.cards.items() if self._match(v["note"], p["query"])
                    and self.cards[c]["deck"] in self._decks_in(p["query"])]
        if a == "notesInfo":
            return [
                {"noteId": n, "modelName": self.notes[n]["model"], "tags": self.notes[n]["tags"],
                 "cards": self.notes[n]["cards"],
                 "fields": {k: {"value": v, "order": i} for i, (k, v) in enumerate(self.notes[n]["fields"].items())}}
                for n in p["notes"]
            ]
        if a == "cardsInfo":
            return [
                {"cardId": c, "note": self.cards[c]["note"], "deckName": self.cards[c]["deck"],
                 "lapses": self.cards[c]["lapses"]}
                for c in p["cards"]
            ]
        if a == "addNote":
            n = p["note"]
            assert n["deckName"] in self.decks
            return self.put_note(n["modelName"], n["fields"], n.get("tags", []), n["deckName"])
        if a == "updateNoteFields":
            self.notes[p["note"]["id"]]["fields"].update(p["note"]["fields"])
            return None
        if a == "addTags":
            for nid in p["notes"]:
                for t in p["tags"].split():
                    if t not in self.notes[nid]["tags"]:
                        self.notes[nid]["tags"].append(t)
            return None
        if a == "storeMediaFile":
            if not p.get("deleteExisting", True) and p["filename"] in self.media:
                return p["filename"]
            self.media[p["filename"]] = base64.b64decode(p["data"])
            return p["filename"]
        raise AssertionError(f"fake does not implement {a}")

    @staticmethod
    def _decks_in(query):
        d = re.search(r'deck:"(.*?)"', query)
        return {d.group(1)} if d else set()

    @property
    def actions(self):
        return [r["action"] for r in self.requests]

    def calls(self, action):
        return [r for r in self.requests if r["action"] == action]


@pytest.fixture
def anki_mod():
    return load_script("anki_sync")


@pytest.fixture
def fake_factory():
    servers = []

    def make(**kw):
        fake = FakeAnki(**kw)

        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                try:
                    out = {"result": fake.handle(body), "error": None}
                except AssertionError as e:
                    out = {"result": None, "error": str(e)}
                data = json.dumps(out).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *a):
                pass

        srv = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        servers.append(srv)
        fake.url = f"http://127.0.0.1:{srv.server_port}"
        return fake

    yield make
    for s in servers:
        s.shutdown()
        s.server_close()


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    case = tmp_path / "output" / "case-1"
    case.mkdir(parents=True)
    return case


def write_csv(case: Path, rows=None) -> Path:
    rows = rows or [
        ("What does exfoliative toxin cleave?", "Desmoglein-1", S3, "case-1;micro;toxins"),
        ("Exfoliative toxin cleaves {{c1::desmoglein-1}}.", "", S3, "case-1;micro;toxins"),
        ("Catalase test separates staph from strep?", "Catalase positive is staph", S2, "case-1;micro;lab"),
    ]
    path = case / "flashcards.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["front", "back", "sources", "tags"])
        w.writerows(rows)
    return path


def gid_of(front: str) -> str:
    return "msad-" + hashlib.sha1(front.lower().encode()).hexdigest()[:12]


def write_diagrams(case: Path) -> Path:
    d = case / "diagrams"
    d.mkdir()
    (d / "staph-toxins.card.png").write_bytes(PNG)
    labels = [
        {"id": "n1", "kind": "node", "label": "Exfoliative toxin", "cite": S3,
         "box": {"left": 0.1, "top": 0.2, "width": 0.15, "height": 0.05},
         "note_id": IO_ID,
         "occlusion": "{{c1::image-occlusion:rect:left=.1:top=.2:width=.15:height=.05:oi=1}}",
         "masked": "x.png", "highlight": "y.png"},
        {"id": "n2", "kind": "node", "label": "Desmoglein-1", "cite": S3,
         "box": {"left": 0.5, "top": 0.2, "width": 0.15, "height": 0.05},
         "note_id": "msad-bbbbbbbbbbbb",
         "occlusion": "{{c1::image-occlusion:rect:left=.5:top=.2:width=.15:height=.05:oi=1}}",
         "masked": "x.png", "highlight": "y.png"},
    ]
    (d / "staph-toxins.occlusion.json").write_text(json.dumps(
        {"case": "case-1", "slug": "staph-toxins", "title": "S. aureus toxins",
         "image": "staph-toxins.card.png", "labels": labels}), encoding="utf-8")
    return d


def sync(mod, monkeypatch, fake, case, *extra, csv_path=True, diagrams=None):
    argv = ["--case", "case-1", "--url", fake.url, *extra]
    if csv_path:
        argv += ["--csv", str(case / "flashcards.csv")]
    if diagrams:
        argv += ["--diagrams", str(diagrams)]
    return run_main(mod, argv, monkeypatch)


def summary(out: str) -> dict:
    m = re.search(r"added (\d+), updated (\d+), adopted (\d+), skipped (\d+), weak spots (\d+)", out)
    assert m, out
    return dict(zip(["added", "updated", "adopted", "skipped", "weak"], map(int, m.groups())))


DECK = "AI Study::case-1"


def test_first_sync_adds_then_second_updates_none_added(anki_mod, monkeypatch, fake_factory, workdir, capsys):
    fake = fake_factory()
    write_csv(workdir)
    assert sync(anki_mod, monkeypatch, fake, workdir) == 0
    assert summary(capsys.readouterr().out) == {"added": 3, "updated": 0, "adopted": 0, "skipped": 0, "weak": 0}
    assert DECK in fake.decks and len(fake.notes) == 3
    models = sorted(n["model"] for n in fake.notes.values())
    assert models == ["Basic", "Basic", "Cloze"]
    cloze = next(n for n in fake.notes.values() if n["model"] == "Cloze")
    assert "{{c1::desmoglein-1}}" in cloze["fields"]["Text"] and "Back Extra" in cloze["fields"]
    basic = next(n for n in fake.notes.values() if n["model"] == "Basic")
    assert set(basic["fields"]) == {"Front", "Back"}
    assert "msad" in basic["tags"] and any(t.startswith("msad-id::msad-") for t in basic["tags"])
    assert "micro" in basic["tags"]
    assert "MICRO/Staph deck (sample)" in basic["fields"]["Back"] and "[[" not in basic["fields"]["Back"]

    assert sync(anki_mod, monkeypatch, fake, workdir) == 0
    assert summary(capsys.readouterr().out) == {"added": 0, "updated": 3, "adopted": 0, "skipped": 0, "weak": 0}
    assert len(fake.notes) == 3


def test_hand_imported_note_is_adopted(anki_mod, monkeypatch, fake_factory, workdir, capsys):
    fake = fake_factory()
    fake.decks.add(DECK)
    front = "What does exfoliative toxin cleave?"
    nid = fake.put_note("Basic", {"Front": html.escape(front), "Back": "old"}, [], DECK)
    write_csv(workdir)
    sync(anki_mod, monkeypatch, fake, workdir)
    s = summary(capsys.readouterr().out)
    assert s["adopted"] == 1 and s["added"] == 2 and len(fake.notes) == 3
    gid = gid_of(front)
    assert {"msad", f"msad-id::{gid}"} <= set(fake.notes[nid]["tags"])
    assert fake.notes[nid]["fields"]["Back"] != "old"


def test_tagged_note_in_foreign_deck_is_skipped(anki_mod, monkeypatch, fake_factory, workdir, capsys):
    fake = fake_factory()
    front = "What does exfoliative toxin cleave?"
    gid = gid_of(front)
    nid = fake.put_note("Basic", {"Front": front, "Back": "mine"}, ["msad", f"msad-id::{gid}"], "Other deck")
    write_csv(workdir)
    sync(anki_mod, monkeypatch, fake, workdir)
    s = summary(capsys.readouterr().out)
    assert s["skipped"] == 1 and s["added"] == 2
    assert fake.notes[nid]["fields"]["Back"] == "mine"
    assert all(r["params"]["note"]["id"] != nid for r in fake.calls("updateNoteFields"))


def test_note_with_a_card_in_foreign_deck_is_skipped_by_recheck(anki_mod, monkeypatch, fake_factory, workdir, capsys):
    fake = fake_factory()
    fake.decks.add(DECK)
    front = "What does exfoliative toxin cleave?"
    gid = gid_of(front)
    nid = fake.put_note("Basic", {"Front": front, "Back": "mine"}, ["msad", f"msad-id::{gid}"], DECK,
                        extra_decks=("Other deck",))
    write_csv(workdir)
    sync(anki_mod, monkeypatch, fake, workdir)
    assert summary(capsys.readouterr().out)["skipped"] == 1
    assert fake.notes[nid]["fields"]["Back"] == "mine"
    assert "cardsInfo" in fake.actions


def test_unrelated_note_in_owned_deck_is_untouched(anki_mod, monkeypatch, fake_factory, workdir):
    fake = fake_factory()
    fake.decks.add(DECK)
    nid = fake.put_note("Basic", {"Front": "My own card", "Back": "mine"}, ["personal"], DECK)
    write_csv(workdir)
    sync(anki_mod, monkeypatch, fake, workdir)
    sync(anki_mod, monkeypatch, fake, workdir)
    assert fake.notes[nid] == {"model": "Basic", "fields": {"Front": "My own card", "Back": "mine"},
                               "tags": ["personal"], "cards": fake.notes[nid]["cards"]}
    assert all(r["params"]["note"]["id"] != nid for r in fake.calls("updateNoteFields"))
    assert all(nid not in r["params"]["notes"] for r in fake.calls("addTags"))


def test_every_request_is_allowlisted_and_others_raise(anki_mod, monkeypatch, fake_factory, workdir):
    fake = fake_factory()
    write_csv(workdir)
    d = write_diagrams(workdir)
    sync(anki_mod, monkeypatch, fake, workdir, diagrams=d)
    sync(anki_mod, monkeypatch, fake, workdir, diagrams=d)
    assert set(fake.actions) <= ALLOWED
    assert all(r["version"] == 6 for r in fake.requests)
    before = len(fake.requests)
    for bad in ("multi", "deleteNotes", "deleteDecks", "guiBrowse"):
        with pytest.raises(Exception):
            anki_mod.request(fake.url, bad, {})
    assert len(fake.requests) == before


def test_diagram_notes_use_hashed_media_and_never_overwrite(anki_mod, monkeypatch, fake_factory, workdir, capsys):
    fake = fake_factory()
    fake.media["diagram.png"] = b"students own file"
    write_csv(workdir)
    d = write_diagrams(workdir)
    sync(anki_mod, monkeypatch, fake, workdir, diagrams=d)
    s = summary(capsys.readouterr().out)
    assert s["added"] == 5
    assert fake.media["diagram.png"] == b"students own file"
    stores = fake.calls("storeMediaFile")
    assert stores and all(r["params"]["deleteExisting"] is False for r in stores)
    sha = hashlib.sha256(PNG).hexdigest()[:8]
    assert len(stores) == 1  # one upload per diagram, not per label
    for r in stores:
        assert r["params"]["filename"] == f"staph-toxins-{sha}.png"
        assert base64.b64decode(r["params"]["data"]) == PNG
    io = next(n for n in fake.notes.values() if n["model"] == "Image Occlusion")
    assert io["fields"]["Occlusion"].startswith("{{c1::image-occlusion:rect:")
    assert io["fields"]["Image"] == f'<img src="staph-toxins-{sha}.png">'
    assert io["fields"]["Header"] == "S. aureus toxins"
    assert "Exfoliative toxin" in io["fields"]["Back Extra"] and "[[MICRO/Staph deck (sample)#S3]]" in html.unescape(io["fields"]["Back Extra"])
    assert f"msad-id::{IO_ID}" in io["tags"]
    # second run: updates, no new notes, no overwritten media
    sync(anki_mod, monkeypatch, fake, workdir, diagrams=d)
    assert summary(capsys.readouterr().out)["added"] == 0 and len(fake.notes) == 5


def test_bad_case_rejected_before_any_request(anki_mod, monkeypatch, fake_factory, workdir):
    fake = fake_factory()
    for bad in ('x"y', "a*b", "../etc", "Case", "a b", ""):
        with pytest.raises(SystemExit):
            run_main(anki_mod, ["--case", bad, "--url", fake.url], monkeypatch)
    assert fake.requests == []


def test_non_loopback_url_rejected(anki_mod, monkeypatch, workdir):
    with pytest.raises(SystemExit):
        run_main(anki_mod, ["--case", "case-1", "--url", "http://example.com:8765"], monkeypatch)


def test_missing_image_occlusion_model_skips_diagrams_with_hint(anki_mod, monkeypatch, fake_factory, workdir, capsys):
    fake = fake_factory(models=("Basic", "Cloze"))
    write_csv(workdir)
    d = write_diagrams(workdir)
    sync(anki_mod, monkeypatch, fake, workdir, diagrams=d)
    out = capsys.readouterr().out
    assert summary(out) == {"added": 3, "updated": 0, "adopted": 0, "skipped": 2, "weak": 0}
    assert "Open Anki > Add > Image Occlusion once, or import diagrams.apkg" in out
    assert not fake.calls("storeMediaFile")
    assert all(n["model"] != "Image Occlusion" for n in fake.notes.values())


def test_weak_spots_appended_once_across_runs(anki_mod, monkeypatch, fake_factory, workdir, capsys):
    fake = fake_factory()
    write_csv(workdir)
    d = write_diagrams(workdir)
    sync(anki_mod, monkeypatch, fake, workdir, diagrams=d)
    capsys.readouterr()
    basic = next(i for i, n in fake.notes.items() if n["fields"].get("Front", "").startswith("What does"))
    low = next(i for i, n in fake.notes.items() if n["fields"].get("Front", "").startswith("Catalase"))
    cloze = next(i for i, n in fake.notes.items() if n["model"] == "Cloze")
    io = next(i for i, n in fake.notes.items() if n["model"] == "Image Occlusion" and IO_ID in " ".join(n["tags"]))
    for nid, lapses in ((basic, 3), (low, 2), (cloze, 5), (io, 4)):
        fake.cards[fake.notes[nid]["cards"][0]]["lapses"] = lapses
    sync(anki_mod, monkeypatch, fake, workdir, diagrams=d)
    assert summary(capsys.readouterr().out)["weak"] == 3
    lines = (workdir / "weak-spots.md").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    pat = re.compile(r"- \d{4}-\d{2}-\d{2} \| [^|]+ \| [^|]+ \| (\[\[.+#[SPT]\d+\]\]|\[PMID:\d+\])")
    assert all(pat.fullmatch(line) for line in lines), lines
    text = "\n".join(lines)
    assert "| micro | What does exfoliative toxin cleave? | [[MICRO/Staph deck (sample)#S3]]" in text
    assert "| diagram | Exfoliative toxin | [[MICRO/Staph deck (sample)#S3]]" in text
    assert "Catalase" not in text and "desmoglein-1" in text
    sync(anki_mod, monkeypatch, fake, workdir, diagrams=d)
    assert summary(capsys.readouterr().out)["weak"] == 0
    assert len((workdir / "weak-spots.md").read_text(encoding="utf-8").splitlines()) == 3
    fake.cards[fake.notes[low]["cards"][0]]["lapses"] = 3
    sync(anki_mod, monkeypatch, fake, workdir, diagrams=d)
    assert summary(capsys.readouterr().out)["weak"] == 1
    assert len((workdir / "weak-spots.md").read_text(encoding="utf-8").splitlines()) == 4


def test_weak_spots_respects_threshold_option(anki_mod, monkeypatch, fake_factory, workdir, capsys):
    fake = fake_factory()
    write_csv(workdir)
    sync(anki_mod, monkeypatch, fake, workdir)
    capsys.readouterr()
    nid = next(iter(fake.notes))
    fake.cards[fake.notes[nid]["cards"][0]]["lapses"] = 1
    sync(anki_mod, monkeypatch, fake, workdir, "--threshold", "1")
    assert summary(capsys.readouterr().out)["weak"] == 1


def test_unreachable_gives_hint_and_exit_2(anki_mod, monkeypatch, workdir, capsys):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    rc = run_main(anki_mod, ["--case", "case-1", "--url", f"http://127.0.0.1:{port}"], monkeypatch)
    out = capsys.readouterr()
    assert rc == 2
    text = (out.out + out.err).strip()
    assert "2055492159" in text and "Anki" in text and len(text.splitlines()) == 1


def test_version_mismatch_is_reported(anki_mod, monkeypatch, fake_factory, workdir, capsys):
    fake = fake_factory(version=5)
    write_csv(workdir)
    rc = run_main(anki_mod, ["--case", "case-1", "--url", fake.url, "--csv", str(workdir / "flashcards.csv")], monkeypatch)
    out = capsys.readouterr()
    assert rc == 2 and "version" in (out.out + out.err).lower() and "5" in (out.out + out.err)
    assert fake.actions == ["version"]
