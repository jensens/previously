# Task 3 review (c17879b..488a240): the assertion command line

Measured: `pytest tests/test_cli.py -k "assert or approve or reject or obligation or decision"` gives 26 passed.
T201 measures 74 against the configuration, as the comment says.
Tutorial block: 50 files, progress sums to 1878, every percentage equals int(100*cum/N), no `F`; test_cli.py collects 441, which matches 54+72*5+27.

## Spec compliance

- Commands, options and help wording: OK (cli.py COMMANDS, `_assert_arguments`).
- `assert`: author `human:operator`, direct; form, dates, references and `--source` are checked before the question: OK (`_asserted`, `_parse_day`, `_parse_source`).
- `--subject` fills from the winner or the latest version, preview shows `change` lines: OK (cli.py `_base_of`, `_cmd_assert`).
- `name:` hint: stderr, before the question, does not block, text as contracted: OK.
- Lists and `--proposals`, `--history`: OK against the brief.
- Review Focus 5: dates refused before the question; a past due is written and overdue: OK, tested.
- F-10: MISSING. No `check_statements` exists. References, erased or non-observation sources, and the approve/reject answerability beyond `_proposal_of` are only checked in `write_statements`, after the question (cli.py `_write_asked`). cli.md even documents this ("refused after the question").
- F-11: MISSING, all four parts.
  - `--due none` cannot clear a due date with `--subject` (`_obligation_body`: `args.due is None` keeps the old one, anything else goes to `_parse_day`).
  - Lists say `1 versions` / `1 proposals` (cli.py `_list_line`); cli.md says "The words are plural for one as well", so the docs must change with it.
  - `approve 3 3` builds two statements for one proposal (`_cmd_approve` does not de-duplicate); the second is refused only by the write path.
  - No test holds the quoted assertion error sentences and formats in cli.md against the code in `test_docs_references`.

Verdict on compliance: matches the brief as written; the later rulings F-10 and F-11 are not yet implemented.

## Named risks

1. F-6: holds. `assert` and `reject` write `OPERATOR`/`DIRECT`; `approve` copies the proposal's author, sets `approves`, direct. No CLI path writes `model:` direct without `approves`.
2. `--subject`: no hole found. Kind is checked (`thread.kind != kind`), the body is taken only by `isinstance` of the right body type, an erased version is not in `thread.versions` (F-2), so nothing is copied from one. Two behaviours worth knowing, not defects: a proposal winner is the base (documented), and with no winner the base is `versions[-1]`, which may be a rejected proposal.
3. Hint: pairs address and name inside the same identity entry of the same event, so an address is never printed for a name that sits in another entry or another source. Printed through `escape_field`. Does not block. No test covers the two-source case (Minor, M-2).
4. Escaping: lists, page, history, change lines and the hint go through `escape_field`; `reason`, `what`, references, sources, author are all covered. EXCEPT `_preview` (see I-1).
5. Review Focus 5: OK. See F-10 above for the part that is still after the question.
6. Docs: spot checks of three formats (the list line with seven fields, the `change` line with four fields, the hint line) match the code byte for byte. The tutorial block is sound. The cli.md sentence "plural for one as well" matches the code today and will be wrong after F-11.
7. T201: 74 measured, comment says seventy-four. OK. The repeated word count in the second comment sentence is fine.

## Strengths

- Tight, readable structure; every body-level function is small; strict form checks (`\d{4}-\d{2}-\d{2}` before `fromisoformat`, `fullmatch` on sources).
- Tests run against real PostgreSQL, verbatim output, controls beside the hint and date tests.
- The tutorial block was retyped from one run and checks out arithmetically.

## Issues

### Important

- I-1: `_preview` (cli.py, `_preview`) prints `json.dumps(..., ensure_ascii=False)` raw. That leaves DEL and C1 characters (U+009B is `ESC[`) unescaped. For `approve` the payload is a model-authored proposal, so text from outside reaches the terminal raw; `_json_line` in the same file exists for exactly this and is not used. Fix: use `_json_line` (it cannot do `indent=2`, so give it an indent parameter or post-apply `_JSON_CONTROLS`), and add a test with `\x9b` in a proposal's `what`, measured red.
- I-2: F-10 missing (above). Add `check_statements` in core/assertions.py and call it in `_cmd_assert`, `_cmd_approve` and `_cmd_reject` before the question, inside the snapshot; update the cli.md sentence "refused after the question". Test: a source that does not exist, an erased source and a missing unit are all refused with exit 2 and no question.
- I-3: F-11 missing (above): `--due none`, singular `1 version`/`1 proposal` (and the cli.md sentence), de-duplicated `approve`, docs-reference test for the quoted sentences and formats.

### Minor

- M-1: The docstring of `_name_hints` contains a garbled clause: "(a reference to a name is a label); this tells the operator". The header comment of the section has an odd line break after "stated". Reword.
- M-2: Test gaps: the escaping test covers only `what` in a list line; none for the page, the history, `reason` or references; none for the hint with the name in a different source than the address. Add them (a mutation that drops `escape_field` on the history `reason` currently stays green).
- M-3: `_list_assertions` reads all threads twice in one snapshot (`_entries` and `_replaced_by(read_threads(...))`); read once and pass it. Matters for the planned 5 000-assertion measurement.
- M-4: `_cmd_decisions` assigns `owed_by`, `owed_to`, `overdue` onto `args` so the shared code can read them; a small shared filter object or `getattr` would be cleaner.
- M-5: `--replaces` cannot be cleared with `--subject` (same shape as `--due none`); say so in cli.md or handle it with F-11.
- M-6: `obligation ID --history` on an entry whose every version was rejected answers "no obligation stands", though a history exists. Defensible; consider showing the history.

## Assessment: Needs fixes

I-1 is a real defect; I-2 and I-3 are rulings F-10 and F-11 not yet applied. No Critical findings.
