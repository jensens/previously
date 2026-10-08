# Task 5 review: IMAP connector and `previously ingest imap` (b4e5a8c..e26551d)

Reviewer: independent, read-only on the tree. Rulings T5-a, T5-b, T5-c applied; the lag in `module-boundaries.md`, README and CLAUDE.md is not reported (task 6).

## Spec compliance: ✅

Every item of the brief is there:

- the interface (`ImapConnector` plus an optional `timeout`, which ruling T5-c covers, and `encode_folder`);
- the position `{"uidvalidity", "uid"}`;
- a changed `UIDVALIDITY` reads from 1;
- `UID SEARCH UID n:*` without parentheses, filtered to `> after`;
- `(UID INTERNALDATE BODY.PEEK[])`, one mail at a time;
- the `connectors` layer between `cli` and `core`, and the contract `only-imap-knows-imaplib` with one named edge;
- the GreenMail fixture, with the folder "Kunde Müller" filled by `APPEND` from `tests/mails/`;
- all eight test bullets of Step 2 (the `\Seen` test uses the double mutation, under ruling T5-a);
- `ingest` in `COMMANDS` with the contracted help text;
- the five settings, then the recipient, the DSN and the store's five, all read before any connection, and the identities never read;
- `cli.md` and `configuration.md`;
- `T201`;
- the tutorial's test block.

The spec's §4.3 (TLS only, verified, no switch, `BODY.PEEK[]`, modified UTF-7), §5 (inputs, output line, exit codes, password in no output) and §7.2 are met.

## Quality verdict: Needs fixes

One Important finding, a test gap on a value that goes into every event hash.
Everything on the critical list (password, TLS, protocol use, the watermark, the contract) holds, and I checked it by measurement where I could.

## Findings

### Critical

None.

### Important

**I1: the INTERNALDATE parser has no test that reads its value. Two mutations of it leave every IMAP test green.**
`src/previously/connectors/imap.py:283-314` (`_DATE`, `_MONTHS`, `_internaldate`); the only assertion is `tests/test_imap.py:105`, `tzinfo is not None`.

- Measured. Both mutations together left `tests/test_imap.py` plus `tests/test_cli.py -k imap` at **34 passed**:
  - `_MONTHS` built with `start=0`: every month is read one too early, and January raises `ImapError` "… which is not a date".
  - The sign of the zone swapped: `-0230` is read as `+0230`.
- Why it matters: `Fetched.internaldate` becomes the payload field `internaldate` of every mail event, and `occurred_at` for a mail whose `Date` is missing or unreadable (spec §3.1, §3.4). Both go into the event hash, so a parser slip writes wrong, permanent data that no gate notices.
- The parser is hand-written on purpose (`%b` depends on the locale), so it has no stdlib behaviour to lean on.
- Failure scenario: a later "simplification" of the month table, or a sign fix in the wrong direction, ships green. Every mail the pilot takes in then carries an `internaldate` a month or a few hours off, sealed into the chain.
- Fix:
  - Give the parser a public name (CLAUDE.md: what deserves a direct test deserves a public name).
  - Pin RFC 3501 strings against it, at least these: a space-padded day (`" 5-Jan-2026 23:30:00 -0230"`), a two-digit day with a positive offset, a month name that isn't English, and an impossible date.
  - Add one end-to-end case: `APPEND` with an explicit date. Measured: GreenMail keeps the instant (`"05-Jan-2026 23:30:00 -0230"` came back as `2026-01-06 02:00:00+00:00`) but normalises the zone to `+0000`. So the end-to-end case catches the month and the instant, but only the unit cases catch the sign.

### Minor

**M1: the escaping of `"` and `\` in `_quoted` has no test** (`imap.py:324-327`).
- Mutation `return '"' + text + '"'`: all 34 IMAP tests stay green.
- The unmutated code is right. Against GreenMail, folders `Kunde "Müller"`, `Back\slash Ä`, `Angebote & Rechnungen` and `Emoji 😀 Ordner` were each created, appended to and fetched by the connector.
- A folder name with a quote is rare, so this is named rather than chased. Adding one parametrised folder to the fetch test would close it.

**M2: the `> after` filter in `_uids` has no test** (`imap.py:182`). The implementer named this.
- GreenMail answers `UID SEARCH UID 5:*` on a four-mail folder with `b''` (measured again; `4:*` gives `b'4'`), so the RFC behaviour that Dovecot shows cannot be produced there.
- Without the filter, a Dovecot run fetches the newest mail again on every run and reports it as `1 known`. That costs work but loses no data.
- A public pure helper (the tokens and `after` in, the UIDs out) would make it testable without a server.

**M3: the variant notices and the counts of batches already appended are lost when a later batch's fetch breaks off** (`cli.py:528-537`).
- `ingest` returns only at the end, so a run that appended batch 1 (which held a variant) and then hit `ImapError` in batch 2 prints only `Error: …`.
- The next run sees the variant's key as known, so its `variant of …` line is never printed.
- The variant is in the log with `variant_of`, so nothing is lost but the notice.
- This only affects runs of more than `MAX_BATCH` = 500 events. A pilot folder is normally one batch, and there a break means nothing was appended.

**M4: the docstring of `_uids` (`imap.py:174-176`) reads the wrong way round.**
"The search is `UID n:*`, without parentheses, which GreenMail refuses" reads as if GreenMail refused the form without parentheses. The spec says GreenMail refuses the bracketed form.

**M5: the comment in `_login` (`imap.py:137-139`) says "the encoder's view of the command line, which holds the password".**
`imaplib` encodes each argument on its own (`imaplib.py:1107-1109`, CPython 3.14.3), so `UnicodeEncodeError.object` is the quoted password argument, not the command line. The conclusion (it holds the password, hence `from None`) stands.

**M6: `test_a_server_that_stops_answering_ends_the_fetch` gives exact figures, "7303 bytes … the first mail is through at 3577"** (`tests/test_imap.py:172-174`).
- Measured twice: 3575/7301 and 3576/7302. The count moves by a byte or two per run.
- That is harmless against the limit of 5000, which keeps margins of about 1.4 KB and 2.3 KB.
- But the comment states as exact a figure that isn't stable. "About" would make it true.

**M7: `configuration.md` describes `PREVIOUSLY_IMAP_FOLDER` as "the folder, by the name a mail client shows".**
- For a nested folder, the IMAP name carries the parent and the server's hierarchy separator. GreenMail lists `"."`, and for Dovecot it depends on the configuration.
- A mail client shows only the leaf, so a user who copies the leaf name gets "refused to open the folder".
- Top-level folders, which is the pilot's case, are fine.

**M8: the `127.0.0.2` half of `test_ingest_imap_verifies_the_certificate_and_the_host_name` is Linux-only, as its docstring says.**
It goes red on macOS, where only `127.0.0.1` is configured. CI and the maintainer run Linux, so this is named only.

## What was measured

- **Gates on the touched files:**
  - `uv run pyright tests/mailserver.py src/previously/connectors/imap.py tests/test_imap.py`: 0 errors. The editor's diagnostics at `mailserver.py:~98` are not real under the project's pyright.
  - `uv run lint-imports`: 8 kept, 0 broken, and the new contract shows "1 ignored import".
  - `ruff check` on the new files: clean.
  - The diff adds no `noqa` and no `type: ignore`.
- **`T201`:** `ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py` counts 36, as `pyproject.toml` says.
- **`.importlinter` header:** "Seven of the eight" checks out. Every contract but the layers contract forbids an external package.
- **Tests:**
  - `tests/test_imap.py`: 16 passed.
  - `tests/test_cli.py -k ingest_imap`: 18 passed.
  - `test_docs_references`, `test_contracts`, `test_docs_typed_output`: 15 passed.
  - The relay-based tests (dropped connection, server stops answering, mail leaves the folder) ran five times in a row and were green every time, at 15-16 s.
- **Tutorial block:** checked against `pytest --collect-only` per file. The total is 1026, `test_cli` is 291 (54+72+72+72+21), `test_imap` 16 and `test_contracts` 7, all matching.
- **Mutations I ran myself** (on a scratch copy of `src` put ahead on `PYTHONPATH`; the tree was left untouched):
  - The abort text quoted again: the dropped-connection test goes red with `broke off: command: UID => unexpected response: b'To: pilot@example.org'`. That confirms both the CPython buffer behaviour and the guard. Control `takes_in_the_folder`: green.
  - The CLI given `ssl._create_unverified_context()`: `verifies_the_certificate…` red; `takes_in…` green.
  - `_quoted` without escaping: green (M1).
  - The month table and the zone sign: green (I1).
- **Password and mail content, read path by path** (`imap.py` and the `ingest` branch of `cli.py`):
  - `_connect`: the reason from the certificate check, or the greeting or the system's reason. No password has been sent yet at that point.
  - `_login`: both refusals use `from None` and quote nothing. An `abort` during LOGIN becomes "broke off" with no text. `imaplib`'s abort texts name only the command (`'command: %s => %s' % (name, val)`).
  - `_speaking`: drops all `abort` text. Its `IMAP4.error` branch can only quote a BAD line of the server or `got more than N bytes`, never mail.
  - `_ok`: quotes the server's NO or BAD text.
  - The `INTERNALDATE` error quotes only the date as the server wrote it.
  - In `cli.py`: the port error quotes the port, and a missing setting names only the variable.
  - The `UnicodeEncodeError` for a non-ASCII password comes out as one sentence with `__suppress_context__ = True`, measured.
  - The one place the password survives is `imaplib`'s in-memory `_cmd_log`, which only prints at `Debug >= 1`. The implementer named that.
- **TLS:** `ssl.create_default_context()` with no switch. `SSL_CERT_FILE` only replaces the trust store. A certificate refusal becomes one sentence and exit 2, which the test holds for the self-signed case and the host mismatch case.
- **Modified UTF-7:**
  - Checked against GreenMail's `LIST` output: `Kunde \"M&APw-ller\"`, `Angebote &- Rechnungen`, `Back\\slash &AMQ-`, `Emoji &2D3eAA- Ordner`. The last is a non-BMP character as a surrogate pair, correct by RFC 3501.
  - The RFC example and the hypothesis round trip pass.
- **GreenMail fixture:**
  - The keytool certificate (EC, SAN `localhost` and `127.0.0.1`) is exported by `container.exec` in a retry loop with a 60 s ceiling and only `time.sleep` between tries.
  - The DB fixture truncates `watermark` for every test, so GreenMail's one-second `UIDVALIDITY` cannot leak a watermark between tests.
  - The relay counts bytes, not time. Its margins are about 512 KiB for the dropped connection and about 1.4 KB for the hold, against a run-to-run variation of a few bytes.

## Verdicts

Spec compliance: ✅. Quality: Needs fixes (I1).
