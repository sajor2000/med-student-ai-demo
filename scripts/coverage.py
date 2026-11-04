# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Report which learning objectives have no tagged card and no vignette.

Objectives come from `Learning objectives: (1) ...; (2) ...` lines in any *.md under
--notes. A card covers objective N when its `tags` column (`;`-separated) holds the
exact tag `objN`; a vignette covers it through an integer `objective` field. Objectives are kept
per notes file: when two lectures both number (1)-(3), tag cards `<lecture-slug>-objN` (slug = the
notes path under --notes without `.md`, lowercased, non-alphanumerics as `-`, e.g.
`micro-staphylococcus-aureus-sample-lecture-obj2`)
and add `"lecture": "<slug>"` to vignettes. A plain `objN` only counts when one lecture defines N.

Usage:
    uv run scripts/coverage.py --notes notes/<case> [--csv flashcards.csv] [--vignettes vignettes.json]
Exit codes: 0 report printed (gaps do not fail), 2 bad arguments or malformed vignettes JSON.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

LINE_RE = re.compile(r"Learning objectives:\s*(.*)", re.IGNORECASE)
MARK_RE = re.compile(r"\((\d+)\)")
TAG_RE = re.compile(r"(?:([a-z0-9-]+)-)?obj(\d+)")
Key = tuple[str, int]  # (lecture slug, objective number); slug "" means unqualified


def lecture_slug(md: Path, notes: Path) -> str:
    """Slug of the notes path without `.md` (so MICRO/Lecture 1 and PHARM/Lecture 1 differ)."""
    rel = md.relative_to(notes).with_suffix("").as_posix()
    return re.sub(r"[^a-z0-9]+", "-", rel.lower()).strip("-")


def parse_objectives(notes: Path) -> dict[Key, str]:
    """Objectives keyed by (notes file slug, number), so two lectures can each number (1)-(3)."""
    found: dict[Key, str] = {}
    owner: dict[str, Path] = {}
    for md in sorted(notes.rglob("*.md")):
        slug = lecture_slug(md, notes)
        if owner.setdefault(slug, md) != md:
            raise ValueError(f"{md} and {owner[slug]} give the same lecture slug {slug!r}; rename one")
        for line in md.read_text(encoding="utf-8").splitlines():
            m = LINE_RE.search(line)
            if not m:
                continue
            parts = MARK_RE.split(m.group(1))
            for num, text in zip(parts[1::2], parts[2::2]):
                found.setdefault((slug, int(num)), text.strip().rstrip(";").strip())
    return dict(sorted(found.items(), key=lambda kv: (kv[0][0], kv[0][1])))


def card_counts(path: Path) -> dict[Key, int]:
    counts: dict[Key, int] = {}
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            seen = set()
            for tag in (row.get("tags") or "").split(";"):
                m = TAG_RE.fullmatch(tag.strip())
                if m:
                    seen.add((m.group(1) or "", int(m.group(2))))
            for key in seen:
                counts[key] = counts.get(key, 0) + 1
    return counts


def vignette_counts(path: Path) -> dict[Key, int]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data["vignettes"]
        if not isinstance(items, list):
            raise TypeError
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError(f"{path}: not a vignettes file ({exc.__class__.__name__}: {exc})") from exc
    counts: dict[Key, int] = {}
    for i, v in enumerate(items, 1):
        if not isinstance(v, dict):
            raise ValueError(f"{path}: vignette #{i} is not an object")
        n = v.get("objective")
        if n is None:
            continue
        if not isinstance(n, int) or isinstance(n, bool) or n < 1:
            raise ValueError(f"{path}: vignette #{i} needs an objective that is an integer of 1 or more, not {n!r}")
        lecture = v.get("lecture") if isinstance(v.get("lecture"), str) else ""
        counts[(lecture, n)] = counts.get((lecture, n), 0) + 1
    return counts


def plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def existing(value: str, kind: str = "any") -> Path:
    p = Path(value)
    if not p.exists():
        raise argparse.ArgumentTypeError(f"path does not exist: {value}")
    if kind == "dir" and not p.is_dir():
        raise argparse.ArgumentTypeError(f"not a directory: {value}")
    if kind == "file" and not p.is_file():
        raise argparse.ArgumentTypeError(f"not a file: {value}")
    return p


def existing_dir(value: str) -> Path:
    return existing(value, "dir")


def existing_file(value: str) -> Path:
    return existing(value, "file")


def csv_path(value: str) -> Path:
    p = Path(value)
    if p.is_dir():
        raise argparse.ArgumentTypeError(f"not a file: {value}")
    return p


def main() -> int:
    ap = argparse.ArgumentParser(description="Report learning objectives with no card or vignette.")
    ap.add_argument("--notes", type=existing_dir, required=True, help="notes folder, e.g. notes/<case>")
    ap.add_argument("--csv", type=csv_path, help="flashcards.csv with objN tags (a missing file counts as 0 cards)")
    ap.add_argument("--vignettes", type=existing_file, help="vignettes.json with objective fields")
    args = ap.parse_args()

    try:
        objectives = parse_objectives(args.notes)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not objectives:
        print("no objectives found")
        return 0
    try:
        if args.csv and not args.csv.exists():
            print(f"note: {args.csv} does not exist yet; counting 0 cards")
        cards = card_counts(args.csv) if args.csv and args.csv.exists() else {}
        vigs = vignette_counts(args.vignettes) if args.vignettes else {}
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    slugs = {slug for slug, _ in objectives}
    owners: dict[int, list[str]] = {}
    for slug, n in objectives:
        owners.setdefault(n, []).append(slug)
    # An unqualified objN is only unambiguous when one lecture defines N.
    ambiguous = {n for n, who in owners.items() if len(who) > 1}
    for n in sorted(ambiguous):
        if cards.get(("", n)) or vigs.get(("", n)):
            names = ", ".join(f"{slug}-obj{n}" for slug in owners[n])
            print(f"warning: obj{n} is ambiguous (lectures {', '.join(owners[n])}); use {names}")

    open_count = 0
    for (slug, n), text in objectives.items():
        def hits(counts: dict[Key, int]) -> int:
            return counts.get((slug, n), 0) + (0 if n in ambiguous else counts.get(("", n), 0))

        how = []
        if hits(cards):
            how.append(plural(hits(cards), "card"))
        if hits(vigs):
            how.append(plural(hits(vigs), "vignette"))
        status = f"covered ({', '.join(how)})" if how else "UNCOVERED"
        open_count += not how
        label = f"[{slug}] " if len(slugs) > 1 else ""
        print(f"{label}({n}) {text}: {status}")
    print("all objectives covered" if not open_count else f"{open_count} objective(s) uncovered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
