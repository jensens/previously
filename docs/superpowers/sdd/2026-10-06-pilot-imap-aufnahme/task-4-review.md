# Task 4 review: the run — `core/ingest.py` (5b55f68..b4e5a8c)

**Spec compliance:** ✅ — §4.2 (watermark after the append, batches up to `MAX_BATCH`, copies merged within the batch, `ArtifactChanged` → variant key and a second append, one mail at a time), §2.2 (the append rule, erased = known), §3.5 (second raw copy not stored, variant under `<id>#<16 hex>` with `variant_of`), §3.6 (inner mail as its own event in the same batch, `forwarded_in`). The deviations are the ones rulings T4-a and T4-b accepted (lookup before the blobs via `append.known_id`; sanitized attachment names), plus `forwarded_in` naming the variant key of a varied outer (report decision 2), which is consistent with §3.4 ("der Schlüssel der äußeren Mail"). Every test the brief lists is present.

**Quality verdict:** Approved.

Counts: Critical 0, Important 0, Minor 6. There is also one observation for the controller about ruling T4-c and task 6. It is not a finding against this task.

## What I checked, by priority

1. **The watermark never passes unappended mail.** `take` maps the mail, then flushes (append, then watermark) *before* it stores anything of the current mail, and `self.position` is the previous mail's position at that moment. `self.position` moves only after `_take` has returned. `ingest` has no `finally: flush()`, so a connector error, a blob-store error halfway through a mail, or a refused append leaves the watermark where the last successful append put it. `flush` writes the watermark only after `_append` has returned. If two runs overlap, the worst case is a watermark that moves backwards, which is harmless because the run is idempotent. A watermark can never move forwards past unappended mail, because each run writes only positions it has itself appended (or found known). ✅
   Measured: in a scratch copy of the source on `PYTHONPATH`, I moved the watermark write ahead of the append inside `flush`. `test_a_batch_the_log_refuses_leaves_the_watermark` goes red and the other 12 tests I ran stay green, matching the report's row.
2. **Erasure holds.** `known_id` is consulted with the key the event would actually go in under: the outer key, each inner key (its `forwarded_in` rewrite does not touch the key), and the variant key after a base-key `ArtifactChanged`. An erased row (payload `NULL`) returns its `id` from `known_id`, so nothing is stored.
   Measured:
   - Mutation `_holds` → no log lookup: `test_an_erased_mail_is_not_taken_in_again` and `test_a_copy_in_a_later_run_stores_no_raw_mail` go red, the in-batch copies test stays green.
   - Two probes in scratch, both green:
     - an erased **inner** mail (`INVOICE_ID`), re-read from a renamed folder: 0 appended, 2 known, bucket unchanged;
     - an erased **variant**, re-read in the reverse order: 0 appended, 2 known, no variants, bucket unchanged.
3. **Variants.**
   - In-batch: `_holds` compares against `in_batch`, then against the log.
   - Variant of a variant key: `_holds(variant)`.
   - Race: a key another writer appends between the lookup and the append is handled. `_vary` turns the refused entry into a variant, rewrites `forwarded_in` of its direct children, and appends again. A refused variant stops the run before the watermark. The loop terminates, because each round either varies a non-variant entry or raises.
   - Tested with four events in one batch (`test_a_key_another_writer_appends_meanwhile_is_a_variant_or_known`). ✅
4. **Copies.** Same key and same artifact in the batch → known, raw not stored. Asserted as `_objects == {sha(PLAIN)}`, in one run and across runs. ✅
5. **`known_id` in `core/append.py`.** This is `lookup` plus the existing `_check_artifact`, behaviour unchanged. `append` still calls it inside its transaction, so the existing isolation reasoning is untouched. `ingest` calls it in a read-only `snapshot`, which is advisory only, because `append` decides again. It is exercised in `tests/test_append.py` through `append` (the artifact-rule tests at lines 782–878), but not directly (Minor 5).
6. **Memory test.** It measures `VmHWM` growth in a spawned child after `clear_refs`. The argument against `ru_maxrss` (Linux folds the old mm's high-water mark into `signal->maxrss` across `exec`) is correct.
   - Measured five times with the pin: 241, 241, 241 MiB for 3 mails and 240 MiB for 1 mail. That matches the docstring, and the result is deterministic.
   - The bound of 290 sits 49 MiB above the correct run and 46 MiB below the reported mutation (336). CI runs `ubuntu-latest` (24.04, glibc 2.39), the same glibc as here (`Ubuntu GLIBC 2.39-0ubuntu8.9`). `/proc/self/clear_refs` is writable by the process owner on a VM runner.
   - I do not expect flakiness.
7. **Numbers in comments.**
   - `MAX_BATCH` arithmetic in the 600-mail and the watermark tests: correct.
   - "27 MiB of raw mail": 27.37 MiB, measured.
   - "first 64 bits": 16 hex characters, correct.
   - Default mmap threshold of 128 KiB: correct.
   - `BytesIO` sharing the buffer: true for CPython ≥ 3.5.
   - 15 tests in the file and 990 dots in the retyped tutorial block: counted, consistent.
   - The deviations are in Minor 2–4.

## Findings

### Critical

None.

### Important

None.

### Minor

1. **An erased mail forwarded again comes back into the bucket as the new outer mail's attachment.** `src/previously/core/ingest.py:442-450` (`_stored`) stores every attachment of a *new* outer mail, the `message/rfc822` part included.
   Scenario, measured in a scratch probe: run `FORWARDED`, then erase both the inner (`INVOICE_ID`) and the outer, and delete their obsolete blobs. The inner raw blob is gone. A new mail forwards the same inner mail again. Result: `appended=1, known=1`, and the inner raw blob is back under its old address, referenced by the new outer event. The inner event stays known and erased.
   This is per-event erasure working as designed (the new mail is a new artifact), not a defect of this task. A customer re-forwarding an old mail is ordinary, though, and whether erasure should also hold for *content* is a spec question. Name it in the map as an open point; no fix round.
2. **"The one place the rule lives" is not quite true.** `src/previously/core/append.py:150-159` says so of `known_id`, but `_Run._holds` (`src/previously/core/ingest.py:427-438`) carries a second copy of the hash comparison for in-batch keys ("The rule of `append`: a hash that is not given compares with nothing"). If the rule in `_check_artifact` changes, the in-batch copy will not follow. Either reword the docstring ("the one place the rule against the log lives") or point from `_holds` to `_check_artifact`.
3. **The module docstring overstates what a batch does not hold.** `src/previously/core/ingest.py:247-249`: "a batch holds events with their references, not their content". A `RawEvent` carries its units, which is the decoded body text (spec §3.4: the text is only in the units). A batch of 500 text-heavy mails holds 500 bodies. That is harmless in size, but the sentence is a claim. Suggested: "not their raw mail or attachments".
4. **The unpinned memory figures are presented as point values, but vary from run to run.** Test docstring, `tests/test_ingest.py:1150-1157`. Measured without the pin for 3 mails: 322, 322 and 349 MiB, against the stated 346. The pinned figures reproduce exactly. In addition, glibc's dynamic threshold is capped at 32 MiB on 64-bit, so "raises the threshold to the size of the largest block freed so far" holds for these 27 MiB mails but not for a 50 MB one. Since the test pins the threshold, this does not affect the assertion. It matters for the rationale ruling T4-c carries into task 6.
5. **`known_id` has no direct test where it lives.** `src/previously/core/append.py:150`. The new public name is covered only through `append` (the `tests/test_append.py` artifact-rule tests) and through `tests/test_ingest.py`. A mutation of `known_id` would turn the append tests red, so the assurance is held. A four-row direct test would document the public contract: new → `None`, same → id, other → raises, erased → id. Optional.
6. **The refused-batch test docstring says what the test does not do.** `tests/test_ingest.py:959-962`: "its variant key with yet another, after the run looked both up". The second writer appends the variant key with the *same* artifact as the base key (`replace(other, external_id=taken)`), not with yet another one. The run never looked up the variant key `taken`: it only arises in `_vary`. It did not look up `REPLY` either before the hook fired. The test itself is right; only its description is off.

## Observation for the controller (ruling T4-c, task 6), not a finding

Measured in a spawned child with `MALLOC_MMAP_THRESHOLD_=131072` (scratch probe mirroring `measure_run`, reporting absolute `VmHWM`):

| Attachment | Raw mail | Baseline after warm-up | Peak | Growth |
|---|---|---|---|---|
| 20 MiB | 27.4 MiB | 97 MiB | 336 MiB | 240 MiB |
| 36 MiB | 49.3 MiB | 97 MiB | **528 MiB** | 431 MiB |

The report's "about 450 MiB per mail" at Mailu's limit is growth only. The process peak at a 50 MB mail is about 530 MiB, so a CronJob limit of **512 MiB is too small**. Ruling T4-c says "mind. 512 MiB"; task 6 should state a limit that has headroom over ~530 MiB (for example 768 MiB) and measure it. Mailu's default `MESSAGE_SIZE_LIMIT` of 50,000,000 bytes is 47.7 MiB, which still extrapolates to ≈ 515 MiB.

## What I measured (reproducible from the scratchpad)

- **Memory test growth:** a `-p` plugin set `BOUND_MIB = 1` so the assertion prints the growth.
  - Pinned: 241, 241, 241 MiB (3 mails) and 240 MiB (1 mail).
  - Unpinned: 241 MiB (1 mail) and 322, 322, 349 MiB (3 mails).
- **Mutations** in a copy of `src/previously` on `PYTHONPATH` (I verified the copy was the module actually imported):
  - Watermark write before the append in `flush`: 1 red (`test_a_batch_the_log_refuses_leaves_the_watermark`), 12 green.
  - `_holds` without the log lookup: 2 red (erased, later-run copy), 1 green (in-batch copies).
- **Probes, all green:** an erased inner mail is not taken in again; an erased variant is not taken in again. A probe of an erased inner mail forwarded again is recorded in Minor 1.
- **Absolute memory at 20 and 36 MiB attachments:** the table above.
- **Working tree:** unchanged (`git status` clean). I did not run the full suite or the gates.
