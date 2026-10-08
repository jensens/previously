# Fix wave re-review: `worktree-pilot-aufnahme`, `42425e7..bf70bb1`

Reviewer: re-review of the one fix wave (Sonnet), 2026-10-06. Read-only on the checkout.
Read: the brief, both final reviews, the implementer's report, `fixwave.diff` in passes, and the tree where a claim needed it.

Measured by me (scratch in the session scratchpad, no checkout change):

- `Date` edge cases through `map_mail` and `iso_utc`: `Fri, 31 Dec 9999 23:30:00 -0100`, `+9999`, `-9999`, `Sat, 31 Dec 9999 23:59:59 +0000`, year `0001` (Python reads the two-digit-normalised 2001) and `+2359`. Every mapped `occurred_at` hashes without an exception; the overflowing one falls back to `internaldate`.
- `tests/test_docs_references.py`: 11 passed.
- `pytest --collect-only`: 1071 collected; per-file counts equal the dots of the retyped tutorial block (cli 300, mail 159, ingest 16, docs_references 11, and so on).
- The map's awk count: 149 at `42425e7`, 152 at HEAD. PyPI `previously 0.1.0a1`, Test-PyPI `0.1.dev193`, tag `v0.1.0a1` on `fd3e17f`: all confirmed.
- `contract/store.py`: `grep -rl LogStore src/previously/core` lists six modules, and the quoted `grep` command with `core/ingest.py` counts 13.
- Census `grep -rnioE 'ruling (P|T[0-9]+)-[a-z0-9]+'`: the only citations the branch added are the five in `tests/test_mail.py` (651, 742, 799, 805, 841).
- The whole suite, the mutations and the containers were not rerun; the mutation tables are the implementer's, and I judged them by reading each test against the code.

## Item Verdicts

1. **ADDRESSED**: both guards.
   - Message-ID: `core/mail.py` `MAX_MESSAGE_ID_BYTES = 998`, applied in `_message_id` on the UTF-8 length of the stripped value, so `ü` counts two.
     The longest key a run builds is `<id>#<16 hex>`: 17 bytes more (`variant_key`), and the entry is the key plus 20 bytes, so 1,035 bytes at the bound against 2,704.
     `source_key_pkey` is the only index over `external_id` (`storage/schema.py`: the `unit` and `p_chronicle` columns of that name have no index), and no other long mail-derived text goes into a btree key.
     Tests red without the guard by reading: `test_a_message_id_too_long_…` (expects the `sha256:` key), the boundary parametrization 998/999 in ASCII and in `ü` (the `utf8-999` case is red for a character count), and the PostgreSQL test with the longest variant key.
   - `Date`: `_has_utc` catches `OverflowError` around `iso_utc`; `west-of-utc` is red without it (expects `INTERNALDATE`), `east-of-utc` is the green control.
     `mail-mapping.md` says both cases (the `external_id` and `occurred_at` rows, two rows of the cases table).
2. **ADDRESSED**: `core/mail.py` `_addresses` catches per header and the other headers still contribute. The control test (same list without the quote) sits beside it, and `mail-mapping.md` now says what such a header contributes.
3. **ADDRESSED**: see "Escaping checked" below. `escape_controls` (C0 but tab and LF, DEL, C1) is applied in `escape_field`, in the units of `show`, in `_json_line` for the payload of `show`, in the variant notice and in the `Error:` line.
   Tests: ESC, OSC with BEL, CSI as `ESC [` and as U+009B, DEL, with a green control for tab, LF and text. No typed output holds a control character, so none needed retyping.
4. **ADDRESSED**: `cli.py` `_cmd_append` hashes `normalize_line_endings(args.text)`. CRLF and lone CR are known, the control (a text that differs beyond its line endings) is refused. `cli.md` and `hash-format.md` say it. A consequence is named under New Breakage (Minor 1).
5. **ADDRESSED**: `tests/test_mail.py:651, 742, 799, 805, 841` read `Ruling T2-x of the 2026-10-06 pilot ingest plan`, one `ruling` per label, and each has its reason in the comment beside it, which stands without the label.
   The ledger path they name does not exist at HEAD yet: the brief leaves shipping it to the controller. Until it is shipped none of the five resolves (named under Out-of-Scope).
6. **ADDRESSED**, each checked against the code:
   - `errors.py` and `hash-format.md` now say the refusal is raised inside a transaction that rolls back, and that `core.ingest` raises it too (`_Run._holds`, `known_id`).
   - `tests/test_append.py`: `check_units` has seven `raise InvalidPayload` (`append.py:225-252`), two with the word `seq`. Correct.
   - `_recovered`: the docstring says encoded words are decoded after it; matches `_headers`, and the `Gr��e` figure is the one `test_a_replaced_character_in_the_subject_is_noted` pins.
   - `known_id`, `_Run._holds`, the `ingest.py` module docstring, the memory test docstring (the 32 MiB cap is glibc's `DEFAULT_MMAP_THRESHOLD_MAX` on 64-bit; 322/322/349 MiB are in `task-4-review.md`), the refused-batch test docstring, and the `schema.py` comment: all as the code does.
   - `{ref}` labels moved to `connectors` and `mail-mapping`; `test_docs_references` resolves them.
   - `contract/store.py`: six modules and 13 methods, measured above.
7. **ADDRESSED**: see "Erase query checked" below. The three pages cover variants, carriers and depth, with a runnable query. The page's own query is not held by a committed test; the implementer ran it from scratch against containers.
8. **ADDRESSED**: `docs/superpowers/handoffs/2026-10-06-kup6s-ingest.md` says "Alarm on any exit code but `0`" and lists 2, 1, 137 and 143. It also says the init-container order and the entrypoint caveat (Minor 6 of the docs review).
9. **ADDRESSED**: `cli.md` quotes all twelve `ImapError` sentences, the `ingest` exit row names the log's refusals, and the two refusals have a block of their own.
   `tests/test_docs_references.py::test_the_reference_quotes_every_error_of_ingest_imap` holds the direction code to page (every `ImapError` pattern of `connectors/imap.py` must match a quoted line), the `BatchTooLarge` line against `append.py`, and the `ArtifactChanged` line by raising it with the page's hashes.
   Together with the existing page-to-code test and the count of 12, the two sets are equal. It passes (11 passed).
10. **ADDRESSED**: all ten minors fixed, each checked in the diff. The `previously sends the login in ASCII only` wording changed in the program message, the test and `cli.md` together. "travelled" and "afterwards" are gone from the pages the review named.
11. **ADDRESSED**: the one bullet that carried the PyPI name and condition 8 moved to *Erledigt* with the tag and `fd3e17f`, struck as the other entries are, with the facts confirmed above. M-3, M-4 and M-5 are added in German under *Aufnahme aus IMAP*, plus the carrier point under *Tilgung*. Count 149 to 152 matches my recount: three points added, none lost, the PyPI bullet leaves the section.

### Escaping checked (focus 2)

- Where mail content reaches the terminal: `chronicle` (every field through `escape_field`), `stats` (same), `show` (units, payload JSON, blob lines through `escape_field`), the variant notice, the `Error:` line, and the verify/finding lines. The `FINDING` reasons quote no mail content (every reason in `core/verify.py` is fixed text or ids). `evidence` and `kind` are fixed values. Nothing else prints a mapped value.
- Regex `[\x00-\x08\x0b-\x1f\x7f-\x9f]` covers ESC (0x1b), BEL (0x07), CR, DEL and U+0080 to U+009F. `\x1b` and U+009B are the two the test uses. `_JSON_CONTROLS` `[\x7f-\x9f]` is right: `json.dumps(ensure_ascii=False)` escapes C0 itself, and `\u009b` stays valid JSON for the same character.
- Reversibility of `chronicle`: the backslash is doubled first, then tab, LF and CR, then the controls, so a literal `\x1b` (`\\x1b`) and an ESC (`\x1b`) stay apart; the test pins both. `cli.md` still says the backslash is escaped first.
- `show` keeps LF and tab in a unit, so a stranger's text can still start a line that looks like `id=…`. That was asked for ("keep tab/newline handling") and is not a terminal command.
- Existing typed output is unchanged: the full suite's green run in the report and the dots in the tutorial agree; no typed block holds a control character. The `T201` count stays 36 (no `print` added).

### Erase query checked (focus 3)

By reading the SQL on `ingest-a-mail-folder.md`:

- `inside` starts at the Message-ID's event. Each step takes, for every found event's key, the events whose `forwarded_in` equals that key (mails inside, at every depth, because the recursion repeats) and the events whose key is that key plus `#` (variants), by `left(…) = key || '#'`, so no `LIKE` wildcard problem. A variant's own inner mails carry the variant key in `forwarded_in` (`core/ingest.py` rewrites it), so they are found too.
- `around` adds, for each found event, the other events that hold its raw-mail address in `event_blob` (an outer mail's `message/rfc822` attachment has the inner mail's content address; `carrier.event_id <> event.id` leaves out the mail's own raw blob), and repeats for those, so carriers of carriers at every depth. A variant's raw mail and a variant of a carrier are found the same way.
- `UNION` ends the recursion. The output column `why` and the redact order (inner first, outer last) match the real run that the page types.
- The query reads `payload`, so it cannot follow an already erased event (accepted, as named; see Out-of-Scope for a neighbor of that case).

## New Breakage

- **Minor 1** (name, consequence of decided item 4), `src/previously/cli.py:_cmd_append`: an event that `append --text` wrote before this change with a CRLF or CR text carries the hash of the text as typed. The same text submitted again now hashes as LF and is refused as `known with another content`, where it was known before. Release `0.1.0a1` is on PyPI, so such events can exist. Neither `cli.md` nor `hash-format.md` names this one-time effect; both only say what the new rule is.
- **Minor 2** (docs): the new page query is not under any committed test. A change to the payload keys (`raw`, `forwarded_in`) or to the key format would silently stale the page. The implementer's scratch test shows it ran once.

No new Critical, no new Important.

## Out-of-Scope Observations

- The ledger `docs/superpowers/sdd/2026-10-06-pilot-imap-aufnahme/progress.md`, which the five citations in `tests/test_mail.py` name, is not in the tree yet; the controller ships it after this round. Until then the labels resolve nowhere, though the reasons stand beside them.
- The erase query does not reach the inner mails of a mail that was erased earlier: with the middle event's payload `NULL`, `forwarded_in` can no longer be read from it, so its children are not found from above. Same family as the accepted "later forward of an already erased mail".
- The worktree has two uncommitted changes that are not part of this fix wave: `CLAUDE.md` (the "six contract names" wording) and `DEPENDENCIES.md` (the `html2text` row). Presumably the maintainer's; the brief reserves `CLAUDE.md` for him.
- `docs/explanation/concurrency.md` and `docs/explanation/module-boundaries.md` still contain "afterwards" or "towards"; neither was in the docs review, and `vale` passes.

## Verdict

**Fix wave:** all addressed, no new Critical/Important
