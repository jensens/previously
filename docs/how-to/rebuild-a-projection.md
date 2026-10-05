(rebuild-a-projection)=

# How to rebuild a projection

This guide shows you how to bring a projection back to the tip of the log, and how to force a rebuild when a catch-up isn't enough.

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

## Force a rebuild after a change to the derivation

Raise the projection's version in the code whenever you change how its rows are derived.
`ChronicleProjection.version` in `src/previously/core/projection/chronicle.py` carries the chronicle's version, and `SourceStatsProjection.version` in `src/previously/core/projection/source_stats.py` carries the statistics' version.
Read the current value there, and raise it by one.
For a chronicle at version 2, the line becomes this one:

```python
version: int = 3
```

Then run `previously project`.
It empties that projection's table and builds it again from the log.
The line for the projection you raised begins with `rebuilt:`, names the version it moved from and to, and ends with the number of events projected and the new `up_to_id`.
The line for the projection you left alone reports `up to date`.
If `previously redact` runs before `previously project` does, it catches the projections up itself, and prints the same `rebuilt:` line on standard error.

A raised version rebuilds the rows and leaves the table's columns and indexes as they are.
If your change needs a column that isn't there yet, write a migration for it as well; see {ref}`add-a-migration`.

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
The line for the other projection again reports `up to date`.

:::{warning}
The `DELETE` drops the bookmark and leaves the rows of `p_chronicle` standing.
Until the next `previously project`, or a `previously redact`, which catches up as well, `previously chronicle` prints those old rows and reports the whole log as its lag.
`previously project` then empties the table in its first transaction and fills it batch by batch, so a `previously chronicle` run during a long rebuild sees a partial chronicle, with the lag line saying how far the rebuild has come.
:::

To force the statistics the same way, use `'source-stats'` in place of `'chronicle'` in the `DELETE`.

A `previously project` or `previously redact` that runs while you delete the row stops with exit code 2 and a sentence that the projection `has no state row`; run it again once the `DELETE` is done.

## When a catch-up says that the projection was rebuilt while it ran

If `previously project`, or a `previously redact` in the sentence of an unfinished redaction, reports that a projection `was rebuilt while this catch-up ran: it stands at version <n>`, another version of the code is catching up the same database.
Each release rebuilds the table to its own version whenever it finds another, so the two undo each other's work.

1.  Find the process of the release that isn't meant to run against this database, such as a scheduled `previously project` of the old or the new version, and stop it.
2.  Run `previously project` again with the release meant to run against this database.
    Its line for that projection begins with `rebuilt:` if the other release left the table at its own version.
3.  If the error came from `previously redact`, run the same `redact` command again with that release; it finds its target covered and finishes.

For the wording of the error, see {ref}`cli-reference`.

For why a rebuild yields the same rows as the incremental path, see {ref}`projections`.
