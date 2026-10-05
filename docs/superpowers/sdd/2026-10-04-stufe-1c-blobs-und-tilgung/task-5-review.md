# Task 5 review: blobs as a library (eb81651..13d0d5e)

Reviewed from the diff file in four passes: source (`contract/blobs.py`, `core/blob.py`, `core/sealing.py`, `core/errors.py`, `storage/errors.py`, `storage/keys.py`, `storage/s3.py`); tests (`conftest.py`, `test_blob.py`, `test_s3.py`, `test_keys.py`, `test_sealing.py`, `test_contracts.py`); configuration and dependencies (`.importlinter`, `pyproject.toml`, `DEPENDENCIES.md`, `CLAUDE.md`, `.vale.ini`, vocabulary, `gates.yml`; `uv.lock` skimmed); documentation (`blobs.md`, `module-boundaries.md`, `index.md`, tutorial). No changed file was read outside the diff.

Checks outside the diff, one per named risk:

- *Untranslated error through `key_id` and through an address:* one `uv run python` snippet, no network (`from_settings` does not connect, and botocore validates parameters before it sends). Result: `stat("")` raises `BlobStoreUnreachable … is not reachable: ParamValidationError`. `DirectoryKeys(d).identity("age1" + "a"*300)` raises a bare `OSError [Errno 36] File name too long`. `ParamValidationError` and `NoCredentialsError` are both `BotoCoreError` subclasses.
- *A comment is a claim (`.vale.ini`):* `awk 'NF && /^[a-z]/'` over `accept.txt` gives 15 of 19. The comment is correct.
- *Source of the "2 GiB" figure in `DEPENDENCIES.md`:* grep in the stage 1c spec. It comes from spec line 677, not from the author's own measurement.

### Spec Compliance
- ✅ Spec compliant, with justified departures:
  - `close()` as a fifth protocol method, per ruling T5-a, with the socket measurement and a mutation.
  - Public `client`, `bucket` and `endpoint` properties.
  - `EncryptError` translation, with a test.
  - `key_id` lower-cased, with a test and a mutation.
  - `InvalidKey` passes through `fetch_blob`, and the docstring says so.
  - Vale vocabulary added.
  - One commit, for a stated reason.

  What the brief asked for is all there:
  - every test the brief names;
  - all six mutations, plus the adapter's, each with a red and a green control;
  - the three measurements left to the implementer (time to fail, memory on both sides, the race), and the T5-a socket measurement;
  - every sentence the brief names, fixed. `CLAUDE.md` changed in exactly one number (`four` → `six`);
  - every point `blobs.md` must carry, with the author's own figures dated 2026-10-05;
  - both contracts with exemptions by name, and a probe test for each;
  - the test count retyped from a real run, and consistent per file (11 + 14 + 12 + 9 + 2 = 48; 410 + 48 = 458).

  The identity-belongs-to-key check was removed on a measurement. The assurance still holds: `age` refuses an identity of another key with `DecryptError`, `unseal` turns that into `CannotOpen`, and `test_an_identity_file_that_holds_another_key_cannot_open` holds the case and checks that the message names no identity.
- ⚠️ Cannot verify from the diff:
  - the registry figures in `DEPENDENCIES.md` (dates, versions, archive states);
  - the measured figures the report and the comments cite (timings, MiB, race counts, socket counts);
  - the six gate runs and `pip-audit`;
  - that the commit message ends in `Assisted-By:` and carries no `Co-Authored-By:` (the diff file shows only the subject line).

### Strengths
- The layering is clean:
  - `pyrage` lives only in `core/sealing.py`, and `boto3`/`botocore` only in `storage/s3.py`.
  - The protocols in `contract/blobs.py` need no imports beyond the standard library.
  - `_Stream` closes the one leak a reader would miss: a `botocore` error raised during a later `read`, passing through `pyrage` into `core`. A real broken stream holds it, and a mutation shows it.
- `get` uses one `GetObject` and is tested structurally through `client.meta.events`, with no mock. The `HeadObject + GetObject` mutation is measured red.
- The time to fail is made deterministic by counting attempts, not only by timing. The comment explains why timing alone could not tell the configuration from the default, and gives the 10.0/10.5 s case against an address that drops packets.
- The secret hygiene is thorough:
  - The wrong-secret test checks `str`, `repr` and the formatted cause chain for all four methods, and the store's `repr`.
  - Secrets are drawn at run time, which removed `S105` without a suppression.
  - `InvalidKey` for an identity uses `from None`.
- `DirectoryKeys` checks `key_id` with `fullmatch` before any path is built. The test's controls are well chosen: the `../x` target exists beside the directory, and `AGE1ABC` exists inside it, so only the check can make it `None`.
- The report is honest: it names the weak `age1../x` parameter, the Linux-only tests, the unmeasured `age` emergency path (stated on the page too), and the 2 GiB figure removed from the page.
- Ruling T5-a was carried out exactly as asked: measured first, then the method, a test with an in-test control (`> before` while open), and a mutation.

### Issues

#### Critical (Must Fix)
None.

#### Important (Should Fix)

1. **The two-writer test can fail by chance, and the chance-dependent assertion adds no assurance.** This is partly plan-mandated. `tests/test_blob.py:219` requires `set(winners) == {"0", "1"}` over `ROUNDS = 16` (`tests/test_blob.py:44`).
   - The brief asked for repetition "until both outcomes occur" because it assumed only the loser fetches. In this test **both writers fetch in every round** (`_race`, `tests/test_blob.py` around 100–108). So every round has exactly one writer whose recipient is not the object's key, and the caller-key mutation goes red in round 1 whoever wins. The report measured this: red 3 runs out of 3.
   - The winner assertion therefore only adds a false-red probability. At the measured 53/45 split it is about 6e-5 per run (0.54^16 + 0.46^16, nearer 1 in 17,000 than the "one in ten thousand" the comment at `:40–43` states). On a CI runner whose scheduling favors one thread it is unbounded.
   - A formulation that cannot flake: drop the `winners` assertion, or record the winners only for the failure message. Keep the per-round assertions that both fetches return the content, and change the comment and docstring to say that every round has a losing fetcher.
   - The brief's wording ("repeat so that both outcomes occur") should be ruled superseded by the controller.
2. **A false statement on a page.** `docs/explanation/module-boundaries.md:19` reads "The arrows that leave the package each have a contract that names the one module allowed to draw them."
   - That is true for `pyrage` and `boto3`. It is not true for `sqlalchemy`: "Only storage imports sqlalchemy" names `core` and `contract` as forbidden *sources*. It names no allowed module, and `cli` is outside it. The same page says so at "The third names `core` and `contract` as its sources".
   - Fix: limit the sentence to the two new arrows, or describe the `sqlalchemy` contract correctly.

#### Minor (Nice to Have)

1. **An overlong `key_id` escapes as a bare `OSError`.** `src/previously/storage/keys.py:24` allows `age1[a-z0-9]+` of any length. Measured: 304 characters raise `OSError: [Errno 36] File name too long` from `:54`, not `None`.
   - Whoever can write the bucket can make `fetch_blob` raise a non-`PreviouslyError`.
   - An X25519 recipient is exactly `age1` plus 58 Bech32 characters. `age1[02-9ac-hj-np-z]{58}` closes this and is stricter.
   - The brief's regex has the same gap.
2. **Every `BotoCoreError` is reported as "not reachable".** See `src/previously/storage/s3.py:66, 108–111, 127, 140, 157, 171`. Measured: `stat("")` gives "the blob store at … is not reachable: ParamValidationError". `NoCredentialsError` (an empty access key) would read the same way. This is plan-mandated ("a `BotoCoreError` is `BlobStoreUnreachable`"). Consider mapping `ParamValidationError` and `NoCredentialsError` to `BlobStoreRefused` or to an input error, so operators are not sent chasing the network.
3. **The address is not validated where it becomes an object key.** `fetch_blob` (`src/previously/core/blob.py:96`) and `S3BlobStore.get/stat/delete` accept any string. `store_blob` always computes hex, and the CLI check comes in a later task, so nothing at this commit feeds a foreign address. A `[0-9a-f]{64}` check in the adapter would hold the line for task 7's `delete` too. Path-style keys containing `../` depend on the server's normalisation.
4. **Error paths in `fetch_blob` abandon the response stream.** At `src/previously/core/blob.py:117–131`, the paths with no key, no identity, `CannotOpen` or `AddressMismatch` leave the `GetObject` body unread and unclosed. The connection is held until `store.close()`. `close()` mitigates this, but `ByteSource` has no `close`, so a long-lived store accumulates one connection per failed fetch.
5. **`from_settings` uses the default `boto3` session.** `src/previously/storage/s3.py:212` calls `boto3.client`. boto3 documents sessions as not thread-safe, and the two-writer test builds clients in two threads at once (it is saved today because `conftest` already materialized the default session in the main thread). The default session also reads `~/.aws/config` and `AWS_*` variables. `boto3.session.Session().client(...)` per store avoids both.
6. **No read timeout is set.** `src/previously/storage/s3.py:199–224` sets only `connect_timeout`. A server that accepts and then stalls waits the default 60 s per attempt, 120 s in all. The comment's "how long a call … takes to fail" covers only an endpoint that does not answer at all; say so, or set `read_timeout`.
7. **Two figures in `DEPENDENCIES.md` were not measured by the author.**
   - "stops at 2 GiB" (`DEPENDENCIES.md:51`) comes from the spec (line 677). The report says it was removed from the page for exactly that reason, yet it stays here.
   - The `lite` reasoning (`:53`) cites the 2026-10-04 draft measurement. Today only "0 errors with lite" was confirmed.

   Either re-measure them or attribute them explicitly.
8. **Two claims on `blobs.md` go beyond what was measured.**
   - "raises the peak … by 120 MiB at most" (`docs/explanation/blobs.md:70`) generalizes three solo runs; say "by 120 MiB in three runs, run on its own".
   - "A second attempt succeeds." (`:86`) is inferred, not measured.
   - "The upload in parts of `boto3` … rejects `IfNoneMatch`" (`:92`) refers to `upload_fileobj`, which rejects it at any size, not only for multipart uploads.
9. **Two tests depend on Linux and would error rather than skip elsewhere.**
   - `test_memory_stays_bounded` (`tests/test_blob.py:171,176`): `ru_maxrss` is in bytes on macOS, so the growth would read 1024× too high and go falsely red.
   - `test_close_releases_the_connections_the_store_opened` (`tests/test_s3.py:213`) reads `/proc`.

   CI is `ubuntu-latest`, so this is not a gate risk. A `skipif(sys.platform != "linux")` with its reason states the limit honestly.
10. **The `age1../x` parameter does not exercise the check.** At `tests/test_keys.py:52` it stays green under the mutation, because `keys/age1../x` does not exist. Creating `keys/age1../x` (a directory `age1..` with a file `x`) would make it a real case. The report already names this.
11. **The read-break test relies on RustFS stopping its send when the object is deleted.** `test_a_read_that_breaks_off_is_a_storage_error` (`tests/test_s3.py`, ~`:180`) passed 10 of 10 at 64 MiB, which is far above socket buffers. It depends on server behavior rather than timing, so it is reasonably robust. Watch it on the first CI runs.
12. **Polish.**
    - The reflow of the `.importlinter` header comment (`.importlinter:3–6`) leaves a short line, "requires this setting for that,".
    - The `.vale.ini` comment line now exceeds the file's wrap width.
    - `winners.append(str(...))` stores indices as strings for no reason.

### Assessment
**Task quality:** Needs fixes

**Reasoning:** The implementation is sound, well layered and carefully measured, and every requirement and mutation is present. Two things should not ship as they are: the two-writer test carries a chance-dependent assertion that adds nothing to what it proves, and `module-boundaries.md` states a falsehood about the `sqlalchemy` contract. Both are small fixes.
