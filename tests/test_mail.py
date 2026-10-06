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
    assert event.payload["body"] == {
        "part": "text/plain",
        "charset": "utf-8",
        "converter": None,
        "replaced": False,
    }
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
    """Both `Received` lines, names as written, values unfolded and with
    encoded words decoded, and otherwise as written: `"Office"` keeps its
    quotes, `charset=utf-8` gets none."""
    assert _map("plain").event.payload["headers"] == [
        [
            "Received",
            "from mx.example.net (mx.example.net [192.0.2.10])"
            "\tby mail.example.org with ESMTPS id 4F2A1; Mon, 05 Oct 2026 10:15:04 +0200",
        ],
        [
            "Received",
            "from client.example.net ([198.51.100.7])"
            "\tby mx.example.net with ESMTPSA; Mon, 05 Oct 2026 10:15:02 +0200",
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
    """Spelled out: the decoded subject, the SHA-256 of the body part's bytes
    after the transfer encoding and before any conversion, and the sorted
    SHA-256 of every attachment — here none."""
    expected = artifact_hash_of(
        {
            "subject": "Angebot für den Relaunch",
            "body": _sha(mailfiles.PLAIN_BODY),
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
    assert mapped.event.payload["body"] == {
        "part": "text/html",
        "charset": "windows-1252",
        "converter": _converter(),
        "replaced": False,
    }


def test_the_body_hash_of_html_is_taken_before_the_conversion() -> None:
    """The identity does not depend on the converter: the hash is over the
    windows-1252 bytes the quoted-printable decodes to."""
    expected = artifact_hash_of(
        {
            "subject": "AW: Angebot für den Relaunch",
            "body": _sha(quopri.decodestring(mailfiles.HTML_ONLY_QP)),
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
    assert mapped.event.payload["body"] == {
        "part": "text/plain",
        "charset": "utf-8",
        "converter": None,
        "replaced": False,
    }
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


def test_an_unknown_charset_is_read_as_latin_1_and_says_so() -> None:
    mapped = _map("charset_unknown")
    assert _contents(mapped) == ["Gruss aus Graz", "Grüße aus Graz."]
    assert mapped.event.payload["body"] == {
        "part": "text/plain",
        "charset": "iso-8859-1",
        "converter": None,
        "replaced": True,
    }


def test_a_null_byte_and_an_unreadable_byte_become_the_replacement_character() -> None:
    mapped = _map("body_unreadable")
    assert _contents(mapped) == [
        "Invoice 17",
        "Rechnung Nr. 17\ufffd liegt bei.",
        "Betrag: 120 \ufffd EUR",
    ]
    body = mapped.event.payload["body"]
    assert body == {"part": "text/plain", "charset": "utf-8", "converter": None, "replaced": True}


def test_the_body_hash_is_over_the_bytes_not_over_the_replaced_text() -> None:
    expected = artifact_hash_of(
        {
            "subject": "Invoice 17",
            "body": _sha(mailfiles.BODY_UNREADABLE_BODY),
            "attachments": [],
        }
    )
    assert _map("body_unreadable").event.artifact_hash == expected


def test_a_lone_surrogate_in_a_body_becomes_the_replacement_character() -> None:
    mapped = _map("body_lone_surrogate")
    assert _contents(mapped)[1] == "Smiley \ufffd here."
    assert mapped.event.payload["body"] == {
        "part": "text/plain",
        "charset": "utf-7",
        "converter": None,
        "replaced": True,
    }


def test_header_bytes_outside_ascii_are_read_as_utf_8_or_replaced() -> None:
    """UTF-8 in a header reads as UTF-8, in the subject as in a display
    name; Latin-1 and a null byte become the replacement character."""
    mapped = _map("headers_8bit")
    assert _contents(mapped)[0] == "Grüße aus Köln"
    assert mapped.event.channel_identities[:2] == (
        ChannelIdentity("email", "from", "juergen.mueller@example.net", "Jürgen Müller"),
        ChannelIdentity("email", "sender", "joerg@example.net", "J\ufffdrg"),
    )
    headers = _headers(mapped)
    assert ["X-Note", "Gr\ufffd\ufffde"] in headers
    assert ["X-Null", "a\ufffdb"] in headers


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
    assert mapped.event.payload["body"] is None
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
            "body": None,
            "attachments": sorted([_sha(mailfiles.PDF_CONTENT), _sha(mailfiles.PNG_CONTENT)]),
        }
    )
    assert mapped.event.artifact_hash == expected


def test_a_mail_with_nothing_but_a_subject_says_it_is_empty() -> None:
    """Without a `Content-Type` a mail is `text/plain` in US-ASCII (RFC
    2045), so it has a body part — an empty one."""
    mapped = _map("empty")
    assert _contents(mapped) == ["Rückruf bitte / please call back", "no readable body: empty"]
    assert mapped.event.payload["body"] == {
        "part": "text/plain",
        "charset": "us-ascii",
        "converter": None,
        "replaced": False,
    }


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
            "body": _sha(b"Das Angebot, einmal unter jedem Namen."),
            "attachments": [_sha(mailfiles.PDF_CONTENT)] * 2,
        }
    )
    assert mapped.event.artifact_hash == expected


# --- broken MIME -------------------------------------------------------------


@pytest.mark.parametrize("name", ["broken_mime", "broken_mime_no_boundary"])
def test_a_multipart_without_a_findable_boundary_is_read_as_text(name: str) -> None:
    """No part can be found, so the whole body is the text: the MIME lines
    stand in it, and so does every word of the mail. Undeclared, the
    charset is US-ASCII, and the `ä` is replaced and says so."""
    mapped = _map(name)
    contents = _contents(mapped)
    assert contents[0] == "Protokoll Baubesprechung"
    assert "Protokoll der Baubesprechung vom 1. Oktober." in contents
    assert any(content.startswith("N\ufffd\ufffdchster Termin") for content in contents)
    assert mapped.event.payload["body"] == {
        "part": "multipart/mixed",
        "charset": "us-ascii",
        "converter": None,
        "replaced": True,
    }


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
            "body": _sha(b""),
            "attachments": [_sha(mailfiles.FORWARDED_INNER)],
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
