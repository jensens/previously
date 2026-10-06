# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""A mail as an event ({ref}`artifact-identity`).

`map_mail` takes the raw bytes of one mail and gives back the event, the
attachments, and the mails attached to it, each mapped the same way. It is
pure: no network, no database, no clock — where the mail names no usable
time, the fallback is the server's arrival time handed in, not "now".

The identity of a mail is a rule of this project and not of a library: the
SHA-256 of the canonical form of the decoded subject, the SHA-256 of each
body part's bytes after the transfer encoding and before any conversion into
text, and the sorted SHA-256 of every attachment. Line endings enter as LF
wherever the bytes are text a transport may rewrite. Nothing else of the
transport goes in, so two copies from two mailboxes, or an `.eml` file saved
on a Unix machine, are one artifact; nothing of the conversion goes in, so a
better converter or a better guess at a charset does not turn every sighting
into a variant. That is why this module takes the mail apart with the
standard library's `email` and decides itself what is decoded.

What it does not do is interpret. Quotes and signatures stay in the text,
addresses stay as written, nothing is decrypted.
"""

from dataclasses import dataclass
from email.generator import BytesGenerator
from email.headerregistry import AddressHeader
from email.headerregistry import DateHeader
from email.headerregistry import HeaderRegistry
from email.message import EmailMessage
from previously.contract.types import ChannelIdentity
from previously.contract.types import Evidence
from previously.contract.types import RawEvent
from previously.contract.types import RawUnit
from previously.core.hashing import iso_utc
from previously.core.identity import artifact_hash_of
from previously.core.units import split_plaintext
from typing import cast
from typing import TYPE_CHECKING

import base64
import binascii
import codecs
import email
import email.policy
import hashlib
import html2text
import io
import quopri
import re


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterator
    from collections.abc import Mapping
    from datetime import datetime


MAX_FORWARD_DEPTH = 5
"""How deep mails inside mails are unpacked. The outer mail is depth 0, and
the mails attached to it down to depth 5 are unpacked. A mail attached to the
mail at depth 5 stays an attachment, and the payload of the mail at depth 5
lists it under `not_unpacked`. The limit guards against a broken or hostile
mail, not against real mail."""

SOURCE = "email"

# The one unit of a mail without a readable body, so that no mail is
# without a unit. Fixed English sentences: they say why, and they are what
# the reference page quotes.
NO_BODY_ENCRYPTED = "no readable body: encrypted"
NO_BODY_ATTACHMENTS_ONLY = "no readable body: attachments only"
NO_BODY_EMPTY = "no readable body: empty"

# The one unit of a mail that does not map, followed by the class of the
# error — never its message, which can quote a header.
UNREADABLE_MAIL = "unreadable mail: "

CONVERTER = "html2text " + ".".join(str(part) for part in html2text.__version__)
"""The converter from HTML into text and its version, as the payload names
it: a unit converted by another version may read differently."""

_POLICY = email.policy.default

# Every header as unstructured text: unfolded and with encoded words
# decoded, otherwise as written. The default registry would render a
# structured header anew — `"Office" <office@example.org>` loses its quotes,
# `charset=utf-8` gains some — and the payload is meant to show the header
# as the mail has it.
_UNSTRUCTURED = HeaderRegistry(use_default_map=False)

_ROLES = {
    "from": "from",
    "sender": "sender",
    "reply-to": "reply_to",
    "to": "to",
    "cc": "cc",
    "bcc": "bcc",
}

# A line break and the blanks that follow it: the folding of a header. It
# unfolds into one space, so that a header folded with a tab and the same
# header folded with a space are one value.
_FOLD = re.compile(r"(?:\r\n|\r|\n)[ \t]*")
_SURROGATE = re.compile("[\ud800-\udfff]")
# What the parser makes out of a byte it could not read: a surrogate from
# U+DC80 to U+DCFF, which `surrogateescape` turns back into the byte.
_ESCAPED_BYTE = re.compile("[\udc80-\udcff]")

# The end of the header block: an empty line, or one right at the start.
_HEADER_END = re.compile(rb"(?:\A|\n)(?:\r\n|\n)")

# Transfer encodings that carry text in lines, whose line endings a
# transport or a file on disk may rewrite.
_LINE_ENCODINGS = ("", "7bit", "8bit", "quoted-printable")


@dataclass(frozen=True)
class Attachment:
    """One attachment of a mail: its decoded bytes, its name if it carries
    one, and its media type. A mail attached to a mail is an attachment too,
    with the type `message/rfc822` and its bytes as they stand in the
    attachment — after a transfer encoding is undone, where a client wrote
    one."""

    content: bytes
    filename: str | None
    media_type: str


@dataclass(frozen=True)
class Mapped:
    """A mail mapped onto an event.

    `event` carries no `blobs` and its payload no `raw`: both name blobs,
    and blobs are stored by the run that appends, not here. `raw` is the
    mail's raw bytes, the blob that comes first; `attachments` the blobs
    after it, in the order of the mail. `inner` holds the mails attached to
    this one, each mapped the same way and pointing back with
    `forwarded_in`.
    """

    event: RawEvent
    raw: bytes
    attachments: tuple[Attachment, ...]
    inner: tuple[Mapped, ...]


@dataclass(frozen=True)
class _Text:
    """One body part, read."""

    part: EmailMessage
    data: bytes
    text: str
    charset: str
    declared: str | None
    guessed: bool
    converter: str | None
    replaced: bool


def variant_key(message_id: str, artifact_hash: bytes) -> str:
    """The key of a mail that arrives under a known Message-ID with another
    content: the Message-ID, `#`, and the first sixteen hexadecimal
    characters of its artifact hash."""
    return f"{message_id}#{artifact_hash.hex()[:16]}"


def map_mail(raw: bytes, *, internaldate: datetime, found_in: Mapping[str, str]) -> Mapped:
    """The mail in `raw` as an event, with its attachments and the mails
    attached to it.

    `internaldate` is the server's arrival time and has to carry a zone;
    `found_in` says where this sighting lay. Both go into the payload, and
    every mail attached to this one is given the same two.

    Raises `InvalidPayload` for a naive `internaldate`, which is the
    caller's error, and nothing for what a mail contains: a mail that does
    not map becomes an event of what is safe to say about it (`_unreadable`),
    and so does each attached mail on its own.
    """
    return _map_or_keep(
        raw, internaldate=internaldate, found_in=found_in, depth=0, forwarded_in=None
    )


def _map_or_keep(
    raw: bytes,
    *,
    internaldate: datetime,
    found_in: Mapping[str, str],
    depth: int,
    forwarded_in: str | None,
) -> Mapped:
    # Before the `try`: a naive `internaldate` is no content of the mail,
    # and the event of a mail that does not map needs a zoned one too.
    iso_utc(internaldate)
    try:
        return _map(
            raw,
            internaldate=internaldate,
            found_in=found_in,
            depth=depth,
            forwarded_in=forwarded_in,
        )
    # Every exception, deliberately: a mail is input from anybody, and the
    # standard library raises on some of it — `UnicodeEncodeError` for a
    # UTF-7 encoded word that decodes to a lone surrogate, measured on
    # 2026-10-06 with Python 3.14.3. A run that stopped at one mail would
    # stop there at every run after it, and take in nothing more.
    except Exception as error:
        return _unreadable(
            raw, error, internaldate=internaldate, found_in=found_in, forwarded_in=forwarded_in
        )


def _unreadable(
    raw: bytes,
    error: Exception,
    *,
    internaldate: datetime,
    found_in: Mapping[str, str],
    forwarded_in: str | None,
) -> Mapped:
    """The event of a mail that does not map, from what is safe: the raw
    bytes as its identity and its key, the arrival time, and one unit naming
    the class of the error. The raw mail stays a blob, so a better parser can
    read it later; the event can be erased and the mail taken in again."""
    digest = hashlib.sha256(raw).digest()
    payload: dict[str, object] = {
        "date_source": "internaldate",
        "internaldate": iso_utc(internaldate),
        "found_in": dict(found_in),
    }
    if forwarded_in is not None:
        payload["forwarded_in"] = forwarded_in
    event = RawEvent(
        source=SOURCE,
        external_id="sha256:" + digest.hex(),
        occurred_at=internaldate,
        evidence=Evidence.VERBATIM,
        units=(RawUnit(seq=1, content=UNREADABLE_MAIL + type(error).__name__),),
        payload=payload,
        artifact_hash=digest,
    )
    return Mapped(event=event, raw=raw, attachments=(), inner=())


def _map(
    raw: bytes,
    *,
    internaldate: datetime,
    found_in: Mapping[str, str],
    depth: int,
    forwarded_in: str | None,
) -> Mapped:
    message = email.message_from_bytes(raw, policy=_POLICY)
    headers, headers_replaced = _headers(message)
    subject = _first(headers, "subject")
    read = _reader()
    body_parts, alternatives = _body_parts(message, read)
    texts = [read(part) for part in body_parts]
    leaves = _attachment_parts(message, [*body_parts, *alternatives])
    sliced = _sliced(message, raw)
    attachments = tuple(_attachment(part, sliced, raw) for part in leaves)

    # The subject as the headers have it, decoded, unfolded and with a null
    # byte already replaced: the canonical form refuses one. A subject that
    # is absent is `null`, one that is empty is `""`.
    artifact_hash = artifact_hash_of(
        {
            "subject": subject,
            "body": [_sha256(_lf(text.data)) for text in texts],
            "attachments": sorted(
                _identity_digest(part, attachment)
                for part, attachment in zip(leaves, attachments, strict=True)
            ),
        }
    )
    external_id = _message_id(headers) or "sha256:" + artifact_hash.hex()
    occurred_at, date_source = _occurred_at(message, internaldate)

    payload: dict[str, object] = {
        "headers": [[name, value] for name, value in headers],
        "date_source": date_source,
        "internaldate": iso_utc(internaldate),
        "found_in": dict(found_in),
        "body": [
            {
                "part": text.part.get_content_type(),
                "charset": text.charset,
                "declared": text.declared,
                "guessed": text.guessed,
                "converter": text.converter,
                "replaced": text.replaced,
            }
            for text in texts
        ],
    }
    if headers_replaced:
        payload["headers_replaced"] = headers_replaced
    if forwarded_in is not None:
        payload["forwarded_in"] = forwarded_in

    inner: list[Mapped] = []
    not_unpacked: list[str] = []
    for attachment in attachments:
        if attachment.media_type != "message/rfc822":
            continue
        if depth < MAX_FORWARD_DEPTH:
            inner.append(
                _map_or_keep(
                    attachment.content,
                    internaldate=internaldate,
                    found_in=found_in,
                    depth=depth + 1,
                    forwarded_in=external_id,
                )
            )
        else:
            not_unpacked.append(_sha256(attachment.content))
    if not_unpacked:
        payload["not_unpacked"] = not_unpacked

    event = RawEvent(
        source=SOURCE,
        external_id=external_id,
        occurred_at=occurred_at,
        evidence=Evidence.VERBATIM,
        units=_units(subject, texts, _no_body_reason(message, attachments)),
        payload=payload,
        artifact_hash=artifact_hash,
        channel_identities=_channel_identities(message),
    )
    return Mapped(event=event, raw=raw, attachments=attachments, inner=tuple(inner))


# --- text --------------------------------------------------------------------


def _readable(text: str) -> tuple[str, bool]:
    """`text` with what the log cannot hold replaced by U+FFFD, and whether
    anything was: a lone surrogate — what is left of a byte nothing could
    read, or what a UTF-7 body decodes to — and a null byte. PostgreSQL
    stores neither, in `text` or in `jsonb`."""
    replaced = False
    if _SURROGATE.search(text):
        text, replaced = _SURROGATE.sub("\ufffd", text), True
    if "\x00" in text:
        text, replaced = text.replace("\x00", "\ufffd"), True
    return text, replaced


def _windows_1252(data: bytes) -> str:
    """`data` as Windows-1252, and the five bytes it leaves undefined (0x81,
    0x8D, 0x8F, 0x90, 0x9D) as Latin-1, so that every byte reads as some
    character."""
    text = data.decode("cp1252", "surrogateescape")
    return _ESCAPED_BYTE.sub(lambda match: chr(ord(match.group()) - 0xDC00), text)


def _guess(data: bytes) -> tuple[str, str]:
    """Bytes whose charset nobody said or nobody knows: strict UTF-8 if they
    are UTF-8 — no other charset in use produces valid UTF-8 by accident
    beyond a few letters —, otherwise Windows-1252."""
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return _windows_1252(data), "windows-1252"


def _decode(data: bytes, declared: str | None) -> tuple[str, str, bool, bool]:
    """`data` as text: the text, the charset it was read with, whether that
    charset is a guess, and whether a character was replaced.

    - A label of ISO-8859-1 is read as Windows-1252, as the WHATWG Encoding
      Standard, every browser and Thunderbird do: Windows clients and PHP
      mailers write Windows-1252 under that label, and ISO-8859-1 has only
      invisible control characters where Windows-1252 has „“, – and €.
    - Without a label, under a label of US-ASCII when a byte is above 127,
      and under a label Python does not know (`unknown-8bit`, which
      Python's own `email` and mutt write), the charset is guessed.
    - Under any other label the text is read as declared, and what does not
      read becomes U+FFFD.
    """
    try:
        codec = None if declared is None else codecs.lookup(declared).name
    except LookupError:
        codec = None
    if codec in ("iso8859-1", "cp1252"):
        text, charset, guessed, replaced = _windows_1252(data), "windows-1252", False, False
    elif codec not in (None, "ascii"):
        charset, guessed = cast("str", declared), False
        try:
            text, replaced = data.decode(charset), False
        except UnicodeDecodeError:
            text, replaced = data.decode(charset, "replace"), True
    elif data.isascii() and (declared is None or codec == "ascii"):
        text, charset, guessed, replaced = data.decode("ascii"), "us-ascii", False, False
    else:
        (text, charset), guessed, replaced = _guess(data), True, False
    text, nul = _readable(text)
    return text, charset, guessed, replaced or nul


def _html_to_text(html: str) -> str:
    """HTML mechanically turned into text, paragraphs into blank lines.

    `unicode_snob` is not cosmetic. Without it html2text writes an entity
    such as `&uuml;` as the ASCII `u`, so that "für" becomes "fur" —
    measured on 2026-10-06 with version 2025.4.15. `ignore_images` keeps the
    addresses of tracking pixels out of the text; links stay. `body_width`
    0 wraps no line.
    """
    converter = html2text.HTML2Text()
    converter.body_width = 0
    converter.ignore_images = True
    converter.unicode_snob = True
    return converter.handle(html)


def _lf(data: bytes) -> bytes:
    """Every line ending as LF, for the identity of bytes that are text."""
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


# --- headers -----------------------------------------------------------------


def _unfolded(value: object) -> str:
    return _FOLD.sub(" ", str(value))


def _recovered(text: str) -> str:
    """A header byte outside ASCII arrives from the parser as an escaped
    byte — raw in the header, or out of an encoded word labelled
    `unknown-8bit`, which is how the standard library writes such a header
    back out. It is read as UTF-8 if the bytes are UTF-8, which RFC 6532
    allows in a header, and as Windows-1252 otherwise — what an old mailer
    writes."""
    if not _ESCAPED_BYTE.search(text):
        return text
    # A lone surrogate beside the escaped bytes, which no byte made, does
    # not encode: the mail then does not map, and becomes the event of an
    # unreadable mail.
    return _guess(text.encode("utf-8", "surrogateescape"))[0]


def _headers(message: EmailMessage) -> tuple[list[tuple[str, str]], list[str]]:
    """Every header in the order of the mail, duplicates included, the name
    as written, the value unfolded and with encoded words decoded; and the
    names of the headers in which a character was replaced.

    A replacement shows as U+FFFD in the decoded value that was not in the
    source: the decoder replaces what an encoded word's charset cannot read,
    and records no defect for it (measured on 2026-10-06 with an encoded
    word labelled UTF-8 that holds Latin-1).
    """
    headers: list[tuple[str, str]] = []
    replaced_in: list[str] = []
    for name, value in message.raw_items():
        source = _recovered(_unfolded(value))
        text, replaced = _readable(str(_UNSTRUCTURED(name, source)))
        if replaced or ("\ufffd" in text and "\ufffd" not in source):
            replaced_in.append(name)
        headers.append((name, text))
    return headers, replaced_in


def _first(headers: list[tuple[str, str]], name: str) -> str | None:
    return next((value for key, value in headers if key.lower() == name), None)


def _message_id(headers: list[tuple[str, str]]) -> str | None:
    """The Message-ID without its angle brackets and the blanks around
    them, or `None` when there is none to speak of."""
    value = _first(headers, "message-id")
    if value is None:
        return None
    value = value.strip().removeprefix("<").removesuffix(">").strip()
    return value or None


def _occurred_at(message: EmailMessage, internaldate: datetime) -> tuple[datetime, str]:
    """The `Date` header when it reads as a moment with a zone, otherwise
    the server's arrival time. `-0000` is a time without a zone (RFC 5322),
    and Python reads it as a naive datetime: that falls back too, because
    the log cannot order a moment it does not know the zone of."""
    header: object = message.get("date")
    if isinstance(header, DateHeader):
        moment = header.datetime
        if moment is not None and moment.utcoffset() is not None:
            return moment, "header"
    return internaldate, "internaldate"


def _channel_identities(message: EmailMessage) -> tuple[ChannelIdentity, ...]:
    """Every address of `From`, `Sender`, `Reply-To`, `To`, `Cc` and `Bcc`,
    in the order the headers stand in. A group contributes its members, an
    empty group nothing. The address is what the parser reads out of the
    header, not lower-cased and not merged with another spelling — even
    `<>` stays `<>`."""
    identities: list[ChannelIdentity] = []
    for name, value in message.raw_items():
        role = _ROLES.get(name.lower())
        if role is None:
            continue
        header = _POLICY.header_fetch_parse(name, _recovered(_unfolded(value)))
        if isinstance(header, AddressHeader):
            identities.extend(
                ChannelIdentity(
                    SOURCE,
                    role,
                    _readable(_recovered(address.addr_spec))[0],
                    _readable(_recovered(address.display_name))[0] or None,
                )
                for address in header.addresses
            )
    return tuple(identities)


# --- parts -------------------------------------------------------------------


def _children(part: EmailMessage) -> list[EmailMessage]:
    """The parts of a multipart. A mail inside a mail has none here: it is
    an attachment, and it gets mapped on its own. A multipart whose parts
    could not be found has none either — its payload is the text."""
    payload: object = part.get_payload()
    if part.get_content_maintype() != "multipart" or not isinstance(payload, list):
        return []
    return cast("list[EmailMessage]", payload)


def _walk(part: EmailMessage) -> Iterator[EmailMessage]:
    yield part
    for child in _children(part):
        yield from _walk(child)


def _is_leaf(part: EmailMessage) -> bool:
    return part.get_content_maintype() != "multipart" or not _children(part)


def _unsplit(part: EmailMessage) -> bool:
    """A multipart whose parts the parser could not find — its boundary
    missing, or never found. Its payload is the text: the MIME lines stand
    in it, and so does every word of the mail."""
    return part.get_content_maintype() == "multipart" and isinstance(part.get_payload(), str)


def _reader() -> Callable[[EmailMessage], _Text]:
    """Reads a body part once, however often the choice of the body asks."""
    seen: dict[int, _Text] = {}

    def read(part: EmailMessage) -> _Text:
        if id(part) not in seen:
            data = _decoded(part)
            declared = part.get_content_charset()
            text, charset, guessed, replaced = _decode(data, declared)
            converter = None
            if part.get_content_type() == "text/html":
                text, converter = _html_to_text(text), CONVERTER
            seen[id(part)] = _Text(
                part, data, text, charset, declared, guessed, converter, replaced
            )
        return seen[id(part)]

    return read


def _body_parts(
    message: EmailMessage, read: Callable[[EmailMessage], _Text]
) -> tuple[list[EmailMessage], list[EmailMessage]]:
    """The body of a mail is every text part of its content, in order — a
    `text/*` part without a file name and not marked as an attachment —,
    and the second list the text parts that are another form of it.

    Apple Mail splits a text around a PDF placed between two paragraphs, a
    mailing list appends its footer as a part of its own: each is text of
    the mail. A text part with a file name (`filename=` or `name=`) is a
    file someone attached, even as `text/plain`.
    """
    alternatives: list[EmailMessage] = []
    return _content(message, read, alternatives), alternatives


def _content(
    part: EmailMessage, read: Callable[[EmailMessage], _Text], alternatives: list[EmailMessage]
) -> list[EmailMessage]:
    if part.is_attachment() or part.get_filename() is not None:
        return []
    if part.get_content_maintype() == "text" or _unsplit(part):
        return [part]
    children = _children(part)
    if not children:
        return []
    subtype = part.get_content_subtype()
    if subtype == "alternative":
        return _alternative(children, read, alternatives)
    if subtype == "related":
        return _content(_root(part, children), read, alternatives)
    return [found for child in children for found in _content(child, read, alternatives)]


def _alternative(
    children: list[EmailMessage],
    read: Callable[[EmailMessage], _Text],
    alternatives: list[EmailMessage],
) -> list[EmailMessage]:
    """One form out of a `multipart/alternative`: plain text before HTML
    before anything else, and a form whose text is empty or blank gives way
    to the next — a generator that writes an empty `text/plain` beside the
    whole text in HTML is common enough. The plain and HTML text of the
    forms not chosen is the same text again; any other part of them is
    kept as an attachment."""
    options = [_content(child, read, alternatives) for child in children]
    ranked = sorted(
        (index for index, parts in enumerate(options) if parts),
        key=lambda index: _rank(options[index]),
    )
    chosen = next(
        (index for index in ranked if any(read(part).text.strip() for part in options[index])),
        ranked[0] if ranked else None,
    )
    for index, parts in enumerate(options):
        if index != chosen:
            alternatives.extend(
                part for part in parts if part.get_content_type() in ("text/plain", "text/html")
            )
    return [] if chosen is None else options[chosen]


def _rank(parts: list[EmailMessage]) -> int:
    types = {part.get_content_type() for part in parts}
    if types == {"text/plain"}:
        return 0
    return 1 if "text/html" in types else 2


def _root(part: EmailMessage, children: list[EmailMessage]) -> EmailMessage:
    """The part of a `multipart/related` that the others belong to: the one
    its `start` names, otherwise the first (RFC 2387)."""
    start = part.get_param("start")
    if isinstance(start, str):
        for child in children:
            if child.get("content-id") == start:
                return child
    return children[0]


def _decoded(part: EmailMessage) -> bytes:
    """The bytes of a part after its transfer encoding."""
    data: object = part.get_payload(decode=True)
    return data if isinstance(data, bytes) else b""


def _transfer_encoding(part: EmailMessage) -> str:
    return str(part.get("content-transfer-encoding") or "").strip().lower()


def _attachment_parts(message: EmailMessage, text: list[EmailMessage]) -> list[EmailMessage]:
    """Every leaf part that is not text of the mail — neither the body nor
    another form of it. An inline image, a calendar invitation beside the
    text, a signature, the parts of an encrypted mail are kept: what is not
    an attachment here is only in the raw mail."""
    return [
        part
        for part in _walk(message)
        if _is_leaf(part) and not any(part is other for other in text)
    ]


def _attachment(part: EmailMessage, sliced: dict[int, bytes], raw: bytes) -> Attachment:
    filename = part.get_filename()
    return Attachment(
        content=_message_bytes(part, sliced, raw)
        if isinstance(part.get_payload(), list)
        else _decoded(part),
        filename=None if filename is None else _readable(_recovered(filename))[0],
        media_type=part.get_content_type(),
    )


def _identity_digest(part: EmailMessage, attachment: Attachment) -> str:
    """The digest of an attachment as the identity takes it. Bytes that
    travelled as lines of text — no transfer encoding, 7bit, 8bit,
    quoted-printable, which is also how an attached mail travels — enter
    with every line ending as LF, so that an LF copy of the mail is no other
    artifact. Bytes in base64 or binary enter as they are, and their digest
    is the address of their blob."""
    if _transfer_encoding(part) in _LINE_ENCODINGS:
        return _sha256(_lf(attachment.content))
    return _sha256(attachment.content)


def _no_body_reason(message: EmailMessage, attachments: tuple[Attachment, ...]) -> str:
    """Why a mail has no readable body. Encrypted wins, so that a reader
    does not take the encrypted parts for the mail's attachments."""
    for part in _walk(message):
        media_type = part.get_content_type()
        if media_type == "multipart/encrypted":
            return NO_BODY_ENCRYPTED
        if media_type in ("application/pkcs7-mime", "application/x-pkcs7-mime"):
            smime_type = str(part.get_param("smime-type") or "").lower()
            if smime_type in ("enveloped-data", "authenveloped-data"):
                return NO_BODY_ENCRYPTED
    return NO_BODY_ATTACHMENTS_ONLY if attachments else NO_BODY_EMPTY


def _units(subject: str | None, texts: list[_Text], no_body: str) -> tuple[RawUnit, ...]:
    """The subject as unit 1, then the paragraphs of every body part in
    order. Without a readable body the fixed sentence stands in its place,
    so that no mail is without a unit and every mail says why it has no
    text."""
    contents: list[str] = []
    if subject is not None and subject.strip():
        contents.append(subject.strip())
    body = "\n\n".join(text.text for text in texts)
    if body.strip():
        contents.extend(unit.content for unit in split_plaintext(body))
    else:
        contents.append(no_body)
    return tuple(RawUnit(seq=seq, content=content) for seq, content in enumerate(contents, 1))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --- a mail inside a mail ----------------------------------------------------
#
# The bytes of an attached mail are its raw mail, and they have to be the
# bytes as they stand in the attachment. The parser does not keep them: it
# keeps the attached mail as a parsed message, and writing that back out is
# no copy — a header in raw UTF-8 comes out as an encoded word, a blank
# after a colon gets normalised (measured on 2026-10-06). The same mail
# forwarded and lying in the folder on its own would then be two different
# raw mails, and its subject could decode to something else.
#
# So the attached mail is cut out of the raw bytes: along the boundaries the
# parser found, part by part, to the body of the `message/*` part. The cut
# is held against the parser before it is used: parsed on its own and
# written back out, it has to come out as the parser's attached mail does —
# this module reads delimiters and header ends with a few lines of its own,
# and the parser is the one the rest of the mapping follows. Where no cut is
# found, or the cut disagrees, the part as the parser has it is written back
# out instead. That is no copy, as said, but it is all of the content.
# Measured on 2026-10-06 with a lone CR as the line ending: the parser
# splits lines there, this module's delimiters do not match, and the
# fallback carries the mail.


def _body_of(data: bytes) -> bytes:
    match = _HEADER_END.search(data)
    return data[match.end() :] if match else b""


def _split(body: bytes, boundary: str) -> list[bytes] | None:
    """The parts of a multipart body, each without the line ending that
    belongs to the delimiter after it. Up to the closing delimiter; a body
    cut off before it ends with the last part as far as it goes."""
    try:
        marker = boundary.encode("ascii")
    except UnicodeEncodeError:
        return None
    delimiter = re.compile(
        rb"^--" + re.escape(marker) + rb"(--)?[ \t]*(?:\r\n|\r|\n|\Z)", re.MULTILINE
    )
    matches = list(delimiter.finditer(body))
    chunks: list[bytes] = []
    for index, match in enumerate(matches):
        if match.group(1):
            break
        if index + 1 < len(matches):
            chunk = body[match.end() : matches[index + 1].start()]
            chunk = chunk.removesuffix(b"\n").removesuffix(b"\r")
        else:
            chunk = body[match.end() :]
        chunks.append(chunk)
    return chunks


def _sliced(message: EmailMessage, raw: bytes) -> dict[int, bytes]:
    """The bytes of every `message/*` part in `raw`, by the part's `id`, for
    the parts whose cut agrees with the parser."""
    found: dict[int, bytes] = {}
    _collect(message, raw, found)
    return found


def _collect(part: EmailMessage, data: bytes, found: dict[int, bytes]) -> None:
    payload: object = part.get_payload()
    if not isinstance(payload, list):
        return
    if part.get_content_maintype() != "multipart":
        # The cut that is kept is the body, so the body is what gets held
        # against the parser's attached mail — not the whole part, which
        # agrees even where the body does not: a line that is no header,
        # right below the part's headers, starts the parser's body there,
        # while `_body_of` looks for the next empty line.
        #
        # Compared without trailing line endings. A mail whose own boundary
        # cannot be found keeps, as the parser reads it inside the multipart,
        # the line ending that belongs to the delimiter after it, and loses
        # it when the cut is parsed on its own — measured on 2026-10-06 with
        # the quoted-printable forward, whose `boundary=3D` the parser cannot
        # read. `_agree` strips every CR and LF at the end, not only one line
        # ending; the cut itself ends where the delimiter begins, which is
        # where RFC 2046 puts the end of the part.
        body = _body_of(data)
        attached = cast("list[EmailMessage]", payload)
        if len(attached) == 1 and _agree(_parsed(body), attached[0]):
            found[id(part)] = body
        return
    children = _children(part)
    boundary = part.get_boundary()
    chunks = None if boundary is None else _split(_body_of(data), boundary)
    if chunks is None or len(chunks) != len(children):
        return
    for child, chunk in zip(children, chunks, strict=True):
        _collect(child, chunk, found)


def _message_bytes(part: EmailMessage, sliced: dict[int, bytes], raw: bytes) -> bytes:
    """The bytes of a `message/*` part: as they stand in `raw` where the cut
    agrees with the parser, otherwise written back out, and in both cases
    with a transfer encoding undone.

    RFC 2046 allows a `message/rfc822` part no encoding other than 7bit,
    8bit or binary, and some clients write base64 all the same. The parser
    then reads the base64 text as a mail without headers; decoding it first
    gives the mail.
    """
    content = sliced.get(id(part))
    if content is None:
        linesep = "\r\n" if b"\r\n" in raw else "\n"
        content = _body_of(_serialised(part, linesep))
    encoding = _transfer_encoding(part)
    if encoding == "base64":
        try:
            return base64.b64decode(content)
        except binascii.Error:
            # Broken base64 inside a part that should carry none: the bytes
            # stay as they are, and the mail inside is mapped from them.
            return content
    if encoding == "quoted-printable":
        return quopri.decodestring(content)
    return content


def _agree(first: EmailMessage, second: EmailMessage) -> bool:
    return _serialised(first).rstrip(b"\r\n") == _serialised(second).rstrip(b"\r\n")


def _parsed(data: bytes) -> EmailMessage:
    return email.message_from_bytes(data, policy=_POLICY)


def _serialised(part: EmailMessage, linesep: str = "\n") -> bytes:
    buffer = io.BytesIO()
    policy = _POLICY.clone(linesep=linesep, refold_source="none")
    BytesGenerator(buffer, mangle_from_=False, policy=policy).flatten(part)
    return buffer.getvalue()
