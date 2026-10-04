# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The blob protocols: what `core` may ask of a blob store and of a key
source, and the byte streams that pass between them ({ref}`blobs`).

The store gets and gives **ciphertext only**. Sealing and opening happen in
`core.sealing`, so nothing behind `BlobStore` ever holds a plaintext or a key
that opens one.
"""

from dataclasses import dataclass
from typing import Protocol
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from typing import IO


class ByteSource(Protocol):
    """Something to read bytes from, a piece at a time. `read` returns
    `b""` at the end."""

    def read(self, size: int = -1, /) -> bytes: ...


class SeekableSource(ByteSource, Protocol):
    """A source that can be read twice: the address is the hash of the
    plaintext and has to be known before the upload, so the content is read
    once to hash it and once more to seal it. A file can do that."""

    def seek(self, offset: int, whence: int = 0, /) -> int: ...


class ByteSink(Protocol):
    """Something to write bytes into, a piece at a time."""

    def write(self, data: bytes, /) -> int: ...


@dataclass(frozen=True)
class StoredBlob:
    """What the store says about an object without opening it.

    `key_id` is the recipient the object is sealed to, as written beside it
    by whoever uploaded it, or `None` when the object names none. It is a
    hint and not a proof: whoever can change it can also delete the object.
    `sealed_size` is the size of the ciphertext.
    """

    key_id: str | None
    sealed_size: int


class BlobStore(Protocol):
    """Sealed objects under their addresses.

    `get` gives the metadata and the stream out of **one** answer of the
    store: two requests could see, while an object is being replaced, the key
    of one upload and the body of the other.

    `close` gives back the connections the store holds. It is the fifth
    method because a measurement asked for it: a store that is built per
    command and not closed keeps its connections until the garbage collector
    finds it (`storage.s3.S3BlobStore.close` has the figures).
    """

    def stat(self, address: str) -> StoredBlob | None: ...
    def put(self, address: str, sealed: IO[bytes], *, key_id: str) -> None: ...
    def get(self, address: str) -> tuple[StoredBlob, ByteSource] | None: ...
    def delete(self, address: str) -> None: ...
    def close(self) -> None: ...


class KeyProvider(Protocol):
    """The seam for keys: a `key_id` in, the identity that opens it out, as
    text — or `None` when there is none. As text, so that whatever provides
    it needs to know nothing about the `age` format."""

    def identity(self, key_id: str) -> str | None: ...
