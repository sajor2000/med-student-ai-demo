# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Check every citation in a study guide (.md) or flashcard deck (.csv).

Two citation forms are allowed (see CLAUDE.md):
  [[MICRO/Staph aureus#S3]]   course material: notes file + slide/paragraph anchor
  [PMID:12345678]             PubMed record (StatPearls chapters have PMIDs too)

What it checks:
  - every course citation points at a notes file and an anchor that exists
  - every PMID exists in PubMed (NCBI E-utilities), and prints its title so a
    human can eyeball that it is on topic
  - no PMID is flagged as a retracted publication
  - every flashcard row has at least one citation

Usage:
    uv run scripts/check.py output/study-guide.md --notes notes/rmd561-case1
    uv run scripts/check.py output/flashcards.csv --notes notes/rmd561-case1

Exit code 0 = all citations verified, 1 = problems found.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

COURSE = re.compile(r"\[\[([^\]#]+)#([SPT]\d+)\]\]")
PMID = re.compile(r"PMID:\s?(\d{4,9})")
MALFORMED: list[str] = []
ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


def pubmed_summaries(pmids: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for i in range(0, len(pmids), 150):
        batch = pmids[i : i + 150]
        params = {"db": "pubmed", "id": ",".join(batch), "retmode": "json", "tool": "med-student-ai-demo"}
        if os.environ.get("NCBI_API_KEY"):
            params["api_key"] = os.environ["NCBI_API_KEY"]
        url = ESUMMARY + "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.load(r).get("result", {})
        for pmid in batch:
            rec = data.get(pmid)
            if rec and "error" not in rec:
                out[pmid] = rec
        time.sleep(0.4)  # NCBI asks for <= 3 requests/second without a key
    return out


def anchor_exists(notes_dir: Path, rel: str, anchor: str) -> tuple[bool, str]:
    f = notes_dir / (rel.strip() + ".md")
    if not f.exists():
        return False, f"no notes file {f}"
    text = f.read_text(encoding="utf-8")
    if f"[{anchor}]" not in text:
        return False, f"{anchor} not found in {f.name}"
    return True, ""


def load_units(path: Path) -> list[tuple[str, str]]:
    """Return (label, text) pairs: one per flashcard row, or one per guide line."""
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        units = []
        for i, r in enumerate(rows, 2):
            label = f"card {i}: {(r.get('front') or '')[:50]}"
            if None in r:  # more fields than headers: an unquoted comma
                MALFORMED.append(f"{label}: extra columns (wrap text containing commas in double quotes)")
            units.append((label, " ".join(v for v in r.values() if isinstance(v, str))))
        return units
    return [(f"line {i}", line) for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", type=Path)
    ap.add_argument("--notes", type=Path, required=True, help="folder made by extract.py")
    args = ap.parse_args()

    units = load_units(args.file)
    is_deck = args.file.suffix.lower() == ".csv"
    problems: list[str] = list(MALFORMED)
    course_refs = 0
    pmids: dict[str, str] = {}

    for label, text in units:
        refs = COURSE.findall(text)
        ids = PMID.findall(text)
        if is_deck and not refs and not ids:
            problems.append(f"{label}: no citation")
        for rel, anchor in refs:
            course_refs += 1
            ok, why = anchor_exists(args.notes, rel, anchor)
            if not ok:
                problems.append(f"{label}: bad course citation [[{rel}#{anchor}]] ({why})")
        for p in ids:
            pmids.setdefault(p, label)

    found: dict[str, dict] = {}
    online = False
    if pmids:
        try:
            found = pubmed_summaries(sorted(pmids))
            online = True
        except OSError as exc:
            problems.append(f"could not reach PubMed to verify PMIDs ({exc}); rerun when online")
    for p, label in sorted(pmids.items()):
        rec = found.get(p)
        if online and not rec:
            problems.append(f"{label}: PMID:{p} does not exist in PubMed")
            continue
        if rec:
            types = [t.lower() for t in rec.get("pubtype", [])]
            if any("retract" in t for t in types):
                problems.append(f"{label}: PMID:{p} is a RETRACTED publication")
            print(f"  PMID:{p}  {rec.get('pubdate', '')[:4]}  {rec.get('title', '')[:100]}")

    kind = f"{len(units)} cards" if is_deck else "study guide"
    print(f"\n{args.file.name} ({kind}): {course_refs} course citations, {len(pmids)} PubMed citations")
    if problems:
        print(f"FAIL: {len(problems)} problem(s)")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("PASS: every citation resolves")
    return 0


if __name__ == "__main__":
    sys.exit(main())
