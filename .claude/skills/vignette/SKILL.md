---
name: vignette
description: Cited five-option clinical vignettes from the student's notes, run attempt-first (free-text answer before any options), with every miss turned into a cited cloze card.
argument-hint: <case-name> [number of vignettes, default 5]
disable-model-invocation: true
---

Arguments: `$ARGUMENTS`. The first word is `<case>` (a folder under `notes/`), then an optional count `n` (default 5).
If `notes/<case>` is missing, tell the student to run `/ingest <case>`. Study aid only: synthetic patients, no graded work.
Schema, distractor design, and the miss-card recipe live in `reference.md`.

1. **Read** `notes/<case>`, the case objectives, and `output/<case>/weak-spots.md` when it exists.
   Done when you can name `n` mechanisms to test, each with a slide, weighted toward the weak spots.
2. **Write** `output/<case>/vignettes.json` per `reference.md`: a synthetic patient, look-alike distractors from one category, a cited explanation for every option.
   Done when the file holds `n` vignettes and every option carries a `[[path#S#]]` citation.
3. **Check.** Run `uv run scripts/check.py output/<case>/vignettes.json --notes notes/<case>`. Fix and rerun.
   Done when it prints PASS.
4. **Run the attempt**, one vignette at a time: show the stem only and wait for the student's free-text answer.
   Then show options A-E and wait for the pick. Then give the explanation for every option, quoting the slide line.
   Done when each vignette has a recorded free-text answer, a pick, and a shown explanation.
5. **Log misses.** If the student missed any vignette, append each miss to `output/<case>/weak-spots.md` as `- YYYY-MM-DD | discipline | topic | [[path#S#]]`.
   Turn each miss into a cited cloze card merged into `output/<case>/flashcards.csv` (`reference.md`).
   Done when `check.py` prints PASS on each of those two files that was written, or the student had no misses and nothing was written.
6. **Coverage.** Run `uv run scripts/coverage.py --notes notes/<case> --csv output/<case>/flashcards.csv --vignettes output/<case>/vignettes.json` and relay the objectives report.
   Done when the report is shown and the score is stated. (A missing flashcards.csv counts as 0 cards.)
7. **Next.** Suggest `/anki-sync <case>`; miss cards land in `AI Study::<case>::misses`.
   Done when the student has the command.

A PASS shows the cited sources exist, not that they support the explanation; remind the student once to open the quoted slide when unsure.
