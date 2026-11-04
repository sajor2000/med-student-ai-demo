"""Hand-run skills must be explicit-only in Codex too (it ignores disable-model-invocation)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".claude" / "skills"


def test_manual_skills_have_codex_policy():
    manual = [d for d in SKILLS.iterdir()
              if "disable-model-invocation: true" in (d / "SKILL.md").read_text()]
    assert {d.name for d in manual} == {"anki-sync", "mnemonic-art", "teach-back", "vignette", "visualize"}
    for d in manual:
        policy = (d / "agents" / "openai.yaml").read_text()
        assert "allow_implicit_invocation: false" in policy, d.name
