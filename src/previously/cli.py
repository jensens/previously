# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The minimal submission path ({ref}`cli-reference`).

Not meant as a product surface, but so that stage 1a **runs** — not because
that is useful, but because being runnable drives out things one otherwise
forgets.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from datetime import UTC
from previously.contract.types import Evidence
from previously.contract.types import RawEvent
from previously.core.anchor import format_anchor
from previously.core.anchor import parse_anchors
from previously.core.append import append
from previously.core.errors import InvalidPayload
from previously.core.errors import PreviouslyError
from previously.core.projection import catch_up
from previously.core.projection import CHRONICLE
from previously.core.projection import Outcome
from previously.core.projection import PROJECTIONS
from previously.core.projection import SOURCE_STATS
from previously.core.units import split_plaintext
from previously.core.verify import examine
from previously.storage.errors import StorageError
from previously.storage.postgres import from_dsn
from previously.storage.postgres import PostgresStorage
from typing import TYPE_CHECKING

import argparse
import io
import json
import os
import sys


if TYPE_CHECKING:
    from collections.abc import Sequence
    from previously.contract.types import Anchor

MAX_TEXT_BYTES = 1_000_000


def parse_moment(text: str) -> datetime:
    """An ISO 8601 timestamp **with** a zone. Without a zone, local time would be meant."""
    try:
        moment = datetime.fromisoformat(text)
    except ValueError as error:
        raise InvalidPayload(f"{text!r} is not an ISO 8601 timestamp") from error
    if moment.tzinfo is None:
        raise InvalidPayload(
            f"{text!r} has no time zone — without a zone local time would be meant "
            "and the hash would not be reproducible"
        )
    return moment


def _parse_evidence(value: str) -> Evidence:
    """The kind of evidence out of `--evidence` (review finding G3).

    Not as `choices=` on the argparse argument, for two reasons: first,
    `choices=` on an invalid value goes straight to `sys.exit(2)` via
    `parser.error()` — a real process abort, not a `return 2` out of `main`,
    and therewith different from every other error path of this command line
    (W2: "both branches return exit code 2"). Second, this keeps the
    translation at the same place as every other payload check:
    `InvalidPayload`, caught by the existing `except` branch in `main`.
    """
    try:
        return Evidence(value)
    except ValueError as error:
        allowed = ", ".join(e.value for e in Evidence)
        raise InvalidPayload(
            f"{value!r} is not a valid kind of evidence — allowed are {allowed}"
        ) from error


def escape_field(text: str) -> str:
    """One row is one line of a tab-separated stream ({ref}`projections`), so
    tab, newline, carriage return and the backslash itself come out as two
    characters each. Backslash first, or the other escapes would be escaped
    again and the mapping would stop being reversible. Output format, not
    data: `p_chronicle` holds the content unchanged.

    Applied to **every** string field both reading commands print, not to
    `content` alone. `source` and `external_id` come from `--source` and
    `--external-id`, and `core.append` refuses only a null byte and a lone
    surrogate there — a tab and a newline are reachable from the command
    line. Measured on 2026-10-04 with the escaping on `content` only, one
    appended event carrying a tab in `--source` and a newline in
    `--external-id`: `chronicle` printed that one unit as two lines with six
    and two fields instead of one line with six, and `stats` printed six
    fields instead of five.

    Public rather than `_escape` because a test calls it directly, and a
    direct test earns a public name instead of a suppressed private-usage
    warning.
    """
    return text.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")


def _plural(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def _describe(outcome: Outcome) -> str:
    """Which path the worker took — a version-triggered rebuild is otherwise
    invisible ({ref}`projections`).

    Order matters. A version change is reported even when it processed no
    event, because it changed the state row. A first run over an empty log
    says `up to date`, not `built: 0 events`: nothing was built, and the
    reading of `up_to_id 0` is "nothing yet".
    """
    tail = f"{_plural(outcome.events, 'event')}, up_to_id {outcome.up_to_id}"
    if outcome.rebuilt_from:  # a version the table was at before: 1, 2, …
        return f"rebuilt: version {outcome.rebuilt_from} -> {outcome.version}, {tail}"
    if outcome.events == 0:
        return f"up to date, up_to_id {outcome.up_to_id}"
    if outcome.rebuilt_from == 0:
        return f"built: {tail}"
    return f"caught up: {tail}"


def _lag_line(tip_id: int, up_to_id: int) -> str | None:
    """The lag of the projection being read, or `None` for none.

    Takes the two numbers rather than a connection, because `cli` is not to
    know that SQLAlchemy exists (ruling T9-a): over `storage` it stands for
    `from_dsn` and `PostgresStorage`, and a `Connection` in this signature
    would add a third name. The caller reads the two numbers in **one
    statement**, through `tip_and_bookmark`, or the difference is one that
    never existed — one transaction does not do it under READ COMMITTED, see
    that method.
    """
    lag = tip_id - up_to_id
    if lag <= 0:
        return None
    return f"projection is {_plural(lag, 'event')} behind; run `previously project`"


def _storage() -> PostgresStorage:
    # Creating the engine itself stands in `storage.postgres.from_dsn`
    # (ruling T9-a) — `cli` knows neither SQLAlchemy nor a driver URL, only
    # the environment variable.
    dsn = os.environ.get("PREVIOUSLY_DSN")
    if not dsn:
        raise PreviouslyError("PREVIOUSLY_DSN is not set")
    return from_dsn(dsn)


def _read_anchors(source: str) -> tuple[Anchor, ...]:
    """The anchor file, or standard input for `-` ({ref}`external-anchor`).

    Reading is all this function does; what a line has to look like is
    `parse_anchors` in `core`, so that a second entry point reads the same
    format without this file.

    Both sources are read as bytes and decoded once, here, with
    `utf-8-sig`, so that nothing can be true of a file and false of standard
    input: a byte order mark is dropped from either, and bytes that are not
    UTF-8 are an input error from either. Standard input is not decoded with
    the terminal's settings, and a source that cannot be read or decoded
    becomes `InvalidPayload` and with it exit code 2 — one sentence, not a
    stack trace, and not the exit code 1 a scheduled job reads as a finding.

    `io.StringIO(text, newline=None)` hands the parser lines the way a file
    opened in text mode does: `\\r\\n` and `\\r` become `\\n`, and nothing else
    ends a line. `str.splitlines()` would also break on a form feed and the
    other Unicode line separators, and one bad line would then be reported
    under two line numbers. The parser runs after the `try`, so an
    `InvalidPayload` it raises never passes through the two handlers.
    """
    name = "standard input" if source == "-" else f"the anchor file {source!r}"
    try:
        if source == "-":
            raw = sys.stdin.buffer.read()
        else:
            with open(source, "rb") as handle:
                raw = handle.read()
        text = raw.decode("utf-8-sig")
    except OSError as error:
        raise InvalidPayload(f"cannot read {name}: {error.strerror}") from error
    except UnicodeDecodeError as error:
        raise InvalidPayload(f"{name} is not UTF-8 text") from error
    return parse_anchors(io.StringIO(text, newline=None))


def _append_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source", required=True)
    parser.add_argument("--external-id", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--occurred-at")
    # The default "recollection": the cautious assumption, and a submission by
    # hand is mostly exactly that (review finding G3). No `choices=` — the
    # invalid case is translated in `_parse_evidence`, see there.
    parser.add_argument("--evidence", default="recollection")


def _cmd_append(args: argparse.Namespace) -> int:
    # `surrogatepass`, not strict (finding W-1): a lone UTF-16 surrogate can
    # arrive out of `argv` — `argv` carries bytes, and Python decodes
    # undecodable ones with `surrogateescape` — and strict encoding raised
    # `UnicodeEncodeError` here. Measured on stderr of the real command, 10
    # lines of traceback and the interpreter's exit code 1 instead of this
    # command line's 2. This line is supposed to measure a **size**, not
    # decide about encodability; that decision belongs to the canonicalisation
    # ({ref}`payload-range`), which `core.append` reaches via `payload_hash`
    # and which then reports `InvalidPayload` with a sentence naming the field.
    # For every string without surrogates `surrogatepass` and strict yield the
    # identical byte count, so the bound itself does not move.
    if len(args.text.encode("utf-8", "surrogatepass")) > MAX_TEXT_BYTES:
        raise InvalidPayload(
            f"text larger than {MAX_TEXT_BYTES} bytes — split it into smaller submissions"
        )
    occurred = parse_moment(args.occurred_at) if args.occurred_at else datetime.now(UTC)
    event = RawEvent(
        source=args.source,
        external_id=args.external_id,
        occurred_at=occurred,
        evidence=_parse_evidence(args.evidence),
        units=split_plaintext(args.text),
        payload={"text": args.text},
    )
    ids = append(_storage(), [event], recorded_at=datetime.now(UTC))
    print(ids[0])
    return 0


def _log_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--from", dest="from_id", type=int, default=1)
    parser.add_argument("--limit", type=int, default=50)


def _cmd_log(args: argparse.Namespace) -> int:
    # The same guard as `chronicle`, in the same words and for the same
    # reason; see there for why it is `InvalidPayload` and not a `type=`
    # callable. `log` had been open since stage 1a, and measured against a
    # real PostgreSQL 17 on 2026-10-04 the two halves failed differently:
    # `--limit 0` returned 0 with nothing on stdout and nothing on stderr, so
    # an empty log and a refused limit looked alike, and `--limit -2` passed
    # `LIMIT -2` to the driver and came back as `sqlalchemy.exc.DataError:
    # (psycopg.errors.InvalidRowCountInLimitClause) LIMIT must not be
    # negative` — a foreign exception this command line does not catch, so a
    # stack trace and the interpreter's exit code 1 instead of 2. Two
    # commands, the same option, two error shapes.
    if args.limit < 1:
        raise InvalidPayload(f"--limit must be at least 1, got {args.limit}")
    storage = _storage()
    # The reading methods take the connection in since review finding G4: the
    # transaction boundary belongs to the caller, who knows what has to be
    # read together. Here that is a formality. `show` reads an event and its
    # units in one transaction, but in two statements, which under the READ
    # COMMITTED of `begin` are two snapshots. It still shows one state, and
    # not because of a snapshot: `insert_event` writes an event and its units
    # in the one transaction of `append`, so they commit together, and
    # nothing in `src` rewrites or deletes either afterwards. Whoever sees the
    # event sees its units.
    with storage.begin() as conn:
        for row in storage.read(conn, from_id=args.from_id, limit=args.limit):
            print(f"{row.id}\t{row.occurred_at.isoformat()}\t{row.kind}\t{row.hash.hex()[:12]}")
    return 0


def _verify_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--anchors", metavar="FILE", help="anchor lines to check against; - reads standard input"
    )
    parser.add_argument("--exact", action="store_true", help="the tip has to be the newest anchor")


def _cmd_verify(args: argparse.Namespace) -> int:
    # Refused before the database is asked for: there is nothing `--exact`
    # could compare the tip with.
    if args.exact and args.anchors is None:
        raise InvalidPayload("--exact needs --anchors")
    anchors = () if args.anchors is None else _read_anchors(args.anchors)
    examination = examine(_storage(), anchors=anchors, exact=args.exact)
    for finding in examination.findings:
        print(f"FINDING {finding.event_id}: {finding.reason}")
    if examination.findings:
        return 1
    if not anchors:
        # Standard output stays the one line scripts read. The limit of the
        # statement goes to standard error, the way `chronicle` reports its
        # lag ({ref}`external-anchor`): without an anchor the chain attests
        # "unchanged" and nothing about "complete". Only on an intact chain —
        # beside findings the sentence would be noise.
        print("chain intact")
        print(
            "no anchor given: verify attests that the log is unchanged, "
            "not that it is complete; see `previously anchor`",
            file=sys.stderr,
        )
        return 0
    count = len(anchors)
    held = f"{_plural(count, 'anchor')} {'holds' if count == 1 else 'hold'}"
    tail = ", the tip is the newest anchor" if args.exact else ""
    print(f"chain intact, {held}{tail}")
    return 0


def _cmd_anchor(_args: argparse.Namespace) -> int:
    """Prints the tip of an intact chain as an anchor line
    ({ref}`external-anchor`).

    The tip is the last row the pass saw, so the line describes exactly the
    chain that was checked. Whether there is a line at all is
    `Examination.anchor`'s decision, not this function's: on a finding the
    core gives none, because an anchor on a broken chain would certify the
    break. What is left here is formatting.

    The findings go to standard error, unlike `verify`'s. Standard output
    of this command is a data channel: the routine appends it to the anchor
    file with `>>`, and a finding printed there landed in that file, where
    the next `verify --anchors` refused the line as an input error (exit
    code 2) instead of reporting the finding (exit code 1). On standard
    output there is an anchor line or nothing ({ref}`cli-reference`).
    """
    examination = examine(_storage())
    for finding in examination.findings:
        print(f"FINDING {finding.event_id}: {finding.reason}", file=sys.stderr)
    anchor = examination.anchor
    if anchor is not None:
        print(format_anchor(anchor))
    elif not examination.findings:
        print("the log is empty: nothing to anchor", file=sys.stderr)
    return 1 if examination.findings else 0


def _show_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("event_id", type=int)


def _cmd_show(args: argparse.Namespace) -> int:
    storage = _storage()
    with storage.begin() as conn:
        for row in storage.read(conn, from_id=args.event_id, limit=1):
            if row.id != args.event_id:
                break
            print(f"id={row.id} kind={row.kind}")
            print(f"occurred_at={row.occurred_at.isoformat()}")
            print(f"hash={row.hash.hex()}")
            # The kind of evidence and the payload (finding G-1). Before, both
            # were writable through `append` and unreadable through any
            # documented surface — in an append-only store, where the kind of
            # evidence stands permanently in the hash and cannot be supplied
            # afterwards, that was the wrong half.
            #
            # `evidence` out of the payload and named separately, because
            # `append` mixes it in under that reserved key
            # ({ref}`canonicalization`): it is not one payload field among
            # others but the statement that separates proof from report. The
            # tombstone has neither ({ref}`tombstone-seam`), and
            # `payload=<erased>` says that instead of printing an empty line.
            if row.payload is None:
                print("payload=<erased>")
            else:
                print(f"evidence={row.payload.get('evidence')}")
                # `sort_keys` so the output is stable across runs: `payload`
                # comes back out of jsonb, and the order of keys in jsonb is
                # not the order they were written in.
                print(f"payload={json.dumps(row.payload, ensure_ascii=False, sort_keys=True)}")
            for unit in storage.units(conn, row.id):
                # An erased unit says so, like the payload above, rather than
                # printing `None` where its text stood.
                content = "<erased>" if unit.content is None else unit.content
                print(f"  ¶{unit.seq} {content}")
            return 0
    print(f"No event {args.event_id}", file=sys.stderr)
    return 1


def _cmd_project(_args: argparse.Namespace) -> int:
    storage = _storage()
    # `PROJECTIONS` fixes the order, so two runs print their lines the same way
    # round. `catch_up` gets the same object twice because `PostgresStorage` is
    # both the log it reads and the projection store it writes.
    for projection in PROJECTIONS:
        outcome = catch_up(storage, storage, projection)
        print(f"{outcome.name:<15} {_describe(outcome)}")
    return 0


def _chronicle_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--since", help="ISO 8601 with a zone, inclusive")
    parser.add_argument("--until", help="ISO 8601 with a zone, exclusive")
    parser.add_argument("--limit", type=int, default=50)


def _cmd_chronicle(args: argparse.Namespace) -> int:
    # A caller error, named as one and refused before the read. Measured
    # against a real PostgreSQL 17 without this guard: `--limit 0` returned 0
    # with an empty stdout and `output truncated at 0 lines` on stderr — a
    # truncation that had not happened, because `limit + 1` still returns a
    # row — and `--limit -2` passed `LIMIT -1` to the driver and came back as
    # `sqlalchemy.exc.DataError: LIMIT must not be negative`, a foreign
    # exception this command line does not catch, so a stack trace and the
    # interpreter's exit code 1 instead of 2 (review finding W2's class).
    #
    # `InvalidPayload` and not a `type=` callable on the argument: a callable
    # that raises goes through `parser.error()` to `sys.exit(2)`, a process
    # abort rather than a `return 2` out of `main` — the same reason
    # `_parse_evidence` exists instead of `choices=` (review finding W2, both
    # branches return exit code 2). `core.projection.catch_up` refuses its own
    # `batch_size` below one in the same words.
    if args.limit < 1:
        raise InvalidPayload(f"--limit must be at least 1, got {args.limit}")
    # The same `parse_moment` as `--occurred-at`, so a window without a zone is
    # refused here too rather than silently read as local time.
    since = parse_moment(args.since) if args.since else None
    until = parse_moment(args.until) if args.until else None
    storage = _storage()
    with storage.begin() as conn:
        # Tip and bookmark in one statement, not in two: a transaction is not
        # a moment under READ COMMITTED (see `tip_and_bookmark`).
        position = storage.tip_and_bookmark(conn, CHRONICLE.name)
        # One more than the limit: if that extra row comes back, the window was
        # cut. Counting the printed lines against the limit cannot tell a
        # window that ends exactly at the limit from one that was cut there.
        rows = storage.read_chronicle(conn, since=since, until=until, limit=args.limit + 1)
    # Every string field through `escape_field`, not `content` alone: a tab or
    # a newline in `source` or `external_id` would otherwise add a field or
    # break the record in two (see `escape_field`).
    for row in rows[: args.limit]:
        print(
            f"{row.event_id}\t{row.seq}\t{row.occurred_at.isoformat()}\t"
            f"{escape_field(row.source or '')}\t{escape_field(row.external_id or '')}\t"
            f"{escape_field(row.content)}"
        )
    # Both notices go to stderr, not into the stream: in stdout either one
    # would be a line every consumer reads as a record. Silence means current
    # and complete ({ref}`projections`).
    if len(rows) > args.limit:
        print(
            f"output truncated at {args.limit} lines; raise --limit or narrow --since/--until",
            file=sys.stderr,
        )
    lag = _lag_line(position.tip_id, position.up_to_id)
    if lag:
        print(lag, file=sys.stderr)
    return 0


def _cmd_stats(_args: argparse.Namespace) -> int:
    storage = _storage()
    with storage.begin() as conn:
        # `SOURCE_STATS.name`, not `CHRONICLE.name`: after a rebuild of one of
        # the two the bookmarks differ, and the lag a reader is told has to be
        # the lag of the table they are reading. The name comes off the
        # projection object rather than being typed as a literal, so that
        # renaming a projection cannot leave this read silently pointing at a
        # missing state row — which `tip_and_bookmark` would report as "the
        # whole log is behind".
        position = storage.tip_and_bookmark(conn, SOURCE_STATS.name)
        rows = storage.read_source_stats(conn)
    for row in rows:
        print(
            f"{escape_field(row.source)}\t{row.events}\t{row.units}\t"
            f"{row.first_seen.isoformat()}\t{row.last_seen.isoformat()}"
        )
    lag = _lag_line(position.tip_id, position.up_to_id)
    if lag:
        print(lag, file=sys.stderr)
    return 0


def _no_arguments(_parser: argparse.ArgumentParser) -> None:
    """For a command that takes no arguments."""


@dataclass(frozen=True)
class Command:
    """One subcommand: its name, its help line, its arguments and its body."""

    name: str
    help: str
    run: Callable[[argparse.Namespace], int]
    arguments: Callable[[argparse.ArgumentParser], None] = _no_arguments


# The one place a command is declared. `main` builds the subparsers and the
# dispatch from this sequence, so a command cannot have a subparser and no
# body, or a body nobody can call: until 2026-10-04 the two were written out
# separately, and a subparser without its entry in the dispatch table would
# have ended in a `KeyError` traceback. The order is the order
# `previously --help` lists them in.
#
# Public because a test reads it: `tests/test_cli.py` holds the commands the
# help names against these names.
COMMANDS: tuple[Command, ...] = (
    Command("append", "submit text", _cmd_append, _append_arguments),
    # "print the chronicle" until stage 1b, which is now the other command:
    # `log` is the chain order and `chronicle` the chronology ({ref}`projections`).
    Command("log", "print the log in chain order", _cmd_log, _log_arguments),
    Command("verify", "check the chain, and anchors if given", _cmd_verify, _verify_arguments),
    Command("anchor", "print the tip of an intact chain as an anchor line", _cmd_anchor),
    Command("show", "show one event with its units", _cmd_show, _show_arguments),
    Command("project", "bring the projections up to the tip of the log", _cmd_project),
    Command("chronicle", "print the chronicle in time order", _cmd_chronicle, _chronicle_arguments),
    Command("stats", "print the per-source statistics", _cmd_stats),
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="previously")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in COMMANDS:
        command.arguments(sub.add_parser(command.name, help=command.help))
    args = parser.parse_args(argv)

    # A table instead of an `if` chain: a lookup adds no branch where each
    # `if` adds one, so the number of commands does not move the complexity
    # of `main`. Measured with `ruff check --select C901 --config
    # 'lint.mccabe.max-complexity = 1' src/previously/cli.py` on 2026-10-04,
    # once the subparsers and the table were built from `COMMANDS`: `main`
    # stands at 3 — the 1 every function starts with, the loop and the
    # `except`; the comprehension adds nothing — against the project's
    # threshold of 10, ruff's default, which `C901` has to exceed. The `if`
    # chain the table replaced was measured earlier that day at 9 with seven
    # commands, 10 with eight and 11 with nine: a ninth command would have
    # broken the gate.
    run = {command.name: command.run for command in COMMANDS}
    try:
        # No fallback below: `add_subparsers(..., required=True)` makes
        # `parse_args` fail before this line without the name of a command,
        # and every name it accepts came out of `COMMANDS`, so the lookup
        # cannot raise `KeyError`.
        return run[args.command](args)
    except (PreviouslyError, StorageError) as error:
        # Two kinds of error, one branch (review finding W2): `core` raises
        # `PreviouslyError`, `storage` raises `StorageError` — the two
        # deliberately do not inherit from the same root (see
        # `storage/errors.py`), which is why there are two types in one
        # exception tuple instead of one common umbrella. Foreign sqlalchemy
        # exceptions that `storage` does not know this branch deliberately does
        # not catch — they are to come through as a stack trace, not dressed up
        # as a one-liner.
        print(f"Error: {error}", file=sys.stderr)
        return 2
