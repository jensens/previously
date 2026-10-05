## Task 3: Das Image und sein Smoke-Test

**Files:**
- Create: `Dockerfile`, `.dockerignore`, `scripts/smoke-image.sh`

**Interfaces:**
- Consumes: `previously migrate` (Aufgabe 2).
- Produces: `docker build --build-context wheels=<dir> --build-arg PREVIOUSLY_VERSION=<v> -t <tag> .`; `scripts/smoke-image.sh <image>` mit Rückgabecode 0 bei Erfolg; Aufgabe 4 ruft beides.

- [ ] **Step 1: `Dockerfile`** — gelaufen im Spike, so übernehmen:

```dockerfile
# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# The dependencies exactly as `uv.lock` has them, then Previously itself in the
# version of the release, from PyPI, without resolving anything again. The
# image thus holds the package that is on PyPI and the versions the gates ran
# against ({ref}`delivery`).
FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim@sha256:8e88a074b0969bdc461f681727238e109438d70771828909f9ef19cfcc96c43a

ARG PREVIOUSLY_VERSION

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# `wheels` is a named build context: an empty directory in the release
# workflow, where the package comes from PyPI; a directory holding a locally
# built wheel otherwise. One file, two ways in.
RUN --mount=type=bind,from=wheels,target=/wheels \
    uv pip install --python /app/.venv/bin/python --no-deps --find-links /wheels \
    "previously==${PREVIOUSLY_VERSION}"

RUN groupadd --system --gid 1000 previously \
    && useradd --system --uid 1000 --gid 1000 --home-dir /app --no-create-home --shell /usr/sbin/nologin previously
USER previously

LABEL org.opencontainers.image.source="https://github.com/jensens/previously" \
      org.opencontainers.image.licenses="AGPL-3.0-or-later" \
      org.opencontainers.image.version="${PREVIOUSLY_VERSION}"

ENTRYPOINT ["previously"]
CMD ["--help"]
```

Ein `{ref}` in einem Dockerfile hält kein Test (`test_docs_references` liest nur `*.py`); die Marke `delivery` entsteht in Aufgabe 5. Steht sie dann nicht, ist die Zeile falsch — Aufgabe 5 prüft es.

- [ ] **Step 2: `.dockerignore`** — alles außer `pyproject.toml` und `uv.lock`; das Image kopiert nichts anderes aus dem Kontext:

```
*
!pyproject.toml
!uv.lock
```

- [ ] **Step 3: `scripts/smoke-image.sh`** — gelaufen im Spike, grün; der Text ist die Datei `smoke-image.sh` aus dem Scratchpad dieser Sitzung, hier vollständig:

```bash
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
chmod 0777 "$WORK"

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
  docker exec "$PG" pg_isready -U previously -d previously > /dev/null 2>&1 && break
  sleep 1
done

run() {
  docker run --rm --network "$NET" -v "$WORK:/work" -w /work \
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
test "$(run --entrypoint id "$IMAGE" -u)" = 1000
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
```

Die Identität entsteht zur Laufzeit in einem temporären Verzeichnis, das das Skript am Ende löscht, und öffnet nichts außerhalb dieses Laufs.

- [ ] **Step 4: Lokal bauen und den Smoke-Test laufen lassen**

```bash
SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0.dev0 uv build --wheel -o /tmp/<scratch>/wheels
docker build --build-context wheels=/tmp/<scratch>/wheels --build-arg PREVIOUSLY_VERSION=0.0.0.dev0 -t previously:local .
bash scripts/smoke-image.sh previously:local
```
Expected: `smoke test passed: previously:local`. Danach `docker rmi previously:local`.

- [ ] **Step 5: Die Mutationen des Smoke-Tests** — jede rot, jede sofort zurück:
  - `USER previously` im Dockerfile entfernt → „runs as user 1000" scheitert.
  - im Dockerfile `--frozen` → `--upgrade` bei `uv sync` (löst frei auf) → der Lock-Vergleich scheitert, **wenn** eine neuere Fassung existiert; sonst melden, dass die Mutation an diesem Tag nichts misst.
  - `cmp` gegen eine andere Datei → scheitert.
  Kontrolle: unverändert grün.

- [ ] **Step 6: shellcheck** im Container (`koalaman/shellcheck:v0.11.0` oder die zum Zeitpunkt neueste Fassung, gepinnt) über `scripts/smoke-image.sh`: keine Meldung, oder jede Meldung im Bericht begründet.

- [ ] **Step 7: Sechs Tore, Commit**

```bash
git add Dockerfile .dockerignore scripts/smoke-image.sh
git commit -F <message-file>   # "build: an image of the released package, and its smoke test"
```

---

