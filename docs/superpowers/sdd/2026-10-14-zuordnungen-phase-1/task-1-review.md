# Task 1 review: vocabulary

Spec: PASS (with notes)
Quality: Approved

## Findings

### Minor
1. src/previously/core/vocabulary.py `_text` (~l.1074): `str.isprintable()` is stricter than "no control characters". It also rejects NBSP, U+2028 and other non-ASCII separators and unassigned or private-use code points, so a label such as "Kreis<NBSP>X" is refused. Harmless for now. Say so in the reference page or test it (`unicodedata.category` Cc would be the exact rule).
2. src/previously/core/vocabulary.py `refusal` (~l.1347): the reference check skips built-in kinds. `member_of` names `person` and `organization`, so a file can retire `person` with no refusal and `member_of` is left pointing at a retired kind. No test covers it. The stated rule "a kind another kind needs cannot be retired" has this hole, and it opens in phase 3 when the gate reads these.
3. `ref` to a relation is a write-time refusal, not a form error. The brief listed it among the form errors (Step 1). The report discloses this, and it is justified because the form cannot know kinds. The consequence is that `verify` cannot flag an event with a ref to a relation or an unknown kind.
4. src/previously/core/vocabulary.py `Vocabulary.label` takes one `language`. The `PREVIOUSLY_LANGUAGE` default (`en`) step of decision 11 is not here. It is not testable from the diff and is presumably a caller concern for a later task (see the warning below).
5. tests/test_vocabulary.py `test_the_check_never_raises_on_a_payload_of_the_wrong_shape` asserts only `None or str`, but its purpose (no exception) is real.
6. tests/test_wheel.py builds the wheel a second time (slow). It could share a fixture.

### Critical / Important
None.

## Verified
- Payload contract (decision 7): keys, identifier regex, language-tag regex, text 1..80, choice values 1..50 distinct, `values`/`ref` exactly with their type, behaviors per kind, `from`/`to` exactly for a relation, required text field `name`, field named `period` only as type period (and never on a relation), and the `period` behavior requiring that field. All present and parametrized with sentence assertions.
- Built-ins: always present in the fold, fold keeps only `labels` from an event, `apply` refuses everything else including retiring. Control is the labels-only write (the test itself shows control and failure).
- File: tomllib, own emitter, unknown key and unknown table are errors, retired kinds are rendered and parsed, base file is its own canonical rendering (tested), show -> apply is a no-op (CLI test and DB test), missing kind retired, built-ins never retired. Shipped as `src/previously/vocabulary.toml`, wheel test present.
- Ruling P-2: no `concerns`, `member_of` from person/organization to circle, `in_circle` empty from. Matches, and there is a test for the absence of `concerns`.
- `KNOWN_ACTIONS` gets `vocabulary`; `approval_class` deferred to task 3 and disclosed. Tests and the docs sentence pin five names.
- `verify` branch refactored via `_statement_finding`. The policy messages are unchanged.
- No new `LogStore` method; no `# type: ignore` or new noqa in the diff; no mocks. Trailer was not checked (commit message not in the diff file).
- T201: measured 81 `print(` in cli.py, which matches the pyproject figure (ruff statistic not separately run).
- Mutations claimed are plausible against the tests: the built-in refusal test (7 params), the fold test for a stray event, `differences` returning all (second-apply control), and verify without the branch (control: good event gives `[]`). I did not re-run them.

## Warnings (unverifiable from the diff)
- The CLI error path for `VocabularyRefused` returning exit 2 is asserted in tests, but the exit-code mapping of `PreviouslyError` is not in the diff.
- The docs pages (vocabulary.md, cli.md) were not read in full. The gate results (vale, html, linkcheck) were reported but not re-run.
- The `PREVIOUSLY_LANGUAGE` handling of decision 11 is not implemented here (see finding 4). The task 2 or CLI consumer of `label` must do it.
