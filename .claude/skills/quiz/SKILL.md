---
name: quiz
description: Interactive practice quiz from the student's notes. Asks one USMLE-style vignette at a time, waits for the answer, explains with quoted slide evidence, and saves weak spots for the next flashcard run.
argument-hint: <case-name> ["topic"] [number of questions, default 5]
---

Arguments: `$ARGUMENTS`. The first word is `<case>` (a folder under `notes/`), then an optional quoted topic and an
optional question count (default 5). Do NOT show answers in advance.
If `output/<case>/weak-spots.md` exists, read it and bias the questions toward those topics.

For each question:
1. Write a short clinical vignette with 5 options (A–E) that tests a mechanism, not a buzzword, and is answerable from
   the notes. Tag it internally with its discipline.
2. Stop and wait for the student's answer.
3. Explain:
   - why the right answer is right, **quoting the supporting slide line** with its citation `[[path#S#]]`
   - why each distractor is wrong, citing a slide where one exists. Mark anything that goes beyond the slides
     `(beyond slides)` and back it with a PMID from a tool call, or say plainly that it is general knowledge.
   - Remind the student once per quiz that explanations are not run through `check.py`, so they should open the quoted slide when unsure.
At the end, show the score, then append each missed topic to `output/<case>/weak-spots.md` as
`- YYYY-MM-DD | discipline | topic | [[path#S#]]`
(create the file if it is missing). Then run `uv run scripts/check.py output/<case>/weak-spots.md --notes notes/<case>`.
Done when it prints PASS. Tell the student `/flashcards <case>` will target these.
Also suggest `/anki-sync <case>` to push cards into Anki and pull back the ones the student keeps missing.
