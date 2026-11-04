---
name: flashcards
description: Generate cited Anki flashcards for a case/topic from extracted notes (and quiz weak spots), verify every citation, and export to Anki plus a flip-card web page.
argument-hint: <case-name> ["topic"] [number of cards, default 20]
---

Arguments: `$ARGUMENTS`. The first word is `<case>` (a folder under `notes/`), then an optional quoted topic and an
optional card count (default 20). If `notes/<case>` does not exist, tell the student to run `/ingest <case>` first.

1. Read the notes for the topic. **If `output/<case>/weak-spots.md` exists, read it too**: cover those topics first,
   and use them as the topic when none was given.
   With no topic, run `uv run scripts/coverage.py --notes notes/<case> --csv output/<case>/flashcards.csv`
   (plus `--vignettes output/<case>/vignettes.json` if it exists) and spend cards on objectives it reports `UNCOVERED` (weak spots still first); tag them with the `<slug>-objN` form it expects.
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
     Add `<slug>-objN` when a card covers learning objective N (plain `objN` only if one lecture defines N; `scripts/coverage.py` reads it), and `miss` for a card made from a missed question (`/anki-sync` files it under `AI Study::<case>::misses`).
   - Up to 20% of cards may extend beyond the slides from StatPearls/PubMed; get those PMIDs from a tool call this session.
3. Run `uv run scripts/check.py output/<case>/flashcards.csv --notes notes/<case>`. Fix and rerun until PASS.
4. Run `uv run scripts/export.py output/<case>/flashcards.csv --notes notes/<case>`, adding `--guide output/<case>/study-guide.md`,
   `--diagrams output/<case>/diagrams`, `--art output/<case>/art`, `--deepen output/<case>/deepen` and
   `--vignettes output/<case>/vignettes.json` for each that already exists (`--notes` makes every slide citation open its slide).
5. Report the card count by discipline and the two output paths. Tell the student:
   - Anki: **File → Import →** `flashcards.anki.txt` (basic cards), and again for `flashcards.cloze.anki.txt` if it exists
     (cloze cards). Both land in the deck `AI Study::<case>`, and re-importing updates existing cards instead of duplicating them.
   - On the study page (`flashcards.html`), click any slide citation to open that slide's text. The `flashcards_sources/`
     folder is course material: keep it for yourself and don't share it.
   - These cards supplement a premade deck: they cover *this course's* framing and faculty emphasis.
   - Before studying, spot-check 3 random cards against their cited slide or paper.
   - After a later `/study-guide`, `/visualize`, `/mnemonic-art`, `/deepen`, or `/vignette`, re-run export with every flag above that applies.
6. Suggest `/anki-sync <case>` to push these cards into Anki and pull back the ones the student keeps missing.
