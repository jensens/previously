## Task 2, fix round 3: re-review (fa61473..2579eb5)

Read: the whole diff package; `_read_as_written`, `_unescaped`, `_unreadable`, `from_dsn` and `_transaction` at head; `storage/migrate.py` and `migrations/env.py`; SQLAlchemy 2.1.2's `_parse_url` and `URL.render_as_string`; rulings T2-i and T2-j; report round 3; CloudNativePG's `pkg/specs/secrets.go` (how the app secret's `uri` is built).
Ran: `pytest tests/test_cli.py tests/test_migrate.py tests/test_docs_references.py -k "no_form_of_the_connection_string or unknown_query_key or quotes_what_the_code" --no-cov -p no:randomly` → 80 passed.
Probes: 37 new DSN forms through `.venv/bin/previously log` as a process, 13 of them also through `previously migrate`. The server was a throwaway `postgres:17` with user `app`, database `probe`, and a role `cnpg` whose password is `Ab+cd/EF=gh==Zq8x`. The container is removed.
The same forms ran against `fa61473`, exported with `git archive` into the scratchpad, to tell new leaks from pre-existing ones.
Scripts: `scratchpad/probe3.py` (process probes; each flags any 8-character run of a secret), `scratchpad/clauses3.py` (which clause refuses each table form), `scratchpad/proposal3.py` (the proposed fix, parse only).
Secrets were 20 characters (`<A>`…`<D>` below), plus a 20-digit `<N>`.
Not run: the six gates. The report claims them green.

### Finding Verdicts

1. **Serious, the password reaches the message (open part: forms 4, 15, 16, 19-21).** PARTIALLY ADDRESSED.
   - Every form of the round-2 review is closed, measured by the table test and by my probe: 4, 15, 16 refused; 19-21 refused, with no traceback.
   - The same class is still open in the reverse order: an unencoded `@` in the password **followed by** a `?`. The parse is a canonical URL, so the round trip gives it back, and the password piece after the `@` is printed as the host (and as the database). See Attack results N01-N05, and New Breakage 1.
2. **Minor, the rule sentence on the pages.** PARTIALLY ADDRESSED. The new wording admits the user and a rejected value. It still says "The password appears in neither", which N01-N08 refute, and the reason now also quotes a rejected *key*. See New Breakage 3.
3. **Minor, `@` in a user name blamed on the password.** ADDRESSED. The sentence names "the user name, the password, the database name or a query value". `app@corp:…` is refused and `app%40corp:…` connects (table forms 20, 21; probe N17).
4. **Nit, the `a@b/c@host` comment.** ADDRESSED: the comment is gone with the count. Its successor makes a claim that does not hold, though; see New Breakage 4.
5. **Test gaps.** PARTIALLY ADDRESSED.
   - `_no_fragment_of` asserts `len(secret) >= 8` (`tests/test_cli.py:556`). Pieces are 20 characters.
   - The table now carries forms 4, 15 and 16, the live leaks of round 2.
   - Still missing: an `@` then `?` in the password (N01), an `&`/`=` split of a `?password=` value (N06), a negative "port" (N09).
   - The query clause has no test of its own. `clauses3.py` shows that every table form the query clause refuses (only form 4) is refused by the head clause too. So the mutation `sorted(parse_qsl(written_query)) == sorted(parse_qsl(rendered_query))` → `True` stays green. Derived by reading the clause results, not run against the suite.
6. **Out-of-scope 2 of round 2, `migrate` recommending itself on a query typo.** ADDRESSED for the advice: `?passwrod=` now gives `connecting to database probe at …: invalid connection option "passwrod"`, measured, and `test_cli_migrate_with_an_unknown_query_key_does_not_advise_itself` holds it. The quoted line introduces a leak; see New Breakage 2.

### Attack results (form → printed, verdict)

`log` unless noted. Every case exits 2. "Also `migrate`" means the same line was measured through `previously migrate`. "At fa61473" is the same form through the round-2 code.

**Password piece in host or database (the open part of Finding 1):**

- **N01 `app:<A>@<B>?<C>@host:port/probe`** → `Error: connecting to database (default) at <B> failed: failed to resolve host '<B>': [Errno -2] Name or service not known`. **LEAK of `<B>`, twice. Also `migrate`. At fa61473: the same leak**, so it predates this round and the round-trip check doesn't close it.
  - The cause: SQLAlchemy cuts the password at the first `@`, so `<B>` becomes the host. `<C>@host:port/probe` becomes the query, and `parse_qsl` drops it because it has no `=`. The rendering is `…app:<A>@<B>`, the same as the written head. The written query and the rendered one are both empty after `parse_qsl`. The host holds no `@`.
- **N02 `app:<A>@<B>/<C>?<D>@host:port/probe`** → `Error: connecting to database <C> at <B> failed: failed to resolve host '<B>': …`. **LEAK of `<B>` (host) and `<C>` (database). Also `migrate`. At fa61473: the same.**
- **N03 `app:<A>@<B>?<C>=<D>@host:port/probe`** → `… database (default) at <B> failed: failed to resolve host '<B>' …`. **LEAK of `<B>`. Also `migrate`.**
  - Here the query is `C=D@host:port/probe`, and it survives `parse_qsl`. The rendering writes it as `C=D%40host%3A…`, which parses to the same pairs. So keeping blank values would not close this form either.
- **N04 `app:<A>@<B>:5432?<C>@host:port/probe`** → `… database (default) at <B>:5432 failed: …`. **LEAK of `<B>`. Also `migrate`.**
- **N05 `app:<A>@[<B>:<C>]?<D>@host:port/probe`** → `… database (default) at <B>:<C> failed: failed to resolve host '<B>:<C>' …`. **LEAK of `<B>` and `<C>`. Also `migrate`.**

**A password piece quoted by the client library (query split at an unencoded `&`):**

- **N06 `app@host/probe?password=<A>&<B>=<C>`** → `Error: connecting to database probe at localhost:32769 failed: invalid connection option "<B>"`. **LEAK of `<B>`. Also `migrate`. At fa61473: clean** (`database schema incomplete — …`). This is new in this diff; see New Breakage 2.
- **N08 `…?password=<A>&<B>%20<C>=<D>`** → `… failed: missing "=" after "<B>" in connection info string`. **LEAK of `<B>`. Also `migrate`. At fa61473: clean.** New in this diff.
- **N07 `…?password=<A>&sslmode=<B>`** → `… failed: connection is bad: invalid sslmode value: "<B>"`. **LEAK. At fa61473: the same**, so it is pre-existing (an `OperationalError`). It needs a password that holds `&sslmode=` literally, or `&host=` or `&port=` and the like.

**Port:**

- **N09 `app:-<N>/probe` (all-digit password with a leading `-`, `@host` forgotten)** → `Error: connecting to database probe at app:-<N> failed: failed to resolve host 'app': [Errno -8] Servname not supported for ai_socktype`. **LEAK of the whole password, any length. Also `migrate`. At fa61473: the same.**
  - `int("-<N>")` is negative, and the check is `url.port <= 65535` with no lower bound.
  - This is beyond the limit ruling T2-j names ("five digits or fewer").
- N29 `app:54321/probe` → `… at app:54321 failed …`. The known T2-j limit, as stated.

**The normalization, attacked as the brief asks (all clean):**

- N10 raw `+` in the password → the wrong-password sentence. Clean. SQLAlchemy keeps `+` as `+` in user info, and so does libpq.
- N11 `+` in a `?password=` value → the wrong-password sentence. Clean.
  - The parse differs from intent: `parse_qsl` makes `+` a space on both sides, so the round trip cannot see it. The result is a wrong password, not a leak.
- N12 `%2F` and N13 lower-case `%3a` in the password → the wrong-password sentence. Clean, accepted.
- N14 `ü€` raw in the password → the wrong-password sentence. Clean, accepted.
- N24 `%FF` in the password → the wrong-password sentence. Clean.
  - Both sides decode `%FF` to U+FFFD, so it compares equal. The password sent is not the bytes written. Not a leak.
- N15 unicode in the host, `hösté.invalid` → `… at hösté.invalid failed: failed to resolve host 'hösté.invalid' …`. Clean.
- N16 an empty password, `app:@host` → `… fe_sendauth: no password supplied`. Clean, accepted.
- N17 a user with no password and an `@` elsewhere, `app@<A>@host/probe` → refused with the sentence. Clean.
- N18 a fragment after the database, `/probe#<B>` → refused. Clean.
- N19 a fragment after a query value, `?sslmode=prefer#<B>` → `… invalid sslmode value: "prefer#<B>"`. The fragment is quoted, but it is not a password. The page already names quoted values. Clean as far as the password goes.
- N20 upper-case scheme `POSTGRESQL+PSYCOPG://` → refused with the sentence. Clean. The sentence doesn't hint at case. Nit.
- `postgresql://` without a driver → connects through psycopg (C03-C08). Clean.
- Whitespace:
  - A leading space is refused (table form 38).
  - N21, a trailing space → `… at database probe  at …` (database `probe `). Accepted; the database name is wrong. Clean.
  - N22, a trailing newline → `Error: connecting to database probe\n at localhost:… failed: …`. Two lines on stderr. Clean, but see Out-of-Scope 1.
  - N23, a trailing newline after a query → refused. SQLAlchemy's query `.*` stops at the newline. Clean.
- N25 a newline inside a `?password=` value → refused. Clean.
- N26 a raw `/` in the password → refused. Clean. libpq itself misreads that form: `psql` gives `invalid integer value "Ab+cd" for connection option "port"`, measured.
- N27 raw `=` and `&`, N28 raw `;$,!*'()` in the password → the wrong-password sentence. Clean, accepted.

### Legitimate forms

CloudNativePG builds the app secret's `uri` as `url.URL{Scheme: "postgresql", User: url.UserPassword(user, password), Host: host, Path: dbname}.String()`, according to `pkg/specs/secrets.go` on `main`.
Go's `UserPassword`, as I read `net/url`'s `shouldEscape` for user info (not measured), leaves letters, digits, `-_.~` and `$&+,;=` raw, and writes everything else, `@ / ? :` included, as upper-case `%XX`.

Against the role `cnpg` / `Ab+cd/EF=gh==Zq8x`, with the database migrated by C03:

| Form | Result |
|---|---|
| C04 `postgresql://cnpg:Ab+cd%2FEF=gh==Zq8x@host/cnpgdb` (what Go writes) | **accepted, connects** (`log`: schema incomplete, before the migration) |
| C05 the same with lower-case `%2f` | accepted, connects |
| C03 `postgresql://cnpg:Ab%2Bcd%2FEF%3Dgh%3D%3DZq8x@host/cnpgdb` (all encoded) | accepted; `migrate` → `migrated: (empty) -> 0004_event_blob`, exit 0 |
| C08 C04 with `?sslmode=disable` | accepted, connects |
| C06 `postgresql://cnpg@host/cnpgdb?password=<all encoded>` | accepted, connects |
| C02 `postgresql+psycopg://cnpg:Ab+cd/EF=gh==Zq8x@…` (raw `/`) | refused with the sentence |
| C01 the same with `postgresql://` | refused with the sentence. **At fa61473 it connected:** SQLAlchemy reads a raw `/` in the password correctly. |
| C07 `?password=Ab+cd/EF=gh==Zq8x` raw | the wrong-password sentence: `parse_qsl` turns `+` into a space |

- The CNPG `uri` key, pasted as it is, works. `postgresql://` is enough; `+psycopg` is not required, since SQLAlchemy 2.1 picks psycopg for `postgresql`.
- A hand-typed DSN with a raw `/` in the password is refused, where fa61473 accepted it. The refusal is defensible, because libpq misreads the same string. The sentence says to percent-encode "a special character" but does not say which ones. `+` and `=` work raw in the user info, and `/` does not. Naming `%2F` beside `%40` would spare the operator a round.
- C07 is the trap the sentence does not cover: a raw `+` in a **query** value is a space. The pages don't say so. Minor.

### New Breakage in the Fix Diff

1. **Serious: the round trip accepts a password with an unencoded `@` followed by `?`.** `src/previously/storage/postgres.py:930-969` (`_read_as_written`).
   - The docstring's premise, "Where it gives back the text as written, nothing was cut elsewhere" (`:934-935`), is false. N01-N05 are canonical URLs whose host is a password piece and whose query is the rest of the string. A comparison cannot tell them from a legitimate `host?query`.
   - The forms are pre-existing, since fa61473 printed them the same. But they are the class ruling T2-i set out to close: the reverse order of form 16.
   - Proposed, parse-based and not a guess: also require `dsn.count("@") == rendered.count("@")`.
     - The rendering writes at most one raw `@`, the user-info separator. Every `@` inside a user name, password, database or query value comes back as `%40`, and the host check already covers the host.
     - A raw `@` the writer left anywhere else, wherever the parser put it, makes the counts differ.
     - `proposal3.py`, parse only: N01-N05 and N09 are refused. Eleven legitimate forms stay accepted, among them plain, encoded specials, `?password=`, `?sslmode=…&connect_timeout=…`, `%40` in user and database, no user, the Go-encoded CNPG `uri`, IPv6, `?password=…%40…`, and `?options=-c%20…`.
   - Cost: a raw `@` in a query value (`?options=x@y`) is refused, and the sentence already says to encode query values.
   - Add N01 and N03 to the table. N03 shows that the query comparison alone can't do this.
2. **Serious: the new connect-time `ProgrammingError` branch quotes a password piece.** `src/previously/storage/postgres.py:284-294`.
   - `_first_line(error)` quotes psycopg's text, and that text names the rejected *key*. With an unencoded `&` in a `?password=` value, the key is a piece of the password:
     - N06: `invalid connection option "<B>"`;
     - N08: `missing "=" after "<B>" in connection info string`.
   - Both were clean at fa61473 (`MigrationPending`) and leak now, through `log` and `migrate`.
   - The round trip cannot see this: `password=<A>&<B>=<C>` is canonical.
   - Proposed:
     - in that branch, a fixed reason that quotes nothing, for example `connecting to {where} failed: the client library does not accept an option in the query of PREVIOUSLY_DSN`;
     - or check the query keys against psycopg's list of libpq keywords before connecting, and refuse with a sentence that names no key.
   - The self-advice of round 2 stays gone either way.
   - N07 (`&sslmode=<B>`, an `OperationalError`) is the pre-existing sibling. It needs a password that literally holds `&<libpq keyword>=`, so name it as a limit rather than fix it.
3. **Minor: both pages promise more than the code keeps.**
   - `docs/reference/cli.md:14` and `docs/reference/configuration.md:16`: "the password appears in neither". It does: N01-N08 (host, database, rejected key, rejected value), and N09/T2-j (port).
   - `cli.md:12` and `configuration.md:16` name "the value of a query parameter it rejects". Since this diff, the line also quotes a rejected **key** (`invalid connection option "…"`).
   - `configuration.md:19` and `cli.md:36` say a string with an unescaped `@ : / ? # %` in a part "is refused". At head, a raw `@`, `/` or `:` inside a query value is accepted (table form 6 `passfile=/tmp/…`; N01). The qualifier "so that it would be cut … elsewhere than its writer meant" is what fails in N01.
   - Neither page says that `+` in a query value reads as a space (C07).
4. **Minor (comment is a claim): the docstring of `_read_as_written`.** `postgres.py:933-949`.
   - "nothing was cut elsewhere" is refuted by N01-N05, see 1.
   - "a raw `@`, `?` … inside a part … does not [compare equal]" is false for a query value: the query is compared as `parse_qsl` pairs, which decode `%40` and `@` alike.
   - Lines 951-955 present the port check as closing the missing-`@host` case. With N09, a negative port passes it: `0 <= url.port <= 65535` would close that.
5. **Minor: the query clause has no test that it alone makes red.** `postgres.py:966`. See Finding 5. N25 (a newline inside a `?password=` value) is refused by that clause alone and would serve.
6. **Nit: `except (ArgumentError, ValueError)` around `create_engine`** (`postgres.py:1002`). After `_read_as_written` has parsed the string, only the `ArgumentError` of a missing dialect (table forms 26, 27, N20) reaches it. The `ValueError` half looks unreachable. Harmless, but the docstring at `:981-990` reads as if `create_engine` were the parser of record.

### Out-of-Scope Observations

1. A trailing newline (N22), which a secret file easily carries, is accepted as part of the database name. It prints a sentence that spans two lines. The table's `connect` check asserts one line, so it would catch this, but no form has the newline. It isn't a leak.
2. Table form 28 (`postgresql+psycopg2://`) is still a traceback. It carries no DSN content, as the report says.
3. The ruling T2-j limit holds as stated for `user:<≤5 digits>/db`, measured (N29). With N09 it isn't the only port residual. Once `port >= 0` is added, it is.
4. Other residuals I looked for and did not find:
   - With the count-of-`@` check from Breakage 1 added, every misparse of a password needs an unencoded `@` or a missing `@host`. A raw `? / : #` in a password is swallowed by SQLAlchemy's `[^@]*` and caught by the head comparison, measured with N26 and table forms 33 and 34.
   - What remains after both proposals:
     - T2-j (`user:<≤5 digits>/db`);
     - N07, a password literally holding `&<libpq keyword>=` inside `?password=`;
     - a password typed into the user name's place (`postgresql+psycopg://<PW>@host/db`), which libpq quotes as the user. That is not a parse problem, and the page names the user.

### Verdict

**Changes required.** Findings 3 and 4 are ADDRESSED. Finding 6 is ADDRESSED for the advice. Findings 1, 2 and 5 are PARTIALLY ADDRESSED.

The round-2 forms are all closed, and the CNPG `uri` as Go writes it is accepted. Still leaking, measured through `log` and `migrate`:
- N01-N05, an unencoded `@` then `?` in the password. The host and database print the password piece. Pre-existing, not closed by the round trip. Fix: `dsn.count("@") == rendered.count("@")`.
- N06 and N08, an unencoded `&` in a `?password=` value: the rejected key is quoted. **New in this diff**, through the connect-time `ProgrammingError` branch. Fix: a fixed reason there.
- N09, a `-`-prefixed all-digit password with `@host` forgotten, printed as the port, at any length. Beyond the T2-j limit. Fix: `port >= 0`.
- N07, a password holding `&sslmode=`: pre-existing; name it as a limit.

Also: the page sentence "the password appears in neither" (both pages) and the `_read_as_written` docstring premise, plus tests for N01, N03, N06 and N09.
