---
name: study-guide
description: Build a cited, integrated study guide for one case (or one topic in it) from extracted notes plus trusted open sources (StatPearls, PubMed reviews). Use after /ingest.
argument-hint: <case-name> ["focus topic"]
---

Arguments: `$ARGUMENTS`. The first word is `<case>` (a folder under `notes/`). Anything after it is the
optional focus topic. If `notes/<case>` does not exist, tell the student to run `/ingest <case>` first.

Goal: `output/<case>/study-guide.md`, a reference to check yourself against **after** you try to recall the material.
Tool names, query forms, and the section list live in `reference.md`.

1. Read the notes under `notes/<case>`: all of them, or only the files relevant to the focus topic.
   Done when you can name each topic with its slide numbers.
2. Draft the sections listed in `reference.md`. Every bullet, numbered item, and table row carries a citation
   (`[[path#S#]]`, `[[path#P#]]`, `[[path#T#]]`, or `[PMID:…]`), or is marked `[source needed]`. `(AI mnemonic)` is for mnemonic wording only, never for a factual mechanism or treatment claim: those need a citation or `[source needed]`.
   `check.py` verifies this for bullets, numbered items, and table rows outside Self-test. It does not check
   plain prose lines or the Self-test answers, so read those yourself: each Self-test answer needs a citation.
   Done when every such line has a citation or a mark and `check.py` agrees.
3. Add "Beyond the slides" for the 3 highest-yield topics using the PubMed tools (`reference.md`). A fact the course
   has no slide for (a drug mechanism, for example) goes here with a PMID from a tool call this session, or is marked
   `[source needed]`. Attach each fact only to a source that states it. If the PubMed tools are unavailable, write
   "Beyond the slides: skipped (PubMed unavailable) [source needed]".
   Done when each Beyond-the-slides line has a tool-returned PMID or `[source needed]`.
4. Run `uv run scripts/check.py output/<case>/study-guide.md --notes notes/<case>`. Fix every failure and rerun.
   Done when it prints PASS.
5. Report the sections written, the number of course and PubMed citations, any discrepancies, and one citation the
   student should open and compare (PASS proves the source exists, not that it supports the claim).
   Done when the student has the open-this-one citation.
