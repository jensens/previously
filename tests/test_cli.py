# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from datetime import UTC
from previously.cli import main
from previously.cli import MAX_TEXT_BYTES
from previously.cli import parse_moment
from previously.core.errors import InvalidPayload

import pytest


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
    the fact (§5.1), so a surface that can set it but not read it back is the
    wrong half. The payload goes with it: `show` was the only command that
    could display it at all, and it did not.
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
    """The tombstone has neither payload nor kind of evidence (§4.6 of the
    architecture). `show` has to say that rather than print an empty line —
    and it must not crash on `None`, which is the branch a plain
    `payload.get(...)` would have fallen into."""
    from sqlalchemy import Engine
    from sqlalchemy import text

    assert isinstance(db, Engine)
    monkeypatch.setenv("PREVIOUSLY_DSN", db.url.render_as_string(hide_password=False))
    assert main(["append", "--source", "cli", "--external-id", "a", "--text", "Hello"]) == 0
    capsys.readouterr()
    with db.begin() as c:
        c.execute(text("UPDATE event SET payload = NULL WHERE id = 1"))

    assert main(["show", "1"]) == 0
    output = capsys.readouterr().out
    assert "payload=<erased>" in output
    assert "evidence=" not in output


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
    `test_storage.py`."""
    monkeypatch.setenv("PREVIOUSLY_DSN", "postgresql+psycopg://user:SECRET123@localhost:1/db")
    assert main(["log"]) == 2
    sentence = _single_line(capsys.readouterr().err)
    assert "Traceback" not in sentence
    assert "SECRET123" not in sentence


@pytest.mark.db
def test_a_missing_table_shows_one_sentence(
    unmigrated_engine: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Case 3 out of review finding W2: `log` before `alembic upgrade head`."""
    from sqlalchemy import Engine

    assert isinstance(unmigrated_engine, Engine)
    monkeypatch.setenv(
        "PREVIOUSLY_DSN", unmigrated_engine.url.render_as_string(hide_password=False)
    )
    assert main(["log"]) == 2
    sentence = _single_line(capsys.readouterr().err)
    assert "Traceback" not in sentence
    assert "alembic upgrade head" in sentence


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
    # standing (§5.1) and the finding is the one this test is about — the same
    # reasoning as in `test_p5`, and `CAST(... AS jsonb)` for the same reason
    # as well, see the comment there.
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
    `external_id` are checked in `core.append` now, because §3.2's
    canonicalisation would decide about them only inside `event_hash`, that is
    **after** `storage.lookup` has carried them into the driver. The text was
    already covered by `payload_hash`; what crashed for it was `cli.py`'s size
    check.
    """
    monkeypatch.setenv("PREVIOUSLY_DSN", "postgresql+psycopg://unused/unused")
    argv = ["append", "--source", "cli", "--external-id", "x1", "--text", "hello"]
    argv[argv.index(field) + 1] = f"value{probe}"

    assert main(argv) == 2
    sentence = _single_line(capsys.readouterr().err)
    assert "Traceback" not in sentence
    assert expected in sentence
