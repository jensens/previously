You are reviewing one task's implementation: first whether it matches its requirements, then whether it is well-built. This is a task-scoped gate, not a merge review — a broad whole-branch review happens separately after all tasks are complete.

Work in the git worktree `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen` (branch `worktree-stufe-1b-projektionen`). Run every command from there; never touch the parent checkout `/home/jensens/ws/jwk/previously`. Your review is read-only on this checkout: do not mutate the working tree, the index, HEAD, or branch state in any way, and do not create files inside the worktree — scratch goes to `/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/`.

## What Was Requested

Read the task brief: `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/.superpowers/sdd/2026-10-04-stufe-1b-projektionen/task-6-brief.md`

Then the controller's dispatch to the implementer, which resolves ambiguities in the brief and carries two findings from earlier reviews (F10 and a `since == until` assertion) — the implementer was bound by both files: `/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/task-6-dispatch.md`

Global constraints that bind this task (from the plan and `CLAUDE.md` in the worktree root, which you should read once):
- English in `src/`, `tests/`, `docs/` outside `docs/superpowers/`: code, comments, docstrings, test names, messages.
- All six gates named and run: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run lint-imports`, `uv run pytest --cov --cov-report=term-missing`, `make -C docs html && make -C docs vale && make -C docs linkcheck`. A report that names fewer is a finding.
- No `# type: ignore`; no mock for time, database or randomness; no new `# noqa` without a stated reason and an entry in `CLAUDE.md`'s suppression list (five today).
- "A comment is a claim": every number in a comment, docstring or page is measured against the code, not copied. Check each one you meet in the diff.
- Documentation: one Diátaxis quadrant per page (`docs/reference/cli.md` is reference — facts, tables, no reasoning; `docs/explanation/projections.md` is explanation — reasoning, no instruction), one sentence per line, sentence-case headings, American English, no `SQL`/`NULL`/`JSON`/`FK` in headings, at most two admonitions per page.
- `tests/test_docs_references.py` refuses a `{ref}` label that does not resolve, a bare `§`, and any citation inside a string that reaches `print`. The `stderr` lines and error messages carry no citation.
- `tests/test_docs_typed_output.py` holds every `N passed` in the tutorial against the tree: the typed test block must be retyped from a real run, without a `rootdir:` line, and the count must be 232.
- Exact output formats from the brief are contractual: the `project` line (`name` padded to 15, space, outcome), the six tab-separated `chronicle` fields, the five `stats` fields, the two `stderr` sentences, the escaping of tab/newline/carriage return/backslash as two characters each with backslash first.
- `_describe` order is a ruling (P-1): version change first, then `events == 0` → `up to date`, then `rebuilt_from == 0` → `built`, else `caught up`.
- `cli` imports nothing from SQLAlchemy; the dispatch in `main` is a table, and `ruff` must not report `C901` on `main`.

## What the Implementer Claims They Built

Read the implementer's report: `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/.superpowers/sdd/2026-10-04-stufe-1b-projektionen/task-6-report.md`

## Diff Under Review

**Base:** `71dc078`
**Head:** `a2dbe17`
**Diff file:** `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/.superpowers/sdd/2026-10-04-stufe-1b-projektionen/review-71dc078..a2dbe17.diff`

Read the diff file once — it contains the commit list, a stat summary, and the full diff with surrounding context, and it is your view of the change. The diff's context lines ARE the changed files: do not Read a changed file separately unless a hunk you must judge is cut off mid-function — and say so in your report. Do not re-run git commands. If the diff file is missing, fetch the diff yourself: `git diff --stat 71dc078..HEAD` and `git diff 71dc078..HEAD`. Do not crawl the broader codebase. Inspect code outside the diff only to evaluate a concrete risk you can name — one focused check per named risk, and name both the risk and what you checked in your report. Cross-cutting changes are legitimate named risks: `_cmd_verify` gained a parameter, so its call site in the dispatch table is one; the `log` help string changed, so `docs/reference/cli.md` agreeing with every help string is another.

## You Do Not Dispatch Subagents

Do all of this review yourself. Never spawn a subagent to review part of the diff, and never spawn another reviewer for a second opinion. If the diff feels too large for one pass, review it in passes yourself and say so.

## Do Not Trust the Report

Treat the implementer's report as unverified claims about the code. Verify the claims against the diff. Design rationales in the report are claims too; a stated rationale never downgrades a finding's severity.

## Tests

The implementer already ran the tests and reported results with RED/GREEN evidence. Do not re-run the suite to confirm their report. Run a test only when reading the code raises a specific doubt that no existing run answers — and then a focused test (`uv run pytest tests/test_cli.py -k <name> -p no:randomly -q`; needs Docker), never the package-wide suite. Warnings or noise in the reported test output are findings. Evidence you cannot see is not evidence that does not exist: if the report looks truncated, re-read it at its path before calling it a gap.

Four specific checks, because this project's failure mode is a claim that reads like competent work:

1. **The `chronicle` lag and the window.** `_cmd_chronicle` reads `tip`, `state` and the rows in one transaction and asks for `limit + 1` rows. Confirm the truncation sentence prints only when the extra row came back, and that an empty window (`since >= until`) prints neither the truncation sentence nor anything on `stdout`. Confirm the lag line is computed from the `chronicle` state row, not `source-stats`, and that `_cmd_stats` uses `source-stats`.
2. **`_describe` and F10.** The dispatch asked for one sentence on the explanation page saying that a rebuild whose first batch did not commit shows up in the next run as an ordinary catch-up. Find it; if it instead landed in code or in the reference page, that is a quadrant finding.
3. **Every number in the diff's prose**, including the tutorial's typed test block (`232 passed`, and whatever file counts appear in it — the typed block is a measurement, so the per-file counts must be plausible against the test files, not edited by hand; look for a `rootdir:` line, which must be absent) and the `cli.md` exit-code table.
4. **The `log` help string.** It said `print the chronicle`; the dispatch asked for it to change. Check the new wording and that `cli.md` says the same.

## Part 1: Spec Compliance

Compare the diff against What Was Requested: missing requirements, extras not asked for, right feature built the wrong way. The brief lists four files to modify plus the tutorial's test block; every one must have its hunk. If a requirement cannot be verified from this diff alone, report it as a ⚠️ item instead of broadening your search.

## Part 2: Code Quality

Separation of concerns, error handling, DRY without premature abstraction, edge cases; tests verify real behavior against the database, not mocks; each helper has one job; the files the task grew did not grow beyond the plan's intent. Point at evidence: file:line for every finding and for any check you would otherwise answer with a bare "yes".

## Calibration

Important means this task cannot be trusted until it is fixed: incorrect or fragile behavior, a missed requirement, a wrong number in prose, a page in the wrong quadrant. Polish is Minor. If the brief itself mandates something this rubric calls a defect, report it as Important, labeled plan-mandated. Acknowledge what was done well, specifically, before the issues.

## Output Format

Your final message is the report itself, in German (identifiers and quoted English text stay as they are): begin directly with the spec-compliance verdict. Every line is a verdict, a finding with file:line, or a check you ran — no preamble, no process narration, no closing summary.

### Spec Compliance
- ✅ Spec compliant | ❌ Issues found: [with file:line]
- ⚠️ Cannot verify from diff: [what, and what the controller should check]

### Strengths

### Issues
#### Critical (Must Fix)
#### Important (Should Fix)
#### Minor (Nice to Have)
For each: file:line, what is wrong, why it matters, how to fix if not obvious.

### Assessment
**Task quality:** [Approved | Needs fixes]
**Reasoning:** [1-2 sentences]
