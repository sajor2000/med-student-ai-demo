from __future__ import annotations

import csv
from pathlib import Path

from conftest import run_main

DECK = "[[MICRO/Staph deck (sample)#S3]]"


def write_deck(path: Path, rows: list[dict]) -> Path:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["front", "back", "sources", "tags"])
        w.writeheader()
        for r in rows:
            w.writerow({"tags": "t", "back": "", **r})
    return path


def card(front, sources=DECK, back=""):
    return {"front": front, "back": back, "sources": sources}


def test_valid_cloze_card_passes(check, notes, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "d.csv", [card("Exfoliative toxin cleaves {{c1::desmoglein-1}}.")])
    assert run_main(check, [str(deck), "--notes", str(notes)], monkeypatch) == 0


def test_cloze_with_hint_and_multiple_deletions_pass(check, notes, tmp_path, monkeypatch):
    deck = write_deck(
        tmp_path / "d.csv",
        [
            card("Toxin cleaves {{c1::desmoglein-1::protein}}."),
            card("{{c1::Catalase}} separates {{c2::staph}} from strep.", "[[MICRO/Staph deck (sample)#S2]]"),
        ],
    )
    assert run_main(check, [str(deck), "--notes", str(notes)], monkeypatch) == 0


def test_malformed_cloze_fails(check, notes, tmp_path, monkeypatch, capsys):
    deck = write_deck(
        tmp_path / "d.csv",
        [
            card("Unclosed {{c1::desmoglein-1 here"),
            card("No number {{c::desmoglein-1}}"),
            card("Empty {{c1::}} deletion"),
        ],
    )
    assert run_main(check, [str(deck), "--notes", str(notes)], monkeypatch) == 1
    out = capsys.readouterr().out
    assert out.count("cloze") >= 3
    assert "Unclosed" in out and "No number" in out and "Empty" in out


def test_cloze_card_still_needs_citation(check, notes, tmp_path, monkeypatch, capsys):
    deck = write_deck(tmp_path / "d.csv", [card("Toxin cleaves {{c1::desmoglein-1}}.", sources="")])
    assert run_main(check, [str(deck), "--notes", str(notes)], monkeypatch) == 1
    assert "no citation" in capsys.readouterr().out


def test_basic_card_with_empty_back_unchanged(check, notes, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "d.csv", [card("Which enzyme separates staph from strep?", back="")])
    assert run_main(check, [str(deck), "--notes", str(notes)], monkeypatch) == 0


def test_template_like_text_is_not_cloze(check, notes, tmp_path, monkeypatch):
    deck = write_deck(tmp_path / "d.csv", [card("Explain {{class}} of this drug?")])
    assert run_main(check, [str(deck), "--notes", str(notes)], monkeypatch) == 0


def test_cloze_helpers(check):
    assert check.cloze_problems("ok {{c1::a}} and {{c2::b::hint}}") == []
    assert check.cloze_problems("bad {{c1::a")
    assert check.cloze_problems("bad {{c::a}}")
    assert check.cloze_problems("bad {{c1::}}")


def test_hallucination_example_still_reports_three(check, monkeypatch, capsys):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setattr(check, "pubmed_summaries", lambda pmids: {})  # deterministic: PMID "does not exist"
    code = run_main(
        check,
        [str(root / "examples/hallucination-test.csv"), "--notes", str(root / "sample/notes")],
        monkeypatch,
    )
    assert code == 1
    assert "FAIL: 3 problem(s)" in capsys.readouterr().out
