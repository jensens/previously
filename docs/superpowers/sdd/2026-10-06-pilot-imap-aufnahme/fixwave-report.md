# Fix wave after the final review — report

Base `42425e7`, six commits, branch `worktree-pilot-aufnahme`.
Status: **DONE**.

| Commit | What |
|---|---|
| `6b339cf` | Code guards: long Message-ID, `Date` without a time in UTC, address header the parser raises on, `append --text` line endings (items 1, 2, 4) |
| `3ad8663` | Escaping of control characters in `chronicle`, `show`, the variant notice and `Error:` lines (item 3) |
| `fe40308` | Ruling citations with their plan, and the comments that claimed too much (items 5, 6) |
| `7d15703` | Docs and handoff: erasing every copy of a mail, the alarm, the error list in `cli.md`, the minors (items 7–10) |
| `031d9cb` | The map (item 11) |
| `bf70bb1` | Tutorial test block retyped from a green run, last (ruling P-1) |

Mutations were run with a scratch script (`mut.py` in the session scratchpad) that patches one string, runs pytest, and restores the file; the tree was clean after each run.

## Item 1 — a mail `append` refuses no longer stops every run

- `core/mail.py`: `MAX_MESSAGE_ID_BYTES = 998`. A Message-ID longer than that in UTF-8 counts as none, and the key is `sha256:<artifact hash>`.
  The constant's docstring argues the bound from a measurement of mine against PostgreSQL 17: a 3,212-byte key gave `index row size 3232 exceeds btree version 4 maximum 2704 for index "source_key_pkey"`, a 2,700-byte key gave 2,720, so an entry is the key plus 20 bytes, the source `email` among them.
  The longest key a run builds from a Message-ID is the variant key, 17 bytes longer, so the largest entry at the bound is 1,035 bytes.
  `forwarded_in` and `variant_of` are payload, not indexed; `source_key_pkey` is the only index over `external_id`.
- `_occurred_at` takes the header only when `iso_utc` reads it (`_has_utc`, catching `OverflowError`); `Fri, 31 Dec 9999 23:30:00 -0100` falls back to `INTERNALDATE`, `date_source` `internaldate`.
- `mail-mapping.md`: the `external_id` and `occurred_at` rows and two rows of the cases table.
- Tests: three invented mails (`message_id_long.eml` with 3,200 hex digits from a SHA-256 chain so it does not compress, `date_out_of_range.eml`, `address_lone_quote.eml`), held by `mailfiles.py`; no existing mail's bytes changed (`test_every_mail_file_is_what_mailfiles_writes` green).
  In `test_mail.py`: the long Message-ID falls back; a boundary test at 998/999 bytes in ASCII and in `ü`; the date west and east of UTC.
  In `test_ingest.py`: `test_the_longest_key_a_message_id_gives_fits_the_key_index` runs a `MAX_MESSAGE_ID_BYTES` Message-ID and its variant through PostgreSQL. The new mails also go through `test_every_test_mail_is_taken_in_and_a_second_run_appends_nothing`.

| Mutation | Red | Green control |
|---|---|---|
| bound removed | long-ID test, `ascii-999`, `utf8-999`; against PostgreSQL the every-mail run (`index row size 3232`) | `ascii-998`, `utf8-998` |
| characters instead of bytes | `utf8-999-bytes` | the other three cases |
| bound raised to 2,700 | the longest-key run (`index row size 2720`) | the variant test |
| `_has_utc` removed | `west-of-utc`, the every-mail mapping test, the every-mail run (`OverflowError`) | `east-of-utc` |

## Item 2 — one broken address header

`_channel_identities` asks `_addresses(name, value)`, which returns `()` when `header_fetch_parse` raises (any exception; the docstring says why).
A plain `try/except/continue` was flagged by ruff `S112`, so the catch moved into a helper that returns `()`; no suppression.
`mail-mapping.md` now says what a header the parser raises on contributes; the existing sentence on line 130 stays true.
Test: `address_lone_quote.eml` maps with subject, text, `From` and `Cc`, and `To` stays in `headers`; red with the `except` narrowed to `ZeroDivisionError`.
Control in a test of its own: the same list without the quote contributes its address (green under the mutation).

## Item 3 — terminal control sequences

- `cli.py`: `escape_controls` writes every C0 control but tab and LF, DEL and C1 as `\xNN`; `escape_field` applies it after its four escapes, so it stays reversible (`\\x1b` for a literal, `\x1b` for ESC).
- `show`: units through `escape_controls` (line breaks and tabs kept, as asked); the payload line through `_json_line`, which leaves `json.dumps` as it was and writes only DEL and C1 as `\u007f`–`\u009f`. Measured: `json.dumps(ensure_ascii=False)` escapes C0 itself and leaves DEL and C1 raw.
- Two more places carried mail content raw and are covered too: the variant notice of `ingest imap` (Message-ID through `escape_field`) and the `Error:` line in `main` (through `escape_controls`; `ArtifactChanged` quotes the key, which is a Message-ID). The `T201` count stays 36 (measured), so the `pyproject.toml` comment holds.
- `cli.md`: chronicle, show, the variant notice, and the general error sentence.
- Tests: ESC, an OSC title sequence ended by BEL, CSI as ESC `[` and as U+009B, DEL; a DB test through `show` (unit and payload, JSON round-trips) and `chronicle`; a GreenMail test with ESC/BEL raw in a Message-ID of a variant; a DB test with ESC in a key of `ArtifactChanged`.

| Mutation | Red | Green control |
|---|---|---|
| `show` prints the unit raw | show/chronicle test | `escape_controls` unit tests |
| DEL/C1 left raw in the payload | show/chronicle test | — (same test, other assertions) |
| `escape_field` without `escape_controls` | escape_field test, show/chronicle test | the old four-character test |
| C1 range dropped | three tests | the keep-tab-and-text test |
| tab escaped too | keep-tab-and-text test, show/chronicle test | — |
| variant notice raw | variant-escape test | `names_each_variant` |
| `Error:` line raw | error-escape test | `another_text_under_a_known_key` |

No typed output changed: no typed block holds a control character.

## Item 4 — ruling T1-b

`append --text` hashes `normalize_line_endings(args.text)`. `cli.md` and `hash-format.md` say so.
Tests: CRLF and lone CR are known (`1\n1\n`), the hash is that of the LF text; control in its own test: a text differing beyond its line endings is refused.
Mutations: hashing the text as given → both line-ending cases red; normalising CRLF only → the CR case red; the control stayed green both times.

## Item 5 — ruling citations

The four section headers in `tests/test_mail.py` now read `Ruling T2-d of the 2026-10-06 pilot ingest plan` (and T2-e, T2-b, T2-f, T2-g), one `ruling` per label, the plural split in two, the ledger path named once, the reason written beside each.
Census `grep -rnioE 'ruling (P|T[0-9]+)-[a-z0-9]+' src tests pyproject.toml .importlinter`: the five now match; `git diff -U0 fd3e17f..HEAD` shows no other ruling citation added on the branch (the `T9-c` line in `pyproject.toml` was an existing one, already qualified as lost).
The ledger is not shipped by me, as the brief says.

## Item 6 — comments

All corrected against the code:

- `errors.py` `ArtifactChanged`, the comment in `append`'s loop, and `hash-format.md`: the refusal is raised inside the transaction, which rolls back, so nothing is kept; `core.ingest` raises it too. `hash-format.md` no longer says only an old event can carry a malformed hash (`insert_event` without `append` can).
- `test_append.py`: "two of the seven messages of `check_units` carry the word seq" (counted: seven `raise InvalidPayload` in `check_units`, two with the word); the dated 2026-10-05 measurement keeps the old name as "then named `_check_units`".
- `_recovered`: recovers raw header bytes only; an `unknown-8bit` encoded word is decoded after it and becomes U+FFFD — measured, `=?unknown-8bit?q?Gr=FC=DFe?=` → `Gr��e`, `headers_replaced` `['Subject']`.
- `known_id`: "the one place the rule lives for a key the log holds"; `_Run._holds` says it copies the rule and where it lives.
- `ingest.py` module docstring: a batch holds units and references, not raw mails or attachments.
- Memory test docstring: glibc's 32 MiB cap; pinned figures repeat, unpinned ones vary (322/322/349 from the task 4 review).
- Refused-batch test docstring: what the second writer does and what the run looked up.
- `schema.py` watermark comment rewrapped.
- `{ref}` in `core/mail.py` and `core/ingest.py` → `connectors`; `tests/test_mail.py` → `mail-mapping`.
- `contract/store.py`: six modules, the command includes `core/ingest.py`; recounted, still thirteen methods.

## Item 7 — erasing a mail

`ingest-a-mail-folder.md` *Erase a mail* now names variants, mails inside at every depth, and mails that carry it, and gives one recursive SQL query (variants by the `#` prefix of any found key, `forwarded_in` downward, `event_blob` against each found event's `raw` upward).
The `redact` session is reordered (the mail first, then its carrier) and retyped from a real run.
A last paragraph says how to find a later forward of an erased mail through the noted `raw` address.
`erasure.md` (*An erasure holds for the event…*) and `erase-something.md` say the same; the map has the point under *Tilgung*.

Checked against the containers with a scratch test that extracts the SQL from the page itself (scratchpad `test_erase_query.py`, run with `PYTHONPATH=tests pytest -p conftest`; invented mail; containers discarded):

- page example: the query lists 5 (invoice) and 4 (the forward); before erasing, two objects held the invoice text (`90f565d1…`, `911ba009…`), after `redact event 5` and `4`, none. The typed output matches that run byte for byte.
- variant and carriers: `PLAIN`, `PLAIN_OTHER_BODY` and two wrapping mails → 1, the variant 6, the carriers 7 and 8; after erasing those four, no object holds either body.
- depth: a six-level chain lists all six from the top, and from level 2 the two carriers above and the three below.

## Item 8 — handoff alarm

"Alarm on any exit code but `0`", with a table of 2, 1, 137 and 143, and the two refusals that recur at every run.

## Item 9 — `cli.md` errors

Five IMAP sentences added (no UIDVALIDITY, refused search, refused fetch, INTERNALDATE not a date, refused command with `got more than 1000000 bytes`), the two refusals of the log in a block of their own, the exit-code row for `ingest`, and the pointers of Minor 4.
`tests/test_docs_references.py`: the count is now 12, and a new test `test_the_reference_quotes_every_error_of_ingest_imap` holds the direction from the code to the page (every `ImapError` message quoted), the `BatchTooLarge` line, and the `ArtifactChanged` line by raising it with the page's hashes.
Mutations: a line dropped from the page → both tests red; a new `ImapError` message in the connector → the new test red; the batch sentence shortened → red; the other nine tests stayed green each time.

## Item 10 — docs review minors

All ten fixed, none left: (1) *Text from markup*; (2) "whoever maps a source decides"; (3) `erasure.md` points at `mail-mapping` for where, `connectors` for why; (4) `cli.md` ingest pointers; (5) "without quotes" for `--env-file` — named as misuse by the reviewer, fixed because it is one clause; (6) init container, and the `sh -c … exec` form with the entrypoint and `SIGTERM` caveat; (7) the 512 MiB run named; (8) `memory.peak` includes the tmpfs, the resident peak doesn't; (9) `appended` as "at most", copies count as known; (10) "traveled", "afterward", and the ASCII login.
For (10) the program's message changed too: `… holds a character other than ASCII, and previously sends the login in ASCII only` (test and `cli.md` follow).
The how-to also says what an exit code other than 0 and 2 means.

## Item 11 — the map

Verified on 2026-10-06: PyPI `previously 0.1.0a1` (wheel and sdist, 2026-10-05), Test-PyPI `0.1.dev193`, `ghcr.io/jensens/previously:0.1.0a1` pulled with an anonymous token, `linux/amd64` and `linux/arm64`; tag `v0.1.0a1` on `fd3e17f`.
The one bullet that carried both the PyPI name and condition 8 is struck into *Erledigt* with the tag and commit.
Added under *Aufnahme aus IMAP*: M-3, M-4, M-5; under *Tilgung*: the copies no command finds (docs review I1). The broken-address point notes the fix.
**Count: 149 before, 152 after** (awk command from `CLAUDE.md`). The test-duration point quotes the new figure.

## Gates (final tree, `bf70bb1`)

- `ruff check .`: all checks passed.
- `ruff format --check .`: 88 files already formatted.
- `pyright`: 0 errors, 0 warnings.
- `lint-imports`: 8 kept, 0 broken.
- `pytest --cov --cov-report=term-missing`: 1071 passed, coverage 97.85 %.
- `make -C docs html`: succeeded; `vale`: 0 errors, 0 warnings, 0 suggestions in 34 files; `linkcheck`: succeeded.
- `pip-audit --skip-editable`: no known vulnerabilities.

Tutorial block: placeholder, green `uv run pytest`, whole block typed: `1071 passed in 170.26s`.

## Named, not chased

- `show` escapes controls but not the backslash, so in a unit a literal `\x1b` and an escaped ESC look alike there; `chronicle` stays the reversible form.
- Bidirectional and format characters (U+202E and the like) pass unescaped: they are no terminal commands, but they can reorder what a line shows.
- The erase query scans every event for `forwarded_in` (no index); fine for a pilot folder.
- The erase query finds no later forward of a mail already erased (the payload that names its raw mail is gone); the page gives the `event_blob` lookup by the noted address instead.
- Test construction note: `_mail(attached=[_mail(…)])` in `test_ingest.py` nests two multiparts with the same boundary `part`, so the inner one does not parse as nested; it surfaced only in my scratch scenario, not in any committed test.
