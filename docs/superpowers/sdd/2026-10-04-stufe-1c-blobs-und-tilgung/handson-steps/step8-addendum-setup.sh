#!/usr/bin/env bash
# Hands-on addendum after the code fix wave (head d02aaf6): a fresh database,
# blob store, bucket and key, set up as the guides say.
set -e
S=/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/handson
W=/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1c-blobs
rm -rf "$S"
mkdir -p "$S"
cd "$S"
{
  echo "export PATH=$W/.venv/bin:\$PATH"
  echo "export PREVIOUSLY_DSN=postgresql+psycopg://previously:previously@localhost:5434/previously"
  echo "export PREVIOUSLY_BLOB_ACCESS_KEY=previously-dev"
  echo "export PREVIOUSLY_BLOB_SECRET_KEY=$(openssl rand -hex 16)"
  echo "export PREVIOUSLY_BLOB_ENDPOINT=http://localhost:9000"
  echo "export PREVIOUSLY_BLOB_REGION=us-east-1"
  echo "export PREVIOUSLY_BLOB_BUCKET=previously-blobs"
} > env.sh
chmod 600 env.sh
. ./env.sh
docker run -d --name previously-handson-pg -p 5434:5432 \
    -e POSTGRES_USER=previously -e POSTGRES_PASSWORD=previously -e POSTGRES_DB=previously \
    postgres:17 >/dev/null
docker network create previously-blobs >/dev/null
docker run -d --name previously-blobs --network previously-blobs -p 9000:9000 \
    -e RUSTFS_ACCESS_KEY="$PREVIOUSLY_BLOB_ACCESS_KEY" \
    -e RUSTFS_SECRET_KEY="$PREVIOUSLY_BLOB_SECRET_KEY" \
    rustfs/rustfs:1.0.1 >/dev/null
docker run -d --name previously-handson-age -v "$S:$S" -w "$S" alpine:3.22 sleep 7200 >/dev/null
docker exec previously-handson-age apk add --no-cache age >/dev/null 2>&1
sleep 5
docker run --rm --network previously-blobs \
    -e AWS_ACCESS_KEY_ID="$PREVIOUSLY_BLOB_ACCESS_KEY" \
    -e AWS_SECRET_ACCESS_KEY="$PREVIOUSLY_BLOB_SECRET_KEY" \
    -e AWS_DEFAULT_REGION=us-east-1 \
    amazon/aws-cli:2.37.9 --endpoint-url http://previously-blobs:9000 \
    s3 mb s3://previously-blobs
U="$(id -u):$(id -g)"
docker exec --user "$U" -w "$S" previously-handson-age age-keygen -o key.txt 2>/dev/null
mkdir identities
R=$(docker exec --user "$U" -w "$S" previously-handson-age age-keygen -y key.txt)
mv key.txt "identities/$R"
{
  echo "export PREVIOUSLY_BLOB_RECIPIENT=$R"
  echo "export PREVIOUSLY_BLOB_IDENTITIES=$S/identities"
} >> env.sh
cd "$W"
. "$S/env.sh"
uv run alembic upgrade head 2>&1 | tail -1
git -C "$W" log --oneline -1
