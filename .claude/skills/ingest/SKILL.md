---
name: ingest
description: Extract a folder of course slides/guides into citable Markdown notes and summarize what the case covers. Use first, before any study guide, flashcards, or quiz.
argument-hint: <case-name, a folder under curriculum/>
---

Arguments: `$ARGUMENTS`. The first word is `<case>`, the folder name under `curriculum/`.
If it is missing, list the folders in `curriculum/` and ask which one.

1. Run `uv run scripts/extract.py curriculum/<case> --out notes/<case>`.
2. Read `notes/<case>/manifest.json`, then skim each notes file (headings first).
3. Reply with:
   - a table: discipline | deck/guide | slides | 1-line topic
   - the case's **learning objectives**: quote any slide that lists objectives, with its citation
   - 3–5 **cross-discipline threads** (e.g. "protein A (micro) → blocked opsonization (immuno) → abscess (path) → PBP2a/MRSA (pharm)"), each link cited
   - anything skipped (videos, legacy `.ppt`) the student should review by hand
   - the suggested next step: `/flashcards <case> "<topic>"` or `/quiz <case> "<topic>"`
Write no files other than the notes.
