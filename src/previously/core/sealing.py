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
from typing import cast
from typing import TYPE_CHECKING

import hashlib
import pyrage


if TYPE_CHECKING:
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


def seal(source: ByteSource, sink: ByteSink, recipient: str) -> None:
    """Seals what `source` gives to `recipient` and writes the `age` file
    into `sink`, a piece at a time.

    A recipient is public, so a malformed one is quoted in the message.
    """
    try:
        to = pyrage.x25519.Recipient.from_str(recipient)
    except pyrage.RecipientError:
        raise InvalidKey(f"{recipient!r} is not an age X25519 recipient") from None
    # pyrage-stubs ask for `BufferedIOBase`; at run time `read` and `write`
    # suffice, measured with a source that has nothing but `read` and a sink
    # that has nothing but `write` (`tests/test_sealing.py`).
    try:
        pyrage.encrypt_io(cast("BufferedIOBase", source), cast("BufferedIOBase", sink), [to])
    except pyrage.EncryptError as error:
        # `pyrage` wraps an exception the source raises into its own type,
        # with the original's name and message as text and no cause. The
        # text is kept; the type is not, so no `pyrage` type leaves `core`.
        raise BlobError(f"cannot seal: {error}") from None


def unseal(source: ByteSource, sink: ByteSink, identity: str) -> None:
    """Opens the `age` file that `source` gives with `identity` and writes the
    plaintext into `sink`, a piece at a time.

    An exception the source or the sink raises passes through unchanged:
    `pyrage` does not wrap them when it opens, measured on 2026-10-05. So a
    store whose stream breaks off is reported by the store's own error, not
    as a file that cannot be opened.
    """
    key = _identity(identity)
    # The same two casts as in `seal`, for the same reason.
    try:
        pyrage.decrypt_io(cast("BufferedIOBase", source), cast("BufferedIOBase", sink), [key])
    except pyrage.DecryptError as error:
        # The message is `age`'s, and it never contains the identity: "No
        # matching keys found" for the wrong one, "failed to fill whole
        # buffer" for bytes that are not an age file.
        raise CannotOpen(str(error)) from None


class HashingSink:
    """Hashes and counts what passes through on its way to `sink`.

    The reader puts it between the opening and the caller's sink, so the
    address is checked against what was actually written, without a second
    pass over the plaintext.
    """

    def __init__(self, sink: ByteSink) -> None:
        self._sink = sink
        self._digest = hashlib.sha256()
        self.size = 0

    def write(self, data: bytes, /) -> int:
        self._digest.update(data)
        self.size += len(data)
        return self._sink.write(data)

    def hexdigest(self) -> str:
        return self._digest.hexdigest()
