# Review of fix round F2 (rulings F-c, F-d) — base a4c04f2, head 96dac0f

Reviewer: Opus, read-only, 2026-10-15. Tree restored: `git status --short` and `git diff --stat` empty after every mutation.

## Verdicts

- **Spec: ✅** — every point of the brief is met (only `project` builds; no reader fallback; exactly one retry with a new snapshot; start check and readiness; privilege no longer misnamed on the CLI; kept folds untouched; F-d residuals done; docs, handoff, map, tutorial follow). F-e is not counted.
- **Quality: Changes requested** — one Important (wrong advice in one `redact` sentence that re-opens the ping-pong F-c closes), eight Minor.

Counts: Critical 0 · Important 1 · Minor 8.

## Call sites of `catch_up` in `src/`

| Site | `rebuild` | Verdict |
|---|---|---|
| `cli.py:1494` `_cmd_project` | `True` | the only builder ✅ |
| `cli.py:1365` `_catch_up_after` (redact) | `False` | ✅ |
| `core/graph_read.py:433` `graph_snapshot` (every CLI reader via `_graph_snapshot`, every MCP call via `Service.reading`) | `False` | ✅ |
| `mcp_server/server.py:2638` `build_server` start check | `False` | ✅ |

`rebuild` is keyword-only without a default, so pyright forces every caller to name it. No other call site exists.

## Whole folds left on serving paths

- CLI readers (`entities`, `relations` without `--as-of`, `entity ID`, `triage`, `status`, `classes list|sample`, `chronicle --within`): projection only, no fallback ✅.
- MCP `whoami`, `list_entities`, `list_triage`, `previously(within=…)`, `get_event`: all go through `Service.answer` → `Service.reading` → `graph_snapshot`; `bracket`, `list_entities`, `list_triage` take the call's graph from `_FOLDED` ✅.
- Folds that remain, by design: `verify`, `project --check` (`check_graph`), `relations --as-of` (`cli.py:3562`), the write path (`cli.py:2672, 2710, 3350, 3827`, `Service.graph_of` at `server.py:1734`) ✅.
- F-e mode: `Service.reading` without projection (`server.py:942-945`), `graph_now` outside a call (`server.py:1724-1728`, see M-3).
- Not listed by F-c and still a whole fold on a serving path: `policy gaps` / MCP `policy_gaps` via `core/gaps.py:176` (see M-4). No fallback, it's the only way that tool counts, but it's a second computation of the graph.

## The one retry

`graph_snapshot` (`core/graph_read.py:432-447`): each attempt runs `catch_up(rebuild=False)` in its own transactions, then opens `with log.snapshot()` *inside* the loop, so a miss leaves that snapshot (the `with` exits) before the next catch-up, and the next check reads in a new REPEATABLE READ snapshot. A version mismatch or a missing row in the snapshot raises `ProjectionNotBuilt` and is never retried. After `REBUILD_RETRIES + 1 = 2` attempts it raises `ProjectionRebuilt`. The constant has the comment saying why one.

The tests pin "once" in both directions, and not only by reading the constant: `misses=1` reads after two snapshots, and `misses=2` fails after two snapshots although a third would read (control: the same store reads on its third snapshot). Measured below (mutations A and B): reusing the first snapshot turns the retry tests red, and so does a third attempt with the constant left at 1.

## Mutations re-run by the reviewer

Script `scratchpad/mutate.py`: one textual change, the named tests with `--no-cov`, file restored in `finally`.

| # | Mutation | Red | Green (control) |
|---|---|---|---|
| A (new) | retry stays in the snapshot it opened first (`with log.snapshot()` moved outside the loop) | graph_read retry-once, CLI `…catches_up_once_more…`, MCP `…once_more…` [legacy, auto] — 4 | graph_read `…version_change…not_caught_up_again` |
| B (m3 variant) | `range(REBUILD_RETRIES + 2)`, **constant left at 1**, so `assert REBUILD_RETRIES == 1` can't be what turns it red | graph_read two-rebuilds, CLI `…second_rebuild_in_a_row…`, CLI `chronicle --within`[2], MCP ×2 — 5 | graph_read retry-once, CLI `chronicle --within`[1] |
| C (m9) | 42501 branch never matches | CLI `test_a_role_that_may_only_read_the_projection…` | CLI `…catches_up_once_more…` |
| D (m4) | `_catch_up_after` with `rebuild=True` | CLI `test_redact_does_not_rebuild…`[no-state-row, other-version] | `test_redacting_twice_says_already` |
| E (new) | `ProjectionNotBuilt` raised after the placeholder transaction committed (lock in one txn, refusal in the next) | graph_read, CLI, MCP ×2, MCP refuse-to-start [DELETE], CLI redact [no-state-row] — 6 | all `other-version` / `UPDATE` params — 6 |
| F (new) | worker refuses only a missing row; another version rebuilds under `rebuild=False` | graph_read, CLI [other-version], MCP refuse-to-start [UPDATE] — 3 | the `no-state-row` params, readiness test |
| G (m6) | start catch-up removed from `build_server` | MCP refuse-to-start ×2, CLI `test_mcp_and_serve_refuse_to_start…` | `test_one_store_of_the_projection_without_the_other_is_refused` |

Everything the report claims for m1–m10 that I re-ran held. E is the one that matters most: it proves the "touches nothing" assertion reads the rollback of the placeholder, not only the absence of a rebuild.

## Concurrency: a reader's catch-up (`rebuild=False`) racing `previously project` (`rebuild=True`)

`truncate_projection` is a `DELETE` (`postgres.py:815`), so it's MVCC-safe: a snapshot opened before the rebuild commits keeps seeing the old rows. Rows and `up_to_id` commit together per batch, so any committed state at `up_to_id = k` is a complete projection of events 1..k.

**Same version, after an operator deleted the state row:**

1. DELETE committed, `project` not yet started. A reader's catch-up (first txn) inserts the placeholder and finds no row → `ProjectionNotBuilt` → rollback, placeholder gone. Error, nothing touched ✅. A reader *mid* catch-up whose next batch locks: no row → `ProjectionRebuilt "has no state row"` → rollback ✅.
2. `project`'s first txn (placeholder, DELETE of rows, state V/0) holds the row lock. A reader waits at the lock, then finds V with `up_to_id` 0 and carries the build on batch by batch, taking turns with `project`. Its outcome is the tip and its snapshot finds `up_to_id ≥` outcome → it reads a complete projection. Correct, and that reader pays for part of the build (documented in `projections.md`).
3. Reader's catch-up finished at T, then `project` empties (V/0) before the reader's snapshot. The snapshot sees `up_to_id < T` → leaves it, catches up again (as in 2), new snapshot → reads ✅. If `project` already passed T when the snapshot opens, the snapshot shows a complete projection at k ≥ T, which is just a lagging projection, not a half-built one ✅.
4. The snapshot lands between the operator's DELETE and `project`'s first commit → no row → `ProjectionNotBuilt` (true at that moment), no retry. An error, not a wrong answer ✅.
5. Snapshot opened before `project`'s DELETE commits → old rows, complete at T ✅.

**Other version (new release's `project` against an old reader):**

6. Before the new `project`'s first commit, the old reader reads its own version as before ✅.
7. The commit lands between two batches of the old reader → `ProjectionRebuilt "stands at version n+1"`, not retried, no rebuild back ✅.
8. The commit lands between the old reader's catch-up and its snapshot → `ProjectionNotBuilt` at the snapshot check, not retried ✅.
9. After it, every old catch-up → `ProjectionNotBuilt`, the probe → 503 ✅.

No interleaving gives a reader an empty or half-built graph, or a wrong answer in place of an error. **No Critical.**

What's left of the ping-pong is two `project`s of different releases, which only an operator or a stale scheduled job can start (M-6), and the advice in I-1, which points an operator at that.

## Error surfaces

| Cause | CLI reader | `mcp`/`serve` start | running MCP call | `/healthz` |
|---|---|---|---|---|
| no state row | exit 2, `Error: projection graph is not built, and this code declares version 1; \`previously project\` builds it` | exit 2, same sentence | client: `_FAILED`; log: `ERROR an MCP call failed` + traceback ending in the sentence; access `error` | 503 `NOT_BUILT`, WARNING `…found projection graph not built…` |
| other version | exit 2, `…stands at version N, and this code declares version 1; the release that is to serve builds it with \`previously project\`` | exit 2, same | as above | 503 `NOT_BUILT`, WARNING `…at version N…` |
| gap | exit 2, `Error: expected events X.. above id Y, read […]; the tip is Z` | exit 2, same | `_FAILED` + traceback | **200** (the probe doesn't catch up); acceptable, since every pod shares the damage |
| missing table (0006 not migrated) | no state row yet → the "not built" sentence; `project` then says `database schema incomplete — \`previously migrate\` has not run yet`. Two steps, each sentence true. With a state row: `MigrationPending` directly | the same | the same | 503 `NOT_BUILT` (the state table exists) |
| missing privilege | exit 2, `Error: the role of PREVIOUSLY_DSN lacks a privilege on database … at host:port: permission denied for table projection_state` ✅ | exit 2, same ✅ | `_FAILED` + traceback with `PrivilegeMissing` | SELECT-only role: 200, but the server can't have started like that. No SELECT: `except Exception` → ERROR + traceback, body **`Error: the database does not answer`**, which misnames the cause (M-1) |

On the CLI and at start, the privilege case no longer misnames the cause, which closes the map's open point. The one surface left that misnames it is the probe body, M-1.

## Findings

### Important

**I-1 — `redact`'s advice on a projection at a newer version sends an old release to build back.**
`src/previously/cli.py:1301-1305` (`_unfinished`, `unbuilt=True`) and `cli.py:1366-1367` (`_catch_up_after` returns `error.finding`, dropping the class's own advice).
`ProjectionNotBuilt` deliberately avoids an unqualified "run `previously project`" when the version differs, because "an old pod's operator running its `project` would rebuild back" (report, decision 1; `core/errors.py:121-123`). `redact` keeps the finding, drops that advice, and appends `run \`previously project\`, then the same command again` for every `ProjectionNotBuilt`, the version mismatch included.
Failure scenario: during or after a rolling update to a release that raised `CHRONICLE.version` from 3 to 4, an operator runs `redact` in a tools pod (or a `docker compose run`) still on the old image. They get `…projection chronicle stands at version 4, and this code declares version 3; run \`previously project\`, then the same command again`, and run that pod's `project`. It rebuilds the chronicle (and any other changed projection) back to version 3. The new release's graph readers then fail, its probe answers 503 if the graph was the one, and the next new `project` flips it again: the exchange F-c removed, now started by the code's own advice.
Fix: for `found is not None`, keep the class's qualified advice (`the release that is to serve builds it with \`previously project\`, then run the same command again`), or derive the tail from `str(error)`. Add an `other-version` case with `found > declared` to `test_redact_does_not_rebuild_and_names_project_as_what_finishes_it` (it covers only version 1 < 3), and the matching quote to `reference/cli.md` (third form, around line 410), which shows only the safe direction.

### Minor

**M-1 — The probe misnames a privilege refusal.** `mcp_server/server.py:3207-3209`: `PrivilegeMissing` (or `MigrationPending`) falls into `except Exception`, so the log gets a traceback and the body is `NOT_READY`, "the database does not answer". It's reachable only if grants are revoked after start (the start check refuses such a role), so decision 8 is acceptable. But a `except StorageError as error: logger.warning(...); return NOT_READY` costs three lines and removes the traceback noise. Strictly, the body still names the wrong cause; a neutral body ("the server cannot read its database") or a third constant would end it.

**M-2 — Expected states are logged as ERROR with a traceback, once per call.** `server.py:1035-1036`. `ProjectionNotBuilt` during a rolling update is the designed state (ruling F-c), yet every call to an old pod until readiness drains it writes a full traceback. Keep the client text (decision 2 accepted), but give `ProjectionNotBuilt`, `ProjectionRebuilt`, `ProjectionGap` and `StorageError` one WARNING line with the sentence, as the probe does. The handoff's "It stands when" (no `an MCP call failed` line naming the projection) would then read a stable line rather than a traceback.

**M-3 — A dormant fold in `graph_now`.** `server.py:1724-1728`: outside a call, `graph_now` folds the log ("which nothing in the server does"). That's a fold path no test reaches, and with F-e it should raise instead. Part of the F-e scope below.

**M-4 — `policy gaps` folds the whole log on a serving path, and the list of kept folds omits it.** `core/gaps.py:176` (CLI `policy gaps`, MCP `policy_gaps`). It's pre-existing, not a fallback, and the projection holds no evidence column, so it isn't a defect of this round. But the docstring at `core/graph_read.py:22-28` and `projections.md` ("A reader has one way to the graph") read as an exhaustive list of what folds, and this is a second computation of the graph that F-c's maintainer statement covers. Either list it as kept, with its reason, or put it on the map.

**M-5 — The handoff doesn't name the scheduled `project` in the rolling update.** `docs/superpowers/handoffs/2026-10-15-kup6s-graph-phase-2.md`, section "A rolling update runs two versions at once", with the CronJob mentioned at line 99. With readers no longer building, the only thing that can flip the version back is a `project` of the old image *starting* after the new one ran. An in-flight old job stops with `ProjectionRebuilt` at its next batch, but a CronJob not yet moved to the new image starts a fresh one that rebuilds. State it as a requirement with its reason: the scheduled `project` runs the new image (or is suspended) before the upgrade step's `project`. The same sentence belongs in `how-to/rebuild-a-projection.md` "During a rolling update".

**M-6 — The map's status row is stale.** `docs/superpowers/landkarte.md:30`, third column: "PR, Release und Handoff stehen aus", while PR #26 is open and the same file names PR #26 in *Erledigt*.

**M-7 — A stale clause in the reference.** `docs/reference/cli.md:399`: `redact` "brings every projection up to the tip of the log, the way \`project\` does". `project` builds and `redact` doesn't; the next sentence corrects it, but the clause is a claim.

**M-8 — The take-turns test plays `redact` with `rebuild=True`.** `tests/test_projection_worker.py:774-777`, `redact_catch_up` → `catch_up(..., rebuild=True)`. `redact` passes `False` now, and that interleaving is the one `REBUILD_RETRIES = 1` rests on ("the second catch-up … takes turns with that build"). The flag only acts in the first transaction, so the risk is low; pass `False` so the test says what `redact` does.

## Implementer decisions 2 and 8 (and the `redact` one)

- **Decision 2 (MCP client sees `_FAILED`, the sentence goes to the log): accept.** The client can't run `previously project`, readiness drains the pod, and stdio refuses to start, so the case where a running client sees it is a short window. Rendering it as `Refused` would also mix an operator's state into a channel that `Refused` keeps for the client's own errors. M-2 asks only for the log line's form.
- **Report decision 8 (`PrivilegeMissing` in the probe falls into the generic branch): accept**, with M-1. It's unreachable at start, and the log names the cause.
- **`redact` with an unbuilt projection (progress.md lists it among the decisions): accept for "not built" and for found < declared**: the redaction stands, `project` takes it in while building, and the second run finishes. **Reject the wording for found > declared** (I-1).

The brief's numbering and the report's differ: the report's #8 is the probe, while progress.md's summary lists `redact` last. I judged both.

## Docs and comments ("a comment is a claim")

`grep -rn -i "folds the log|fall back|falls back|fallback|never an error|folds instead|could not be caught up|rebuilt since"` over `src tests docs` (excluding frozen records and `_build`) finds no reader-fallback claim left. What it finds:

- the F-e mode docstrings (`server.py:901`, `server.py:2618`, `graph_read.py:284`, `tests/test_mcp_server.py:4267, 4376, 5035`), which go with F-e;
- `projections.md:100` and `cli.md:832`, which now say `previously project` rebuilds, which is correct;
- unrelated policy and erasure "fallback" uses.

Other checks:

- `projections.md` "How a reader reads it" argues the new behavior with its reasons (gap is damage; privilege or table is a setup fault the fold hid; the ping-pong; cost figure sourced to `graph-cost`).
- `rebuild-a-projection.md`, `cut-a-release.md` (grep checked: it prints the graph `version: int = 1` line since `v0.1.0a7`), `run-the-image.md`, the two how-to prerequisites and `erase-something.md` state the upgrade order with its reason.
- The handoff states `previously project` after `migrate` and before serving as a requirement, with why, what an operator sees, and "It stands when", in the CLAUDE.md "demands / provides" form (with M-5's gap).
- Map: the misleading-warning point and the rolling-update gap are struck into *Erledigt* naming PR #26. The two watch points (a) catch-up after a large import (threshold 1 s, write path first then `LISTEN/NOTIFY`, the maintainer's "10,000 mails unlikely/very rare" stated) and (b) build time against the upgrade window (linear, 34.6 s at 100k, shadow tables and switch) stand as observations with thresholds.
- F-d residuals: the map's line counts and the "etwa Zeilen" range are dropped, and the sentence holds without them. `module-boundaries.md:425` reads "no content beyond the period dates of a relation".

## Gates at 96dac0f (run by the reviewer)

```
uv run ruff check .                  All checks passed!
uv run ruff format --check .         143 files already formatted
uv run pyright                       0 errors, 0 warnings, 0 informations
uv run lint-imports                  Contracts: 9 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing   2824 passed in 407.82s; TOTAL 11444 stmts, 243 missed, 98 %
make -C docs html                    build succeeded (no warning)
make -C docs vale                    0 errors, 0 warnings and 0 suggestions in 51 files
make -C docs linkcheck               build succeeded, no non-ok entry in output.txt
```

pytest ran with `-p no:cacheprovider` added, to leave no cache in the worktree; nothing else differed from the gate line.

## F-e scope: removing the projection-less `build_server`

**src (about 50-70 lines):**

- `mcp_server/server.py`:
  - `Service.__init__` (920-932): `graph`/`projections` become required; drop the one-without-the-other refusal and `self.projected`'s `None`.
  - `Service.reading` (942-945): drop the fold branch.
  - `graph_now` (1724-1728): raise instead of folding outside a call.
  - `graph_of` (1734): always `read_graph`, the write path.
  - `build_server` (2603-2604, 2616-2638) and `build_app` (3144-3145): required parameters, drop `if projections is not None`.
  - `ready` (3179-3186): drop the `log.tip` branch, so the probe always reads the state row.
  - Docstrings at 899-910 and 2616-2625.
- `core/graph_read.py:278-292` `reader_bracket_edges`: the fold branch (`bracket_edges(graph, vocabulary)`) becomes unreachable from `src` (the CLI always passes a `ProjectedGraph`). Collapse it to `projected_bracket_edges` or keep it typed on `ProjectedGraph`; fix the docstring.

`run_stdio`/`run_http` and `cli.py` already pass both, so they're unchanged. No docs page mentions the mode (grep), only docstrings.

**tests (`tests/test_mcp_server.py` only; about 150-250 lines of churn):**

- 17 `build_server` and 2 `build_app` calls without the projection (lines 402, 482, 516, 567, 847, 873, 915, 980, 993, 1172, 1238, 1387, 2747, 3428, 4268, 4324, 4380-4387, 4541, 5038).
  - About 11 are mechanical: add `graph=…, projections=…`. `_world` already builds the projections.
  - The 4 readiness tests through `_get_without_token` (`build_app(storage, allowed_hosts=())` at 1238, used at 1293, 1308, 1343, 1361) build the app against an unreachable, ended or empty store. With the start check those fail at build time, so they need an `_Armed`-style store (reachable while built, failing once armed), as the round already did for gap and failure.
- Three oracle tests compare the projected server against the folding server, and need a new oracle (`read_graph`/`fold_graph` fed to the renderers in `mcp_server/read.py`, e.g. `entities(..., graph=read_graph(log, conn))`):
  - `test_a_call_reads_no_assertion_in_full_and_of_the_graph_only_what_is_new`: its control at 4266-4270 goes or is rewritten.
  - `test_the_reading_tools_answer_from_the_projection_as_from_the_fold` (4321-4324).
  - `test_previously_within_finds_by_the_fold_what_it_finds_by_the_projection` (5033-5040).
- `test_one_store_of_the_projection_without_the_other_is_refused` (4375) goes. Its role as the control of mutation m6/G passes to the readiness and refuse-to-start tests' own controls.
- The control line in `test_the_server_refuses_to_start…` (4541, "without the projection it starts whatever the table holds") goes.

Size: medium. One implementer pass, about half a day, mostly test rewiring. The only design work is the oracle for the three equality tests.
