# Task 2 report: policy events (commit 7c662ca)

## What
- `src/previously/core/policy.py` (new): Region, ANY, LOCAL_ONLY (ruling R-1), Circle/Membership/OwnIdentity/Rule/Inference/Provider/Policy, PolicyRefused, to_payload, set_policy (check and write in one transaction via `retrying`), read_policy(at), check_payload, plus public helpers `refusal`, `normalized`, `key_of` that the CLI uses so a refusal comes before the question.
- `core/verify.py`: a `policy` action is checked with `check_payload`; finding text `policy event has no valid form: it <what>`.
- `cli.py`: `policy circle|member|own|rule|provider|show`, help `set and show the processing policy`, placed last in COMMANDS.
- Docs: `docs/reference/cli.md` (thirteen subcommands, exit-code row, `## policy` section), README command list, tutorial test block retyped (ruling T1-a) from one green run (seed 3505003528, 1118 passed, coverage section omitted as a whole, rootdir line left out as the page already says).
- `pyproject.toml`: T201 count 36 -> 40, measured with `ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py` (40 errors).

## Decisions worth a look
- Domain part of a member is lower-cased at write, local part as typed, so a revocation spelled with another case hits the same key.
- Declining the confirmation (or EOF) returns 1 with `nothing written` on stderr; documented in the exit-code table.
- Revoking a membership does not need the circle to exist (check only applies to non-revoked).
- Refusal is checked before the structured form is printed, so nobody confirms what cannot be written.
- Existing tests that wrote a bare `{"action": "policy"}` (tests/test_action.py, tests/test_verify.py control) were changed to a well-formed policy payload or `model_call`, because such a payload is now a finding.

## RED
`tests/test_policy.py` written before the module was used; run with `policy.py` moved away: `ModuleNotFoundError: No module named 'previously.core.policy'`, 1 error (collection). Honest note: the module had been written before the tests; RED was produced by removing it, not by a hand-written stub. verify/CLI tests were written after the code.

## GREEN
`tests/test_policy.py` 29 passed; CLI policy tests 13 selected passed; full run `1118 passed in 167.03s`, `exit 0`.

## Mutations (selection: tests/test_policy.py + tests/test_cli.py, -k policy/refused/...)
1. Replace takes the older event (`setdefault`): 6 failed (replace, revoke, at, capitals, revoked-circle, CLI round trip).
2. Circle-exists check removed: 3 failed (CLI review-focus-5 test, parametrized refusal, revoked-circle).
3. `at` ignored: 2 failed (core `at` test, CLI `show --at`).
Control, unmutated: 54 passed.

## Six gates (final tree)
ruff check, ruff format --check, pyright (0 errors), lint-imports (8 kept), pytest 1118 passed (cov 97.8%), docs html + vale (0 errors) + linkcheck (no broken) all green. docs tests rerun after the retype: 22 passed.

## Concerns
- `redact` refuses any action (`RedactionRefused ... is a redaction`) because "every action is a redaction"; so erasing a policy event (spec 2.1, stage 1c) is not possible through the command yet. My erased-event test makes the tombstone with `storage.erase_payload`. Task 6 or a later one should decide whether `redact event` may target a policy event.
- `policy gaps` is in spec section 5 but not in this task's brief; not built.
- Key of a membership in `Policy.ids` is `circle<TAB>member`.
