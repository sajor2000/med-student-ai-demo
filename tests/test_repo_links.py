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


MESSAGE_FILES = ["README.md", "AGENTS.md", "docs/DEMO-WALKTHROUGH.md", "docs/RESPONSIBLE-USE.md"]
MESSAGE_MARKERS = {
    "educational demo": r"educational demo",
    "AI powers learning, does not replace it": r"(power|augment)\w*[^.\n]{0,40}(learning|learn)|not replace",
    "materials belong to the institution": r"belong\w* to (your|the) (institution|school|medical school)",
    "institution's AI policy": r"(institution|school)['’]s AI policy|AI policy",
}


def test_responsible_use_message_in_key_docs():
    missing = []
    for name in MESSAGE_FILES:
        text = (ROOT / name).read_text()
        for label, pattern in MESSAGE_MARKERS.items():
            if not re.search(pattern, text, re.IGNORECASE):
                missing.append(f"{name}: {label}")
    assert not missing, missing


def test_readme_links_required_files_and_they_exist():
    readme = (ROOT / "README.md").read_text()
    required = ["docs/FOR-EDUCATORS.md", "CONTRIBUTING.md", "SECURITY.md",
                "CODE_OF_CONDUCT.md", "CHANGELOG.md", "NOTICE.md", "LICENSE", "LICENSE-CONTENT"]
    for target in required:
        assert f"]({target})" in readme, f"README does not link {target}"
        assert (ROOT / target).exists(), target
    assert "scripts/doctor.py" in readme
    assert "MIT" in readme and "CC BY 4.0" in readme


def test_demo_walkthrough_shows_every_screenshot_and_keeps_them_small():
    walkthrough = (ROOT / "docs" / "DEMO-WALKTHROUGH.md").read_text()
    shots = sorted((ROOT / "docs" / "img" / "demo").glob("*.png"))
    assert shots, "no demo screenshots"
    for png in shots:
        assert f"img/demo/{png.name}" in walkthrough, f"{png.name} is not shown in DEMO-WALKTHROUGH.md"
        assert png.stat().st_size <= 260_000, f"{png.name} is over 260 KB"
    for target in LINK.findall(walkthrough):
        if not re.match(r"[a-z]+:", target):
            assert (ROOT / "docs" / target).exists(), target
