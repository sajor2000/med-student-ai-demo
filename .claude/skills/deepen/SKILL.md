---
name: deepen
description: Go beyond the slides on one concept with trusted literature (StatPearls, reviews, a landmark paper) via PubMed and Paperclip, producing a short cited explainer tied back to the case.
argument-hint: "<concept>" [case-name]
---

Arguments: `$ARGUMENTS`. The quoted part is the concept. An optional last word is `<case>` (a folder under `notes/`).
If no case is given and exactly one folder exists under `notes/`, use it. If there are several, ask which one.

1. Look up the concept in MeSH (the PubMed `lookup_mesh` tool) to build a good query.
2. Search PubMed in this order and stop when you have enough:
   a. a StatPearls chapter (`<concept> AND statpearls[book]`)
   b. reviews from the last 10 years (`review[pt]`), by relevance
   c. one landmark/primary paper if the student asks "how do we know?"
3. For the best 1–2 open-access papers, read the full text with **Paperclip**: the Paperclip MCP tools
   (search, grep, head, evidence), or the `paperclip` CLI if it is installed. Use `evidence` to test a specific claim.
   If Paperclip is not signed in, continue with PubMed abstracts and say so.
4. Compare with the course: search `notes/<case>` for the concept. Note agreements and any ⚠️ discrepancies, with both sides cited.
5. Write `output/deepen/<slug>.md`: a ~300-word explainer, a "how this connects to the case" box, and an annotated
   bibliography (citation + 1 line on why it is worth reading). Every bullet gets a citation.
6. Run `uv run scripts/check.py output/deepen/<slug>.md --notes notes/<case>` until PASS.
