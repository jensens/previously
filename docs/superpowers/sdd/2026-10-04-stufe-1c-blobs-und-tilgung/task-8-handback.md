# Task 8 — the implementer's report, as handed back

Filed by the controller on 2026-10-05. The implementer of task 8 was not allowed
to write its report file (the tool answered that subagents return their findings
as text), did not look for another way, and returned the report as its final
message. What follows is that message, unchanged apart from this note.

---

**Status:** DONE_WITH_CONCERNS

**Commits** (on top of `ef5c84b`; trailer `Assisted-By: Claude Opus 5.5 <noreply@anthropic.com>`; message files `task-8-commit-msg-{1,2,3}.txt` in the plan directory):
- `29e1ef1` docs: four guides for blobs and erasure, and the old guides follow
- `e5b0759` docs: explanations say what holds of erasure, blobs and their keys
- `789533e` docs: README, tutorial and map for stage 1c, and its specification freezes

**Gates:** all six pass on `789533e` (ruff, format, pyright, lint-imports, 606 tests passed, docs html/vale/linkcheck). Vale now checks 28 files instead of 24.

**Concerns:**
1. **`redact units` leaves the unit text in place for events written by `append --text`.** That command stores the whole text in the payload under `text`. In my run, after `redact units 2 2`, `show 2` printed `¶2 <erased by event 3>` while the payload still held "The client wants it by Friday." The pages (`erasure.md`, `erase-something.md`) and the map now say this. Which event shapes erasing units is for is a decision for the maintainer.
2. The tutorial leaves out uv's hardlink warning without saying so. The warning appeared only because my scratch directory is on a different file system than uv's cache.
3. Four anonymous Docker volumes from my `postgres:17` containers remain. I removed the containers without `-v` and did not prune, because a prune would also remove volumes that aren't mine.
4. I walked the `age` emergency path in a container, not with an installed tool. Acceptance condition 14 still asks for it by hand.
5. `backup-encryption.md` still opens "Previously encrypts its backups…" in the present tense, though no backup exists yet. It wasn't on the handed-over list, so I flagged it and left it.

# Full report

## Runs, and how I ran them (all on 2026-10-05)

**Tutorial.**
- A fresh `git clone` of the branch at `ef5c84b` into the scratch directory, against `postgres:17` started with the tutorial's own `docker run`.
- I logged each command with `eval`, stdout and stderr together, with `PYTHONUNBUFFERED=1` so that lines appear in the order a terminal shows them.
- Two earlier attempts were thrown away together with their clone and database:
  - without unbuffered output, `verify` printed its notice before `chain intact`;
  - a pty capture produced colour codes.
- The run typed onto the page is a third, complete run from scratch.

**Blob guides.**
- `previously` ran from the worktree's `.venv`, against a fresh `postgres:17`.
- `age`, `age-keygen` and `aws` ran through shell functions:
  - `age` and `age-keygen` with `docker exec --user uid:gid -w $PWD agebox …`. `agebox` is `alpine:3.22` after `apk add age`, which gave **age 1.2.1, package `age-1.2.1-r10`**.
  - `aws` with `docker run --rm --network host --user uid:gid -e HOME=/tmp -v dir:dir -w $PWD -e AWS_* amazon/aws-cli:2.37.9`, which is AWS CLI 2.37.9.
- RustFS ran as `rustfs/rustfs:1.0.1`.
- The rehearsal's "identity from the backup" was a `cp` of the identity file; there was no real backup to take it from.
- A first full run was thrown away for two reasons:
  - the first `redact` built the projections and printed two extra `built:` lines;
  - `aws s3 cp` printed a garbled progress line.
- The kept run adds `previously project` before the erase steps and `--no-progress` to the fetch.

**Containers.** All my containers are stopped and removed, and so is the `previously-blobs` network. Scratch keys, the clone and the work directory are deleted.

## Raw transcripts

### Tutorial session

The 98 ` + package==version` lines are cut here as on the page:
```
$ uv sync --all-extras
Using CPython 3.14.3
Creating virtual environment at: .venv
Resolved 101 packages in 0.98ms
   Building previously @ file:///tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/tut
      Built previously @ file:///tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/tut
Prepared 1 package in 331ms
warning: Failed to hardlink files; falling back to full copy. This may lead to degraded performance.
         If the cache and target directories are on different filesystems, hardlinking may not be supported.
         If this is intentional, set `export UV_LINK_MODE=copy` or use `--link-mode=copy` to suppress this warning.
Installed 98 packages in 174ms
[exit 0]
$ uv run alembic upgrade head
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_log, Log, units, idempotency key
INFO  [alembic.runtime.migration] Running upgrade 0001_log -> 0002_projections, Projections: state, chronicle, source statistics
INFO  [alembic.runtime.migration] Running upgrade 0002_projections -> 0003_hash_version_2, Hash format version 2: version, salts and unit digests
INFO  [alembic.runtime.migration] Running upgrade 0003_hash_version_2 -> 0004_event_blob, The blob register: which event names which blob
[exit 0]
$ uv run previously append \
    --source email \
    --external-id 2026-10-03-kickoff@example.org \
    --text "The client approved the new homepage design.

Next milestone: content migration starts Monday."
1
[exit 0]
$ uv run previously log
1	2026-10-05T02:55:45.634838+00:00	observation	e8fa1a71a86a
[exit 0]
$ uv run previously verify
chain intact
no anchor given: verify attests that the log is unchanged, not that it is complete; see `previously anchor`
[exit 0]
$ uv run previously anchor > anchors.txt
[exit 0]
$ uv run previously verify --anchors anchors.txt
chain intact, 1 anchor holds
[exit 0]
$ uv run previously show 1
id=1 kind=observation
occurred_at=2026-10-05T02:55:45.634838+00:00
hash=e8fa1a71a86acd49e34247147322983d6bb6ca888182ea60f9b0bfe7050ea720
evidence=recollection
payload={"evidence": "recollection", "text": "The client approved the new homepage design.\n\nNext milestone: content migration starts Monday."}
  ¶1 The client approved the new homepage design.
  ¶2 Next milestone: content migration starts Monday.
[exit 0]
$ uv run previously project
chronicle       built: 1 event, up_to_id 1
source-stats    built: 1 event, up_to_id 1
[exit 0]
$ uv run previously project
chronicle       up to date, up_to_id 1
source-stats    up to date, up_to_id 1
[exit 0]
$ uv run previously chronicle
1	1	2026-10-05T02:55:45.634838+00:00	email	2026-10-03-kickoff@example.org	The client approved the new homepage design.
1	2	2026-10-05T02:55:45.634838+00:00	email	2026-10-03-kickoff@example.org	Next milestone: content migration starts Monday.
[exit 0]
$ uv run previously stats
email	1	2	2026-10-05T02:55:45.634838+00:00	2026-10-05T02:55:45.634838+00:00
[exit 0]
```

What the page leaves out of this:
- the `Building` and `Built` lines, because they name the checkout directory; the page says it leaves them out;
- the hardlink warning; the page does not mention it (concern 2).

### Blob session: `run-a-blob-store-on-your-machine`
```
$ export PREVIOUSLY_BLOB_ACCESS_KEY=previously-dev
$ export PREVIOUSLY_BLOB_SECRET_KEY=$(openssl rand -hex 16)
$ docker network create previously-blobs
7e5ca730b63e…
$ docker run -d --name previously-blobs --network previously-blobs -p 9000:9000 -e RUSTFS_ACCESS_KEY="$PREVIOUSLY_BLOB_ACCESS_KEY" -e RUSTFS_SECRET_KEY="$PREVIOUSLY_BLOB_SECRET_KEY" rustfs/rustfs:1.0.1
595eb8b64323…
$ docker run --rm --network previously-blobs -e AWS_ACCESS_KEY_ID=… -e AWS_SECRET_ACCESS_KEY=… -e AWS_DEFAULT_REGION=us-east-1 amazon/aws-cli:2.37.9 --endpoint-url http://previously-blobs:9000 s3 mb s3://previously-blobs
make_bucket: previously-blobs
[exit 0]
$ (same) s3api get-bucket-versioning --bucket previously-blobs
[exit 0, no output]
$ (same) s3api get-object-lock-configuration --bucket previously-blobs

aws: [ERROR]: An error occurred (ObjectLockConfigurationNotFoundError) when calling the GetObjectLockConfiguration operation: Object Lock configuration does not exist for this bucket
[exit 254]
$ export PREVIOUSLY_BLOB_ENDPOINT=http://localhost:9000
$ export PREVIOUSLY_BLOB_REGION=us-east-1
$ export PREVIOUSLY_BLOB_BUCKET=previously-blobs
```
Here "(same)" stands for the full command line, which the page types out in full; the AWS key values were the two exported variables.

### Blob session: `keep-the-blob-key-safe`, creating the key
```
$ age-keygen -o key.txt
Public key: age1x7xtemjzh6dl65j2wjfhcewmdyawczlhw00387um4n4drl9v93lsv6d3pa
$ age-keygen -y key.txt
age1x7xtemjzh6dl65j2wjfhcewmdyawczlhw00387um4n4drl9v93lsv6d3pa
$ mkdir identities
$ mv key.txt "identities/$(age-keygen -y key.txt)"
$ ls -l identities
-rw------- 1 <user> <user> 184 … age1x7xtemjzh6dl65j2wjfhcewmdyawczlhw00387um4n4drl9v93lsv6d3pa
$ export PREVIOUSLY_BLOB_RECIPIENT=$(ls identities)
$ export PREVIOUSLY_BLOB_IDENTITIES=$PWD/identities
```

### Blob session: `attach-and-fetch-a-file`
```
$ printf "Kickoff minutes: the client approved the new homepage design.\n" > minutes.txt
$ previously append --source email --external-id 2026-10-05-minutes@example.org --text "The minutes of the kickoff are attached." --attach minutes.txt
1
$ previously show 1
id=1 kind=observation
occurred_at=2026-10-05T02:58:45.665679+00:00
hash=57cf08a07e7efb0c91d1cfcd16a51ad9b92fabf299d1e9837c714976490b8544
evidence=recollection
payload={"blobs": [{"filename": "minutes.txt", "media_type": "text/plain", "sha256": "72f4f2c5a92ade61b696c0fe800b8af775fd2f3982b123693379e6ee7cd264f2", "size": 62}], "evidence": "recollection", "text": "The minutes of the kickoff are attached."}
  ¶1 The minutes of the kickoff are attached.
  blob 72f4f2c5a92ade61b696c0fe800b8af775fd2f3982b123693379e6ee7cd264f2 62 text/plain minutes.txt
$ previously blob get 72f4…64f2 --output minutes-copy.txt
wrote 62 bytes to minutes-copy.txt
$ cmp minutes.txt minutes-copy.txt
[exit 0]
```

### Blob session: `verify-the-chain`
```
$ previously verify --blobs
chain intact, 1 blob matches
no anchor given: verify attests that the log is unchanged, not that it is complete; see `previously anchor`
$ previously anchor > anchors.txt
$ previously verify --anchors anchors.txt --blobs
chain intact, 1 anchor holds, 1 blob matches
```

### Blob session: rehearsing the backup
```
$ cp "identities/$PREVIOUSLY_BLOB_RECIPIENT" rehearsal/identity.txt ; cd rehearsal
$ export AWS_ACCESS_KEY_ID=$PREVIOUSLY_BLOB_ACCESS_KEY  (and SECRET, REGION)
$ aws --endpoint-url "$PREVIOUSLY_BLOB_ENDPOINT" s3 cp --no-progress s3://$PREVIOUSLY_BLOB_BUCKET/72f4f2c5…64f2 blob.age
download: s3://previously-blobs/72f4f2c5a92ade61b696c0fe800b8af775fd2f3982b123693379e6ee7cd264f2 to ./blob.age
$ head -c 21 blob.age; echo
age-encryption.org/v1
$ age -d -i identity.txt -o content blob.age
[exit 0]
$ sha256sum content
72f4f2c5a92ade61b696c0fe800b8af775fd2f3982b123693379e6ee7cd264f2  content
```

### Blob session: changing the key
```
$ age-keygen -o key.txt
Public key: age18q27nlpyfjrmftuusq6dtdgl8nmqqnwduq63fs5ly5ns7wjsqpwsuf2y4l
$ mv key.txt "identities/$(age-keygen -y key.txt)"
$ ls identities
age18q27nlpyfjrmftuusq6dtdgl8nmqqnwduq63fs5ly5ns7wjsqpwsuf2y4l
age1x7xtemjzh6dl65j2wjfhcewmdyawczlhw00387um4n4drl9v93lsv6d3pa
$ export PREVIOUSLY_BLOB_RECIPIENT=age18q27…y4l
$ printf "Second draft of the homepage copy.\n" > draft.txt
$ previously append --source email --external-id 2026-10-05-draft@example.org --text "The second draft is attached.

The client wants it by Friday." --attach draft.txt
2
$ previously verify --blobs
chain intact, 2 blobs match
no anchor given: …
```

### Blob session: `erase-something`
```
$ previously project
chronicle       built: 2 events, up_to_id 2
source-stats    built: 2 events, up_to_id 2
$ previously redact units 2 2 --reason "a deadline the client asked to keep out of the record"
redacted by event 3
$ previously show 2
id=2 kind=observation
occurred_at=2026-10-05T02:58:49.072311+00:00
hash=4819583f9e9fcdeec92a46e267593d4d78a24193b0233c18f86523b2c4ecc5af
evidence=recollection
payload={"blobs": [{"filename": "draft.txt", "media_type": "text/plain", "sha256": "b00c29a1d42316f16fd5ef9c72ce82bc5c1dcf24ff1280e12bfe3d61e3846373", "size": 35}], "evidence": "recollection", "text": "The second draft is attached.\n\nThe client wants it by Friday."}
  ¶1 The second draft is attached.
  ¶2 <erased by event 3>
  blob b00c29a1…6373 35 text/plain draft.txt
$ previously verify
chain intact
no anchor given: …
$ previously redact blob b00c29a1…6373 --reason "the draft is superseded and must not be kept"
redacted by event 4
$ previously show 2
(as above, last line) blob b00c29a1…6373 35 text/plain draft.txt <erased by event 4>
$ previously blob get b00c29a1…6373 --output draft-copy.txt
blob b00c29a1d42316f16fd5ef9c72ce82bc5c1dcf24ff1280e12bfe3d61e3846373 is erased (event 4)
[exit 1]
$ previously verify --blobs
chain intact, 2 blobs match
no anchor given: …
$ previously redact event 1 --reason "the client withdrew consent to keep the kickoff minutes"
redacted by event 5
$ previously show 1
id=1 kind=observation
occurred_at=2026-10-05T02:58:45.665679+00:00
hash=57cf08a07e7efb0c91d1cfcd16a51ad9b92fabf299d1e9837c714976490b8544
payload=<erased by event 5>
  ¶1 <erased by event 5>
  blob 72f4f2c5a92ade61b696c0fe800b8af775fd2f3982b123693379e6ee7cd264f2 <erased by event 5>
$ previously verify --blobs
chain intact, 2 blobs match
no anchor given: …
$ previously redact event 1 --reason "the client withdrew consent to keep the kickoff minutes"
already redacted by event 5
$ aws … s3 ls s3://previously-blobs
[exit 0, empty: both blobs deleted]
```
The pages carry the full lines; the `…` here only shortens this message.

### Second short session: object metadata and a wrong identity

This session ran against the same containers, with the settings recovered from them and not logged:
```
$ previously append --source email --external-id 2026-10-05-agenda@example.org --text "The agenda is attached." --attach agenda.txt
6
$ aws --endpoint-url "$PREVIOUSLY_BLOB_ENDPOINT" s3api head-object --bucket $PREVIOUSLY_BLOB_BUCKET --key 109d441a2425851023028341d7ce024fa010d2dfe1d89a49a543c3f8c74aacc9
{ "AcceptRanges": "bytes", "LastModified": "2026-10-05T03:01:23+00:00", "ContentLength": 266, "ETag": "\"c0faf964bd63fecfe796f41c6ed3ccb0\"", "ContentType": "application/octet-stream", "Metadata": { "key-id": "age18q27nlpyfjrmftuusq6dtdgl8nmqqnwduq63fs5ly5ns7wjsqpwsuf2y4l" } }
$ age -d -i identity.txt -o content2 blob.age        (identity.txt = the OLD key)
age: error: no identity matched any of the recipients
age: report unexpected or unhelpful errors at https://filippo.io/age/report
[exit 1]
```

### Measurement for `erasure.md`
```
$ previously append --source note --external-id forged-1 --text "A note somebody will null by hand."
7
$ docker exec previously psql -U previously -c "UPDATE event SET payload = NULL, payload_salt = NULL WHERE id = 7"
UPDATE 1
$ previously verify
FINDING 7: payload is erased without a redaction
[exit 1]
```

### Clean-up

Both commands from `run-a-blob-store-on-your-machine.md` were run as written:
```
$ docker rm -f -v previously-blobs
previously-blobs
$ docker network rm previously-blobs
previously-blobs
```

### Final `uv run pytest`, typed into the tutorial without its `rootdir:` line
```
platform linux -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0
Using --randomly-seed=2908823063
configfile: pyproject.toml / testpaths: tests
plugins: randomly-5.0.0, platformdirs-4.12.2, cov-7.1.0, hypothesis-6.168.3
collected 606 items
(30 per-file lines, typed in full on the page)
======================== 606 passed in 72.97s (0:01:12) ========================
```

## Commands on the pages that were not run, or not run as shown
- **`attach-and-fetch-a-file`:** `PREVIOUSLY_BLOB_SECRET_KEY=YOUR-SECRET` and `PREVIOUSLY_BLOB_IDENTITIES=/path/to/identities` are placeholders. In the run they were the generated secret and `$PWD/identities`.
- **`erase-something`:**
  - The `blob … stays in the store: event 7 still uses it` notice is quoted from the reference and introduced as "in this form"; no run produced it.
  - The `already redacted by event 5` rerun followed a completed erasure, not an exit-2 failure. The reference says the output is the same.
- **`run-a-blob-store-on-your-machine`:** "If it prints a `Status`, delete the bucket" is an instruction I did not exercise.
- **`restore-from-a-backup`:** I performed no restore. "Once every erasure is repeated, no `missing` finding is left" follows from the rule in `cli.md`, not from a run.
- **`keep-the-blob-key-safe`:** the creation block no longer shows `ls -l`, because that output named my user and locale.

## Every page I wrote or changed

### New guides
- **`run-a-blob-store-on-your-machine.md`:**
  - starts RustFS 1.0.1 on a Docker network and creates the bucket with the **AWS CLI** in its own container (`amazon/aws-cli:2.37.9`, `s3 mb`), adding that any S3 client does the same job;
  - checks versioning and object lock, both measured;
  - says this is the test server and not the one for operation;
  - removes the server with `docker rm -f -v` and `docker network rm`.
- **`keep-the-blob-key-safe.md`:**
  - one warning only: losing the key loses every blob sealed to it, for good;
  - the key steps: create the key with `age-keygen`, name the file after its recipient, set the two variables;
  - says which command needs which half of the key;
  - states, without naming a platform, what must be true of the backup;
  - a rehearsal in five steps: fetch with any S3 tool, open with `age -d -i`, check that `sha256sum` equals the address, delete the files;
  - the failure case, with the real `age` error and the object's `key-id` metadata;
  - changing the key.
- **`attach-and-fetch-a-file.md`:** the seven variables, `append --attach`, `show`, `blob get`.
- **`erase-something.md`:**
  - how to choose the target, and why `--reason` must not contain what is erased;
  - which settings `redact` needs;
  - the three forms, each followed by `show`, plus `blob get` and `verify --blobs` as checks;
  - exit code 2 means "run the same command again";
  - what an erasure doesn't reach: backups until their retention ends, and restores, with a pointer to the erasure page.
- **`index.md`:** the four new entries.

### Existing guides
- **`verify-the-chain.md`:** a new nightly section with `verify --anchors anchors.txt --blobs`, whose output is measured.
- **`restore-from-a-backup.md`:**
  - a new section: the blob store doesn't go back with the database, so run `verify --blobs`;
  - a `missing` blob is, as a rule, one deleted by an erasure after the restore point;
  - erasures since that point have to be repeated, and the log can't say which they were, so keep a record outside the database;
  - an object uploaded after the restore point is reported by nothing;
  - no admonition added (the page keeps its one).
- **`rebuild-a-projection.md`:** version 2 made the page false. Its snippet showed `version: int = 2` as the *raised* version, but 2 is now the chronicle's current one; it now shows `version: int = 3`, as current plus one. It also says that `redact` catches the projections up and prints the `rebuilt:` line.

### Explanations
- **`backup-encryption.md`:**
  - AES-GCM is gone: there are two keys, the `age` identity for the blobs and the passphrase for the backups, and neither may lie where its data lies;
  - "Today both arrive through ESO" became "in the operation this design plans";
  - a new section: the backup retention is part of what an erasure promises.
- **`silent-losses.md`:** one sentence: a tombstone without a redaction is now a finding.
- **`erasure.md` and `blobs.md`:** see the handed-over sentences and the further fixes below.
- **`concurrency.md`:** see the handed-over sentences.

### README, tutorial, design records
- **`README.md`:**
  - stage 1c in the state;
  - "each unit with a salted digest of its own";
  - new bullets for blobs, erasure and `verify --blobs`;
  - **ten commands**, counted from `previously --help`;
  - "migrations" in the plural;
  - "no erasure" removed;
  - two sentences on what an erasure doesn't achieve, with a link to the erasure page;
  - the specifications table now says "six" and has the stage 1c row.
- **Tutorial:**
  - retyped from the run above, with four migrations;
  - the note now says a random salt feeds the hash as well;
  - one sentence under *Next steps*: no blobs, so no second service, with a pointer to `attach-and-fetch-a-file`;
  - the test block typed last.
- **`design-records.md`:**
  - six records; the sixth froze on 2026-10-05;
  - its reasoning lives in the `erasure` and `blobs` pages and the `hash-version-2` section of the hash chain page, which is a section, not a page;
  - the reference pages, the four guides and the map are named;
  - the paragraph-sign measurement is repeated (below).

## Handed-over sentences
1. **`README.md`, "no erasure":** removed, as described above.
2. **`backup-encryption.md`, AES-GCM:** replaced, as described above.
3. **`redact.py`, the comment in `redact_event` (comment only):**
   - "The blob is kept for it" now holds only if that event commits before `_blobs_after` reads the register again.
   - If it commits later, the erasure deletes the blob — the race that `{ref}`concurrency`` names.
   - The later locking now holds for `redact event` and `redact blob` only; `redact units` "locks only its target, and erases no reference".
4. **`erasure.md`, the two restore sentences:**
   - "reports as missing every blob that an erasure since that point deleted and that an event of the restored log names";
   - "A blob attached after that point and erased since is named by no event of the restored log, and neither is an object uploaded after that point for a content no restored event names; nothing reports either".
5. **`concurrency.md`:**
   - The lock is now described by form: the row of the target event for `redact event` and `redact units`; for `redact blob`, whose target has no row, the rows of the events that use it.
   - The lock set now reads: "For `redact units` the set is its target event, for `redact event` its target event and every event that uses one of that event's blobs, and for `redact blob` exactly the events that use the blob."

Further sentences that were no longer true, now fixed:
- **`erasure.md`:**
  - "locks the row of its target" in the "covered" section;
  - the undated `FINDING 1` example, now my own measurement, `FINDING 7`, dated 2026-10-05;
  - "measured as `verify() -> []`" is now attributed to stage 1a;
  - a new paragraph on `append --text` and `redact units` (concern 1).
- **`blobs.md`:**
  - "That emergency path isn't measured yet" became my measurement: `age` 1.2.1 in a container, 2026-10-05;
  - the memory-test numbers now carry their date (2026-10-05, from the task 5 report);
  - the intro now names the last two sections.
- **Map:** "acht Kommandos" became "zehn".

## The map
- **Count**, with the command from `CLAUDE.md`: **72 before, 93 after**. Six entries were struck and 27 added.
- **Struck under *Erledigt*, with their commits:**
  - `hash_version` per row: `72a0044`, `4c078ad`;
  - erasure as an event: `a0377ba`, with the blob form in `a65d1cc`;
  - when to build erasure (A §13): `a0377ba`;
  - erasing a payload didn't take the units, and `p_source_stats`: `a0377ba`, `600f757`;
  - blobs, encryption, keys, the file-system adapter: `13d0d5e`, `9efb419`. Note: there is one S3 adapter instead (1c §1.1), and "no versioning" is documented, not checked;
  - `evidence` goes with the payload: decided, `a0377ba`.
- **Partly closed:** the subkind of an action now has a place, and `verify` knows a first rule per kind. Both halves are recorded under *Erledigt*; the remaining assertion halves stay open under *Feststellungen*, reworded.
- **Spec §12: counted 14 points there.**
  - 1 → Blobs und Speicher; 2 → Tilgung (merged with execution point 4); 3 → Betrieb.
  - 4 → Einwurf-Vertrag; 5 → Feststellungen; 6 → Tilgung; 7 → Betrieb; 8 → Einwurf-Vertrag.
  - 9 → Kette und Anker (merged with execution point 2); 10 → Blobs.
  - 11 → Betrieb (merged with execution point 9 and the §7 bucket).
  - 12 → Einwurf-Vertrag; 13 and 14 → Blobs.
- **The 15 execution points, each checked against the tree:**
  - 1 → Kette (`test_verify.py:1048`); 2 → merged.
  - 3 → Tilgung (`redact.py:114`); 4 → merged.
  - 5 → Projektionen (`cli.py:807`).
  - 6, 7 and 8 → Blobs (`_READ_TIMEOUT = 20`); 9 → merged.
  - 10 → Betrieb; 11 → Betrieb, updated with my container run, with the by-hand walk still open for acceptance.
  - 12 → Tore, measured: 73 s, `606 passed in 72.97s`.
  - 13, 14 and 15 → Tore.
- **One new point**, the `redact units` finding (concern 1) → Tilgung.
- **Nothing dropped.** With three merges: 14 + 15 − 3 + 1 = 27.
- ***Wo das Projekt steht*:** a 1c row "gebaut, zur Abnahme: Merge steht aus". Teilprojekt 1 is built and closes with that merge.
- ***Was als Nächstes kommt*:**
  - the pilot comes first;
  - its resting spec works around 1c in three places, as its own header says (`git show 9b493f0`): the throwaway pilot log (§1.1), the raw reference instead of raw bytes (§2.3), and attachments without content (§1, §3.4).
- **Legend:** gains **1c** and **P-1c**.

## The freeze
In `specs/2026-10-04-stufe-1c-blobs-und-tilgung.md`:
- the blockquote header copied verbatim from the anchor spec, dated "Stand 2026-10-05";
- the status line becomes "eingefroren am 2026-10-05; zuvor Entwurf, vom Betreuer am 2026-10-04 durchgesehen, Grundlage des Plans `…`";
- the §12 introduction becomes "Gepflegt, solange der Spec lebte; beim Einfrieren am 2026-10-05 gingen die Punkte in die Landkarte (`docs/superpowers/landkarte.md`), jeder unter die Einheit, zu der er gehört, und dort leben sie weiter. Die Liste hier ist der Stand dieses Tages."

Nothing else in it changed. The diff touches only these lines: +20, −4.

Design-records measurement:
- `grep -rn "§" src tests migrations | grep -v "frozen design record"` prints nothing.
- The 15 paragraph-sign lines sit in the same 7 files with the same per-file counts as at the base `7cfe686`.

`CLAUDE.md` is untouched.

## Gates, final lines (each run on its own, on `789533e`)
- `ruff check`: All checks passed!
- `ruff format --check`: 69 files already formatted
- `pyright`: 0 errors, 0 warnings, 0 informations
- `lint-imports`: Contracts: 6 kept, 0 broken.
- `pytest --cov`: 606 passed in 72.58s (0:01:12), coverage 98.35%
- `make -C docs html`: build succeeded.
- `make -C docs vale`: ✔ 0 errors, 0 warnings and 0 suggestions in 28 files.
- `make -C docs linkcheck`: build succeeded, exit 0, nothing broken.

## Self-review
- **Secrets:** none on any page. Pages show recipients (public) and `AGE-SECRET-KEY-1…` only. The bucket secret was generated at run time and never printed. The keys are deleted.
- **Reference:** every command behaved as `cli.md` says; no deviation found.
- **Working tree:** clean; nothing foreign in it.
