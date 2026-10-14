# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Approval classes: the form of their events, the fold with its states, the
level decision, the write path, the hit rate and the sample."""

from dataclasses import replace
from datetime import datetime
from datetime import timedelta
from datetime import UTC
from previously.core.action import append_action
from previously.core.action import KNOWN_ACTIONS
from previously.core.assertion import DIRECT
from previously.core.assertion import model_author
from previously.core.assertion import OPEN
from previously.core.assertion import OPERATOR
from previously.core.assertion import payload_of
from previously.core.assertion import REJECTION
from previously.core.assertion import Source
from previously.core.assertion import Statement
from previously.core.classes import ApprovalClass
from previously.core.classes import class_payload
from previously.core.classes import class_problem
from previously.core.classes import Classes
from previously.core.classes import ClassFold
from previously.core.classes import ClassRefused
from previously.core.classes import hit_rates
from previously.core.classes import read_classes
from previously.core.classes import sample
from previously.core.classes import set_class
from previously.core.graph import ACTIVE
from previously.core.graph import Claim
from previously.core.graph import claim_payload
from previously.core.graph import ClassState
from previously.core.graph import ENTITY
from previously.core.graph import EntityBody
from previously.core.graph import fold_graph
from previously.core.graph import Graph
from previously.core.graph import level_of
from previously.core.graph import RETRACTED
from previously.core.graph import SOURCES
from previously.core.graph import TRANSITIVE
from previously.core.redact import redact_event
from previously.core.verify import Finding
from previously.core.verify import verify
from previously.core.vocabulary import apply_vocabulary
from previously.core.vocabulary import base_vocabulary
from previously.core.vocabulary import FieldSpec
from previously.core.vocabulary import GATE_TYPES
from previously.core.vocabulary import KindSpec
from previously.core.vocabulary import parse_file
from previously.core.vocabulary import Vocabulary
from previously.storage.postgres import PostgresStorage
from typing import cast
from typing import TYPE_CHECKING

import pytest
import random


if TYPE_CHECKING:
    from collections.abc import Mapping
    from sqlalchemy import Engine


T0 = datetime(2026, 10, 14, 12, 0, 0, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)
T2 = T0 + timedelta(hours=2)
MODEL = model_author("claude")

CLASS = ApprovalClass(
    "claude_projects",
    MODEL,
    ENTITY,
    frozenset({"project", "person"}),
    80,
    None,
    None,
    revoked=False,
    demote=False,
)


# The base vocabulary, as `level` reads it for a kind's behaviors.
VOCABULARY = Vocabulary(
    {(spec.declares, spec.name): spec for spec in parse_file(base_vocabulary())}, {}
)


def _classes(*entries: tuple[ApprovalClass, int]) -> Classes:
    """Classes as `read_classes` would build them from `entries`, which are
    given in chain order."""
    by_name = {item.name: (item, event_id) for item, event_id in entries}
    ids: dict[str, list[int]] = {}
    for item, event_id in entries:
        ids.setdefault(item.name, []).append(event_id)
    states = {
        event_id: ClassState(by_name[name][1], by_name[name][0].revoked, by_name[name][0].demote)
        for name, group in ids.items()
        for event_id in group
    }
    return Classes(by_name, states)


def _level(
    classes: Classes,
    *,
    author: str = MODEL,
    kind: str = ENTITY,
    type_name: str = "project",
    confidence: int | None = 90,
    recorded_at: datetime = T1,
) -> tuple[str, int | None]:
    return classes.level(
        author=author,
        kind=kind,
        type_name=type_name,
        confidence=confidence,
        recorded_at=recorded_at,
        vocabulary=VOCABULARY,
    )


# --- Form -------------------------------------------------------------------------


def test_the_payload_reads_back_as_the_class() -> None:
    windowed = replace(CLASS, valid_from=T0, valid_until=T2, revoked=True, demote=True)
    for item in (CLASS, windowed):
        payload = class_payload(item, statement="allow it")
        assert class_problem(payload) is None
        assert payload["types"] == ["person", "project"]
    assert class_payload(CLASS, statement="s")["valid"] is None
    assert class_payload(windowed, statement="s")["valid"] == {
        "from": "2026-10-14T12:00:00.000000Z",
        "until": "2026-10-14T14:00:00.000000Z",
    }


def test_a_window_open_on_one_side_is_sound_form() -> None:
    for item in (replace(CLASS, valid_from=T0), replace(CLASS, valid_until=T2)):
        payload = class_payload(item, statement="s")
        assert class_problem(payload) is None
        assert None in cast("dict[str, object]", payload["valid"]).values()


def _payload(**changes: object) -> dict[str, object]:
    return {**class_payload(CLASS, statement="allow it"), **changes}


@pytest.mark.parametrize(
    ("changes", "fragment"),
    [
        ({"action": "policy"}, "no approval class event"),
        ({"name": "Claude"}, "no identifier"),
        ({"author": "human:operator"}, "no model:<client>"),
        ({"author": "model:"}, "no model:<client>"),
        ({"author": "model:a b"}, "no model:<client>"),
        ({"assertion": "obligation"}, "neither entity nor relation"),
        ({"types": []}, "at least one type"),
        ({"types": ["project", "project"]}, "a type twice"),
        ({"types": ["Project"]}, "no identifier"),
        ({"threshold": 101}, "threshold"),
        ({"threshold": -1}, "threshold"),
        ({"threshold": True}, "threshold"),
        ({"threshold": 80.5}, "threshold"),
        ({"valid": {"from": None}}, "neither null nor a table"),
        ({"valid": {"from": "2026-10-14T12:00:00", "until": None}}, "time zone"),
        ({"valid": {"from": "tomorrow", "until": None}}, "time zone"),
        (
            {"valid": {"from": "2026-10-14T12:00:00Z", "until": "2026-10-14T12:00:00Z"}},
            "not after",
        ),
        ({"revoked": "no"}, "revoked"),
        ({"demote": True}, "demotes without being revoked"),
        ({"statement": " "}, "statement"),
    ],
)
def test_each_form_fault_is_named_on_its_own(changes: dict[str, object], fragment: str) -> None:
    problem = class_problem(_payload(**changes))
    assert problem is not None
    assert problem.startswith("has no valid form: it ")
    assert fragment in problem


@pytest.mark.parametrize("gate", sorted(GATE_TYPES))
def test_a_built_in_type_is_a_form_fault(gate: str) -> None:
    problem = class_problem(_payload(types=["project", gate]))
    assert problem is not None
    assert f'"{gate}"' in problem


def test_a_missing_or_extra_key_is_a_form_fault() -> None:
    payload = _payload()
    del payload["demote"]
    assert class_problem(payload) is not None
    assert class_problem({**_payload(), "extra": 1}) is not None


def test_approval_class_is_a_known_action() -> None:
    assert "approval_class" in KNOWN_ACTIONS


# --- The level --------------------------------------------------------------------


def test_the_threshold_is_included_and_below_it_is_open() -> None:
    classes = _classes((CLASS, 7))
    assert _level(classes, confidence=80) == (TRANSITIVE, 7)
    assert _level(classes, confidence=100) == (TRANSITIVE, 7)
    assert _level(classes, confidence=79) == (OPEN, None)
    assert _level(classes, confidence=None) == (OPEN, None)


def test_a_threshold_of_zero_takes_every_confidence() -> None:
    classes = _classes((replace(CLASS, threshold=0), 7))
    assert _level(classes, confidence=0) == (TRANSITIVE, 7)


def test_the_window_includes_its_start_and_excludes_its_end() -> None:
    classes = _classes((replace(CLASS, valid_from=T1, valid_until=T2), 7))
    assert _level(classes, recorded_at=T1 - timedelta(microseconds=1)) == (OPEN, None)
    assert _level(classes, recorded_at=T1) == (TRANSITIVE, 7)
    assert _level(classes, recorded_at=T2 - timedelta(microseconds=1)) == (TRANSITIVE, 7)
    assert _level(classes, recorded_at=T2) == (OPEN, None)


def test_a_window_open_on_one_side_is_open_on_that_side() -> None:
    before = _classes((replace(CLASS, valid_until=T1), 7))
    after = _classes((replace(CLASS, valid_from=T1), 7))
    assert _level(before, recorded_at=T0) == (TRANSITIVE, 7)
    assert _level(after, recorded_at=T2) == (TRANSITIVE, 7)


def test_another_author_another_kind_and_another_type_are_open() -> None:
    classes = _classes((CLASS, 7))
    assert _level(classes, author=model_author("other")) == (OPEN, None)
    assert _level(classes, author=OPERATOR) == (OPEN, None)
    assert _level(classes, kind="relation") == (OPEN, None)
    assert _level(classes, type_name="matter") == (OPEN, None)
    assert _level(classes, type_name="person") == (TRANSITIVE, 7)


def test_a_revoked_class_takes_nothing_new() -> None:
    revoked = replace(CLASS, revoked=True)
    assert _level(_classes((CLASS, 7), (revoked, 9))) == (OPEN, None)
    # The control: the same classes without the revocation.
    assert _level(_classes((CLASS, 7), (replace(CLASS, threshold=70), 9))) == (TRANSITIVE, 9)


def test_the_highest_threshold_wins_then_the_oldest_event() -> None:
    low = replace(CLASS, name="low", threshold=50)
    high = replace(CLASS, name="high", threshold=85)
    twin = replace(CLASS, name="twin", threshold=85)
    assert _level(_classes((low, 3), (high, 5)), confidence=90) == (TRANSITIVE, 5)
    assert _level(_classes((low, 3), (high, 5)), confidence=60) == (TRANSITIVE, 3)
    assert _level(_classes((twin, 9), (high, 5)), confidence=90) == (TRANSITIVE, 5)
    assert _level(_classes((high, 9), (twin, 5)), confidence=90) == (TRANSITIVE, 5)


@pytest.mark.parametrize("gate", sorted(GATE_TYPES))
def test_a_built_in_type_is_open_even_if_an_event_names_it(gate: str) -> None:
    """The control is the same class with a type that is not built in."""
    named = replace(CLASS, types=frozenset({gate, "project"}), assertion="relation")
    classes = _classes((named, 7))
    assert _level(classes, kind="relation", type_name=gate) == (OPEN, None)
    assert _level(classes, kind="relation", type_name="project") == (TRANSITIVE, 7)


def test_an_acyclic_kind_is_open_even_if_an_event_names_it() -> None:
    """Ruling T6-a of the 2026-10-14 assignments plan: `part_of` is acyclic
    in the base vocabulary, and no class covers it; `involved_in` is not,
    and the same class covers it, the control."""
    named = replace(CLASS, types=frozenset({"part_of", "involved_in"}), assertion="relation")
    classes = _classes((named, 7))
    assert _level(classes, kind="relation", type_name="part_of") == (OPEN, None)
    assert _level(classes, kind="relation", type_name="involved_in") == (TRANSITIVE, 7)
    assert not classes.covers(
        7,
        author=MODEL,
        kind="relation",
        type_name="part_of",
        confidence=90,
        recorded_at=T1,
        vocabulary=VOCABULARY,
    )


# --- The fold from the log --------------------------------------------------------


@pytest.mark.db
def test_a_written_class_is_read_back(db: Engine) -> None:
    storage = PostgresStorage(db)
    apply_vocabulary(storage, parse_file(base_vocabulary()), recorded_at=T0)
    event = set_class(storage, CLASS, statement="allow it", recorded_at=T1)
    with storage.begin() as conn:
        classes = read_classes(storage, conn)
    assert classes.by_name == {CLASS.name: (CLASS, event)}
    assert classes.states == {event: ClassState(event, False, False)}


@pytest.mark.db
def test_every_event_of_a_name_sees_the_newest_state(db: Engine) -> None:
    storage = PostgresStorage(db)
    apply_vocabulary(storage, parse_file(base_vocabulary()), recorded_at=T0)
    first = set_class(storage, CLASS, statement="allow it", recorded_at=T0)
    second = set_class(storage, replace(CLASS, threshold=70), statement="lower", recorded_at=T1)
    with storage.begin() as conn:
        classes = read_classes(storage, conn)
    assert classes.states[first] == ClassState(second, False, False)
    assert classes.states[second] == ClassState(second, False, False)
    # A revocation reaches the older event too (the mutation: only the newest).
    revoked = set_class(
        storage, replace(CLASS, revoked=True, demote=True), statement="stop", recorded_at=T2
    )
    with storage.begin() as conn:
        classes = read_classes(storage, conn)
    assert classes.states[first] == ClassState(revoked, True, True)
    assert classes.states[second] == ClassState(revoked, True, True)
    assert classes.by_name[CLASS.name][1] == revoked


@pytest.mark.db
def test_a_reenabling_event_makes_the_older_events_active_again(db: Engine) -> None:
    storage = PostgresStorage(db)
    apply_vocabulary(storage, parse_file(base_vocabulary()), recorded_at=T0)
    first = set_class(storage, CLASS, statement="allow it", recorded_at=T0)
    set_class(storage, replace(CLASS, revoked=True), statement="stop", recorded_at=T1)
    third = set_class(storage, CLASS, statement="again", recorded_at=T2)
    with storage.begin() as conn:
        classes = read_classes(storage, conn)
    assert classes.states[first] == ClassState(third, False, False)
    # A statement written while the class was revoked was written open, and
    # the write path decided that then; from now on the class takes new ones.
    assert _level(classes) == (TRANSITIVE, third)


@pytest.mark.db
def test_the_classes_of_a_moment_are_the_log_up_to_it(db: Engine) -> None:
    storage = PostgresStorage(db)
    apply_vocabulary(storage, parse_file(base_vocabulary()), recorded_at=T0)
    set_class(storage, CLASS, statement="allow it", recorded_at=T1)
    with storage.begin() as conn:
        assert read_classes(storage, conn, at=T0).by_name == {}
        assert CLASS.name in read_classes(storage, conn, at=T1).by_name


@pytest.mark.db
def test_a_class_in_the_log_that_names_a_built_in_type_is_never_transitive(db: Engine) -> None:
    """Written by hand, past the write path."""
    storage = PostgresStorage(db)
    bad = {**class_payload(CLASS, statement="s"), "types": ["circle", "project"]}
    append_action(storage, bad, (), recorded_at=T0)
    with storage.begin() as conn:
        classes = read_classes(storage, conn)
    # The event is broken as a whole and read as nothing; and even a class
    # that had slipped through would not reach the gate types.
    assert classes.by_name == {}
    forced = Classes({"x": (replace(CLASS, types=frozenset({"circle"})), 1)}, {})
    assert _level(forced, type_name="circle") == (OPEN, None)


@pytest.mark.db
def test_an_erased_class_event_counts_as_nothing(db: Engine) -> None:
    storage = PostgresStorage(db)
    apply_vocabulary(storage, parse_file(base_vocabulary()), recorded_at=T0)
    event = set_class(storage, CLASS, statement="allow it", recorded_at=T1)
    redact_event(storage, storage, event, reason="test", recorded_at=T2)
    with storage.begin() as conn:
        assert read_classes(storage, conn).by_name == {}


# --- The write path ---------------------------------------------------------------


@pytest.mark.db
def test_a_class_is_refused_for_a_type_the_vocabulary_does_not_know(db: Engine) -> None:
    storage = PostgresStorage(db)
    apply_vocabulary(storage, parse_file(base_vocabulary()), recorded_at=T0)
    with pytest.raises(ClassRefused, match='names "ghost"'):
        set_class(
            storage, replace(CLASS, types=frozenset({"ghost"})), statement="s", recorded_at=T1
        )
    # A relation kind is no entity kind.
    with pytest.raises(ClassRefused, match='names "holds"'):
        set_class(
            storage, replace(CLASS, types=frozenset({"holds"})), statement="s", recorded_at=T1
        )
    # The control: a kind that stands.
    assert set_class(storage, CLASS, statement="s", recorded_at=T1)


@pytest.mark.db
def test_a_retired_kind_is_refused_but_a_revocation_still_goes_through(db: Engine) -> None:
    storage = PostgresStorage(db)
    base = parse_file(base_vocabulary())
    name = FieldSpec("name", "text", None, None, True)
    team = KindSpec("entity", "team", {"en": "Team"}, (name,), frozenset(), None, None, False)
    apply_vocabulary(storage, (*base, team), recorded_at=T0)
    item = replace(CLASS, types=frozenset({"team"}))
    set_class(storage, item, statement="s", recorded_at=T0)
    apply_vocabulary(storage, base, recorded_at=T1)
    with pytest.raises(ClassRefused, match='names "team"'):
        set_class(storage, replace(item, threshold=60), statement="s", recorded_at=T2)
    assert set_class(storage, replace(item, revoked=True), statement="stop", recorded_at=T2)


@pytest.mark.db
@pytest.mark.parametrize("gate", sorted(GATE_TYPES))
def test_a_class_naming_a_built_in_type_is_refused(db: Engine, gate: str) -> None:
    storage = PostgresStorage(db)
    apply_vocabulary(storage, parse_file(base_vocabulary()), recorded_at=T0)
    item = replace(
        CLASS, types=frozenset({gate}), assertion="entity" if gate == "circle" else "relation"
    )
    with pytest.raises(ClassRefused, match="the gate reads"):
        set_class(storage, item, statement="s", recorded_at=T1)
    with storage.begin() as conn:
        assert read_classes(storage, conn).by_name == {}


@pytest.mark.db
@pytest.mark.parametrize(
    "item",
    [
        replace(CLASS, demote=True),
        replace(CLASS, author=OPERATOR),
        replace(CLASS, threshold=101),
        replace(CLASS, threshold=-1),
        replace(CLASS, types=frozenset()),
        replace(CLASS, valid_from=T2, valid_until=T1),
    ],
)
def test_a_class_of_a_wrong_form_is_refused_and_nothing_is_written(
    db: Engine, item: ApprovalClass
) -> None:
    storage = PostgresStorage(db)
    apply_vocabulary(storage, parse_file(base_vocabulary()), recorded_at=T0)
    with pytest.raises(ClassRefused):
        set_class(storage, item, statement="s", recorded_at=T1)
    with storage.begin() as conn:
        assert read_classes(storage, conn).by_name == {}


@pytest.mark.db
def test_a_written_class_passes_verify_and_a_broken_one_is_reported(db: Engine) -> None:
    """The control is the class written properly."""
    storage = PostgresStorage(db)
    apply_vocabulary(storage, parse_file(base_vocabulary()), recorded_at=T0)
    set_class(storage, CLASS, statement="allow it", recorded_at=T1)
    assert verify(storage) == []
    broken = _payload(threshold=500)
    bad = append_action(storage, broken, (), recorded_at=T2)
    (finding,) = verify(storage)
    assert finding == Finding(
        bad,
        "approval_class event has no valid form: it has the threshold 500, "
        "which is no whole number from 0 to 100",
    )


# --- Hit rate and sample ----------------------------------------------------------

CLASS_EVENT = 900
STATES = {CLASS_EVENT: ClassState(CLASS_EVENT, False, False)}


def _entity(
    responsibility: str,
    *,
    subject: int | None,
    approves: int | None = None,
    under: int | None = None,
    state: str = ACTIVE,
) -> Claim:
    return Claim(
        ENTITY,
        OPERATOR if responsibility == DIRECT else MODEL,
        responsibility,
        SOURCES,
        (Source(5, None),),
        None,
        None,
        subject,
        approves,
        under,
        90 if responsibility != DIRECT else None,
        None,
        EntityBody("project", "en", {"name": "Fair"}, state),
    )


def _transitive(subject: int | None) -> Claim:
    return _entity(TRANSITIVE, subject=subject, under=CLASS_EVENT)


def _row(row_id: int, claim: Claim | Statement) -> tuple[int, datetime, Mapping[str, object]]:
    payload = claim_payload(claim) if isinstance(claim, Claim) else payload_of(claim)
    return row_id, T0 + timedelta(minutes=row_id), payload


def _rejection(of: int) -> Statement:
    return Statement(
        REJECTION, OPERATOR, DIRECT, (Source(5, None),), "wrong", None, None, None, of, None
    )


def _graph(*claims: Claim | Statement, states: Mapping[int, ClassState] = STATES) -> Graph:
    return fold_graph([_row(index, claim) for index, claim in enumerate(claims, 1)], states)


def _classes_for_graph() -> Classes:
    return _classes((CLASS, CLASS_EVENT))


def test_the_hit_rate_counts_confirmed_corrected_and_standing() -> None:
    # Thread 1: transitive, then approved (confirmed).
    # Thread 3: transitive, then a later direct version (corrected).
    # Thread 5: transitive, retracted by the operator (corrected).
    # Thread 7: transitive, rejected (corrected).
    # Thread 8: transitive and left alone (standing).
    graph = _graph(
        _transitive(None),  # 1
        _entity(DIRECT, subject=1, approves=1),  # 2
        _transitive(None),  # 3
        _entity(DIRECT, subject=3),  # 4
        _transitive(None),  # 5
        _entity(DIRECT, subject=5, state=RETRACTED),  # 6
        _transitive(None),  # 7
        _rejection(7),  # 8
        _transitive(None),  # 9
    )
    assert set(graph.threads) == {1, 3, 5, 7, 9}
    (rate,) = hit_rates(graph, _classes_for_graph())
    assert (rate.class_id, rate.name) == (CLASS_EVENT, CLASS.name)
    assert (rate.total, rate.confirmed, rate.corrected, rate.standing) == (5, 1, 3, 1)
    assert rate.total == rate.confirmed + rate.corrected + rate.standing


def test_a_later_transitive_version_overtakes_nothing() -> None:
    """The control for `corrected`: only a later direct version counts."""
    graph = _graph(_transitive(None), _transitive(1))
    (rate,) = hit_rates(graph, _classes_for_graph())
    assert (rate.total, rate.confirmed, rate.corrected, rate.standing) == (2, 0, 0, 2)


def test_the_sum_holds_for_every_class_and_open_versions_are_not_counted() -> None:
    other = replace(CLASS, name="other")
    classes = _classes((CLASS, CLASS_EVENT), (other, 901))
    states = {**STATES, 901: ClassState(901, False, False)}
    graph = _graph(
        _transitive(None),
        _entity(TRANSITIVE, subject=None, under=901),
        _entity("open", subject=None),
        _entity(DIRECT, subject=None),
        states=states,
    )
    rates = hit_rates(graph, classes)
    assert [rate.name for rate in rates] == ["claude_projects", "other"]
    assert [rate.total for rate in rates] == [1, 1]
    for rate in rates:
        assert rate.total == rate.confirmed + rate.corrected + rate.standing


def test_versions_under_a_class_revoked_with_demote_stay_in_its_numbers() -> None:
    revoked = replace(CLASS, revoked=True, demote=True)
    classes = _classes((CLASS, CLASS_EVENT), (revoked, 950))
    states = {CLASS_EVENT: ClassState(950, True, True), 950: ClassState(950, True, True)}
    graph = _graph(_transitive(None), states=states)
    (version,) = graph.threads[1].versions
    assert level_of(version, states) == OPEN
    (rate,) = hit_rates(graph, classes)
    assert (rate.class_id, rate.total, rate.standing) == (950, 1, 1)


def test_a_class_without_versions_has_a_zero_rate() -> None:
    (rate,) = hit_rates(_graph(), _classes_for_graph())
    assert (rate.total, rate.confirmed, rate.corrected, rate.standing) == (0, 0, 0, 0)


def test_the_sample_draws_distinct_versions_of_the_class_sorted_by_id() -> None:
    other_state = {**STATES, 901: ClassState(901, False, False)}
    graph = _graph(
        *[_transitive(None) for _ in range(6)],
        _entity(TRANSITIVE, subject=None, under=901),
        _entity("open", subject=None),
        states=other_state,
    )
    rng = random.SystemRandom()
    drawn = sample(graph, CLASS_EVENT, 3, rng)
    assert len(drawn) == 3
    assert len({version.id for version in drawn}) == 3
    assert [v.id for v in drawn] == sorted(v.id for v in drawn)
    assert {v.id for v in drawn} <= {1, 2, 3, 4, 5, 6}
    # Fewer than asked for: all of them. The control for the size.
    assert [v.id for v in sample(graph, CLASS_EVENT, 10, rng)] == [1, 2, 3, 4, 5, 6]
    assert [v.id for v in sample(graph, 901, 10, rng)] == [7]
    assert sample(graph, 12345, 3, rng) == ()
    assert sample(graph, CLASS_EVENT, 0, rng) == ()


def test_the_fold_takes_one_event_at_a_time_and_passes_over_what_is_no_sound_one() -> None:
    folded = ClassFold()
    before = folded.classes()
    folded.add(7, None)
    folded.add(8, {"action": "policy"})
    folded.add(9, {**class_payload(CLASS, statement="s"), "threshold": 101})
    assert folded.classes() is before
    folded.add(10, class_payload(CLASS, statement="s"))
    folded.add(11, class_payload(replace(CLASS, revoked=True), statement="stop"))
    after = folded.classes()
    assert before.by_name == {}
    assert after.states == {
        10: ClassState(11, revoked=True, demote=False),
        11: ClassState(11, revoked=True, demote=False),
    }


def test_covers_asks_whether_a_class_in_force_covers_a_statement() -> None:
    """`verify` asks it of the `under` of a transitive version: the class
    has to be one `level` could choose, by the newest event of its name."""

    def covers(
        class_id: int = 10,
        *,
        author: str = MODEL,
        type_name: str = "project",
        confidence: int | None = 90,
    ) -> bool:
        return _classes((CLASS, 10)).covers(
            class_id,
            author=author,
            kind=ENTITY,
            type_name=type_name,
            confidence=confidence,
            recorded_at=T1,
            vocabulary=VOCABULARY,
        )

    assert covers()
    assert not covers(confidence=50)
    assert not covers(confidence=None)
    assert not covers(type_name="post")
    assert not covers(author=model_author("other"))
    assert not covers(11)
