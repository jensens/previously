# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The policy events: their form, the write path, and reading the policy at a
point in time."""

from datetime import datetime
from datetime import timedelta
from datetime import UTC
from previously.core.action import append_action
from previously.core.policy import check_payload
from previously.core.policy import Circle
from previously.core.policy import Inference
from previously.core.policy import LOCAL_ONLY
from previously.core.policy import Membership
from previously.core.policy import OwnIdentity
from previously.core.policy import PolicyRefused
from previously.core.policy import Provider
from previously.core.policy import read_policy
from previously.core.policy import Rule
from previously.core.policy import set_policy
from previously.core.policy import to_payload
from previously.core.verify import verify
from previously.storage.postgres import PostgresStorage
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from previously.core.policy import Statement
    from sqlalchemy import Engine


T0 = datetime(2026, 10, 9, 12, 0, 0, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)
T2 = T0 + timedelta(hours=2)

RULE_EU = Rule("circle:xz", frozenset({"eu"}), 30, frozenset({"anthropic"}))
ANTHROPIC = Provider(
    "anthropic",
    (Inference("global", frozenset({"any"})), Inference("us", frozenset({"us"}))),
    frozenset({"us"}),
    30,
    True,
    False,
)


def _count(storage: PostgresStorage) -> int:
    with storage.begin() as conn:
        return len(list(storage.read_by_kind(conn, "action")))


def _read(storage: PostgresStorage, *, at: datetime | None = None):
    with storage.begin() as conn:
        return read_policy(storage, conn, at=at)


def _erase(storage: PostgresStorage, event_id: int) -> None:
    """The payload gone, as an erasure leaves it. `redact` refuses an action
    today, so the tombstone is made at the storage level, which is what an
    erasure of a policy event would do."""
    with storage.begin() as conn:
        storage.erase_payload(conn, event_id)


def test_the_name_of_the_built_in_rule() -> None:
    assert LOCAL_ONLY == "local_only"


@pytest.mark.db
def test_every_kind_is_written_and_read_back(db: Engine) -> None:
    storage = PostgresStorage(db)
    ids = [
        set_policy(storage, item, statement="why", recorded_at=T0)
        for item in (
            Circle("xz"),
            Membership("xz", "eva@kunde-xz.at"),
            OwnIdentity("@mine.example"),
            RULE_EU,
            ANTHROPIC,
        )
    ]
    policy = _read(storage)
    assert policy.circles == {"xz": Circle("xz")}
    assert policy.memberships == (Membership("xz", "eva@kunde-xz.at"),)
    assert policy.own == (OwnIdentity("@mine.example"),)
    assert policy.rules == {"circle:xz": RULE_EU}
    assert set(policy.providers) == {"anthropic"}
    assert policy.providers["anthropic"].inference == ANTHROPIC.inference
    assert sorted(policy.ids.values()) == ids
    assert verify(storage) == []


@pytest.mark.db
def test_a_newer_event_with_the_same_key_replaces_the_older(db: Engine) -> None:
    storage = PostgresStorage(db)
    set_policy(storage, RULE_EU, statement="first", recorded_at=T0)
    wider = Rule("circle:xz", frozenset({"eu", "us"}), None, frozenset())
    second = set_policy(storage, wider, statement="second", recorded_at=T1)
    policy = _read(storage)
    assert policy.rules == {"circle:xz": wider}
    assert policy.ids[("rule", "circle:xz")] == second


@pytest.mark.db
def test_a_revocation_lifts_the_statement(db: Engine) -> None:
    storage = PostgresStorage(db)
    set_policy(storage, Circle("xz"), statement="s", recorded_at=T0)
    set_policy(storage, Circle("xz"), statement="gone", revoked=True, recorded_at=T1)
    policy = _read(storage)
    assert policy.circles == {}
    assert policy.ids == {}
    # The control: the revoked statement is still in the chain.
    assert _count(storage) == 2


@pytest.mark.db
def test_a_domain_spelled_with_capitals_is_one_key(db: Engine) -> None:
    """A revocation typed with another case of the domain has to find the
    membership; the local part stays as it stands."""
    storage = PostgresStorage(db)
    set_policy(storage, Circle("xz"), statement="s", recorded_at=T0)
    set_policy(storage, Membership("xz", "Eva@Kunde-XZ.at"), statement="s", recorded_at=T0)
    assert _read(storage).memberships == (Membership("xz", "Eva@kunde-xz.at"),)
    set_policy(
        storage, Membership("xz", "Eva@KUNDE-xz.AT"), statement="s", revoked=True, recorded_at=T1
    )
    assert _read(storage).memberships == ()


@pytest.mark.db
def test_at_reads_the_policy_of_that_day(db: Engine) -> None:
    storage = PostgresStorage(db)
    set_policy(storage, RULE_EU, statement="first", recorded_at=T0)
    wider = Rule("circle:xz", frozenset({"any"}), None, frozenset())
    set_policy(storage, wider, statement="second", recorded_at=T2)
    assert _read(storage, at=T1).rules == {"circle:xz": RULE_EU}
    assert _read(storage, at=T2).rules == {"circle:xz": wider}
    assert _read(storage, at=T0 - timedelta(seconds=1)).rules == {}
    assert _read(storage).rules == {"circle:xz": wider}


@pytest.mark.db
def test_an_erased_policy_event_counts_for_nothing(db: Engine) -> None:
    """The version before applies; the erasure of the only version leaves no
    statement."""
    storage = PostgresStorage(db)
    set_policy(storage, RULE_EU, statement="first", recorded_at=T0)
    wider = Rule("circle:xz", frozenset({"any"}), None, frozenset())
    second = set_policy(storage, wider, statement="second", recorded_at=T1)
    _erase(storage, second)
    assert _read(storage).rules == {"circle:xz": RULE_EU}

    only = set_policy(storage, Circle("xz"), statement="s", recorded_at=T2)
    _erase(storage, only)
    assert _read(storage).circles == {}


@pytest.mark.db
@pytest.mark.parametrize(
    ("item", "sentence"),
    [
        (Membership("nowhere", "eva@kunde-xz.at"), 'no circle "nowhere" exists'),
        (
            Rule("project:alpha", frozenset({"eu"}), None, frozenset()),
            "is not effective yet",
        ),
        (Rule("everything", frozenset({"eu"}), None, frozenset()), "is not circle:<name>"),
        (Rule("circle:xz", frozenset(), None, frozenset()), "needs at least one region"),
        (Rule("circle:xz", frozenset({"any", "eu"}), None, frozenset()), 'combines "any"'),
        (Rule("circle:xz", frozenset({"mars"}), None, frozenset()), "not a region"),
        (Rule("circle:xz", frozenset({"eu"}), -1, frozenset()), "is negative"),
        (Membership("xz", "@localhost"), "not an address or a domain"),
        (OwnIdentity("someone"), "not an address or a domain"),
    ],
)
def test_a_refused_statement_is_one_sentence_and_writes_nothing(
    db: Engine, item: Statement, sentence: str
) -> None:
    storage = PostgresStorage(db)
    set_policy(storage, Circle("xz"), statement="s", recorded_at=T0)
    before = _count(storage)
    with pytest.raises(PolicyRefused, match=sentence):
        set_policy(storage, item, statement="s", recorded_at=T1)
    assert _count(storage) == before


@pytest.mark.db
@pytest.mark.parametrize("statement", ["", "   \t"])
def test_an_empty_sentence_is_refused(db: Engine, statement: str) -> None:
    storage = PostgresStorage(db)
    with pytest.raises(PolicyRefused, match="statement is empty"):
        set_policy(storage, Circle("xz"), statement=statement, recorded_at=T0)
    assert _count(storage) == 0


@pytest.mark.db
def test_a_membership_in_an_existing_circle_and_a_domain_with_a_dot_are_accepted(
    db: Engine,
) -> None:
    """The control of the refusals above."""
    storage = PostgresStorage(db)
    set_policy(storage, Circle("xz"), statement="s", recorded_at=T0)
    set_policy(storage, Membership("xz", "@kunde-xz.at"), statement="s", recorded_at=T0)
    assert _count(storage) == 2


@pytest.mark.db
def test_a_membership_in_a_circle_that_was_revoked_is_refused(db: Engine) -> None:
    storage = PostgresStorage(db)
    set_policy(storage, Circle("xz"), statement="s", recorded_at=T0)
    set_policy(storage, Circle("xz"), statement="s", revoked=True, recorded_at=T1)
    with pytest.raises(PolicyRefused, match='no circle "xz" exists'):
        set_policy(storage, Membership("xz", "eva@kunde-xz.at"), statement="s", recorded_at=T2)


def test_the_payload_has_sorted_sets_whatever_the_order_of_the_input() -> None:
    one = Rule("circle:xz", frozenset(["us", "eu"]), 0, frozenset(["b", "a"]))
    two = Rule("circle:xz", frozenset(["eu", "us"]), 0, frozenset(["a", "b"]))
    assert to_payload(one, statement="s") == to_payload(two, statement="s")
    assert to_payload(one, statement="s")["regions"] == ["eu", "us"]
    provider_one = Provider(
        "p",
        (Inference("us", frozenset({"us"})), Inference("global", frozenset({"any"}))),
        frozenset(["us", "eu"]),
        None,
        False,
        False,
    )
    provider_two = Provider(
        "p",
        (Inference("global", frozenset({"any"})), Inference("us", frozenset({"us"}))),
        frozenset(["eu", "us"]),
        None,
        False,
        False,
    )
    assert to_payload(provider_one, statement="s") == to_payload(provider_two, statement="s")


def test_the_payload_names_the_fields_of_the_specification() -> None:
    assert to_payload(Membership("xz", "a@b.at"), statement="why", revoked=True) == {
        "action": "policy",
        "policy": "membership",
        "circle": "xz",
        "member": "a@b.at",
        "statement": "why",
        "revoked": True,
    }


def test_check_payload_is_none_for_every_payload_the_write_path_makes() -> None:
    for item in (
        Circle("xz"),
        Membership("xz", "a@b.at"),
        OwnIdentity("@b.at"),
        RULE_EU,
        ANTHROPIC,
    ):
        assert check_payload(to_payload(item, statement="s")) is None


@pytest.mark.parametrize(
    ("payload", "sentence"),
    [
        ({"action": "policy", "statement": "s", "revoked": False}, "has no kind"),
        (
            {"action": "policy", "policy": "wish", "statement": "s", "revoked": False},
            'unknown kind "wish"',
        ),
        (
            {"action": "policy", "policy": "circle", "statement": "s", "revoked": False},
            'has no "name"',
        ),
        (
            {"action": "policy", "policy": "circle", "name": "xz", "revoked": False},
            'has no "statement"',
        ),
        (
            {"action": "policy", "policy": "circle", "name": "xz", "statement": "s"},
            'has no true or false "revoked"',
        ),
    ],
)
def test_check_payload_names_what_is_wrong(payload: dict[str, object], sentence: str) -> None:
    found = check_payload(payload)
    assert found is not None
    assert sentence in found


@pytest.mark.db
def test_verify_reports_a_policy_event_that_missed_the_write_path(db: Engine) -> None:
    storage = PostgresStorage(db)
    append_action(
        storage,
        {"action": "policy", "policy": "wish", "statement": "s", "revoked": False},
        (),
        recorded_at=T0,
    )
    (finding,) = verify(storage)
    assert 'unknown kind "wish"' in finding.reason
    # The read skips it and does not stop.
    assert _read(storage).circles == {}
