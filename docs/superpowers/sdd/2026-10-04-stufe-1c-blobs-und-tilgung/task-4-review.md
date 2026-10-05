# Task 4 review: d95882d..746ea4b

Reviewer pass on 2026-10-05. The diff file (1989 lines) was read in three passes: docs and `cli.py` (1–700), `cli.py` rest, `store.py`, `chronicle.py`, `postgres.py`, `schema.py` and the first CLI tests (700–1350), the remaining tests (1350–1989).
Focused checks outside the diff, one per named risk:

- *A command uses or fails to close the storage after the `with`:* `grep` for `_storage` over `src` and `tests` — ten sites, all in `cli.py`, all `with _storage() as storage`; no test calls `_storage`. `_cmd_show` read in full (`cli.py:366-409`): its `return 0` and `break` sit inside the `with`, so both close. `read_chronicle` and `read_source_stats` return lists, so the rows used after the `with` in `chronicle` and `stats` are materialized.
- *`close()` and the two execution-option views:* SQLAlchemy's `OptionEngineMixin.pool` is a property proxying `self._proxied.pool`, so `dispose()` on the base engine reaches both views, and the views pick up the recreated pool afterwards. The `close` docstring ("can still be used") is true.
- *`main` catches what `_catch_up_after` re-raises:* `cli.py:648` catches `(PreviouslyError, StorageError)` and returns 2.
- *The forward-redaction guard agrees with `verify`:* `core/verify.py:404` reports `target >= redaction.id` as `redaction names a target that does not exist`, so the comment at `chronicle.py` "a finding of `verify`" holds. `read_index` (`core/redaction.py:215`) reads only `kind = 'action'`, which matches the `kind` filter in `erasures`.

No test was run.

### Spec Compliance

- ✅ Spec compliant for (a) and (b), with one false page statement and one untested assurance listed under Important.
  - Interfaces: `delete_chronicle(conn, event_id, seqs: Sequence[int] | None)` (`contract/store.py:124`, `storage/postgres.py:527`), `erasures(batch) -> list[tuple[int, tuple[int, ...] | None]]` pure and in chain order, `version = 2`, `write` inserts then deletes, `redact` catches up after `written` and after `already` — all as specified.
  - All six tests of the brief exist with the named expectations; the property test draws `_Redact` as a third step; both renames with new docstrings are done.
  - The four mutations of the brief were reported with red tests and the named green controls (`test_a_redacted_event_leaves_no_chronicle_row`, `test_redact_event_prints_the_redaction_and_show_names_it`); the version-1 test is `test_project_rebuilds_a_chronicle_built_at_version_1`.
  - Handed-over sentences: `projections.md` section rewritten, `erasure.md` sentence corrected, the `chronicle.py` comment removed, the worker test renamed. Nits: the `{ref}` in `_cmd_redact` replaced by the argument itself, the tombstone sentence in `redact.py` and `concurrency.md` corrected, "forged row" on `cli.md` reworded.
  - Error wording matches the table (`the redaction is recorded as event <id>, but it is not finished: …; run the same command again`), exit 2, one line on stdout, no citation in the message.
  - Ruling T4-a: cause measured before the change (peak 93 of 100, 1 → 31 → 1 after `gc.collect()`), release lives in `storage` (`PostgresStorage.close`) and `cli` calls only that name, lifetime tied to a context manager covering success and exceptions, the NullPool alternative measured (≈0.55 s vs ≈0.75 s; the docstring figure matches the five reported runs, means 0.547 and 0.756), a test with 33 in-process `main()` calls including an exit-1 and an exit-2 command, two mutations red with controls green, three fixed-order runs reported green.
  - Extras, judged: the `redaction.event >= event.id` guard is right — without it a forged forward redaction deletes rows in a rebuild and none incrementally, and it agrees with `verify`. Forging a real gap instead of a wrapper is right — it avoids reaching into the private `_storage` and exercises a genuine `ProjectionGap`; its weakness is on the reference page, not in the test (see I2).
- ⚠️ Cannot verify from diff: the commit trailers (`Assisted-By:`, no `Co-Authored-By`) of `600f757` and `746ea4b` — the diff file carries no messages.
- ⚠️ Cannot verify from diff: the three fixed-order runs and the mutation outputs are claims in the report; the tutorial block is consistent with them (408, per-file counts 11 and 15 match the page's "eleven" and "fifteen").

### Strengths

- The core argument — a unit without content gives no row, a redaction deletes rows, so reading the target before or after its redaction ends alike — is stated once in the module docstring, once on the page, and walked in `test_incremental_equals_rebuilt_with_redactions_before_and_after_the_worker`, which covers both orders and a unit redaction in one log.
- `erasures` is pure, small, and its negative cases (malformed, blob, other action name, observation with a redaction-shaped payload, `None` payload, forward target) are each pinned in one pure test.
- `delete_chronicle` distinguishes `[]` from `None` and the test says why that matters.
- The connection fix is the right shape: one context manager at the place that opens the storage, nested `with` ordering closes the transaction before the pool, no SQLAlchemy in `cli`, and the cost of the alternative was measured instead of argued. The connection test disables the collector so a missing release cannot be hidden by a collection, and the success-only mutation was measured red, so the error path is really covered.
- Stale numbers were remeasured and dated rather than edited (`projections.md`, `test_incremental_equals_rebuilt` docstring), and the counts agree with the typed tutorial run.

### Issues

#### Critical (Must Fix)

None.

#### Important (Should Fix)

**I1. `projections.md` promises a visible rebuild that `redact` now performs silently.**
`docs/explanation/projections.md:223` says "the first `project` after the upgrade rebuilds it and says `rebuilt: version 1 -> 2`".
Since `_cmd_redact` runs `catch_up` over `PROJECTIONS` (`src/previously/cli.py:440` (`_catch_up_after`)), a `redact` issued before the first `project` after an upgrade does the version-triggered rebuild itself and prints nothing about it (`docs/reference/cli.md:78`: "prints nothing about it"); the following `project` then says `up to date`.
So the sentence is false in a reachable order, and it also runs against the same page's argument at `projections.md:200` that `project` names the path so "a version-triggered rebuild stops being invisible" — `redact` is now a second path that rebuilds invisibly (and on a large log, slowly, with no word on why).
The brief's own sentence ("der erste `project` … sagt es") carries the same gap, so this is partly plan-mandated.
Fix: either say "the first catch-up after the upgrade — `project` or `redact` — rebuilds it; only `project` says so", or let `redact` report a rebuild on standard error (stdout stays one line).

**I2. The reference page shows a failure whose advice it then says works, and for that failure it does not.**
`docs/reference/cli.md:83-87` shows the error for a gap in the log (`expected events 2.. above id 1, read [3, 4]; the tip is 4`) and continues: "Running the same command again finds the target covered, prints `already redacted by event 42`, and catches up."
For a gap that is false: the second run hits the same `ProjectionGap` and fails with the same message, and the test's own docstring (`tests/test_cli.py`, `test_a_catch_up_that_fails_after_the_redaction_says_what_is_outstanding`) says nothing in the write paths can produce a gap — it is not transient.
The wording "run the same command again" is fixed by the table; the example and the sentence after it are the implementer's.
Fix: show a transient failure as the example (a server that does not answer), or qualify the sentence ("once the cause is gone, running the same command again …").

**I3. The insert-before-delete order in `ChronicleProjection.write` is an assurance without a test that fails.**
`src/previously/core/projection/chronicle.py:121-127` states that inserting before deleting means "the batch boundaries … cannot change the result" for a target that still carries what its redaction erased (an order without its execution).
No test arranges that case: every redaction in the new tests and in the property is written by `core.redact`, which sets the tombstones in the same transaction, so the target either has rows from an earlier batch or derives none — and in both cases the order inside `write` makes no difference.
Swapping the two lines (delete, then insert) would therefore leave every test green, by this reading (not run; the reviewer is read-only).
The project rule is that an explicit assurance needs a test measured to fail with a control beside it.
Fix: one worker test that forges an order without its execution (append, project; write a redaction whose target keeps its content, for example by restoring a unit's content with raw SQL after `redact`, salt handled per ruling P-1 of the 2026-10-04 stage 1c plan), compares incremental against rebuilt, and is measured red with the two lines swapped.

#### Minor (Nice to Have)

**M1. The connection test can race backend shutdown.**
`tests/test_cli.py`, `test_main_releases_the_connections_it_opened`: `after <= before` with no allowance is read from `pg_stat_activity` immediately after the last `dispose()`.
A backend leaves `pg_stat_activity` only when it has processed the terminate and exited, which is asynchronous to the client closing its socket.
It was measured green, so this is a latent flake risk, not an observed one; a short bounded poll until the count settles would remove it without weakening the bound.
The test also relies on engines holding reference cycles (that is what makes `gc.disable()` meaningful); if a later SQLAlchemy freed them by refcount alone, the test would stay green without `close`. The docstring could say so.

**M2. A touched docstring keeps an unqualified ruling citation.**
`src/previously/cli.py:160` (`_storage` docstring, moved from a comment and rewritten) and `src/previously/storage/postgres.py:696` (`from_dsn`, extended) both carry a bare `ruling T9-a`.
`CLAUDE.md` says "Whoever touches one qualifies it"; if the plan is unknowable (the stage 1a ledger is lost), say that, or leave the label and note why it stays bare.

**M3. The error sentence nests the inner error's semicolon.**
`src/previously/cli.py:440` (`_catch_up_after`) produces `… (expected events 2.. above id 1, read [3, 4]; the tip is 4); run the same command again`.
It matches the table, but the inner semicolon makes the parenthesis read like the end of the sentence. Acceptable; noted only.

**M4. "Behind it in the chain" is ambiguous.**
`docs/explanation/projections.md:220`: "A redaction that names an event behind it in the chain takes nothing" — "behind" can read as "earlier". The code comment says "a later event"; the page should too.

**M5. `_catch_up_after` stops at the first failing projection.**
`src/previously/cli.py:440` (`_catch_up_after`) raises on the chronicle and never tries `source-stats`. Harmless today (both read the same log and a gap fails both), and the message names only the projection that failed, so nothing is claimed falsely.

### Assessment

**Task quality:** Needs fixes
**Reasoning:** The code is correct and the connection fix is well measured and well bounded, but one page sentence is false in a reachable order (I1), one reference example promises a remedy that fails for that very example (I2), and the comment in `write` asserts a property no test can fail on (I3).
