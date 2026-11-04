# Open and trusted resources for an AI study loop

A menu for M1/M2 students: free or open-source pieces you can plug into the
agent loop (**read course material → draft → cite → verify → review → repeat**).
Check each tool's license and your school's AI policy before using it with
course files.

## 1. Trusted sources the agent can cite

| Need | Resource | Why it's trusted | How the agent reaches it |
|---|---|---|---|
| Literature search | **PubMed / MEDLINE** | NLM-indexed, MeSH-tagged | PubMed MCP server, NCBI E-utilities (free API key) |
| Open full text | **PubMed Central OA**, **Europe PMC** | Full text you can legally read and quote briefly | Europe PMC REST API, Paperclip |
| Review-level textbook | **StatPearls** (NCBI Bookshelf) | Peer-reviewed, updated, free; chapters have PMIDs | PubMed search `statpearls[book]` |
| Genetics and genomics courses | **GeneReviews**, **ClinVar**, **MedGen** | Expert-authored, NCBI-hosted | E-utilities |
| Older free textbooks | NCBI Bookshelf (e.g. *Medical Microbiology*, Baron, 4th ed.) | Classic texts, free online | Bookshelf search |
| Open textbooks | **OpenStax** *Anatomy & Physiology*, *Microbiology*; **LibreTexts** | CC-BY, faculty-reviewed | Web fetch |
| Drug facts | **DailyMed** (FDA labels), **openFDA**, **RxNorm/RxNav** | The official label is the legal source of truth | Free REST APIs |
| Management | **CDC**, **WHO**, **IDSA** guidelines | Society/agency consensus | Web fetch |
| Vocabulary | **MeSH**; UMLS (free license) | Standard terms, synonyms | PubMed MCP `lookup_mesh` |
| Is a paper retracted? | **Crossref + Retraction Watch** data (open since 2023); PubMed "Retracted Publication" type | Catches bad citations | `scripts/check.py` flags PubMed retractions |
| Exam blueprint | **USMLE Step 1 content outline** (public PDF) | What is actually tested | Map objectives to outline (gap check) |

Images: course figures and most atlases are copyrighted. For open images, use
**Wikimedia Commons** (check each file's license) and the CDC **Public Health
Image Library**.

## 2. Open-source tools for the loop

| Step | Open-source option | Notes |
|---|---|---|
| Agent harness | **OpenCode**, **Aider**, **Goose**, **Cline** (Claude Code / Codex are not open source) | All can read `CLAUDE.md`/`AGENTS.md`-style rules and call MCP servers |
| Literature tools | **PubMed MCP server** (`@cyanheads/pubmed-mcp-server`), **Zotero** + a Zotero MCP server | Zotero becomes your personal citation library |
| Local / private models | **Ollama** or **LM Studio** with open-weight models (Llama, Qwen, Gemma, gpt-oss) | Course files stay on your laptop; weaker at accuracy, so run the citation check |
| Flashcards | **Anki** (open source) + **FSRS** scheduler, **genanki** (build `.apkg` in Python), **AnkiConnect** (open source; wired into `/anki-sync`, which adds your cards and reads which ones you miss) | Lets the agent see which cards you miss and write new ones on those weak spots |
| Notes / knowledge base | **Logseq** (open source), **Obsidian** (free, closed), plain Markdown + git | `[[wikilinks]]` match this repo's citation style |
| Document conversion | **pandoc**, **python-pptx**, **python-docx**, **Docling**, **MarkItDown** | Turn slides and PDFs into text the agent can cite |
| Diagrams / concept maps | **Mermaid**; **diagram-design** (MIT, by cathrynlavery; wired into `/visualize`) | Agent draws the micro → immuno → path → pharm map in text, or a cited diagram that becomes Image Occlusion cards |
| Verification / CI | **GitHub Actions** running `scripts/check.py` | In a *private* study-group repo, the build fails if any citation breaks |

## 3. Ideas: how M1/M2 students could use the loop

1. **Slides → cited study guide** (this repo's `/study-guide`). Every bullet
   links back to a slide number; "beyond the slides" boxes add one StatPearls
   or review citation.
2. **Flashcards that know where they came from** (`/flashcards`). Every card
   carries `[[deck#S12]]` or a verified PMID, so the student can click back
   to the source whenever they doubt an answer.
3. **Weak-spot loop.** `/quiz` → misses saved to `weak-spots.md` → `/flashcards`
   targets them → Anki (via AnkiConnect) reports lapses → next quiz.
4. **Discrepancy finder.** The agent compares slides with current
   StatPearls/IDSA/DailyMed and flags differences (e.g. a resistance
   pattern, a dosing note) for the student to ask faculty about. It doesn't
   overwrite the slide.
5. **Integration maps.** For each case, a Mermaid map connecting each
   discipline's facts, with a citation on every edge.
6. **Teach-back grading.** The student explains a mechanism out loud or in
   writing; the agent grades it against the slides and points to the exact slide for each gap.
7. **"How do we know this?" boxes.** `/deepen` finds the landmark paper behind a
   fact (e.g. the discovery of PBP2a/mecA) and reads the full text through Paperclip.
8. **Blueprint gap check.** Map the case objectives to the USMLE Step 1
   content outline and list the outline topics the case never covers.
9. **Private study-group repo.** Each student adds cards in a pull request,
   and CI runs `check.py` before merging. Keep that repo **private** and within
   your course's sharing rules: cards built from faculty slides are course
   material, so they never go in this public repo or a public fork.
10. **Private mode.** The same skills running on a local model through
    Ollama, for students who don't want course files sent to any cloud service.

## 4. Guardrails to teach alongside the tools

- **Never trust a citation the checker hasn't verified, and spot-check the ones
  it has.** LLMs invent realistic-looking PMIDs, and a real PMID can still be
  the wrong paper for the claim.
- **Course material is the exam's ground truth.** Bring discrepancies to
  faculty; don't let the AI quietly overrule them.
- **Copyright:** keep slides local and never post them to a public repo or
  shared deck.
- **Integrity:** use the tools for studying, not for graded work.
- **Active recall beats rereading.** The AI writes the cards, but you still
  have to do the reviews.
