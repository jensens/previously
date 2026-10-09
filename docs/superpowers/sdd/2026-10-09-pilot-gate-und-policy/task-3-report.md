# Task 3 report: core/decide.py

Commit 5cbdf9d. Files: src/previously/core/decide.py, tests/test_decide.py, docs/tutorials/record-your-first-event.md (test block retyped, 1146 tests).

## What
`Candidate`, `Fallback`, `Decision`, `circles_of`, `decide`; `LOCAL_ONLY` imported from policy (R-1). Memberships count only for circles in `Policy.circles` (R-5). Own identities (address or "@domain") removed first. Domain compared case-insensitively via `normalize_member` on both sides, local part exactly. A circle without a rule, or no rule at all, adds built-in `local_only` and `Decision.fallback = Fallback("no_rule", <circles without a rule>)`; `rule_keys` lists rule scopes plus `local_only`. Regions: intersection, `any` is the universe and drops out (all-any gives {"any"}). Candidate passes: declared, not excluded, local under local_only, storage inside regions (empty storage always), retention known and <= limit, an inference space inside regions. Reasons: first `no local provider is declared` (if local_only and no declared local provider), then one sentence per rejected candidate (up to the chosen one).

## RED
`ModuleNotFoundError: No module named 'previously.core.decide'` at collection (implementation moved away to show it). First green run also exposed two wrong expectations of mine (local passes on {eu}; reasons count 4), fixed in the tests, not the code.

## GREEN
28 tests in test_decide.py; full suite 1146 passed (one green run, retyped into tutorial per T1-a, rootdir line left out as before).

## Mutations (all reverted, control green 28 passed)
- regions union instead of intersection: 3 red (incl. the Hypothesis property).
- own identities not removed: 2 red.
- circle without rule ignored (`local_only = not rules`): 3 red (two-circle test among them).
- domain compared exactly (no normalize): 1 red (review focus 2 test).

## Gates (all six run)
ruff check, ruff format --check, pyright 0, lint-imports 8 kept, pytest 1146 passed (coverage decide.py 100%), docs html + vale (0 errors) + linkcheck ok.

## Interpretations / concerns
1. Selectable inference space: I treat a provider with a single declared space as having none to select, so `inference_geo` is None (Mistral, local); a provider with 2+ spaces gets one set. The spec/brief do not define "selectable" precisely; the alternative would be `reports_inference_geo`. Task 5 should confirm.
2. Region choice: regions == {us} picks a space with regions {us}; otherwise spaces that mean exactly {us} are dropped, then prefer the one containing `any`, then by name. Consequence: regions {eu, us} fails Anthropic (global is outside, us would be narrower) and passes Mistral/local. Matches the maintainer wording but is worth a glance.
3. Hypothesis property: the extra rule is a source rule the baseline lacks; baselines that fell back for "no rule at all" are skipped (first rule legitimately loosens there). A new circle rule for a circle lacking one also loosens by design (local_only lifted); not covered by the property.
4. `rule_keys` holds scope strings (not event ids); Task 5 can map via `Policy.ids[("rule", scope)]`.
5. Spec paragraph signs in test comments trip test_docs_references, so section comments say "Pilot assertion N".

## Fix round 1
Changes: decide.py `_space` per R-7 (fitting spaces ranked widest first: `any`, larger meaning, name; the `us` filter is gone; docstring rewritten); redundant `"@" in address` dropped. test_decide.py: `{eu,us}` test inverted (Anthropic passes with `us`, geo `us`); property extended per R-8 (kinds: source rule, rule for an uninvolved circle, further involved circle with rule; two named exemptions in the docstring) with the reviewer's counterexample as `@example`; both `pyright: ignore` removed; section comment at assertion 7 completed; R-5 citation qualified.
Mutations (reverted, control green 28 passed): old `us` filter back -> 2 red (inverted test and the property via the @example); R-5 membership filter removed -> 1 red (test_a_membership_in_a_circle_that_does_not_exist_counts_for_nothing).
Gates: ruff check, format, pyright 0, lint-imports 8 kept, pytest 1146 passed (count unchanged, tutorial untouched), docs html/vale/linkcheck ok.
