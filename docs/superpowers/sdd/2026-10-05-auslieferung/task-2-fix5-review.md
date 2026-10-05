## Task 2, fix round 5: re-review (9cdb5b8..194acf4)

Read: the whole diff package; `_DSN`, `_USERINFO`, `_PART`, `_VALUE`, `_LABEL`, `_decoded`, `_url_of`, `_unreadable` at head; `storage/migrate.py` and `migrations/env.py` at head; rulings T2-l and T2-m; `task-2-fix4-review.md`; "Fix round 5" of the report.
Ran: `pytest tests/test_migrate.py tests/test_cli.py tests/test_storage.py tests/test_docs_references.py -k "commit or no_form_of_the_connection or cloudnativepg or refusal or lists_the_query" --no-cov -p no:randomly` -> 142 passed; `pytest tests/test_docs_typed_output.py tests/test_docs_references.py` -> 6 passed; `--collect-only` -> 800 (the tutorial says 800); `ruff check src tests`, `ruff format --check .`, `pyright src/previously/storage` clean.
Probes (no database): `_url_of` on 31 forms (`scratchpad/p5.py`); ten host names through `previously log` as a process (`scratchpad/h5.py`). Not run: the six gates in full, a mutation of `SET CONSTRAINTS ALL IMMEDIATE` (the sandbox refused a copy of the tree run under `PYTHONPATH`). The worktree is unchanged.

### Finding Verdicts

1. **T2-l, `&` in user and password, refused in query values, R09 accepted: ADDRESSED.**
   - `_USERINFO` has `&`, `_PART` (database) and `_VALUE` do not. Probed: `app:a&b@h/db` and `a&b:c&d@h:5432/db?sslmode=disable` are accepted and decode to `a&b` and `c&d`; `/db&x`, `/d&b` and `?application_name=a&b` are refused; `%26` in the database and in a value is accepted and decoded.
   - No split is reopened. The user part is the optional group `(user(:password)?@)?` before the host, and `?`, `/`, `:`, `@` cannot stand in it, so a `&` there can never meet the query. The forms that carry a `&` after a `?` (`app:A?k=1&B@h/db`, `app:A@B?sslmode=a&b@h/probe`, `app:A&B/probe`, `app:12345&x/probe`) are all refused.
   - R09 is `connect` with both pieces listed as must-not-appear; R19 pins the query value. The CloudNativePG test password now holds `&$,;` and `migrate` exits 0.
2. **Line separators and C1 controls refused, every message one line: ADDRESSED.**
   - `_decoded` checks the decoded text for `Cc`, `Zl`, `Zp`. Probed: U+0085, U+2028, U+2029, U+009B, `%0A`, `%0B`, `%0C`, `%1C`-`%1E` are refused in the database, the user, the password and a query value. That is the whole set `str.splitlines()` breaks at (C0 `\n\r\x0b\x0c\x1c-\x1e`, `\x85`, ` `, ` `).
   - U+00A0 and U+200B (`Zs`, `Cf`) are accepted: neither breaks a line. Not a finding.
   - The table now asserts `len(err.splitlines()) == 1` for every form, before the outcome branch, and R11-R15 cover the database part.
3. **The refusal sentence covers query values: ADDRESSED.** "`?key=value`" and "a value that is not a letter, a digit or one of -._~" are in the sentence. It is the rule that always works (an escape is accepted anywhere but for a control or separator); the `_unreadable` docstring says so. `test_the_refusal_lists_the_query_keys_…` follows the new "no key but" wording. The sentence is one line and the same in `cli.md`, the code and `_UNREADABLE`.
4. **Host with an empty or over-long label: ADDRESSED.**
   - `_LABEL{1,63}(\._LABEL)*\.?`. Probed: `a..b`, `.`, `.a`, a 64-character label refused; `a.`, a 63-character label, `a.b.c.d` accepted.
   - Through `previously log` as a process: `xn--`, `xn--a`, `xn--zz`, `a_b`, `-`, `0.invalid`, `1.2.3.4.5`, a trailing dot, and five labels of 63 characters (319 characters) all end in one sentence, exit 2, with no idna traceback.
5. **A database error at the upgrade's COMMIT: ADDRESSED.**
   - The test uses a real deferred constraint trigger (an event trigger adds it when Alembic creates `alembic_version`), for `XX000` and `P0001`; both pass at head and assert exit 2, the one sentence and no lock left. I did not rerun the mutation.
   - `SET CONSTRAINTS ALL IMMEDIATE` is the last statement inside `with storage.begin() as upgrade, _refusals(head)`, so a failing deferred check is raised inside `_refusals` and ends as `MigrationFailed`.
   - It does not change the meaning of any revision. `git grep -n -i DEFERR src/previously/migrations` finds nothing, and no revision has a constraint trigger or `SET CONSTRAINTS`. The setting is local to the transaction.
   - What stays outside: a failure of the COMMIT itself (I/O, shutdown, serialization), which is an `OperationalError` that `_transaction` translates. The comment says what is covered and the report names the remaining worry.
6. **Every residual named on the page and in the docstring, "the one thing" gone: ADDRESSED, with one omission.**
   - The page table and the docstring list the same six cases, and `git grep` finds no "the one thing" in `postgres.py`.
   - Against "Leaks that remain" of `task-2-fix4-review.md`: T2-j, its variant G21 (`user:12345/rest`), residual (2) with `[hex]` (G20, G22, G42, G49), residual (3) for `sslmode`, `require_auth`, `channel_binding` (G12, G13, G13b, G45, G47), the password as the user name (G50), the password as the database name (G52), and `alembic` unparsed by the grammar (named in the page and the docstring). Nothing is softened. The "Printed" wording is as measured: the value "decoded" (G45, G47), the user name "when the server refuses the login" (G50).
   - Omitted: the attack's G14 note that `sslrootcert`, `sslcert` and `sslkey`, against a TLS server, name the file libpq cannot open, so a secret written as a path is printed. The attack called it residual (3) "only when a secret is written as a path", and the table's fourth row lists three keys only. See Breakage 1.

### New Breakage in the Fix Diff

1. **Minor, a comment is a claim: residual (3) lists three keys, the attack's measure covered six.** `docs/reference/configuration.md` (row 4 of the table) and the `_url_of` docstring name `sslmode`, `require_auth`, `channel_binding`. A password written as the value of `sslrootcert`, `sslcert` or `sslkey` is quoted by libpq against a server that offers TLS (not measured here, as in the attack: its test server had none). The cheapest fix is "or a path in `sslrootcert`, `sslcert` or `sslkey`" in the row and the docstring. `application_name` and `connect_timeout` were measured clean.
2. **Nit: `cli.md:14` says the accepted form "lists each such case and what gets printed".** It does, for the six rows; the sentence is true as long as breakage 1 is fixed together with it.
3. **Nit: the `_unreadable` docstring says "every part takes the escape of any character but a control or a line separator".** The host, the port and the scheme take no escape. "Every part" reads as the parts the sentence names (user, password, database, value); say so or drop "every".

No problem found in: the regex (`&` stays out of `_PART` and `_VALUE`), `_decoded` (`ValueError` covers `UnicodeDecodeError`; nothing else that `_url_of` calls inside the `try` raises one), `except ValueError` (`URL.create` and `int(port)` are outside it), the tutorial retype (800 collected and passed, matches the tree), or the lock handling.

### Out-of-Scope Observations

- `SET CONSTRAINTS ALL IMMEDIATE` runs once, after the last revision, not per revision. A revision may therefore still rely on deferral between its own statements; only deferral past the end of the whole upgrade is gone, and no revision has that. A later revision that wanted it would have to say so in its own transaction handling.
- Unicode formatting characters (`Cf`, such as a right-to-left override) in a printed database name are accepted. They don't split a line; they could make a message misleading in a terminal. Not a password path.

### Verdict

**Approve.** All six findings are ADDRESSED, and I found no new leak path or split from `&`, the host labels or the decoded-category check. One minor open item for the maintainer's call, which needs no further round: name `sslrootcert`, `sslcert` and `sslkey` beside the three keys in residual (3), on the page and in the docstring (Breakage 1). The two nits are optional.
