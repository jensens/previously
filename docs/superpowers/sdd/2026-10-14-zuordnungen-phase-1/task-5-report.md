# Task 5 report: the command line

## Commands built
entity (write, page, --history), relate (--subject, --to-date, --retract), entities, relations (--at, --as-of), classes add|revoke|list|sample, triage, status, answer; approve and reject dispatch on graph versions (mixed call refused). PREVIOUSLY_LANGUAGE read in cli.py; `display_label` and `is_language_tag` in core/vocabulary.py (Task 6 can import them).

## Deviations
- `classes.class_refusal` added to core/classes.py (public pre-check, `set_class` shares `_standing_kinds`): so a class is refused before the question, as `policy` does.
- `answer` pre-checks the candidate and says the write path's `_check_answer` sentence; through the write path alone an approval naming a stranger gets "an approval takes the content ... unchanged" (test_graph_write pins that order, so I did not reorder). A test holds the two sentences equal.
- `--count` error is a PreviouslyError (not InvalidPayload) so the doc test that reads cli.py sees it.
- Listings: type column shows the label, not the identifier (page shows both). `relations` never lists open winners (triage does); no `--proposals` on relations.
- "does not fit" is not judged when an end of a relation is gone (shown as `ID (erased)` / `(retracted)` / `(none stands)`).
- Doc section `## Entities and relations` sits before `(cli-mcp)=`; it is outside the span the assertions doc tests read? (they passed).

## Tests
27 new tests in tests/test_cli.py (Vellenfeld sequence incl. who sat on the board 2019-03-01, page both directions, history with changed vocabulary, as-of, language and fallback, erased/retracted ends, classes, hit rate, sample, triage order, answer, approve/reject graph, mixed approve, help). Full suite: 2549 passed.

## Mutations (each red when mutated, green restored; the test's own control assertions stay green)
triage order; --at ignored; --as-of ignored; fallback mark dropped; working language ignored; erased end dropped; not-fit mark dropped; class refusal after the question; mixed approve allowed; --recollection with --source allowed; revoke loses fields; answer changes author; sample ignores count; candidate sentence changed. 14/14.

## T201
81 -> 96 (measured with the ruff command); narrative in pyproject.toml extended, both "eighty-one" retyped "ninety-six".

## Gates
ruff check, ruff format --check, pyright (0 errors), lint-imports (9 kept), pytest --cov (98.14%, 2549 tests; tutorial block retyped from one green plain run, 2549 passed), docs html/vale (0 errors)/linkcheck all green.

## Concerns
- Label shown in listings is the kind label only; scripting by identifier needs `entity N`.
- Config doc says twenty-one variables.
- `approve` reads the whole graph when an id is not an obligation/decision.

## Fix round 1 (Ruling T5-b)
1. cli.md now says "thirty-four subcommands" and lists all of `COMMANDS` (vocabulary included). New test `test_the_command_line_reference_names_every_subcommand_and_counts_them` in tests/test_docs_references.py derives the spelled number and the name set from `COMMANDS`. Mutations: dropping `triage` from the page -> 1 failed; "thirty-three" -> 1 failed; restored -> 1 passed.
2. `ID (none stands)` documented next to `(erased)` and `(retracted)`; one sentence added that the type column shows the label while `entity ID` shows both.
3. `relate --retract` without `--subject` refused: "--retract needs --subject: only a relation that stands can be retracted" (test with a control that retracts with --subject). Mutation (condition off) -> red; restored green.
4. "he" replaced by "the operator" in the `triage` paragraph.
5. `approve` on a question id refused: "event N is a question: answer it with answer N --choose ID", nothing written; test has the control that `answer` works. Mutation -> red; restored green. Documented in the `answer` section.
Measured: tests/test_cli.py + tests/test_docs_references.py 526 passed (before the last two edits); T201 still 96 (no print added). Six gates green; full suite 2552 passed; tutorial retyped from one green run (the two earlier runs: one expected failure of the stale tutorial, one flake of the unrelated tests/test_mcp_server.py::test_a_mail_that_carries_an_earlier_tag_does_not_close_the_fence, which passes alone and twice more).
