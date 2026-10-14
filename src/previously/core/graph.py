# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The graph: entities and relations as assertions, their payload form, three
levels of responsibility, and the fold into a graph.

Pure: no database, no clock. A caller hands in rows in chain order and the
state of the approval classes, and gets back what stands.

An entity or a relation is an assertion of the kind `entity` or `relation`
under the event kind `assertion`, beside obligations and decisions. Like them
it is named after the event of its first version, and each further version
says everything that holds after it and carries that name as `subject`.

Three levels decide which version stands. `direct`: the operator stands for
it, written or approved by him. `transitive`: the operator stands for it
because he allowed this class of statements in advance; a model wrote it
under the approval class that `under` names. `open`: a proposal nobody stands
for. Direct beats transitive beats open, and within one level the latest
version wins. A transitive version whose class was revoked with `demote`
counts as open from then on, and so does one whose class is unknown: a
statement nobody authorized stands for nothing.

The form is hashed into the log for good, so it is checked as strictly as an
obligation: exactly the keys of the subtype, no float, no date but
`YYYY-MM-DD`. `claim_problem` checks the form alone; `conformance_problem`
checks a claim against a vocabulary. Both return one sentence that never
contains text found in the payload.
"""

from collections.abc import Iterable
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from datetime import date
from datetime import datetime
from itertools import pairwise
from previously.core.assertion import DIRECT
from previously.core.assertion import MODEL_PREFIX
from previously.core.assertion import OPEN
from previously.core.assertion import OPERATOR
from previously.core.assertion import parse_statement
from previously.core.assertion import REJECTION
from previously.core.assertion import Source
from previously.core.canonical import MAX_SAFE_INT
from previously.core.vocabulary import CHOICE
from previously.core.vocabulary import CLOSABLE
from previously.core.vocabulary import DATE
from previously.core.vocabulary import ENTITY_KIND
from previously.core.vocabulary import GATE_TYPES
from previously.core.vocabulary import PERIOD
from previously.core.vocabulary import PERIOD_BEHAVIOR
from previously.core.vocabulary import RELATION_KIND
from previously.core.vocabulary import TEXT
from typing import cast
from typing import Final
from typing import TYPE_CHECKING

import re
import unicodedata


if TYPE_CHECKING:
    from previously.core.vocabulary import FieldSpec
    from previously.core.vocabulary import KindSpec
    from previously.core.vocabulary import Vocabulary


ENTITY: Final = ENTITY_KIND
RELATION: Final = RELATION_KIND
GRAPH_KINDS: Final = frozenset({ENTITY, RELATION})

# The responsibility level, not the behavior `transitive` of a relation kind
# in core/vocabulary.py, which carries a relation upwards. Same word, two
# meanings, kept apart by their modules.
TRANSITIVE: Final = "transitive"
LEVELS: Final = (DIRECT, TRANSITIVE, OPEN)

SOURCES: Final = "sources"
RECOLLECTION: Final = "recollection"
EVIDENCE: Final = (SOURCES, RECOLLECTION)

ACTIVE: Final = "active"
CLOSED: Final = "closed"
RETRACTED: Final = "retracted"
STANDING: Final = "standing"
ENTITY_STATES: Final = (ACTIVE, CLOSED, RETRACTED)
RELATION_STATES: Final = (STANDING, RETRACTED)

MAX_CONFIDENCE: Final = 100
MIN_CANDIDATES: Final = 2
MAX_CANDIDATES: Final = 5

# The same patterns as an identifier and a language tag in
# core/vocabulary.py, where they are private; tests/test_graph.py holds the
# two copies against each other.
_IDENTIFIER = re.compile(r"[a-z][a-z0-9_]{0,39}")
_LANGUAGE = re.compile(r"[a-z]{2,3}(-[A-Za-z0-9]{1,8})*")
_DATE_FORM = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)
_MAX_CLIENT = 200

_COMMON_KEYS: Final = frozenset(
    {"assertion", "author", "responsibility", "evidence", "sources", "reason", "handle"}
    | {"subject", "approves", "under", "confidence", "contests", "type"}
)
_ENTITY_KEYS: Final = _COMMON_KEYS | {"language", "fields", "state"}
_RELATION_KEYS: Final = _COMMON_KEYS | {"from", "to", "period", "fields", "state"}
_KEYS: Final = {ENTITY: _ENTITY_KEYS, RELATION: _RELATION_KEYS}


# --- Values -----------------------------------------------------------------------


@dataclass(frozen=True)
class Period:
    """When something held, with open ends as `None`. Both ends are
    inclusive: "office holder until 2019-12-31" holds on that day."""

    start: date | None
    end: date | None

    def holds(self, day: date) -> bool:
        return (self.start is None or self.start <= day) and (self.end is None or day <= self.end)


type FieldValue = str | date | Period | int


@dataclass(frozen=True)
class EntityBody:
    type: str
    language: str | None
    fields: Mapping[str, FieldValue]
    state: str


@dataclass(frozen=True)
class RelationBody:
    """`start` is the entity in `from`; `to` is the entity it points at, or
    `None` for a question, which names `candidates` instead."""

    type: str
    start: int
    to: int | None
    candidates: tuple[int, ...] | None
    period: Period | None
    fields: Mapping[str, FieldValue]
    state: str


# Not `Statement`: that name is taken twice, by the obligation and decision in
# core/assertion.py and by a type alias in core/policy.py.
@dataclass(frozen=True)
class Claim:
    kind: str
    author: str
    responsibility: str
    evidence: str
    sources: tuple[Source, ...]
    reason: str | None
    handle: str | None
    subject: int | None
    approves: int | None
    under: int | None
    confidence: int | None
    contests: int | None
    body: EntityBody | RelationBody


def _period_payload(period: Period) -> dict[str, object]:
    return {
        "from": None if period.start is None else period.start.isoformat(),
        "to": None if period.end is None else period.end.isoformat(),
    }


def _value_payload(value: FieldValue) -> object:
    if isinstance(value, Period):
        return _period_payload(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


def _source_payload(source: Source) -> dict[str, object]:
    units: list[int] | None = None if source.units is None else list(source.units)
    return {"event": source.event, "units": units}


def claim_payload(claim: Claim) -> dict[str, object]:
    """The payload a claim is written as; the inverse of `parse_claim`."""
    body = claim.body
    payload: dict[str, object] = {
        "assertion": claim.kind,
        "author": claim.author,
        "responsibility": claim.responsibility,
        "evidence": claim.evidence,
        "sources": [_source_payload(source) for source in claim.sources],
        "reason": claim.reason,
        "handle": claim.handle,
        "subject": claim.subject,
        "approves": claim.approves,
        "under": claim.under,
        "confidence": claim.confidence,
        "contests": claim.contests,
        "type": body.type,
        "fields": {name: _value_payload(value) for name, value in body.fields.items()},
        "state": body.state,
    }
    if isinstance(body, EntityBody):
        payload["language"] = body.language
    else:
        payload["from"] = {"entity": body.start}
        if body.candidates is not None:
            payload["to"] = {"candidates": list(body.candidates)}
        else:
            payload["to"] = {"entity": body.to}
        payload["period"] = None if body.period is None else _period_payload(body.period)
    return payload


# --- Checking the form ------------------------------------------------------------


def _is_id(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= MAX_SAFE_INT


def _date(value: object) -> date | None:
    # The form is checked before `fromisoformat`, which would also take
    # `20260203` and `2026-W05-1`; the payload carries one spelling only.
    if not isinstance(value, str) or _DATE_FORM.fullmatch(value) is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _has_forbidden_character(text: str) -> bool:
    return any(unicodedata.category(char) in ("Cc", "Cf") or char in "  " for char in text)


def _author_problem(author: object) -> str | None:
    # The rule of core/assertion.py, where it is private; tests/test_graph.py
    # holds the two against each other on the same authors.
    if author == OPERATOR:
        return None
    if isinstance(author, str) and author.startswith(MODEL_PREFIX):
        client = author[len(MODEL_PREFIX) :]
        if (
            0 < len(client) <= _MAX_CLIENT
            and not any(char.isspace() for char in client)
            and not _has_forbidden_character(client)
        ):
            return None
    return "the author is neither human:operator nor model:<client>"


def _units_problem(units: object) -> str | None:
    if units is None:
        return None
    if not isinstance(units, list):
        return "the units of a source are neither a list nor null"
    seqs = cast("list[object]", units)
    if not seqs:
        return "the units of a source are an empty list: use null for the whole event"
    if not all(
        isinstance(seq, int) and not isinstance(seq, bool) and 0 <= seq <= MAX_SAFE_INT
        for seq in seqs
    ):
        return "the units of a source are not whole numbers"
    ints = cast("list[int]", seqs)
    if any(later <= earlier for earlier, later in pairwise(ints)):
        return "the units of a source are not ascending without duplicates"
    return None


def _source_problem(item: object) -> str | None:
    if not isinstance(item, dict):
        return "a source is not an object"
    entry = cast("dict[str, object]", item)
    if set(entry) != {"event", "units"}:
        return "a source must have exactly the keys event and units"
    if not _is_id(entry["event"]):
        return "a source names an event that is not a whole number of at least 1"
    return _units_problem(entry["units"])


def _evidence_problem(payload: Mapping[str, object]) -> str | None:
    evidence, sources = payload["evidence"], payload["sources"]
    if evidence not in EVIDENCE:
        return "the evidence is neither sources nor recollection"
    if not isinstance(sources, list):
        return "the sources are not a list"
    items = cast("list[object]", sources)
    if evidence == RECOLLECTION:
        # A recollection is what the operator remembers; a source beside it
        # would make it something else.
        return "a recollection has no sources" if items else None
    if not items:
        return "the sources are empty: a statement from sources needs at least one"
    for item in items:
        problem = _source_problem(item)
        if problem is not None:
            return problem
    return None


def _scalar_problem(payload: Mapping[str, object]) -> str | None:
    for key in ("reason", "handle"):
        value = payload[key]
        if value is not None and not (isinstance(value, str) and value.strip()):
            return f"{key} is neither null nor a non-empty text"
    for key in ("subject", "approves", "under", "contests"):
        value = payload[key]
        if value is not None and not _is_id(value):
            return f"{key} is neither null nor an event id"
    confidence = payload["confidence"]
    if confidence is not None and not (
        isinstance(confidence, int)
        and not isinstance(confidence, bool)
        and 0 <= confidence <= MAX_CONFIDENCE
    ):
        return f"confidence is neither null nor a whole number from 0 to {MAX_CONFIDENCE}"
    kind = payload["type"]
    if not isinstance(kind, str) or _IDENTIFIER.fullmatch(kind) is None:
        return "the type is not an identifier of the form a-z0-9_"
    return None


def _level_problem(payload: Mapping[str, object]) -> str | None:
    """The rules between author, level, evidence and the references."""
    author = cast("str", payload["author"])
    responsibility = payload["responsibility"]
    model = author.startswith(MODEL_PREFIX)
    approves, subject = payload["approves"], payload["subject"]
    # A model remembers nothing: what it says rests on sources. The operator
    # stands for his recollection himself, so it is direct.
    if payload["evidence"] == RECOLLECTION and model:
        return "only the operator writes a recollection"
    if payload["evidence"] == RECOLLECTION and responsibility != DIRECT:
        return "a recollection is direct"
    if approves is not None and subject is None:
        return "an approval needs a subject"
    if approves is not None and responsibility != DIRECT:
        return "an approval is direct"
    # A model proposes; what it writes is direct only when it is an approval,
    # which makes the operator's choice its own. Otherwise a proposal that
    # came around the MCP tool would outrank the operator's direct version
    # ({ref}`assertions-responsibility`). The rule for obligations is ruling
    # F-6 of the 2026-10-12 assertions plan.
    if model and responsibility == DIRECT and approves is None:
        return "a version by a model is direct only as an approval"
    return _transitive_problem(payload, model=model)


def _transitive_problem(payload: Mapping[str, object], *, model: bool) -> str | None:
    responsibility = payload["responsibility"]
    transitive = responsibility == TRANSITIVE
    # The operator stands for a transitive version only through the class a
    # model wrote it under, and the class compares the model's confidence
    # with its threshold; without the three there is nothing to stand on.
    if transitive and not model:
        return "a transitive version is written by a model"
    if transitive != (payload["under"] is not None):
        return "under names an approval class exactly on a transitive version"
    if transitive and payload["confidence"] is None:
        return "a transitive version carries a confidence"
    if not model and payload["confidence"] is not None:
        return "the operator gives no confidence"
    if payload["contests"] is not None:
        # An objection is a model's proposal against what the operator
        # stands for; it goes to him whatever its confidence.
        if responsibility != OPEN or not model:
            return "contests stands only on an open version by a model"
        if payload["subject"] is None:
            return "an objection needs a subject"
    return None


def _period_of(value: object) -> Period | None:
    """The period a payload value holds, or None if it holds none."""
    if not isinstance(value, dict):
        return None
    entry = cast("dict[str, object]", value)
    if set(entry) != {"from", "to"}:
        return None
    start, end = entry["from"], entry["to"]
    if (start is not None and _date(start) is None) or (end is not None and _date(end) is None):
        return None
    period = Period(_date(start), _date(end))
    if period.start is not None and period.end is not None and period.end < period.start:
        return None
    return period


def _value_problem(value: object) -> str | None:
    if isinstance(value, str):
        return None if value.strip() else "a field holds an empty text"
    if isinstance(value, int) and not isinstance(value, bool):
        return None if _is_id(value) else "a field holds a number that is no entity id"
    if isinstance(value, dict):
        if _period_of(cast("dict[str, object]", value)) is None:
            return (
                "a field holds a period that is not from and to, each null or a date"
                " written YYYY-MM-DD, with from not after to"
            )
        return None
    return "a field holds a value that is none of text, date, period, entity id"


def _fields_problem(fields: object) -> str | None:
    if not isinstance(fields, dict):
        return "the fields are not an object"
    for name, value in cast("dict[object, object]", fields).items():
        if not isinstance(name, str) or _IDENTIFIER.fullmatch(name) is None:
            return "a field name is not an identifier of the form a-z0-9_"
        problem = _value_problem(value)
        if problem is not None:
            return problem
    return None


def _entity_problem(payload: Mapping[str, object]) -> str | None:
    language = payload["language"]
    if language is not None and (
        not isinstance(language, str) or _LANGUAGE.fullmatch(language) is None
    ):
        return "the language is neither null nor a language tag"
    problem = _fields_problem(payload["fields"])
    if problem is not None:
        return problem
    if payload["state"] not in ENTITY_STATES:
        return "the state of an entity is none of active, closed, retracted"
    return None


def _end_problem(value: object) -> str | None:
    if isinstance(value, dict) and set(cast("dict[str, object]", value)) == {"event", "units"}:
        # The form keeps room for an event as the start, which phase 2 brings;
        # until then it is refused with the sentence the write path says.
        return "an event as the start of a relation comes with assignments"
    if (
        not isinstance(value, dict)
        or set(cast("dict[str, object]", value)) != {"entity"}
        or not _is_id(cast("dict[str, object]", value)["entity"])
    ):
        return "from is not an object with the id of an entity"
    return None


def _to_problem(value: object, responsibility: object) -> str | None:
    if not isinstance(value, dict):
        return "to is neither an entity nor candidates"
    entry = cast("dict[str, object]", value)
    if set(entry) == {"entity"}:
        return None if _is_id(entry["entity"]) else "to names no entity id"
    if set(entry) != {"candidates"}:
        return "to is neither an entity nor candidates"
    # A question is a model's: it asks instead of guessing, and the answer
    # is the operator's direct version.
    if responsibility != OPEN:
        return "candidates stand only in an open version"
    candidates = entry["candidates"]
    if (
        not isinstance(candidates, list)
        or not all(_is_id(item) for item in cast("list[object]", candidates))
        or not MIN_CANDIDATES <= len(cast("list[object]", candidates)) <= MAX_CANDIDATES
        or len(set(cast("list[int]", candidates))) != len(cast("list[int]", candidates))
    ):
        return f"the candidates are not {MIN_CANDIDATES} to {MAX_CANDIDATES} distinct entity ids"
    return None


def _relation_problem(payload: Mapping[str, object]) -> str | None:
    problem = _end_problem(payload["from"]) or _to_problem(payload["to"], payload["responsibility"])
    if problem is not None:
        return problem
    period = payload["period"]
    if period is not None and _period_of(period) is None:
        return (
            "the period is neither null nor from and to, each null or a date"
            " written YYYY-MM-DD, with from not after to"
        )
    problem = _fields_problem(payload["fields"])
    if problem is not None:
        return problem
    if payload["state"] not in RELATION_STATES:
        return "the state of a relation is neither standing nor retracted"
    return None


def claim_problem(payload: Mapping[str, object]) -> str | None:
    """Why `payload` is not the form of an entity or a relation, or None.
    Checks the form alone, without a vocabulary. Never raises."""
    kind = payload.get("assertion")
    keys = _KEYS.get(kind) if isinstance(kind, str) else None
    if keys is None:
        return "the assertion kind is neither entity nor relation"
    if frozenset(payload) != keys:
        return "the keys of the payload are not those of the assertion kind"
    problem = _author_problem(payload["author"])
    if problem is not None:
        return problem
    if payload["responsibility"] not in LEVELS:
        return "the responsibility is none of direct, transitive, open"
    problem = _evidence_problem(payload) or _scalar_problem(payload) or _level_problem(payload)
    if problem is not None:
        return problem
    return _entity_problem(payload) if kind == ENTITY else _relation_problem(payload)


def _value_of(value: object) -> FieldValue:
    """A field value of a payload that passed `claim_problem`.

    The payload cannot tell a text that is spelled like a date from a date:
    both are the same string. A string of the date form that is a date
    becomes a `date`, and `conformance_problem` takes it for a text field as
    the text it is written as.
    """
    if isinstance(value, dict):
        return cast("Period", _period_of(cast("dict[str, object]", value)))
    if isinstance(value, str):
        day = _date(value)
        return value if day is None else day
    return cast("int", value)


def _fields_of_payload(value: object) -> dict[str, FieldValue]:
    return {name: _value_of(item) for name, item in cast("dict[str, object]", value).items()}


def _source_of(item: object) -> Source:
    entry = cast("dict[str, object]", item)
    units = entry["units"]
    return Source(
        cast("int", entry["event"]),
        None if units is None else tuple(cast("list[int]", units)),
    )


def _body_of(payload: Mapping[str, object]) -> EntityBody | RelationBody:
    kind = cast("str", payload["type"])
    fields = _fields_of_payload(payload["fields"])
    state = cast("str", payload["state"])
    if payload["assertion"] == ENTITY:
        return EntityBody(kind, cast("str | None", payload["language"]), fields, state)
    start = cast("int", cast("dict[str, object]", payload["from"])["entity"])
    to = cast("dict[str, object]", payload["to"])
    candidates = to.get("candidates")
    period = payload["period"]
    return RelationBody(
        kind,
        start,
        cast("int | None", to.get("entity")),
        None if candidates is None else tuple(cast("list[int]", candidates)),
        None if period is None else _period_of(period),
        fields,
        state,
    )


def parse_claim(payload: Mapping[str, object]) -> Claim | None:
    """The claim a payload holds, or None if `claim_problem` finds fault."""
    if claim_problem(payload) is not None:
        return None
    return Claim(
        cast("str", payload["assertion"]),
        cast("str", payload["author"]),
        cast("str", payload["responsibility"]),
        cast("str", payload["evidence"]),
        tuple(_source_of(item) for item in cast("list[object]", payload["sources"])),
        cast("str | None", payload["reason"]),
        cast("str | None", payload["handle"]),
        cast("int | None", payload["subject"]),
        cast("int | None", payload["approves"]),
        cast("int | None", payload["under"]),
        cast("int | None", payload["confidence"]),
        cast("int | None", payload["contests"]),
        _body_of(payload),
    )


# --- Checking against the vocabulary ----------------------------------------------


def _field_problem(
    spec: FieldSpec, value: FieldValue, entity_types: Mapping[int, str] | None
) -> str | None:
    name, kind = spec.name, spec.type
    if kind == TEXT:
        # A date here is a text spelled like one (see `_value_of`).
        fits = isinstance(value, (str, date))
    elif kind == DATE:
        fits = isinstance(value, date)
    elif kind == PERIOD:
        fits = isinstance(value, Period)
    elif kind == CHOICE:
        fits = isinstance(value, str) and value in (spec.values or ())
    else:
        fits = isinstance(value, int) and (
            entity_types is None or entity_types.get(value) == spec.ref
        )
    if fits:
        return None
    return {
        TEXT: f'the field "{name}" is not a text',
        DATE: f'the field "{name}" is not a date written YYYY-MM-DD',
        PERIOD: f'the field "{name}" is not a period',
        CHOICE: f'the field "{name}" holds none of the values its kind allows',
    }.get(kind, f'the field "{name}" names no standing entity of the kind it refers to')


def _fields_conformance(
    spec: KindSpec, fields: Mapping[str, FieldValue], entity_types: Mapping[int, str] | None
) -> str | None:
    """`entity_types` None leaves the entities a `ref` names unlooked-up."""
    declared = {item.name: item for item in spec.fields}
    for name, value in fields.items():
        item = declared.get(name)
        if item is None:
            return "a field is not declared for its kind"
        problem = _field_problem(item, value, entity_types)
        if problem is not None:
            return problem
    for item in spec.fields:
        if item.required and item.name not in fields:
            return f'the field "{item.name}" is required'
    return None


def _ends_conformance(
    spec: KindSpec, body: RelationBody, entity_types: Mapping[int, str]
) -> str | None:
    # One sentence for an entity that does not stand and one the caller may
    # not see: a caller passes only the entities it may show, and the
    # sentence must not tell the two apart.
    ends = [body.start, *([body.to] if body.to is not None else body.candidates or ())]
    if any(end not in entity_types for end in ends):
        return "an end of the relation is not an entity that stands"
    if entity_types[body.start] not in (spec.from_ or ()):
        return "the start of the relation is of a kind its relation kind does not start from"
    if any(entity_types[end] not in (spec.to or ()) for end in ends[1:]):
        return "the end of the relation is of a kind its relation kind does not point at"
    return None


def conformance_problem(
    claim: Claim, vocabulary: Vocabulary, *, new_thread: bool, entity_types: Mapping[int, str]
) -> str | None:
    """Why `claim` does not fit `vocabulary`, or None.

    `new_thread` says whether the claim starts a new entity or relation; a
    retired kind takes none, while a further version of an existing one may
    close, retract or rename it. `entity_types` gives the kind of each entity
    that stands and that the caller may name, by id: the ends of a relation
    and every `ref` field are looked up there. A retracted version asserts
    nothing about what it names, so its ends and refs are not looked up.
    """
    body = claim.body
    spec = vocabulary.kind(claim.kind, body.type)
    if spec is None:
        return f"the type is not declared as a kind of {claim.kind} in the vocabulary"
    if spec.retired and new_thread:
        return f"the kind is retired and takes no new {claim.kind}"
    # The gate reads circles and memberships, and a class must never decide
    # what the gate lets through: a mistake there hands a customer's mails to
    # a model. So these kinds are direct or open, never transitive.
    if body.type in GATE_TYPES and claim.responsibility == TRANSITIVE:
        return "a kind the gate reads is never transitive"
    retracted = body.state == RETRACTED
    problem = _fields_conformance(spec, body.fields, None if retracted else entity_types)
    if problem is not None:
        return problem
    if isinstance(body, EntityBody):
        if body.state == CLOSED and CLOSABLE not in spec.behaviors:
            return "the state closed needs a kind with the behavior closable"
        return None
    if body.period is not None and PERIOD_BEHAVIOR not in spec.behaviors:
        return "a period needs a relation kind with the behavior period"
    return None if retracted else _ends_conformance(spec, body, entity_types)


# --- Folding versions -------------------------------------------------------------


@dataclass(frozen=True)
class ClassState:
    """What the fold needs of an approval class: the event id that set it
    and whether it is revoked, and if so with `demote`. Filled from the log
    by core/classes.py."""

    id: int
    revoked: bool
    demote: bool


@dataclass(frozen=True)
class GraphVersion:
    id: int
    recorded_at: datetime
    claim: Claim


def level_of(version: GraphVersion, classes: Mapping[int, ClassState]) -> str:
    """The level a version counts at under `classes`: its own, except that a
    transitive version whose class was revoked with `demote`, or whose class
    `classes` does not know, counts as open. Revoked without `demote`, it
    stays transitive, and a caller marks it."""
    claim = version.claim
    if claim.responsibility != TRANSITIVE:
        return claim.responsibility
    state = classes.get(cast("int", claim.under))
    if state is None or (state.revoked and state.demote):
        return OPEN
    return TRANSITIVE


@dataclass(frozen=True)
class GraphThread:
    """All standing versions of one entity or relation, in chain order."""

    subject: int
    kind: str
    versions: tuple[GraphVersion, ...]
    rejected: frozenset[int] = field(default_factory=frozenset[int])
    approved: frozenset[int] = field(default_factory=frozenset[int])

    def _unanswered(self, level: str, classes: Mapping[int, ClassState]) -> list[GraphVersion]:
        return [
            version
            for version in self.versions
            if level_of(version, classes) == level
            and version.id not in self.rejected
            and version.id not in self.approved
        ]

    def _anchor(self, classes: Mapping[int, ClassState]) -> GraphVersion | None:
        """The latest version the operator stands for: direct, else
        transitive and unanswered."""
        direct = [v for v in self.versions if v.claim.responsibility == DIRECT]
        if direct:
            return direct[-1]
        transitive = self._unanswered(TRANSITIVE, classes)
        return transitive[-1] if transitive else None

    def winner(self, classes: Mapping[int, ClassState]) -> GraphVersion | None:
        """The latest direct version, else the latest transitive one that
        counts as transitive and is neither rejected nor approved, else the
        latest open one that is neither (then it stands as a proposal)."""
        anchor = self._anchor(classes)
        if anchor is not None:
            return anchor
        candidates = self._unanswered(OPEN, classes)
        return candidates[-1] if candidates else None

    def _waiting(self, classes: Mapping[int, ClassState]) -> list[GraphVersion]:
        """Unanswered versions that are not direct and not overtaken: newer
        than the anchor, or all open ones when there is none. The winner is
        among them when it is a proposal."""
        anchor = self._anchor(classes)
        if anchor is None:
            return self._unanswered(OPEN, classes)
        later = self.versions[self.versions.index(anchor) + 1 :]
        return [
            v
            for v in later
            if level_of(v, classes) != DIRECT
            and v.id not in self.rejected
            and v.id not in self.approved
        ]

    def pending(self, classes: Mapping[int, ClassState]) -> tuple[GraphVersion, ...]:
        """Versions that are neither rejected nor approved and wait for the
        operator: those newer than the version he stands for, or, with none,
        every open one except the latest, which stands as the proposal. The
        winner is never in the list."""
        winner = self.winner(classes)
        return tuple(v for v in self._waiting(classes) if v != winner)

    def objections(self, classes: Mapping[int, ClassState]) -> tuple[GraphVersion, ...]:
        """Pending versions that contest the current direct winner. One that
        contests an older direct version is a proposal like any other: what
        it contested no longer stands."""
        winner = self.winner(classes)
        if winner is None or winner.claim.responsibility != DIRECT:
            return ()
        return tuple(v for v in self.pending(classes) if v.claim.contests == winner.id)

    def question(self, classes: Mapping[int, ClassState]) -> GraphVersion | None:
        """The newest unanswered open relation version that names candidates
        and is not overtaken, whether it stands as the proposal or waits
        behind one. A later direct version answers it."""
        asking = [
            v
            for v in self._waiting(classes)
            if isinstance(v.claim.body, RelationBody) and v.claim.body.candidates is not None
        ]
        return asking[-1] if asking else None


@dataclass(frozen=True)
class Graph:
    threads: Mapping[int, GraphThread]
    classes: Mapping[int, ClassState]

    def _winners(self, kind: str) -> dict[int, GraphVersion]:
        winners: dict[int, GraphVersion] = {}
        for subject, thread in self.threads.items():
            winner = thread.winner(self.classes) if thread.kind == kind else None
            if winner is not None:
                winners[subject] = winner
        return winners

    def entities(self) -> Mapping[int, GraphVersion]:
        """The winner of each entity, by id, unless it is retracted."""
        return {
            subject: version
            for subject, version in self._winners(ENTITY).items()
            if version.claim.body.state != RETRACTED
        }

    def relations(self, *, at: date | None = None) -> Mapping[int, GraphVersion]:
        """The winner of each relation, by id, if it stands, points at an
        entity, and, with `at`, its period holds on that day. A question is
        no relation yet, and a relation without a period holds on every day."""
        found: dict[int, GraphVersion] = {}
        for subject, version in self._winners(RELATION).items():
            body = cast("RelationBody", version.claim.body)
            if body.state != STANDING or body.to is None:
                continue
            if at is not None and body.period is not None and not body.period.holds(at):
                continue
            found[subject] = version
        return found

    def reaches(
        self,
        start: int,
        end: int,
        types: frozenset[str],
        *,
        extra: Iterable[tuple[int, int]] = (),
        without: frozenset[int] = frozenset(),
    ) -> bool:
        """Whether a path of at least one edge leads from entity `start` to
        entity `end` over relations of `types`, whatever their periods.

        `extra` adds edges a batch is about to write, and `without` leaves out
        the relations, by id, whose current edge the batch replaces. A path
        from an entity back to itself is a cycle, an edge to itself included.
        """
        edges: dict[int, set[int]] = {}
        for subject, version in self.relations().items():
            body = cast("RelationBody", version.claim.body)
            if subject in without or body.type not in types:
                continue
            edges.setdefault(body.start, set()).add(cast("int", body.to))
        for origin, target in extra:
            edges.setdefault(origin, set()).add(target)
        seen: set[int] = set()
        frontier = [start]
        while frontier:
            for target in edges.get(frontier.pop(), ()):
                if target == end:
                    return True
                if target not in seen:
                    seen.add(target)
                    frontier.append(target)
        return False


@dataclass
class _Draft:
    kind: str
    versions: list[GraphVersion] = field(default_factory=lambda: [])
    rejected: set[int] = field(default_factory=lambda: set[int]())
    approved: set[int] = field(default_factory=lambda: set[int]())

    def version(self, version_id: int) -> GraphVersion | None:
        return next((v for v in self.versions if v.id == version_id), None)


def _approvable(draft: _Draft, approves: int, erased: set[int]) -> bool:
    """Whether an approval of `approves` joins the thread: the version is not
    answered yet, and it is an open or transitive version of the thread, or
    erased, as with an obligation."""
    if approves in draft.approved or approves in draft.rejected:
        return False
    if approves in erased:
        return True
    proposal = draft.version(approves)
    return proposal is not None and proposal.claim.responsibility in (OPEN, TRANSITIVE)


def _contestable(draft: _Draft, contests: int, erased: set[int]) -> bool:
    """Whether `contests` names a direct version of the thread, or an erased
    one; an objection against an erased version is a proposal like any other."""
    if contests in erased:
        return True
    target = draft.version(contests)
    return target is not None and target.claim.responsibility == DIRECT


def _reject(
    payload: Mapping[str, object], drafts: dict[int, _Draft], thread_of: dict[int, int]
) -> None:
    statement = parse_statement(payload)
    if statement is None or statement.of is None:
        return
    target = thread_of.get(statement.of)
    if target is not None:
        drafts[target].rejected.add(statement.of)


def fold_graph(
    rows: Iterable[tuple[int, datetime, Mapping[str, object] | None]],
    classes: Mapping[int, ClassState],
) -> Graph:
    """The graph standing in `rows`, which are given in chain order.

    Erased rows (payload None), rows that are no entity or relation, and rows
    with a form fault are skipped, and so is a version whose `subject` names
    nothing, whose kind is not that of its thread, whose `approves` names no
    unanswered open or transitive version, or whose `contests` names no
    direct version of its thread. A rejection, parsed with
    `core.assertion.parse_statement`, counts when its `of` names a standing
    version of the graph; it is ignored otherwise, since it may reject an
    obligation or a decision. Approvals and objections that name an erased
    version stand, as with an obligation.
    """
    drafts: dict[int, _Draft] = {}
    thread_of: dict[int, int] = {}  # standing version id -> subject of its thread
    erased: set[int] = set()
    for row_id, recorded_at, payload in rows:
        if payload is None:
            erased.add(row_id)
            continue
        if payload.get("assertion") == REJECTION:
            _reject(payload, drafts, thread_of)
            continue
        claim = parse_claim(payload) if payload.get("assertion") in GRAPH_KINDS else None
        if claim is None:
            continue
        subject = row_id if claim.subject is None else claim.subject
        if claim.subject is not None and subject not in drafts and subject not in erased:
            continue  # names nothing: not a first version, not an erased one
        draft = drafts.get(subject) or _Draft(claim.kind)  # kept only once a version joins
        if draft.kind != claim.kind:
            continue
        if claim.contests is not None and not _contestable(draft, claim.contests, erased):
            continue
        if claim.approves is not None:
            if not _approvable(draft, claim.approves, erased):
                continue
            draft.approved.add(claim.approves)
        draft.versions.append(GraphVersion(row_id, recorded_at, claim))
        drafts[subject] = draft
        thread_of[row_id] = subject
    threads = {
        subject: GraphThread(
            subject,
            draft.kind,
            tuple(draft.versions),
            frozenset(draft.rejected),
            frozenset(draft.approved),
        )
        for subject, draft in drafts.items()
    }
    return Graph(threads, classes)


# --- Reading ----------------------------------------------------------------------

_NONE: Final = "(none)"
_OPEN_END: Final = "(open)"


def _period_text(period: Period | None) -> str:
    if period is None:
        return _NONE
    start = _OPEN_END if period.start is None else period.start.isoformat()
    end = _OPEN_END if period.end is None else period.end.isoformat()
    return f"{start} to {end}"


def _value_text(value: FieldValue) -> str:
    if isinstance(value, Period):
        return _period_text(value)
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _sources_text(sources: tuple[Source, ...]) -> str:
    def one(source: Source) -> str:
        if source.units is None:
            return f"event {source.event}"
        return f"event {source.event} units {', '.join(str(seq) for seq in source.units)}"

    return "; ".join(one(source) for source in sources) or _NONE


def _texts_of(claim: Claim) -> dict[str, str]:
    body = claim.body
    texts: dict[str, str] = {"type": body.type}
    if isinstance(body, EntityBody):
        texts["language"] = _NONE if body.language is None else body.language
    else:
        texts["from"] = f"entity {body.start}"
        if body.candidates is not None:
            texts["to"] = "candidates " + ", ".join(str(item) for item in body.candidates)
        else:
            texts["to"] = f"entity {body.to}"
        texts["period"] = _period_text(body.period)
    for name in sorted(body.fields):
        texts[f"fields.{name}"] = _value_text(body.fields[name])
    texts["state"] = body.state
    texts["evidence"] = claim.evidence
    texts["sources"] = _sources_text(claim.sources)
    texts["reason"] = _NONE if claim.reason is None else claim.reason
    return texts


def claim_changes(before: Claim, after: Claim) -> tuple[tuple[str, str, str], ...]:
    """The fields that differ, as `(field, before, after)`: the type, the
    body with each field as `fields.<name>`, the evidence, the sources and the
    reason. Computed when read, never stored."""
    old, new = _texts_of(before), _texts_of(after)
    names = [*old, *(name for name in new if name not in old)]
    return tuple(
        (name, old.get(name, _NONE), new.get(name, _NONE))
        for name in names
        if old.get(name) != new.get(name)
    )
