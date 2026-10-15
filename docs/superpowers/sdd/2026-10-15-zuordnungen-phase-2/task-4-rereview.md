# Task 4 re-review (fix base 5323559, head b64d43f)

Read from the diff only; no test run. Line numbers are diff-file lines (review-5323559..b64d43f.diff) / tree paths.

## Verdicts
- I-1 ADDRESSED. graph_read.py `version_differences` + `check_graph` (diff ~l.915-985), `rebuilt_versions` in core/projection/graph.py (~l.1010-1030); test in tests/test_cli.py falsifies missing/extra/wrong row; property now runs check_graph.
- I-2 ADDRESSED. `projection_stands` (graph_read.py, version + up_to_id >= outcome + row present), same snapshot conn as the read. CLI `_caught_up`/`_reader_graph`/`_graph_warning` (cli.py, print to sys.stderr only); MCP `Service.caught_up`/`read_graph` (server.py, logger.warning only). Tests: CLI rebuilt/failed (assert out == fold output, err == exactly one line), MCP rebuilt/failed (four calls equal the fold server, "projection" not in result, one warning per call, not is_error).
- M-1 ADDRESSED. Service.__init__ raises ValueError on one store (server.py); test with both/neither.
- M-2 ADDRESSED. `_http` passes the projection; working-language test passes both stores; new HTTP counting test (folds == 0).
- M-3 ADDRESSED. "two short transactions" in cli.py `_caught_up` and projections.md.
- M-4 (graph.md wording only) ADDRESSED. graph.md graph-cost now says what each reader folds and that MCP list_entities folds every entity per page and why. The SQL `types` part is left out, accepted.
- M-5 ADDRESSED. Property calls check_graph after each catch-up.

## Warning never in a result
CLI: the only emitter is `_graph_warning`, print(..., file=sys.stderr); listings' stdout is asserted equal to the fold output. MCP: logger.warning only; `answer()` is unchanged apart from catching; tests assert no "projection" in the result text and not is_error. Nothing in either path writes the warning into an Answer, a header or a page. (Logging has no basicConfig in src, so Python's last-resort handler writes to stderr, never stdout; fine for stdio MCP.)

## Can a client force the fold?
No, not via anything a client can send. The fallback triggers on (a) ProjectionRebuilt / StorageError from the catch-up, or (b) the state row at another version, absent, or up_to_id below the catch-up's. Client writes only append to the log; they never lower projection up_to_id, never change its version and don't touch the state row lock, so they cannot make (b) true. (a) needs a version bump/forced rebuild by an operator or another deployed version, or a DB fault; there is no lock_timeout/statement_timeout in src, so lock contention waits instead of raising. Only a client that can already drive the DB into errors (connection exhaustion, OperationFailed) gets the more expensive fold, and then it is an amplification of an outage, not a trigger. Cost during a genuine rebuild window: every concurrent call does one full fold (today's phase-1 cost), N callers = N folds; operator-triggered, bounded by the rebuild duration.

## New Critical or Important issues in the fix diff
None.

## Minor / out of scope
- ProjectionGap still fails the call (already in progress.md as a final-wave item).
- CLI and MCP fallback tests wrap or replace `catch_up` (spy over the real call in the rebuilt case; a raising stub in the failed case); the real failing path is exercised through the MCP `_CatchUpFails` store, so acceptable.
- Tests cover entities/triage/status for the CLI; relations/show/classes share `_reader_graph`, untested individually but identical code.
- The warning embeds `str(error)` from a StorageError in stderr/log; check once that no storage error text carries the DSN/password (InvalidDsn is not reachable from a catch-up that already connected, so likely fine).
