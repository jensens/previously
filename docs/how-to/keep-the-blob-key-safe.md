(keep-the-blob-key-safe)=

# How to keep the blob key safe

This guide shows you how to create the key that blobs are sealed to, back it up apart from the data, rehearse opening a blob from that backup without Previously, and change the key.
The commands use `age` and `age-keygen`, the command-line tools of the `age` file format; install them from your system's packages.
For why the blobs are sealed with `age`, and why the key stands beside the object, see {ref}`blobs`.

```{warning}
Losing the key loses every blob sealed to it, for good.
The bucket holds ciphertext only, and nothing else holds the key: no command of Previously and no provider can open such a blob again.
```

## Create the key

Generate a key on a machine you trust:

```console
$ age-keygen -o key.txt
Public key: age1x7xtemjzh6dl65j2wjfhcewmdyawczlhw00387um4n4drl9v93lsv6d3pa
```

`key.txt` now holds the identity, the secret half, as one line of the form `AGE-SECRET-KEY-1…`, after two comment lines.
The public key on the screen is the recipient, the public half.
Your recipient differs from the one above.

Move the file into a directory of its own, named after its recipient:

```shell
mkdir identities
mv key.txt "identities/$(age-keygen -y key.txt)"
```

`age-keygen -y` prints the recipient of an identity file, so the file now carries its recipient as its name.
`age-keygen -o` created it readable by its owner only; keep it that way.

Point Previously at the recipient and at the directory:

```shell
export PREVIOUSLY_BLOB_RECIPIENT=$(ls identities)
export PREVIOUSLY_BLOB_IDENTITIES=$PWD/identities
```

`previously append --attach` needs only the recipient.
`previously blob get` and `previously verify --blobs` need the directory, and `previously redact` needs neither.
Give the directory only to the processes that run the two commands that need it.
In operation, the directory is wherever your platform makes a secret available as files, one file per recipient and named after it; it must not lie in the bucket, nor in a backup of the bucket or of the database.
See {ref}`configuration-reference` for both settings.

## Back up the key

Copy every file of the identity directory to a place that's backed up apart from the data:

- not in the bucket, and not in a backup or a copy of the bucket;
- not in the database, and not in its backups;
- in a place you can reach when the machine that runs Previously is gone, such as the vault your other secrets come from.

Keep the file name with the copy: it names the recipient, and with it the objects the identity opens.
Back up a new key before the first blob is sealed to it.

## Rehearse the backup

Rehearse on a regular schedule that a blob opens with the backup alone, without Previously.

1.  Pick a blob from the log, and note its address, the 64 hexadecimal characters after `blob` in the output of `previously show`.

2.  Take the identity file out of the backup, the way you would after losing the machine, and save it as `identity.txt` in an empty directory.
    Don't copy it from the identity directory: that rehearses nothing.

3.  Fetch the object with any S3 tool.
    The bucket holds it under its address as the key.
    With the AWS command-line interface and the settings of the store:

    ```console
    $ export AWS_ACCESS_KEY_ID=$PREVIOUSLY_BLOB_ACCESS_KEY
    $ export AWS_SECRET_ACCESS_KEY=$PREVIOUSLY_BLOB_SECRET_KEY
    $ export AWS_DEFAULT_REGION=$PREVIOUSLY_BLOB_REGION
    $ aws --endpoint-url "$PREVIOUSLY_BLOB_ENDPOINT" s3 cp --no-progress s3://$PREVIOUSLY_BLOB_BUCKET/72f4f2c5a92ade61b696c0fe800b8af775fd2f3982b123693379e6ee7cd264f2 blob.age
    download: s3://previously-blobs/72f4f2c5a92ade61b696c0fe800b8af775fd2f3982b123693379e6ee7cd264f2 to ./blob.age
    ```

4.  Open it with the identity from the backup, and hash what comes out:

    ```console
    $ age -d -i identity.txt -o content blob.age
    $ sha256sum content
    72f4f2c5a92ade61b696c0fe800b8af775fd2f3982b123693379e6ee7cd264f2  content
    ```

    The rehearsal holds when `age` opens the object and the hash is the address.

5.  Delete `content`, `blob.age` and `identity.txt`: the first is the plaintext, and the last is the secret.
    Unset the credentials of the store you exported for the fetch:

    ```shell
    unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_DEFAULT_REGION
    ```

If the object is sealed to a different key than the identity you took, `age` refuses it:

```text
age: error: no identity matched any of the recipients
```

The object names the recipient it's sealed to in its metadata `key-id`, and any S3 tool shows it.
The example below shows an object sealed to the second key of this guide, the one *Change the key* creates:

```console
$ aws --endpoint-url "$PREVIOUSLY_BLOB_ENDPOINT" s3api head-object --bucket $PREVIOUSLY_BLOB_BUCKET --key 109d441a2425851023028341d7ce024fa010d2dfe1d89a49a543c3f8c74aacc9
{
    "AcceptRanges": "bytes",
    "LastModified": "2026-10-05T03:01:23+00:00",
    "ContentLength": 266,
    "ETag": "\"c0faf964bd63fecfe796f41c6ed3ccb0\"",
    "ContentType": "application/octet-stream",
    "Metadata": {
        "key-id": "age18q27nlpyfjrmftuusq6dtdgl8nmqqnwduq63fs5ly5ns7wjsqpwsuf2y4l"
    }
}
```

Take the backup of the file with that name, and try again.
If no backup of it exists, copy that file from the identity directory into the backup now, before anything else.
Only if the identity directory doesn't hold it either is every object sealed to that key lost; then rehearse with the backups of the other keys as well, now.

## Change the key

Create a new key into the same directory, the same way as the first:

```console
$ age-keygen -o key.txt
Public key: age18q27nlpyfjrmftuusq6dtdgl8nmqqnwduq63fs5ly5ns7wjsqpwsuf2y4l
$ mv key.txt "identities/$(age-keygen -y key.txt)"
$ ls identities
age18q27nlpyfjrmftuusq6dtdgl8nmqqnwduq63fs5ly5ns7wjsqpwsuf2y4l
age1x7xtemjzh6dl65j2wjfhcewmdyawczlhw00387um4n4drl9v93lsv6d3pa
```

Back up the new file, then make its recipient the one new blobs are sealed to:

```shell
export PREVIOUSLY_BLOB_RECIPIENT=age18q27nlpyfjrmftuusq6dtdgl8nmqqnwduq63fs5ly5ns7wjsqpwsuf2y4l
```

Keep the old file in the directory and in the backup.
Every object sealed to the old key stays sealed to it, also when a new event names the same content again.

Once a blob is sealed to the new key, check that the objects of both keys open:

```console
$ previously verify --blobs
chain intact, 2 blobs match
no anchor given: verify attests that the log is unchanged, not that it is complete; see `previously anchor`
```

For the findings `verify --blobs` can report, see {ref}`cli-reference`.
