# Contributing

Thanks for helping. This repo is a study aid for M1/M2 students and the schools
that adopt it. Contributions that make setup easier, add a school's file format,
or sharpen a skill are the most useful.

## Never commit these

- **Course files**: slides, lecture notes, handouts, exam material, anything under
  `curriculum/`, `notes/`, or `output/` (git-ignored for this reason).
- **Patient information** of any kind, real or reconstructable.
- Secrets (API keys, tokens).

Only the synthetic material in `sample/` and `examples/` belongs here. If you commit
something private by accident, follow [SECURITY.md](SECURITY.md); do not open a public issue.

**Follow your institution's AI policy; never include course content or patient information.** See [NOTICE.md](NOTICE.md).

## Set up and test

```bash
uv run scripts/doctor.py     # checks your machine
uv run --with pytest --with markdown --with genanki --with pillow --with playwright --with pymupdf pytest tests -q
uv run scripts/check.py --help   # citation checker; run it on examples/ before a PR
```

Scripts are standalone `uv` inline scripts. Add tests first, in `tests/`, and keep them
offline: monkeypatch network and machine probes (see `tests/test_doctor.py`).

## Add a skill

A skill is `.claude/skills/<name>/SKILL.md`. It is read by an agent, not a person, so
write it the way you would brief a capable colleague who has never seen this repo.

- Frontmatter: `name`, a `description` that says what it does and when to use it, and
  `argument-hint`.
- **40 lines or fewer.** Move tool names, query forms, and templates into a
  `reference.md` beside it.
- State the goal and the output path first, then the rules that are easy to get wrong.
  Do not explain things the agent already knows.
- Give the reason behind each rule in a few words; agents follow rules they understand.
- Prefer one concrete example over a paragraph of description.
- Every factual claim a skill produces must carry a source link or a verified PMID.

## Pull requests

Fill in the PR template. Keep PRs small, and say what you ran. For a new school format,
include a synthetic file (not a real lecture) that reproduces the problem.

**Contributor license grant.** By submitting a contribution you agree that:

1. Your code is published under the PolyForm Noncommercial License 1.0.0 and your sample/example content
   under CC BY-NC-SA 4.0 (see `LICENSE` and `LICENSE-CONTENT`).
2. You grant J.C. Rojas, the maintainer, a perpetual, worldwide, non-exclusive, royalty-free, irrevocable
   license, with the right to sublicense through multiple tiers, to use, copy, modify, distribute, and
   license your contribution under any terms, including commercial terms.
3. You grant the maintainer and every recipient of the project a perpetual, worldwide, royalty-free,
   irrevocable patent license for any patent claims you can license that your contribution would infringe.
4. You have the right to make these grants. If your employer or school has rights to your work, you have
   its permission. Be kind: see [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
