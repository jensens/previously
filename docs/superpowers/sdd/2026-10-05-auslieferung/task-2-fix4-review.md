## Task 2, fix round 4: re-review as an attack (2579eb5..9cdb5b8)

Read: the whole diff package; `_DSN`, `_ESCAPE`, `_PART`, `_VALUE`, `_url_of`, `from_dsn`, `_where` and `_transaction` at head; `storage/migrate.py` and `migrations/env.py` at head; rulings T2-j, T2-k and T2-l; the attacks of rounds 2 and 3; the "Fix round 4" section of the report; CloudNativePG's `pkg/specs/secrets.go` and `internal/controller/cluster_create.go` on `main`.
Ran: `pytest tests/test_migrate.py tests/test_cli.py tests/test_storage.py -k "migrate or no_form_of_the_connection or query or dsn" --no-cov -p no:randomly` → 137 passed.
Probes: a throwaway `postgres:17` (user `app`, database `probe`, `log_statement=all`), removed afterwards.
- 63 attack forms through `.venv/bin/previously log` as a process, 17 of them also through `migrate` (`scratchpad/probe4.py`).
- N01-N09 plus three port variants, each through `log` and `migrate` (`scratchpad/nforms.py`).
- Ten odd host names through both commands (`scratchpad/hosts.py`).
- Twelve legitimate forms against roles with real passwords (`scratchpad/legit.py`).
- What Go's `url.UserPassword` writes, measured with `go run` (`scratchpad/gourl/main.go`).
- `alembic upgrade head` in the checkout, and `previously migrate` from a wheel built out of `git archive HEAD` and installed into a fresh venv.
- Base comparison: `git archive 2579eb5 src` run with the same venv through `PYTHONPATH`.

Secrets were 20 hex characters (`<A>`, `<B>`, …), 20 letters (`<F>`) or 20 digits (`<D>`), drawn at run time; a leak is any 8-character run of one in stdout or stderr.
Not run: the six gates. The report claims them green. The tree, index and HEAD are unchanged (`git status --short` empty).

### Finding Verdicts

Round 3's numbered findings:

1. **Serious, the password reaches the message (N01-N05).** ADDRESSED. All five are refused through `log` and `migrate`, with no fragment, both in the table and in my own run.
2. **Minor, the page sentences.** ADDRESSED, with one nit. "The password appears in neither" is gone from both pages; the fixed reason replaces the quoted key; `+` in a query value is now refused rather than read as a space. Nit: `cli.md:14` says the accepted form "names that case", but `configuration.md:43-44` names the port and the host, not the database (G21 below).
3. **Minor, `@` in a user name.** Still ADDRESSED; table forms 20 and 21.
4. **Comment claims of `_read_as_written`.** ADDRESSED, by removal. The successor docstring has a narrower claim of its own; see Breakage 4.
5. **Test gaps.** ADDRESSED. N01-N09 are in the table, each through both commands. The four mutations the report names are plausible, but I did not rerun them. By reading, two more go red: `fullmatch` → `match` makes N01 connect to `<B>`, and dropping `1 <=` makes R05 red.
6. **`except (ArgumentError, ValueError)` around `create_engine`.** ADDRESSED: gone, and `create_engine` now gets a URL object.

Round 3's out-of-scope points: a trailing newline is now refused (G09, both commands), and `postgresql+psycopg2://` is refused, not a traceback.

N01-N09, measured at head through `log` and `migrate`:

| Form | Verdict |
|---|---|
| N01 `app:<A>@<B>?<C>@H/probe` | ADDRESSED: refused, clean |
| N02 `app:<A>@<B>/<C>?<E>@H/probe` | ADDRESSED: refused, clean |
| N03 `app:<A>@<B>?<C>=<E>@H/probe` | ADDRESSED: refused, clean |
| N04 `app:<A>@<B>:5432?<C>@H/probe` | ADDRESSED: refused, clean |
| N05 `app:<A>@[<B>:<C>]?<E>@H/probe` | ADDRESSED: refused, clean |
| N06 `?password=<A>&<B>=<C>` | ADDRESSED: refused (key `password`), and the connect-time branch quotes nothing anyway (R02, G16) |
| N07 `?password=<A>&sslmode=<B>` | ADDRESSED as written: refused. Its sibling, a secret written as the value of an allowed key, stays (residual 3, G12/G13) |
| N08 `?password=<A>&<B>%20<C>=<E>` | ADDRESSED: refused, clean |
| N09 `app:-<D>/probe` | ADDRESSED: refused. Also `app:+<D>`, `app:<D>` and `app:0<A>` are refused, clean |

### Attack results (form → printed, verdict)

`log` unless noted. Every case exits 2 unless noted. `refused` means the one sentence of `_unreadable()`. `H` is the session server. A password is `<PW>`, or the piece's letter.

**The grammar, character by character** (`postgres.py:951-968`):
- The character classes are explicit ASCII ranges with `-` escaped (`\-`): no `\w` or `\d`, and no `A-z`. `re` without `IGNORECASE` matches `[A-Za-z]` only in ASCII.
- G11 a fullwidth-digit port (`:５４３２`) and G11b Arabic-Indic digits → refused. G11c a raw `ö` in the host → refused.
- `fullmatch` is used, not `match` or `$`. G09 a trailing `\n` → refused, through `log` and `migrate`. G09b `\n` after a query → refused.
- G06 `POSTGRESQL+PSYCOPG://` and G06b `postgresql+Psycopg://` → refused, clean.
- G33 `#<B>` after the database → refused, clean.
- G24 `%68` in the host → refused: the host takes no escapes.
- G26 a trailing `&`, G27 an empty `?` and G17 an upper-case key → refused.
- G38 an empty user (`:<A>@H`) → refused.
- G37 port 65536 → refused. G32 `:0<port>` reads as the port and connects, clean.
- G41 an IPv6 zone `[fe80::1%25lo]` → refused (a legitimate form refused; nobody needs it here).

**Escapes decoded after the check (intended):**
- G01 `%40` in the password → `connecting to database probe at H failed: … password authentication failed for user "app"`. Clean, through both commands. The decoded `@` goes into `URL.create(password=…)` and from there into psycopg's keyword arguments; nothing re-parses it.
- G02 `/pro%2Fbe%3Fx%40y` → `… database pro/be?x@y at H …`. Clean, both commands.
- G03 `/host=nohost.invalid%20port=1`, G03c `/dbname=x` → the server got the literal name: libpq does not expand a database name into a connection string on this path (it still connected to H). Clean.
- G03b `/postgresql:%2F%2Fx@nohost.invalid` → refused, because of the raw `@` and `:`.
- G30 `%2541` in the password reads as the literal `%41`, with no second decode. Clean.
- G48 `%5C%27` (`\'`) in the password → wrong-password sentence. psycopg's quoting holds. Clean.
- G46 `application_name=a%20password%3D<B>` → wrong-password sentence. No injection into the conninfo: the server got the user-part password. Clean.

**Control characters and Unicode:**
- G05 `%0A`, G05b `%7F` and G05c the overlong NUL `%C0%80` in the password → all refused, clean.
- G05d `%E2%80%A8` (U+2028) in the password → accepted. Wrong password, clean.
- G34 a raw fullwidth `＠` → refused. G34b the same encoded (`%EF%BC%A0`) → a literal password character, no split. Clean. No Unicode normalization anywhere; none is needed for the cut.
- G04 `/pro%C2%85be` (U+0085 NEL) and G04b `/pro%E2%80%A8be` (U+2028) → accepted, and the sentence prints the database with that character. `str.splitlines()` counts **2 lines**. Not a leak; see Breakage 1.
- G04c `/pro%C2%9B31mbe` (U+009B, the C1 CSI) → printed raw. Not a leak; see Breakage 1.

**Query keys whose values libpq echoes:**
- G12 `?sslmode=<A>` → `… failed: connection is bad: invalid sslmode value: "<A>"`. **Prints `<A>`, through both commands.** Residual (3).
- G13 `?require_auth=<A>` → `… invalid require_auth value: "<A>"`. **Prints `<A>`, through both commands.** Residual (3); the report names only `sslmode`.
- G13b `?channel_binding=<A>` → `… invalid channel_binding value: "<A>"`. **Prints `<A>`, through both commands.** Residual (3).
- G45 `?sslmode=disable%26password%3D<B>` → `… invalid sslmode value: "disable&password=<B>"`. **Prints `<B>`.** The value is decoded before libpq quotes it; same class.
- G47 `?sslmode=a%27%20password%3D<B>` → `… invalid sslmode value: "a' password=<B>"`. **Prints `<B>`, through both commands.** Same class; no conninfo injection.
- G16 `?connect_timeout=<A>` → `… the client library refused a query parameter of PREVIOUSLY_DSN`. Clean, through both commands.
- G16b `connect_timeout=-<D>` → libpq accepts it. Clean.
- G15 `application_name=<B>` → clean.
- G14 and G14b `sslrootcert`, `sslcert` and `sslkey` = `/tmp/<A>` → `server does not support SSL, but SSL was required`. Clean against this server. Against a TLS server libpq names the file it cannot open; that is residual (3) only when a secret is written as a path.

**Mis-typed strings (the T2-j class):**
- G19 `app:12345/probe` → `… database probe at app:12345 failed: failed to resolve host 'app' …`. T2-j as ruled.
- G51 `app:<D>/probe` → refused.
- G20 `app:<F>@<A>/probe` (password `<F>@<A>`, `@host` forgotten) → `… database probe at <A> failed: failed to resolve host '<A>' …`. **Prints `<A>`, through both commands.** Residual (2), named on `configuration.md:44`.
  - G22 `app:<F>@<A>` and G49 `app:<F>@<D>/probe` are the same, **printing `<A>` and `<D>`**.
- G21 `app:12345/<A>` (password `12345/<A>`, with both `@host` and the database forgotten) → `connecting to database <A> at app:12345 failed: …`. **Prints `<A>`, through both commands.** Not named anywhere; see Residuals.
- G21b `app:12345?sslmode=<A>` → `… database (default) at app:12345 …`, clean, because the host fails before the value is read.
- G42 `app:<A>@[<B>]:port/probe` → `… at <B>:port failed: failed to resolve host '<B>' …`. The IPv6 class takes any run of hex digits, `:` and `.`, so a hex piece in brackets is printed as the host. Writing brackets is not a typo shape, so I file it under residual (2) rather than as a new class.

**A secret in a part a message prints (not a parse problem):**
- G50 `<F>:app@H` (user and password swapped) → `password authentication failed for user "<F>"`. **Prints `<F>`.** Residual (3).
- G52 `app@H/<F>` (password in the database's place) → `connecting to database <F> at …`. **Prints `<F>`.** The same class as (3), but our own sentence prints it, not libpq. Not named by the report.
- G18 `<F>@H` with no password → `fe_sendauth: no password supplied`, and the user is not named. Clean. A server that knows no such role does name it, per the report.

**Host names** (`hosts.py`, both commands):
- `.`, `..`, `a..b`, `.a`, and a 64- or 300-character label → **exit 1, an 80-line traceback** ending in `UnicodeEncodeError: 'idna' codec can't encode …: label empty` or `label too long`. No piece of the password is in it.
  - The base commit gives the same traceback for `a..b`, so it is pre-existing.
- `a.`, `-a`, `_`, `-` and five labels of 63 → one sentence, exit 2, clean.

### Legitimate forms

**CloudNativePG.**
- Its secret's `uri` is `url.URL{Scheme: "postgresql", User: url.UserPassword(user, password), Host: host, Path: dbname}.String()` (`pkg/specs/secrets.go`).
- The password it generates is `password.Generate(64, 10, 0, false, true)` (`internal/controller/cluster_create.go`, sethvargo/go-password): 64 characters, **no symbols**, only letters and digits. A generated `uri` therefore never holds a special character in the password.
- A special character arrives only with a password the operator supplies as a secret.
- Measured with `go run`, Go writes `$&+,;=`, the letters, the digits and `-._~` raw in the user info. It writes everything else as upper-case `%XX`, `!*'()` and the space (`%20`) included.

| Form | Result |
|---|---|
| L01 `postgresql://cnpg:Ab+cd%2FEF=gh$,;==Zq8x@H/cnpgdb` (Go's encoding of `Ab+cd/EF=gh$,;==Zq8x`) | `migrate` → `migrated: (empty) -> 0004_event_blob`, exit 0; `log` exit 0; `migrate` again → `up to date: 0004_event_blob` |
| L02 the same with `postgresql+psycopg://` | `log` exit 0 |
| L03 the same with `?sslmode=disable` | `log` exit 0 |
| L04 the same with `?sslmode=require` | accepted; `… server does not support SSL, but SSL was required` (this server has no TLS) |
| L05 `postgresql://amp:Ab&cd+ef=Zq8xYYYY@H/ampdb` (Go's form, raw `&`) | **refused.** Ruling T2-l is not implemented at head; the ruling post-dates the round, and table form R09 still pins the refusal |
| L06 the same with `%26` | `migrate` exit 0, `log` exit 0 |
| L07 `[::ffff:127.0.0.1]:port` | `log` exit 0 |
| L08 `[::1]:port` | accepted; `Connection refused` (the container was bound to 127.0.0.1 only) |
| L09 host `postgres`, L10 `db_1`, L11 `c-rw.ns.svc.cluster.local` | accepted; one sentence, `failed to resolve host '…'` (nothing of those names here) |
| L12 `postgresql+psycopg://…/psydb?application_name=previously&connect_timeout=5` | `migrate` exit 0, `log` exit 0 |

Refused although legitimate, by reading the grammar and checked with `_url_of`:
- `?application_name=my+app` is refused, and `my%2Bapp` is accepted.
- `?application_name=a=b` is refused.
- An IPv6 zone ID is refused (G41).

### Migrate's connection hand-off

- **Installed package.** A wheel built from `git archive HEAD` (`SETUPTOOLS_SCM_PRETEND_VERSION=0.0.1`) and installed into a fresh venv:
  - `previously migrate` with `%72ightpw` → `migrated: (empty) -> 0004_event_blob`, exit 0; again → `up to date`;
  - with a wrong password, one sentence and exit 2, and no fragment.
- **`alembic` in a checkout.** `uv run --frozen alembic upgrade head` with `PREVIOUSLY_DSN` holding `%72ightpw` runs `0001`→`0004`, exit 0, and `alembic current` → `0004_event_blob (head)`. The old `env.py` branch is intact: `attributes` is empty there.
- **One transaction, the lock held across it.** I measured this in the server's statement log for a fresh database.
  - Backend 147: `SELECT pg_advisory_lock($1)`, then the read of `alembic_version`.
  - Backend 148: `BEGIN ISOLATION LEVEL READ COMMITTED`, `CREATE TABLE alembic_version`, every revision's DDL, `INSERT` `0001_log`, then `UPDATE`s to `0002`, `0003` and `0004`, then **one** `COMMIT`.
  - Backend 147: `SELECT pg_advisory_unlock($1)`, after that `COMMIT`.
  - Alembic sees the external transaction, and its `begin_transaction` adds none of its own.
  - The two-waiter lock test is among the 137 that passed.

### New Breakage in the Fix Diff

1. **Minor: an escape can still put a line break or a C1 control into a printed part.** `src/previously/storage/postgres.py:951`, `_ESCAPE`.
   - The comment above it (`:945-950`) gives keeping the sentence on one line as the reason for refusing control escapes. But `%C2%85` (U+0085), `%E2%80%A8` (U+2028) and `%E2%80%A9` decode to characters that `str.splitlines()` and many log shippers treat as line ends. `%C2%80`-`%C2%9F` are C1 controls (U+009B is CSI).
   - In the database name, which the sentence prints (G04, G04b, G04c), the table's own `len(err.splitlines()) == 1` check would fail on them, but no form tries.
   - It is not a password leak. The fix is to check the decoded parts for `unicodedata.category(c) in {"Cc", "Zl", "Zp"}`, which costs no legitimate name.
2. **Minor, pre-existing: a host with an empty label or a label over 63 characters is a traceback, exit 1.** `postgres.py:964` (the host class `[A-Za-z0-9_.\-]+`).
   - The cause is psycopg's `getaddrinfo` raising `UnicodeEncodeError` from the `idna` codec (`a..b`, `.`, `.a`, a 64-character label). That happens inside `engine.begin()`, and `_transaction` does not catch it.
   - No password is in it, and the base commit does the same. Now that the grammar owns the host, it could require labels of 1-63 characters: `[A-Za-z0-9_-]{1,63}(?:\.[A-Za-z0-9_-]{1,63})*\.?`.
3. **Minor: the refusal sentence does not say what a query value may hold.** `postgres.py:900-916`.
   - A value with a raw `+`, `=`, `&`, space or `:` is refused, such as `application_name=my+app`.
   - The sentence speaks only of the user name, the password, the database name and the allowed keys. An operator whose key is allowed cannot tell from it what to change. `configuration.md:37` does say it.
   - One clause such as "and percent-encode a query value as well" would do.
4. **Nit (a comment is a claim): `_url_of`'s docstring** (`postgres.py:986-989`) says "The one thing a grammar cannot tell apart … is `user:12345/database`".
   - Residual (2) (`app:<F>@<A>/db`, G20) is a second thing, and the page names it.
   - G21 (`app:12345/<A>`, where the rest prints as the database) is a third, and nothing names it.
   - Likewise, `configuration.md:43` names the host and the port, not the database.
5. **Nit, by reading, not measured: a non-`OperationalError` raised at `COMMIT` of the upgrade escapes `_refusals`.** `src/previously/storage/migrate.py:134`.
   - `with storage.begin() as upgrade, _refusals(head):` exits `_refusals` before `storage.begin()` commits. A `ProgrammingError` at commit would read as `MigrationPending`, and an `IntegrityError` from a deferred constraint as a traceback.
   - Before, Alembic committed inside the one `try`. None of the four revisions can raise either at commit, as far as I can tell. Swapping the order, `with _refusals(head), storage.begin() as upgrade:`, would not do as it stands: a connection-time `ProgrammingError` would then become `MigrationFailed`. So leave the order and name it in the comment, or translate in `_refusals` only once `connected`.

T2-l is not breakage. The head does what ruling T2-k said, and T2-l arrived after the round. It is the open item for the next round:
- add `&` to the class for the user and the password;
- flip R09 to `connect`;
- add `&` to the list in the refusal sentence (`postgres.py:900-916`) and on `configuration.md:34`, and drop "`%26` for `&`" there;
- the test `test_the_refusal_lists_the_query_keys_from_dsn_accepts` is unaffected.

`&` is safe before `@`: it is special only after `?`, and `?` cannot stand in the user part. With the `@host` forgotten, `app:a&b/db` still fails the digit-only port.

### Residuals

Every residual I found is of a kind the rulings or the report already name, except G21 and G52, which are new variants of named classes:

- **T2-j, as ruled:** `app:12345/probe` → host `app`, port `12345` (G19).
- **T2-j variant, new, not named:** `app:12345/<rest>` → `<rest>` printed as the database (G21, both commands).
  - It takes a password that starts with up to five digits and then a raw `/`, with both the `@host` and the database forgotten.
  - Three mistakes at once. It needs one more clause on `configuration.md:43` (and in `_url_of`'s docstring), not code.
- **Residual (2), named:** a raw `@` in the password with the `@host` forgotten → the rest is printed as the host (G20, G22, G49, both commands). G42, a hex piece written in brackets, is the same shape.
- **Residual (3), named in kind, broader than the report says:**
  - every allowed key whose value libpq validates quotes that value, decoded: `sslmode`, `require_auth` and `channel_binding` (G12, G13, G13b, G45, G47, both commands);
  - a password typed into the user's place is quoted as the user (G50);
  - a password typed into the database's place is printed by our own sentence (G52), a variant the report doesn't list.
  - None is a mis-parse: the string is read as written.
- **Residual (4), named:** `alembic` in a checkout parses with SQLAlchemy. It works (measured), it is not a `previously` command, and it is outside the goal.
- **Not a leak:** the idna traceback (Breakage 2) and the line breaks in a printed database name (Breakage 1).

I found no form, through `log` or `migrate`, in which the grammar cuts a correctly typed string differently from its writer and a password piece gets printed. The N01-N09 class is closed.

### Verdict

**Approve on the leak goal; one ruling still to carry out.**
- N01-N09 and every minor finding of round 3 are ADDRESSED, measured through `log` and `migrate`.
- The CloudNativePG `uri` as Go writes it migrates (exit 0), and so does the installed wheel. `alembic upgrade head` in a checkout still works.
- The upgrade is one transaction, with the advisory lock held on its own connection until after the `COMMIT`.

Open for the next round:
- **T2-l:** a raw `&` in the user part is still refused (L05, table R09). CloudNativePG's generated passwords never hold it; an operator-supplied one can.
- Minor: Breakage 1 (line-break and C1 escapes in a printed part); Breakage 3 (the sentence says nothing of query values).
- Pre-existing: Breakage 2 (idna traceback).
- Nits: Breakage 4 and 5; name G21 beside T2-j on the page and in the docstring.
