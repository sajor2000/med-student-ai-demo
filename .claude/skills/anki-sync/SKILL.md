---
name: anki-sync
description: Push verified flashcards and diagram cards into Anki desktop as *owned* notes in AI Study::<case>, and pull cards the student keeps missing back into weak-spots.md. Run after /flashcards or /visualize.
argument-hint: <case-name>
disable-model-invocation: true
---

Arguments: `$ARGUMENTS`. The first word is `<case>` (lowercase letters, digits, hyphens; a folder under `output/`).
If neither `output/<case>/flashcards.csv` nor any `output/<case>/diagrams/*.occlusion.json` exists, tell the student to run `/flashcards <case>` (or `/visualize <case>`) first.

Sync touches only *owned* notes: tagged `msad`, living in the deck `AI Study::<case>`. See `reference.md` for the full rule.

1. **Sync.** Run:
   `uv run scripts/anki_sync.py --case <case>` plus `--csv output/<case>/flashcards.csv` when that file exists,
   and `--diagrams output/<case>/diagrams` when that folder holds `*.occlusion.json` files (either or both).
   Done when the last line reads `added N, updated N, adopted N, skipped N, weak spots N`.
   Exit code 2 means Anki is closed or AnkiConnect is missing: relay the script's one-line fix
   (open Anki desktop, install add-on `2055492159`; steps in `reference.md`) and stop.
2. **Explain skips.** A nonzero `skipped` means a note was left alone because it sat outside the owned deck, or the
   Image Occlusion note type is missing. Relay the hint the script printed.
   Done when every skip has a one-line reason for the student.
3. **Report weak spots.** If `weak spots` is above 0, show the new lines at the end of `output/<case>/weak-spots.md`.
   Done when the count shown matches the summary line.
4. **Next step.** Tell the student `/flashcards <case>` will now target those weak spots first.

Report added, updated, adopted, skipped, and the new weak spots. Anki desktop stays the place to review.
