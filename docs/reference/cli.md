(cli-reference)=

# Command line

`previously` is the command-line entry point.
It has four subcommands: `append`, `log`, `verify`, and `show`.
Every subcommand reads the database connection string from `PREVIOUSLY_DSN`; see {ref}`configuration-reference`.

## Exit codes

| Command | 0 | 1 | 2 |
|---|---|---|---|
| `append` | The event was recorded, or an event with the same `--source` and `--external-id` already existed. | Not used. | The input was invalid, or storage raised an error. |
| `log` | The chronicle was printed. | Not used. | Storage raised an error. |
| `verify` | The chain has no finding. | The chain has at least one finding. | Storage raised an error. |
| `show` | The event was printed. | No event exists at the given `event_id`. | The input was invalid, or storage raised an error. |

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

Prints the chronicle, one line per event.

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
