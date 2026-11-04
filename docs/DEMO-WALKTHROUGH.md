# Live demo walkthrough: one fictional case, 25 minutes

> **Educational demo.** AI powers your learning; it does not replace it.
> Course materials belong to your institution: anything you upload must follow your institution's AI policy.
> Read the full [Responsible use](RESPONSIBLE-USE.md) page first. The patient, school, and faculty in this demo are invented.

This script is written for a presenter, and a student can follow it alone. It uses the fictional
case guide **BMS 501 Self-Study Guide 02, Jordan Rivera** (a 19-year-old wrestler with a CA-MRSA forearm
abscess) plus a short *S. aureus* lecture deck. Both live in `sample/curriculum/`. Nothing here is real course material.

**Total time:** 25 minutes plus 5 of buffer (a 20-minute version is marked below).

## Before you start (5 minutes, the day before)

1. Clone the repo, then follow the README install (`uv`, Claude Code, the project MCP servers).
2. Stage the sample as your "course" (the skills read from the gitignored `curriculum/` folder):
   ```bash
   mkdir -p curriculum && cp -R sample/curriculum curriculum/sample
   ```
3. Open a terminal in the repo and start `claude`. Approve the project MCP servers when asked.
4. Open `examples/case2/flashcards.html` in a browser tab now. It is your fallback (see the last section).
5. Close anything with real patient or course data. Use a clean screen share.

**Check you are ready:** `uv run scripts/check.py examples/case2/study-guide.md --notes sample/notes` prints `PASS`.

## Run of show

| Time | Act | You say / do |
|---|---|---|
| 0-3 | Why, and responsible use | Slide-free talk, then show `docs/RESPONSIBLE-USE.md` |
| 3-8 | `/ingest sample` | Turn a case guide and a deck into citable notes |
| 8-15 | `/study-guide sample "Jordan Rivera"` | Build a cited guide, then check it live |
| 15-21 | `/flashcards sample` + export | Open the page, click a citation |
| 21-26 | `/quiz sample` | Attempt first, then explain |
| 26-30 | Anki import, your own course | Hand off to the audience |

### Act 1 (0-3 min): why, and what responsible use means

- Say: "AI is good at drafting and quizzing. It is bad at knowing when it is wrong. This tool is built around that."
- Point at: the three rules in [RESPONSIBLE-USE.md](RESPONSIBLE-USE.md) (attempt first, open the sources, your school owns the materials).
- Point at: the repo's citation rule in `CLAUDE.md`: every fact cites a slide or a PubMed record, or is marked `[source needed]`.
- Show: the case guide's "Course Director Notes" box, which carries the same reminder about school AI policy.

### Act 2 (3-8 min): ingest

Type in Claude Code:

```
/ingest sample
```

**Expected:** a table with two sources (the GUIDE case guide with about 210 paragraphs, the MICRO deck with 6 slides),
the case's learning objectives quoted with citations, and 3-5 cross-discipline threads such as
protein A (micro) to blocked opsonization (immuno) to abscess to PBP2a/MRSA (pharm).

**Point at:** the citation tags. `[[GUIDE/...#P18]]` means paragraph 18 of the guide, `[[MICRO/...#S3]]` means slide 3.
Open `notes/sample/GUIDE/` and show paragraph numbers in the Markdown, so the audience sees that a citation is an address.

### Act 3 (8-15 min): study guide with a live citation check

```
/study-guide sample "Jordan Rivera"
```

**Expected:** `output/sample/study-guide.md` with objectives, a one-page summary, a mechanism chain
(exposure, recognition, recruitment, evasion, killing, lab identity, treatment), a "Beyond the slides" section with
PubMed IDs, and recall questions. The agent then runs the citation check itself.

Run the check on screen, whether or not the agent already did:

```bash
uv run scripts/check.py output/sample/study-guide.md --notes notes/sample
```

**Expected output:** a list of PubMed titles, then `PASS: every citation resolves and every fact line is cited`.

**The key teaching moment (do not skip):** `PASS` proves a source *exists*, not that it *supports* the claim.
Open one citation together. Suggested: the TMP-SMX line, `[PMID:26962903]`. Read the abstract and find
"80.5% vs 73.6%". Then ask the room: "What did the check not catch?" (Answer: whether the claim matches the paper.)

Optional beat: show `examples/case2/study-guide.md`, which has a **Discrepancies** section. The lecture says
enterotoxin vomiting starts 1-6 h after eating, and the case guide says 30 min-8 h. Real decks disagree; the agent should say so.

### Act 4 (15-21 min): flashcards, export, click a citation

```
/flashcards sample "Jordan Rivera" 14
```

**Expected:** `output/sample/flashcards.csv` with about 14 cards (basic and cloze), each with a source. Then:

```bash
uv run scripts/check.py output/sample/flashcards.csv --notes notes/sample
uv run scripts/export.py output/sample/flashcards.csv --notes notes/sample --guide output/sample/study-guide.md
open output/sample/flashcards.html          # macOS; use xdg-open on Linux, start on Windows
```

**Expected:** `PASS`, then a page with a **Study guide** tab and flip cards.

**Point at:** click a card, flip it, then click a `[[GUIDE/...#P60]]` citation. The exact paragraph opens.
Say: "This is how you verify an AI-written card in 5 seconds." Then show one `{{c1::...}}` cloze card.

*20-minute version: skip generating live. Open `examples/case2/flashcards.html` and do only the click-a-citation beat.*

### Act 5 (21-26 min): quiz, attempt first

```
/quiz sample "Jordan Rivera" 3
```

**Expected:** one vignette at a time, no answers shown. **Rule for the presenter:** ask a volunteer to answer
out loud *before* you type a letter. The agent then explains with a quoted line and a citation, and saves misses to
`output/sample/weak-spots.md` for the next `/flashcards` run.

Say: "Attempt first is the whole point. If you ask for the answer, you learn nothing."

### Act 6 (26-30 min): Anki, and your own course

- Anki: **File, Import,** pick `output/sample/flashcards.anki.txt`, and again for `flashcards.cloze.anki.txt`.
  Cards land in the deck `AI Study::sample`. Re-importing updates cards instead of duplicating them.
- Optional extras, only if merged or installed on your machine: `/visualize` (diagrams), `/vignette`,
  `/teach-back`, `/anki-sync` (pull your misses back from Anki). Mention each in one line; do not demo them live.
- Close with the section below.

## If the network fails

The agent steps and the PubMed lookups need the network. Everything you need to finish is already committed:

1. Open `examples/case2/flashcards.html` in a browser (`open examples/case2/flashcards.html`). It works offline.
2. Walk the same beats: the **Study guide** tab, flip a card, click a citation to open the source paragraph.
3. Show the cited guide at `examples/case2/study-guide.md` and the card list at `examples/case2/flashcards.csv`.
4. Say what you would have run: `/ingest`, `/study-guide`, `/flashcards`, and the `check.py` line. Be honest that `check.py` needs the network.
5. Do the quiz from the committed notes by hand: read the questions in `sample/notes/GUIDE/` (Immunology, Microbiology, Pharmacology), let the room answer, then read the answer lines.

## Use this on your own course

1. Put your own files in the gitignored `curriculum/<case>/` folder, one folder per case or week.
   **First confirm your school's AI policy allows it.** Do not upload exams, question banks, or anything you may not share.
2. Run `/ingest <case>`, then `/study-guide <case>`, `/flashcards <case>`, and `/quiz <case>` in that order.
3. Try to recall before you read the guide. Open at least two citations per session.
4. Treat faculty and official materials as the ground truth. When the AI and your course disagree, ask faculty.
5. Never commit `curriculum/`, `notes/`, or `output/`. They are gitignored on purpose.

## Presenter checklist

- [ ] `sample/curriculum` copied to `curriculum/sample`
- [ ] `claude` started in the repo, MCP servers approved
- [ ] `examples/case2/flashcards.html` open in a tab
- [ ] `docs/RESPONSIBLE-USE.md` open in another tab
- [ ] A volunteer lined up for the quiz
