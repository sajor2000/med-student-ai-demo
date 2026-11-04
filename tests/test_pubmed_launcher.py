"""scripts/pubmed-mcp.sh refuses Node < 24 and proceeds on Node >= 24 (offline: fake node, fake exec target)."""
from __future__ import annotations

import os
import subprocess

import pytest

from conftest import ROOT

SCRIPT = ROOT / "scripts" / "pubmed-mcp.sh"
BASH = "/bin/bash"


def _fake(path, body):
    path.write_text("#!/bin/sh\n" + body + "\n")
    path.chmod(0o755)


def _run(tmp_path, version, extra_env=None):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    _fake(bindir / "node", f'echo "{version}"' if version else "exit 1")
    target = tmp_path / "fake-cmd"
    _fake(target, 'echo "LAUNCHED node=$(command -v node)"')
    env = {"PATH": f"{bindir}:/usr/bin:/bin", "PUBMED_MCP_CMD": str(target)}
    env.update(extra_env or {})
    return subprocess.run([BASH, str(SCRIPT)], env=env, capture_output=True, text=True), bindir


def test_script_is_executable():
    assert os.access(SCRIPT, os.X_OK)


@pytest.mark.skipif(any(os.access(p, os.X_OK) for p in ("/opt/homebrew/bin/node", "/usr/local/bin/node")),
                    reason="a system node >= 22 fallback may exist on this machine")
def test_node_22_is_rejected(tmp_path):
    r, _ = _run(tmp_path, "v22.11.0")
    assert r.returncode == 1
    assert "PubMed connector needs Node 24+" in r.stderr
    assert "LAUNCHED" not in r.stdout


def test_node_24_proceeds_with_its_dir_first(tmp_path):
    r, bindir = _run(tmp_path, "v24.1.0")
    assert r.returncode == 0, r.stderr
    assert f"LAUNCHED node={bindir}/node" in r.stdout


def test_env_override_node(tmp_path):
    good = tmp_path / "good"
    good.mkdir()
    _fake(good / "node", 'echo "v25.0.0"')
    r, _ = _run(tmp_path, "v22.0.0", {"PUBMED_MCP_NODE": str(good / "node")})
    assert r.returncode == 0, r.stderr
    assert f"LAUNCHED node={good}/node" in r.stdout
