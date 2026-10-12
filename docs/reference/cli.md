(cli-reference)=

# Command line

`previously` is the command-line entry point.
It has twenty-five subcommands: `migrate`, `append`, `ingest`, `redact`, `log`, `verify`, `anchor`, `show`, `blob`, `project`, `chronicle`, `stats`, `policy`, `gate`, `client`, `access`, `assert`, `approve`, `reject`, `obligations`, `obligation`, `decisions`, `decision`, `mcp`, and `serve`.
Every subcommand reads the database connection string from `PREVIOUSLY_DSN`; see {ref}`configuration-reference`.
`append --attach`, `ingest imap`, `blob get` and `verify --blobs` also read the blob settings, and `redact` reads them when it has a blob to delete; no other subcommand reads any of them.
`ingest imap` alone reads the `PREVIOUSLY_IMAP_*` settings, and `gate try` alone reads `ANTHROPIC_API_KEY`, `MISTRAL_API_KEY`, `PREVIOUSLY_LOCAL_MODEL_URL` and `PREVIOUSLY_PRICES`.
`mcp` alone reads `PREVIOUSLY_MCP_CLIENT`, `serve` alone reads `PREVIOUSLY_MCP_ADDRESS` and `PREVIOUSLY_MCP_ALLOWED_HOSTS`, and both read `PREVIOUSLY_MCP_CONFIRM_KEY`.
A missing setting is an input error that names the first variable missing, in the form `Error: PREVIOUSLY_BLOB_BUCKET is not set`.
An error sentence prints every control character but a tab and a line feed as `\xNN`, such as `\x1b` for the escape character, because a key it quotes can be the Message-ID of a mail.
A transaction the database aborts in a conflict with a concurrent one, a deadlock or a lock not granted in time, is a storage error with exit code 2, in the form `Error: the database aborted the operation in a conflict with a concurrent one; run the command again`.

A message about the database names the database, the host and the port from `PREVIOUSLY_DSN`, and of the connection string nothing else, in its own words.
The reason it quotes can say more: the line from the client library can name the user, and quote the value of a query parameter it rejects, such as an `sslmode` it doesn't know.
`previously` takes the password from the user part of the connection string alone, so a message can carry a piece of it only where the string is mistyped, such as with the `@host` forgotten or the password in the place of another part; {ref}`the accepted form <dsn-form>` lists each such case and what gets printed.

When connecting to the database fails, every subcommand prints one sentence to standard error and returns 2, followed by the first line of the reason:

```text
Error: connecting to database previously at localhost:5432 failed: connection to server at "127.0.0.1", port 5432 failed: FATAL:  password authentication failed for user "previously"
Error: connecting to database nope at localhost:5432 failed: connection to server at "127.0.0.1", port 5432 failed: FATAL:  database "nope" does not exist
Error: connecting to database previously at localhost:5432 failed: connection to server at "127.0.0.1", port 5432 failed: Connection refused
Error: connecting to database previously at localhost:5432 failed: the client library refused a query parameter of PREVIOUSLY_DSN
```

The first is a password the server refuses, the second a database the server doesn't have, and the third a port where nothing listens.
The fourth is a value of a query parameter that the client library refuses before it connects, such as a `connect_timeout` that isn't a number, and its reason is fixed: it quotes nothing of the connection string.
In the first three, the reason is the first line of the message the driver, `psycopg`, gives for the failed connection, without the `connection failed: ` the driver puts in front.
Most of that line comes from `libpq`, the PostgreSQL client library: `connection to server at …` and a reason from the operating system, such as `Connection refused`, come from the client, in the client's locale, and what follows `FATAL:` comes from the server, in the server's language.
Some reasons are the driver's own text, such as `failed to resolve host '…'` for a host name that doesn't resolve.

When the database ends an operation after the connection stands, such as with a statement timeout, the sentence says so and quotes the server's reason, in the server's language:

```text
Error: the operation on database previously at localhost:5432 failed: canceling statement due to statement timeout
```

A `PREVIOUSLY_DSN` outside {ref}`the accepted form <dsn-form>` is refused before anything connects, with one sentence that names no part of it:

```text
Error: PREVIOUSLY_DSN is refused — write it as postgresql://user:password@host:5432/database?key=value with the password there and nowhere else, percent-encode every character of the user name, the password, the database name and a value that is not a letter, a digit or one of -._~ (such as `%40` for `@`), and use no key but application_name, channel_binding, connect_timeout, require_auth, sslcert, sslkey, sslmode or sslrootcert
```

Every subcommand but `migrate` needs the schema that `migrate` creates, and against a database without it prints one sentence to standard error and returns 2:

```text
Error: database schema incomplete — `previously migrate` has not run yet
```

## Exit codes

| Command | 0 | 1 | 2 |
|---|---|---|---|
| `migrate` | The schema stands at the newest revision, whether `migrate` ran a migration or found it up to date. | Not used. | The database is at a revision this version doesn't know, the database refused to let the role read the revision or apply a migration, or storage raised an error. |
| `append` | The event was recorded, or an event with the same `--source` and `--external-id` and the same content already existed. | Not used. | The input was invalid, an event with the same `--source` and `--external-id` holds another content, an attachment couldn't be read, a blob setting is missing or invalid, or storage or the blob store raised an error. |
| `ingest` | The run read every folder, with or without variants. | Not used. | A setting is missing or invalid, or `--folder` is empty, the IMAP server couldn't be reached, refused a step or broke the connection off, the log refused a batch, for a mail with more than 500 events or a variant key held with another content (see {ref}`mail-mapping`), or storage or the blob store raised an error; for one folder or more. |
| `redact` | The redaction was recorded and carried out, or the target was already covered by one, every blob it made obsolete is gone from the blob store, and every projection stands at the tip of the log. | Not used. | The input was invalid, the redaction was refused, storage raised an error, or after the redaction was recorded a blob couldn't be deleted or the projections couldn't be caught up. |
| `log` | The log was printed. | Not used. | The input was invalid, or storage raised an error. |
| `verify` | The chain has no finding, every anchor holds, and with `--blobs` no blob has a finding. | The chain, an anchor or, with `--blobs`, a blob has at least one finding. | The input was invalid, a blob setting is missing or invalid, an identity file can't be read, or storage or the blob store raised an error. |
| `anchor` | The anchor line was printed, or the log is empty. | The chain has at least one finding. | Storage raised an error. |
| `show` | The event was printed. | No event exists at the given `event_id`. | The input was invalid, or storage raised an error. |
| `blob` | The blob was written to the file. | No event names the blob, or the blob is erased. | The input was invalid, a blob setting is missing or invalid, the blob is missing from the store, can't be opened or doesn't match its address, the file can't be written, or storage or the blob store raised an error. |
| `project` | Every projection stands at the tip of the log. | Not used. | Storage raised an error, the worker found a gap in the log, or a catch-up at another version rebuilt a projection while this one ran. |
| `chronicle` | The chronicle was printed, even when the window holds no row. | Not used. | The input was invalid, or storage raised an error. |
| `stats` | The statistics were printed, even when no source has an event. | Not used. | Storage raised an error. |
| `policy` | The statement was written, `show` printed the policy, or `gaps` printed what fell back, even when nothing did. | The confirmation was answered with anything but yes, or not answered, and nothing was written. | The input was invalid, the statement was refused, or storage raised an error. |
| `client` | The client was added and its token printed, revoked, or listed, even when none exists. | The confirmation was answered with anything but yes, or not answered, and nothing was written. | The input was invalid, the processor isn't declared, no such client exists to revoke, or storage raised an error. |
| `access` | The access log was printed, even when no call matches. | Not used. | The input was invalid, or storage raised an error. |
| `assert` | The version was written. | The confirmation was answered with anything but yes, or not answered, and nothing was written. | The input was invalid, including a date that isn't one, a malformed `--source` and a reference without a known prefix, the write path refused the version, or storage raised an error. |
| `approve` | Every proposal was made the operator's own. | The confirmation was answered with anything but yes, or not answered, and nothing was written. | The input was invalid, a proposal is none, is direct, is already approved or rejected, or a direct version came after it, the write path refused the batch, or storage raised an error. |
| `reject` | The rejection was written. | The confirmation was answered with anything but yes, or not answered, and nothing was written. | The input was invalid, the proposal is none, is direct, or is already approved or rejected, the write path refused the rejection, or storage raised an error. |
| `obligations`, `decisions` | The list was printed, even when no entry matches. | Not used. | The input was invalid, or storage raised an error. |
| `obligation`, `decision` | The entry was printed. | No entry of that kind stands under the id, or the id names an assertion an erasure took. | Storage raised an error. |
| `mcp` | Standard input closed, and the server ended. | Not used. | `PREVIOUSLY_MCP_CLIENT` is unset or names no client in force, or storage raised an error. |
| `serve` | The server was stopped with an interrupt, such as Ctrl+C. | Not used. | `PREVIOUSLY_MCP_ADDRESS` isn't an address, `PREVIOUSLY_MCP_HOST` is set without it, or storage raised an error. |
| `gate` | `explain` printed the decision, whether it allows a call or denies it; `try` made the call, got an answer that matches the schema, and recorded it. | Not used. | The event doesn't exist, the price file can't be read, storage raised an error, or `try` recorded a call that was denied, failed, refused by the model, or answered against the schema. |

`gate try` returns 3 when the call was made and recorded with an answer that matches the schema, and the provider reported another inference region than the one requested; the code differs from 0 so that a script doesn't read past the alarm.

Every command that receives `SIGTERM` once it has started stops with exit code 143, 128 and the signal's number, and prints nothing to standard error.
The handler is set after the command's imports; a `SIGTERM` in the first fraction of a second, measured at about 0.7 s in the image, isn't caught, and as process 1 of a container the command then runs on until the grace period ends.
A transaction it had open rolls back, so a `migrate` that was applying a migration leaves the schema at the revision it found.
That holds when `previously` runs as process 1 of a container as well.

## `migrate`

Brings the database schema up to the newest revision this version of previously carries.
It takes no arguments.

`migrate` reads `PREVIOUSLY_DSN` and nothing else, and needs neither a checkout nor `alembic.ini`: the migrations ship inside the package.

`migrate` prints one line to standard output, in one of two forms:

```text
migrated: (empty) -> 0005_watermark
migrated: 0002_projections -> 0005_watermark
up to date: 0005_watermark
```

The first form names the revision the database was at, or `(empty)` for a database without a schema, and the newest revision, which the database is at now.
The second means that the database was at the newest revision already, and nothing ran.

`migrate` only goes forward.
Going back to an older revision is `alembic downgrade` in a checkout, with the refusals {ref}`database-schema` lists.

`migrate` holds a PostgreSQL advisory lock on the database for as long as it runs, and releases it once its migration has committed.
A second `migrate` against the same database, such as a second job of the same release, waits until the first is done, and then finds the schema up to date.
The lock is a session lock outside any transaction, and a `migrate` that fails gives it up when it closes its connection.

A database at a revision this version doesn't know, such as one that a newer version of previously has migrated already, is refused, and nothing changes:

```text
Error: the database is at revision 0006_example, which this version of previously does not know; it knows revisions up to 0005_watermark
```

A database that refuses the role in `PREVIOUSLY_DSN` the reading of the revision or a step of the migration gives one sentence that names the newest revision and the database's own reason:

```text
Error: the database refused the migration to 0005_watermark: permission denied for schema public
Error: the database refused the migration to 0005_watermark: permission denied for table alembic_version
```

The first comes from a role that may not create a table in schema `public`, which since PostgreSQL 15 is every role but the owner of the database and a superuser.
The second comes from a role that may not read the table `alembic_version`, where the revision stands.

A connection string outside the accepted form, a server that doesn't answer, a password the server refuses, and a database that doesn't exist each print one sentence to standard error, the same sentence every other command prints for it, as described at the top of this page.

## `append`

Submits one event and prints its `id`.

| Argument | Required | Default | Description |
|---|---|---|---|
| `--source` | Yes | — | The event's source system. |
| `--external-id` | Yes | — | The event's identifier within that source. |
| `--text` | Yes | — | UTF-8 text, at most 1,000,000 bytes. |
| `--occurred-at` | No | The current UTC time. | An ISO 8601 timestamp with a UTC offset. |
| `--evidence` | No | `recollection` | `verbatim` or `recollection`. |
| `--attach FILE` | No | — | A file to store as a blob and name at the event; may repeat. |

`append` splits `--text` into units, one per paragraph, and the text stands in those units alone.
The payload of the event is a JSON object that holds the artifact hash under `artifact_hash` and the kind of evidence under `evidence`, and nothing of the text:

```json
{"artifact_hash": "f20cefad341c110ed191bef30ee347645f114e81202c754d4298bf5794d83a5d", "evidence": "recollection"}
```

The artifact hash is the SHA-256 of the canonical form of `{"text": <--text>, "attachments": <the attachment addresses, sorted>}`, here for `--text Hello` without attachments; see {ref}`artifact-identity`.
The text enters with every line ending as LF, CRLF and a lone CR included, the way `append` splits it into units.
With `--attach`, the payload carries a third key, `blobs`; see *Attachments* below.

`append` prints exactly one line to standard output: the new event's `id`.
Calling `append` again with the same `--source`, `--external-id` and `--text`, the text with other line endings included, and the same attachments in any order, doesn't create a second event.
It prints the existing event's `id` and returns 0.
An event that was erased, or that was written before events carried an artifact hash, counts as the same whatever the text.

Calling `append` with the same `--source` and `--external-id` and another text or other attachments is refused with one sentence on standard error, and nothing is written:

```text
Error: cli/a is known with another content (artifact 7b1a628ef0d8a64e ≠ 0a422dac18a45b5e)
```

The example is `--text A` followed by `--text B` under the same key.
The sentence names the source and the external identifier, then the first 16 hexadecimal characters of the artifact hash the event carries and of the one that arrived.

### Attachments

With `--attach`, `append` reads `PREVIOUSLY_BLOB_RECIPIENT` and the five settings of the blob store, opens every file, stores each file as a blob, and then appends the event; see {ref}`blobs`.
It checks that `PREVIOUSLY_DSN` is set and the recipient before it stores anything, and a recipient that isn't an age X25519 recipient is an input error, quoted in the sentence.
A file that can't be opened, that can't be read twice, such as a pipe, or that fails while it's read is an input error:

```text
Error: cannot read the attachment notes/minutes.txt: No such file or directory
```

A temporary file for the sealed form that can't be created or written is an error as well, with the system's reason after the colon:

```text
Error: cannot write a temporary file: Permission denied
```

On any of these errors, nothing is appended.
A file that can't be opened stores nothing, since `append` opens every file before it stores the first.
A blob stored before a later attachment or the append fails stays in the store, and no event names it.

The payload of the event carries one reference per `--attach`, in the order given, under the key `blobs`:

```json
{"blobs": [{"sha256": "5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03", "size": 6, "media_type": "text/plain", "filename": "hello.txt"}]}
```

`sha256` is the SHA-256 of the file's content in 64 lowercase hexadecimal characters, and `size` is its size in bytes.
`filename` is the file's name without its directory.
`media_type` comes from the name's extension, looked up in the table built into Python's `mimetypes` module and in no file of the system; without a match, or for a compression suffix such as `.gz`, it's `application/octet-stream`.
The same file given twice is two references and one blob.
An event without `--attach` carries no key `blobs`, and a payload must not carry it: `append` refuses it with `payload already carries the key 'blobs' — it is reserved for the attachments`.

## `ingest`

Takes in the mail that IMAP folders hold above the watermark of the last run.
{ref}`mail-mapping` says what a mail turns into, {ref}`artifact-identity` how a sighting is told from a changed mail, and {ref}`connectors` why.
It has one form:

```text
previously ingest imap [--folder NAME]...
```

| Argument | Required | Default | Description |
|---|---|---|---|
| `--folder` | No | The folder `PREVIOUSLY_IMAP_FOLDER` names. | The full name of a folder of the mailbox on the server, as `PREVIOUSLY_IMAP_FOLDER` takes it. Repeatable. |

The run reads the folders one after the other, in the order given, and a name given twice only once.
With `--folder`, it doesn't read `PREVIOUSLY_IMAP_FOLDER`.
An empty name is an input error, `Error: --folder must not be empty`, refused before any setting is read.

One run reads one mailbox, with one user and one password.
Several mailboxes take several runs, each with the settings of its own mailbox.

`ingest imap` reads `PREVIOUSLY_IMAP_ADDRESS`, `PREVIOUSLY_IMAP_USER`, `PREVIOUSLY_IMAP_PASSWORD`, `PREVIOUSLY_IMAP_FOLDER` without `--folder`, `PREVIOUSLY_BLOB_RECIPIENT`, `PREVIOUSLY_DSN` and the five settings of the blob store, in that order; see {ref}`configuration-reference`.
It doesn't read `PREVIOUSLY_BLOB_IDENTITIES`.
It reads every setting and checks the recipient before it connects to anything, and a missing one is an input error in the form `Error: PREVIOUSLY_IMAP_PASSWORD is not set`.
An address outside {ref}`the address form <address-form>` is refused the same way, and so is a `PREVIOUSLY_IMAP_HOST` without the address that took its place:

```text
Error: PREVIOUSLY_IMAP_ADDRESS is not host or host:port, with an IPv6 host in brackets: 'mail.example.org:imaps'
Error: PREVIOUSLY_IMAP_HOST is not read any more: set PREVIOUSLY_IMAP_ADDRESS to host or host:port
```

`ingest imap` connects over TLS only, and verifies the server's certificate and host name against the trust store of the system; no setting turns that off.
OpenSSL reads a certificate file named in `SSL_CERT_FILE` in place of the system's file, and that's how a certificate outside the trust store is trusted.
A socket operation that waits longer than 60 seconds ends the run.
It connects and logs in anew for each folder, opens the folder read-only and reads every mail with `BODY.PEEK[]`, so no mail is marked as read and nothing in the folder changes.

Each folder has a watermark of its own, under `imap:<user>@<host>/<folder>`, with the host as `PREVIOUSLY_IMAP_ADDRESS` spells it and without the port.
A folder named with `--folder` and the same folder named in `PREVIOUSLY_IMAP_FOLDER` share one watermark.
Its position is the folder's `UIDVALIDITY` and the UID of the last mail taken in.
The run fetches the mails above that UID, oldest first and one at a time, maps each onto its events, stores the raw mail and every attachment as a blob, and appends the events in batches; after each batch, it moves the watermark to the last mail the batch covered.
A folder with another `UIDVALIDITY` than the watermark's, such as one deleted and created again, is read from the start, and so is a folder under another name or host; a mail whose events are in the log already counts as known, and so does a mail that another folder gave the log before.
A mail that leaves the folder while the run fetches is passed over.

`ingest imap` prints one line to standard output for each folder it read, once the folder is done:

```text
imap: 5 appended, 0 known, 0 variants, up to uid 4 in Kunde Müller
```

The counts are of events, not of mails: a mail with a mail attached is two events.
`appended` counts the variants as well.
`up to uid` is the UID the watermark stands at, and `up to uid 0` means that the folder hasn't given a mail yet.
The folder's name ends the line, escaped the way `chronicle` escapes its fields.

For each variant, one notice goes to standard error, with the Message-ID the variant deviates from and the `id` of its event:

```text
variant of 20261005101500.4711@example.net: event 6
```

The Message-ID is escaped the way `chronicle` escapes its fields.

`ingest` doesn't catch the projections up; `previously project` does, and may run beside it.

Errors that every folder of the mailbox would meet alike end the run at once, before the next folder, print one sentence to standard error and return 2:

```text
Error: cannot connect to the IMAP server mail.example.org:993: Connection refused
Error: the certificate of the IMAP server mail.example.org:993 does not verify: self-signed certificate
Error: the IMAP server mail.example.org:993 refused the login of pilot
Error: the login of pilot at the IMAP server mail.example.org:993 holds a character other than ASCII, and previously sends the login in ASCII only
```

An error of the database or of the blob store ends the run at once as well.
The folders read before it keep their lines and their watermarks.

Errors of a folder print one line to standard error that names the folder, escaped like the line on standard output, and the server's or the connection's sentence:

```text
Error: folder Kunde Müller: the IMAP server mail.example.org:993 refused to open the folder 'Kunde Müller' of pilot: EXAMINE failed. No such mailbox
Error: folder Kunde Müller: the IMAP server mail.example.org:993 names no UIDVALIDITY for the folder 'Kunde Müller'
Error: folder Kunde Müller: the IMAP server mail.example.org:993 refused the search in the folder 'Kunde Müller': SEARCH failed
Error: folder Kunde Müller: the IMAP server mail.example.org:993 refused to fetch uid 7 from the folder 'Kunde Müller': FETCH failed
Error: folder Kunde Müller: the IMAP server mail.example.org:993 gave uid 7 the INTERNALDATE '31-Okt-2026 10:00:00 +0000', which is not a date
Error: folder Kunde Müller: the IMAP server mail.example.org:993 refused a command: got more than 1000000 bytes
Error: folder Kunde Müller: the connection to the IMAP server mail.example.org:993 broke off
Error: folder Kunde Müller: the connection to the IMAP server mail.example.org:993 broke off: The read operation timed out
```

The run then goes on with the next folder, over a connection of its own, and returns 2 once it has tried every folder.

No message names the password.
A refused login quotes nothing of the server's answer, and a connection that broke off quotes the reason of the system, never what the server sent, which can be mail.
A refusal to open the folder, to search it or to fetch a mail quotes the server's reason, and so does a command the server answers in a way Python's `imaplib` refuses, such as a line longer than 1,000,000 bytes.
An `INTERNALDATE` that isn't a date in the form of RFC 3501 is quoted as the server wrote it.
On every error, the watermark of the folder stands where its last appended batch left it, and the next run fetches the rest again; a blob stored for a batch that wasn't appended stays in the store, and that run finds it there.

Two refusals of the log come back at every run until the mail that causes them leaves the folder; they're errors of that folder, and {ref}`mail-mapping` describes both:

```text
Error: folder Kunde Müller: email/20261005101500.4711@example.net#afe0b335e95e6b9e is known with another content (artifact afe0b335e95e6b9e ≠ afe0b335e95e6b9e)
Error: folder Kunde Müller: 501 events in one transaction, 500 are allowed — larger batches starve against small submissions
```

The first is a variant key the log already holds with another content, which takes two artifact hashes that share their first 64 bits, so the message shows the same 16 characters twice.
The second is a mail that makes more than 500 events together with the mails attached to it.

## `redact`

Erases an event, units of one event, or a blob, and records the erasure as a redaction event; see {ref}`erasure`.
It has three forms:

```text
previously redact event ID --reason TEXT
previously redact units ID SEQ [SEQ] --reason TEXT
previously redact blob HASH --reason TEXT
```

`[SEQ]` may repeat.

| Argument | Required | Default | Description |
|---|---|---|---|
| `ID` | Yes | — | The `id` of the event to erase from, as a positional argument. |
| `SEQ` | Yes, for `units` | — | The `seq` of each unit to erase, as positional arguments, one or more. |
| `HASH` | Yes, for `blob` | — | The blob's address, the SHA-256 of its content in 64 lowercase hexadecimal characters, as a positional argument. |
| `--reason` | Yes | — | Why the erasure happens, not empty and not blanks alone. It stays in the log for good and must not contain what's erased. |

`redact event` erases the event's payload, and the content, speaker, timestamps and salt of every unit.
`redact units` erases the content, speaker, timestamps and salt of the named units, and leaves the event's payload as it is.
A payload that holds the wording of a unit keeps it after `redact units`, readable where `show` prints the payload; `redact event` erases it.
The payload of an event `append` writes holds none of the text, only the artifact hash, the kind of evidence and, with `--attach`, the references to the blobs, so for such an event `redact units` takes the wording with the units.
The artifact hash stays in the payload after `redact units`; it's an unsalted digest of the whole text, and `redact event` erases it.
The order of the `SEQ` arguments doesn't matter, and a `SEQ` given twice counts once.
`redact blob` erases the blob for every event whose reference to it isn't erased yet; their payloads and units stay as they are.
Every hash, the source key, the rows of the units and the rows of the blob register stay, and after `redact units` the payload as well.

A blob has to lie in the blob store as long as at least one event names it whose reference isn't erased.
A reference is erased when its event is erased whole, or when a `redact blob` names its event.
After either `redact event` or `redact blob`, `redact` deletes from the blob store every blob of the target that no longer has to lie there.
Deleting a blob that isn't there is no error.
`redact units` erases no reference and deletes no blob.

The redaction is an event of kind `action`, written in the same transaction as the tombstones.
Its payload holds four keys: `action` with the value `redaction`, `scope` with `event`, `units` or `blob`, `target`, and `reason`.
For `event`, `target` holds the erased event's `id` under `event`, and under `blobs` the hashes the blob register names for the event, in ascending order and empty for an event without attachments.
For `units`, `target` holds the event's `id` under `event`, and under `units` the erased `seq` values in ascending order.
For `blob`, `target` holds the blob's hash under `blob`, and under `events` the `id` of every event whose reference it erases, in ascending order.
A unit a redaction already covers isn't named again, and neither is an event whose reference to the blob is already erased.

`redact` prints one of two lines to standard output:

```text
redacted by event 42
already redacted by event 42
```

The first names the redaction it wrote.
The second means that a redaction already covers the target and nothing was written; it names that redaction, for units the newest of the redactions that cover them, and for a blob the newest of the redactions that erased its references.
In both cases the tombstones are set, and the blobs that no longer have to lie are deleted.

When a `model_call` read the target, `redact` erases the units of that call with it, by a redaction of its own with the reason `cascade of redaction ID`, where `ID` is the redaction that triggered it.
For each such call it prints one more line to standard output, after the first:

```text
cascaded: model_call 43
```

When an assertion rests on what's erased, `redact` erases the assertion with it, by a redaction of the whole assertion with the same reason.
An assertion rests on an event it names as a source, on a unit it cites, and on every unit of an event it cites whole that's erased after the assertion was written.
For each such assertion it prints a line of the same form, and the lines of calls and assertions come in ascending order of `id`:

```text
cascaded: assertion 44
```

An erasure of a blob erases no payload and no unit, so it takes no assertion with it.
A target that no call read and no assertion rests on prints no such line, and neither does a repeat of an erasure whose cascade stands.

An approval keeps standing when `redact event` erases its proposal, and it carries the proposal's content.
For each approval that stands of the target, one notice goes to standard error, after the other notices, and before the sentence of an unfinished redaction:

```text
the approval 9 still carries the words of the proposal 6; redact event 9 to erase them too
```
`redact` refuses a redaction as a target and accepts every other action, a policy event and a `model_call` included.

`redact` works in this order: it records the redaction and sets the tombstones in one transaction, deletes the blobs that no longer have to lie, and brings every projection up to the tip of the log, the way `project` does.
Only then does it print the line to standard output.
The chronicle then holds no row of what was erased, without a separate `project`.
An ordinary catch-up prints nothing.
A catch-up that builds a projection for the first time, or rebuilds it because its version changed, prints the line `project` prints for that projection, on standard error:

```text
chronicle       rebuilt: version 2 -> 3, 12000 events, up_to_id 12000
```

Standard output carries the one line either way.
If deleting a blob or the catch-up fails, the redaction stays recorded, nothing goes to standard output, one sentence goes to standard error, and the exit code is 2:

```text
Error: the redaction is recorded as event 42, but it is not finished: blob 5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03 is not deleted from the store (the blob store at http://localhost:9000 is not reachable: EndpointConnectionError); run the same command again
Error: the redaction is recorded as event 42, but it is not finished: projection chronicle is not caught up (expected events 2.. above id 1, read [3, 4]; the tip is 4); run the same command again
```

The text in parentheses is the error that stopped it.
For `redact units`, the notice that the payload holds the wording of an erased unit, described below, can come before that sentence.
When several blobs are still to delete, the first form names them all, separated by a comma and a space, as `blobs <hashes> are not deleted from the store`.
`redact` attempts the catch-up whether or not the deletion failed.
When both fail, the sentence names the deletion first and then the catch-up, joined by `, and `, and ends in the same advice.
Once the cause is gone, running the same command again finds the target covered, prints `already redacted by event 42`, deletes what's left, and catches up.
The cause in the second example, a gap in the log, doesn't go away by itself, so until it does the same command fails with the same sentence; a server that didn't answer for a moment is a cause that does go away.

After the line on standard output come the notices.
For each unit it skips, one notice goes to standard error:

```text
unit 3 was already erased
```

`redact units` skips a unit that a redaction already covers, and names the remaining units in the redaction it writes.
For each blob of the target that stays in the store because another event still uses it, one notice goes to standard error, naming the blob and those events:

```text
blob 5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03 stays in the store: event 7 still uses it
blob 5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03 stays in the store: events 7, 9 still use it
```

When a string anywhere in the payload of the target, at any depth, contains the content of a unit `redact units` erases, one notice goes to standard error: last on success, and before the sentence of an unfinished redaction, whose exit code stays 2:

```text
the payload of event 7 is not erased and holds the wording of an erased unit; `previously redact event 7` erases it
```

`redact units` compares the content of the named units before it erases them, and compares the values of the payload, not its keys.
It compares with every line ending normalized to a line feed on both sides, the way `append` normalizes `--text` before it splits it, so a payload that keeps a text with CRLF or CR endings still counts.
A unit's whole content counts only where it stands in one string; a part of it, or a value that isn't a string, doesn't count.
A value `append` adds counts as well: a unit that reads `minutes.txt` matches the file name of an attachment of that name.
A unit already erased has no content left to compare, so a call on units that are all erased already prints no such notice.
An empty unit is never compared.

Seven refusals print one sentence to standard error, print nothing to standard output, write nothing, delete nothing, and return 2:

```text
Error: there is no event 9
Error: event 3 is a redaction, and a redaction cannot be redacted
Error: event 2 was written in hash format 1, which attests its units only together: use `previously redact event`
Error: event 4 names hash format 3, which is not known
Error: event 1 has no unit 7
Error: no event uses blob 5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03
Error: --reason must not be empty
```

The fourth refuses `redact units` on an event whose `hash_version` is neither 1 nor 2, which only a row this version didn't write can carry.
`--reason` counts as empty when it holds nothing but blanks.
A `HASH` that isn't 64 lowercase hexadecimal characters is an input error in the words `blob get` uses for it, refused before a setting is read or the database is asked.

## `log`

Prints the log in chain order, one line per event.

| Argument | Required | Default | Description |
|---|---|---|---|
| `--from` | No | `1` | The lowest event `id` to print. |
| `--limit` | No | `50` | The maximum number of events to print, at least 1. |

Each line holds four tab-separated fields, in this order: `id`, `occurred_at` (ISO 8601), `kind`, and the first 12 hexadecimal characters of `hash`.

A `--limit` below 1 is refused before anything is read: `log` returns 2 and prints one sentence naming `--limit` to standard error.

## `verify`

Checks the chain and reports every finding.
With `--anchors`, it also checks the log against anchor lines kept outside the database; see {ref}`external-anchor`.

| Argument | Required | Default | Description |
|---|---|---|---|
| `--anchors FILE` | No | — | A file of anchor lines to check against; `-` reads standard input. |
| `--exact` | No | Off | The tip of the log has to be the newest anchor; requires `--anchors`. |
| `--blobs` | No | Off | Also check every blob the blob register names against the blob store: read and open each blob that has to lie there, and ask after each that doesn't. |

An anchor line holds two fields separated by whitespace: an event `id`, a positive integer of at most 19 digits, and that event's `hash`, 64 hexadecimal characters.
`anchor` prints lines in this format.

The anchor lines come from the file named by `--anchors`, or from standard input for `-`.
Both sources are read the same way: as UTF-8 text, with or without a byte order mark, and with Unix or Windows line ends.
Blank lines and lines starting with `#` don't count.
Any other line that isn't an anchor line is an input error, named by its line number.
Input without a single anchor line, a file or standard input that can't be read, and input that isn't UTF-8 text are input errors as well.
`--exact` without `--anchors` is an input error, refused before the database is read.
On an input error, `verify` prints nothing to standard output, prints one sentence to standard error, and returns 2.

Every anchor is checked in the pass that checks the chain.
An anchor holds when the log contains it: the event at the anchor's `id` exists and carries the anchor's `hash`.
The same `id` may appear on several lines.
Lines that repeat the same `hash` for it count as one: they give at most one finding, however many there are.
Lines that carry different hashes for it are each compared with the event's `hash`, and each of those that doesn't match gives its own finding.
A missing event gives one finding for its `id`, however many lines name it.
With `--exact`, the log also must not continue past the newest anchor, the anchor with the highest `id`.

Each finding prints as one line: `FINDING <event_id>: <reason>`.
Nine findings come from the chain itself.
The seven in the block below can come from an event in either hash format; the last two rows of the table belong to one hash format each:

```text
FINDING 7: payload_hash does not match the payload
FINDING 7: units_hash does not match the units
FINDING 7: hash does not match the fields
FINDING 7: prev_hash does not match the predecessor
FINDING 1: first event has prev_hash, expected NULL
FINDING 0: event has 12 rows, 11 checked — the rest is unreachable
FINDING 7: payload not canonicalizable: $.amount: floating point number not allowed — state a scale as an integer
```

| Finding | Condition | Event |
|---|---|---|
| `payload_hash does not match the payload` | The payload isn't erased, and its digest computed in the event's hash format isn't `payload_hash`; in hash format 2 also when the payload has no salt. | The event. |
| `units_hash does not match the units` | In hash format 1, every unit carries content and the digest over their texts isn't `units_hash`; in hash format 2, a unit has no digest or the digest over the units' digests isn't `units_hash`. | The event. |
| `hash does not match the fields` | The event hash computed over the row's fields, the stored `payload_hash` and `units_hash`, and the source key isn't `hash`. | The event. |
| `prev_hash does not match the predecessor` | `prev_hash` isn't the `hash` of the event before it in the chain. | The event. |
| `first event has prev_hash, expected NULL` | The first event of the chain has a `prev_hash`. | The first event. |
| `event has <n> rows, <m> checked — the rest is unreachable` | The table holds more rows than the pass reached from `id` 1 on, such as a row with an `id` of 0 or below. | `0`, which is no chain position. |
| `payload not canonicalizable: <reason>` | The payload holds a value the canonical form refuses, so no digest can be computed. | The event. |
| `units not canonicalizable: <reason>` | In hash format 1, a unit holds a value the canonical form refuses. | The event. |
| `unit <seq> not canonicalizable: <reason>` | In hash format 2, the unit holds a value the canonical form refuses. | The event of the unit. |

The last two rows of the table are findings no row of this schema in a UTF-8 database can produce, since a unit's columns can't hold a value the canonical form refuses; they stay for a column or an encoding that changes later, and the block above doesn't show them.
A row in a hash format `verify` doesn't know is still checked for its linkage and its blob register, and none of its digests is computed; it gets the finding `hash_version <n> is not known` below.

Three findings come from the anchors:

```text
FINDING 42: hash does not match the anchor
FINDING 42: anchored event is missing (the log ends at 40)
FINDING 43: the log continues past the newest anchor (42)
```

The first two name the anchored `id`, the third names the tip.
`the log ends at` names the `id` of the last event in the log, and `0` for an empty log.
The number in parentheses in the third is the `id` of the newest anchor.

Ten findings come from the hash formats, from erasure and from the names of actions:

```text
FINDING 7: unit 2 does not match its digest
FINDING 7: hash_version 3 is not known
FINDING 7: payload is erased without a redaction
FINDING 7: unit 2 is erased without a redaction
FINDING 9: redaction of event 7 is not carried out
FINDING 9: redaction of unit 2 of event 7 is not carried out
FINDING 9: redaction names a target that does not exist
FINDING 7: units are erased in part, which version 1 cannot attest
FINDING 9: action has no valid form
FINDING 9: unknown action "teleport"
```

| Finding | Condition | Event |
|---|---|---|
| `unit <seq> does not match its digest` | A unit in hash format 2 carries content, and its digest isn't the one computed from that content with its salt, or its salt or digest is missing. | The event of the unit. |
| `hash_version <n> is not known` | The event names a hash format `verify` doesn't know; nothing else is computed for it. | The event. |
| `payload is erased without a redaction` | The payload is `NULL`, and no redaction of the event exists. | The event. |
| `unit <seq> is erased without a redaction` | The unit has no content, and no redaction names it or its event. | The event of the unit. |
| `redaction of event <id> is not carried out` | The event a redaction erased still carries its payload or the content of a unit. | The redaction. |
| `redaction of unit <seq> of event <id> is not carried out` | A unit a redaction erased still carries its content. | The redaction. |
| `redaction names a target that does not exist` | The event a redaction names doesn't stand before the redaction in the chain, or doesn't have a unit it names; for a redaction of a blob, an event it names doesn't stand before it or doesn't name the blob in the blob register. | The redaction. |
| `units are erased in part, which version 1 cannot attest` | An event in hash format 1 has some units without content, and others with it. | The event. |
| `action has no valid form` | An event of kind `action` carries no `action` name in its payload, or a redaction's payload doesn't have exactly the form `redact` writes. | The action. |
| `unknown action "<name>"` | An event of kind `action` carries an `action` name that isn't `redaction`, `policy`, `model_call` or `mcp_access`. | The action. |

Sixteen findings come from assertions, the events of the kind `assertion` ({ref}`assertions-reference`):

```text
FINDING 57: assertion has no valid form: the sources are empty: an assertion needs at least one source
FINDING 57: assertion has units
FINDING 57: assertion names a source that does not stand before it
FINDING 57: assertion has a subject that names no earlier obligation or decision
FINDING 57: assertion has a subject of another kind
FINDING 57: decision replaces no earlier decision
FINDING 57: approval names no open proposal of its subject
FINDING 57: approval of a proposal that is already approved or rejected
FINDING 57: approval does not take the content and the author of its proposal
FINDING 57: approval does not take the sources of its proposal
FINDING 57: rejection names no open proposal
FINDING 57: rejection of a proposal that is already approved or rejected
FINDING 57: rejection does not take the sources of its proposal
FINDING 57: assertion names a source that is not an observation
FINDING 57: assertion names a unit its source does not have
FINDING 57: assertion stands on an erased source
```

| Finding | Condition |
|---|---|
| `assertion has no valid form: <reason>` | The payload isn't the form of an obligation, a decision or a rejection; the reason is the first fault, such as the one in the block. An assertion with this finding gets no other. |
| `assertion has units` | The assertion has rows in `unit`; its statement belongs in the payload, which an erasure takes. |
| `assertion names a source that does not stand before it` | A source names the assertion itself or an event after it in the chain. |
| `assertion has a subject that names no earlier obligation or decision` | `subject` names no earlier first version of an entry; an erased earlier assertion counts as one, unless an approval named it under another subject. |
| `assertion has a subject of another kind` | `subject` names an obligation where the version is a decision, or the reverse. |
| `decision replaces no earlier decision` | `replaces` names neither an earlier decision nor an erased assertion. |
| `approval names no open proposal of its subject` | `approves` names no earlier proposal of the entry that `subject` names, and no erased assertion. |
| `approval of a proposal that is already approved or rejected` | An earlier approval or rejection answered the proposal. |
| `approval does not take the content and the author of its proposal` | The approval's obligation or decision, or its author, differs from that of the proposal it approves, while the proposal stands; the reason may differ. An approval with this finding doesn't get the next one. |
| `approval does not take the sources of its proposal` | The approval's sources differ from those of the proposal it approves, while the proposal stands. |
| `rejection names no open proposal` | `of` names no earlier proposal, and no erased assertion. |
| `rejection of a proposal that is already approved or rejected` | An earlier approval or rejection answered the proposal. |
| `rejection does not take the sources of its proposal` | The rejection's sources differ from those of the proposal it rejects. |
| `assertion names a source that is not an observation` | A source event doesn't exist, or its kind isn't `observation`. |
| `assertion names a unit its source does not have` | A cited unit isn't a unit of its source event. |
| `assertion stands on an erased source` | A redaction erased a source event, a cited unit, or, for a source cited whole, a unit of it after the assertion; the erasure didn't take the assertion along. |

Each stands under the assertion.

One finding comes from the blob register:

```text
FINDING 7: blob register does not match the payload
```

It stands under the event whose register rows differ from the hashes the event names.
For an event with a payload, `verify` compares the set of hashes under `blobs` in the payload with the set of rows in `event_blob`; a `blobs` that doesn't have the form `append` writes is the same finding.
For an erased payload, it compares the rows with `blobs` in the redaction of the event.

`verify` matches tombstones and redactions, and the register of an erased event, after it has read the whole chain, in the same snapshot.

With `--blobs`, `verify` reads `PREVIOUSLY_BLOB_IDENTITIES` and the five settings of the blob store, and after the snapshot it checks every blob the blob register names.
A blob that has to lie in the store is fetched, opened with the identity for the key the object names, and its content hashed against its address; the content isn't kept.
A blob that doesn't have to lie in the store is only asked for.
Four findings come from the blobs:

```text
FINDING 7: blob 5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03 is missing
FINDING 7: blob 5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03 does not match its address
FINDING 7: blob 5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03 cannot be opened
FINDING 7: blob 5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03 is erased and still present
```

| Finding | Condition |
|---|---|
| `blob <hex> is missing` | The blob has to lie in the store, and the store holds no object under its address. |
| `blob <hex> does not match its address` | The object opens, and the SHA-256 of its content isn't its address. |
| `blob <hex> cannot be opened` | The object names no key, the identity directory holds no identity for its key, or `age` refuses the object. |
| `blob <hex> is erased and still present` | Every reference to the blob is erased, and the store still holds an object under its address. |

Each stands under the smallest `id` of the events that name the blob.
`verify` reads the blob store after the snapshot of the chain, so a blob erased and deleted while it runs can appear as missing, and a blob still being deleted by a concurrent `redact`, or attached again after the snapshot, can appear as erased and still present; the next run doesn't report either.
`verify --blobs` checks only the blobs the blob register names, and reports nothing about an object in the store that no event names.
A blob store that doesn't answer or refuses, an identity file that exists and can't be read, an identity file whose content isn't an age identity, and a stream that breaks off aren't findings: `verify` prints one sentence to standard error and returns 2.
The findings of the chain and the anchors come before the blobs are checked, so they still go to standard output as `FINDING` lines beside that sentence; without one, standard output stays empty.

With no finding, `verify` prints a single line, which depends on the arguments:

| Arguments | Line |
|---|---|
| None | `chain intact` |
| `--anchors` | `chain intact, <n> anchors hold` |
| `--anchors` and `--exact` | `chain intact, <n> anchors hold, the tip is the newest anchor` |

`<n>` is the number of anchor lines in the file, and a count of one prints as `1 anchor holds`.
With `--blobs`, the line ends in `, <m> blobs match`, where `<m>` is the number of distinct blobs the blob register names, erased ones included; a count of one prints as `, 1 blob matches`.

Without anchors, one notice goes to standard error, and the exit code stays 0:

```text
no anchor given: verify attests that the log is unchanged, not that it is complete; see `previously anchor`
```

`verify` prints the notice only with no finding.

## `anchor`

Checks the chain and prints its tip as an anchor line.
It takes no arguments.

On an intact chain, `anchor` prints exactly one line to standard output: `<id> <hash>`, the `id` of the last event in the log and its `hash` as 64 lowercase hexadecimal characters.
The line describes the chain the same run checked.
With a finding, `anchor` prints the `FINDING` lines in the format `verify` uses to standard error, and nothing to standard output.
Unlike `verify`, `anchor` never prints a finding to standard output: its standard output holds an anchor line or nothing.

On an empty log, one notice goes to standard error, and nothing goes to standard output:

```text
the log is empty: nothing to anchor
```

## `show`

Prints one event with its units.

| Argument | Required | Default | Description |
|---|---|---|---|
| `event_id` | Yes | — | The event's `id`, as a positional argument. |

On success, `show` opens with three lines, in this order: `id=<id> kind=<kind>`—both on the one line—then `occurred_at=<ISO 8601>`, then `hash=<64 hexadecimal characters>`.
For an erased payload it then prints `payload=<erased by event <id>>`, naming the redaction that ordered the erasure, or `payload=<erased>` when no redaction did.
Otherwise it prints `evidence=<verbatim|recollection>` when the payload carries the key `evidence`, and then `payload=<JSON object, with sorted keys>`.
A redaction carries no `evidence`, so `show` prints no `evidence=` line for it.
It then prints one line per unit, in `seq` order: `  ¶<seq> <content>`, or for a unit without content `  ¶<seq> <erased by event <id>>`, or `  ¶<seq> <erased>` when no redaction covers it.
`content` keeps its tabs and line breaks, and prints every other control character as `\xNN`: the C0 controls, a carriage return among them, DEL, and the C1 controls from U+0080 to U+009F.
In the payload, JSON writes the C0 controls as escape sequences itself, and `show` writes DEL and the C1 controls as `\u007f` to `\u009f`, so the line stays JSON with the same value.
Last, it prints one line per reference in the payload's `blobs`, in their order: `  blob <sha256> <size> <media_type> <filename>`, with `-` for a reference without a file name.
A reference that a redaction erased ends in ` <erased by event <id>>`, naming the earliest redaction that erased it.
For an erased payload, the lines come from the redaction of the event instead, one per hash it names, as `  blob <sha256> <erased by event <id>>`; without a redaction, `show` prints no blob line.
`media_type` and `filename` are escaped the way `chronicle` escapes its fields.
`show` reads these lines from the log and doesn't ask the blob store, so it needs no blob setting.
Without an event at the given `event_id`, `show` prints `No event <event_id>` to standard error.

## `blob`

Fetches a stored blob, opens it, checks it against its address, and writes it to a file; see {ref}`blobs`.
It has one form:

```text
previously blob get HASH --output FILE
```

| Argument | Required | Default | Description |
|---|---|---|---|
| `HASH` | Yes | — | The blob's address, the SHA-256 of its content in 64 lowercase hexadecimal characters, as a positional argument. |
| `--output FILE` | Yes | — | The file to write the content to. |

`blob get` checks `HASH` before it reads a setting or asks the database, and refuses anything else as an input error:

```text
Error: 5891B5B522D5DF086D0FF0B110FBD9D21BB4FC7163AF34D08286A2E846F6BE03 is not a blob address: 64 hexadecimal characters, lower case
```

It asks the database first and reads no blob setting for the two answers below.
When no event names the blob, `blob get` returns 1 and prints one notice to standard error:

```text
no event uses blob 5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03
```

When every reference to the blob is erased, `blob get` returns 1, prints one notice to standard error that names the newest of the redactions that erased them, and writes nothing, whether or not the store still holds the object:

```text
blob 5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03 is erased (event 42)
```

Otherwise it reads `PREVIOUSLY_BLOB_IDENTITIES` and the five settings of the blob store, and writes the content to a temporary file in the directory of `--output`, and renames that file to `--output` only once the content matched its address.
The file is readable by its owner only.
An existing file at `--output` is replaced by the content, without a question.
On success it prints one line to standard output and never the content:

```text
wrote 6 bytes to hello.txt
```

Four errors of `blob get` print one sentence to standard error and return 2:

```text
Error: blob 5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03 is not in the store
Error: blob 5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03 cannot be opened: No matching keys found
Error: blob 5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03 does not match its address; nothing was written
Error: cannot write out/hello.txt: No such file or directory
```

After `cannot be opened:` stands the reason: the object names no key, no identity for its key is in the directory, or `age` refuses the object.
`cannot write` covers a directory of `--output` that doesn't exist or doesn't allow writing, an `--output` that's a directory, and a write that fails while the content passes through.
On every error, the temporary file is gone and an existing `--output` is unchanged.

## `project`

Brings every projection up to the tip of the log.
It takes no arguments.

`project` prints one line per projection, `chronicle` first and `source-stats` second.
Each line holds the projection's name padded to 15 characters, a space, and the outcome of the run.
There are four outcomes:

| Outcome | Condition |
|---|---|
| `built: <n> events, up_to_id <id>` | The projection had no state row, and the log held events to project. |
| `caught up: <n> events, up_to_id <id>` | The projection had a state row at the code's version, and the log had grown since. |
| `rebuilt: version <n> -> <m>, <k> events, up_to_id <id>` | The state row stood at version `<n>` and the code declares `<m>`, so the table was emptied and built again. |
| `up to date, up_to_id <id>` | No event was projected, and the version was unchanged. |

A count of one prints as `1 event`, every other count as `<n> events`.
`up to date` carries no count, and `up_to_id 0` means that nothing has been projected yet.

Two catch-ups of one projection, such as a `project` and the catch-up of a `redact`, take turns at the projection's state row, batch by batch; see {ref}`projections`.
A catch-up that finds the state row at another version than its own, or gone, between two of its batches stops with exit code 2 and one sentence on standard error:

```text
Error: projection chronicle was rebuilt while this catch-up ran: it stands at version 4, and this code declares version 3
Error: projection chronicle was rebuilt while this catch-up ran: it has no state row, and this code declares version 3
```

The first means that a catch-up of another version of the code ran against the same database and rebuilt the projection between two batches of this one.
The second means that the state row was deleted while this catch-up ran, as {ref}`rebuild-a-projection` does by hand to force a rebuild.
A catch-up rebuilds whenever the version it finds differs from its own, in either direction, so the next `project` of this release rebuilds the table back to its own version, and a `project` of the other release rebuilds it back again.
Inside `redact`, the same sentence stands in parentheses in the sentence of an unfinished redaction, whose advice to run the same command again holds once only one release runs against the database.
{ref}`rebuild-a-projection` says what to do.

## `chronicle`

Prints the chronicle in time order, one line per unit of an observation; the units of an action aren't in it ({ref}`projections`).

| Argument | Required | Default | Description |
|---|---|---|---|
| `--since` | No | — | An ISO 8601 timestamp with a UTC offset, as an inclusive lower bound on `occurred_at`. |
| `--until` | No | — | An ISO 8601 timestamp with a UTC offset, as an exclusive upper bound on `occurred_at`. |
| `--limit` | No | `50` | The maximum number of lines to print, at least 1. |

Each line holds six tab-separated fields, in this order: `event_id`, `seq`, `occurred_at` (ISO 8601), `source`, `external_id`, and `content`.
An event with no source attribution prints two empty fields in place of `source` and `external_id`.
Lines come out ordered by `occurred_at`, then `event_id`, then `seq`.

Four characters print as two characters each, in every field and not in `content` alone: a tab as `\t`, a newline as `\n`, a carriage return as `\r`, and a backslash as `\\`.
`source` and `external_id` carry whatever `append` was given, and a tab there would otherwise add a field and a newline would break the record in two.
Every other control character prints as `\xNN`: the C0 controls, DEL, and the C1 controls from U+0080 to U+009F, such as `\x1b` for the escape character.
The backslash is escaped first, so the escaping is reversible.
The stored values are unchanged; the escaping is part of the output format.

`--since` and `--until` form a half-open window, so a `--since` equal to or later than `--until` selects nothing.
Both need a UTC offset; without one, `chronicle` returns 2 and prints one sentence to standard error.
A `--limit` below 1 is refused the same way, before anything is read.

Two notices go to standard error, and both leave the exit code at 0.
The first prints when `--limit` cuts the output, the second when the projection stands behind the tip of the log, and a single run can print both in that order:

```text
output truncated at 50 lines; raise --limit or narrow --since/--until
projection is 12 events behind; run `previously project`
```

A lag of one event prints as `1 event behind`.
Standard output carries neither notice, and no notice at all means that the chronicle is current and the window is complete.

{ref}`projections` explains why `log` and `chronicle` are two commands.

## `stats`

Prints the per-source statistics, one line per source.
It takes no arguments.

Each line holds five tab-separated fields, in this order: `source`, `events`, `units`, `first_seen` (ISO 8601), and `last_seen` (ISO 8601).
`units` counts the units recorded, erased units included.
`source` is escaped the way `chronicle` escapes its fields, so a tab in a source name can't add a sixth field.
Lines come out ordered by `source`.
An event with no source attribution appears in no line.

`stats` reports the lag of `source-stats` on standard error, in the same sentence `chronicle` uses and with the same exit code 0.
The two commands report the lag of the projection each one reads, so after a rebuild of one of the two the numbers can differ.

## `policy`

Sets one statement of the processing policy, or prints the policy in force.
Every statement is an event of the kind `action` with `payload.action` set to `policy`, written with no source key and no units.
It has seven forms, and the five that write take the same three options:

```text
previously policy circle NAME --statement TEXT
previously policy member CIRCLE ADDRESS-OR-@DOMAIN --statement TEXT
previously policy own ADDRESS-OR-@DOMAIN --statement TEXT
previously policy rule SCOPE --regions REGION [REGION ...] --statement TEXT
previously policy provider NAME --storage [REGION ...] --retention-days N|unknown --operator NAME|unknown --training yes|no|unknown --subprocessors NAME [NAME ...]|none|unknown --statement TEXT
previously policy show [--at TIME]
previously policy gaps [--since TIME]
```

| Option | Required | Default | Description |
|---|---|---|---|
| `--statement TEXT` | Yes | — | The sentence the statement was set with. It stays in the log, and nothing evaluates it. An empty sentence or one of white space is refused. |
| `--revoke` | No | off | Lift the statement instead of setting it. The older event stays in the chain. |
| `--yes` | No | off | Write without asking. |

| Form | Key | Meaning |
|---|---|---|
| `circle` | `NAME` | A circle exists. |
| `member` | `CIRCLE` and `ADDRESS-OR-@DOMAIN` | An address, or a domain written `@domain.tld`, belongs to the circle. The domain is stored in lower case, and the local part as typed. |
| `own` | `ADDRESS-OR-@DOMAIN` | The operator's own identity. It doesn't count as a member of any circle. |
| `rule` | `SCOPE` | A scope gets conditions. `SCOPE` is `circle:<name>` or `source:<source>`. |
| `provider` | `NAME` | What a provider account promises. |

`rule` takes these further options:

| Option | Required | Default | Description |
|---|---|---|---|
| `--regions REGION ...` | Yes | — | `eu`, `us`, both, or `any`. `any` can't stand beside another region. |
| `--max-retention-days N` | No | no limit | A whole number of days. `0` means zero retention. |
| `--exclude-provider NAME` | No | none | A provider the scope never uses. May repeat. |
| `--no-training` | No | off | Only a provider declared not to train on its input passes. One that trains, or that says nothing about it, fails. |
| `--no-subprocessors` | No | off | Only a provider declared to have no subprocessors passes. |
| `--exclude-operator NAME` | No | none | An operator the scope never uses. A provider whose operator is unknown fails too. May repeat. |
| `--exclude-model-origin NAME` | No | none | A model origin the scope never uses. A provider whose origin is unknown fails too. May repeat. |

`provider` takes these further options:

| Option | Required | Default | Description |
|---|---|---|---|
| `--inference NAME=REGIONS` | No | none | A space of inference and what it means, such as `global=any` or `us=us`. May repeat. |
| `--storage [REGION ...]` | Yes | — | Where the provider stores. Given with no region, the provider stores nothing, as a local one does. |
| `--retention-days N\|unknown` | Yes | — | How long the provider keeps what it receives. |
| `--operator NAME\|unknown` | Yes | — | Who runs the service. |
| `--training yes\|no\|unknown` | Yes | — | Whether the provider trains on what it receives. |
| `--subprocessors NAME ...\|none\|unknown` | Yes | — | The others who handle the input. `none` and `unknown` stand alone, without a name beside them. |
| `--model-origin NAME\|unknown` | No | unknown | Where the model comes from. `unknown` is the same as leaving it out. |
| `--reports-geo` | No | off | The answer of the provider names the region. |
| `--local` | No | off | The provider runs on hardware the operator runs. |

A form that writes prints the statement as a JSON object, asks `write? [y/N]` and reads the answer from standard input.
`y` and `yes`, in any case, write the event and print `policy event ID`.
Any other answer writes nothing, prints `nothing written` to standard error and returns 1.
An input that ends before an answer, such as under `kubectl exec` without `-i`, does the same after one more line:

```text
no answer: the input ended before one came; --yes writes without asking
nothing written
```

`--yes` skips the question.

A statement the write path refuses is an input error: one sentence on standard error, return code 2, no question asked and nothing written.
These are refused:

- a membership in a circle that doesn't exist, as `Error: no circle "nowhere" exists — create it first with previously policy circle nowhere`;
- a scope of the form `project:<name>`, as `Error: scope "project:alpha" is not effective yet: project scopes arrive with the projects; use circle:<name> or source:<source>`;
- any other scope that isn't `circle:<name>` or `source:<source>`;
- `--regions` with no region, with `any` beside another region, or with a word that isn't a region;
- a negative number of days;
- an address or a domain that has no dot in its domain part;
- an empty statement.

`policy show` prints one table per kind, with a row ending in the id of the event that set it.
The rule rows end with the four restrictions on the processing chain, and the provider rows with the operator, the training, the subprocessors and the model origin, each `unknown` where nothing was declared.
The rules table starts with the built-in rule `local_only`, which isn't an event and can't be revoked: where no other rule applies, only a provider declared `local` is used.
`--at TIME` prints the policy as it stood at that moment, which is the log read up to it; the time needs a zone, as for `--occurred-at`.
A newer event with the same key replaces the older one, a revocation lifts the statement, and an event whose payload was erased counts for nothing.

`verify` reports a policy event whose form isn't sound, such as one that has no name, with a finding of the form `policy event has no valid form: it has no "name"`.
It reports a policy event that has units with `policy event has units`: the write path never gives one any.

`policy gaps` lists where the built-in rule `local_only` acted: the circles without a rule, and the sources whose content no rule covered at all, each with the number of calls that fell back and the time of the last, sorted by name, one per line, the three fields separated by a tab:

```text
circle:xz	3	2026-10-09T14:02:11.482113Z
source:email	1	2026-10-09T12:00:00.000000Z
```

It reads the `model_call` events, and the source of each event that a call read where the fallback named no circle, and counts a call whether the local model answered it or not.
`--since TIME` counts only the calls recorded from that moment on; the time needs a zone.
A call over an event that has no source and no circle stands under `event:<id>`.
It also counts what the MCP server withheld for lack of a rule, from the `mcp_access` events ({ref}`cli-access`): each entry of `withheld` with the reason code `no_rule` counts once for each circle it names under `uncovered`, the circles of the event that have no rule.
An entry that names none counts under `source:<source>` with the source it names, as the gate's lines do, or under `event:<id>` when it names no source either.
Those lines start with `mcp:`, so that every line keeps its three fields and the gate's lines stay as they were.
The gate's lines come first and the MCP lines after them, each group sorted by name:

```text
circle:xz	3	2026-10-09T14:11:11.482113Z
source:email	1	2026-10-09T12:00:00.000000Z
mcp:circle:h_da	2	2026-10-11T09:30:00.000000Z
```

When no call fell back, standard output stays empty, and one notice goes to standard error:

```text
no call fell back to local only
```

(cli-gate)=

## `gate`

Shows or runs one task over one event.
The one task is `mail_overview`: the language of a mail, its topic in one sentence, and the people its text names.
It has two forms:

```text
previously gate explain EVENT
previously gate try EVENT
```

`EVENT` is the `id` of an event in the log.
The caller names the event and never the model: the processing policy decides which model may see the content, and in which inference region.
The task names its models in this order, and the first one the policy lets through is the one called:

| Provider | Model | Effort |
|---|---|---|
| `anthropic` | `claude-haiku-5-5` | `low` |
| `mistral` | `mistral-small-2603` | — |
| `local` | `qwen3:4b` | — |

An event that doesn't exist is an input error, `Error: there is no event 9`, and nothing is written.

### `gate explain`

Prints the decision for the event, calls nothing and writes nothing.
One line per item, the fields separated by a tab: the circles of the people involved, the rules that applied with the event that set each, the merged regions, the retention limit, the excluded providers, every candidate with what became of it, and the decision with the inference region the call would set.
For the example of `previously policy`, with a rule `eu` for the circle and a rule `any` for `source:email`, the mail goes to Mistral:

```text
circles	xz
rules	circle:xz (event 8),source:email (event 9)
regions	eu
max retention days	-
excluded providers	-
candidate	anthropic/claude-haiku-5-5	rejected: anthropic/claude-haiku-5-5: the provider stores in ['us'], outside the allowed ['eu']
candidate	mistral/mistral-small-2603	chosen
candidate	local/qwen3:4b	not reached
decision	mistral/mistral-small-2603, inference_geo -
```

`-` stands for nothing: no inference region is set for a provider that declares a single one.
`local_only` stands in the rules line, without an event, where the built-in rule acted.
A reason that belongs to no candidate, such as `no local provider is declared`, stands on a line of its own with `-` in place of the candidate, and a decision that allows no candidate reads `decision	denied`.
An erased event is denied with the reason `the event is erased`.
An event that isn't an observation, such as a policy event, a redaction or a `model_call`, is denied with the reason `the event is not an observation`.
Where the built-in rule `local_only` acted and the decision chose the local model, `gate explain` writes the `processed locally` line of `gate try` to standard error, after the table; a denial gets no such line.

Where the decision allows no candidate and the provider of at least one has no declaration, `gate explain` writes one more line to standard error, after the table:

```text
undeclared: anthropic, mistral, local — the gate chooses among its own providers, each declared with previously policy provider NAME …, apart from the provider of an MCP client
only local: the built-in rule local_only acted, so only a provider declared with --local can be chosen — set a rule with previously policy rule SCOPE …, or declare one with previously policy provider NAME … --local
```

The first names those providers in the order of the candidates, each once, and stands where rules applied.
The gate calls only the providers its task names, and a provider declared for an MCP client, such as `claude-max`, is none of them.
The second stands where the built-in rule `local_only` acted, and names no provider: only one declared with `--local` can be chosen there, and whether a provider is local is what its declaration says.

### `gate try`

Runs the task over the event, and records the call as an event of the kind `action` with `payload.action` set to `model_call`, whatever became of it.
It reads four settings, described in {ref}`configuration-reference`: `ANTHROPIC_API_KEY`, `MISTRAL_API_KEY`, `PREVIOUSLY_LOCAL_MODEL_URL` and `PREVIOUSLY_PRICES`.
A missing key or address is no error by itself: only the adapter of that provider is missing, and the call fails only when the policy chooses that provider.

On standard output it prints the answer as one line of JSON, and then the `id` of the `model_call`:

```text
{"language": "de", "participants": ["Eva Huber"], "topic": "An offer for the relaunch"}
model_call: event 12
```

A call that didn't end with an answer prints only the second line, and one sentence on standard error, with exit code 2.
So does a call whose input was erased while the provider was answering: it's recorded as `ok`, but its answer is erased with the input in the same transaction ({ref}`erasure`), so it isn't printed either, and the sentence names the redaction:

```text
erased: the input was erased by redaction 14 while the call ran; the answer is erased with it
```

Every outcome but `ok` is recorded the same way, with no units: a denial, a refusal by the model, an answer the schema refuses, and a call that failed.
A denial and a refusal by the model read:

```text
denied: the event is erased
refused: anthropic/claude-haiku-5-5 declined the task
```

A denial names every reason, joined by `; `, such as `no local provider is declared; anthropic/claude-haiku-5-5: the provider anthropic is not local, and only local applies`.

`gate try` writes these lines to standard error as well:

```text
processed locally: no rule for circle:xz — set one with previously policy rule circle:xz …
alarm: inference_geo requested us, reported global
schema_invalid: the answer of anthropic/claude-haiku-5-5 does not match the schema of mail_overview
Error: anthropic: the provider is not configured — set ANTHROPIC_API_KEY
Error: local: call failed (APIConnectionError): Connection error. — the local model server is http://localhost:11434/v1
undeclared: local — the gate chooses among its own providers, each declared with previously policy provider NAME …, apart from the provider of an MCP client
```

The first comes before everything else, one line per circle without a rule, or for the source when no rule applied at all; under a real rule there's no such line.
It's written only where the local model answered: a call denied because no local provider is declared, and a call to a local server that didn't answer, processed nothing, and print their own sentence alone.
The second is an alarm: the provider reported another inference region than the one requested, and the call returns 3.
The third is an answer that isn't JSON, lacks a field, or has a field too many; the gate checks every answer itself, even where the provider enforces the schema.
The fourth names the setting that's missing, and the fifth the address of the local model server that didn't answer.
The sixth follows a denial where the provider of a candidate has no declaration, as for `gate explain`, and reads `only local: …` where `local_only` acted.
A call that failed prints the sentence of the client, after the provider and the class of the error, and never the key.
What the provider said doesn't go into the event: the event names the provider, the class of the error and the HTTP status.

`verify` holds every `model_call` to its form: an outcome it knows, units exactly when the outcome is `ok`, and a list `inputs` whose every entry names an event.
Each break of that form is a finding:

```text
FINDING 12: model_call has no valid form: it has no outcome
FINDING 12: model_call has no valid form: it has the unknown outcome "teleported"
FINDING 12: model_call has no valid form: it is ok and has no units
FINDING 12: model_call has no valid form: it is denied and has units
FINDING 12: model_call has no valid form: it has no list "inputs"
FINDING 12: model_call has no valid form: it has an "inputs" entry without an event
```

## `client`

Adds, revokes or lists the MCP clients.
A client is a name, a declared provider whose promise its reading is processed under, and a token.
It's stored as a policy event of the kind `client` ({ref}`policy-and-model-calls`), and holds only the SHA-256 of the token.

```text
previously client add NAME --processor PROVIDER --statement TEXT [--yes]
previously client revoke NAME --statement TEXT [--yes]
previously client list
```

| Option | Required | Default | Description |
|---|---|---|---|
| `--processor PROVIDER` | Yes, for `add` | — | The name of a provider declared with `policy provider`. |
| `--statement TEXT` | Yes, for `add` and `revoke` | — | The sentence the statement was set with. It stays in the log. |
| `--yes` | No | off | Write without asking. |

`add` prints a summary of two fields on standard output, `client NAME` and `processor PROVIDER`, separated by a tab.
It then asks `write? [y/N]` the way `policy` does, and after the write prints the token on standard output in two lines:

```text
client NAME: token TOKEN
shown once; store it now
```

The token is 32 random bytes, encoded as base64url.
Those two lines are the only place it ever appears: not in the log, not in `client list`, not in an error, not in `policy show`.
Nothing can bring it back, so a lost token means adding the client again.

`add` for a name that already belongs to a client replaces it: a new token is made, and the old one stops matching from the next lookup.
It says `client NAME exists: this replaces it, and its token stops working` on standard error before the question.
`revoke` lifts the client, and its token matches nothing from then on.
`revoke` prints `policy event ID`, and `add` prints nothing after the two lines.

`list` prints one line per client in force, sorted by name, the three fields separated by a tab: the name, the processor and the time of the event that set it.
It never prints the hash.
With no client it prints `no client exists` to standard error.

An undeclared processor is refused before the question, as `Error: the processor "NAME" is not declared — declare it first with previously policy provider NAME`.
Revoking a client that doesn't exist is refused as `Error: no client "NAME" exists`.

(cli-access)=

## `access`

Shows what the MCP clients saw.
Every call of a client, whether a tool, a resource or a prompt, is written to the log as an action `mcp_access`, with no source key and no units.
Its payload holds ids, names, the circles of each delivered or withheld event as the policy named them at the time of the call, reason codes, the sentences that say why something was withheld, and the arguments of the call, which are the client's input; it holds nothing of any event.
`access` reads those events:

```text
previously access [--client NAME] [--circle NAME] [--since TIME]
```

| Option | Required | Default | Description |
|---|---|---|---|
| `--client NAME` | No | all clients | Only the calls of this client. |
| `--circle NAME` | No | all circles | Only the calls that named this circle in their arguments, or delivered or withheld an event of it. |
| `--since TIME` | No | all time | Only the calls recorded from that moment on (ISO 8601, with a zone). |

It prints one line per call, in the order of the chain, the six fields separated by a tab: the time, the client, the kind and the name of the call joined by a colon, the outcome (`ok` or `error`), the delivered events, and the withheld ones.
The delivered events are ids separated by commas, the withheld ones `ID:REASON_CODE:REASON` separated by spaces, and a dash stands for none:

```text
2026-10-11T12:00:00.000000Z	claude-code	tool:previously	ok	delivered 42,44	withheld 43:no_rule:circle h_da has no rule, so only local processing is allowed; this client (claude-code) processes with claude-max, which is not local
```

The reason code is `no_rule` where a circle of the event had no rule for the client, and `rule` where a rule said no.
An entry that was erased, or whose form `verify` reports, is left out.
When no call matches, standard output stays empty, and one notice goes to standard error:

```text
no access matches
```

`verify` holds every `mcp_access` to its form: known fields only, at every level, a client, a policy, a call with a known kind (`tool`, `resource` or `prompt`), a name and arguments, lists `delivered` and `withheld` whose every entry is an object with exactly its fields, an event, and its circles as a list of names (and its units as a list of numbers), a known reason code on every withheld entry, an outcome of `ok` or `error`, and no units.
A break of that form is a finding of the form `FINDING 12: mcp_access has no valid form: it has no outcome`, and an `mcp_access` with units is `FINDING 12: mcp_access has units`.

## Assertions

`assert`, `approve`, `reject`, `obligations`, `obligation`, `decisions` and `decision` write and read assertions: obligations and decisions, each with the events it rests on and who stands for it.
An obligation or a decision is named after the event of its first version, and `ID` below is that number.
Every later version says everything that holds after it and carries the name in `subject`; the newest direct version stands, and a direct version beats an open one.
The command line is the operator's tool, so it writes `human:operator` as the author and `direct` as the responsibility, and it checks no policy.

### `assert`

```text
previously assert obligation --debtor REF --creditor REF --what TEXT [--due DATE] [--state STATE] [--subject ID] [--reason TEXT] --source SOURCE [--source SOURCE ...] [--yes]
previously assert decision --what TEXT --by REF [--by REF ...] --on DATE [--state STATE] [--replaces ID] [--subject ID] [--reason TEXT] --source SOURCE [--source SOURCE ...] [--yes]
```

| Option | Required | Default | Description |
|---|---|---|---|
| `--debtor REF`, `--creditor REF` | Yes, without `--subject` | — | A reference: `own`, `circle:NAME`, `address:ADDRESS` or `name:TEXT`. |
| `--by REF` | Yes, without `--subject` | — | Who decided, a reference. May repeat. |
| `--what TEXT` | Yes, without `--subject` | — | The text of the obligation or the decision. |
| `--due DATE` | No | none | By when, written `YYYY-MM-DD`, or `none` to clear the date of the version that stands. A date in the past is allowed, and the obligation is overdue at once. |
| `--on DATE` | Yes, without `--subject` | — | When it was decided, written `YYYY-MM-DD`. |
| `--state STATE` | No | `open`, or `valid` | One of `open`, `fulfilled`, `cancelled` for an obligation, `valid` or `revoked` for a decision. |
| `--replaces ID` | No | none | The decision this one replaces, or `none` to clear it on the version that stands. |
| `--subject ID` | No | none | The obligation or decision to write a further version of. |
| `--reason TEXT` | No | none | Why this version, for the history. |
| `--source SOURCE` | Yes, without `--subject` | — | An event it rests on: `EVENT` for the whole event, or `EVENT:SEQ,SEQ` for units of it, in ascending order. May repeat. |
| `--yes` | No | off | Write without asking. |

With `--subject`, every option left out takes its value from the version that stands, a proposal included, and the new version is direct.
`--reason` is never taken over.
Without `--subject`, a missing option is refused as `Error: an obligation needs --creditor, --what and --source unless --subject names the one to change`, and `a decision` for a decision.

The command shows the payload as `policy` does, indented, with sorted keys.
With `--subject`, one line per field that differs from the version that stands follows, with four tab-separated fields: `change`, the field, the old value and the new one.
It then asks `write? [y/N]`, and after the write prints `assertion ID` for the event written.

A `name:` reference is a label and not an identity.
When a source of the version shows an address whose display name contains the text of a `name:` reference, ignoring case, one notice per address goes to standard error before the question, and the command goes on:

```text
hint: anna@huber.example appears in the sources; address: is a reference that holds
```

The input is checked before the question, and when it fails nothing is written:

```text
Error: --due is not a date written YYYY-MM-DD
Error: --on is not a date written YYYY-MM-DD
Error: --source is not EVENT or EVENT:SEQ,SEQ: 'abc'
Error: --subject 5 names no obligation that stands
```

A reference without a known prefix is refused as `Error: --debtor: the reference has no known prefix: use own, circle:, address: or name:`, and the other form errors of an assertion come from its checks.
What only the log knows is checked before the question as well, with the sentence of the write path: a source that isn't an event, isn't an observation or is erased, a unit that doesn't exist or is erased, and a `--subject`, `--replaces` or proposal that names nothing that stands.
So is a text the log can't hold, such as one with a lone UTF-16 surrogate, which the write path would refuse with `a statement cannot be written:` and the path of the field.
The write path checks again under its locks, so a refusal can still follow the question when an erasure comes in between.

### `approve` and `reject`

```text
previously approve ID [ID ...] [--reason TEXT] [--yes]
previously reject ID [--reason TEXT] [--yes]
```

`approve` makes proposals the operator's own.
Each becomes a direct version of the same obligation or decision, with the content, the sources and the author of the proposal, and `approves` naming it.
The reason of the proposal stays unless `--reason` gives another.
An id named twice is approved once.
`reject` writes a rejection with the sources of the proposal.
Both show one payload per statement, with DEL and the C1 control characters written as `\u00NN`.
They then ask, and print `assertion ID` for each event written.

A proposal that can't be answered is refused before the question, with exit code 2:

```text
Error: event 99 is no proposal that stands
Error: the version 6 is no proposal: it is direct
Error: the proposal 3 is already approved
Error: the proposal 4 is already rejected
Error: the proposal 5 is overtaken: the direct version 7 came after it
```

`approve` takes only a proposal that's pending, or that stands because no direct version exists.
A proposal that a direct version came after was made against what stood before that version, and approving it would put its older content back over the newer one; `reject` still takes it.
The batch is checked as it will stand once written, so a call that approves two proposals of one entry is refused at the second one: the approval of the first is a direct version that came after it.

### `obligations` and `decisions`

```text
previously obligations [--circle NAME] [--owed-by REF] [--owed-to REF] [--state STATE] [--overdue] [--proposals]
previously decisions [--circle NAME] [--state STATE] [--proposals]
```

| Option | Description |
|---|---|
| `--circle NAME` | Only entries that concern the circle: by the circles of their sources, by a `circle:` party, or by the circles of an `address:` party, as the policy in force names them. |
| `--owed-by REF`, `--owed-to REF` | Only this debtor or creditor. A `name:` reference is searched in the text of a name, ignoring case; any other must be equal. |
| `--state STATE` | Only this state of the version that stands. |
| `--overdue` | Only obligations that are open and due before today, the UTC date. |
| `--proposals` | Only entries with a proposal pending, or that stand as a proposal because no direct version exists. |

Without `--proposals`, only entries with a direct version appear, and a proposal never passes for one that stands.
Each line holds seven tab-separated fields, ordered by id:

1. The id.
2. The state, with `proposed` in front when the entry stands as a proposal, `overdue` behind an open obligation past its date, and `replaced by ID` behind a decision that a standing decision replaces.
3. The due date of an obligation or the day of a decision, or `-` for no date.
4. `DEBTOR -> CREDITOR`, or the deciders separated by a comma and a space.
5. The text.
6. `N versions`, the versions that stand, proposals and rejected ones included.
7. `K proposals`, the open proposals that are pending.

Every field that comes from outside is escaped as `chronicle` escapes its fields.
The words are singular for one: `1 version`, `1 proposal`.

### `obligation` and `decision`

```text
previously obligation ID [--history]
previously decision ID [--history]
```

Prints the version that stands as lines of a name, a tab and a value: `version` with the id of that version, `state`, `overdue` with `yes` only for an overdue obligation, `replaced by` only for a replaced decision, then `due`, `debtor`, `creditor` and `what`, or `on`, `by`, `what` and `replaces`, then `sources`, `reason`, `author`, `responsibility`, `versions` and `proposals`.
The first line is `obligation ID` or `decision ID`, with `(proposal)` behind it when the version that stands is a proposal.
A value that isn't set reads `(none)`.
Each pending proposal adds one line per field it changes, with six tab-separated fields: `proposal`, its id, its author, the field, the old value and the new one, or a line of three fields when it changes nothing.

`--history` prints instead the first line `obligation ID: N versions`, or `1 version`, and then, in chain order, each version and each rejection.
A version is a line `version`, its id, the time, the responsibility, the author, and when it applies `rejected`, `approved` or `approves ID`, then `sources` and `reason`.
The first version adds a `set` line per field; each later one adds a `change` line per field that differs from the version before it, with the old and the new value.
A rejection is a line `rejection`, its id, the time, its author and `rejects ID`, then `reason`.

`--history` also answers for an entry whose versions are all rejected proposals.
When no obligation or decision of that kind stands under the id, or none of its versions wins and `--history` is absent, the command prints `no obligation stands under event ID` to standard error, with `decision` for a decision, and returns 1.
When no entry stands under the id and the id names an assertion an erasure took, the command prints `assertion ID is erased` to standard error instead, with or without `--history`, and returns 1.
That's the answer for an entry whose versions are all erased, and for any other erased version too: the erasure took the payload that said which kind and which entry it was.

(cli-mcp)=

## `mcp`

Serves MCP over standard input and standard output, for the client that `PREVIOUSLY_MCP_CLIENT` names:

```shell
PREVIOUSLY_MCP_CLIENT=claude-code previously mcp
```

`mcp` takes no options.
Over standard input there is no token: whoever starts the process is the client.
Before it reads a request, `mcp` checks that the variable names a client in force, and otherwise returns 2 with one of two sentences:

```text
Error: PREVIOUSLY_MCP_CLIENT is not set: name the client this process serves
Error: no client "claude-code" is in force; add it with previously client add
```

Every call reads the policy again.
A client revoked while the process runs gets an error from its next call on, and the access log records that call with the outcome `error`.
Standard output carries the protocol and nothing else, and the process ends when standard input closes.
The tools, resources and prompts are the same as over HTTP; every call writes an `mcp_access`, which {ref}`cli-access` reads.
The writing tools write only when `PREVIOUSLY_MCP_CONFIRM_KEY` holds at least 32 characters ({ref}`configuration-reference`); otherwise they answer with an error, and `mcp` starts all the same.

(cli-serve)=

## `serve`

Serves MCP over HTTP under the path `/mcp`, with answers as JSON and without a session.
A client of the protocol revision `2026-07-28` and one of an earlier revision are served at the same address.
`serve` takes no options, and reads `PREVIOUSLY_MCP_ADDRESS`, `PREVIOUSLY_MCP_ALLOWED_HOSTS` and, for the writing tools as `mcp` does, `PREVIOUSLY_MCP_CONFIRM_KEY` ({ref}`configuration-reference`).
On start it prints one line to standard error, and then runs until it's stopped:

```text
serving MCP over HTTP on http://127.0.0.1:8765/mcp
```

An address outside {ref}`the address form <address-form>`, and a `PREVIOUSLY_MCP_HOST` without the address that took its place, are refused before anything connects, with exit code 2:

```text
Error: PREVIOUSLY_MCP_ADDRESS is not host:port, with an IPv6 host in brackets: 'tcp://10.43.0.5:8765'
Error: PREVIOUSLY_MCP_HOST is not read any more: set PREVIOUSLY_MCP_ADDRESS to host:port
```

`serve` doesn't read `PREVIOUSLY_MCP_PORT`, which Kubernetes sets in every pod of a namespace with a Service named `previously-mcp`.

Every request but the readiness probe below needs the header `Authorization: Bearer TOKEN`, with the token that `client add` printed for a client in force.
The token is checked against the policy at every request, so a token that a later `client add` for the same name replaced, or that `client revoke` lifted, stops working with the next request.
A header that names a client is no identity: only the token says which client asks.
A request without a valid token gets the status 401, the header `WWW-Authenticate: Bearer`, and one sentence as its body:

```text
Error: a valid bearer token is required
```

No `mcp_access` is written for such a request, since no client is known.
The server publishes no Protected Resource Metadata: `/.well-known/oauth-protected-resource` answers 404 to a request with a valid token, and 401 without one, like every other path but the readiness probe.

`GET /healthz` is the readiness probe, and it needs no token.
It runs one trivial query against the database and answers with the status 200 and the body `ok`, or, when the database doesn't answer, with the status 503 and this body:

```text
Error: the database does not answer
```

It reaches no MCP, returns no data and writes no `mcp_access`.
Only `GET` on exactly that path passes without a token: another method, or another path such as `/healthz/`, gets the 401 above.

The `Host` header of a request has to name `127.0.0.1`, `localhost`, `[::1]` or a name in `PREVIOUSLY_MCP_ALLOWED_HOSTS`, with any port, or the request gets the status 421.
An `Origin` header has to name one of those hosts too, with `http` or `https`, or the request gets the status 403.
Both checks are the protection of the MCP SDK against DNS rebinding.
The readiness probe is answered before them, whatever the two headers name, since it shows nothing.
