#!/usr/bin/env bash
# Hands-on session, step 2: the bucket (guide `run-a-blob-store-on-your-machine`),
# the key (guide `keep-the-blob-key-safe`), the schema.
S=/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/handson
W=/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1c-blobs
cd "$S"
. ./env.sh
U="$(id -u):$(id -g)"
age-keygen() { docker exec --user "$U" -w "$PWD" previously-handson-age age-keygen "$@"; }

echo "== Create the bucket"
docker run --rm --network previously-blobs \
    -e AWS_ACCESS_KEY_ID="$PREVIOUSLY_BLOB_ACCESS_KEY" \
    -e AWS_SECRET_ACCESS_KEY="$PREVIOUSLY_BLOB_SECRET_KEY" \
    -e AWS_DEFAULT_REGION=us-east-1 \
    amazon/aws-cli:2.37.9 --endpoint-url http://previously-blobs:9000 \
    s3 mb s3://previously-blobs
echo "[exit $?]"

echo "== versioning"
docker run --rm --network previously-blobs \
    -e AWS_ACCESS_KEY_ID="$PREVIOUSLY_BLOB_ACCESS_KEY" \
    -e AWS_SECRET_ACCESS_KEY="$PREVIOUSLY_BLOB_SECRET_KEY" \
    -e AWS_DEFAULT_REGION=us-east-1 \
    amazon/aws-cli:2.37.9 --endpoint-url http://previously-blobs:9000 \
    s3api get-bucket-versioning --bucket previously-blobs
echo "[exit $?]"

echo "== object lock"
docker run --rm --network previously-blobs \
    -e AWS_ACCESS_KEY_ID="$PREVIOUSLY_BLOB_ACCESS_KEY" \
    -e AWS_SECRET_ACCESS_KEY="$PREVIOUSLY_BLOB_SECRET_KEY" \
    -e AWS_DEFAULT_REGION=us-east-1 \
    amazon/aws-cli:2.37.9 --endpoint-url http://previously-blobs:9000 \
    s3api get-object-lock-configuration --bucket previously-blobs
echo "[exit $?]"

echo "== Point Previously at the server"
{
  echo "export PREVIOUSLY_BLOB_ENDPOINT=http://localhost:9000"
  echo "export PREVIOUSLY_BLOB_REGION=us-east-1"
  echo "export PREVIOUSLY_BLOB_BUCKET=previously-blobs"
} >> env.sh

echo "== Create the key"
age-keygen -o key.txt
mkdir identities
mv key.txt "identities/$(age-keygen -y key.txt)"
ls -l identities | sed -E 's/^(\S+) .* (age1\S+)$/\1 \2/'
echo "identity file: $(grep -c '^AGE-SECRET-KEY-1' identities/*) secret line(s), $(grep -c '^#' identities/*) comment line(s)"
{
  echo "export PREVIOUSLY_BLOB_RECIPIENT=$(ls identities)"
  echo "export PREVIOUSLY_BLOB_IDENTITIES=$PWD/identities"
} >> env.sh

echo "== schema"
cd "$W"
uv run alembic upgrade head 2>&1 | tail -4
echo "[exit $?]"
