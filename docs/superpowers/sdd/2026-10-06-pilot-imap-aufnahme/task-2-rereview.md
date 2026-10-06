### Finding Verdicts

Read: the findings file, the brief, the previous review, the report's "Fix round 1", the package `review-0807c35..a1da00e.diff` (mail.py, tests, tutorial hunks), and `src/previously/core/mail.py` whole at `a1da00e` (the working tree equals it for that file; HEAD `5735843` only touches the spec).
Measured with invented mails through `map_mail` (scratch `r1.py`, `r2.py` in the scratchpad); suite not re-run.

1. **Important 1 — only the first `text/plain` became the body: ADDRESSED.**
   `mail.py:575-606` (`_body_parts`, `_content`): a part with `is_attachment()` or any `get_filename()` (covers `filename=` and `name=`) is never body (`594-595`); a `text/*` part or an unsplit multipart is body (`596-597`); `multipart/mixed`/`signed`/others contribute every child in order (`606`); `multipart/related` takes its `start` root or the first child (`604-605`, `644-652`).
   Attachments are every leaf not in body or alternatives (`665-674`).
   Units join all body texts in order (`714-727`); identity takes one digest per chosen part, in order, LF-normalized (`276`), as T2-d asks.
   Tests: `test_mail.py:652-674`, `717-728`.
   Measured myself: Apple-Mail split in the HTML form (`alternative{plain, mixed{html, pdf, html}}`) gives plain as body and the PDF as attachment; a list footer as a trailing inline `text/plain` beside `alternative{plain, html}` gives both texts as units in order.
2. **Important 2 — empty `text/plain` beside full HTML: ADDRESSED.**
   `mail.py:609-634` (`_alternative`): options ranked plain < HTML < other; the first ranked option with non-blank text wins (`625-628`; `str.strip` treats NBSP as blank); all blank keeps the best-ranked one. Unchosen plain/HTML go to `alternatives`, not attachments (`629-633`).
   Tests: `test_mail.py:677-690` (incl. Outlook's `related` with `start` naming the HTML after the image).
   Measured myself: `related{alternative{plain "", html}, image}` → units `["Outlook", "Nur hier."]`, body `text/html` with converter, image an attachment.
3. **Important 3 — `iso-8859-1` with cp1252 bytes: ADDRESSED.**
   `mail.py:375-406` (`_decode`): labels resolving to `iso8859-1`/`cp1252` read via `_windows_1252` (`357-362`, Latin-1 for the five undefined bytes), `guessed: false`; undeclared, `us-ascii` with bytes > 127, or unknown label → `_guess` (`365-372`, strict UTF-8 then cp1252), `guessed: true`; `replaced` only set on a real replacement (`398-400`, `405-406`). Payload carries `charset`, `declared`, `guessed` (`291-301`).
   Tests: `test_mail.py:734-777` (five guess cases plus the label case).
   Measured myself: `charset="ISO-8859-1"` with `\x84Angebot\x93 \x96 100 \x80 f\xfcr M\xfcller` → `„Angebot“ – 100 € für Müller`, `windows-1252`, declared `iso-8859-1`, guessed false, replaced false.
4. **T2-b with T2-f — `map_mail` never raises on mail content: ADDRESSED.**
   `mail.py:190-217`: `iso_utc(internaldate)` before the `try` (naive still raises, test `test_mail.py:341`); `except Exception` → `_unreadable` (`220-249`): `source=email`, `external_id = "sha256:" + sha256(raw)`, `artifact_hash = sha256(raw)`, `occurred_at = internaldate`, one unit `"unreadable mail: " + type(error).__name__` (class only, `245`), `Mapped.raw` = raw, no attachments/inner.
   Inner mails go through `_map_or_keep` each (`314-322`), so an inner failure does not sink the outer.
   Tests: `test_mail.py:783-808`.
   Measured myself: `charset=base64` (a codec that is no text encoding) → `unreadable mail: LookupError`, nothing raised.
5. **T2-g — the minors: ADDRESSED.**
   - Subject replacement noted: `headers_replaced` (`mail.py:452-470`, `303-304`); test `test_mail.py:814-819` with a control.
   - Tab folding: `_FOLD` (`106`, `433-434`) applied before decoding (`465`); test `test_mail.py:822-832` over four foldings.
   - Identity across 8bit/QP/base64: `test_mail.py:835-849`.
   - The four comments: `MAX_FORWARD_DEPTH` `61-66`, `Attachment` `121-126`, `_readable` `344-348`, `_collect` `806-813` — each now matches the code.

**Extensions T2-h, checked for correctness:**
- Line-travelled attachments enter with LF (`mail.py:688-697`, `115-117`); base64/binary unchanged; `not_unpacked` keeps raw blob addresses (`324`). Correct; test `test_mail.py:707-714`.
- `headers` unfolded for every header (`465`): measured `References: <a@x>\r\n\t<b@x>` → `<a@x> <b@x>`, folded encoded-word subject → `Grüße aus Wien`. Correct.

### New Breakage in the Fix Diff

1. **Minor — the `_recovered` docstring claims more than `_headers` does** — `src/previously/core/mail.py:437-443` with `465`.
   It says an escaped byte "out of an encoded word labelled `unknown-8bit`" is read as UTF-8, else Windows-1252.
   In `_headers`, `_recovered` runs before the encoded words are decoded, so it never sees them: `Subject: =?unknown-8bit?q?Gr=FC=DFe?=` → `Gr��e`, `headers_replaced: ["From", "Subject"]` (measured).
   The same bytes in a display name are recovered (`Jörg`), because `_channel_identities` applies `_recovered` after parsing (`517-518`).
   UTF-8 bytes in such a word do read correctly, but that comes from the stdlib's own sanitizing, not from `_recovered`.
   Where it shows: the fallback that writes an attached mail back out (lone CR, or a cut that disagrees) — measured: an inner mail with a raw Latin-1 subject and CR line endings maps to `Gr��e`, where the same mail on its own reads `Grüße`. It is flagged in `headers_replaced`, not silent.
   Fix the sentence, or apply `_recovered` after decoding in `_headers` too. The input is malformed, so the behaviour is "name". The docstring is a claim, and this one is in the fix diff.
2. **Minor, name — a charset label that resolves to a non-text codec turns the whole mail unreadable** — `mail.py:389-400`.
   `codecs.lookup` accepts `base64`, `hex`, `quoted-printable` (quopri), `rot13`, `zlib` and similar; `bytes.decode` then raises `LookupError`, which is not `UnicodeDecodeError`, so the mail becomes `unreadable mail: LookupError` instead of having its charset guessed (measured with `charset=base64`).
   The run does not stop, so this is misuse only.
3. **Minor, name (follows ruling T2-d) — a bounce's `text/rfc822-headers` part becomes body.**
   A Postfix-style `multipart/report{text/plain, message/delivery-status, text/rfc822-headers}` gives units `["Undelivered Mail", "This is the mail system.", "From: …\nTo: …\nSubject: Vertraulich: Angebot"]` (measured).
   No text is lost, but the bounced mail's headers become searchable units.
   This is what "every `text/*` part without a file name" says. The reference page or the map should name it, and code does not need to change.

No Critical, no Important.

### Out-of-Scope Observations

- A declared `utf-8` label over Latin-1 bytes still reads as declared and gives U+FFFD with `replaced: true` (ruling T2-e reads "any other label" as declared). It is a common mislabelling, and the map may want it as an open point beside T2-e.
- `message/delivery-status` has a list payload, so `_attachment` sends it through `_message_bytes`. Its multi-block payload never gives a cut, so it is always written back out (pre-existing, `mail.py:681`, `816`).
- The tutorial's typed block was retyped whole: `collected 965 items`, `965 passed`, and the `test_mail.py` rows sum to 144. This matches the report.

### Verdict

**Fix round:** All findings addressed, no new Critical/Important breakage.
