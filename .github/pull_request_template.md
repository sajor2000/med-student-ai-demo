## What and why

## Checklist

- [ ] Tests green: `uv run --with pytest --with markdown --with genanki --with pillow --with playwright pytest tests -q`
- [ ] `uv run scripts/check.py` passes on `examples/`
- [ ] No course files, no patient information, no secrets (nothing from `curriculum/`, `notes/`, `output/`)
- [ ] Any new or changed skill is 40 lines or fewer (detail lives in `reference.md`)
- [ ] CHANGELOG.md updated under Unreleased
