# Task 3 re-review: fix round 1 (da30de4..b37aeb6)

- Issue 1 (no-content test): RESOLVED. tests/test_access.py `test_the_search_for_content_finds_it_in_a_stored_payload` puts a mail wording into `arguments` (nested, and as a key `key4711`) and into `Withheld.reason` of a real `record_access` call, reads the stored payload with `_payloads(db)` and asserts the exact set of strings found. The normal-case test keeps asserting `_found_in(payload) == []` on the stored payload, now with `circles` filled. Caveat, inherent: the normal case still only pins the inputs it chose. The control now shows the search is not blind on the real payload.
- Issue 2 (unhashable kind/reason_code): RESOLVED. access.py:138-142 `_in` tests `isinstance(str)` before `in`; used at :164 (reason_code) and :181 (kind); outcome checked `isinstance(str)` first (:210). Measured: a forged row with `kind={"a":1}`, `reason_code=["x"]` and `outcome={"a":1}` returns a finding from `access_problem` and `None` from `parse_access`, no TypeError. The test (test_access.py ~265-282) adds the forged variants and asserts `read_access` and `gaps` survive and show only the good row. `uv run pytest tests/test_access.py -q`: 14 passed.
- Issue 3 (cli.md gaps example): RESOLVED (point e). docs/reference/cli.md ~l.855-860: sentence "gate lines first, MCP lines after, each group sorted"; the example shows circle:xz, source:email, mcp:circle:h_da, which matches gaps.py:104 (`[sorted gate] + _mcp_gaps`, itself sorted at :134).
- Issue 4 (R-3 circles on Delivered): RESOLVED. `Delivered.circles` added, written in `_payload` (access.py:~93), form-checked in `_entry_problem` (keys exactly event/units/circles), parsed in `parse_access`, matched in `_names_circle`; module docstring, cli.py help text and cli.md (option row, "payload holds" sentence, verify form) updated; `test_a_delivered_event_of_a_circle_is_found_by_that_circle` (get_event by id, circle in neither arguments nor withheld) and the sketch test carry the field.
- Minor 5 (lenient parsing): RESOLVED. `_is_list_of(..., _is_int / _is_str)` rejects bools and non-lists for units and circles; `reason` must be text; entries need exactly their keys; client, policy, outcome, era types are checked; test cases cover each.
- Minor 6: named only, not fixed. Fine.
- Minor 7 (OK/ERROR rename): RESOLVED. `ACCESS_OK`, `ACCESS_ERROR`, `ACCESS_OUTCOMES` (access.py:39-41); no remaining importer of the old names.

Judgement points:
- (a) `era`: required key, value may be null or text (access.py:215: `"era" not in payload or not (None or str)`); `_payload` always writes it (:113). Not a defect.
- (b) see Issue 1.
- (c) see Issue 2; measured.
- (d) tutorial pytest block: measured with a script. The progress lines sum to 1345, every cumulative percentage equals int(100*n/1345) (0 mismatches), "collected 1345" equals "1345 passed", and 181.50 s = 0:03:01. Consistent as one run.
- (e) see Issue 3.

## New issues
none found in the touched lines. Minor observation only: the stored-row `era` is now mandatory, so any `mcp_access` written before this commit without the key would be reported by verify; the feature is unreleased, so no action.

## Verdict
Approved
