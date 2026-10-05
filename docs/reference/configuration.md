(configuration-reference)=

# Configuration

Previously reads its settings from eight environment variables.
Every command reads `PREVIOUSLY_DSN`; the seven `PREVIOUSLY_BLOB_*` variables are read only by the commands that store, fetch or delete a blob, as the table below says per variable.

## Database

| Variable | Form | Used by |
|---|---|---|
| `PREVIOUSLY_DSN` | `postgresql+psycopg://user:pass@host:5432/database` | The `previously` command line, `previously migrate` included, and `alembic` in a checkout. |

A message about the database names the database, the host and the port from `PREVIOUSLY_DSN`, and of the connection string nothing else, in its own words.
When connecting fails, because the server refuses the password, doesn't have the database, or can't be reached, every command prints one such sentence and quotes the first line of the reason.
That line can name the user, and quote the value of a query parameter the client library rejects; the password appears in neither, and {ref}`cli-reference` says where the line comes from.

A character such as `@`, `:`, `/`, `?`, `#` or `%` inside the user name, the password, the database name or a query value stands in the connection string as its escape sequence, such as `%40` for `@`, and `previously` reads it as the character.
A `PREVIOUSLY_DSN` that holds such a character without its escape sequence, so that it would be cut into its parts elsewhere than its writer meant, is refused before anything connects.

`previously migrate` reads the connection string from `PREVIOUSLY_DSN` alone.

`alembic`, run in a checkout during development, resolves the connection string through `previously.migrations.dsn.resolve_dsn`.
There, an explicit `sqlalchemy.url` in `alembic.ini`, or set programmatically on the `Config` object, takes precedence over `PREVIOUSLY_DSN`.
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
