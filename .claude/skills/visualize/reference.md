# /visualize reference

## Type by topic shape

| Topic shape | Type | Why |
|---|---|---|
| Mechanism, pathway, cascade, algorithm ("A causes B causes C") | `flowchart` | Edges carry the verbs; edge labels become cited cards |
| Classification, taxonomy, family ("kinds of X") | `tree` | Depth shows the hierarchy; max 4 levels, 5 per level |
| Compare two or more things on two axes | `quadrant` | Axes name the contrast |
| Part-of structure, compartments, layers of a structure | `nested` | Containment shows "inside" |

Keep a diagram to 9 nodes or fewer; split larger topics into two slugs. A topic that fits none of the shapes usually belongs on a flashcard, not a diagram.

## Spec schema

`output/<case>/diagrams/<slug>.json` (`<case>` and `<slug>` match `[a-z0-9-]`):

```json
{
  "title": "S. aureus toxins",
  "type": "flowchart",
  "nodes": [{"id": "n1", "label": "Exfoliative toxin", "cite": "[[MICRO/Staphylococcus aureus#S4]]"}],
  "edges": [{"id": "e1", "from": "n1", "to": "n2", "label": "cleaves", "cite": "[[MICRO/Staphylococcus aureus#S4]]"}]
}
```

- `id` matches `^[a-z0-9-]{1,40}$` and is unique across nodes and edges.
- Every node has `label` and `cite`. An edge with a `label` has a `cite`; an edge with no label needs none.
- `cite` uses the existing syntax: `[[path#S#]]`, `[[path#P#]]`, `[[path#T#]]`, or `[PMID:n]`. Citations in a PASS resolve to real sources; the student still spot-checks one against the slide.

## diagram-design handoff

- The repo's `.diagram-design` marker (`profile: teaching`) makes the plugin read `~/.diagram-design/profiles/teaching.md` directly, so the first-time style-guide prompt never fires.
- Pass the plugin the spec's `type`, title, nodes, and edges. Labels are the spec's strings verbatim; do not reword them.
- Output format is `html`. The occlusion step makes the PNG itself; skip the plugin's export step.
- Every `<text>` the student should be quizzed on carries `data-node="<id>"`, edge labels included. Title, legend, and axis captions carry `data-decorative="true"`. The occlusion check runs both ways: a spec id with no `<text>`, or an unmarked `<text>`, is a FAIL.
- Edge labels stay within 14 characters: diagram-design renders them in capitals, and `occlude.py` compares labels
  case-insensitively after whitespace normalization, so `cleaves` matches `CLEAVES`. Any other text difference fails.
- Node labels stay within 6 words.
- Run the plugin's self check before occluding: `python3 <diagram-design skill dir>/scripts/self_check.py --offline <html>`.
- Invoke the Skill `diagram-design:diagram-design`; when it is unavailable, read the installed plugin's `SKILL.md` and author the HTML following it.
- Use the `node-name` role at 20px as the teaching profile defines. Leave the profile's `accent` on one focal node.

## Troubleshooting

- **check.py FAIL on a citation:** the slide number or path is wrong. Reopen the note, correct the `cite`, rerun.
- **occlude.py "spec id has no text":** the HTML dropped or renamed a label. Re-render or add `data-node` to that `<text>`.
- **occlude.py "text has no data-node":** mark it `data-decorative="true"` if it is a title or legend, otherwise add the spec node.
- **Chromium missing (exit 2):** run `uv run --with playwright playwright install chromium` once, then rerun the step.
- **Plugin asks about the style guide:** the marker or profile file is missing; redo step 0.
- **Labels overlap on the card:** shorten the label or split the diagram; boxes that overlap make unreliable masks.
