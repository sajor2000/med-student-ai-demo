from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

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


def test_missing_file_is_a_clean_failure(check, notes, tmp_path, monkeypatch, capsys):
    assert run_main(check, [str(tmp_path / "nope.md"), "--notes", str(notes)], monkeypatch) == 1
    assert "no such file" in capsys.readouterr().out


def test_crlf_inside_pmid_citation_is_checked(check, notes, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(check, "pubmed_summaries", lambda pmids: {})
    deck = write_deck(tmp_path / "d.csv", [card("Q?", sources="[PMID:\r\n99999999]")])
    assert run_main(check, [str(deck), "--notes", str(notes)], monkeypatch) == 1
    assert "PMID:99999999 does not exist" in capsys.readouterr().out


@pytest.mark.parametrize("bad", [["n1"], {"id": "n1"}, 7])
def test_non_string_edge_endpoint_is_readable_failure(check, tmp_path, monkeypatch, capsys, bad):
    path = spec_copy(tmp_path, lambda s: s["edges"][0].__setitem__("from", bad))
    code, out = run_spec(check, path, monkeypatch, capsys)
    assert code == 1 and "not a node id" in out and "Traceback" not in out


# ---- vignette files ----

CITE_OK = "[[MICRO/Staph deck (sample)#S3]]"


def make_vignette(vid="v1", **over):
    opts = [
        {"key": k, "text": f"Option {k}", "correct": k == "A", "explanation": f"Because {k}. {CITE_OK}"}
        for k in "ABCDE"
    ]
    v = {"id": vid, "objective": 2, "discipline": "MICRO", "stem": "A synthetic patient has a rash.", "options": opts}
    v.update(over)
    return v


def write_vignettes(tmp_path, vignettes):
    p = tmp_path / "vignettes.json"
    p.write_text(json.dumps({"vignettes": vignettes}), encoding="utf-8")
    return p


def run_vig(check, notes, path, monkeypatch, capsys):
    code = run_main(check, [str(path), "--notes", str(notes)], monkeypatch)
    return code, capsys.readouterr().out


def mutated(fn, vid="v1"):
    v = make_vignette(vid)
    fn(v)
    return v


def test_pmid_digits_in_a_citation_are_not_phi(check, notes, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(check, "pubmed_summaries", lambda pmids: {p: {"title": "T", "pubdate": "2024"} for p in pmids})
    v = mutated(lambda v: v["options"][0].update(explanation=v["options"][0]["explanation"] + " [PMID:38247655]"))
    code, out = run_vig(check, notes, write_vignettes(tmp_path, [v]), monkeypatch, capsys)
    assert code == 0 and "PMID:38247655" in out


def test_bad_citation_in_stem_fails(check, notes, tmp_path, monkeypatch, capsys):
    v = mutated(lambda v: v.update(stem=v["stem"] + " See [[MICRO/does-not-exist#S99]]."), "vx")
    code, out = run_vig(check, notes, write_vignettes(tmp_path, [v]), monkeypatch, capsys)
    assert code == 1 and "stem" in out and "does-not-exist" in out


def test_bad_citation_in_option_text_fails(check, notes, tmp_path, monkeypatch, capsys):
    v = mutated(lambda v: v["options"][1].update(text=v["options"][1]["text"] + " [[MICRO/does-not-exist#S99]]"), "vx")
    code, out = run_vig(check, notes, write_vignettes(tmp_path, [v]), monkeypatch, capsys)
    assert code == 1 and "does-not-exist" in out


def test_stem_without_citation_still_passes(check, notes, tmp_path, monkeypatch, capsys):
    code, out = run_vig(check, notes, write_vignettes(tmp_path, [make_vignette("v1")]), monkeypatch, capsys)
    assert code == 0


def test_valid_vignette_file_passes(check, notes, tmp_path, monkeypatch, capsys):
    p = write_vignettes(tmp_path, [make_vignette("v1"), make_vignette("v2", objective=1)])
    code, out = run_vig(check, notes, p, monkeypatch, capsys)
    assert code == 0 and "2 vignettes" in out and "PASS" in out


def test_vignette_optional_fields_may_be_absent(check, notes, tmp_path, monkeypatch, capsys):
    v = make_vignette()
    del v["objective"], v["discipline"]
    code, _ = run_vig(check, notes, write_vignettes(tmp_path, [v]), monkeypatch, capsys)
    assert code == 0


@pytest.mark.parametrize("count", [4, 6])
def test_wrong_option_count_fails(check, notes, tmp_path, monkeypatch, capsys, count):
    def f(v):
        v["options"] = [dict(v["options"][0], key=k, correct=k == "A") for k in "ABCDEF"[:count]]
    code, out = run_vig(check, notes, write_vignettes(tmp_path, [mutated(f, "vx")]), monkeypatch, capsys)
    assert code == 1 and "vx" in out and "5 options" in out


def test_duplicate_option_keys_fail(check, notes, tmp_path, monkeypatch, capsys):
    code, out = run_vig(
        check, notes, write_vignettes(tmp_path, [mutated(lambda v: v["options"][1].update(key="A"), "vx")]),
        monkeypatch, capsys,
    )
    assert code == 1 and "vx" in out and "keys" in out


@pytest.mark.parametrize("flags", [[False] * 5, [True, True, False, False, False]])
def test_zero_or_two_correct_fail(check, notes, tmp_path, monkeypatch, capsys, flags):
    def f(v):
        for o, c in zip(v["options"], flags):
            o["correct"] = c
    code, out = run_vig(check, notes, write_vignettes(tmp_path, [mutated(f, "vx")]), monkeypatch, capsys)
    assert code == 1 and "vx" in out and "exactly one correct" in out


@pytest.mark.parametrize("expl", ["", "   ", "No citation here."])
def test_empty_or_uncited_explanation_fails(check, notes, tmp_path, monkeypatch, capsys, expl):
    p = write_vignettes(tmp_path, [mutated(lambda v: v["options"][2].update(explanation=expl), "vx")])
    code, out = run_vig(check, notes, p, monkeypatch, capsys)
    assert code == 1 and "vx" in out and "C" in out and "explanation" in out


def test_missing_anchor_in_explanation_fails(check, notes, tmp_path, monkeypatch, capsys):
    bad = "Because. [[MICRO/Staph deck (sample)#S99]]"
    p = write_vignettes(tmp_path, [mutated(lambda v: v["options"][0].update(explanation=bad), "vx")])
    code, out = run_vig(check, notes, p, monkeypatch, capsys)
    assert code == 1 and "vx" in out and "S99" in out


def test_vitals_in_stem_are_not_flagged_as_name_with_age(check, notes, tmp_path, monkeypatch, capsys):
    stem = "Vitals: Pulse, 110 bpm, Temperature, 39 C, Respirations, 22 /min. A wound swab grows gram-positive cocci."
    p = write_vignettes(tmp_path, [mutated(lambda v: v.update(stem=stem), "vx")])
    code, out = run_vig(check, notes, p, monkeypatch, capsys)
    assert code == 0, out


def test_phi_in_discipline_fails(check, notes, tmp_path, monkeypatch, capsys):
    p = write_vignettes(tmp_path, [mutated(lambda v: v.update(discipline="Maria, 45"), "vx")])
    code, out = run_vig(check, notes, p, monkeypatch, capsys)
    assert code == 1 and "discipline" in out


@pytest.mark.parametrize(
    "stem",
    [
        "Patient MRN 12345678 presents with a rash.",
        "Seen on 03/14/2024 with a rash.",
        "Seen on 2024-03-14 with a rash.",
        "Maria, 45 presents with a rash.",
    ],
)
def test_phi_shaped_stem_fails(check, notes, tmp_path, monkeypatch, capsys, stem):
    p = write_vignettes(tmp_path, [mutated(lambda v: v.update(stem=stem), "vx")])
    code, out = run_vig(check, notes, p, monkeypatch, capsys)
    assert code == 1 and "vx" in out and "stem" in out


def test_phi_in_option_text_fails(check, notes, tmp_path, monkeypatch, capsys):
    p = write_vignettes(tmp_path, [mutated(lambda v: v["options"][3].update(text="DOB noted"), "vx")])
    code, out = run_vig(check, notes, p, monkeypatch, capsys)
    assert code == 1 and "vx" in out and "D" in out


@pytest.mark.parametrize("obj", [0, "two", -1, True, 1.5])
def test_bad_objective_fails(check, notes, tmp_path, monkeypatch, capsys, obj):
    p = write_vignettes(tmp_path, [mutated(lambda v: v.update(objective=obj), "vx")])
    code, out = run_vig(check, notes, p, monkeypatch, capsys)
    assert code == 1 and "vx" in out and "objective" in out


def test_vignette_duplicate_and_invalid_ids_fail(check, notes, tmp_path, monkeypatch, capsys):
    p = write_vignettes(tmp_path, [make_vignette("same"), make_vignette("same"), make_vignette("Bad Id")])
    code, out = run_vig(check, notes, p, monkeypatch, capsys)
    assert code == 1 and "duplicate id" in out and "invalid id" in out


def test_empty_stem_fails(check, notes, tmp_path, monkeypatch, capsys):
    p = write_vignettes(tmp_path, [mutated(lambda v: v.update(stem=" "), "vx")])
    code, out = run_vig(check, notes, p, monkeypatch, capsys)
    assert code == 1 and "vx" in out and "stem" in out


def test_json_without_vignettes_key_is_diagram_spec_failure(check, notes, tmp_path, monkeypatch, capsys):
    p = tmp_path / "other.json"
    p.write_text(json.dumps({"stuff": []}), encoding="utf-8")
    code, out = run_vig(check, notes, p, monkeypatch, capsys)
    assert code == 1 and "nodes" in out and "vignettes" not in out.split("FAIL")[0]


def test_vignettes_not_a_list_or_empty_fails_readably(check, notes, tmp_path, monkeypatch, capsys):
    for val in ({}, []):
        p = tmp_path / "v.json"
        p.write_text(json.dumps({"vignettes": val}), encoding="utf-8")
        code, out = run_vig(check, notes, p, monkeypatch, capsys)
        assert code == 1 and "Traceback" not in out and "vignettes" in out


def test_non_json_file_fails_readably(check, notes, tmp_path, monkeypatch, capsys):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    code, out = run_vig(check, notes, p, monkeypatch, capsys)
    assert code == 1 and "not valid JSON" in out and "Traceback" not in out


def test_malformed_option_shapes_fail_readably(check, notes, tmp_path, monkeypatch, capsys):
    p = write_vignettes(tmp_path, ["junk", mutated(lambda v: v.update(options=["x"] * 5), "vx")])
    code, out = run_vig(check, notes, p, monkeypatch, capsys)
    assert code == 1 and "Traceback" not in out


def test_case2_guide_has_five_cited_recall_questions_and_no_uncited_attribution():
    import re
    from pathlib import Path
    text = (Path(__file__).resolve().parent.parent / "examples" / "case2" / "study-guide.md").read_text(encoding="utf-8")
    recall = text.split("## Recall questions", 1)[1].split("<details>", 1)[0]
    qs = re.findall(r"^\d+\. .+$", recall, re.M)
    assert len(qs) == 5 and all("[[" in q for q in qs)
    discrepancy = text.split("## Discrepancies", 1)[1].split("## Recall questions", 1)[0]
    assert "CDC" not in discrepancy


def test_walkthrough_staging_is_guarded_and_commands_pass_no_patient_name_as_topic():
    from pathlib import Path
    text = (Path(__file__).resolve().parent.parent / "docs" / "DEMO-WALKTHROUGH.md").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.lstrip("| `").startswith(("/study-guide", "/flashcards", "/quiz")):
            assert "Rivera" not in line, line
    assert "\n   mkdir -p curriculum && cp -R" not in text and "if [ -e curriculum/sample ]" in text
    assert "already exists" in text


@pytest.mark.parametrize("stem", ["Maria, age 45 presents with fever", "Maria, aged 45 presents with fever", "Maria aged 45 presents"])
def test_phi_gate_catches_name_comma_age_forms(check, stem):
    assert check.phi_hit(stem) == "a name with an age"


@pytest.mark.parametrize("stem", ["Fever, 38 C on arrival", "Tachycardic, 104 bpm at rest"])
def test_phi_gate_keeps_vital_sign_exclusions(check, stem):
    assert check.phi_hit(stem) is None


@pytest.mark.parametrize("stem", [
    "Contact maria@example.com about the result", "Call 312-555-0142 for the lab", "SSN 123-45-6789 on the form",
    "Lives at 42 Maple Street", "ZIP 60611 on file", "Mr. Garcia has a fever", "Jane Wilson presents with fever",
])
def test_phi_gate_covers_contact_details_and_names(check, stem):
    assert check.phi_hit(stem) is not None


def test_phi_pattern_lists_stay_in_sync_with_mnemonic_art(check):
    from conftest import load_script
    art = load_script("mnemonic_art")
    # check.py adds a vital-sign exclusion to the "Name, <number>" rule; every other rule must match exactly
    mine = [(rx.pattern, w) for rx, w in check.PHI_PATTERNS if "bpm" not in rx.pattern]
    theirs = [(rx.pattern, w) for rx, w in art.PHI_PATTERNS if not rx.pattern.startswith(r"\b[A-Z][a-z]+(?:,")]
    assert mine == theirs
    assert check.NAME_ALLOW == art.NAME_ALLOW and check.GENERIC_WORDS == art.GENERIC_WORDS


def test_id_with_trailing_newline_is_invalid(check, notes, tmp_path, monkeypatch, capsys):
    p = write_vignettes(tmp_path, [make_vignette("v1\n")])
    code, out = run_vig(check, notes, p, monkeypatch, capsys)
    assert code == 1 and "invalid id" in out


# ---- PHI gate on diagram text ----

@pytest.mark.parametrize("mutate, what", [
    (lambda s: s.update(title="Jane Smith case 4"), "title"),
    (lambda s: s["nodes"][0].update(label="Jane Smith, 54"), "node"),
    (lambda s: s["nodes"][0].update(label="MRN 12345678"), "node"),
    (lambda s: s["edges"][0].update(label="admitted 03/14/2024"), "edge"),
    (lambda s: s["nodes"][1].update(note="Call 312-555-0142"), "node"),
])
def test_diagram_text_with_phi_fails_closed(check, tmp_path, monkeypatch, capsys, mutate, what):
    path = spec_copy(tmp_path, mutate)
    code, out = run_spec(check, path, monkeypatch, capsys)
    assert code == 1 and "PHI" in out, out


def test_diagram_clinical_terms_and_vitals_do_not_false_positive(check, tmp_path, monkeypatch, capsys):
    def ok(s):
        s["title"] = "Graves Disease and Toxic Shock Syndrome"
        s["nodes"][0]["label"] = "Fever 38.5 C, HR 120 bpm"
        s["nodes"][1]["label"] = "Gram Positive Staphylococcus"
        s["edges"][0]["label"] = "cleaves in 24 hours"
    code, out = run_spec(check, spec_copy(tmp_path, ok), monkeypatch, capsys)
    assert code == 0, out
