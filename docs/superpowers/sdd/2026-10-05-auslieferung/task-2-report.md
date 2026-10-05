# Task 2 report: `previously migrate`

Status: DONE, with concerns (below). Commit `5e5691e` on `worktree-auslieferung` (base `4de9be9`). Tree clean.

## Changes, file by file

- `src/previously/storage/migrate.py` (new): `MIGRATION_LOCK = 0x70726576`, `Migrated(before, head)`, `migrate(dsn)`. Brief's core, adapted:
  - **Reused from `storage/postgres.py`:** `from_dsn(dsn)` (→ `InvalidDsn` for an unparsable string) and the public `PostgresStorage.begin()` (→ `_transaction`'s translation: `OperationalError` → `ServerUnreachable`/`TransactionAborted`, `ProgrammingError` → `MigrationPending`), closed with `storage.close()` in `finally`. No second translation written.
  - Lock connection = `storage.begin()`; `pg_advisory_lock` first, then `MigrationContext.configure(conn).get_current_revision()` (READ COMMITTED → fresh snapshot after the lock is granted), `script.get_revision(before)` → `CommandError` → `UnknownRevision` (exact contractual wording), `if before != head: command.upgrade(config, "head")`, `finally: pg_advisory_unlock`. `command.upgrade` runs **inside** the `with`, so an `OperationalError` from Alembic's own engine (env.py) goes through the same translation.
  - `config.set_main_option("sqlalchemy.url", dsn.replace("%", "%%"))` — see *Deviation 1*.
  - `head is None` → `RuntimeError` (the one uncovered line, 75). Correction to the brief: `get_current_head()` is `None` only for a directory **without** revisions; several heads **raise** `CommandError` (read in alembic 1.20.0 source). The comment says so.
  - P-1: no `{ref}`delivery``; the module docstring states the reason (an image carries the package only, so `alembic upgrade head` beside `alembic.ini` is not there).
- `src/previously/storage/errors.py`: `UnknownRevision(StorageError)`.
- `src/previously/cli.py`: `_dsn()` extracted from `_storage` (same message `PREVIOUSLY_DSN is not set`), `_migrated_line(result)` (returns the line, so `test_docs_references` can collect it), `_cmd_migrate`, `Command("migrate", "bring the database schema up to the newest revision", _cmd_migrate)` first in `COMMANDS`.
- `src/previously/migrations/env.py` (**not in the brief's list**): `config.set_main_option("sqlalchemy.url", resolve_dsn(config).replace("%", "%%"))` with a comment — *Deviation 1*.
- `tests/test_migrate.py` (new): fixture `empty_dsn` (`CREATE DATABASE migrate_<n>` on the session container, `DROP DATABASE … WITH (FORCE)` after; the `unmigrated_engine` container was not used, because its docstring relies on every access to it failing). `HEAD` read via `ScriptDirectory`, asserted not `None`. **Six** tests: the brief's five plus `test_migrate_takes_a_password_with_a_percent_sign` (*Deviation 1*). The wrong-password test also asserts that `log` prints the identical stderr line (holds the reuse). The wrong password is drawn with `secrets.token_hex` (ruff `S105` on a literal; cause removed, no suppression).
- `tests/test_docs_references.py` (**not in the brief's list**): the `migrate` stdout block (3 lines) joined the notice blocks, and the `UnknownRevision` block is held against `_raised_patterns(storage/migrate.py, "UnknownRevision")`; the docstring's counts updated ("ten standard-error sentences, the two lines of `redact` and the three of `migrate` …, in ten blocks"). Reason: CLAUDE.md wants the messages a reference page quotes held against the code; without this the new quotes were unheld.
- `pyproject.toml`: `T201` comment thirty-three → thirty-four, plus one clause.
- `docs/reference/cli.md`: eleven subcommands; `migrate` row first in the exit-code table; section `## \`migrate\`` first: reads only `PREVIOUSLY_DSN`, no checkout/`alembic.ini`, the three stdout forms, only forward (`alembic downgrade` in a checkout, `{ref}`database-schema``), the advisory lock, the refusal with the contractual wording, one sentence without password for connection errors.
- `docs/reference/configuration.md`: `PREVIOUSLY_DSN` used by the CLI "`previously migrate` included" and `alembic` in a checkout; `migrate` reads the environment alone; escaped password characters; the `sqlalchemy.url` precedence now scoped to `alembic` in a checkout.
- `docs/how-to/add-a-migration.md`: apply with `uv run previously migrate`; `alembic revision`/`alembic downgrade` stay.
- `README.md`: "the eleven commands `migrate`, …"; "the schema as Alembic migrations inside the package, applied by `previously migrate`".
- `docs/explanation/module-boundaries.md` (**not in the brief's list**): the diagram lacked `storage --> alembic`, which `storage/migrate.py` now draws; arrow added, caption "Five" → "Six arrows leave the package", one sentence why storage reaches alembic without an edge to `migrations`. Re-measured the five `grep … | sort -u` blocks: unchanged.
- `docs/tutorials/record-your-first-event.md`: only the pytest block, per T1-a (placeholder → green run → typed whole, without `rootdir:`). `alembic upgrade head` in the tutorial left for task 5.
- `docs/how-to/restore-from-a-backup.md`: `grep` finds no schema creation there; unchanged.

## TDD evidence

RED: `uv run pytest tests/test_migrate.py -q` →
`E   ImportError: cannot import name 'UnknownRevision' from 'previously.storage.errors'` / `1 error in 0.19s`.

After module + errors, before the command: `2 failed, 4 passed` (the two CLI tests: `argument command: invalid choice: 'migrate'`).

GREEN: `uv run pytest tests/test_migrate.py -q` → `6 passed in 7.58s`.

## Mutations (each applied by script, covering tests run, restored; `git status --short` showed only intended changes afterwards)

| Mutation | Red | Green control |
|---|---|---|
| `pg_advisory_lock` line removed | `test_migrate_waits_for_a_migration_that_holds_the_lock` | the other 5 |
| the `before` check removed | `test_migrate_refuses_a_revision_it_does_not_know` | the other 5 |
| `if before != head` → `if True` (always upgrade) | **none** — `6 passed`, as the brief expected: the second run is an Alembic no-op and the output is decided by `before == head`, not by the call | — |
| `%` escape removed in `migrate.py` | `test_migrate_takes_a_password_with_a_percent_sign` | the other 5 |
| `%` escape removed in `env.py` | `test_migrate_takes_a_password_with_a_percent_sign` | the other 5 |
| lock connection via `create_engine(dsn).begin()` instead of `storage.begin()` | `test_cli_migrate_names_no_password_and_gives_one_sentence` (raw `sqlalchemy.exc.OperationalError … password authentication failed`) | the other 5 |
| page: refusal wording changed in `cli.md` | `test_the_reference_quotes_what_the_code_actually_prints` | the other 4 docs-reference tests |
| page: `up to date:` → `current:` in `cli.md` | same | same |
| code: `_migrated_line` `up to date:` → `current:` | `test_cli_migrate_prints_one_line_each_way` and the docs-reference test | 9 others |
| code: `UnknownRevision` message truncated | `test_migrate_refuses_a_revision_it_does_not_know` and the docs-reference test | 9 others |

## `previously migrate`, run as a process (`uv run previously migrate`, PostgreSQL 17 container, 2026-10-05)

```
== empty
stdout: 'migrated: (empty) -> 0004_event_blob\n'   stderr: ''   exit: 0
== second time
stdout: 'up to date: 0004_event_blob\n'   stderr: ''   exit: 0
== unknown revision (alembic_version set to 9999_future)
stdout: ''   exit: 2
stderr: 'Error: the database is at revision 9999_future, which this version of previously does not know; it knows revisions up to 0004_event_blob\n'
== wrong password (migrate, then log with the same DSN)
stdout: ''   exit: 2
stderr: 'Error: database server at postgresql+psycopg://test:***@localhost:36141/test does not answer — is PostgreSQL running there, and is it reachable from here?\n'
log: identical stderr, exit 2
== PREVIOUSLY_DSN=not-a-dsn
Error: PREVIOUSLY_DSN is not a valid connection string — something like postgresql+psycopg://user:pass@host:5432/database is expected   (exit 2)
```

Further measurements (same run):

- **Alembic's own connection failing** (role with `CONNECTION LIMIT 1`: the lock connection gets in, env.py's does not): `Error: database server at postgresql+psycopg://limrole:***@…/lim does not answer — …`, exit 2. So because `command.upgrade` runs inside `storage.begin()`, the `OperationalError` from env.py's engine is translated; outside the `with` it would be a raw traceback (not measured by mutation, and **no test holds this case**).
- **Percent-encoded password** (`p%40ss%25w`): `migrated: (empty) -> 0004_event_blob`, exit 0.
- **Role without CREATE on schema `public`** (PG 17 default for a non-owner): `Error: database schema incomplete — \`uv run alembic upgrade head\` has not run yet`, exit 2 — see concern 2.

## `T201`

33 → 34, measured with `uv run ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py --statistics` (`34	T201	print`). Comment in `pyproject.toml` updated.

## Gates (each its own command, after the tutorial block was typed)

- `uv run ruff check .` → `All checks passed!`
- `uv run ruff format --check .` → `73 files already formatted`
- `uv run pyright` → `0 errors, 0 warnings, 0 informations`
- `uv run lint-imports` → `Contracts: 6 kept, 0 broken.`
- `uv run pytest --cov --cov-report=term-missing` → `651 passed in 97.31s`; `Total coverage: 97.99%` (migrate.py 97 %, missing line 75; env.py 83 %, as before: offline branch)
- `make -C docs html` → `build succeeded.`; `make -C docs vale` → `✔ 0 errors, 0 warnings and 0 suggestions in 28 files.`; `make -C docs linkcheck` → `build succeeded.`

Tutorial block retyped from `uv run pytest`: `collected 651 items` … `651 passed in 95.23s (0:01:35)`.

## Deviations from the brief

1. **`%` in the DSN (bug in the brief's code, and pre-existing in env.py).** `Config().set_main_option("sqlalchemy.url", dsn)` raised `ValueError: invalid interpolation syntax in 'postgresql+psycopg://u:p%40ss@h/db' at position 24` — a traceback quoting the password. `env.py` then re-sets the option from `get_main_option`, which returns it unescaped, so it fails the same way even if `migrate` escapes. Both now double `%`; a sixth test holds it (both escapes measured red). This also fixes `alembic upgrade head` with such a `PREVIOUSLY_DSN`. Touches `env.py`, outside the file list.
2. A sixth test, and three files outside the list (`env.py`, `test_docs_references.py`, `module-boundaries.md`), each with the reason above.
3. Brief said `get_current_head()` is `None` on several heads; it raises there (comment written accordingly).

## Concerns

1. **The wrong-password sentence says "does not answer — is PostgreSQL running there"**, which is the existing `ServerUnreachable` text for every `OperationalError`. Same sentence as the other commands, as required, but misleading for a refused password; `migrate` is the first command an operator runs, so they will meet it first. Not changed (shared wording, outside scope).
2. **`MigrationPending` mislabels a migration failure.** `command.upgrade` runs inside `_transaction`, so a `ProgrammingError` from a revision (measured: missing CREATE privilege on `public`) becomes `database schema incomplete — \`uv run alembic upgrade head\` has not run yet` — wrong advice, from `migrate` itself. And that message in `storage/postgres.py` still names `uv run alembic upgrade head` as the operator's way, which the spec §1.1.2 replaces with `previously migrate` (program output; `tests/test_cli.py::test_a_missing_table_shows_one_sentence` asserts the old text). Neither is in task 2's file list; needs a ruling (task 5 or a fix round).
3. No test holds the translation of a failure on **Alembic's own** connection (measured once by hand, connection limit 1). A test with a `CONNECTION LIMIT 1` role would be cheap if wanted.
4. `cli` now imports `storage.migrate` and thereby `alembic` at start-up for every command (no measurement of the start-up cost taken).

---

# Fix round 1 (rulings T2-a … T2-e)

Commit `5431bbd` (on `5e5691e`). Tree clean.

Status:
- **Done:** T2-a, T2-b, T2-c, T2-e.
- **Partly done:** T2-d. Only its last point is in: a test for a failure on Alembic's own connection.
- **NEEDS_CONTEXT:** the two new sentences T2-d asks for, for a refused login and a missing database, are not implemented. See the T2-d section.

## T2-a — the lock connection in autocommit

- **`storage/postgres.py`:** new public `PostgresStorage.autocommit()`.
  - It is `_transaction` on `engine.execution_options(isolation_level="AUTOCOMMIT")`.
  - So it translates errors the same way as `begin` and `snapshot`.
  - Its docstring gives the reason.
- **`storage/migrate.py`:** `with storage.autocommit() as conn:`.
  - Taking the lock, reading the revision and releasing the lock are each a statement of their own.
  - The release runs only after success. It is no longer in a `finally`.
  - On the error path, `storage.close()` in the outer `finally` disposes the pool. That ends the session, and the lock with it.
  - So no release can hide the first error. A comment above the release says this.
- **Test** `test_cli_migrate_as_a_role_that_cannot_read_the_revision_gives_one_sentence`:
  - New `role` fixture: `CREATE ROLE … LOGIN PASSWORD <random>` before the test and `DROP ROLE` after, both raw SQL.
  - The owner migrates first. Then `migrate` runs as the fresh role, which has no SELECT on `alembic_version`.
  - Expected output, exactly: `("", "Error: the database refused the migration to 0004_event_blob: permission denied for table alembic_version\n")`, exit code 2.
  - Then `_no_lock_left` polls `pg_locks` for up to 10 s. It must find no advisory lock with `classid = 0 AND objid = MIGRATION_LOCK` in that database.
  - **RED** against `5e5691e`: `sqlalchemy.exc.InternalError: (psycopg.errors.InFailedSqlTransaction) current transaction is aborted …`. That is the reviewer's traceback.

## T2-b — new `MigrationPending` wording, and `MigrationFailed`

- **`MigrationPending`, every command** (`storage/postgres.py`):
  - New wording: `database schema incomplete — \`previously migrate\` has not run yet`.
  - A comment gives the reason.
  - The `MigrationPending` docstring in `errors.py` now names `previously migrate`.
- **New `MigrationFailed(StorageError)`** in `errors.py`:
  - `migrate.py` catches `ProgrammingError` around the revision read and around the upgrade.
  - It raises `f"the database refused the migration to {head}: {reason}"`.
  - `reason` is `diagnosis(error, "message_primary")`. If that is empty, it is the class name of the driver's exception.
  - `diagnosis(error, field)` is a new public reader of the psycopg diagnosis in `postgres.py`. `_constraint_name` now uses it too, so there is one reader.
- **Exact sentences**, measured against PostgreSQL 17:
  - `Error: the database refused the migration to 0004_event_blob: permission denied for schema public`
  - `Error: the database refused the migration to 0004_event_blob: permission denied for table alembic_version`
- **Test** `test_cli_migrate_as_a_role_that_cannot_create_names_the_reason`:
  - A role without CREATE on `public` gets the first sentence and exit code 2.
  - The lock is gone afterwards.
  - **RED** before: `Error: database schema incomplete — \`previously migrate\` has not run yet`.
- **Two tests outside the brief's file list** follow the new wording, docstrings included:
  - `tests/test_cli.py::test_a_missing_table_shows_one_sentence` now asserts the whole sentence `Error: database schema incomplete — \`previously migrate\` has not run yet`.
  - `tests/test_storage.py::test_a_missing_table_becomes_a_storage_error` now matches ``"`previously migrate`"``.
- **`docs/reference/cli.md`:**
  - Top section: a `text` block with the `MigrationPending` sentence ("Every subcommand but `migrate` needs the schema …").
  - Exit-code row for `migrate`: "the database refused to let the role read the revision or apply a migration".
  - `migrate` section: a block with the two `MigrationFailed` sentences, and one sentence each on when they occur.
  - Also in the `migrate` section: the lock is "released once its migration has committed", and "a `migrate` that fails gives it up when it closes its connection".
  - No other page quotes either message: `git grep "schema incomplete\|MigrationPending\|has not run yet"` over `docs` and `README.md`, without `docs/superpowers`, finds nothing else.
- **`tests/test_docs_references.py`** now holds three `migrate`-related blocks:
  - `UnknownRevision`: 1 line.
  - `MigrationFailed`: 2 lines.
  - `MigrationPending`: 1 line, against `postgres.py`.
  - The check moved into a helper, `_assert_raised`, because inline it pushed the test over ruff's `C901` threshold.
  - Measured with `ruff check --select C901 --config 'lint.mccabe.max-complexity = 1' tests/test_docs_references.py`: 9 at `5e5691e`, 11 with the loop inline, 10 now. The helper's docstring records this.

## T2-c — the lock is held until the upgrade has committed

- **New test** `test_migrate_holds_the_lock_until_its_upgrade_has_committed`:
  - The test takes the lock and starts two `migrate` threads.
  - It polls `pg_stat_activity` until it sees two advisory waiters, with a 10 s deadline.
  - It releases the lock and joins both threads, 30 s each.
  - It asserts no errors, and that the sorted results are `[Migrated(None, HEAD), Migrated(HEAD, HEAD)]`.
- `_waiting_on_the_lock` now returns a count instead of a flag. The single-waiter test works as before.

## T2-d — refused login and missing database: NOT implemented (NEEDS_CONTEXT)

The ruling says to read the SQLSTATE the way `TransactionAborted` does. That cannot work at connect time.

- **Measured** with psycopg 3.3.6 against PostgreSQL 17, for a wrong password, a missing database, an unknown user and nobody listening:
  - `error.orig.sqlstate`, `diag.sqlstate` and `diag.message_primary` are all `None`.
- **Why**, from the source (`psycopg/generators.py:93-98`):
  - A failed `connect_poll` raises `e.OperationalError(f"connection failed: {conn.get_error_message(encoding)}", pgconn=e.finish_pgconn(conn))`.
  - The error is built from libpq's message text only. There is no result object, so there is no SQLSTATE.
- **The only signal left is the text**, such as `FATAL:  password authentication failed for user "test"` or `FATAL:  database "nope" does not exist`.
  - That text depends on the server's `lc_messages`.
  - `postgres.py` refuses text matching for exactly that reason, in `_constraint_name`'s docstring.
  - So I did not write a matcher on it.
- **Options for a ruling:**
  - (a) Match the English server text, and fall back to today's sentence for any other language.
  - (b) Change `ServerUnreachable` for every command to "cannot connect to the database at <url with ***>: <libpq's first line>". That is honest for all three cases. It needs a check that libpq's text never contains the password; I believe it doesn't, but have not proven it.
  - (c) Leave it as it is.
- Nothing in `cli.md` or `configuration.md` changed for T2-d.
- **Done from T2-d** — test `test_cli_migrate_translates_a_failure_on_alembics_own_connection`:
  - A fresh role gets `ALTER ROLE … CONNECTION LIMIT 1`, so its lock connection gets in and `env.py`'s connection fails with `FATAL: too many connections for role`.
  - The test expects exit code 2, an empty stdout, one stderr line starting with `Error: database server at `, and no password in it.
  - No mock.

## T2-e

Nothing changed: `statement_timeout` and the import cost are deferred.

## Mutations

Each mutation was applied by a script, the covering tests run, and the file restored at once; `git status --short` showed none of them afterwards. Every run is `tests/test_migrate.py` (10 tests) unless named.

| Mutation | Red | Green control |
|---|---|---|
| T2-a: `begin()` instead of `autocommit()`, **and** the release back in a `finally` (the old shape) | `…cannot_read_the_revision…` (`InFailedSqlTransaction`) | the other 9 |
| T2-a: `autocommit()` kept, the release back in a `finally` | none, `10 passed` | — |
| T2-a: `begin()` instead of `autocommit()`, release still only after success | none, `10 passed` | — |
| T2-a: `storage.close()` removed | `…cannot_create_names_the_reason…` (the lock is still in `pg_locks` after 10 s) | the other 9 |
| T2-b: `except ProgrammingError` changed to `except ZeroDivisionError` | `…cannot_read_the_revision…`, `…cannot_create_names_the_reason…` | the other 8 |
| T2-b: `MigrationPending` back to the old wording (run: the `test_cli` case, the `test_storage` case, `test_docs_references.py`, `test_migrate.py`) | `test_a_missing_table_shows_one_sentence`, `test_a_missing_table_becomes_a_storage_error`, `test_the_reference_quotes_what_the_code_actually_prints` | 14 others |
| T2-c: release moved to just before `command.upgrade` (3 runs) | `test_migrate_holds_the_lock_until_its_upgrade_has_committed`, in 3 of 3 runs, about 68 s each | the other 9, including the single-waiter test |
| T2-d: `command.upgrade` moved out of the `with`, into the outer `finally` before `close`, still under the lock | `…translates_a_failure_on_alembics_own_connection…`, for the right reason: a raw `sqlalchemy.exc.OperationalError … too many connections for role` | 4 passed |

What the table shows:

- **T2-a rests on two things:** autocommit, and no release on the error path. Either one alone keeps the error visible, which is why the two single mutations stay green. The test catches only the removal of both together. No test holds either one separately.
- **`storage.close()`:** only one of the two lock-gone checks catches its removal. The `…cannot_read_the_revision…` test stayed green under that mutation.
- **T2-c:** the red is not the expected duplicate-table error. It is `AssertionError: migrate is hanging`: one `migrate` was still running after the two 30 s joins. Two concurrent upgrades without the lock hung rather than failed. I did not investigate the hang.
- **T2-d:** the mutation is not clean. It also turned 5 other tests red, because the mutated code leaves `pending` unbound or releases the lock early.

## TDD

- **RED** against `5e5691e`, new tests only (`uv run pytest tests/test_migrate.py -q -p no:randomly`): `2 failed, 8 passed`.
  - The read test failed with `InternalError … InFailedSqlTransaction`.
  - The create test failed with the `MigrationPending` sentence.
- The two-waiter test and the own-connection test were already green against `5e5691e`. That code already held the lock correctly and ran the upgrade inside the translation. Their red comes only from the mutations above.
- **GREEN:** `tests/test_migrate.py` plus the two `MigrationPending` tests, `12 passed in 14.37s`.

## Tutorial

The test block was retyped from a green `uv run pytest`, through a placeholder first: `collected 655 items` … `655 passed in 93.70s (0:01:33)`.

## Gates (each its own command)

- `uv run ruff check .` → `All checks passed!`
- `uv run ruff format --check .` → `73 files already formatted`
- `uv run pyright` → `0 errors, 0 warnings, 0 informations`
- `uv run lint-imports` → `Contracts: 6 kept, 0 broken.`
- `uv run pytest --cov --cov-report=term-missing` → `655 passed in 92.52s`; `Total coverage: 98.00%`. `migrate.py` is at 98 %: line 83, the `head is None` raise, is missing. `postgres.py` is at 100 %.
- `make -C docs html` → `build succeeded.`
- `make -C docs vale` → `✔ 0 errors, 0 warnings and 0 suggestions in 28 files.`
- `make -C docs linkcheck` → `build succeeded.`

## Remaining concerns

1. **T2-d sentences: NEEDS_CONTEXT**, see above. A wrong password and a missing database still print "does not answer — is PostgreSQL running there".
2. **`MigrationFailed` catches only `ProgrammingError`.** An `IntegrityError` or `InternalError` from a revision would still end as a traceback. That is deliberate, since an unknown error stays a traceback, but no ruling names it.

---

# Fix round 1b (rulings T2-f, T2-g)

Commit `3c8e506` (on `5431bbd`). The tree is clean. Status: done.

## T2-f — a failed connection says that connecting failed, and quotes libpq's reason

The new sentence, for every command, is raised in `storage/postgres.py` `_transaction`:

```
connecting to the database at <dsn with the password as ***> failed: <first line of libpq's message>
```

- **How the reason is built:** `reason = str(error.orig).partition("\n")[0].removeprefix("connection failed: ")`.
  - It is the first line only, because libpq lists every address it tried on the lines below.
  - The prefix `connection failed: ` is psycopg's, not libpq's, so it is removed.
  - `partition` never raises, even on an empty message.
  - The comment beside the code gives the reason: psycopg gives no SQLSTATE at connect time, and the text is in the server's language, so it is quoted and never matched.
- **`ServerUnreachable` docstring** is updated to match.
- `TransactionAborted` (SQLSTATE `40…`/`55P03`) is unchanged.

Samples, from `uv run previously migrate` run as a process against PostgreSQL 17 (exit code 2 and empty stdout in every case):

```
Error: connecting to the database at postgresql+psycopg://test:***@localhost:36234/test failed: connection to server at "127.0.0.1", port 36234 failed: FATAL:  password authentication failed for user "test"
Error: connecting to the database at postgresql+psycopg://test:***@localhost:36234/nope failed: connection to server at "127.0.0.1", port 36234 failed: FATAL:  database "nope" does not exist
Error: connecting to the database at postgresql+psycopg://test:***@localhost:1/test failed: connection to server at "127.0.0.1", port 1 failed: Connection refused
```

The three lines are a wrong password, a missing database, and nothing listening.

### Tests (`tests/test_cli.py`, through `main(["log"])`, against the session container)

- **`test_a_refused_password_names_libpqs_reason_and_not_the_password`**
  - The password is drawn at run time.
  - The check `secret not in out + sentence` comes first, so that a password in the output fails on that line and no other.
  - Then: empty stdout, a sentence starting with `Error: connecting to the database at <dsn with ***> failed: `, and `FATAL:  password authentication failed for user ` in it. Exit code 2.
- **`test_a_missing_database_names_libpqs_reason`**
  - The same start of the sentence, with `FATAL:  database "no_such_database" does not exist` in it. Exit code 2.
- **`test_an_unreachable_server_shows_one_sentence`** (extended; `localhost:1`, nothing listening)
  - Still one sentence, `SECRET123` absent, and `verify` gives the identical line.
  - Now also: the sentence starts with `Error: connecting to the database at postgresql+psycopg://user:***@localhost:1/db failed: connection to server at `, and contains `Connection refused`.
- **`tests/test_migrate.py::test_cli_migrate_translates_a_failure_on_alembics_own_connection`** now expects `Error: connecting to the database at ` and `too many connections for role`.

### Documentation

- **`docs/reference/cli.md`, top section:** a paragraph and a `text` block quoting the three cases, with a sample DSN, and one sentence on which case is which.
  - The `migrate` section's list of connection errors now also names "a database that doesn't exist".
  - The old sentence was quoted nowhere: `git grep "does not answer"` over `docs` found it on no page.
- **`docs/reference/configuration.md`:** one sentence under *Database*, pointing to the reference: a refused password, a missing database or an unreachable server each give one sentence that quotes the reason, without the password.
- **`tests/test_docs_references.py`:** the block after "When connecting to the database fails" (3 lines) is now held against `ServerUnreachable` in `storage/postgres.py`.
  - The comment and the docstring name it.
  - The complexity of `test_the_reference_quotes_what_the_code_actually_prints` is still 10, so the helper's docstring stays true. Measured with the command it names.

## T2-g — `MigrationFailed` for every database error but a failed connection

- **`storage/migrate.py`:** `except DBAPIError as error:` around the revision read and the upgrade.
  - An `OperationalError` is re-raised unchanged, so `_transaction` translates it as a connection failure, or as `TransactionAborted`.
  - Every other database error becomes `MigrationFailed`, with the same wording as before: `the database refused the migration to <head>: <server's message_primary>`.
  - The `MigrationFailed` docstring is updated to match.
- **Test** `test_cli_migrate_names_the_reason_of_an_error_that_is_no_programming_error`:
  - Setup: an event trigger in the empty database, `ON ddl_command_start`, whose function runs `RAISE EXCEPTION 'no schema changes in this database' USING ERRCODE = 'XX000'`.
  - Expects `("", "Error: the database refused the migration to 0004_event_blob: no schema changes in this database\n")`, exit code 2, and the lock gone afterwards.
  - It uses `XX000`, not the default `P0001`, for a measured reason: psycopg 3.3.6 files `P0001` (`RaiseException`) under `ProgrammingError`, and the first version of this test passed against the `ProgrammingError`-only code. `XX000` is filed under `InternalError`.
  - **RED** against `5431bbd`: `sqlalchemy.exc.InternalError: (psycopg.errors.InternalError_) no schema changes in this database`, a traceback.

## TDD

- **RED** against `5431bbd` (old sentence), with the new and changed tests:
  - the password test, the missing-database test, the unreachable-server test and the own-connection test all failed on the start of the sentence, which was `database server at … does not answer — …`;
  - the event-trigger test failed with the `InternalError` traceback.
- **GREEN:** `tests/test_migrate.py`, `tests/test_cli.py` and `tests/test_storage.py`, `189 passed`. The three CLI connection tests: `3 passed`.

## Mutations (each applied by script and restored; the tree had none of them afterwards)

Every run covers `tests/test_migrate.py` (11 tests), `tests/test_docs_references.py` (5) and the three CLI connection tests, 19 tests in all.

| Mutation | Red | Green control |
|---|---|---|
| libpq's line dropped: `…failed: {reason}"` → `…failed"` | the password, missing-database and unreachable tests, the own-connection test, and `test_the_reference_quotes_what_the_code_actually_prints` | 14 passed |
| password into the message: `hide_password=True` → `False` | the password test, red on `assert secret not in out + sentence`; also `test_cli_migrate_names_no_password_and_gives_one_sentence`, the own-connection test, the missing-database and unreachable tests (prefix with the password) | 14 passed |
| `except DBAPIError` → `except ProgrammingError` | `test_cli_migrate_names_the_reason_of_an_error_that_is_no_programming_error` | 18 passed |
| the `OperationalError` re-raise removed | the own-connection test (it became `MigrationFailed … OperationalError`) | 18 passed |

The password mutation was rerun on the password test alone, after the assertions were reordered. It failed on `assert 'wrong-…' not in 'Error: conn…'`.

## Tutorial

The test block was retyped from a green `uv run pytest`, through a placeholder first: `collected 658 items` … `658 passed in 96.58s (0:01:36)`.

## Gates (each its own command)

- `uv run ruff check .` → `All checks passed!`
- `uv run ruff format --check .` → `73 files already formatted`
- `uv run pyright` → `0 errors, 0 warnings, 0 informations`
- `uv run lint-imports` → `Contracts: 6 kept, 0 broken.`
- `uv run pytest --cov --cov-report=term-missing` → `658 passed in 93.15s`; `Total coverage: 98.00%`. `migrate.py` is at 98 %, with only line 84, the `head is None` raise, uncovered; `postgres.py` is at 100 %.
- `make -C docs html` → `build succeeded.`
- `make -C docs vale` → `✔ 0 errors, 0 warnings and 0 suggestions in 28 files.`
- `make -C docs linkcheck` → `build succeeded.`

## Concerns

1. **Not every `OperationalError` is a failed connection.** `ServerUnreachable` still covers every one whose SQLSTATE is not `40…`/`55P03`. One that arrives after connecting, such as `statement_timeout` (57014), now reads "connecting to the database … failed: canceling statement due to statement timeout". The quoted reason is right, but "connecting" is not. This belongs with the deferred T2-e point.
2. **The quoted reason is in the server's language** (and the operating system's, for `Connection refused`). The tests assert the English texts of the `postgres:17` container. A server with another `lc_messages` would print other words, which is intended.

---

# Fix round 2 (ruling T2-h)

Commit `fa61473`, on top of `3c8e506`. The tree is clean, and every point below is done.

## Point 1 — a message names only database, host and port

I searched with `git grep -n "render_as_string\|\.url\b\|dsn" -- src`. Of the places that could put a DSN or a part of one into a message, one did and one could:

1. **`storage/postgres.py` `_transaction`.** The address was `engine.url.render_as_string(hide_password=True)`, which hides only a password written as `user:password@`. This was the leak.
2. **`storage/postgres.py` `from_dsn` (`InvalidDsn`).** Its message is a fixed text and names no piece of the DSN. It is unchanged, and the new check for a second `@` (point 2) sits beside it.

The other places hand the DSN on without printing it:

- `cli.py` reads it from the environment.
- `storage/migrate.py` passes it to Alembic's `Config`, escaped since round 1.
- `migrations/env.py` and `dsn.py` resolve it; the `RuntimeError` in `dsn.py` names the variable, not its value.

The fix is a new function in `postgres.py`, `_where(url)`. It returns `database <db> at <host>:<port>` from the parsed URL. A missing part reads `(default)`, `(default host)`, or the port is left out. The user part and the query are never read. A comment beside it records the leak, measured on 2026-10-05.

The connection sentence for every command is now:

```
connecting to database <db> at <host>:<port> failed: <first line of the reason>
```

## Point 2 — a second `@` is refused before anything connects

`from_dsn` counts the `@` in everything after `://` and before the first `?`. If there is more than one, it raises `InvalidDsn` before `create_engine`, so before any connection attempt:

```
PREVIOUSLY_DSN holds more than one `@` before the host — a password with special characters has to be percent-encoded, such as `%40` for `@`
```

- **Why the count runs up to the query:** SQLAlchemy's grammar lets a password hold a `/`, so `a@b/c@host` leaks the same way. A comment beside the check says this.
- **Known false refusal:** a database name that contains an `@` is refused too. I did not measure whether such a name can be written as `%40` instead.
- **`migrate` is covered:** it calls `from_dsn` before it opens any connection. Alembic's `Config` sees the string earlier, but prints nothing.

## Point 4 — the reviewer's minors

- **The lock statement:** `pg_advisory_lock` now sits inside the `try` that turns a database error into `MigrationFailed`. A comment says why.
- **An error with a SQLSTATE gets its own sentence.** In `_transaction`, an `OperationalError` whose SQLSTATE starts with `40` or is `55P03` stays `TransactionAborted`. Any other one that carries a SQLSTATE becomes the new `OperationFailed` (in `errors.py`), with the server's `message_primary`, or the SQLSTATE if that is empty:
  ```
  the operation on database <db> at <host>:<port> failed: <reason>
  ```
  Only an `OperationalError` with no SQLSTATE says "connecting … failed". psycopg gives none to a failure to connect: measured in round 1, and the comment says so. The docstrings of `ServerUnreachable` and `OperationFailed` say the same.
- **Where the reason line comes from** (`cli.md`, as the reviewer measured):
  - It is the first line of the driver's (`psycopg`) message, without the driver's own `connection failed: `.
  - Most of it comes from `libpq`: `connection to server at …` and an operating-system reason such as `Connection refused` come from the client, in the client's locale. What follows `FATAL:` comes from the server, in the server's language.
  - Some reasons are the driver's own text, such as `failed to resolve host '…'`.
  - `psycopg` and `libpq` stand in backticks, because `vale` does not know either word.
- **The line break** at `tests/test_docs_references.py:476` is fixed. The docstring now also lists the new blocks.

## Point 5 — the pages

**`cli.md`, top section:**
- A sentence states the rule: a message about the database names the database, the host and the port from `PREVIOUSLY_DSN`, and not the user, not the password, not the query.
- The three connection samples are retyped in the new form, with the provenance described above.
- A new block quotes the `OperationFailed` sentence, and another the refusal of a second `@`.

**`cli.md`, `migrate` section:** it now says "naming only database, host and port" where it said "without the password".

**`configuration.md`:** it states the same rule, says that a failed connection quotes the first line of the reason and points to the reference for where that line comes from, and says that a second `@` is refused before anything connects. The claim "without the password" is gone, and `***` appears nowhere.

**`tests/test_docs_references.py`:** the error loop now also holds the `OperationFailed` block (1 line) and the second-`@` block (1 line, against `InvalidDsn` in `postgres.py`). The test's `C901` complexity is still 10, so the claim in the helper's docstring still holds.

## Samples

From `uv run previously migrate` run as a process against PostgreSQL 17. Each case gave exit code 2, an empty stdout, and one stderr line:

```
password wrong (user:password@):  Error: connecting to database test at localhost:36283 failed: connection to server at "127.0.0.1", port 36283 failed: FATAL:  password authentication failed for user "test"
password wrong (?password=):      Error: connecting to database test at localhost:36283 failed: connection to server at "127.0.0.1", port 36283 failed: FATAL:  password authentication failed for user "test"
database missing:                 Error: connecting to database nope at localhost:36283 failed: connection to server at "127.0.0.1", port 36283 failed: FATAL:  database "nope" does not exist
nothing listening:                Error: connecting to database test at localhost:1 failed: connection to server at "127.0.0.1", port 1 failed: Connection refused
unencoded @ (test:Wrong@Pw4711@…): Error: PREVIOUSLY_DSN holds more than one `@` before the host — a password with special characters has to be percent-encoded, such as `%40` for `@`
```

From the test, a statement timeout of 500 ms on the database while the test holds the lock:

```
Error: the operation on database migrate_N at localhost:PORT failed: canceling statement due to statement timeout
```

From the test, a role that may not call `pg_advisory_lock` (`REVOKE EXECUTE … FROM PUBLIC`):

```
Error: the database refused the migration to 0004_event_blob: permission denied for function pg_advisory_lock
```

## Tests

**`tests/test_cli.py`, against the session container:**

- **Shared helpers:**
  - `_wrong_password()` draws `Wrong<24 hex>Pw` at run time; letters at both ends keep a port or a count from looking like a piece of it.
  - `_no_fragment_of(secret, output)` checks that no 8 characters in a row of the password stand in the output.
  - The check for fragments runs first in every password test.
- **`test_a_refused_password_names_libpqs_reason_and_not_the_password`** (`user:password@`, rewritten): no fragment in stdout or stderr; the sentence starts with `Error: connecting to database <db> at <host>:<port> failed: ` and holds the `FATAL:` reason.
- **`test_a_password_in_the_query_is_not_printed`** (new, `?password=`): no fragment; the same start and the same reason.
  - **RED** at `3c8e506`: the sentence held `…/test?password=Wrong…Pw` in clear.
- **`test_a_password_with_an_unencoded_at_sign_is_refused_before_connecting`** (new, `user:<pw1>@<pw2>@host`): no fragment of either part; the exact refusal sentence; an empty stdout.
  - **RED** at `3c8e506`: the host `Wrong…Pw@localhost` was printed, and so was the reason `failed to resolve host 'Wrong…Pw@localhost'`.
- **`test_a_missing_database_names_libpqs_reason`** and **`test_an_unreachable_server_shows_one_sentence`:** rewritten to the new form.
  - The unreachable test still asserts one sentence, `SECRET123` absent, and the same line from `verify`.

**`tests/test_migrate.py`:**

- **`test_cli_migrate_names_an_error_after_connecting_as_one_of_the_operation`** (new): `ALTER DATABASE … SET statement_timeout = '500ms'`; the test holds the lock; `migrate` waits and is cancelled with SQLSTATE `57014`. It expects the exact `OperationFailed` sentence.
  - **RED** at `3c8e506`: `connecting to the database at …` was printed.
- **`test_cli_migrate_as_a_role_that_may_not_take_the_lock_names_the_reason`** (new): the database revokes `EXECUTE` on `pg_advisory_lock(bigint)` from `PUBLIC`, and `migrate` runs as a fresh role. It expects the exact `MigrationFailed` sentence.
  - **RED** at `3c8e506`: `database schema incomplete — \`previously migrate\` has not run yet`.
- **`test_cli_migrate_translates_a_failure_on_alembics_own_connection`:** updated to `Error: connecting to database <db> at <host>:<port>`.

## Mutations

Each mutation was applied by a script, and the file was restored at once. Each run covered 23 tests: `tests/test_migrate.py` (13), `tests/test_docs_references.py` (5), and the five connection tests of `test_cli.py`.

| Mutation | Red | Green control |
|---|---|---|
| The query printed again: `_where` appends `?k=v…` when the URL has a query | `test_a_password_in_the_query_is_not_printed` only, on `_no_fragment_of` | 22 passed |
| The check for a second `@` dropped (`> 1` changed to `> 99`) | `test_a_password_with_an_unencoded_at_sign_is_refused_before_connecting` only (it printed `…at Wrong…Pw@localhost:…`) | 22 passed |
| `pg_advisory_lock` moved back before the `try` | `test_cli_migrate_as_a_role_that_may_not_take_the_lock_names_the_reason` only | 22 passed |
| SQLSTATE split taken out (`if isinstance(state, str)` changed to `if False`) | `test_cli_migrate_names_an_error_after_connecting_as_one_of_the_operation` only (it printed `connecting to database … failed: canceling statement …`) | 22 passed |

A first version of the query mutation appended `?` even to a URL without a query. It turned five tests red, the query test among them for the right reason. The version in the table appends only when a query exists, so only the query test goes red.

## Tutorial

The test block was retyped from a green `uv run pytest`, through a placeholder: `collected 662 items` … `662 passed in 103.45s (0:01:43)`.

## Gates (each its own command)

- `uv run ruff check .` → `All checks passed!`
- `uv run ruff format --check .` → `73 files already formatted`
- `uv run pyright` → `0 errors, 0 warnings, 0 informations`
- `uv run lint-imports` → `Contracts: 6 kept, 0 broken.`
- `uv run pytest --cov --cov-report=term-missing` → `662 passed in 99.61s`; `Total coverage: 98.01%`. `postgres.py` is at 100 %. `migrate.py` is at 98 %, missing line 85, the `head is None` raise.
- `make -C docs html` → `build succeeded.`
- `make -C docs vale` → `✔ 0 errors, 0 warnings and 0 suggestions in 28 files.`
- `make -C docs linkcheck` → `build succeeded.`

## Concerns

1. **A database name that contains `@` is refused** by the check for a second `@`. I did not measure whether `%40` works there.
2. **Other parsing errors were not probed.** `create_engine` can raise a `ValueError` for a non-numeric port, and that comes out as a traceback that would name the port. No password piece was seen in any probe, but I did not probe this beyond the cases above.

---

# Fix round 3 (ruling T2-i)

Commit `2579eb5`, on top of `fa61473`. The tree is clean. Status: done.

One addition to the ruling: the round trip alone does not close the leak, because SQLAlchemy writes the host back unescaped. Two structural checks on the parsed parts sit beside it: the host holds no `@`, and the port is at most 65535. Measurement and reason are below.

## Point 2 — the equivalences, measured first

Measured with SQLAlchemy 2.1.2 (`make_url(dsn).render_as_string(hide_password=False)`). Probe scripts: `scratchpad/roundtrip.py` and `scratchpad/equiv.py`.

**What the rendering does to each part:**
- **User name and password:** it escapes `@ : / ? # % & = ! $ ' ( ) * , ;` as `%XX` in upper case. It writes `~`, `+`, a space and letters as they are, and decodes `%7E` and `%41`.
- **Database:** it escapes `@`.
- **Host:** it writes the host as it is, `@` included.
- **Query:** it writes the query with `quote_plus` (space as `+`, `/` as `%2F`, `@` as `%40`), with the keys sorted.

**What has to be normalized on both sides** for an equivalent string to compare equal:
- **Outside the query:** decode every `%XX` except those of the separators `@ : / ? # [ ] %`. Keep those as they are, in upper case. This is `_unescaped`, built on `urllib.parse.unquote`, so UTF-8 sequences decode whole.
- **The query:** compare it as `sorted(parse_qsl(…))` on both sides. SQLAlchemy reads it with the same `parse_qsl`.

**The raw comparison against the normalized one:**

| Equivalence | raw `==` | normalized |
|---|---|---|
| `%40` written, `%40` rendered | same | accepted |
| lower-case `%3a%2f` | differs | accepted |
| `%7E` for `~` | differs | accepted |
| `%41` for `A` | differs | accepted |
| `%20` for a space | differs | accepted |
| raw `&`, raw `!$'()*,;` in the password | differs | accepted |
| query keys out of order | differs | accepted |
| query `%20` against `+` | differs | accepted |
| query value with a raw `/` | differs | accepted |
| repeated query key | same | accepted |
| IPv6 in brackets, with and without a port | same | accepted |
| no port, no database, no host | same | accepted |
| UTF-8 password, raw and encoded | differs, same | accepted |
| `%2B` for `+` | differs | accepted |

**Where the round trip is not enough:**
- **Plain `app:x@y@localhost` comes back unchanged**, because the host is written as it is, here `y@localhost`. So the round trip alone accepts the reviewer's two-`@` form (14).
- **The added check:** `"@" not in url.host`. A host never holds an `@`. This is a check on what the parser produced, not a count over the raw text.
- **The reviewer's reasoned all-digit case:** `app:<20 digits>/probe` comes back unchanged too, as host `app` and port `<digits>`.
- **The added check:** `port <= 65535`. A password of five digits or fewer, with the `@host` forgotten, stays indistinguishable from `host:port/db`, and is still printed as the port. That is noted as a concern below.

## Point 1 — `from_dsn`

New code in `storage/postgres.py`:
- `_read_as_written(dsn)` does the comparison and the two checks.
- `_unescaped(text)` normalizes one side.
- `_unreadable()` returns the one `InvalidDsn`. It is a function so that the call carries the text where `test_docs_references` reads it.
- `from_dsn` refuses when `_read_as_written` is false. It also wraps `create_engine` in `except (ArgumentError, ValueError)`, which ends in the same sentence. The count of `@` is gone.

The sentence, the same for every refusal, with no part of the DSN in it:

```
PREVIOUSLY_DSN cannot be read as written — something like postgresql+psycopg://user:password@host:5432/database is expected, and a special character in the user name, the password, the database name or a query value has to be percent-encoded, such as `%40` for `@`
```

The comment about `a@b/c@host`, whose mechanism the reviewer refuted, went with the count. The docstring of `_read_as_written` makes no claim about that form.

## Point 4 — the small findings

- **The pages say what they can promise.**
  - On `cli.md`: the sentence's own words name only database, host and port. The quoted reason can name the user and quote the value of a query parameter the client library rejects, such as an `sslmode` it doesn't know. The password appears in neither.
  - `configuration.md` says the same, and that a special character in user, password, database or query value stands as its escape sequence, or the string is refused before anything connects.
  - The refusal block on `cli.md` is replaced. It quotes the new sentence and says how `previously` decides.
- **`@` in a user name:** it is covered by the new sentence, which names the user name. Form 20 is refused, and form 21 (`%40`) is accepted.
- **A rejected query key or value no longer makes `migrate` recommend itself.**
  - `_transaction` sets `connected` once `engine.begin()` has entered. A `ProgrammingError` before that, raised by psycopg while connecting, now becomes the connection sentence, `connecting to database <db> at <host>:<port> failed: <first line>`, via a new helper `_first_line`.
  - Measured, through `migrate` and `log`:
    - `invalid connection option "passwrod"`
    - `bad value for connect_timeout: 'abc'`
    - `connection is bad: invalid sslmode value: "bogus"` (that one was an `OperationalError` already).
  - **Why this and not one of the ruling's two sentences:** the error comes while connecting, before the server is asked anything. So `OperationFailed` ("the operation on …") would be untrue. The string itself was read as written, so the `InvalidDsn` sentence would be untrue too. "connecting … failed" is the true one.
  - New test `tests/test_migrate.py::test_cli_migrate_with_an_unknown_query_key_does_not_advise_itself` expects the exact sentence. Forms 5 and 10 of the table hold the same through `log` and `migrate`.

## Point 3 — the table test

`tests/test_cli.py::test_no_form_of_the_connection_string_prints_the_password` is parametrized over the 38 forms and one more, each through `log` and `migrate`: 78 cases.

- **The pieces:** `{A}`, `{B}`, `{C}` are 20 hexadecimal characters each, and `{D}` is 20 digits, all drawn at run time. The specials sit between them in the forms, as in the reviewer's probe.
- **The checks:**
  - `refused`: exit code 2, empty stdout, and exactly the sentence.
  - `connect`: exit code 2, empty stdout, and one stderr line starting `Error: connecting to `.
  - `traceback` (form 28 only): `ModuleNotFoundError`.
  - In every case, no 8-character run of a listed piece appears in stdout, stderr or the formatted traceback.
- **`_no_fragment_of`** now asserts `len(secret) >= 8`.
- The old single test for an unencoded `@` is removed, since the table covers it.

| # | form (`<PW>` pieces as `<A>` `<B>` `<C>` `<D>`) | outcome now | at `fa61473` |
|---|---|---|---|
| 01 | `app:<A>@host/probe` | connect, clean | same |
| 02 | `app:<A>%40%3A%2F%3F%23<B>@host/probe` | connect, clean | same |
| 03 | `app@host/probe?password=<A>` | connect, clean | same |
| 04 | `app@host/probe?password=<A>@<B>` | **refused** | leaked `<B>` (host) |
| 05 | `?passwrod=<A>` | connect: `invalid connection option "passwrod"` | `MigrationPending`, self-advice |
| 06 | `?passfile=/tmp/<A>` | connect, clean | same |
| 07 | `?sslpassword=<A>` | connect, clean | same |
| 08 | `?sslpassword=<A>&sslkey=…&sslmode=require` | connect, clean | same |
| 09 | `?sslmode=bogus` (no password; the value is quoted) | connect | same |
| 10 | `?connect_timeout=abc` (no password) | connect: `bad value for connect_timeout: 'abc'` | `MigrationPending` |
| 11 | `?options=-c%20foo%3D<A>` | connect, clean | same |
| 12 | libpq key/value `… password=<A>` | refused | refused (other sentence) |
| 13 | `postgresql://app:<A>@host/probe` | connect, clean | same |
| 14 | `app:<A>@<B>@host/probe` | refused (`@` in host) | refused (count) |
| 15 | `app:<A>@<B>/<C>@host/probe` | refused | refused (count) |
| 16 | `app:<A>?<B>@<C>@host/probe` | **refused** | leaked `<C>` (host) |
| 17 | `app:<A>?x@<B>:<C>@host/probe` | **refused** | leaked `<C>` (traceback) |
| 18 | `app:<A>@host/pro@be` | refused | refused (count) |
| 19 | `app:<A>@host/pro%40be` | connect, clean | same |
| 20 | `app@corp:<A>@host/probe` | refused | refused (count) |
| 21 | `app%40corp:<A>@host/probe` | connect, clean | same |
| 22 | `app:<A>@localhost:54x32/probe` | refused | traceback |
| 23 | `app:<A>/probe` | **refused** | leaked `<A>` (traceback) |
| 24 | `app:<A>` | **refused** | leaked `<A>` (traceback) |
| 25 | `app:<A>:host/probe` | **refused** | leaked `<A>` (traceback) |
| 26 | `postgres://app:<A>@host/probe` | refused | refused (old sentence) |
| 27 | `postgresql+nope://…` | refused | refused (old sentence) |
| 28 | `postgresql+psycopg2://…` | traceback `ModuleNotFoundError`, clean | same; broken anyway (driver not installed) |
| 29 | `postgresql+psycopg:app:<A>@<B>@host/probe` | refused | refused (old sentence) |
| 30 | `app:<A>@[::1]:port/probe` | connect, clean | same |
| 31 | `app:<A>@localhost:1/probe` | connect, clean | same |
| 32 | `app:<A>@no-such-host.invalid/probe` | connect, clean | same |
| 33 | `app:<A>%zz<B>@host/probe` | refused | connect, clean; now refused, since `%` itself has to be `%25` |
| 34 | `app:<A>#<B>@host/probe` | refused | connect, clean; now refused (`#` unescaped) |
| 35 | `app:<A> <B>@host/probe` | connect, clean | same |
| 36 | `app:<A>\n<B>@host/probe` | connect, clean | same |
| 37 | `app@host/probe?password=<A>&<B>` | connect, clean | same |
| 38 | ` postgresql+psycopg://app:<A>@<B>@host/probe` | refused | refused (count) |
| 39 | `app:<D>/probe` (20 digits, not in the review) | refused (port > 65535) | (not run) |

- **Forms that were clean and are now refused:** 33 and 34. Both are refused only because a `%` or `#` stands unescaped. The sentence says what to do.
- **The one form broken anyway:** 28.
- **RED at `fa61473`:** the table measured `40 failed, 36 passed`, run against the committed `postgres.py` swapped in and restored at once; form 39 was not yet in the table. The 40 that failed are 4, 5, 10, 12, 14–18, 20, 22–27, 29, 33, 34 and 38, each through both commands.
  - Some failed for the new sentence alone: 12, 14, 15, 18, 20, 26, 27, 29 and 38 were refused at `fa61473` too, in the old wording.
  - The leaks: 4, 16, 17 and 23–25.

## Mutations

Each mutation was applied by a script and restored at once; `git status` afterwards showed only the intended changes. Every run covered `tests/test_cli.py`, `test_migrate.py`, `test_storage.py` and `test_docs_references.py`, 276 tests.

| Mutation | Red | Green control |
|---|---|---|
| compare without normalization (`rendered == dsn`) | forms 6, 8, 11, 36, 37 (both commands), and `test_migrate_takes_a_password_with_a_percent_sign` | 265 passed |
| skip the comparison (`True`; host and port checks kept) | forms 4, 15, 18, 20, 33, 34 (both commands); 4 and 15 print password pieces in the host | 264 passed |
| catch only `ArgumentError`, in `_read_as_written` and `from_dsn` | forms 17, 22, 23, 24, 25 (both commands), as tracebacks | 266 passed |
| the host check for `@` dropped | form 14 (both commands): `… at <B>@localhost:… failed to resolve host '<B>@localhost'` | 274 passed |
| the port check dropped | form 39 (both commands): `… at app:<D> failed …` | 274 passed |
| the connect-time `ProgrammingError` branch off | forms 5 and 10 (both commands), and `test_cli_migrate_with_an_unknown_query_key_does_not_advise_itself` (it printed `MigrationPending` again) | 271 passed |

## Tutorial

The test block was retyped from a green `uv run pytest` run through a placeholder: `collected 740 items` … `740 passed in 96.61s (0:01:36)`.

## Gates (each its own command)

- `uv run ruff check .` → `All checks passed!`
- `uv run ruff format --check .` → `73 files already formatted`
- `uv run pyright` → `0 errors, 0 warnings, 0 informations`
- `uv run lint-imports` → `Contracts: 6 kept, 0 broken.`
- `uv run pytest --cov --cov-report=term-missing` → `740 passed in 96.34s`; `Total coverage: 98.04%`
  - `postgres.py`: 100 %.
  - `migrate.py`: 98 %; line 85, the `head is None` raise, is the one not covered.
- `make -C docs html` → `build succeeded.`
- `make -C docs vale` → `✔ 0 errors, 0 warnings and 0 suggestions in 28 files.`
- `make -C docs linkcheck` → `build succeeded.`

## Concerns

1. **A password of five digits or fewer, with `@host` forgotten** (`user:12345/db`), is indistinguishable from `host:port/db`, and is still printed as the port. No check on the parse can tell them apart.
2. **The round trip rests on SQLAlchemy 2.1.2's rendering.** A release that renders differently would refuse or accept other strings. The table test would show which, since it runs all 39 forms.
3. **Form 28 (a driver not installed) is still a traceback.** It carries no DSN content, measured, and is left as it was.
4. **The table adds 78 test cases.** The suite went from 662 to 740 tests, at about the same run time.
5. **ruff format rewrote** `except (ArgumentError, ValueError):` in `_read_as_written` as `except ArgumentError, ValueError:` (PEP 758, Python 3.14). The mutation script uses that spelling.

---

# Fix round 4 (ruling T2-k)

The commit sits on top of `2579eb5`, and the reply gives its hash. Status: done, with the residuals named at the end.

## The grammar

The grammar is `_DSN` in `storage/postgres.py`, matched with `fullmatch` against the whole string. SQLAlchemy never parses the operator's string any more: `_url_of` builds the URL with `URL.create` from the parts the grammar names, and `from_dsn` calls `create_engine(url)`.

```
ESCAPE = %(?:[2-6][0-9A-Fa-f]|7[0-9A-Ea-e]|[89A-Fa-f][0-9A-Fa-f])     # any byte but a control (00-1F, 7F)
PART   = [A-Za-z0-9-._~!$'()*+,;=] | ESCAPE                          # unreserved, sub-delims without &
VALUE  = [A-Za-z0-9-._~/] | ESCAPE                                   # no & = + in a query value

(postgresql|postgresql\+psycopg)://
(PART+ (: PART*)? @)?                                   # user, optional password
([A-Za-z0-9_.-]+ | \[[0-9A-Fa-f:.]+\])                  # host name or IPv6 in brackets (required)
(: [0-9]{1,5})?                                         # port, then 1 <= port <= 65535 in code
(/ PART*)?                                              # database; empty means none
(\? [a-z_]+=VALUE+ (& [a-z_]+=VALUE+)*)?                # query
```

The code checks three things after the match:
- the port lies in 1..65535;
- every query key is in `DSN_QUERY_KEYS`, and none appears twice;
- the user, the password, the database and the values decode with `unquote(errors="strict")`, so an escape that is not UTF-8 is refused.

Each departure from the ruling's wording is deliberate:
- **`_` in the host name.** docker-compose service names may hold `_` (the compose spec allows `[a-zA-Z0-9._-]`), and compose is the second way of hosting. An `_` cannot create a second reading, because it separates nothing.
- **No control-character escapes.** Measured with psycopg 3.3.6: a NUL in the user, the password or the database cut the connection parameters short. The port given with them was lost, and the client went to 5432. A newline in the database name splits the one-line message (review round 3, N22).
- **No raw `&`, `=` or `+` in a query value.** `&` and `=` cut the pairs, and `+` reads as a space (C07 of review round 3).
- **A non-empty user whenever there is a user part.** `:pw@host` is refused.

### The query allow-list (`DSN_QUERY_KEYS`, public, held against the sentence by a test)

| Key | Reason |
|---|---|
| `sslmode`, `sslrootcert`, `sslcert`, `sslkey` | TLS to the server and a client certificate, which kup6s/CloudNativePG offers |
| `channel_binding`, `require_auth` | keep the password from a server that should not get it |
| `connect_timeout` | how long a migration job waits for a server that is starting |
| `application_name` | a name in `pg_stat_activity` |

Left out on purpose:
- `password`, because T2-k puts the password in the user part only;
- `sslpassword` and `passfile`, a secret and a second place for one;
- `host`, `hostaddr`, `port`, `dbname` and `user`, which would overrule the authority;
- `options` and `service`, which hand over server settings or read them from a file;
- SQLAlchemy's `plugin`, which loads code.

## What was removed, and why

- **The round trip and the two checks of round 3.** That is `_read_as_written`, `_unescaped` and `_SEPARATOR_ESCAPE`, with the check for `@` in the host and the port check up to 65535. They are redundant: SQLAlchemy no longer parses the string, so there is no parse to compare with. The host's character class does the host check. The port check is `[0-9]{1,5}` plus `1 <= port <= 65535`, which also closes N09 (a negative port) and an empty port.
- **`except (ArgumentError, ValueError)` around `create_engine`.** `create_engine(url)` gets a URL object with a known scheme, and nothing left there parses text. The grammar now refuses form 28 (`psycopg2`), with no traceback.
- **`migrate` handing the string to Alembic.**
  - `Config.set_main_option("sqlalchemy.url", dsn.replace("%", "%%"))` is gone from `migrate`.
  - The upgrade runs on a second connection out of the same storage (`storage.begin()`). `migrate` hands it to `env.py` as `config.attributes["connection"]`, and `env.py` uses it when present.
  - So SQLAlchemy doesn't parse the operator's string on Alembic's side either, and Alembic's `%` interpolation is out of the path.
  - The two refusal translations in `migrate` are now one context manager, `_refusals(head)`. It wraps the lock and the read, and sits inside `storage.begin()` around the upgrade. It has to be inside, so that a `ProgrammingError` from a revision becomes `MigrationFailed` and not `MigrationPending`.
  - `env.py` keeps its `%%` escape for `alembic` in a checkout.
- **The libpq quote in the connect-time `ProgrammingError` branch.** That branch now gives a fixed reason: `connecting to <db> at <host>:<port> failed: the client library refused a query parameter of PREVIOUSLY_DSN`.

## The refusal sentence (exact)

```
PREVIOUSLY_DSN is refused — write it as postgresql://user:password@host:5432/database with the password there and nowhere else, percent-encode every character of the user name, the password and the database name that is not a letter, a digit or one of -._~!$'()*+,;= (such as `%40` for `@`), and use no query parameter but application_name, channel_binding, connect_timeout, require_auth, sslcert, sslkey, sslmode or sslrootcert
```

`tests/test_storage.py::test_the_refusal_lists_the_query_keys_from_dsn_accepts` holds the keys the sentence lists equal to `DSN_QUERY_KEYS`, and checks that each one is accepted.

## The table (`tests/test_cli.py::test_no_form_of_the_connection_string_prints_the_password`)

The table runs 58 forms through `log` and through `migrate`, 116 cases.
- **The password pieces:** `<A>`, `<B>`, `<C>` and `<E>` are 20 hexadecimal characters each, and `<D>` is 20 digits, all drawn at run time. `{H}` is the session server.
- **Every case:** exit code 2, an empty stdout, and no run of 8 characters of a listed piece in stdout or stderr. That last check comes first.
- **The outcomes:** `refused` means exactly the sentence; `connect` means one line that starts with `Error: connecting to `.
- `_no_fragment_of` asserts `len(secret) >= 8`.
- Each row carries its reason as a fifth field, which the assertion messages print.

The column "At 2579eb5" is the new table run against `postgres.py` and `migrate.py` of `2579eb5`, swapped in and restored at once: 90 failed and 26 passed. The cases marked LEAK failed on the fragment check.

| # | form | now | at 2579eb5 |
|---|---|---|---|
| 01 | `app:<PW>@{H}/probe` | connect, clean | same |
| 02 | `app:<A>%40%3A%2F%3F%23<B>@…` | connect, clean | same |
| 03 | `app@…/probe?password=<PW>` | **refused** (key `password`) | connect |
| 04 | `?password=<A>@<B>` | refused | refused (old sentence) |
| 05 | `?passwrod=<PW>` | refused (key) | connect |
| 06 | `?passfile=/tmp/<PW>` | refused (key) | connect |
| 07 | `?sslpassword=<PW>` | refused (key) | connect |
| 08 | `?sslpassword=…&sslkey=…&sslmode=require` | refused (key) | connect |
| 09 | `?sslmode=bogus` | connect (libpq quotes `bogus`) | same |
| 10 | `?connect_timeout=abc` | connect, fixed reason | connect, quoted |
| 11 | `?options=-c%20foo%3D<PW>` | refused (key) | connect |
| 12 | libpq `key=value` | refused | refused |
| 13 | `postgresql://app:<PW>@…` | connect, clean | same |
| 14 | `app:<A>@<B>@…` | refused | refused |
| 15 | `app:<A>@<B>/<C>@…` | refused | refused |
| 16 | `app:<A>?<B>@<C>@…` | refused | refused |
| 17 | `app:<A>?x@<B>:<C>@…` | refused | refused |
| 18 | `/pro@be` | refused | refused |
| 19 | `/pro%40be` | connect, clean | same |
| 20 | `app@corp:<PW>@…` | refused | refused |
| 21 | `app%40corp:<PW>@…` | connect, clean | same |
| 22 | `localhost:54x32` | refused | refused |
| 23 | `app:<PW>/probe` | refused | refused |
| 24 | `app:<PW>` | refused | refused |
| 25 | `app:<PW>:{H}/probe` | refused | refused |
| 26 | `postgres://` | refused | refused |
| 27 | `postgresql+nope://` | refused | refused |
| 28 | `postgresql+psycopg2://` | **refused** (it was a traceback, a clean one) | traceback |
| 29 | `postgresql+psycopg:app:…` | refused | refused |
| 30 | `@[::1]:{port}` | connect, clean | same |
| 31 | `@localhost:1` | connect, clean | same |
| 32 | `@no-such-host.invalid` | connect, clean | same |
| 33 | `%zz` in password | refused | refused |
| 34 | raw `#` in password | refused | refused |
| 35 | raw space in password | **refused** | connect, clean |
| 36 | raw newline in password | **refused** | connect, clean |
| 37 | `?password=<A>&<B>` | refused (key) | connect, clean |
| 38 | leading space | refused | refused |
| 39 | `app:<D>/probe` | refused (port > 65535) | refused |
| N01 | `app:<A>@<B>?<C>@{H}/probe` | refused | **LEAK** |
| N02 | `app:<A>@<B>/<C>?<E>@…` | refused | **LEAK** |
| N03 | `app:<A>@<B>?<C>=<E>@…` | refused | **LEAK** |
| N04 | `app:<A>@<B>:5432?<C>@…` | refused | **LEAK** |
| N05 | `app:<A>@[<B>:<C>]?<E>@…` | refused | **LEAK** |
| N06 | `?password=<A>&<B>=<C>` | refused | **LEAK** |
| N07 | `?password=<A>&sslmode=<B>` | refused | **LEAK** |
| N08 | `?password=<A>&<B>%20<C>=<E>` | refused | **LEAK** |
| N09 | `app:-<D>/probe` | refused | **LEAK** through `log`; through `migrate` the old code failed with no fragment in the output |
| R01 | `?sslmode=disable&connect_timeout=5&application_name=previously` | connect, clean | connect |
| R02 | `?connect_timeout=x<B>` | connect, fixed reason, clean | **LEAK** (`bad value … 'x<B>'`) |
| R03 | `postgresql://app:Ab+cd%2FEF=<A>==@…` (Go's encoding, wrong password) | connect, clean | connect |
| R04 | `@localhost:/probe` (empty port) | refused | refused (other sentence) |
| R05 | `@localhost:0/probe` | refused | connect |
| R06 | `%00` in password | refused | connect |
| R07 | `%FF` in password | refused | connect |
| R08 | `sslmode` twice | refused | connect |
| R09 | raw `&` in password | refused | connect |
| R10 | `nobody.invalid:54321/probe` (T2-j) | connect, prints host and port: the known limit | same |

Accepted legitimate forms: 01, 02, 13, 19, 21, 30-32, R01 and R03. Two more are in `tests/test_migrate.py`:
- `test_cli_migrate_takes_the_uri_cloudnativepg_writes`:
  - a role with the password `Ab+cd/EF=<16 hex>==`, owner of a fresh database;
  - the DSN `postgresql://<role>:Ab+cd%2FEF=…==@host:port/db`, exactly as Go writes it;
  - the result: `migrated: (empty) -> 0004_event_blob`, exit code 0.
- `test_migrate_takes_a_password_with_a_percent_sign`: every byte of the password encoded, and the migration runs.

Other test changes:
- `test_a_password_in_the_query_is_not_printed` became `test_a_password_in_the_query_is_refused`, which expects the exact sentence.
- `test_cli_migrate_with_an_unknown_query_key_does_not_advise_itself` became `test_cli_migrate_with_a_query_value_the_client_refuses_quotes_none_of_it`. It uses `?connect_timeout=x<hex>` and expects the exact fixed sentence.
- The docstrings of the percent-sign test and the own-connection test follow the new mechanism.

## Mutations

The script `scratchpad/mutate.py` applied each mutation to `postgres.py` and restored the file at once. Each run covered `test_cli.py`, `test_migrate.py`, `test_storage.py` and `test_docs_references.py`, 316 tests. `git status --short` showed only the intended files afterwards.

| Mutation | Red | Green control |
|---|---|---|
| M1 a raw `@` allowed in the password (`(?:PART\|@)*`) | form 14, through `log` and `migrate` | 314 passed |
| M2 `password` added to `DSN_QUERY_KEYS` | forms 03 and N07 (both commands), `test_a_password_in_the_query_is_refused`, `test_the_refusal_lists_the_query_keys_from_dsn_accepts` | 310 passed |
| M3 the connect-time branch quotes `_first_line(error)` again | R02 (both commands), `test_cli_migrate_with_a_query_value_the_client_refuses_quotes_none_of_it` | 313 passed |
| M4 port `-?[0-9]*`, empty allowed, lower bound dropped | N09, R04, R05 (both commands) | 310 passed |

## Pages

- **`docs/reference/configuration.md`** has a new subsection, *The accepted form*, with the label `dsn-form`. It holds:
  - a table of the parts, the escape rule, the eight query keys with `password` refused there, the query values and the refused escapes;
  - that the CloudNativePG `uri` is taken unchanged;
  - the limit: a string without `@` has no user part, and what follows the first `:` there is the port; a raw `@` in a password with the `@host` forgotten is read the same way;
  - that `alembic` in a checkout parses the string with SQLAlchemy and is not held to the form.
  - The promise "the password appears in neither" is gone.
- **`docs/reference/cli.md`:**
  - "The password appears in neither" is replaced. The page now says the password is taken from the user part alone, so a message carries a piece of it only where the string is read otherwise than its writer meant, and it points to the form.
  - The connection block has a fourth line, the fixed reason.
  - The refusal block quotes the new sentence.
  - The paragraph on the round trip is gone.
- **`tests/test_docs_references.py`:** the connection block's count goes from 3 to 4. The refusal anchor is now "is refused before anything connects, with one sentence that names no part of it". The docstring and the comment follow.
- **The tutorial:** only the pytest block, retyped through a placeholder from a green `uv run pytest`: `collected 780 items` … `780 passed in 104.46s (0:01:44)`.

## Gates (each its own command, after the tutorial block)

- `uv run ruff check .` → `All checks passed!`
- `uv run ruff format --check .` → `73 files already formatted`
- `uv run pyright` → `0 errors, 0 warnings, 0 informations`
- `uv run lint-imports` → `Contracts: 6 kept, 0 broken.`
- `uv run pytest --cov --cov-report=term-missing` → `780 passed in 94.00s (0:01:33)`; `Total coverage: 98.05%`. `postgres.py` is at 100 %. `migrate.py` is at 98 %: line 111, the `head is None` raise, is uncovered, as before.
- `make -C docs html` → `build succeeded.`
- `make -C docs vale` → `✔ 0 errors, 0 warnings and 0 suggestions in 28 files.`
- `make -C docs linkcheck` → `build succeeded.`

## Residual leaks I can still find

1. **T2-j, as ruled.** With the `@host` forgotten, `user:12345/db` prints `user` and `12345` as host and port (R10).
2. **The same class, which T2-j does not name:** a password with a raw `@` **and** the `@host` forgotten.
   - Measured by hand: `postgresql://app:abcdefgh12345678@ijklmnop87654321/probe` reads as the password `abcdefgh12345678` and the host `ijklmnop87654321`.
   - It prints `… at ijklmnop87654321 failed: failed to resolve host 'ijklmnop87654321'`.
   - With exactly one `@`, the grammar has one reading, and here it is not the writer's. It takes two mistakes: a raw `@` and a forgotten host.
   - `configuration.md` names it beside T2-j.
3. **Not a parse problem.** Two ways a password reaches the output that neither the grammar nor a message of ours can tell from a legitimate string:
   - A password typed into the user's place (`postgresql://<PW>@host/db`) is named by libpq on a refused login: `password authentication failed for user "…"`.
   - A password written as the value of an allowed key that libpq validates, such as `?sslmode=<PW>`, is quoted.
4. **Outside `previously`.** `alembic` run in a checkout reads `PREVIOUSLY_DSN` through SQLAlchemy's parser and is not held to the grammar. Its errors are Alembic's.

## Concerns

1. **The ruling excludes `&` from the user and the password, though `&` splits nothing there.** Go's `url.UserPassword` writes `&` raw. So a CloudNativePG `uri` for a password that holds `&` would be refused, and the sentence says to encode it. The passwords CloudNativePG generated in the review were base64-like (`+/=`), and those pass. I did not check CloudNativePG's alphabet in its source.
2. **The page's fourth connection line is held only loosely.** `test_docs_references` matches it against the static parts of the messages `ServerUnreachable` raises. The generic one (`connecting to … failed: …`) matches any reason, so a drift of the fixed wording on the page alone would stay green. `test_cli_migrate_with_a_query_value_the_client_refuses_quotes_none_of_it` holds the code's exact wording.
3. **`migrate` now runs the upgrade inside `storage.begin()`.** That is READ COMMITTED, committed by the storage, and Alembic sees an external transaction and does not begin its own. Every `migrate` test passes, the two-waiter lock test among them. All revisions run in one transaction, as before.
4. Neither the `T201` count nor the list of suppressions changes.

---

# Fix round 5 (rulings T2-l, T2-m)

The commit sits on top of `9cdb5b8`, and the reply gives its hash. Status: done.

## 1. T2-l: `&` in the user part

- `_USERINFO` is the user and password class, `[A-Za-z0-9\-._~!$&'()*+,;=]` or an escape. `_PART`, the class for the database name, stays without `&`, and `_VALUE` still has no `&`.
- Table form R09, `app:<A>&<B>@H/probe`, now connects, and no fragment of the password reaches the output.
- `test_cli_migrate_takes_the_uri_cloudnativepg_writes` now uses the password `Ab+cd/EF=gh&$,;<16 hex>==`. That holds every character Go leaves raw, and Go's encoding writes only `/` as `%2F`. The result is `migrated: (empty) -> 0004_event_blob`, exit code 0.
- R19, a raw `&` in a query value (`application_name=a&b`), stays refused.

## 2. Line separators and C1 controls

- `_ESCAPE` is now `%[0-9A-Fa-f]{2}`. `_decoded` checks the decoded text and refuses any character whose `unicodedata.category` is in `{"Cc", "Zl", "Zp"}`. That is:
  - C0, DEL and C1 (U+0080-U+009F, U+0085 included) through `Cc`;
  - U+2028 through `Zl`;
  - U+2029 through `Zp`.
- One check of the decoded text now does what two did: the byte-wise exclusion of control escapes in the regex is gone.
- The table asserts `len(err.splitlines()) == 1` for every case, refused or not. It comes before the outcome check, and `str.splitlines()` breaks at U+0085, U+2028 and U+2029.
- New forms for the database name:
  - R11 `/pro%C2%85be`
  - R12 `%E2%80%A8`
  - R13 `%E2%80%A9`
  - R14 `%C2%9B`
  - R15 `%0A`
  All five are refused. Against `9cdb5b8`, R11-R13 printed a sentence that `splitlines()` counts as 2 lines, and R14 was accepted.

## 3. The refusal sentence

```
PREVIOUSLY_DSN is refused — write it as postgresql://user:password@host:5432/database?key=value with the password there and nowhere else, percent-encode every character of the user name, the password, the database name and a value that is not a letter, a digit or one of -._~ (such as `%40` for `@`), and use no key but application_name, channel_binding, connect_timeout, require_auth, sslcert, sslkey, sslmode or sslrootcert
```

What is true: a special character in a query value has to be percent-encoded; raw, the value is refused. A value takes only letters, digits, `-._~/` and escapes raw.

The sentence gives the one rule that always works, not the whole grammar. Every part takes the escape of any character but a control or a line separator, so encoding everything except letters, digits and `-._~` is always accepted. The docstring of `_unreadable` says so, and `configuration.md` gives the whole form. The sentence is about as long as before: the list of raw sub-delimiters is gone, and the query value has come in.

## 4. Host labels

The host is now `_LABEL(\._LABEL)*\.?`, with `_LABEL = [A-Za-z0-9_\-]{1,63}`. These forms are refused with the sentence:
- R16 `a..b`;
- R17 `.`;
- R18 a label of 64 characters.

Against `9cdb5b8`, each was a traceback ending in `UnicodeEncodeError: 'idna' codec … label empty` or `label too long`, measured through both commands.

## 5. A database error at the upgrade's COMMIT: it escaped, and it is translated now

- **Measured, without a mock:** `test_cli_migrate_names_the_reason_of_an_error_at_commit`, parametrized over two SQLSTATEs.
  - An event trigger on `ddl_command_end` adds a constraint trigger to `alembic_version` as soon as Alembic creates the table: `DEFERRABLE INITIALLY DEFERRED`, `AFTER INSERT`, raising `no revision may be recorded here`.
  - It fires at COMMIT.
- **Against `9cdb5b8`:**
  - `XX000` gave a traceback: `sqlalchemy.exc.InternalError … no revision may be recorded here`.
  - `P0001` gave `Error: database schema incomplete — \`previously migrate\` has not run yet`, which is the self-advice.
- **The fix:** `upgrade.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))`, the last statement inside `with storage.begin() as upgrade, _refusals(head):`.
  - Every deferred constraint and constraint trigger is checked there, inside `_refusals`.
  - Both cases now end in `Error: the database refused the migration to 0004_event_blob: no revision may be recorded here`, and the lock is gone afterwards.
- **What it does not cover:** a failure of the COMMIT itself. Those arrive as an `OperationalError` (I/O, shutdown, serialization), and `_transaction` translates them.

## 6. Residuals named

`configuration.md` has a table, "Mistyped → Printed", with one row each:
- T2-j;
- its variant `user:12345/rest`, where the rest is printed as the database;
- residual 2, `user:pw@rest` and `user:pw@[hex]`;
- the password as the value of `sslmode`, `require_auth` or `channel_binding`;
- the password as the user;
- the password as the database.

Beside the table:
- a line that `alembic` in a checkout isn't held to the form;
- the review's nit: the page used to name the host and the port, and now names the database as well.

`_url_of`'s docstring carries the same list and no longer says "the one thing". `cli.md:14` now says a piece can reach a message "only where the string is mistyped", with two examples, and that the form "lists each such case".

## Table

The table now runs 67 forms × `log`/`migrate`, 134 cases. Compared with round 4, R09 is now `connect`, and R11-R19 are new:

| # | form | now | at 9cdb5b8 |
|---|---|---|---|
| R09 | `app:<A>&<B>@H/probe` | connect, clean | refused |
| R11 | `/pro%C2%85be` | refused | connect, 2 lines |
| R12 | `/pro%E2%80%A8be` | refused | connect, 2 lines |
| R13 | `/pro%E2%80%A9be` | refused | connect, 2 lines |
| R14 | `/pro%C2%9Bbe` | refused | connect |
| R15 | `/pro%0Abe` | refused | refused (old sentence) |
| R16 | host `a..b` | refused | traceback (idna) |
| R17 | host `.` | refused | traceback (idna) |
| R18 | a host label of 64 characters | refused | traceback (idna) |
| R19 | `?application_name=a&b` | refused | refused (old sentence) |

I ran the new forms against `postgres.py` and `migrate.py` of `9cdb5b8`, swapped in and restored at once: 20 failed and 2 passed, the 2 being R10.

## Mutations

The script `scratchpad/mutate5.py` applied each mutation and restored at once. Each run covered `test_cli.py`, `test_migrate.py`, `test_storage.py` and `test_docs_references.py`, 336 tests. `git status --short` afterwards showed only the intended files.

| Mutation | Red | Green control |
|---|---|---|
| M1 a raw `@` allowed in the password | form 14, both commands | 334 passed |
| M2 `password` added to the keys | 03, N07 (both), `test_a_password_in_the_query_is_refused`, `test_the_refusal_lists_the_query_keys_from_dsn_accepts` | 330 passed |
| M3 the connect-time branch quotes libpq again | R02 (both), `…_quotes_none_of_it` | 333 passed |
| M4 negative or empty port | N09, R04, R05 (both) | 330 passed |
| M5 `&` refused in the user part again (T2-l) | R09 (both), `test_cli_migrate_takes_the_uri_cloudnativepg_writes` | 333 passed |
| M6 only `Cc` refused (`Zl`, `Zp` allowed) | R12, R13 (both) | 332 passed |
| M9 the decoded check off entirely | R06, R11-R15 (both) | 324 passed |
| M7 host labels `*` instead of `{1,63}` | R16, R17, R18 (both) | 330 passed |
| M8 `SET CONSTRAINTS ALL IMMEDIATE` removed | `…error_at_commit[XX000]`, `[P0001]` | 334 passed |

## Tutorial

Only the pytest block changed, retyped through a placeholder from a green `uv run pytest`: `collected 800 items` … `800 passed in 93.56s (0:01:33)`.

## Gates (each its own command, after the tutorial block)

- `uv run ruff check .` → `All checks passed!`
- `uv run ruff format --check .` → `73 files already formatted`
- `uv run pyright` → `0 errors, 0 warnings, 0 informations`
- `uv run lint-imports` → `Contracts: 6 kept, 0 broken.`
- `uv run pytest --cov --cov-report=term-missing` → `800 passed in 93.36s (0:01:33)`; `Total coverage: 98.06%`. `postgres.py` is at 100 %. `migrate.py` is at 98 %: line 111, `head is None`, is uncovered, as before.
- `make -C docs html` → `build succeeded.`
- `make -C docs vale` → `✔ 0 errors, 0 warnings and 0 suggestions in 28 files.`
- `make -C docs linkcheck` → `build succeeded.`

## Residual leaks

These are the ones named in item 6. Each takes a mistyped string or a password in the place of another part. I found no new one. There is no code for them, per T2-m.

## Concerns

1. Escaping everything but letters, digits and `-._~` is always accepted. What the grammar takes raw is wider, and the sentence doesn't say so. `configuration.md` does.
2. `SET CONSTRAINTS ALL IMMEDIATE` covers deferred constraints and constraint triggers. Any other database error that a COMMIT raises without being an `OperationalError` would still escape `_refusals`. I know of none in PostgreSQL apart from deferred checks.
