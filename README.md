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

The three specifications below are **frozen design records**, in German and
dated: they hold how and why a decision was taken, and the documentation under
`docs/` carries the reasoning that is maintained with the code. Where the two
disagree, the documentation wins. A new stage starts with a new German
specification, which freezes once its explanation pages stand.

| Document | Content |
|---|---|
| [Design](docs/superpowers/specs/2026-10-01-previously-design.md) | Frozen design record: goal, guiding principles, core model, attribution, projections, release model, acceptance conditions |
| [Architecture](docs/superpowers/specs/2026-10-01-architektur.md) | Frozen design record: modules and boundaries, schema, connector contract, process model, MCP, tooling |
| [Stage 1a](docs/superpowers/specs/2026-10-02-stufe-1a-log.md) | Frozen design record: detailed specification of the append-only log with its hash chain |
| [Execution records](docs/superpowers/sdd/) | Frozen working records, one directory per executed plan: the ledger of every decision taken while building it, and the target of the `ruling …` citations in the code |
| [CLAUDE.md](CLAUDE.md) | The working agreements: language, attribution, dependencies, the six gates |
| [DEPENDENCIES.md](DEPENDENCIES.md) | Every dependency with its purpose, the rejected alternative and the date it was last checked |
| [NOTIZEN.md](NOTIZEN.md) | The conversation log of how it came about, the discarded routes included |

## Licence

[AGPL-3.0-or-later](LICENSE).

Affero deliberately: Previously is a server application, and the ordinary GPL
does not bite when somebody runs a modified version as a service without
handing out code.
