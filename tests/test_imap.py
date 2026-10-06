# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The IMAP connector against a real IMAP server, GreenMail in a container,
and the run it feeds against real PostgreSQL and a real S3 server.

The folder every test starts from is `Kunde Müller` with four invented mails
out of `tests/mails/` at UIDs 1 to 4 (`conftest.py`). Every connection is
verified: the context trusts the certificate the container made for this
run, and the host name has to match it.
"""

from datetime import datetime
from datetime import timedelta
from datetime import timezone
from datetime import UTC
from hypothesis import given
from hypothesis import strategies as st
from mailserver import MailServer
from mailserver import Relay
from pathlib import Path
from previously.connectors.imap import decode_folder
from previously.connectors.imap import encode_folder
from previously.connectors.imap import ImapConnector
from previously.connectors.imap import ImapError
from previously.connectors.imap import parse_internaldate
from previously.contract.types import Watermark
from previously.core.ingest import ingest
from previously.core.sealing import recipient_of
from previously.storage.postgres import PostgresStorage
from typing import TYPE_CHECKING

import pytest
import secrets
import socket
import ssl
import threading


if TYPE_CHECKING:
    from previously.core.ingest import Ingested
    from previously.storage.s3 import S3BlobStore
    from sqlalchemy import Engine


MAILS = Path(__file__).resolve().parent / "mails"
# The four mails of the folder, in the order `conftest.py` appends them.
FOLDER_MAILS = [
    (MAILS / name).read_bytes()
    for name in ("plain.eml", "reply.eml", "html_only.eml", "forwarded.eml")
]
RECORDED_AT = datetime(2026, 10, 6, 12, 0, 0, tzinfo=UTC)


# --- Folder names --------------------------------------------------------------


def test_a_folder_with_an_umlaut_is_spelled_the_imap_way_and_back() -> None:
    assert encode_folder("Kunde Müller") == "Kunde M&APw-ller"
    assert decode_folder("Kunde M&APw-ller") == "Kunde Müller"


@pytest.mark.parametrize(
    ("name", "spelled"),
    [
        # The example of RFC 3501, section 5.1.3.
        ("~peter/mail/台北/日本語", "~peter/mail/&U,BTFw-/&ZeVnLIqe-"),
        ("Angebote & Rechnungen", "Angebote &- Rechnungen"),
        ("INBOX", "INBOX"),
        ("Ärger", "&AMQ-rger"),
    ],
)
def test_folder_names_are_spelled_by_rfc_3501(name: str, spelled: str) -> None:
    assert encode_folder(name) == spelled
    assert decode_folder(spelled) == name


@pytest.mark.parametrize("spelled", ["Kunde M&APw", "Kunde M&A-ller", "&!!-"])
def test_a_spelling_that_is_not_modified_utf_7_is_refused(spelled: str) -> None:
    with pytest.raises(ValueError, match=r"."):
        decode_folder(spelled)


@given(st.text())
def test_every_folder_name_is_printable_ascii_and_comes_back(name: str) -> None:
    spelled = encode_folder(name)
    assert all(" " <= character <= "~" for character in spelled)
    assert decode_folder(spelled) == name


# --- INTERNALDATE ----------------------------------------------------------------


def _zone(hours: int, minutes: int = 0) -> timezone:
    return timezone(timedelta(hours=hours, minutes=minutes))


@pytest.mark.parametrize(
    ("written", "moment"),
    [
        # A day below ten is padded with a blank, RFC 3501 `date-day-fixed`.
        (" 6-Oct-2026 10:15:00 +0200", datetime(2026, 10, 6, 10, 15, 0, tzinfo=_zone(2))),
        # Both ends of the month table, and a zone on either side of UTC.
        ("05-Jan-2026 23:30:00 -0230", datetime(2026, 1, 5, 23, 30, 0, tzinfo=_zone(-2, -30))),
        ("31-Dec-2026 00:00:59 +0545", datetime(2026, 12, 31, 0, 0, 59, tzinfo=_zone(5, 45))),
        ("29-Feb-2028 12:00:00 +0000", datetime(2028, 2, 29, 12, 0, 0, tzinfo=UTC)),
        # ABNF strings match without regard to case.
        ("06-OCT-2026 10:15:00 +0200", datetime(2026, 10, 6, 10, 15, 0, tzinfo=_zone(2))),
    ],
)
def test_an_internaldate_is_read_as_the_moment_it_names(written: str, moment: datetime) -> None:
    """Compared with `utcoffset` as well as with `==`: two aware datetimes
    are equal when they name the same instant, whatever their zones, and a
    swapped sign would name another instant here, but a zone is what the
    payload writes."""
    parsed = parse_internaldate(written)
    assert parsed == moment
    assert parsed is not None and parsed.utcoffset() == moment.utcoffset()


@pytest.mark.parametrize(
    "written",
    [
        "06-Okt-2026 10:15:00 +0200",  # a German month
        "06-Mai-2026 10:15:00 +0200",
        "30-Feb-2026 10:15:00 +0200",  # a day the month does not have
        "06-Oct-2026 25:15:00 +0200",  # an hour the day does not have
        "06-Oct-2026 10:15:00 +2400",  # a zone that does not exist
        "06-Oct-2026 10:15:00",  # no zone
        "2026-10-06T10:15:00+02:00",  # another form
        "",
    ],
)
def test_a_text_that_names_no_moment_is_no_internaldate(written: str) -> None:
    assert parse_internaldate(written) is None


# --- The connector ---------------------------------------------------------------


@pytest.mark.imap
def test_the_connector_fetches_every_mail_then_only_the_new_ones(
    mail_server: MailServer, imap_folder: str
) -> None:
    connector = mail_server.connector(imap_folder)
    validity = mail_server.uidvalidity(imap_folder)
    assert connector.name == f"imap:pilot@{mail_server.host}/Kunde Müller"

    fetched = list(connector.fetch(None))
    assert [f.raw for f in fetched] == FOLDER_MAILS
    assert [f.position for f in fetched] == [
        {"uidvalidity": validity, "uid": str(uid)} for uid in (1, 2, 3, 4)
    ]
    assert fetched[0].found_in == {"connector": connector.name, "uidvalidity": validity, "uid": "1"}
    assert all(f.internaldate.tzinfo is not None for f in fetched)

    mark = Watermark(connector.name, fetched[-1].position, RECORDED_AT)
    assert list(connector.fetch(mark)) == []
    mail_server.append(imap_folder, (MAILS / "signed.eml").read_bytes())
    new = list(connector.fetch(mark))
    assert [f.position["uid"] for f in new] == ["5"]
    assert new[0].raw == (MAILS / "signed.eml").read_bytes()


@pytest.mark.imap
def test_the_connector_hands_over_the_moment_the_server_received_a_mail(
    mail_server: MailServer, imap_folder: str
) -> None:
    """A mail appended with an INTERNALDATE of its own comes back at that
    instant. GreenMail keeps the instant and writes it in UTC (measured on
    2026-10-06), so this catches the month and the moment, and the unit
    cases above catch the sign of a zone."""
    mail_server.append_dated(
        imap_folder, (MAILS / "signed.eml").read_bytes(), "05-Jan-2026 23:30:00 -0230"
    )
    fetched = list(mail_server.connector(imap_folder).fetch(None))
    assert fetched[-1].position["uid"] == "5"
    assert fetched[-1].internaldate == datetime(2026, 1, 6, 2, 0, 0, tzinfo=UTC)


@pytest.mark.imap
@pytest.mark.parametrize("folder", ['Kunde "Müller"', "Back\\slash Ä"])
def test_a_folder_name_with_a_quote_or_a_backslash_is_read(
    mail_server: MailServer, folder: str
) -> None:
    """The connector sends the folder as a quoted string, and a `"` or a
    `\\` in the name has to be escaped there, or the server reads another
    name, or none."""
    mail_server.recreate(folder)
    mail_server.append(folder, FOLDER_MAILS[0])
    fetched = list(mail_server.connector(folder).fetch(None))
    assert [f.raw for f in fetched] == FOLDER_MAILS[:1]


@pytest.mark.imap
def test_a_mail_that_leaves_the_folder_during_a_fetch_is_passed_over(
    mail_server: MailServer, imap_folder: str
) -> None:
    """The search names the UIDs, and each mail is fetched after the one
    before it is taken in: a mail moved out of the folder in between is gone
    when its turn comes, and the fetch goes on with the next."""
    fetching = mail_server.connector(imap_folder).fetch(None)
    assert next(fetching).position["uid"] == "1"
    mail_server.remove(imap_folder, 2)
    assert [f.position["uid"] for f in fetching] == ["3", "4"]


@pytest.mark.imap
def test_a_folder_that_does_not_exist_is_one_sentence(mail_server: MailServer) -> None:
    connector = mail_server.connector("Nirgendwo")
    with pytest.raises(ImapError) as raised:
        list(connector.fetch(None))
    assert str(raised.value) == (
        f"the IMAP server {mail_server.host}:{mail_server.port} refused to open the folder "
        "'Nirgendwo' of pilot: EXAMINE failed. No such mailbox"
    )


def test_a_server_nobody_answers_at_is_one_sentence(unused_port: int) -> None:
    """Nothing listens at the port: the system's reason, after the server."""
    connector = ImapConnector(
        host="127.0.0.1",
        port=unused_port,
        user="pilot",
        password=secrets.token_hex(8),
        folder="Kunde Müller",
        ssl_context=ssl.create_default_context(),
    )
    with pytest.raises(ImapError) as raised:
        list(connector.fetch(None))
    assert str(raised.value) == (
        f"cannot connect to the IMAP server 127.0.0.1:{unused_port}: Connection refused"
    )


@pytest.fixture
def unused_port() -> int:
    """A port on the loopback that was free a moment ago and nothing listens
    at now."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port: int = probe.getsockname()[1]
    return port


@pytest.mark.imap
def test_a_server_that_stops_answering_ends_the_fetch(
    mail_server: MailServer, imap_folder: str
) -> None:
    """A relay that stops passing the server's bytes on and keeps the
    connection open: the fetch ends with one sentence once the timeout has
    passed, rather than waiting for good. The limit falls inside the second
    mail; measured on 2026-10-06 over three runs, the whole fetch of the
    folder is 7301 to 7303 bytes from the server, and the first mail is
    through at 3575 to 3577 — the count moves by a byte or two per run.

    Run in a thread with a deadline, so that a fetch without a timeout fails
    this test instead of hanging the suite; leaving the relay closes the
    connection and lets such a thread end."""
    outcome: list[BaseException | None] = []
    with Relay(mail_server, limit=5_000, hold=True) as relay:
        connector = mail_server.connector(imap_folder, port=relay.port, timeout=1)

        def run() -> None:
            try:
                list(connector.fetch(None))
            except ImapError as error:
                outcome.append(error)
            else:
                outcome.append(None)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        thread.join(timeout=15)
        alive = thread.is_alive()
    assert not alive, "the fetch waited on a server that does not answer"
    assert len(outcome) == 1 and isinstance(outcome[0], ImapError), outcome
    assert str(outcome[0]) == (
        f"the connection to the IMAP server {mail_server.host}:{relay.port} broke off: "
        "The read operation timed out"
    )


# --- The run over IMAP -------------------------------------------------------------


def _ingest(
    storage: PostgresStorage,
    store: S3BlobStore,
    mail_server: MailServer,
    folder: str,
    identity: str,
) -> Ingested:
    return ingest(
        storage,
        storage,
        store,
        mail_server.connector(folder),
        recipient=recipient_of(identity),
        recorded_at=RECORDED_AT,
    )


def _event_count(storage: PostgresStorage) -> int:
    with storage.snapshot() as conn:
        return len(list(storage.read(conn, 1, 1000)))


@pytest.mark.db
@pytest.mark.s3
@pytest.mark.imap
def test_no_mail_is_marked_as_read_by_a_run(
    db: Engine,
    blob_store: S3BlobStore,
    mail_server: MailServer,
    imap_folder: str,
    age_identity: str,
) -> None:
    """The folder stays as it is: no mail carries `\\Seen` after a run that
    took every one of them in. The connector keeps it two ways at once, the
    folder opened read-only and every mail read with `BODY.PEEK[]`."""
    result = _ingest(PostgresStorage(db), blob_store, mail_server, imap_folder, age_identity)
    assert result.appended == 5
    assert mail_server.seen(imap_folder) == []


@pytest.mark.db
@pytest.mark.s3
@pytest.mark.imap
def test_a_folder_made_anew_is_read_from_the_start_and_nothing_doubles(
    db: Engine,
    blob_store: S3BlobStore,
    mail_server: MailServer,
    imap_folder: str,
    age_identity: str,
) -> None:
    """The folder deleted and created again, with the same mails: the server
    gives it another `UIDVALIDITY` and the UIDs start at 1 again. The run
    reads it from the start, finds every event known, and moves the
    watermark to the new generation.

    GreenMail counts `UIDVALIDITY` in seconds, so a folder made anew within
    the same second gets the same one; the test makes it anew until it does
    not, which is the precondition, not the thing under test."""
    storage = PostgresStorage(db)
    first = _ingest(storage, blob_store, mail_server, imap_folder, age_identity)
    before = mail_server.uidvalidity(imap_folder)
    assert first.position == {"uidvalidity": before, "uid": "4"}

    after = before
    while after == before:
        after = mail_server.recreate(imap_folder)
    mail_server.append(imap_folder, *FOLDER_MAILS)

    second = _ingest(storage, blob_store, mail_server, imap_folder, age_identity)
    assert (second.appended, second.known) == (0, 5)
    assert second.position == {"uidvalidity": after, "uid": "4"}
    assert _event_count(storage) == 5
