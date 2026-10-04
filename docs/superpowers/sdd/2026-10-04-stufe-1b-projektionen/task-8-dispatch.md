You are implementing Task 8 of stage 1b of "Previously", the last task of the plan: the stage 1b specification freezes, the design-records page lists it, and the tutorial gains the three new commands as a typed run and is retyped last.

## Where this fits

Previously is an append-only event log for project histories (Python 3.13, SQLAlchemy Core, PostgreSQL, AGPL). Stage 1b added projections: derived, disposable tables rebuilt from the log, with the commands `project`, `chronicle`, `stats`. Tasks 1 to 7 are on the branch and the explanation pages stand (`docs/explanation/projections.md`, `module-boundaries.md`), which is the condition under which a German specification freezes. After you, the controller runs the final whole-branch review, a fix wave, and ships this plan's execution record.

## Task Description

Read your task brief first — it is your requirements, with the exact header text, the grep, the section titles, the commit message:
`/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/.superpowers/sdd/2026-10-04-stufe-1b-projektionen/task-8-brief.md`

Read `CLAUDE.md` in the worktree root once — binding here: *A specification starts in German and then freezes* (the spec and its header stay German; you edit a German document for the only time in this plan), the *Documentation* section (typed output is a measurement with a date; retype it last, from a real run, never edit a number inside it), the six gates by name, `Assisted-By:` and never `Co-Authored-By`. Then invoke the skill `plone-doc-style:author` (exactly that name) for the tutorial quadrant before touching the tutorial: first-person plural, imperative, "Notice that …", one guaranteed path, no explanation.

Work from: `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen` (branch `worktree-stufe-1b-projektionen`). Never touch the parent checkout.

## Facts from the tree the brief could not know

- **The spec's head today** (`docs/superpowers/specs/2026-10-04-stufe-1b-projektionen.md`, lines 1 to 9): title, then `Stand: 2026-10-04 · Status: Entwurf, zur Abnahme`, then a paragraph beginning "Dieser Spec entsteht auf Deutsch …" and ending "… Bis dahin ist er das maßgebliche Dokument für 1b." The brief's header block goes between the title and the `Stand:` line; the status becomes `Status: eingefroren`; that paragraph is deleted. The freeze date in the header is the date of your commit, 2026-10-04. The 1a spec you copy the header from still carries `Status: zur Abnahme` under its own frozen header — that is a frozen record and stays as it is; do not touch it.
- **§10 "Was offen bleibt"** has seven numbered points, the external anchor first. Its introduction speaks in the present tense ("ist gepflegt, nicht eingefroren, solange der Spec lebt"). Rewrite that introduction for a frozen document: the section was maintained while the spec lived; with the freeze it loses its maintenance, and what is still open belongs in the next stage's spec, the anchor first. Keep the seven points. Then add, from the Task 5 review (findings F9, F11, F12). Cite them by those labels, but say whose labels they are in the same sentence — "Prüfbefunde F9, F11 und F12 aus der Prüfung von Aufgabe 5 dieses Plans" or the like — because `CLAUDE.md` (*How review findings are cited*) describes two older numbering spaces (`W2`, `G-7` and the like) and a bare letter-number label would land a reader there. The ledger that ships with this plan (`docs/superpowers/sdd/2026-10-04-stufe-1b-projektionen/progress.md`, after the final review) is where they resolve; name that path in the spec as the place to look, as a path in prose, not as a link.
  - **F11, a new point 8:** `catch_up` takes no lock on the `projection_state` row. Two concurrent runs for the same projection can both pass the version check and both write; today nothing can start two, because the worker is a command and there is no queue (point 4). The lock belongs with the queue: `SELECT … FOR UPDATE` on the state row, or an advisory lock per projection.
  - **F9 and F12, as two notes under point 8 or as a point 9:** `Projection.write` receives the caller's connection and could open its own transaction through `store.begin()`; nothing in the types prevents it, the contract lives in the docstring. And `projection_state.version` has no `CHECK (version > 0)`; the worker reads `rebuilt_from == 0` as "nothing existed", so a version 0 in the table would be reported as a first build.
  Write these in the spec's German, in its register.
- **`design-records.md`** (`docs/explanation/design-records.md`): the table `| Paragraph | Document | Where the reasoning lives now |` lists cited paragraphs of the frozen records with their pages. The frozen records are introduced above it. Add the 1b spec where the others are introduced (date 2026-10-04, topic projections, the pages that carry its reasoning: `{ref}`projections``, `{ref}`module-boundaries``; the reference pages `{ref}`database-schema`` and `{ref}`cli-reference`` took its facts). For the table, the one new thing: stage 1b code cites no paragraph of the 1b spec — measured before your task with the brief's grep over `src/previously/core/projection`, `src/previously/contract/store.py`, `src/previously/contract/rows.py`: exactly **one** `§` in those modules, citing the architecture with `(frozen design record)` on the same line; zero cite the 1b spec. Re-run the grep, put the count in the report, and write the sentence the brief asks for: the first stage whose code never pointed at its spec, because the pages were written alongside the code and `test_no_bare_paragraph_references_remain` in `tests/test_docs_references.py` refuses a bare paragraph sign. Do not link to `docs/superpowers/sdd/2026-10-04-stufe-1b-projektionen/` from this page: that directory does not exist yet (the controller ships it after the final review), and `make -C docs html` treats a dangling link as an error.
- **The tutorial** (`docs/tutorials/record-your-first-event.md`) has two places that became wrong when `chronicle` became a command of its own in Task 6, both yours to fix because you own the tutorial: the introduction (line 5, "look at the chronicle it produces") and the heading `## Look at the chronicle` (line 80), which sits over `previously log`. `log` prints the log in chain order (`cli.md` has the wording); `chronicle` is now the chronology. Rename the heading to match what the section runs (for example `## Look at the log`), fix the introduction so it names what the tutorial now does — record, look at the log, check the chain, build the derived views, read the chronicle, count per source, run the tests — and check `## Next steps` for anything that names the old meaning.
- **The three new sections** go after `## Look at the event in full` and before `## Run the test suite`, as the brief specifies. Their output blocks are **typed from a real run** against the container the tutorial itself sets up (follow the tutorial's own steps from a clean container: schema, one `append`, then `project`, `chronicle`, `stats`). The brief predicts two `built: 1 event, up_to_id 1` lines, two chronicle lines, one stats line; type what you see, and if it differs from the prediction, say so in the report and write the tutorial's "Notice that …" from what is true. The `project` second run (`up to date`) is part of the brief's narrative — run it, type it.
- **The README** (`README.md`, around lines 58 to 70) says "The three specifications below are frozen design records" and lists three. Your commit freezes a fourth. The sentence and its table have to follow in the same commit: four records, the 1b spec with its date and the pages that carry its reasoning. The Task 7 reviewer caught this; the brief does not list the README, you stage it all the same.
- **The test count**: measure it, do not assume 232. `uv run pytest --collect-only -q -p no:randomly | tail -1` before the retype. Task 7 was not supposed to change it; if it did, the number in the plan is stale, not the tree. Retype the whole test-run block from a real `uv run pytest` run, without the `rootdir:` line and without a machine path, as the block's trailing note says. `tests/test_docs_typed_output.py` holds every `N passed` in the page against the tree.

## Documentation gates

`make -C docs html` treats warnings as errors. `make -C docs vale`: the tutorial may use "we" (`Microsoft.We` is off under `docs/tutorials/`), headings in sentence case, no `SQL`/`NULL`/`JSON`/`FK` in headings, at most two admonitions on the page; the spec under `docs/superpowers/` is outside both the Sphinx build and Vale. `make -C docs linkcheck` resolves every link. `tests/test_docs_references.py` checks `{ref}` labels in `src/` and `tests/`; you add none in code.

## Your job

1. The spec (brief step 1, with §10 as above), then `design-records.md` (step 2, with the grep count in the report), then the tutorial (step 3): the two corrections, the three typed sections, and the test-run block last.
2. All six gates, each run separately, each closing line quoted in full in the report:
   ```
   uv run ruff check .
   uv run ruff format --check .
   uv run pyright
   uv run lint-imports
   uv run pytest --cov --cov-report=term-missing
   make -C docs html && make -C docs vale && make -C docs linkcheck
   ```
3. Commit hygiene: `git status --short` before `git add`; stage only `docs/superpowers/specs/2026-10-04-stufe-1b-projektionen.md`, `docs/explanation/design-records.md`, `docs/tutorials/record-your-first-event.md`, `README.md`. Anything else modified: do not add it, report it. The brief's commit message, with the count you measured in place of 232 if it differs, and the trailer `Assisted-By: Claude Opus 5 <noreply@anthropic.com>`.
4. Self-review: read the tutorial once end to end as a newcomer who has never seen the project, checking that every typed block is something they will see; read §10 once as the maintainer of the next stage, checking that each point says what to do, not only what is wrong. Then report.

## You do not dispatch subagents

Do all of this task's work yourself. Never spawn a subagent to write a section, and never spawn a reviewer; the controller dispatches a fresh reviewer against your diff after you report.

## When you are in over your head

It is always OK to stop and say so. Report `BLOCKED` or `NEEDS_CONTEXT` with what you are stuck on and what would unblock you. If the tutorial's container steps do not work for you (Docker, ports), that is a `BLOCKED`, not a reason to type output from memory.

## Report

Write the full report to:
`/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/.superpowers/sdd/2026-10-04-stufe-1b-projektionen/task-8-report.md`

It contains: the spec changes section by section; the grep output and count; the design-records entry; the tutorial changes, with the real-run transcript the typed blocks came from (commands and raw output, so the reviewer can compare); the measured test count and the retype; the six closing lines; files changed; every deviation from the brief or this dispatch and why; concerns.

Then reply with ONLY (under 15 lines):
- **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
- Commit (short SHA + subject)
- One-line gate summary (pytest count, Vale file count and errors)
- Your concerns and disagreements, one line each
- The report file path

If the task review finds issues, you will be resumed with the findings. Fix them, re-run the covering gates, append a fix report to the same report file, and reply with the same short contract.
