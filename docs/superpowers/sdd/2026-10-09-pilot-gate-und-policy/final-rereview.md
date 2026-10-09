# Final re-review of the fix wave (b9276e7..f08ca34)

Method: report read in full, diff read in passes (the code files in full, the spec header, design-records and the tutorial block), no suite run. Checks made: map count (awk gives 183), spec commits (da6c574 and 5a2fa6f both touch §8 Punkt 3, 26f4cb4 touches no spec text), R-6, R-7 and R-11 text in progress.md.

### Finding Verdicts
- Code I-1 (R-14): ADDRESSED. core/redact.py `append_call` and `_lock_round`, gate/gate.py `call`/`_ok`.
- M-1: ADDRESSED. core/verify.py `_form_finding` ("policy event has units").
- M-2: ADDRESSED. pyproject.toml:106 (fifty-one, plus the note on the `cascaded:` line).
- M-3: ADDRESSED. core/action.py `write_action_at`, core/policy.py `set_policy`.
- M-4: ADDRESSED. cli.py `_fallback_lines` (chosen is None) and `_cmd_gate_try` (outcome error).
- M-5: ADDRESSED. cli.py `--storage` required.
- M-6: ADDRESSED. Citations in tests/test_gate.py name the plan.
- Docs I-1: ADDRESSED. Spec header: amendments "da6c574, 5a2fa6f" (matches git), the sentence that §2.5 Punkt 5 stays unamended, R-6 and R-7 stated as departures that match the rulings, six bullets, body untouched, design-records.md says "six places" (no other "four places" remains).
- Docs I-2, I-3, the factually wrong minors, and the four map points: ADDRESSED as reported. Not re-measured; the diff shows the blocks and text. Landkarte count 178 to 183 confirmed.

### Named risks
1. Locking: `append_call` locks the input events with `_lock_ascending` (same `lock_event`, FOR NO KEY UPDATE, sorted). The call row does not exist yet, so the gate waits only on rows it takes in ascending order. Its other wait is the chain position, held by writers that have already finished locking, so no cycle with redact's round. Redact's second round locks only newcomers, whose ids are above all first-round rows. No deadlock found. The cascade uses `_cascade` with trigger = `redaction.id` (the redaction event id, the same value redact passes), giving reason `cascade of redaction <id>`, one redaction of units naming the live units; verify's three questions are the ones `_erasure_of` asks.
2. Second read: gate first, redact waits, then the second read finds the call and locks it, and the cascade runs once from redact (the gate saw no erasure). Redact first, the gate waits, re-reads the index, and cascades itself; redact's cascade list cannot contain the call (the gate cannot commit while redact holds the input lock), and if it did, `_cascade` finds no live units. No double cascade. Covered both ways by tests with mutations A and B.
3. M-3: tip read first, check, write at that tip. A commit in between takes the position, the insert raises ChainPositionTaken, `retrying` re-runs `once` including the check. Correct. Test with a measured mutation.
4. M-4: correct; denial, explain-with-no-choice and `error` print no line; local answers (including schema_invalid) keep it.
5. Frozen spec: truthful, see Docs I-1.
6. Typed output: the tutorial block is one run (1267 items, 1267 passed, seed 1318060385), consistent with the count guard. The how-to blocks are said to come from one replay.

### New Breakage in the Fix Diff
None found.

### Out-of-Scope Observations
- `append_call` treats a redaction that already existed when the gate read its input as an erasure of the call too (cascades). Arguably right, since the answer is then derived from erased input; not a defect.
- Mutation C (lock removed) is caught only by timing, not by verify, as the report says; the lock itself has no direct assertion. Acceptable.
- `policy provider --revoke` now also requires `--storage` (mapped in the landkarte).

### Verdict
All findings addressed: yes. Ready to merge: yes (docs I-4, shipping the ledger, remains the controller's).
