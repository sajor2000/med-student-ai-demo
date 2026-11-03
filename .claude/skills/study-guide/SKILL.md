---
name: study-guide
description: Build a cited, integrated study guide for one case (or one topic in it) from extracted notes plus trusted open sources (StatPearls, PubMed reviews). Use after /ingest.
argument-hint: <case-name> ["focus topic"]
---

Arguments: `$ARGUMENTS`. The first word is `<case>` (a folder under `notes/`). Anything after it is the
optional focus topic. If `notes/<case>` does not exist, tell the student to run `/ingest <case>` first.

Goal: `output/<case>/study-guide.md`, a reference to check yourself against **after** you try to recall the material.

1. Read the notes under `notes/<case>`: all of them, or only the files relevant to the focus topic.
2. Draft sections. **Every bullet, numbered item, and table row carries a citation** (`[[path#S#]]`, `[[path#P#]]`,
   `[[path#T#]]`, or `[PMID:…]`), or is marked `[source needed]` or `(AI mnemonic)`:
   - **Learning objectives**: from the course, cited
   - **One-page summary**: the case story in 8–12 bullets that link disciplines
   - **Per topic**: mechanism → disease → presentation → diagnosis → treatment
   - **Compare/contrast tables** where students confuse things (e.g. Staph vs Strep, bacteriostatic vs bactericidal)
   - **Beyond the slides**: for the 3 highest-yield topics, search PubMed (StatPearls first, then reviews from the
     last 10 years) and add 1–2 sentences + `[PMID:…]` each. Only PMIDs a tool returned in this session.
     **If the PubMed tools are unavailable**, write "Beyond the slides: skipped (PubMed unavailable)" and cite slides only. Never reuse or guess a PMID.
   - **Discrepancies**: any place a trusted source, or another slide, disagrees with a slide (⚠️ callout, both sides cited)
   - **Self-test**: 5 short "why" questions, answers in a collapsed `<details>` block
3. Run `uv run scripts/check.py output/<case>/study-guide.md --notes notes/<case>`. Fix every failure and rerun until PASS.
4. Report: sections written, the number of course and PubMed citations, any discrepancies found, and **one citation the
   student should open and compare themselves** (PASS proves the source exists, not that it supports the claim).
