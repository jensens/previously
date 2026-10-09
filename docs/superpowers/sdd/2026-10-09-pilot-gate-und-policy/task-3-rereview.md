# Task 3 re-review (5a2fa6f..26f4cb4)

### Finding Verdicts
1. ADDRESSED. src/previously/core/decide.py `_space`: fitting spaces sorted `any` first, larger meaning, name; `us` filter gone. Monotone by construction (smaller `regions` only shrinks `fitting`). {eu,us} gives Anthropic with `us` (tests/test_decide.py, test_eu_and_us_together_let_anthropic_pass_with_the_widest_fitting_space, asserts geo `us`). Counterexample is an `@example` (kind="source", circle rule {eu,us}, extra {us}); with the old filter the circle-only baseline passes {mistral, local} and the after case adds anthropic, so it goes red (report: 2 red).
2. ADDRESSED. tests/test_decide.py `test_adding_a_rule_never_widens_the_passing_candidates`: `kind` in source / uninvolved / further. `uninvolved` builds the baseline with a rule-less `far` circle and gives it the rule afterwards; `further` adds "more" with membership, involvement and rule. The docstring names both exemptions (an involved circle's first rule, the first rule that applies at all); the code skips the latter via `fallback.circles == ()` and `bare` never gets a rule.
3. ADDRESSED. grep for `pyright: ignore|type: ignore|noqa` in tests/test_decide.py: no match.
4. ADDRESSED. Section comment at assertion 7 completed; R-5 heading at tests/test_decide.py:441 names "the 2026-10-09 gate plan"; report records the R-5 mutation (1 red, control green); `"@" in address` dropped in `_matches`.

### New Breakage in the Fix Diff
None found. Small note: the `uninvolved` case is trivially equal before/after (an uninvolved circle cannot affect the decision), which is the intended check, not a defect.

### Out-of-Scope Observations
Empty `inference` list never passes (already named as minor in progress.md). Not re-run: the suite (per instructions); verified by reading the generator.

### Verdict — all findings addressed: yes
