# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The IMAP test server as the tests see it, and a relay that breaks a
connection to it at a byte count.

`conftest.py` starts the server; this module is what a test holds of it: a
session of its own to arrange a folder and to look at it afterwards, and the
connector that reads it. A module of its own rather than part of
`conftest.py`, so that a test can name the types it is handed.
"""

from contextlib import contextmanager
from contextlib import suppress
from previously.connectors.imap import encode_folder
from previously.connectors.imap import ImapConnector
from typing import TYPE_CHECKING

import imaplib
import re
import socket
import ssl
import threading


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Generator
    from pathlib import Path
    from types import TracebackType
    from typing import Self


def quoted(text: str) -> str:
    """A folder name as an IMAP quoted string, spelled the IMAP way."""
    return '"' + encode_folder(text) + '"'


class MailServer:
    """Where the server is, the one user on it, and the certificate it
    presents, which names `localhost` and `127.0.0.1` and nothing else.

    A plain class rather than a dataclass, whose field annotations would
    have to be importable at run time."""

    def __init__(self, host: str, port: int, user: str, password: str, certificate: Path) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.certificate = certificate

    def context(self) -> ssl.SSLContext:
        """The default context, verifying, with the server's certificate as
        the one it trusts."""
        return ssl.create_default_context(cafile=str(self.certificate))

    @contextmanager
    def session(self) -> Generator[imaplib.IMAP4_SSL]:
        """A logged-in session of the test's own, beside the connector's."""
        imap = imaplib.IMAP4_SSL(self.host, self.port, ssl_context=self.context(), timeout=10)
        try:
            imap.login(self.user, self.password)
            yield imap
        finally:
            imap.logout()

    def connector(
        self, folder: str, *, port: int | None = None, timeout: float = 10
    ) -> ImapConnector:
        return ImapConnector(
            host=self.host,
            port=self.port if port is None else port,
            user=self.user,
            password=self.password,
            folder=folder,
            ssl_context=self.context(),
            timeout=timeout,
        )

    def recreate(self, folder: str) -> str:
        """Deletes `folder` if it exists, creates it empty, and returns its
        `UIDVALIDITY`."""
        with self.session() as imap:
            imap.delete(quoted(folder))
            _expect(imap.create(quoted(folder)))
            return self.uidvalidity(folder, imap)

    def uidvalidity(self, folder: str, imap: imaplib.IMAP4_SSL | None = None) -> str:
        if imap is None:
            with self.session() as own:
                return self.uidvalidity(folder, own)
        typ, data = imap.status(quoted(folder), "(UIDVALIDITY)")
        _expect((typ, data))
        found = re.search(rb"UIDVALIDITY ([0-9]+)", data[0] or b"")
        assert found is not None, data
        return found[1].decode("ascii")

    def append(self, folder: str, *mails: bytes) -> None:
        with self.session() as imap:
            for mail in mails:
                _expect(imap.append(quoted(folder), None, None, mail))

    def seen(self, folder: str) -> list[int]:
        """The UIDs in `folder` that carry `\\Seen`, read without setting it."""
        with self.session() as imap:
            _expect(imap.select(quoted(folder), readonly=True))
            typ, data = imap.uid("FETCH", "1:*", "(UID FLAGS)")
            _expect((typ, data))
        seen: list[int] = []
        for line in data:
            if not isinstance(line, bytes):
                continue
            uid = re.search(rb"UID ([0-9]+)", line)
            assert uid is not None, line
            if b"\\Seen" in line:
                seen.append(int(uid[1]))
        return seen

    def remove(self, folder: str, uid: int) -> None:
        """Takes the mail under `uid` out of `folder` for good."""
        with self.session() as imap:
            _expect(imap.select(quoted(folder)))
            _expect(imap.uid("STORE", str(uid), "+FLAGS", "(\\Deleted)"))
            _expect(imap.expunge())


def _expect(answer: tuple[str, object]) -> None:
    assert answer[0] == "OK", answer


class Relay:
    """A TCP relay to the server on a port of its own, which passes
    `limit` bytes from the server to the client and then breaks the
    connection — or, with `hold`, stops passing anything on and keeps it
    open, the way a server that stops answering does.

    The count is of bytes, not of time, so where the break falls depends on
    what the server sent and not on how fast: a test sizes the mails so that
    the limit lands inside the one it means. Bytes from the client pass
    unchanged and uncounted. Use it as a context manager; leaving it closes
    every socket, which also ends a client that waits on a held connection.
    """

    def __init__(self, server: MailServer, *, limit: int, hold: bool = False) -> None:
        self.limit = limit
        self.hold = hold
        self._target = (server.host, server.port)
        self._listener = socket.create_server(("127.0.0.1", 0))
        self.port: int = self._listener.getsockname()[1]
        self._sockets: list[socket.socket] = [self._listener]
        self._closed = threading.Event()
        self._threads: list[threading.Thread] = []
        # The bytes passed from the server so far, over every connection.
        self.passed = 0

    def __enter__(self) -> Self:
        self._start(self._accept)
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._closed.set()
        for each in self._sockets:
            self._close(each)
        for thread in list(self._threads):
            thread.join(timeout=10)

    def _start(self, target: Callable[..., None], *args: object) -> None:
        thread = threading.Thread(target=target, args=args, daemon=True)
        self._threads.append(thread)
        thread.start()

    def _accept(self) -> None:
        while not self._closed.is_set():
            try:
                client, _ = self._listener.accept()
            except OSError:
                return
            upstream = socket.create_connection(self._target)
            self._sockets += [client, upstream]
            self._start(self._pump, client, upstream, False)
            self._start(self._pump, upstream, client, True)

    def _pump(self, source: socket.socket, sink: socket.socket, counted: bool) -> None:
        with suppress(OSError):
            while chunk := source.recv(65536):
                if counted and self.passed + len(chunk) >= self.limit:
                    sink.sendall(chunk[: self.limit - self.passed])
                    self.passed = self.limit
                    if self.hold:
                        self._closed.wait()
                    break
                if counted:
                    self.passed += len(chunk)
                sink.sendall(chunk)
        self._close(source)
        self._close(sink)

    @staticmethod
    def _close(each: socket.socket) -> None:
        with suppress(OSError):
            each.shutdown(socket.SHUT_RDWR)
        each.close()
