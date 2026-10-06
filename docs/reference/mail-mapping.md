(mail-mapping)=

# Mail mapping

`previously.core.mail.map_mail` maps the raw bytes of one mail onto an event, its attachments, and the mails attached to it.
`previously.core.ingest.ingest` stores the raw mail and every attachment as a blob and appends the events.
`previously ingest imap` is the command that runs both; see {ref}`cli-reference`.
For why a mail maps this way, see {ref}`connectors`.

The mapping reads the mail with the standard library's `email` package and its default policy.
It uses no network and no database.

## The event

| Field | Value |
|---|---|
| `source` | `email`, whatever the mailbox or the folder. |
| `external_id` | The `Message-ID` header without its angle brackets and without the blanks around them. A mail without a `Message-ID`, or with an empty one, has `sha256:` and the artifact hash in hexadecimal. |
| `occurred_at` | The `Date` header, when it reads as a moment with a time zone. Otherwise the server's arrival time, `INTERNALDATE`. A `Date` with the zone `-0000` names no zone and falls back too. |
| `evidence` | `verbatim`. |
| `units` | See *Units*. |
| `artifact_hash` | See *Artifact identity*. |
| `channel_identities` | See *Channel identities*. |
| `blobs` | The raw mail first, then every attachment; see *Blobs*. |
| `payload` | See *Payload*. |

## Units

Unit 1 is the subject, from the first `Subject` header, decoded, unfolded and stripped of the blanks around it.
An absent or blank subject gives no unit.
The text of every body part follows, joined by blank lines and split into paragraphs by `split_plaintext`, quotes and signatures included.

A mail whose body holds no text has one unit in place of the body, with one of three sentences:

```text
no readable body: encrypted
no readable body: attachments only
no readable body: empty
```

`encrypted` stands for a mail with a `multipart/encrypted` part, or with an `application/pkcs7-mime` or `application/x-pkcs7-mime` part whose `smime-type` is `enveloped-data` or `authenveloped-data`.
`attachments only` stands for a mail with at least one attachment, and `empty` for one without.

### Body parts

The body is every text part of the content, in the order of the mail:

- A part `text/*` is body when it carries no file name, neither `filename=` nor `name=`, and no `Content-Disposition: attachment`.
  A part with a file name is an attachment, also as `text/plain`.
- A `multipart/mixed`, or any other multipart but the two below, contributes the body parts of each of its parts, in order.
- A `multipart/alternative` contributes one of its forms: `text/plain` before `text/html` before any other.
  A form whose text is empty or blank gives way to the next.
  The `text/plain` and `text/html` parts of the other forms are no body and no attachment; every other part of them is an attachment.
- A `multipart/related` contributes the body of the part its `start` parameter names, or of its first part.
- A multipart whose boundary is missing, or never found, is one body part, with its MIME lines in the text.
- A mail attached as `message/rfc822` contributes nothing to the body of the mail it's attached to.

### Character sets

| The part declares | Read as | `guessed` |
|---|---|---|
| `iso-8859-1`, `latin1` or another name of ISO-8859-1, or `windows-1252` | Windows-1252, with the five bytes Windows-1252 leaves undefined read as ISO-8859-1. | `false` |
| No character set, and only bytes up to 127 | `us-ascii`. | `false` |
| `us-ascii`, and only bytes up to 127 | `us-ascii`. | `false` |
| No character set, or `us-ascii`, with a byte above 127 | UTF-8 if the bytes are valid UTF-8, otherwise Windows-1252. | `true` |
| A name Python doesn't know, such as `unknown-8bit` | UTF-8 if the bytes are valid UTF-8, otherwise Windows-1252. | `true` |
| Any other name Python knows | That character set; a byte sequence it can't read becomes U+FFFD. | `false` |

A lone UTF-16 surrogate and a null byte become U+FFFD as well, because PostgreSQL stores neither.
A body part in which a character was replaced carries `"replaced": true`.

### Text from markup

A `text/html` part is turned into text by `html2text` 2025.4.15, with these settings:

| Setting | Value | Effect |
|---|---|---|
| `body_width` | `0` | No line is wrapped. |
| `ignore_images` | `True` | An image leaves nothing in the text, its alternative text included. |
| `unicode_snob` | `True` | An entity such as `&uuml;` becomes its character, `ü`. |

The result is Markdown, and `split_plaintext` splits it at blank lines:

| HTML | Text |
|---|---|
| `<br>` | Two blanks and a line break. |
| `<b>` and `<strong>` | `**` around the text. |
| `<i>` and `<em>` | `_` around the text. |
| `<a href="https://example.org/x">Link</a>` | `[Link](https://example.org/x)`. |
| `<blockquote>` | `> ` in front of each line. |
| A table | A Markdown table, its cells separated by vertical bars. |
| A character that would start Markdown, such as the period in `1. Punkt` at the start of a line | Escaped, such as `1\. Punkt`. |
| A `<` that opens no tag, such as in `a<b and c>d` | The text up to the next `>` is read as a tag and dropped: `a**d`. |

The payload names the converter and its version for each part it converted, as `html2text 2025.4.15`.

## Artifact identity

The artifact hash is the SHA-256 of the canonical form of this document, computed by `previously.core.identity.artifact_hash_of`:

```json
{"subject": "Angebot für den Relaunch",
 "body": ["<SHA-256 of each body part, in order>"],
 "attachments": ["<SHA-256 of each attachment, sorted>"]}
```

| Key | Value |
|---|---|
| `subject` | The value of the first `Subject` header as `headers` holds it, decoded and unfolded; `null` when there's none, `""` when it's empty. |
| `body` | For each body part, in order, the SHA-256 in hexadecimal of its bytes after the transfer encoding is undone and before they're read as text, with every line ending as LF. |
| `attachments` | For each attachment, the SHA-256 in hexadecimal of its bytes after the transfer encoding is undone, sorted. Bytes that travelled as lines, without a transfer encoding or with `7bit`, `8bit` or `quoted-printable`, enter with every line ending as LF; bytes in `base64` or `binary` enter as they are. |

Two mails with the same subject, the same body parts and the same attachments have the same artifact hash, whatever their other headers.
A copy whose line endings are LF where the server's are CRLF, such as a mail saved as an `.eml` file, has the same artifact hash too.
A mail with another subject, another body part or another attachment has another one.
No setting of the converter and no guess at a character set enters the hash.

## Channel identities

Every address of the headers `From`, `Sender`, `Reply-To`, `To`, `Cc` and `Bcc`, in the order the headers stand in the mail, as one entry each:

| Key | Value |
|---|---|
| `channel` | `email`. |
| `role` | `from`, `sender`, `reply_to`, `to`, `cc` or `bcc`. |
| `address` | The address as the parser reads it out of the header, not converted to lowercase and not merged with another spelling; `<>` stays `<>`. |
| `name` | The display name, or `null` where the address carries none. |

A group contributes its members, an empty group nothing.
An address list the parser can't read in full contributes the addresses it reads.

## Blobs

The first blob is the raw mail, with the media type `message/rfc822` and no file name.
Every attachment follows, in the order of the mail, with the media type of its part and its file name.

An attachment is every part of the mail other than a multipart, the text of the body, and the plain or HTML text of a form `multipart/alternative` didn't choose.
That includes an inline image, a calendar invitation, a signature, and the parts of an encrypted mail.

| The file name in the mail | The name in the blob reference |
|---|---|
| Absent | None. |
| `""`, `.` or `..` | None. |
| A name with `/`, such as `Angebot 10/2026.pdf` | Each `/` as `_`: `Angebot 10_2026.pdf`. |
| Any other name | The name, decoded. |

The raw mail keeps the name as the mail wrote it.

## Payload

The mapping and the run write these keys:

| Key | Present | Value |
|---|---|---|
| `headers` | Always, except for a mail that doesn't map. | Every header as a pair `[name, value]`, in the order of the mail and duplicates included; the name as written, the value unfolded, every folding as one blank, and with encoded words decoded. A byte above 127 in a header reads as UTF-8 if it's valid UTF-8, otherwise as Windows-1252. |
| `headers_replaced` | When a character was replaced in a header. | The names of the headers in which a character became U+FFFD. |
| `raw` | Always. | The address of the raw mail, the first blob. |
| `date_source` | Always. | `header` or `internaldate`: where `occurred_at` comes from. |
| `internaldate` | Always. | The server's arrival time, in ISO 8601 in UTC, such as `2026-10-06T13:34:36.000000Z`. |
| `found_in` | Always. | Where this sighting lay: for IMAP, `connector`, the name of the connector's watermark, and `uidvalidity` and `uid`, as text. |
| `body` | Always, except for a mail that doesn't map. | One entry for each body part; see the table below. An empty list for a mail without a body part. |
| `not_unpacked` | On a mail at depth 5 with a mail attached. | The address of each mail attached to it, which stays an attachment and isn't mapped. |
| `variant_of` | On a variant. | The Message-ID under which the log holds another content. |
| `forwarded_in` | On a mail out of an attachment. | The `external_id` of the mail it was attached to, as that mail went into the log. |

Each entry of `body`:

| Key | Value |
|---|---|
| `part` | The media type of the part, such as `text/plain`. |
| `charset` | The character set the part was read with. |
| `declared` | The character set the part declares, in lowercase, or `null`. |
| `guessed` | `true` when the character set was guessed. |
| `converter` | `html2text 2025.4.15` for a part converted from HTML, otherwise `null`. |
| `replaced` | `true` when a character of the part became U+FFFD. |

`append` adds `evidence`, `blobs`, `artifact_hash` and `channel_identities`; see {ref}`artifact-identity`.
The text of the body stands in the units alone and nowhere in the payload.
The subject stands in unit 1 and in `headers`.

## A mail inside a mail

A part `message/rfc822` is an attachment of the mail it's in, and the mail it holds maps as well, as an event of its own:

- Its raw mail is its bytes as they stand in the attachment, with a transfer encoding undone where a client wrote one.
  That's the same blob as the attachment.
- It has its own `Message-ID`, `Date`, addresses, units and attachments, and the same `internaldate` and `found_in` as the mail it's in.
- Its payload carries `forwarded_in`.
- A mail inside it maps the same way, down to depth 5, counting the mail in the folder as depth 0.
  A mail attached to the mail at depth 5 stays an attachment, and the mail at depth 5 lists it under `not_unpacked`.

A mail and every mail inside it go into one batch of `append`.
A mail that, together with the mails inside it at every depth, makes more than 500 events is refused at every run:

```text
Error: 501 events in one transaction, 500 are allowed — larger batches starve against small submissions
```

A forward written as quoted text into the body, under a line such as `---------- Forwarded message ----------`, stays text of the mail it's in.

## A mail that doesn't map

A mail on which the parser or the mapping raises an exception becomes an event of what's safe to say about it, and the run goes on:

| Field | Value |
|---|---|
| `external_id` | `sha256:` and the SHA-256 of the raw bytes. |
| `occurred_at` | The server's arrival time. |
| `artifact_hash` | The SHA-256 of the raw bytes. |
| `units` | One unit, `unreadable mail: ` and the class of the error. |
| `blobs` | The raw mail. |
| `payload` | `date_source`, which is `internaldate`, `internaldate`, `found_in`, `raw`, and `forwarded_in` for a mail out of an attachment. |

The unit names the class of the error and never its message, which can quote a header, as in this one:

```text
unreadable mail: UnicodeEncodeError
```

A mail attached to another that doesn't map becomes such an event on its own, and the mail it's attached to maps as usual.
A part that declares a character set Python knows as an encoding of bytes and not of text, such as `charset=base64`, makes the whole mail one that doesn't map.

## Cases

| Case | Result |
|---|---|
| The same Message-ID and the same artifact hash as an event in the log or earlier in the run, such as two copies of a mail with other `Received` headers | Known: no event, no blob stored. |
| The same Message-ID and another artifact hash | A variant: an event under `<Message-ID>#<the first 16 hexadecimal characters of its artifact hash>`, with `variant_of`. `ingest imap` names it on standard error. |
| The variant key held with yet another artifact hash, which takes two artifact hashes that share their first 64 bits | The run stops with `ArtifactChanged`, and the batch it was gathering isn't written. |
| An event under the key that has been erased | Known: no event, no blob stored. |
| No Message-ID | The key `sha256:<artifact hash>`. Two mails without a Message-ID and with the same subject, body and attachments, such as a daily `Backup OK`, are one event. |
| No `Date`, or one that doesn't read as a moment with a zone | `occurred_at` is `INTERNALDATE`, and `date_source` is `internaldate`. |
| HTML only | Converted; see *HTML*. |
| Signed, as `multipart/signed` | The signed text is the body; the signature is an attachment. |
| Signed opaquely, as `application/pkcs7-mime` with `smime-type=signed-data` | No body: `no readable body: attachments only`, with the signed content as an attachment. |
| Encrypted | `no readable body: encrypted`; nothing is decrypted, and the encrypted parts are attachments. |
| A bounce with a part `text/rfc822-headers` | That part is body text. |
