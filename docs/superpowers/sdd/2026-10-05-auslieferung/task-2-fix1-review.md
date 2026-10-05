## Task 2, fix round 1: re-review (5e5691e..3c8e506)

Read: the whole diff, `storage/migrate.py` and `storage/postgres.py` (imports through `_transaction`, `from_dsn`) at head, `migrations/env.py` online branch.
Ran: `pytest tests/test_migrate.py tests/test_docs_references.py tests/test_storage.py -k "migrate or reference or unreachable or missing_table"` 20 passed; `pytest tests/test_cli.py -k "unreachable or refused_password or missing_database or missing_table"` 4 passed; `make -C docs vale` 0/0/0.
Probes: `from_dsn(...).begin()` against `localhost:1` with eight DSN forms, then a throwaway `postgres:17` (port 55491, removed afterwards) for three CLI runs. Not run: the full suite, `ruff`, `pyright`, `lint-imports`, `html`, `linkcheck`. The report claims them green.

### Finding Verdicts

1. **Important 1: lock connection error → traceback.** ADDRESSED.
   - `migrate.py:87` takes the lock on `storage.autocommit()` (`postgres.py:177-188`, isolation `AUTOCOMMIT`). The unlock left the `finally` and now runs only after success (`migrate.py:121`).
   - On error the connection is checked in when the `with` exits, and `storage.close()` (`migrate.py:124`) calls `Engine.dispose()`. That closes checked-in connections, so the session ends and the lock goes with it.
   - Alembic's engine is `NullPool` (`env.py`), so nothing of it stays pooled.
   - `dispose()` logs and swallows close errors rather than raising. I found no path that leaves the session open with the lock held. A failing unlock after success would close by the same route.
   - Test: `tests/test_migrate.py:315`, with exit 2, the exact sentence and `_no_lock_left`. Reported red against 5e5691e with `InFailedSqlTransaction`, which matches the original measurement.
   - The two-mechanism masking is already in the ledger as deferred.
2. **Important 2: wrong advice.** ADDRESSED for the revision read and for applying a revision. One statement is left outside, see New Breakage 1.
   - `MigrationPending` now names `previously migrate` (`postgres.py:249-255`). `MigrationFailed` (`errors.py`) is raised for every `DBAPIError` except `OperationalError` (`migrate.py:101-115`), which covers T2-g.
   - Tests: `test_migrate.py:341` (CREATE), `:389` (`XX000` → `InternalError`, chosen after `P0001` was measured as `ProgrammingError`), `test_cli.py:361`, `test_storage.py:581`.
3. **Important 3: lock held until commit.** ADDRESSED.
   - `test_migrate.py:201`: two waiters, released together, results sorted to `{Migrated(None, HEAD), Migrated(HEAD, HEAD)}`.
   - Under the named mutation the second waiter gets the lock immediately after the first one's read and reads `None` long before the DDL commits, so the red result is deterministic, not a matter of luck. The implementer measured it red 3/3.
4. **Minor 4: "does not answer".** ADDRESSED, per T2-f.
   - `postgres.py:244-248`: `connecting to the database at <url, hide_password> failed: <first line>`, for every command, since `begin`, `snapshot` and `autocommit` all go through `_transaction`.
   - Tests: `test_cli.py:279` (Connection refused), `:330` (wrong password, drawn at run time, asserted absent from stdout and stderr), `:349` (missing database).
   - My probes reproduce the wording. psycopg resolves `localhost` to `hostaddr` itself, so `"127.0.0.1", port …` in `cli.md` is what really prints.
   - No old "does not answer" wording is left outside `docs/superpowers/`. The remaining "doesn't answer" in `cli.md:84` is prose about the case, not a quotation.
   - On the password itself, see the trace under Out-of-Scope 1.
5. **Minor 6: Alembic's own connection.** ADDRESSED.
   - `test_migrate.py:364`: role with `CONNECTION LIMIT 1`, one line, `too many connections for role`, password absent.

### New Breakage in the Fix Diff

1. **Minor: `previously migrate` can still advise running `previously migrate`.** `src/previously/storage/migrate.py:88`.
   - The `pg_advisory_lock` statement is outside the inner `try`. A `ProgrammingError` there goes to `_transaction` and becomes `MigrationPending`.
   - Measured on a throwaway PG 17 after `REVOKE EXECUTE ON FUNCTION pg_advisory_lock(bigint) FROM PUBLIC`, as a role with `CREATE` on `public`. Output: `Error: database schema incomplete — \`previously migrate\` has not run yet`, exit 2.
   - The configuration is unusual (a hardened database), so this is Minor. It is the same defect class as Important 2 and T2-b ("inside `migrate` a failure … is its own error").
   - Fix: move line 88 into the `try`. Since there is no unlock in a `finally` any more, that is safe.
2. **Minor, as the implementer feared: a database error after connecting now reads "connecting to the database at … failed: …".** `postgres.py:244-248`.
   - It covers every `OperationalError` outside class 40 and `55P03`: `57014` statement timeout, `57P01` admin shutdown, class 53 (disk full), class 58, `55000`/`55006`, and a connection dropped mid-query.
   - Inside `migrate` it also covers such an error from a revision, because `migrate.py:104` passes every `OperationalError` on by class, not by "failed to connect".
   - The grade is Minor, not worse. The old sentence ("does not answer — is PostgreSQL running") was equally wrong for all of these. The quoted reason is now the true one, so an operator is no longer sent to the network blind.
   - A cheap, language-independent fix fits under T2-e: the implementer measured that psycopg gives connect-time failures no SQLSTATE. So `sqlstate is None` → "connecting … failed", otherwise a sentence like "the database at … ended the operation: <reason>".
3. **Nit: "the reason the PostgreSQL client library gives, in the server's language"** (`cli.md:11`, `configuration.md:14`, `postgres.py:234-243`) is only partly true.
   - `failed to resolve host '…': [Errno -2] …` is psycopg's own text (measured). An unknown host never reaches libpq.
   - `connection is bad: invalid sslmode value: "bogus"` keeps a psycopg prefix that `removeprefix` does not strip (measured).
   - `connection to server at …` and `Connection refused` are client-side texts in the client's locale, not the server's. Only the `FATAL:` part is the server's.
   - None of this affects correctness or the password.
4. **Nit: an odd line break in the docstring.** `tests/test_docs_references.py:476-477` ("the nine / errors of the blob commands and of / an unfinished …").

No other breakage:
- `diagnosis` is a faithful split of `_constraint_name`.
- `_assert_raised` has the same assertions as the inline version, and the counts 1/2/1/3 match the page.
- `cli.md` and `configuration.md` agree with the code for every new wording (held by `test_docs_references`, which passed). The exit-code row for `migrate` is accurate.
- The tutorial test block was retyped from a run with 658 items, which matches the reported total (ruling T1-a). I did not recount it per file.

### Out-of-Scope Observations

1. **Important, pre-existing: the password is printed in clear when the DSN carries it as a query parameter.**
   - Measured at head: `PREVIOUSLY_DSN='postgresql+psycopg://app@localhost:55491/probe?password=WRONGQP' previously log` printed `Error: connecting to the database at postgresql+psycopg://app@localhost:55491/probe?password=WRONGQP failed: … password authentication failed for user "app"`.
   - `render_as_string(hide_password=True)` masks only the userinfo password, not `url.query["password"]`. psycopg accepts that form, and libpq documents it.
   - This round did not introduce it. The address line is unchanged from 5e5691e, and libpq's own line never carried the password in any probe.
   - But this round wrote the claim again in two new places: `cli.md:11` ("with the connection string's password replaced by `***`") and `configuration.md:14` ("without the password"). The old `cli.md:84` claim was already there.
   - Proposal: mask `password` in `url.query` as well, wherever an address is rendered (`postgres.py:245`; check other `render_as_string` call sites). Add a test using the `?password=` form, measured red today.
2. **Pre-existing, the same family: an unencoded `@` in the password puts the rest of it into the host.**
   - `user:WRONG@PW@host` renders as `app:***@PW@localhost…`, and psycopg's reason repeats it (`failed to resolve host 'PW@localhost'`).
   - The new line only repeats a fragment the address already leaked. `configuration.md` tells users to escape.
   - Belongs with 1 in a map entry. Raw `:` and `/` probed fine; `/` after an `@` leaks the same way.
3. The tests hold English server and client texts (`FATAL:  password authentication failed`, `Connection refused`, `too many connections for role`, `permission denied for …`). That is fine against `postgres:17` with the C locale, but would break on a localized client or server. The implementer already raised this.

### Verdict

**Approved with minors.** All five findings are ADDRESSED. No password exposure was introduced: libpq's line carried none in any probe, and the address rendering is unchanged.

New in the diff:
- Minor 1 (`migrate.py:88`: the lock statement outside the `try` still yields the `MigrationPending` advice from `migrate`, measured). A one-line move; worth taking in this round.
- Minor 2 ("connecting … failed" for errors after connecting). Joins T2-e.
- Two nits.

Out of scope but serious: a `?password=` DSN prints the password in clear on every connection failure. This is pre-existing, and this round's new doc sentences repeat the claim that it is masked. It needs a ruling.
