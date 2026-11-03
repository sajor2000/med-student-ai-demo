---
name: deepen
description: Go beyond the slides on one concept with trusted literature (StatPearls, reviews, landmark papers) via PubMed and Paperclip, producing a short cited explainer.
argument-hint: <concept, e.g. "MRSA mecA PBP2a">
---

1. MeSH-check the concept (`pubmed_lookup_mesh`) to build a good query.
2. Search PubMed in this order and stop when you have enough:
   a. StatPearls chapter (`<concept> AND statpearls[book]` or title search)
   b. Reviews, last 10 years (`review[pt]`), sorted by relevance
   c. One landmark/primary paper if the student asks "how do we know?"
3. For the best 1–2 open-access papers, use Paperclip to read full text
   (`paperclip search -s pmc "<concept>"`, then `paperclip grep`/`head` on the paper,
   or `paperclip evidence "<claim>"` to test a specific claim).
4. Compare with what the course slides say (search `notes/` with grep). Note agreements and any ⚠️ discrepancies.
5. Write `output/deepen/<slug>.md`: a 300-word explainer, a "how this connects to the case" box, and an annotated bibliography (citation + 1 line on why it is worth reading).
6. Run `scripts/check.py` on it until PASS.
