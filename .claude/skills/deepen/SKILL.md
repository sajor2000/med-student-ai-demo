---
name: deepen
description: Go beyond the slides on one concept with trusted literature (StatPearls, reviews, a landmark paper) via PubMed and Paperclip, producing a short cited explainer tied back to the case.
argument-hint: "<concept>" [case-name]
---

Arguments: `$ARGUMENTS`. The quoted part is the concept. An optional last word is `<case>` (a folder under `notes/`).
If no case is given and exactly one folder exists under `notes/`, use it. If there are several, ask which one.
Tool names and query forms live in `reference.md`.

1. Look up the concept with `pubmed_lookup_mesh` and build a query.
   Done when you have a query with MeSH terms.
2. Search with `pubmed_search_articles`: a StatPearls chapter first, then reviews from the last 10 years, then one
   landmark paper if the student asks "how do we know?". Read hits with `pubmed_fetch_articles`.
   Done when you have 2-4 on-topic papers with PMIDs.
3. Read the best 1-2 open-access papers with Paperclip (MCP tools, or the `paperclip` CLI). `evidence` takes ONE claim
   per call. If Paperclip is not signed in, continue with abstracts and say so.
   Done when each claim you plan to write has a paper behind it.
4. Search `notes/<case>` for the concept. Note agreements and any discrepancies, with both sides cited.
   Done when each discrepancy cites a slide and a paper.
5. Write `output/<case>/deepen/<slug>.md` as cited bullets: a ~300-word explainer, a "how this connects to the case"
   box, and an annotated bibliography. Every cited paper has a PMID from a PubMed tool (`pubmed_convert_ids` for PMC ids).
   Done when every bullet has a citation.
6. Run `uv run scripts/check.py output/<case>/deepen/<slug>.md --notes notes/<case>`.
   Done when it prints PASS.
