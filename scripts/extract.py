# /// script
# requires-python = ">=3.11"
# dependencies = ["python-pptx>=1.0", "python-docx>=1.1"]
# ///
"""Turn course slides (.pptx) and guides (.docx) into citable Markdown.

Every slide becomes a "## [S12] Title" section so the agent can cite
"Deck name, slide 12" and a checker can confirm slide 12 exists.
Word guides become "## [P34] ..." blocks (P = paragraph anchor).

Usage:
    uv run scripts/extract.py <input_dir> [--out notes]

Output mirrors the input folder tree under --out, plus notes/manifest.json.
Source files are never modified.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from docx import Document
from pptx import Presentation
from pptx.util import Emu  # noqa: F401  (keeps pptx type registry loaded)

SKIP = {".DS_Store"}


def slug(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def shape_text(shape) -> list[str]:
    out: list[str] = []
    if getattr(shape, "has_text_frame", False) and shape.has_text_frame:
        for p in shape.text_frame.paragraphs:
            t = slug("".join(r.text for r in p.runs))
            if t:
                out.append(("  " * p.level) + "- " + t)
    if getattr(shape, "has_table", False) and shape.has_table:
        for row in shape.table.rows:
            cells = [slug(c.text) for c in row.cells]
            out.append("| " + " | ".join(cells) + " |")
    if shape.shape_type == 6:  # group
        for s in shape.shapes:
            out.extend(shape_text(s))
    return out


def pptx_to_md(path: Path) -> tuple[str, int]:
    prs = Presentation(str(path))
    lines = [f"# {path.stem}", "", f"Source: `{path.name}` (slides)", ""]
    for i, slide in enumerate(prs.slides, start=1):
        title = ""
        if slide.shapes.title is not None and slide.shapes.title.has_text_frame:
            title = slug(slide.shapes.title.text_frame.text)
        lines.append(f"## [S{i}] {title or '(untitled slide)'}")
        body: list[str] = []
        for shape in slide.shapes:
            if slide.shapes.title is not None and shape.shape_id == slide.shapes.title.shape_id:
                continue
            body.extend(shape_text(shape))
        n_pics = sum(1 for s in slide.shapes if s.shape_type == 13)
        if n_pics:
            body.append(f"- _[{n_pics} image(s) on slide; not extracted]_")
        lines.extend(body or ["- _(no text)_"])
        if slide.has_notes_slide:
            notes = slug(slide.notes_slide.notes_text_frame.text)
            if notes:
                lines += ["", f"> Speaker notes: {notes}"]
        lines.append("")
    return "\n".join(lines), len(prs.slides)


def docx_to_md(path: Path) -> tuple[str, int]:
    doc = Document(str(path))
    lines = [f"# {path.stem}", "", f"Source: `{path.name}` (document)", ""]
    n = 0
    for para in doc.paragraphs:
        t = slug(para.text)
        if not t:
            continue
        n += 1
        style = (para.style.name or "").lower()
        if style.startswith("heading"):
            lines.append(f"## [P{n}] {t}")
        else:
            lines.append(f"[P{n}] {t}")
        lines.append("")
    for ti, table in enumerate(doc.tables, start=1):
        lines.append(f"## [T{ti}] Table {ti}")
        for row in table.rows:
            lines.append("| " + " | ".join(slug(c.text) for c in row.cells) + " |")
        lines.append("")
    return "\n".join(lines), n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input_dir", type=Path)
    ap.add_argument("--out", type=Path, default=Path("notes"))
    args = ap.parse_args()

    src: Path = args.input_dir.expanduser().resolve()
    if not src.is_dir():
        print(f"not a folder: {src}", file=sys.stderr)
        return 2

    manifest = []
    skipped = []
    for path in sorted(src.rglob("*")):
        if not path.is_file() or path.name in SKIP or path.name.startswith("~$"):
            continue
        ext = path.suffix.lower()
        rel = path.relative_to(src)
        try:
            if ext == ".pptx":
                md, units = pptx_to_md(path)
                kind = "slides"
            elif ext == ".docx":
                md, units = docx_to_md(path)
                kind = "document"
            else:
                skipped.append(str(rel))
                continue
        except Exception as exc:  # corrupt or password-protected file
            skipped.append(f"{rel} (error: {exc.__class__.__name__})")
            continue
        dest = args.out / rel.with_suffix(".md")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(md, encoding="utf-8")
        manifest.append(
            {"source": str(rel), "notes": str(dest), "kind": kind, "units": units, "words": len(md.split())}
        )

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "manifest.json").write_text(
        json.dumps({"input": str(args.input_dir), "files": manifest, "skipped": skipped}, indent=2), encoding="utf-8"
    )
    words = sum(f["words"] for f in manifest)
    print(f"extracted {len(manifest)} files ({words:,} words) -> {args.out}/")
    for f in manifest:
        unit = "slides" if f["kind"] == "slides" else "paragraphs"
        print(f"  {f['units']:>4} {unit:<10} {f['source']}")
    if skipped:
        print(f"skipped {len(skipped)} (video, legacy .ppt, or unreadable):")
        for s in skipped:
            print(f"  - {s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
