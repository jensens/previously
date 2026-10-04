(first-event-tutorial)=

# Record your first event

In this tutorial, we will record our first event in Previously, look at the chronicle it produces, check that the chain holds, and prove both with the project's own test suite.
Every command below is real: it was typed against a real PostgreSQL 17, in a fresh checkout at `/tmp/previously-task3-fresh`.
No output below names a directory, so nothing here depends on where you put yours.

## Prerequisites

- **Python 3.14**, and **[uv](https://docs.astral.sh/uv/)**, which fetches that version of Python itself if the machine doesn't have it.
- **PostgreSQL 17** to append to.
- **Docker**, for the test suite at the end: the tests start their own PostgreSQL container, so they never touch the database below.

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
```

Notice that there's exactly one upgrade step.
Stage 1a's whole schema—the log, its units, and the idempotency key—lives in that one migration.

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

## Look at the chronicle

```console
$ uv run previously log
1	2026-10-03T15:41:19.888666+00:00	observation	495362ef39c9
```

Notice that the chain now has one event.
Each line carries the event's `id`, when it occurred, its kind, and the first twelve characters of its hash.

## Check the chain

```console
$ uv run previously verify
chain intact
```

`verify` walks every event, recomputing each hash and checking it against its predecessor.
It found nothing wrong, so it printed exactly that one line.

## Look at the event in full

```console
$ uv run previously show 1
id=1 kind=observation
occurred_at=2026-10-03T15:41:19.888666+00:00
hash=495362ef39c9af8358eaee83acc956d4813464cdd07057bd38c44680e3410dcc
evidence=recollection
payload={"evidence": "recollection", "text": "The client approved the new homepage design.\n\nNext milestone: content migration starts Monday."}
  ¶1 The client approved the new homepage design.
  ¶2 Next milestone: content migration starts Monday.
```

Notice that the text split into two units at the blank line, numbered `¶1` and `¶2`.
Notice also `evidence=recollection`: the command above didn't pass `--evidence`, and `recollection` is what it defaults to.

:::{note}
The hash on your screen won't match the one above.
`recorded_at`—the moment you submitted the event—feeds the hash, so the same text submitted at a different time produces a different event, and therefore a different hash.
Running this tutorial twice, or on two different machines, gives two different hashes, both correct.
:::

## Run the test suite

The test suite needs no `PREVIOUSLY_DSN`.
It raises its own PostgreSQL container and never touches the database above.

```console
$ uv run pytest
============================= test session starts ==============================
platform linux -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0
Using --randomly-seed=3130907343
configfile: pyproject.toml
testpaths: tests
plugins: hypothesis-6.168.3, cov-7.1.0, randomly-5.0.0, platformdirs-4.12.2
collected 202 items

tests/test_schema.py .............                                       [  6%]
tests/test_migrations_dsn.py ...                                         [  7%]
tests/test_verify.py .................                                   [ 16%]
tests/test_hashing.py ........................                           [ 28%]
tests/test_rows.py ....                                                  [ 30%]
tests/test_canonical.py ...............                                  [ 37%]
tests/test_docs_references.py .....                                      [ 40%]
tests/test_append.py ..............................                      [ 54%]
tests/test_storage.py ..........................                         [ 67%]
tests/test_cli.py ..........................                             [ 80%]
tests/test_projection_store.py ........                                  [ 84%]
tests/test_units.py .............                                        [ 91%]
tests/test_docs_build.py ......                                          [ 94%]
tests/test_contracts.py ..                                               [ 95%]
tests/test_docs_typed_output.py .                                        [ 95%]
tests/test_properties.py .........                                       [100%]

============================= 202 passed in 18.69s =============================
```

`pytest-randomly` reshuffles the file order on every run and prints its seed, so a hidden dependency between two tests surfaces instead of staying hidden.
Your run prints one line this page leaves out, a `rootdir:` naming your own checkout.

## Next steps

You have now recorded your first event, confirmed the chain is intact, and proven both with the project's own test suite.
For the full command reference, see {ref}`cli-reference`.
For exactly what goes into the hash you saw above, see {ref}`hash-format`.
