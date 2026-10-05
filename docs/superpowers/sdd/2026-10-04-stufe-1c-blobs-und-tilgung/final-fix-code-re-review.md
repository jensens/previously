# Final fix wave, code part: re-review (1ec0b2e..d02aaf6)

## Finding Verdicts

1. **Critical 1: two catch-ups of one projection run one after the other, per batch.** ADDRESSED.
   - `worker.py:116` (first transaction) and `worker.py:128` (every batch) take `state` from `lock_projection_state`. No value read before the lock is used after it. The only thing carried across transactions is `rebuilt_from`, which is display.
   - `postgres.py:568-594`: `INSERT … ON CONFLICT DO NOTHING RETURNING`, then `SELECT … FOR UPDATE` (`:590`).
   - **Walk-through under READ COMMITTED:**
     - **Both up to date.** Each locks the row, reads `tip <= up_to_id`, breaks and commits.
     - **One behind.** The second waits at `:590`. EvalPlanQual then returns the committed `up_to_id` of the first.
     - **First build by both.** The second waits at the primary key behind the uncommitted placeholder, inserts nothing, and locks the committed row at a new statement snapshot. If the first rolls back, the second inserts and builds.
     - **Rebuild beside a catch-up.** The rebuild's first transaction waits at the row. The other worker's next batch reads the new version and raises.
     - **`redact` catch-up during a `project` batch.** It waits at the first transaction's lock.
   - **The original interleaving:** `project` reads event 1, the redaction (id 2) commits, event 3 is appended. The catch-up of `redact` waits until `project` commits `up_to_id 1`, then reads 2..3 from the row and deletes event 1's rows (`chronicle.py:131`) at a statement snapshot that sees them.
   - Erased content in `p_chronicle` is **impossible**, not just unlikely. A redaction's id is greater than every event in a batch that read its target before it committed (contiguous chain, one-statement cursor in `read`, `postgres.py:322-332`). So the redaction is always projected by a later batch, which is serialized behind the one that inserted the rows. A redaction committed before the batch's `read` makes `units_by_event` (a later statement) see the erased units as well.
   - **Tests:** `test_two_catch_ups_of_one_projection_take_turns[appended-meanwhile|control]`, `test_two_first_builds_build_once`, `test_a_catch_up_stops_when_another_release_rebuilds_under_it`, and `test_cli.py::test_redact_beside_a_project_holding_rows_ends_without_a_traceback`.
     - They pause at real calls with `threading.Event`, and release on an observable condition (`pg_stat_activity.wait_event_type = 'Lock'`) or on the other thread finishing. The 10 ms poll waits for that condition and does not hope for an order.
     - No mock. The subclasses call `super()`.
     - I traced them by hand: with the lock taken but `up_to_id` from memory, `[appended-meanwhile]` goes red (A's second batch re-reads 2..3 → `IntegrityError` on (3,1)). It is listed below for measurement.
   - **No traceback:** a `ProjectionRebuilt` or `TransactionAborted` from a catch-up is a `PreviouslyError` or `StorageError`. `main` turns it into one sentence, and `_catch_up_after` (`cli.py:890`) catches it.
   - Ran: the four tests, 9 passed together with the docs-references tests.
2. **Important 1: `redact units` says the payload stays.** ADDRESSED.
   - `redact.py:327` sets `payload_stands` from the locked target on both the written and the covered path. `cli.py:952` prints `_payload_line` (`cli.py:810`) last, on stderr. Stdout and exit code are unchanged.
   - The `redact` subcommand list shows the help (`cli.py:784`).
   - `append --text` is unchanged.
   - The page (`cli.md`) quotes the block, and `test_docs_references.py` holds it. The tests passed when I ran them.
   - Caveat under New Breakage (Minor A): `previously redact units --help` itself does not show the sentence.
3. **Important 2: lock mode, and the error for an aborted transaction.** ADDRESSED.
   - `postgres.py:523` uses `with_for_update(key_share=True)`. `test_lock_event_and_a_foreign_key_check_on_the_event_do_not_wait_for_each_other` covers both directions with `lock_timeout`. `test_lock_event_makes_a_second_locker_wait` is unchanged and green.
   - `postgres.py:200-207`: `sqlstate` from `error.orig` (psycopg 3 `Error.sqlstate`). `40*` or `55P03` becomes `TransactionAborted`. A failed connection carries `sqlstate None` and stays `ServerUnreachable`, so the two cannot be confused.
   - Retry loops: `append.py:463` and `redact.py:165` catch only `ChainPositionTaken`, which comes from `IntegrityError` and is unaffected. Nothing caught `ServerUnreachable` before.
   - Real deadlock test and real `55P03` test. Both pass.
4. **Important 3: the lock comments.** ADDRESSED.
   - `schema.py` at `event_prev_hash_idx`, the `lock_event` docstring (`postgres.py:510-521`) and the `RedactionStore` docstring were checked against `redact.py:246` (event plus sharers, ascending), `:294` (units, target only) and `:360` (blob users, ascending), and against `worker.py`. All are true at the head, including the mode.
5. **Minor 2: the 0003 downgrade.** ADDRESSED. `0003_hash_version_2.py:68` uses `hash_version <> 1`. `test_the_downgrade_refuses_on_any_version_other_than_1` uses `hash_version = 3` set with raw SQL, and checks that the database is still at head. I did not run it (own container); the report claims red against the old condition.
6. **Minor 3: order of checks.** ADDRESSED.
   - `cli.py:418-419`: `_attach` is now inside `with _storage()`, which refuses an unset `PREVIOUSLY_DSN` before `from_dsn` and before any upload.
   - `cli.py:936`: the address check in `redact` comes before `_storage()`. `blob get` already checked first (`cli.py:735`).
   - Tests: `test_append_with_an_attachment_and_no_database_stores_nothing` (bucket empty), and `test_a_blob_address_that_is_not_one_is_an_input_error[blob get|redact blob]` with the DSN unset. Ran: green.
7. **Minor 4: both steps after the commit.** ADDRESSED.
   - `_delete_obsolete` (`cli.py:836`) and `_catch_up_after` (`:868`) return a phrase instead of raising. `_cmd_redact` (`:942-946`) calls both unconditionally and joins what is left with `, and `. Exit code 2 through `main`.
   - All combinations:
     - deletion fails, catch-up succeeds → deletion phrase only;
     - the reverse → catch-up phrase only;
     - both fail → both phrases, deletion first;
     - neither fails → success lines.
   - No path claims a step outstanding that is done. A phrase exists only when that step's `except` ran.
   - An exception of a foreign type in the deletion still skips the catch-up and escapes as a traceback. That is the module's stated policy, and `S3BlobStore.delete` (`s3.py:240-248`) and `from_settings` (`s3.py:337`) translate every `ClientError`/`BotoCoreError`, so I know of no reachable path. It is noted under Out-of-Scope.
   - Tests: the extended `test_a_delete_that_fails_is_finished_by_the_second_call` (the chronicle is clean after the failed deletion) and `test_a_delete_and_a_catch_up_that_both_fail_are_named_in_one_sentence`. Ran: green.
8. **Minor 5: `of_unit` returns the earlier redaction.** ADDRESSED. `redaction.py:216-225`: `min(…, key=id)`, the same as `of_reference`. The test covers both orders. Ran: green.
9. **Minor 6: `verify --blobs` keeps the chain's findings.** ADDRESSED.
   - `verify.py:689` calls `before_blobs(tuple(findings))` after `_closing_findings` and before `_blob_findings`. `cli.py:528` prints them, and `cli.py:540` prints only the remainder (`findings[len(chain):]`), so no finding is printed twice.
   - The error goes to stderr with exit code 2 through `main`.
   - The test is parametrized over `forged` × 3 failure kinds. Ran: green.
10. **Minor 7: the census in `contract/store.py`.** ADDRESSED. `store.py:9`: I ran the command, which now ends in `| sed 's/.*\.//' | sort -u`, over the five files. It prints 13 lines. The `def`s in `LogStore` number 13.
11. **Identity directory.** ADDRESSED.
    - `cli.py:248-261` refuses a path that is no directory with `PREVIOUSLY_BLOB_IDENTITIES is not a directory: <path>`, exit code 2.
    - It is reached from `_examine` before the chain pass for `verify --blobs`, and before the store for `blob get`.
    - The control in the same test: an existing empty directory still gives `FINDING … cannot be opened` (exit 1) or `Error: blob … cannot be opened` (exit 2).
    - `configuration.md` matches the code. Ran: green.

## New Breakage in the Fix Diff

- **Minor A: `previously redact units --help` does not say that the payload stays.** `cli.py:783-785` passes the sentence as `help=`, which argparse prints only in the parent's list (`previously redact --help`, measured). The `units` subcommand's own `--help` prints usage and arguments only (measured). Brief §2 asks for "`redact units --help` says that the payload stays". Fix: pass the same sentence as `description=` as well.
- **Minor B: `concurrency.md:8` is now false.** It still promises to say "what the one row lock in the system is for". Since `3ae7038` there is a second row lock, the catch-up's lock on `projection_state`. The fix edited this page (lines 79-81), and its own `schema.py` comment now says "row locks" in the plural. This is for the documentation part. The page explains nothing about the catch-up lock yet, which the implementer's report also says.
- **Minor C: the reference does not say what an operator does on `ProjectionRebuilt`.** `cli.md` adds the case to the `project` exit-code row and nothing else.
  - What the operator has to know: a catch-up at another code version is running against the same database, and running the same release again rebuilds the table back to its own version (`worker.py:117`, `!=`).
  - Inside `redact`, the error is wrapped in "…; run the same command again". Followed with the older release, that advice rebuilds the projection back.
  - Not false, but missing on a page the fix touched. This is for the documentation part.
- **Minor D: on an unfinished `redact units` (exit code 2), the payload notice is not printed.** `cli.py:946` raises before `:952`. The rerun prints it, and exit code 2 claims no success, so the defect of Important 1 (a false success) does not recur. Noted because brief §2 says "whenever".

No Critical or Important breakage. Other checks, all clean:
- `noqa`: still 5 in the tree (`grep -rn noqa src tests migrations docs/conf.py`).
- No `# type: ignore` added.
- No mock.
- No private name reached from a test.
- `.importlinter` is unchanged.
- The T201 count of 33 is measured (`ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py` → 33).
- No ruling label was added. No citation appears in program output.
- English throughout.
- All eleven commits carry `Assisted-By` only.
- Gates I ran: `ruff check` All checks passed, `ruff format --check` 69 files already formatted, `pyright` 0 errors, `lint-imports` 6 kept 0 broken. I did not run the full suite or the docs gate. The focused runs were 9 passed and 24 passed.

## The two design choices

- **`ProjectionRebuilt` instead of rebuilding back: sound.**
  - Rebuilding back inside one run would have two releases truncate each other's tables batch by batch at a FIFO lock. Raising bounds the damage to one aborted run with one sentence and exit code 2.
  - It cannot fire between two workers of the same version. A same-version worker that finds the row reset to `up_to_id 0` (a hand-deleted row, then a first build by a third worker) continues from the row, which is correct.
  - It can fire for a `project` running while an operator follows `rebuild-a-projection.md` (`DELETE FROM projection_state`), with "has no state row". That is accurate.
  - The residual ping-pong across runs comes from the pre-existing `!=` rule, not from this choice.
  - What is missing is the operator text (Minor C).
- **The version-0 placeholder: sound, and it cannot be committed.**
  - First transaction (`worker.py:116-123`): `None` always leads to `truncate_projection` and `set_projection_state` at the code's version. That overwrites the placeholder, or an exception rolls the transaction back.
  - Batch transaction (`worker.py:128-136`): `None` raises inside `with store.begin()`, so it rolls back.
  - No early return or `break` comes before either. There is no other caller: `lock_projection_state` is called only at those two lines in `src`, and the tests' wrappers delegate.
  - A zero-event batch cannot meet the placeholder: the check comes before `tip`.
  - Readers (`chronicle` lag, `stats`) read `projection_state` unlocked at READ COMMITTED and never see an uncommitted row. No check constraint refuses version 0 (`schema.py`).
  - If a placeholder were ever committed, the next catch-up would see version 0, which differs from the code's version, and rebuild, as the docstring says.
  - The steady-state `INSERT … ON CONFLICT DO NOTHING` on an existing row writes no tuple. It waits only behind an in-progress update of the row (DirtySnapshot), which is harmless.

## Mutations for the controller to measure

1. `src/previously/core/projection/worker.py:128`: change `state = store.lock_projection_state(conn, projection.name)` to `store.lock_projection_state(conn, projection.name)`, so the batch takes the lock and keeps `state` from the previous transaction.
   - Expected red: `tests/test_projection_worker.py::test_two_catch_ups_of_one_projection_take_turns[appended-meanwhile]` (`IntegrityError` on `p_chronicle_pkey` (3, 1)) and `test_a_catch_up_stops_when_another_release_rebuilds_under_it`.
   - Expected green: `[control]`.
   - This settles "would they go red if the lock were taken but `up_to_id` came from memory"; the implementer measured only the lock taken out entirely.
2. `src/previously/storage/postgres.py:590`: drop `.with_for_update()` from the `SELECT`, and keep the placeholder insert.
   - Expected red: `test_two_catch_ups_of_one_projection_take_turns[appended-meanwhile]` and `tests/test_cli.py::test_redact_beside_a_project_holding_rows_ends_without_a_traceback`.
   - Expected green: `test_two_first_builds_build_once`, because the placeholder alone still serializes first builds.
   - This separates the two halves of the lock, which mutation 1 of the report removed together.

## Out-of-Scope Observations

- `_catch_up_after` (`cli.py:886-892`) returns at the first projection that fails and does not attempt the ones after it. If `chronicle` fails, `source-stats` is neither caught up nor named in the sentence. Brief §5 defines the two steps as deletion and catch-up, and the old code had the same order, so this does not block.
- A foreign exception type in `_delete_obsolete` still skips the catch-up (see 7). I found no reachable source.
- The census command in `store.py:9` is in a non-raw docstring. Its source text reads `\\.`, and copied from the file into a shell it matches nothing; the rendered docstring is correct. The same was true before the fix.
- `docs/explanation/projections.md:148` ("sixteen in `test_projection_worker.py`") is now stale (20). The implementer flagged it for the documentation part.
- `TransactionAborted` covers class 40 as a whole, including `40003` (statement completion unknown), for which "run again" is not certainly safe. PostgreSQL does not raise it from the server. No test pins `40001`.

## Verdict

**Fix wave, code part:** All findings addressed, no new Critical/Important breakage. Four Minor items for the controller and the documentation part: A (`redact units --help`), B (`concurrency.md:8`), C (operator text for `ProjectionRebuilt`), D (no payload notice on an unfinished `redact units`). Two mutations to measure.
