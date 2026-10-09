# Previously — an append-only knowledge store for project histories
# Copyright (C) 2026 Jens W. Klein
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The decision: circles, merged rules, candidates, region and fallback.

Every test builds a `Policy` from values. The function is pure, so there is
no database to start.
"""

from hypothesis import example
from hypothesis import given
from hypothesis import strategies as st
from previously.core.decide import Candidate
from previously.core.decide import circles_of
from previously.core.decide import decide
from previously.core.decide import NO_LOCAL_PROVIDER
from previously.core.policy import ANY
from previously.core.policy import Circle
from previously.core.policy import Inference
from previously.core.policy import LOCAL_ONLY
from previously.core.policy import Membership
from previously.core.policy import OwnIdentity
from previously.core.policy import Policy
from previously.core.policy import Provider
from previously.core.policy import Rule


ANTHROPIC = Provider(
    "anthropic",
    (Inference("global", frozenset({ANY})), Inference("us", frozenset({"us"}))),
    frozenset({"us"}),
    30,
    True,
    False,
)
MISTRAL = Provider(
    "mistral", (Inference("eu", frozenset({"eu"})),), frozenset({"eu"}), None, False, False
)
LOCAL = Provider("local", (Inference("eu", frozenset({"eu"})),), frozenset(), 0, False, True)
PROVIDERS = (ANTHROPIC, MISTRAL, LOCAL)

CANDIDATES = (
    Candidate("anthropic", "claude-haiku-5-5", "low"),
    Candidate("mistral", "mistral-small-2603", None),
    Candidate("local", "qwen3:4b", None),
)


def rule(
    scope: str,
    regions: set[str],
    *,
    days: int | None = None,
    excluded: set[str] | None = None,
) -> Rule:
    return Rule(scope, frozenset(regions), days, frozenset(excluded or ()))


def build(
    *,
    circles: tuple[str, ...] = (),
    memberships: tuple[tuple[str, str], ...] = (),
    own: tuple[str, ...] = (),
    rules: tuple[Rule, ...] = (),
    providers: tuple[Provider, ...] = PROVIDERS,
) -> Policy:
    return Policy(
        {name: Circle(name) for name in circles},
        tuple(Membership(circle, member) for circle, member in memberships),
        tuple(OwnIdentity(member) for member in own),
        {item.scope: item for item in rules},
        {item.name: item for item in providers},
        {},
    )


def who(*addresses: str) -> list[dict[str, object]]:
    return [{"channel": "email", "role": "from", "address": a, "name": None} for a in addresses]


def passing(policy: Policy, identities: list[dict[str, object]], source: str | None) -> set[str]:
    return {
        candidate.provider
        for candidate in CANDIDATES
        if decide(policy, identities=identities, source=source, candidates=[candidate]).chosen
        is not None
    }


# --- Pilot assertion 1: no rule, local only ---


def test_no_rule_means_local_only_and_the_fallback_is_marked() -> None:
    decision = decide(build(), identities=who("x@y.at"), source="email", candidates=CANDIDATES)
    assert decision.local_only
    assert decision.chosen == CANDIDATES[2]
    assert decision.fallback is not None
    assert decision.fallback.reason == "no_rule"
    assert decision.fallback.circles == ()
    assert decision.rule_keys == (LOCAL_ONLY,)


def test_no_rule_and_no_local_provider_rejects_with_the_reason() -> None:
    policy = build(providers=(ANTHROPIC, MISTRAL))
    decision = decide(policy, identities=[], source="email", candidates=CANDIDATES)
    assert decision.chosen is None
    assert decision.inference_geo is None
    assert decision.reasons[0] == NO_LOCAL_PROVIDER == "no local provider is declared"
    assert len(decision.reasons) == 1 + 3  # the sentence, then one per candidate


# --- Pilot assertion 2: a circle without a rule ---


def test_a_circle_without_a_rule_makes_it_local_only_beside_an_open_one() -> None:
    policy = build(
        circles=("open", "bare"),
        memberships=(("open", "@open.at"), ("bare", "@bare.at")),
        rules=(rule("circle:open", {ANY}),),
    )
    decision = decide(
        policy, identities=who("a@open.at", "b@bare.at"), source="email", candidates=CANDIDATES
    )
    assert decision.circles == ("bare", "open")
    assert decision.local_only
    assert decision.chosen == CANDIDATES[2]
    assert decision.fallback is not None
    assert decision.fallback.circles == ("bare",)


def test_a_circle_without_a_rule_beats_an_open_source_rule() -> None:
    policy = build(
        circles=("bare",),
        memberships=(("bare", "@bare.at"),),
        rules=(rule("source:email", {ANY}),),
    )
    decision = decide(policy, identities=who("b@bare.at"), source="email", candidates=CANDIDATES)
    assert decision.chosen == CANDIDATES[2]


def test_an_unknown_address_binds_nothing_and_an_open_source_rule_lets_it_out() -> None:
    policy = build(rules=(rule("source:email", {ANY}),))
    decision = decide(policy, identities=who("who@else.at"), source="email", candidates=CANDIDATES)
    assert decision.fallback is None
    assert decision.chosen == CANDIDATES[0]


# --- Pilot assertion 3: the strictest rule wins ---


def test_regions_are_intersected_and_the_rest_merges_strictly() -> None:
    policy = build(
        circles=("a", "b"),
        memberships=(("a", "@a.at"), ("b", "@b.at")),
        rules=(
            rule("circle:a", {"eu", "us"}, days=30, excluded={"mistral"}),
            rule("circle:b", {"eu"}, days=7, excluded={"anthropic"}),
        ),
    )
    decision = decide(
        policy, identities=who("x@a.at", "y@b.at"), source=None, candidates=CANDIDATES
    )
    assert decision.regions == frozenset({"eu"})
    assert decision.max_retention_days == 7
    assert decision.excluded_providers == frozenset({"anthropic", "mistral"})
    assert decision.chosen == CANDIDATES[2]  # only the local provider is left
    assert decision.rule_keys == ("circle:a", "circle:b")


_REGION_SETS = st.sampled_from(
    [frozenset({"eu"}), frozenset({"us"}), frozenset({"eu", "us"}), frozenset({ANY})]
)
_RULE_VALUES = st.tuples(
    _REGION_SETS,
    st.none() | st.integers(min_value=0, max_value=60),
    st.frozensets(st.sampled_from(["anthropic", "mistral", "local"])),
)


type _Values = tuple[frozenset[str], int | None, frozenset[str]]


def _policy_of(
    circle_rules: list[_Values],
    bare: bool,
    *,
    source: _Values | None = None,
    more: _Values | None = None,
    far: _Values | str | None = None,
) -> tuple[Policy, list[dict[str, object]]]:
    """A policy and the people involved.

    `bare` adds an involved circle without a rule, `source` a rule for the
    source, `more` a further involved circle with its rule, and `far` a
    circle whose members are not involved: `"bare"` without a rule, or with
    the rule given.
    """
    names = [f"c{index}" for index in range(len(circle_rules))] + (["bare"] if bare else [])
    rules = [Rule(f"circle:c{i}", *values) for i, values in enumerate(circle_rules)]
    involved = list(names)
    if source is not None:
        rules.append(Rule("source:email", *source))
    if more is not None:
        names.append("more")
        involved.append("more")
        rules.append(Rule("circle:more", *more))
    if far is not None:
        names.append("far")
        if far != "bare":
            assert not isinstance(far, str)
            rules.append(Rule("circle:far", *far))
    policy = build(
        circles=tuple(names),
        memberships=tuple((name, f"@{name}.at") for name in names),
        rules=tuple(rules),
    )
    return policy, who(*(f"x@{name}.at" for name in involved))


@given(
    circle_rules=st.lists(_RULE_VALUES, max_size=3),
    bare=st.booleans(),
    kind=st.sampled_from(["source", "uninvolved", "further"]),
    extra=_RULE_VALUES,
)
@example(  # a rule {eu,us} lets mistral and local out; a source rule {us} must not add anthropic
    circle_rules=[(frozenset({"eu", "us"}), None, frozenset())],
    bare=False,
    kind="source",
    extra=(frozenset({"us"}), None, frozenset()),
)
def test_adding_a_rule_never_widens_the_passing_candidates(
    circle_rules: list[_Values], bare: bool, kind: str, extra: _Values
) -> None:
    """Pilot assertion 3 (point 3 of the specification's assertions, "adding a rule").

    Three ways to add a rule for a scope that has none yet: a source rule
    beside rules that already apply, a rule for a circle nobody involved
    belongs to, and a further involved circle together with its membership
    and rule. Two cases are left out on purpose, because they lift the
    built-in `local_only` and loosen the decision as designed: the first
    rule of an involved circle (that is `bare` here, which never gets one),
    and the first rule that applies at all. Replacing a rule is no addition
    and may loosen.
    """
    before, ids_before = _policy_of(
        circle_rules, bare, far="bare" if kind == "uninvolved" else None
    )
    baseline = decide(before, identities=ids_before, source="email", candidates=CANDIDATES)
    if baseline.fallback is not None and baseline.fallback.circles == ():
        return  # the first rule that applies at all
    if kind == "source":
        after, ids_after = _policy_of(circle_rules, bare, source=extra)
    elif kind == "uninvolved":
        after, ids_after = _policy_of(circle_rules, bare, far=extra)
    else:
        after, ids_after = _policy_of(circle_rules, bare, more=extra)
    assert passing(after, ids_after, "email") <= passing(before, ids_before, "email")


# --- Pilot assertion 4: own identities do not count ---


def test_own_identities_are_removed_before_the_circles_resolve() -> None:
    circles = ("klein",)
    memberships = (("klein", "@klein.at"),)
    with_own = build(circles=circles, memberships=memberships, own=("jens@klein.at",))
    without = build(circles=circles, memberships=memberships)
    assert circles_of(with_own, who("jens@klein.at")) == ()
    assert circles_of(without, who("jens@klein.at")) == ("klein",)


def test_an_own_domain_removes_every_address_in_it() -> None:
    policy = build(circles=("klein",), memberships=(("klein", "@klein.at"),), own=("@Klein.at",))
    assert circles_of(policy, who("anyone@KLEIN.at")) == ()


def test_an_own_identity_still_leaves_the_other_involved() -> None:
    policy = build(
        circles=("xz",),
        memberships=(("xz", "@xz.at"),),
        own=("jens@klein.at",),
    )
    assert circles_of(policy, who("jens@klein.at", "eva@xz.at")) == ("xz",)


# --- Pilot assertion 5: where each region leads ---


def test_eu_leads_to_mistral_without_a_selectable_space() -> None:
    decision = decide(
        build(rules=(rule("source:email", {"eu"}),)),
        identities=[],
        source="email",
        candidates=CANDIDATES,
    )
    assert decision.chosen == CANDIDATES[1]
    assert decision.inference_geo is None


def test_anywhere_leads_to_anthropic_with_global() -> None:
    decision = decide(
        build(rules=(rule("source:email", {ANY}),)),
        identities=[],
        source="email",
        candidates=CANDIDATES,
    )
    assert decision.chosen == CANDIDATES[0]
    assert decision.inference_geo == "global"
    assert decision.fallback is None


def test_us_leads_to_anthropic_with_us() -> None:
    decision = decide(
        build(rules=(rule("source:email", {"us"}),)),
        identities=[],
        source="email",
        candidates=CANDIDATES,
    )
    assert decision.chosen == CANDIDATES[0]
    assert decision.inference_geo == "us"


def test_eu_and_us_together_let_anthropic_pass_with_the_widest_fitting_space() -> None:
    # `global` lies outside {eu, us}; `us` is the widest space that lies within.
    policy = build(rules=(rule("source:email", {"eu", "us"}),))
    assert passing(policy, [], "email") == {"anthropic", "mistral", "local"}
    decision = decide(policy, identities=[], source="email", candidates=[CANDIDATES[0]])
    assert decision.inference_geo == "us"


def test_disjoint_regions_pass_only_what_stores_nothing_and_fits_no_space() -> None:
    policy = build(
        circles=("a", "b"),
        memberships=(("a", "@a.at"), ("b", "@b.at")),
        rules=(rule("circle:a", {"eu"}), rule("circle:b", {"us"})),
    )
    assert passing(policy, who("x@a.at", "y@b.at"), None) == set()


def test_a_provider_that_stores_nothing_passes_any_regions() -> None:
    nowhere = Provider(
        "nowhere", (Inference("us", frozenset({"us"})),), frozenset(), 0, False, False
    )
    policy = build(rules=(rule("source:email", {"us"}),), providers=(nowhere,))
    decision = decide(
        policy, identities=[], source="email", candidates=[Candidate("nowhere", "m", None)]
    )
    assert decision.chosen is not None


def test_local_only_lets_only_a_local_provider_pass() -> None:
    assert passing(build(), [], "email") == {"local"}


def test_an_undeclared_provider_is_rejected_by_name() -> None:
    decision = decide(
        build(rules=(rule("source:email", {ANY}),)),
        identities=[],
        source="email",
        candidates=[Candidate("ghost", "m", None)],
    )
    assert decision.chosen is None
    assert "ghost" in decision.reasons[0]


def test_an_excluded_provider_is_rejected() -> None:
    policy = build(rules=(rule("source:email", {ANY}, excluded={"anthropic"}),))
    assert passing(policy, [], "email") == {"mistral", "local"}


# --- Pilot assertion 6: unknown retention passes no limit ---


def test_unknown_retention_fails_a_limit_and_the_reason_says_so() -> None:
    policy = build(rules=(rule("source:email", {"eu"}, days=30),))
    decision = decide(policy, identities=[], source="email", candidates=[CANDIDATES[1]])
    assert decision.chosen is None
    assert "unknown" in decision.reasons[0]


def test_unknown_retention_passes_when_no_limit_applies() -> None:
    policy = build(rules=(rule("source:email", {"eu"}),))
    assert passing(policy, [], "email") == {"mistral", "local"}


def test_zero_retention_leaves_only_the_local_provider() -> None:
    policy = build(rules=(rule("source:email", {ANY}, days=0),))
    assert passing(policy, [], "email") == {"local"}


def test_a_known_retention_above_the_limit_fails() -> None:
    policy = build(rules=(rule("source:email", {ANY}, days=29),))
    decision = decide(policy, identities=[], source="email", candidates=[CANDIDATES[0]])
    assert decision.chosen is None
    assert "30" in decision.reasons[0]
    assert passing(build(rules=(rule("source:email", {ANY}, days=30),)), [], "email") >= {
        "anthropic"
    }


# --- Pilot assertion 7: the fallback is marked, a real rule carries none ---


def test_a_real_rule_carries_no_fallback() -> None:
    policy = build(
        circles=("xz",),
        memberships=(("xz", "@xz.at"),),
        rules=(rule("circle:xz", {"eu"}),),
    )
    decision = decide(policy, identities=who("e@xz.at"), source="email", candidates=CANDIDATES)
    assert decision.fallback is None
    assert not decision.local_only
    assert LOCAL_ONLY not in decision.rule_keys


# --- Review focus 2: how addresses compare -----------------------------------------------


def test_the_domain_compares_without_case_and_the_local_part_exactly() -> None:
    policy = build(
        circles=("xz",),
        memberships=(("xz", "@kunde-xz.at"), ("xz", "Eva.Huber@Other.at")),
    )
    assert circles_of(policy, who("Eva.Huber@Kunde-XZ.at")) == ("xz",)
    assert circles_of(policy, who("eva.huber@OTHER.AT")) == ()
    assert circles_of(policy, who("Eva.Huber@OTHER.AT")) == ("xz",)


def test_a_domain_membership_does_not_match_a_longer_domain() -> None:
    policy = build(circles=("xz",), memberships=(("xz", "@xz.at"),))
    assert circles_of(policy, who("a@evilxz.at", "b@sub.xz.at", "xz.at")) == ()


def test_an_involved_without_an_address_is_skipped() -> None:
    policy = build(circles=("xz",), memberships=(("xz", "@xz.at"),))
    identities: list[dict[str, object]] = [{"channel": "email", "role": "from", "address": None}]
    assert circles_of(policy, identities) == ()


# --- Ruling R-5 of the 2026-10-09 gate plan: only a circle that exists has members ---


def test_a_membership_in_a_circle_that_does_not_exist_counts_for_nothing() -> None:
    policy = build(circles=(), memberships=(("gone", "@xz.at"),))
    assert circles_of(policy, who("e@xz.at")) == ()
