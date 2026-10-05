# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The blob store on S3 ({ref}`blobs`).

This is the one module that imports `boto3` and `botocore`, and
`.importlinter` holds it to that: storing sits where the foreign systems are,
the way SQL sits in `storage.postgres`. What leaves this module is the
protocol of `contract.blobs` and the errors of `storage.errors` — no
`botocore` exception, not even out of a stream that is read later, in `core`.

The store gets and gives ciphertext only. The key an object is sealed to is
written beside it as the metadata `key-id`, in the same request as the
ciphertext, so that the two are replaced together or not at all.
"""

from boto3.session import Session
from botocore.config import Config
from botocore.exceptions import BotoCoreError
from botocore.exceptions import ClientError
from botocore.exceptions import ConnectionError as BotoConnectionError
from botocore.exceptions import HTTPClientError
from botocore.exceptions import IncompleteReadError
from previously.contract.blobs import StoredBlob
from previously.storage.errors import BlobStoreRefused
from previously.storage.errors import BlobStoreUnreachable
from typing import TYPE_CHECKING

import re


if TYPE_CHECKING:
    from botocore.response import StreamingBody
    from previously.contract.blobs import ClosableSource
    from types_boto3_s3 import S3Client
    from typing import IO


# The name of the metadata that carries the recipient. S3 sends it as the
# header `x-amz-meta-key-id` and gives it back under this name.
_KEY_ID = "key-id"
# What a missing object answers: `GetObject` says `NoSuchKey`; `HeadObject`
# has no body to carry a code in, so `botocore` gives the status, `404`.
# `NotFound` is what other servers put there.
_ABSENT = frozenset({"404", "NoSuchKey", "NotFound"})


# An address is the SHA-256 of a plaintext in hex, and nothing else becomes an
# object key: a key with `/` or `..` in it would depend on how the server
# normalizes a path, and the address reaches `delete` too.
_ADDRESS = re.compile(r"[0-9a-f]{64}")
# The errors `botocore` raises about a connection: it groups them itself, under
# `ConnectionError` (no connection, a connect timeout, TLS, a proxy) and
# `HTTPClientError` (a connection that closed, a read timeout, a stream that
# broke off). `IncompleteReadError`, a body shorter than its length, stands
# directly under `BotoCoreError` and is named on its own.
_CONNECTION = (BotoConnectionError, HTTPClientError, IncompleteReadError)


def _code(error: ClientError) -> str:
    return error.response.get("Error", {}).get("Code", "")


def _checked(address: str) -> str:
    """`address`, if it is one. A caller error otherwise, raised before
    anything is sent."""
    if _ADDRESS.fullmatch(address) is None:
        raise ValueError(f"{address} is not a blob address: 64 hexadecimal characters, lower case")
    return address


class _Stream:
    """The body of a `get`, with `read` translated and `close` passed on.

    A read can break off: measured on 2026-10-05 against RustFS 1.0.1, an
    object of 64 MiB deleted while it was being read did so in five rounds
    out of five, and a second upload replacing it does the same. `botocore`
    raises `ResponseStreamingError` then, and `pyrage` lets an exception out
    of `read` pass unchanged — so without this wrapper a `botocore` type
    would arrive in `core`, which is not to know it.

    `close` gives the connection back at once. A body that is not read to its
    end holds its connection for as long as anything refers to it, and a
    reader that stops early — no key, no identity, a file `age` refuses —
    leaves exactly such a body behind.
    """

    def __init__(self, body: StreamingBody, store: S3BlobStore, address: str) -> None:
        self._body = body
        self._store = store
        self._address = address

    def read(self, size: int = -1, /) -> bytes:
        try:
            return self._body.read(None if size < 0 else size)
        except BotoCoreError as error:
            raise BlobStoreUnreachable(
                f"the blob store at {self._store.endpoint} broke off while sending "
                f"{self._address} from bucket {self._store.bucket!r}: {type(error).__name__}"
            ) from error

    def close(self) -> None:
        self._body.close()


class S3BlobStore:
    """`contract.blobs.BlobStore` on one bucket of an S3 server.

    The bucket runs without versioning and without object lock: a delete has
    to delete, or an erasure would leave the ciphertext behind as a version.
    """

    def __init__(self, client: S3Client, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    @property
    def client(self) -> S3Client:
        """The `boto3` client, for setting up and inspecting a bucket —
        what tests and operations need beyond the protocol."""
        return self._client

    @property
    def bucket(self) -> str:
        return self._bucket

    @property
    def endpoint(self) -> str:
        return self._client.meta.endpoint_url

    def __repr__(self) -> str:
        # Endpoint and bucket, never the credentials the client holds.
        return f"S3BlobStore(endpoint={self.endpoint!r}, bucket={self._bucket!r})"

    def _refused(self, error: ClientError) -> BlobStoreRefused:
        return BlobStoreRefused(
            f"the blob store at {self.endpoint} refused a request on bucket "
            f"{self._bucket!r}: {_code(error) or 'no code'}"
        )

    def _translated(self, error: BotoCoreError) -> BlobStoreUnreachable | BlobStoreRefused:
        """A `BotoCoreError` by kind: about the connection, or about the
        settings and the request.

        What `botocore` does not file under a connection falls on the side of
        the settings. Those errors are raised by the client's own checks,
        before a request goes out or apart from the network —
        `ParamValidationError` for a bucket name the client will not send
        (measured on 2026-10-05 with an empty one), `NoCredentialsError` and
        their like — and a message that called them "not reachable" would
        send an operator to the network for a typo in the environment. The
        message names the class, which carries no setting's value.
        """
        if isinstance(error, _CONNECTION):
            return BlobStoreUnreachable(
                f"the blob store at {self.endpoint} is not reachable: {type(error).__name__}"
            )
        return BlobStoreRefused(
            f"the settings for the blob store at {self.endpoint}, bucket {self._bucket!r}, "
            f"are not usable: {type(error).__name__}"
        )

    def stat(self, address: str) -> StoredBlob | None:
        """What the store says about the object, or `None` when there is none.

        A bucket that does not exist is `None` here, too: a HEAD request has
        no body, and the answer for a missing bucket is the same `404` without
        a code as for a missing object (measured on 2026-10-04 and again on
        2026-10-05). The missing bucket shows at the first `get` or `put`.
        """
        try:
            head = self._client.head_object(Bucket=self._bucket, Key=_checked(address))
        except ClientError as error:
            if _code(error) in _ABSENT:
                return None
            raise self._refused(error) from error
        except BotoCoreError as error:
            raise self._translated(error) from error
        return StoredBlob(key_id=head["Metadata"].get(_KEY_ID), sealed_size=head["ContentLength"])

    def put(self, address: str, sealed: IO[bytes], *, key_id: str) -> None:
        """Uploads the ciphertext under `address`, with `key_id` beside it,
        in parts when it is large, so that memory stays bounded."""
        try:
            self._client.upload_fileobj(
                sealed, self._bucket, _checked(address), ExtraArgs={"Metadata": {_KEY_ID: key_id}}
            )
        except ClientError as error:
            raise self._refused(error) from error
        except BotoCoreError as error:
            raise self._translated(error) from error

    def get(self, address: str) -> tuple[StoredBlob, ClosableSource] | None:
        """The metadata and the stream of the object, out of one answer, or
        `None` when there is none. Whoever takes the stream closes it.

        One request and not a `stat` beside it: two requests could see,
        while the object is being replaced, the key of one upload and the
        body of the other.
        """
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=_checked(address))
        except ClientError as error:
            if _code(error) in _ABSENT:
                return None
            raise self._refused(error) from error
        except BotoCoreError as error:
            raise self._translated(error) from error
        stored = StoredBlob(
            key_id=response["Metadata"].get(_KEY_ID), sealed_size=response["ContentLength"]
        )
        return stored, _Stream(response["Body"], self, address)

    def delete(self, address: str) -> None:
        """Deletes the object. An object that is not there is no error: S3
        answers a delete of a missing key with success."""
        try:
            self._client.delete_object(Bucket=self._bucket, Key=_checked(address))
        except ClientError as error:
            raise self._refused(error) from error
        except BotoCoreError as error:
            raise self._translated(error) from error

    def close(self) -> None:
        """Closes every connection the client's pool holds, a stream that was
        not read to its end included.

        Without it they stay open until the garbage collector finds the
        client: an upload in parts leaves it in reference cycles. Measured on
        2026-10-05 with the collector off, twenty uses of a store each built
        by `from_settings` left fifty connections established; with `close`
        after each, none. Whoever builds a store closes it when done, the way
        `storage.postgres.PostgresStorage.close` is called. The client stays
        usable and opens a new connection at the next request.
        """
        self._client.close()


# How long a call against a store that does not answer takes to fail, in
# both ways a store can fail to answer. Measured on 2026-10-05.
#
# Nobody there, or packets dropped: the connect timeout. With boto3's
# defaults — 60 s and the legacy retry mode with five attempts — one call
# against `http://127.0.0.1:1`, where nothing listens, took between 1.95 and
# 11.95 s over ten calls, and one against an address that drops the packets
# (`10.255.255.1`) had not failed after 200 s. With the values below, the
# calls against `127.0.0.1:1` failed in at most 0.89 s over twenty (the
# backoff before the second attempt is random, up to a second), and the two
# against the address that drops the packets in 10.0 and 10.5 s: two
# attempts of five seconds each.
#
# A server that accepts the connection and then never answers: the read
# timeout, which bounds each wait for the next bytes of an answer, not the
# whole transfer, so a large object that keeps flowing is not cut off.
# boto3's default is 60 s per attempt, which over the two attempts below would
# come to two minutes; this was not run. With the value below,
# a `stat` and a `get` against a socket that accepted and stayed silent
# failed after 40.26 and 40.43 s: two attempts of twenty seconds each, with
# `ReadTimeoutError`, which counts as unreachable.
_CONNECT_TIMEOUT = 5
_READ_TIMEOUT = 20
_ATTEMPTS = 2


def from_settings(
    *, endpoint: str, region: str, bucket: str, access_key: str, secret_key: str
) -> S3BlobStore:
    """A store on `bucket` at `endpoint`. Connects nowhere yet, like
    `storage.postgres.from_dsn`: the first request does.

    Path-style addressing (`<endpoint>/<bucket>/<key>`), because a server
    that is not AWS rarely has a name for every bucket.

    A session of its own per store: `boto3`'s default session is shared by
    the whole process, and `boto3` documents sessions as not safe to share
    between threads.
    """
    client: S3Client = Session().client(
        "s3",
        endpoint_url=endpoint,
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            connect_timeout=_CONNECT_TIMEOUT,
            read_timeout=_READ_TIMEOUT,
            retries={"mode": "standard", "total_max_attempts": _ATTEMPTS},
        ),
    )
    return S3BlobStore(client, bucket)
