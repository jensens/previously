# Final fix wave, part 1 (code): report

Status: **DONE_WITH_CONCERNS**. The concerns are small and listed at the end. Branch `worktree-stufe-1c-blobs`, eleven commits on top of `1ec0b2e`, head `d02aaf6`. The worktree is clean.

## Per finding

### Critical 1: two catch-ups of one projection are not serialized (`3ae7038`)

**Measured before the change.** I ran the reviewer's scratch test unchanged against the tree's fixtures (`uv run pytest …/scratchpad/race/test_race.py`). It failed with `assert [(1, 1, 'secret line one.'), …] == []`, so the erased text was still in the chronicle after a further catch-up. The failure reproduced.

**Changed.**
- `src/previously/contract/store.py`: `ProjectionStore.projection_state` is replaced by `lock_projection_state(conn, name) -> ProjectionState | None`, and the docstring says why. `core` called nothing else that read the state row. `PostgresStorage.projection_state` stays, outside the protocol, because tests read it.
- `src/previously/storage/postgres.py`, `lock_projection_state`: it runs `INSERT … ON CONFLICT (name) DO NOTHING RETURNING name` with a placeholder row (`up_to_id 0`, version 0, `now()`).
  - If the insert wrote a row, the method returns `None` and the transaction holds the new row.
  - Otherwise it runs `SELECT … FOR UPDATE` on the existing row and returns it.
  - A second first build waits at the primary key, then inserts nothing and locks the committed row.
  - Version 0 is never committed: the first transaction overwrites it, and a batch rolls it back. If it ever were committed, it would only trigger a rebuild.
- `src/previously/core/projection/worker.py`: every transaction locks the state row and takes `up_to_id` and the version from the locked row. That covers the first transaction (first build, rebuild after a version change) and every batch.
  - A batch that finds the row missing or at another version raises `ProjectionRebuilt`. This is a new error in `core/errors.py`.
  - It raises instead of rebuilding back because two releases that each rebuilt on seeing the other's version would alternate at the lock forever. PostgreSQL's lock queue is FIFO, so that alternation is strict.
- `src/previously/storage/schema.py`: the comment at `event_prev_hash_idx` names the catch-up's lock.
- `docs/reference/cli.md`: the `project` row of the exit-code table gains the rebuilt-under-it case.

**Tests.**
- `tests/test_projection_worker.py::test_two_catch_ups_of_one_projection_take_turns[appended-meanwhile]` is the reviewer's interleaving, made deterministic. A `PostgresStorage` subclass pauses at `source_keys` and again after `set_projection_state`. It continues once the other worker is done, or once `pg_stat_activity` shows a backend with `wait_event_type = 'Lock'`. There is no sleep that hopes for an order.
  - The test asserts no errors, chronicle keys `[(3, 1), (3, 2)]`, a further catch-up with 0 events, and that the result equals a rebuild.
- `…[control]` is the same run without the extra append.
- `test_two_first_builds_build_once`: with no state row, two catch-ups start at once. Exactly one reports `rebuilt_from == 0`.
- `test_a_catch_up_stops_when_another_release_rebuilds_under_it`: a catch-up at version 3 runs between the first transaction and the first batch of a version 2 catch-up. The version 2 catch-up raises `ProjectionRebuilt` with the exact sentence. The control (no other release) ends clean.
- `tests/test_cli.py::test_redact_beside_a_project_holding_rows_ends_without_a_traceback` covers item 4. A `project` holds event 1's chronicle rows uncommitted while `main(["redact", "event", "2", …])` runs.
  - The test asserts exit 0, stdout `redacted by event 3`, stderr only `source-stats    built: 3 events, up_to_id 3`, and the chronicle rows of event 1.

**Mutation 1: the lock taken out.** `lock_projection_state` returned `self.projection_state(conn, name)` as its first line, so it only read.
- `take_turns[appended-meanwhile]` went red with `IntegrityError … p_chronicle_pkey … Key (event_id, seq)=(3, 1)`. This is the reviewer's failure.
- `two_first_builds_build_once` went red: `(0, 0) == (0, None)`, so both built.
- The CLI test went red: `main` raised `IntegrityError … Key (event_id, seq)=(1, 1)` as a traceback.
- `take_turns[control]` stayed green. All four are green with the lock.

**Mutation 2: the version check in the batch reduced to `if state is None`.** Only `test_a_catch_up_stops_when_another_release_rebuilds_under_it` went red (no error raised). The other 19 tests in the file stayed green.

**Deadlock check (item 5).** Which transaction holds which locks:
- **The redaction transaction** (`redact_event` / `redact_units` / `redact_blob`, one transaction per attempt) locks in two phases.
  - First phase: `FOR NO KEY UPDATE` on event rows, in ascending `id`, all before anything else.
  - Then it inserts its own new event row (unique-index entries), runs `UPDATE event` (a no-key update, the same mode on the same rows) and `UPDATE unit` on the target's unit rows.
  - It never touches `projection_state`, `p_chronicle` or `p_source_stats`.
- **A catch-up batch transaction** first locks `projection_state` (`FOR UPDATE`, or holds the placeholder insert) and nothing before it.
  - It reads `event`, `unit`, `source_key` and `event_blob` without locks.
  - It inserts and deletes `p_chronicle` rows and upserts `p_source_stats` rows.
  - Its foreign keys (`p_chronicle.event_id`, `p_source_stats.last_event_id`, both onto `event` only) take `FOR KEY SHARE` on committed event rows.
- **Between a redaction and a catch-up.** The only rows both touch are `event` rows. `FOR NO KEY UPDATE` and no-key `UPDATE` are compatible with `FOR KEY SHARE`, so there is no wait edge in either direction and no cycle. The redaction's new event row is uncommitted and invisible to the catch-up, so nothing references it.
- **Between two catch-ups of one projection.** The second waits at the state row, which is its first lock, while holding nothing, so there is no cycle. Catch-ups of different projections share only `KEY SHARE` on `event`, and those are compatible.
- **Between two redactions.** Both lock in ascending order before any write. A wait at the unique index (two erasures racing for one chain position) happens after the lock phase, and the one that inserted first waits for nothing, so there is no cycle.
- **Within the `redact` command.** The redaction transaction commits before the first catch-up opens, so one process never holds both.

With `FOR UPDATE`, a cycle was possible, as the reviewer reasoned: an erasure holding row *a* and wanting *b*, beside a source-stats upsert holding the key share on *b* and wanting *a*. Important 2 removes that cycle.

### Important 1: `redact units` and the payload (`4bbb305`)

**Changed.**
- `core/redact.py`: `Redacted.payload_stands: bool = False`. `redact_units` sets it from the locked target row (`target.payload is not None`), on the written path and on the covered path.
- `cli.py`: `_payload_line(event_id)` holds the wording. `_cmd_redact` prints it on stderr after the other notices. The `units` subparser help now reads `erase the content of the named units; the payload of the event stays`.
- `docs/reference/cli.md`: one sentence at `redact units` ("leaves the event's payload as it is"), and a quoted block with the notice and why.
- `tests/test_docs_references.py`: the block is added to the list of quoted stderr sentences, and the docstring count is corrected to "ten … in nine blocks".
- `pyproject.toml`: the T201 count is updated from 32 to 33, measured with the command in the comment.

**Form.** The wording is exactly the one in the brief, backticks included. The `stays in the store` notices quote no command at all, so their form gives nothing to follow. The other notices that name a command (the lag line, the `verify` anchor notice) use backticks as well.

**Tests.**
- `tests/test_cli.py::test_redact_units_says_that_the_payload_stays`:
  - the first run and a rerun both print the notice, stdout keeps its one line, and the exit code is 0;
  - `show` still prints the text in the payload;
  - the control: after `redact event` has erased the payload, `redact units` prints no notice.
- `tests/test_redact.py::test_redacting_units_says_whether_the_payload_still_stands` is the core half, with the same control.
- Three existing tests now expect the notice or the new field.

**Mutation: `payload_stands=False`.** Five tests went red: the two new ones, `test_redact_units_names_each_tombstone`, `test_redacting_units_leaves_the_others_attested` and `test_redacting_units_again_skips_what_is_covered`. All are green with the fix.

**Page check.** I changed the code's wording to "may hold that text". `test_the_reference_quotes_what_the_code_actually_prints` then failed with `cli.md quotes … and no message in cli.py says that`. Restored.

### Important 2: the lock mode, and what a lock failure is called (`30c33eb`)

**Measured** with a scratch test against the real container, `lock_timeout = 300ms`, at `FOR UPDATE`:
- `lock_event` after an open transaction that inserted a `p_chronicle` row of the same event: `LockNotAvailable … canceling statement due to lock timeout`.
- The reverse, an insert after `lock_event`: also `LockNotAvailable`.
- At `FOR NO KEY UPDATE`: "no wait" in both directions.

**Changed.**
- `storage/postgres.py`: `lock_event` uses `with_for_update(key_share=True)`, and its docstring states the measurement and the reason.
- `storage/errors.py`: `TransactionAborted(StorageError)`.
- `_transaction` reads `error.orig.sqlstate` through `getattr`. A string that starts with `40`, or equals `55P03`, becomes `TransactionAborted` with the sentence below. Every other `OperationalError` stays `ServerUnreachable`.
- `cli.py` needed no change: `main` already turns every `StorageError` into `Error: …` with exit code 2.
- `docs/reference/cli.md` gets one sentence with the wording.

**Tests.** All three are in `tests/test_storage.py`.
- `test_lock_event_and_a_foreign_key_check_on_the_event_do_not_wait_for_each_other`: both directions, with `lock_timeout`.
- `test_a_deadlock_becomes_a_storage_error_that_says_to_run_again`: two threads, two rows, opposite order, a real deadlock. Exactly one transaction ends in `TransactionAborted` with the exact sentence.
- `test_a_lock_not_granted_in_time_becomes_the_same_storage_error`: `55P03` inside `storage.begin()`.

**Mutation: back to `with_for_update()`.** Only the foreign-key test went red, across `test_storage.py` and `test_redact.py` (1 failed, 68 passed). The existing tests that pin two erasures waiting for each other (`test_lock_event_makes_a_second_locker_wait` and those in `test_redact.py`) stayed green, unchanged.

**Mutation: the translation disabled (`if False:`).** The deadlock test and the `55P03` test went red; the deadlock came out as `ServerUnreachable: database server at … does not answer`.

### Important 3: the comments that described the old lock (`3ae7038`, `30c33eb`)

- `storage/schema.py` at `event_prev_hash_idx` now says:
  - the row locks order other things, never the chain;
  - an erasure locks `FOR NO KEY UPDATE` its target for `redact units`, its target and every event sharing a blob with it for `redact event`, and every user of the blob for `redact blob`, each set in ascending `id`;
  - foreign-key checks wait for neither;
  - a catch-up locks its state row.
- `storage/postgres.py`, the `lock_event` docstring, says the same, with the mode and the reason.
- The `RedactionStore` docstring in `contract/store.py` said `FOR UPDATE` as well. I corrected it too.
- I checked all three against `redact.py` (`_lock_ascending`, `redact_units`, `redact_blob`) and `worker.py` as they stand at the head.
- `docs/explanation/concurrency.md` named `SELECT … FOR UPDATE`. It now says `FOR NO KEY UPDATE`, in two sentences that say why.

### Minor 2: the downgrade below 0003 (`bb85f6c`)

- `migrations/versions/0003_hash_version_2.py` asks for `hash_version <> 1`. The sentence now reads `the log holds events in a hash format other than 1, which cannot be verified without the version and the salts this would drop`.
- New test: `tests/test_migration_0003.py::test_the_downgrade_refuses_on_any_version_other_than_1`, in its own container. It uses `UPDATE event SET hash_version = 3` and expects the exact refusal, with the database left at head.
  - **Red with the old condition:** `DID NOT RAISE CommandError`. Green with the new one.
  - The existing test (a version 2 row) is the control, green both ways; its expected sentence is updated.
  - No page quotes the sentence.

### Minor 3: the order of the checks (`6ed8f8a`, `d02aaf6`)

- `cli.py` `_cmd_append`: `with _storage()` now encloses `_attach`, so an unset DSN is refused before any upload.
- `_cmd_redact`: an address that is no address is refused, after the empty-reason check and before `_storage()`, with the wording `blob get` uses.
- Tests:
  - `test_append_with_an_attachment_and_no_database_stores_nothing`: exit 2, `Error: PREVIOUSLY_DSN is not set`, bucket empty. Red before.
  - `test_a_blob_address_that_is_not_one_is_an_input_error` now runs `blob get` and `redact blob` with `PREVIOUSLY_DSN` unset. Before, it ran only `blob get`, with an unreachable DSN. Both `redact blob` cases were red before (`PREVIOUSLY_DSN is not set`).
- `d02aaf6` adds `test_redacting_a_blob_by_something_that_is_no_address_is_refused` in `test_redact.py`. After the change, the core's own refusal in `redact_blob` was reached by no test, and the full run showed `redact.py:352` uncovered. It is now 100%.
- `cli.md`: two sentences, the DSN check before storing, and the address refused before a setting or the database is asked.

### Minor 4: both outstanding steps attempted (`b9b0cdc`)

- `cli.py`: `_delete_obsolete` and `_catch_up_after` return the outstanding phrase, or `None`, instead of raising. `_cmd_redact` calls both, collects what is outstanding, and raises one `_unfinished` sentence with the parts joined by `, and ` (deletion first).
- Both phrases are still assigned to a variable named `outstanding`, so `test_docs_references` still finds them.
- `cli.md`: "A failed deletion leaves the catch-up undone as well" is replaced by two sentences: the catch-up runs regardless, and how both are named.
- Tests:
  - `test_a_delete_that_fails_is_finished_by_the_second_call` now also asserts that `chronicle` prints nothing on either stream after the failed call (no erased row, no lag).
  - New `test_a_delete_and_a_catch_up_that_both_fail_are_named_in_one_sentence`: store down plus a forged gap. The sentence starts with the blob and ends with `), and projection chronicle is not caught up (expected events 2.. above id 1, read [3, 4]; the tip is 4); run the same command again`.
- **Mutation:** a deletion failure raised before the catch-up, as before. Both tests went red: the chronicle still printed the erased unit and the lag, and the sentence named the blob only.

### Minor 5: `RedactionIndex.of_unit` (`44e8024`)

- `core/redaction.py`: the earlier of the units redaction and the event redaction, `min(…, key=id)`, as in `of_reference`.
- Test: `tests/test_redaction.py::test_the_index_names_the_earlier_of_a_unit_redaction_and_an_event_redaction`, both orders. Red with the old code, on the first assertion.

### Minor 6: `verify --blobs` keeps the chain's findings (`b2aa253`)

- `core/verify.py`: `examine(…, before_blobs=callback)` is called with the chain and anchor findings after `_closing_findings` and before `_blob_findings`.
- `cli.py`:
  - `_cmd_verify` prints those findings in the callback and the remainder (`examination.findings[len(chain):]`) afterwards.
  - The `print` moved into `_print_findings`, so the T201 count stays 33. I re-measured it.
- `cli.md`: one sentence. The findings of the chain still go to standard output beside the error sentence, and with no finding standard output stays empty.
- Test: `test_verify_blobs_that_cannot_check_is_an_error_and_no_finding` is parametrized additionally over `forged` (a unit rewritten by SQL). For all three failure kinds, stdout is `FINDING 1: unit 1 does not match its digest\n` and stderr is the error; without `forged`, stdout stays empty.
- **Mutation: callback never called.** The three `forged-unit` cases went red.
- **Mutation: the slice removed** (chain findings printed twice). `test_anchor_prints_the_tip_and_verify_holds_it` and `test_verify_reports_a_deleted_tip_against_the_anchor` went red.

### Minor 7: the census (`1bbc658`)

- The command in `contract/store.py` now ends in `| sed 's/.*\.//' | sort -u`.
- Measured: the old command printed 21 lines; the new one prints the 13 names, which equal the 13 `def`s of `LogStore`.
- `lock_projection_state` belongs to `ProjectionStore`, and `worker.py` calls it as `store.…`, so `LogStore` stays at 13. The comment says when it was taken and why it used to print 21.

### Doc review Minor 11: the identity directory (`d68b2e7`)

- **Measured before the change:**
  - `verify --blobs`, with `PREVIOUSLY_BLOB_IDENTITIES` pointing at a path that does not exist, returned 1 with `FINDING … cannot be opened`.
  - `blob get` returned 2 with `cannot be opened: there is no identity for the key 'age1…'`.
- `cli.py` `_identities()` checks `Path(directory).is_dir()` and raises `PreviouslyError("PREVIOUSLY_BLOB_IDENTITIES is not a directory: <path>")`.
- Test: `test_an_identity_directory_that_is_no_directory_is_a_configuration_error[verify --blobs | blob get]` covers a missing path and a file. Expected: exit 2, the exact sentence, nothing on stdout, no output file.
  - The control is in the same test: an existing empty directory still gives `FINDING 1: blob … cannot be opened` (exit 1) and `Error: blob … cannot be opened: …` respectively.
  - Both cases were red before the change.
  - The control could not be measured on its own against the old code, because the test failed before reaching it; at core level `test_a_blob_whose_key_is_not_at_hand_cannot_be_opened_and_the_check_goes_on` holds the same behavior.
- Pages:
  - `configuration.md` gets the sentence, an example, and that a directory lacking one identity stays a finding.
  - The `blob` row in the `cli.md` exit-code table now says "missing or invalid".

## Command-line wordings added or changed, exactly

- stderr, `redact units`: ``the payload of event <id> is not erased and may hold the same text; `previously redact event <id>` erases it``
- Error, storage: `the database aborted the operation in a conflict with a concurrent one; run the command again`
- Error, `project` and inside a `redact` unfinished sentence:
  - `projection <name> was rebuilt while this catch-up ran: it stands at version <n>, and this code declares version <m>`
  - and, for a vanished row, `… ran: it has no state row, and this code declares version <m>`
- Error, `redact` unfinished with both steps outstanding: `the redaction is recorded as event <id>, but it is not finished: <deletion phrase>, and <catch-up phrase>; run the same command again`. The single forms are unchanged.
- Error: `PREVIOUSLY_BLOB_IDENTITIES is not a directory: <path>`
- Help, `redact units`: `erase the content of the named units; the payload of the event stays`
- Alembic refusal: `refusing to downgrade below 0003_hash_version_2: the log holds events in a hash format other than 1, which cannot be verified without the version and the salts this would drop` (followed, when it applies, by `; the log holds units without content, which cannot be NOT NULL again`).
- Unchanged wordings that now come in a different order or place:
  - `redact blob` refuses a bad address before `PREVIOUSLY_DSN is not set`;
  - `append --attach` says `PREVIOUSLY_DSN is not set` before storing anything;
  - `verify --blobs` prints the chain's `FINDING` lines on stdout beside an error.

## Commits

```
3ae7038 fix: two catch-ups of one projection take turns at its state row
30c33eb fix: an erasure locks FOR NO KEY UPDATE, and an aborted transaction says so
4bbb305 fix: redact units says that the payload stays and may hold the same text
bb85f6c fix: the downgrade below 0003 refuses on any hash version other than 1
6ed8f8a fix: append --attach stores nothing before the database setting is known
b9b0cdc fix: redact attempts the deletion and the catch-up whatever the other does
44e8024 fix: RedactionIndex.of_unit names the earlier of two redactions
b2aa253 fix: verify --blobs prints the chain's findings before an error can drop them
d68b2e7 fix: an identity directory that is no directory is a configuration error
1bbc658 fix: the LogStore census prints the number its comment claims
d02aaf6 test: core refuses a blob address that is no address on its own
```

Every commit carries `Assisted-By: Claude Opus 5.5 <noreply@anthropic.com>` and no other trailer. The messages are in `WS/final-fix-code-commit-msg-1.txt` … `-11.txt`.

## Gates, after the last commit (`d02aaf6`)

```
uv run ruff check .                              -> All checks passed!
uv run ruff format --check .                     -> 69 files already formatted
uv run pyright                                   -> 0 errors, 0 warnings, 0 informations
uv run lint-imports                              -> Contracts: 6 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing    -> 1 failed, 627 passed in 82.90s (0:01:22)
make -C docs html                                -> exit 0, "The HTML pages are in _build/html."
make -C docs vale                                -> ✔ 0 errors, 0 warnings and 0 suggestions in 28 files.
make -C docs linkcheck                           -> exit 0
```

- The one pytest failure is the expected one: `tests/test_docs_typed_output.py::test_typed_test_counts_match_the_tree`, `record-your-first-event.md claims 606 passing tests, the tree has 628`. It is the only failure. Coverage is 98.38%.
- **New test count: 628 collected** (606 before, +22). The second part retypes the tutorial block; I did not touch the tutorial.

## Things the brief got wrong about the code, open points, disagreements

1. The brief says "`core` does not import … `storage`". It already does, and did before this wave: `core/append.py` and `core/redact.py` import `ChainPositionTaken` (and `append.py` imports `SourceKeyTaken`) from `previously.storage.errors`; the layers contract allows `core` above `storage`. I added no such import. The verify fix uses a callback precisely so that `core` does not have to catch storage errors.
2. The `ProjectionRebuilt` error and the exit-code row of `project` are a decision I took that the brief did not spell out. The brief asks to take the version "from the locked row" without saying what happens when it differs mid-run. Rebuilding again risks a strict livelock between two releases (FIFO lock queue), so I chose to stop with a sentence. A reviewer may prefer otherwise.
3. Version 0 as the placeholder of a first lock is a design choice too. It never commits in the code as written: the first transaction overwrites it, and a batch rolls it back.
4. Stale counts for the second part:
   - `docs/explanation/projections.md` says "sixteen in `test_projection_worker.py`" and "leaves the other fourteen green". The file now has 20 tests, and the version-mutation statement there is about the old 16. The page dates both as measurements of 2026-10-05, so I left them.
   - Neither `projections.md` nor `concurrency.md` explains the catch-up lock yet. Only the schema comment, the code docstrings and the one exit-code row say it. A paragraph there belongs to the second part.
5. `docs/how-to/rebuild-a-projection.md` (delete the state row, then run `project`) still works: a missing row becomes a first build. A `project` that is running while the row is deleted by hand now stops with `ProjectionRebuilt` ("has no state row") instead of continuing.
6. Two `cli.py` lines are uncovered: 374 (a non-seekable attachment) and 764 (`is not in the store` in `blob get`). Neither has a test in the tree at `1ec0b2e` either; they are not from this wave.
7. Permissions: no mutation was refused. Every mutation was restored at once, and `git status --short` is empty.

## Containers

- The suite's PostgreSQL and RustFS containers, and the two own containers of `test_migration_0003.py`, were started by `testcontainers` and removed by it.
- `docker ps` after the run shows one `postgres:17` that has been up for 2 days. It is not mine, and I left it alone.
- Scratch files are only under the session scratchpad: `race/`, `lockmode/`, `census.sh`, `edit_cli_notice.py`, and the gate output files.

## Round 2: after the re-review (items A, D, and the census)

Status: **DONE**. Two commits on top of `d02aaf6`; the head is `dacb067`, and the worktree is clean.

### Minor A: `redact units --help` (`1b696a6`)

- `cli.py`, `_redact_arguments`: a small local `form(name, sentence)` passes each form's sentence as both `help=` and `description=`.
  - argparse prints `help` only in the list of `previously redact --help`, and `description` only in the form's own `--help`.
  - I treated all three forms (`event`, `units`, `blob`) the same way, so that every form's own help says what it erases. The sentences are unchanged.
- Test: `tests/test_cli.py::test_each_form_of_redact_says_in_its_own_help_what_it_erases[event|units|blob]`.
  - It reads `main([..., "--help"])` output, with whitespace normalized because argparse rewraps the text.
  - All three cases were red before the change.
- `previously redact units --help` now prints, with `COLUMNS=100`:

```
usage: previously redact units [-h] --reason REASON event_id SEQ [SEQ ...]

erase the content of the named units; the payload of the event stays

positional arguments:
  event_id
  SEQ

options:
  -h, --help       show this help message and exit
  --reason REASON  why; it stays in the log for good
```

### Minor D: the notice on an unfinished `redact units` (`1b696a6`)

- `cli.py`: `_notice_payload(result, args)` prints the notice when `payload_stands`. `_cmd_redact` calls it before raising the unfinished sentence, and at the end on success. The T201 count stays at 33, re-measured.
- Test: `test_an_unfinished_redact_units_still_says_that_the_payload_stays` forges a gap, so the catch-up fails after the units are erased.
  - It asserts exit code 2, nothing on stdout, and exactly these two lines on stderr:

```
the payload of event 1 is not erased and may hold the same text; `previously redact event 1` erases it
Error: the redaction is recorded as event 4, but it is not finished: projection chronicle is not caught up (expected events 2.. above id 1, read [3, 4]; the tip is 4); run the same command again
```

  - Red before the change: the sentence came alone.
- `cli.md`, two places:
  - The notice paragraph now says the notice comes "last on success, and before the sentence of an unfinished redaction, whose exit code stays 2".
  - After the unfinished examples: "For `redact units`, the notice that the payload stays, described below, can come before that sentence."
  - The sentence prefixes that `test_docs_references` keys on are unchanged.

### The census (`dacb067`)

- The module docstring of `contract/store.py` is raw now (`r"""`). The command names the five files and ends in `| wc -l`, so it prints the number and not the names.
- It runs from the repository root, with backslash continuations that bash and fish both accept.
- Measured: a scratch script cut the four lines out of the file with `sed` and ran them unchanged. Output: `13` in bash, `13` in fish.
- Python's `__doc__` carries single backslashes, so the docstring holds the same text.

### On the controller's two mutations

The controller found that, without `.with_for_update()` in the `SELECT` and with the placeholder insert kept, `test_redact_beside_a_project_holding_rows_ends_without_a_traceback` stays green.

- That test pins the lock method as a whole, the placeholder insert included.
  - In its scenario, the `INSERT … ON CONFLICT` of the `redact` catch-up waits behind the `project`'s uncommitted upsert of the state row. That wait serializes the run.
  - The row lock of the `SELECT` is pinned by `[appended-meanwhile]` and `test_two_first_builds_build_once`.
- Its docstring says "Measured … with the lock taken out of `lock_projection_state`", meaning the whole method reduced to a plain read. That is what I measured and it is true. Read as "the `FOR UPDATE`", though, it claims more than the test pins.
- As instructed, I did not change it. A reviewer may want the docstring to say "with `lock_projection_state` reduced to a plain read".

### Gates, after `dacb067`

```
uv run ruff check .                              -> All checks passed!
uv run ruff format --check .                     -> 69 files already formatted
uv run pyright                                   -> 0 errors, 0 warnings, 0 informations
uv run lint-imports                              -> Contracts: 6 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing    -> 1 failed, 631 passed in 86.80s (0:01:26)
make -C docs html                                -> exit 0
make -C docs vale                                -> ✔ 0 errors, 0 warnings and 0 suggestions in 28 files.
make -C docs linkcheck                           -> exit 0
```

- The one failure is the expected `test_typed_test_counts_match_the_tree`: `claims 606 passing tests, the tree has 632`.
- **New test count: 632** (+4 this round: three help cases and one unfinished-notice test). Coverage is 98%.
