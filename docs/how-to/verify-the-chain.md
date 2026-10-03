(verify-the-chain)=

# How to check the chain in operation

This guide shows you how to check whether the chain is intact, and how to read what it reports.

Run `previously verify`.
It takes no arguments.

```shell
previously verify
echo $?
```

If the exit code is `0`, the chain has no finding.
`previously verify` printed exactly one line: `chain intact`.

If the exit code is `1`, the chain has at least one finding.
`previously verify` printed one `FINDING <event_id>: <reason>` line per finding instead of `chain intact`.
Read the `<reason>` directly: it names the specific problem with that event, such as a hash that no longer matches its fields.
There's no separate table to look it up against—the printed line is the finding.
See {ref}`cli-reference` for the full exit-code table, including the `2` that a storage error uses.

If you run this check from a script, for example in a deployment pipeline, treat any exit code other than `0` as a failure and stop before you rely on that database further.

`previously verify` proves that no event in the chain has changed since you recorded it.
It doesn't prove that the chain is complete.
Deleting the chain's tip, or appending a new event with its own self-consistent chain, can both leave `previously verify` satisfied.
For what the chain guarantees and where that stops, see {ref}`hash-chain`.
