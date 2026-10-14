# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Assertions in the log: the write path, reading by folding, and the policy
verdict and circles of a thread.

The write path writes a batch in one transaction, under the row lock of
every source, and refuses with one sentence that holds no text of an
assertion and no address. The erasure cascade is in `tests/test_cascade.py`,
the form checks of `verify` in `tests/test_verify.py`.
"""

from dataclasses import replace
from datetime import date
from datetime import datetime
from datetime import UTC
from previously.contract.types import ChannelIdentity
from previously.contract.types import Evidence
from previously.contract.types import RawEvent
from previously.contract.types import RawUnit
from previously.core.action import append_action
from previously.core.append import append
from previously.core.assertion import changes
from previously.core.assertion import DECISION
from previously.core.assertion import DecisionBody
from previously.core.assertion import DIRECT
from previously.core.assertion import model_author
from previously.core.assertion import OBLIGATION
from previously.core.assertion import ObligationBody
from previously.core.assertion import OPEN
from previously.core.assertion import OPERATOR
from previously.core.assertion import REJECTION
from previously.core.assertion import Source
from previously.core.assertion import Statement
from previously.core.assertion import Thread
from previously.core.assertion import Version
from previously.core.assertions import assertion_decisions
from previously.core.assertions import assertion_verdict
from previously.core.assertions import AssertionRefused
from previously.core.assertions import check_statements
from previously.core.assertions import read_source_events
from previously.core.assertions import read_threads
from previously.core.assertions import source_identities
from previously.core.assertions import thread_circles
from previously.core.assertions import write_statements
from previously.core.classes import ApprovalClass
from previously.core.classes import set_class
from previously.core.decide import Decision
from previously.core.graph import ACTIVE
from previously.core.graph import Claim
from previously.core.graph import ENTITY
from previously.core.graph import EntityBody
from previously.core.graph import Graph
from previously.core.graph import SOURCES
from previously.core.graph import TRANSITIVE
from previously.core.graph_write import read_graph
from previously.core.graph_write import write_claims
from previously.core.policy import ANY
from previously.core.policy import Circle
from previously.core.policy import Client
from previously.core.policy import Inference
from previously.core.policy import Membership
from previously.core.policy import OwnIdentity
from previously.core.policy import Policy
from previously.core.policy import Provider
from previously.core.policy import Rule
from previously.core.redact import redact_event
from previously.core.redact import redact_units
from previously.core.verify import verify
from previously.core.vocabulary import apply_vocabulary
from previously.core.vocabulary import base_vocabulary
from previously.core.vocabulary import parse_file
from previously.storage.postgres import PostgresStorage
from sqlalchemy import event
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from sqlalchemy import Engine


NOW = datetime(2026, 11, 1, 12, 0, 0, tzinfo=UTC)
LATER = datetime(2026, 11, 2, 12, 0, 0, tzinfo=UTC)
WHAT = "send the offer for the roof"
ADDRESS = "anna@huber.example"


def _mail(external_id: str, *addresses: str) -> RawEvent:
    return RawEvent(
        source="email",
        external_id=external_id,
        occurred_at=datetime(2026, 10, 30, 9, 0, 0, tzinfo=UTC),
        evidence=Evidence.VERBATIM,
        units=(RawUnit(1, "One."), RawUnit(2, "Two."), RawUnit(3, "Three.")),
        payload={"text": "One. Two. Three."},
        channel_identities=tuple(ChannelIdentity("email", "from", a) for a in addresses),
    )


def _setup(db: Engine, mails: int = 2) -> PostgresStorage:
    """A log with `mails` observations, ids 1 to `mails`."""
    storage = PostgresStorage(db)
    append(storage, [_mail(f"m{n}") for n in range(1, mails + 1)], recorded_at=NOW)
    return storage


def obligation(
    *sources: Source,
    responsibility: str = DIRECT,
    author: str = OPERATOR,
    subject: int | None = None,
    approves: int | None = None,
    handle: str | None = None,
    what: str = WHAT,
    due: date | None = date(2026, 11, 30),
    debtor: str = "own",
    creditor: str = f"address:{ADDRESS}",
) -> Statement:
    return Statement(
        OBLIGATION,
        author,
        responsibility,
        sources or (Source(1, None),),
        None,
        handle,
        subject,
        approves,
        None,
        ObligationBody(debtor, creditor, what, due, "open"),
    )


def proposal(*sources: Source, subject: int | None = None, handle: str | None = None) -> Statement:
    return obligation(
        *sources,
        responsibility=OPEN,
        author=model_author("claude-code"),
        subject=subject,
        handle=handle,
    )


def approval(of: Statement, proposal_id: int, subject: int) -> Statement:
    """The approval a caller builds: the proposal's content, sources and
    author, direct, pointing at it."""
    return replace(of, responsibility=DIRECT, subject=subject, approves=proposal_id, handle=None)


def rejection(of: int, *sources: Source) -> Statement:
    return Statement(
        REJECTION,
        OPERATOR,
        DIRECT,
        sources or (Source(1, None),),
        "not what was said",
        None,
        None,
        None,
        of,
        None,
    )


def decision(
    *sources: Source, subject: int | None = None, replaces: int | None = None
) -> Statement:
    return Statement(
        DECISION,
        OPERATOR,
        DIRECT,
        sources or (Source(1, None),),
        None,
        None,
        subject,
        None,
        None,
        DecisionBody("use slate", ("own",), date(2026, 10, 30), "valid", replaces),
    )


def _write(storage: PostgresStorage, *statements: Statement) -> tuple[int, ...]:
    return write_statements(storage, storage, statements, recorded_at=NOW)


def _threads(storage: PostgresStorage) -> dict[int, Thread]:
    with storage.begin() as conn:
        return read_threads(storage, conn)


def _count(storage: PostgresStorage) -> int:
    with storage.begin() as conn:
        return storage.count_events(conn)


def _ids(versions: tuple[Version, ...]) -> list[int]:
    return [version.id for version in versions]


# --- writing and reading ------------------------------------------------------------


@pytest.mark.db
def test_an_obligation_in_three_versions_reads_back_with_its_winner_and_history(
    db: Engine,
) -> None:
    storage = _setup(db)
    (first,) = _write(storage, obligation(Source(1, (1, 2))))
    (second,) = _write(storage, obligation(Source(2, None), subject=first, due=date(2026, 12, 4)))
    (third,) = _write(storage, proposal(Source(2, (3,)), subject=first))

    threads = _threads(storage)

    assert list(threads) == [first]
    thread = threads[first]
    assert thread.kind == OBLIGATION
    assert _ids(thread.versions) == [first, second, third]
    winner = thread.winner()
    assert winner is not None
    assert winner.id == second  # a younger proposal never beats a direct version
    assert _ids(thread.pending()) == [third]
    assert winner.recorded_at == NOW
    assert changes(thread.versions[0].statement, winner.statement) == (
        ("due", "2026-11-30", "2026-12-04"),
        ("sources", "event 1 units 1, 2", "event 2"),
    )
    assert verify(storage) == []


@pytest.mark.db
def test_an_assertion_is_an_event_of_the_kind_assertion_with_no_units(db: Engine) -> None:
    storage = _setup(db)
    (written,) = _write(storage, obligation())

    with storage.begin() as conn:
        (row,) = list(storage.read(conn, written, 1))
        units = storage.units_by_event(conn, [written])
        keys = storage.source_keys(conn, [written])

    assert row.kind == "assertion"
    assert row.occurred_at == row.recorded_at == NOW
    assert units == {}
    assert keys == {}


@pytest.mark.db
def test_a_batch_is_written_in_order_and_one_version_can_name_another_of_the_batch(
    db: Engine,
) -> None:
    storage = _setup(db)
    ids = _write(storage, obligation(), obligation(subject=3, due=None), decision())

    assert ids == (3, 4, 5)
    threads = _threads(storage)
    assert _ids(threads[3].versions) == [3, 4]
    assert threads[5].kind == DECISION


@pytest.mark.db
def test_a_second_write_with_the_same_handle_writes_nothing_and_returns_the_same_ids(
    db: Engine,
) -> None:
    """The handle of the MCP confirmation makes confirming twice harmless
    (decision 9 of the plan): the second call finds the assertions that
    carry it and returns their ids."""
    storage = _setup(db)
    batch = (proposal(handle="nonce-1"), proposal(Source(2, None), handle="nonce-1"))
    first = write_statements(storage, storage, batch, recorded_at=NOW)
    size = _count(storage)

    again = write_statements(storage, storage, batch, recorded_at=LATER)

    assert again == first
    assert _count(storage) == size


@pytest.mark.db
def test_another_handle_or_none_writes_again(db: Engine) -> None:
    """The control: without the same handle, the same content is written
    once more, on the command line by asking first."""
    storage = _setup(db)
    first = _write(storage, proposal(handle="nonce-1"))
    second = _write(storage, proposal(handle="nonce-2"))
    third = _write(storage, proposal())
    fourth = _write(storage, proposal())

    assert len({*first, *second, *third, *fourth}) == 4


# --- refusals -----------------------------------------------------------------------


def _refused(storage: PostgresStorage, *statements: Statement) -> str:
    """Writes, expects a refusal, checks that nothing was written and that the
    sentence holds no text and no address; returns the sentence."""
    size = _count(storage)
    with pytest.raises(AssertionRefused) as raised:
        _write(storage, *statements)
    assert _count(storage) == size
    message = str(raised.value)
    assert WHAT not in message
    assert ADDRESS not in message
    assert "\n" not in message
    return message


@pytest.mark.db
def test_a_source_that_does_not_exist_is_refused(db: Engine) -> None:
    storage = _setup(db)
    assert _refused(storage, obligation(Source(9, None))) == "there is no event 9 to rest on"


@pytest.mark.db
def test_an_erased_source_is_refused(db: Engine) -> None:
    storage = _setup(db)
    redact_event(storage, storage, 2, reason="wrong list", recorded_at=NOW)

    message = _refused(storage, obligation(Source(1, None), Source(2, (1,))))

    assert message == "event 2 is erased and cannot be a source"


@pytest.mark.db
def test_an_erased_unit_is_refused_and_the_other_units_are_not(db: Engine) -> None:
    storage = _setup(db)
    redact_units(storage, storage, 1, [2], reason="wrong", recorded_at=NOW)

    message = _refused(storage, obligation(Source(1, (1, 2))))

    assert message == "unit 2 of event 1 is erased and cannot be a source"
    # The control: the units left, and the whole event with them, still carry.
    assert len(_write(storage, obligation(Source(1, (1, 3))), obligation(Source(1, None)))) == 2


@pytest.mark.db
def test_a_unit_the_source_does_not_have_is_refused(db: Engine) -> None:
    storage = _setup(db)
    assert _refused(storage, obligation(Source(1, (4,)))) == "event 1 has no unit 4"


@pytest.mark.db
def test_a_source_that_is_not_an_observation_is_refused(db: Engine) -> None:
    """An assertion rests on what was observed. An action or another
    assertion as a source would need a cascade that follows a cascade."""
    storage = _setup(db)
    action = append_action(storage, {"action": "policy"}, (), recorded_at=NOW)
    (written,) = _write(storage, obligation())

    for event_id in (action, written):
        message = _refused(storage, obligation(Source(event_id, None)))
        assert message == f"event {event_id} is not an observation, and only one can be a source"


@pytest.mark.db
def test_a_statement_without_a_valid_form_is_refused(db: Engine) -> None:
    storage = _setup(db)
    bad = replace(obligation(), sources=())

    message = _refused(storage, bad)

    assert message == (
        "a statement has no valid form: "
        "the sources are empty: an assertion needs at least one source"
    )


@pytest.mark.db
def test_a_subject_that_names_nothing_or_another_kind_is_refused(db: Engine) -> None:
    storage = _setup(db)
    (first,) = _write(storage, obligation())
    (made,) = _write(storage, decision())

    assert _refused(storage, obligation(subject=99)) == (
        "the subject 99 names no obligation or decision that stands"
    )
    assert _refused(storage, obligation(subject=made)) == (
        f"the subject {made} is a decision, and this statement is an obligation"
    )
    # A later version is no subject: the subject is the first version's id.
    (later,) = _write(storage, obligation(subject=first))
    assert _refused(storage, obligation(subject=later)) == (
        f"the subject {later} names no obligation or decision that stands"
    )


@pytest.mark.db
def test_replaces_names_a_decision_or_nothing(db: Engine) -> None:
    storage = _setup(db)
    (owed,) = _write(storage, obligation())
    (made,) = _write(storage, decision())

    assert _refused(storage, decision(replaces=owed)) == (
        f"replaces names {owed}, which is no decision that stands"
    )
    assert len(_write(storage, decision(replaces=made))) == 1


@pytest.mark.db
def test_statements_of_one_batch_with_different_handles_are_refused(db: Engine) -> None:
    storage = _setup(db)
    assert _refused(storage, proposal(handle="a"), proposal(handle="b")) == (
        "the statements of one batch carry different handles"
    )


@pytest.mark.db
def test_an_empty_batch_is_refused(db: Engine) -> None:
    storage = _setup(db)
    assert _refused(storage) == "there is no statement to write"


@pytest.mark.db
def test_a_batch_with_one_refused_statement_writes_none_of_them(db: Engine) -> None:
    storage = _setup(db)
    message = _refused(storage, obligation(), obligation(Source(9, None)))
    assert message == "there is no event 9 to rest on"


# --- approval and rejection ---------------------------------------------------------


@pytest.mark.db
def test_an_approval_makes_the_proposal_direct(db: Engine) -> None:
    storage = _setup(db)
    made = proposal()
    (proposed,) = _write(storage, made)
    (approved,) = _write(storage, approval(made, proposed, proposed))

    thread = _threads(storage)[proposed]

    winner = thread.winner()
    assert winner is not None
    assert winner.id == approved
    assert winner.statement.responsibility == DIRECT
    assert winner.statement.author == model_author("claude-code")
    assert thread.approved == {proposed}
    assert thread.pending() == ()
    assert verify(storage) == []


@pytest.mark.db
def test_a_rejection_takes_the_proposal_out_of_the_open_points(db: Engine) -> None:
    storage = _setup(db)
    (proposed,) = _write(storage, proposal(Source(2, (1,))))
    _write(storage, rejection(proposed, Source(2, (1,))))

    thread = _threads(storage)[proposed]

    assert thread.winner() is None
    assert thread.rejected == {proposed}
    assert _ids(thread.versions) == [proposed]  # it stays in the history
    assert verify(storage) == []


@pytest.mark.db
def test_approving_what_is_approved_or_rejected_is_refused(db: Engine) -> None:
    """Review focus 2 of the plan: refused with one sentence, nothing
    written."""
    storage = _setup(db)
    made = proposal()
    (first, second) = _write(storage, made, made)
    _write(storage, approval(made, first, first))
    _write(storage, rejection(second))

    assert _refused(storage, approval(made, first, first)) == (
        f"the proposal {first} is already approved"
    )
    assert _refused(storage, approval(made, second, second)) == (
        f"the proposal {second} is already rejected"
    )
    assert _refused(storage, rejection(first)) == f"the proposal {first} is already approved"
    assert _refused(storage, rejection(second)) == f"the proposal {second} is already rejected"


@pytest.mark.db
def test_approving_an_erased_proposal_is_refused(db: Engine) -> None:
    storage = _setup(db)
    made = proposal()
    (proposed,) = _write(storage, made)
    (later,) = _write(storage, replace(made, subject=proposed))
    redact_event(storage, storage, proposed, reason="wrong", recorded_at=NOW)

    message = _refused(storage, approval(made, proposed, proposed))

    assert message == f"approves names {proposed}, which is no proposal of the subject {proposed}"
    # The control: the later proposal of the same thread stands and is approved.
    assert len(_write(storage, approval(made, later, proposed))) == 1


@pytest.mark.db
def test_two_approvals_of_one_proposal_in_one_batch_are_refused(db: Engine) -> None:
    storage = _setup(db)
    made = proposal()
    (proposed,) = _write(storage, made)

    message = _refused(
        storage, approval(made, proposed, proposed), approval(made, proposed, proposed)
    )

    assert message == f"the proposal {proposed} is already approved"


@pytest.mark.db
def test_a_proposal_a_later_direct_version_overtook_is_not_approved_but_still_rejected(
    db: Engine,
) -> None:
    """Ruling F-17 of the 2026-10-12 assertions plan: a proposal made before
    the direct version that stands now was made against an entry that no
    longer stands, and approving it would put its older content back over
    the newer. The check before the question says the same. The proposal
    made after the direct version is pending and is the control; once one
    approval of it is written, the second proposal it was written beside is
    overtaken too, in one batch as in two."""
    storage = _setup(db)
    (owned,) = _write(storage, obligation())
    made = proposal(subject=owned)
    (stale,) = _write(storage, made)
    (newer,) = _write(storage, obligation(subject=owned, due=date(2026, 12, 15)))
    fresh, beside = _write(storage, made, made)
    overtaken = f"the proposal {stale} is overtaken: the direct version {newer} came after it"

    assert _refused(storage, approval(made, stale, owned)) == overtaken
    with storage.begin() as conn, pytest.raises(AssertionRefused) as checked:
        check_statements(storage, conn, [approval(made, stale, owned)])
    assert str(checked.value) == overtaken
    assert _refused(storage, approval(made, fresh, owned), approval(made, beside, owned)) == (
        f"the proposal {beside} is overtaken: the direct version {beside + 1} came after it"
    )
    assert _write(storage, approval(made, fresh, owned)) == (beside + 1,)
    assert _write(storage, rejection(stale)) == (beside + 2,)
    assert verify(storage) == []


@pytest.mark.db
def test_an_approval_takes_the_proposal_unchanged(db: Engine) -> None:
    storage = _setup(db)
    made = proposal()
    (proposed,) = _write(storage, made)
    unchanged = (
        "an approval takes the content, the sources and the author of its proposal unchanged"
    )

    assert _refused(storage, replace(approval(made, proposed, proposed), author=OPERATOR)) == (
        unchanged
    )
    assert _refused(
        storage, replace(approval(made, proposed, proposed), sources=(Source(2, None),))
    ) == (unchanged)
    other = replace(made, body=ObligationBody("own", "circle:huber", WHAT, None, "open"))
    assert _refused(storage, replace(approval(other, proposed, proposed))) == unchanged
    # The reason is the approver's own.
    assert len(_write(storage, replace(approval(made, proposed, proposed), reason="checked"))) == 1


@pytest.mark.db
def test_an_approval_or_rejection_of_a_direct_version_or_another_thread_is_refused(
    db: Engine,
) -> None:
    storage = _setup(db)
    direct = obligation()
    made = proposal()
    (owned, proposed) = _write(storage, direct, made)

    assert _refused(storage, approval(direct, owned, owned)) == (
        f"the version {owned} is no proposal: it is direct"
    )
    assert _refused(storage, rejection(owned)) == (
        f"the version {owned} is no proposal: it is direct"
    )
    assert _refused(storage, approval(made, proposed, owned)) == (
        f"approves names {proposed}, which is no proposal of the subject {owned}"
    )
    assert _refused(storage, rejection(99)) == "of names 99, which is no proposal that stands"


@pytest.mark.db
def test_a_rejection_takes_the_sources_of_its_proposal(db: Engine) -> None:
    storage = _setup(db)
    (proposed,) = _write(storage, proposal(Source(2, (1,))))

    assert _refused(storage, rejection(proposed, Source(1, None))) == (
        "a rejection takes the sources of its proposal unchanged"
    )


# --- policy -------------------------------------------------------------------------


CLAUDE = Provider(
    "claude-max", (Inference("global", frozenset({ANY})),), frozenset({"us"}), 30, True, False
)
LOCAL = Provider("local", (Inference("eu", frozenset({"eu"})),), frozenset(), 0, False, True)
POLICY = Policy(
    circles={"huber": Circle("huber"), "bauer": Circle("bauer"), "team": Circle("team")},
    memberships=(
        Membership("huber", "@huber.example"),
        Membership("bauer", "@bauer.example"),
        Membership("team", "@example.org"),
    ),
    own=(OwnIdentity("@example.org"),),
    rules={
        "circle:huber": Rule("circle:huber", frozenset({ANY}), None, frozenset()),
        "source:email": Rule("source:email", frozenset({ANY}), None, frozenset()),
    },
    providers={"claude-max": CLAUDE, "local": LOCAL},
    ids={},
)
CLIENT = Client("claude-code", "claude-max", "0" * 64)


def _huber(address: str = ADDRESS) -> dict[str, object]:
    return {"channel": "email", "role": "from", "address": address, "name": None}


def test_a_source_in_a_circle_with_a_rule_lets_the_assertion_pass() -> None:
    verdict = assertion_verdict(POLICY, CLIENT, [_huber()], ("email",))
    assert verdict.chosen is not None
    assert verdict.circles == ("huber",)


def test_the_first_decision_that_chooses_nothing_wins() -> None:
    """Decision 7 of the plan: the strictest rule among all sources."""
    identities = [_huber(), _huber("max@bauer.example")]

    verdict = assertion_verdict(POLICY, CLIENT, identities, ("email", None))

    assert verdict.chosen is None
    assert verdict.circles == ("bauer", "huber")


def test_each_distinct_source_is_decided_and_the_last_wins_when_all_pass() -> None:
    policy = replace(
        POLICY,
        rules={
            **POLICY.rules,
            "source:gitlab": Rule("source:gitlab", frozenset({"eu"}), None, frozenset()),
        },
    )

    passing = assertion_verdict(policy, CLIENT, [_huber()], ("email",))
    stopped = assertion_verdict(policy, CLIENT, [_huber()], ("email", "gitlab"))
    reversed_order = assertion_verdict(policy, CLIENT, [_huber()], ("gitlab", "email"))

    assert passing.chosen is not None
    assert passing.rule_keys == ("circle:huber", "source:email")
    assert stopped.chosen is None
    assert stopped.rule_keys == ("circle:huber", "source:gitlab")
    assert reversed_order == stopped


def test_the_decisions_of_every_source_are_returned_so_that_no_rule_is_lost() -> None:
    """When every source passes, `assertion_verdict` is the last decision
    only; the rules of the other sources are in the decisions."""
    policy = replace(
        POLICY,
        rules={
            **POLICY.rules,
            "source:gitlab": Rule("source:gitlab", frozenset({"eu"}), None, frozenset()),
        },
    )
    decisions = assertion_decisions(policy, CLIENT, [_huber()], ("email", "gitlab"))
    passing = assertion_decisions(policy, CLIENT, [_huber()], ("email",))

    assert [d.rule_keys for d in decisions] == [
        ("circle:huber", "source:email"),
        ("circle:huber", "source:gitlab"),
    ]
    assert len(passing) == 1
    assert assertion_decisions(policy, CLIENT, [], ())[0].local_only


def test_no_source_at_all_is_decided_once_without_one() -> None:
    verdict = assertion_verdict(POLICY, CLIENT, [], ())
    assert isinstance(verdict, Decision)
    assert verdict.local_only
    assert verdict.chosen is None


def test_an_actor_named_in_an_assertion_changes_nothing_in_the_verdict() -> None:
    """The policy goes by the sources alone; the circles of the
    filter take the actors as well."""
    identities = [_huber()]
    made = obligation(debtor="circle:bauer", creditor="address:max@bauer.example")

    verdict = assertion_verdict(POLICY, CLIENT, identities, ("email",))

    assert verdict.chosen is not None
    assert thread_circles(POLICY, identities, made) == ("bauer", "huber")


def test_the_circles_of_a_thread_are_its_sources_and_its_actors() -> None:
    by_source = obligation(debtor="own", creditor="name:the hosting firm")
    by_circle = obligation(debtor="circle:office", creditor="own")
    by_address = decision()
    by_address = replace(
        by_address,
        body=DecisionBody(
            "use slate",
            ("address:max@bauer.example", "address:ben@example.org"),
            date(2026, 10, 30),
            "valid",
            None,
        ),
    )
    turned_down = rejection(5)

    assert thread_circles(POLICY, [_huber()], by_source) == ("huber",)
    assert thread_circles(POLICY, [], by_circle) == ("office",)
    # An own address belongs to no circle, as it does for a source.
    assert thread_circles(POLICY, [], by_address) == ("bauer",)
    assert thread_circles(POLICY, [], turned_down) == ()


@pytest.mark.db
def test_the_identities_and_sources_of_a_thread_are_those_of_all_its_versions(
    db: Engine,
) -> None:
    storage = PostgresStorage(db)
    append(
        storage,
        [_mail("m1", ADDRESS), _mail("m2", "max@bauer.example")],
        recorded_at=NOW,
    )
    other = RawEvent(
        source="gitlab",
        external_id="note-1",
        occurred_at=NOW,
        evidence=Evidence.VERBATIM,
        units=(RawUnit(1, "A note."),),
    )
    append(storage, [other], recorded_at=NOW)
    (first,) = _write(storage, obligation(Source(1, None)))
    _write(storage, proposal(Source(2, (1,)), Source(3, None), subject=first))

    with storage.begin() as conn:
        thread = read_threads(storage, conn)[first]
        identities, sources = source_identities(storage, conn, thread)

    assert [identity["address"] for identity in identities] == [ADDRESS, "max@bauer.example"]
    assert sources == ("email", "gitlab")
    verdict = assertion_verdict(POLICY, CLIENT, identities, sources)
    assert verdict.chosen is None


@pytest.mark.db
def test_more_statements_than_a_batch_holds_are_refused(db: Engine) -> None:
    storage = _setup(db)
    assert _refused(storage, *[obligation()] * 501) == "a batch holds at most 500 statements"


@pytest.mark.db
def test_a_text_the_log_cannot_hold_is_refused_without_the_text(db: Engine) -> None:
    storage = _setup(db)
    message = _refused(storage, obligation(what=f"{WHAT}\x00"))
    assert message == (
        "a statement cannot be written: "
        "$.what: null byte not allowed — PostgreSQL jsonb cannot store it"
    )


@pytest.mark.db
def test_the_check_before_the_question_refuses_what_the_canonical_form_refuses(
    db: Engine,
) -> None:
    """Ruling F-19 of the 2026-10-12 assertions plan: `check_statements`
    refuses with the sentence the write path refuses with. The statement
    without the surrogate passes, and is the control."""
    storage = _setup(db)
    broken = obligation(what="send \ud800 the offer")
    written = _refused(storage, broken)

    with storage.begin() as conn:
        with pytest.raises(AssertionRefused) as checked:
            check_statements(storage, conn, [broken])
        check_statements(storage, conn, [obligation()])

    assert str(checked.value) == written
    assert written.startswith("a statement cannot be written: $.what: string not representable")


@pytest.mark.db
def test_an_erased_source_adds_no_identity(db: Engine) -> None:
    """Only a log that came around the cascade has a standing assertion on
    an erased event; its identities are gone with its payload."""
    storage = PostgresStorage(db)
    append(storage, [_mail("m1", ADDRESS), _mail("m2", "max@bauer.example")], recorded_at=NOW)
    (owed,) = _write(storage, obligation(Source(1, None), Source(2, None)))
    with storage.begin() as conn:
        storage.erase_payload(conn, 2)

    with storage.begin() as conn:
        identities, sources = source_identities(storage, conn, read_threads(storage, conn)[owed])

    assert [identity["address"] for identity in identities] == [ADDRESS]
    assert sources == ("email",)


@pytest.mark.db
def test_the_source_events_of_many_threads_are_read_in_two_queries(db: Engine) -> None:
    """The rows and the source keys, one query each, however many threads
    and source events: read one at a time, they were most of the time a
    list took. Counted at the engine, on the statements the store sends.
    Each thread is then what `source_identities` makes of it alone."""
    storage = PostgresStorage(db)
    append(storage, [_mail(f"m{n}", ADDRESS) for n in range(1, 6)], recorded_at=NOW)
    names = [_write(storage, obligation(Source(n, None), Source(n + 1, None)))[0] for n in (1, 3)]
    with storage.begin() as conn:
        threads = [read_threads(storage, conn)[name] for name in names]
    statements: list[str] = []

    def counted(*args: object) -> None:
        statements.append(str(args[2]))

    event.listen(db, "before_cursor_execute", counted)
    try:
        with storage.begin() as conn:
            found = read_source_events(storage, conn, threads)
    finally:
        event.remove(db, "before_cursor_execute", counted)

    assert len(statements) == 2, statements
    with storage.begin() as conn:
        for thread in threads:
            assert found.of(thread) == source_identities(storage, conn, thread)


@pytest.mark.db
def test_a_thread_whose_source_events_were_not_read_is_refused(db: Engine) -> None:
    """An event left out would add no identity, and the policy would decide
    over fewer people than the sources name. The thread that was read is the
    control."""
    storage = PostgresStorage(db)
    append(storage, [_mail("m1", ADDRESS), _mail("m2", ADDRESS)], recorded_at=NOW)
    first, second = _write(storage, obligation(Source(1, None)), obligation(Source(2, None)))
    with storage.begin() as conn:
        threads = read_threads(storage, conn)
        found = read_source_events(storage, conn, [threads[first]])

    assert found.of(threads[first])[1] == ("email",)
    with pytest.raises(ValueError, match="the source events of this thread were not read"):
        found.of(threads[second])


@pytest.mark.db
def test_a_direct_version_by_a_model_is_refused(db: Engine) -> None:
    """Ruling F-6 of the 2026-10-12 assertions plan: a model's version is
    direct only as an approval. The control, a model's approval, is
    `test_an_approval_makes_the_proposal_direct`."""
    storage = _setup(db)
    (owned,) = _write(storage, obligation())

    message = _refused(
        storage, obligation(subject=owned, author=model_author("claude-code"), what="other")
    )

    assert (
        message
        == "a statement has no valid form: a version by a model is direct only as an approval"
    )


@pytest.mark.db
def test_check_statements_refuses_what_the_write_path_refuses_with_its_sentence_and_writes_nothing(
    db: Engine,
) -> None:
    """Ruling F-10 of the 2026-10-12 assertions plan: the preview of a
    command and of a tool can ask this before it asks anyone. The cases are
    the ones the write path refuses by source, by unit and by reference; the
    control is a batch that stands, which both accept."""
    storage = _setup(db, mails=3)
    redact_event(storage, storage, 3, reason="wrong", recorded_at=NOW)
    (first,) = _write(storage, obligation())
    cases = (
        obligation(Source(9, None)),
        obligation(Source(3, None)),
        obligation(Source(1, (4,))),
        obligation(subject=99),
        decision(replaces=1),
        approval(proposal(), 99, first),
    )
    before = _count(storage)
    for statement in cases:
        with storage.begin() as conn, pytest.raises(AssertionRefused) as checked:
            check_statements(storage, conn, [statement])
        assert str(checked.value) == _refused(storage, statement)
    assert _count(storage) == before
    good = obligation(Source(1, (1, 2)), subject=first)
    with storage.begin() as conn:
        check_statements(storage, conn, [good])
    assert len(_write(storage, good)) == 1


@pytest.mark.db
def test_check_statements_lets_a_repeated_handle_pass_as_the_write_path_does(db: Engine) -> None:
    """A batch whose handle is in the log is a repeat, answered with the ids;
    it must not be refused for what it did the first time (here, a proposal
    that is answered by now)."""
    storage = _setup(db)
    (first,) = _write(storage, proposal(handle="h-1"))
    (approved,) = _write(storage, approval(proposal(handle="h-1"), first, first))
    assert approved == first + 1
    with storage.begin() as conn:
        check_statements(storage, conn, [proposal(handle="h-1")])
        with pytest.raises(AssertionRefused):
            check_statements(storage, conn, [approval(proposal(), first, first)])


# --- rejections of entities and relations ------------------------------------------


MODEL = model_author("claude-code")


def _with_vocabulary(db: Engine) -> PostgresStorage:
    storage = _setup(db)
    apply_vocabulary(storage, parse_file(base_vocabulary()), recorded_at=NOW)
    return storage


def _person(
    *, author: str = MODEL, responsibility: str = OPEN, confidence: int | None = 40
) -> Claim:
    return Claim(
        ENTITY,
        author,
        responsibility,
        SOURCES,
        (Source(1, (2,)),),
        None,
        None,
        None,
        None,
        None,
        confidence,
        None,
        EntityBody("person", None, {"name": "Anna Huber"}, ACTIVE),
    )


def _claimed(storage: PostgresStorage, claim: Claim) -> int:
    (written,) = write_claims(storage, storage, [claim], recorded_at=NOW).ids
    return written


def _graph(storage: PostgresStorage) -> Graph:
    with storage.begin() as conn:
        return read_graph(storage, conn)


@pytest.mark.db
def test_a_rejection_of_an_open_entity_is_written_and_takes_it_out_of_the_graph(
    db: Engine,
) -> None:
    """Decision 5 of the 2026-10-14 assignments plan: `of` may name an open
    version of an entity, and the rejection takes its sources unchanged."""
    storage = _with_vocabulary(db)
    proposed = _claimed(storage, _person())
    assert _refused(storage, rejection(proposed)) == (
        "a rejection takes the sources of its proposal unchanged"
    )
    (rejected,) = _write(storage, rejection(proposed, Source(1, (2,))))
    graph = _graph(storage)
    assert graph.threads[proposed].rejected == {proposed}
    assert proposed not in graph.entities()
    assert _refused(storage, rejection(proposed, Source(1, (2,)))) == (
        f"the proposal {proposed} is already rejected"
    )
    assert rejected == proposed + 1
    assert verify(storage) == []


@pytest.mark.db
def test_two_rejections_of_one_entity_in_one_batch_are_refused(db: Engine) -> None:
    storage = _with_vocabulary(db)
    proposed = _claimed(storage, _person())
    rejected = rejection(proposed, Source(1, (2,)))
    assert _refused(storage, rejected, rejected) == f"the proposal {proposed} is already rejected"


@pytest.mark.db
def test_a_direct_or_approved_version_of_an_entity_is_not_rejected(db: Engine) -> None:
    storage = _with_vocabulary(db)
    direct = _claimed(storage, _person(author=OPERATOR, responsibility=DIRECT, confidence=None))
    assert _refused(storage, rejection(direct, Source(1, (2,)))) == (
        f"the version {direct} is no proposal: it is direct"
    )
    proposal_claim = _person()
    proposed = _claimed(storage, proposal_claim)
    _claimed(
        storage,
        replace(proposal_claim, responsibility=DIRECT, subject=proposed, approves=proposed),
    )
    assert _refused(storage, rejection(proposed, Source(1, (2,)))) == (
        f"the proposal {proposed} is already approved"
    )


@pytest.mark.db
def test_a_transitive_version_of_an_entity_is_rejected_like_a_proposal(db: Engine) -> None:
    storage = _with_vocabulary(db)
    item = ApprovalClass(
        "people", MODEL, ENTITY, frozenset({"person"}), 80, None, None, revoked=False,
        demote=False,
    )  # fmt: skip
    set_class(storage, item, statement="people", recorded_at=NOW)
    written = _claimed(storage, _person(confidence=90))
    (version,) = _graph(storage).threads[written].versions
    assert version.claim.responsibility == TRANSITIVE
    _write(storage, rejection(written, Source(1, (2,))))
    graph = _graph(storage)
    assert graph.threads[written].rejected == {written}
    assert written not in graph.entities()


@pytest.mark.db
def test_a_rejection_of_an_entity_is_refused_by_the_preview_with_the_same_sentence(
    db: Engine,
) -> None:
    storage = _with_vocabulary(db)
    direct = _claimed(storage, _person(author=OPERATOR, responsibility=DIRECT, confidence=None))
    with storage.begin() as conn, pytest.raises(AssertionRefused) as refused:
        check_statements(storage, conn, [rejection(direct, Source(1, (2,)))])
    assert str(refused.value) == f"the version {direct} is no proposal: it is direct"
