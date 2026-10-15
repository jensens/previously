# Final review, phase 2 of the graph core (1aa8a36..22b3dec), code

**Verdict: ready after the fix wave.**

Counts: Critical 0 · Important 2 · Minor 8 · ⚠️ 5

## Method

- `W/final-src.diff` read in four passes:
  1. core: vocabulary, graph, graph_write, verify, classes, members;
  2. the projection: `core/projection/graph.py`, worker, `graph_read.py`, contract, schema, `0006_graph`, postgres;
  3. the CLI;
  4. the MCP server: `server.py` and `read.py`.
- `core/members.py` and `core/projection/graph.py` were read whole, from the tree.
- Test files read directly where a named risk needed it: `test_projection_graph.py` (concurrency, cascade), `test_cli.py` (Markus end to end), `test_mcp_server.py` (fallback stores), `test_schema.py`, `test_vocabulary.py`, `test_projection_worker.py`, `test_graph_write.py`.
- Lines removed from tests: all 67 compared (point 4 below).
- No test was run.
- Measured in the worktree at 22b3dec (commands below):
  - T201;
  - the counts in `contract/store.py`;
  - the tables in `metadata`;
  - the tools;
  - the map's open entries;
  - the census of ruling citations.

## Answers to the six points

### 1. The security boundary across tasks

- **No combination found that releases content or reveals an edge.**
  - An assignment's start is a source by a *form* rule (`_start_problem` in `claim_problem`). `parse_claim` returns `None` for a payload that breaks it, so the fold, the projection (`version_row`) and every reader skip it. That holds for a payload forged around the write path too. My first doubt, that `relation_visible` decides over the sources only and not over the start, is therefore moot.
  - A withheld mail makes every assignment of it invisible (`relation_visible` over the sources), so `seen_members` drops it and the event is absent under `within` (T5-c).
  - `within` only drops rows before `_decided`, so the policy decides each kept event as it does without `within`.
  - The bracket itself must be `seen` by the client, and is refused in the words of a missing one otherwise.
  - The cursor carries `within` among its filters, and `Service.bracket` runs on every call before the cursor is decoded.
  - `_last_member` reads `within.events`, which is already the client's view.
  - The header and the triage list fold from the log every thread the rows name, and decide visibility on what the log holds now.
  - A row that drifted can hide a thread, never add one.
- **The race between a catch-up and its snapshot.** An erasure that commits between a reader's catch-up and its snapshot is seen by the log reads, so it shows *less*, never more. An event of a bracket erased in that window can stand as an `[erased: …]` placeholder for that one call. That is no release.
- **`core/decide.py`:** untouched. `git diff --stat 1aa8a36..22b3dec -- src/previously/core/decide.py` is empty.
- **`in_circle` is never an assignment:**
  - `bracket_kinds` (members.py:82) excludes `GATE_TYPES`;
  - the built-in `in_circle` keeps `from_ = ()` (vocabulary.py:231);
  - `_built_in_problem` refuses to reshape it.
- **No new built-in kind:**
  - `BUILT_IN` is unchanged, and `concerns` stands in `vocabulary.toml`.
  - `grep '"concerns"\|"part_of"' src/previously --include=*.py` finds only help texts and tool descriptions.
  - `EVENT_START` and `ANY_ENTITY` are vocabulary words, not kinds.

### 2. Projection correctness end to end

- **The incremental step matches the fold for every listed history.** Marks:
  - a version, by its subject;
  - a rejection, by its target's subject;
  - an erased row, as subject and by its own subject;
  - a class event, through `_same_name`;
  - an erased action, which refolds everything under any class;
  - the cascade's own whole-event redactions, which cover a unit erasure.
- **A version written and erased in one batch.** It is never inserted, and its thread needs no refold. An approval or objection that names it reads the erased row through `_named`.
- **Vocabulary changes:** they correctly mark nothing.
- **Migration down and up:** covered by `test_migration_0006`.
- **Every reader that reads the projection catches up first and falls back:**
  - the CLI: `entities`, `relations` without `--as-of`, `entity ID`, `triage`, `status`, `classes list/sample`, `chronicle --within`;
  - the MCP server: every call, through `Service.answer`.
- **No reader reads the projection without a catch-up.** `graph_now` outside a call has no production caller.
- **Readers that still fold per call:**
  - by design: the write path, `--as-of`, `verify`, `--check`, the approve/reject/answer/relate commands, and the writing MCP tools (`graph_of`);
  - **`policy gaps`**, CLI and MCP `policy_gaps`, folds the whole log on every call through `core/gaps.py:176` (M-6).
- **One exception to "equal to the fold":** see M-5. The reader reads the classes at its snapshot and the rows as of the catch-up, which is a one-call staleness.

### 3. Erasure

- **Every write path puts the start among the sources:**
  - CLI `relate` (`sources_with_start`, cli.py `_relation_claim`);
  - MCP `write_relation` (`_relation_claim` in server.py);
  - approvals and answers, which copy the proposal's sources;
  - a batch, since each claim is checked;
  - verify, through `claim_problem` and `rests_on`.
- **The cascade follows the sources,** and that includes the start. A `units: null` assignment falls with any unit erased after it (T2-b).
- **The projection and the readers follow the cascade:**
  - `test_an_erased_mail_takes_its_assignment_by_the_cascade` checks the projection;
  - `test_chronicle_within_shows_the_units_…` checks the CLI end to end: unit 3 is erased, XZ's chronicle is empty, the party keeps unit 2, and `verify == []`;
  - `redact` prints `cascaded: assertion N`, so the operator learns which assignments fell.
- **No MCP test erases a mail and then reads `within`.** It reads the same rows and folds from the log, so I'd leave it unwritten.

### 4. Unit 5, phase 1 and the phase 2 tasks don't break each other

- All 67 removed test lines were compared.
- Each is either a count moved by `concerns` or by the projection tables (9→10 kinds, 12→13 event ids, a third `project` line), or a phase-1 refusal replaced by its phase-2 counterpart.
- The replaced phase-1 tests:
  - `test_an_event_as_the_start_is_sound_form_and_refused_by_the_vocabulary`;
  - the `from_event` line in `test_a_relation_is_visible_…`, now `test_an_assignment_is_decided_over_its_mail_…`;
  - `test_a_call_folds_the_graph_once…`, which pre-flight declared as intended.
- `test_the_projection_tables_exist` widened from three to five tables.
- No assertion was weakened.

### 5. Counted claims, measured

| Claim | Where | Measured | Holds |
|---|---|---|---|
| T201 "ninety-eight" | pyproject.toml:172 | `ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py` → 98 | yes |
| store.py: 15 methods, 16 modules | contract/store.py:6-30 | methods command → 15; `grep -rl LogStore src/previously/core --include='*.py' \| wc -l` → 16 | yes |
| store.py: the server calls nine | contract/store.py | `grep -ohE 'log\.[a-z_]*\(' src/previously/mcp_server/*.py \| sort -u` → 9 | yes |
| store.py: the protocol declares sixteen | contract/store.py | 16 `def` lines in `LogStore` | yes |
| database-schema.md "ten tables", "Five more" | database-schema.md:5, 138 | `len(metadata.tables)` → 10, five of them projections | yes |
| "fifteen tools" | mcp-tools.md:5, connect-…md:137 | `grep -c '@server.tool('` → 15 | yes |
| projections.md "two short transactions"; "an MCP call always finds one thing new … ends before it reads any approval class" | projections.md | `GraphProjection.write` returns before `class_states` when nothing is touched and no class event is in the batch; the access entry is written in `finally` after the answer | yes |
| projections.md and graph.md test names | projections.md:329, 357 | both tests exist under those names | yes (but see M-1: renaming the concurrency test moves the page) |
| graph.md figures (½ s at 10,000; 1.7 s; >7 s at 100,000) | graph.md | phase 1 measurements, labeled as such; not re-measured (the performance agent's) | not checked |
| map open entries | landkarte.md | awk command of CLAUDE.md → 242 | yes, but includes a struck point (M-8) |

### 6. Quality at branch level

These are listed under Minor below:

- the duplicated fallback;
- the duplicated bracket check;
- dead code;
- the flaky test;
- the growth of `cli.py` (4,329→4,483 lines) and of `server.py` (3,062→3,245 lines).

`ProjectedGraph` overriding the query methods of `Graph` is a clean seam.

- Every reader method walks only the rows.
- `ThreadsFromLog.__iter__` would fold everything, and nothing in a reader iterates it. I checked every `graph.threads.values()/items()` in `src`: the remaining ones are on full folds or in write paths. `graph_version` and `_graph_version_of` predate the branch.

## Important

### I-1 — A catch-up that fails with anything but `ProjectionRebuilt` or a `StorageError` fails every reader, and every MCP tool with it

- **Where:**
  - `src/previously/cli.py:3492` (`_caught_up`);
  - `src/previously/mcp_server/server.py:941` (`Service.caught_up`).
- **What is wrong:**
  - Both catch only `(ProjectionRebuilt, StorageError)`.
  - `ProjectionGap` (core/errors.py:62) is a `PreviouslyError`, raised by `catch_up` itself (worker.py:161). It propagates.
  - In the CLI, the command fails.
  - Over MCP, it reaches the generic `except Exception` in `Service.answer` (server.py:1048), and the call answers `_FAILED`. That happens on every call, `whoami` and `get_event` included, since every call catches up first.
- **Why it matters:**
  - Before this branch, no MCP call ran a catch-up. A gap broke `project` and nothing the clients use.
  - Now one impossible-but-guarded state takes the whole MCP server and every graph reader of the CLI dark.
  - This is the failure the T4-b fallback exists to absorb ("a reader must never answer wrong or fail because the projection is being rebuilt"). The fold reads the log whole and needs no gap-free projection.
  - The ledger has it as "minor (→ final wave)". I rank it higher: it widens the blast radius of a state the code itself guards against, and the fix is one name per site.
- **Proposed fix:**
  - Catch `PreviouslyError` beside `StorageError` at both sites. It covers `ProjectionGap` and `ProjectionRebuilt`, and it keeps genuine programming errors (`KeyError`, `TypeError`) visible.
  - Keep the warning line as it is.
  - Add a third store to the parametrizations of `test_a_call_folds_the_log_when_its_projection_does_not_stand_and_says_so_only_in_the_log` (MCP) and of its CLI twin: one whose `read` skips an id above `up_to_id`, so that `catch_up` raises `ProjectionGap`.
  - Measure each red with the catch reverted to the old tuple.
  - The existing `rebuilt`/`failed` cases are the green control.
  - Name it in the reader section of projections.md and graph.md where the two causes are listed.

### I-2 — Four new ruling citations in `tests/test_members.py` resolve to the wrong decisions

- **Where:** `tests/test_members.py:124` (`Ruling T2-e:`), `:196` (`Ruling T2-c:`), `:318` (`Ruling T2-d:`), `:434` (`(ruling T2-c)`). All came in with a6d358a.
- **What is wrong:**
  - These are rulings of the 2026-10-15 phase 2 plan, cited bare.
  - The ledger that ships, `docs/superpowers/sdd/2026-10-14-zuordnungen-phase-1/progress.md`, has its own `Ruling T2-c` (line 51, a transitive version answers a question) and `Ruling T2-d` (line 52).
  - `src/previously/core/graph.py:862` already cites "ruling T2-c of the 2026-10-14 assignments plan".
- **Why it matters:**
  - CLAUDE.md: "Labels are assigned per plan, so a citation names the plan", and "a pointer that resolves to the wrong decision is worse than a label with no pointer, because the reader stops with an answer".
  - A reader of `test_members.py` who looks up T2-c lands on the phase-1 decision about questions, not on "a proposal must not narrow a direct assignment".
- **Proposed fix:**
  - Write "ruling T2-c of the 2026-10-15 assignments plan, phase 2", and likewise for T2-d and T2-e, at the four sites.
  - Write one `ruling` per label, so the census catches each.
  - Check that the reason stands beside each label: it does at 196 and 318; 124 and 434 should be read once more.
  - Census after the fix: `grep -rnioE 'ruling (P|T[0-9]+)-[a-z0-9]+' src tests pyproject.toml .importlinter | sort -u`. Every 2026-10-15 label should carry its date.

## Minor

### M-1 — The concurrency test can still flake (deferred from Task 3), fix in the wave

- **Where:** `tests/test_projection_graph.py:669-735`, `_Holding` at :648-665.
- **What is wrong:**
  - `_Holding` holds only the *first* batch, until the second catch-up waits at a lock.
  - That wait is in the second's version-check transaction, the first `with store.begin()` of `catch_up`, which commits at once.
  - Both then race for the lock of batch 2. If the first wins batch 2 and the second's lock request comes only after the first has started batch 3, the first takes all six events. Then `outcomes["second"].events >= 2` fails.
  - The likely trigger is GIL scheduling under load. PostgreSQL's tuple-lock queue orders only those already waiting.
- **Proposed fix:**
  - Hold *every* batch, not only the first: in `set_projection_state`, whenever `state.up_to_id > 0`, wait until the other catch-up waits at a lock or has returned. The `second_done` condition already exists.
  - Each commit of the first then hands the lock to a queued second, and alternation follows by construction: the second takes at least the batch after the first's last hold.
  - Keep the assertions unchanged, and keep both measured-red variants of the docstring: the lock read without locking, and the `FOR UPDATE` taken out.
  - Re-measure them, since the timing changes.
  - The test name stays, so projections.md:329 stays right. If it is renamed, the page follows.

### M-2 — `_claim_fields`' relation branch is dead (deferred from Task 2), fix in the wave

- **Where:** `src/previously/cli.py:3604-3613`.
- **What is wrong:**
  - The only caller is `_entity_history_lines` (cli.py:3729), for entity threads.
  - A fold puts a relation version in no entity thread, so the whole `else:` is unreachable, not only the event-start line.
  - It predates phase 2. Task 2's M-1 aligned code nothing runs.
- **Proposed fix:** narrow `_claim_fields` to `EntityBody` (take an `EntityBody` claim, or `cast` with a one-line reason), and delete the branch. No test changes.

### M-3 — The fallback is written twice, and so is the bracket check

- **Where:**
  - cli.py:3479-3511 (`_caught_up`, `_reader_graph`, `_graph_warning`) against server.py:931-959 (`caught_up`, `read_graph`);
  - cli.py:1579-1590 (`_bracket_selection`) against server.py:1175-1193 (`bracket`): the same `1 <= N <= MAX_SAFE_INT and N in EntityTypes(graph)`.
- **Why it matters:** I-1 has to be fixed twice, which is how the copies drift.
- **Proposed fix, not in this wave:**
  - The exception tuple can't live in `core`, since `StorageError` is in `storage`.
  - A small `projection_graph_or_none(log, store, conn, outcome) -> Graph | None` in `core/graph_read.py` could carry the "stands, else `None`" decision, and leave the fold and the warning to each caller.
  - Put it on the map. For this wave, fix I-1 at both sites in one commit.

### M-4 — `cli.py` and `server.py` keep growing

- **Where:** `cli.py` grew from 4,329 to 4,483 lines and `server.py` from 3,062 to 3,245.
- **What is wrong:** nothing in phase 2 is misplaced, but `cli.py` is the module every task touches.
- **Proposed fix:** a map entry to split `cli.py` by command family (graph readers, writers, operations) before phase 3 adds `in_circle`. Not this wave.

### M-5 — The reader reads its classes at the snapshot and its rows as of the catch-up

- **Where:** `src/previously/core/graph_read.py:221` (`classes = read_classes(log, conn).states`).
- **What is wrong:**
  - The rows (`level`, `pending`) were folded under the classes at `up_to_id`.
  - An approval-class event that commits between the catch-up and the snapshot, such as a `demote`, can turn a thread open that `graph_waiting` doesn't select.
  - That thread is missing from `list_triage`, `status` and the header for that one call. The next call catches up and finds it.
  - Not a release: a class doesn't decide visibility.
- **Proposed fix:**
  - Leave it on the map; don't fix it in this wave.
  - Reading the classes as of the projection's `up_to_id` (`class_states(log, conn, up_to)`) would make the reader exact. But `classes list` takes `by_name` from `read_classes` over the whole log, so the change needs care in `hit_rates`.

### M-6 — `policy gaps` still folds the whole log per call, on the CLI and over MCP

- **Where:** `src/previously/core/gaps.py:176` (`read_graph`), reached from `cli.py:1888` and `server.py:1315` (`policy_gaps`).
- **What is wrong:**
  - Decision 10 doesn't name it, so this is no spec violation.
  - It is the one graph reader the projection didn't reach, and over MCP it costs what phase 1 cost, whenever a fallback for `recollection` is in force.
- **Proposed fix:** a map entry. It is `graph.winners(...)` over recollection threads, and an index or a row flag would be needed. Not this wave.

### M-7 — No retracted entity as a `*` target is tested (deferred from Task 1)

- **Triage:** close; no map entry.
- **Why:**
  - `_ends_conformance` checks presence (`end not in entity_types`) before the `*` shortcut.
  - Callers pass `EntityTypes`, which raises `KeyError` for a retracted entity.
  - The unknown-id test already goes red if the presence check is removed.
  - A retracted entity takes the same branch; a test of it would read the same line twice.

### M-8 — The map counts a struck point as open (deferred from Task 6), fix in the wave, docs

- **Where:** `docs/superpowers/landkarte.md:577`. The struck "Ein Ereignis als Beginn einer Beziehung…" stands above `## Erledigt`, and the CLAUDE.md awk command counts it among the 242.
- **Proposed fix:** move it under `## Erledigt` with its commit (`fbdd05e`/`a6d358a`), and retype the count where the map states one. This is the docs reviewer's domain; listed here so the wave has it once.

## Triage of every deferred minor in `progress.md`

| Ledger line | Triage |
|---|---|
| Task 1: no test for a retracted entity as a `*` target | **Close** (M-7): the unknown-id test guards the same branch. |
| Task 2: dead event-start branch in `_claim_fields` | **Fix in the wave** (M-2): the whole relation branch, not just the event line. |
| Task 3: concurrency test relies on lock alternation | **Fix in the wave** (M-1): hold every batch. |
| Task 4: `ProjectionGap` not caught by the reader fallback | **Fix in the wave, raised to Important** (I-1): catch `PreviouslyError`. |
| Task 4: CLI fallback tests cover entities/triage/status, not relations/show/classes | **Close**: one helper (`_reader_graph`), and `chronicle --within` has its own fallback test (test_cli.py:8028). I-1's new case goes into the existing parametrization. |
| Task 4: the warning embeds `str(error)` | **Close**: `OperationFailed` and `ServerUnreachable` name where (`_where`, no password) and the server's primary message (postgres.py:276-295); `InvalidDsn` can't come from a catch-up that has connected. It goes to stderr or the server log only. |
| Task 5: `seen_members` cost grows with hidden deciding edges | **Map** (same class as ⚠️ 4 of Task 5, timing only); for the performance agent's report. |
| Task 5: `_last_member` reads the payloads of all member events per call | **Map**; for the performance agent. A projection of `(event_id, occurred_at)` (`p_chronicle` has both) would replace it. |
| Task 6: the struck event-start point sits among the open ones | **Fix in the wave** (M-8, docs). |

## ⚠️ For the controller and the maintainer

1. **The ledger has to ship before the merge.**
   - `.superpowers/` is git-ignored (`.gitignore:24`).
   - Every "ruling T…-x of the 2026-10-15 assignments plan" in `src` and `tests` resolves only once `W` moves to `docs/superpowers/sdd/2026-10-15-zuordnungen-phase-2/`, which is plan step 191, "Ausführungsprotokoll nach …".
   - The citations are: T2-a, T2-b, T2-c, T2-f, T4-b and T5-c, plus I-2's four.
   - After the move, check each cited label with `grep -c 'Ruling <label>'` against the moved `progress.md`.
2. **Every MCP call, and every graph reader of the CLI, now writes and takes the `projection_state` row lock `FOR UPDATE`.**
   - The database role of `mcp` and `serve` needs write access to `p_graph_*` and `projection_state`. Without it, every call falls back to the fold with a warning: correct and slow.
   - No `lock_timeout` stands anywhere in `src`. The first call after a large ingest, or after an upgrade that bumps `GRAPH.version`, does the whole catch-up inside the call, and every concurrent call waits at the lock until it ends.
   - The handoff should say: run `previously project` after an upgrade, and after a bulk ingest.
   - Measuring the wait is the performance agent's.
3. **Rolling update (carried from Task 4):** two versions with different `GRAPH.version` truncate each other's projection on every call, and every call then folds. This is correct, and costs a truncate plus a fold per call. The handoff says so (Task 6 carry); confirm it reached the page and the handoff.
4. **T2-b in practice:**
   - The Markus test shows it. Erasing unit 3 of mail 1 takes the operator's whole-mail assignment to XZ, so units 1 and 2 leave XZ's chronicle although they weren't erased.
   - `redact` prints `cascaded: assertion N`, so the operator sees it, but nothing says "re-assign the rest".
   - Ruled as erring on the safe side. The maintainer may want a how-to sentence.
5. **The equivalence argument doesn't cover two out-of-band cases,** a forged cross-thread `approves`/`contests` and a payload nulled without a redaction. The module docstring names both, and `project --check` reports both. Nothing runs `--check` on a schedule; whether the kup6s CronJob should is a decision for the handoff.

## Final fix wave

Base `22b3dec`, ruling F-a. Seven commits, `0f91e78..9ad6eeb`, files staged by name, trailer `Assisted-By: Claude Opus 5.5 <noreply@anthropic.com>`. Nothing pushed.

### I-1, a catch-up's refusal fails no reader (`0f91e78`)

- **Change:**
  - `cli.py` `_caught_up` and `server.py` `Service.caught_up` now catch `(PreviouslyError, StorageError)`.
  - The `ProjectionRebuilt` import is gone from both; the docstrings name the gap, and say that a programming error still fails visibly.
  - `projections.md` (reader section) names the gap among the causes. `graph.md` lists no causes, so nothing to name there.
- **Tests:**
  - MCP: `_GapAboveTheProjection` (a batch read, `limit > 1`, leaves out the first id asked for; a one-row read finds it, so the fold and `get_event` are unaffected).
    - It is a third case of `test_a_call_folds_the_log_when_its_projection_does_not_stand_and_says_so_only_in_the_log`, with `get_event` added to the calls beside `whoami`.
    - A second event (Bert, through `core`) is written past the projection, since a gap needs room between two new events.
    - Each case now asserts its cause in the warning.
  - CLI: `test_a_listing_folds_the_log_when_its_catch_up_meets_a_gap_in_the_log`.
    - The graph's state row is deleted (a build, as after an upgrade), then `entities`, `triage` and `status` run through the real `catch_up` over the gapped log.
    - It checks the fold's output and the one warning line, `... (expected events 1.. ...); this command folds the log instead`.
- **Mutations:**
  - The old tuple in `server.py`: `gap-auto` and `gap-legacy` red (`the call failed inside the server`), the four rebuilt/failed cases green.
  - With the calls cut to `get_event` alone, and to `whoami` alone, each red under the mutation.
  - The old tuple in `cli.py`: the gap test red (`main(['entities']) == 2`, `Error: expected events 1.. above id 0, read [2, 3, 4]…`), the four other fallback tests green.
- **Observation (not fixed, on the map):** a role without write access to the projection tables also falls back, but its warning reads `database schema incomplete — previously migrate has not run yet`. `_transaction` maps every `ProgrammingError` after connecting to `MigrationPending`, and psycopg's `InsufficientPrivilege` is a `ProgrammingError` (MRO checked). The handoff says so.

### I-2, ruling citations name their plan (`894eeec`)

- The four sites in `tests/test_members.py` (T2-e, T2-c, T2-d, T2-c) now read "Ruling/ruling T2-x of the 2026-10-15 assignments plan, phase 2", one `ruling` per label.
- A reason stands beside each: 124 says a gate kind is no assignment; 434 says only an edge that stands for someone replaces.
- Census after, `grep -rnioE 'ruling (P|T[0-9]+)-[a-z0-9]+' src tests pyproject.toml .importlinter | sort -u`: every label added since `1aa8a36` names its plan. T2-a, T2-b, T2-c, T2-f, T4-b and T5-c name "the 2026-10-15 assignments plan", some with ", phase 2" and some without; the date alone disambiguates, so those were left.
- Each of T2-c/d/e occurs as `Ruling T2-x` in `W/progress.md`, once each (`grep -c` → 3).

### M-1, the concurrency test is deterministic (`62154b2`)

- `_Holding` holds every batch (`up_to_id > 0`) until the second waits at a lock or has returned; `holding` is set at the first. The docstring says why the turns now follow by construction. Name and assertions unchanged.
- 20 runs in a row: **20 passed** (5.53–5.71 s each).
- Mutations, three runs each, all red with `IntegrityError ... already exists`:
  - `FOR UPDATE` taken out of `lock_projection_state`;
  - the row read without locking (no placeholder insert, no `FOR UPDATE`).

### M-2, the dead branch is gone (`18efaff`)

- `_claim_fields` became `_entity_fields(body: EntityBody)`.
- The caller casts `claim.body` with the reason: `_show_entity` passes only a thread of kind entity (`thread.kind != ENTITY` refused), and the fold drops a version whose kind differs from its thread's (`draft.kind != claim.kind`, graph.py).
- `_period_text`, whose only caller was the branch, is deleted.
- Behaviour unchanged: 21 entity/history CLI tests green, and the full suite green.
- Coverage: the gate run lists 29 missing of 2,062 statements in `cli.py`, none in `_entity_fields`. The deleted lines were unreachable, so coverage can only have risen. No baseline run at `22b3dec` was made to give the exact figure.

### M-8 and the six docs minors (`2567226`, `416385b`)

- **The map:**
  - The struck event-start point moved to *Erledigt*, in the map's form, citing **PR #26**.
  - That number is predicted: the highest issue or PR on GitHub is #25 (`gh api`, 2026-10-15). Check it when the PR opens.
- **projections.md:348:** it now says "the walk ... folds no thread", followed by one sentence that `chronicle --within` folds the bracket's own thread to check it stands and reads the approval classes.
- **"Holds no content":** graph.md:71, projections.md:10, README.md:121 and the handoff now name the period dates of a relation.
- **The handoff:**
  - `caught up:` where events arrived, `up to date, up_to_id <id>` where none did.
  - A container of `v0.1.0a7` rebuilds nothing; stop only one of an intermediate build.
- **vocabulary.md:** one sentence per line in the `event` and `*` bullets.

### The handoff (`416385b`)

- A new section, "Every reader catches the projection up first":
  - **Requirement:** `SELECT`, `INSERT`, `UPDATE` and `DELETE` on `projection_state`, `p_graph_version` and `p_graph_thread` for the role of every reader, with the reason and what happens without it. kup6s uses the owner role for every pod (feedback of 2026-10-12, `handoffs/2026-10-12-kup6s-feedback-settings-and-assertions.md:37`), so nothing changes there.
  - **Run `previously project`** after an upgrade or a bulk ingest: the row lock is taken batch by batch with no lock timeout, so a reader that arrives waits and shares the batches until the tip. Figures: first build 3.5 s / 35 s, a catch-up after one write 0.04 s. The existing five-minute `project` CronJob is named.
  - **Recommended:** `project --check` on a schedule like `verify`, with an alarm on exit 1. Exit 2 means it could not check, as for every command (cli.py `return 1 if found else 0`). The two known out-of-band drifts are named, and the repair points at `rebuild-a-projection.md`.
- "What this release leaves": the write figure (0.54 s / 6.9 s) and `verify` (3.6 s / 130 s) replace the 2026-10-14 ones, and one new bullet covers the slow listings and `within` at scale.
- Only requirements; no cdk8s. The compose paragraph gets the `--check` cron line.

### The map (`2567226`, `416385b`)

- **Count:** 242 before, 244 after `2567226`, 245 after `416385b`. Each figure is from the CLAUDE.md awk command.
- **Moved to *Erledigt*** (−4), each citing PR #26:
  - the struck event-start point;
  - `ProjectionGap` (I-1);
  - "Jeder MCP-Aufruf faltet den ganzen Graphen für die Zahl im Kopf", measured gone (`whoami` 0.019 s at 100,000);
  - "Zurückgestellte Kleinigkeiten aus Phase 2" with its four items: M-7 and the fallback tests closed by triage, M-1 and M-2 fixed.
- **New** (+7):
  - full listings (`relations --at`, `entities`) that the projection helps only by half;
  - M-3;
  - M-5;
  - M-6;
  - the re-assignment hint after a unit erasure (⚠️ 4);
  - the lock without a timeout (⚠️ 2);
  - the misleading `MigrationPending` for a missing privilege (under *Storage-Schnittstelle*).
- **Rewritten in place** (±0): "Die Kosten von `seen_members` und `_last_member` sind ungemessen" became the measured point on MCP `within` over a large bracket.
- **Figures added:** `list_entities`, the write path, `verify`, the per-batch class read, and the `cli.py` point, which carries M-4's growth.
- **Status:** the phase-2 row and paragraph and "Was als Nächstes kommt" are updated.
- **Legend:** P-Z2 is added.

### The measured figures (`416385b`)

- **graph.md, "What it costs":**
  - The phase-2 table: 15 rows at 10,000 and 100,000 relations, measured 2026-10-15 on an i7-11370H (8 threads), fixed detached copy of `22b3dec`, medians of three, `verify` clean. It is followed by what carries and what doesn't.
  - Phase 1's per-call table and its header rows (53 / 153 ms) are gone. Phase 1 stays as one history paragraph that explains the change (7.69 → 0.019 s, 23.7 → 4.97 s, write 7.34 → 6.94 s).
  - The `part_of` `verify` tables stay, since they aren't superseded.
- **projections.md:**
  - `whoami` at 100,000 in the graph section;
  - the no-news catch-up figures in the reader section;
  - a paragraph on a long catch-up and the lock;
  - the `within` cost in the bracket section.

### Gates, at `9ad6eeb`

```
uv run ruff check .                              All checks passed!
uv run ruff format --check .                     143 files already formatted
uv run pyright                                   0 errors, 0 warnings, 0 informations
uv run lint-imports                              Contracts: 9 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing    2807 passed in 348.54s; total coverage 97.83%
make -C docs html && make -C docs vale && make -C docs linkcheck
                                                 build succeeded; 0 errors, 0 warnings and 0 suggestions in 51 files; build succeeded, 0 broken
uv run pip-audit --skip-editable                 No known vulnerabilities found
```

- The tutorial block was retyped from one green `uv run pytest`: seed 270588370, `2807 passed in 345.38s`.
- Before that run, only line 292's count was set to 2807, so that `test_docs_typed_output` could pass inside the run being typed. Nothing in the tree changed after the run except the retyped block, and the gates above ran on the committed tree.
