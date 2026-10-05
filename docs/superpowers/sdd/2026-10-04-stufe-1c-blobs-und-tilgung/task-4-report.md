# Task 4 report: the projections follow an erasure

Status: DONE_WITH_CONCERNS. Commit `600f757` on `worktree-stufe-1c-blobs`. Date of every measurement: 2026-10-05.

## What I implemented

1. `ProjectionStore.delete_chronicle(conn, event_id, seqs: Sequence[int] | None)` in `contract/store.py`, implemented in `storage/postgres.py`. `None` deletes every row of the event; an empty sequence issues no statement and deletes nothing.
2. `chronicle.erasures(batch)`: a pure function that returns `(event, None | units)` per redaction in chain order. It reads only events of kind `action` and calls `redaction.parse`. A `MalformedAction` takes nothing, and so does an action of another name (`parse` refuses those itself, so I dropped a separate `action_name` check that turned out redundant). A blob redaction (`event is None`) takes nothing. **One addition beyond the brief:** a redaction that names an event at or after its own `id` also takes nothing. Without that guard, a forged redaction that points forward would delete rows in a rebuild, where the target shares its batch, and none on the incremental path. That would break incremental == rebuilt. The reason is written in the comment.
3. `ChronicleProjection.version = 2`. `write` inserts what `derive` returns, then deletes what `erasures` names. Insert before delete keeps the batch boundaries out of the result for a target that still carries content its redaction erased (an order without its execution); the comment says so.
4. `cli._cmd_redact` prints its one line, then calls the new `_catch_up_after(storage, redaction_id)`. It does this after `already` as well. `_catch_up_after` runs `catch_up` over `PROJECTIONS`. On `PreviouslyError`/`StorageError` it raises `PreviouslyError("the redaction is recorded as event <id>, but it is not finished: projection <name> is not caught up (<error>); run the same command again")`, and `main` prints that with exit code 2. Standard output keeps the one line. Foreign exceptions still come through as a stack trace, as everywhere else in `main`. No new `print` call: the count stays at 26, measured with the command in `pyproject.toml`.

## TDD evidence

RED: `uv run pytest -q -p no:randomly tests/test_projection_derive.py tests/test_projection_store.py tests/test_projection_worker.py tests/test_cli.py`, which gave `9 failed, 91 passed`:
- `test_erasures_names_what_a_redaction_takes_out`: `AttributeError: module ... chronicle has no attribute 'erasures'` (expected, the function did not exist).
- `test_delete_chronicle_takes_the_named_rows_or_all_of_an_event`: `'PostgresStorage' object has no attribute 'delete_chronicle'` (expected).
- `test_incremental_equals_rebuilt_with_redactions_before_and_after_the_worker`: `[(1, 1), (1, …), (3, 2), …] == [(2, 2), (3, …), (7, 1), (7, 2)]` failed. Expected: version 1 never deletes, so the rows of event 1 and of unit 1 of event 2 stay.
- `test_project_on_an_empty_log_…` and `test_project_says_which_path_it_took`: `rebuilt: version 3 -> 1` instead of `3 -> 2`. Expected, the code was still at version 1.
- `test_after_redact_the_chronicle_no_longer_shows_it`: event 1's lines were still printed (no catch-up).
- `test_a_second_redact_finishes_what_the_first_left_behind`: stdout carried event 1's chronicle lines (no catch-up).
- `test_a_catch_up_that_fails_after_the_redaction_says_what_is_outstanding`: `assert 0 == 2` (no catch-up, so no failure).
- `test_project_rebuilds_a_chronicle_built_at_version_1`: `up to date, up_to_id 3` instead of `rebuilt: version 1 -> 2` (version still 1).
- The property test passed in that run and failed in a separate run (`--hypothesis-show-statistics`: "5 passing, 5 failing" in the generate phase). It is probabilistic, and the redaction step finds the bug about half the time per example.

GREEN: the same command gave `100 passed`. The property test passed 3 out of 3 when run alone. Full suite: `407 passed`.

## Mutations (command: edit one line with `sed`, run, then `cp` the backup back; `grep -c MUTATION` gave 0 after each restore)

| Mutation | Red | Green controls |
|---|---|---|
| `write` does not delete (`store.delete_chronicle(...)` → `pass`), run over the four projection/CLI test files | `test_incremental_equals_rebuilt_with_redactions_before_and_after_the_worker`, `test_property_…` (falsifying example `[_Append(email), _CatchUp(), _Redact(0, None)]`), `test_after_redact_the_chronicle_no_longer_shows_it`, `test_a_second_redact_finishes_what_the_first_left_behind`: `4 failed, 96 passed` | `test_a_redacted_event_leaves_no_chronicle_row` stayed green |
| `derive` builds a row for a unit without content (`continue` → `pass`) | 15 failed, every one with `psycopg.errors.NotNullViolation: null value in column "content" of relation "p_chronicle"`. That includes the refused-redaction CLI tests, whose setup runs a `redact` that now catches up | — |
| `_cmd_redact` does not catch up (the call → `pass`), `tests/test_cli.py` | `test_after_redact_the_chronicle_no_longer_shows_it`, `test_a_second_redact_…`, `test_a_catch_up_that_fails_…`: `3 failed, 61 passed` | `test_redact_event_prints_the_redaction_and_show_names_it` stayed green |
| Extra: catch up only `if result.written` | `test_a_second_redact_finishes_what_the_first_left_behind` only: `1 failed, 63 passed` | `test_after_redact_…` stayed green |
| `version` stays 1, over `test_cli.py` and `test_projection_worker.py` | `test_project_rebuilds_a_chronicle_built_at_version_1`, plus the two existing `project` tests: `3 failed, 76 passed` | — |
| Extra: drop the `redaction.event >= event.id` guard (re-run on the final code) | `test_erasures_…`: `[(5, None), (…), (13, None)]`, `1 failed, 10 passed` | the other 10 derive tests |
| Extra: drop the `kind != "action"` filter (re-run on the final code) | `test_erasures_…`: `[(5, None), (…), (4, None)]`, `1 failed, 10 passed` | the other 10 derive tests |

One flake during the first run of mutation 1: `test_redact_event_prints_the_redaction_and_show_names_it` also failed. A rerun of the same mutation kept it green (shown above). I put this down to the pre-existing connection issue under Concerns.

**Re-measured dated counts** (they had to move because the test files grew):
- `SourceStatsProjection.write` merges `None`: `test_incremental_equals_rebuilt` and the property fail, `2 failed, 24 passed`, and all 11 derive tests stay green.
- Overwriting `first_seen`: only `test_source_stats_aggregates_a_batch_per_source` and `test_merge_adds_counts_and_keeps_the_extremes` fail. All 15 worker tests stay green.
- Never catching up: `test_incremental_equals_rebuilt` and the late-arrival merge test fail.
- Version comparison dropped from the worker: both version tests fail, `2 failed, 13 passed`.

## Existing tests whose arrangement or expectation changed

- `test_cli.py::test_project_on_an_empty_log_is_up_to_date_at_zero_but_still_names_a_rebuild` and `test_project_says_which_path_it_took`: the state row is now raised to version 3 instead of 2, and the expectation is `rebuilt: version 3 -> 2`. The code now declares 2, so raising the state row to 2 would no longer be a mismatch.
- `test_projection_worker.py::test_a_tombstoned_event_keeps_its_chronicle_rows_with_evidence_null` is renamed to `test_a_payload_erased_without_a_redaction_keeps_its_chronicle_rows_with_evidence_null`. The docstring says it is a tombstone without an order, and the arrangement is unchanged. `test_a_redacted_event_leaves_no_chronicle_row` is the new test beside it.
- `test_projection_derive.py::test_chronicle_still_derives_rows_for_an_erased_payload` is renamed to `…_for_a_payload_erased_without_a_redaction`, with the docstring changed the same way.
- `_FailingStore` in `test_projection_worker.py` gains a delegating `delete_chronicle`, which the protocol requires.
- The property test `test_property_any_interleaving_of_append_and_catch_up_equals_a_rebuild` keeps its name. Its steps are now `_Append | _CatchUp | _Redact` (dataclasses, 1–8 steps). A redaction picks an appended event by position and erases the whole event or units `(1,)`, `(2,)` or `(1, 2)`. There is always a final catch-up before the snapshot.
- `test_incremental_equals_rebuilt` docstring: "all twelve tests in this file" / "all nine tests in test_projection_derive.py" became "every test", plus a line saying all three were remeasured on 2026-10-05 with 15 and 11 tests.
- `test_erasures_…` uses a `kind` parameter added to the `_event` helper in `test_projection_derive.py` (default `"observation"`).

## Departures from the brief

- **Two extra CLI tests** beyond the brief's table: `test_a_second_redact_finishes_what_the_first_left_behind` (pins the catch-up after `already`, which the brief requires) and `test_a_catch_up_that_fails_after_the_redaction_says_what_is_outstanding` (pins the error wording, exit code 2 and the single stdout line). The version-1 test the brief asks for is `test_cli.py::test_project_rebuilds_a_chronicle_built_at_version_1`.
- **How the failure test fails the catch-up:** it uses no wrapper. It forges a gap in the log with plain SQL, the way `test_projection_worker` already does, so the catch-up raises a real `ProjectionGap`. `_storage()` is private, and swapping it from a test would mean reaching into a private name.
- **`<what is outstanding>`** is filled with `projection <name> is not caught up (<error>)`.
- **The later-target guard** in `erasures` is not in the brief. Its reason is under "What I implemented" above.
- No signature departs from the brief.
- Test count: 398 → **407** (+9; the brief predicted +7, plus my two extra CLI tests).

## Handed-over sentences

- `projections.md` "What a chronicle per unit teaches about erasure": replaced by a new section, "How the chronicle follows an erasure". It covers the two rules, the before/after argument, the batch-boundary details, `redact` catching up, version 2 and `rebuilt: version 1 -> 2`, the tombstone without an order and its test, and why `source-stats` stays at version 1 and what `units` means. The intro line, the `evidence` paragraph, the "None of this is reachable in `p_chronicle`" paragraph, the append-only paragraph, the property sentence and the two mutation counts ("eleven", "thirteen", with a remeasurement sentence) were updated.
- `erasure.md` line 129: it now says the chronicle follows an erasure, that `redact` catches up, and that a failed catch-up leaves the chronicle behind until the same command or `project` runs.
- `chronicle.py` "because nothing in the tree erases a unit yet": removed. The docstring that cited `ChronicleProjection(version=2)` as the way to force a rebuild now says `version=3`.
- The worker test name and docstring: done as listed above.

## The three wording nits

- `cli.py`: I dropped the `{ref}` citation and stated the argument in place: "a reason that says nothing brakes nothing". That matches `_check_input` in `redact.py`.
- `redact.py` `_retrying` docstring and `concurrency.md`: the tombstones are set by the attempt that wins a position, *or by one that needs none because a redaction already covers its target and it writes no event*.
- `cli.md`: "which only a row this version didn't write can carry".

## Further sentences found untrue and rewritten

- `storage/schema.py`, the comment on `p_chronicle.evidence`: `NULL` now only happens for a payload tombstone without an order. A redacted event has no rows.
- `docs/reference/database-schema.md`, the `evidence` row: same correction.
- `core/projection/source_stats.py` docstring: one paragraph added saying that erasure does not make a row disappear, and that this is tested (`test_the_stats_keep_counting_an_erased_unit`).
- `docs/reference/cli.md`: the `redact` exit-code row; a catch-up paragraph with the error example and how to finish it; under `stats`, "`units` counts the units recorded, erased units included".
- `contract/store.py` `ProjectionStore` docstring: one paragraph on `delete_chronicle`.
- Tutorial test run retyped from a real `uv run pytest` run, without the `rootdir:` line.
- Left as is: the `version: int = 2` example in `how-to/rebuild-a-projection.md`. It tells the reader to "read the current value there", and the example still reads as a raised value.

## Gates (final run, on the tree that was committed)

```
uv run ruff check .                      -> All checks passed!
uv run ruff format --check .             -> 58 files already formatted
uv run pyright                           -> 0 errors, 0 warnings, 0 informations
uv run lint-imports                      -> Contracts: 4 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing -> ============================= 407 passed in 35.33s =============================
make -C docs html                        -> build succeeded.
make -C docs vale                        -> ✔ 0 errors, 0 warnings and 0 suggestions in 23 files.
make -C docs linkcheck                   -> build succeeded.
```

Coverage: `chronicle.py` 100%, `cli.py` 100%, `postgres.py` 100%, TOTAL 98%.

## Files changed

`src/previously/{cli.py, contract/store.py, core/projection/chronicle.py, core/projection/source_stats.py, core/redact.py, storage/postgres.py, storage/schema.py}`; `tests/{test_cli.py, test_projection_derive.py, test_projection_store.py, test_projection_worker.py}`; `docs/explanation/{concurrency.md, erasure.md, projections.md}`; `docs/reference/{cli.md, database-schema.md}`; `docs/tutorials/record-your-first-event.md`. The commit message file `task-4-commit-msg.txt` is in this directory and is not committed. `git status --short` before staging showed only my files.

## Concerns

1. **A flake that predates this task (measured at HEAD `d95882d` before I changed anything).** `uv run pytest -p no:randomly` (fixed file order) failed `test_cli.py::test_a_refused_redaction_is_one_sentence[a-redaction]` twice in a row, at its final `main(["log"])`, with `Error: database server at … does not answer`. Run alone in the same order, `test_cli.py` passes, and the default randomized run passes. My guess, not measured: `cli._storage()` builds a new engine with its own pool on every `main` call and never disposes it, so connections pile up until the server refuses. A similar flake showed up once during mutation 1. Worth a look by the controller; I left it alone because it is outside this task.
2. When the property test fails, Hypothesis's explain phase takes about 50 s. That only happens on a failure.
3. The catch-up failure test depends on the exact `ProjectionGap` message text, and so does the example in `cli.md`. If someone rewords that message, both have to change with it. `test_docs_references` passes today.

## Fix before review (ruling T4-a)

Commit `746ea4b` "fix: every command releases the connections it opened", on top of `600f757`. All measurements are from 2026-10-05.

### Measuring the cause, before any change

The tool was a throwaway pytest plugin in the scratchpad, `connprobe.py` (not committed). Around every test that takes `db` it recorded `SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()` and `SHOW max_connections`. It ran as `uv run pytest -q -p no:randomly -p connprobe` on `600f757`.

- `max_connections` = **100**.
- At the start of the run (`test_append.py`): **1** connection before and 1 after each test.
- Across `test_cli.py` the count climbs by roughly one per `main()` call. It is 2 at `test_append_log_and_verify_together`, then 59 → 65 at `test_verify_reports_a_deleted_tip_against_the_anchor`, 81 → 86 at `test_redact_event_prints…`, 86 → 90 at `test_redact_units…`, and **90 → 93** at `test_redacting_twice_says_already`, the test just before `test_a_refused_redaction_is_one_sentence`. Then it falls (7 before `[a-redaction]`), because a garbage collection ran.
- That run happened to pass: peak 93 of 100. The two failing runs at `d95882d` were not probed. Their error, `does not answer` = `ServerUnreachable` out of an `OperationalError` at connect, fits connection exhaustion, but I did not see 100 directly.
- A loop of in-process `main()` calls (temporary probe test, `log`/`verify`/`project` 10 times each): count **1** before, **31** after the 30 calls, **1** after `gc.collect()`.

Cause confirmed: one pool per `main()` call. It keeps its connection open until the unreferenced engine is collected.

### The choice

- **NullPool in `from_dsn`, measured and rejected.** `previously project` over 3,000 events (six appends of 500, five fresh builds each) took 0.535 / 0.548 / 0.537 / 0.560 / 0.555 s with the pool and 0.652 / 0.699 / 0.841 / 0.721 / 0.866 s with NullPool, one connection per transaction. That is about +35 % locally, and it would grow with the round-trip time of a remote server with TLS.
- **Chosen: an explicit lifetime.**
  - `PostgresStorage.close()` disposes the base engine. Both isolation views share its pool, so `__init__` keeps the base engine as `self._base`.
  - `cli._storage()` becomes a `@contextmanager` that closes in `finally`, so the release happens on success and on error alike.
  - Every command opens its storage with `with _storage() as storage` (combined with `storage.begin()` where the command had one).
  - `cli` still knows no SQLAlchemy and calls only `close`.
- I tied the release to the place that opens the storage rather than to `main` itself. `main` does not know whether or what a command opened, and a `with` on the opening line covers both success and the exception path.
- No test-only fix. The comments at `_storage`, `from_dsn` (which now names the pool, `close`, and the NullPool measurement) and `PostgresStorage.__init__` were updated.

### RED and GREEN

- New test: `tests/test_cli.py::test_main_releases_the_connections_it_opened`. It sets up one event, then makes 33 `main()` calls with the garbage collector disabled during the loop: 11 commands × 3, including `show 99` (exit 1) and a refused `redact event 99` (exit 2). The bound is `after <= before`.
- RED, before the fix: `E       assert 34 <= 1`.
- GREEN: measured `(before, after) == (1, 1)`, so the constant is **0**, no allowance.

### Mutations

- `PostgresStorage.close` body becomes `pass`: `E assert 34 <= 1`, `FAILED test_main_releases_the_connections_it_opened`, `1 failed, 64 passed`. Controls green: the other 64 tests in `test_cli.py`, among them `test_after_redact_the_chronicle_no_longer_shows_it`.
- Release on success only (`try`/`finally` in `_storage` replaced by `if True:` blocks): `E assert 4 <= 1`, one left over per refused `redact`. `1 failed, 64 passed`.
- Both restored; `grep -c MUTATION` gave 0.

### Evidence that the flake is gone

- The probe re-run after the fix, fixed order: **peak 4** connections across the whole run.
- `uv run pytest -p no:randomly`, three times in a row:
  - `============================= 408 passed in 34.76s =============================`
  - `============================= 408 passed in 35.24s =============================`
  - `============================= 408 passed in 44.85s =============================`
- Random order (`--randomly-seed=2747270624`): `============================= 408 passed in 56.44s =============================`. That run is the one typed into the tutorial.

### Count and gates

The test count is 407 → **408**. The `print` count in `cli.py` is still 26, measured with the command in `pyproject.toml`.

```
uv run ruff check .                      -> All checks passed!
uv run ruff format --check .             -> 58 files already formatted
uv run pyright                           -> 0 errors, 0 warnings, 0 informations
uv run lint-imports                      -> Contracts: 4 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing -> ============================= 408 passed in 47.07s =============================
make -C docs html                        -> build succeeded.
make -C docs vale                        -> ✔ 0 errors, 0 warnings and 0 suggestions in 23 files.
make -C docs linkcheck                   -> build succeeded.
```

Files changed: `src/previously/cli.py`, `src/previously/storage/postgres.py`, `tests/test_cli.py`, `docs/tutorials/record-your-first-event.md`. `cli.py` and `postgres.py` are at 100 % coverage.

### Remaining

- The other two concerns go to the reviewer unchanged (ruling T4-a).
- One side effect: every command body that used storage is now indented one level deeper under `with _storage() as storage`. `C901` stays green.

## Fix round 1

Commit `eb81651` "fix: redact names a rebuild it runs, and write's order is tested", on top of `746ea4b`. All measurements are from 2026-10-05.

### I1: redact reports a rebuild it runs (ruling T4-b)

What changed:
- `_catch_up_after` keeps the `Outcome` of each `catch_up`. When `outcome.rebuilt_from is not None` (a first build, or a rebuild after a version change), it prints `f"{outcome.name:<15} {_describe(outcome)}"` to standard error, the same line `project` prints. An ordinary catch-up prints nothing, and standard output stays the one line.
- `docs/explanation/projections.md`: "the first catch-up after the upgrade rebuilds it". It can be a `project` or a `redact`, and both name the rebuild, `redact` on standard error. A sentence in "Saying what it doesn't know" adds the same.
- `docs/reference/cli.md`: "An ordinary catch-up prints nothing. A catch-up that builds … or rebuilds … prints the line `project` prints for that projection, on standard error", with an example.
- `print` count in `cli.py`: 26 → **27**, measured with `ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py` (`Found 27 errors.`). The comment in `pyproject.toml` moved with it.

New test, `tests/test_cli.py::test_redact_reports_a_rebuild_it_runs_on_standard_error`:
- Setup: append, `project`, set the chronicle's `projection_state.version` to 1, then `redact event 1`.
- It expects `("redacted by event 2\n", "chronicle       rebuilt: version 1 -> 2, 2 events, up_to_id 2\n")`, and then `project` reports both projections as `up to date, up_to_id 2`.
- RED before the change: `At index 1 diff: '' != 'chronicle       rebuilt: version 1 -> 2, 2 events, up_to_id 2\n'`.
- GREEN after.
- Control: `test_after_redact_the_chronicle_no_longer_shows_it`, where projections are current and `stderr` stays `""`. Green.

Existing tests whose expectation changed, because their `redact` is the first catch-up on a log nobody projected and so builds both projections:
- `test_redact_event_prints_the_redaction_and_show_names_it`: `err` is now the two `built: 2 events, up_to_id 2` lines.
- `test_redact_units_names_each_tombstone`: `err` is those two lines, then `unit 3 was already erased`.
- Each carries a comment saying why.

Mutations, `uv run pytest -q -p no:randomly tests/test_cli.py`:
- Report removed (`if False:`): `3 failed, 63 passed`. Red: `test_redact_reports_a_rebuild_it_runs_on_standard_error` and the two tests above. Green: `test_after_redact_the_chronicle_no_longer_shows_it`.
- Every catch-up reported (`if True:`): `5 failed, 61 passed`. Red: `test_redact_units_names_each_tombstone`, `test_redacting_twice_says_already`, `test_after_redact_the_chronicle_no_longer_shows_it`, `test_a_second_redact_finishes_what_the_first_left_behind`, `test_redact_reports_a_rebuild…`. This is the control direction: the silence on an ordinary catch-up is pinned too.
- Both restored; `grep -c MUTATION` gave 0.

### I2: the reference page no longer promises that a rerun fixes a gap

`docs/reference/cli.md`:
- It now reads "Once its cause is gone, running the same command again finds the target covered, prints `already redacted by event 42`, and catches up."
- Added: "The cause in the example, a gap in the log, doesn't go away by itself, so until it does the same command fails with the same sentence; a server that didn't answer for a moment is a cause that does go away."
- The quoted example is unchanged, so `tests/test_docs_references.py` stays green without adjustment (in the 87-pass run below).

### I3: the insert-before-delete order is tested

New test, `tests/test_projection_worker.py::test_an_order_without_its_execution_ends_alike_on_both_paths`:
- Steps: append (2 units), project; `redact_units(1, [1])`; put the content of unit 1 back with raw SQL; project; compare incremental with a forced rebuild.
- Expected chronicle keys: `[(1, 2)]`.
- On ruling P-1 of the 2026-10-04 stage 1c plan: restoring content needs no other column. `unit_tombstone_check` only constrains a unit *without* content, which the test comment says.
- Green on the current order.

Mutation, the two steps of `write` swapped (delete first, then insert), `uv run pytest -q -p no:randomly tests/test_projection_worker.py tests/test_cli.py`:
- `1 failed, 80 passed`.
- Red: `test_an_order_without_its_execution_ends_alike_on_both_paths`, with `At index 0 diff: [(1, 1, 'one', …), (1, 2, 'two', …)] != [(1, 2, 'two', …)]` (the rebuild keeps `(1, 1)`).
- Green: `test_incremental_equals_rebuilt_with_redactions_before_and_after_the_worker` and the property, as the reviewer predicted.
- Restored.

The comment in `write` now names the test. The order does make an observable difference, so the claim stays.

### M1: the connection test polls

- After the loop it reads the count until it is no higher than before, for at most 5 s, polling every 0.05 s. It stays inside the garbage-collector-off block, so a collection during the polling cannot hide a leak. The bound `after <= before` is unchanged.
- The docstring now says what the test relies on: engines are freed only by the cycle collector, not by reference counting, and a later SQLAlchemy that freed them by refcount would make the test prove nothing.
- Re-measured: with `close` emptied it is still red, `E assert 34 <= 1`, `1 failed, 65 passed`.

### M2: `ruling T9-a` qualified at the two touched sites

`cli._storage` and `postgres.from_dsn` now read "ruling T9-a of the 2026-10-02 stage 1a plan, whose ledger is lost", worded after `.importlinter`, with the reason standing in the same sentence. The untouched citation at `_lag_line` (`cli.py:141`) stays bare.

### M4

`projections.md`: "A redaction that names a later event than itself takes nothing".

### Further numbers re-measured because the worker file grew to sixteen tests

- Version comparison dropped: `2 failed, 14 passed`. The page now says "the other fourteen green".
- `write` merges `None`: `test_incremental_equals_rebuilt` and the property red, `2 failed, 25 passed`, all derive tests green.
- Overwriting `first_seen`: `16 passed` in the worker file.
- Never catching up: `test_incremental_equals_rebuilt` and the late-arrival merge test red, `2 failed, 25 passed`.
- So the dated sentences now say "sixteen" (`projections.md`, the `test_incremental_equals_rebuilt` docstring).

### Count, covering tests and gates

- Covering tests: `uv run pytest -q -p no:randomly tests/test_cli.py tests/test_projection_worker.py tests/test_docs_references.py` → `87 passed in 19.89s`.
- Test count: 408 → **410**. The tutorial block is retyped from a real random-order run (`410 passed in 35.91s`).
- `print` count: **27**.

```
uv run ruff check .                      -> All checks passed!
uv run ruff format --check .             -> 58 files already formatted
uv run pyright                           -> 0 errors, 0 warnings, 0 informations
uv run lint-imports                      -> Contracts: 4 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing -> ============================= 410 passed in 36.02s =============================
make -C docs html                        -> build succeeded.
make -C docs vale                        -> ✔ 0 errors, 0 warnings and 0 suggestions in 23 files.
make -C docs linkcheck                   -> build succeeded.
uv run pytest -p no:randomly             -> ============================= 410 passed in 35.22s =============================
```

The first `ruff check` of this round found an `E501` in the qualified `_storage` docstring. I rewrapped it and then ran all six gates again; the lines above are from that second run.

Files changed: `docs/explanation/projections.md`, `docs/reference/cli.md`, `docs/tutorials/record-your-first-event.md`, `pyproject.toml`, `src/previously/cli.py`, `src/previously/core/projection/chronicle.py`, `src/previously/storage/postgres.py`, `tests/test_cli.py`, `tests/test_projection_worker.py`.

Concerns: none new. The cli.md example `12000 events, up_to_id 12001` is an illustrative line, not a measurement.
