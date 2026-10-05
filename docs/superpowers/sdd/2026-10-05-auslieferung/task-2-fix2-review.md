## Task 2, fix round 2: re-review (3c8e506..fa61473)

Read: the whole diff package; `storage/postgres.py` (`diagnosis`, `_where`, `_transaction`, `from_dsn`) and `storage/migrate.py` (the `try` around the lock) at head; `cli.main`; `migrations/env.py`; SQLAlchemy 2.1's `_parse_url` regex; ruling T2-h; report round 2.
Ran: `pytest tests/test_migrate.py tests/test_cli.py tests/test_docs_references.py -k "migrate or unreachable or refused_password or query or at_sign or missing_database or reference" --no-cov` → 23 passed.
Probes: 38 DSN forms through `.venv/bin/previously log` as a process, 10 of them also through `previously migrate`, against a throwaway `postgres:17` (user `app`, db `probe`; removed afterwards).
Probe script: `scratchpad/probe.py`. Each probe flags any 8-character run of each secret in stdout+stderr.
Not run: the six gates. The report claims them green.

### Finding Verdicts

1. **Serious: the password reaches the message.** PARTIALLY ADDRESSED.
   - `_where` (`postgres.py:113-125`) reads only `url.database`, `url.host` and `url.port`. The `user:pw@` and `?password=` forms are clean, measured.
   - The two-`@` check (`postgres.py:904`) refuses `a@b@host` and `a@b/c@host`, measured.
   - It does not refuse two forms, and both still print a piece of the password through the parsed host:
     - a `?` in the password before the unencoded `@`;
     - an `@` inside a `?password=` value.
   - See Attack results 15, 16 and 4. Both forms are the same mistake the finding names, an unencoded `@` in a password. The defect class stays open at Serious.
2. **Minor: `pg_advisory_lock` outside the `try`.** ADDRESSED.
   - `migrate.py:91-95` is inside the `try` that turns any non-`OperationalError` `DBAPIError` into `MigrationFailed`.
   - `test_cli_migrate_as_a_role_that_may_not_take_the_lock_names_the_reason` expects the exact sentence.
   - The REVOKE is per database, because `pg_proc` is per database, so it does not reach other tests.
   - The mutation the report names (moving the statement back) restores the `MigrationPending` path I measured in round 1. Red is the expected result.
3. **Minor: "connecting … failed" for errors after connecting.** ADDRESSED.
   - `postgres.py:252-257`: a string SQLSTATE now gives `OperationFailed`, with `message_primary` or else the state. No SQLSTATE still gives `ServerUnreachable`.
   - The statement-timeout test is deterministic: the holder takes the lock at once, and `migrate` waits past 500 ms.
   - A connection dropped mid-operation without a SQLSTATE would still read "connecting … failed". Not measured; see Out-of-Scope 3.
4. **Nit: where the reason line comes from, and a line break.** ADDRESSED.
   - `cli.md:50-52` matches what I measured: psycopg's own `failed to resolve host '…'`, and libpq's client-side text before `FATAL:`.
   - The line break in `test_docs_references.py` is fixed.
   - The new rule sentence above it is not accurate; see New Breakage 2.

### Attack results (form → printed, verdict)

`log` unless noted. Every case exits 2 except where a traceback is noted (exit 1). `<PW>` is the password; `<PW-2>` is the part of it after an unencoded `@`.

1. `app:<PW>@host/probe` (wrong password) → `Error: connecting to database probe at localhost:32768 failed: connection to server at "127.0.0.1", port 32768 failed: FATAL:  password authentication failed for user "app"`. Clean.
2. `app:<PW with %40%3A%2F%3F%23>@host/probe` → the same sentence. Clean.
3. `app@host/probe?password=<PW>` (log and migrate) → the same sentence. Clean.
4. **`app@host/probe?password=<PW-1>@<PW-2>` → `Error: connecting to database (default) at <PW-2> failed: failed to resolve host '<PW-2>': [Errno -2] Name or service not known`. LEAK, twice in one line, through `log` and `migrate`.**
   - The `@` after `?` is not counted.
   - SQLAlchemy's username `[^:/]*` runs to `app@host`. The "password" becomes `32768/probe?password=<PW-1>`, and the host becomes `<PW-2>`.
5. `?passwrod=<PW>` (a typo in the key) → `Error: database schema incomplete — \`previously migrate\` has not run yet`, through `log` and `migrate`. Clean, but wrong advice; see Out-of-Scope 2.
6. `?passfile=/tmp/<PW>` → `… failed: fe_sendauth: no password supplied`. Clean.
7. `?sslpassword=<PW>` → `… fe_sendauth: no password supplied`. Clean.
   - With `&sslkey=/nonexistent&sslmode=require` → `… server does not support SSL, but SSL was required`. Clean.
8. `?options=-c%20foo%3D<PW>` → `… fe_sendauth: no password supplied`. Clean.
9. `?sslmode=<PW>` → `… failed: connection is bad: invalid sslmode value: "<PW>"`.
   - Not a password leak: libpq quotes the value of a non-secret option.
   - It refutes the page's "not the query", though; see New Breakage 2.
   - `?connect_timeout=<PW>` → `database schema incomplete …` (Out-of-Scope 2).
10. libpq key/value `host=… password=<PW>` → `Error: PREVIOUSLY_DSN is not a valid connection string — something like postgresql+psycopg://user:pass@host:5432/database is expected`. Clean.
11. `postgresql://app:<PW>@…` (plain libpq scheme) → connects through psycopg; the wrong-password sentence of 1. Clean.
12. `app:<PW-1>@<PW-2>@host/probe` (log and migrate) → `Error: PREVIOUSLY_DSN holds more than one \`@\` before the host — …`. Clean.
13. `app:<PW-1>@<PW-2>/<PW-3>@host/probe` → the same refusal. Clean.
14. `@` in the database: `/pro@be` → refused with the same sentence. `/pro%40be` → connects, `database pro@be`.
15. **`app:<PW-1>?<PW-1b>@<PW-2>@host:32768/probe` → `Error: connecting to database probe at <PW-2>@localhost:32768 failed: failed to resolve host '<PW-2>@localhost': [Errno -2] Name or service not known`. LEAK, through `log` and `migrate`.**
   - The check counts `@` only up to the first `?`, and here that `?` is the password's own.
   - SQLAlchemy's password `[^@]*` swallows the `?`.
16. **`app:<PW-1>?x@<PW-2>:<PW-3>@host:32768/probe` → a 28-line traceback (26 under `migrate`), exit 1, ending `ValueError: invalid literal for int() with base 10: '<PW-3>@localhost:32768'`. LEAK.**
17. `app@corp:<PW>@host/probe` (an unencoded `@` in the user name) → refused with the two-`@` sentence. `app%40corp:<PW>@…` → connects as `app@corp`. See New Breakage 3.
18. Non-numeric port `@localhost:54x32/probe` → a traceback, exit 1, ending `ValueError: invalid literal for int() with base 10: '54x32'`.
    - The traceback's other lines are file paths and source lines (`engine = create_engine(dsn)`, `components["port"] = int(components["port"])`), with no DSN content. Clean.
    - It is clean only because the port really is the port. Forms 16 and 19-21 put the password in its place.
19. **`app:<PW>/probe` (the `@host` forgotten) → a traceback, exit 1, ending `ValueError: invalid literal for int() with base 10: '<PW>'`. LEAK, the whole password, through `log` and `migrate`.**
   - With no `@`, the userinfo group fails. `app` becomes the host and `<PW>` the port.
20. **`app:<PW>` (no host at all) → the same traceback with `'<PW>'`. LEAK.**
21. **`app:<PW>:localhost:32768/probe` (`:` typed for `@`) → the same traceback with `'<PW>:localhost:32768'`. LEAK.**
22. Malformed schemes:
    - `postgres://…`, `postgresql+nope://…` and `postgresql+psycopg:app:…` (no `//`) → the `InvalidDsn` sentence. Clean.
    - `postgresql+psycopg2://…` → a traceback ending `ModuleNotFoundError: No module named 'psycopg2'`, with no DSN content. Clean.
23. A leading space before the scheme, with two `@` → refused. Clean.
24. `[::1]:port` → `connecting to database probe at ::1:32768 failed: … Connection refused`. Clean. The colon makes it ambiguous (Nit, not filed).
25. Unreachable (`localhost:1`) and unresolvable (`no-such-host.invalid`) → the documented sentences. Clean.
26. A password holding `%zz`, `#`, a space, a newline, or `&` inside `?password=` → the wrong-password sentence of 1. Clean.

What is not reachable from the tree: an all-digit password in form 19. That makes the "port" valid, so `_where` would print it as the port. I reasoned this from the regex and did not run it.

### New Breakage in the Fix Diff

1. **Serious (the open part of Finding 1): the two-`@` check is cut at the wrong place.** `src/previously/storage/postgres.py:904`.
   - `partition("?")[0]` stops at the first `?` anywhere. SQLAlchemy's password group `[^@]*` happily holds a `?`, and its username group `[^:/]*` happily holds an `@`. So the forms in 4, 15 and 16 pass the check and print a piece of the password, measured.
   - A fix that closes every form I measured, 4, 15, 16 and 19-21:
     - count `@` over everything after `://`, not only up to `?`;
     - wrap `create_engine` so that a `ValueError` becomes the fixed `InvalidDsn` sentence as well, `except (ArgumentError, ValueError)`.
   - Cost of the first part: an unencoded `@` in a query value is refused even where it was harmless. It is harmless only when the userinfo carries a `:password`, and `%40` remains the way to write it.
   - The second part is outside the diff: `from_dsn`'s `try` is unchanged. But T2-h (1) says that every place which puts a DSN into a message follows the rule. An uncaught `ValueError` is such a place in effect, because its message lands on stderr.
2. **Minor: the new rule sentence on both pages is false as written.** `docs/reference/cli.md:36` and `docs/reference/configuration.md:14`.
   - The sentence: "A message about the database names the database, the host and the port … and nothing else of it: not the user, not the password, and not the query."
   - The quoted reason is part of the message, and it names the user. `cli.md:44`, eight lines below, prints `password authentication failed for user "previously"`.
   - The reason can also quote a query value (form 9: `invalid sslmode value: "…"`).
   - And it can name the password through the host, while Breakage 1 stands.
   - Fix: say the sentence's own part names only database, host and port, and that the quoted reason can name the user and a parameter the client library rejects.
   - `cli.md:60` also says a second `@` "is a character of the password". That is false for forms 14 and 17, and for form 15 it is not refused at all.
3. **Minor: an unencoded `@` in a user name worked until 3c8e506 and is now refused with a sentence that blames the password.** `postgres.py:904-908`.
   - SQLAlchemy parses `app@corp:pw@host` as user `app@corp`, measured with `make_url`.
   - User names of that shape are what Cloud SQL IAM (`sa@project.iam`) and the retired Azure Single Server (`user@server`) issue.
   - Refusing is defensible, since `%40` works (form 17). The sentence should name the cause, though: "a user name, password or database name holding `@` writes it as `%40`".
   - The same goes for the wording "before the host": the check also counts an `@` in the database (form 14), which comes after the host. The pages say "before the query". Those are two descriptions, and neither one is exact.
4. **Nit: the comment's mechanism is wrong.** `postgres.py:901-903`.
   - The comment says "`a@b/c@host` put `b/c` into the host".
   - Measured with `make_url('…app:aaaa@bbbb/cccc@host/db')`: host `bbbb`, database `cccc@host/db`. The rest goes into the host and the database, and both are printed.
   - The conclusion, to count past `/`, holds. The stated reason does not. A comment is a claim.
5. **Test gaps (Minor).**
   - The mutation `partition("?")` → `partition("/")` stays green, derived by reading: the test DSN `user:first@second@host:port/db` has both `@` before the first `/`. The `/` rationale in the comment has no test.
   - No test has a `?` in the password, or an `@` in a `?password=` value. Those are forms 15 and 4, the live leaks.
   - `_no_fragment_of` is vacuously true for a secret shorter than 8 characters, because `range(len - 7)` is then empty. The tests draw 29 characters, so it does not bite today. An `assert len(secret) >= 8` inside the helper would keep it from biting later.
   - A leak shorter than 8 characters, such as the tail after an unencoded `@` in a short password, is not caught by design.
   - The parser splits only at `@`, `:`, `/` and `?`, and the tests make every part a full 29-character draw. So within the tested forms there is no split hole.
6. The remaining mutations in the report's table check out by reading.
   - `_where` printing the query: only the query test carries a query.
   - `> 99`: the at-sign test asserts the exact refusal.
   - The SQLSTATE split taken out: the timeout test asserts the exact sentence.
   - I did not rerun them.

### Out-of-Scope Observations

1. Forms 19-21 (a traceback with the whole password) are pre-existing.
   - The `ValueError` comes out of SQLAlchemy's `int(port)`, and `from_dsn` never caught it.
   - The implementer's concern 2 ("would name the port … no password piece was seen") understated it: when `@host` is missing, the "port" is the password.
   - The fix belongs with Breakage 1 in the same round.
2. **Minor: wrong advice.** An unknown query key (`?passwrod=`) or an invalid value (`?connect_timeout=abc`) makes psycopg raise `ProgrammingError` at connect time.
   - `_transaction` turns it into `MigrationPending`.
   - So `migrate` itself prints "database schema incomplete — `previously migrate` has not run yet", measured, the self-referential advice T2-b removed elsewhere.
   - It is not a leak. It belongs in the map.
3. A connection lost mid-operation without a SQLSTATE (`server closed the connection unexpectedly`) would read "connecting to … failed". Not measured.

### Verdict

**Changes required.** Findings 2, 3 and 4 are ADDRESSED. Finding 1 is PARTIALLY ADDRESSED.

The `user:pw@`, `?password=` and plain two-`@` forms are clean. Three forms of the same mistake still put password text on stderr, measured through `log` and `migrate`:
- `?` before the unencoded `@` (15, 16);
- `@` inside a `?password=` value (4);
- with forms 19-21, three typo forms that are pre-existing but in the attack scope, where a traceback prints the whole password.

Proposed for the round:
- count `@` over the whole string after `://`;
- catch `ValueError` beside `ArgumentError` in `from_dsn`;
- add tests for forms 4, 15 and 19;
- correct the rule sentence on both pages (the reason names the user) and the refusal sentence (user and database names too).
