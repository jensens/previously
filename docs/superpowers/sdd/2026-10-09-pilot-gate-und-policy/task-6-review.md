# Review task 6: the erasure cascade (9362d0a..8cac96f)

### Spec Compliance
- Decision 5 (one `redaction` per affected call, scope units, reason `cascade of redaction <id>`, same transaction and lock): met. `_cascade` (redact.py) runs inside `once(conn)` of all three forms, writes `units_payload(..., reason=f"cascade of redaction {trigger}")` per call, and erases the tombstones in the same connection. Tests pin reason, scope, target.
- Decision 6 (all actions are read): met, `log.read_by_kind(conn, _KIND)` filtered by `action == MODEL_CALL`.
- R-4: `_target` refuses only `action == "redaction"` (payload-None rows pass, reasoning stated), stale comment fixed, policy-erasure test present (`test_erasing_a_policy_event_reads_the_previous_version_or_none`) and a model_call target test. Met.
- Spec 2.1, 4.2, 4.3 point 1: cascade, new verify finding, CLI line, docs (erasure, how-to, cli reference) all present. 30-day provider note present.
- Extra: none that matters. R-11 absence not flagged.
- ⚠️ Lock-order claim (risk 1) does not hold, see Important 1.

### Strengths
- Cascade is a single transaction: any `ChainPositionTaken` in the cascade rolls the target's tombstones back too and the whole `once` retries (risk 4 is fine: all or nothing; blob deletion stays after the transaction as before).
- Repeat erasure: `live` is empty once units are tombstones, so no second cascade (tested for event; same code path for units and blobs). A late call that names erased input is picked up by a repeat erasure, which is arguably right.
- Matching per kind is right: event erasure matches `entry.event == id` regardless of listed units; unit erasure matches the event and an overlap of units; blob erasure matches the address. Controls for "unit not read", "other event", "other blob" exist.
- `verify` check: `of_event`/`of_unit`/`of_reference` cover event, unit and blob; `_inputs_read` is only reached after `_model_call_problem` passed, so its casts are safe. Fires only for calls with live units, which is why it stays green after every cascade (checked by `verify(storage) == []` in each cascade test). Two tests fire it (unit/event and blob), plus a green control.
- Malformed `inputs` do not stop an erasure and `verify` still reports the call (tested).
- Counts: block has 1249 dots, equals `collected 1249` = 1233 + 15 + 1.

### Issues

#### Critical
None.

#### Important
1. **Lock order claim is false; a deadlock exists (risk 1).** `redact.py` module docstring says "two erasures cannot each hold what the other waits for", and the report says "no cycle possible". Counter-case: A = `redact event 1` (call 5 read it), B = `redact event 5` (the call itself is the target). A locks row 1, B locks row 5 (phase 1). A writes its redaction at position N; B tries to write at N and waits on A's uncommitted unique-index entry. A then reaches `_lock_ascending` for call 5, held by B. Cycle: A waits for the row lock of 5, B waits for A's chain position. PostgreSQL will abort one with a deadlock error; `retrying` retries only `ChainPositionTaken`, so the user sees an error (rolled back cleanly, no corruption). The ascending-id argument only orders the row locks among themselves; it ignores the chain position that is taken between the two phases. Fix options: take the call locks in phase 1 together with the targets (find the calls once unlocked, lock the union ascending, re-read under lock), or treat the deadlock error as retryable, or at minimum correct the docstring and the `ruling` text and state the limit (narrow: needs a concurrent erasure of the call itself). No test exists; not stress-tested as the report admits.
2. **Tutorial block: command and output disagree (risk 5).** The block under `$ uv run pytest` now contains the `tests coverage` table and `Required test coverage of 90.0% reached`. `uv run pytest` prints no coverage: `pyproject.toml` has no `addopts` with `--cov` (only the gate command `pytest --cov --cov-report=term-missing` does). The pre-change block had no table. The block is one run's lines (seed, collected, ordering, dots sum to 1249, `1249 passed`), so the "placeholder then replace" is fine as far as the numbers go, but it is the output of a different command than the one typed above it. Either type the command as `uv run pytest --cov --cov-report=term-missing` or retype the block from a plain `uv run pytest` run. `tests/test_docs_typed_output.py` guards only the `N passed` figure, so no gate sees this. Also the sentence after the block ("Your run prints one line this page leaves out, a `rootdir:`") says nothing about the table, which would mislead a reader whose run lacks it.

#### Minor
1. `cli.py:1146-1175`: on the "unfinished" error path the `cascaded:` lines are not printed. Reported honestly; a rerun finds the calls covered and prints nothing, so the user never learns which calls were cascaded. Acceptable for a pilot but worth an open point in the map.
2. `_cascade` blob case (redact.py): matches `inputs[].blobs` containing the address without checking that the entry's event is one of the redaction's events (report notes it). Over-cascade is the safe direction; fine, but the comment at the lambda should say so.
3. `verify._inputs_read` accepts `bool` as a unit (`isinstance(u, int)`); harmless.
4. Cascade silently erases only `live` units; documented.

### Assessment
**Needs fixes.** The functional behavior (risks 2, 3, 4) is correct and well tested; fix Important 1 (wrong concurrency assurance with a real, if narrow, deadlock; correct the docstring at minimum, ideally lock the calls with the targets) and Important 2 (retype the tutorial block so the command matches the output).
