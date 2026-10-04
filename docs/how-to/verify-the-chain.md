(verify-the-chain)=

# How to check the chain in operation

This guide shows you how to check whether the chain is intact, how to read what it reports, and how to anchor the chain outside the database.

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
On a chain with a finding, it prints the `FINDING` lines to standard output and exits `1`, so those lines are in the file.
In either case, delete the file and deal with the cause first.

From then on, run this routine on a schedule, between fetching the anchor file from the place you keep it and putting it back there:

```shell
previously verify --anchors anchors.txt && previously anchor >> anchors.txt
```

The first command checks the chain and every anchor taken so far.
The second command appends the current tip as a new anchor, and runs only if the first one exited `0`.
Treat any exit code other than `0` as an alarm.
If the second command exits other than `0`, whatever it printed to standard output is now in the anchor file, and you have to remove those lines by hand before the next run.
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
  With a terminal, standard error is mixed into standard output, and on an empty log the notice `the log is empty: nothing to anchor` lands in the anchor file.

For the format of an anchor line and the three findings an anchor can produce, see {ref}`cli-reference`.
For what an anchor closes, and what it leaves open, see {ref}`external-anchor`.
