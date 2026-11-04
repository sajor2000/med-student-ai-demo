"""Hand-run skills must be explicit-only in Codex too (it ignores disable-model-invocation)."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".claude" / "skills"


def test_manual_skills_have_codex_policy():
    manual = [d for d in SKILLS.iterdir()
              if "disable-model-invocation: true" in (d / "SKILL.md").read_text()]
    assert {d.name for d in manual} == {"anki-sync", "mnemonic-art", "teach-back", "vignette", "visualize"}
    for d in manual:
        policy = (d / "agents" / "openai.yaml").read_text()
        assert "allow_implicit_invocation: false" in policy, d.name


def test_flashcards_skill_runs_coverage_before_writing_cards():
    """A deck of N cards should close objective gaps first, not pile onto objectives already covered."""
    text = (SKILLS / "flashcards" / "SKILL.md").read_text()
    write_step = text.index("Write `output/<case>/flashcards.csv`")
    assert "scripts/coverage.py" in text[:write_step]
    assert "UNCOVERED" in text[:write_step]
    assert "--vignettes" in text[:write_step]  # vignettes already cover objectives; do not duplicate them


def test_flashcards_skill_stays_within_the_forty_line_cap():
    assert len((SKILLS / "flashcards" / "SKILL.md").read_text().splitlines()) <= 40


def _frontmatter(skill: Path) -> list[str]:
    parts = (skill / "SKILL.md").read_text().split("---\n")
    assert parts[0] == "" and len(parts) >= 3, f"{skill.name}: missing frontmatter"
    return parts[1].splitlines()


def test_skill_frontmatter_is_strict_yaml():
    """Claude Code reads these leniently; Codex and other YAML loaders reject the file and drop the skill."""
    problems = []
    for d in sorted(SKILLS.iterdir()):
        for line in _frontmatter(d):
            key, _, value = line.partition(":")
            value = value.strip()
            if not value:
                continue
            if value[0] in "\"'":
                if len(value) < 2 or value[-1] != value[0]:
                    problems.append(f"{d.name}: {key} starts with a quote but does not end with one")
            elif ": " in value or value.endswith(":") or " #" in value:
                problems.append(f"{d.name}: {key} has an unquoted ': ' or ' #' in its value")
    assert not problems, problems


def test_skill_frontmatter_loads_with_a_real_yaml_parser():
    yaml = pytest.importorskip("yaml")
    for d in sorted(SKILLS.iterdir()):
        meta = yaml.safe_load("\n".join(_frontmatter(d)))
        assert meta["name"] == d.name
        assert isinstance(meta["description"], str) and meta["description"]
