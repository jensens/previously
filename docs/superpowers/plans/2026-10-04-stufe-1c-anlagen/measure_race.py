"""Scratch: two writers store the same content under the same address at once.

    uv run --with boto3 --with pyrage python measure_race.py <size in MiB> <rounds>

The same plaintext, sealed twice to two different recipients, so that the two
ciphertexts can be told apart: whichever identity opens the surviving object
names the writer that won. Each writer tags its upload with its own name as
object metadata. A reader keeps getting and opening the object while both
uploads run.

Answers:
  - is the surviving object ever torn (a mix of both uploads)
  - does the surviving metadata belong to the surviving body
  - what does a reader see while the object is being replaced
  - does the server refuse a second write under `If-None-Match: *`
"""

import hashlib
import io
import os
import sys
import tempfile
import threading
import time
from collections import Counter
from pathlib import Path

import boto3
import pyrage
from boto3.s3.transfer import S3Transfer
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError
from testcontainers.core.container import DockerContainer

size_mib = int(sys.argv[1]) if len(sys.argv) > 1 else 64
rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 10
ACCESS, SECRET, BUCKET = "probe-access", "probe-secret-key", "blobs"


class Hashing:
    def __init__(self):
        self.digest = hashlib.sha256()

    def write(self, data):
        self.digest.update(data)
        return len(data)

    def flush(self):
        pass


def new_client(endpoint):
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=ACCESS,
        aws_secret_access_key=SECRET,
        region_name="us-east-1",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def opens_with(client, key, identities):
    """The plaintext hash the object opens to with these identities, or the error's name."""
    try:
        response = client.get_object(Bucket=BUCKET, Key=key)
        sink = Hashing()
        pyrage.decrypt_io(response["Body"], sink, identities)
        return sink.digest.hexdigest(), response.get("Metadata", {})
    except ClientError as error:
        return "ClientError:" + error.response["Error"]["Code"], {}
    except Exception as error:
        return type(error).__name__, {}


container = (
    DockerContainer("rustfs/rustfs:1.0.1")
    .with_exposed_ports(9000)
    .with_env("RUSTFS_ACCESS_KEY", ACCESS)
    .with_env("RUSTFS_SECRET_KEY", SECRET)
)
with container, tempfile.TemporaryDirectory() as tmp:
    endpoint = f"http://{container.get_container_host_ip()}:{container.get_exposed_port(9000)}"
    client = new_client(endpoint)
    for _ in range(120):
        try:
            client.list_buckets()
            break
        except (BotoCoreError, ClientError):
            time.sleep(0.25)
    client.create_bucket(Bucket=BUCKET)

    plain = Path(tmp) / "plain"
    address = hashlib.sha256()
    block = os.urandom(1024 * 1024)
    with plain.open("wb") as handle:
        for _ in range(size_mib):
            handle.write(block)
            address.update(block)
    key = address.hexdigest()

    identities = {name: pyrage.x25519.Identity.generate() for name in ("a", "b")}
    sealed = {}
    for name, identity in identities.items():
        sealed[name] = Path(tmp) / f"sealed-{name}"
        with plain.open("rb") as source, sealed[name].open("wb") as target:
            pyrage.encrypt_io(source, target, [identity.to_public()])

    winners = Counter()
    reader_saw = Counter()
    torn = 0
    metadata_mismatch = 0

    for round_number in range(rounds):
        client.delete_object(Bucket=BUCKET, Key=key)
        barrier = threading.Barrier(2)
        stop = threading.Event()

        def write(name):
            own = new_client(endpoint)
            barrier.wait()
            with sealed[name].open("rb") as source:
                own.upload_fileobj(source, BUCKET, key, ExtraArgs={"Metadata": {"writer": name}})

        def read():
            own = new_client(endpoint)
            while not stop.is_set():
                outcome, _ = opens_with(own, key, list(identities.values()))
                reader_saw["right plaintext" if outcome == key else outcome] += 1

        reader = threading.Thread(target=read)
        writers = [threading.Thread(target=write, args=(name,)) for name in identities]
        reader.start()
        for thread in writers:
            thread.start()
        for thread in writers:
            thread.join()
        stop.set()
        reader.join()

        # Which body survived, and whose metadata sits on it.
        opened_by = [
            name for name, identity in identities.items() if opens_with(client, key, [identity])[0] == key
        ]
        metadata = client.head_object(Bucket=BUCKET, Key=key).get("Metadata", {})
        if len(opened_by) != 1:
            torn += 1
            print(f"round {round_number}: surviving object opens with {opened_by}")
            continue
        winners[opened_by[0]] += 1
        if metadata.get("writer") != opened_by[0]:
            metadata_mismatch += 1
            print(f"round {round_number}: body of {opened_by[0]}, metadata {metadata}")

    print(f"{rounds} rounds at {size_mib} MiB, two writers at once on one key")
    print("  surviving body sealed by:", dict(winners))
    print("  surviving object not openable by exactly one writer's identity:", torn)
    print("  metadata of one writer on the body of the other:", metadata_mismatch)
    print("  what the reader saw meanwhile:", dict(reader_saw))

    # Does the server know a conditional write?
    client.delete_object(Bucket=BUCKET, Key=key)
    for label, call in (
        (
            "put_object, small",
            lambda: client.put_object(Bucket=BUCKET, Key="small", Body=b"x", IfNoneMatch="*"),
        ),
        (
            "upload_fileobj, multipart",
            lambda: client.upload_fileobj(
                io.BytesIO(sealed["a"].read_bytes()), BUCKET, key, ExtraArgs={"IfNoneMatch": "*"}
            ),
        ),
    ):
        results = []
        for _ in range(2):
            try:
                call()
                results.append("written")
            except ClientError as error:
                results.append("refused " + error.response["Error"]["Code"])
            except Exception as error:
                results.append(type(error).__name__ + ": " + str(error)[:90])
        print(f"  If-None-Match: * | {label}: first {results[0]}, second {results[1]}")
    print("  allowed upload arguments include IfNoneMatch:", "IfNoneMatch" in S3Transfer.ALLOWED_UPLOAD_ARGS)
