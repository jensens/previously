# Task 3 report: watermark and connector contract

Status: DONE (with the notes below). Commit: 5b55f68.

## What was built

- `contract/types.py`: `Watermark(connector, position, set_at)` and `Fetched(raw, position, found_in, internaldate)`, frozen dataclasses, as in the brief.
- `contract/connector.py` (new): `Connector` protocol (`name`, `fetch(since)`).
- `contract/store.py`: `WatermarkStore[Conn]` (`watermark`, `set_watermark`).
- `storage/schema.py`: table `watermark` (`connector text PK`, `position jsonb NOT NULL`, `set_at timestamptz NOT NULL`).
- `storage/postgres.py`: `watermark` reads (position returned as a plain `dict`), `set_watermark` upserts with `ON CONFLICT (connector) DO UPDATE` and replaces the position as a whole.
- `migrations/versions/0005_watermark.py`: revision chained on `0004_event_blob`; `downgrade` refuses with a `CommandError` while the table has a row, checked before the drop, as 0004 does.
- Tests: `tests/test_watermark.py` (8 tests), `tests/test_migration_0005.py` (1, own container like 0003/0004), one test in `tests/test_schema.py` (primary key on `connector`; the generic column/CHECK comparison already covers every table in `metadata`).
- Docs: new `watermark` section and the table count (seven to eight) in `docs/reference/database-schema.md`; the head revision `0004_event_blob` to `0005_watermark` in the typed output of `docs/reference/cli.md`, `docs/how-to/run-the-image.md`, `docs/tutorials/record-your-first-event.md` (the unknown-revision example `0005_example` became `0006_example`, so it stays unknown); the tutorial's revision narration (five revisions); the whole typed test-run block retyped from a green run.

## Decisions

- Naive `set_at`: `set_watermark` raises `ValueError("set_at has no time zone — ...")` in storage. `core.hashing.iso_utc` raises `InvalidPayload`, but storage cannot import `core` and `contract/types.py` is declared "no logic", so the check stands where PostgreSQL would silently read the value in the session zone. Reads always come back aware.
- The migration test is a separate file (`test_migration_0005.py`), not in `test_watermark.py`, because it downgrades and needs its own container (the session database must never stand below head), like 0003/0004.
- No `{ref}` to a `watermark` explanation page: none exists; the reason stands in the comments.
- The test for a naive moment uses `datetime.fromisoformat(...)`, which builds a naive value without a `DTZ001` suppression; no new suppression was added.
- Docs that type the head revision had to follow (cli.md, run-the-image.md, tutorial); `tests/test_migrate.py` derives `HEAD` from the script directory and needed no change.

## Gates (final tree, each run separately)

1. `uv run ruff check .`: All checks passed.
2. `uv run ruff format --check .`: 82 files already formatted.
3. `uv run pyright`: 0 errors, 0 warnings.
4. `uv run lint-imports`: 7 kept, 0 broken.
5. `uv run pytest --cov --cov-report=term-missing`: 975 passed in 106.62s. `contract/connector.py` shows 0% and `contract/store.py` 0%: protocol modules never reach `sys.modules` at runtime, as `store.py`'s docstring explains. `storage/postgres.py`, `contract/types.py`, and the new migration are 100%.
6. `make -C docs html` (exit 0, no warnings), `make -C docs vale` (0 errors, 0 warnings; the first run caught "is not" in the new section, fixed to "isn't"), `make -C docs linkcheck` (exit 0).

Ruling P-1: before retyping, the suite was red with exactly one failure, `test_docs_typed_output::test_typed_test_counts_match_the_tree` (974 passed, 1 failed). After the new number was in place and a plain `uv run pytest` was green (975 passed), the whole block (seed, ordering, percentages, duration, collected count) was retyped from that run, with the `rootdir:` line left out as the page says.

## Mutation measurements

- Mutation: `downgrade` without the refusal (the `bind`/`EXISTS`/`raise` block deleted). `tests/test_migration_0005.py` went red (1 failed). Control: file restored, same test green (1 passed).
- Extra: the naive-moment check replaced by `if False:`. `test_a_moment_without_a_zone_is_refused` went red (1 failed, 7 passed). Control: restored, green.
- Extra: `on_conflict_do_update` replaced by `on_conflict_do_nothing`. `test_a_second_write_replaces_the_first` went red (1 failed, 7 passed). Control: restored, green.

All mutations were reverted; `git diff` of the committed files shows no leftover.

## Concerns

- The tests were written before the implementation in the file, but I ran them only after writing the implementation, so the "red first" step was not observed as a run. The mutations above are the measured red.
- `pip-audit` was not run (not one of the six gates).
