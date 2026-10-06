# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
from contextlib import contextmanager
from datetime import datetime
from datetime import UTC
from previously.cli import COMMANDS
from previously.cli import escape_field
from previously.cli import main
from previously.cli import MAX_TEXT_BYTES
from previously.cli import media_type_of
from previously.cli import parse_moment
from previously.contract.rows import EventRow
from previously.contract.rows import ProjectionState
from previously.contract.rows import UnitRow
from previously.contract.types import BlobRef
from previously.contract.types import Evidence
from previously.contract.types import RawEvent
from previously.core.append import append
from previously.core.errors import InvalidPayload
from previously.core.identity import artifact_hash_of
from previously.core.projection import catch_up
from previously.core.projection import CHRONICLE
from previously.core.redact import redact_blob
from previously.core.redact import redact_event
from previously.core.sealing import recipient_of
from previously.core.sealing import seal
from previously.core.units import split_plaintext
from previously.storage.postgres import PostgresStorage
from typing import TYPE_CHECKING

import hashlib
import io
import os
import pytest
import re
import secrets
import sys
import threading
import time


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Generator
    from collections.abc import Sequence
    from previously.contract.blobs import ClosableSource
    from previously.contract.blobs import StoredBlob
    from previously.storage.s3 import S3BlobStore
    from sqlalchemy import Connection
    from sqlalchemy import Engine
    from sqlalchemy import URL
    from typing import IO

    import pathlib


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
    ]

    with db.begin() as c:
        c.execute(text("UPDATE projection_state SET version = 3 WHERE name = 'chronicle'"))
    assert main(["project"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "chronicle       rebuilt: version 3 -> 2, 0 events, up_to_id 0",
        "source-stats    up to date, up_to_id 0",
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
    ]

    _append("email", "m2", "Again", "2026-10-02T09:00:00Z")
    capsys.readouterr()
    assert main(["project"]) == 0
    second = capsys.readouterr().out.splitlines()
    assert second == [
        "chronicle       caught up: 1 event, up_to_id 2",
        "source-stats    caught up: 1 event, up_to_id 2",
    ]

    assert main(["project"]) == 0
    third = capsys.readouterr().out.splitlines()
    assert third == [
        "chronicle       up to date, up_to_id 2",
        "source-stats    up to date, up_to_id 2",
    ]

    # The fourth path, and the only one invisible in the table itself: the
    # stored version is raised past the one the code declares, the way a
    # rolled-back release leaves it, and the next run empties `p_chronicle` and
    # builds it again. Without this line `rebuilt:` would be a format the
    # reference page promises and nothing produces. `source-stats` is left
    # alone, so the two projections report different paths in the same run.
    with db.begin() as c:
        c.execute(text("UPDATE projection_state SET version = 3 WHERE name = 'chronicle'"))
    capsys.readouterr()
    assert main(["project"]) == 0
    fourth = capsys.readouterr().out.splitlines()
    assert fourth == [
        "chronicle       rebuilt: version 3 -> 2, 2 events, up_to_id 2",
        "source-stats    up to date, up_to_id 2",
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
    # builds both projections and says so on standard error.
    assert main(["redact", "event", "1", "--reason", "wrong recipient"]) == 0
    out, err = capsys.readouterr()
    assert (out, err) == (
        "redacted by event 2\n",
        "chronicle       built: 2 events, up_to_id 2\n"
        "source-stats    built: 2 events, up_to_id 2\n",
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
        "source-stats    built: 3 events, up_to_id 3\n",
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
        "chronicle       rebuilt: version 1 -> 2, 2 events, up_to_id 2\n",
    )
    assert main(["project"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "chronicle       up to date, up_to_id 2",
        "source-stats    up to date, up_to_id 2",
    ]


@pytest.mark.db
def test_project_rebuilds_a_chronicle_built_at_version_1(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Version 1 of the chronicle did not read redactions, so a table it built
    can still hold the rows of an erased event. The state row is set to what
    such a table carries — version 1, caught up past the redaction — and the
    first `project` of version 2 rebuilds it and says so."""
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
        "chronicle       rebuilt: version 1 -> 2, 3 events, up_to_id 3"
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
        "source-stats    built: 4 events, up_to_id 4\n" + _stays(shared_address, 2, 3),
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
