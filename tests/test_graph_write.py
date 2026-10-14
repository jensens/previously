# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Entities and relations in the log: the write path and its preview, the
level the write path gives a claim, the cycle rule, reading the graph, and
what the policy says of a claim.

The form and the fold are in `tests/test_graph.py`, the classes in
`tests/test_classes.py`. The rejection of a graph version through
`write_statements` is in `tests/test_assertions.py`, the erasure cascade in
`tests/test_cascade.py`, and the findings of `verify` in
`tests/test_verify.py`.
"""

from dataclasses import replace
from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import UTC
from previously.contract.types import ChannelIdentity
from previously.contract.types import Evidence
from previously.contract.types import RawEvent
from previously.contract.types import RawUnit
from previously.core.action import append_action
from previously.core.append import append
from previously.core.append import MAX_BATCH
from previously.core.assertion import DIRECT
from previously.core.assertion import model_author
from previously.core.assertion import OBLIGATION
from previously.core.assertion import ObligationBody
from previously.core.assertion import OPEN
from previously.core.assertion import OPERATOR
from previously.core.assertion import REJECTION
from previously.core.assertion import Source
from previously.core.assertion import Statement
from previously.core.assertions import check_statements
from previously.core.assertions import write_statements
from previously.core.classes import ApprovalClass
from previously.core.classes import class_payload
from previously.core.classes import class_refusal
from previously.core.classes import ClassRefused
from previously.core.classes import set_class
from previously.core.graph import ACTIVE
from previously.core.graph import Claim
from previously.core.graph import ENTITY
from previously.core.graph import EntityBody
from previously.core.graph import FieldValue
from previously.core.graph import Graph
from previously.core.graph import GraphThread
from previously.core.graph import GraphVersion
from previously.core.graph import Period
from previously.core.graph import RECOLLECTION
from previously.core.graph import RELATION
from previously.core.graph import RelationBody
from previously.core.graph import RETRACTED
from previously.core.graph import SOURCES
from previously.core.graph import STANDING
from previously.core.graph import START_NOT_A_SOURCE
from previously.core.graph import TRANSITIVE
from previously.core.graph_write import check_claims
from previously.core.graph_write import claim_sources
from previously.core.graph_write import claim_verdict
from previously.core.graph_write import CLASS_CHANGED
from previously.core.graph_write import closes_cycle
from previously.core.graph_write import Decided
from previously.core.graph_write import decided
from previously.core.graph_write import DIRECT_WRITTEN
from previously.core.graph_write import EntityTypes
from previously.core.graph_write import GraphRefused
from previously.core.graph_write import read_claim_events
from previously.core.graph_write import read_graph
from previously.core.graph_write import relation_visible
from previously.core.graph_write import write_claims
from previously.core.graph_write import Written
from previously.core.policy import ANY
from previously.core.policy import Client
from previously.core.policy import Inference
from previously.core.policy import Policy
from previously.core.policy import Provider
from previously.core.policy import Rule
from previously.core.verify import verify
from previously.core.vocabulary import apply_vocabulary
from previously.core.vocabulary import base_vocabulary
from previously.core.vocabulary import ENTITY_KIND
from previously.core.vocabulary import FieldSpec
from previously.core.vocabulary import KindSpec
from previously.core.vocabulary import parse_file
from previously.core.vocabulary import read_vocabulary
from previously.core.vocabulary import RELATION_KIND
from previously.storage.postgres import PostgresStorage
from typing import TYPE_CHECKING

import pytest
import threading


if TYPE_CHECKING:
    from collections.abc import Mapping
    from previously.contract.rows import Tip
    from sqlalchemy import Connection
    from sqlalchemy import Engine


T0 = datetime(2026, 10, 14, 9, 0, 0, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)
T2 = T0 + timedelta(hours=2)
T3 = T0 + timedelta(hours=3)
MODEL = model_author("claude")
ADDRESS = "anna@huber.example"

CLASS = ApprovalClass(
    "claude_people",
    MODEL,
    ENTITY,
    frozenset({"person", "project"}),
    80,
    None,
    None,
    revoked=False,
    demote=False,
)
EDGES = ApprovalClass(
    "claude_parts",
    MODEL,
    RELATION,
    frozenset({"part_of"}),
    80,
    None,
    None,
    revoked=False,
    demote=False,
)


# Two kinds beside the base vocabulary, which nothing else names, so that a
# test can retire them without retiring what names them.
TEAM = KindSpec(
    ENTITY_KIND,
    "team",
    {"en": "Team"},
    (FieldSpec("name", "text", None, None, True),),
    frozenset(),
    None,
    None,
    False,
)
LEADS = KindSpec(
    RELATION_KIND, "leads", {"en": "Leads"}, (), frozenset(), ("person",), ("team",), False
)


def _mail(external_id: str) -> RawEvent:
    return RawEvent(
        source="email",
        external_id=external_id,
        occurred_at=datetime(2026, 10, 1, 9, 0, 0, tzinfo=UTC),
        evidence=Evidence.VERBATIM,
        units=(RawUnit(1, "One."), RawUnit(2, "Two.")),
        payload={"text": "One. Two."},
        channel_identities=(ChannelIdentity("email", "from", ADDRESS),),
    )


def _setup(db: Engine, mails: int = 3) -> PostgresStorage:
    """Mails 1 to `mails`, then the base vocabulary with `team` and
    `leads`."""
    storage = PostgresStorage(db)
    append(storage, [_mail(f"m{n}") for n in range(1, mails + 1)], recorded_at=T0)
    apply_vocabulary(storage, (*parse_file(base_vocabulary()), TEAM, LEADS), recorded_at=T0)
    return storage


def entity(
    kind: str,
    name: str,
    *,
    author: str = OPERATOR,
    responsibility: str = DIRECT,
    evidence: str = SOURCES,
    sources: tuple[Source, ...] = (Source(1, None),),
    subject: int | None = None,
    approves: int | None = None,
    confidence: int | None = None,
    handle: str | None = None,
    state: str = ACTIVE,
    fields: Mapping[str, FieldValue] | None = None,
) -> Claim:
    return Claim(
        ENTITY,
        author,
        responsibility,
        evidence,
        () if evidence == RECOLLECTION else sources,
        None,
        handle,
        subject,
        approves,
        None,
        confidence,
        None,
        EntityBody(kind, "de", {"name": name, **(fields or {})}, state),
    )


def guess(kind: str, name: str, *, confidence: int = 90, **changes: object) -> Claim:
    """A model's entity, at the level the client would like: the write path
    takes none of it."""
    claim = entity(kind, name, author=MODEL, responsibility=OPEN, confidence=confidence)
    return replace(claim, **changes)


def relation(
    kind: str,
    start: int,
    to: int | None,
    *,
    author: str = OPERATOR,
    responsibility: str = DIRECT,
    sources: tuple[Source, ...] = (Source(1, None),),
    subject: int | None = None,
    approves: int | None = None,
    confidence: int | None = None,
    candidates: tuple[int, ...] | None = None,
    period: Period | None = None,
    state: str = STANDING,
) -> Claim:
    return Claim(
        RELATION,
        author,
        responsibility,
        SOURCES,
        sources,
        None,
        None,
        subject,
        approves,
        None,
        confidence,
        None,
        RelationBody(kind, start, to, candidates, period, {}, state),
    )


def edge(
    start: int,
    to: int,
    *,
    subject: int | None = None,
    state: str = STANDING,
    sources: tuple[Source, ...] = (Source(1, None),),
) -> Claim:
    """The operator's `part_of` edge."""
    return relation("part_of", start, to, subject=subject, state=state, sources=sources)


def model_edge(start: int, to: int, *, confidence: int = 90, **changes: object) -> Claim:
    claim = relation("part_of", start, to, author=MODEL, responsibility=OPEN, confidence=confidence)
    return replace(claim, **changes)


def _write(storage: PostgresStorage, *claims: Claim, at: datetime = T1) -> Written:
    return write_claims(storage, storage, claims, recorded_at=at)


def _ids(storage: PostgresStorage, *claims: Claim, at: datetime = T1) -> tuple[int, ...]:
    return _write(storage, *claims, at=at).ids


def _refused(
    storage: PostgresStorage,
    *claims: Claim,
    at: datetime = T1,
    expect: tuple[Decided, ...] | None = None,
) -> str:
    before = _count(storage)
    with pytest.raises(GraphRefused) as refused:
        write_claims(storage, storage, claims, recorded_at=at, expect=expect)
    assert _count(storage) == before
    return str(refused.value)


def _checked(storage: PostgresStorage, *claims: Claim, at: datetime = T1) -> tuple[Claim, ...]:
    with storage.begin() as conn:
        return check_claims(storage, conn, claims, recorded_at=at)


def _graph(storage: PostgresStorage, *, as_of: datetime | None = None) -> Graph:
    with storage.begin() as conn:
        return read_graph(storage, conn, as_of=as_of)


def _count(storage: PostgresStorage) -> int:
    with storage.begin() as conn:
        return storage.count_events(conn)


def _projects(storage: PostgresStorage, count: int) -> tuple[int, ...]:
    return _ids(storage, *(entity("project", f"project {n}") for n in range(1, count + 1)))


def _retire_team(storage: PostgresStorage, *, at: datetime) -> None:
    """Retires `team` and `leads`, the way the base file without them does."""
    apply_vocabulary(storage, parse_file(base_vocabulary()), recorded_at=at)


# --- Writing and reading ----------------------------------------------------------


@pytest.mark.db
def test_the_vellenfeld_association_reads_back_with_its_posts_and_their_holders(
    db: Engine,
) -> None:
    """An organization, two posts in it, three persons and who held which
    post when; the board on 2019-03-01 is the two whose period holds that
    day."""
    storage = _setup(db)
    club, chair, treasurer, anna, bert, clara = _ids(
        storage,
        entity("organization", "Verein Vellenfeld"),
        entity("post", "Obmann"),
        entity("post", "Kassier"),
        entity("person", "Anna Huber"),
        entity("person", "Bert Bauer"),
        entity("person", "Clara Moser"),
    )
    posts = _ids(
        storage,
        relation("post_in", chair, club),
        relation("post_in", treasurer, club),
        relation("holds", anna, chair, period=Period(date(2015, 5, 1), date(2018, 12, 31))),
        relation("holds", bert, chair, period=Period(date(2019, 1, 1), None)),
        relation("holds", clara, treasurer, period=Period(date(2016, 3, 1), date(2020, 2, 29))),
    )

    graph = _graph(storage)
    assert {subject: v.claim.body.type for subject, v in graph.entities().items()} == {
        club: "organization",
        chair: "post",
        treasurer: "post",
        anna: "person",
        bert: "person",
        clara: "person",
    }
    assert set(graph.relations()) == set(posts)
    bodies = [v.claim.body for v in graph.relations(at=date(2019, 3, 1)).values()]
    board = {
        (body.start, body.to)
        for body in bodies
        if isinstance(body, RelationBody) and body.type == "holds"
    }
    assert board == {(bert, chair), (clara, treasurer)}


@pytest.mark.db
def test_a_batch_is_written_in_order_and_a_relation_may_name_an_entity_of_the_batch(
    db: Engine,
) -> None:
    storage = _setup(db)
    with storage.begin() as conn:
        tip = storage.tip(conn)
    assert tip is not None
    first = tip.id + 1
    written = _write(
        storage,
        entity("post", "Obmann"),
        entity("organization", "Verein"),
        relation("post_in", first, first + 1),
    )
    assert written == Written((first, first + 1, first + 2), (DIRECT, DIRECT, DIRECT))
    assert set(_graph(storage).relations()) == {first + 2}


@pytest.mark.db
def test_a_second_write_with_the_same_handle_writes_nothing_and_returns_the_same_ids(
    db: Engine,
) -> None:
    storage = _setup(db)
    claims = (
        guess("person", "Anna Huber", handle="nonce-1"),
        guess("person", "Bert Bauer", handle="nonce-1"),
    )
    first = _write(storage, *claims)
    count = _count(storage)
    assert _write(storage, *claims) == first
    assert first.levels == (OPEN, OPEN)
    assert _count(storage) == count
    # The preview of a repeat shows what stands under the handle.
    assert [c.body for c in _checked(storage, *claims)] == [c.body for c in claims]
    # Another handle, or none, writes again.
    assert _write(storage, replace(claims[0], handle="nonce-2")).ids != first.ids
    assert _count(storage) == count + 1


@pytest.mark.db
def test_a_refused_claim_takes_the_whole_batch_with_it(db: Engine) -> None:
    storage = _setup(db)
    sentence = _refused(storage, entity("person", "Anna"), entity("planet", "Mars"))
    assert sentence == "the type is not declared as a kind of entity in the vocabulary"


@pytest.mark.db
def test_the_batch_rules_are_those_of_obligations(db: Engine) -> None:
    storage = _setup(db)
    assert _refused(storage) == "there is no statement to write"
    assert (
        _refused(storage, entity("person", "A", handle="a"), entity("person", "B", handle="b"))
        == "the statements of one batch carry different handles"
    )


@pytest.mark.db
def test_more_claims_than_a_batch_holds_are_refused(db: Engine) -> None:
    storage = _setup(db)
    claims = [entity("person", f"person {n}") for n in range(MAX_BATCH + 1)]
    assert _refused(storage, *claims) == f"a batch holds at most {MAX_BATCH} statements"


@pytest.mark.db
def test_a_text_the_log_cannot_hold_is_refused_without_the_text(db: Engine) -> None:
    storage = _setup(db)
    assert _refused(storage, entity("person", "Anna\x00 Huber")) == (
        "a statement cannot be written: "
        "$.fields.name: null byte not allowed — PostgreSQL jsonb cannot store it"
    )


@pytest.mark.db
def test_a_claim_without_a_valid_form_is_refused_with_its_sentence(db: Engine) -> None:
    storage = _setup(db)
    claim = entity("person", "Anna", sources=())
    assert _refused(storage, claim) == (
        "a statement has no valid form: the sources are empty: a statement from sources"
        " needs at least one"
    )


@pytest.mark.db
def test_a_subject_that_names_nothing_or_another_kind_is_refused(db: Engine) -> None:
    storage = _setup(db)
    (anna,) = _ids(storage, entity("person", "Anna"))
    assert (
        _refused(storage, entity("person", "Anna", subject=999))
        == "the subject 999 names no entity or relation that stands"
    )
    assert (
        _refused(storage, relation("holds", anna, anna, subject=anna))
        == f"the subject {anna} is an entity, and this statement is a relation"
    )


@pytest.mark.db
def test_an_end_that_does_not_stand_is_refused(db: Engine) -> None:
    storage = _setup(db)
    (anna,) = _ids(storage, entity("person", "Anna"))
    assert (
        _refused(storage, relation("holds", anna, 999))
        == "an end of the relation is not an entity that stands"
    )
    # A retracted entity stands no more.
    (chair,) = _ids(storage, entity("post", "Obmann"))
    _ids(storage, entity("post", "Obmann", subject=chair, state=RETRACTED))
    assert (
        _refused(storage, relation("holds", anna, chair))
        == "an end of the relation is not an entity that stands"
    )


# --- Sources ------------------------------------------------------------------------


@pytest.mark.db
def test_the_sources_are_checked_with_the_sentences_of_obligations(db: Engine) -> None:
    storage = _setup(db)
    assert _refused(storage, entity("person", "Anna", sources=(Source(999, None),))) == (
        "there is no event 999 to rest on"
    )
    assert _refused(storage, entity("person", "Anna", sources=(Source(1, (7,)),))) == (
        "event 1 has no unit 7"
    )
    action = append_action(storage, {"action": "teleport"}, (), recorded_at=T1)
    assert _refused(storage, entity("person", "Anna", sources=(Source(action, None),))) == (
        f"event {action} is not an observation, and only one can be a source"
    )
    with storage.begin() as conn, pytest.raises(GraphRefused, match="no event 999"):
        check_claims(
            storage, conn, [entity("person", "A", sources=(Source(999, None),))], recorded_at=T1
        )


@pytest.mark.db
def test_a_recollection_is_the_operators_and_a_models_is_refused(db: Engine) -> None:
    """Point 6 of the spec's acceptance list: the operator remembers, a
    model rests on sources."""
    storage = _setup(db)
    (anna,) = _ids(storage, entity("person", "Anna Huber", evidence=RECOLLECTION))
    assert _graph(storage).entities()[anna].claim.sources == ()
    claim = replace(guess("person", "Bert"), evidence=RECOLLECTION, sources=())
    assert (
        _refused(storage, claim)
        == "a statement has no valid form: only the operator writes a recollection"
    )


# --- Levels -------------------------------------------------------------------------


@pytest.mark.db
def test_the_operator_writes_direct_versions_only(db: Engine) -> None:
    storage = _setup(db)
    claim = entity("person", "Anna", responsibility=OPEN)
    assert _refused(storage, claim) == "a version by the operator is direct"


@pytest.mark.db
def test_a_model_without_a_class_writes_open_whatever_it_asks_for(db: Engine) -> None:
    storage = _setup(db)
    asked = guess("person", "Anna", responsibility=TRANSITIVE, under=1)
    written = _write(storage, asked)
    assert written.levels == (OPEN,)
    (version,) = _graph(storage).threads[written.ids[0]].versions
    assert (version.claim.responsibility, version.claim.under) == (OPEN, None)


@pytest.mark.db
def test_a_class_in_force_makes_a_confident_claim_transitive(db: Engine) -> None:
    storage = _setup(db)
    class_id = set_class(storage, CLASS, statement="people", recorded_at=T0)
    confident, unsure, other = _ids(
        storage,
        guess("person", "Anna", confidence=90),
        guess("person", "Bert", confidence=50),
        guess("post", "Obmann", confidence=99),
    )
    threads = _graph(storage).threads
    levels = {
        subject: (version.claim.responsibility, version.claim.under)
        for subject in (confident, unsure, other)
        for version in threads[subject].versions
    }
    assert levels == {
        confident: (TRANSITIVE, class_id),
        unsure: (OPEN, None),
        other: (OPEN, None),
    }


@pytest.mark.db
def test_a_class_does_not_make_a_question_transitive(db: Engine) -> None:
    storage = _setup(db)
    set_class(storage, POSTS, statement="posts", recorded_at=T0)
    chair, one, two = _ids(
        storage,
        entity("post", "Obmann"),
        entity("organization", "Verein"),
        entity("organization", "Club"),
    )
    question = relation(
        "post_in", chair, None, author=MODEL, responsibility=OPEN, confidence=99,
        candidates=(one, two),
    )  # fmt: skip
    assert _write(storage, question).levels == (OPEN,)


@pytest.mark.db
def test_a_model_against_a_direct_winner_writes_an_objection(db: Engine) -> None:
    """Point 4 of the spec's acceptance list: a model that contradicts what
    the operator stands for objects, whatever its class and confidence."""
    storage = _setup(db)
    set_class(storage, CLASS, statement="people", recorded_at=T0)
    (anna,) = _ids(storage, entity("person", "Anna Huber"))
    (objection,) = _ids(storage, guess("person", "Anna Huber-Moser", subject=anna))

    thread = _graph(storage).threads[anna]
    graph = _graph(storage)
    claim = thread.versions[-1].claim
    assert (claim.responsibility, claim.under, claim.contests) == (OPEN, None, anna)
    assert [v.id for v in thread.objections(graph.classes)] == [objection]
    assert thread.winner(graph.classes) == thread.versions[0]


@pytest.mark.db
def test_the_preview_shows_the_levels_and_writes_nothing(db: Engine) -> None:
    storage = _setup(db)
    set_class(storage, CLASS, statement="people", recorded_at=T0)
    count = _count(storage)
    shown = _checked(storage, guess("person", "Anna"), guess("person", "Bert", confidence=10))
    assert [c.responsibility for c in shown] == [TRANSITIVE, OPEN]
    assert _count(storage) == count
    with pytest.raises(GraphRefused, match=r"^a version by the operator is direct$"):
        _checked(storage, entity("person", "Anna", responsibility=OPEN))


def _shown(storage: PostgresStorage, *claims: Claim, at: datetime = T1) -> tuple[Decided, ...]:
    """What a preview shows of the claims: the decision for each."""
    return tuple(decided(claim) for claim in _checked(storage, *claims, at=at))


@pytest.mark.db
def test_a_class_revoked_since_the_preview_refuses_the_write(db: Engine) -> None:
    """Review Focus 2: the level of the confirmation is the one under the
    tip, and one that differs from the preview is refused, not written."""
    storage = _setup(db)
    class_id = set_class(storage, CLASS, statement="people", recorded_at=T0)
    claim = guess("person", "Anna")
    shown = _shown(storage, claim)
    assert shown == (Decided(TRANSITIVE, class_id, None),)
    set_class(storage, replace(CLASS, revoked=True), statement="stop", recorded_at=T1)
    assert _refused(storage, claim, at=T2, expect=shown) == CLASS_CHANGED
    # Without a preview to hold it against, the write takes the level now.
    assert _write(storage, claim, at=T2).levels == (OPEN,)


@pytest.mark.db
def test_a_class_set_since_the_preview_refuses_the_write(db: Engine) -> None:
    storage = _setup(db)
    claim = guess("person", "Anna")
    shown = _shown(storage, claim)
    assert shown == (Decided(OPEN, None, None),)
    set_class(storage, CLASS, statement="people", recorded_at=T1)
    assert _refused(storage, claim, at=T2, expect=shown) == CLASS_CHANGED
    # The control: the decisions of a preview taken now are written.
    now = _shown(storage, claim, at=T2)
    assert write_claims(storage, storage, [claim], recorded_at=T2, expect=now).levels == (
        TRANSITIVE,
    )


@pytest.mark.db
def test_another_class_at_the_same_level_since_the_preview_refuses_the_write(
    db: Engine,
) -> None:
    """Ruling T4-e: the class a claim stands under is part of what the
    preview showed, not only its level."""
    storage = _setup(db)
    set_class(storage, CLASS, statement="people", recorded_at=T0)
    claim = guess("person", "Anna", confidence=95)
    shown = _shown(storage, claim)
    stricter = replace(CLASS, name="claude_people_strict", threshold=90)
    stricter_id = set_class(storage, stricter, statement="stricter", recorded_at=T1)
    now = _shown(storage, claim, at=T2)
    assert (shown[0].level, now[0]) == (TRANSITIVE, Decided(TRANSITIVE, stricter_id, None))
    assert _refused(storage, claim, at=T2, expect=shown) == CLASS_CHANGED


@pytest.mark.db
def test_a_direct_version_written_since_the_preview_refuses_the_write(db: Engine) -> None:
    """Ruling T4-e: an objection that would contest another direct version
    than the one shown, and a proposal that would become an objection, are
    refused with a sentence of their own."""
    storage = _setup(db)
    (anna,) = _ids(storage, entity("person", "Anna"))
    objection = guess("person", "Anna Moser", subject=anna)
    shown = _shown(storage, objection)
    assert shown == (Decided(OPEN, None, anna),)
    (newer,) = _ids(storage, entity("person", "Anna Huber", subject=anna))
    assert _refused(storage, objection, at=T2, expect=shown) == DIRECT_WRITTEN

    proposal = guess("post", "Obmann", confidence=10)
    (post,) = _ids(storage, proposal, at=T2)
    further = guess("post", "Obfrau", subject=post, confidence=10)
    shown = _shown(storage, further, at=T2)
    assert shown == (Decided(OPEN, None, None),)
    _ids(storage, entity("post", "Obmann", subject=post), at=T2)
    assert _refused(storage, further, at=T3, expect=shown) == DIRECT_WRITTEN
    # The control: a preview taken now is written as shown.
    now = _shown(storage, objection, at=T3)
    assert now == (Decided(OPEN, None, newer),)
    write_claims(storage, storage, [objection], recorded_at=T3, expect=now)


@pytest.mark.db
def test_expect_gives_one_decision_per_claim(db: Engine) -> None:
    storage = _setup(db)
    with pytest.raises(ValueError, match="one decision per claim"):
        write_claims(storage, storage, [guess("person", "A")], recorded_at=T1, expect=())


@pytest.mark.db
def test_a_handle_repeats_only_within_its_own_write_path(db: Engine) -> None:
    """Ruling T4-e: an obligation batch and a graph batch with the same
    handle are two batches, each written once."""
    storage = _setup(db)
    owed = Statement(
        OBLIGATION, OPERATOR, DIRECT, (Source(1, None),), None, "shared", None, None, None,
        ObligationBody("own", "circle:huber", "send the offer", None, "open"),
    )  # fmt: skip
    (obligation,) = write_statements(storage, storage, [owed], recorded_at=T1)
    claim = entity("person", "Anna", handle="shared")
    assert _checked(storage, claim) == (claim,)
    written = _write(storage, claim)
    assert written.ids != (obligation,)
    assert _write(storage, claim) == written
    other = replace(owed, handle="graph")
    (graph_id,) = _write(storage, replace(claim, handle="graph")).ids
    with storage.begin() as conn:
        check_statements(storage, conn, [other])
    (again,) = write_statements(storage, storage, [other], recorded_at=T1)
    assert again != graph_id
    assert write_statements(storage, storage, [other], recorded_at=T1) == (again,)


# --- The vocabulary -----------------------------------------------------------------


@pytest.mark.db
def test_a_vocabulary_changed_since_the_preview_refuses_the_write(db: Engine) -> None:
    """Review Focus 1: the write checks again under the tip, and nothing is
    written against a vocabulary that no longer holds."""
    storage = _setup(db)
    claim = entity("team", "Board")
    assert _checked(storage, claim) == (claim,)
    _retire_team(storage, at=T1)
    assert _refused(storage, claim, at=T2) == "the kind is retired and takes no new entity"


@pytest.mark.db
def test_a_retired_kind_takes_further_versions_but_no_new_entity_or_relation(
    db: Engine,
) -> None:
    """Review Focus 4: an entity or a relation of a retired kind may be
    renamed, ended or retracted; a new one of that kind is refused."""
    storage = _setup(db)
    anna, board = _ids(storage, entity("person", "Anna"), entity("team", "Board"))
    (leads,) = _ids(storage, relation("leads", anna, board))
    _retire_team(storage, at=T1)

    assert _refused(storage, entity("team", "Staff"), at=T2) == (
        "the kind is retired and takes no new entity"
    )
    assert _refused(storage, relation("leads", anna, board), at=T2) == (
        "the kind is retired and takes no new relation"
    )
    _ids(
        storage,
        entity("team", "The board", subject=board),
        relation("leads", anna, board, subject=leads, state=RETRACTED),
        entity("team", "The board", subject=board, state=RETRACTED),
        at=T2,
    )
    graph = _graph(storage)
    assert (board in graph.entities(), leads in graph.relations()) == (False, False)


TEAMS = ApprovalClass(
    "claude_teams", MODEL, ENTITY, frozenset({"team"}), 80, None, None, revoked=False,
    demote=False,
)  # fmt: skip


@pytest.mark.db
def test_approving_a_later_proposal_of_a_thread_that_never_stood_is_new(db: Engine) -> None:
    """Ruling T4-e: a thread on which no direct or transitive version ever
    stood is no entity yet, whichever of its proposals an approval names,
    and neither does a direct version make it one for a kind retired since.
    Further proposals on it stay possible, as they stand for nobody."""
    storage = _setup(db)
    (first,) = _ids(storage, guess("team", "Board", confidence=10))
    later = guess("team", "The board", subject=first, confidence=10)
    (proposed,) = _ids(storage, later)
    _retire_team(storage, at=T1)
    approval = replace(later, responsibility=DIRECT, approves=proposed)
    sentence = "the kind is retired and takes no new entity"
    assert _refused(storage, approval, at=T2) == sentence
    assert _refused(storage, entity("team", "Board", subject=first), at=T2) == sentence
    assert _write(storage, guess("team", "Boards", subject=first, confidence=10), at=T2).levels == (
        OPEN,
    )


@pytest.mark.db
def test_approving_a_transitive_version_of_a_retired_kind_is_no_new_entity(db: Engine) -> None:
    """Ruling T4-e: a transitive first version already stood for the
    operator, so its approval only confirms what stands."""
    storage = _setup(db)
    set_class(storage, TEAMS, statement="teams", recorded_at=T0)
    proposal = guess("team", "Board")
    (first,) = _ids(storage, proposal)
    (version,) = _graph(storage).threads[first].versions
    assert version.claim.responsibility == TRANSITIVE
    _retire_team(storage, at=T1)
    approval = replace(
        version.claim, responsibility=DIRECT, under=None, subject=first, approves=first
    )
    assert _write(storage, approval, at=T2).levels == (DIRECT,)


@pytest.mark.db
def test_approving_a_new_entity_of_a_kind_retired_since_is_refused(db: Engine) -> None:
    storage = _setup(db)
    proposal = guess("team", "Board")
    (proposed,) = _ids(storage, proposal)
    _retire_team(storage, at=T1)
    approval = replace(proposal, responsibility=DIRECT, subject=proposed, approves=proposed)
    assert _refused(storage, approval, at=T2) == "the kind is retired and takes no new entity"


# --- Approvals, objections and questions ------------------------------------------


@pytest.mark.db
def test_an_approval_makes_a_proposal_direct_and_takes_it_unchanged(db: Engine) -> None:
    storage = _setup(db)
    proposal = guess("person", "Anna", confidence=40)
    (proposed,) = _ids(storage, proposal)
    approval = replace(proposal, responsibility=DIRECT, subject=proposed, approves=proposed)

    changed = replace(approval, body=replace(approval.body, fields={"name": "Bert"}))
    assert _refused(storage, changed) == (
        "an approval takes the content, the sources and the author of its proposal unchanged"
    )
    for other in (
        replace(approval, confidence=99),
        replace(approval, sources=(Source(2, None),)),
    ):
        assert _refused(storage, other).startswith("an approval takes the content")

    (approved,) = _ids(storage, replace(approval, reason="checked"))
    graph = _graph(storage)
    thread = graph.threads[proposed]
    assert thread.winner(graph.classes) == thread.versions[-1]
    assert thread.versions[-1].id == approved
    assert _refused(storage, approval) == f"the proposal {proposed} is already approved"
    assert _refused(storage, replace(approval, approves=approved)) == (
        f"the version {approved} is no proposal: it is direct"
    )


@pytest.mark.db
def test_a_transitive_version_is_approved_like_a_proposal(db: Engine) -> None:
    storage = _setup(db)
    set_class(storage, CLASS, statement="people", recorded_at=T0)
    (anna,) = _ids(storage, guess("person", "Anna"))
    (version,) = _graph(storage).threads[anna].versions
    approval = replace(
        version.claim, responsibility=DIRECT, under=None, approves=anna, subject=anna
    )
    assert _write(storage, approval).levels == (DIRECT,)


@pytest.mark.db
def test_an_overtaken_proposal_or_one_of_another_thread_is_not_approved(db: Engine) -> None:
    storage = _setup(db)
    proposal = guess("person", "Anna")
    proposed, other = _ids(storage, proposal, guess("person", "Bert"))
    (direct,) = _ids(storage, entity("person", "Anna Huber", subject=proposed))
    approval = replace(proposal, responsibility=DIRECT, subject=proposed, approves=proposed)
    assert _refused(storage, approval) == (
        f"the proposal {proposed} is overtaken: the direct version {direct} came after it"
    )
    assert _refused(storage, replace(approval, approves=other)) == (
        f"approves names {other}, which is no proposal of the subject {proposed}"
    )


@pytest.mark.db
def test_a_rejected_proposal_is_not_approved(db: Engine) -> None:
    storage = _setup(db)
    proposal = guess("person", "Anna")
    (proposed,) = _ids(storage, proposal)
    rejection = Statement(
        REJECTION, OPERATOR, DIRECT, proposal.sources, None, None, None, None, proposed, None
    )
    write_statements(storage, storage, [rejection], recorded_at=T1)
    approval = replace(proposal, responsibility=DIRECT, subject=proposed, approves=proposed)
    assert _refused(storage, approval) == f"the proposal {proposed} is already rejected"


@pytest.mark.db
def test_two_approvals_of_one_proposal_in_one_batch_are_refused(db: Engine) -> None:
    storage = _setup(db)
    proposal = guess("person", "Anna")
    (proposed,) = _ids(storage, proposal)
    approval = replace(proposal, responsibility=DIRECT, subject=proposed, approves=proposed)
    assert _refused(storage, approval, approval) == f"the proposal {proposed} is already approved"


def _question(storage: PostgresStorage) -> tuple[int, int, int, int, int]:
    """A post, three organizations, and a model's question which of the
    first two the post is in."""
    chair, one, two, three = _ids(
        storage,
        entity("post", "Obmann"),
        entity("organization", "Verein"),
        entity("organization", "Club"),
        entity("organization", "Bund"),
    )
    asked = relation(
        "post_in", chair, None, author=MODEL, responsibility=OPEN, confidence=50,
        candidates=(one, two),
    )  # fmt: skip
    (question,) = _ids(storage, asked)
    return question, chair, one, two, three


@pytest.mark.db
def test_a_direct_version_answers_a_question_with_one_of_its_candidates(db: Engine) -> None:
    storage = _setup(db)
    question, chair, one, _two, three = _question(storage)
    graph = _graph(storage)
    assert graph.threads[question].question(graph.classes) is not None

    wrong = relation("post_in", chair, three, subject=question)
    assert _refused(storage, wrong) == f"the answer names {three}, which is none of the candidates"
    _ids(storage, relation("post_in", chair, one, subject=question))
    graph = _graph(storage)
    assert graph.threads[question].question(graph.classes) is None
    answered = graph.relations()[question].claim.body
    assert isinstance(answered, RelationBody)
    assert answered.to == one
    # Once answered, a further version may point elsewhere.
    _ids(storage, relation("post_in", chair, three, subject=question))


@pytest.mark.db
def test_an_approval_answers_a_question_in_the_models_words(db: Engine) -> None:
    """The way `write_triage_answer` answers: the question approved, its
    author kept, with `to` one of the candidates in place of them."""
    storage = _setup(db)
    question, _chair, _one, two, three = _question(storage)
    (version,) = _graph(storage).threads[question].versions
    body = version.claim.body
    assert isinstance(body, RelationBody)
    answer = replace(
        version.claim,
        responsibility=DIRECT,
        subject=question,
        approves=question,
        body=replace(body, to=three, candidates=None),
    )
    assert _refused(storage, answer) == (
        "an approval takes the content, the sources and the author of its proposal unchanged"
    )
    (answered,) = _ids(storage, replace(answer, body=replace(body, to=two, candidates=None)))
    graph = _graph(storage)
    winner = graph.threads[question].winner(graph.classes)
    assert winner is not None
    assert (winner.id, winner.claim.author) == (answered, MODEL)
    assert graph.threads[question].question(graph.classes) is None


POSTS = ApprovalClass(
    "claude_posts", MODEL, RELATION, frozenset({"post_in"}), 10, None, None, revoked=False,
    demote=False,
)  # fmt: skip


@pytest.mark.db
def test_a_class_does_not_answer_a_question_with_none_of_its_candidates(db: Engine) -> None:
    """Ruling T4-d: a model's claim on a thread whose question waits, and
    whose end is none of the candidates, is written open whatever its class
    covers, and the question stays pending."""
    storage = _setup(db)
    question, chair, _one, _two, three = _question(storage)
    set_class(storage, POSTS, statement="posts", recorded_at=T1)
    outside = relation(
        "post_in", chair, three, author=MODEL, responsibility=OPEN, confidence=90,
        subject=question,
    )  # fmt: skip
    assert _write(storage, outside, at=T2).levels == (OPEN,)
    graph = _graph(storage)
    pending = graph.threads[question].question(graph.classes)
    assert pending is not None
    assert pending.id == question


@pytest.mark.db
def test_a_class_answers_a_question_with_one_of_its_candidates(db: Engine) -> None:
    """The control of the test above: a transitive claim that names a
    candidate answers the question, as a direct one does (ruling T2-c)."""
    storage = _setup(db)
    question, chair, one, _two, _three = _question(storage)
    set_class(storage, POSTS, statement="posts", recorded_at=T1)
    inside = relation(
        "post_in", chair, one, author=MODEL, responsibility=OPEN, confidence=90,
        subject=question,
    )  # fmt: skip
    assert _write(storage, inside, at=T2).levels == (TRANSITIVE,)
    graph = _graph(storage)
    assert graph.threads[question].question(graph.classes) is None


@pytest.mark.db
def test_a_retraction_answers_a_question_with_none_of_its_candidates(db: Engine) -> None:
    storage = _setup(db)
    question, chair, _one, _two, three = _question(storage)
    _ids(storage, relation("post_in", chair, three, subject=question, state=RETRACTED))
    assert question not in _graph(storage).relations()


# --- Cycles -------------------------------------------------------------------------


@pytest.mark.db
def test_a_new_edge_that_closes_a_cycle_is_refused(db: Engine) -> None:
    storage = _setup(db)
    one, two, three = _projects(storage, 3)
    _ids(storage, edge(one, two), edge(two, three))
    sentence = "the relation would close a cycle over a kind that is acyclic"
    assert _refused(storage, edge(three, one)) == sentence
    # The control: an edge that closes nothing.
    _ids(storage, edge(one, three))


@pytest.mark.db
def test_an_edge_from_an_entity_to_itself_is_refused(db: Engine) -> None:
    storage = _setup(db)
    (one,) = _projects(storage, 1)
    assert _refused(storage, edge(one, one)) == (
        "the relation would close a cycle over a kind that is acyclic"
    )


@pytest.mark.db
def test_a_new_version_that_turns_an_edge_closes_a_cycle_through_the_others(db: Engine) -> None:
    """Review Focus 5: a cycle through a new version of an edge, not only
    through a new edge."""
    storage = _setup(db)
    one, two, three = _projects(storage, 3)
    first, _second = _ids(storage, edge(one, two), edge(three, one))
    assert _refused(storage, edge(one, three, subject=first)) == (
        "the relation would close a cycle over a kind that is acyclic"
    )
    # The control: the version that turns the edge around replaces it, and
    # is not held against the edge it replaces.
    _ids(storage, edge(two, one, subject=first))


@pytest.mark.db
def test_a_cycle_within_one_batch_is_refused_and_nothing_written(db: Engine) -> None:
    storage = _setup(db)
    one, two, three = _projects(storage, 3)
    assert _refused(storage, edge(one, two), edge(two, three), edge(three, one)) == (
        "the relation would close a cycle over a kind that is acyclic"
    )
    # A version earlier in the batch that removes an edge is folded in too.
    (first,) = _ids(storage, edge(one, two))
    _ids(storage, edge(one, two, subject=first, state=RETRACTED), edge(two, one))


@pytest.mark.db
def test_an_open_edge_neither_vetoes_the_operator_nor_is_refused_for_a_cycle(
    db: Engine,
) -> None:
    """Ruling T2-b of the 2026-10-14 assignments plan: a direct write is held
    against direct and transitive edges, so a proposal does not veto it. And
    ruling T6-a, which replaced the rest of T2-b: a model's open version is
    held to no cycle at all, since its refusal would tell a client about
    edges it may not see."""
    storage = _setup(db)
    one, two, three = _projects(storage, 3)
    _ids(storage, edge(one, two), edge(two, three))
    assert _write(storage, model_edge(three, one)).levels == (OPEN,)
    assert _write(storage, model_edge(one, one)).levels == (OPEN,)
    (proposed,) = _ids(storage, model_edge(two, one))
    # The control: the operator closing the same cycle is refused, and an
    # open edge does not veto an edge of the operator's that closes nothing.
    assert _refused(storage, edge(three, one)) == (
        "the relation would close a cycle over a kind that is acyclic"
    )
    _ids(storage, edge(one, three))
    assert proposed in _graph(storage).relations()


@pytest.mark.db
def test_no_class_reaches_an_acyclic_kind(db: Engine) -> None:
    """Ruling T6-a: a class over `part_of` is refused, and one that came
    another way covers nothing, so a model's edge stays open, as it does for
    a kind the gate reads."""
    storage = _setup(db)
    with pytest.raises(ClassRefused) as refused:
        set_class(storage, EDGES, statement="parts", recorded_at=T0)
    assert str(refused.value) == (
        'the approval class names "part_of", a relation kind that is acyclic, '
        "which no class reaches"
    )
    with storage.begin() as conn:
        assert class_refusal(storage, conn, EDGES, statement="parts") == str(refused.value)
    append_action(storage, class_payload(EDGES, statement="by hand"), (), recorded_at=T0)
    one, two = _projects(storage, 2)
    assert _write(storage, model_edge(one, two, confidence=99)).levels == (OPEN,)
    # The control: a revocation is not refused, and a class over a kind
    # without the behavior is taken.
    set_class(storage, replace(EDGES, revoked=True), statement="gone", recorded_at=T0)
    set_class(storage, POSTS, statement="posts", recorded_at=T0)


@pytest.mark.db
def test_approving_an_open_edge_that_closes_a_cycle_is_refused(db: Engine) -> None:
    storage = _setup(db)
    one, two = _projects(storage, 2)
    proposal = model_edge(one, two)
    (proposed,) = _ids(storage, proposal)
    _ids(storage, edge(two, one))
    approval = replace(proposal, responsibility=DIRECT, subject=proposed, approves=proposed)
    assert _refused(storage, approval) == (
        "the relation would close a cycle over a kind that is acyclic"
    )


@pytest.mark.db
def test_a_relation_that_starts_at_an_event_closes_no_cycle(db: Engine) -> None:
    """`part_of` does not start at an event, and the vocabulary refuses
    one that does before the cycle rule; the rule itself counts it as no
    edge between entities, so that `verify` does not trip over one written
    by hand, and an assignment, which does start at one, closes nothing."""
    storage = _setup(db)
    with storage.begin() as conn:
        vocabulary = read_vocabulary(storage, conn)
    body = RelationBody("part_of", Source(1, None), 2, None, None, {}, STANDING)
    claim = replace(edge(1, 2), body=body)
    assert not closes_cycle(_graph(storage), claim, vocabulary, level=DIRECT)


class _MeetingAtTheTip(PostgresStorage):
    """The real store, except that the first `tip` each thread reads waits
    until the other thread has read its first one as well, so that both
    check under the same tip before either writes."""

    def __init__(self, engine: Engine) -> None:
        super().__init__(engine)
        self.meeting = threading.Barrier(2)
        self.met = threading.local()
        self.reads: list[int] = []
        self._lock = threading.Lock()

    def tip(self, conn: Connection) -> Tip | None:
        found = super().tip(conn)
        with self._lock:
            self.reads.append(threading.get_ident())
        if not getattr(self.met, "done", False):
            self.met.done = True
            self.meeting.wait(timeout=15)
        return found


@pytest.mark.db
def test_two_writes_that_each_close_half_a_cycle_cannot_both_stand(db: Engine) -> None:
    """Point 7 of the spec's acceptance list and decision 13 of the
    2026-10-14 assignments plan: each edge alone is allowed, both read the
    same tip, and the chain lets one of them write; the other loses the
    position, folds again with the first edge in, and is refused.

    The two use different source events, so that no row lock orders them
    before they meet at the tip."""
    _setup(db)
    storage = _MeetingAtTheTip(db)
    storage.met.done = True  # this thread meets nobody
    one, two = _ids(storage, entity("project", "one"), entity("project", "two"))
    storage.reads.clear()
    written: list[Written] = []
    refused: list[str] = []
    failures: list[BaseException] = []

    def write(claim: Claim) -> None:
        try:
            written.append(write_claims(storage, storage, [claim], recorded_at=T2))
        except GraphRefused as error:
            refused.append(str(error))
        except BaseException as error:  # a thread that fails must not pass silently
            failures.append(error)

    threads = [
        threading.Thread(target=write, args=(edge(one, two, sources=(Source(1, None),)),)),
        threading.Thread(target=write, args=(edge(two, one, sources=(Source(2, None),)),)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
        assert not thread.is_alive(), "thread is hanging"

    assert failures == []
    assert refused == ["the relation would close a cycle over a kind that is acyclic"]
    assert len(written) == 1
    assert set(_graph(storage).relations()) == set(written[0].ids)
    # The loser read the tip twice: it lost the position and tried again.
    losers = [ident for ident in set(storage.reads) if storage.reads.count(ident) == 2]
    assert len(losers) == 1


# --- Reading at a past moment -----------------------------------------------------


@pytest.mark.db
def test_the_graph_as_of_a_moment_is_the_one_recorded_up_to_it(db: Engine) -> None:
    storage = _setup(db)
    (anna,) = _ids(storage, entity("person", "Anna"), at=T1)
    _ids(storage, entity("person", "Anna Huber", subject=anna), at=T2)
    set_class(storage, CLASS, statement="people", recorded_at=T2)

    def name(graph: Graph) -> FieldValue:
        return graph.entities()[anna].claim.body.fields["name"]

    assert name(_graph(storage, as_of=T1)) == "Anna"
    assert name(_graph(storage)) == "Anna Huber"
    assert _graph(storage, as_of=T1).classes == {}
    assert _graph(storage, as_of=T2).classes != {}
    assert _graph(storage, as_of=T0).threads == {}


@pytest.mark.db
def test_entity_types_are_the_standing_entities_looked_up_one_at_a_time(db: Engine) -> None:
    storage = _setup(db)
    anna, chair = _ids(storage, entity("person", "Anna"), entity("post", "Obmann"))
    (holds,) = _ids(storage, relation("holds", anna, chair))
    _ids(storage, entity("post", "Obmann", subject=chair, state=RETRACTED))
    types = EntityTypes(_graph(storage))
    assert dict(types) == {anna: "person"}
    assert len(types) == 1
    assert (chair in types, holds in types, 999 in types) == (False, False, False)


# --- The policy ---------------------------------------------------------------------


CLAUDE = Provider(
    "claude-max", (Inference("global", frozenset({ANY})),), frozenset({"us"}), 30, True, False
)
CLIENT = Client("claude-code", "claude-max", "0" * 64)


def _policy(*scopes: str) -> Policy:
    return Policy(
        circles={},
        memberships=(),
        own=(),
        rules={scope: Rule(scope, frozenset({ANY}), None, frozenset()) for scope in scopes},
        providers={"claude-max": CLAUDE},
        ids={},
    )


def test_a_recollection_is_held_back_until_a_rule_for_it_exists() -> None:
    """Decision 12 of the 2026-10-14 assignments plan."""
    held = claim_verdict(_policy("source:email"), CLIENT, [], (), recollection=True)
    assert held.chosen is None
    free = claim_verdict(_policy("source:recollection"), CLIENT, [], (), recollection=True)
    assert free.chosen is not None


def test_a_claim_from_sources_is_decided_as_an_obligation_is() -> None:
    assert claim_verdict(_policy("source:email"), CLIENT, [], ("email",), recollection=False).chosen
    assert (
        claim_verdict(_policy("source:recollection"), CLIENT, [], ("email",), recollection=False)
    ).chosen is None


def test_a_thread_with_sources_and_a_recollection_needs_both_rules() -> None:
    both = _policy("source:email", "source:recollection")
    assert claim_verdict(both, CLIENT, [], ("email",), recollection=True).chosen is not None
    only_mail = _policy("source:email")
    assert claim_verdict(only_mail, CLIENT, [], ("email",), recollection=True).chosen is None


def _thread(*claims: Claim) -> GraphThread:
    versions = tuple(GraphVersion(50 + n, T1, claim) for n, claim in enumerate(claims))
    return GraphThread(50, RELATION, versions)


def test_a_relation_is_visible_when_its_sources_and_both_ends_are() -> None:
    policy = _policy("source:email")
    holds = _thread(relation("holds", 10, 12))
    assert relation_visible(policy, CLIENT, holds, {10: True, 12: True}, [], ("email",))
    assert not relation_visible(policy, CLIENT, holds, {10: True, 12: False}, [], ("email",))
    assert not relation_visible(policy, CLIENT, holds, {10: True}, [], ("email",))
    assert not relation_visible(_policy(), CLIENT, holds, {10: True, 12: True}, [], ("email",))
    question = _thread(relation("holds", 10, None, candidates=(12, 13)))
    assert not relation_visible(policy, CLIENT, question, {10: True, 12: True}, [], ("email",))
    assert relation_visible(
        policy, CLIENT, question, {10: True, 12: True, 13: True}, [], ("email",)
    )


def test_an_assignment_is_decided_over_its_mail_and_the_entity_it_points_at() -> None:
    """Its start is among its sources, so the sources the caller hands in
    are the mail's: a client that may not see the mail does not see the
    assignment, and one that may not see the bracket does not either.
    Measured red with the phase 1 rule back, which showed no relation that
    starts at an event."""
    policy = _policy("source:email")
    start = Source(1, (2,))
    assigned = replace(
        relation("concerns", 10, 12, sources=(start,)),
        body=RelationBody("concerns", start, 12, None, None, {}, STANDING),
    )
    thread = _thread(assigned)
    assert relation_visible(policy, CLIENT, thread, {12: True}, [], ("email",))
    assert not relation_visible(policy, CLIENT, thread, {12: False}, [], ("email",))
    assert not relation_visible(_policy(), CLIENT, thread, {12: True}, [], ("email",))
    # A thread that holds an entity is no relation, whatever the policy says.
    assert not relation_visible(
        policy, CLIENT, _thread(entity("project", "XZ")), {12: True}, [], ("email",)
    )


def test_an_erased_end_withholds_nothing_and_every_version_names_its_ends() -> None:
    """Ruling T6-c of the 2026-10-14 assignments plan: the one rule MCP
    uses. An end whose every version is erased (`None`) is nothing to keep
    from the client, while an end an older version named counts as one the
    newest names does."""
    policy = _policy("source:email")
    holds = _thread(relation("holds", 10, 12))
    assert relation_visible(policy, CLIENT, holds, {10: True, 12: None}, [], ("email",))
    turned = _thread(relation("holds", 10, 13), relation("holds", 10, 12, subject=50))
    assert not relation_visible(
        policy, CLIENT, turned, {10: True, 12: True, 13: False}, [], ("email",)
    )
    # The control: with the old end seen too, it is seen.
    assert relation_visible(policy, CLIENT, turned, {10: True, 12: True, 13: True}, [], ("email",))
    remembered = _thread(
        relation("holds", 10, 12),
        replace(relation("holds", 10, 12), evidence=RECOLLECTION, sources=()),
    )
    assert not relation_visible(policy, CLIENT, remembered, {10: True, 12: True}, [], ("email",))


@pytest.mark.db
def test_the_source_events_of_graph_threads_are_read_with_their_identities(db: Engine) -> None:
    storage = _setup(db)
    (anna,) = _ids(storage, entity("person", "Anna", sources=(Source(2, None),)))
    _ids(storage, entity("person", "Anna H", subject=anna, sources=(Source(1, (2,)),)))
    graph = _graph(storage)
    with storage.begin() as conn:
        events = read_claim_events(storage, conn, graph.threads.values())
    identities, sources = claim_sources(events, graph.threads[anna])
    assert [identity["address"] for identity in identities] == [ADDRESS, ADDRESS]
    assert sources == ("email",)


# --- Assignments: a relation that starts at an event (the 2026-10-15
# assignments plan, phase 2) ------------------------------------------------------

ASSIGNMENTS = ApprovalClass(
    "claude_assignments",
    MODEL,
    RELATION,
    frozenset({"concerns"}),
    80,
    None,
    None,
    revoked=False,
    demote=False,
)


def assignment(
    start: Source,
    to: int | None,
    *,
    sources: tuple[Source, ...] | None = None,
    candidates: tuple[int, ...] | None = None,
    **changes: object,
) -> Claim:
    """The operator's `concerns` from `start`, resting on the start unless
    `sources` says otherwise."""
    claim = relation(
        "concerns", 1, to, sources=(start,) if sources is None else sources, candidates=candidates
    )
    claim = replace(claim, body=replace(claim.body, start=start))
    return replace(claim, **changes)


@pytest.mark.db
def test_an_assignment_of_a_mail_or_of_its_units_is_written_and_verify_finds_nothing(
    db: Engine,
) -> None:
    storage = _setup(db)
    (project,) = _ids(storage, entity("project", "XZ", sources=(Source(2, None),)))
    whole, unit = _ids(
        storage, assignment(Source(1, None), project), assignment(Source(1, (2,)), project)
    )

    relations = _graph(storage).relations()
    assert relations[whole].claim.body == RelationBody(
        "concerns", Source(1, None), project, None, None, {}, STANDING
    )
    assert relations[unit].claim.sources == (Source(1, (2,)),)
    assert verify(storage) == []


@pytest.mark.db
def test_an_assignment_whose_start_no_source_covers_is_refused(db: Engine) -> None:
    """Decision 3: the write path refuses it with the sentence of the form,
    and so does the preview. Measured red with `_start_problem` answering
    None: both were written."""
    storage = _setup(db)
    (project,) = _ids(storage, entity("project", "XZ"))
    sentence = f"a statement has no valid form: {START_NOT_A_SOURCE}"
    for sources in ((Source(2, None),), (Source(1, (1,)),)):
        claim = assignment(Source(1, (1, 2)), project, sources=sources)
        assert _refused(storage, claim) == sentence
        with pytest.raises(GraphRefused, match=f"^{sentence}$"):
            _checked(storage, claim)


@pytest.mark.db
def test_the_start_of_an_assignment_is_checked_as_a_source(db: Engine) -> None:
    """The start is a source, so what refuses a source refuses a start: no
    such event, no such unit, an event that is no observation."""
    storage = _setup(db)
    (project,) = _ids(storage, entity("project", "XZ"))
    assert _refused(storage, assignment(Source(999, None), project)) == (
        "there is no event 999 to rest on"
    )
    assert _refused(storage, assignment(Source(1, (7,)), project)) == "event 1 has no unit 7"
    assert _refused(storage, assignment(Source(project, None), project)) == (
        f"event {project} is not an observation, and only one can be a source"
    )


@pytest.mark.db
def test_a_model_assigns_at_the_level_of_its_class_and_asks_with_candidates(
    db: Engine,
) -> None:
    """An assignment is a relation like any other: a class makes a confident
    one transitive, an unsure one stays open, and a question with
    candidates waits for the operator."""
    storage = _setup(db)
    class_id = set_class(storage, ASSIGNMENTS, statement="assignments", recorded_at=T0)
    xz, party = _ids(storage, entity("project", "XZ"), entity("project", "Summer party"))

    def model(claim: Claim, confidence: int) -> Claim:
        return replace(claim, author=MODEL, responsibility=OPEN, confidence=confidence)

    sure, unsure, asking = _write(
        storage,
        model(assignment(Source(1, None), xz), 90),
        model(assignment(Source(2, None), xz), 40),
        model(assignment(Source(3, (2,)), None, candidates=(xz, party)), 99),
    ).ids
    graph = _graph(storage)
    claims = {
        subject: graph.threads[subject].versions[0].claim for subject in (sure, unsure, asking)
    }
    levels = {subject: (claim.responsibility, claim.under) for subject, claim in claims.items()}
    assert levels == {sure: (TRANSITIVE, class_id), unsure: (OPEN, None), asking: (OPEN, None)}
    question = graph.threads[asking].question(graph.classes)
    assert question is not None
    assert verify(storage) == []


@pytest.mark.db
def test_an_assignment_is_retracted_with_a_new_version(db: Engine) -> None:
    storage = _setup(db)
    (project,) = _ids(storage, entity("project", "XZ"))
    (assigned,) = _ids(storage, assignment(Source(1, (2,)), project))
    claim = assignment(Source(1, (2,)), project, subject=assigned)
    _ids(storage, replace(claim, body=replace(claim.body, state=RETRACTED)))

    assert assigned not in _graph(storage).relations()
    assert verify(storage) == []
