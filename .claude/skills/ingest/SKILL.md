---
name: ingest
description: Extract a folder of course slides, PDFs, guides, and lecture transcripts (any school) into citable Markdown notes and summarize what the case covers. Use first, before any study guide, flashcards, or quiz.
argument-hint: <case-name, a folder under curriculum/>
---

Arguments: `$ARGUMENTS`. The first word is `<case>`, the folder name under `curriculum/`.
If it is missing, list the folders in `curriculum/` and ask which one.

Supported: `.pptx`, `.pdf` (slides, `[S#]` per page), `.docx`, `.txt`, `.md` (`[P#]` per paragraph), `.vtt`, `.srt` (transcripts, `[P#]` per ~60 s with a `[mm:ss]` stamp).
Keynote or Google Slides: the student exports to PDF or PPTX first. Say so if they have those.

1. Remind the student: course files belong to their institution; confirm their school's AI policy allows sending course content to an AI tool before ingesting (see [docs/RESPONSIBLE-USE.md](../../../docs/RESPONSIBLE-USE.md)).
2. Run `uv run scripts/extract.py curriculum/<case> --out notes/<case>`.
3. Read `notes/<case>/manifest.json`, then skim each notes file (headings first).
4. Reply with:
   - a table: discipline | deck/guide | slides | 1-line topic
   - the case's **learning objectives**: quote any slide that lists objectives, with its citation
   - 3–5 **cross-discipline threads** (e.g. "protein A (micro) → blocked opsonization (immuno) → abscess (path) → PBP2a/MRSA (pharm)"), each link cited
   - anything skipped (videos, legacy `.ppt`/`.doc`) the student should review by hand
   - PDF pages flagged `[no text on this page — scanned slide]` (`image_only_pages` in the manifest): list them, never guess their content, suggest OCR or retyping
   - the suggested next step: `/flashcards <case> "<topic>"` or `/quiz <case> "<topic>"`
Write no files other than the notes.
