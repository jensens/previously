(rebuild-a-projection)=

# How to rebuild a projection

This guide shows you how to bring a projection back to the tip of the log, and how to force a rebuild when a catch-up isn't enough.

## Check how far behind a projection is

Run the command that reads the projection you're asking about: `previously chronicle` for the chronicle, `previously stats` for the per-source statistics.

```shell
previously chronicle
```

Each command reports the lag of the projection it read, as one line on standard error.

```text
projection is 12 events behind; run `previously project`
```

Without that line, the projection stands at the tip of the log.
Both commands return 0 whether the projection is behind or not, so read standard error rather than the exit code.
`previously chronicle` can print a second line there, about a window cut by `--limit`; see {ref}`cli-reference` for both.
Each command reports the lag of its own projection, so run both if you want to know about both.

Then bring every projection up to the tip.

```shell
previously project
```

`previously project` prints one line per projection, and each line names the path that run took.
See {ref}`cli-reference` for the four outcomes and their exact wording.

## Force a rebuild after a change to the derivation

Raise the projection's version in the code whenever you change how its rows are derived.
`ChronicleProjection.version` in `src/previously/core/projection/chronicle.py` carries the chronicle's version, and `SourceStatsProjection.version` in `src/previously/core/projection/source_stats.py` carries the statistics' version.
Both stand at `1`.

```python
version: int = 2
```

Then run `previously project`.
It empties that projection's table and builds it again from the log.

```text
chronicle       rebuilt: version 1 -> 2, 12 events, up_to_id 12
```

A raised version rebuilds the rows and leaves the table's columns and indexes as they are.
If your change needs a column that isn't there yet, write a migration for it as well; see {ref}`add-a-migration`.

## Force a rebuild without a code change

Delete the projection's row from `projection_state`, then run `previously project`.

```shell
psql postgresql://previously:previously@localhost:5432/previously \
    -c "DELETE FROM projection_state WHERE name = 'chronicle'"
previously project
```

Pass `psql` the plain `postgresql://` form of the connection, not the value of `PREVIOUSLY_DSN`: `libpq` doesn't know the `+psycopg` driver prefix and reads the whole value as a database name.
See {ref}`configuration-reference` for the form that `PREVIOUSLY_DSN` carries.

With no state row left to compare against, the run reports a first build.

```text
chronicle       built: 12 events, up_to_id 12
```

:::{warning}
The `DELETE` drops the bookmark and leaves the rows of `p_chronicle` standing.
Until the next `previously project`, `previously chronicle` prints those old rows and reports the whole log as its lag.
`previously project` then empties the table in its first transaction and fills it batch by batch, so a `previously chronicle` run during a long rebuild sees a partial chronicle, with the lag line saying how far the rebuild has come.
:::

To force the statistics the same way, use `source-stats` in place of `chronicle`.

For why a rebuild yields the same rows as the incremental path, see {ref}`projections`.
