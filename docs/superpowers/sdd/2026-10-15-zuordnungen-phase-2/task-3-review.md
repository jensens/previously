# Task 3 review — the projection `graph` (a6d358a..207d647)

Spec: ❌ (narrowly: two Global Constraints are not met, I-2 and I-3; decision 5, ruling T3-a and every dispatch detail are met)
Quality: Changes requested

Counts: 0 Critical, 3 Important, 5 Minor, 7 ⚠️

Ran no test. Measured with grep against the worktree at 207d647 (HEAD verified).

## What matches

- Tables and columns as decision 5 says, indexes `(kind, type)`, `to_entity`, `start_event`; `schema.py` and `0006_graph` agree on columns, types, nullability, CHECK names, index names and the two FKs (`p_graph_version.id`, `p_graph_thread.subject`).
- Dirty rules: version → subject; rejection → subject of its target (from the batch or `graph_versions`); `redaction` of scope `event` → the target's subject and the target as a subject; `approval_class` → every class event of the same name (`_same_name`); vocabulary → nothing. Refold from the log through `events_by_id`, classes through a `ClassFold` over `log.actions` up to the batch's end, which is `read_classes` at the end of every catch-up.
- `_PROJECTION_TABLES` holds tuples; `truncate_projection("graph")` empties both. `PROJECTIONS = (CHRONICLE, SOURCE_STATS, GRAPH)`.
- Hypothesis against real PostgreSQL with catch-ups at random points in batch sizes 1/2/5/500, and a rebuild compared at the end; two concurrent catch-ups; column-name test.
- `core` imports no SQL; `.importlinter` unchanged; no suppression, no `# type: ignore`, no private name imported by a test.
- The additions:
  - (a) erasing an action refolds everything under a class: correct and needed, because an erased class event loses its name with its payload.
  - (b) the refold reads the erased ids named by `approves`/`contests`: correct and needed once (c) prunes them.
  - (c) pruning `p_graph_version`: correct, because otherwise incremental ≠ rebuild.
  - `candidates bigint[]`: right, since entity ids are bigint.
  - Deleting the state row on the downgrade: right, but untested (I-3).
- The two documented limits are both forged-only:
  - `graph_write.py:414-429` refuses an `approves` that is not a standing proposal of the same thread, and the write path sets `contests` itself to the thread's winner.
  - A payload nulled without a redaction is something `verify` reports.

## Important

**I-1 `src/previously/core/projection/worker.py:52-56`. The claim that the log is read-only is false, and there is a cleaner seam.**
"the log stays read-only to a projection, since `LogStore` holds no method that changes it". But `LogStore` has `insert_event` (`contract/store.py:104`).
Every projection now gets, inside the catch-up transaction, a handle that can append to the log. Ruling T3-a asked the reviewer to say whether there is a cleaner seam, and there is one.
Give `Projection.write` a narrow read protocol for the log, for example one with `events_by_id` and `actions`, which is what the graph calls. `LogStore` and `PostgresStorage` satisfy it structurally, so `catch_up` passes its `log` unchanged.
That puts no log reads into `ProjectionStore`, needs no contravariance trick and widens no contract, and it makes the sentence true.
At the least, the sentence has to go. The docstring count in `contract/store.py` then needs re-measuring, because `graph.py` would no longer name `LogStore`.

**I-2 `src/previously/contract/store.py:16`. "sixteen on 2026-10-15" is wrong: it is eighteen.**
`grep -rl LogStore src/previously/core --include='*.py' | wc -l` gives 18 at 207d647 and 15 at a6d358a.
`core/projection/chronicle.py` and `core/projection/source_stats.py` name `LogStore` too now, because their `write` signature imports it. The report says "measured: 15 before + `core/projection/graph.py`".
The method count, 15, is right (re-measured with the docstring's command). This count is one the Global Constraints name explicitly ("die Zählungen in `contract/store.py` — nachmessen").

**I-3 `src/previously/migrations/versions/0006_graph.py:12-17, :83` and `docs/reference/database-schema.md:258-259`. The downgrade's assurance has no test.**
The docstring promises that the state row goes, "else the next upgrade would start from there with empty tables".
Only `test_migration_0003.py:42-43` passes through this downgrade, on an empty database, and it asserts nothing about `projection_state`. Deleting line 83 leaves every test green, which I read from the tests and did not run.
This is the silent drift that Review Focus 2 is about, so it needs a test measured to fail, in the pattern of `tests/test_migration_0005.py`:
1. upgrade to head;
2. write a version and catch up;
3. downgrade to `0005_watermark` and assert no `graph` row;
4. upgrade again, catch up, and compare the rows with the fold.
Measure it red with the `DELETE` removed.

## Minor

**M-1 `docs/reference/database-schema.md:138`.** "Three more tables hold projections derived from the tables above." This is now five. The intro on line 7 was updated, this sentence was not.

**M-2 `tests/test_projection_graph.py:927-943` and `:820-841`. The property cannot erase a rejection.**
Rejection ids never enter `history.versions`, because `_reject` returns them to nobody. A mail erasure takes a rejection only together with its proposal, since a rejection carries the proposal's sources.
So the real path `redact event <rejection>` is never generated, and there is no dedicated test for it either. In that path the proposal becomes the winner again and the rejection row is pruned.
The code handles it, by reading: `graph_versions` finds the rejection row, its subject is touched, and `_stale` takes the row. But a mutation that left rejection rows out of `graph_versions`, or that skipped `known[target].subject` for kind `rejection`, would stay green.
Append the rejection ids to `history.versions`, or to a list of their own that `_EraseVersion` picks from. `docs/explanation/projections.md:313`, "Each way a thread changes also has a test of its own", overclaims until this is fixed.

**M-3 `src/previously/core/projection/graph.py:199-206`. The `contests` half of addition (b) has no test.**
`test_an_approval_of_a_proposal_erased_unread…` covers `approves` only. The `contests` case is a real path:
1. the operator writes a second direct version D;
2. a model writes O, and the write path sets `contests=D`;
3. `redact event D` erases D, and the refold prunes its row;
4. a later version on the thread refolds it.

Without `contests` in `_named`, O is dropped (`_contestable`), and `objections` and `pending` differ from the fold. A mutation of `_named` to `("approves",)` is caught by no dedicated test, and by the property only by luck (compare M6 in the report). Add one dedicated test and measure it red.

**M-4 `tests/test_projection_graph.py:600-652`. The concurrency test runs one batch, and it does not check what each reader sees when it returns.**
After the first `_project`, there are three new events at `batch_size=3`. The first catch-up has exactly one batch, so the second always finds `up to date`.
The interleaving "the second takes the next batch and the first continues after it" never happens, and the docstring's "then starts where the first committed" is true only trivially.
"Each sees a whole state" (Review Focus 5, brief Step 1) is also asserted only after both threads have joined.
Write more events than one batch holds, and assert `_rows == _folded` inside `run_second` right after its `catch_up` returns.

**M-5 `docs/explanation/projections.md:292`, `src/previously/storage/schema.py:274-276` and `contract/rows.py`.** "only ids, counts and words of the vocabulary". `period_start`/`period_end` are dates the claim asserts, not ids, counts or words.
Decision 5 lists them, and they leave with their version on erasure through the refold, so the principle holds. The sentence does not.
The content test (`test_the_tables_hold_ids…`) pins the column names and the `Text` columns only. Name the period in the sentence.

## ⚠️

1. **Equivalence holes (named risk 1).**
   - **No hole for the listed cases:**
     - A class revoked, then set again: `_same_name` marks every event of the name, and `_Class(revoked=False)` after a revoke is generated.
     - The cascade in the same batch as the claim's write: the batch reads the claim already nulled, so it gets no row and no thread sees it. The target is touched as a subject, and the rebuild does the same.
     - A batch boundary between a version and its rejection: the target is found through `graph_versions`, and batch sizes 1, 2 and 5 generate it.
     - Vocabulary: the fold does not read it, and `level_of` reads only the constant `GATE_TYPES`, so no refold is needed.
     - Mixed snapshots under READ COMMITTED: a redaction can commit between the batch read and `events_by_id`. The refold then sees the erasure early and prunes the row. The later redaction batch finds no row and touches only the target as a subject, but the thread is already right.
   - **The strategy cannot generate these:** the erasure of a rejection (M-2), the pruned `contests` case (M-3), and the implementer's pruned `approves` case (M6).
     - All three are real write paths. `docs/reference/cli.md:385` even documents the approval that outlives its proposal.
     - Two of the three lack a dedicated test.
2. **Cost (named risk 3).**
   - `_classes` reads every `approval_class` action per batch with graph marks, and `log.actions` visits every action, every `mcp_access` among them.
   - A rebuild therefore costs about batches × actions. The first catch-up after the upgrade is such a full build, and `project`, `redact` or Task 4's first reader pays for it. That belongs in the handoff (Task 6).
   - Acceptable for the pilot. It goes on the map next to the write path's full fold.
   - An index on `p_graph_version(under)` is not needed now: `class_subjects` runs only on class events and erasures of actions, over a narrow table.
   - If one is wanted, a partial index `WHERE under IS NOT NULL` costs nothing in migrations while `0006_graph` is unreleased, and later it would need a `0007`.
3. **Typed output (named risk 4).** I spot-checked these against the code that prints them:
   - The `project` line format, `cli.py:1467` `f"{outcome.name:<15} …"`: `graph` plus 11 spaces, which matches every typed line.
   - `migrate` at `cli.py:569-570`, and the two errors at `storage/migrate.py:71` and `:129-130`: they match.
   - The tutorial's line for `test_projection_graph.py` has 17 dots, and the file has 17 items.
   - `ingest-a-mail-folder.md:67` comes from a run over five appended events and not from an IMAP ingest. That is acceptable because the line depends only on the count, and the report says so.
   - Whether the outputs came from real runs I cannot check beyond their format.
4. **Task 4, part one.** The property's oracle is `read_graph` (`graph_write.py:165`), a fold of the log. If Task 4 points `read_graph` or its callers at the projection, the property becomes a tautology. Keep a log fold as the oracle.
5. **Task 4, part two.** `p_graph_thread` holds every winner: retracted ones, and questions with `to_entity` NULL. The readers have to apply the filters `Graph.entities()` and `Graph.relations()` apply.
6. **Comment, `schema.py:310-312`.** "The ends carry no foreign key either, for the reason `subject` above gives" points at the comment on `p_graph_version.subject`, while `p_graph_thread.subject` just above it does carry one. It is readable, but name the table.
7. **The plan text.** It says `int[]` for `candidates`, and `bigint[]` is right. Note the deviation in the ledger, not in the frozen plan.
