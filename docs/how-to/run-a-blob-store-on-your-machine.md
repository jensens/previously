(run-a-blob-store-on-your-machine)=

# How to run a blob store on your machine

This guide shows you how to start an S3 server in a container on your own machine, create a bucket on it, and point Previously at it.
The server is RustFS, the one the test suite starts for itself.
It serves trying out the blob commands and development, not operation: in operation, the bucket comes from the storage provider your deployment uses.
For what each setting means, see {ref}`configuration-reference`.

## Start the server

Choose an access key, generate a secret, and export both under the names Previously reads:

```shell
export PREVIOUSLY_BLOB_ACCESS_KEY=previously-dev
export PREVIOUSLY_BLOB_SECRET_KEY=$(openssl rand -hex 16)
```

Create a network, so that the container of the next step can reach the server by its name:

```shell
docker network create previously-blobs
```

Start RustFS on that network, with port 9000 published to your machine and the two values above as its credentials:

```shell
docker run -d --name previously-blobs --network previously-blobs -p 9000:9000 \
    -e RUSTFS_ACCESS_KEY="$PREVIOUSLY_BLOB_ACCESS_KEY" \
    -e RUSTFS_SECRET_KEY="$PREVIOUSLY_BLOB_SECRET_KEY" \
    rustfs/rustfs:1.0.1
```

Wait a few seconds before the next step: the container counts as started before the server answers.

## Create the bucket

Create the bucket with the AWS command-line interface, run from its own container on the same network:

```console
$ docker run --rm --network previously-blobs \
    -e AWS_ACCESS_KEY_ID="$PREVIOUSLY_BLOB_ACCESS_KEY" \
    -e AWS_SECRET_ACCESS_KEY="$PREVIOUSLY_BLOB_SECRET_KEY" \
    -e AWS_DEFAULT_REGION=us-east-1 \
    amazon/aws-cli:2.37.9 --endpoint-url http://previously-blobs:9000 \
    s3 mb s3://previously-blobs
make_bucket: previously-blobs
```

Any S3 client that can create a bucket does the same job.

## Check that the bucket keeps nothing back

The bucket must have neither versioning nor object lock.
On a bucket with either, deleting an object keeps a copy of it, and an erasure no longer removes the blob; see {ref}`erasure`.

Ask for the versioning of the bucket:

```console
$ docker run --rm --network previously-blobs \
    -e AWS_ACCESS_KEY_ID="$PREVIOUSLY_BLOB_ACCESS_KEY" \
    -e AWS_SECRET_ACCESS_KEY="$PREVIOUSLY_BLOB_SECRET_KEY" \
    -e AWS_DEFAULT_REGION=us-east-1 \
    amazon/aws-cli:2.37.9 --endpoint-url http://previously-blobs:9000 \
    s3api get-bucket-versioning --bucket previously-blobs
```

No output means that versioning was never switched on.
If it prints a `Status`, `Enabled` or `Suspended`, delete the bucket and create a new one.

Ask for the object lock of the bucket:

```console
$ docker run --rm --network previously-blobs \
    -e AWS_ACCESS_KEY_ID="$PREVIOUSLY_BLOB_ACCESS_KEY" \
    -e AWS_SECRET_ACCESS_KEY="$PREVIOUSLY_BLOB_SECRET_KEY" \
    -e AWS_DEFAULT_REGION=us-east-1 \
    amazon/aws-cli:2.37.9 --endpoint-url http://previously-blobs:9000 \
    s3api get-object-lock-configuration --bucket previously-blobs

aws: [ERROR]: An error occurred (ObjectLockConfigurationNotFoundError) when calling the GetObjectLockConfiguration operation: Object Lock configuration does not exist for this bucket
```

That error is the answer you want: the bucket has no object lock.

## Point Previously at the server

Export the address, the region and the bucket:

```shell
export PREVIOUSLY_BLOB_ENDPOINT=http://localhost:9000
export PREVIOUSLY_BLOB_REGION=us-east-1
export PREVIOUSLY_BLOB_BUCKET=previously-blobs
```

With the access key and the secret from the first step, these are the five settings of the store.
The two settings that remain, the recipient and the directory of identities, come from a key; create one as {ref}`keep-the-blob-key-safe` shows.
Then attach a first file as {ref}`attach-and-fetch-a-file` shows.

## Remove the server

Remove the container and the network once you're done:

```shell
docker rm -f -v previously-blobs
docker network rm previously-blobs
```

The blobs go with the container and its volume.
Remove the database you appended their events to as well: those events name blobs that no store holds any longer.
