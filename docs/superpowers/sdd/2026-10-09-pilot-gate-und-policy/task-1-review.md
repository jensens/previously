### Spec Compliance
- ✅ `core/action.py`: constants, `KNOWN_ACTIONS`, `write_action`, `append_action` as specified (action.py:292-360). Kind `action`, key `None`, `occurred_at = recorded_at`, tip chain, retry on `ChainPositionTaken`.
- ✅ `redact._write` replaced by `write_action(..., (), recorded_at=...)` (redact.py three sites); `REDACTION` moved, `redaction.py` imports it.
- ✅ `derive` filters `kind != "observation"` before units, version 3 with docstring (chronicle.py:51, 105-130).
- ✅ `verify`: unknown name is a finding (verify.py:773-774); `name` is always bound there, since the `except` returns.
- ✅ Tests: test_action, test_verify (teleport red; policy/model_call control), test_chronicle (action not shown, observation shown, v2->v3 rebuild equals fresh). Mutations M1/M2 reported with controls.
- ✅ projections.md section added; cli.md and tutorial updated.
- ⚠️ Cannot verify from diff: the six gates and the mutation results are the implementer's claim; no RED run before the code (admitted).
- Extra (acceptable): public `retrying` in action.py, shared by `redact` and `append_action`. It is a sound way to avoid duplicating the loop, but the brief did not name it.

### Strengths
- The retry loop is moved, not copied; redact's tests still cover it.
- The v2->v3 test builds the stale table by hand and compares it to a fresh build. That is a real behavioral check, not a presence check.
- Known-name control sits beside the `teleport` test; the `test_redact` expectation is adapted, not weakened.
- Docs explain why the filter exists (units of model calls) and name the test.

### Issues
**Important**
- docs/reference/cli.md:~487-500 (the verify findings table): the new finding `unknown action "<name>"` is not documented. The table lists `action has no valid form` and every other finding, and the project rule is that docs follow code in the same change. Add a row (condition: an event of kind `action` whose `action` name is not `redaction`, `policy` or `model_call`; event: the action). Ideally also pin the quoted message in a docs test.
- docs/tutorials/record-your-first-event.md (typed block): by the implementer's own report the numbers (seed, duration, order, collected count) come from an earlier full run, with one failure typed as `.`. This is a hand-edited measurement, against "type it last, once the tree has stopped moving". The total of 1079 matches the later green run, so the guarded number is right. Retyping from one final run at the end of the whole plan (not per task) would honor the rule; at minimum, make sure that retype happens in the last task.

**Minor**
- docs/how-to/rebuild-a-projection.md:36-40: "For a chronicle at version 2, the line becomes `version: int = 3`" is now stale, because the chronicle stands at 3. Use a generic example or "4".
- action.py `retrying` docstring dropped the reasoning of the old `_retrying` (position lost at `insert_event` before any tombstone is set, so the rollback undoes only the lock). That argument is specific to redact and now lives nowhere; keep it as a comment in redact.py at the `retrying(log, once)` call sites.
- action.py:356 `iso_utc(recorded_at)  # fail early if naive`: no test covers a naive datetime to `append_action`, so the early failure is an untested assurance (CLAUDE.md "needs a test measured to fail"). Add a test, or drop the line if `prepare`/`link` already rejects naive values.
- tests/test_chronicle.py:914-915 reads columns by index (`r[0]`, `r[1]`, `r[4]`); fragile if column order changes. Select named columns.
- tests/test_action.py has no test for the `ChainPositionTaken` retry through `append_action`; coverage is indirect via redact. Acceptable, but a one-case test with the existing contested-log helper would be cheap.

### Assessment
Task quality: Needs fixes
Reasoning: The code and tests are correct and well-mutated, and the refactor is clean. The undocumented new verify finding (docs must follow code) and the hand-assembled tutorial measurement should be fixed before this is called done; the rest is polish.
