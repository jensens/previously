# Task 3 review: the access log (bde877b..da30de4)

## Spec Compliance
- OK: record/read/filter/verify form/gaps/CLI exist with the briefed interfaces (access.py:575-796); `mcp_access` in KNOWN_ACTIONS (action.py); no units (append_action with ()), not in the chronicle (test_access.py:1166).
- OK: `policy gaps` gate part unchanged. gaps.py has no early return before the MCP part, the gate list is built as before, `origin` defaults to "gate" and the gate lines print without prefix (cli.py:427).
- OK: tutorial pytest block is one run's output. Measured: the 53 progress lines sum to 1343 and every cumulative percentage matches int(100*n/1343) (0 mismatches); 1331+12 = 1343; 179.16 s = 2:59. The provisional edit of the count only enabled the run whose output was then pasted; the block itself is consistent.
- FAIL: no-content test does not do what it claims (Issue 1).
- FAIL: form check can crash instead of report (Issue 2).
- FAIL: R-3 gap (Issue 4).
- Doc example of `policy gaps` is wrong (Issue 3).

## Strengths
- Mutation of the form check and of the gaps MCP part were measured, each with a green control; the `rule`-is-no-gap control test is a real control.
- Seven separately pinned broken forms, each tied to the event id; units case and stored-payload-equals-sketch test.
- Gate output kept byte-identical by prefixing the origin in the CLI only.

## Issues
### Critical
none.

### Important
1. tests/test_access.py:1137-1162 (named risk 1). The test feeds `record_access` inputs that contain no content (`arguments` and `reason` are fixed strings, the delivered/withheld entries are ints). `record_access` never sees an event, so the assertion cannot fail by any change to it. A unit text placed in `reason` or `arguments` would NOT be caught, because the test never puts one there. The control only proves the search function finds a string in a dict it was handed itself, which is not the control the rule wants (a red case on the real payload). The walker itself is fine (keys included, nested lists/dicts, ints skipped as non-strings). No mutation was measured for this test. Fix: build the payload with one wording in `reason`, one in `arguments`, and assert that the search finds it (the control, on the real stored payload); then assert absence for the normal case. Or, better, state what the guard is: the test as written pins only the inputs the test chose. Measure it red by putting MAIL_TEXT in `reason`.
2. src/previously/core/access.py:673 and :689 (named risk 2). `named.get("kind") not in KINDS` and `entry.get("reason_code") not in REASON_CODES` hash the value. A forged `kind` or `reason_code` that is a dict or list raises `TypeError: unhashable type` (checked). `verify` then crashes instead of printing a finding, and `read_access`/`gaps`/`previously access` crash on the same row through `parse_access`. verify exists for forged rows, so this is the one input it must survive. Fix: test `isinstance(x, str) and x in SET` first; add both variants to `test_verify_finds_a_broken_form` (the tests cover unknown values but only strings). Also unchecked and untested: `client` not a string, `policy` not a dict, `era` of another type, a non-dict `withheld` entry. The docs promise "known fields only" but only the top level is checked (call, entries may carry extra fields, e.g. content smuggled in `withheld[].text`); either check them or say top level in cli.md.
3. docs/reference/cli.md (policy gaps section, new example). The text says lines are sorted by name and the example interleaves `circle:xz`, `mcp:circle:h_da`, `source:email`. The code prints the gate part sorted, then the MCP part sorted (gaps.py `+ _mcp_gaps`), so `mcp:` lines come last, after `source:email`. Retype the example from a real run, and say "gate lines first, then the MCP ones, each sorted".
4. R-3 (named risk 4), access.py:587 and :763. `Delivered` has no `circles`, so `_names_circle` finds only `arguments.circle` and withheld circles. `previously access --circle X` misses every `get_event` call that delivered an event of X. The implementer disclosed it as a concern, but the ruling makes it a required fix: add `circles: tuple[str, ...]` to `Delivered`, write it in `_payload`, parse it (with a form check), extend `_names_circle`, the `--circle` help text, cli.md (option row and the "payload holds" sentences, and the module docstring "nothing else"), and `test_the_stored_payload_is_the_sketch_of_the_concept`. Then a test with a delivered event of a circle, red before and green after. Check concept §5 and the no-content binding: circle names are policy names, so they stay allowed.

### Minor
5. Withheld/Delivered `circles`, `units`, `reason` are read leniently (`_strings`, `_ints`, `_text`) and `_ints` accepts bools; verify does not report a malformed `units` or `circles`. Either validate or accept it knowingly.
6. Report says RED was shown by hiding access.py (collection error); that is not a red test but a missing module. Not strict TDD, as the report admits; noted only.
7. `OK`/`ERROR` and `OUTCOMES` in access.py duplicate names in action.py with a different meaning; an import of both would collide silently. Rename to `ACCESS_OUTCOMES` etc.

## Assessment
Needs fixes (Issues 1 to 4 before approval).
