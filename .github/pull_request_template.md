## What and why

Reminder: Follow your institution's AI policy; never include course content or patient information.

## Checklist

- [ ] Tests green: `uv run --with pytest --with markdown --with genanki --with pillow --with playwright pytest tests -q`
- [ ] `uv run scripts/check.py examples/flashcards.csv --notes sample/notes` passes
- [ ] No course files, no patient information, no secrets (nothing from `curriculum/`, `notes/`, `output/`)
- [ ] Any new or changed skill is 40 lines or fewer (detail lives in `reference.md`)
- [ ] CHANGELOG.md updated under Unreleased
