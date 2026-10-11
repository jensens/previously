# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The processing policy: what may leave the machine, and where it may go.

The policy is not a file or a table. It is a sequence of events of the kind
`action` with `payload.action = "policy"`, set by the keeper, with no source
key and no units, so it sits in the chain and `verify` covers it like any
other action. Six statements exist (`payload.policy`): a circle, the
membership of an address or a domain in a circle, an own identity of the
operator, a rule that gives a scope its conditions, what a provider account
promises, and an MCP client with the promise it is processed under and the
SHA-256 of its token. Every one carries the sentence it was set with under
`statement`; the gate never reads it.

A newer event with the same key replaces the older one, and a revocation is
an event of the same statement with `revoked: true`. The older one stays in
the chain, so the policy of a past day is the log read up to that day:
`read_policy(at=…)`. An erased policy event (its payload is gone) counts as
nothing, which is the same as a revocation: the version before it applies, or
none.

Sets are written as sorted lists, so that the same statement has the same
payload whatever order it was typed in.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from enum import StrEnum
from previously.core.action import POLICY
from previously.core.action import retrying
from previously.core.action import write_action_at
from previously.core.errors import PreviouslyError
from typing import cast
from typing import Final
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from datetime import datetime
    from previously.contract.store import LogStore


class Region(StrEnum):
    """A place of processing or storage that a rule can name."""

    EU = "eu"
    US = "us"


# The value of a rule that allows every region, and of an inference space
# that stands for "wherever the provider likes" (`global` at Anthropic).
ANY: Final = "any"

# The name of the built-in rule that applies where no other rule does: only a
# provider that is `local`. It is not an event and cannot be revoked; it is
# named here so that `policy show` can list it and the decision can cite it,
# and nobody has to hunt for a silent default.
LOCAL_ONLY: Final = "local_only"

_REGIONS: Final = frozenset({Region.EU.value, Region.US.value, ANY})
_STORAGE_PLACES: Final = frozenset({Region.EU.value, Region.US.value})

CIRCLE: Final = "circle"
MEMBERSHIP: Final = "membership"
OWN_IDENTITY: Final = "own_identity"
RULE: Final = "rule"
PROVIDER: Final = "provider"
CLIENT: Final = "client"
KINDS: Final = (CIRCLE, MEMBERSHIP, OWN_IDENTITY, RULE, PROVIDER, CLIENT)

# A SHA-256 as hex: 64 digits. The payload never holds the token itself.
_TOKEN_HASH_LENGTH: Final = 64
_HEX_DIGITS: Final = frozenset("0123456789abcdef")

_KEY_SEPARATOR: Final = "\t"


@dataclass(frozen=True)
class Circle:
    name: str


@dataclass(frozen=True)
class Membership:
    circle: str
    member: str  # an address, or a domain as "@domain"


@dataclass(frozen=True)
class OwnIdentity:
    member: str


@dataclass(frozen=True)
class Rule:
    scope: str  # "circle:<name>" or "source:<source>"
    regions: frozenset[str]  # {"eu"}, {"us"}, {"eu", "us"} or {"any"}
    max_retention_days: int | None
    excluded_providers: frozenset[str]
    # Restrictions on the processing chain behind a provider. A flag is off
    # by default; a candidate passes a restriction only with a known value
    # that satisfies it.
    no_training: bool = False
    no_subprocessors: bool = False
    excluded_operators: frozenset[str] = frozenset()
    excluded_model_origins: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Inference:
    name: str
    regions: frozenset[str]  # "global" is {"any"}, "us" is {"us"}, "eu" is {"eu"}


@dataclass(frozen=True)
class Provider:
    name: str
    inference: tuple[Inference, ...]
    storage: frozenset[str]  # empty: stores nothing
    retention_days: int | None  # None: unknown
    reports_inference_geo: bool
    local: bool
    # The processing chain. `None` means unknown, which is what a declaration
    # written before these fields existed reads as; for the subprocessors,
    # `frozenset()` is the statement that there are none.
    operator: str | None = None
    training: bool | None = None
    subprocessors: frozenset[str] | None = None
    model_origin: str | None = None


@dataclass(frozen=True)
class Client:
    """An MCP client as a principal: a name, the declared provider whose
    promise its reading is processed under, and the hash of its token."""

    name: str
    processor: str  # the name of a declared provider
    token_sha256: str  # hex; the token itself is never stored


type Statement = Circle | Membership | OwnIdentity | Rule | Provider | Client


@dataclass(frozen=True)
class Policy:
    circles: Mapping[str, Circle]
    memberships: tuple[Membership, ...]
    own: tuple[OwnIdentity, ...]
    rules: Mapping[str, Rule]
    providers: Mapping[str, Provider]
    # (kind, key) → the id of the event that set it, for the audit of a call.
    ids: Mapping[tuple[str, str], int]
    clients: Mapping[str, Client] = field(default_factory=dict[str, Client])


class PolicyRefused(PreviouslyError):
    """A statement the write path refuses: one sentence, nothing written."""


class _FormError(Exception):
    """The sentence about what is wrong with a statement."""


def _kind_of(item: Statement) -> str:
    match item:
        case Circle():
            return CIRCLE
        case Membership():
            return MEMBERSHIP
        case OwnIdentity():
            return OWN_IDENTITY
        case Rule():
            return RULE
        case Provider():
            return PROVIDER
        case Client():
            return CLIENT


def key_of(item: Statement) -> tuple[str, str]:
    """The kind and the key under which a newer event replaces an older one."""
    match item:
        case Circle(name=name):
            return CIRCLE, name
        case Membership(circle=circle, member=member):
            return MEMBERSHIP, f"{circle}{_KEY_SEPARATOR}{member}"
        case OwnIdentity(member=member):
            return OWN_IDENTITY, member
        case Rule(scope=scope):
            return RULE, scope
        case Provider(name=name):
            return PROVIDER, name
        case Client(name=name):
            return CLIENT, name


def to_payload(item: Statement, *, statement: str, revoked: bool = False) -> dict[str, object]:
    """The payload of one policy event; every set as a sorted list."""
    payload: dict[str, object] = {"action": POLICY, "policy": _kind_of(item)}
    match item:
        case Circle(name=name):
            payload["name"] = name
        case Membership(circle=circle, member=member):
            payload["circle"] = circle
            payload["member"] = member
        case OwnIdentity(member=member):
            payload["member"] = member
        case Rule():
            payload["scope"] = item.scope
            payload["regions"] = sorted(item.regions)
            payload["max_retention_days"] = item.max_retention_days
            payload["excluded_providers"] = sorted(item.excluded_providers)
            payload["no_training"] = item.no_training
            payload["no_subprocessors"] = item.no_subprocessors
            payload["excluded_operators"] = sorted(item.excluded_operators)
            payload["excluded_model_origins"] = sorted(item.excluded_model_origins)
        case Provider():
            payload["provider"] = item.name
            payload["inference"] = [
                {"name": spaces.name, "regions": sorted(spaces.regions)}
                for spaces in sorted(item.inference, key=lambda spaces: spaces.name)
            ]
            payload["storage"] = sorted(item.storage)
            payload["retention_days"] = item.retention_days
            payload["reports_inference_geo"] = item.reports_inference_geo
            payload["local"] = item.local
            payload["operator"] = item.operator
            payload["training"] = item.training
            payload["subprocessors"] = (
                None if item.subprocessors is None else sorted(item.subprocessors)
            )
            payload["model_origin"] = item.model_origin
        case Client():
            payload["name"] = item.name
            payload["processor"] = item.processor
            payload["token_sha256"] = item.token_sha256
    payload["statement"] = statement
    payload["revoked"] = revoked
    return payload


def normalize_member(member: str) -> str:
    """The domain in lower case, the local part as it stands.

    Domains do not depend on case and local parts may (RFC 5321), so two
    spellings of one domain must be one key: otherwise a revocation typed
    with another case would revoke nothing.
    """
    local, at, domain = member.rpartition("@")
    return f"{local}{at}{domain.lower()}"


# --- The form of each statement -------------------------------------------------


def _check_text(value: str, what: str) -> None:
    if not value.strip():
        raise _FormError(f"{what} is empty")


def _check_member(member: str) -> None:
    _local, at, domain = member.rpartition("@")
    if not at or "." not in domain or domain.startswith(".") or domain.endswith("."):
        raise _FormError(
            f'"{member}" is not an address or a domain: use name@domain.tld or @domain.tld'
        )
    if any(char.isspace() for char in member):
        raise _FormError(f'"{member}" contains white space')


def _check_regions(regions: frozenset[str], allowed: frozenset[str], what: str) -> None:
    if not regions:
        raise _FormError(f"{what} needs at least one region: eu, us or any")
    unknown = sorted(regions - allowed)
    if unknown:
        raise _FormError(f'{what} names "{unknown[0]}", which is not a region')
    if ANY in regions and len(regions) > 1:
        raise _FormError(f'{what} combines "any" with another region')


def _check_days(days: int | None, what: str) -> None:
    if days is not None and days < 0:
        raise _FormError(f"{what} is negative")


def _check_scope(scope: str) -> None:
    name = scope.partition(":")[2]
    if scope.startswith("project:"):
        raise _FormError(
            f'scope "{scope}" is not effective yet: project scopes arrive with the projects; '
            "use circle:<name> or source:<source>"
        )
    if not (scope.startswith(("circle:", "source:")) and name.strip()):
        raise _FormError(f'scope "{scope}" is not circle:<name> or source:<source>')


def _check_names(names: frozenset[str], what: str) -> None:
    for name in names:
        _check_text(name, f"{what} name")


def _check_chain(provider: Provider) -> None:
    for what, value in (("operator", provider.operator), ("model origin", provider.model_origin)):
        if value is not None:
            _check_text(value, f"the {what}")
    _check_names(provider.subprocessors or frozenset(), "a subprocessor")


def _check_client(client: Client) -> None:
    _check_text(client.name, "the client name")
    _check_text(client.processor, "the processor")
    digits = set(client.token_sha256)
    if len(client.token_sha256) != _TOKEN_HASH_LENGTH or not digits <= _HEX_DIGITS:
        raise _FormError("the token hash is not a SHA-256 in lower-case hex")


def _check(item: Statement, statement: str) -> None:
    """Everything that can be said about a statement without the policy."""
    _check_text(statement, "the statement")
    match item:
        case Circle(name=name):
            _check_text(name, "the circle name")
        case Membership(circle=circle, member=member):
            _check_text(circle, "the circle name")
            _check_member(member)
        case OwnIdentity(member=member):
            _check_member(member)
        case Rule():
            _check_scope(item.scope)
            _check_regions(item.regions, _REGIONS, "a rule")
            _check_days(item.max_retention_days, "the retention limit")
            _check_names(item.excluded_operators | item.excluded_model_origins, "an exclusion")
        case Provider():
            _check_text(item.name, "the provider name")
            _check_days(item.retention_days, "the retention")
            _check_chain(item)
            for spaces in item.inference:
                _check_text(spaces.name, "an inference space name")
                _check_regions(spaces.regions, _REGIONS, f'inference "{spaces.name}"')
            if item.storage:
                _check_regions(item.storage, _STORAGE_PLACES, "storage")
        case Client():
            _check_client(item)


def refusal(item: Statement, *, statement: str, revoked: bool, current: Policy) -> str | None:
    """The sentence that says why `item` is refused against the policy
    `current`, or `None`."""
    try:
        _check(item, statement)
    except _FormError as error:
        return str(error)
    if isinstance(item, Membership) and not revoked and item.circle not in current.circles:
        return (
            f'no circle "{item.circle}" exists — create it first with '
            f"previously policy circle {item.circle}"
        )
    if isinstance(item, Client) and not revoked and item.processor not in current.providers:
        return (
            f'the processor "{item.processor}" is not declared — declare it first with '
            f"previously policy provider {item.processor}"
        )
    return None


def normalized(item: Statement) -> Statement:
    match item:
        case Membership(circle=circle, member=member):
            return Membership(circle, normalize_member(member))
        case OwnIdentity(member=member):
            return OwnIdentity(normalize_member(member))
        case _:
            return item


def set_policy[Conn](
    log: LogStore[Conn],
    item: Statement,
    *,
    statement: str,
    revoked: bool = False,
    recorded_at: datetime,
) -> int:
    """Writes one policy event and returns its `id`, or refuses with
    `PolicyRefused` and writes nothing.

    The check runs against every event below the position the statement
    takes, so a circle revoked while the check ran cannot be named by a
    membership that passed it. The tip is read before the policy and the
    statement is written right after that tip: one transaction alone would
    not do it, since under READ COMMITTED each statement reads a snapshot of
    its own. A revocation that commits after the tip was read takes the
    position, the write loses it, and the next attempt checks again.
    """
    item = normalized(item)
    payload = to_payload(item, statement=statement, revoked=revoked)

    def once(conn: Conn) -> int:
        tip = log.tip(conn)
        sentence = refusal(
            item, statement=statement, revoked=revoked, current=read_policy(log, conn)
        )
        if sentence is not None:
            raise PolicyRefused(sentence)
        return write_action_at(log, conn, tip, payload, (), recorded_at=recorded_at)

    return retrying(log, once)


# --- Reading ---------------------------------------------------------------------


def _text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise _FormError(f'has no "{key}"')
    return value


def _names(payload: Mapping[str, object], key: str) -> frozenset[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise _FormError(f'has no list "{key}"')
    entries = cast("list[object]", value)
    names = [entry for entry in entries if isinstance(entry, str)]
    if len(names) != len(entries):
        raise _FormError(f'has a "{key}" entry that is not text')
    return frozenset(names)


def _days(payload: Mapping[str, object], key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise _FormError(f'has no whole number "{key}"')
    return value


def _flag(payload: Mapping[str, object], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise _FormError(f'has no true or false "{key}"')
    return value


def _optional_text(payload: Mapping[str, object], key: str) -> str | None:
    """Text, or `None` for `null` and for a key a declaration written before
    the key existed does not have."""
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise _FormError(f'has a "{key}" that is not text or null')
    return value


def _optional_flag(payload: Mapping[str, object], key: str) -> bool | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, bool):
        raise _FormError(f'has a "{key}" that is not true, false or null')
    return value


def _optional_names(payload: Mapping[str, object], key: str) -> frozenset[str] | None:
    if payload.get(key) is None:
        return None
    return _names(payload, key)


def _flag_or_off(payload: Mapping[str, object], key: str) -> bool:
    """A flag that an older rule does not have is off."""
    return _flag(payload, key) if key in payload else False


def _names_or_empty(payload: Mapping[str, object], key: str) -> frozenset[str]:
    """A set that an older rule does not have is empty."""
    return _names(payload, key) if key in payload else frozenset()


def _inference(payload: Mapping[str, object]) -> tuple[Inference, ...]:
    value = payload.get("inference")
    if not isinstance(value, list):
        raise _FormError('has no list "inference"')
    spaces: list[Inference] = []
    for entry in cast("list[object]", value):
        if not isinstance(entry, dict):
            raise _FormError('has an "inference" entry that is not an object')
        fields = cast("dict[str, object]", entry)
        spaces.append(Inference(_text(fields, "name"), _names(fields, "regions")))
    return tuple(spaces)


def _parse(payload: Mapping[str, object]) -> tuple[Statement, str, bool]:
    """The statement, its sentence and its revocation flag out of a payload;
    `_FormError` says what is wrong."""
    kind = payload.get("policy")
    item: Statement
    match kind:
        case "circle":
            item = Circle(_text(payload, "name"))
        case "membership":
            item = Membership(_text(payload, "circle"), _text(payload, "member"))
        case "own_identity":
            item = OwnIdentity(_text(payload, "member"))
        case "rule":
            item = Rule(
                _text(payload, "scope"),
                _names(payload, "regions"),
                _days(payload, "max_retention_days"),
                _names(payload, "excluded_providers"),
                _flag_or_off(payload, "no_training"),
                _flag_or_off(payload, "no_subprocessors"),
                _names_or_empty(payload, "excluded_operators"),
                _names_or_empty(payload, "excluded_model_origins"),
            )
        case "client":
            item = Client(
                _text(payload, "name"), _text(payload, "processor"), _text(payload, "token_sha256")
            )
        case "provider":
            item = Provider(
                _text(payload, "provider"),
                _inference(payload),
                _names(payload, "storage"),
                _days(payload, "retention_days"),
                _flag(payload, "reports_inference_geo"),
                _flag(payload, "local"),
                _optional_text(payload, "operator"),
                _optional_flag(payload, "training"),
                _optional_names(payload, "subprocessors"),
                _optional_text(payload, "model_origin"),
            )
        case str():
            raise _FormError(f'is of the unknown kind "{kind}"')
        case _:
            raise _FormError("has no kind")
    sentence = _text(payload, "statement")
    revoked = _flag(payload, "revoked")
    _check(item, sentence)
    return item, sentence, revoked


def check_payload(payload: Mapping[str, object]) -> str | None:
    """What `verify` reports about the form of a policy payload, or `None`
    when it is sound.

    The write path would have refused anything found here: a finding means
    the event came another way.
    """
    try:
        _parse(payload)
    except _FormError as error:
        return f"has no valid form: it {error}"
    return None


def read_policy[Conn](log: LogStore[Conn], conn: Conn, *, at: datetime | None = None) -> Policy:
    """The policy in force: every policy event up to `at` (all of them
    without it), the newest per key, revocations lifted.

    An event whose payload was erased counts as nothing, and one whose form
    is broken is skipped as `verify` reports it; neither stops the read.
    """
    current: dict[tuple[str, str], tuple[Statement, int] | None] = {}
    for row in log.actions(conn, POLICY):
        payload = row.payload
        if payload is None or payload.get("action") != POLICY:
            continue
        if at is not None and row.recorded_at > at:
            continue
        try:
            item, _sentence, revoked = _parse(payload)
        except _FormError:
            continue
        current[key_of(item)] = None if revoked else (item, row.id)
    return _assemble(current)


def _assemble(current: Mapping[tuple[str, str], tuple[Statement, int] | None]) -> Policy:
    """The policy out of the newest statement per key."""
    circles: dict[str, Circle] = {}
    memberships: list[Membership] = []
    own: list[OwnIdentity] = []
    rules: dict[str, Rule] = {}
    providers: dict[str, Provider] = {}
    clients: dict[str, Client] = {}
    ids: dict[tuple[str, str], int] = {}
    for key in sorted(current):
        entry = current[key]
        if entry is None:
            continue
        item, event_id = entry
        ids[key] = event_id
        match item:
            case Circle(name=name):
                circles[name] = item
            case Membership():
                memberships.append(item)
            case OwnIdentity():
                own.append(item)
            case Rule(scope=scope):
                rules[scope] = item
            case Provider(name=name):
                providers[name] = item
            case Client(name=name):
                clients[name] = item
    return Policy(circles, tuple(memberships), tuple(own), rules, providers, ids, clients)
