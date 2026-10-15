# Task 3 re-review — fix round 207d647..518d438

Read the diff once; ran the docstring's commands in the worktree (HEAD 518d438). Ran no test.

- I-1 ADDRESSED. `contract/store.py` (new `LogReader[Conn]`, two methods); `worker.py` Projection.write takes it; chronicle, source_stats, graph follow; the false sentence replaced. Test `tests/test_projection_store.py` (`test_the_log_and_its_store_satisfy_the_read_protocol_of_a_projection`) assigns LogStore and PostgresStorage to LogReader.
- I-2 ADDRESSED. Measured: `grep -rl LogStore src/previously/core --include='*.py' | wc -l` = 15; method command = 15; mcp_server command = 8; LogStore declares 16. All match the docstring.
- I-3 ADDRESSED. `tests/test_migration_0006.py` asserts state rows `["chronicle","source-stats"]` after the downgrade, then `rebuilt_from == 0` and rows == fold after the way up. Red-without-DELETE is reported; I did not re-run it.
- M-1 ADDRESSED. `docs/reference/database-schema.md:138` "Five more tables". metadata has 10 tables (per report).
- M-2 ADDRESSED. `test_an_erased_rejection_lets_its_proposal_wait_again`; the property appends rejection ids to `history.versions` (test_projection_graph.py, `_Reject` branch).
- M-3 ADDRESSED. `test_an_objection_against_an_erased_direct_version_still_waits`; property docstring states it stays green for contests.
- M-4 ADDRESSED. Six events, batch size 2, `_rows == _folded` checked inside each thread after its catch_up, events >= 2 each.
- M-5 ADDRESSED. Period dates named in schema.py comment, rows.py, projections.md, database-schema.md.
- Index ADDRESSED. `schema.py` (`p_graph_version_under_idx`, postgresql_where), `0006_graph.py` create and drop in downgrade, `tests/test_schema.py::test_a_declared_partial_index_is_partial_in_the_database` against `indpred`.

New Critical/Important: none.

Out of scope / minor:
- The concurrency test's `events >= 2` for the second reader depends on the lock handoff alternating; reported green five times, not deterministic by construction.
- Tutorial retype (2746) is consistent with five new tests; not re-measured.
