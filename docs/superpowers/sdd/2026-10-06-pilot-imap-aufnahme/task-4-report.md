# Task 4 report: the run — `core/ingest.py`

Status: DONE_WITH_CONCERNS. Commit: b4e5a8c (base 5b55f68).

## What was built

- `src/previously/core/ingest.py` (new): `Ingested(appended, known, variants, position)` and `ingest[Conn](log, marks, blobs, connector, *, recipient, recorded_at)`, with the signature from the brief. The two protocols arrive as two parameters for one store, the same shape `redact_event` uses.
  How a run goes:
  1. It reads the watermark and iterates `connector.fetch(since)` lazily.
  2. For each `Fetched` it calls `map_mail` and walks the tree of `Mapped`, the outer mail first and then the inner ones.
  3. It looks up every event before it stores anything.
  4. For each new event it stores the raw mail (`message/rfc822`, no file name, first) and the attachments with `store_blob` over `io.BytesIO`, sets `blobs`, and sets `payload["raw"]` to the raw mail's address.
  5. It appends in batches. Once a batch is appended, it writes the watermark at the position of the last `Fetched` the batch covered.
- `src/previously/core/append.py`: new public `known_id(storage, conn, event) -> int | None`, which is `lookup` followed by the existing `_check_artifact`. `append` now calls it. Behaviour is unchanged, and the rule lives in one place (see decision 1).
- `tests/test_ingest.py` (new, 15 tests): an in-memory `ListConnector` (positions as `uid`, an optional `fail_at`, and a `hook(index)` called before each mail, which a test uses to read the watermark or to act as a second writer), plus a `FileFolder` for the memory test.
- `docs/tutorials/record-your-first-event.md`: the typed test run retyped (ruling P-1).

## Decisions (beyond the brief — please confirm)

1. **The run looks every event up *before* it stores its blobs**, against the batch and against the log (`known_id`, one `snapshot` per event). Two reasons:
   - Spec §3.5 says the second raw copy is "not stored". That holds only within one batch if the lookup comes after the blobs. Across runs, for example when a copy is filed into the folder later, a second object would land in the bucket.
   - **Erasure:** after `redact event` and the deletion of its obsolete blobs, a re-read of the folder (renamed folder, changed `UIDVALIDITY`) would put the erased raw mail **back into the bucket** as an orphan, before `append` answers "known". `test_an_erased_mail_is_not_taken_in_again` holds this, and the mutation without the log lookup turns it red.
   The `ArtifactChanged` handling from spec §4.2 still exists, in two places:
   - **At the lookup:** `known_id` raises `ArtifactChanged`, and the run takes the event under `variant_key` with `variant_of`.
   - **At the append:** for a key another writer appended after the lookup, `append` raises `ArtifactChanged`; the run turns the named event into a variant and appends again. The blobs stay the same.
   A variant that is refused again (a 64-bit prefix collision of `variant_key`) stops the run, before the watermark.
2. **The inner mails of a variant name the variant key in `forwarded_in`.** Spec §3.4 says `forwarded_in` holds "the key of the outer mail"; once the outer becomes a variant, that is the variant key. Otherwise the pointer resolves to the other mail. This happens at the lookup (through the tree walk) and in the race (`_vary` rewrites the batch's children).
3. **Attachment names that a blob reference refuses:** `chain._filename_problem` refuses `/`, `""`, `.` and `..`. A mail named `Angebot 10/2026.pdf` (an ordinary German date in a file name) would make `append` refuse the whole batch **at every run**. The run turns `/` into `_` and turns `""`, `.` and `..` into no name. The raw mail keeps the original name. A test and a mutation cover it.
4. **The watermark is written also for a batch with nothing to append** (every mail known): otherwise a folder of known mails would be read again at every run. The order holds: the append (if any) first, then the watermark.
5. **Batches:** a mail goes into the next batch when `len(batch) + events of the mail > MAX_BATCH`, so a mail is never split across two batches. The counts in `Ingested` are of events, as the docstring says.
6. **`Ingested.appended` versus `known` after the append:** the tip is read just before `append`. An `id` at or below it is a key that another writer appended after the lookup, and counts as known. The docstring names the remaining window between reading the tip and the append's own transaction.
7. I removed the `del fetched` in the loop that I had added. It held the previous raw mail for the duration of the next fetch, but mapping a mail costs more than that (see the memory section), so no measurement can see the difference. The module docstring no longer claims it.

## Gates (final tree, each run separately)

1. `uv run ruff check .`: All checks passed.
2. `uv run ruff format --check .`: 84 files already formatted.
3. `uv run pyright`: 0 errors, 0 warnings, 0 informations.
4. `uv run lint-imports`: 7 kept, 0 broken.
5. `uv run pytest --cov --cov-report=term-missing`: 990 passed in 142.02s.
   `core/ingest.py` is at 100%, `core/append.py` at 99%. The one missing line is 593, the final `raise ChainConflict` after `MAX_RETRIES`, a contention path that predates this task.
6. `make -C docs html`: build succeeded, no warning. `make -C docs vale`: 0 errors, 0 warnings, 0 suggestions in 31 files. `make -C docs linkcheck`: exit 0, 0 broken.

Ruling P-1: before the retype, the suite showed exactly `1 failed, 989 passed` (`test_docs_typed_output`). I set the number to 990, then ran a plain `uv run pytest` green (`990 passed in 140.80s`) and retyped the whole block from that run, leaving out the `rootdir:` line.

## Mutation measurements

The whole of `tests/test_ingest.py` (15 tests) ran against each mutation; the source was restored afterwards and the diff checked clean. "Control" means the tests that stayed green under the same mutation. The unmutated file is green (15 passed) before and after.

| Mutation | Red | Green control |
|---|---|---|
| **Watermark before the append** (brief), as a watermark written per `Fetched` as soon as it is taken | `the_watermark_follows_the_append` (watermark uid 3 instead of 1), `a_batch_the_log_refuses_leaves_the_watermark`, `more_mails_than_a_batch_holds` (watermark moves before the batch) | 12 others, among them the copies and variant tests |
| Watermark before the append **inside** `flush` | `a_batch_the_log_refuses_leaves_the_watermark` | 14 others: when the append succeeds, the order is invisible, which is why this test exists |
| **Merging within the batch removed** (brief) | 3: the copies test (one run), the variant test (one run), and every-test-mail (the MAILS hold copies); `append` refuses with a duplicate key | `a_copy_in_a_later_run_stores_no_raw_mail`, the variant test (two runs) |
| Log lookup before the blobs removed | `an_erased_mail_is_not_taken_in_again` (raw mail back in the bucket), `a_copy_in_a_later_run_stores_no_raw_mail` | the in-batch copies test |
| **Variant at the lookup removed** (brief) | 2: the variant test (one run) and every-test-mail | the variant test (two runs) stays green, because the race path catches it at the append; the next row removes both |
| Variant removed entirely (`_variant` keeps the key) | 4: both variant tests, the race test, every-test-mail | 11 others |
| Variant at the append (`_vary`) removed | `a_key_another_writer_appends_meanwhile…` | 14 others |
| Rewrite of `forwarded_in` in the race removed | `a_key_another_writer_appends_meanwhile…` (the inner mail names the old key) | 14 others |
| Counting a raced key as known removed | `a_key_another_writer_appends_meanwhile…` (4 appended, 0 known) | 14 others |
| Name fix for `/` and `""` removed | `an_attachment_name_with_a_slash…` (InvalidPayload) | 14 others |
| Flush on a full batch removed | `more_mails_than_a_batch_holds` and `the_watermark_follows_the_append` (BatchTooLarge) | 13 others |
| **Memory:** every mapped mail kept until the run ends | `a_run_holds_one_mail_at_a_time` (336 MiB > 290) | 14 others |

Not measured as a mutation: "never split one mail across two batches". Splitting would be invisible from outside, because the watermark covers only mails taken completely: after an abort between the two halves, the next run finds the outer event known and appends the inner one. The rule holds by construction (`_count` before `_take`), not by a test.

## Memory: the bound and how it was measured

`test_a_run_holds_one_mail_at_a_time`: three invented mails with a 20 MiB attachment each (27 MiB of raw mail in base64), read from files one per fetch. The bound is `BOUND_MIB = 290`.

- **Measured in a spawned interpreter** (`ProcessPoolExecutor` with the `spawn` context). Inside the child, after a warm-up run, it writes `5` to `/proc/self/clear_refs` and reads `VmHWM` before and after the run. **Not `ru_maxrss`, and that is a deviation from the brief's "resource.getrusage, wie Stufe 1c"**, for a reason I measured: Linux carries `ru_maxrss` over an `exec`, so the child started at pytest's size. The same unmutated run read 75 MiB alone and 0 and 1 MiB after the other tests of the file. In that context, the memory mutation stayed green in the full-file sweep at the first attempt (55 and 93 MiB under a bound of 150). That bound is gone.
- **glibc's `MALLOC_MMAP_THRESHOLD_` is pinned to 128 KiB in the child**, through `monkeypatch.setenv` before the spawn. Measured, `VmHWM` growth by number of mails:

  | Mails | Pinned | Not pinned |
  |---|---|---|
  | 1 | 240 MiB | 241 MiB |
  | 3 | 241 MiB | 346 MiB |
  | 6 | 241 MiB | 383 MiB |

  With `ru_maxrss` in an earlier setup, without the pin: 91, 162, 203 and 313 MiB for 1, 3, 6 and 12 mails; with it: 92, 80, 69 and 94 MiB. So the run does let go of each mail; the growth without the pin is glibc's dynamic mmap threshold plus heap fragmentation.
- The bound lies between the correct run (241 MiB, three runs) and the mutation that keeps every mapped mail (336 MiB, three runs).

## Concerns

1. **Memory per large mail is about 9× its raw size.** A 27 MiB raw mail costs about 240 MiB of peak during `map_mail` plus the stores. The stores stream (`BytesIO` shares the buffer, and `store_blob` reads in 1 MiB pieces), so the cost is in the mapping (task 2). At Mailu's 50 MB limit that is about 450 MiB per mail. The CronJob's memory limit in the kup6s handoff (task 6) has to account for it.
2. **Without the pin, peak memory grows with the number of large mails in a run** (241, 346, 383 MiB for 1, 3, 6 mails; earlier 313 for 12). The first ingest of a real customer folder with many large attachments can approach a pod limit. A cheap fix is `ENV MALLOC_MMAP_THRESHOLD_=131072` in the `Dockerfile` (Debian trixie, glibc) and in the compose example. This is an operations decision, so I left the `Dockerfile` alone; it is for the controller or task 5/6.
3. **Decision 1 extends the run beyond the brief's sequence** (a lookup before the blobs, and `known_id` made public in `append.py`). It closes an erasure hole: erased raw mail written back into the bucket. Please confirm. The reference and explanation pages for the run (task 6) should state it.
4. **Decision 3** (`/` becomes `_`, an empty name becomes none) is a fix for ordinary mail that task 2's mapping did not cover. The reference page should name it.
5. Named, not chased (misuse or hostile only):
   - A single mail with more than `MAX_BATCH - 1` attached mails makes `append` raise `BatchTooLarge` at every run, and the watermark stays before it.
   - A `variant_key` collision on the first 64 bits stops the run.
   - The count window in decision 6.
   - Blobs stored for a batch that never got appended stay until the next run (spec open point).
6. The memory test uses `/proc/self/clear_refs` and a spawned interpreter, which differs from the stage 1c tests; the docstring gives the reason.
7. The two large tests (600 mails; a mail with 499 attached mails) take about 13 s each, and the whole file about 45 s. The suite went from about 106 s to about 142 s.
8. I did not observe "red first" as a run: the tests passed at their first run against the implementation. The mutations above are the measured red. I did not run `pip-audit` (not a gate).
