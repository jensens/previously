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
from previously.contract.rows import UnitRow
from previously.contract.types import BlobRef
from previously.contract.types import Evidence
from previously.contract.types import RawEvent
from previously.core.append import append
from previously.core.errors import InvalidPayload
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
import sys
import time


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Generator
    from collections.abc import Sequence
    from previously.storage.s3 import S3BlobStore
    from sqlalchemy import Engine

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
    # stable: jsonb does not give the keys back in the order written.
    assert 'payload={"evidence": "verbatim", "text": "Hello"}' in output


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
    assert main(["verify"]) == 2
    assert _single_line(capsys.readouterr().err) == sentence


@pytest.mark.db
def test_a_missing_table_shows_one_sentence(
    unmigrated_engine: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Case 3 out of review finding W2: `log` before `alembic upgrade head`.

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
    assert "alembic upgrade head" in sentence
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
        ("--text", "\ud800", "$.text: string not representable as UTF-8"),
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


@pytest.mark.db
def test_redact_units_names_each_tombstone(
    db: object, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each erased unit names the redaction that ordered it, and the payload
    and the unit left standing print as before."""
    _connect(db, monkeypatch)
    text_ = "One\n\nTwo\n\nThree"
    assert main(["append", "--source", "cli", "--external-id", "a", "--text", text_]) == 0
    assert main(["redact", "units", "1", "3", "--reason", "r"]) == 0
    assert main(["redact", "units", "1", "1", "3", "--reason", "r"]) == 0
    out, err = capsys.readouterr()
    assert out == "1\nredacted by event 2\nredacted by event 3\n"
    # The first `redact` builds the projections, which nobody had built; the
    # second only catches up and says nothing about it.
    assert err == (
        "chronicle       built: 2 events, up_to_id 2\n"
        "source-stats    built: 2 events, up_to_id 2\n"
        "unit 3 was already erased\n"
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
    """The redaction is written and the catch-up fails: one line on standard
    output, as for a call that finished, and the error says what stands and
    what does not. The failure is a gap in the log, forged with plain SQL the
    way `test_projection_worker` forges it — nothing in the write paths can
    produce one, which makes it a failure no wrapper has to stand in for."""
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
    assert out == "redacted by event 4\n"
    assert err == (
        "Error: the redaction is recorded as event 4, but it is not finished: "
        "projection chronicle is not caught up (expected events 2.. above id 1, "
        "read [3, 4]; the tip is 4); run the same command again\n"
    )


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


@pytest.mark.parametrize("address", ["A" * 64, "a" * 63], ids=["upper-case", "63-characters"])
def test_a_blob_address_that_is_not_one_is_an_input_error(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    address: str,
) -> None:
    """Review focus 6 of the 2026-10-04 stage 1c plan. Refused before
    anything is asked: there is no database and no blob setting, and the
    sentence is still about the address."""
    monkeypatch.setenv("PREVIOUSLY_DSN", "postgresql+psycopg://user:pw@localhost:1/db")
    for name in _BLOB_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    target = tmp_path / "out.bin"
    assert main(["blob", "get", address, "--output", str(target)]) == 2
    assert _single_line(capsys.readouterr().err) == (
        f"Error: {address} is not a blob address: 64 hexadecimal characters, lower case"
    )
    assert not target.exists()


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
def test_blob_get_whose_output_cannot_be_written_leaves_nothing(
    blobs: _Blobs, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Ruling T6-c of the 2026-10-04 stage 1c plan: the temporary output
    fills up while the content passes into it — a file size limit below
    the blob's size, for real. One sentence, exit code 2, no target, and no
    temporary file; `fetch_blob` returns no size for bytes that never
    arrived."""
    content = os.urandom(_LARGE)
    assert main(_attach("a", _file(tmp_path, "large.bin", content))) == 0
    capsys.readouterr()
    directory = tmp_path / "out"
    directory.mkdir()
    target = directory / "large.bin"
    with _file_size_limit(_LIMIT):
        code = main(["blob", "get", hashlib.sha256(content).hexdigest(), "--output", str(target)])
    out, err = capsys.readouterr()
    assert code == 2
    assert out == ""
    assert _single_line(err) == f"Error: cannot write {target}: File too large"
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
    6 it left `main` as a `ValueError` traceback."""
    monkeypatch.setenv("PREVIOUSLY_BLOB_ENDPOINT", "localhost:9000")
    if command == "append":
        argv = _attach("a", _file(tmp_path, "a.txt", b"an attachment"))
    else:
        argv = ["blob", "get", "c" * 64, "--output", str(tmp_path / "out.bin")]
    assert main(argv) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert _single_line(err).startswith(
        "Error: the settings for the blob store at localhost:9000, bucket "
    )
    assert err.rstrip().endswith("are not usable: ValueError")
    assert blobs.secret not in out + err
    assert _events(blobs.engine) == 0


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
