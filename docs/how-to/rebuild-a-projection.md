(rebuild-a-projection)=

# How to rebuild a projection

This guide shows you how to bring a projection back to the tip of the log, how to build one after an upgrade, and how to force a rebuild when a catch-up isn't enough.

Only `previously project` builds or rebuilds a projection.
Every other command that catches one up, the listings of the graph, every MCP call and `previously redact`, catches up from where the projection stands and stops with an error where it isn't built at the version its code declares.

## Check how far behind a projection is

Run the command that reads the projection you're asking about: `previously chronicle` for the chronicle, `previously stats` for the per-source statistics.

```shell
previously chronicle
```

Each command reports the lag of the projection it read as one line on standard error: the line names how many events are missing and recommends `previously project`.

Without that line, the projection stands at the tip of the log.
Both commands return 0 whether the projection is behind or not, so read standard error rather than the exit code.
`previously chronicle` can print a second line there, about a window cut by `--limit`; see {ref}`cli-reference` for the exact wording of both.
Run both commands if you want to know about both projections.

Then bring every projection up to the tip.

```shell
previously project
```

`previously project` prints one line per projection, and each line names the path that run took.
See {ref}`cli-reference` for the four outcomes and their exact wording.

## Check the graph projection against the log

Run `previously project` with `--check`.

```shell
previously project --check
```

It catches up as `previously project` does, then folds the log and prints one line per thread whose row in `p_graph_thread` differs from the fold, beginning with `graph` and the thread's id.
It returns 0 when no line was printed and 1 otherwise; see {ref}`cli-project-check` for the wording.
If it reports a thread or a version row, force a rebuild of the projection `graph` as the next sections describe, and run the check again.

## Force a rebuild after a change to the derivation

Raise the projection's version in the code whenever you change how its rows are derived.
`ChronicleProjection.version` in `src/previously/core/projection/chronicle.py` carries the chronicle's version, `SourceStatsProjection.version` in `src/previously/core/projection/source_stats.py` carries the statistics' version, and `GraphProjection.version` in `src/previously/core/projection/graph.py` carries the graph's version.
Read the current value there, and raise it by one.
For a chronicle at version 3, the line becomes this one:

```python
version: int = 4
```

Then run `previously project`.
It empties that projection's tables and builds them again from the log.
The line for the projection you raised begins with `rebuilt:`, names the version it moved from and to, and ends with the number of events projected and the new `up_to_id`.
The lines for the projections you left alone report `up to date`.
Until `previously project` has run, every command that would need the rebuild stops with an error that names `previously project`, and builds nothing: the listings of the graph and every MCP call for `GraphProjection.version`, and `previously redact` for any of the three.
The next section says how to order that in a deployment.

A raised version rebuilds the rows and leaves the table's columns and indexes as they are.
If your change needs a column that isn't there yet, write a migration for it as well; see {ref}`add-a-migration`.

## Build the projections in the upgrade step

Run `previously project` after `previously migrate` and before the new release serves, on every upgrade whose release raises a projection's version, and on the first upgrade to a release with migration `0006`, which creates the graph projection's tables empty.
A new installation needs it once as well, after its first `previously migrate`.

```shell
previously migrate
previously project
```

The `previously project` line of a projection that was built begins with `built:` or `rebuilt:`.
It takes as long as the log is: 3.5 s at 10,000 relations and 35 s at 100,000 for the graph, measured on 2026-10-15 ({ref}`graph-cost`).

If the step is skipped, nothing is built behind your back, and nothing answers from a slower path either:

- `previously entities`, `relations`, `entity`, `triage`, `status`, `classes list`, `classes sample` and `chronicle --within` exit 2 with the sentence ``projection graph is not built, and this code declares version <n>; `previously project` builds it``, or with `stands at version <m>` in place of `is not built` and an advice that names the release meant to serve.
- `previously mcp` and `previously serve` refuse to start with the same sentence.
- A server that's already running fails every call, and the reason is in its log.
- `previously redact` records the redaction and then reports it as unfinished, with the advice to run `previously project` and then the same command again.

### During a rolling update

When a rolling update replaces the pods of a server whose release changes the graph projection's version, run `previously project` of the new release once, before the first new pod serves, for example in an init container or a job of the upgrade step.

1.  Move a scheduled `previously project` to the new release, or suspend it, first.
    A `project` of the old release that starts after the new one ran would build the projection back to the old version; one already running stops at its next batch.
2.  `previously project` of the new release rebuilds the graph projection at the new version.
3.  From then on, the old pods' readiness probe on `/healthz` answers 503, and their calls fail until they're replaced, because the projection no longer stands at the version they declare.
4.  The new pods start, find the projection at their version, and their readiness probe answers 200.

The old pods don't rebuild back, so the two releases never take turns at undoing each other's build.
Graph calls to an old pod fail for as long as it runs, so keep that window short.
A rollback is the same move the other way round: run `previously project` of the release you roll back to.

## Force a rebuild without a code change

Delete the projection's row from `projection_state`, then run `previously project`.

```shell
psql postgresql://USER:PASSWORD@HOST:PORT/DATABASE \
    -c "DELETE FROM projection_state WHERE name = 'chronicle'"
previously project
```

Pass `psql` the plain `postgresql://` form of the connection, not the value of `PREVIOUSLY_DSN`: `libpq` doesn't know the `+psycopg` driver prefix and reads the whole value as a database name.
Take the host, port, database and credentials from the value you have set; see {ref}`configuration-reference` for its form.

With no state row left to compare against, that projection's line begins with `built:` instead of `rebuilt:`.
The lines for the other projections again report `up to date`.

:::{warning}
The `DELETE` drops the bookmark and leaves the rows of `p_chronicle` standing.
Until the next `previously project`, `previously chronicle` prints those old rows and reports the whole log as its lag.
For the graph, every listing of the graph and every MCP call fails meanwhile, with the sentence that the projection `is not built`, and the readiness probe of a running server answers 503.
`previously project` then empties the table in its first transaction and fills it batch by batch, so a `previously chronicle` run during a long rebuild sees a partial chronicle, with the lag line saying how far the rebuild has come.
:::

To force the statistics the same way, use `'source-stats'` in place of `'chronicle'` in the `DELETE`.

A `previously project`, a `previously redact` or a reader of the graph whose next batch starts after your `DELETE` commits stops with exit code 2 and a sentence that the projection `has no state row`; run `previously project` again once the `DELETE` is done.
A reader whose snapshot finds the graph projection emptied by that `previously project` catches up once more and reads; a reader that finds it emptied twice in a row stops with a sentence to read again once `previously project` has finished.

## When a catch-up says that the projection was rebuilt while it ran

If `previously project`, or a `previously redact` in the sentence of an unfinished redaction, reports that a projection `was rebuilt while this catch-up ran: it stands at version <n>`, another version of the code is catching up the same database.
The `previously project` of each release rebuilds the table to its own version whenever it finds another, so two of them undo each other's work.

1.  Find the process of the release that isn't meant to run against this database, such as a scheduled `previously project` of the old or the new version, and stop it.
2.  Run `previously project` again with the release meant to run against this database.
    Its line for that projection begins with `rebuilt:` if the other release left the table at its own version.
3.  If the error came from `previously redact`, run the same `redact` command again with that release; it finds its target covered and finishes.

For the wording of the error, see {ref}`cli-reference`.

For why a rebuild yields the same rows as the incremental path, see {ref}`projections`.
