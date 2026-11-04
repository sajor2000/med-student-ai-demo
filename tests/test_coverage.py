from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import load_script, run_main


@pytest.fixture
def cov():
    return load_script("coverage")


def make_notes(tmp_path: Path, line="- Learning objectives: (1) identify it; (2) link factors; (3) explain resistance") -> Path:
    d = tmp_path / "notes" / "MICRO"
    d.mkdir(parents=True)
    (d / "Deck.md").write_text(f"# Deck\n\n## [S1] Title\n{line}\n\n## [S2] More\n- x\n", encoding="utf-8")
    return tmp_path / "notes"


def make_csv(tmp_path: Path, tags: list[str]) -> Path:
    p = tmp_path / "cards.csv"
    lines = ["front,back,sources,tags"] + [f"q{i},a,[[x#S1]],{t}" for i, t in enumerate(tags)]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def make_vignettes(tmp_path: Path, objectives: list) -> Path:
    p = tmp_path / "v.json"
    items = [{"id": f"v{i}", **({"objective": o} if o is not None else {})} for i, o in enumerate(objectives)]
    p.write_text(json.dumps({"vignettes": items}), encoding="utf-8")
    return p


def test_card_and_vignette_leave_objective_one_uncovered(cov, tmp_path, monkeypatch, capsys):
    notes = make_notes(tmp_path)
    csv_ = make_csv(tmp_path, ["sample;obj2"])
    vig = make_vignettes(tmp_path, [3])
    rc = run_main(cov, ["--notes", str(notes), "--csv", str(csv_), "--vignettes", str(vig)], monkeypatch)
    out = capsys.readouterr().out
    assert rc == 0
    lines = out.splitlines()
    assert "UNCOVERED" in next(l for l in lines if l.startswith("(1)") or "1" in l.split()[0:2])
    assert "1 objective(s) uncovered" in out.splitlines()[-1]
    assert "1 card" in out and "1 vignette" in out
    assert out.count("UNCOVERED") == 1


def test_all_covered(cov, tmp_path, monkeypatch, capsys):
    notes = make_notes(tmp_path)
    csv_ = make_csv(tmp_path, ["obj1", "obj2;x", "obj2"])
    vig = make_vignettes(tmp_path, [3, None])
    assert run_main(cov, ["--notes", str(notes), "--csv", str(csv_), "--vignettes", str(vig)], monkeypatch) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[-1] == "all objectives covered"
    assert "2 cards" in out


def test_no_objectives(cov, tmp_path, monkeypatch, capsys):
    notes = make_notes(tmp_path, line="- nothing here")
    assert run_main(cov, ["--notes", str(notes)], monkeypatch) == 0
    assert "no objectives found" in capsys.readouterr().out


def test_obj12_does_not_cover_obj1(cov, tmp_path, monkeypatch, capsys):
    notes = make_notes(tmp_path)
    csv_ = make_csv(tmp_path, ["obj12", "obj10;obj2", "obj3"])
    assert run_main(cov, ["--notes", str(notes), "--csv", str(csv_)], monkeypatch) == 0
    out = capsys.readouterr().out
    assert "1 objective(s) uncovered" in out.splitlines()[-1]
    assert out.count("UNCOVERED") == 1


def test_csv_and_vignettes_optional(cov, tmp_path, monkeypatch, capsys):
    notes = make_notes(tmp_path)
    assert run_main(cov, ["--notes", str(notes)], monkeypatch) == 0
    assert "3 objective(s) uncovered" in capsys.readouterr().out


@pytest.mark.parametrize("flag", ["--csv", "--vignettes", "--notes"])
def test_nonexistent_path_is_argument_error(cov, tmp_path, monkeypatch, flag, capsys):
    notes = make_notes(tmp_path)
    argv = ["--notes", str(notes)]
    argv = [a for a in argv] if flag != "--notes" else []
    argv += [flag, str(tmp_path / "missing")]
    with pytest.raises(SystemExit) as e:
        run_main(cov, argv, monkeypatch)
    assert e.value.code == 2


def test_malformed_vignettes_json_exit_2(cov, tmp_path, monkeypatch, capsys):
    notes = make_notes(tmp_path)
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert run_main(cov, ["--notes", str(notes), "--vignettes", str(bad)], monkeypatch) == 2
    assert "bad.json" in capsys.readouterr().err


def test_objectives_from_multiple_files(cov, tmp_path, monkeypatch, capsys):
    notes = make_notes(tmp_path)
    (notes / "MICRO" / "Other.md").write_text("- Learning objectives: (4) another one\n", encoding="utf-8")
    assert run_main(cov, ["--notes", str(notes)], monkeypatch) == 0
    assert "4 objective(s) uncovered" in capsys.readouterr().out.splitlines()[-1]
