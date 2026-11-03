---
name: flashcards
description: Generate cited Anki flashcards for a case/topic from extracted notes (and quiz weak spots), verify every citation, and export to Anki plus a flip-card web page.
argument-hint: <case-name> ["topic"] [number of cards, default 20]
---

Arguments: `$ARGUMENTS`. The first word is `<case>` (a folder under `notes/`), then an optional quoted topic and an
optional card count (default 20). If `notes/<case>` does not exist, tell the student to run `/ingest <case>` first.

1. Read the notes for the topic. **If `output/<case>/weak-spots.md` exists, read it too**: cover those topics first,
   and use them as the topic when none was given.
2. Write `output/<case>/flashcards.csv` with columns `front,back,sources,tags`. Quote any field that contains a comma.
   - One fact per card. Specific question, answer under ~20 words. No "list all 8" cards.
   - Mix: ~40% mechanism/"why", ~30% recall, ~20% clinical vignette ("A 7-year-old with honey-crusted lesions… organism?"), ~10% compare/contrast.
   - `sources`: one or more `[[path#S#]]` / `[[path#P#]]` and/or `[PMID:…]`. Every card needs one.
   - `tags`: `case;discipline;topic` separated by `;` (discipline = micro, immuno, path, pharm, histo, biochem, genetics, …).
   - Up to 20% of cards may extend beyond the slides from StatPearls/PubMed; get those PMIDs from a tool call this session.
3. Run `uv run scripts/check.py output/<case>/flashcards.csv --notes notes/<case>`. Fix and rerun until PASS.
4. Run `uv run scripts/export.py output/<case>/flashcards.csv` (add `--guide output/<case>/study-guide.md` if that file exists).
5. Report the card count by discipline and the two output paths. Tell the student:
   - Anki: **File → Import →** the `.anki.txt` file. Cards land in the deck `AI Study::<case>`, and re-importing updates existing cards instead of duplicating them.
   - These cards supplement a premade deck: they cover *this course's* framing and faculty emphasis.
   - Before studying, spot-check 3 random cards against their cited slide or paper.
