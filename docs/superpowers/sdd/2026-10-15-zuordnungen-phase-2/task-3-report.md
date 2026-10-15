# Task 3 report — the projection `graph`

Status: DONE_WITH_CONCERNS. Commit `207d647` on `worktree-zuordnungen-2` (base `a6d358a`), not pushed.
Test count 2724 → 2741 (`2741 passed`).

## What was built

- `src/previously/core/projection/graph.py` (new): `GraphProjection(name="graph", version=1)`, `GRAPH`; pure helpers `summary(thread, classes) -> GraphThreadRow | None`, `version_row(event)`, `rejected(event)`, `marks(batch) -> Marks`; private `_classes` (a `ClassFold` over `log.actions(APPROVAL_CLASS)` with `id <= batch end`), `_same_name`, `_named`, `_rows`, `_stale`.
- `PROJECTIONS = (CHRONICLE, SOURCE_STATS, GRAPH)`; `GRAPH` exported from `core.projection`.
- `contract/rows.py`: `GraphVersionRow(id, subject, kind, under)`, `GraphThreadRow(subject, kind, type, winner_id, level, state, start_entity, start_event, start_units, to_entity, candidates, period_start, period_end, pending, objections, question)`.
- `ProjectionStore` gained seven methods: `insert_graph_versions`, `graph_versions(conn, ids) -> dict[int, GraphVersionRow]`, `graph_version_ids(conn, subjects) -> dict[int, list[int]]`, `class_subjects(conn, under_ids) -> set[int]`, `delete_graph_versions(conn, ids)`, `upsert_graph_threads`, `delete_graph_threads(conn, subjects)`. Two more than the brief lists: `graph_versions` (id → row, for a rejection's target and a redaction's target) and `delete_graph_versions` (see "stale rows" below). Docstring of the protocol describes them.
- `PostgresStorage`: the seven methods; `_PROJECTION_TABLES: dict[str, tuple[Table, ...]]`, `graph` → `(p_graph_thread, p_graph_version)`; `truncate_projection` deletes every table of the name. `read_graph_threads(conn)` outside the protocols (tests read it; Task 4 builds `GraphStore`). Comment of the "outside the protocols" section corrected: `core` now reads a projection back, but only to catch it up.
- `storage/schema.py` + `migrations/versions/0006_graph.py` (`down_revision = "0005_watermark"`): tables as in decision 5, CHECKs `p_graph_version_kind_check` (`entity, relation, rejection`) and `p_graph_thread_kind_check` (`entity, relation`), indexes `p_graph_version_subject_idx`, `p_graph_thread_kind_type_idx`, `p_graph_thread_to_entity_idx`, `p_graph_thread_start_event_idx`. FK onto `event.id` only on `p_graph_version.id` and `p_graph_thread.subject`; `subject` of a version row and the ends carry none (a hand-written version may name a nonexistent id; a catch-up must not fail on it). `start_units int[]`, `candidates bigint[]` (entity ids are bigint; the brief said `int[]` for both). Downgrade drops both tables **and deletes the `graph` row of `projection_state`**, else a re-upgrade would meet an `up_to_id` with empty tables.

## Ruling T3-a: which seam

Chosen: **widen `Projection.write` to `write(store, log, conn, batch)`** — the projection writes through `ProjectionStore[Conn]` and reads the log through `LogStore[Conn]`, both on the caller's connection; `catch_up` passes its `log`. Chronicle and source-stats take and ignore `log`. Reason: the other option would have put log reads into `ProjectionStore`, the protocol whose point is that it is not the log; a `write` with a narrower store type would not satisfy the protocol (parameter contravariance). `core` stays SQL-free, `.importlinter` unchanged (9 kept). The graph calls only `events_by_id` and `actions`, both already among the fifteen `LogStore` methods `core` calls; `contract/store.py` docstring updated: the files naming `LogStore` are sixteen now (measured: 15 before + `core/projection/graph.py`), method count stays fifteen (measured with the docstring's command). Written up on `docs/explanation/module-boundaries.md`.

## Design as implemented

- **Marks per batch:** a graph version → its subject; a rejection whose `of` names an earlier event that is a version row (batch or `p_graph_version`, kind ≠ rejection) → row `(R, subject(of), 'rejection', None)`, subject touched; a `redaction` of scope `event` → the target's subject when it has a row, **and the target as a subject itself** (an erased first version, or an erased non-graph assertion, lets later versions of that subject stand in `GraphFold.add`); an `approval_class` event → `class_subjects` of every class event id of the same name (grouped by `Classes.states[id].id`, the newest of the name). A vocabulary event marks nothing.
- **Beyond the brief, needed for equivalence:** (a) an erasure of an **action** (fetched kind) marks every thread under any class (`class_subjects(all class ids ∪ targets)`): a class event can be erased (`redact` refuses only redactions), its name goes with its payload, and the fold reads classes "now". (b) The refold reads the erased rows a version names via `approves`/`contests` (the fold treats an erased id there as standing). (c) **Stale rows**: after the refold, rows of the thread a rebuild would not write are deleted — an erased version or rejection, and a rejection whose version is erased. Without (c), `p_graph_version` differs between incremental and rebuild (a version read before its erasure keeps its row) and `test_incremental_equals_rebuilt` cannot hold both tables.
- **Refold:** ids of the touched subjects from `p_graph_version`, plus each subject itself, rows from the batch where it holds them and `events_by_id` for the rest, only `kind == 'assertion'`, in id order, one `fold_graph` for all touched subjects under the class states as of the batch's last event; `summary` per subject; upsert where a winner stands, delete otherwise. `level` via `level_of`, counters via `pending()`, `objections()`, `question()`.

## Tests

`tests/test_projection_graph.py` (17 tests, new):
- `test_the_tables_hold_ids_counts_and_vocabulary_words_and_no_content` — holds both column lists and that the only `Text` columns are `kind, type, level, state`.
- `test_a_rebuild_empties_both_tables`, `test_the_graph_is_the_third_projection_the_command_line_catches_up`.
- Shapes: `test_an_entity_and_its_relations_stand_with_their_ends_and_level` (entity, assignment of a whole mail, of a unit, `involved_in` with period), `test_a_question_stands_with_its_candidates_until_it_is_answered`, `test_a_model_version_under_a_class_is_transitive_and_its_objection_counts`.
- One test per way a thread changes: erased version; erased mail → cascade takes the assignment (Review Focus 1, projection side); rejection; class revoked with/without `demote` (parametrized, `control` id); erased class event; first version erased before the projection read it; approval of a proposal erased before the projection read it (second batch on the same thread); `test_incremental_equals_rebuilt_for_both_tables`.
- Review Focus 5: `test_two_catch_ups_at_once_write_every_row_once_and_end_where_the_fold_does` — first catch-up holds its first batch uncommitted (overridden `set_projection_state`) until the second waits on a lock; both finish, no error, rows == fold, incremental == rebuild.
- Review Focus 2: `test_property_the_projection_stands_where_the_fold_does` — Hypothesis, `max_examples=60, deadline=None`, `truncate_statement`, 6 mails, an opening of two persons, two projects (operator), a transitive person and a transitive assignment, folded once; then 8–30 random steps: entities and relations (`concerns` from a mail or units, `involved_in`, `part_of`; operator or model at confidence 10 or 90; new thread or new version; model questions), approvals (also answering a question), rejections (with the proposal's sources), erasures of versions / of mails 2–6 whole or one unit (cascade) / of class events, class events set again or revoked with or without `demote`, catch-ups with batch size 1, 2, 5 or 500. After every catch-up `p_graph_thread == summary(fold_graph(whole log), read_classes().states)`; at the end once more, then a rebuild from nothing in batches of 1 equals both tables. Refused steps write nothing and the history goes on. Green run ≈ 22–24 s.
  Measured reach (hypothesis `event()`, 60 examples, temporary instrumentation, removed): rejections in ~19 %, approvals ~30 %, objections pending ~27 %, questions ~20 %, demote ~25 %, event-start rows ~25 %, every level appears. Earlier versions of the strategy reached far less (rejections 0 % — a rejection must take its proposal's sources; mail erasures blocked all later writes); fixed by picking standing mails, sparing mail 1, picking proposals for answers.

Extended:
- `tests/test_projection_worker.py`: `_snapshot` returns four tables (chronicle, stats, `p_graph_version`, `p_graph_thread`); `test_incremental_equals_rebuilt` now also runs `_graph_history` (vocabulary, project, assignment of unit 1 of event 2, model proposal, its rejection, erasure of that unit → cascade) with a catch-up after each step, and pins both graph tables. `_FailingStore` delegates the seven new methods (pyright).
- `tests/test_schema.py`: `test_the_projection_tables_exist` holds five tables, docstring updated. Columns/NOT NULL/CHECK names and indexes are held by the existing generic tests.
- `tests/test_cli.py`: a `graph` line in every typed `project` / `redact` output (11 places), one comment updated.

## Mutations (each change → red; restore → green), final tree

Harness: apply one change to `core/projection/graph.py`, run the named test and the property alone, restore. Run on the final tree:

| Mutation | Dedicated test | Property alone |
|---|---|---|
| M1 a redaction marks nothing (`touched.update(found.erased …)` removed) | `test_an_erased_version_takes_its_thread_with_it` red; `test_an_erased_mail_takes_its_assignment_by_the_cascade` red | red |
| M2 a class event marks nothing (`under = set()`) | `test_a_class_revoked_with_demote…[demote]` red, `[control]` green | red |
| M3 a rejection marks nothing | `test_a_rejection_takes_the_proposal_it_rejects` red | red |
| M4 `_stale` returns nothing | `test_incremental_equals_rebuilt_for_both_tables` red; also `test_projection_worker.py::test_incremental_equals_rebuilt` red | red |
| M5 an erased action marks nothing | `test_an_erased_class_event_turns_what_stands_under_it_open` red | red |
| M6 refold leaves out erased named rows | `test_an_approval_of_a_proposal_erased_unread…` red | **green** (scenario too rare for the strategy; stated in the property's docstring) |
| M7 refold leaves out the subject itself | `test_a_thread_whose_first_version_was_erased_unread…` red | red |
| restored | 16 passed | passed |

Controls: the `control` parameter of the demote test stays green under M2; the thread beside the erased one keeps its row in the erasure test; the restored file passes everything.
Note: under the first version of the property (without the transitive opening), M2 left the property green; the opening was added for that, and the run above is after it.

Concurrency: with `lock_projection_state` reduced to an unlocked read, the concurrency test goes red (`UniqueViolation` on `p_graph_version_pkey`); restored green. Taking out only `FOR UPDATE` leaves it green — measured via `pg_stat_activity`, the second catch-up then waits at the placeholder `INSERT … ON CONFLICT DO NOTHING` into `projection_state`. Both written into the test's docstring.

## Typed output retyped (real runs, scratch `postgres:18` container, 2026-10-15)

- `migrate`: `migrated: (empty) -> 0006_graph`, `up to date: 0006_graph`, `migrated: 0002_projections -> 0006_graph` (DB upgraded to `0002_projections` with alembic first), `Error: the database is at revision 0007_example, which this version of previously does not know; it knows revisions up to 0006_graph` (alembic_version stamped by hand), `Error: the database refused the migration to 0006_graph: permission denied for schema public` (a login role on a default `public` schema), `… permission denied for table alembic_version` (role with CREATE on `public` but only SELECT on `alembic_version`, DB at `0005_watermark`). Into `docs/reference/cli.md`, `docs/how-to/run-the-image.md`, `docs/tutorials/record-your-first-event.md`; the release example in `docs/how-to/cut-a-release.md` moved `0006_example` → `0007_example`.
- `project`: tutorial (`built: 1 event, up_to_id 1` ×3, `up to date, up_to_id 1` ×3) from the tutorial's own `append`; `docs/how-to/ingest-a-mail-folder.md` `graph built: 5 events, up_to_id 5` from a run over a log of five appended events (not an IMAP ingest — the line depends only on the count).
- Tutorial test block retyped whole from one green `uv run pytest`: `collected 2741 items`, `2741 passed in 304.43s (0:05:04)` (the count was set first so the typed-output test could pass, then the block replaced by that run).

## Docs (plone-doc-style:author loaded)

- `docs/explanation/projections.md`: intro (five tables), new section `(graph-projection)=` "The graph, folded again thread by thread" (why no content, why refold not merge, what touches a thread, the asymmetry, the property, the stale-row rule, what it doesn't follow, two readers); "lists the three tables" → five.
- `docs/reference/database-schema.md`: "eight" → "ten" tables, "Three hold projections" → five; sections `p_graph_version`, `p_graph_thread` with constraints and the migration's way back; `projection_state.name` lists `graph`.
- `docs/reference/cli.md`: `project` order sentence; migrate lines.
- `docs/how-to/rebuild-a-projection.md`: `GraphProjection.version`, plural tables/lines.
- `docs/explanation/module-boundaries.md`: the `write(store, log, …)` seam.
- Counts rechecked: "eight tables" (now ten, counted in `metadata`: event, unit, source_key, event_blob, watermark, projection_state, p_chronicle, p_source_stats, p_graph_version, p_graph_thread), "three tables" in projections.md and test_schema.py (now five), `contract/store.py` counts (files 16, methods 15, both measured). `docs/explanation/design-records.md:24` "the three tables" is about stage 1b and stays.

## Gates (final tree, 2026-10-15)

```
uv run ruff check .                     All checks passed!
uv run ruff format --check .            140 files already formatted
uv run pyright                          0 errors, 0 warnings, 0 informations
uv run lint-imports                     Contracts: 9 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing
                                        2741 passed in 308.29s; TOTAL 98% (97.68%, fail_under 90);
                                        core/projection/graph.py 157 stmts, 99% (114, 128 missing:
                                        a graph payload with a form fault, a rejection payload
                                        parse_statement refuses)
make -C docs html                       build succeeded
make -C docs vale                       0 errors, 0 warnings and 0 suggestions in 50 files
make -C docs linkcheck                  build succeeded
```

## Concerns

1. **Two documented limits** (also on the page): a version written around the write path that approves/contests a version of *another* thread starts counting in the fold once that version is erased, and the erasure does not touch the naming thread; a payload nulled by hand without a redaction is never seen. In both the projection can lag until a rebuild. Task 4's `project --check` should catch them. A column for named ids would close the first; not added (decision 5's columns are binding).
2. **Cost of a catch-up batch that touches the graph:** it reads every `approval_class` action (`log.actions` visits every action, no index) — on a rebuild once per batch with graph events. Batches without graph marks (e.g. an MCP access entry) return before that read. `class_subjects` scans `p_graph_version` without an index on `under` (class events are rare). Neither measured at scale.
3. **Two store methods beyond the brief** (`graph_versions`, `delete_graph_versions`) and the stale-row rule; Task 4 should know that `p_graph_version` holds only rows of unerased events.
4. M6 is caught only by its dedicated test, not by the property.
5. Map (landkarte) not touched — the limits in concern 1 and the class-read cost may belong there (Task 6).

---

# Fix round 1 (review `task-3-review.md`, ruling T3-b)

All nine items addressed in one round; commit listed at the end.

- **I-1** `contract/store.py` declares `LogReader[Conn]` (`events_by_id`, `actions`). `Projection.write(store, log: LogReader[Conn], conn, batch)`; chronicle, source-stats and graph take `LogReader`; `catch_up` still holds a `LogStore` and passes it (structural). The false sentence in `worker.py` replaced by one about `LogReader` having no appending method. `docs/explanation/module-boundaries.md` says why (a `LogStore` would hand every projection `insert_event`). Proof: `tests/test_projection_store.py::test_the_log_and_its_store_satisfy_the_read_protocol_of_a_projection` assigns a `PostgresStorage` and a `LogStore[Connection]` to `LogReader[Connection]`; measured red (pyright, 11 errors) with `LogReader.actions` renamed, green restored.
- **I-2** Counts in `contract/store.py`, measured at the fix: `grep -rl LogStore src/previously/core --include='*.py' | wc -l` → 15 (the projections no longer name `LogStore`; at 207d647 it was 18, as the reviewer measured — the docstring now says so and gives the `--include` form, since without it `__pycache__` files are listed too: 33 in this tree). Method command → 15. `LogStore` declares 16 (counted). `grep -ohE 'log\.[a-z_]*\(' src/previously/mcp_server/*.py | sort -u | wc -l` → 8. Added one sentence: `LogReader` declares two of the sixteen.
- **I-3** `tests/test_migration_0006.py` (own container): upgrade head → mail, vocabulary, project → catch up all → downgrade `0005_watermark` (both tables gone, state rows `chronicle`, `source-stats` only) → upgrade head → `catch_up(GRAPH)` reports `rebuilt_from 0` and every event, rows == fold, the project has its row. Measured red with the `DELETE` removed from the downgrade (the `graph` state row survived); with that assertion also removed, red again at `(rebuilt_from, events) == (None, 0)` — the empty tables called up to date. Restored green.
- **M-1** Table count on `database-schema.md` measured: `metadata.tables` holds 10; line 138 "Three more tables hold projections" → "Five more". Intro (ten; three log, one register, one watermark, five projections) and the mermaid caption ("the three tables of the log and the blob register", four boxes) checked, correct.
- **M-2** `test_an_erased_rejection_lets_its_proposal_wait_again`: an objection rejected, then `redact_event` on the rejection → `(winner, pending, objections) == (anna, 1, 1)`, rows == fold, the rejection's row pruned (`p_graph_version` ids == `[anna, objected]`). The property now appends rejection ids to `history.versions`, so `_EraseVersion` erases rejections. Mutation M8 (an erased rejection touches only itself — `known[target].subject` skipped for kind `rejection`): dedicated test red, **property red** too now.
- **M-3** `test_an_objection_against_an_erased_direct_version_still_waits`: second direct version D, model objection O (`contests=D` by the write path), `redact_event(D)`, catch up (D pruned, asserted), later model version → `(winner, pending, objections) == (anna, 2, 1)`, rows == fold. Mutation M9 (`_named` reads only `approves`): dedicated test red; property green (stated in its docstring, like M6).
- **M-4** Concurrency test now: six events after a first catch-up, batch size 2. The first holds its first batch until the second waits on a lock; each thread checks `_rows == _folded` right after its own `catch_up` returns (`seen == {first: True, second: True}`), both took batches (`events >= 2` each, sum 6), then rebuild equality. Five repeated runs green. Mutations: `lock_projection_state` without any lock → red (`UniqueViolation` on `p_graph_version_pkey`); **only `FOR UPDATE` removed → now red too** (it was green with one batch). Docstring updated with both.
- **M-5** Wording names the period dates as the one claim value the projection holds, removed by the refold on erasure: `schema.py` comment, `contract/rows.py` (`GraphThreadRow`, refs now `graph-projection`), `projections.md`, `database-schema.md`. ⚠️6 comment in `schema.py` now names `p_graph_version.subject`.
- **Index** `p_graph_version_under_idx` on `under WHERE under IS NOT NULL` in `schema.py` and `0006_graph` (dropped in the downgrade); `class_subjects` docstring and the reference table follow. New `tests/test_schema.py::test_a_declared_partial_index_is_partial_in_the_database` holds `postgresql_where` against `pg_index.indpred` for every declared index; measured red with `postgresql_where` removed from the migration, the other indexes are the control.

Mutations of the first round still hold (unchanged code paths); the property docstring lists which it catches (M1–M5, M7, M8) and which only their dedicated tests catch (M6, M9).

Tutorial block retyped from one green `uv run pytest`: `collected 2746 items`, `2746 passed in 310.75s (0:05:10)`.
Commit: 518d438
