(add-a-migration)=

# How to add a migration

This guide shows you how to add a schema change as an Alembic migration.

Create a blank revision.

```shell
uv run alembic revision -m "add an index on occurred_at"
```

Alembic writes a new file into `src/previously/migrations/versions/`.
Write its `upgrade()` and `downgrade()` by hand, the way `src/previously/migrations/versions/0001_log.py` does.
Make the same change to the `Table` and `Index` objects in `src/previously/storage/schema.py`; see {ref}`database-schema` for the schema as it stands before your change.
Keep the two in agreement: the migration is what runs against the database, and the metadata is what the test suite and a future `autogenerate` compare against it.

:::{warning}
If the index you're adding must enforce `NULLS NOT DISTINCT`, set `postgresql_nulls_not_distinct=True` on **both** the `Index` in `schema.py` and the matching `op.create_index()` call in the migration.
Leave it on only one side, and `tests/test_schema.py::test_the_declared_indexes_exist_in_the_migrated_database` won't catch it: it compares index names against `pg_indexes`, and a name can't carry a flag.
`tests/test_schema.py::test_the_declared_nulls_not_distinct_reaches_the_database` does catch it, in both directions, for every index `metadata` declares—run it before you ship the migration.
:::

Apply the migration to the database `PREVIOUSLY_DSN` names.

```shell
uv run previously migrate
```

It prints `migrated:`, the revision the database was at, and your new revision; see {ref}`cli-reference`.
`alembic revision` stays the way to create a revision, and `alembic downgrade` the way back while you work on it.

Confirm that every index declared in `metadata` exists in the migrated database with the same `NULLS NOT DISTINCT` setting.

```shell
uv run pytest tests/test_schema.py::test_the_declared_indexes_exist_in_the_migrated_database tests/test_schema.py::test_the_declared_nulls_not_distinct_reaches_the_database
```
