# Task 7 report

Status: DONE. Commits: 72e7df2 (pages, handoff, map), 9967268 (tutorial retype).

## Pages written
- docs/explanation/graph.md (label `graph`), docs/how-to/keep-a-club-and-its-offices.md, docs/how-to/adapt-the-vocabulary.md (own page), docs/how-to/let-a-model-stand-for-a-class.md, docs/superpowers/handoffs/2026-10-14-kup6s-graph-phase-1.md.
## Pages changed
- explanation/assertions.md (third level pointer), explanation/processing-policy.md (recollection section), explanation/concurrency.md (new section, label `concurrency-graph`), explanation/index.md, how-to/index.md, docs/index.md, how-to/record-what-is-owed-and-decided.md and connect-claude-code-and-vibe.md (ask rule, Vibe note, fifteen tools), reference/environment.md (client row), reference/mcp-tools.md (one-bit residual under write_triage_answer), README.md (fifteen tools, graph bullet, command list now 34 and complete, "no people as entities" sentence replaced), .vale-styles/.../accept.txt (word Vellenfeld), landkarte.md, tutorial.
## Figures on pages and sources
- Verify 1,000 edges 0.57 s, 2,000 edges 1.77 s; post_in 2,000 0.56 s, 10,000 2.67 s: progress.md line 73 and task-4-report.md lines 232-235. NOTE: the brief called the post_in figures "post_in"; the source shows they are verify timings, so the page says `verify` over `post_in` relations. The 10,000-edge "about a minute" is the implementer's extrapolation, marked as not measured.
- whoami 53 ms at 1,000, 153 ms at 5,000 entities: task-6-report.md lines 335-336, progress.md line 97.
- 2026-10-14 for all; "final review measures again at 10,000 and 100,000" sentence left on graph.md and in the map.
- Hit-rate sample line in the class how-to (12 total ...) is an illustration, not a measurement.
- Club how-to commands and output (relations --at 2019-03-01, entity listing, classes add/list/revoke, vocabulary apply with `founded`): run by hand against PostgreSQL 18 in a scratch container on 2026-10-14; the output block shown is the real output. Container removed.
## Map count
- Before 220, after 225 (five top-level bullets in the new section *Zuordnungen (Phasen 1-4)*: residual, verify, header, deferred minors with four sub-bullets, phases 2-4). The flaky entry got the diagnosis, no new bullet. Also legend gained Z and P-Z1; "Wo das Projekt steht" and "Was als Nächstes kommt" updated.
## Gates (after the last edit)
- ruff check: all checks passed; ruff format --check: 135 files formatted; pyright 0 errors; lint-imports 9 kept, 0 broken.
- pytest --cov: 2616 passed, coverage 97.62 percent (run before the tutorial retype; no test or source file changed after). Plain `uv run pytest` run (seed 1126326222): 2616 passed in 263.05s, typed into the tutorial. test_docs_typed_output and test_docs_references: 32 passed after the retype.
- docs html: build succeeded, no warnings; vale 0 errors 0 warnings in 50 files; linkcheck build succeeded, 0 broken.
- pip-audit --skip-editable: no known vulnerabilities.
## Concerns
- The tutorial count did not change (2616): this task added no tests.
- `apply --base` retires kinds that the base file lacks and removes added fields (verified by hand); the adapt how-to and the handoff say so. The handoff therefore tells kup6s not to run it from a job.
- Two statements on the graph page are my reading and worth a reviewer's eye: that the header cost is "one fold per call" and that a write naming no source locks nothing (the latter follows from `events` being empty in `core/assertions.py`; graph_write was read from its docstring only).
- The ask-rule claim for write_triage_answer rests on mcp-tools.md (it carries the mark); only write_approve/write_reject were measured against Claude Code. Vibe keys for the new tool are unmeasured, like the old ones.
- Vale vocabulary: added `Vellenfeld` to accept.txt rather than rephrasing the example.
