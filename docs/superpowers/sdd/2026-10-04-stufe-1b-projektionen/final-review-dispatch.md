You are the final whole-branch reviewer for stage 1b of "Previously": projections. Eight tasks were implemented one at a time, each with its own task review and fix rounds; this review looks at the branch as a whole — what the task reviews, each scoped to one diff, could not see: seams between tasks, claims that drifted while later tasks moved on, the shape of the result against the specification.

Work in the git worktree `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen` (branch `worktree-stufe-1b-projektionen`). Run every command from there; never touch the parent checkout `/home/jensens/ws/jwk/previously`. Your review is read-only: do not mutate the working tree, the index, HEAD, or branch state in any way, and do not create files inside the worktree — scratch goes to `/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/`.

## What was implemented

Previously is an append-only event log for project histories (Python 3.13, SQLAlchemy Core, PostgreSQL 17 via testcontainers in tests, AGPL). Stage 1a built the log: hash chain, `append`, `log`, `verify`, `show`. Stage 1b, this branch, adds projections — derived, disposable tables rebuilt from the log:

- `previously.contract.store`: `LogStore[Conn]` and `ProjectionStore[Conn]` protocols (PEP 695 generics); `previously.contract.rows`: the row types. `core` depends on the protocols, `storage` implements them; two import-linter exemptions that existed before are gone.
- Schema and migration `0002_projections`: `projection_state`, `p_chronicle` (one row per unit, with source attribution, indexed by `occurred_at`), `p_source_stats` (per source: events, units, first and last `occurred_at`).
- `previously.core.projection`: the worker `catch_up` (batched; rows and `up_to_id` move in one transaction; version `!=` triggers a rebuild; a contiguity check refuses a gap), two projections (`chronicle`, `source-stats`) with pure `derive`/`merge` functions.
- Commands `project`, `chronicle` (time order, half-open window, escaping, lag and truncation on `stderr`), `stats`.
- Documentation in the same branch: `docs/explanation/projections.md`, `module-boundaries.md` rewritten, `docs/reference/cli.md` and `database-schema.md` extended, a how-to `rebuild-a-projection.md`, the tutorial extended and retyped, `design-records.md` listing the frozen 1b spec, README.

## Requirements

- The specification (German, frozen in the last commit): `docs/superpowers/specs/2026-10-04-stufe-1b-projektionen.md`. It is the authority the plan argued from; §9 is the acceptance table; §10 lists what was deliberately left open. Read §1, §4, §5, §6, §9 and §10 in full.
- The plan: `docs/superpowers/plans/2026-10-04-stufe-1b-projektionen.md` (German, long). Read only its `## Global Constraints` and `## Review Focus` sections (lines 22 to 58) and skim the task headings; the plan's amendments and corrections during execution are marked with dated `> **Nachtrag` / `> **Korrektur` blocks — you do not need them.
- The project's working agreements: `CLAUDE.md` in the worktree root. Read it once in full. The parts that bite here: the six gates by name; "A comment is a claim" (every number in prose is measured, not copied); "An assurance needs a test measured to fail"; the suppression list is complete at five; one Diátaxis quadrant per page; typed output is a measurement; `{ref}` labels in code comments are checked by `tests/test_docs_references.py`; `Assisted-By:` and never `Co-Authored-By`.
- The ledger of this execution, with every ruling the controller made: `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/.superpowers/sdd/2026-10-04-stufe-1b-projektionen/progress.md`. Read the section `## Rueckstandsliste (Stand vor der Endpruefung, nach Aufgabe 8)` — the last section with that heading; an earlier one with the same heading is superseded — it lists the findings the task reviews deferred to you, numbered, with what is already done — and the `Ruling` lines (grep `Ruling [PT]`). Everything else in it is history you may consult when a decision puzzles you.

## Git range

**Base:** `cdc508a` (main before this branch)
**Head:** `4c52091`

Two review packages, so you do not read the German design records as a diff:

- Code and configuration: `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/.superpowers/sdd/2026-10-04-stufe-1b-projektionen/final-review-code-cdc508a..4c52091.diff` — `src/`, `tests/`, `migrations/`, `pyproject.toml`, `.importlinter`.
- English documentation: `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/.superpowers/sdd/2026-10-04-stufe-1b-projektionen/final-review-docs-cdc508a..4c52091.diff` — `docs/` without `docs/superpowers/`, `README.md`, `CLAUDE.md`, `.vale.ini`, `.vale-styles/`.

Each contains the commit list, a stat summary and the full diff with context. Read both. Context lines are the changed files; where a hunk you must judge is cut off, read the file at HEAD and say so. You may run `git log --oneline cdc508a..HEAD` and `git show <sha> --stat`; do not rebuild the diffs.

## The spec is a vision document

The spec says what the software must do. It does not enumerate every input, environment, or condition the software will meet. For behavior the spec is silent on, judge by what a reasonable person operating this software would expect: a reasonable person's expectation is a requirement, and a spec's silence is not permission. Grade such findings by their effect on that person, not by whether the spec mentions the trigger.

## Declined to judge

Before your verdict, list every behavior you considered and set aside as outside the plan or spec, one line each, with the reason. The controller rules on each line; nothing you set aside is dropped silently. An empty list means you set nothing aside.

## You do not dispatch subagents

Do all of this review yourself. Never spawn a subagent to review part of the diff, and never spawn another reviewer for a second opinion. This process already provides every review seat the work gets. If the diff feels too large for one pass, review it in passes yourself and say so in your report.

## Tests and gates

The implementers ran the six gates after every task and the controller recorded the closing lines. Run the cheap ones yourself once on HEAD — `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run lint-imports` — and `uv run pytest --collect-only -q -p no:randomly | tail -1` for the count. Run the full `pytest --cov` once if you have Docker and time (it takes under a minute); run `make -C docs html && make -C docs vale` once. Do not run `linkcheck` (network). A gate you did not run is a gate you report as not run.

## What to check

**Seams between tasks** — the thing per-task reviews cannot see:
- Does `cli.py` use the protocols and the worker exactly as `core.projection` exposes them, and do `cli.md`'s promises match what `_describe`, `_lag_line`, `escape_field` and the two read functions do?
- Does `projections.md` describe the worker that exists after the Task 5 fix round (contiguity check, `batch_size` guard), the commands that exist after Task 6's fix round (`--limit` guard), and the how-to's rebuild paths?
- Does `module-boundaries.md` describe the import graph the `.importlinter` contracts enforce, and does `test_the_exempted_core_modules_load_no_sql_at_runtime` no longer exist (it was deleted with the exemptions)?
- Does the tutorial's typed run agree with the commands as shipped (output formats, counts)?
- Does the frozen spec's §10 list what the ledger's deferred items say was left open, and does `design-records.md` list the 1b record consistently with the README?

**Claims** — every number and every assertion in a comment, docstring or page the branch added or touched. Spot-check at least ten, choosing the ones a wrong value would hurt most, and say which ones you checked and how.

**Assurances** — the spec's §5 promises three layers (pure `merge` tests; the pinned `first_seen` assertion inside `test_incremental_equals_rebuilt`; the incremental-equals-rebuilt comparison). The ledger records which mutation each layer catches. Judge whether the tests as written match that description; you may run one mutation yourself if a doubt is specific (restore the file afterwards with `git checkout -- <file>` — that is the one write to the tree you are allowed, and only to undo your own).

**Architecture** — the layering (`cli > core > storage > contract`, `core` is clean of SQL), the generics on the protocols, the worker's transaction boundaries, the error hierarchy (`PreviouslyError` in core, `StorageError` in storage, and the one deliberate `ValueError` for `batch_size < 1` — ruling T5-f in the ledger), the schema (keys, indexes, nullability).

**Code quality, tests, production readiness** per the usual rubric: separation of concerns, error handling, DRY without premature abstraction, edge cases; tests against the real database and no mocks; migrations; documentation complete and in the right quadrant.

**The deferred list** — for each item in `## Rueckstandsliste` that has no owner among Tasks 7 and 8, say whether it should be fixed before merge, fixed later, or dropped, and why. Items already marked as Task 7's or Task 8's: confirm they were done.

## Calibration

Categorize by actual severity. Critical: wrong data, lost data, a gate that lies. Important: incorrect or fragile behavior, a missed requirement, a wrong claim in prose, a page in the wrong quadrant, maintainability damage you would block a merge over. Minor: polish. Acknowledge what was done well, specifically, before the issues. If you find deviations from the plan, name them and say whether the ledger's ruling on them holds up. If you find issues with the spec or plan itself rather than the implementation, say so.

## Output format

Your final message is the report itself, in German (identifiers and quoted English stay as they are). Begin directly with the first strength. Every line is a finding with file:line, a check you ran with its result, or a verdict.

### Strengths

### Gates run
One line per gate you ran, with its closing line; one line per gate you did not run.

### Issues
#### Critical (Must Fix)
#### Important (Should Fix)
#### Minor (Nice to Have)
For each: file:line, what is wrong, why it matters, how to fix if not obvious.

### Deferred items
One line per item of the `Rueckstandsliste`: fix before merge | fix later | drop — and why.

### Declined to judge

### Recommendations

### Assessment
**Ready to merge?** [Yes | No | With fixes]
**Reasoning:** [2-3 sentences]
