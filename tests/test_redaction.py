# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The form of a redaction and the index over them, without a database
({ref}`erasure`)."""

from previously.core.canonical import canonical
from previously.core.redaction import action_name
from previously.core.redaction import blob_expected
from previously.core.redaction import blob_payload
from previously.core.redaction import event_payload
from previously.core.redaction import MalformedAction
from previously.core.redaction import parse
from previously.core.redaction import Redaction
from previously.core.redaction import RedactionIndex
from previously.core.redaction import units_payload

import pytest


BLOB = "ab" * 32
OTHER_BLOB = "cd" * 32


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
                "scope": "event",
                "target": {"event": 5, "blobs": []},
                "reason": " \t",
            },
            id="reason-only-blanks",
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
    """The third form, written by hand rather than by `blob_payload`, so that
    the parser is held against the form and not against its own builder."""
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


def test_the_index_names_the_earlier_of_a_unit_redaction_and_an_event_redaction() -> None:
    """A unit covered both by a redaction of its units and by a redaction
    of its whole event is answered with the earlier of the two, the rule the
    class states and `of_reference` keeps. Neither `redact` path writes
    that pair, so only a log written otherwise holds it; the order of `add`
    is the chain order. Measured on 2026-10-05 with the units redaction
    preferred as before: the first assertion failed."""
    index = RedactionIndex()
    of_event = parse(8, event_payload(5, blobs=[], reason="r"))
    of_units = parse(9, units_payload(5, [2], reason="r"))
    index.add(of_event)
    index.add(of_units)
    assert index.of_unit(5, 2) == of_event
    assert index.of_unit(5, 1) == of_event

    later = RedactionIndex()
    of_units = parse(8, units_payload(5, [2], reason="r"))
    of_event = parse(9, event_payload(5, blobs=[], reason="r"))
    later.add(of_units)
    later.add(of_event)
    assert later.of_unit(5, 2) == of_units
    assert later.of_unit(5, 1) == of_event


def test_every_payload_a_builder_makes_is_canonical() -> None:
    canonical(event_payload(5, blobs=[BLOB, BLOB], reason="r"))
    canonical(units_payload(5, [2, 1], reason="r"))
    canonical(blob_payload(BLOB, [7, 2, 7], reason="r"))


def test_the_blob_form_round_trips() -> None:
    payload = blob_payload(BLOB, [7, 2, 7], reason="r")
    assert payload["target"] == {"blob": BLOB, "events": [2, 7]}
    assert parse(9, payload) == Redaction(id=9, scope="blob", reason="r", blob=BLOB, events=(2, 7))


def test_a_reference_is_erased_through_its_event_or_through_a_blob_redaction_that_names_it() -> (
    None
):
    """A reference (event, blob) is erased when its event is erased whole or
    when a blob redaction names the event ({ref}`erasure`). A blob redaction
    that names another event leaves this reference alone, and so does one of
    another blob."""
    index = RedactionIndex()
    of_event = parse(8, event_payload(2, blobs=[BLOB], reason="r"))
    of_blob = parse(9, blob_payload(BLOB, [3], reason="r"))
    index.add(of_event)
    index.add(of_blob)
    assert index.of_reference(2, BLOB) == of_event
    assert index.of_reference(3, BLOB) == of_blob
    assert index.of_reference(4, BLOB) is None
    assert index.of_reference(3, OTHER_BLOB) is None
    # The erasure of the event covers every blob it named, whichever list
    # names them: the register is what says which, not this index.
    assert index.of_reference(2, OTHER_BLOB) == of_event


def _index(*payloads: dict[str, object]) -> RedactionIndex:
    index = RedactionIndex()
    for offset, payload in enumerate(payloads):
        index.add(parse(100 + offset, payload))
    return index


@pytest.mark.parametrize(
    ("index", "users", "expected"),
    [
        pytest.param(
            _index(event_payload(1, blobs=[BLOB], reason="r")), [1, 2], True, id="one-of-two-erased"
        ),
        pytest.param(
            _index(
                event_payload(1, blobs=[BLOB], reason="r"),
                event_payload(2, blobs=[BLOB], reason="r"),
            ),
            [1, 2],
            False,
            id="both-erased",
        ),
        pytest.param(
            _index(blob_payload(BLOB, [1, 2], reason="r")), [1, 2], False, id="blob-names-both"
        ),
        pytest.param(
            _index(blob_payload(BLOB, [1, 2], reason="r")),
            [1, 2, 3],
            True,
            id="blob-names-both-and-a-third-comes",
        ),
        pytest.param(RedactionIndex(), [], False, id="no-reference"),
    ],
)
def test_blob_expected(index: RedactionIndex, users: list[int], expected: bool) -> None:
    """The rule ({ref}`erasure`): a blob has to lie in the store as long as
    at least one of its references is not erased, and without any
    reference it has nothing to lie for."""
    assert blob_expected(index, BLOB, users) is expected
