# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The minimal submission path ({ref}`cli-reference`).

Not meant as a product surface, but so that stage 1a **runs** — not because
that is useful, but because being runnable drives out things one otherwise
forgets.
"""

from collections.abc import Callable
from collections.abc import Generator
from contextlib import contextmanager
from contextlib import ExitStack
from dataclasses import dataclass
from dataclasses import replace
from datetime import date
from datetime import datetime
from datetime import UTC
from pathlib import Path
from previously.connectors.imap import ImapConnector
from previously.connectors.imap import ImapError
from previously.connectors.imap import MailboxUnreachable
from previously.connectors.imap import PORT as IMAP_PORT
from previously.contract.types import BlobRef
from previously.contract.types import Evidence
from previously.contract.types import RawEvent
from previously.core.access import read_access
from previously.core.anchor import format_anchor
from previously.core.anchor import parse_anchors
from previously.core.append import append
from previously.core.append import check_units
from previously.core.assertion import assertion_problem
from previously.core.assertion import changes
from previously.core.assertion import DECISION
from previously.core.assertion import DECISION_STATES
from previously.core.assertion import DecisionBody
from previously.core.assertion import DIRECT
from previously.core.assertion import OBLIGATION
from previously.core.assertion import OBLIGATION_STATES
from previously.core.assertion import ObligationBody
from previously.core.assertion import OPEN
from previously.core.assertion import OPERATOR
from previously.core.assertion import overdue
from previously.core.assertion import parse_statement
from previously.core.assertion import payload_of
from previously.core.assertion import reference_problem
from previously.core.assertion import REJECTION
from previously.core.assertion import Source as AssertionSource
from previously.core.assertion import Statement as AssertionStatement
from previously.core.assertions import ASSERTION
from previously.core.assertions import read_threads
from previously.core.assertions import source_identities
from previously.core.assertions import thread_circles
from previously.core.assertions import write_statements
from previously.core.blob import fetch_blob
from previously.core.blob import store_blob
from previously.core.chain import read_references
from previously.core.clients import add_client
from previously.core.clients import client_rows
from previously.core.clients import revoke_client
from previously.core.clients import token_hash
from previously.core.errors import AddressMismatch
from previously.core.errors import ArtifactChanged
from previously.core.errors import BatchTooLarge
from previously.core.errors import CannotOpen
from previously.core.errors import InvalidPayload
from previously.core.errors import PreviouslyError
from previously.core.errors import reason_of
from previously.core.errors import RedactionRefused
from previously.core.errors import SinkUnwritable
from previously.core.errors import SourceUnreadable
from previously.core.gaps import gaps
from previously.core.hashing import is_address
from previously.core.hashing import iso_utc
from previously.core.identity import artifact_hash_of
from previously.core.ingest import ingest
from previously.core.policy import Circle
from previously.core.policy import Client
from previously.core.policy import Inference
from previously.core.policy import key_of
from previously.core.policy import LOCAL_ONLY
from previously.core.policy import Membership
from previously.core.policy import normalized
from previously.core.policy import OwnIdentity
from previously.core.policy import PolicyRefused
from previously.core.policy import Provider
from previously.core.policy import read_policy
from previously.core.policy import refusal
from previously.core.policy import Rule
from previously.core.policy import set_policy
from previously.core.policy import to_payload
from previously.core.projection import catch_up
from previously.core.projection import CHRONICLE
from previously.core.projection import Outcome
from previously.core.projection import PROJECTIONS
from previously.core.projection import SOURCE_STATS
from previously.core.redact import redact_blob
from previously.core.redact import redact_event
from previously.core.redact import redact_units
from previously.core.redaction import blob_erasure
from previously.core.redaction import read_index
from previously.core.sealing import check_recipient
from previously.core.units import normalize_line_endings
from previously.core.units import split_plaintext
from previously.core.verify import BlobCheck
from previously.core.verify import examine
from previously.gate.gate import call
from previously.gate.gate import explain
from previously.gate.prices import load_prices
from previously.gate.tasks.mail_overview import MAIL_OVERVIEW
from previously.storage.errors import StorageError
from previously.storage.keys import DirectoryKeys
from previously.storage.migrate import migrate
from previously.storage.migrate import Migrated
from previously.storage.postgres import from_dsn
from previously.storage.postgres import PostgresStorage
from previously.storage.s3 import from_settings
from previously.storage.s3 import S3BlobStore
from typing import cast
from typing import TYPE_CHECKING

import argparse
import io
import ipaddress
import json
import mimetypes
import os
import re
import signal
import ssl
import sys
import tempfile


if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping
    from collections.abc import Sequence
    from previously.contract.blobs import BlobStore
    from previously.contract.blobs import KeyProvider
    from previously.contract.rows import EventRow
    from previously.contract.types import Anchor
    from previously.core.assertion import Thread
    from previously.core.assertion import Version
    from previously.core.decide import Decision
    from previously.core.policy import Policy
    from previously.core.policy import Statement
    from previously.core.redact import Redacted
    from previously.core.redaction import Redaction
    from previously.core.redaction import RedactionIndex
    from previously.core.verify import Examination
    from previously.core.verify import Finding
    from previously.gate.adapters import Adapter
    from previously.gate.gate import Called
    from sqlalchemy import Connection
    from types import FrameType
    from typing import BinaryIO

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

    Every other control character comes out as `\\xNN` (`escape_controls`),
    after the backslash, so the mapping stays reversible.

    Public rather than `_escape` because a test calls it directly, and a
    direct test earns a public name instead of a suppressed private-usage
    warning.
    """
    escaped = (
        text.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")
    )
    return escape_controls(escaped)


# Every C0 control character but tab and line feed, DEL, and every C1
# control character (U+0080 to U+009F).
_CONTROLS = re.compile("[\x00-\x08\x0b-\x1f\x7f-\x9f]")

# What `json.dumps` leaves raw with `ensure_ascii=False`: it escapes every
# character below U+0020 itself, DEL and C1 not.
_JSON_CONTROLS = re.compile("[\x7f-\x9f]")


def escape_controls(text: str) -> str:
    """`text` with every control character but tab and line feed as `\\xNN`,
    for output a person reads on a terminal.

    Since `ingest`, what the reading commands print is written by strangers:
    a subject, a mail's text, a Message-ID. A terminal takes ESC and its
    sequences as commands: an OSC sequence such as `ESC]0;title BEL` sets
    the window title, OSC 52 the clipboard, and `ESC[2J` clears the screen.
    Measured on 2026-10-06, `show` printed both from a unit raw before this
    function existed. C1 characters are the same commands in one character,
    U+009B for `ESC[`, and DEL is no character to read. The log holds the
    text unchanged.

    Public because a test calls it directly, as for `escape_field`.
    """
    return _CONTROLS.sub(lambda match: f"\\x{ord(match.group()):02x}", text)


def _json_line(payload: Mapping[str, object]) -> str:
    """The payload as one line of JSON, with sorted keys, and DEL and the
    C1 controls as `\\u00NN`, which is JSON for the same character: the line
    stays valid JSON and says the same, and no control reaches a terminal
    raw."""
    line = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return _JSON_CONTROLS.sub(lambda match: f"\\u{ord(match.group()):04x}", line)


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


def _dsn() -> str:
    """`PREVIOUSLY_DSN`, or the error that says it is not set."""
    dsn = os.environ.get("PREVIOUSLY_DSN")
    if not dsn:
        raise PreviouslyError("PREVIOUSLY_DSN is not set")
    return dsn


@contextmanager
def _storage() -> Generator[PostgresStorage]:
    """The storage a command works with, closed when the command is done,
    whether it returns or raises.

    Creating the engine itself stands in `storage.postgres.from_dsn` — `cli`
    knows neither SQLAlchemy nor a driver URL, only the environment variable
    (ruling T9-a of the 2026-10-02 stage 1a plan, whose ledger is lost, so
    the label resolves nowhere and this sentence is the reason). Closing it
    is `PostgresStorage.close`: `main` may run many times in one process, and
    a storage left open keeps its connections until the garbage collector
    finds it.
    """
    storage = from_dsn(_dsn())
    try:
        yield storage
    finally:
        storage.close()


# --- The blob settings ({ref}`blobs`) -----------------------------------------
#
# Read from the environment like the DSN, handed on as text, and each read
# only by a command that needs it: a command that touches no blob reads none
# of them, so a deployment without a blob store runs every other command as
# before.


def _setting(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise PreviouslyError(f"{name} is not set")
    return value


# --- Addresses ({ref}`configuration-reference`) --------------------------------
#
# A host and its port stand in one setting, `…_ADDRESS`, and never in a setting
# that ends in `_PORT` or `_HOST`. Kubernetes gives every container of a
# namespace variables named after each Service in it: `X_SERVICE_HOST`,
# `X_SERVICE_PORT`, `X_PORT` and `X_PORT_<n>_<PROTO>` with `_PROTO`, `_PORT`
# and `_ADDR` after it, as the Kubernetes documentation lists them under
# "Environment variables" on its page "Service", and `X_SERVICE_PORT_<NAME>`
# for every named port, which the kubelet's `FromServices` adds; `X` is the
# Service's name upper-cased, with `-` as `_`. Until 2026-10-11, `serve` read
# `PREVIOUSLY_MCP_PORT`, and a Service named `previously-mcp` set it to
# `tcp://<cluster IP>:8765` in the tools pod, where `serve` then refused to
# start. `tests/test_settings.py` holds every name the source reads against
# those patterns.

# A host name as `PREVIOUSLY_DSN` takes one: labels of 1 to 63 characters, an
# optional final dot. An empty label is refused here for the reason the DSN
# refuses it (`storage/postgres.py`): measured on 2026-10-11,
# `imaplib.IMAP4_SSL("a..b", 993)` raises `UnicodeEncodeError` out of the
# `idna` codec, which no handler of `ingest` catches, so the run would end in
# a traceback.
_HOST_LABEL = r"[A-Za-z0-9_\-]{1,63}"
_ADDRESS = re.compile(
    rf"(?:(?P<name>{_HOST_LABEL}(?:\.{_HOST_LABEL})*\.?)|\[(?P<ipv6>[0-9A-Fa-f:.]+)\])"
    r"(?::(?P<port>[0-9]{1,5}))?"
)


def parse_address(name: str, text: str, *, default_port: int | None) -> tuple[str, int]:
    """The host and the port of the setting `name`, whose value is `text`.

    The host is a host name, an IPv4 address, or an IPv6 address in brackets,
    and comes back without the brackets, as a socket takes it. The port is a
    number from 1 to 65535; `default_port` is the port where the address may
    leave it out, and `None` where it may not.

    The refusal quotes the value from its last `@` on. An address holds no
    `@`, and the likely mistake that puts one there is a URL with a user and
    a password in front of the host, such as `imaps://user:password@host`;
    the setting stands beside the password in the same secret, and a value
    quoted whole would print it. What is left can still hold a secret
    written anywhere else in the value, as any quotation of a mistyped
    setting can.

    Public because a test calls it directly, as for `escape_field`.
    """
    # Two sentences written out rather than one with the form interpolated:
    # `tests/test_docs_references.py` holds the pages' quotations against the
    # literal parts, and an interpolated form would let any wording pass.
    _before, at, after = text.rpartition("@")
    shown = f"…@{after}" if at else text
    if default_port is None:
        refusal = PreviouslyError(
            f"{name} is not host:port, with an IPv6 host in brackets: {shown!r}"
        )
    else:
        refusal = PreviouslyError(
            f"{name} is not host or host:port, with an IPv6 host in brackets: {shown!r}"
        )
    match = _ADDRESS.fullmatch(text)
    if match is None:
        raise refusal
    host = match["name"]
    if host is None:
        try:
            ipaddress.IPv6Address(match["ipv6"])
        except ValueError:
            raise refusal from None
        host = match["ipv6"]
    if match["port"] is None:
        if default_port is None:
            raise refusal
        return host, default_port
    port = int(match["port"])
    if not 0 < port < 65536:
        raise refusal
    return host, port


@contextmanager
def _blob_store() -> Generator[S3BlobStore]:
    """The blob store out of its five variables, the first missing one
    named, closed when the command is done, whether it returns or raises —
    for the reason `_storage` closes the database: `S3BlobStore.close` has
    the measurement."""
    store = from_settings(
        endpoint=_setting("PREVIOUSLY_BLOB_ENDPOINT"),
        region=_setting("PREVIOUSLY_BLOB_REGION"),
        bucket=_setting("PREVIOUSLY_BLOB_BUCKET"),
        access_key=_setting("PREVIOUSLY_BLOB_ACCESS_KEY"),
        secret_key=_setting("PREVIOUSLY_BLOB_SECRET_KEY"),
    )
    try:
        yield store
    finally:
        store.close()


def _recipient() -> str:
    """The recipient new blobs are sealed to, checked before anything is
    stored: `store_blob` seals only content the store does not hold yet, so
    a mistyped recipient would otherwise pass until new content arrives."""
    recipient = _setting("PREVIOUSLY_BLOB_RECIPIENT")
    check_recipient(recipient)
    return recipient


def _identities() -> DirectoryKeys:
    """The directory of identities that open what was sealed.

    A setting that names no directory is a configuration error, said as
    one. `DirectoryKeys` answers "no identity" for every key out of a
    directory that does not exist, so `verify --blobs` reported every blob
    as one that cannot be opened, with exit code 1, which reads as a lost
    key on a freshly restored machine. An existing directory without the
    identity for one key stays what it is: a finding about that blob.
    """
    directory = _setting("PREVIOUSLY_BLOB_IDENTITIES")
    if not Path(directory).is_dir():
        raise PreviouslyError(f"PREVIOUSLY_BLOB_IDENTITIES is not a directory: {directory}")
    return DirectoryKeys(directory)


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
        raise InvalidPayload(f"cannot read {name}: {reason_of(error)}") from error
    except UnicodeDecodeError as error:
        raise InvalidPayload(f"{name} is not UTF-8 text") from error
    return parse_anchors(io.StringIO(text, newline=None))


def _migrated_line(result: Migrated) -> str:
    """The one line `migrate` prints on standard output."""
    if result.before == result.head:
        return f"up to date: {result.head}"
    return f"migrated: {result.before or '(empty)'} -> {result.head}"


def _cmd_migrate(_args: argparse.Namespace) -> int:
    """Brings the database schema up to the newest revision
    ({ref}`cli-reference`). `UnknownRevision` is a `StorageError` and ends
    in `main`'s one sentence like every other."""
    print(_migrated_line(migrate(_dsn())))
    return 0


def _append_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source", required=True)
    parser.add_argument("--external-id", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--occurred-at")
    # The default "recollection": the cautious assumption, and a submission by
    # hand is mostly exactly that (review finding G3). No `choices=` — the
    # invalid case is translated in `_parse_evidence`, see there.
    parser.add_argument("--evidence", default="recollection")
    parser.add_argument(
        "--attach",
        action="append",
        default=[],
        metavar="FILE",
        help="a file to store as a blob and name at the event; may be given more than once",
    )


# Python's own table and nothing else. A `MimeTypes()` fills its own maps from
# the table built into the `mimetypes` module, and from a file only when it is
# given one; the module functions consult the system's `mime.types` as well.
# Constructing the instance does run the module's `init()`, which reads those
# files into the module's maps, but the instance does not look there.
# Measured on 2026-10-05 with an extension known only to a file passed to
# `mimetypes.init`: the module function found it, the instance did not. The
# media type stands in the event hash for good, so it must not depend on the
# machine that attached the file.
_MEDIA_TYPES = mimetypes.MimeTypes()
_OCTET_STREAM = "application/octet-stream"


def media_type_of(name: str) -> str:
    """The media type a file's name suggests, or `application/octet-stream`.

    From the name only: guessing from the content is what the specification
    rules out. A name with a compression suffix (`.gz`, `.bz2`, …) gives the
    type of what is inside, `application/x-tar` for `.tar.gz`, which is not
    the type of the bytes stored, so it counts as no answer.

    Public because a test calls it directly.
    """
    media_type, encoding = _MEDIA_TYPES.guess_file_type(name)
    if media_type is None or encoding is not None:
        return _OCTET_STREAM
    return media_type


def _attach(paths: Sequence[str]) -> tuple[BlobRef, ...]:
    """Stores every attachment as a blob and returns the references to them
    ({ref}`blobs`).

    Every file is opened before the first is stored, so that one that cannot
    be read stores nothing and appends nothing. A file is read twice — once
    to hash, once to seal — so something that can be read only once, a pipe,
    is refused with the files that cannot be opened. What is stored stays
    when the append after it fails: a blob no event names, which nothing
    reads.

    `filename` is the name without its directory: where the file lay on the
    machine that attached it says nothing about the content, and it would
    stand in the event hash for good.
    """
    recipient = _recipient()
    with ExitStack() as files, _blob_store() as store:
        handles: list[BinaryIO] = []
        for path in paths:
            try:
                handle = files.enter_context(open(path, "rb"))
            except OSError as error:
                raise InvalidPayload(
                    f"cannot read the attachment {path}: {reason_of(error)}"
                ) from error
            if not handle.seekable():
                raise InvalidPayload(f"cannot read the attachment {path}: it cannot be read twice")
            handles.append(handle)
        references: list[BlobRef] = []
        for path, handle in zip(paths, handles, strict=True):
            # A file that opened can still fail to read, a disk that gives
            # out among them: `core` says that it was the content, and only
            # this function knows which file it was.
            try:
                stored = store_blob(store, handle, recipient=recipient)
            except SourceUnreadable as error:
                raise InvalidPayload(
                    f"cannot read the attachment {path}: {error.reason}"
                ) from error
            name = Path(path).name
            references.append(
                BlobRef(stored.address, stored.size, media_type_of(name), filename=name)
            )
    return tuple(references)


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
    evidence = _parse_evidence(args.evidence)
    units = split_plaintext(args.text)
    # Before the text is hashed into the artifact identity below: the
    # canonical form would refuse a null byte or a lone surrogate there too,
    # but as `$.text` of a document nothing stores, where this names the unit.
    check_units(units)
    # The database setting before anything is stored: `_storage` refuses an
    # unset `PREVIOUSLY_DSN` without connecting, and a blob stored before that
    # refusal would lie in the bucket with no event to name it. Then the
    # blobs, then the event ({ref}`blobs`), and the blob settings only when
    # there is something to attach.
    with _storage() as storage:
        blobs = _attach(args.attach) if args.attach else ()
        # The artifact is what was submitted: the text with its line endings
        # as LF, and the attachments by their addresses, sorted, so that their
        # order on the command line and their file names do not make another
        # artifact ({ref}`artifact-identity`). Not the units, which are
        # derived. The line endings the way `split_plaintext` reads them: the
        # same text pasted from a Windows clipboard, with CRLF, gives the same
        # units, and would otherwise be refused under its own key as another
        # content.
        artifact = {
            "text": normalize_line_endings(args.text),
            "attachments": sorted(blob.sha256 for blob in blobs),
        }
        event = RawEvent(
            source=args.source,
            external_id=args.external_id,
            occurred_at=occurred,
            evidence=evidence,
            units=units,
            blobs=blobs,
            artifact_hash=artifact_hash_of(artifact),
        )
        ids = append(storage, [event], recorded_at=datetime.now(UTC))
    print(ids[0])
    return 0


# --- Taking in mail ({ref}`cli-reference`) -------------------------------------


def _ingest_arguments(parser: argparse.ArgumentParser) -> None:
    # A second level, like `blob`: the source is a word of its own, and the
    # next connector is the next word beside it.
    sources = parser.add_subparsers(dest="source", required=True)
    sentence = "take in the mail IMAP folders hold above the watermark of the last run"
    imap = sources.add_parser("imap", help=sentence, description=sentence)
    imap.add_argument(
        "--folder",
        action="append",
        metavar="NAME",
        help="a folder to read, by its full name; repeatable, and in place of "
        "PREVIOUSLY_IMAP_FOLDER",
    )


def _imap_address() -> tuple[str, int]:
    """`PREVIOUSLY_IMAP_ADDRESS`, with the port of IMAP over TLS where it
    names none. The host is what the certificate is checked against, and
    what the name of the watermark carries."""
    # `PREVIOUSLY_IMAP_HOST` and `PREVIOUSLY_MCP_HOST` held the host until
    # 2026-10-11, and are read now only to be refused where the address is
    # unset: a deployment of the release before would otherwise run on
    # without the host it named, and `serve` would listen on the loopback
    # address inside its pod, with nothing to say why no probe reaches it.
    # Kubernetes never sets a name that ends in `_HOST` without `_SERVICE`
    # before it. The old `_PORT` is never read, not even for this: Kubernetes
    # sets it.
    text = os.environ.get("PREVIOUSLY_IMAP_ADDRESS")
    if not text:
        if os.environ.get("PREVIOUSLY_IMAP_HOST"):
            raise PreviouslyError(
                "PREVIOUSLY_IMAP_HOST is not read any more: "
                "set PREVIOUSLY_IMAP_ADDRESS to host or host:port"
            )
        raise PreviouslyError("PREVIOUSLY_IMAP_ADDRESS is not set")
    return parse_address("PREVIOUSLY_IMAP_ADDRESS", text, default_port=IMAP_PORT)


def _imap_connectors(named: Sequence[str] | None) -> list[ImapConnector]:
    """One connector per folder, out of the folder's settings, read before
    anything connects: `--folder` as given, each name once and in the order
    first given, or `PREVIOUSLY_IMAP_FOLDER` without it. Read in the order
    `PREVIOUSLY_IMAP_ADDRESS`, `…_USER`, `…_PASSWORD`, `…_FOLDER`, as before
    `--folder` existed; with it, the folder setting is not read at all.

    One mailbox, one password: several mailboxes are several runs, each with
    the settings of its own.

    The certificate is verified against the system's trust store, and so is
    the host name: `ssl.create_default_context()`, with no setting that turns
    it off. A server with a certificate of its own is trusted the way
    OpenSSL trusts anything, through `SSL_CERT_FILE` or the trust store, not
    through a switch of this command.
    """
    # Refused here rather than sent: an empty name is no folder, and the
    # setting refuses an empty value the same way.
    if named is not None and "" in named:
        raise PreviouslyError("--folder must not be empty")
    host, port = _imap_address()
    user = _setting("PREVIOUSLY_IMAP_USER")
    password = _setting("PREVIOUSLY_IMAP_PASSWORD")
    folders = named if named is not None else [_setting("PREVIOUSLY_IMAP_FOLDER")]
    context = ssl.create_default_context()
    return [
        ImapConnector(
            host=host, port=port, user=user, password=password, folder=folder, ssl_context=context
        )
        for folder in dict.fromkeys(folders)
    ]


def _cmd_ingest(args: argparse.Namespace) -> int:
    """Takes in what each folder holds above its watermark ({ref}`cli-reference`).

    Every setting is read, and the recipient checked, before anything
    connects: the mailbox's address, user and password, the folder setting
    unless `--folder` names the folders, the recipient, `PREVIOUSLY_DSN` and
    the store's five, in that order. The directory of identities is not
    among them: taking in seals and opens nothing.

    The folders are read one after the other, each over a connection of its
    own: `ImapConnector.fetch` connects, logs in and logs out again, so a
    connection that breaks off in one folder is that folder's, and the next
    folder connects anew. Standard output is one line per folder that was
    read, the counts and the UID the watermark stands at, and the folder;
    `up to uid 0` is a folder that has given nothing yet, since a UID is
    never 0. Each variant is one line on standard error. The projections are
    not caught up: `project` does that, and the two may run side by side.

    A folder that fails is one line on standard error that names it, and
    the run goes on with the next folder and returns 2 at the end. A
    failure is the folder's when it comes from that folder alone: the server
    refuses to open it, to search it or to fetch from it, the connection
    breaks off while it is read, or the log refuses a mail of it, for too
    many events or a variant key held with another content. The last two
    come back at every run until the mail leaves the folder, and would
    otherwise keep every folder after it from being read.

    What every folder would meet alike stops the run at once, with the one
    sentence a run of a single folder prints: a `MailboxUnreachable` — the
    server out of reach, a certificate that does not verify, a login refused
    — and an error of the database or the blob store. Going on would only
    repeat it, and for a refused login that is one more refused login at
    the server for each folder.
    """
    connectors = _imap_connectors(args.folder)
    recipient = _recipient()
    failed = False
    with _storage() as storage, _blob_store() as store:
        for connector in connectors:
            # The folder is the operator's, but it is printed the way every
            # field from outside is: one line, and no control raw.
            folder = escape_field(connector.folder)
            try:
                result = ingest(
                    storage,
                    storage,
                    store,
                    connector,
                    recipient=recipient,
                    recorded_at=datetime.now(UTC),
                )
            except MailboxUnreachable:
                raise
            except (ImapError, BatchTooLarge, ArtifactChanged) as error:
                print(f"Error: folder {folder}: {escape_controls(str(error))}", file=sys.stderr)
                failed = True
                continue
            # The Message-ID is the mail's, so it is escaped like a field of
            # `chronicle`: one line per variant, and no control reaches the
            # terminal.
            for message_id, event_id in result.variants:
                print(f"variant of {escape_field(message_id)}: event {event_id}", file=sys.stderr)
            uid = "0" if result.position is None else result.position["uid"]
            print(
                f"imap: {result.appended} appended, {result.known} known, "
                f"{len(result.variants)} variants, up to uid {uid} in {folder}"
            )
    return 2 if failed else 0


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
    # The reading methods take the connection in since review finding G4: the
    # transaction boundary belongs to the caller, who knows what has to be
    # read together. Here that is a formality. `show` reads an event and its
    # units in one transaction, but in two statements, which under the READ
    # COMMITTED of `begin` are two snapshots. It still shows one state, and
    # not because of a snapshot: `insert_event` writes an event and its units
    # in the one transaction of `append`, so they commit together, and
    # nothing in `src` deletes either afterwards, so whoever sees the event
    # sees its units. Since stage 1c one thing rewrites them: an erasure
    # ({ref}`erasure`) turns payload and units into tombstones in one
    # transaction. `show` reads the event, the redactions and the units in
    # three statements, so an erasure that commits between them can show a
    # payload from before it beside units from after it — every row whole,
    # and the next `show` consistent again. That is a display, not a check;
    # `verify` reads in one snapshot.
    with _storage() as storage, storage.begin() as conn:
        for row in storage.read(conn, from_id=args.from_id, limit=args.limit):
            print(f"{row.id}\t{row.occurred_at.isoformat()}\t{row.kind}\t{row.hash.hex()[:12]}")
    return 0


def _verify_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--anchors", metavar="FILE", help="anchor lines to check against; - reads standard input"
    )
    parser.add_argument("--exact", action="store_true", help="the tip has to be the newest anchor")
    parser.add_argument(
        "--blobs", action="store_true", help="also read every blob in the store and check it"
    )


def _examine(
    storage: PostgresStorage,
    anchors: Sequence[Anchor],
    *,
    exact: bool,
    blobs: bool,
    before_blobs: Callable[[Sequence[Finding]], None],
) -> Examination:
    """The one pass, and with `blobs` the check of the blob store after it
    ({ref}`blobs`). The store is built once, every blob is fetched through
    it, and it is closed whether the pass returns or raises. Its settings
    are read only with `blobs`."""
    if not blobs:
        return examine(storage, anchors=anchors, exact=exact, before_blobs=before_blobs)
    keys = _identities()
    with _blob_store() as store:
        return examine(
            storage,
            anchors=anchors,
            exact=exact,
            blobs=BlobCheck(store, keys),
            before_blobs=before_blobs,
        )


def _print_findings(findings: Sequence[Finding]) -> None:
    for finding in findings:
        print(f"FINDING {finding.event_id}: {finding.reason}")


def _cmd_verify(args: argparse.Namespace) -> int:
    # Refused before the database is asked for: there is nothing `--exact`
    # could compare the tip with.
    if args.exact and args.anchors is None:
        raise InvalidPayload("--exact needs --anchors")
    anchors = () if args.anchors is None else _read_anchors(args.anchors)
    # The findings of the chain are printed as soon as the pass is done,
    # before the blobs are checked: a check of the blobs that ends in an
    # error, a store that does not answer, leaves `_examine` without an
    # `Examination`, and the error must not take a forgery report with it.
    # Those findings head `examination.findings`, so only the rest, the
    # blobs' own, is printed after it.
    chain: list[Finding] = []

    def report(findings: Sequence[Finding]) -> None:
        _print_findings(findings)
        chain.extend(findings)

    with _storage() as storage:
        examination = _examine(
            storage, anchors, exact=args.exact, blobs=args.blobs, before_blobs=report
        )
    # The count of blobs closes the line, after whatever the anchors said.
    count = examination.blobs_checked
    matched = f", {_plural(count, 'blob')} {'matches' if count == 1 else 'match'}"
    blob_tail = matched if args.blobs else ""
    _print_findings(examination.findings[len(chain) :])
    if examination.findings:
        return 1
    if not anchors:
        # Standard output stays the one line scripts read. The limit of the
        # statement goes to standard error, the way `chronicle` reports its
        # lag ({ref}`external-anchor`): without an anchor the chain attests
        # "unchanged" and nothing about "complete". Only on an intact chain —
        # beside findings the sentence would be noise.
        print(f"chain intact{blob_tail}")
        print(
            "no anchor given: verify attests that the log is unchanged, "
            "not that it is complete; see `previously anchor`",
            file=sys.stderr,
        )
        return 0
    count = len(anchors)
    held = f"{_plural(count, 'anchor')} {'holds' if count == 1 else 'hold'}"
    tail = ", the tip is the newest anchor" if args.exact else ""
    print(f"chain intact, {held}{tail}{blob_tail}")
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
    with _storage() as storage:
        examination = examine(storage)
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
    with _storage() as storage, storage.begin() as conn:
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
            # `payload=<erased by event …>` says that instead of printing an
            # empty line, naming the redaction that ordered it ({ref}`erasure`).
            #
            # `evidence=` only where the payload carries the key: `append`
            # mixes it into every observation, and an action has none, so
            # `evidence=None` would be a statement nobody made.
            index = read_index(storage, conn)
            if row.payload is None:
                print(f"payload={_erased(index.of_event(row.id))}")
            else:
                if "evidence" in row.payload:
                    print(f"evidence={row.payload['evidence']}")
                # `sort_keys` so the output is stable across runs: `payload`
                # comes back out of jsonb, and the order of keys in jsonb is
                # not the order they were written in.
                print(f"payload={_json_line(row.payload)}")
            for unit in storage.units(conn, row.id):
                # An erased unit says so, like the payload above, rather than
                # printing `None` where its text stood.
                content = unit.content
                # A unit keeps its line breaks here, unlike in `chronicle`,
                # and loses every other control character (`escape_controls`).
                if content is None:
                    content = _erased(index.of_unit(row.id, unit.seq))
                print(f"  ¶{unit.seq} {escape_controls(content)}")
            for line in _blob_lines(row, index):
                print(line)
            return 0
    print(f"No event {args.event_id}", file=sys.stderr)
    return 1


def _blob_lines(row: EventRow, index: RedactionIndex) -> list[str]:
    """One line per reference the payload names, in its order, out of the
    log alone: `show` does not ask the blob store whether the blob is there
    ({ref}`blobs`). A reference a redaction erased names it at the end of
    its line ({ref}`erasure`).

    Name and media type pass through `escape_field`, so that a newline in a
    file's name cannot end the line. A payload whose list does not have its
    form prints no line; `verify` reports it.

    An erased payload took size, media type and name with it, so the blobs
    of an erased event come from its redaction, the hash alone; without a
    redaction there is no list to print, and `verify` reports the tombstone.
    """
    if row.payload is None:
        redaction = index.of_event(row.id)
        named = () if redaction is None else redaction.blobs
        return [
            f"  blob {sha256} {_erased(index.of_reference(row.id, sha256))}" for sha256 in named
        ]
    lines: list[str] = []
    for reference in read_references(row.payload) or ():
        line = (
            f"  blob {reference.sha256} {reference.size} {escape_field(reference.media_type)} "
            f"{'-' if reference.filename is None else escape_field(reference.filename)}"
        )
        by = index.of_reference(row.id, reference.sha256)
        lines.append(line if by is None else f"{line} {_erased(by)}")
    return lines


def _blob_arguments(parser: argparse.ArgumentParser) -> None:
    # A second level, like `redact`: what is done with a blob is a word of its
    # own.
    actions = parser.add_subparsers(dest="action", required=True)
    get = actions.add_parser("get", help="fetch a blob, open it, check it and write it to a file")
    get.add_argument("address", metavar="HASH", help="the SHA-256 of the content, in hex")
    get.add_argument("--output", required=True, metavar="FILE", help="where to write the content")


def _fetch_to(store: BlobStore, keys: KeyProvider, address: str, target: str) -> int | None:
    """Fetches the blob into `target` and returns its size, or `None` when
    the store has no object; on every error, `target` is as it was.

    `fetch_blob` writes before it knows whether the address holds, so it
    writes into a temporary file in the target's directory, and only a fetch
    that returned is renamed onto the target — in one step, since a rename
    within one directory is atomic. Every other way out removes the
    temporary file. `mkstemp` creates it readable by its owner only, and the
    rename keeps that ({ref}`blobs`).
    """
    directory = Path(target).absolute().parent
    try:
        descriptor, part = tempfile.mkstemp(dir=directory, prefix=".previously-", suffix=".part")
    except OSError as error:
        raise InvalidPayload(f"cannot write {target}: {reason_of(error)}") from error
    kept = False
    try:
        # Unbuffered, so that a write that fails does so inside `fetch_blob`,
        # where `unseal` names it, and not at the close, after `fetch_blob`
        # has returned a size. Measured on 2026-10-05 with a file size limit:
        # buffered, `test_blob_get_whose_output_cannot_be_written_leaves_nothing`
        # stayed green with the translation of `SinkUnwritable` below taken
        # out, so the failure had come from the flush at the close.
        with os.fdopen(descriptor, "wb", buffering=0) as sink:
            size = fetch_blob(store, keys, address, sink)
        if size is not None:
            os.replace(part, target)
            kept = True
    except SinkUnwritable as error:
        # A write into the temporary file failed while the content passed
        # through; `fetch_blob` returns no size then.
        raise InvalidPayload(f"cannot write {target}: {error.reason}") from error
    except OSError as error:
        # Closing the temporary file, or renaming it onto the target.
        raise InvalidPayload(f"cannot write {target}: {reason_of(error)}") from error
    finally:
        if not kept:
            os.unlink(part)
    return size


def _cmd_blob_get(args: argparse.Namespace) -> int:
    """Fetches one blob, opens it, checks its address and writes it to a
    file ({ref}`blobs`). Standard output says how much was written, never the
    bytes."""
    address: str = args.address
    # The command line checks the address before anything is read or asked,
    # as an input error; the store's own refusal, in the same words, is a
    # second line and raises a bare `ValueError` this command does not catch.
    if not is_address(address):
        raise InvalidPayload(
            f"{address} is not a blob address: 64 hexadecimal characters, lower case"
        )
    # The log first: whether any event uses the blob, and whether its
    # references are all erased, are answers about the log, given whether or
    # not an object lies in the store ({ref}`erasure`). The blob settings are
    # read only once there is something to fetch, so both answers come on a
    # machine that has none.
    with _storage() as storage, storage.begin() as conn:
        users = storage.events_by_blob(conn, bytes.fromhex(address))
        erasure = blob_erasure(read_index(storage, conn), address, users)
    if not users:
        print(f"no event uses blob {address}", file=sys.stderr)
        return 1
    if erasure is not None:
        print(f"blob {address} is erased (event {erasure.id})", file=sys.stderr)
        return 1
    keys = _identities()
    with _blob_store() as store:
        try:
            size = _fetch_to(store, keys, address, args.output)
        except AddressMismatch as error:
            raise PreviouslyError(
                f"blob {address} does not match its address; nothing was written"
            ) from error
        except CannotOpen as error:
            raise PreviouslyError(f"blob {address} cannot be opened: {error}") from error
    if size is None:
        raise PreviouslyError(f"blob {address} is not in the store")
    print(f"wrote {size} bytes to {args.output}")
    return 0


def _erased(by: Redaction | None) -> str:
    """How `show` prints what is missing: with the redaction that ordered
    it, or bare when none did — a tombstone without an order, which `verify`
    reports."""
    return "<erased>" if by is None else f"<erased by event {by.id}>"


def _redact_arguments(parser: argparse.ArgumentParser) -> None:
    # The first command with a second level: what is erased is a word of its
    # own, `event`, `units` or `blob`, each with its own arguments.
    #
    # Each sentence is both the `help` and the `description`: argparse prints
    # `help` only in the list of `previously redact --help`, and `description`
    # only in the form's own `--help`, which is where somebody about to erase
    # looks.
    targets = parser.add_subparsers(dest="target", required=True)

    def form(name: str, sentence: str) -> argparse.ArgumentParser:
        return targets.add_parser(name, help=sentence, description=sentence)

    event = form("event", "erase the payload and the content of every unit")
    event.add_argument("event_id", type=int)
    event.add_argument("--reason", required=True, help="why; it stays in the log for good")
    units = form("units", "erase the content of the named units; the payload of the event stays")
    units.add_argument("event_id", type=int)
    units.add_argument("seqs", type=int, nargs="+", metavar="SEQ")
    units.add_argument("--reason", required=True, help="why; it stays in the log for good")
    blob = form("blob", "erase a blob for every event that uses it")
    blob.add_argument("address", metavar="HASH", help="the SHA-256 of the content, in hex")
    blob.add_argument("--reason", required=True, help="why; it stays in the log for good")


def _redacted_line(result: Redacted) -> str:
    """The one line `redact` prints on standard output."""
    if result.written:
        return f"redacted by event {result.redaction_id}"
    return f"already redacted by event {result.redaction_id}"


def _kept_line(address: str, users: Sequence[int]) -> str:
    """The notice for a blob that stays in the store, with the events that
    still use it."""
    ids = ", ".join(str(event_id) for event_id in users)
    if len(users) == 1:
        return f"blob {address} stays in the store: event {ids} still uses it"
    return f"blob {address} stays in the store: events {ids} still use it"


def _payload_line(event_id: int) -> str:
    """The notice for a payload that holds the wording of a unit a redaction
    of units erased.

    `redact units` erases units and nothing else, and the line on standard
    output says the redaction is done. A payload written beside the units can
    hold their wording too, and then it can still be read there after the
    units are erased; this says so, and names the command that erases it,
    rather than leave the line on standard output to read as "the content is
    gone". `append --text` writes none of the text into the payload, only
    what `append` adds — the kind of evidence, the artifact hash, and with
    attachments their names, media types and addresses —, so for an event it
    wrote the notice comes only where the wording of an erased unit equals or
    lies inside one of those values, such as a unit that reads `minutes.txt`
    beside an attachment of that name, or a unit of a few hexadecimal
    characters that the artifact hash happens to contain. The notice is then
    true: the payload holds that wording."""
    return (
        f"the payload of event {event_id} is not erased and holds the wording of an "
        f"erased unit; `previously redact event {event_id}` erases it"
    )


def _unfinished(redaction_id: int, outstanding: str) -> PreviouslyError:
    """The error of a redaction that stands and is not carried out to its
    end: what stands, what is outstanding, and that the same command
    finishes it — the second call finds the target covered, writes nothing,
    and does what is left."""
    return PreviouslyError(
        f"the redaction is recorded as event {redaction_id}, but it is not finished: "
        f"{outstanding}; run the same command again"
    )


def _delete_obsolete(result: Redacted) -> str | None:
    """Deletes from the store every blob the redaction says no longer has
    to lie there ({ref}`erasure`), after its transaction: the store takes
    part in none, and a blob deleted before the redaction stands would be
    gone for a redaction that might still fail. A blob that is gone already
    is no error, so a second call deletes again what the first did.

    The blob settings are read only when there is something to delete, so
    a redaction that touches no blob runs without them. A failure is
    returned, not raised, as what is outstanding: the blobs still to delete,
    with the error that stopped it quoted, so that the catch-up after it
    runs all the same.
    """
    pending = list(result.obsolete_blobs)
    if not pending:
        return None
    try:
        with _blob_store() as store:
            while pending:
                store.delete(pending[0])
                pending.pop(0)
    except (PreviouslyError, StorageError) as error:
        failure = str(error)
    else:
        return None
    if len(pending) == 1:
        outstanding = f"blob {pending[0]} is not deleted from the store ({failure})"
    else:
        outstanding = f"blobs {', '.join(pending)} are not deleted from the store ({failure})"
    return outstanding


def _catch_up_after(storage: PostgresStorage) -> str | None:
    """Brings every projection up to the tip once a redaction is recorded, so
    the chronicle stops showing what was erased without waiting for the next
    `project` ({ref}`projections`).

    A failure here comes after the redaction committed, and is returned as
    what is outstanding, for the caller to say in its one sentence: what
    stands, what does not, and that the same command finishes it — the
    second call finds the target covered, writes nothing and catches up.
    Only the errors `main` turns into a sentence are caught; anything foreign
    goes through as a stack trace, as everywhere else.

    A catch-up that builds a projection from scratch — the first build, or a
    rebuild after a version change — is named on standard error, in the line
    `project` prints for it. `project` names its path so that a rebuild is not
    invisible, and the first `redact` after an upgrade would otherwise rebuild
    without a word, for as long as the log takes. An ordinary catch-up says
    nothing, and standard output stays the one line.
    """
    for projection in PROJECTIONS:
        try:
            outcome = catch_up(storage, storage, projection)
        except (PreviouslyError, StorageError) as error:
            outstanding = f"projection {projection.name} is not caught up ({error})"
            return outstanding
        if outcome.rebuilt_from is not None:
            print(f"{outcome.name:<15} {_describe(outcome)}", file=sys.stderr)
    return None


def _redact(storage: PostgresStorage, args: argparse.Namespace) -> Redacted:
    """The redaction the arguments ask for, in its own transaction."""
    now = datetime.now(UTC)
    if args.target == "event":
        return redact_event(storage, storage, args.event_id, reason=args.reason, recorded_at=now)
    if args.target == "units":
        return redact_units(
            storage, storage, args.event_id, args.seqs, reason=args.reason, recorded_at=now
        )
    return redact_blob(storage, storage, args.address, reason=args.reason, recorded_at=now)


def _cmd_redact(args: argparse.Namespace) -> int:
    """Erases an event, units of it, or a blob ({ref}`erasure`), deletes
    what no longer has to lie in the blob store, then catches the
    projections up.

    No question before it acts: the reason is the brake, and a command that
    asked would be no tool for a script.

    The order is the one the redaction needs, whether it wrote an event or
    found its target covered: the transaction, then the store, then the
    projections, then what is printed. If deleting or catching up fails, the
    redaction stands, and the error says so and what is outstanding; the
    same command again finds the target covered and does what is left.

    Both steps after the transaction are attempted whatever happens to the
    other, and the one sentence names everything outstanding. In either
    fixed order, a step that kept failing would keep the other from ever
    running: a store that is down would leave the chronicle showing what
    was erased, though the catch-up needs only the database.
    """
    # Blanks alone count as empty: a reason that says nothing brakes nothing.
    if not args.reason.strip():
        raise RedactionRefused("--reason must not be empty")
    # An address that is no address is an input error before anything is
    # asked, the database setting included, as in `blob get`; `redact_blob`
    # refuses it in the same words, a second line behind this one.
    if args.target == "blob" and not is_address(args.address):
        raise InvalidPayload(
            f"{args.address} is not a blob address: 64 hexadecimal characters, lower case"
        )
    with _storage() as storage:
        result = _redact(storage, args)
        deletion = _delete_obsolete(result)
        catching_up = _catch_up_after(storage)
    left = [step for step in (deletion, catching_up) if step is not None]
    if left:
        # The units are erased whether or not what follows is finished, and
        # the payload is left as it was either way, so the notice comes beside
        # the sentence of the unfinished redaction too.
        _notice_payload(result, args)
        raise _unfinished(result.redaction_id, ", and ".join(left))
    print(_redacted_line(result))
    for event_id in result.cascaded:
        kind = "assertion" if event_id in result.cascaded_assertions else "model_call"
        print(f"cascaded: {kind} {event_id}")
    for seq in result.skipped_units:
        print(f"unit {seq} was already erased", file=sys.stderr)
    for address, users in result.kept_blobs.items():
        print(_kept_line(address, users), file=sys.stderr)
    _notice_payload(result, args)
    return 0


def _notice_payload(result: Redacted, args: argparse.Namespace) -> None:
    """The notice of `_payload_line`, on standard error, when the payload of
    the target holds the wording of a unit the redaction erased."""
    if result.payload_holds_wording:
        print(_payload_line(args.event_id), file=sys.stderr)


def _cmd_project(_args: argparse.Namespace) -> int:
    # `PROJECTIONS` fixes the order, so two runs print their lines the same way
    # round. `catch_up` gets the same object twice because `PostgresStorage` is
    # both the log it reads and the projection store it writes.
    with _storage() as storage:
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
    with _storage() as storage, storage.begin() as conn:
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
    with _storage() as storage, storage.begin() as conn:
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


# --- The processing policy ----------------------------------------------------


def _policy_arguments(parser: argparse.ArgumentParser) -> None:
    # A second level, like `redact`: which statement is set is a word of its
    # own. Every one that writes takes `--statement`, `--revoke` and `--yes`.
    what = parser.add_subparsers(dest="what", required=True)

    def writing(name: str, sentence: str) -> argparse.ArgumentParser:
        form = what.add_parser(name, help=sentence, description=sentence)
        form.add_argument(
            "--statement", required=True, help="the sentence it was set with; it stays in the log"
        )
        form.add_argument("--revoke", action="store_true", help="lift the statement instead")
        form.add_argument("--yes", action="store_true", help="write without asking")
        return form

    circle = writing("circle", "create a circle")
    circle.add_argument("name")
    member = writing("member", "put an address or a domain into a circle")
    member.add_argument("circle")
    member.add_argument("member", metavar="ADDRESS-OR-@DOMAIN")
    own = writing("own", "name an address or a domain as the operator's own")
    own.add_argument("member", metavar="ADDRESS-OR-@DOMAIN")
    rule = writing("rule", "give a scope its conditions")
    rule.add_argument("scope", help="circle:<name> or source:<source>")
    rule.add_argument("--regions", nargs="+", required=True, metavar="REGION", help="eu, us or any")
    rule.add_argument("--max-retention-days", type=int, help="0 means zero retention")
    rule.add_argument(
        "--exclude-provider", action="append", default=[], metavar="NAME", help="may repeat"
    )
    rule.add_argument(
        "--no-training", action="store_true", help="only providers declared not to train on input"
    )
    rule.add_argument(
        "--no-subprocessors",
        action="store_true",
        help="only providers declared to have no subprocessors",
    )
    rule.add_argument(
        "--exclude-operator", action="append", default=[], metavar="NAME", help="may repeat"
    )
    rule.add_argument(
        "--exclude-model-origin", action="append", default=[], metavar="NAME", help="may repeat"
    )
    provider = writing("provider", "declare what a provider account promises")
    provider.add_argument("name")
    provider.add_argument(
        "--inference",
        action="append",
        default=[],
        metavar="NAME=REGIONS",
        help="a space of inference and what it means, such as global=any or us=us; may repeat",
    )
    # Required, with no value allowed: an empty storage means the provider
    # stores nothing, which passes every region rule, so it has to be said
    # and never fall out of a forgotten option.
    provider.add_argument(
        "--storage",
        nargs="*",
        required=True,
        metavar="REGION",
        help="where the provider stores; give it no region for one that stores nothing",
    )
    provider.add_argument(
        "--retention-days", required=True, metavar="N|unknown", help="how long the provider keeps"
    )
    # Required like `--storage`: an unknown chain passes no restriction that
    # concerns it, so it has to be said and never fall out of a forgotten option.
    provider.add_argument(
        "--operator", required=True, metavar="NAME|unknown", help="who runs the service"
    )
    provider.add_argument(
        "--training",
        required=True,
        choices=["yes", "no", "unknown"],
        help="whether the provider trains on input",
    )
    provider.add_argument(
        "--subprocessors",
        nargs="+",
        required=True,
        metavar="NAME|none|unknown",
        help="who else handles the input: names, none or unknown",
    )
    provider.add_argument(
        "--model-origin",
        metavar="NAME",
        help="where the model comes from; unknown, or unknown if omitted",
    )
    provider.add_argument("--reports-geo", action="store_true", help="the answer names the region")
    provider.add_argument("--local", action="store_true", help="runs on hardware the operator runs")
    show = what.add_parser("show", help="print the policy in force", description="print the policy")
    show.add_argument("--at", metavar="TIME", help="the policy as it was then (ISO 8601, a zone)")
    sentence = "list the circles and sources whose calls fell back to local only"
    found = what.add_parser("gaps", help=sentence, description=sentence)
    found.add_argument("--since", metavar="TIME", help="only calls from then on (ISO 8601, a zone)")


def _inference_of(text: str) -> Inference:
    name, equals, regions = text.partition("=")
    if not equals:
        raise InvalidPayload(f"{text!r} is not NAME=REGIONS, such as global=any")
    return Inference(name, frozenset(part for part in regions.split(",") if part))


def _retention_of(text: str) -> int | None:
    if text == "unknown":
        return None
    try:
        return int(text)
    except ValueError as error:
        raise InvalidPayload(f"{text!r} is not a number of days or unknown") from error


def _training_of(text: str) -> bool | None:
    return {"yes": True, "no": False}.get(text)


def _subprocessors_of(names: list[str]) -> frozenset[str] | None:
    if names == ["unknown"]:
        return None
    if names == ["none"]:
        return frozenset()
    if "none" in names or "unknown" in names:
        raise InvalidPayload('"none" and "unknown" stand alone, without a name beside them')
    return frozenset(names)


def _policy_statement(args: argparse.Namespace) -> Statement:
    """The statement the arguments of a writing form describe."""
    if args.what == "circle":
        return Circle(args.name)
    if args.what == "member":
        return Membership(args.circle, args.member)
    if args.what == "own":
        return OwnIdentity(args.member)
    if args.what == "rule":
        return Rule(
            args.scope,
            frozenset(args.regions),
            args.max_retention_days,
            frozenset(args.exclude_provider),
            args.no_training,
            args.no_subprocessors,
            frozenset(args.exclude_operator),
            frozenset(args.exclude_model_origin),
        )
    return Provider(
        args.name,
        tuple(_inference_of(text) for text in args.inference),
        frozenset(args.storage),
        _retention_of(args.retention_days),
        args.reports_geo,
        args.local,
        None if args.operator == "unknown" else args.operator,
        _training_of(args.training),
        _subprocessors_of(args.subprocessors),
        None if args.model_origin == "unknown" else args.model_origin,
    )


def _confirmed(args: argparse.Namespace) -> bool:
    """Asks on the terminal unless `--yes`; an answer that never comes (the
    input ended) is a no, and says so.

    The input ends without an answer where nobody can give one, such as
    under `kubectl exec` without `-i`, where kup6s found on 2026-10-11 that
    `client add` printed no token. `nothing written` alone, which the caller
    prints after this, says neither why nor what to do instead."""
    if args.yes:
        return True
    try:
        answer = input("write? [y/N] ")
    except EOFError:
        print(
            "no answer: the input ended before one came; --yes writes without asking",
            file=sys.stderr,
        )
        return False
    return answer.strip().lower() in {"y", "yes"}


def _cmd_policy_set(args: argparse.Namespace) -> int:
    """Shows the structured statement, asks, and writes one policy event.
    A refusal comes before the question, so nobody confirms what cannot be
    written."""
    item = normalized(_policy_statement(args))
    with _storage() as storage:
        with storage.begin() as conn:
            current = read_policy(storage, conn)
        sentence = refusal(item, statement=args.statement, revoked=args.revoke, current=current)
        if sentence is not None:
            raise PolicyRefused(sentence)
        payload = to_payload(item, statement=args.statement, revoked=args.revoke)
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
        if not _confirmed(args):
            print("nothing written", file=sys.stderr)
            return 1
        event_id = set_policy(
            storage,
            item,
            statement=args.statement,
            revoked=args.revoke,
            recorded_at=datetime.now(UTC),
        )
    print(f"policy event {event_id}")
    return 0


def _list(names: Iterable[str]) -> str:
    return ",".join(sorted(names)) or "-"


def _policy_lines(policy: Policy) -> list[str]:
    """The tables of `policy show`, one per kind, each row ending in the id
    of the event that set it."""

    def event(kind: str, key: str) -> str:
        return f"(event {policy.ids[(kind, key)]})"

    lines = ["circles"]
    lines += [f"  {escape_field(name)}\t{event('circle', name)}" for name in sorted(policy.circles)]
    lines += ["memberships"]
    for member in policy.memberships:
        key = key_of(member)[1]
        who = f"{escape_field(member.circle)}\t{escape_field(member.member)}"
        lines.append(f"  {who}\t{event('membership', key)}")
    lines += ["own identities"]
    lines += [
        f"  {escape_field(own.member)}\t{event('own_identity', own.member)}" for own in policy.own
    ]
    lines += ["rules", f"  {LOCAL_ONLY}\tbuilt-in: without a rule, only providers with local"]
    for scope, rule in sorted(policy.rules.items()):
        days = "-" if rule.max_retention_days is None else str(rule.max_retention_days)
        lines.append(
            f"  {escape_field(scope)}\tregions {_list(rule.regions)}\tmax retention days {days}"
            f"\texcluded {_list(rule.excluded_providers)}"
            f"\tno training {'yes' if rule.no_training else 'no'}"
            f"\tno subprocessors {'yes' if rule.no_subprocessors else 'no'}"
            f"\texcluded operators {_list(rule.excluded_operators)}"
            f"\texcluded model origins {_list(rule.excluded_model_origins)}"
            f"\t{event('rule', scope)}"
        )
    lines += ["providers"]
    for name, provider in sorted(policy.providers.items()):
        days = "unknown" if provider.retention_days is None else str(provider.retention_days)
        inference = ",".join(
            f"{space.name}={_list(space.regions)}"
            for space in sorted(provider.inference, key=lambda space: space.name)
        )
        reports = "yes" if provider.reports_inference_geo else "no"
        local = "yes" if provider.local else "no"
        training = "unknown" if provider.training is None else "yes" if provider.training else "no"
        subprocessors = (
            "unknown" if provider.subprocessors is None else _list(provider.subprocessors)
        )
        lines.append(
            f"  {escape_field(name)}\tinference {inference or '-'}"
            f"\tstorage {_list(provider.storage)}\tretention days {days}"
            f"\treports geo {reports}\tlocal {local}"
            f"\toperator {escape_field(provider.operator or 'unknown')}\ttraining {training}"
            f"\tsubprocessors {escape_field(subprocessors)}"
            f"\tmodel origin {escape_field(provider.model_origin or 'unknown')}"
            f"\t{event('provider', name)}"
        )
    return lines


def _cmd_policy_gaps(args: argparse.Namespace) -> int:
    """Prints one line per scope whose calls fell back: the scope, how many
    calls, and the time of the last ({ref}`cli-reference`)."""
    since = parse_moment(args.since) if args.since else None
    with _storage() as storage, storage.begin() as conn:
        found = gaps(storage, conn, since=since)
    if not found:
        print("no call fell back to local only", file=sys.stderr)
    for gap in found:
        # A withholding of the MCP server is told from a model call by the
        # prefix, so that every line keeps its three fields.
        scope = gap.what if gap.origin == "gate" else f"{gap.origin}:{gap.what}"
        print(f"{escape_field(scope)}\t{gap.count}\t{iso_utc(gap.last)}")
    return 0


def _cmd_policy(args: argparse.Namespace) -> int:
    """Sets one statement of the policy, prints the policy in force, or
    lists where the built-in rule acted."""
    if args.what == "gaps":
        return _cmd_policy_gaps(args)
    if args.what != "show":
        return _cmd_policy_set(args)
    at = parse_moment(args.at) if args.at else None
    with _storage() as storage, storage.begin() as conn:
        policy = read_policy(storage, conn, at=at)
    for line in _policy_lines(policy):
        print(line)
    return 0


# --- The gate ---------------------------------------------------------------------
#
# One task for now, `mail_overview`. The caller names the event, never the
# model: the policy decides which model may see the content.

# The variable each provider's adapter is built from; without it set, that
# adapter is absent and a call the policy gives to that provider ends as an
# error that names the variable.
_PROVIDER_SETTINGS: Mapping[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "local": "PREVIOUSLY_LOCAL_MODEL_URL",
}


def _gate_arguments(parser: argparse.ArgumentParser) -> None:
    how = parser.add_subparsers(dest="how", required=True)
    sentence = "show the decision for an event, without a call"
    explaining = how.add_parser("explain", help=sentence, description=sentence)
    explaining.add_argument("event", type=int, metavar="EVENT")
    sentence = "run mail_overview over an event and record the call"
    trying = how.add_parser("try", help=sentence, description=sentence)
    trying.add_argument("event", type=int, metavar="EVENT")


def _adapters() -> dict[str, Adapter]:
    """One adapter per provider whose setting is present.

    Imported here and not at the head of the module: the two vendor clients
    take about a second to import, measured on 2026-10-09 with
    `python -c "import previously.cli, previously.gate.adapters.anthropic"`
    at 1.3 to 1.5 s against 0.5 s for `previously.cli` alone, and every
    other command would pay for it, and stay that much longer deaf to
    `SIGTERM`.
    """
    from previously.gate.adapters.anthropic import AnthropicAdapter
    from previously.gate.adapters.openai_compatible import MISTRAL_BASE_URL
    from previously.gate.adapters.openai_compatible import OpenAICompatibleAdapter

    found: dict[str, Adapter] = {}
    if key := os.environ.get(_PROVIDER_SETTINGS["anthropic"]):
        found["anthropic"] = AnthropicAdapter(api_key=key)
    if key := os.environ.get(_PROVIDER_SETTINGS["mistral"]):
        found["mistral"] = OpenAICompatibleAdapter(
            provider="mistral", api_key=key, base_url=MISTRAL_BASE_URL
        )
    if url := os.environ.get(_PROVIDER_SETTINGS["local"]):
        # Measured on 2026-10-09 against `qwen3:4b` on Ollama: without
        # `reasoning_effort` set to `none` the model thinks for over 600 s.
        found["local"] = OpenAICompatibleAdapter(
            provider="local", api_key="unused", base_url=url, extra={"reasoning_effort": "none"}
        )
    return found


def _fallback_lines(storage: PostgresStorage, decision: Decision, event_id: int) -> list[str]:
    """One line per scope without a rule, with the command that sets one,
    where the built-in rule `local_only` acted and a local model was chosen.

    A decision that chose nothing gets no line: `processed locally` would be
    false there, since no local provider is declared, and the reason of the
    denial already says so."""
    fallback = decision.fallback
    if fallback is None or decision.chosen is None:
        return []
    scopes = [f"circle:{circle}" for circle in fallback.circles]
    if not scopes:
        with storage.begin() as conn:
            key = storage.source_keys(conn, [event_id]).get(event_id)
        scopes = [f"event:{event_id}" if key is None else f"source:{key[0]}"]
    return [_fallback_line(escape_field(scope)) for scope in scopes]


def _undeclared_lines(decision: Decision) -> list[str]:
    """`_undeclared_line` as a list of none or one."""
    line = _undeclared_line(decision)
    return [] if line is None else [line]


def _undeclared_line(decision: Decision) -> str | None:
    """One line where the decision chose nothing and a candidate of the task
    failed because its provider has no declaration.

    kup6s's maintainer met it on 2026-10-11 after setting up a client: the
    client's chain declared, a rule for the circle, and `gate explain` said
    `denied`, which read like the client's view of the circle. Under a rule,
    the line names the providers and says that the gate's are declared apart
    from an MCP client's.

    Under the built-in rule `local_only` it names none. Only a provider
    declared with `--local` can be chosen there, and naming `anthropic` sent
    the reader to declare it and then meet `not local, and only local
    applies`. Which undeclared provider would be local is what its
    declaration says, so the line says what can be chosen instead of
    guessing from a name. A decision that chose a provider gets no line,
    since nothing was denied."""
    if decision.chosen is not None or not decision.undeclared:
        return None
    if decision.local_only:
        return (
            "only local: the built-in rule local_only acted, so only a provider declared with "
            "--local can be chosen — set a rule with previously policy rule SCOPE …, or declare "
            "one with previously policy provider NAME … --local"
        )
    names = ", ".join(escape_field(name) for name in decision.undeclared)
    return (
        f"undeclared: {names} — the gate chooses among its own providers, each declared "
        "with previously policy provider NAME …, apart from the provider of an MCP client"
    )


def _fallback_line(scope: str) -> str:
    return f"processed locally: no rule for {scope} — set one with previously policy rule {scope} …"


def _explain_lines(decision: Decision, rule_ids: Mapping[tuple[str, str], int]) -> list[str]:
    """The decision as `gate explain` prints it: what it rested on, each
    candidate with what became of it, and the choice."""

    def rule(scope: str) -> str:
        known = rule_ids.get(("rule", scope))
        return escape_field(scope) if known is None else f"{escape_field(scope)} (event {known})"

    days = decision.max_retention_days
    lines = [
        f"circles\t{_list(escape_field(c) for c in decision.circles)}",
        f"rules\t{','.join(rule(scope) for scope in decision.rule_keys) or '-'}",
        f"regions\t{_list(decision.regions)}",
        f"max retention days\t{'-' if days is None else days}",
        f"excluded providers\t{_list(escape_field(p) for p in decision.excluded_providers)}",
    ]
    names = [f"{c.provider}/{c.model}" for c in MAIL_OVERVIEW.candidates]
    lines += [
        f"candidate\t-\t{escape_field(reason)}"
        for reason in decision.reasons
        if not any(reason.startswith(f"{name}: ") for name in names)
    ]
    chosen = decision.chosen
    for candidate, name in zip(MAIL_OVERVIEW.candidates, names, strict=True):
        reasons = [r for r in decision.reasons if r.startswith(f"{name}: ")]
        if candidate == chosen:
            state = "chosen"
        elif reasons:
            state = f"rejected: {escape_field(reasons[0])}"
        else:
            state = "not reached"
        lines.append(f"candidate\t{escape_field(name)}\t{state}")
    if chosen is None:
        lines.append("decision\tdenied")
    else:
        geo = decision.inference_geo or "-"
        lines.append(f"decision\t{chosen.provider}/{chosen.model}, inference_geo {geo}")
    return lines


def _cmd_gate_explain(args: argparse.Namespace) -> int:
    with _storage() as storage:
        decision = explain(storage, MAIL_OVERVIEW, args.event)
        with storage.begin() as conn:
            rule_ids = read_policy(storage, conn).ids
        fallback = _fallback_lines(storage, decision, args.event)
    for line in _explain_lines(decision, rule_ids):
        print(line)
    for line in [*fallback, *_undeclared_lines(decision)]:
        print(line, file=sys.stderr)
    return 0


def _failure_line(called: Called, adapters: Mapping[str, Adapter]) -> str:
    """The one sentence on standard error for a call that did not end `ok`."""
    message = escape_controls(called.message or "")
    chosen = called.decision.chosen
    if called.outcome == "denied" or chosen is None:
        return f"denied: {message}"
    if called.outcome == "refused":
        return f"refused: {message}"
    if called.outcome == "schema_invalid":
        return f"schema_invalid: {message}"
    setting = _PROVIDER_SETTINGS.get(chosen.provider)
    if chosen.provider not in adapters and setting is not None:
        return f"Error: {message} — set {setting}"
    if chosen.provider == "local" and setting is not None:
        url = os.environ.get(setting, "")
        return f"Error: {message} — the local model server is {escape_controls(url)}"
    return f"Error: {message}"


def _cmd_gate_try(args: argparse.Namespace) -> int:
    """Runs the task and records the call: the output and the id of the
    `model_call` on standard output; the fallback, an alarm and a failure
    on standard error. 2 for anything but `ok`, and for an `ok` whose input
    was erased while the call ran; 3 for `ok` with an alarm, so that a script
    does not read past it.

    The fallback is said only where the local model answered: a call that
    ended `error` processed nothing, and one that was denied called nothing."""
    prices_path = os.environ.get("PREVIOUSLY_PRICES")
    prices = load_prices(Path(prices_path) if prices_path else None)
    adapters = _adapters()
    with _storage() as storage:
        called = call(
            storage,
            storage,
            MAIL_OVERVIEW,
            args.event,
            adapters,
            prices,
            recorded_at=datetime.now(UTC),
        )
        answered = called.outcome != "error"
        fallback = _fallback_lines(storage, called.decision, args.event) if answered else []
    for line in fallback:
        print(line, file=sys.stderr)
    if called.output is not None:
        print(_json_line(called.output.model_dump(mode="json")))
    print(f"model_call: event {called.event_id}")
    for _alarm in called.alarms:
        requested = called.decision.inference_geo
        reported = escape_controls(called.reported_geo or "nothing")
        print(f"alarm: inference_geo requested {requested}, reported {reported}", file=sys.stderr)
    if called.outcome != "ok":
        for line in [_failure_line(called, adapters), *_undeclared_lines(called.decision)]:
            print(line, file=sys.stderr)
        return 2
    if called.erased_by is not None:
        print(f"erased: {called.message}; the answer is erased with it", file=sys.stderr)
        return 2
    return 3 if called.alarms else 0


def _cmd_gate(args: argparse.Namespace) -> int:
    if args.how == "explain":
        return _cmd_gate_explain(args)
    return _cmd_gate_try(args)


def _access_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--client", metavar="NAME", help="only calls of this client")
    parser.add_argument(
        "--circle",
        metavar="NAME",
        help="only calls that named this circle, or delivered or withheld something of it",
    )
    parser.add_argument(
        "--since", metavar="TIME", help="only calls from then on (ISO 8601, a zone)"
    )


def _ids(values: tuple[int, ...]) -> str:
    return ",".join(str(value) for value in values) or "-"


def _cmd_access(args: argparse.Namespace) -> int:
    """Prints one line per call: the time, the client, the kind and name of
    the call, the delivered events, and the withheld ones with the reason
    ({ref}`cli-reference`)."""
    since = parse_moment(args.since) if args.since else None
    with _storage() as storage, storage.begin() as conn:
        rows = read_access(storage, conn, client=args.client, circle=args.circle, since=since)
    if not rows:
        print("no access matches", file=sys.stderr)
    for row in rows:
        access = row.access
        delivered = _ids(tuple(item.event for item in access.delivered))
        withheld = (
            " ".join(
                f"{item.event}:{item.reason_code}:{escape_field(item.reason)}"
                for item in access.withheld
            )
            or "-"
        )
        print(
            f"{iso_utc(row.recorded_at)}\t{escape_field(access.client)}"
            f"\t{access.kind}:{escape_field(access.name)}\t{access.outcome}"
            f"\tdelivered {delivered}\twithheld {withheld}"
        )
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


# --- assertions ------------------------------------------------------------------
#
# An assertion states an obligation or a decision, with its sources and who
# stands for it. The command line is the operator's own
# way to write one, so its author is `human:operator` and its responsibility
# is direct. Nothing here asks the policy: whoever has the command line is the
# operator, as with `chronicle`.

_SOURCE_FORM = re.compile(r"(\d{1,16})(?::(\d{1,16}(?:,\d{1,16})*))?", re.ASCII)
_DAY_FORM = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)
_NO_VALUE = "(none)"
_NAME_PREFIX = "name:"
_BLANK_OBLIGATION = ObligationBody("", "", "", None, "open")
_BLANK_DECISION = DecisionBody("", (), date.min, "valid", None)


def _parse_source(text: str) -> AssertionSource:
    """`EVENT` for the whole event, `EVENT:SEQ,SEQ` for units of it. Strict:
    anything else, white space around a number included, is refused."""
    found = _SOURCE_FORM.fullmatch(text)
    if found is None:
        raise PreviouslyError(f"--source is not EVENT or EVENT:SEQ,SEQ: {text!r}")
    units = found[2]
    return AssertionSource(
        int(found[1]), None if units is None else tuple(int(seq) for seq in units.split(","))
    )


def _parse_day(option: str, text: str) -> date:
    """A date written `YYYY-MM-DD` and nothing else: `date.fromisoformat`
    alone would also take `20261130`, and the payload carries one spelling."""
    if _DAY_FORM.fullmatch(text) is None:
        raise PreviouslyError(f"{option} is not a date written YYYY-MM-DD")
    try:
        return date.fromisoformat(text)
    except ValueError as error:
        raise PreviouslyError(f"{option} is not a date written YYYY-MM-DD") from error


def _reference(option: str, text: str) -> str:
    problem = reference_problem(text)
    if problem is not None:
        raise PreviouslyError(f"{option}: {problem}")
    return text


def _joined(names: Sequence[str]) -> str:
    if len(names) == 1:
        return names[0]
    return f"{', '.join(names[:-1])} and {names[-1]}"


def _utc_today() -> date:
    """The day `overdue` is judged on: the UTC date of now, passed in."""
    return datetime.now(UTC).date()


def _base_of(
    threads: Mapping[int, Thread], subject: int | None, kind: str
) -> AssertionStatement | None:
    """The statement that stands under `--subject`, from which a version
    fills what it leaves out: the winner, a proposal included, and for a
    thread with no winner left (every proposal rejected) its latest version."""
    if subject is None:
        return None
    thread = threads.get(subject)
    if thread is None or thread.kind != kind:
        raise PreviouslyError(f"--subject {subject} names no {kind} that stands")
    return (thread.winner() or thread.versions[-1]).statement


def _obligation_body(
    args: argparse.Namespace, base: AssertionStatement | None
) -> tuple[ObligationBody, list[str]]:
    old = base.body if base is not None and isinstance(base.body, ObligationBody) else None
    absent = [
        flag
        for flag, value in (
            ("--debtor", args.debtor),
            ("--creditor", args.creditor),
            ("--what", args.what),
        )
        if value is None
    ]
    old = old or _BLANK_OBLIGATION
    return ObligationBody(
        old.debtor if args.debtor is None else _reference("--debtor", args.debtor),
        old.creditor if args.creditor is None else _reference("--creditor", args.creditor),
        old.what if args.what is None else args.what,
        old.due if args.due is None else _parse_day("--due", args.due),
        old.state if args.state is None else args.state,
    ), absent


def _decision_body(
    args: argparse.Namespace, base: AssertionStatement | None
) -> tuple[DecisionBody, list[str]]:
    old = base.body if base is not None and isinstance(base.body, DecisionBody) else None
    absent = [
        flag
        for flag, missing in (
            ("--what", args.what is None),
            ("--by", not args.by),
            ("--on", args.on is None),
        )
        if missing
    ]
    old = old or _BLANK_DECISION
    return DecisionBody(
        old.what if args.what is None else args.what,
        tuple(_reference("--by", by) for by in args.by) if args.by else old.by,
        old.on if args.on is None else _parse_day("--on", args.on),
        old.state if args.state is None else args.state,
        old.replaces if args.replaces is None else args.replaces,
    ), absent


def _asserted(
    args: argparse.Namespace, kind: str, base: AssertionStatement | None
) -> AssertionStatement:
    """The version `assert` writes: what the options say, and for the rest
    what stands under `--subject`. The form is checked here, before any
    question is asked."""
    sources = tuple(_parse_source(text) for text in args.source or ())
    if kind == OBLIGATION:
        body, absent = _obligation_body(args, base)
    else:
        body, absent = _decision_body(args, base)
    if not sources:
        absent.append("--source")
    if base is None and absent:
        article = "an" if kind == OBLIGATION else "a"
        raise PreviouslyError(
            f"{article} {kind} needs {_joined(absent)} unless --subject names the one to change"
        )
    statement = AssertionStatement(
        kind,
        OPERATOR,
        DIRECT,
        sources or (base.sources if base is not None else ()),
        args.reason,
        None,
        args.subject,
        None,
        None,
        body,
    )
    problem = assertion_problem(payload_of(statement))
    if problem is not None:
        raise PreviouslyError(problem)
    return statement


def _references(statement: AssertionStatement) -> tuple[str, ...]:
    body = statement.body
    if isinstance(body, ObligationBody):
        return (body.debtor, body.creditor)
    if isinstance(body, DecisionBody):
        return body.by
    return ()


def _name_hints(
    storage: PostgresStorage, conn: Connection, statement: AssertionStatement
) -> list[str]:
    """One hint per address that a source of the statement shows next to a
    display name containing the text of a `name:` reference, case-insensitive.
    A name is a label and an address is a reference that holds
    (a reference to a name is a label); this tells the operator, and forbids nothing."""
    needles = [
        reference.removeprefix(_NAME_PREFIX).casefold()
        for reference in _references(statement)
        if reference.startswith(_NAME_PREFIX)
    ]
    found: set[str] = set()
    for source in statement.sources if needles else ():
        row = next(iter(storage.read(conn, source.event, 1)), None)
        if row is None or row.id != source.event or row.payload is None:
            continue
        listed = row.payload.get("channel_identities")
        for identity in cast("list[object]", listed) if isinstance(listed, list) else ():
            entry = cast("dict[str, object]", identity) if isinstance(identity, dict) else {}
            address, name = entry.get("address"), entry.get("name")
            if (
                isinstance(address, str)
                and isinstance(name, str)
                and any(needle in name.casefold() for needle in needles)
            ):
                found.add(address)
    return [
        f"hint: {escape_field(address)} appears in the sources; address: is a reference that holds"
        for address in sorted(found)
    ]


def _change_lines(lead: str, before: AssertionStatement, after: AssertionStatement) -> list[str]:
    return [
        f"{lead}\t{escape_field(name)}\t{escape_field(old)}\t{escape_field(new)}"
        for name, old, new in changes(before, after)
    ]


def _preview(statements: Sequence[AssertionStatement]) -> None:
    for statement in statements:
        print(json.dumps(payload_of(statement), indent=2, sort_keys=True, ensure_ascii=False))


def _write_asked(
    args: argparse.Namespace, storage: PostgresStorage, statements: Sequence[AssertionStatement]
) -> int:
    """Asks, writes and prints `assertion <id>` for each statement written.
    `write_statements` refuses with one sentence, which `main` prints."""
    if not _confirmed(args):
        print("nothing written", file=sys.stderr)
        return 1
    ids = write_statements(storage, storage, statements, recorded_at=datetime.now(UTC))
    for event_id in ids:
        print(f"assertion {event_id}")
    return 0


def _cmd_assert(args: argparse.Namespace) -> int:
    """Shows the version in full, asks, and writes it. With `--subject` the
    gaps are filled from the winner and the preview adds how the new version
    differs from it."""
    kind = OBLIGATION if args.form == "obligation" else DECISION
    with _storage() as storage:
        with storage.snapshot() as conn:
            base = _base_of(read_threads(storage, conn), args.subject, kind)
            statement = _asserted(args, kind, base)
            hints = _name_hints(storage, conn, statement)
        for hint in hints:
            print(hint, file=sys.stderr)
        _preview([statement])
        if base is not None:
            for line in _change_lines("change", base, statement):
                print(line)
        return _write_asked(args, storage, [statement])


def _proposal_of(threads: Mapping[int, Thread], event_id: int) -> tuple[Thread, Version]:
    """The open version `event_id` names, or the sentence that says why it is
    none. The write path refuses the same cases; asking first spares the
    question."""
    for thread in threads.values():
        for version in thread.versions:
            if version.id != event_id:
                continue
            if version.statement.responsibility != OPEN:
                raise PreviouslyError(f"the version {event_id} is no proposal: it is direct")
            if event_id in thread.approved:
                raise PreviouslyError(f"the proposal {event_id} is already approved")
            if event_id in thread.rejected:
                raise PreviouslyError(f"the proposal {event_id} is already rejected")
            return thread, version
    raise PreviouslyError(f"event {event_id} is no proposal that stands")


def _cmd_approve(args: argparse.Namespace) -> int:
    """Makes each proposal the operator's own: a direct version with the
    content, sources and author of the proposal, pointing at it."""
    with _storage() as storage:
        with storage.snapshot() as conn:
            threads = read_threads(storage, conn)
        statements: list[AssertionStatement] = []
        for event_id in args.ids:
            thread, version = _proposal_of(threads, event_id)
            proposal = version.statement
            statements.append(
                replace(
                    proposal,
                    responsibility=DIRECT,
                    reason=proposal.reason if args.reason is None else args.reason,
                    handle=None,
                    subject=thread.subject,
                    approves=version.id,
                )
            )
        _preview(statements)
        return _write_asked(args, storage, statements)


def _cmd_reject(args: argparse.Namespace) -> int:
    with _storage() as storage:
        with storage.snapshot() as conn:
            _thread, version = _proposal_of(read_threads(storage, conn), args.id)
        statement = AssertionStatement(
            REJECTION,
            OPERATOR,
            DIRECT,
            version.statement.sources,
            args.reason,
            None,
            None,
            None,
            version.id,
            None,
        )
        _preview([statement])
        return _write_asked(args, storage, [statement])


def _asserting(form: argparse.ArgumentParser) -> None:
    form.add_argument(
        "--subject", type=int, help="the id of the one to change; fills what is left out"
    )
    form.add_argument("--reason", help="why this version, for the history")
    form.add_argument(
        "--source",
        action="append",
        help="an event it rests on, EVENT or EVENT:SEQ,SEQ; may repeat",
    )
    form.add_argument("--yes", action="store_true", help="write without asking")


def _assert_arguments(parser: argparse.ArgumentParser) -> None:
    sentence = "state an obligation or a decision"
    form = parser.add_subparsers(dest="form", required=True)
    obligation = form.add_parser("obligation", help="state an obligation", description=sentence)
    obligation.add_argument(
        "--debtor", help="who owes: own, circle:NAME, address:ADDRESS or name:TEXT"
    )
    obligation.add_argument("--creditor", help="who is owed: a reference, as for --debtor")
    obligation.add_argument("--what", help="what is owed")
    obligation.add_argument("--due", help="by when, YYYY-MM-DD; may lie in the past")
    obligation.add_argument("--state", choices=OBLIGATION_STATES, help="open unless --subject")
    _asserting(obligation)
    decision = form.add_parser("decision", help="state a decision", description=sentence)
    decision.add_argument("--what", help="what was decided")
    decision.add_argument("--by", action="append", help="who decided, a reference; may repeat")
    decision.add_argument("--on", help="when it was decided, YYYY-MM-DD")
    decision.add_argument("--state", choices=DECISION_STATES, help="valid unless --subject")
    decision.add_argument("--replaces", type=int, help="the id of the decision it replaces")
    _asserting(decision)


def _approve_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("ids", metavar="ID", type=int, nargs="+", help="a proposal")
    parser.add_argument("--reason", help="why; the reason of the proposal stays if left out")
    parser.add_argument("--yes", action="store_true", help="write without asking")


def _reject_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("id", metavar="ID", type=int, help="a proposal")
    parser.add_argument("--reason", help="why the proposal is not taken")
    parser.add_argument("--yes", action="store_true", help="write without asking")


def _refers_to(actor: str, wanted: str) -> bool:
    """Whether `actor` is the reference `wanted`. A `name:` is a label, not an
    identity, so a list searches the text of one, ignoring case, and never
    treats two names as the same actor."""
    if wanted.startswith(_NAME_PREFIX):
        return actor.startswith(_NAME_PREFIX) and (
            wanted.removeprefix(_NAME_PREFIX).casefold()
            in actor.removeprefix(_NAME_PREFIX).casefold()
        )
    return actor == wanted


def _kept(body: ObligationBody | DecisionBody, args: argparse.Namespace, today: date) -> bool:
    """The filters of the list that look at the body of the winner."""
    if args.state is not None and body.state != args.state:
        return False
    if not isinstance(body, ObligationBody):
        return True
    return (
        (args.owed_by is None or _refers_to(body.debtor, args.owed_by))
        and (args.owed_to is None or _refers_to(body.creditor, args.owed_to))
        and (not args.overdue or overdue(body, today))
    )


def _entries(
    storage: PostgresStorage, conn: Connection, args: argparse.Namespace, kind: str
) -> list[tuple[Thread, Version]]:
    """The threads a list shows, each with the version that stands for it, in
    order of their ids. Without `--proposals`, only an entry with a direct
    winner; with it, only one that has a pending proposal or stands as one.
    A proposal never passes for a valid entry."""
    today = _utc_today()
    threads = read_threads(storage, conn)
    policy = read_policy(storage, conn) if args.circle is not None else None
    entries: list[tuple[Thread, Version]] = []
    for subject in sorted(threads):
        thread = threads[subject]
        winner = thread.winner()
        if thread.kind != kind or winner is None or winner.statement.body is None:
            continue
        proposed = winner.statement.responsibility == OPEN
        listed = (proposed or bool(thread.pending())) if args.proposals else not proposed
        if not listed or not _kept(winner.statement.body, args, today):
            continue
        if policy is not None:
            identities, _sources = source_identities(storage, conn, thread)
            if args.circle not in thread_circles(policy, identities, winner.statement):
                continue
        entries.append((thread, winner))
    return entries


def _replaced_by(threads: Mapping[int, Thread]) -> dict[int, int]:
    """Which decision a decision that stands directly replaces, by id."""
    replaced: dict[int, int] = {}
    for subject, thread in sorted(threads.items()):
        winner = thread.winner()
        if winner is None or winner.statement.responsibility != DIRECT:
            continue
        body = winner.statement.body
        if isinstance(body, DecisionBody) and body.replaces is not None:
            replaced[body.replaces] = subject
    return replaced


def _state_text(thread: Thread, winner: Version, today: date, replaced_by: int | None) -> str:
    body = winner.statement.body
    words = ["proposed"] if winner.statement.responsibility == OPEN else []
    words.append("" if body is None else body.state)
    if isinstance(body, ObligationBody) and overdue(body, today):
        words.append("overdue")
    if replaced_by is not None:
        words.append(f"replaced by {replaced_by}")
    return " ".join(words)


def _parties(body: ObligationBody | DecisionBody | None) -> str:
    if isinstance(body, ObligationBody):
        return f"{escape_field(body.debtor)} -> {escape_field(body.creditor)}"
    if isinstance(body, DecisionBody):
        return ", ".join(escape_field(by) for by in body.by)
    return ""


def _day(day: date | None, none: str) -> str:
    return none if day is None else day.isoformat()


def _list_line(thread: Thread, winner: Version, today: date, replaced_by: int | None) -> str:
    body = winner.statement.body
    when = body.due if isinstance(body, ObligationBody) else body.on if body else None
    return "\t".join(
        (
            str(thread.subject),
            _state_text(thread, winner, today, replaced_by),
            _day(when, "-"),
            _parties(body),
            escape_field("" if body is None else body.what),
            f"{len(thread.versions)} versions",
            f"{len(thread.pending())} proposals",
        )
    )


def _list_assertions(args: argparse.Namespace, kind: str) -> int:
    if args.owed_by is not None:
        _reference("--owed-by", args.owed_by)
    if args.owed_to is not None:
        _reference("--owed-to", args.owed_to)
    today = _utc_today()
    with _storage() as storage, storage.snapshot() as conn:
        entries = _entries(storage, conn, args, kind)
        replaced = _replaced_by(read_threads(storage, conn))
    for thread, winner in entries:
        print(_list_line(thread, winner, today, replaced.get(thread.subject)))
    return 0


def _cmd_obligations(args: argparse.Namespace) -> int:
    return _list_assertions(args, OBLIGATION)


def _cmd_decisions(args: argparse.Namespace) -> int:
    args.owed_by = args.owed_to = None
    args.overdue = False
    return _list_assertions(args, DECISION)


def _sources_text(sources: Sequence[AssertionSource]) -> str:
    """The sources the way `changes` writes them, so that a line of the
    history and a change line agree."""

    def one(source: AssertionSource) -> str:
        if source.units is None:
            return f"event {source.event}"
        return f"event {source.event} units {', '.join(str(seq) for seq in source.units)}"

    return "; ".join(one(source) for source in sources)


def _body_fields(statement: AssertionStatement) -> list[tuple[str, str]]:
    body = statement.body
    if isinstance(body, ObligationBody):
        return [
            ("state", body.state),
            ("due", _day(body.due, _NO_VALUE)),
            ("debtor", body.debtor),
            ("creditor", body.creditor),
            ("what", body.what),
        ]
    if isinstance(body, DecisionBody):
        return [
            ("state", body.state),
            ("on", body.on.isoformat()),
            ("by", ", ".join(body.by)),
            ("what", body.what),
            ("replaces", _NO_VALUE if body.replaces is None else str(body.replaces)),
        ]
    return []


def _field_lines(lead: str, fields: Sequence[tuple[str, str]]) -> list[str]:
    return [f"{lead}{escape_field(name)}\t{escape_field(value)}" for name, value in fields]


def _entry_lines(
    thread: Thread, winner: Version, today: date, replaced_by: int | None
) -> list[str]:
    """The page of one entry: what stands, and the pending proposals as the
    fields they would change."""
    statement = winner.statement
    fields = _body_fields(statement)
    extra: list[tuple[str, str]] = []
    if isinstance(statement.body, ObligationBody) and overdue(statement.body, today):
        extra.append(("overdue", "yes"))
    if replaced_by is not None:
        extra.append(("replaced by", str(replaced_by)))
    fields[1:1] = extra
    proposed = " (proposal)" if statement.responsibility == OPEN else ""
    lines = [f"{thread.kind} {thread.subject}{proposed}", f"version\t{winner.id}"]
    lines += _field_lines("", fields)
    lines += _field_lines(
        "",
        [
            ("sources", _sources_text(statement.sources)),
            ("reason", _NO_VALUE if statement.reason is None else statement.reason),
            ("author", statement.author),
            ("responsibility", statement.responsibility),
            ("versions", str(len(thread.versions))),
            ("proposals", str(len(thread.pending()))),
        ],
    )
    for pending in thread.pending():
        lead = f"proposal\t{pending.id}\t{escape_field(pending.statement.author)}"
        lines += _change_lines(lead, statement, pending.statement) or [lead]
    return lines


def _history_lines(
    thread: Thread, rejections: Sequence[tuple[int, datetime, AssertionStatement]]
) -> list[str]:
    """Every version in chain order, each with its difference to the one
    standing before it, and the rejections among them."""
    lines = [f"{thread.kind} {thread.subject}: {len(thread.versions)} versions"]
    shown: list[tuple[int, list[str]]] = []
    for position, version in enumerate(thread.versions):
        statement = version.statement
        head = [
            "version",
            str(version.id),
            iso_utc(version.recorded_at),
            statement.responsibility,
            escape_field(statement.author),
        ]
        if version.id in thread.rejected:
            head.append("rejected")
        elif version.id in thread.approved:
            head.append("approved")
        elif statement.approves is not None:
            head.append(f"approves {statement.approves}")
        body = [
            "\t".join(head),
            f"sources\t{escape_field(_sources_text(statement.sources))}",
            f"reason\t{escape_field(_NO_VALUE if statement.reason is None else statement.reason)}",
        ]
        if position == 0:
            body += _field_lines("set\t", _body_fields(statement))
        else:
            body += _change_lines("change", thread.versions[position - 1].statement, statement)
        shown.append((version.id, body))
    for event_id, recorded_at, rejection in rejections:
        head = "\t".join(
            (
                "rejection",
                str(event_id),
                iso_utc(recorded_at),
                escape_field(rejection.author),
                f"rejects {rejection.of}",
            )
        )
        reason = _NO_VALUE if rejection.reason is None else rejection.reason
        shown.append((event_id, [head, f"reason\t{escape_field(reason)}"]))
    for _event_id, body in sorted(shown):
        lines += body
    return lines


def _rejections_of(
    storage: PostgresStorage, conn: Connection, thread: Thread
) -> list[tuple[int, datetime, AssertionStatement]]:
    named = {version.id for version in thread.versions}
    found: list[tuple[int, datetime, AssertionStatement]] = []
    for row in storage.read_by_kind(conn, ASSERTION):
        statement = None if row.payload is None else parse_statement(row.payload)
        if statement is not None and statement.kind == REJECTION and statement.of in named:
            found.append((row.id, row.recorded_at, statement))
    return found


def _show_assertion(args: argparse.Namespace, kind: str) -> int:
    today = _utc_today()
    with _storage() as storage, storage.snapshot() as conn:
        threads = read_threads(storage, conn)
        thread = threads.get(args.id)
        winner = None if thread is None or thread.kind != kind else thread.winner()
        if thread is None or winner is None:
            print(f"no {kind} stands under event {args.id}", file=sys.stderr)
            return 1
        if args.history:
            lines = _history_lines(thread, _rejections_of(storage, conn, thread))
        else:
            lines = _entry_lines(thread, winner, today, _replaced_by(threads).get(thread.subject))
    for line in lines:
        print(line)
    return 0


def _cmd_obligation(args: argparse.Namespace) -> int:
    return _show_assertion(args, OBLIGATION)


def _cmd_decision(args: argparse.Namespace) -> int:
    return _show_assertion(args, DECISION)


def _listing(parser: argparse.ArgumentParser, states: Sequence[str]) -> None:
    parser.add_argument(
        "--circle", help="only what concerns this circle: its sources or its parties"
    )
    parser.add_argument("--state", choices=states, help="only this state")
    parser.add_argument(
        "--proposals",
        action="store_true",
        help="list what has a proposal pending, or stands as one, instead of what stands",
    )


def _obligations_arguments(parser: argparse.ArgumentParser) -> None:
    _listing(parser, OBLIGATION_STATES)
    parser.add_argument("--owed-by", help="only this debtor, a reference")
    parser.add_argument("--owed-to", help="only this creditor, a reference")
    parser.add_argument(
        "--overdue", action="store_true", help="only what is open and past its due date"
    )


def _decisions_arguments(parser: argparse.ArgumentParser) -> None:
    _listing(parser, DECISION_STATES)


def _entry_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("id", type=int, help="the id of the first version")
    parser.add_argument("--history", action="store_true", help="every version, in chain order")


# --- MCP clients ---------------------------------------------------------------


def _client_arguments(parser: argparse.ArgumentParser) -> None:
    what = parser.add_subparsers(dest="what", required=True)

    def writing(name: str, sentence: str) -> argparse.ArgumentParser:
        form = what.add_parser(name, help=sentence, description=sentence)
        form.add_argument("name")
        form.add_argument(
            "--statement", required=True, help="the sentence it was set with; it stays in the log"
        )
        form.add_argument("--yes", action="store_true", help="write without asking")
        return form

    add = writing("add", "create a client and print its token once")
    add.add_argument(
        "--processor", required=True, metavar="PROVIDER", help="a declared provider's promise"
    )
    writing("revoke", "lift a client; its token stops matching")
    sentence = "list the clients in force"
    what.add_parser("list", help=sentence, description=sentence)


def _cmd_client_add(args: argparse.Namespace) -> int:
    """Asks, writes the client and prints its token: the only place the
    token ever appears. A refusal and the replacement of a client come
    before the question, so nobody confirms what cannot be written or what
    they did not know they were replacing."""
    with _storage() as storage:
        with storage.begin() as conn:
            current = read_policy(storage, conn)
        # Only the form and the processor are checked here, and neither
        # depends on the hash: a placeholder of the right length stands in
        # for a hash that does not exist before the token does.
        placeholder = Client(args.name, args.processor, token_hash(""))
        sentence = refusal(placeholder, statement=args.statement, revoked=False, current=current)
        if sentence is not None:
            raise PolicyRefused(sentence)
        replaced = args.name in current.clients
        if replaced:
            print(
                f"client {escape_field(args.name)} exists: this replaces it, "
                "and its token stops working",
                file=sys.stderr,
            )
        print(f"client {escape_field(args.name)}\tprocessor {escape_field(args.processor)}")
        if not _confirmed(args):
            print("nothing written", file=sys.stderr)
            return 1
        _event_id, token = add_client(
            storage,
            args.name,
            processor=args.processor,
            statement=args.statement,
            recorded_at=datetime.now(UTC),
        )
    print(f"client {escape_field(args.name)}: token {token}")
    print("shown once; store it now")
    return 0


def _cmd_client_revoke(args: argparse.Namespace) -> int:
    with _storage() as storage:
        with storage.begin() as conn:
            if args.name not in read_policy(storage, conn).clients:
                raise PolicyRefused(f'no client "{args.name}" exists')
        print(f"revoke client {escape_field(args.name)}")
        if not _confirmed(args):
            print("nothing written", file=sys.stderr)
            return 1
        event_id = revoke_client(
            storage, args.name, statement=args.statement, recorded_at=datetime.now(UTC)
        )
    print(f"policy event {event_id}")
    return 0


def _cmd_client(args: argparse.Namespace) -> int:
    """Adds, revokes or lists the MCP clients. The list shows the name, the
    processor and the date of the event, never the hash."""
    if args.what == "add":
        return _cmd_client_add(args)
    if args.what == "revoke":
        return _cmd_client_revoke(args)
    with _storage() as storage, storage.begin() as conn:
        rows = client_rows(storage, conn)
    if not rows:
        print("no client exists", file=sys.stderr)
    for row in rows:
        print(
            f"{escape_field(row.client.name)}\t{escape_field(row.client.processor)}"
            f"\t{iso_utc(row.recorded_at)}"
        )
    return 0


# --- The MCP server ------------------------------------------------------------

# Where `previously serve` listens unless told otherwise: the loopback address,
# so that nothing outside the machine reaches it without a decision.
MCP_ADDRESS = "127.0.0.1:8765"


def _cmd_mcp(_args: argparse.Namespace) -> int:
    """Serves MCP over stdin and stdout for the client named in
    `PREVIOUSLY_MCP_CLIENT` ({ref}`cli-reference`).

    Over stdio there is no token: whoever starts the process is the client.
    The name has to be a client in force, checked before a request is read;
    a revocation while the process runs locks the client out from its next
    call, because every call reads the policy again.
    Nothing is printed: standard output is the protocol.

    The server module is imported here and not at the head, as the adapters
    of the gate are: the MCP SDK, Starlette and uvicorn add about 0.3 s to
    the import, measured on 2026-10-11 with `python -X importtime -c "import
    previously.cli, previously.mcp_server.server"` at 0.67 s against 0.36 s
    for `previously.cli` alone, cumulative, three runs each; every other
    command would pay for it.
    """
    from previously.mcp_server.server import CLIENT_VARIABLE
    from previously.mcp_server.server import run_stdio

    name = os.environ.get(CLIENT_VARIABLE)
    if not name:
        raise PreviouslyError(f"{CLIENT_VARIABLE} is not set: name the client this process serves")
    with _storage() as storage:
        with storage.begin() as conn:
            if name not in read_policy(storage, conn).clients:
                raise PreviouslyError(
                    f'no client "{name}" is in force; add it with previously client add'
                )
        run_stdio(storage, name)
    return 0


def _mcp_address() -> tuple[str, int]:
    """`PREVIOUSLY_MCP_ADDRESS`, or `MCP_ADDRESS` when it is unset or empty.
    `PREVIOUSLY_MCP_HOST` is refused for the reason `_imap_address` gives."""
    text = os.environ.get("PREVIOUSLY_MCP_ADDRESS")
    if not text:
        if os.environ.get("PREVIOUSLY_MCP_HOST"):
            raise PreviouslyError(
                "PREVIOUSLY_MCP_HOST is not read any more: set PREVIOUSLY_MCP_ADDRESS to host:port"
            )
        text = MCP_ADDRESS
    return parse_address("PREVIOUSLY_MCP_ADDRESS", text, default_port=None)


def _cmd_serve(_args: argparse.Namespace) -> int:
    """Serves MCP over HTTP under `/mcp` until stopped ({ref}`cli-reference`).

    Every request needs the bearer token of a client in force. The host check
    against DNS rebinding lets through the loopback names and those in
    `PREVIOUSLY_MCP_ALLOWED_HOSTS`, separated by commas or blanks.

    The server module is imported here for the reason `_cmd_mcp` gives.
    """
    from previously.mcp_server.server import run_http

    host, port = _mcp_address()
    allowed = (os.environ.get("PREVIOUSLY_MCP_ALLOWED_HOSTS") or "").replace(",", " ").split()
    where = f"[{host}]:{port}" if ":" in host else f"{host}:{port}"
    with _storage() as storage:
        print(f"serving MCP over HTTP on http://{where}/mcp", file=sys.stderr)
        run_http(storage, host=host, port=port, allowed_hosts=allowed)
    return 0


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
    # First, because it comes first in the life of a database: nothing else
    # runs before the schema stands.
    Command("migrate", "bring the database schema up to the newest revision", _cmd_migrate),
    Command("append", "submit text", _cmd_append, _append_arguments),
    Command("ingest", "take in new mail from IMAP folders", _cmd_ingest, _ingest_arguments),
    Command("redact", "erase an event, units of it, or a blob", _cmd_redact, _redact_arguments),
    # "print the chronicle" until stage 1b, which is now the other command:
    # `log` is the chain order and `chronicle` the chronology ({ref}`projections`).
    Command("log", "print the log in chain order", _cmd_log, _log_arguments),
    Command("verify", "check the chain, and anchors if given", _cmd_verify, _verify_arguments),
    Command("anchor", "print the tip of an intact chain as an anchor line", _cmd_anchor),
    Command("show", "show one event with its units", _cmd_show, _show_arguments),
    Command("blob", "fetch a stored blob into a file", _cmd_blob_get, _blob_arguments),
    Command("project", "bring the projections up to the tip of the log", _cmd_project),
    Command("chronicle", "print the chronicle in time order", _cmd_chronicle, _chronicle_arguments),
    Command("stats", "print the per-source statistics", _cmd_stats),
    Command("policy", "set and show the processing policy", _cmd_policy, _policy_arguments),
    Command("gate", "explain or try a model call", _cmd_gate, _gate_arguments),
    Command("client", "add, revoke and list MCP clients", _cmd_client, _client_arguments),
    Command("access", "show what MCP clients saw", _cmd_access, _access_arguments),
    Command("assert", "state an obligation or a decision", _cmd_assert, _assert_arguments),
    Command("approve", "make proposals your own", _cmd_approve, _approve_arguments),
    Command("reject", "reject a proposal", _cmd_reject, _reject_arguments),
    Command("obligations", "list what is owed", _cmd_obligations, _obligations_arguments),
    Command("obligation", "show one obligation", _cmd_obligation, _entry_arguments),
    Command("decisions", "list what was decided", _cmd_decisions, _decisions_arguments),
    Command("decision", "show one decision", _cmd_decision, _entry_arguments),
    Command("mcp", "serve MCP over stdio", _cmd_mcp),
    Command("serve", "serve MCP over HTTP", _cmd_serve),
)


# What a process ends with when a signal ended it, by the shell's convention:
# 128 and the signal's number, 143 for `SIGTERM`.
_SIGNAL_EXIT_BASE = 128


def _terminate(signum: int, frame: FrameType | None) -> None:
    """Ends the command on `SIGTERM` the way an exception would.

    In a container, `previously` runs as process 1, and the kernel delivers no
    signal to process 1 that it has left at the default action: measured on
    2026-10-05, `docker stop` on a `migrate` waiting for the lock waited its
    whole ten seconds and ended in `SIGKILL`, exit code 137. Kubernetes stops
    a pod the same way.

    `SystemExit` and not `os._exit`: it unwinds the stack, so every `with`
    closes, an open transaction rolls back, and a migration that was running
    leaves the schema where it found it. psycopg cancels a query it waits on
    when `SystemExit` or `KeyboardInterrupt` reaches it, so a `migrate`
    waiting for the lock lets go of it at once. A second `SIGTERM` during
    that unwinding is ignored, so that it cannot break into the cleanup.
    """
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    raise SystemExit(_SIGNAL_EXIT_BASE + signum)


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
    # broken the gate. The `finally` that puts the handler of `SIGTERM` back
    # adds nothing either: measured the same way on 2026-10-05, still 3.
    run = {command.name: command.run for command in COMMANDS}
    # Set for the command and put back after it, so that a caller that goes
    # on after `main` returns, such as the test suite, keeps its own handler.
    previous = signal.signal(signal.SIGTERM, _terminate)
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
        # The sentence can quote a key, and the key of a mail is the
        # mail's Message-ID (`escape_controls`).
        print(f"Error: {escape_controls(str(error))}", file=sys.stderr)
        return 2
    finally:
        signal.signal(signal.SIGTERM, previous)
