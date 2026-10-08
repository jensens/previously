# Task 2 report — `core/mail.py`

**Status:** DONE_WITH_CONCERNS. Commit `0807c35` on `worktree-pilot-aufnahme` (base `5aa447a`). 919 tests passed (820 + 98 in `test_mail.py` + 1 contract probe). All six gates green, `pip-audit` clean.

## What was built

- `src/previously/core/mail.py`: `Attachment`, `Mapped`, `MAX_FORWARD_DEPTH = 5`, `map_mail`, `variant_key`, and the fixed sentences as constants (`NO_BODY_*`, `CONVERTER`, `SOURCE`).
- `tests/mailfiles.py` writes `tests/mails/*.eml`: 27 invented mails, German and English, all CRLF. `test_every_mail_file_is_what_mailfiles_writes` holds every file against those bytes. `tests/mails/.gitattributes` sets `*.eml -text`.
- `tests/test_mail.py` (98 tests). `tests/test_contracts.py` adds one probe for the new contract.
- `html2text>=2025.4` in `pyproject.toml`/`uv.lock`. The `DEPENDENCIES.md` row was rechecked on 2026-10-06 with `gh api` and PyPI rather than copied from the plan.
- `.importlinter` has the new contract `Only core.mail imports html2text`, one named edge. The header count now reads "Six of the seven".
- Docs that had to follow: `docs/explanation/module-boundaries.md` (gate output retyped from a run, diagram arrow, caption, a section "A contract for the mail", "last three contracts"). The tutorial's pytest block was retyped under ruling P-1: placeholder, green run, whole block, no `rootdir:` line.

## Decisions beyond the brief (please confirm)

1. **`unicode_snob = True` for html2text.** Without it, html2text writes `&uuml;` as `u` ("für" becomes "fur", "Grüßen" becomes "Grußen"). Measured on 2026-10-06 with 2025.4.15. That is silent content loss, and the plan's comparison of converters missed it. Mutation M5 guards it.
2. **New payload name `not_unpacked`.** The brief requires the depth-5 mail to record the mail it did not unpack, but the contractual list of names has none for that. I chose `not_unpacked`: the list of SHA-256 hex of the `message/rfc822` attachments left as blobs. Task 6's reference page and the wording table need it.
3. **`headers` values as written.** Each value is unfolded and its encoded words decoded, nothing more (an unstructured `HeaderRegistry`). The default policy re-renders structured headers: `"Office" <…>` loses its quotes, `charset=utf-8` gains some.
4. **The fixed sentence also stands when a subject exists.** Units are subject (if any), then body paragraphs, or the sentence when there is no readable body. This follows the brief ("der feste Satz bei keinem lesbaren Körper"). Spec §3.2 only fixes the case of no subject and no body, which yields a single unit as required.
5. **Which sentence.**
   - Encrypted wins, when `multipart/encrypted` or S/MIME `application/(x-)pkcs7-mime; smime-type=enveloped-data|authenveloped-data` is present.
   - Otherwise "attachments only" when there is an attachment.
   - Otherwise "empty".
   - An empty body part counts as no readable body. The forward with an empty frame therefore says "attachments only".
6. **`body.charset` is the charset the text was read with**, not the declared one: `iso-8859-1` for an unknown charset, `us-ascii` when none is declared (RFC 2045). `body.part` is the content type. `body` is `null` only when no body part exists. A mail without `Content-Type` is `text/plain`, so it has an empty body part.
7. **Attachments are every leaf part except the body and its `text/plain|html` alternatives** under the same `multipart/alternative`. Inline images, calendar parts, PGP signatures and encrypted parts are kept.
8. **The body is the first non-attachment `text/plain`, else `text/html`.** I wrote my own body finder rather than using `get_body`. The reason: when a multipart's boundary is missing, `get_body` returns `None`, and the text would be lost. In that case the unsplittable multipart's payload becomes the body, MIME lines included (`broken_mime`).
9. **The inner raw mail is cut from the outer bytes, not re-serialized.** Measured: the generator writes raw UTF-8 headers as `=?unknown-8bit?…?=` and normalizes blanks after colons. Without the cut, a mail forwarded and also lying in the folder would be two raw mails. The cut is checked against the parser by comparing the cut body with the parser's attached mail, ignoring the final line ending. If no cut is found, or it disagrees, the part is written back out instead.
10. **base64 and quoted-printable `message/rfc822`** are decoded first. RFC 2046 forbids both encodings there, but clients send them. Without decoding, a garbage event would land in the append-only log.
11. **Subject in the hash.** It is the decoded header value with nulls replaced (the canonical form refuses `\x00`). An absent subject is `null`, an empty one is `""`.
12. **8-bit header bytes** (display names, filenames) are recovered as UTF-8 (RFC 6532). What is not UTF-8 becomes U+FFFD.

## Each test mail and what came out

All mails use `internaldate = 2026-10-08T12:00Z`. "Units" lists unit 1 (the subject) first.

| Mail | What it is | What came out |
|---|---|---|
| `plain` | text/plain UTF-8 8bit, umlauts, two `Received`, To before From, Cc, Reply-To | key `20261005101500.4711@example.net`; `occurred_at` 2026-10-05 10:15+02 from the header; 5 units (subject, 4 paragraphs incl. signature); body text/plain utf-8, no converter, replaced false; identities in header order to,to,from,cc,reply_to; all 12 headers; no attachments |
| `plain_other_transport` | same mail, other Return-Path/Delivered-To/Received | same key, same artifact hash, other headers |
| `plain_other_body` | same Message-ID, "three weeks" | same key, other artifact hash |
| `html_only` | Outlook HTML, windows-1252 QP, `&uuml;`, `&nbsp;` paragraphs, tracking pixel | 4 units, umlauts intact, pixel absent; body text/html windows-1252 `html2text 2025.4.15`; hash over the QP-decoded bytes |
| `html_blockquote` | Gmail HTML base64 with `blockquote` | 5 units, the quote as `> Können …` |
| `no_message_id` | no Message-ID | key `sha256:<artifact hash>` |
| `date_unreadable` | `Date: Montag, 5. Oktober 2026, 10 Uhr` | `occurred_at` = internaldate, `date_source` internaldate |
| `date_without_zone` | `-0000` | internaldate (naive datetime) |
| `date_missing` | no Date | internaldate |
| `charset_unknown` | `x-mac-klingon`, Latin-1 bytes | "Grüße aus Graz."; charset iso-8859-1, replaced true |
| `body_unreadable` | UTF-8 with `\x00` and `\xff` | U+FFFD in both units; replaced true; hash over the raw bytes |
| `body_lone_surrogate` | UTF-7 body `+2D0-` (lone surrogate) | U+FFFD; replaced true |
| `headers_8bit` | raw UTF-8 subject and From name, Latin-1 Sender name and X-Note, null in X-Null | subject "Grüße aus Köln", name "Jürgen Müller", "J�rg", `Gr��e`, `a�b` |
| `encrypted` | PGP/MIME | [subject, "no readable body: encrypted"]; body null; 2 attachments (pgp-encrypted, encrypted.asc) |
| `encrypted_smime` | S/MIME enveloped-data, top-level | same sentence; 1 attachment smime.p7m with the decoded bytes |
| `empty` | headers only, subject | [subject, "no readable body: empty"]; body text/plain us-ascii (empty) |
| `attachments_only` | no subject, PDF and PNG | single unit "no readable body: attachments only"; hash subject null, body null, 2 sorted hashes |
| `signed` | PGP multipart/signed, QP text | 4 units of the text; signature.asc as attachment |
| `reply` | multipart/alternative, In-Reply-To, folded References, quote | both headers in `headers`; body text/plain; HTML alternative is no attachment; 5 units |
| `forwarded` | empty frame plus `message/rfc822` with raw UTF-8 From and its own PDF | outer [subject, "attachments only"], 1 attachment = inner bytes exactly; inner key `invoice-2026-10@example.com`, `forwarded_in` `fwd-20261008@example.org`, own `Date`, 4 units, own PDF; outer has no PDF and none of the inner text; inner hash equals the same mail mapped on its own |
| `forwarded_base64` / `forwarded_quoted_printable` | the same with a transfer encoding | decoded; inner event equal to `forwarded`'s |
| `nested_six` | 7 mails deep | levels 1–5 unpacked, each `forwarded_in` its parent and its own date; level 5 keeps level 6 as a `message/rfc822` attachment, `not_unpacked: [sha]` |
| `broken_mime` / `broken_mime_no_boundary` | boundary declared ≠ used / no boundary param | whole body read as text (MIME lines included); body part multipart/mixed, us-ascii, replaced true (the `ä` is lost, see concerns) |
| `broken_mime_truncated` | no closing delimiter, base64 cut | text unit read; EG.pdf attachment with the bytes that arrived |
| `duplicate_attachments` | same PDF twice, one RFC 2231 name with umlauts | 2 attachments ("Angebot für Müller.pdf"); hash lists the SHA twice |

Also tested without a file:
- LF line endings for `forwarded`: the cut works.
- Lone CR line endings: the cut is not found and the part is written back out, with content intact.
- A non-header line right below the attached part's headers: the cut is refused.
- A naive internaldate raises `InvalidPayload`.
- `variant_key` gives `<id>#<16 hex>`.
- Mapping is pure (equal output twice).
- Text nowhere in the payload: every body unit of 15 characters or more, all mails. Shorter units are skipped because "Eva" legitimately stands in the headers too.
- Every mail maps to something `check_units`, `canonical` and `iso_utc` accept, with only allowed payload names.

## TDD evidence

- **Red:** `test_mail.py` was written first, against the 14 mail kinds of the brief plus the copies. The first run failed at collection: `ModuleNotFoundError: No module named 'previously.core.mail'`.
- **Green:** after the implementation, 86 of 87 passed. The failure was my own wrong expectation: the `empty` mail has a body part, since `text/plain` is the MIME default. I corrected the test.
- **Written after the code:** the `date_missing`, `body_lone_surrogate`, Latin-1 display name, lone-CR and quoted-printable tests came from coverage and measurement. They were green on arrival; each is backed by a mutation below.
- **Bug found by a mutation:** the cut was verified at the wrong level. M16 stayed green, which led to the case of a non-header line below the part headers. Before the fix, that cut dropped the line and the attached mail's headers. After the fix the new test reads the check (M16 red).

## Mutations

Each mutation was applied, run, and restored at once; `git status` was clean afterwards. Scratch script: `mutate.py` in the scratchpad.

| # | Mutation | Target (red) | Control (green) |
|---|---|---|---|
| M1 | transport lines (`headers`) in the artifact hash | two copies → one artifact | other body → other artifact |
| M2 | no unpacking | forwarded becomes own event | plain field by field |
| M3 | depth without limit | nesting down to five | forwarded own event |
| M4 | Date without fallback | date fallback [date_unreadable] | plain |
| M5 | no `unicode_snob` | html_only paragraphs | blockquote |
| M6 | no cut (always re-serialized) | raw of forward byte-equal | forwarded own event |
| M7 | alternatives kept as attachments | reply | signed |
| M8 | `multipart/encrypted` not recognized | encrypted [PGP] | encrypted [S/MIME] |
| M9 | no surrogate-escape recovery of header bytes | headers_8bit | plain |
| M10 | body text copied into the payload | text nowhere in payload (16 of 27 red) | copies |
| M11 | `not_unpacked` not recorded | nesting | forwarded |
| M12 | HTML preferred over plain | reply | plain |
| M13 | no null replacement | null/unreadable byte | unknown charset |
| M14 | unknown charset not Latin-1 | unknown charset | null/unreadable |
| M15 | identities sorted by role | header order | headers_8bit |
| M16 | cut not checked against the parser | cut the parser disagrees with | plain |
| C1 | drop the `html2text` exemption | `lint-imports`: contract BROKEN at `core.mail -> html2text` | — |
| C2 | drop the `html2text` contract | probe test red | pyrage probe green |

## What real mail could bring that the tests do not cover

- **Undeclared charset with 8-bit text** is read as US-ASCII (RFC 2045), so umlauts become U+FFFD with `replaced: true` (shown by `broken_mime`). The raw mail keeps them. Reading undeclared text as UTF-8 would avoid that but goes beyond the brief.
- **An empty `text/plain` beside a full HTML alternative:** the plain part is chosen (spec: plain if there is one), so the units are empty and the HTML text is only in the raw mail.
- **Apple Mail splits the text around an inline image** (text, image, text in `multipart/mixed`). Only the first text part becomes the body; the later pieces become `text/plain` attachments. Their text is in blobs, not in units.
- **`message/global`** (forwarded SMTPUTF8 mail) and `message/delivery-status` become attachments but are not unpacked; only `message/rfc822` is.
- **An inline `.txt` without `Content-Disposition: attachment`** can be chosen as the body over an HTML part.
- **Several `Subject`, `Date` or `Message-ID` headers:** the first one counts.

## Named, not engineered (malformed or hostile only)

- **A UTF-7 encoded word that decodes to a lone surrogate** (`=?utf-7?q?+2D0-?=`) in any header makes the standard library's header classes raise `UnicodeEncodeError`. `map_mail` raises for such a mail. Measured in an `X-` header, in `From` and in `Date` (Python 3.14.3); documented at `_headers`.
- **Broken base64 inside a base64-encoded `message/rfc822`:** the bytes stay undecoded and are mapped as a mail without headers (uncovered lines 629–632).
- **A non-ASCII boundary** gives no cut, so the fallback applies (uncovered lines 552–553).
- **A charset whose codec refuses `errors="replace"`** (e.g. `idna`) would raise from `_decode`.
- **Python's recursion limit:** very deep nesting of multiparts (not of mails, which stop at depth 5) could reach it in `_walk` and `_collect`.

## Gates (final tree, each run on its own)

```
uv run ruff check .                      All checks passed!
uv run ruff format --check .             78 files already formatted
uv run pyright                           0 errors, 0 warnings, 0 informations
uv run lint-imports                      Contracts: 7 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing
                                         919 passed in 98.10s; TOTAL 98.07% (core/mail.py 99%, missing 552-553, 629-632)
make -C docs html                        build succeeded.
make -C docs vale                        ✔ 0 errors, 0 warnings and 0 suggestions in 31 files.
make -C docs linkcheck                   build succeeded (0 broken)
uv run pip-audit --skip-editable         No known vulnerabilities found
```

## Concerns

1. **Task 4 needs a policy for a mail that does not map.** `map_mail` raises for the UTF-7 header case above, and possibly for unknown stdlib edge cases. Today such a mail would stop the run before the watermark, so every later run stops at the same mail and the folder never advances past it.
2. **`CLAUDE.md` says "the six contract names in `.importlinter`"**; there are now seven, and Task 5 adds more. I did not edit `CLAUDE.md`; that is for the controller or the maintainer.
3. **`html2text` is GPL-3.0-or-later.** It is the only copyleft dependency besides the project's own AGPL-3.0-or-later licence. Combining the two is allowed (section 13 of both licences), and the `DEPENDENCIES.md` row says so. The maintainer may want to know.
4. **`not_unpacked`** is a payload name outside the contractual table (decision 2). Task 6 has to put it on the reference page and in the table.
5. **Memory.** The check behind the cut parses and writes back out every attached mail twice. A forward with a large attachment holds a few copies of it while it is mapped.

---

# Fix round 1

**Status:** DONE_WITH_CONCERNS. Commit `a1da00e` (on `0807c35`). 965 tests passed (919 + 46 in `test_mail.py`; `test_mail.py` now holds 144). All six gates green, `pip-audit` clean. 14 new invented mails (41 in all), held byte for byte by `tests/mailfiles.py`. `src/` was unchanged from `0807c35` when the new tests were first run.

## Per ruling

### T2-d — the body is every text part of the content, in order

**Changes in `core/mail.py`:**
- `_body_parts` and `_content` replace the old "first `text/plain` anywhere" finder.
- A part is body when it is `text/*` (or a multipart whose boundary cannot be found), has no file name (`filename=` or `name=`, via `get_filename()`), and is not `Content-Disposition: attachment`.
- `multipart/mixed`, `multipart/signed` and the like contribute every child in order.
- `multipart/alternative` (`_alternative`) ranks plain before HTML before anything else. An option whose text is empty or blank gives way to the next; if every option is blank, the best-ranked one is kept, which gives "no readable body: empty".
- The plain and HTML parts of the options not chosen count as alternatives: neither body nor attachment. Any other part of them (an image, a `text/calendar`) stays an attachment.
- `multipart/related` takes its root: the child its `start` names, otherwise the first (RFC 2387).
- The units are the subject, then `split_plaintext` over the parts' texts joined by a blank line.
- Attachments are every leaf that is neither body nor alternative.

**Identity (§3.3):**
- `"body"` is now a **list**: the SHA-256 of each chosen part's decoded bytes, in order, with every line ending as LF. A mail with no body part gives `[]` instead of `null`.

**Extension beyond the ruling (please confirm):**
- Attachments that travelled as lines (no CTE, 7bit, 8bit, quoted-printable; this includes an attached `message/rfc822`) enter the identity with LF line endings.
- Otherwise an LF copy of a forwarded mail would still become a variant, because its attached mail's bytes differ in line endings.
- base64 and binary attachments enter as they are, so their digest stays their blob address.
- `not_unpacked` keeps listing blob addresses (raw SHA-256).

**Payload:**
- `body` is now a **list** with one entry per chosen part: `{"part", "charset", "declared", "guessed", "converter", "replaced"}`. It is `[]` when there is no body part.

**Test mails:**
- `apple_split`: text, an inline PDF, text.
- `html_with_text_attachments`: HTML, plus `notiz.txt` inline with a filename, plus `liste.txt` with only `name=`.
- `alternative_empty_plain`: `text/plain` holding only an NBSP, beside HTML.
- `plain_lf`: the simple mail with LF only.
- `alternative_related`: an empty plain part beside a related part whose `start` names the HTML, which stands after the image.
- `related_without_start`.

The LF copy of the forward is derived in its test.

### T2-e — charsets (replaces T2-c)

`_decode(data, declared)`:
- A label that resolves to `iso8859-1` or `cp1252` reads as Windows-1252, with Latin-1 for 0x81, 0x8D, 0x8F, 0x90 and 0x9D (`_windows_1252`). This is not a guess.
- Any other known label reads as declared; what fails becomes U+FFFD with `replaced: true`.
- Pure ASCII, undeclared or labelled US-ASCII, reads as `us-ascii` and is not a guess.
- Otherwise the charset is guessed (`_guess`), which sets `guessed: true`: strict UTF-8 first, else Windows-1252. That covers no label with bytes above 127, a US-ASCII label with bytes above 127, and a label Python does not know.
- `replaced` now means only "a character was replaced" (U+FFFD for unreadable bytes, a null byte or a lone surrogate).
- `charset` is what the text was read with; `declared` is the label as given, lowercased, or `null`.
- Raw 8-bit header bytes, display names and filenames go through the same guess (`_recovered`). Before, Latin-1 header bytes became U+FFFD; now `Jörg` and `Grüße` read correctly.

**Test mails:**
- `charset_latin1_label`: „Angebot" – 100 € für Müller, cp1252 bytes under `iso-8859-1`.
- `charset_undeclared`: UTF-8 bytes with no label.
- `charset_ascii_8bit`: UTF-8 bytes under `us-ascii`.
- `charset_unknown_utf8`: UTF-8 bytes under `unknown-8bit`.
- `charset_undefined_byte`: undeclared bytes 0x80 and 0x81.
- The existing `charset_unknown` (Latin-1 bytes under `x-mac-klingon`) now reads as a guessed Windows-1252.

`broken_mime` and `broken_mime_no_boundary` now keep their `ä` (guessed UTF-8).

### T2-b and T2-f — `map_mail` never raises on mail content

- `_map_or_keep` checks `iso_utc(internaldate)` before the `try`: a naive `internaldate` raises `InvalidPayload`.
- It then wraps `_map` in `except Exception`, with no lint suppression (`BLE` is not selected) and the reason written in a comment.
- A failure becomes `_unreadable`:
  - `source = email`
  - `external_id = sha256:<SHA-256 of the raw bytes>`
  - `artifact_hash` = the SHA-256 of the raw bytes
  - `occurred_at = internaldate`
  - payload `date_source: "internaldate"`, `internaldate`, `found_in`, and `forwarded_in` for an inner mail
  - no headers, no body, no identities, no attachments, no inner mails
  - `Mapped.raw` is the raw mail, so it is still stored as a blob
- Each attached mail goes through `_map_or_keep` on its own, so an inner failure does not sink the outer mail.

**The fixed sentence (contractual, for the wording table):**

```
unreadable mail: <exception class name>
```

The prefix is the constant `UNREADABLE_MAIL = "unreadable mail: "`, followed by `type(error).__name__` only, never the message. Measured with the UTF-7 header: `unreadable mail: UnicodeEncodeError`.

**Test mails:**
- `unreadable_header`: `Subject: =?utf-7?q?+2D0-?=`.
- `forwarded_unreadable`: a readable outer mail carrying `unreadable_header` as an attachment.

### T2-g

- **A replaced character in the subject is noted.** The new payload name `headers_replaced` lists, in order, the names of the headers in which a character was replaced. It is present only when not empty.
  - A header counts when `_readable` replaced a null byte or a lone surrogate, or when the decoded value holds U+FFFD that the source did not.
  - The second check is needed because the decoder replaces silently: an encoded word labelled UTF-8 that holds Latin-1 bytes decodes to `Gr��e` with no defect recorded (measured).
  - Test mail: `subject_replaced`.
  - `headers_8bit` now gives `headers_replaced: ["X-Null"]`.
- **Folding whitespace is normalized.** `_FOLD` unfolds a line break plus the blanks after it into one space, for every header value, so the payload's `headers` change too: the `Received` lines read `…) by mail…` instead of `…)\tby mail…`.
  - Test: the subject folded as space, CRLF+space, CRLF+tab and CRLF+blanks+tab gives one hash.
- **The identity is pinned across transfer encodings.** The simple mail as 8bit, quoted-printable and base64 gives the same units and the same hash (derived in the test).
- **Four untrue comments corrected:**
  - the `MAX_FORWARD_DEPTH` docstring now says a mail attached *to* the mail at depth 5 stays an attachment;
  - the `Attachment` docstring now says the transfer encoding is undone first;
  - the `_readable` docstring now covers every value it is applied to, the subject included;
  - the comment in `_collect` now says `_agree` strips every trailing CR and LF.

Also corrected: the comment block above the cut said the whole part is compared, where it is the body; and a docstring held a literal `—` escape.

## TDD: red against `0807c35`

The new tests were run with `src/` byte-equal to `0807c35`. 16 were red, every one on the content itself except one:
- `apple_split`: units stop after "Erster Teil vor dem Anhang."
- `html_with_text_attachments`: unit "Inhalt der Notiz." instead of the HTML text.
- `alternative_empty_plain`: "no readable body: empty".
- `plain_lf` and the LF forward: different hashes.
- The body-hash-per-part test: different hash.
- `charset_latin1_label`: `'\x84Angebot\x93 \x96 100 \x80 für Müller'`.
- `charset_undeclared`: `'Gr����e aus Wien'`.
- `charset_ascii_8bit`: `'f��r M��ller'`.
- `charset_unknown_utf8`: `'GrÃ¼Ã\x9fe aus Linz'`.
- `charset_undefined_byte`: `'Preis � 5, Zeichen �.'`.
- `charset_unknown`: red only on the payload shape; the text was already right under Latin-1.
- `unreadable_header` and `forwarded_unreadable`: `UnicodeEncodeError` raised out of `map_mail`.
- `subject_replaced`: `KeyError 'headers_replaced'`.
- Tab folding: 3 different hashes for 4 foldings.

The transfer-encoding test was green against `0807c35`: it pins a property the reviewer had measured as holding. N18 below is its red.

`related_without_start` and `alternative_related` were added after the implementation, for coverage of `_root`; N20 is their red.

## Mutations

Each mutation was applied to `core/mail.py`, run, and restored. The file was byte-compared with a backup afterwards: identical. Scripts: `mutate_fix1.py` and `mutate.py` in the scratchpad.

| # | Mutation | Target | Control |
|---|---|---|---|
| N1 | only the first child of a multipart is body | apple_split RED | plain GREEN |
| N2 | a text part with a file name can be body | file name is attachment RED | signed GREEN |
| N3 | an empty plain option does not give way | empty plain gives way RED | reply GREEN |
| N4 | body digest without LF | LF copy RED | two copies GREEN |
| N5 | attachment digest without LF | LF copy of a forward RED | duplicate attachments GREEN |
| N6 | ISO-8859-1 read as ISO-8859-1 | iso-8859-1 as windows-1252 RED | guess [undeclared] GREEN |
| N7 | the guess skips UTF-8 | guess [undeclared] RED | guess [x-mac-klingon] GREEN |
| N8 | a US-ASCII label trusted over bytes above 127 | guess [ascii-8bit] RED | guess [undeclared] GREEN |
| N9 | the five undefined bytes not read as Latin-1 | guess [undefined-byte] RED | iso-8859-1 GREEN |
| N10 | a guess not noted (`guessed` false) | all 5 guess cases RED | iso-8859-1 GREEN |
| N11 | fallback only for `LookupError` | unreadable mail RED | plain GREEN |
| N12 | inner mails mapped without the fallback | inner does not sink outer RED | unreadable mail GREEN |
| N13 | the unit carries the error's message | unreadable mail RED | plain GREEN |
| N14 | naive `internaldate`: pre-check and the fallback's own `iso_utc` both removed | naive refused RED | unreadable mail GREEN |
| N14a | only the pre-check removed | naive refused **GREEN** | plain GREEN |
| N15 | `headers_replaced` not written | subject replaced RED | plain GREEN |
| N16 | decoder replacement not seen (only `_readable`'s flag) | subject replaced RED | headers_8bit GREEN |
| N17 | folding keeps its tab | tab folding RED | two copies GREEN |
| N18 | body digest over the transfer-encoded payload | transfer encodings RED | LF copy GREEN |
| N19 | header bytes not recovered | headers_8bit RED | plain GREEN |
| N20 | `multipart/related` ignores `start` | inline image RED | related without start GREEN |
| R7 | alternatives kept as attachments (M7 retargeted) | reply RED | signed GREEN |
| R10 | body text copied into the payload (M10 retargeted) | text nowhere in payload RED (24 of 41) | two copies GREEN |
| R12 | HTML preferred over plain (M12 retargeted) | reply RED | plain GREEN |
| R13 | no null replacement (M13 with a valid control) | null/unreadable byte RED | iso-8859-1 GREEN |

**N14a is green, and that is expected.** The refusal of a naive `internaldate` has two guards: the pre-check, and `_unreadable`'s own `iso_utc` call. Removing either one alone leaves the test green. N14 removes both, and the test goes red. I kept the pre-check because it keeps the intent visible and saves mapping a mail whose event could never be written.

**First-round mutations against the new code:**
- M1–M6, M8, M11, M15 and M16 are RED again, each control GREEN.
- M7, M10 and M12 had lost their target lines and were retargeted as R7, R10 and R12, all RED.
- M9 and M14 are replaced by N19 and N6–N10.
- M13's control named a test that no longer exists; it was rerun as R13.

## Named, for task 6

These go on the reference page and in the map; none is handled in code.
1. **Alt text of images is dropped** (`ignore_images`). `<img alt="Unterschrift Jürgen">` gives nothing; `images_to_alt` would keep it.
2. **html2text escapes Markdown characters**: `1. Punkt` → `1\. Punkt`, `- Strich` → `\- Strich`. Nothing is lost, but the units are not the words exactly as written, while `evidence` says `verbatim`.
3. **An unescaped `<` in HTML swallows text**: `Preis <100 Euro und a<b, x > y` → `Preis <100 Euro und a y`. Malformed HTML.
4. **Broken address lists lose or invent identities**: semicolons as separators keep only the first address; an unquoted comma in a display name gives a bogus identity; `eva@example.org (Eva Huber)` gives no name. All of these stay intact in `headers`.
5. **Opaque-signed S/MIME** (`application/pkcs7-mime; smime-type=signed-data`) has its text inside the p7m and says "no readable body: attachments only".
6. **Mails without a Message-ID and with the same content collapse into one event** (a daily "Backup OK"): the later ones are known. Spec §3.5 decides this; it is a point for the map.
7. **An encoded word whose label is wrong** (UTF-8 label, Latin-1 bytes) becomes U+FFFD. `headers_replaced` notes it, but it is not recovered; only raw 8-bit header bytes go through the UTF-8-then-Windows-1252 guess.
8. **A guess in a header is not noted**: raw 8-bit header bytes read as UTF-8 or Windows-1252 carry no `guessed` flag (there is no per-header body entry for one).
9. **Only `message/rfc822` is unpacked**; `message/global` and `message/delivery-status` stay attachments.
10. **The first `Subject`, `Date` and `Message-ID` count** when a mail carries several.
11. **Malformed or hostile, from round 1, now ending as an unreadable-mail event or named:**
    - a charset whose codec refuses `errors="replace"` (`idna`) now becomes an unreadable mail instead of raising;
    - very deep multipart nesting reaching the recursion limit is caught the same way;
    - a non-ASCII boundary gives no cut, so the fallback applies (lines 768–769 uncovered);
    - broken base64 inside a base64 `message/rfc822` is mapped undecoded (lines 846–849 uncovered).
12. **The identity of a text attachment that travelled as lines is not its blob address**: it is hashed with LF line endings (extension above). The reference page should state the rule.

## Gates

At `a1da00e`. Gates 1–4 were rerun after the commit, each as its own command. Gates 5 and 6 and `pip-audit` ran on the identical tree just before the commit, after the tutorial was retyped; the commit changed no file since.

```
uv run ruff check .                      All checks passed!
uv run ruff format --check .             78 files already formatted
uv run pyright                           0 errors, 0 warnings, 0 informations
uv run lint-imports                      Contracts: 7 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing
                                         965 passed in 97.72s; TOTAL 98.12% (core/mail.py 99%, missing 768-769, 846-849)
make -C docs html                        build succeeded.
make -C docs vale                        ✔ 0 errors, 0 warnings and 0 suggestions in 31 files.
make -C docs linkcheck                   build succeeded.
uv run pip-audit --skip-editable         No known vulnerabilities found
```

The tutorial's pytest block was retyped under ruling P-1 (placeholder, green run, whole block, no `rootdir:` line): 965 passed.

## Concerns

1. **The payload and identity shapes changed; the spec and the wording table need them** (the controller updates §3.2, §3.3 and §3.5):
   - `body` is a list of part entries with the new keys `declared` and `guessed`, and `[]` when there is no body part;
   - the identity's `"body"` is a list of per-part digests;
   - `headers_replaced` is a new payload name;
   - `unreadable mail: <class>` is a new fixed sentence.
2. **The attachment LF normalization goes beyond T2-d's text.** I took it from the ruling's reason, that an LF copy must not become a variant. Please confirm or overrule.
3. **`headers` now shows folding whitespace as one space** (T2-g applied to every header value, not only the subject), so header values in the payload are no longer byte-equal to the unfolded source.
4. **The unreadable-mail key for two copies of one broken mail** with different transport lines gives two events. This is the "Wenn falsch" direction of T2-b, unchanged.
5. **Still open from round 1:** `CLAUDE.md` says "six contract names" while there are seven; `html2text` is GPL-3.0-or-later.
