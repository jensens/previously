# Task 7 report: erasing blobs and checking them

Commit `a65d1cc` on top of `ea62154`. All measurements below were taken on 2026-10-05.

## What was implemented, step by step

### Step 1: the rule, without a database (`core/redaction.py`)
- `blob_payload(sha256, event_ids, *, reason)`: the third form, with the events ascending and each named once.
- `RedactionIndex.of_reference(event_id, sha256)`: the redaction of the whole event, or a blob redaction that names the event. When both exist it returns the earlier one, matching the "first one wins" rule of the class.
- `blob_expected(index, sha256, event_ids)`: returns `any(of_reference(...) is None)`. It is false when there is no reference at all.
- **Addition, not in the brief:** `blob_erasure(index, sha256, event_ids) -> Redaction | None` is the redaction to name for a blob that no longer has to lie: the newest of those that erased its references. It returns `None` while the blob has to lie. It calls `blob_expected` and does not compute the rule itself. `redact_blob` uses it for the id of `already redacted by event <id>`, and `blob get` uses it for `blob <hex> is erased (event <id>)`, so the choice of id lives in one place.

### Step 2: the procedure
- `LogStore.blob_references(conn) -> Iterator[tuple[bytes, int]]`: the protocol, and `PostgresStorage` with a server-side cursor ordered by `(sha256, event_id)`.
- `Redacted` gained `obsolete_blobs` and `kept_blobs`, with the signature from the brief. `Mapping` is now a runtime import in `redact.py`, because ruff TC004 and `runtime-evaluated-decorators = ["dataclasses.dataclass"]` require it.
- `redact_blob` follows the procedure in the brief. It reads the users from the register; with none it refuses with `no event uses blob <hex>`. It locks the users' rows in ascending order (`_lock_ascending`), reads the index, and names the users whose reference is not yet erased. When none is left it writes nothing and returns the newest erasing redaction. Payloads and units are left untouched. A malformed address is refused with `InvalidPayload`, using the wording of the input-error table, before the store is asked.
- `redact_event` now computes `obsolete_blobs` and `kept_blobs` as well, on every call, including one that writes nothing. Both functions add their own new redaction to the index (`index.add(parse(...))`) before `_blobs_after` applies the rule.
- **Addition, not in the brief:** `redact_event` locks the target **and every event that shares one of its blobs**, in ascending order. See "Departures" for the reason and the measurement.

### Step 3: `verify --blobs` (`core/verify.py`, `core/sealing.py`)
- `sealing.NullSink.write` returns `len(data)`. It has to, because `HashingSink` counts what its sink says it took.
- `BlobCheck(store, keys)`. `Examination.blobs_checked: int = 0` counts the distinct blobs the register names. Erased ones are included, because each of them is checked (fetched or asked for).
- `examine(..., blobs=None)`. Inside the snapshot, after the reconciliation, `_references` groups `blob_references` by hash; without a `BlobCheck` it returns `{}`. After the snapshot, `_blob_findings` and `_blob_reason` work through each blob. A blob that has to lie goes through `fetch_blob` into a `NullSink`: `None` means missing, `AddressMismatch` means "does not match its address", and `CannotOpen` means "cannot be opened". A blob that does not have to lie gets `stat`, and if the object is there the finding is "is erased and still present". Each finding stands under `min(event_ids)`. The in-memory limit is stated in the `_references` docstring.
- `_execution_findings` holds a blob redaction against its target. Every named event has to have an id below the redaction's, and `events_by_blob` (one query per redaction) has to contain it. Otherwise the finding is `redaction names a target that does not exist`.

### Step 4: the command line (`cli.py`)
- `redact blob HASH --reason TEXT`. `_redact` dispatches the three forms.
- The order now matches the brief and point 4 of the dispatch:
  1. `_delete_obsolete`, which reads the blob settings only when `obsolete_blobs` is non-empty.
  2. `_catch_up_after`, which prints build or rebuild lines on stderr (ruling T4-b).
  3. The single line on stdout.
  4. `unit … was already erased` and `blob … stays in the store: …` on stderr.
- A failed deletion goes through `_unfinished`, the shared builder of `the redaction is recorded as event <id>, but it is not finished: <outstanding>; run the same command again`. The outstanding part is `blob <hex> is not deleted from the store (<error>)`, or `blobs <hex>, <hex> are not deleted from the store (<error>)`, and the exit code is 2. The new error is raised after the `except` and carries only `str(error)`, so it carries no context (the pattern from `storage/keys.py`).
- `verify --blobs`: `_examine` builds the store once with `_blob_store()` and closes it in `finally`. The success line ends in `, 1 blob matches` or `, N blobs match`, both with and without anchors.
- `show`: a reference that a redaction erased gets ` <erased by event <id>>` at the end of its line. At an erased event the lines come from the event's redaction, as `  blob <hex> <erased by event <id>>`. This is an interpretation: the size, type and name went with the payload, so only the hash is left.
- `blob get`: when every reference is erased, it prints `blob <hex> is erased (event <id>)` on stderr and returns 1. That holds whether or not the object still lies in the store.

### Step 5: the pages
- `docs/reference/cli.md`:
  - `redact`: three forms, the `HASH` argument, the rule, the blob form of the payload, the order of the work, both "not finished" sentences, the kept-blob notices, and seven refusals.
  - `verify --blobs`: the argument, the four findings in a table, the error side, the "can appear as missing" sentence, and the success-line suffix.
  - `show`: the erased suffix.
  - `blob get`: the erased notice, and the exit-code table.
  - The intro sentence about which commands read the blob settings.
- `docs/reference/configuration.md`: the "Missing at" column now names `verify --blobs` and a `redact` that deletes a blob.
- `docs/explanation/erasure.md`:
  - The target sentence and the third table row; the event row now covers its file names and obsolete blobs, and its register rows stay.
  - A new section, "When a blob has to lie in the store": the rule in one sentence, its three consequences, why a shared blob stays, and the redaction of a blob leaving the payloads alone.
  - A new subsection, "First the transaction, then the store": what a second call finishes, and the lock on the sharing events.
  - "covered" for a blob.
  - A restore shows for blobs.
  - The address carries no salt, and what that means.
- `docs/explanation/blobs.md`: the placeholder section "What this page doesn't say yet" is replaced by "When a blob goes again" (with a `{ref}` to erasure) and "What verify checks in the store" (why it reads every byte, why after the snapshot, and where the line between finding and error runs).
- `docs/explanation/concurrency.md`: see "Sentences found no longer true".

### Step 6
The tutorial transcript was retyped from a real `uv run pytest` run (604 passed, without the `rootdir:` line). All six gates ran, and there was one commit.

## TDD evidence

| Step | RED (command and output) | Why expected | GREEN |
|---|---|---|---|
| 1 | `uv run pytest tests/test_redaction.py -q` → `ImportError: cannot import name 'blob_expected' from 'previously.core.redaction'`, `1 error during collection` | the functions did not exist | `25 passed` (18 + 7) |
| 2 | `uv run pytest tests/test_redact.py tests/test_storage.py -q -k blob` → `ImportError: cannot import name 'redact_blob' from 'previously.core.redact'` | the function did not exist | `tests/test_redact.py tests/test_storage.py tests/test_redaction.py` → `90 passed` |
| 3 | `uv run pytest tests/test_verify.py -q -k blob` → `1 error during collection` (`BlobCheck` missing). After the first implementation: `8 failed` (`AttributeError: 'list' object has no attribute 'store'`, caused by a loop variable `blobs` shadowing the parameter; renamed to `registered`), then `NameError` at `target` (a line my edit script dropped; restored) | missing feature, then my own two mistakes | `tests/test_verify.py … -q` → all passed |
| 4 | `uv run pytest tests/test_cli.py -q -p no:randomly -k "blob or erased or redact"` → `8 failed, 38 passed` (`SystemExit: 2` for the unknown `redact blob` and `verify --blobs`, the missing show suffix, the two new refusal cases) | the commands and arguments did not exist | `tests/test_cli.py` → `113 passed` after updating one existing test (see below) |

## Mutations

Commands and outputs are from the scratch scripts `mut_brief.sh`, `mut_release.sh`, `mut_release2.sh`, `mut_line.sh` and `mut_docs.sh` in the scratchpad. Each script restores the file and compares it with `cmp`; none reported "NOT RESTORED".

| Mutation | Red | Green control |
|---|---|---|
| M1: `blob_expected` counts every reference (`any(True for event_id in event_ids)`) | `test_blob_expected[both-erased]`, `[blob-names-both]`; `test_redacting_the_only_event_of_a_blob_makes_it_obsolete`; `test_a_shared_blob_is_kept_until_its_last_event_goes` fails on its **second** assert, `assert ((), {'555555...5555555': ()}) == (('5555555555...555555',), {})`, so its first step passed. `4 failed, 3 passed` | the first step of the shared-blob test; `[one-of-two-erased]`, `[blob-names-both-and-a-third-comes]`, `[no-reference]` |
| M2: a call that writes nothing returns `obsolete_blobs` empty (in `redact_event` and `redact_blob`) | `test_a_delete_that_fails_is_finished_by_the_second_call` (`assert ['…'] == []`, the bucket still holds the blobs), `test_a_second_blob_redaction_writes_nothing_and_still_names_the_blob_obsolete`. `2 failed, 1 passed` | `test_redact_event_deletes_its_blob_and_says_which_one_stays` |
| M3: `verify --blobs` does not ask about erased blobs (`return None`) | `test_verify_blobs_finds_each_of_the_four[erased-and-present]` (`assert () == (Finding(…ll present'),)`). `1 failed, 3 passed` | `[missing]`, `[foreign]`, `[garbage]` |
| M4: `fetch_blob` does not compare the address (`if False:`) | `[foreign]` (`assert () == (Finding(…ts address'),)`). `1 failed, 1 passed` | `[missing]` |
| M5: the command line deletes before the transaction (`redact blob` deletes the address before `_redact`) | the new `test_a_refused_redaction_deletes_nothing` (`assert [] == ['6b56f89a918…']`) | `test_redact_blob_and_then_blob_get_says_erased` |
| Added: `redact_event` locks only its target | `test_two_redactions_of_events_sharing_a_blob_let_it_go_however_they_meet` (`assert ((), ()) == ((), ('555555…',))`). `1 failed, 1 passed` | `test_two_redactions_of_one_event_at_once_write_one` |
| Added: `verify --blobs` turns any fetch error into a finding (`except Exception: return "cannot be opened"`) | `test_verify_blobs_that_cannot_check_is_an_error_and_no_finding[store-does-not-answer]` and `[identity-cannot-be-read]` (`assert 1 == 2`) | `test_a_blob_whose_key_is_not_at_hand_cannot_be_opened_and_the_check_goes_on` stayed green (`2 failed, 115 passed`) |
| Added, release: `_examine` builds its store without closing it | `test_every_command_closes_each_blob_store_it_builds` (`assert (7, 5) == (7, 7)`) | — |
| Added, release: `_delete_obsolete` builds its store without closing it | same test (`assert (7, 5) == (7, 7)`) | — |
| Added, page quotes: `be03 is missing` → `is gone`, `be03 is erased and still present` → `is erased, still present`, `stays in the store: event 7 still uses it` → `… uses it`, `is erased (event 42)` → `is erased by event 42`, `is not deleted from the store` → `was not deleted …` | `test_the_reference_quotes_what_the_code_actually_prints` turned red for each | unmutated page: `5 passed` |

On release (instruction 2): the existing `test_main_releases_the_blob_store_it_opened` **cannot see** an unclosed store of the two new paths. With `verify --blobs` and `redact blob` added to its loop, and either path's close taken out, it stayed green (`1 passed` three times: unmutated, verify mutation, redact mutation). That fits its own docstring: a store that never uploads is freed by reference counting. So I took the two lines back out of its loop and added `test_every_command_closes_each_blob_store_it_builds`. That test wraps the real store returned by the real `from_settings` (patched in `previously.cli`) to count `close`, and checks seven builds against seven closes, on success and on error.

## Complexity

Measured with `ruff check --select C901 --config 'lint.mccabe.max-complexity = 1'`. HEAD values come from copies of the HEAD files measured with `--isolated` (they are outside the tree; only the C901 count is read).

| Function | HEAD | now |
|---|---|---|
| `verify.examine` | 9 | 9 (the new branches sit in `_references` and `_blob_findings`) |
| `verify._execution_findings` | 6 | 7 |
| `cli._cmd_show` | 8 | 8 |
| `cli._cmd_blob_get` | 6 | 7 |
| `cli._cmd_verify` | 5 | 5 |
| `cli._cmd_redact` | 4 | below 5 |
| `cli._delete_obsolete` | — | 5 |
| `redact.redact_units` | 8 | 8 |
| `redact.redact_blob` | — | 5 |
| `redaction.parse` | 9 | 9 |

## Where the line runs between finding and error in `verify --blobs`

The line is documented in the `_blob_findings` docstring, on the explanation page `blobs.md` and on the reference page.

- **Findings:**
  - `None` from the store: missing.
  - `AddressMismatch`: does not match its address.
  - `CannotOpen`: no key named, no identity for the key, or `age` refuses the object.
  - Present while not expected: erased and still present.
- **Errors**, which are raised, end the command with exit code 2, and are never turned into findings:
  - `storage.errors` from the store (unreachable, refused, unusable settings).
  - `IdentityUnreadable`.
  - `InvalidKey` (an identity file whose content is not an identity).
  - A stream that breaks off.
  - Missing settings.
- **Tests on the finding side:** `test_a_blob_whose_key_is_not_at_hand_cannot_be_opened_and_the_check_goes_on` and the four cases of `test_verify_blobs_finds_each_of_the_four`.
- **Tests on the error side:** `tests/test_cli.py::test_verify_blobs_that_cannot_check_is_an_error_and_no_finding[store-does-not-answer | identity-cannot-be-read]`. Each expects exit code 2, an empty stdout, one sentence, and no secret and no identity in the output.

## Existing tests whose arrangement or expectation changed
- `tests/test_cli.py::test_a_catch_up_that_fails_after_the_redaction_says_what_is_outstanding`: the **expectation** changed from `out == "redacted by event 4\n"` to `out == ""`, and the docstring was rewritten. The reason is the order this dispatch prescribes (point 4): the line on stdout comes last. The page says so too.
- `tests/test_redact.py::test_read_index_passes_over_what_it_cannot_read`: the **arrangement** changed. Event 1 now names the blob (`_attached("m", blob)`), because a blob redaction naming an event that does not use the blob is now a finding, as the brief requires. The expectation stays as it was. The docstring sentence "A redaction of a blob names no event, so `verify` holds nothing against the log for it" was false and has been rewritten.
- `tests/test_cli.py::test_a_refused_redaction_is_one_sentence`: two new parameter cases (`unused-blob`, `not-a-blob-address`).
- `tests/test_redact.py::_ContestedLog`: gained `blob_references`, so that it still satisfies `LogStore`.
- `tests/test_docs_references.py::test_the_reference_quotes_what_the_code_actually_prints`:
  - New blocks: the kept-blob notices (2), the erased notice of `blob get` (1), the two "not finished" errors.
  - Seven refusals instead of six; nine blob and command errors instead of seven.
  - The outstanding phrase is held against what `cli.py` passes to `_unfinished` and assigns to `outstanding`.
  - The four blob findings are held against the string literals of `_blob_reason`.
  - The docstring counts were updated.
  - To make the outstanding phrase checkable, `_delete_obsolete` builds the singular and the plural form as two literals rather than interpolating `is`/`are`. Before that, `was not deleted` passed the check.
- `tests/test_blob.py::test_a_fetch_into_a_sink_that_fails_returns_no_size`: the docstring now says what has been true since `ea62154` (point 6 of the dispatch).
- `tests/test_redaction.py::test_the_blob_form_parses`: the docstring no longer says that the builder "comes with the erasure of a blob".

## Departures from the brief
- **`redact_event` locks every event that shares a blob with its target, in ascending order.** The brief prescribes the ascending lock only for `redact_blob`. Without it there is a window: the second erasure reads the redactions before the first one commits, then reads the tip after the first one has committed, and so wins its chain position. Both erasures then keep the shared blob, and nothing ever deletes it. The chain-position conflict closes the window only when both erasures read the tip before either commits; I measured that a naive barrier test stayed green under the mutation for exactly that reason (3 of 3 runs). The deterministic test `test_two_redactions_of_events_sharing_a_blob_let_it_go_however_they_meet` forces the window: a `PostgresStorage` subclass delays `tip`, and an eraser holds the first transaction open until the second erasure has either read the redactions or waits on a lock, which it detects through `pg_stat_activity.wait_event_type = 'Lock'`. Red and green are shown in the mutation table. The page `concurrency.md` states the reason.
- **`blob_erasure`** is added to `core.redaction`. See step 1.
- **`InvalidPayload` from `redact_blob`** for a malformed address. The table lists the wording as an input error, and the command line passes the core's refusal through unchanged.
- **The `show` lines at an erased event** are `  blob <hex> <erased by event <id>>`, because only the hash survives. The table names only the line with size, type and name.
- Signatures from the brief are unchanged. `examine` takes `blobs: BlobCheck | None = None`, and `Examination` gains `blobs_checked: int = 0`. `BlobCheck`'s field types are runtime imports from `contract.blobs` (TC004 with the `dataclass` setting).

## Sentences found no longer true, and rewritten
- `contract/store.py` said the protocol has "eleven methods" and that `events_by_blob` is called by no module of `core`. Re-measured with the command written beside it: **thirteen**, every declared method is called, and `events_by_blob` is called by `redact`.
- `pyproject.toml` said the `print` count is thirty. Re-measured with the command written beside it: **thirty-two** (the `blob get` erased notice and the kept-blob notice).
- `cli._cmd_redact` said "The line first: the redaction stands …". It is replaced by the new order.
- `cli._redact_arguments` said "`event` or `units`". It now also names `blob`.
- The help line of the `redact` command now reads "erase an event, units of it, or a blob".
- The `redaction.py` module docstring said "All three forms are accepted, the one for a blob included …". It now names `blob_expected` as the one place the rule is computed.
- `verify._execution_findings` said "its check comes with the blobs, names no event to read". It is replaced by the target check.
- `docs/explanation/concurrency.md` said "two erasures of different targets never wait for each other". It now reads "that share neither a target nor a blob", with a new paragraph on the lock of the sharing events.
- `docs/explanation/blobs.md`:
  - The section "What this page doesn't say yet" is replaced.
  - "as an erasure of a blob will" now reads "as an erasure does".
- `docs/reference/cli.md`:
  - "two forms" and the payload description.
  - "the line on standard output stands" on a failed catch-up is now "nothing goes to standard output".
  - "Six refusals" is now "Seven refusals".
  - The exit-code rows of `redact`, `verify` and `blob`.
  - The settings sentence in the intro.
- `docs/reference/configuration.md`: the "Missing at" column.
- `docs/explanation/erasure.md`: "the target is either a whole event or some units of one event".

## Counts and gates
- Tests: **604** (566 + 38), made up of:
  - `test_redaction.py`: 7.
  - `test_storage.py`: 1.
  - `test_redact.py`: 7 (the 6 from the brief and the shared-blob concurrency test).
  - `test_verify.py`: 10.
  - `test_cli.py`: 13 (the 7 from the brief, 2 refusal cases, `test_a_refused_redaction_deletes_nothing`, `test_every_command_closes_each_blob_store_it_builds`, and the 2 cases of the error-side test).
- The brief's figure of 485 came from an earlier estimate.
- `print` count: 32.
- Full run: about 70 to 74 s, up from about 62 s.
- `uv run ruff check .` → `All checks passed!`
- `uv run ruff format --check .` → `69 files already formatted`
- `uv run pyright` → `0 errors, 0 warnings, 0 informations`
- `uv run lint-imports` → `Contracts: 6 kept, 0 broken.`
- `uv run pytest --cov --cov-report=term-missing` → `======================== 604 passed in 73.60s (0:01:13) ========================` (`Total coverage: 98.35%`; the two uncovered lines in `cli.py`, 362 and 717, were uncovered before this task)
- `make -C docs html` → `build succeeded.`
- `make -C docs vale` → `✔ 0 errors, 0 warnings and 0 suggestions in 24 files.`
- `make -C docs linkcheck` → `build succeeded.`
- `uv run pytest -p no:randomly` → `======================== 604 passed in 70.14s (0:01:10) ========================`

## Files changed
- `src/previously/cli.py`
- `src/previously/contract/store.py`
- `src/previously/core/redact.py`
- `src/previously/core/redaction.py`
- `src/previously/core/sealing.py`
- `src/previously/core/verify.py`
- `src/previously/storage/postgres.py`
- `pyproject.toml`
- `tests/test_blob.py`
- `tests/test_cli.py`
- `tests/test_docs_references.py`
- `tests/test_redact.py`
- `tests/test_redaction.py`
- `tests/test_storage.py`
- `tests/test_verify.py`
- `docs/reference/cli.md`
- `docs/reference/configuration.md`
- `docs/explanation/erasure.md`
- `docs/explanation/blobs.md`
- `docs/explanation/concurrency.md`
- `docs/tutorials/record-your-first-event.md`

`git status --short` was clean of foreign files before staging.

## Self-review
- Every wording was checked character by character against the table:
  - `blob <hex> is missing`, `does not match its address`, `cannot be opened`, `is erased and still present`.
  - `blob <hex> stays in the store: event <ids> still uses it` and `events … still use it`.
  - `blob <hex> is erased (event <id>)`.
  - `no event uses blob <hex>`.
  - `<hex> is not a blob address: 64 hexadecimal characters, lower case`.
  - `, 1 blob matches` and `, N blobs match`.
  - ` <erased by event <id>>`.
  - The "not finished" frame.
  - The page quotes are held by `test_docs_references`.
- The rule is computed only in `blob_expected`. `_unerased` and `blob_erasure` read `of_reference` to name events or redactions; they do not decide whether a blob has to lie.
- No secret in output: the delete error quotes only the store error's text (endpoint, no credentials; checked in `test_a_delete_that_fails…`). The two error-side tests check the secret, the identity and `AGE-SECRET-KEY`.
- A comment number I first wrote without measuring was taken out: a sentence in `blobs.md` claiming that the store keeps checksums which pass a foreign ciphertext. It was replaced by a statement that follows from the design.

## Concerns
- **An `append --attach` racing a `redact` of the last user of the same content.** `store_blob` sees the object and does not upload; the redaction then deletes it after its transaction. The new event names a blob the store no longer holds, and `verify --blobs` reports it as missing. The store takes part in no transaction, so I did not try to close this race, and none of the pages mention it. It may belong in the map.
- **A wrapper patched into `previously.cli.from_settings`.** `test_every_command_closes_each_blob_store_it_builds` patches it to wrap the real store. It is not a mock, since every call reaches the real S3 server, but it does monkeypatch a module attribute. The reviewer may want to judge that against "no mock for storage".
- **The memory limit of `verify --blobs`.** All references are held in process memory; the docstring says so but gives no measured figure.
- The deterministic concurrency test relies on `pg_stat_activity.wait_event_type = 'Lock'` to see the second erasure waiting. Its green path costs no timeout. Its red path under the mutation was measured once.

---

## Fix round 1

Commit `867e30a` on top of `a65d1cc`. Measurements taken on 2026-10-05.

### Important 1: `concurrency.md`, which erasures wait for each other
The false sentence "two erasures that share neither a target nor a blob never wait for each other" is replaced. The page now says:
- Two erasures wait for each other when the sets of rows they lock overlap.
- Each set is the target, and for `redact event` and `redact blob` also every event that uses one of the target's blobs.
- Both of the review's counterexamples are covered: two erasures that each share a different blob with event 2 both lock event 2, and a `redact units` still waits behind an erasure whose set holds its target.

### Important 2: backups of the bucket
- `erasure.md`, "Backups keep it": an erased blob is gone from the store and stays in every backup or replica of the bucket for as long as that copy is kept. Its identity has a backup of its own, as `blobs.md` asks. The promise of an erasure is as long as the longer of the two retentions, and whoever promises erasure chooses both by it.
- `blobs.md`, "When a blob goes again": the same point, from the side of the bucket.

### Confirmed gap (Minor 7): `InvalidKey` on the `verify --blobs` path
New case `identity-is-not-one` in `tests/test_cli.py::test_verify_blobs_that_cannot_check_is_an_error_and_no_finding`. The identity file holds `AGE-SECRET-KEY-1PREVIOUSLYTESTNOTAKEY`, a line that looks like an identity and isn't one. The test expects:
- exit code 2 and an empty stdout;
- one sentence containing `the identity is not an age X25519 identity`;
- neither the store's secret, nor the identity, nor `AGE-SECRET-KEY`, nor `PREVIOUSLYTESTNOTAKEY` anywhere in the output.

`main` prints only `str(error)`, so a foreign exception's context does not reach the output.

The case first ran green: `3 passed`.

Mutation (script `mut_fix1.sh`): `_blob_reason` gains `except InvalidKey: return "cannot be opened"`.
```
FAILED tests/test_cli.py::test_verify_blobs_that_cannot_check_is_an_error_and_no_finding[identity-is-not-one]   (assert 1 == 2)
PASSED …[store-does-not-answer], …[identity-cannot-be-read]
PASSED tests/test_verify.py::test_a_blob_whose_key_is_not_at_hand_cannot_be_opened_and_the_check_goes_on
1 failed, 118 passed
```
Afterwards the file was restored and checked with `cmp`.

The reference page now lists "an identity file whose content isn't an age identity" on the error side.

### Minor 1: the snapshot caveat in both directions
The caveat is now stated in both directions in three places: `_blob_findings` in `core/verify.py`, `cli.md` and `blobs.md`.
- A blob erased and deleted during the run can show as missing.
- A blob whose redaction the snapshot already holds can show as erased and still present: either a concurrent `redact` hasn't deleted it yet, or the same content was attached again after the snapshot.
- The next run reports none of them.

### Minor 2: the restore case
`erasure.md` now says that `verify --blobs` reports as missing only the blobs an erasure since the restore point deleted. An object uploaded after that point is named by no event and reported by nothing.

### Minor 3: the append-versus-redact race, and objects no event names
- `concurrency.md`, under "Two write paths": an `append --attach` that skips its upload while a `redact` deletes the object after its commit leaves an event that names a missing blob. Nothing prevents this, `verify --blobs` reports the blob as missing, and attaching the same file again stores it again.
  - I first wrote that re-attaching would not restore the blob. That was wrong: `store_blob` asks the store, not the register. I read `core/blob.py` and corrected the sentence before committing.
- `cli.md`, `blobs.md` and the `_blob_findings` docstring now say explicitly that `verify --blobs` checks only the blobs the register names, and reports nothing about an object that no event names.

### Minor 4: the comment in `redact_event`
The comment now gives the whole reason:
- `registered` is final.
- `sharing` can grow while the erasure runs, and an event appended late goes unlocked.
- That is still correct: the late event's reference isn't erased, so the blob is kept for it (`_blobs_after` reads the register again), and any later erasure of that event locks every user of the blob, this target included.

### Minor 5: `blob get` asks the log first
`_cmd_blob_get` answers `no event uses blob …` and `blob … is erased (event …)` from the database. It reads `PREVIOUSLY_BLOB_IDENTITIES` and builds the store only when there is something to fetch. `cli.md` says so.

New test: `test_blob_get_answers_from_the_log_without_any_blob_setting`. It runs with no blob settings at all and expects:
- for an unused address: exit 1 and the "no event uses" notice;
- for an erased blob: exit 1 and `is erased (event 3)`;
- for a blob that has to lie: exit 2 and `Error: PREVIOUSLY_BLOB_IDENTITIES is not set`. This is the control that the settings really are missing.

Mutation (script `mut_fix1.sh`): `keys = _identities()` is moved back before the database query.
```
FAILED tests/test_cli.py::test_blob_get_answers_from_the_log_without_any_blob_setting   (assert 2 == 1)
PASSED tests/test_cli.py::test_redact_blob_and_then_blob_get_says_erased
```
Afterwards the file was restored and checked with `cmp`.

One existing test changed its arrangement and keeps its expectation: `test_an_endpoint_without_a_scheme_is_one_sentence[blob-get]`. It used an address no event names, which now gets the log's answer (exit 1) before any store is built. The address is now named by an event written through `core` (`_append_naming`), and the expected event count is 1 for that case.

### Minor 6: complexity measured under the project configuration
For `ea62154` (the files exported with `git show` to the scratchpad):
```
uv run ruff check --config pyproject.toml --config 'lint.mccabe.max-complexity = 1' --select C901 --output-format concise <scratchpad>/head/
```
For the tree:
```
uv run ruff check --config 'lint.mccabe.max-complexity = 1' --select C901 --output-format concise src/previously/cli.py src/previously/core/verify.py src/previously/core/redact.py src/previously/core/redaction.py
```

| Function | `ea62154` | now |
|---|---|---|
| `examine` | 9 | 9 |
| `_execution_findings` | 6 | 7 |
| `_cmd_show` | 8 | 8 |
| `_cmd_blob_get` | 6 | 7 |
| `_cmd_verify` | 5 | 5 |
| `_delete_obsolete` | — | 6 |
| `redact_units` | 8 | 8 |
| `redact_blob` | — | 5 |
| `parse` | 9 | 9 |

- These are the same figures the `--isolated` measurement gave, except `_delete_obsolete`. That function went from 5 to 6 when the singular and plural sentences became two literals at the end of round 0.
- Under the project configuration nothing exceeds 9.
- No comment in the tree cites any of these figures.

### Counts and gates
- Tests: **606** (604 + 2: the `InvalidKey` case and the `blob get` test).
- `print` count: unchanged at 32 (re-measured; `grep -c T201` → 32).
- `uv run ruff check .` → `All checks passed!`
- `uv run ruff format --check .` → `69 files already formatted`
- `uv run pyright` → `0 errors, 0 warnings, 0 informations`
- `uv run lint-imports` → `Contracts: 6 kept, 0 broken.`
- `uv run pytest --cov --cov-report=term-missing` → `======================== 606 passed in 72.56s (0:01:12) ========================` (`Total coverage: 98.35%`)
- `make -C docs html` → `build succeeded.`; `make -C docs vale` → `✔ 0 errors, 0 warnings and 0 suggestions in 24 files.`; `make -C docs linkcheck` → `build succeeded.`
- `uv run pytest -p no:randomly` → `======================== 606 passed in 74.38s (0:01:14) ========================`
- The tutorial's test-run block was retyped from a real run: `606 passed in 72.34s`.

### Concerns
- The append-versus-redact race is now named on the pages but not prevented. It stays an open point for the map (spec §12).
