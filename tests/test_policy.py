# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The policy events: their form, the write path, and reading the policy at a
point in time."""

from datetime import datetime
from datetime import timedelta
from datetime import UTC
from previously.contract.types import RawUnit
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
from previously.core.verify import Finding
from previously.core.verify import verify
from previously.storage.postgres import PostgresStorage
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from collections.abc import Iterator
    from previously.contract.rows import EventRow
    from previously.core.policy import Statement
    from sqlalchemy import Connection
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
        STRICT,
        CHAINED,
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
@pytest.mark.parametrize("units", [True, False], ids=["with-units", "control"])
def test_verify_reports_a_policy_event_with_units(db: Engine, units: bool) -> None:
    """Spec §4.3 point 2 (frozen design record): a policy event has no
    units. One written past `set_policy` with a unit is a finding; the
    control, the same statement through `set_policy`, is none."""
    storage = PostgresStorage(db)
    if units:
        event_id = append_action(
            storage,
            to_payload(Circle("xz"), statement="customer", revoked=False),
            [RawUnit(1, "secret customer text")],
            recorded_at=T0,
        )
        assert verify(storage) == [Finding(event_id, "policy event has units")]
    else:
        set_policy(storage, Circle("xz"), statement="customer", recorded_at=T0)
        assert verify(storage) == []


class _RevokingAfterTheRead(PostgresStorage):
    """The real store, except that the first read of the actions through it,
    once its rows are read, revokes the circle `xz` through another store, in
    a transaction of its own that commits before the rows are handed on."""

    def __init__(self, engine: Engine, *, revoke: bool) -> None:
        super().__init__(engine)
        self._other = PostgresStorage(engine)
        self._revoke = revoke

    def read_by_kind(self, conn: Connection, kind: str) -> Iterator[EventRow]:
        rows = list(super().read_by_kind(conn, kind))
        if self._revoke:
            self._revoke = False
            set_policy(self._other, Circle("xz"), statement="gone", revoked=True, recorded_at=T0)
        return iter(rows)


@pytest.mark.db
@pytest.mark.parametrize("revoke", [True, False], ids=["revoked-meanwhile", "control"])
def test_a_membership_checked_while_its_circle_is_revoked_is_refused(
    db: Engine, revoke: bool
) -> None:
    """`set_policy` reads the policy, finds the circle, and the circle is
    revoked before the membership is written. The membership is written
    right after the tip read before the check, so the revocation holds that
    position, the attempt is lost, and the next one is refused.

    Written after a tip read at the write, as `write_action` does, the
    membership goes in behind the revocation and names a circle that no
    longer exists. The control revokes nothing, and the membership is
    written."""
    set_policy(PostgresStorage(db), Circle("xz"), statement="customer", recorded_at=T0)
    storage = _RevokingAfterTheRead(db, revoke=revoke)
    member = Membership("xz", "@example.net")
    if revoke:
        with pytest.raises(PolicyRefused, match='no circle "xz" exists'):
            set_policy(storage, member, statement="theirs", recorded_at=T0)
        assert member not in _read(storage).memberships
    else:
        set_policy(storage, member, statement="theirs", recorded_at=T0)
        assert member in _read(storage).memberships


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


CHAINED = Provider(
    "chained",
    (Inference("eu", frozenset({"eu"})),),
    frozenset({"eu"}),
    0,
    False,
    False,
    operator="acme",
    training=False,
    subprocessors=frozenset({"b-cloud", "a-cloud"}),
    model_origin="fr",
)
STRICT = Rule(
    "circle:xz",
    frozenset({"eu"}),
    None,
    frozenset(),
    no_training=True,
    no_subprocessors=True,
    excluded_operators=frozenset({"y", "x"}),
    excluded_model_origins=frozenset({"cn"}),
)


@pytest.mark.db
def test_the_processing_chain_and_the_restrictions_are_written_and_read_back(db: Engine) -> None:
    storage = PostgresStorage(db)
    set_policy(storage, CHAINED, statement="s", recorded_at=T0)
    set_policy(storage, STRICT, statement="s", recorded_at=T0)
    policy = _read(storage)
    assert policy.providers["chained"] == CHAINED
    assert policy.rules["circle:xz"] == STRICT


def test_the_chain_is_written_with_sorted_sets_and_null_for_unknown() -> None:
    payload = to_payload(CHAINED, statement="s")
    assert payload["subprocessors"] == ["a-cloud", "b-cloud"]
    assert (payload["operator"], payload["training"], payload["model_origin"]) == (
        "acme",
        False,
        "fr",
    )
    bare = to_payload(ANTHROPIC, statement="s")
    assert (bare["operator"], bare["training"], bare["subprocessors"], bare["model_origin"]) == (
        None,
        None,
        None,
        None,
    )
    assert to_payload(STRICT, statement="s")["excluded_operators"] == ["x", "y"]


def test_none_and_unknown_subprocessors_stay_apart_in_the_payload() -> None:
    none = Provider("p", (), frozenset(), 0, False, True, subprocessors=frozenset())
    assert to_payload(none, statement="s")["subprocessors"] == []
    assert to_payload(ANTHROPIC, statement="s")["subprocessors"] is None


@pytest.mark.db
def test_a_declaration_and_a_rule_from_before_the_chain_read_with_the_defaults(db: Engine) -> None:
    """Stored events are hash-chained and are not migrated: a payload without
    the new keys reads as unknown, and as no restriction."""
    storage = PostgresStorage(db)
    legacy_provider = to_payload(ANTHROPIC, statement="s")
    legacy_rule = to_payload(RULE_EU, statement="s")
    for key in ("operator", "training", "subprocessors", "model_origin"):
        del legacy_provider[key]
    for key in ("no_training", "no_subprocessors", "excluded_operators", "excluded_model_origins"):
        del legacy_rule[key]
    append_action(storage, legacy_provider, (), recorded_at=T0)
    append_action(storage, legacy_rule, (), recorded_at=T0)
    assert verify(storage) == []
    policy = _read(storage)
    assert policy.providers["anthropic"] == ANTHROPIC
    assert policy.rules["circle:xz"] == RULE_EU
    assert policy.providers["anthropic"].subprocessors is None
    assert policy.providers["anthropic"].training is None


@pytest.mark.parametrize(
    ("key", "value", "sentence"),
    [
        ("training", "no", 'a "training" that is not true, false or null'),
        ("operator", 3, 'a "operator" that is not text'),
        ("subprocessors", "aws", 'has no list "subprocessors"'),
    ],
)
def test_check_payload_names_a_chain_field_of_the_wrong_kind(
    key: str, value: object, sentence: str
) -> None:
    payload = to_payload(CHAINED, statement="s")
    payload[key] = value
    found = check_payload(payload)
    assert found is not None
    assert sentence in found


@pytest.mark.db
def test_a_client_is_a_statement_of_its_own_kind(db: Engine) -> None:
    from previously.core.policy import Client

    storage = PostgresStorage(db)
    set_policy(storage, ANTHROPIC, statement="declared", recorded_at=T0)
    client = Client("claude-code", "anthropic", "0" * 64)
    event_id = set_policy(storage, client, statement="s", recorded_at=T1)
    policy = _read(storage)
    assert policy.clients == {"claude-code": client}
    assert policy.ids[("client", "claude-code")] == event_id
    assert to_payload(client, statement="s")["policy"] == "client"
    assert verify(storage) == []


@pytest.mark.db
@pytest.mark.parametrize(
    ("name", "processor", "token_sha256"),
    [
        ("", "anthropic", "0" * 64),
        ("c", "", "0" * 64),
        ("c", "anthropic", "0" * 63),
        ("c", "anthropic", "G" * 64),
    ],
)
def test_a_client_of_a_wrong_form_is_refused(
    db: Engine, name: str, processor: str, token_sha256: str
) -> None:
    from previously.core.policy import Client

    storage = PostgresStorage(db)
    set_policy(storage, ANTHROPIC, statement="declared", recorded_at=T0)
    before = _count(storage)
    with pytest.raises(PolicyRefused):
        set_policy(storage, Client(name, processor, token_sha256), statement="s", recorded_at=T1)
    assert _count(storage) == before


@pytest.mark.db
def test_a_client_with_an_undeclared_processor_is_refused_but_its_revocation_is_not(
    db: Engine,
) -> None:
    from previously.core.policy import Client

    storage = PostgresStorage(db)
    client = Client("c", "anthropic", "0" * 64)
    with pytest.raises(PolicyRefused, match="is not declared"):
        set_policy(storage, client, statement="s", recorded_at=T0)
    set_policy(storage, ANTHROPIC, statement="declared", recorded_at=T0)
    set_policy(storage, client, statement="s", recorded_at=T1)
    # The provider goes; lifting the client still has to work.
    set_policy(storage, ANTHROPIC, statement="gone", revoked=True, recorded_at=T2)
    set_policy(storage, client, statement="gone", revoked=True, recorded_at=T2)
    assert _read(storage).clients == {}


@pytest.mark.db
def test_a_client_event_with_a_damaged_hash_is_skipped_and_a_lookup_returns_none(
    db: Engine,
) -> None:
    """A hash that is not 64 lower-case hex digits, such as one with a
    non-ASCII character that `hmac.compare_digest` would raise on, makes the
    event malformed: the read skips it and a lookup finds no client."""
    from previously.core.clients import client_for_token
    from previously.core.policy import Client

    storage = PostgresStorage(db)
    set_policy(storage, ANTHROPIC, statement="declared", recorded_at=T0)
    good = Client("good", "anthropic", "0" * 64)
    set_policy(storage, good, statement="s", recorded_at=T0)
    damaged = to_payload(Client("bad", "anthropic", "0" * 64), statement="s")
    damaged["token_sha256"] = "é" * 64
    append_action(storage, damaged, (), recorded_at=T1)
    policy = _read(storage)
    assert policy.clients == {"good": good}
    assert client_for_token(policy, "any token") is None
