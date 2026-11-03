---
name: visualize
description: Turn a case topic into a cited diagram spec, render it with diagram-design in the teaching profile, and build Anki Image Occlusion cards from it.
argument-hint: <case-name> "topic"
disable-model-invocation: true
---

Arguments: `$ARGUMENTS`. The first word is `<case>` (lowercase letters, digits, hyphens; a folder under `notes/`), then a quoted topic.
If `notes/<case>` does not exist, tell the student to run `/ingest <case>` first. Pick a `<slug>` for the topic (`[a-z0-9-]`, e.g. `staph-toxins`).

The *spec* is the source of truth: cited JSON first, picture second. Schema, type choice, and troubleshooting live in `reference.md`.

0. **Preflight.** Check three things.
   - The diagram-design plugin is installed. If not, print `/plugin marketplace add cathrynlavery/diagram-design` and `/plugin install diagram-design@diagram-design`, then stop.
   - `~/.diagram-design/profiles/teaching.md` exists. If not, `mkdir -p ~/.diagram-design/profiles` and copy `docs/diagram-teaching-profile.md` there.
   - Chromium is available for the occlusion step. If `occlude.py` later prints `Install Chromium once: ...`, run that line and rerun.
   Done when the plugin is present, `teaching.md` exists, and no style-guide prompt is pending (the repo's `.diagram-design` marker selects the profile).
1. **Read the notes** for the topic under `notes/<case>/`, including slide numbers (`S#`) for citations.
   Done when you can name the 4-9 ideas the diagram will hold, each with a slide.
2. **Write the spec** to `output/<case>/diagrams/<slug>.json`: pick the `type` by topic shape (`reference.md`), one idea per label (6 words max), every node cited, every labeled edge cited.
   Done when the file parses as JSON and each node has `label` and `cite`.
3. **Check.** Run `uv run scripts/check.py output/<case>/diagrams/<slug>.json --notes notes/<case>`. Fix and rerun.
   Done when it prints PASS.
4. **Render.** Invoke the `diagram-design` skill on the spec and write `output/<case>/diagrams/<slug>.html`.
   Every label `<text>` carries `data-node="<spec id>"`; title and legend text carry `data-decorative="true"`.
   Done when the HTML exists and the count of `data-node` attributes equals nodes plus labeled edges.
5. **Occlude.** Run `uv run scripts/occlude.py output/<case>/diagrams/<slug>.html --spec output/<case>/diagrams/<slug>.json --case <case>`. Fix the HTML or spec and rerun.
   Done when it prints the label summary with no FAIL lines.
6. **Pack the offline deck.** Run `uv run scripts/occlude.py --apkg output/<case>/diagrams --case <case>`.
   Done when `output/<case>/diagrams.apkg` exists.
7. **Report.** Give the paths (`<slug>.html`, `<slug>.card.png`, `<slug>.occlusion.json`, `diagrams.apkg`), the label count and card count, and one label to spot-check against its cited slide.
   Offer one delivery path and let the student pick:
   - `/anki-sync <case>` creates Image Occlusion notes in Anki desktop (best: the masks stay editable).
   - Or File -> Import `diagrams.apkg` in Anki (no add-on; each label becomes a masked basic card).
   Done when both paths are stated and the student has the spot-check label.
