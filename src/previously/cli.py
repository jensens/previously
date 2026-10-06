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
from datetime import datetime
from datetime import UTC
from pathlib import Path
from previously.connectors.imap import ImapConnector
from previously.connectors.imap import PORT as IMAP_PORT
from previously.contract.types import BlobRef
from previously.contract.types import Evidence
from previously.contract.types import RawEvent
from previously.core.anchor import format_anchor
from previously.core.anchor import parse_anchors
from previously.core.append import append
from previously.core.append import check_units
from previously.core.blob import fetch_blob
from previously.core.blob import store_blob
from previously.core.chain import read_references
from previously.core.errors import AddressMismatch
from previously.core.errors import CannotOpen
from previously.core.errors import InvalidPayload
from previously.core.errors import PreviouslyError
from previously.core.errors import reason_of
from previously.core.errors import RedactionRefused
from previously.core.errors import SinkUnwritable
from previously.core.errors import SourceUnreadable
from previously.core.hashing import is_address
from previously.core.identity import artifact_hash_of
from previously.core.ingest import ingest
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
from previously.core.units import split_plaintext
from previously.core.verify import BlobCheck
from previously.core.verify import examine
from previously.storage.errors import StorageError
from previously.storage.keys import DirectoryKeys
from previously.storage.migrate import migrate
from previously.storage.migrate import Migrated
from previously.storage.postgres import from_dsn
from previously.storage.postgres import PostgresStorage
from previously.storage.s3 import from_settings
from previously.storage.s3 import S3BlobStore
from typing import TYPE_CHECKING

import argparse
import io
import json
import mimetypes
import os
import signal
import ssl
import sys
import tempfile


if TYPE_CHECKING:
    from collections.abc import Sequence
    from previously.contract.blobs import BlobStore
    from previously.contract.blobs import KeyProvider
    from previously.contract.rows import EventRow
    from previously.contract.types import Anchor
    from previously.core.redact import Redacted
    from previously.core.redaction import Redaction
    from previously.core.redaction import RedactionIndex
    from previously.core.verify import Examination
    from previously.core.verify import Finding
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
        # The artifact is what was submitted: the text as given, and the
        # attachments by their addresses, sorted, so that their order on the
        # command line and their file names do not make another artifact
        # ({ref}`artifact-identity`). Not the units, which are derived.
        artifact = {"text": args.text, "attachments": sorted(blob.sha256 for blob in blobs)}
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
    sentence = "take in the mail an IMAP folder holds above the watermark of the last run"
    sources.add_parser("imap", help=sentence, description=sentence)


def _imap_port() -> int:
    """`PREVIOUSLY_IMAP_PORT`, or the port of IMAP over TLS when it is unset
    or empty, like every other setting that is empty."""
    text = os.environ.get("PREVIOUSLY_IMAP_PORT") or str(IMAP_PORT)
    if not (text.isascii() and text.isdigit() and 0 < int(text) < 65536):
        raise PreviouslyError(f"PREVIOUSLY_IMAP_PORT is not a port number: {text!r}")
    return int(text)


def _imap_connector() -> ImapConnector:
    """The folder out of its five settings, read before anything connects.

    The certificate is verified against the system's trust store, and so is
    the host name: `ssl.create_default_context()`, with no setting that turns
    it off. A server with a certificate of its own is trusted the way
    OpenSSL trusts anything, through `SSL_CERT_FILE` or the trust store, not
    through a switch of this command.
    """
    return ImapConnector(
        host=_setting("PREVIOUSLY_IMAP_HOST"),
        port=_imap_port(),
        user=_setting("PREVIOUSLY_IMAP_USER"),
        password=_setting("PREVIOUSLY_IMAP_PASSWORD"),
        folder=_setting("PREVIOUSLY_IMAP_FOLDER"),
        ssl_context=ssl.create_default_context(),
    )


def _cmd_ingest(_args: argparse.Namespace) -> int:
    """Takes in what the folder holds above its watermark ({ref}`cli-reference`).

    Every setting is read, and the recipient checked, before anything
    connects: the folder's five, the recipient, `PREVIOUSLY_DSN` and the
    store's five, in that order. The directory of identities is not among
    them: taking in seals and opens nothing.

    Standard output is one line, the counts and the UID the watermark stands
    at; `up to uid 0` is a folder that has given nothing yet, since a UID is
    never 0. Each variant is one line on standard error. The projections are
    not caught up: `project` does that, and the two may run side by side.
    """
    connector = _imap_connector()
    recipient = _recipient()
    with _storage() as storage, _blob_store() as store:
        result = ingest(
            storage, storage, store, connector, recipient=recipient, recorded_at=datetime.now(UTC)
        )
    for message_id, event_id in result.variants:
        print(f"variant of {message_id}: event {event_id}", file=sys.stderr)
    uid = "0" if result.position is None else result.position["uid"]
    print(
        f"imap: {result.appended} appended, {result.known} known, "
        f"{len(result.variants)} variants, up to uid {uid}"
    )
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
                print(f"payload={json.dumps(row.payload, ensure_ascii=False, sort_keys=True)}")
            for unit in storage.units(conn, row.id):
                # An erased unit says so, like the payload above, rather than
                # printing `None` where its text stood.
                content = unit.content
                if content is None:
                    content = _erased(index.of_unit(row.id, unit.seq))
                print(f"  ¶{unit.seq} {content}")
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
    # First, because it comes first in the life of a database: nothing else
    # runs before the schema stands.
    Command("migrate", "bring the database schema up to the newest revision", _cmd_migrate),
    Command("append", "submit text", _cmd_append, _append_arguments),
    Command("ingest", "take in new mail from an IMAP folder", _cmd_ingest, _ingest_arguments),
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
        print(f"Error: {error}", file=sys.stderr)
        return 2
    finally:
        signal.signal(signal.SIGTERM, previous)
