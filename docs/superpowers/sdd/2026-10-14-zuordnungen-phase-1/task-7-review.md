# Task 7 review

Spec: ✅ (one Important content defect)
Quality: Changes requested

Checked against the tree at head 9967268 (docs, code, rulings), not against the report.

## Findings

### Important
1. docs/superpowers/handoffs/2026-10-14-kup6s-graph-phase-1.md, section "One step after the image" (sentence "Run it again after an update whose notes say the base vocabulary changed"). `apply --base` treats the shipped file as the whole vocabulary and retires every kind the file lacks (`differences`/`_difference_lines` in `src/previously/cli.py`; adapt-the-vocabulary.md "After an update" says the same). The handoff itself says the maintainer adapts the vocabulary and that a job would undo it, then tells the maintainer to re-run the command after updates. For an operator with own kinds (the maintainer is the stated one) that retires them and removes added fields. The command prints the lines and asks first, so it is not silent, but the handoff gives no warning at that point and contradicts itself. Fix: say the re-run is only for an operator who has not adapted the vocabulary; otherwise apply their own file started from the new base. Same sentence, same defect, in docs/how-to/keep-a-club-and-its-offices.md "Apply the base vocabulary" ("Run it again after an update that changes the vocabulary"): add the caveat or point at adapt-the-vocabulary "After an update".

### Minor
2. docs/explanation/graph.md "What it costs" and handoff "The tool list grows": "its cost is the fold it needs for that count" / "one fold of the graph per call". The fold is once per call (`Service.answer`, server.py:926, `_FOLDED`), so "one fold" holds. But the same line also runs `objections_seen` (reads source events and decides the policy per objection), so the header costs more than the fold. The measured 53/153 ms covers both. Wording understates; say "the fold and the policy check of the objections".
3. docs/superpowers/landkarte.md, entry "`verify` ist quadratisch über azyklischen Ketten": the measurement is a factor of 3.1 per doubling (exponent about 1.6), not 4. graph.md says "faster than the number of edges", which is right; the map headline claims more. Say "überlinear".
4. docs/explanation/graph.md "What it costs" says "the rest are still to be taken" while the table lists 6 rows; fine, but "Phase 1 has the measurements below" is the only dating cue besides one sentence. Acceptable, no action required beyond wording.

## Claims checked
1. Header "one fold per call": holds (finding 2 on wording). "A write naming no source locks nothing": holds. `events` is built from claim sources; for none it is empty and `write_claims` takes no `lock_event` (graph_write.py `write_claims`).
2. Relabel to `verify` timings: correct. progress.md:73 and task-4-report.md:232-235 are `verify` timings. Page and map consistent. 3.1x per doubling and "about three times" hold. The 10,000-edge minute is marked as not measured.
3. Destructive `apply --base`: confirmed by code; see finding 1. Adapt page is correct and clear; handoff and club how-to are not.
4. Ask-rule claim for `write_triage_answer`: stated as the requirement, the "carries the mark" part rests on mcp-tools.md (which says so). Vibe keys are marked unmeasured. Acceptable as worded.

## Named risks
- Option check: 14 options spot-checked against the parsers in cli.py (`classes add --author --assertion --type --threshold --from --until --statement --yes`, `classes revoke --demote --statement`, `classes sample --count`, `relate --from --to --from-date --to-date --retract --subject --reason --recollection`, `relations --type --to --at --as-of`, `entity --field --name --history`, `answer --choose --reason`, `vocabulary apply FILE|--base --yes`). All exist as written. `--type` on `classes add` repeats (`action=append`), as used.
- Reason check: graph.md and the concurrency section hold against graph_write.py and the rulings. T6-a: acyclic kinds are never covered by a class, a model's open version is never refused for a cycle (`closes_cycle` returns False for OPEN), the approval is checked, residual is one bit behind the ask mark, also named for `write_triage_answer`. T2-b: direct/transitive checked against direct and transitive edges only, open edges may show in lists. T4-d: answer outside the candidates and (T4-g) retraction written open. Nothing claims more than the code. "Gate kinds never transitive" and "acyclic never covered" are kept as two separate statements.
- Handoff check: states requirements with "It stands when" checks; no cdk8s how; tool count fifteen holds (15 headings in mcp-tools.md, five new named correctly). Defect is finding 1 only.
- Map check: awk gives 225; the five new top-level bullets are German and each says what it is; sub-bullets are indented and not counted. Legend entries Z and P-Z1 added.
- README check: command list equals `COMMANDS` in cli.py, 34, same order; "thirty-four" matches. "fifteen tools" matches.
- Style: no multi-sentence lines found in the new pages; American English; one quadrant each (graph explanation, three how-tos).

## ⚠️ Not verified by me
- Typed output of the club how-to (ids 25-27, listing) is from the implementer's hand run; not re-run.
- Plan decision 12 text not read; concurrency claims were checked against graph_write.py's docstring and code.
- Docs gates not re-run, as instructed.
