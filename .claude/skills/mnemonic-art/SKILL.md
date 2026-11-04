---
name: mnemonic-art
description: Draw one *aid* - a captioned memory-hook illustration for a single cited concept, made through the student's own OpenRouter key. Hand-fired; the image is never a reference or a citation. Low evidence, memory aid only.
argument-hint: <case-name> ["concept"]
disable-model-invocation: true
---

Arguments: `$ARGUMENTS`. The first word is `<case>` (a folder under `notes/`), then an optional quoted concept.
An *aid* helps the student remember; the notes stay the source.

1. **Pick the concept.** Read `notes/<case>/`, choose one concept the notes explain (ask the student when
   several fit), and quote its citation `[[path#S#]]`.
   Done when one concept and its citation are named.
2. **Draft the scene.** Write a one-sentence scene with the student that works as a memory hook for the concept
   (pun, character, or visual metaphor). Use objects and cartoon characters, and no patient details.
   Done when the student has said the scene is right.
3. **Show the prompt.** Run
   `uv run scripts/mnemonic_art.py --case <case> --concept "<concept>" --scene "<scene>"`
   and show the printed prompt.
   - Exit 2 means no key: relay the printed setup steps and stop.
   - Exit 1 with "Refused" means the text looked patient-identifying: reword the scene and rerun.
   Done when the exact prompt and the OpenRouter notice are on screen.
4. **Confirm, then send.** Ask the student to confirm sending the prompt to OpenRouter. After a yes, rerun the same
   command with `--yes`.
   Done when the script prints `Saved output/<case>/art/<slug>.png`.
5. **Report.** Give the image path and the concept's citation. Remind the student that the picture is an *aid*,
   not a reference, and that a citation always points to the notes.
   Done when the path and the reminder are both in the message.

Prompt patterns, cost and key notes, and the school AI-policy note are in `reference.md`.
