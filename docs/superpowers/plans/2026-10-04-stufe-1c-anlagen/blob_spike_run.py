"""Runs `blob_spike.py` against a RustFS container, so that the signatures the
stage 1c plan prescribes are executed and not only typed.

    cd docs/superpowers/plans/2026-10-04-stufe-1c-anlagen
    uv run --with boto3 --with pyrage python blob_spike_run.py

Run on 2026-10-04. What it showed, beyond every path working: a missing
bucket answers a HEAD with a plain 404, so `stat` cannot tell it from a
missing object; and with boto3's default configuration two calls against an
endpoint nobody listens on took 23.3 s to fail in one run and 14.1 s in the
next.
"""

import io
import os
import time

import pyrage
from botocore.exceptions import BotoCoreError, ClientError
import blob_spike as s
from testcontainers.core.container import DockerContainer

ACCESS, SECRET, BUCKET = "probe-access", "probe-secret-key", "blobs"


class Keys:
    def __init__(self, identities):
        self._by_recipient = {s.recipient_of(text): text for text in identities}

    def identity(self, key_id):
        return self._by_recipient.get(key_id)


class OnlyRead:
    """A source with nothing but `read`, to see what pyrage needs."""

    def __init__(self, data):
        self._inner = io.BytesIO(data)

    def read(self, size=-1, /):
        return self._inner.read(size)


container = (
    DockerContainer("rustfs/rustfs:1.0.1")
    .with_exposed_ports(9000)
    .with_env("RUSTFS_ACCESS_KEY", ACCESS)
    .with_env("RUSTFS_SECRET_KEY", SECRET)
)
with container:
    endpoint = f"http://{container.get_container_host_ip()}:{container.get_exposed_port(9000)}"
    store = s.from_settings(
        endpoint=endpoint, region="us-east-1", bucket=BUCKET, access_key=ACCESS, secret_key=SECRET
    )
    raw = store._client
    for _ in range(120):
        try:
            raw.list_buckets()
            break
        except (BotoCoreError, ClientError):
            time.sleep(0.25)
    raw.create_bucket(Bucket=BUCKET)

    old = pyrage.x25519.Identity.generate()
    new = pyrage.x25519.Identity.generate()
    keys = Keys([str(old), str(new)])
    data = os.urandom(3 * 1024 * 1024 + 17)

    print("stat of a missing object:", store.stat("0" * 64))
    print("get of a missing object:", store.get("0" * 64))

    address, size, uploaded = s.store_blob(store, io.BytesIO(data), recipient=str(old.to_public()))
    print("first store: uploaded", uploaded, "| size", size == len(data))
    print("stat:", store.stat(address).key_id == str(old.to_public()), store.stat(address).sealed_size > size)

    # After a key change the second writer does not upload; the object keeps its key.
    again = s.store_blob(store, io.BytesIO(data), recipient=str(new.to_public()))
    print("second store, new recipient: uploaded", again[2], "| object still names the old key:",
          store.stat(address).key_id == str(old.to_public()))

    out = io.BytesIO()
    print("fetch:", s.fetch_blob(store, keys, address, out) == len(data), out.getvalue() == data)
    print("fetch into a sink with nothing but write:", s.fetch_blob(store, keys, address, s.NullSink()))

    try:
        s.fetch_blob(store, Keys([str(new)]), address, s.NullSink())
    except s.CannotOpen as error:
        print("no identity for the object's key:", error)

    # An object under a foreign address.
    with io.BytesIO() as sealed:
        s.seal(io.BytesIO(b"something else"), sealed, str(old.to_public()))
        sealed.seek(0)
        store.put("f" * 64, sealed, key_id=str(old.to_public()))
    try:
        s.fetch_blob(store, keys, "f" * 64, s.NullSink())
    except s.AddressMismatch as error:
        print("foreign address: AddressMismatch", str(error)[:8])

    # Garbage under an address.
    store.put("e" * 64, io.BytesIO(b"not an age file"), key_id=str(old.to_public()))
    try:
        s.fetch_blob(store, keys, "e" * 64, s.NullSink())
    except s.CannotOpen as error:
        print("garbage: CannotOpen |", error)

    # A source with nothing but read.
    sink = io.BytesIO()
    s.seal(OnlyRead(b"abc" * 1000), sink, str(old.to_public()))
    plain = io.BytesIO()
    s.unseal(OnlyRead(sink.getvalue()), plain, str(old))
    print("read-only source both ways:", plain.getvalue() == b"abc" * 1000)

    for bad in ("nonsense", ""):
        try:
            s.seal(io.BytesIO(b"x"), io.BytesIO(), bad)
        except s.InvalidKey as error:
            print("bad recipient:", error)

    store.delete(address)
    store.delete(address)
    print("after two deletes:", store.stat(address))

    # What an unreachable or refusing store looks like.
    for label, other in (
        ("wrong secret", s.from_settings(endpoint=endpoint, region="us-east-1", bucket=BUCKET, access_key=ACCESS, secret_key="wrong")),
        ("missing bucket", s.from_settings(endpoint=endpoint, region="us-east-1", bucket="nope", access_key=ACCESS, secret_key=SECRET)),
        ("nobody there", s.from_settings(endpoint="http://127.0.0.1:1", region="us-east-1", bucket=BUCKET, access_key=ACCESS, secret_key=SECRET)),
    ):
        started = time.perf_counter()
        for call_label, call in (("stat", lambda: other.stat(address)), ("get", lambda: other.get(address))):
            try:
                print(f"{label} | {call_label}:", call())
            except s.BlobStoreError as error:
                cause = error.__cause__
                print(f"{label} | {call_label}: BlobStoreError({error}) from {type(cause).__name__} | {str(cause)[:110]}")
        print(f"   took {time.perf_counter() - started:.1f} s")
