**Verdict: Needs fixes.** The set algebra, the candidate checks, the address comparison, R-5 and R-6 are right. Two things are not. First, the region choice still implements the reading that R-7 overruled. Because of that, the decision is **not monotone**: one added rule makes it looser. I measured a concrete counterexample against the committed Hypothesis property. Second, the property covers only source rules, where R-8 asks for more. The test file also brings in two new `pyright: ignore` suppressions.

(R-6..R-8 were ruled after the implementer's report: progress.md:58-61 come after the "Task 3: implementer DONE_WITH_CONCERNS" line. So the R-7/R-8 gaps are expected rather than careless. They are still binding.)

### Spec Compliance

| Requirement | Status | Evidence |
|---|---|---|
| §2.2 domain without regard to case, local part exactly (Review Focus 2) | ✅ | decide.py:63-71 normalizes both sides; tests/test_decide.py:377-384 covers the upper-case domain hit and the local-part miss |
| §2.2 own identities removed before resolution (address and `@domain`) | ✅ | decide.py:76-82; tests 223-243 |
| R-5 membership counts only if its circle is in `Policy.circles` | ✅ | decide.py:88; test 401 |
| §2.5.3 circle without a rule, or no rule at all → `local_only` | ✅ | decide.py:190-195 |
| §2.5.4 intersection / minimum / union / `local_only` | ✅ | decide.py:104-111 (`any` drops out of the intersection, all-`any` → `{any}`), 197-199; test 150-167 |
| §2.5.5 candidate checks (excluded, local, storage or nothing stored, retention known and ≤ limit, inference ⊆ regions) | ✅ except the region choice | decide.py:133-177 |
| R-6 single declared space → `inference_geo = None` | ✅ | decide.py:123-124 |
| **R-7 widest fitting space; `{eu, us}` → Anthropic with `us`** | ❌ | decide.py:125-130 drops `us` unless `regions == {us}`. Measured: `decide(... rules=(source:email {eu,us}), candidates=[anthropic])` → `chosen=None`, reason `no inference space of anthropic lies within ['eu', 'us']`. test_decide.py:282-286 pins the overruled behavior |
| §2.5.6 no candidate → reason per candidate; `no local provider is declared` under `local_only` | ✅ | decide.py:203-204; test 102-108 pins the wording |
| §2.6 fallback `no_rule`, circles without a rule, empty when no rule at all | ✅ | decide.py:230; tests 92-99, 114-127, 362-371 |
| §8 points 1, 2, 4, 5, 6, 7 (decision level) | ✅ (5 needs the R-7 change for `{eu,us}`) | sections at test lines 89, 111, 220, 245, 329, 359 |
| **§8 point 3 + R-8: the property covers every kind of added rule except an involved circle's first rule** | ❌ partial | test 195-217: `extra` is only ever `source:email`. No uninvolved-circle rule, no "circle that has one" |
| Purity (no DB, clock or network) | ✅ | decide.py imports only `core.policy` and stdlib |
| Mutations measured red, control green | ⚠️ not verifiable here | report lists four; none for R-5 |
| Tutorial retyped from one run | ✅ arithmetically | 1118 + 28 = 1146 (diff lines 83, 133); I did not rerun it |

### Strengths

- The set algebra is correct and short. `_merge_regions` handles `any` as the universe without special cases downstream, and an empty intersection lets only a provider that stores nothing through and then fails it on inference (test 289-295).
- Unknown retention is checked only under a limit, and the reason names it (decide.py:157-163).
- Domain matching anchors on `@` (`endswith("@xz.at")`), so `evilxz.at` and `sub.xz.at` do not match (test 387-389).
- The tests pin the external wording `no local provider is declared` and the shape of `reasons` (1 + one per candidate).
- The report raised the region and property doubts openly, which is what produced R-7 and R-8.

### Issues

#### Critical
None.

#### Important

1. **The region choice implements the overruled reading, and that breaks "the strictest wins"** — src/previously/core/decide.py:125-130; tests/test_decide.py:282-286.
   *What:* `wanted` keeps a `{us}` space only when `regions == {us}`. R-7 says to take the widest of the spaces that lie wholly in `regions`, so `{eu, us}` → Anthropic with `us`.
   *Why it matters beyond R-7:* the filter is not monotone in `regions`. I measured it with the test module's own helpers (scratchpad chk4.py): a circle rule `{eu,us}` with no added rule passes `{mistral, local}`. Adding the source rule `{us}` passes `{anthropic}`. **One added rule lets out a provider that was not allowed before**, which violates §8 point 3 outright. The committed property test (line 200) would fail on exactly this input, and its 100 random examples did not hit it.
   *Fix:* drop the `(space.regions == us) == (regions == us)` filter. Rank `fitting` by width (`ANY` in the meaning first, then larger meaning, then name), and pass iff `fitting` is non-empty. Then `_space` is monotone: a smaller `regions` can only shrink `fitting`. Rewrite the docstring at 114-122 ("There is no ranking between regions" contradicts "the widest"). Invert test 282 to "Anthropic passes with `us`". Add `@example` for the counterexample above to the property (circle rule `{eu,us}`, no limit, nothing excluded, `bare=False`, extra `{us}`). Then measure: put the filter back, and the example goes red.

2. **The property covers only source rules (R-8)** — tests/test_decide.py:177-217.
   *What:* `extra` is always `Rule("source:email", ...)`, and the identities always involve every circle, so there is never an uninvolved one. R-8 asks for the other kinds too.
   *Fix:* draw the kind of the added rule, and assert the subset relation for each kind:
   - a source rule (as now);
   - a rule for an uninvolved circle: a circle with members that are not among the identities, with or without a prior rule;
   - the "circle that has one" case.
   *Ruling question for the controller:* in this model a scope holds exactly one rule (`Policy.rules` is keyed by scope, policy.py:121), so a further rule for a circle that already has one is a **replacement**. A replacement can loosen (`{eu}` → `{any}`), and no property can hold for it. A closer reading would be "the content comes to involve a further circle that has a rule". But that adds a membership, not a rule. R-8 needs a sentence on which of these it means before the implementer writes it.

3. **The property's skip goes beyond the exemption that R-8 and the spec name** — tests/test_decide.py:215-216; spec §8.3 (da6c574); R-8.
   *What:* the test skips baselines where no rule applied at all and no circle is involved. That skip is necessary: measured, `build()` passes `{local}`, and adding `source:email any` passes all three. §2.5 point 3 makes that loosening intended, because the first rule of all lifts `local_only` just as an involved circle's first rule does. But R-8 and the spec sentence of da6c574 name only the circle case. So the test carries an exemption that nothing in writing grants.
   *Fix (controller):* add "or it is the first rule that applies at all" to R-8 and the spec sentence. No code change. Until then, the skip is an exemption that nobody ruled.

4. **Two new suppressions in the test file** — tests/test_decide.py:225-226, `# pyright: ignore[reportArgumentType]`.
   *What:* these are the only pyright or type ignores in `src` and `tests` (grep). CLAUDE.md says "No `# type: ignore` … if the types do not work out, fix the types" and holds the suppression list at five. context.md says "keine neue Lint-Unterdrückung".
   *Fix:* pass the keyword arguments directly, as the neighbouring tests do: `build(circles=("klein",), memberships=(("klein", "@klein.at"),), own=(...))`. That removes the need for the suppressions entirely.

#### Minor

5. tests/test_decide.py:359: the section comment is cut off mid-word ("a real rule carr"). It also departs from the "Pilot assertion N" form of the other six sections.
6. tests/test_decide.py:398, `# --- Ruling R-5: …`: this ruling citation does not name its plan. CLAUDE.md asks for e.g. "ruling R-5 of the 2026-10-09 pilot gate plan". The ledger sits under `.superpowers/` and does not ship yet, and the census pattern `ruling (P|T[0-9]+)-…` does not catch `R-` labels. The reason does stand beside the label, so the comment holds without it. Either qualify the citation or drop the label.
7. R-5 has a direct test (line 401), which would go red without the filter at decide.py:88 by reading, but the report lists no mutation for it. Measure it once, with the control green.
8. decide.py:70: `and "@" in address` is redundant after `endswith(member)`, because `member` starts with `@`.
9. decide.py:123 with decide.py:171-175: the write path accepts a provider declared with an empty `inference` list (policy.py:268 loops over nothing). Such a provider never passes, and under `regions = {any}` the reason reads "no inference space of local lies within ['any']". That is conservative and correct, but a misdeclared local provider would surface with an odd sentence. Name it and do not chase it (only reachable by a mistaken declaration).

### Assessment

**Task quality: Needs fixes.** Fixes 1 and 4 are code changes for the implementer. Fix 2 needs the controller to make R-8 precise first (the replacement question), and fix 3 is a ruling and spec sentence for the controller. After fix 1, rerun the property with the added `@example`. Put the old filter back as a mutation, and it should go red.
