# Previously

> *Previously, on Project …*

A tool that gathers courses of events, commitments and open points from many
channels, orders them and makes them provable — so that the question "how do
things stand here?" is answerable without looking into six mailboxes.

The name is the main view: the header and the chronicle of a project, every
line with its source attribution.

## State

**Stage 1a is built and runs: the append-only log with its hash chain.** Not a
product surface — a command line thin enough to get at the log by hand, so
that the stage is *runnable* and not merely described.

**What it does:**

- an **append-only event log** in PostgreSQL, every event hash-linked to its
  predecessor (SHA-256 over canonicalised JSON after RFC 8785)
- **appending** with idempotency over `(source, external_id)`, and without any
  prior lock: concurrent writers serialise on unique indexes, and the loser
  re-reads the tip and repeats
- **units** — plain text split at blank lines, numbered, covered by the hash
- **checking** (`verify`): for every existing row the payload, the units, the
  source attribution, the linkage to the predecessor, and a count
  reconciliation that proves no row lay outside the check
- the four commands `append`, `log`, `verify` and `show`
- the schema as an Alembic migration

**What it does not do:** no projections (header, chronicle as a view — stage
1b), no connectors for e-mail or issue trackers (stage 2), no MCP interface,
no language model and therefore no assertions or actions, no search, no
erasure, no user administration and no network interface.

And one limit that is not a gap but the nature of the thing: a hash chain
without an **outer anchor** bears witness that what stands in the log is
unchanged — not that it is complete. Deleting the tip, appending a
self-computed event or rewriting the whole chain leaves a result that is
consistent in itself. §11 of the stage 1a specification states which forgeries
are covered and which are not.

| Document | Content |
|---|---|
| [Design](docs/superpowers/specs/2026-10-01-previously-design.md) | Goal, guiding principles, core model, attribution, projections, release model, acceptance conditions |
| [Architecture](docs/superpowers/specs/2026-10-01-architektur.md) | Modules and boundaries, schema, connector contract, process model, MCP, tooling |
| [Stage 1a](docs/superpowers/specs/2026-10-02-stufe-1a-log.md) | Detailed specification of the append-only log with its hash chain |
| [CLAUDE.md](CLAUDE.md) | The working agreements: language, attribution, dependencies, the five gates |
| [DEPENDENCIES.md](DEPENDENCIES.md) | Every dependency with its purpose, the rejected alternative and the date it was last checked |
| [NOTIZEN.md](NOTIZEN.md) | The conversation log of how it came about, the discarded routes included |

## Getting started

The session below was typed out against a real PostgreSQL 17 in a fresh
checkout; the output is what actually came back. That checkout stood at
`/tmp/previously-fresh`, which is why the paths say so.

### 1. Prerequisites

- **Python 3.14.** Not a preference: the annotations in `core/canonical.py`
  and `core/hashing.py` rely on PEP 649, and an older version fails there.
- **[uv](https://docs.astral.sh/uv/)** — it fetches Python 3.14 itself if the
  machine has not got it.
- **PostgreSQL 15 or newer** for operation. `NULLS NOT DISTINCT` is not
  optional: it is what makes exactly one genesis event possible, instead of
  one per process.
- **Docker** for the tests — they run against a real PostgreSQL in a
  container, never against a mock.

A database for trying it out, if there is not one already:

```console
$ docker run -d --name previously -p 5432:5432 \
    -e POSTGRES_USER=previously \
    -e POSTGRES_PASSWORD=previously \
    -e POSTGRES_DB=previously \
    postgres:17
```

### 2. Install

```console
$ uv sync
Using CPython 3.14.3
Creating virtual environment at: .venv
Resolved 48 packages in 0.62ms
   Building previously @ file:///tmp/previously-fresh
Downloading sqlalchemy (4.4MiB)
Downloading psycopg-binary (5.0MiB)
 Downloaded sqlalchemy
 Downloaded psycopg-binary
      Built previously @ file:///tmp/previously-fresh
Prepared 8 packages in 817ms
Installed 8 packages in 1ms
 + alembic==1.20.0
 + mako==1.4.3
 + markupsafe==3.0.3
 + previously==0.1.dev110 (from file:///tmp/previously-fresh)
 + psycopg==3.3.6
 + psycopg-binary==3.3.6
 + sqlalchemy==2.1.2
 + typing-extensions==4.16.0
```

`uv sync` installs the **runtime** dependencies. The tests and the gates need
the extras as well; §6 below says so where it matters.

### 3. Name the database

One environment variable, used by the command line and by the migrations
alike:

```console
$ export PREVIOUSLY_DSN=postgresql+psycopg://previously:previously@localhost:5432/previously
```

The `+psycopg` belongs in there: it chooses the driver, and without it
SQLAlchemy reaches for one that is not installed here.

Forgetting the variable is not a riddle:

```console
$ uv run alembic upgrade head
  File "/tmp/previously-fresh/migrations/dsn.py", line 43, in resolve_dsn
    raise RuntimeError(
    ...<6 lines>...
    )
RuntimeError: No database URL found: neither is `sqlalchemy.url` set in
alembic.ini, nor is PREVIOUSLY_DSN set in the environment. Either `export
PREVIOUSLY_DSN=postgresql+psycopg://…` before the call, or programmatically
via `config.set_main_option("sqlalchemy.url", …)` before the migration run
(the way tests/conftest.py does it for the test container).
```

*(The traceback above the message is shortened here, and the message itself
comes on one long line — it is wrapped for reading.)*

### 4. Create the schema

```console
$ uv run alembic upgrade head
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_log, Log, units, idempotency key
```

### 5. A submission, a chronicle, a check, a display

`append` prints the identifier of the event. Blank lines split the text into
units:

```console
$ uv run previously append \
    --source email \
    --external-id 20261001T0900@example.org \
    --occurred-at 2026-10-01T09:00:00+02:00 \
    --evidence verbatim \
    --text "Price remains 1000 Euro.

Please confirm."
1
```

`--evidence` separates proof from report: `verbatim` is the wording as it
arrived, `recollection` — the default — is reported from memory. It goes into
the hash and cannot be supplied afterwards.

```console
$ uv run previously append --source cli --external-id note-1 \
    --text "Confirmed by telephone on the 2nd of October."
2
```

The same submission a second time yields the **same** identifier and no second
event — idempotency over `(source, external_id)`:

```console
$ uv run previously append --source cli --external-id note-1 \
    --text "Confirmed by telephone on the 2nd of October."
2
```

The chronicle: identifier, `occurred_at`, kind, and the first twelve
characters of the hash. `--occurred-at` was given for event 1 and defaulted to
the moment of submission for event 2:

```console
$ uv run previously log
1	2026-10-01T07:00:00+00:00	observation	f732f2a79ce7
2	2026-10-03T04:11:49.558241+00:00	observation	18da5b14174e
```

The check walks the whole chain in one transaction. Exit code **0** when
intact, **1** with findings — that is the interface for a cron run:

```console
$ uv run previously verify
chain intact
```

And one event in full — head, kind of evidence, payload and units:

```console
$ uv run previously show 1
id=1 kind=observation
occurred_at=2026-10-01T07:00:00+00:00
hash=f732f2a79ce75dec80dace65b069fbf1904be498f17ad80e894b49490fa29a1f
evidence=verbatim
payload={"evidence": "verbatim", "text": "Price remains 1000 Euro.\n\nPlease confirm."}
  ¶1 Price remains 1000 Euro.
  ¶2 Please confirm.
```

The kind of evidence is read back here, not only written: it stands
permanently in the hash and cannot be supplied after the fact, so a surface
that could set it but not show it would be the wrong half. After an erasure
the line reads `payload=<erased>` and there is no `evidence=` line — the
tombstone has neither.

The hash will come out differently on your machine, and that is deliberate:
`recorded_at` — the moment of submission — is part of the hashed range, so the
same text submitted at a different time is a different event. Reproducible is
the other direction: the same input *including* `recorded_at` always gives the
same hash, which is what the pinned test vector in `tests/test_hashing.py`
holds down.

### 6. The tests

They need the `test` and `dev` extras, which a plain `uv sync` does not
install — measured:

```console
$ uv run pytest
error: Failed to spawn: `pytest`
  Caused by: No such file or directory (os error 2)
```

So:

```console
$ uv sync --all-extras
Resolved 48 packages in 0.85ms
Prepared 37 packages in 866ms
Installed 37 packages in 31ms
$ uv run pytest
============================= test session starts ==============================
platform linux -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0
Using --randomly-seed=3132245745
rootdir: /tmp/previously-fresh
configfile: pyproject.toml
testpaths: tests
plugins: hypothesis-6.168.3, randomly-5.0.0, cov-7.1.0, platformdirs-4.12.2
collected 181 items

tests/test_append.py ..............................                      [ 16%]
tests/test_contracts.py ...                                              [ 18%]
tests/test_hashing.py ........................                           [ 31%]
tests/test_cli.py ..........................                             [ 45%]
tests/test_rows.py ....                                                  [ 48%]
tests/test_canonical.py ...............                                  [ 56%]
tests/test_units.py .............                                        [ 63%]
tests/test_verify.py .................                                   [ 72%]
tests/test_schema.py ...........                                         [ 79%]
tests/test_properties.py .........                                       [ 83%]
tests/test_storage.py ..........................                         [ 98%]
tests/test_migrations_dsn.py ...                                         [100%]

============================= 181 passed in 17.02s =============================
```

The order of the files differs from run to run: `pytest-randomly` shuffles it
and prints the seed, so a dependency between two tests comes to notice instead
of staying hidden.

*(The `Downloading …` lines and the 37 `+ package==version` lines of the
install are left out here.)*

The tests raise their own PostgreSQL container, so they need no
`PREVIOUSLY_DSN` and do not touch the database from step 3.

The five gates that everything has to pass before it counts as done stand in
[CLAUDE.md](CLAUDE.md); `.github/workflows/gates.yml` runs the same five on
every push and every pull request.

## The basic idea

An **append-only event log** is the single truth; every state is a projection
recomputable from it. Foreign systems such as project management tools or
issue trackers are at the same time an inbox **and** an output target, never a
source of truth — which keeps them replaceable.

Three kinds of event carry the whole: **observations** cannot be wrong, they
only claim that something arrived. **Assertions** can be wrong and are
overwritten, never deleted. **Actions** are evidenced, with the authority they
rest on. Only assertions come out of a language model.

The guiding principles stand in §3 of the design. The most important one:

> Autonomy arises through restriction, not through trust.

## Language

**Source files, documentation and configuration are English** — code, SQL,
identifiers, comments, docstrings, test names and strings such as error
messages, and likewise this file and `DEPENDENCIES.md`.

**German stays** for specification, plans and the working notes: they contain
more reasoning than description, and the reasoning is the actual content.

`CLAUDE.md` carries the binding wording, including the one exception that
matters — test data that feeds a hash is never translated. The glossary in §3
of the architecture is the binding mapping of the terms.

## What it is not

- **Not a surveillance tool.** Recordings of conversations presuppose consent,
  disclosure to third parties presupposes a covering agreement, and both are
  anchored in the model rather than in a policy.
- **Not SaaS.** Self-hosted, the data stays in-house.
- **Not an AI product.** The language model is replaceable trimming behind a
  single interface; the core is an event log with projections.

## Licence

[AGPL-3.0-or-later](LICENSE).

Affero deliberately: Previously is a server application, and the ordinary GPL
does not bite when somebody runs a modified version as a service without
handing out code.
