(cli-reference)=

# Command line

`previously` is the command-line entry point.
It has seven subcommands: `append`, `log`, `verify`, `show`, `project`, `chronicle`, and `stats`.
Every subcommand reads the database connection string from `PREVIOUSLY_DSN`; see {ref}`configuration-reference`.

## Exit codes

| Command | 0 | 1 | 2 |
|---|---|---|---|
| `append` | The event was recorded, or an event with the same `--source` and `--external-id` already existed. | Not used. | The input was invalid, or storage raised an error. |
| `log` | The log was printed. | Not used. | Storage raised an error. |
| `verify` | The chain has no finding. | The chain has at least one finding. | Storage raised an error. |
| `show` | The event was printed. | No event exists at the given `event_id`. | The input was invalid, or storage raised an error. |
| `project` | Every projection stands at the tip of the log. | Not used. | Storage raised an error. |
| `chronicle` | The chronicle was printed, even when the window holds no row. | Not used. | The input was invalid, or storage raised an error. |
| `stats` | The statistics were printed, even when no source has an event. | Not used. | Storage raised an error. |

## `append`

Submits one event and prints its `id`.

| Argument | Required | Default | Description |
|---|---|---|---|
| `--source` | Yes | — | The event's source system. |
| `--external-id` | Yes | — | The event's identifier within that source. |
| `--text` | Yes | — | UTF-8 text, at most 1,000,000 bytes. |
| `--occurred-at` | No | The current UTC time. | An ISO 8601 timestamp with a UTC offset. |
| `--evidence` | No | `recollection` | `verbatim` or `recollection`. |

`append` prints exactly one line to standard output: the new event's `id`.
Calling `append` again with the same `--source` and `--external-id` doesn't create a second event.
It prints the existing event's `id` and returns 0.

## `log`

Prints the log in chain order, one line per event.

| Argument | Required | Default | Description |
|---|---|---|---|
| `--from` | No | `1` | The lowest event `id` to print. |
| `--limit` | No | `50` | The maximum number of events to print. |

Each line holds four tab-separated fields, in this order: `id`, `occurred_at` (ISO 8601), `kind`, and the first 12 hexadecimal characters of `hash`.

## `verify`

Checks the chain and reports every finding.
It takes no arguments.

Each finding prints as one line: `FINDING <event_id>: <reason>`.
With no finding, `verify` prints the single line `chain intact`.

## `show`

Prints one event with its units.

| Argument | Required | Default | Description |
|---|---|---|---|
| `event_id` | Yes | — | The event's `id`, as a positional argument. |

On success, `show` opens with three lines, in this order: `id=<id> kind=<kind>`—both on the one line—then `occurred_at=<ISO 8601>`, then `hash=<64 hexadecimal characters>`.
It then prints either `payload=<erased>`, or both `evidence=<verbatim|recollection>` and `payload=<JSON object, with sorted keys>`.
It then prints one line per unit, in `seq` order: `  ¶<seq> <content>`.
Without an event at the given `event_id`, `show` prints `No event <event_id>` to standard error.

## `project`

Brings every projection up to the tip of the log.
It takes no arguments.

`project` prints one line per projection, `chronicle` first and `source-stats` second.
Each line holds the projection's name padded to 15 characters, a space, and the outcome of the run.
There are four outcomes:

| Outcome | Condition |
|---|---|
| `built: <n> events, up_to_id <id>` | The projection had no state row, and the log held events to project. |
| `caught up: <n> events, up_to_id <id>` | The projection had a state row at the code's version, and the log had grown since. |
| `rebuilt: version <n> -> <m>, <k> events, up_to_id <id>` | The state row stood at version `<n>` and the code declares `<m>`, so the table was emptied and built again. |
| `up to date, up_to_id <id>` | No event was projected, and the version was unchanged. |

A count of one prints as `1 event`, every other count as `<n> events`.
`up to date` carries no count, and `up_to_id 0` means that nothing has been projected yet.

## `chronicle`

Prints the chronicle in time order, one line per unit.

| Argument | Required | Default | Description |
|---|---|---|---|
| `--since` | No | — | An ISO 8601 timestamp with a UTC offset, as an inclusive lower bound on `occurred_at`. |
| `--until` | No | — | An ISO 8601 timestamp with a UTC offset, as an exclusive upper bound on `occurred_at`. |
| `--limit` | No | `50` | The maximum number of lines to print, at least 1. |

Each line holds six tab-separated fields, in this order: `event_id`, `seq`, `occurred_at` (ISO 8601), `source`, `external_id`, and `content`.
An event with no source attribution prints two empty fields in place of `source` and `external_id`.
Lines come out ordered by `occurred_at`, then `event_id`, then `seq`.

Four characters in `content` print as two characters each: a tab as `\t`, a newline as `\n`, a carriage return as `\r`, and a backslash as `\\`.
The backslash is escaped first, so the escaping is reversible.
The stored content is unchanged; the escaping is part of the output format.

`--since` and `--until` form a half-open window, so a `--since` equal to or later than `--until` selects nothing.
Both need a UTC offset; without one, `chronicle` returns 2 and prints one sentence to standard error.
A `--limit` below 1 is refused the same way, before anything is read.

Two notices go to standard error, and both leave the exit code at 0.
The first prints when the projection stands behind the tip of the log, the second when `--limit` cuts the output:

```text
projection is 12 events behind; run `previously project`
output truncated at 50 lines; raise --limit or narrow --since/--until
```

A lag of one event prints as `1 event behind`.
Standard output carries neither notice, and no notice at all means that the chronicle is current and the window is complete.

{ref}`projections` explains why `log` and `chronicle` are two commands.

## `stats`

Prints the per-source statistics, one line per source.
It takes no arguments.

Each line holds five tab-separated fields, in this order: `source`, `events`, `units`, `first_seen` (ISO 8601), and `last_seen` (ISO 8601).
Lines come out ordered by `source`.
An event with no source attribution appears in no line.

`stats` reports the lag of `source-stats` on standard error, in the same sentence `chronicle` uses and with the same exit code 0.
The two commands report the lag of the projection each one reads, so after a rebuild of one of the two the numbers can differ.
