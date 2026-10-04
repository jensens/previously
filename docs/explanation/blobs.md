(blobs)=

# About blobs

An event can carry more than text: a scanned letter, a recording, a spreadsheet somebody attached to a mail.
Previously keeps such a content as a blob, outside the database, in an S3 bucket, and seals it before it leaves the process.
This page explains how a blob is addressed, why the store only ever sees ciphertext, why the format is `age`, and what "first wins" does and doesn't promise.
It also says what isn't built yet.

## The address is the hash of the content

A blob lies under the SHA-256 of its plaintext, written as 64 lower-case hexadecimal characters.
That hash is its address in the store and, from the next step on, its name in the log.

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
The test suite holds the memory bound as a test, `test_memory_stays_bounded`, with both sides of its bound measured: the path stores and fetches 256 MiB and raises the peak of the test process by 120 MiB at most, while a reader that takes the object in one piece raises it by 478 to 502 MiB.

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
A second attempt succeeds.
Both writers get the same address back, and each of them can fetch the content with the identities at hand, the loser included, because the reader takes the key from the object.
The adapter translates the broken read into a storage error, so the S3 client's own exception never reaches `core`.

A conditional write, `If-None-Match: *`, would close the window.
RustFS knows it, and refused a second `PutObject` with `PreconditionFailed`.
The upload in parts of `boto3` 1.43.108 doesn't pass it through, though: it rejects `IfNoneMatch` as an argument, and whether the store of the operation knows it isn't measured.
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
Only `age1` followed by lower-case letters and digits names a file, and anything else, `../x` or `/etc/passwd` among it, is treated as unknown without the disk being asked.
That's also why the writer stores the recipient in lower case, the canonical spelling of its encoding, even when it was given in upper case.

No message of the blob path names an identity, and no message of the store names its credentials.
A malformed recipient is quoted, since a recipient is public; a malformed identity isn't, since what stands in its place may be a real one with a typo in it.

```{warning}
Losing the identity loses every blob sealed to it.
There is no recovery: the store holds ciphertext only, and nothing else holds the key.
The identity is one line of text, and it has to be backed up apart from the bucket—never where the blobs are.
```

## What this page doesn't say yet

The blob path stands as a library, and the log doesn't know about it yet.
How a blob gets attached to an event, and how the log names it, comes with the next step of stage 1c.
When a blob goes again, through an erasure of the events that use it, comes after that; {ref}`erasure` describes erasure as it stands today.
