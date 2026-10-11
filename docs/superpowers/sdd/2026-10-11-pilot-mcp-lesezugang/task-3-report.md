# Task 3 report: the access log

Status: DONE. Commit da30de4.

## What
- `core/access.py` (new): `Withheld`, `Delivered`, `Access`, `AccessRow`, `record_access` (own transaction via `append_action`, no units), `read_access` (filters client, circle, since; skips erased or malformed), `access_problem` (form check), `parse_access`. Constants `NO_RULE`, `RULE`, `OUTCOMES`, `KINDS`.
- `core/action.py`: `MCP_ACCESS` in `KNOWN_ACTIONS`.
- `core/verify.py`: `mcp_access has no valid form: <problem>` and `mcp_access has units`.
- `core/gaps.py`: `Gap.origin` (default `gate`); `gaps` appends the MCP part (`origin="mcp"`, one count per `withheld` entry with `no_rule`, per circle, `event:<id>` without circle). Gate output unchanged.
- `cli.py`: `policy gaps` prints MCP lines with prefix `mcp:` (keeps three tab fields); new command `access [--client] [--circle] [--since]`, help `show what MCP clients saw`.
- Docs: `reference/cli.md` (access section, gaps, exit codes, count sixteen), `policy-and-model-calls.md` (four names), tutorial test block retyped from ONE run of `uv run pytest` (1343 passed; a provisional edit of the count in the last line was made first so that run could be green; the block is the second run, only the `rootdir:` line the page omits was dropped). `tests/test_action.py`, `tests/test_docs_references.py` updated for four names. `pyproject.toml` T201 count 61 -> 63 (measured with the named command).

## Tests (tests/test_access.py, 12)
write/read back, filters, no content in payload (recursive, with control), no units and absent from chronicle, verify broken forms (7 variants + good control), units finding, gaps by origin (+ `rule` is no gap control), CLI access, CLI policy gaps, stored payload equals the concept sketch.
RED: I wrote the implementation before the first test run (not strict TDD); RED shown by hiding `access.py`: collection error "1 error during collection".

## Mutations
- `gaps` ignores mcp_access: 2 failed (gaps by origin, policy gaps CLI). Control (restored): 12 passed.
- form check in verify removed: `test_verify_finds_a_broken_form` red. Control restored: green.

## Gates
ruff check, ruff format --check, pyright (0 errors), lint-imports (8 kept), pytest 1343 passed (97.85% cov on the earlier full run), docs html/vale (0 errors)/linkcheck all clean. The pyproject comment edit came after the last gate run (comment only; ruff check re-run green).

## Concerns
- `--circle` matches only the circle named in `arguments.circle` or in withheld circles; delivered events carry no circle in the payload, so `get_event` calls on a delivered event of that circle are not found by `--circle`. Task 5 could put a `circle` argument or add circles to delivered if that matters.
- The `mcp:` prefix in `policy gaps` is my choice for "separated by origin" while keeping gate output byte-identical.

## Fix round 1

1. No-content test: `test_the_payload_of_an_access_holds_no_content` stays as the normal case on the stored payload. New red case `test_the_search_for_content_finds_it_in_a_stored_payload` puts mail wordings into `reason`, into a nested argument and into an argument key of a real `record_access` call and asserts the walker finds exactly those strings. Measured: walker mutated to ignore dict values: the red case fails (1 failed, 13 passed); restored: green.
2. Form check never raises: `_in` tests `isinstance(str)` before membership (kind, reason_code); entries must be objects with exactly their keys (call, delivered, withheld); `units` list of int (bool rejected), `circles` list of str, `reason` str; era required as text or null. `parse_access` now casts only after the form passed. 12 new variants in `test_verify_finds_a_broken_form`, pinned by event id (unhashable kind and reason_code, extra keys at call and entry level, bool units/circles, non-object entries, non-str client/outcome, non-dict policy, era 7, missing circles); the same test asserts `read_access` and `gaps` survive the forged rows. Measured: `_in` reverted to a bare `value in allowed`: TypeError, test red; restored green.
3. cli.md `policy gaps`: example retyped from one real run of `previously policy gaps` (temporary test, since removed; synthetic model_call and mcp_access rows written through `append_action` and `record_access`); output pasted unedited: gate lines first, then `mcp:` lines. The text now says so.
4. R-3: `Delivered.circles` added; written, parsed and form-checked; `_names_circle` matches on it; `--circle` help, cli.md option row and payload sentence, module docstring and the sketch test updated. New test `test_a_delivered_event_of_a_circle_is_found_by_that_circle`. Measured: delivered match removed: red; restored: green. The field is required in the form; Task 5 must fill it.
5. Renamed `ACCESS_OK`, `ACCESS_ERROR`, `ACCESS_OUTCOMES`.

Gates: ruff check, ruff format --check, pyright (0 errors), lint-imports (8 kept), pytest --cov 1345 passed (98.02%), docs html, vale (0 errors), linkcheck all clean. Tutorial block retyped from one run of `uv run pytest` (1345 passed; the count in the last line was set provisionally beforehand so that the run was green, as in the first round). T201 count re-measured: 63, unchanged.
