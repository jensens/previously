# Task 4 review — readers read from the projection, `project --check`

Reviewed: diff `518d438..5323559` (HEAD `5323559`), read in passes; brief, context (decisions 5, 6, 7, 10, 11, Review Focus 2, Global Constraints), ruling T4-a, the controller's decisions in the dispatch.
No test was run.
Counts re-measured against the tree: `grep -rl LogStore src/previously/core --include='*.py' | wc -l` → 16; the `T201` command → 97; `grep -ohE 'log\.[a-z_]*\(' src/previously/mcp_server/*.py | sort -u | wc -l` → 8. All three match the comments.

**Spec: ❌** — one item: decision 11 and Step 1 of the brief ("`--check` compares the projection with the fold and reports every difference"; "a row falsified by hand is reported") hold for `p_graph_thread` only (I-1). Everything else in the dispatch is met: `GraphStore` read protocol; every CLI and MCP reader catches up, then reads; `--as-of`, the write path, `verify` fold; the header selects `objections > 0` and asks the policy only for those; no `read_by_kind('assertion')` when nothing is new; `build_server(..., graph=None)` fallback; `project --check` prints lines on stdout, exits 0/1 and writes nothing beyond the catch-up; phase-1 listing tests unchanged; the oracle is the fold.

**Quality: Changes requested** — 0 Critical, 2 Important, 5 Minor, plus ⚠️ items.

## Answers to the named risks

1. **Policy: holds.**
   Every `ProjectedGraph` override takes subjects from SQL, folds those threads from the log, and runs the *base* method on them (`graph_read.py` `winners`/`relations`/`waiting`/`objected`/`under`).
   So its answer is always a subset of the fold's answer, re-filtered by the same code.
   A stale or drifted row can hide a thread, but it can never add one.
   Header (`read.py` `objections_seen`): `graph.objected()` → base `objections()` on the folded threads → `view.seen` only for those, so the header counts only objections the client may see, as before.
   A thread with pending versions or objections always has a winner, and so always has a row (checked against `GraphThread._waiting`/`winner`), so `graph_waiting`/`graph_objected` miss nothing the fold has.
   Placeholders and triage go through the same `GraphView.verdict`.
   Ends are folded lazily on lookup, and `GraphView._read` reads their source events through `more`; without `more` it fails closed.
   `entity_kinds()` reads rows, but only on the CLI, where no policy applies.
2. **Freshness: holds for content.**
   Every CLI reader calls `_caught_up` before `storage.snapshot()`.
   `Service.answer` catches up before its snapshot, for stdio and HTTP alike, and `run_stdio`/`run_http` require both stores.
   An erasure committing between catch-up and snapshot nulls the payload (the cascade runs at erasure time in `core/redact.py`, through `stands_on_erased`).
   `fold_threads` reads by id and skips a `None` payload, so erased content never shows.
   A version written in that window is simply absent: the fold uses only the ids in `p_graph_version`, which is consistent staleness.
   The window does matter for one thing: a *rebuild* in between (I-2).
   The only uncaught-up path is `Service.graph_now` outside a call, which has no production caller (⚠️).
3. **Unchanged control: mostly.**
   The phase-1 tests in `test_mcp_server.py`, `test_cli.py` and `test_projection_graph.py` are unchanged apart from the helpers `_tool`/`_writer` and the one replaced test.
   The CLI has no fallback, so every phase-1 CLI test runs against the projection.
   On the MCP side the report says every phase-1 MCP test does too, and that overstates it (M-2).
4. **Cost.**
   The counting test counts what it says: `read_by_kind('assertion')` is 0 for `list_entities`, `list_entities subject`, `list_triage` and `whoami`.
   `whoami` with nothing new reads no assertion row at all, and with one new version it reads exactly `{new}`.
   The in-test control (the fallback server folds once) shows the counter sees a fold.
   No reader still does a full `read_by_kind('assertion')`: `graph_rejections` is reached only from `write_reject`.
   `read_classes` reads `approval_class` actions per call, which is the same as in phase 1.
   MCP `list_entities` still folds every entity thread, and reads the source events of all of them, on every page (M-4).
5. **`--check`.**
   `differences` compares the whole `GraphThreadRow` (winner, level, state, both start forms, to, candidates, period, pending, objections, question), so the column coverage is complete.
   It compares only `p_graph_thread`, though (I-1).
   The spurious difference under a concurrent erasure is acceptable as documented (⚠️).
6. **Replaced phase-1 test.**
   It is not listed as measured red against a reader that folds.
   But its own control (the fallback server, `folds == 1`) is that mutation for `whoami`.
   For the other calls, any `read_graph` raises `folds` above 0.
   Accepted (⚠️).

## Important

**I-1. `--check` doesn't look at `p_graph_version`, yet the readers now depend on it.**
`src/previously/core/graph_read.py:298-310` (`check_graph`) compares `store.read_graph_threads(conn)` against the fold; `cli.py:1471-1490`.
Since this task, the threads a reader *shows* are folded from `graph_version_ids` (`projected_graph`, `graph_read.py:210`), which means from the rows of `p_graph_version`.
Suppose a version row or a rejection row is missing there, extra, or carries the wrong `subject`/`under`, by hand or by a fault nobody has found yet.
Then the reader shows a thread different from the fold's: a rejected proposal reads as pending, or a version is missing from a history.
`p_graph_thread` can still agree with the fold, so `--check` exits 0.
That is the silent drift decision 11 exists to rule out ("ihr Fehler darf nicht still bleiben"), and the brief's falsified-row requirement doesn't hold for this table.
The report names the gap (concern 5) but does not close it.
Fix: hold `p_graph_version` against what a rebuild would write (the Task 3 property already proves the rebuild equals the incremental path), with a line form of its own, such as `graph\t<id>\tversion row …`.
Then add a falsified version row to `test_project_check_…` and measure it red.

**I-2. A reader doesn't check, in its snapshot, that the projection stands where its catch-up left it.**
`cli.py:3439` (`_caught_up`) and `server.py:983` return the `Outcome` and throw it away.
The snapshot then reads whatever `p_graph_thread` holds.
Two routine operations truncate the projection between a reader's catch-up and its snapshot:

- the forced rebuild the how-to describes (`truncate_projection` plus deleting the state row);
- a catch-up by code at another `GraphProjection.version`, since `worker.py:128` uses `!=`.

The reader then lists an empty or half-built projection: no entities, a header of 0, an empty triage.
Nothing says so.
It is no leak, since the result is a subset, but it is a wrong answer given as a right one.
With two versions live at once, which is a rolling update in kup6s or an old pod beside the new release's CronJob, it gets worse.
Every MCP call of each version truncates and rebuilds the other's projection, and the call whose catch-up loses raises `ProjectionRebuilt` and answers with the generic failure.
Phase 1's server never touched a projection, so this operational coupling is new, and *Operations are part of every design* asks for it to be considered.
Fix (cheap, and the oracle path exists): in the snapshot, read `projection_state(GRAPH)`.
If its version is not `GRAPH.version`, or its `up_to_id` is below the catch-up's `outcome.up_to_id`, fold the log for this call (`read_graph`) instead of reading the rows.
Add a test that truncates between the catch-up and the read, measured red without the check.
The ping-pong across versions belongs in the handoff and on the how-to page (Task 6).

## Minor

**M-1. A silent fallback when only one of `graph`/`projections` is passed.**
`server.py:908`.
A caller that passes one gets the fold and no word about it.
`run_*` require both, but `build_server`/`build_app` don't.
Raise `ValueError` for one of the two, as `build_server` already refuses a bad language.

**M-2. The HTTP path with the projection is untested, and the report's control claim overstates.**
`tests/test_mcp_server.py:1027` (`_http` → `build_app` without `graph`/`projections`).
`:3389` (the working-language heading test, a phase-1 `list_entities` test) builds a server without the projection, too.
So those run on the fallback, not against the projection.
With the silent fallback (M-1), a `build_app` that stopped forwarding `graph=`/`projections=` would pass every test.
Let `_http` pass both stores.

**M-3. "Nothing new costs one query" is a claim, and it is wrong.**
`cli.py:3441-3442`, `docs/explanation/projections.md:337`.
`catch_up` runs two transactions: `lock_projection_state` (an insert-on-conflict and a `SELECT … FOR UPDATE`), then the lock again plus `tip`.
Say "two short transactions", or count the statements.

**M-4. MCP `list_entities` folds every entity on every page.**
`src/previously/mcp_server/read.py:1343`.
`graph.winners(ENTITY)` is called without `listing.types` (the CLI passes `types` to SQL), and `graph_view(..., standing)` reads the source events of every entity.
`docs/explanation/graph.md:207` says the readers "fold only the threads they show", which overstates this case.
Pass `types` through, and either narrow the page or word the page claim to match.

**M-5. "`--check` is clean after every sequence" is asserted for one CLI history only.**
`tests/test_projection_graph.py`, `_CatchUp` step.
The property checks `_rows == _folded` but never calls `check_graph`, whose oracle (`class_states(up_to)`, `id <= up_to`) is a different code path.
`assert check_graph(storage, storage, conn, up_to) == []` beside `_readers_agree` costs one line.

## ⚠️ (for the controller, not defects of this task)

- **`read_brackets` deviates from the brief's signature** (`graph_read.py:226`, no `ProjectionStore`; the caller catches up).
  The reason holds, since a catch-up can't run inside an open snapshot.
  Task 5 must catch up before it opens `conn`.
  Its edges are rows only, with no log check, so an assignment erased after the catch-up still counts until the next one.
  Task 5 has to take what it *shows* from where the erasure already took it (the log, a chronicle caught up in the same order).
- **Concurrent erasure during `--check`** can print a difference and exit 1 once (documented on `cli.md`).
  That's acceptable for a manual check.
  If it runs from a CronJob as an alert, re-checking the differing subjects after a second catch-up would remove the false positive.
- **The first call after a version bump** waits for the whole rebuild.
  The how-to says so; the handoff must say "run `previously project` after the upgrade" (Task 6), and see I-2 for the overlap.
- **Every MCP call's availability now depends on the graph catch-up.**
  A `ProjectionGap` or a `ProjectionRebuilt` fails every tool, `whoami` and `list_obligations` included.
  Decide whether that's wanted, or whether a failed catch-up should fall back to the fold (I-2's fix gives that path).
- **`Service.graph_now` outside a call** reads the projection without catching up.
  Nothing in production calls it; the docstring could say so.
- **The replaced counting test** isn't in the mutation table as "a reader that folds".
  Its in-test control is that mutation for `whoami`, and any `read_graph` on the other calls raises `folds`.
  Accepted.
- **Cost is unmeasured:** N+1 within a page (`graph_relations(touching=…)`, plus a lazy event read per relation) and `read_classes` per call.
  This belongs in the map as a point for later, together with the write path's fold.
- **Design judgement on `ProjectedGraph`: sound.**
  It runs the same code on the same threads; it is a subset by construction; `ThreadsFromLog` folds on any lookup, so no end reads as "erased" by omission.
  Walking `threads` stays correct and as slow as the log, and no converted reader walks it.
  `classes list`/`sample` reading the projection is exact: `class_subjects` gives exactly the threads with a version under a class event, and `hit_rates`/`sample` count nothing else.
