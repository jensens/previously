# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The S3 adapter against a real S3 server, RustFS in a container
({ref}`blobs`).

Every test gets a bucket of its own from `blob_store`, so no test sees
another's objects. The store gets and gives ciphertext only, but this adapter
does not look at what it stores: the bytes here are made up, not sealed.
"""

from previously.contract.blobs import StoredBlob
from previously.storage.errors import BlobStoreRefused
from previously.storage.errors import BlobStoreUnreachable
from previously.storage.errors import StorageError
from previously.storage.s3 import from_settings
from typing import TYPE_CHECKING

import io
import os
import pytest
import secrets
import sys
import time
import traceback


if TYPE_CHECKING:
    from collections.abc import Callable
    from previously.contract.blobs import BlobStore
    from previously.storage.s3 import S3BlobStore


pytestmark = pytest.mark.s3

# What the `s3_connections` fixture is, spelled here as `conftest.py` asks
# of a test that takes one of its callables.
type ConnectionCount = Callable[[], int]

ADDRESS = "ab" * 32
KEY_ID = "age1" + "q" * 58


def test_stat_and_get_of_a_missing_object_are_none(blob_store: S3BlobStore) -> None:
    assert blob_store.stat(ADDRESS) is None
    assert blob_store.get(ADDRESS) is None


def test_put_stat_get_round_trip_with_the_key_id(blob_store: S3BlobStore) -> None:
    data = os.urandom(70_000)
    blob_store.put(ADDRESS, io.BytesIO(data), key_id=KEY_ID)

    assert blob_store.stat(ADDRESS) == StoredBlob(key_id=KEY_ID, sealed_size=len(data))
    found = blob_store.get(ADDRESS)
    assert found is not None
    stored, stream = found
    assert stored == StoredBlob(key_id=KEY_ID, sealed_size=len(data))
    assert stream.read() == data


def test_get_gives_metadata_and_body_from_one_answer(blob_store: S3BlobStore) -> None:
    """One request, so that the key and the body come from the same version
    of the object: two requests could see, while it is being replaced, the
    key of one upload and the body of the other. Counted at the events the
    client emits before every call, not at a stand-in for the client."""
    blob_store.put(ADDRESS, io.BytesIO(b"sealed"), key_id=KEY_ID)
    calls: list[str] = []

    def count(model: object, **_: object) -> None:
        calls.append(str(getattr(model, "name", model)))

    blob_store.client.meta.events.register("before-call.s3", count)
    found = blob_store.get(ADDRESS)
    assert found is not None
    assert found[1].read() == b"sealed"
    assert calls == ["GetObject"]


def test_delete_twice_is_no_error(blob_store: S3BlobStore) -> None:
    blob_store.put(ADDRESS, io.BytesIO(b"sealed"), key_id=KEY_ID)
    blob_store.delete(ADDRESS)
    blob_store.delete(ADDRESS)
    assert blob_store.stat(ADDRESS) is None


def test_a_fresh_bucket_keeps_no_version_after_a_delete(blob_store: S3BlobStore) -> None:
    """Deleting deletes: a bucket with versioning would keep the ciphertext
    as a version, or a delete marker in front of it, and an erasure would
    erase nothing."""
    blob_store.put(ADDRESS, io.BytesIO(b"sealed"), key_id=KEY_ID)
    blob_store.delete(ADDRESS)
    versions = blob_store.client.list_object_versions(Bucket=blob_store.bucket)
    assert versions.get("Versions", []) == []
    assert versions.get("DeleteMarkers", []) == []


def test_a_missing_bucket_is_refused_and_named(
    blob_store: S3BlobStore, s3_settings: dict[str, str]
) -> None:
    """`get` names the bucket. `stat` cannot: a HEAD on a bucket that does not
    exist answers 404 without a code, the same answer as for a missing
    object, so the missing bucket shows at the first `get` or `put`."""
    elsewhere = from_settings(**s3_settings, bucket="no-such-bucket")
    assert elsewhere.stat(ADDRESS) is None
    with pytest.raises(BlobStoreRefused) as caught:
        elsewhere.get(ADDRESS)
    message = str(caught.value)
    assert s3_settings["endpoint"] in message
    assert "no-such-bucket" in message
    assert "NoSuchBucket" in message
    with pytest.raises(BlobStoreRefused, match="no-such-bucket"):
        elsewhere.put(ADDRESS, io.BytesIO(b"sealed"), key_id=KEY_ID)


def test_a_wrong_secret_is_refused_and_not_shown(
    blob_store: S3BlobStore, s3_settings: dict[str, str]
) -> None:
    """Neither the message, nor the `repr`, nor anything in the chain of
    causes as a traceback prints it, carries the secret — the wrong one here,
    which stands for a right one with a typo in it. Drawn at run time, so
    that it cannot turn up in any text by chance."""
    secret = secrets.token_hex(16)
    wrong = from_settings(**{**s3_settings, "secret_key": secret}, bucket=blob_store.bucket)
    calls = (
        lambda: wrong.stat(ADDRESS),
        lambda: wrong.get(ADDRESS),
        lambda: wrong.put(ADDRESS, io.BytesIO(b"sealed"), key_id=KEY_ID),
        lambda: wrong.delete(ADDRESS),
    )
    for call in calls:
        with pytest.raises(BlobStoreRefused) as caught:
            call()
        error = caught.value
        printed = "".join(traceback.format_exception(error))
        assert secret not in str(error)
        assert secret not in repr(error)
        assert secret not in printed
        assert s3_settings["endpoint"] in str(error)
    assert secret not in repr(wrong)


def test_an_endpoint_nobody_listens_on_is_unreachable_within_seconds(
    s3_settings: dict[str, str],
) -> None:
    """Two attempts per call, and a bound on the time.

    Measured on 2026-10-05 against `http://127.0.0.1:1`: with the
    configuration in `storage/s3.py` one call failed in at most 0.89 s over
    twenty, and the bound of 3 s stands above that. The time alone cannot
    tell that configuration from boto3's default, though: the backoff
    between attempts is random, and over ten calls the default took between
    1.95 and 11.95 s — with the configuration removed, this test once went
    red on the time at 3.9 s, and it could as well have stayed green. The
    number of attempts tells them apart every time: two here, five by
    default. They are counted at the event the client emits before it sends
    each one."""
    nobody = from_settings(**{**s3_settings, "endpoint": "http://127.0.0.1:1"}, bucket="blobs")
    attempts: list[str] = []

    def count(**_: object) -> None:
        attempts.append("sent")

    nobody.client.meta.events.register("before-send.s3", count)
    calls = (
        lambda: nobody.stat(ADDRESS),
        lambda: nobody.get(ADDRESS),
        lambda: nobody.put(ADDRESS, io.BytesIO(b"sealed"), key_id=KEY_ID),
        lambda: nobody.delete(ADDRESS),
    )
    for call in calls:
        attempts.clear()
        started = time.monotonic()
        with pytest.raises(BlobStoreUnreachable) as caught:
            call()
        assert len(attempts) == 2
        assert time.monotonic() - started < 3
        assert "http://127.0.0.1:1" in str(caught.value)
        assert "not reachable: EndpointConnectionError" in str(caught.value)


def test_a_read_that_breaks_off_is_a_storage_error(blob_store: S3BlobStore) -> None:
    """The stream `get` hands out translates what `botocore` raises while
    reading, so no foreign exception passes through `pyrage` into `core`.

    The break is a real one. Measured on 2026-10-05 against RustFS 1.0.1: an
    object of 64 MiB deleted after the first 8 KiB were read broke the read
    off with `ResponseStreamingError` in five rounds out of five, and so did
    a second upload replacing it, while at 4 and at 16 MiB the rest arrived
    out of the buffers in all ten rounds of each size. This test passed in
    ten runs out of ten the same day.
    """
    blob_store.put(ADDRESS, io.BytesIO(os.urandom(64 * 1024 * 1024)), key_id=KEY_ID)
    found = blob_store.get(ADDRESS)
    assert found is not None
    _, stream = found
    assert len(stream.read(8192)) == 8192
    blob_store.delete(ADDRESS)
    with pytest.raises(BlobStoreUnreachable) as caught:
        while stream.read(1024 * 1024):
            pass
    assert isinstance(caught.value, StorageError)
    assert ADDRESS in str(caught.value)


def test_s3_blob_store_satisfies_the_protocol(blob_store: S3BlobStore) -> None:
    """Static, like the proofs for `PostgresStorage` in
    `tests/test_projection_store.py`: pyright rejects the assignment if a
    method is missing or has the wrong form."""
    store: BlobStore = blob_store
    assert store is blob_store


@pytest.mark.skipif(sys.platform != "linux", reason="counts connections in /proc")
def test_close_releases_the_connections_the_store_opened(
    blob_store: S3BlobStore, s3_settings: dict[str, str], s3_connections: ConnectionCount
) -> None:
    """A store built per command and closed when the command is done leaves
    no connection behind, so a process that runs many commands holds no more
    at the end than at the start — ruling T5-a of the 2026-10-04 stage 1c
    plan, which asked for this method only if a measurement said so.

    It did. Measured on 2026-10-05 with the garbage collector off, as here: a
    store that uploads in parts keeps the client in reference cycles, and
    without `close` twenty uses left fifty connections established, two or
    three per use. With `close`, none. The collector is off because a
    collection would hide a missing release; the control is the count while
    the store is open, which has to see the connections it then releases.
    """
    import gc

    # Above the 8 MiB from which `upload_fileobj` uploads in parts.
    data = os.urandom(10 * 1024 * 1024)
    gc.collect()
    before = s3_connections()
    gc.disable()
    try:
        for _ in range(3):
            store = from_settings(**s3_settings, bucket=blob_store.bucket)
            store.stat(ADDRESS)
            store.put(ADDRESS, io.BytesIO(data), key_id=KEY_ID)
            found = store.get(ADDRESS)
            assert found is not None
            found[1].read(8192)  # abandoned, as when `age` refuses the header
            assert s3_connections() > before
            store.close()
            del store, found
        after = s3_connections()
    finally:
        gc.enable()
    assert after <= before


def test_a_refused_upload_in_parts_leaves_no_connection_behind_after_close(
    blob_store: S3BlobStore, s3_settings: dict[str, str], s3_connections: ConnectionCount
) -> None:
    """Ruling T6-a of the 2026-10-04 stage 1c plan: a store closed after an
    upload in parts that the store refused holds no connection, on the error
    path as on the success path.

    Measured on 2026-10-05 before the fix, with the collector off as here:
    four refused uploads of 9 MiB into a bucket that does not exist, each
    store closed, left 4 connections established, still 4 two seconds
    later, and 0 after `gc.collect()`. What held each one, walked by
    `gc.get_referrers`: the socket <- the `urllib3` response <- botocore's
    `AWSResponse` <- the frame of `_make_api_call` that raised `NoSuchBucket`
    <- the traceback of that exception <- the exception, kept by the
    transfer's `s3transfer.futures.TransferCoordinator`, which sits in
    reference cycles. `close` empties the pool, and a connection a response
    still holds is not in it. The message keeps endpoint, bucket and code.

    This test, measured the same day: 1 before and 1 after with the fix;
    with the traceback kept, 4 after.
    """
    import gc

    data = os.urandom(9 * 1024 * 1024)  # above the 8 MiB of an upload in parts
    gc.collect()
    before = s3_connections()
    gc.disable()
    try:
        for _ in range(3):
            refused = from_settings(**s3_settings, bucket="previously-no-such-bucket")
            with pytest.raises(BlobStoreRefused) as caught:
                refused.put(ADDRESS, io.BytesIO(data), key_id=KEY_ID)
            refused.close()
            message = str(caught.value)
            del refused, caught
            assert s3_settings["endpoint"] in message
            assert "'previously-no-such-bucket'" in message
            assert message.endswith(": NoSuchBucket")
        after = s3_connections()
    finally:
        gc.enable()
    assert after <= before, f"{after} connections after the refused uploads, {before} before"


def test_settings_the_client_will_not_send_are_refused_not_unreachable(
    s3_settings: dict[str, str],
) -> None:
    """An error `botocore` raises from its own checks, before anything goes
    out, is about the settings and not about the network: an empty bucket
    name fails parameter validation (measured on 2026-10-05), and the message
    says the settings are not usable instead of sending an operator to look
    for a server that is down. The other side, an endpoint where nobody
    listens, is `test_an_endpoint_nobody_listens_on_is_unreachable_within_seconds`.
    """
    unusable = from_settings(**s3_settings, bucket="")
    with pytest.raises(BlobStoreRefused) as caught:
        unusable.stat(ADDRESS)
    message = str(caught.value)
    assert "are not usable: ParamValidationError" in message
    assert s3_settings["endpoint"] in message
    assert s3_settings["secret_key"] not in message
    assert s3_settings["access_key"] not in message


@pytest.mark.parametrize(
    "address",
    ["", "AB" * 32, "ab" * 31, "../" + "ab" * 31, "ab" * 32 + "\n"],
    ids=["empty", "upper-case", "short", "parent", "newline"],
)
def test_an_address_that_is_not_one_is_a_caller_error_and_nothing_is_sent(
    blob_store: S3BlobStore, address: str
) -> None:
    """Only 64 lower-case hexadecimal characters become an object key, in
    each of the four methods — `delete` included, which an erasure calls.
    Nothing reaches the server: the requests are counted at the event the
    client emits before it sends one."""
    sent: list[str] = []

    def count(**_: object) -> None:
        sent.append("sent")

    blob_store.client.meta.events.register("before-send.s3", count)
    calls = (
        lambda: blob_store.stat(address),
        lambda: blob_store.get(address),
        lambda: blob_store.put(address, io.BytesIO(b"sealed"), key_id=KEY_ID),
        lambda: blob_store.delete(address),
    )
    for call in calls:
        with pytest.raises(ValueError, match="is not a blob address"):
            call()
    assert sent == []
