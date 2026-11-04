# For faculty and curriculum deans

**AI powers learning; it does not replace it.** This is an educational demonstration: the
AI drafts, cites, and quizzes, and the student does the retrieving, explaining, and reviewing.

One page. Students may ask your permission to use this tool; here is what it is and
what to decide.

## Institutional policy comes first

Nothing here overrides your school's AI, data, and academic-integrity policies. Students
must confirm those policies allow uploading course content to an AI tool before they use real
materials. The licenses grant no rights to your course materials. See
[RESPONSIBLE-USE.md](RESPONSIBLE-USE.md) and [NOTICE.md](../NOTICE.md).

## What it does

A student keeps their own course slides on their own laptop. An AI coding agent
(Claude Code or Codex) reads those slides and drafts a study guide, flashcards, quiz
questions, and diagrams. Every claim carries a link to the slide it came from or to a
PubMed-verified source, and a checker script flags citations it cannot verify. The
student does the studying; the tool does the drafting and the bookkeeping.

## Data flow

| What | Where it goes |
|---|---|
| Course files (`curriculum/`, `notes/`, `output/`) | Stay on the student's machine and are git-ignored. **The AI provider reads whatever the agent reads** (slide text it is asked to process), under the provider's terms for that student's account. |
| PubMed and Europe PMC queries | Search terms and PMIDs go to NCBI/NLM. No course files are uploaded. |
| Paperclip (optional) | Paper searches go to Paperclip's service. |
| OpenRouter (optional) | Only if the student sets a key and uses the optional judgment checks; never on patient data. |
| Anki sync (optional) | Loopback only, between the agent and the student's own Anki. |

The repo contains no patient data and the tool should never be given any.

## School AI policy checklist

- [ ] Does your policy allow students to give course material to a third-party AI provider? Which providers and plans (consumer, education, enterprise with no-training terms)?
- [ ] Do you require disclosure of AI use for study aids? (Nothing here is for graded work.)
- [ ] Are slides your faculty's, licensed from a publisher, or both? Publisher-owned images may not be sent to an AI.
- [ ] Who answers student questions about this tool, and where do they report problems?
- [ ] Do you want students to bring discrepancies between AI output and lecture content to faculty? (Recommended.)

## Copyright

Course files remain the property of their authors and your institution. The tool never
redistributes them: students must not post slides, notes built from them, or generated
cards to a public repo, shared deck, or forum. Shared study-group repos must be
private and within your sharing rules. Only the synthetic `sample/` and `examples/`
are public.

## Academic integrity

This is a study aid: retrieval practice, spaced repetition, self-testing. It is not for
graded work, take-home assessments, or anything your honor code reserves for the
student's own writing. The drafts can be wrong; the checker catches invented citations
but not every wrong claim, so lecture content stays the ground truth.

## Evidence base

The design follows retrieval practice, spacing, and interleaving research. See
[LEARNING-SCIENCE.md](LEARNING-SCIENCE.md) for the sources.

## How to pilot

1. Recruit 3 to 5 volunteer students across M1 and M2. Have each run
   `uv run scripts/doctor.py` and note setup failures.
2. Run one block (2 to 4 weeks) on one course.
3. Collect:
   - **Retention on repeat questions**: score on questions the student missed earlier
     (from Anki lapses or the weak-spot list), first versus later attempt.
   - **Objectives coverage**: share of the block's learning objectives with at least
     one verified card or question.
   - **Setup failures**: count and cause, per student.
4. Decide with the students whether to extend. Report problems or unsupported file
   formats through the issue templates, without course content.
