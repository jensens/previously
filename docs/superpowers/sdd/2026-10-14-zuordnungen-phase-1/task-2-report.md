# Task 2 report: the graph model, `core/graph.py`

Status: DONE_WITH_CONCERNS
Commits: `bf43451` (model, tests, tutorial retyped), `99a67dd` (grammar of one sentence).
Base: `5432bc6`.

## What was built

`src/previously/core/graph.py` (pure, no database, no clock) and `tests/test_graph.py` (50 test functions, 202 collected).

- Constants: `ENTITY`, `RELATION`, `GRAPH_KINDS`, `TRANSITIVE`, `LEVELS`, `SOURCES`, `RECOLLECTION`, `ACTIVE`, `CLOSED`, `RETRACTED`, `STANDING`; plus `EVIDENCE`, `ENTITY_STATES`, `RELATION_STATES`, `MAX_CONFIDENCE = 100`, `MIN_CANDIDATES = 2`, `MAX_CANDIDATES = 5`.
- `Period(start, end)` with `holds(day)`. **Both ends inclusive**: "until 2019-12-31" holds on that day.
- `FieldValue`, `EntityBody`, `RelationBody`, `Claim` as in the brief.
- `claim_payload` / `claim_problem` / `parse_claim`: payload keys exactly as plan decisions 3 and 4.
- `conformance_problem` against a `Vocabulary`.
- `ClassState`, `GraphVersion`, `GraphThread` (`winner`, `pending`, `objections`, `question`), `Graph` (`entities`, `relations(at=)`, `reaches`), `fold_graph`, `claim_changes`.
- An extra public function, `level_of(version, classes) -> str`.

## Deviations from the brief's signatures, and why

1. **`conformance_problem(claim, vocabulary, *, new_thread, entity_types: Mapping[int, str])`.** It has a new required keyword. The brief puts "Enden-Arten nach from/to" into conformance, but a claim alone carries only entity ids, not their kinds. `entity_types` maps the id of each standing entity the caller may name to its kind. It is used for:
   - the ends of a relation (start, `to`, every candidate);
   - every `ref` field (its value must name an entity of kind `spec.ref`).

   An id missing from the map gives `"an end of the relation is not an entity that stands"`. That is the same sentence for "does not exist" and "not visible", so Task 6 can pass only the visible entities (Review Focus 3).
   A **retracted** version looks up neither its ends nor its refs: retracting asserts nothing about them, and it must stay possible after an end was retracted. Its fields still have to fit their types.
   Task 4 builds the map as `{i: v.claim.body.type for i, v in graph.entities().items()}`.
2. **`Graph.reaches(..., *, extra=(), without=frozenset())`.** As the controller asked.
3. **`level_of(version, classes)`.** This is an addition. The winner needs it, and Tasks 3, 5 and 6 need the same answer to mark a version ("counts as open"). One function keeps that rule in one place.
4. **`GraphThread.rejected` / `approved` default to empty frozensets**, as `assertion.Thread` does.

## Decisions taken inside the brief

- **Field values:** `str` / `"YYYY-MM-DD"` / `{"from","to"}` / `int` id. The payload cannot tell a text spelled like a date from a date, so `parse_claim` turns any string of the date form that is a real date into a `date`. Conformance accepts a `date` for a text field, as the text it is written as. Payload → claim → payload is stable. A claim built with `str("2026-03-01")` for a text field does not equal its parsed form.
  - `"2026-02-30"` in a **field** is a sound text by form; conformance against a date field says `the field "started" is not a date written YYYY-MM-DD`.
  - `"2026-02-30"` in a relation's **`period`** is a form fault.
  - Both are tested.
- **Form rules beyond the brief's list:**
  - Text field values must not be blank.
  - A period has `from` not after `to`.
  - `under` is set exactly on a transitive version (decision 3: "gesetzt genau bei transitive").
  - The operator gives no confidence (decision 3: "null beim Betreiber").
  - `contests` needs a `subject`.
  - A recollection is direct.
  - An event as the start of a relation (`{"event","units"}`) is refused with the sentence plan decision 4 gives the write path: `an event as the start of a relation comes with assignments`.
- **Rejections in `fold_graph`:** parsed with `core.assertion.parse_statement`. A rejection counts when its `of` names a standing graph version, and is ignored otherwise.
- **`contests` in the fold:** it must name a direct version of the same thread, or an erased one. Otherwise the row is skipped, as a dangling `subject` is.
- **Approvals in the fold:** an approval may name an open or a transitive version (raw level), or an erased one. A demoted transitive version can be approved and rejected (tested).
- **`pending` / `question`:** the "anchor" is the version the operator stands for: the latest direct, else the latest unanswered version that counts as transitive.
  - `pending` = unanswered non-direct versions newer than the anchor.
  - With no anchor, `pending` = every unanswered open version except the latest. So a transitive winner overtakes older proposals, as a direct one does.
  - `question()` also considers the winner. A first-version question stands as the proposal and is not pending, but it is still asked (tested).
- **`relations()`** excludes a question (`to` is None): it states no relation yet. With `at=None` there is no time filter. `reaches` walks `relations()` unfiltered, so an ended edge still counts for a cycle, and open proposals count too, because they are winners.
- **`reaches(a, a)`** means a path of at least one edge, so it is true for an edge a→a and for a→b→a.
- **`claim_changes`** names fields as `fields.<name>`, so a field called `state` cannot collide with the body's `state`. It compares type, language / from / to / period, the fields, state, evidence, sources and reason.

## Duplicated rules, held by tests

`graph.py` must not import private names, so it carries copies of three rules from other modules. Each copy has a test that holds it against the original:

| Copy in `graph.py` | Original | Test |
|---|---|---|
| author rule, `_author_problem` | `assertion.py`, private | `test_the_author_rule_is_that_of_obligations` compares against `assertion_problem` on eight authors |
| identifier pattern | `vocabulary.py`, private | `test_the_type_is_an_identifier_as_the_vocabulary_has_it` compares against `vocabulary_problem` |
| language-tag pattern | `vocabulary.py`, private | `test_a_language_is_a_tag_as_the_vocabulary_has_it` compares against `vocabulary_problem` |

The source and unit checks are copied too. They differ on purpose: an empty source list is required for a recollection.

## Tests

| Test | What it holds |
|---|---|
| `test_every_form_round_trips` | 15 claims, every level, recollection, approval of a transitive version, question, objection, all four kinds of field value |
| `test_the_payload_has_exactly_the_contract_keys` | the key sets of decisions 3 and 4 |
| `test_a_period_is_written_with_from_and_to`, `test_a_text_spelled_like_a_date_reads_back_as_the_same_payload` | |
| `test_each_form_fault_has_its_sentence` | 66 cases. Includes the brief's list: float, bool and 101 in `confidence`; transitive without `under`; recollection with sources; recollection from a model; `contests` on direct; one, duplicate and six candidates; `closed` on a relation; `2026-02-30` in the period. Also every source and unit fault |
| `test_the_sentences_are_measured_against_good_payloads` | control: the payloads the table changes are sound |
| `test_an_operator_may_write_a_recollection_but_a_model_may_not` | also: a model without sources writes nothing |
| `test_claim_problem_never_raises` | every key × 9 odd values × 3 base payloads |
| the three equivalence tests in the table above | |
| `test_a_claim_that_fits_the_vocabulary_has_no_problem` | control |
| `test_each_rule_of_the_vocabulary_has_its_sentence` | 24 cases |
| `test_a_date_that_does_not_exist_is_text_and_no_date`, `test_a_text_field_takes_a_text_spelled_like_a_date` | |
| `test_a_retired_kind_takes_further_versions_but_no_new_thread` | Review Focus 4, for an entity and a relation |
| `test_a_retracted_version_does_not_look_up_what_it_names` | |
| `test_a_kind_the_gate_reads_is_direct_or_open` | |
| Fold: `test_direct_beats_a_newer_transitive_and_transitive_a_newer_open`, `test_within_a_level_the_latest_wins`, `test_a_class_revoked_with_demote_or_unknown_counts_as_open[in-force, revoked, revoked-demote, unknown-class]`, `test_a_demoted_version_can_be_rejected_and_approved_like_an_open_one`, `test_a_rejected_transitive_version_no_longer_wins`, `test_an_approval_of_a_transitive_version_makes_it_direct`, `test_a_second_approval_and_an_approval_of_a_direct_version_are_skipped`, `test_the_fold_skips_what_is_no_graph_version`, `test_a_thread_survives_the_erasure_of_its_first_version`, `test_an_objection_must_name_a_direct_version_of_its_thread` | |
| Objections and questions: `test_an_objection_contests_the_current_direct_winner`, `test_an_objection_against_a_superseded_direct_version_is_a_proposal`, `test_a_later_direct_version_overtakes_an_objection`, `test_an_answered_objection_is_no_longer_one`, `test_there_is_no_objection_without_a_direct_winner`, `test_a_newer_transitive_version_waits_behind_a_direct_one`, `test_a_transitive_winner_overtakes_older_proposals`, `test_a_question_is_asked_until_a_direct_version_answers_it`, `test_a_question_behind_a_newer_proposal_is_still_asked`, `test_a_question_is_no_relation_yet` | |
| What stands: `test_entities_are_the_winners_that_are_not_retracted`, `test_relations_at_a_day_hold_at_the_bounds_of_their_period` | 10 cases: both bounds, the day before and after, open start, open end, both open, no period |
| `test_a_retracted_relation_does_not_stand` | |
| `reaches`: `test_reaches_follows_a_chain_in_its_direction`, `test_reaches_finds_an_edge_to_itself`, `test_reaches_finds_a_cycle_back_to_the_start`, `test_reaches_takes_the_edges_of_a_batch`, `test_reaches_walks_only_what_stands_and_ignores_periods` | |
| Changes: three `test_claim_changes_*` tests | |
| The property | see below |

Coverage of `core/graph.py`: 100 % (555 statements).

## The Hypothesis property

`test_the_winner_is_direct_else_transitive_else_open_and_the_latest_within`, at `max_examples=400`.

**What it draws:**
- the first version: direct, open or transitive;
- up to 14 further steps from `direct`, `open`, `transitive`, `reject`, `approve`, `contest`;
- erasures of ids 1 to 15;
- a state for each of two known classes, 901 and 902: in force, revoked, or revoked with `demote`.

Transitive versions pick `under` from 901, 902 and 903. Nothing knows 903.
An approval copies the claim it approves.
A contest names an earlier direct id, which may be erased or may be an approval that did not count.

**How the expectation comes from the rows alone** (`expected_versions` and `expected_level`, never `fold_graph`):
1. Walk the rows in order.
2. A rejection counts if its `of` is a version already standing.
3. A contest counts if its target is erased or a standing direct version.
4. An approval counts if its target is unanswered and either erased or a standing open or transitive version.
5. A transitive version's level is open if its class is missing or revoked with `demote`, and transitive otherwise.
6. Then:
   - `expected = (direct or unanswered transitive or unanswered open)[-1]`;
   - `anchor = (direct or unanswered transitive)[-1]`;
   - `pending` = the unanswered non-direct versions after the anchor, or, with no anchor, `unanswered open[:-1]`;
   - `objections` = the pending versions whose `contests` is the latest direct id.

**What it asserts:**
- the versions of the thread, its rejected set, the winner, `pending` and `objections`;
- whenever a direct version stands, the winner is direct, so a transitive version never wins over a direct one.

**Why 400 examples:** measured with the demote mutation (M2 below). At 100 examples the property went red under 3 of 5 seeds; at 400, under 10 of 10. The run takes 0.6 s green under `--cov`. The comment above `@settings` says so.

## Mutations

Each mutation is measured red and then restored green. The script compared the restored file with the backup (identical), and the restored run gave 202 passed.

| # | Mutation | Red | Stayed green (control) |
|---|---|---|---|
| M1 | transitive before direct (`_anchor` order swapped) | property 10/10 seeds, plus 3 unit tests | `…[in-force]`, every form test |
| M2 | `demote` ignored (`state is None` only) | property 10/10 seeds, `…[revoked-demote]` | `…[in-force]`, `…[revoked]` |
| M3 | a model may write a recollection (check removed) | `test_an_operator_may_write_a_recollection_but_a_model_may_not`, the form-table row | the round-trip case `entity(evidence=RECOLLECTION, sources=())` |
| M4 | GATE_TYPES transitive allowed (check removed) | `test_a_kind_the_gate_reads_is_direct_or_open`, 2 rows of the rule table | `test_a_claim_that_fits_the_vocabulary_has_no_problem` (direct `member_of`) |
| M5 | an unknown class counts as transitive | `…[unknown-class]`, property 9/10 seeds | `…[revoked]` |
| M6 | any contest is an objection | `test_an_objection_against_a_superseded_direct_version_is_a_proposal` | `test_an_objection_contests_the_current_direct_winner` |
| M7 | a retired kind takes a new thread | Review Focus 4 test, 2 rule rows | |
| M8 | a retired kind takes no further version | Review Focus 4 test | the rule rows for retired kinds |
| M9 | period end exclusive | `relations_at…[2019-12-31]` | the other 9 cases |
| M10 | `extra` edges ignored | `test_reaches_takes_the_edges_of_a_batch` | `test_reaches_follows_a_chain_in_its_direction` |
| M11 | approval of a transitive version skipped | property 10/10 seeds, 3 unit tests | approval of an open version in `test_an_answered_objection_is_no_longer_one` |
| M12 | transitive without `under` allowed | its form-table row | the `under` on open row |
| M13 | revoked without `demote` counts open | property 10/10 seeds | |

## Gates

Last lines, after `99a67dd`:

```
uv run ruff check .              -> All checks passed!
uv run ruff format --check .     -> 131 files already formatted
uv run pyright                   -> 0 errors, 0 warnings, 0 informations
uv run lint-imports              -> Contracts: 9 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing
                                 -> Required test coverage of 90.0% reached. Total coverage: 98.08%
                                    2341 passed in 238.96s (0:03:58)
make -C docs html && make -C docs vale && make -C docs linkcheck
                                 -> build succeeded / 0 errors, 0 warnings and 0 suggestions in 46 files / build succeeded (exit 0 each)
```

The docs gate ran after the retype, which is the last change under `docs/`.
The tutorial's test block was retyped because `test_docs_typed_output.py` failed (2139 against 2341):
1. The interim `N passed` was set to 2341.
2. One green `uv run pytest` run: 2341 passed in 238.11s.
3. The whole block was replaced with that run's output, without its `rootdir:` line.

## Concerns

1. **The `conformance_problem` signature has a new required `entity_types`.** Task 4 has to build it from the graph under the tip. Task 6 has to build it from the entities visible to the client.
2. **A text that is spelled like a real date parses as a `date`.** It is harmless to the payload and to conformance. A consumer that renders `EntityBody.fields` must handle `date` in a text field: `claim_changes` already does. If the maintainer wants exact types back, the payload needs a type tag, which is a contract change.
3. **Rules copied rather than shared:** the author rule and the source and unit checks from `assertion.py`, and the identifier and language patterns from `vocabulary.py`. Making them public there would remove the copies, but that touches files outside this task. The equivalence tests above catch drift.
4. **Edges that count in `reaches` and `relations()`.** Open proposals and ended edges count; questions do not. If Task 4 wants only direct or transitive edges for the acyclic check, it can filter. Today a model's open `part_of` proposal would block an operator's edge that closes a cycle with it.
5. **Not checked here, left to Task 4:**
   - that an answer's `to.entity` is one of the question's candidates;
   - that an approval copies the content of what it approves.

   As with obligations, the fold does not check approval content.

---

# Fix round 1

Commit: `1156411`, on top of `99a67dd`.
Review: `task-2-review.md`.
Rulings: T2-b, T2-c, T2-d.

## What changed

- **I1, ruling T2-b.** `Graph.reaches(..., levels: frozenset[str] = frozenset(LEVELS))`.
  - It keeps an edge only when `level_of(version, self.classes)` is in `levels`. The default is all three, for the cycle check of an open write.
  - A direct or transitive write, and an approval, should pass `{DIRECT, TRANSITIVE}`.
  - A relation that starts at an event is never an edge.
  - The `relations()` docstring now says that it holds winners of every level, so it may hold a cycle through an open edge, and that a walk over it needs a visited set.
- **M2, ruling T2-c.** No code change. The `pending()` and `question()` docstrings say that a later transitive version overtakes the older open ones and answers a question.
- **M1.** `_field_problem` turns a `date` in a text **or choice** field into its `isoformat()` before checking. So a built claim and the same claim parsed back from its payload get the same verdict.
- **M3.** `_reject` counts a rejection only when its `of` names a version whose `level_of` at fold time is not direct. A rejection of a direct version is ignored. The docstring of `fold_graph` says so.
- **M5.** An event as the start of a relation is now **sound form**.
  - `RelationBody.start` is `int | Source`. **This changes the brief's signature.** I reused `Source`, since it is exactly `{"event", "units"}`.
  - `claim_payload`, `parse_claim` and `claim_changes` handle it.
  - `conformance_problem` refuses it first, before the kind lookup and for every state, with "an event as the start of a relation comes with assignments".
  - New form sentences: "from names an event that is not a whole number of at least 1", the source unit sentences, and "from is neither an entity nor an event with its units". The last one replaces "from is not an object with the id of an entity".
- **M4.**
  - The author rule uses the exported `assertion.MAX_NAME_LENGTH`; `_MAX_CLIENT` is gone.
  - The separators are spelled `"  "` as escapes rather than literal characters.
  - `test_the_author_rule_is_that_of_obligations` now compares the **sentences**, not only the verdicts. It covers clients of 200 and 201 characters, U+202E, U+2028 and U+2029.
  - A new `test_the_source_rule_is_that_of_obligations` compares the sentences on 18 non-empty source cases.
  - Each of the two has a both-sides control.
- **M6.** The module docstring now says what a message holds: "It may name a field as the vocabulary declares it, and never holds a field value or any other text from the payload."
- **Property.** A rejection step may now also name a direct version. The expectation counts a rejection only when its target is a standing non-direct version.

## New tests

| Test | Covers |
|---|---|
| `test_an_open_edge_does_not_block_what_the_operator_stands_for` | the reviewer's case: open `part_of` 10→11 at confidence 10. `reaches(..., levels={direct, transitive})` is false; with all levels it is true |
| `test_direct_and_transitive_edges_count_for_what_the_operator_stands_for` | the control: direct and transitive edges count. A transitive edge demoted to open does not count under `{direct, transitive}` but does under all levels |
| `test_a_relation_that_starts_at_an_event_is_no_edge` | |
| `test_a_later_transitive_version_answers_a_question_and_overtakes_proposals` | ruling T2-c. The control: with the class demoted, the question is asked again and `pending == [1, 2]` |
| `test_a_choice_spelled_like_a_date_gets_one_verdict_built_and_read_back[2026-01-01, 2026-01-02, later]` | M1, both paths |
| `test_a_rejection_of_a_direct_version_is_ignored` | M3. The control: a rejection of an open version counts |
| `test_an_event_as_the_start_is_sound_form_and_refused_by_the_vocabulary[standing, retracted]` | M5. The control: the same relation with an entity start conforms |
| two round-trip cases with an event start | |
| two form rows for a broken event start | |
| `test_the_author_cases_fall_on_both_sides`, `test_the_source_rule_is_that_of_obligations` (18 cases), `test_the_source_cases_fall_on_both_sides` | M4 |

## Mutations

Each mutation was applied to a copy of the fixed module (`mutate2.py` in the scratchpad) and the run was `uv run pytest tests/test_graph.py -q -p no:randomly`. The restored file is identical to the copy, and the restored run gave 239 passed.

| # | Mutation | Result | Stayed green (control) |
|---|---|---|---|
| N1 | the level filter of `reaches` ignored | 2 red: the open-edge test and the direct/transitive test | `test_reaches_follows_a_chain_in_its_direction` |
| N2 | only a direct version ends the wait | 3 red: the T2-c test, `test_a_transitive_winner_overtakes_older_proposals`, the property | the question tests answered by a direct version |
| N3 | a date in a choice not taken as its string | red: `…[2026-01-01-None]` | `…[later-None]`, `…[2026-01-02-…]` |
| N4 | a rejection of a direct version counts | red: `test_a_rejection_of_a_direct_version_is_ignored`, the property | `test_a_rejected_transitive_version_no_longer_wins` |
| N5 | an event as the start made a form fault again | 6 red: both round-trip cases, both event-start tests, the no-edge test, one form row | the entity-start round trips |
| N6 | the vocabulary takes an event as the start | red: both event-start tests | `test_a_claim_that_fits_the_vocabulary_has_no_problem` |
| N7 | the author length bound plus one | red: the 201-character case | the other 11 author cases |
| N8 | the line separators dropped from `_has_forbidden_character` | **green**, see below | |
| N9 | units may repeat | red: `sources7` (`[2, 2]`) | the other 17 source cases |
| N10 | a source may have extra keys | red: `sources14` | the other 17 source cases |

**N8 stays green, and that is not a gap in the test.** `" ".isspace()` and `" ".isspace()` are both `True` (measured). So the `isspace()` clause of the author rule already refuses both separators in a client name, in `assertion.py` and in the copy alike.
The separator clause in `_has_forbidden_character` cannot change an author verdict, so no author test can tell it apart. `graph.py` uses that helper for authors only.
The equivalence test does cover U+2028 and U+2029, as ruled. Both sides refuse them with the same sentence.

## Gates

After `1156411`:

```
uv run ruff check .              -> All checks passed!
uv run ruff format --check .     -> 131 files already formatted
uv run pyright                   -> 0 errors, 0 warnings, 0 informations
uv run lint-imports              -> Contracts: 9 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing
                                 -> src/previously/core/graph.py 572 0 100%
                                    Required test coverage of 90.0% reached. Total coverage: 98.08%
                                    2378 passed in 239.97s (0:03:59)
make -C docs html                -> exit 0
make -C docs vale                -> ✔ 0 errors, 0 warnings and 0 suggestions in 46 files.
make -C docs linkcheck           -> exit 0, build succeeded.
```

The tutorial's test block was retyped a second time (2341 → 2378), in the same way as before: interim count, one green `uv run pytest` run (2378 passed in 235.04s), the whole block replaced without `rootdir:`. The docs gate ran after that.

## Still open

- **`RelationBody.start: int | Source`** deviates from the brief. Tasks 4 to 6 must handle a `Source` start or rely on conformance to refuse it. `relations()` returns event-start relations if a hand-written one stands; `verify` would report it through conformance.
- **The tutorial block will need a final retype after Task 7**, as the review notes.
