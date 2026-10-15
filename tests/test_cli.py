# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
from contextlib import contextmanager
from dataclasses import replace
from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import UTC
from mailserver import Relay
from previously.cli import COMMANDS
from previously.cli import escape_controls
from previously.cli import escape_field
from previously.cli import main
from previously.cli import MAX_TEXT_BYTES
from previously.cli import media_type_of
from previously.cli import parse_address
from previously.cli import parse_moment
from previously.contract.rows import EventRow
from previously.contract.rows import ProjectionState
from previously.contract.rows import UnitRow
from previously.contract.types import BlobRef
from previously.contract.types import ChannelIdentity
from previously.contract.types import Evidence
from previously.contract.types import RawEvent
from previously.contract.types import RawUnit
from previously.core.append import append
from previously.core.assertion import DIRECT
from previously.core.assertion import model_author
from previously.core.assertion import OBLIGATION
from previously.core.assertion import ObligationBody
from previously.core.assertion import OPEN
from previously.core.assertion import OPERATOR
from previously.core.assertion import Source
from previously.core.assertion import Statement as AssertionStatement
from previously.core.assertions import write_statements
from previously.core.errors import InvalidPayload
from previously.core.errors import PreviouslyError
from previously.core.errors import ProjectionRebuilt
from previously.core.graph import ACTIVE
from previously.core.graph import Claim
from previously.core.graph import ENTITY
from previously.core.graph import EntityBody
from previously.core.graph import Graph
from previously.core.graph import RELATION
from previously.core.graph import RelationBody
from previously.core.graph import SOURCES
from previously.core.graph_write import check_claims
from previously.core.graph_write import GraphRefused
from previously.core.graph_write import read_graph
from previously.core.graph_write import write_claims
from previously.core.identity import artifact_hash_of
from previously.core.members import bracket_edges
from previously.core.members import bracket_kinds
from previously.core.members import members
from previously.core.projection import catch_up
from previously.core.projection import CHRONICLE
from previously.core.redact import redact_blob
from previously.core.redact import redact_event
from previously.core.sealing import recipient_of
from previously.core.sealing import seal
from previously.core.units import split_plaintext
from previously.core.verify import verify
from previously.core.vocabulary import read_vocabulary
from previously.storage.postgres import PostgresStorage
from typing import cast
from typing import TYPE_CHECKING

import hashlib
import http.client
import io
import json
import mailfiles
import os
import pathlib
import pytest
import re
import secrets
import socket
import subprocess
import sys
import threading
import time


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Generator
    from collections.abc import Iterator
    from collections.abc import Sequence
    from mailserver import MailServer
    from previously.contract.blobs import ClosableSource
    from previously.contract.blobs import StoredBlob
    from previously.core.projection import Outcome
    from previously.core.projection import Projection
    from previously.storage.s3 import S3BlobStore
    from sqlalchemy import Connection
    from sqlalchemy import Engine
    from sqlalchemy import URL
    from typing import IO


@pytest.mark.parametrize(
    ("text", "port", "expected"),
    [
        ("127.0.0.1:8765", None, ("127.0.0.1", 8765)),
        ("10.43.0.5:1", None, ("10.43.0.5", 1)),
        ("[::1]:8765", None, ("::1", 8765)),
        ("[::]:65535", None, ("::", 65535)),
        ("mail.example.org", 993, ("mail.example.org", 993)),
        ("mail.example.org:143", 993, ("mail.example.org", 143)),
        (
            "previously-mcp.previously.svc.cluster.local.:8765",
            None,
            (
                "previously-mcp.previously.svc.cluster.local.",
                8765,
            ),
        ),
        ("[2001:db8::1]", 993, ("2001:db8::1", 993)),
    ],
)
def test_parse_address_splits_the_host_from_the_port(
    text: str, port: int | None, expected: tuple[str, int]
) -> None:
    """The host comes back without the brackets of an IPv6 address, as the
    socket wants it, and the port is the default where the address may leave
    it out."""
    assert parse_address("X", text, default_port=port) == expected


@pytest.mark.parametrize(
    ("text", "port"),
    [
        ("mail.example.org", None),
        ("[::1]", None),
        ("::1", 993),
        ("::1:8765", None),
        ("mail.example.org:", 993),
        ("mail.example.org:0", 993),
        ("mail.example.org:99999", 993),
        ("mail example.org", 993),
        ("mäil.example.org", 993),
        ("a..b", 993),
        ("[::1]x", 993),
        ("[1.2.3.4]", 993),
        ("", 993),
    ],
)
def test_parse_address_refuses_any_other_form(text: str, port: int | None) -> None:
    form = "host:port" if port is None else "host or host:port"
    with pytest.raises(PreviouslyError) as raised:
        parse_address("X", text, default_port=port)
    assert str(raised.value) == f"X is not {form}, with an IPv6 host in brackets: {text!r}"


@pytest.mark.parametrize(
    ("text", "shown"),
    [
        ("imaps://pilot:s3cret@mail.example.org", "…@mail.example.org"),
        ("pilot:s3c@ret@mail.example.org:993", "…@mail.example.org:993"),
        ("s3cret@", "…@"),
    ],
)
def test_parse_address_quotes_nothing_before_the_last_at(text: str, shown: str) -> None:
    """An address holds no `@`, so one there is a mistake, and the likely one
    is a user and a password written in front of the host. The refusal
    quotes from the last `@` on; a value without one is quoted whole, as the
    test above shows."""
    with pytest.raises(PreviouslyError) as raised:
        parse_address("X", text, default_port=993)
    message = str(raised.value)
    assert message == f"X is not host or host:port, with an IPv6 host in brackets: {shown!r}"
    assert "s3c" not in message


def test_parse_moment_with_a_zone() -> None:
    assert parse_moment("2026-10-01T09:00:00+02:00").utcoffset() is not None


def test_parse_moment_with_z() -> None:
    assert parse_moment("2026-10-01T09:00:00Z") == datetime(2026, 10, 1, 9, 0, 0, tzinfo=UTC)


def test_parse_moment_rejects_a_naive_timestamp() -> None:
    """Review Focus 3: without a zone, local time would be hashed as UTC."""
    with pytest.raises(InvalidPayload, match="time zone"):
        parse_moment("2026-10-01T09:00:00")


def test_parse_moment_rejects_nonsense() -> None:
    with pytest.raises(InvalidPayload, match="ISO 8601"):
        parse_moment("yesterday")


@pytest.mark.db
def test_append_log_and_verify_together(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from sqlalchemy import Engine

    assert isinstance(db, Engine)
    monkeypatch.setenv("PREVIOUSLY_DSN", db.url.render_as_string(hide_password=False))

    submit = ["append", "--source", "cli", "--external-id", "a", "--text", "Hello\n\nWorld"]
    assert main(submit) == 0
    assert main(["verify"]) == 0
    assert main(["log"]) == 0
    output = capsys.readouterr().out
    assert "1" in output

    # `log --limit` is bolted the way `chronicle --limit` is, and until
    # 2026-10-04 it was not. Measured then against this container: `--limit 0`
    # returned 0 with nothing on stdout and nothing on stderr, so a refused
    # limit looked exactly like an empty log, and `--limit -2` came back as
    # `sqlalchemy.exc.DataError: (psycopg.errors.InvalidRowCountInLimitClause)
    # LIMIT must not be negative` — a stack trace and exit code 1 instead of
    # 2, which is the shape of review finding W2.
    for limit in ("0", "-2"):
        assert main(["log", "--limit", limit]) == 2
        out, err = capsys.readouterr()
        assert out == ""
        assert err.strip() == f"Error: --limit must be at least 1, got {limit}"


@pytest.mark.db
def test_appending_twice_gives_the_same_id(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from sqlalchemy import Engine

    assert isinstance(db, Engine)
    monkeypatch.setenv("PREVIOUSLY_DSN", db.url.render_as_string(hide_password=False))
    main(["append", "--source", "cli", "--external-id", "a", "--text", "x"])
    first = capsys.readouterr().out.strip()
    main(["append", "--source", "cli", "--external-id", "a", "--text", "x"])
    second = capsys.readouterr().out.strip()
    assert first == second


@pytest.mark.db
def test_another_text_under_a_known_key_is_refused(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same text twice is known; another text under the same key is
    refused with one sentence and 2, and nothing is written. The hashes are
    those of the text and the sorted attachment addresses, here none."""
    from sqlalchemy import Engine
    from sqlalchemy import text

    assert isinstance(db, Engine)
    monkeypatch.setenv("PREVIOUSLY_DSN", db.url.render_as_string(hide_password=False))
    submit = ["append", "--source", "cli", "--external-id", "a", "--text"]
    assert main([*submit, "A"]) == 0
    assert main([*submit, "A"]) == 0
    assert capsys.readouterr().out == "1\n1\n"

    assert main([*submit, "B"]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    known = artifact_hash_of({"text": "A", "attachments": []}).hex()[:16]
    arrived = artifact_hash_of({"text": "B", "attachments": []}).hex()[:16]
    assert _single_line(err) == (
        f"Error: cli/a is known with another content (artifact {known} ≠ {arrived})"
    )
    with db.connect() as c:
        assert c.execute(text("SELECT count(*) FROM event")).scalar_one() == 1


@pytest.mark.parametrize("ending", ["\r\n", "\r"], ids=["crlf", "cr"])
@pytest.mark.db
def test_the_same_text_with_other_line_endings_is_known(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, ending: str
) -> None:
    """Text pasted from a Windows clipboard ends its lines in CRLF, and
    `split_plaintext` reads it as the same units; the artifact reads it the
    same way, so the text is known and not refused as another content. The
    hash is that of the text with LF."""
    _setup(db, monkeypatch)
    submit = ["append", "--source", "cli", "--external-id", "a", "--text"]
    assert main([*submit, "Erster Absatz.\n\nZweiter Absatz."]) == 0
    assert main([*submit, f"Erster Absatz.{ending}{ending}Zweiter Absatz."]) == 0
    out, err = capsys.readouterr()
    assert (out, err) == ("1\n1\n", "")

    assert main(["show", "1"]) == 0
    expected = artifact_hash_of(
        {"text": "Erster Absatz.\n\nZweiter Absatz.", "attachments": []}
    ).hex()
    assert f'"artifact_hash": "{expected}"' in capsys.readouterr().out


@pytest.mark.db
def test_a_text_that_differs_in_more_than_its_line_endings_is_refused(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control of the test above: the line endings are all that is
    made alike."""
    _setup(db, monkeypatch)
    submit = ["append", "--source", "cli", "--external-id", "a", "--text"]
    assert main([*submit, "Erster Absatz.\n\nZweiter Absatz."]) == 0
    assert main([*submit, "Erster Absatz.\r\n\r\nZweiter Absatz!"]) == 2
    assert "is known with another content" in capsys.readouterr().err


@pytest.mark.db
def test_show_displays_the_event_with_its_units(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`show` reads event **and** units, since review finding G4 in a shared
    connection — without this test precisely the path on which two queries run
    one after the other on the same `Connection` would be unchecked."""
    from sqlalchemy import Engine

    assert isinstance(db, Engine)
    monkeypatch.setenv("PREVIOUSLY_DSN", db.url.render_as_string(hide_password=False))
    submit = ["append", "--source", "cli", "--external-id", "a", "--text", "Hello\n\nWorld"]
    assert main(submit) == 0
    capsys.readouterr()

    assert main(["show", "1"]) == 0
    output = capsys.readouterr().out
    assert "id=1 kind=observation" in output
    assert "¶1 Hello" in output
    assert "¶2 World" in output


@pytest.mark.db
def test_show_displays_the_evidence_and_the_payload(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Finding G-1: the kind of evidence was writable and unreadable.

    `--evidence` goes permanently into the hash and cannot be supplied after
    the fact ({ref}`canonicalization`), so a surface that can set it but not
    read it back is the wrong half. The payload goes with it: `show` was the
    only command that could display it at all, and it did not.
    """
    from sqlalchemy import Engine

    assert isinstance(db, Engine)
    monkeypatch.setenv("PREVIOUSLY_DSN", db.url.render_as_string(hide_password=False))
    assert (
        main(
            [
                "append",
                "--source",
                "cli",
                "--external-id",
                "a",
                "--text",
                "Hello",
                "--evidence",
                "verbatim",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert main(["show", "1"]) == 0
    output = capsys.readouterr().out
    assert "evidence=verbatim" in output
    # The payload as canonical-ish JSON with sorted keys, so the line is
    # stable: jsonb does not give the keys back in the order written. The
    # text is in the units alone: `append --text` adds nothing to the payload
    # but the hash of the artifact and the kind of evidence. Measured on
    # 2026-10-05 with the text copied into the payload again: this comparison
    # failed.
    artifact = artifact_hash_of({"text": "Hello", "attachments": []}).hex()
    payload = f'{{"artifact_hash": "{artifact}", "evidence": "verbatim"}}'
    assert f"payload={payload}\n  ¶1 Hello\n" in output


@pytest.mark.db
def test_show_says_so_when_the_payload_is_erased(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The tombstone has neither payload nor kind of evidence
    ({ref}`tombstone-seam`). `show` has to say that rather than print an
    empty line — and it must not crash on `None`, which is the branch a plain
    `payload.get(...)` would have fallen into. Forged with plain SQL, the
    tombstone has no redaction to name, and the line stays `payload=<erased>`
    ({ref}`erasure`)."""
    from sqlalchemy import Engine
    from sqlalchemy import text

    assert isinstance(db, Engine)
    monkeypatch.setenv("PREVIOUSLY_DSN", db.url.render_as_string(hide_password=False))
    assert main(["append", "--source", "cli", "--external-id", "a", "--text", "Hello"]) == 0
    capsys.readouterr()
    with db.begin() as c:
        # The salt goes with the payload, or `event_payload_salt_check`
        # refuses the statement (ruling P-1 of the 2026-10-04 stage 1c plan).
        c.execute(text("UPDATE event SET payload = NULL, payload_salt = NULL WHERE id = 1"))

    assert main(["show", "1"]) == 0
    output = capsys.readouterr().out
    assert "payload=<erased>" in output
    assert "evidence=" not in output


@pytest.mark.db
def test_show_says_so_when_a_unit_is_erased(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A unit without content prints as erased, and its neighbour as before.
    The tombstone is forged with plain SQL here, so no redaction ordered it,
    and `show` says `<erased>` without naming one ({ref}`erasure`)."""
    from sqlalchemy import Engine
    from sqlalchemy import text

    assert isinstance(db, Engine)
    monkeypatch.setenv("PREVIOUSLY_DSN", db.url.render_as_string(hide_password=False))
    assert main(["append", "--source", "cli", "--external-id", "a", "--text", "One\n\nTwo"]) == 0
    capsys.readouterr()
    with db.begin() as c:
        c.execute(
            text("UPDATE unit SET content = NULL, salt = NULL WHERE event_id = 1 AND seq = 1")
        )

    assert main(["show", "1"]) == 0
    output = capsys.readouterr().out
    assert "  ¶1 <erased>\n  ¶2 Two\n" in output


@pytest.mark.db
def test_show_does_not_know_the_event(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from sqlalchemy import Engine

    assert isinstance(db, Engine)
    monkeypatch.setenv("PREVIOUSLY_DSN", db.url.render_as_string(hide_password=False))
    assert main(["show", "99"]) == 1
    assert "No event 99" in capsys.readouterr().err


def test_a_too_large_text_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Review Focus 5: without an upper bound a submission blows up memory and
    the transaction."""
    monkeypatch.setenv("PREVIOUSLY_DSN", "postgresql+psycopg://unused/unused")
    huge = "x" * (MAX_TEXT_BYTES + 1)
    assert main(["append", "--source", "cli", "--external-id", "a", "--text", huge]) == 2


def _single_line(output: str) -> str:
    """Exactly one line on stderr — no stack trace (review finding W2)."""
    lines = output.strip().splitlines()
    assert len(lines) == 1, f"expected exactly one sentence, got: {output!r}"
    return lines[0]


def test_an_unparsable_dsn_shows_one_sentence(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Case 1 out of review finding W2, measured with
    `PREVIOUSLY_DSN=not-a-dsn`: before, a `sqlalchemy.exc.ArgumentError` stack
    trace and exit code 1 from the Python interpreter (an unhandled exception)
    instead of 2 from `main`."""
    monkeypatch.setenv("PREVIOUSLY_DSN", "not-a-dsn")
    assert main(["log"]) == 2
    sentence = _single_line(capsys.readouterr().err)
    assert "Traceback" not in sentence
    assert "PREVIOUSLY_DSN" in sentence


def test_an_unreachable_server_shows_one_sentence(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Case 2 out of review finding W2. The DSN carries a password — the
    message must not show it, which is checked along here, not only in
    `test_storage.py`.

    `verify` is in it because it reads through a different entrance to the
    storage than `log` does: `snapshot`, not `begin`. A `snapshot` that
    skipped the shared translation would bring back a traceback and exit code
    1 — the code of a finding — for a server that is down."""
    monkeypatch.setenv("PREVIOUSLY_DSN", "postgresql+psycopg://user:SECRET123@localhost:1/db")
    assert main(["log"]) == 2
    sentence = _single_line(capsys.readouterr().err)
    assert "Traceback" not in sentence
    assert "SECRET123" not in sentence
    # Nothing listens on port 1: the reason is the operating system's, and it
    # comes after host, port and database, as for a server that answers and
    # refuses.
    assert sentence.startswith(
        "Error: connecting to database db at localhost:1 failed: connection to server at "
    )
    assert "Connection refused" in sentence
    assert main(["verify"]) == 2
    assert _single_line(capsys.readouterr().err) == sentence


def _session_url(db: object) -> URL:
    from sqlalchemy import Engine

    assert isinstance(db, Engine)
    return db.url


def _log_with(
    dsn: str, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> tuple[str, str]:
    """`log` with `dsn`: what it prints on standard output, and the one
    sentence on standard error."""
    monkeypatch.setenv("PREVIOUSLY_DSN", dsn)
    assert main(["log"]) == 2
    out, err = capsys.readouterr()
    return out, _single_line(err)


def _no_fragment_of(secret: str, output: str) -> bool:
    """Whether no eight characters in a row of `secret` stand in `output`:
    a password cut in two by a parser that read it wrongly shows as a piece,
    not as itself. A secret shorter than eight characters has no such piece,
    and the check would pass whatever the output held, so it is refused."""
    assert len(secret) >= 8, f"a secret of {len(secret)} characters proves nothing here"
    return not any(secret[i : i + 8] in output for i in range(len(secret) - 7))


def _wrong_password() -> str:
    """Drawn at run time, so that no output can hold it by coincidence, and
    with letters at both ends, so that no port or count can look like a
    piece of it."""
    return f"Wrong{secrets.token_hex(12)}Pw"


@pytest.mark.db
def test_a_refused_password_names_libpqs_reason_and_not_the_password(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The server answers and refuses the login, the password in the usual
    `user:password@` place. The sentence names host, port and database and
    nothing else of the connection string, says that connecting failed, and
    quotes the first line of the reason: a guess of ours in its place said
    "does not answer — is PostgreSQL running there", and sent whoever had
    typed a wrong password to look at the network."""
    url = _session_url(db)
    secret = _wrong_password()
    dsn = url.set(password=secret).render_as_string(hide_password=False)
    out, sentence = _log_with(dsn, capsys, monkeypatch)
    # First, so that a password in the output fails on this line and no other.
    assert _no_fragment_of(secret, out + sentence)
    assert out == ""
    assert sentence.startswith(
        f"Error: connecting to database {url.database} at {url.host}:{url.port} failed: "
    )
    assert "FATAL:  password authentication failed for user " in sentence


@pytest.mark.db
def test_a_password_in_the_query_is_refused(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """libpq takes the password as a parameter of the query as well,
    `…/database?password=…`. Measured at `3c8e506`: the sentence printed the
    whole connection string with the query, and the password in clear; at
    `2579eb5`, a password there holding an unencoded `&` was cut into a key
    the client library quoted. The password stands in the user part and
    nowhere else, so `from_dsn` refuses the key before anything connects."""
    url = _session_url(db)
    secret = _wrong_password()
    dsn = url.set(password=None).render_as_string(hide_password=False) + f"?password={secret}"
    out, sentence = _log_with(dsn, capsys, monkeypatch)
    assert _no_fragment_of(secret, out + sentence)
    assert out == ""
    assert sentence + "\n" == _UNREADABLE


# The connection strings of the attack reviews of 2026-10-05: the 38 of fix
# round 2 in its order, one more after them, the nine of fix round 3 as
# N01-N09, and the forms of fix rounds 4 and 5 as R01-R19. `{A}`, `{B}`, `{C}` and
# `{E}` are pieces of a password, 20 hexadecimal characters each, and `{D}`
# one of 20 digits, all drawn at run time; `{H}` is the session server's
# host and port. The specials stand in the forms between the pieces. The
# outcome is what the command must do: `refused` before anything connects,
# with the one sentence `from_dsn` has for a string outside its grammar, or
# `connect`, which fails with the connection sentence. The pieces listed are
# the ones that must appear nowhere; a form that puts no password where a
# message could print it lists none. The last field says why the form ends
# as it does.
_FORMS: tuple[tuple[str, str, str, str, str], ...] = (
    ("01-user-pass", "{S}app:{A}@{H}/probe", "connect", "A", "the plain form"),
    (
        "02-encoded-specials",
        "{S}app:{A}%40%3A%2F%3F%23{B}@{H}/probe",
        "connect",
        "AB",
        "every special of the password encoded",
    ),
    ("03-query-password", "{S}app@{H}/probe?password={A}", "refused", "A", "key `password`"),
    (
        "04-query-password-with-at",
        "{S}app@{H}/probe?password={A}@{B}",
        "refused",
        "AB",
        "key `password`, and a raw `@` in a value",
    ),
    ("05-query-key-typo", "{S}app@{H}/probe?passwrod={A}", "refused", "A", "key not allowed"),
    ("06-query-passfile", "{S}app@{H}/probe?passfile=/tmp/{A}", "refused", "A", "key not allowed"),
    ("07-query-sslpassword", "{S}app@{H}/probe?sslpassword={A}", "refused", "A", "a secret key"),
    (
        "08-query-sslpassword-sslkey",
        "{S}app@{H}/probe?sslpassword={A}&sslkey=/nonexistent&sslmode=require",
        "refused",
        "A",
        "a secret key",
    ),
    (
        "09-query-sslmode-value",
        "{S}app@{H}/probe?sslmode=bogus",
        "connect",
        "",
        "an allowed key; libpq quotes the value, which holds no password",
    ),
    (
        "10-query-connect-timeout-value",
        "{S}app@{H}/probe?connect_timeout=abc",
        "connect",
        "",
        "an allowed key; the client refuses the value, and the reason is fixed",
    ),
    (
        "11-query-options",
        "{S}app@{H}/probe?options=-c%20foo%3D{A}",
        "refused",
        "A",
        "key not allowed",
    ),
    (
        "12-libpq-key-value",
        "host=localhost dbname=probe user=app password={A}",
        "refused",
        "A",
        "no scheme",
    ),
    ("13-libpq-scheme", "postgresql://app:{A}@{H}/probe", "connect", "A", "the plain scheme"),
    ("14-two-at", "{S}app:{A}@{B}@{H}/probe", "refused", "AB", "a raw `@` in the password"),
    ("15-at-slash-at", "{S}app:{A}@{B}/{C}@{H}/probe", "refused", "ABC", "a raw `@` and `/`"),
    (
        "16-question-before-second-at",
        "{S}app:{A}?{B}@{C}@{H}/probe",
        "refused",
        "ABC",
        "a raw `?` and `@` in the password",
    ),
    (
        "17-question-then-colon",
        "{S}app:{A}?x@{B}:{C}@{H}/probe",
        "refused",
        "ABC",
        "a raw `?`, `@` and `:` in the password",
    ),
    ("18-at-in-database", "{S}app:{A}@{H}/pro@be", "refused", "A", "a raw `@` in the database"),
    (
        "19-at-in-database-encoded",
        "{S}app:{A}@{H}/pro%40be",
        "connect",
        "A",
        "the `@` of the database encoded",
    ),
    ("20-at-in-user", "{S}app@corp:{A}@{H}/probe", "refused", "A", "a raw `@` in the user"),
    (
        "21-at-in-user-encoded",
        "{S}app%40corp:{A}@{H}/probe",
        "connect",
        "A",
        "the `@` of the user encoded",
    ),
    (
        "22-port-not-a-number",
        "{S}app:{A}@localhost:54x32/probe",
        "refused",
        "A",
        "a port of more than digits",
    ),
    ("23-host-forgotten", "{S}app:{A}/probe", "refused", "A", "the password read as port"),
    ("24-host-and-database-forgotten", "{S}app:{A}", "refused", "A", "the password as port"),
    ("25-colon-for-at", "{S}app:{A}:{H}/probe", "refused", "A", "the password read as port"),
    ("26-scheme-postgres", "postgres://app:{A}@{H}/probe", "refused", "A", "scheme not allowed"),
    (
        "27-scheme-unknown-driver",
        "postgresql+nope://app:{A}@{H}/probe",
        "refused",
        "A",
        "scheme not allowed",
    ),
    (
        "28-scheme-psycopg2",
        "postgresql+psycopg2://app:{A}@{H}/probe",
        "refused",
        "A",
        "scheme not allowed; a traceback before this round",
    ),
    (
        "29-scheme-without-slashes",
        "postgresql+psycopg:app:{A}@{B}@{H}/probe",
        "refused",
        "AB",
        "no `//`",
    ),
    ("30-ipv6", "{S}app:{A}@[::1]:{port}/probe", "connect", "A", "an IPv6 host in brackets"),
    ("31-unreachable", "{S}app:{A}@localhost:1/probe", "connect", "A", "nothing listens"),
    (
        "32-unresolvable",
        "{S}app:{A}@no-such-host.invalid/probe",
        "connect",
        "A",
        "a host that does not resolve",
    ),
    ("33-percent-not-an-escape", "{S}app:{A}%zz{B}@{H}/probe", "refused", "AB", "`%zz`"),
    ("34-hash", "{S}app:{A}#{B}@{H}/probe", "refused", "AB", "a raw `#` in the password"),
    ("35-space", "{S}app:{A} {B}@{H}/probe", "refused", "AB", "a raw space in the password"),
    ("36-newline", "{S}app:{A}\n{B}@{H}/probe", "refused", "AB", "a raw newline"),
    (
        "37-ampersand-in-query-password",
        "{S}app@{H}/probe?password={A}&{B}",
        "refused",
        "AB",
        "key `password`",
    ),
    (
        "38-leading-space",
        " {S}app:{A}@{B}@{H}/probe",
        "refused",
        "AB",
        "a space before the scheme",
    ),
    ("39-digits-host-forgotten", "{S}app:{D}/probe", "refused", "D", "a port above 65535"),
    (
        "N01-at-then-question",
        "{S}app:{A}@{B}?{C}@{H}/probe",
        "refused",
        "ABC",
        "a query pair without `=`, and a raw `@` in it",
    ),
    (
        "N02-at-slash-question",
        "{S}app:{A}@{B}/{C}?{E}@{H}/probe",
        "refused",
        "ABCE",
        "a query pair without `=`",
    ),
    (
        "N03-at-question-pair",
        "{S}app:{A}@{B}?{C}={E}@{H}/probe",
        "refused",
        "ABCE",
        "key not allowed, and a raw `@` in a value",
    ),
    (
        "N04-at-port-question",
        "{S}app:{A}@{B}:5432?{C}@{H}/probe",
        "refused",
        "ABC",
        "a query pair without `=`",
    ),
    (
        "N05-at-brackets-question",
        "{S}app:{A}@[{B}:{C}]?{E}@{H}/probe",
        "refused",
        "ABCE",
        "a query pair without `=`",
    ),
    (
        "N06-query-password-ampersand-pair",
        "{S}app@{H}/probe?password={A}&{B}={C}",
        "refused",
        "ABC",
        "key `password`",
    ),
    (
        "N07-query-password-then-sslmode",
        "{S}app@{H}/probe?password={A}&sslmode={B}",
        "refused",
        "AB",
        "key `password`",
    ),
    (
        "N08-query-password-ampersand-space",
        "{S}app@{H}/probe?password={A}&{B}%20{C}={E}",
        "refused",
        "ABCE",
        "key `password`",
    ),
    ("N09-negative-port", "{S}app:-{D}/probe", "refused", "D", "a port of more than digits"),
    (
        "R01-allowed-query",
        "{S}app:{A}@{H}/probe?sslmode=disable&connect_timeout=5&application_name=previously",
        "connect",
        "A",
        "three allowed keys",
    ),
    (
        "R02-refused-value-holds-a-piece",
        "{S}app:{A}@{H}/probe?connect_timeout=x{B}",
        "connect",
        "AB",
        "the client refuses the value, and the reason quotes none of it",
    ),
    (
        "R03-cloudnativepg-uri",
        "postgresql://app:Ab+cd%2FEF={A}==@{H}/probe",
        "connect",
        "A",
        "what Go writes: `/` as `%2F`, `+` and `=` raw",
    ),
    ("R04-empty-port", "{S}app:{A}@localhost:/probe", "refused", "A", "a `:` without a port"),
    ("R05-port-zero", "{S}app:{A}@localhost:0/probe", "refused", "A", "port 0"),
    ("R06-nul-escape", "{S}app:{A}%00{B}@{H}/probe", "refused", "AB", "an escaped control"),
    ("R07-not-utf8", "{S}app:{A}%FF{B}@{H}/probe", "refused", "AB", "an escape that is no UTF-8"),
    (
        "R08-repeated-key",
        "{S}app:{A}@{H}/probe?sslmode=disable&sslmode=require",
        "refused",
        "A",
        "a key twice",
    ),
    (
        "R09-ampersand-in-password",
        "{S}app:{A}&{B}@{H}/probe",
        "connect",
        "AB",
        "a raw `&` in the password, as Go writes it (ruling T2-l of the 2026-10-05 delivery plan)",
    ),
    ("R11-nel-in-database", "{S}app:{A}@{H}/pro%C2%85be", "refused", "A", "U+0085 decoded"),
    ("R12-line-separator", "{S}app:{A}@{H}/pro%E2%80%A8be", "refused", "A", "U+2028 decoded"),
    ("R13-paragraph-separator", "{S}app:{A}@{H}/pro%E2%80%A9be", "refused", "A", "U+2029"),
    ("R14-c1-control", "{S}app:{A}@{H}/pro%C2%9Bbe", "refused", "A", "U+009B, a C1 control"),
    ("R15-newline-in-database", "{S}app:{A}@{H}/pro%0Abe", "refused", "A", "an escaped newline"),
    ("R16-empty-label", "{S}app:{A}@a..b/probe", "refused", "A", "a host label that is empty"),
    ("R17-dot-host", "{S}app:{A}@./probe", "refused", "A", "a host of one dot"),
    (
        "R18-long-label",
        "{S}app:{A}@" + "a" * 64 + ".invalid/probe",
        "refused",
        "A",
        "a host label of 64 characters",
    ),
    (
        "R19-ampersand-in-query-value",
        "{S}app:{A}@{H}/probe?application_name=a&b",
        "refused",
        "A",
        "a raw `&` in a query value stays refused",
    ),
    (
        "R10-known-limit",
        "{S}nobody.invalid:54321/probe",
        "connect",
        "",
        "ruling T2-j of the 2026-10-05 delivery plan: no `@`, so the user name is "
        "the host and 54321 the port",
    ),
)

_UNREADABLE = (
    "Error: PREVIOUSLY_DSN is refused — write it as "
    "postgresql://user:password@host:5432/database?key=value with the password "
    "there and nowhere else, percent-encode every character of the user name, the "
    "password, the database name and a value that is not a letter, a digit or one "
    "of -._~ (such as `%40` for `@`), and use no key but application_name, "
    "channel_binding, connect_timeout, require_auth, sslcert, sslkey, sslmode or "
    "sslrootcert\n"
)


@pytest.mark.db
@pytest.mark.parametrize("command", ["log", "migrate"])
@pytest.mark.parametrize(
    ("template", "outcome", "secret", "reason"),
    [form[1:] for form in _FORMS],
    ids=[f[0] for f in _FORMS],
)
def test_no_form_of_the_connection_string_prints_the_password(
    db: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    template: str,
    outcome: str,
    secret: str,
    reason: str,
) -> None:
    """Every connection string the attack reviews tried, through `log` and
    through `migrate`.

    Measured on 2026-10-05: at `fa61473`, forms 4, 15-17 and 23-25 printed a
    piece of the password, through the host or the port in the sentence, or
    in a `ValueError` traceback; at `2579eb5`, N01-N09 did, through the host,
    the database, the port or a key the client library quoted. Three rounds
    of checks after SQLAlchemy's parse each let the next form through;
    `from_dsn` now reads the string by a grammar of its own and refuses what
    is outside it.

    Each piece of the password is 20 characters and is drawn at run time, so
    that an eight-character run of it in the output is no coincidence. Where a
    form joins pieces with specials, the password is longer than one piece.
    """
    url = _session_url(db)
    pieces = {name: secrets.token_hex(10) for name in "ABCE"}
    pieces["D"] = "".join(secrets.choice("0123456789") for _ in range(20))
    dsn = template.format(
        S="postgresql+psycopg://", H=f"{url.host}:{url.port}", port=url.port, **pieces
    )
    monkeypatch.setenv("PREVIOUSLY_DSN", dsn)
    assert main([command]) == 2
    out, err = capsys.readouterr()
    # First, so that a password in the output fails on this line and no other.
    for name in secret:
        assert _no_fragment_of(pieces[name], out + err), f"{reason}: {err}"
    assert out == ""
    # `str.splitlines()`, which also breaks at U+0085, U+2028 and U+2029,
    # the way a log shipper may.
    assert len(err.splitlines()) == 1, f"{reason}: {err!r}"
    if outcome == "refused":
        assert err == _UNREADABLE, f"{reason}: {err}"
    else:
        assert err.startswith("Error: connecting to "), f"{reason}: {err}"


@pytest.mark.db
def test_a_missing_database_names_libpqs_reason(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A database name the server does not know: the same sentence, with
    the server's reason."""
    url = _session_url(db).set(database="no_such_database")
    out, sentence = _log_with(url.render_as_string(hide_password=False), capsys, monkeypatch)
    assert out == ""
    assert sentence.startswith(
        f"Error: connecting to database no_such_database at {url.host}:{url.port} failed: "
    )
    assert 'FATAL:  database "no_such_database" does not exist' in sentence


@pytest.mark.db
def test_a_missing_table_shows_one_sentence(
    unmigrated_engine: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Case 3 out of review finding W2: `log` before `previously migrate`,
    and the sentence names that command, the way an operator has.

    `verify` is in it because it reads through a different entrance to the
    storage than `log` does: `snapshot`, not `begin`, and the translation has
    to hold for both."""
    from sqlalchemy import Engine

    assert isinstance(unmigrated_engine, Engine)
    monkeypatch.setenv(
        "PREVIOUSLY_DSN", unmigrated_engine.url.render_as_string(hide_password=False)
    )
    assert main(["log"]) == 2
    sentence = _single_line(capsys.readouterr().err)
    assert "Traceback" not in sentence
    assert sentence == "Error: database schema incomplete — `previously migrate` has not run yet"
    assert main(["verify"]) == 2
    assert _single_line(capsys.readouterr().err) == sentence


# --- Finding G3: --evidence instead of being fixed to RECOLLECTION -------


@pytest.mark.db
def test_the_evidence_default_is_recollection(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without `--evidence` the cautious assumption stays: reported from
    memory. That was the only behaviour before G3 already — this test holds it
    down as a default, no longer as a pinning."""
    from sqlalchemy import Engine
    from sqlalchemy import select

    assert isinstance(db, Engine)
    monkeypatch.setenv("PREVIOUSLY_DSN", db.url.render_as_string(hide_password=False))
    assert main(["append", "--source", "cli", "--external-id", "a", "--text", "x"]) == 0
    capsys.readouterr()
    from previously.storage.schema import event

    with db.connect() as c:
        payload = c.execute(select(event.c.payload)).scalar_one()
    assert payload["evidence"] == "recollection"


@pytest.mark.db
def test_evidence_verbatim_can_be_chosen(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Finding G3: whoever submits the verbatim wording via the CLI has to be
    able to hold that down as `verbatim` — after the fact it is no longer
    possible, the kind of evidence goes into the hash."""
    from sqlalchemy import Engine
    from sqlalchemy import select

    assert isinstance(db, Engine)
    monkeypatch.setenv("PREVIOUSLY_DSN", db.url.render_as_string(hide_password=False))
    assert (
        main(
            [
                "append",
                "--source",
                "cli",
                "--external-id",
                "a",
                "--text",
                "x",
                "--evidence",
                "verbatim",
            ]
        )
        == 0
    )
    capsys.readouterr()
    from previously.storage.schema import event

    with db.connect() as c:
        payload = c.execute(select(event.c.payload)).scalar_one()
    assert payload["evidence"] == "verbatim"


def test_an_invalid_evidence_value_is_rejected(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """An invalid value yields exit code 2 and a sentence that names the
    permitted values — not a stack trace out of `Evidence(value)` first."""
    monkeypatch.setenv("PREVIOUSLY_DSN", "postgresql+psycopg://unused/unused")
    assert (
        main(
            [
                "append",
                "--source",
                "cli",
                "--external-id",
                "a",
                "--text",
                "x",
                "--evidence",
                "nonsense",
            ]
        )
        == 2
    )
    sentence = _single_line(capsys.readouterr().err)
    assert "verbatim" in sentence
    assert "recollection" in sentence


# --- Finding N1: three paths of the command line that nothing exercised ----
#
# None of the three is an ordinary coverage gap. `cli.py:109` carries the
# assurance an automated caller depends on, `cli.py:71` is the first thing a
# fresh checkout runs into, and `cli.py:120` is the branch that tells "that is
# not the event asked for" from "there is no event".


def test_a_missing_dsn_names_the_environment_variable(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without `PREVIOUSLY_DSN` the command line says what is missing.

    The first wall a fresh checkout walks into, and until now unexercised: the
    sentence out of `_storage()` has to name the variable, because that name
    is the whole instruction for what to do next.
    """
    monkeypatch.delenv("PREVIOUSLY_DSN", raising=False)
    assert main(["log"]) == 2
    sentence = _single_line(capsys.readouterr().err)
    assert "Traceback" not in sentence
    assert "PREVIOUSLY_DSN is not set" in sentence


@pytest.mark.db
def test_verify_prints_the_finding_and_returns_1(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A broken chain: the finding on stdout **and** exit code 1.

    This is the interface at which an automated caller — a cron run, a
    monitoring script — notices that something is amiss; it reads the exit
    code, not the text. Both halves had only ever been run against an intact
    chain, where `verify` prints "chain intact" and returns 0, so the
    assurance stood in the code and in no test.
    """
    from sqlalchemy import Engine
    from sqlalchemy import text

    assert isinstance(db, Engine)
    monkeypatch.setenv("PREVIOUSLY_DSN", db.url.render_as_string(hide_password=False))
    assert main(["append", "--source", "cli", "--external-id", "a", "--text", "Hello"]) == 0
    capsys.readouterr()

    # Only the field `text`, so that the reserved key `evidence` stays
    # standing ({ref}`canonicalization`) and the finding is the one this test
    # is about — the same reasoning as in `test_p5`, and `CAST(... AS jsonb)`
    # for the same reason as well, see the comment there.
    with db.begin() as c:
        c.execute(
            text("UPDATE event SET payload = jsonb_set(payload, '{text}', CAST(:new AS jsonb))"),
            {"new": '"forged"'},
        )

    assert main(["verify"]) == 1
    output = capsys.readouterr().out
    assert "FINDING 1: payload_hash does not match the payload" in output
    assert "chain intact" not in output


@pytest.mark.db
def test_show_does_not_display_the_next_event_instead(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`show 0` must not display event 1.

    `storage.read` filters `id >= from_id`, so asking for an `id` below an
    existing event hands that existing event over — and `show` has to turn it
    down. `test_show_does_not_know_the_event` does not reach this branch: it
    asks for id 99 in an empty table, where `read` yields nothing at all and
    the loop body never runs.
    """
    from sqlalchemy import Engine

    assert isinstance(db, Engine)
    monkeypatch.setenv("PREVIOUSLY_DSN", db.url.render_as_string(hide_password=False))
    assert main(["append", "--source", "cli", "--external-id", "a", "--text", "Hello"]) == 0
    capsys.readouterr()

    assert main(["show", "0"]) == 1
    captured = capsys.readouterr()
    assert "No event 0" in captured.err
    assert "id=1" not in captured.out


# --- Finding W-1: unrepresentable characters out of argv -------------------
#
# A lone UTF-16 surrogate or a null byte is representable in neither the
# database nor the hash. Measured before the fix against a real PostgreSQL 17,
# on stderr of the real command — in-process through `main()` it is one line
# fewer, the console-script frame being absent:
#
#     lone surrogate in --source       96 lines of traceback, UnicodeEncodeError
#     lone surrogate in --external-id  96 lines, the same
#     lone surrogate in --text         10 lines, in cli.py's size check
#
# A surrogate really arrives that way: `argv` carries bytes, and Python decodes
# undecodable ones with `surrogateescape`.
#
# The **null byte** cannot come from a command line — measured, `os.execv` and
# `subprocess.run` refuse an argument containing one with `ValueError: embedded
# null byte`. It reaches `main()` only through a direct call, as below, and
# from stage 2 on through a connector; measured that way it was 89 lines for
# `--source` and `--external-id`, while `--text` already returned 2.
#
# In each case a foreign exception left a layer that is not supposed to know
# it, and the interpreter's exit code 1 replaced this command line's 2 — the
# same class as review finding W2 of the first final review.


@pytest.mark.parametrize(
    ("field", "probe", "expected"),
    [
        # The expected sentence is written out per case instead of derived
        # from the option name: `--external-id` is reported as the field
        # `external_id`, and a null byte in `--text` is caught by the **unit**
        # check and names the unit, not the option. A clever derivation got
        # both of those wrong while looking right.
        ("--source", "\ud800", "source: not representable as UTF-8"),
        ("--source", "\x00", "source contains a null byte"),
        ("--external-id", "\ud800", "external_id: not representable as UTF-8"),
        ("--external-id", "\x00", "external_id contains a null byte"),
        ("--text", "\ud800", "unit 1: not representable as UTF-8"),
        # The text becomes units before it becomes a payload, so the unit
        # check gets there first. That message is pinned in
        # `test_append.py::test_a_null_byte_in_a_unit_is_refused`; what is new
        # here is only that it arrives as one sentence with exit code 2
        # instead of as 89 lines of sqlalchemy.
        ("--text", "\x00", "unit 1 contains a null byte"),
    ],
)
def test_an_unrepresentable_character_in_argv_gives_one_sentence(
    field: str,
    probe: str,
    expected: str,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exit code 2 and a single sentence, for all three fields.

    No database is needed: every case is refused in `append`'s preparation,
    before `storage.begin()` — which is the point of the fix. `source` and
    `external_id` are checked in `core.append` now, because the
    canonicalisation ({ref}`payload-range`) would decide about them only
    inside `event_hash`, that is **after** `storage.lookup` has carried them
    into the driver. The text was already covered by `payload_hash`; what
    crashed for it was `cli.py`'s size check.
    """
    monkeypatch.setenv("PREVIOUSLY_DSN", "postgresql+psycopg://unused/unused")
    argv = ["append", "--source", "cli", "--external-id", "x1", "--text", "hello"]
    argv[argv.index(field) + 1] = f"value{probe}"

    assert main(argv) == 2
    sentence = _single_line(capsys.readouterr().err)
    assert "Traceback" not in sentence
    assert expected in sentence


# --- Stage 1b: the three projection commands -------------------------------


def test_escape_field_folds_tab_newline_return_and_backslash_into_two_characters_each() -> None:
    """One unit is one line ({ref}`cli-reference`) plus review focus 3.

    The escaping is reversible because the backslash is escaped first.
    """
    assert escape_field("a\tb\nc\rd\\e") == "a\\tb\\nc\\rd\\\\e"
    assert escape_field("plain") == "plain"


# Terminal commands a stranger can write into a mail: an OSC sequence that
# sets the window title, ended by BEL; a CSI sequence that turns text red,
# once with ESC and `[`, once as the one C1 character U+009B; DEL.
HOSTILE = "\x1b]0;Titel gesetzt\x07Rot: \x1b[31mja\x9b0m\x7f"
HOSTILE_ESCAPED = "\\x1b]0;Titel gesetzt\\x07Rot: \\x1b[31mja\\x9b0m\\x7f"


def _raw_controls(text: str) -> list[str]:
    """Every control character in `text` but tab and line feed."""
    return [c for c in text if (ord(c) < 0x20 and c not in "\t\n") or 0x7F <= ord(c) <= 0x9F]


def test_escape_controls_writes_every_control_but_tab_and_line_feed_as_hex() -> None:
    assert escape_controls(HOSTILE) == HOSTILE_ESCAPED
    assert escape_controls("\x00\r\x1f\x80\x9f") == "\\x00\\x0d\\x1f\\x80\\x9f"


def test_escape_controls_keeps_tab_line_feed_and_every_other_character() -> None:
    """The control of the test above: text, tabs and line breaks pass."""
    text = "Grüße\tan alle\nÄ € \xa0 \u2028 \\x1b"
    assert escape_controls(text) == text


def test_escape_field_writes_a_control_as_hex_and_stays_reversible() -> None:
    """A control and the four characters it already escaped; a literal
    backslash and `x1b` stay apart from an ESC."""
    assert escape_field(HOSTILE) == HOSTILE_ESCAPED
    assert escape_field("\\x1b\x1b\t") == "\\\\x1b\\x1b\\t"


@pytest.mark.db
def test_show_and_chronicle_print_no_control_of_a_unit_or_a_payload_raw(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A mail puts what its sender wrote into the units and the payload:
    `show` writes each control as `\\xNN` in a unit and as `\\u00NN` in the
    JSON of the payload, and keeps a unit's line break; `chronicle` writes
    each as `\\xNN`. The log holds the text unchanged."""
    from sqlalchemy import Engine

    assert isinstance(db, Engine)
    _setup(db, monkeypatch)
    storage = PostgresStorage(db)
    moment = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)
    event = RawEvent(
        source="email",
        external_id="hostile@example.org",
        occurred_at=moment,
        evidence=Evidence.VERBATIM,
        units=split_plaintext(f"{HOSTILE}\nzweite Zeile"),
        payload={"headers": [["Subject", HOSTILE]]},
    )
    append(storage, [event], recorded_at=moment)

    assert main(["show", "1"]) == 0
    out = capsys.readouterr().out
    assert _raw_controls(out) == []
    assert f"  ¶1 {HOSTILE_ESCAPED}\nzweite Zeile\n" in out
    (line,) = [line for line in out.splitlines() if line.startswith("payload=")]
    assert json.loads(line.removeprefix("payload="))["headers"] == [["Subject", HOSTILE]]
    assert "\\u001b]0;Titel gesetzt\\u0007" in line
    assert "\\u009b0m\\u007f" in line

    assert main(["project"]) == 0
    capsys.readouterr()
    assert main(["chronicle"]) == 0
    out = capsys.readouterr().out
    assert _raw_controls(out) == []
    assert out.endswith(f"\temail\thostile@example.org\t{HOSTILE_ESCAPED}\\nzweite Zeile\n")
    with storage.begin() as conn:
        assert [unit.content for unit in storage.units(conn, 1)] == [f"{HOSTILE}\nzweite Zeile"]


def _setup(db: object, monkeypatch: pytest.MonkeyPatch) -> None:
    from sqlalchemy import Engine

    assert isinstance(db, Engine)
    monkeypatch.setenv("PREVIOUSLY_DSN", db.url.render_as_string(hide_password=False))


def _append(source: str, external_id: str, text: str, occurred_at: str) -> None:
    argv = ["append", "--source", source, "--external-id", external_id, "--text", text]
    assert main([*argv, "--occurred-at", occurred_at]) == 0


@pytest.mark.db
def test_project_on_an_empty_log_is_up_to_date_at_zero_but_still_names_a_rebuild(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review focus 5. Nothing was built, so it does not say `built`.

    The second half pins the order inside `_describe` (ruling P-1 of the
    2026-10-04 stage 1b plan, recorded in
    `docs/superpowers/sdd/2026-10-04-stufe-1b-projektionen/progress.md`): a
    version change is reported even when the run projected no event, because
    it changed the state row all the same. Measured by mutation — with the
    `events == 0` branch moved above the version branch, the second half goes
    red and the first stays green.
    """
    from sqlalchemy import Engine
    from sqlalchemy import text

    assert isinstance(db, Engine)
    _setup(db, monkeypatch)
    assert main(["project"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "chronicle       up to date, up_to_id 0",
        "source-stats    up to date, up_to_id 0",
        "graph           up to date, up_to_id 0",
    ]

    with db.begin() as c:
        c.execute(text("UPDATE projection_state SET version = 4 WHERE name = 'chronicle'"))
    assert main(["project"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "chronicle       rebuilt: version 4 -> 3, 0 events, up_to_id 0",
        "source-stats    up to date, up_to_id 0",
        "graph           up to date, up_to_id 0",
    ]


@pytest.mark.db
def test_project_says_which_path_it_took(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """All four paths: `built`, `caught up`, `up to date`, `rebuilt`.

    The first run has to come *after* the first append — a run on the empty
    log already writes the state row, and every later run is an ordinary
    catch-up (found by the plan's pre-flight scan).
    """
    from sqlalchemy import Engine
    from sqlalchemy import text

    assert isinstance(db, Engine)
    _setup(db, monkeypatch)
    _append("email", "m1", "Hello\n\nWorld", "2026-10-01T09:00:00Z")
    capsys.readouterr()
    assert main(["project"]) == 0
    first = capsys.readouterr().out.splitlines()
    assert first == [
        "chronicle       built: 1 event, up_to_id 1",
        "source-stats    built: 1 event, up_to_id 1",
        "graph           built: 1 event, up_to_id 1",
    ]

    _append("email", "m2", "Again", "2026-10-02T09:00:00Z")
    capsys.readouterr()
    assert main(["project"]) == 0
    second = capsys.readouterr().out.splitlines()
    assert second == [
        "chronicle       caught up: 1 event, up_to_id 2",
        "source-stats    caught up: 1 event, up_to_id 2",
        "graph           caught up: 1 event, up_to_id 2",
    ]

    assert main(["project"]) == 0
    third = capsys.readouterr().out.splitlines()
    assert third == [
        "chronicle       up to date, up_to_id 2",
        "source-stats    up to date, up_to_id 2",
        "graph           up to date, up_to_id 2",
    ]

    # The fourth path, and the only one invisible in the table itself: the
    # stored version is raised past the one the code declares, the way a
    # rolled-back release leaves it, and the next run empties `p_chronicle` and
    # builds it again. Without this line `rebuilt:` would be a format the
    # reference page promises and nothing produces. `source-stats` and
    # `graph` are left alone, so the projections report different paths in
    # the same run.
    with db.begin() as c:
        c.execute(text("UPDATE projection_state SET version = 4 WHERE name = 'chronicle'"))
    capsys.readouterr()
    assert main(["project"]) == 0
    fourth = capsys.readouterr().out.splitlines()
    assert fourth == [
        "chronicle       rebuilt: version 4 -> 3, 2 events, up_to_id 2",
        "source-stats    up to date, up_to_id 2",
        "graph           up to date, up_to_id 2",
    ]


@pytest.mark.db
def test_chronicle_prints_one_line_per_unit_in_time_order_with_the_source(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Time order, not chain order ({ref}`projections`).

    Event 2 happened before event 1. Event 3 carries no source attribution,
    which is the only way to reach the two empty fields the reference page
    promises: `append` always writes a `source_key`, so the sourceless event
    goes in through `insert_event` with no key, the way
    `test_projection_worker.py` builds one.

    Event 4 carries a tab in `--source` and a newline in `--external-id`, and
    both are reachable over the command line: `core.append` refuses a null
    byte and a lone surrogate there, nothing else. Measured on 2026-10-04
    with `escape_field` applied to `content` alone, as it was until then: that
    one unit came out as **two** lines with six and two tab-separated fields
    instead of one line with six, so a consumer splitting on tabs read one
    unit as two records with the fields shifted. Hence the field count below,
    which is the assurance the reference page makes.
    """
    from sqlalchemy import Engine

    assert isinstance(db, Engine)
    _setup(db, monkeypatch)
    _append("email", "m1", "late", "2026-10-02T09:00:00Z")
    _append("chat", "c1", "early\ttab", "2026-10-01T09:00:00Z")
    storage = PostgresStorage(db)
    with storage.begin() as conn:
        tip = storage.tip(conn)
        assert tip is not None
        orphan = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
        storage.insert_event(
            conn,
            # The hash fields are arbitrary 32-byte values: nothing in this
            # test verifies the chain, and `hash` and `prev_hash` only have to
            # satisfy their unique indexes.
            EventRow(
                3,
                "observation",
                orphan,
                orphan,
                tip.hash,
                b"\x03" * 32,
                b"\x04" * 32,
                b"\x05" * 32,
                {},
            ),
            [UnitRow(3, 1, "orphan")],
            None,
        )
    _append("de\tsk", "id\nx", "raw", "2026-10-03T09:00:00Z")
    main(["project"])
    capsys.readouterr()
    assert main(["chronicle"]) == 0
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        "2\t1\t2026-10-01T09:00:00+00:00\tchat\tc1\tearly\\ttab",
        "3\t1\t2026-10-01T12:00:00+00:00\t\t\torphan",
        "1\t1\t2026-10-02T09:00:00+00:00\temail\tm1\tlate",
        "4\t1\t2026-10-03T09:00:00+00:00\tde\\tsk\tid\\nx\traw",
    ]
    # One record is one line with six fields, whatever the fields carry.
    assert [len(line.split("\t")) for line in out.splitlines()] == [6, 6, 6, 6]
    assert err == ""  # up to date: silence


@pytest.mark.db
def test_both_reading_commands_report_the_lag_on_stderr_and_only_there(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """One event appended and nothing projected, so both commands are behind.

    The second half pulls the two bookmarks apart by hand, because that is the
    only state in which a command reading the **other** projection's bookmark
    looks any different: with both projections current, and with both at zero
    as in the first half, the wrong bookmark gives the right number.
    """
    from sqlalchemy import Engine
    from sqlalchemy import text

    assert isinstance(db, Engine)
    _setup(db, monkeypatch)
    _append("email", "m1", "x", "2026-10-01T09:00:00Z")
    capsys.readouterr()
    assert main(["chronicle"]) == 0
    out, err = capsys.readouterr()
    assert out == ""
    assert err.strip() == "projection is 1 event behind; run `previously project`"
    assert main(["stats"]) == 0
    out, err = capsys.readouterr()
    assert out == ""
    assert err.strip() == "projection is 1 event behind; run `previously project`"

    main(["project"])
    capsys.readouterr()
    with db.begin() as c:
        c.execute(text("UPDATE projection_state SET up_to_id = 0 WHERE name = 'source-stats'"))
    assert main(["chronicle"]) == 0
    assert capsys.readouterr().err == ""
    assert main(["stats"]) == 0
    assert capsys.readouterr().err.strip() == (
        "projection is 1 event behind; run `previously project`"
    )


@pytest.mark.db
def test_chronicle_window_is_half_open_and_an_empty_window_is_not_truncated(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review focus 1 folded in: `--since` at or after `--until` prints nothing.

    It returns 0 and says nothing on standard error — an empty window is not a
    cut one, and the truncation notice would read as though it were.
    """
    _setup(db, monkeypatch)
    for n, day in enumerate(("01", "02", "03"), start=1):
        _append("email", f"m{n}", f"day {day}", f"2026-10-{day}T09:00:00Z")
    main(["project"])
    capsys.readouterr()
    inside = ["chronicle", "--since", "2026-10-01T09:00:00Z", "--until", "2026-10-03T09:00:00Z"]
    assert main(inside) == 0
    out, err = capsys.readouterr()
    assert [line.split("\t")[-1] for line in out.splitlines()] == ["day 01", "day 02"]
    assert err == ""
    backward = ["chronicle", "--since", "2026-10-05T00:00:00Z", "--until", "2026-10-01T00:00:00Z"]
    assert main(backward) == 0
    out, err = capsys.readouterr()
    assert (out, err) == ("", "")
    # `since == until`: the half-open window of zero length, carried over from
    # the Task 3 review. Half-open means it holds nothing, not everything.
    empty = ["chronicle", "--since", "2026-10-02T09:00:00Z", "--until", "2026-10-02T09:00:00Z"]
    assert main(empty) == 0
    out, err = capsys.readouterr()
    assert (out, err) == ("", "")


@pytest.mark.db
def test_chronicle_limit_warns_on_stderr_when_it_cuts_and_not_otherwise(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The truncation notice, its absence, the `--limit` bolt — and the order.

    The third part is the only place where both notices fire in one run, and
    until it existed the order in which `chronicle` prints them was unchecked;
    {ref}`cli-reference` had them the other way round and nothing noticed.
    """
    _setup(db, monkeypatch)
    for n in range(1, 4):
        _append("email", f"m{n}", f"u{n}", f"2026-10-0{n}T09:00:00Z")
    main(["project"])
    capsys.readouterr()
    assert main(["chronicle", "--limit", "2"]) == 0
    out, err = capsys.readouterr()
    assert len(out.splitlines()) == 2
    assert err.strip() == "output truncated at 2 lines; raise --limit or narrow --since/--until"
    assert main(["chronicle", "--limit", "3"]) == 0
    out, err = capsys.readouterr()
    assert (len(out.splitlines()), err) == (3, "")

    # A fourth event, appended and deliberately not projected: the window is
    # cut *and* the projection is behind, so both notices fire in one run and
    # their order can be checked. The truncation comes first.
    _append("email", "m4", "u4", "2026-10-04T09:00:00Z")
    capsys.readouterr()
    assert main(["chronicle", "--limit", "2"]) == 0
    out, err = capsys.readouterr()
    assert len(out.splitlines()) == 2
    assert err.splitlines() == [
        "output truncated at 2 lines; raise --limit or narrow --since/--until",
        "projection is 1 event behind; run `previously project`",
    ]

    # A limit below one is refused before the read, through the same path as
    # every other user error: exit code 2, one sentence, nothing on stdout.
    # Measured without the guard: `--limit 0` returned 0 and claimed `output
    # truncated at 0 lines` with no line printed, and `--limit -2` came back
    # as `sqlalchemy.exc.DataError: LIMIT must not be negative` — a stack
    # trace and exit code 1, which is the shape of review finding W2.
    for limit in ("0", "-2"):
        assert main(["chronicle", "--limit", limit]) == 2
        out, err = capsys.readouterr()
        assert out == ""
        assert err.strip() == f"Error: --limit must be at least 1, got {limit}"


@pytest.mark.db
def test_chronicle_rejects_a_naive_since(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review focus 2: the same `parse_moment` as `--occurred-at`."""
    _setup(db, monkeypatch)
    assert main(["chronicle", "--since", "2026-10-01T09:00:00"]) == 2
    assert "time zone" in capsys.readouterr().err


@pytest.mark.db
def test_stats_prints_one_line_per_source(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The fourth source carries a tab in its name, for the reason
    `test_chronicle_prints_one_line_per_unit_in_time_order_with_the_source`
    gives. Measured on 2026-10-04 with `stats` escaping nothing, as it was
    until then: that line came out with **six** tab-separated fields instead
    of five.
    """
    _setup(db, monkeypatch)
    _append("email", "m1", "a\n\nb", "2026-10-02T09:00:00Z")
    _append("email", "m2", "c", "2026-10-01T09:00:00Z")
    _append("chat", "c1", "d", "2026-10-03T09:00:00Z")
    _append("de\tsk", "d1", "e", "2026-10-04T09:00:00Z")
    main(["project"])
    capsys.readouterr()
    assert main(["stats"]) == 0
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        "chat\t1\t1\t2026-10-03T09:00:00+00:00\t2026-10-03T09:00:00+00:00",
        "de\\tsk\t1\t1\t2026-10-04T09:00:00+00:00\t2026-10-04T09:00:00+00:00",
        "email\t2\t3\t2026-10-01T09:00:00+00:00\t2026-10-02T09:00:00+00:00",
    ]
    assert [len(line.split("\t")) for line in out.splitlines()] == [5, 5, 5]
    assert err == ""


_HINT = (
    "no anchor given: verify attests that the log is unchanged, "
    "not that it is complete; see `previously anchor`\n"
)


@pytest.mark.db
def test_verify_without_an_anchor_says_what_it_does_not_attest(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Standard output stays the one line scripts read; the limit of the
    statement goes to standard error ({ref}`external-anchor`). Beside a
    finding the hint would be noise, so the second half has none."""
    from sqlalchemy import Engine
    from sqlalchemy import text

    assert isinstance(db, Engine)
    _setup(db, monkeypatch)
    _append("email", "m1", "Hello", "2026-10-01T09:00:00Z")
    capsys.readouterr()

    assert main(["verify"]) == 0
    out, err = capsys.readouterr()
    assert out == "chain intact\n"
    assert err == _HINT

    with db.begin() as c:
        c.execute(text("UPDATE event SET hash = :h WHERE id = 1"), {"h": b"\x00" * 32})
    assert main(["verify"]) == 1
    out, err = capsys.readouterr()
    assert out.startswith("FINDING 1: ")
    assert err == ""


@pytest.mark.db
def test_anchor_prints_the_tip_and_verify_holds_it(
    db: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """The routine end to end: anchor, check, grow, check again."""
    _setup(db, monkeypatch)
    _append("email", "m1", "one", "2026-10-01T09:00:00Z")
    _append("email", "m2", "two", "2026-10-02T09:00:00Z")
    capsys.readouterr()

    assert main(["anchor"]) == 0
    line, err = capsys.readouterr()
    assert re.fullmatch(r"2 [0-9a-f]{64}\n", line)
    assert err == ""
    assert main(["show", "2"]) == 0
    assert f"hash={line.split()[1]}\n" in capsys.readouterr().out  # the tip, not some hash

    anchors = tmp_path / "anchors.txt"
    anchors.write_text(line, encoding="utf-8")
    assert main(["verify", "--anchors", str(anchors)]) == 0
    out, err = capsys.readouterr()
    assert (out, err) == ("chain intact, 1 anchor holds\n", "")
    assert main(["verify", "--anchors", str(anchors), "--exact"]) == 0
    out, err = capsys.readouterr()
    assert (out, err) == ("chain intact, 1 anchor holds, the tip is the newest anchor\n", "")

    _append("email", "m3", "three", "2026-10-03T09:00:00Z")
    capsys.readouterr()
    assert main(["verify", "--anchors", str(anchors), "--exact"]) == 1
    assert capsys.readouterr().out == "FINDING 3: the log continues past the newest anchor (2)\n"

    assert main(["anchor"]) == 0
    with anchors.open("a", encoding="utf-8") as handle:
        handle.write(capsys.readouterr().out)
    assert main(["verify", "--anchors", str(anchors), "--exact"]) == 0
    expected = "chain intact, 2 anchors hold, the tip is the newest anchor\n"
    assert capsys.readouterr().out == expected


@pytest.mark.db
def test_verify_reports_a_deleted_tip_against_the_anchor(
    db: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """The case stage 1a measured, at the surface a cron job reads: without
    an anchor exit code 0, with one exit code 1 and the finding."""
    from sqlalchemy import Engine
    from sqlalchemy import text

    assert isinstance(db, Engine)
    _setup(db, monkeypatch)
    for n in (1, 2, 3):
        _append("email", f"m{n}", f"text {n}", f"2026-10-0{n}T09:00:00Z")
    capsys.readouterr()
    assert main(["anchor"]) == 0
    anchors = tmp_path / "anchors.txt"
    anchors.write_text(capsys.readouterr().out, encoding="utf-8")

    with db.begin() as c:
        c.execute(text("DELETE FROM source_key WHERE event_id = 3"))
        c.execute(text("DELETE FROM unit WHERE event_id = 3"))
        c.execute(text("DELETE FROM event WHERE id = 3"))

    assert main(["verify"]) == 0
    assert capsys.readouterr().out == "chain intact\n"
    assert main(["verify", "--anchors", str(anchors)]) == 1
    out, err = capsys.readouterr()
    assert out == "FINDING 3: anchored event is missing (the log ends at 2)\n"
    assert err == ""


@pytest.mark.db
@pytest.mark.parametrize(
    ("content", "fragment"),
    [
        (b"1 zz\n", "anchor line 1"),
        (b"", "Error: the input holds no anchor"),
        (b"\xff\xfe\x00junk", "not UTF-8"),
        (None, "cannot read the anchor file"),
    ],
)
def test_a_broken_anchor_file_is_an_input_error(
    db: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    content: bytes | None,
    fragment: str,
) -> None:
    """A file that is no anchor file is an input error: exit code 2 and one
    sentence, never a traceback, and nothing on standard output — no half
    result. `None` is the file that does not exist. (Review focus 2 of the
    2026-10-04 external-anchor plan.)"""
    _setup(db, monkeypatch)
    _append("email", "m1", "Hello", "2026-10-01T09:00:00Z")
    capsys.readouterr()
    anchors = tmp_path / "anchors.txt"
    if content is not None:
        anchors.write_bytes(content)

    assert main(["verify", "--anchors", str(anchors)]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err.startswith("Error: ")
    assert fragment in err


@pytest.mark.db
def test_a_directory_as_anchor_file_is_an_input_error(
    db: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """A directory is the third shape of "not a file", after the one that is
    missing and the one that is not text: same exit code, same kind of
    sentence. (Review focus 2 of the 2026-10-04 external-anchor plan.)"""
    _setup(db, monkeypatch)
    assert main(["verify", "--anchors", str(tmp_path)]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err.startswith("Error: cannot read the anchor file")


def test_exact_without_anchors_is_an_input_error(capsys: pytest.CaptureFixture[str]) -> None:
    """Refused before the database is even asked for, which is why this test
    needs none."""
    assert main(["verify", "--exact"]) == 2
    out, err = capsys.readouterr()
    assert (out, err) == ("", "Error: --exact needs --anchors\n")


@pytest.mark.db
def test_anchor_says_nothing_on_an_empty_log_and_refuses_a_broken_chain(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """An anchor on a broken chain would certify the break
    ({ref}`external-anchor`).

    On a broken chain, standard output stays empty and the finding goes to
    standard error. The routine appends standard output to the anchor file
    with `previously anchor >> anchors.txt`, so a finding printed there would
    become a line of that file, and the next `verify --anchors` would refuse
    the file as an input error, exit code 2, instead of reporting the finding
    with exit code 1."""
    from sqlalchemy import Engine
    from sqlalchemy import text

    assert isinstance(db, Engine)
    _setup(db, monkeypatch)
    assert main(["anchor"]) == 0
    out, err = capsys.readouterr()
    assert (out, err) == ("", "the log is empty: nothing to anchor\n")

    _append("email", "m1", "Hello", "2026-10-01T09:00:00Z")
    capsys.readouterr()
    with db.begin() as c:
        c.execute(text("UPDATE event SET hash = :h WHERE id = 1"), {"h": b"\x00" * 32})
    assert main(["anchor"]) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert err.startswith("FINDING 1: ")
    assert not re.search(r"^1 [0-9a-f]{64}$", err, flags=re.MULTILINE)


@pytest.mark.db
def test_verify_reads_the_anchors_from_standard_input(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`-` is not a convenience: it is how a host with docker-compose runs
    the check without mounting the file into the container
    ({ref}`external-anchor`)."""
    _setup(db, monkeypatch)
    _append("email", "m1", "Hello", "2026-10-01T09:00:00Z")
    capsys.readouterr()
    assert main(["anchor"]) == 0
    line = capsys.readouterr().out

    # As bytes, the way a pipe delivers them: `io.StringIO` has no `.buffer`.
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(line.encode())))
    assert main(["verify", "--anchors", "-"]) == 0
    assert capsys.readouterr().out == "chain intact, 1 anchor holds\n"


@pytest.mark.db
def test_a_byte_order_mark_and_windows_line_ends_on_standard_input_are_read(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Standard input is read the way a file is, so what an editor on another
    system leaves in a file it also leaves in a pipe, and it is read all the
    same. The `-` twin of the test for the file. (Review focus 1 of the
    2026-10-04 external-anchor plan.)"""
    _setup(db, monkeypatch)
    _append("email", "m1", "Hello", "2026-10-01T09:00:00Z")
    capsys.readouterr()
    assert main(["anchor"]) == 0
    line = capsys.readouterr().out.strip()

    data = b"\xef\xbb\xbf# kept outside\r\n" + line.encode() + b"\r\n"
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(data)))
    assert main(["verify", "--anchors", "-"]) == 0
    assert capsys.readouterr().out == "chain intact, 1 anchor holds\n"


def test_bytes_that_are_not_utf8_on_standard_input_are_an_input_error(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exit code 2 and one sentence, never a traceback: a traceback leaves
    the interpreter's exit code 1, and 1 tells a scheduled job that the log
    was tampered with when only its input was broken. Refused before the
    database is asked for, which is why this test needs none. (Review focus
    2 of the 2026-10-04 external-anchor plan.)"""
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b"\xff\xfe junk\n")))
    assert main(["verify", "--anchors", "-"]) == 2
    out, err = capsys.readouterr()
    assert (out, err) == ("", "Error: standard input is not UTF-8 text\n")


@pytest.mark.db
def test_an_anchor_file_with_a_byte_order_mark_and_windows_line_ends_is_read(
    db: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """A byte order mark and Windows line ends are what an editor on another
    system leaves behind, and the file is read all the same. (Review focus 1
    of the 2026-10-04 external-anchor plan.)"""
    _setup(db, monkeypatch)
    _append("email", "m1", "Hello", "2026-10-01T09:00:00Z")
    capsys.readouterr()
    assert main(["anchor"]) == 0
    line = capsys.readouterr().out.strip()

    anchors = tmp_path / "anchors.txt"
    anchors.write_bytes(b"\xef\xbb\xbf# kept outside\r\n" + line.encode() + b"\r\n")
    assert main(["verify", "--anchors", str(anchors)]) == 0
    assert capsys.readouterr().out == "chain intact, 1 anchor holds\n"


# --- One sequence declares the commands --------------------------------------


def test_the_help_names_exactly_the_commands_of_the_sequence(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`main` builds its subparsers and its dispatch from `COMMANDS`, so a
    command cannot be in one and not in the other. What is left to hold is
    that nobody adds a subparser beside the sequence: that one would parse,
    and then end in a `KeyError` traceback at the dispatch. Read through the
    public surface, `previously --help`, rather than through `argparse`'s
    private attributes, because the help lists every subparser `main` added,
    whichever way it was added.

    The order is held too: the reference and `--help` list the commands in
    the order of the sequence.
    """
    with pytest.raises(SystemExit) as exit_info:
        main(["--help"])
    assert exit_info.value.code == 0
    out = capsys.readouterr().out
    listed = re.search(r"^  \{([a-z,]+)\}$", out, flags=re.MULTILINE)
    assert listed is not None, out
    assert listed.group(1).split(",") == [command.name for command in COMMANDS]
    for command in COMMANDS:
        assert re.search(rf"^    {command.name} +{re.escape(command.help)}$", out, re.MULTILINE)


# --- redact ({ref}`erasure`) -------------------------------------------------

# The `write_version_1` fixture from `conftest.py`, under a `type` alias for
# the reason its docstring gives.
type WriteVersion1 = Callable[[PostgresStorage, Sequence[RawEvent], datetime], list[int]]


def _connect(db: object, monkeypatch: pytest.MonkeyPatch) -> Engine:
    from sqlalchemy import Engine

    assert isinstance(db, Engine)
    monkeypatch.setenv("PREVIOUSLY_DSN", db.url.render_as_string(hide_password=False))
    return db


@pytest.mark.db
def test_redact_event_prints_the_redaction_and_show_names_it(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _connect(db, monkeypatch)
    assert main(["append", "--source", "cli", "--external-id", "a", "--text", "One\n\nTwo"]) == 0
    capsys.readouterr()

    # Nothing was projected before, so the catch-up after the redaction
    # builds all three projections and says so on standard error.
    assert main(["redact", "event", "1", "--reason", "wrong recipient"]) == 0
    out, err = capsys.readouterr()
    assert (out, err) == (
        "redacted by event 2\n",
        "chronicle       built: 2 events, up_to_id 2\n"
        "source-stats    built: 2 events, up_to_id 2\n"
        "graph           built: 2 events, up_to_id 2\n",
    )

    assert main(["show", "1"]) == 0
    output = capsys.readouterr().out
    assert (
        "payload=<erased by event 2>\n  ¶1 <erased by event 2>\n  ¶2 <erased by event 2>\n"
        in output
    )
    assert "evidence=" not in output

    assert main(["show", "2"]) == 0
    output = capsys.readouterr().out
    assert "id=2 kind=action" in output
    assert (
        'payload={"action": "redaction", "reason": "wrong recipient", "scope": "event", '
        '"target": {"blobs": [], "event": 1}}'
    ) in output
    assert "evidence=" not in output
    assert main(["verify"]) == 0


def _payload_standing(event_id: int) -> str:
    return (
        f"the payload of event {event_id} is not erased and holds the wording of an "
        f"erased unit; `previously redact event {event_id}` erases it\n"
    )


def _append_with_text_in_payload(engine: Engine, text_: str) -> None:
    """Event 1, written through `core` with its text in the units and, which
    `append --text` does not write, under `text` in the payload as well."""
    append(
        PostgresStorage(engine),
        [
            RawEvent(
                source="cli",
                external_id="a",
                occurred_at=datetime(2026, 10, 1, 9, 0, 0, tzinfo=UTC),
                evidence=Evidence.RECOLLECTION,
                units=split_plaintext(text_),
                payload={"text": text_},
            )
        ],
        recorded_at=datetime(2026, 10, 2, 12, 0, 0, tzinfo=UTC),
    )


@pytest.mark.db
def test_redacting_an_approved_proposal_says_that_its_approval_keeps_its_words(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ruling F-19 of the 2026-10-12 assertions plan: the approval stands
    with the proposal's words when the proposal is erased on its own, and
    the line on standard output would read as if the words were gone. The
    redaction of the approval itself, and of a proposal nobody approved,
    are the controls: neither says it."""
    storage = _assertion_log(db, monkeypatch)
    approved, lone = _propose(storage, _debt(), _debt(what="lone"))
    assert main(["approve", str(approved), "--yes"]) == 0
    approval = lone + 1
    capsys.readouterr()

    assert main(["redact", "event", str(approved), "--reason", "r"]) == 0
    assert capsys.readouterr().err.splitlines()[-1] == (
        f"the approval {approval} still carries the words of the proposal {approved}; "
        f"redact event {approval} to erase them too"
    )
    for target in (lone, approval):
        assert main(["redact", "event", str(target), "--reason", "r"]) == 0
        assert "approval" not in capsys.readouterr().err


@pytest.mark.db
def test_redact_units_on_an_event_of_append_leaves_no_text_and_says_nothing(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`append --text` writes the text into the units alone, so `redact
    units` erases it, `show` no longer has it anywhere, and no notice about
    the payload comes. Measured on 2026-10-05 with the text copied into the
    payload again: the notice came."""
    _connect(db, monkeypatch)
    submit = ["append", "--source", "cli", "--external-id", "a", "--text", "One\n\nTwo"]
    assert main(submit) == 0
    assert main(["project"]) == 0
    capsys.readouterr()

    assert main(["redact", "units", "1", "2", "--reason", "r"]) == 0
    assert capsys.readouterr() == ("redacted by event 2\n", "")

    assert main(["show", "1"]) == 0
    output = capsys.readouterr().out
    # The payload keeps the artifact hash, which is no wording: a digest of
    # the text, not the text ({ref}`artifact-identity`).
    artifact = artifact_hash_of({"text": "One\n\nTwo", "attachments": []}).hex()
    payload = f'{{"artifact_hash": "{artifact}", "evidence": "recollection"}}'
    assert f"payload={payload}\n  ¶1 One\n  ¶2 <erased by event 2>\n" in output
    assert "Two" not in output


@pytest.mark.db
def test_redact_units_says_when_the_payload_holds_the_wording(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A payload that holds the wording of an erased unit keeps it after
    `redact units`. Standard output keeps its one line and the exit code
    stays 0; the notice on standard error says so. A rerun that finds the
    units covered has no wording left to compare and says nothing. The
    control: once `redact event` has erased the payload, `redact units` on
    the same event prints no such notice either. Measured on 2026-10-05
    with `payload_holds_wording` always `False`: the first comparison
    failed; always `True`: the second."""
    engine = _connect(db, monkeypatch)
    _append_with_text_in_payload(engine, "One\n\nTwo")
    assert main(["project"]) == 0
    capsys.readouterr()

    assert main(["redact", "units", "1", "2", "--reason", "r"]) == 0
    assert capsys.readouterr() == ("redacted by event 2\n", _payload_standing(1))
    assert main(["redact", "units", "1", "2", "--reason", "r"]) == 0
    assert capsys.readouterr() == ("already redacted by event 2\n", "unit 2 was already erased\n")

    assert main(["show", "1"]) == 0
    assert '"text": "One\\n\\nTwo"' in capsys.readouterr().out

    assert main(["redact", "event", "1", "--reason", "r"]) == 0
    capsys.readouterr()
    assert main(["redact", "units", "1", "1", "--reason", "r"]) == 0
    assert capsys.readouterr() == ("already redacted by event 3\n", "unit 1 was already erased\n")


@pytest.mark.db
def test_redact_units_names_each_tombstone(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each erased unit names the redaction that ordered it, and the payload
    and the unit left standing print as before."""
    engine = _connect(db, monkeypatch)
    _append_with_text_in_payload(engine, "One\n\nTwo\n\nThree")
    assert main(["redact", "units", "1", "3", "--reason", "r"]) == 0
    assert main(["redact", "units", "1", "1", "3", "--reason", "r"]) == 0
    out, err = capsys.readouterr()
    assert out == "redacted by event 2\nredacted by event 3\n"
    # The first `redact` builds the projections, which nobody had built; the
    # second only catches up and says nothing about it. Both say that the
    # payload, which holds the whole text under `text`, holds the wording of
    # a unit they erased: unit 3 in the first, unit 1 in the second.
    standing = _payload_standing(1)
    assert err == (
        "chronicle       built: 2 events, up_to_id 2\n"
        "source-stats    built: 2 events, up_to_id 2\n"
        "graph           built: 2 events, up_to_id 2\n"
        f"{standing}"
        "unit 3 was already erased\n"
        f"{standing}"
    )

    assert main(["show", "1"]) == 0
    output = capsys.readouterr().out
    assert "evidence=recollection" in output
    assert "  ¶1 <erased by event 3>\n  ¶2 Two\n  ¶3 <erased by event 2>\n" in output


@pytest.mark.db
def test_redacting_twice_says_already(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _connect(db, monkeypatch)
    assert main(["append", "--source", "cli", "--external-id", "a", "--text", "One"]) == 0
    assert main(["redact", "event", "1", "--reason", "r"]) == 0
    capsys.readouterr()

    assert main(["redact", "event", "1", "--reason", "r"]) == 0
    assert capsys.readouterr() == ("already redacted by event 2\n", "")


@pytest.mark.parametrize(
    ("arguments", "refusal"),
    [
        pytest.param(["event", "9"], "there is no event 9", id="missing-event"),
        pytest.param(
            ["event", "3"],
            "event 3 is a redaction, and a redaction cannot be redacted",
            id="a-redaction",
        ),
        pytest.param(
            ["units", "2", "1"],
            "event 2 was written in hash format 1, which attests its units only "
            "together: use `previously redact event`",
            id="version-1-units",
        ),
        pytest.param(["units", "1", "1", "7"], "event 1 has no unit 7", id="missing-unit"),
        pytest.param(["blob", "c" * 64], f"no event uses blob {'c' * 64}", id="unused-blob"),
        pytest.param(
            ["blob", "C" * 64],
            f"{'C' * 64} is not a blob address: 64 hexadecimal characters, lower case",
            id="not-a-blob-address",
        ),
        pytest.param(
            ["event", "1", "--reason", ""], "--reason must not be empty", id="empty-reason"
        ),
        pytest.param(
            ["event", "1", "--reason", "   "], "--reason must not be empty", id="blank-reason"
        ),
    ],
)
@pytest.mark.db
def test_a_refused_redaction_is_one_sentence(
    db: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    write_version_1: WriteVersion1,
    arguments: list[str],
    refusal: str,
) -> None:
    """Event 1 is version 2, event 2 version 1, event 3 a redaction of a unit
    of event 1. Every refusal leaves the log as it was."""
    engine = _connect(db, monkeypatch)
    assert main(["append", "--source", "cli", "--external-id", "a", "--text", "One\n\nTwo"]) == 0
    write_version_1(
        PostgresStorage(engine),
        [
            RawEvent(
                source="cli",
                external_id="b",
                occurred_at=datetime(2026, 10, 1, 9, 0, 0, tzinfo=UTC),
                evidence=Evidence.RECOLLECTION,
                units=split_plaintext("Old"),
                payload={"text": "Old"},
            )
        ],
        datetime(2026, 10, 1, 9, 0, 0, tzinfo=UTC),
    )
    assert main(["redact", "units", "1", "2", "--reason", "r"]) == 0
    capsys.readouterr()

    if "--reason" not in arguments:
        arguments = [*arguments, "--reason", "r"]
    assert main(["redact", *arguments]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err == f"Error: {refusal}\n"
    assert main(["log"]) == 0
    assert len(capsys.readouterr().out.splitlines()) == 3


@pytest.mark.db
def test_after_redact_the_chronicle_no_longer_shows_it(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`redact` brings the projections up to date itself ({ref}`projections`):
    `chronicle` straight after it, with no `project` between, shows neither
    the erased event nor a lag."""
    _connect(db, monkeypatch)
    _append("cli", "a", "One\n\nTwo", "2026-10-01T09:00:00Z")
    _append("cli", "b", "Three", "2026-10-02T09:00:00Z")
    assert main(["project"]) == 0
    capsys.readouterr()

    assert main(["redact", "event", "1", "--reason", "wrong recipient"]) == 0
    assert capsys.readouterr() == ("redacted by event 3\n", "")

    assert main(["chronicle"]) == 0
    out, err = capsys.readouterr()
    assert [line.split("\t")[:2] for line in out.splitlines()] == [["2", "1"]]
    assert err == ""


@pytest.mark.db
def test_a_second_redact_finishes_what_the_first_left_behind(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A redaction written by a call that did not get to the catch-up — taken
    here through `core`, which does not catch up — is caught up by the next
    call, the one that says `already`."""
    engine = _connect(db, monkeypatch)
    _append("cli", "a", "One\n\nTwo", "2026-10-01T09:00:00Z")
    assert main(["project"]) == 0
    storage = PostgresStorage(engine)
    redact_event(storage, storage, 1, reason="r", recorded_at=datetime.now(UTC))
    capsys.readouterr()

    assert main(["redact", "event", "1", "--reason", "r"]) == 0
    assert capsys.readouterr() == ("already redacted by event 2\n", "")
    assert main(["chronicle"]) == 0
    assert capsys.readouterr() == ("", "")


@pytest.mark.db
def test_a_catch_up_that_fails_after_the_redaction_says_what_is_outstanding(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The redaction is written and the catch-up fails: nothing on standard
    output, which carries its line only once the redaction is carried out,
    and the error says what stands and what does not. The failure is a gap
    in the log, forged with plain SQL the way `test_projection_worker` forges
    it — nothing in the write paths can produce one, which makes it a
    failure no wrapper has to stand in for."""
    from sqlalchemy import text

    engine = _connect(db, monkeypatch)
    _append("cli", "a", "One", "2026-10-01T09:00:00Z")
    assert main(["project"]) == 0
    _append("cli", "b", "Two", "2026-10-02T09:00:00Z")
    _append("cli", "c", "Three", "2026-10-03T09:00:00Z")
    with engine.begin() as c:
        c.execute(text("DELETE FROM source_key WHERE event_id = 2"))
        c.execute(text("DELETE FROM unit WHERE event_id = 2"))
        c.execute(text("DELETE FROM event WHERE id = 2"))
    capsys.readouterr()

    assert main(["redact", "event", "1", "--reason", "r"]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err == (
        "Error: the redaction is recorded as event 4, but it is not finished: "
        "projection chronicle is not caught up (expected events 2.. above id 1, "
        "read [3, 4]; the tip is 4); run the same command again\n"
    )


@pytest.mark.db
def test_an_unfinished_redact_units_still_says_that_the_payload_holds_the_wording(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The units are erased and the catch-up fails on a forged gap, as in
    `test_a_catch_up_that_fails_after_the_redaction_says_what_is_outstanding`:
    the payload still holds the wording of the erased unit, so the notice
    comes on standard error beside
    the sentence of the unfinished redaction, and the exit code stays 2.
    Measured on 2026-10-05 with the notice printed only on success: the
    sentence came alone."""
    from sqlalchemy import text

    engine = _connect(db, monkeypatch)
    _append_with_text_in_payload(engine, "One\n\nTwo")
    assert main(["project"]) == 0
    _append("cli", "b", "Three", "2026-10-02T09:00:00Z")
    _append("cli", "c", "Four", "2026-10-03T09:00:00Z")
    with engine.begin() as c:
        c.execute(text("DELETE FROM source_key WHERE event_id = 2"))
        c.execute(text("DELETE FROM unit WHERE event_id = 2"))
        c.execute(text("DELETE FROM event WHERE id = 2"))
    capsys.readouterr()

    assert main(["redact", "units", "1", "2", "--reason", "r"]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err == (
        f"{_payload_standing(1)}"
        "Error: the redaction is recorded as event 4, but it is not finished: "
        "projection chronicle is not caught up (expected events 2.. above id 1, "
        "read [3, 4]; the tip is 4); run the same command again\n"
    )


@pytest.mark.parametrize(
    ("target", "sentence"),
    [
        ("event", "erase the payload and the content of every unit"),
        ("units", "erase the content of the named units; the payload of the event stays"),
        ("blob", "erase a blob for every event that uses it"),
    ],
)
def test_each_form_of_redact_says_in_its_own_help_what_it_erases(
    capsys: pytest.CaptureFixture[str], target: str, sentence: str
) -> None:
    """`previously redact units --help` says that the payload stays, and the
    other two forms say what they erase the same way, not only in the list
    `previously redact --help` prints. argparse rewraps the text to the
    terminal, so the comparison ignores where the lines break. Measured on
    2026-10-05 with the sentence passed as `help=` only: the subcommand's own
    help did not carry it."""
    with pytest.raises(SystemExit) as exit_:
        main(["redact", target, "--help"])
    assert exit_.value.code == 0
    assert sentence in " ".join(capsys.readouterr().out.split())


class _HoldingProject(PostgresStorage):
    """The real store, except that a catch-up through it, once it has
    written the rows of its first batch that reads an event and the new
    `up_to_id`, holds them uncommitted until `may_commit()` is true, and
    says so in `holding`."""

    def __init__(self, engine: Engine, may_commit: Callable[[], bool]) -> None:
        super().__init__(engine)
        self.holding = threading.Event()
        self._may_commit = may_commit

    def set_projection_state(self, conn: Connection, state: ProjectionState) -> None:
        super().set_projection_state(conn, state)
        if state.up_to_id > 0 and not self.holding.is_set():
            self.holding.set()
            deadline = time.monotonic() + 10
            while not self._may_commit():
                assert time.monotonic() < deadline, "redact never came"
                time.sleep(0.01)


def _waiting_on_a_lock(engine: Engine) -> bool:
    from sqlalchemy import text

    with engine.connect() as c:
        return bool(
            c.execute(
                text(
                    "SELECT count(*) FROM pg_stat_activity "
                    "WHERE datname = current_database() AND wait_event_type = 'Lock'"
                )
            ).scalar_one()
        )


@pytest.mark.db
def test_redact_beside_a_project_holding_rows_ends_without_a_traceback(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A `project` holds the chronicle rows of event 1 uncommitted while
    `redact event 2` runs its own catch-up. The catch-up waits at the state
    row of the chronicle, starts where the `project` committed, and the
    command ends with its one line and nothing on standard error.

    Measured on 2026-10-05 with the lock taken out of
    `lock_projection_state`: the catch-up of `redact` started at `up_to_id` 0,
    inserted event 1's rows behind the uncommitted ones of the `project`, and
    once that committed, `main` raised `IntegrityError` on `p_chronicle_pkey`
    — a traceback after the redaction had committed, with no word that it
    stood."""
    engine = _connect(db, monkeypatch)
    storage = PostgresStorage(engine)
    _append("cli", "a", "One\n\nTwo", "2026-10-01T09:00:00Z")
    redacted = threading.Event()
    project = _HoldingProject(engine, lambda: redacted.is_set() or _waiting_on_a_lock(engine))
    errors: list[BaseException] = []

    def run_project() -> None:
        try:
            catch_up(project, project, CHRONICLE)
        except BaseException as e:
            errors.append(e)

    thread = threading.Thread(target=run_project)
    thread.start()
    try:
        assert project.holding.wait(timeout=10)
        _append("cli", "b", "Three", "2026-10-02T09:00:00Z")
        capsys.readouterr()
        assert main(["redact", "event", "2", "--reason", "r"]) == 0
    finally:
        redacted.set()
        thread.join(timeout=20)
    assert not thread.is_alive(), "thread is hanging"

    assert errors == []
    assert capsys.readouterr() == (
        "redacted by event 3\n",
        "source-stats    built: 3 events, up_to_id 3\n"
        "graph           built: 3 events, up_to_id 3\n",
    )
    with storage.begin() as conn:
        rows = storage.read_chronicle(conn, since=None, until=None, limit=10)
    assert [(row.event_id, row.seq) for row in rows] == [(1, 1), (1, 2)]


@pytest.mark.db
def test_redact_reports_a_rebuild_it_runs_on_standard_error(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A `redact` that is the first catch-up after an upgrade rebuilds the
    chronicle, and says so in the words of `project`, on standard error:
    standard output stays the one line ({ref}`projections`). The `project`
    after it has nothing left to rebuild. The control is
    `test_after_redact_the_chronicle_no_longer_shows_it`, where the
    projections are current and `redact` says nothing on standard error."""
    from sqlalchemy import text

    engine = _connect(db, monkeypatch)
    _append("cli", "a", "One\n\nTwo", "2026-10-01T09:00:00Z")
    assert main(["project"]) == 0
    with engine.begin() as c:
        c.execute(text("UPDATE projection_state SET version = 1 WHERE name = 'chronicle'"))
    capsys.readouterr()

    assert main(["redact", "event", "1", "--reason", "r"]) == 0
    assert capsys.readouterr() == (
        "redacted by event 2\n",
        "chronicle       rebuilt: version 1 -> 3, 2 events, up_to_id 2\n",
    )
    assert main(["project"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "chronicle       up to date, up_to_id 2",
        "source-stats    up to date, up_to_id 2",
        "graph           up to date, up_to_id 2",
    ]


@pytest.mark.db
def test_project_rebuilds_a_chronicle_built_at_version_1(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Version 1 of the chronicle did not read redactions, so a table it built
    can still hold the rows of an erased event. The state row is set to what
    such a table carries — version 1, caught up past the redaction — and the
    first `project` of version 3 rebuilds it and says so."""
    from sqlalchemy import text

    engine = _connect(db, monkeypatch)
    _append("cli", "a", "One\n\nTwo", "2026-10-01T09:00:00Z")
    _append("cli", "b", "Three", "2026-10-02T09:00:00Z")
    assert main(["project"]) == 0
    storage = PostgresStorage(engine)
    redact_event(storage, storage, 1, reason="r", recorded_at=datetime.now(UTC))
    with engine.begin() as c:
        c.execute(
            text("UPDATE projection_state SET version = 1, up_to_id = 3 WHERE name = 'chronicle'")
        )
    capsys.readouterr()

    assert main(["project"]) == 0
    assert capsys.readouterr().out.splitlines()[0] == (
        "chronicle       rebuilt: version 1 -> 3, 3 events, up_to_id 3"
    )
    assert main(["chronicle"]) == 0
    out = capsys.readouterr().out
    assert [line.split("\t")[:2] for line in out.splitlines()] == [["2", "1"]]


def _connections(engine: Engine) -> int:
    """What the server holds for the test database right now, this query's
    own connection included."""
    from sqlalchemy import text

    with engine.connect() as c:
        return c.execute(
            text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")
        ).scalar_one()


@pytest.mark.db
def test_main_releases_the_connections_it_opened(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every command gives back what it opened, on success and on error alike,
    so a process that calls `main` again and again holds no more connections
    at the end than at the start.

    The test relies on one property of SQLAlchemy's engines: an engine nobody
    refers to any more is held in reference cycles, so it lets go of its
    connections only when the garbage collector collects it, not when the
    last reference goes. The collector is therefore switched off for the loop
    and for the reading after it, since a collection in either would hide a
    missing release. Were a later SQLAlchemy to free an engine by reference
    counting alone, this test would stay green without the release and stop
    proving anything.

    The count is read until it is no higher than before, for at most five
    seconds: a backend leaves `pg_stat_activity` only once it has processed
    the client's terminate, which happens after `dispose` returns. The bound
    itself stays where it was. Measured on 2026-10-05: with the release, 1 connection before
    the 33 calls and 1 after, so the bound needs no allowance. With
    `PostgresStorage.close` emptied, 34 after; with the release on success
    only, 4 after, one for each refused `redact`. Before the release existed,
    a test run in fixed order piled up 93 of the server's 100 connections,
    and on other runs the test that came next could not connect.
    """
    import gc

    engine = _connect(db, monkeypatch)
    _append("cli", "a", "One\n\nTwo", "2026-10-01T09:00:00Z")
    assert main(["redact", "units", "1", "1", "--reason", "r"]) == 0
    capsys.readouterr()
    commands = [
        ["append", "--source", "cli", "--external-id", "a", "--text", "One\n\nTwo"],
        ["redact", "units", "1", "1", "--reason", "r"],
        ["log"],
        ["verify"],
        ["anchor"],
        ["show", "1"],
        ["project"],
        ["chronicle"],
        ["stats"],
        ["show", "99"],  # exit code 1
        ["redact", "event", "99", "--reason", "r"],  # a refusal, exit code 2
    ]
    gc.collect()
    before = _connections(engine)
    gc.disable()
    try:
        for _ in range(3):
            for command in commands:
                main(command)
        deadline = time.monotonic() + 5
        after = _connections(engine)
        while after > before and time.monotonic() < deadline:
            time.sleep(0.05)
            after = _connections(engine)
    finally:
        gc.enable()
    capsys.readouterr()
    assert after <= before


# --- Blobs at the event ({ref}`blobs`) ----------------------------------------

_BLOB_VARIABLES = (
    "PREVIOUSLY_BLOB_ENDPOINT",
    "PREVIOUSLY_BLOB_REGION",
    "PREVIOUSLY_BLOB_BUCKET",
    "PREVIOUSLY_BLOB_ACCESS_KEY",
    "PREVIOUSLY_BLOB_SECRET_KEY",
    "PREVIOUSLY_BLOB_RECIPIENT",
    "PREVIOUSLY_BLOB_IDENTITIES",
)

# What the `s3_connections` fixture is, spelled as `conftest.py` asks of a
# test that takes one of its callables.
type ConnectionCount = Callable[[], int]


class _Blobs:
    """What a test of the blob commands works with: the database, the bucket,
    and the identity whose recipient the environment names.

    A plain class rather than a dataclass, whose field annotations would have
    to be importable at run time."""

    def __init__(
        self, engine: Engine, store: S3BlobStore, identity: str, keys: pathlib.Path, secret: str
    ) -> None:
        self.engine = engine
        self.store = store
        self.identity = identity
        self.keys = keys
        self.secret = secret


@pytest.fixture
def blobs(
    db: object,
    monkeypatch: pytest.MonkeyPatch,
    blob_store: S3BlobStore,
    s3_settings: dict[str, str],
    age_identity: str,
    tmp_path: pathlib.Path,
) -> _Blobs:
    """The database, a bucket of its own and a key directory with one
    identity in it, all seven variables set to reach them. The identity and
    the secret are drawn at run time (`conftest.py`)."""
    engine = _connect(db, monkeypatch)
    keys = tmp_path / "keys"
    keys.mkdir()
    (keys / recipient_of(age_identity)).write_text(age_identity + "\n", encoding="utf-8")
    values = (
        s3_settings["endpoint"],
        s3_settings["region"],
        blob_store.bucket,
        s3_settings["access_key"],
        s3_settings["secret_key"],
        recipient_of(age_identity),
        str(keys),
    )
    for name, value in zip(_BLOB_VARIABLES, values, strict=True):
        monkeypatch.setenv(name, value)
    return _Blobs(engine, blob_store, age_identity, keys, s3_settings["secret_key"])


def _file(directory: pathlib.Path, name: str, content: bytes) -> pathlib.Path:
    path = directory / name
    path.write_bytes(content)
    return path


def _attach(external_id: str, *paths: pathlib.Path) -> list[str]:
    argv = ["append", "--source", "cli", "--external-id", external_id, "--text", "See attached."]
    for path in paths:
        argv += ["--attach", str(path)]
    return argv


def _bucket(store: S3BlobStore) -> list[str]:
    listing = store.client.list_objects_v2(Bucket=store.bucket)
    return [entry.get("Key", "") for entry in listing.get("Contents", [])]


def _events(engine: Engine) -> int:
    from sqlalchemy import text

    with engine.connect() as c:
        return c.execute(text("SELECT count(*) FROM event")).scalar_one()


@pytest.mark.db
@pytest.mark.s3
def test_the_artifact_of_append_is_the_text_and_the_sorted_attachment_addresses(
    blobs: _Blobs, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The same files in the other order are the same artifact; another file
    is another one, and refused under the same key."""
    from sqlalchemy import text

    first = _file(tmp_path, "first.txt", b"The first attachment, invented for this test.\n")
    second = _file(tmp_path, "second.txt", b"The second attachment, invented for this test.\n")
    third = _file(tmp_path, "third.txt", b"A third one, not attached before.\n")
    addresses = sorted(hashlib.sha256(path.read_bytes()).hexdigest() for path in (first, second))

    assert main(_attach("a", second, first)) == 0
    assert main(_attach("a", first, second)) == 0
    assert capsys.readouterr().out == "1\n1\n"
    with blobs.engine.connect() as c:
        stored = c.execute(text("SELECT payload ->> 'artifact_hash' FROM event")).scalar_one()
    assert stored == artifact_hash_of({"text": "See attached.", "attachments": addresses}).hex()

    assert main(_attach("a", first, third)) == 2
    assert "Error: cli/a is known with another content" in capsys.readouterr().err
    assert _events(blobs.engine) == 1


@pytest.mark.db
@pytest.mark.s3
def test_append_with_an_attachment_and_blob_get_bring_the_bytes_back(
    blobs: _Blobs, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    content = b"Minutes of the site meeting, invented for this test.\n" * 50
    attachment = _file(tmp_path, "minutes.txt", content)
    address = hashlib.sha256(content).hexdigest()

    assert main(_attach("a", attachment)) == 0
    assert capsys.readouterr().out == "1\n"

    target = tmp_path / "out" / "fetched.txt"
    target.parent.mkdir()
    assert main(["blob", "get", address, "--output", str(target)]) == 0
    assert capsys.readouterr().out == f"wrote {len(content)} bytes to {target}\n"
    assert target.read_bytes() == content
    # Readable by its owner only, as the temporary file was created.
    assert target.stat().st_mode & 0o777 == 0o600
    assert sorted(path.name for path in target.parent.iterdir()) == ["fetched.txt"]
    assert _bucket(blobs.store) == [address]


@pytest.mark.db
@pytest.mark.s3
@pytest.mark.parametrize("broken", ["missing", "directory"])
def test_an_attachment_that_cannot_be_read_appends_nothing(
    blobs: _Blobs, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str], broken: str
) -> None:
    """Review focus 1 of the 2026-10-04 stage 1c plan. Two attachments, the
    second unreadable: every file is opened before the first is stored, so
    the readable one is not stored either, and nothing is appended."""
    readable = _file(tmp_path, "readable.txt", b"stored only if every attachment opens")
    unreadable = tmp_path / "unreadable"
    if broken == "directory":
        unreadable.mkdir()
    reason = "Is a directory" if broken == "directory" else "No such file or directory"

    assert main(_attach("a", readable, unreadable)) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert _single_line(err) == f"Error: cannot read the attachment {unreadable}: {reason}"
    assert _events(blobs.engine) == 0
    assert _bucket(blobs.store) == []


@pytest.mark.parametrize("command", ["blob get", "redact blob"])
@pytest.mark.parametrize("address", ["A" * 64, "a" * 63], ids=["upper-case", "63-characters"])
def test_a_blob_address_that_is_not_one_is_an_input_error(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    command: str,
    address: str,
) -> None:
    """Review focus 6 of the 2026-10-04 stage 1c plan. Refused before
    anything is asked: `PREVIOUSLY_DSN` is not even set, there is no blob
    setting, and the sentence is still about the address. Measured on
    2026-10-05 for `redact blob` before it checked the address itself: it
    said `PREVIOUSLY_DSN is not set`."""
    monkeypatch.delenv("PREVIOUSLY_DSN", raising=False)
    for name in _BLOB_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    target = tmp_path / "out.bin"
    if command == "blob get":
        argv = ["blob", "get", address, "--output", str(target)]
    else:
        argv = ["redact", "blob", address, "--reason", "r"]
    assert main(argv) == 2
    assert _single_line(capsys.readouterr().err) == (
        f"Error: {address} is not a blob address: 64 hexadecimal characters, lower case"
    )
    assert not target.exists()


@pytest.mark.db
@pytest.mark.s3
def test_append_with_an_attachment_and_no_database_stores_nothing(
    blobs: _Blobs,
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unset `PREVIOUSLY_DSN` is the most predictable configuration
    error, and it is named before anything is stored, so it leaves no object
    in the bucket that no event names. Measured on 2026-10-05 with the blobs
    stored first: the sentence was the same, and the bucket held the
    object."""
    monkeypatch.delenv("PREVIOUSLY_DSN")
    path = _file(tmp_path, "hello.txt", b"hello\n")
    assert main(_attach("a", path)) == 2
    assert capsys.readouterr() == ("", "Error: PREVIOUSLY_DSN is not set\n")
    assert _bucket(blobs.store) == []


@pytest.mark.db
@pytest.mark.s3
def test_blob_get_of_an_address_no_event_uses_returns_1(
    blobs: _Blobs, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    address = hashlib.sha256(b"never attached").hexdigest()
    target = tmp_path / "out.bin"
    assert main(["blob", "get", address, "--output", str(target)]) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert err == f"no event uses blob {address}\n"
    assert not target.exists()


def _forge_foreign_object(blobs: _Blobs, address: str, content: bytes) -> None:
    """Lays a sealed object of other content under `address`: it opens with
    the identity at hand, and its plaintext is not what the address names."""
    sealed = io.BytesIO()
    seal(io.BytesIO(content), sealed, recipient_of(blobs.identity))
    sealed.seek(0)
    blobs.store.put(address, sealed, key_id=recipient_of(blobs.identity))


@pytest.mark.db
@pytest.mark.s3
def test_blob_get_writes_nothing_when_the_address_does_not_match(
    blobs: _Blobs, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The plaintext passes into a temporary file before the address is
    known to hold, so a mismatch leaves neither the target nor that file
    behind ({ref}`blobs`)."""
    content = b"the content the event names"
    assert main(_attach("a", _file(tmp_path, "named.txt", content))) == 0
    address = hashlib.sha256(content).hexdigest()
    _forge_foreign_object(blobs, address, b"another content, laid under a foreign address")
    capsys.readouterr()

    directory = tmp_path / "out"
    directory.mkdir()
    target = directory / "fetched.txt"
    assert main(["blob", "get", address, "--output", str(target)]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert _single_line(err) == (
        f"Error: blob {address} does not match its address; nothing was written"
    )
    assert list(directory.iterdir()) == []


@pytest.mark.db
@pytest.mark.s3
def test_blob_get_leaves_an_existing_target_alone_when_it_fails(
    blobs: _Blobs, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    content = b"the content the event names"
    assert main(_attach("a", _file(tmp_path, "named.txt", content))) == 0
    address = hashlib.sha256(content).hexdigest()
    _forge_foreign_object(blobs, address, b"another content, laid under a foreign address")
    capsys.readouterr()

    directory = tmp_path / "out"
    directory.mkdir()
    target = _file(directory, "fetched.txt", b"what stood here before")
    assert main(["blob", "get", address, "--output", str(target)]) == 2
    capsys.readouterr()
    assert target.read_bytes() == b"what stood here before"
    assert list(directory.iterdir()) == [target]


# What the write side and the read side of the blob path can fail with, for
# real. A directory without write permission is no obstacle to root, so the
# tests that need one are skipped there, with that reason.
_ROOT = sys.platform != "win32" and os.geteuid() == 0


@pytest.mark.db
@pytest.mark.s3
@pytest.mark.parametrize("failure", ["parent-missing", "not-writable", "target-a-directory"])
def test_blob_get_that_cannot_write_is_one_sentence_and_leaves_nothing(
    blobs: _Blobs, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str], failure: str
) -> None:
    """Ruling T6-a of the 2026-10-04 stage 1c plan: a target whose directory
    does not exist, a directory that does not allow writing, and a target
    that is a directory, so that the rename fails after the fetch. Each is
    `cannot write <file>: <reason>` and exit code 2, and no temporary file
    stays behind."""
    if failure == "not-writable" and _ROOT:
        pytest.skip("root writes into a directory without write permission")
    content = b"fetched, and then nowhere to put it"
    assert main(_attach("a", _file(tmp_path, "a.txt", content))) == 0
    capsys.readouterr()
    address = hashlib.sha256(content).hexdigest()
    directory = tmp_path / "out"
    directory.mkdir()
    target, reason = {
        "parent-missing": (directory / "missing" / "a.txt", "No such file or directory"),
        "not-writable": (directory / "a.txt", "Permission denied"),
        "target-a-directory": (directory / "a.txt", "Is a directory"),
    }[failure]
    if failure == "target-a-directory":
        target.mkdir()
    if failure == "not-writable":
        directory.chmod(0o500)
    try:
        assert main(["blob", "get", address, "--output", str(target)]) == 2
    finally:
        directory.chmod(0o700)
    out, err = capsys.readouterr()
    assert out == ""
    assert _single_line(err) == f"Error: cannot write {target}: {reason}"
    expected = [target] if failure == "target-a-directory" else []
    assert list(directory.iterdir()) == expected


@contextmanager
def _file_size_limit(limit: int) -> Generator[None]:
    """A real limit on the size of every file this process writes, for the
    duration of one command: a write past it fails with `EFBIG`, `File too
    large`. CPython ignores the `SIGXFSZ` the kernel would send instead
    (`signal.getsignal(signal.SIGXFSZ)` is `SIG_IGN`, read on 2026-10-05).
    Only the soft limit moves, and it is put back."""
    import resource

    soft, hard = resource.getrlimit(resource.RLIMIT_FSIZE)
    resource.setrlimit(resource.RLIMIT_FSIZE, (limit, hard))
    try:
        yield
    finally:
        resource.setrlimit(resource.RLIMIT_FSIZE, (soft, hard))


_LARGE = 1024 * 1024
_LIMIT = 256 * 1024


@pytest.mark.db
@pytest.mark.s3
@pytest.mark.skipif(sys.platform != "linux", reason="RLIMIT_FSIZE as measured on Linux")
@pytest.mark.parametrize("before", ["no-target", "existing-target"])
def test_blob_get_whose_output_cannot_be_written_leaves_nothing(
    blobs: _Blobs, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str], before: str
) -> None:
    """Ruling T6-c of the 2026-10-04 stage 1c plan: the temporary output
    fills up while the content passes into it — a file size limit below
    the blob's size, for real. One sentence, exit code 2, and no temporary
    file; no target where there was none, and a target that was there is
    byte for byte what it was. `fetch_blob` returns no size for bytes that
    never arrived."""
    content = os.urandom(_LARGE)
    assert main(_attach("a", _file(tmp_path, "large.bin", content))) == 0
    capsys.readouterr()
    directory = tmp_path / "out"
    directory.mkdir()
    target = directory / "large.bin"
    earlier = b"what stood here before"
    if before == "existing-target":
        target.write_bytes(earlier)
    with _file_size_limit(_LIMIT):
        code = main(["blob", "get", hashlib.sha256(content).hexdigest(), "--output", str(target)])
    out, err = capsys.readouterr()
    assert code == 2
    assert out == ""
    assert _single_line(err) == f"Error: cannot write {target}: File too large"
    if before == "existing-target":
        assert list(directory.iterdir()) == [target]
        assert target.read_bytes() == earlier
    else:
        assert list(directory.iterdir()) == []


@pytest.mark.db
@pytest.mark.s3
@pytest.mark.skipif(sys.platform != "linux", reason="RLIMIT_FSIZE as measured on Linux")
def test_a_sealed_form_that_cannot_be_written_appends_nothing(
    blobs: _Blobs, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The same limit while the attachment is sealed into its temporary
    file: one sentence, exit code 2, nothing appended and nothing stored."""
    attachment = _file(tmp_path, "large.bin", os.urandom(_LARGE))
    with _file_size_limit(_LIMIT):
        code = main(_attach("a", attachment))
    out, err = capsys.readouterr()
    assert code == 2
    assert out == ""
    assert _single_line(err) == "Error: cannot write a temporary file: File too large"
    assert _events(blobs.engine) == 0
    assert _bucket(blobs.store) == []


@pytest.mark.db
@pytest.mark.s3
@pytest.mark.skipif(sys.platform != "linux", reason="/proc/self/mem is Linux's")
def test_an_attachment_that_opens_and_cannot_be_read_appends_nothing(
    blobs: _Blobs, capsys: pytest.CaptureFixture[str]
) -> None:
    """A file that opens, can be rewound, and fails at its first read with a
    real `EIO`: `/proc/self/mem`, whose offset 0 no process maps. One
    sentence naming the attachment, exit code 2, nothing appended and
    nothing stored."""
    from pathlib import Path

    assert main(_attach("a", Path("/proc/self/mem"))) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert _single_line(err) == (
        "Error: cannot read the attachment /proc/self/mem: Input/output error"
    )
    assert _events(blobs.engine) == 0
    assert _bucket(blobs.store) == []


@pytest.mark.db
@pytest.mark.s3
@pytest.mark.skipif(_ROOT, reason="root writes into a directory without write permission")
def test_a_temporary_file_that_cannot_be_made_appends_nothing(
    blobs: _Blobs,
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The sealed form goes into a temporary file, here in a directory that
    does not allow writing: one sentence, exit code 2, nothing appended and
    nothing stored."""
    import tempfile

    closed = tmp_path / "closed"
    closed.mkdir()
    closed.chmod(0o500)
    monkeypatch.setattr(tempfile, "tempdir", str(closed))
    try:
        assert main(_attach("a", _file(tmp_path, "a.txt", b"to be sealed"))) == 2
    finally:
        closed.chmod(0o700)
    out, err = capsys.readouterr()
    assert out == ""
    assert _single_line(err) == "Error: cannot write a temporary file: Permission denied"
    assert _events(blobs.engine) == 0
    assert _bucket(blobs.store) == []


@pytest.mark.db
@pytest.mark.s3
def test_a_mistyped_recipient_is_refused_before_anything_is_stored(
    blobs: _Blobs,
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A content the store already holds is not sealed again, so the
    recipient is not used — and a typo in it would pass unnoticed until new
    content arrived. `append --attach` checks it first: one sentence, which
    may quote the recipient because a recipient is public, and nothing
    appended."""
    attachment = _file(tmp_path, "a.txt", b"stored before the typo")
    assert main(_attach("a", attachment)) == 0
    capsys.readouterr()
    mistyped = recipient_of(blobs.identity)[:-1] + "!"
    monkeypatch.setenv("PREVIOUSLY_BLOB_RECIPIENT", mistyped)

    assert main(_attach("b", attachment)) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert _single_line(err) == f"Error: {mistyped!r} is not an age X25519 recipient"
    assert _events(blobs.engine) == 1


@pytest.mark.db
@pytest.mark.s3
@pytest.mark.parametrize("variable", _BLOB_VARIABLES)
def test_a_missing_blob_setting_is_named(
    blobs: _Blobs,
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    variable: str,
) -> None:
    """Each variable, taken away alone, at the command that needs it: the
    five of the store and the recipient at `append --attach`, which then
    appends nothing; the key directory at `blob get`."""
    content = b"an attachment"
    attachment = _file(tmp_path, "a.txt", content)
    if variable == "PREVIOUSLY_BLOB_IDENTITIES":
        assert main(_attach("a", attachment)) == 0
        capsys.readouterr()
        argv = ["blob", "get", hashlib.sha256(content).hexdigest(), "--output", "unused"]
    else:
        argv = _attach("a", attachment)
    monkeypatch.delenv(variable)

    assert main(argv) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert _single_line(err) == f"Error: {variable} is not set"
    expected_events = 1 if variable == "PREVIOUSLY_BLOB_IDENTITIES" else 0
    assert _events(blobs.engine) == expected_events


@pytest.mark.db
def test_the_commands_of_today_run_without_any_blob_setting(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every command that touches no blob reads no blob setting, so a
    deployment without a blob store runs as before ({ref}`blobs`)."""
    _connect(db, monkeypatch)
    for name in _BLOB_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    commands = [
        ["append", "--source", "cli", "--external-id", "a", "--text", "One\n\nTwo"],
        ["log"],
        ["verify"],
        ["anchor"],
        ["show", "1"],
        ["project"],
        ["chronicle"],
        ["stats"],
        ["redact", "event", "1", "--reason", "r"],
    ]
    for command in commands:
        assert main(command) == 0, command
    capsys.readouterr()


@pytest.mark.db
@pytest.mark.s3
def test_a_store_that_does_not_answer_appends_nothing_and_shows_no_secret(
    blobs: _Blobs,
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Review focus 5 of the 2026-10-04 stage 1c plan: an endpoint where
    nobody listens is one sentence with the endpoint in it, exit code 2, no
    event — and the secret of the store stands in neither output, since a
    message ends up on a terminal and in a log."""
    endpoint = "http://127.0.0.1:1"
    monkeypatch.setenv("PREVIOUSLY_BLOB_ENDPOINT", endpoint)
    assert main(_attach("a", _file(tmp_path, "a.txt", b"an attachment"))) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert endpoint in _single_line(err)
    assert blobs.secret not in out + err
    assert _events(blobs.engine) == 0


@pytest.mark.db
@pytest.mark.s3
@pytest.mark.parametrize("command", ["append", "blob-get"])
def test_an_endpoint_without_a_scheme_is_one_sentence(
    blobs: _Blobs,
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    command: str,
) -> None:
    """A typo in the environment, `localhost:9000` without `http://`, at
    both commands that build a store: one sentence that names the endpoint,
    exit code 2, nothing appended, and no secret. Before fix round 1 of task
    6 it left `main` as a `ValueError` traceback. `blob get` builds its store
    only for a blob an event uses and no redaction erased, so it asks for
    one an event names, written through `core` without a store."""
    events = 0
    if command == "append":
        argv = _attach("a", _file(tmp_path, "a.txt", b"an attachment"))
    else:
        _append_naming(blobs.engine, "c" * 64)
        events = 1
        argv = ["blob", "get", "c" * 64, "--output", str(tmp_path / "out.bin")]
    monkeypatch.setenv("PREVIOUSLY_BLOB_ENDPOINT", "localhost:9000")
    assert main(argv) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert _single_line(err).startswith(
        "Error: the settings for the blob store at localhost:9000, bucket "
    )
    assert err.rstrip().endswith("are not usable: ValueError")
    assert blobs.secret not in out + err
    assert _events(blobs.engine) == events


@pytest.mark.db
@pytest.mark.s3
def test_no_identity_reaches_any_output(
    blobs: _Blobs,
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
    other_age_identity: str,
) -> None:
    """No identity in any output, on the path that reads identities: an
    identity is the secret half of a key, and a message ends up on a
    terminal and in a log. The file named after the object's recipient holds
    the identity of another key, `age` refuses it, and the sentence says the
    blob cannot be opened without quoting either identity."""
    content = b"sealed to the key the environment names"
    assert main(_attach("a", _file(tmp_path, "a.txt", content))) == 0
    capsys.readouterr()
    (blobs.keys / recipient_of(blobs.identity)).write_text(
        other_age_identity + "\n", encoding="utf-8"
    )
    address = hashlib.sha256(content).hexdigest()

    assert main(["blob", "get", address, "--output", str(tmp_path / "out.bin")]) == 2
    out, err = capsys.readouterr()
    assert _single_line(err).startswith(f"Error: blob {address} cannot be opened: ")
    for secret in (blobs.identity, other_age_identity, "AGE-SECRET-KEY"):
        assert secret not in out + err
    assert not (tmp_path / "out.bin").exists()


@pytest.mark.db
def test_show_lists_the_blobs_of_an_event(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """One line per reference, in the payload's order, the same content
    twice included, and `-` for a reference without a name. Written through
    `core` with references to blobs no store holds and without any blob
    setting: `show` reads the log and does not ask the store."""
    engine = _connect(db, monkeypatch)
    for name in _BLOB_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    first, second = "1" * 64, "2" * 64
    append(
        PostgresStorage(engine),
        [
            RawEvent(
                source="cli",
                external_id="a",
                occurred_at=datetime(2026, 10, 1, 9, 0, 0, tzinfo=UTC),
                evidence=Evidence.VERBATIM,
                units=split_plaintext("See attached."),
                payload={"text": "See attached."},
                blobs=(
                    BlobRef(sha256=second, size=12, media_type="text/plain", filename="a.txt"),
                    BlobRef(sha256=first, size=0, media_type="application/octet-stream"),
                    BlobRef(sha256=second, size=12, media_type="text/plain", filename="b.txt"),
                ),
            )
        ],
        recorded_at=datetime(2026, 10, 2, 12, 0, 0, tzinfo=UTC),
    )
    assert main(["show", "1"]) == 0
    out = capsys.readouterr().out
    assert out.endswith(
        "  ¶1 See attached.\n"
        f"  blob {second} 12 text/plain a.txt\n"
        f"  blob {first} 0 application/octet-stream -\n"
        f"  blob {second} 12 text/plain b.txt\n"
    )


@pytest.mark.parametrize(
    ("name", "media_type"),
    [
        ("minutes.txt", "text/plain"),
        ("PLAN.PDF", "application/pdf"),
        ("photo.jpeg", "image/jpeg"),
        ("archive.tar.gz", "application/octet-stream"),
        ("no-extension", "application/octet-stream"),
        ("unknown.previously-test", "application/octet-stream"),
    ],
)
def test_the_media_type_comes_from_the_name_and_the_built_in_table(
    name: str, media_type: str
) -> None:
    """From the file's name, and from Python's own table only, not from the
    files of the system it runs on: the value stands in the hash for good,
    and has to be the same whichever machine attached it. A name that says
    the content is compressed (`.gz`) names the type of what is inside, not
    of the bytes, so it is no answer."""
    assert media_type_of(name) == media_type


@pytest.mark.db
@pytest.mark.s3
def test_main_releases_the_blob_store_it_opened(
    blobs: _Blobs,
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    s3_connections: ConnectionCount,
) -> None:
    """Every command that builds a blob store closes it, on success and on
    error alike, the way `test_main_releases_the_connections_it_opened` holds
    it for the database: a process that calls `main` again and again holds
    no more connections to the store at the end than at the start.

    The attachments are above the 8 MiB from which an upload goes in parts,
    and a new content each round, since a content already stored is not
    uploaded again: an upload in parts keeps the client in reference cycles,
    so only the garbage collector would free a store left open, and the
    collector is off for the loop and the count after it, as in
    `tests/test_s3.py::test_close_releases_the_connections_the_store_opened`.
    Two calls fail: a fetch of an object that names a key no identity in the
    directory belongs to, and an attachment uploaded in parts into a bucket
    that does not exist. The second is the one that holds the "on error"
    half: a failing fetch uploads nothing, and a store without an upload is
    freed by reference counting even unclosed, while a refused upload in
    parts leaves the store in reference cycles.

    Measured on 2026-10-05, after ruling T6-a of the 2026-10-04 stage 1c
    plan had the adapter let go of what a refused upload kept: 1 connection
    before the twenty calls and 1 after; with the close moved out of the
    `finally` of `_blob_store`, so that it runs on success only, 5 after;
    with `store.close()` taken out, 13 after. Before that ruling the
    refused upload kept its connection through `close` as well, and the
    test had to leave it out.
    """
    import gc

    broken = b"an object nobody can open"
    assert main(_attach("broken", _file(tmp_path, "broken.txt", broken))) == 0
    broken_address = hashlib.sha256(broken).hexdigest()
    blobs.store.put(broken_address, io.BytesIO(b"not an age file"), key_id="age1unknown")
    capsys.readouterr()
    target = tmp_path / "out.bin"

    gc.collect()
    before = s3_connections()
    gc.disable()
    try:
        for round_ in range(4):
            content = os.urandom(9 * 1024 * 1024)
            attachment = _file(tmp_path, f"large-{round_}.bin", content)
            address = hashlib.sha256(content).hexdigest()
            assert main(_attach(f"large-{round_}", attachment)) == 0
            assert main(["blob", "get", address, "--output", str(target)]) == 0
            assert main(["blob", "get", broken_address, "--output", str(target)]) == 2
            assert main(["blob", "get", address, "--output", str(target)]) == 0
            monkeypatch.setenv("PREVIOUSLY_BLOB_BUCKET", "previously-no-such-bucket")
            assert main(_attach(f"refused-{round_}", attachment)) == 2
            monkeypatch.setenv("PREVIOUSLY_BLOB_BUCKET", blobs.store.bucket)
        after = s3_connections()
    finally:
        gc.enable()
    capsys.readouterr()
    assert after <= before, f"{after} connections after the commands, {before} before"


# --- Erasing and checking blobs ({ref}`erasure`) ------------------------------


def _stays(address: str, *event_ids: int) -> str:
    users = ", ".join(str(event_id) for event_id in event_ids)
    verb = "event" if len(event_ids) == 1 else "events"
    use = "uses" if len(event_ids) == 1 else "use"
    return f"blob {address} stays in the store: {verb} {users} still {use} it\n"


@pytest.mark.db
@pytest.mark.s3
def test_redact_event_deletes_its_blob_and_says_which_one_stays(
    blobs: _Blobs, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Event 1 has a blob of its own and one it shares with events 2 and 3.
    Erasing event 1 deletes its own blob and leaves the shared one, named
    with the events that still use it, on standard error after the lines of
    the catch-up; erasing event 2 names the one event left."""
    own, shared = b"only in the first mail", b"in three mails"
    own_address = hashlib.sha256(own).hexdigest()
    shared_address = hashlib.sha256(shared).hexdigest()
    assert (
        main(_attach("a", _file(tmp_path, "own.txt", own), _file(tmp_path, "s.txt", shared))) == 0
    )
    assert main(_attach("b", tmp_path / "s.txt")) == 0
    assert main(_attach("c", tmp_path / "s.txt")) == 0
    assert sorted(_bucket(blobs.store)) == sorted([own_address, shared_address])
    capsys.readouterr()

    assert main(["redact", "event", "1", "--reason", "r"]) == 0
    assert capsys.readouterr() == (
        "redacted by event 4\n",
        "chronicle       built: 4 events, up_to_id 4\n"
        "source-stats    built: 4 events, up_to_id 4\n"
        "graph           built: 4 events, up_to_id 4\n" + _stays(shared_address, 2, 3),
    )
    assert _bucket(blobs.store) == [shared_address]

    assert main(["redact", "event", "2", "--reason", "r"]) == 0
    assert capsys.readouterr() == ("redacted by event 5\n", _stays(shared_address, 3))
    assert _bucket(blobs.store) == [shared_address]


@pytest.mark.db
@pytest.mark.s3
def test_redact_blob_and_then_blob_get_says_erased(
    blobs: _Blobs, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    content = b"a scan that must go"
    address = hashlib.sha256(content).hexdigest()
    assert main(_attach("a", _file(tmp_path, "scan.pdf", content))) == 0
    assert main(["project"]) == 0
    capsys.readouterr()

    assert main(["redact", "blob", address, "--reason", "r"]) == 0
    assert capsys.readouterr() == ("redacted by event 2\n", "")
    assert _bucket(blobs.store) == []

    target = tmp_path / "out.pdf"
    assert main(["blob", "get", address, "--output", str(target)]) == 1
    assert capsys.readouterr() == ("", f"blob {address} is erased (event 2)\n")
    assert not target.exists()


@pytest.mark.db
@pytest.mark.s3
def test_a_delete_that_fails_is_finished_by_the_second_call(
    blobs: _Blobs,
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    s3_settings: dict[str, str],
) -> None:
    """The store does not answer when the first call deletes: the redaction
    stands, the sentence names the blobs still to delete, and the same
    command with a store that answers deletes them without a second
    redaction."""
    content, other = b"the attachment to erase", b"the second attachment"
    address, other_address = sorted(hashlib.sha256(c).hexdigest() for c in (content, other))
    assert (
        main(_attach("a", _file(tmp_path, "a.txt", content), _file(tmp_path, "b.txt", other))) == 0
    )
    assert main(["project"]) == 0
    capsys.readouterr()

    monkeypatch.setenv("PREVIOUSLY_BLOB_ENDPOINT", "http://127.0.0.1:1")
    assert main(["redact", "event", "1", "--reason", "r"]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    line = _single_line(err)
    assert line.startswith(
        "Error: the redaction is recorded as event 2, but it is not finished: "
        f"blobs {address}, {other_address} are not deleted from the store ("
    )
    assert line.endswith("); run the same command again")
    assert "http://127.0.0.1:1" in line
    assert "is not caught up" not in line
    assert blobs.secret not in err
    assert _events(blobs.engine) == 2
    assert _bucket(blobs.store) == [address, other_address]
    # The catch-up ran although the deletion failed: the chronicle no longer
    # shows the erased text, and stands at the tip. Measured on 2026-10-05
    # with a deletion that raised before the catch-up: the chronicle still
    # printed the erased unit, and the lag on standard error.
    assert main(["chronicle"]) == 0
    assert capsys.readouterr() == ("", "")

    monkeypatch.setenv("PREVIOUSLY_BLOB_ENDPOINT", s3_settings["endpoint"])
    assert main(["redact", "event", "1", "--reason", "r"]) == 0
    assert capsys.readouterr() == ("already redacted by event 2\n", "")
    assert _bucket(blobs.store) == []
    assert _events(blobs.engine) == 2


@pytest.mark.db
@pytest.mark.s3
def test_a_delete_and_a_catch_up_that_both_fail_are_named_in_one_sentence(
    blobs: _Blobs,
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The store does not answer, and the log has a gap above the
    chronicle's `up_to_id`, forged with plain SQL the way
    `test_a_catch_up_that_fails_after_the_redaction_says_what_is_outstanding`
    forges it: the sentence names the deletion and then the catch-up, and
    still ends in the advice to run the same command again. Measured on
    2026-10-05 with the deletion raising as it used to: the sentence named
    the blob alone."""
    from sqlalchemy import text

    content = b"the attachment to erase"
    address = hashlib.sha256(content).hexdigest()
    assert main(_attach("a", _file(tmp_path, "a.txt", content))) == 0
    assert main(["project"]) == 0
    _append("cli", "b", "Two", "2026-10-02T09:00:00Z")
    _append("cli", "c", "Three", "2026-10-03T09:00:00Z")
    with blobs.engine.begin() as c:
        c.execute(text("DELETE FROM source_key WHERE event_id = 2"))
        c.execute(text("DELETE FROM unit WHERE event_id = 2"))
        c.execute(text("DELETE FROM event WHERE id = 2"))
    capsys.readouterr()

    monkeypatch.setenv("PREVIOUSLY_BLOB_ENDPOINT", "http://127.0.0.1:1")
    assert main(["redact", "event", "1", "--reason", "r"]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    line = _single_line(err)
    assert line.startswith(
        "Error: the redaction is recorded as event 4, but it is not finished: "
        f"blob {address} is not deleted from the store ("
    )
    assert line.endswith(
        "), and projection chronicle is not caught up (expected events 2.. above id 1, "
        "read [3, 4]; the tip is 4); run the same command again"
    )
    assert blobs.secret not in err


@pytest.mark.db
@pytest.mark.s3
def test_a_refused_redaction_deletes_nothing(
    blobs: _Blobs, capsys: pytest.CaptureFixture[str]
) -> None:
    """An object no event names, the kind an append that failed after its
    upload leaves behind: `redact blob` refuses it, and the object stays,
    since deleting comes only after a redaction stands."""
    address = hashlib.sha256(b"left behind").hexdigest()
    blobs.store.put(address, io.BytesIO(b"sealed bytes"), key_id=recipient_of(blobs.identity))

    assert main(["redact", "blob", address, "--reason", "r"]) == 2
    assert capsys.readouterr() == ("", f"Error: no event uses blob {address}\n")
    assert _bucket(blobs.store) == [address]


@pytest.mark.db
@pytest.mark.s3
def test_verify_blobs_prints_the_count(
    blobs: _Blobs, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(_attach("a", _file(tmp_path, "a.txt", b"first"))) == 0
    capsys.readouterr()
    assert main(["verify", "--blobs"]) == 0
    assert capsys.readouterr().out == "chain intact, 1 blob matches\n"

    assert main(_attach("b", _file(tmp_path, "b.txt", b"second"), tmp_path / "a.txt")) == 0
    capsys.readouterr()
    assert main(["verify", "--blobs"]) == 0
    assert capsys.readouterr().out == "chain intact, 2 blobs match\n"


@pytest.mark.db
@pytest.mark.s3
def test_verify_blobs_reports_a_missing_blob_and_returns_1(
    blobs: _Blobs, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    content = b"deleted by hand"
    address = hashlib.sha256(content).hexdigest()
    assert main(_attach("a", _file(tmp_path, "a.txt", content))) == 0
    blobs.store.delete(address)
    capsys.readouterr()

    assert main(["verify", "--blobs"]) == 1
    assert capsys.readouterr() == (f"FINDING 1: blob {address} is missing\n", "")


@pytest.mark.db
def test_show_marks_an_erased_blob(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """At an event with its payload, the line of a blob a blob redaction
    erased for the event names that redaction. At an erased event the blobs
    come from its redaction, each with the redaction that erased the
    reference first. Written through `core`, with references to blobs no
    store holds and without any blob setting: `show` does not ask the
    store."""
    engine = _connect(db, monkeypatch)
    for name in _BLOB_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    erased, kept = "1" * 64, "2" * 64
    storage = PostgresStorage(engine)
    append(
        storage,
        [
            RawEvent(
                source="cli",
                external_id="a",
                occurred_at=datetime(2026, 10, 1, 9, 0, 0, tzinfo=UTC),
                evidence=Evidence.VERBATIM,
                units=split_plaintext("See attached."),
                payload={"text": "See attached."},
                blobs=(
                    BlobRef(sha256=erased, size=12, media_type="text/plain", filename="a.txt"),
                    BlobRef(sha256=kept, size=3, media_type="text/plain", filename="b.txt"),
                ),
            )
        ],
        recorded_at=datetime(2026, 10, 2, 12, 0, 0, tzinfo=UTC),
    )
    now = datetime.now(UTC)
    redact_blob(storage, storage, erased, reason="r", recorded_at=now)

    assert main(["show", "1"]) == 0
    assert capsys.readouterr().out.endswith(
        "  ¶1 See attached.\n"
        f"  blob {erased} 12 text/plain a.txt <erased by event 2>\n"
        f"  blob {kept} 3 text/plain b.txt\n"
    )

    redact_event(storage, storage, 1, reason="r", recorded_at=now)
    assert main(["show", "1"]) == 0
    assert capsys.readouterr().out.endswith(
        "  ¶1 <erased by event 3>\n"
        f"  blob {erased} <erased by event 2>\n"
        f"  blob {kept} <erased by event 3>\n"
    )


@pytest.mark.db
def test_redacting_an_event_without_blobs_needs_no_blob_setting(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _connect(db, monkeypatch)
    for name in _BLOB_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    assert main(["append", "--source", "cli", "--external-id", "a", "--text", "One"]) == 0
    capsys.readouterr()
    assert main(["redact", "event", "1", "--reason", "r"]) == 0
    assert capsys.readouterr().out == "redacted by event 2\n"


class _CountedStore:
    """The real store, counting the times it is closed."""

    def __init__(self, inner: S3BlobStore, closed: list[int]) -> None:
        self._inner = inner
        self._closed = closed

    def stat(self, address: str) -> StoredBlob | None:
        return self._inner.stat(address)

    def put(self, address: str, sealed: IO[bytes], *, key_id: str) -> None:
        self._inner.put(address, sealed, key_id=key_id)

    def get(self, address: str) -> tuple[StoredBlob, ClosableSource] | None:
        return self._inner.get(address)

    def delete(self, address: str) -> None:
        self._inner.delete(address)

    def close(self) -> None:
        self._closed.append(1)
        self._inner.close()


@pytest.mark.db
@pytest.mark.s3
def test_every_command_closes_each_blob_store_it_builds(
    blobs: _Blobs,
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`verify --blobs` and the deletion after a redaction build a store
    and never upload, and a store that never uploads is freed by reference
    counting whether or not it is closed: with either one's close taken out,
    `test_main_releases_the_blob_store_it_opened` stayed green with both
    commands in its loop, measured on 2026-10-05. So the stores are counted
    instead, each one the command line builds against each `close`, on
    success and on error: the store the command line builds is the real one,
    wrapped so that its closing is seen."""
    from previously.storage import s3

    built: list[int] = []
    closed: list[int] = []

    def counted(**settings: str) -> _CountedStore:
        built.append(1)
        return _CountedStore(s3.from_settings(**settings), closed)

    monkeypatch.setattr("previously.cli.from_settings", counted)
    content = b"counted"
    address = hashlib.sha256(content).hexdigest()
    target = tmp_path / "out.txt"
    assert main(_attach("a", _file(tmp_path, "a.txt", content))) == 0
    assert main(_attach("b", tmp_path / "a.txt")) == 0
    assert main(["blob", "get", address, "--output", str(target)]) == 0
    assert main(["verify", "--blobs"]) == 0
    assert main(["redact", "event", "1", "--reason", "r"]) == 0  # keeps the blob
    assert main(["redact", "event", "2", "--reason", "r"]) == 0  # deletes it
    monkeypatch.setenv("PREVIOUSLY_BLOB_ENDPOINT", "http://127.0.0.1:1")
    assert main(["verify", "--blobs"]) == 2
    assert main(["redact", "blob", address, "--reason", "r"]) == 2
    capsys.readouterr()
    assert (len(built), len(closed)) == (7, 7)


@pytest.mark.parametrize("forged", [False, True], ids=["intact-chain", "forged-unit"])
@pytest.mark.parametrize(
    "failure", ["store-does-not-answer", "identity-cannot-be-read", "identity-is-not-one"]
)
@pytest.mark.db
@pytest.mark.s3
def test_verify_blobs_that_cannot_check_is_an_error_and_no_finding(
    blobs: _Blobs,
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    forged: bool,
) -> None:
    """A store that does not answer, an identity file that is there and
    cannot be read, or one whose content is no age identity says nothing
    about the blobs: one sentence, exit code 2, no `FINDING` line about a
    blob, and neither the secret of the store nor an identity nor the
    file's content in any output. The file in the third case holds a line
    that looks like an identity and is none, so that its content would show
    in the output. The finding on the other side of the line is
    `test_a_blob_whose_key_is_not_at_hand_cannot_be_opened_and_the_check_goes_on`
    in `tests/test_verify.py`.

    What the pass over the chain found before the blobs stands all the same:
    with a unit rewritten by hand, its finding is on standard output beside
    the error, so that a store that does not answer cannot hide a forgery.
    Measured on 2026-10-05 with the findings printed only after the blobs:
    standard output stayed empty."""
    assert main(_attach("a", _file(tmp_path, "a.txt", b"checked"))) == 0
    capsys.readouterr()
    if forged:
        from sqlalchemy import text

        with blobs.engine.begin() as c:
            c.execute(text("UPDATE unit SET content = 'forged' WHERE event_id = 1 AND seq = 1"))
    if failure == "store-does-not-answer":
        monkeypatch.setenv("PREVIOUSLY_BLOB_ENDPOINT", "http://127.0.0.1:1")
        expected = "http://127.0.0.1:1"
    elif failure == "identity-cannot-be-read":
        path = blobs.keys / recipient_of(blobs.identity)
        path.unlink()
        path.mkdir()
        expected = "cannot be read: IsADirectoryError"
    else:
        path = blobs.keys / recipient_of(blobs.identity)
        path.write_text("AGE-SECRET-KEY-1PREVIOUSLYTESTNOTAKEY\n", encoding="utf-8")
        expected = "the identity is not an age X25519 identity"

    assert main(["verify", "--blobs"]) == 2
    out, err = capsys.readouterr()
    assert out == ("FINDING 1: unit 1 does not match its digest\n" if forged else "")
    line = _single_line(err)
    assert line.startswith("Error: ")
    assert expected in line
    for secret in (blobs.secret, blobs.identity, "AGE-SECRET-KEY", "PREVIOUSLYTESTNOTAKEY"):
        assert secret not in out + err


@pytest.mark.parametrize("command", ["verify --blobs", "blob get"])
@pytest.mark.db
@pytest.mark.s3
def test_an_identity_directory_that_is_no_directory_is_a_configuration_error(
    blobs: _Blobs,
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    command: str,
) -> None:
    """`PREVIOUSLY_BLOB_IDENTITIES` naming a path that does not exist, or a
    file, is a configuration error: one sentence, exit code 2. Measured on
    2026-10-05 before the check: `verify --blobs` reported every blob as
    `cannot be opened` with exit code 1, which reads as a lost key on a
    freshly restored machine. The control: an existing directory without
    the identity stays a finding about that blob."""
    content = b"checked"
    address = hashlib.sha256(content).hexdigest()
    assert main(_attach("a", _file(tmp_path, "a.txt", content))) == 0
    capsys.readouterr()
    target = tmp_path / "out.bin"
    if command == "verify --blobs":
        argv = ["verify", "--blobs"]
    else:
        argv = ["blob", "get", address, "--output", str(target)]

    for nowhere in (tmp_path / "no-such-directory", _file(tmp_path, "a-file", b"")):
        monkeypatch.setenv("PREVIOUSLY_BLOB_IDENTITIES", str(nowhere))
        assert main(argv) == 2
        assert capsys.readouterr() == (
            "",
            f"Error: PREVIOUSLY_BLOB_IDENTITIES is not a directory: {nowhere}\n",
        )
        assert not target.exists()

    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("PREVIOUSLY_BLOB_IDENTITIES", str(empty))
    if command == "verify --blobs":
        assert main(argv) == 1
        assert capsys.readouterr().out == f"FINDING 1: blob {address} cannot be opened\n"
    else:
        assert main(argv) == 2
        assert _single_line(capsys.readouterr().err).startswith(
            f"Error: blob {address} cannot be opened: "
        )


def _append_naming(engine: Engine, *addresses: str) -> None:
    """One event per address that names it, written through `core` with
    references to blobs no store holds."""
    append(
        PostgresStorage(engine),
        [
            RawEvent(
                source="cli",
                external_id=address,
                occurred_at=datetime(2026, 10, 1, 9, 0, 0, tzinfo=UTC),
                evidence=Evidence.VERBATIM,
                units=split_plaintext("See attached."),
                payload={"text": "See attached."},
                blobs=(BlobRef(sha256=address, size=1, media_type="text/plain"),),
            )
            for address in addresses
        ],
        recorded_at=datetime(2026, 10, 2, 12, 0, 0, tzinfo=UTC),
    )


@pytest.mark.db
def test_blob_get_answers_from_the_log_without_any_blob_setting(
    db: object,
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ "No event uses it" and "it is erased" are answers about the log, and
    come on a machine without a single blob setting. The blob that is
    neither needs the store, and the first setting it reads is the control
    that the settings are really missing."""
    engine = _connect(db, monkeypatch)
    for name in _BLOB_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    kept, erased, unused = "1" * 64, "2" * 64, "3" * 64
    _append_naming(engine, kept, erased)
    storage = PostgresStorage(engine)
    redact_blob(storage, storage, erased, reason="r", recorded_at=datetime.now(UTC))
    target = str(tmp_path / "out.bin")

    assert main(["blob", "get", unused, "--output", target]) == 1
    assert capsys.readouterr() == ("", f"no event uses blob {unused}\n")
    assert main(["blob", "get", erased, "--output", target]) == 1
    assert capsys.readouterr() == ("", f"blob {erased} is erased (event 3)\n")
    assert main(["blob", "get", kept, "--output", target]) == 2
    assert capsys.readouterr() == ("", "Error: PREVIOUSLY_BLOB_IDENTITIES is not set\n")


# --- ingest imap ({ref}`cli-reference`) ---------------------------------------

_IMAP_VARIABLES = (
    "PREVIOUSLY_IMAP_ADDRESS",
    "PREVIOUSLY_IMAP_USER",
    "PREVIOUSLY_IMAP_PASSWORD",
    "PREVIOUSLY_IMAP_FOLDER",
)
# The folder every test of `ingest imap` reads, at `127.0.0.1`: an address
# the certificate of the test server names, and the one the relay listens on,
# so that a run through the relay keeps the watermark of a run without it —
# the host is part of the connector's name, the port is not.
_IMAP_HOST = "127.0.0.1"
_IMAP_CONNECTOR = "imap:pilot@127.0.0.1/Kunde Müller"


@pytest.fixture
def imap(
    blobs: _Blobs,
    mail_server: MailServer,
    imap_folder: str,
    monkeypatch: pytest.MonkeyPatch,
) -> _Blobs:
    """What the blob commands work with, a folder of four mails at UIDs 1 to
    4, and the four settings that reach it.

    The command line keeps no switch for a certificate it cannot verify, so
    the test trusts the server the way OpenSSL trusts anything:
    `SSL_CERT_FILE` names the certificate the container made, and the
    default context reads it. The directory of identities is unset, because
    taking in reads none."""
    values = (f"{_IMAP_HOST}:{mail_server.port}", mail_server.user, mail_server.password)
    for name, value in zip(_IMAP_VARIABLES, (*values, imap_folder), strict=True):
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("SSL_CERT_FILE", str(mail_server.certificate))
    monkeypatch.delenv("PREVIOUSLY_BLOB_IDENTITIES")
    return blobs


def _imap_watermark(engine: Engine) -> dict[str, str] | None:
    storage = PostgresStorage(engine)
    with storage.snapshot() as conn:
        mark = storage.watermark(conn, _IMAP_CONNECTOR)
    return None if mark is None else dict(mark.position)


@pytest.mark.db
@pytest.mark.s3
@pytest.mark.imap
def test_ingest_imap_takes_in_the_folder_and_a_second_run_appends_nothing(
    imap: _Blobs, capsys: pytest.CaptureFixture[str]
) -> None:
    """Four mails, five events — the fourth has a mail attached — and then
    nothing new. The chronicle shows each subject once the projections are
    caught up."""
    assert main(["ingest", "imap"]) == 0
    assert capsys.readouterr() == (
        "imap: 5 appended, 0 known, 0 variants, up to uid 4 in Kunde Müller\n",
        "",
    )
    assert main(["ingest", "imap"]) == 0
    assert capsys.readouterr() == (
        "imap: 0 appended, 0 known, 0 variants, up to uid 4 in Kunde Müller\n",
        "",
    )
    assert _events(imap.engine) == 5

    assert main(["project"]) == 0
    capsys.readouterr()
    assert main(["chronicle"]) == 0
    out, err = capsys.readouterr()
    assert err == ""
    contents = {line.split("\t")[5] for line in out.splitlines()}
    assert {
        "Angebot für den Relaunch",
        "Re: Angebot für den Relaunch",
        "AW: Angebot für den Relaunch",
        "Fwd: Rechnung Oktober",
        "Rechnung Oktober",
    } <= contents


@pytest.mark.db
@pytest.mark.s3
@pytest.mark.imap
def test_ingest_imap_names_each_variant_on_standard_error(
    imap: _Blobs, mail_server: MailServer, imap_folder: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """A mail under a Message-ID the log holds with another body is taken in
    as a variant, counted on standard output and named on standard error."""
    assert main(["ingest", "imap"]) == 0
    capsys.readouterr()
    mail_server.append(imap_folder, mailfiles.PLAIN_OTHER_BODY)
    assert main(["ingest", "imap"]) == 0
    assert capsys.readouterr() == (
        "imap: 1 appended, 0 known, 1 variants, up to uid 5 in Kunde Müller\n",
        "variant of 20261005101500.4711@example.net: event 6\n",
    )


@pytest.mark.db
@pytest.mark.s3
@pytest.mark.imap
def test_ingest_imap_escapes_a_control_in_the_message_id_of_a_variant(
    imap: _Blobs, mail_server: MailServer, imap_folder: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """The Message-ID is the sender's, raw ESC and BEL included; the line
    that names the variant writes them as `\\xNN`."""
    plain_id = b"<20261005101500.4711@example.net>"
    hostile_id = b"<ein\x1b]0;Titel\x07@example.net>"
    assert main(["ingest", "imap"]) == 0
    capsys.readouterr()
    mail_server.append(imap_folder, mailfiles.PLAIN.replace(plain_id, hostile_id))
    mail_server.append(imap_folder, mailfiles.PLAIN_OTHER_BODY.replace(plain_id, hostile_id))
    assert main(["ingest", "imap"]) == 0
    assert capsys.readouterr() == (
        "imap: 2 appended, 0 known, 1 variants, up to uid 6 in Kunde Müller\n",
        "variant of ein\\x1b]0;Titel\\x07@example.net: event 7\n",
    )


@pytest.mark.db
def test_an_error_writes_a_control_in_the_key_it_quotes_as_hex(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`ArtifactChanged` quotes the key, and the key of a mail is its
    Message-ID; the `Error:` line writes a control in it as `\\xNN`."""
    _setup(db, monkeypatch)
    submit = ["append", "--source", "cli", "--external-id", "a\x1b[2Jb", "--text"]
    assert main([*submit, "A"]) == 0
    assert main([*submit, "B"]) == 2
    err = capsys.readouterr().err
    assert _raw_controls(err) == []
    assert err.startswith("Error: cli/a\\x1b[2Jb is known with another content")


@pytest.mark.db
@pytest.mark.s3
@pytest.mark.imap
@pytest.mark.parametrize("tail", ["", "-Grüße"])
def test_ingest_imap_refuses_a_wrong_password_without_printing_it(
    imap: _Blobs,
    mail_server: MailServer,
    tail: str,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One sentence, exit code 2, and the password in neither stream: a
    password the server refuses, and one with a character beyond ASCII,
    which `imaplib` writes the login in and would otherwise end in a stack
    trace."""
    password = f"wrong-{secrets.token_hex(8)}{tail}"
    monkeypatch.setenv("PREVIOUSLY_IMAP_PASSWORD", password)
    assert main(["ingest", "imap"]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    server = f"{_IMAP_HOST}:{mail_server.port}"
    if tail:
        assert err == (
            f"Error: the login of pilot at the IMAP server {server} holds a character other "
            "than ASCII, and previously sends the login in ASCII only\n"
        )
    else:
        assert err == f"Error: the IMAP server {server} refused the login of pilot\n"
    for secret in (password, password.removeprefix("wrong-"), mail_server.password):
        assert secret not in out + err
    assert _events(imap.engine) == 0
    assert _imap_watermark(imap.engine) is None


@pytest.mark.db
@pytest.mark.s3
@pytest.mark.imap
def test_ingest_imap_verifies_the_certificate_and_the_host_name(
    imap: _Blobs,
    mail_server: MailServer,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without `SSL_CERT_FILE`, the system trusts nothing the container made;
    with it, a name the certificate does not carry is refused all the same.
    `127.0.0.2` reaches the same server on Linux, where all of `127.0.0.0/8`
    is the loopback."""
    monkeypatch.delenv("SSL_CERT_FILE")
    assert main(["ingest", "imap"]) == 2
    assert capsys.readouterr() == (
        "",
        f"Error: the certificate of the IMAP server {_IMAP_HOST}:{mail_server.port} "
        "does not verify: self-signed certificate\n",
    )

    monkeypatch.setenv("SSL_CERT_FILE", str(mail_server.certificate))
    monkeypatch.setenv("PREVIOUSLY_IMAP_ADDRESS", f"127.0.0.2:{mail_server.port}")
    assert main(["ingest", "imap"]) == 2
    assert capsys.readouterr() == (
        "",
        f"Error: the certificate of the IMAP server 127.0.0.2:{mail_server.port} "
        "does not verify: IP address mismatch, certificate is not valid for '127.0.0.2'.\n",
    )
    assert _events(imap.engine) == 0


def _large_mail(number: int) -> bytes:
    """An invented mail of a little over 1 MiB, most of it an attachment of
    one byte value repeated: its size is what a test of the relay needs, not
    its content."""
    head = (
        "From: Archiv <archiv@example.org>",
        "To: pilot@example.org",
        f"Subject: Scan {number}",
        "Date: Tue, 06 Oct 2026 08:00:00 +0200",
        f"Message-ID: <scan-large-{number}@example.org>",
        "MIME-Version: 1.0",
        'Content-Type: multipart/mixed; boundary="part"',
        "",
        "--part",
        "Content-Type: text/plain; charset=utf-8",
        "",
        f"Scan {number}, invented for this test.",
        "--part",
        "Content-Type: application/octet-stream",
        f'Content-Disposition: attachment; filename="scan-{number}.bin"',
        "Content-Transfer-Encoding: base64",
        "",
    )
    attachment = mailfiles.base64_lines(bytes([number]) * (768 * 1024))
    return b"\r\n".join([*(line.encode() for line in head), *attachment, b"--part--"]) + b"\r\n"


@pytest.mark.db
@pytest.mark.s3
@pytest.mark.imap
def test_ingest_imap_stops_at_a_dropped_connection_with_the_watermark_at_the_last_batch(
    imap: _Blobs,
    mail_server: MailServer,
    imap_folder: str,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The connection breaks off in the middle of a run: one sentence, exit
    code 2, nothing of the broken batch in the log, and the watermark where
    the last appended batch left it. The next run takes in the rest.

    The break is a relay that ends the connection once the server has sent
    the size of the first large mail and half a mebibyte more (`Relay`): the
    login, the search and the first mail take a few kibibytes beyond that
    size, so the break falls about half a mebibyte into the second. Stopping
    the container from a thread while the run fetches was the other way, and
    it is not one a test can rely on: the session's server would be gone for
    every later test, and where the stop lands — before the login, between
    two mails, after the run — depends on how two threads are scheduled. A
    byte count puts the break inside the second mail every time."""
    assert main(["ingest", "imap"]) == 0
    capsys.readouterr()
    mail_server.append(imap_folder, _large_mail(1), _large_mail(2))

    with Relay(mail_server, limit=len(_large_mail(1)) + 512 * 1024) as relay:
        monkeypatch.setenv("PREVIOUSLY_IMAP_ADDRESS", f"{_IMAP_HOST}:{relay.port}")
        assert main(["ingest", "imap"]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    # Nothing of the mail either: `imaplib` aborts here with a header line of
    # the second mail in its text (see `ImapConnector._speaking`).
    assert err == (
        "Error: folder Kunde Müller: "
        f"the connection to the IMAP server {_IMAP_HOST}:{relay.port} broke off\n"
    )
    assert mail_server.password not in err
    assert "example.org" not in err
    assert _imap_watermark(imap.engine) == {
        "uidvalidity": mail_server.uidvalidity(imap_folder),
        "uid": "4",
    }
    assert _events(imap.engine) == 5

    monkeypatch.setenv("PREVIOUSLY_IMAP_ADDRESS", f"{_IMAP_HOST}:{mail_server.port}")
    assert main(["ingest", "imap"]) == 0
    assert capsys.readouterr() == (
        "imap: 2 appended, 0 known, 0 variants, up to uid 6 in Kunde Müller\n",
        "",
    )


# --- ingest imap over several folders ------------------------------------------

# The mails of `imap_folder` as files, for a second folder that holds them too.
_MAILS = pathlib.Path(__file__).resolve().parent / "mails"


def _folder_line(appended: int, known: int, uid: int, folder: str) -> str:
    return f"imap: {appended} appended, {known} known, 0 variants, up to uid {uid} in {folder}\n"


def _watermark_of(engine: Engine, folder: str) -> dict[str, str] | None:
    storage = PostgresStorage(engine)
    with storage.snapshot() as conn:
        mark = storage.watermark(conn, f"imap:pilot@{_IMAP_HOST}/{folder}")
    return None if mark is None else dict(mark.position)


@pytest.mark.db
@pytest.mark.s3
@pytest.mark.imap
def test_ingest_imap_reads_each_folder_with_its_own_watermark_and_line(
    imap: _Blobs, mail_server: MailServer, imap_folder: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """Two folders in one run: each is read, each line names its folder, and
    each folder moves a watermark of its own. A mail added to one of them
    is the next run's only news, and it comes from that folder alone."""
    mail_server.recreate("Gesendet")
    mail_server.append("Gesendet", (_MAILS / "signed.eml").read_bytes())
    both = ["ingest", "imap", "--folder", imap_folder, "--folder", "Gesendet"]

    assert main(both) == 0
    assert capsys.readouterr() == (
        _folder_line(5, 0, 4, "Kunde Müller") + _folder_line(1, 0, 1, "Gesendet"),
        "",
    )
    assert _watermark_of(imap.engine, "Kunde Müller") == {
        "uidvalidity": mail_server.uidvalidity(imap_folder),
        "uid": "4",
    }
    assert _watermark_of(imap.engine, "Gesendet") == {
        "uidvalidity": mail_server.uidvalidity("Gesendet"),
        "uid": "1",
    }

    mail_server.append("Gesendet", (_MAILS / "encrypted.eml").read_bytes())
    assert main(both) == 0
    assert capsys.readouterr() == (
        _folder_line(0, 0, 4, "Kunde Müller") + _folder_line(1, 0, 2, "Gesendet"),
        "",
    )
    assert _events(imap.engine) == 7


@pytest.mark.db
@pytest.mark.s3
@pytest.mark.imap
def test_ingest_imap_reads_a_folder_named_twice_once_and_the_setting_not_beside_an_option(
    imap: _Blobs, mail_server: MailServer, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--folder` takes the place of `PREVIOUSLY_IMAP_FOLDER`, which still
    names `Kunde Müller` here, and the same name twice is one folder."""
    mail_server.recreate("Gesendet")
    mail_server.append("Gesendet", (_MAILS / "signed.eml").read_bytes())
    assert main(["ingest", "imap", "--folder", "Gesendet", "--folder", "Gesendet"]) == 0
    assert capsys.readouterr() == (_folder_line(1, 0, 1, "Gesendet"), "")
    assert _watermark_of(imap.engine, "Kunde Müller") is None


@pytest.mark.db
@pytest.mark.s3
@pytest.mark.imap
def test_ingest_imap_takes_the_same_mail_in_two_folders_in_once(
    imap: _Blobs, mail_server: MailServer, imap_folder: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """The second folder holds the same four mails, the first of them as it
    arrived in another mailbox, with other `Received` lines: the same
    Message-ID and the same content, so every event of the second folder is
    known, and the log holds each mail once, found where it was first."""
    mail_server.recreate("Kopie")
    copies = [mailfiles.PLAIN_OTHER_TRANSPORT]
    copies += [(_MAILS / name).read_bytes() for name in ("reply.eml", "html_only.eml")]
    copies += [(_MAILS / "forwarded.eml").read_bytes()]
    mail_server.append("Kopie", *copies)

    assert main(["ingest", "imap", "--folder", imap_folder, "--folder", "Kopie"]) == 0
    assert capsys.readouterr() == (
        _folder_line(5, 0, 4, "Kunde Müller") + _folder_line(0, 5, 4, "Kopie"),
        "",
    )
    assert _events(imap.engine) == 5
    storage = PostgresStorage(imap.engine)
    with storage.snapshot() as conn:
        found = [
            cast("dict[str, str]", row.payload["found_in"])["connector"]
            for row in storage.read(conn, 1, 100)
            if row.payload is not None
        ]
    assert found == [_IMAP_CONNECTOR] * 5


@pytest.mark.db
@pytest.mark.s3
@pytest.mark.imap
def test_ingest_imap_goes_on_after_a_folder_it_cannot_open(
    imap: _Blobs, mail_server: MailServer, imap_folder: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """A folder the server does not have: one line on standard error that
    names it and the server's reason, the next folder is read all the same,
    and the run returns 2."""
    assert main(["ingest", "imap", "--folder", "Nirgendwo", "--folder", imap_folder]) == 2
    server = f"{_IMAP_HOST}:{mail_server.port}"
    assert capsys.readouterr() == (
        _folder_line(5, 0, 4, "Kunde Müller"),
        f"Error: folder Nirgendwo: the IMAP server {server} refused to open the folder "
        "'Nirgendwo' of pilot: EXAMINE failed. No such mailbox\n",
    )
    assert _watermark_of(imap.engine, "Kunde Müller") is not None


@pytest.mark.db
@pytest.mark.s3
@pytest.mark.imap
def test_ingest_imap_goes_on_after_a_folder_whose_connection_broke_off(
    imap: _Blobs,
    mail_server: MailServer,
    imap_folder: str,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The connection of the first folder breaks off inside its second large
    mail (`Relay`, as in the test of a single folder above); the second
    folder is read over a connection of its own. Nothing of the first folder
    is in the log, and its watermark is unset, since its one batch was never
    appended. The line on standard error names the folder and nothing of the
    mail."""
    mail_server.recreate("Scans")
    mail_server.append("Scans", _large_mail(1), _large_mail(2))
    with Relay(mail_server, limit=len(_large_mail(1)) + 512 * 1024, first_only=True) as relay:
        monkeypatch.setenv("PREVIOUSLY_IMAP_ADDRESS", f"{_IMAP_HOST}:{relay.port}")
        assert main(["ingest", "imap", "--folder", "Scans", "--folder", imap_folder]) == 2
    assert capsys.readouterr() == (
        _folder_line(5, 0, 4, "Kunde Müller"),
        f"Error: folder Scans: the connection to the IMAP server {_IMAP_HOST}:{relay.port} "
        "broke off\n",
    )
    assert _watermark_of(imap.engine, "Scans") is None
    assert _events(imap.engine) == 5


@pytest.mark.db
@pytest.mark.s3
@pytest.mark.imap
def test_ingest_imap_goes_on_after_a_mail_the_log_refuses(
    imap: _Blobs, mail_server: MailServer, imap_folder: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """A mail with 500 mails attached is 501 events, more than one batch
    holds, and the log refuses it at every run until it leaves its folder;
    the folders after it are read all the same."""
    inner = mailfiles.PLAIN.replace(b"<20261005101500.4711@example.net>", b"<inner-{}@example.org>")
    attached = b"".join(
        b"--part\r\nContent-Type: message/rfc822\r\n\r\n"
        + inner.replace(b"{}", str(number).encode())
        for number in range(500)
    )
    huge = (
        b"From: archiv@example.org\r\nTo: pilot@example.org\r\nSubject: Sammlung\r\n"
        b"Date: Tue, 06 Oct 2026 08:00:00 +0200\r\nMessage-ID: <sammlung@example.org>\r\n"
        b'MIME-Version: 1.0\r\nContent-Type: multipart/mixed; boundary="part"\r\n\r\n'
        + attached
        + b"--part--\r\n"
    )
    mail_server.recreate("Sammlung")
    mail_server.append("Sammlung", huge)
    assert main(["ingest", "imap", "--folder", "Sammlung", "--folder", imap_folder]) == 2
    assert capsys.readouterr() == (
        _folder_line(5, 0, 4, "Kunde Müller"),
        "Error: folder Sammlung: 501 events in one transaction, 500 are allowed — "
        "larger batches starve against small submissions\n",
    )


@pytest.mark.db
@pytest.mark.s3
@pytest.mark.imap
def test_ingest_imap_stops_at_a_refused_login_before_the_next_folder(
    imap: _Blobs,
    mail_server: MailServer,
    imap_folder: str,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A refused login is the mailbox's, not a folder's: every folder would
    be refused the same way, so the run stops at the first, with the one
    sentence a single folder gets, and no folder in front of it."""
    monkeypatch.setenv("PREVIOUSLY_IMAP_PASSWORD", f"wrong-{secrets.token_hex(8)}")
    assert main(["ingest", "imap", "--folder", imap_folder, "--folder", "Gesendet"]) == 2
    assert capsys.readouterr() == (
        "",
        f"Error: the IMAP server {_IMAP_HOST}:{mail_server.port} refused the login of pilot\n",
    )


@pytest.mark.db
@pytest.mark.s3
@pytest.mark.imap
def test_ingest_imap_keeps_the_watermark_of_the_setting_for_the_option(
    imap: _Blobs, mail_server: MailServer, imap_folder: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """A deployment that named its folder in `PREVIOUSLY_IMAP_FOLDER` has a
    watermark under `imap:<user>@<host>/<folder>`; the same folder given
    with `--folder` reads on from it, and the setting reads on from where
    the option left it. Read from the start instead, the second run would
    count five events as known."""
    assert main(["ingest", "imap"]) == 0
    assert capsys.readouterr().out == _folder_line(5, 0, 4, "Kunde Müller")
    assert _imap_watermark(imap.engine) == {
        "uidvalidity": mail_server.uidvalidity(imap_folder),
        "uid": "4",
    }

    mail_server.append(imap_folder, (_MAILS / "signed.eml").read_bytes())
    assert main(["ingest", "imap", "--folder", "Kunde Müller"]) == 0
    assert capsys.readouterr().out == _folder_line(1, 0, 5, "Kunde Müller")

    mail_server.append(imap_folder, (_MAILS / "encrypted.eml").read_bytes())
    assert main(["ingest", "imap"]) == 0
    assert capsys.readouterr().out == _folder_line(1, 0, 6, "Kunde Müller")
    assert _imap_watermark(imap.engine) == {
        "uidvalidity": mail_server.uidvalidity(imap_folder),
        "uid": "6",
    }


def test_ingest_imap_needs_no_folder_setting_beside_the_option(
    age_identity: str, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """With `--folder`, `PREVIOUSLY_IMAP_FOLDER` is not read: the run gets as
    far as connecting, to the database first. An empty name is refused
    before any setting is read, the way an empty setting is refused."""
    _unreachable(age_identity, monkeypatch)
    monkeypatch.delenv("PREVIOUSLY_IMAP_FOLDER")
    assert main(["ingest", "imap", "--folder", "Kunde Müller"]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err.startswith("Error: connecting to database previously at 127.0.0.1:1 failed: ")

    monkeypatch.delenv("PREVIOUSLY_IMAP_ADDRESS")
    assert main(["ingest", "imap", "--folder", "Kunde Müller", "--folder", ""]) == 2
    assert capsys.readouterr() == ("", "Error: --folder must not be empty\n")


# Every setting `ingest imap` needs, each pointing nowhere that answers: a
# run that connected anywhere before it had read them all would end in an
# error of that connection instead of naming the setting.
_UNREACHABLE = {
    "PREVIOUSLY_IMAP_ADDRESS": "127.0.0.1:1",
    "PREVIOUSLY_IMAP_USER": "pilot",
    "PREVIOUSLY_IMAP_PASSWORD": "not-the-password",
    "PREVIOUSLY_IMAP_FOLDER": "Kunde Müller",
    "PREVIOUSLY_DSN": "postgresql://previously:pw@127.0.0.1:1/previously",
    "PREVIOUSLY_BLOB_ENDPOINT": "http://127.0.0.1:1",
    "PREVIOUSLY_BLOB_REGION": "us-east-1",
    "PREVIOUSLY_BLOB_BUCKET": "nowhere",
    "PREVIOUSLY_BLOB_ACCESS_KEY": "nobody",
    "PREVIOUSLY_BLOB_SECRET_KEY": "nothing",
}


def _unreachable(age_identity: str, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = {**_UNREACHABLE, "PREVIOUSLY_BLOB_RECIPIENT": recipient_of(age_identity)}
    for name, value in settings.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("PREVIOUSLY_BLOB_IDENTITIES", raising=False)


@pytest.mark.parametrize(
    "missing",
    [
        *_UNREACHABLE,
        "PREVIOUSLY_BLOB_RECIPIENT",
    ],
)
def test_ingest_imap_names_a_missing_setting_before_it_connects(
    missing: str,
    age_identity: str,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _unreachable(age_identity, monkeypatch)
    monkeypatch.delenv(missing)
    assert main(["ingest", "imap"]) == 2
    assert capsys.readouterr() == ("", f"Error: {missing} is not set\n")


def test_ingest_imap_reads_every_setting_and_then_connects(
    age_identity: str, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control of the test above: with every setting there, and the
    directory of identities not, the run gets as far as connecting — to the
    database first, for the watermark. An address of another form is refused
    before that, like a missing setting.

    `PREVIOUSLY_IMAP_PORT` is what Kubernetes sets for a Service named
    `previously-imap`, and nothing reads it any more: set to what the kubelet
    writes, it changes nothing."""
    _unreachable(age_identity, monkeypatch)
    monkeypatch.setenv("PREVIOUSLY_IMAP_PORT", "tcp://10.43.0.6:993")
    assert main(["ingest", "imap"]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err.startswith("Error: connecting to database previously at 127.0.0.1:1 failed: ")

    for address in ("tcp://10.43.0.6:993", "mail.example.org:imaps", "::1", "[::1]:0"):
        monkeypatch.setenv("PREVIOUSLY_IMAP_ADDRESS", address)
        assert main(["ingest", "imap"]) == 2
        assert capsys.readouterr() == (
            "",
            "Error: PREVIOUSLY_IMAP_ADDRESS is not host or host:port, "
            f"with an IPv6 host in brackets: {address!r}\n",
        )


def test_ingest_imap_says_that_the_host_setting_was_renamed(
    age_identity: str, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A deployment of the release before carries `PREVIOUSLY_IMAP_HOST`; the
    run names the setting that took its place instead of only the missing
    one. Without the old name, the missing one is all it says."""
    _unreachable(age_identity, monkeypatch)
    monkeypatch.delenv("PREVIOUSLY_IMAP_ADDRESS")
    monkeypatch.setenv("PREVIOUSLY_IMAP_HOST", "mail.example.org")
    assert main(["ingest", "imap"]) == 2
    assert capsys.readouterr() == (
        "",
        "Error: PREVIOUSLY_IMAP_HOST is not read any more: "
        "set PREVIOUSLY_IMAP_ADDRESS to host or host:port\n",
    )
    monkeypatch.setenv("PREVIOUSLY_IMAP_HOST", "")
    assert main(["ingest", "imap"]) == 2
    assert capsys.readouterr() == ("", "Error: PREVIOUSLY_IMAP_ADDRESS is not set\n")


# --- policy ------------------------------------------------------------------


def _answer(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(text.encode())))


def _action_count(db: object) -> int:
    from sqlalchemy import Engine
    from sqlalchemy import text

    assert isinstance(db, Engine)
    with db.begin() as c:
        return c.execute(text("SELECT count(*) FROM event WHERE kind = 'action'")).scalar_one()


@pytest.mark.db
def test_policy_circle_with_yes_writes_and_show_lists_it_with_the_built_in_rule(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup(db, monkeypatch)
    argv = ["policy", "circle", "xz", "--statement", "customer xz", "--yes"]
    assert main(argv) == 0
    out = capsys.readouterr().out
    assert '"name": "xz"' in out
    assert out.endswith("policy event 1\n")
    assert main(["policy", "show"]) == 0
    shown = capsys.readouterr().out
    assert "circles\n  xz\t(event 1)\n" in shown
    assert "local_only\tbuilt-in: without a rule, only providers with local" in shown


@pytest.mark.db
def test_policy_circle_asks_and_an_n_writes_nothing(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup(db, monkeypatch)
    _answer(monkeypatch, "n\n")
    assert main(["policy", "circle", "xz", "--statement", "s"]) == 1
    captured = capsys.readouterr()
    assert "write? [y/N]" in captured.out
    assert captured.err == "nothing written\n"
    assert _action_count(db) == 0


@pytest.mark.db
def test_policy_circle_asks_and_a_y_writes(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control of the `n` above."""
    _setup(db, monkeypatch)
    _answer(monkeypatch, "y\n")
    assert main(["policy", "circle", "xz", "--statement", "s"]) == 0
    assert _action_count(db) == 1


# What a command that asks says when its input ends without an answer, as
# under `kubectl exec` without `-i`: the `n` above says `nothing written` alone.
_NO_ANSWER = "no answer: the input ended before one came; --yes writes without asking\n"


@pytest.mark.db
def test_policy_without_an_answer_writes_nothing_and_names_yes(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup(db, monkeypatch)
    _answer(monkeypatch, "")
    assert main(["policy", "circle", "xz", "--statement", "s"]) == 1
    assert capsys.readouterr().err == _NO_ANSWER + "nothing written\n"
    assert _action_count(db) == 0


@pytest.mark.db
def test_a_membership_in_a_circle_that_does_not_exist_is_one_sentence_and_nothing_is_written(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review focus 5 of the 2026-10-09 plan, on the command line: return 2,
    one sentence, no question asked, nothing written."""
    _setup(db, monkeypatch)
    argv = ["policy", "member", "nowhere", "eva@kunde-xz.at", "--statement", "s", "--yes"]
    assert main(argv) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err.count("\n") == 1
    assert err.startswith('Error: no circle "nowhere" exists')
    assert _action_count(db) == 0


@pytest.mark.db
def test_a_rule_for_a_project_is_refused_on_the_command_line(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup(db, monkeypatch)
    argv = ["policy", "rule", "project:alpha", "--regions", "eu", "--statement", "s", "--yes"]
    assert main(argv) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err.count("\n") == 1
    assert "is not effective yet" in err
    assert _action_count(db) == 0


@pytest.mark.db
def test_policy_rule_provider_member_own_and_revoke_round_trip_through_show(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup(db, monkeypatch)
    steps = [
        ["circle", "xz", "--statement", "s"],
        ["member", "xz", "@Kunde-XZ.at", "--statement", "s"],
        ["own", "me@mine.example", "--statement", "s"],
        [
            *("rule", "circle:xz", "--regions", "eu", "--max-retention-days", "0"),
            *("--exclude-provider", "anthropic", "--no-training", "--no-subprocessors"),
            *("--exclude-operator", "zeta", "--exclude-operator", "alpha"),
            *("--exclude-model-origin", "cn", "--statement", "s"),
        ],
        [
            *("provider", "anthropic", "--inference", "global=any", "--inference", "us=us"),
            *("--storage", "us", "--retention-days", "30", "--reports-geo", "--statement", "s"),
            *("--operator", "Anthropic PBC", "--training", "no", "--subprocessors", "aws", "gcp"),
            *("--model-origin", "us"),
        ],
    ]
    for step in steps:
        assert main(["policy", *step, "--yes"]) == 0
    capsys.readouterr()
    assert main(["policy", "show"]) == 0
    shown = capsys.readouterr().out
    assert "  xz\t@kunde-xz.at\t(event 2)" in shown
    assert "  me@mine.example\t(event 3)" in shown
    assert (
        "  circle:xz\tregions eu\tmax retention days 0\texcluded anthropic"
        "\tno training yes\tno subprocessors yes\texcluded operators alpha,zeta"
        "\texcluded model origins cn\t(event 4)" in shown
    )
    assert (
        "  anthropic\tinference global=any,us=us\tstorage us\tretention days 30"
        "\treports geo yes\tlocal no\toperator Anthropic PBC\ttraining no"
        "\tsubprocessors aws,gcp\tmodel origin us\t(event 5)" in shown
    )

    revoke = ["policy", "member", "xz", "@kunde-xz.at", "--statement", "gone", "--revoke", "--yes"]
    assert main(revoke) == 0
    capsys.readouterr()
    assert main(["policy", "show"]) == 0
    assert "@kunde-xz.at" not in capsys.readouterr().out


@pytest.mark.db
@pytest.mark.parametrize("storage", [None, [], ["eu"]], ids=["omitted", "empty", "eu"])
def test_policy_provider_requires_storage(
    db: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    storage: list[str] | None,
) -> None:
    """An empty storage passes every region rule, so a forgotten
    `--storage` would declare the provider the loosest it can be: argparse
    refuses the omission and writes nothing. Given with no region, it is
    written as `storage: []`, the way a local provider is declared."""
    _setup(db, monkeypatch)
    argv = ["policy", "provider", "local", "--inference", "eu=eu", "--retention-days", "0"]
    argv += [*("--operator", "me", "--training", "no", "--subprocessors", "none")]
    argv += [] if storage is None else ["--storage", *storage]
    argv += ["--statement", "s", "--yes"]
    if storage is None:
        with pytest.raises(SystemExit) as raised:
            main(argv)
        assert raised.value.code == 2
        assert "the following arguments are required: --storage" in capsys.readouterr().err
        assert _action_count(db) == 0
        return
    assert main(argv) == 0
    statement, _ = capsys.readouterr().out.rsplit("policy event ", 1)
    assert json.loads(statement)["storage"] == storage
    assert _action_count(db) == 1


@pytest.mark.db
def test_policy_show_at_reads_the_policy_of_that_moment(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup(db, monkeypatch)
    assert main(["policy", "circle", "xz", "--statement", "s", "--yes"]) == 0
    capsys.readouterr()
    assert main(["policy", "show", "--at", "2000-01-01T00:00:00Z"]) == 0
    assert "  xz" not in capsys.readouterr().out
    assert main(["policy", "show", "--at", "2999-01-01T00:00:00Z"]) == 0
    assert "  xz" in capsys.readouterr().out
    assert main(["policy", "show", "--at", "2999-01-01T00:00:00"]) == 2


def test_the_help_names_policy_with_its_sentence(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])
    assert re.search(
        r"^\s+policy\s+set and show the processing policy$", capsys.readouterr().out, re.M
    )


def test_the_help_names_gate_with_its_sentence(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])
    assert re.search(r"^\s+gate\s+explain or try a model call$", capsys.readouterr().out, re.M)


_CHAIN_ARGUMENTS = {
    "--operator": "acme",
    "--training": "no",
    "--subprocessors": "none",
}


@pytest.mark.db
@pytest.mark.parametrize("omitted", [None, "--operator", "--training", "--subprocessors"])
def test_policy_provider_requires_the_processing_chain(
    db: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    omitted: str | None,
) -> None:
    """An unknown chain passes no restriction, so a forgotten option would
    declare a provider that no rule can use, and silently: argparse refuses
    the omission and writes nothing. `omitted=None` is the control that
    writes."""
    _setup(db, monkeypatch)
    argv = ["policy", "provider", "p", "--inference", "eu=eu", "--storage", "eu"]
    argv += ["--retention-days", "0", "--statement", "s", "--yes"]
    for option, value in _CHAIN_ARGUMENTS.items():
        if option != omitted:
            argv += [option, value]
    if omitted is None:
        assert main(argv) == 0
        assert _action_count(db) == 1
        return
    with pytest.raises(SystemExit) as raised:
        main(argv)
    assert raised.value.code == 2
    assert f"the following arguments are required: {omitted}" in capsys.readouterr().err
    assert _action_count(db) == 0


@pytest.mark.db
@pytest.mark.parametrize(
    ("training", "subprocessors", "expected_training", "expected_subprocessors"),
    [
        ("yes", ["none"], True, []),
        ("no", ["unknown"], False, None),
        ("unknown", ["b", "a"], None, ["a", "b"]),
    ],
)
def test_policy_provider_writes_the_chain_in_the_payload(
    db: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    training: str,
    subprocessors: list[str],
    expected_training: bool | None,
    expected_subprocessors: list[str] | None,
) -> None:
    _setup(db, monkeypatch)
    argv = ["policy", "provider", "p", "--inference", "eu=eu", "--storage", "eu"]
    argv += ["--retention-days", "0", "--operator", "unknown", "--training", training]
    argv += ["--subprocessors", *subprocessors, "--statement", "s", "--yes"]
    assert main(argv) == 0
    statement, _ = capsys.readouterr().out.rsplit("policy event ", 1)
    payload = json.loads(statement)
    assert payload["training"] is expected_training
    assert payload["subprocessors"] == expected_subprocessors
    assert payload["operator"] is None
    assert payload["model_origin"] is None


@pytest.mark.db
def test_policy_provider_refuses_none_beside_a_name(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup(db, monkeypatch)
    argv = ["policy", "provider", "p", "--inference", "eu=eu", "--storage", "eu"]
    argv += ["--retention-days", "0", "--operator", "x", "--training", "no"]
    argv += ["--subprocessors", "none", "aws", "--statement", "s", "--yes"]
    assert main(argv) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err.count("\n") == 1
    assert _action_count(db) == 0


@pytest.mark.db
@pytest.mark.parametrize(("given", "expected"), [("unknown", None), ("us", "us")])
def test_policy_provider_reads_model_origin_unknown_as_unknown(
    db: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    given: str,
    expected: str | None,
) -> None:
    _setup(db, monkeypatch)
    argv = ["policy", "provider", "p", "--inference", "eu=eu", "--storage", "eu"]
    argv += ["--retention-days", "0", "--operator", "x", "--training", "no"]
    argv += ["--subprocessors", "none", "--model-origin", given, "--statement", "s", "--yes"]
    assert main(argv) == 0
    statement, _ = capsys.readouterr().out.rsplit("policy event ", 1)
    assert json.loads(statement)["model_origin"] == expected


def _declare_local(db: object, capsys: pytest.CaptureFixture[str]) -> None:
    argv = ["policy", "provider", "local", "--storage", "--retention-days", "0"]
    argv += ["--operator", "me", "--training", "no", "--subprocessors", "none"]
    argv += ["--local", "--statement", "s", "--yes"]
    assert main(argv) == 0
    capsys.readouterr()


def _all_actions(db: object) -> str:
    from sqlalchemy import Engine
    from sqlalchemy import text

    assert isinstance(db, Engine)
    with db.begin() as c:
        rows = c.execute(text("SELECT payload::text FROM event WHERE kind = 'action'")).scalars()
        return "\n".join(rows)


def _token_of(out: str) -> str:
    """The token of the one line that carries it; a prompt without a newline
    may stand in front of that line."""
    assert out.endswith("\nshown once; store it now\n")
    prefix = "client claude-code: token "
    (line,) = (line for line in out.splitlines() if prefix in line)
    return line.split(prefix, 1)[1]


@pytest.mark.db
def test_client_add_prints_the_token_once_and_stores_only_its_hash(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from previously.core.clients import token_hash

    _setup(db, monkeypatch)
    _declare_local(db, capsys)
    argv = ["client", "add", "claude-code", "--processor", "local", "--statement", "s", "--yes"]
    assert main(argv) == 0
    out, err = capsys.readouterr()
    token = _token_of(out)
    assert len(token) == 43
    assert token not in err
    assert out.count(token) == 1
    stored = _all_actions(db)
    assert token not in stored
    assert token_hash(token) in stored
    # The list shows the name, the processor and a date; never the hash, never the token.
    assert main(["client", "list"]) == 0
    listed = capsys.readouterr().out
    assert listed.startswith("claude-code\tlocal\t20")
    assert token_hash(token) not in listed
    assert token not in listed
    assert main(["policy", "show"]) == 0
    shown = capsys.readouterr().out
    assert token not in shown
    assert token_hash(token) not in shown


@pytest.mark.db
def test_client_add_for_an_existing_name_says_so_before_it_asks(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup(db, monkeypatch)
    _declare_local(db, capsys)
    argv = ["client", "add", "claude-code", "--processor", "local", "--statement", "s"]
    _answer(monkeypatch, "y\n")
    assert main(argv) == 0
    old = _token_of(capsys.readouterr().out)
    # The control: a first add says nothing about replacing.
    # An n replaces nothing.
    _answer(monkeypatch, "n\n")
    assert main(argv) == 1
    out, err = capsys.readouterr()
    assert "exists: this replaces it, and its token stops working" in err
    assert "nothing written" in err
    assert "token" not in out
    _answer(monkeypatch, "y\n")
    assert main(argv) == 0
    out, err = capsys.readouterr()
    assert "exists: this replaces it" in err
    assert _token_of(out) != old


@pytest.mark.db
def test_client_add_for_a_new_name_does_not_claim_a_replacement(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup(db, monkeypatch)
    _declare_local(db, capsys)
    argv = ["client", "add", "claude-code", "--processor", "local", "--statement", "s", "--yes"]
    assert main(argv) == 0
    assert "replaces" not in capsys.readouterr().err


@pytest.mark.db
def test_client_add_without_an_answer_writes_nothing(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup(db, monkeypatch)
    _declare_local(db, capsys)
    before = _action_count(db)
    _answer(monkeypatch, "")
    argv = ["client", "add", "claude-code", "--processor", "local", "--statement", "s"]
    assert main(argv) == 1
    out, err = capsys.readouterr()
    assert "token" not in out
    assert err == _NO_ANSWER + "nothing written\n"
    assert _action_count(db) == before

    # The same for `revoke`, the third command that asks.
    assert main([*argv, "--yes"]) == 0
    capsys.readouterr()
    _answer(monkeypatch, "")
    assert main(["client", "revoke", "claude-code", "--statement", "gone"]) == 1
    assert capsys.readouterr().err == _NO_ANSWER + "nothing written\n"
    assert _action_count(db) == before + 1


@pytest.mark.db
def test_client_add_for_an_undeclared_processor_is_refused_before_the_question(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup(db, monkeypatch)
    argv = ["client", "add", "claude-code", "--processor", "nowhere", "--statement", "s"]
    assert main(argv) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err.startswith('Error: the processor "nowhere" is not declared')
    assert _action_count(db) == 0


@pytest.mark.db
def test_client_revoke_lifts_the_client_and_list_is_empty_again(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup(db, monkeypatch)
    _declare_local(db, capsys)
    add = ["client", "add", "claude-code", "--processor", "local", "--statement", "s", "--yes"]
    assert main(add) == 0
    capsys.readouterr()
    assert main(["client", "revoke", "claude-code", "--statement", "left", "--yes"]) == 0
    assert capsys.readouterr().out.endswith("policy event 3\n")
    assert main(["client", "list"]) == 0
    out, err = capsys.readouterr()
    assert out == ""
    assert err == "no client exists\n"
    assert main(["client", "revoke", "claude-code", "--statement", "again", "--yes"]) == 2
    assert 'Error: no client "claude-code" exists' in capsys.readouterr().err


def test_the_help_of_client_names_what_it_does(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])
    assert "add, revoke and list MCP clients" in " ".join(capsys.readouterr().out.split())
    with pytest.raises(SystemExit):
        main(["client", "--help"])
    out = capsys.readouterr().out
    assert "add" in out and "revoke" in out and "list" in out


@pytest.mark.db
def test_client_add_prints_the_summary_then_the_two_lines_and_the_page_says_so(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from pathlib import Path

    _setup(db, monkeypatch)
    _declare_local(db, capsys)
    argv = ["client", "add", "a\tb", "--processor", "local", "--statement", "s", "--yes"]
    assert main(argv) == 0
    lines = capsys.readouterr().out.splitlines()
    # The tab of the name is escaped like in every other line, so the summary
    # stays two fields; the token line carries the same escaped name.
    assert lines[0] == "client a\\tb\tprocessor local"
    assert lines[1].startswith("client a\\tb: token ")
    assert lines[2] == "shown once; store it now"
    assert len(lines) == 3
    page = (Path(__file__).parent.parent / "docs/reference/cli.md").read_text(encoding="utf-8")
    assert "`client NAME` and `processor PROVIDER`, separated by a tab" in page
    assert "prints nothing after the two lines" in page


# --- mcp and serve --------------------------------------------------------------


def test_the_help_names_mcp_and_serve_with_their_sentences(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])
    out = " ".join(capsys.readouterr().out.split())
    assert "mcp serve MCP over stdio" in out
    assert "serve serve MCP over HTTP" in out


def test_mcp_without_its_client_ends_with_2_before_it_reads_anything(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # No DSN either: the client is named before anything connects.
    monkeypatch.delenv("PREVIOUSLY_MCP_CLIENT", raising=False)
    monkeypatch.delenv("PREVIOUSLY_DSN", raising=False)
    assert main(["mcp"]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err == "Error: PREVIOUSLY_MCP_CLIENT is not set: name the client this process serves\n"


@pytest.mark.db
def test_mcp_for_a_client_not_in_force_ends_with_2(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup(db, monkeypatch)
    _declare_local(db, capsys)
    argv = ["client", "add", "claude-code", "--processor", "local", "--statement", "s", "--yes"]
    assert main(argv) == 0
    assert main(["client", "revoke", "claude-code", "--statement", "gone", "--yes"]) == 0
    capsys.readouterr()
    for name in ("claude-code", "nobody"):
        monkeypatch.setenv("PREVIOUSLY_MCP_CLIENT", name)
        assert main(["mcp"]) == 2
        out, err = capsys.readouterr()
        assert out == ""
        assert err == (
            f'Error: no client "{name}" is in force; add it with previously client add\n'
        )


@pytest.mark.parametrize(
    "address",
    [
        "http",
        "127.0.0.1",
        "127.0.0.1:http",
        "127.0.0.1:0",
        "127.0.0.1:65536",
        "127.0.0.1:８７６５",
        "::1:8765",
        "[::1]",
        "[::1:8765",
        "[::g]:8765",
        ":8765",
        "a..b:8765",
        "tcp://10.43.0.5:8765",
    ],
)
def test_serve_with_an_address_of_another_form_ends_with_2(
    address: str, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PREVIOUSLY_MCP_ADDRESS", address)
    assert main(["serve"]) == 2
    assert capsys.readouterr().err == (
        "Error: PREVIOUSLY_MCP_ADDRESS is not host:port, "
        f"with an IPv6 host in brackets: {address!r}\n"
    )


@pytest.mark.parametrize("address", [None, "", "0.0.0.0:8765", "[::]:8765"])
def test_serve_reads_neither_the_port_kubernetes_sets_nor_the_old_host(
    address: str | None, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Service named `previously-mcp` sets `PREVIOUSLY_MCP_PORT` to
    `tcp://<cluster IP>:8765` in every pod of its namespace, and until
    2026-10-11 `serve` read it and refused to start. With the address unset,
    empty or set, it now goes on to the database; without a connection string
    that is where it stops, before it listens anywhere."""
    monkeypatch.setenv("PREVIOUSLY_MCP_PORT", "tcp://10.43.0.5:8765")
    monkeypatch.delenv("PREVIOUSLY_MCP_HOST", raising=False)
    monkeypatch.delenv("PREVIOUSLY_DSN", raising=False)
    if address is None:
        monkeypatch.delenv("PREVIOUSLY_MCP_ADDRESS", raising=False)
    else:
        monkeypatch.setenv("PREVIOUSLY_MCP_ADDRESS", address)
    assert main(["serve"]) == 2
    assert capsys.readouterr() == ("", "Error: PREVIOUSLY_DSN is not set\n")


def test_serve_says_that_the_host_setting_was_renamed(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without the hint, a deployment that still sets `PREVIOUSLY_MCP_HOST`
    to the address of its pod would listen on the loopback address inside its pod, and
    nothing would say why no probe reaches it. With the address set, the old
    name is left alone: the control."""
    monkeypatch.delenv("PREVIOUSLY_DSN", raising=False)
    monkeypatch.delenv("PREVIOUSLY_MCP_ADDRESS", raising=False)
    monkeypatch.setenv("PREVIOUSLY_MCP_HOST", "10.42.1.17")
    assert main(["serve"]) == 2
    assert capsys.readouterr() == (
        "",
        "Error: PREVIOUSLY_MCP_HOST is not read any more: "
        "set PREVIOUSLY_MCP_ADDRESS to host:port\n",
    )
    monkeypatch.setenv("PREVIOUSLY_MCP_ADDRESS", "0.0.0.0:8765")
    assert main(["serve"]) == 2
    assert capsys.readouterr() == ("", "Error: PREVIOUSLY_DSN is not set\n")


def _free_port(host: str) -> int:
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as probe:
        probe.bind((host, 0))
        return int(probe.getsockname()[1])


@pytest.mark.db
@pytest.mark.parametrize("host", ["127.0.0.1", "::1"])
def test_serve_listens_where_the_address_says_beside_the_variables_of_a_service(
    host: str, db: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`previously serve` as kup6s runs it: in a pod where the Service
    `previously-mcp` set its variables. The server starts, prints where it
    listens, and answers the readiness probe there.

    A process of its own, because the server runs until it is stopped and
    the test has to stop it from outside."""
    try:
        port = _free_port(host)
    except OSError:
        pytest.skip(f"{host} is not an address of this machine")
    where = f"[{host}]:{port}" if ":" in host else f"{host}:{port}"
    _setup(db, monkeypatch)
    environment = {
        **os.environ,
        "PREVIOUSLY_MCP_ADDRESS": where,
        "PREVIOUSLY_MCP_PORT": "tcp://10.43.0.5:8765",
        "PREVIOUSLY_MCP_SERVICE_HOST": "10.43.0.5",
        "PREVIOUSLY_MCP_PORT_8765_TCP_PORT": "8765",
    }
    environment.pop("PREVIOUSLY_MCP_HOST", None)
    server = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import sys; from previously.cli import main; sys.exit(main(['serve']))",
        ],
        env=environment,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert server.stderr is not None
        assert server.stderr.readline() == f"serving MCP over HTTP on http://{where}/mcp\n"
        deadline = time.monotonic() + 30
        while True:
            try:
                connection = http.client.HTTPConnection(host, port, timeout=5)
                connection.request("GET", "/healthz")
                response = connection.getresponse()
                break
            except ConnectionRefusedError:
                assert time.monotonic() < deadline, "the server never listened"
                time.sleep(0.1)
        assert (response.status, response.read()) == (200, b"ok")
        connection.close()
    finally:
        server.terminate()
        server.wait(timeout=30)
        assert server.stderr is not None
        server.stderr.close()


def _call_over_http(url: str, token: str, name: str, arguments: dict[str, object]) -> str:
    """The text of one tool call to a running `serve`, as a client sends it."""
    from mcp.client.client import Client
    from mcp.client.streamable_http import streamable_http_client
    from mcp.types import TextContent

    import anyio
    import httpx2

    async def call() -> str:
        headers = {"Authorization": f"Bearer {token}"}
        async with (
            httpx2.AsyncClient(headers=headers) as http,
            Client(streamable_http_client(url, http_client=http)) as session,
        ):
            result = await session.call_tool(name, arguments)
        (block,) = result.content
        assert isinstance(block, TextContent)
        return block.text

    return anyio.run(call)


@pytest.mark.db
@pytest.mark.parametrize("key", [None, "k" * 32])
def test_serve_passes_the_confirm_key_on_to_the_writing_tools(
    key: str | None,
    db: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With the key set, a writing call reaches the write path, which names
    an id that is no proposal; without it, the same call is not configured,
    the control that the answer depends on the key."""
    port = _free_port("127.0.0.1")
    _setup(db, monkeypatch)
    _declare_local(db, capsys)
    argv = ["client", "add", "claude-code", "--processor", "local", "--statement", "s", "--yes"]
    assert main(argv) == 0
    token = _token_of(capsys.readouterr().out)
    environment = {**os.environ, "PREVIOUSLY_MCP_ADDRESS": f"127.0.0.1:{port}"}
    environment.pop("PREVIOUSLY_MCP_CONFIRM_KEY", None)
    if key is not None:
        environment["PREVIOUSLY_MCP_CONFIRM_KEY"] = key
    server = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import sys; from previously.cli import main; sys.exit(main(['serve']))",
        ],
        env=environment,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert server.stderr is not None
        server.stderr.readline()
        deadline = time.monotonic() + 30
        while True:
            try:
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                connection.request("GET", "/healthz")
                connection.getresponse().read()
                connection.close()
                break
            except ConnectionRefusedError:
                assert time.monotonic() < deadline, "the server never listened"
                time.sleep(0.1)
        url = f"http://127.0.0.1:{port}/mcp"
        text = _call_over_http(url, token, "write_reject", {"proposal": 999_999})
    finally:
        server.terminate()
        server.wait(timeout=30)
        assert server.stderr is not None
        server.stderr.close()
    if key is None:
        assert text == "Error: writing is not configured on this server"
    else:
        assert text == "Error: event 999999 is not a proposal this client can answer"
    assert "k" * 32 not in _all_actions(db)


# --- assertions: assert, approve, reject and the lists ----------------------------

_ANNA = "anna@huber.example"
_WHAT = "send the offer for the roof"
_THE_OFFER = f"address:{_ANNA}"
_ASSERT_AT = datetime(2026, 11, 1, 12, 0, 0, tzinfo=UTC)


def _assertion_mail(external_id: str, *identities: tuple[str, str | None]) -> RawEvent:
    return RawEvent(
        source="email",
        external_id=external_id,
        occurred_at=datetime(2026, 10, 30, 9, 0, 0, tzinfo=UTC),
        evidence=Evidence.VERBATIM,
        units=(RawUnit(1, "One."), RawUnit(2, "Two."), RawUnit(3, "Three.")),
        payload={"text": "One. Two. Three."},
        channel_identities=tuple(
            ChannelIdentity("email", "from", address, name) for address, name in identities
        ),
    )


def _assertion_log(db: object, monkeypatch: pytest.MonkeyPatch, mails: int = 2) -> PostgresStorage:
    """A log with `mails` observations, ids 1 to `mails`; the first one is
    from Anna Huber."""
    _setup(db, monkeypatch)
    from sqlalchemy import Engine

    assert isinstance(db, Engine)
    storage = PostgresStorage(db)
    events = [_assertion_mail("m1", (_ANNA, "Anna Huber"))]
    events += [_assertion_mail(f"m{n}") for n in range(2, mails + 1)]
    append(storage, events, recorded_at=_ASSERT_AT)
    return storage


def _debt(
    *sources: Source,
    responsibility: str = OPEN,
    author: str = model_author("claude-code"),
    subject: int | None = None,
    what: str = _WHAT,
    due: date | None = date(2026, 11, 30),
    state: str = "open",
    debtor: str = "own",
    creditor: str = _THE_OFFER,
) -> AssertionStatement:
    return AssertionStatement(
        OBLIGATION,
        author,
        responsibility,
        sources or (Source(1, None),),
        None,
        None,
        subject,
        None,
        None,
        ObligationBody(debtor, creditor, what, due, state),
    )


def _propose(storage: PostgresStorage, *statements: AssertionStatement) -> tuple[int, ...]:
    return write_statements(storage, storage, statements, recorded_at=_ASSERT_AT)


def _standing(db: object) -> list[tuple[int, dict[str, object]]]:
    """Every assertion payload in the log, in chain order."""
    from sqlalchemy import Engine
    from sqlalchemy import text

    assert isinstance(db, Engine)
    with db.begin() as c:
        rows = c.execute(
            text("SELECT id, payload FROM event WHERE kind = 'assertion' ORDER BY id")
        ).all()
    return [(row[0], row[1]) for row in rows]


def _assert_obligation(*extra: str) -> list[str]:
    return [
        "assert",
        "obligation",
        "--debtor",
        "own",
        "--creditor",
        _THE_OFFER,
        "--what",
        _WHAT,
        "--due",
        "2026-11-30",
        "--source",
        "1:1,2",
        *extra,
    ]


_FIRST_PREVIEW = f"""{{
  "approves": null,
  "assertion": "obligation",
  "author": "human:operator",
  "creditor": "address:{_ANNA}",
  "debtor": "own",
  "due": "2026-11-30",
  "handle": null,
  "reason": null,
  "responsibility": "direct",
  "sources": [
    {{
      "event": 1,
      "units": [
        1,
        2
      ]
    }}
  ],
  "state": "open",
  "subject": null,
  "what": "{_WHAT}"
}}
"""


@pytest.mark.parametrize(
    ("name", "sentence"),
    [
        ("assert", "state an obligation or a decision"),
        ("approve", "make proposals your own"),
        ("reject", "reject a proposal"),
        ("obligations", "list what is owed"),
        ("obligation", "show one obligation"),
        ("decisions", "list what was decided"),
        ("decision", "show one decision"),
    ],
)
def test_the_assertion_commands_carry_the_contractual_help(name: str, sentence: str) -> None:
    assert [(c.name, c.help) for c in COMMANDS if c.name == name] == [(name, sentence)]


@pytest.mark.db
def test_assert_obligation_shows_the_payload_asks_and_writes_after_a_yes(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _assertion_log(db, monkeypatch)
    _answer(monkeypatch, "y\n")
    assert main(_assert_obligation()) == 0
    captured = capsys.readouterr()
    assert captured.out == _FIRST_PREVIEW + "write? [y/N] assertion 3\n"
    assert captured.err == ""
    ((event_id, payload),) = _standing(db)
    assert event_id == 3
    assert payload["author"] == "human:operator"
    assert payload["responsibility"] == "direct"


@pytest.mark.db
def test_assert_obligation_with_yes_writes_without_asking(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _assertion_log(db, monkeypatch)
    assert main(_assert_obligation("--yes")) == 0
    assert capsys.readouterr().out == _FIRST_PREVIEW + "assertion 3\n"


@pytest.mark.db
def test_assert_without_an_answer_writes_nothing(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review focus 5 of the 2026-10-12 plan, the last part, and its two
    controls: an `n` and an input that ends write nothing and exit 1."""
    _assertion_log(db, monkeypatch)
    _answer(monkeypatch, "n\n")
    assert main(_assert_obligation()) == 1
    captured = capsys.readouterr()
    assert captured.out == _FIRST_PREVIEW + "write? [y/N] "
    assert captured.err == "nothing written\n"
    _answer(monkeypatch, "")
    assert main(_assert_obligation()) == 1
    assert capsys.readouterr().err == _NO_ANSWER + "nothing written\n"
    assert _standing(db) == []


@pytest.mark.db
@pytest.mark.parametrize("day", ["2026-02-30", "30.11.2026", "", "2026-11-3", "20261130"])
def test_a_due_that_is_not_a_date_is_refused_before_the_question(
    day: str, db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review focus 5 of the 2026-10-12 plan: one sentence, exit 2, no
    payload shown, no question asked, nothing written."""
    _assertion_log(db, monkeypatch)
    argv = _assert_obligation()
    argv[argv.index("--due") + 1] = day
    assert main(argv) == 2
    assert capsys.readouterr() == ("", "Error: --due is not a date written YYYY-MM-DD\n")
    assert _standing(db) == []


@pytest.mark.db
@pytest.mark.parametrize("day", ["2026-02-30", "30.11.2026", ""])
def test_an_on_that_is_not_a_date_is_refused_before_the_question(
    day: str, db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _assertion_log(db, monkeypatch)
    argv = ["assert", "decision", "--what", "use slate", "--by", "own", "--on", day]
    assert main([*argv, "--source", "1"]) == 2
    assert capsys.readouterr() == ("", "Error: --on is not a date written YYYY-MM-DD\n")
    assert _standing(db) == []


@pytest.mark.db
def test_a_due_in_the_past_is_written_and_the_obligation_is_overdue_at_once(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review focus 5, the other half: yesterday is allowed. The control is
    the obligation due tomorrow, which is not overdue."""
    _assertion_log(db, monkeypatch)
    today = datetime.now(UTC).date()
    yesterday, tomorrow = today - timedelta(days=1), today + timedelta(days=1)
    for day in (yesterday, tomorrow):
        argv = _assert_obligation("--yes")
        argv[argv.index("--due") + 1] = day.isoformat()
        assert main(argv) == 0
    capsys.readouterr()
    assert main(["obligations"]) == 0
    assert capsys.readouterr().out == (
        f"3\topen overdue\t{yesterday}\town -> {_THE_OFFER}\t{_WHAT}\t1 version\t0 proposals\n"
        f"4\topen\t{tomorrow}\town -> {_THE_OFFER}\t{_WHAT}\t1 version\t0 proposals\n"
    )
    assert main(["obligations", "--overdue"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        f"3\topen overdue\t{yesterday}\town -> {_THE_OFFER}\t{_WHAT}\t1 version\t0 proposals"
    ]


@pytest.mark.db
@pytest.mark.parametrize(
    ("source", "sentence"),
    [
        ("", "--source is not EVENT or EVENT:SEQ,SEQ: ''"),
        ("abc", "--source is not EVENT or EVENT:SEQ,SEQ: 'abc'"),
        ("1:", "--source is not EVENT or EVENT:SEQ,SEQ: '1:'"),
        ("1:a", "--source is not EVENT or EVENT:SEQ,SEQ: '1:a'"),
        ("1:1,", "--source is not EVENT or EVENT:SEQ,SEQ: '1:1,'"),
        ("1:1,,2", "--source is not EVENT or EVENT:SEQ,SEQ: '1:1,,2'"),
        ("1 :1", "--source is not EVENT or EVENT:SEQ,SEQ: '1 :1'"),
        ("-1", "--source is not EVENT or EVENT:SEQ,SEQ: '-1'"),
        ("1:2,1", "the units of a source are not ascending without duplicates"),
        ("0", "a source names an event that is not a whole number of at least 1"),
    ],
)
def test_a_malformed_source_is_refused_before_the_question(
    source: str,
    sentence: str,
    db: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _assertion_log(db, monkeypatch)
    argv = _assert_obligation()
    argv[argv.index("--source") + 1] = source
    assert main(argv) == 2
    assert capsys.readouterr() == ("", f"Error: {sentence}\n")
    assert _standing(db) == []


@pytest.mark.db
def test_a_source_that_is_the_whole_event_has_null_units(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _assertion_log(db, monkeypatch)
    argv = _assert_obligation("--source", "2", "--yes")
    argv[argv.index("1:1,2")] = "1"
    assert main(argv) == 0
    ((_, payload),) = _standing(db)
    assert payload["sources"] == [{"event": 1, "units": None}, {"event": 2, "units": None}]


@pytest.mark.db
def test_a_reference_that_is_none_is_refused_before_the_question(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _assertion_log(db, monkeypatch)
    argv = _assert_obligation()
    argv[argv.index("--debtor") + 1] = "Anna"
    assert main(argv) == 2
    assert capsys.readouterr() == (
        "",
        "Error: --debtor: the reference has no known prefix: use own, circle:, address: or name:\n",
    )
    assert _standing(db) == []


@pytest.mark.db
def test_what_is_missing_without_a_subject_is_named_before_the_question(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _assertion_log(db, monkeypatch)
    assert main(["assert", "obligation", "--debtor", "own"]) == 2
    assert capsys.readouterr() == (
        "",
        "Error: an obligation needs --creditor, --what and --source "
        "unless --subject names the one to change\n",
    )
    assert main(["assert", "decision", "--what", "x"]) == 2
    assert capsys.readouterr() == (
        "",
        "Error: a decision needs --by, --on and --source "
        "unless --subject names the one to change\n",
    )


@pytest.mark.db
def test_a_source_that_is_not_in_the_log_is_refused_with_the_sentence_of_the_write_path(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _assertion_log(db, monkeypatch)
    argv = _assert_obligation("--yes")
    argv[argv.index("1:1,2")] = "99"
    assert main(argv) == 2
    assert capsys.readouterr().err == "Error: there is no event 99 to rest on\n"
    assert _standing(db) == []


@pytest.mark.db
def test_a_subject_fills_the_fields_that_are_left_out_and_shows_what_changed(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The brief's mutation: with `--subject` not filling, the second call
    fails for lack of `--debtor`, and this test goes red. The control is the
    refusal above, which says the fields are needed without a subject."""
    _assertion_log(db, monkeypatch)
    assert main(_assert_obligation("--yes")) == 0
    capsys.readouterr()
    argv = ["assert", "obligation", "--subject", "3", "--state", "fulfilled", "--reason", "done"]
    assert main([*argv, "--yes"]) == 0
    out = capsys.readouterr().out
    assert out == (
        _FIRST_PREVIEW.replace('"reason": null', '"reason": "done"')
        .replace('"state": "open"', '"state": "fulfilled"')
        .replace('"subject": null', '"subject": 3')
        + "change\tstate\topen\tfulfilled\n"
        + "change\treason\t(none)\tdone\n"
        + "assertion 4\n"
    )
    ((_, first), (_, second)) = _standing(db)
    assert second["debtor"] == first["debtor"] == "own"
    assert second["sources"] == first["sources"]
    assert second["subject"] == 3


@pytest.mark.db
def test_a_subject_that_names_no_obligation_is_refused_before_the_question(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _assertion_log(db, monkeypatch)
    assert main(["assert", "obligation", "--subject", "1", "--state", "cancelled"]) == 2
    assert capsys.readouterr() == ("", "Error: --subject 1 names no obligation that stands\n")
    assert main(["assert", "decision", "--subject", "1", "--what", "x"]) == 2
    assert capsys.readouterr() == ("", "Error: --subject 1 names no decision that stands\n")


@pytest.mark.db
def test_a_subject_whose_winner_is_a_proposal_fills_from_it_and_writes_a_direct_version(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = _assertion_log(db, monkeypatch)
    (proposal_id,) = _propose(storage, _debt(due=date(2026, 12, 1)))
    assert (
        main(["assert", "obligation", "--subject", str(proposal_id), "--what", "x", "--yes"]) == 0
    )
    (_, proposed), (_, written) = _standing(db)
    assert written["responsibility"] == "direct"
    assert written["author"] == "human:operator"
    assert written["approves"] is None
    assert written["due"] == proposed["due"] == "2026-12-01"
    assert written["what"] == "x"


@pytest.mark.db
def test_a_name_that_matches_a_sender_in_a_source_draws_a_hint_and_blocks_nothing(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The hint goes to standard error before the question, case-insensitive on
    the display name. Controls: a name that matches nobody, and `address:`,
    draw none."""
    _assertion_log(db, monkeypatch)
    argv = _assert_obligation("--yes")
    argv[argv.index("--creditor") + 1] = "name:huber"
    _answer(monkeypatch, "")
    assert main(argv) == 0
    captured = capsys.readouterr()
    assert (
        captured.err
        == f"hint: {_ANNA} appears in the sources; address: is a reference that holds\n"
    )
    assert captured.out == _FIRST_PREVIEW.replace(_THE_OFFER, "name:huber") + "assertion 3\n"
    for creditor in ("name:meier", _THE_OFFER):
        argv[argv.index("--creditor") + 1] = creditor
        assert main(argv) == 0
        assert capsys.readouterr().err == ""


@pytest.mark.db
def test_the_hint_comes_before_the_question(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _assertion_log(db, monkeypatch)
    argv = _assert_obligation()
    argv[argv.index("--creditor") + 1] = "name:ANNA"
    _answer(monkeypatch, "n\n")
    assert main(argv) == 1
    assert capsys.readouterr().err == (
        f"hint: {_ANNA} appears in the sources; address: is a reference that holds\n"
        "nothing written\n"
    )


@pytest.mark.db
def test_assert_decision_writes_a_decision_and_the_list_shows_it(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _assertion_log(db, monkeypatch)
    argv = ["assert", "decision", "--what", "use slate", "--by", "circle:huber", "--by", "own"]
    assert main([*argv, "--on", "2026-10-30", "--source", "1", "--source", "2:3", "--yes"]) == 0
    assert capsys.readouterr().out.endswith("assertion 3\n")
    ((_, payload),) = _standing(db)
    assert payload["by"] == ["circle:huber", "own"]
    assert payload["replaces"] is None
    assert main(["decisions"]) == 0
    assert capsys.readouterr().out == (
        "3\tvalid\t2026-10-30\tcircle:huber, own\tuse slate\t1 version\t0 proposals\n"
    )


@pytest.mark.db
def test_a_decision_that_is_replaced_says_so_in_the_list_and_in_its_page(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _assertion_log(db, monkeypatch)
    base = ["assert", "decision", "--by", "own", "--on", "2026-10-30", "--source", "1", "--yes"]
    assert main([*base, "--what", "use slate"]) == 0
    assert main([*base, "--what", "use tiles", "--replaces", "3"]) == 0
    capsys.readouterr()
    assert main(["decisions"]) == 0
    assert capsys.readouterr().out == (
        "3\tvalid replaced by 4\t2026-10-30\town\tuse slate\t1 version\t0 proposals\n"
        "4\tvalid\t2026-10-30\town\tuse tiles\t1 version\t0 proposals\n"
    )
    assert main(["decisions", "--state", "revoked"]) == 0
    assert capsys.readouterr().out == ""
    assert main(["decision", "3"]) == 0
    assert capsys.readouterr().out == (
        "decision 3\n"
        "version\t3\n"
        "state\tvalid\n"
        "replaced by\t4\n"
        "on\t2026-10-30\n"
        "by\town\n"
        "what\tuse slate\n"
        "replaces\t(none)\n"
        "sources\tevent 1\n"
        "reason\t(none)\n"
        "author\thuman:operator\n"
        "responsibility\tdirect\n"
        "versions\t1\n"
        "proposals\t0\n"
    )


@pytest.mark.db
def test_a_text_the_log_cannot_hold_is_refused_before_the_question(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ruling F-19 of the 2026-10-12 assertions plan: the check before the
    question runs the canonical check the write runs, so nobody confirms
    what the write then refuses. A lone surrogate reaches `--what` the way
    finding W-1 describes; the same command without it, answered `n`, is
    the control that the question comes otherwise."""
    _assertion_log(db, monkeypatch)
    _answer(monkeypatch, "n\n")

    assert main(_assert_obligation("--what", "send \ud800 the offer")) == 2
    assert capsys.readouterr() == (
        "",
        "Error: a statement cannot be written: $.what: string not representable as UTF-8 "
        "(surrogates not allowed) — a lone UTF-16 surrogate, for instance\n",
    )
    assert main(_assert_obligation()) == 1
    assert "write? [y/N]" in capsys.readouterr().out


@pytest.mark.db
def test_approve_makes_a_list_of_proposals_the_operators_own(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = _assertion_log(db, monkeypatch)
    first, second = _propose(storage, _debt(what="one"), _debt(what="two", due=None))
    assert main(["approve", str(first), str(second), "--reason", "read it", "--yes"]) == 0
    out = capsys.readouterr().out
    assert out.endswith("assertion 5\nassertion 6\n")
    written = dict(_standing(db))
    for new, proposal_id, what in ((5, first, "one"), (6, second, "two")):
        payload = written[new]
        assert payload["approves"] == payload["subject"] == proposal_id
        assert payload["responsibility"] == "direct"
        assert payload["author"] == "model:claude-code"
        assert payload["what"] == what
        assert payload["reason"] == "read it"
        assert payload["sources"] == written[proposal_id]["sources"]
    assert main(["obligations"]) == 0
    assert capsys.readouterr().out == (
        f"{first}\topen (made its own by the operator)\t2026-11-30\town -> {_THE_OFFER}\tone"
        "\t2 versions\t0 proposals\n"
        f"{second}\topen (made its own by the operator)\t-\town -> {_THE_OFFER}\ttwo"
        "\t2 versions\t0 proposals\n"
    )
    # The page of an approval says what a direct version by a model means; the
    # control is the proposal's page, which has no such row.
    note = f"made its own by the operator (approval of {first}), formulated by model:claude-code"
    assert main(["obligation", str(first)]) == 0
    assert f"responsibility\tdirect\nmeaning\t{note}\nversions\t2\n" in capsys.readouterr().out


@pytest.mark.db
def test_approve_asks_and_an_n_writes_nothing(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = _assertion_log(db, monkeypatch)
    (proposal_id,) = _propose(storage, _debt())
    _answer(monkeypatch, "n\n")
    assert main(["approve", str(proposal_id)]) == 1
    captured = capsys.readouterr()
    assert "write? [y/N]" in captured.out
    assert captured.err == "nothing written\n"
    assert len(_standing(db)) == 1


@pytest.mark.db
def test_approving_what_is_answered_already_or_is_no_proposal_is_refused_before_the_question(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review focus 2 of the 2026-10-12 plan, on the command line. The
    control is the proposal nobody answered, approved at the end."""
    storage = _assertion_log(db, monkeypatch)
    approved, rejected, open_one = _propose(
        storage, _debt(what="a"), _debt(what="b"), _debt(what="c")
    )
    assert main(["approve", str(approved), "--yes"]) == 0
    assert main(["reject", str(rejected), "--yes"]) == 0
    direct = approved + 3
    capsys.readouterr()
    count = len(_standing(db))
    for argv, sentence in (
        (["approve", str(approved)], f"the proposal {approved} is already approved"),
        (["approve", str(rejected)], f"the proposal {rejected} is already rejected"),
        (["approve", str(direct)], f"the version {direct} is no proposal: it is direct"),
        (["approve", "1"], "event 1 is no proposal that stands"),
        (["approve", "99"], "event 99 is no proposal that stands"),
        (["approve", str(open_one), "99"], "event 99 is no proposal that stands"),
    ):
        assert main(argv) == 2
        assert capsys.readouterr() == ("", f"Error: {sentence}\n")
        assert len(_standing(db)) == count
    assert main(["approve", str(open_one), "--yes"]) == 0


@pytest.mark.db
def test_approving_a_proposal_a_later_direct_version_overtook_is_refused_before_the_question(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ruling F-17 of the 2026-10-12 assertions plan on the command line;
    rejecting the same proposal is the control."""
    storage = _assertion_log(db, monkeypatch)
    (owned,) = _propose(storage, _debt(responsibility=DIRECT, author=OPERATOR))
    (stale,) = _propose(storage, _debt(subject=owned, what="later"))
    (newer,) = _propose(storage, _debt(responsibility=DIRECT, author=OPERATOR, subject=owned))
    count = len(_standing(db))

    assert main(["approve", str(stale)]) == 2
    assert capsys.readouterr() == (
        "",
        f"Error: the proposal {stale} is overtaken: the direct version {newer} came after it\n",
    )
    assert len(_standing(db)) == count
    assert main(["reject", str(stale), "--yes"]) == 0


@pytest.mark.db
def test_reject_writes_a_rejection_with_the_sources_of_the_proposal_and_a_reason(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = _assertion_log(db, monkeypatch)
    (proposal_id,) = _propose(storage, _debt(Source(2, (1,)), Source(1, None)))
    assert main(["reject", str(proposal_id), "--reason", "not what was said", "--yes"]) == 0
    out = capsys.readouterr().out
    assert out == (
        "{\n"
        '  "assertion": "rejection",\n'
        '  "author": "human:operator",\n'
        '  "handle": null,\n'
        f'  "of": {proposal_id},\n'
        '  "reason": "not what was said",\n'
        '  "responsibility": "direct",\n'
        '  "sources": [\n'
        "    {\n"
        '      "event": 2,\n'
        '      "units": [\n'
        "        1\n"
        "      ]\n"
        "    },\n"
        "    {\n"
        '      "event": 1,\n'
        '      "units": null\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "assertion 4\n"
    )
    assert main(["obligations"]) == 0
    assert capsys.readouterr().out == ""
    assert main(["obligations", "--proposals"]) == 0
    assert capsys.readouterr().out == ""


@pytest.mark.db
def test_reject_asks_first_and_refuses_a_proposal_that_is_not_open(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = _assertion_log(db, monkeypatch)
    (proposal_id,) = _propose(storage, _debt())
    _answer(monkeypatch, "n\n")
    assert main(["reject", str(proposal_id)]) == 1
    assert capsys.readouterr().err == "nothing written\n"
    assert main(["reject", str(proposal_id), "--yes"]) == 0
    capsys.readouterr()
    assert main(["reject", str(proposal_id), "--yes"]) == 2
    assert capsys.readouterr().err == f"Error: the proposal {proposal_id} is already rejected\n"
    assert main(["reject", "1", "--yes"]) == 2
    assert capsys.readouterr().err == "Error: event 1 is no proposal that stands\n"


@pytest.mark.db
def test_a_list_shows_proposals_as_proposals_and_only_when_asked(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The brief's mutation: with a proposal shown as a valid entry, the
    plain list holds `5` and this test goes red. The control is `3`, which
    stands direct and stays in both lists."""
    storage = _assertion_log(db, monkeypatch)
    assert main(_assert_obligation("--yes")) == 0  # 3, direct
    (alone,) = _propose(storage, _debt(what="proposed alone"))  # 4
    (pending,) = _propose(storage, _debt(what="newer", subject=3, due=date(2026, 12, 24)))  # 5
    capsys.readouterr()
    assert main(["obligations"]) == 0
    assert capsys.readouterr().out == (
        f"3\topen\t2026-11-30\town -> {_THE_OFFER}\t{_WHAT}\t2 versions\t1 proposal\n"
    )
    assert main(["obligations", "--proposals"]) == 0
    assert capsys.readouterr().out == (
        f"3\topen\t2026-11-30\town -> {_THE_OFFER}\t{_WHAT}\t2 versions\t1 proposal\n"
        f"{alone}\tproposed open\t2026-11-30\town -> {_THE_OFFER}\tproposed alone"
        "\t1 version\t0 proposals\n"
    )
    assert pending == 5


@pytest.mark.db
def test_the_lists_filter_by_debtor_creditor_and_state(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _assertion_log(db, monkeypatch)
    plain = ["--source", "1", "--yes"]
    rows = (
        ("own", _THE_OFFER, "a", "open"),
        ("name:Hosting Company", "own", "b", "open"),
        ("circle:huber", "name:Anna", "c", "fulfilled"),
    )
    for debtor, creditor, what, state in rows:
        argv = ["assert", "obligation", "--debtor", debtor, "--creditor", creditor]
        assert main([*argv, "--what", what, "--state", state, *plain]) == 0
    capsys.readouterr()

    def listed(*argv: str) -> list[str]:
        assert main(["obligations", *argv]) == 0
        return [line.split("\t")[4] for line in capsys.readouterr().out.splitlines()]

    assert listed() == ["a", "b", "c"]
    assert listed("--owed-by", "own") == ["a"]
    assert listed("--owed-to", "own") == ["b"]
    assert listed("--owed-by", "circle:huber") == ["c"]
    assert listed("--owed-by", "name:hosting") == ["b"]  # a name is searched, case-insensitive
    assert listed("--owed-to", "name:anna") == ["c"]
    assert listed("--owed-to", f"address:{_ANNA}") == ["a"]
    assert listed("--state", "fulfilled") == ["c"]
    assert listed("--state", "open", "--owed-by", "own") == ["a"]
    assert main(["obligations", "--owed-by", "Anna"]) == 2
    assert (
        capsys.readouterr().err == "Error: --owed-by: the reference has no known prefix: "
        "use own, circle:, address: or name:\n"
    )


@pytest.mark.db
def test_the_circle_filter_finds_a_named_circle_and_a_source_of_the_circle(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--circle huber` finds the obligation whose creditor is `circle:huber`,
    the one that rests on a mail of Anna Huber (a member), and the one whose
    creditor is her address. The control is the obligation that does none of
    this."""
    _assertion_log(db, monkeypatch, mails=3)
    for argv in (
        ["policy", "circle", "huber", "--statement", "s", "--yes"],
        ["policy", "member", "huber", _ANNA, "--statement", "s", "--yes"],
    ):
        assert main(argv) == 0
    named = ["--debtor", "own", "--creditor", "circle:huber", "--source", "2"]
    from_mail = ["--debtor", "own", "--creditor", "name:somebody", "--source", "1"]
    by_address = ["--debtor", "own", "--creditor", _THE_OFFER, "--source", "3"]
    other = ["--debtor", "own", "--creditor", "circle:bauer", "--source", "3"]
    for what, rest in (
        ("named", named),
        ("mail", from_mail),
        ("address", by_address),
        ("other", other),
    ):
        assert main(["assert", "obligation", "--what", what, *rest, "--yes"]) == 0
    capsys.readouterr()
    assert main(["obligations", "--circle", "huber"]) == 0
    assert [line.split("\t")[4] for line in capsys.readouterr().out.splitlines()] == [
        "named",
        "mail",
        "address",
    ]
    assert main(["obligations", "--circle", "bauer"]) == 0
    assert [line.split("\t")[4] for line in capsys.readouterr().out.splitlines()] == ["other"]
    assert main(["obligations", "--circle", "nobody"]) == 0
    assert capsys.readouterr().out == ""
    assert main(["decisions", "--circle", "huber"]) == 0
    assert capsys.readouterr().out == ""


@pytest.mark.db
def test_a_field_from_outside_is_escaped_in_the_lists(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _assertion_log(db, monkeypatch)
    argv = ["assert", "obligation", "--debtor", "own", "--creditor", "name:Anna", "--source", "1"]
    assert main([*argv, "--what", "two\nli\tnes\\", "--yes"]) == 0
    capsys.readouterr()
    assert main(["obligations"]) == 0
    assert capsys.readouterr().out == (
        "3\topen\t-\town -> name:Anna\ttwo\\nli\\tnes\\\\\t1 version\t0 proposals\n"
    )


@pytest.mark.db
def test_one_obligation_shows_its_state_and_its_pending_proposals(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = _assertion_log(db, monkeypatch)
    today = datetime.now(UTC).date()
    argv = _assert_obligation("--yes")
    argv[argv.index("--due") + 1] = (today - timedelta(days=2)).isoformat()
    assert main(argv) == 0
    (pending,) = _propose(
        storage, _debt(subject=3, due=date(2027, 1, 15), what="send it twice", state="fulfilled")
    )
    capsys.readouterr()
    assert main(["obligation", "3"]) == 0
    assert capsys.readouterr().out == (
        "obligation 3\n"
        "version\t3\n"
        "state\topen\n"
        "overdue\tyes\n"
        f"due\t{today - timedelta(days=2)}\n"
        "debtor\town\n"
        f"creditor\t{_THE_OFFER}\n"
        f"what\t{_WHAT}\n"
        "sources\tevent 1 units 1, 2\n"
        "reason\t(none)\n"
        "author\thuman:operator\n"
        "responsibility\tdirect\n"
        "versions\t2\n"
        "proposals\t1\n"
        f"proposal\t{pending}\tmodel:claude-code\twhat\t{_WHAT}\tsend it twice\n"
        f"proposal\t{pending}\tmodel:claude-code\tdue\t{today - timedelta(days=2)}\t2027-01-15\n"
        f"proposal\t{pending}\tmodel:claude-code\tstate\topen\tfulfilled\n"
        f"proposal\t{pending}\tmodel:claude-code\tsources\tevent 1 units 1, 2\tevent 1\n"
    )


@pytest.mark.db
def test_one_obligation_that_stands_as_a_proposal_says_so(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = _assertion_log(db, monkeypatch)
    (proposal_id,) = _propose(storage, _debt())
    assert main(["obligation", str(proposal_id)]) == 0
    out = capsys.readouterr().out
    assert out.startswith(f"obligation {proposal_id} (proposal)\n")
    assert "responsibility\topen\n" in out


@pytest.mark.db
def test_a_missing_entry_is_exit_1_and_a_sentence(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = _assertion_log(db, monkeypatch)
    _propose(storage, _debt())
    assert main(["obligation", "99"]) == 1
    assert capsys.readouterr() == ("", "no obligation stands under event 99\n")
    assert main(["decision", "3"]) == 1
    assert capsys.readouterr() == ("", "no decision stands under event 3\n")


@pytest.mark.db
def test_an_entry_whose_versions_are_all_erased_says_it_is_erased(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ruling F-18 of the 2026-10-12 assertions plan: an id an erasure took
    says so, whatever kind is asked for, since the kind went with the
    payload; the lists leave it out. The entry beside it, whose first version
    alone is erased, still stands under its id and is the control."""
    storage = _assertion_log(db, monkeypatch)
    gone, kept = _propose(
        storage,
        _debt(responsibility=DIRECT, author=OPERATOR),
        _debt(responsibility=DIRECT, author=OPERATOR, what="kept"),
    )
    (later,) = _propose(storage, _debt(responsibility=DIRECT, author=OPERATOR, subject=gone))
    _propose(storage, _debt(responsibility=DIRECT, author=OPERATOR, subject=kept))
    for erased in (gone, later, kept):
        redact_event(storage, storage, erased, reason="r", recorded_at=datetime.now(UTC))
    for argv in (["obligation", str(gone)], ["decision", str(gone)], ["obligation", str(later)]):
        assert main([*argv]) == 1
        assert capsys.readouterr() == ("", f"assertion {argv[1]} is erased\n")
    assert main(["obligation", str(gone), "--history"]) == 1
    assert capsys.readouterr().err == f"assertion {gone} is erased\n"
    assert main(["obligations"]) == 0
    assert capsys.readouterr().out.split("\t")[0] == str(kept)
    assert main(["obligation", str(kept)]) == 0
    assert main(["obligation", "99"]) == 1
    assert capsys.readouterr().err == "no obligation stands under event 99\n"


@pytest.mark.db
def test_the_history_lists_every_version_with_the_difference_and_the_rejections(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Versions in chain order, each against the one standing before it, and
    a rejection among them with what it rejects. The two events the command
    line wrote carry the time of the run, which the test replaces by `NOW`."""
    storage = _assertion_log(db, monkeypatch)
    (first,) = _propose(
        storage,
        _debt(Source(1, (1, 2)), responsibility=DIRECT, author=OPERATOR),
    )
    (rejected,) = _propose(storage, _debt(subject=first, what="wrong"))  # 4
    (approved,) = _propose(storage, _debt(subject=first, due=date(2026, 12, 1)))  # 5
    assert main(["reject", str(rejected), "--reason", "not said", "--yes"]) == 0  # 6
    assert main(["approve", str(approved), "--yes"]) == 0  # 7
    capsys.readouterr()
    assert main(["obligation", str(first), "--history"]) == 0
    out = re.sub(r"(?m)^(rejection\t6\t|version\t7\t)\S+", r"\1NOW", capsys.readouterr().out)
    stamp = "2026-11-01T12:00:00.000000Z"
    assert out == (
        "obligation 3: 4 versions\n"
        f"version\t3\t{stamp}\tdirect\thuman:operator\n"
        "sources\tevent 1 units 1, 2\n"
        "reason\t(none)\n"
        "set\tstate\topen\n"
        "set\tdue\t2026-11-30\n"
        "set\tdebtor\town\n"
        f"set\tcreditor\t{_THE_OFFER}\n"
        f"set\twhat\t{_WHAT}\n"
        f"version\t4\t{stamp}\topen\tmodel:claude-code\trejected\n"
        "sources\tevent 1\n"
        "reason\t(none)\n"
        f"change\twhat\t{_WHAT}\twrong\n"
        "change\tsources\tevent 1 units 1, 2\tevent 1\n"
        f"version\t5\t{stamp}\topen\tmodel:claude-code\tapproved\n"
        "sources\tevent 1\n"
        "reason\t(none)\n"
        f"change\twhat\twrong\t{_WHAT}\n"
        "change\tdue\t2026-11-30\t2026-12-01\n"
        "rejection\t6\tNOW\thuman:operator\trejects 4\n"
        "reason\trejected (by the operator) — not said\n"
        "version\t7\tNOW\tdirect\tmodel:claude-code\t"
        "made its own by the operator (approval of 5), formulated by model:claude-code\n"
        "sources\tevent 1\n"
        "reason\t(none)\n"
    )
    assert first == 3 and rejected == 4 and approved == 5


@pytest.mark.db
def test_the_preview_of_an_approval_escapes_the_controls_of_a_proposal(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A proposal is text a model wrote from a stranger's mail. U+009B is
    `ESC [` for a terminal and DEL is none to read; neither may come out
    raw. The control is the plain text beside them, which stays as it was."""
    storage = _assertion_log(db, monkeypatch)
    (proposal_id,) = _propose(storage, _debt(what="plain\x9b[2Jmore\x7fend"))
    assert main(["approve", str(proposal_id), "--yes"]) == 0
    out = capsys.readouterr().out
    assert "\x9b" not in out
    assert "\x7f" not in out
    assert '"what": "plain\\u009b[2Jmore\\u007fend"' in out
    assert '"assertion": "obligation"' in out


@pytest.mark.db
@pytest.mark.parametrize(
    ("change", "sentence"),
    [
        ("99", "there is no event 99 to rest on"),
        ("2", "event 2 is erased and cannot be a source"),
        ("1:9", "event 1 has no unit 9"),
    ],
)
def test_a_source_the_log_refuses_is_refused_before_the_question(
    change: str,
    sentence: str,
    db: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ruling F-10 of the 2026-10-12 assertions plan: nobody confirms what
    the write path will refuse. Nothing is shown, nothing is asked, nothing
    is written; the control is the same command with a source that stands."""
    storage = _assertion_log(db, monkeypatch)
    redact_event(storage, storage, 2, reason="r", recorded_at=datetime.now(UTC))
    _answer(monkeypatch, "y\n")
    argv = _assert_obligation()
    argv[argv.index("--source") + 1 :] = [change]
    assert main(argv) == 2
    assert capsys.readouterr() == ("", f"Error: {sentence}\n")
    assert _standing(db) == []
    argv[argv.index("--source") + 1 :] = ["1:1"]
    _answer(monkeypatch, "y\n")
    assert main(argv) == 0


@pytest.mark.db
def test_a_replaced_decision_that_does_not_stand_is_refused_before_the_question(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _assertion_log(db, monkeypatch)
    argv = ["assert", "decision", "--what", "x", "--by", "own", "--on", "2026-10-30"]
    assert main([*argv, "--source", "1", "--replaces", "1"]) == 2
    assert capsys.readouterr() == (
        "",
        "Error: replaces names 1, which is no decision that stands\n",
    )
    assert main([*argv, "--source", "1", "--replaces", "x"]) == 2
    assert capsys.readouterr() == (
        "",
        "Error: --replaces is neither an event id nor none: 'x'\n",
    )


@pytest.mark.db
def test_due_none_and_replaces_none_clear_what_a_subject_would_fill(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control is the same command without `none`, which keeps the value."""
    _assertion_log(db, monkeypatch)
    assert main(_assert_obligation("--yes")) == 0
    capsys.readouterr()
    assert main(["assert", "obligation", "--subject", "3", "--what", "again", "--yes"]) == 0
    assert "change\tdue" not in capsys.readouterr().out
    assert main(["assert", "obligation", "--subject", "3", "--due", "none", "--yes"]) == 0
    assert "change\tdue\t2026-11-30\t(none)\n" in capsys.readouterr().out
    assert _standing(db)[-1][1]["due"] is None
    base = ["assert", "decision", "--what", "x", "--by", "own", "--on", "2026-10-30"]
    assert main([*base, "--source", "1", "--yes"]) == 0  # 6
    assert main([*base, "--source", "1", "--replaces", "6", "--yes"]) == 0  # 7
    assert main(["assert", "decision", "--subject", "7", "--what", "y", "--yes"]) == 0
    assert _standing(db)[-1][1]["replaces"] == 6
    assert main(["assert", "decision", "--subject", "7", "--replaces", "none", "--yes"]) == 0
    assert _standing(db)[-1][1]["replaces"] is None


@pytest.mark.db
def test_approving_an_id_named_twice_approves_it_once(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = _assertion_log(db, monkeypatch)
    first, second = _propose(storage, _debt(what="a"), _debt(what="b"))
    assert main(["approve", str(second), str(first), str(second), "--yes"]) == 0
    assert capsys.readouterr().out.endswith("assertion 5\nassertion 6\n")
    assert [payload["approves"] for _id, payload in _standing(db)[2:]] == [second, first]


@pytest.mark.db
def test_every_field_that_comes_from_outside_is_escaped_on_the_page_and_in_the_history(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Measured by mutation: with `escape_field` dropped from the `reason`
    line of the history, a newline in a reason splits the line and this test
    goes red."""
    _assertion_log(db, monkeypatch)
    argv = ["assert", "obligation", "--debtor", "own", "--creditor", "name:back\\slash"]
    assert main([*argv, "--what", "w\tx", "--reason", "why\ny\x1b", "--source", "1", "--yes"]) == 0
    assert (
        main(
            [
                "assert",
                "obligation",
                "--subject",
                "3",
                "--what",
                "w\ty",
                "--reason",
                "r\tz",
                "--yes",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert main(["obligation", "3"]) == 0
    page = capsys.readouterr().out.splitlines()
    assert "what\tw\ty" not in page
    assert "what\tw\\ty" in page
    assert "creditor\tname:back\\\\slash" in page
    assert "reason\tr\\tz" in page
    assert main(["obligation", "3", "--history"]) == 0
    history = capsys.readouterr().out.splitlines()
    assert "reason\twhy\\ny\\x1b" in history
    assert "set\twhat\tw\\tx" in history
    assert "set\tcreditor\tname:back\\\\slash" in history
    assert "change\twhat\tw\\tx\tw\\ty" in history
    assert all(line.count("\t") <= 5 for line in history)


@pytest.mark.db
def test_the_hint_names_only_the_address_whose_name_matches(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A name in another source than the matching address draws no hint for
    that address. Event 3 shows Bob Meier, event 1 Anna Huber."""
    storage = _assertion_log(db, monkeypatch)
    append(storage, [_assertion_mail("m3", ("bob@x.example", "Bob Meier"))], recorded_at=_ASSERT_AT)
    argv = _assert_obligation("--yes")
    argv[argv.index("--creditor") + 1] = "name:meier"
    argv[argv.index("1:1,2")] = "1"
    assert main(argv) == 0
    assert capsys.readouterr().err == ""
    argv += ["--source", "3"]
    assert main(argv) == 0
    assert capsys.readouterr().err == (
        "hint: bob@x.example appears in the sources; address: is a reference that holds\n"
    )


@pytest.mark.db
def test_the_history_of_an_entry_without_a_winner_is_shown_and_its_page_is_not(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = _assertion_log(db, monkeypatch)
    (proposal_id,) = _propose(storage, _debt())
    assert main(["reject", str(proposal_id), "--yes"]) == 0
    capsys.readouterr()
    assert main(["obligation", str(proposal_id), "--history"]) == 0
    assert capsys.readouterr().out.splitlines()[0] == "obligation 3: 1 version"
    assert main(["obligation", str(proposal_id)]) == 1
    assert capsys.readouterr().err == "no obligation stands under event 3\n"
    assert main(["obligation", "99", "--history"]) == 1


# --- vocabulary -------------------------------------------------------------------


@pytest.mark.db
def test_vocabulary_apply_base_writes_one_event_per_kind_and_show_prints_the_file(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from previously.core.vocabulary import base_vocabulary

    _setup(db, monkeypatch)
    assert main(["vocabulary", "apply", "--base", "--yes"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert "add\tentity\tproject" in lines
    assert lines[-10:] == [f"vocabulary event {n}" for n in range(1, 11)]
    assert _action_count(db) == 10
    assert main(["vocabulary", "show"]) == 0
    assert capsys.readouterr().out == base_vocabulary()
    assert main(["vocabulary", "apply", "--base", "--yes"]) == 0
    assert capsys.readouterr().out == "nothing to change\n"
    assert _action_count(db) == 10


@pytest.mark.db
def test_vocabulary_apply_shows_each_difference_before_it_asks(
    db: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """Declining writes nothing; the control is the same file answered with yes."""
    _setup(db, monkeypatch)
    assert main(["vocabulary", "apply", "--base", "--yes"]) == 0
    capsys.readouterr()
    from previously.core.vocabulary import base_vocabulary

    changed = base_vocabulary().replace('en = "Project"', 'en = "Undertaking"')
    path = tmp_path / "vocabulary.toml"
    path.write_text(changed.replace("[relation.holds]", "[relation.holds]\nretired = true"))
    _answer(monkeypatch, "n\n")
    assert main(["vocabulary", "apply", str(path)]) == 1
    captured = capsys.readouterr()
    assert "retire\trelation\tholds" in captured.out
    assert "change\tentity\tproject" in captured.out
    assert "  labels\t" in captured.out
    assert "nothing written" in captured.err
    assert _action_count(db) == 10
    _answer(monkeypatch, "y\n")
    assert main(["vocabulary", "apply", str(path)]) == 0
    assert _action_count(db) == 12
    assert "vocabulary event 11" in capsys.readouterr().out


@pytest.mark.db
def test_vocabulary_apply_base_after_an_update_adds_and_names_what_differs(
    db: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """The operator's own kind and their label stay, the kind the update
    brings is added, and the kind that differs is named with the way to take
    it. Measured red with `--base` writing `differences` again (it retired
    `team` and changed `project`); the test above, on an empty log, stays
    green then."""
    from previously.core.vocabulary import base_vocabulary

    _setup(db, monkeypatch)
    own = (
        base_vocabulary()
        .replace('en = "Project"', 'en = "Undertaking"')
        .replace(
            "[relation.post_in]",
            '[entity.team]\nlabels = { en = "Team" }\n'
            'fields = [{ name = "name", type = "text", required = true }]\n\n'
            "[relation.post_in]",
        )
    )
    lacking = own.split("[relation.post_in]")[0]
    path = tmp_path / "vocabulary.toml"
    path.write_text(lacking)
    assert main(["vocabulary", "apply", str(path), "--yes"]) == 0
    capsys.readouterr()
    written = _action_count(db)
    _answer(monkeypatch, "y\n")
    assert main(["vocabulary", "apply", "--base"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "add\trelation\tpost_in"
    assert "differs\tentity\tproject" in lines
    assert any(line.startswith("  labels\t") and "Undertaking" in line for line in lines)
    assert "--base changes no kind the log holds" in "\n".join(lines)
    assert not [line for line in lines if line.startswith(("retire", "change"))]
    assert _action_count(db) == written + 1
    assert main(["vocabulary", "show"]) == 0
    shown = capsys.readouterr().out
    assert "[entity.team]" in shown
    assert "retired = true" not in shown
    assert 'en = "Undertaking"' in shown
    # Nothing is missing any more: the difference is named again, nothing written.
    assert main(["vocabulary", "apply", "--base", "--yes"]) == 0
    out = capsys.readouterr().out
    assert "differs\tentity\tproject" in out
    assert out.endswith("nothing to change\n")
    assert _action_count(db) == written + 1


@pytest.mark.db
def test_vocabulary_apply_needs_a_file_or_base_and_refuses_before_asking(
    db: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    _setup(db, monkeypatch)
    assert main(["vocabulary", "apply", "--yes"]) == 2
    assert "give a FILE or --base" in capsys.readouterr().err
    assert main(["vocabulary", "apply", "x.toml", "--base", "--yes"]) == 2
    assert main(["vocabulary", "apply", str(tmp_path / "missing.toml"), "--yes"]) == 2
    path = tmp_path / "v.toml"
    path.write_text('[entity.team]\nlabels = { en = "T" }\nbehaviours = []\n')
    assert main(["vocabulary", "apply", str(path), "--yes"]) == 2
    assert "unknown key 'behaviours'" in capsys.readouterr().err
    path.write_text('[relation.r]\nlabels = { en = "R" }\nfrom = ["nothing"]\nto = ["circle"]\n')
    assert main(["vocabulary", "apply", str(path)]) == 2
    captured = capsys.readouterr()
    assert "no entity kind that stands" in captured.err
    assert "add\t" not in captured.out
    assert _action_count(db) == 0


@pytest.mark.db
def test_vocabulary_show_at_reads_the_vocabulary_of_that_moment(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup(db, monkeypatch)
    assert main(["vocabulary", "apply", "--base", "--yes"]) == 0
    capsys.readouterr()
    assert main(["vocabulary", "show", "--at", "2000-01-01T00:00:00Z"]) == 0
    before = capsys.readouterr().out
    assert "[entity.project]" not in before
    assert "[entity.circle]" in before
    assert main(["vocabulary", "show", "--at", "2999-01-01T00:00:00Z"]) == 0
    assert "[entity.project]" in capsys.readouterr().out
    assert main(["vocabulary", "show", "--at", "2999-01-01T00:00:00"]) == 2


def test_the_help_names_vocabulary_with_its_sentence(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])
    assert re.search(
        r"^\s+vocabulary\s+show or apply the vocabulary of entities and relations$",
        capsys.readouterr().out,
        re.M,
    )


# --- entities and relations: entity, relate, the lists, classes, triage ------------

_VELLENFELD = "Verein Vellenfeld"


def _graph_log(
    db: object, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> PostgresStorage:
    """A log with two mails (events 1 and 2) and the base vocabulary, so the
    first entity gets event id 13 (the vocabulary writes ten events)."""
    storage = _assertion_log(db, monkeypatch)
    assert main(["vocabulary", "apply", "--base", "--yes"]) == 0
    capsys.readouterr()
    return storage


def _run(capsys: pytest.CaptureFixture[str], *argv: str, code: int = 0) -> str:
    """The standard output of one command, which has to end with `code`;
    the standard error is left for the caller to read with `capsys`."""
    assert main(list(argv)) == code, capsys.readouterr().err
    return capsys.readouterr().out


def _written(capsys: pytest.CaptureFixture[str], *argv: str) -> int:
    """The id a writing command printed: its last line is `assertion <id>`,
    or `approval class event <id>`."""
    out = _run(capsys, *argv, "--yes")
    last = re.fullmatch(r"(?:assertion|approval class event) (\d+)", out.splitlines()[-1])
    assert last is not None, out
    return int(last[1])


def _refused(capsys: pytest.CaptureFixture[str], *argv: str) -> str:
    """The sentence after `Error: ` of a command that exits 2."""
    assert main(list(argv)) == 2
    captured = capsys.readouterr()
    assert captured.err.startswith("Error: "), captured.err
    return captured.err.removeprefix("Error: ").rstrip("\n")


def _lines(out: str) -> list[list[str]]:
    return [line.split("\t") for line in out.splitlines()]


@pytest.mark.db
def test_entity_shows_the_claim_asks_and_writes_a_direct_version(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _graph_log(db, monkeypatch, capsys)
    _answer(monkeypatch, "y\n")
    assert main(["entity", "organization", "--name", _VELLENFELD, "--source", "1:1,2"]) == 0
    captured = capsys.readouterr()
    assert captured.out.endswith("write? [y/N] assertion 13\n")
    assert captured.err == ""
    preview = json.loads(captured.out.removesuffix("write? [y/N] assertion 13\n"))
    assert preview["assertion"] == "entity"
    assert preview["author"] == "human:operator"
    assert preview["responsibility"] == "direct"
    assert preview["evidence"] == "sources"
    assert preview["sources"] == [{"event": 1, "units": [1, 2]}]
    assert preview["fields"] == {"name": _VELLENFELD}
    assert preview["state"] == "active"
    ((event_id, payload),) = _standing(db)
    assert event_id == 13
    assert payload == preview


@pytest.mark.db
def test_entity_writes_nothing_after_a_no_and_says_so(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _graph_log(db, monkeypatch, capsys)
    _answer(monkeypatch, "n\n")
    assert main(["entity", "organization", "--name", "x", "--source", "1"]) == 1
    captured = capsys.readouterr()
    assert captured.err == "nothing written\n"
    assert '"assertion": "entity"' in captured.out
    assert _standing(db) == []


@pytest.mark.db
def test_a_recollection_has_no_source_and_the_two_together_are_refused(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _graph_log(db, monkeypatch, capsys)
    out = _run(capsys, "entity", "person", "--name", "Anna", "--recollection", "--yes")
    assert out.endswith("assertion 13\n")
    ((_id, payload),) = _standing(db)
    assert payload["evidence"] == "recollection"
    assert payload["sources"] == []
    assert payload["responsibility"] == "direct"
    assert _refused(
        capsys, "entity", "person", "--name", "B", "--recollection", "--source", "1", "--yes"
    ) == ("--recollection and --source exclude each other")
    assert _refused(capsys, "entity", "person", "--name", "B", "--yes") == (
        "an entity needs --source or --recollection unless --subject names the one to change"
    )
    assert len(_standing(db)) == 1


@pytest.mark.db
def test_the_fields_are_read_by_the_type_the_kind_declares(
    db: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    _graph_log(db, monkeypatch, capsys)
    from previously.core.vocabulary import base_vocabulary

    path = tmp_path / "vocabulary.toml"
    path.write_text(
        base_vocabulary()
        + """
[entity.case]
labels = { en = "Case" }
behaviors = ["period"]
fields = [
  { name = "name", type = "text", required = true },
  { name = "opened", type = "date", required = false },
  { name = "period", type = "period", required = false },
  { name = "state_of", type = "choice", values = ["open", "shut"], required = false },
  { name = "owner", type = "ref", ref = "person", required = false },
]
""",
        encoding="utf-8",
    )
    _run(capsys, "vocabulary", "apply", str(path), "--yes")
    person = _written(capsys, "entity", "person", "--name", "Anna", "--recollection")
    case = _written(
        capsys,
        *("entity", "case", "--name", "C 1", "--source", "1"),
        *("--field", "opened=2019-03-01", "--field", "period=2015-01-01.."),
        *("--field", "state_of=shut", "--field", f"owner={person}"),
    )
    page = {
        line[1]: line[2] for line in _lines(_run(capsys, "entity", str(case))) if line[0] == "field"
    }
    assert page == {
        "name": "C 1",
        "opened": "2019-03-01",
        "owner": str(person),
        "period": "2015-01-01..",
        "state_of": "shut",
    }
    payload = cast("dict[str, object]", dict(_standing(db))[case]["fields"])
    assert payload["period"] == {"from": "2015-01-01", "to": None}
    assert payload["owner"] == person
    assert _written(
        capsys, "entity", "case", "--name", "C 2", "--source", "1", "--field", "period=..2019-12-31"
    )
    second = cast("dict[str, object]", dict(_standing(db))[case + 1]["fields"])
    assert second["period"] == {"from": None, "to": "2019-12-31"}


@pytest.mark.db
@pytest.mark.parametrize(
    ("option", "sentence"),
    [
        ("colour=red", '--field names "colour", which the kind does not declare'),
        ("name", "--field is not NAME=VALUE: 'name'"),
        ("name=A", '--field names "name" twice'),
    ],
)
def test_a_field_that_cannot_be_read_is_refused_with_one_sentence(
    db: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    option: str,
    sentence: str,
) -> None:
    _graph_log(db, monkeypatch, capsys)
    argv = ["entity", "person", "--name", "A", "--source", "1", "--field", option, "--yes"]
    assert _refused(capsys, *argv) == sentence
    assert _standing(db) == []


@pytest.mark.db
def test_a_value_the_type_does_not_read_is_refused(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _graph_log(db, monkeypatch, capsys)
    base = ["entity", "project", "--name", "P", "--source", "1", "--yes"]
    assert _refused(capsys, *base, "--field", "period=2019") == (
        "--field period is not a period written FROM..TO; an end may be empty"
    )
    assert _refused(capsys, *base, "--field", "period=2019-13-01..") == (
        "--field period is not a date written YYYY-MM-DD"
    )
    assert _standing(db) == []


def _vellenfeld(capsys: pytest.CaptureFixture[str]) -> dict[str, int]:
    """The association of the specification, written on the command line:
    the association, its board as a circle, three people, and their terms on
    the board. The terms of the first two overlap on 2019-03-01."""
    ids: dict[str, int] = {}
    ids["verein"] = _written(
        capsys, "entity", "organization", "--name", _VELLENFELD, "--source", "1"
    )
    ids["board"] = _written(capsys, "entity", "circle", "--name", "Vorstand", "--source", "1")
    for key, name in (("anna", "Anna Huber"), ("berta", "Berta Maier"), ("carl", "Carl Steiner")):
        ids[key] = _written(capsys, "entity", "person", "--name", name, "--source", "1")
    ids["obmann"] = _written(capsys, "entity", "post", "--name", "Obmann", "--source", "1")
    ids["post_in"] = _written(
        capsys,
        *("relate", "post_in", "--from", str(ids["obmann"]), "--to", str(ids["verein"])),
        *("--source", "1"),
    )
    ids["holds"] = _written(
        capsys,
        *("relate", "holds", "--from", str(ids["anna"]), "--to", str(ids["obmann"])),
        *("--from-date", "2015-01-01", "--to-date", "2019-12-31", "--source", "1"),
    )
    board = str(ids["board"])
    ids["anna_term"] = _written(
        capsys,
        *("relate", "member_of", "--from", str(ids["anna"]), "--to", board),
        *("--from-date", "2015-01-01", "--to-date", "2019-12-31", "--source", "1"),
    )
    ids["berta_term"] = _written(
        capsys,
        *("relate", "member_of", "--from", str(ids["berta"]), "--to", board),
        *("--from-date", "2017-06-01", "--source", "1"),
    )
    ids["carl_term"] = _written(
        capsys,
        *("relate", "member_of", "--from", str(ids["carl"]), "--to", board),
        *("--from-date", "2020-01-01", "--source", "1"),
    )
    return ids


@pytest.mark.db
def test_who_sat_on_the_board_on_the_first_of_march_2019(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _graph_log(db, monkeypatch, capsys)
    ids = _vellenfeld(capsys)
    board = str(ids["board"])
    out = _run(capsys, "relations", "--type", "member_of", "--to", board, "--at", "2019-03-01")
    lines = _lines(out)
    assert [line[0] for line in lines] == [str(ids["anna_term"]), str(ids["berta_term"])]
    assert lines[0] == [
        str(ids["anna_term"]),
        "active" if False else "standing",
        "Member of",
        f"{ids['anna']} Anna Huber",
        f"{ids['board']} Vorstand",
        "2015-01-01..2019-12-31",
        "1 version",
    ]
    assert lines[1][3:6] == [
        f"{ids['berta']} Berta Maier",
        f"{ids['board']} Vorstand",
        "2017-06-01..",
    ]
    # The control: without the day, all three terms are listed; so `--at` is
    # what keeps Carl out.
    everyone = _lines(_run(capsys, "relations", "--type", "member_of", "--to", board))
    assert [line[0] for line in everyone] == [
        str(ids["anna_term"]),
        str(ids["berta_term"]),
        str(ids["carl_term"]),
    ]
    later = _lines(
        _run(capsys, "relations", "--type", "member_of", "--to", board, "--at", "2020-06-01")
    )
    assert [line[0] for line in later] == [str(ids["berta_term"]), str(ids["carl_term"])]


@pytest.mark.db
def test_the_page_of_an_entity_shows_its_relations_in_both_directions(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _graph_log(db, monkeypatch, capsys)
    ids = _vellenfeld(capsys)
    page = _lines(_run(capsys, "entity", str(ids["obmann"])))
    assert page[0] == [f"entity {ids['obmann']}"]
    assert ["type", "post", "Post"] in page
    assert ["field", "name", "Obmann"] in page
    relations = [line for line in page if line[0] == "relation"]
    assert relations == [
        [
            "relation",
            str(ids["post_in"]),
            "Post in",
            "out",
            f"{ids['verein']} {_VELLENFELD}",
            "-",
            "standing",
        ],
        [
            "relation",
            str(ids["holds"]),
            "Holds",
            "in",
            f"{ids['anna']} Anna Huber",
            "2015-01-01..2019-12-31",
            "standing",
        ],
    ]


@pytest.mark.db
def test_entities_lists_what_stands_and_filters_by_kind_and_state(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _graph_log(db, monkeypatch, capsys)
    ids = _vellenfeld(capsys)
    project = _written(capsys, "entity", "project", "--name", "Roof", "--source", "1")
    _written(capsys, "entity", "project", "--subject", str(project), "--state", "closed")
    everything = _lines(_run(capsys, "entities"))
    wanted = [ids[key] for key in ("verein", "board", "anna", "berta", "carl", "obmann")]
    assert [line[0] for line in everything] == [str(item) for item in [*wanted, project]]
    assert everything[0] == [
        str(ids["verein"]),
        "active",
        "Organization",
        _VELLENFELD,
        "1 version",
        "0 proposals",
    ]
    people = _lines(_run(capsys, "entities", "--type", "person"))
    assert [line[3] for line in people] == ["Anna Huber", "Berta Maier", "Carl Steiner"]
    closed = _lines(_run(capsys, "entities", "--state", "closed"))
    assert closed == [[str(project), "closed", "Project", "Roof", "2 versions", "0 proposals"]]


@pytest.mark.db
def test_a_new_version_fills_what_it_leaves_out_and_a_retraction_takes_the_entity_out(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _graph_log(db, monkeypatch, capsys)
    anna = _written(
        capsys, "entity", "person", "--name", "Anna", "--language", "de", "--source", "1:2"
    )
    _written(capsys, "entity", "person", "--subject", str(anna), "--name", "Anna Huber")
    ((_, first), (_, second)) = _standing(db)
    assert second["subject"] == anna
    assert second["sources"] == first["sources"] == [{"event": 1, "units": [2]}]
    assert second["language"] == "de"
    assert second["fields"] == {"name": "Anna Huber"}
    _written(capsys, "entity", "person", "--subject", str(anna), "--state", "retracted")
    assert _run(capsys, "entities") == ""
    retracted = _lines(_run(capsys, "entities", "--state", "retracted"))
    assert [(line[0], line[1]) for line in retracted] == [(str(anna), "retracted")]
    assert _refused(capsys, "entity", "person", "--subject", "999", "--yes") == (
        "--subject 999 names no entity that stands"
    )


@pytest.mark.db
def test_a_relation_is_ended_with_a_new_version_and_taken_back_with_a_retraction(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _graph_log(db, monkeypatch, capsys)
    ids = _vellenfeld(capsys)
    carl = str(ids["carl_term"])
    ended = _written(capsys, "relate", "member_of", "--subject", carl, "--to-date", "2022-12-31")
    assert ended == ids["carl_term"] + 1
    payload = dict(_standing(db))[ended]
    assert payload["subject"] == ids["carl_term"]
    assert payload["period"] == {"from": "2020-01-01", "to": "2022-12-31"}
    assert payload["from"] == {"entity": ids["carl"]}
    assert payload["to"] == {"entity": ids["board"]}
    gone = _lines(_run(capsys, "relations", "--to", str(ids["board"]), "--at", "2023-06-01"))
    assert [line[0] for line in gone] == [str(ids["berta_term"])]
    _written(capsys, "relate", "member_of", "--subject", carl, "--retract")
    still = _lines(_run(capsys, "relations", "--to", str(ids["board"])))
    assert [line[0] for line in still] == [str(ids["anna_term"]), str(ids["berta_term"])]
    assert _refused(capsys, "relate", "member_of", "--from", "1", "--yes") == (
        "a relation needs --to and --source or --recollection "
        "unless --subject names the one to change"
    )


@pytest.mark.db
def test_as_of_shows_the_graph_as_it_stood(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _graph_log(db, monkeypatch, capsys)
    ids = _vellenfeld(capsys)
    roof = _written(capsys, "entity", "project", "--name", "Roof", "--source", "1")
    before = datetime.now(UTC).isoformat()
    time.sleep(0.02)
    late = _written(
        capsys,
        *("relate", "involved_in", "--from", str(ids["carl"]), "--to", str(roof)),
        *("--source", "1"),
    )
    assert _run(capsys, "relations", "--type", "involved_in", "--as-of", before) == ""
    earlier = _lines(_run(capsys, "relations", "--as-of", before))
    assert str(late) not in [line[0] for line in earlier]
    assert len(earlier) == 5
    now = _lines(_run(capsys, "relations", "--type", "involved_in"))
    assert [line[0] for line in now] == [str(late)]
    assert main(["relations", "--as-of", "2026-10-14T10:00:00"]) == 2
    assert "has no time zone" in capsys.readouterr().err


@pytest.mark.db
def test_a_relation_to_an_erased_or_retracted_entity_stays_and_says_so(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = _graph_log(db, monkeypatch, capsys)
    board = _written(capsys, "entity", "circle", "--name", "Vorstand", "--source", "1")
    anna = _written(capsys, "entity", "person", "--name", "Anna", "--source", "2")
    berta = _written(capsys, "entity", "person", "--name", "Berta", "--source", "1")
    for person in (anna, berta):
        _written(
            capsys,
            *("relate", "member_of", "--from", str(person), "--to", str(board)),
            *("--source", "1"),
        )
    _written(capsys, "entity", "person", "--subject", str(berta), "--state", "retracted")
    redact_event(storage, storage, 2, reason="r", recorded_at=datetime.now(UTC))
    lines = _lines(_run(capsys, "relations", "--type", "member_of"))
    assert [(line[3], line[4]) for line in lines] == [
        (f"{anna} (erased)", f"{board} Vorstand"),
        (f"{berta} (retracted)", f"{board} Vorstand"),
    ]
    # An erased entity has no page; the reader is told so, not that none stood.
    assert main(["entity", str(anna)]) == 1
    assert capsys.readouterr().err == f"assertion {anna} is erased\n"
    assert main(["entity", "999"]) == 1
    assert capsys.readouterr().err == "no entity stands under event 999\n"


@pytest.mark.db
def test_the_history_shows_an_old_version_unchanged_and_marks_what_no_longer_fits(
    db: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    from previously.core.vocabulary import base_vocabulary

    _graph_log(db, monkeypatch, capsys)
    path = tmp_path / "vocabulary.toml"
    path.write_text(
        base_vocabulary()
        + """
[entity.badge]
labels = { en = "Badge" }
behaviors = []
fields = [
  { name = "name", type = "text", required = true },
  { name = "colour", type = "choice", values = ["red", "blue"], required = false },
]
""",
        encoding="utf-8",
    )
    _run(capsys, "vocabulary", "apply", str(path), "--yes")
    badge = _written(
        capsys, "entity", "badge", "--name", "B", "--field", "colour=red", "--source", "1"
    )
    other = _written(
        capsys, "entity", "badge", "--name", "C", "--field", "colour=blue", "--source", "1"
    )
    before = _run(capsys, "entity", str(badge), "--history")
    # The same file with red taken out of the choice: today's vocabulary
    # would not take the first badge any more.
    path.write_text(path.read_text(encoding="utf-8").replace('["red", "blue"]', '["blue"]'))
    _run(capsys, "vocabulary", "apply", str(path), "--yes")
    after = _run(capsys, "entity", str(badge), "--history")
    # Only the mark is added to the head of the version; nothing else of it
    # was rewritten.
    assert after.splitlines()[0] == before.splitlines()[0]
    assert after.splitlines()[1] == before.splitlines()[1] + "\t(does not fit the vocabulary)"
    assert after.splitlines()[2:] == before.splitlines()[2:]
    marked = _lines(after)
    assert marked[1][:2] == ["version", str(badge)]
    assert marked[1][-1] == "(does not fit the vocabulary)"
    assert ["set", "fields.colour", "red"] in marked
    assert "(does not fit the vocabulary)" not in before
    assert _lines(_run(capsys, "entities", "--type", "badge")) == [
        [
            str(badge),
            "active",
            "Badge",
            "B",
            "1 version",
            "0 proposals",
            "(does not fit the vocabulary)",
        ],
        [str(other), "active", "Badge", "C", "1 version", "0 proposals"],
    ]
    assert _run(capsys, "entity", str(badge)).splitlines()[0] == (
        f"entity {badge} (does not fit the vocabulary)"
    )
    # A new version has to fit, and the sentence says so; the old one stays.
    assert _refused(
        capsys, "entity", "badge", "--subject", str(badge), "--name", "B2", "--yes"
    ) == ('the field "colour" holds none of the values its kind allows')
    assert [
        line[1]
        for line in _lines(_run(capsys, "entity", str(badge), "--history"))
        if line[0] == "set"
    ] == [
        "type",
        "language",
        "fields.colour",
        "fields.name",
        "state",
    ]


@pytest.mark.db
def test_a_label_is_shown_in_the_working_language_of_the_entity_else_in_the_setting(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _graph_log(db, monkeypatch, capsys)
    plain = _written(capsys, "entity", "circle", "--name", "A", "--source", "1")
    german = _written(
        capsys, "entity", "circle", "--name", "B", "--language", "de", "--source", "1"
    )
    japanese = _written(
        capsys, "entity", "circle", "--name", "C", "--language", "ja", "--source", "1"
    )
    shown = {line[0]: line[2] for line in _lines(_run(capsys, "entities"))}
    # No working language: the setting, which is `en` unless set. A working
    # language the kind has no label in: the first label there is, marked.
    assert shown == {str(plain): "Circle", str(german): "Kreis", str(japanese): "Kreis (de)"}
    monkeypatch.setenv("PREVIOUSLY_LANGUAGE", "de")
    shown = {line[0]: line[2] for line in _lines(_run(capsys, "entities"))}
    assert shown == {str(plain): "Kreis", str(german): "Kreis", str(japanese): "Kreis (de)"}
    monkeypatch.setenv("PREVIOUSLY_LANGUAGE", "fr")
    shown = {line[0]: line[2] for line in _lines(_run(capsys, "entities"))}
    assert shown[str(plain)] == "Kreis (de)"
    assert _lines(_run(capsys, "entity", str(plain)))[2][2] == "Kreis (de)"


@pytest.mark.db
def test_the_language_setting_is_a_language_tag_or_it_is_refused(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _graph_log(db, monkeypatch, capsys)
    monkeypatch.setenv("PREVIOUSLY_LANGUAGE", "pt-BR")
    assert main(["entities"]) == 0
    for bad in ("German", "de_AT", "d"):
        monkeypatch.setenv("PREVIOUSLY_LANGUAGE", bad)
        assert _refused(capsys, "entities") == (
            "PREVIOUSLY_LANGUAGE is not a language tag such as en or pt-BR"
        )
    monkeypatch.setenv("PREVIOUSLY_LANGUAGE", "")
    assert main(["entities"]) == 0


def _model_claim(
    kind: str,
    body: EntityBody | RelationBody,
    *,
    subject: int | None = None,
    confidence: int | None = None,
) -> Claim:
    return Claim(
        kind,
        model_author("claude-code"),
        OPEN,
        SOURCES,
        (Source(1, None),),
        None,
        None,
        subject,
        None,
        None,
        confidence,
        None,
        body,
    )


def _model_writes(storage: PostgresStorage, *claims: Claim) -> tuple[int, ...]:
    return write_claims(storage, storage, claims, recorded_at=_ASSERT_AT).ids


def _model_person(
    storage: PostgresStorage,
    name: str,
    *,
    subject: int | None = None,
    confidence: int | None = None,
) -> int:
    body = EntityBody("person", None, {"name": name}, ACTIVE)
    return _model_writes(
        storage, _model_claim(ENTITY, body, subject=subject, confidence=confidence)
    )[0]


@pytest.mark.db
def test_classes_add_shows_the_class_asks_and_writes_an_event(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _graph_log(db, monkeypatch, capsys)
    argv = ["classes", "add", "maier", "--author", "model:claude-code", "--assertion", "entity"]
    argv += ["--type", "person", "--threshold", "80", "--statement", "names from mails"]
    _answer(monkeypatch, "y\n")
    assert main(argv) == 0
    out = capsys.readouterr().out
    assert out.endswith("write? [y/N] approval class event 13\n")
    payload = json.loads(out.removesuffix("write? [y/N] approval class event 13\n"))
    assert payload["threshold"] == 80
    assert payload["types"] == ["person"]
    assert payload["revoked"] is False
    _answer(monkeypatch, "n\n")
    assert main([*argv[:2], "other", *argv[3:]]) == 1
    assert capsys.readouterr().err == "nothing written\n"


@pytest.mark.db
def test_a_class_that_cannot_be_written_is_refused_before_the_question(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _graph_log(db, monkeypatch, capsys)
    argv = ["classes", "add", "maier", "--author", "model:claude-code", "--assertion", "entity"]
    argv += ["--threshold", "80", "--statement", "s"]
    # Nobody is asked: with no input at all, a question would end in "no
    # answer", and the refusal would never be said.
    _answer(monkeypatch, "")
    sentence = _refused(capsys, *argv, "--type", "nothing")
    assert sentence == (
        'the approval class names "nothing", which is no entity kind that stands in the vocabulary'
    )
    # The control: a class that can be written reaches the question.
    assert main([*argv, "--type", "person"]) == 1
    assert "no answer: the input ended" in capsys.readouterr().err
    assert _action_count(db) == 10


@pytest.mark.db
def test_classes_revoke_keeps_the_other_fields_and_demote_is_a_state_of_its_own(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _graph_log(db, monkeypatch, capsys)
    argv = ["classes", "add", "maier", "--author", "model:claude-code", "--assertion", "entity"]
    argv += ["--type", "person", "--type", "post", "--threshold", "80"]
    argv += ["--from", "2026-01-01T00:00:00Z", "--until", "2027-01-01T00:00:00Z"]
    _written(capsys, *argv, "--statement", "s")
    before = _lines(_run(capsys, "classes", "list"))[0]
    assert before[:7] == [
        "maier",
        "model:claude-code",
        "entity",
        "person,post",
        "80",
        "2026-01-01T00:00:00.000000Z..2027-01-01T00:00:00.000000Z",
        "active",
    ]
    _run(capsys, "classes", "revoke", "maier", "--statement", "no longer", "--yes")
    revoked = _lines(_run(capsys, "classes", "list"))[0]
    assert revoked[:6] == before[:6]
    assert revoked[6] == "revoked"
    _run(capsys, "classes", "revoke", "maier", "--demote", "--statement", "worse", "--yes")
    demoted = _lines(_run(capsys, "classes", "list"))[0]
    assert demoted[:6] == before[:6]
    assert demoted[6] == "revoked and demoted"
    assert _refused(capsys, "classes", "revoke", "nobody", "--statement", "s", "--yes") == (
        "no approval class is named nobody"
    )


@pytest.mark.db
def test_the_hit_rate_counts_what_was_confirmed_corrected_and_left_standing(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = _graph_log(db, monkeypatch, capsys)
    argv = ["classes", "add", "maier", "--author", "model:claude-code", "--assertion", "entity"]
    _written(capsys, *argv, "--type", "person", "--threshold", "80", "--statement", "s")
    assert _lines(_run(capsys, "classes", "list"))[0][7:] == [
        "0 total, 0 confirmed, 0 corrected, 0 standing",
        "(event 13)",
    ]
    confirmed, corrected, standing = (
        _model_person(storage, name, confidence=90) for name in ("Anna", "Berta", "Carl")
    )
    _written(capsys, "approve", str(confirmed))
    _written(capsys, "entity", "person", "--subject", str(corrected), "--name", "Berta Maier")
    row = _lines(_run(capsys, "classes", "list"))[0]
    assert row[7] == "3 total, 1 confirmed, 1 corrected, 1 standing"
    assert str(standing) in _run(capsys, "classes", "sample", "maier")


@pytest.mark.db
def test_sample_gives_the_asked_number_from_the_versions_the_class_let_through(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = _graph_log(db, monkeypatch, capsys)
    argv = ["classes", "add", "maier", "--author", "model:claude-code", "--assertion", "entity"]
    _written(capsys, *argv, "--type", "person", "--threshold", "80", "--statement", "s")
    inside = [_model_person(storage, f"P{n}", confidence=90) for n in range(4)]
    outside = _model_person(storage, "Low", confidence=10)
    everything = _lines(_run(capsys, "classes", "sample", "maier"))
    assert [line[0] for line in everything] == [str(item) for item in inside]
    assert everything[0] == [
        str(inside[0]),
        str(inside[0]),
        "entity",
        "Person",
        "P0",
        "90",
        "model:claude-code",
    ]
    one = _lines(_run(capsys, "classes", "sample", "maier", "--count", "1"))
    assert len(one) == 1
    assert one[0][0] in {str(item) for item in inside}
    assert str(outside) not in {line[0] for line in everything}
    assert _refused(capsys, "classes", "sample", "maier", "--count", "0") == (
        "--count must be at least 1, got 0"
    )
    assert _refused(capsys, "classes", "sample", "nobody") == "no approval class is named nobody"


def _waiting_graph(
    db: object, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> dict[str, int]:
    """A proposal, then a question, then an objection: the order of their
    ids is the reverse of the order triage lists them in."""
    storage = _graph_log(db, monkeypatch, capsys)
    ids: dict[str, int] = {}
    ids["anna"] = _written(capsys, "entity", "person", "--name", "Anna", "--source", "1")
    ids["circle_a"] = _written(capsys, "entity", "circle", "--name", "Kasse", "--source", "1")
    ids["circle_b"] = _written(capsys, "entity", "circle", "--name", "Kasse II", "--source", "1")
    ids["proposal"] = _model_person(storage, "Berta")
    asking = RelationBody(
        "member_of", ids["anna"], None, (ids["circle_a"], ids["circle_b"]), None, {}, "standing"
    )
    (ids["question"],) = _model_writes(storage, _model_claim(RELATION, asking))
    ids["objection"] = _model_person(storage, "Anna Maier", subject=ids["anna"])
    return ids


@pytest.mark.db
def test_triage_lists_objections_then_questions_then_proposals(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = _waiting_graph(db, monkeypatch, capsys)
    assert ids["proposal"] < ids["question"] < ids["objection"]
    author = "model:claude-code"
    anna, a, b = ids["anna"], ids["circle_a"], ids["circle_b"]
    assert _lines(_run(capsys, "triage")) == [
        ["objection", str(ids["objection"]), "Person", "Anna Maier", author],
        [
            *("question", str(ids["question"]), "Member of"),
            f"{anna} Anna -> ? ({a} Kasse, {b} Kasse II)",
            author,
        ],
        ["proposal", str(ids["proposal"]), "Person", "Berta", author],
    ]
    assert _run(capsys, "status") == "objections\t1\nquestions\t1\nproposals\t1\n"


@pytest.mark.db
def test_status_counts_nothing_as_three_lines_of_zero(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _graph_log(db, monkeypatch, capsys)
    assert _run(capsys, "triage") == ""
    assert _run(capsys, "status") == "objections\t0\nquestions\t0\nproposals\t0\n"


@pytest.mark.db
def test_answer_approves_the_question_with_the_chosen_candidate(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = _waiting_graph(db, monkeypatch, capsys)
    question = str(ids["question"])
    _answer(monkeypatch, "n\n")
    assert main(["answer", question, "--choose", str(ids["circle_b"])]) == 1
    assert capsys.readouterr().err == "nothing written\n"
    answer = _written(capsys, "answer", question, "--choose", str(ids["circle_b"]))
    payload = dict(_standing(db))[answer]
    assert payload["responsibility"] == "direct"
    assert payload["approves"] == ids["question"]
    assert payload["subject"] == ids["question"]
    assert payload["to"] == {"entity": ids["circle_b"]}
    # The model's author and sources are kept: an approval takes them unchanged.
    assert payload["author"] == "model:claude-code"
    assert payload["sources"] == [{"event": 1, "units": None}]
    assert _run(capsys, "status") == "objections\t1\nquestions\t0\nproposals\t1\n"
    stands = _lines(_run(capsys, "relations", "--type", "member_of"))
    assert [(line[0], line[3], line[4]) for line in stands] == [
        (question, f"{ids['anna']} Anna", f"{ids['circle_b']} Kasse II")
    ]


@pytest.mark.db
def test_answer_refuses_what_is_no_question_and_a_choice_that_is_no_candidate(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = _waiting_graph(db, monkeypatch, capsys)
    stranger = _written(capsys, "entity", "circle", "--name", "Other", "--source", "1")
    before = len(_standing(db))
    assert _refused(capsys, "answer", str(ids["proposal"]), "--choose", "1", "--yes") == (
        f"event {ids['proposal']} is no question that waits"
    )
    assert _refused(capsys, "answer", "9999", "--choose", "1", "--yes") == (
        "event 9999 is no question that waits"
    )
    sentence = _refused(capsys, "answer", str(ids["question"]), "--choose", str(stranger), "--yes")
    assert sentence == f"the answer names {stranger}, which is none of the candidates"
    # It is the sentence the write path gives for a direct answer.
    direct = RelationBody("member_of", ids["anna"], stranger, None, None, {}, "standing")
    claim = replace(
        _model_claim(RELATION, direct, subject=ids["question"]),
        author="human:operator",
        responsibility="direct",
    )
    storage = PostgresStorage(cast("Engine", db))
    with pytest.raises(GraphRefused) as raised, storage.snapshot() as conn:
        check_claims(storage, conn, [claim], recorded_at=_ASSERT_AT)
    assert str(raised.value) == sentence
    assert len(_standing(db)) == before


@pytest.mark.db
def test_approve_makes_a_membership_a_model_proposed_direct_on_the_command_line(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ruling F-b of the 2026-10-14 assignments plan refuses this over MCP;
    the command line is where the operator does it, and it stays allowed."""
    ids = _waiting_graph(db, monkeypatch, capsys)
    storage = PostgresStorage(cast("Engine", db))
    member = RelationBody("member_of", ids["anna"], ids["circle_a"], None, None, {}, "standing")
    (proposed,) = _model_writes(storage, _model_claim(RELATION, member))
    approval = _written(capsys, "approve", str(proposed))
    payload = dict(_standing(db))[approval]
    assert (payload["type"], payload["responsibility"], payload["approves"]) == (
        "member_of",
        "direct",
        proposed,
    )


@pytest.mark.db
def test_approve_takes_a_proposal_or_an_objection_of_the_graph_as_the_operators_own(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = _waiting_graph(db, monkeypatch, capsys)
    out = _run(capsys, "approve", str(ids["proposal"]), str(ids["objection"]), "--yes")
    previews = out.split("assertion ")[0]
    assert previews.count('"approves"') == 2
    written = [int(line.removeprefix("assertion ")) for line in out.splitlines()[-2:]]
    payloads = dict(_standing(db))
    first, second = payloads[written[0]], payloads[written[1]]
    assert (first["approves"], first["subject"]) == (ids["proposal"], ids["proposal"])
    assert (second["approves"], second["subject"]) == (ids["objection"], ids["anna"])
    assert first["responsibility"] == second["responsibility"] == "direct"
    assert second["contests"] is None
    assert second["fields"] == {"name": "Anna Maier"}
    assert _run(capsys, "status") == "objections\t0\nquestions\t1\nproposals\t0\n"
    names = {line[0]: line[3] for line in _lines(_run(capsys, "entities", "--type", "person"))}
    assert names == {str(ids["anna"]): "Anna Maier", str(ids["proposal"]): "Berta"}


@pytest.mark.db
def test_reject_turns_a_proposal_of_the_graph_down_with_its_sources(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = _waiting_graph(db, monkeypatch, capsys)
    rejection = _written(capsys, "reject", str(ids["proposal"]), "--reason", "not a member")
    payload = dict(_standing(db))[rejection]
    assert payload["assertion"] == "rejection"
    assert payload["of"] == ids["proposal"]
    assert payload["sources"] == [{"event": 1, "units": None}]
    assert payload["reason"] == "not a member"
    assert _run(capsys, "status") == "objections\t1\nquestions\t1\nproposals\t0\n"
    waiting = [line[0] for line in _lines(_run(capsys, "entities", "--proposals"))]
    assert waiting == [str(ids["anna"])]  # the objection is still there; Berta is not
    # Once is enough: the same proposal is not rejected twice.
    assert _refused(capsys, "reject", str(ids["proposal"]), "--yes") == (
        f"the proposal {ids['proposal']} is already rejected"
    )
    assert _refused(capsys, "reject", "9999", "--yes") == "event 9999 is no proposal that stands"


@pytest.mark.db
def test_one_approval_does_not_mix_obligations_with_entities(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = _waiting_graph(db, monkeypatch, capsys)
    storage = PostgresStorage(cast("Engine", db))
    (debt,) = _propose(storage, _debt())
    before = len(_standing(db))
    sentence = _refused(capsys, "approve", str(debt), str(ids["proposal"]), "--yes")
    assert sentence == (
        "one call approves obligations and decisions, or entities and relations, not both"
    )
    assert len(_standing(db)) == before
    # The control: each family alone goes through.
    assert main(["approve", str(debt), "--yes"]) == 0
    assert main(["approve", str(ids["proposal"]), "--yes"]) == 0
    assert _refused(capsys, "approve", "9999", "--yes") == "event 9999 is no proposal that stands"
    assert _refused(capsys, "approve", str(ids["proposal"]), "--yes") == (
        f"the proposal {ids['proposal']} is already approved"
    )


@pytest.mark.db
def test_the_graph_commands_carry_the_contractual_help(
    capsys: pytest.CaptureFixture[str],
) -> None:
    sentences = {
        "entity": "state an entity, or show one",
        "relate": "state a relation between two entities",
        "entities": "list the entities",
        "relations": "list the relations",
        "classes": "allow a model to stand for a class of statements",
        "triage": "list what waits for an answer",
        "answer": "answer a question with one of its candidates",
        "status": "show what waits",
    }
    found = {c.name: c.help for c in COMMANDS if c.name in sentences}
    assert found == sentences


@pytest.mark.db
def test_a_first_version_of_an_entity_cannot_be_a_retraction(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Measured red with the guard taken out of `_entity_claim`: the
    command wrote a first version already retracted. The control, the same
    state with `--subject`, stays green then."""
    _graph_log(db, monkeypatch, capsys)
    first = _written(capsys, "entity", "person", "--name", "Anna", "--source", "1")
    before = len(_standing(db))
    sentence = _refused(
        capsys,
        "entity",
        "person",
        "--name",
        "Bert",
        "--source",
        "1",
        "--state",
        "retracted",
        "--yes",
    )
    assert sentence == (
        "--state retracted needs --subject: only an entity that stands can be retracted"
    )
    assert len(_standing(db)) == before
    taken = _written(capsys, "entity", "person", "--subject", str(first), "--state", "retracted")
    assert dict(_standing(db))[taken]["state"] == "retracted"


@pytest.mark.db
def test_entity_retract_is_state_retracted_and_needs_a_subject(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--retract` is `--state retracted`, as `relate --retract` takes a
    relation back. Mutations measured red: `--retract` ignored (the entity
    stays active), the guard for a first version taken out (a retracted
    first version is written), and the exclusion of another state taken out
    (the contradiction is written). The control, `--retract` with `--state
    retracted`, stays green."""
    _graph_log(db, monkeypatch, capsys)
    first = _written(capsys, "entity", "person", "--name", "Anna", "--source", "1")
    before = len(_standing(db))
    assert _refused(
        capsys, "entity", "person", "--name", "Bert", "--source", "1", "--retract", "--yes"
    ) == ("--state retracted needs --subject: only an entity that stands can be retracted")
    assert _refused(
        capsys,
        "entity",
        "person",
        "--subject",
        str(first),
        "--retract",
        "--state",
        "closed",
        "--yes",
    ) == ("--retract and --state closed exclude each other")
    assert _refused(capsys, "entity", str(first), "--retract") == (
        "an id shows an entity; to change one, give its kind and --subject"
    )
    assert len(_standing(db)) == before
    taken = _written(
        capsys, "entity", "person", "--subject", str(first), "--retract", "--state", "retracted"
    )
    assert dict(_standing(db))[taken]["state"] == "retracted"
    assert _run(capsys, "entities") == ""
    second = _written(capsys, "entity", "person", "--name", "Eva", "--source", "1")
    again = _written(capsys, "entity", "person", "--subject", str(second), "--retract")
    assert dict(_standing(db))[again]["state"] == "retracted"


@pytest.mark.db
def test_policy_gaps_names_the_rule_that_would_open_what_was_stated_from_memory(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A recollection has no source event, so no call and no withholding
    reports it; `policy gaps` counts the entities and relations that stand
    on one while no rule `source:recollection` exists. Mutations measured
    red: the count including the retracted entity, the rule not looked at,
    and `--since` not applied. The controls: an entity on a source is not
    counted, and neither is anything once the rule exists."""
    _graph_log(db, monkeypatch, capsys)
    assert _run(capsys, "policy", "gaps") == ""
    anna = _written(capsys, "entity", "person", "--name", "Anna", "--source", "1")
    assert _run(capsys, "policy", "gaps") == ""
    _written(capsys, "entity", "person", "--name", "Eva", "--recollection")
    bert = _written(capsys, "entity", "person", "--name", "Bert", "--recollection")
    _written(capsys, "entity", "person", "--name", "Zoe", "--recollection")
    post = _written(capsys, "entity", "post", "--name", "Treasurer", "--source", "1")
    _written(capsys, "relate", "holds", "--from", str(anna), "--to", str(post), "--recollection")
    gone = _written(capsys, "entity", "person", "--subject", str(bert), "--retract")
    assert gone > bert
    lines = _lines(_run(capsys, "policy", "gaps"))
    assert [(line[0], line[1]) for line in lines] == [("graph:source:recollection", "3")]
    # A later `--since` leaves out what was stated before it.
    assert _run(capsys, "policy", "gaps", "--since", "2999-01-01T00:00:00Z") == ""
    _run(
        capsys,
        "policy",
        "rule",
        "source:recollection",
        "--regions",
        "any",
        "--statement",
        "recollections may go anywhere",
        "--yes",
    )
    assert _run(capsys, "policy", "gaps") == ""


@pytest.mark.db
def test_a_first_version_of_a_relation_cannot_be_a_retraction(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = _vellenfeld_small(db, monkeypatch, capsys)
    before = len(_standing(db))
    sentence = _refused(
        capsys,
        *("relate", "member_of", "--from", str(ids[0]), "--to", str(ids[1])),
        *("--source", "1", "--retract", "--yes"),
    )
    assert sentence == "--retract needs --subject: only a relation that stands can be retracted"
    assert len(_standing(db)) == before
    # The control: with --subject the same flag retracts.
    term = _written(
        capsys, "relate", "member_of", "--from", str(ids[0]), "--to", str(ids[1]), "--source", "1"
    )
    assert _written(capsys, "relate", "member_of", "--subject", str(term), "--retract")


def _vellenfeld_small(
    db: object, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> tuple[int, int]:
    _graph_log(db, monkeypatch, capsys)
    person = _written(capsys, "entity", "person", "--name", "Anna", "--source", "1")
    board = _written(capsys, "entity", "circle", "--name", "Vorstand", "--source", "1")
    return person, board


@pytest.mark.db
def test_approve_sends_a_question_to_answer_and_writes_nothing(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = _waiting_graph(db, monkeypatch, capsys)
    before = len(_standing(db))
    question = ids["question"]
    sentence = _refused(capsys, "approve", str(question), "--yes")
    assert (
        sentence == f"event {question} is a question: answer it with answer {question} --choose ID"
    )
    assert len(_standing(db)) == before
    # The control: answering it, which the sentence names, works.
    assert _written(capsys, "answer", str(question), "--choose", str(ids["circle_a"]))


# --- assignments: relate concerns --from-event ------------------------------------


def _markus(capsys: pytest.CaptureFixture[str]) -> dict[str, int]:
    """Markus's mail, the example of the 2026-10-14 assignments specification, as
    mail 1: its units are about the project XZ, and its last, unit 3, about
    the summer party of the club. Assigned on the command line: the mail to
    XZ, its last unit to the summer party, and the summer party part of the
    club."""
    ids: dict[str, int] = {}
    ids["xz"] = _written(capsys, "entity", "project", "--name", "XZ", "--source", "2")
    ids["club"] = _written(capsys, "entity", "organization", "--name", "Verein", "--source", "2")
    ids["party"] = _written(capsys, "entity", "matter", "--name", "Sommerfest", "--source", "2")
    ids["part_of"] = _written(
        capsys,
        *("relate", "part_of", "--from", str(ids["party"]), "--to", str(ids["club"])),
        *("--source", "2"),
    )
    ids["mail"] = _written(
        capsys, "relate", "concerns", "--from-event", "1", "--to", str(ids["xz"])
    )
    ids["last"] = _written(
        capsys, "relate", "concerns", "--from-event", "1:3", "--to", str(ids["party"])
    )
    return ids


@pytest.mark.db
def test_relate_concerns_assigns_a_mail_and_a_unit_with_the_start_as_their_source(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = _graph_log(db, monkeypatch, capsys)
    ids = _markus(capsys)

    payloads = dict(_standing(db))
    assert payloads[ids["mail"]]["from"] == {"event": 1, "units": None}
    assert payloads[ids["mail"]]["sources"] == [{"event": 1, "units": None}]
    assert payloads[ids["last"]]["from"] == {"event": 1, "units": [3]}
    assert payloads[ids["last"]]["sources"] == [{"event": 1, "units": [3]}]
    assert payloads[ids["last"]]["responsibility"] == "direct"
    lines = _lines(_run(capsys, "relations", "--type", "concerns"))
    assert lines == [
        [str(ids["mail"]), "standing", "concerns", "event 1", f"{ids['xz']} XZ", "-", "1 version"],
        [
            *(str(ids["last"]), "standing", "concerns", "event 1 #3"),
            *(f"{ids['party']} Sommerfest", "-", "1 version"),
        ],
    ]
    with storage.begin() as conn:
        vocabulary = read_vocabulary(storage, conn)
        edges = bracket_edges(read_graph(storage, conn), vocabulary)
    kinds = bracket_kinds(vocabulary)
    assert [members(edges, ids["xz"], kinds).holds(1, seq) for seq in (1, 2, 3)] == [
        True,
        True,
        False,
    ]
    assert [members(edges, ids["party"], kinds).holds(1, seq) for seq in (1, 2, 3)] == [
        False,
        False,
        True,
    ]
    assert [members(edges, ids["club"], kinds).holds(1, seq) for seq in (1, 2, 3)] == [
        False,
        False,
        True,
    ]
    # The page of the project is the project's; its assignments are listed
    # by `relations`, above.
    page = _run(capsys, "entity", str(ids["xz"]))
    assert "concerns" not in page
    assert verify(storage) == []


@pytest.mark.db
def test_relate_concerns_keeps_a_source_that_covers_the_start_and_refuses_one_that_does_not(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A source of another event stands beside the start, which is added;
    one of the same event that covers the start is the start's source; one
    of the same event with fewer units is refused, not merged."""
    _graph_log(db, monkeypatch, capsys)
    xz = str(_written(capsys, "entity", "project", "--name", "XZ", "--source", "2"))
    beside = _written(
        capsys, "relate", "concerns", "--from-event", "1:3", "--to", xz, "--source", "2"
    )
    covered = _written(
        capsys, "relate", "concerns", "--from-event", "1:3", "--to", xz, "--source", "1:2,3"
    )
    payloads = dict(_standing(db))
    assert payloads[beside]["sources"] == [
        {"event": 2, "units": None},
        {"event": 1, "units": [3]},
    ]
    assert payloads[covered]["sources"] == [{"event": 1, "units": [2, 3]}]
    count = len(_standing(db))
    argv = ("relate", "concerns", "--from-event", "1:2,3", "--to", xz, "--source", "1:2", "--yes")
    assert _refused(capsys, *argv) == (
        "a statement has no valid form: the event a relation starts at must be among its sources"
    )
    assert _refused(
        capsys, "relate", "concerns", "--from-event", "1", "--to", xz, "--recollection", "--yes"
    ) == ("a statement has no valid form: the event a relation starts at must be among its sources")
    assert len(_standing(db)) == count


@pytest.mark.db
def test_relate_concerns_refuses_a_start_it_cannot_read_and_one_given_twice(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _graph_log(db, monkeypatch, capsys)
    xz = str(_written(capsys, "entity", "project", "--name", "XZ", "--source", "2"))
    assert _refused(capsys, "relate", "concerns", "--from-event", "1:", "--to", xz, "--yes") == (
        "--from-event is not EVENT or EVENT:SEQ,SEQ: '1:'"
    )
    assert _refused(capsys, "relate", "concerns", "--from-event", "1:9", "--to", xz, "--yes") == (
        "event 1 has no unit 9"
    )
    # A source of the whole mail covers the start, and its unit is checked all the same.
    whole = ("--source", "1", "--yes")
    assert _refused(capsys, "relate", "concerns", "--from-event", "1:9", "--to", xz, *whole) == (
        "event 1 has no unit 9"
    )
    assert _refused(capsys, "relate", "concerns", "--to", xz, "--yes") == (
        "a relation needs --from or --from-event and --source or --recollection "
        "unless --subject names the one to change"
    )
    with pytest.raises(SystemExit) as both:
        main(["relate", "concerns", "--from", xz, "--from-event", "1", "--to", xz])
    assert both.value.code == 2
    assert "not allowed with argument" in capsys.readouterr().err


@pytest.mark.db
def test_an_assignment_is_retracted_and_a_models_question_about_one_is_answered(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = _graph_log(db, monkeypatch, capsys)
    ids = _markus(capsys)
    _written(capsys, "relate", "concerns", "--subject", str(ids["last"]), "--retract")
    listed = _lines(_run(capsys, "relations", "--type", "concerns"))
    assert [line[0] for line in listed] == [str(ids["mail"])]
    payload = dict(_standing(db))[_standing(db)[-1][0]]
    assert (payload["state"], payload["from"]) == ("retracted", {"event": 1, "units": [3]})

    asking = RelationBody(
        "concerns", Source(1, (1,)), None, (ids["xz"], ids["party"]), None, {}, "standing"
    )
    (question,) = _model_writes(storage, _model_claim(RELATION, asking))
    assert _lines(_run(capsys, "triage")) == [
        [
            *("question", str(question), "concerns"),
            f"event 1 #1 -> ? ({ids['xz']} XZ, {ids['party']} Sommerfest)",
            "model:claude-code",
        ],
    ]
    answer = _written(capsys, "answer", str(question), "--choose", str(ids["party"]))
    stands = _lines(_run(capsys, "relations", "--type", "concerns"))
    assert [(line[0], line[3], line[4]) for line in stands] == [
        (str(ids["mail"]), "event 1", f"{ids['xz']} XZ"),
        (str(question), "event 1 #1", f"{ids['party']} Sommerfest"),
    ]
    assert dict(_standing(db))[answer]["approves"] == question
    assert verify(storage) == []


# --- the readers read the graph from its projection -------------------------------


def _listed_history(storage: PostgresStorage, capsys: pytest.CaptureFixture[str]) -> dict[str, int]:
    """Vellenfeld and Markus's mail, and one of every kind of thread the
    listings tell apart: a retracted organization, a relation with a
    period, a class and a person standing under it, a proposal, an
    objection and a question."""
    ids = _markus(capsys)
    ids["vellenfeld"] = _written(
        capsys, "entity", "organization", "--name", _VELLENFELD, "--source", "2"
    )
    ids["anna"] = _written(capsys, "entity", "person", "--name", "Anna", "--source", "1")
    ids["involved"] = _written(
        capsys,
        *("relate", "involved_in", "--from", str(ids["anna"]), "--to", str(ids["xz"])),
        *("--from-date", "2026-01-01", "--source", "1"),
    )
    _written(capsys, "entity", "organization", "--subject", str(ids["vellenfeld"]), "--retract")
    ids["class"] = _written(
        capsys,
        *("classes", "add", "maier", "--author", "model:claude-code", "--assertion", "entity"),
        *("--type", "person", "--threshold", "80", "--statement", "names from mails"),
    )
    ids["through"] = _model_person(storage, "Clara", confidence=90)
    ids["proposal"] = _model_person(storage, "Dora", confidence=40)
    ids["objection"] = _model_person(storage, "Anna Maier", subject=ids["anna"], confidence=40)
    asking = RelationBody(
        "concerns", Source(1, (1,)), None, (ids["xz"], ids["party"]), None, {}, "standing"
    )
    (ids["question"],) = _model_writes(storage, _model_claim(RELATION, asking))
    return ids


def _fold_instead(log: PostgresStorage, store: PostgresStorage, conn: Connection) -> Graph:
    """What the readers read before the projection: the fold of the log."""
    del store
    return read_graph(log, conn)


@pytest.mark.db
def test_the_listings_read_from_the_projection_are_those_the_fold_gives(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every listing of the graph shows from the projection what it showed
    when it folded the log ({ref}`graph-projection`). The oracle is the
    fold: the same commands with the reader swapped back."""
    storage = _graph_log(db, monkeypatch, capsys)
    ids = _listed_history(storage, capsys)
    commands = [
        ["entities"],
        ["entities", "--proposals"],
        ["entities", "--state", "retracted"],
        ["entities", "--type", "person"],
        ["relations"],
        ["relations", "--type", "concerns"],
        ["relations", "--at", "2025-12-31"],
        ["relations", "--to", str(ids["xz"])],
        ["relations", "--from", str(ids["party"])],
        ["entity", str(ids["xz"])],
        ["entity", str(ids["anna"])],
        ["entity", str(ids["anna"]), "--history"],
        ["entity", str(ids["vellenfeld"])],
        ["triage"],
        ["status"],
        ["classes", "list"],
        ["classes", "sample", "maier", "--count", "50"],
    ]
    projected = [_run(capsys, *command) for command in commands]
    monkeypatch.setattr("previously.cli.projected_graph", _fold_instead)
    folded = [_run(capsys, *command) for command in commands]
    assert projected == folded
    # Every listing has something to show, so that agreeing is not
    # agreeing on nothing.
    assert all(projected)
    assert _lines(projected[-4]) == [
        ["objection", str(ids["objection"]), "Person", "Anna Maier", "model:claude-code"],
        [
            *("question", str(ids["question"]), "concerns"),
            f"event 1 #1 -> ? ({ids['xz']} XZ, {ids['party']} Sommerfest)",
            "model:claude-code",
        ],
        ["proposal", str(ids["proposal"]), "Person", "Dora", "model:claude-code"],
    ]
    assert _lines(projected[-3]) == [["objections", "1"], ["questions", "1"], ["proposals", "1"]]
    assert projected[-1].startswith(f"{ids['through']}\t")


@pytest.mark.db
def test_a_listing_catches_the_projection_up_before_it_reads(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nothing but the listing itself catches up here: the writes go
    through `core`, past the command line, and nobody runs `project`."""
    storage = _graph_log(db, monkeypatch, capsys)
    assert _run(capsys, "status") == "objections\t0\nquestions\t0\nproposals\t0\n"
    assert _run(capsys, "entities") == ""
    first = _model_person(storage, "Dora", confidence=40)
    assert _run(capsys, "status") == "objections\t0\nquestions\t0\nproposals\t1\n"
    assert _lines(_run(capsys, "entities", "--proposals")) == [
        [str(first), "proposed active", "Person", "Dora", "1 version", "0 proposals"]
    ]
    assert _lines(_run(capsys, "triage"))[0][:2] == ["proposal", str(first)]
    assert capsys.readouterr().err == ""


@pytest.mark.db
def test_project_check_is_clean_after_a_history_and_names_each_row_falsified_by_hand(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--check` holds every row of `p_graph_thread` against the fold of the
    log and writes nothing beyond the catch-up: a row changed by hand is
    named on every run, until a rebuild writes it again."""
    from sqlalchemy import Engine
    from sqlalchemy import text

    storage = _graph_log(db, monkeypatch, capsys)
    ids = _listed_history(storage, capsys)
    redact_event(storage, storage, ids["proposal"], reason="wrong", recorded_at=_ASSERT_AT)
    clean = _run(capsys, "project", "--check")
    assert [line.split()[0] for line in clean.splitlines()] == [
        "chronicle",
        "source-stats",
        "graph",
    ]
    assert isinstance(db, Engine)
    with db.begin() as c:
        c.execute(
            text("UPDATE p_graph_thread SET objections = 2 WHERE subject = :s"), {"s": ids["xz"]}
        )
        c.execute(text("DELETE FROM p_graph_thread WHERE subject = :s"), {"s": ids["club"]})
        c.execute(
            text("UPDATE p_graph_thread SET level = 'open', pending = 4 WHERE subject = :s"),
            {"s": ids["mail"]},
        )
        # The version rows the readers fold a thread from: one missing, one
        # extra, on a mail, and one under a class it was never written under.
        c.execute(text("DELETE FROM p_graph_version WHERE id = :s"), {"s": ids["part_of"]})
        c.execute(text("INSERT INTO p_graph_version VALUES (2, 2, 'entity', NULL)"))
        c.execute(
            text("UPDATE p_graph_version SET under = :c WHERE id = :s"),
            {"c": ids["class"], "s": ids["anna"]},
        )
    falsified = [
        f"graph\t{ids['xz']}\tobjections 2 instead of 0",
        f"graph\t{ids['club']}\tno row instead of winner {ids['club']}",
        f"graph\t{ids['mail']}\tlevel open instead of direct, pending 4 instead of 0",
        "graph\t2\tversion row entity of 2 instead of none",
        f"graph\t{ids['part_of']}\tno version row instead of relation of {ids['part_of']}",
        f"graph\t{ids['anna']}\tversion row under {ids['class']} instead of -",
    ]
    for _run_again in (1, 2):
        out = _run(capsys, "project", "--check", code=1)
        assert out.splitlines()[3:] == falsified
        assert capsys.readouterr().err == ""
    # The control: without `--check`, `project` says nothing of it.
    assert len(_run(capsys, "project").splitlines()) == 3
    with storage.begin() as conn:
        storage.truncate_projection(conn, "graph")
        conn.execute(text("DELETE FROM projection_state WHERE name = 'graph'"))
    rebuilt = _run(capsys, "project", "--check")
    assert rebuilt.splitlines()[2].startswith("graph           built:")
    assert len(rebuilt.splitlines()) == 3


def _expected_listings(capsys: pytest.CaptureFixture[str]) -> list[str]:
    return [_run(capsys, *command) for command in (["entities"], ["triage"], ["status"])]


@pytest.mark.db
def test_a_listing_folds_the_log_when_the_projection_was_rebuilt_since_its_catch_up(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Another version of the code, or a forced rebuild, empties the
    projection between a reader's catch-up and its snapshot: the reader
    finds the state row at another version, says so on standard error and
    shows the fold, never the empty tables ({ref}`graph-readers`)."""
    from sqlalchemy import Engine
    from sqlalchemy import text

    storage = _graph_log(db, monkeypatch, capsys)
    _listed_history(storage, capsys)
    expected = _expected_listings(capsys)
    assert all(expected)
    assert isinstance(db, Engine)

    def rebuilt_after(
        log: PostgresStorage, store: PostgresStorage, projection: Projection
    ) -> Outcome:
        outcome = catch_up(log, store, projection)
        with db.begin() as c:
            c.execute(text("UPDATE projection_state SET version = 7 WHERE name = 'graph'"))
            c.execute(text("DELETE FROM p_graph_thread"))
            c.execute(text("DELETE FROM p_graph_version"))
        return outcome

    monkeypatch.setattr("previously.cli.catch_up", rebuilt_after)
    for command, shown in zip((["entities"], ["triage"], ["status"]), expected, strict=True):
        assert main(command) == 0
        captured = capsys.readouterr()
        assert captured.out == shown
        assert captured.err == (
            "the graph projection was rebuilt since this command caught it up; "
            "this command folds the log instead\n"
        )


@pytest.mark.db
def test_a_listing_folds_the_log_when_its_catch_up_fails(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A catch-up stopped by another version of the code rebuilding the
    projection fails no listing: one line on standard error, and the
    fold."""
    storage = _graph_log(db, monkeypatch, capsys)
    _listed_history(storage, capsys)
    expected = _expected_listings(capsys)
    stopped = "projection graph was rebuilt while this catch-up ran"

    def failing(log: PostgresStorage, store: PostgresStorage, projection: Projection) -> Outcome:
        del log, store, projection
        raise ProjectionRebuilt(stopped)

    monkeypatch.setattr("previously.cli.catch_up", failing)
    for command, shown in zip((["entities"], ["triage"], ["status"]), expected, strict=True):
        assert main(command) == 0
        captured = capsys.readouterr()
        assert captured.out == shown
        assert captured.err == (
            f"the graph projection could not be caught up ({stopped}); "
            "this command folds the log instead\n"
        )


class _GapAboveTheProjection(PostgresStorage):
    """The real store, whose log has a gap where a catch-up reads: a read of
    more than one event leaves out the first one asked for, so `catch_up`
    refuses with `ProjectionGap`. A read of one event finds it."""

    def read(self, conn: Connection, from_id: int, limit: int) -> Iterator[EventRow]:
        found = super().read(conn, from_id, limit)
        return found if limit == 1 else (row for row in found if row.id != from_id)


@pytest.mark.db
def test_a_listing_folds_the_log_when_its_catch_up_meets_a_gap_in_the_log(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A gap above where the projection stands, which `catch_up` refuses
    with `ProjectionGap`, fails no listing either: the fold reads the log
    whole and needs no projection, so the reader says so in one line on
    standard error and shows the fold ({ref}`graph-readers`)."""
    from sqlalchemy import Engine
    from sqlalchemy import text

    storage = _graph_log(db, monkeypatch, capsys)
    _listed_history(storage, capsys)
    expected = _expected_listings(capsys)
    assert isinstance(db, Engine)
    # The projection has to be built again, as after an upgrade, so that
    # the catch-up reads a batch of many events, and meets the gap there.
    with db.begin() as c:
        c.execute(text("DELETE FROM projection_state WHERE name = 'graph'"))
    gapped = _GapAboveTheProjection(db)

    def through_the_gap(
        log: PostgresStorage, store: PostgresStorage, projection: Projection
    ) -> Outcome:
        del log
        return catch_up(gapped, store, projection)

    monkeypatch.setattr("previously.cli.catch_up", through_the_gap)
    for command, shown in zip((["entities"], ["triage"], ["status"]), expected, strict=True):
        assert main(command) == 0, capsys.readouterr().err
        captured = capsys.readouterr()
        assert captured.out == shown
        assert captured.err.startswith(
            "the graph projection could not be caught up (expected events 1.. "
        )
        assert captured.err.endswith("); this command folds the log instead\n")
        assert captured.err.count("\n") == 1


# --- the chronicle of a bracket: chronicle --within ---------------------------------

_MAIL_1 = "2026-10-30T09:00:00+00:00\temail\tm1"


def _within(capsys: pytest.CaptureFixture[str], bracket: int, *argv: str) -> list[str]:
    """The lines of `chronicle --within bracket`, which has to say nothing
    on standard error."""
    out = _run(capsys, "chronicle", "--within", str(bracket), *argv)
    assert capsys.readouterr().err == ""
    return out.splitlines()


@pytest.mark.db
def test_chronicle_within_shows_the_units_of_a_bracket_and_one_level_up_those_of_the_club(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Markus, point 2 of the acceptance of the 2026-10-14 assignments
    specification: mail 1 is about the project XZ, its last unit about the
    summer party, and the summer party is part of the club. The chronicle
    of the summer party holds the last unit, so does the club's, one level
    up, and the project's holds the others: the more specific replaces the
    general."""
    storage = _graph_log(db, monkeypatch, capsys)
    ids = _markus(capsys)
    _run(capsys, "project")

    assert _within(capsys, ids["party"]) == [f"1\t3\t{_MAIL_1}\tThree."]
    assert _within(capsys, ids["club"]) == [f"1\t3\t{_MAIL_1}\tThree."]
    assert _within(capsys, ids["xz"]) == [f"1\t1\t{_MAIL_1}\tOne.", f"1\t2\t{_MAIL_1}\tTwo."]
    # The control: the whole chronicle holds both mails, the second of
    # which belongs to no bracket.
    assert len(_run(capsys, "chronicle").splitlines()) == 6

    # A unit assigned on its own after `project`: the reader catches the
    # graph up and finds it, and says that the chronicle itself stands one
    # event behind, as `chronicle` does.
    _written(capsys, "relate", "concerns", "--from-event", "1:2", "--to", str(ids["party"]))
    assert main(["chronicle", "--within", str(ids["party"])]) == 0
    assert capsys.readouterr() == (
        f"1\t2\t{_MAIL_1}\tTwo.\n1\t3\t{_MAIL_1}\tThree.\n",
        "projection is 1 event behind; run `previously project`\n",
    )
    _run(capsys, "project")
    assert _within(capsys, ids["xz"]) == [f"1\t1\t{_MAIL_1}\tOne."]

    # An erased unit takes its assignments with it, and an assignment of
    # the whole mail falls with it too (ruling T2-b of the 2026-10-15
    # assignments plan): what is left is the unit assigned on its own.
    _run(capsys, "redact", "units", "1", "3", "--reason", "wrong")
    assert _within(capsys, ids["party"]) == [f"1\t2\t{_MAIL_1}\tTwo."]
    assert _within(capsys, ids["xz"]) == []
    assert verify(storage) == []


def _observation_at(storage: PostgresStorage, name: str, day: int) -> int:
    """An observation with one unit, `name`, on day `day` of October 2026."""
    _append("email", name, name, f"2026-10-{day:02d}T09:00:00Z")
    with storage.begin() as conn:
        tip = storage.tip(conn)
    assert tip is not None
    return tip.id


@pytest.mark.db
def test_chronicle_within_counts_its_limit_and_its_window_among_the_units_of_the_bracket(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A unit outside the bracket takes no place under `--limit`: the
    selection is made in the query, before the limit, so that the notice of
    a cut says what it says without `--within`."""
    storage = _graph_log(db, monkeypatch, capsys)
    days = {name: _observation_at(storage, name, day) for day, name in enumerate("ABCD", 1)}
    project = _written(capsys, "entity", "project", "--name", "P", "--source", "2")
    for name in "ACD":
        _written(
            capsys, "relate", "concerns", "--from-event", str(days[name]), "--to", str(project)
        )
    _run(capsys, "project")

    def line(name: str) -> str:
        day = "ABCD".index(name) + 1
        return f"{days[name]}\t1\t2026-10-{day:02d}T09:00:00+00:00\temail\t{name}\t{name}"

    assert _within(capsys, project) == [line("A"), line("C"), line("D")]
    assert _within(capsys, project, "--limit", "3") == [line("A"), line("C"), line("D")]
    assert main(["chronicle", "--within", str(project), "--limit", "2"]) == 0
    assert capsys.readouterr() == (
        f"{line('A')}\n{line('C')}\n",
        "output truncated at 2 lines; raise --limit or narrow --since/--until\n",
    )
    window = ("--since", "2026-10-02T00:00:00Z", "--until", "2026-10-04T00:00:00Z")
    assert _within(capsys, project, *window) == [line("C")]
    # The control: without `--within` the same window holds B as well.
    assert len(_run(capsys, "chronicle", *window).splitlines()) == 2


@pytest.mark.db
def test_chronicle_within_refuses_what_is_not_an_entity_that_stands_and_shows_an_empty_one(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _graph_log(db, monkeypatch, capsys)
    ids = _markus(capsys)
    gone = _written(capsys, "entity", "project", "--name", "Alt", "--source", "2")
    _written(capsys, "entity", "project", "--subject", str(gone), "--retract")
    empty = _written(capsys, "entity", "project", "--name", "Leer", "--source", "2")
    _run(capsys, "project")

    # Nothing at that id, a relation, a mail, a retracted entity, and an
    # id no event can have.
    for bracket in (999_999, ids["part_of"], 1, gone, 0):
        assert _refused(capsys, "chronicle", "--within", str(bracket)) == (
            f"--within {bracket} is not an entity that stands"
        )
    # The control: an entity nothing is assigned to has an empty chronicle.
    assert _within(capsys, empty) == []


@pytest.mark.db
def test_chronicle_within_finds_from_the_projection_what_the_fold_finds(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The oracle is the fold, as for the listings: the same commands with
    the reader swapped back. The history holds an open proposal of a unit
    of its own, which adds the unit to the summer party and takes it from
    nothing (ruling T2-c of the 2026-10-15 assignments plan), and a question,
    which points at no bracket yet."""
    storage = _graph_log(db, monkeypatch, capsys)
    ids = _listed_history(storage, capsys)
    proposal = RelationBody("concerns", Source(1, (1,)), ids["party"], None, None, {}, "standing")
    _model_writes(storage, _model_claim(RELATION, proposal, confidence=40))
    _run(capsys, "project")
    brackets = [ids[name] for name in ("party", "club", "xz", "anna")]
    projected = [_within(capsys, bracket) for bracket in brackets]
    monkeypatch.setattr("previously.cli.projected_graph", _fold_instead)
    folded = [_within(capsys, bracket) for bracket in brackets]
    assert projected == folded
    assert projected == [
        [f"1\t1\t{_MAIL_1}\tOne.", f"1\t3\t{_MAIL_1}\tThree."],
        [f"1\t1\t{_MAIL_1}\tOne.", f"1\t3\t{_MAIL_1}\tThree."],
        [f"1\t1\t{_MAIL_1}\tOne.", f"1\t2\t{_MAIL_1}\tTwo."],
        [],
    ]


@pytest.mark.db
@pytest.mark.parametrize("cause", ["rebuilt", "failed"])
def test_chronicle_within_folds_the_log_when_the_projection_does_not_stand(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, cause: str
) -> None:
    """Ruling T4-b of the 2026-10-15 assignments plan: a rebuild between the
    catch-up and the snapshot, or a catch-up that fails, costs a fold and
    one line on standard error, never an empty chronicle."""
    from sqlalchemy import Engine
    from sqlalchemy import text

    _graph_log(db, monkeypatch, capsys)
    ids = _markus(capsys)
    _run(capsys, "project")
    expected = _within(capsys, ids["club"])
    assert expected
    assert isinstance(db, Engine)
    stopped = "projection graph was rebuilt while this catch-up ran"

    def rebuilt_after(
        log: PostgresStorage, store: PostgresStorage, projection: Projection
    ) -> Outcome:
        outcome = catch_up(log, store, projection)
        with db.begin() as c:
            c.execute(text("UPDATE projection_state SET version = 7 WHERE name = 'graph'"))
            c.execute(text("DELETE FROM p_graph_thread"))
            c.execute(text("DELETE FROM p_graph_version"))
        return outcome

    def failing(log: PostgresStorage, store: PostgresStorage, projection: Projection) -> Outcome:
        del log, store, projection
        raise ProjectionRebuilt(stopped)

    monkeypatch.setattr("previously.cli.catch_up", rebuilt_after if cause == "rebuilt" else failing)
    assert main(["chronicle", "--within", str(ids["club"])]) == 0
    captured = capsys.readouterr()
    assert captured.out.splitlines() == expected
    warning = (
        "the graph projection was rebuilt since this command caught it up"
        if cause == "rebuilt"
        else f"the graph projection could not be caught up ({stopped})"
    )
    assert captured.err == f"{warning}; this command folds the log instead\n"
