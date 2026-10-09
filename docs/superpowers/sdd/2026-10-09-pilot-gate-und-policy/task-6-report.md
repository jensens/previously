# Task 6 report: the erasure cascade

Commit 8cac96f on worktree-pilot-gate.

## What
- `core/redact.py`: `_cascade` (find model calls, lock, one `units` redaction per call with live units, reason `cascade of redaction <id>`), called in `redact_event`, `redact_units`, `redact_blob` after the tombstones, same transaction. `Redacted.cascaded`. `_target` refuses only payload.action == "redaction"; comment fixed with the reason.
- `core/verify.py`: new finding `model_call <id> keeps the result of erased input` (calls with live units whose read event/unit/blob is covered by a redaction index entry); checked in `reconcile`.
- `cli.py`: prints `cascaded: model_call <id>` per id after the first line (stdout). Not printed on the "unfinished" error path.
- Docs: erasure.md (cascade, policy event, 30 days at Anthropic), erase-something.md, cli.md; tutorial test block retyped.
- Tests: tests/test_cascade.py (15), one gate-based test in tests/test_gate.py.

## RED / GREEN
RED: 12 failed, 2 passed (first run, `Redacted.cascaded` missing etc.). GREEN: 15 passed; full suite 1249 passed.

## Mutations (tests/test_cascade.py + test_gate.py, control 75 passed)
- cascade omitted (calls = []): 7 failed.
- cascade erases without own redaction: 6 failed (incl. verify-based).
- verify check disabled: 2 failed (the two "keeps the result" findings).
- refuse every action again: 2 failed (policy, model_call target).

## Lock order
Phase 1 as before (targets ascending). Phase 2: after the lock, model calls read via read_by_kind and locked ascending with `_lock_ascending`. A call reads only earlier events, so a cascaded call id is always higher than the lock it follows from; no cycle possible (reasoned, not stress-tested).

## Gates
ruff check, ruff format --check, pyright, lint-imports, pytest (1249 passed; redact.py, verify.py 100%), docs html/vale/linkcheck all green.

## Notes / concerns
- T1-a: the full-run progress block could not be green before the count matched, so I set "1233 passed" to "1249 passed" once as a placeholder, ran the one full `pytest --cov` (green), and replaced the whole block with that run's lines (rootdir line dropped, as the page says).
- Not transitive: a model call that read another call's result is not cascaded; verify reports it. No task does this.
- A command that stops with the "unfinished" error does not print `cascaded:` lines; the rerun finds them covered.
- Cascade names only units that still have content; all of them in the normal case.
- Finding all calls reads every action (decision 6); index is an open point for the map.
- Blob cascade matches `inputs[].blobs` containing the address, without checking that the entry's event is among the redaction's events.

## Fix round 1

Changes
- R-12: `redact.py` now finds the calls first (`_calls`, an unlocked read of all actions) and locks them with the targets in one ascending round (`_lock_ascending` over target, sharing events and calls) before `write_action`; `_cascade` takes the call ids and reads their units under the lock. Module docstring rewritten with the cycle and why one round avoids it (the known race for a call appended after the read is named). `redact units` now also uses `_lock_ascending` for target plus calls.
- Test `test_an_erasure_waits_at_the_row_lock_of_the_call_before_it_takes_a_chain_position`: B (erasure of the call) is held holding the call's row lock; A (`redact event 1`) runs in a thread; the test waits until PostgreSQL shows a lock wait, then B writes its redaction at the tip and commits. Both finish, no error, `verify` green. It proves the order for this pair only, not every interleaving.
- Mutation: call locks moved back after `write_action` -> red (A or B ends with `TransactionAborted`, the deadlock). Control (restored) green.
- R-11: `gate._decide` denies any event whose kind is not `observation` with `the event is not an observation` (checked before the erased case); `cli.md` names the reason. Test `test_an_action_is_denied_as_input_without_a_prompt` (policy event and model_call via `call`, `gate try <policy event>` exit 2 with the message, an observation passes first, no extra request). Mutation (check removed) -> red; restored green.
- Minor: comment at the blob lookup in `redact_blob` says over-cascading is the safe direction and why.
- T1-b: tutorial block retyped from one plain `uv run pytest` run (1251 passed); the only edits were the placeholder count "1249 -> 1251" before that run (so its docs test could pass) and dropping the `rootdir:` line the sentence below the block already names. No coverage table. The sentence after the block still fits.

Gates (once, after the fixes): ruff check, ruff format --check, pyright, lint-imports (8 kept), `pytest --cov --cov-report=term-missing` 1251 passed, docs html, vale (0 errors), linkcheck all green. Coverage: redact.py and verify.py 100%; gate.py line 159 is uncovered (not touched by this task's code path).
