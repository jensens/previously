(blobs)=

# About blobs

An event can carry more than text: a scanned letter, a recording, a spreadsheet somebody attached to a mail.
Previously keeps such a content as a blob, outside the database, in an S3 bucket, and seals it before it leaves the process.
This page explains how a blob is addressed, why the store only ever sees ciphertext, why the format is `age`, and what "first wins" does and doesn't promise.
It then explains how a blob comes to an event, and why the log names it twice, once in the payload and once in a register.

## The address is the hash of the content

A blob lies under the SHA-256 of its plaintext, written as 64 lower-case hexadecimal characters.
That hash is its address in the store and its name in the log.

Two things follow from addressing by content, and both are the reason for it.
The same content is one object, however often it arrives: the same attachment on five mails is stored once.
And a log that names the address names *which bytes* are meant, not merely where some bytes were put.
A name chosen by the writer, a counter or a random identifier, would say where to look and nothing about what should be found there.

The address has a cost that shapes the whole writing path.
It has to be known before the upload, so the writer reads the content twice: once to hash it, and once more to seal it.
A source that can only be read once, such as a pipe, doesn't fit; a file does.

## The store sees only ciphertext

Every blob is sealed before it's uploaded, and opened after it's fetched, and both happen in `core`.
The store gets ciphertext and gives back ciphertext; nothing behind the store's protocol ever holds a plaintext or a key that opens one.
`.importlinter` holds that line: only `core.sealing` may import the library that seals, and {ref}`module-boundaries` gives the reason for each side.

What that's worth is easiest to say from the side of a thief.
Whoever gets hold of the bucket's credentials, or of the bucket itself, or of a backup of it, gets files that open to nothing without the identity that belongs to them.
The provider of the store never sees a key.
That isn't a promise about the provider's honesty; it's the absence of anything for the provider to be honest about.

The address isn't protected the same way: `age` doesn't bind a ciphertext to the name it lies under.
So the reader hashes the plaintext as it comes out of the opening, and compares the result with the address at the end.
A ciphertext put under a foreign address, by mistake or on purpose, opens and then fails that comparison.
The comparison comes at the end, so the plaintext has already passed into the caller's sink by then; whoever fetches into a file writes into a temporary one and renames it only once the fetch has returned.
A fetch whose writing failed doesn't return, and so nothing is renamed.
That doesn't rest on the sealing library: measured on 2026-10-05, `pyrage` returned as though it had sealed when the one write of a 12-byte content failed, so sealing and opening watch every read and write themselves.

## Why `age` and not a custom scheme

The architecture first named AES-GCM, with the nonce in a header of the object.
Three properties of the `age` file format replaced it.

`age` is a standard format with a specification and several independent implementations.
A custom scheme, even one built from sound primitives, would be security-critical code that only this project reviews, in a format only this project reads.

`age` seals and opens a piece at a time, so the memory a blob costs doesn't grow with the blob.
AES-GCM in one piece holds the whole blob in memory at once, and a chunked AES-GCM is exactly the custom scheme that the previous paragraph rules out.

And `age` can be opened in an emergency without this software.
The `age` command-line tool and the identity are enough to read any blob in the bucket.
That turns a recovery that depends on Previously still running into one that depends on a widely packaged tool and one line of text.
That emergency path isn't measured yet: on 2026-10-05 neither `age` nor `rage` was installed on the machine the measurements on this page come from.
It's also why the dependency on the Python binding, `pyrage`, is judged by the format rather than by the binding: should the binding be orphaned, every other `age` implementation still reads the blobs.

## Why there is no size limit

Sealing goes into a temporary file, the upload goes out of it in parts, and the opening reads the fetched stream a piece at a time and writes into the caller's sink.
At no point does the whole content sit in memory.

Measured on 2026-10-05 with `measure_rustfs.py`, the whole path against RustFS 1.0.1 in a container, each size in a fresh process: seal into a temporary file, upload, fetch, open from the stream while hashing.
The peak memory of the process was 85 MiB at 16 MiB, 183 MiB at 256 MiB, and 183 MiB at 1 GiB.
That's a base plus the buffers of the upload in parts, and no function of the size.
A blob of 1 GiB took 1.04 s to seal, 2.58 s to upload and 2.66 s to fetch and open, and the address matched every time.
The sealed form was 262,406 bytes larger than the content, the per-chunk overhead of `age`.

The price is disk space, not memory: the temporary file is as large as the blob while it's being stored.
Whoever takes in attachments needs room for the largest one.
The test suite holds the memory bound as a test, `test_memory_stays_bounded`, with both sides of its bound measured: with the test run on its own, the path stored and fetched 256 MiB and raised the peak of the test process by 120 MiB in each of three runs, while a reader that takes the object in one piece raised it by 478 to 502 MiB.

## "First wins" is a look, not a lock

Before it uploads, the writer asks the store whether an object lies under the address, and if one does it uploads nothing.
The same content stored twice is one object, and the second call reports that it didn't upload.

That's a look followed by an action, and between the two lies the time that sealing and uploading take.
Two writers that store the same new content at the same moment both see nothing, and both upload.
Measured on 2026-10-05 with `measure_race.py`, twenty rounds at 64 MiB against RustFS 1.0.1, the two ciphertexts sealed to two different recipients so that the survivor could be told apart, and a reader fetching the object in a loop meanwhile:

- **The object was never torn.** Every round, exactly one of the two ciphertexts stayed, whole—thirteen times the one, seven times the other—and it opened to the address.
- **The metadata belonged to the ciphertext** in all twenty rounds: the key an object names and the bytes it holds are replaced together.
- **A reader caught mid-replacement gets an error, not wrong bytes.** Of the reader's attempts that found an object, seventeen broke off with an error from the S3 client while the second upload replaced what they were reading, and three opened to the right content.

The damage, then, is a read that breaks off, and only for a reader who fetches a content at the instant it's being stored for the first time and twice at once.
A second attempt is expected to succeed, since the object that stays is whole; that wasn't measured on its own.
Both writers get the same address back, and each of them can fetch the content with the identities at hand, the loser included, because the reader takes the key from the object.
The adapter translates the broken read into a storage error, so the S3 client's own exception never reaches `core`.

A conditional write, `If-None-Match: *`, would close the window.
RustFS knows it, and refused a second `PutObject` with `PreconditionFailed`.
The adapter uploads with `upload_fileobj` of `boto3` 1.43.108, though, at every size, and that call doesn't pass it through: it rejects `IfNoneMatch` as an argument.
Whether the store of the operation knows the condition isn't measured.
The design doesn't need it and doesn't build it.

"First wins" has a price even without a race: the writer trusts what lies there.
It can't check it, because a writer holds no identity.
If a damaged object lies under an address, every later writer of that content is told it's stored, and only a fetch, which compares the address, finds out.

## Why the key stands beside the object and not in the log

Every object names the key it's sealed to, as metadata written beside it in the same request as the ciphertext.
The architecture wanted that name in the log instead, in the reference to the blob, as "the key actually used."
Under "first wins" the log can't know it.

Take the writer that finds an object already there.
It uploads nothing, so the key it would write into the log is its own current recipient, and after a change of key that's a different key from the one the existing object is sealed to.
Take two writers that upload at once.
One ciphertext stays, and the loser would write into the log a key that nothing in the store is sealed to.
In both cases the log would carry a wrong key, and a reference in the payload is attested by the chain and can never be corrected.

The key is a property of the object, so it stands with the object, and the measurement above shows that the store keeps the two together.
The reader takes it from there, out of the same answer that delivers the bytes: two requests could see, while an object is being replaced, the key of one upload and the body of the other.
The name is a hint and not a proof.
Whoever forges it achieves an object that doesn't open, and whoever can do that can delete the object as well.

## The keys

Writing needs a recipient, the public half of a key, in its `age1…` spelling.
Reading needs the identity, the secret half.
A service that only takes in attachments therefore never needs the secret, and that's the separation operations want: the process that faces the outside world can seal and can't open.

After a change of key, new objects are sealed to the new recipient, and old ones stay readable for as long as their identity is kept.
An object that already lies there stays sealed to its old key, even when a new event points at it.

The identities come through a narrow seam: a key name goes in, an identity comes out, as text.
The one implementation today reads them from a directory with one file per recipient, named after it, in the format `age-keygen` writes.
A directory of files is the form in which Kubernetes shows a mounted secret, and on a host with `docker-compose` it's a directory beside the compose file.
A vault with key management of its own would be a second implementation behind the same seam.

The key name comes from the metadata of an object, so it's input from outside: whoever can write to the bucket chooses it.
It's therefore checked before it becomes part of a path.
Only the exact shape of a recipient names a file, `age1` and 58 characters of its alphabet, and anything else, `../x` or `/etc/passwd` or a name too long for the file system among it, is treated as unknown without the disk being asked.
A file that's there and can't be read is a fault of the key directory, and it's reported as one rather than as a missing key.
That's also why the writer stores the recipient in lower case, the canonical spelling of its encoding, even when it was given in upper case.

The address is held to its shape too: the adapter refuses anything that isn't 64 lower-case hexadecimal characters before a request goes out, because a key with `/` or `..` in it would depend on how the server normalizes a path.

The store's errors come in two kinds, and the split decides where an operator looks.
A store that doesn't answer, a connection that times out or a stream that breaks off is unreachable.
A store that answers and refuses, or settings the client won't even send, such as an empty bucket name, are refused, with a message that says the settings aren't usable.
An error the S3 client doesn't file under a connection lands on the side of the settings, so that a typo in the environment doesn't send anybody to look for a server that's down.

No message of the blob path names an identity, and no message of the store names its credentials.
A malformed recipient is quoted, since a recipient is public; a malformed identity isn't, since what stands in its place may be a real one with a typo in it.

```{warning}
Losing the identity loses every blob sealed to it.
There is no recovery: the store holds ciphertext only, and nothing else holds the key.
The identity is one line of text, and it has to be backed up apart from the bucket—never where the blobs are.
```

## First the blob, then the event

`previously append --attach` stores every attachment before it appends the event, and the order is forced by what the event says.
The event names its blobs by address, and the address is known only once the content has been read; the event hash covers the names, so the event can't be written first and corrected later.

Before it stores anything, the command opens every file.
A file that can't be read then stores nothing and appends nothing, rather than leaving the first attachments in the bucket and failing on the third.
It checks the recipient up front as well: "first wins" means that a content the store already holds isn't sealed again, so a mistyped recipient would otherwise pass unnoticed until the first new content arrived.

What can still go wrong comes after the blobs are stored: the database doesn't answer, or the event is refused.
Then the blobs stay in the bucket, and no event names them.
That's harmless in the sense that matters—nothing reads a blob no event names, and `blob get` refuses an address no event uses—but it's storage nobody accounts for, and there is no sweep for it yet.
The other order would be worse: an event that names a blob the store never received is a reference the chain attests and nothing can satisfy.

The store takes part in no database transaction, so no order makes the two writes one.
Blob first is the order in which a failure leaves something unused rather than something wrong.

## The reference in the payload, the register beside it

An event names each blob in its payload, under the key `blobs`: the address, the size, the media type and the file name.
Because the reference stands in the payload, the payload digest covers it, and the chain attests *which* bytes belong to the event—not the bytes themselves, which lie outside the database, but their identity.
That's the same move as for the units: the log holds a digest, and the digest pins the content wherever it lies.

The key `blobs` is reserved like `evidence`: `append` refuses a payload that already carries it, rather than overwriting it.
The reservation came with stage 1c, so a payload written through the library before it may carry a key `blobs` of its own; `verify` now reads that key as references, and reports such an event as one whose register doesn't match.
An event without attachments carries no such key at all, so its payload is the one it would have had before blobs existed.

Next to the payload stands a table, `event_blob`, with one row per event and blob.
It answers a question the payload can't answer cheaply: which events use this blob?
Asking the payloads would mean reading every event, and `blob get` asks it before every fetch, as an erasure does.

The register carries no truth of its own, and that's the point of keeping it beside the payload rather than instead of it.
The chain covers the payload and not the register, so the register can be wrong in a way the chain doesn't see: a row added, a row deleted.
`verify` therefore holds the two against each other, as sets of addresses: the same content attached twice is two references and one row.
Once an event is erased, its payload is gone, and the redaction takes over what the payload attested: it names the blobs the erased event used, out of the register, and `verify` holds the register against that list from then on.

## Why the file name belongs to the use

The same bytes can arrive as `invoice.pdf` on one mail and as `scan-0042.pdf` on another.
They make one blob, because they hold one content, and two uses with two names.
So the name stands in the reference, at the event, and not at the object in the store.
An object that carried a name would carry the name of whichever writer came first, and "first wins" would turn every later name into a silent loss.

The name is the file's name without its directory: where the file lay on the machine that attached it says nothing about the content, and the payload is kept for good.
The media type is derived from that name alone, never guessed from the content, and only from the table built into Python itself, not from the files of the system it runs on.
Both stand in the event hash forever, so neither may depend on which machine attached the file.

## When a blob goes again

A blob leaves the store through an erasure, of the events that use it or of the blob itself, and only once every reference to it has been erased.
A blob shared by two mails stays when one of them is erased, because the other still names it.
{ref}`erasure` gives the rule, its consequences, and why the store is touched only after the redaction stands.

Gone from the store isn't gone everywhere.
Whatever backup or replica of the bucket exists keeps the object for as long as it's kept, and the identity, backed up as the warning above asks, still opens it.
Whoever promises erasure within a period chooses the retention of the bucket's backups by it, beside that of the database's.

The register is what makes that rule cheap to compute.
An erasure asks it which events use a blob, holds each of them against the redactions, and knows whether the blob still has to lie, without reading a single payload.

## What verify checks in the store

Without a switch, `verify` touches no blob: it holds the register against the payloads and the redactions, inside the database.
With `--blobs` it also reads the store, after the pass over the chain, and holds every blob the register names against the rule.
A blob that has to lie is fetched whole, opened, and its plaintext hashed against its address; a blob that doesn't have to lie is only asked for, and if it's still there, that's a finding.

It reads every byte because nothing short of that shows that a blob is the content its address names.
The address is the hash of the plaintext, and the store holds ciphertext only, so asking whether an object exists, or how large its ciphertext is, says nothing about which content it opens to.
Only the opened plaintext, hashed, answers the question the log asks.
That makes the switch as slow as the store is large, which is a check for the night and not for every run of the anchor routine.

The blobs are read after the snapshot of the chain, not inside it.
A transaction held open for as long as reading the whole store takes holds back the database's cleanup for that long.
The price is that the store is seen a little later than the log, and that can show either way.
A blob erased and deleted while the check runs is reported as missing.
A blob whose redaction the snapshot already holds is reported as erased and still present while a concurrent `redact` hasn't deleted it yet, or when the same content was attached again after the snapshot.
The next run reports none of them.
The check starts from the register, so an object in the store that no event names, such as one left by an append that failed after its upload, is reported by nothing.
The references of every blob are held in memory until then, one address and its event identifiers per blob.

A finding says something about the log and its blobs: a blob is missing, doesn't match its address, can't be opened, or is erased and still present.
A store that doesn't answer, an identity file that can't be read, or a stream that breaks off says nothing about the blobs, only that the check couldn't be made, so it ends the command as an error instead of reporting blobs as broken that nobody looked at.
