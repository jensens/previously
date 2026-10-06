# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The test mails under `tests/mails/`, as the bytes they are made of.

Every mail here is invented, German and English mixed, and none is anybody's
real mail: the repository is public. The files exist because a mail reaches
the mapping as bytes — from IMAP, and later as an `.eml` file in a folder —
and this module exists because the bytes are what a reviewer has to see:
line endings, 8-bit header bytes and base64 are invisible in an editor.

`test_mail.py` holds every file against `MAILS`, so a file and this module
cannot drift apart. To write the files again::

    uv run python tests/mailfiles.py

Every mail ends in exactly one CRLF and no line carries trailing blanks, so
the `trailing-whitespace` and `end-of-file-fixer` hooks of the pre-commit
configuration leave the files as they are.
"""

import base64
import pathlib
import quopri


CRLF = b"\r\n"
HERE = pathlib.Path(__file__).resolve().parent / "mails"


def _lines(*lines: str | bytes) -> bytes:
    """Lines joined with CRLF, the line ending IMAP delivers, and ended with
    one. A `str` line is UTF-8; a `bytes` line goes in as it stands, for the
    cases that need bytes no encoding produces."""
    encoded = [line.encode() if isinstance(line, str) else line for line in lines]
    return CRLF.join(encoded) + CRLF


def _base64_lines(data: bytes) -> list[bytes]:
    """`data` in base64, in lines of 76 characters as MIME has them."""
    text = base64.b64encode(data)
    return [text[i : i + 76] for i in range(0, len(text), 76)]


def _without_final_crlf(mail: bytes) -> bytes:
    """A mail as it stands inside a multipart: the line ending before the
    next delimiter belongs to the delimiter, not to the part."""
    return mail.removesuffix(CRLF)


# The body of the simple mail, as bytes, so that a test can compute the
# artifact hash from it without asking the code under test.
PLAIN_BODY = _lines(
    "Liebe Eva,",
    "",
    "anbei die Eckpunkte für den Relaunch. The budget stays as discussed, the",
    "timeline moves by two weeks.",
    "",
    "Schöne Grüße",
    "Jürgen",
    "",
    "--",
    "Jürgen Müller · Example Studio",
)

_PLAIN_HEADERS = (
    "To: Eva Huber <eva.huber@example.org>, team@example.org",
    "From: =?utf-8?q?J=C3=BCrgen_M=C3=BCller?= <juergen.mueller@example.net>",
    'Cc: "Office" <office@example.org>',
    "Reply-To: projekte@example.net",
    "Subject: =?utf-8?q?Angebot_f=C3=BCr_den_Relaunch?=",
    "Date: Mon, 05 Oct 2026 10:15:00 +0200",
    "Message-ID: <20261005101500.4711@example.net>",
    "MIME-Version: 1.0",
    "Content-Type: text/plain; charset=utf-8",
    "Content-Transfer-Encoding: 8bit",
)

PLAIN = (
    _lines(
        "Received: from mx.example.net (mx.example.net [192.0.2.10])",
        "\tby mail.example.org with ESMTPS id 4F2A1; Mon, 05 Oct 2026 10:15:04 +0200",
        "Received: from client.example.net ([198.51.100.7])",
        "\tby mx.example.net with ESMTPSA; Mon, 05 Oct 2026 10:15:02 +0200",
        *_PLAIN_HEADERS,
        "",
    )
    + PLAIN_BODY
)

# The same mail as it arrived in a second mailbox: other transport lines,
# the same content.
PLAIN_OTHER_TRANSPORT = (
    _lines(
        "Return-Path: <juergen.mueller@example.net>",
        "Delivered-To: office@example.org",
        "Received: from mx2.example.net (mx2.example.net [192.0.2.20])",
        "\tby mail.example.org with ESMTPS id 9C3B7; Mon, 05 Oct 2026 10:15:09 +0200",
        *_PLAIN_HEADERS,
        "",
    )
    + PLAIN_BODY
)

# The same Message-ID with another body, as a mailing list or a forger
# would produce it.
PLAIN_OTHER_BODY = _lines(*_PLAIN_HEADERS, "") + PLAIN_BODY.replace(
    b"by two weeks", b"by three weeks"
)

# Outlook: HTML only, windows-1252 in quoted-printable, an entity for the
# umlaut, empty paragraphs of a non-breaking space, and a tracking pixel.
HTML_ONLY_QP = _lines(
    '<html xmlns:o=3D"urn:schemas-microsoft-com:office:office"><head>',
    "<style><!-- p.MsoNormal {margin:0cm;} --></style></head>",
    "<body lang=3DDE><div class=3DWordSection1>",
    "<p class=3DMsoNormal>Hallo J=FCrgen,<o:p></o:p></p>",
    "<p class=3DMsoNormal><o:p>&nbsp;</o:p></p>",
    "<p class=3DMsoNormal>danke f&uuml;r das Angebot. We accept the new timel=",
    "ine.<o:p></o:p></p>",
    "<p class=3DMsoNormal><o:p>&nbsp;</o:p></p>",
    "<p class=3DMsoNormal>Viele Gr=FC=DFe<br>Eva<o:p></o:p></p>",
    '<p class=3DMsoNormal><img src=3D"https://tracker.example.com/open.gif" width=',
    "=3D1 height=3D1><o:p></o:p></p>",
    "</div></body></html>",
)

HTML_ONLY = (
    _lines(
        "From: Eva Huber <eva.huber@example.org>",
        "To: =?iso-8859-1?q?J=FCrgen_M=FCller?= <juergen.mueller@example.net>",
        "Subject: =?windows-1252?q?AW=3A_Angebot_f=FCr_den_Relaunch?=",
        "Date: Tue, 06 Oct 2026 09:02:11 +0000",
        "Message-ID: <AM0PR01MB1234ABCD@example.org>",
        "MIME-Version: 1.0",
        'Content-Type: text/html; charset="windows-1252"',
        "Content-Transfer-Encoding: quoted-printable",
        "",
    )
    + HTML_ONLY_QP
)

_BLOCKQUOTE_HTML = (
    '<div dir="ltr">Thanks, that works for us.<div><br></div><div>Best, Lea</div></div>'
    '<br><div class="gmail_quote"><div dir="ltr" class="gmail_attr">'
    "On Mon, Oct 5, 2026 at 10:00 AM Max wrote:<br></div>"
    '<blockquote class="gmail_quote" style="margin:0px 0px 0px 0.8ex">'
    '<div dir="ltr">Können wir am Donnerstag telefonieren?<br><br>Gruß, Max</div>'
    "</blockquote></div>"
)

HTML_BLOCKQUOTE = _lines(
    "From: Lea Bauer <lea@example.com>",
    "To: max@example.net",
    "Subject: Re: Call on Thursday?",
    "Date: Wed, 07 Oct 2026 16:45:00 -0400",
    "Message-ID: <CAF+lea-20261007@mail.example.com>",
    "MIME-Version: 1.0",
    'Content-Type: text/html; charset="UTF-8"',
    "Content-Transfer-Encoding: base64",
    "",
    *_base64_lines(_BLOCKQUOTE_HTML.encode()),
)

NO_MESSAGE_ID = _lines(
    "From: scanner@example.org",
    "To: office@example.org",
    "Subject: Scan vom Kopierer",
    "Date: Fri, 02 Oct 2026 07:30:00 +0200",
    "Content-Type: text/plain; charset=us-ascii",
    "",
    "Scanned document, 3 pages.",
)

DATE_UNREADABLE = _lines(
    "From: Oma Huber <oma@example.org>",
    "To: eva.huber@example.org",
    "Subject: Sonntag",
    "Date: Montag, 5. Oktober 2026, 10 Uhr",
    "Message-ID: <oma-sonntag@example.org>",
    "Content-Type: text/plain; charset=utf-8",
    "",
    "Kommt ihr am Sonntag zum Essen?",
)

# RFC 5322 says `-0000` means the time carries no zone information, and
# Python reads it as a naive datetime.
DATE_WITHOUT_ZONE = _lines(
    "From: build@example.org",
    "To: team@example.org",
    "Subject: Nightly build green",
    "Date: Mon, 05 Oct 2026 23:00:00 -0000",
    "Message-ID: <build-1234@example.org>",
    "Content-Type: text/plain; charset=us-ascii",
    "",
    "All 412 checks passed.",
)

DATE_MISSING = _lines(
    "From: printer@example.org",
    "To: office@example.org",
    "Subject: Toner low",
    "Message-ID: <printer-toner@example.org>",
    "Content-Type: text/plain; charset=us-ascii",
    "",
    "Cartridge K is at 5 percent.",
)

CHARSET_UNKNOWN = _lines(
    "From: graz@example.at",
    "To: eva.huber@example.org",
    "Subject: Gruss aus Graz",
    "Date: Sat, 03 Oct 2026 12:00:00 +0200",
    "Message-ID: <graz-1@example.at>",
    'Content-Type: text/plain; charset="x-mac-klingon"',
    "Content-Transfer-Encoding: 8bit",
    "",
    b"Gr\xfc\xdfe aus Graz.",
)

# A null byte and a byte that is no UTF-8, under a declared UTF-8.
BODY_UNREADABLE_BODY = _lines(
    b"Rechnung Nr. 17\x00 liegt bei.",
    b"",
    b"Betrag: 120 \xff EUR",
)

BODY_UNREADABLE = (
    _lines(
        "From: billing@example.com",
        "To: office@example.org",
        "Subject: Invoice 17",
        "Date: Thu, 01 Oct 2026 08:00:00 +0200",
        "Message-ID: <invoice-17@example.com>",
        "Content-Type: text/plain; charset=utf-8",
        "Content-Transfer-Encoding: 8bit",
        "",
    )
    + BODY_UNREADABLE_BODY
)

# UTF-7 can spell half of a surrogate pair, which no codec turns into a
# character: Python decodes `+2D0-` to a lone U+D83D. Malformed, and the
# one way found to put a lone surrogate into a body.
BODY_LONE_SURROGATE = _lines(
    "From: legacy@example.org",
    "To: office@example.org",
    "Subject: Legacy client",
    "Date: Thu, 01 Oct 2026 09:00:00 +0200",
    "Message-ID: <legacy-utf7@example.org>",
    'Content-Type: text/plain; charset="utf-7"',
    "",
    "Smiley +2D0- here.",
)

# Header bytes outside ASCII: UTF-8 as RFC 6532 allows it, Latin-1 as an
# old mailer writes it, and a null byte.
HEADERS_8BIT = _lines(
    b"From: J\xc3\xbcrgen M\xc3\xbcller <juergen.mueller@example.net>",
    b"Sender: J\xf6rg <joerg@example.net>",
    b"To: eva.huber@example.org",
    b"Subject: Gr\xc3\xbc\xc3\x9fe aus K\xc3\xb6ln",
    b"X-Note: Gr\xfc\xdfe",
    b"X-Null: a\x00b",
    b"Date: Sun, 04 Oct 2026 18:00:00 +0200",
    b"Message-ID: <koeln-1@example.net>",
    b"Content-Type: text/plain; charset=utf-8",
    b"",
    b"Der Dom steht noch.",
)

ENCRYPTED = _lines(
    "From: max@example.net",
    "To: eva.huber@example.org",
    "Subject: Vertrag",
    "Date: Mon, 05 Oct 2026 15:00:00 +0200",
    "Message-ID: <pgp-vertrag@example.net>",
    "MIME-Version: 1.0",
    'Content-Type: multipart/encrypted; protocol="application/pgp-encrypted";',
    ' boundary="enc"',
    "",
    "--enc",
    "Content-Type: application/pgp-encrypted",
    "Content-Description: PGP/MIME version identification",
    "",
    "Version: 1",
    "",
    "--enc",
    'Content-Type: application/octet-stream; name="encrypted.asc"',
    'Content-Disposition: inline; filename="encrypted.asc"',
    "",
    "-----BEGIN PGP MESSAGE-----",
    "",
    "hQEMA0InventedNotARealCiphertextAtAll0123456789abcdefghijklmnopqrstuv",
    "=AbCd",
    "-----END PGP MESSAGE-----",
    "",
    "--enc--",
)

SMIME_CONTENT = b"0\x82\x01\x00invented, not a real PKCS #7 envelope"

ENCRYPTED_SMIME = _lines(
    "From: notar@example.at",
    "To: office@example.org",
    "Subject: Kaufvertrag Entwurf",
    "Date: Mon, 05 Oct 2026 16:00:00 +0200",
    "Message-ID: <smime-kaufvertrag@example.at>",
    "MIME-Version: 1.0",
    'Content-Type: application/pkcs7-mime; smime-type=enveloped-data; name="smime.p7m"',
    "Content-Transfer-Encoding: base64",
    'Content-Disposition: attachment; filename="smime.p7m"',
    "",
    *_base64_lines(SMIME_CONTENT),
)

# A subject, and nothing else: no body, no attachment. RFC 5322 needs the
# blank line only before a body, and there is none.
EMPTY = _lines(
    "From: max@example.net",
    "To: eva.huber@example.org",
    "Subject: Rückruf bitte / please call back",
    "Date: Tue, 06 Oct 2026 08:15:00 +0200",
    "Message-ID: <rueckruf@example.net>",
)

PDF_CONTENT = b"%PDF-1.7\n% invented, not a real document\n%%EOF\n"
PNG_CONTENT = b"\x89PNG\r\n\x1a\n invented, not a real image"

ATTACHMENTS_ONLY = _lines(
    "From: scanner@example.org",
    "To: office@example.org",
    "Date: Fri, 02 Oct 2026 07:35:00 +0200",
    "Message-ID: <scan-2@example.org>",
    "MIME-Version: 1.0",
    'Content-Type: multipart/mixed; boundary="att"',
    "",
    "--att",
    'Content-Type: application/pdf; name="Angebot.pdf"',
    "Content-Transfer-Encoding: base64",
    'Content-Disposition: attachment; filename="Angebot.pdf"',
    "",
    *_base64_lines(PDF_CONTENT),
    "--att",
    'Content-Type: image/png; name="plan.png"',
    "Content-Transfer-Encoding: base64",
    'Content-Disposition: attachment; filename="plan.png"',
    "",
    *_base64_lines(PNG_CONTENT),
    "--att--",
)

SIGNATURE = _lines(
    "-----BEGIN PGP SIGNATURE-----",
    "",
    "iQEzBAEBCAAdInventedNotARealSignature0123456789",
    "=XyZw",
    "-----END PGP SIGNATURE-----",
)

SIGNED = _lines(
    "From: max@example.net",
    "To: team@example.org",
    "Subject: Freigabe Version 2",
    "Date: Tue, 06 Oct 2026 11:00:00 +0200",
    "Message-ID: <pgp-freigabe@example.net>",
    "MIME-Version: 1.0",
    'Content-Type: multipart/signed; micalg=pgp-sha256; protocol="application/pgp-signature";',
    ' boundary="sig"',
    "",
    "--sig",
    "Content-Type: text/plain; charset=utf-8",
    "Content-Transfer-Encoding: quoted-printable",
    "",
    "Hallo Team,",
    "",
    "die Freigabe f=C3=BCr Version 2 ist erteilt.",
    "",
    "Max",
    "--sig",
    'Content-Type: application/pgp-signature; name="signature.asc"',
    'Content-Disposition: attachment; filename="signature.asc"',
    "",
    _without_final_crlf(SIGNATURE),
    "--sig--",
)

REPLY = _lines(
    "From: Eva Huber <eva.huber@example.org>",
    "To: =?utf-8?q?J=C3=BCrgen_M=C3=BCller?= <juergen.mueller@example.net>",
    "Subject: =?utf-8?q?Re=3A_Angebot_f=C3=BCr_den_Relaunch?=",
    "Date: Mon, 05 Oct 2026 11:02:00 +0200",
    "Message-ID: <reply-relaunch@example.org>",
    "In-Reply-To: <20261005101500.4711@example.net>",
    "References: <20261001080000.1@example.org>",
    " <20261005101500.4711@example.net>",
    "MIME-Version: 1.0",
    'Content-Type: multipart/alternative; boundary="alt"',
    "",
    "--alt",
    "Content-Type: text/plain; charset=utf-8",
    "Content-Transfer-Encoding: 8bit",
    "",
    "Hallo Jürgen,",
    "",
    "passt, wir nehmen den neuen Zeitplan.",
    "",
    "Eva",
    "",
    "Am 05.10.2026 um 10:15 schrieb Jürgen Müller:",
    "> Liebe Eva,",
    ">",
    "> anbei die Eckpunkte für den Relaunch.",
    "--alt",
    "Content-Type: text/html; charset=utf-8",
    "Content-Transfer-Encoding: 8bit",
    "",
    "<p>Hallo Jürgen,</p><p>passt, wir nehmen den neuen Zeitplan.</p><p>Eva</p>",
    "--alt--",
)

INVOICE_PDF = b"%PDF-1.7\n% invented invoice, October\n%%EOF\n"

# The mail that gets forwarded. Its sender's display name is raw UTF-8, so
# that only the bytes as they stand reproduce it: re-serialising the parsed
# mail writes that header as an encoded word.
FORWARDED_INNER = _without_final_crlf(
    _lines(
        b"From: Buchhaltung M\xc3\xbcller GmbH <buchhaltung@example.com>",
        b"To: eva.huber@example.org",
        b"Subject: Rechnung Oktober",
        b"Date: Wed, 30 Sep 2026 14:20:00 +0200",
        b"Message-ID: <invoice-2026-10@example.com>",
        b"MIME-Version: 1.0",
        b'Content-Type: multipart/mixed; boundary="inner"',
        b"",
        b"--inner",
        b"Content-Type: text/plain; charset=utf-8",
        b"Content-Transfer-Encoding: 8bit",
        b"",
        "Sehr geehrte Frau Huber,",
        b"",
        "anbei die Rechnung für Oktober.",
        b"",
        "Mit freundlichen Grüßen",
        b"Buchhaltung",
        b"--inner",
        b'Content-Type: application/pdf; name="Rechnung-2026-10.pdf"',
        b"Content-Transfer-Encoding: base64",
        b'Content-Disposition: attachment; filename="Rechnung-2026-10.pdf"',
        b"",
        *_base64_lines(INVOICE_PDF),
        b"--inner--",
    )
)

_FORWARDED_FRAME = (
    "From: Eva Huber <eva.huber@example.org>",
    "To: max@example.net",
    "Subject: Fwd: Rechnung Oktober",
    "Date: Thu, 08 Oct 2026 11:00:00 +0200",
    "Message-ID: <fwd-20261008@example.org>",
    "MIME-Version: 1.0",
    'Content-Type: multipart/mixed; boundary="outer"',
    "",
    "--outer",
    "Content-Type: text/plain; charset=utf-8",
    "",
    "",
    "--outer",
)

# Forwarded as an attachment, by a client that writes an empty frame mail.
FORWARDED = _lines(
    *_FORWARDED_FRAME,
    "Content-Type: message/rfc822",
    'Content-Disposition: attachment; filename="Rechnung Oktober.eml"',
    "",
    FORWARDED_INNER,
    "--outer--",
)

# The same, with the attached mail in base64. RFC 2046 does not allow an
# encoding other than 7bit, 8bit or binary for message/rfc822, and some
# clients write it anyway.
FORWARDED_BASE64 = _lines(
    *_FORWARDED_FRAME,
    "Content-Type: message/rfc822",
    "Content-Transfer-Encoding: base64",
    'Content-Disposition: attachment; filename="Rechnung Oktober.eml"',
    "",
    *_base64_lines(FORWARDED_INNER),
    "--outer--",
)

# The same in quoted-printable, which RFC 2046 does not allow here either.
FORWARDED_QUOTED_PRINTABLE = _lines(
    *_FORWARDED_FRAME,
    "Content-Type: message/rfc822",
    "Content-Transfer-Encoding: quoted-printable",
    'Content-Disposition: attachment; filename="Rechnung Oktober.eml"',
    "",
    quopri.encodestring(FORWARDED_INNER),
    "--outer--",
)

NESTED_LEVELS = 6


def nested(level: int) -> bytes:
    """A mail at `level` that carries the mail of the next level as an
    attachment, down to `NESTED_LEVELS`, which carries none. Ends without the
    final CRLF below the top, as a mail inside a multipart stands."""
    head = (
        f"From: level{level}@example.org",
        "To: office@example.org",
        f"Subject: Ebene {level} / level {level}",
        f"Date: Mon, {level + 1:02d} Nov 2026 09:00:00 +0100",
        f"Message-ID: <level-{level}@example.org>",
        "MIME-Version: 1.0",
    )
    if level == NESTED_LEVELS:
        mail = _lines(
            *head, "Content-Type: text/plain; charset=utf-8", "", f"Text der Ebene {level}."
        )
    else:
        boundary = f"level-{level}"
        mail = _lines(
            *head,
            f'Content-Type: multipart/mixed; boundary="{boundary}"',
            "",
            f"--{boundary}",
            "Content-Type: text/plain; charset=utf-8",
            "",
            f"Text der Ebene {level}.",
            f"--{boundary}",
            "Content-Type: message/rfc822",
            "",
            nested(level + 1),
            f"--{boundary}--",
        )
    return mail if level == 0 else _without_final_crlf(mail)


# The boundary is declared as "=_part_7", and the delimiters say
# "=_part_8": no part can be found.
BROKEN_MIME = _lines(
    "From: bauleitung@example.at",
    "To: office@example.org",
    "Subject: Protokoll Baubesprechung",
    "Date: Fri, 02 Oct 2026 17:00:00 +0200",
    "Message-ID: <protokoll-7@example.at>",
    "MIME-Version: 1.0",
    'Content-Type: multipart/mixed; boundary="=_part_7"',
    "",
    "--=_part_8",
    "Content-Type: text/plain; charset=utf-8",
    "",
    "Protokoll der Baubesprechung vom 1. Oktober.",
    "",
    "Nächster Termin: 15. Oktober.",
    "--=_part_8--",
)

# A multipart without any boundary parameter.
BROKEN_MIME_NO_BOUNDARY = BROKEN_MIME.replace(
    b'multipart/mixed; boundary="=_part_7"', b"multipart/mixed"
).replace(b"<protokoll-7@", b"<protokoll-8@")

# Cut off in the middle of the attachment: no closing delimiter, and the
# base64 ends where the transfer stopped.
BROKEN_MIME_TRUNCATED = _lines(
    "From: bauleitung@example.at",
    "To: office@example.org",
    "Subject: Plan Erdgeschoss",
    "Date: Fri, 02 Oct 2026 17:05:00 +0200",
    "Message-ID: <plan-eg@example.at>",
    "MIME-Version: 1.0",
    'Content-Type: multipart/mixed; boundary="cut"',
    "",
    "--cut",
    "Content-Type: text/plain; charset=utf-8",
    "",
    "Anbei der Plan fürs Erdgeschoss.",
    "--cut",
    'Content-Type: application/pdf; name="EG.pdf"',
    "Content-Transfer-Encoding: base64",
    'Content-Disposition: attachment; filename="EG.pdf"',
    "",
    base64.b64encode(PDF_CONTENT)[:30],
)

DUPLICATE_ATTACHMENTS = _lines(
    "From: max@example.net",
    "To: eva.huber@example.org",
    "Subject: Angebot, zweimal",
    "Date: Tue, 06 Oct 2026 14:00:00 +0200",
    "Message-ID: <angebot-zweimal@example.net>",
    "MIME-Version: 1.0",
    'Content-Type: multipart/mixed; boundary="dup"',
    "",
    "--dup",
    "Content-Type: text/plain; charset=utf-8",
    "",
    "Das Angebot, einmal unter jedem Namen.",
    "--dup",
    'Content-Type: application/pdf; name="Angebot.pdf"',
    "Content-Transfer-Encoding: base64",
    'Content-Disposition: attachment; filename="Angebot.pdf"',
    "",
    *_base64_lines(PDF_CONTENT),
    "--dup",
    "Content-Type: application/pdf",
    "Content-Transfer-Encoding: base64",
    "Content-Disposition: attachment;",
    " filename*=utf-8''Angebot%20f%C3%BCr%20M%C3%BCller.pdf",
    "",
    *_base64_lines(PDF_CONTENT),
    "--dup--",
)

MAILS: dict[str, bytes] = {
    "plain": PLAIN,
    "plain_other_transport": PLAIN_OTHER_TRANSPORT,
    "plain_other_body": PLAIN_OTHER_BODY,
    "html_only": HTML_ONLY,
    "html_blockquote": HTML_BLOCKQUOTE,
    "no_message_id": NO_MESSAGE_ID,
    "date_unreadable": DATE_UNREADABLE,
    "date_without_zone": DATE_WITHOUT_ZONE,
    "date_missing": DATE_MISSING,
    "charset_unknown": CHARSET_UNKNOWN,
    "body_unreadable": BODY_UNREADABLE,
    "body_lone_surrogate": BODY_LONE_SURROGATE,
    "headers_8bit": HEADERS_8BIT,
    "encrypted": ENCRYPTED,
    "encrypted_smime": ENCRYPTED_SMIME,
    "empty": EMPTY,
    "attachments_only": ATTACHMENTS_ONLY,
    "signed": SIGNED,
    "reply": REPLY,
    "forwarded": FORWARDED,
    "forwarded_base64": FORWARDED_BASE64,
    "forwarded_quoted_printable": FORWARDED_QUOTED_PRINTABLE,
    "nested_six": nested(0),
    "broken_mime": BROKEN_MIME,
    "broken_mime_no_boundary": BROKEN_MIME_NO_BOUNDARY,
    "broken_mime_truncated": BROKEN_MIME_TRUNCATED,
    "duplicate_attachments": DUPLICATE_ATTACHMENTS,
}


def main() -> None:
    HERE.mkdir(exist_ok=True)
    for name, mail in MAILS.items():
        (HERE / f"{name}.eml").write_bytes(mail)


if __name__ == "__main__":
    main()
