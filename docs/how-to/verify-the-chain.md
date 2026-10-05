(verify-the-chain)=

# How to check the chain in operation

This guide shows you how to check whether the chain is intact, how to read what it reports, how to anchor the chain outside the database, and how to check the blobs.

Run `previously verify`.

```shell
previously verify
echo $?
```

If the exit code is `0`, the chain has no finding.
`previously verify` printed `chain intact` on standard output, and a notice on standard error that no anchor was given.

If the exit code is `1`, the chain or an anchor has at least one finding.
`previously verify` printed one `FINDING <event_id>: <reason>` line per finding instead of `chain intact`.
Read the `<reason>` directly: it names the specific problem with that event, such as a hash that no longer matches its fields.
There's no separate table to look it up against—the printed line is the finding.
See {ref}`cli-reference` for the full exit-code table, including the `2` that invalid input or a storage error uses.

If you run this check from a script, for example in a deployment pipeline, treat any exit code other than `0` as a failure and stop before you rely on that database further.

Without anchors, exit code `0` means that the chain is consistent in itself, and nothing more.
It doesn't mean that the chain is complete: a deleted tip, an appended event, or a chain rewritten from the start can each leave that check satisfied.
To check the log up to a point you recorded outside the database, anchor the chain as the next section shows.

## Anchor the chain, and check against the anchors

Keep the anchor file in a place that whoever can write the database can't write.
A file on the database's own host or volume doesn't count.

The first time, no anchor file exists yet.
Once the log holds at least one event, take the first anchor:

```shell
previously anchor > anchors.txt
```

Check the new file with the tool right away, not by eye:

```shell
previously verify --anchors anchors.txt
```

It prints `chain intact, 1 anchor holds` and exits `0` when the file holds an anchor.
It exits `2` when the file holds none, and that happens in two cases.
On an empty log, `previously anchor` prints nothing to standard output and exits `0`, so the file is empty.
On a chain with a finding, it prints the `FINDING` lines to standard error, nothing to standard output, and exits `1`, so the file is empty as well.
In either case, delete the file and deal with the cause first.

From then on, run this routine on a schedule, between fetching the anchor file from the place you keep it and putting it back there:

```shell
previously verify --anchors anchors.txt && previously anchor >> anchors.txt
```

The first command checks the chain and every anchor taken so far.
The second command appends the current tip as a new anchor, and runs only if the first one exited `0`.
Treat any exit code other than `0` as an alarm.
If the second command exits other than `0`, it printed nothing to standard output, so the anchor file is unchanged, and its findings or its error are on standard error.
If no event arrived since the last run, the routine appends the same line again.
That's harmless, and it means that the count in `chain intact, <n> anchors hold` counts lines, not events.
Put the file back after every run: an anchor that hasn't left the database's host isn't an anchor yet.

If the command runs inside a container and the anchor file lives outside it, pass `-` to read the anchors from standard input:

```shell
previously verify --anchors - < anchors.txt
```

`previously anchor` prints its line to standard output, so redirect that output to the file outside the container in the same way.

Whatever starts the command inside the container has to meet two conditions, and the usual defaults of container tools don't always meet them:

- It has to pass standard input through, such as `-i` for `docker exec`.
  Without it, `--anchors -` receives nothing and reports that the input holds no anchor.
- It must not allocate a terminal, such as `-T` for `docker compose exec`.
  With a terminal, standard error is mixed into standard output, and whatever `previously anchor` prints to standard error lands in the anchor file: the notice `the log is empty: nothing to anchor` on an empty log, and the `FINDING` lines on a chain with a finding.
  If that happened, remove those lines from the anchor file by hand before the next run.

## Check the blobs, once a night

If the log names blobs, run a second, longer check on a schedule of its own, such as once a night:

```console
$ previously verify --anchors anchors.txt --blobs
chain intact, 1 anchor holds, 1 blob matches
```

`--blobs` reads every blob that has to lie in the store, opens it, and checks it against its address, and it asks the store whether an erased blob is gone, so it takes about as long as reading the whole store does.
Keep it out of the anchor routine above, which runs more often: `--blobs` adds nothing to an anchor.
It needs the five settings of the store and the directory of identities; see {ref}`configuration-reference`.

Treat exit code `1` as an alarm, as for the chain.
The four findings it adds name the blob, and each stands under the first event that names it.
A blob that appears as `missing` after a restore of the database is the case {ref}`restore-from-a-backup` covers.
If every blob of one key appears as `cannot be opened`, first check that the directory of identities holds that key's file, above all on a restored or new machine; {ref}`keep-the-blob-key-safe` says where its backup is.
Exit code `2` means that the check couldn't be made and says nothing about the blobs; run it again once the cause on standard error is gone.
The causes include a store that didn't answer, and a `PREVIOUSLY_BLOB_IDENTITIES` that names no directory on this machine:

```console
$ previously verify --blobs
Error: PREVIOUSLY_BLOB_IDENTITIES is not a directory: /srv/previously/identities
```

The settings are read before the chain is checked, so this error comes alone; an error of the store while the blobs are checked comes after the pass over the chain, and that pass's findings still go to standard output beside it.

The check can't see a bucket with versioning or object lock: there, deleting an erased blob keeps a copy, and `--blobs` asks only after the current object.
Nothing in Previously checks the bucket for it; {ref}`run-a-blob-store-on-your-machine` shows how to ask a bucket for both.

For the format of an anchor line and the three findings an anchor can produce, see {ref}`cli-reference`.
For what an anchor closes, and what it leaves open, see {ref}`external-anchor`.
