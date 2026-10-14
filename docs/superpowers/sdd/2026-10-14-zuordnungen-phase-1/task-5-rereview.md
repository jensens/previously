# Task 5 re-review, fix round 0677488..3a23a9b

1. ADDRESSED. docs/reference/cli.md line 25 of the diff hunk now says "thirty-four" and lists 34 names. I counted them: the 14th is vocabulary, and entity, relate, entities, relations, classes, triage, answer and status are all present. New test `test_the_command_line_reference_names_every_subcommand_and_counts_them` (tests/test_docs_references.py, end of file) derives the spelled number via `_spelled(len(COMMANDS))` and the name set from `COMMANDS`, and checks for duplicates. `_spelled(34)` gives "thirty-four".
2. ADDRESSED. cli.md, relations section: `ID (none stands)` is documented. It also adds a sentence that the type column shows the label, not the identifier.
3. ADDRESSED. src/previously/cli.py `_relation_claim` raises "--retract needs --subject: only a relation that stands can be retracted" before `_base_claim`, so nothing is written. tests/test_cli.py `test_a_first_version_of_a_relation_cannot_be_a_retraction` checks the sentence and the standing count, and has a control where `--subject --retract` succeeds. cli.md documents the refusal.
4. ADDRESSED. The triage paragraph in cli.md now says "the operator" in all three places.
5. ADDRESSED. src/previously/cli.py `_approve_claims` refuses a `RelationBody` with `candidates is not None` with "event N is a question: answer it with answer N --choose ID". This happens while claims are being collected, before the check and write. tests/test_cli.py `test_approve_sends_a_question_to_answer_and_writes_nothing` checks the sentence and the standing count, and has a control where `answer` works. cli.md documents the sentence.

Tutorial retype: collected 2552, passed 2552, which is the previous 2549 plus the 3 new tests (2 in test_cli, 1 in test_docs_references). The test_docs_references row shows 31 dots, up from 30, which is consistent.

New Critical/Important problems introduced by the fix diff: none.

Out-of-scope observations:
- The `--retract` guard is only in `_relation_claim`. I did not check whether `entity --retract` without `--subject` has the same gap.
- The new docs test only matches the exact "It has N subcommands:" phrasing. If someone rewords the sentence, it fails loudly on the `found is not None` assertion, which is acceptable.
- I did not re-run the suite, as instructed.
