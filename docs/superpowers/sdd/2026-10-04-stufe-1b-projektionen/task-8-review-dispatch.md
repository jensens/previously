You are reviewing one task's implementation — Task 8 of stage 1b of "Previously", the last task of the plan: the stage 1b specification freezes, the design-records page lists it, the README's list of frozen records grows to four, and the tutorial gains the three new commands as a typed run and is retyped last. First whether it matches its requirements, then whether it is well-built. This is a task-scoped gate; a whole-branch review follows.

Work in the git worktree `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen` (branch `worktree-stufe-1b-projektionen`). Run every command from there; never touch the parent checkout. Your review is read-only: do not mutate the working tree, the index, HEAD, or branch state, and do not create files inside the worktree — scratch goes to `/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/`.

## What Was Requested

Read the task brief: `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/.superpowers/sdd/2026-10-04-stufe-1b-projektionen/task-8-brief.md`

Then the controller's dispatch, which carries facts from the tree, three additions to the spec's open points from the Task 5 review (F9, F11, F12), two tutorial corrections, the README correction, and the rule that the test count is measured, not assumed — the implementer was bound by both: `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/.superpowers/sdd/2026-10-04-stufe-1b-projektionen/task-8-dispatch.md`

Read `CLAUDE.md` in the worktree root once. Binding here: *A specification starts in German and then freezes* (the header's wording and what freezing means), the *Documentation* section (typed output is a measurement, retyped last, never edited inside; one quadrant per page; one sentence per line), "A comment is a claim", the six gates by name, `Assisted-By:` only.

The tutorial quadrant per the `plone-doc-style:author` skill: first-person plural, imperative, "Notice that …", one guaranteed path, no explanation beyond what the next step needs.

## What the Implementer Claims They Built

Read the implementer's report: `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/.superpowers/sdd/2026-10-04-stufe-1b-projektionen/task-8-report.md` — it must contain the raw transcript of the real run the tutorial's new typed blocks came from.

## Diff Under Review

**Base:** `af5f5de`
**Head:** `fee6d2b`
**Diff file:** `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/.superpowers/sdd/2026-10-04-stufe-1b-projektionen/review-af5f5de..fee6d2b.diff`

Read the diff file once — commit list, stat summary, full diff with context. The context lines ARE the changed files; do not Read a changed file separately unless a hunk is cut off, and say so. Do not re-run git commands. Inspect code outside the diff only for a concrete named risk, one focused check each. The German spec is under review this time, because the task edits it: judge the header against the 1a spec's header (`docs/superpowers/specs/2026-10-02-stufe-1a-log.md`, lines 3 to 14) and the §10 additions against the findings as the dispatch states them.

## You Do Not Dispatch Subagents

Do all of this review yourself. Never spawn a subagent or a second reviewer.

## Do Not Trust the Report

Treat the report as unverified claims. Verify against the diff. A stated rationale never downgrades a finding.

## Tests and gates

The implementer ran the six gates and quoted the closing lines. Do not re-run the suite. One focused gate on a specific doubt is fine (`uv run pytest tests/test_docs_typed_output.py -q`, `make -C docs vale`, `make -C docs html`).

Six specific checks:

1. **The typed blocks are a measurement.** Compare every new `text`/`console` block in the tutorial against the raw transcript in the report, character by character where the report allows it. The test-run block: `collected N items`, the per-file counts and their sum, the final `N passed` line, no `rootdir:` line, no machine path. Measure N yourself: `uv run pytest --collect-only -q -p no:randomly | tail -1`. If the report's transcript is missing or does not match the page, that is Important: the page then carries numbers nobody measured.
2. **The spec header and status.** The quoted header matches the 1a spec's wording except for the date; `Status: eingefroren`; the paragraph beginning "Dieser Spec entsteht auf Deutsch" is gone; the 1a spec is untouched (no hunk).
3. **§10.** The introduction speaks of a frozen document; the seven original points are intact and the anchor is first; the three additions say what the dispatch states — F11 (no lock on the `projection_state` row; two concurrent runs; belongs with the queue; `SELECT … FOR UPDATE` or an advisory lock), F9 (`Projection.write` could open its own transaction, the contract lives in the docstring), F12 (`version` without `CHECK (version > 0)`; `rebuilt_from == 0` means "nothing existed") — and nothing is claimed beyond that. The labels F9/F11/F12 are this plan's review labels; the text must say so, or the reader lands in the wrong numbering space (`CLAUDE.md`, *How review findings are cited*).
4. **`design-records.md`.** The 1b spec is introduced where the others are, with date and the pages that carry its reasoning; the sentence about "no line of stage 1b code cites a paragraph of this spec" is there and is true — run the brief's grep yourself (`grep -rn "§" src/previously/core/projection src/previously/contract/store.py src/previously/contract/rows.py`): the controller measured exactly one hit, citing the architecture with `(frozen design record)` on the line. No link to `docs/superpowers/sdd/2026-10-04-stufe-1b-projektionen/` (the directory does not exist yet).
5. **The tutorial's two corrections and the new sections.** Introduction names what the tutorial now does; the heading over `previously log` no longer says "chronicle"; three new sections between `## Look at the event in full` and `## Run the test suite`; "Notice that …" sentences true of the transcript; `## Next steps` consistent.
6. **README.** Four frozen records listed, the 1b spec with its date and pages; nothing else in the README changed.

## Part 1: Spec Compliance

Missing, extra, misunderstood — against the brief's three steps and the dispatch's additions. Four files must have their hunks: the spec, `design-records.md`, the tutorial, `README.md`. Anything you cannot verify from the diff alone: a ⚠️ item.

## Part 2: Quality

The German of the spec additions is in the spec's register (you can judge it: the rest of §10 is the model). The tutorial reads as one path a newcomer completes. One sentence per line, sentence-case headings, no acronym headings.

## Calibration

Important: a typed number that does not match the transcript or the tree, a wrong claim in §10, a missed hunk, a wrong quadrant. Minor: polish. Name what was done well, specifically, first.

## Output Format

Your final message is the report itself, in German (identifiers and quoted English stay as they are), beginning directly with the spec-compliance verdict. Every line a verdict, a finding with file:line, or a check you ran.

### Spec Compliance
- ✅ | ❌ with file:line
- ⚠️ Cannot verify from diff

### Strengths

### Issues
#### Critical (Must Fix)
#### Important (Should Fix)
#### Minor (Nice to Have)

### Assessment
**Task quality:** [Approved | Needs fixes]
**Reasoning:** [1-2 sentences]
