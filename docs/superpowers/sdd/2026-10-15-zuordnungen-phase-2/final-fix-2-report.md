# Fix round F2 — report (rulings F-c and F-d)

Base `a4c04f2`. Commits: `1edcf8a` (code, tests, docs), `96dac0f` (tutorial retyped).
No subagents dispatched. Nothing pushed.

## What changed, per point of the brief

### 1. Only `previously project` rebuilds

- `catch_up` (`core/projection/worker.py`) takes a keyword-only `rebuild: bool` **without a default**, so no caller rebuilds by leaving it out (pyright makes every call site name it).
  With `rebuild=False`, a missing state row or another version raises `ProjectionNotBuilt` inside the first transaction, which rolls back — the placeholder `lock_projection_state` writes for a missing row goes with it, so tables and state row stay untouched.
- Callers: `_cmd_project` → `True`; `_catch_up_after` (redact) → `False`; CLI readers, MCP server per call and at start → `False` via `graph_snapshot`.
  All tests that set up projections the way `project` does pass `True` explicitly.
- **New class `ProjectionNotBuilt(PreviouslyError)`** in `core/errors.py`, not `ProjectionRebuilt`.
  Why a new class: `ProjectionRebuilt` means "something rebuilt it *while* this ran" (a concurrency event, retry may help); `ProjectionNotBuilt` means "it is not at this code's version *when I looked*, and I may not build it" (a deployment state; only an operator action helps).
  Different remedies, different sentences, and `redact` needs to tell them apart (different advice tail).
  It carries `name`, `found`, `declared` and `finding` (the sentence without the advice), which `redact` uses.
  Sentences:
  - `projection graph is not built, and this code declares version 1; `previously project` builds it`
  - `projection graph stands at version 2, and this code declares version 1; the release that is to serve builds it with `previously project``
  The second advice deliberately doesn't say "run `previously project`" unqualified: the code cannot know whether it is the old or the new release, and an old pod's operator running its `project` would rebuild back.
- `redact`: `_unfinished` now has two static sentences. For `ProjectionNotBuilt` the outstanding part is `error.finding` and the tail is `run `previously project`, then the same command again` (the same command alone would stop again; `project` takes the redaction in while building). Other catch-up failures keep `projection X is not caught up (…); run the same command again`.
  The old behavior of `redact` naming a build/rebuild on stderr is gone (it can't build any more).

### 2. No reader falls back to the whole fold

- CLI: `_caught_up`, `_reader_graph`, `_graph_warning` removed. `_graph_snapshot(storage)` yields `(conn, projected_graph(...))` inside `core.graph_read.graph_snapshot`. Errors propagate to `main` (exit 2, one sentence).
- MCP: `Service.caught_up` / `Service.read_graph` removed; `Service.reading()` yields `(conn, graph)` from `graph_snapshot` (or the fold, only for a server built without the projection — see "Decisions").
  "The tool error the server gives any `PreviouslyError`" — found: there is no generic mapping; a `PreviouslyError` not converted to `Refused` by a tool lands in `Service.answer`'s `except Exception`, which logs `an MCP call failed` with the traceback and returns `_FAILED` (`Error: the call failed inside the server; its log says why, this result cannot`), access outcome `error`. That is what a projection error now gets. I kept it rather than showing the sentence to the client: the client can't run `previously project`, the operator reads the log, and readiness keeps traffic off such a pod anyway.
- `StorageError` goes the same way as everywhere (CLI: `main`'s sentence; MCP: `_FAILED` + log).
- Nothing is logged as a warning and swallowed any more; `PreviouslyError`/`StorageError` imports in `server.py` became unused and were removed.

### 3. One retry for a rebuild in between

`graph_snapshot` (`core/graph_read.py`, replaces `projection_stands`):
for up to `REBUILD_RETRIES + 1` attempts: `catch_up(..., rebuild=False)`, open `log.snapshot()`, read the state row there;
no row or another version → `ProjectionNotBuilt` immediately (**never retried**: a catch-up can't change a version — the controller's "a version mismatch is never retried");
`up_to_id` ≥ the outcome's → yield; else leave the snapshot and try again.
After the attempts: `ProjectionRebuilt("projection graph was rebuilt between catching it up and reading it, on each of 2 tries; read again once `previously project` has finished")`.
`REBUILD_RETRIES: Final = 1` with a comment saying why one: the second catch-up meets the projection at its own version and takes turns with the build at the state-row lock, carrying it to the tip; a second miss means a rebuild started again in that moment.
Same-version concurrent catch-ups need no retry (they take turns at the lock).

### 4. MCP server checks before it serves

- `build_server` (and so `build_app`, `run_stdio`, `run_http`) runs `catch_up(log, projections, GRAPH, rebuild=False)` after constructing `Service` when the projection is given; the error propagates, `previously mcp` / `serve` exit 2 with the sentence.
- `run_http` got `announce: Callable[[], None] | None`; `_cmd_serve` prints `serving MCP over HTTP on …` through it, after the app is built — so a refused start never claims it serves (the line stays the first stderr line on success, which the existing subprocess tests pin).
- Readiness (`ready` in `build_app`, wired via `guarded` in `mcp_server/auth.py`): with the projection, one read of the state row (`graph.projection_state`) in a snapshot instead of `log.tip`; not built / other version → 503. No catch-up.
  `guarded`'s `ready` now returns `str | None` (the 503 body or `None`), so the probe doesn't misname the cause: new `NOT_BUILT = "Error: the graph projection is not built at this server's version"` beside `NOT_READY` (database). One `WARNING` per failed probe: `the readiness probe found projection graph not built, and this code declares version 1` (or `at version N`).

### 5. The misleading warning — measured

`_transaction` (`storage/postgres.py`) now translates a `ProgrammingError` with SQLSTATE `42501` into a new `PrivilegeMissing(StorageError)` (`storage/errors.py`) with the server's `message_primary`; every other `ProgrammingError` stays `MigrationPending`.
Test `test_a_role_that_may_only_read_the_projection_is_told_so_and_not_to_migrate` (testcontainers): a role with SELECT/INSERT/UPDATE on all tables, then `REVOKE INSERT, UPDATE ON projection_state, p_chronicle, p_source_stats, p_graph_thread, p_graph_version`; `project` ran as owner first.

Measured 2026-10-15, what that role gets from `previously entities` / `status`:

| Tree | exit | stderr |
|---|---|---|
| `a4c04f2` (base, measured in a detached worktree with this test) | 0, output folded (5 / 3 lines) | `the graph projection could not be caught up (database schema incomplete — `previously migrate` has not run yet); this command folds the log instead` |
| this round without the 42501 branch (mutation) | 2 | `Error: database schema incomplete — `previously migrate` has not run yet` |
| this round | 2 | `Error: the role of PREVIOUSLY_DSN lacks a privilege on database test at localhost:<port>: permission denied for table projection_state` |

Control in the same test: that role's `chronicle --limit 1` (no catch-up) exits 0.

### 6. Kept, not touched

`verify`, `project --check`, `relations --as-of`, the write path (`read_graph` in approve/reject/answer/entity/relate), `graph_now`/`graph_of` in the server: unchanged. Documented as deliberate in `projections.md` and the `graph_read.py` module docstring.

### Residuals (ruling F-d)

- Map: the `cli.py teilen` point no longer carries line counts (the sentence holds without them; also dropped the "etwa Zeilen 2 995–3 950" range, which drifts the same way).
- `module-boundaries.md`: "hold no content beyond the period dates of a relation".

## Tests

Removed (they pinned the fallback): CLI `test_a_listing_folds_the_log_when_the_projection_was_rebuilt_since_its_catch_up`, `…_when_its_catch_up_fails`, `…_when_its_catch_up_meets_a_gap_in_the_log`, `test_chronicle_within_folds_the_log_when_the_projection_does_not_stand`, `test_redact_reports_a_rebuild_it_runs_on_standard_error`; MCP `test_a_call_folds_the_log_when_its_projection_does_not_stand_and_says_so_only_in_the_log`; graph_read `test_the_projection_stands_where_its_catch_up_left_it_or_the_reader_folds`.

Fixture changes (the operator's `project` after `migrate`): MCP `_world` builds all projections with `rebuild=True`; CLI `_connect` builds them on the empty log (and `_assertion_log` now goes through `_connect`); the two cascade CLI tests and the two `serve` subprocess tests run `project` first. Redact tests that expected `built:` lines on stderr now expect none.

### Mutations (each measured red; controls in the same run green)

Script: `mutate.py` in the scratchpad applies one textual change, runs the named tests, restores the file.

| # | Mutation | Red | Green (control) |
|---|---|---|---|
| m1 | `graph_snapshot` catches up with `rebuild=True` | graph_read `…meeting_a_projection_it_would_have_to_build…` ×2, CLI same ×2, MCP same ×4 (rows rebuilt / call answers) | graph_read `…rebuild_between_catch_up_and_snapshot…` |
| m2 | `REBUILD_RETRIES = 0` | graph_read retry-once, CLI `…catches_up_once_more…`, CLI `chronicle --within` [1] and [2], MCP `…once_more…_fails_on_a_second` ×2 | graph_read `…would_have_to_build…` ×2 |
| m3 | `REBUILD_RETRIES = 2` | graph_read `test_two_rebuilds_in_a_row_fail_the_reader_though_a_third_try_would_read`, CLI `…fails_on_a_second_rebuild_in_a_row_though_a_third_try_would_read`, CLI `chronicle --within`[2], MCP ×2 (each constructed so the third try would succeed, asserting it isn't taken) | graph_read retry-once, CLI `chronicle --within`[1] |
| m4 | `_catch_up_after` with `rebuild=True` | CLI `test_redact_does_not_rebuild_and_names_project_as_what_finishes_it` ×2 | `test_redacting_twice_says_already` |
| m5 | `_cmd_project` with `rebuild=False` | CLI `test_project_on_an_empty_log_is_up_to_date_at_zero_but_still_names_a_rebuild`, `test_project_rebuilds_a_chronicle_built_at_version_1`, `test_project_check_is_clean_after_a_history_and_names_each_row_falsified_by_hand` | `test_redact_event_prints_the_redaction_and_show_names_it` |
| m6 | start catch-up removed from `build_server` | MCP `test_the_server_refuses_to_start_without_a_projection_at_its_version` ×2; separately CLI `test_mcp_and_serve_refuse_to_start_before_project_built_the_graph` | `test_one_store_of_the_projection_without_the_other_is_refused` |
| m7 | probe reads the tip only (`if True: log.tip`) | MCP `test_the_readiness_probe_is_not_ready_while_the_projection_is_at_another_version` | `test_the_readiness_probe_answers_without_a_token_and_records_nothing` |
| m8 | worker never raises `ProjectionGap` (`if False:`) | CLI `test_a_listing_whose_catch_up_meets_a_gap_in_the_log_fails_with_it`, MCP `test_a_call_whose_catch_up_fails_fails_and_folds_nothing[gap-*]` ×2 | MCP same test `[failed-*]` ×2 (storage error), CLI `test_a_listing_catches_the_projection_up_before_it_reads` |
| m9 | 42501 branch disabled (`"4250X"`) | CLI `test_a_role_that_may_only_read_the_projection_is_told_so_and_not_to_migrate` (got `database schema incomplete …`) | — (its own control: `chronicle` exits 0) |
| m10 | version mismatch in the snapshot treated as a miss (`if False:`) | graph_read `test_a_version_change_between_catch_up_and_snapshot_is_not_caught_up_again` | graph_read retry-once |

Injection without mocks: a `PostgresStorage` subclass whose `snapshot()` empties the projection at its own version before the first N snapshots (`_RebuiltBeforeSnapshot`), counting snapshots; CLI tests route `_storage()` to such a store by monkeypatching `previously.cli.from_dsn` (a real store over the test engine, as the existing tests patched `previously.cli.catch_up`). The MCP gap/failure stores are "armed" after `build_server` so the start check doesn't pre-empt them.

## Docs

- `explanation/projections.md`: "How a reader reads it" rewritten (one way to the graph; who builds; the retry and why one; why the fold fallback is gone — gap is damage, privilege/table is a fault of the setup the fold hid, the ping-pong; the cost figure is the measured phase-1 fold, >7 s per call at 100k, not the unsourced "17 s"); the catch-up-lock section, version-trigger, `project` path names, chronicle version history adjusted.
- `explanation/graph.md` (first build line), `concurrency.md`, `mcp-interface.md` (probe), `module-boundaries.md`.
- `how-to/rebuild-a-projection.md`: who builds; new section "Build the projections in the upgrade step" with what an operator sees if skipped and "During a rolling update" (old pods fail and go unready, new pods ready; rollback the same way); `DELETE` warning and `redact` paragraphs adjusted.
- `how-to/cut-a-release.md`: notes must name `previously project` after `migrate` when a projection version changes or `0006_graph` arrives, with a `git diff … | grep version` command (checked: since `v0.1.0a7` it prints the new graph version line). `run-the-image.md`: section "Build the projections next". Prerequisites of `keep-a-club-and-its-offices.md` and `connect-claude-code-and-vibe.md` name `project`; `erase-something.md` the new redact advice.
- `reference/cli.md`: privilege error, redact third form, exit-code rows, `project` only builds, graph readers' three sentences, `mcp`/`serve` refusal, the `/healthz` second body. `reference/mcp-tools.md`, `reference/database-schema.md`.
  `tests/test_docs_references.py` holds the new quotes: `PrivilegeMissing` against `postgres.py`, `NOT_BUILT` against `auth.py`, the two `ProjectionNotBuilt` sentences produced whole from the class, the retry sentence against `graph_read.py`, the redact outstanding phrase against `finding` in `core/errors.py` (the `; run ` split now takes either tail); counts in that test's docstring updated (nine → ten errors).
- Handoff (English, kept English): new section "`previously project` after the migration, before the release serves" as requirement + why + what an operator sees + "It stands when"; rolling-update section rewritten; role section says what a role without privilege now gets; "run project after an upgrade" became "after a bulk ingest"; compose paragraph and checklist.
- Map (German): struck "Eine fehlende Berechtigung meldet sich als unvollständiges Schema" and "Eine Rolling-Update-Lücke ohne Lösung" into *Erledigt* naming PR #26; "Der Rückfall … stehen zweimal" reduced to the bracket check; "Die Zeilensperre … kein Zeitlimit" replaced by the two watch points (a) catch-up after a large import (threshold > 1 s; counter-measures write path then `LISTEN/NOTIFY`; maintainer: 10,000-mail imports unlikely/very rare) and (b) build time vs upgrade window (linear, 34.6 s at 100k; beyond: shadow tables and switch); status row of phase 2 updated. Open-point count by the CLAUDE.md command: 244.
- Tutorial: typed test run retyped from one green run at the final tree.

## Gates (final tree)

All six at `96dac0f`, measured 2026-10-15:

```
uv run ruff check .                 All checks passed!
uv run ruff format --check .        143 files already formatted
uv run pyright                      0 errors, 0 warnings, 0 informations
uv run lint-imports                 Contracts: 9 kept, 0 broken.
uv run pytest --cov ...             2824 passed in 441.17s; TOTAL 11444 stmts, 243 missed, 98 %
make -C docs html / vale / linkcheck   build succeeded / 0 errors, 0 warnings, 0 suggestions in 51 files / build succeeded
```

New and changed modules: `core/graph_read.py`, `core/errors.py`, `core/projection/worker.py`, `storage/postgres.py`, `storage/errors.py` at 100 %; the uncovered lines in `server.py` near the change (`run_stdio`, `run_http`'s `announce`/`uvicorn.run`) run only in the subprocess tests, as before.
The tutorial's typed run was retyped from a green plain `uv run pytest` at `1edcf8a` + the provisional count (2824 passed in 426.96s), `rootdir:` left out as before.

## Decisions the brief did not settle

1. **`ProjectionNotBuilt` is a new class** (argued above). Its version-mismatch advice names "the release that is to serve" rather than plain `previously project`.
2. **MCP error text**: the projection error reaches the client as the generic `_FAILED` tool error, reason in the server log (the existing path for any unconverted `PreviouslyError`), not as `Refused` with the sentence.
3. **The projection-less MCP server stays** (`build_server` without `graph`/`projections` folds per call). It is a construction mode, not a fallback: `run_stdio`/`run_http` require both stores, and the tests use it as the oracle. Flag if the maintainer wants it gone too.
4. **Readiness body**: a second 503 body (`NOT_BUILT`) instead of reusing "the database does not answer", which would misname the cause (point 5's spirit). `guarded`'s `ready` contract changed from `bool` to `str | None`.
5. **`run_http(announce=…)`** so `serve` prints its line only after a successful start.
6. **Version mismatch found in the snapshot raises at once** rather than costing a retry (the controller's rule; m10 pins it).
7. **Test fixtures build projections** (`_world`, `_connect`) to mirror the upgrade step; a fresh database now needs `previously project` once before any graph reader or the MCP server — documented in the how-tos and the handoff.
8. A `PrivilegeMissing` inside the readiness probe still falls into the probe's generic `except Exception` (503, `NOT_READY` body, traceback in the log). Reading the state row needs only SELECT, so I left it.

## Concerns

- Rolling update cost is now explicit: between the start of the new release's `project` and the replacement of old pods, old pods' graph calls fail (by design, ruling F-c). The handoff and how-to say it.
- A brand-new install must run `previously project` once before `entities`/`serve`; the error says so, the docs say so, but it is a new step for anyone following an older guide.

## Re-fix (review findings and rulings F-e, F-f)

Base `96dac0f`. Commits: `e63e711` (code, tests, docs), `9b4ffef` (tutorial retyped).
M-4 isn't built, per ruling F-f; it's listed (see below).

Mutations were run with the same `mutate.py`, each on its named tests: red where listed, green controls in the same run, and `src` restored after each.

| Finding | What changed | Mutation → red | Control (green) |
|---|---|---|---|
| **I-1** | `_catch_up_after` returns one of three tails. A projection that isn't built gets "run `previously project`, then the same command again". A projection at another version, in either direction, gets "the release that is to serve builds it with `previously project`, then run the same command again". Everything else gets "run the same command again". `_unfinished` builds three static sentences. The test gained `newer-version` (4 > 3); `reference/cli.md` quotes the fourth form and gives the reason; `erase-something.md` says what to do. | r1: every `ProjectionNotBuilt` gets the plain advice → `[older-version]`, `[newer-version]` | `[no-state-row]` |
| **M-1** | The probe catches `PrivilegeMissing` and answers 503 with a new constant `NOT_PERMITTED` ("Error: the database refuses this server's role a privilege it needs"), plus one WARNING line, no traceback. New test with a role that has no grant on `projection_state`; `reference/cli.md` quotes the body, and `test_docs_references` holds it against `auth.py`. | r2: branch removed → `test_a_role_the_database_refuses_makes_the_probe_say_so_in_one_line` (gets `NOT_READY` and an ERROR) | `test_a_database_that_refuses_costs_the_probe_one_line_without_a_traceback` |
| **M-2** | `Service.answer` turns `ProjectionNotBuilt`, `ProjectionRebuilt`, `ProjectionGap` and `StorageError` into `logger.warning("an MCP call failed: %s", error)` with no traceback. The client text is unchanged. The test pins level WARNING, no `exc_info`, and the sentence. | r3: back to `logger.exception` → `test_a_call_meeting_a_projection…` ×4 | `test_a_failed_call_writes_an_access_with_the_outcome_error` |
| **M-3 / F-e** | `graph_now()` takes no connection; outside a call it raises `RuntimeError`. | r4: fold restored → `test_the_graph_of_a_call_is_none_outside_a_call` | `test_the_reading_tools_answer_from_the_projection_as_from_the_fold` |
| **F-e** | `Service`, `build_server` and `build_app` require `graph` and `projections`. The one-without-the-other `ValueError` and `self.projected` are gone, and so is the fold branch of `Service.reading`. `graph_of` always folds (the write path). The probe always reads the state row (no `log.tip` branch). `reader_bracket_edges` refuses a non-projected graph with `TypeError` instead of `bracket_edges` over a fold. | r5: fold branch back → `test_a_reader_finds_a_brackets_edges_in_the_projection_and_refuses_a_fold`; r7: probe ignores the version → readiness version test | r5: `test_the_members_of_a_bracket_read_from_the_projection_are_those_of_the_fold`; r7: probe without token |
| **F-e oracles** | The three equality tests hand in the fold themselves: `_fold_instead` for `previously.mcp_server.server.projected_graph`, and `_edges_of_the_fold` for `previously.mcp_server.read.reader_bracket_edges` (and `previously.core.graph_read.reader_bracket_edges` in the CLI `--within` oracle), by `monkeypatch`, as the CLI oracles already did. `test_one_store_of_the_projection_without_the_other_is_refused` is removed. All 17 MCP builds without stores now pass them. The readiness failure tests start the app against a built database and hand the probe to the failing store through `_ProbedThrough` (the server refuses to start against a store it can't catch up). | r6: `ProjectedGraph.objected` returns `{}` → `test_the_reading_tools_answer…` ×2; r8: projection loses the bracket edges → MCP `within` oracle ×2, CLI `--within` oracle | `test_the_graph_of_a_call_is_none_outside_a_call` |
| **M-5** | Handoff: a new requirement, with its reason, that the scheduled `project` runs the new image or is suspended before the upgrade step's `project`; "It stands when" names the CronJob. The rebuild how-to's "During a rolling update" gains step 1. | — (docs) | |
| **M-6** | Map status row: "PR #26 offen, …, Release und Abnahme stehen aus". | — | |
| **M-7** | `reference/cli.md`: `redact` "catches every projection up to the tip of the log" (no longer "the way `project` does"). | — | |
| **M-8** | `test_two_catch_ups_of_one_projection_take_turns`: the `redact` side calls `catch_up(..., rebuild=False)`. This is a test-only change, and the test stays green. | — | |
| **M-4 / F-f** | Not built. `core/graph_read.py` (module docstring) and `projections.md` now name `policy gaps` / `policy_gaps` (`core/gaps.py` `_recollection_gaps`) as the one serving path that still folds the whole log, a second way to the graph rather than a fallback, with its reason: the projection has no column for what a version rests on, so moving it takes a column and a version change, which is a design step. The map's existing point under *Zuordnungen* now says so, with ruling F-f and finding M-4. | — | |

Docs also follow:
- `mcp-interface.md` says why each 503 body names its cause.
- The handoff gives the call-failure log line in its new form.
- `vale` and `html` are clean.

### Concerns of the re-fix

- `reader_bracket_edges` keeps `graph: Graph` in its signature and refuses a non-projected graph at runtime (`TypeError`). Typing it as `ProjectedGraph` would have run through `mcp_server/read.py`'s whole `Graph`-typed chain.
- The oracle tests reach the fold by monkeypatching module names (`projected_graph`, `reader_bracket_edges`), as the CLI oracle already did. If those names move, the tests fail loudly rather than pass silently.
- The maintainer should be told: `policy gaps` is still a serving path that folds the whole log (ruling F-f).

### Gates of the re-fix (at `9b4ffef`, 2026-10-15)

```
uv run ruff check .                 All checks passed!
uv run ruff format --check .        143 files already formatted
uv run pyright                      0 errors, 0 warnings, 0 informations
uv run lint-imports                 Contracts: 9 kept, 0 broken.
uv run pytest --cov ...             2827 passed in 441.23s; TOTAL 11452 stmts, 245 missed, 98 %
make -C docs html / vale / linkcheck   build succeeded / 0 errors, 0 warnings, 0 suggestions in 51 files / build succeeded
```

The tutorial's typed run was retyped from one green plain `uv run pytest` at `e63e711` with the provisional count in place (2827 passed in 449.36s).
