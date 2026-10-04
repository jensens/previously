"""Scratch: RustFS in a container, boto3 against it, pyrage in between.

    uv run --with boto3 --with pyrage python measure_rustfs.py <size in MiB>

Answers, for the stage 1c specification:
  - does the generic testcontainers container bring RustFS up, and how long does it take
  - is versioning off on a fresh bucket, and does a delete delete
  - does pyrage read from boto3's streaming body and write into a plain Python object
  - what does the round trip cost in memory
"""

import hashlib
import os
import resource
import sys
import tempfile
import time
from pathlib import Path

import boto3
import pyrage
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError
from testcontainers.core.container import DockerContainer

size_mib = int(sys.argv[1]) if len(sys.argv) > 1 else 16
ACCESS, SECRET, BUCKET = "probe-access", "probe-secret-key", "blobs"


class HashingWriter:
    """What `core` would hand to the decryption: hashes while it writes."""

    def __init__(self, target):
        self.target = target
        self.digest = hashlib.sha256()
        self.calls = 0

    def write(self, data):
        self.calls += 1
        self.digest.update(data)
        return self.target.write(data)

    def flush(self):
        self.target.flush()


started = time.perf_counter()
container = (
    DockerContainer("rustfs/rustfs:1.0.1")
    .with_exposed_ports(9000)
    .with_env("RUSTFS_ACCESS_KEY", ACCESS)
    .with_env("RUSTFS_SECRET_KEY", SECRET)
)
with container:
    endpoint = f"http://{container.get_container_host_ip()}:{container.get_exposed_port(9000)}"
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=ACCESS,
        aws_secret_access_key=SECRET,
        region_name="us-east-1",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    for attempt in range(120):
        try:
            client.list_buckets()
            break
        except (BotoCoreError, ClientError) as error:
            last = error
            time.sleep(0.25)
    else:
        print("never came up:", last)
        print(container.get_logs()[0].decode()[-2000:])
        print(container.get_logs()[1].decode()[-2000:])
        raise SystemExit(1)
    print(f"up after {time.perf_counter() - started:5.1f} s (image pull included on the first run)")

    client.create_bucket(Bucket=BUCKET)
    versioning = client.get_bucket_versioning(Bucket=BUCKET)
    print("versioning on a fresh bucket:", versioning.get("Status", "(no status: never enabled)"))

    identity = pyrage.x25519.Identity.generate()
    recipient = identity.to_public()

    with tempfile.TemporaryDirectory() as tmp:
        plain, sealed, opened = (Path(tmp) / name for name in ("plain", "sealed", "opened"))
        block = os.urandom(1024 * 1024)
        address = hashlib.sha256()
        with plain.open("wb") as handle:
            for _ in range(size_mib):
                handle.write(block)
                address.update(block)
        key = address.hexdigest()

        try:
            client.head_object(Bucket=BUCKET, Key=key)
            print("exists before put: yes (unexpected)")
        except ClientError as error:
            print("exists before put: no, error code", error.response["Error"]["Code"])

        t0 = time.perf_counter()
        with plain.open("rb") as source, sealed.open("wb") as target:
            pyrage.encrypt_io(source, target, [recipient])
        t1 = time.perf_counter()
        with sealed.open("rb") as source:
            client.upload_fileobj(source, BUCKET, key)
        t2 = time.perf_counter()
        head = client.head_object(Bucket=BUCKET, Key=key)
        print(
            f"put {size_mib} MiB | seal {t1 - t0:5.2f} s | upload {t2 - t1:5.2f} s"
            f" | stored {head['ContentLength']} bytes (+{head['ContentLength'] - plain.stat().st_size})"
        )
        first = client.get_object(Bucket=BUCKET, Key=key, Range="bytes=0-20")["Body"].read()
        print("stored object begins with:", first)

        body = client.get_object(Bucket=BUCKET, Key=key)["Body"]
        t3 = time.perf_counter()
        try:
            with opened.open("wb") as target:
                writer = HashingWriter(target)
                pyrage.decrypt_io(body, writer, [identity])
            t4 = time.perf_counter()
            print(
                f"get: streaming body -> pyrage -> hashing writer | {t4 - t3:5.2f} s"
                f" | {writer.calls} write calls | address matches: {writer.digest.hexdigest() == key}"
                f" | size matches: {opened.stat().st_size == plain.stat().st_size}"
            )
        except Exception as error:
            print("get: streaming body -> pyrage failed:", type(error).__name__, error)

        other = pyrage.x25519.Identity.generate()
        body = client.get_object(Bucket=BUCKET, Key=key)["Body"]
        try:
            with opened.open("wb") as target:
                pyrage.decrypt_io(body, target, [other])
            print("wrong identity: opened (unexpected)")
        except Exception as error:
            print("wrong identity:", type(error).__name__, "|", str(error)[:80])

        client.delete_object(Bucket=BUCKET, Key=key)
        try:
            client.head_object(Bucket=BUCKET, Key=key)
            print("after delete: still there (unexpected)")
        except ClientError as error:
            print("after delete: gone, error code", error.response["Error"]["Code"])
        versions = client.list_object_versions(Bucket=BUCKET)
        print(
            "versions left:", len(versions.get("Versions", [])),
            "| delete markers:", len(versions.get("DeleteMarkers", [])),
        )
        client.delete_object(Bucket=BUCKET, Key=key)
        print("second delete of the same key: no error")

peak_mib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
print(f"peak RSS {peak_mib:.0f} MiB at {size_mib} MiB")
