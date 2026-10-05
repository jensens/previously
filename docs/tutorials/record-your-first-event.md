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
Resolved 74 packages in 0.65ms
Installed 71 packages in 159ms
```

uv then lists every one of the 71 packages it installed.
This page leaves that list out.

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
```

Notice that there are two upgrade steps.
The first one brings the log, its units, and the idempotency key.
The second one brings three more tables: one for each derived view, and one that records how far each view has read.

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
1	2026-10-04T13:24:54.151385+00:00	observation	52a060a8734b
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
occurred_at=2026-10-04T13:24:54.151385+00:00
hash=52a060a8734ba42c073985683adce79da3ba550a9d26902a6f7a60fb451f9f17
evidence=recollection
payload={"evidence": "recollection", "text": "The client approved the new homepage design.\n\nNext milestone: content migration starts Monday."}
  ¶1 The client approved the new homepage design.
  ¶2 Next milestone: content migration starts Monday.
```

Notice that the text split into two units at the blank line, numbered `¶1` and `¶2`.
Notice also `evidence=recollection`: the command above didn't pass `--evidence`, and `recollection` is what it defaults to.

:::{note}
The hash and the timestamps on your screen won't match the ones above, here or in any block below.
`recorded_at`—the moment you submitted the event—feeds the hash, so the same text submitted at a different time produces a different event, and therefore a different hash.
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
1	1	2026-10-04T13:24:54.151385+00:00	email	2026-10-03-kickoff@example.org	The client approved the new homepage design.
1	2	2026-10-04T13:24:54.151385+00:00	email	2026-10-03-kickoff@example.org	Next milestone: content migration starts Monday.
```

Notice that each line is one unit, and that each one carries `email` and the message identifier we passed to `append`.
That source attribution is what makes this a chronicle and not a copy of `log`.

## Count per source

```console
$ uv run previously stats
email	1	2	2026-10-04T13:24:54.151385+00:00	2026-10-04T13:24:54.151385+00:00
```

Notice that `email` stands at one event and two units, and that the two timestamps are the same moment: the log holds one event, so the first one seen and the last one seen are that event.

## Run the test suite

The test suite needs no `PREVIOUSLY_DSN`.
It raises its own PostgreSQL container, and a RustFS container as the S3 server for the blob tests, and never touches the database above.

```console
$ uv run pytest
============================= test session starts ==============================
platform linux -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0
Using --randomly-seed=3038919282
configfile: pyproject.toml
testpaths: tests
plugins: randomly-5.0.0, platformdirs-4.12.2, cov-7.1.0, hypothesis-6.168.3
collected 468 items

tests/test_canonical.py ...............                                  [  3%]
tests/test_migrations_dsn.py ...                                         [  3%]
tests/test_docs_build.py ......                                          [  5%]
tests/test_storage.py ...................................                [ 12%]
tests/test_projection_derive.py ...........                              [ 14%]
tests/test_blob.py .............                                         [ 17%]
tests/test_keys.py ............                                          [ 20%]
tests/test_verify.py ................................................... [ 31%]
..............                                                           [ 34%]
tests/test_schema.py .................                                   [ 37%]
tests/test_properties.py ..........                                      [ 39%]
tests/test_projection_worker.py ................                         [ 43%]
tests/test_docs_typed_output.py .                                        [ 43%]
tests/test_redact.py ...................                                 [ 47%]
tests/test_redaction.py ..................                               [ 51%]
tests/test_docs_references.py .....                                      [ 52%]
tests/test_anchor.py .............                                       [ 55%]
tests/test_units.py .............                                        [ 58%]
tests/test_s3.py .................                                       [ 61%]
tests/test_contracts.py ....                                             [ 62%]
tests/test_sealing.py ..............                                     [ 65%]
tests/test_projection_store.py ..........                                [ 67%]
tests/test_hashing.py ........................................           [ 76%]
tests/test_append.py ...............................                     [ 82%]
tests/test_cli.py ...................................................... [ 94%]
............                                                             [ 97%]
tests/test_rows.py ......                                                [ 98%]
tests/test_chain.py .......                                              [ 99%]
tests/test_migration_0003.py .                                           [100%]

============================= 468 passed in 44.04s =============================
```

`pytest-randomly` reshuffles the file order on every run and prints its seed, so a hidden dependency between two tests surfaces instead of staying hidden.
Your run prints one line this page leaves out, a `rootdir:` naming your own checkout.

## Next steps

You have now recorded your first event, confirmed the chain is intact, pinned its tip, built the two derived views, read the chronicle and the counts per source, and proven all of it with the project's own test suite.
For the full command reference, see {ref}`cli-reference`.
For why `log` and `chronicle` are two commands, see {ref}`projections`.
For exactly what goes into the hash you saw above, see {ref}`hash-format`.
For what the anchor in `anchors.txt` protects, and what it doesn't, see {ref}`external-anchor`.
