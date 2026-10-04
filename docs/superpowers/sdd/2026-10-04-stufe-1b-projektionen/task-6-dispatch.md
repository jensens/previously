You are implementing Task 6 of stage 1b of "Previously": the three commands `project`, `chronicle` and `stats`.

## Where this fits

Previously is an append-only event log for project histories (Python 3.13, SQLAlchemy Core, PostgreSQL, AGPL). Stage 1b adds *projections*: derived, disposable tables rebuilt from the log. Tasks 1 to 5 are on the branch: the `LogStore`/`ProjectionStore` protocols, the schema, the storage implementation, the two pure derivations, and the worker `catch_up`. Your task gives the user access to all of that from the command line, and documents it. Tasks 7 and 8 (how-to, README, freezing the spec, tutorial) come after you.

## Task Description

Read your task brief first — it is your requirements, with the exact values to use verbatim (test code, output formats, help strings, the commit message):
`/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/.superpowers/sdd/2026-10-04-stufe-1b-projektionen/task-6-brief.md`

The brief is in German; everything you write into `src/`, `tests/`, `docs/` (outside `docs/superpowers/`) is English. Read `CLAUDE.md` in the worktree root once before you start — it is binding, in particular: the six gates by name, no `# type: ignore`, no mocks, no `# noqa` without a reason beside it (and the suppression list in CLAUDE.md has to be kept complete), "A comment is a claim" (every number in prose must be measured), one sentence per line in docs, American English (Vale enforces it), `Assisted-By:` trailer, never `Co-Authored-By`.

Work from: `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen` (branch `worktree-stufe-1b-projektionen`). Never touch the parent checkout.

## Interfaces from earlier tasks, checked against the tree

The brief's Interfaces block was written before Tasks 3 and 5 landed. These are the real names and signatures; where the brief differs, the tree wins.

- `from previously.core.projection import PROJECTIONS, catch_up, Outcome` — `PROJECTIONS: tuple[Projection, ...] = (CHRONICLE, SOURCE_STATS)`, chronicle first, which is the order the `project` tests expect. `catch_up(log, store, projection, *, batch_size=500) -> Outcome`; `PostgresStorage` is both the `log` and the `store`: `catch_up(storage, storage, projection)`.
- `Outcome` is a frozen dataclass with fields in this order: `name: str`, `version: int`, `rebuilt_from: int | None`, `events: int`, `up_to_id: int`. `rebuilt_from` means: `None` ordinary catch-up, `0` nothing existed before (first build), `n > 0` the table was at version `n` and was rebuilt.
- `PostgresStorage` (in `previously.storage.postgres`): `begin()` context manager yielding a connection; `tip(conn) -> Tip | None` (`Tip.id`, `Tip.hash`); `projection_state(conn, name) -> ProjectionState | None` (`up_to_id`, `version`, `built_at`); `read_chronicle(conn, *, since: datetime | None, until: datetime | None, limit: int) -> list[ChronicleRow]` ordered by `(occurred_at, event_id, seq)`, `since` inclusive, `until` exclusive; `read_source_stats(conn) -> list[SourceStatsRow]` ordered by `source`.
- `ChronicleRow` fields: `event_id, seq, content, occurred_at, kind, evidence, source, external_id, speaker, start_ms, end_ms` — `source` and `external_id` are `str | None`. `SourceStatsRow` fields: `source, events, units, first_seen, last_seen, last_event_id`. `occurred_at`, `first_seen`, `last_seen` are tz-aware datetimes; `.isoformat()` gives `2026-10-01T09:00:00+00:00`, which is what the tests expect.
- `parse_moment(text) -> datetime` in `previously.cli` already exists and is what `--occurred-at` uses; it raises `InvalidPayload` (a `PreviouslyError`) on a naive timestamp. Check that its message contains the words "time zone" — the test `test_chronicle_rejects_a_naive_since` asserts that substring on stderr and exit code 2, which `main`'s `except (PreviouslyError, StorageError)` produces.
- `_cmd_verify()` currently takes no parameter; the brief tells you to give it `_args: argparse.Namespace` so every command function shares one signature for the dispatch table.
- `tests/test_cli.py` already imports `main`, `MAX_TEXT_BYTES`, `parse_moment` from `previously.cli` at the top, one name per line, sorted — ruff's isort config uses `force-single-line`. Put `from previously.cli import escape_field` there, in sorted position, not in the middle of the file where the brief shows it. Look at how the existing `db` tests in that file obtain the `Engine` and set `PREVIOUSLY_DSN`, and follow the pattern that is already there rather than the brief's `_setup` if the two differ.

## Resolutions of things the brief leaves ambiguous

1. **`escape_field`, not `_escape`.** The brief's Interfaces block says `_escape`; its test and its prose say `escape_field`, and the prose gives the reason (CLAUDE.md: a function a test imports gets a public name). `escape_field` it is. `_plural`, `_describe`, `_lag_line` stay private — no test imports them; they are exercised through `main`.
2. **`_lag_line`, not `_report_lag`.** The brief first writes `_report_lag` with an `isinstance(conn, Connection)` detour and then corrects itself ("Halt"). Implement the correction only: `_lag_line(tip_id, up_to_id) -> str | None`, and each command reads `tip` and `state` inside its own transaction, as the `_cmd_chronicle`/`_cmd_stats` code in the brief shows. `cli` imports nothing from SQLAlchemy.
3. **`_describe` order is a ruling (P-1 in the ledger), not a suggestion:** version change first (reported even with zero events, because it changed the state row), then `events == 0` → `up to date`, then `rebuilt_from == 0` → `built`, else `caught up`. The brief's code has exactly that order; keep it.
4. **One finding from the Task 5 review is yours to answer (ledger F10):** if a `catch_up` run is interrupted after the version check rewrote the state row but before its first batch committed, the next run finds the state row already at the new version and reports `caught up`, not `rebuilt` — the `rebuilt_from` is lost with the aborted process. `_describe` cannot know this. Say it in one sentence where the page talks about what the commands do not know (the brief's `## Saying what it doesn't know` section of `docs/explanation/projections.md`): the path `project` reports is the path *this* run took, and a rebuild whose first batch did not commit shows up in the next run as an ordinary catch-up. Do not try to fix it in the worker; it is recorded as a known limit.
5. **One assertion carried from the Task 3 review:** the window test `test_chronicle_window_is_half_open_and_an_empty_window_is_not_truncated` checks `since > until`; add the `since == until` case as one more call in the same test — same instant for both, expect exit 0 and `(out, err) == ("", "")`. That is one assertion, not a new test; the count stays nine.
6. **`Outcome`'s docstring** in `worker.py` cites `{ref}`projections`` for "the command line to say which path it took". Your `## Two orders, two commands` / `## Saying what it doesn't know` sections make that citation land. Do not edit `worker.py`.
7. **Help strings:** the brief's `log` parser already says `help="print the chronicle"` in the current `cli.py` — that was written before `chronicle` existed and is now wrong. Change it to `help="print the log in chain order"` (or the equivalent in one line) in the same commit, and mention it in the report. `cli.md` must agree with every help string.
8. **Commit hygiene.** Before `git add`, run `git status --short` and add only the files you changed: `src/previously/cli.py`, `tests/test_cli.py`, `docs/reference/cli.md`, `docs/explanation/projections.md`, `docs/tutorials/record-your-first-event.md`. If anything else shows up as modified, do not add it — report it.

## Test count and the tutorial

Nine new tests → `pytest` **232 passed** (223 + 9). `tests/test_docs_typed_output.py` holds the number in `docs/tutorials/record-your-first-event.md` against the tree, so the test-run block in the tutorial has to be retyped from a real `uv run pytest` run, without the `rootdir:` line (the page says so at the end of the block) and without any machine path. Do not type the number by hand; paste the run.

In the tutorial you change only that test-run block. The typed `project`, `chronicle` and `stats` sections are Task 8's, written last.

## Documentation gates

`docs/reference/cli.md` and `docs/explanation/projections.md` per the brief's steps 5 and 6. One sentence per line. Facts in the reference, reasoning in the explanation. Headings in sentence case. `make -C docs html` treats warnings as errors; `make -C docs vale` enforces American English and the project vocabulary — if Vale flags a word you need (an identifier used in prose, a term of the domain), do not add it to the vocabulary yourself; use inline code for identifiers and report the word. `make -C docs linkcheck` resolves every link. `tests/test_docs_references.py` checks every `{ref}` in `src/` and `tests/` against labels in `docs/`, refuses a bare `§` citation, and refuses a citation inside program output (strings that reach `print`). Error messages and the `stderr` lines carry no `{ref}`.

## Your job

1. Tests first (brief step 1), run them red (step 2), implement (step 3), run green (step 4): `uv run pytest tests/test_cli.py -v`, then `uv run ruff check .` with no `C901` on `main`.
2. `cli.md` (step 5), `projections.md` (step 6), tutorial test block.
3. All six gates, each run separately, each output quoted in the report:
   ```
   uv run ruff check .
   uv run ruff format --check .
   uv run pyright
   uv run lint-imports
   uv run pytest --cov --cov-report=term-missing
   make -C docs html && make -C docs vale && make -C docs linkcheck
   ```
4. Commit with the brief's message, trailer `Assisted-By: Claude Opus 5 <noreply@anthropic.com>`.
5. Self-review your own diff (completeness against the brief, names, no overbuilding, test output pristine), then report.

While iterating, run the focused test for what you are changing; run the full suite once before committing.

## You do not dispatch subagents

Do all of this task's work yourself. Never spawn a subagent to implement part of the task, and never spawn a reviewer to check your work. Review is the controller's job: after you report, a fresh reviewer is dispatched against your diff. If you catch yourself thinking "an independent review would strengthen my report" — that review is already scheduled.

## When you are in over your head

It is always OK to stop and say so. Report `BLOCKED` or `NEEDS_CONTEXT` with what you are stuck on, what you tried, and what would unblock you. Bad work is worse than no work.

## Report

Write the full report to:
`/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1b-projektionen/.superpowers/sdd/2026-10-04-stufe-1b-projektionen/task-6-report.md`

It contains: what you implemented; the RED run (command and the relevant failing output) and the GREEN run; the six gate outputs; files changed; every place you deviated from the brief and why (including the `log` help string and anything from the Resolutions above you disagree with); self-review findings; concerns.

Then reply with ONLY (under 15 lines):
- **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
- Commit (short SHA + subject)
- One-line test summary (count, coverage)
- Your concerns and disagreements, one line each
- The report file path

If the task review finds issues, you will be resumed with the findings. Fix them, re-run the covering tests, append a fix report to the same report file, and reply with the same short contract.
