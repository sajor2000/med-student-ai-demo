# Changelog

All notable changes are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `docs/img/skill-map.svg`, a diagram of every skill and when to use it, plus a "Which skill when" section in the README.

### Fixed
- `docs/diagram-teaching-profile.md` linked to four files that only exist in the upstream diagram-design repo; the links now point there. The link test covers every page under `docs/`.
- README repo map lists `doctor.py`, `make_case_guide.py`, and all the docs.

### Changed
- The fictional case-guide PDF now looks like a real case-guide handout: a cover page, a table of contents with page numbers, an "N of M - Self Study Guide" footer, and green headings. It is 10 pages; `examples/case2` citations moved to the new page numbers.
- `scripts/extract.py` treats a footer that differs only by its page number ("3 of 10 - ...") as a running footer.

## [0.4.0] - 2026-11-04

### Changed
- License: code moves from MIT to the PolyForm Noncommercial License 1.0.0, and the fictional sample and example content from CC BY 4.0 to CC BY-NC-SA 4.0. Free for personal study and for noncommercial teaching and research by schools, universities, and other noncommercial organizations; commercial use needs a separate written license. Copies obtained under 0.3.0 or earlier keep their MIT / CC BY 4.0 terms.
- Demo walkthrough: live steps run on the MRSA resistance topic, and Act 6 is a live Anki sync (#15).

## [0.3.0] - 2026-11-04

### Added
- Evidence-based practice skills: `/vignette` (synthetic board-style vignettes, answer first, look-alike options), `/teach-back` (explain a mechanism, get marked against the slides), `scripts/coverage.py`, and a Vignettes tab on the study page (#7).
- Any-school ingest: `scripts/extract.py` reads PDF, plain text, Markdown, VTT/SRT transcripts and more, beyond PowerPoint and Word (#6).
- Fictional case-based sample guide and a 25-minute demo walkthrough (#8). The demo input is a fictional M1 class PDF, built by `scripts/make_case_guide.py` with LibreOffice (#9); the editable Word file is in `docs/sample-case/`.
- README onboarding for Claude Code and Codex, and `AGENTS.md` as the single source of agent rules (#4).
- Open-source readiness: MIT license (code), CC BY 4.0 (sample and examples), contributing guide, code of conduct, security policy, citation file, issue and PR templates, `scripts/doctor.py`, and `docs/FOR-EDUCATORS.md` (#5).
- Follow-ups to the first release: a PHI gate, safer Anki adoption of existing cards, a Deep dives tab, and CI (#3).
- `scripts/pubmed-mcp.sh`: PubMed connector launcher that finds Node 24+ (the server fails every tool call on Node 22) and exits with a clear message if there is none.

### Changed
- `.mcp.json` and `.codex/config.toml` start the PubMed server through `scripts/pubmed-mcp.sh`.
- `docs/OPEN-RESOURCES.md` is school-agnostic (no course codes).

## [0.2.0]

### Added
- Cited diagrams, memory aids, and Anki sync (PR #2).

## [0.1.0]

### Added
- Cloze cards and source links (PR #1).

[Unreleased]: https://github.com/sajor2000/med-student-ai-demo/compare/main...HEAD
