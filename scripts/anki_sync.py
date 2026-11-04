# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Sync verified cards into Anki desktop through AnkiConnect, and pull missed cards back.

Owned means: notes tagged `msad` + `msad-id::<id>` in the deck `AI Study::<case>` or its
`::misses` subdeck. CSV rows tagged `miss` go to `AI Study::<case>::misses` (created only
when such a row exists); other rows go to the base deck. Existing notes are updated in
place and never moved. The client talks only to a loopback AnkiConnect (API version 6),
sends only the actions in ALLOWED, and never edits a note whose cards sit outside the
owned decks (so `::diagrams-offline` stays untouched).

Inputs:
  --csv output/<case>/flashcards.csv      basic and cloze notes (same rules as export.py)
  --diagrams output/<case>/diagrams       one Image Occlusion note per label in *.occlusion.json
Outputs:
  Anki notes, and new weak spots appended to output/<case>/weak-spots.md
  (ids already appended live in output/<case>/.weak-spots-synced.json)

Usage:
    uv run scripts/anki_sync.py --case <case> [--csv ...] [--diagrams ...] [--threshold 3]
Exit codes: 0 ok, 1 AnkiConnect error, 2 not reachable / wrong version / bad arguments.
"""

from __future__ import annotations

import argparse
import base64
import csv
import datetime
import hashlib
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_VERSION = 6
ADDON_CODE = "2055492159"
ALLOWED = frozenset({
    "version", "deckNames", "createDeck", "modelNames", "findNotes", "findCards",
    "notesInfo", "cardsInfo", "addNote", "updateNoteFields", "addTags", "storeMediaFile",
})
CASE_RE = re.compile(r"^[a-z0-9-]+$")
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
IO_MODEL = "Image Occlusion"
IO_HINT = "Open Anki > Add > Image Occlusion once, or import diagrams.apkg"

PMID = re.compile(r"\[?PMID:\s?(\d{4,9})\]?")
COURSE = re.compile(r"\[\[([^\]#]+)#([SPT]\d+)\]\]")
CLOZE = re.compile(r"\{\{c(\d+)::(.*?)(?:::(.*?))?\}\}", re.S)
LABEL_SPAN = re.compile(r'title="([^"]*)">[^<]* · ([SPT]\d+)</span>')
LABEL_PMID = re.compile(r"PMID (\d{4,9})")


class AnkiError(Exception):
    pass


class Unreachable(AnkiError):
    pass


class VersionMismatch(AnkiError):
    pass


def guid(front: str) -> str:
    return "msad-" + hashlib.sha1(front.strip().lower().encode()).hexdigest()[:12]


def is_cloze(front: str) -> bool:
    return bool(CLOZE.search(front or ""))


def request(url: str, action: str, params: dict | None = None):
    """The only function that talks to AnkiConnect. Anything off the allowlist raises."""
    if action not in ALLOWED:
        raise ValueError(f"AnkiConnect action not allowed: {action}")
    body = json.dumps({"action": action, "version": API_VERSION, "params": params or {}}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=30) as resp:
            out = json.loads(resp.read())
    except (urllib.error.URLError, OSError) as e:
        raise Unreachable(str(e)) from e
    except ValueError as e:
        raise AnkiError(f"AnkiConnect returned a reply that is not JSON: {e}") from e
    if not isinstance(out, dict) or "result" not in out or "error" not in out:
        raise AnkiError("AnkiConnect returned an unexpected reply (need a JSON object with result and error)")
    if out.get("error"):
        raise AnkiError(str(out["error"]))
    return out.get("result")


def linkify_plain(text: str) -> str:
    """Citations as plain labels, as export.py writes them to the Anki files."""
    text = PMID.sub(r'<a class="cite" href="https://pubmed.ncbi.nlm.nih.gov/\1/">PMID \1</a>', text)
    return COURSE.sub(
        lambda m: f'<span class="cite course" title="{html.escape(html.unescape(m.group(1)), quote=True)}">{m.group(1)} · {m.group(2)}</span>', text
    )


def tag_list(raw: str) -> list[str]:
    return [t.strip().replace(" ", "_") for t in (raw or "").split(";") if t.strip()]


def csv_notes(path: Path, case: str = "") -> list[dict]:
    notes, seen = [], set()
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            front = (row.get("front") or "").strip()
            if not front:
                continue
            nid = guid(front)
            if nid in seen:
                continue
            seen.add(nid)
            extra = linkify_plain(html.escape(row.get("back") or "", quote=False))
            sources = "<small>" + linkify_plain(html.escape(row.get("sources") or "", quote=False)) + "</small>"
            back = f"{extra}<br>{sources}" if extra else sources
            if is_cloze(front):
                model, fields = "Cloze", {"Text": html.escape(front), "Back Extra": back}
            else:
                model, fields = "Basic", {"Front": html.escape(front), "Back": back}
            user_tags = tag_list(row.get("tags", ""))
            disc_tag = [f"msad-disc::{user_tags[1]}"] if len(user_tags) > 1 else []
            note = {"id": nid, "model": model, "fields": fields,
                    "tags": ["msad", f"msad-id::{nid}", *disc_tag, *user_tags]}
            if case and "miss" in user_tags:
                note["deck"] = f"AI Study::{case}::misses"
            notes.append(note)
    return notes


def diagram_notes(folder: Path) -> list[dict]:
    notes = []
    for f in sorted(folder.glob("*.occlusion.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        image = folder / data["image"]
        try:
            png = image.read_bytes()
        except FileNotFoundError:
            print(f"warning: {image} is missing; skipped {f.name}")
            continue
        name = f"{data['slug']}-{hashlib.sha256(png).hexdigest()[:8]}.png"
        for lab in data["labels"]:
            back = f"{html.escape(lab['label'])}<br><small>{html.escape(lab['cite'])}</small>"
            notes.append({
                "id": lab["note_id"], "model": IO_MODEL,
                "fields": {"Occlusion": lab["occlusion"], "Image": f'<img src="{name}">',
                           "Header": html.escape(data["title"]), "Back Extra": back},
                "tags": ["msad", f"msad-id::{lab['note_id']}", "diagram"],
                "media": (name, png),
            })
    return notes


class Sync:
    def __init__(self, url: str, case: str):
        self.url, self.case = url, case
        self.deck = f"AI Study::{case}"
        self.misses = f"{self.deck}::misses"
        self.owned_decks = {self.deck, self.misses}
        self.counts = {"added": 0, "updated": 0, "adopted": 0, "skipped": 0}
        self._adopt: dict[tuple[str, str], int] | None = None
        self._foreign: set[tuple[str, str]] = set()
        self._stored: set[str] = set()

    def call(self, action: str, **params):
        return request(self.url, action, params)

    def prepare(self) -> None:
        version = self.call("version")
        if version != API_VERSION:
            raise VersionMismatch(f"AnkiConnect API version {version} found, version {API_VERSION} needed: update the add-on ({ADDON_CODE})")
        if self.deck not in self.call("deckNames"):
            self.call("createDeck", deck=self.deck)

    def owned(self, nid: int) -> bool:
        cards = self.call("notesInfo", notes=[nid])[0]["cards"]
        return all(c["deckName"] in self.owned_decks for c in self.call("cardsInfo", cards=cards))

    def adoptable(self) -> dict[tuple[str, str], int]:
        """Hand-imported notes (tag `msad`, no `msad-id::`) in the owned deck, keyed by (model, guid of
        their first field). Notes without the `msad` tag are never adopted; their keys go to self._foreign."""
        if self._adopt is None:
            self._adopt = {}
            ids = self.call("findNotes", query=f'deck:"{self.deck}"')
            for n in self.call("notesInfo", notes=ids) if ids else []:
                if any(t.startswith("msad-id::") for t in n["tags"]):
                    continue
                first = {"Basic": "Front", "Cloze": "Text"}.get(n["modelName"])
                if first and first in n["fields"]:
                    text = html.unescape(re.sub(r"<br\s*/?>", "\n", n["fields"][first]["value"]))
                    # export turns CRLF into <br>, but a CSV front hashes with its raw line endings, so
                    # register both spellings; legacy IDs stay unchanged.
                    for variant in {text, text.replace("\n", "\r\n")}:
                        key = (n["modelName"], guid(variant))
                        if "msad" in n["tags"]:
                            self._adopt.setdefault(key, n["noteId"])
                        else:
                            self._foreign.add(key)
        return self._adopt

    def store_media(self, note: dict) -> None:
        name, png = note["media"]
        if name in self._stored:
            return
        self._stored.add(name)
        self.call("storeMediaFile", filename=name, data=base64.b64encode(png).decode(), deleteExisting=False)

    def upsert(self, note: dict) -> None:
        deck = note.get("deck", self.deck)
        tag = f"msad-id::{note['id']}"
        found = self.call("findNotes", query=f'deck:"{self.deck}" tag:{tag}')
        adopted = False
        if found:
            nid = found[0]
        elif note["model"] != IO_MODEL and (nid := self.adoptable().get((note["model"], note["id"]))):
            adopted = True
        elif note["model"] != IO_MODEL and (note["model"], note["id"]) in self._foreign:
            self.counts["skipped"] += 1
            print("skip: same front as a generated card but not created by this repo (left untouched)")
            return
        elif self.call("findNotes", query=f"tag:{tag}"):
            self.counts["skipped"] += 1  # tagged note lives outside the owned deck
            print(f"skip {note['id']}: note sits outside {self.deck}")
            return
        else:
            nid = None
            if deck not in self.call("deckNames"):
                self.call("createDeck", deck=deck)
        if nid is not None and not self.owned(nid):
            self.counts["skipped"] += 1
            print(f"skip {note['id']}: note has a card outside {self.deck}")
            return
        if "media" in note:
            self.store_media(note)
        if nid is None:
            self.call("addNote", note={"deckName": deck, "modelName": note["model"], "fields": note["fields"],
                                       "tags": note["tags"], "options": {"allowDuplicate": True}})
            self.counts["added"] += 1
            return
        if adopted:
            self.call("addTags", notes=[nid], tags=" ".join(note["tags"]))
            self.adoptable().pop((note["model"], note["id"]), None)
        self.call("updateNoteFields", note={"id": nid, "fields": note["fields"]})
        self.counts["adopted" if adopted else "updated"] += 1

    def lapsed(self, threshold: int) -> list[dict]:
        """Owned cards with lapses >= threshold: stable id, discipline, topic, citation."""
        card_ids = sorted({c for d in sorted(self.owned_decks)
                           for c in self.call("findCards", query=f'deck:"{d}" tag:msad')})
        cards = self.call("cardsInfo", cards=card_ids) if card_ids else []
        note_ids = sorted({c["note"] for c in cards if c["deckName"] in self.owned_decks and c["lapses"] >= threshold})
        out = []
        for n in self.call("notesInfo", notes=note_ids) if note_ids else []:
            tags = n["tags"]
            sid = next((t.split("::", 1)[1] for t in tags if t.startswith("msad-id::")), str(n["noteId"]))
            vals = {k: v["value"] for k, v in n["fields"].items()}
            if n["modelName"] == IO_MODEL:
                topic, discipline = vals.get("Back Extra", "").partition("<br")[0], "diagram"
            else:
                topic = vals.get("Front") or vals.get("Text") or ""
                discipline = next((t.split("::", 1)[1] for t in tags if t.startswith("msad-disc::")), "unknown")
            topic = clean_topic(topic)
            out.append({"id": sid, "discipline": discipline, "topic": topic, "cite": first_cite(vals)})
        return out


def clean_topic(text: str) -> str:
    text = CLOZE.sub(lambda m: m.group(2), text)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    return re.sub(r"\s+", " ", text).replace("|", "/").strip()[:120]


def first_cite(fields: dict[str, str]) -> str:
    blob = " ".join(fields.values())
    if m := COURSE.search(html.unescape(blob)):
        return f"[[{m.group(1)}#{m.group(2)}]]"
    if m := LABEL_SPAN.search(blob):
        return f"[[{html.unescape(m.group(1))}#{m.group(2)}]]"
    if m := LABEL_PMID.search(blob):
        return f"[PMID:{m.group(1)}]"
    return "[source needed]"


def append_weak_spots(case_dir: Path, items: list[dict]) -> int:
    sidecar = case_dir / ".weak-spots-synced.json"
    done: list[str] = []
    try:
        done = json.loads(sidecar.read_text(encoding="utf-8")).get("synced", [])
    except FileNotFoundError:
        pass
    seen = set(done)
    new = [i for i in items if i["id"] not in seen]
    if not new:
        return 0
    case_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    with (case_dir / "weak-spots.md").open("a", encoding="utf-8") as fh:
        for i in new:
            fh.write(f"- {today} | {i['discipline']} | {i['topic']} | {i['cite']}\n")
    tmp = sidecar.with_name(sidecar.name + ".tmp")
    tmp.write_text(json.dumps({"synced": done + [i["id"] for i in new]}, indent=1), encoding="utf-8")
    tmp.replace(sidecar)
    return len(new)


def case_name(value: str) -> str:
    if not CASE_RE.fullmatch(value):
        raise argparse.ArgumentTypeError("case must match ^[a-z0-9-]+$")
    return value


def loopback_url(value: str) -> str:
    parts = urllib.parse.urlsplit(value)
    if parts.scheme != "http" or parts.hostname not in LOOPBACK:
        raise argparse.ArgumentTypeError("only a loopback http URL is allowed (127.0.0.1, localhost, ::1)")
    return value


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", required=True, type=case_name)
    ap.add_argument("--csv", type=Path, help="output/<case>/flashcards.csv")
    ap.add_argument("--diagrams", type=Path, help="output/<case>/diagrams")
    ap.add_argument("--threshold", type=int, default=3, help="lapses that make a weak spot (default 3)")
    ap.add_argument("--url", type=loopback_url, default="http://127.0.0.1:8765")
    args = ap.parse_args()
    if args.csv and not args.csv.is_file():
        ap.error(f"no such file: {args.csv}")
    if args.diagrams and not args.diagrams.is_dir():
        ap.error(f"no such folder: {args.diagrams}")

    notes = csv_notes(args.csv, args.case) if args.csv else []
    diagrams = diagram_notes(args.diagrams) if args.diagrams else []
    s = Sync(args.url, args.case)
    try:
        s.prepare()
        for n in notes:
            s.upsert(n)
        if diagrams:
            if IO_MODEL in s.call("modelNames"):
                for n in diagrams:
                    s.upsert(n)
            else:
                s.counts["skipped"] += len(diagrams)
                print(f"Image Occlusion note type not found, diagram notes skipped. {IO_HINT}")
        weak = append_weak_spots(Path("output") / args.case, s.lapsed(args.threshold))
    except Unreachable:
        print(f"AnkiConnect not reachable at {args.url}: open Anki desktop and install add-on {ADDON_CODE}.")
        return 2
    except VersionMismatch as e:
        print(f"AnkiConnect error: {e}")
        return 2
    except AnkiError as e:
        print(f"AnkiConnect error: {e}")
        return 1
    c = s.counts
    print(f"added {c['added']}, updated {c['updated']}, adopted {c['adopted']}, "
          f"skipped {c['skipped']}, weak spots {weak}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
