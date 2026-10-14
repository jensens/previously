# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The vocabulary: which kinds of entities and relations exist, and what a
statement about one may say.

The vocabulary is not a file or a table. It is a sequence of events of the
kind `action` with `payload.action = "vocabulary"`, written by the operator on
the command line, so it sits in the chain and `verify` covers it like any
other action. One event declares one kind, an entity kind or a relation kind,
under a fixed identifier. A newer event with the same `(declares, name)`
replaces the older one, and the vocabulary of a past day is the log read up to
that day: `read_vocabulary(at=…)`. Retiring a kind is such an event with
`retired: true`: the kind takes nothing new, and what was said about it stays
readable.

The file is a detour and the log is the truth. `parse_file` reads the TOML
form, `differences` compares it with the vocabulary in force, and
`apply_vocabulary` writes one event per kind that differs. The base
vocabulary that ships is applied differently: it only adds the kinds the log
does not hold (`missing_kinds`), because an update must not take away what
the operator made of the vocabulary. `render_file` gives
the vocabulary back as a file, in one canonical form, so that what `apply`
wrote is what `show` prints.

Three kinds are built in: the entity kind `circle` and the relation kinds
`member_of` and `in_circle`. Their connections and behaviors stand in this
module, because the gate reads exactly these and nothing a declaration says
may change what the gate decides. A vocabulary event for one of them can set
the labels and nothing else; `apply_vocabulary` refuses the rest, and
`read_vocabulary` takes only the labels out of an event that tries.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import replace
from importlib import resources
from previously.core.action import retrying
from previously.core.action import VOCABULARY
from previously.core.action import write_action
from previously.core.action import write_action_at
from previously.core.errors import PreviouslyError
from typing import cast
from typing import Final
from typing import TYPE_CHECKING

import json
import re
import tomllib


if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime
    from previously.contract.store import LogStore


ENTITY_KIND: Final = "entity"
RELATION_KIND: Final = "relation"
_DECLARES: Final = (ENTITY_KIND, RELATION_KIND)

TEXT: Final = "text"
DATE: Final = "date"
PERIOD: Final = "period"
CHOICE: Final = "choice"
REF: Final = "ref"
_FIELD_TYPES: Final = (TEXT, DATE, PERIOD, CHOICE, REF)

CLOSABLE: Final = "closable"
PERIOD_BEHAVIOR: Final = "period"
TRANSITIVE: Final = "transitive"
ACYCLIC: Final = "acyclic"
_BEHAVIORS: Final = {
    ENTITY_KIND: frozenset({CLOSABLE, PERIOD_BEHAVIOR}),
    RELATION_KIND: frozenset({TRANSITIVE, ACYCLIC, PERIOD_BEHAVIOR}),
}

# The kinds the gate reads, and so the kinds a declaration cannot reshape.
BUILT_IN: Final[frozenset[tuple[str, str]]] = frozenset(
    {(ENTITY_KIND, "circle"), (RELATION_KIND, "member_of"), (RELATION_KIND, "in_circle")}
)
GATE_TYPES: Final[frozenset[str]] = frozenset(name for _declares, name in BUILT_IN)

NAME_FIELD: Final = "name"
PERIOD_FIELD: Final = "period"

_IDENTIFIER = re.compile(r"[a-z][a-z0-9_]{0,39}")
_LANGUAGE = re.compile(r"[a-z]{2,3}(-[A-Za-z0-9]{1,8})*")
_MAX_TEXT = 80
_MAX_VALUES = 50

_KEYS: Final = frozenset(
    {"action", "declares", "name", "labels", "fields", "behaviors", "from", "to", "retired"}
    | {"statement"}
)
_FIELD_KEYS: Final = frozenset({"name", "type", "values", "ref", "required"})
_FILE_KEYS: Final = frozenset({"labels", "fields", "behaviors", "from", "to", "retired"})


@dataclass(frozen=True)
class FieldSpec:
    """One field of an entity kind or of a relation kind."""

    name: str
    type: str
    values: tuple[str, ...] | None
    ref: str | None
    required: bool


@dataclass(frozen=True)
class KindSpec:
    """What the vocabulary says of one kind.

    `from_` and `to` are the kinds of entities a relation may connect, sorted
    so that the same kind has the same spec however it was typed; both are
    `None` for an entity kind.
    """

    declares: str
    name: str
    labels: Mapping[str, str]
    fields: tuple[FieldSpec, ...]
    behaviors: frozenset[str]
    from_: tuple[str, ...] | None
    to: tuple[str, ...] | None
    retired: bool


@dataclass(frozen=True)
class Vocabulary:
    """The vocabulary in force at a moment: every kind that was ever
    declared, retired ones included, and the id of the event that set each.
    A built-in kind that no event has touched has no id."""

    kinds: Mapping[tuple[str, str], KindSpec]
    ids: Mapping[tuple[str, str], int]

    def kind(self, declares: str, name: str) -> KindSpec | None:
        return self.kinds.get((declares, name))

    def label(self, declares: str, name: str, language: str) -> tuple[str, str | None]:
        """The label in `language`, or the first one that exists in the
        alphabetical order of the languages together with its tag, so the
        caller can mark it. A kind nobody declared shows as its identifier."""
        spec = self.kind(declares, name)
        if spec is None or not spec.labels:
            return name, None
        if language in spec.labels:
            return spec.labels[language], None
        fallback = min(spec.labels)
        return spec.labels[fallback], fallback


def is_language_tag(text: str) -> bool:
    """Whether `text` is a language tag as a label and a working language
    spell it: two or three lower-case letters and optional subtags."""
    return _LANGUAGE.fullmatch(text) is not None


def display_label(
    vocabulary: Vocabulary, declares: str, name: str, *, language: str | None, default: str
) -> str:
    """The label of a kind for a person to read: in `language`, the working
    language of the entity, or in `default` where it has none. A label that
    exists in neither stands in the first language in alphabetical order,
    followed by its tag in parentheses, so that nobody takes it for the one
    asked for. A kind nobody declared shows as its identifier.

    Here and not in a command line, because the MCP tools show the same
    labels the same way."""
    text, fallback = vocabulary.label(declares, name, default if language is None else language)
    return text if fallback is None else f"{text} ({fallback})"


class VocabularyRefused(PreviouslyError):
    """The vocabulary event or the file cannot be accepted. The message is
    one sentence that says why; nothing was written."""


class _FormError(Exception):
    """The payload or file has the wrong shape; the message finishes the
    sentence 'it …'."""


def _name_field() -> FieldSpec:
    return FieldSpec(NAME_FIELD, TEXT, None, None, True)


def _built_in(declares: str, name: str) -> KindSpec:
    """The fixed form of a built-in kind, with the labels it ships with."""
    match (declares, name):
        case ("entity", "circle"):
            labels = {"de": "Kreis", "en": "Circle"}
            return KindSpec(
                declares, name, labels, (_name_field(),), frozenset(), None, None, False
            )
        case ("relation", "member_of"):
            # Phase 1 connects persons and organizations to a circle. The
            # addresses and domains the gate reads today come with phase 3
            # ({ref}`vocabulary-reference`).
            labels = {"de": "Mitglied von", "en": "Member of"}
            behaviors = frozenset({PERIOD_BEHAVIOR})
            return KindSpec(
                declares,
                name,
                labels,
                (),
                behaviors,
                ("organization", "person"),
                ("circle",),
                False,
            )
        case _:
            # `in_circle` starts at an event, which is no entity kind, so
            # `from_` is empty until phase 3 gives a relation that start.
            labels = {"de": "Im Kreis", "en": "In circle"}
            return KindSpec(declares, name, labels, (), frozenset(), (), ("circle",), False)


def built_in_kinds() -> tuple[KindSpec, ...]:
    return tuple(_built_in(declares, name) for declares, name in sorted(BUILT_IN))


# --- Form -------------------------------------------------------------------------


def _identifier(value: object, what: str) -> str:
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise _FormError(f"has {what} {value!r}, which is no identifier of the form a-z0-9_")
    return value


def _text(value: object, what: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= _MAX_TEXT or not value.isprintable():
        raise _FormError(f"has {what} {value!r}, which is no text of 1 to {_MAX_TEXT} characters")
    return value


def _flag(value: object, what: str) -> bool:
    if not isinstance(value, bool):
        raise _FormError(f'has no true or false "{what}"')
    return value


def _list(value: object, what: str) -> list[object]:
    if not isinstance(value, list):
        raise _FormError(f'has no list "{what}"')
    return cast("list[object]", value)


def _mapping(value: object, what: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise _FormError(f'has no table "{what}"')
    return cast("dict[str, object]", value)


def _labels(value: object) -> dict[str, str]:
    labels = _mapping(value, "labels")
    if not labels:
        raise _FormError("has no label in any language")
    for language, text in labels.items():
        if _LANGUAGE.fullmatch(language) is None:
            raise _FormError(f"has the language {language!r}, which is no language tag")
        _text(text, f'the label in "{language}"')
    return {language: cast("str", labels[language]) for language in sorted(labels)}


def _identifiers(value: object, what: str) -> tuple[str, ...]:
    items = [_identifier(item, f'a kind in "{what}"') for item in _list(value, what)]
    return tuple(sorted(set(items)))


def _choice_values(value: object) -> tuple[str, ...]:
    items = [_text(item, "a value") for item in _list(value, "values")]
    if not 1 <= len(items) <= _MAX_VALUES or len(set(items)) != len(items):
        raise _FormError(f"has {len(items)} values, which are not 1 to {_MAX_VALUES} distinct ones")
    return tuple(items)


def _field(value: object) -> FieldSpec:
    entry = _mapping(value, "fields")
    if frozenset(entry) != _FIELD_KEYS:
        raise _FormError(f"has a field with the keys {sorted(entry)}, not {sorted(_FIELD_KEYS)}")
    name = _identifier(entry["name"], "a field name")
    kind = entry["type"]
    if kind not in _FIELD_TYPES:
        raise _FormError(f'has the field "{name}" of the unknown type {kind!r}')
    values, ref = entry["values"], entry["ref"]
    if (kind == CHOICE) != (values is not None):
        raise _FormError(f'has the field "{name}" with values exactly when it is a choice')
    if (kind == REF) != (ref is not None):
        raise _FormError(f'has the field "{name}" with a ref exactly when it is a ref')
    return FieldSpec(
        name,
        cast("str", kind),
        None if values is None else _choice_values(values),
        None if ref is None else _identifier(ref, f'the ref of "{name}"'),
        _flag(entry["required"], "required"),
    )


def _behaviors(value: object, declares: str) -> frozenset[str]:
    items = _list(value, "behaviors")
    allowed = _BEHAVIORS[declares]
    for item in items:
        if not isinstance(item, str) or item not in allowed:
            raise _FormError(
                f"has the behavior {item!r}, which a {declares} kind does not have; "
                f"it has {sorted(allowed)}"
            )
    return frozenset(cast("list[str]", items))


def _check_fields(declares: str, fields: tuple[FieldSpec, ...], behaviors: frozenset[str]) -> None:
    names = [field.name for field in fields]
    if len(set(names)) != len(names):
        raise _FormError("has two fields of one name")
    by_name = {field.name: field for field in fields}
    period = by_name.get(PERIOD_FIELD)
    if period is not None and (declares == RELATION_KIND or period.type != PERIOD):
        raise _FormError('has a field "period", which is the period and no other field')
    if declares == RELATION_KIND:
        return
    name = by_name.get(NAME_FIELD)
    if name is None or name.type != TEXT or not name.required:
        raise _FormError('has no required text field "name"; every entity has a name')
    if PERIOD_BEHAVIOR in behaviors and period is None:
        raise _FormError('has the behavior "period" and no field "period" to hold it')


def _parse(payload: Mapping[str, object]) -> tuple[KindSpec, str]:
    """The spec and the statement of a payload, or `_FormError`."""
    if frozenset(payload) != _KEYS:
        raise _FormError(f"has the keys {sorted(payload)}, not {sorted(_KEYS)}")
    if payload["action"] != VOCABULARY:
        raise _FormError("is no vocabulary event")
    declares = payload["declares"]
    if declares not in _DECLARES:
        raise _FormError(f"declares {declares!r}, which is neither an entity nor a relation")
    declares = cast("str", declares)
    from_, to = payload["from"], payload["to"]
    connected = from_ is not None and to is not None
    unconnected = from_ is None and to is None
    if not (connected if declares == RELATION_KIND else unconnected):
        raise _FormError("has from and to exactly when it is a relation")
    name = _identifier(payload["name"], "a name")
    labels = _labels(payload["labels"])
    fields = tuple(_field(item) for item in _list(payload["fields"], "fields"))
    behaviors = _behaviors(payload["behaviors"], declares)
    _check_fields(declares, fields, behaviors)
    spec = KindSpec(
        declares,
        name,
        labels,
        fields,
        behaviors,
        None if from_ is None else _identifiers(from_, "from"),
        None if to is None else _identifiers(to, "to"),
        _flag(payload["retired"], "retired"),
    )
    statement = payload["statement"]
    if not isinstance(statement, str) or not statement:
        raise _FormError('has no "statement"')
    return spec, statement


def vocabulary_problem(payload: Mapping[str, object]) -> str | None:
    """What `verify` reports about the form of a vocabulary payload, or
    `None` when it is sound. Never raises.

    The write path would have refused anything found here: a finding means
    the event came another way.
    """
    try:
        _parse(payload)
    except _FormError as error:
        return f"has no valid form: it {error}"
    return None


def to_payload(spec: KindSpec, *, statement: str) -> dict[str, object]:
    return {
        "action": VOCABULARY,
        "declares": spec.declares,
        "name": spec.name,
        "labels": dict(spec.labels),
        "fields": [
            {
                "name": field.name,
                "type": field.type,
                "values": None if field.values is None else list(field.values),
                "ref": field.ref,
                "required": field.required,
            }
            for field in spec.fields
        ],
        "behaviors": sorted(spec.behaviors),
        "from": None if spec.from_ is None else list(spec.from_),
        "to": None if spec.to is None else list(spec.to),
        "retired": spec.retired,
        "statement": statement,
    }


# --- Reading ----------------------------------------------------------------------


def read_vocabulary[Conn](
    log: LogStore[Conn], conn: Conn, *, at: datetime | None = None
) -> Vocabulary:
    """The vocabulary in force: every vocabulary event up to `at` (all of
    them without it), the newest per kind, and the built-in kinds always.

    An event whose payload was erased counts as nothing, and one whose form
    is broken is skipped as `verify` reports it; neither stops the read. An
    event for a built-in kind sets the labels and nothing else.
    """
    folded = VocabularyFold()
    for row in log.actions(conn, VOCABULARY):
        if at is None or row.recorded_at <= at:
            folded.add(row.id, row.payload)
    return folded.vocabulary()


class VocabularyFold:
    """The vocabulary built one event at a time, in chain order, the way
    `read_vocabulary` builds it from the log.

    `verify` holds an entity or a relation against the vocabulary in force
    where it stands in the chain, and meets the vocabulary events on the
    way; reading the log again for every statement would cost a read per
    statement.
    """

    def __init__(self) -> None:
        self._kinds = {(spec.declares, spec.name): spec for spec in built_in_kinds()}
        self._ids: dict[tuple[str, str], int] = {}
        self._current: Vocabulary | None = None

    def add(self, event_id: int, payload: Mapping[str, object] | None) -> None:
        """Takes in one event. An erased one, one that is no vocabulary
        event, and one with a broken form change nothing."""
        if payload is None or payload.get("action") != VOCABULARY:
            return
        try:
            spec, _statement = _parse(payload)
        except _FormError:
            return
        key = (spec.declares, spec.name)
        if key in BUILT_IN:
            spec = replace(_built_in(*key), labels=spec.labels)
        self._kinds[key] = spec
        self._ids[key] = event_id
        self._current = None

    def vocabulary(self) -> Vocabulary:
        """The vocabulary of the events taken in so far. It does not change
        when more are taken in later."""
        if self._current is None:
            self._current = Vocabulary(dict(self._kinds), dict(self._ids))
        return self._current


# --- Differences and the write path -----------------------------------------------


def _order(spec: KindSpec) -> tuple[int, str]:
    return _DECLARES.index(spec.declares), spec.name


def differences(current: Vocabulary, wanted: Sequence[KindSpec]) -> tuple[KindSpec, ...]:
    """What to write so that the vocabulary becomes `wanted`: every spec that
    differs from the one in force, and every kind in force that `wanted` does
    not mention, retired. Built-in kinds a file leaves out stay, since they
    cannot be retired. Entities first, so that a relation finds the kinds it
    connects."""
    named = {(spec.declares, spec.name) for spec in wanted}
    changed = [spec for spec in wanted if current.kinds.get((spec.declares, spec.name)) != spec]
    changed += [
        replace(spec, retired=True)
        for key, spec in current.kinds.items()
        if key not in named and key not in BUILT_IN and not spec.retired
    ]
    return tuple(sorted(changed, key=_order))


def missing_kinds(current: Vocabulary, wanted: Sequence[KindSpec]) -> tuple[KindSpec, ...]:
    """The kinds of `wanted` that the vocabulary in force does not hold at
    all, entities first: what `apply --base` writes. A kind the log holds,
    retired or not and in whatever form, is not missing, so the base never
    retires, reshapes or lifts a kind the operator has made their own."""
    return tuple(
        sorted(
            (spec for spec in wanted if (spec.declares, spec.name) not in current.kinds),
            key=_order,
        )
    )


def differing_kinds(current: Vocabulary, wanted: Sequence[KindSpec]) -> tuple[KindSpec, ...]:
    """The kinds of `wanted` that the vocabulary in force holds in another
    form, entities first: what `apply --base` names and leaves as it
    stands."""
    return tuple(
        sorted(
            (
                spec
                for spec in wanted
                if (held := current.kinds.get((spec.declares, spec.name))) is not None
                and held != spec
            ),
            key=_order,
        )
    )


def changed_attributes(before: KindSpec, after: KindSpec) -> tuple[str, ...]:
    """The attributes of a kind that differ between two specs, in the order
    the file lists them."""
    names = ("labels", "fields", "behaviors", "from_", "to", "retired")
    return tuple(name for name in names if getattr(before, name) != getattr(after, name))


def _reference_problem(spec: KindSpec, kinds: Mapping[tuple[str, str], KindSpec]) -> str | None:
    """The sentence about a kind a spec names that does not stand, or `None`.
    A retired kind is not checked: it takes nothing new, whatever it names."""
    if spec.retired:
        return None
    named = [("from", name) for name in spec.from_ or ()] + [("to", n) for n in spec.to or ()]
    named += [(f'the ref of "{f.name}"', f.ref) for f in spec.fields if f.ref is not None]
    for where, name in named:
        target = kinds.get((ENTITY_KIND, name))
        if target is None or target.retired:
            return (
                f'{spec.declares} kind "{spec.name}" names "{name}" in {where}, '
                "which is no entity kind that stands"
            )
    if spec.declares == RELATION_KIND and (not spec.from_ or not spec.to):
        return f'relation kind "{spec.name}" needs at least one kind in from and in to'
    return None


def _built_in_problem(spec: KindSpec) -> str | None:
    fixed = _built_in(spec.declares, spec.name)
    if spec.retired:
        return f'"{spec.name}" is built in and cannot be retired'
    if replace(spec, labels=fixed.labels) != fixed:
        return f'"{spec.name}" is built in; only its labels can change'
    return None


def refusal(current: Vocabulary, changed: Sequence[KindSpec]) -> str | None:
    """The sentence that says why `changed` cannot be written on top of
    `current`, or `None`. The check runs against the vocabulary as it would
    stand afterwards, so a file may declare a relation together with the
    entity kinds it connects, and may not retire a kind another one needs."""
    after = dict(current.kinds)
    for spec in changed:
        after[(spec.declares, spec.name)] = spec
    for spec in changed:
        if (spec.declares, spec.name) in BUILT_IN and (problem := _built_in_problem(spec)):
            return problem
    for spec in after.values():
        if (spec.declares, spec.name) in BUILT_IN:
            continue
        if (problem := _reference_problem(spec, after)) is not None:
            return problem
    return None


def _statement(before: KindSpec | None, after: KindSpec) -> str:
    verb = "add" if before is None else "retire" if after.retired else "change"
    return f"{verb} {after.declares} kind {after.name} from a vocabulary file"


def apply_vocabulary[Conn](
    log: LogStore[Conn],
    specs: Sequence[KindSpec],
    *,
    recorded_at: datetime,
    add_only: bool = False,
) -> tuple[int, ...]:
    """Writes one event per kind that differs from the vocabulary in force,
    all in one transaction, and returns their ids; refuses with
    `VocabularyRefused` and writes nothing. A second call with the same specs
    writes nothing.

    With `add_only`, the specs are not the whole vocabulary but an offer: only
    the kinds the log does not hold yet are written (`missing_kinds`), and
    nothing is retired or changed. That is `apply --base`, which an operator
    runs after an update and which must not take their own kinds and fields
    away. What is missing is worked out here, under the tip, and not by the
    caller, so a vocabulary event that lands between the caller's preview and
    this write is never written over.

    The tip is read before the vocabulary, and the first event is written
    right after that tip, so a vocabulary event that joined the chain in
    between takes the position and the next attempt checks again; the rest
    follow inside the same transaction.
    """

    def once(conn: Conn) -> tuple[int, ...]:
        tip = log.tip(conn)
        current = read_vocabulary(log, conn)
        changed = missing_kinds(current, specs) if add_only else differences(current, specs)
        if (sentence := refusal(current, changed)) is not None:
            raise VocabularyRefused(sentence)
        ids: list[int] = []
        for spec in changed:
            payload = to_payload(
                spec, statement=_statement(current.kinds.get((spec.declares, spec.name)), spec)
            )
            if ids:
                ids.append(write_action(log, conn, payload, (), recorded_at=recorded_at))
            else:
                ids.append(write_action_at(log, conn, tip, payload, (), recorded_at=recorded_at))
        return tuple(ids)

    return retrying(log, once)


# --- The file ---------------------------------------------------------------------


def base_vocabulary() -> str:
    """The vocabulary file that ships with the package."""
    return resources.files("previously").joinpath("vocabulary.toml").read_text(encoding="utf-8")


def _quoted(text: str) -> str:
    return json.dumps(text, ensure_ascii=False)


def _inline_list(items: Sequence[str]) -> str:
    return "[" + ", ".join(_quoted(item) for item in items) + "]"


def _field_line(field: FieldSpec) -> str:
    parts = [f"name = {_quoted(field.name)}", f"type = {_quoted(field.type)}"]
    if field.values is not None:
        parts.append(f"values = {_inline_list(field.values)}")
    if field.ref is not None:
        parts.append(f"ref = {_quoted(field.ref)}")
    parts.append(f"required = {'true' if field.required else 'false'}")
    return "  { " + ", ".join(parts) + " },"


def _kind_lines(spec: KindSpec) -> list[str]:
    labels = ", ".join(f"{language} = {_quoted(spec.labels[language])}" for language in spec.labels)
    lines = [f"[{spec.declares}.{spec.name}]", f"labels = {{ {labels} }}"]
    lines.append(f"behaviors = {_inline_list(sorted(spec.behaviors))}")
    if spec.from_ is not None and spec.to is not None:
        lines += [f"from = {_inline_list(spec.from_)}", f"to = {_inline_list(spec.to)}"]
    if spec.retired:
        lines.append("retired = true")
    if not spec.fields:
        return [*lines, "fields = []"]
    return [*lines, "fields = [", *(_field_line(field) for field in spec.fields), "]"]


def render_file(vocabulary: Vocabulary) -> str:
    """The vocabulary as a file, in one canonical form: entity kinds before
    relation kinds, each sorted by identifier, labels sorted by language.
    `parse_file(render_file(v))` gives back the kinds of `v`."""
    lines = [
        "# The vocabulary of entities and relations, as the log holds it.",
        "# `previously vocabulary apply FILE` writes what differs from the log.",
    ]
    for spec in sorted(vocabulary.kinds.values(), key=_order):
        lines += ["", *_kind_lines(spec)]
    return "\n".join(lines) + "\n"


def _file_kind(declares: str, name: str, table: Mapping[str, object]) -> KindSpec:
    unknown = sorted(set(table) - _FILE_KEYS)
    if unknown:
        raise _FormError(f"has the unknown key {unknown[0]!r}; it knows {sorted(_FILE_KEYS)}")
    if "labels" not in table:
        raise _FormError("has no labels")
    fields = [
        {"values": None, "ref": None, "required": False, **_mapping(item, "fields")}
        for item in _list(table.get("fields", []), "fields")
    ]
    relation = declares == RELATION_KIND
    payload: dict[str, object] = {
        "action": VOCABULARY,
        "declares": declares,
        "name": name,
        "labels": table["labels"],
        "fields": fields,
        "behaviors": table.get("behaviors", []),
        "from": table.get("from", []) if relation else table.get("from"),
        "to": table.get("to", []) if relation else table.get("to"),
        "retired": table.get("retired", False),
        "statement": "from a vocabulary file",
    }
    return _parse(payload)[0]


def parse_file(text: str) -> tuple[KindSpec, ...]:
    """The kinds a vocabulary file declares, or `VocabularyRefused` with one
    sentence that names the kind and says what is wrong.

    An unknown key is an error and not skipped: a misspelled `behaviours`
    would otherwise declare a kind without the behavior and say nothing.
    """
    try:
        document = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise VocabularyRefused(f"the vocabulary file is no TOML: {error}") from error
    unknown = sorted(set(document) - set(_DECLARES))
    if unknown:
        raise VocabularyRefused(
            f"the vocabulary file has the unknown table {unknown[0]!r}; "
            "it has [entity.NAME] and [relation.NAME]"
        )
    specs: list[KindSpec] = []
    for declares in _DECLARES:
        try:
            tables = _mapping(document.get(declares, {}), declares)
        except _FormError as error:
            raise VocabularyRefused(f"the vocabulary file {error}") from error
        for name, table in tables.items():
            try:
                specs.append(_file_kind(declares, name, _mapping(table, name)))
            except _FormError as error:
                raise VocabularyRefused(f'{declares} kind "{name}" {error}') from error
    return tuple(specs)
