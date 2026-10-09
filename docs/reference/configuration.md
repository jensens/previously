(configuration-reference)=

# Configuration

Previously reads its settings from seventeen environment variables.
Every command reads `PREVIOUSLY_DSN`; the seven `PREVIOUSLY_BLOB_*` variables are read only by the commands that store, fetch or delete a blob, as the table below says per variable, the five `PREVIOUSLY_IMAP_*` variables only by `ingest imap`, and the four settings of the model providers only by `gate try`.

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
| User part | Optional: a user name, then optionally `:` and the password, then `@`. A password without a user name in front of it, such as `postgresql://:password@host/database`, is refused. |
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
| The password as the value of `sslmode`, `require_auth` or `channel_binding`; against a server that offers TLS, as the value of `sslrootcert` with `sslmode` set to `verify-ca` or `verify-full`, or of `sslkey` beside an `sslcert` that names a certificate | The value, decoded, in the client library's reason. |
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
| `PREVIOUSLY_BLOB_ENDPOINT` | The address of the S3 server, such as `http://localhost:9000`. | `append --attach`, `ingest imap`, `blob get`, `verify --blobs`, a `redact` that deletes a blob |
| `PREVIOUSLY_BLOB_REGION` | The region the server expects in a signed request, such as `us-east-1`. | `append --attach`, `ingest imap`, `blob get`, `verify --blobs`, a `redact` that deletes a blob |
| `PREVIOUSLY_BLOB_BUCKET` | The bucket, with neither versioning nor object lock. | `append --attach`, `ingest imap`, `blob get`, `verify --blobs`, a `redact` that deletes a blob |
| `PREVIOUSLY_BLOB_ACCESS_KEY` | The access key for the bucket. | `append --attach`, `ingest imap`, `blob get`, `verify --blobs`, a `redact` that deletes a blob |
| `PREVIOUSLY_BLOB_SECRET_KEY` | The secret key for the bucket; no message prints it. | `append --attach`, `ingest imap`, `blob get`, `verify --blobs`, a `redact` that deletes a blob |
| `PREVIOUSLY_BLOB_RECIPIENT` | The age X25519 recipient new blobs are sealed to, in its `age1…` spelling. It's public. | `append --attach`, `ingest imap` |
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
`ingest imap` reads the five settings of the store and the recipient, and never `PREVIOUSLY_BLOB_IDENTITIES`: taking in seals and opens nothing.

## Mail folder settings

The folder `ingest imap` takes mail in from; see {ref}`cli-reference`.

| Variable | Meaning | Missing at |
|---|---|---|
| `PREVIOUSLY_IMAP_HOST` | The host name or address of the IMAP server, which the server's certificate has to name. | `ingest imap` |
| `PREVIOUSLY_IMAP_PORT` | The port of IMAP over TLS, a number from 1 to 65535. Unset or empty, it's 993. | Never; a value that isn't a port number is refused. |
| `PREVIOUSLY_IMAP_USER` | The user that logs in. | `ingest imap` |
| `PREVIOUSLY_IMAP_PASSWORD` | The user's password, in ASCII; no message prints it. | `ingest imap` |
| `PREVIOUSLY_IMAP_FOLDER` | The full name of the folder on the server, in plain characters, such as `Kunde Müller`; see below. | `ingest imap` |

`ingest imap` reads all five before it connects to anything, and names the first one missing, as the blob settings do:

```text
Error: PREVIOUSLY_IMAP_FOLDER is not set
```

The host, the user and the folder make the name of the watermark, `imap:<user>@<host>/<folder>`, and the port doesn't.
A change to any of the three starts another watermark, and the folder is read from the start; every mail in the log counts as known.

`PREVIOUSLY_IMAP_FOLDER` is the name the server gives the folder, which for a folder at the top level is the name a mail client shows.
For a folder inside another, the name holds the names of the folders above it, each followed by the server's hierarchy delimiter, such as `Kunden.Müller` on a server whose delimiter is `.`, or `Kunden/Müller` on one whose delimiter is `/`.
The server names its delimiter in its answer to the `LIST` command, and a mail client shows only the last part of the name.
`ingest imap` writes the name in the modified UTF-7 of RFC 3501 itself, so the setting holds it as it reads, umlauts included, and never as `Kunde M&APw-ller`.

There is no setting for a certificate.
`ingest imap` verifies the server's certificate and host name against the trust store of the system, and OpenSSL reads a certificate file named in `SSL_CERT_FILE` in place of the system's file.

## Model provider settings

The providers `gate try` can call, and the price file it estimates the cost of a call with; see {ref}`cli-reference`.

| Variable | Meaning | Missing at |
|---|---|---|
| `ANTHROPIC_API_KEY` | The API key of the Anthropic account. No message and no event holds it. | A call the policy gives to `anthropic`. |
| `MISTRAL_API_KEY` | The API key of the Mistral account. No message and no event holds it. | A call the policy gives to `mistral`. |
| `PREVIOUSLY_LOCAL_MODEL_URL` | The address of the OpenAI-compatible API of the local model server, such as `http://localhost:11434/v1`, where `ollama serve` listens by default. | A call the policy gives to `local`. |
| `PREVIOUSLY_PRICES` | The path of a price file to use in place of the one in the package. | Never; unset or empty, the file in the package applies. |

`gate try` reads all four, and no other command reads any of them: `gate explain` calls nothing and estimates nothing.
A missing key or address doesn't stop `gate try`.
Only the adapter of that provider is missing, and only a call the policy gives to that provider fails: it's recorded as a `model_call` with the outcome `error`, and the command returns 2 with a sentence that names the variable:

```text
Error: anthropic: the provider is not configured — set ANTHROPIC_API_KEY
```

A key the provider refuses is the same outcome, with the provider's own sentence, from which `previously` removes the key.
The Anthropic client reads `ANTHROPIC_BASE_URL` on its own, when it's set, and sends the call to that address in place of the one of Anthropic; `previously` names no address for Anthropic, and the tests point the client at a server of their own that way.
Mistral's address is fixed in `previously`, `https://api.mistral.ai/v1`.

The price file is TOML, with the date the prices were read, the price of a million input and a million output tokens per model in dollars, and the factor an inference region adds:

```toml
as_of = 2026-10-09

[models.claude-haiku-5-5]
input = 0.10
output = 0.50

[surcharges]
us = 1.1
```

Each `model_call` carries the SHA-256 of the file as it lies on disk, and the estimate as a decimal string under `cost_usd`, which is `null` for a model the file doesn't name, such as the local one.
The file in the package was read on 2026-10-09 and names its sources in its header.
A file that can't be read, isn't TOML or has no date `as_of` stops `gate try` before it calls anything, with exit code 2 and one sentence that names the file.
