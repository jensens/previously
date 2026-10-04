# Previously

> *Previously, on Project …*

A tool that gathers courses of events, commitments and open points from many
channels, orders them and makes them provable — so that the question "how do
things stand here?" is answerable without looking into six mailboxes.

The name is the main view: the header and the chronicle of a project, every
line with its source attribution.

## State

**Stages 1a and 1b are built and run: the append-only log with its hash chain,
and the projections derived from it.** Not a product surface — a command line
thin enough to get at the log by hand, so that each stage is *runnable* and not
merely described.

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
- **projections** (`project`) that are derivable from the log and disposable:
  `projection_state` records how far each one has got, and a raised derivation
  version empties its table and builds it again from the log
- **the chronicle** (`chronicle`) — one line per unit with its source
  attribution, in the order in which things happened rather than the order in
  which they were recorded
- **the per-source statistics** (`stats`): events, units, and the earliest and
  latest `occurred_at` per source
- the seven commands `append`, `log`, `verify`, `show`, `project`, `chronicle`
  and `stats`
- the schema as an Alembic migration

**What it does not do:** no header — a header rests on assertions, and those
come out of the gate; no assignment of events to projects, so the chronicle is
the chronicle of the whole log and not of one project; no job queue — the
projection worker is a command, run when somebody runs it; no connectors for
e-mail or issue trackers (stage 2), no MCP interface, no language model and
therefore no assertions or actions, no search, no erasure, no user
administration and no network interface.

And one limit that is not a gap but the nature of the thing: a hash chain
without an **outer anchor** bears witness that what stands in the log is
unchanged — not that it is complete. Deleting the tip, appending a
self-computed event or rewriting the whole chain leaves a result that is
consistent in itself.
[About the hash chain](docs/explanation/hash-chain.md) states which forgeries
are covered and which are not.

## Documentation

The full documentation — tutorials, how-to guides, reference and explanation —
lives under `docs/`. Build it locally with `make -C docs html`, then open
`docs/_build/html/index.html`. Start with
[Record your first event](docs/tutorials/record-your-first-event.md): a
session typed out against a real PostgreSQL 17, from a fresh checkout to a
passing test suite.

The four specifications below are **frozen design records**, in German and
dated: they hold how and why a decision was taken, and the documentation under
`docs/` carries the reasoning that is maintained with the code. Where the two
disagree, the documentation wins. A new stage starts with a new German
specification, which freezes once its explanation pages stand — stage 1b is
the first one that went that way from the start.

| Document | Content |
|---|---|
| [Design](docs/superpowers/specs/2026-10-01-previously-design.md) | Frozen design record: goal, guiding principles, core model, attribution, projections, release model, acceptance conditions |
| [Architecture](docs/superpowers/specs/2026-10-01-architektur.md) | Frozen design record: modules and boundaries, schema, connector contract, process model, MCP, tooling |
| [Stage 1a](docs/superpowers/specs/2026-10-02-stufe-1a-log.md) | Frozen design record: detailed specification of the append-only log with its hash chain |
| [Stage 1b](docs/superpowers/specs/2026-10-04-stufe-1b-projektionen.md) | Frozen design record, 2026-10-04: detailed specification of the projections — the two derived tables, the worker, and the three commands; its reasoning is maintained in [About derived views](docs/explanation/projections.md) and [About the module boundaries](docs/explanation/module-boundaries.md) |
| [Execution records](docs/superpowers/sdd/) | Frozen working records, one directory per executed plan: the ledger of every decision taken while building it, and the target of the `ruling …` citations in the code |
| [CLAUDE.md](CLAUDE.md) | The working agreements: language, attribution, dependencies, the six gates |
| [DEPENDENCIES.md](DEPENDENCIES.md) | Every dependency with its purpose, the rejected alternative and the date it was last checked |
| [NOTIZEN.md](NOTIZEN.md) | The conversation log of how it came about, the discarded routes included |

## Licence

[AGPL-3.0-or-later](LICENSE).

Affero deliberately: Previously is a server application, and the ordinary GPL
does not bite when somebody runs a modified version as a service without
handing out code.
