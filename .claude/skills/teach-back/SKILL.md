---
name: teach-back
description: Explain-it-back session on one mechanism from the notes. Five prompts, nothing shown until all five attempts are in, then a cited expert model and cloze cards for each gap.
argument-hint: <case-name> "<mechanism>"
disable-model-invocation: true
---

Arguments: `$ARGUMENTS`. The first word is `<case>` (a folder under `notes/`), then a quoted mechanism, e.g. "S. aureus toxin-mediated disease".
If `notes/<case>` is missing, tell the student to run `/ingest <case>`. Study aid only: synthetic patients, no graded work.
Record template, mark rules, and the miss-card recipe live in `reference.md`.

1. **Pick** one mechanism chain from the notes and a `<slug>` (`[a-z0-9-]`). Name the slides that carry it.
   Done when the chain has four links, each tied to a slide, and the notes cover them.
2. **Prompt.** Ask one at a time and wait for a free-text attempt after each: (1) what it is, (2) how it causes disease, (3) how it shows up, (4) how we treat it, then (5) one what-if ("what changes if ...?").
   Show nothing from the notes until all five are answered.
   Done when five attempts are held verbatim.
3. **Mark** each attempt `correct`, `missing`, or `wrong` against the slides, and write `output/<case>/teach-back/<slug>.md` per `reference.md`.
   Done when the record has one table row per prompt, each with a `[[cite]]`, and an expert model of cited bullets.
4. **Check.** Run `uv run scripts/check.py output/<case>/teach-back/<slug>.md --notes notes/<case>`. Fix and rerun.
   Done when it prints PASS.
5. **Show** the expert model next to the marks.
   Done when the student has seen the marks and the model.
6. **Close gaps.** If any row is `missing` or `wrong`, turn each into a cited cloze card in `output/<case>/flashcards.csv` and a line in `output/<case>/weak-spots.md` (`reference.md`).
   Done when `check.py` prints PASS on each file written, or every row was `correct` and nothing was written.
7. **Optional evidence step.** Offer to open one cited PMID with a PubMed tool and judge whether it supports the claim.
   Done when the student declines, or the verdict (supports, partly, does not) is stated with the reminder that existence is not support.
8. **Next.** Suggest `/anki-sync <case>`; cards land in `AI Study::<case>::misses`.
   Done when the student has the command.
