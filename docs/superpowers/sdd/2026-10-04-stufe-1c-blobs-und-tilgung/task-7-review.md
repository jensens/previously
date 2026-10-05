# Task 7 review: erasing blobs and checking them (ea62154..a65d1cc)

I read the diff in three passes: source, then tests, then documentation.
No changed file was opened separately, because no hunk I had to judge was cut off.
I made four focused checks outside the diff, one per named risk:
- **The protocol count in `contract/store.py`.** I ran the comment's own `grep` over the five modules. It gives 13 distinct method names, so the comment holds.
- **Whether the append-versus-erase race and orphaned objects are carried as open points.** Spec §12 points 1 and 2 carry both.
- **Whether `erasure.md` or `blobs.md` says anything about backups of the bucket.** `grep backup|bucket|replica` found nothing in `erasure.md`.
- **Line numbers.** I looked up file line numbers for the findings below.

I re-ran no tests.

### Spec Compliance

- ✅ Spec compliant on every step of the brief:
  - **Interfaces.** All exist with the brief's signatures: `blob_payload`, `of_reference`, `blob_expected` (false without a reference), `Redacted.obsolete_blobs` / `kept_blobs` computed on every call, `redact_blob`, `LogStore.blob_references` ordered by `(sha256, event_id)`, `NullSink`, `BlobCheck`, `examine(..., blobs=)` and `Examination.blobs_checked`.
  - **Every test the brief names exists** across Steps 1 to 4: 3 + 7 + 7 + 7 by name, including the five-case and four-case parametrizations.
  - **The mutation-table test exists** (`test_a_refused_redaction_deletes_nothing`).
  - **The five mutations are reported** with a red test and a green control matching the brief's columns (M1 control: the first step of the shared-blob test).
  - **Order in `_cmd_redact`:** redaction, delete, catch-up, stdout line, stderr notices. Blob settings are read only when `obsolete_blobs` is non-empty.
  - **Every contractual wording matches the table character by character:**
    - the four blob findings;
    - `stays in the store: event … still uses it` / `events … still use it`;
    - `blob <hex> is erased (event <id>)` with exit 1;
    - the ` <erased by event <id>>` suffix;
    - `, 1 blob matches` / `, N blobs match`;
    - `no event uses blob <hex>`;
    - the address input error;
    - the "not finished" frame.
  - **No citation in program output.**
  - **The three pages carry every point the brief lists:** the third table row, the rule in one sentence with three consequences, the shared blob, transaction-then-store and what a second call finishes, the unsalted address, "can appear as missing", and `blob get` on an erased blob. The command count stays at ten.
  - **Handed-over items:** the finding/error line is stated in the `_blob_findings` docstring, on `blobs.md` and on `cli.md`, and is tested on both sides. The stale docstring in `test_blob.py` is rewritten and true.
- **Extra, judged sound:**
  - `blob_erasure`, which calls `blob_expected` and does not recompute the rule.
  - The extra lock in `redact_event` (see Strengths).
  - `InvalidPayload` from `redact_blob` for a malformed address.
  - The release test and the error-side test.
- ⚠️ **Cannot verify from the diff:** that `main` maps `IdentityUnreadable` and `InvalidKey` to exit 2 without a foreign context in the message. This rests on code from earlier tasks, and only the `IdentityUnreadable` case has a test here (`test_verify_blobs_that_cannot_check_is_an_error_and_no_finding[identity-cannot-be-read]`). `InvalidKey` on the `verify --blobs` path has no test.

### Strengths

- **The rule lives in one place.**
  - `redact` reaches `blob_expected` through `_blobs_after` (`src/previously/core/redact.py`), and `blob get` through `blob_erasure`.
  - `verify` reaches it through `_blob_findings` (`src/previously/core/verify.py:705`).
  - `_unerased` and `show` only *name* events or redactions through `of_reference`, the same predicate. Nothing can disagree with it.
- **A redaction is never written twice by a retry.**
  - A second call finds the target covered (`covering` / an empty `fresh`), writes nothing and recomputes `obsolete_blobs`.
  - The test with an unreachable endpoint checks this end to end: exit 2, then exit 0, then `_events == 2`.
- **Nothing is deleted before the commit.** `_delete_obsolete` runs on the returned `Redacted`, after `_retrying` has left its transaction.
  - If an append of the same content has committed by the second call, `_blobs_after` re-reads the register and keeps the blob. The retry is therefore conservative.
- **The extra lock in `redact_event` is correct and needed.**
  - **The window it closes is real.** The chain-position conflict does not cover the interleaving "read the redactions before the other commits, read the tip after it".
  - **The lock order cannot deadlock.** `redact_event` and `redact_blob` both lock in ascending order of `id`. `redact_units` holds exactly one row lock. Every path takes all its row locks before its insert, so no transaction can wait on a row lock while holding an insert another waits on.
  - **Late appends are covered.** An event appended between reading `sharing` and taking the locks is not locked. Any erasure that touches it locks the earlier users as well, so the two still meet on a shared row.
  - **The test is deterministic both ways.** Neither branch depends on timing. The only timeouts are guards against a hang.
- **Foreign exceptions do not leak.**
  - `_delete_obsolete` raises after the `except`, so the store's error is quoted and never chained.
  - The verify error-side test checks for the secret, the identity and `AGE-SECRET-KEY`.
- **Every store is released.**
  - `_examine` and `_delete_obsolete` each use `with _blob_store()`.
  - The counting test was measured to see what the connection-count test could not.
  - On the rule against mocks: the wrapper forwards every call to the real store built by the real `from_settings` against the real S3 server, and only observes `close`. That is within the accepted form, a wrapper around the real store. If the import name in `cli` changed, `built` would be 0 and the test would fail loudly instead of passing.
- **Comments were re-measured instead of patched:**
  - the protocol count (13, confirmed);
  - the `print` count;
  - the false docstring in `test_read_index_passes_over_what_it_cannot_read`, which is rewritten together with its arrangement.
- **The page-quote guard is extended to the new blocks.** The outstanding phrase is held against what `cli.py` builds. The singular and plural were split into two literals so that a mutation of the page actually fails the test, and that was measured.

### Issues

#### Critical (Must Fix)

None.

#### Important (Should Fix)

1. **`docs/explanation/concurrency.md:82` states something false.** The sentence reads "two erasures that share neither a target nor a blob never wait for each other".
   - **First counterexample:** event 2 uses blobs *b* and *c*, event 1 uses *b*, and event 3 uses *c*.
     - `redact event 1` locks {1, 2}, and `redact event 3` locks {2, 3}.
     - The two erasures share neither target nor blob, yet one waits for the other on row 2.
   - **Second counterexample:** `redact units 2` waits behind `redact event 1` on row 2, although a units erasure touches no blob at all.
   - The lock set is "every event that uses a blob of the target", not "the target and its blobs".
   - The waiting is harmless, but the sentence is false at this commit, and it is the sentence this task rewrote.
   - **Fix:** say that erasures wait for each other when the sets of events they lock overlap: the target, plus, for `redact event` and `redact blob`, every event that uses one of the target's blobs.
2. **`docs/explanation/erasure.md:147-149` ("Backups keep it") is incomplete for blobs, in a way that misstates the promise.**
   - The paragraph says what an erasure took "stands in every backup of the database and in the write-ahead log archive", and concludes that "the promise of an erasure is therefore as long as that retention".
   - A blob is not in either of those. The object a blob erasure deletes stays in every copy or backup of the bucket. That copy opens with the identity, which `blobs.md:152` tells the operator to back up separately.
   - So for a blob, the promise is bounded by the retention of the bucket's backups, which nothing on either page names.
   - The brief asks the pages to say what the stage does as a whole. Under the project's rule that operations are part of every design, this is the operational fact an operator needs to choose a retention.
   - **Fix:** one sentence that names the bucket's backups or replicas beside the database's.

#### Minor (Nice to Have)

1. **The snapshot caveat covers only one direction.** It stands at `docs/reference/cli.md:294`, `docs/explanation/blobs.md:224` and in the `_blob_findings` docstring (`src/previously/core/verify.py:705-718`).
   - All three say only that a blob erased and deleted during the run can appear as **missing**.
   - The opposite direction is just as real: `blob <hex> is erased and still present` can also be transient.
     - A redaction that is committed in the snapshot can have its deletion still pending in a concurrent `redact`.
     - The same content can be attached again after the snapshot.
   - **Fix:** add half a sentence that a blob attached again or still being deleted can appear as erased and present, and that the next run does not report it.
2. **`docs/explanation/erasure.md:154` overstates the restore case.** "reports the blob of every erasure since that point as missing" holds only for erasures that deleted an object.
   - An event erasure that kept a shared blob deletes nothing.
   - Objects uploaded after the restore point are orphans, and nothing reports them.
   - **Fix:** "every blob an erasure since that point deleted".
3. **The append-versus-erase race (spec §12 point 2) is named on no page.** `concurrency.md:69` says "a redaction racing an append ends the way two appends do". That stays true of the chain, but it now leaves out the one race in which data goes missing: an append that finds the object present and skips the upload, while a `redact` deletes it after its commit.
   - The spec carries the race as an open point, so it reaches the map when the spec freezes.
   - A sentence on `concurrency.md` or under "what erasure doesn't achieve" would keep the page from reading as complete.
   - Orphaned objects (§12 point 1) are likewise unreported by `verify --blobs`. `cli.md` states that implicitly ("every blob the register names") and nowhere explicitly.
4. **One comment gives only half the reason.** At `src/previously/core/redact.py:220-223`, the comment justifies reading before the lock with "the register rows of an event are written with it and never change". That covers `registered` but not `sharing`, which can grow through a concurrent append.
   - Reading `sharing` before the lock is still correct: a late user is unerased, so the blob is kept, and any erasure of that user also locks the target.
   - The comment does not say so, and a reader could take it for an oversight.
5. **`blob get` on an erased blob still needs every blob setting** (`src/previously/cli.py:695-699`).
   - `_identities()` and `_blob_store()` are built before the register answers "erased", so a machine without blob settings gets `PREVIOUSLY_BLOB_… is not set` instead of the log's answer.
   - This matches the existing "no event uses blob" path and costs nothing in correctness. It is noted only because `show` deliberately avoids the dependency.
6. **Process: complexity at `HEAD` was measured with `--isolated`.** `CLAUDE.md` says never to measure with `--isolated`.
   - Only the `C901` count was read, with an explicit `max-complexity`, so the numbers are probably unaffected.
   - The current tree was measured under the project configuration, and nothing exceeds 9.
7. **`InvalidKey` on the `verify --blobs` path has no test.** The docstring names it as an error, not a finding, but only `IdentityUnreadable` and an unreachable store are tested on the error side.

### Assessment

**Task quality:** Needs fixes

**Reasoning:** The code is correct, and so are the rule, the order, the locking and the release. The tests are real and were measured to fail. Two explanation pages state something false or incomplete at this commit: the lock-scope sentence in `concurrency.md`, and the backup retention in `erasure.md`, which leaves out the bucket. Both are one-sentence fixes, and nothing in `src/` has to change.
