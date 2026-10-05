# Final review, stage 1c — documentation and README

Range 7cfe686..1ec0b2e. Read: all of `final-docs.diff`, plus at the head `docs/reference/cli.md` (verify section), `docs/how-to/restore-from-a-backup.md` (whole), `docs/explanation/module-boundaries.md` (protocol section), `docs/index.md`, `docs/explanation/silent-losses.md` (end).
Held against: `src/previously/cli.py`, `core/redact.py`, `core/redaction.py`, `core/verify.py` (findings, blob check), `core/hashing.py`, `core/blob.py`, `core/sealing.py` (messages), `storage/keys.py`, `storage/s3.py` (messages, metadata), `storage/schema.py`, `storage/errors.py`, migrations `0003` and `0004`, and `previously <cmd> --help`.
Nothing was run beyond `--help`; one count was taken: the per-file dots of the tutorial's pytest block sum to 606, matching `collected 606 items`.

### Strengths

- The contractual wordings hold. Every `redact`, `blob get`, `show` and `verify` message in `cli.md` that I checked against `cli.py`, `redact.py` and `verify.py` matches character for character, including the singular/plural split of `stays in the store`, the `<erased by event <id>>` forms, and "earliest" (`of_reference` takes `min`) against "newest" (`blob_erasure` takes `max`). The 15-space padding of the `rebuilt:` line on standard error is right.
- `cli.md` documents a refusal that the global table doesn't list but the code has (`event 4 names hash format 3, which is not known`). It also says that a failed deletion leaves the catch-up undone. That is the kind of completeness the table alone would have missed.
- The lock sets are stated in the same way in `concurrency.md`, `erasure.md` and the code: the target for `units`, the target plus every co-user of its blobs for `event`, the users for `blob`, all in ascending order.
- `database-schema.md` matches `schema.py` and both migrations, constraint and index names included.
- `hash-format.md` matches `hashing.py`: field order, domains (including the deliberate reuse of `previously/units` in version 2), and `SALT_BYTES`.
- The erasure walkthrough in `erase-something.md` is internally consistent across five commands: redaction ids 3, 4 and 5, the `already redacted by event 5` rerun, and `2 blobs match` counting erased blobs as the code does.
- The rewritten restore procedure gets its central safety right. It confirms a target by its hash rather than its `id`. Every path that could erase the wrong event ends at the hash comparison, whatever order the reader learns the tip in.
- No secret appears anywhere. The one identity is written as `AGE-SECRET-KEY-1…`, and the store secret is a placeholder or `$(openssl rand …)`.
- The guides keep the two admonition budgets, and the one warning about losing the key appears where it belongs.

### Issues

#### Critical (Must Fix)

1. **`docs/reference/cli.md:96-99`: the reference for `redact units` never says that the payload keeps the text.**
   - **What's wrong.** Line 96 says what `redact units` erases. Line 99 gives a list of what stays: "Every hash, the source key, the rows of the units and the rows of the blob register". The list reads as complete, and the payload isn't on it. Nothing in the `redact` section, or in the `append` section, says that `append --text` writes the whole text into the payload under `text`.
   - **Why it matters.** Every event the command line can write carries its text there (`cli.py:410`). So for every CLI-written event, `redact units` leaves the erased wording readable in `show` and prints `redacted by event <id>`. An operator who looks the command up in the reference, the page they consult before running it, comes away believing the unit's wording is gone. This is the calibration's "believe something erased that is still readable".
   - **Fix.** Add to the `redact units` sentence: "The payload stays, and with it any copy of the units' wording it holds; `append --text` puts the whole text into the payload, so for an event it wrote, `redact units` takes the units and leaves the text readable in the payload — use `redact event`." In the `append` section, state that the payload is `{"text": <text>, "evidence": …}`.

#### Important (Should Fix)

2. **`docs/how-to/restore-from-a-backup.md:183-184` and `docs/explanation/erasure.md:160`: the restore procedure misses an `erased and still present` case, and line 184 is false in it.**
   - **The case.**
     1. Before the restore point, blob B was erased: `redact event 5`, or `redact blob B`, deleted it.
     2. After that point, B was attached again to a new event 60, which uploaded it again.
     3. The restore loses event 60. Event 5 and its redaction stay.
   - **What happens.** The restored log names B only through erased references, the bucket holds it, and `verify --blobs` reports `blob B is erased and still present` with exit 1.
   - **What the pages say instead.** Line 184 says that an object uploaded after the restore point is named by no restored event and that no check reports it. Line 183 promises that no `missing` finding is left, and says nothing about this one. So the reader ends the procedure on an alarm the guide doesn't explain.
   - **Why it matters.** The guide doesn't say how to clear it. Content the operator once erased then stays in the bucket.
   - **Fix.** The cure exists: `previously redact blob B --reason …` finds B covered, writes nothing, and deletes it (`redact.py:356-359`). Add one paragraph to the guide. Narrow line 184, and the sentence in `erasure.md`, to "a content no restored event names".

3. **`docs/how-to/keep-the-blob-key-safe.md:116-117`: "If no backup of it exists, every object sealed to that key is lost" is wrong while the live identity directory still holds the key, and it omits the one action that saves it.**
   - **When this happens.** The rehearsal reaches this line exactly when the backup lacks a key that the running system still has.
   - **Why it matters.** The operator should copy that file from the identity directory into the backup now. As written, the guide declares the blobs lost and sends the reader to rehearse the other keys.
   - **Fix.** "If no backup of it exists, copy it from the identity directory into the backup now, before anything else; only if the identity directory doesn't hold it either is every object sealed to that key lost."

4. **`README.md:50`, `docs/how-to/erase-something.md:160-166`: the limit on version 1 events is missing from the pages an operator reads before erasing.**
   - **What's wrong.** The README's feature line says "every hash stays, the salt goes". The guide's *What the erasure doesn't reach* says that "every hash" stays, and nothing more about hashes.
   - **Why it matters.** Every event of a log upgraded from stage 1b is in hash format 1. It has no salt, so short erased content stays guessable from its digests. `erasure.md:171-173` and `hash-chain.md` state this; the README and the guide promise more than the code keeps for those events.
   - **Fix.** One sentence in each: "An event written before stage 1c (hash format 1) has no salt, so short content stays guessable from its digests; see {ref}`erasure`."

5. **`docs/how-to/erase-something.md:142`, `docs/how-to/verify-the-chain.md:92`, `docs/explanation/erasure.md:147-173`: "gone from the store" is promised without the bucket's versioning condition.**
   - **Where the condition is stated.** Only `configuration.md:31` and the local how-to (`run-a-blob-store-on-your-machine.md:54`) require a bucket with neither versioning nor object lock.
   - **What happens on a versioned bucket.** `redact` deletes the object, which leaves a noncurrent version. `verify --blobs` calls `stat`, gets "no object", and reports nothing. So `--blobs also checks that every erased blob is gone from the store` (erase-something) is a promise the check cannot keep there.
   - **What the pages leave out.** Neither the explanation of what an erasure doesn't do nor the erasure guide mentions it. The production bucket is the one where it matters, and no operator page tells anyone to check it.
   - **Fix.** Add a bullet to *What an erasure doesn't do* in `erasure.md` and a sentence in `erase-something.md`: a versioned or locked bucket keeps erased blobs, and `verify --blobs` can't see that.

6. **`docs/explanation/hash-chain.md:300`: "{ref}`cli-reference` gives the lines they print as" is false.**
   - **What's missing.** `cli.md` lists the anchor, erasure, register and blob findings. It doesn't list the core chain findings: `payload_hash does not match the payload`, `units_hash does not match the units`, `hash does not match the fields`, `prev_hash does not match the predecessor`, `first event has prev_hash, expected NULL`, `event has <n> rows, <m> checked — the rest is unreachable`, `payload not canonicalizable: …`, `units not canonicalizable: …`, `unit <seq> not canonicalizable: …` (`verify.py`).
   - **Why it's this stage's.** The gap predates the stage, but the stage reworded this sentence and added fourteen findings to the reference. With those added, the reference now reads as the complete list.
   - **Fix.** Add the chain findings to `cli.md` with their conditions, or reword the sentence.

7. **`docs/reference/configuration.md:6` and `:45` contradict the table between them.**
   - **What's wrong.** Line 6 says the `PREVIOUSLY_BLOB_*` variables are read "only by the commands that store or fetch a blob", but `redact` deletes and reads them (row 4 of the table). Line 45 says "`append` without `--attach`, and every other command, reads none of them". Read plainly, that covers `blob get`, `verify --blobs` and `redact`, all of which the table above names.
   - **Fix.** Use "store, fetch or delete" on line 6, and "Every other command, and `append` without `--attach` and `verify` without `--blobs`, reads none of them" on line 45.

#### Minor (Nice to Have)

8. `docs/how-to/erase-something.md:41-65`: see the open decision. Move the warning about the payload copy to the top of *Erase units*, before the command, and frame the worked example as an event that doesn't repeat its text in the payload. As written, the guide's recipe demonstrates an erasure that, for every CLI-written event, leaves the text readable, and only says so after the output.
9. `docs/how-to/keep-the-blob-key-safe.md:75-78`: the rehearsal exports `AWS_SECRET_ACCESS_KEY` into the operator's shell, and step 5 cleans up the files but not the variables. Add `unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_DEFAULT_REGION` to step 5, or pass them inline to the one `aws` command.
10. `docs/how-to/keep-the-blob-key-safe.md:103-113`: the `head-object` example names `age18q27…`, the key that the page creates only later, under *Change the key*. Read in order, the reader meets a recipient they haven't made yet.
11. `docs/how-to/verify-the-chain.md` and `restore-from-a-backup.md`: a wrong or missing `PREVIOUSLY_BLOB_IDENTITIES` directory doesn't give exit 2. `DirectoryKeys` returns `None` on `FileNotFoundError`, so every blob reports `cannot be opened` with exit 1. On a restored or new machine, this reads as a lost key. One sentence beside "Treat exit code `1` as an alarm" would save a night.
12. `docs/how-to/erase-something.md:28-32` / `restore-from-a-backup.md:160`: consider adding the source key `(source, external_id)` to the erasure record. A submission lost with the restore and submitted again comes back under a new `id` and hash, which the hash check correctly refuses. Without the source key, though, nothing points the operator at the re-submitted copy.
13. `README.md:12-81`: the README states the erasure limits beside the feature, but not the blob limit with the highest cost: losing the identity loses every blob for good. One clause under the blobs bullet, with a link to `keep-the-blob-key-safe`, would put it beside the feature as the erasure limit is.
14. `docs/index.md:24`: the how-to card lists "restore a backup, add a migration, rebuild a projection, check the chain in operation", but not erasing or attaching. The explanation card, likewise, names nothing of the stage.
15. `docs/explanation/module-boundaries.md:298-299`: "A second protocol exists now, `ProjectionStore`… `LogStore` is append-only—write once, read in chain order, never change." Stage 1c added a third, `RedactionStore` (`contract/store.py:86`), which changes rows of the log. The sentence about `LogStore` stays true, but the page's count of protocols is stale, and the reason erasure got its own protocol belongs exactly here.
16. `docs/explanation/blobs.md:28-33`: "The provider of the store never sees a key… the absence of anything for the provider to be honest about." The provider sees each object's name, which is the unsalted SHA-256 of the plaintext, so anyone who holds a candidate file can confirm that it is in the bucket. `erasure.md:174-175` says this for the log; `blobs.md` should say it for the bucket.
17. `docs/explanation/erasure.md:127`: *What "covered" means* says that an erasure "locks the row of its target event, or for a blob the rows of the events that use it". That omits the co-users that `redact event` also locks. The section above and `concurrency.md` have it right; "or more, as above" would close the gap.
18. `docs/reference/cli.md:202`: `--blobs` "Also read every blob the blob register names", but erased blobs are only asked for (`stat`), not read. Use the verb that the later paragraph uses.
19. `docs/reference/database-schema.md`: it documents that `0004_event_blob` refuses to go back while the table holds a row, but not that `0003_hash_version_2` refuses once version 2 rows or units without content exist (`0003_hash_version_2.py:56-64`). The second refusal matters more to an operator.
20. `docs/explanation/blobs.md:216`: the heading "What verify checks in the store" names a command without code formatting, unlike every other heading in the stage.
21. `docs/explanation/hash-chain.md`, under *Separating the domains*: "Every wrapped digest carries a version and a domain of its own". In version 2 the units hash deliberately shares `previously/units` with version 1; `hash-format.md` says so, and this sentence slightly overstates it.

### The open decision

The pages that state the limit state it well: `erasure.md` (table, section and bullet), the README's limits paragraph, and `erase-something.md` under *Choose the target*, *Erase units* and *What the erasure doesn't reach*. A reader who reads the guide from the top understands, before running the command, that the text stays.

A reader who jumps to the section they need doesn't.

- The *Erase units* heading leads straight to the command, and the warning comes two lines after the output.
- The reference, `cli.md` under `redact`, never says it at all (Critical 1).
- `redact units --help` says "erase the content of the named units" — code, for the other reviewer.

Since every event the command line can write repeats its whole text in the payload, the sentence has to stand where the decision is taken:

1. In `cli.md`, beside "`redact units` erases …": the payload stays, and `append --text` events keep their text there.
2. As the first line of *Erase units*, before the command.

I'd also recommend reframing the worked example so that it doesn't present, as a recipe, an erasure that achieves nothing for the only events the CLI writes.

### Declined to judge

- Code quality, the `--help` text of `redact units`, and whether `redact units` should refuse or warn on a payload that repeats the units: code, for the other reviewer. I mention the help text only because it bears on the open decision.
- `.importlinter` and the `KEPT (1 ignored import)` / `(2 ignored imports)` lines in `module-boundaries.md`: configuration, for the other reviewer. I didn't rerun `lint-imports`.
- The measurements quoted in `blobs.md` (memory peaks, the race rounds, `age` 1.2.1) and `hash-chain.md` (the guessing rate): they're dated measurements by scripts in the plan's annexes. I didn't rerun them, under the brief's read-only constraint.
- The exact output formats of RustFS, `aws` CLI 2.37.9 (`aws: [ERROR]: …`, `make_bucket:`, `download:`), `age-keygen` and `age`: they're not reproducible without running containers, which the brief rules out.
- The RustFS environment variable names `RUSTFS_ACCESS_KEY` and `RUSTFS_SECRET_KEY`: same reason.
- The truth of `uv sync` output lines in the tutorial (`Resolved 101 packages`, and the declared omissions): a measurement I can't retake read-only. The 606 sum I did check.
- The frozen specification and `docs/superpowers/`: frozen or German working records, outside the documentation set.
- Vale, linkcheck and the `html` build: gates, which the controller reruns.
- No page tells an operator who upgrades from stage 1b to run `alembic upgrade head`. It's a gap of the project, not of this stage, and older stages had the same.
- The correctness of the projection derivation claims in `projections.md` (batch order, the later-target rule): they're code behavior that the other reviewer and the tests hold. I checked only that the pages agree with each other.

### Assessment

**Ready to merge?** With fixes.

The reference and the explanations are exact against the code in nearly every detail, and the restore procedure's hash check is sound. But the one page an operator consults before `redact units` lets them believe that a paragraph is gone while it stays readable (Critical 1).

The restore and key guides each have a path that ends in a wrong conclusion: an unexplained alarm with erased content lying in the bucket, and a key declared lost while it could still be saved. Both are one-paragraph fixes.
