# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Storing and fetching a blob: the address, "first wins", the two passes
over the source ({ref}`blobs`).

The address is the SHA-256 of the plaintext, so the same content is one
object however often it is stored, and the log, which names the address,
names which bytes are meant. The store sees only what `core.sealing` makes of
the content. Nothing here holds a whole content in memory: it passes through
in pieces, from a file to a file.
"""

from contextlib import ExitStack
from dataclasses import dataclass
from previously.core.errors import AddressMismatch
from previously.core.errors import BlobError
from previously.core.errors import CannotOpen
from previously.core.errors import SourceUnreadable
from previously.core.sealing import HashingSink
from previously.core.sealing import seal
from previously.core.sealing import unseal
from typing import TYPE_CHECKING

import hashlib
import tempfile


if TYPE_CHECKING:
    from previously.contract.blobs import BlobStore
    from previously.contract.blobs import ByteSink
    from previously.contract.blobs import ByteSource
    from previously.contract.blobs import KeyProvider
    from previously.contract.blobs import SeekableSource


# The size of a piece read while hashing. A mebibyte keeps the number of
# calls small without making the piece itself a matter of memory.
_PIECE = 1024 * 1024


@dataclass(frozen=True)
class Stored:
    """What `store_blob` did.

    `address` is the SHA-256 of the plaintext, in hex; `size` the plaintext's
    size in bytes; `uploaded` is `False` when the object was already there.
    """

    address: str
    size: int
    uploaded: bool


def address_of(source: SeekableSource) -> tuple[str, int]:
    """The address and the size of what `source` holds, read from its start
    and rewound to it afterwards."""
    digest = hashlib.sha256()
    size = 0
    source.seek(0)
    while piece := source.read(_PIECE):
        digest.update(piece)
        size += len(piece)
    source.seek(0)
    return digest.hexdigest(), size


def store_blob(store: BlobStore, source: SeekableSource, *, recipient: str) -> Stored:
    """Stores what `source` holds, sealed to `recipient`, under its address.

    Two passes over the source: the address has to be known before the
    upload, so the first pass hashes and the second seals. The sealed form
    goes into a temporary file and is uploaded from there; that costs disk
    space the size of the blob for as long as this call runs, and keeps
    memory bounded.

    **First wins.** When an object lies under the address, nothing is
    uploaded, and the object keeps the key it is sealed to — after a change
    of key too. This is a look and then an action, not a lock: two writers
    that store the same new content at the same moment both see nothing and
    both upload, and one whole ciphertext stays, with the key that belongs to
    it beside it. Whoever reads it at that moment can see the read break off.
    The writer also trusts what lies there; it has no identity to check it
    with.

    The recipient is written beside the object in lower case, the canonical
    spelling of Bech32: `age` accepts either case, and the reader looks the
    key up by that name.

    Raises `SourceUnreadable` when the source fails while it is read, in
    either pass, and `BlobError` when the temporary file cannot be made,
    written or rewound. A store error passes through as it is.
    """
    try:
        address, size = address_of(source)
    except OSError as error:
        raise SourceUnreadable(reason_of(error)) from None
    if store.stat(address) is not None:
        return Stored(address=address, size=size, uploaded=False)
    with ExitStack() as files:
        # Making the temporary file and rewinding it; the writes into it are
        # watched in `seal_into`, because `pyrage` hides them. The upload
        # stands outside: it reads the file inside the store's client, and
        # what fails there is the store's to name. That the client turns
        # every failure of its own into a `botocore` error, which the store
        # translates, is assumed and not measured; an `OSError` it let
        # through would leave here as it is.
        try:
            sealed = files.enter_context(tempfile.TemporaryFile())
            seal_into(source, sealed, recipient)
            sealed.seek(0)
        except OSError as error:
            raise BlobError(f"cannot write a temporary file: {reason_of(error)}") from None
        store.put(address, sealed, key_id=recipient.lower())
    return Stored(address=address, size=size, uploaded=True)


def reason_of(error: OSError) -> str:
    """The system's description of an `OSError`, or its class when it has
    none: an `OSError` raised without an error number has `strerror` set to
    `None`, which would print as the word.

    Public because the command line uses the same rule for the errors it
    names itself."""
    return error.strerror or type(error).__name__


class _WatchedSource:
    """A source that remembers the `OSError` its `read` raised."""

    def __init__(self, source: ByteSource) -> None:
        self._source = source
        self.failure: OSError | None = None

    def read(self, size: int = -1, /) -> bytes:
        try:
            return self._source.read(size)
        except OSError as error:
            self.failure = error
            raise


class _WatchedSink:
    """A sink that remembers the `OSError` its `write` raised."""

    def __init__(self, sink: ByteSink) -> None:
        self._sink = sink
        self.failure: OSError | None = None

    def write(self, data: bytes, /) -> int:
        try:
            return self._sink.write(data)
        except OSError as error:
            self.failure = error
            raise


def seal_into(source: ByteSource, sink: ByteSink, recipient: str) -> None:
    """The sealing pass, with what failed named by kind: the source as
    `SourceUnreadable`, the sink — the temporary file — as a `BlobError`
    that says so ({ref}`blobs`).

    Both are watched, because `pyrage` hides which one it was. It wraps an
    `OSError` of either into its own error, with the original's name and
    message as text and no cause: measured on 2026-10-05, `cannot seal:
    OSError: [Errno 5] Input/output error` for a source, and `[Errno 28] No
    space left on device` the same way for a sink. And for a content of
    12 bytes, a sink whose one write failed made `pyrage` return as though
    it had sealed — no error at all, and a temporary file without the sealed
    form, which would have been uploaded. So the sink is asked after a
    return as well as after an error.

    Public because a test hands it a sink of its own that fails.
    """
    watched_source = _WatchedSource(source)
    watched_sink = _WatchedSink(sink)
    try:
        seal(watched_source, watched_sink, recipient)
    except BlobError:
        if watched_source.failure is not None:
            raise SourceUnreadable(reason_of(watched_source.failure)) from None
        if watched_sink.failure is None:
            raise
    if watched_sink.failure is not None:
        raise BlobError(f"cannot write a temporary file: {reason_of(watched_sink.failure)}")


def fetch_blob(store: BlobStore, keys: KeyProvider, address: str, sink: ByteSink) -> int | None:
    """Fetches the object under `address`, opens it, writes the plaintext
    into `sink` and returns its size — or `None` when there is no object.

    The key is the one the object names, not the caller's: after a change of
    key, or when two writers raced, the object may be sealed to a key the
    caller did not write with.

    **This writes into `sink` before it knows whether the address holds.**
    The plaintext is checked against the address as it passes and compared
    at the end, so on `AddressMismatch` the sink already holds bytes that are
    not the content. Whoever fetches into a file writes into a temporary one
    and renames it only after this returns.

    Raises `CannotOpen` when the object names no key, when there is no
    identity for its key, or when `age` cannot open it — an identity of
    another key included; `InvalidKey` when what the key source holds for
    the key is not an age identity; `AddressMismatch` when the plaintext is
    not the content the address names. A store error passes through as it
    is, a stream that breaks off included, and so does an error of the key
    source — `DirectoryKeys` raises `IdentityUnreadable` for an identity file
    that is there and cannot be read. The stream is closed on every path,
    whatever is raised.
    """
    found = store.get(address)
    if found is None:
        return None
    stored, stream = found
    # Closed on every path. A stream left unread holds its connection for as
    # long as anything refers to it, and an error raised here refers to it
    # through its traceback: a caller that keeps the errors of a long run,
    # fetching blob after blob through one store, would keep one connection
    # per failed fetch. Measured on 2026-10-05 in
    # `test_a_fetch_that_fails_gives_its_connection_back`.
    try:
        if stored.key_id is None:
            raise CannotOpen(f"the object {address} names no key it is sealed to")
        identity = keys.identity(stored.key_id)
        if identity is None:
            raise CannotOpen(f"there is no identity for the key {stored.key_id!r}")
        # Whether the identity belongs to the key is not checked here: `age`
        # refuses an identity of another key with "No matching keys found",
        # and with the check taken out the test of exactly that case stayed
        # green, measured on 2026-10-05. A check that adds nothing is not kept.
        hashing = HashingSink(sink)
        unseal(stream, hashing, identity)
    finally:
        stream.close()
    if hashing.hexdigest() != address:
        raise AddressMismatch(f"the object {address} opens to {hashing.hexdigest()}")
    return hashing.size
