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


@pytest.mark.parametrize("flag", ["--vignettes", "--notes"])
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


def make_two_lectures(tmp_path: Path) -> Path:
    notes = make_notes(tmp_path)  # MICRO/Deck.md: (1)-(3)
    (notes / "MICRO" / "Other Lecture.md").write_text(
        "- Learning objectives: (1) second one; (2) second two; (3) second three\n", encoding="utf-8")
    return notes


def test_same_numbers_in_two_files_stay_separate(cov, tmp_path, monkeypatch, capsys):
    notes = make_two_lectures(tmp_path)
    assert run_main(cov, ["--notes", str(notes)], monkeypatch) == 0
    out = capsys.readouterr().out
    assert "6 objective(s) uncovered" in out.splitlines()[-1]
    assert "[micro-deck] (1) identify it" in out and "[micro-other-lecture] (1) second one" in out


def test_qualified_card_tag_covers_only_its_lecture(cov, tmp_path, monkeypatch, capsys):
    notes = make_two_lectures(tmp_path)
    csv_path = make_csv(tmp_path, ["x;micro-other-lecture-obj2"])
    assert run_main(cov, ["--notes", str(notes), "--csv", str(csv_path)], monkeypatch) == 0
    out = capsys.readouterr().out
    assert "[micro-other-lecture] (2) second two: covered (1 card)" in out
    assert "[micro-deck] (2) link factors: UNCOVERED" in out
    assert "5 objective(s) uncovered" in out.splitlines()[-1]


def test_qualified_vignette_lecture_field(cov, tmp_path, monkeypatch, capsys):
    notes = make_two_lectures(tmp_path)
    p = tmp_path / "v.json"
    p.write_text(json.dumps({"vignettes": [{"id": "a", "objective": 3, "lecture": "micro-deck"}]}), encoding="utf-8")
    assert run_main(cov, ["--notes", str(notes), "--vignettes", str(p)], monkeypatch) == 0
    out = capsys.readouterr().out
    assert "[micro-deck] (3) explain resistance: covered (1 vignette)" in out
    assert "[micro-other-lecture] (3) second three: UNCOVERED" in out


def test_unqualified_tag_on_ambiguous_number_warns_and_covers_nothing(cov, tmp_path, monkeypatch, capsys):
    notes = make_two_lectures(tmp_path)
    csv_path = make_csv(tmp_path, ["x;obj1"])
    assert run_main(cov, ["--notes", str(notes), "--csv", str(csv_path)], monkeypatch) == 0
    out = capsys.readouterr().out
    assert "obj1 is ambiguous" in out and "micro-deck-obj1" in out and "micro-other-lecture-obj1" in out
    assert "6 objective(s) uncovered" in out.splitlines()[-1]


def test_same_basename_in_two_folders_stays_separate(cov, tmp_path, monkeypatch, capsys):
    notes = tmp_path / "notes"
    for folder, line in (("MICRO", "(1) micro one; (2) micro two"), ("PHARM", "(1) pharm one; (2) pharm two")):
        (notes / folder).mkdir(parents=True)
        (notes / folder / "Lecture 1.md").write_text(f"- Learning objectives: {line}\n", encoding="utf-8")
    assert run_main(cov, ["--notes", str(notes)], monkeypatch) == 0
    out = capsys.readouterr().out
    assert "4 objective(s) uncovered" in out.splitlines()[-1]
    assert "[micro-lecture-1] (1) micro one" in out and "[pharm-lecture-1] (1) pharm one" in out


def test_missing_csv_counts_zero_cards_with_a_note(cov, tmp_path, monkeypatch, capsys):
    notes = make_notes(tmp_path)
    assert run_main(cov, ["--notes", str(notes), "--csv", str(tmp_path / "none.csv")], monkeypatch) == 0
    out = capsys.readouterr().out
    assert "none.csv" in out and "0 cards" in out and "3 objective(s) uncovered" in out.splitlines()[-1]


def test_directory_as_vignettes_is_argument_error(cov, tmp_path, monkeypatch):
    notes = make_notes(tmp_path)
    with pytest.raises(SystemExit) as e:
        run_main(cov, ["--notes", str(notes), "--vignettes", str(tmp_path)], monkeypatch)
    assert e.value.code == 2


def test_file_as_notes_is_argument_error(cov, tmp_path, monkeypatch):
    f = tmp_path / "f.md"
    f.write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        run_main(cov, ["--notes", str(f)], monkeypatch)
    assert e.value.code == 2


def test_directory_as_csv_is_argument_error(cov, tmp_path, monkeypatch):
    notes = make_notes(tmp_path)
    with pytest.raises(SystemExit) as e:
        run_main(cov, ["--notes", str(notes), "--csv", str(tmp_path)], monkeypatch)
    assert e.value.code == 2
