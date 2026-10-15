# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The graph model: the form of entities and relations, the check against a
vocabulary, the fold with three levels, and what stands.

Pure functions, so there is no database to start.
"""

from dataclasses import replace
from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import UTC
from hypothesis import given
from hypothesis import settings
from hypothesis import strategies as st
from previously.core.assertion import assertion_problem
from previously.core.assertion import DIRECT
from previously.core.assertion import model_author
from previously.core.assertion import OBLIGATION
from previously.core.assertion import ObligationBody
from previously.core.assertion import OPEN
from previously.core.assertion import OPERATOR
from previously.core.assertion import parse_statement
from previously.core.assertion import payload_of
from previously.core.assertion import REJECTION
from previously.core.assertion import Source
from previously.core.assertion import Statement
from previously.core.graph import ACTIVE
from previously.core.graph import Claim
from previously.core.graph import claim_changes
from previously.core.graph import claim_payload
from previously.core.graph import claim_problem
from previously.core.graph import ClassState
from previously.core.graph import CLOSED
from previously.core.graph import conformance_problem
from previously.core.graph import covers
from previously.core.graph import ENTITY
from previously.core.graph import EntityBody
from previously.core.graph import FieldValue
from previously.core.graph import fold_graph
from previously.core.graph import Graph
from previously.core.graph import GRAPH_KINDS
from previously.core.graph import GraphVersion
from previously.core.graph import level_of
from previously.core.graph import LEVELS
from previously.core.graph import parse_claim
from previously.core.graph import Period
from previously.core.graph import RECOLLECTION
from previously.core.graph import RELATION
from previously.core.graph import RelationBody
from previously.core.graph import RETRACTED
from previously.core.graph import SOURCES
from previously.core.graph import sources_with_start
from previously.core.graph import STANDING
from previously.core.graph import START_NOT_A_SOURCE
from previously.core.graph import TRANSITIVE
from previously.core.vocabulary import built_in_kinds
from previously.core.vocabulary import ENTITY_KIND
from previously.core.vocabulary import FieldSpec
from previously.core.vocabulary import KindSpec
from previously.core.vocabulary import RELATION_KIND
from previously.core.vocabulary import to_payload
from previously.core.vocabulary import Vocabulary
from previously.core.vocabulary import vocabulary_problem
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from collections.abc import Mapping


NOW = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
MODEL = model_author("claude")
CLASS = 900  # the event id of an approval class
ACTIVE_CLASS = {CLASS: ClassState(CLASS, revoked=False, demote=False)}


def entity(
    *,
    responsibility: str = DIRECT,
    author: str = OPERATOR,
    evidence: str = SOURCES,
    sources: tuple[Source, ...] = (Source(5, None),),
    subject: int | None = None,
    approves: int | None = None,
    under: int | None = None,
    confidence: int | None = None,
    contests: int | None = None,
    kind: str = "project",
    language: str | None = "de",
    fields: Mapping[str, FieldValue] | None = None,
    state: str = ACTIVE,
    reason: str | None = None,
    handle: str | None = None,
) -> Claim:
    return Claim(
        ENTITY,
        author,
        responsibility,
        evidence,
        sources,
        reason,
        handle,
        subject,
        approves,
        under,
        confidence,
        contests,
        EntityBody(kind, language, {"name": "Summer fair"} if fields is None else fields, state),
    )


def proposal(
    *,
    subject: int | None = None,
    contests: int | None = None,
    confidence: int | None = 40,
    fields: Mapping[str, FieldValue] | None = None,
) -> Claim:
    """An open entity by a model."""
    return entity(
        responsibility=OPEN,
        author=MODEL,
        subject=subject,
        contests=contests,
        confidence=confidence,
        fields=fields,
    )


def transitive(
    *,
    subject: int | None = 1,
    under: int = CLASS,
    confidence: int = 90,
    fields: Mapping[str, FieldValue] | None = None,
) -> Claim:
    """A transitive entity by a model, by default a further version of 1."""
    return entity(
        responsibility=TRANSITIVE,
        author=MODEL,
        subject=subject,
        under=under,
        confidence=confidence,
        fields=fields,
    )


def relation(
    *,
    responsibility: str = DIRECT,
    author: str = OPERATOR,
    subject: int | None = None,
    approves: int | None = None,
    under: int | None = None,
    confidence: int | None = None,
    contests: int | None = None,
    kind: str = "holds",
    start: int | Source = 10,
    to: int | None = 12,
    candidates: tuple[int, ...] | None = None,
    period: Period | None = None,
    fields: Mapping[str, FieldValue] | None = None,
    state: str = STANDING,
) -> Claim:
    """A relation resting on event 6, or, when it starts at an event, on
    that event as the start names it: the start is among the sources."""
    return Claim(
        RELATION,
        author,
        responsibility,
        SOURCES,
        (start,) if isinstance(start, Source) else (Source(6, (1, 2)),),
        None,
        None,
        subject,
        approves,
        under,
        confidence,
        contests,
        RelationBody(kind, start, to, candidates, period, fields or {}, state),
    )


def row(
    row_id: int, claim: Claim | Statement, *, erased: bool = False
) -> tuple[int, datetime, Mapping[str, object] | None]:
    payload = claim_payload(claim) if isinstance(claim, Claim) else payload_of(claim)
    return (row_id, NOW + timedelta(minutes=row_id), None if erased else payload)


def rejection(of: int) -> Statement:
    return Statement(
        REJECTION, OPERATOR, DIRECT, (Source(5, None),), "wrong", None, None, None, of, None
    )


def approval(subject: int, of: int, claim: Claim) -> Claim:
    """The operator's approval of `claim`, which is version `of` of `subject`:
    content, sources, evidence, author and confidence copied."""
    return replace(
        claim, responsibility=DIRECT, subject=subject, approves=of, under=None, contests=None
    )


def good_entity() -> dict[str, object]:
    return claim_payload(entity())


def good_relation() -> dict[str, object]:
    return claim_payload(relation())


# --- Round trip -------------------------------------------------------------------


@pytest.mark.parametrize(
    "claim",
    [
        entity(),
        entity(language=None, reason="from the minutes", handle="nonce-1"),
        entity(evidence=RECOLLECTION, sources=()),
        entity(
            fields={
                "name": "Summer fair",
                "started": date(2026, 6, 1),
                "period": Period(date(2026, 6, 1), None),
                "lead": 10,
            },
            state=CLOSED,
        ),
        entity(sources=(Source(5, (1, 4, 9)), Source(8, None)), subject=3, state=RETRACTED),
        proposal(),
        proposal(confidence=None),
        proposal(subject=1, contests=2),
        transitive(subject=None),
        approval(1, 3, transitive()),
        relation(),
        relation(period=Period(date(2015, 1, 1), date(2019, 12, 31)), fields={"role": "chair"}),
        relation(period=Period(None, None), state=RETRACTED, subject=4),
        relation(responsibility=OPEN, author=MODEL, to=None, candidates=(11, 14)),
        relation(responsibility=OPEN, author=MODEL, subject=4, contests=4, confidence=70),
        relation(start=Source(5, (1, 2))),
        relation(start=Source(5, None), responsibility=OPEN, author=MODEL),
    ],
    ids=lambda claim: f"{claim.kind}-{claim.responsibility}",
)
def test_every_form_round_trips(claim: Claim) -> None:
    payload = claim_payload(claim)

    assert claim_problem(payload) is None
    assert parse_claim(payload) == claim
    assert claim_payload(cast_claim(parse_claim(payload))) == payload


def cast_claim(claim: Claim | None) -> Claim:
    assert claim is not None
    return claim


def test_the_payload_has_exactly_the_contract_keys() -> None:
    common = {"assertion", "author", "responsibility", "evidence", "sources", "reason"}
    common |= {"handle", "subject", "approves", "under", "confidence", "contests", "type"}

    assert set(good_entity()) == common | {"language", "fields", "state"}
    assert set(good_relation()) == common | {"from", "to", "period", "fields", "state"}
    assert good_relation()["from"] == {"entity": 10}
    assert good_relation()["to"] == {"entity": 12}
    assert {ENTITY, RELATION} == GRAPH_KINDS
    assert LEVELS == (DIRECT, TRANSITIVE, OPEN)


def test_a_period_is_written_with_from_and_to() -> None:
    payload = claim_payload(relation(period=Period(date(2015, 1, 1), None)))

    assert payload["period"] == {"from": "2015-01-01", "to": None}


def test_a_text_spelled_like_a_date_reads_back_as_the_same_payload() -> None:
    payload = claim_payload(entity(fields={"name": "2026-03-01"}))
    claim = cast_claim(parse_claim(payload))

    # The payload cannot tell the two apart; it reads as a date and writes
    # back as the same string.
    assert claim.body.fields["name"] == date(2026, 3, 1)
    assert claim_payload(claim) == payload


# --- Form faults ------------------------------------------------------------------


def changed(payload: dict[str, object], **changes: object) -> dict[str, object]:
    return {**payload, **changes}


def without(payload: dict[str, object], key: str) -> dict[str, object]:
    return {name: value for name, value in payload.items() if name != key}


MODEL_OPEN = claim_payload(proposal())
NO_UNITS: list[int] = []
BAD_PERIOD = (
    "the period is neither null nor from and to, each null or a date"
    " written YYYY-MM-DD, with from not after to"
)
BAD_FIELD_PERIOD = (
    "a field holds a period that is not from and to, each null or a date"
    " written YYYY-MM-DD, with from not after to"
)
QUESTION = claim_payload(relation(responsibility=OPEN, author=MODEL, to=None, candidates=(11, 14)))


@pytest.mark.parametrize(
    ("payload", "sentence"),
    [
        (
            changed(good_entity(), assertion="obligation"),
            "the assertion kind is neither entity nor relation",
        ),
        (
            without(good_entity(), "language"),
            "the keys of the payload are not those of the assertion kind",
        ),
        (
            changed(good_entity(), period=None),
            "the keys of the payload are not those of the assertion kind",
        ),
        (
            without(good_relation(), "period"),
            "the keys of the payload are not those of the assertion kind",
        ),
        (
            changed(good_entity(), author="model:"),
            "the author is neither human:operator nor model:<client>",
        ),
        (
            changed(good_entity(), responsibility="indirect"),
            "the responsibility is none of direct, transitive, open",
        ),
        (
            changed(good_entity(), evidence="hearsay"),
            "the evidence is neither sources nor recollection",
        ),
        (changed(good_entity(), sources={}), "the sources are not a list"),
        (
            changed(good_entity(), sources=[]),
            "the sources are empty: a statement from sources needs at least one",
        ),
        (
            changed(good_entity(), sources=[{"event": 0, "units": None}]),
            "a source names an event that is not a whole number of at least 1",
        ),
        (changed(good_entity(), sources=["event 5"]), "a source is not an object"),
        (
            changed(good_entity(), sources=[{"event": 5}]),
            "a source must have exactly the keys event and units",
        ),
        (
            changed(good_entity(), sources=[{"event": 5, "units": "1"}]),
            "the units of a source are neither a list nor null",
        ),
        (
            changed(good_entity(), sources=[{"event": 5, "units": NO_UNITS}]),
            "the units of a source are an empty list: use null for the whole event",
        ),
        (
            changed(good_entity(), sources=[{"event": 5, "units": [1.5]}]),
            "the units of a source are not whole numbers",
        ),
        (
            changed(good_entity(), sources=[{"event": 5, "units": [2, 1]}]),
            "the units of a source are not ascending without duplicates",
        ),
        (changed(good_entity(), evidence=RECOLLECTION), "a recollection has no sources"),
        (
            changed(MODEL_OPEN, evidence=RECOLLECTION, sources=[]),
            "only the operator writes a recollection",
        ),
        (
            changed(good_entity(), evidence=RECOLLECTION, sources=[], responsibility=OPEN),
            "a recollection is direct",
        ),
        (changed(good_entity(), reason=""), "reason is neither null nor a non-empty text"),
        (changed(good_entity(), subject=0), "subject is neither null nor an event id"),
        (changed(good_entity(), under=True), "under is neither null nor an event id"),
        (
            changed(MODEL_OPEN, confidence=0.5),
            "confidence is neither null nor a whole number from 0 to 100",
        ),
        (
            changed(MODEL_OPEN, confidence=101),
            "confidence is neither null nor a whole number from 0 to 100",
        ),
        (
            changed(MODEL_OPEN, confidence=-1),
            "confidence is neither null nor a whole number from 0 to 100",
        ),
        (
            changed(MODEL_OPEN, confidence=True),
            "confidence is neither null nor a whole number from 0 to 100",
        ),
        (
            changed(good_entity(), type="Project"),
            "the type is not an identifier of the form a-z0-9_",
        ),
        (changed(good_entity(), approves=3), "an approval needs a subject"),
        (changed(MODEL_OPEN, subject=1, approves=3), "an approval is direct"),
        (
            changed(MODEL_OPEN, responsibility=DIRECT),
            "a version by a model is direct only as an approval",
        ),
        (
            changed(good_entity(), responsibility=TRANSITIVE, under=CLASS),
            "a transitive version is written by a model",
        ),
        (
            changed(MODEL_OPEN, responsibility=TRANSITIVE),
            "under names an approval class exactly on a transitive version",
        ),
        (
            changed(MODEL_OPEN, under=CLASS),
            "under names an approval class exactly on a transitive version",
        ),
        (
            changed(MODEL_OPEN, responsibility=TRANSITIVE, under=CLASS, confidence=None),
            "a transitive version carries a confidence",
        ),
        (changed(good_entity(), confidence=50), "the operator gives no confidence"),
        (
            changed(good_entity(), subject=1, contests=2),
            "contests stands only on an open version by a model",
        ),
        (
            changed(MODEL_OPEN, responsibility=TRANSITIVE, under=CLASS, subject=1, contests=2),
            "contests stands only on an open version by a model",
        ),
        (changed(MODEL_OPEN, contests=2), "an objection needs a subject"),
        (changed(good_entity(), language="EN"), "the language is neither null nor a language tag"),
        (changed(good_entity(), fields=[]), "the fields are not an object"),
        (
            changed(good_entity(), fields={"Name": "x"}),
            "a field name is not an identifier of the form a-z0-9_",
        ),
        (changed(good_entity(), fields={"name": " "}), "a field holds an empty text"),
        (changed(good_entity(), fields={"lead": 0}), "a field holds a number that is no entity id"),
        (
            changed(good_entity(), fields={"size": 1.5}),
            "a field holds a value that is none of text, date, period, entity id",
        ),
        (
            changed(good_entity(), fields={"done": True}),
            "a field holds a value that is none of text, date, period, entity id",
        ),
        (
            changed(good_entity(), fields={"tags": ["a"]}),
            "a field holds a value that is none of text, date, period, entity id",
        ),
        (
            changed(good_entity(), fields={"period": {"from": "2026-02-30", "to": None}}),
            BAD_FIELD_PERIOD,
        ),
        (
            changed(good_entity(), state="standing"),
            "the state of an entity is none of active, closed, retracted",
        ),
        (
            changed(good_relation(), state="closed"),
            "the state of a relation is neither standing nor retracted",
        ),
        (changed(good_relation(), period={"from": "2026-02-30", "to": None}), BAD_PERIOD),
        (changed(good_relation(), period={"from": "2020-01-01", "to": "2019-12-31"}), BAD_PERIOD),
        (changed(good_relation(), period={"from": "20260203", "to": None}), BAD_PERIOD),
        (changed(good_relation(), period={"from": None}), BAD_PERIOD),
        (
            changed(good_relation(), **{"from": {"event": 0, "units": None}}),
            "from names an event that is not a whole number of at least 1",
        ),
        (
            changed(good_relation(), **{"from": {"event": 5, "units": NO_UNITS}}),
            "the units of a source are an empty list: use null for the whole event",
        ),
        (
            changed(good_relation(), **{"from": 10}),
            "from is neither an entity nor an event with its units",
        ),
        (
            changed(good_relation(), **{"from": {"entity": "10"}}),
            "from is neither an entity nor an event with its units",
        ),
        (changed(good_relation(), to={"entity": -3}), "to names no entity id"),
        (
            changed(good_relation(), to={"entity": 3, "candidates": [4, 5]}),
            "to is neither an entity nor candidates",
        ),
        (changed(good_relation(), to=[3]), "to is neither an entity nor candidates"),
        (
            changed(good_relation(), to={"candidates": [11, 14]}),
            "candidates stand only in an open version",
        ),
        (
            changed(QUESTION, to={"candidates": [11]}),
            "the candidates are not 2 to 5 distinct entity ids",
        ),
        (
            changed(QUESTION, to={"candidates": [11, 11]}),
            "the candidates are not 2 to 5 distinct entity ids",
        ),
        (
            changed(QUESTION, to={"candidates": [11, 12, 13, 14, 15, 16]}),
            "the candidates are not 2 to 5 distinct entity ids",
        ),
        (
            changed(QUESTION, to={"candidates": [11, "12"]}),
            "the candidates are not 2 to 5 distinct entity ids",
        ),
        (
            changed(QUESTION, to={"candidates": "11, 12"}),
            "the candidates are not 2 to 5 distinct entity ids",
        ),
    ],
)
def test_each_form_fault_has_its_sentence(payload: dict[str, object], sentence: str) -> None:
    assert claim_problem(payload) == sentence
    assert parse_claim(payload) is None


def test_the_sentences_are_measured_against_good_payloads() -> None:
    # The control for the table above: the payloads it changes are sound.
    for payload in (good_entity(), good_relation(), MODEL_OPEN, QUESTION):
        assert claim_problem(payload) is None


def test_an_operator_may_write_a_recollection_but_a_model_may_not() -> None:
    remembered = changed(good_entity(), evidence=RECOLLECTION, sources=[])
    model = changed(MODEL_OPEN, evidence=RECOLLECTION, sources=[])

    assert claim_problem(remembered) is None
    assert claim_problem(model) == "only the operator writes a recollection"
    # Without sources and without recollection a model writes nothing either.
    assert claim_problem(changed(MODEL_OPEN, sources=[])) == (
        "the sources are empty: a statement from sources needs at least one"
    )


WEIRD: list[object] = [None, 1.5, [], {}, "x", True, -1, {"entity": None}, [None]]


@pytest.mark.parametrize("key", sorted(set(good_entity()) | set(good_relation())))
def test_claim_problem_never_raises(key: str) -> None:
    for base in (good_entity(), good_relation(), QUESTION):
        for value in WEIRD:
            problem = claim_problem({**base, key: value})
            assert problem is None or problem.strip()


def obligation_with(*, author: str = OPERATOR, sources: object = None) -> dict[str, object]:
    """An open obligation payload, changed at `author` and, if given, at
    `sources`: everything else is sound."""
    statement = Statement(
        OBLIGATION,
        author,
        OPEN,
        (Source(5, None),),
        None,
        None,
        None,
        None,
        None,
        ObligationBody("own", "circle:acme", "send the offer", None, "open"),
    )
    payload = payload_of(statement)
    return payload if sources is None else changed(payload, sources=sources)


AUTHORS = [
    OPERATOR,
    "model:claude",
    "model:" + "c" * 200,
    "model:" + "c" * 201,
    "model:",
    "model:a b",
    "model:x‮",
    "model:x ",
    "model:x ",
    "human:anna",
    "",
    "claude",
]


@pytest.mark.parametrize("author", AUTHORS)
def test_the_author_rule_is_that_of_obligations(author: str) -> None:
    claim = changed(claim_payload(entity(responsibility=OPEN)), author=author)

    assert claim_problem(claim) == assertion_problem(obligation_with(author=author))


def test_the_author_cases_fall_on_both_sides() -> None:
    # The control for the comparison above: its cases are neither all
    # accepted nor all refused, and the length bound runs between two of them.
    verdicts = {author: assertion_problem(obligation_with(author=author)) for author in AUTHORS}

    assert verdicts["model:" + "c" * 200] is None
    assert verdicts["model:" + "c" * 201] is not None
    assert verdicts["model:x "] is not None
    assert verdicts["model:x "] is not None
    assert verdicts[OPERATOR] is None


SOURCE_CASES: list[object] = [
    [{"event": 5, "units": None}],
    [{"event": 5, "units": [0, 3]}, {"event": 9, "units": None}],
    [{"event": 2**53 - 1, "units": [2**53 - 1]}],
    [{"event": 2**53, "units": None}],
    [{"event": 0, "units": None}],
    [{"event": True, "units": None}],
    [{"event": 5, "units": [-1]}],
    [{"event": 5, "units": [2, 2]}],
    [{"event": 5, "units": [3, 1]}],
    [{"event": 5, "units": [1.0]}],
    [{"event": 5, "units": [False]}],
    [{"event": 5, "units": NO_UNITS}],
    [{"event": 5, "units": "1"}],
    [{"event": 5}],
    [{"event": 5, "units": None, "extra": 1}],
    ["event 5"],
    [{"event": 5, "units": None}, "event 6"],
    "event 5",
]


@pytest.mark.parametrize("sources", SOURCE_CASES)
def test_the_source_rule_is_that_of_obligations(sources: object) -> None:
    # Only non-empty sources: there the two rules have to agree. An empty
    # list differs by design, since a recollection has none.
    claim = changed(good_entity(), sources=sources)

    assert claim_problem(claim) == assertion_problem(obligation_with(sources=sources))


def test_the_source_cases_fall_on_both_sides() -> None:
    verdicts = [assertion_problem(obligation_with(sources=case)) for case in SOURCE_CASES]

    assert verdicts[:3] == [None, None, None]
    assert all(verdict is not None for verdict in verdicts[3:])


@pytest.mark.parametrize(
    "name", ["project", "a", "a" * 40, "a" * 41, "Project", "1st", "x-y", "_x"]
)
def test_the_type_is_an_identifier_as_the_vocabulary_has_it(name: str) -> None:
    spec = KindSpec(
        ENTITY_KIND,
        name,
        {"en": "A kind"},
        (FieldSpec("name", "text", None, None, True),),
        frozenset(),
        None,
        None,
        False,
    )
    declared = vocabulary_problem(to_payload(spec, statement="declare it")) is None

    assert (claim_problem(changed(good_entity(), type=name)) is None) == declared


@pytest.mark.parametrize("language", ["de", "de-AT", "gsw", "deu-x", "DE", "d", "de_AT", "de-"])
def test_a_language_is_a_tag_as_the_vocabulary_has_it(language: str) -> None:
    spec = KindSpec(
        ENTITY_KIND,
        "project",
        {language: "A kind"},
        (FieldSpec("name", "text", None, None, True),),
        frozenset(),
        None,
        None,
        False,
    )
    declared = vocabulary_problem(to_payload(spec, statement="declare it")) is None

    assert (claim_problem(changed(good_entity(), language=language)) is None) == declared


# --- Checking against the vocabulary ----------------------------------------------


def text(name: str, *, required: bool = False) -> FieldSpec:
    return FieldSpec(name, "text", None, None, required)


def kind(
    declares: str,
    name: str,
    fields: tuple[FieldSpec, ...] = (),
    behaviors: frozenset[str] = frozenset(),
    from_: tuple[str, ...] | None = None,
    to: tuple[str, ...] | None = None,
    *,
    retired: bool = False,
) -> KindSpec:
    return KindSpec(declares, name, {"en": name}, fields, behaviors, from_, to, retired)


NAME = text("name", required=True)
KINDS = [
    *built_in_kinds(),
    kind(
        ENTITY_KIND,
        "project",
        (
            NAME,
            FieldSpec("started", "date", None, None, False),
            FieldSpec("status", "choice", ("planned", "running"), None, False),
            FieldSpec("lead", "ref", None, "person", False),
            FieldSpec("period", "period", None, None, False),
        ),
        frozenset({"closable", "period"}),
    ),
    kind(ENTITY_KIND, "person", (NAME,)),
    kind(ENTITY_KIND, "office", (NAME,)),
    kind(ENTITY_KIND, "organization", (NAME,)),
    kind(ENTITY_KIND, "relic", (NAME,), retired=True),
    kind(RELATION_KIND, "holds", (text("role"),), frozenset({"period"}), ("person",), ("office",)),
    kind(
        RELATION_KIND,
        "part_of",
        (),
        frozenset({"acyclic", "transitive"}),
        ("project",),
        ("project", "organization"),
    ),
    kind(RELATION_KIND, "concerns", (), frozenset(), ("event",), ("*",)),
    kind(RELATION_KIND, "knew", (), frozenset(), ("person",), ("person",), retired=True),
]
VOCABULARY = Vocabulary({(spec.declares, spec.name): spec for spec in KINDS}, {})
TYPES = {10: "person", 11: "project", 12: "office", 13: "circle", 14: "project", 15: "person"}


def conformance(claim: Claim, *, new_thread: bool = True) -> str | None:
    return conformance_problem(claim, VOCABULARY, new_thread=new_thread, entity_types=TYPES)


def test_a_claim_that_fits_the_vocabulary_has_no_problem() -> None:
    fields: dict[str, FieldValue] = {
        "name": "Summer fair",
        "started": date(2026, 6, 1),
        "status": "running",
        "lead": 10,
        "period": Period(date(2026, 6, 1), None),
    }

    assert conformance(entity(fields=fields)) is None
    assert conformance(entity(fields=fields, state=CLOSED)) is None
    assert (
        conformance(relation(period=Period(date(2015, 1, 1), None), fields={"role": "x"})) is None
    )
    assert conformance(relation(kind="part_of", start=11, to=14)) is None
    assert conformance(relation(kind="member_of", start=10, to=13)) is None


@pytest.mark.parametrize(
    ("claim", "sentence"),
    [
        (entity(kind="club"), "the type is not declared as a kind of entity in the vocabulary"),
        (
            relation(kind="project"),
            "the type is not declared as a kind of relation in the vocabulary",
        ),
        (entity(kind="relic"), "the kind is retired and takes no new entity"),
        (relation(kind="knew", to=15), "the kind is retired and takes no new relation"),
        (entity(fields={"name": "x", "colour": "red"}), "a field is not declared for its kind"),
        (entity(fields={"name": 10}), 'the field "name" is not a text'),
        (
            entity(fields={"name": "x", "started": "June"}),
            'the field "started" is not a date written YYYY-MM-DD',
        ),
        (
            entity(fields={"name": "x", "period": date(2026, 1, 1)}),
            'the field "period" is not a period',
        ),
        (
            entity(fields={"name": "x", "status": "done"}),
            'the field "status" holds none of the values its kind allows',
        ),
        (
            entity(fields={"name": "x", "status": 3}),
            'the field "status" holds none of the values its kind allows',
        ),
        (
            entity(fields={"name": "x", "lead": 99}),
            'the field "lead" names no standing entity of the kind it refers to',
        ),
        (
            entity(fields={"name": "x", "lead": 11}),
            'the field "lead" names no standing entity of the kind it refers to',
        ),
        (
            entity(fields={"name": "x", "lead": "Anna"}),
            'the field "lead" names no standing entity of the kind it refers to',
        ),
        (entity(fields={}), 'the field "name" is required'),
        (
            entity(kind="person", state=CLOSED),
            "the state closed needs a kind with the behavior closable",
        ),
        (
            relation(kind="part_of", start=11, to=14, period=Period(None, None)),
            "a period needs a relation kind with the behavior period",
        ),
        (relation(start=99), "an end of the relation is not an entity that stands"),
        (relation(to=99), "an end of the relation is not an entity that stands"),
        (
            relation(responsibility=OPEN, author=MODEL, to=None, candidates=(12, 99)),
            "an end of the relation is not an entity that stands",
        ),
        (
            relation(start=11),
            "the start of the relation is of a kind its relation kind does not start from",
        ),
        (
            relation(to=15),
            "the end of the relation is of a kind its relation kind does not point at",
        ),
        (
            relation(responsibility=OPEN, author=MODEL, to=None, candidates=(12, 15)),
            "the end of the relation is of a kind its relation kind does not point at",
        ),
        (
            relation(
                kind="member_of",
                start=10,
                to=13,
                responsibility=TRANSITIVE,
                author=MODEL,
                under=CLASS,
                confidence=99,
            ),
            "a kind the gate reads is never transitive",
        ),
        (
            entity(
                kind="circle", responsibility=TRANSITIVE, author=MODEL, under=CLASS, confidence=99
            ),
            "a kind the gate reads is never transitive",
        ),
    ],
)
def test_each_rule_of_the_vocabulary_has_its_sentence(claim: Claim, sentence: str) -> None:
    assert conformance(claim) == sentence


def test_a_date_that_does_not_exist_is_text_and_no_date() -> None:
    payload = changed(good_entity(), fields={"name": "x", "started": "2026-02-30"})
    claim = cast_claim(parse_claim(payload))

    # Sound as a form: the payload holds a text; the vocabulary wants a date.
    assert claim.body.fields["started"] == "2026-02-30"
    assert conformance(claim) == 'the field "started" is not a date written YYYY-MM-DD'
    good = changed(good_entity(), fields={"name": "x", "started": "2026-02-28"})
    assert conformance(cast_claim(parse_claim(good))) is None


def test_a_text_field_takes_a_text_spelled_like_a_date() -> None:
    payload = claim_payload(entity(fields={"name": "2026-03-01"}))

    assert conformance(cast_claim(parse_claim(payload))) is None


def test_a_retired_kind_takes_further_versions_but_no_new_thread() -> None:
    # Review Focus 4: close, retract or rename an entity of a retired kind.
    old = entity(kind="relic", subject=3, fields={"name": "renamed"})

    assert conformance(old, new_thread=False) is None
    assert (
        conformance(replace(old, body=replace(old.body, state=RETRACTED)), new_thread=False) is None
    )
    assert conformance(relation(kind="knew", to=15, subject=4), new_thread=False) is None
    assert conformance(old, new_thread=True) == "the kind is retired and takes no new entity"


def test_a_retracted_version_does_not_look_up_what_it_names() -> None:
    gone = relation(start=99, to=98, state=RETRACTED, subject=4)
    lead = entity(fields={"name": "x", "lead": 99}, state=RETRACTED, subject=3)

    assert conformance(gone, new_thread=False) is None
    assert conformance(lead, new_thread=False) is None
    # Its fields still have to fit: a retraction is a whole version.
    assert conformance(replace(lead, body=replace(lead.body, fields={"name": 3}))) == (
        'the field "name" is not a text'
    )


def test_a_kind_the_gate_reads_is_direct_or_open() -> None:
    membership = relation(kind="member_of", start=10, to=13)

    assert conformance(membership) is None
    assert conformance(replace(membership, responsibility=OPEN, author=MODEL)) is None
    transitive = replace(
        membership, responsibility=TRANSITIVE, author=MODEL, under=CLASS, confidence=99
    )
    assert conformance(transitive) == "a kind the gate reads is never transitive"
    holds = relation(responsibility=TRANSITIVE, author=MODEL, under=CLASS, confidence=99)
    assert conformance(holds) is None


# --- Folding: who wins ------------------------------------------------------------


def thread_of(
    rows: list[tuple[int, datetime, Mapping[str, object] | None]],
    classes: Mapping[int, ClassState] = ACTIVE_CLASS,
    subject: int = 1,
) -> tuple[Graph, int | None]:
    graph = fold_graph(rows, classes)
    winner = graph.threads[subject].winner(classes)
    return graph, None if winner is None else winner.id


def test_direct_beats_a_newer_transitive_and_transitive_a_newer_open() -> None:
    rows = [row(1, entity()), row(2, transitive()), row(3, proposal(subject=1))]

    assert thread_of(rows)[1] == 1
    first = [row(1, proposal()), row(2, transitive()), row(3, proposal(subject=1))]
    assert thread_of(first)[1] == 2


def test_within_a_level_the_latest_wins() -> None:
    rows = [row(1, proposal()), row(2, transitive()), row(3, transitive())]

    assert thread_of(rows)[1] == 3
    assert thread_of([*rows, row(4, entity(subject=1)), row(5, entity(subject=1))])[1] == 5


@pytest.mark.parametrize(
    ("state", "winner", "level"),
    [
        (ClassState(CLASS, revoked=False, demote=False), 2, TRANSITIVE),
        (ClassState(CLASS, revoked=True, demote=False), 2, TRANSITIVE),
        (ClassState(CLASS, revoked=True, demote=True), 3, OPEN),
        (None, 3, OPEN),
    ],
    ids=["in-force", "revoked", "revoked-demote", "unknown-class"],
)
def test_a_class_revoked_with_demote_or_unknown_counts_as_open(
    state: ClassState | None, winner: int, level: str
) -> None:
    classes = {} if state is None else {CLASS: state}
    rows = [row(1, proposal()), row(2, transitive()), row(3, proposal(subject=1))]
    graph, found = thread_of(rows, classes)

    assert found == winner
    assert level_of(graph.threads[1].versions[1], classes) == level


@pytest.mark.parametrize(
    ("claim", "level"),
    [
        (
            relation(
                responsibility=TRANSITIVE, author=MODEL, under=CLASS, confidence=90, kind="holds"
            ),
            TRANSITIVE,
        ),
        (
            relation(
                responsibility=TRANSITIVE,
                author=MODEL,
                under=CLASS,
                confidence=90,
                kind="member_of",
            ),
            OPEN,
        ),
        (
            entity(
                responsibility=TRANSITIVE,
                author=MODEL,
                under=CLASS,
                confidence=90,
                kind="circle",
                fields={"name": "Board"},
            ),
            OPEN,
        ),
    ],
    ids=["holds-control", "member_of", "circle"],
)
def test_a_forged_transitive_version_of_a_gate_kind_counts_as_open(
    claim: Claim, level: str
) -> None:
    """The write path never writes a transitive circle or membership, so
    such a row came around it; under a class in force it still must not
    stand on the class. Measured red with the gate-kind line taken out of
    `level_of` (both gate cases); the `holds` control stays green then."""
    graph = fold_graph([row(1, claim)], ACTIVE_CLASS)

    assert level_of(graph.threads[1].versions[0], ACTIVE_CLASS) == level


def test_a_demoted_version_can_be_rejected_and_approved_like_an_open_one() -> None:
    demoted = {CLASS: ClassState(CLASS, revoked=True, demote=True)}
    rows = [row(1, proposal()), row(2, transitive())]

    graph, found = thread_of([*rows, row(3, rejection(2))], demoted)
    assert found == 1
    assert graph.threads[1].rejected == {2}
    graph, found = thread_of([*rows, row(3, approval(1, 2, transitive()))], demoted)
    assert found == 3
    assert graph.threads[1].approved == {2}


def test_a_rejected_transitive_version_no_longer_wins() -> None:
    rows = [row(1, proposal()), row(2, transitive()), row(3, rejection(2))]

    assert thread_of(rows)[1] == 1


def test_an_approval_of_a_transitive_version_makes_it_direct() -> None:
    rows = [row(1, transitive(subject=None)), row(2, approval(1, 1, transitive(subject=None)))]
    graph, found = thread_of(rows)

    assert found == 2
    winner = graph.threads[1].versions[1].claim
    assert (winner.author, winner.responsibility, winner.approves) == (MODEL, DIRECT, 1)
    assert graph.threads[1].pending(ACTIVE_CLASS) == ()


def test_a_second_approval_and_an_approval_of_a_direct_version_are_skipped() -> None:
    rows = [row(1, entity()), row(2, transitive()), row(3, approval(1, 2, transitive()))]
    graph = fold_graph(
        [*rows, row(4, approval(1, 2, transitive())), row(5, approval(1, 1, entity()))],
        ACTIVE_CLASS,
    )

    assert [v.id for v in graph.threads[1].versions] == [1, 2, 3]


def test_the_fold_skips_what_is_no_graph_version() -> None:
    obligation = Statement(
        OBLIGATION,
        OPERATOR,
        DIRECT,
        (Source(5, None),),
        None,
        None,
        None,
        None,
        None,
        ObligationBody("own", "circle:acme", "send", None, "open"),
    )
    broken = changed(good_entity(), confidence=0.5)
    rows: list[tuple[int, datetime, Mapping[str, object] | None]] = [
        row(1, obligation),
        (2, NOW, broken),
        row(3, entity()),
        row(4, entity(subject=3), erased=True),
        row(5, entity(subject=77)),  # names nothing
        row(6, relation(subject=3)),  # not the kind of its thread
        row(7, rejection(1)),  # rejects an obligation
        (8, NOW, changed(payload_of(rejection(3)), responsibility=OPEN)),  # a broken rejection
    ]
    graph = fold_graph(rows, ACTIVE_CLASS)

    assert list(graph.threads) == [3]
    assert [v.id for v in graph.threads[3].versions] == [3]
    assert graph.threads[3].rejected == frozenset()


def test_a_thread_survives_the_erasure_of_its_first_version() -> None:
    rows = [row(1, entity(), erased=True), row(2, entity(subject=1, fields={"name": "x"}))]

    assert thread_of(rows)[1] == 2


def test_an_objection_must_name_a_direct_version_of_its_thread() -> None:
    rows = [row(1, entity()), row(2, proposal(subject=1)), row(3, entity(), erased=True)]
    graph = fold_graph(
        [
            *rows,
            row(4, proposal(subject=1, contests=2)),  # an open version: skipped
            row(5, proposal(subject=1, contests=99)),  # nothing: skipped
            row(6, proposal(subject=1, contests=3)),  # erased: stands
            row(7, proposal(subject=1, contests=1)),
        ],
        ACTIVE_CLASS,
    )

    assert [v.id for v in graph.threads[1].versions] == [1, 2, 6, 7]


# --- Pending, objections, questions -----------------------------------------------


def ids(versions: tuple[GraphVersion, ...]) -> list[int]:
    return [version.id for version in versions]


def test_an_objection_contests_the_current_direct_winner() -> None:
    rows = [row(1, entity()), row(2, proposal(subject=1, contests=1))]
    thread = fold_graph(rows, ACTIVE_CLASS).threads[1]

    assert thread.winner(ACTIVE_CLASS) == thread.versions[0]
    assert ids(thread.pending(ACTIVE_CLASS)) == [2]
    assert ids(thread.objections(ACTIVE_CLASS)) == [2]


def test_an_objection_against_a_superseded_direct_version_is_a_proposal() -> None:
    rows = [row(1, entity()), row(2, entity(subject=1)), row(3, proposal(subject=1, contests=1))]
    thread = fold_graph(rows, ACTIVE_CLASS).threads[1]

    assert ids(thread.pending(ACTIVE_CLASS)) == [3]
    assert thread.objections(ACTIVE_CLASS) == ()


def test_a_later_direct_version_overtakes_an_objection() -> None:
    rows = [row(1, entity()), row(2, proposal(subject=1, contests=1)), row(3, entity(subject=1))]
    thread = fold_graph(rows, ACTIVE_CLASS).threads[1]

    assert thread.pending(ACTIVE_CLASS) == ()
    assert thread.objections(ACTIVE_CLASS) == ()


def test_an_answered_objection_is_no_longer_one() -> None:
    rows = [row(1, entity()), row(2, proposal(subject=1, contests=1))]
    rejected = fold_graph([*rows, row(3, rejection(2))], ACTIVE_CLASS).threads[1]
    accepted = fold_graph(
        [*rows, row(3, approval(1, 2, proposal(subject=1, contests=1)))], ACTIVE_CLASS
    ).threads[1]

    assert rejected.objections(ACTIVE_CLASS) == ()
    assert accepted.objections(ACTIVE_CLASS) == ()
    assert cast_version(accepted.winner(ACTIVE_CLASS)).id == 3


def cast_version(version: GraphVersion | None) -> GraphVersion:
    assert version is not None
    return version


def test_there_is_no_objection_without_a_direct_winner() -> None:
    rows = [row(1, proposal()), row(2, transitive()), row(3, proposal(subject=1))]

    assert fold_graph(rows, ACTIVE_CLASS).threads[1].objections(ACTIVE_CLASS) == ()


def test_a_newer_transitive_version_waits_behind_a_direct_one() -> None:
    rows = [row(1, entity()), row(2, transitive())]
    thread = fold_graph(rows, ACTIVE_CLASS).threads[1]

    assert cast_version(thread.winner(ACTIVE_CLASS)).id == 1
    assert ids(thread.pending(ACTIVE_CLASS)) == [2]


def test_a_transitive_winner_overtakes_older_proposals() -> None:
    rows = [row(1, proposal()), row(2, proposal(subject=1)), row(3, transitive())]
    thread = fold_graph([*rows, row(4, proposal(subject=1))], ACTIVE_CLASS).threads[1]

    assert cast_version(thread.winner(ACTIVE_CLASS)).id == 3
    assert ids(thread.pending(ACTIVE_CLASS)) == [4]


QUESTION_CLAIM = relation(responsibility=OPEN, author=MODEL, to=None, candidates=(11, 14))


def test_a_question_is_asked_until_a_direct_version_answers_it() -> None:
    asked = [row(1, QUESTION_CLAIM)]
    thread = fold_graph(asked, ACTIVE_CLASS).threads[1]

    assert cast_version(thread.question(ACTIVE_CLASS)).id == 1
    assert thread.pending(ACTIVE_CLASS) == ()  # it stands as the proposal
    answered = fold_graph([*asked, row(2, relation(subject=1, to=11))], ACTIVE_CLASS)
    assert answered.threads[1].question(ACTIVE_CLASS) is None
    assert list(answered.relations()) == [1]


def test_a_question_behind_a_newer_proposal_is_still_asked() -> None:
    rows = [row(1, QUESTION_CLAIM), row(2, relation(responsibility=OPEN, author=MODEL, subject=1))]
    thread = fold_graph(rows, ACTIVE_CLASS).threads[1]

    assert cast_version(thread.winner(ACTIVE_CLASS)).id == 2
    assert cast_version(thread.question(ACTIVE_CLASS)).id == 1
    assert (
        fold_graph([*rows, row(3, rejection(1))], ACTIVE_CLASS).threads[1].question(ACTIVE_CLASS)
        is None
    )


def test_a_question_is_no_relation_yet() -> None:
    graph = fold_graph([row(1, QUESTION_CLAIM)], ACTIVE_CLASS)

    assert graph.relations() == {}
    assert not graph.reaches(10, 11, frozenset({"holds"}))


# --- What stands ------------------------------------------------------------------


def test_entities_are_the_winners_that_are_not_retracted() -> None:
    rows = [
        row(1, entity()),
        row(2, entity(kind="person")),
        row(3, entity(subject=2, kind="person", state=RETRACTED)),
        row(4, entity(subject=1, state=CLOSED)),
        row(5, proposal()),
    ]
    graph = fold_graph(rows, ACTIVE_CLASS)

    assert {subject: v.id for subject, v in graph.entities().items()} == {1: 4, 5: 5}


SPAN = Period(date(2015, 1, 1), date(2019, 12, 31))


@pytest.mark.parametrize(
    ("period", "day", "holds"),
    [
        (SPAN, date(2014, 12, 31), False),
        (SPAN, date(2015, 1, 1), True),
        (SPAN, date(2019, 12, 31), True),
        (SPAN, date(2020, 1, 1), False),
        (Period(None, date(2019, 12, 31)), date(1900, 1, 1), True),
        (Period(None, date(2019, 12, 31)), date(2020, 1, 1), False),
        (Period(date(2022, 1, 1), None), date(2021, 12, 31), False),
        (Period(date(2022, 1, 1), None), date(2999, 1, 1), True),
        (Period(None, None), date(2026, 1, 1), True),
        (None, date(2026, 1, 1), True),
    ],
)
def test_relations_at_a_day_hold_at_the_bounds_of_their_period(
    period: Period | None, day: date, holds: bool
) -> None:
    graph = fold_graph([row(1, relation(period=period))], ACTIVE_CLASS)

    assert (1 in graph.relations(at=day)) is holds
    assert 1 in graph.relations()


def test_a_retracted_relation_does_not_stand() -> None:
    rows = [row(1, relation()), row(2, relation(subject=1, state=RETRACTED))]

    assert fold_graph(rows, ACTIVE_CLASS).relations() == {}


def edge(
    start: int,
    to: int,
    *,
    subject: int | None = None,
    period: Period | None = None,
    state: str = STANDING,
) -> Claim:
    return relation(kind="part_of", start=start, to=to, subject=subject, period=period, state=state)


PART_OF = frozenset({"part_of"})


def test_reaches_follows_a_chain_in_its_direction() -> None:
    graph = fold_graph([row(1, edge(10, 11)), row(2, edge(11, 12))], ACTIVE_CLASS)

    assert graph.reaches(10, 12, PART_OF)
    assert graph.reaches(10, 11, PART_OF)
    assert not graph.reaches(12, 10, PART_OF)
    assert not graph.reaches(10, 10, PART_OF)
    assert not graph.reaches(10, 12, frozenset({"holds"}))


def test_reaches_finds_an_edge_to_itself() -> None:
    graph = fold_graph([row(1, edge(10, 10))], ACTIVE_CLASS)

    assert graph.reaches(10, 10, PART_OF)
    assert not graph.reaches(11, 11, PART_OF)


def test_reaches_finds_a_cycle_back_to_the_start() -> None:
    graph = fold_graph([row(1, edge(10, 11)), row(2, edge(11, 10))], ACTIVE_CLASS)

    assert graph.reaches(10, 10, PART_OF)


def test_reaches_leaves_out_the_relations_a_write_replaces() -> None:
    graph = fold_graph([row(1, edge(10, 11)), row(2, edge(11, 12))], ACTIVE_CLASS)

    # The write moves relation 2 elsewhere: its old edge is gone.
    assert not graph.reaches(10, 12, PART_OF, without=frozenset({2}))
    assert graph.reaches(10, 11, PART_OF, without=frozenset({2}))
    assert graph.reaches(10, 12, PART_OF)


def test_reaches_walks_only_what_stands_and_ignores_periods() -> None:
    rows = [
        row(1, edge(10, 11)),
        row(2, edge(11, 12, period=Period(None, date(2001, 1, 1)))),
        row(3, edge(12, 13)),
        row(4, edge(12, 13, subject=3, state=RETRACTED)),
    ]
    graph = fold_graph(rows, ACTIVE_CLASS)

    assert graph.reaches(10, 12, PART_OF)
    assert not graph.reaches(10, 13, PART_OF)


# --- Fix round 1: levels in reaches, a later transitive version, dates in a
# choice, rejections of direct versions, an event as the start ---------------

STANDS_FOR = frozenset({DIRECT, TRANSITIVE})


def test_an_open_edge_does_not_block_what_the_operator_stands_for() -> None:
    proposed = replace(edge(10, 11), responsibility=OPEN, author=MODEL, confidence=10)
    graph = fold_graph([row(1, proposed)], ACTIVE_CLASS)

    assert not graph.reaches(10, 11, PART_OF, levels=STANDS_FOR)
    assert graph.reaches(10, 11, PART_OF)  # every level by default


def test_direct_and_transitive_edges_count_for_what_the_operator_stands_for() -> None:
    standing = replace(
        edge(11, 12), responsibility=TRANSITIVE, author=MODEL, under=CLASS, confidence=90
    )
    graph = fold_graph([row(1, edge(10, 11)), row(2, standing)], ACTIVE_CLASS)
    demoted = {CLASS: ClassState(CLASS, revoked=True, demote=True)}

    assert graph.reaches(10, 12, PART_OF, levels=STANDS_FOR)
    assert not replace(graph, classes=demoted).reaches(10, 12, PART_OF, levels=STANDS_FOR)
    assert replace(graph, classes=demoted).reaches(10, 12, PART_OF)


def test_a_relation_that_starts_at_an_event_is_no_edge() -> None:
    graph = fold_graph([row(1, edge(10, 11)), row(2, relation(start=Source(5, None)))], {})

    assert list(graph.relations()) == [1, 2]
    assert graph.reaches(10, 11, frozenset({"part_of", "holds"}))
    assert not graph.reaches(5, 12, frozenset({"part_of", "holds"}))


def test_a_later_transitive_version_answers_a_question_and_overtakes_proposals() -> None:
    # Ruling T2-c of the 2026-10-14 assignments plan: the operator stands for
    # a transitive version through its class, so it ends the wait as a
    # direct one would.
    later = relation(responsibility=TRANSITIVE, author=MODEL, subject=1, under=CLASS, confidence=90)
    rows = [
        row(1, QUESTION_CLAIM),
        row(2, relation(responsibility=OPEN, author=MODEL, subject=1, to=14)),
        row(3, later),
    ]
    thread = fold_graph(rows, ACTIVE_CLASS).threads[1]

    assert cast_version(thread.winner(ACTIVE_CLASS)).id == 3
    assert thread.question(ACTIVE_CLASS) is None
    assert thread.pending(ACTIVE_CLASS) == ()
    demoted = {CLASS: ClassState(CLASS, revoked=True, demote=True)}
    assert cast_version(thread.question(demoted)).id == 1
    assert ids(thread.pending(demoted)) == [1, 2]


MILESTONES = Vocabulary(
    {
        (ENTITY_KIND, "milestone"): kind(
            ENTITY_KIND,
            "milestone",
            (NAME, FieldSpec("phase", "choice", ("2026-01-01", "later"), None, False)),
        )
    },
    {},
)


@pytest.mark.parametrize(
    ("phase", "sentence"),
    [
        ("2026-01-01", None),
        ("2026-01-02", 'the field "phase" holds none of the values its kind allows'),
        ("later", None),
    ],
)
def test_a_choice_spelled_like_a_date_gets_one_verdict_built_and_read_back(
    phase: str, sentence: str | None
) -> None:
    built = entity(kind="milestone", fields={"name": "Kick-off", "phase": phase})
    read_back = cast_claim(parse_claim(claim_payload(built)))

    def verdict(claim: Claim) -> str | None:
        return conformance_problem(claim, MILESTONES, new_thread=True, entity_types={})

    assert verdict(built) == sentence
    assert verdict(read_back) == sentence


def test_a_rejection_of_a_direct_version_is_ignored() -> None:
    rows = [row(1, entity()), row(2, rejection(1))]
    thread = fold_graph(rows, ACTIVE_CLASS).threads[1]

    assert thread.rejected == frozenset()
    assert cast_version(thread.winner(ACTIVE_CLASS)).id == 1
    proposed = [row(1, entity()), row(2, proposal(subject=1)), row(3, rejection(2))]
    assert fold_graph(proposed, ACTIVE_CLASS).threads[1].rejected == {2}


@pytest.mark.parametrize("state", [STANDING, RETRACTED])
def test_an_event_as_the_start_is_sound_form_and_fits_only_a_kind_that_starts_at_one(
    state: str,
) -> None:
    claim = relation(start=Source(5, (1, 2)), state=state)

    assert claim_problem(claim_payload(claim)) is None
    assert conformance(claim) == (
        "an event as the start of a relation needs a relation kind that starts at an event"
    )
    assert conformance(replace(claim, body=replace(claim.body, start=10))) is None


def test_a_kind_that_starts_at_an_event_takes_one_and_refuses_an_entity_start() -> None:
    """The control of the test above: `concerns` declares `event` in `from`,
    so an event starts it, and `holds` still refuses the same start."""
    assigned = relation(kind="concerns", start=Source(5, (1, 2)), to=11)

    assert conformance(assigned) is None
    assert (
        conformance(replace(assigned, body=replace(assigned.body, start=Source(5, None)))) is None
    )
    assert conformance(relation(kind="holds", start=Source(5, (1,)), to=12)) is not None
    entity_start = relation(kind="concerns", start=10, to=11)
    assert conformance(entity_start) == (
        "the start of the relation is of a kind its relation kind does not start from"
    )


@pytest.mark.parametrize("kind_of_end", sorted(set(TYPES.values())))
def test_an_end_of_any_kind_fits_when_the_relation_kind_points_at_every_kind(
    kind_of_end: str,
) -> None:
    """Measured red with the wildcard reduced to the kinds listed in `to`
    (which for `*` is none); the control is `holds`, whose `to` is one kind."""
    end = next(entity for entity, found in TYPES.items() if found == kind_of_end)

    assert conformance(relation(kind="concerns", start=Source(5, (1,)), to=end)) is None


def test_the_wildcard_does_not_take_what_does_not_stand() -> None:
    assert conformance(relation(kind="concerns", start=Source(5, (1,)), to=99)) == (
        "an end of the relation is not an entity that stands"
    )
    assert conformance(relation(kind="holds", start=10, to=99)) == (
        "an end of the relation is not an entity that stands"
    )
    retracted = relation(kind="concerns", start=Source(5, (1,)), to=99, state=RETRACTED)
    assert conformance(retracted) is None


def test_a_wildcard_end_does_not_lift_the_check_of_the_start_kind() -> None:
    assert conformance(relation(kind="holds", start=11, to=12)) == (
        "the start of the relation is of a kind its relation kind does not start from"
    )


# --- Changes ----------------------------------------------------------------------


def test_claim_changes_names_exactly_the_changed_fields() -> None:
    before = entity(fields={"name": "Summer fair", "started": date(2026, 6, 1)})
    after = entity(fields={"name": "Autumn fair", "status": "running"}, state=CLOSED)

    assert claim_changes(before, after) == (
        ("fields.name", "Summer fair", "Autumn fair"),
        ("fields.started", "2026-06-01", "(none)"),
        ("state", "active", "closed"),
        ("fields.status", "(none)", "running"),
    )
    span = entity(fields={"name": "x", "period": Period(None, date(2019, 12, 31))})
    assert claim_changes(entity(fields={"name": "x"}), span) == (
        ("fields.period", "(none)", "(open) to 2019-12-31"),
    )


def test_claim_changes_is_empty_for_the_same_content() -> None:
    claim = relation(period=SPAN)

    assert claim_changes(claim, replace(claim, author=MODEL, responsibility=OPEN)) == ()


def test_claim_changes_sees_the_ends_the_period_and_the_evidence() -> None:
    before = QUESTION_CLAIM
    after = relation(to=11, period=Period(date(2022, 1, 1), None))

    assert claim_changes(before, after) == (
        ("to", "candidates 11, 14", "entity 11"),
        ("period", "(none)", "2022-01-01 to (open)"),
    )
    remembered = entity(evidence=RECOLLECTION, sources=(), reason="I founded it")
    assert claim_changes(entity(), remembered) == (
        ("evidence", "sources", "recollection"),
        ("sources", "event 5", "(none)"),
        ("reason", "(none)", "I founded it"),
    )


# --- The property: who wins -------------------------------------------------------

STEP = st.sampled_from(["direct", "open", "transitive", "reject", "approve", "contest"])
steps = st.lists(st.tuples(STEP, st.integers(0, 30)), min_size=1, max_size=14)
erasures = st.sets(st.integers(min_value=1, max_value=15), max_size=6)
STATES = st.sampled_from([(False, False), (True, False), (True, True)])
KNOWN = (901, 902)
UNDER = (*KNOWN, 903)  # 903 is a class nobody knows
class_states = st.tuples(STATES, STATES)


def build_rows(
    first: str, plan: list[tuple[str, int]], erased: set[int]
) -> list[tuple[int, datetime, Mapping[str, object] | None]]:
    """One entity thread named 1, its versions numbered by row."""
    written: dict[int, Claim] = {}
    answerable: list[int] = []
    direct: list[int] = []

    def version(number: int, action: str, pick: int) -> Claim | Statement:
        subject = None if number == 1 else 1
        target = answerable[pick % len(answerable)] if answerable else None
        rejectable = answerable + direct  # a rejection of a direct version is ignored
        if action == "direct":
            direct.append(number)
            return entity(subject=subject, fields={"name": f"v{number}"})
        if action == "transitive":
            answerable.append(number)
            under = UNDER[pick % len(UNDER)]
            return transitive(subject=subject, under=under, fields={"name": f"v{number}"})
        if action == "reject" and rejectable:
            return rejection(rejectable[pick % len(rejectable)])
        if action == "approve" and target is not None:
            direct.append(number)
            return approval(1, target, written[target])
        answerable.append(number)
        contests = direct[pick % len(direct)] if action == "contest" and direct else None
        return proposal(subject=subject, contests=contests, fields={"name": f"v{number}"})

    rows: list[tuple[int, datetime, Mapping[str, object] | None]] = []
    for number, (action, pick) in enumerate([(first, 0), *plan], start=1):
        made = version(number, action, pick)
        if isinstance(made, Claim):
            written[number] = made
        rows.append(row(number, made, erased=number in erased))
    return rows


def expected_level(claim: Claim, classes: Mapping[int, ClassState]) -> str:
    if claim.responsibility != TRANSITIVE:
        return claim.responsibility
    state = classes.get(claim.under or 0)
    return OPEN if state is None or (state.revoked and state.demote) else TRANSITIVE


def expected_versions(
    rows: list[tuple[int, datetime, Mapping[str, object] | None]],
) -> tuple[dict[int, Claim], set[int], set[int]]:
    """The versions that stand, the ids answered, and the ids rejected,
    worked out from the rows alone and not from `fold_graph`."""
    versions: dict[int, Claim] = {}
    answered: set[int] = set()
    rejected: set[int] = set()
    gone = {row_id for row_id, _at, payload in rows if payload is None}
    for row_id, _at, payload in rows:
        if payload is None:
            continue
        if payload["assertion"] == REJECTION:
            of = cast_int(cast_statement(parse_statement(payload)).of)
            if of in versions and versions[of].responsibility != DIRECT:
                rejected.add(of)
                answered.add(of)
            continue
        claim = cast_claim(parse_claim(payload))
        target = claim.contests
        if (
            target is not None
            and target not in gone
            and (target not in versions or versions[target].responsibility != DIRECT)
        ):
            continue
        if claim.approves is not None:
            proposed = versions.get(claim.approves)
            if claim.approves in answered or not (
                claim.approves in gone
                or (proposed is not None and proposed.responsibility in (OPEN, TRANSITIVE))
            ):
                continue
            answered.add(claim.approves)
        versions[row_id] = claim
    return versions, answered, rejected


# No deadline: under --cov one example can pass 200 ms and fail the whole run.
# Four hundred examples, not the default hundred: measured on 2026-10-14 with
# `level_of` ignoring `demote`, a hundred went red under three seeds of five
# and four hundred under ten of ten, in 0.6 s green under --cov.
@settings(deadline=None, max_examples=400)
@given(
    first=st.sampled_from(["direct", "open", "transitive"]),
    plan=steps,
    erased=erasures,
    states=class_states,
)
def test_the_winner_is_direct_else_transitive_else_open_and_the_latest_within(
    first: str,
    plan: list[tuple[str, int]],
    erased: set[int],
    states: tuple[tuple[bool, bool], tuple[bool, bool]],
) -> None:
    classes = {
        class_id: ClassState(class_id, revoked, demote)
        for class_id, (revoked, demote) in zip(KNOWN, states, strict=True)
    }
    rows = build_rows(first, plan, erased)
    versions, answered, rejected = expected_versions(rows)
    if not versions:
        assert fold_graph(rows, classes).threads == {}
        return

    levels = {i: expected_level(claim, classes) for i, claim in versions.items()}
    direct = [i for i in versions if levels[i] == DIRECT]
    standing = [i for i in versions if levels[i] == TRANSITIVE and i not in answered]
    unanswered = [i for i in versions if levels[i] == OPEN and i not in answered]
    expected = (direct or standing or unanswered or [None])[-1]
    anchor = (direct or standing or [None])[-1]
    if anchor is None:
        pending = unanswered[:-1]
    else:
        pending = [i for i in versions if i > anchor and levels[i] != DIRECT and i not in answered]
    objections = [i for i in pending if direct and versions[i].contests == direct[-1]]

    thread = fold_graph(rows, classes).threads[1]
    winner = thread.winner(classes)
    assert [version.id for version in thread.versions] == list(versions)
    assert thread.rejected == rejected
    assert (winner.id if winner else None) == expected
    assert ids(thread.pending(classes)) == pending
    assert ids(thread.objections(classes)) == objections
    if direct:
        # A transitive version never wins over a direct one.
        assert winner is not None
        assert winner.claim.responsibility == DIRECT


def cast_statement(statement: Statement | None) -> Statement:
    assert statement is not None
    return statement


def cast_int(value: int | None) -> int:
    assert value is not None
    return value


# --- An event at the start is among the sources (decision 3 of the 2026-10-15
# assignments plan, phase 2) -----------------------------------------------------


def assigned(start: Source, *sources: Source, evidence: str = SOURCES) -> Claim:
    """An assignment of `start` to project 11, resting on `sources`."""
    claim = relation(kind="concerns", start=start, to=11)
    return replace(claim, evidence=evidence, sources=sources)


@pytest.mark.parametrize(
    ("start", "sources"),
    [
        (Source(5, None), (Source(5, None),)),
        (Source(5, (2,)), (Source(5, None),)),
        (Source(5, (2, 3)), (Source(5, (1, 2, 3)),)),
        (Source(5, (2, 3)), (Source(7, None), Source(5, (2, 3)))),
    ],
)
def test_a_source_that_covers_the_start_makes_the_form_sound(
    start: Source, sources: tuple[Source, ...]
) -> None:
    """`units: null` covers every unit; a list covers the units it lists."""
    claim = assigned(start, *sources)

    assert claim_problem(claim_payload(claim)) is None
    assert fold_graph([row(1, claim)], {}).threads[1].versions[0].claim == claim


@pytest.mark.parametrize(
    ("start", "sources"),
    [
        (Source(5, None), (Source(6, None),)),
        (Source(5, None), (Source(5, (1, 2)),)),
        (Source(5, (2, 3)), (Source(5, (2,)),)),
        (Source(5, (2, 3)), (Source(5, (2,)), Source(5, (3,)))),
    ],
)
def test_a_start_no_source_covers_is_no_sound_form_and_does_not_stand(
    start: Source, sources: tuple[Source, ...]
) -> None:
    """Measured red with `_start_problem` answering None. Two sources of the
    same event that cover the start only together do not: one entry covers
    it, as the rule says, and the command line and the MCP server add the
    start as one entry of its own."""
    claim = assigned(start, *sources)

    assert claim_problem(claim_payload(claim)) == START_NOT_A_SOURCE
    assert parse_claim(claim_payload(claim)) is None
    assert fold_graph([row(1, claim)], {}).threads == {}


def test_a_recollection_does_not_start_at_an_event() -> None:
    """A recollection has no sources, so nothing can cover the start: an
    assignment rests on the mail it is about."""
    claim = assigned(Source(5, None), evidence=RECOLLECTION)

    assert claim_problem(claim_payload(claim)) == START_NOT_A_SOURCE


def test_an_entity_at_the_start_needs_no_source_of_its_own() -> None:
    """The control of the two tests above: the rule reads an event start
    only."""
    claim = replace(relation(), sources=(Source(6, None),))

    assert claim_problem(claim_payload(claim)) is None


def test_covers_reads_the_event_and_the_units() -> None:
    assert covers(Source(5, None), Source(5, (1,)))
    assert covers(Source(5, (1, 2)), Source(5, (2,)))
    assert not covers(Source(5, (1, 2)), Source(5, None))
    assert not covers(Source(6, None), Source(5, None))


def test_sources_with_start_adds_an_event_start_that_no_source_names() -> None:
    start = Source(5, (2,))

    assert sources_with_start(start, ()) == (start,)
    assert sources_with_start(start, (Source(6, None),)) == (Source(6, None), start)
    assert sources_with_start(start, (Source(5, None),)) == (Source(5, None),)
    # Named with other units: left as given, for the form to refuse, not
    # merged into a claim that rests on more than the caller said.
    assert sources_with_start(start, (Source(5, (1,)),)) == (Source(5, (1,)),)
    assert sources_with_start(10, (Source(6, None),)) == (Source(6, None),)
