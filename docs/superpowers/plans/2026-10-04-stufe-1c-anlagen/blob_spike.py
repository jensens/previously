"""A draft of the blob path, in one file: the protocols, sealing, storing and
fetching, and the S3 adapter. An attachment to the stage 1c plan, not a module.

It exists because the plan prescribes these signatures, and a signature that
was only reasoned about is a claim. This one was measured on 2026-10-04:

- typed: copied to `src/previously/_spike_blobs.py`, `pyright` in strict mode
  reported 0 errors and 0 warnings with `pyrage-stubs` and
  `types-boto3-lite[s3]`. With `types-boto3[s3]` instead, `boto3.client` is
  "partially unknown"; with `from pyrage import x25519`, pyright warns that the
  submodule has no source.
- run: `blob_spike_run.py`, beside this file, against a RustFS container.

Task 5 of the plan cuts it into `contract/blobs.py`, `core/sealing.py`,
`core/blob.py` and `storage/s3.py`, and gives it what it lacks: the error
classes of the two layers, comments that argue, and the client configuration
that bounds how long an unreachable store takes to fail.
"""

from botocore.config import Config
from botocore.exceptions import BotoCoreError
from botocore.exceptions import ClientError
from dataclasses import dataclass
from typing import cast
from typing import IO
from typing import Protocol
from typing import TYPE_CHECKING

import boto3
import hashlib
import pyrage
import tempfile


if TYPE_CHECKING:
    from io import BufferedIOBase
    from types_boto3_s3 import S3Client


class ByteSource(Protocol):
    def read(self, size: int = -1, /) -> bytes: ...


class SeekableSource(ByteSource, Protocol):
    def seek(self, offset: int, whence: int = 0, /) -> int: ...


class ByteSink(Protocol):
    def write(self, data: bytes, /) -> int: ...


@dataclass(frozen=True)
class StoredBlob:
    key_id: str | None
    sealed_size: int


class BlobStore(Protocol):
    def stat(self, address: str) -> StoredBlob | None: ...
    def put(self, address: str, sealed: IO[bytes], *, key_id: str) -> None: ...
    def get(self, address: str) -> tuple[StoredBlob, ByteSource] | None: ...
    def delete(self, address: str) -> None: ...


class KeyProvider(Protocol):
    def identity(self, key_id: str) -> str | None: ...


class BlobError(Exception):
    pass


class InvalidKey(BlobError):
    pass


class CannotOpen(BlobError):
    pass


class AddressMismatch(BlobError):
    pass


class BlobStoreError(Exception):
    pass


# --- sealing -----------------------------------------------------------------


def recipient_of(identity: str) -> str:
    try:
        return str(pyrage.x25519.Identity.from_str(identity).to_public())
    except pyrage.IdentityError as error:
        raise InvalidKey("the identity is not an age X25519 identity") from error


def seal(source: ByteSource, sink: ByteSink, recipient: str) -> None:
    try:
        to = pyrage.x25519.Recipient.from_str(recipient)
    except pyrage.RecipientError as error:
        raise InvalidKey(f"{recipient!r} is not an age X25519 recipient") from error
    pyrage.encrypt_io(cast("BufferedIOBase", source), cast("BufferedIOBase", sink), [to])


def unseal(source: ByteSource, sink: ByteSink, identity: str) -> None:
    try:
        key = pyrage.x25519.Identity.from_str(identity)
    except pyrage.IdentityError as error:
        raise InvalidKey("the identity is not an age X25519 identity") from error
    try:
        pyrage.decrypt_io(cast("BufferedIOBase", source), cast("BufferedIOBase", sink), [key])
    except pyrage.DecryptError as error:
        raise CannotOpen(str(error)) from error


class HashingSink:
    """Hashes what passes through on its way to `sink`."""

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


class NullSink:
    def write(self, data: bytes, /) -> int:
        return len(data)


# --- core/blob ---------------------------------------------------------------

CHUNK = 1024 * 1024


def address_of(source: SeekableSource) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    source.seek(0)
    while chunk := source.read(CHUNK):
        digest.update(chunk)
        size += len(chunk)
    source.seek(0)
    return digest.hexdigest(), size


def store_blob(store: BlobStore, source: SeekableSource, *, recipient: str) -> tuple[str, int, bool]:
    """Address, plaintext size, and whether this call uploaded."""
    address, size = address_of(source)
    if store.stat(address) is not None:
        return address, size, False
    with tempfile.TemporaryFile() as sealed:
        seal(source, sealed, recipient)
        sealed.seek(0)
        store.put(address, sealed, key_id=recipient)
    return address, size, True


def fetch_blob(store: BlobStore, keys: KeyProvider, address: str, sink: ByteSink) -> int | None:
    """Plaintext size, or None when the store has no such object."""
    found = store.get(address)
    if found is None:
        return None
    stored, body = found
    if stored.key_id is None:
        raise CannotOpen("the object does not say which key it is sealed to")
    identity = keys.identity(stored.key_id)
    if identity is None:
        raise CannotOpen(f"no identity for {stored.key_id}")
    hashing = HashingSink(sink)
    unseal(body, hashing, identity)
    if hashing.hexdigest() != address:
        raise AddressMismatch(address)
    return hashing.size


# --- storage/s3 --------------------------------------------------------------

_KEY_ID = "key-id"


def _code(error: ClientError) -> str:
    return error.response.get("Error", {}).get("Code", "")


class S3BlobStore:
    def __init__(self, client: S3Client, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    def stat(self, address: str) -> StoredBlob | None:
        try:
            head = self._client.head_object(Bucket=self._bucket, Key=address)
        except ClientError as error:
            if _code(error) in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise BlobStoreError(_code(error)) from error
        except BotoCoreError as error:
            raise BlobStoreError(type(error).__name__) from error
        return StoredBlob(key_id=head["Metadata"].get(_KEY_ID), sealed_size=head["ContentLength"])

    def put(self, address: str, sealed: IO[bytes], *, key_id: str) -> None:
        try:
            self._client.upload_fileobj(
                sealed, self._bucket, address, ExtraArgs={"Metadata": {_KEY_ID: key_id}}
            )
        except (ClientError, BotoCoreError) as error:
            raise BlobStoreError(type(error).__name__) from error

    def get(self, address: str) -> tuple[StoredBlob, ByteSource] | None:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=address)
        except ClientError as error:
            if _code(error) in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise BlobStoreError(_code(error)) from error
        except BotoCoreError as error:
            raise BlobStoreError(type(error).__name__) from error
        stored = StoredBlob(
            key_id=response["Metadata"].get(_KEY_ID), sealed_size=response["ContentLength"]
        )
        return stored, response["Body"]

    def delete(self, address: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=address)
        except (ClientError, BotoCoreError) as error:
            raise BlobStoreError(type(error).__name__) from error


def from_settings(
    *, endpoint: str, region: str, bucket: str, access_key: str, secret_key: str
) -> S3BlobStore:
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    return S3BlobStore(client, bucket)
