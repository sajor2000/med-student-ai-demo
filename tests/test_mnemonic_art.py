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
    png = tmp_path / "output/case1/art/staph-scalded-skin.png"
    assert png.exists()
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
    assert "staph-scalded-skin.png" in capsys.readouterr().out


def test_caption_constant(art):
    assert art.CAPTION == "AI illustration — not a reference"


def test_dark_image_caption_readable(art, net, monkeypatch, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    net.response = ok_response((0, 0, 0))
    assert run_main(art, args(**{"--yes": True}), monkeypatch) == 0
    img = Image.open(tmp_path / "output/case1/art/staph-scalded-skin.png").convert("RGB")
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
