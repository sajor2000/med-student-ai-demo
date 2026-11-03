# Med Student AI Study Agent

Turn **your own course slides** into **cited study guides, Anki flashcards,
and practice quizzes** with an AI coding agent (Claude Code, Codex, or an
open-source agent), PubMed, and Paperclip.

Every fact the agent writes links back to a **slide number** in your deck or
a **PubMed record**, and a checker script verifies each link before you study
from it.

```
  your slides ──► extract ──► draft guide / cards ──► check citations ──► Anki + study page
       ▲                          │    ▲                    │
       │                     PubMed / StatPearls       FAIL → agent fixes
       └──────────── quiz → weak spots → new cards ◄────────┘
```

Built for M1/M2 students in a case-based basic-science curriculum. Nothing
here is tied to one school.

## Quick start (5 minutes)

```bash
# 1. Prereqs: uv (Python), Node 24+, and Claude Code (or Codex / OpenCode)
brew install uv node        # macOS; see docs.astral.sh/uv for Windows/Linux
git clone https://github.com/<you>/med-student-ai-demo && cd med-student-ai-demo

# 2. Try it on the synthetic sample lecture (no course files needed)
uv run scripts/extract.py sample/curriculum --out sample/notes
uv run scripts/check.py examples/flashcards.csv --notes sample/notes
uv run scripts/export.py examples/flashcards.csv --guide examples/study-guide.md
open examples/flashcards.html
```

## Use it on your own course

1. Copy one case's slides/guides into `curriculum/<case-name>/` (gitignored and never committed).
2. Start your agent in this folder: `claude`. It reads `CLAUDE.md` (the rules).
3. Run the skills in order:

| Command | What you get |
|---|---|
| `/ingest <case-name>` | Notes with slide anchors, plus a map of the case's topics and cross-discipline threads |
| `/study-guide <case-name> [topic]` | `output/<case>/study-guide.md`: integrated, every bullet cited, "beyond the slides" PubMed boxes |
| `/flashcards <case-name> [topic] [n]` | `flashcards.csv` → verified → `.anki.txt` (import into Anki) + `.html` flip cards |
| `/deepen "<concept>"` | Short explainer from StatPearls, reviews, and full text via Paperclip |
| `/quiz <case-name> [topic]` | Interactive vignette questions, with weak spots saved for your next deck |

## Citations, and why the checker matters

- Course: `[[MICRO/Staph aureus#S3]]` = that deck, slide 3
- Literature: `[PMID:26016486]` = a real, verified PubMed record

AI models can invent realistic-looking PMIDs. `scripts/check.py` looks up
every PMID in PubMed, flags retracted papers, confirms that every cited
slide exists, and fails any flashcard with no source. Try it:

```bash
uv run scripts/check.py examples/hallucination-test.csv --notes sample/notes   # FAILs on purpose
```

## Connectors (`.mcp.json`)

- **PubMed**: `@cyanheads/pubmed-mcp-server` (open source, needs Node 24+). Optional: set
  `NCBI_API_KEY` (free from your NCBI account) and `NCBI_EMAIL` for higher rate limits.
- **Paperclip**: hosted biomedical full-text search (`paperclip.gxl.ai`), with
  3M+ papers. Sign in on first use. Optional CLI: `paperclip`.

Prefer open source end to end? See [`docs/OPEN-RESOURCES.md`](docs/OPEN-RESOURCES.md):
trusted free sources (StatPearls, DailyMed, Europe PMC, OpenStax), open agents
(OpenCode, Aider, Goose), local models (Ollama), and ten ways to use the loop.

## Ground rules

1. **Your slides stay on your machine.** They belong to your school.
2. **The course is the exam's ground truth.** When a source disagrees, the
   agent flags a ⚠️ discrepancy for you to ask faculty about. It never overwrites the slide.
3. **Study aid, not a shortcut.** Don't use it for graded work.
4. **Do the reviews yourself.** The agent writes the cards, but the learning comes from recalling the answers.

## Repo map

```
CLAUDE.md                 rules the agent follows (citations, sources, style)
.claude/skills/           /ingest /study-guide /flashcards /deepen /quiz
.mcp.json                 PubMed + Paperclip connectors
scripts/extract.py        pptx/docx → Markdown with [S#]/[P#] anchors
scripts/check.py          citation verifier (PubMed lookup + slide anchors)
scripts/export.py         CSV → Anki import file + flip-card study page
sample/                   synthetic lecture to practice on
examples/                 finished guide + deck built from the sample
docs/OPEN-RESOURCES.md    open-source and trusted-source menu + ideas
curriculum/               YOUR files go here (gitignored)
```
