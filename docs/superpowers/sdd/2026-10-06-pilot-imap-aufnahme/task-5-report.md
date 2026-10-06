# Task 5 report: IMAP connector and `previously ingest imap`

Status: DONE_WITH_CONCERNS. Commit: e26551d (base b4e5a8c).

## What was built

- `src/previously/connectors/__init__.py` (new), and `src/previously/connectors/imap.py` (new).
  - `ImapConnector(*, host, port, user, password, folder, ssl_context, timeout=TIMEOUT)`: the signature from the brief, plus one optional keyword, `timeout` (60 s by default). It is there so that a test can measure the timeout in 1 s.
  - The connector's `name` is `imap:<user>@<host>/<folder>`.
  - The position is `{"uidvalidity", "uid"}`.
  - `found_in` is `{"connector": name, "uidvalidity", "uid"}`.
  - `encode_folder` and `decode_folder` implement modified UTF-7.
  - `ImapError(PreviouslyError)`, so `main` turns it into one sentence and exit code 2.
  - `PORT = 993` and `TIMEOUT = 60.0`.
- How a fetch runs:
  1. `IMAP4_SSL(host, port, ssl_context=…, timeout=…)`.
  2. `login`, with the user as a quoted string.
  3. `select(<"encoded">, readonly=True)`, which sends EXAMINE.
  4. UIDVALIDITY from the EXAMINE answer.
  5. `UID SEARCH UID n+1:*` without parentheses. The UIDs that come back are filtered to `> n`.
  6. One `UID FETCH <uid> (UID INTERNALDATE BODY.PEEK[])` per mail, yielded lazily.
  7. INTERNALDATE is parsed with a fixed English month table, not `strptime %b`, which depends on the locale.
  8. `logout` in a `finally` block, with errors suppressed.
- `cli.py`:
  - `Command("ingest", "take in new mail from an IMAP folder", …)` sits after `append`, with the second level `imap`.
  - `_imap_port` defaults to 993 when the variable is unset or empty, and refuses anything else that is not 1–65535 in ASCII digits.
  - `_imap_connector` always passes `ssl.create_default_context()`.
  - `_cmd_ingest` reads settings in this order: the five IMAP settings, the recipient check, the DSN, then the five store settings. All of that happens before any connection, and the identities are never read.
  - Standard output gets one line, `imap: <a> appended, <k> known, <v> variants, up to uid <uid>`. Standard error gets `variant of <message-id>: event <id>` for each variant.
- `.importlinter`:
  - `previously.connectors` is a layer of its own between `cli` and `core`.
  - The layers contract is renamed to `Layers: cli, connectors, core beside migrations, storage, contract`, because the name is what the gate prints.
  - New contract `only-imap-knows-imaplib`: the whole package is the source, and `previously.connectors.imap -> imaplib` is exempt by name.
  - The header comment now reads "Seven of the eight".
- `pyproject.toml`: the marker `imap`. The `T201` count is now thirty-six, measured with the command written in the comment.
- `tests/conftest.py`: the session fixture `mail_server` (GreenMail 2.1.14, IMAPS only, user `pilot`, password drawn at run time, its own certificate; see below) and the per-test fixture `imap_folder` ("Kunde Müller" created anew, with `plain`, `reply`, `html_only` and `forwarded` from `tests/mails/` at UIDs 1–4).
- `tests/mailserver.py` (new helper module, like `mailfiles.py`):
  - `MailServer`: an admin session, `recreate`, `append`, `seen`, `remove`, `uidvalidity` and `connector`.
  - `Relay`: a TCP relay that breaks the connection after `limit` bytes from the server, or with `hold` keeps it open and silent.
- `tests/test_imap.py` (new, 16 tests): folder names, including the RFC 3501 example and a hypothesis round trip; fetch-all-then-new; a mail removed during a fetch is passed over; a missing folder; a connection refused; a timeout; no `\Seen` after a run; a changed UIDVALIDITY.
- `tests/test_cli.py` (+21 tests): the brief's line and a second run with `0 appended`, then `chronicle` shows the subjects; the variant on standard error; the wrong password, in ASCII and non-ASCII; certificate and host-name verification; the dropped connection; each missing setting before any connection (11 parameters) and its control.
- `tests/test_contracts.py`: an imaplib probe in `core` and one beside `connectors.imap`.
- `tests/test_docs_references.py`: the refused port, the seven IMAP errors (against `ImapError` in `connectors/imap.py`), the variant notice, and the standard-output line (against the one f-string in `cli.py` containing ` appended, `) are held against the code. The docstring counts are updated.
- Docs:
  - `cli.md`: twelve subcommands, an `ingest` row in the exit codes table, and a section `## \`ingest\``.
  - `configuration.md`: thirteen variables, `ingest imap` added to the "Missing at" column of the store settings and the recipient, and a new section "Mail folder settings". The heading avoids "IMAP" because vale's `HeadingAcronyms` flags it.
  - The tutorial's test block is retyped under ruling P-1: a placeholder, a green plain `uv run pytest` (1026 passed in 179.78s), then the whole block typed without `rootdir:`. The sentence about the test containers now names GreenMail.

## Decisions beyond the brief (please confirm)

1. **UIDVALIDITY comes from the EXAMINE answer, not from `STATUS`.**
   The brief says "status für UIDVALIDITY".
   The UIDs the run then reads belong to the selected session. A separate STATUS can see a folder that was recreated between the two commands.
   RFC 3501 makes `[UIDVALIDITY]` in the SELECT/EXAMINE answer mandatory. If it is missing, `ImapError` is raised.
2. **A refused login quotes nothing of the server's answer.**
   GreenMail says `LOGIN failed. Invalid login/password for user id pilot`.
   Not quoting it makes "the password never appears" a guarantee by construction instead of a trust in the server. Both refusals use `from None`: the chained `UnicodeEncodeError` holds the whole LOGIN command line, password included.
3. **A connection that broke off quotes no `imaplib` text. This is a finding, measured.**
   With Python 3.14.3 and a connection cut in the middle of a literal, `imaplib.read()` leaves what it read in `_readbuf`. It then re-reads the mail as a response and aborts with `unexpected response: b'To: pilot@example.org'`, a header line of the mail.
   That would have put mail content into CronJob logs.
   The sentence is now `the connection to the IMAP server <host:port> broke off`. For an `OSError`, it adds the system's reason, for example `The read operation timed out`.
   The comment at `_speaking` gives the measurement, and the mutation "abort text quoted" turns the dropped-connection test red.
   (This looks like a CPython bug: the buffer is not trimmed after a short read at EOF. A report upstream could be worth it.)
4. **A non-ASCII password is caught.** `imaplib` encodes the command as ASCII, so without the catch the run ended in a traceback whose message names the character and its position. The sentence is now `the login of <user> at the IMAP server <host:port> holds a character other than ASCII, which the IMAP login cannot carry`.
   Ordinary use can hit this (Mailu allows such passwords), so it is handled and tested.
5. **`timeout` (60 s per socket operation).** Without it, a server that stops answering holds a CronJob with `concurrencyPolicy: Forbid` forever. It is tested through the relay's `hold` with 1 s.
6. **`up to uid 0`** means the folder has given nothing yet: no watermark and an empty folder. A UID is never 0. This matches `up_to_id 0` in `project`, and `cli.md` says so.
7. **A mail that leaves the folder between SEARCH and FETCH is passed over.** This is ordinary concurrency, for example the maintainer moving mails during a run. It is tested deterministically: the generator is lazy, the test removes UID 2 after the first `next()`, and the run continues with 3 and 4.
8. The user goes to LOGIN as a quoted string (`imaplib` sends it raw), and so does the folder name.
9. Contract name: `Layers: cli, connectors, core beside migrations, storage, contract`. The first attempt wrapped past 80 columns in the gate output.

## How TLS trust was solved in the test

GreenMail's built-in certificate is self-signed with `CN=GreenMail selfsigned Test Certificate`, `O=Icegreen Technologies`, and no SAN. Any host-name check refuses it, as measured.
So the fixture sets the container's entrypoint to `bash -c "keytool -genkeypair … -dname CN=localhost -ext SAN=dns:localhost,ip:127.0.0.1 … && exec ./run_greenmail.sh"`, using the JDK `keytool` inside the image.
`GREENMAIL_OPTS` points at that keystore, with a password drawn at run time, and defines the user (`-Dgreenmail.users=pilot:<pw>@example.org`, without `auth.disabled`).
The test exports the certificate with `container.exec(["keytool", "-exportcert", "-rfc", …])` into `tmp_path`.

- The connector tests pass `ssl.create_default_context(cafile=<pem>)`, so the context is verifying, not unverified.
- The CLI tests set `SSL_CERT_FILE=<pem>`. `ssl.create_default_context()` reads it through OpenSSL's default verify paths. Python 3.14's `VERIFY_X509_STRICT` accepts the keytool EC certificate (measured).
- The CLI tests connect to `127.0.0.1`, which the SAN names. Without `SSL_CERT_FILE`, they get `does not verify: self-signed certificate`. With `127.0.0.2`, they get `IP address mismatch, certificate is not valid for '127.0.0.2'.`

No software was installed on the host, and no dependency was added.

## Review Focus 4: the dropped connection

I did not stop the container from a thread.
- The session's GreenMail would be gone for every later test.
- Where the stop lands depends on thread scheduling: before LOGIN, between two mails, or after the run. A whole fetch of the four test mails is 7303 bytes and takes milliseconds.

Instead, `Relay` sits between the CLI and GreenMail and ends the connection after a byte count. The test appends two invented mails of about 1 MiB each (UIDs 5 and 6). The limit is `len(mail 5) + 512 KiB`, so the break falls about half a MiB into UID 6, independent of timing.

Result:
- Exit code 2 and exactly `Error: the connection to the IMAP server 127.0.0.1:<port> broke off`.
- Neither the password nor `example.org` appears in the output.
- The watermark is still at UID 4, where the last appended batch left it, and there are still 5 events.
- The next run without the relay prints `imap: 2 appended, 0 known, 0 variants, up to uid 6`.

The host is part of the connector's name and the port is not, so the relay run keeps the watermark of the direct runs.

## Mutation measurements

Each mutation was applied by a script in the scratchpad, the named tests were run, and the file was restored. The control was the unmutated tree: 9 tests passed.

| Mutation | Result |
|---|---|
| `BODY[]` instead of `BODY.PEEK[]` (the brief's mutation) | **green** — see below |
| Folder opened read-write (`readonly=False`) | **green** |
| Both together | `test_no_mail_is_marked_as_read_by_a_run` **red** |
| UIDVALIDITY ignored in `_after` | `test_a_folder_made_anew_…` red; control `test_the_connector_fetches_…` green |
| Password in the login refusal message | wrong-password test (ASCII) red; non-ASCII case green |
| CLI passes an unverified context | `test_ingest_imap_verifies_…` red; `takes_in_the_folder` green |
| CLI with `check_hostname = False` | `verifies_…` red (the 127.0.0.2 half); `takes_in` green |
| CLI touches the database before reading the settings | 10 of 11 missing-setting cases red and the control red. The `PREVIOUSLY_DSN` case stays green, because it is refused there anyway |
| Fetch ends quietly on `ImapError` | dropped-connection test red; `takes_in` green |
| `imaplib`'s abort text quoted again | dropped-connection test red (mail header line in stderr) |
| No `timeout` passed to `IMAP4_SSL` | `test_a_server_that_stops_answering_…` red (thread still alive after 15 s) |
| A vanished mail raises instead of being passed over | `…leaves_the_folder…` red; `fetches_every_mail` green |
| `UnicodeEncodeError` not caught | non-ASCII wrong-password case red; ASCII case green |
| Counts swapped in the stdout line | `takes_in` and `variant` tests red |
| Variant notice not printed | variant test red; `takes_in` green |
| `&` not escaped in `encode_folder` | that RFC case red; three other cases green |
| Contract exemption as the pattern `previously.connectors.** -> imaplib` | contract test `[connectors]` red; `[core]` green |
| UID filter `> after` removed | **green** — see below |

- **The brief's `\Seen` mutation alone stays green, and that is measured, not overlooked.** GreenMail honours EXAMINE: `BODY[]` in a read-only folder sets no flag. In the spike, `BODY[]` after a read-write SELECT did set `\Seen`. The folder is guarded twice, and each guard alone keeps the test green. Only removing both turns it red. The module docstring states this.
- **The UID filter cannot be measured against GreenMail.** GreenMail answers `UID n:*` above the highest UID with nothing (`search 5:*` on three mails gave `b''`). RFC 3501 says `n:*` includes the highest UID, and the filter exists for servers that follow the RFC there (Dovecot, so Mailu). This is named, not chased.

## Gates (final tree, each run separately)

1. `uv run ruff check .`: All checks passed.
2. `uv run ruff format --check .`: 88 files already formatted.
3. `uv run pyright`: 0 errors, 0 warnings, 0 informations.
4. `uv run lint-imports`: Contracts: 8 kept, 0 broken.
5. `uv run pytest --cov --cov-report=term-missing`: 1026 passed in 174.94s, TOTAL 98%.
   - `connectors/imap.py` is at 93%.
   - The missing lines are server-misbehaviour paths: a bad greeting, an abort during LOGIN, a missing UIDVALIDITY, a non-date INTERNALDATE, a BAD response, malformed FETCH tuples, impossible calendar dates, and a str-valued error.
6. Docs:
   - `make -C docs html`: build succeeded, exit 0.
   - `make -C docs vale`: 0 errors, 0 warnings, 0 suggestions in 31 files.
   - `make -C docs linkcheck`: exit 0, 0 broken.

`pip-audit` was not run; it is not a gate.

## Concerns

1. **`docs/explanation/module-boundaries.md` now lags.** Its typed `lint-imports` output still says 7 contracts and the old layers name. Its diagram and edge counts ("the order permits nine edges", "Seven of the nine exist") do not include `connectors`. This belongs to task 6, which owns the docs and stays in the same PR, but it has to be retyped from a run.
2. **README still says "the eleven commands".** Task 6.
3. `CLAUDE.md`'s "six contract names" sentence is now two contracts behind. I did not edit it, as instructed.
4. **The CPython `imaplib` buffer bug (decision 3)** is worked around in our message only. It does not corrupt data: the run aborts, and nothing of the broken batch is appended. Upstream report: maintainer's call.
5. **Named, not chased** (misuse, or servers that misbehave):
   - A UID SEARCH answer longer than `imaplib`'s 1,000,000-byte line limit aborts. That is roughly 150,000 mails in one folder.
   - A FETCH answer without a literal (an empty `BODY[] ""`) is treated as a vanished mail.
   - A server that omits UIDVALIDITY or sends an INTERNALDATE that is not a date raises `ImapError`.
   - An IPv6 host prints as `::1:993`.
   - GreenMail counts UIDVALIDITY in seconds, so a folder recreated within the same second keeps its UIDVALIDITY. That is a GreenMail problem; the test loops until it changes.
   - A recreated empty folder leaves the old watermark and its `up to uid` in place until a mail arrives, which is harmless.
6. `imaplib` keeps the last ten command lines, the LOGIN with the password among them, in `_cmd_log`. It prints them only at `Debug >= 1`, which is never set. Nothing writes them out.
7. `tests/mailserver.py` is a third helper module beside `conftest.py` and `mailfiles.py`. Tests need the types, and the conftest docstring advises against importing from `conftest`.
8. Suite time went from about 142 s to about 175 s. GreenMail starts in about 3 s; the rest is the new tests.

# Fix round 1

Commit: bfe301a (on e26551d). Status: DONE.

## I1: the INTERNALDATE parser is pinned by value

What changed:
- `_internaldate` is now the public `parse_internaldate(text) -> datetime | None`, with a docstring that says why it is public.
- **How a rejection surfaces:** the function returns `None` for a text that names no moment. That covers another form, a month that is not one of the twelve English abbreviations, a date or hour that does not exist, and a zone of 24 hours or more.
  - It returns `None` rather than raising because only the caller knows which mail the text belongs to.
  - The connector turns `None` into `ImapError` ("the IMAP server … gave uid N the INTERNALDATE '…', which is not a date"), as before. The run stops there with exit code 2, the watermark stays before that mail, and nothing is written.
- One addition: the month is now matched without regard to case (`06-OCT-2026`). RFC 3501's grammar is ABNF, and ABNF quoted strings are case-insensitive (RFC 5234). Before, a server writing `OCT` would have stopped every run.
  - The comment at `_DATE` says this.
  - The test pins it.

Tests (`tests/test_imap.py`):
- `test_an_internaldate_is_read_as_the_moment_it_names` checks five cases. Each is compared with `==` and with `utcoffset()`.
  - `" 6-Oct-2026 10:15:00 +0200"`: a blank-padded day.
  - `"05-Jan-2026 23:30:00 -0230"`: January, with a negative offset that has minutes.
  - `"31-Dec-2026 00:00:59 +0545"`: December, with a positive offset that has minutes.
  - `"29-Feb-2028 12:00:00 +0000"`: a leap day.
  - `"06-OCT-2026 10:15:00 +0200"`: the month in capitals.
- `test_a_text_that_names_no_moment_is_no_internaldate` checks eight cases that must return `None`:
  - `Okt` and `Mai`, two German months;
  - 30 February;
  - hour 25;
  - zone `+2400`;
  - no zone;
  - an ISO 8601 text;
  - the empty string.
- `test_the_connector_hands_over_the_moment_the_server_received_a_mail`: GreenMail `APPEND`s a mail with `"05-Jan-2026 23:30:00 -0230"`, and the connector returns `2026-01-06 02:00:00+00:00`. GreenMail keeps the instant and writes the zone as `+0000`, as the review measured, so only the unit cases catch the sign.
  - `MailServer.append_dated` is new in `tests/mailserver.py` for this test.

Mutations (scratch script; file restored each time; control: 17 passed):

| Mutation | Red | Green control |
|---|---|---|
| `_MONTHS` with `start=0` | All 5 read cases, the GreenMail case, and the `30-Feb` refusal (read as 30 January) | The other 7 refusals, and `fetches_every_mail` (an October mail read as September still has a zone) |
| Zone sign swapped | The 4 read cases with a non-zero offset | The `+0000` case, all refusals, the GreenMail case (UTC, as predicted), `fetches_every_mail` |

## M1: the escaping of `"` and `\` in a folder name

- New test `test_a_folder_name_with_a_quote_or_a_backslash_is_read`, with the folders `Kunde "Müller"` and `Back\slash Ä`. Each is created, one mail is appended, and the connector fetches it.
- The test helper `mailserver.quoted` now escapes on its own, written out rather than borrowed from the connector, so the folder is set up independently of the code under test.
- Mutation `_quoted` without escaping: both cases red. The control `fetches_every_mail` stays green.

## M4, M5, M6: three comments corrected against the code

- **M4**, docstring of `_uids`: it now reads "The search is `UID n:*` as it stands; GreenMail refuses it inside parentheses".
- **M5**, comment in `_login`: `imaplib` encodes each argument on its own (`imaplib.py:1107-1110`, CPython 3.14.3). So the chained `UnicodeEncodeError.object` is the one argument that would not encode. It is the quoted password only when the password is the argument with the non-ASCII character. The `from None` stands either way.
- **M6**, timeout test docstring: "measured on 2026-10-06 over three runs, … 7301 to 7303 bytes …, first mail through at 3575 to 3577 — the count moves by a byte or two per run". The three runs are mine and the review's two.

## M7: `configuration.md`, `PREVIOUSLY_IMAP_FOLDER`

- The table row now says "The full name of the folder on the server, in plain characters, such as `Kunde Müller`; see below."
- A new paragraph explains:
  - The name is the server's. At the top level it is the name a mail client shows.
  - Inside another folder, the name holds the parents, each followed by the server's hierarchy delimiter (`Kunden.Müller` with `.`, `Kunden/Müller` with `/`). The server names the delimiter in its answer to `LIST`, and a client shows only the last part.
  - `ingest imap` encodes the name to modified UTF-7 itself (`encode_folder` leaves `.` and `/` alone, as printable ASCII). The setting therefore holds the plain name, never `Kunde M&APw-ller`, which would be encoded a second time (`&` becomes `&-`).
- Vale: 0 findings.

## Gates (final tree, each separately)

1. `uv run ruff check .`: All checks passed.
2. `uv run ruff format --check .`: 88 files already formatted.
3. `uv run pyright`: 0 errors, 0 warnings, 0 informations.
4. `uv run lint-imports`: Contracts: 8 kept, 0 broken.
5. `uv run pytest --cov --cov-report=term-missing`: 1042 passed in 168.47s, TOTAL 98%. `connectors/imap.py` is at 95%; the remaining 9 lines are the server-misbehaviour paths named in the first round.
6. Docs:
   - `make -C docs html`: exit 0.
   - `make -C docs vale`: 0 errors, 0 warnings, 0 suggestions in 31 files.
   - `make -C docs linkcheck`: exit 0, 0 broken.

Ruling P-1: I emptied the tutorial block, ran a plain `uv run pytest` green (1042 passed in 174.03s), and typed the whole block from that run without the `rootdir:` line.

## Left as named by the review

M2 (the `> after` filter), M3 (variant notices lost after a later break, only above 500 events), M8 (the `127.0.0.2` half only on Linux).
