# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Assertions: the payload form of an obligation, a decision and a rejection,
the references to actors inside them, and the folding of versions.

Pure: no database, no clock. A caller hands in rows in chain order and gets
back what stands.

The form is hashed into the log for good, so it is checked strictly: exactly
the keys of the subtype, no more and no fewer, no float, no date but
`YYYY-MM-DD`, no source-less assertion. `assertion_problem` returns one short
sentence naming the field, never the text found there: a refusal can end up in
a log or on a terminal, and an assertion's text may come from a mail whose
erasure the log has to survive.

An obligation or a decision is named after the event of its first version.
Each further version says everything that holds after it, and carries that
name as `subject`. A rejection has no `subject`: it names the proposal it
rejects in `of`, and `fold` attaches it to the thread of that proposal.
Direct responsibility beats open; within one level the latest version wins
({ref}`assertions-responsibility`).
An approval is a new direct version with the content of the proposal and
`approves` pointing at it.
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import date
from datetime import datetime
from itertools import pairwise
from previously.core.canonical import MAX_SAFE_INT
from typing import cast
from typing import Final
from typing import TYPE_CHECKING

import re
import unicodedata


if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping
    from collections.abc import Sequence


OBLIGATION: Final = "obligation"
DECISION: Final = "decision"
REJECTION: Final = "rejection"
KINDS: Final = (OBLIGATION, DECISION, REJECTION)

DIRECT: Final = "direct"
OPEN: Final = "open"
RESPONSIBILITIES: Final = (DIRECT, OPEN)

OPERATOR: Final = "human:operator"
MODEL_PREFIX: Final = "model:"

OBLIGATION_STATES: Final = ("open", "fulfilled", "cancelled")
DECISION_STATES: Final = ("valid", "revoked")

OWN: Final = "own"
MAX_NAME_LENGTH: Final = 200
MAX_ADDRESS_LENGTH: Final = 254

_DATE_FORM = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)
_COMMON_KEYS: Final = frozenset(
    {"assertion", "author", "responsibility", "sources", "reason", "handle"}
)
_VERSION_KEYS: Final = _COMMON_KEYS | {"subject", "approves"}
_OBLIGATION_KEYS: Final = _VERSION_KEYS | {"debtor", "creditor", "what", "due", "state"}
_DECISION_KEYS: Final = _VERSION_KEYS | {"what", "by", "on", "state", "replaces"}
_REJECTION_KEYS: Final = _COMMON_KEYS | {"of"}


def model_author(client: str) -> str:
    """The author string of a model: `model:<client>`."""
    return f"{MODEL_PREFIX}{client}"


# --- References to actors -------------------------------------------------------


def _has_forbidden_character(text: str) -> bool:
    # Cc (controls) and Cf (format characters such as the bidi overrides) plus
    # the two line separators, which have category Zl and Zp: all of them
    # change how a name is displayed without being part of it.
    return any(unicodedata.category(char) in ("Cc", "Cf") or char in "  " for char in text)


def _is_label(text: str) -> bool:
    return (
        0 < len(text) <= MAX_NAME_LENGTH
        and bool(text.strip())
        and not _has_forbidden_character(text)
    )


def _address_problem(address: str) -> str | None:
    if len(address) > MAX_ADDRESS_LENGTH:
        return f"the address of the reference is longer than {MAX_ADDRESS_LENGTH} characters"
    if address.count("@") != 1 or any(char.isspace() for char in address):
        return "the address of the reference needs exactly one @ and no white space"
    local, _at, domain = address.partition("@")
    if not local or not domain:
        return "the address of the reference needs a part before and after the @"
    if _has_forbidden_character(address):
        return "the address of the reference has control characters"
    return None


def reference_problem(text: str) -> str | None:
    """Why `text` is not a reference to an actor, or None if it is one.

    The sentence never contains the text, which may be an address.
    """
    prefix, _colon, rest = text.partition(":")
    if text == OWN:
        return None
    if prefix == "circle" and _colon:
        # The policy accepts any non-blank text as a circle name
        # (`_check_text` in core/policy.py). The rule is applied here
        # unchanged instead of exposing a helper from policy.py: a circle the
        # policy can name has to be referable, and a copy of one line is
        # cheaper than a new public name. Control characters are the output
        # side's business.
        if rest.strip():
            return None
        return "the circle name of the reference is empty"
    if prefix == "address" and _colon:
        return _address_problem(rest)
    if prefix == "name" and _colon:
        if _is_label(rest):
            return None
        return (
            f"the name of the reference must have 1 to {MAX_NAME_LENGTH} characters"
            " and no control characters"
        )
    return "the reference has no known prefix: use own, circle:, address: or name:"


# --- Values ---------------------------------------------------------------------


@dataclass(frozen=True)
class Source:
    """An event the assertion rests on, with the units it cites; None means the
    whole event."""

    event: int
    units: tuple[int, ...] | None


@dataclass(frozen=True)
class ObligationBody:
    debtor: str
    creditor: str
    what: str
    due: date | None
    state: str


# Not `Decision`: that is the result of `decide` in core/decide.py, which the
# same code imports.
@dataclass(frozen=True)
class DecisionBody:
    what: str
    by: tuple[str, ...]
    on: date
    state: str
    replaces: int | None


@dataclass(frozen=True)
class Statement:
    kind: str
    author: str
    responsibility: str
    sources: tuple[Source, ...]
    reason: str | None
    handle: str | None
    subject: int | None
    approves: int | None
    of: int | None
    body: ObligationBody | DecisionBody | None  # None only for a rejection


def _source_payload(source: Source) -> dict[str, object]:
    units: list[int] | None = None if source.units is None else list(source.units)
    return {"event": source.event, "units": units}


def payload_of(statement: Statement) -> dict[str, object]:
    """The payload a statement is written as; the inverse of `parse_statement`."""
    payload: dict[str, object] = {
        "assertion": statement.kind,
        "author": statement.author,
        "responsibility": statement.responsibility,
        "sources": [_source_payload(source) for source in statement.sources],
        "reason": statement.reason,
        "handle": statement.handle,
    }
    body = statement.body
    if isinstance(body, ObligationBody):
        payload["subject"] = statement.subject
        payload["approves"] = statement.approves
        payload["debtor"] = body.debtor
        payload["creditor"] = body.creditor
        payload["what"] = body.what
        payload["due"] = None if body.due is None else body.due.isoformat()
        payload["state"] = body.state
    elif isinstance(body, DecisionBody):
        payload["subject"] = statement.subject
        payload["approves"] = statement.approves
        payload["what"] = body.what
        payload["by"] = list(body.by)
        payload["on"] = body.on.isoformat()
        payload["state"] = body.state
        payload["replaces"] = body.replaces
    else:
        payload["of"] = statement.of
    return payload


# --- Checking the form ----------------------------------------------------------


def _is_id(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= MAX_SAFE_INT


def _text(payload: Mapping[str, object], key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) and value.strip() else None


def _date(value: object) -> date | None:
    # The form is checked before `fromisoformat`, which would also take
    # `20260203` and `2026-W05-1`; the payload carries one spelling only.
    if not isinstance(value, str) or _DATE_FORM.fullmatch(value) is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _author_problem(author: object) -> str | None:
    if author == OPERATOR:
        return None
    if isinstance(author, str) and author.startswith(MODEL_PREFIX):
        client = author[len(MODEL_PREFIX) :]
        if (
            0 < len(client) <= MAX_NAME_LENGTH
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


def _sources_problem(sources: object) -> str | None:
    if not isinstance(sources, list):
        return "the sources are not a list"
    items = cast("list[object]", sources)
    if not items:
        return "the sources are empty: an assertion needs at least one source"
    for item in items:
        problem = _source_problem(item)
        if problem is not None:
            return problem
    return None


def _optional_id_problem(payload: Mapping[str, object], key: str) -> str | None:
    value = payload[key]
    if value is None or _is_id(value):
        return None
    return f"{key} is neither null nor an event id"


def _common_problem(payload: Mapping[str, object]) -> str | None:
    problem = _author_problem(payload["author"])
    if problem is not None:
        return problem
    if payload["responsibility"] not in RESPONSIBILITIES:
        return "the responsibility is neither direct nor open"
    problem = _sources_problem(payload["sources"])
    if problem is not None:
        return problem
    for key in ("reason", "handle"):
        value = payload[key]
        if value is not None and not (isinstance(value, str) and value.strip()):
            return f"{key} is neither null nor a non-empty text"
    return None


def _version_problem(payload: Mapping[str, object]) -> str | None:
    for key in ("subject", "approves"):
        problem = _optional_id_problem(payload, key)
        if problem is not None:
            return problem
    approves, subject = payload["approves"], payload["subject"]
    if approves is not None and subject is None:
        return "an approval needs a subject"
    if approves is not None and payload["responsibility"] != DIRECT:
        return "an approval is direct"
    # A model proposes; what it writes is direct only when it is an approval,
    # which makes the operator's choice its own. Otherwise a proposal that
    # came around the MCP tool would outrank the operator's direct version
    # ({ref}`assertions-responsibility`).
    # A rejection is not a version and is exempt: `write_reject` writes it
    # direct with the author of its way.
    author = cast("str", payload["author"])
    if author.startswith(MODEL_PREFIX) and payload["responsibility"] == DIRECT and approves is None:
        return "a version by a model is direct only as an approval"
    return None


def _obligation_problem(payload: Mapping[str, object]) -> str | None:
    for key, label in (("debtor", "the debtor"), ("creditor", "the creditor")):
        value = payload[key]
        if not isinstance(value, str) or reference_problem(value) is not None:
            return f"{label} is not a valid reference"
    if _text(payload, "what") is None:
        return "what is not a non-empty text"
    due = payload["due"]
    if due is not None and _date(due) is None:
        return "due is neither null nor a date written YYYY-MM-DD"
    if payload["state"] not in OBLIGATION_STATES:
        return "the state of an obligation is none of open, fulfilled, cancelled"
    return None


def _decision_problem(payload: Mapping[str, object]) -> str | None:
    if _text(payload, "what") is None:
        return "what is not a non-empty text"
    by = payload["by"]
    if not isinstance(by, list) or not by:
        return "by is not a list with at least one reference"
    for reference in cast("list[object]", by):
        if not isinstance(reference, str) or reference_problem(reference) is not None:
            return "a decider is not a valid reference"
    if _date(payload["on"]) is None:
        return "on is not a date written YYYY-MM-DD"
    if payload["state"] not in DECISION_STATES:
        return "the state of a decision is neither valid nor revoked"
    return _optional_id_problem(payload, "replaces")


def _rejection_problem(payload: Mapping[str, object]) -> str | None:
    if not _is_id(payload["of"]):
        return "of is not the id of a proposal"
    if payload["responsibility"] != DIRECT:
        return "a rejection is direct"
    return None


def assertion_problem(payload: Mapping[str, object]) -> str | None:
    """Why `payload` is not the form of an assertion, or None. Never raises."""
    kind = payload.get("assertion")
    expected = {OBLIGATION: _OBLIGATION_KEYS, DECISION: _DECISION_KEYS, REJECTION: _REJECTION_KEYS}
    keys = expected.get(kind) if isinstance(kind, str) else None
    if keys is None:
        return "the assertion kind is none of obligation, decision, rejection"
    if frozenset(payload) != keys:
        return "the keys of the payload are not those of the assertion kind"
    problem = _common_problem(payload)
    if problem is not None:
        return problem
    if kind == REJECTION:
        return _rejection_problem(payload)
    problem = _version_problem(payload)
    if problem is not None:
        return problem
    return _obligation_problem(payload) if kind == OBLIGATION else _decision_problem(payload)


def _optional_id(payload: Mapping[str, object], key: str) -> int | None:
    value = payload[key]
    return cast("int", value) if value is not None else None


def _source_of(item: object) -> Source:
    entry = cast("dict[str, object]", item)
    units = entry["units"]
    return Source(
        cast("int", entry["event"]),
        None if units is None else tuple(cast("list[int]", units)),
    )


def _body_of(kind: str, payload: Mapping[str, object]) -> ObligationBody | DecisionBody:
    if kind == OBLIGATION:
        due = payload["due"]
        return ObligationBody(
            cast("str", payload["debtor"]),
            cast("str", payload["creditor"]),
            cast("str", payload["what"]),
            None if due is None else date.fromisoformat(cast("str", due)),
            cast("str", payload["state"]),
        )
    return DecisionBody(
        cast("str", payload["what"]),
        tuple(cast("list[str]", payload["by"])),
        date.fromisoformat(cast("str", payload["on"])),
        cast("str", payload["state"]),
        _optional_id(payload, "replaces"),
    )


def parse_statement(payload: Mapping[str, object]) -> Statement | None:
    """The statement a payload holds, or None if `assertion_problem` finds fault."""
    if assertion_problem(payload) is not None:
        return None
    kind = cast("str", payload["assertion"])
    sources = tuple(_source_of(item) for item in cast("list[object]", payload["sources"]))
    author = cast("str", payload["author"])
    responsibility = cast("str", payload["responsibility"])
    reason = cast("str | None", payload["reason"])
    handle = cast("str | None", payload["handle"])
    if kind == REJECTION:
        of = _optional_id(payload, "of")
        return Statement(
            kind, author, responsibility, sources, reason, handle, None, None, of, None
        )
    return Statement(
        kind,
        author,
        responsibility,
        sources,
        reason,
        handle,
        _optional_id(payload, "subject"),
        _optional_id(payload, "approves"),
        None,
        _body_of(kind, payload),
    )


# --- Folding versions -----------------------------------------------------------


@dataclass(frozen=True)
class Version:
    id: int
    recorded_at: datetime
    statement: Statement


@dataclass(frozen=True)
class Thread:
    """All standing versions of one obligation or decision, in chain order."""

    subject: int
    kind: str
    versions: tuple[Version, ...]
    rejected: frozenset[int] = field(default_factory=frozenset[int])
    approved: frozenset[int] = field(default_factory=frozenset[int])

    def _candidates(self) -> tuple[Version, ...]:
        return tuple(
            version
            for version in self.versions
            if version.statement.responsibility == OPEN
            and version.id not in self.rejected
            and version.id not in self.approved
        )

    def _direct_winner(self) -> Version | None:
        direct = [v for v in self.versions if v.statement.responsibility == DIRECT]
        return direct[-1] if direct else None

    def winner(self) -> Version | None:
        """The latest direct version, else the latest open one that is neither
        rejected nor approved (then it stands as a proposal)."""
        direct = self._direct_winner()
        if direct is not None:
            return direct
        candidates = self._candidates()
        return candidates[-1] if candidates else None

    def pending(self) -> tuple[Version, ...]:
        """Open versions that are neither rejected nor approved and are not
        the winner: those newer than the direct winner, or, with no direct
        version, all of them except the latest, which stands as the proposal.
        The winner is never in the list."""
        direct = self._direct_winner()
        candidates = self._candidates()
        if direct is None:
            return candidates[:-1]
        position = self.versions.index(direct)
        later = {version.id for version in self.versions[position + 1 :]}
        return tuple(v for v in candidates if v.id in later)


@dataclass
class _Draft:
    kind: str
    versions: list[Version] = field(default_factory=lambda: [])
    rejected: set[int] = field(default_factory=lambda: set[int]())
    approved: set[int] = field(default_factory=lambda: set[int]())


def _approvable(draft: _Draft, approves: int, erased: set[int]) -> bool:
    """Whether an approval of `approves` joins the thread of `draft`: the
    proposal is not answered yet, and it is an open version of the thread,
    or erased.

    An approval of a proposal erased on its own stands: it is a whole
    statement with its own sources, checked when it was written. One whose
    proposal went through a source went with it.
    """
    if approves in draft.approved or approves in draft.rejected:
        return False
    if approves in erased:
        return True
    proposal = next((v for v in draft.versions if v.id == approves), None)
    return proposal is not None and proposal.statement.responsibility == OPEN


def fold(
    rows: Iterable[tuple[int, datetime, Mapping[str, object] | None]],
) -> dict[int, Thread]:
    """The threads standing in `rows`, which are given in chain order.

    Erased rows (payload None) and rows with a form fault are skipped. A thread
    lives as long as one of its versions stands: it keeps the id of its first
    version as its name even when that version is erased, and takes its kind
    from the first version that stands. Also skipped: a version whose
    `subject` names nothing, a rejection whose `of` names no standing version,
    and an approval of a proposal that is not open or is already approved or
    rejected. `verify` reports each of them, except a rejection of an erased
    proposal, which says nothing that still stands. An approval of an erased
    proposal stands.
    """
    drafts: dict[int, _Draft] = {}
    thread_of: dict[int, int] = {}  # standing version id -> subject of its thread
    erased: set[int] = set()
    for row_id, recorded_at, payload in rows:
        if payload is None:
            erased.add(row_id)
            continue
        statement = parse_statement(payload)
        if statement is None:
            continue
        if statement.kind == REJECTION:
            proposal = cast("int", statement.of)
            target = thread_of.get(proposal)
            if target is not None:
                drafts[target].rejected.add(proposal)
            continue
        subject = row_id if statement.subject is None else statement.subject
        if statement.subject is not None and subject not in drafts and subject not in erased:
            continue  # names nothing: not a first version, not an erased one
        draft = drafts.get(subject) or _Draft(statement.kind)  # kept only once a version joins
        if draft.kind != statement.kind:
            continue
        approves = statement.approves
        if approves is not None:
            if not _approvable(draft, approves, erased):
                continue
            draft.approved.add(approves)
        draft.versions.append(Version(row_id, recorded_at, statement))
        drafts[subject] = draft
        thread_of[row_id] = subject
    return {
        subject: Thread(
            subject,
            draft.kind,
            tuple(draft.versions),
            frozenset(draft.rejected),
            frozenset(draft.approved),
        )
        for subject, draft in drafts.items()
    }


# --- Reading --------------------------------------------------------------------

_NONE: Final = "(none)"


def _sources_text(sources: Sequence[Source]) -> str:
    def one(source: Source) -> str:
        if source.units is None:
            return f"event {source.event}"
        return f"event {source.event} units {', '.join(str(seq) for seq in source.units)}"

    return "; ".join(one(source) for source in sources)


def _fields_of(statement: Statement) -> dict[str, str]:
    fields: dict[str, str] = {}
    body = statement.body
    if isinstance(body, ObligationBody):
        fields["debtor"] = body.debtor
        fields["creditor"] = body.creditor
        fields["what"] = body.what
        fields["due"] = _NONE if body.due is None else body.due.isoformat()
        fields["state"] = body.state
    elif isinstance(body, DecisionBody):
        fields["what"] = body.what
        fields["by"] = ", ".join(body.by)
        fields["on"] = body.on.isoformat()
        fields["state"] = body.state
        fields["replaces"] = _NONE if body.replaces is None else str(body.replaces)
    fields["sources"] = _sources_text(statement.sources)
    fields["reason"] = _NONE if statement.reason is None else statement.reason
    return fields


def approval_note(statement: Statement) -> str | None:
    """How a version that approves a proposal reads where it is shown, or
    `None` for any other version.

    An approval keeps the author of the proposal, the one who formulated
    it, and is direct: the operator stands for it
    ({ref}`assertions-proposals`). Shown as a bare `direct` beside a
    `model:` author it reads as that model's own decision, which it is not.
    The payload records no channel, so the note says none.
    """
    if statement.approves is None:
        return None
    return (
        f"made its own by the operator (approval of {statement.approves}), "
        f"formulated by {statement.author}"
    )


REJECTION_NOTE: Final = "rejected (by the operator)"
"""What a rejection reads as before its reason. Like an approval it is direct,
and the author is whoever wrote it down, which may be a `model:` client."""


def changes(before: Statement, after: Statement) -> tuple[tuple[str, str, str], ...]:
    """The fields that differ, as `(field, before, after)`: the body fields,
    `sources` and `reason`. Computed when read, never stored."""
    old, new = _fields_of(before), _fields_of(after)
    names = [*old, *(name for name in new if name not in old)]
    return tuple(
        (name, old.get(name, _NONE), new.get(name, _NONE))
        for name in names
        if old.get(name) != new.get(name)
    )


def overdue(obligation: ObligationBody, today: date) -> bool:
    """Open and due before `today`; `today` is the caller's, never read here."""
    return obligation.state == "open" and obligation.due is not None and obligation.due < today
