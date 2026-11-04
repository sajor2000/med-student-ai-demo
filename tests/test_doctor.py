"""doctor tests: every probe is monkeypatched, nothing touches the network or the machine."""
from __future__ import annotations

import pytest

from conftest import load_script


@pytest.fixture
def doctor():
    return load_script("doctor")


def patch_all_ok(doctor, monkeypatch):
    monkeypatch.setattr(doctor, "run_cmd", lambda args: {
        "uv": "uv 0.12.0 (x)", "node": "v24.1.0", "npx": "10.0.0",
    }.get(args[0], ""))
    monkeypatch.setattr(doctor.shutil, "which", lambda name: f"/bin/{name}")
    monkeypatch.setattr(doctor, "http_head", lambda url, timeout=3.0: 200)
    monkeypatch.setattr(doctor, "anki_version", lambda url, timeout=2.0: 6)
    monkeypatch.setattr(doctor, "playwright_chromium", lambda: True)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-secret-value")
    monkeypatch.setattr(doctor, "git_ignored", lambda path: True)


def by_name(results):
    return {r.name: r for r in results}


def test_all_ok_exit_zero(doctor, monkeypatch):
    patch_all_ok(doctor, monkeypatch)
    results = doctor.collect()
    assert all(r.status == doctor.OK for r in results)
    assert doctor.exit_code(results) == 0


def test_node_too_old_is_required_failure(doctor, monkeypatch):
    patch_all_ok(doctor, monkeypatch)
    monkeypatch.setattr(doctor, "run_cmd", lambda a: {"uv": "uv 0.12.0", "node": "v22.1.0", "npx": "10"}.get(a[0], ""))
    res = by_name(doctor.collect())
    assert res["node"].status == doctor.FAIL
    assert "24" in res["node"].fix
    assert doctor.exit_code(list(res.values())) == 1


def test_missing_npx_fails(doctor, monkeypatch):
    patch_all_ok(doctor, monkeypatch)
    monkeypatch.setattr(doctor, "run_cmd", lambda a: {"uv": "uv 0.12.0", "node": "v24.0.0"}.get(a[0], ""))
    assert by_name(doctor.collect())["npx"].status == doctor.FAIL


def test_optional_items_only_warn(doctor, monkeypatch):
    patch_all_ok(doctor, monkeypatch)
    monkeypatch.setattr(doctor, "anki_version", lambda url, timeout=2.0: None)
    monkeypatch.setattr(doctor, "playwright_chromium", lambda: False)
    monkeypatch.delenv("OPENROUTER_API_KEY")
    res = by_name(doctor.collect())
    for name in ("anki", "playwright", "openrouter"):
        assert res[name].status == doctor.WARN
        assert res[name].fix
    assert doctor.exit_code(list(res.values())) == 0


def test_anki_wrong_version_warns(doctor, monkeypatch):
    patch_all_ok(doctor, monkeypatch)
    monkeypatch.setattr(doctor, "anki_version", lambda url, timeout=2.0: 5)
    assert by_name(doctor.collect())["anki"].status == doctor.WARN


def test_network_down_is_required_failure(doctor, monkeypatch):
    patch_all_ok(doctor, monkeypatch)
    monkeypatch.setattr(doctor, "http_head", lambda url, timeout=3.0: None)
    res = by_name(doctor.collect())
    assert res["network"].status == doctor.FAIL
    assert doctor.exit_code(list(res.values())) == 1


def test_unprotected_course_dir_fails(doctor, monkeypatch):
    patch_all_ok(doctor, monkeypatch)
    monkeypatch.setattr(doctor, "git_ignored", lambda path: path != "notes/")
    res = by_name(doctor.collect())
    assert res["gitignore"].status == doctor.FAIL
    assert "notes/" in res["gitignore"].detail
    assert doctor.exit_code(list(res.values())) == 1


def test_api_key_never_printed(doctor, monkeypatch, capsys):
    patch_all_ok(doctor, monkeypatch)
    code = doctor.main([])
    out = capsys.readouterr().out
    assert code == 0
    assert "sk-secret-value" not in out
    assert doctor.OK in out


def test_report_has_one_line_fix_per_problem(doctor, monkeypatch, capsys):
    patch_all_ok(doctor, monkeypatch)
    monkeypatch.setattr(doctor, "playwright_chromium", lambda: False)
    doctor.main([])
    out = capsys.readouterr().out
    assert doctor.WARN in out and "fix:" in out


def test_parse_node_major(doctor):
    assert doctor.parse_major("v24.1.0") == 24
    assert doctor.parse_major("garbage") is None


def test_final_policy_reminder(doctor, monkeypatch, capsys):
    patch_all_ok(doctor, monkeypatch)
    doctor.main([])
    assert "NOTICE.md" in capsys.readouterr().out.splitlines()[-1]


def test_run_cmd_resolves_with_which(doctor, monkeypatch):
    seen = {}
    monkeypatch.setattr(doctor.shutil, "which", lambda n: "C:\\node\\npx.cmd" if n == "npx" else None)

    class Done:
        returncode, stdout = 0, "10.0.0\n"

    def fake_run(args, **kw):
        seen["args"] = args
        return Done()

    monkeypatch.setattr(doctor.subprocess, "run", fake_run)
    assert doctor.run_cmd(["npx", "--version"]) == "10.0.0"
    assert seen["args"][0] == "C:\\node\\npx.cmd"
    assert doctor.run_cmd(["nope", "--version"]) == ""


def test_missing_git_is_required_failure_not_crash(doctor, monkeypatch):
    patch_all_ok(doctor, monkeypatch)
    monkeypatch.setattr(doctor, "git_ignored", lambda path: None)
    res = by_name(doctor.collect())
    assert res["gitignore"].status == doctor.FAIL
    assert "git" in res["gitignore"].fix
    assert doctor.exit_code(list(res.values())) == 1


def test_git_ignored_without_git(doctor, monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", lambda n: None)
    assert doctor.git_ignored("notes/") is None


def test_ascii_fallback_on_cp1252(doctor, monkeypatch, capsys):
    patch_all_ok(doctor, monkeypatch)
    monkeypatch.setattr(doctor, "stdout_encoding", lambda: "cp1252")
    doctor.main([])
    out = capsys.readouterr().out
    assert "[OK]" in out
    assert doctor.OK not in out


def test_node_fix_names_promise_try(doctor, monkeypatch):
    patch_all_ok(doctor, monkeypatch)
    monkeypatch.setattr(doctor, "run_cmd", lambda a: {"uv": "uv 0.12.0", "node": "v22.1.0", "npx": "10"}.get(a[0], ""))
    fix = by_name(doctor.collect())["node"].fix
    assert "Promise.try is not a function" in fix


def test_anki_probe_bypasses_proxies(doctor, monkeypatch):
    """A set HTTP_PROXY must not capture the loopback AnkiConnect probe."""
    seen = {}

    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self, *a): return b'{"result": 6, "error": null}'

    class FakeOpener:
        def open(self, req, timeout=None):
            seen["opener"] = True
            return FakeResp()

    real = doctor.urllib.request.build_opener
    def build(*handlers):
        seen["handlers"] = handlers
        return FakeOpener()
    monkeypatch.setattr(doctor.urllib.request, "build_opener", build)
    monkeypatch.setattr(doctor.urllib.request, "urlopen",
                        lambda *a, **k: pytest.fail("default opener honours proxies"))
    assert doctor.anki_version() == 6
    assert seen.get("opener")
    assert any(isinstance(h, doctor.urllib.request.ProxyHandler) and h.proxies == {}
               for h in seen["handlers"])


@pytest.mark.parametrize("stdout,expected", [
    (b".gitignore:5:notes/\tnotes/x\n", True),
    (b"sub/.gitignore:1:notes/\tnotes/x\n", True),
    (b".git/info/exclude:3:notes/\tnotes/x\n", False),
    (b"/home/u/.config/git/ignore:2:notes/\tnotes/x\n", False),
])
def test_git_ignored_requires_repo_gitignore(doctor, monkeypatch, stdout, expected):
    """A global ignore or .git/info/exclude must not count as the repo protecting the path."""
    monkeypatch.setattr(doctor.shutil, "which", lambda name: "/bin/git")
    class Done:
        returncode = 0
    Done.stdout = stdout
    monkeypatch.setattr(doctor.subprocess, "run", lambda *a, **k: Done)
    assert doctor.git_ignored("notes/") is expected
