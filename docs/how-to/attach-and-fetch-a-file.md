(attach-and-fetch-a-file)=

# How to attach a file to an event and fetch it again

This guide shows you how to store a file as a blob at a new event, see it in the log, and fetch it back into a file.
You need a bucket and a key: {ref}`run-a-blob-store-on-your-machine` gives you a bucket to try this against, and {ref}`keep-the-blob-key-safe` gives you the key.

## Set the blob settings

Set the five settings of the store, the recipient new blobs are sealed to, and the directory of identities that opens them:

```shell
export PREVIOUSLY_BLOB_ENDPOINT=http://localhost:9000
export PREVIOUSLY_BLOB_REGION=us-east-1
export PREVIOUSLY_BLOB_BUCKET=previously-blobs
export PREVIOUSLY_BLOB_ACCESS_KEY=previously-dev
export PREVIOUSLY_BLOB_SECRET_KEY=YOUR-SECRET
export PREVIOUSLY_BLOB_RECIPIENT=age1x7xtemjzh6dl65j2wjfhcewmdyawczlhw00387um4n4drl9v93lsv6d3pa
export PREVIOUSLY_BLOB_IDENTITIES=/path/to/identities
```

Put in the values of your own store and key.
A process that only attaches files needs the first six and never the directory of identities.
See {ref}`configuration-reference` for what each setting takes and which command reads it.

## Attach the file

Pass the file to `previously append` with `--attach`:

```console
$ previously append \
    --source email \
    --external-id 2026-10-05-minutes@example.org \
    --text "The minutes of the kickoff are attached." \
    --attach minutes.txt
1
```

To attach several files, repeat `--attach` once per file.
If `append` fails after a file was stored, run the same command again: the store already holds that content and keeps the one object.

## See the blob at the event

```console
$ previously show 1
id=1 kind=observation
occurred_at=2026-10-05T02:58:45.665679+00:00
hash=57cf08a07e7efb0c91d1cfcd16a51ad9b92fabf299d1e9837c714976490b8544
evidence=recollection
payload={"blobs": [{"filename": "minutes.txt", "media_type": "text/plain", "sha256": "72f4f2c5a92ade61b696c0fe800b8af775fd2f3982b123693379e6ee7cd264f2", "size": 62}], "evidence": "recollection", "text": "The minutes of the kickoff are attached."}
  ¶1 The minutes of the kickoff are attached.
  blob 72f4f2c5a92ade61b696c0fe800b8af775fd2f3982b123693379e6ee7cd264f2 62 text/plain minutes.txt
```

The last line names the blob: its address, its size in bytes, its media type and its file name.
The address is what you fetch it by.

## Fetch the file

Pass the address to `previously blob get`, with the file to write to:

```console
$ previously blob get 72f4f2c5a92ade61b696c0fe800b8af775fd2f3982b123693379e6ee7cd264f2 --output minutes-copy.txt
wrote 62 bytes to minutes-copy.txt
```

`blob get` writes the file only once its content matched the address, and makes it readable by its owner only.
If a file of that name exists, `blob get` replaces it without asking; choose a name nothing else uses.
If it returns `1` with `is erased`, an erasure took the blob, and nothing fetches it any longer.
For every other error and its exit code, see {ref}`cli-reference`.

To check every blob of the log at once, run `previously verify --blobs`; see {ref}`verify-the-chain`.
