---
name: ingest
description: Extract a folder of course slides/guides into citable Markdown notes and summarize what the case covers. Use first, before any study guide or flashcards.
argument-hint: <folder under curriculum/>
---

1. Run `uv run scripts/extract.py curriculum/$ARGUMENTS --out notes/$ARGUMENTS`.
2. Read `notes/$ARGUMENTS/manifest.json`, then skim each notes file (headings first).
3. Reply with:
   - a table: discipline | deck/guide | slides | 1-line topic
   - the case's apparent **learning objectives** (quote any slide that lists objectives, with its citation)
   - 3–5 **cross-discipline threads** (e.g. "S. aureus protein A (micro) → opsonization (immuno) → abscess (path) → MRSA PBP2a (pharm)"), each with citations
   - anything skipped (videos, legacy .ppt) the student should review by hand
Do not write files other than the notes.
