# teach-back reference

Rules for every run: study aid only, no graded work, synthetic patients only (no real identifiers in prompts or records).

## Prompts

1. What is it? 2. How does it cause disease? 3. How does it show up? 4. How do we treat it? 5. What if ... (change one variable: a missing gene, a blocked pathway, a resistant strain).
Ask one, wait, ask the next. The student's attempt comes before any slide content; praise and corrections wait until step 5.

## Record template: output/<case>/teach-back/<slug>.md

```
# Teach-back: <mechanism>

## Student attempts
> 1. (student text verbatim)
> 2. ...

## Marks
| step | correct/missing/wrong | cite |
|---|---|---|
| 1 what it is | correct | [[MICRO/Staphylococcus aureus (sample lecture)#S4]] |

## Expert model
- Exfoliative toxin cleaves desmoglein-1. [[MICRO/Staphylococcus aureus (sample lecture)#S4]]
```

- Student text sits in blockquotes, so `check.py` treats the record as a guide and skips it.
- Marks: one row per prompt (five rows), the mark word exactly `correct`, `missing`, or `wrong`, one `[[cite]]` each.
- The expert model is cited bullets only; mark anything beyond the slides `(beyond slides)` and back it with a PMID.
- Check: `uv run scripts/check.py output/<case>/teach-back/<slug>.md --notes notes/<case>`.

## Gap to card

- One cloze card per `missing` or `wrong` row, front in Anki markup: `Exfoliative toxin cleaves {{c1::desmoglein-1}}.`
- `sources`: the row's `[[cite]]`. `tags`: `<case>;<discipline>;<topic>;miss;objN` (`objN` when the mechanism maps to a case objective).
- Merge into `output/<case>/flashcards.csv` (`front,back,sources,tags`): keep existing rows, drop a new row whose `front` already exists.
- Weak-spot line in `output/<case>/weak-spots.md`: `- YYYY-MM-DD | discipline | topic | [[path#S#]]`.
- Check both: `uv run scripts/check.py output/<case>/flashcards.csv --notes notes/<case>` and `uv run scripts/check.py output/<case>/weak-spots.md --notes notes/<case>`.

## Evidence step

Open one cited PMID with a PubMed tool call in this session; use only PMIDs that call returned. Read the abstract, then judge whether it supports the specific claim: supports, partly, or does not. A PMID that exists, or that a tool returned, is not evidence that it supports the claim.

See also: [LEARNING-SCIENCE](../../../docs/LEARNING-SCIENCE.md)
Responsible use (educational demo; follow your institution's AI policy for anything you upload): [RESPONSIBLE-USE](../../../docs/RESPONSIBLE-USE.md)
