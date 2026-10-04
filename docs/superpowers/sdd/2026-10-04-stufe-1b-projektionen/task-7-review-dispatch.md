You are reviewing one task's implementation — Task 7 of stage 1b of "Previously": a how-to page, the last section of an explanation page, the README, the Vale vocabulary, and two small carried corrections. First whether it matches its requirements, then whether it is well-built. This is a task-scoped gate, not a merge review.

Work in the git worktree `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen` (branch `worktree-stufe-1b-projektionen`). Run every command from there; never touch the parent checkout. Your review is read-only: do not mutate the working tree, the index, HEAD, or branch state, and do not create files inside the worktree — scratch goes to `/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/`.

## What Was Requested

Read the task brief: `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/.superpowers/sdd/2026-10-04-stufe-1b-projektionen/task-7-brief.md`

Then the controller's dispatch to the implementer, which corrects the brief's warning text against the worker's measured behavior and carries two findings from earlier reviews — the implementer was bound by both: `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/.superpowers/sdd/2026-10-04-stufe-1b-projektionen/task-7-dispatch.md`

Read `CLAUDE.md` in the worktree root once. Binding here: the *Documentation* section (one Diátaxis quadrant per page, one sentence per line, sentence-case headings, American English, at most two admonitions, typed output is a measurement), "A comment is a claim" (every number on a page is measured against the tree), the six gates by name, no `Co-Authored-By`.

The `plone-doc-style:author` skill defines the quadrants the pages must sit in. The test for a how-to: action only, "This guide shows you how to …", no teaching, links instead of reasons. The test for an explanation: could be read away from the keyboard, no instruction, no fact table. The test for a reference page (`database-schema.md`, touched here): facts, no reasoning.

## What the Implementer Claims They Built

Read the implementer's report: `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/.superpowers/sdd/2026-10-04-stufe-1b-projektionen/task-7-report.md`

## Diff Under Review

**Base:** `daea417`
**Head:** `773cf4a`
**Diff file:** `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/.superpowers/sdd/2026-10-04-stufe-1b-projektionen/review-daea417..773cf4a.diff`

Read the diff file once — commit list, stat summary, full diff with context. The diff's context lines ARE the changed files; do not Read a changed file separately unless a hunk you must judge is cut off, and say so. Do not re-run git commands. Inspect code outside the diff only to evaluate a concrete risk you can name, one focused check per risk, and name both in your report.

## You Do Not Dispatch Subagents

Do all of this review yourself. Never spawn a subagent or a second reviewer.

## Do Not Trust the Report

Treat the implementer's report as unverified claims. Verify against the diff. A stated rationale never downgrades a finding.

## Tests and gates

The implementer ran the six gates and reported the outputs. Do not re-run the suite. Run a gate only on a specific doubt — `make -C docs vale` is cheap and is the right tool if you doubt a wording; `uv run pytest tests/test_docs_references.py -q` if you doubt a label. Warnings in reported output are findings.

Five specific checks:

1. **Every number on the changed pages.** The brief told the implementer to read five numbers off `tests/test_projection_worker.py` for `projections.md` (batch size, event count, `up_to_id`, chronicle rows, Hypothesis examples). Read the same test file and confirm each. The report must also give the Vale error-count sequence while adding vocabulary and the recount of lowercase entries in `.vale.ini`'s comment; check the recount with `awk 'NF && /^[a-z]/' .vale-styles/config/vocabularies/Previously/accept.txt | wc -l` against `wc -l`.
2. **The how-to's warning.** The dispatch states the measured behavior: after `DELETE FROM projection_state WHERE name = 'chronicle'` the rows of `p_chronicle` remain and the reading commands print them with a lag line on `stderr`; `project` empties the table in its first transaction and refills it in batches. The warning must say that and must not say the chronicle is empty before `project` runs. Check it against `catch_up` in `src/previously/core/projection/worker.py` (one focused look).
3. **Quadrant discipline.** No imperative in `projections.md`'s new section; no reasoning in the how-to beyond one linked pointer; `database-schema.md`'s new intro states facts only and its diagram caption says what the diagram covers.
4. **README.** "Stages 1a and 1b", the seven commands named, the three new "What it does" points, and "What it does not do" without the old "no projections" line — and nothing claimed that stage 1b does not do (no header, no project attribution, no queue).
5. **The two carried corrections.** `tests/test_schema.py` docstring names `test_the_declared_indexes_exist_in_the_migrated_database`; `database-schema.md`'s intro names all six tables in two groups. The commit message carries the sentence the dispatch asked for.

## Part 1: Spec Compliance

Missing, extra, misunderstood — against the brief's four steps and the dispatch's two carried corrections. Every file in the brief's list plus the two carried files must have its hunk. Anything you cannot verify from the diff alone: a ⚠️ item.

## Part 2: Quality

For pages: does each sit in one quadrant, is each sentence on its own line, does each heading use sentence case, do the cross-references point where the text promises. For the README: is every claim true of the tree.

## Calibration

Important: a wrong number, a wrong claim about behavior, a page in the wrong quadrant, a missed requirement. Minor: polish. Plan-mandated defects are Important, labeled so. Name what was done well, specifically, first.

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
