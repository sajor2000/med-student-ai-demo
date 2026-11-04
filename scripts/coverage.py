# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Report which learning objectives have no tagged card and no vignette.

Objectives come from `Learning objectives: (1) ...; (2) ...` lines in any *.md under
--notes. A card covers objective N when its `tags` column (`;`-separated) holds the
exact tag `objN`; a vignette covers it through an integer `objective` field.

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
TAG_RE = re.compile(r"obj(\d+)")


def parse_objectives(notes: Path) -> dict[int, str]:
    found: dict[int, str] = {}
    for md in sorted(notes.rglob("*.md")):
        for line in md.read_text(encoding="utf-8").splitlines():
            m = LINE_RE.search(line)
            if not m:
                continue
            parts = MARK_RE.split(m.group(1))
            for num, text in zip(parts[1::2], parts[2::2]):
                found.setdefault(int(num), text.strip().rstrip(";").strip())
    return dict(sorted(found.items()))


def card_counts(path: Path) -> dict[int, int]:
    counts: dict[int, int] = {}
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            seen = set()
            for tag in (row.get("tags") or "").split(";"):
                m = TAG_RE.fullmatch(tag.strip())
                if m:
                    seen.add(int(m.group(1)))
            for n in seen:
                counts[n] = counts.get(n, 0) + 1
    return counts


def vignette_counts(path: Path) -> dict[int, int]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data["vignettes"]
        if not isinstance(items, list):
            raise TypeError
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError(f"{path}: not a vignettes file ({exc.__class__.__name__}: {exc})") from exc
    counts: dict[int, int] = {}
    for v in items:
        n = v.get("objective") if isinstance(v, dict) else None
        if isinstance(n, int) and not isinstance(n, bool):
            counts[n] = counts.get(n, 0) + 1
    return counts


def plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def existing(value: str) -> Path:
    p = Path(value)
    if not p.exists():
        raise argparse.ArgumentTypeError(f"path does not exist: {value}")
    return p


def main() -> int:
    ap = argparse.ArgumentParser(description="Report learning objectives with no card or vignette.")
    ap.add_argument("--notes", type=existing, required=True, help="notes folder, e.g. notes/<case>")
    ap.add_argument("--csv", type=existing, help="flashcards.csv with objN tags")
    ap.add_argument("--vignettes", type=existing, help="vignettes.json with objective fields")
    args = ap.parse_args()

    objectives = parse_objectives(args.notes)
    if not objectives:
        print("no objectives found")
        return 0
    try:
        cards = card_counts(args.csv) if args.csv else {}
        vigs = vignette_counts(args.vignettes) if args.vignettes else {}
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    open_count = 0
    for n, text in objectives.items():
        how = []
        if cards.get(n):
            how.append(plural(cards[n], "card"))
        if vigs.get(n):
            how.append(plural(vigs[n], "vignette"))
        status = f"covered ({', '.join(how)})" if how else "UNCOVERED"
        open_count += not how
        print(f"({n}) {text}: {status}")
    print("all objectives covered" if not open_count else f"{open_count} objective(s) uncovered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
