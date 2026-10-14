# Task 3 review

Spec: ✅
Quality: Approved

## Deviations judged
1. `type_name`: accepted. A002 forbids `type` and no suppression is allowed. Task 4 must call `level(type_name=...)`.
2. Counting by written level: accepted. It keeps the record of a demoted class; test_versions_under_a_class_revoked_with_demote... pins it with `level_of` as the contrast.
3. Rejection counts as corrected: accepted. It is the operator's answer against the version, in the spirit of "Widerruf des Betreibers".
4. `sample` without `Classes`: accepted. All events of a name share the newest id via `graph.classes`; signature equals the brief's.
5. `from >= until` as form fault, revocation not held to vocabulary: accepted. Form (including GATE_TYPES) is still checked on a revocation; test pins retired-but-revocable.
6. `by_name` keeps revoked: accepted. `level` skips them, test pins it.
7. `test_access` untouched: accepted (membership assertion only).

## GATE_TYPES assurance
Three layers, each tested: form (`_types`, parametrized per gate type, `set_class` refusal test), read path (hand-appended log event naming `circle` read as nothing; `by_name == {}`), and `Classes.level` (parametrized, hand-forced `Classes` stays OPEN, with a non-gate control in the same class returning TRANSITIVE). Reported mutations hit the first and the last. The middle layer is pinned by the db test.

## Findings
- Minor, src/previously/core/classes.py `hit_rates` (the `later_direct` line): thread v1 transitive, v2 transitive, operator approves v2 (a direct version) makes v1 count as corrected, though nobody corrected it, only superseded it. This follows the brief's literal wording ("a later direct that is not its approval"), but no test pins either reading; `test_a_later_transitive_version_overtakes_nothing` covers only the case without an approval. Pin or decide in Task 7/final.
- Minor, tests/test_classes.py ~line 322: the by-hand log test asserts `by_name == {}`; the comment "even a class that had slipped through" is carried by the separate forced `Classes` assertion, which is fine, but it sits in a db test while needing no db. Cosmetic.
- Minor, module docstring cites `{ref}vocabulary-reference` for the fold behaviour of `states`; the label is about the vocabulary, not about classes. Test_docs_references passes, so it resolves; relevance is loose.

Counts: Critical 0, Important 0, Minor 3.

## ⚠️
- Interface rename (`type_name`) must reach Task 4's brief.
- Tied threshold "oldest" is by the newest event id of each name, not by the first event that created the name. Consistent with the ruling's text, but a re-set class loses seniority over a twin.
