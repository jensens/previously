# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The form of a redaction and the index over them, without a database
({ref}`erasure`)."""

from previously.core.canonical import canonical
from previously.core.redaction import action_name
from previously.core.redaction import event_payload
from previously.core.redaction import MalformedAction
from previously.core.redaction import parse
from previously.core.redaction import Redaction
from previously.core.redaction import RedactionIndex
from previously.core.redaction import units_payload

import pytest


BLOB = "ab" * 32


def _units_form(**target: object) -> dict[str, object]:
    return {"action": "redaction", "scope": "units", "target": target, "reason": "r"}


def test_the_event_form_round_trips() -> None:
    payload = event_payload(5, blobs=[BLOB], reason="r")
    assert parse(9, payload) == Redaction(id=9, scope="event", reason="r", event=5, blobs=(BLOB,))
    assert parse(9, event_payload(5, blobs=[], reason="r")) == Redaction(
        id=9, scope="event", reason="r", event=5
    )


def test_the_units_form_orders_and_deduplicates() -> None:
    payload = units_payload(5, [3, 1, 3], reason="r")
    assert payload["target"] == {"event": 5, "units": [1, 3]}
    assert parse(9, payload) == Redaction(id=9, scope="units", reason="r", event=5, units=(1, 3))


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(
            {"action": "redaction", "scope": "event", "target": {"event": 5, "blobs": []}},
            id="reason-missing",
        ),
        pytest.param(
            {
                "action": "redaction",
                "scope": "event",
                "target": {"event": 5, "blobs": []},
                "reason": "",
            },
            id="reason-empty",
        ),
        pytest.param(
            {
                "action": "redaction",
                "scope": "unit",
                "target": {"event": 5, "units": [1]},
                "reason": "r",
            },
            id="scope-unknown",
        ),
        pytest.param({**_units_form(event=5, units=[1]), "extra": 1}, id="a-fifth-key"),
        pytest.param(_units_form(event=5, units=[]), id="units-empty"),
        pytest.param(_units_form(event=5, units=[3, 1]), id="units-unordered"),
        pytest.param(_units_form(event=5, units=3), id="units-not-a-list"),
        pytest.param(
            {"action": "redaction", "scope": "event", "target": [5], "reason": "r"},
            id="target-not-an-object",
        ),
        pytest.param(
            {
                "action": "redaction",
                "scope": "event",
                "target": {"event": True, "blobs": []},
                "reason": "r",
            },
            id="event-is-a-bool",
        ),
        pytest.param(
            {
                "action": "redaction",
                "scope": "event",
                "target": {"event": 5, "blobs": ["a" * 63]},
                "reason": "r",
            },
            id="blob-hash-of-63",
        ),
        pytest.param(
            {
                "action": "redaction",
                "scope": "event",
                "target": {"event": 5, "units": [1]},
                "reason": "r",
            },
            id="target-of-another-scope",
        ),
    ],
)
def test_parse_refuses_what_is_not_exactly_one_of_the_forms(payload: dict[str, object]) -> None:
    with pytest.raises(MalformedAction):
        parse(9, payload)


def test_an_action_without_a_name_is_malformed() -> None:
    with pytest.raises(MalformedAction):
        action_name({})
    assert action_name(event_payload(5, blobs=[], reason="r")) == "redaction"


def test_the_blob_form_parses() -> None:
    """The third form, written by hand: its builder comes with the erasure of
    a blob, and the form is one thing already."""
    payload: dict[str, object] = {
        "action": "redaction",
        "scope": "blob",
        "target": {"blob": BLOB, "events": [2, 7]},
        "reason": "r",
    }
    assert parse(9, payload) == Redaction(id=9, scope="blob", reason="r", blob=BLOB, events=(2, 7))


def test_the_index_finds_a_unit_through_its_own_redaction_and_through_its_event() -> None:
    index = RedactionIndex()
    of_units = parse(8, units_payload(5, [2], reason="r"))
    of_event = parse(9, event_payload(6, blobs=[], reason="r"))
    index.add(of_units)
    index.add(of_event)
    assert index.of_unit(5, 2) == of_units
    assert index.of_unit(5, 1) is None
    assert index.of_event(5) is None
    assert index.of_unit(6, 1) == of_event
    assert index.of_event(6) == of_event
    assert list(index) == [of_units, of_event]


def test_every_payload_a_builder_makes_is_canonical() -> None:
    canonical(event_payload(5, blobs=[BLOB, BLOB], reason="r"))
    canonical(units_payload(5, [2, 1], reason="r"))
