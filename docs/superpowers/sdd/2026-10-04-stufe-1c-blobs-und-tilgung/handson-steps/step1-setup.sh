#!/usr/bin/env bash
# Hands-on session, step 1: a fresh database, the blob store of the guide
# `run-a-blob-store-on-your-machine`, and a container that carries `age`.
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
} > env.sh
chmod 600 env.sh
docker ps -a --format '{{.Names}}' | grep -E "^previously" || echo "no container named previously*"
docker network ls --format '{{.Name}}' | grep -E "^previously" || echo "no network named previously*"
docker run -d --name previously-handson-pg -p 5434:5432 \
    -e POSTGRES_USER=previously -e POSTGRES_PASSWORD=previously -e POSTGRES_DB=previously \
    postgres:17 >/dev/null
echo "pg started"
. ./env.sh

# --- the guide: Start the server ---
docker network create previously-blobs >/dev/null
echo "network created"
docker run -d --name previously-blobs --network previously-blobs -p 9000:9000 \
    -e RUSTFS_ACCESS_KEY="$PREVIOUSLY_BLOB_ACCESS_KEY" \
    -e RUSTFS_SECRET_KEY="$PREVIOUSLY_BLOB_SECRET_KEY" \
    rustfs/rustfs:1.0.1 >/dev/null
echo "rustfs started"

# --- age, in a container: nothing is installed on the host ---
docker run -d --name previously-handson-age -v "$S:$S" -w "$S" alpine:3.22 sleep 7200 >/dev/null
echo "age box started"
docker exec previously-handson-age apk add --no-cache age 2>&1 | tail -1
docker exec previously-handson-age age --version
