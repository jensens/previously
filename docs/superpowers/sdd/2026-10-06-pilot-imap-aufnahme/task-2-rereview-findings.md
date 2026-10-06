# Task 2, fix round 1 — what the re-review verdicts

The previous review is `task-2-review.md` in this directory; its three Important findings are the first three items.
The controller's rulings (in German, in `progress.md`, lines starting `Ruling T2-`) decide what the fix had to do; they are summarised here in English.

1. **Important 1 — only the first `text/plain` part became the body.**
   Apple Mail with a PDF between two paragraphs lost the second paragraph into an unnamed blob; an HTML-only mail with an inline `.txt` took the `.txt` as body.
   Ruling T2-d: the body is every text part of the content, in order — a `text/*` part with no file name (`filename=` or `name=`) and no `Content-Disposition: attachment`; in `multipart/alternative` the preferred form, where an empty or whitespace-only `text/plain` gives way to `text/html`.
   A part with a file name is an attachment even as `text/plain`.
   Identity (§3.3) is computed over the decoded bytes of the chosen parts, in order, line endings normalized.
2. **Important 2 — empty `text/plain` beside full HTML gave "no readable body: empty".**
   Same ruling T2-d.
3. **Important 3 — `charset=iso-8859-1` with Windows-1252 bytes became invisible C1 characters, `replaced` wrong.**
   Ruling T2-e: a declared `iso-8859-1`/`latin1` reads as cp1252 (WHATWG); undeclared, `us-ascii` with bytes above 127, or an unknown label: strict UTF-8 first, else cp1252 (Latin-1 only for its five undefined bytes); a separate `guessed` note in `body`; `replaced` means only "a character was replaced".
4. **Implementer concern / ruling T2-b with T2-f — `map_mail` raised on broken mail content, which would halt every later run at that mail.**
   `map_mail` never raises on mail content. A mail that cannot be mapped becomes an event from what is certain: `source = email`, `external_id = sha256:<SHA-256 of the raw bytes>`, `occurred_at` from `internaldate`, one unit `unreadable mail: <exception class>` (class only, never the message — it can quote headers), the raw mail as a blob, `artifact_hash` = SHA-256 of the raw bytes.
   Per mail: an inner mail that fails does not sink the outer one.
   A naive `internaldate` still raises (caller's error).
5. **Ruling T2-g — the minors that ride along:**
   a replacement in the subject is noted (`headers_replaced`); a subject folded with a tab gives the same hash as one folded with a space; a test holds identity across transfer encodings (8bit, QP, base64); the four untrue comments the review named are corrected.
   Named, not fixed (do not report these as open): alt text of images dropped; html2text Markdown escapes; an unescaped `<` swallowing text; malformed address lists; opaque-signed S/MIME reads as "attachments only"; identical mails without Message-ID merge.

## Extensions the implementer made and the controller accepted (ruling T2-h)

- Attachments that travel as lines (no CTE, 7bit, 8bit, quoted-printable, including an attached `message/rfc822`) enter the identity with LF line endings; base64/binary attachments enter unchanged, so their digest stays their blob address.
- `headers` values are unfolded (folding whitespace as one space) for every header.

Check these for correctness too, not for whether they should exist.

## Working rule for this review

A finding that only arises from misuse or typos, or from deliberately malformed mail beyond what real mail software produces, is **named** (one line, Minor, "name") — not a reason for another fix round.
Defects that ordinary mail from ordinary clients (Outlook, Apple Mail, Gmail, Thunderbird, mailing lists, automated senders) would hit are findings.
The question for each new finding: would the pilot customer's real inbox plausibly contain this?
