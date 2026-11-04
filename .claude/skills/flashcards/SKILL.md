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
   When the file already exists, merge: keep every existing row, add the new rows, and dedupe by `front`.
   Done when the row count is at least the old count and no `front` appears twice.
   - One fact per card. Specific question, answer under ~20 words. No "list all 8" cards.
   - Mix: ~40% mechanism/"why", ~30% recall, ~20% clinical vignette ("A 7-year-old with honey-crusted lesions… organism?"), ~10% compare/contrast.
   - About a quarter of the cards may be **cloze** cards, which suit lists, pathways, and "X causes Y" facts. Write them in Anki
     markup in `front`: `Exfoliative toxin cleaves {{c1::desmoglein-1}}.` An optional hint goes after a second `::`
     (`{{c1::desmoglein-1::a desmosome protein}}`). Use `c1`, `c2`… for separate cards from one sentence. Leave `back` empty
     or put one line of extra context there.
   - `sources`: one or more `[[path#S#]]` / `[[path#P#]]` and/or `[PMID:…]`. Every card needs one.
   - `tags`: `case;discipline;topic` separated by `;` (discipline = micro, immuno, path, pharm, histo, biochem, genetics, …).
   - Up to 20% of cards may extend beyond the slides from StatPearls/PubMed; get those PMIDs from a tool call this session.
3. Run `uv run scripts/check.py output/<case>/flashcards.csv --notes notes/<case>`. Fix and rerun until PASS.
4. Run `uv run scripts/export.py output/<case>/flashcards.csv --notes notes/<case>` (add `--guide output/<case>/study-guide.md`,
   `--diagrams output/<case>/diagrams` and `--art output/<case>/art` for each that already exists). `--notes` makes every slide citation on the study page open the exact slide.
5. Report the card count by discipline and the two output paths. Tell the student:
   - Anki: **File → Import →** `flashcards.anki.txt` (basic cards), and again for `flashcards.cloze.anki.txt` if it exists
     (cloze cards). Both land in the deck `AI Study::<case>`, and re-importing updates existing cards instead of duplicating them.
   - On the study page (`flashcards.html`), click any slide citation to open that slide's text. The `flashcards_sources/`
     folder is course material: keep it for yourself and don't share it.
   - These cards supplement a premade deck: they cover *this course's* framing and faculty emphasis.
   - Before studying, spot-check 3 random cards against their cited slide or paper.
   - Pass every export flag that applies on the first run, including `--diagrams` and `--art` when output from
     `/visualize` or `/mnemonic-art` already exists. After a later `/study-guide`, `/visualize` or `/mnemonic-art`, re-run
     export with all applicable flags (`--guide`, `--notes`, `--diagrams`, `--art`) so the study page picks up the new files.
6. Suggest `/anki-sync <case>` to push these cards into Anki and pull back the ones the student keeps missing.
