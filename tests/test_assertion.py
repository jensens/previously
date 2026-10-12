# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Assertions: the form, the references, the folding of versions.

Pure functions, so there is no database to start.
"""

from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import UTC
from hypothesis import given
from hypothesis import strategies as st
from previously.core.assertion import assertion_problem
from previously.core.assertion import changes
from previously.core.assertion import DECISION
from previously.core.assertion import DecisionBody
from previously.core.assertion import DIRECT
from previously.core.assertion import fold
from previously.core.assertion import model_author
from previously.core.assertion import OBLIGATION
from previously.core.assertion import ObligationBody
from previously.core.assertion import OPEN
from previously.core.assertion import OPERATOR
from previously.core.assertion import overdue
from previously.core.assertion import parse_statement
from previously.core.assertion import payload_of
from previously.core.assertion import reference_problem
from previously.core.assertion import REJECTION
from previously.core.assertion import Source
from previously.core.assertion import Statement
from previously.core.canonical import canonical
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from collections.abc import Mapping


NOW = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
TODAY = date(2026, 11, 15)


def make_obligation(
    *,
    responsibility: str = DIRECT,
    author: str = OPERATOR,
    subject: int | None = None,
    approves: int | None = None,
    reason: str | None = None,
    sources: tuple[Source, ...] = (Source(5, None),),
    debtor: str = "own",
    creditor: str = "circle:acme",
    what: str = "send the offer",
    due: date | None = date(2026, 11, 30),
    state: str = "open",
) -> Statement:
    return Statement(
        OBLIGATION,
        author,
        responsibility,
        sources,
        reason,
        None,
        subject,
        approves,
        None,
        ObligationBody(debtor, creditor, what, due, state),
    )


def make_decision(
    *,
    responsibility: str = DIRECT,
    subject: int | None = None,
    by: tuple[str, ...] = ("own", "address:anna@example.org"),
    on: date = date(2026, 11, 3),
    state: str = "valid",
    replaces: int | None = None,
) -> Statement:
    return Statement(
        DECISION,
        model_author("claude"),
        responsibility,
        (Source(7, (1, 2)),),
        "agreed by mail",
        "nonce-1",
        subject,
        None,
        None,
        DecisionBody("use PostgreSQL", by, on, state, replaces),
    )


def make_rejection(of: int, reason: str | None = "not what was said") -> Statement:
    return Statement(
        REJECTION, OPERATOR, DIRECT, (Source(5, None),), reason, None, None, None, of, None
    )


def good_obligation() -> dict[str, object]:
    return payload_of(make_obligation())


def good_decision() -> dict[str, object]:
    return payload_of(make_decision())


def good_rejection() -> dict[str, object]:
    return payload_of(make_rejection(3))


# --- Round trip -----------------------------------------------------------------


@pytest.mark.parametrize(
    "statement",
    [
        make_obligation(),
        make_obligation(due=None, reason="no deadline named"),
        make_obligation(responsibility=OPEN, author=model_author("claude")),
        make_obligation(subject=3, approves=4, sources=(Source(5, (1, 4, 9)), Source(8, None))),
        make_decision(),
        make_decision(subject=9, replaces=2, responsibility=OPEN),
        make_rejection(3),
        make_rejection(3, reason=None),
    ],
)
def test_every_form_round_trips(statement: Statement) -> None:
    payload = payload_of(statement)

    assert assertion_problem(payload) is None
    assert parse_statement(payload) == statement
    canonical(payload)  # the payload passes the canonical range: no float, lower-case keys


def test_dates_are_strings_in_the_payload() -> None:
    assert good_obligation()["due"] == "2026-11-30"
    assert good_decision()["on"] == "2026-11-03"


# --- Form faults, each with its sentence ----------------------------------------


def altered(payload: dict[str, object], **changed: object) -> dict[str, object]:
    return {**payload, **changed}


def without(payload: dict[str, object], key: str) -> dict[str, object]:
    return {name: value for name, value in payload.items() if name != key}


FAULTS: list[tuple[str, dict[str, object], str]] = [
    ("no kind", without(good_obligation(), "assertion"), "the assertion kind is none"),
    ("unknown kind", altered(good_obligation(), assertion="claim"), "the assertion kind is none"),
    ("extra key", altered(good_obligation(), color="red"), "the keys of the payload"),
    ("missing key", without(good_obligation(), "due"), "the keys of the payload"),
    ("empty sources", altered(good_obligation(), sources=[]), "the sources are empty"),
    ("sources not a list", altered(good_obligation(), sources="5"), "the sources are not a list"),
    (
        "source with extra key",
        altered(good_obligation(), sources=[{"event": 5, "units": None, "x": 1}]),
        "exactly the keys event and units",
    ),
    (
        "source event float",
        altered(good_obligation(), sources=[{"event": 5.0, "units": None}]),
        "an event that is not a whole number",
    ),
    (
        "source event bool",
        altered(good_obligation(), sources=[{"event": True, "units": None}]),
        "an event that is not a whole number",
    ),
    (
        "source event zero",
        altered(good_obligation(), sources=[{"event": 0, "units": None}]),
        "an event that is not a whole number",
    ),
    (
        "source not an object",
        altered(good_obligation(), sources=["5"]),
        "a source is not an object",
    ),
    (
        "units a string",
        altered(good_obligation(), sources=[{"event": 5, "units": "1"}]),
        "neither a list nor null",
    ),
    ("empty decision what", altered(good_decision(), what=""), "what is not a non-empty text"),
    (
        "units empty",
        altered(good_obligation(), sources=[{"event": 5, "units": list[int]()}]),
        "an empty list",
    ),
    (
        "units descending",
        altered(good_obligation(), sources=[{"event": 5, "units": [3, 1]}]),
        "not ascending",
    ),
    (
        "units duplicated",
        altered(good_obligation(), sources=[{"event": 5, "units": [1, 1]}]),
        "not ascending",
    ),
    (
        "unit float",
        altered(good_obligation(), sources=[{"event": 5, "units": [1.5]}]),
        "not whole numbers",
    ),
    (
        "unknown prefix",
        altered(good_obligation(), debtor="person:anna"),
        "the debtor is not a valid",
    ),
    (
        "address without at",
        altered(good_obligation(), creditor="address:anna.example.org"),
        "the creditor is not a valid",
    ),
    (
        "name with control character",
        altered(good_obligation(), debtor="name:Anna\x00"),
        "the debtor is not a valid",
    ),
    ("due 30 February", altered(good_obligation(), due="2026-02-30"), "due is neither null"),
    ("due German date", altered(good_obligation(), due="30.11.2026"), "due is neither null"),
    ("due empty", altered(good_obligation(), due=""), "due is neither null"),
    ("due short month", altered(good_obligation(), due="2026-2-3"), "due is neither null"),
    ("due ISO week", altered(good_obligation(), due="2026-W05-1"), "due is neither null"),
    ("due compact", altered(good_obligation(), due="20261130"), "due is neither null"),
    ("due float", altered(good_obligation(), due=1.5), "due is neither null"),
    (
        "unknown obligation state",
        altered(good_obligation(), state="done"),
        "state of an obligation",
    ),
    ("empty what", altered(good_obligation(), what="  "), "what is not a non-empty text"),
    ("unknown decision state", altered(good_decision(), state="open"), "state of a decision"),
    ("empty by", altered(good_decision(), by=[]), "by is not a list"),
    (
        "by with bad reference",
        altered(good_decision(), by=["own", "x"]),
        "a decider is not a valid",
    ),
    ("on empty", altered(good_decision(), on=""), "on is not a date"),
    ("on German date", altered(good_decision(), on="03.11.2026"), "on is not a date"),
    ("replaces float", altered(good_decision(), replaces=2.0), "replaces is neither null"),
    ("rejection without of", without(good_rejection(), "of"), "the keys of the payload"),
    ("rejection of null", altered(good_rejection(), of=None), "of is not the id of a proposal"),
    ("rejection of float", altered(good_rejection(), of=3.0), "of is not the id of a proposal"),
    (
        "rejection that is open",
        altered(good_rejection(), responsibility="open"),
        "a rejection is direct",
    ),
    ("rejection with subject", altered(good_rejection(), subject=3), "the keys of the payload"),
    ("unknown author", altered(good_obligation(), author="human:guest"), "the author is neither"),
    ("empty model client", altered(good_obligation(), author="model:"), "the author is neither"),
    (
        "unknown responsibility",
        altered(good_obligation(), responsibility="maybe"),
        "responsibility",
    ),
    ("empty reason", altered(good_obligation(), reason=""), "reason is neither null"),
    ("subject float", altered(good_obligation(), subject=3.0), "subject is neither null"),
    (
        "approval without subject",
        altered(good_obligation(), approves=4),
        "an approval needs a subject",
    ),
    (
        "open approval",
        altered(good_obligation(), approves=4, subject=3, responsibility="open"),
        "an approval is direct",
    ),
]


@pytest.mark.parametrize(("name", "payload", "sentence"), FAULTS, ids=[f[0] for f in FAULTS])
def test_each_form_fault_gets_its_own_sentence(
    name: str, payload: Mapping[str, object], sentence: str
) -> None:
    problem = assertion_problem(payload)

    assert problem is not None
    assert sentence in problem
    assert parse_statement(payload) is None


def test_a_fault_sentence_quotes_no_payload_text() -> None:
    private = "anna.secret@example.org"
    payload = altered(good_obligation(), debtor=f"address:{private}:", what=private, due=private)

    problem = assertion_problem(payload)

    assert problem is not None
    assert "secret" not in problem


def test_a_sentence_never_raises_for_odd_values() -> None:
    odd_values: list[object] = [None, 3, 2.5, [], {}, "x", True]
    for odd in odd_values:
        for key in ("author", "responsibility", "sources", "reason", "debtor", "due", "state"):
            assertion_problem(altered(good_obligation(), **{key: odd}))
        assertion_problem({"assertion": odd})


# --- References -----------------------------------------------------------------


@pytest.mark.parametrize(
    "reference",
    [
        "own",
        "circle:acme",
        "address:anna@example.org",
        "address:" + "a" * 242 + "@example.org",  # 254 characters in all
        "name:Anbieter XY",
        "name:" + "x" * 200,
        "name:Frau Huber",
    ],
)
def test_valid_references(reference: str) -> None:
    assert reference_problem(reference) is None


@pytest.mark.parametrize(
    ("reference", "sentence"),
    [
        ("", "no known prefix"),
        ("owner", "no known prefix"),
        ("own:x", "no known prefix"),
        ("person:anna", "no known prefix"),
        ("circle:", "circle name"),
        ("circle:  ", "circle name"),
        ("circle:a\nb", "circle name"),
        ("address:", "needs exactly one @"),
        ("address:anna", "needs exactly one @"),
        ("address:a@b@c", "needs exactly one @"),
        ("address:a b@c.d", "needs exactly one @"),
        ("address:@example.org", "part before and after"),
        ("address:anna@", "part before and after"),
        ("address:" + "a" * 243 + "@example.org", "longer than 254"),
        ("name:", "1 to 200"),
        ("name:" + "x" * 201, "1 to 200"),
        ("name:Anna\x00", "1 to 200"),
        ("name:Anna\x1f", "1 to 200"),
        ("name:Anna\x7f", "1 to 200"),
        ("name:Anna​", "1 to 200"),  # Cf: zero width space
        ("name:Anna‮", "1 to 200"),  # Cf: right-to-left override
        ("name:Anna ", "1 to 200"),
        ("name:Anna ", "1 to 200"),
        ("name:   ", "1 to 200"),
    ],
)
def test_invalid_references(reference: str, sentence: str) -> None:
    problem = reference_problem(reference)

    assert problem is not None
    assert sentence in problem


def test_a_reference_sentence_does_not_quote_the_reference() -> None:
    for reference in ("address:secret.person", "name:secret\x00", "secret:thing", "circle:"):
        problem = reference_problem(reference)
        assert problem is not None
        assert "secret" not in problem
        assert reference not in problem


def test_model_author_names_the_client() -> None:
    assert model_author("claude-desktop") == "model:claude-desktop"


# --- Folding --------------------------------------------------------------------


def row(
    row_id: int, statement: Statement | None, *, erased: bool = False
) -> tuple[int, datetime, Mapping[str, object] | None]:
    payload = None if erased or statement is None else payload_of(statement)
    return row_id, NOW + timedelta(minutes=row_id), payload


def test_a_first_version_is_named_after_its_own_event() -> None:
    threads = fold([row(4, make_obligation())])

    assert set(threads) == {4}
    assert threads[4].subject == 4
    assert threads[4].kind == OBLIGATION
    winner = threads[4].winner()
    assert winner is not None
    assert winner.id == 4
    assert winner.recorded_at == NOW + timedelta(minutes=4)


def test_a_direct_version_beats_a_newer_proposal() -> None:
    threads = fold(
        [
            row(1, make_obligation()),
            row(2, make_obligation(responsibility=OPEN, subject=1, due=date(2026, 12, 24))),
        ]
    )

    thread = threads[1]
    winner = thread.winner()
    assert winner is not None
    assert winner.id == 1
    assert [version.id for version in thread.pending()] == [2]


def test_without_a_direct_version_the_latest_open_one_stands_as_proposal() -> None:
    threads = fold(
        [
            row(1, make_obligation(responsibility=OPEN)),
            row(2, make_obligation(responsibility=OPEN, subject=1)),
        ]
    )

    winner = threads[1].winner()
    assert winner is not None
    assert winner.id == 2
    assert winner.statement.responsibility == OPEN


def test_without_a_direct_version_every_unanswered_proposal_is_pending() -> None:
    threads = fold(
        [
            row(1, make_obligation(responsibility=OPEN)),
            row(2, make_obligation(responsibility=OPEN, subject=1)),
            row(3, make_rejection(1)),
        ]
    )

    assert [version.id for version in threads[1].pending()] == [2]


def test_a_rejection_is_attached_to_the_thread_of_its_proposal() -> None:
    threads = fold(
        [
            row(1, make_obligation()),
            row(2, make_obligation(responsibility=OPEN, subject=1)),
            row(3, make_rejection(2)),
        ]
    )

    assert threads[1].rejected == frozenset({2})
    assert threads[1].pending() == ()
    assert set(threads) == {1}


def test_an_approval_takes_the_proposal_out_of_the_pending_ones() -> None:
    threads = fold(
        [
            row(1, make_obligation()),
            row(2, make_obligation(responsibility=OPEN, subject=1, due=date(2026, 12, 24))),
            row(
                3,
                make_obligation(
                    subject=1, approves=2, author=model_author("claude"), due=date(2026, 12, 24)
                ),
            ),
        ]
    )

    thread = threads[1]
    assert thread.approved == frozenset({2})
    assert thread.pending() == ()
    winner = thread.winner()
    assert winner is not None
    assert winner.id == 3
    assert winner.statement.responsibility == DIRECT
    assert winner.statement.author == model_author("claude")


def test_when_the_winning_direct_version_is_erased_the_earlier_direct_one_stands() -> None:
    erased = fold(
        [
            row(1, make_obligation(what="first")),
            row(2, make_obligation(subject=1, what="second"), erased=True),
            row(3, make_obligation(responsibility=OPEN, subject=1, what="proposal")),
        ]
    )

    fallback = erased[1].winner()
    assert fallback is not None
    assert fallback.id == 1  # the next direct version, not the proposal
    assert [version.id for version in erased[1].pending()] == [3]


def test_when_no_direct_version_is_left_the_proposal_shows_as_proposal() -> None:
    threads = fold(
        [
            row(1, make_obligation(), erased=True),
            row(2, make_obligation(responsibility=OPEN)),
        ]
    )

    winner = threads[2].winner()
    assert winner is not None
    assert winner.statement.responsibility == OPEN


def test_an_erased_approval_makes_its_proposal_stand_again() -> None:
    threads = fold(
        [
            row(1, make_obligation(responsibility=OPEN)),
            row(2, make_obligation(subject=1, approves=1), erased=True),
        ]
    )

    assert threads[1].approved == frozenset()
    winner = threads[1].winner()
    assert winner is not None
    assert winner.id == 1


def test_an_erased_rejection_leaves_the_proposal_pending() -> None:
    threads = fold(
        [
            row(1, make_obligation()),
            row(2, make_obligation(responsibility=OPEN, subject=1)),
            row(3, make_rejection(2), erased=True),
        ]
    )

    assert [version.id for version in threads[1].pending()] == [2]


def test_a_thread_with_an_erased_first_version_is_gone() -> None:
    threads = fold(
        [
            row(1, make_obligation(), erased=True),
            row(2, make_obligation(subject=1)),
        ]
    )

    assert threads == {}


def test_a_row_with_a_form_fault_is_skipped() -> None:
    broken = {**payload_of(make_obligation()), "due": "30.11.2026"}

    threads = fold([(1, NOW, broken), row(2, make_obligation())])

    assert set(threads) == {2}


@pytest.mark.parametrize(
    "statement",
    [
        make_obligation(subject=99),  # nothing stands there
        make_obligation(subject=2),  # a decision stands there: wrong kind
        make_obligation(subject=1, approves=99),
        make_obligation(subject=1, approves=1),  # approving a direct version
        make_rejection(99),
        make_rejection(5),  # the rejection's own id: nothing earlier
    ],
)
def test_a_dangling_reference_is_ignored(statement: Statement) -> None:
    threads = fold([row(1, make_obligation()), row(2, make_decision()), row(5, statement)])

    assert set(threads) == {1, 2}
    assert [version.id for version in threads[1].versions] == [1]
    assert [version.id for version in threads[2].versions] == [2]
    assert threads[1].rejected == frozenset()
    assert threads[2].rejected == frozenset()


def test_a_decision_thread_keeps_its_kind() -> None:
    threads = fold([row(1, make_decision()), row(2, make_decision(subject=1, state="revoked"))])

    assert threads[1].kind == DECISION
    assert len(threads[1].versions) == 2


def test_a_rejection_of_a_rejection_is_ignored() -> None:
    threads = fold(
        [row(1, make_obligation()), row(2, make_rejection(1)), row(3, make_rejection(2))]
    )

    assert threads[1].rejected == frozenset({1})


# --- The property: who wins -----------------------------------------------------

ops = st.lists(
    st.tuples(
        st.sampled_from(["direct", "open", "reject", "approve"]),
        st.integers(min_value=0, max_value=30),
    ),
    min_size=1,
    max_size=14,
)
erasures = st.sets(st.integers(min_value=2, max_value=15), max_size=6)


def build_rows(
    steps: list[tuple[str, int]], erased: set[int]
) -> list[tuple[int, datetime, Mapping[str, object] | None]]:
    rows = [row(1, make_obligation(what="v1"))]
    open_ids: list[int] = []
    for number, (action, pick) in enumerate(steps, start=2):
        target = open_ids[pick % len(open_ids)] if open_ids else None
        if action == "direct":
            statement = make_obligation(subject=1, what=f"v{number}")
        elif action == "open":
            statement = make_obligation(responsibility=OPEN, subject=1, what=f"v{number}")
            open_ids.append(number)
        elif action == "reject" and target is not None:
            statement = make_rejection(target)
        elif action == "approve" and target is not None:
            statement = make_obligation(subject=1, approves=target, what=f"v{number}")
        else:
            statement = make_obligation(responsibility=OPEN, subject=1, what=f"v{number}")
            open_ids.append(number)
        rows.append(row(number, statement, erased=number in erased))
    return rows


@given(steps=ops, erased=erasures)
def test_the_winner_is_the_latest_direct_else_the_latest_unanswered_open(
    steps: list[tuple[str, int]], erased: set[int]
) -> None:
    rows = build_rows(steps, erased)
    thread = fold(rows)[1]

    # The expectation is worked out from the rows alone, not from `fold`.
    parsed = {
        row_id: parse_statement(payload) for row_id, _at, payload in rows if payload is not None
    }
    standing = {row_id: s for row_id, s in parsed.items() if s is not None}
    # An approval of something that does not stand is not itself a version.
    for row_id, s in list(standing.items()):
        if s.approves is not None and s.approves not in standing:
            del standing[row_id]
    rejected = {
        s.of
        for s in standing.values()
        if s.kind == REJECTION and s.of in standing and standing[s.of].kind == OBLIGATION
    }
    approved = {
        s.approves
        for s in standing.values()
        if s.approves is not None and s.approves in standing and s.subject == 1
    }
    direct = [i for i, s in standing.items() if s.kind == OBLIGATION and s.responsibility == DIRECT]
    unanswered = [
        i
        for i, s in standing.items()
        if s.kind == OBLIGATION
        and s.responsibility == OPEN
        and i not in rejected
        and i not in approved
    ]
    expected = direct[-1] if direct else (unanswered[-1] if unanswered else None)

    winner = thread.winner()
    assert (winner.id if winner else None) == expected
    if direct:
        assert winner is not None
        assert winner.statement.responsibility == DIRECT
        newer = [i for i in unanswered if i > direct[-1]]
        assert [version.id for version in thread.pending()] == newer
    else:
        assert [version.id for version in thread.pending()] == unanswered


# --- Changes --------------------------------------------------------------------


def test_changes_names_exactly_the_changed_fields() -> None:
    before = make_obligation()
    after = make_obligation(
        due=date(2026, 12, 24),
        reason="the customer asked for a delay",
        sources=(Source(5, None), Source(8, (2,))),
    )

    assert changes(before, after) == (
        ("due", "2026-11-30", "2026-12-24"),
        ("sources", "event 5", "event 5; event 8 units 2"),
        ("reason", "(none)", "the customer asked for a delay"),
    )


def test_changes_is_empty_for_the_same_content() -> None:
    assert changes(make_obligation(), make_obligation(responsibility=OPEN, subject=3)) == ()


def test_changes_ignores_author_and_responsibility_but_sees_every_body_field() -> None:
    before = make_decision()
    after = make_decision(by=("own",), on=date(2026, 12, 1), state="revoked", replaces=4)

    assert [name for name, _old, _new in changes(before, after)] == [
        "by",
        "on",
        "state",
        "replaces",
    ]
    assert changes(before, make_decision(responsibility=OPEN)) == ()


def test_changes_between_unlike_kinds_lists_the_fields_of_both() -> None:
    names = [name for name, _old, _new in changes(make_obligation(), make_decision())]

    assert "debtor" in names
    assert "replaces" in names


# --- Overdue --------------------------------------------------------------------


def due_body(due: date | None, state: str = "open") -> ObligationBody:
    return ObligationBody("own", "circle:acme", "x", due, state)


@pytest.mark.parametrize(
    ("due", "state", "late"),
    [
        (TODAY - timedelta(days=1), "open", True),
        (TODAY, "open", False),
        (TODAY + timedelta(days=1), "open", False),
        (None, "open", False),
        (TODAY - timedelta(days=1), "fulfilled", False),
        (TODAY - timedelta(days=1), "cancelled", False),
    ],
)
def test_overdue(due: date | None, state: str, late: bool) -> None:
    assert overdue(due_body(due, state), TODAY) is late
