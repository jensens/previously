# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The minimal submission path ({ref}`cli-reference`).

Not meant as a product surface, but so that stage 1a **runs** — not because
that is useful, but because being runnable drives out things one otherwise
forgets.
"""

from datetime import datetime
from datetime import UTC
from previously.contract.types import Evidence
from previously.contract.types import RawEvent
from previously.core.append import append
from previously.core.errors import InvalidPayload
from previously.core.errors import PreviouslyError
from previously.core.units import split_plaintext
from previously.core.verify import verify
from previously.storage.errors import StorageError
from previously.storage.postgres import from_dsn
from previously.storage.postgres import PostgresStorage
from typing import TYPE_CHECKING

import argparse
import json
import os
import sys


if TYPE_CHECKING:
    from collections.abc import Sequence

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


def _storage() -> PostgresStorage:
    # Creating the engine itself stands in `storage.postgres.from_dsn`
    # (ruling T9-a) — `cli` knows neither SQLAlchemy nor a driver URL, only
    # the environment variable.
    dsn = os.environ.get("PREVIOUSLY_DSN")
    if not dsn:
        raise PreviouslyError("PREVIOUSLY_DSN is not set")
    return from_dsn(dsn)


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


def _cmd_log(args: argparse.Namespace) -> int:
    storage = _storage()
    # The reading methods take the connection in since review finding G4: the
    # transaction boundary belongs to the caller, who knows what has to be
    # read together. For the chronicle that is a formality, for `show` it is
    # not — there, event and units belong in the same snapshot.
    with storage.begin() as conn:
        for row in storage.read(conn, from_id=args.from_id, limit=args.limit):
            print(f"{row.id}\t{row.occurred_at.isoformat()}\t{row.kind}\t{row.hash.hex()[:12]}")
    return 0


def _cmd_verify() -> int:
    findings = verify(_storage())
    for finding in findings:
        print(f"FINDING {finding.event_id}: {finding.reason}")
    if not findings:
        print("chain intact")
    return 1 if findings else 0


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
                print(f"  ¶{unit.seq} {unit.content}")
            return 0
    print(f"No event {args.event_id}", file=sys.stderr)
    return 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="previously")
    sub = parser.add_subparsers(dest="command", required=True)

    p_append = sub.add_parser("append", help="submit text")
    p_append.add_argument("--source", required=True)
    p_append.add_argument("--external-id", required=True)
    p_append.add_argument("--text", required=True)
    p_append.add_argument("--occurred-at")
    # The default "recollection": the cautious assumption, and a submission by
    # hand is mostly exactly that (review finding G3). No `choices=` — the
    # invalid case is translated in `_parse_evidence`, see there.
    p_append.add_argument("--evidence", default="recollection")

    p_log = sub.add_parser("log", help="print the chronicle")
    p_log.add_argument("--from", dest="from_id", type=int, default=1)
    p_log.add_argument("--limit", type=int, default=50)

    sub.add_parser("verify", help="check the chain")

    p_show = sub.add_parser("show", help="show one event with its units")
    p_show.add_argument("event_id", type=int)

    args = parser.parse_args(argv)

    # One branch per command instead of all four command bodies in one
    # function (a find against the extract): its `main` measured a cyclomatic
    # complexity of 13 against a threshold of 10 (`C901`, this project's ruff
    # selection) — a real gate violation, not a matter of taste. The split
    # changes no behaviour, only the structure.
    try:
        if args.command == "append":
            return _cmd_append(args)
        if args.command == "log":
            return _cmd_log(args)
        if args.command == "verify":
            return _cmd_verify()
        if args.command == "show":
            return _cmd_show(args)
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

    # Unreachable: `add_subparsers(..., required=True)` makes `parse_args`
    # fail without one of the four commands before this code runs —
    # `args.command` is always one of "append", "log", "verify", "show" here.
    # Needed nonetheless, so that `main` returns an `int` on every path and
    # not `None`.
    return 2  # pragma: no cover
