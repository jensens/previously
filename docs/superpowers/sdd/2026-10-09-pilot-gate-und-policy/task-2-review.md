# Review Task 2 (377f713..7c662ca)

**Verdict: Approved.** No Critical or Important finding. Three Minor points.

### Spec Compliance
- All brief interfaces are present with the stated signatures (policy.py:703-1138). R-1 holds: `LOCAL_ONLY` is in core/policy.py:718 and `policy show` lists it (cli.py:1587).
- Refusals: missing circle, `project:` scope, unknown scope, empty/`any`+other regions, empty or blank sentence, dot-less domain (policy.py:869-947). Check and write share one transaction via `retrying` (policy.py:978-986).
- Refusal happens before the question, return 2, one sentence (cli.py:546-548, test_cli "nowhere" test).
- `show [--at]` (R-3, `--at`): naive time gives 2 (test_cli at test). Revoke is `--revoke` and tested. The supersede, revoke and at tests are measured.
- Exit codes: `nothing written` returns 1 and is documented in the exit-code table as column 1; consistent with how `verify` uses 1.
- verify: `check_payload` hooked at verify.py:1193; the finding text matches the cli.md quote. The old bare `{"action":"policy"}` tests were adjusted legitimately.
- Counts hold: test_policy has 29 tests (matches 29 dots), test_cli +9 (39 dots), total 1080 -> 1118. T201 36 -> 40 matches the four new prints. The wording `set and show the processing policy` matches the table.
- Assurance tests have a measured control beside them: `n` vs `y`, refused vs accepted, revoked statement still in the chain. The report claims three mutations (replace, circle check, `at`); the tests exercise each of them directly.
- ⚠️ I did not re-run the mutations or the gates.

### Strengths
- Refusal is separated from writing (`refusal`/`normalized`/`key_of` are public, no private reach from tests).
- `read_policy` is tolerant (skips tombstones and malformed forms), while `verify` reports them.
- Canonical sorted sets are tested with swapped input.
- Domain case normalization closes a real revocation hole and is tested.
- The typed pytest block was retyped whole, and the progress-line counts check out.

### Issues
**Minor**
1. docs/reference/cli.md (refused list, "`--regions` with no region"): `--regions` is `nargs="+"` (cli.py:461), so a bare `--regions` is an argparse usage error, not the "one sentence" `PolicyRefused`. Exit is 2, but the text and shape differ. Fix: drop the item from the list or say argparse refuses it.
2. policy.py `read_policy` ignores nothing about circles revoked later: memberships of a revoked circle stay in `Policy.memberships`. Not in the brief; Task 3 (membership lookup) should decide whether to filter by `circles`. Worth a note for Task 3.
3. tests/test_cli.py:1263-1269: `_action_count` imports inside the function and takes `db: object` plus `isinstance`; it works but is clumsier than a top-level import. Style only.

### Assessment
Task quality: Approved. The implementation matches the brief and the rulings; the tests are measured against mutations with controls, and only documentation and style nits remain.
