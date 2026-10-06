(cli-reference)=

# Command line

`previously` is the command-line entry point.
It has twelve subcommands: `migrate`, `append`, `ingest`, `redact`, `log`, `verify`, `anchor`, `show`, `blob`, `project`, `chronicle`, and `stats`.
Every subcommand reads the database connection string from `PREVIOUSLY_DSN`; see {ref}`configuration-reference`.
`append --attach`, `ingest imap`, `blob get` and `verify --blobs` also read the blob settings, and `redact` reads them when it has a blob to delete; no other subcommand reads any of them.
`ingest imap` alone reads the five `PREVIOUSLY_IMAP_*` settings.
A missing setting is an input error that names the first variable missing, in the form `Error: PREVIOUSLY_BLOB_BUCKET is not set`.
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
| `ingest` | The run went through, with or without variants. | Not used. | A setting is missing or invalid, the IMAP server couldn't be reached, refused a step or broke the connection off, or storage or the blob store raised an error. |
| `redact` | The redaction was recorded and carried out, or the target was already covered by one, every blob it made obsolete is gone from the blob store, and every projection stands at the tip of the log. | Not used. | The input was invalid, the redaction was refused, storage raised an error, or after the redaction was recorded a blob couldn't be deleted or the projections couldn't be caught up. |
| `log` | The log was printed. | Not used. | The input was invalid, or storage raised an error. |
| `verify` | The chain has no finding, every anchor holds, and with `--blobs` no blob has a finding. | The chain, an anchor or, with `--blobs`, a blob has at least one finding. | The input was invalid, a blob setting is missing or invalid, an identity file can't be read, or storage or the blob store raised an error. |
| `anchor` | The anchor line was printed, or the log is empty. | The chain has at least one finding. | Storage raised an error. |
| `show` | The event was printed. | No event exists at the given `event_id`. | The input was invalid, or storage raised an error. |
| `blob` | The blob was written to the file. | No event names the blob, or the blob is erased. | The input was invalid, a blob setting is missing or invalid, the blob is missing from the store, can't be opened or doesn't match its address, the file can't be written, or storage or the blob store raised an error. |
| `project` | Every projection stands at the tip of the log. | Not used. | Storage raised an error, the worker found a gap in the log, or a catch-up at another version rebuilt a projection while this one ran. |
| `chronicle` | The chronicle was printed, even when the window holds no row. | Not used. | The input was invalid, or storage raised an error. |
| `stats` | The statistics were printed, even when no source has an event. | Not used. | Storage raised an error. |

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

Takes in the mail an IMAP folder holds above the watermark of the last run; see {ref}`artifact-identity`.
It has one form, and takes no arguments:

```text
previously ingest imap
```

`ingest imap` reads the five `PREVIOUSLY_IMAP_*` settings, `PREVIOUSLY_BLOB_RECIPIENT`, `PREVIOUSLY_DSN` and the five settings of the blob store, in that order; see {ref}`configuration-reference`.
It doesn't read `PREVIOUSLY_BLOB_IDENTITIES`.
It reads every setting and checks the recipient before it connects to anything, and a missing one is an input error in the form `Error: PREVIOUSLY_IMAP_PASSWORD is not set`.
A port that isn't a number from 1 to 65535 is refused the same way:

```text
Error: PREVIOUSLY_IMAP_PORT is not a port number: 'imaps'
```

`ingest imap` connects over TLS only, and verifies the server's certificate and host name against the trust store of the system; no setting turns that off.
OpenSSL reads a certificate file named in `SSL_CERT_FILE` in place of the system's file, and that's how a certificate outside the trust store is trusted.
A socket operation that waits longer than 60 seconds ends the run.
It opens the folder read-only and reads every mail with `BODY.PEEK[]`, so no mail is marked as read and nothing in the folder changes.

The watermark belongs to `imap:<user>@<host>/<folder>`, with the host as `PREVIOUSLY_IMAP_HOST` spells it and without the port.
Its position is the folder's `UIDVALIDITY` and the UID of the last mail taken in.
The run fetches the mails above that UID, oldest first and one at a time, maps each onto its events, stores the raw mail and every attachment as a blob, and appends the events in batches; after each batch, it moves the watermark to the last mail the batch covered.
A folder with another `UIDVALIDITY` than the watermark's, such as one deleted and created again, is read from the start, and so is a folder under another name or host; a mail whose events are in the log already counts as known.
A mail that leaves the folder while the run fetches is passed over.

`ingest imap` prints one line to standard output:

```text
imap: 5 appended, 0 known, 0 variants, up to uid 4
```

The counts are of events, not of mails: a mail with a mail attached is two events.
`appended` counts the variants as well.
`up to uid` is the UID the watermark stands at, and `up to uid 0` means that the folder hasn't given a mail yet.

For each variant, one notice goes to standard error, with the Message-ID the variant deviates from and the `id` of its event:

```text
variant of 20261005101500.4711@example.net: event 6
```

`ingest` doesn't catch the projections up; `previously project` does, and may run beside it.

Errors of the IMAP server and of the connection print one sentence to standard error and return 2:

```text
Error: cannot connect to the IMAP server mail.example.org:993: Connection refused
Error: the certificate of the IMAP server mail.example.org:993 does not verify: self-signed certificate
Error: the IMAP server mail.example.org:993 refused the login of pilot
Error: the login of pilot at the IMAP server mail.example.org:993 holds a character other than ASCII, which the IMAP login cannot carry
Error: the IMAP server mail.example.org:993 refused to open the folder 'Kunde Müller' of pilot: EXAMINE failed. No such mailbox
Error: the connection to the IMAP server mail.example.org:993 broke off
Error: the connection to the IMAP server mail.example.org:993 broke off: The read operation timed out
```

No message names the password.
A refused login quotes nothing of the server's answer, and a connection that broke off quotes the reason of the system, never what the server sent, which can be mail.
A refusal to open the folder quotes the server's reason.
On every error, the watermark stands where the last appended batch left it, and the next run fetches the rest again; a blob stored for a batch that wasn't appended stays in the store, and that run finds it there.

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

`redact` works in this order: it records the redaction and sets the tombstones in one transaction, deletes the blobs that no longer have to lie, and brings every projection up to the tip of the log, the way `project` does.
Only then does it print the line to standard output.
The chronicle then holds no row of what was erased, without a separate `project`.
An ordinary catch-up prints nothing.
A catch-up that builds a projection for the first time, or rebuilds it because its version changed, prints the line `project` prints for that projection, on standard error:

```text
chronicle       rebuilt: version 1 -> 2, 12000 events, up_to_id 12000
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

Nine findings come from the hash formats and from erasure:

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
Error: projection chronicle was rebuilt while this catch-up ran: it stands at version 3, and this code declares version 2
Error: projection chronicle was rebuilt while this catch-up ran: it has no state row, and this code declares version 2
```

The first means that a catch-up of another version of the code ran against the same database and rebuilt the projection between two batches of this one.
The second means that the state row was deleted while this catch-up ran, as {ref}`rebuild-a-projection` does by hand to force a rebuild.
A catch-up rebuilds whenever the version it finds differs from its own, in either direction, so the next `project` of this release rebuilds the table back to its own version, and a `project` of the other release rebuilds it back again.
Inside `redact`, the same sentence stands in parentheses in the sentence of an unfinished redaction, whose advice to run the same command again holds once only one release runs against the database.
{ref}`rebuild-a-projection` says what to do.

## `chronicle`

Prints the chronicle in time order, one line per unit.

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
