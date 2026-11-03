from __future__ import annotations

import csv
import json
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
    code = run_main(
        check,
        [str(root / "examples/hallucination-test.csv"), "--notes", str(root / "sample/notes")],
        monkeypatch,
    )
    assert code == 1
    assert "FAIL: 3 problem(s)" in capsys.readouterr().out


# ---- diagram specs (.json) and AI-art citations ----

ROOT = Path(__file__).resolve().parents[1]
SPEC_FIXTURE = ROOT / "tests/fixtures/diagram-spec.json"
SAMPLE_NOTES = ROOT / "sample/notes"
SLIDE = "[[MICRO/Staphylococcus aureus (sample lecture)#S4]]"


def spec_copy(tmp_path, mutate=None):
    spec = json.loads(SPEC_FIXTURE.read_text(encoding="utf-8"))
    if mutate:
        mutate(spec)
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    return path


def run_spec(check, path, monkeypatch, capsys):
    code = run_main(check, [str(path), "--notes", str(SAMPLE_NOTES)], monkeypatch)
    return code, capsys.readouterr().out


def test_cited_spec_passes(check, monkeypatch, capsys):
    code, out = run_spec(check, SPEC_FIXTURE, monkeypatch, capsys)
    assert code == 0
    assert "4 nodes, 2 edges" in out
    assert "PASS" in out and "spot-check" in out


def test_node_with_empty_cite_fails_naming_id(check, tmp_path, monkeypatch, capsys):
    path = spec_copy(tmp_path, lambda s: s["nodes"][1].update(cite=""))
    code, out = run_spec(check, path, monkeypatch, capsys)
    assert code == 1 and "n2" in out and "no citation" in out


def test_edge_with_unknown_anchor_fails(check, tmp_path, monkeypatch, capsys):
    path = spec_copy(tmp_path, lambda s: s["edges"][0].update(cite="[[MICRO/Staphylococcus aureus (sample lecture)#S99]]"))
    code, out = run_spec(check, path, monkeypatch, capsys)
    assert code == 1 and "e1" in out and "S99" in out


def test_labeled_edge_needs_cite_unlabeled_does_not(check, tmp_path, monkeypatch, capsys):
    path = spec_copy(tmp_path, lambda s: s["edges"][0].pop("cite"))
    code, out = run_spec(check, path, monkeypatch, capsys)
    assert code == 1 and "e1" in out


def test_missing_nodes_is_readable_failure(check, tmp_path, monkeypatch, capsys):
    path = spec_copy(tmp_path, lambda s: s.pop("nodes"))
    code, out = run_spec(check, path, monkeypatch, capsys)
    assert code == 1 and "nodes" in out and "Traceback" not in out


def test_bad_json_is_readable_failure(check, tmp_path, monkeypatch, capsys):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    code, out = run_spec(check, path, monkeypatch, capsys)
    assert code == 1 and "JSON" in out and "Traceback" not in out


def test_non_object_spec_is_readable_failure(check, tmp_path, monkeypatch, capsys):
    path = tmp_path / "list.json"
    path.write_text("[1, 2]", encoding="utf-8")
    code, out = run_spec(check, path, monkeypatch, capsys)
    assert code == 1 and "Traceback" not in out


def test_duplicate_and_invalid_ids_fail(check, tmp_path, monkeypatch, capsys):
    def mutate(s):
        s["nodes"][1]["id"] = "n1"  # duplicate
        s["nodes"][2]["id"] = "Bad Id!"  # invalid
    code, out = run_spec(check, spec_copy(tmp_path, mutate), monkeypatch, capsys)
    assert code == 1 and "duplicate id" in out and "invalid id" in out


def test_edge_to_missing_node_fails(check, tmp_path, monkeypatch, capsys):
    path = spec_copy(tmp_path, lambda s: s["edges"][1].update(to="n99"))
    code, out = run_spec(check, path, monkeypatch, capsys)
    assert code == 1 and "e2" in out and "n99" in out


def test_node_missing_label_fails(check, tmp_path, monkeypatch, capsys):
    path = spec_copy(tmp_path, lambda s: s["nodes"][0].update(label=" "))
    code, out = run_spec(check, path, monkeypatch, capsys)
    assert code == 1 and "n1" in out and "label" in out


def test_art_citation_in_spec_is_unresolved(check, tmp_path, monkeypatch, capsys):
    path = spec_copy(tmp_path, lambda s: s["nodes"][0].update(cite="[[output/case1/art/staph.png#S1]]"))
    code, out = run_spec(check, path, monkeypatch, capsys)
    assert code == 1 and "AI illustrations are memory aids, not sources" in out


def test_art_citation_in_deck_and_guide_is_unresolved(check, notes, tmp_path, monkeypatch, capsys):
    # even when a notes file exists at that path, art is never a source
    art = notes / "output" / "case1" / "art"
    art.mkdir(parents=True)
    (art / "pic.md").write_text("## [S1] x\n", encoding="utf-8")
    deck = write_deck(tmp_path / "d.csv", [card("Q?", sources="[[output/case1/art/pic#S1]]")])
    assert run_main(check, [str(deck), "--notes", str(notes)], monkeypatch) == 1
    assert "AI illustrations are memory aids, not sources" in capsys.readouterr().out
    guide = tmp_path / "g.md"
    guide.write_text("# G\n\n- fact [[MICRO/x/art/pic#S1]]\n", encoding="utf-8")
    assert run_main(check, [str(guide), "--notes", str(notes)], monkeypatch) == 1
    assert "AI illustrations are memory aids, not sources" in capsys.readouterr().out


def test_is_art_path_helper(check):
    assert check.is_art_path("output/c/art/x")
    assert check.is_art_path("MICRO/art/x")
    assert not check.is_art_path("MICRO/Staph deck (sample)")
    assert not check.is_art_path("MICRO/article/x")


def _guide(tmp_path, cite):
    g = tmp_path / "g.md"
    g.write_text(f"# G\n\n- fact {cite}\n", encoding="utf-8")
    return g


def test_traversal_into_output_art_is_unresolved(check, notes, tmp_path, monkeypatch, capsys):
    # [[../../output/case/generated#S1]] from notes/ resolves to <tmp>/output/case/generated.md
    gen = tmp_path / "output" / "case"
    gen.mkdir(parents=True)
    (gen / "generated.md").write_text("## [S1] x\n", encoding="utf-8")
    g = _guide(tmp_path, "[[../../output/case/generated#S1]]")
    assert run_main(check, [str(g), "--notes", str(notes)], monkeypatch) == 1
    assert "points outside the notes folder" in capsys.readouterr().out


def test_traversal_outside_notes_is_unresolved(check, notes, tmp_path, monkeypatch, capsys):
    (tmp_path / "secret.md").write_text("## [S1] x\n", encoding="utf-8")
    g = _guide(tmp_path, "[[../secret#S1]]")
    assert run_main(check, [str(g), "--notes", str(notes)], monkeypatch) == 1
    assert "points outside the notes folder" in capsys.readouterr().out


def test_dotted_art_paths_still_unresolved(check, notes, tmp_path, monkeypatch, capsys):
    (notes / "MICRO" / "art").mkdir()
    (notes / "MICRO" / "art" / "pic.md").write_text("## [S1] x\n", encoding="utf-8")
    g = _guide(tmp_path, "[[MICRO/./art/pic#S1]] [[MICRO/x/../art/pic#S1]]")
    assert run_main(check, [str(g), "--notes", str(notes)], monkeypatch) == 1
    assert capsys.readouterr().out.count("AI illustrations are memory aids, not sources") == 2


def test_normal_citation_with_dot_segment_passes(check, notes, tmp_path, monkeypatch):
    g = _guide(tmp_path, "[[MICRO/./Staph deck (sample)#S3]]")
    assert run_main(check, [str(g), "--notes", str(notes)], monkeypatch) == 0


def test_numeric_label_fails_naming_id(check, tmp_path, monkeypatch, capsys):
    path = spec_copy(tmp_path, lambda s: s["nodes"][1].update(label=123))
    code, out = run_spec(check, path, monkeypatch, capsys)
    assert code == 1 and "n2" in out and "label" in out and "string" in out


def test_non_string_cite_fails_naming_id(check, tmp_path, monkeypatch, capsys):
    path = spec_copy(tmp_path, lambda s: s["nodes"][1].update(cite=["x"]))
    code, out = run_spec(check, path, monkeypatch, capsys)
    assert code == 1 and "n2" in out and "cite" in out and "string" in out
