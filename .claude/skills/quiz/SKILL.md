---
name: quiz
description: Interactive practice quiz from the student's notes. Asks one USMLE-style question at a time, waits for the answer, explains with citations, and tracks weak spots.
argument-hint: <notes folder> [topic] [n questions, default 5]
---

Run an interactive quiz. Do NOT show answers in advance.

For each question:
1. Write a short clinical vignette with 5 options (A–E), testing a mechanism, not a buzzword. Base it on the notes.
2. Stop and wait for the student's answer.
3. Then explain: why the right answer is right, why each distractor is wrong, citing `[[path#S#]]`.
At the end, list weak topics and append them to `output/<case>/weak-spots.md` (date, topic, citation) so /flashcards can target them next time.
