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
uv run scripts/export.py examples/flashcards.csv --guide examples/study-guide.md
open examples/flashcards.html
```

**Windows (PowerShell)**
```powershell
winget install astral-sh.uv OpenJS.NodeJS Git.Git
irm https://claude.ai/install.ps1 | iex       # installs Claude Code
node -v                                       # must print v24 or higher
git clone https://github.com/sajor2000/med-student-ai-demo; cd med-student-ai-demo
uv run scripts/extract.py sample/curriculum --out sample/notes
uv run scripts/check.py examples/flashcards.csv --notes sample/notes
uv run scripts/export.py examples/flashcards.csv --guide examples/study-guide.md
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
| `/flashcards <case-name> ["topic"] [n]` | `output/<case>/flashcards.csv` → verified → `.anki.txt` (deck `AI Study::<case>`) + `.html` flip cards |
| `/quiz <case-name> ["topic"] [n]` | One vignette at a time. Explanations quote the slide, and misses are saved to `weak-spots.md` |
| `/flashcards <case-name>` again | New cards aimed at your weak spots. Re-importing updates cards instead of duplicating them |
| `/study-guide <case-name> ["topic"]` | A cited reference to check yourself against **after** recall, with "beyond the slides" boxes from StatPearls/PubMed |
| `/deepen "<concept>" [case-name]` | "How do we know?" explainer from StatPearls, reviews, and Paperclip full text |

These cards **supplement** a premade deck (e.g. AnKing): they follow *your
course's* cases and faculty emphasis, tagged by discipline.

## What the checker proves, and what it doesn't

- Course citation: `[[MICRO/Staph aureus#S3]]` = that deck, slide 3 (`#P12` = Word paragraph, `#T2` = Word table)
- Literature citation: `[PMID:26016486]` = a real PubMed record

AI models can invent realistic-looking PMIDs. `scripts/check.py`:
- **catches:** PMIDs that don't exist, retracted papers, slides that don't exist, and cards or guide bullets with no citation
- **does not catch:** a real source that doesn't actually say what the card claims, or a medical error

So **PASS means "the sources exist."** Before you study a deck, open 2–3 cited
slides or papers and compare. See it fail on purpose:

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

1. **Slides stay out of git and out of public places.** They belong to your
   school. The agent *does* send the text it reads to your AI provider (and
   Paperclip searches go to Paperclip), so follow your school's AI policy for
   course materials. For fully local use, see "private mode" in `docs/OPEN-RESOURCES.md`.
2. **The course is the exam's ground truth.** When a source disagrees, the
   agent flags a ⚠️ discrepancy for you to ask faculty about. It never
   overwrites the slide, and it only checks the topics it researched.
3. **Spot-check before you study.** PASS means the sources exist, not that they're right.
4. **Study aid, not a shortcut.** Don't use it for graded work.
5. **Do the reviews yourself.** The agent writes the cards, but the learning comes from recalling the answers.

## Repo map

```
CLAUDE.md                 rules the agent follows (citations, sources, style)
.claude/skills/           /ingest /flashcards /quiz /study-guide /deepen
.mcp.json                 PubMed + Paperclip connectors
.claude/settings.json     pre-approves only the 3 scripts + PubMed/Paperclip tools (edits still ask)
scripts/extract.py        pptx/docx -> Markdown with [S#]/[P#]/[T#] anchors
scripts/check.py          citation verifier (PubMed lookup, slide anchors, coverage)
scripts/export.py         CSV -> Anki import file + flip-card study page
sample/                   synthetic lecture to practice on
examples/                 finished guide + deck built from the sample
docs/OPEN-RESOURCES.md    open-source and trusted-source menu + ideas
curriculum/               YOUR files go here (gitignored)
```
