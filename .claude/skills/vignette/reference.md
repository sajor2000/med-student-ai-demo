# vignette reference

Rules for every run: study aid only, no graded work, synthetic patients only (no real names, dates of birth, MRNs, or phone numbers; the PHI screen in `check.py` rejects them).

## vignettes.json schema

```
{"vignettes": [{"id": "kebab-id", "objective": 2, "discipline": "micro", "stem": "...",
  "options": [{"key": "A", "text": "...", "correct": false, "explanation": "..."}, ... E]}]}
```

- `id`: `^[a-z0-9-]{1,40}$`, unique. `objective`: integer 1 or more (optional). `discipline`: micro, immuno, path, pharm, histo, biochem, genetics...
- Exactly 5 options, keys A-E once each, exactly one `correct: true`.
- Every `explanation` is non-empty and cites `[[path#S#]]` or `[PMID:n]`. A PMID comes from a PubMed tool call in this session.
- Mark anything beyond the slides `(beyond slides)` and back it with a PMID.

Short example:

```
{"vignettes": [{"id": "staph-scalded-skin", "objective": 1, "discipline": "micro",
  "stem": "A 3-year-old has fever and sheets of superficial skin peeling after a minor impetigo lesion...",
  "options": [
   {"key": "A", "text": "Exfoliative toxin cleaving desmoglein-1", "correct": true,
    "explanation": "Toxin cleaves desmoglein-1 in the granular layer. [[MICRO/Staphylococcus aureus (sample lecture)#S4]]"},
   {"key": "B", "text": "Toxic shock syndrome toxin-1 acting as a superantigen", "correct": false,
    "explanation": "TSST-1 drives T-cell activation and shock, not blistering. [[MICRO/Staphylococcus aureus (sample lecture)#S4]]"}
   ]}]}
```
(Real files carry all five options.)

## Distractor design

- Draw all four distractors from the category the question tests (five toxins, five drugs, five organisms) so each one looks plausible.
- Each distractor is the right answer to a neighbouring question; its explanation names that neighbour.
- Make the stem answerable without the options, since the attempt comes first. The stem ends with an open question ("Which mechanism explains these findings?").
- Test a mechanism, not a buzzword. Keep the correct option similar in length to the others.

## Attempt-first protocol

1. Stem only. Wait for free-text.
2. Options A-E. Wait for the pick.
3. Explanation for all five options, with the quoted slide line.
Record per vignette: free-text answer, pick, correct or miss. A correct pick with a wrong free-text answer counts as a miss on recall; log it and say so.

## Miss-card recipe

- Cloze front in Anki markup: `Exfoliative toxin cleaves {{c1::desmoglein-1}}.` One fact per card; `back` empty or one line.
- `sources`: the explanation's `[[path#S#]]` (or `[PMID:n]`).
- `tags`: `<case>;<discipline>;<topic>;miss;objN` (`objN` only when the vignette has an `objective`).
- Merge into `output/<case>/flashcards.csv` (columns `front,back,sources,tags`): keep every existing row, drop a new row whose `front` already exists, quote fields containing commas.
- Check: `uv run scripts/check.py output/<case>/flashcards.csv --notes notes/<case>` and `uv run scripts/check.py output/<case>/weak-spots.md --notes notes/<case>`.
- Weak-spot line: `- YYYY-MM-DD | discipline | topic | [[path#S#]]`.
- `/anki-sync <case>` routes `miss` rows to `AI Study::<case>::misses`.

See also: [LEARNING-SCIENCE](../../../docs/LEARNING-SCIENCE.md)
Responsible use (educational demo; follow your institution's AI policy for anything you upload): [RESPONSIBLE-USE](../../../docs/RESPONSIBLE-USE.md)
If two lectures in the case both number objectives (1)-(3), tag cards `<lecture-slug>-objN` (slug = the notes path under `notes/<case>` without `.md`, lowercased, non-alphanumerics as `-`, e.g. `micro-staph-deck-obj2`) and add `"lecture": "<slug>"` to the vignette so `coverage.py` keeps them apart.
