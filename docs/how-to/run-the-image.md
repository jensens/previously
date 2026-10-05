(run-the-image)=

# How to run Previously from its image

This guide shows you how to run Previously from its container image with `docker run`, one container per command, and how to build the image yourself from a checkout.
In a cluster, the platform's operators build the jobs, the scheduled runs and the tools pod from the same image; this guide covers the commands, not the cluster.
For the reasons behind how the image is built, see {ref}`delivery`.

## Choose the image

The image is `ghcr.io/jensens/previously`, for `linux/amd64` and `linux/arm64`.
Use the exact version as its tag, such as `ghcr.io/jensens/previously:0.1.0a1`.
A pre-release, which every release until `1.0.0` is, has no other tag, and `latest` follows only stable releases.

The image runs `previously`, and without arguments it prints the help:

```shell
docker run --rm ghcr.io/jensens/previously:0.1.0a1
```

It runs as user 1000 by default and works under any other user ID, opens no port, and keeps nothing between two runs: the data lives in PostgreSQL and in the bucket.

## Reach the database

The container reads its settings from the environment, as the command line does; {ref}`configuration-reference` lists them.
It needs a PostgreSQL that it can reach under a name, so put the database and the containers of Previously on one Docker network.

This guide uses the network `previously-blobs` that {ref}`run-a-blob-store-on-your-machine` creates for the S3 server.
If you don't need blobs, create the network on its own:

```shell
docker network create previously-blobs
```

Start a database on it, if you don't run one already:

```shell
docker run -d --name previously-db --network previously-blobs \
    -e POSTGRES_USER=previously \
    -e POSTGRES_PASSWORD=previously \
    -e POSTGRES_DB=previously \
    postgres:17
```

Export the connection string with the database's name on the network as its host:

```shell
export PREVIOUSLY_DSN=postgresql+psycopg://previously:previously@previously-db:5432/previously
```

`-e PREVIOUSLY_DSN` without a value hands the variable from your shell to the container, so the string stays out of the command line.

## Migrate first

Bring the schema up to the newest revision before you run anything else, after every new version of the image:

```shell
docker run --rm --network previously-blobs -e PREVIOUSLY_DSN \
    ghcr.io/jensens/previously:0.1.0a1 migrate
```

On a new database, it prints the revision the database came from and the one it's at now:

```text
migrated: (empty) -> 0004_event_blob
```

Run it again, and it reports that nothing had to run:

```text
up to date: 0004_event_blob
```

Every other command refuses a database whose schema is behind, and an image older than the database refuses to migrate it; {ref}`cli-reference` gives both messages.

## Run a command

Run each command in a container of its own, with the same network and the same variable:

```shell
docker run --rm --network previously-blobs -e PREVIOUSLY_DSN \
    ghcr.io/jensens/previously:0.1.0a1 append \
    --source email --external-id 2026-10-05-first@example.org \
    --text "The first event recorded from the image."
docker run --rm --network previously-blobs -e PREVIOUSLY_DSN \
    ghcr.io/jensens/previously:0.1.0a1 project
docker run --rm --network previously-blobs -e PREVIOUSLY_DSN \
    ghcr.io/jensens/previously:0.1.0a1 verify
```

To keep the anchor file outside the container, pass `-i` and read the anchors from standard input, and don't pass `-t`:

```shell
docker run --rm --network previously-blobs -e PREVIOUSLY_DSN \
    ghcr.io/jensens/previously:0.1.0a1 anchor >> anchors.txt
docker run --rm -i --network previously-blobs -e PREVIOUSLY_DSN \
    ghcr.io/jensens/previously:0.1.0a1 verify --anchors - < anchors.txt
```

{ref}`verify-the-chain` says where the anchor file has to live and why a terminal breaks it.

## Attach and fetch a file

A command that stores, fetches or deletes a blob needs the settings of the store as well, and it reads and writes files, so it needs a directory from your machine.
Export the settings and create a key as {ref}`run-a-blob-store-on-your-machine` and {ref}`keep-the-blob-key-safe` show, then change two of them for the container: the store's address is its name on the network, and the directory of identities is where you mount it.

Attach a file from the current directory:

```shell
docker run --rm --network previously-blobs --user "$(id -u):$(id -g)" \
    -v "$PWD:/work" -w /work \
    -e PREVIOUSLY_DSN \
    -e PREVIOUSLY_BLOB_ENDPOINT=http://previously-blobs:9000 \
    -e PREVIOUSLY_BLOB_REGION -e PREVIOUSLY_BLOB_BUCKET \
    -e PREVIOUSLY_BLOB_ACCESS_KEY -e PREVIOUSLY_BLOB_SECRET_KEY \
    -e PREVIOUSLY_BLOB_RECIPIENT \
    ghcr.io/jensens/previously:0.1.0a1 append \
    --source email --external-id 2026-10-05-letter@example.org \
    --text "The signed letter." --attach letter.txt
```

Fetch it again by its address, with the directory of identities mounted read-only:

```shell
docker run --rm --network previously-blobs --user "$(id -u):$(id -g)" \
    -v "$PWD:/work" -w /work \
    -v "$PWD/identities:/identities:ro" \
    -e PREVIOUSLY_DSN \
    -e PREVIOUSLY_BLOB_ENDPOINT=http://previously-blobs:9000 \
    -e PREVIOUSLY_BLOB_REGION -e PREVIOUSLY_BLOB_BUCKET \
    -e PREVIOUSLY_BLOB_ACCESS_KEY -e PREVIOUSLY_BLOB_SECRET_KEY \
    -e PREVIOUSLY_BLOB_IDENTITIES=/identities \
    ghcr.io/jensens/previously:0.1.0a1 blob get \
    "$(sha256sum letter.txt | cut -d' ' -f1)" --output fetched.txt
```

`--user "$(id -u):$(id -g)"` runs the container as you.
The identity file is readable by its owner only, and the fetched file then belongs to you rather than to user 1000.
Mount the identities only into the containers of `blob get` and `verify --blobs`, the two commands that read them; `append --attach` needs only the recipient.

## Build the image yourself

Build it from a checkout when you want to try a change before it's released.
You need Docker and [uv](https://docs.astral.sh/uv/), and for the smoke test `openssl` as well.

Build a wheel of the checkout, with a version you give it, into a directory outside the checkout:

```shell
SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0.dev0 uv build --wheel -o /tmp/previously-wheels
```

Build the image with that directory as the build context `wheels`, and the same version:

```shell
docker build --build-context wheels=/tmp/previously-wheels \
    --build-arg PREVIOUSLY_VERSION=0.0.0.dev0 -t previously:local .
```

The `Dockerfile` looks for the package in `wheels` as well as on PyPI, and a version that only your wheel has comes from there; a release passes an empty directory, so its package comes from PyPI.

Run the smoke test against the image, from the root of the checkout:

```shell
bash scripts/smoke-image.sh previously:local
```

It starts PostgreSQL 17 and an S3 server in containers of its own, runs the image against them, removes them again, and ends with this line:

```text
smoke test passed: previously:local
```

## Remove what you started

```shell
docker rm -f -v previously-db
docker rmi previously:local
```

Remove the S3 server and the network as {ref}`run-a-blob-store-on-your-machine` shows, or the network alone with `docker network rm previously-blobs` if you created it here.
