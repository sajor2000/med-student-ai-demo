"""mnemonic_art.py: prompt confirmation, PHI refusal, stamped output. Network is always mocked."""
from __future__ import annotations

import base64
import io
import json

import pytest
from PIL import Image

from conftest import load_script, run_main

KEY = "sk-or-test-SECRET-1234567890"
SCENE = "a tiny knight peeling a banana skin off a cartoon staph bubble"


@pytest.fixture
def art():
    return load_script("mnemonic_art")


def png_b64(color=(255, 255, 255), size=(256, 256)) -> str:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


def ok_response(color=(255, 255, 255)):
    return {"choices": [{"message": {"content": "", "images": [
        {"type": "image_url", "image_url": {"url": "data:image/png;base64," + png_b64(color)}}]}}]}


@pytest.fixture
def net(art, monkeypatch):
    """Replace the HTTP function; record calls."""
    calls = []

    def fake(url, headers, payload):
        calls.append({"url": url, "headers": headers, "payload": payload})
        return fake.response

    fake.response = ok_response()
    monkeypatch.setattr(art, "http_post", fake)
    fake.calls = calls
    return fake


@pytest.fixture(autouse=True)
def _cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("MSAD_IMAGE_MODEL", raising=False)


def args(**kw):
    base = {"--case": "case1", "--concept": "Staph scalded skin", "--scene": SCENE}
    base.update(kw)
    out = []
    for k, v in base.items():
        out += [k] if v is True else [k, v]
    return out


def test_success_saves_captioned_png_and_sidecar(art, net, monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    assert run_main(art, args(**{"--yes": True}), monkeypatch) == 0
    png = next((tmp_path / "output/case1/art").glob("staph-scalded-skin-*.png"))
    img = Image.open(png).convert("RGB")
    assert img.height > 256 and img.width == 256  # canvas extended with a caption band
    band = img.crop((0, 256, img.width, img.height))
    lums = {sum(c) // 3 for _, c in band.getcolors(maxcolors=100000)}
    assert min(lums) < 100 and max(lums) > 200  # text pixels contrast with the band background
    side = json.loads(png.with_suffix(".json").read_text())
    assert set(side) == {"prompt", "caption", "model", "created_at"}
    assert side["caption"] == "Staph scalded skin"
    assert "Staph scalded skin" in side["prompt"] and SCENE in side["prompt"]
    assert side["model"] == "google/gemini-2.5-flash-image"
    assert png.name in capsys.readouterr().out


def test_caption_constant(art):
    assert art.CAPTION == "AI illustration — not a reference"


def test_dark_image_caption_readable(art, net, monkeypatch, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    net.response = ok_response((0, 0, 0))
    assert run_main(art, args(**{"--yes": True}), monkeypatch) == 0
    img = Image.open(next((tmp_path / "output/case1/art").glob("staph-scalded-skin-*.png"))).convert("RGB")
    band = img.crop((0, 256, img.width, img.height))
    lums = {sum(c) // 3 for _, c in band.getcolors(maxcolors=100000)}
    assert min(lums) < 100 and max(lums) > 200


def test_request_shape(art, net, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    monkeypatch.setenv("MSAD_IMAGE_MODEL", "some/model")
    run_main(art, args(**{"--yes": True}), monkeypatch)
    (call,) = net.calls
    assert call["url"] == "https://openrouter.ai/api/v1/chat/completions"
    p = call["payload"]
    assert p["model"] == "some/model"
    assert p["modalities"] == ["image", "text"]
    assert p["provider"] == {"data_collection": "deny"}
    assert "no text labels" in p["messages"][0]["content"]


def test_model_flag_overrides(art, net, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    run_main(art, args(**{"--yes": True, "--model": "x/y"}), monkeypatch)
    assert net.calls[0]["payload"]["model"] == "x/y"


def test_no_key_prints_setup_and_no_network(art, net, monkeypatch, capsys):
    assert run_main(art, args(**{"--yes": True}), monkeypatch) == 2
    out = capsys.readouterr()
    text = out.out + out.err
    assert "openrouter.ai" in text and "spend limit" in text and "export OPENROUTER_API_KEY" in text
    assert net.calls == []


@pytest.mark.parametrize("scene", [
    "patient MRN 1234567 smiling",
    "born on 03/14/1980 with rash",
    "DOB 1980-03-14",
    "date of birth March 4 1980",
    "John, 45 with a rash",
    "a 45-year-old named John",
    "see MRN on the chart",
])
def test_phi_patterns_refused_before_network(art, net, monkeypatch, scene, capsys):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    assert run_main(art, args(**{"--scene": scene, "--yes": True}), monkeypatch) == 1
    assert net.calls == []
    assert "refus" in (capsys.readouterr().err).lower()


def test_phi_in_concept_refused(art, net, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    assert run_main(art, args(**{"--concept": "MRN 5551234", "--yes": True}), monkeypatch) == 1
    assert net.calls == []


def test_without_yes_prints_prompt_and_no_network(art, net, monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    assert run_main(art, args(), monkeypatch) == 0
    out = capsys.readouterr().out
    assert SCENE in out and "Staph scalded skin" in out
    assert "This prompt will be sent to OpenRouter (a third-party AI provider). Re-run with --yes to send." in out
    assert KEY not in out
    assert net.calls == []
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("bad", ["../x", "Case1", "a b", "a/b", ""])
def test_bad_case_rejected(art, net, monkeypatch, bad):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    assert run_main(art, args(**{"--case": bad, "--yes": True}), monkeypatch) == 1
    assert net.calls == []


def test_missing_images_readable_error(art, net, monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    net.response = {"choices": [{"message": {"content": "sorry, text only"}}]}
    assert run_main(art, args(**{"--yes": True}), monkeypatch) == 1
    err = capsys.readouterr().err
    assert "no image" in err.lower()
    assert not (tmp_path / "output/case1/art").exists() or not list((tmp_path / "output/case1/art").iterdir())


def test_key_never_leaks_on_success(art, net, monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    run_main(art, args(**{"--yes": True}), monkeypatch)
    out = capsys.readouterr()
    assert KEY not in out.out + out.err
    for f in (tmp_path / "output/case1/art").iterdir():
        if f.suffix == ".json":
            assert KEY not in f.read_text()


def test_http_error_shows_status_and_message_not_key(art, monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)

    def boom(url, headers, payload):
        raise art.ApiError(402, "Insufficient credits")

    monkeypatch.setattr(art, "http_post", boom)
    assert run_main(art, args(**{"--yes": True}), monkeypatch) == 1
    out = capsys.readouterr()
    assert "402" in out.err and "Insufficient credits" in out.err
    assert KEY not in out.out + out.err
    assert not (tmp_path / "output").exists()


def test_http_post_maps_urllib_error_without_key(art, monkeypatch):
    import urllib.error

    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, io.BytesIO(
            b'{"error": {"message": "No auth credentials found"}}'))

    monkeypatch.setattr(art.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(art.ApiError) as e:
        art.http_post("https://openrouter.ai/api/v1/chat/completions",
                      {"Authorization": "Bearer " + KEY}, {"a": 1})
    assert e.value.status == 401 and "No auth credentials" in e.value.message
    assert KEY not in str(e.value)


def test_plain_concepts_not_refused(art):
    assert art.phi_hit("Type 2 diabetes", "a vitamin 12 pill with a cape") is None


@pytest.mark.parametrize("scene, rule", [
    ("patient 1234567 smiling", "a number with 6 or more digits"),
    ("2024-03-14", "a date"),
    ("seen on March 4, 1980", "a date"),
    ("born in 1980", "a birth year"),
])
def test_each_phi_rule_refuses_in_isolation(art, net, monkeypatch, capsys, scene, rule):
    # each scene trips exactly one rule: phi_hit names it, and the CLI refuses before any network call
    assert art.phi_hit(scene) is not None and rule in art.phi_hit(scene)
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    assert run_main(art, args(**{"--scene": scene, "--yes": True}), monkeypatch) == 1
    assert net.calls == []
    assert "refus" in capsys.readouterr().err.lower()


@pytest.mark.parametrize("scene", ["vitamin B12", "2 cm lesion", "Type 2 diabetes"])
def test_clinical_text_not_refused(art, net, monkeypatch, scene):
    assert art.phi_hit(scene) is None
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    assert run_main(art, args(**{"--scene": scene, "--yes": True}), monkeypatch) == 0
    assert len(net.calls) == 1


def test_zdr_policy_error_prints_hint_exit_1(art, monkeypatch, capsys, tmp_path):
    import urllib.error
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)

    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, io.BytesIO(
            b'{"error":{"message":"No endpoints found: ZDR violation"}}'))

    monkeypatch.setattr(art.urllib.request, "urlopen", fake_urlopen)
    assert run_main(art, args(**{"--yes": True}), monkeypatch) == 1
    out = capsys.readouterr()
    assert "Your OpenRouter privacy settings exclude every image endpoint for this model." in out.err + out.out
    assert "https://openrouter.ai/settings/privacy" in out.err + out.out
    assert KEY not in out.out + out.err


def test_distinct_concepts_get_distinct_files(art, net, monkeypatch, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    for concept in ("IL-1α", "IL-1β"):
        assert run_main(art, args(**{"--yes": True, "--concept": concept}), monkeypatch) == 0
    pngs = list((tmp_path / "output/case1/art").glob("*.png"))
    assert len(pngs) == 2
    captions = {json.loads(p.with_suffix(".json").read_text())["caption"] for p in pngs}
    assert captions == {"IL-1α", "IL-1β"}


def test_same_concept_regenerates_same_file(art, net, monkeypatch, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    for _ in range(2):
        assert run_main(art, args(**{"--yes": True}), monkeypatch) == 0
    assert len(list((tmp_path / "output/case1/art").glob("*.png"))) == 1


def test_never_overwrites_other_concepts_image(art, net, monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    assert run_main(art, args(**{"--yes": True}), monkeypatch) == 0
    png = next((tmp_path / "output/case1/art").glob("*.png"))
    side = png.with_suffix(".json")
    data = json.loads(side.read_text())
    data["caption"] = "Something else"
    side.write_text(json.dumps(data))
    before = png.read_bytes()
    assert run_main(art, args(**{"--yes": True}), monkeypatch) == 1
    assert png.read_bytes() == before and "different concept" in capsys.readouterr().err


# --- fail-closed de-identification gate (heuristic; the student's confirmation stays the real control) ---
@pytest.mark.parametrize("scene, rule", [
    ("email me at jane.doe@example.com", "an email address"),
    ("call (312) 555-0100 now", "a phone number"),
    ("call 312-555-0100 now", "a phone number"),
    ("call 312.555.0100 now", "a phone number"),
    ("call +1 312 555 0100 now", "a phone number"),
    ("call +1-312-555-0100 now", "a phone number"),
    ("lives at 123 Main Street", "a street address"),
    ("lives at 45 Oak Ave", "a street address"),
    ("near 9 Elm Blvd", "a street address"),
    ("lives at 123 main street", "a street address"),
    ("45 OAK AVE", "a street address"),
    ("John Smith Type 2 diabetes", "a likely personal name"),
    ("Mary Jones Disease course", "a likely personal name"),
    ("ssn 123 45 6789", "an SSN-like number"),
    ("Patient JOHN SMITH with fever", "a title followed by a name"),
    ("DR SMITH examined", "a title followed by a name"),
    ("Jane Wilson with fever", "a likely personal name"),
    ("Anna Turner from Chicago", "a likely personal name"),
    ("zip 60612", "a ZIP code"),
    ("zip 60612-1234", "a ZIP code"),
    ("ssn 123-45-6789", "an SSN-like number"),
    ("chart #48213 on desk", "an MRN-like identifier"),
    ("see https://example.com/p?id=5", "a URL with a query string"),
    ("Mr Smith with a rash", "a title followed by a name"),
    ("Patient Jones with fever", "a title followed by a name"),
    ("John Smith from Chicago", "a likely personal name"),
])
def test_deid_rule_refuses_in_isolation(art, net, monkeypatch, capsys, scene, rule):
    hit = art.phi_hit(scene)
    assert hit is not None and rule in hit
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    assert run_main(art, args(**{"--scene": scene, "--yes": True}), monkeypatch) == 1
    assert net.calls == []
    err = capsys.readouterr().err.lower()
    assert "refus" in err and "a patient" in err and "a farmer" in err and "contact details" in err


@pytest.mark.parametrize("scene", [
    "Graves disease thyroid storm",
    "Staphylococcus aureus toxin",
    "Type 2 diabetes",
    "vitamin B12",
    "Lyme disease bullseye rash",
    "a hiker in the woods",
    "2 cm lesion",
    "Hashimoto thyroiditis and Cushing syndrome",
    "Gram positive Streptococcus pyogenes",
    "Crohn disease with Borrelia",
    "patient with fever",
    "Patient with fever and Wilson Disease",
    "Wilson Disease and Gram Positive Staphylococcus Aureus",
])
def test_deid_clinical_negatives_pass(art, net, monkeypatch, scene):
    assert art.phi_hit(scene) is None
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    assert run_main(art, args(**{"--scene": scene, "--yes": True}), monkeypatch) == 0
    assert len(net.calls) == 1


def test_deid_checks_concept_too(art, net, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    assert run_main(art, args(**{"--concept": "John Smith", "--yes": True}), monkeypatch) == 1
    assert net.calls == []


@pytest.mark.parametrize("scene", ["patient JOHN SMITH with fever", "PATIENT JANE DOE presenting"])
def test_lowercase_or_uppercase_patient_title_with_caps_name_is_refused(art, scene):
    assert art.phi_hit(scene) is not None


@pytest.mark.parametrize("scene", ["Toxic Shock Syndrome", "Acute Myocardial Infarction", "Congestive Heart Failure",
                                   "patient COPD flare"])
def test_title_cased_medical_concepts_not_refused(art, scene):
    assert art.phi_hit(scene) is None
