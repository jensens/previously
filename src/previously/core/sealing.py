# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sealing and opening in the `age` format, a piece at a time ({ref}`blobs`).

This is the one module that imports `pyrage`, and `.importlinter` holds it to
that. Sealing sits in `core` because that is where the rules are: the store
below gets ciphertext only, and the format a content is sealed in is part of
what the log promises about it.

`age` and not a scheme of this project's own: a standard format, sealed and
opened a piece at a time and therefore without a size limit, and readable in
an emergency with the `age` tool and the identity, without this software.

`pyrage` is imported as one module and its submodule reached through it. With
`from pyrage import x25519`, pyright warns `Import "pyrage.x25519" could not
be resolved from source` (measured on 2026-10-05): the submodule lives inside
the compiled extension, and only the stub from `pyrage-stubs` is a file.
"""

from previously.core.errors import BlobError
from previously.core.errors import CannotOpen
from previously.core.errors import InvalidKey
from previously.core.errors import reason_of
from previously.core.errors import SinkUnwritable
from previously.core.errors import SourceUnreadable
from typing import cast
from typing import TYPE_CHECKING

import hashlib
import pyrage


if TYPE_CHECKING:
    from collections.abc import Callable
    from io import BufferedIOBase
    from previously.contract.blobs import ByteSink
    from previously.contract.blobs import ByteSource


def _identity(identity: str) -> pyrage.x25519.Identity:
    """The parsed identity. The message does not quote what it was given:
    a malformed identity may be a real one with a typo in it, and `from None`
    keeps `pyrage`'s own exception out of the traceback as well."""
    try:
        return pyrage.x25519.Identity.from_str(identity)
    except pyrage.IdentityError:
        raise InvalidKey("the identity is not an age X25519 identity") from None


def recipient_of(identity: str) -> str:
    """The public half of an identity: the recipient that seals to it, in
    its `age1…` spelling."""
    return str(_identity(identity).to_public())


def _recipient(recipient: str) -> pyrage.x25519.Recipient:
    """The parsed recipient. A recipient is public, so a malformed one is
    quoted in the message."""
    try:
        return pyrage.x25519.Recipient.from_str(recipient)
    except pyrage.RecipientError:
        raise InvalidKey(f"{recipient!r} is not an age X25519 recipient") from None


def check_recipient(recipient: str) -> None:
    """Raises `InvalidKey` unless `recipient` is an age X25519 recipient.

    For a caller that has to know before it stores anything: `seal` checks
    the recipient too, but `core.blob.store_blob` calls it only for content
    the store does not hold yet, so a mistyped recipient would otherwise go
    unnoticed until new content arrives.
    """
    _recipient(recipient)


class _WatchedSource:
    """A source that remembers what its `read` raised."""

    def __init__(self, source: ByteSource) -> None:
        self._source = source
        self.failure: Exception | None = None

    def read(self, size: int = -1, /) -> bytes:
        try:
            return self._source.read(size)
        except Exception as error:
            self.failure = error
            raise


class _WatchedSink:
    """A sink that remembers what its `write` raised, and that writes all
    of what it is given or fails.

    An unbuffered file may take fewer bytes than it is given — at a file
    size limit, on a disk that fills up — and say so only in the count it
    returns. `encrypt_io` does not retry one either: with a sink that took
    seven bytes a call and this loop taken out, it raised `failed to write
    the buffered data` (measured on 2026-10-05) — no loss, but no reason
    either. So this wrapper writes the rest itself, and the write after a
    short one is the one that fails with the system's reason. A sink that
    takes nothing at all fails here.

    This is the one place that finishes a short write. What it wraps — the
    caller's sink, or `HashingSink` in front of it — passes on the count
    of what was taken and does not retry, so every byte reaches the sink
    once and is counted once.
    """

    def __init__(self, sink: ByteSink) -> None:
        self._sink = sink
        self.failure: Exception | None = None

    def write(self, data: bytes, /) -> int:
        try:
            done = 0
            while done < len(data):
                taken = self._sink.write(data[done:])
                if taken <= 0:
                    raise OSError("the output took no bytes")
                done += taken
        except Exception as error:
            self.failure = error
            raise
        return done


def _through(
    run: Callable[[BufferedIOBase, BufferedIOBase], object],
    source: ByteSource,
    sink: ByteSink,
    own: type[Exception],
) -> str | None:
    """Runs one of `pyrage`'s two calls over a watched source and sink, and
    says afterwards what went wrong, whatever `pyrage` made of it.

    A failure of the source or the sink is raised here, after the call and
    outside any `except`: an `OSError` of the source as `SourceUnreadable`,
    one of the sink as `SinkUnwritable`, and anything else — a store's error
    out of its stream — as itself. What is left is `pyrage`'s own refusal,
    `own`, whose text is returned for the caller to name.

    The casts: pyrage-stubs ask for `BufferedIOBase`; at run time `read`
    and `write` suffice, measured with a source that has nothing but `read`
    and a sink that has nothing but `write` (`tests/test_sealing.py`).
    """
    watched_source = _WatchedSource(source)
    watched_sink = _WatchedSink(sink)
    refusal: str | None = None
    try:
        run(cast("BufferedIOBase", watched_source), cast("BufferedIOBase", watched_sink))
    except own as error:
        refusal = str(error)
    except Exception:
        if watched_source.failure is None and watched_sink.failure is None:
            raise
    for failure, translated in (
        (watched_source.failure, SourceUnreadable),
        (watched_sink.failure, SinkUnwritable),
    ):
        if isinstance(failure, OSError):
            raise translated(reason_of(failure))
        if failure is not None:
            raise failure
    return refusal


def seal(source: ByteSource, sink: ByteSink, recipient: str) -> None:
    """Seals what `source` gives to `recipient` and writes the `age` file
    into `sink`, a piece at a time.

    A recipient is public, so a malformed one is quoted in the message.

    Raises `SourceUnreadable` or `SinkUnwritable` when the source or the
    sink fails with an `OSError`, and lets anything else either raises pass
    as it is. It watches both itself, because `pyrage` does not say which
    failed and does not always say that anything did: measured on 2026-10-05
    against `pyrage` 1.4.0, with a sink whose every write raises,
    `encrypt_io` returned normally for a content of 12 bytes, after one
    write, and raised its own `EncryptError` for 70,000 bytes and 1 MiB; a
    source that raised came back as that `EncryptError` at every size. Its
    other refusals are a `BlobError` with `age`'s text.
    """
    to = _recipient(recipient)
    refusal = _through(
        lambda source, sink: pyrage.encrypt_io(source, sink, [to]),
        source,
        sink,
        pyrage.EncryptError,
    )
    if refusal is not None:
        # The text is kept; the type is not, so no `pyrage` type leaves `core`.
        raise BlobError(f"cannot seal: {refusal}")


def unseal(source: ByteSource, sink: ByteSink, identity: str) -> None:
    """Opens the `age` file that `source` gives with `identity` and writes the
    plaintext into `sink`, a piece at a time.

    Raises `SourceUnreadable` or `SinkUnwritable` when the source or the
    sink fails with an `OSError`, and lets anything else either raises pass
    as it is — a store whose stream breaks off is reported by the store's
    own error. Measured on 2026-10-05 against `pyrage` 1.4.0: `decrypt_io`
    let a failing sink's `OSError` through at 12 bytes, 70,000 bytes and
    1 MiB alike, and let a source's error through at a later read, but at
    the first read, the header, turned it into its own `DecryptError`, which
    read as a file that cannot be opened. It watches both itself, so that
    neither depends on which call `pyrage` happens to be in.

    `CannotOpen` carries `age`'s message, which never contains the identity:
    "No matching keys found" for the wrong one, "failed to fill whole
    buffer" for bytes that are not an age file.
    """
    key = _identity(identity)
    refusal = _through(
        lambda source, sink: pyrage.decrypt_io(source, sink, [key]),
        source,
        sink,
        pyrage.DecryptError,
    )
    if refusal is not None:
        raise CannotOpen(refusal)


class HashingSink:
    """Hashes and counts what passes through on its way to `sink`.

    The reader puts it between the opening and the caller's sink, so the
    address is checked against what was actually written, without a second
    pass over the plaintext.

    It hashes and counts what `sink` took, not what it was given, and
    returns that count: finishing a short write is not its business but
    `unseal`'s, whose watched sink sends the rest again, and a byte that
    comes round a second time has to be counted only when it is taken. Fix
    round 2 of task 6, the 2026-10-04 stage 1c plan: counting what it was
    given made a sink that took seven bytes a call count 39,806,307 bytes
    for 70,000 and the address fail on correct bytes (re-review probe,
    2026-10-05).
    """

    def __init__(self, sink: ByteSink) -> None:
        self._sink = sink
        self._digest = hashlib.sha256()
        self.size = 0

    def write(self, data: bytes, /) -> int:
        taken = self._sink.write(data)
        self._digest.update(data[:taken])
        self.size += taken
        return taken

    def hexdigest(self) -> str:
        return self._digest.hexdigest()


class NullSink:
    """Takes bytes and throws them away, saying it took all of them.

    For a check that only needs what passes to be hashed — `verify --blobs`
    fetches every blob into one, through `HashingSink` — and nothing to be
    kept. It returns the length of what it was given, because `HashingSink`
    hashes and counts what its sink says it took.
    """

    def write(self, data: bytes, /) -> int:
        return len(data)
