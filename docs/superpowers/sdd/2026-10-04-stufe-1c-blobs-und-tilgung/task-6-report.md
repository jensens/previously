# Task 6 report — blobs at the event

Status: DONE_WITH_CONCERNS. Commit `9efb419` (one commit, on top of `8ca910d`). All measurements 2026-10-05.

## What was implemented, step by step

### Step 1 — schema and storage
- `storage/schema.py`: table `event_blob` (`event_id bigint NOT NULL REFERENCES event(id)`, `sha256 bytea NOT NULL`, PK `(event_id, sha256)`, `CHECK (octet_length(sha256) = 32)` named `event_blob_sha256_check`, index `event_blob_sha256_idx`).
- `migrations/versions/0004_event_blob.py`: same table; `downgrade()` refuses while the table has a row (`refusing to downgrade below 0004_event_blob: the register names blobs, and without it nothing says which events use them`).
- `contract/store.py` / `storage/postgres.py`: `insert_event(..., blobs=())` writes the register rows after `source_key` in the same transaction; `blobs_by_event` (one query per batch, ascending, empty batch = no statement) and `events_by_blob` (ascending).
- `tests/conftest.py`: "All six tables" → "Every table `metadata` declares stands in one statement, however many there are".

### Step 2 — `append` carries the references
- `contract/types.py`: `BlobRef(sha256, size, media_type, filename=None)`; `RawEvent.blobs: tuple[BlobRef, ...] = ()` at the end.
- `core/chain.py`: `Prepared.blobs: tuple[bytes, ...] = ()`; `prepare(..., blobs=())` refuses a payload carrying `blobs` (exact table wording), validates each reference (`blob reference <i>: …`), mixes them in only when non-empty, before hashing, and keeps the distinct hashes ascending. New public `read_references(payload) -> tuple[BlobRef, ...] | None` (the reader of a stored payload, used by `verify` and `show`).
- `core/blob.py`: new public `is_address(text)` (one regex for core: chain, verify, cli).
- `core/append.py`: passes `event.blobs` to `prepare` and `ready.blobs` to `insert_event`.

### Step 3 — `verify` and `redact_event`
- `core/verify.py`: per batch `blobs_by_event` (one statement); `_register_finding` for events with payload (set of hashes in `payload.blobs` vs register; a list without the form = same finding); erased events: register rows remembered in `_Erasures` and held against `redaction.blobs` at the end. A payload tombstone without any redaction is skipped (its finding is already "erased without a redaction").
- `core/redact.py`: `redact_event` fills `target.blobs` from the register (hex, ascending — `event_payload` sorts/dedups).

### Step 4 — command line
- `_setting`, `_blob_store()` (context manager, five variables, closes in `finally`), `_recipient()` (checks with new `core.sealing.check_recipient`), `_identities()`.
- `append --attach FILE` (repeatable): `_attach` reads recipient, then store settings, opens **all** files (input error `cannot read the attachment <path>: <strerror>`; a non-seekable source is refused too), then `store_blob` each, then append. `filename` = `Path(path).name`; `media_type_of(name)` via a private `mimetypes.MimeTypes()` instance.
- `blob get HASH --output FILE` (second level like `redact`): address check first (table wording, `InvalidPayload`, exit 2), then settings, then `events_by_blob` (empty → stderr `no event uses blob <hex>`, exit 1), then `fetch_blob` into `mkstemp` in the target's directory, `os.replace` only after return; temp file removed on every other path. Errors: `blob <hex> does not match its address; nothing was written`, `blob <hex> cannot be opened: <reason>`, `blob <hex> is not in the store`; and (new, not in the table) `cannot write <file>: <strerror>`.
- `show`: one line per reference, `  blob <hex> <size> <media_type> <filename or ->`, from the log only.
- `COMMANDS`: `blob` after `show` (ten commands).

### Step 5 — pages
`docs/reference/cli.md` (ten subcommands, exit-code row for `blob`, `--attach` + "Attachments" subsection, `target.blobs` now from the register, the register finding, `show` blob lines, new `blob` section, rebuild example fixed), `configuration.md` (eight variables; "Database" and "Blob settings" sections; table of the seven with what each is and the command it is missing at), `database-schema.md` (seven tables, `event_blob` section, ER diagram), `docs/explanation/blobs.md` (first the blob then the event and what stays on failure; reference in the payload and register beside it; why `filename` belongs to the use; media type from the built-in table; closing section now names only task 7's part). Tutorial test run retyped.

## TDD evidence

- Step 1 RED: `uv run pytest -q -p no:randomly tests/test_schema.py::test_a_register_row_needs_a_hash_of_32_bytes tests/test_storage.py -k "register or blob"` → `4 failed` (`relation "event_blob" does not exist`; `'PostgresStorage' object has no attribute 'blobs_by_event'`) — expected, nothing existed. GREEN: schema/storage/migration files `56 passed` + `test_migration_0003` red (see below), fixed → green.
- Step 2 RED: `tests/test_chain.py tests/test_append.py -k "blob or reserved"` → `6 failed, 2 passed` (`DID NOT RAISE InvalidPayload`, `KeyError: 'blobs'`, `prepare() got an unexpected keyword argument 'blobs'`). The two passing were `test_the_reserved_key_is_refused` (old) and `test_an_event_without_blobs_carries_no_blobs_key` (holds today already; it is the guard against a future always-mix-in). GREEN: `47 passed`.
- Step 3 RED: `5 failed, 2 passed` (target `{'blobs': [], ...}`; verify returned `[]` where the finding was expected). GREEN: `127 passed` then one failure in `test_a_lost_chain_position_is_retried_and_leaves_nothing_behind` + 2 pyright errors: the test's `_ContestedLog` wrapper lacked the new protocol methods — extended (see "changed tests"). Then `115 passed`, pyright 0.
- Step 4 RED: `ImportError: cannot import name 'media_type_of' from 'previously.cli'` at collection — expected, nothing of step 4 existed. GREEN: `tests/test_cli.py` `92 passed`, later 93 with the recipient test.
- Keys: RED `test_a_file_that_cannot_be_read_is_a_storage_error_that_shows_no_content[not-utf-8]` failed: the `UnicodeDecodeError` kept as `__context__` (despite `from None`) carries the whole file, identity included. GREEN after the fix in `storage/keys.py`.

## Mutations (command, red, control)

All done in the tree, file restored from a copy afterwards; `git diff` checked.

1. Step 1, column missing from the migration (added `Column("probe", Text)` to `event_blob` in `schema.py` only): `test_the_declared_columns_match_the_migrated_database` → `AssertionError: event_blob … Right contains 1 more item: {'probe': True}`. Also: CHECK constraint removed from `0004` → same test `assert set() == {'event_blob_sha256_check'}`.
2. Step 3, `redact_event` writes `blobs=[]`: `test_the_register_of_an_erased_event_is_held_against_its_redaction` → `Left contains one more item: Finding(event_id=1, reason='blob register does not match the payload')`; control `test_a_register_row_without_a_reference_fires` green (`1 failed, 1 passed`).
3. `_cmd_append` (here `_attach`) stores each file as soon as it is opened: `test_an_attachment_that_cannot_be_read_appends_nothing[missing]` and `[directory]` red (`assert ['392637f3…'] == []`, the bucket holds the first attachment); control `test_append_with_an_attachment_and_blob_get_bring_the_bytes_back` green — `2 failed, 1 passed`. The test is built with two attachments, the second broken.
4. `_cmd_blob_get` writes straight into the target (`with open(target, "wb")` before the temp logic): `test_blob_get_writes_nothing_when_the_address_does_not_match` red (`Left contains one more item: …/out/fetched.txt`); control green — `1 failed, 1 passed`. Extra: `os.unlink(part)` taken out → mismatch test and existing-target test red (`.previously-….part` left), control green — `2 failed, 1 passed`.
5. `_cmd_log` reads a blob setting (`_identities()` at its start): `test_the_commands_of_today_run_without_any_blob_setting` red (`['log'] assert 2 == 0`); `test_a_missing_blob_setting_is_named` (7 cases) green — `1 failed, 7 passed`.
6. Recipient check removed (`check_recipient` → `pass`): `test_a_mistyped_recipient_is_refused_before_anything_is_stored` red (`assert 0 == 2`); control green.
7. `blob get` without its own address check: both `test_a_blob_address_that_is_not_one_is_an_input_error` cases red (sentence became `PREVIOUSLY_BLOB_IDENTITIES is not set`); control `test_blob_get_of_an_address_no_event_uses_returns_1` green.
8. Blob store release (`store.close()` in `_blob_store` replaced by `pass`): `test_main_releases_the_blob_store_it_opened` → `9 connections after the commands, 1 before`; with the release `1` and `1` (measured twice). Control `test_append_with_…` green.
   - **Close on success only** (close moved out of `finally`): stays green, `1` and `1`. The error half is not held by this test — see concerns.
9. Docs: `is not in the store` → `is not in the bucket` on cli.md, and the register finding rewritten on the page: `test_the_reference_quotes_what_the_code_actually_prints` red both times with the new messages.
10. T5-d test (`test_a_fetch_that_fails_gives_its_connection_back`), re-measured for the docstring: `stream.close()` moved from `finally` to the line after `unseal` → `10 connections after the failed fetches, 1 before`, twice.

## Complexity (cli.py and touched core)
`ruff check --select C901 --config 'lint.mccabe.max-complexity = 1'`: `examine` 9, `_cmd_show` 8, `_read_reference` 7, `observe` 6, `_execution_findings` 6, `_cmd_blob_get` 6, `_check_event` 6, `_references` 5, `prepare` 5, `_fetch_to` 5, `_attach` 5, `_cmd_verify` 5, `_cmd_chronicle` 5; `main` 3, `_cmd_append` 2. Threshold 10 not reached.

## Existing tests whose arrangement or expectation changed
- `tests/test_migration_0003.py`: expectation `revision == "0003_hash_version_2"` → `== ScriptDirectory…get_current_head()`. Reason: `env.py` runs a whole downgrade in one transaction; the downgrade from head now passes through `0004` first and the refusal in `0003` rolls that back too, so the database stays at head (was measured: `'0004_event_blob' == '0003_hash_version_2'` failed). The comment in `0003.downgrade` said "leaves the database at this revision" — rewritten.
- `tests/test_redact.py::_ContestedLog`: gained `blobs` on `insert_event` and the two new protocol methods (pyright and the test needed them).
- `tests/test_keys.py`: `test_a_file_that_cannot_be_read_is_a_storage_error_that_shows_no_content` (directory case) renamed `test_a_directory_in_place_of_the_file_is_a_storage_error`; the old name now belongs to a new parametrized test (no permission; not UTF-8) that checks str/repr of the whole cause/context chain. Skipped on Windows and for root (with reason).
- `tests/test_docs_references.py::test_the_reference_quotes_what_the_code_actually_prints`: two new blocks (the `blob get` stderr notice; six errors of the blob commands against `PreviouslyError`/`InvalidPayload` in `cli.py`) and the register finding block (12 → 13 findings). The success line `wrote <n> bytes to <file>` is not covered there (`_message_patterns` reads only stderr prints and returns); `test_cli.py` compares it exactly.

## Departures from the brief
- `mimetypes.MimeTypes().guess_file_type(name)` instead of `guess_type(...)`: `guess_file_type` (3.13+) is the path function; `guess_type` parses its argument as a URL first. Additionally a name with a compression suffix (`encoding` not `None`, e.g. `.tar.gz` → `application/x-tar`+gzip) yields `application/octet-stream`, because the inner type is not the type of the bytes stored. New public `media_type_of` in `cli.py` with a parametrized test (6 cases).
- New public names beyond the Interfaces block: `core.blob.is_address`, `core.chain.read_references`, `core.sealing.check_recipient`, `cli.media_type_of`. All signatures of the brief are as given.
- New error sentence not in the table: `cannot write <file>: <strerror>` (`blob get` target directory missing / not writable / target is a directory), input error exit 2. And `cannot read the attachment <path>: it cannot be read twice` for a pipe (fits the table's `<Grund>`).
- Reference validation in `prepare` (and the reservation of `blobs`) sits in `chain.prepare`, the one place that mixes the key in, so it holds for every caller.
- Extra tests beyond the brief: `test_migration_0004.py` (downgrade refusal — an assurance of the brief without a test in its table), `test_a_reference_list_without_its_form_fires` (verify), `test_read_references_refuses_a_list_prepare_does_not_write` (12 cases), `test_a_mistyped_recipient_is_refused_before_anything_is_stored`, `test_the_media_type_comes_from_the_name_and_the_built_in_table` (6), `test_main_releases_the_blob_store_it_opened`, and the keys test (2).

## Handed-over small things
1. `cli.md` rebuild example → `12000 events, up_to_id 12000`.
2. `IdentityUnreadable` named in `fetch_blob`'s docstring and in `KeyProvider`'s.
3. `test_keys`: renamed **and** added the real case — which found a real leak: `IdentityUnreadable` was raised inside `except … from None`, and the `UnicodeDecodeError` context's `repr` held the whole identity file. `keys.py` now raises after the `except` block; comment with the measurement.
4. `test_blob` docstring: now says what was run (close moved from `finally` to after `unseal`, closes on success and on mismatch), `10 after, twice over`, and that the 9+1 breakdown is reckoned.
5. `s3.py` read-timeout comment: the "keeps flowing" sentence marked as not run (rests on botocore's documentation of `read_timeout`), the 60 s × 2 called arithmetic, and the upload-part case named (a part whose answer takes longer than 20 s fails, after the second attempt the upload, as unreachable; not measured).

## Sentences found untrue and rewritten
- `postgres.py`: "The five reading methods below — read, units, units_by_event, count_events and source_keys" — already left out `read_by_kind`; now lists all eight without a count.
- `contract/store.py`: "ten methods, counted on 2026-10-04" → eleven, counted 2026-10-05 with the given grep; `events_by_blob` named as the twelfth, which no `core` module calls yet.
- `0003_hash_version_2.downgrade` comment (see above).
- `conftest.py` "All six tables".
- `blobs.md`: "from the next step on, its name in the log"; the closing section "the log doesn't know about it yet".
- `cli.md`: "nine subcommands"; `target.blobs` "an empty list"; `database-schema.md` "six tables"; `configuration.md` "exactly one environment variable".
- `pyproject.toml` print count 27 → 30, measured with `ruff check --select T201 --config 'lint.per-file-ignores = {}' src/previously/cli.py` (30 findings).
- Left alone (task 8 files): `docs/explanation/backup-encryption.md` still says the blobs use "AES-GCM and a key identifier in the row" — wrong since task 5.

## Counts and gates
- Tests: **528** (468 + 60: step 1 five incl. migration 0004; step 2 nine; step 3 five; step 4 27 incl. media type 6, recipient 1, release 1; chain reader 12; keys 2).
- `print` calls in `cli.py`: 30.
- `uv run ruff check .` → `All checks passed!`
- `uv run ruff format --check .` → `69 files already formatted`
- `uv run pyright` → `0 errors, 0 warnings, 0 informations`
- `uv run lint-imports` → `Contracts: 6 kept, 0 broken.`
- `uv run pytest --cov --cov-report=term-missing` → `============================= 528 passed in 59.56s =============================` (`Required test coverage of 90.0% reached. Total coverage: 98.10%`)
- `make -C docs html` → `build succeeded.`; `make -C docs vale` → `✔ 0 errors, 0 warnings and 0 suggestions in 24 files.`; `make -C docs linkcheck` → `build succeeded.` (0 broken in output.txt)
- `uv run pytest -p no:randomly` → `============================= 528 passed in 58.76s =============================`

## Files changed
src: `cli.py`, `contract/{blobs,store,types}.py`, `core/{append,blob,chain,redact,sealing,verify}.py`, `storage/{keys,postgres,s3,schema}.py`; migrations: `0003_hash_version_2.py` (comment), new `0004_event_blob.py`; tests: `conftest.py`, `test_{append,blob,chain,cli,docs_references,keys,migration_0003,redact,schema,storage,verify}.py`, new `test_migration_0004.py`; docs: `reference/{cli,configuration,database-schema}.md`, `explanation/blobs.md`, `tutorials/record-your-first-event.md`; `pyproject.toml`. `git status --short` before staging showed only my files.

## Self-review findings
- No secret in output: the store test checks the secret is absent from stdout+stderr; the identity test checks both identities and `AGE-SECRET-KEY` absent; the keys test's failure text is a bare flag so a failure cannot print the identity (my first version printed it in the assertion diff — fixed).
- `show` escapes `media_type` and `filename` with `escape_field` (page says so).
- The fetched file is mode 0600 (from `mkstemp`); stated on cli.md and asserted in the round-trip test.

## Concerns
1. **A refused upload in parts leaks a connection even after `close()`** (task 5 adapter). Measured with a probe: four `put`s of 9 MiB into a bucket that does not exist (`NoSuchBucket` on `CreateMultipartUpload`), each store closed: 0 before, 4 after, still 4 after 2 s, 0 after `gc.collect()` — something in a reference cycle holds a checked-out connection that `client.close()` cannot reach. Consequence for this task: the "on error" half of the blob-store release cannot be shown by mutation — the only failing path after which a store holds a connection leaks regardless of `close`, and the other failing paths (fetch errors) are freed by reference counting. The release test therefore holds `close` (9 vs 1) but stays green under close-on-success-only; the docstring says so. Untested idea for the controller: `TransferConfig(use_threads=False)` in `put`.
2. An `OSError` while **reading** an attachment after it opened (e.g. EIO) or while writing the sealed temp file escapes `store_blob` as a traceback, not one sentence. Not built; attributing it to the attachment would misreport a full disk.
3. The register check skips a payload tombstone without any redaction (no list to compare); not covered by a mutation test.
4. `core/redaction.py` keeps its own `_BLOB_ADDRESS` regex beside the new `core.blob.is_address`.
5. Release test makes 16 `main()` calls (4 rounds × 4), not "a few dozen"; each round uploads 9 MiB.

---

## Fix before review (ruling T6-a)

Commit `bc8ebdb` on top of `9efb419`. All measurements 2026-10-05.

### 1. The refused upload in parts

**Reference chain**, walked with `gc.get_referrers` from the leaked socket after one refused 9 MiB `put` into a missing bucket and `close()`, collector off:

`socket.socket` <- bound method in the `__dict__` of `urllib3.response.HTTPResponse` <- `botocore.awsrequest.AWSResponse` <- frame `_make_api_call` (`botocore/client.py:1094`, the call that raised) <- `traceback` <- … <- `botocore.errorfactory.NoSuchBucket` (the `ClientError`, traceback frames `_api_call`, `wrapper`, `_make_api_call`) <- `s3transfer.futures.TransferCoordinator` (its only referrer), which sits in reference cycles with the transfer's futures. `client.close()` empties the pool and does not reach a connection a response still holds; `gc.collect()` freed it (0 after).

**Fix** (`storage/s3.py`, `put` only, preference 1 of the ruling): on `ClientError` and `BotoCoreError` the adapter builds its own error inside the `except`, sets `error.__traceback__ = None` on the foreign error, and raises the project's error **after** the `except`, not chained. No collection anywhere. Why this one: the traceback is the only link from the kept exception to the response; dropping it frees frame, response and socket by reference counting. Measured which part does it: traceback kept, raised after → 4 after (red); traceback let go, still chained `from error` → 1 (green). Not chaining is kept anyway so that a caller who keeps our error does not keep the foreign one. Message unchanged: endpoint, bucket, code (`…refused a request on bucket 'previously-no-such-bucket': NoSuchBucket`); `test_a_wrong_secret_is_refused_and_not_shown` stays green.

**RED/GREEN** — `tests/test_s3.py::test_a_refused_upload_in_parts_leaves_no_connection_behind_after_close` (three refused 9 MiB uploads, each store closed, collector off): before the fix `AssertionError: 4 connections after the refused uploads, 1 before`; after `18 passed` (twice). Mutation `error.__traceback__ = None` → `pass`: 4 after vs 1 (red).

**Command line** — `test_main_releases_the_blob_store_it_opened` got the error case it needed: per round, `append --attach` of the 9 MiB file into a missing bucket (exit 2). Twenty calls now. Measured: with the release 1 before / 1 after; **close on success only → 5 after (red)**; `store.close()` taken out → 13 after (red). Docstring rewritten with these figures.

### 2. `OSError` on the blob path

- `core/errors.py`: new `SourceUnreadable(BlobError)` with `reason`.
- `core/blob.py`: hashing pass `OSError` → `SourceUnreadable`; sealing pass through `_Watched`, a source wrapper that remembers its `OSError`, because `pyrage` wraps a source failure into `EncryptError` text (measured before the fix: `BlobError: cannot seal: OSError: [Errno 5] Input/output error`); every `OSError` around the temporary file (making, writing, rewinding, reading for the upload) → `BlobError("cannot write a temporary file: <reason>")`. No `OSError` leaves `core`.
- `cli.py`: `SourceUnreadable` → `cannot read the attachment <path>: <reason>` (input error, exit 2). `blob get` already translated `mkstemp`, writing and `os.replace` failures to `cannot write <file>: <reason>`; now tested.
- New tests (all provoking real failures): `test_a_source_that_fails_while_it_is_sealed_is_an_error_of_its_own` (a small source of the test's own, `EIO` on the second pass), `test_a_temporary_file_that_cannot_be_made_is_an_error_of_its_own` (`tempfile.tempdir` pointed at a directory with mode 0500), in `test_cli.py` `test_blob_get_that_cannot_write_is_one_sentence_and_leaves_nothing` [parent-missing, not-writable, target-a-directory], `test_an_attachment_that_opens_and_cannot_be_read_appends_nothing` (`/proc/self/mem`: opens, seekable, `EIO` at offset 0; Linux only), `test_a_temporary_file_that_cannot_be_made_appends_nothing`. Each asserts one sentence, exit 2, nothing appended / bucket empty, or target untouched and no temporary file left. The permission tests skip for root, with the reason.
- RED: core tests `BlobError: cannot seal: OSError: [Errno 5]…` and a bare `PermissionError: [Errno 13]`; GREEN `29 passed` (blob + sealing), CLI `5 passed`.

**Mutations** (script in the scratchpad, each restored and checked):

| Mutation | red | green control |
|---|---|---|
| hashing-pass translation off (`except ZeroDivisionError`) | `test_an_attachment_that_opens_and_cannot_be_read_appends_nothing` | `test_append_with_an_attachment_and_blob_get_bring_the_bytes_back` |
| sealing-pass check off (`if False`) | `test_a_source_that_fails_while_it_is_sealed_is_an_error_of_its_own` | `test_the_same_content_twice_is_one_object` |
| temporary-file translation off | both temporary-file tests (core and CLI) | round-trip test |
| CLI `SourceUnreadable` translation off | `/proc/self/mem` test | round-trip test |
| `mkstemp` translation off | `[parent-missing]`, `[not-writable]` | `[target-a-directory]`, round-trip |
| `os.replace` translation off | `[target-a-directory]` | the two others, round-trip |

### Docs
`docs/reference/cli.md`: the attachment input error now covers "fails while it's read"; `Error: cannot write a temporary file: Permission denied` quoted; what `cannot write` covers. `tests/test_docs_references.py` holds seven blob-command errors now, the temporary-file one against `BlobError` in `core/blob.py`. Measured limit: rewording the page to `cannot write the temporary file: …` stays **green**, because `cannot write <file>: <reason>` from `cli.py` absorbs it (`<file>` = "the temporary file"); `cannot create a temporary file: …` goes red.

### Counts and gates
- Tests: **536** (528 + 8: s3 1, blob 2, cli 5). `print` count unchanged at 30.
- `uv run ruff check .` → `All checks passed!`
- `uv run ruff format --check .` → `69 files already formatted`
- `uv run pyright` → `0 errors, 0 warnings, 0 informations`
- `uv run lint-imports` → `Contracts: 6 kept, 0 broken.`
- `uv run pytest --cov --cov-report=term-missing` → `======================== 536 passed in 61.01s (0:01:01) ========================` (`Total coverage: 98.25%`)
- `make -C docs html` → `build succeeded.`; `make -C docs vale` → `✔ 0 errors, 0 warnings and 0 suggestions in 24 files.`; `make -C docs linkcheck` → `build succeeded.` (0 broken)
- `uv run pytest -p no:randomly` → `======================== 536 passed in 61.01s (0:01:01) ========================`

### Remaining concerns
- The other adapter methods (`stat`, `get`, `delete`) still chain `from error`; none of them was measured to leak, as none runs through the transfer manager.
- An `OSError` while `fetch_blob` writes into the temporary output file is translated by the same `except` as the other write failures, but no test provokes it (it would need a full disk).

---

## Fix round 1

Commit `bfe87d8` on top of `bc8ebdb`. Measurements 2026-10-05. Mutations run with a script in the scratchpad that patches one line, runs the named tests, and restores the file (checked).

### Important 1 — malformed endpoint or region
- `storage/s3.py` `from_settings`: `Session().client(...)` inside `try`; `ValueError`/`BotoCoreError` → `BlobStoreRefused("the settings for the blob store at <endpoint>, bucket '<bucket>', region '<region>', are not usable: <class>")`, raised after the `except` (no cause, no context). Region added to the message.
- Tests: `tests/test_s3.py::test_settings_the_client_refuses_to_be_built_with_are_refused` [endpoint-without-a-scheme → `ValueError`, region-with-blanks → `InvalidRegionError`] (exact message, `__cause__`/`__context__` None, secret absent from the formatted traceback); `tests/test_cli.py::test_an_endpoint_without_a_scheme_is_one_sentence` [append, blob-get] (exit 2, one sentence, no secret, nothing appended).
- RED: `ValueError: Invalid endpoint: localhost:9000`, `botocore.exceptions.InvalidRegionError: Provided region_name 'us east 1' doesn't match a supported format.`
- Mutation `except (ValueError, BotoCoreError)` → `except ZeroDivisionError`: all four new cases red (`4 failed`); controls `test_append_with_an_attachment_and_blob_get_bring_the_bytes_back`, `test_put_stat_get_round_trip_with_the_key_id` green (`2 passed`).
- `docs/reference/configuration.md`: one sentence on this case.

### Important 2 — writes into the temporary file
- **New finding while writing the test:** at 12 bytes of content, a sink whose one write raises `ENOSPC` makes `pyrage.encrypt_io` **return without an error** (1 write call); at 70,000 bytes and 1 MiB it wraps it (`cannot seal: OSError: [Errno 28] …`, 2 calls). Probe: `seal(io.BytesIO(b'x'*n), Full(), r)` for n = 12, 70000, 1<<20. Without the watcher a small content would have been uploaded as an empty/partial sealed file.
- `core/blob.py`: `seal_into` (public now) wraps source **and** sink (`_WatchedSource`, `_WatchedSink`); after an error *or a return*, a sink failure → `BlobError("cannot write a temporary file: <reason>")` raised after the `except`; a source failure → `SourceUnreadable`.
- Test: `tests/test_blob.py::test_a_sealed_form_that_cannot_be_written_is_an_error_of_its_own` [12-bytes, 70000-bytes] with a `_FullSink` of the test's own; plus a failing source stays `SourceUnreadable`. RED (with only the rename): `Failed: DID NOT RAISE BlobError` (12 bytes).
- Mutation "no check after return" (`if watched_sink.failure is not None:` → `if False:`): both sizes red; control `test_the_same_content_twice_is_one_object` green. Mutation "re-raise pyrage's error" (`if watched_sink.failure is None: raise` → `raise`): 70000-bytes red, 12-bytes green (pyrage did not raise there), control green.

### Minors
- **1** `put` docstring: not chaining is "no part of the fix"; `stat`/`get`/`delete` chain because no transfer manager keeps their errors.
- **2** `store_blob`: the `try` now covers making the temporary file, `seal_into` and `seek`, not `store.put`; the comment states the unmeasured assumption that the client turns its own failures into `botocore` errors, and that an `OSError` it let through would leave as is.
- **4** `test_docs_references.py`: the temporary-file block is held against `core/blob.py` alone. Wrong quotation `cannot write the temporary file: Permission denied` → red (`… and core/blob.py raises no such message`); unchanged page green (`5 passed`).
- **5** `core/chain.py`: one `_reference_problem(sha256, size, media_type, filename)` (plus `_filename_problem`) used by writer and reader. New checks for the writer: size an `int` and not a `bool`, `media_type` a string, `filename` a string, not empty, not `.`/`..`, no `/`. Test `test_prepare_refuses_what_read_references_refuses` (11 cases, each refused by `prepare` with `blob reference 0: <problem>` and by `read_references`). Mutation writer check off: 11 red; control `test_prepare_mixes_the_references_in_…` green. (No backslash rule: a POSIX file name may contain one.)
- **6** `cli.py`: all four `error.strerror` (anchor file, attachment, two `cannot write`) → `reason_of(error)` from `core.blob`.
- **7** `test_keys.py`: the root/Windows skip sits on the `no-permission` case only (`pytest.param(..., marks=...)`).
- **8** `docs/explanation/blobs.md`: one sentence that a pre-1c library payload with its own `blobs` key is now read as references and reported.
- **9** `core.redaction` uses `is_address`, which moved to `core.hashing` so that `redaction`, `chain` and `verify` don't import the sealing module.
- **10** `test_cli.py`: the three docstrings now state the reason (or review focus 5 of the plan) instead of "assurance 17/18 of the specification".
- **11** `test_verify.py::test_a_tombstone_without_a_redaction_is_not_held_against_a_list`. Mutation: compare against an empty list when there is no redaction (`named = () if redaction is None else redaction.blobs`) → red; control `test_the_register_of_an_erased_event_is_held_against_its_redaction` green.

### Interface as it now stands (for task 7)
- **Moved:** `previously.core.blob.is_address` → `previously.core.hashing.is_address(text: str) -> bool`.
- **Renamed to public:** `previously.core.blob.seal_into(source: ByteSource, sink: ByteSink, recipient: str) -> None` (was `_seal_into`; its source type widened from `SeekableSource` to `ByteSource`).
- **New public:** `previously.core.blob.reason_of(error: OSError) -> str`.
- **Unchanged:** `store_blob`, `fetch_blob`, `Stored`, `address_of`; `core.errors.SourceUnreadable(reason)`; `core.chain.prepare(..., blobs=())`, `read_references`, `Prepared.blobs`; `LogStore.insert_event(..., blobs=())`, `blobs_by_event`, `events_by_blob`; `storage.s3.from_settings` (same signature, now raises `BlobStoreRefused` for unusable settings); `cli.media_type_of`.
- `BlobStoreRefused` message for unusable settings now also names the region.

### Counts and gates
- Tests: **554** (536 + 18: s3 2, cli 2, blob 2, chain 11, verify 1). `print` count unchanged: 30.
- Covering tests: `uv run pytest -q -p no:randomly tests/test_cli.py tests/test_blob.py tests/test_s3.py tests/test_chain.py tests/test_append.py tests/test_keys.py tests/test_verify.py tests/test_redaction.py tests/test_docs_references.py` → `314 passed in 41.45s`.
- `uv run ruff check .` → `All checks passed!`
- `uv run ruff format --check .` → `69 files already formatted`
- `uv run pyright` → `0 errors, 0 warnings, 0 informations`
- `uv run lint-imports` → `Contracts: 6 kept, 0 broken.`
- `uv run pytest --cov --cov-report=term-missing` → `======================== 554 passed in 60.14s (0:01:00) ========================` (`Total coverage: 98.28%`)
- `make -C docs html` → `build succeeded.`; `make -C docs vale` → `✔ 0 errors, 0 warnings and 0 suggestions in 24 files.`; `make -C docs linkcheck` → `build succeeded.` (0 broken)
- `uv run pytest -p no:randomly` → `======================== 554 passed in 61.59s (0:01:01) ========================`

### Concerns
- The `pyrage` behavior with a small content and a failing sink (silent return) is upstream; `seal_into` covers it, but any other caller of `core.sealing.seal` with a sink that can fail does not get that protection.
- Minor 3 (no provoked write failure into `blob get`'s temporary output) stays open, as ruled.

---

## Fix round 1, part two (ruling T6-c)

Commit `7bc8f4a` on top of `bfe87d8`. Measurements 2026-10-05, `pyrage` 1.4.0.

### Measurements (before the change)
Probe: `seal`/`unseal` of `core.sealing` (which then wrapped only `EncryptError`/`DecryptError`) with sinks and sources of the probe's own.

| Call | 12 bytes | 70,000 bytes | 1 MiB |
|---|---|---|---|
| `seal` into a sink whose `write` raises `ENOSPC` | **returned normally** (1 write call) | `BlobError: cannot seal: OSError: [Errno 28] …` | same |
| `seal` from a source whose `read` raises `EIO` | `BlobError: cannot seal: OSError: [Errno 5] …` | same | same |
| `unseal` into a sink whose `write` raises `ENOSPC` | the sink's `OSError` raw (2 write calls) | same | same |
| `unseal` from a source raising a non-`OSError` | at the first read: `CannotOpen` ("cannot be opened"); after 1 or 3 reads: the source's own exception | | |
| `seal` into a sink raising a non-`OSError` | returned normally | `BlobError: cannot seal: <name>: …` | |

So the reading direction did **not** swallow a failed write: `decrypt_io` let it through, `fetch_blob` raised, and `blob get` reported `cannot write <file>: <reason>` through its `except OSError`. The command line: a real write failure of `blob get`'s temporary output is provoked with `RLIMIT_FSIZE` = 256 KiB on a 1 MiB blob, in-process (CPython ignores `SIGXFSZ`, `signal.getsignal(signal.SIGXFSZ)` = `SIG_IGN`), and so is the sealed temporary file of `append --attach`. Found along the way: with a **buffered** temporary file the failure surfaced at the close, not inside `pyrage` — for `append --attach` that turned the `BlobError` into a bare `OSError: [Errno 27] File too large` out of `ExitStack`, and for `blob get` the failure reached only the `except OSError` after `fetch_blob` had returned.

Also measured: `encrypt_io` does not finish a short write; with a sink that took 7 bytes a call it raised `cannot seal: failed to write the buffered data`.

### What moved where
- `core/sealing.py`: `seal` and `unseal` run `pyrage` through `_through`, with a `_WatchedSource` and a `_WatchedSink` that record whatever their `read`/`write` raised. After the call (returned or raised): a source `OSError` → `SourceUnreadable(reason)`, a sink `OSError` → `SinkUnwritable(reason)`, any other recorded exception → raised as itself (a store's error now comes through even at the header). Only then `pyrage`'s own refusal → `BlobError("cannot seal: …")` / `CannotOpen(…)`. `_WatchedSink` finishes short writes and fails on a write that takes nothing (`the output took no bytes`). Docstrings of `seal`/`unseal` carry the measurements.
- `core/errors.py`: new `SinkUnwritable(BlobError)` with `reason`; `reason_of` moved here (now `strerror`, else the error's text, else the class).
- `core/blob.py`: `seal_into`, its two watchers and `reason_of` removed. `store_blob` calls `seal` and maps `SinkUnwritable` → `BlobError("cannot write a temporary file: <reason>")`; the temporary file is `TemporaryFile(buffering=0)`. `fetch_blob` docstring names `SinkUnwritable` (no size returned).
- `cli.py`: the `blob get` temporary output is `os.fdopen(…, buffering=0)`; `_fetch_to` maps `SinkUnwritable` → `cannot write <file>: <reason>`; `reason_of` imported from `core.errors`.
- `docs/explanation/blobs.md`: two sentences — a fetch whose writing failed doesn't return and nothing is renamed; why sealing and opening watch for themselves.

### Tests, RED and GREEN
- `tests/test_sealing.py`: `test_seal_into_a_sink_that_fails_does_not_return` [12, 70000], `test_unseal_into_a_sink_that_fails_does_not_return` [12, 70000], `test_a_source_that_fails_is_told_apart_from_a_sink`, `test_a_sink_that_takes_less_gets_the_rest_and_one_that_takes_nothing_fails` [12, 70000]. RED before the change: `5 failed, 14 passed` (the short-write test was added after). GREEN `21 passed`.
- `tests/test_blob.py`: `test_a_fetch_into_a_sink_that_fails_returns_no_size` [12, 70000] replaces the `seal_into` test.
- `tests/test_cli.py`: `test_blob_get_whose_output_cannot_be_written_leaves_nothing` (`Error: cannot write <target>: File too large`, directory empty), `test_a_sealed_form_that_cannot_be_written_appends_nothing` (`Error: cannot write a temporary file: File too large`, no event, empty bucket). The second was red at first with the buffered temporary file (`OSError: [Errno 27] File too large` out of `ExitStack`).
- Existing `test_a_source_that_breaks_off_while_sealing_is_a_blob_error` unchanged: `SourceUnreadable` is a `BlobError`, and `reason_of` keeps the text of an `OSError` without an errno.

### Mutations (script in the scratchpad; each file restored and checked)
| Mutation | red | green control |
|---|---|---|
| `_through` raises no recorded failure | both sink tests ×2, source test, `test_a_fetch_into_a_sink_that_fails_returns_no_size` ×2 (7 failed) | `test_what_is_sealed_opens_to_the_same_bytes` |
| `_WatchedSink` passes one write and its count on | short-write test ×2 (`cannot seal: failed to write the buffered data`) | `test_what_is_sealed_opens_to_the_same_bytes` |
| `_fetch_to` without the `SinkUnwritable` translation | `test_blob_get_whose_output_cannot_be_written_leaves_nothing` | round-trip test |
| `_fetch_to` leaves the temporary file | same | round-trip test |
| `store_blob` temporary file buffered again | `test_a_sealed_form_that_cannot_be_written_appends_nothing` | round-trip test |
| `store_blob` without the `SinkUnwritable` translation | same | round-trip test |

Note: before `blob get`'s output was unbuffered, the `SinkUnwritable` translation in `_fetch_to` could be taken out without a test going red — the failure came at the close; that is why the output is unbuffered now.

### Interface as it now stands
`previously.core.sealing` (public):
- `recipient_of(identity: str) -> str`
- `check_recipient(recipient: str) -> None`
- `seal(source: ByteSource, sink: ByteSink, recipient: str) -> None`
- `unseal(source: ByteSource, sink: ByteSink, identity: str) -> None`
- `class HashingSink(sink: ByteSink)` with `write(data: bytes, /) -> int`, `hexdigest() -> str`, `size: int`

`previously.core.blob` (public):
- `@dataclass(frozen=True) class Stored(address: str, size: int, uploaded: bool)`
- `address_of(source: SeekableSource) -> tuple[str, int]`
- `store_blob(store: BlobStore, source: SeekableSource, *, recipient: str) -> Stored`
- `fetch_blob(store: BlobStore, keys: KeyProvider, address: str, sink: ByteSink) -> int | None`

Removed since part one: `core.blob.seal_into`, `core.blob.reason_of`. New/moved: `core.errors.SinkUnwritable(reason: str)`, `core.errors.reason_of(error: OSError) -> str`. Unchanged from part one: `core.hashing.is_address`, `core.errors.SourceUnreadable(reason: str)`.

### Counts and gates
- Tests: **563** (554 + 9: sealing 7, cli 2; blob ±0). `print` count: 30.
- `uv run ruff check .` → `All checks passed!`
- `uv run ruff format --check .` → `69 files already formatted`
- `uv run pyright` → `0 errors, 0 warnings, 0 informations`
- `uv run lint-imports` → `Contracts: 6 kept, 0 broken.`
- `uv run pytest --cov --cov-report=term-missing` → `======================== 563 passed in 61.46s (0:01:01) ========================` (`Total coverage: 98.25%`)
- `make -C docs html` → `build succeeded.`; `make -C docs vale` → `✔ 0 errors, 0 warnings and 0 suggestions in 24 files.`; `make -C docs linkcheck` → `build succeeded.` (0 broken)
- `uv run pytest -p no:randomly` → `======================== 563 passed in 63.64s (0:01:03) ========================`

### Concerns
- The two command-line tests lower `RLIMIT_FSIZE` for the whole test process during one `main()` call; anything else that grew a file past 256 KiB in that window would fail too. Nothing did in four runs, and the soft limit is put back in `finally`.
- Unbuffered temporary files mean one system call per `pyrage` piece; `test_memory_stays_bounded` (256 MiB) stayed green, and its time was not compared.

---

## Fix round 2

Commit `ea62154` on top of `7bc8f4a`. Measurements 2026-10-05.

### Who owns the short write
`core.sealing._WatchedSink` — the outermost sink `pyrage` sees in `seal` and `unseal` — is the one place that finishes a short write. Everything it wraps passes on the count of what was taken and does not retry. `HashingSink.write` now calls the inner sink first, hashes and counts `data[:taken]`, and returns `taken`; every byte is counted once, when the sink takes it. Both docstrings say so.

### RED and GREEN
- New `tests/test_blob.py::test_a_fetch_into_a_sink_that_takes_little_at_a_time_is_whole_and_counted_once` [12, 70000]: `fetch_blob` into a sink that takes seven bytes a call returns the true size and the bytes are the content.
- RED before the fix: `AddressMismatch: the object 30d62400… opens to b47a1a08…` (12 bytes) and the same at 70,000 bytes, on correct bytes.
- GREEN: `tests/test_blob.py tests/test_sealing.py` → `40 passed`.

### Mutations
| Mutation | red | green control |
|---|---|---|
| `HashingSink` hashes and counts what it was given again (`update(data)`, `size += len(data)`) | both cases of the new test | `test_the_hashing_sink_counts_and_hashes_what_passes`, `test_the_same_content_twice_is_one_object` (`2 failed, 2 passed`) |
| `blob get` writes straight into the target | `test_blob_get_whose_output_cannot_be_written_leaves_nothing` [no-target] and [existing-target] | `test_blob_get_of_an_address_no_event_uses_returns_1` (`2 failed, 1 passed`) |

### Sealing direction
No such composition there. `seal`'s sink chain is `_WatchedSink` → the caller's sink (in `store_blob` the unbuffered temporary file); no counting wrapper sits between them. The address is computed in a separate pass (`address_of`) over the source, not from what passes through the sink. `test_a_sink_that_takes_less_gets_the_rest_and_one_that_takes_nothing_fails` holds `seal` and `unseal` with a short-writing sink directly; the new test holds `unseal` behind `HashingSink`, which is how `fetch_blob` uses it.

### Riding along
- `tests/test_cli.py::test_blob_get_whose_output_cannot_be_written_leaves_nothing` is parametrized [no-target, existing-target]; with an existing target holding `what stood here before`, it is byte for byte unchanged and the directory holds only it.
- `src/previously/storage/s3.py`, `_Stream` docstring: `pyrage` let a later read's exception pass and turned the first read's into `DecryptError` (measured 2026-10-05); `unseal` now raises the stream's own in both cases.

### Counts and gates
- Tests: **566** (563 + 3: blob 2, cli 1).
- `uv run ruff check .` → `All checks passed!`
- `uv run ruff format --check .` → `69 files already formatted`
- `uv run pyright` → `0 errors, 0 warnings, 0 informations`
- `uv run lint-imports` → `Contracts: 6 kept, 0 broken.`
- `uv run pytest --cov --cov-report=term-missing` → `======================== 566 passed in 62.37s (0:01:02) ========================` (`Total coverage: 98.25%`)
- `make -C docs html` → `build succeeded.`; `make -C docs vale` → `✔ 0 errors, 0 warnings and 0 suggestions in 24 files.`; `make -C docs linkcheck` → `build succeeded.` (0 broken)
- `uv run pytest -p no:randomly` → `======================== 566 passed in 61.37s (0:01:01) ========================`
