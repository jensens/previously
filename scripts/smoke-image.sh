#!/usr/bin/env bash
# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Smoke test of one image: run from the repository root as
# `scripts/smoke-image.sh IMAGE`. Starts PostgreSQL 17 and RustFS 1.0.1 on a
# network of its own, runs the image against them, and removes everything it
# started, also when a step fails.
set -euo pipefail

IMAGE="$1"
NET="previously-smoke-$$"
PG="$NET-pg"
S3="$NET-s3"
WORK="$(mktemp -d)"

cleanup() {
  docker rm -f -v "$PG" "$S3" > /dev/null 2>&1 || true
  docker network rm "$NET" > /dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT

SECRET="$(openssl rand -hex 16)"
docker network create "$NET" > /dev/null
docker run -d --name "$PG" --network "$NET" \
  -e POSTGRES_USER=previously -e POSTGRES_PASSWORD=previously -e POSTGRES_DB=previously \
  postgres:17 > /dev/null
docker run -d --name "$S3" --network "$NET" \
  -e RUSTFS_ACCESS_KEY=smoke -e RUSTFS_SECRET_KEY="$SECRET" \
  rustfs/rustfs:1.0.1 > /dev/null
for _ in $(seq 1 60); do
  # `-h localhost` asks over TCP: without it, the temporary server that the
  # image starts while it initializes (socket only) would count as ready.
  docker exec "$PG" pg_isready -h localhost -U previously -d previously > /dev/null 2>&1 && break
  sleep 1
done

# Every container but the one that checks the default user runs as the host
# user. What it writes into $WORK then belongs to the host user, which can read
# and remove all of it whatever its uid is (a GitHub runner is 1001): a file the
# container wrote as uid 1000 would be unreadable for `cmp` (`blob get` writes
# mode 0600) and the key could not be removed. It also proves the image works
# under a foreign uid, as it does in Kubernetes with `runAsUser`.
run() {
  docker run --rm --user "$(id -u):$(id -g)" --network "$NET" -v "$WORK:/work" -w /work \
    -e PREVIOUSLY_DSN="postgresql+psycopg://previously:previously@$PG:5432/previously" \
    -e PREVIOUSLY_BLOB_ENDPOINT="http://$S3:9000" \
    -e PREVIOUSLY_BLOB_REGION=us-east-1 \
    -e PREVIOUSLY_BLOB_BUCKET=smoke \
    -e PREVIOUSLY_BLOB_ACCESS_KEY=smoke \
    -e PREVIOUSLY_BLOB_SECRET_KEY="$SECRET" \
    -e PREVIOUSLY_BLOB_RECIPIENT="${RECIPIENT:-}" \
    -e PREVIOUSLY_BLOB_IDENTITIES=/work/identities \
    "$@"
}

echo "::group::the image runs as user 1000"
test "$(docker run --rm --entrypoint id "$IMAGE" -u)" = 1000
echo "::endgroup::"

echo "::group::installed versions match uv.lock"
uv export --frozen --no-dev --no-emit-project --no-hashes \
  | grep -E '^[A-Za-z0-9_.-]+==' | sed 's/ .*//' | tr 'A-Z_' 'a-z-' | sort > "$WORK/expected.txt"
run -e UV_CACHE_DIR=/tmp/uv-cache --entrypoint uv "$IMAGE" pip freeze --python /app/.venv/bin/python \
  | grep -E '^[A-Za-z0-9_.-]+==' | grep -vi '^previously==' | tr 'A-Z_' 'a-z-' | sort > "$WORK/actual.txt"
# One direction only: every version installed must stand in the lock. The
# reverse would fail on packages the lock needs only on another platform
# (measured: `tzdata`, for Windows); a missing package shows in the steps below.
if comm -23 "$WORK/actual.txt" "$WORK/expected.txt" | grep .; then
  echo "::error::installed versions differ from uv.lock (lines above)"
  exit 1
fi
echo "::endgroup::"

echo "::group::the bucket and a key made at run time"
for _ in $(seq 1 30); do
  run --entrypoint python "$IMAGE" -c "
import boto3, os
s3 = boto3.client('s3', endpoint_url=os.environ['PREVIOUSLY_BLOB_ENDPOINT'], region_name='us-east-1',
    aws_access_key_id='smoke', aws_secret_access_key=os.environ['PREVIOUSLY_BLOB_SECRET_KEY'])
s3.create_bucket(Bucket='smoke')
" > /dev/null 2>&1 && break
  sleep 1
done
RECIPIENT="$(run --entrypoint python "$IMAGE" -c "
import os, pyrage
identity = pyrage.x25519.Identity.generate()
recipient = str(identity.to_public())
os.makedirs('/work/identities', exist_ok=True)
path = '/work/identities/' + recipient
with open(path, 'w') as f:
    f.write(str(identity) + '\n')
os.chmod(path, 0o600)
print(recipient)
")"
export RECIPIENT
echo "::endgroup::"

echo "::group::migrate, twice"
run "$IMAGE" migrate
run "$IMAGE" migrate | grep -q '^up to date: '
echo "::endgroup::"

echo "::group::a blob in and out"
printf 'Smoke test of the image.\n' > "$WORK/attachment.txt"
run "$IMAGE" append --source smoke --external-id one --text "A smoke test." --attach attachment.txt
ADDRESS="$(sha256sum "$WORK/attachment.txt" | cut -d' ' -f1)"
run "$IMAGE" blob get "$ADDRESS" --output fetched.txt
cmp "$WORK/attachment.txt" "$WORK/fetched.txt"
run "$IMAGE" verify --blobs
run "$IMAGE" anchor
echo "::endgroup::"

echo "smoke test passed: $IMAGE"
