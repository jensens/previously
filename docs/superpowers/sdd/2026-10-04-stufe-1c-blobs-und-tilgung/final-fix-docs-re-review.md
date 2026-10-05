# Re-review of the final fix wave, pages part (dacb067..8d1c591)

Read-only review. Nothing was run except the map count (100, matches the claim) and file reads. Prose was checked against `cli.py`, `core/verify.py`, `core/projection/worker.py`, `storage/postgres.py`, `contract/store.py`, `core/errors.py`, `migrations/versions/0003_hash_version_2.py` and `tests/test_projection_worker.py`.

## Item Verdicts

1. ADDRESSED. `cli.md` append section now holds the JSON example and the "twice" sentence (`cli.py:426` payload `{"text": ...}`, `append.py:324` adds `evidence`); the redact section says the wording stays readable in the payload and ties to the notice. The notice wording matches `cli.py:827`.
2. ADDRESSED. `restore-from-a-backup.md` (new paragraph, "no check reports it" narrowed to "a content that no event of the restored log names") and `erasure.md` "Restoring brings it back".
3. ADDRESSED. `keep-the-blob-key-safe.md`, the paragraph after the `head-object` example.
4. ADDRESSED. README erasure bullet; `erase-something.md` "What the erasure doesn't reach".
5. ADDRESSED. `erasure.md` (new bold item), `erase-something.md` (settings and check sections), `verify-the-chain.md`. All say only that nothing checks the bucket.
6. ADDRESSED. `cli.md` 244-270 against `verify.py`: each of the nine rows has the right wording and condition (`_payload_finding`, `_payload_finding_v2` including the missing salt, `_units_finding`, `_units_finding_v2`, `_event_hash_finding`, `_check_event` for linkage and first event, `_count_finding` with id 0, both "not canonicalizable" branches with `# pragma: no cover`). The unknown-version sentence matches `_check_event`. The block is not test-held, as the implementer said (see Out-of-Scope).
7. ADDRESSED. `configuration.md` lines 6, 53 and the directory sentence (`cli.py:259` exit 2, `cli.py:762` exit 2 for `blob get`, `verify --blobs` exit 1 via `verify.py:769`). The "redact reads the five only when it has a blob to delete" claim matches `_delete_obsolete`.
8. ADDRESSED. `erase-something.md`, *Erase units* opens with the payload statement before the command; the block includes the notice line after `redacted by event 3`, in the order `_cmd_redact` prints it (notice last on success).
9. ADDRESSED. `keep-the-blob-key-safe.md`, step 5 `unset AWS_*`.
10. ADDRESSED. `keep-the-blob-key-safe.md`, sentence before the `head-object` example.
11. ADDRESSED. `verify-the-chain.md` and `restore-from-a-backup.md` give both answers; "settings are read before the chain pass" is right (`_examine` calls `_identities()` before `examine`), and the store-error-after-pass remark matches `before_blobs`.
12. ADDRESSED. `show` prints no source key (`cli.py:595-639`); `chronicle` prints source and external_id as fields 4 and 5 (`cli.py:1025-1027`); no command finds an event by source key. Stated so in `erase-something.md` and `restore-from-a-backup.md`, and put into the map.
13. ADDRESSED. README blobs bullet.
14. ADDRESSED. `docs/index.md` cards.
15. ADDRESSED. `module-boundaries.md`: `RedactionStore` has three methods (`store.py:111-113`), "thirteen" and "five modules" match the `store.py` docstring, and the page counts no `ProjectionStore` methods.
16. ADDRESSED. `blobs.md` new paragraph on the unsalted address.
17. ADDRESSED. `erasure.md`, *What "covered" means* (target plus events sharing a blob; matches `lock_event` docstring).
18. ADDRESSED. `cli.md` `--blobs` row.
19. ADDRESSED. `database-schema.md`: text and condition (`hash_version <> 1`, units without content) match `0003_hash_version_2.py:56-77`, including the `; ` join and the rollback to the starting revision.
20. ADDRESSED. `blobs.md` heading with `verify` in code formatting.
21. ADDRESSED. `hash-chain.md` domain sentence.
22. ADDRESSED. `cli.md` ("replaced ... without a question") and `attach-and-fetch-a-file.md`.
23. ADDRESSED. `projections.md`: the counts are gone; the remaining "eleven tests in test_projection_derive.py" in the measured block matches the tutorial's 11 dots.
24. ADDRESSED. `projections.md` `(catch-up-lock)` section, `concurrency.md` paragraph. They match `worker.py:116-139` (lock per transaction, position and version from the locked row, `!=` rule, error on a missing or different row) and `lock_projection_state` (placeholder with `ON CONFLICT DO NOTHING`). The three named tests exist (`test_projection_worker.py:643, 730, 802`). `FOR NO KEY UPDATE` is right (`lock_event`, `with_for_update(key_share=True)`), with the reason as in its docstring.
25. ADDRESSED. Spot-checked `cli.md`, `configuration.md`, `blobs.md`, `erase-something.md` against the code's wordings; "a deletion, the catch-up, or both" matches `_cmd_redact` (`left` joined with ", and ").
26. ADDRESSED. `concurrency.md:8`; no other page counts locks.
27. ADDRESSED. `cli.md` `project` section: both error sentences are exactly `worker.py:133-136`'s text ("stands at version N" / "has no state row", then "and this code declares version M"); exit 2 (`PreviouslyError`); the wrapping in parentheses matches `cli.py:898`; the "either direction" rule matches `worker.py:117`. `rebuild-a-projection.md` has the three steps (stop the other release, run `project`, rerun `redact`).
Map. ADDRESSED. `awk` count prints 100. Present: register-only blob list, bucket versioning point extended (not duplicated), `N blobs match`, `--hash` added to the existing id point, re-delivery with a new id and hash, the `append --text` point reworded with E-3, the stage 1b upgrade gap, the two-releases point and the unreviewed-block point. The lock point is struck with `3ae7038`, `_catch_up_after` is reworded correctly (it returns on the first failing projection, `cli.py:894-899`).
Tutorial. ADDRESSED. Block retyped, 632 items; the per-file dot counts sum to 632; the last line reads `632 passed`.

## New Breakage in the Fix Diff

None Critical or Important.
- Minor, `docs/reference/cli.md:245`: "Seven findings come from the chain itself, whatever the hash format" introduces a table of nine rows, two of them format-dependent (`units not canonicalizable` is format 1 only, `unit <seq> not canonicalizable` format 2 only). The following sentences explain the two extra rows, so it reads, but "whatever the hash format" is loose.
- Minor, `docs/how-to/rebuild-a-projection.md` (new sentence after the force-rebuild step): a `project` that runs while the row is deleted stops with `has no state row` only if the delete lands between two of its batches; a `project` that starts after the delete just builds. The sentence says "runs while you delete the row", which is true but not every run. Not false.
- No secret found (`grep` for `AGE-SECRET` shows only the `…` form). Form on changed lines: one sentence per line holds in what I read; American English holds.

## Out-of-Scope Observations

- `tests/test_docs_references.py` still does not hold the new chain-findings block (implementer's concern, recorded in the map under *Tore*). The wording was compared by hand with `verify.py` above and is right. It needs a change under `tests/`.
- The help of `verify --blobs` still says "read every blob in the store" (map entry added).

## Verdict

**Fix wave, pages part:** All addressed, no new Critical/Important breakage.
