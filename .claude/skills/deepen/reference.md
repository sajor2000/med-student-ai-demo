# /deepen reference

## PubMed tools

- `pubmed_search_articles`, `pubmed_fetch_articles`, `pubmed_lookup_mesh`, `pubmed_convert_ids`.
- Date filters go in `dateRange {minDate, maxDate}`; both are required. Use `1000` and `3000` for an open bound.
- StatPearls query form: `"StatPearls"[Book] AND (term[ti] OR term[ti])`. Drop off-topic hits.
- Reviews: add `review[pt]` and a last-10-years `dateRange`.

## Paperclip

- `evidence` tests one claim per call; make one call per claim.
- Paperclip ids are not citations. Convert each cited paper to a PMID (`pubmed_convert_ids` for PMC ids).

## Output

- Explainer text is cited bullets, written to `output/<case>/deepen/<slug>.md`.
