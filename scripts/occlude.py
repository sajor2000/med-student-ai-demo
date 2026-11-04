# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright>=1.45", "pillow>=10", "genanki>=0.13"]
# ///
"""Turn a diagram-design HTML diagram into occlusion boxes, masked cards, and an offline deck.

Per diagram (<slug>.html + <slug>.json spec), written beside the HTML:
  <slug>.card.png               opaque PNG of the <svg> element (paper background)
  <slug>.occlusion.json         one box per label (normalized 0-1), note_id, Anki occlusion string
  <slug>.<id>.masked.png        card with only that label covered
  <slug>.<id>.highlight.png     card with only that label outlined

Browser safety: the page loads via file:// with JavaScript DISABLED and every
non-file request aborted, so a <script> in the HTML cannot run or reach out.
Playwright's page.evaluate still works with JavaScript disabled (it runs in an
isolated world), so measurement needs no second, script-enabled context.

Usage:
    uv run scripts/occlude.py output/<case>/diagrams/<slug>.html \\
        --spec output/<case>/diagrams/<slug>.json --case <case>
    uv run scripts/occlude.py --apkg output/<case>/diagrams --case <case>
Exit codes: 0 ok, 1 spec/SVG mismatch or bad input, 2 Chromium unavailable.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import re
import sys
import tempfile
from pathlib import Path

SAFE = re.compile(r"[a-z0-9-]{1,60}")
ID_FORMAT = re.compile(r"[a-z0-9-]{1,40}")  # same format scripts/check.py enforces for node and edge ids
PAPER_COLOR = (245, 245, 245)
MASK_COLOR = (31, 41, 55)
HIGHLIGHT_COLOR = (234, 88, 12)
PAD_PX = 3
SCALE = 2
MODEL_ID = 1607392319  # fixed genanki model id
INSTALL_HINT = "Install Chromium once: uv run --with playwright playwright install chromium"

MEASURE_JS = """
async () => {
  await document.fonts.ready;
  const svg = document.querySelector('svg');
  if (!svg) return {error: 'no <svg> element'};
  const vb = svg.viewBox.baseVal;
  if (!vb || !vb.width || !vb.height) return {error: 'svg has no viewBox'};
  svg.style.cssText += ';width:' + vb.width + 'px;height:' + vb.height + 'px;max-width:none;display:block;background:#f5f5f5';
  const inv = svg.getScreenCTM().inverse();
  const texts = [];
  for (const el of svg.querySelectorAll('text')) {
    const b = el.getBBox();
    const m = inv.multiply(el.getScreenCTM());
    const xs = [], ys = [];
    for (const [x, y] of [[b.x, b.y], [b.x + b.width, b.y], [b.x, b.y + b.height], [b.x + b.width, b.y + b.height]]) {
      xs.push(m.a * x + m.c * y + m.e); ys.push(m.b * x + m.d * y + m.f);
    }
    const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
    texts.push({
      id: el.getAttribute('data-node'),
      decorative: el.getAttribute('data-decorative') === 'true',
      text: el.textContent,
      box: {left: (x0 - vb.x) / vb.width, top: (y0 - vb.y) / vb.height,
            width: (x1 - x0) / vb.width, height: (y1 - y0) / vb.height},
    });
  }
  return {vbw: vb.width, vbh: vb.height, texts};
}
"""


def note_id(case: str, slug: str, label_id: str) -> str:
    return "msad-" + hashlib.sha1(f"{case}:{slug}:{label_id}".encode()).hexdigest()[:12]


def fmt_norm(v: float) -> str:
    """Anki style: 4 decimals, trailing zeros and the leading zero dropped (.2325, .202, .2)."""
    s = f"{round(float(v), 4):.4f}".rstrip("0").rstrip(".")
    if s.startswith("0."):
        s = s[1:]
    return s or "0"


def occlusion_string(box: dict) -> str:
    return ("{{c1::image-occlusion:rect:left=%s:top=%s:width=%s:height=%s:oi=1}}"
            % (fmt_norm(box["left"]), fmt_norm(box["top"]), fmt_norm(box["width"]), fmt_norm(box["height"])))


def back_extra(label: str, cite: str) -> str:
    return f"{html.escape(label)}<br><small>{html.escape(cite)}</small>"


def io_fields(title: str, image: str, label: str, cite: str, box: dict) -> dict:
    """Image Occlusion note fields in Anki's field order (rslib/src/image_occlusion)."""
    return {
        "Occlusion": occlusion_string(box),
        "Image": f'<img src="{html.escape(image)}">',
        "Header": html.escape(title),
        "Back Extra": back_extra(label, cite),
        "Comments": "",
    }


def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


class ChromiumUnavailable(Exception):
    """Both Chromium launch attempts failed."""


def launch_chromium(p):
    try:
        return p.chromium.launch()
    except Exception:
        try:
            return p.chromium.launch(channel="chromium")
        except Exception as e:
            raise ChromiumUnavailable(str(e)) from e


def spec_type_problems(spec: dict) -> list[str]:
    """Labels and cites must be strings (checked before norm_ws touches them)."""
    probs: list[str] = []
    for kind, key in (("node", "nodes"), ("edge", "edges")):
        for i, item in enumerate(spec.get(key) or [], 1):
            if not isinstance(item, dict):
                probs.append(f"{kind} #{i}: must be an object")
                continue
            if not isinstance(item.get("id"), str):
                probs.append(f"{kind} #{i}: id is missing or not a string")
            elif not ID_FORMAT.fullmatch(item["id"]):
                probs.append(f"{kind} {item['id']!r}: id must match [a-z0-9-]{{1,40}}")
            if kind == "node" and "label" not in item:
                probs.append(f"{kind} {item['id'] if isinstance(item.get('id'), str) else '#' + str(i)}: label is missing")
            ident = item.get("id") if isinstance(item.get("id"), str) else f"#{i}"
            for field in ("label", "cite"):
                if field in item and not isinstance(item[field], str):
                    probs.append(f"{kind} {ident}: {field} must be a string")
    return probs


def validate(spec: dict, texts: list[dict]) -> tuple[list[str], dict]:
    """Both-way spec <-> SVG check. Returns (failures, {id: text entry})."""
    fails: list[str] = []
    want: dict[str, dict] = {}
    for n in spec.get("nodes", []):
        want[n["id"]] = {"kind": "node", "label": n["label"], "cite": n.get("cite", "")}
    for e in spec.get("edges", []):
        if str(e.get("label") or "").strip():
            want[e["id"]] = {"kind": "edge", "label": e["label"], "cite": e.get("cite", "")}
    found: dict[str, dict] = {}
    for t in texts:
        tid = t["id"]
        if tid is None:
            if not t["decorative"]:
                fails.append(f'<text> without data-node or data-decorative: "{norm_ws(t["text"])}"')
        elif tid not in want:
            fails.append(f'{tid}: <text data-node> has no label in the spec')
        elif tid in found:
            fails.append(f"{tid}: more than one element with data-node={tid}")
        else:
            found[tid] = t
    for tid, w in want.items():
        if tid not in found:
            fails.append(f'{tid}: spec label "{w["label"]}" has no <text data-node="{tid}"> in the SVG')
        elif norm_ws(found[tid]["text"]).casefold() != norm_ws(w["label"]).casefold():
            fails.append(f'{tid}: SVG text "{norm_ws(found[tid]["text"])}" differs from spec label "{norm_ws(w["label"])}"')
    return fails, {tid: (want[tid], found[tid]) for tid in want if tid in found}


def measure(page_html: Path) -> dict:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = launch_chromium(p)
        try:
            ctx = browser.new_context(java_script_enabled=False, device_scale_factor=SCALE,
                                      viewport={"width": 1400, "height": 1000})
            ctx.route("**/*", lambda route: route.continue_() if route.request.url.startswith("file:") else route.abort())
            page = ctx.new_page()
            page.goto(page_html.resolve().as_uri())
            res = page.evaluate(MEASURE_JS)
            png = page.locator("svg").first.screenshot(type="png") if "texts" in res else b""
        finally:
            browser.close()
    res["png"] = png
    return res


def render_variants(card_png: bytes, items: list[dict], outdir: Path, slug: str) -> None:
    from PIL import Image, ImageDraw
    card = Image.open(io.BytesIO(card_png)).convert("RGB")
    W, H = card.size
    for it in items:
        b = it["box"]
        x0, y0 = b["left"] * W - PAD_PX, b["top"] * H - PAD_PX
        x1, y1 = (b["left"] + b["width"]) * W + PAD_PX, (b["top"] + b["height"]) * H + PAD_PX
        masked = card.copy()
        ImageDraw.Draw(masked).rectangle([x0, y0, x1, y1], fill=MASK_COLOR)
        masked.save(outdir / it["masked"])
        hl = card.copy().convert("RGBA")
        over = Image.new("RGBA", hl.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(over)
        d.rectangle([x0, y0, x1, y1], fill=HIGHLIGHT_COLOR + (60,), outline=HIGHLIGHT_COLOR + (255,), width=3)
        Image.alpha_composite(hl, over).convert("RGB").save(outdir / it["highlight"])


def run_diagram(html_path: Path, spec_path: Path, case: str) -> int:
    slug = html_path.stem
    if not SAFE.fullmatch(slug) or not SAFE.fullmatch(case):
        print(f"FAIL: slug and case must match [a-z0-9-] (slug={slug!r}, case={case!r})")
        return 1
    if not html_path.is_file() or not spec_path.is_file():
        print(f"FAIL: missing input {html_path if not html_path.is_file() else spec_path}")
        return 1
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except ValueError as e:
        print(f"FAIL: bad spec {spec_path.name}: {e!r}")
        return 1
    if not isinstance(spec, dict) or not isinstance(spec.get("nodes"), list):
        print(f"FAIL: bad spec {spec_path.name}: 'nodes' must be a list")
        return 1
    bad = spec_type_problems(spec)
    if bad:
        print("FAIL:\n  - " + "\n  - ".join(bad))
        return 1
    try:
        res = measure(html_path)
    except ChromiumUnavailable:
        print(INSTALL_HINT)
        return 2
    if "error" in res:
        print(f"FAIL: {res['error']}")
        return 1
    fails, matched = validate(spec, res["texts"])
    if fails:
        print(f"FAIL ({len(fails)}):")
        for f in fails:
            print(f"  - {f}")
        return 1
    out = html_path.parent
    labels = []
    for tid, (w, t) in matched.items():
        box = {k: round(v, 4) for k, v in t["box"].items()}
        if box["left"] < 0 or box["top"] < 0 or box["left"] + box["width"] > 1.0001 or box["top"] + box["height"] > 1.0001:
            fails.append(f"{tid}: label box falls outside the SVG viewBox")
        labels.append({
            "id": tid, "kind": w["kind"], "label": w["label"], "cite": w["cite"], "box": box,
            "note_id": note_id(case, slug, tid), "occlusion": occlusion_string(box),
            "masked": f"{slug}.{tid}.masked.png", "highlight": f"{slug}.{tid}.highlight.png",
        })
    if fails:
        print("FAIL:\n  - " + "\n  - ".join(fails))
        return 1
    (out / f"{slug}.card.png").write_bytes(res["png"])
    render_variants(res["png"], labels, out, slug)
    data = {"case": case, "slug": slug, "title": spec.get("title", slug),
            "image": f"{slug}.card.png", "labels": labels}
    (out / f"{slug}.occlusion.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\n".join(summary_lines(slug, labels)))
    return 0


def summary_lines(slug: str, labels: list[dict]) -> list[str]:
    lines = [f"{slug}: {len(labels)} labels"]
    for l in labels:
        b = l["box"]
        lines.append(f"  {l['id']:<14} {l['kind']:<5} left={b['left']} top={b['top']} "
                     f"w={b['width']} h={b['height']}  {l['label']}")
    lines.append(f"data-node labels: {len(labels)} (nodes + labeled edges)")
    return lines


def confined_png(folder: Path, name: object) -> Path | None:
    """folder/name resolved (symlinks too) if it is a .png that stays inside folder, else None.
    Deliberate copy in anki_sync.py: each script stays standalone."""
    if not isinstance(name, str) or not name:
        return None
    rel = Path(name)
    if rel.is_absolute() or ".." in rel.parts:
        return None  # aliases would package a different name than the card references
    root = folder.resolve()
    path = root / rel
    probe = root
    for part in rel.parts:
        probe = probe / part
        if probe.is_symlink():
            return None
    return path if path.suffix.lower() == ".png" and path.resolve().is_relative_to(root) else None


def build_apkg(folder: Path, case: str) -> int:
    import genanki
    if not SAFE.fullmatch(case):
        print(f"FAIL: case must match [a-z0-9-] (got {case!r})")
        return 1
    files = sorted(folder.glob("*.occlusion.json"))
    if not files:
        print(f"FAIL: no *.occlusion.json in {folder}")
        return 1
    model = genanki.Model(
        MODEL_ID, "AI Study Masked Diagram Card",
        fields=[{"name": "Front"}, {"name": "Back"}],
        templates=[{"name": "Card 1", "qfmt": "{{Front}}",
                    "afmt": "{{FrontSide}}<hr id=answer>{{Back}}"}],
    )
    deck_id = int(hashlib.sha1(f"deck:{case}".encode()).hexdigest()[:8], 16)
    deck = genanki.Deck(deck_id, f"AI Study::{case}::diagrams-offline")
    media: list[str] = []
    count = 0
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        for lab in data["labels"]:
            for name in (lab["masked"], lab["highlight"]):
                path = confined_png(folder, name)
                if path is None:
                    print(f"FAIL: {name!r} in {f.name} is outside {folder} or not a .png; rerun occlude.py on {data['slug']}")
                    return 1
                if not path.is_file():
                    print(f"FAIL: missing {path}; rerun occlude.py on {data['slug']}")
                    return 1
                media.append(str(path))
            back = f'<img src="{html.escape(lab["highlight"])}"><br>{back_extra(lab["label"], lab["cite"])}'
            deck.add_note(genanki.Note(model=model, fields=[f'<img src="{html.escape(lab["masked"])}">', back],
                                       guid=lab["note_id"], tags=["msad", "diagram"]))
            count += 1
    pkg = genanki.Package(deck)
    pkg.media_files = media
    dest = folder.parent / f"{folder.name}.apkg"
    pkg.write_to_file(str(dest))
    print(f"wrote {dest} ({count} notes, deck AI Study::{case}::diagrams-offline)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("html", nargs="?", type=Path, help="diagram HTML (diagram-design output)")
    ap.add_argument("--spec", type=Path, help="diagram spec JSON")
    ap.add_argument("--case", required=True)
    ap.add_argument("--apkg", type=Path, help="diagrams folder: pack *.occlusion.json into <folder>.apkg")
    a = ap.parse_args()
    if a.apkg:
        return build_apkg(a.apkg, a.case)
    if not a.html or not a.spec:
        ap.error("pass the HTML and --spec, or --apkg <folder>")
    return run_diagram(a.html, a.spec, a.case)


if __name__ == "__main__":
    sys.exit(main())
