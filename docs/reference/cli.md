(cli-reference)=

# Command line

`previously` is the command-line entry point.
It has eight subcommands: `append`, `log`, `verify`, `anchor`, `show`, `project`, `chronicle`, and `stats`.
Every subcommand reads the database connection string from `PREVIOUSLY_DSN`; see {ref}`configuration-reference`.

## Exit codes

| Command | 0 | 1 | 2 |
|---|---|---|---|
| `append` | The event was recorded, or an event with the same `--source` and `--external-id` already existed. | Not used. | The input was invalid, or storage raised an error. |
| `log` | The log was printed. | Not used. | The input was invalid, or storage raised an error. |
| `verify` | The chain has no finding, and every anchor holds. | The chain or an anchor has at least one finding. | The input was invalid, or storage raised an error. |
| `anchor` | The anchor line was printed, or the log is empty. | The chain has at least one finding. | Storage raised an error. |
| `show` | The event was printed. | No event exists at the given `event_id`. | The input was invalid, or storage raised an error. |
| `project` | Every projection stands at the tip of the log. | Not used. | Storage raised an error, or the worker found a gap in the log. |
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
| `--limit` | No | `50` | The maximum number of events to print, at least 1. |

Each line holds four tab-separated fields, in this order: `id`, `occurred_at` (ISO 8601), `kind`, and the first 12 hexadecimal characters of `hash`.

A `--limit` below 1 is refused before anything is read: `log` returns 2 and prints one sentence naming `--limit` to standard error.

## `verify`

Checks the chain and reports every finding.
With `--anchors`, it also checks the log against anchor lines kept outside the database; see {ref}`external-anchor`.

| Argument | Required | Default | Description |
|---|---|---|---|
| `--anchors FILE` | No | — | A file of anchor lines to check against; `-` reads standard input. |
| `--exact` | No | Off | The tip of the log has to be the newest anchor; requires `--anchors`. |

An anchor line holds two fields separated by whitespace: an event `id`, a positive integer, and that event's `hash`, 64 hexadecimal characters.
`anchor` prints lines in this format.

The anchor file is read as UTF-8 text, with or without a byte order mark, and with Unix or Windows line ends.
Blank lines and lines starting with `#` don't count.
Any other line that isn't an anchor line is an input error, named by its line number.
A file without a single anchor line, a file that can't be read, and a file that isn't UTF-8 text are input errors as well.
`--exact` without `--anchors` is an input error, refused before the database is read.
On an input error, `verify` prints nothing to standard output, prints one sentence to standard error, and returns 2.

Every anchor is checked in the pass that checks the chain.
An anchor holds when the log contains it: the event at the anchor's `id` exists and carries the anchor's `hash`.
A file may name the same `id` on several lines, and each line is checked.
With `--exact`, the log also must not continue past the newest anchor, the anchor with the highest `id`.

Each finding prints as one line: `FINDING <event_id>: <reason>`.
Three findings come from the anchors:

```text
FINDING 42: hash does not match the anchor
FINDING 42: anchored event is missing (the log ends at 40)
FINDING 43: the log continues past the newest anchor (42)
```

The first two name the anchored `id`, the third names the tip.
`the log ends at` names the `id` of the last event in the log, and `0` for an empty log.
The number in parentheses in the third is the `id` of the newest anchor.

With no finding, `verify` prints a single line, which depends on the arguments:

| Arguments | Line |
|---|---|
| None | `chain intact` |
| `--anchors` | `chain intact, <n> anchors hold` |
| `--anchors` and `--exact` | `chain intact, <n> anchors hold, the tip is the newest anchor` |

`<n>` is the number of anchor lines in the file, and a count of one prints as `1 anchor holds`.

Without anchors, one notice goes to standard error, and the exit code stays 0:

```text
no anchor given: verify attests that the log is unchanged, not that it is complete; see `previously anchor`
```

`verify` prints the notice only with no finding.

## `anchor`

Checks the chain and prints its tip as an anchor line.
It takes no arguments.

On an intact chain, `anchor` prints exactly one line to standard output: `<id> <hash>`, the `id` of the last event in the log and its `hash` as 64 lowercase hexadecimal characters.
The line describes the chain the same run checked.
With a finding, `anchor` prints the `FINDING` lines in the format `verify` uses and no anchor line.

On an empty log, one notice goes to standard error, and nothing goes to standard output:

```text
the log is empty: nothing to anchor
```

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

Four characters print as two characters each, in every field and not in `content` alone: a tab as `\t`, a newline as `\n`, a carriage return as `\r`, and a backslash as `\\`.
`source` and `external_id` carry whatever `append` was given, and a tab there would otherwise add a field and a newline would break the record in two.
The backslash is escaped first, so the escaping is reversible.
The stored values are unchanged; the escaping is part of the output format.

`--since` and `--until` form a half-open window, so a `--since` equal to or later than `--until` selects nothing.
Both need a UTC offset; without one, `chronicle` returns 2 and prints one sentence to standard error.
A `--limit` below 1 is refused the same way, before anything is read.

Two notices go to standard error, and both leave the exit code at 0.
The first prints when `--limit` cuts the output, the second when the projection stands behind the tip of the log, and a single run can print both in that order:

```text
output truncated at 50 lines; raise --limit or narrow --since/--until
projection is 12 events behind; run `previously project`
```

A lag of one event prints as `1 event behind`.
Standard output carries neither notice, and no notice at all means that the chronicle is current and the window is complete.

{ref}`projections` explains why `log` and `chronicle` are two commands.

## `stats`

Prints the per-source statistics, one line per source.
It takes no arguments.

Each line holds five tab-separated fields, in this order: `source`, `events`, `units`, `first_seen` (ISO 8601), and `last_seen` (ISO 8601).
`source` is escaped the way `chronicle` escapes its fields, so a tab in a source name can't add a sixth field.
Lines come out ordered by `source`.
An event with no source attribution appears in no line.

`stats` reports the lag of `source-stats` on standard error, in the same sentence `chronicle` uses and with the same exit code 0.
The two commands report the lag of the projection each one reads, so after a rebuild of one of the two the numbers can differ.
