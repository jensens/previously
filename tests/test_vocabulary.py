# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The vocabulary: the form of its events, the fold at a moment, the built-in
kinds, the file and the write path."""

from copy import deepcopy
from dataclasses import replace
from datetime import datetime
from datetime import timedelta
from datetime import UTC
from previously.core.action import append_action
from previously.core.action import KNOWN_ACTIONS
from previously.core.redact import redact_event
from previously.core.verify import Finding
from previously.core.verify import verify
from previously.core.vocabulary import apply_vocabulary
from previously.core.vocabulary import base_vocabulary
from previously.core.vocabulary import BUILT_IN
from previously.core.vocabulary import differences
from previously.core.vocabulary import differing_kinds
from previously.core.vocabulary import FieldSpec
from previously.core.vocabulary import GATE_TYPES
from previously.core.vocabulary import KindSpec
from previously.core.vocabulary import missing_kinds
from previously.core.vocabulary import parse_file
from previously.core.vocabulary import read_vocabulary
from previously.core.vocabulary import render_file
from previously.core.vocabulary import to_payload
from previously.core.vocabulary import Vocabulary
from previously.core.vocabulary import vocabulary_problem
from previously.core.vocabulary import VocabularyFold
from previously.core.vocabulary import VocabularyRefused
from previously.storage.postgres import PostgresStorage
from typing import cast
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from collections.abc import Callable
    from sqlalchemy import Engine


T0 = datetime(2026, 10, 14, 12, 0, 0, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)
T2 = T0 + timedelta(hours=2)

NAME = FieldSpec("name", "text", None, None, True)
PERIOD_FIELD = FieldSpec("period", "period", None, None, False)

TEAM = KindSpec(
    "entity",
    "team",
    {"de": "Team", "en": "Team"},
    (
        NAME,
        PERIOD_FIELD,
        FieldSpec("day", "date", None, None, False),
        FieldSpec("size", "choice", ("small", "large"), None, False),
        FieldSpec("lead", "ref", None, "team", False),
    ),
    frozenset({"closable", "period"}),
    None,
    None,
    False,
)
WORKS_FOR = KindSpec(
    "relation",
    "works_for",
    {"en": "Works for"},
    (FieldSpec("role", "text", None, None, False),),
    frozenset({"transitive", "acyclic", "period"}),
    ("team",),
    ("team",),
    False,
)


def _kind(
    declares: str,
    name: str,
    *,
    fields: tuple[FieldSpec, ...] = (),
    behaviors: frozenset[str] = frozenset(),
    ends: tuple[tuple[str, ...], tuple[str, ...]] | None = None,
    labels: dict[str, str] | None = None,
) -> KindSpec:
    from_, to = (None, None) if ends is None else ends
    return KindSpec(declares, name, labels or {"en": name}, fields, behaviors, from_, to, False)


def _vocabulary_of(*specs: KindSpec) -> Vocabulary:
    return Vocabulary({(spec.declares, spec.name): spec for spec in specs}, {})


def _payload(spec: KindSpec = TEAM) -> dict[str, object]:
    return to_payload(spec, statement="s")


def _vocabulary(storage: PostgresStorage, *, at: datetime | None = None) -> Vocabulary:
    with storage.begin() as conn:
        return read_vocabulary(storage, conn, at=at)


def _count(storage: PostgresStorage) -> int:
    with storage.begin() as conn:
        return len(list(storage.read_by_kind(conn, "action")))


# --- The form ---------------------------------------------------------------------


@pytest.mark.parametrize("spec", [TEAM, WORKS_FOR], ids=["entity", "relation"])
def test_every_form_has_the_form_the_check_accepts(spec: KindSpec) -> None:
    assert vocabulary_problem(_payload(spec)) is None


def _set(key: str, value: object) -> Callable[[dict[str, object]], None]:
    def change(payload: dict[str, object]) -> None:
        payload[key] = value

    return change


def _field(index: int, key: str, value: object) -> Callable[[dict[str, object]], None]:
    def change(payload: dict[str, object]) -> None:
        fields = cast("list[dict[str, object]]", payload["fields"])
        fields[index][key] = value

    return change


def _fields(
    make: Callable[[list[dict[str, object]]], list[dict[str, object]]],
) -> Callable[[dict[str, object]], None]:
    def change(payload: dict[str, object]) -> None:
        payload["fields"] = make(cast("list[dict[str, object]]", payload["fields"]))

    return change


def _drop(key: str) -> Callable[[dict[str, object]], None]:
    def change(payload: dict[str, object]) -> None:
        del payload[key]

    return change


FORM_ERRORS = [
    ("an identifier with a capital", _set("name", "Team"), "no identifier"),
    ("an identifier that starts with a digit", _set("name", "1team"), "no identifier"),
    ("an identifier that is too long", _set("name", "a" * 41), "no identifier"),
    ("an empty label", _set("labels", {"en": ""}), "no text of 1 to 80 characters"),
    ("a label with a control character", _set("labels", {"en": "a\nb"}), "no text of 1 to 80"),
    ("a label of 81 characters", _set("labels", {"en": "a" * 81}), "no text of 1 to 80"),
    ("no label", _set("labels", {}), "no label in any language"),
    ("a language that is no tag", _set("labels", {"English": "Team"}), "no language tag"),
    ("a choice without values", _field(3, "values", None), "values exactly when it is a choice"),
    ("values on a text", _field(0, "values", ["a"]), "values exactly when it is a choice"),
    ("a choice with an empty list", _field(3, "values", []), "not 1 to 50 distinct"),
    ("a choice with a repeated value", _field(3, "values", ["a", "a"]), "not 1 to 50 distinct"),
    ("a ref without a kind", _field(4, "ref", None), "a ref exactly when it is a ref"),
    ("a text with a ref", _field(0, "ref", "team"), "a ref exactly when it is a ref"),
    ("an unknown field type", _field(0, "type", "number"), "unknown type"),
    ("a required that is no flag", _field(0, "required", "yes"), "true or false"),
    ("an unknown behavior", _set("behaviors", ["closable", "shiny"]), "the behavior 'shiny'"),
    (
        "a relation behavior on an entity",
        _set("behaviors", ["transitive"]),
        "the behavior 'transitive'",
    ),
    ("an entity with from", _set("from", ["team"]), "from and to exactly when it is a relation"),
    ("no statement", _set("statement", ""), 'no "statement"'),
    ("a key too many", _set("colour", "red"), "has the keys"),
    ("a key too few", _drop("retired"), "has the keys"),
    ("an unknown declares", _set("declares", "thing"), "neither an entity nor a relation"),
    ("a field list that is no list", _set("fields", "name"), 'no list "fields"'),
    ("a field that is no table", _set("fields", ["name"]), 'no table "fields"'),
    ("two fields of one name", _fields(lambda fields: [fields[0], fields[0]]), "two fields"),
    ("no field name", _field(0, "name", "Name"), "no identifier"),
    ("a period behavior without the field", _fields(lambda fields: fields[:1]), "no field"),
    ("an entity without a name", _fields(lambda fields: fields[1:]), "no required text field"),
    ("a name that is not required", _field(0, "required", False), "no required text field"),
    ("a name that is not text", _field(0, "type", "date"), "no required text field"),
    ("a field with a key too many", _field(0, "colour", "red"), "has a field with the keys"),
    ("a period field of another type", _field(1, "type", "text"), "which is the period"),
]


@pytest.mark.parametrize(
    ("change", "problem"), [case[1:] for case in FORM_ERRORS], ids=[c[0] for c in FORM_ERRORS]
)
def test_a_broken_form_is_named_with_a_sentence(
    change: Callable[[dict[str, object]], None], problem: str
) -> None:
    payload = deepcopy(_payload())
    change(payload)
    assert (found := vocabulary_problem(payload)) is not None
    assert found.startswith("has no valid form: it ")
    assert problem in found


def test_a_relation_has_no_field_period_because_it_has_a_period() -> None:
    """`period` is the period of the relation itself, so a field of that name
    would say it twice. The control is the same relation without it."""
    payload = _payload(WORKS_FOR)
    assert vocabulary_problem(payload) is None
    cast("list[dict[str, object]]", payload["fields"]).append(
        {"name": "period", "type": "period", "values": None, "ref": None, "required": False}
    )
    assert "which is the period" in str(vocabulary_problem(payload))


def test_a_relation_has_from_and_to_and_an_entity_has_neither() -> None:
    payload = _payload(WORKS_FOR)
    payload["to"] = None
    assert "from and to exactly when it is a relation" in str(vocabulary_problem(payload))
    assert vocabulary_problem(_payload(WORKS_FOR)) is None


def test_the_check_never_raises_on_a_payload_of_the_wrong_shape() -> None:
    payload = _payload()
    for key in ("labels", "fields", "behaviors", "name", "declares", "retired", "statement"):
        wrongs: list[object] = [None, 3, [], {}, "x", [1], [[]], {"a": 1}]
        for wrong in wrongs:
            result = vocabulary_problem({**payload, key: wrong})
            assert result is None or isinstance(result, str)
    assert vocabulary_problem({}) is not None
    assert vocabulary_problem({**payload, "action": "policy"}) is not None


# --- The file ---------------------------------------------------------------------


def _file(*, extra: str = "", behaviors: str = 'behaviors = ["closable"]') -> str:
    return f"""
[entity.team]
labels = {{ en = "Team" }}
{behaviors}
fields = [{{ name = "name", type = "text", required = true }}]
{extra}
"""


def test_a_file_is_read_into_specs() -> None:
    (spec,) = parse_file(_file())
    assert spec == KindSpec(
        "entity", "team", {"en": "Team"}, (NAME,), frozenset({"closable"}), None, None, False
    )


@pytest.mark.parametrize(
    ("text", "sentence"),
    [
        (_file(behaviors='behaviours = ["closable"]'), "unknown key 'behaviours'"),
        (_file(extra='colour = "red"'), "unknown key 'colour'"),
        ("[thing.team]\nlabels = {}", "unknown table 'thing'"),
        (_file(behaviors='behaviors = ["shiny"]'), "the behavior 'shiny'"),
        ("[entity.team]\nfields = []", "has no labels"),
        ("[entity.Team]\nlabels = { en = 'T' }", "no identifier"),
        ("[entity.team]\nlabels = 3", 'no table "labels"'),
        ("entity = 3", "the vocabulary file has no table"),
        ("[entity", "is no TOML"),
    ],
    ids=[
        "misspelled-key",
        "unknown-key",
        "unknown-table",
        "unknown-behavior",
        "no-labels",
        "capital",
        "labels-no-table",
        "entity-no-table",
        "not-toml",
    ],
)
def test_a_file_with_a_fault_is_refused_with_a_sentence(text: str, sentence: str) -> None:
    with pytest.raises(VocabularyRefused) as raised:
        parse_file(text)
    assert sentence in str(raised.value)


def test_a_file_that_gives_an_entity_connections_is_refused() -> None:
    with pytest.raises(VocabularyRefused, match="from and to exactly when it is a relation"):
        parse_file(_file(extra='from = ["team"]'))


def test_the_rendered_file_reads_back_to_the_same_specs() -> None:
    specs = (TEAM, WORKS_FOR)
    assert parse_file(render_file(_vocabulary_of(*specs))) == specs
    retired = KindSpec("entity", "old", {"en": "Old"}, (NAME,), frozenset(), None, None, True)
    assert parse_file(render_file(_vocabulary_of(retired))) == (retired,)


# --- The shipped vocabulary -------------------------------------------------------


def test_the_base_vocabulary_has_the_form_of_every_event() -> None:
    specs = parse_file(base_vocabulary())
    assert {(s.declares, s.name) for s in specs} >= BUILT_IN
    assert len(specs) == 9 + len(BUILT_IN)
    for spec in specs:
        assert vocabulary_problem(to_payload(spec, statement="s")) is None
        assert set(spec.labels) == {"de", "en"}


def test_the_base_vocabulary_is_its_own_canonical_rendering() -> None:
    """What `show` prints after `apply --base` is the shipped file, so it has
    to be written the way `render_file` writes it."""
    assert render_file(_vocabulary_of(*parse_file(base_vocabulary()))) == base_vocabulary()


def test_the_base_vocabulary_leaves_concerns_for_the_phase_that_starts_at_an_event() -> None:
    declared = {(s.declares, s.name) for s in parse_file(base_vocabulary())}
    assert ("relation", "concerns") not in declared


# --- The label --------------------------------------------------------------------


def test_a_label_falls_back_to_the_first_language_there_is_and_says_which() -> None:
    both = _vocabulary_of(TEAM)
    assert both.label("entity", "team", "de") == ("Team", None)
    only_english = _vocabulary_of(WORKS_FOR)
    assert only_english.label("relation", "works_for", "en") == ("Works for", None)
    assert only_english.label("relation", "works_for", "de") == ("Works for", "en")
    many = _kind("entity", "x", fields=(NAME,), labels={"fr": "X", "de": "Y"})
    assert _vocabulary_of(many).label("entity", "x", "it") == ("Y", "de")
    assert both.label("entity", "nothing", "en") == ("nothing", None)


# --- Differences ------------------------------------------------------------------


def test_the_differences_are_what_changes_and_what_the_file_leaves_out() -> None:
    current = _vocabulary_of(TEAM, WORKS_FOR)
    assert differences(current, (TEAM, WORKS_FOR)) == ()
    crew = replace(TEAM, labels={"en": "Crew"})
    assert differences(current, (crew, WORKS_FOR)) == (crew,)
    (gone,) = differences(current, (TEAM,))
    assert (gone.name, gone.retired) == ("works_for", True)
    assert differences(current, (TEAM, WORKS_FOR, gone)) == (gone,)


def test_the_differences_write_entities_before_relations() -> None:
    assert [s.name for s in differences(_vocabulary_of(), (WORKS_FOR, TEAM))] == [
        "team",
        "works_for",
    ]


def test_a_built_in_kind_the_file_leaves_out_stays() -> None:
    current = _vocabulary_of(*parse_file(base_vocabulary()))
    left_out = {s.name for s in differences(current, ())}
    assert left_out
    assert not left_out & GATE_TYPES


# --- The fold ---------------------------------------------------------------------


@pytest.mark.db
def test_the_base_vocabulary_is_applied_and_shown_as_the_same_file(db: Engine) -> None:
    storage = PostgresStorage(db)
    ids = apply_vocabulary(storage, parse_file(base_vocabulary()), recorded_at=T0)
    assert len(ids) == 9
    assert render_file(_vocabulary(storage)) == base_vocabulary()


@pytest.mark.db
def test_a_second_apply_of_the_same_file_writes_nothing(db: Engine) -> None:
    """The control for the mutation that makes `apply` write what did not
    change: the first apply writes, the second does not."""
    storage = PostgresStorage(db)
    specs = parse_file(base_vocabulary())
    assert apply_vocabulary(storage, specs, recorded_at=T0)
    written = _count(storage)
    assert apply_vocabulary(storage, specs, recorded_at=T1) == ()
    assert _count(storage) == written


@pytest.mark.db
def test_only_the_kind_that_changed_is_written(db: Engine) -> None:
    storage = PostgresStorage(db)
    specs = parse_file(base_vocabulary())
    apply_vocabulary(storage, specs, recorded_at=T0)
    wanted = [
        replace(s, labels={**s.labels, "fr": "Projet"}) if s.name == "project" else s for s in specs
    ]
    (event,) = apply_vocabulary(storage, wanted, recorded_at=T1)
    assert _vocabulary(storage).ids[("entity", "project")] == event
    assert _vocabulary(storage).label("entity", "project", "fr") == ("Projet", None)


def _adapted_log(storage: PostgresStorage) -> tuple[KindSpec, ...]:
    """A log as an operator leaves it: the base vocabulary without `post`
    and the two relations that need it (as if they came with an update),
    `project` with a label of the operator's own, and a kind of their own,
    `team`. Returns the base."""
    base = parse_file(base_vocabulary())
    needs_post = {"post", "holds", "post_in"}
    adapted = [
        replace(s, labels={**s.labels, "en": "Undertaking"}) if s.name == "project" else s
        for s in base
        if s.name not in needs_post
    ]
    apply_vocabulary(storage, (*adapted, TEAM), recorded_at=T0)
    return base


@pytest.mark.db
def test_adding_the_base_writes_only_the_kinds_the_log_does_not_hold(db: Engine) -> None:
    """The base after an update retires nothing and changes nothing the
    operator made: `team` stays, `project` keeps its label, and only the
    three kinds the log lacks are written. Measured red with `add_only`
    falling back to `differences`; the control below stays green then."""
    storage = PostgresStorage(db)
    base = _adapted_log(storage)
    before = _vocabulary(storage)
    assert [s.name for s in missing_kinds(before, base)] == ["post", "holds", "post_in"]
    assert [s.name for s in differing_kinds(before, base)] == ["project"]
    ids = apply_vocabulary(storage, base, recorded_at=T1, add_only=True)
    after = _vocabulary(storage)
    assert len(ids) == 3
    assert after.kind("entity", "team") == TEAM
    assert after.label("entity", "project", "en") == ("Undertaking", None)
    assert {key for key, event in after.ids.items() if event in ids} == {
        ("entity", "post"),
        ("relation", "holds"),
        ("relation", "post_in"),
    }
    assert apply_vocabulary(storage, base, recorded_at=T2, add_only=True) == ()


@pytest.mark.db
def test_adding_the_base_keeps_a_kind_the_operator_retired(db: Engine) -> None:
    """A retired kind is one the log holds: the base does not lift it."""
    storage = PostgresStorage(db)
    base = parse_file(base_vocabulary())
    apply_vocabulary(storage, base, recorded_at=T0)
    apply_vocabulary(storage, [s for s in base if s.name != "post_in"], recorded_at=T1)
    assert apply_vocabulary(storage, base, recorded_at=T2, add_only=True) == ()
    kept = _vocabulary(storage).kind("relation", "post_in")
    assert kept is not None
    assert kept.retired


@pytest.mark.db
def test_applying_the_base_as_a_whole_file_still_retires_and_changes(db: Engine) -> None:
    """The control: without `add_only` the same base is the whole
    vocabulary, so `team` is retired and `project` takes the base label."""
    storage = PostgresStorage(db)
    base = _adapted_log(storage)
    apply_vocabulary(storage, base, recorded_at=T1)
    after = _vocabulary(storage)
    team = after.kind("entity", "team")
    assert team is not None
    assert team.retired
    assert after.label("entity", "project", "en") == ("Project", None)


@pytest.mark.db
def test_the_vocabulary_of_a_moment_is_the_log_up_to_it(db: Engine) -> None:
    storage = PostgresStorage(db)
    apply_vocabulary(storage, (TEAM,), recorded_at=T1)
    apply_vocabulary(storage, (replace(TEAM, labels={"en": "Crew"}),), recorded_at=T2)
    assert _vocabulary(storage, at=T0).kind("entity", "team") is None
    assert _vocabulary(storage, at=T1).label("entity", "team", "en") == ("Team", None)
    assert _vocabulary(storage, at=T2).label("entity", "team", "en") == ("Crew", None)
    assert _vocabulary(storage).label("entity", "team", "en") == ("Crew", None)


@pytest.mark.db
def test_a_kind_the_file_leaves_out_is_retired_and_stays_readable(db: Engine) -> None:
    storage = PostgresStorage(db)
    apply_vocabulary(storage, (TEAM,), recorded_at=T0)
    (event,) = apply_vocabulary(storage, (), recorded_at=T1)
    retired = _vocabulary(storage).kind("entity", "team")
    assert retired is not None
    assert retired.retired
    assert retired.labels == TEAM.labels
    assert _vocabulary(storage).ids[("entity", "team")] == event
    assert _vocabulary(storage, at=T0).kind("entity", "team") == TEAM
    # Leaving it out again changes nothing, and declaring it again lifts it.
    assert apply_vocabulary(storage, (), recorded_at=T1) == ()
    apply_vocabulary(storage, (TEAM,), recorded_at=T2)
    assert _vocabulary(storage).kind("entity", "team") == TEAM


@pytest.mark.db
def test_an_erased_event_counts_as_nothing(db: Engine) -> None:
    """The control is the vocabulary before the erasure."""
    storage = PostgresStorage(db)
    apply_vocabulary(storage, (TEAM,), recorded_at=T0)
    (event,) = apply_vocabulary(storage, (replace(TEAM, labels={"en": "Crew"}),), recorded_at=T1)
    assert _vocabulary(storage).label("entity", "team", "en") == ("Crew", None)
    redact_event(storage, storage, event, reason="test", recorded_at=T2)
    assert _vocabulary(storage).kind("entity", "team") == TEAM


@pytest.mark.db
def test_an_event_of_a_broken_form_counts_as_nothing(db: Engine) -> None:
    storage = PostgresStorage(db)
    apply_vocabulary(storage, (TEAM,), recorded_at=T0)
    broken = _payload()
    broken["name"] = "Broken"
    broken["labels"] = {}
    append_action(storage, broken, (), recorded_at=T1)
    assert _vocabulary(storage).kind("entity", "team") == TEAM
    assert _vocabulary(storage).kind("entity", "Broken") is None


# --- The built-in kinds -----------------------------------------------------------


@pytest.mark.db
def test_the_built_in_kinds_are_there_without_any_event(db: Engine) -> None:
    vocabulary = _vocabulary(PostgresStorage(db))
    assert set(vocabulary.kinds) == BUILT_IN
    assert vocabulary.ids == {}
    member_of = vocabulary.kind("relation", "member_of")
    assert member_of is not None
    assert member_of.behaviors == {"period"}
    assert member_of.to == ("circle",)
    assert {"circle", "member_of", "in_circle"} == GATE_TYPES


MEMBER_OF = KindSpec(
    "relation",
    "member_of",
    {"en": "Member of"},
    (),
    frozenset({"period"}),
    ("organization", "person"),
    ("circle",),
    False,
)


def _member_of(**changes: object) -> KindSpec:
    return replace(MEMBER_OF, **changes)


@pytest.mark.db
def test_a_built_in_kind_can_have_its_labels_changed(db: Engine) -> None:
    storage = PostgresStorage(db)
    apply_vocabulary(storage, (_member_of(labels={"en": "Belongs to"}),), recorded_at=T0)
    assert _vocabulary(storage).label("relation", "member_of", "en") == ("Belongs to", None)


@pytest.mark.db
@pytest.mark.parametrize(
    "changes",
    [
        {"from_": ("person",)},
        {"from_": ("organization", "person", "post")},
        {"to": ("organization",)},
        {"behaviors": frozenset({"period", "transitive"})},
        {"behaviors": frozenset[str]()},
        {"fields": (FieldSpec("note", "text", None, None, False),)},
        {"retired": True},
    ],
    ids=["from-fewer", "from-more", "to", "behavior-more", "behavior-fewer", "field", "retired"],
)
def test_a_built_in_kind_cannot_be_redeclared(db: Engine, changes: dict[str, object]) -> None:
    """Z section 15 point 2: no declaration changes what the gate reads. The
    control is the same kind with its labels changed, which is written."""
    storage = PostgresStorage(db)
    with pytest.raises(VocabularyRefused, match="built in"):
        apply_vocabulary(storage, (_member_of(**changes),), recorded_at=T0)
    assert _count(storage) == 0
    assert apply_vocabulary(storage, (_member_of(labels={"en": "Belongs"}),), recorded_at=T0)


@pytest.mark.db
def test_an_event_that_came_around_the_write_path_cannot_reshape_a_built_in_kind(
    db: Engine,
) -> None:
    """The write path refuses it, and the fold keeps only the labels of what
    got in anyway, so the kinds of the gate are fixed in both places."""
    storage = PostgresStorage(db)
    odd = _member_of(from_=("post",), to=("post",), behaviors=frozenset[str]())
    append_action(storage, to_payload(odd, statement="s"), (), recorded_at=T0)
    read = _vocabulary(storage).kind("relation", "member_of")
    assert read is not None
    assert (read.from_, read.to, read.behaviors) == (
        ("organization", "person"),
        ("circle",),
        frozenset({"period"}),
    )
    assert read.labels == {"en": "Member of"}


# --- The checks of the write path -------------------------------------------------


def _relation(from_: tuple[str, ...], to: tuple[str, ...]) -> KindSpec:
    return _kind("relation", "r", ends=(from_, to))


def _with_ref(target: str) -> KindSpec:
    field = FieldSpec("x", "ref", None, target, False)
    return _kind("entity", "e", fields=(NAME, field))


@pytest.mark.db
@pytest.mark.parametrize(
    ("spec", "sentence"),
    [
        (_relation(("nothing",), ("circle",)), '"nothing" in from, which is no entity kind'),
        (_relation(("circle",), ("works_for",)), '"works_for" in to'),
        (_relation((), ("circle",)), "needs at least one kind in from and in to"),
        (_with_ref("nothing"), 'the ref of "x"'),
        (_with_ref("member_of"), "which is no entity kind that stands"),
    ],
    ids=["from-unknown", "to-a-relation", "no-from", "ref-unknown", "ref-a-relation"],
)
def test_a_kind_that_names_what_does_not_stand_is_refused(
    db: Engine, spec: KindSpec, sentence: str
) -> None:
    storage = PostgresStorage(db)
    with pytest.raises(VocabularyRefused) as raised:
        apply_vocabulary(storage, (TEAM, WORKS_FOR, spec), recorded_at=T0)
    assert sentence in str(raised.value)
    assert _count(storage) == 0, "one refused kind stops the whole file"


@pytest.mark.db
def test_a_file_may_declare_a_relation_together_with_the_kinds_it_connects(db: Engine) -> None:
    storage = PostgresStorage(db)
    ids = apply_vocabulary(storage, (WORKS_FOR, TEAM), recorded_at=T0)
    assert len(ids) == 2
    assert ids == tuple(sorted(ids)), "entities first, so a reader folds them in order"


@pytest.mark.db
def test_a_kind_another_one_needs_cannot_be_retired(db: Engine) -> None:
    storage = PostgresStorage(db)
    apply_vocabulary(storage, (TEAM, WORKS_FOR), recorded_at=T0)
    with pytest.raises(VocabularyRefused, match='names "team"'):
        apply_vocabulary(storage, (WORKS_FOR,), recorded_at=T1)
    assert apply_vocabulary(storage, (), recorded_at=T1), "both together can go"


# --- verify -----------------------------------------------------------------------


@pytest.mark.db
def test_verify_reports_a_vocabulary_event_of_a_broken_form(db: Engine) -> None:
    """The control is the same event written properly."""
    storage = PostgresStorage(db)
    (good,) = apply_vocabulary(storage, (TEAM,), recorded_at=T0)
    assert verify(storage) == []
    broken = _payload()
    broken["labels"] = {}
    bad = append_action(storage, broken, (), recorded_at=T1)
    assert good == 1
    assert verify(storage) == [
        Finding(bad, "vocabulary event has no valid form: it has no label in any language")
    ]


def test_vocabulary_is_a_known_action() -> None:
    assert "vocabulary" in KNOWN_ACTIONS


def test_the_fold_takes_one_event_at_a_time_and_passes_over_what_is_no_sound_one() -> None:
    """`verify` holds a claim against the vocabulary where it stands, so a
    vocabulary given out earlier stays as it was when more events come."""
    folded = VocabularyFold()
    before = folded.vocabulary()
    folded.add(7, None)
    folded.add(8, {"action": "policy"})
    folded.add(9, {**to_payload(TEAM, statement="add"), "retired": "no"})
    assert folded.vocabulary() is before
    folded.add(10, to_payload(TEAM, statement="add"))
    after = folded.vocabulary()
    assert (before.kind("entity", "team"), after.kind("entity", "team")) == (None, TEAM)
    assert after.ids == {("entity", "team"): 10}
