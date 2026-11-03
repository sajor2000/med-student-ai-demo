# /// script
# requires-python = ">=3.11"
# dependencies = ["markdown>=3.5"]
# ///
"""Export a flashcard CSV to Anki, and build a one-page study site.

Inputs (CSV columns): front, back, sources, tags
Outputs, next to the CSV:
  <name>.anki.txt   import in Anki: File > Import (tab-separated, HTML, tags column)
  <name>.html       self-contained page: study guide + flip cards, citations linked

Usage:
    uv run scripts/export.py output/flashcards.csv [--guide output/study-guide.md]
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
from pathlib import Path

import markdown

PMID = re.compile(r"\[?PMID:\s?(\d{4,9})\]?")
COURSE = re.compile(r"\[\[([^\]#]+)#([SPT]\d+)\]\]")


def linkify(text: str) -> str:
    text = PMID.sub(r'<a class="cite" href="https://pubmed.ncbi.nlm.nih.gov/\1/">PMID \1</a>', text)
    return COURSE.sub(r'<span class="cite course" title="\1">\1 · \2</span>', text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", type=Path)
    ap.add_argument("--guide", type=Path)
    args = ap.parse_args()

    with args.csv.open(newline="", encoding="utf-8") as fh:
        cards = list(csv.DictReader(fh))

    anki = args.csv.with_suffix(".anki.txt")
    with anki.open("w", encoding="utf-8") as out:
        out.write("#separator:tab\n#html:true\n#tags column:3\n")
        for c in cards:
            back = linkify(html.escape(c["back"])) + "<br><small>" + linkify(html.escape(c["sources"])) + "</small>"
            tags = " ".join(t.strip().replace(" ", "_") for t in c.get("tags", "").split(";") if t.strip())
            out.write(f"{html.escape(c['front'])}\t{back}\t{tags}\n")

    guide_html = ""
    if args.guide and args.guide.exists():
        guide_html = linkify(markdown.markdown(args.guide.read_text(encoding="utf-8"), extensions=["tables"]))

    data = [
        {
            "front": html.escape(c["front"]),
            "back": linkify(html.escape(c["back"])),
            "sources": linkify(html.escape(c["sources"])),
            "tags": c.get("tags", ""),
        }
        for c in cards
    ]
    page = TEMPLATE.replace("__TITLE__", html.escape(args.csv.stem.replace("-", " ").title()))
    page = page.replace("__GUIDE__", guide_html or "<p>No study guide passed (use --guide).</p>")
    page = page.replace("__CARDS__", json.dumps(data))
    site = args.csv.with_suffix(".html")
    site.write_text(page, encoding="utf-8")
    print(f"{len(cards)} cards -> {anki} (Anki import)")
    print(f"study site  -> {site}")
    return 0


TEMPLATE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title>
<style>
:root{--bg:#f7f6f2;--fg:#1d1d1b;--muted:#6b6a65;--card:#fff;--line:#dedbd2;--accent:#0b6e4f}
@media (prefers-color-scheme:dark){:root{--bg:#161614;--fg:#ecebe6;--muted:#a3a19a;--card:#21211e;--line:#3a3934;--accent:#5fc9a2}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,sans-serif}
main{max-width:860px;margin:0 auto;padding:24px 16px 80px}
nav{display:flex;gap:8px;margin:8px 0 24px}nav button{flex:1;padding:10px;border:1px solid var(--line);background:var(--card);color:var(--fg);border-radius:8px;font:inherit;cursor:pointer}
nav button[aria-pressed=true]{border-color:var(--accent);color:var(--accent);font-weight:600}
table{border-collapse:collapse;width:100%;font-size:14px}td,th{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
.cite{font-size:12px;color:var(--accent);white-space:nowrap}.cite.course{color:var(--muted)}
#card{background:var(--card);border:1px solid var(--line);border-radius:12px;min-height:260px;padding:28px;cursor:pointer;display:flex;flex-direction:column;justify-content:center}
#card .q{font-size:20px;font-weight:600}#card .a{margin-top:18px;display:none}#card.flipped .a{display:block}
.src{margin-top:14px;font-size:13px;color:var(--muted)}.row{display:flex;gap:8px;margin-top:12px;align-items:center}
.row button{padding:8px 14px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--fg);font:inherit;cursor:pointer}
.row span{margin-left:auto;color:var(--muted);font-size:14px}
</style></head><body><main>
<h1>__TITLE__</h1>
<nav><button id="tg" aria-pressed="false">Study guide</button><button id="tc" aria-pressed="true">Flashcards</button></nav>
<section id="guide" hidden>__GUIDE__</section>
<section id="cards"><div id="card"><div class="q"></div><div class="a"><div class="b"></div><div class="src"></div></div></div>
<div class="row"><button id="prev">← Prev</button><button id="flip">Flip (space)</button><button id="next">Next →</button><span id="pos"></span></div>
<p class="src">Click the card or press space to flip. Arrow keys move between cards.</p></section>
</main><script>
const C=__CARDS__;let i=0;const card=document.getElementById('card');
function show(){const c=C[i];card.classList.remove('flipped');card.querySelector('.q').innerHTML=c.front;
card.querySelector('.b').innerHTML=c.back;card.querySelector('.src').innerHTML='Sources: '+c.sources+(c.tags?' · '+c.tags:'');
document.getElementById('pos').textContent=(i+1)+' / '+C.length}
const flip=()=>card.classList.toggle('flipped');card.onclick=e=>{if(e.target.tagName!=='A')flip()};
document.getElementById('flip').onclick=flip;document.getElementById('next').onclick=()=>{i=(i+1)%C.length;show()};
document.getElementById('prev').onclick=()=>{i=(i-1+C.length)%C.length;show()};
document.onkeydown=e=>{if(e.key===' '){e.preventDefault();flip()}if(e.key==='ArrowRight')document.getElementById('next').click();if(e.key==='ArrowLeft')document.getElementById('prev').click()};
const tg=document.getElementById('tg'),tc=document.getElementById('tc');
tg.onclick=()=>{guide.hidden=false;cards.hidden=true;tg.setAttribute('aria-pressed',true);tc.setAttribute('aria-pressed',false)};
tc.onclick=()=>{guide.hidden=true;cards.hidden=false;tc.setAttribute('aria-pressed',true);tg.setAttribute('aria-pressed',false)};
if(C.length)show();
</script></body></html>"""

if __name__ == "__main__":
    raise SystemExit(main())
