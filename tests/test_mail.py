# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""A mail as an event: the raw bytes of a mail mapped onto an event, its
attachments and the mails forwarded inside it ({ref}`artifact-identity`).

The mails are files under `tests/mails/`, written by `tests/mailfiles.py`;
every expected value here is stated from the bytes there, not read back from
the code under test. A mapping that silently loses content is the costliest
defect this mapping can have, so most tests name what has to arrive where.
"""

from datetime import datetime
from datetime import timedelta
from datetime import timezone
from datetime import UTC
from previously.contract.types import ChannelIdentity
from previously.contract.types import Evidence
from previously.core.append import check_units
from previously.core.canonical import canonical
from previously.core.errors import InvalidPayload
from previously.core.hashing import iso_utc
from previously.core.identity import artifact_hash_of
from previously.core.mail import Attachment
from previously.core.mail import map_mail
from previously.core.mail import Mapped
from previously.core.mail import MAX_FORWARD_DEPTH
from previously.core.mail import variant_key
from typing import cast

import hashlib
import importlib.metadata
import mailfiles
import pytest
import quopri


INTERNALDATE = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
FOUND_IN = {"connector": "imap:pilot@mail.example.org/Kunde Müller", "uidvalidity": "1", "uid": "7"}
CEST = timezone(timedelta(hours=2))
CET = timezone(timedelta(hours=1))

# The names the payload of a mail may carry. `raw` is not among them: the
# address of the raw mail is known only once the run has stored it.
PAYLOAD_NAMES = {
    "headers",
    "date_source",
    "internaldate",
    "found_in",
    "body",
    "forwarded_in",
    "not_unpacked",
    "headers_replaced",
}


def _map(name: str) -> Mapped:
    raw = (mailfiles.HERE / f"{name}.eml").read_bytes()
    return map_mail(raw, internaldate=INTERNALDATE, found_in=FOUND_IN)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _contents(mapped: Mapped) -> list[str]:
    return [unit.content for unit in mapped.event.units]


def _headers(mapped: Mapped) -> list[list[str]]:
    return cast("list[list[str]]", mapped.event.payload["headers"])


def _body(mapped: Mapped) -> list[dict[str, object]]:
    return cast("list[dict[str, object]]", mapped.event.payload["body"])


def _part(
    part: str,
    charset: str,
    declared: str | None,
    *,
    guessed: bool = False,
    converter: str | None = None,
    replaced: bool = False,
) -> dict[str, object]:
    """One entry of `body` in the payload, spelled out."""
    return {
        "part": part,
        "charset": charset,
        "declared": declared,
        "guessed": guessed,
        "converter": converter,
        "replaced": replaced,
    }


def _body_digest(data: bytes) -> str:
    """The digest of one body part as the identity takes it: its decoded
    bytes with every line ending as LF."""
    return _sha(data.replace(b"\r\n", b"\n").replace(b"\r", b"\n"))


def _converter() -> str:
    return f"html2text {importlib.metadata.version('html2text')}"


# --- the files ---------------------------------------------------------------


def test_every_mail_file_is_what_mailfiles_writes() -> None:
    """A file and the bytes that describe it cannot drift apart."""
    on_disk = {path.stem: path.read_bytes() for path in mailfiles.HERE.glob("*.eml")}
    assert on_disk == mailfiles.MAILS


@pytest.mark.parametrize("name", sorted(mailfiles.MAILS))
def test_every_mail_maps_to_an_event_append_would_take(name: str) -> None:
    """Whatever a mail brings, it maps, and what comes out passes the checks
    `append` applies: no mail falls out of the folder."""
    mapped = _map(name)
    event = mapped.event
    assert event.source == "email"
    assert event.evidence is Evidence.VERBATIM
    assert event.units
    assert [unit.seq for unit in event.units] == list(range(1, len(event.units) + 1))
    assert all(unit.content.strip() == unit.content and unit.content for unit in event.units)
    check_units(event.units)
    canonical(event.payload)
    iso_utc(event.occurred_at)
    assert event.artifact_hash is not None
    assert len(event.artifact_hash) == 32
    assert set(event.payload) <= PAYLOAD_NAMES
    assert event.blobs == ()
    assert mapped.raw == mailfiles.MAILS[name]


# --- the simple mail ---------------------------------------------------------


def test_a_plain_mail_maps_field_by_field() -> None:
    mapped = _map("plain")
    event = mapped.event
    assert event.external_id == "20261005101500.4711@example.net"
    assert event.occurred_at == datetime(2026, 10, 5, 10, 15, tzinfo=CEST)
    assert event.payload["date_source"] == "header"
    assert event.payload["internaldate"] == "2026-10-08T12:00:00.000000Z"
    assert event.payload["found_in"] == FOUND_IN
    assert _contents(mapped) == [
        "Angebot für den Relaunch",
        "Liebe Eva,",
        "anbei die Eckpunkte für den Relaunch. The budget stays as discussed, the\n"
        "timeline moves by two weeks.",
        "Schöne Grüße\nJürgen",
        "--\nJürgen Müller · Example Studio",
    ]
    assert _body(mapped) == [
        {
            "part": "text/plain",
            "charset": "utf-8",
            "declared": "utf-8",
            "guessed": False,
            "converter": None,
            "replaced": False,
        }
    ]
    assert mapped.attachments == ()
    assert mapped.inner == ()
    assert "forwarded_in" not in event.payload


def test_channel_identities_follow_the_order_of_the_header() -> None:
    """`To` stands first in this mail, so it comes first; `Reply-To` is
    `reply_to`; a display name is decoded, an address stays as written."""
    assert _map("plain").event.channel_identities == (
        ChannelIdentity("email", "to", "eva.huber@example.org", "Eva Huber"),
        ChannelIdentity("email", "to", "team@example.org", None),
        ChannelIdentity("email", "from", "juergen.mueller@example.net", "Jürgen Müller"),
        ChannelIdentity("email", "cc", "office@example.org", "Office"),
        ChannelIdentity("email", "reply_to", "projekte@example.net", None),
    )


def test_headers_are_all_there_in_order_with_their_duplicates() -> None:
    """Both `Received` lines, names as written, values unfolded — the
    line break and the tab after it into one space — and with encoded words
    decoded, and otherwise as written: `"Office"` keeps its quotes,
    `charset=utf-8` gets none."""
    assert _map("plain").event.payload["headers"] == [
        [
            "Received",
            "from mx.example.net (mx.example.net [192.0.2.10])"
            " by mail.example.org with ESMTPS id 4F2A1; Mon, 05 Oct 2026 10:15:04 +0200",
        ],
        [
            "Received",
            "from client.example.net ([198.51.100.7])"
            " by mx.example.net with ESMTPSA; Mon, 05 Oct 2026 10:15:02 +0200",
        ],
        ["To", "Eva Huber <eva.huber@example.org>, team@example.org"],
        ["From", "Jürgen Müller <juergen.mueller@example.net>"],
        ["Cc", '"Office" <office@example.org>'],
        ["Reply-To", "projekte@example.net"],
        ["Subject", "Angebot für den Relaunch"],
        ["Date", "Mon, 05 Oct 2026 10:15:00 +0200"],
        ["Message-ID", "<20261005101500.4711@example.net>"],
        ["MIME-Version", "1.0"],
        ["Content-Type", "text/plain; charset=utf-8"],
        ["Content-Transfer-Encoding", "8bit"],
    ]


def test_the_artifact_hash_is_subject_body_and_attachments() -> None:
    """Spelled out: the decoded subject, the SHA-256 of each body part's
    bytes after the transfer encoding and before any conversion, line endings
    as LF, and the sorted SHA-256 of every attachment — here none."""
    expected = artifact_hash_of(
        {
            "subject": "Angebot für den Relaunch",
            "body": [_body_digest(mailfiles.PLAIN_BODY)],
            "attachments": [],
        }
    )
    assert _map("plain").event.artifact_hash == expected


def test_two_copies_with_other_transport_lines_are_one_artifact() -> None:
    first = _map("plain")
    second = _map("plain_other_transport")
    # Control: the two copies really do differ, in their transport lines.
    assert first.event.payload["headers"] != second.event.payload["headers"]
    assert first.event.external_id == second.event.external_id
    assert first.event.artifact_hash == second.event.artifact_hash


def test_another_body_under_the_same_message_id_is_another_artifact() -> None:
    first = _map("plain")
    other = _map("plain_other_body")
    assert first.event.external_id == other.event.external_id
    assert first.event.artifact_hash != other.event.artifact_hash


@pytest.mark.parametrize("name", sorted(mailfiles.MAILS))
def test_the_text_stands_nowhere_in_the_payload(name: str) -> None:
    """The text of a mail lives in its units, so that erasing units erases
    it. Units shorter than fifteen characters are left out of the check:
    "Eva" is a body unit of the reply and also a display name in its
    headers, which is where the spec puts it."""
    mapped = _map(name)
    payload = canonical(mapped.event.payload).decode()
    body_units = [unit.content for unit in mapped.event.units[1:] if len(unit.content) >= 15]
    for content in body_units:
        assert content not in payload


# --- HTML --------------------------------------------------------------------


def test_html_only_is_converted_into_paragraphs() -> None:
    """Outlook's paragraphs become units; the entity `&uuml;` stays an `ü`;
    the tracking pixel does not reach the text."""
    mapped = _map("html_only")
    assert _contents(mapped) == [
        "AW: Angebot für den Relaunch",
        "Hallo Jürgen,",
        "danke für das Angebot. We accept the new timeline.",
        "Viele Grüße  \nEva",
    ]
    assert not any("tracker" in content for content in _contents(mapped))
    assert _body(mapped) == [
        _part("text/html", "windows-1252", "windows-1252", converter=_converter())
    ]


def test_the_body_hash_of_html_is_taken_before_the_conversion() -> None:
    """The identity does not depend on the converter: the hash is over the
    windows-1252 bytes the quoted-printable decodes to."""
    expected = artifact_hash_of(
        {
            "subject": "AW: Angebot für den Relaunch",
            "body": [_body_digest(quopri.decodestring(mailfiles.HTML_ONLY_QP))],
            "attachments": [],
        }
    )
    assert _map("html_only").event.artifact_hash == expected


def test_a_blockquote_stays_marked_as_a_quote() -> None:
    assert _contents(_map("html_blockquote")) == [
        "Re: Call on Thursday?",
        "Thanks, that works for us.",
        "Best, Lea",
        "On Mon, Oct 5, 2026 at 10:00 AM Max wrote:",
        "> Können wir am Donnerstag telefonieren?  \n>   \n> Gruß, Max",
    ]


def test_a_reply_keeps_its_references_and_its_text_part() -> None:
    """The plain part is the body; the HTML alternative of the same text is
    no attachment."""
    mapped = _map("reply")
    headers = _headers(mapped)
    assert ["In-Reply-To", "<20261005101500.4711@example.net>"] in headers
    assert [
        "References",
        "<20261001080000.1@example.org> <20261005101500.4711@example.net>",
    ] in headers
    assert _body(mapped) == [_part("text/plain", "utf-8", "utf-8")]
    assert mapped.attachments == ()
    assert _contents(mapped) == [
        "Re: Angebot für den Relaunch",
        "Hallo Jürgen,",
        "passt, wir nehmen den neuen Zeitplan.",
        "Eva",
        "Am 05.10.2026 um 10:15 schrieb Jürgen Müller:\n> Liebe Eva,\n>\n"
        "> anbei die Eckpunkte für den Relaunch.",
    ]


# --- keys and times ----------------------------------------------------------


def test_without_a_message_id_the_key_is_the_artifact_hash() -> None:
    event = _map("no_message_id").event
    assert event.artifact_hash is not None
    assert event.external_id == "sha256:" + event.artifact_hash.hex()


@pytest.mark.parametrize("name", ["date_unreadable", "date_without_zone", "date_missing"])
def test_a_date_that_reads_as_no_moment_with_a_zone_falls_back_to_internaldate(
    name: str,
) -> None:
    """`Montag, 5. Oktober 2026, 10 Uhr` is no date; `-0000` is one without
    a zone; and a mail may carry none. None of them becomes a moment the log
    can order — and none becomes 1900-01-01 or now."""
    event = _map(name).event
    assert event.occurred_at == INTERNALDATE
    assert event.payload["date_source"] == "internaldate"


def test_a_naive_internaldate_is_refused() -> None:
    """Local time would not be reproducible, and the fallback has to be."""
    naive = INTERNALDATE.replace(tzinfo=None)
    with pytest.raises(InvalidPayload, match="without time zone"):
        map_mail(mailfiles.PLAIN, internaldate=naive, found_in=FOUND_IN)


def test_the_variant_key_is_the_message_id_and_sixteen_hex_characters() -> None:
    assert variant_key("a@example.org", bytes(range(32))) == "a@example.org#0001020304050607"


def test_mapping_is_pure() -> None:
    """The same bytes, the same sighting: the same result, twice."""
    assert _map("forwarded") == _map("forwarded")


# --- characters --------------------------------------------------------------


def test_a_null_byte_and_an_unreadable_byte_become_the_replacement_character() -> None:
    mapped = _map("body_unreadable")
    assert _contents(mapped) == [
        "Invoice 17",
        "Rechnung Nr. 17\ufffd liegt bei.",
        "Betrag: 120 \ufffd EUR",
    ]
    assert _body(mapped) == [_part("text/plain", "utf-8", "utf-8", replaced=True)]


def test_the_body_hash_is_over_the_bytes_not_over_the_replaced_text() -> None:
    expected = artifact_hash_of(
        {
            "subject": "Invoice 17",
            "body": [_body_digest(mailfiles.BODY_UNREADABLE_BODY)],
            "attachments": [],
        }
    )
    assert _map("body_unreadable").event.artifact_hash == expected


def test_a_lone_surrogate_in_a_body_becomes_the_replacement_character() -> None:
    mapped = _map("body_lone_surrogate")
    assert _contents(mapped)[1] == "Smiley \ufffd here."
    assert _body(mapped) == [_part("text/plain", "utf-7", "utf-7", replaced=True)]


def test_header_bytes_outside_ascii_are_read_as_utf_8_or_replaced() -> None:
    """UTF-8 in a header reads as UTF-8, in the subject as in a display
    name; bytes that are no UTF-8 read as Windows-1252, as an old mailer
    writes them; a null byte becomes the replacement character, and the
    payload names the header it stood in."""
    mapped = _map("headers_8bit")
    assert _contents(mapped)[0] == "Grüße aus Köln"
    assert mapped.event.channel_identities[:2] == (
        ChannelIdentity("email", "from", "juergen.mueller@example.net", "Jürgen Müller"),
        ChannelIdentity("email", "sender", "joerg@example.net", "Jörg"),
    )
    headers = _headers(mapped)
    assert ["X-Note", "Grüße"] in headers
    assert ["X-Null", "a\ufffdb"] in headers
    assert mapped.event.payload["headers_replaced"] == ["X-Null"]


# --- no readable body --------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "subject"),
    [("encrypted", "Vertrag"), ("encrypted_smime", "Kaufvertrag Entwurf")],
)
def test_an_encrypted_mail_says_so_and_keeps_its_parts(name: str, subject: str) -> None:
    """Nothing is decrypted. The subject stands, then the fixed sentence;
    the encrypted parts are attachments, so that they are kept."""
    mapped = _map(name)
    assert _contents(mapped) == [subject, "no readable body: encrypted"]
    assert _body(mapped) == []
    assert mapped.attachments


def test_the_parts_of_a_pgp_mail_are_its_attachments() -> None:
    attachments = _map("encrypted").attachments
    assert [(a.media_type, a.filename) for a in attachments] == [
        ("application/pgp-encrypted", None),
        ("application/octet-stream", "encrypted.asc"),
    ]


def test_the_envelope_of_an_smime_mail_is_its_attachment() -> None:
    assert _map("encrypted_smime").attachments == (
        Attachment(mailfiles.SMIME_CONTENT, "smime.p7m", "application/pkcs7-mime"),
    )


def test_a_mail_with_attachments_only_and_no_subject_has_one_unit() -> None:
    mapped = _map("attachments_only")
    assert _contents(mapped) == ["no readable body: attachments only"]
    assert mapped.attachments == (
        Attachment(mailfiles.PDF_CONTENT, "Angebot.pdf", "application/pdf"),
        Attachment(mailfiles.PNG_CONTENT, "plan.png", "image/png"),
    )
    expected = artifact_hash_of(
        {
            "subject": None,
            "body": [],
            "attachments": sorted([_sha(mailfiles.PDF_CONTENT), _sha(mailfiles.PNG_CONTENT)]),
        }
    )
    assert mapped.event.artifact_hash == expected


def test_a_mail_with_nothing_but_a_subject_says_it_is_empty() -> None:
    """Without a `Content-Type` a mail is `text/plain` in US-ASCII (RFC
    2045), so it has a body part — an empty one."""
    mapped = _map("empty")
    assert _contents(mapped) == ["Rückruf bitte / please call back", "no readable body: empty"]
    assert _body(mapped) == [_part("text/plain", "us-ascii", None)]


def test_a_signed_mail_reads_its_text_and_keeps_its_signature() -> None:
    mapped = _map("signed")
    assert _contents(mapped) == [
        "Freigabe Version 2",
        "Hallo Team,",
        "die Freigabe für Version 2 ist erteilt.",
        "Max",
    ]
    assert mapped.attachments == (
        Attachment(
            mailfiles.SIGNATURE.removesuffix(b"\r\n"), "signature.asc", "application/pgp-signature"
        ),
    )


def test_two_attachments_with_the_same_content_are_two_attachments() -> None:
    """Both stay, each with its name; the identity lists the hash twice."""
    mapped = _map("duplicate_attachments")
    assert mapped.attachments == (
        Attachment(mailfiles.PDF_CONTENT, "Angebot.pdf", "application/pdf"),
        Attachment(mailfiles.PDF_CONTENT, "Angebot für Müller.pdf", "application/pdf"),
    )
    expected = artifact_hash_of(
        {
            "subject": "Angebot, zweimal",
            "body": [_body_digest(b"Das Angebot, einmal unter jedem Namen.")],
            "attachments": [_sha(mailfiles.PDF_CONTENT)] * 2,
        }
    )
    assert mapped.event.artifact_hash == expected


# --- broken MIME -------------------------------------------------------------


@pytest.mark.parametrize("name", ["broken_mime", "broken_mime_no_boundary"])
def test_a_multipart_without_a_findable_boundary_is_read_as_text(name: str) -> None:
    """No part can be found, so the whole body is the text: the MIME lines
    stand in it, and so does every word of the mail. No charset is
    declared, so it is guessed — and the bytes are UTF-8, so the `ä`
    stays."""
    mapped = _map(name)
    contents = _contents(mapped)
    assert contents[0] == "Protokoll Baubesprechung"
    assert "Protokoll der Baubesprechung vom 1. Oktober." in contents
    assert any(content.startswith("Nächster Termin") for content in contents)
    assert _body(mapped) == [_part("multipart/mixed", "utf-8", None, guessed=True)]


def test_a_truncated_mail_keeps_what_arrived() -> None:
    mapped = _map("broken_mime_truncated")
    assert _contents(mapped) == ["Plan Erdgeschoss", "Anbei der Plan fürs Erdgeschoss."]
    (attachment,) = mapped.attachments
    assert attachment.filename == "EG.pdf"
    assert attachment.content
    assert mailfiles.PDF_CONTENT.startswith(attachment.content)


# --- a mail inside a mail ----------------------------------------------------


def test_a_forwarded_mail_becomes_an_event_of_its_own() -> None:
    mapped = _map("forwarded")
    (inner,) = mapped.inner
    assert inner.event.external_id == "invoice-2026-10@example.com"
    assert inner.event.payload["forwarded_in"] == "fwd-20261008@example.org"
    assert inner.event.occurred_at == datetime(2026, 9, 30, 14, 20, tzinfo=CEST)
    assert inner.event.payload["date_source"] == "header"
    assert inner.event.payload["found_in"] == FOUND_IN
    assert _contents(inner) == [
        "Rechnung Oktober",
        "Sehr geehrte Frau Huber,",
        "anbei die Rechnung für Oktober.",
        "Mit freundlichen Grüßen\nBuchhaltung",
    ]
    assert inner.event.channel_identities[0] == ChannelIdentity(
        "email", "from", "buchhaltung@example.com", "Buchhaltung Müller GmbH"
    )
    assert inner.attachments == (
        Attachment(mailfiles.INVOICE_PDF, "Rechnung-2026-10.pdf", "application/pdf"),
    )


def test_the_raw_mail_of_a_forwarded_mail_is_its_bytes_as_they_stand() -> None:
    """Byte for byte, the raw UTF-8 display name included — a re-serialised
    mail would write it as an encoded word."""
    mapped = _map("forwarded")
    assert mapped.inner[0].raw == mailfiles.FORWARDED_INNER
    assert mapped.attachments == (
        Attachment(mailfiles.FORWARDED_INNER, "Rechnung Oktober.eml", "message/rfc822"),
    )


def test_the_frame_of_a_forward_keeps_its_own_content_only() -> None:
    """The outer mail is an event of its own; the inner mail's text is not
    in its units, the inner mail's attachment not in its attachments."""
    mapped = _map("forwarded")
    assert _contents(mapped) == ["Fwd: Rechnung Oktober", "no readable body: attachments only"]
    assert "forwarded_in" not in mapped.event.payload
    expected = artifact_hash_of(
        {
            "subject": "Fwd: Rechnung Oktober",
            "body": [_body_digest(b"")],
            # The attached mail travels as lines of text, so its line
            # endings enter as LF; its blob is the bytes as they stand.
            "attachments": [_body_digest(mailfiles.FORWARDED_INNER)],
        }
    )
    assert mapped.event.artifact_hash == expected


def test_a_forwarded_mail_with_lf_line_endings_is_sliced_the_same_way() -> None:
    """An `.eml` file saved on a Unix machine carries LF only."""
    raw = mailfiles.FORWARDED.replace(b"\r\n", b"\n")
    mapped = map_mail(raw, internaldate=INTERNALDATE, found_in=FOUND_IN)
    assert mapped.inner[0].raw == mailfiles.FORWARDED_INNER.replace(b"\r\n", b"\n")


def test_a_forwarded_mail_the_cut_cannot_find_is_written_back_out() -> None:
    """With a lone CR as the line ending the delimiters are not found, and
    the attached mail is written back out from the parsed part: no copy of
    its bytes — the raw UTF-8 display name comes out as an encoded word —,
    but all of its content."""
    raw = mailfiles.FORWARDED.replace(b"\r\n", b"\r")
    mapped = map_mail(raw, internaldate=INTERNALDATE, found_in=FOUND_IN)
    (inner,) = mapped.inner
    assert inner.raw != mailfiles.FORWARDED_INNER.replace(b"\r\n", b"\r")
    assert b"=?unknown-8bit?" in inner.raw
    assert inner.event.external_id == "invoice-2026-10@example.com"
    assert _contents(inner) == _contents(_map("forwarded").inner[0])
    assert inner.event.channel_identities == _map("forwarded").inner[0].event.channel_identities
    assert inner.attachments == _map("forwarded").inner[0].attachments


def test_a_cut_the_parser_disagrees_with_is_not_used() -> None:
    """A line that is no header, right below the headers of the attached
    part, starts that part's body for the parser — no empty line between.
    Cut at the next empty line instead, the attached mail would lose that
    line and its own headers; held against the parser, the cut is refused
    and the part is written back out with all of it — as a mail without
    headers, whose text starts with that line."""
    raw = mailfiles.FORWARDED.replace(
        b'filename="Rechnung Oktober.eml"\r\n\r\n',
        b'filename="Rechnung Oktober.eml"\r\nForwarded below.\r\n',
    )
    mapped = map_mail(raw, internaldate=INTERNALDATE, found_in=FOUND_IN)
    content = mapped.attachments[0].content
    assert b"Forwarded below.\r\nFrom: Buchhaltung" in content
    assert b"Message-ID: <invoice-2026-10@example.com>" in content
    assert mapped.inner[0].raw == content


@pytest.mark.parametrize("name", ["forwarded_base64", "forwarded_quoted_printable"])
def test_a_forwarded_mail_in_a_transfer_encoding_is_decoded_first(name: str) -> None:
    """RFC 2046 allows neither encoding for `message/rfc822`, and clients
    write them anyway. Decoded, it is the same mail as the unencoded one."""
    mapped = _map(name)
    assert mapped.attachments[0].content == mailfiles.FORWARDED_INNER
    (inner,) = mapped.inner
    assert inner.raw == mailfiles.FORWARDED_INNER
    assert inner.event.external_id == "invoice-2026-10@example.com"
    assert inner.event == _map("forwarded").inner[0].event


def test_the_same_mail_forwarded_and_on_its_own_is_one_artifact() -> None:
    forwarded = _map("forwarded").inner[0].event
    alone = map_mail(mailfiles.FORWARDED_INNER, internaldate=INTERNALDATE, found_in=FOUND_IN).event
    assert forwarded.external_id == alone.external_id
    assert forwarded.artifact_hash == alone.artifact_hash


def test_nesting_is_unpacked_down_to_five_and_the_sixth_stays_an_attachment() -> None:
    assert MAX_FORWARD_DEPTH == 5
    level = _map("nested_six")
    assert "not_unpacked" not in level.event.payload
    for depth in range(1, MAX_FORWARD_DEPTH + 1):
        (inner,) = level.inner
        assert inner.event.external_id == f"level-{depth}@example.org"
        assert inner.event.payload["forwarded_in"] == f"level-{depth - 1}@example.org"
        assert inner.event.occurred_at == datetime(2026, 11, depth + 1, 9, 0, tzinfo=CET)
        assert _contents(inner)[1] == f"Text der Ebene {depth}."
        level = inner
        if depth < MAX_FORWARD_DEPTH:
            assert "not_unpacked" not in level.event.payload
    sixth = mailfiles.nested(6)
    assert level.inner == ()
    assert level.attachments == (Attachment(sixth, None, "message/rfc822"),)
    assert level.event.payload["not_unpacked"] == [_sha(sixth)]


# --- every text part of the content (ruling T2-d) ----------------------------


def test_text_on_both_sides_of_an_attachment_is_all_body() -> None:
    """Apple Mail splits the text around a PDF placed between two
    paragraphs. Both halves are the mail's text; the PDF is the attachment."""
    mapped = _map("apple_split")
    assert _contents(mapped) == [
        "Termin",
        "Erster Teil vor dem Anhang.",
        "Zweiter Teil nach dem Anhang: der Termin ist am Freitag.",
    ]
    assert mapped.attachments == (
        Attachment(mailfiles.PDF_CONTENT, "Termin.pdf", "application/pdf"),
    )


def test_a_text_part_with_a_file_name_is_an_attachment_not_the_body() -> None:
    """A `.txt` with `filename=` or only `name=` is a file someone attached;
    the HTML beside it is the mail's text."""
    mapped = _map("html_with_text_attachments")
    assert _contents(mapped) == ["Notizen", "Hier der eigentliche Text der Mail."]
    assert mapped.attachments == (
        Attachment(b"Inhalt der Notiz.", "notiz.txt", "text/plain"),
        Attachment(b"Inhalt der Liste.", "liste.txt", "text/plain"),
    )


def test_an_empty_plain_part_gives_way_to_the_html_beside_it() -> None:
    mapped = _map("alternative_empty_plain")
    assert _contents(mapped) == ["Ihre Anfrage", "Der ganze Text steht nur hier."]
    assert mapped.attachments == ()


def test_html_with_an_inline_image_is_the_body_and_the_image_an_attachment() -> None:
    """Outlook's shape: an empty text part, and the HTML in a related part
    whose `start` names it although the image stands first."""
    mapped = _map("alternative_related")
    assert _contents(mapped) == ["Mit Logo", "Text neben dem Logo."]
    assert _body(mapped) == [_part("text/html", "utf-8", "utf-8", converter=_converter())]
    assert mapped.attachments == (Attachment(mailfiles.PNG_CONTENT, "logo.png", "image/png"),)


def test_a_related_part_without_start_begins_with_its_body() -> None:
    mapped = _map("related_without_start")
    assert _contents(mapped) == ["Logo ohne start", "Nur HTML, das Logo danach."]
    assert mapped.attachments == (Attachment(mailfiles.PNG_CONTENT, None, "image/png"),)


def test_an_lf_copy_of_a_mail_is_the_same_artifact() -> None:
    """The same mail saved with LF only, as an `.eml` file on a Unix
    machine, is no variant of the one IMAP delivers with CRLF."""
    crlf = _map("plain").event
    lf = _map("plain_lf").event
    assert lf.external_id == crlf.external_id
    assert lf.artifact_hash == crlf.artifact_hash


def test_an_lf_copy_of_a_forward_is_the_same_artifact() -> None:
    """The attached mail is text with line endings too: its raw bytes enter
    the outer identity with every line ending as LF."""
    crlf = _map("forwarded")
    raw = mailfiles.FORWARDED.replace(b"\r\n", b"\n")
    lf = map_mail(raw, internaldate=INTERNALDATE, found_in=FOUND_IN)
    assert lf.event.artifact_hash == crlf.event.artifact_hash
    assert lf.inner[0].event.artifact_hash == crlf.inner[0].event.artifact_hash


def test_the_body_hash_covers_every_chosen_part_in_order() -> None:
    expected = artifact_hash_of(
        {
            "subject": "Termin",
            "body": [
                _body_digest(b"Erster Teil vor dem Anhang."),
                _body_digest(b"Zweiter Teil nach dem Anhang: der Termin ist am Freitag."),
            ],
            "attachments": [_sha(mailfiles.PDF_CONTENT)],
        }
    )
    assert _map("apple_split").event.artifact_hash == expected


# --- charsets (ruling T2-e) --------------------------------------------------


def test_iso_8859_1_is_read_as_windows_1252() -> None:
    """The euro sign, the German quotes and the dash survive the label."""
    mapped = _map("charset_latin1_label")
    assert _contents(mapped)[1] == mailfiles.CP1252_TEXT
    assert _body(mapped) == [
        {
            "part": "text/plain",
            "charset": "windows-1252",
            "declared": "iso-8859-1",
            "guessed": False,
            "converter": None,
            "replaced": False,
        }
    ]


@pytest.mark.parametrize(
    ("name", "text", "charset", "declared"),
    [
        ("charset_undeclared", "Grüße aus Wien", "utf-8", None),
        ("charset_ascii_8bit", "für Müller", "utf-8", "us-ascii"),
        ("charset_unknown_utf8", "Grüße aus Linz", "utf-8", "unknown-8bit"),
        ("charset_unknown", "Grüße aus Graz.", "windows-1252", "x-mac-klingon"),
        ("charset_undefined_byte", "Preis € 5, Zeichen \x81.", "windows-1252", None),
    ],
)
def test_a_charset_that_cannot_be_trusted_is_guessed_and_says_so(
    name: str, text: str, charset: str, declared: str | None
) -> None:
    """Strict UTF-8 first, Windows-1252 next, and Latin-1 for the five bytes
    Windows-1252 leaves undefined. Nothing is replaced, so `replaced` stays
    false; `guessed` says the charset is a guess."""
    mapped = _map(name)
    assert _contents(mapped)[1] == text
    assert _body(mapped) == [
        {
            "part": "text/plain",
            "charset": charset,
            "declared": declared,
            "guessed": True,
            "converter": None,
            "replaced": False,
        }
    ]


# --- a mail that does not map (rulings T2-b and T2-f) ------------------------


def test_a_mail_that_does_not_map_becomes_an_event_from_what_is_safe() -> None:
    """The unit names the class of the error and nothing of its message,
    which can quote a header."""
    raw = mailfiles.UNREADABLE_HEADER
    mapped = _map("unreadable_header")
    event = mapped.event
    assert event.source == "email"
    assert event.external_id == "sha256:" + _sha(raw)
    assert event.artifact_hash == hashlib.sha256(raw).digest()
    assert event.occurred_at == INTERNALDATE
    assert _contents(mapped) == ["unreadable mail: UnicodeEncodeError"]
    assert mapped.raw == raw
    assert mapped.attachments == ()
    assert mapped.inner == ()
    assert event.channel_identities == ()


def test_an_inner_mail_that_does_not_map_does_not_sink_the_outer_one() -> None:
    mapped = _map("forwarded_unreadable")
    assert _contents(mapped) == ["Fwd: kaputt", "Siehe unten, die Mail lässt sich nicht öffnen."]
    (inner,) = mapped.inner
    inner_raw = mailfiles.UNREADABLE_HEADER.removesuffix(b"\r\n")
    assert inner.raw == inner_raw
    assert inner.event.external_id == "sha256:" + _sha(inner_raw)
    assert inner.event.payload["forwarded_in"] == "fwd-unreadable@example.org"
    assert _contents(inner) == ["unreadable mail: UnicodeEncodeError"]


# --- headers (ruling T2-g) ---------------------------------------------------


def test_a_replaced_character_in_the_subject_is_noted() -> None:
    mapped = _map("subject_replaced")
    assert _contents(mapped)[0] == "Gr\ufffd\ufffde"
    assert mapped.event.payload["headers_replaced"] == ["Subject"]
    # Control: a mail with nothing replaced carries no such note.
    assert "headers_replaced" not in _map("plain").event.payload


def test_a_subject_folded_with_a_tab_is_the_same_subject() -> None:
    line = b"Subject: =?utf-8?q?Angebot_f=C3=BCr_den_Relaunch?="
    hashes = {
        map_mail(
            mailfiles.PLAIN.replace(line, b"Subject: Angebot zum" + fold + b"Relaunch"),
            internaldate=INTERNALDATE,
            found_in=FOUND_IN,
        ).event.artifact_hash
        for fold in (b" ", b"\r\n ", b"\r\n\t", b"\r\n  \t")
    }
    assert len(hashes) == 1


def test_the_identity_does_not_depend_on_the_transfer_encoding() -> None:
    """An MTA that downgrades 8bit to quoted-printable, or a client that
    writes base64, sends the same mail."""
    head = mailfiles.PLAIN.removesuffix(mailfiles.PLAIN_BODY)
    base64_body = b"\r\n".join(mailfiles.base64_lines(mailfiles.PLAIN_BODY)) + b"\r\n"
    plain = _map("plain")
    for encoding, body in (
        (b"quoted-printable", quopri.encodestring(mailfiles.PLAIN_BODY)),
        (b"base64", base64_body),
    ):
        header = b"Content-Transfer-Encoding: " + encoding
        raw = head.replace(b"Content-Transfer-Encoding: 8bit", header) + body
        mapped = map_mail(raw, internaldate=INTERNALDATE, found_in=FOUND_IN)
        assert _contents(mapped) == _contents(plain)
        assert mapped.event.artifact_hash == plain.event.artifact_hash
