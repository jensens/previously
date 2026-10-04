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
from previously.core.errors import CannotOpen
from previously.core.sealing import recipient_of
from previously.core.sealing import seal
from previously.core.sealing import unseal
from previously.storage.keys import DirectoryKeys
from previously.storage.s3 import from_settings
from typing import TYPE_CHECKING

import hashlib
import io
import os
import pytest
import resource
import threading


if TYPE_CHECKING:
    from pathlib import Path
    from previously.core.blob import Stored
    from previously.storage.s3 import S3BlobStore


pytestmark = pytest.mark.s3

# Rounds of the two-writer test. Which writer wins is a matter of timing:
# measured on 2026-10-05 over 98 rounds, writer 0 won 53 and writer 1 won 45,
# and both writers uploaded in every one of the 48 rounds that counted it.
# At that split, sixteen rounds all going one way is a chance of about one in
# ten thousand.
ROUNDS = 16
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

    Both writers fetch in every round, so every round has a loser that
    fetches; the test still runs `ROUNDS` rounds, each with a content of its
    own, and requires that each writer won at least once, so that the
    fetch of either one is known to work after it lost.
    """
    keys = _keys(tmp_path, age_identity, other_age_identity)
    recipients = [recipient_of(age_identity), recipient_of(other_age_identity)]
    winners: list[str] = []
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
        winners.append(str(recipients.index(found.key_id)))
    assert len(_objects(blob_store)) == ROUNDS
    assert set(winners) == {"0", "1"}, f"one writer won every round: {winners}"


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
