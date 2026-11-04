# /study-guide reference

## Sections

- **Learning objectives**: from the course, cited
- **One-page summary**: the case story in 8-12 bullets that link disciplines
- **Per topic**: mechanism, disease, presentation, diagnosis, treatment
- **Compare/contrast tables** where students confuse things (Staph vs Strep, bacteriostatic vs bactericidal)
- **Beyond the slides**: 1-2 sentences + `[PMID:…]` per high-yield topic
- **Discrepancies**: where a trusted source or another slide disagrees with a slide (callout, both sides cited)
- **Self-test**: 5 short "why" questions, answers in a collapsed `<details>` block, answers cited

## PubMed tools

- `pubmed_search_articles`: search. `pubmed_fetch_articles`: read titles and abstracts for the PMIDs you found.
- `pubmed_lookup_mesh`: build a better query. `pubmed_convert_ids`: turn a PMC id or DOI into a PMID.
- Date filters go in `dateRange {minDate, maxDate}`; both are required. Use `1000` and `3000` for an open bound.
- StatPearls query form: `"StatPearls"[Book] AND (term[ti] OR term[ti])`. Drop off-topic hits after reading titles.
- Then reviews from the last 10 years (`review[pt]`).

## Rules

- Only PMIDs a tool returned in this session. Never reuse or guess one.
- Never attach an unrelated slide to a fact the slides do not cover.
