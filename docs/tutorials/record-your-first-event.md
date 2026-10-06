(first-event-tutorial)=

# Record your first event

In this tutorial, we will record our first event in Previously, read it back from the log, check that the chain holds, pin its tip outside the database, build the two derived views, read the chronicle and the counts per source, and prove all of it with the project's own test suite.
Every command below is real: it was typed in a fresh checkout, against a real PostgreSQL 17 in a container like the one below.
No output below names a directory, so nothing here depends on where you put yours.

## Prerequisites

- **Python 3.14**, and **[uv](https://docs.astral.sh/uv/)**, which fetches that version of Python itself if the machine doesn't have it.
- **PostgreSQL 17** to append to.
- **Docker**, for the test suite at the end: the tests start their own PostgreSQL container and their own S3 server, so they never touch the database below.

Start a trial database if you don't already have one running:

```shell
docker run -d --name previously -p 5432:5432 \
    -e POSTGRES_USER=previously \
    -e POSTGRES_PASSWORD=previously \
    -e POSTGRES_DB=previously \
    postgres:17
```

## Install the dependencies

Clone the repository, then install it with every extra: the test suite and the documentation toolchain both need packages a plain install leaves out.

```console
$ uv sync --all-extras
Using CPython 3.14.3
Creating virtual environment at: .venv
Resolved 109 packages in 0.74ms
Prepared 1 package in 566ms
Installed 106 packages in 192ms
```

uv then lists every one of the 106 packages it installed.
This page leaves that list out, and the two lines before `Prepared` in which uv builds Previously itself, because they name the directory of your checkout, and a warning that uv can't link its files from its cache, which it prints when its cache and your checkout lie on different file systems.

## Point the tools at the database

Every command of the command line reads the database from one environment variable.

```shell
export PREVIOUSLY_DSN=postgresql+psycopg://previously:previously@localhost:5432/previously
```

The `+psycopg` names the driver.
Without it, `postgresql://` reaches the same one, and the tutorial keeps it so that you can see which driver talks to the database.

## Create the schema

```console
$ uv run previously migrate
migrated: (empty) -> 0005_watermark
```

Notice that the line names two revisions: where the database came from, `(empty)`, and where it stands now, `0005_watermark`, the fifth.
Five revisions ran to bring it there.
The first one brings the log, its units, and the idempotency key.
The second one brings three more tables: one for each derived view, and one that records how far each view has read.
The third brings hash format 2, in which every event gets a salt of its own, and our event is written in it; the fourth prepares the log for attached files, and the fifth adds a table that records how far each source has been read; this tutorial uses neither.

## Submit your first event

`append` prints exactly one line: the new event's `id`.

```console
$ uv run previously append \
    --source email \
    --external-id 2026-10-03-kickoff@example.org \
    --text "The client approved the new homepage design.

Next milestone: content migration starts Monday."
1
```

Notice that the id is `1`.
This is the first event in the chain, so there's no predecessor to link to.

## Look at the log

```console
$ uv run previously log
1	2026-10-05T18:31:07.449934+00:00	observation	ac286d534003
```

Notice that the chain now has one event.
Each line carries the event's `id`, when it occurred, its kind, and the first twelve characters of its hash.

## Check the chain

```console
$ uv run previously verify
chain intact
no anchor given: verify attests that the log is unchanged, not that it is complete; see `previously anchor`
```

`verify` walks every event, recomputing each hash and checking it against its predecessor.
It found nothing wrong, so its first line says `chain intact`.
Notice that a second line follows, and that it names a command we haven't run yet.
That line goes to standard error, and the terminal shows it right below the first one.

## Pin the tip

Let's run that command, and save what it prints to a file.
Then we check the chain again, this time against that file.

```console
$ uv run previously anchor > anchors.txt
$ uv run previously verify --anchors anchors.txt
chain intact, 1 anchor holds
```

Notice that the first line is now a different one: it counts the anchor it checked.
Notice also that the second line is gone.
This `anchors.txt` is this tutorial's alone, so delete it from your clone once you finish; {ref}`verify-the-chain` shows where a real one has to live.

## Look at the event in full

```console
$ uv run previously show 1
id=1 kind=observation
occurred_at=2026-10-05T18:31:07.449934+00:00
hash=ac286d53400316ad869450ea6189a7e9c4788cb1bd5602c850cfb9f58d6c8f8d
evidence=recollection
payload={"evidence": "recollection"}
  ¶1 The client approved the new homepage design.
  ¶2 Next milestone: content migration starts Monday.
```

Notice that the text split into two units at the blank line, numbered `¶1` and `¶2`, and that it stands in those units alone: the payload holds the kind of evidence and nothing else.
Notice also `evidence=recollection`: the command above didn't pass `--evidence`, and `recollection` is what it defaults to.

:::{note}
The hash and the timestamps on your screen won't match the ones above, here or in any block below.
`recorded_at`—the moment you submitted the event—feeds the hash, and so does a random salt drawn for the event, so the same text submitted twice produces two different events, and therefore two different hashes.
Running this tutorial twice, or on two different machines, gives two different hashes, both correct.
:::

## Build the derived views

The chronicle and the counts per source are derived from the log, and they start out empty.
One command fills them both.

```console
$ uv run previously project
chronicle       built: 1 event, up_to_id 1
source-stats    built: 1 event, up_to_id 1
```

Notice that both lines say `built`: nothing existed yet, so the worker built each view from the log, starting at the first event.
Run the same command a second time.

```console
$ uv run previously project
chronicle       up to date, up_to_id 1
source-stats    up to date, up_to_id 1
```

Notice that both lines now say `up to date`.
`up_to_id 1` is how far each view has read, and the log hasn't grown since.
There was nothing left to project.

## Read the chronicle

```console
$ uv run previously chronicle
1	1	2026-10-05T18:31:07.449934+00:00	email	2026-10-03-kickoff@example.org	The client approved the new homepage design.
1	2	2026-10-05T18:31:07.449934+00:00	email	2026-10-03-kickoff@example.org	Next milestone: content migration starts Monday.
```

Notice that each line is one unit, and that each one carries `email` and the message identifier we passed to `append`.
That source attribution is what makes this a chronicle and not a copy of `log`.

## Count per source

```console
$ uv run previously stats
email	1	2	2026-10-05T18:31:07.449934+00:00	2026-10-05T18:31:07.449934+00:00
```

Notice that `email` stands at one event and two units, and that the two timestamps are the same moment: the log holds one event, so the first one seen and the last one seen are that event.

## Run the test suite

The test suite needs no `PREVIOUSLY_DSN`.
It raises its own PostgreSQL container, a RustFS container as the S3 server for the blob tests, and a GreenMail container as the IMAP server for the mail tests, and never touches the database above.

```console
$ uv run pytest
============================= test session starts ==============================
platform linux -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0
Using --randomly-seed=1437899426
configfile: pyproject.toml
testpaths: tests
plugins: cov-7.1.0, randomly-5.0.0, hypothesis-6.168.3, platformdirs-4.12.2
collected 1026 items

tests/test_watermark.py ........                                         [  0%]
tests/test_projection_derive.py ...........                              [  1%]
tests/test_migration_0003.py ..                                          [  2%]
tests/test_projection_worker.py ....................                     [  3%]
tests/test_docs_typed_output.py .                                        [  4%]
tests/test_blob.py ...................                                   [  5%]
tests/test_keys.py ..............                                        [  7%]
tests/test_verify.py ................................................... [ 12%]
.............................                                            [ 15%]
tests/test_canonical.py ...............                                  [ 16%]
tests/test_schema.py ...................                                 [ 18%]
tests/test_docs_references.py .......                                    [ 19%]
tests/test_storage.py ...........................................        [ 23%]
tests/test_identity.py ...                                               [ 23%]
tests/test_wheel.py .                                                    [ 23%]
tests/test_imap.py ................                                      [ 25%]
tests/test_docs_build.py ......                                          [ 25%]
tests/test_rows.py ......                                                [ 26%]
tests/test_anchor.py .............                                       [ 27%]
tests/test_sealing.py .....................                              [ 29%]
tests/test_cli.py ...................................................... [ 34%]
........................................................................ [ 42%]
........................................................................ [ 49%]
........................................................................ [ 56%]
.....................                                                    [ 58%]
tests/test_redact.py .......................................             [ 61%]
tests/test_chain.py ...............................                      [ 64%]
tests/test_projection_store.py ..........                                [ 65%]
tests/test_properties.py ..........                                      [ 66%]
tests/test_migrate.py ....................                               [ 68%]
tests/test_migration_0004.py .                                           [ 68%]
tests/test_migration_0005.py .                                           [ 69%]
tests/test_s3.py ....................                                    [ 70%]
tests/test_redaction.py ..........................                       [ 73%]
tests/test_mail.py ..................................................... [ 78%]
........................................................................ [ 85%]
...................                                                      [ 87%]
tests/test_migrations_dsn.py ...                                         [ 87%]
tests/test_ingest.py ...............                                     [ 89%]
tests/test_contracts.py .......                                          [ 89%]
tests/test_hashing.py ........................................           [ 93%]
tests/test_units.py .............                                        [ 95%]
tests/test_append.py ..................................................  [100%]

======================= 1026 passed in 179.78s (0:02:59) =======================
```

`pytest-randomly` reshuffles the file order on every run and prints its seed, so a hidden dependency between two tests surfaces instead of staying hidden.
Your run prints one line this page leaves out, a `rootdir:` naming your own checkout.

## Next steps

You have now recorded your first event, confirmed the chain is intact, pinned its tip, built the two derived views, read the chronicle and the counts per source, and proven all of it with the project's own test suite.
For the full command reference, see {ref}`cli-reference`.
For why `log` and `chronicle` are two commands, see {ref}`projections`.
For exactly what goes into the hash you saw above, see {ref}`hash-format`.
For what the anchor in `anchors.txt` protects, and what it doesn't, see {ref}`external-anchor`.
This tutorial attaches no file to an event, so that it runs without a second service beside PostgreSQL; to attach one, see {ref}`attach-and-fetch-a-file`.
