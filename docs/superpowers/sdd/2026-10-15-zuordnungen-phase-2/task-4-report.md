# Task 4 report — readers read from the projection, `project --check`

Status: DONE_WITH_CONCERNS. Commit `5323559` on `worktree-zuordnungen-2` (base `518d438`), not pushed.
Test count 2746 → 2760 (`2760 passed`).

## The protocol: `GraphStore[Conn]` (contract/store.py:244)

Read-only, beside `ProjectionStore` (decision 6). Methods:

- `read_graph_threads(conn, *, kind=None, types=None)` — rows of `p_graph_thread` by subject (the former test-only method, now in the protocol, keyword args added).
- `graph_relations(conn, *, at, types, start, to, touching)` — relations that stand (`state='standing'`) and point at an entity (`to_entity IS NOT NULL`), as `Graph.relations` takes them; `at` → period holds (both ends inclusive, open end holds).
- `graph_waiting(conn)` — `pending > 0 OR level = 'open'`; `graph_objected(conn)` — `objections > 0`.
- `graph_version_ids`, `class_subjects` — the `ProjectionStore` methods, redeclared (a reader needs them to fold a thread from the log).
- `graph_subjects(conn)` — every subject of `p_graph_version`, for a reader that walks every thread (fallback).

`PostgresStorage` implements them (storage/postgres.py:1049–1110). Pyright proof: `tests/test_projection_store.py::test_postgres_storage_satisfies_the_read_protocol_of_the_graph`.

**Members for Task 5:** `read_brackets(log, store, conn, bracket) -> Members` (core/graph_read.py) builds `BracketEdge`s from `graph_relations(types=hierarchy|assignments)` rows (start_entity or `Source(start_event, start_units)`, to_entity, level) with `bracket_kinds(read_vocabulary(log, conn))`; reads nothing of the log but the vocabulary. **Deviation from the brief's signature** `read_brackets(log, projection, graph_store, conn, bracket)`: the catch-up cannot run inside a snapshot that is already open (REPEATABLE READ would not see it), so the caller catches up before opening `conn`; `read_brackets` takes no `ProjectionStore`.

## Design: `ProjectedGraph` (core/graph_read.py, new)

The readers kept their code; the `Graph` they get changed.

- `Graph` (core/graph.py) gained reader questions, each a walk over every thread: `winners(kind, *, types)`, `entity_kinds()`, `relations(*, at, types, start, to, touching)` (extended), `waiting()`, `objected()`, `under(class_ids)`. `entities()` uses `winners`. Behaviour for the fold is the same as before (the old loops became these methods).
- `ProjectedGraph(Graph)` overrides each: ask `GraphStore` which subjects, fold those threads from the log (`fold_threads`), and ask **the same base method** of a `Graph` of them — so the answer is computed by the same code on the same threads as the whole fold. Relation ends are folded alongside (prefetch). `entity_kinds` is read off the rows (no log read).
- `threads` is `ThreadsFromLog`, a lazy `Mapping`: any lookup folds that thread from the log (batched via `load`), so a reader can never meet a missing thread (a missing end would otherwise read as "erased" in `GraphView.verdict` and withhold nothing — fail-open). Iteration folds every thread there is (correct, slow; the converted readers don't iterate).
- `GraphIndex` holds store and conn: dataclass fields are runtime-evaluated (pyproject `runtime-evaluated-decorators`), and `contract.store` is imported for the type checker only (its docstring says nothing imports it at runtime).
- `core/projection/graph.py`: the refold was extracted into public `fold_threads(log, conn, subjects, ids, classes)` (used by both the catch-up and the reader) and `_classes` became public `class_states(log, conn, up_to)` (used by `--check`).
- Ruling T4-a holds: everything shown is folded from log rows (`events_by_id`); the projection supplies only which subjects. The filters of `Graph.entities()`/`relations()` are re-applied by construction (the base method runs on the folded threads), so retracted winners and questions in `p_graph_thread` are filtered exactly as before.
- MCP `GraphView` (mcp_server/read.py:899) reads the source events of a thread lazily (`more` reader) when a thread is asked about that `graph_view` did not read; without `more`, `SourceEvents.named` still refuses (fail-closed).

## Every reader switched (file:line at 5323559)

CLI (each: `_caught_up(storage)` = `catch_up(storage, storage, GRAPH)` cli.py:3439, silent, then a snapshot and `projected_graph`; printing moved inside the snapshot because threads load lazily):
- `entities` cli.py:3454 — `graph.winners(ENTITY, types=…)`, `graph.entity_kinds()` (replaces `_kinds_of`, removed).
- `relations` without `--as-of` cli.py:3513 — `graph.relations(at, types, start, to)`; `--as-of` keeps `read_graph(as_of=…)` cli.py:3515 (decision 7), no catch-up.
- `entity ID` / `entity ID --history` cli.py:3678 — page uses `graph.relations(touching=ID)`.
- `triage` cli.py:3758, `status` cli.py:3783 — `_waiting` walks `graph.waiting()`.
- `classes list` cli.py:3891 and `classes sample` cli.py:3925 — **read the projection**: `hit_rates`/`sample` (core/classes.py:524, :552) walk `graph.under(graph.classes)`, the threads with a version under a class (`class_subjects`), and only those are folded. Exact: both functions only count versions whose `under` is a known class.

MCP:
- `Service.answer` server.py:983 catches up (own transactions, before the snapshot), then `Service.read_graph` server.py:910 builds the projected graph.
- Header `objections_seen` read.py:1023 — `graph.objected()`: rows with `objections > 0`, folds those, policy only for those.
- `list_entities` read.py:1343 (`graph.winners(ENTITY)`, `graph_view(subjects=…)`), entity page relations read.py:1212 (`relations(touching=…)`), subject branch with `graph_view(subjects=(subject,))`.
- `list_triage` read.py:1379 (`waiting_versions` walks `graph.waiting()`), `graph_view(subjects=waiting)`.
- `graph_now` returns the call's graph; nothing else per call called `read_graph`.

## What still folds, and why

- Write path (`check_claims`/`write_claims`), and in the MCP server the write tools' `graph_of` (server.py:1682 → `read_graph` when projected) — decision 5: checks under the tip it locks; also `graph_version` walks every thread.
- CLI writes: `approve` cli.py:2623, `_rejection_of` :2661, `_stated` :3301, `answer` :3796.
- `relations --as-of` (decision 7). `verify`. `core/gaps.py` (`policy gaps`, not a graph listing — not touched).
- `project --check` folds by design (its oracle).

## `None` fallback decision

Kept, and named: `build_server`/`build_app`/`Service` take `graph: GraphStore[Conn] | None = None` **and** `projections: ProjectionStore[Conn] | None = None`; the server reads the projection only with both (like `locker` + `key`), else every call folds the log. Reason: `catch_up` needs a `ProjectionStore`, and `GraphStore` is deliberately read-only, so one parameter can't carry both without making the read protocol a writer; the codebase passes one object under two protocols elsewhere (`log`/`locker`, `catch_up(storage, storage, …)`). The fallback stays because it is the **oracle**: the MCP equivalence test compares a server with and without the projection. `run_stdio`/`run_http` make both **required**, and the CLI `mcp`/`serve` pass `graph=storage, projections=storage`. The test helpers `_tool` and `_writer` now pass both, so every phase-1 MCP test (assertions unchanged) runs against the projection — they are the control; the m2 mutation shows a phase-1 listing test going red without catch-up. Direct `build_server(world.storage, …)` calls elsewhere in tests (non-graph tools) still use the fallback.

## `previously project --check` (cli.py:1471)

Catches up every projection and prints the usual three lines, then in a snapshot folds the assertions with `id <= up_to_id` of `graph` under `class_states(up_to_id)` (`check_graph`) and compares every `p_graph_thread` row (`differences`): `graph\t<subject>\t<what>` with `COLUMN P instead of F, …`, `no row instead of winner N`, `winner N instead of no row`; values `-`, `true/false`, ISO dates, comma lists. Exit 0 / 1. Writes nothing beyond the catch-up (a falsified row is reported on every run until a rebuild). Race documented: an erasure committing between catch-up and comparison can show as a difference the next run doesn't report.

## Tests

New `tests/test_graph_read.py` (6): every question of `ProjectedGraph` equals the fold on a history with one thread of each kind (retracted, objection, open proposal, transitive under a class, period relation, question, rejected proposal, assignment of a mail and of a unit, part_of, erased version), with assertions that each question has a non-empty answer; lazy loading (opening reads no thread, a thread is read once, `waiting()` reads what waits + candidate ends and not other threads); walking every thread equals the fold; `graph_relations` narrowing incl. inclusive period ends; `differences` (missing, extra, changed columns incl. None/bool/date/tuple forms; clean control); `read_brackets` equals `members(bracket_edges(fold))` for every bracket, open proposal included.

`tests/test_projection_graph.py`: the Task 3 property now also runs `_readers_agree` after every catch-up — all questions of the projected graph vs the fold for every thread, and `read_brackets` vs `members(bracket_edges(fold))` for every entity (the Hypothesis sample of the brief; ~23 s unchanged at 60 examples).

`tests/test_cli.py` (3): `test_the_listings_read_from_the_projection_are_those_the_fold_gives` (Vellenfeld + Markus + retraction, period, class + transitive, proposal, objection, question; 17 commands; oracle = same commands with `previously.cli.projected_graph` monkeypatched to `read_graph`); `test_a_listing_catches_the_projection_up_before_it_reads` (writes through `core`, nobody runs `project`); `test_project_check_is_clean_after_a_history_and_names_each_row_falsified_by_hand` (clean after a history with an erasure; UPDATE/DELETE → three lines, reported twice, `project` without `--check` silent, rebuild → clean).

`tests/test_mcp_server.py`: **replaced** `test_a_call_folds_the_graph_once_for_its_header_and_its_body` by `test_a_call_reads_no_assertion_in_full_and_of_the_graph_only_what_is_new` (`_CountingReads` counts `read_by_kind('assertion')` and every assertion row from `read`/`events_by_id`: zero full reads for list_entities, list_entities subject, list_triage, whoami; whoami with nothing new reads **no assertion row at all**; after one new version, exactly `{new}`; control: the fallback server folds once). Added `test_the_reading_tools_answer_from_the_projection_as_from_the_fold` (10 calls × 2 clients, header included, untagged fences, no error results; includes a relation resting on a mail no entity rests on) and `test_a_call_catches_the_projection_up_before_it_reads`.

Phase-1 listing tests: unchanged.

## Mutations (each change → red; restore → green), harness in the scratchpad, run on the final tree

| Mutation | Red | Control green |
|---|---|---|
| m1 CLI reader without catch-up (`_caught_up` does nothing) | catches_up test, listings-equivalence test | test_graph_read.py (6) |
| m2 MCP call without catch-up | catches_up, counting test, phase-1 header test, phase-1 `list_entities` test | — (all four red, as intended) |
| m3 `--check` compares nothing (`differences` returns `[]`) | `project --check` test, `differences` test | questions-equivalence test |
| m4 header reads no objection (`objected` from no rows) | phase-1 header test, questions test, **property alone** | phase-1 `list_entities` test |
| m5 `GraphView` reads no more events | MCP equivalence test | phase-1 `list_entities` test |
| m6 period end exclusive in SQL | store-narrowing test | walking-every-thread test |
| m7 `graph_waiting` without `level='open'` | catches_up test, questions test, phase-1 MCP triage test, **property alone** | differences test |
| m8 `relations(touching)` passes a wrong end to SQL | phase-1 CLI entity page test, phase-1 MCP `list_entities` test | differences test |
| m9 `under` from no rows | listings-equivalence test, questions test, **property alone** | catches_up test |

Two rounds were needed for m5: first green because every relation rested on the mail its ends rest on, then green again because both servers failed alike and the comparison didn't check `is_error`. Fixed (relation on `html_only`, `assert not result.is_error`), then red.

## Counts re-measured

- `contract/store.py`: `grep -rl LogStore src/previously/core --include='*.py' | wc -l` → **16** (+ `core/graph_read.py`); method command → **15** (unchanged; it calls `read_by_kind`, `events_by_id`); `LogStore` declares 16 (unchanged); `grep -ohE 'log\.[a-z_]*\(' src/previously/mcp_server/*.py | sort -u | wc -l` → **8** (unchanged). Docstring updated with dates.
- `pyproject.toml` T201: measured 96 at HEAD (`git show HEAD:…` into the scratchpad) and **97** now (`project --check` line); comment updated. The reader catch-up prints nothing (a stderr rebuild line was tried and dropped: it changed a phase-1 test's stderr).
- Tutorial test block retyped from one green `uv run pytest`: `collected 2760 items`, `2760 passed in 323.30s (0:05:23)`.

## Docs (plone-doc-style:author loaded)

`reference/cli.md`: `project [--check]` synopsis, option table, `(cli-project-check)=` section with the line forms and exit codes, the exit-code table row, a paragraph that the graph listings catch up and read the projection (and what folds). `reference/mcp-tools.md` header section: catch-up per call, what reads the projection, writes fold. `explanation/projections.md`: new `(graph-readers)=` "How a reader reads it" (catch up then snapshot, rows select / log shows, same code on folded threads, header, what still folds, `--check`); the limits paragraph names `--check`. `explanation/graph.md` (graph-cost): phase-1 tense, readers now read the projection, writes still fold. `explanation/module-boundaries.md`: the fifth protocol. `how-to/rebuild-a-projection.md`: "Check the graph projection against the log", and run `project` after deploying a version bump (readers catch up silently, the first would wait for the rebuild).

## Gates (final tree, 2026-10-15)

```
uv run ruff check .                     All checks passed!
uv run ruff format --check .            143 files already formatted
uv run pyright                          0 errors, 0 warnings, 0 informations
uv run lint-imports                     Contracts: 9 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing
                                        2760 passed in 327.67s; TOTAL 98% (97.69%);
                                        core/graph_read.py 97% (the four `_cell` lines,
                                        covered since by the extended differences test),
                                        core/graph.py 100%, storage/postgres.py 100%
make -C docs html                       build succeeded
make -C docs vale                       0 errors, 0 warnings and 0 suggestions in 50 files
make -C docs linkcheck                  build succeeded
```
The first full run (before the stderr line was dropped) also hit the known Task 3 flake `test_two_catch_ups_at_once_…` (second reader took 0 events); green alone and in both later full runs.

## Concerns

1. **Cost is shifted, not measured.** `list_entities` (MCP) and `entities`/`relations` without filters still fold every entity/relation thread from the log via `events_by_id` (they show every winner and need versions counts, pending versions, and — for MCP — the policy over all versions' sources). The gain there is reading only the kind asked for and no full `read_by_kind`; the header and `whoami` are where the cost goes away. Relation lines on an MCP page are one `graph_relations` query per listed entity, and lazy lookups/`more` event reads are per thread (N+1 within a page). Not measured at scale (as instructed).
2. **Every call still reads all `approval_class` actions** (`read_classes` in `projected_graph`), and `log.actions` visits every action, `mcp_access` included — the same class of cost as the per-call policy read. Could be made lazy.
3. **Readers catch up silently**, also when a version bump rebuilds: the first MCP call or listing after such a deploy waits for the whole rebuild. Documented in the how-to; the handoff (Task 6) should say "run `previously project` after the upgrade".
4. **Selection trusts the projection.** Where the projection drifted (the two documented limits of Task 3), a reader shows or misses threads by the stale rows; content shown is still exact. `--check` reports it.
5. **`--check` race** with a concurrent erasure (documented). It also compares only `p_graph_thread`, not `p_graph_version`.
6. `read_brackets` signature deviates from the brief (no `ProjectionStore`; caller catches up) — Task 5 should know.
7. The `None`/two-parameter API is "only with both"; a caller passing one of them gets the fold silently.
8. Landkarte not touched (Task 6): points 1–3 may belong there.

---

# Fix round 1 (review `task-4-review.md`, ruling T4-b)

- **I-1, `--check` reads `p_graph_version` too.** `core/projection/graph.py` `rebuilt_versions(events)`: the rows a rebuild writes (every version; every rejection whose `of` names an earlier version, under its subject; nothing for an erased row). `core/graph_read.py` `version_differences` + `check_graph` returns thread lines, then version lines, same form `graph\t<id>\t<what>`: `version row COLUMN P instead of R, …`, `no version row instead of KIND of SUBJECT[ under ID]`, `version row KIND of SUBJECT instead of none`. `GraphStore` gained `read_graph_versions`. Test: `test_project_check_…` falsifies a missing, an extra (on mail 2) and a wrong (`under`) version row → three lines, each run. Since the property now calls `check_graph` (M-5), `rebuilt_versions` is held against the incremental table at every catch-up of every random history.
- **I-2, a reader holds the projection against its catch-up.** `GraphStore.projection_state` (now in the protocol); `core/graph_read.projection_stands(store, conn, outcome)`: same `version`, `up_to_id >= outcome.up_to_id`, row present. CLI: `_caught_up` returns `Outcome | None` and catches `ProjectionRebuilt` and `StorageError`; `_reader_graph` folds the log when the catch-up failed or the projection doesn't stand; one stderr line `…; this command folds the log instead` (`_graph_warning`). MCP: `Service.caught_up` (same catch, `logger.warning`), `Service.read_graph(conn, outcome)` (fold + `logger.warning` when it doesn't stand); nothing in the result. `graph_now` outside a call now folds (nothing calls it; docstring says so). Tests: CLI `test_a_listing_folds_the_log_when_the_projection_was_rebuilt_since_its_catch_up` (catch_up wrapped: after the real one, `UPDATE projection_state SET version = 7` and both tables emptied) and `…_when_its_catch_up_fails` (`ProjectionRebuilt`), each: `entities`, `triage`, `status` equal the outputs before, exit 0, exactly one stderr line. MCP `test_a_call_folds_the_log_when_its_projection_does_not_stand_and_says_so_only_in_the_log[rebuilt|failed]` (stores `_RebuiltAfterCatchUp`: version moved and tables emptied in `snapshot()`; `_CatchUpFails`: `lock_projection_state` raises `OperationFailed`): four calls equal the fold server's, header with the objection, no error, `projection` not in the result, exactly one warning per call in the log. Core `test_the_projection_stands_where_its_catch_up_left_it_or_the_reader_folds` (version, `up_to_id` behind, no row; control after each re-catch-up).
- **M-1.** `Service.__init__` raises `ValueError("graph and projections are the two stores of one projection: give both or neither")`; `build_server`/`build_app` reach it. Test with both/neither as control.
- **M-2.** `_http`/`_over_http` pass the projection (optional `storage=`); the working-language test passes both stores. New `test_over_http_a_call_reads_the_graph_from_the_projection` (`_CountingReads` through `build_app`: header with the objection, `folds == 0`).
- **M-3.** "one query" → "two short transactions: one locks the state row, and the other locks it again and finds the tip" (`cli.py` `_caught_up`, `projections.md`).
- **M-4, partly not done, deliberately.** Passing `listing.types` into SQL for MCP `list_entities` breaks the phase-1 rule that a withheld entity's placeholder passes every filter so the client never learns its kind (`mcp-tools.md:418`; `test_list_entities_filters_by_kind_state_and_proposals_and_shows_a_history`, "A placeholder passes the filter, whatever its kind") — measured: with `graph.winners(ENTITY, types=listing.types)` that phase-1 test goes red (m10). Kept as is; `graph.md` now says exactly what each reader folds, MCP `list_entities` every entity on every page and why.
- **M-5.** The property calls `check_graph(…, state.up_to_id) == []` after every catch-up; docstring says so.
- Docs: `cli.md` (`--check` both tables, line forms, the two stderr lines of a reader), `mcp-tools.md` (fallback, log only), `projections.md` (`--check` on version rows; new paragraphs on a reader during a rebuild and a rolling update), `graph.md` (what each reader folds), how-to (`a thread or a version row`).

## Mutations (fix round), each → red; restore → green

| Mutation | Red | Control green |
|---|---|---|
| f1 `version_differences` returns `[]` | `project --check` test | thread `differences` test |
| f2 `rebuilt_versions` writes no rejection rows | property (alone) | `project --check` test (no rejection in its history) |
| f3 CLI without `projection_stands` | rebuilt-since test | failed-catch-up test |
| f4 CLI catch-up error not caught | failed-catch-up test | rebuilt-since test |
| f5 MCP without `projection_stands` | `…does_not_stand…[rebuilt]` | `[failed]` (2 passed) |
| f6 MCP catch-up error not caught | `[failed-auto]` | `[rebuilt-auto]` |
| f7 one store accepted | one-store test | — (its control is in-test: both / neither) |
| f8 `build_app` doesn't forward the stores | HTTP test | stdio counting test |
| f9 `projection_stands` ignores `up_to_id` | core stands test | CLI rebuilt-since test (version case) |
| m10 (measures M-4) `types` in SQL for MCP | phase-1 filter test | phase-1 `list_entities` test |

## Counts

`T201` 97 → **98** (`_graph_warning`), measured with the command; pyproject comment updated. `LogStore` files 16, methods 15, MCP `log.` 8 — unchanged, re-measured. Tutorial retyped from one green `uv run pytest`: `collected 2770 items`, `2770 passed in 329.34s (0:05:29)`.

## Gates (2026-10-15, fix round)

```
uv run ruff check .                     All checks passed!
uv run ruff format --check .            143 files already formatted
uv run pyright                          0 errors, 0 warnings, 0 informations
uv run lint-imports                     Contracts: 9 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing
                                        2770 passed in 331.68s; 97.72%; core/graph_read.py 100%
make -C docs html                       build succeeded
make -C docs vale                       0 errors, 0 warnings and 0 suggestions in 50 files
make -C docs linkcheck                  build succeeded
```

## Open

- M-4's SQL filter (see above): a maintainer decision if the placeholder rule should change; nothing in this round changes it.
- `ProjectionGap` is not caught by the reader fallback (ruling names `ProjectionRebuilt` and `StorageError`); a gap still fails the call.
- A rolling update with two versions still makes each version rebuild the other's projection on every call (each call then folds — correct, but every call pays a rebuild in one of them); the handoff and how-to of Task 6 should say so.
