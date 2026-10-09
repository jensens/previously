### Finding Verdicts
1. ADDRESSED. src/previously/core/redact.py `redact_event` finds calls via `_calls` (unlocked read), then one `_lock_ascending([event_id, *sharing, *calls])` before `write_action`; `redact_units` and `redact_blob` do the same. Docstring states the cycle and the single-round remedy. tests/test_cascade.py `test_an_erasure_waits_at_the_row_lock_of_the_call_...` holds the call's row, waits for a lock wait, has B write at the tip; under the old order (A takes a position, then waits for the call) B's write would wait on A's position, a cycle. Assertions are sound (the call has two units, B erases both, so cascaded == ()).
2. ADDRESSED. docs/tutorials/record-your-first-event.md: the block is now plain `uv run pytest` output with no coverage table. Count 1251 = 1249 + 1 cascade test + 1 gate test, consistent with the tree. The `rootdir:` omission is named in the sentence below the block, and that sentence predates the fix. Fixing the seed placeholder before the run does not make the block stitched.
3. ADDRESSED. src/previously/gate/gate.py `_decide` denies on `kind != "observation"` with NOT_OBSERVATION; docs/reference/cli.md line after the erased-event sentence quotes it; tests/test_gate.py `test_an_action_is_denied_as_input_without_a_prompt` covers policy event, model_call, CLI exit 2 with the stderr message, no extra provider request, and an observation passing earlier in the same test.
4. ADDRESSED. Comment at the blob-cascade call site in `redact_blob` explains over-cascading as the safe direction.

Race note: the docstring statement (a call appended after the read goes unlocked and uncascaded, same race as the blob section, a later erasure finds it) is truthful. `verify` would report it: verify.py ~line 463 emits `model_call <id> keeps the result of erased input`.

### New Breakage in the Fix Diff
None found. Minor: one comment line in `redact_event` ("locks only its target and the calls, and") is long and reflows oddly. Ruff passed per the report.

### Out-of-Scope Observations
The docstring could say that verify reports the raced call. Optional.

### Verdict — all findings addressed: yes
