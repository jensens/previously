You are implementing Task 7 of stage 1b of "Previously": the how-to `Rebuild a projection`, the last section of the explanation page `projections.md`, the README, and the Vale vocabulary.

## Where this fits

Previously is an append-only event log for project histories (Python 3.13, SQLAlchemy Core, PostgreSQL, AGPL). Stage 1b adds *projections*: derived, disposable tables rebuilt from the log. Tasks 1 to 6 are on the branch: protocols, schema, storage, the two derivations, the worker `catch_up`, and the commands `project`, `chronicle`, `stats` with their reference page. Your task is documentation only, apart from one docstring word in a test. Task 8 (freezing the spec, design records, tutorial) comes after you.

## Task Description

Read your task brief first — it is your requirements, with the exact section titles, the label, the commit message:
`/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/.superpowers/sdd/2026-10-04-stufe-1b-projektionen/task-7-brief.md`

The brief is in German; everything you write under `docs/` (outside `docs/superpowers/`), in `README.md` and in `tests/` is English. Read `CLAUDE.md` in the worktree root once before you start — it is binding, in particular the section *Documentation* (one Diátaxis quadrant per page, one sentence per line, sentence-case headings, American English, typed output is a measurement), "A comment is a claim" (every number in prose measured against the tree), the six gates by name, `Assisted-By:` trailer and never `Co-Authored-By`.

Then invoke the skill `plone-doc-style:author` (exactly that name) for the how-to quadrant before writing the how-to, and for the explanation quadrant before touching `projections.md`. A how-to is action without explanation; an explanation is reasoning without instruction.

Work from: `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen` (branch `worktree-stufe-1b-projektionen`). Never touch the parent checkout.

## Facts from the tree the brief could not know

- The worker (`src/previously/core/projection/worker.py`, `catch_up`) handles a missing state row and a version mismatch in the same branch: it **truncates the projection table and writes a fresh state row at `up_to_id 0`** in one transaction, then catches up in batches. So `DELETE FROM projection_state WHERE name = 'chronicle'` followed by `previously project` really does print `built: …`, as the brief says.
- **But the brief's `:::{warning}` text is not accurate as written** ("until the next `project` the chronicle is empty"). Deleting the state row leaves the rows of `p_chronicle` in place. What is true, in order: after the `DELETE` and before the next `project`, `chronicle` and `stats` print the old rows and report the whole log as lag on `stderr` (`projection is N events behind; run \`previously project\``); `project` then empties the table in its first transaction and refills it batch by batch, so a `chronicle` run during a long rebuild sees a partial chronicle, with the lag line saying so. Write the warning from that. Keep it to a few lines.
- `escape_field`, `_lag_line`, the `stderr` wording for lag and truncation, and the `project` output lines (`built: …`, `caught up: …`, `rebuilt: version N -> M, …`, `up to date, up_to_id N`) are in `src/previously/cli.py` and documented in `docs/reference/cli.md` (Task 6). Quote them from there, not from memory; the how-to shows output only where the brief asks for it.
- The labels the brief cites exist: `(add-a-migration)=` in `docs/how-to/add-a-migration.md`, `(tombstone-seam)=` in `docs/explanation/hash-chain.md`, `(projections)=` at the top of `docs/explanation/projections.md`. The how-to toctree is in `docs/how-to/index.md`: `verify-the-chain`, `restore-from-a-backup`, `add-a-migration` — add `rebuild-a-projection` after them.
- The numbers the brief tells you to read off the tests for `projections.md`: batch size 2 in the abort test; ten events; `up_to_id 4`; 8 chronicle rows; 25 Hypothesis examples. Read them in `tests/test_projection_worker.py`, do not trust this list — and the page already carries measured mutation counts ("leaves the other ten green" and the like) from Task 5's fix round; leave those as they are unless you re-measure.
- Vocabulary baseline measured before your task: `.vale-styles/config/vocabularies/Previously/accept.txt` has 15 entries, 11 of them lowercase; the comment in `.vale.ini` says "Eleven of the fifteen entries are lowercase". If you add words, recount both numbers with the `awk` from the brief and update the comment. That comment also tells a story about "task 6" — that is task 6 of the documentation plan of 2026-10-03, not of this plan; do not rewrite it, only the two numbers if they change. `make -C docs vale` currently reports 21 files; your how-to makes it 22.

## Two findings carried from earlier task reviews — yours to close

1. **`docs/reference/database-schema.md`, line 5 and the diagram.** The intro says "Previously stores every event in three PostgreSQL tables" and the `erDiagram` shows three, while the page documents six since Task 2 (`projection_state`, `p_chronicle`, `p_source_stats` have their own sections below). Ruling: the intro names all six, in two groups — three hold the log (`event`, `unit`, `source_key`), three hold projections, derived from the log and disposable, with `{ref}`projections`` for the why. The diagram stays the log's three tables, and its caption says so explicitly ("The three tables of the log; the projection tables are described below" or words to that effect). Do not redraw the diagram.
2. **`tests/test_schema.py`, line 351.** The docstring cites `test_the_declared_indexes_exist`; the real test is named `test_the_declared_indexes_exist_in_the_migrated_database` (line 256). Fix the name. Add one sentence to the brief's commit message for it, after the vocabulary paragraph: "A test docstring cited a neighbor by a name it does not have; it now cites the real one."

Do **not** touch `docs/explanation/module-boundaries.md` — its open minors (length, one antecedent) wait for the final review.

## Documentation gates

`make -C docs html` treats warnings as errors (a page missing from a toctree is a warning). `make -C docs vale` enforces American English, the Microsoft style and the vocabulary; `Microsoft.We` is off only under `docs/tutorials/`, so the how-to and the explanation use "you", never "we". `Microsoft.HeadingAcronyms`: no `SQL`, `NULL`, `FK` in a heading. At most two admonitions on a page. `make -C docs linkcheck` resolves every link. `tests/test_docs_references.py` checks every `{ref}` in `src/` and `tests/` against labels under `docs/` — you add none in code.

## Your job

1. The how-to (brief step 1), then `projections.md` (step 2), then the README (step 3), then the two carried findings above.
2. Vocabulary (step 4): measure with `make -C docs vale`, add one word at a time, re-measure each time, and write the sequence of error counts into your report.
3. All six gates, each run separately, each output quoted in the report:
   ```
   uv run ruff check .
   uv run ruff format --check .
   uv run pyright
   uv run lint-imports
   uv run pytest --cov --cov-report=term-missing
   make -C docs html && make -C docs vale && make -C docs linkcheck
   ```
   Expected `pytest`: **232 passed**, unchanged. If the number differs, count what changed and say so.
4. Commit hygiene: before `git add`, run `git status --short` and add only the files you changed: `docs/how-to/rebuild-a-projection.md`, `docs/how-to/index.md`, `docs/explanation/projections.md`, `docs/reference/database-schema.md`, `README.md`, `tests/test_schema.py`, and `.vale-styles/config/vocabularies/Previously/accept.txt` plus `.vale.ini` if the vocabulary changed. Anything else that shows up modified: do not add it, report it. Trailer `Assisted-By: Claude Opus 5 <noreply@anthropic.com>`.
5. Self-review your diff — read the how-to once as an operator who has never seen the project, and the explanation section once as a reader in the bath — then report.

## You do not dispatch subagents

Do all of this task's work yourself. Never spawn a subagent to write a page, and never spawn a reviewer to check your work; the controller dispatches a fresh reviewer against your diff after you report.

## When you are in over your head

It is always OK to stop and say so. Report `BLOCKED` or `NEEDS_CONTEXT` with what you are stuck on and what would unblock you.

## Report

Write the full report to:
`/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/.superpowers/sdd/2026-10-04-stufe-1b-projektionen/task-7-report.md`

It contains: what you wrote, section by section; every number on the pages and where in the tests you read it; the Vale error-count sequence while adding vocabulary; the six gate outputs; files changed; every place you deviated from the brief or from this dispatch and why; concerns.

Then reply with ONLY (under 15 lines):
- **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
- Commit (short SHA + subject)
- One-line gate summary (pytest count, Vale file count and errors)
- Your concerns and disagreements, one line each
- The report file path

If the task review finds issues, you will be resumed with the findings. Fix them, re-run the covering gates, append a fix report to the same report file, and reply with the same short contract.
