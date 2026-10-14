# SDD ledger — plan: docs/superpowers/plans/2026-10-14-zuordnungen-phase-1.md

Spec: docs/superpowers/specs/2026-10-14-zuordnungen.md (Z), reviewed by the maintainer 2026-10-14.
Execution: subagent-driven, chosen by the maintainer 2026-10-14 ("eigenständig … subagent driven umsetzen und einen PR draus machen").
Cycle budget (maintainer's standing rule, memory "Zyklenbudget je Aufgabe"): per task at most ONE fix round + one Sonnet re-review; final review ONE fix wave + one re-review; residuals adjudicated with rulings.
Models: implementers/reviewers Opus for tasks 2, 4, 6; Sonnet otherwise; re-reviews Sonnet.
Code facts: code-facts.md in this directory (measured 2026-10-14 at 4aeb187).
Branch base: 90c6aa8 (main); plan commit 01eb4ac.

## Pre-flight scan

| Pair / task | Produces → consumes | Finding |
|---|---|---|
| T1 ↔ T3 | both add a name to KNOWN_ACTIONS and touch the same pinned tests/pages (test_action, test_access, test_docs_references, cli.md, policy-and-model-calls.md) | sequential; T3 extends what T1 changed. No conflict. |
| T1 → T2 | Vocabulary, KindSpec, FieldSpec, GATE_TYPES | consistent names. |
| T2 → T3 | ClassState (defined in graph.py), Graph, GraphVersion | T3 fills `Classes.states: Mapping[int, ClassState]`; consistent. |
| T2/T3 → T4 | Claim, fold_graph, conformance_problem, Classes.level, read_classes | consistent. T4 also extends verify (graph branch, rejection of graph versions) beyond T3's form-only check — intended. |
| T4 ↔ core/assertions.py | rejection `of` may name a graph version | T4 edits assertions.py; F unit-5 tests must stay green. |
| T1 ↔ T5 | both edit cli.py and the T201 tally in pyproject.toml | sequential; each re-measures. |
| T5 → T6 | PREVIOUSLY_LANGUAGE read in cli.py | the MCP server needs the language too, and plan T6 doesn't say how. **Ruling P-1 below.** |
| T4 → T6 | check_claims/write_claims(expect_levels), claim_verdict, relation_visible | consistent. |
| T6 ↔ T7 | INSTRUCTIONS, tool list, mcp-tools.md | T6 owns mcp-tools.md; T7 owns explanation/how-to; no overlap. |
| T1 self | creates vocabulary.toml + reads it via importlib.resources; hatchling `packages = ["src/previously"]` ships non-py files | test_wheel holds it. OK. |
| T2 self | Claim tests vs code | consistent. |
| T3 self | `sample` takes rng — SystemRandom satisfies "no mock for randomness" | OK. |
| T4 self | plan earlier implied a rejection with empty sources; fixed in 01eb4ac (proposals always have sources) | OK. |
| T5 self | file list names cli.py for settings | OK. |
| T6 self | tool count 10 → 15 | OK. |
| T7 self | spec stays alive (not frozen) in phase 1; cite Z as spec, not "frozen design record" | OK. |

Ruling P-1: the MCP server takes the display language as a parameter — `build_server(..., language: str = "en")` and `build_app` likewise; `previously mcp` and `serve` pass the `PREVIOUSLY_LANGUAGE` value that Task 5 reads. Task 6 makes that edit in cli.py. — the plan names the setting in T5 and labels in T6 but no path between them; a parameter keeps settings reading in cli.py like every other setting — if wrong, the server renders English labels only, which T6's tests would show.

## Tasks

Ruling P-2: the base vocabulary of phase 1 leaves out `concerns`, and declares `member_of` from `person` and `organization` only; `in_circle` stays a built-in with no entity start. — both start at an event or an address, which phase 1 refuses as a relation start (plan decision 4); declaring them with entity starts now would put a wrong connection into the log that phase 2/3 would have to retire — if wrong, phase 2 adds `concerns` with one `apply`, which the vocabulary is built for.

Task 1: dispatched (base 01eb4ac, Sonnet implementer)
Task 1: implemented 5432bc6 (DONE_WITH_CONCERNS: KNOWN_ACTIONS five names until T3; ref-to-relation refused at write; tutorial retyped early); review dispatched (Sonnet)
Task 1: minor (deferred): _text uses isprintable(), stricter than "no control characters" (refuses NBSP in labels)
Task 1: minor (deferred): refusal skips the reference check for built-ins — retiring `person` while built-in member_of names it is not refused; untested
Task 1: minor (deferred): a field ref to a relation kind is a write-time refusal, not a form error — verify can't flag such an event
Task 1: minor (deferred): Vocabulary.label takes one language; the PREVIOUSLY_LANGUAGE default step belongs to the consumer (T5/T6 must do it)
Task 1: minor (deferred): the "never raises" test asserts only None-or-str
Task 1: minor (deferred): tests/test_wheel.py builds the wheel a second time
Task 1: complete (commits 01eb4ac..5432bc6, review clean)
Ruling T2-a: in the graph model a transitive version whose class is revoked with demote, or whose `under` names no known class, counts as open; `objections()` are pending open versions contesting the *current* direct winner; `reaches` takes `extra` edges and `without` threads so the write path can check a batch. — plan decision 10 and Z §7.2 say what revoke/demote mean but not the unknown-class case; fail-safe means a statement nobody authorized stands for nothing; the batch arguments are what Task 4 needs for Review Focus 5 — if wrong, Task 4's tests show it.
Task 2: dispatched (base 5432bc6, Opus implementer)
Task 2: implemented bf43451..99a67dd (DONE_WITH_CONCERNS: conformance_problem needs entity_types; public level_of; reaches counts open proposals; answer-in-candidates and approval-copies left to T4); review dispatched (Opus)
Task 2: review: Spec ✅, Quality changes requested — 1 Important (I1 reaches counts open proposals), 6 Minor
Ruling T2-b (I1): `reaches` takes a level filter. An open write is checked against every standing edge; a direct or transitive write, and an approval, against direct and transitive edges only (level_of). `relations()` may therefore show a cycle that runs through an open edge; that is a proposal waiting, not a fact. — Z §7.1: a statement nobody authorized stands for nothing, so it can't block the operator; checking open writes against all edges keeps models from proposing cycles — if wrong, an approval of an open edge that closes a cycle is refused at approval time (Task 4 re-checks).
Ruling T2-c (M2): a later transitive version overtakes older open versions and answers a question, as a direct one does. — transitive stands for the operator by a class he set; Z §7.1 orders transitive above open; the operator corrects with a direct version — if wrong, questions answered by a confident model get no human look; the hit rate shows it.
Ruling T2-d (M1, M3, M5, M4, M6 in the same round): conformance treats a date value in a text or choice field as its ISO string, so the built claim and the parsed payload agree; a rejection counts only when its `of` names an open or transitive version; the event start of a relation is valid form and refused in conformance_problem with the same sentence (plan decision 4); the copied author rule uses the exported MAX_NAME_LENGTH and its test covers the boundary and the line separators, and the copied source checks get an equivalence test; the module docstring's claim about messages is made true.
Task 2: fix round 1/1 (7 addressed, 0 open — I1 reaches level filter, M1-M6; commits 99a67dd..1156411)
Task 2: deviation accepted: RelationBody.start is int | Source (event start is valid form, refused in conformance); consumers of relations() must skip a Source start
Task 2: complete (commits 5432bc6..1156411, review clean after one fix round)
Task 3: dispatched (base 1156411, Sonnet implementer)
Ruling T3-a: Classes.states maps every event id of a class name to the state of the name's latest event; level() takes the matching class with the highest threshold, then the oldest; hit_rates counts per class name with total = confirmed + corrected + standing. — the plan says a revocation reaches every version under the class (Z §7.2), which needs all event ids of a name; the tie-break makes the level deterministic and the strictest class decide — if wrong, the hit rate per name hides differences between a class's versions, which the sample still shows.
Task 3: implemented 516ba45 (deviations: level(type_name=), hit rate by written level, rejections count as corrected, sample without Classes, valid.from<until form rule); review dispatched (Sonnet)
Task 3: review: Spec ✅, Quality Approved — 0 Critical, 0 Important, 3 Minor; all 7 deviations accepted
Task 3: minor (deferred): hit_rates counts v1 as corrected when a later transitive v2 gets approved — follows the brief, unpinned
Task 3: minor (deferred): the tie-break "oldest" uses the newest event id per name, so a re-set class loses seniority over a twin
Task 3: minor (deferred): a test comment and a docstring ref are cosmetic
Task 3: complete (commits 1156411..516ba45, review clean)
Ruling T4-a: the write path sets a model claim's level (objection against a direct winner → open with contests; else Classes.level); operator claims must be direct; an answer to a pending question must name one of its candidates; the source check of unit 5 may become public and shared; verify checks graph claims against the vocabulary and classes at their own position in the chain. — Z §7.1/§7.4, plan decisions 9 and 13; sharing the source check keeps one sentence per refusal — if wrong, a reviewer will see a divergence between the two write paths.
Task 4: dispatched (base 516ba45, Opus implementer)
Task 4: implemented a93ee1b (DONE_WITH_CONCERNS). Reported deviations: batch cycle check by folding the batch (not `extra`); an approval may answer a question (to becomes a candidate); approving a new entity of a since-retired kind refused; bad source re-raised as GraphRefused; repeated handle returns stored claims. Concerns: verify quadratic in acyclic edges (1,000: 0.57 s, 2,000: 1.87 s); erasing a vocabulary/class event can make verify report claims of its time; Task 6 must refuse invisible ends with the same sentence.
Ruling T4-b: all five deviations stand, subject to review. — folding the batch makes verify and the write path ask the same question, and keeps objections and proposals of a batch out of the cycle check as T2-b requires; an answer as an approval is the only form in which write_triage_answer can be a model-authored direct version (F-6) — if wrong, the reviewer will show a case where the batch fold differs from `extra`.
Ruling T4-c: the final measurement (plan decision 14) also measures `verify` over acyclic edges at 10,000. — the implementer's extrapolation is a minute; verify runs daily as a CronJob in kup6s — if it doesn't carry, verify's cycle check becomes incremental in phase 2.
Task 4: review: Spec ❌, Quality changes requested — 1 Important (I1 a transitive version answers a question outside its candidates), 7 Minor; named risks (gate kinds, model direct, unit-5 unchanged, messages, verify, race) all hold
Ruling T4-d (I1): a model claim on a thread with a pending question whose `to` is none of its candidates is written `open`, never transitive, whatever its class. — a question exists because nobody was sure; an answer outside the candidates is new information a person should see (Z §7.3) — if wrong, a confident model's correct answer waits in triage, which costs one approval.
Ruling T4-e (minors in the same round): M1 expect_levels compares level, under and contests, and a changed contests refuses with its own sentence; M2 "new entity" for the retired-kind rule means a thread on which no direct or transitive version ever stood, for approvals of any version; M3 verify reports the three refusals it missed; M4 verify's graph pass stops copying the thread map per row; M5 verify and the write path treat a vocabulary or class event with units the same way; M6 the docstring in assertions.py says what that module reads; M7 a repeated handle matches only claims of its own write path.
Ruling T4-f: the operator who wants another answer than a pending question offers rejects the question first; no change. — it keeps one rule for answers; the CLI's `answer` and `reject` make it two commands — if wrong, Task 5 can offer `answer --other ID` later.
Task 4: fix commit dac79b0 — I1, M1-M7; expect is now Sequence[Decided(level, under, contests)]; verify timings: part_of chain 1,000 0.57 s / 2,000 1.77 s; post_in 2,000 0.56 s / 10,000 2.67 s (old copy 4.90 s)
Ruling T4-g: a model's retraction on a thread with a pending question is written open as well (the implementer's reading past the letter of T4-d) — it stands. — a retraction ends the thread, which answers the question as much as a `to` does; a person should see it — if wrong, a model's retraction waits for an approval.
Carry to Task 6: the confirm call must get the preview's Decided values sealed in the handle (confirm.py) and pass them as `expect`; the author of a claim is set by the server, never taken from the client.
Carry to Task 5: listings must show a relation that points at an erased entity as such.
Task 4: fix round 1/1 (8 addressed, 0 open — I1 question answers, M1-M7; commits a93ee1b..dac79b0)
Task 4: minor (deferred): a direct standing relation carrying candidates is refused on a thread with a pending question (pre-existing, out of scope of the fix)
Task 4: complete (commits 516ba45..dac79b0, review clean after one fix round)
Ruling T5-a: `answer N --choose ID` writes the approval of question N with `to = ID` (the question's author kept); `approve`/`reject` dispatch on the kind of the version; the display-language helper lives in core/vocabulary.py (`display_label`) so the MCP server can use it without importing cli. — Task 4 accepts an answer only in that form (T4-b deviation 2); one approve/reject for both kinds keeps the operator's habits — if wrong, Task 6 finds the helper missing and reports it.
Task 5: dispatched (base dac79b0, Sonnet implementer)
Task 5: implemented 0677488 (deviations: answer checks candidates itself with the write path's sentence; labels in listings; relations without proposals; class_refusal added to classes.py); review dispatched (Sonnet)
Task 5: review: Spec ✅, Quality changes requested — 1 Important (cli.md says twenty-five subcommands, COMMANDS has 34), 4 Minor, 3 ⚠️; named risks hold
Ruling T5-b (same round): the count and list on cli.md follow COMMANDS, and a docs test derives them so no page counts again by hand; `(none stands)` documented; `relate --retract` without `--subject` refused; "he" on cli.md becomes "the operator"; `approve` on a question id gets a test and a clear refusal; the type column showing the label stays (deferred minor) — CLAUDE.md "a comment is a claim" — a figure on a page drifts unless a test holds it — if wrong, a reader of cli.md undercounts once more.
Task 5: minor (deferred): the type column shows the label, so a listing can't feed --type directly (entity N shows both)
Task 5: fix commit 3a23a9b (5 findings)
Observed: the flaky `test_a_mail_that_carries_an_earlier_tag_does_not_close_the_fence[auto]` failed again, "in its own number check on a random fence tag" — likely the harness's `_text` refuses a number > 2^53 and a random tag can hold a long digit run. Not this branch's; goes to the map with that diagnosis (Task 7), the map already lists the flake.
Task 5: fix round 1/1 (5 addressed, 0 open; commits 0677488..3a23a9b)
Task 5: minor (deferred): `entity … --retract` without `--subject` may write a first version that is already retracted (re-reviewer, unchecked)
Task 5: complete (commits dac79b0..3a23a9b, review clean after one fix round)
Task 6: dispatched (base 3a23a9b, Opus implementer)
Task 6: implemented 830d2fe, 364a971 (deviations: list_entities(types=[]); claim_decisions in core; erased ends shown marked; three existing tests changed). Concerns: header count folds the graph each call (26 ms at 1,000 entities, 132 ms at 5,000); count from before a resolving write; visibility not re-checked at write; core/MCP differ on erased ends; count via a context variable. Review dispatched (Opus)
Task 6: review: Spec ✅, Quality changes requested — 2 Important (I1 cycle refusal in a preview reveals hidden paths; I2 list_triage shows placeholders and ids of hidden threads only when something waits), 5 Minor, 7 ⚠️; named risks 2-6 hold, 1 holds except I1/I2
Ruling T6-a (I1, replaces part of T2-b): a model's version is never refused for closing a cycle, so no refusal tells a client about edges it can't see. To keep the graph sound: (1) a relation type with behaviour `acyclic` is never covered by an approval class — `set_class` refuses it and `Classes.level` gives open for it — so a model's version of it is always open; (2) the cycle check applies to direct versions, to approvals and to the operator, over direct and transitive edges, as before; verify follows the same rule (a model's open version that closes a cycle is no finding). Residual, documented on mcp-tools.md and in the map: `write_approve` of such a proposal over MCP is refused for the cycle, which tells a person-confirmed call one bit. — Z §9.4 orders confidentiality before availability; the leak was a free, repeatable probe through previews; what remains needs the ask mark and a person — if wrong, `part_of` can't be assigned by a class in phase 1, which costs approvals, not safety.
Ruling T6-b (I2): list_triage shows only what the client may see; the section of withheld waiting items goes. — the header already counts only visible objections; a placeholder that appears when someone writes on a hidden thread is a signal — if wrong, the operator sees the rest on the command line.
Ruling T6-c (minors, same round): M1 the access entry records the circles of the versions on mails; M2 an MCP test for Review Focus 1; M3 one rule for a relation's visibility, in core, used by MCP, with the erased-end behaviour MCP has; M4 the always-true assert replaced by a check that nothing was written; M5 the graph is read once per call. And the header's cost joins the final measurement (with T4-c) at 10,000 and 100,000 relations.
Task 6: fix commits f9ff79c, fc0d6f0 (I1, I2, M1-M5); whoami 53 ms at 1,000 / 153 ms at 5,000 entities; map entry for the T6-a residual left to Task 7
Task 6: fix round 1/1 (7 addressed, 0 open — I1, I2, M1-M5; commits 364a971..fc0d6f0)
Task 6: minor (deferred → Task 7): mcp-tools.md documents the one-bit cycle residual under write_approve only; write_triage_answer has it too
Task 6: minor (deferred): ThreadVerdict docstring says an event-start relation has no `blocked`, the code doesn't clear it (unused for relations)
Task 6: complete (commits 3a23a9b..fc0d6f0, review clean after one fix round)
Task 7: dispatched (base fc0d6f0, Sonnet implementer)
Task 7: implemented 72e7df2, 9967268 (map 220 → 225). Concern of weight: `vocabulary apply --base` treats the base file as the whole vocabulary and retires the operator's own kinds — the handoff's "again after an update" would do that. Goes to the final review as a design question.
Ruling F-a (for the final fix wave): `vocabulary apply --base` adds the base kinds that don't exist yet and changes nothing else: it never retires and never overwrites a kind the log already holds; where the base differs from what stands, it names the kind and says to take it with show → edit → apply. Retiring stays with an explicit file. The handoff and the adapt how-to follow. — Z §4.3: the base vocabulary "is never applied silently", and an update must not take the operator's own kinds and fields — if wrong, a changed base kind reaches the log one manual apply later.
Task 7: review: Spec ✅, Quality changes requested — 1 Important (handoff and club how-to tell the operator to re-run `apply --base` after an update, which retires own kinds), 3 Minor
Ruling T7-a: the Important finding and the three minors go into the final fix wave together with ruling F-a (the code change to `--base` that removes the danger), instead of a separate fix round now — fixing the docs alone would document a trap the code should not have — if wrong, the final wave carries one more item.
Task 7: minor (→ final wave): "one fold per call" understates the header cost (objections_seen decides policy per objection)
Task 7: minor (→ final wave): the map calls verify "quadratisch"; measured ~3.1× per doubling — superlinear
Task 7: minor (→ final wave): wording on graph.md's cost section
Task 7: complete (commits fc0d6f0..9967268; Important carried to the final wave by T7-a)
Final review: dispatched (Opus, whole-branch source diff 01eb4ac..9967268) in parallel with the measurement (Sonnet, scratch only)
Reboot overnight 2026-10-14/15: final review and measurement stopped. Final review had written nothing. The measurement had written results into the worktree root (moved to scratchpad/measure): 2,000 and 10,000 relations done, 100,000 not. Medians at 10,000 relations (5,000 entities): read_graph 0.47 s; CLI entities 0.53 s; one write 0.47 s; verify 2.77 s, clean; MCP whoami 0.52 s, list_entities 1.72 s; with 20 objections the same. At 2,000: read 0.08 s, whoami 0.10 s, list_entities 0.28 s, verify 0.62 s. Linear growth. Leftover testcontainer distracted_mcnulty removed.
Final review: ready to merge after the fix wave — 0 Critical, 2 Important (I1 gate kinds approvable over MCP; I2 header folds the whole graph per call), 12 Minor; gate untouched, unit-5 tests not weakened, T201 96 holds.
Ruling F-b (I1): a statement about a gate kind (circle, member_of, in_circle) becomes direct only on the command line; `write_approve` and `write_triage_answer` refuse it with one sentence, and the fold counts a transitive gate-kind row as open (M1). — Z §7.6.1: the gate's membership must not stand on a model's word; the ask mark is advisory ("don't ask again") — if wrong, the operator approves memberships on the CLI, which the phase-3 design asks anyway.
Ruling F-c (I2): the header's whole-graph fold stays in phase 1; graph.md and the map state the measured cost (10,000 relations: whoami 0.52 s, list_entities 1.72 s) and that phase 2 needs a projection or an incremental fold before data grows. — a cache keyed on the tip is invalidated by every call's own access entry; an incremental fold at the security boundary is too much for a fix wave; the pilot holds hundreds of claims, where the cost is milliseconds — if wrong, MCP slows down as the pilot grows, visibly and before it hurts.
Ruling F-d (minors): fix now — M1, M2, M6, M7, M9 (classes.py's copy of the identifier/author rule must equal the shared one), M10, M11, M12, and the Task 7 minors; strike Task 4's candidates case (can't happen); map — M3, M4, M5, M8, the placeholder that vanishes when a hidden entity's last proposal is rejected, and the remaining deferred minors as the review triaged them.
Final fix wave: dispatched (base 9967268, Opus fixer, one wave for F-a, F-b, F-c, F-d, T7-a)
VSCodium restart 2026-10-14: fix wave had committed 1f802ef, b75af5e, 1b5fbf4, 22d571e, 8613d6c (tree clean) without its report; measurement had verify part_of chain 1,000 0.84 s / 2,000 2.34 s / 5,000 14.84 s, tree 0.78 / 2.10 / 13.05 s (≈ quadratic). Both resumed; measurement on a fixed detached checkout of 9967268. The 100,000 figures (reads 7.3 s, write 7.0 s, verify 126 s) are provisional: taken while the fix wave edited the tree.
Measurement complete (fixed tree 9967268 where marked): 100,000 relations — read_graph 7.35 s, verify 135 s (single), MCP whoami 7.69 s, list_entities 23.7 s; CLI lists 7.5 s and one write 7.3 s (first run); part_of chain 10,000 edges verify 78.6 s (single). Verify clean everywhere. Results: scratchpad/measure/results.md. Sent to the fixer for graph.md and the map.
Final fix wave: done 1f802ef..992029c (2645 passed; map 225 → 233); re-review dispatched (Sonnet)
