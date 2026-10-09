# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The decision: which circles a content belongs to, which rules apply, which
candidate model may be called, and in which inference region.

A pure function of the policy, the people involved and the candidates: no
database, no clock, no network. Whatever is not explicitly allowed stays on
the machine, and the strictest rule wins. A policy that decides more loosely
than it was written looks exactly like working code, so every step below
errs towards "not allowed".
"""

from dataclasses import dataclass
from previously.core.policy import ANY
from previously.core.policy import LOCAL_ONLY
from previously.core.policy import normalize_member
from previously.core.policy import Policy
from previously.core.policy import Provider
from previously.core.policy import Rule
from typing import Final
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence


NO_RULE: Final = "no_rule"
NO_LOCAL_PROVIDER: Final = "no local provider is declared"


@dataclass(frozen=True)
class Candidate:
    provider: str
    model: str
    effort: str | None


@dataclass(frozen=True)
class Fallback:
    reason: str  # "no_rule"
    circles: tuple[str, ...]  # the circles without a rule; empty: no rule applied at all


@dataclass(frozen=True)
class Decision:
    circles: tuple[str, ...]
    rule_keys: tuple[str, ...]  # the scopes of the rules that applied, or `local_only`
    regions: frozenset[str]
    max_retention_days: int | None
    excluded_providers: frozenset[str]
    local_only: bool
    chosen: Candidate | None
    inference_geo: str | None  # None where the provider has no selectable space
    fallback: Fallback | None
    reasons: tuple[str, ...]  # one sentence per rejected candidate


def _matches(member: str, address: str) -> bool:
    """Whether `address` is the address `member`, or lies in the domain
    `member` names as "@domain". Domains compare without regard to case and
    local parts exactly (RFC 5321)."""
    member = normalize_member(member)
    address = normalize_member(address)
    if member.startswith("@"):
        return address.endswith(member)
    return member == address


def circles_of(policy: Policy, identities: Sequence[Mapping[str, object]]) -> tuple[str, ...]:
    """The circles a content belongs to: every circle that exists and has a
    member among the involved, own identities left out first."""
    addresses = [
        address
        for identity in identities
        if isinstance(address := identity.get("address"), str)
        and not any(_matches(own.member, address) for own in policy.own)
    ]
    return tuple(
        sorted(
            {
                membership.circle
                for membership in policy.memberships
                if membership.circle in policy.circles
                and any(_matches(membership.member, address) for address in addresses)
            }
        )
    )


def _inside(meaning: frozenset[str], regions: frozenset[str]) -> bool:
    """Whether a place or space with this `meaning` lies wholly in `regions`.

    `any` as the regions contains everything; `any` as a meaning lies only
    in `any`. A thing that means nothing (stores nothing) lies in any set.
    """
    return ANY in regions or meaning <= regions


def _merge_regions(rules: Sequence[Rule]) -> frozenset[str]:
    """The intersection of the regions; `any` is the whole set and drops out."""
    merged: frozenset[str] | None = None
    for rule in rules:
        if ANY in rule.regions:
            continue
        merged = rule.regions if merged is None else merged & rule.regions
    return frozenset({ANY}) if merged is None else merged


def _space(provider: Provider, regions: frozenset[str]) -> tuple[bool, str | None]:
    """Whether some inference space fits, and the one to set.

    A space fits if its meaning lies wholly in `regions`. Of the spaces that
    fit, the widest is set: one that means `any` first, then the larger
    meaning, then the name. The rules allow everything that fits, so the
    widest is the space they demand, and a narrower one would only cost more.
    A smaller `regions` can only shrink what fits, so a stricter rule never
    lets a provider through that a looser one stopped. A provider with a
    single space has nothing to select, so none is set.
    """
    fitting = [space for space in provider.inference if _inside(space.regions, regions)]
    if len(provider.inference) <= 1:
        return bool(fitting), None
    fitting.sort(key=lambda space: (ANY not in space.regions, -len(space.regions), space.name))
    return (True, fitting[0].name) if fitting else (False, None)


def _rejection(
    provider: Provider | None,
    candidate: Candidate,
    *,
    regions: frozenset[str],
    max_retention_days: int | None,
    excluded: frozenset[str],
    local_only: bool,
) -> tuple[str | None, str | None]:
    """The sentence that says why a candidate fails, or `None`; and the space
    to set when it passes."""
    name = f"{candidate.provider}/{candidate.model}"
    if provider is None:
        return f"{name}: no declaration for the provider {candidate.provider}", None
    if provider.name in excluded:
        return f"{name}: the provider {provider.name} is excluded by a rule", None
    if local_only and not provider.local:
        return f"{name}: the provider {provider.name} is not local, and only local applies", None
    if not _inside(provider.storage, regions):
        return (
            f"{name}: the provider stores in {sorted(provider.storage)}, "
            f"outside the allowed {sorted(regions)}",
            None,
        )
    if max_retention_days is not None:
        if provider.retention_days is None:
            return (
                f"{name}: the retention of {provider.name} is unknown, "
                f"and at most {max_retention_days} days are allowed",
                None,
            )
        if provider.retention_days > max_retention_days:
            return (
                f"{name}: the retention of {provider.name} is {provider.retention_days} days, "
                f"above the allowed {max_retention_days}",
                None,
            )
    fits, geo = _space(provider, regions)
    if not fits:
        return (
            f"{name}: no inference space of {provider.name} lies within {sorted(regions)}",
            None,
        )
    return None, geo


def decide(
    policy: Policy,
    *,
    identities: Sequence[Mapping[str, object]],
    source: str | None,
    candidates: Sequence[Candidate],
) -> Decision:
    """The decision for one content: the first candidate that every merged
    condition lets pass, or none."""
    circles = circles_of(policy, identities)
    scopes = [f"circle:{circle}" for circle in circles]
    if source is not None:
        scopes.append(f"source:{source}")
    rules = [policy.rules[scope] for scope in scopes if scope in policy.rules]
    without_rule = tuple(circle for circle in circles if f"circle:{circle}" not in policy.rules)
    # A circle without a rule, and no rule at all, both bring the built-in one.
    local_only = bool(without_rule) or not rules
    regions = _merge_regions(rules)
    limits = [r.max_retention_days for r in rules if r.max_retention_days is not None]
    max_retention_days = min(limits) if limits else None
    excluded: frozenset[str] = frozenset(name for r in rules for name in r.excluded_providers)
    rule_keys = tuple(rule.scope for rule in rules) + ((LOCAL_ONLY,) if local_only else ())

    reasons: list[str] = []
    if local_only and not any(p.local for p in policy.providers.values()):
        reasons.append(NO_LOCAL_PROVIDER)
    chosen: Candidate | None = None
    geo: str | None = None
    for candidate in candidates:
        sentence, space = _rejection(
            policy.providers.get(candidate.provider),
            candidate,
            regions=regions,
            max_retention_days=max_retention_days,
            excluded=excluded,
            local_only=local_only,
        )
        if sentence is not None:
            reasons.append(sentence)
        else:
            chosen, geo = candidate, space
            break
    return Decision(
        circles=circles,
        rule_keys=rule_keys,
        regions=regions,
        max_retention_days=max_retention_days,
        excluded_providers=excluded,
        local_only=local_only,
        chosen=chosen,
        inference_geo=geo,
        fallback=Fallback(NO_RULE, without_rule) if local_only else None,
        reasons=tuple(reasons),
    )
