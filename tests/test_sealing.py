# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sealing and opening in the `age` format, without a container ({ref}`blobs`).

The identities are made at run time by `age_identity` and never written into
the tree: the repository is public.
"""

from previously.core.errors import BlobError
from previously.core.errors import CannotOpen
from previously.core.errors import InvalidKey
from previously.core.errors import SinkUnwritable
from previously.core.errors import SourceUnreadable
from previously.core.sealing import HashingSink
from previously.core.sealing import recipient_of
from previously.core.sealing import seal
from previously.core.sealing import unseal

import errno
import hashlib
import io
import pytest


# A plaintext that cannot turn up in a ciphertext by chance: 4800 bytes of a
# sentence nobody would encrypt to.
CONSPICUOUS = b"the plaintext of this test, plainly legible. " * 100


class OnlyRead:
    """A source with nothing but `read` — what `pyrage` needs at run time,
    although its stubs ask for a `BufferedIOBase`."""

    def __init__(self, data: bytes) -> None:
        self._inner = io.BytesIO(data)

    def read(self, size: int = -1, /) -> bytes:
        return self._inner.read(size)


class OnlyWrite:
    """A sink with nothing but `write`."""

    def __init__(self) -> None:
        self.data = bytearray()

    def write(self, data: bytes, /) -> int:
        self.data.extend(data)
        return len(data)


class BreaksOff:
    """A source whose `read` raises, the way a file on a failing disk does."""

    def read(self, size: int = -1, /) -> bytes:
        raise OSError("the disk went away")


def _sealed(plaintext: bytes, recipient: str) -> bytes:
    sink = io.BytesIO()
    seal(io.BytesIO(plaintext), sink, recipient)
    return sink.getvalue()


def _opened(sealed: bytes, identity: str) -> bytes:
    sink = io.BytesIO()
    unseal(io.BytesIO(sealed), sink, identity)
    return sink.getvalue()


def test_what_is_sealed_opens_to_the_same_bytes(age_identity: str) -> None:
    sealed = _sealed(CONSPICUOUS, recipient_of(age_identity))
    assert _opened(sealed, age_identity) == CONSPICUOUS


def test_the_sealed_form_is_an_age_file_and_does_not_contain_the_plaintext(
    age_identity: str,
) -> None:
    sealed = _sealed(CONSPICUOUS, recipient_of(age_identity))
    assert sealed.startswith(b"age-encryption.org/v1")
    assert b"plainly legible" not in sealed


def test_an_empty_plaintext_seals_and_opens(age_identity: str) -> None:
    """Review focus 2 of the 2026-10-04 stage 1c plan: an empty file is a
    content like any other, and `age` gives it a header and one empty chunk."""
    sealed = _sealed(b"", recipient_of(age_identity))
    assert sealed.startswith(b"age-encryption.org/v1")
    assert _opened(sealed, age_identity) == b""


def test_a_source_with_nothing_but_read_and_a_sink_with_nothing_but_write_suffice(
    age_identity: str,
) -> None:
    sealed = OnlyWrite()
    seal(OnlyRead(CONSPICUOUS), sealed, recipient_of(age_identity))
    opened = OnlyWrite()
    unseal(OnlyRead(bytes(sealed.data)), opened, age_identity)
    assert bytes(opened.data) == CONSPICUOUS


def test_the_wrong_identity_cannot_open(age_identity: str, other_age_identity: str) -> None:
    sealed = _sealed(CONSPICUOUS, recipient_of(age_identity))
    with pytest.raises(CannotOpen):
        _opened(sealed, other_age_identity)


def test_garbage_cannot_be_opened(age_identity: str) -> None:
    with pytest.raises(CannotOpen):
        _opened(b"not an age file at all", age_identity)


@pytest.mark.parametrize("text", ["nonsense", ""])
@pytest.mark.parametrize("role", ["recipient", "identity"])
def test_a_recipient_or_identity_that_is_none_is_refused(
    role: str, text: str, age_identity: str
) -> None:
    """A recipient is public and may be named; an identity is the secret
    half, and a message that quoted a malformed one would print whatever
    somebody had put in its place — a real identity with a typo in it."""
    sealed = _sealed(b"x", recipient_of(age_identity))
    with pytest.raises(InvalidKey) as caught:
        if role == "recipient":
            seal(io.BytesIO(b"x"), io.BytesIO(), text)
        else:
            _opened(sealed, text)
    message = str(caught.value)
    if role == "recipient":
        assert repr(text) in message
    else:
        assert "identity" in message
        assert "nonsense" not in message


def test_recipient_of_gives_the_public_half(age_identity: str) -> None:
    recipient = recipient_of(age_identity)
    assert recipient.startswith("age1")
    assert recipient != age_identity
    assert _opened(_sealed(b"x", recipient), age_identity) == b"x"


def test_recipient_of_does_not_quote_a_malformed_identity(age_identity: str) -> None:
    mangled = age_identity[:-4] + "qqqq"
    with pytest.raises(InvalidKey) as caught:
        recipient_of(mangled)
    assert mangled not in str(caught.value)
    assert age_identity[20:40] not in str(caught.value)


def test_a_source_that_breaks_off_while_sealing_is_a_blob_error(age_identity: str) -> None:
    """`pyrage` wraps an exception raised by the source into its own
    `EncryptError`; `seal` translates that, so no `pyrage` type leaves `core`."""
    with pytest.raises(BlobError, match="the disk went away"):
        seal(BreaksOff(), io.BytesIO(), recipient_of(age_identity))


class Full:
    """A sink that fails the way a full disk does, at every write."""

    def write(self, data: bytes, /) -> int:
        raise OSError(errno.ENOSPC, "No space left on device")


class StoreBrokeOff(Exception):
    """What a store's stream raises when it breaks off — not an `OSError`."""


class BreaksOffAt:
    """A source that gives `data` for `reads` reads and then raises
    `StoreBrokeOff`."""

    def __init__(self, data: bytes, reads: int) -> None:
        self._inner = io.BytesIO(data)
        self._left = reads

    def read(self, size: int = -1, /) -> bytes:
        if self._left == 0:
            raise StoreBrokeOff("the store broke off")
        self._left -= 1
        return self._inner.read(size)


# Ruling T6-c of the 2026-10-04 stage 1c plan. Measured on 2026-10-05 against
# `pyrage` 1.4.0, before `seal` and `unseal` watched for themselves: with a
# sink whose `write` raises, `encrypt_io` *returned* for a content of 12
# bytes (one write call) and raised its own `EncryptError` for 70,000 bytes
# and 1 MiB; `decrypt_io` let the sink's `OSError` through at all three
# sizes. A source that failed at the first read of `decrypt_io` came back as
# `DecryptError`, whatever it raised; at a later read it passed through.
SIZES = pytest.mark.parametrize("size", [12, 70_000], ids=["12-bytes", "70000-bytes"])


@SIZES
def test_seal_into_a_sink_that_fails_does_not_return(age_identity: str, size: int) -> None:
    with pytest.raises(SinkUnwritable) as caught:
        seal(io.BytesIO(b"x" * size), Full(), recipient_of(age_identity))
    assert caught.value.reason == "No space left on device"


@SIZES
def test_unseal_into_a_sink_that_fails_does_not_return(age_identity: str, size: int) -> None:
    sealed = _sealed(b"x" * size, recipient_of(age_identity))
    with pytest.raises(SinkUnwritable) as caught:
        unseal(io.BytesIO(sealed), Full(), age_identity)
    assert caught.value.reason == "No space left on device"


def test_a_source_that_fails_is_told_apart_from_a_sink(age_identity: str) -> None:
    """The source's `OSError` is `SourceUnreadable` in both directions, and
    what a store's stream raises comes through as itself even at the first
    read, where `pyrage` would have called it a file it cannot open."""
    with pytest.raises(SourceUnreadable):
        seal(BreaksOff(), io.BytesIO(), recipient_of(age_identity))
    with pytest.raises(SourceUnreadable):
        unseal(BreaksOff(), io.BytesIO(), age_identity)
    sealed = _sealed(b"x" * 200_000, recipient_of(age_identity))
    for reads in (0, 1, 3):
        with pytest.raises(StoreBrokeOff):
            unseal(BreaksOffAt(sealed, reads), io.BytesIO(), age_identity)


def test_the_hashing_sink_counts_and_hashes_what_passes() -> None:
    target = OnlyWrite()
    sink = HashingSink(target)
    assert sink.write(b"abc") == 3
    assert sink.write(b"") == 0
    assert sink.write(b"def") == 3
    assert sink.size == 6
    assert sink.hexdigest() == hashlib.sha256(b"abcdef").hexdigest()
    assert bytes(target.data) == b"abcdef"


class Takes:
    """A sink that takes at most `most` bytes per call and says so in the
    count it returns, the way an unbuffered file may."""

    def __init__(self, most: int) -> None:
        self.most = most
        self.data = bytearray()

    def write(self, data: bytes, /) -> int:
        taken = bytes(data[: self.most])
        self.data.extend(taken)
        return len(taken)


@pytest.mark.parametrize("size", [12, 70_000], ids=["12-bytes", "70000-bytes"])
def test_a_sink_that_takes_less_gets_the_rest_and_one_that_takes_nothing_fails(
    age_identity: str, size: int
) -> None:
    """Ruling T6-c of the 2026-10-04 stage 1c plan: a short write is
    finished, not lost, whatever `pyrage` makes of the count, in both
    directions; a sink that takes nothing is `SinkUnwritable`."""
    content = b"y" * size
    sealed = Takes(7)
    seal(io.BytesIO(content), sealed, recipient_of(age_identity))
    opened = Takes(7)
    unseal(io.BytesIO(bytes(sealed.data)), opened, age_identity)
    assert bytes(opened.data) == content
    with pytest.raises(SinkUnwritable) as caught:
        seal(io.BytesIO(content), Takes(0), recipient_of(age_identity))
    assert caught.value.reason == "the output took no bytes"
