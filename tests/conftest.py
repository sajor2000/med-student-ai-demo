"""Shared fixtures. Scripts are standalone uv inline scripts, so tests load them by path.

Run: uv run --with pytest --with python-pptx --with python-docx --with markdown pytest tests -q
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"script_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def check():
    return load_script("check")


@pytest.fixture
def export():
    return load_script("export")


@pytest.fixture
def notes(tmp_path: Path) -> Path:
    """Synthetic notes folder shaped like extract.py output (slides, a Word doc, a table)."""
    d = tmp_path / "notes"
    (d / "MICRO").mkdir(parents=True)
    (d / "MICRO" / "Staph deck (sample).md").write_text(
        "# Staph deck (sample)\n\nSource: `Staph deck (sample).pptx` (slides)\n\n"
        "## [S1] Title slide\n- Synthetic\n\n"
        "## [S2] Lab identification\n- Catalase positive separates staph from strep\n\n"
        "## [S3] Toxins\n- Exfoliative toxin cleaves desmoglein-1\n",
        encoding="utf-8",
    )
    (d / "PHARM").mkdir()
    (d / "PHARM" / "Guide.md").write_text(
        "# Guide\n\nSource: `Guide.docx` (document)\n\n"
        "## [P1] Overview\n\n"
        "[P2] Beta-lactams inhibit cell wall synthesis.\n"
        "[P3] PBP2a has low affinity for beta-lactams.\n\n"
        "## [T1] Table 1\n| Drug | Class |\n| Vancomycin | Glycopeptide |\n",
        encoding="utf-8",
    )
    return d


def run_main(mod, argv: list[str], monkeypatch) -> int:
    monkeypatch.setattr(sys, "argv", ["prog", *argv])
    return mod.main()
