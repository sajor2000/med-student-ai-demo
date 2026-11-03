---
name: flashcards
description: Generate cited Anki flashcards from extracted notes, verify every citation, and export to Anki + a flip-card web page.
argument-hint: <notes folder> [topic] [n cards, default 25]
---

1. Read the notes for the topic. Write `output/<case>/flashcards.csv` with columns
   `front,back,sources,tags` (proper CSV quoting).
   - One fact per card. Specific question, answer under ~20 words.
   - Mix: ~40% mechanism/"why", ~30% recall, ~20% clinical vignette ("A 7-year-old with honey-crusted lesions… organism?"), ~10% compare/contrast.
   - `sources` = one or more `[[path#S#]]` and/or `[PMID:…]`. Every card needs one.
   - `tags` = `case;discipline;topic` separated by `;`.
   - Up to 20% of cards may come from a PubMed/StatPearls source to extend beyond the slides; get those PMIDs from a tool call.
2. Run `uv run scripts/check.py output/<case>/flashcards.csv --notes notes/<case>`. Fix and rerun until PASS.
3. Run `uv run scripts/export.py output/<case>/flashcards.csv --guide output/<case>/study-guide.md` (omit `--guide` if none).
4. Report the card count by discipline and the two output paths. Tell the student: Anki → File → Import → choose the `.anki.txt` file.
