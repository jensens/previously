# Task 2 — review (commit `0807c35`, base `5aa447a`)

Reviewer: Opus, read-only on the worktree. Read: brief, global constraints, spec §3 (§3.1–§3.6) and §2.1/§2.2, rulings P-1, T2-a, T2-b, T2-c, the report, `core/mail.py` whole at the head, `core/units.py` (`split_plaintext`), the test list and the hash tests of `tests/test_mail.py`, `tests/mails/forwarded.eml`, and the config and documentation hunks of the diff (`.importlinter`, `DEPENDENCIES.md`, `pyproject.toml`, `module-boundaries.md`).

What I measured myself, not taken from the report:

- Task-scoped gate: `pytest tests/test_mail.py tests/test_contracts.py`: 103 passed. `ruff check` and `ruff format --check` on `core/mail.py`, `tests/test_mail.py`, `tests/mailfiles.py`: green. `pyright` on those three: 0 errors. `lint-imports`: 7 kept, 0 broken. I did not run the whole suite with `--cov` or the three doc targets (task-scoped; the report claims them).
- About 90 invented mails through `map_mail`, from scratch scripts `t1.py`…`t11.py` in the scratchpad (`h.py` is the harness). Nothing in the worktree touched. The findings below name the mail that shows each loss; every one can be rebuilt from the description.
- The mermaid diagram in `module-boundaries.md` recounted: 7 internal edges, 7 external arrows. Matches its caption.

### Spec Compliance

**§3.1.** `source` `email`; `external_id` the Message-ID with brackets and edge blanks stripped, else `sha256:<artifact_hash hex>`; `evidence` verbatim; `channel_identities` from the six headers in header order (groups give members, `<>` stays `<>`, measured); `Mapped.raw` plus `attachments` in mail order for the blobs. Matches.

**§3.2.** Subject first, then `split_plaintext` of the body; plain before HTML; quotes and signature stay; the fixed sentences exactly as the global constraints word them; U+FFFD for a null byte and for undecodable body bytes with `body.replaced`. Matches by the letter — but see Important 1 and 2: the rule "the `text/plain` part, if there is one" is implemented as "the first `text/plain` anywhere in the tree", and that loses text from the units in two ordinary shapes of mail. The payload notes a replacement only for the body, not for the subject (Minor 1).

**§3.3.** Measured: the same body as 8bit, quoted-printable and base64 gives one hash (`edaa7a6c…` three times); a subject folded at another place, or spelled as Q, B, split encoded words, ISO-8859-1 encoded words or raw UTF-8, gives one hash (`2ec74544…` five times); extra `X-` headers do not change it; base64 of an attachment rewrapped at another line length does not change it; one changed attachment byte does (`9575f542…` → `a535e4cb…`). Matches. Two edges named in Minor 5 and 6.

**§3.4.** `headers` complete, in order, duplicates kept, names as written, values unfolded and decoded. `date_source`, `internaldate`, `found_in`, `body` with `part`, `charset`, `converter`, `replaced`; `forwarded_in` only on inner mails; `not_unpacked` per ruling T2-a. `raw` and `variant_of` are absent by design (Task 4). No body text in the payload (the test checks units of 15 or more characters over all 27 mails). Matches.

**§3.5.** Date fallback measured on 23 spellings: `EST`, `PDT`, `pst`, `GMT`, `UT`, `Z`, no seconds, two-digit year, a weekday that does not match the date, `(CEST)` as a comment all read from the header; `CEST`/`MEZ` as zone, `-0000`, no zone, ISO 8601, `Okt`, hour 25, 31 February, `+2400` all fall back to `internaldate`. Nothing raised. Unknown charset → Latin-1 with `replaced`. Encrypted and signed as specified. Matches.

**§3.6.** Measured with my own forward (a multipart inner mail with its own PDF, and a single-part inner mail with raw UTF-8 headers), each with CRLF and with LF: the inner raw equals the original inner bytes exactly, the attachment content equals `inner.raw`, and the inner hash equals that of the same bytes mapped on their own. `forwarded_in` is the outer key; the inner PDF is not among the outer attachments; the inner text is not in the outer units. A top-level `Content-Type: message/rfc822` mail and an `inline` `message/rfc822` are unpacked too. Seven levels deep, with CRLF and with LF: levels 1–5 unpacked, level 5 carries `not_unpacked` with one SHA-256 and `forwarded_in` of level 4. Matches.

**Spec compliance: ✅** — by the letter of §3.1–§3.6. The three Important findings are text that the letter of §3.2 lets go.

### Strengths

- The identity rule holds against every transport variation I tried, and it is spelled out in tests from the bytes (`test_the_artifact_hash_is_subject_body_and_attachments`, the QP-decoded HTML hash), not read back from the code.
- The inner raw mail is cut out of the outer bytes and checked against the parser before it is used. That is the hard part of §3.6 ("ihre Bytes, wie sie im Anhang stehen"), and it is right for CRLF and LF alike; the fallback keeps content when the cut fails.
- `unicode_snob = True` is a real catch: without it, `&uuml;` becomes `u`. Same for the base64/QP-encoded `message/rfc822` that clients send against RFC 2046.
- The body finder that survives a missing boundary instead of returning `None` (as `get_body` would) keeps the text of a broken mail.
- Comments carry measurements with dates, and the uncovered lines are named with the reason they are uncovered.

### Issues

#### Critical

None.

#### Important

1. **Text after an attachment, and a text attachment before an HTML body, go missing from the units** — `src/previously/core/mail.py:405-419` (`_body_part`), `440-472` (`_attachment_parts`).
   `_body_part` takes the first `text/plain` leaf anywhere in the tree as the whole body. Every further text part becomes an attachment with no file name; its text is in a blob, never in a unit. Mails that show it:
   - (a) Apple Mail in plain-text format, or iOS Mail, with a photo or PDF placed between two paragraphs: `multipart/mixed { text/plain "Erster Teil vor dem Anhang.", application/pdf (inline), text/plain "Zweiter Teil nach dem Anhang: der Termin ist am Freitag." }`. Units: subject, "Erster Teil vor dem Anhang." The appointment is only in an unnamed `text/plain` blob. A Mailman footer added as a trailing `text/plain` part is the same shape.
   - (b) An HTML-only mail with a `.txt` attached as `Content-Disposition: inline; filename="notiz.txt"` (Apple Mail's disposition for attachments) or with only `name=` and no disposition: `multipart/mixed { text/html "<p>Hier der eigentliche Text der Mail.</p>", text/plain name="notiz.txt" }`. Units: subject, "Inhalt der Notiz." The mail's own text is an unnamed `text/html` attachment.
   Fix direction: when the body is not inside a `multipart/alternative`, the body is every inline text leaf of the body's `multipart/mixed` in order (joined, each converted as its type requires); and a text part that carries a file name is never the body while a nameless one exists. The identity in §3.3 would then need a word on "the chosen body part" when there are several — the hash of each in order, or of their concatenation. This touches §3.2/§3.3 and wants a ruling.

2. **An empty `text/plain` beside a full HTML alternative says "no readable body: empty", and the HTML text is nowhere but in the raw mail** — `src/previously/core/mail.py:412-415`, `464-470`, `507-510`.
   Mail: `multipart/alternative { text/plain "" (or only `=C2=A0`), text/html "<p>Der ganze Text steht nur hier.</p>" }` — a shape some generators, CRMs and mobile clients send. Units: subject, "no readable body: empty". That sentence is false, and the HTML part is skipped as an alternative of the body, so it is not even an attachment: the text exists only inside the raw-mail blob. Compounding: for such mails without a Message-ID, two different HTML texts under the same subject have the same `artifact_hash` (body = SHA-256 of the empty part) and therefore the same key `sha256:…`; the second is "known" and silently not appended.
   Fix direction: a `text/plain` part whose decoded text is empty or whitespace only does not count as "a `text/plain` part" in §3.2; the next candidate (the HTML) is chosen. The report names the case (concern list "what real mail could bring") but does not grade it; it is a loss, not a gap.

3. **Windows-1252 text labelled `iso-8859-1` loses its €, „“, – and … silently** — `src/previously/core/mail.py:270-283` (`_decode`).
   Mail: `Content-Type: text/plain; charset=iso-8859-1`, 8bit, body bytes of "„Angebot“ – 100 € für Müller" in cp1252. Unit: `'\x84Angebot\x93 \x96 100 \x80 für Müller'` with `replaced: false`. The C1 control characters display as nothing; a reader sees "Angebot 100 für Müller". This labelling is common in German mail from Windows clients and PHP mailers — common enough that the WHATWG Encoding Standard, every browser and Thunderbird decode the labels `iso-8859-1`, `latin1` and `us-ascii` as windows-1252. Fix direction: decode those labels as `cp1252`, and fall back to Latin-1 only for the five bytes cp1252 leaves undefined (0x81, 0x8D, 0x8F, 0x90, 0x9D). The hash is over bytes and does not move. The same applies to the Latin-1 fallback of §3.5 and of ruling T2-c (below). Encoded words in headers carry the same mislabelling; reaching them needs a step of its own (Minor 1).

#### Minor

1. **A replacement in the subject or another header is not noted in the payload** — `src/previously/core/mail.py:324` drops the flag of `_readable`. §3.2: "Ein Nullbyte und ein Zeichen, das sich … nicht lesen lässt, werden durch U+FFFD ersetzt; die Nutzlast vermerkt es." Mail: `Subject: Grüße` in raw Latin-1 bytes → unit 1 `Gr��e`, `body.replaced` false, nothing else says so. Raw 8-bit headers outside RFC 6532 are malformed, so: name it, or let the fix round of T2-c read header bytes the same way (strict UTF-8, else cp1252/Latin-1) and add a note.
2. **`ignore_images` drops alt text with the tracking pixel** — `src/previously/core/mail.py:297`. `<img alt="Unterschrift Jürgen">` gives nothing. `images_to_alt = True` keeps alt text without the URL, and a tracking pixel's alt is empty. Small loss; worth one measurement.
3. **html2text inserts Markdown escapes into the text** — `1. Punkt` → `1\. Punkt`, `- Strich` → `\- Strich`, `+ Plus` → `\+ Plus`, `2026. Jahr` → `2026\. Jahr`. Nothing lost, but the units are no longer the words as written, and `evidence` says `verbatim`. Name it on the reference page in Task 6.
4. **An unescaped `<` in HTML text swallows text** — `<p>Preis <100 Euro und a<b, x > y</p>` → `Preis <100 Euro und a y`. Malformed HTML: name it.
5. **A subject folded with a tab instead of a space is another subject** — `Subject: … Montag\r\n\tund …` decodes to `Montag\tund`, so another hash than the copy folded with a space (`57511c38…` vs `edaa7a6c…`). By RFC 5322 the unfolded value keeps the WSP, so this is only real if a transport refolds and swaps the whitespace character. Name it.
6. **The decoded bytes of an 8bit body carry their line endings** — the same mail stored with LF hashes differently from its CRLF copy (`819b26dd…` vs `edaa7a6c…`). IMAP delivers CRLF, so Task 4 is unaffected; it matters the day a connector reads `.eml` or mbox files. Name it in the reference page's statement of the identity rule.
7. **Malformed address lists lose or invent identities** — `To: a@example.org; b@example.org` (semicolon) gives only `a`; `Cc: Huber, Eva <eva@…>` (unquoted comma) gives a bogus identity `Huber`; `From: eva@example.org (Eva Huber)` gives no name. All three stay intact in `headers`. Name it.
8. **Opaque S/MIME signed mail** (`application/pkcs7-mime; smime-type=signed-data`) has its text inside the p7m and says "no readable body: attachments only". §3.5 "signiert: der lesbare Teil" assumes `multipart/signed`. Rare; name it.
9. **No test holds §3.3 "independent of transport" for the body's transfer encoding** — an MTA's 8BITMIME downgrade (8bit → quoted-printable) is ordinary. I measured that it holds; a test with `plain` re-encoded as QP and base64 would keep it.
10. **Comments not quite true:**
    - `mail.py:58-61` `MAX_FORWARD_DEPTH`: "a mail attached at depth 5 stays an attachment" — the mail at depth 5 is unpacked; the one attached *to* it (depth 6) stays. Say "a mail attached to the mail at depth 5".
    - `mail.py:103-105` `Attachment`: "with its bytes as they stand" — a base64- or QP-encoded `message/rfc822` is decoded first (`_message_bytes`).
    - `mail.py:247-248` `_readable`: "in a display name or a file name" — it is applied to every header value, the subject included (line 324), and that is where the measured `Gr��e` comes from.
    - `mail.py:590-591` "Compared without the final line ending" — `_agree` (`mail.py:639`) strips every trailing CR and LF, not one line ending. Harmless, but the claim is narrower than the code.
11. **Spec observation, not a code defect:** a mail without a Message-ID is keyed by subject, body and attachments only. Daily identical notifications without a Message-ID ("Backup OK") collapse into one event, the later ones "known". §3.5 decides it so; the landkarte may want the point.
12. Already named by the implementer and confirmed: a charset whose codec refuses `errors="replace"` (`charset=idna`) raises `UnicodeError` from `_decode`; `charset=rot13` is read as Latin-1. Hostile only — T2-b will catch it.

### Rulings T2-b and T2-c

**T2-b — sound,** with three refinements the fix round should write down:

- **Per mail, not per sighting.** An inner mail that does not map must not turn the outer one into "unreadable mail"; the outer keeps its event and the inner gets the fallback with `forwarded_in`. And when the outer fails, its inner mails are not reached, which is acceptable because the raw blob holds them.
- **A naive `internaldate` still raises.** It is a caller error, not mail content, and the fallback itself needs a zoned `internaldate`. A blanket `except Exception` around `_map` would otherwise turn a programming error into an "unreadable mail" event.
- **The unit names the class only, never the message.** An exception message can quote header content (the UTF-7 case quotes the surrogate). The ruling already says "Klasse des Fehlers"; the test should hold it.

The key `sha256:<SHA-256 of the raw bytes>` shares the `sha256:` prefix with mails without a Message-ID, whose suffix is the SHA-256 of a canonical form; the preimages differ, so they do not collide. Two copies of one unreadable mail with different `Received` lines become two events — the ruling's "Wenn falsch" covers that direction.

**T2-c — sound in direction, and too narrow in two places:**

- **cp1252, not Latin-1, as the second reading** — for the reason in Important 3: Latin-1 turns €, „“ and – into invisible C1 characters. Strict UTF-8 first, then cp1252, then Latin-1 for the five undefined bytes.
- **Not only for an undeclared charset.** The same guess is right for a declared `us-ascii` (or `ansi_x3.4-1968`) with bytes above 127 — measured with UTF-8 bytes under `charset=us-ascii`: `f��r M��ller` today — and for an unknown label: `unknown-8bit`, which Python's own `email` and mutt write, carries UTF-8 in practice and is read today as Latin-1 mojibake (`fÃ¼r`). For an unknown label this changes §3.5 ("als Latin-1 gelesen"), so it needs a word in the spec or the ruling.
- **Keep `replaced` meaning "a character was replaced"** and record the guess separately inside `body` (say, the declared charset beside the one read with). Otherwise a mail whose undeclared bytes are clean UTF-8 says `replaced: true` although nothing was replaced, and `body.charset` alone cannot tell a declared `utf-8` from a guessed one. That keeps the payload's top-level names as the global constraints list them.

The broken-MIME mails (`broken_mime`, `broken_mime_no_boundary`) read their multipart body with no charset, so T2-c recovers their `ä` too.

### Assessment

**Needs fixes.** 0 Critical, 3 Important, 12 Minor.

The three Important findings are all one kind — text an ordinary mail carries, absent from the units with nothing saying so — and they are the costliest defect the brief names. Important 3 and ruling T2-c share one fix (the second reading is cp1252). Important 1 and 2 touch the wording of §3.2 ("der Teil `text/plain`, wenn es einen gibt") and, for 1, §3.3's "the chosen body part"; they want a ruling before the fix round.
