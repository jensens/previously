(configuration-reference)=

# Configuration

Previously reads exactly one environment variable: `PREVIOUSLY_DSN`.

| Variable | Form | Used by |
|---|---|---|
| `PREVIOUSLY_DSN` | `postgresql+psycopg://user:pass@host:5432/database` | The `previously` command line, and Alembic migrations. |

Alembic migrations resolve the connection string through `migrations.dsn.resolve_dsn`.
An explicit `sqlalchemy.url` in `alembic.ini`, or set programmatically on the `Config` object, takes precedence over `PREVIOUSLY_DSN`.
With neither set, the migration fails with an error that names both.

```{important}
PostgreSQL 15 or newer.
`NULLS NOT DISTINCT` is not optional; see {ref}`concurrency`.
```
