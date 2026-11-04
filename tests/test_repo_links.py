"""Docs hygiene: relative markdown links resolve, and the PR checklist runs as written."""
from __future__ import annotations

import re
import sys

from conftest import ROOT, load_script

# only the docs this repo ships for onboarding; docs/diagram-teaching-profile.md predates the PR
DOCS = [ROOT / "README.md", ROOT / "NOTICE.md", ROOT / "docs" / "FOR-EDUCATORS.md"]
LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")


def test_relative_markdown_links_resolve():
    broken = []
    for doc in DOCS:
        for target in LINK.findall(doc.read_text()):
            if re.match(r"[a-z]+:", target):
                continue
            if not (doc.parent / target).exists():
                broken.append(f"{doc.relative_to(ROOT)} -> {target}")
    assert not broken, broken


def test_doctor_policy_reminder_points_at_existing_file():
    text = (ROOT / "scripts" / "doctor.py").read_text()
    for path in re.findall(r"(?:docs/)?[A-Za-z-]+\.md", text):
        assert (ROOT / path).exists(), path


def test_pr_template_check_command_runs(monkeypatch, capsys):
    """Run the template's check.py command in-process with the PubMed lookup mocked (offline)."""
    tpl = (ROOT / ".github" / "pull_request_template.md").read_text()
    m = re.search(r"`uv run (scripts/check\.py[^`]*)`", tpl)
    assert m, "no check.py command in PR template"
    args = m.group(1).split()[1:]
    check = load_script("check")
    monkeypatch.setattr(check, "pubmed_summaries",
                        lambda pmids: {p: {"pubdate": "2000", "title": "t", "pubtype": []} for p in pmids})
    monkeypatch.setattr(sys, "argv", ["check.py", *args])
    monkeypatch.chdir(ROOT)
    assert check.main() == 0, capsys.readouterr().out


def test_educator_data_flow_is_accurate():
    text = (ROOT / "docs" / "FOR-EDUCATORS.md").read_text()
    assert "No course text is sent" not in text
    assert "course-derived" in text  # /mnemonic-art prompt may carry course concepts
    assert "EMBL-EBI" in text  # Europe PMC is not NCBI


def test_citation_has_no_unverifiable_release_date():
    """CHANGELOG entries carry no dates and no release tag exists, so CITATION.cff must not invent one."""
    cff = (ROOT / "CITATION.cff").read_text()
    assert "date-released" not in cff
    version = re.search(r"^version:\s*(\S+)", cff, re.M).group(1)
    assert re.search(rf"^## \[{re.escape(version)}\]", (ROOT / "CHANGELOG.md").read_text(), re.M)
