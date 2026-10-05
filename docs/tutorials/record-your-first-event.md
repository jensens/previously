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
Resolved 101 packages in 0.98ms
Prepared 1 package in 331ms
Installed 98 packages in 174ms
```

uv then lists every one of the 98 packages it installed.
This page leaves that list out, and the two lines before `Prepared` in which uv builds Previously itself, because they name the directory of your checkout, and a warning that uv can't link its files from its cache, which it prints when its cache and your checkout lie on different file systems.

## Point the tools at the database

Both the command line and the Alembic migrations read the same environment variable.

```shell
export PREVIOUSLY_DSN=postgresql+psycopg://previously:previously@localhost:5432/previously
```

The `+psycopg` belongs in there.
It names the driver, and without it SQLAlchemy reaches for one that isn't installed here.

## Create the schema

```console
$ uv run alembic upgrade head
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_log, Log, units, idempotency key
INFO  [alembic.runtime.migration] Running upgrade 0001_log -> 0002_projections, Projections: state, chronicle, source statistics
INFO  [alembic.runtime.migration] Running upgrade 0002_projections -> 0003_hash_version_2, Hash format version 2: version, salts and unit digests
INFO  [alembic.runtime.migration] Running upgrade 0003_hash_version_2 -> 0004_event_blob, The blob register: which event names which blob
```

Notice that there are four upgrade steps.
The first one brings the log, its units, and the idempotency key.
The second one brings three more tables: one for each derived view, and one that records how far each view has read.
The third brings hash format 2, in which every event gets a salt of its own, and our event is written in it; the fourth prepares the log for attached files, which this tutorial doesn't use.

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
1	2026-10-05T08:53:13.103557+00:00	observation	c675a31e2500
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
occurred_at=2026-10-05T08:53:13.103557+00:00
hash=c675a31e25000bc9768a9fa0a08f3467e247667a303c0c43f1af7eaf2c237bc3
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
1	1	2026-10-05T08:53:13.103557+00:00	email	2026-10-03-kickoff@example.org	The client approved the new homepage design.
1	2	2026-10-05T08:53:13.103557+00:00	email	2026-10-03-kickoff@example.org	Next milestone: content migration starts Monday.
```

Notice that each line is one unit, and that each one carries `email` and the message identifier we passed to `append`.
That source attribution is what makes this a chronicle and not a copy of `log`.

## Count per source

```console
$ uv run previously stats
email	1	2	2026-10-05T08:53:13.103557+00:00	2026-10-05T08:53:13.103557+00:00
```

Notice that `email` stands at one event and two units, and that the two timestamps are the same moment: the log holds one event, so the first one seen and the last one seen are that event.

## Run the test suite

The test suite needs no `PREVIOUSLY_DSN`.
It raises its own PostgreSQL container, and a RustFS container as the S3 server for the blob tests, and never touches the database above.

```console
$ uv run pytest
============================= test session starts ==============================
platform linux -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0
Using --randomly-seed=245583016
configfile: pyproject.toml
testpaths: tests
plugins: cov-7.1.0, randomly-5.0.0, platformdirs-4.12.2, hypothesis-6.168.3
collected 662 items

tests/test_properties.py ..........                                      [  1%]
tests/test_sealing.py .....................                              [  4%]
tests/test_redact.py .......................................             [ 10%]
tests/test_migrate.py .............                                      [ 12%]
tests/test_docs_references.py .....                                      [ 13%]
tests/test_rows.py ......                                                [ 14%]
tests/test_anchor.py .............                                       [ 16%]
tests/test_docs_build.py ......                                          [ 17%]
tests/test_units.py .............                                        [ 19%]
tests/test_canonical.py ...............                                  [ 21%]
tests/test_projection_worker.py ....................                     [ 24%]
tests/test_append.py ........................................            [ 30%]
tests/test_docs_typed_output.py .                                        [ 30%]
tests/test_migration_0003.py ..                                          [ 30%]
tests/test_projection_derive.py ...........                              [ 32%]
tests/test_chain.py ...............................                      [ 37%]
tests/test_hashing.py ........................................           [ 43%]
tests/test_blob.py ...................                                   [ 46%]
tests/test_keys.py ..............                                        [ 48%]
tests/test_migrations_dsn.py ...                                         [ 48%]
tests/test_cli.py ...................................................... [ 56%]
........................................................................ [ 67%]
............                                                             [ 69%]
tests/test_wheel.py .                                                    [ 69%]
tests/test_migration_0004.py .                                           [ 69%]
tests/test_redaction.py ..........................                       [ 73%]
tests/test_projection_store.py ..........                                [ 75%]
tests/test_contracts.py ....                                             [ 75%]
tests/test_schema.py ..................                                  [ 78%]
tests/test_verify.py ................................................... [ 86%]
.............................                                            [ 90%]
tests/test_storage.py ..........................................         [ 96%]
tests/test_s3.py ....................                                    [100%]

======================= 662 passed in 103.45s (0:01:43) ========================
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
