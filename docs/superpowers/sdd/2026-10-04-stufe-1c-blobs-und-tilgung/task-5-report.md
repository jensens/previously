# Task 5 report: blobs as a library (sealed, stored, fetched)

Status: DONE_WITH_CONCERNS (concerns at the end). Commit `13d0d5e` on top of `eb81651`. Every measurement below was taken on 2026-10-05 on this tree.

## What was implemented, step by step

1. **Dependencies.** In `pyproject.toml`, `boto3>=1.43` and `pyrage>=1.4` went under `dependencies`, and `pyrage-stubs>=1.4` and `types-boto3-lite[s3]>=1.43` under `dev`. All four are floors. `uv lock` then added 12 packages. Four rows went into `DEPENDENCIES.md`, plus a paragraph on the `rustfs/rustfs:1.0.1` image.
2. **Contracts.** I added two `forbidden` contracts to `.importlinter`. Each has the whole package as its source and its exemptions named one by one. Each has a comment giving the reason. The header count now reads "Five of the six", and `CLAUDE.md` now reads "the six contract names". I changed only that number in `CLAUDE.md`. `tests/test_contracts.py` now accepts a probe path and sweeps both probe locations. It has two new tests: a `boto3` probe in `core` and a `pyrage` probe in `storage`.
3. **Sealing.** I wrote `core/sealing.py`, which has `seal`, `unseal`, `recipient_of` and `HashingSink`. The two `cast`s carry the sentence the brief asks for. The error classes went into `core/errors.py`: `BlobError`, `InvalidKey`, `CannotOpen` and `AddressMismatch`.
4. **Keys.** I wrote `storage/keys.py` with `DirectoryKeys`. A `key_id` must match `age1[a-z0-9]+` in full before it becomes part of a path. Comment lines and empty lines are skipped. The `repr` shows only the directory.
5. **Adapter.** I wrote `storage/s3.py` with `S3BlobStore` and `from_settings`, and added `BlobStoreUnreachable` and `BlobStoreRefused` to `storage/errors.py`. I added the `_Stream` wrapper, the client configuration (connect timeout 5 s, `standard` retry mode, 2 attempts in total), and `close()` under ruling T5-a. The `conftest.py` fixtures are `s3_settings` (one container per session), `blob_store` (a fresh bucket per test, closed afterwards), `age_identity` and `other_age_identity`. The `s3` marker is registered.
6. **Store and fetch.** I wrote `core/blob.py` with `Stored`, `address_of`, `store_blob` and `fetch_blob`.
7. **Sentences that were no longer true.** I fixed:
   - the counts in `.importlinter` and `CLAUDE.md`;
   - the job comment in `gates.yml`, which now names the S3 server and says "its own containers";
   - the module docstring of `conftest.py`;
   - the two tutorial sentences about Docker and the test suite.
8. **Pages.** I wrote the new page `docs/explanation/blobs.md` with the label `(blobs)=` and added it to the index. In `module-boundaries.md` I added the section "Two contracts for the blobs" and retyped the gate output. I also updated the intro count, the heading and the diagram, which now has the `pyrage` and `boto3` arrows.
9. **Tutorial.** I retyped the tutorial's test run from a real `uv run pytest` run, without the `rootdir:` line: `458 passed`.

## Dependency checks (2026-10-05)

I queried the PyPI JSON API, the GitHub API and the Docker Hub API with scratch scripts.

**`boto3` 1.43.108**
- Released 2026-10-02. There was a release on each of 09-29, 09-30, 10-01 and 10-02.
- `boto/boto3` was pushed 2026-10-02, is not archived, and is Apache-2.0.
- It brings in `botocore` 1.43.108 (2026-10-02), `s3transfer` 0.19.2 (2026-07-22) and `jmespath` 1.1.0 (2026-01-22).
- Judgement: active.

**`pyrage` 1.4.0**
- Released 2026-08-23. Earlier releases were 2025-06-14 and 2025-04-02.
- `woodruffw/pyrage` was pushed 2026-09-30, its last commit was 2026-09-27, it is not archived, and it is MIT.
- The wheel is `cp310-abi3`, has no Python dependencies, and its SBOM lists the Rust crate `age` at 0.12.1.
- Its `RECORD` holds no `py.typed` and no `.pyi`.
- Judgement: released rarely, but acceptable, because the judgement rests on the format and not on the binding.

**`pyrage-stubs` 1.4.0**
- Released 2026-08-23, from the same repository, MIT.
- Judgement: active, needed only for type checking.

**`types-boto3-lite[s3]` 1.43.108**
- Released 2026-10-02, and generated daily.
- It brings in `types-boto3-s3` 1.43.106 (09-30), `botocore-stubs` 1.43.67 (08-08) and `types-s3transfer` 0.16.0 (2025-12-08).
- Why `lite`: the 2026-10-04 measurement, plus today's tree, where pyright reports 0 errors.
- `boto3` and `botocore` ship no `py.typed`; I checked.

**`rustfs/rustfs:1.0.1`**
- The tag was pushed on 2026-10-03.
- The repository is Apache-2.0, was pushed 2026-10-04, and is not archived.

**MinIO, which the rows name as the rejected alternative**
- `minio/minio` is archived.
- Docker Hub answers 404 for `minio/minio`.
- The Python SDK's last release is 7.2.20, on 2025-11-27.

**Audit.** `uv run pip-audit --skip-editable` reported `No known vulnerabilities found`. I ran it after locking and again before the commit.

## TDD evidence

**Contracts.**
- RED: `uv run pytest tests/test_contracts.py`. The two new tests failed with `assert 0 != 0`: the gate output was `Contracts: 4 kept, 0 broken.` because the contracts did not exist yet. That was the expected failure.
- GREEN: 4 passed.
- Measured along the way: before `core/sealing.py` existed, `lint-imports` failed with `No matches for ignored import previously.core.sealing -> pyrage.` So an exemption cannot outlive the edge it names. This is the reason all of the work is in one commit (see Departures).

**Sealing.**
- RED: an `ImportError` at collection (`cannot import name 'BlobError'`), because the module and the error classes did not exist.
- GREEN: 14 passed.

**Keys.**
- RED: a collection error, because the module did not exist.
- GREEN: 9 passed.

**Adapter.**
- `conftest` imports `storage.s3`, so the RED was a collection error.
- GREEN: 10 passed on the first run.
- Because that RED proves little, the meaningful red for each assurance comes from the mutations below.
- `close`: RED with `AttributeError: 'S3BlobStore' object has no attribute 'close'`, then GREEN.

**Store and fetch.**
- RED: a collection error.
- GREEN: 11 passed. With the two tests added later, 12 pass.

## Mutations

I made each mutation in the tree and restored the file from a scratch copy. For `.importlinter` I also restored from a copy.

| Mutation | Red | Stayed green |
|---|---|---|
| `.importlinter`: exemptions widened to `previously.** -> pyrage` and `previously.** -> boto3` | both new contract tests | `test_import_contracts_hold`, the sqlalchemy probe test |
| `keys.py`: the `fullmatch` check replaced by `if False:` | `[../x]`, `[/etc/passwd]`, `[]`, `[AGE1ABC]` (4 failed) | the other 5 tests. Note: `[age1../x]` stays green under this mutation, because `keys/age1../x` doesn't exist. It is a weak case, and I report it rather than contrive a fixture for it. |
| `s3.py`: `get` returns the raw `response["Body"]` | `test_a_read_that_breaks_off_is_a_storage_error`, with `botocore.exceptions.ResponseStreamingError: ... IncompleteRead(25165824 bytes read, 41943040 more expected)` | the other 9 |
| `s3.py`: `connect_timeout` and `retries` removed | `test_an_endpoint_nobody_listens_on_is_unreachable_within_seconds`: `assert 5 == 2` (5 sends). On the first try, before I reordered the asserts, it was red on the time at 3.9 s and then at 5.9 s. | the other tests in the file |
| `s3.py`: `self.stat(address)` before `get_object` | `test_get_gives_metadata_and_body_from_one_answer`: `['HeadObject', 'GetObject'] == ['GetObject']` | the other 9, the round trip among them |
| `s3.py`: `close()` body set to `pass` | `test_close_releases_the_connections_the_store_opened`: `assert 5 <= 2` | its own control, `_established(port) > before` while the store is open, stays green in the GREEN run |
| `store_blob` uploads the source unsealed (sealing removed) | `test_the_store_sees_only_ciphertext`: the bucket holds the plaintext | `test_the_same_content_twice_is_one_object` |
| `store_blob` doesn't ask `stat` (`if False:`) | `test_the_same_content_twice_is_one_object` and `test_after_a_key_change_the_stored_object_keeps_its_key`, both with `assert not True` (`uploaded=True`) | `test_the_store_sees_only_ciphertext` |
| `fetch_blob` doesn't compare the address | `test_an_object_under_a_foreign_address_is_not_delivered`: `DID NOT RAISE AddressMismatch` | `test_a_missing_object_is_none` |
| `fetch_blob` reads in one piece (`unseal(io.BytesIO(stream.read()), …)`) | `test_memory_stays_bounded`, with growth of 502 MiB alone, 502 MiB in the full suite in fixed order, and 453 MiB in the full suite in random order | `test_the_store_sees_only_ciphertext` |
| `fetch_blob` takes the key from the caller's recipient (thread-local `_CALLER.recipient` set in `store_blob`, used in place of `stored.key_id`) | `test_two_writers_at_once_leave_one_whole_object_that_opens`, with `CannotOpen: No matching keys found`, in 3 runs out of 3 | `test_the_same_content_twice_is_one_object` |
| `store_blob` writes `key_id=recipient` without lowering it | `test_a_recipient_in_upper_case_is_written_beside_the_object_in_lower_case` (the key comes back in upper case) | `test_the_same_content_twice_is_one_object` |

**Two writers, rounds and winners.**
- Over 50 rounds at `ROUNDS=10`, writer 0 won 28 and writer 1 won 22.
- Over 48 rounds at `ROUNDS=16`, writer 0 won 25 and writer 1 won 23.
- Both writers uploaded in all 48 rounds of the second set.
- Total: 53 against 45 over 98 rounds. I set `ROUNDS = 16`, where all rounds going one way has a chance of about 1e-4.
- In my test both writers fetch in every round, so every round has a loser that fetches, and the mutation goes red in round 1.
- The test still requires both outcomes, as the brief asks.

**The identity check (does the identity belong to the `key_id`?).**
- With the check removed, `test_an_identity_file_that_holds_another_key_cannot_open` stayed green: `age` refuses the identity on its own with `CannotOpen: No matching keys found`.
- So the check added nothing, and I removed it. The comment in `fetch_blob` says so, with the date.

## My measurements

**`measure_rustfs.py`, peak memory.**
- 16 MiB: 85 MiB peak.
- 256 MiB: 183 MiB peak.
- 1 GiB: 183 MiB peak.
- Timings at 1 GiB: seal 1.04 s, upload 2.58 s, fetch and open 2.66 s.
- The sealed form was 262,406 bytes larger than the content. The address matched every time.
- A fresh bucket has no versioning, and a delete leaves 0 versions and 0 delete markers.

**`measure_race.py 64 20`.**
- The surviving object was sealed by `a` 13 times and by `b` 7 times. It was never torn, and its metadata never belonged to the other writer.
- What the reader saw:

  | Outcome | Count |
  |---|---|
  | `NoSuchKey` | 2672 |
  | `ResponseStreamingError` | 17 |
  | the right plaintext | 3 |

- `If-None-Match`: a plain `put_object` was refused the second time with `PreconditionFailed`. `upload_fileobj` rejects `IfNoneMatch` with a `ValueError`.

**Unreachable endpoint (`http://127.0.0.1:1`).**
- Default configuration, 10 calls: 1.95 to 11.95 s.
- My configuration, 20 calls: 0.11 to 0.89 s.
- Against `10.255.255.1`, which drops packets: the default had not failed after 200 s (killed by `timeout`). Mine failed in 10.49 s and 10.02 s.
- The test bounds a call at 3 s and requires exactly 2 attempts. The attempt count, not the time, is what makes it deterministic: the default backoff is random, and the default once failed in 1.95 s.

**Memory bound (256 MiB, `BOUND_MIB = 256`).**
- The path with the test run alone: +120 MiB in three runs out of three.
- The path after the other S3 tests: +0 MiB.
- The mutation alone: +478, +502 and +502 MiB.
- The mutation after the other S3 tests: +395 MiB.
- The mutation in the full suite: +502 MiB in fixed order and +453 MiB in random order.

**Sockets (ruling T5-a).** I counted with `/proc`, with the garbage collector off.
- A plain `boto3` client with small objects: 1 socket established while the client lives, 0 after `del`, over 10 uses. Nothing stays open.
- Through the adapter, with a 20 MiB `put` (an upload in parts) and an abandoned stream in every second use: 3, 5, 8 … 50 sockets left established after `del`, piling up over 20 uses, and 0 only after `gc.collect()`. No `ResourceWarning` was shown, even under `-X dev` (count 0).
- With `client.close()` after each use: 3 while alive and 0 after, in every use.
- So `close()` was added: it is the fifth protocol method, `S3BlobStore.close()` calls `client.close()`, and a test holds it with the mutation above.

**A read that breaks off.**
- An object deleted after the first 8 KiB were read: 64 MiB broke in 5 of 5 rounds, and so did a second upload replacing it. At 4 MiB and 16 MiB the read finished (5+5 rounds each).
- The test passed in 10 runs out of 10.

## What the full test run costs with the second container

| Run (fixed order) | Wall time |
|---|---|
| `pytest -p no:randomly -m "not s3"`, no RustFS container | 34.25 s and 34.27 s |
| The full run | 44.81 s and 42.16 s |

So the second container and its 23 tests cost about 8 to 10 s. The gate runs took 41 to 44 s.

## Departures from the brief

- **`close()`, the fifth protocol method.** This is the one addition the brief sanctions (ruling T5-a), and the measurement asked for it.
- **`S3BlobStore` has public read-only properties `client`, `bucket` and `endpoint`.** The tests count client events and list versions without reaching into a private name. The fixtures create buckets through `client`.
- **`seal` translates `pyrage.EncryptError` into `BlobError("cannot seal: …")`.** I measured that `pyrage` wraps an exception from the source into its own type when it seals. Without the translation a `pyrage` type would leave `core`.
- **`store_blob` writes `key_id=recipient.lower()`.** I measured that `age` accepts an upper-case recipient and that RustFS keeps the metadata's case. `DirectoryKeys` (per the brief) rejects upper case, so without this, such an object could never be opened.
- **`fetch_blob` lets `InvalidKey` through.** If the key file holds something that is not an identity, `InvalidKey` (a `BlobError`, and its message names no identity) passes through unchanged. It is not turned into `CannotOpen`. The docstring says so.
- **Additional tests beyond the brief's tables.**
  - `test_recipient_of_does_not_quote_a_malformed_identity`
  - `test_a_source_that_breaks_off_while_sealing_is_a_blob_error`
  - `test_close_releases_the_connections_the_store_opened`
  - `test_a_recipient_in_upper_case_is_written_beside_the_object_in_lower_case`
  - `test_an_object_whose_key_has_no_identity_cannot_be_opened`: this one covers a `CannotOpen` case the brief lists, and it closed a coverage gap.

  Two existing tests were extended:
  - The unreachable test also calls `put` and `delete`.
  - A key file with nothing but comments now yields `None`.
- **Fixture `other_age_identity`, not in the brief.** Tests that need two keys use it.
- **Two secrets are drawn at run time.** The test secret (`secrets.token_hex(16)`) and the wrong secret in `test_a_wrong_secret…` are generated, not written as literals. This removes the cause of ruff `S105` without a suppression, and no secret-looking literal stands in the public tree.
- **`.vale.ini` and the Vale vocabulary are not in the file list.** `ciphertext`, `ciphertexts` and `plaintext` went into `accept.txt`, and I recounted the comment in `.vale.ini` (now "Fifteen of the nineteen", with a date). Without them Vale reported 16 spelling errors on the new page.
- **Test count.** 410 + 48 = **458**, not 417:

  | File | New tests |
  |---|---|
  | contracts | 2 |
  | sealing | 14 |
  | keys | 9 |
  | s3 | 11 |
  | blob | 12 |

- **One commit instead of several.** Each split I considered would have left an intermediate commit red:
  - an unmatched exemption fails `lint-imports`;
  - `{ref}\`blobs\`` in code needs the page, or `test_docs_references` fails;
  - the typed count needs the tests, or `test_docs_typed_output` fails.
- **`tests/test_contracts.py` was generalized.** `_probe_module` takes a path, and the sweep fixture covers `_PROBES`.

## Sentences found no longer true and rewritten

- `.importlinter`: "Three of the four contracts …" now reads "Five of the six …", and the list of external packages now includes `pyrage`, `boto3` and `botocore`.
- `CLAUDE.md`: "four contract names" now reads "six".
- `gates.yml`: Docker is now needed for PostgreSQL and for the S3 server. The comment says "brings its own containers up", and "second route to either server" replaces "second PostgreSQL route".
- The `conftest.py` module docstring.
- `module-boundaries.md`:
  - "In stages 1a and 1b there are four of them" now reads "Through stage 1c".
  - "It's four `import-linter` contracts" now reads "six of them since stage 1c".
  - The heading "Four contracts" now reads "Six contracts", and the typed block was re-measured.
  - "Stage 1b paid it, which is why there's no parenthesis left to read" was rewritten: there are parentheses again, now for named exemptions.
  - "Two of the four contracts differ" now reads "Two of the first four".
  - The diagram caption, "The seventh arrow leaves the package", now reads "Three arrows leave the package".
- The tutorial: the prerequisites line on Docker, and the "raises its own PostgreSQL container" sentence.
- `.vale.ini`: the vocabulary count.
- Left as they were: the dated historical blocks in `module-boundaries.md` (`4 kept` in the 2026-10-03 measurement and in the "bolt" section). They are measurements with a date.

## Final lines of the gates (last run before the commit)

```
uv run ruff check .                 All checks passed!
uv run ruff format --check .        67 files already formatted
uv run pyright                      0 errors, 0 warnings, 0 informations
uv run lint-imports                 Contracts: 6 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing
                                    ============================= 458 passed in 43.98s =============================
                                    (Required test coverage of 90.0% reached. Total coverage: 98.25%)
make -C docs html                   build succeeded.
make -C docs vale                   ✔ 0 errors, 0 warnings and 0 suggestions in 24 files.
make -C docs linkcheck              build succeeded.
uv run pytest -p no:randomly        ============================= 458 passed in 41.48s =============================
uv run pip-audit --skip-editable    No known vulnerabilities found
```

There is no warnings summary in the pytest output. The measured test count is 458.

## Files changed

**New**
- `src/previously/contract/blobs.py`
- `src/previously/core/sealing.py`
- `src/previously/core/blob.py`
- `src/previously/storage/s3.py`
- `src/previously/storage/keys.py`
- `tests/test_sealing.py`
- `tests/test_keys.py`
- `tests/test_s3.py`
- `tests/test_blob.py`
- `docs/explanation/blobs.md`

**Modified**
- `pyproject.toml`
- `uv.lock`
- `DEPENDENCIES.md`
- `.importlinter`
- `CLAUDE.md`
- `.vale.ini`
- `.vale-styles/config/vocabularies/Previously/accept.txt`
- `.github/workflows/gates.yml`
- `src/previously/core/errors.py`
- `src/previously/storage/errors.py`
- `tests/conftest.py`
- `tests/test_contracts.py`
- `docs/explanation/index.md`
- `docs/explanation/module-boundaries.md`
- `docs/tutorials/record-your-first-event.md`

**Also written:** `task-5-commit-msg.txt` and this report, under `.superpowers/` (git-ignored).

`git status --short` before staging showed only my files. Both probe paths are absent, and the tree is clean after the commit.

## Self-review findings

- **No secret in any output.**
  - The identity is never in an `InvalidKey` message; `from None` drops `pyrage`'s cause.
  - `DirectoryKeys.__repr__` shows the directory.
  - `S3BlobStore.__repr__` shows the endpoint and the bucket.
  - Store errors name the endpoint, the bucket and the error code or exception type. A test checks that the wrong secret is in neither `str`, `repr` nor the formatted traceback chain.
- **No new suppression, no `# type: ignore`.** The only `except Exception` is in the test thread, which hands the error to the main thread; it catches `Exception`, not `BaseException`.
- **Every number in a comment, docstring or page comes from my runs today**, with one exception: the `.importlinter` and spec references to 2026-10-04 that are already dated. On the blobs page, I removed the "AES-GCM stops at 2 GiB" figure, because I did not measure it.
- **Figures still cited from 2026-10-04** (they come from the plan's spike, and today's tree agrees):
  - The `lite` stubs reasoning cites the 2026-10-04 draft measurement. Today I confirmed only that the tree reports 0 with `lite`; I did not re-measure the full flavor.
  - `stat` on a missing bucket returning 404 is cited as "2026-10-04 and again on 2026-10-05". The spike run today printed `missing bucket | stat: None`.

## Concerns

1. **The two-writer test needs both outcomes**, and so has a residual flake risk of about 1e-4 per run at 16 rounds. The 53/45 split was measured on this machine; a slower CI runner might skew it.
2. **`test_memory_stays_bounded` depends on `ru_maxrss` in KiB (Linux).** Inside the suite, the path's growth is usually 0 because earlier peaks hide it. The bound still caught the mutation in full suites, at 453 and 502 MiB.
3. **`test_close_releases_the_connections_the_store_opened` reads `/proc`, so it is Linux-only.** The gates run on `ubuntu-latest`, and testcontainers needs Linux Docker anyway, but the test would error rather than skip on macOS.
4. **`store_blob` does not validate the recipient when the object already exists.** A misconfigured recipient goes unnoticed until the first new content arrives. This is the template's behavior; I left it alone and flag it for task 6.
5. **The emergency path with the `age` tool is not measured.** Neither `age` nor `rage` is installed here, and the page says so.

---

# Fix round 1

Commit `8ca910d` on top of `0c8de69`. Every measurement in this section was taken on 2026-10-05.

## Per item

**I1 / ruling T5-b: the two-writer test.**
- The assertion that each writer wins at least once is gone, and so is the `winners` list.
- What stays: the per-round assertions that both writers fetch the content back, that the object opens to the address, that the key on the object is one of the two, and that there is one object per round.
- `ROUNDS = 4`. One round already contains a losing fetcher. Four rounds repeat the interleaving of the two uploads for about half a second. The comment at `ROUNDS` and the test's docstring now say this.
- Mutation (the caller's recipient used as the key, via the thread-local `_CALLER`): `uv run pytest tests/test_blob.py -p no:randomly -k "two_writers or same_content_twice"`.
  - Red in 3 runs out of 3, with `CannotOpen: No matching keys found`.
  - The control `test_the_same_content_twice_is_one_object` passed each time.
- The same mutation with `ROUNDS = 1`: red in 5 runs out of 5 (`1 failed, 12 deselected`).
- Without the mutation, 5 runs in random order: `1 passed` each time.

**I2: `module-boundaries.md`.**
- The sentence now covers only the two arrows from stage 1c (`pyrage` and `boto3`, each with the one module allowed to draw it named).
- It adds that the `sqlalchemy` arrow is held the other way round: its contracts name the modules that mustn't draw it, `core` and `contract`.

**Ruling T5-c: errors by kind.**
- `S3BlobStore._translated` replaces `_unreachable`. It decides by `botocore`'s own class hierarchy:
  - `botocore.exceptions.ConnectionError`, `HTTPClientError` and `IncompleteReadError` give `BlobStoreUnreachable`.
  - `IncompleteReadError` is named on its own because it sits directly under `BotoCoreError`.
  - Every other `BotoCoreError` gives `BlobStoreRefused`: "the settings for the blob store at …, bucket '…', are not usable: <class>".
- Which side the unknown falls on, and why: the refused side. Those errors come from the client's own checks, so calling them "not reachable" would send an operator to the network. The docstring of `_translated` says so.
- Measured what bad settings raise:
  - An empty access key gives a `ClientError` 401, which was already refused.
  - An empty secret gives a `ClientError` 403.
  - An empty bucket name, or one with a space, gives `ParamValidationError`.
- Tests:
  - Refused side: the new `test_settings_the_client_will_not_send_are_refused_not_unreachable` (`bucket=""`). It also checks that neither key is in the message.
  - Unreachable side: the existing test for an endpoint nobody listens on now also asserts `not reachable: EndpointConnectionError`.
- Mutations (`-k "not_send or nobody_listens or breaks_off"`):
  - `if True:` in place of the `isinstance` check: the refused test goes red (`ParamValidationError`). The read-break test stays green.
  - `if False:`: the unreachable test goes red. The read-break test and the refused test stay green.
- The docstrings of `storage/errors.py` were rewritten to match.

**Ruling T5-d: closing the stream.**
- `contract.blobs` has a new protocol: `ClosableSource(ByteSource, Protocol)` with `close() -> None`.
- `BlobStore.get` now returns `tuple[StoredBlob, ClosableSource] | None`.
- `_Stream.close()` calls `body.close()`. `fetch_blob` closes the stream in a `finally` on every path.
- New test: `test_a_fetch_that_fails_gives_its_connection_back`.
  - It runs four ways of failing three times each, with 4 MiB objects and the garbage collector off: no key, no identity, `age` refuses (garbage), and `AddressMismatch`.
  - It counts connections with the new `s3_connections` fixture, which moved to `conftest.py` and reads `/proc`.
- **One finding the ruling did not foresee.** With the stream closed on success only, the test first stayed green, 1 connection before and 1 after. An abandoned stream that nothing refers to is freed by reference counting, and its connection goes with it.
- The leak is real only when something keeps the error, because the traceback holds `fetch_blob`'s frame and the stream in it. A caller that collects the errors of a long run does exactly that.
- The test now keeps each `ExceptionInfo`:
  - Green: 1 connection before, 1 after.
  - Mutation (`stream.close()` moved inside the `try`, after `unseal`, the `finally` emptied): `AssertionError: 10 connections after the failed fetches, 1 before`, in 2 runs out of 2.
  - Control: `test_the_store_sees_only_ciphertext` stayed green.
- The comments in `fetch_blob` and `_Stream` now say this precisely: a connection is held "for as long as anything refers to it".
- The docstring explains the count of 10 as one connection for each of the nine streams left unread, plus the one the pool keeps. That breakdown is my reading of the number, not a separate measurement.

**Minor 1: key IDs.**
- `_RECIPIENT = age1[02-9ac-hj-np-z]{58}`.
- A file that is there but cannot be read (`OSError`, `UnicodeDecodeError`) raises the new `storage.errors.IdentityUnreadable(StorageError)`. The message has the path and the class, never the content.
- The parametrized test now has 7 cases, each with a file it would hit as a path. It gained `short` and `overlong` and got short ids.
- New test: `test_a_file_that_cannot_be_read_is_a_storage_error_that_shows_no_content`, with a directory in place of the file.
- Mutations:
  - No check (`if False:`): 7 of 7 cases red.
  - The old regex `age1[a-z0-9]+`: `short` and `overlong` red. `overlong` now fails with `IdentityUnreadable … OSError` rather than a bare `OSError`.

**Minor 3: addresses.**
- `_checked()` in the adapter, used by all four address methods. It raises `ValueError` with the wording from the plan's table: "`<address> is not a blob address: 64 hexadecimal characters, lower case`".
- New test: `test_an_address_that_is_not_one_is_a_caller_error_and_nothing_is_sent`, parametrized over 5 cases (empty, upper-case, short, parent, newline). It covers stat, get, put and delete, and counts `before-send` events (0).
- Mutation (no check): 5 of 5 red, the first with `ParamValidationError`. The control, the round trip, stayed green.

**Minor 5: sessions.**
- `from_settings` builds `boto3.session.Session().client(...)`, one session per store.
- `pyright` strict: 0 errors with the lite stubs.

**Minor 6: read timeout.**
- `read_timeout=20`. The comment now names both bounds and what each covers.
- Measured with a local socket that accepts and never answers (a scratch script):
  - `stat`: `ReadTimeoutError` after 40.26 s, 2 connections accepted.
  - `get`: `ReadTimeoutError` after 40.43 s, 4 connections accepted.
  - So 2 attempts of 20 s each.
- The default of 60 s is stated as `botocore`'s constant, `DEFAULT_TIMEOUT = 60`. It was not run.

**Minor 7: `DEPENDENCIES.md`.**
- I ran `uv run --with cryptography python measure_gcm.py`:
  - `256 MiB | … | peak RSS 793 MiB | factor 3.1`
  - `2048 MiB | encrypt failed: OverflowError: Data or associated data too long. Max 2**31 - 1 bytes`
- The row now cites these figures, the script path and today's date.
- The `lite` reasoning is now attributed to the 2026-10-04 measurement in the header of `blob_spike.py`, and the row says it was not repeated. Only "0 errors with lite" is mine.

**Minor 8: `blobs.md`.**
- "by 120 MiB in each of three runs", stated as measured with the test run on its own.
- "A second attempt is expected to succeed …; that wasn't measured on its own."
- `IfNoneMatch`: the sentence now names `upload_fileobj` at every size.
- I also added paragraphs on what this round changed in the design:
  - the exact shape of a key ID and the unreadable-file case;
  - the check on the address's shape;
  - the two kinds of store error and which side the unknown falls on.

**Minor 9: Linux-only tests.**
- `skipif(sys.platform != "linux")`, with the reason, on three tests:
  - `test_memory_stays_bounded`
  - `test_close_releases_the_connections_the_store_opened`
  - the new `test_a_fetch_that_fails_gives_its_connection_back`

**Minor 10.** `keys/age1../x` now exists as a directory with a file in it. The case went red under the mutation (see Minor 1).

**Minor 12.** The `.importlinter` header and the `.vale.ini` comment were reflowed. No line is longer than 79 characters. The `winners` strings are gone with I1.

**Also fixed:** the `S3BlobStore.client` docstring said "beyond the four methods" and now says "beyond the protocol".

## Interface as it now stands (for tasks 6 and 7)

`previously.contract.blobs`:
- `ByteSource.read(size=-1, /) -> bytes`
- `SeekableSource(ByteSource).seek(offset, whence=0, /) -> int`
- **new:** `ClosableSource(ByteSource).close() -> None`
- `ByteSink.write(data, /) -> int`
- `StoredBlob(key_id: str | None, sealed_size: int)`
- `BlobStore`:
  - `stat(address) -> StoredBlob | None`
  - `put(address, sealed: IO[bytes], *, key_id: str) -> None`
  - **changed:** `get(address) -> tuple[StoredBlob, ClosableSource] | None`
  - `delete(address) -> None`
  - `close() -> None`
  - Every address method raises `ValueError` ("`<address> is not a blob address: 64 hexadecimal characters, lower case`") before anything is sent.
- `KeyProvider.identity(key_id: str) -> str | None`

`previously.storage.errors`:
- `BlobStoreUnreachable`: about the connection.
- `BlobStoreRefused`: the store refused, or the settings are not usable.
- **new:** `IdentityUnreadable(StorageError)`: `DirectoryKeys.identity` raises it for a file that exists but cannot be read.

`previously.core.blob.fetch_blob`: the signature is unchanged. It now closes the stream on every path.

`previously.storage.s3.from_settings(...)`: the signature is unchanged. The client now has `read_timeout=20`, its own session per store, and, as before, connect 5 s and 2 attempts.

Test fixture: `s3_connections` in `conftest.py`, a callable that counts established connections to the S3 server. It works on Linux only.

## Test count and gates

468 tests: 458 + 3 in keys + 6 in s3 + 1 in blob.

```
uv run ruff check .                 All checks passed!
uv run ruff format --check .        67 files already formatted
uv run pyright                      0 errors, 0 warnings, 0 informations
uv run lint-imports                 Contracts: 6 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing
                                    ============================= 468 passed in 45.10s =============================
                                    (Total coverage: 98.28%; blob.py, sealing.py, keys.py, s3.py at 100%)
make -C docs html                   build succeeded.
make -C docs vale                   ✔ 0 errors, 0 warnings and 0 suggestions in 24 files.
make -C docs linkcheck              build succeeded.
uv run pytest -p no:randomly        ============================= 468 passed in 43.98s =============================
uv run pip-audit --skip-editable    No known vulnerabilities found
```

The tutorial's test-run block was retyped from a real `uv run pytest` run (`468 passed in 44.04s`), without the `rootdir:` line. `git status --short` was clean after the commit, and no scratch file is in the tree.

## Concerns after this round

1. **T5-d's leak depends on references, not on unread bytes alone.** The test proves the case of a caller that keeps its errors. A caller that drops them never leaked, thanks to reference counting. `close` is still right, because it does not rely on who keeps what.
2. **The 10 connections are my reading, not a measurement.** The docstring explains the count as nine unread streams plus the pooled one; I did not count them separately.
3. **The read timeout of 20 s per wait is my choice.** It is not measured against a slow real store. A provider that takes longer than 20 s between bytes, for example to complete a multipart upload, would turn into `BlobStoreUnreachable` after two attempts. Operation will show; it is one constant in `storage/s3.py`.
