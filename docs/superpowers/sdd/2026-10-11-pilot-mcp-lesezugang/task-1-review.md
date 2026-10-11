# Review Task 1 (c90fb40..890de55)

## Spec Compliance
- OK Provider/Rule fields, defaults, payload keys, sorted sets, null for unknown, [] for none: policy.py diff.
- OK (1) Old declarations: `_parse` uses `_optional_*` (absent -> None) and `_flag_or_off`/`_names_or_empty` (absent -> off/empty). verify goes through the same `_parse`/check_payload, so old events pass the form check. Tested by test_a_declaration_and_a_rule_from_before_the_chain_read_with_the_defaults, which appends legacy payloads and asserts `verify == []`. Present-but-wrong-type is a form error (tested).
- OK (2) Merge: flags `any`, sets union (`_merge_chain`). Candidate: no_training needs `training is False`; no_subprocessors needs `== frozenset()`; operator/origin: None with non-empty exclusion fails, named-and-excluded fails, None with empty exclusion passes. Per-restriction tests cover pass / known-fail / unknown-fail, plus a control "unknown passes where nothing restricts", plus a two-rule merge matrix with both single-rule operator exclusions. Reasons name the property.
- OK (3) Hypothesis: `_RULE_VALUES` draws all four new restrictions; `_policy_of` does `Rule(scope, *values)`, so the 7-tuples reach the Rule. The providers carry varied chains (known, trains+unknown subprocessors, local with no origin), and the sampled operator/origin names match them, so the restrictions actually bite. Both exemptions are untouched. The pinned @example for the union is justified (random search did not find M2).
- OK (4) accept.txt: `awk 'NF && /^[a-z]/'` gives 16 lowercase entries, matching the new .vale.ini sentence. The vocabulary change is the one word `subprocessors`.
- OK CLI: three required options (parametrized omit test with a green control), none/unknown beside a name gives return 2 with one line, show prints the fields. Docs and tutorial block updated (1304, matches the claimed run; not re-run).
- ⚠ Mutation results are from the report only; not re-run.

## Strengths
- Unknown-as-fail is implemented in one place and each case has a control.
- Legacy read is tested end to end through append + verify + read.
- The sets are checked for sorted payload and `[]` vs `null` stay apart.

## Issues
### Critical
none
### Important
none
### Minor
1. src/previously/cli.py:1351 and :1421: `--model-origin unknown` is stored as the string "unknown", which counts as a known origin (`excluded_model_origins` containing "unknown" would exclude it, and a rule excluding nothing is unaffected, but the state is inconsistent). `--operator unknown` maps to None (cli.py:1415 region) but `--model-origin` does not, although the help says "unknown if omitted" and the docs table for operator says `NAME|unknown`. Fix: map "unknown" to None for model_origin too, or reject it; add a test.
2. .vale.ini:~15: the sentence "Fifteen of the twenty entries are lowercase, so those fifteen words" still opens the paragraph while the tail now says sixteen (and the file has 24 entries, not twenty). The tail corrects the count, the head contradicts it; a comment is a claim. Fix: reword the head to the current count, or drop the numbers there and keep one counted sentence.
3. Report concern 2 (a local provider must declare `--training no --subprocessors none` to pass such rules) is inherent to the spec; make sure Task 2's local declaration says so.
4. `Decision` does not expose the merged chain (report concern 3); only a note for Task 5.

## Assessment
Approved (minor fixes 1 and 2 advisable before the whole-branch review).
