---
name: study-guide
description: Build a cited, integrated study guide from extracted notes plus trusted open sources (StatPearls, PubMed reviews). Use after /ingest.
argument-hint: <notes folder> [focus topic]
---

Goal: `output/<case>/study-guide.md`, a guide a student could study from the night before an exam.

1. Read every notes file under `notes/$ARGUMENTS` (or only the focus topic if given).
2. Draft sections:
   - **Learning objectives** (from the course, cited)
   - **One-page summary**: the case story in 8–12 bullets that link disciplines
   - **Per topic**: mechanism → disease → presentation → diagnosis → treatment, each bullet cited `[[path#S#]]`
   - **Compare/contrast tables** where students confuse things (e.g. Staph vs Strep, bacteriostatic vs bactericidal)
   - **Beyond the slides**: for the 3 highest-yield topics, search PubMed (prefer StatPearls, then reviews from the last 10 years). Add 1–2 sentences + `[PMID:…]` each. Only PMIDs returned by a tool call this session.
   - **Discrepancies**: any place a trusted source disagrees with or updates a slide (⚠️ callout, both sides cited)
   - **Self-test**: 5 short "why" questions (answers at the bottom)
3. Run `uv run scripts/check.py output/<case>/study-guide.md --notes notes/<case>`. Fix every failure, then rerun until PASS.
4. Report: sections written, # course citations, # PubMed citations, any discrepancies found.
