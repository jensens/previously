# Task 6 review — blobs at the event (8ca910d..bc8ebdb)

Reviewer: task-scoped gate, 2026-10-05.
Read the diff file once, in four passes: source; migration and schema; tests; documentation.
No changed file was re-read separately.
Focused checks outside the diff, each for a named risk:

- **Secret in text / foreign error out of the CLI:** `storage/s3.py` `from_settings`, `_refused`, `_translated` (lines 85–160, 296–330), and `storage/errors.py` class list. Then one probe of `from_settings` with a malformed endpoint and region, and one call of `cli.main` with `PREVIOUSLY_BLOB_ENDPOINT=localhost:9000` (no database reached).
- **Secret in an exception context:** probe of `pyrage.x25519.Identity.from_str` on a malformed identity (message `invalid Bech32 encoding`, no identity text).
- **Write failures named correctly:** probe of `core.sealing.unseal` into a sink whose `write` raises `ENOSPC` (passes through as `OSError`), and of `core.sealing.seal` into such a sink (becomes `BlobError("cannot seal: OSError: [Errno 28] …")`).
- **`verify` raising on a forged redaction:** `core/redaction.py` validates `target.blobs` with `_BLOB_ADDRESS` (line 122), so `bytes.fromhex` in `_register_findings` cannot raise.
- **Protocol count comment:** the `grep` from `contract/store.py`, run over the five modules: 11 distinct names, as claimed.

No test suite was run.

### Spec Compliance

- ❌ Issues found:
  - The exit-code table on `docs/reference/cli.md:15` claims "a blob setting is missing **or invalid**" → 2. A malformed `PREVIOUSLY_BLOB_ENDPOINT` or `PREVIOUSLY_BLOB_REGION` escapes `main` as a foreign traceback. See Important 1.
  - Ruling T6-a(2) asks that every `OSError` on the blob path become one *named* sentence. A temporary file that fails while it is **written** is reported as `cannot seal: OSError: [Errno 28] …`, not as the `cannot write a temporary file: …` the comment and the page promise. See Important 2.
  - Everything else of the brief and of T6-a is there:
    - The interfaces, with the signatures as given.
    - The schema and migration `0004`, identical, with the downgrade refusal.
    - All 4 + 6 + 4 + 11 named tests; the three brief mutations and the T6-a mutations, with red and green controls reported.
    - The seven variables, each read only by the command that needs it.
    - The address checked first; `blob get` through a temporary file in the target's directory, renamed with `os.replace`.
    - `show` from the log only, the register in the event's transaction, and `redact_event` filling `blobs` from the register.
    - `verify` with a register finding for live and erased events.
    - The five handed-over items and the recipient check.
    - The S3 fix at the cause, with no collection and no hand-written multipart upload. `test_s3.py` has a red-without-fix test, and the release test now holds the "on error" half (5 vs 1 under close-on-success-only).
  - Every contractual wording I checked against the table matches character by character: the register finding, `blob get` (four errors, stderr notice, stdout line), the attachment input error, the reserved-key sentence with its em dash, the address input error, `<VARIABLE> is not set`, and the `show` blob line.
- ⚠️ Cannot verify from diff:
  - The table's `show` suffix ` <erased by event <id>>` for an erased *reference*. That needs blob erasure (task 7), and nothing in this diff prints it. I took it as out of scope.
  - The admonition count per page: only the hunks of `blobs.md` are visible.
  - The reported gate and mutation outputs: taken as reported, not re-run.

### Strengths

- **The secret leak in `storage/keys.py` was found by a real test, and the fix is right.**
  - It decodes inside the `try`, records only the class name, and raises after the `except`. With nothing being handled at the raise, `__context__` is `None`, and the `UnicodeDecodeError` with its bytes is gone.
  - `tests/test_keys.py::_chain` walks cause and context recursively, and the assertion message is a bare flag, so a failure cannot print the identity.
  - I looked for the same pattern across the diff and the blob modules it touches:
    - `sealing._identity`: the `IdentityError` context carries only `invalid Bech32 encoding`.
    - `unseal`'s `DecryptError` context, and the `from error` chains in `_attach`, `_fetch_to` and `_cmd_blob_get`: none carries an identity, a credential or a response.
    - `s3._refused` and `_translated` build from code and class names only.
  - No second instance.
- **The T6-a(1) fix is at the cause, and the docstring is a measurement.**
  - It records the referrer chain, which half of the fix does the work (traceback let go: 1; traceback kept: 4), and why the error is not chained anyway.
  - `test_main_releases_the_blob_store_it_opened` now has the failing path it lacked, with all three figures (1/5/13) in its docstring.
- **Write order and transaction are right.**
  - The order is blob first, then the event.
  - The register rows go into `insert_event` inside `append`'s one transaction (`core/append.py`, the `storage.insert_event(..., ready.blobs)` call). A lost race rolls them back with the event.
  - `redact_event` reads the register after the lock.
- **`chain.prepare` is the single place that mixes in `blobs`, and it rejects the reserved key whether or not attachments are present.**
  - `read_references` is a strict reader of the stored form: `bool` is rejected as a size, and keys must match exactly.
  - It is used identically by `verify` and `show`.
- **`_Watched` is a precise answer to pyrage's flattening of source errors.** It was measured before and after.
- **`blob get` is careful in the main ways.**
  - The temporary file is in the target directory, is mode 0600, and is unlinked on every non-success path.
  - The test asserts the directory listing, not just the target.
- **Comments that were already false were corrected rather than extended:**
  - the `postgres.py` method list;
  - the `0003` downgrade comment;
  - the "six tables" and "nine subcommands";
  - the `cli.md` 12000/12001 example.

### Issues

#### Critical (Must Fix)

None.

#### Important (Should Fix)

1. **A malformed blob endpoint or region escapes `main` as a Python traceback.**
   - Where: `src/previously/cli.py:213-224` (`_blob_store` → `from_settings`) and `docs/reference/cli.md:15`.
   - What happens: `from_settings` passes `endpoint` and `region` straight to `Session().client(...)`, which validates them at construction.
     - Measured: `endpoint="localhost:9000"` raises a bare `ValueError("Invalid endpoint: localhost:9000")`.
     - `region="us east 1"` raises `botocore.exceptions.InvalidRegionError`.
     - Neither is a `PreviouslyError` or a `StorageError`. `main(["append", …, "--attach", f])` with the scheme-less endpoint raised `ValueError` out of `main` (measured; no database was reached).
     - So `append --attach` and `blob get` print a traceback and exit 1 for a typo in the environment.
   - What it breaks:
     - The `cli.md` exit-code row "a blob setting is missing or invalid" → 2.
     - "Nothing foreign leaves" for a `botocore` type.
     - The one-sentence rule the ruling stands on.
   - No secret appears (checked: neither message holds the secret key).
   - Fix: translate it where it is raised, in `storage/s3.py` `from_settings`, into `BlobStoreRefused` ("the settings for the blob store at … are not usable: …", the existing `_translated` wording). Add a CLI test with a scheme-less endpoint, and a mutation.

2. **A temporary file that fails while it is written is not reported as `cannot write a temporary file`. The comment and the page say it is.**
   - Where: `src/previously/core/blob.py:100`, `:110-120`, and `docs/reference/cli.md:53-56`.
   - Claims made:
     - The docstring says `BlobError` "when the temporary file cannot be made, written or read".
     - The comment says "Every `OSError` in this block is about the temporary file: making it, writing the sealed form into it…".
     - The page says a temporary file "that can't be created or written" gives `Error: cannot write a temporary file: <reason>`.
   - Measured: writes into the temporary file happen inside `pyrage.encrypt_io`, and `pyrage` wraps a sink's `OSError` exactly as it wraps a source's. A sink raising `ENOSPC` gives `BlobError("cannot seal: OSError: [Errno 28] No space left on device")`. That `BlobError` never reaches the `except OSError` at `blob.py:119`.
   - It is still one sentence with exit 2, so the behavior is acceptable. The comment and the page are false, and the message carries a foreign class name and errno, which is what T6-a(2) asked to name.
   - The tests do not see it: the only provoked case is `mkstemp`/`TemporaryFile` creation (`PermissionError`). That is outside `encrypt_io`.
   - Fix: let `_Watched` (or a sibling wrapper on the sink) remember a sink `OSError` too, and raise `BlobError("cannot write a temporary file: …")` from `_seal_into`. Otherwise, correct the comment, docstring and page to "created". A test with a sink that fails on write would close it.

#### Minor (Nice to Have)

1. **`put` breaks the chain; `stat`, `get` and `delete` keep it.**
   - Where: `src/previously/storage/s3.py:176, 229, 243` vs `:205-214`.
   - The asymmetry is defensible as measured: only `put` runs through the transfer manager's cycles. An operator still gets endpoint, bucket and S3 code; the lost botocore text adds little.
   - But the docstring's second reason ("so that a caller who keeps the error … does not keep the foreign one") applies equally to the other three methods, and they do not follow it.
   - Either drop that reason from `put`'s docstring, or say there why the others may chain.

2. **`except OSError` in `store_blob` wraps `store.put`.**
   - Where: `src/previously/core/blob.py:117-120`.
   - Any raw `OSError` from the store path would be reported as "cannot write a temporary file". Reading the temporary file for the upload happens inside `put`, so the wrapping is deliberate. The comment's "the store raises its own errors" is an assumption about botocore wrapping every socket error, and nothing measures it.

3. **No test provokes a write failure while content passes into the temporary output of `blob get`** (the implementer's own concern).
   - I probed that `unseal` lets a sink's `ENOSPC` through as `OSError`, so `_fetch_to`'s second `except` (`cli.py:623`) catches it. The page claim at `cli.md:346` therefore holds by reasoning.
   - Only the `os.replace` trigger exercises that branch. A sink-side failure could be provoked without a full disk, for example with `RLIMIT_FSIZE`, which `tests/test_blob.py` already imports `resource` for.

4. **The docs check cannot tell `cannot write the temporary file: …` from `cannot write <file>: <reason>`** (the implementer's measured limit).
   - Where: `tests/test_docs_references.py`.
   - It is a real gap in the gate, but small. One fix: hold the temporary-file block against `core/blob.py` patterns only.

5. **The writer accepts what the reader refuses.**
   - Where: `src/previously/core/chain.py:80-98`.
   - `_references` does not check that `size` is a non-`bool` `int`, that `media_type` and `filename` are `str`, or that `filename` is non-empty and has no directory part.
   - A library caller with `size=True` gets an event that `prepare` writes and `read_references` then rejects. `verify` would report the register finding on an event `core` itself wrote.
   - pyright prevents this for typed callers. Mirroring `_read_reference`'s checks would make the two agree by construction.

6. **`error.strerror` can be `None`.**
   - Where: `src/previously/cli.py:352, 615, 624`.
   - An `OSError` raised without an errno prints `…: None`. `core.blob._reason` already has the fallback (`strerror or type(error).__name__`); the CLI does not use it.

7. **The leak test is skipped as a whole for root.**
   - Where: `tests/test_keys.py:113-118`.
   - The `not-utf-8` case does not depend on permissions, but the `skipif` covers both parameters. Under root (common in containers) the regression test for the leak this task fixed does not run.
   - Skip only the `no-permission` case.

8. **The `blobs` key in pre-existing payloads.**
   - `read_references` now interprets a top-level `blobs` key in every payload. An event written through the library before this task with its own `blobs` key, which was not reserved then, would now draw the register finding.
   - It is unlikely for the CLI, whose payload is `{"text": …}`. It is worth one sentence where the reservation is explained.

9. **Duplicate address regex.**
   - Where: `src/previously/core/redaction.py:47`.
   - `_BLOB_ADDRESS` duplicates `core.blob.is_address` (the implementer's concern 4). Two spellings of one rule.

10. **Test docstrings cite "Assurance 17/18 of the 2026-10-04 stage 1c specification".**
    - Where: `tests/test_cli.py:1949, 2001`.
    - The global constraints allow pages, and `review focus N` / `ruling X` of the plan; this is a numbered item of the unfrozen specification. The reason does stand beside it, so it is provenance only, but it is a form the constraints do not list.

11. **Other implementer concerns, as reported:**
    - `_register_findings` skipping a payload tombstone without a redaction (`core/verify.py:414-424`) has no mutation test.
    - The release test makes twenty `main` calls and uploads 9 MiB per round, which is a cost, not a defect.

Judged on their merits and accepted:

- The four new public names, each used across modules or by a test that deserves it.
- `guess_file_type` with the compression-suffix rule (the right call for a path).
- The changed `test_migration_0003.py` expectation (correct: one transaction rolls back `0004`'s downgrade too).
- The new `cannot write <file>: <reason>` sentence (needed, quoted, held by the docs test).
- Validation in `chain.prepare` rather than `append`.

### Assessment

**Task quality:** Needs fixes

**Reasoning:**

- The implementation meets the brief and ruling T6-a almost everywhere, and the leak fix and the connection fix are measured at their cause.
- Two places still break the one-sentence promise this task exists to keep:
  - A malformed endpoint or region crashes both blob commands with a foreign traceback, contrary to the exit-code table.
  - A temporary-file write failure is described falsely in a comment and on the reference page.
