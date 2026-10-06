# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""A mail as an event ({ref}`artifact-identity`).

`map_mail` takes the raw bytes of one mail and gives back the event, the
attachments, and the mails attached to it, each mapped the same way. It is
pure: no network, no database, no clock — where the mail names no usable
time, the fallback is the server's arrival time handed in, not "now".

The identity of a mail is a rule of this project and not of a library: the
SHA-256 of the canonical form of the decoded subject, the SHA-256 of the
chosen body part's bytes after the transfer encoding and before any
conversion into text, and the sorted SHA-256 of every attachment. Nothing of
the transport goes in, so two copies from two mailboxes are one artifact;
nothing of the conversion goes in, so a better converter does not turn every
sighting into a variant. That is why this module takes the mail apart with
the standard library's `email` and decides itself what is decoded.

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
import email
import email.policy
import hashlib
import html2text
import io
import quopri
import re


if TYPE_CHECKING:
    from collections.abc import Iterator
    from collections.abc import Mapping
    from datetime import datetime


MAX_FORWARD_DEPTH = 5
"""How deep mails inside mails are unpacked. The outer mail is depth 0; a
mail attached at depth 5 stays an attachment, and the payload of the mail at
depth 5 lists it under `not_unpacked`. The limit guards against a broken or
hostile mail, not against real mail."""

SOURCE = "email"

# The one unit of a mail without a readable body, so that no mail is
# without a unit. Fixed English sentences: they say why, and they are what
# the reference page quotes.
NO_BODY_ENCRYPTED = "no readable body: encrypted"
NO_BODY_ATTACHMENTS_ONLY = "no readable body: attachments only"
NO_BODY_EMPTY = "no readable body: empty"

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

_LINE_BREAK = re.compile(r"\r\n|\r|\n")
_SURROGATE = re.compile("[\ud800-\udfff]")

# The end of the header block: an empty line, or one right at the start.
_HEADER_END = re.compile(rb"(?:\A|\n)(?:\r\n|\n)")


@dataclass(frozen=True)
class Attachment:
    """One attachment of a mail: its decoded bytes, its name if it carries
    one, and its media type. A mail attached to a mail is an attachment too,
    with its bytes as they stand and the type `message/rfc822`."""

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
class _Body:
    part: EmailMessage
    data: bytes
    text: str
    charset: str
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
    every mail attached to this one is given the same two. Raises
    `InvalidPayload` for a naive `internaldate`. A mail that cannot be taken
    apart is mapped as far as it reads; the one mail known not to map is
    named at `_headers`.
    """
    return _map(raw, internaldate=internaldate, found_in=found_in, depth=0, forwarded_in=None)


def _map(
    raw: bytes,
    *,
    internaldate: datetime,
    found_in: Mapping[str, str],
    depth: int,
    forwarded_in: str | None,
) -> Mapped:
    message = email.message_from_bytes(raw, policy=_POLICY)
    headers = _headers(message)
    subject = _first(headers, "subject")
    body = _body(message)
    leaves = _attachment_parts(message, body.part if body else None)
    sliced = _sliced(message, raw)
    attachments = tuple(_attachment(part, sliced, raw) for part in leaves)

    # The subject as the headers have it, decoded and with a null byte
    # already replaced: the canonical form refuses one. A subject that is
    # absent is `null`, one that is empty is `""`.
    artifact_hash = artifact_hash_of(
        {
            "subject": subject,
            "body": _sha256(body.data) if body else None,
            "attachments": sorted(_sha256(attachment.content) for attachment in attachments),
        }
    )
    external_id = _message_id(headers) or "sha256:" + artifact_hash.hex()
    occurred_at, date_source = _occurred_at(message, internaldate)

    payload: dict[str, object] = {
        "headers": [[name, value] for name, value in headers],
        "date_source": date_source,
        "internaldate": iso_utc(internaldate),
        "found_in": dict(found_in),
        "body": None
        if body is None
        else {
            "part": body.part.get_content_type(),
            "charset": body.charset,
            "converter": body.converter,
            "replaced": body.replaced,
        },
    }
    if forwarded_in is not None:
        payload["forwarded_in"] = forwarded_in

    inner: list[Mapped] = []
    not_unpacked: list[str] = []
    for attachment in attachments:
        if attachment.media_type != "message/rfc822":
            continue
        if depth < MAX_FORWARD_DEPTH:
            inner.append(
                _map(
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
        units=_units(subject, body, _no_body_reason(message, attachments)),
        payload=payload,
        artifact_hash=artifact_hash,
        channel_identities=_channel_identities(message),
    )
    return Mapped(event=event, raw=raw, attachments=attachments, inner=tuple(inner))


# --- text --------------------------------------------------------------------


def _readable(text: str) -> tuple[str, bool]:
    """`text` with what the log cannot hold replaced, and whether anything
    was.

    A header byte outside ASCII arrives from the parser as a lone surrogate,
    in a display name or a file name. It is read as UTF-8 first, which RFC
    6532 allows in a header; whatever is no UTF-8 becomes U+FFFD. A
    surrogate no byte was escaped into \u2014 a UTF-7 body can decode to one \u2014
    and a null byte become U+FFFD too: PostgreSQL stores neither, in `text`
    or in `jsonb`.
    """
    replaced = False
    if _SURROGATE.search(text):
        try:
            data = text.encode("utf-8", "surrogateescape")
        except UnicodeEncodeError:
            text, replaced = _SURROGATE.sub("\ufffd", text), True
        else:
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                text, replaced = data.decode("utf-8", "replace"), True
    if "\x00" in text:
        text, replaced = text.replace("\x00", "\ufffd"), True
    return text, replaced


def _decode(data: bytes, charset: str) -> tuple[str, str, bool]:
    """`data` as text in `charset`: the text, the charset it was read with,
    and whether anything was replaced. A charset Python does not know is
    read as Latin-1, which reads every byte as some character, so the
    content stays and the payload says that it may be wrong."""
    try:
        text, replaced = data.decode(charset), False
    except LookupError:
        charset = "iso-8859-1"
        text, replaced = data.decode(charset), True
    except UnicodeDecodeError:
        text, replaced = data.decode(charset, "replace"), True
    text, nul = _readable(text)
    return text, charset, replaced or nul


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


# --- headers -----------------------------------------------------------------


def _unfolded(value: object) -> str:
    return _LINE_BREAK.sub("", str(value))


def _headers(message: EmailMessage) -> list[tuple[str, str]]:
    """Every header in the order of the mail, duplicates included, the name
    as written, the value unfolded and with encoded words decoded.

    Not caught, and named rather than handled: an encoded word that decodes
    to a lone surrogate — UTF-7 can spell one, as in `=?utf-7?q?+2D0-?=` —
    makes the standard library's header classes raise `UnicodeEncodeError`,
    in any header, and every header passes through here first (measured on
    2026-10-06 with Python 3.14.3, in an `X-` header, in `From` and in
    `Date`). No encoder writes such a word; a mail that carries one does
    not map.
    """
    headers: list[tuple[str, str]] = []
    for name, value in message.raw_items():
        header = _UNSTRUCTURED(name, _unfolded(value))
        headers.append((name, _readable(str(header))[0]))
    return headers


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
        header = _POLICY.header_fetch_parse(name, _unfolded(value))
        if isinstance(header, AddressHeader):
            identities.extend(
                ChannelIdentity(
                    SOURCE,
                    role,
                    _readable(address.addr_spec)[0],
                    _readable(address.display_name)[0] or None,
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


def _walk(
    part: EmailMessage, ancestors: tuple[EmailMessage, ...] = ()
) -> Iterator[tuple[EmailMessage, tuple[EmailMessage, ...]]]:
    yield part, ancestors
    for child in _children(part):
        yield from _walk(child, (*ancestors, part))


def _is_leaf(part: EmailMessage) -> bool:
    return part.get_content_maintype() != "multipart" or not _children(part)


def _body_part(message: EmailMessage) -> EmailMessage | None:
    """The part `text/plain` when there is one, otherwise `text/html`, the
    first of either that is not an attachment. When neither exists and a
    multipart could not be split — its boundary missing, or never found —
    that multipart's payload is the text: the MIME lines stand in it, and so
    does every word of the mail."""
    candidates = [part for part, _ in _walk(message) if _is_leaf(part)]
    for subtype in ("plain", "html"):
        for part in candidates:
            if part.get_content_type() == f"text/{subtype}" and not part.is_attachment():
                return part
    for part in candidates:
        if part.get_content_maintype() == "multipart":
            return part
    return None


def _body(message: EmailMessage) -> _Body | None:
    part = _body_part(message)
    if part is None:
        return None
    data = _decoded(part)
    text, charset, replaced = _decode(data, part.get_content_charset() or "us-ascii")
    converter = None
    if part.get_content_type() == "text/html":
        text, converter = _html_to_text(text), CONVERTER
    return _Body(part, data, text, charset, converter, replaced)


def _decoded(part: EmailMessage) -> bytes:
    """The bytes of a part after its transfer encoding."""
    data: object = part.get_payload(decode=True)
    return data if isinstance(data, bytes) else b""


def _attachment_parts(message: EmailMessage, body: EmailMessage | None) -> list[EmailMessage]:
    """Every leaf part except the body and the alternatives to it.

    An alternative is a `text/plain` or `text/html` part, not marked as an
    attachment, under the same `multipart/alternative` as the body: the
    same text once more. Everything else is kept — an inline image, a
    calendar invitation beside the text, a signature, the parts of an
    encrypted mail —, because what is not an attachment here is only in the
    raw mail.
    """
    alternative = None
    leaves: list[tuple[EmailMessage, tuple[EmailMessage, ...]]] = []
    for part, ancestors in _walk(message):
        if part is body:
            alternative = next(
                (a for a in reversed(ancestors) if a.get_content_type() == "multipart/alternative"),
                None,
            )
        if _is_leaf(part):
            leaves.append((part, ancestors))
    kept: list[EmailMessage] = []
    for part, ancestors in leaves:
        if part is body:
            continue
        if (
            alternative is not None
            and any(a is alternative for a in ancestors)
            and part.get_content_type() in ("text/plain", "text/html")
            and not part.is_attachment()
        ):
            continue
        kept.append(part)
    return kept


def _attachment(part: EmailMessage, sliced: dict[int, bytes], raw: bytes) -> Attachment:
    filename = part.get_filename()
    return Attachment(
        content=_message_bytes(part, sliced, raw)
        if isinstance(part.get_payload(), list)
        else _decoded(part),
        filename=None if filename is None else _readable(filename)[0],
        media_type=part.get_content_type(),
    )


def _no_body_reason(message: EmailMessage, attachments: tuple[Attachment, ...]) -> str:
    """Why a mail has no readable body. Encrypted wins, so that a reader
    does not take the encrypted parts for the mail's attachments."""
    for part, _ in _walk(message):
        media_type = part.get_content_type()
        if media_type == "multipart/encrypted":
            return NO_BODY_ENCRYPTED
        if media_type in ("application/pkcs7-mime", "application/x-pkcs7-mime"):
            smime_type = str(part.get_param("smime-type") or "").lower()
            if smime_type in ("enveloped-data", "authenveloped-data"):
                return NO_BODY_ENCRYPTED
    return NO_BODY_ATTACHMENTS_ONLY if attachments else NO_BODY_EMPTY


def _units(subject: str | None, body: _Body | None, no_body: str) -> tuple[RawUnit, ...]:
    """The subject as unit 1, then the paragraphs of the body. Without a
    readable body the fixed sentence stands in its place, so that no mail is
    without a unit and every mail says why it has no text."""
    contents: list[str] = []
    if subject is not None and subject.strip():
        contents.append(subject.strip())
    if body is not None and body.text.strip():
        contents.extend(unit.content for unit in split_plaintext(body.text))
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
# is held against the parser before it is used: the part it belongs to,
# parsed on its own and written back out, has to come out as the parser's
# own part does — this module reads delimiters and header ends with a few
# lines of its own, and the parser is the one the rest of the mapping
# follows. Where no cut is found, or the cut disagrees, the part as the
# parser has it is written back out instead. That is no copy, as said, but
# it is all of the content. Measured on 2026-10-06 with a lone CR as the
# line ending: the parser splits lines there, this module's delimiters do
# not match, and the fallback carries the mail.


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
        # Compared without the final line ending. A mail whose own boundary
        # cannot be found keeps, as the parser reads it inside the multipart,
        # the line ending that belongs to the delimiter after it, and loses
        # it when the cut is parsed on its own — measured on 2026-10-06 with
        # the quoted-printable forward, whose `boundary=3D` the parser cannot
        # read. The cut ends where the delimiter begins, which is where RFC
        # 2046 puts the end of the part.
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
    encoding = str(part.get("content-transfer-encoding") or "").strip().lower()
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
