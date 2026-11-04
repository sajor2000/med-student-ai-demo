# /// script
# requires-python = ">=3.11"
# dependencies = ["python-pptx>=1.0", "python-docx>=1.1", "pymupdf>=1.24"]
# ///
"""Turn course materials into citable Markdown, for any school.

Supported: .pptx and .pdf (slides), .docx, .txt, .md (documents),
.vtt and .srt (lecture transcripts).

Every slide or PDF page becomes a "## [S12] Title" section so the agent can cite
"Deck name, slide 12" and a checker can confirm slide 12 exists.
Documents and transcripts become "[P34] ..." paragraph blocks (P = paragraph
anchor); transcripts get one block per ~60 s with "[mm:ss]" at the start.
PDF pages with no text layer (scanned slides) are flagged and counted.

Usage:
    uv run scripts/extract.py <input_dir> [--out notes]

Output mirrors the input folder tree under --out, plus notes/manifest.json.
Source files are never modified.
"""

from __future__ import annotations

import argparse
import codecs
import json
import re
import sys
from pathlib import Path

SKIP = {".DS_Store"}
NO_TEXT = "[no text on this page — scanned slide]"
CHUNK_SECONDS = 60
TS = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,]\d{1,3}\s*-->")
TAG = re.compile(
    r"</?(?:v|c|i|b|u|ruby|rt|rp|font|lang)(?:[.\s][^<>]*)?>"  # known subtitle tags only
    r"|<\d+:\d{2}(?::\d{2})?\.\d{1,3}>",  # inline timestamp tags
    re.I,
)
PRIORITY = [".pptx", ".pdf", ".docx", ".txt", ".md", ".vtt", ".srt"]


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
    from pptx import Presentation

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
    from docx import Document

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


# Word bullets (Symbol/Wingdings) extract as these private-use characters. The same area holds Symbol-font
# letters (beta, alpha...), so only a marker that starts a line is a bullet; one inside a line is kept.
BULLET = re.compile("^[\uf0b7\uf0a7\uf0a8\uf0d8\uf0fc]+\\s*")
RUNNING_MIN_PAGES = 3  # fewer pages cannot establish a running header or footer
EDGE_LINES = 4  # a banner or footer sits within this many lines of the top or bottom of the page


def pdf_page_lines(raw: str) -> list[str]:
    """One page's text as clean lines: private-use bullet glyphs dropped, blank lines removed."""
    return [t for t in (slug(BULLET.sub("", slug(ln))) for ln in raw.splitlines()) if t]


PAGE_NUMBER = re.compile(r"^\d+$|\b\d+\s*(?:of|/)\s*\d+\b", re.I)


def _shape(line: str) -> str:
    """A line with its page number masked, so "3 of 10 - Study Guide" and "4 of 10 - Study Guide" match."""
    return PAGE_NUMBER.sub("#", line)


def running_lines(pages: list[list[str]]) -> set[str]:
    """Edge lines repeated on at least half the pages of a 3+ page PDF: a banner or footer, not page content.

    Lines are compared with their numbers masked, so a numbered footer ("N of M - ...") counts as one running line.
    """
    if len(pages) < RUNNING_MIN_PAGES:
        return set()
    counts: dict[str, int] = {}
    for page in pages:
        for shape in {_shape(line) for line in page[:EDGE_LINES] + page[-EDGE_LINES:]}:
            counts[shape] = counts.get(shape, 0) + 1
    shapes = {shape for shape, n in counts.items() if n * 2 >= len(pages)}
    return {line for page in pages for line in page[:EDGE_LINES] + page[-EDGE_LINES:] if _shape(line) in shapes}


def pdf_to_md(path: Path) -> tuple[str, int, int]:
    import pymupdf as fitz

    lines = [f"# {path.stem}", "", f"Source: `{path.name}` (slides)", ""]
    blanks = 0
    with fitz.open(str(path)) as doc:
        pages = [pdf_page_lines(page.get_text()) for page in doc]
        running = running_lines(pages)
        for i, text in enumerate(pages, start=1):
            # The heading is the first line that is not a running banner; every line stays in the body.
            idx = next((k for k, t in enumerate(text) if t not in running), 0)
            lines.append(f"## [S{i}] {text[idx] if text else '(no text)'}")
            if text:
                lines.extend("- " + t for k, t in enumerate(text) if k != idx)
            else:
                blanks += 1
                lines.append(f"- _{NO_TEXT}_")
            lines.append("")
        n = len(doc)
    return "\n".join(lines), n, blanks


def read_text(path: Path) -> str:
    """Decode by BOM (UTF-8/16/32). No BOM means strict UTF-8, so bad bytes fail loudly."""
    data = path.read_bytes()
    for bom, enc in ((codecs.BOM_UTF32_LE, "utf-32"), (codecs.BOM_UTF32_BE, "utf-32"),
                     (codecs.BOM_UTF16_LE, "utf-16"), (codecs.BOM_UTF16_BE, "utf-16")):
        if data.startswith(bom):
            return data.decode(enc)
    return data.decode("utf-8-sig")


def text_to_md(path: Path) -> tuple[str, int]:
    raw = read_text(path)
    lines = [f"# {path.stem}", "", f"Source: `{path.name}` (document)", ""]
    n = 0
    for block in re.split(r"\n\s*\n", raw):
        t = slug(block)
        if t:
            n += 1
            lines += [f"[P{n}] {t}", ""]
    return "\n".join(lines), n


def transcript_to_md(path: Path) -> tuple[str, int]:
    """Group cues into ~60 s chunks, each a [P#] block starting with its [mm:ss]."""
    raw = read_text(path).replace("\r\n", "\n")
    chunks: list[tuple[int, list[str]]] = []
    for cue in re.split(r"\n\s*\n", raw):
        cl = cue.strip().splitlines()
        if cl and re.match(r"(NOTE|STYLE|REGION)(\s|$)", cl[0]):
            continue  # WebVTT metadata block, never transcript text
        idx = next((k for k, ln in enumerate(cl) if TS.search(ln)), None)
        if idx is None:
            continue  # WEBVTT header, NOTE, or cue number alone
        h, m, sec = TS.search(cl[idx]).groups()
        start = int(h or 0) * 3600 + int(m) * 60 + int(sec)
        text = slug(TAG.sub("", " ".join(cl[idx + 1 :])))
        if not text:
            continue
        if not chunks or start - chunks[-1][0] >= CHUNK_SECONDS:
            chunks.append((start, []))
        chunks[-1][1].append(text)
    lines = [f"# {path.stem}", "", f"Source: `{path.name}` (lecture transcript)", ""]
    for n, (start, parts) in enumerate(chunks, start=1):
        lines += [f"[P{n}] [{start // 60:02d}:{start % 60:02d}] {' '.join(parts)}", ""]
    return "\n".join(lines), len(chunks)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input_dir", type=Path)
    ap.add_argument("--out", type=Path, default=Path("notes"))
    args = ap.parse_args(argv)

    src: Path = args.input_dir.expanduser().resolve()
    if not src.is_dir():
        print(f"not a folder: {src}", file=sys.stderr)
        return 2

    args.out = args.out.expanduser()  # every later use (dest, mkdir, manifest) sees the expanded path
    out = args.out.resolve()
    fold = lambda p: [q.casefold() for q in p.parts]  # case-insensitive filesystems
    if fold(out)[: len(src.parts)] == fold(src):
        print(f"--out must not be the input folder or inside it (would overwrite sources): {out}", file=sys.stderr)
        return 2

    manifest = []
    skipped = []
    taken: set[str] = set()  # casefolded: destination notes files; macOS/Windows ignore case
    files = sorted(src.rglob("*"), key=lambda q: (PRIORITY.index(q.suffix.lower()) if q.suffix.lower() in PRIORITY else 99, str(q)))
    for path in files:
        if not path.is_file() or path.name in SKIP or path.name.startswith("~$"):
            continue
        ext = path.suffix.lower()
        rel = path.relative_to(src)
        try:
            extra: dict = {}
            if ext == ".pptx":
                md, units = pptx_to_md(path)
                kind = "slides"
            elif ext == ".pdf":
                md, units, blanks = pdf_to_md(path)
                kind = "slides"
                extra["image_only_pages"] = blanks
            elif ext in (".txt", ".md"):
                md, units = text_to_md(path)
                kind = "text"
            elif ext in (".vtt", ".srt"):
                md, units = transcript_to_md(path)
                kind = "transcript"
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
        if str(dest).casefold() in taken:  # Renal.pdf and Renal.vtt: keep both citable
            dest = dest.with_name(f"{rel.stem} ({ext[1:]}).md")
            k = 2
            while str(dest).casefold() in taken:  # fallback name itself already used
                dest = dest.with_name(f"{rel.stem} ({ext[1:]} {k}).md")
                k += 1
        taken.add(str(dest).casefold())
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(md, encoding="utf-8")
        manifest.append(
            {"source": str(rel), "notes": str(dest), "kind": kind, "units": units, "words": len(md.split()), **extra}
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
    blank = sum(f.get("image_only_pages", 0) for f in manifest)
    if blank:
        print(f"{blank} image-only PDF page(s) have no text; review those slides by hand or OCR them")
    if skipped:
        print(f"skipped {len(skipped)} (video, legacy .ppt/.doc, or unreadable):")
        for s in skipped:
            print(f"  - {s}")
    print("Course files stay in curriculum/ (gitignored). Follow your school's AI policy before sharing content with any AI tool.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
