# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Check every citation in a study guide (.md), flashcard deck (.csv), diagram
spec (.json), or vignette file (.json).

Two citation forms are allowed (see AGENTS.md):
  [[MICRO/Staph aureus#S3]]   course material: notes file + slide/paragraph anchor
  [PMID:12345678]             PubMed record (StatPearls chapters have PMIDs too)

What it checks:
  - every course citation points at a notes file and an anchor that exists
  - every PMID exists in PubMed (NCBI E-utilities), and prints its title so a
    human can eyeball that it is on topic
  - no PMID is flagged as a retracted publication
  - every flashcard row has at least one citation
  - cloze cards (Anki markup `{{c1::answer}}` or `{{c1::answer::hint}}` in the
    front) are well formed: closed, numbered, and not empty. A cloze card's
    back is optional.
  - every study-guide bullet, numbered item, and table row has a citation,
    `[source needed]` (reported as a warning), or an `(AI mnemonic)` /
    `(AI analogy)` label. The Self-test section is exempt.
  - a diagram spec (.json: title, nodes, edges) has unique valid ids, edges that
    join existing nodes, and a citation on every node and every labeled edge
  - a vignette file (.json whose top level has a `vignettes` key) has unique
    valid ids, a non-empty stem, exactly 5 options keyed A-E with exactly one
    correct, an integer `objective` of 1 or more when present, a cited
    explanation on every option, and no patient-identifier shapes (MRN-like
    numbers, dates, a name with an age) in the stem, options or explanations.
    Any other .json is checked as a diagram spec.
  - a citation into an output/ or art/ folder is always unresolved: AI
    illustrations are memory aids, not sources

What PASS does NOT mean: that the source actually says what the card says.
Open one or two cited slides/PMIDs and compare before you study a deck.

Usage:
    uv run scripts/check.py output/study-guide.md --notes notes/rmd561-case1
    uv run scripts/check.py output/flashcards.csv --notes notes/rmd561-case1

Exit code 0 = all citations verified, 1 = problems found.
"""

from __future__ import annotations

import argparse
import csv
import functools
import json
import os
import posixpath
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

COURSE = re.compile(r"\[\[([^\]#]+)#([SPT]\d+)\]\]")
FACT_LINE = re.compile(r"^\s*(?:[-*+]\s|\d+\.\s|\|)")
TABLE_SEP = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
AI_LABEL = re.compile(r"\(AI (?:mnemonic|analogy)\)", re.I)
PMID = re.compile(r"PMID:\s*(\d{4,9})")  # any whitespace, incl. a CRLF line break
CLOZE_START = re.compile(r"\{\{c(?:\d|:)")  # a cloze prefix, not ordinary text like {{class}}
CLOZE_BODY = re.compile(r"^c(\d+)::(.*?)(?:::(.*))?$", re.S)


def cloze_problems(text: str) -> list[str]:
    """Describe every malformed cloze deletion in `text` (empty list = well formed)."""
    problems = []
    pos = 0
    while m := CLOZE_START.search(text, pos):
        end = text.find("}}", m.start())
        if end == -1:
            problems.append("cloze deletion is not closed with }}")
            break
        body = CLOZE_BODY.match(text[m.start() + 2 : end])
        if not body:
            problems.append("cloze deletion needs a number, like {{c1::answer}}")
        elif not body.group(2).strip():
            problems.append("cloze deletion is empty")
        pos = end + 2
    return problems


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


# Deliberate copy of PHI_PATTERNS, NAME_ALLOW, and name_hit in mnemonic_art.py: each script stays standalone,
# and tests/test_check.py asserts the two stay in sync (apart from the vital-sign exclusion on "Name, 38 C").
PHI_PATTERNS = [
    (re.compile(r"\d{6,}"), "a number with 6 or more digits (MRN-like)"),
    (re.compile(r"\b(?:MRN|DOB)\b|date\s+of\s+birth|medical\s+record", re.I), "MRN or date-of-birth wording"),
    (re.compile(r"\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b"), "a date"),
    (re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b"
                r"|\b\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?,?\s+\d{4}\b"), "a date"),
    (re.compile(r"\b(?:born|dob)\b[^.]{0,20}\b(?:19|20)\d{2}\b", re.I), "a birth year"),
    (re.compile(r"\b[A-Z][a-z]+(?:,\s*(?!\d{1,3}\s*(?:bpm|mm|mg|mL|ml|kg|cm|lb|%|°|[CF]\b|breaths|/min|mEq|U/L|g/dL))|,?\s+aged?\s+)\d{1,3}\b"), "a name with an age"),
    (re.compile(r"\b\d{1,3}[- ]years?[- ]old\s+(?:named|called)\b", re.I), "a name with an age"),
    # De-identification gate (heuristic, fail closed): contact details and locators.
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "an email address"),
    (re.compile(r"(?<![\w-])(?:\+?1[\s.-]?)?(?:\(\d{3}\)\s?|\d{3}[\s.-])\d{3}[\s.-]\d{4}(?![\w-])"), "a phone number"),
    (re.compile(r"(?<![\w-])\d{3}[- ]\d{2}[- ]\d{4}(?![\w-])"), "an SSN-like number"),
    (re.compile(r"\b\d{1,6}\s+(?:[A-Za-z]+\s+){0,3}(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|"
                r"Ln|Lane|Ct|Court|Way|Pl|Place|Pkwy|Parkway|Hwy|Highway)\b\.?", re.I), "a street address"),
    (re.compile(r"#\s*\d{4,}|\b(?:chart|account|acct|patient|pt|record)\s*(?:no\.?|number|id|#)?\s*[:#]?\s*\d{4,}\b",
                re.I), "an MRN-like identifier"),
    (re.compile(r"(?<![\d-])\d{5}(?:-\d{4})?(?![\d-])"), "a ZIP code"),
    (re.compile(r"\b(?:https?://|www\.)\S*\?\S+", re.I), "a URL with a query string"),
    (re.compile(r"\b(?:Mr|Mrs|Ms|Miss|Dr|Patient)\b\.?\s+[A-Z][a-z]+"), "a title followed by a name"),
    # all-caps names: after a personal title, or two all-caps words after "Patient" (so "Patient COPD" is not refused)
    (re.compile(r"\b(?:Mr|Mrs|Ms|Miss|Dr|MR|MRS|MS|MISS|DR)\b\.?\s+[A-Z]{2,}\b|\b(?i:patient)\s+[A-Z]{3,}(?:\s+[A-Z]{3,})+"),
     "a title followed by a name"),
]


# Title-Case words that are medical or scientific terms (eponyms, genera, units of naming), not people.
NAME_ALLOW = frozenset(w.lower() for w in """
Graves Hashimoto Cushing Addison Crohn Lyme Staphylococcus Streptococcus Borrelia Gram Type Vitamin Staph Strep
Parkinson Alzheimer Huntington Down Turner Klinefelter Marfan Ehlers Danlos Kawasaki Wilson Raynaud Sjogren
Hodgkin Burkitt Epstein Barr Guillain Barre Bell Paget Hirschsprung Meniere Reye Zika Ebola Salmonella Escherichia
Pseudomonas Klebsiella Neisseria Clostridium Clostridioides Candida Aspergillus Mycobacterium Helicobacter
Chlamydia Treponema Plasmodium Giemsa Ziehl Neelsen Wright Coombs Babinski Murphy Virchow Beck Cheyne Stokes
Kussmaul Trousseau Chvostek Osler Janeway Roth Charcot Horner Wernicke Korsakoff Mallory Weiss Barrett Zenker
Meckel Wolff Parkinson White Brugada Lewy Pick Creutzfeldt Jakob Tay Sachs Gaucher Fabry Pompe Niemann Hurler
Hunter Duchenne Becker Rh Factor Toxic Shock Acute Chronic Myocardial Infarction Congestive Heart Failure
Respiratory Distress Pulmonary Embolism Cardiac Arrest Renal Kidney Liver Septic Diabetes Mellitus Insipidus Multiple
Sclerosis Systemic Lupus Erythematosus Rheumatoid Arthritis Deep Vein Thrombosis Urinary Tract Infection Chronic
Obstructive Disease Hypertension Atrial Fibrillation Sickle Anemia Vitamin Group Stage Grade Class Phase Day Week Month Year Case Cell Cells
Island Islet Islets Bundle Node Valve Nerve Artery Vein Lobe Gland Cortex Syndrome Disease Law Test Sign Triad
Tetralogy Pentad Reflex Cycle Krebs Calvin Golgi Purkinje Schwann Kupffer Langerhans Leydig Sertoli Meissner
Pacinian Ruffini Merkel Broca Brodmann Wernicke Heimlich Valsalva Glasgow Apgar Ringer Hartmann Foley Swan Ganz
The A An In On At Of To For And Or But With From By As If When While Then This That These Those It Its He She
They We You I My Our Your One Two Three Four Five Each Every Some Any No Not Is Are Was Were Be
""".split())
GENERIC_WORDS = frozenset(w.lower() for w in """
Type Vitamin Group Stage Grade Class Phase Day Week Month Year Case Cell Cells Island Islet Islets Bundle Node Valve
Nerve Artery Vein Lobe Gland Cortex Syndrome Disease Law Test Sign Triad Tetralogy Pentad Reflex Cycle Factor Rh
The A An In On At Of To For And Or But With From By As If When While Then This That These Those It Its He She
They We You I My Our Your One Two Three Four Five Each Every Some Any No Not Is Are Was Were Be
""".split())
_CAP_RUN = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b")


def name_hit(text: str) -> str | None:
    """Two or more Title-Case words in a row, none of them a known medical or common term."""
    for m in _CAP_RUN.finditer(text):
        words = m.group(0).split()
        # A known medical word first ("Wilson Disease", "Gram Positive") is clinical. An unknown first word
        # ("Jane Wilson", "John Smith Type") followed by anything but a generic word reads as a name,
        # even when the second word happens to be an eponym surname.
        # Words that continue a clinical phrase ("Gram Positive Staphylococcus") are not name candidates.
        for i, (a, b) in enumerate(zip(words, words[1:], strict=False)):
            if i and words[i - 1].lower() in NAME_ALLOW:
                continue
            if a.lower() not in NAME_ALLOW and b.lower() not in GENERIC_WORDS:
                return "a likely personal name"
    return None


def phi_hit(*texts: str) -> str | None:
    for text in texts:
        text = PMID.sub(" ", COURSE.sub(" ", text))  # citation tokens are not patient identifiers
        for rx, what in PHI_PATTERNS:
            if rx.search(text):
                return what
        if hit := name_hit(text):
            return hit
    return None


ART_WHY = "AI illustrations are memory aids, not sources"
ID_OK = re.compile(r"[a-z0-9-]{1,40}")


def _norm_cite_path(rel: str) -> str:
    return posixpath.normpath(rel.strip().replace("\\", "/"))


def is_art_path(rel: str) -> bool:
    """True for a citation path inside an output or art folder (AI illustrations are never sources)."""
    parts = _norm_cite_path(rel).split("/")
    return parts[0] == "output" or "art" in parts[:-1]


def escapes_notes(rel: str) -> bool:
    """True for a normalized citation path that climbs out of the notes folder or names output/art."""
    norm = _norm_cite_path(rel)
    parts = norm.split("/")
    return norm.startswith("..") or posixpath.isabs(norm) or "output" in parts or "art" in parts


@functools.lru_cache(maxsize=None)
def read_notes(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def anchor_exists(notes_dir: Path, rel: str, anchor: str) -> tuple[bool, str]:
    if is_art_path(rel):
        return False, ART_WHY
    outside = "points outside the notes folder"
    if escapes_notes(rel):
        return False, outside
    f = notes_dir / (_norm_cite_path(rel) + ".md")
    if not f.resolve().is_relative_to(notes_dir.resolve()):
        return False, outside
    text = read_notes(f)
    if text is None:
        return False, f"no notes file {f}"
    if f"[{anchor}]" not in text:
        return False, f"{anchor} not found in {f.name}"
    return True, ""


def load_units(path: Path) -> tuple[list[tuple[str, str]], list[str]]:
    """Return ((label, text) pairs, structural problems): one pair per card row or guide line."""
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        units, problems = [], []
        for i, r in enumerate(rows, 2):
            front = r.get("front") or ""
            label = f"card {i}: {front[:50]}"
            if None in r:  # more fields than headers: an unquoted comma
                problems.append(f"{label}: extra columns (wrap text containing commas in double quotes)")
            problems.extend(f"{label}: {p}" for p in cloze_problems(front))
            units.append((label, " ".join(v for v in r.values() if isinstance(v, str))))
        return units, problems
    lines = path.read_text(encoding="utf-8").splitlines()
    return [(f"line {i}", line) for i, line in enumerate(lines, 1)], []


def uncited_guide_lines(path: Path) -> tuple[list[str], list[str]]:
    """Return (uncited factual lines, [source needed] lines) for a Markdown guide."""
    lines = path.read_text(encoding="utf-8").splitlines()
    uncited, needed = [], []
    section, in_code = "", False
    for i, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if line.startswith("#"):
            section = line.lower()
            continue
        if "self-test" in section or not FACT_LINE.match(line):
            continue
        nxt = lines[i] if i < len(lines) else ""
        if TABLE_SEP.match(line) or (line.lstrip().startswith("|") and TABLE_SEP.match(nxt)):
            continue  # table separator or header row
        if COURSE.search(line) or PMID.search(line) or AI_LABEL.search(line):
            continue
        if "[source needed]" in line.lower():
            needed.append(f"line {i}: {line.strip()[:70]}")
        else:
            uncited.append(f"line {i}: uncited: {line.strip()[:70]}")
    return uncited, needed


def has_citation(text: str) -> bool:
    return bool(COURSE.search(text) or PMID.search(text))


def spec_units(path: Path) -> tuple[list[tuple[str, str]], list[str], str]:
    """Validate a diagram spec: ((label, cite text) pairs, structural problems, summary)."""
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return [], [f"not valid JSON ({exc})"], "diagram spec"
    if not isinstance(spec, dict):
        return [], ["diagram spec must be a JSON object with title, nodes, and edges"], "diagram spec"
    problems: list[str] = []
    if not str(spec.get("title") or "").strip():
        problems.append("spec needs a non-empty title")
    nodes, edges = spec.get("nodes"), spec.get("edges", [])
    if not isinstance(nodes, list) or not nodes:
        problems.append("spec needs a non-empty list of nodes")
        nodes = []
    if not isinstance(edges, list):
        problems.append("edges must be a list")
        edges = []
    units: list[tuple[str, str]] = []
    seen: set[str] = set()
    node_ids: set[str] = set()

    def check_id(kind: str, i: int, item: dict) -> str:
        ident = item.get("id")
        name = f"{kind} {ident!r}" if isinstance(ident, str) and ident else f"{kind} #{i}"
        if not isinstance(ident, str) or not ID_OK.fullmatch(ident):
            problems.append(f"{name}: invalid id (use 1-40 chars of a-z, 0-9, -)")
        elif ident in seen:
            problems.append(f"{name}: duplicate id")
        else:
            seen.add(ident)
        return name

    for i, n in enumerate(nodes, 1):
        if not isinstance(n, dict):
            problems.append(f"node #{i}: must be an object")
            continue
        name = check_id("node", i, n)
        if isinstance(n.get("id"), str):
            node_ids.add(n["id"])
        if "label" in n and not isinstance(n["label"], str):
            problems.append(f"{name}: label must be a string")
        elif not str(n.get("label") or "").strip():
            problems.append(f"{name}: missing label")
        cite = n.get("cite") or ""
        if not isinstance(cite, str):
            problems.append(f"{name}: cite must be a string")
            cite = ""
        if not has_citation(cite):
            problems.append(f"{name}: no citation")
        units.append((name, cite))
    for i, e in enumerate(edges, 1):
        if not isinstance(e, dict):
            problems.append(f"edge #{i}: must be an object")
            continue
        name = check_id("edge", i, e)
        for end in ("from", "to"):
            target = e.get(end)
            if not isinstance(target, str) or target not in node_ids:
                problems.append(f"{name}: {end} {e.get(end)!r} is not a node id")
        cite = e.get("cite") or ""
        if not isinstance(cite, str):
            problems.append(f"{name}: cite must be a string")
            cite = ""
        if "label" in e and not isinstance(e["label"], str):
            problems.append(f"{name}: label must be a string")
        elif str(e.get("label") or "").strip() and not has_citation(cite):
            problems.append(f"{name}: labeled edge has no citation")
        units.append((name, cite))
    # De-identification gate: every free-text string (title, labels, notes, any other field), fail closed.
    # Everything is scanned, citations and ids included (phi_hit already ignores well-formed PMID and course tokens).
    def free_text(value: object, key: str = "") -> list[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, dict):
            return [t for k, v in value.items() for t in free_text(v, str(k))]
        if isinstance(value, list):
            return [t for v in value for t in free_text(v, key)]
        return []

    # phi_hit ignores well-formed course tokens. A citation path names a notes file the student ingested
    # (case guides are named after the fictional case patient, e.g. "... Jordan Rivera"), so it is not
    # scanned as free text; a path that matches no notes file fails the citation check below instead.
    texts = free_text(spec)
    for text in texts:
        if what := phi_hit(text):
            problems.append(f"diagram text looks like PHI ({what}); de-identify before it goes in a diagram")
            break
    return units, problems, f"{len(nodes)} nodes, {len(edges)} edges"


def vignette_units(path: Path) -> tuple[list[tuple[str, str]], list[str], str]:
    """Validate a vignette file: ((label, cite text) pairs, structural problems, summary)."""
    summary = "vignettes"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return [], [f"not valid JSON ({exc})"], summary
    items = data.get("vignettes") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        return [], ["`vignettes` must be a non-empty list"], summary
    problems: list[str] = []
    units: list[tuple[str, str]] = []
    seen: set[str] = set()
    for i, v in enumerate(items, 1):
        if not isinstance(v, dict):
            problems.append(f"vignette #{i}: must be an object")
            continue
        vid = v.get("id")
        name = f"vignette {vid!r}" if isinstance(vid, str) and vid else f"vignette #{i}"
        if not isinstance(vid, str) or not ID_OK.fullmatch(vid):
            problems.append(f"{name}: invalid id (use 1-40 chars of a-z, 0-9, -)")
        elif vid in seen:
            problems.append(f"{name}: duplicate id")
        else:
            seen.add(vid)
        obj = v.get("objective")
        if "objective" in v and (not isinstance(obj, int) or isinstance(obj, bool) or obj < 1):
            problems.append(f"{name}: objective must be an integer of 1 or more")
        stem = v.get("stem")
        if not isinstance(stem, str) or not stem.strip():
            problems.append(f"{name}: stem is missing or empty")
            stem = ""
        if what := phi_hit(stem):
            problems.append(f"{name}: stem contains {what}")
        units.append((f"{name} stem", stem))
        if what := phi_hit(str(v.get("discipline") or "")):
            problems.append(f"{name}: discipline contains {what}")
        opts = v.get("options")
        if not isinstance(opts, list) or len(opts) != 5:
            problems.append(f"{name}: needs exactly 5 options (A-E)")
            opts = opts if isinstance(opts, list) else []
        keys = [o.get("key") for o in opts if isinstance(o, dict)]
        if len(opts) == 5 and sorted(map(str, keys)) != list("ABCDE"):
            problems.append(f"{name}: option keys must be A, B, C, D, E once each")
        if sum(1 for o in opts if isinstance(o, dict) and o.get("correct") is True) != 1:
            problems.append(f"{name}: exactly one correct option is required")
        for j, o in enumerate(opts, 1):
            if not isinstance(o, dict):
                problems.append(f"{name}: option #{j} must be an object")
                continue
            oname = f"{name} option {o.get('key') if isinstance(o.get('key'), str) else '#' + str(j)}"
            text, expl = o.get("text"), o.get("explanation")
            if not isinstance(text, str) or not text.strip():
                problems.append(f"{oname}: text is missing or empty")
                text = ""
            if not isinstance(expl, str) or not expl.strip():
                problems.append(f"{oname}: explanation is missing or empty")
                expl = ""
            elif not has_citation(expl):
                problems.append(f"{oname}: explanation has no citation")
            for part, t in (("text", text), ("explanation", expl)):
                if what := phi_hit(t):
                    problems.append(f"{oname}: {part} contains {what}")
            units.append((f"{oname} text", text))
            units.append((f"{oname} explanation", expl))
    return units, problems, f"{len(items)} vignettes"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", type=Path)
    ap.add_argument("--notes", type=Path, required=True, help="folder made by extract.py")
    args = ap.parse_args()

    if not args.file.is_file():
        print(f"FAIL: no such file {args.file}")
        return 1
    is_spec = args.file.suffix.lower() == ".json"
    if is_spec:
        try:
            top = json.loads(args.file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            top = None
        if isinstance(top, dict) and "vignettes" in top:
            units, problems, summary = vignette_units(args.file)
        else:
            units, problems, summary = spec_units(args.file)
    else:
        units, problems = load_units(args.file)
    is_deck = args.file.suffix.lower() == ".csv"
    course_refs = 0
    pmids: dict[str, str] = {}
    needed: list[str] = []
    if not is_deck and not is_spec:
        uncited, needed = uncited_guide_lines(args.file)
        problems.extend(uncited)

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

    kind = summary if is_spec else f"{len(units)} cards" if is_deck else "study guide"
    print(f"\n{args.file.name} ({kind}): {course_refs} course citations, {len(pmids)} PubMed citations")
    for n in needed:
        print(f"  WARN [source needed] {n}")
    if problems:
        print(f"FAIL: {len(problems)} problem(s)")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("PASS: every citation resolves" + ("" if is_deck or is_spec else " and every fact line is cited"))
    print("Next: spot-check 2-3 citations yourself. PASS means the sources exist, not that they support the claim.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
