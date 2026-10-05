(configuration-reference)=

# Configuration

Previously reads its settings from eight environment variables.
Every command reads `PREVIOUSLY_DSN`; the seven `PREVIOUSLY_BLOB_*` variables are read only by the commands that store, fetch or delete a blob, as the table below says per variable.

## Database

| Variable | Form | Used by |
|---|---|---|
| `PREVIOUSLY_DSN` | `postgresql+psycopg://user:pass@host:5432/database` | The `previously` command line, and Alembic migrations. |

Alembic migrations resolve the connection string through `migrations.dsn.resolve_dsn`.
An explicit `sqlalchemy.url` in `alembic.ini`, or set programmatically on the `Config` object, takes precedence over `PREVIOUSLY_DSN`.
With neither set, the migration fails with an error that names both.

```{important}
PostgreSQL 15 or newer.
`NULLS NOT DISTINCT` is not optional; see {ref}`concurrency`.
```

## Blob settings

The blob store is an S3 bucket; see {ref}`blobs`.

| Variable | Meaning | Missing at |
|---|---|---|
| `PREVIOUSLY_BLOB_ENDPOINT` | The address of the S3 server, such as `http://localhost:9000`. | `append --attach`, `blob get`, `verify --blobs`, a `redact` that deletes a blob |
| `PREVIOUSLY_BLOB_REGION` | The region the server expects in a signed request, such as `us-east-1`. | `append --attach`, `blob get`, `verify --blobs`, a `redact` that deletes a blob |
| `PREVIOUSLY_BLOB_BUCKET` | The bucket, with neither versioning nor object lock. | `append --attach`, `blob get`, `verify --blobs`, a `redact` that deletes a blob |
| `PREVIOUSLY_BLOB_ACCESS_KEY` | The access key for the bucket. | `append --attach`, `blob get`, `verify --blobs`, a `redact` that deletes a blob |
| `PREVIOUSLY_BLOB_SECRET_KEY` | The secret key for the bucket; no message prints it. | `append --attach`, `blob get`, `verify --blobs`, a `redact` that deletes a blob |
| `PREVIOUSLY_BLOB_RECIPIENT` | The age X25519 recipient new blobs are sealed to, in its `age1…` spelling. It's public. | `append --attach` |
| `PREVIOUSLY_BLOB_IDENTITIES` | A directory holding one file per recipient, named after it, with the identity that opens what was sealed to it. No message prints an identity. | `blob get`, `verify --blobs` |

A command that needs a variable and finds it unset or empty returns 2 and names the first one missing:

```text
Error: PREVIOUSLY_BLOB_RECIPIENT is not set
```

A `PREVIOUSLY_BLOB_IDENTITIES` that names no directory, a path that doesn't exist or a file, returns 2 as well, with the path in the sentence:

```text
Error: PREVIOUSLY_BLOB_IDENTITIES is not a directory: /srv/previously/identities
```

A directory that exists and holds no identity for a key isn't an error of the setting: `verify --blobs` reports each blob sealed to that key as one that can't be opened, with exit code 1, and `blob get` refuses such a blob with exit code 2.

An endpoint without a scheme, such as `localhost:9000`, or a region the S3 client can't parse, such as `us east 1`, returns 2 as well, with one sentence that names the endpoint, the bucket, the region and the kind of refusal, and never a key.

Every other command, and `append` without `--attach` and `verify` without `--blobs`, reads none of them; `redact` reads the five settings of the store only when it has a blob to delete.
