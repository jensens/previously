(environment-requirements)=

# Environment requirements

Previously requires the following of the environment it runs in.
How an environment meets a requirement is its own choice, and the page that gives the reason names examples.
An operator who doesn't meet a requirement decides that consciously and carries the risk the reason names.

| Concerns | Requirement | Reason |
|---|---|---|
| Database | PostgreSQL 18, the version the tests and the smoke test run against. The schema itself needs 15 or newer. | {ref}`configuration-reference`, {ref}`concurrency` |
| Database | The role in `PREVIOUSLY_DSN` may create tables and indexes in the schema `public` when `previously migrate` runs, and read the table `alembic_version`. | {ref}`cli-reference`, under `migrate` |
| Backups | Encrypted before they leave the database's host. The key that opens them lies outside the system it protects, and opening a backup with it has been rehearsed. | {ref}`backup-encryption` |
| Backups | A named retention for every backup of the database, for a write-ahead log archive where one is kept, and for every backup or copy of the bucket. | {ref}`backup-encryption`, {ref}`erasure` |
| Backups | A stated recovery point: a point in time, or the newest dump. | {ref}`backup-encryption` |
| Backups | A restore probe runs at a rhythm the operator names, and ends with `previously verify --anchors` against the anchor file as of the backup. Where the probe holds the opening key is the environment's choice. | {ref}`backup-encryption`, {ref}`restore-from-a-backup` |
| Backups | No credential that a process handling foreign content holds can delete or overwrite a backup: not one held by the ingest, the gate, the MCP server, or wherever an operator runs the commands by hand. | {ref}`backup-deletion` |
| Bucket | One S3 bucket for the blobs, without versioning and without object lock. | {ref}`erasure` |
| Bucket | No credential other than those Previously holds can delete or overwrite the bucket's objects. | {ref}`blob-bucket-requirements` |
| Credentials | The bucket credentials Previously holds reach that bucket and nothing else. | {ref}`blob-bucket-requirements` |
| Credentials | Within the bucket, those credentials allow `HeadObject`, `PutObject` with multipart upload, `GetObject` and `DeleteObject` on its objects. On a server that answers a missing object with `403` instead of `404` without it, they also allow `ListBucket`; otherwise `append --attach` of new content fails. | {ref}`blobs` |
| Keys | The blob identity has a backup apart from the bucket, the database and their backups, and opening a blob from that backup has been rehearsed. | {ref}`keep-the-blob-key-safe` |
| Keys | The blob identity reaches only the processes that open blobs, `blob get` and `verify --blobs`. A process that only takes content in gets the recipient, which is public. | {ref}`blobs` |
| Anchors | The anchor file lies where whoever can write the database can't write. A history of the file lets a restore check against its version as of the backup. | {ref}`verify-the-chain`, {ref}`restore-from-a-backup` |
