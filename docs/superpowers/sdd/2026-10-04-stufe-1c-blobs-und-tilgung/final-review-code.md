# Final review, code and configuration — stage 1c (7cfe686..1ec0b2e)

Reviewer: Opus, 2026-10-05. Read: `final-code.diff` in full (source files at the head read whole where the diff showed only context), the plan's *Global Constraints* and *Review Focus*, `global-constraints.md`, `progress.md`. `final-tests.diff` consulted per doubt. Run: `uv run lint-imports` (6 kept), the `T201` count in `pyproject.toml` (32, matches), the `LogStore` method census in `contract/store.py` (13, matches), the `noqa` census (five, all listed), the ruling census, a `pyrage` probe on what `IdentityError` says (no identity in it), and one scratch measurement outside the tree for Critical 1 (below; the file is `/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/race/test_race.py`, real PostgreSQL through the project's `db` fixture, the only hooks pause a thread between real calls). The six gates were not run by me.

### Strengths

- **The blob rule really lives in one place.** `redaction.blob_expected` over `RedactionIndex.of_reference` is what `redact` (`_blobs_after`), `verify --blobs` (`_blob_findings`), `blob get` (`blob_erasure`) and `show` (`of_reference` in `_blob_lines`) all go through. `read_index` and `_Erasures.observe` build the index with the same filter (kind `action`, payload present, strict `parse`, malformed skipped), so the two index builders cannot disagree on which redactions count. I looked for a second place that decides "erased reference" and found none.
- **The tombstone is enforced by the database, not by discipline.** `event_payload_salt_check` and `unit_tombstone_check` make "erased but salt kept" unwritable; `erase_payload`/`erase_units` set every column in one statement; `RedactionStore` is a type of its own, so nothing typed against `LogStore` can erase.
- **`verify` dispatches per row on `hash_version`, never tries a second version**, keeps checking linkage on an unknown version, and reconciles order against execution in both directions inside the one snapshot. Every forgery class in focus point 4 produces a finding; I found none that goes silent, and nothing in version 2 weakens a version 1 check except the documented skip on a fully erased v1 event.
- **Secrets were hunted, not assumed.** The `UnicodeDecodeError` context leak in `keys.py` was found and fixed by raising after the `except`; `put` drops the foreign traceback for a measured reason; `repr` of store and key provider name nothing secret; `key-id` is pinned to the exact recipient shape before it touches a path; addresses are checked at the object key.
- **Rerun semantics are coherent.** Every `redact_*` recomputes `obsolete_blobs`/`kept_blobs` even when it writes nothing, so "run the same command again" finishes a delete or a catch-up that died after the commit. The commit-then-delete order is right: nothing is deleted from the store for a redaction that might still roll back.
- **Comments with numbers were measured.** Spot-checked: 32 `print` calls, 13 `LogStore` methods, five suppressions, "five of the six contracts" — all true.

### Issues

#### Critical (Must Fix)

1. **A `project` running beside `redact` can leave erased content in the chronicle for good, while `redact` reports success.** `src/previously/core/projection/worker.py:116-142`, reached from `src/previously/cli.py:807-833`.
   `catch_up` keeps `up_to_id` in memory and takes no lock on the projection's state row, so two catch-ups of the same projection run unserialized. Before 1c that needed two `project` runs at once; since 1c every `redact` is a second worker, and a scheduled `project` is the normal deployment.
   **Measured** (scratch test above, PostgreSQL 17, 2026-10-05). Interleaving:
   - A (`project`) reads event 1 and its units;
   - `redact event 1` commits as event 2, and a new event 3 is appended;
   - A inserts event 1's rows with their content and sets its state, uncommitted;
   - B (the catch-up of `redact`) reads 1..3, inserts event 3's rows, and deletes event 1's rows, which it cannot see yet;
   - B's state update waits for A; A commits; B commits `up_to_id = 3`.
   - A's next batch then hits B's rows: `IntegrityError ... p_chronicle_pkey`, a traceback out of `project`.

   Result: `p_chronicle` holds `(1, 1, 'secret line one.')` and `(1, 2, 'secret line two.')` at `up_to_id 3`. A further `catch_up` reports `up to date` and leaves them there. Only a rebuild removes them.

   A measured control: without the append of event 3, A's own next batch reads the redaction and deletes the rows, and the table ends clean.

   The same lack of serialization also gives `redact` itself an untranslated `IntegrityError` traceback after its commit, whenever its batch overlaps rows a concurrent `project` holds uncommitted. That breaks "every failure is one sentence and an exit code" and hides the "run the same command again" advice.

   *Fix (small):* serialize catch-ups per projection. In each batch transaction, read the state row `FOR UPDATE` (a `ProjectionStore` method, e.g. `lock_projection_state`) and take `up_to_id` and `version` from it, not from memory. The rebuild transaction does the same. B then waits for A, re-reads `up_to_id = 1`, processes the redaction and deletes the rows; A's next batch finds itself up to date. The scratch test turns into a regression test that pauses A between `source_keys` and the commit, and it has to be measured red without the lock.

#### Important (Should Fix)

1. **`redact units` prints `redacted by event <id>` while the text stays in the payload of every event `append --text` writes** (`src/previously/cli.py:410`, `src/previously/cli.py:848-874`). This is the first of the two late findings; see that section for the proposed change. I grade it Important and not Critical only because the pages and the map name it. The person running the command reads the terminal, and the terminal says the content is gone.

2. **Since 1c the log has row locks, and a lock failure is reported as "database server … does not answer"** (`src/previously/storage/postgres.py:190-195`, `postgres.py:485-495`). These two are reasoned, not measured.
   - **The lock mode.** `lock_event` takes `FOR UPDATE`, and that conflicts with the `FOR KEY SHARE` every foreign-key check takes on `event`. `p_chronicle.event_id` and `p_source_stats.last_event_id` both reference `event`.
   - **A deadlock.** `redact event` on an event with a shared blob locks several rows in ascending `id`. The source-stats write upserts in order of source name, so its key-share locks on `last_event_id` come in an order unrelated to `id`. A redaction holding row *a* and wanting *b*, beside a projection batch holding *b* and wanting *a*, is a deadlock, and PostgreSQL aborts one of them.
   - **The message.** The abort, a `lock_timeout` or a `statement_timeout` arrives as `OperationalError`. `_transaction` turns every `OperationalError` into `ServerUnreachable` ("is PostgreSQL running there?"), which sends the operator to the network.

   *Fix:* `with_for_update(key_share=True)` (`FOR NO KEY UPDATE`). It still serializes two erasures, because it conflicts with itself and with the `UPDATE`s, and it no longer conflicts with foreign-key checks. Separately, translate SQLSTATE class 40 (and `55P03`) into an error of its own that says to run again, rather than "does not answer".

3. **Two comments state the lock as it was before task 7.** Whoever fixes 1 or 2 next will read them first.
   - `src/previously/storage/schema.py:107-109` says "The one row lock in the system, an erasure's `FOR UPDATE`, is on the erased event and orders two erasures of the same target". Since task 7, `redact event` also locks every event that shares a blob with its target, and `redact blob` locks every user of its blob, so the lock is not only on the erased event, and it orders erasures that share a blob as well.
   - `src/previously/storage/postgres.py:489-490` ("The lock is on the target of an erasure") is wrong in the same way.

#### Minor (Nice to Have)

1. **`redact_event` takes the blob list from the register only** (`src/previously/core/redact.py:234-236`). If the register lacks a row that the payload names (a forged or damaged register, which `verify` reports before the erasure), the redaction neither names nor deletes that blob. After the erasure nothing attests it any more, and the ciphertext stays in the bucket. A union with `read_references(target.payload)` costs one call and removes the dependence on the register being intact. Refusing when the two disagree would be the stricter alternative.
2. **`0003.downgrade` tests `hash_version = 2`** (`migrations/versions/0003_hash_version_2.py:64`). A row with any other non-1 version (this software writes none, a later one might) is silently stripped of its salt and version by the downgrade. `hash_version <> 1` is the safe test.
3. **`append --attach` uploads before `PREVIOUSLY_DSN` is checked** (`src/previously/cli.py:403-413`). An unset DSN, the most predictable configuration error, leaves orphan objects every time. Entering `_storage()` before `_attach` costs nothing.

   Likewise, `redact blob <bad-address>` reports a missing DSN before the address error. The plan's review focus 6 says the address error should come "before anything is asked".
4. **`_cmd_redact` deletes before it catches up** (`src/previously/cli.py:866-868`). The catch-up needs only the database, but on a host without blob settings, or while the store is down, the chronicle keeps showing what was erased until the store answers. The error says so honestly. Catching up first, or attempting both and naming both outstanding, removes the dependence. Together with deferred M5 (stop at the first failing projection), this is the one place where an unfinished erasure stays visible longer than it has to.
5. **`RedactionIndex.of_unit` does not apply the "earlier one" rule the class docstring states** (`src/previously/core/redaction.py:216-219`). It prefers a units redaction over an earlier event redaction. Neither `redact` path can produce that pair, so this only affects the id that `show` and a finding print. `min(..., key=id)` as in `of_reference` would make the docstring true.
6. **`verify --blobs` drops the chain findings already collected** when the blob phase raises: a store hiccup, an unreadable identity, or `InvalidKey` (`src/previously/core/verify.py:678-681`, `cli.py:489-490`). The operator sees one `Error:` line and none of the findings from a pass that completed. Printing the chain findings before the blob phase, or attaching them to the error, would keep a store problem from hiding a forgery report.
7. **The census in `src/previously/contract/store.py:6-15` names a command whose output is not the number.** The `grep … | sort -u` prints 21 lines (`log.` and `storage.` prefixed); 13 is the count of distinct method names behind them. One more pipe stage (`sed 's/.*\.//' | sort -u`) makes the command print the claim.
8. **`S3BlobStore` assumes a bucket without versioning or object lock** (`src/previously/storage/s3.py:112-113`). Nothing checks it. A `get_bucket_versioning` in `verify --blobs` would turn the assumption into a finding; on a versioned bucket every "deleted" blob stays as a noncurrent version that the identity opens.
9. **`, N blobs match` counts erased blobs correctly absent from the store as matching** (`verify.py:681`, `cli.py:493`). That is defensible, but it reads as "N blobs were opened and checked".

### The two late findings

**`redact units` and `append --text`.** Yes, a code change belongs in this stage. The command's one line on standard output is the operator's record that the content is gone. For every v2 event in existence, all written by this stage's `append --text`, that line is false, and an erasure is the one operation where a false success cannot be corrected later.

The smallest change that stops the lie without touching the ingest contract:

- `redact_units` returns whether the target's payload still stands. It is already locked and read (`target.payload is not None`); a field on `Redacted` carries it.
- `_cmd_redact` prints on standard error `the payload of event <id> is not erased and may hold the same text; previously redact event <id> erases it`.
- One test, plus a row in the `cli.md` table.

The structural fix is to stop duplicating the text in the payload in `append`. No deployed database holds a v2 event yet, and `redact units` refuses v1, so after that change no event would exist on which the command can lie. That changes what `show` prints and loses the verbatim original. That belongs to the pilot specification, which redefines ingest anyway (ruling T8-a).

**The id after a restore.** A code change is not needed to merge, but I would make it before the pilot. The failure needs a restore *and* a replay from notes, and `restore-from-a-backup.md` tells the operator to confirm the hash with `show` first. The guard is cheap and turns that instruction into a refusal: an optional `--hash <hex>` on `redact event` and `redact units`, compared with `lock_event`'s `row.hash` under the lock, before anything is written, with a refusal such as `event <id> has hash <x>, not <y>`. Ruling T8-d already makes the hash the thing operators record, so the option uses data they will have.

### Deferred findings

Handed to a later task (`deferred → task N`): **all closed** in the tree.
- 2/M-2: test present, mutation reported in task 3.
- 2/M-5: `cli.md:252`.
- 3/Minor 10b: the sentence is gone from `chronicle.py`.
- 3: the `{ref}` beside "brake": `cli.py:853` and `cli.py:862` carry no citation.
- 3: "only the attempt that wins": `redact.py:150-153` and `concurrency.md:68`.
- 3: "only a forged row": `cli.md:176`.
- 4: 12000/12001: `cli.md:132`.
- 5: `IdentityUnreadable` documented: `blob.py:148-150` and `contract/blobs.py:99-102`.
- 5: the test of a file that cannot be read now covers no-permission and not-UTF-8 with content.
- 5: the T5-d docstring says "reckoned, not counted".
- 5: the read-timeout comment is marked "Not run" (`s3.py:285-294`).
- 6: the `test_blob.py` docstring now says the hashing sink writes first.
- 7: the `redact.py` comment (`redact.py:220-233`) and the restore and `concurrency.md` sentences (`erasure.md:156-165`, `concurrency.md:79-91`).

Left for this review (plain `deferred`):
- Task 1, plan hex count: **already gone**; controller commit `0c8de69`.
- Task 1, `SALT_BYTES` and `unit_digest` speak of erasure as a fact: **already gone**; true since task 3.
- Task 1, the `HASH_VERSION_1` comment: **already gone**; `hashing.py:59-62` is true.
- Task 1, the reason on `hash-format.md`, and "both halves" on `hash-chain.md`: **already gone**; the wording is no longer in the tree. Pages are the second reviewer's.
- Task 1, `HASH_VERSION` names a version nobody writes: **already gone**; `append` writes v2. The comment "nothing reads this one" is true.
- Task 3, Minor 3, "is a redaction" refuses every action: **leave**. It is true while every action is a redaction, and it stands in the map (`landkarte.md:254`).
- Task 3, Minor 7, the loosened quotation test: **leave**. The stricter form breaks on quoted messages that end in an inserted reason, and the remaining blind spot (free text after a final inserted value) is narrow.
- Task 4, M3, the semicolon of the inner error inside the parentheses: **leave**; it matches the contractual wording.
- Task 4, M5, `_catch_up_after` stops at the first failing projection: **leave** on its own, since a rerun completes. See Minor 4 for the ordering it compounds.
- Task 5, Minor 11, RustFS stops sending on delete: **leave**; watch the first CI runs, as planned.
- Task 6, Minor 3, no write failure during `blob get`: **already gone**; `test_blob_get_whose_output_cannot_be_written_leaves_nothing` (`tests/test_cli.py:1875`) does it with `RLIMIT_FSIZE`.

### Declined to judge

- **What an erasure leaves standing:** `source_key`, `occurred_at`, `kind`, the digests, and after `redact blob` the reference with `filename` and `media_type` in the payload. The specification decides the scope of each erasure (§4), and I reviewed against it, not against my preference.
- **`redact blob` repeated after a failure also erases a reference attached since.** The docstring and the restore guide say it erases "for every event that uses it now", so that is specified behavior.
- **`append --attach` racing `redact` of the last user** leaves a missing blob. It is an open limit in the specification and on the pages; the comment at `redact.py:220-233` describes it truthfully. I checked the description, not whether to fix it.
- **The v1 limit** (rows of a fully erased v1 event are not counted) is specified and documented.
- **`verify --blobs` seeing the store after the snapshot** is plan decision 9.
- **Endpoint URLs carrying userinfo** (`https://user:secret@host`) would be printed in store errors. No configuration the project documents does that, and the settings are separate variables.
- **A plaintext `.part` file can be left after a SIGKILL during `blob get`.** It is created 0600 in the target's directory. Nothing in the spec covers process kills on that path.
- **Prose pages** are the second reviewer's.

### Assessment

**Ready to merge? With fixes.**

The erasure path is careful and its rule is single-sourced, and `verify` is not fooled by anything this stage introduced. But Critical 1 is measured: a scheduled `project` beside a `redact` can leave the erased text in the chronicle permanently while `redact` exits 0, and the fix is a row lock in the worker. Important 1 (the false success of `redact units`) should get at least the standard-error notice before the merge.
