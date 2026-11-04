"""Docs hygiene: relative markdown links resolve, and the PR checklist runs as written."""
from __future__ import annotations

import re
import subprocess
import sys

from conftest import ROOT

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


def test_pr_template_check_command_runs():
    tpl = (ROOT / ".github" / "pull_request_template.md").read_text()
    m = re.search(r"`uv run (scripts/check\.py[^`]*)`", tpl)
    assert m, "no check.py command in PR template"
    args = m.group(1).split()[1:]
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "check.py"), *args],
                          cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode != 2, proc.stderr  # 2 = argparse usage error
