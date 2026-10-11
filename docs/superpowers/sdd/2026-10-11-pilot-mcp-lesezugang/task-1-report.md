# Task 1 report: the processing chain and the restrictions of a rule

Status: DONE (one point for the maintainer under Concerns).

## What
- `Provider` gets `operator`, `training`, `subprocessors`, `model_origin` (defaults: unknown); `Rule` gets `no_training`, `no_subprocessors`, `excluded_operators`, `excluded_model_origins` (defaults: off/empty). Payload keys as in the brief; sets sorted, `null` for unknown, `[]` for "none" subprocessors.
- Reading: a payload without the new keys reads with the defaults (no migration). A key present with a wrong type is a form error that `verify` reports.
- `decide`: new `_Chain` merged strictest-wins (flags `any`, sets union); a candidate passes only with a known satisfying value; the reason per rejected candidate names the property (training, subprocessors, operator, model origin).
- CLI: `policy provider` requires `--operator NAME|unknown`, `--training yes|no|unknown`, `--subprocessors NAME…|none|unknown`; optional `--model-origin`. `policy rule` gets `--no-training`, `--no-subprocessors`, `--exclude-operator`, `--exclude-model-origin`. `policy show` prints the new fields. "none"/"unknown" beside a name: return 2, one sentence.
- Docs: `cli.md`, `policy-and-model-calls.md` (keys, example payload, legacy-read paragraph), the how-to (provider commands and one paragraph), tutorial test block retyped from one run of `uv run pytest` (1304 passed, `rootdir:` line dropped as before).
- `subprocessors` added to the Vale vocabulary (`accept.txt`) and counted in the `.vale.ini` comment (sixteen lowercase entries).

## Files
src/previously/core/policy.py, core/decide.py, cli.py; tests/test_policy.py, test_decide.py, test_cli.py, test_docs_references.py (rule example now passes the four new keys); docs/reference/cli.md, policy-and-model-calls.md; docs/how-to/set-a-policy-and-try-a-call.md; docs/tutorials/record-your-first-event.md; .vale.ini; .vale-styles/config/vocabularies/Previously/accept.txt.

## RED / GREEN
Tests were written before the source was reverted to HEAD for the RED run (implementation had been written first; I restored HEAD source to measure RED honestly): `tests/test_decide.py` and `tests/test_policy.py` fail at collection with `TypeError: Provider.__init__() got an unexpected keyword argument 'operator'`. With the implementation back: two test bugs of my own fixed, then 90 passed (decide+policy), full run 1304 passed.

## Mutations (tests/test_decide.py, each reverted, control green: 50 passed)
- M1 unknown `training` passes `no_training` (`is not False` -> `is True`): red, `test_no_training_passes_only_a_declared_no[unknown]` and `test_the_reason_names_the_property_that_failed`.
- M2 `excluded_operators` as intersection: red, `test_rules_merge_strictest_wins_for_the_chain[operator-x|y]` and `test_adding_a_rule_never_widens_the_passing_candidates`. First attempt left the Hypothesis property green: my first `@example` was wrong (an added rule that excludes more cannot widen under an intersection). Replaced by an example where one rule excludes `me` and the added one excludes nothing; now red. Plain random search did not find it in one run, so the pinned example carries it.
- M3 unknown operator/origin pass an exclusion (`if value is None and excluded` -> `if False`): red, both `[unknown]` cases.
- M4 `no_subprocessors` merged with `all` instead of `any`: red, `[subprocessors]` merge case.
- Controls: `[no]`, `[other]`, `[none]` cases stay green under every mutation; `test_training_does_not_matter_without_the_restriction` and the no-exclusion test pin that unknown passes where nothing restricts.

## Hypothesis property
`_RULE_VALUES` now draws all eight rule values (flags, operator names, origin names); the providers in `test_decide.py` carry varied chains (anthropic: known; mistral: trains, subprocessors unknown; local: no origin). Both exemptions are unchanged.

## Six gates (each its own run, after the last edit)
ruff check: all passed. ruff format --check: 108 files formatted. pyright: 0 errors. lint-imports: 8 kept, 0 broken. pytest --cov: 1304 passed, 98.04% (decide.py 100%, policy.py 98%, cli.py 99%). docs html OK, vale 0 errors, linkcheck exit 0.
(A first `ruff check` hit C901 on `_check`; fixed by extracting `_check_names`/`_check_chain`, no suppression.)

## Concerns
1. "Pflichtoptionen fehlen -> Rückgabe 2, ein Satz": argparse raises `SystemExit(2)` with usage plus one error line, same as the existing `--storage` case; I followed that precedent and tested it that way. Because the options are required, `policy provider --revoke` needs them too (values unread), as it already does for `--storage`; the how-to says so.
2. A local provider that declares nothing about training fails `--no-training`; local providers must say `--training no --subprocessors none` to pass such rules. Intended by "unknown passes no restriction", but worth knowing when Task 2 declares the local provider.
3. `Decision` does not expose the merged chain restrictions (only reasons). Task 5 may want them.
