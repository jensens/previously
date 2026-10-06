# Task 3 review: watermark and connector contract (5735843..5b55f68)

**Spec compliance:** ✅ No gaps. `Watermark`, `Fetched`, `Connector`, `WatermarkStore[Conn]` match the brief's names, field order, types and signatures. Table `watermark` (`connector text PK`, `position jsonb NOT NULL`, `set_at timestamptz NOT NULL`) is identical in `schema.py` and in migration `0005_watermark` (chained on `0004_event_blob`). The downgrade checks `EXISTS` before the drop and refuses with `CommandError`, in the form of 0004. Tests cover None read, write/read/overwrite, `migrate` creating the table (via `test_schema`, session DB at head), and the downgrade refusal.

**Quality verdict:** Approved

Verified by running: `tests/test_watermark.py`, `tests/test_migration_0005.py`, `tests/test_docs_typed_output.py` (10 passed); `pytest --collect-only` gives 975 (matches the retyped "collected 975 items"); `lint-imports` 7 kept, 0 broken. Working tree clean.

## Critical
None.

## Important
None.

## Minor

1. **Stale example revision name, `docs/how-to/cut-a-release.md:87`.** The release-notes example says "it adds the revision 0005_example". That revision number now exists for real (`0005_watermark`), so the example reads as if it were the next revision. The implementer moved the same example in `cli.md` to `0006_example` but missed this one. It is an illustration, not a head-revision claim, so no test or gate catches it. Suggest `0006_example`. Everything else naming the head revision was grepped (`docs`, `src`, `tests`, `README.md`, excluding `docs/superpowers` and `_build`): `cli.md`, `run-the-image.md` and the tutorial are correct and complete. The remaining `0004_event_blob` hits are legitimate (`database-schema.md:127`, which is the 0004 section; `tests/test_migrate.py:698`, a docstring about 0004's own upgrade).

2. **`docs/reference/database-schema.md` (new section, `set_at` row): "When the row was last written."** The caller supplies `set_at`; the store neither sets nor checks it against the clock. `types.py` says "when that was written down", which is closer. A caller passing an old moment makes the sentence false. Suggest "The moment the caller gave when it wrote the row." A name, not a defect in ordinary use (Task 4/5 pass `now`).

3. **`docs/explanation/module-boundaries.md:336-343` still tells of "a second ... a third" protocol and stops there.** `WatermarkStore` is the fourth. Nothing in the text is false (it narrates stages 1b and 1c), so this is a documentation follow-up for the page that explains why protocols are separate, not a gate failure. The brief lists only `database-schema.md`; a later task or the landkarte could take it.

4. **`src/previously/storage/schema.py` comment above `watermark`: ragged wrap** ("one row per connector,\n# replaced as a whole"). Cosmetic only.

5. **Untested branch (name, misuse only):** `moment.tzinfo.utcoffset(moment) is None` (a `tzinfo` object that returns no offset) shares a line with the `tzinfo is None` test, so coverage reads 100% while only the first half is exercised. Same shape as `iso_utc`. Position values that are not strings are also not validated (`Mapping[str, str]` is a type-level promise only). Both need misuse to trigger.

## Decisions examined

- **Naive `set_at` raises `ValueError` in storage: acceptable.** `storage/errors.py` has no exception for an invalid argument; every `StorageError` subclass names an operational failure. Storage already raises bare `ValueError` for bad input (`postgres.py:711` unknown projection, `s3.py:68` bad blob address, and `contract/blobs.py:73` documents the same convention). `core.errors.InvalidPayload` is a `ValueError` subclass, so a caller catching `ValueError` handles both. The `store.py` docstring, the `postgres.py` docstring and the schema page all state it, and `test_a_moment_without_a_zone_is_refused` reads it (together with the nothing-written check and the zone-aware control tests `test_a_moment_in_another_zone_reads_back_as_the_same_instant` and the round-trip).
- **Migration test in its own file:** correct, same reason and same `Config("alembic.ini")` as `test_migration_0004.py`. The test checks the open way down on an empty table, the exact refusal sentence, the revision still at `0005_watermark`, and the row kept.
- **Comments and numbers added by the diff, checked against code:** "seven to eight" tables and 3+1+1+3 = 8 in `database-schema.md` is correct; "the fifth", "Five revisions" in the tutorial is correct; `test_schema` 18 to 19, `test_watermark` 8, `test_migration_0005` 1 are consistent with the typed block; "no foreign key" and the `watermark_pkey` name match the DDL; the `test_schema` docstring's claim about `test_the_declared_columns_match_the_migrated_database` (column names and `NOT NULL`) is accurate; the "no `{ref}`" choice is consistent since no explanation page exists. The "refusal leaves the database at 0005_watermark" claim is covered by the migration test.
- **Test reads what it claims:** the upsert-replaces-whole test would catch a merge (`uidvalidity` absent in the second write) and a `do_nothing`; rollback test uses a real transaction; no mocks. `test_a_watermark_round_trips_as_a_plain_dict` pins `type(...) is dict`, which the docstring promises.
- **Interfaces for Tasks 4 and 5:** `Connector.fetch(since: Watermark | None) -> Iterator[Fetched]` and `WatermarkStore` methods are exactly as briefed. `PostgresStorage.watermark` / `set_watermark` take `Connection` and run in the caller's transaction (upsert, no commit), so Task 4 can write events and watermark atomically.
