# Task 4 report: write path, reading, verify, cascade (`core/graph_write.py`)

Commit a93ee1b (one commit, base 516ba45). Status: DONE with concerns below.

## Built

- `core/graph_write.py` (new), with the contract signatures unchanged:
  - `GraphRefused`, `Written(ids, levels)`, `CLASS_CHANGED` (the sentence of Review Focus 2, as a constant for Task 6);
  - `check_claims(log, conn, claims, *, recorded_at) -> tuple[Claim, ...]`;
  - `write_claims(log, locker, claims, *, recorded_at, expect_levels=None) -> Written`;
  - `read_graph(log, conn, *, as_of=None) -> Graph`;
  - `claim_verdict(policy, client, identities, sources, *, recollection) -> Decision`;
  - `relation_visible(policy, client, relation, ends, identities, sources) -> bool`.
- Also public, because `verify` and Tasks 5/6 need them:
  - `EntityTypes(graph)`, a lazy `Mapping[int, str]` equal to `{s: v.claim.body.type for s, v in graph.entities().items()}`, so a check does not walk every thread;
  - `starts_thread(claim)`: `subject is None or approves == subject`;
  - `closes_cycle(graph, claim, vocabulary, *, level)`: the one cycle question that the write path and `verify` both ask;
  - `takes_proposal(approval, proposal)`: the approval copy rule, including answering a question;
  - `read_claim_events(log, conn, threads)` and `claim_sources(events, thread)`: `SourceEvents` for graph threads, for Task 6's verdicts.
- Write path order inside `retrying`:
  - lock the sources ascending (`lock_event`);
  - read the tip and the assertions below it; a repeated handle returns `Written` of the stored rows;
  - `read_vocabulary` and `read_classes`;
  - `check_sources` (shared);
  - then per claim: level, the `expect_levels` comparison, form and canonical form, subject, approval, `conformance_problem` with `EntityTypes`, the answer to a question, the cycle rule;
  - fold the claim into a `GraphFold` at `top+1+offset`;
  - prepare and link per attempt, then insert.
- Level ruling T4-a:
  - an approval is taken as given;
  - an operator claim must be direct (`"a version by the operator is direct"`);
  - a model claim against a thread whose winner is direct (by `level_of`) becomes `open` with `contests=winner.id`;
  - a model question (candidates) is always `open`, because the form forbids a transitive question;
  - otherwise `Classes.level(type_name=body.type, ...)` decides.
- `core/assertions.py`:
  - `check_sources` (public, takes a `Sequence[Source]`) and `read_sources` (unlocked read for previews), used by both write paths;
  - a rejection whose `of` is no obligation or decision version is looked up in a lazily folded graph (`_GraphVersions`). The fold runs only when needed, under `read_classes` read after the tip. The version must not be direct by `level_of`, must not be approved or rejected (the batch included), and the rejection must take its sources;
  - `SourceEvents.named(events)` and `read_events(log, conn, events)`, which `of`/`read_source_events` now delegate to;
  - module docstring order updated.
- `core/graph.py`: `GraphFold`, an incremental fold with `add(row_id, recorded_at, payload, classes)`, `graph(classes)`, `subject_of`, `erased`. Only touched threads are rebuilt, and thread order is preserved. `fold_graph` is now a loop over it, so its semantics are unchanged (all 383 graph/class/vocabulary tests stayed green).
- `core/vocabulary.py`: `VocabularyFold`. `core/classes.py`: `ClassFold` and `Classes.covers(class_id, ...)`, sharing `_covering` with `level`. `read_vocabulary` and `read_classes` now use the folds.
- `core/verify.py`: `_Claims`, owned by `_Assertions`:
  - it is fed vocabulary and class actions as the pass meets them (`_Erasures.observe` → `claims.action`), and every erased, rejection and graph row;
  - a graph row branches off before `assertion_problem`. The checks are: form (`claim_problem`), units, source position, subject, approval (copy and answered), contests, conformance against the vocabulary at its position, `under` covered (`Classes.covers`) by the classes at its position, and `closes_cycle`;
  - a rejection naming a graph version goes to `claims.rejection_reason`, so it is no longer "names no open proposal";
  - `reconcile` covers graph claims through the shared `_standing`.
- `docs/reference/cli.md`: a second block under `verify`, "Five more come from entities and relations alone", with a table. `tests/test_docs_references.py`: `test_the_reference_quotes_the_findings_about_entities_and_relations`, which holds it like the sixteen.

## Deviations (please rule)

1. **Cycle check of a batch by folding, not by `extra`.** The ruling says `reaches(..., extra=<batch edges>, without=<threads the batch re-versions>)`. I fold each earlier claim of the batch into the graph, as it will stand once written, and call `reaches(to, start, {type}, without={own subject}, levels=...)`.
   - Why: `verify` cannot know batches, so with `extra` the two would disagree. `extra` would count a batch objection or a pending proposal as an edge, and an open batch edge against a later transitive claim, which ruling T2-b excludes outside a batch.
   - With folding, write path and `verify` ask the identical question (`closes_cycle`) over the identical graph. The brief's mutation ("cycle only against the folded graph, not the batch") goes red.
   - `without` is still used, for the claim's own thread. Without it, turning an edge around is refused against its own old edge (mutation E).
2. **An approval may answer a question.** `takes_proposal` accepts an approval of a question whose body equals the question's except `to ∈ candidates` and `candidates=None`.
   - The plan has `write_triage_answer` write "direct with the author of the question, like write_approve". The form allows a model-authored direct version only as an approval, and a plain approval must copy the body, so without this Task 6 could not write that answer.
   - A plain operator direct version with `to` among the candidates also answers. A direct standing relation with another `to` is refused with `"the answer names {id}, which is none of the candidates"` while the question is pending; that applies to approvals of other pending versions too. A retraction answers with none (allowed).
3. **Retired kind and approvals.** `starts_thread` counts an approval of a thread's first version as new, so approving a proposed new entity of a kind retired since is refused (`"the kind is retired and takes no new entity"`).
4. **Source refusals arrive as `GraphRefused`.** `check_sources` raises `AssertionRefused`; `write_claims`/`check_claims` re-raise its sentence unchanged as `GraphRefused`, so Tasks 5/6 catch one class.
5. **`check_claims` on a repeated handle** returns the claims stored under the handle (parsed), not the input; the write returns their ids and levels.
6. `expect_levels` of the wrong length raises `ValueError`, a programming error rather than a refusal.
7. The verify finding for `under` checks that `under` is the newest event of a class in force that covers author, kind, type, confidence and `recorded_at`. It is not required to be the class `level` would pick among several.

## Tests (68 new; suite 2439 → 2507)

- `tests/test_graph_write.py` (47):
  - Vellenfeld association (organization, posts, persons, `holds` with periods, `relations(at=2019-03-01)`); a batch naming its own entity; handle idempotency, preview of a repeat; batch rules, `MAX_BATCH`, null byte; form;
  - subject nothing / other kind; ends missing or retracted; source sentences (as `GraphRefused`); recollection by the operator yes, by a model no;
  - operator open refused; level from class, open without, client-given level ignored; a question never transitive; objection against a direct winner; preview levels writing nothing;
  - class revoked or set between preview and write → `CLASS_CHANGED`, with control; vocabulary retired between preview and write (Review Focus 1); retired kind: further versions yes, new ones no, for an entity and a relation (Review Focus 4); approving a new entity of a retired kind;
  - approvals (copy, already approved, overtaken, other thread, twice in one batch, rejected, transitive); questions (answer by direct version, by approval in the model's words, by retraction);
  - cycles: new edge, self edge, turned version (Review Focus 5), within a batch, open edge vs operator and model, approving an open edge that closes one; **two concurrent writers over two connections**, forced to meet at the tip with a barrier on a `PostgresStorage` subclass, each on its own source event so that no row lock orders them. Exactly one is written, the other is refused after a retry (the loser read the tip twice). Five repeated runs were green;
  - `read_graph(as_of=)`; `EntityTypes`; `closes_cycle` with an event start; `claim_verdict` (recollection held without a rule, free with `source:recollection`, mixed needs both); `relation_visible`; `read_claim_events`/`claim_sources`.
- `tests/test_assertions.py` (+5): a rejection of an open entity is written and folded and `verify` stays clean; wrong sources; twice in one batch; direct or approved refused; transitive rejected; preview with the same sentence.
- `tests/test_cascade.py` (+2): an erased source erases the renamed entity version and a relation, the winner falls back, `verify` is clean; an approval stands when its graph proposal is erased on its own.
- `tests/test_verify.py` (+10), with forged rows via `prepare`/`insert_event`:
  - write-path control clean;
  - broken form;
  - vocabulary of its time: declared-later is a finding, retired-later is not;
  - transitive under a revoked class or a non-class is a finding, under a class revoked later is not;
  - forged cycle and self edge, with a turned-version control;
  - subject nothing, other kind, approval of a direct version, bad contests;
  - approval content, sources, twice;
  - graph rejection: of a direct version, again, without sources;
  - units and a later source; a non-observation source.
- `tests/test_vocabulary.py`, `tests/test_classes.py` (+3): the folds and `Classes.covers`. `tests/test_docs_references.py` (+1).

## Mutations

Each: mutation → red, restored → green, with a control test that stays green under the mutation. The script is in the scratchpad (`mutate.py`); each test was run alone.

| # | Mutation | Red | Control (green under mutation) |
|---|---|---|---|
| A | cycle checked against the graph below the tip only, not the batch (brief) | `test_a_cycle_within_one_batch_is_refused_and_nothing_written` | `test_a_new_edge_that_closes_a_cycle_is_refused` |
| B | write path trusts the preview's vocabulary, no conformance re-check under the tip (brief: "vocabulary of the preview") | `test_a_vocabulary_changed_since_the_preview_refuses_the_write` | `test_the_preview_shows_the_levels_and_writes_nothing` |
| C | `verify` uses today's vocabulary (read once at the snapshot) (brief) | `test_an_entity_is_held_against_the_vocabulary_of_its_time` | `test_entities_and_relations_written_through_the_write_path_are_no_finding` |
| D | level taken from the client for models (brief) | `..._writes_open_whatever_it_asks_for`, `..._writes_an_objection`, `..._makes_a_confident_claim_transitive` | `test_the_operator_writes_direct_versions_only` |
| E | own thread not left out of the cycle check | `test_a_new_version_that_turns_an_edge_...` | `test_a_new_edge_that_closes_a_cycle_is_refused` |
| F | every level counted for a direct write (T2-b) | `test_an_open_edge_does_not_veto_the_operator_...` | same control as E |
| G | graph checked once, not under the tip of each attempt (decision 13) | `test_two_writes_that_each_close_half_a_cycle_cannot_both_stand` | same control as E |
| H | an answer outside the candidates let through | `test_a_direct_version_answers_a_question_...` | `test_a_retraction_answers_a_question_...` |
| I | an approval may not answer a question | `test_an_approval_answers_a_question_in_the_models_words` | `test_an_approval_makes_a_proposal_direct_...` |
| J | a direct graph version may be rejected | `test_a_direct_or_approved_version_of_an_entity_is_not_rejected` | `test_a_rejection_of_an_open_entity_is_written_...` |
| K | `verify` does not check `under` | `test_a_transitive_version_under_no_class_in_force_is_a_finding` | write-path control in `test_verify.py` |
| L | `verify` does not route graph rejections to the graph | write-path control in `test_verify.py` (reports "rejection names no open proposal") | `test_assertions_written_through_their_write_path_are_no_finding` |
| M | `expect_levels` ignored | both `test_a_class_..._since_the_preview_refuses_the_write` | `test_expect_levels_gives_one_level_per_claim` |
| docs | page wording changed; a block line deleted; a vocabulary reason that `graph.py` never returns; the code message changed | each red | unchanged page green |

## Gates (after the retype, tree as committed)

```
uv run ruff check .                 All checks passed!
uv run ruff format --check .        135 files already formatted
uv run pyright                      0 errors, 0 warnings, 0 informations
uv run lint-imports                 Contracts: 9 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing   2507 passed in 243.68s; TOTAL 98%;
                                    graph_write, graph, verify, assertions, classes, vocabulary 100%
make -C docs html && make -C docs vale && make -C docs linkcheck   exit 0; vale 0 errors, 0 warnings, 0 suggestions in 46 files; linkcheck 0 broken
```

The tutorial block was retyped whole from one green `uv run pytest` run (2507 passed in 239.81s; the `rootdir:` line left out as the page says).

## Comments that move

- The transaction-order comment in `assertions.py` was updated. Its module docstring now says that a graph rejection reads the classes after the tip, why a vocabulary or class event read after the tip is safe (it takes the position, so the insert fails and the next attempt reads again), and that `graph_write.py` uses the same order and `check_sources`.
- `docs/explanation/concurrency.md` was not changed, because the order did not change: locks, tip, read, check, write, as unit 5. Note for Task 7: the page does not describe the assertion write path at all ("Since stage 1c two paths write…"), which was already incomplete before this task.
- `contract/store.py` counts: the measuring command still gives 15. `graph_write.py` calls no new `LogStore` method; the "twelve modules" is dated 2026-10-12 and stays a dated statement.
- No new suppression; noqa count is 4 + `docs/conf.py`.

## Concerns

1. **The cost of `verify` grows with the square of the acyclic edges.** Every such claim walks `relations()` of the graph before it. Measured 2026-10-14, one run each, a chain of `part_of` edges: 1,000 edges → `verify` 0.57 s, 2,000 → 1.87 s. At 2,000 edges a single edge write took 148 ms and `read_graph` 103 ms. Extrapolated, 10,000 edges is about a minute of `verify`. Recorded in the `_Claims` docstring; decision 14's final measurement should include `verify`.
2. **An erased vocabulary or class event** is not folded by `verify`, as `read_vocabulary`/`read_classes` skip it. A claim written while it stood can then become a finding: a "not declared" kind, or "transitive under no class" (the fold already counts such a version as open). Nobody erases such events today; Task 7 may want it under the limits.
3. **Task 6 hidden ends (Review Focus 3).** The write path looks up ends among all standing entities. The MCP server must refuse an invisible end with the same sentence (`"an end of the relation is not an entity that stands"`) before calling `write_claims`; the write path takes no visibility filter, since the contract has none.
4. **`CLASS_CHANGED` also fires** when a direct version written since the preview turns a model claim into an objection (level transitive → open). The ruling fixed the sentence; it is slightly imprecise for that case.
5. `relation_visible` treats a question's candidates as ends (all must be visible) and returns False for an event start (phase 1).

---

# Fix round 1 (review `task-4-review.md`, rulings T4-d and T4-e)

Commit dac79b0 (on a93ee1b). Status: DONE. 11 new tests; the suite went from 2507 to 2518.

## What changed, per finding

- **I1 (ruling T4-d)** — `graph_write._levelled`:
  - Order of the rules: objection first (a direct winner); then a thread with a pending question, where a model claim that does not name one of its candidates is written `open` (`under=None`, `contests=None`) and the question stays pending; then the class.
  - New public helpers, shared with `verify` and `_check_answer`: `pending_question(thread, classes)` and `names_a_candidate(claim, asked)`.
  - *My reading of the ruling:* only a claim that is a **standing** relation pointing at a candidate may be transitive on such a thread. A model's *retraction* there is therefore written open as well, not only a claim whose `to` is no candidate. It is the safer side, since an open version stands for nobody. Please say if retractions should follow the letter instead.
- **M1** — signature change in `write_claims`:
  - `expect_levels: Sequence[str] | None` becomes `expect: Sequence[Decided] | None`. `Decided(level, under, contests)` is new, and `decided(claim)` gives it for each claim that `check_claims` returned.
  - `_check_expected`: a different `contests` refuses with `DIRECT_WRITTEN = "a direct version was written since the preview; call again without confirm"`. A different level or `under` refuses with `CLASS_CHANGED`. Contests is checked first, because a new direct winner also changes the level of a would-be transitive claim, and that sentence is the true cause.
  - A wrong length raises `ValueError("expect gives one decision per claim")`.
  - **For Task 6's `staged` flow:**
    - The preview runs `shown = check_claims(...)`, shows them, and keeps `[decided(c) for c in shown]`.
    - The confirm call has nothing but the client's arguments and the handle. So the decisions have to travel inside the sealed handle, for example as `[[level, under, contests], ...]` beside the digest in `seal`'s canonical body (a `confirm.py` change in Task 6), so that `open_handle` returns them for `write_claims(..., expect=...)`.
    - Sealing the digest of the *levelled* payloads instead would catch the change too, but only with the generic handle sentence.
- **M2** — `starts_thread(claim, thread)`, where `thread` is the thread before the claim:
  - New: `subject is None`, or a direct or transitive version that is not a retraction, on a thread with no version written direct or transitive. Not new: an open version, a retraction, and a subject whose versions are all erased (`thread is None`; nothing is known of it, so it is not counted as new, to avoid false findings).
  - This applies to every claim, not only approvals. So an operator's plain direct version on a proposal-only thread of a retired kind is refused too, since that also makes the entity stand for the first time. Approving a transitive first version of a retired kind is allowed.
  - `verify` uses the same function.
- **M3** — `verify._Claims`; `claim_reason` is split for C901 into `_claim_references`, `_claim_level` and `_claim_rules`. Three new findings:
  - `assertion is open but written by the operator`;
  - `assertion by a model follows a direct version and does not object to it`: a model non-approval on a thread whose winner is direct by `level_of`, which is not `open` with `contests == winner.id`;
  - `relation answers a question with none of its candidates`: a pending question, and the version is direct and standing, or transitive, and does not name a candidate.
  - `cli.md` now says "Eight more come from entities and relations alone", with three new rows. The docs test collects from the three methods and expects 8 lines.
  - Still not held, and said in the docstring: a model open version that a class would have made transitive.
- **M4** — `GraphFold.current(classes)` is a `MappingProxyType` view that follows the fold, with no per-row copy. `verify` and the write path's batch loop use it; `graph()` still copies for `fold_graph`. The new timings are in the `_Claims` docstring, dated.
- **M5** — `_Erasures.observe` feeds `claims.action` **before** `_form_finding`. `VocabularyFold` and `ClassFold` check the form themselves, so `verify` takes an event with units as `read_vocabulary`/`read_classes` do. The event itself is still a finding.
- **M6** — `core/assertions.py` docstring: this module reads only the classes, and only for a graph rejection; `graph_write.py` reads the vocabulary too.
- **M7** — `_repeated` in `graph_write.py` matches only `GRAPH_KINDS` payloads, and the one in `assertions.py` only `KINDS` (obligation, decision, rejection). Each docstring says why.

## New tests (11)

- `test_graph_write.py`:
  - `test_a_class_does_not_answer_a_question_with_none_of_its_candidates` (I1, the reviewer's case) and its control `test_a_class_answers_a_question_with_one_of_its_candidates`;
  - `test_another_class_at_the_same_level_since_the_preview_refuses_the_write` and `test_a_direct_version_written_since_the_preview_refuses_the_write`, which covers an objection against a newer direct version and a proposal that turned into an objection, with a control (M1);
  - `test_expect_gives_one_decision_per_claim`, renamed;
  - `test_approving_a_later_proposal_of_a_thread_that_never_stood_is_new`, which also covers the operator's direct version and a further proposal, and `test_approving_a_transitive_version_of_a_retired_kind_is_no_new_entity` (M2);
  - `test_a_handle_repeats_only_within_its_own_write_path`, in both directions (M7).
- `test_verify.py`:
  - `test_an_answer_with_none_of_the_candidates_is_a_finding` (direct and transitive, with a control), `test_a_model_version_after_a_direct_one_that_does_not_object_is_a_finding`, `test_an_open_version_by_the_operator_is_a_finding` (M3);
  - `test_a_vocabulary_event_with_units_governs_the_claims_after_it` (M5).
- The revoked-class and set-class tests now go through `expect` and `decided`.

## Mutations

Run with the scratchpad script `mutate.py`, one replacement at a time, each test run alone, file restored after each.

```
== N1 a class may answer a question outside its candidates (T4-d)
   mutated FAILED restored PASSED test_a_class_does_not_answer_a_question_with_none_of_its_candidates
   mutated PASSED restored PASSED test_a_class_answers_a_question_with_one_of_its_candidates
== N2 under not compared with the preview
   mutated FAILED restored PASSED test_another_class_at_the_same_level_since_the_preview_refuses_the_write
   mutated PASSED restored PASSED test_a_class_revoked_since_the_preview_refuses_the_write
== N3 contests not compared with the preview
   mutated FAILED restored PASSED test_a_direct_version_written_since_the_preview_refuses_the_write
   mutated PASSED restored PASSED test_a_class_set_since_the_preview_refuses_the_write
== N4 new thread is approving the first version (old rule)
   mutated FAILED restored PASSED test_approving_a_later_proposal_of_a_thread_that_never_stood_is_new
   mutated FAILED restored PASSED test_approving_a_transitive_version_of_a_retired_kind_is_no_new_entity
   mutated PASSED restored PASSED test_a_retired_kind_takes_further_versions_but_no_new_entity_or_relation
== N5 verify: operator open not reported
   mutated FAILED restored PASSED test_an_open_version_by_the_operator_is_a_finding
   mutated PASSED restored PASSED test_entities_and_relations_written_through_the_write_path_are_no_finding
== N6 verify: model after a direct winner not held to the objection rule
   mutated FAILED restored PASSED test_a_model_version_after_a_direct_one_that_does_not_object_is_a_finding
   mutated PASSED restored PASSED test_entities_and_relations_written_through_the_write_path_are_no_finding
== N7 verify: answer outside the candidates not reported
   mutated FAILED restored PASSED test_an_answer_with_none_of_the_candidates_is_a_finding
   mutated PASSED restored PASSED test_entities_and_relations_written_through_the_write_path_are_no_finding
== N8 verify: vocabulary fed only after the form finding (units skip it)
   mutated FAILED restored PASSED test_a_vocabulary_event_with_units_governs_the_claims_after_it
   mutated PASSED restored PASSED test_an_entity_is_held_against_the_vocabulary_of_its_time
== N9 graph handle repeats across write paths
   mutated FAILED restored PASSED test_a_handle_repeats_only_within_its_own_write_path
   mutated PASSED restored PASSED test_a_second_write_with_the_same_handle_writes_nothing_and_returns_the_same_ids
== N10 assertion handle repeats across write paths
   mutated FAILED restored PASSED test_a_handle_repeats_only_within_its_own_write_path
   mutated PASSED restored PASSED test_a_second_write_with_the_same_handle_writes_nothing_and_returns_the_same_ids
```

- N10 was green the first time: the test compared against the wrong ids. I fixed the test and re-measured it red, above.
- Mutations A to M of the first round were rerun on the new code, B, K and M with their replacement text adapted, and were all red with green controls.
- Docs test: the new page line `assertion is open but written by the operator` reworded went red, and the deleted `relation answers a question…` line went red; the unchanged page is green.

## `verify` timings (M4)

Measured 2026-10-14, one run each, temporary test file, removed afterwards.

```
chain part_of n=1000: verify 0.57s
chain part_of n=2000: verify 1.77s
post_in n=2000: verify 0.56s
post_in n=10000: verify 2.67s
copy per row (old), post_in n=2000:  verify 0.58s
copy per row (old), post_in n=10000: verify 4.90s
```

Without acyclic kinds, the pass is now close to linear: 10,000 relations means 20,001 graph rows. With acyclic edges it is still quadratic through `reaches`/`relations()`, as stated in the docstring. The 100,000 measurement belongs to the final review (decision 14).

## Commands and gates (final tree, dac79b0)

```
uv run pytest -q -p no:randomly tests/test_graph_write.py tests/test_verify.py tests/test_assertions.py tests/test_docs_references.py
  244 passed in 13.49s
uv run ruff check .                 All checks passed!
uv run ruff format --check .        135 files already formatted
uv run pyright                      0 errors, 0 warnings, 0 informations
uv run lint-imports                 Contracts: 9 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing
                                    2518 passed in 242.32s; TOTAL 98%; graph_write, graph, verify,
                                    assertions, classes, vocabulary 100%
make -C docs html && make -C docs vale && make -C docs linkcheck
                                    exit 0; vale 0 errors in 46 files; linkcheck 0 broken
```

- The first docs run failed `vale`: "it is" → contraction, in the new `cli.md` row. I fixed the wording and reran the docs gate and then the full coverage run on the final tree; both results are above.
- The tutorial block was retyped from one green `uv run pytest` run: 2518 passed in 237.50s.

## Left open

- The review's ⚠️ items are outside this task:
  - `level_of` trusts `under` for gate kinds (Task 2's code; fix before the gate reads the graph);
  - Task 6 must set `author` itself;
  - a pending question blocks the operator's other answers (Task 7 how-to);
  - relations can point at an erased entity (Task 5 listings).
- The Task 6 handle carrying `Decided`, as described under M1.
