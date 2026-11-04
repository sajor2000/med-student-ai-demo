# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Check that this machine is ready to run the study loop.

Prints one line per check (OK / WARN / FAIL) with a one-line fix for anything
not OK. Exit 1 only when a required item fails; optional items only warn.
Prints no secrets and no file contents.

Usage:
    uv run scripts/doctor.py
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

OK, WARN, FAIL = "✅", "⚠️ ", "❌"
ROOT = Path(__file__).resolve().parents[1]
PROTECTED = ("curriculum/", "notes/", "output/")
NCBI_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi"
ANKI_URL = "http://127.0.0.1:8765"


class Result:
    def __init__(self, name: str, status: str, detail: str, fix: str = "", required: bool = True):
        self.name, self.status, self.detail = name, status, detail
        self.fix, self.required = fix, required


def run_cmd(args: list[str]) -> str:
    """Return stdout of a command, or '' if it is missing or fails."""
    exe = shutil.which(args[0])  # resolves npx.cmd etc. on Windows
    if not exe:
        return ""
    try:
        done = subprocess.run([exe, *args[1:]], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def http_head(url: str, timeout: float = 3.0) -> int | None:
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as err:
        return err.code  # the server answered, so the network works
    except (OSError, ValueError):
        return None


def anki_version(url: str = ANKI_URL, timeout: float = 2.0) -> int | None:
    body = json.dumps({"action": "version", "version": 6}).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    try:
        # loopback probe: never route through HTTP_PROXY (matches anki_sync.py)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=timeout) as resp:
            data = json.load(resp)
            return data.get("result") if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def playwright_chromium() -> bool:
    """True when Playwright imports and its Chromium binary exists."""
    code = ("from playwright.sync_api import sync_playwright\n"
            "import os\n"
            "with sync_playwright() as p:\n"
            "    raise SystemExit(0 if os.path.exists(p.chromium.executable_path) else 1)\n")
    uv = shutil.which("uv")
    if not uv:
        return False
    try:
        done = subprocess.run([uv, "run", "--with", "playwright", "python", "-c", code],
                              capture_output=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


def git_ignored(path: str) -> bool | None:
    """True/False for the ignore rule; None when git is missing or cannot run."""
    git = shutil.which("git")
    if not git:
        return None
    try:
        done = subprocess.run([git, "-C", str(ROOT), "check-ignore", "-v", path + "x"],
                              capture_output=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return False
    # -v prints "<source>:<line>:<pattern>\t<path>"; only the repo's own .gitignore counts,
    # not a global ignore file or .git/info/exclude.
    source = done.stdout.decode(errors="replace").split(":", 1)[0]
    src = Path(source)
    if not src.is_absolute():
        src = ROOT / src  # git prints repo-relative paths for the repo's own files
    return src.name == ".gitignore" and ROOT.resolve() in src.resolve().parents


def parse_major(text: str) -> int | None:
    m = re.search(r"(\d+)\.\d+", text)
    return int(m.group(1)) if m else None


def check_uv() -> Result:
    out = run_cmd(["uv", "--version"])
    if out:
        return Result("uv", OK, out)
    return Result("uv", FAIL, "not found", "install uv: https://docs.astral.sh/uv/getting-started/installation/")


def check_python() -> Result:
    v = sys.version_info
    if v >= (3, 11):
        return Result("python", OK, f"{v.major}.{v.minor}")
    return Result("python", FAIL, f"{v.major}.{v.minor}", "run `uv python install 3.12`")


def check_node() -> Result:
    out = run_cmd(["node", "--version"])
    major = parse_major(out)
    fix = ("install Node 24 or newer from https://nodejs.org; the PubMed MCP server "
           "fails on Node 22 with \"Promise.try is not a function\"")
    if major is None:
        return Result("node", FAIL, "not found", fix)
    if major < 24:
        return Result("node", FAIL, f"{out} (need 24+)", fix)
    return Result("node", OK, out)


def check_npx() -> Result:
    out = run_cmd(["npx", "--version"])
    if out:
        return Result("npx", OK, out)
    return Result("npx", FAIL, "not found", "reinstall Node from https://nodejs.org; npx ships with it")


def check_network() -> Result:
    status = http_head(NCBI_URL, 3.0)
    if status is not None:
        return Result("network", OK, "eutils.ncbi.nlm.nih.gov reachable")
    return Result("network", FAIL, "eutils.ncbi.nlm.nih.gov unreachable",
                  "check wifi/VPN; PubMed lookups and citation checks need it")


def check_anki() -> Result:
    v = anki_version(ANKI_URL, 2.0)
    if v == 6:
        return Result("anki", OK, "AnkiConnect v6 on 127.0.0.1:8765", required=False)
    detail = "not running" if v is None else f"API version {v}, need 6"
    return Result("anki", WARN, detail,
                  "optional: open Anki and install the AnkiConnect add-on (code 2055492159)", False)


def check_playwright() -> Result:
    if playwright_chromium():
        return Result("playwright", OK, "Chromium available", required=False)
    return Result("playwright", WARN, "Chromium not installed",
                  "optional (diagram cards): `uv run --with playwright playwright install chromium`", False)


def check_openrouter() -> Result:
    if os.environ.get("OPENROUTER_API_KEY"):
        return Result("openrouter", OK, "OPENROUTER_API_KEY set", required=False)
    return Result("openrouter", WARN, "OPENROUTER_API_KEY not set",
                  "optional: export OPENROUTER_API_KEY in your shell profile", False)


def check_gitignore() -> Result:
    states = {p: git_ignored(p) for p in PROTECTED}
    if None in states.values():
        return Result("gitignore", FAIL, "git not available",
                      "install git (https://git-scm.com) so the ignore rules can be checked")
    missing = [p for p, ok in states.items() if not ok]
    if not missing:
        return Result("gitignore", OK, "curriculum/ notes/ output/ are git-ignored")
    return Result("gitignore", FAIL, "not ignored: " + ", ".join(missing),
                  "restore the .gitignore lines from the repo so course files can never be committed")


CHECKS = (check_uv, check_python, check_node, check_npx, check_network,
          check_anki, check_playwright, check_openrouter, check_gitignore)


def collect() -> list[Result]:
    return [c() for c in CHECKS]


def exit_code(results: list[Result]) -> int:
    return 1 if any(r.required and r.status == FAIL for r in results) else 0


def stdout_encoding() -> str:
    return getattr(sys.stdout, "encoding", None) or "ascii"


def labels() -> dict[str, str]:
    """Emoji labels, or ASCII ones when stdout cannot encode them (e.g. cp1252)."""
    try:
        for s in (OK, WARN, FAIL):
            s.encode(stdout_encoding())
    except (UnicodeEncodeError, LookupError):
        return {OK: "[OK]  ", WARN: "[WARN]", FAIL: "[FAIL]"}
    return {OK: OK, WARN: WARN, FAIL: FAIL}


def main(argv: list[str] | None = None) -> int:
    results = collect()
    mark = labels()
    for r in results:
        tag = "" if r.required else " (optional)"
        print(f"{mark[r.status]} {r.name}{tag}: {r.detail}")
        if r.status != OK and r.fix:
            print(f"     fix: {r.fix}")
    print("\nBefore using real course materials, confirm your school's AI policy allows it"
          " - see NOTICE.md")
    return exit_code(results)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
