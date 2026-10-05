# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Storing and fetching a blob, sealed, against a real S3 server
({ref}`blobs`).

The identities are made at run time and written into `tmp_path` only, as a
directory of files named after their recipients — the form `DirectoryKeys`
reads.
"""

from previously.core.blob import fetch_blob
from previously.core.blob import store_blob
from previously.core.errors import AddressMismatch
from previously.core.errors import BlobError
from previously.core.errors import CannotOpen
from previously.core.errors import SinkUnwritable
from previously.core.errors import SourceUnreadable
from previously.core.sealing import recipient_of
from previously.core.sealing import seal
from previously.core.sealing import unseal
from previously.storage.keys import DirectoryKeys
from previously.storage.s3 import from_settings
from typing import TYPE_CHECKING

import errno
import hashlib
import io
import os
import pytest
import resource
import sys
import tempfile
import threading


if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from previously.core.blob import Stored
    from previously.storage.s3 import S3BlobStore


pytestmark = pytest.mark.s3

# What the `s3_connections` fixture is, spelled here as `conftest.py` asks of
# a test that takes one of its callables.
type ConnectionCount = Callable[[], int]

# Rounds of the two-writer test. Both writers fetch in every round, so every
# round has a writer whose own recipient is not the key of the object that
# stayed, whichever of the two won — one round is enough to catch a reader
# that takes the key from the caller, and measured on 2026-10-05 that
# mutation went red in the first round. Which writer wins is timing (53
# against 45 over 98 rounds that day), so the test asserts nothing about it.
# Four rounds repeat the interleaving of the two uploads, which varies from
# round to round, for about half a second.
ROUNDS = 4
# The bound on the growth of the peak in `test_memory_stays_bounded`: the size
# of the blob, which is what the assurance says the path must not cost.
BOUND_MIB = 256
CONSPICUOUS = b"a content nobody would store in clear, plainly legible. " * 100


def _keys(tmp_path: Path, *identities: str) -> DirectoryKeys:
    directory = tmp_path / "keys"
    directory.mkdir(exist_ok=True)
    for identity in identities:
        (directory / recipient_of(identity)).write_text(identity + "\n", encoding="utf-8")
    return DirectoryKeys(str(directory))


def _objects(store: S3BlobStore) -> list[str]:
    listing = store.client.list_objects_v2(Bucket=store.bucket)
    return [entry.get("Key", "") for entry in listing.get("Contents", [])]


def _race(
    settings: dict[str, str],
    bucket: str,
    keys: DirectoryKeys,
    recipients: list[str],
    content: bytes,
) -> dict[int, tuple[Stored, int | None, bytes]]:
    """One round: two threads, each with a store of its own, released by one
    barrier to store `content` sealed to their own recipient, and released by
    a second, once both have stored, to fetch it back. What each stored and
    fetched, by writer; the first failure of either is raised here."""
    start = threading.Barrier(2)
    both_stored = threading.Barrier(2)
    results: dict[int, tuple[Stored, int | None, bytes]] = {}
    failures: list[Exception] = []

    def writer(number: int) -> None:
        store = from_settings(**settings, bucket=bucket)
        try:
            start.wait()
            stored = store_blob(store, io.BytesIO(content), recipient=recipients[number])
            both_stored.wait()
            fetched = io.BytesIO()
            size = fetch_blob(store, keys, stored.address, fetched)
            results[number] = (stored, size, fetched.getvalue())
        except Exception as error:  # handed to the main thread below
            failures.append(error)
            start.abort()
            both_stored.abort()
        finally:
            store.close()

    threads = [threading.Thread(target=writer, args=(number,)) for number in (0, 1)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    if failures:
        raise failures[0]
    return results


def test_the_store_sees_only_ciphertext(blob_store: S3BlobStore, age_identity: str) -> None:
    stored = store_blob(blob_store, io.BytesIO(CONSPICUOUS), recipient=recipient_of(age_identity))

    raw = blob_store.client.get_object(Bucket=blob_store.bucket, Key=stored.address)
    sealed = raw["Body"].read()
    assert sealed.startswith(b"age-encryption.org/v1")
    assert b"plainly legible" not in sealed
    opened = io.BytesIO()
    unseal(io.BytesIO(sealed), opened, age_identity)
    assert opened.getvalue() == CONSPICUOUS


def test_the_same_content_twice_is_one_object(blob_store: S3BlobStore, age_identity: str) -> None:
    recipient = recipient_of(age_identity)
    first = store_blob(blob_store, io.BytesIO(CONSPICUOUS), recipient=recipient)
    second = store_blob(blob_store, io.BytesIO(CONSPICUOUS), recipient=recipient)

    assert first.uploaded
    assert not second.uploaded
    assert first.address == second.address == hashlib.sha256(CONSPICUOUS).hexdigest()
    assert first.size == second.size == len(CONSPICUOUS)
    assert _objects(blob_store) == [first.address]


def test_an_object_under_a_foreign_address_is_not_delivered(
    blob_store: S3BlobStore, age_identity: str, tmp_path: Path
) -> None:
    """`age` does not bind a ciphertext to the address it lies under, so the
    reader hashes what it opens and compares at the end."""
    recipient = recipient_of(age_identity)
    foreign = hashlib.sha256(b"some other content").hexdigest()
    sealed = io.BytesIO()
    seal(io.BytesIO(CONSPICUOUS), sealed, recipient)
    sealed.seek(0)
    blob_store.put(foreign, sealed, key_id=recipient)

    with pytest.raises(AddressMismatch, match=foreign):
        fetch_blob(blob_store, _keys(tmp_path, age_identity), foreign, io.BytesIO())


@pytest.mark.skipif(sys.platform != "linux", reason="ru_maxrss is in KiB on Linux only")
def test_memory_stays_bounded(blob_store: S3BlobStore, age_identity: str, tmp_path: Path) -> None:
    """A blob of 256 MiB stored and fetched does not raise the memory of the
    process by its size.

    The test runs inside pytest, whose peak may already be higher than what
    this path needs, so it can only hold the growth of the peak
    (`ru_maxrss`, in KiB on Linux) and not the peak itself; and the content
    goes from file to file, never as one `bytes`.

    Measured on 2026-10-05, both sides of the bound. With the test run on its
    own, so that nothing before it raised the peak, the path grew it by 120
    MiB in three runs out of three; after the other tests of this file and
    of `tests/test_s3.py`, by 0. With `fetch_blob` mutated to read the object
    in one piece, by 478 to 502 MiB on its own, by 395 after the others, and
    by 502 and 453 within the whole suite, in fixed and in random order.
    The bound lies between the two.
    """
    size_mib = 256
    plain = tmp_path / "plain"
    block = os.urandom(1024 * 1024)
    with plain.open("wb") as handle:
        for _ in range(size_mib):
            handle.write(block)
    keys = _keys(tmp_path, age_identity)

    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    with plain.open("rb") as source:
        stored = store_blob(blob_store, source, recipient=recipient_of(age_identity))
    with (tmp_path / "opened").open("wb") as sink:
        size = fetch_blob(blob_store, keys, stored.address, sink)
    growth_mib = (resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - before) / 1024

    assert size == size_mib * 1024 * 1024
    assert growth_mib < BOUND_MIB, f"the peak grew by {growth_mib:.0f} MiB"


def test_two_writers_at_once_leave_one_whole_object_that_opens(
    blob_store: S3BlobStore,
    s3_settings: dict[str, str],
    age_identity: str,
    other_age_identity: str,
    tmp_path: Path,
) -> None:
    """Two writers store the same new content at the same moment, each sealed
    to a recipient of its own. "First wins" is a look before the upload and
    not a lock, so both see nothing and both upload; one ciphertext stays,
    whole, and each writer fetches the content back — which only works when
    the key is taken from the object, since the writer that lost wrote to a
    key the object is not sealed to.

    Both writers fetch in every round, so every round has a losing writer
    that fetches, whichever of the two won; which one won is not asserted,
    since that is timing and not the assurance. `ROUNDS` says why there are
    several rounds, each with a content of its own.
    """
    keys = _keys(tmp_path, age_identity, other_age_identity)
    recipients = [recipient_of(age_identity), recipient_of(other_age_identity)]
    for _ in range(ROUNDS):
        content = os.urandom(1024 * 1024)
        results = _race(s3_settings, blob_store.bucket, keys, recipients, content)

        address = hashlib.sha256(content).hexdigest()
        for stored, size, fetched in results.values():
            assert stored.address == address
            assert size == len(content)
            assert fetched == content
        assert address in _objects(blob_store)
        found = blob_store.stat(address)
        assert found is not None
        assert found.key_id in recipients
    assert len(_objects(blob_store)) == ROUNDS


def test_after_a_key_change_the_stored_object_keeps_its_key(
    blob_store: S3BlobStore, age_identity: str, other_age_identity: str, tmp_path: Path
) -> None:
    """A writer with a new recipient finds the content already there, does
    not upload, and the object stays sealed to the old key — so it is the old
    identity that fetches it."""
    old, new = recipient_of(age_identity), recipient_of(other_age_identity)
    first = store_blob(blob_store, io.BytesIO(CONSPICUOUS), recipient=old)
    second = store_blob(blob_store, io.BytesIO(CONSPICUOUS), recipient=new)

    assert not second.uploaded
    found = blob_store.stat(first.address)
    assert found is not None
    assert found.key_id == old
    fetched = io.BytesIO()
    assert fetch_blob(blob_store, _keys(tmp_path, age_identity), first.address, fetched) == len(
        CONSPICUOUS
    )
    assert fetched.getvalue() == CONSPICUOUS


def test_an_object_that_names_no_key_cannot_be_opened(
    blob_store: S3BlobStore, age_identity: str, tmp_path: Path
) -> None:
    sealed = io.BytesIO()
    seal(io.BytesIO(CONSPICUOUS), sealed, recipient_of(age_identity))
    address = hashlib.sha256(CONSPICUOUS).hexdigest()
    blob_store.client.put_object(Bucket=blob_store.bucket, Key=address, Body=sealed.getvalue())

    with pytest.raises(CannotOpen, match="names no key"):
        fetch_blob(blob_store, _keys(tmp_path, age_identity), address, io.BytesIO())


def test_an_object_whose_key_has_no_identity_cannot_be_opened(
    blob_store: S3BlobStore, age_identity: str, other_age_identity: str, tmp_path: Path
) -> None:
    """The key directory holds identities, only not the one for the key the
    object names. The message names the key, which is public."""
    recipient = recipient_of(age_identity)
    stored = store_blob(blob_store, io.BytesIO(CONSPICUOUS), recipient=recipient)

    with pytest.raises(CannotOpen, match=recipient):
        fetch_blob(blob_store, _keys(tmp_path, other_age_identity), stored.address, io.BytesIO())


def test_an_identity_file_that_holds_another_key_cannot_open(
    blob_store: S3BlobStore, age_identity: str, other_age_identity: str, tmp_path: Path
) -> None:
    """The file named after the object's recipient holds an identity of
    another key — a file copied under the wrong name."""
    recipient = recipient_of(age_identity)
    stored = store_blob(blob_store, io.BytesIO(CONSPICUOUS), recipient=recipient)
    directory = tmp_path / "keys"
    directory.mkdir()
    (directory / recipient).write_text(other_age_identity + "\n", encoding="utf-8")

    with pytest.raises(CannotOpen) as caught:
        fetch_blob(blob_store, DirectoryKeys(str(directory)), stored.address, io.BytesIO())
    assert other_age_identity not in str(caught.value)
    assert "AGE-SECRET-KEY" not in str(caught.value)


class _FailsOnTheSecondPass:
    """A source that reads like a file until it is rewound for the second
    pass, and then fails the way a disk does: an `OSError` with `EIO`. A
    small source of the test's own, not a stand-in for the store."""

    def __init__(self, content: bytes) -> None:
        self._content = io.BytesIO(content)
        self._passes = 0

    def seek(self, offset: int, whence: int = 0, /) -> int:
        if offset == 0 and whence == 0:
            self._passes += 1
        return self._content.seek(offset, whence)

    def read(self, size: int = -1, /) -> bytes:
        # `address_of` rewinds before its pass and after it, and `seal` reads
        # without rewinding: the reads after the second rewind are the
        # sealing pass.
        if self._passes >= 2:
            raise OSError(errno.EIO, "Input/output error")
        return self._content.read(size)


def test_a_source_that_fails_while_it_is_sealed_is_an_error_of_its_own(
    blob_store: S3BlobStore, age_identity: str
) -> None:
    """Ruling T6-a of the 2026-10-04 stage 1c plan: nothing foreign leaves
    `core`. The hashing pass reads the source, the sealing pass fails on it,
    and what arrives is `SourceUnreadable` with the reason, not the
    `OSError` and not `age`'s wrapping of it; nothing is uploaded."""
    with pytest.raises(SourceUnreadable) as caught:
        store_blob(
            blob_store,
            _FailsOnTheSecondPass(b"read once, then no more"),
            recipient=recipient_of(age_identity),
        )
    assert caught.value.reason == "Input/output error"
    assert _objects(blob_store) == []


class _FullSink:
    """A sink that fails the way a full disk does, at its first write: an
    `OSError` with `ENOSPC`. A small sink of the test's own."""

    def write(self, data: bytes, /) -> int:
        raise OSError(errno.ENOSPC, "No space left on device")


class _TakesSeven:
    """A sink that takes at most seven bytes a call and says so in the count
    it returns, the way an unbuffered file may."""

    def __init__(self) -> None:
        self.data = bytearray()

    def write(self, data: bytes, /) -> int:
        self.data.extend(data[:7])
        return len(data[:7])


@pytest.mark.parametrize("size", [12, 70_000], ids=["12-bytes", "70000-bytes"])
def test_a_fetch_into_a_sink_that_takes_little_at_a_time_is_whole_and_counted_once(
    blob_store: S3BlobStore, age_identity: str, tmp_path: Path, size: int
) -> None:
    """Fix round 2 of task 6, the 2026-10-04 stage 1c plan: the short write
    is finished by `unseal`'s watched sink, outside `HashingSink`, so every
    byte passes `HashingSink` as often as the sink takes it — once. Before,
    `HashingSink` hashed and counted what it was given, not what the sink
    took, and the rest came round again: a re-review probe on 2026-10-05
    counted 39,806,307 bytes for 70,000 and the digest did not match."""
    content = os.urandom(size)
    stored = store_blob(blob_store, io.BytesIO(content), recipient=recipient_of(age_identity))
    sink = _TakesSeven()
    assert fetch_blob(blob_store, _keys(tmp_path, age_identity), stored.address, sink) == size
    assert bytes(sink.data) == content


@pytest.mark.parametrize("size", [12, 70_000], ids=["12-bytes", "70000-bytes"])
def test_a_fetch_into_a_sink_that_fails_returns_no_size(
    blob_store: S3BlobStore, age_identity: str, tmp_path: Path, size: int
) -> None:
    """Ruling T6-c of the 2026-10-04 stage 1c plan: a write that failed
    without a word would leave a size returned for bytes nobody has, and
    before fix round 2 of task 6, when `fetch_blob` hashed what passed before
    the sink wrote it, a digest that held as well. Since then the hashing
    sink writes first and hashes only what the sink took. The sink's failure
    is raised, and no size is returned."""
    content = b"x" * size
    stored = store_blob(blob_store, io.BytesIO(content), recipient=recipient_of(age_identity))
    with pytest.raises(SinkUnwritable) as caught:
        fetch_blob(blob_store, _keys(tmp_path, age_identity), stored.address, _FullSink())
    assert caught.value.reason == "No space left on device"


def test_a_temporary_file_that_cannot_be_made_is_an_error_of_its_own(
    blob_store: S3BlobStore,
    age_identity: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The sealed form goes into a temporary file, and a directory for
    temporary files that does not allow writing makes that fail with a real
    `PermissionError`. What leaves `core` is a `BlobError` with one
    sentence; nothing is uploaded."""
    if os.geteuid() == 0:
        pytest.skip("root writes into a directory without write permission")
    closed = tmp_path / "closed"
    closed.mkdir()
    closed.chmod(0o500)
    monkeypatch.setattr(tempfile, "tempdir", str(closed))
    try:
        with pytest.raises(BlobError) as caught:
            store_blob(
                blob_store, io.BytesIO(b"to be sealed"), recipient=recipient_of(age_identity)
            )
    finally:
        closed.chmod(0o700)
    assert str(caught.value) == "cannot write a temporary file: Permission denied"
    assert _objects(blob_store) == []


def test_a_missing_object_is_none(
    blob_store: S3BlobStore, age_identity: str, tmp_path: Path
) -> None:
    sink = io.BytesIO()
    address = hashlib.sha256(b"never stored").hexdigest()
    assert fetch_blob(blob_store, _keys(tmp_path, age_identity), address, sink) is None
    assert sink.getvalue() == b""


def test_an_empty_file_goes_through_the_whole_path(
    blob_store: S3BlobStore, age_identity: str, tmp_path: Path
) -> None:
    """Review focus 2 of the 2026-10-04 stage 1c plan: the empty content has
    an address like any other, and its sealed form is not empty."""
    stored = store_blob(blob_store, io.BytesIO(b""), recipient=recipient_of(age_identity))
    assert stored.address == hashlib.sha256(b"").hexdigest()
    assert stored.size == 0
    found = blob_store.stat(stored.address)
    assert found is not None
    assert found.sealed_size > 0
    fetched = io.BytesIO()
    assert fetch_blob(blob_store, _keys(tmp_path, age_identity), stored.address, fetched) == 0
    assert fetched.getvalue() == b""


def test_a_recipient_in_upper_case_is_written_beside_the_object_in_lower_case(
    blob_store: S3BlobStore, age_identity: str, tmp_path: Path
) -> None:
    """Bech32 reads either case, and `age` accepts an upper-case recipient;
    `DirectoryKeys` reads a file by the lower-case name only. A `key-id`
    written as given would make the object one that cannot be opened."""
    recipient = recipient_of(age_identity)
    stored = store_blob(blob_store, io.BytesIO(CONSPICUOUS), recipient=recipient.upper())
    found = blob_store.stat(stored.address)
    assert found is not None
    assert found.key_id == recipient
    fetched = io.BytesIO()
    fetch_blob(blob_store, _keys(tmp_path, age_identity), stored.address, fetched)
    assert fetched.getvalue() == CONSPICUOUS


@pytest.mark.skipif(sys.platform != "linux", reason="counts connections in /proc")
def test_a_fetch_that_fails_gives_its_connection_back(
    blob_store: S3BlobStore,
    age_identity: str,
    other_age_identity: str,
    tmp_path: Path,
    s3_connections: ConnectionCount,
) -> None:
    """Every way a fetch can fail after the object was found — it names no
    key, there is no identity for its key, `age` refuses it, it opens to
    another content — closes the stream, so a store that lives long and
    fetches blob after blob does not gather a connection per failure.

    A stream that nobody refers to any more is freed and lets its connection
    go even unclosed, so the test does what a caller that reports failures
    does: it keeps each error, and with the error its traceback, which holds
    the frame of `fetch_blob` and the stream in it. The objects are 4 MiB,
    so that a stream left unread still holds its connection; the garbage
    collector is off, because a collection could free what the errors keep.
    Three fetches per way of failing, and the count after them may not
    exceed the count before. Measured on 2026-10-05: 1 before and 1 after;
    with `stream.close()` moved out of the `finally` to the line after
    `unseal`, 10 after, twice over. That mutation closes whenever `unseal`
    returns, so on the address mismatch too, and leaves open the nine
    fetches of the three other ways; that the ten are those nine and one the
    pool keeps is reckoned from that, not counted.
    Without the kept errors that mutation stayed green, 1 and 1.
    """
    import gc

    recipient = recipient_of(age_identity)
    content = os.urandom(4 * 1024 * 1024)
    sealed = io.BytesIO()
    seal(io.BytesIO(content), sealed, recipient)
    ciphertext = sealed.getvalue()
    address = hashlib.sha256(content).hexdigest()
    no_key = hashlib.sha256(content + b"no key").hexdigest()
    foreign = hashlib.sha256(content + b"foreign").hexdigest()
    garbage = hashlib.sha256(content + b"garbage").hexdigest()
    blob_store.put(address, io.BytesIO(ciphertext), key_id=recipient)
    blob_store.put(foreign, io.BytesIO(ciphertext), key_id=recipient)
    blob_store.put(garbage, io.BytesIO(os.urandom(4 * 1024 * 1024)), key_id=recipient)
    blob_store.client.put_object(Bucket=blob_store.bucket, Key=no_key, Body=ciphertext)
    keys = _keys(tmp_path, age_identity)
    other_directory = tmp_path / "other"
    other_directory.mkdir()
    (other_directory / recipient_of(other_age_identity)).write_text(
        other_age_identity + "\n", encoding="utf-8"
    )
    other_keys = DirectoryKeys(str(other_directory))
    failures = (
        (no_key, keys, CannotOpen),
        (address, other_keys, CannotOpen),
        (garbage, keys, CannotOpen),
        (foreign, keys, AddressMismatch),
    )

    gc.collect()
    before = s3_connections()
    kept: list[pytest.ExceptionInfo[Exception]] = []
    gc.disable()
    try:
        for failing, provider, error in failures:
            for _ in range(3):
                with pytest.raises(error) as caught:
                    fetch_blob(blob_store, provider, failing, io.BytesIO())
                kept.append(caught)
        after = s3_connections()
    finally:
        gc.enable()
    assert len(kept) == 12
    assert after <= before, f"{after} connections after the failed fetches, {before} before"
