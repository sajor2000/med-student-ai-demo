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
