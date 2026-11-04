---
title: Visual Learning and Anki Sync - Plan
type: feat
date: 2026-11-03
artifact_contract: ce-unified-plan/v1
product_contract_source: ce-plan-bootstrap
execution: code
---

# Visual Learning and Anki Sync - Plan

## Goal Capsule

- **Objective:** An M1/M2 student can turn a case topic into a cited teaching diagram they drill as Image Occlusion cards, add optional AI memory-aid art that is clearly marked as not a reference, and have every verified card land in Anki desktop, with the cards they keep missing feeding their next flashcard and quiz run.
- **Means:** A cited diagram spec rendered by the diagram-design plugin (KTD1, KTD2), a label-masking script that yields Image Occlusion notes plus a portable masked-card fallback (KTD3, KTD4), an AnkiConnect client limited to the student's AI Study decks (KTD5), and an OpenRouter illustration script that stamps every image (KTD6). The new skills are written in the writing-for-agents style (KTD7).
- **Authority:** Product Contract requirements (R1–R10) > Key Technical Decisions > unit Approach text.
- **Stop conditions:**
  - Stop if any unit needs course files committed.
  - Stop if a unit would let an AI image act as a citation.
  - Stop if a unit would write to, edit, or delete notes outside the student's `AI Study::` decks.
- **Execution profile:** One repo, several standalone uv scripts, three new skills, and doc updates. Built on branch `feat/cloze-cards-source-links` (open PR #1), and shipped as one PR after the 2026-11-04 class demo.

---

## Product Contract

### Summary

Add three study features to the loop.
- `/visualize` builds a cited mechanism or concept diagram and turns its labels into Image Occlusion cards.
- `/mnemonic-art` makes optional, clearly labeled AI memory-aid images through OpenRouter.
- `/anki-sync` pushes verified cards into Anki desktop and pulls frequently missed cards back as weak spots.

### Problem Frame

Basic science is half visual: pathways, mechanisms, and structures are learned as pictures. The repo produces only text cards, and students still import files into Anki by hand, so the quiz-to-weak-spots loop never sees which cards a student actually misses in Anki. The demo audience asked for visual study tools, and the instructor chose diagram-design for diagrams and OpenRouter for images.

### Requirements

- **R1.** `/visualize` produces a diagram for one case topic where every node and every edge label carries a course or PubMed citation, and `scripts/check.py` fails the diagram when any label lacks one or a citation does not resolve.
- **R2.** The diagram renders through the diagram-design plugin as self-contained HTML/SVG, plus a PNG.
- **R3.** Each cited label becomes one Image Occlusion card ("hide one, guess one") whose answer is that label.
- **R4.** The same labels also produce portable masked-image cards (front: diagram with one label masked; back: full diagram) in an offline `.apkg`, usable without AnkiConnect.
- **R5.** The study page shows diagrams in their own section, with each label's citation clickable, as for cards.
- **R6.** `/mnemonic-art` generates an illustration for one concept through an OpenRouter image model only when the student has set their own key. Every saved image carries the visible caption "AI illustration — not a reference".
- **R7.** AI illustrations are never accepted as citations, and prompts sent to the image model contain no patient-identifying content.
- **R8.** `/anki-sync` adds or updates basic, cloze, and diagram cards in `AI Study::<case>` decks without creating duplicates on repeat runs.
- **R9.** Sync never edits or deletes notes outside the decks it owns.
- **R10.** Sync reads review history for its own cards and appends each card whose lapse count reaches the threshold to `output/<case>/weak-spots.md` once, in the format `/flashcards` already reads.

### Key Decisions

- **Build all three, after the demo.** Governs R1–R10. (session-settled: user-directed — chosen over one pre-made diagram for the demo: user asked to plan all three)
- **diagram-design (cathrynlavery) is the diagram engine.** Governs R2. (session-settled: user-directed — chosen over Excalidraw as primary: user named it)
- **AI images are memory aids only, never sources.** Governs R6, R7. (session-settled: user-approved — chosen over using image-model output as labeled figures: image models invent structures and garble labels)
- **Images go through OpenRouter.** Governs R6. (session-settled: user-directed — chosen over other image APIs: user named it)
- **Anki desktop stays the review app.** Governs R3, R4, R8–R10. (session-settled: user-approved — chosen over Logseq, Obsidian plugins, Mochi: free, open source, already used)
- **No course files in the public repo; standalone uv scripts; citation syntax unchanged.** Governs R1, R4, R5. (session-settled: user-directed — chosen over a private repo with course files, a packaged project, and footnote citations)

### Scope Boundaries

- Data-shaped scientific plots (dose-response, Michaelis–Menten, pressure–volume loops) are deferred. diagram-design's line and scatter types may cover them later.
- Real histology, radiology, or photographic images are out of scope.
- AnkiMobile/iPhone-specific behavior, shared or hosted decks, and AnkiHub are out of scope.

### Assumptions

- Students run Anki desktop 23.10 or later (built-in Image Occlusion). Sync needs the AnkiConnect add-on (code 2055492159) with Anki open.
- Lapse threshold for weak spots defaults to 3, overridable per run.
- The default image model is `google/gemini-2.5-flash-image`, listed in OpenRouter's image-generation docs, overridable by an environment variable. The key comes from `OPENROUTER_API_KEY`.
- Students who use `/visualize` install the diagram-design plugin and Playwright's Chromium once. The README documents both.

---

## Planning Contract

### Key Technical Decisions

- **KTD1. A diagram is a cited JSON spec first, a picture second.** The agent writes `output/<case>/diagrams/<slug>.json`: nodes and edges, each with a stable `id`, a short label, and a citation in the existing syntax. `<case>` and `<slug>` are restricted to `[a-z0-9-]` and every resolved path must stay under `output/<case>/`. A PASS proves each label's source exists, not that it supports the label; the skill points the student to one label to spot-check, as for cards. `check.py` validates the spec as it does decks: every label cited, every citation resolves. The spec is what diagram-design draws from and what the occlusion step reads. Labels stay checkable text instead of pixels.
- **KTD2. diagram-design renders the spec, with a teaching profile students install once.** The `/visualize` skill hands the spec to diagram-design (flowchart, tree, nested, or quadrant type by topic shape), which writes `<slug>.html`. The plugin resolves profiles only from `~/.diagram-design/profiles/<slug>.md`. So the repo commits the profile in plugin format (metadata header plus full style-guide body) at `docs/diagram-teaching-profile.md`. A `/visualize` preflight copies it to `~/.diagram-design/profiles/teaching.md` when absent, and the committed `.diagram-design` marker contains exactly `profile: teaching`. Every SVG `<text>` label, node or edge, carries `data-node="<id>"` from the spec, so later steps find labels without OCR. (session-settled: user-directed — chosen over Excalidraw as primary: user named diagram-design)
- **KTD3. Boxes and the card image come from one render.** A new uv script opens the diagram HTML in headless Chromium (Playwright, the same dependency diagram-design's exporter uses), with JavaScript disabled and every non-file request blocked.
  - It sizes the SVG to its viewBox in pixels, waits for `document.fonts.ready`, and computes each `[data-node]` box with `getBBox` in viewBox units, normalized to 0–1.
  - It screenshots that same `<svg>` element with an opaque paper background as the card image. The plugin's own PNG export is display-only.
  - It enforces the spec both ways: every spec id has exactly one element, every `<text>` has a spec id, and each element's text equals its spec label after whitespace normalization. A mismatch fails the run.
  - It writes `<slug>.occlusion.json` (image, one box per label, answer, citation) and renders, per label, one masked PNG and one highlighted PNG for KTD4.
- **KTD4. Two delivery paths from one occlusion file; a student uses one.** Each label gets its own stable id, `msad-<sha1(slug + ":" + node id)[:12]>`, so a missed card maps to exactly one label and regenerating a diagram never re-maps review history.
  - *Primary, Image Occlusion via AnkiConnect:* one Image Occlusion note per label, holding a single occlusion. The Occlusion field uses Anki's stored occlusion syntax, captured from a real note during U2 and pinned in a test (see Risks).
  - *Fallback, portable masked-image cards:* one basic note per label (front: masked PNG; back: highlighted PNG, the answer, and its citation), packaged with `genanki` into `output/<case>/diagrams.apkg` under `AI Study::<case>::diagrams-offline`. Sync never touches that subdeck, and the docs tell students to pick one path per diagram.
- **KTD5. Sync owns only what it created, by deck and by tag.**
  - Every synced note carries the tags `msad` and `msad-id::<stable id>` and lives under `AI Study::<case>`. `<case>` is validated to `[a-z0-9-]` before it enters any search string.
  - Upsert searches `deck:"AI Study::<case>" tag:msad-id::<id>`. Before each `updateNoteFields`, the client confirms through `cardsInfo` that every card of the note sits under `AI Study::<case>`; otherwise it skips and counts the note.
  - *Adoption:* a note already in the owned deck without `msad-id`, whose Front hashes via `guid()` to a card's id (a hand-imported `.anki.txt` card), is tagged and updated in place instead of duplicated.
  - Media is uploaded as `msad-<id>-<sha256 prefix>.png` with `deleteExisting: false`, so a student's own media is never replaced.
  - The client sends only an allowlist of actions (`version`, `deckNames`, `createDeck`, `modelNames`, `findNotes`, `findCards`, `notesInfo`, `cardsInfo`, `addNote`, `updateNoteFields`, `addTags`, `storeMediaFile`) to `http://127.0.0.1:8765`, API version 6. Any other action, including `multi`, raises.
  - Before adding Image Occlusion notes, it checks `modelNames`. Anki creates that note type only after its editor is opened once, so a missing type skips diagram notes with that instruction and points to `diagrams.apkg`.
  - Stats come from `findCards` with the same deck and tag scope, plus `cardsInfo` lapses.
  (session-settled: user-approved — Anki desktop chosen over other SRS apps)
- **KTD6. Illustrations are confirmed before sending, stamped at write time, and kept out of the citation path.**
  - The prompt is built from the concept name and a short scene description the student approves. The script prints the exact prompt and that it goes to OpenRouter, then sends only after the student confirms. A regex refusal (MRN, date of birth, name-with-age) runs as a second check.
  - The request sets OpenRouter's provider data-collection opt-out (`provider.data_collection: "deny"`). It uses chat completions with `modalities:["image","text"]` and decodes the returned base64 PNG.
  - The key is read from `OPENROUTER_API_KEY` and never printed, logged, or written. Errors show only the status code and OpenRouter's message.
  - The script burns the caption "AI illustration — not a reference" into the image with Pillow, and writes a sidecar with prompt, model, and timestamp only.
  - Images are saved under `output/<case>/art/`. `check.py` reports any citation into that folder as unresolved.
  (session-settled: user-approved — memory aids only, never sources; user-directed — OpenRouter)
- **KTD7. New skills follow writing-for-agents.**
  - Each `SKILL.md` stays near 40 lines: a front-loaded description, steps that each end on a checkable completion criterion, positive phrasing, and one anchoring leading word (*spec* for visualize, *aid* for mnemonic-art, *owned* for sync).
  - Detail moves to a sibling `reference.md`.
  - All three are hand-fired (`disable-model-invocation: true`), so they add no always-loaded context.
  (session-settled: user-directed — chosen over long monolithic skills)

### High-Level Technical Design

```mermaid
flowchart LR
  N[notes/case] --> S[diagram spec JSON\ncited nodes + edges]
  S --> C[check.py\nevery label cited]
  S --> D[diagram-design\nHTML/SVG + PNG]
  D --> O[occlude script\nlabel boxes + masked PNGs]
  O --> IO[Image Occlusion notes]
  O --> APKG[diagrams.apkg\nmasked-image cards]
  IO --> A[anki-sync\nAI Study::case only]
  CSV[flashcards.csv] --> A
  A -->|lapses >= 3| W[weak-spots.md]
  W --> F[/flashcards, /quiz]
  K[OpenRouter key] --> M[mnemonic-art\nstamped image]
  M --> P[study page: Memory aids]
  D --> P2[study page: Diagrams]
```

### Risks & Dependencies

- **Image Occlusion field grammar is undocumented.** The Anki manual describes the editor, not the stored field. U2 captures a real note's fields (created in Anki's editor, read back with AnkiConnect `notesInfo`) as a fixture and pins the generator against it. If AnkiConnect cannot add notes of that type, the masked-card fallback (R4) still delivers occlusion study, and R3 is reported as blocked rather than faked.
- **Playwright Chromium install** is a one-time student cost (`uv run --with playwright playwright install chromium`). diagram-design's exporter already needs it.
- **OpenRouter costs and model churn:** the model is an environment variable, and the skill states that each image costs the student's own credits.

---

## Implementation Units

### U1. Cited diagram spec and its check

**Goal:** A diagram spec format the checker validates like a deck.
**Requirements:** R1
**Dependencies:** none
**Files:** `scripts/check.py`, `tests/test_check.py`, `tests/fixtures/diagram-spec.json`
**Approach:**
1. Accept `.json` diagram specs in `check.py`: nodes and edges, each with `label` and `cite`.
2. Report every label without a citation, and every unresolved course or PMID citation, using the existing resolution code.
**Patterns to follow:** the deck branch of `load_units` and `uncited_guide_lines`.
**Test scenarios:**
- A spec whose nodes and edges are all cited to existing sample slides passes.
- A node with an empty `cite` fails, naming the node id.
- An edge citing a slide anchor that does not exist fails.
- A malformed spec (missing `nodes`) fails with a readable message, not a traceback.
**Verification:** tests pass, and the existing deck and guide checks are unchanged.

### U2. Occlusion boxes, masked cards, and the offline deck

**Goal:** Turn a rendered diagram into an occlusion file, per-label masked PNGs, Image Occlusion note fields, and `diagrams.apkg`.
**Requirements:** R3, R4
**Dependencies:** U1
**Files:** `scripts/occlude.py`, `tests/test_occlude.py`, `tests/fixtures/diagram.html`, `tests/fixtures/diagram-spec.json`, `tests/fixtures/io-note-fields.json`
**Approach:**
1. Load the diagram HTML headless. Read each `[data-node]` text box relative to the SVG, and normalize it.
2. Write `<slug>.occlusion.json`. Render one PNG per label with only that label covered.
3. Build Image Occlusion field values from the occlusion file, matching the captured fixture (Risks).
4. Package masked-image basic notes and media into `diagrams.apkg` with stable IDs.
**Execution note:** Capture the Image Occlusion fixture from a real Anki note before writing the field generator.
**Patterns to follow:** `guid()` and Anki header conventions in `scripts/export.py`.
**Test scenarios:**
- The fixture diagram with two node labels and one edge label yields three boxes, each inside 0–1 and matching its id.
- A mask box covers the label's pixels in the screenshot, even when the HTML page has a title and margins around the SVG.
- A spec id with no element, an extra `<text>` with no spec id, and a label whose text differs from the spec each fail the run, naming the id.
- A `<script>` in the fixture HTML never runs (JavaScript disabled), and the run still succeeds.
- A `../` slug is rejected before anything is written.
- The generated Occlusion field for the fixture equals the captured real-note format.
- The `.apkg` contains one note per label (masked front, highlighted back with answer and citation) in the offline subdeck, with IDs stable across two runs and unchanged for the other labels when one node is added.
- The Playwright-dependent tests skip with a clear reason when Chromium is not installed.
**Verification:** tests pass, and `diagrams.apkg` imports into Anki and shows one masked card per label.

### U3. `/visualize` skill and teaching profile

**Goal:** A hand-fired skill that takes a case topic to a checked, rendered, occlusion-ready diagram.
**Requirements:** R1, R2, R3, R4
**Dependencies:** U1, U2
**Files:** `.claude/skills/visualize/SKILL.md`, `.claude/skills/visualize/reference.md`, `.diagram-design`, `docs/diagram-teaching-profile.md` (plugin profile format)
**Approach:**
1. Write the skill per KTD7: read notes, write the *spec*, check until PASS, render with diagram-design (type by topic shape, `data-node` on labels), occlude, then report paths and card counts.
2. Put type-selection guidance, the spec schema, and the diagram-design handoff in `reference.md`.
3. Commit the marker (`profile: teaching`) and the profile file. Add a preflight step that installs the profile into `~/.diagram-design/profiles/` when it is missing.
**Test expectation:** none -- skill prose and config. Verified by running `/visualize` on the synthetic sample.
**Verification:** `/visualize` on `sample/` yields a passing spec, HTML, PNG, an occlusion file, and an `.apkg`, with no style-guide prompt.

### U4. AnkiConnect client and weak-spot feedback

**Goal:** A uv script that upserts owned notes and returns frequently missed cards.
**Requirements:** R8, R9, R10
**Dependencies:** U2
**Files:** `scripts/anki_sync.py`, `tests/test_anki_sync.py`
**Approach:**
1. Check the AnkiConnect version, and create `AI Study::<case>` when it is missing.
2. Upsert per KTD5: basic or cloze notes from `flashcards.csv` rows (cloze when the front carries cloze markup, as export.py's `is_cloze` decides), and one Image Occlusion note per label from occlusion files. Adopt hand-imported notes first, store media, then update or add.
3. Read `findCards` and `cardsInfo` for owned cards only. Append cards with lapses at or above the threshold to `weak-spots.md` once each.
4. Print a one-line summary of added, updated, skipped, and weak spots.
**Patterns to follow:** the `guid()` scheme, and the weak-spots line format from the quiz skill.
**Test scenarios:** use a fake AnkiConnect server in tests.
- First sync adds every card; a second sync updates and adds none.
- A hand-imported note in the owned deck (no tags, Front hashing to a card id) is adopted and updated, not duplicated.
- A note tagged `msad-id::<id>` but sitting in a foreign deck is skipped and counted, never updated.
- An unrelated note in the owned deck (no tag, Front matching no card) is never updated.
- Every recorded request uses an allowlisted action; `multi` or any other action raises.
- A pre-existing media file with a generic name is never replaced; uploads use the hashed name with `deleteExisting` false.
- A case name containing a quote, `*`, or `../` is rejected before any request.
- A collection without the Image Occlusion note type skips diagram notes and prints the open-the-editor-once hint.
- Cards with 3 lapses are appended once, and a re-run does not duplicate them.
- AnkiConnect unreachable gives a one-line hint (open Anki, install add-on 2055492159) and exit code 2.
- A version mismatch is reported, not ignored.
**Verification:** tests pass, and a manual run against real Anki adds then updates without duplicates.

### U5. `/anki-sync` skill and loop wiring

**Goal:** A hand-fired skill around U4, and pointers from the existing loop.
**Requirements:** R8, R10
**Dependencies:** U4
**Files:** `.claude/skills/anki-sync/SKILL.md`, `.claude/skills/anki-sync/reference.md`, `.claude/skills/flashcards/SKILL.md`, `.claude/skills/quiz/SKILL.md`, `.claude/settings.json`
**Approach:**
1. Write the skill per KTD7 around the *owned* leading word: check first, sync, then report weak spots.
2. Add one line to flashcards and quiz suggesting `/anki-sync <case>` after a run.
3. Allowlist only `uv run scripts/anki_sync.py`.
**Test expectation:** none -- skill prose. Verified by the U4 tests and a manual run.
**Verification:** `/anki-sync sample` runs end to end against Anki, or prints the add-on hint when Anki is closed.

### U6. `/mnemonic-art` script and skill

**Goal:** Optional, stamped memory-aid illustrations through OpenRouter.
**Requirements:** R6, R7
**Dependencies:** none
**Files:** `scripts/mnemonic_art.py`, `tests/test_mnemonic_art.py`, `scripts/check.py`, `tests/test_check.py`, `.claude/skills/mnemonic-art/SKILL.md`, `.claude/skills/mnemonic-art/reference.md`
**Approach:**
1. Exit with setup instructions when `OPENROUTER_API_KEY` is unset.
2. Build, print, and confirm the prompt per KTD6. Send with the data-collection opt-out, and refuse patient-identifying patterns.
3. Call OpenRouter, decode the PNG, burn in the caption, and save the image and a sidecar under `output/<case>/art/`.
4. Write the skill per KTD7 around the *aid* leading word, with prompt patterns in `reference.md`.
**Test scenarios:** use a mocked HTTP response.
- A successful response saves a PNG whose bottom band contains the caption, plus a sidecar with the prompt.
- No key prints setup steps and makes no network call.
- A prompt containing an MRN-like number or a date of birth is refused before any network call.
- A response with no `images` field fails with a readable message.
- `check.py` reports a citation pointing into `output/<case>/art/` as unresolved (test in `tests/test_check.py`).
- A fake key never appears in stdout, stderr, or the sidecar, on success or on an HTTP error.
- Without confirmation, no network call is made.
**Verification:** tests pass, and one real call with a key produces a captioned image.

### U7. Study page sections, examples, and docs

**Goal:** Diagrams and memory aids appear on the study page, and the docs describe all three skills.
**Requirements:** R5, R6, R7
**Dependencies:** U1–U6
**Files:** `scripts/export.py`, `tests/test_export.py`, `examples/`, `README.md`, `CLAUDE.md`, `docs/OPEN-RESOURCES.md`
**Approach:**
1. Add `--diagrams` and `--art` folders to `export.py`.
2. Render a Diagrams tab: the image, its labels with linked citations via the existing `SourceLinker`, and a Memory aids tab where every image keeps its caption.
3. Regenerate the synthetic examples with one diagram, without art (no key in CI).
4. Document setup (diagram-design plugin and teaching profile, Chromium, AnkiConnect add-on 2055492159, OpenRouter key with a spend limit, and cost). Say that `/mnemonic-art` sends the approved prompt to a second provider, OpenRouter, so students check their school's AI policy, and that students pick one of the two diagram paths.
**Test scenarios:**
- With `--diagrams`, the page shows each diagram's PNG (never its SVG/HTML), with escaped labels whose course citations link to source pages; a label containing `<img onerror>` renders as text.
- With `--art`, every memory-aid image appears under a heading that states it is not a reference.
- Without either flag, the page is unchanged from today.
**Verification:** tests pass, and the example page shows the diagram tab in a browser.

---

## Verification Contract

- `uv run --with pytest --with markdown --with genanki --with pillow pytest tests -q` passes. Playwright tests skip only when Chromium is missing.
- `check.py` passes on the example deck, the guide, and the diagram spec. The hallucination test still fails with three problems.
- Manual Anki pass before merge:
  1. Import `diagrams.apkg` into a fresh profile and confirm the masked front and highlighted back.
  2. Run `/anki-sync sample` twice and confirm there are no duplicates and only `AI Study::` decks change.
  3. Open one Image Occlusion card.
- The diff contains nothing under `curriculum/`, `notes/`, `output/`, or `DEMO.md`.

## Definition of Done

- R1–R10 hold, and the U1, U2, U4, U6, and U7 tests pass. R3 and the Image Occlusion part of R8 may instead be reported as blocked in the PR when AnkiConnect cannot add Image Occlusion notes (see Risks); then the masked-card `diagrams.apkg` is the delivered occlusion path, and the PR says so.
- The three skills follow KTD7 (near 40 lines each, hand-fired, with a sibling reference).
- The manual Anki pass above is done, or its blocked step is named in the PR.
- No abandoned or experimental code is left in the diff.
