# Previously

> *Previously, on Project …*

A tool that gathers courses of events, commitments and open points from many
channels, orders them and makes them provable — so that the question "how do
things stand here?" is answerable without looking into six mailboxes.

The name is the main view: the header and the chronicle of a project, every
line with its source attribution.

## State

**Stages 1a, 1b and 1c are built and run: the append-only log with its hash
chain, the projections derived from it, and blobs and erasure. A release
publishes a package on PyPI and an image on ghcr.io.** Not a product surface — a command line
thin enough to get at the log by hand, so that each stage is *runnable* and not
merely described.

**What it does:**

- an **append-only event log** in PostgreSQL, every event hash-linked to its
  predecessor (SHA-256 over canonicalised JSON after RFC 8785)
- **appending** with idempotency over `(source, external_id)`, and without any
  prior lock: concurrent writers serialise on unique indexes, and the loser
  re-reads the tip and repeats
- **units** — plain text split at blank lines, numbered, each with a salted
  digest of its own (hash format 2), covered by the hash
- **checking** (`verify`): for every existing row the payload, the units, the
  source attribution, the linkage to the predecessor, and a count
  reconciliation that proves no row lay outside the check
- **projections** (`project`) that are derivable from the log and disposable:
  `projection_state` records how far each one has got, and a raised derivation
  version empties its table and builds it again from the log
- **the chronicle** (`chronicle`) — one line per unit with its source
  attribution, in the order in which things happened rather than the order in
  which they were recorded
- **the per-source statistics** (`stats`): events, units, and the earliest and
  latest `occurred_at` per source
- **the external anchor** (`anchor`, `verify --anchors`): `anchor` prints the
  tip of an intact chain as one line `<id> <hash>`, to be kept where the
  database's writer cannot write; `verify --anchors` checks the log against
  such lines, so that up to the newest anchor nothing can go missing or be
  rewritten unseen
- **blobs** (`append --attach`, `blob get`): a file attached to an event is
  sealed in the `age` format before it leaves the process, stored in an S3
  bucket under the SHA-256 of its content, and named in the payload; `blob get`
  fetches it and writes it out only if it matches its address. Losing the
  identity that opens the blobs loses every blob sealed to it, for good:
  [How to keep the blob key safe](docs/how-to/keep-the-blob-key-safe.md)
  says how to back it up and rehearse the backup
- **erasure** (`redact`): an event, some of its units, or a blob, erased as an
  event of its own in the same chain, so that a tombstone without an order is
  a finding; every hash stays, the salt goes, the projections follow, and a
  blob leaves the store once no reference to it is left. An event written
  before stage 1c, in hash format 1, has no salt, so short erased content
  stays guessable from its digests; see
  [About erasure](docs/explanation/erasure.md)
- **checking the blobs** (`verify --blobs`): every blob that has to lie in
  the store is read, opened and held against its address, and every erased one
  has to be gone
- the eleven commands `migrate`, `append`, `redact`, `log`, `verify`,
  `anchor`, `show`, `blob`, `project`, `chronicle` and `stats`
- the schema as Alembic migrations inside the package, applied by
  `previously migrate`

**What it does not do:** no header — a header rests on assertions, and those
come out of the gate; no assignment of events to projects, so the chronicle is
the chronicle of the whole log and not of one project; no job queue — the
projection worker is a command, run when somebody runs it; no connectors for
e-mail or issue trackers (stage 2), no MCP interface, no language model and
therefore no assertions, and no action but the redaction; no search, no
user administration and no network interface.

And one limit that is not a gap but the nature of the thing: a hash chain by
itself bears witness that what stands in the log is unchanged — not that it is
complete. Deleting the tip, appending a self-computed event or rewriting the
whole chain leaves a result that is consistent in itself. An **external
anchor**, kept where the database's writer cannot write, adds completeness up
to the newest anchor: a deleted or rewritten event below it shows. What it
does not add is the interval since: a tip deleted above the newest anchor
shows nowhere, and a forged appended event shows only against an anchor taken
at a moment of rest, when nothing legitimate should have been written since.
[About the hash chain](docs/explanation/hash-chain.md) states which forgeries
are covered and which are not.

An erasure has a limit of the same kind: it takes content out of the log and
out of the bucket, not out of the backups taken before it, and a restore to an
earlier point brings it back. The address of a blob and the source key stay as
well, and an erasure of units leaves their wording in a payload that holds
it too, and says so when a string of the payload contains a unit's wording;
[About erasure](docs/explanation/erasure.md) says what an erasure does not
achieve and why.

## Install

Each release is a package on PyPI and a container image on ghcr.io, for
`linux/amd64` and `linux/arm64`. Until `1.0.0` every release is an alpha, so
ask `pip` for a pre-release, or name the version:

```shell
pip install --pre previously
```

The image runs `previously` as its entry point, and an alpha has one tag only,
its exact version — no `latest`:

```shell
docker run --rm ghcr.io/jensens/previously:0.1.0a1
```

Either way, Previously reads its settings from the environment, and
`previously migrate` creates or upgrades the schema before any other command
runs against a database.
[How to run Previously from its image](docs/how-to/run-the-image.md) shows the
image at work, and [How to cut a release](docs/how-to/cut-a-release.md) how a
release comes about.

## Documentation

The full documentation — tutorials, how-to guides, reference and explanation —
lives under `docs/`. Build it locally with `make -C docs html`, then open
`docs/_build/html/index.html`. Start with
[Record your first event](docs/tutorials/record-your-first-event.md): a
session typed out against a real PostgreSQL 17, from a fresh checkout to a
passing test suite.

The six specifications below are **frozen design records**, in German and
dated: they hold how and why a decision was taken, and the documentation under
`docs/` carries the reasoning that is maintained with the code. Where the two
disagree, the documentation wins. A new stage starts with a new German
specification, which freezes once its explanation pages stand — stage 1b is
the first one that went that way from the start.

| Document | Content |
|---|---|
| [Design](docs/superpowers/specs/2026-10-01-previously-design.md) | Frozen design record, 2026-10-03: goal, guiding principles, core model, attribution, projections, release model, acceptance conditions |
| [Architecture](docs/superpowers/specs/2026-10-01-architektur.md) | Frozen design record, 2026-10-03: modules and boundaries, schema, connector contract, process model, MCP, tooling |
| [Stage 1a](docs/superpowers/specs/2026-10-02-stufe-1a-log.md) | Frozen design record, 2026-10-03: detailed specification of the append-only log with its hash chain |
| [Stage 1b](docs/superpowers/specs/2026-10-04-stufe-1b-projektionen.md) | Frozen design record, 2026-10-04: detailed specification of the projections — the two derived tables, the worker, and the three commands; its reasoning is maintained in [About derived views](docs/explanation/projections.md) and [About the module boundaries](docs/explanation/module-boundaries.md) |
| [External anchor](docs/superpowers/specs/2026-10-04-aeusserer-anker.md) | Frozen design record, 2026-10-04: detailed specification of the external anchor — the anchor line, `anchor`, and `verify --anchors`; its reasoning is maintained in [About the hash chain](docs/explanation/hash-chain.md), the routines in [How to check the chain in operation](docs/how-to/verify-the-chain.md) and [How to check how much of the chain a restore brought back](docs/how-to/restore-from-a-backup.md) |
| [Stage 1c](docs/superpowers/specs/2026-10-04-stufe-1c-blobs-und-tilgung.md) | Frozen design record, 2026-10-05: detailed specification of blobs and erasure — hash format 2 with its salt, erasure as an event, blobs sealed in `age` on S3, and the commands `redact`, `blob get` and `verify --blobs`; its reasoning is maintained in [About erasure](docs/explanation/erasure.md), [About blobs](docs/explanation/blobs.md) and [About the hash chain](docs/explanation/hash-chain.md), its routines in the guides under [How-to guides](docs/how-to/index.md), and its open points in the [map](docs/superpowers/landkarte.md) |
| [Execution records](docs/superpowers/sdd/) | Frozen working records, one directory per executed plan: the ledger of every decision taken while building it, and the target of the `ruling …` citations in the code |
| [CLAUDE.md](CLAUDE.md) | The working agreements: language, attribution, dependencies, the six gates |
| [DEPENDENCIES.md](DEPENDENCIES.md) | Every dependency with its purpose, the rejected alternative and the date it was last checked |
| [NOTIZEN.md](NOTIZEN.md) | The conversation log of how it came about, the discarded routes included |

## Licence

[AGPL-3.0-or-later](LICENSE).

Affero deliberately: Previously is a server application, and the ordinary GPL
does not bite when somebody runs a modified version as a service without
handing out code.
