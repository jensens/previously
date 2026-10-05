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
That line can name the user, and quote the value of a query parameter the client library rejects; {ref}`cli-reference` says where the line comes from.

(dsn-form)=

### The accepted form

`previously` reads `PREVIOUSLY_DSN` by the form below, and refuses anything else before it connects, with one sentence that names no part of the string.
Every subcommand, `migrate` included, builds the connection from the parts the form names, and SQLAlchemy never parses the string; `alembic`, run in a checkout, parses it with SQLAlchemy and doesn't hold it to this form.

| Part | Form |
|---|---|
| Scheme | `postgresql://` or `postgresql+psycopg://`, in lowercase. |
| User part | Optional: a user name, then optionally `:` and the password, then `@`. |
| Host | A host name of labels of 1 to 63 letters, digits, `-` and `_`, joined by `.`, or an IPv6 address in brackets, such as `[::1]`. |
| Port | Optional: `:` and a number from 1 to 65535, in digits alone. |
| Database | Optional: `/` and the database name. |
| Query | Optional: `?` and pairs `key=value`, joined by `&`, each key at most once. |

- In the user name and the password, every character but a letter, a digit or one of `-._~!$&'()*+,;=` stands as its escape sequence, such as `%40` for `@` and `%2F` for `/`, and `previously` reads it as the character.
- The database name takes the same characters but `&`, which stands as `%26`.
- The password stands in the user part and nowhere else.
- The query takes the keys `application_name`, `channel_binding`, `connect_timeout`, `require_auth`, `sslcert`, `sslkey`, `sslmode` and `sslrootcert`, and no other; `password` is refused there.
- A query value holds letters, digits, `-._~/` and escape sequences; any other character in it, `+`, `=`, `&` or a space among them, stands as its escape sequence.
- An escape sequence that isn't UTF-8 is refused, and so is one of a control character or a line separator, such as `%00`, `%0A`, `%C2%85` or `%E2%80%A8`.

The `uri` that CloudNativePG writes into the secret of an application's role has this form, and `previously` takes it unchanged.

The form reads a string in one way, which isn't always the way its writer meant.
A string without `@` has no user part, and what follows the first `:` there is the port.
A mistyped string that matches the form is read as written, and a message can then print a piece of a password:

| Mistyped | Printed |
|---|---|
| The `@host` forgotten after a password of up to five digits: `user:12345/database` | The user name as the host, and the password as the port. |
| The `@host` and the database forgotten: `user:12345/rest` | The rest of the password as the database. |
| A raw `@` in the password and the `@host` forgotten: `user:pw@rest`, or `user:pw@[rest]` with a rest of hexadecimal digits | The rest of the password as the host. |
| The password as the value of `sslmode`, `require_auth` or `channel_binding` | The value, decoded, in the client library's reason. |
| The password as the user name | The user name, in the client library's reason when the server refuses the login. |
| The password as the database name | The database name, in the sentence of `previously`. |

`alembic`, run in a checkout, isn't held to the form, as said above.

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
