# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reading a mail folder over IMAP, without changing it ({ref}`cli-reference`).

The one module that imports `imaplib`, and `.importlinter` holds it to that:
what leaves it is `Fetched` and `ImapError`, no type of `imaplib`.

A fetch connects over TLS with the context its caller gives, logs in, opens
the folder read-only (`EXAMINE`), and takes the folder's `UIDVALIDITY` from
the answer to that, so that the UIDs it then reads belong to the generation
it names. It searches for the UIDs above the watermark and fetches them one
at a time, oldest first, with `BODY.PEEK[]`.

Two things keep the folder as it is, and each would on its own: `EXAMINE`
opens it read-only, and `BODY.PEEK[]` reads a mail without setting `\\Seen`.
Measured against GreenMail 2.1.14 on 2026-10-06: `BODY[]` in a folder opened
with `EXAMINE` left the flags alone, `BODY[]` in one opened with `SELECT` set
`\\Seen`.

A connection that breaks off, a refusal of the server and a certificate that
does not verify each become one `ImapError`. No message of this module names
the password, and none quotes what the server said about a login.
"""

from datetime import datetime
from datetime import timedelta
from datetime import timezone
from previously.contract.types import Fetched
from previously.core.errors import PreviouslyError
from previously.core.errors import reason_of
from typing import cast
from typing import TYPE_CHECKING

import base64
import contextlib
import imaplib
import re
import ssl


if TYPE_CHECKING:
    from collections.abc import Generator
    from collections.abc import Iterator
    from collections.abc import Sequence
    from previously.contract.types import Watermark


# The port of IMAP over TLS, RFC 8314.
PORT = 993

# Seconds a socket operation may wait before the run gives up. A server that
# stops answering would otherwise hold a scheduled run for good, and the next
# runs with it when the schedule forbids two at once. It bounds each read and
# write, not the run: a large mail that keeps arriving does not time out.
TIMEOUT = 60.0


class ImapError(PreviouslyError):
    """The IMAP server could not be reached, refused a step, or the
    connection to it broke off. One sentence that names the server, and the
    user and the folder where they help; never the password."""


class ImapConnector:
    """A mail folder as a connector: `fetch` yields every mail the folder
    holds above the watermark, as raw bytes, oldest first.

    `name` is `imap:<user>@<host>/<folder>`, the key of the watermark. A
    folder that is renamed is another name and is read from the start, which
    the run takes in as known. The position is the folder's `UIDVALIDITY`
    and the UID of the mail; a watermark of another `UIDVALIDITY` is of a
    folder that was made anew, and the folder is read from the start.

    `ssl_context` is the caller's: the command line gives the default one,
    which verifies the certificate and the host name. `timeout` is
    `TIMEOUT` unless a caller needs another.
    """

    def __init__(
        self,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        folder: str,
        ssl_context: ssl.SSLContext,
        timeout: float = TIMEOUT,
    ) -> None:
        self.name = f"imap:{user}@{host}/{folder}"
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._folder = folder
        self._context = ssl_context
        self._timeout = timeout
        self._server = f"{host}:{port}"

    def fetch(self, since: Watermark | None) -> Iterator[Fetched]:
        imap = self._connect()
        try:
            self._login(imap)
            validity = self._open(imap)
            after = _after(since, validity)
            for uid in self._uids(imap, after):
                fetched = self._fetch(imap, uid, validity)
                if fetched is not None:
                    yield fetched
        finally:
            # A connection that broke off cannot say goodbye, and the error
            # that ended the run is the one to report.
            with contextlib.suppress(imaplib.IMAP4.error, OSError):
                imap.logout()

    def _connect(self) -> imaplib.IMAP4_SSL:
        try:
            return imaplib.IMAP4_SSL(
                self._host, self._port, ssl_context=self._context, timeout=self._timeout
            )
        except ssl.SSLCertVerificationError as error:
            raise ImapError(
                f"the certificate of the IMAP server {self._server} does not verify: "
                f"{error.verify_message}"
            ) from error
        except imaplib.IMAP4.error as error:
            raise ImapError(
                f"cannot connect to the IMAP server {self._server}: {_said(error.args[0])}"
            ) from error
        except OSError as error:
            raise ImapError(
                f"cannot connect to the IMAP server {self._server}: {reason_of(error)}"
            ) from error

    def _login(self, imap: imaplib.IMAP4_SSL) -> None:
        # `from None` on both refusals: what is chained to them is the
        # server's answer to the login, and the encoder's error, whose
        # `object` is the one argument that would not encode — `imaplib`
        # encodes each on its own — and that is the quoted password when
        # the password is the one with a character beyond ASCII.
        with self._speaking():
            try:
                imap.login(_quoted(self._user), self._password)
            except imaplib.IMAP4.abort:
                raise
            except imaplib.IMAP4.error:
                raise ImapError(
                    f"the IMAP server {self._server} refused the login of {self._user}"
                ) from None
            except UnicodeEncodeError:
                # `imaplib` writes the login as ASCII; a character beyond it
                # in the password would otherwise end in a stack trace.
                raise ImapError(
                    f"the login of {self._user} at the IMAP server {self._server} holds a "
                    "character other than ASCII, which the IMAP login cannot carry"
                ) from None

    def _open(self, imap: imaplib.IMAP4_SSL) -> str:
        """Opens the folder read-only and returns its `UIDVALIDITY`."""
        with self._speaking():
            typ, data = imap.select(_quoted(encode_folder(self._folder)), readonly=True)
            self._ok(typ, data, f"to open the folder {self._folder!r} of {self._user}")
            _, validity = imap.response("UIDVALIDITY")
        value = validity[-1]
        if not isinstance(value, bytes) or not value.isdigit():
            raise ImapError(
                f"the IMAP server {self._server} names no UIDVALIDITY for the folder "
                f"{self._folder!r}"
            )
        return value.decode("ascii")

    def _uids(self, imap: imaplib.IMAP4_SSL, after: int) -> list[int]:
        """The UIDs above `after`, in ascending order.

        The search is `UID n:*` as it stands; GreenMail refuses it inside
        parentheses (measured on 2026-10-05). `n:*` names the highest UID
        even when it is below `n`, by RFC 3501, so what the server returns
        is filtered.
        """
        with self._speaking():
            typ, data = imap.uid("SEARCH", "UID", f"{after + 1}:*")
        self._ok(typ, data, f"the search in the folder {self._folder!r}")
        found: bytes = data[0] or b""
        return sorted(uid for uid in (int(token) for token in found.split()) if uid > after)

    def _fetch(self, imap: imaplib.IMAP4_SSL, uid: int, validity: str) -> Fetched | None:
        """The mail under `uid`, or `None` when it left the folder after the
        search."""
        with self._speaking():
            typ, data = imap.uid("FETCH", str(uid), "(UID INTERNALDATE BODY.PEEK[])")
        self._ok(typ, data, f"to fetch uid {uid} from the folder {self._folder!r}")
        found = _message(data, uid)
        if found is None:
            return None
        written, raw = found
        internaldate = parse_internaldate(written)
        if internaldate is None:
            raise ImapError(
                f"the IMAP server {self._server} gave uid {uid} the INTERNALDATE "
                f"{written!r}, which is not a date"
            )
        position = {"uidvalidity": validity, "uid": str(uid)}
        return Fetched(
            raw=raw,
            position=position,
            found_in={"connector": self.name, **position},
            internaldate=internaldate,
        )

    def _ok(self, typ: str, data: Sequence[object], what: str) -> None:
        if typ != "OK":
            raise ImapError(f"the IMAP server {self._server} refused {what}: {_said(data[-1])}")

    @contextlib.contextmanager
    def _speaking(self) -> Generator[None]:
        """Turns a connection that breaks off into one sentence. `abort` is
        `imaplib`'s word for it; an `OSError` that passes `imaplib` is the
        same, and so is a socket that timed out.

        The text of an `abort` stays out of the sentence, because it can
        quote what the server sent, and what the server sends is mail.
        Measured on 2026-10-06 with Python 3.14.3 and a connection cut in
        the middle of a mail: `imaplib` keeps what it read of the mail in
        its buffer, reads it a second time as a response, and aborts with
        `unexpected response: b'To: pilot@example.org'`, a header line of
        the mail. The system's reason for an `OSError` is the system's, and
        is quoted."""
        try:
            yield
        except imaplib.IMAP4.abort as error:
            raise ImapError(
                f"the connection to the IMAP server {self._server} broke off"
            ) from error
        except imaplib.IMAP4.error as error:
            raise ImapError(
                f"the IMAP server {self._server} refused a command: {_said(error.args[0])}"
            ) from error
        except OSError as error:
            raise ImapError(
                f"the connection to the IMAP server {self._server} broke off: {reason_of(error)}"
            ) from error


def _after(since: Watermark | None, validity: str) -> int:
    """The UID the folder is read above: the watermark's, when it is of this
    generation of the folder, and none otherwise."""
    if since is None or since.position.get("uidvalidity") != validity:
        return 0
    return int(since.position["uid"])


# What `imaplib` hands back for a FETCH: a tuple of the text up to the
# literal and the literal, then the rest of the response as bytes. The
# server chooses the order of the items, so `UID` may come after the body.
_BODY = re.compile(rb"\bBODY\[\] \{[0-9]+\}$")
_UID = re.compile(rb"\bUID ([0-9]+)")
_INTERNALDATE = re.compile(rb'\bINTERNALDATE "([^"]*)"')


def _message(data: Sequence[object], uid: int) -> tuple[str, bytes] | None:
    """The INTERNALDATE as written and the raw bytes of the mail under
    `uid`, out of a FETCH response, or `None` when the response holds none."""
    for index, item in enumerate(data):
        if not isinstance(item, tuple):
            continue
        pair = cast("tuple[object, ...]", item)
        if len(pair) != 2:
            continue
        head, raw = pair
        if not isinstance(head, bytes) or not isinstance(raw, bytes) or not _BODY.search(head):
            continue
        rest = data[index + 1] if index + 1 < len(data) else b""
        text = head + (rest if isinstance(rest, bytes) else b"")
        named = _UID.search(text)
        if named is None or int(named[1]) != uid:
            continue
        written = _INTERNALDATE.search(text)
        return ("" if written is None else written[1].decode("ascii", "replace")), raw
    return None


# `dd-Mon-yyyy hh:mm:ss +zzzz`, RFC 3501, the day possibly padded with a
# blank. The month names are English whatever the locale, so they are a
# table here and not `strptime`'s `%b`; RFC 3501 writes them in ABNF, whose
# quoted strings match without regard to case.
_DATE = re.compile(
    r" ?([0-9]{1,2})-([A-Za-z]{3})-([0-9]{4}) "
    r"([0-9]{2}):([0-9]{2}):([0-9]{2}) ([-+])([0-9]{2})([0-9]{2})"
)
_MONTHS = {
    name: number
    for number, name in enumerate(
        ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
        start=1,
    )
}


def parse_internaldate(text: str) -> datetime | None:
    """The moment an INTERNALDATE names, with its zone, or `None` for a text
    that names none: another form, a month that is not one of the twelve
    English abbreviations, or a date or zone that does not exist.

    `None` rather than an exception, because only the caller knows which
    mail the text belongs to: the connector turns it into an `ImapError`
    that names the UID and the text as the server wrote it.

    Public because a test pins it: the moment goes into the payload of every
    mail event, and into `occurred_at` when the `Date` header cannot be
    read, so a slip here would be written into the chain for good.
    """
    matched = _DATE.fullmatch(text)
    if matched is None:
        return None
    day, month, year, hour, minute, second, sign, zone_hours, zone_minutes = matched.groups()
    number = _MONTHS.get(month.capitalize())
    if number is None:
        return None
    offset = timedelta(hours=int(zone_hours), minutes=int(zone_minutes))
    try:
        return datetime(
            int(year),
            number,
            int(day),
            int(hour),
            int(minute),
            int(second),
            tzinfo=timezone(-offset if sign == "-" else offset),
        )
    except ValueError:
        return None


def _said(value: object) -> str:
    """What the server or `imaplib` said, as text."""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return str(value)


def _quoted(text: str) -> str:
    """`text` as an IMAP quoted string: `imaplib` sends every argument but
    the password as it stands, and a folder name holds blanks."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


# --- Folder names, RFC 3501 section 5.1.3 -----------------------------------
#
# A folder name travels in "modified UTF-7": printable ASCII stands for
# itself, `&` as `&-`, and every run of other characters as `&`, the base64
# of its UTF-16 with `,` for `/` and no padding, and `-`.


def encode_folder(name: str) -> str:
    """`name` the way IMAP spells a folder: `Kunde Müller` is
    `Kunde M&APw-ller`."""
    out: list[str] = []
    pending: list[str] = []

    def flush() -> None:
        if pending:
            data = "".join(pending).encode("utf-16-be", "surrogatepass")
            encoded = base64.b64encode(data).decode("ascii").rstrip("=").replace("/", ",")
            out.append(f"&{encoded}-")
            pending.clear()

    for character in name:
        if " " <= character <= "~":
            flush()
            out.append("&-" if character == "&" else character)
        else:
            pending.append(character)
    flush()
    return "".join(out)


def decode_folder(spelled: str) -> str:
    """The folder name `spelled` stands for, the inverse of
    `encode_folder`. A spelling that is not modified UTF-7 raises
    `ValueError`."""
    out: list[str] = []
    position = 0
    while position < len(spelled):
        start = spelled.find("&", position)
        if start < 0:
            out.append(spelled[position:])
            break
        out.append(spelled[position:start])
        end = spelled.find("-", start + 1)
        if end < 0:
            raise ValueError(f"{spelled!r} opens a run with & and does not close it")
        run = spelled[start + 1 : end]
        if run:
            data = base64.b64decode(run.replace(",", "/") + "=" * (-len(run) % 4), validate=True)
            out.append(data.decode("utf-16-be", "surrogatepass"))
        else:
            out.append("&")
        position = end + 1
    return "".join(out)
