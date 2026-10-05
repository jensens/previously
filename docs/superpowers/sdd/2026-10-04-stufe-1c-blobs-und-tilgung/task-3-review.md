# Task 3 review — erasure of events and units (30f7768..a0377ba)

I read the diff file in three passes: source, then tests, then documentation and configuration.
No changed file was re-read separately, because no hunk I had to judge was cut off.
I made these focused checks outside the diff, each for a named risk:

- **Concurrency of the lock:** the isolation level of `begin()` (`postgres.py:112`, READ COMMITTED), so that the `read_index` after a lock wait sees the first erasure's commit.
- **Reconciliation inside the snapshot:** `verify.py:530/543`, where `reconcile` is called inside `with storage.snapshot()`.
- **The store.py count claim:** the `grep` it names, run over the five modules. It gives ten distinct names, as claimed.
- **The vocabulary claim:** the `.vale.ini` count, 12 lowercase entries of 16, as claimed.
- **The pyproject claim:** the `print` count in `cli.py`, 26, as claimed.
- **Stale sentences outside the touched files:** a grep across `src`, `docs` and `tests`.
- **The rebuild sentence on `erasure.md`:** `core/projection/chronicle.py:44`. It skips a unit without content, so that sentence is true.
- **The loosened docs-references test:** I listed every open-ended pattern it now builds.
- **The refusal for an unknown hash version:** whether `hash_version` is constrained in `schema.py`. It is not.

I ran no tests.

### Spec Compliance

❌ Issues found, both in documentation:

- `docs/explanation/erasure.md` doesn't say what the version 1 skip costs (Important 1).
- `docs/explanation/hash-chain.md:300` still says the check "establishes five things" (Important 2).

Everything else the brief names is present:

- **Interfaces:** they match the brief's signatures exactly.
  - `read_by_kind`.
  - `RedactionStore` with `lock_event` (`FOR UPDATE`), `erase_payload` (one `UPDATE`, `null()` for SQL `NULL`) and `erase_units` (one `UPDATE` over the five columns, with an early return for an empty sequence).
  - `Redaction`, `MalformedAction`, the two builders, `action_name`, `parse` (strict, all three scopes), `RedactionIndex`, `read_index`, `Redacted`, `redact_event`, `redact_units` and `RedactionRefused`.
- **The procedure:** one transaction per attempt.
  - The lock comes first, and `read_index` is read after it.
  - "Covered" means a redaction exists.
  - The tombstones are set even when nothing is written.
  - `prepare`/`tip`/`link`/`insert_event` run, then the retry on `ChainPositionTaken` with `backoff_delay`, `MAX_RETRIES` and `ChainConflict`.
- **Tests:** every test the brief names exists in the named file.
- **Mutations:** every mutation it names is reported red, each with a green control.
- **The race test:** the two-thread test uses a barrier inside `lock_event`. That makes the `read_index`-before-lock mutation deterministic, and the report gives 20 of 20 runs red.
- **`verify`:**
  - It reconciles at the end of the pass, inside the snapshot.
  - Each target is read by `id`.
  - The version 1 rule follows the brief.
- **Deferred findings, all three closed:**
  - M-2: the version 2 skip gets a test and a mutation.
  - M-5: both task 2 findings are now on `cli.md`.
  - The `SALT_BYTES` comment is rewritten.
- **Contractual wordings:** every one in this task matches the table character by character.
  - The seven findings.
  - `redacted by event <id>` and `already redacted by event <id>`.
  - `unit <seq> was already erased`.
  - The five refusals.
  - `payload=<erased by event <id>>` / `payload=<erased>`, and `  ¶<seq> <erased by event <id>>` / `  ¶<seq> <erased>`.
- **Terminal output:** `stdout` of `redact` is one line, and no citation reaches the terminal.
- **Sentences the brief named as no longer true:** each one is rewritten.

⚠️ Cannot verify from the diff:

- Whether the M-2 mutation, "v2 skip removed", was run on exactly the line it names. The skip line is unchanged context outside the diff hunks, and the report's red output is consistent with it.
- Whether `test_a_redaction_racing_an_append_keeps_the_chain` loses a chain position in every run. It has no forcing barrier inside the write, so whether `_retrying`'s `except ChainPositionTaken` branch is reached deterministically is not shown (Minor 6).

### Strengths

- **The layering is clean.**
  - `core/redaction.py` is pure.
  - `storage` filters by `kind` only and doesn't interpret a payload.
  - `core/redact.py` holds the procedure.
  - `verify` keeps `examine` at complexity 9 by moving the bookkeeping into `_Erasures` and `_execution_findings`.
- **The JSON-`null` trap was caught by measurement.** `erase_payload` writes `null()`, not `None`, and the comment beside it records why.
- **The two-thread test is designed well.** The barrier sits *inside* the wrapper's `lock_event`, so the mutation in which `read_index` comes before the lock reads the index before the barrier, red every time, instead of depending on timing. The `lock_timeout` test of `lock_event` has a control (a plain read doesn't wait), as the project's rule asks.
- **The tests forge with raw SQL that follows ruling P-1, and assert exact `Finding` lists.**
  - The tombstone tests and the not-carried-out tests run on both hash versions (`WRITTEN_IN`).
  - The version 1 partial case is asserted alongside them.
- **`test_docs_references.py` now holds the refusals and all nine new findings.**
  - Three page-side mutations were measured red, each restored to green.
  - I listed every open-ended pattern the loosened `_static_parts` builds. None matches broadly enough to admit a quotation whose fixed parts differ from the code: the shortest are `['FINDING ', ': ', '']`, `['redacted by event ', '']` and `['there is no event ', '']`.
- **`erasure.md` carries every point the brief lists, in the explanation quadrant.** That includes the honest case of a tombstone without an order. The findings table is on `cli.md`, where it belongs.
- **The comment counts were recounted.** These are the `contract/store.py` count with its command, the `print` count and the vocabulary count, and each was measured.

### Issues

#### Critical (Must Fix)

None.

#### Important (Should Fix)

1. **`erasure.md` doesn't say what the version 1 skip costs.**
   - **Files:** `docs/explanation/erasure.md:66-68` and `:17`, with `src/previously/core/verify.py:128` and `:354`.
   - **What the code does:**
     - `_units_finding` no longer computes `units_hash` once any unit of a version 1 event lacks content.
     - On a version 1 event whose units are all erased under an event redaction, nothing checks the set of unit rows at all.
     - A tombstone row deleted, or a fabricated tombstone row inserted (any `seq`, `content` and the four other columns `NULL`), produces no finding. `of_unit` finds the event redaction, `_partial` doesn't fire because every unit is erased, and `units_hash` isn't recomputed.
     - In version 2, `units_hash_v2` over the stored digests still catches both.
   - **Why it matters:**
     - The brief prescribes the skip, and the report names the consequence (concern 4). The page doesn't.
     - The page tells the reader that the rows of the units stay as tombstones and every hash stays. A reader takes that to mean the tombstone rows are still attested.
     - For version 1, they are not.
   - **Fix:** add a sentence in the section on version 1 ("Why the payload can't be erased in part" → units paragraph) saying the following:
     - Once all units of a version 1 event are erased, nothing can recompute its units digest.
     - So the number and the `seq` of its tombstone rows are attested by nothing.
     - That is part of the cost version 1 carries, beside the unsalted digests.
   - **Test (optional):** a test pinning this behavior would turn the disclosed limit into a measured one, in the way the old `test_a_tombstone_passes` pinned the seam: verify reports nothing after a tombstone row of a fully erased version 1 event is deleted.

2. **`docs/explanation/hash-chain.md:300-305` is now false, in a touched file.**
   - **The text:** "The check reads the chain … and establishes five things; {ref}`cli-reference` gives the one line each of them prints as", followed by the enumeration of the four event checks and the count.
   - **Why it's false:**
     - Since this commit `verify` also establishes order and execution of erasure, with seven new finding lines on `cli.md`. The "five" no longer covers what the check establishes, nor "the one line each of them prints as".
     - "the units digest against the units" no longer runs for a version 1 event with any unit erased.
   - **The rule it breaks:** the brief and the constraints say that every statement in a touched file is re-read against the new state.
   - **Fix:** this page edited the `tombstone-seam` section and the version 2 closing paragraph and left this paragraph alone. Name the erasure reconciliation, either as a sixth thing or as a separate sentence pointing to {ref}`erasure`, and qualify the version 1 units digest.

#### Minor (Nice to Have)

1. **"tombstones included" describes a rollback that never has tombstones in it.**
   - **Where:** `src/previously/core/redact.py:119` and `docs/explanation/concurrency.md:66`.
   - **Why:** in both functions the tombstones are written *after* `insert_event`. When the chain position is lost, the attempt has set none yet. The sentence isn't false, but it implies a case that cannot occur.
   - **Fix:** say "the transaction rolls back before any tombstone is set", or drop the phrase.

2. **The refusal for version 1 units interpolates the version.**
   - **Where:** `src/previously/core/redact.py:199`.
   - **Why:**
     - The table's wording is the literal "hash format 1". The code prints `{target.hash_version}` and refuses on `!= 2`.
     - `hash_version` has no CHECK constraint (`schema.py:50`), so an event with an unknown version (which `verify` reports as `hash_version 3 is not known`) gets "was written in hash format 3, which attests its units only together". That is a claim about a format nobody knows.
     - For every event the system writes, the output is identical to the table.
   - **Fix:** refuse `== 1` with the literal sentence, or keep the condition and the literal "1".

3. **The refusal of an action target says "is a redaction" for any `action`.**
   - **Where:** `src/previously/core/redact.py:87`.
   - **Why:**
     - A hand-written action of another name, or an action that `verify` reports as `action has no valid form`, gets "event N is a redaction".
     - The comment beside it states the assumption, and refusing every action is the safer direction.
     - The sentence is still untrue for such a row.
   - **Fix:** acceptable for now. Revisit when a second action kind arrives, as the report says.

4. **Two errors leave `core` outside the table.**
   - **Where:** `src/previously/core/redact.py:191` and the empty-reason refusal in `_check_input`.
   - **Why:**
     - An empty `seqs` raises a bare `ValueError`, not a `PreviouslyError`.
     - The empty reason in core is a second wording, not in the table.
     - Neither is reachable from the CLI (`nargs="+"`, and `cli.py:432` checks the reason first).
   - **Fix:** fine as a guard. Consider `RedactionRefused` for the first, so that nothing foreign leaves `core`.

5. **A reason of only whitespace passes.**
   - **Where:** `src/previously/cli.py:432` checks `not args.reason`.
   - **Why:** `--reason " "` passes and writes a redaction with a blank reason. `parse` accepts it too, because the string isn't empty.
   - **Fix:** a matter of taste, so no change is needed. If one is wanted, `.strip()` in both places.

6. **The retry path of `redact` isn't forced deterministically.**
   - **Where:** `tests/test_redact.py:298`.
   - **Why:**
     - The brief mandates the pattern of `test_append.py`, a barrier before the call. Whether a chain position is actually lost depends on timing.
     - `_retrying`'s `except` branch is therefore covered only when the race happens, and line 128 (`ChainConflict`) not at all.
   - **Fix:** a wrapper `LogStore` whose `insert_event` raises `ChainPositionTaken` once, and always in a second case, would make both branches deterministic. The report suggests the same.

7. **The loosened `_is_the_same_sentence` admits trailing filler after a trailing interpolation.**
   - **Where:** `tests/test_docs_references.py:288/356`.
   - **Why:**
     - `cli.md` could quote `redacted by event 42, and its blobs too`, and the test stays green, because `['redacted by event ', '']` matches any suffix.
     - Interpolations in the middle already had this property, so this is a consistent extension, not a hole that lets a wrong *fixed* wording through.
     - The report's concern that `f"{a}: {b}"` would match any line with `: ` is real but hypothetical: no such pattern exists today.
   - **Fix:** a cheap tightening is to require the interpolated tail to contain no space.

8. **`postgres.py:6` keeps "no update, no delete" as the opening statement.**
   - **Why:** the brief named this sentence as certainly false. The fix added a qualifying paragraph instead of correcting it. It follows the pattern the docstring already uses for projections, and a reader who reads the whole docstring isn't misled.
   - **Fix:** the first sentence alone is false for the log now. Qualify it ("no update except the two below").

9. **`hashing.py:66` says "`core.redact` erases both in one statement".**
   - **Why:** `core.redact` issues no statements. `storage`'s `erase_payload` and `erase_units` do, each in one `UPDATE`.
   - **Fix:** name `RedactionStore`, or "the store".

10. **The report missed two stale sentences outside the touched files.** Its list names `projections.md`, the README and a `test_projection_worker.py` docstring. These two are carried forward to their owners:
    - `src/previously/core/projection/chronicle.py:43`: "because nothing in the tree erases a unit yet". This is task 4's file.
    - `tests/test_migration_0003.py:67`: "Erased by hand: nothing in the tree erases a unit".

### Assessment

**Task quality:** Needs fixes

**Reasoning:**
- The code, the tests and the contractual wordings are sound and match the brief.
- The concurrency design and its deterministic two-thread test are good.
- Two documentation statements break the "comment is a claim" rule:
  - `erasure.md` leaves out that a fully erased version 1 event's tombstone rows are attested by nothing.
  - `hash-chain.md` still says the check establishes five things.
- Both are small, page-only fixes.
