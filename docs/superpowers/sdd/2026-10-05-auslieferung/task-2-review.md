### Spec Compliance

- ✅ Interfaces: `Migrated(before, head)`, `migrate(dsn)`, public `MIGRATION_LOCK`, `UnknownRevision(StorageError)` — `src/previously/storage/migrate.py:36,39,47`, `src/previously/storage/errors.py:78`.
- ✅ Lock taken before the revision is read (`migrate.py:79` then `:81`), the read is a fresh READ COMMITTED statement after the grant, `command.upgrade` commits on its own connection (`env.py` `begin_transaction`) before the unlock at `:93`. On every path `storage.close()` (`:96`) disposes the pool, so a lock left by a failed unlock dies with the connection; a killed process ends the session and the lock with it.
- ✅ Waiting test is deterministic: it polls `pg_stat_activity` for `wait_event_type = 'Lock' AND wait_event = 'advisory'` with a 10 s deadline and stops early when the thread ends (`tests/test_migrate.py:83-133`). Reported mutation (lock removed → red) is consistent with the code.
- ✅ Unknown revision refused with the contractual wording (`migrate.py:84-89`); `Error: ` prefix and exit 2 from `main` (`cli.py` `except (PreviouslyError, StorageError)`).
- ✅ stdout forms `migrated: <from> -> <head>` with `(empty)`, `up to date: <head>` (`cli.py:308-312`); help line exact (`cli.py:1120`, measured `previously --help`).
- ✅ `PREVIOUSLY_DSN` unset: `Error: PREVIOUSLY_DSN is not set`, exit 2 (measured). Malformed: `InvalidDsn`, exit 2 (report; same `from_dsn`).
- ✅ Wrong password, missing database, server down: one sentence, exit 2, password masked (`***`) — measured wrong password (test) and missing database (my probe). Wording misleading, see Minor 4.
- ❌ "Every failure is one sentence, exit 2": an error on the lock connection after the lock is granted ends in a traceback, exit 1 — Important 1 (measured).
- ❌ Database user lacking CREATE / any `ProgrammingError` in a revision: one sentence, exit 2, but the sentence is wrong advice from `migrate` itself — Important 2.
- ⚠️→❌ Spec §7 criterion 3 ("einer migriert, der andere wartet und findet die Datenbank fertig") and `cli.md:50` ("then finds the schema up to date"): the "finds it done" half — the lock held across the upgrade — has no test — Important 3. The brief narrowed the test to "the test holds the lock", so this is a gap in the brief the implementer followed, not a deviation.
- ✅ `%` fix (`migrate.py:74`, `env.py:79`): correct. Measured round trip: `set_main_option('…a%%40b…')` → `get_main_option` and `get_section` both give `…a%40b…`. Probed against a container: password `a@b:c/d%e` percent-encoded → `migrated: (empty) -> 0004_event_blob`; raw `x:y/z` unencoded → migrated; `uv run alembic upgrade head` with that encoded `PREVIOUSLY_DSN` in development → exit 0. `alembic.ini` has `sqlalchemy.url =` (empty), so dev still falls through to the environment; a non-empty ini value with `%%` now works where it used to raise. Offline branch untouched (does not go through ConfigParser).
- ✅ Contractual wordings on the page held by `tests/test_docs_references.py` (new `migrate` block of 3, `UnknownRevision` against `_raised_patterns`); docstring counts (ten stderr sentences, ten blocks) recounted correct.
- ✅ Pages: `git grep "alembic upgrade"` over `README.md` and `docs/` without `docs/superpowers` finds only the tutorial (`record-your-first-event.md:55`, task 5). Eleven commands in `README.md:61` and `cli.md:6`.
- ✅ Tutorial test block: `collected 651 items`, per-file dot counts summed per file equal `pytest --collect-only -q` per file (651 = 651, no file differs).
- ✅ `T201` comment: 34, measured with the command it names.
- ✅ Ruling P-1: no `{ref}`delivery`` in `migrate.py`. Ruling T1-a: only the test block retyped.
- ✅ No new suppression, no `# type: ignore`. Gates I ran: `ruff check` green, `ruff format --check` green (73 files), `pyright` 0 errors, `lint-imports` 6 kept, `tests/test_migrate.py` 6 passed, `test_docs_references.py`+`test_docs_typed_output.py` 6 passed. ⚠️ Full `pytest --cov` and the docs gate not run by me (read-only brief); the report claims them green.

### Strengths

- Reused `from_dsn` and `storage.begin()` instead of writing a second translation, and ran `command.upgrade` inside the `with` so Alembic's own connection errors are translated too (measured by the implementer with `CONNECTION LIMIT 1`).
- Found and fixed a real password leak the plan's code had (`ValueError: invalid interpolation syntax in '…password…'`), in both places it occurs, with a test measured red against each half.
- The wrong-password test draws the password at run time and also holds that `log` prints the identical line — a cheap proof of reuse.
- `HEAD` read from the tree, not typed; the `get_current_head` comment corrects the brief against the Alembic 1.20.0 source (verified: several heads raise).
- Honest report: the always-upgrade mutation measured and reported as not caught, three concerns raised unprompted, all three confirmed below.

### Issues

#### Critical

None.

#### Important

1. **An error on the lock connection becomes a traceback, exit 1** — `src/previously/storage/migrate.py:92-93`.
   What: once `pg_advisory_lock` is granted, any database error on the same connection (the `get_current_revision` read: permission denied on `alembic_version`, `statement_timeout`, …) aborts its transaction; the `finally` then runs `pg_advisory_unlock` in the aborted transaction, which raises `InFailedSqlTransaction` (`sqlalchemy.exc.InternalError`). That replaces the original error, and `_transaction` translates only `OperationalError`/`ProgrammingError`.
   Measured (throwaway PostgreSQL 17, database migrated by its owner, `REVOKE ALL ON alembic_version FROM PUBLIC`, `previously migrate` as a second role): `exit 1`, stderr a full traceback ending `sqlalchemy.exc.InternalError: (psycopg.errors.InFailedSqlTransaction) current transaction is aborted … [SQL: SELECT pg_advisory_unlock(%(key)s)]`. No password in it, but it breaks the spec's "ein Satz, ohne Traceback". A migration job running as an application role that lacks a grant is the plausible case.
   How: don't unlock in an aborted transaction. Either rely on `storage.close()` for release on the error path (it disposes the pool and closes the session; say so in the comment) and unlock only after success, or take the lock on an AUTOCOMMIT connection so the read cannot poison the unlock (that also resolves Minor 5). Test: the scenario above as a test (role without SELECT on `alembic_version`), asserting exit 2 and one line; measured red today.

2. **A failing revision says "`uv run alembic upgrade head` has not run yet" — from `migrate`** — `src/previously/storage/postgres.py:213-215` reached via `migrate.py:91`.
   What: `command.upgrade` runs inside `_transaction`, so a `ProgrammingError` from DDL (role without CREATE on `public`, the PG 15+ default for a non-owner; measured by the implementer) becomes `MigrationPending`: `database schema incomplete — \`uv run alembic upgrade head\` has not run yet`. An operator reading it after `previously migrate` exited 2 is told the migration has not run and to run a command that is not in the image; in a checkout with the same role they get the same failure as a raw traceback. Not harmful to data, but it sends them to the wrong place, and it hides the real cause (a missing grant). Separately, every other command still prints the old operator path as program output, which spec §1.1.2 replaces with `previously migrate` (the brief's step 6 scoped the replacement to pages; `tests/test_cli.py:318` and `tests/test_storage.py:579` pin the old text; `errors.py` `MigrationPending` docstring names it too).
   How: needs a ruling, since it touches `postgres.py` and two tests outside the task's list. Proposal: `MigrationPending` says `… run \`previously migrate\``; in `migrate`, catch `ProgrammingError` around `command.upgrade` and raise a `StorageError` naming the revision and the server's primary message (`error.orig.diag.message_primary`, e.g. "permission denied for schema public" — it carries no connection string). Same fix covers the `ProgrammingError` half of Important 1.

3. **"The second finds the schema up to date" is not held by any test** — `tests/test_migrate.py:97-136`, claim at `migrate.py:47`, `docs/reference/cli.md:50`, spec §7 criterion 3.
   What: the waiting test proves that `migrate` waits for a lock someone holds, not that `migrate` holds it until its upgrade has committed. Mutation (named, not run): move the `pg_advisory_unlock` from the `finally` to directly after the `get_current_revision` read, before `command.upgrade`. The waiting test still waits, then migrates and returns `Migrated(None, HEAD)`; the other five are single-threaded. Expected: all six green while two concurrent jobs would both read `None` and race the DDL.
   How: the test holds the lock, starts two `migrate` threads, polls until `pg_stat_activity` shows **two** advisory waiters, releases, joins both, and asserts no errors and results `{Migrated(None, HEAD), Migrated(HEAD, HEAD)}`. Under the mutation the second reads `None` before the first commits and fails on the existing table; measure that it goes red, and keep the single-waiter test as the green control.

#### Minor

4. **"does not answer — is PostgreSQL running there" for a refused password, a missing database, and a timeout** — `src/previously/storage/postgres.py:207-211` (pre-existing wording, implementer's concern 1).
   Measured: missing database → `Error: database server at …/nope does not answer — …`; a second `migrate` waiting longer than a database-level `statement_timeout = '1s'` → the same sentence (SQLSTATE 57014, an answer from the server). An operator checks network and pod while the cause is the credentials, the database name, or a timeout. `migrate` is the first command an operator runs, so this is where they meet it. `cli.md:58` is accurate ("the same sentence every other command prints"). How: a map entry; 57014 is distinguishable by SQLSTATE now, the connect-time cases likely only by message.

5. **The lock connection idles in an open transaction for the whole upgrade** — `migrate.py:78-94`.
   It holds `AccessShareLock` on `alembic_version` (from the revision read) until the end. A future revision that alters `alembic_version` would wait on it, and the cycle runs through the client, so PostgreSQL detects no deadlock: the job hangs. A server with `idle_in_transaction_session_timeout` would kill the lock connection mid-upgrade and drop the lock. Neither bites today's revisions. How: same as the AUTOCOMMIT option in Important 1 — take the lock outside a transaction, read the revision in a short one.

6. **The docstring's claim about Alembic's own connection has no test** — `migrate.py:59-60` (implementer's concern 3).
   Measured once by hand with `CONNECTION LIMIT 1`. Per *An assurance needs a test measured to fail*, add that test; mutation: run `command.upgrade` after the `with` closes (keeping the lock semantics aside) and see it go red.

7. **`cli` now imports `alembic` for every command** — `src/previously/cli.py:46-47` (implementer's concern 4).
   Measured `-X importtime`: `previously.storage.migrate` cumulative 177 ms, of which `sqlalchemy` (103 ms) is paid anyway; about 70 ms more per command, 309 ms for `import previously.cli` in total. Acceptable; note only. A lazy import in `_cmd_migrate` would avoid it if start-up ever matters.

### Assessment

**Task quality:** Needs fixes

Spec compliance: ❌ on two points (Important 1: a traceback with exit 1 on a measured path; Important 3: spec §7 criterion 3 half untested). Important 2 needs a ruling because it reaches outside the task's files.
