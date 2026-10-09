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
Resolved 110 packages in 0.69ms
Prepared 1 package in 457ms
Installed 107 packages in 202ms
```

uv then lists every one of the 107 packages it installed.
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
1	2026-10-06T13:57:26.741708+00:00	observation	0cea8ec261a5
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
occurred_at=2026-10-06T13:57:26.741708+00:00
hash=0cea8ec261a5016005524ace920f87441038256d8006774000755d28daf8e191
evidence=recollection
payload={"artifact_hash": "dc61469da1b794f30b8e795e72b06b98e6a5ad04bb46bac936d98c3ac3888b01", "evidence": "recollection"}
  ¶1 The client approved the new homepage design.
  ¶2 Next milestone: content migration starts Monday.
```

Notice that the text split into two units at the blank line, numbered `¶1` and `¶2`, and that it stands in those units alone: the payload holds a hash of the text, `artifact_hash`, and the kind of evidence, and none of the words.
Notice also `evidence=recollection`: the command above didn't pass `--evidence`, and `recollection` is what it defaults to.

:::{note}
The hash and the timestamps on your screen won't match the ones above, here or in any block below.
`recorded_at`—the moment you submitted the event—feeds the hash, and so does a random salt drawn for the event, so the same text submitted twice produces two different events, and therefore two different hashes.
Running this tutorial twice, or on two different machines, gives two different hashes, both correct.
Only `artifact_hash` comes out the same as above, because it's computed from the text alone.
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
1	1	2026-10-06T13:57:26.741708+00:00	email	2026-10-03-kickoff@example.org	The client approved the new homepage design.
1	2	2026-10-06T13:57:26.741708+00:00	email	2026-10-03-kickoff@example.org	Next milestone: content migration starts Monday.
```

Notice that each line is one unit, and that each one carries `email` and the message identifier we passed to `append`.
That source attribution is what makes this a chronicle and not a copy of `log`.

## Count per source

```console
$ uv run previously stats
email	1	2	2026-10-06T13:57:26.741708+00:00	2026-10-06T13:57:26.741708+00:00
```

Notice that `email` stands at one event and two units, and that the two timestamps are the same moment: the log holds one event, so the first one seen and the last one seen are that event.

## Run the test suite

The test suite needs no `PREVIOUSLY_DSN`.
It raises its own PostgreSQL container, a RustFS container as the S3 server for the blob tests, and a GreenMail container as the IMAP server for the mail tests, and never touches the database above.

```console
$ uv run pytest
============================= test session starts ==============================
platform linux -- Python 3.14.8, pytest-9.1.1, pluggy-1.6.0
Using --randomly-seed=2321377033
configfile: pyproject.toml
testpaths: tests
plugins: cov-7.1.0, randomly-5.0.0, hypothesis-6.168.3, platformdirs-4.12.2, anyio-4.15.1
collected 1249 items

tests/test_migration_0003.py ..                                          [  0%]
tests/test_contracts.py ...........                                      [  1%]
tests/test_sealing.py .....................                              [  2%]
tests/test_policy.py .............................                       [  5%]
tests/test_redaction.py ..........................                       [  7%]
tests/test_migrate.py ....................                               [  8%]
tests/test_schema.py ...................                                 [ 10%]
tests/test_wheel.py .                                                    [ 10%]
tests/test_keys.py ..............                                        [ 11%]
tests/test_blob.py ...................                                   [ 12%]
tests/test_verify.py ................................................... [ 17%]
................................                                         [ 19%]
tests/test_gate.py ..................................................... [ 23%]
........                                                                 [ 24%]
tests/test_cli.py ...................................................... [ 28%]
........................................................................ [ 34%]
........................................................................ [ 40%]
........................................................................ [ 46%]
........................................                                 [ 49%]
tests/test_hashing.py ........................................           [ 52%]
tests/test_projection_worker.py ....................                     [ 54%]
tests/test_docs_typed_output.py .                                        [ 54%]
tests/test_chain.py ...............................                      [ 56%]
tests/test_s3.py ....................                                    [ 58%]
tests/test_migration_0004.py .                                           [ 58%]
tests/test_anchor.py .............                                       [ 59%]
tests/test_canonical.py ...............                                  [ 60%]
tests/test_cascade.py ...............                                    [ 61%]
tests/test_projection_derive.py ...........                              [ 62%]
tests/test_identity.py ...                                               [ 62%]
tests/test_mail.py ..................................................... [ 67%]
........................................................................ [ 72%]
..................................                                       [ 75%]
tests/test_redact.py .......................................             [ 78%]
tests/test_action.py ....                                                [ 79%]
tests/test_migrations_dsn.py ...                                         [ 79%]
tests/test_units.py .............                                        [ 80%]
tests/test_projection_store.py ..........                                [ 81%]
tests/test_chronicle.py ..                                               [ 81%]
tests/test_decide.py ............................                        [ 83%]
tests/test_gate_adapters.py ......................                       [ 85%]
tests/test_properties.py ..........                                      [ 86%]
tests/test_docs_build.py ......                                          [ 86%]
tests/test_append.py ..................................................  [ 90%]
tests/test_watermark.py ........                                         [ 91%]
tests/test_docs_references.py ...........                                [ 92%]
tests/test_migration_0005.py .                                           [ 92%]
tests/test_rows.py ......                                                [ 92%]
tests/test_imap.py ................................                      [ 95%]
tests/test_storage.py ...........................................        [ 98%]
tests/test_ingest.py ................                                    [100%]

================================ tests coverage ================================
_______________ coverage: platform linux, python 3.14.8-final-0 ________________

Name                                                        Stmts   Miss  Cover   Missing
-----------------------------------------------------------------------------------------
src/previously/__init__.py                                      0      0   100%
src/previously/cli.py                                         769      8    99%   475, 953, 1321, 1327, 1330-1331, 1717-1718
src/previously/connectors/__init__.py                           0      0   100%
src/previously/connectors/imap.py                             180      9    95%   128, 146, 167, 199, 236, 269, 272, 277, 339
src/previously/contract/__init__.py                             0      0   100%
src/previously/contract/blobs.py                               21      0   100%
src/previously/contract/connector.py                            4      4     0%   12-34
src/previously/contract/rows.py                                27      0   100%
src/previously/contract/store.py                               32     32     0%   53-177
src/previously/contract/types.py                               31      0   100%
src/previously/core/__init__.py                                 0      0   100%
src/previously/core/action.py                                  37      0   100%
src/previously/core/anchor.py                                  30      0   100%
src/previously/core/append.py                                 129      1    99%   596
src/previously/core/blob.py                                    61      0   100%
src/previously/core/canonical.py                               41      0   100%
src/previously/core/chain.py                                   96      0   100%
src/previously/core/decide.py                                  85      0   100%
src/previously/core/errors.py                                  28      0   100%
src/previously/core/gaps.py                                    46      4    91%   43, 46, 64, 86
src/previously/core/hashing.py                                 57      0   100%
src/previously/core/identity.py                                 5      0   100%
src/previously/core/ingest.py                                 130      0   100%
src/previously/core/mail.py                                   354      4    99%   831-832, 909-912
src/previously/core/policy.py                                 269      6    98%   221, 342, 346, 355, 369, 373
src/previously/core/projection/__init__.py                      8      0   100%
src/previously/core/projection/chronicle.py                    44      0   100%
src/previously/core/projection/source_stats.py                 28      0   100%
src/previously/core/projection/worker.py                       55      0   100%
src/previously/core/redact.py                                 157      0   100%
src/previously/core/redaction.py                              113      0   100%
src/previously/core/sealing.py                                 92      2    98%   157, 194
src/previously/core/units.py                                   13      0   100%
src/previously/core/verify.py                                 331      0   100%
src/previously/gate/__init__.py                                 0      0   100%
src/previously/gate/adapters/__init__.py                       26      0   100%
src/previously/gate/adapters/anthropic.py                      25      0   100%
src/previously/gate/adapters/openai_compatible.py              23      0   100%
src/previously/gate/gate.py                                   119      1    99%   149
src/previously/gate/prices.py                                  56      1    98%   65
src/previously/gate/task.py                                    19      0   100%
src/previously/gate/tasks/__init__.py                           0      0   100%
src/previously/gate/tasks/mail_overview.py                      9      0   100%
src/previously/migrations/__init__.py                           0      0   100%
src/previously/migrations/dsn.py                               11      0   100%
src/previously/migrations/env.py                               30      4    87%   43-51, 100
src/previously/migrations/versions/0001_log.py                 19      3    84%   107-109
src/previously/migrations/versions/0002_projections.py         16      4    75%   62-65
src/previously/migrations/versions/0003_hash_version_2.py      31      0   100%
src/previously/migrations/versions/0004_event_blob.py          16      0   100%
src/previously/migrations/versions/0005_watermark.py           16      0   100%
src/previously/storage/__init__.py                              0      0   100%
src/previously/storage/errors.py                               13      0   100%
src/previously/storage/keys.py                                 28      0   100%
src/previously/storage/migrate.py                              53      1    98%   113
src/previously/storage/postgres.py                            270      0   100%
src/previously/storage/s3.py                                  108      0   100%
src/previously/storage/schema.py                               31      0   100%
-----------------------------------------------------------------------------------------
TOTAL                                                        4192     84    98%
Required test coverage of 90.0% reached. Total coverage: 98.00%
======================= 1249 passed in 190.75s (0:03:10) =======================
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
