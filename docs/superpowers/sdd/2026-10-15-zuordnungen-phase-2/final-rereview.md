# Final re-review of the fix wave 22b3dec..9ad6eeb

1. I-1 ADDRESSED. src/previously/cli.py `_caught_up` and src/previously/mcp_server/server.py `Service.caught_up` catch `(PreviouslyError, StorageError)`. Gap tests: tests/test_cli.py `test_a_listing_folds_the_log_when_its_catch_up_meets_a_gap_in_the_log` and the `gap` case of tests/test_mcp_server.py (`whoami` and `get_event` are in its call list, and the case asserts the cause text). The store reads without the first event on a batched read, so `ProjectionGap` is raised. Without the broader tuple it escapes (not re-run by me).
2. I-2 ADDRESSED. tests/test_members.py:124, 198, 322, 441 name "the 2026-10-15 assignments plan, phase 2". Census plus the diff against main: every ruling label added in phase 2 names its plan (T2-a, T2-c/d/e/f, T4-b, T5-c, T6-c, T9-c). Older bare labels were not touched.
3. M-1 ADDRESSED. tests/test_projection_graph.py `_Holding` holds every batch with `up_to_id > 0` until the second catch-up waits on a lock or is done. Reasoning: the second is queued whenever the first commits, so the first cannot take the next batch ahead of it; the second therefore gets at least the last batch, and the first gets batch 1. The asserts `>= 2` each hold by construction. Residual: there is no guard against `_waiting_on_a_lock` counting another waiter in the same database, which is unlikely in this test.
4. M-2 ADDRESSED. cli.py: `_claim_fields` and `_period_text` are gone, and `_entity_fields(body: EntityBody)` is called with a `cast`. The cast is argued in a comment: `_show_entity` hands over entity threads only. Output of the entity branch is identical (type, language, fields, state).
5. M-8 and docs minors ADDRESSED.
   - Struck event-start point: landkarte.md:1643.
   - projections.md:348 ("the walk that finds ...", plus the added sentence on the thread folded around it).
   - Period dates in the "no content" sentences: graph.md, projections.md (intro and the graph section), handoff, README.
   - Handoff wording: the `project` line now covers `caught up:` and `up to date`; the compose paragraph is rewritten.
   - vocabulary.md bullets are one sentence per line.
6. Handoff ADDRESSED. Section "Every reader catches the projection up first" covers: project after an upgrade or a bulk ingest, the lock without a timeout, write access for readers (SELECT/INSERT/UPDATE/DELETE on three tables, with reason), and `project --check` scheduled with an alarm on exit 1. It states requirements with reasons. kup6s is named only as the example (its single owner role) and for its CronJob; no cdk8s.
7. Map ADDRESSED. awk gives 245 (claim matches). Present: M-3 (l.656), M-4 (l.577), M-5 (l.666), M-6 (l.673), the re-assignment hint (l.676), the lock (l.683), measured points, and the misleading `MigrationPending` (l.754). Erledigt (l.1643+) holds the struck event-start point, ProjectionGap, the `whoami` header cost, and the "Zurückgestellte Kleinigkeiten". The line counts quoted (4,483 for cli.py, 3,245 for server.py) differ from HEAD (4,476 and 3,251); see below.
8. Figures ADDRESSED. All figures in graph.md, projections.md and the handoff match measurements.md. Some figures are not in your list but are in measurements.md: nothing new 0.022 / 0.023, after one write 0.038 / 0.040, empty bracket CLI 0.042 / 0.135, empty bracket MCP 0.025 / 0.135. Your listed medians all appear correctly (rounded to 3.5 s / 35 s / 130 s / 7 s in prose).
9. Tutorial ADDRESSED. `uv run pytest --collect-only -q` gives 2807 tests; tutorial line 292 says 2807 passed.

## New Critical/Important issues
None.

## Minor (inside the diff's neighbourhood)
- landkarte.md:~574 says cli.py has 4,483 lines after phase 2 and server.py 3,245. HEAD has 4,476 and 3,251. Probably measured before the M-2 removal in cli.py; server.py differs in the other direction because the docstring grew. Recount.

## Out of scope
- docs/explanation/module-boundaries.md:425 still says the graph projection's tables "hold no content", without the period dates (same sentence the wave qualified elsewhere).
- projections.md:346 "they hold no content" is similar, but it stands next to the qualified sentences.
