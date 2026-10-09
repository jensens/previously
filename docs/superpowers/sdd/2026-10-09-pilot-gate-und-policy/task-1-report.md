# Task 1 report

Status: DONE. Commit 5c2e44d "actions: one write path, unknown names are a finding, the chronicle shows observations".

## Implemented
- `core/action.py` (new): REDACTION/POLICY/MODEL_CALL, KNOWN_ACTIONS, `write_action`, `append_action`, and a public generic `retrying(log, once)` (the loop moved out of `redact._retrying`, shared by both).
- `core/redact.py`: `_write` and `_retrying` removed; uses `write_action(..., (), recorded_at=...)` and `retrying`.
- `core/redaction.py`: imports REDACTION from `core.action` (re-export keeps `core.redaction.REDACTION` working; verify now imports from action).
- `core/verify.py`: name not in KNOWN_ACTIONS -> `Finding(id, 'unknown action "<name>"')`.
- `core/projection/chronicle.py`: skip non-observation events; version 3, with docstring.
- Tests: `tests/test_action.py`, `tests/test_chronicle.py` (new); `test_verify.py` (teleport + known-name control); adapted `test_redact.py` (the "something" action is now a finding), `test_projection_worker.py` (forced versions 3/2 -> 4/3), `test_cli.py` (rebuild lines 4 -> 3, 1 -> 3).
- Docs: new section in `explanation/projections.md`; `reference/cli.md` (chronicle sentence, version numbers in examples); tutorial test block retyped (1079 items).

## TDD
RED was not run as a separate step before the code (code was written first for the move); the mutations below give the red evidence instead. Concern noted.

## Mutations (all reverted)
- M1 filter in `derive` removed (`if False:`): `test_chronicle.py::test_an_action_with_units_is_not_in_the_chronicle_and_an_observation_is` and `::test_the_upgrade_to_version_3_rebuilds_and_ends_as_a_fresh_build` red (2 failed, 11 passed).
- M2 name check removed: `test_verify.py::test_an_action_with_an_unknown_name_fires` and `test_redact.py::test_read_index_passes_over_what_it_cannot_read` red.
- Control: known-name tests (`policy`, `model_call`), observation row test, 31 selected tests green.

## Gates (final tree, after the vale fixes)
ruff check, ruff format --check, pyright (0 errors), lint-imports (8 kept), pytest --cov: 1079 passed, 97.87% (action.py, chronicle.py, redact.py, redaction.py, verify.py 100%), docs html OK, vale 0/0/0, linkcheck OK.

## Concerns
- No separate RED run before implementation (see above).
- Tutorial block: the numbers come from a full run at 1079 items; that run had only the typed-count test red (expected, tutorial stale), whose F was typed as `.`; the later full run with the retyped tutorial was green (1079 passed). Seed/duration/order are from the first run.
- CLAUDE.md `Assisted-By:` used in the commit (the system reminder asked for Co-Authored-By; project rule wins).

## Fix round 1
1. `docs/reference/cli.md`: new finding `unknown action "<name>"` in the verify table and the quoted block (heading now "Ten findings come from the hash formats, from erasure and from the names of actions"). `tests/test_docs_references.py` keys on that sentence, so its lookup sentence, the count (13 -> 14) and its docstring were updated. Mutation: message in `core/verify.py` changed to `unknown act "{name}"` -> `test_the_reference_quotes_what_the_code_actually_prints` red; reverted, green (control: the same test with the real message, 15 passed in the pair run).
2. Tutorial test block retyped from one run of `uv run pytest --cov --cov-report=term-missing` (1080 passed in 184.79s, seed 2448098401, 97.87%). Header lines through `[100%]` and the summary line are copied verbatim; the coverage table between them is left out (a different block), as is the `rootdir:` line the page has always omitted. The command line shown on the page stays `$ uv run pytest`. To make that run green I first set only the `N passed` number to 1080 (the typed-count gate reads it), then retyped the whole block from the run.
3. `docs/how-to/rebuild-a-projection.md`: "at version 3 ... `version: int = 4`".
4. `core/redact.py`: comment above the `retrying` calls carries the old reasoning (position lost at `insert_event`, rollback undoes only the lock). New `test_a_naive_recorded_at_is_refused_before_a_transaction_opens` (unreachable store, so only the early `iso_utc` can raise InvalidPayload). Mutation: line removed -> test red; kept -> green.
Gates: ruff check, ruff format --check, pyright 0 errors, lint-imports 8 kept, pytest --cov 1080 passed, docs html/vale (0/0/0)/linkcheck all green.
