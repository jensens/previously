# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The access log: `mcp_access` written, read, form-checked and counted."""

from datetime import datetime
from datetime import timedelta
from datetime import UTC
from previously.cli import main
from previously.contract.types import Evidence
from previously.contract.types import RawEvent
from previously.contract.types import RawUnit
from previously.core.access import Access
from previously.core.access import Delivered
from previously.core.access import read_access
from previously.core.access import record_access
from previously.core.access import Withheld
from previously.core.action import append_action
from previously.core.action import KNOWN_ACTIONS
from previously.core.append import append
from previously.core.gaps import Gap
from previously.core.gaps import gaps
from previously.core.projection.chronicle import CHRONICLE
from previously.core.projection.worker import catch_up
from previously.core.units import split_plaintext
from previously.core.verify import verify
from previously.storage.postgres import PostgresStorage
from sqlalchemy import Engine
from sqlalchemy import text
from typing import cast

import pytest


T0 = datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)
T2 = T0 + timedelta(hours=2)

MAIL_TEXT = "Dear Mr Hofer,\n\nthe invoice 4711 of the Danube project is overdue."


def _mail(storage: PostgresStorage) -> int:
    (event_id,) = append(
        storage,
        [
            RawEvent(
                source="email",
                external_id="m-1",
                occurred_at=T0,
                evidence=Evidence.VERBATIM,
                units=split_plaintext(MAIL_TEXT),
                payload={"text": MAIL_TEXT},
            )
        ],
        recorded_at=T0,
    )
    return event_id


def _access(
    *,
    client: str = "claude-code",
    name: str = "previously",
    arguments: dict[str, object] | None = None,
    delivered: tuple[Delivered, ...] = (),
    withheld: tuple[Withheld, ...] = (),
    outcome: str = "ok",
) -> Access:
    return Access(
        client=client,
        policy_ids={"client": 31, "processor": 12, "rules": [19]},
        kind="tool",
        name=name,
        arguments=arguments if arguments is not None else {"circle": "h_da"},
        delivered=delivered,
        withheld=withheld,
        outcome=outcome,
        era="2026-07-28",
    )


def _no_rule(event: int, *circles: str) -> Withheld:
    """A withholding for lack of a rule, where every circle of the event is
    one without a rule."""
    reason = f"circle {circles[0]} has no rule for this client"
    return Withheld(event, "no_rule", circles, reason, circles, "email")


def _strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        entries = cast("dict[str, object]", value)
        return [s for key, item in entries.items() for s in (key, *_strings(item))]
    if isinstance(value, list):
        return [s for item in cast("list[object]", value) for s in _strings(item)]
    return []


def _payloads(db: Engine) -> list[dict[str, object]]:
    with db.begin() as conn:
        rows = conn.execute(
            text("SELECT payload FROM event WHERE kind = 'action' ORDER BY id")
        ).scalars()
        return [cast("dict[str, object]", row) for row in rows]


def test_mcp_access_is_a_known_action() -> None:
    assert "mcp_access" in KNOWN_ACTIONS


@pytest.mark.db
def test_an_access_is_written_and_read_back(db: Engine) -> None:
    storage = PostgresStorage(db)
    written = _access(
        delivered=(Delivered(42, (1, 2), ()),),
        withheld=(_no_rule(43, "h_da"),),
    )
    event_id = record_access(storage, written, recorded_at=T1)
    with storage.begin() as conn:
        (row,) = read_access(storage, conn, client=None, circle=None, since=None)
    assert (row.id, row.recorded_at, row.access) == (event_id, T1, written)
    assert verify(storage) == []


@pytest.mark.db
def test_reading_narrows_by_client_circle_and_time(db: Engine) -> None:
    storage = PostgresStorage(db)
    record_access(storage, _access(client="a", arguments={"circle": "h_da"}), recorded_at=T0)
    record_access(storage, _access(client="b", arguments={"circle": "xz"}), recorded_at=T1)
    record_access(
        storage,
        _access(client="b", arguments={"ids": [5]}, withheld=(_no_rule(5, "h_da", "xz"),)),
        recorded_at=T2,
    )

    def ids(
        client: str | None = None, circle: str | None = None, since: datetime | None = None
    ) -> list[int]:
        with storage.begin() as conn:
            rows = read_access(storage, conn, client=client, circle=circle, since=since)
        return [row.id for row in rows]

    assert ids() == [1, 2, 3]
    assert ids(client="b") == [2, 3]
    assert ids(circle="h_da") == [1, 3]  # named in the arguments, and withheld
    assert ids(circle="xz") == [2, 3]
    assert ids(since=T1) == [2, 3]
    assert ids(client="b", circle="h_da", since=T1) == [3]
    assert ids(client="nobody") == []


def _wordings() -> list[str]:
    return [
        MAIL_TEXT,
        *(line.strip() for line in MAIL_TEXT.splitlines() if len(line.strip()) >= 8),
        "Hofer",
        "4711",
    ]


def _found_in(payload: dict[str, object]) -> list[tuple[str, str]]:
    """Every wording of the mail, with the string of the payload it stands in."""
    return [(w, s) for s in _strings(payload) for w in _wordings() if w in s]


@pytest.mark.db
def test_a_delivered_event_of_a_circle_is_found_by_that_circle(db: Engine) -> None:
    """A `get_event` by id names no circle in its arguments; the circles of
    the event it delivered still find it."""
    storage = PostgresStorage(db)
    record_access(
        storage,
        _access(
            name="get_event",
            arguments={"ids": [5]},
            delivered=(Delivered(5, (1,), ("xz",)),),
        ),
        recorded_at=T0,
    )
    record_access(
        storage,
        _access(arguments={"ids": [6]}, delivered=(Delivered(6, (1,), ("h_da",)),)),
        recorded_at=T1,
    )
    with storage.begin() as conn:
        xz = read_access(storage, conn, client=None, circle="xz", since=None)
        other = read_access(storage, conn, client=None, circle="nope", since=None)
    assert [row.id for row in xz] == [1]
    assert other == []


@pytest.mark.db
def test_the_payload_of_an_access_holds_no_content(db: Engine) -> None:
    """Not the text of a unit, not a line of it, not a name in it, searched in
    every string of the stored payload, keys included. The arguments are the
    client's input and stay."""
    storage = PostgresStorage(db)
    event_id = _mail(storage)
    record_access(
        storage,
        _access(
            arguments={"circle": "h_da", "since": "2026-09-01", "ids": [event_id]},
            delivered=(Delivered(event_id, (1, 2), ("h_da",)),),
            withheld=(_no_rule(event_id + 1, "h_da"),),
        ),
        recorded_at=T1,
    )
    payload = _payloads(db)[-1]
    assert payload["action"] == "mcp_access"
    assert _found_in(payload) == []


@pytest.mark.db
def test_the_search_for_content_finds_it_in_a_stored_payload(db: Engine) -> None:
    """The control of the test above, on a real stored payload: the same
    search finds a wording of the mail put into `reason` and into
    `arguments`, nested and as a key, so that its green is not blindness."""
    storage = PostgresStorage(db)
    _mail(storage)
    line = "the invoice 4711 of the Danube project is overdue."
    record_access(
        storage,
        _access(
            arguments={"circle": "h_da", "note": {"deep": [line]}, "key4711": 1},
            withheld=(Withheld(2, "no_rule", ("h_da",), f"because {line}", ("h_da",), None),),
        ),
        recorded_at=T1,
    )
    found = _found_in(_payloads(db)[-1])
    strings = {s for _, s in found}
    assert strings == {line, f"because {line}", "key4711"}


@pytest.mark.db
def test_an_access_has_no_units_and_does_not_enter_the_chronicle(db: Engine) -> None:
    storage = PostgresStorage(db)
    _mail(storage)
    record_access(storage, _access(delivered=(Delivered(1, (1, 2), ()),)), recorded_at=T1)
    catch_up(storage, storage, CHRONICLE)
    with storage.begin() as conn:
        assert storage.units_by_event(conn, [2]).get(2, []) == []
    with db.begin() as conn:
        shown = {r[0] for r in conn.execute(text("SELECT event_id FROM p_chronicle"))}
    assert shown == {1}


def _entry(base: dict[str, object], key: str) -> dict[str, object]:
    return cast("list[dict[str, object]]", base[key])[0]


def _without(entry: dict[str, object], key: str) -> dict[str, object]:
    return {name: value for name, value in entry.items() if name != key}


@pytest.mark.db
def test_verify_finds_a_broken_form(db: Engine) -> None:
    storage = PostgresStorage(db)
    good = _access(delivered=(Delivered(1, (1,), ("h_da",)),), withheld=(_no_rule(2, "h_da"),))
    record_access(storage, good, recorded_at=T0)
    assert verify(storage) == []  # the control

    base = _payloads(db)[0]
    broken: list[dict[str, object]] = [
        {**base, "outcome": "denied"},
        {k: v for k, v in base.items() if k != "outcome"},
        {**base, "surprise": 1},
        {**base, "delivered": "42"},
        {**base, "delivered": [{"units": [1]}]},
        {**base, "withheld": [{"event": 2, "reason_code": "because"}]},
        {**base, "call": {"kind": "tool", "name": "x"}},
        {**base, "call": {**cast("dict[str, object]", base["call"]), "kind": ["tool"]}},
        {**base, "call": {**cast("dict[str, object]", base["call"]), "text": "smuggled"}},
        {**base, "withheld": [{**_entry(base, "withheld"), "reason_code": {"a": 1}}]},
        {**base, "withheld": [{**_entry(base, "withheld"), "text": "smuggled"}]},
        {**base, "withheld": [{**_entry(base, "withheld"), "reason": 5}]},
        {**base, "withheld": [{**_entry(base, "withheld"), "circles": [True]}]},
        {**base, "withheld": [{**_entry(base, "withheld"), "uncovered": "h_da"}]},
        {**base, "withheld": [{**_entry(base, "withheld"), "uncovered": [7]}]},
        {**base, "withheld": [{**_entry(base, "withheld"), "source": ["email"]}]},
        {**base, "withheld": [_without(_entry(base, "withheld"), "source")]},
        {**base, "withheld": ["event 2"]},
        {**base, "delivered": [3]},
        {**base, "delivered": [{**_entry(base, "delivered"), "text": "smuggled"}]},
        {**base, "delivered": [{**_entry(base, "delivered"), "units": [True]}]},
        {**base, "delivered": [{**_entry(base, "delivered"), "units": "1"}]},
        {**base, "delivered": [{**_entry(base, "delivered"), "circles": [1]}]},
        {**base, "delivered": [{"event": 1, "units": [1]}]},
        {**base, "client": ["claude-code"]},
        {**base, "policy": []},
        {**base, "outcome": ["ok"]},
        {**base, "era": 7},
    ]
    for payload in broken:
        append_action(storage, payload, (), recorded_at=T1)
    findings = verify(storage)
    assert [f.event_id for f in findings] == list(range(2, 2 + len(broken)))
    assert all(f.reason.startswith("mcp_access has no valid form: ") for f in findings)

    # Reading, counting and printing survive the forged rows and show only the good one.
    with storage.begin() as conn:
        assert [r.id for r in read_access(storage, conn, client=None, circle=None, since=None)] == [
            1
        ]
        assert gaps(storage, conn, since=None) == [Gap("circle:h_da", 1, T0, "mcp")]


@pytest.mark.db
def test_verify_finds_an_access_with_units(db: Engine) -> None:
    storage = PostgresStorage(db)
    record_access(storage, _access(), recorded_at=T0)
    base = _payloads(db)[0]
    append_action(storage, base, (RawUnit(seq=1, content="smuggled"),), recorded_at=T1)
    assert [(f.event_id, f.reason) for f in verify(storage)] == [(2, "mcp_access has units")]


@pytest.mark.db
def test_gaps_count_what_mcp_withheld_for_lack_of_a_rule_apart_from_the_gate(db: Engine) -> None:
    storage = PostgresStorage(db)
    record_access(storage, _access(withheld=(_no_rule(5, "xz"),)), recorded_at=T0)
    record_access(
        storage,
        _access(
            withheld=(
                _no_rule(6, "xz"),
                Withheld(7, "rule", ("xz",), "circle xz requires eu", (), "email"),
                _no_rule(8, "h_da"),
            )
        ),
        recorded_at=T2,
    )
    with storage.begin() as conn:
        found = gaps(storage, conn, since=None)
        recent = gaps(storage, conn, since=T1)
        none = gaps(storage, conn, since=T2 + timedelta(hours=1))
    assert [(g.origin, g.what, g.count, g.last) for g in found] == [
        ("mcp", "circle:h_da", 1, T2),
        ("mcp", "circle:xz", 2, T2),
    ]
    assert [(g.what, g.count) for g in recent] == [("circle:h_da", 1), ("circle:xz", 1)]
    assert none == []


@pytest.mark.db
def test_gaps_count_only_the_circles_without_a_rule_and_else_the_source(db: Engine) -> None:
    """An event of three circles, two of them with a rule, is a gap of the
    third alone; an event of no circle is one of its source, once per source
    as the gate counts it, and of itself only where it has no source
    (ruling R-16 of the 2026-10-11 MCP read access plan: counting every circle
    of the event named rules that exist as missing)."""
    storage = PostgresStorage(db)
    reason = "circle team has no rule"
    record_access(
        storage,
        _access(
            withheld=(
                Withheld(5, "no_rule", ("huber", "office", "team"), reason, ("team",), "email"),
                Withheld(6, "no_rule", (), "no rule covers this content", (), "email"),
                Withheld(7, "no_rule", (), "no rule covers this content", (), "email"),
                Withheld(8, "no_rule", (), "no rule covers this content", (), None),
            )
        ),
        recorded_at=T0,
    )
    with storage.begin() as conn:
        found = gaps(storage, conn, since=None)
    assert [(g.what, g.count) for g in found] == [
        ("circle:team", 1),
        ("event:8", 1),
        ("source:email", 2),
    ]


@pytest.mark.db
def test_gaps_ignore_a_withholding_that_a_rule_caused(db: Engine) -> None:
    """The control of the test above: `rule` is no gap."""
    storage = PostgresStorage(db)
    record_access(
        storage,
        _access(withheld=(Withheld(7, "rule", ("xz",), "circle xz requires eu", (), "email"),)),
        recorded_at=T0,
    )
    with storage.begin() as conn:
        assert gaps(storage, conn, since=None) == []


@pytest.mark.db
def test_the_command_access_prints_one_line_per_call(
    db: Engine, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("PREVIOUSLY_DSN", db.url.render_as_string(hide_password=False))
    storage = PostgresStorage(db)
    record_access(
        storage,
        _access(
            delivered=(Delivered(42, (1, 2), ()), Delivered(44, (), ())),
            withheld=(_no_rule(43, "h_da"),),
        ),
        recorded_at=T0,
    )
    record_access(storage, _access(client="other", arguments={"circle": "xz"}), recorded_at=T1)

    assert main(["access", "--client", "claude-code"]) == 0
    out, err = capsys.readouterr()
    assert err == ""
    assert out == (
        "2026-10-11T12:00:00.000000Z\tclaude-code\ttool:previously\tok"
        "\tdelivered 42,44\twithheld 43:no_rule:circle h_da has no rule for this client\n"
    )

    assert main(["access", "--circle", "xz", "--since", "2026-10-11T12:30:00Z"]) == 0
    out, _ = capsys.readouterr()
    assert out == (
        "2026-10-11T13:00:00.000000Z\tother\ttool:previously\tok\tdelivered -\twithheld -\n"
    )

    assert main(["access", "--client", "nobody"]) == 0
    assert capsys.readouterr() == ("", "no access matches\n")


@pytest.mark.db
def test_policy_gaps_prints_the_mcp_withholdings_with_their_origin(
    db: Engine, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("PREVIOUSLY_DSN", db.url.render_as_string(hide_password=False))
    storage = PostgresStorage(db)
    record_access(storage, _access(withheld=(_no_rule(5, "xz"),)), recorded_at=T0)
    assert main(["policy", "gaps"]) == 0
    assert capsys.readouterr() == ("mcp:circle:xz\t1\t2026-10-11T12:00:00.000000Z\n", "")


@pytest.mark.db
def test_the_stored_payload_is_the_sketch_of_the_concept(db: Engine) -> None:
    """The sketch in §5 of the concept specification (frozen design record),
    field for field, plus the `reason_code` and `circles` of a withheld
    entry."""
    storage = PostgresStorage(db)
    record_access(
        storage,
        _access(
            arguments={"circle": "h_da", "since": "2026-09-01"},
            delivered=(Delivered(42, (1, 2, 3), ("h_da",)),),
            withheld=(_no_rule(43, "h_da"),),
        ),
        recorded_at=T0,
    )
    assert _payloads(db) == [
        {
            "action": "mcp_access",
            "client": "claude-code",
            "policy": {"client": 31, "processor": 12, "rules": [19]},
            "call": {
                "kind": "tool",
                "name": "previously",
                "arguments": {"circle": "h_da", "since": "2026-09-01"},
            },
            "delivered": [{"event": 42, "units": [1, 2, 3], "circles": ["h_da"]}],
            "withheld": [
                {
                    "event": 43,
                    "reason_code": "no_rule",
                    "circles": ["h_da"],
                    "reason": "circle h_da has no rule for this client",
                    "uncovered": ["h_da"],
                    "source": "email",
                }
            ],
            "outcome": "ok",
            "era": "2026-07-28",
        }
    ]
