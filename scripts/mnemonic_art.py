# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow>=10"]
# ///
"""Generate one captioned memory-aid illustration through OpenRouter.

Usage:
    uv run scripts/mnemonic_art.py --case <case> --concept "<concept>" --scene "<approved scene>" [--yes]

Without --yes the script prints the exact prompt and stops (no network). With --yes it sends the prompt to
OpenRouter, burns the caption "AI illustration - not a reference" into the image, and writes
output/<case>/art/<slug>.png plus <slug>.json (prompt, model, created_at). The key comes from
OPENROUTER_API_KEY and is never printed or stored. Model: --model, else MSAD_IMAGE_MODEL, else the default below.
"""

from __future__ import annotations

import argparse
import base64
import io
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemini-2.5-flash-image"
CAPTION = "AI illustration — not a reference"
STYLE = (
    "Style: a simple, memorable illustration in a clean cartoon style, with no text labels (no letters or "
    "words in the image), no real people, and no patients."
)
CONFIRM = "This prompt will be sent to OpenRouter (a third-party AI provider). Re-run with --yes to send."
SLUG = re.compile(r"^[a-z0-9-]{1,60}$")
SETUP = """OPENROUTER_API_KEY is not set. To enable illustrations:
  1. Get a key at https://openrouter.ai/keys (your own account).
  2. Set a spend limit on the key in the OpenRouter dashboard.
  3. export OPENROUTER_API_KEY=<your key>   (add it to your shell profile)
Then re-run this command."""

# Second check after the student's own review: refuse text that looks patient-identifying.
POLICY_WORDS = ("zdr", "data policy", "guardrail")
POLICY_HINT = ("Your OpenRouter privacy settings exclude every image endpoint for this model. Enable an "
               "image-capable endpoint at https://openrouter.ai/settings/privacy (or turn off "
               "zero-data-retention for image models), then retry once.")
PHI_PATTERNS = [
    (re.compile(r"\d{6,}"), "a number with 6 or more digits (MRN-like)"),
    (re.compile(r"\b(?:MRN|DOB)\b|date\s+of\s+birth|medical\s+record", re.I), "MRN or date-of-birth wording"),
    (re.compile(r"\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b"), "a date"),
    (re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b"
                r"|\b\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?,?\s+\d{4}\b"), "a date"),
    (re.compile(r"\b(?:born|dob)\b[^.]{0,20}\b(?:19|20)\d{2}\b", re.I), "a birth year"),
    (re.compile(r"\b[A-Z][a-z]+(?:,\s*|\s+aged?\s+)\d{1,3}\b"), "a name with an age"),
    (re.compile(r"\b\d{1,3}[- ]years?[- ]old\s+(?:named|called)\b", re.I), "a name with an age"),
]


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.message = message


def http_post(url: str, headers: dict, payload: dict) -> dict:
    """POST JSON, return parsed JSON. Errors carry only the status code and OpenRouter's message."""
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read())["error"]["message"]
        except Exception:
            msg = e.reason or "request failed"
        raise ApiError(e.code, str(msg)) from None
    except urllib.error.URLError as e:
        raise ApiError(0, f"network error: {e.reason}") from None


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def phi_hit(*texts: str) -> str | None:
    for text in texts:
        for rx, what in PHI_PATTERNS:
            if rx.search(text):
                return what
    return None


def build_prompt(concept: str, scene: str) -> str:
    return f"Illustrate the concept \"{concept}\" as a memory aid. Scene: {scene}. {STYLE}"


def font(size: int):
    for name in ("DejaVuSans.ttf", "Arial.ttf", "Helvetica.ttc", "/System/Library/Fonts/Helvetica.ttc"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def stamp(png_bytes: bytes) -> Image.Image:
    """Extend the canvas with a caption band whose colors contrast with the picture."""
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    w, h = img.size
    luma = img.convert("L").resize((1, 1)).getpixel((0, 0))
    dark_art = luma < 128
    bg, fg = ((255, 255, 255), (0, 0, 0)) if dark_art else ((0, 0, 0), (255, 255, 255))
    size = max(14, w // 28)
    band = size * 2
    out = Image.new("RGB", (w, h + band), bg)
    out.paste(img, (0, 0))
    draw = ImageDraw.Draw(out)
    f = font(size)
    box = draw.textbbox((0, 0), CAPTION, font=f)
    while box[2] - box[0] > w - 16 and size > 8:
        size -= 1
        f = font(size)
        box = draw.textbbox((0, 0), CAPTION, font=f)
    x = (w - (box[2] - box[0])) // 2 - box[0]
    y = h + (band - (box[3] - box[1])) // 2 - box[1]
    draw.text((x, y), CAPTION, font=f, fill=fg)
    return out


def extract_png(data: dict) -> bytes:
    try:
        url = data["choices"][0]["message"]["images"][0]["image_url"]["url"]
        return base64.b64decode(url.split(",", 1)[1] if url.startswith("data:") else url)
    except (KeyError, IndexError, TypeError, ValueError):
        raise ValueError("the model returned no image (it may not support image output; try --model)") from None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", required=True)
    ap.add_argument("--concept", required=True)
    ap.add_argument("--scene", required=True, help="short scene the student approved; no patient details")
    ap.add_argument("--yes", action="store_true", help="confirm sending the printed prompt")
    ap.add_argument("--model", default=os.environ.get("MSAD_IMAGE_MODEL") or DEFAULT_MODEL)
    a = ap.parse_args()

    if not SLUG.match(a.case):
        print("Error: --case must use only a-z, 0-9 and '-'.", file=sys.stderr)
        return 1
    slug = slugify(a.concept)
    if not slug:
        print("Error: --concept needs letters or digits.", file=sys.stderr)
        return 1
    slug = f"{slug}-{hashlib.sha1(a.concept.strip().casefold().encode()).hexdigest()[:8]}"
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        print(SETUP)
        return 2
    hit = phi_hit(a.concept, a.scene)
    if hit:
        print(f"Refused: the concept or scene contains {hit}. Describe the idea without patient details.",
              file=sys.stderr)
        return 1
    prompt = build_prompt(a.concept, a.scene)
    if not a.yes:
        print(f"Model: {a.model}\nPrompt:\n{prompt}\n\n{CONFIRM}")
        return 0

    payload = {
        "model": a.model,
        "messages": [{"role": "user", "content": prompt}],
        "modalities": ["image", "text"],
        "provider": {"data_collection": "deny"},
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    try:
        data = http_post(URL, headers, payload)
        png = extract_png(data)
        img = stamp(png)
    except ApiError as e:
        print(f"Error: OpenRouter returned {e.status}: {e.message}", file=sys.stderr)
        if any(w in e.message.lower() for w in POLICY_WORDS):
            print(POLICY_HINT, file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    out_dir = Path("output") / a.case / "art"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{slug}.png"
    if path.exists() or path.with_suffix(".json").exists():
        try:
            old = json.loads(path.with_suffix(".json").read_text(encoding="utf-8")).get("caption")
        except (OSError, ValueError, AttributeError):
            old = None
        if old != a.concept:
            print(f"Error: {path} belongs to a different concept; not overwriting it.", file=sys.stderr)
            return 1
    img.save(path, "PNG")
    path.with_suffix(".json").write_text(json.dumps({
        "prompt": prompt,
        "caption": a.concept,
        "model": a.model,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, indent=2), encoding="utf-8")
    print(f"Saved {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
