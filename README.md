# Med Student AI Study Agent

Turn **your own course slides** into **cited Anki flashcards, practice
quizzes, and study guides** with Claude Code, PubMed, and Paperclip.

Every fact the agent writes links back to a **slide number** in your deck or
a **PubMed record**. A checker script fails the output if a citation is
fake, retracted, points at a slide that doesn't exist, or is missing.

```
  your slides -> extract -> cards / quiz / guide -> check citations -> Anki + study page
       ^                        |      ^                   |
       |                  PubMed / StatPearls        FAIL -> agent fixes
       +------------- quiz misses -> weak spots -> new cards <--------+
```

Built for M1/M2 students in a case-based basic-science curriculum. Tested
with Claude Code. Other agents (Codex, OpenCode) can follow `CLAUDE.md`, but
the `/slash` skills and `.mcp.json` setup here are Claude Code's.

## Tonight's first win (no course files, ~15 min on a fresh laptop)

You need: a Claude account that includes Claude Code (Pro or Max) or an
Anthropic API account, plus about 15 minutes for the first install.

**macOS**
```bash
brew install uv node git                      # needs Homebrew: https://brew.sh
curl -fsSL https://claude.ai/install.sh | bash   # installs Claude Code
node -v                                       # must print v24 or higher (PubMed connector needs it)
git clone https://github.com/sajor2000/med-student-ai-demo && cd med-student-ai-demo
uv run scripts/extract.py sample/curriculum --out sample/notes
uv run scripts/check.py examples/flashcards.csv --notes sample/notes
uv run scripts/export.py examples/flashcards.csv --guide examples/study-guide.md --notes sample/notes
open examples/flashcards.html                 # click a slide citation to open the cited slide
```

**Windows (PowerShell)**
```powershell
winget install astral-sh.uv OpenJS.NodeJS Git.Git
irm https://claude.ai/install.ps1 | iex       # installs Claude Code
node -v                                       # must print v24 or higher
git clone https://github.com/sajor2000/med-student-ai-demo; cd med-student-ai-demo
uv run scripts/extract.py sample/curriculum --out sample/notes
uv run scripts/check.py examples/flashcards.csv --notes sample/notes
uv run scripts/export.py examples/flashcards.csv --guide examples/study-guide.md --notes sample/notes
start examples\flashcards.html
```
On Windows, the PubMed connector must be launched through `cmd`. Run this once
inside the repo folder: `claude mcp add pubmed --scope local -- cmd /c npx -y @cyanheads/pubmed-mcp-server@2.12.0`

Then run `claude` in the folder, approve the project's MCP servers when asked,
and type `/mcp` to sign in to Paperclip.

Stuck? Open an issue: https://github.com/sajor2000/med-student-ai-demo/issues

## Use it on your own course

1. Check your school's policy on using AI with course materials (see Ground rules).
2. Copy one case's slides/guides into `curriculum/<case-name>/`. The folder is gitignored and never committed.
3. Start the agent in this folder with `claude`. It reads `CLAUDE.md` (the rules).
4. Recommended order (active recall first, reading last):

| Command | What you get |
|---|---|
| `/ingest <case-name>` | Notes with slide anchors, plus a map of the case's topics and cross-discipline threads |
| `/flashcards <case-name> ["topic"] [n]` | `output/<case>/flashcards.csv` → verified → `.anki.txt` (basic) + `.cloze.anki.txt` (cloze) for deck `AI Study::<case>`, plus `.html` flip cards whose slide citations open the cited slide |
| `/quiz <case-name> ["topic"] [n]` | One vignette at a time. Explanations quote the slide, and misses are saved to `weak-spots.md` |
| `/flashcards <case-name>` again | New cards aimed at your weak spots. Re-importing updates cards instead of duplicating them |
| `/study-guide <case-name> ["topic"]` | A cited reference to check yourself against **after** recall, with "beyond the slides" boxes from StatPearls/PubMed |
| `/deepen "<concept>" [case-name]` | "How do we know?" explainer from StatPearls, reviews, and Paperclip full text |
| `/visualize <case-name> "topic"` | A cited diagram spec, a rendered diagram, and Anki Image Occlusion cards (see "See it, drill it, sync it") |
| `/mnemonic-art <case-name> ["concept"]` | One captioned AI illustration as a memory hook. An aid, never a reference |
| `/anki-sync <case-name>` | Pushes your cards and diagram cards into Anki desktop, and pulls cards you keep missing back into `weak-spots.md` |

**Card types.** Basic cards are a question and an answer. Cloze cards hide part of a sentence
in Anki markup, e.g. `Exfoliative toxin cleaves {{c1::desmoglein-1}}.` In Anki, import each
file once (File → Import). Re-importing an edited deck updates cards instead of duplicating them.

These cards **supplement** a premade deck (e.g. AnKing): they follow *your
course's* cases and faculty emphasis, tagged by discipline.

## See it, drill it, sync it

Three optional commands add pictures and a live link to Anki. Each runs only when you type it.

- `/visualize <case> "topic"` writes a cited diagram spec (`output/<case>/diagrams/<slug>.json`), checks it
  like a deck, renders it with the diagram-design plugin, and cuts one occlusion card per label.
- `/mnemonic-art <case> ["concept"]` draws one memory-hook picture. It is an **aid**: it is always labeled
  "AI illustration - not a reference", and a citation always points to your notes.
- `/anki-sync <case>` adds your cards to Anki desktop and reads back the ones you miss. It only touches
  notes in `AI Study::<case>` tagged `msad`. Your other decks are never changed.

One-time setup:

1. **diagram-design plugin** (for `/visualize`). In Claude Code run
   `/plugin marketplace add cathrynlavery/diagram-design`, then `/plugin install diagram-design@diagram-design`.
   `/visualize` installs the teaching profile (`docs/diagram-teaching-profile.md`) for you.
2. **Chromium** (for occlusion boxes and card images): `uv run --with playwright playwright install chromium`
3. **AnkiConnect** (for `/anki-sync`): in Anki desktop, Tools > Add-ons > Get Add-ons, code `2055492159`,
   restart Anki. Keep Anki open while you sync.
4. **OpenRouter key** (for `/mnemonic-art` only): create a key at openrouter.ai with a **spend limit**, then
   `export OPENROUTER_API_KEY=...`. Each image costs your OpenRouter credits.
   `/mnemonic-art` sends the prompt you approve to a second provider (OpenRouter), so check your school's AI
   policy first. `/visualize` and `/anki-sync` send nothing new.

Pick **one** way to get the diagram cards into Anki:

- `/anki-sync <case>` creates Image Occlusion notes (the masks stay editable), or
- File > Import `output/<case>/diagrams.apkg` (no add-on; each label becomes a masked card).

To see them on your study page, add the folders to the export:

```bash
uv run scripts/export.py output/<case>/flashcards.csv --guide output/<case>/study-guide.md \
    --notes notes/<case> --diagrams output/<case>/diagrams
```

To include your AI illustrations too, add `--art output/<case>/art` to the end of that command.

The page gets a Diagrams tab (the picture plus each label with its citation) and, with `--art`, a Memory aids
tab under the heading "AI illustrations — memory aids, not references". `--deepen output/<case>/deepen` adds a Deep dives tab with your `/deepen` explainers. A finished example, with no art, is in
`examples/diagrams/` and `examples/flashcards.html`.

## What the checker proves, and what it doesn't

- Course citation: `[[MICRO/Staph aureus#S3]]` = that deck, slide 3 (`#P12` = Word paragraph, `#T2` = Word table)
- Literature citation: `[PMID:26016486]` = a real PubMed record

AI models can invent realistic-looking PMIDs. `scripts/check.py`:
- **catches:** PMIDs that don't exist, retracted papers, slides that don't exist, cards or guide bullets with no citation, and malformed cloze markup
- **does not catch:** a real source that doesn't actually say what the card claims, or a medical error

So **PASS means "the sources exist."** Before you study a deck, open 2–3 cited
slides or papers and compare: on the study page, a slide citation opens that slide. See it fail on purpose:

```bash
uv run scripts/check.py examples/hallucination-test.csv --notes sample/notes
```

## Connectors (`.mcp.json`)

- **PubMed**: `@cyanheads/pubmed-mcp-server` (open source, Node 24+, pinned version).
  Optional: set `NCBI_API_KEY` (free from your NCBI account) and `NCBI_EMAIL` for higher rate limits.
- **Paperclip**: hosted biomedical full-text search (`paperclip.gxl.ai`), 3M+ papers.
  Sign in once through `/mcp` in Claude Code. That's all `/deepen` needs. The `paperclip` CLI is optional.
- If PubMed is down, the skills still work from your slides and say that the literature step was skipped.

Prefer open source end to end? [`docs/OPEN-RESOURCES.md`](docs/OPEN-RESOURCES.md)
lists trusted free sources (StatPearls, DailyMed, Europe PMC, OpenStax),
open agents (OpenCode, Aider, Goose), local models (Ollama), and ten ways to
use the loop.

## Ground rules

1. **Never put patient information (PHI) into these tools.** Course slides
   normally have none. If a deck includes real patient cases or images, leave it out.
2. **Slides stay out of git and out of public places.** They belong to your
   school. The agent *does* send the text it reads to your AI provider (and
   Paperclip searches go to Paperclip), so follow your school's AI policy for
   course materials. For fully local use, see "private mode" in `docs/OPEN-RESOURCES.md`.
   The `<name>_sources/` folder next to a study page is a copy of slide text: keep it to yourself.
3. **The course is the exam's ground truth.** When a source disagrees, the
   agent flags a ⚠️ discrepancy for you to ask faculty about. It never
   overwrites the slide, and it only checks the topics it researched.
4. **AI pictures are memory aids.** Diagrams are cited specs you can check. `/mnemonic-art` pictures are
   labeled aids, not sources, and each one costs credits and goes to a second provider.
5. **Spot-check before you study.** PASS means the sources exist, not that they're right.
6. **Study aid, not a shortcut.** Don't use it for graded work.
7. **Do the reviews yourself.** The agent writes the cards, but the learning comes from recalling the answers.

## Repo map

```
CLAUDE.md                 rules the agent follows (citations, sources, style)
.claude/skills/           /ingest /flashcards /quiz /study-guide /deepen /visualize /mnemonic-art /anki-sync
.mcp.json                 PubMed + Paperclip connectors
.claude/settings.json     pre-approves only the 3 scripts + PubMed/Paperclip tools (edits still ask)
scripts/extract.py        pptx/docx -> Markdown with [S#]/[P#]/[T#] anchors
scripts/check.py          citation verifier (PubMed lookup, slide anchors, coverage)
scripts/export.py         CSV -> Anki import files (basic + cloze) + flip-card page with clickable sources, diagrams, and memory aids
scripts/occlude.py        diagram HTML -> occlusion boxes, masked cards, diagrams.apkg (needs Chromium)
scripts/anki_sync.py      pushes cards and diagram cards into Anki desktop through AnkiConnect
scripts/mnemonic_art.py   one captioned AI illustration through your OpenRouter key
sample/                   synthetic lecture to practice on
examples/                 finished guide + deck + one cited diagram built from the sample
docs/OPEN-RESOURCES.md    open-source and trusted-source menu + ideas
curriculum/               YOUR files go here (gitignored)
tests/                    script tests: uv run --with pytest --with markdown --with genanki --with pillow --with playwright pytest tests -q
```
