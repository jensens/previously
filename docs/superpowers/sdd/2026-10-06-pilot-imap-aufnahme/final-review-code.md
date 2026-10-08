# Final review, code: branch `worktree-pilot-aufnahme`, `fd3e17f..42425e7`

Reviewer: final whole-branch code review (Opus), 2026-10-06. Read-only; scratch probes only in the session scratchpad.

## Verdict

**Ready after fixes.** 0 Critical, 2 Important, 5 Minor.

The seams hold end to end. IMAP fetch, `map_mail`, the run, `append` (variant path included), then `show`/`chronicle`, the blobs, `redact event` and the next run all fit together: the types, the payload names, the variant key, erasure and the watermark.
Both Important findings are cheap to fix.
One is a class of mapped values that `append` refuses and that then stops every run. It is reachable only from hostile or absurd mail, so the working rule may make it a "name" (see the precedent below).
The other is a rule breach in four new ruling citations.

## How it was read

- `final-code.diff` read in passes, not front to back. `src/` was read whole from the tree: `core/ingest.py`, `core/mail.py`, `core/append.py` and `connectors/imap.py`, the `cli.py` diff, `contract/*`, `core/errors.py`, `core/identity.py`, the storage, schema and migration diffs.
  The diffs of `.importlinter`, `pyproject.toml`, `Dockerfile`, `.vale.ini` and `DEPENDENCIES.md` were read in full.
  For the tests, I sampled the cross-task parts: the helpers and the erasure/batch tests in `test_ingest.py`, every new `ingest imap` test in `test_cli.py`, `test_contracts.py`, `test_identity.py`, the new parts of `test_docs_references.py`, and the ruling sections of `test_mail.py`.
  I did not read `tests/mails/*.eml` byte by byte.
- Spec §1–§3.5 were read against the code, along with the ledger and the global constraints.
  Deferred items in the ledger (`deferred → Fixwelle`) and named items (`benannt`) are not re-reported.

## Important

### I-1 A mapped mail that `append` refuses stops every run (hostile or absurd input; the T2-b failure mode by another door)

`core/mail.py:283` (`external_id` from `_message_id`, no bound) and `core/mail.py:487-497` (`_occurred_at` accepts any zoned moment).
`map_mail` never raises for mail content (ruling T2-b), but two values it returns are refused later, in `append`, outside the fallback.

1. **A Message-ID longer than about 2.7 KB.** Measured against the test PostgreSQL 17 with three mails in one batch, where the middle one has a 3,200-character Message-ID of random hex.
   `ingest` raised `OperationFailed: … index row size 3232 exceeds btree version 4 maximum 2704 for index "source_key_pkey"` on both runs.
   The watermark stayed `None`, and the first mail of the batch was not appended either.
   From the command line, this is `Error: …`, exit 2, every run.
   The message names neither the UID nor the Message-ID, so the operator has to work out by hand which mail to move out of the folder.
   No mail content leaked into the message (measured: the subject is absent).
2. **`Date: Fri, 31 Dec 9999 23:30:00 -0100`.** `_occurred_at` takes it, `date_source` is `header`, and `iso_utc` in `append._prepare` raises `OverflowError: date value out of range`.
   That is not a `PreviouslyError`, so the command ends in a stack trace, every run (measured through `map_mail` and `iso_utc`).

Scenario: one spam mail with such a header in the pilot folder halts intake until somebody notices that the CronJob fails daily, finds the mail and removes it.

Precedent: ">499 attached mails → `BatchTooLarge` at every run" was named, not fixed (Task 4).
The difference is cost. Here, one header line from any sender is enough, and the fix is small.

Suggested fix, either one:

- Close the instances in `core/mail.py`.
  A Message-ID over a bound falls back to the `sha256:` key, as a missing one does. Use a bound well under 2,704 bytes in UTF-8 that leaves room for the 17 characters of the variant suffix: RFC 5322's 998 is a natural one.
  `_occurred_at` uses the header only when `iso_utc(moment)` succeeds.
- Or close the class in `core/ingest.py`: check each mapped event with the checks `append._prepare` applies, made public, plus the key bound. On refusal, substitute `_unreadable` for that mail.

Either way, one test per instance, red when the guard is removed.

### I-2 New ruling citations name no plan, and resolve to other decisions in a shipped ledger

`tests/test_mail.py:649` (`ruling T2-d`), `:731` (`ruling T2-e`), `:780` (`rulings T2-b and T2-f`), `:811` (`ruling T2-g`). These are section headers, added on this branch.

- `CLAUDE.md` § "A ruling citation is provenance": labels are assigned per plan, so a new citation names the plan ("the 2026-10-06 pilot ingest plan"), and it says to write one `ruling` per label.
- Measured with `grep 'Ruling T2-[bdefg]' docs/superpowers/sdd/2026-10-05-auslieferung/progress.md`: all five labels exist in that shipped ledger as **other** decisions. T2-d there is about refused database logins, T2-e about `statement_timeout`, and T2-g about `MigrationFailed`.
  A reader who looks up `ruling T2-e` lands on the wrong decision. That is the case `CLAUDE.md` calls worse than an unresolvable label.
- `rulings T2-b and T2-f` is the plural form that the census pattern does not match.
  The census `grep -rnioE 'ruling (P|T[0-9]+)-[a-z0-9]+' …` misses that line, which is how the `.importlinter` case hid before.
- This plan's ledger is still under `.superpowers/` (git-ignored), not under `docs/superpowers/sdd/2026-10-06-pilot-imap-aufnahme/`. As the tree stands, none of the four citations resolves to its own decision.

The reason does stand beside each citation: the tests' docstrings carry it. So the fix is mechanical:

- write `ruling T2-d of the 2026-10-06 pilot ingest plan` (and so on), one `ruling` per label;
- ship `progress.md` under `docs/superpowers/sdd/2026-10-06-pilot-imap-aufnahme/`, as the earlier executions did.

No other new ruling, finding or `§` citation was added on the branch. Measured with `git diff -U0 fd3e17f..HEAD` over `src tests pyproject.toml .importlinter Dockerfile`.

## Minor

### M-1 A trailing lone quote in an address header makes the whole mail unreadable, against the reference page

`core/mail.py:500-522` (`_channel_identities`) and `docs/reference/mail-mapping.md:130`.
Measured: `To: a@example.org, "` and `To: "Mueller, Hans" <hans@example.org>, "` make the standard library raise `IndexError` inside `header_fetch_parse`. The fallback then turns the whole mail into `unreadable mail: IndexError`, and its subject and text are lost from the units (the raw mail is kept).
24 other malformed forms map fine: unbalanced quotes inside a display name, `;` separators, empty groups, `<>`, `<a@b.c`.
Only broken mail does this, but the page states "An address list the parser can't read in full contributes the addresses it reads", which this input falsifies.

Fix: catch per header in `_channel_identities`. A header the parser raises on contributes no identities (it stays under `headers`). Add a test with this input, red without the guard.

### M-2 Terminal control sequences from mail reach the terminal raw

`cli.py:128-149` (`escape_field`), `cli.py:737-744` (`show`).
Measured: a subject `=?utf-8?q?=1B]0;Titel_gesetzt=07=1B[31mRot?=` and a body with `ESC[2J` go into the units unchanged.
`escape_field` escapes only `\`, tab, LF and CR, and `show` prints units unescaped.
Before this branch, only the operator's own `--text` reached these commands; now any sender's content does. The result is title or clipboard (OSC 52) writes and screen clearing in the maintainer's terminal.

Fix: escape the remaining C0 controls, DEL and C1 (U+0080–U+009F) in `escape_field` and in the unit and payload lines of `show`, as `\xNN` or `\u00NN`. Data in the log stays unchanged.

### M-3 The first run over a large folder cannot complete its search

`connectors/imap.py:173-185`.
`UID SEARCH UID 1:*` comes back as one line, and `imaplib` refuses a line over `_MAXLINE = 1000000` bytes (Python 3.14.3, read from the module).
At about 7 bytes per UID, a folder of roughly 140,000 mails fails with `ImapError: … refused a command: got more than 1000000 bytes` at every first run.
The pilot folder is curated, so this is a "name" unless a whole mailbox is ever pointed at.
A fix, if wanted: search in UID ranges, for example in steps of 50,000.

### M-4 A FETCH answer the parser does not recognise is taken for an expunged mail

`connectors/imap.py:187-195`, `261-280`.
When the FETCH is `OK` but `_message` finds no `BODY[] {n}` literal for the UID, the mail is skipped and the next mail's position carries the watermark past it, silently.
RFC 3501 allows `BODY[]` as a quoted string (`nstring`). Dovecot, Gmail, Exchange and GreenMail all send a literal, so this is theoretical.

Name it, or make the skip loud: when a FETCH returns `OK` without a body, confirm with `UID SEARCH UID <n>` that the mail is gone, and raise `ImapError` otherwise.

### M-5 Two test domains are not reserved names

`tests/mails/*`, `tests/mailfiles.py`: 18 addresses at `example.at` and 4 at `example.de`.
RFC 2606 reserves only `example.com`, `.net` and `.org` (and the `.example` TLD), and `example.de` is a registered domain.
Nothing is sent, so this is cosmetic. Changing it would change the test mails' bytes and every hash derived from them, so it is "name", not a fix round.

## Confirmed or sharpened (already in the ledger)

- Deferred comment fixes: still as described. `known_id` "the one place the rule lives" (`append.py:339`), with `_Run._holds` comparing too. `ingest.py:35-37` "not their content". `errors.py:38` "before anything … is written".
  No new false numbers were found in the branch's comments. Checked:
  - `T201` count, 36: `ruff --select T201 --config 'lint.per-file-ignores = {}'` reports 36;
  - `.importlinter`, eight contracts, seven forbidding packages, ten packages listed: counted;
  - `.vale.ini`, 15 of 20 lowercase: `awk` gives 20 and 15;
  - the five undefined bytes of cp1252: correct;
  - glibc's 32 MiB cap on the dynamic mmap threshold: correct;
  - the `Dockerfile` memory figures: they match `task-6-report.md` (529–533 MiB; 335/336 against 336/360/361 MiB).

## Rule compliance

- `noqa`: five in the tree (canonical `C901`, two `DTZ001`, `S607`, `docs/conf.py` `A001`), none new. That matches `CLAUDE.md`.
- `# type: ignore`: none. The one hit is prose in `tests/test_schema.py:297`.
- Tests reach no private names of the new modules (`grep` for `import _x` and `module._x`).
- Gates measured: `ruff check` passes, `ruff format --check` passes (88 files), `pyright` reports 0 errors, `lint-imports` reports 8 kept and 0 broken.
  `pytest` (whole suite) and the docs gate were not run, as the brief forbids the whole suite.
- Citations in program output: none. The new messages in `connectors/imap.py` and `cli.py` carry no `{ref}` and no `§`.

## Security

- The password reaches no message. `_login` raises `from None` on both refusals, `_setting` names only the variable, and nothing reprs the connector.
- Mail content reaches no message on the IMAP paths: `abort` text is dropped, and `_ok` and `_speaking` quote only the server's tagged text or `imaplib`'s own.
  On the storage path, `OperationFailed` for the I-1 case carried no content (measured).
  A foreign exception would still print a stack trace (`OverflowError` in I-1), but without values.
- TLS: `ssl.create_default_context()` with no switch. The CLI test shows a self-signed certificate refused and an IP mismatch refused.
  The trust store of the published image `ghcr.io/jensens/previously:0.1.0a1` (same base image) holds 150 CAs (measured), which matters because this is the first code that needs the system store; `boto3` brings its own.
- Committed secrets: none. The S3 secret, the IMAP password and the keystore password are drawn at run time in `conftest.py`, and all test addresses are invented (see M-5 on two of the domains).
- The `Dockerfile` change is one `ENV` with a measured reason.
  It applies to every command of the image, which is harmless.

## Seams checked end to end

- **IMAP → `Fetched` → `map_mail`.** `internaldate` is zoned, `found_in` holds `connector`/`uidvalidity`/`uid`, and the position is text-to-text, so it survives JSONB.
- **`map_mail` → run.** `Mapped.event` comes without blobs or `raw`; the run adds the raw mail first, unnamed, then the attachments with `_blob_name`.
  An inner mail's raw bytes and the outer's `message/rfc822` attachment are the same content address, so there is one object.
- **Run → `append`.** The lookup comes before the blobs, so a known or erased mail stores nothing.
  Copies in the batch are decided by the same rule.
  A variant in the batch gets `variant_key` and `variant_of`, and its children get the variant key in `forwarded_in`, also after a late `ArtifactChanged` in `_vary`.
  A `known` whose `id` is at or below the tip is counted as such.
- **Watermark.** It is written only after `append`, in its own transaction, at the position of the last mail the flushed batch covered (and not the mail that triggered the flush).
  A `UIDVALIDITY` change reads from the start.
- **Erasure.** An erased key is known, and nothing is re-stored.
  An inner mail is its own event, and its raw blob is kept while the outer event still names it. That matches `erasure.md:210-211` ("per event, not per content").
- **Ordinary mail.** No new silent loss or doubling was found beyond what is named.
  - Outlook invitations: the calendar part becomes an attachment, plain text is chosen.
  - Thunderbird `format=flowed`: the text is kept as wrapped.
  - Forward-as-attachment from Thunderbird: unpacked.
  - Mailing-list footers and subject tags: a variant, by design.
  - Gmail and Mailu (Dovecot): `UID n:*` is filtered as named.
  - Outlook `.msg`: named in the map.

## Scratch probes

These lie in the session scratchpad and are not in the tree:

- `probe1.py`: 8-bit parameters in `Content-Type` stay canonical.
- `probe2.py`: `Date` edge values.
- `probe3.py`: terminal escapes.
- `probe4.py` and `probe5.py`: 33 malformed address headers.
- `test_probe_ingest.py`: the long Message-ID against the test containers, run via `PYTHONPATH=tests pytest -p conftest`.
