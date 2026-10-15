# Task 6 report

Commits: ce68779 (docs, handoff, map, README), 22b3dec (tutorial retyped).

Pages changed: docs/explanation/graph.md (stale "later phases" and "no table to fill" removed; new section graph-assignment: why concerns is declared, start is a source, in_circle never an assignment), README.md (assignments entry, "does not do" sentence), docs/superpowers/handoffs/2026-10-15-kup6s-graph-phase-2.md (new), docs/superpowers/landkarte.md, docs/tutorials/record-your-first-event.md (test block).
projections.md, the how-tos and the reference pages were already coherent after Tasks 3-5; commands in assign-mails-and-read-a-bracket.md checked against cli.md (relate --from-event, chronicle --within, error sentence), no output retyped.

Figures: map count 233 before, 242 after (9 new top-level points; the closed event-start point is struck but still counted). Tests: 2804 passed (two runs, 344 s and 345 s), coverage 97.77 %. Tutorial block from the second run (seed 42747105).
Gates: ruff check, ruff format --check, pyright 0 errors, lint-imports 9 kept, pytest, docs html/vale (0 errors, 51 files)/linkcheck (0 broken): green. pip-audit: no known vulnerabilities.

Concerns: the rolling-update advice. The a7 image has no graph projection, so a7 -> new does not itself make two versions rebuild each other; the handoff says so and gives the advice for every later update (ledger carry line states it generally).
Map "Erledigt" section not touched; the event-start point is struck in place.
Flakes did not occur.
