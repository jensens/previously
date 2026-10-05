# Final fix wave, part 2 (the pages) — the implementer's report, as handed back

Filed by the controller on 2026-10-05. The controller asked for this report as
the implementer's final message instead of a file; what follows is that
message, unchanged apart from this note.

---

**Status: DONE_WITH_CONCERNS.** All 27 items, the map and the tutorial are done in six commits on top of `dacb067`, and all six gates are green. The one concern is under item 6: `tests/test_docs_references.py` does not hold the new chain-findings block, and only a change under `tests/` could make it. I changed nothing under `src/`, `tests/` or `migrations/`, and did not touch the frozen specifications, the plan or `CLAUDE.md`.

**Commits** (messages in `final-fix-docs-commit-msg-1..6.txt` in the plan directory; trailer `Assisted-By: Claude Opus 5.5 <noreply@anthropic.com>`):
- `db51fac` docs: the reference says what the payload keeps and what verify finds
- `041246c` docs: the guides say what erasing units keeps, and how a restore is cured
- `2db5fb7` docs: explanations name the catch-up lock, the third protocol and the bucket
- `0ccf909` docs: README and index name the costly limits and the new pages
- `4b51b4c` map: the final fixes struck one point, reworded four, and found seven
- `8d1c591` docs: the tutorial's test run is retyped, 632 passed

**Gates** (each run on its own, after `8d1c591`):
- `uv run ruff check .`: All checks passed!
- `uv run ruff format --check .`: 69 files already formatted
- `uv run pyright`: 0 errors, 0 warnings, 0 informations
- `uv run lint-imports`: Contracts: 6 kept, 0 broken.
- `uv run pytest --cov --cov-report=term-missing`: ======================== 632 passed in 84.33s (0:01:24) ========================
- `make -C docs html`: build succeeded.
- `make -C docs vale`: ✔ 0 errors, 0 warnings and 0 suggestions in 28 files.
- `make -C docs linkcheck`: exit 0, 0 broken.

## Per finding

1. **`redact units` and the payload.**
   - `cli.md`, `append` section: a new paragraph with a JSON example. The payload holds the whole `--text` under `text` and the evidence kind under `evidence` (`cli.py:426` `payload={"text": args.text}`; evidence added in `core/append.py:324`). So every event `append` writes carries its text twice.
   - `cli.md`, `redact` section: after the `redact units` sentence, one sentence says that for such an event the wording stays readable in the payload and `redact event` erases it. "…stay" now includes "after `redact units` the payload as well". The sentence after the notice block now refers back to these, so the section reads as one piece.
2. **Blob erased before the restore point and attached again after it.**
   - `restore-from-a-backup.md`: a new paragraph. `verify --blobs` reports it as `erased and still present` and returns 1. `redact blob` then finds the blob covered, prints `already redacted by event <id>`, writes nothing and deletes the object (`redact.py` `redact_blob`: with nothing left to erase it names the existing redaction, and the blob is deleted as obsolete).
   - "No check reports it" is narrowed to "a content that no event of the restored log names".
   - `erasure.md`: the same case and its cure, under *Restoring brings it back*.
   - Prose only, no output block.
3. **`keep-the-blob-key-safe.md`:** if a key is missing from the backup, copy it from the identity directory now. Only if the directory lacks it too is every object sealed to it lost.
4. **Hash format 1:**
   - README: a sentence on the erasure bullet.
   - `erase-something.md`: a sentence under *What the erasure doesn't reach*, with a link to `erasure`.
5. **Versioned or locked bucket:**
   - `erasure.md`: a new bold item, "A bucket that keeps versions keeps the blobs."
   - `erase-something.md`: a paragraph under *Set the blob settings*, and a sentence under *Check the log*.
   - `verify-the-chain.md`: a paragraph.
   - All three say only that nothing in Previously checks the bucket; `verify --blobs` only asks for the current object (`verify.py`, `_blob_reason`: `stat`).
6. **Chain findings in `cli.md`:**
   - A new block, "Seven findings come from the chain itself", plus a table of nine rows with their conditions, read from `verify.py`.
   - The two `unit…`/`units not canonicalizable` findings are in the table only. The page says that no row of this schema in a UTF-8 database can produce them (`# pragma: no cover` branches).
   - Also added: what an unknown hash version still gets checked (`_event_findings`).
   - **Not held by the test.** `test_docs_references.py` keys on fixed lead sentences and asserts `len(findings) == 13`. Holding this block too needs a change under `tests/`, which this brief forbids.
   - What I did instead: a scratch script used the test's own helpers (`_finding_patterns`, `_quoted_block`, `_is_the_same_sentence`) and found all 7 lines OK. A control with a reason the code doesn't produce came out False.
   - This is in the map under *Tore*.
7. **`configuration.md`:**
   - Line 6 now reads "store, fetch or delete".
   - Line 53 now reads "Every other command, and `append` without `--attach` and `verify` without `--blobs`, reads none of them; `redact` reads the five only when it has a blob to delete".
   - An existing directory missing a key gives exit 1 for `verify --blobs` and exit 2 for `blob get` (`cli.py:762` raises `PreviouslyError`).
8. **`erase-something.md`, *Erase units*:**
   - The section now opens with three sentences: the payload stays, the text of an `append` event stays readable, and what the example shows.
   - Every block on the page is retyped from one run.
   - The `redact units` block now includes the notice line.
9. **Rehearsal step 5:** now also `unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_DEFAULT_REGION`. Run in bash: no `AWS_` variable left.
10. **`head-object` example:** one sentence says the object is sealed to the second key, the one *Change the key* creates. The output is unchanged.
11. **Identity directory:**
    - `verify-the-chain.md`:
      - all `cannot be opened` for one key → check the directory;
      - exit 2 `PREVIOUSLY_BLOB_IDENTITIES is not a directory` → a new block, typed from a run;
      - the settings are read before the chain pass (`_examine` calls `_identities()` before `examine`), so that error comes alone. A store error in the blob phase comes after the pass, and the chain's findings still print.
    - `restore-from-a-backup.md`: both answers, and what to do on a restored machine.
12. **Source key in the erasure record:**
    - `show` does not print the source key (`cli.py:601-639`). Only `chronicle` does, in fields 4 and 5, and only for units that still have a row there.
    - No command finds an event by its source key.
    - `erase-something.md` says all three and tells the reader to note the source key before erasing.
    - `restore-from-a-backup.md`: the record carries it, plus a paragraph on re-delivery under a new id and hash.
    - The map has a point for it.
13. **README:** the blobs bullet gets the key-loss limit and a link to `keep-the-blob-key-safe.md`.
14. **`docs/index.md`:** the how-to card names the four new guides; the explanation card names erasure and blobs.
15. **`module-boundaries.md`:**
    - New paragraph on `RedactionStore`: three methods (`contract/store.py:111-113`), and why erasure got its own protocol.
    - "nine methods" is now dated to stage 1b, with "thirteen" today and a pointer to the census in `store.py`.
    - "A second protocol has existed since stage 1b."
    - The page counts no `ProjectionStore` methods.
16. **`blobs.md`:** a new paragraph. The provider sees each object's name, the unsalted SHA-256, so anyone holding a candidate file can confirm it is in the bucket.
17. **`erasure.md`, *What "covered" means*:** the lock set now includes, for an event with attachments, every event that shares a blob with it.
18. **`cli.md`, `--blobs` row:** now "read and open each blob that has to lie there, and ask after each that doesn't".
19. **`database-schema.md`:** the 0003 refusal, with its condition (`hash_version <> 1`, units without content), the exact line from `0003_hash_version_2.py:56-77`, and that the database stays at the revision it started from.
20. **`blobs.md` heading:** "What `verify` checks in the store".
21. **`hash-chain.md`:** the units digest of version 2 keeps the domain of version 1, and its version tells the two apart. `hash-chain.md:300` ("cli-reference gives the lines") is true now thanks to item 6.
22. **`blob get` replaces an existing file:**
    - `cli.md` says "An existing file at `--output` is replaced by the content, without a question."
    - `attach-and-fetch-a-file.md` says it as well.
    - Measured: a file holding "something else" became the agenda; `wrote 34 bytes to existing.txt`.
23. **`projections.md`, stale counts:**
    - The "eleven / sixteen" counts are removed.
    - The version-mutation sentence is now dated: "measured on 2026-10-05, before the catch-up lock added a second comparison to every batch", with no count.
24. **The catch-up lock:**
    - `projections.md`: a new section, label `catch-up-lock`. It covers:
      - the lock per transaction, with position and version read from the locked row (`worker.py:116`, `:128`);
      - the placeholder row on a first build (`lock_projection_state` docstring);
      - the interleaving from the code review's Critical 1, attributed;
      - the three tests that hold it;
      - `ProjectionRebuilt` and why it stops instead of rebuilding (`errors.py:51-60`).
    - `concurrency.md`: a paragraph on the second kind of lock. It doesn't wait on the erasure lock: foreign-key checks take a key-share lock, which `FOR NO KEY UPDATE` lets through (code report, Important 2).
    - The `FOR NO KEY UPDATE` wording was already corrected by part 1. A grep finds no other page that names it as `FOR UPDATE`.
25. **Wordings:**
    - Checked each wording in the code report against `cli.md`, `configuration.md` and `database-schema.md`: TransactionAborted, both forms of the unfinished sentence, the notice and its order, identities, the downgrade, and the order of checks.
    - Grepped for old forms and fixed what was left:
      - `blobs.md`: a "no directory" sentence, and the chain findings printed beside an error;
      - `erase-something.md`: "a deletion, the catch-up, or both".
26. **`concurrency.md:8`:** now names "the two kinds of row lock in the system". The grep finds no other page that counts locks.
27. **`ProjectionRebuilt`:**
    - `cli.md`, `project` section:
      - both error forms;
      - what each means: another release, or a state row removed by hand;
      - the `!=` rule in either direction (`worker.py:117`);
      - inside `redact` it comes wrapped in the unfinished sentence, whose advice holds once only one release runs.
    - `rebuild-a-projection.md`:
      - a new section in three steps: stop the other release's process; run `project` with the intended release; rerun the `redact`;
      - one sentence on a `project` that runs while the row is deleted by hand.

## Blocks retyped, and the runs they come from
- **`erase-something.md`, every block.** One run at `dacb067`, 2026-10-05, against these containers:
  - `ffprev`: `postgres:17`;
  - `ffrustfs`: `rustfs/rustfs:1.0.1` on network `ffblobs`, with the bucket made through the `amazon/aws-cli:2.37.9` container;
  - `ffage`: `alpine:3.22` with `age`, for the key.
  - New hashes: event 2 `3d4758…c4c4`, event 1 `7e084a…a02e`. The `redact units` block now carries the notice line.
- **`verify-the-chain.md`:** the new `PREVIOUSLY_BLOB_IDENTITIES is not a directory: /srv/previously/identities` block, from a separate run of `previously verify --blobs` against the same containers (exit 2).
- **Tutorial pytest block:**
  - Typed last, from one `uv run pytest`: 632 collected, `632 passed in 86.80s`, without the `rootdir:` line.
  - With the old block in place the typed-output test fails, so that run can't pass. I first replaced the old block with a placeholder that claims no count (not committed), ran the suite green, then typed the whole new block from that run. No number was edited inside a block.

## Map (`docs/superpowers/landkarte.md`)
- **Count:** 94 before, **100** after.
- **Struck:** "Sperre auf der Zustandszeile" (commit `3ae7038`). The *Was vor was* row on the queue is updated.
- **Reworded:**
  - `_catch_up_after`: still stops at the first failing projection, but a failed deletion no longer blocks the catch-up (`b9b0cdc`);
  - `redact units`: the notice and help now say it (`4bbb305`, `1b696a6`, E-3); the `append --text` decision stays open;
  - target as an id: gains the `--hash` proposal;
  - Hetzner/bucket entry: gains "nothing checks for versioning or object lock";
  - test time: 31 s → 87 s, `632 passed in 86.80s`.
- **Added (7):**
  - re-delivery after a restore, and that no command finds an event by its source key (Einwurf-Vertrag);
  - two releases rebuilding a projection against each other (Projektionen);
  - `redact_event` takes blobs from the register only (E-6, Tilgung);
  - no page describes the upgrade from stage 1b (Betrieb);
  - `N blobs match` counts erased blobs (Kommandozeile);
  - the help text of `verify --blobs` (Kommandozeile);
  - the chain-findings block that no test holds (Tore).

## Disagreements, things not settled
- **Item 6 test coverage:** see above.
- **`verify --blobs` help text:** it still reads "also read every blob in the store and check it" (`cli.py`, `_verify_arguments`). That is code, so it went to the map, not to the pages.

## Containers
- **Started:** `ffprev`, `ffrustfs`, `ffage`, network `ffblobs`, plus `--rm` runs of `amazon/aws-cli:2.37.9`.
- **Removed:** all three containers with `docker rm -f -v` (volumes included), and the network.
- **Scratch files:** the scratch directory with keys is deleted.
