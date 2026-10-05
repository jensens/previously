# Task 8 review — ef5c84b..789533e

### Spec Compliance

✅ Spec compliant. Every file in the brief's list is touched, and each step is carried out:

- Step 1: four new guides, each hosting-neutral.
  - `erase-something.md` covers the three forms, `show` and `verify` as checks, the permanent reason, exit code 2, and the backups with `{ref}erasure`.
  - `attach-and-fetch-a-file.md` covers the seven variables, `append --attach`, `show` and `blob get`.
  - `run-a-blob-store-on-your-machine.md` gives RustFS 1.0.1 and creates the bucket with `amazon/aws-cli:2.37.9`. It says this is the test server and not the operational one, and it checks versioning and object lock by measurement.
  - `keep-the-blob-key-safe.md` covers `age-keygen`, the file named after its recipient, the backup kept apart, a rehearsal with an S3 tool and `age -d -i`, and the key change. It has exactly one warning.
- Step 2: restore, verify and rebuild follow.
  - In the restore guide, a `missing` blob is explained, erasures are to be repeated, and a record outside the database is required. The page still has one admonition.
  - `verify-the-chain` gains a nightly `--blobs` section.
  - `rebuild-a-projection` is corrected. Its snippet showed the raised version as `2`, which is now the chronicle's current version (`chronicle.py:118`).
- Step 3: explanation pages.
  - `backup-encryption` now names two keys and the retention.
  - `silent-losses` gets one sentence.
  - `erasure` and `blobs` have their measurements dated.
- Step 4: README. Ten commands (agrees with `cli.md:6`), the new capabilities, and the limits paragraph with a link.
- Step 5: the tutorial is retyped from one run, with the sentence under *Next steps*. The test block adds up: the per-file dots sum to 606.
- Step 6: map. Measured 72 → 93 with the awk command on base and head (6 struck, 27 added; 72 − 6 + 27 = 93).
  - All fourteen §12 points are present, each under a unit of its own.
  - All fifteen execution points are present.
  - The three merges keep both halves: §12.2 with point 4 (concurrency.md named), §12.9 with point 2 (memory), and §12.11 with point 9 (all four Hetzner questions).
  - The struck entries name commits. `git show --stat` of 72a0044, 4c078ad, a0377ba, a65d1cc, 600f757, 13d0d5e and 9efb419 matches each entry.
- Step 7: freeze.
  - The spec diff is +20/−4: the frozen header (identical in wording to `aeusserer-anker.md`), the status line and the §12 introduction. Nothing else changed.
  - `design-records.md` gets its paragraph.
  - `grep -rn "§" src tests migrations | grep -v "frozen design record"` prints nothing. There are 15 lines in 7 files, the same per-file counts as `git grep -c § 7cfe686`.
  - The README row is added.
- Deferred task 7 findings: all three are addressed (`redact.py` comment, `erasure.md` restore sentences, `concurrency.md` lock sets).
- Not extra: `concurrency.md` was outside the brief's list but was required by the third deferred finding.
- Considered judgment, not a deviation: the brief asked for "Teilprojekt 1 ist damit abgeschlossen". The map instead says the stage is built and awaits the merge, which follows the CLAUDE.md rule that the merge is the acceptance.

⚠️ Cannot verify from the diff:
- That the commands not run as shown behave as written. The implementer lists them itself; I checked them against code and `cli.md` and found them consistent.
- That the six gates are green. The implementer claims they are; the controller reruns them.

### Strengths

- **The new erasure limit is in the right place.** The finding that `redact units` leaves the text of an `append --text` event in the payload is real: `cli.py:410` writes `payload={"text": args.text}`.
  - `erase-something.md` puts it in *Choose the target*, the first thing a reader about to erase sees.
  - Its own worked example then shows the payload still holding the erased sentence, and says so.
- **Output blocks agree with the transcripts.** Hashes, ids, the `show` lines, the `verify` lines, `already redacted by event 5`, the object-lock error and the `head-object` metadata all match the raw runs.
- **No block shows output that no run produced unless it says so.** The kept-blob notice is introduced as "in this form" and matches the wording in `_kept_line` (`cli.py:755-761`).
- **The `redact.py` comment is now true, statement by statement.**
  - The register is read before the lock (`redact.py:234-240`).
  - `_blobs_after` reads `events_by_blob` again inside the same transaction (`redact.py:190`). Under `begin()`'s READ COMMITTED (`storage/postgres.py:116`), a commit before that read is seen and the blob is kept. A later commit is not seen, which is the race described in `concurrency`.
  - `redact_event` locks `[event_id, *sharing]` ascending (`:240`), and `redact_blob` locks all users (`:349`), so the two meet on a shared row.
  - `redact_units` locks only its target (`:288`) and returns no blob lists (`:317`).
- **Every settings claim checks out against `cli.py`:**
  - `redact` reads the store settings only when it has something to delete (`_delete_obsolete`, `:788-792`), and it never reads a recipient or an identity.
  - `blob get` and `verify --blobs` read `_identities()` and the store (`:478`, `:709`).
  - `append --attach` reads the recipient and the store, never the identities (`:351-352`).
  - `blob get` writes only after the address check, through `mkstemp` (0600) and `os.replace` (`:654-669`).
  - The `verify --blobs` findings stand under `min(event_ids)` (`verify.py:745`). There are four of them.
- **No secret appears anywhere.** I grepped for `AGE-SECRET-KEY` across the diff, the handback, the commit-message files and `docs/`. The only hit is the form `AGE-SECRET-KEY-1…` in prose. The commit messages carry `Assisted-By:` only.
- **The map is honest.** Half-closed entries are reworded rather than struck. An entry struck with a remainder says what remains ("geprüft wird es nicht").

### Issues

#### Critical (Must Fix)

None.

#### Important (Should Fix)

1. **`docs/how-to/restore-from-a-backup.md:158` — "Repeat every erasure … with the same `previously redact` command" can erase the wrong event.**
   - Ids are assigned as tip + 1 (`redact.py:136`, and the same in `append`). After a restore to an earlier point, every id above the restored tip is free again.
   - Any event appended since the restore takes one of those ids. That includes ingestion resumed by a CronJob, and the redaction events the repetition itself writes.
   - An erasure whose target was appended after the restore point therefore names, when repeated verbatim, a different event or nothing.
   - The redaction events the repetition writes get refused as targets ("is a redaction"). An ordinary event appended in the meantime does not: it is erased, irreversibly, and with a reason that belongs to someone else's content.
   - Fix: say to repeat only the erasures whose target event id is at or below the tip of the restored log, and to do it before anything else writes. Say that an erasure of an event above the tip has nothing to repeat, because the event went with the restore. Have the record kept outside the database (`:160`) carry the source key beside the id, so that a target can be confirmed with `show` before it is erased again.
   - The map entry for that record (`landkarte.md`, *Betrieb*) could note the same.

2. **`README.md:78-82` and `docs/explanation/erasure.md:18` and `:147-…` state the reach of `redact units` wider than the code keeps it.**
   - The README's limits paragraph says an erasure "takes content out of the log". It lists what stays (backups, blob address, source key) and leaves out that, for every event the command line writes today, the text of erased units stays in the payload.
   - On `erasure.md`, the table's *Units* row says the content of the named units disappears. The section *What an erasure doesn't do*, which is where a reader looks for the limits, does not mention it. The accurate paragraph sits in *Why the payload can't be erased in part* (`:106-108`).
   - This is the defect the brief ranks worst: a promise stated wider than the code keeps it, on the two pages read before the guide.
   - Fix:
     - Add to the *Units* row's "What stays" a copy of their text in the payload, where the payload repeats it, as `append --text` does.
     - Add a bolded item to *What an erasure doesn't do*, pointing to the paragraph.
     - Add one clause to the README's limits paragraph.

#### Minor (Nice to Have)

3. **`docs/tutorials/record-your-first-event.md:39` — the uv hardlink warning is left out without saying so.**
   - Verdict on the implementer's point: this is a finding, but a minor one.
   - The block is a dated measurement, and the sentence below it claims to enumerate what the page leaves out. The enumeration is now incomplete by three lines.
   - The warning depends on the environment, so leaving it out is right. Saying so costs one clause: "and a warning uv prints when its cache and the checkout lie on different file systems".

4. **`docs/explanation/backup-encryption.md:5` and `:100` — present tense for a backup that does not exist.**
   - Verdict on the implementer's point: this is a real inaccuracy.
   - "Previously encrypts its backups" says the software does something it does not do. No backup and no operations exist (the map's *Wo das Projekt steht*).
   - Line 100 was written by this task and says "The backups are encrypted …" in the same tense. Two sentences earlier, the task itself wrote "In the operation this design plans".
   - The global constraint says whoever touches a file reads its sentences against the new state.
   - Minor rather than Important: the page is an explanation of an operations design, and no command or guide relies on it.
   - Fix: frame both sentences as the design ("The backups this design plans are encrypted …").

5. **`docs/tutorials/record-your-first-event.md:67` — "The third and the fourth prepare the log for erasure and for attached files, which this tutorial doesn't use."**
   - Migration `0003` brings `hash_version`, the salts and the unit digests.
   - The tutorial's own event is written in hash format 2 with a salt, and the note at the tutorial's `show` step says the salt feeds the hash. So the tutorial does use the third step.
   - Fix: "The third brings hash format 2, with the salt you'll see feed the hash; the fourth prepares the log for attached files, which this tutorial doesn't use."

6. **`docs/superpowers/landkarte.md:24` and `:28` — the map will be false on `main` the moment it gets there.**
   - "Gebaut, auf dem Zweig `worktree-stufe-1c-blobs`, und zur Abnahme … steht aus: der Merge nach `main`" arrives on `main` through exactly that merge.
   - Either the controller amends it in the PR's last commit, or the wording is chosen to hold in both states (for example, "Abnahme: der Merge dieses Zweigs, PR #…"). Note it for the PR step at least.

7. **`docs/how-to/verify-the-chain.md:92` — "`--blobs` reads every blob the log names out of the store, opens it".**
   - An erased blob is only asked for, with `stat`, and is never read (`verify.py:752`).
   - The sentence is true of the blobs that have to lie, which is what dominates the run time.
   - Fix: "every blob that has to lie in the store".

8. **`docs/how-to/erase-something.md:137` — "Leave it out if the log names no blob; it then needs no blob setting."**
   - The antecedent of "it" is ambiguous: `--blobs`, or `verify`.
   - Fix: "Without `--blobs`, `verify` reads no blob setting; leave it out if the log names no blob."

Verdict on the third point the implementer raised: `keep-the-blob-key-safe.md` no longer shows the `ls -l` output, and that is **no finding**.
- The creation steps are `shell` blocks that present no output.
- The claim that `age-keygen -o` creates the file readable by its owner only is backed by the run (`-rw-------` in the transcript).
- Dropping a line that named the implementer's user and locale was right.

Checks run, each for a named risk:

- **A page says something the code doesn't do.** I read `cli.py` (settings, `_attach`, `_fetch_to`, `_cmd_blob_get`, `_delete_obsolete`, `_catch_up_after`, `_cmd_redact`, `main`), `core/redact.py` in full, the blob part of `core/verify.py`, `storage/keys.py` and the exit-code table in `cli.md`. Issues 1, 2 and 7 come out of this.
- **The comment's claims in `redact.py` hold under the isolation level.** `storage/postgres.py:113-119` shows READ COMMITTED for `begin()`.
- **Version claim in `rebuild-a-projection`.** `grep version: int` gives chronicle 2 and source-stats 1.
- **Stale neighbors.** Greps for `AES-GCM`, `aes-256`, "no erasure", "only migration", the command counts and "stages 1a and 1b" over `docs/` and `README.md` (excluding `superpowers/` and `_build`) turned up only issue 4. The `AES-GCM` hits in `blobs.md:45` and `:52` are historical and correct.
- **Map count.** The `CLAUDE.md` awk program gives 72 on `git show ef5c84b:…` and 93 on the head.
- **Paragraph signs.** The `grep` command from design-records prints nothing. `git grep -c § 7cfe686` gives 15 lines in 7 files.

### Assessment

**Task quality:** Needs fixes

**Reasoning:** The guides, the map, the freeze and the comment are accurate and well measured. However, the restore guide tells an operator to repeat erasures by an id that a restore frees for another event, and the README and the limits section of `erasure.md` state the reach of `redact units` wider than the code keeps it.
