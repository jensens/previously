# Task 1 — report

Status: DONE_WITH_CONCERNS. Commit `5aa447a` on `worktree-pilot-aufnahme` (base `05ba61e`), not pushed.

## What changed

- `contract/types.py`: `ChannelIdentity(channel, role, address, name=None)`; `RawEvent.artifact_hash: bytes | None = None`, `RawEvent.channel_identities: tuple[ChannelIdentity, ...] = ()` after `blobs`.
- `core/identity.py` (new): `artifact_hash_of(document) -> bytes` = `sha256(canonical(document))`, reusing `core.canonical`, no second canonicalization.
- `core/errors.py`: `ArtifactChanged(PreviouslyError)` with `source`, `external_id`, `known`, `arrived`; message `<source>/<external_id> is known with another content (artifact <16 hex> ≠ <16 hex>)`.
- `core/append.py`:
  - `_identities(event)` refuses a payload carrying `artifact_hash` or `channel_identities` and returns what gets mixed in: `artifact_hash` as hex when not `None`, `channel_identities` as a list of `{channel, role, address, name}` in order when non-empty. Neither key appears when not given, like `blobs` (keeps `test_an_event_without_blobs_carries_no_blobs_key` green unchanged).
  - `_check_artifact(storage, conn, id, event)` is called where `lookup` finds a known key, inside the transaction: arriving `None` → known; `read(conn, id, 1)` → payload `None` (erased) → known; no `artifact_hash`, or a value that is not 64 lowercase hex (`is_address`) → known; different → `ArtifactChanged`, the transaction rolls back, nothing of the batch written. `LogStore` unchanged.
  - `_check_units` → public `check_units` (see below); comment references updated.
  - Comment added at the `SourceKeyTaken` early return: it returns ids without the artifact comparison (branch stays `pragma: no cover`, argued unreachable).
- `cli.py` `_cmd_append`: `check_units(units)` before `_storage()`; inside, after `_attach`, `artifact_hash=artifact_hash_of({"text": args.text, "attachments": sorted(blob.sha256 for blob in blobs)})`. `_payload_line` docstring now names the artifact hash among what `append` adds.
- Docs: `hash-format.md` new section `(artifact-identity)=` "Artifact identity" (the two payload names, the reserved-key refusal, `artifact_hash_of`, the four-row rule, arriving `None`, the foreign value, the message, and that `redact units` leaves the hash); one line in Payload range pointing there. `cli.md` `append`: payload example with `artifact_hash` (real hash of `--text Hello`), what counts as the same, the refusal block, exit-code table, `redact units` sentence. Tutorial test block retyped (ruling P-1): placeholder without count, green plain `uv run pytest` (820 passed), whole block typed from that run without `rootdir:`.
- Tests: `tests/test_identity.py` (3); `tests/test_append.py` +9 (incl. 2 parametrized); `tests/test_cli.py` +2, two existing `show` expectations updated for the new payload; `tests/test_docs_references.py` +2 (the `ArtifactChanged` sentence in both pages produced by raising it; the reserved-key refusal held against `core/append.py`).

### Why `check_units` became public

`artifact_hash_of` canonicalizes `--text`; for a lone surrogate or null byte it would refuse first as `$.text: … — PostgreSQL jsonb cannot store it`, about a document nothing stores, and `test_an_unrepresentable_character_in_argv_gives_one_sentence[--text-…]` (pinned `unit 1: …`) went red. Calling the existing unit check first keeps the message and also refuses before any blob is stored. Alternatives rejected: changing the pinned messages (the jsonb one would be false), or swallowing `InvalidPayload` around the hash.

## TDD evidence

RED 1 (before any production code): collection errors — `ModuleNotFoundError: previously.core.identity`, `ImportError: cannot import name 'ChannelIdentity'`.

RED 2 (types, error, identity in place; `append`/`cli` unchanged), on the new tests:
```
FAILED tests/test_append.py::test_same_key_other_artifact_is_refused_and_nothing_is_written
FAILED tests/test_append.py::test_artifact_hash_and_channel_identities_land_in_the_payload
FAILED tests/test_append.py::test_the_new_names_are_reserved[artifact_hash]
FAILED tests/test_append.py::test_the_new_names_are_reserved[channel_identities]
FAILED tests/test_cli.py::test_another_text_under_a_known_key_is_refused - As...
FAILED tests/test_cli.py::test_the_artifact_of_append_is_the_text_and_the_sorted_attachment_addresses
6 failed, 32 passed, 288 deselected
```
The erased / without-hash / arriving-`None` / foreign-value tests were green here by design: they pin today's behaviour and serve as controls; the mutations below show they read the right thing.

GREEN: `820 passed` (full suite, plain and with `--cov`).

## Mutations (each applied alone, file restored at once, `git status --short` clean afterwards)

| Mutation | Red | Green control |
|---|---|---|
| M1 comparison dropped (`if False: raise`) | `test_same_key_other_artifact_is_refused_and_nothing_is_written`, `test_another_text_under_a_known_key_is_refused` | `test_same_key_same_artifact_is_known`, `test_an_erased_event_stays_known` |
| M2 erased event compared (payload `None` treated as carrying `00…`) | `test_an_erased_event_stays_known` (raises `ArtifactChanged`) | `test_same_key_same_artifact_is_known`, `…_is_refused…` |
| M3 `is_address` guard dropped | `test_a_foreign_value_under_the_name_counts_as_no_artifact_hash` | `test_an_event_without_artifact_hash_stays_known` |
| M4 arriving `None` not skipped | `test_a_sighting_without_artifact_hash_is_known` | `test_same_key_same_artifact_is_known` |
| M5 reserved names not refused | `test_the_new_names_are_reserved[artifact_hash]`, `[channel_identities]` | `test_the_reserved_key_is_refused` |
| M6 CLI attachments unsorted | `test_the_artifact_of_append_is_the_text_and_the_sorted_attachment_addresses` | `test_another_text_under_a_known_key_is_refused` |
| M7 `check_units` dropped from `_cmd_append` | `…argv_gives_one_sentence[--text-\ud800-…]`, `[--text-\x00-…]` | the four `--source`/`--external-id` cases, `test_another_text_under_a_known_key_is_refused` |
| M8 identities not mixed in | `test_artifact_hash_and_channel_identities_land_in_the_payload` | `test_without_either_the_payload_carries_neither_name` |
| D1 `cli.md` quotes a wrong hash | `test_the_reference_quotes_the_refusal_of_another_artifact` | `…_of_a_reserved_identity_key` |
| D2 message cut at 12 hex chars | `test_the_reference_quotes_the_refusal_of_another_artifact` | `…_of_a_reserved_identity_key` |
| D3 reserved refusal reworded | `test_the_reference_quotes_the_refusal_of_a_reserved_identity_key` | `…_of_another_artifact` |

## The `ArtifactChanged` sentence as the CLI prints it

From `test_another_text_under_a_known_key_is_refused` (`--text A`, then `--text B`, same key), stderr, exit 2:
```
Error: cli/a is known with another content (artifact 7b1a628ef0d8a64e ≠ 0a422dac18a45b5e)
```

## Gates (after the last change)

```
uv run ruff check .                 All checks passed!
uv run ruff format --check .        75 files already formatted
uv run pyright                      0 errors, 0 warnings, 0 informations
uv run lint-imports                 Contracts: 6 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing   820 passed in 104.43s; TOTAL 98%; core/identity.py 100%, core/errors.py 100%, contract/types.py 100%, core/append.py 99% (578, the ChainConflict raise), cli.py 99%
make -C docs html                   build succeeded (warnings are errors)
make -C docs vale                   0 errors, 0 warnings and 0 suggestions in 31 files
make -C docs linkcheck              exit 0, 0 broken
```
After the gate run one word changed in `hash-format.md` (vale: "as it is" → "unchanged"); html, vale, linkcheck, ruff and the three docs test files were rerun green after it.

## Concerns

1. **Typed-out `show` output elsewhere is now stale, outside this brief's files.** `payload=` lines no longer match what `show` prints for an `append` event: tutorial `record-your-first-event.md` line 128 (`payload={"evidence": "recollection"}`) and the sentence after it ("the payload holds the kind of evidence and nothing else"); `how-to/erase-something.md` lines 75 and 102; `how-to/attach-and-fetch-a-file.md` line 50. No gate catches it. Retyping them means rerunning those sessions (the tutorial's log/show hashes belong to one session; the how-tos need S3). Not done here; needs a decision (task 6 already touches `erase-something.md`).
2. **The artifact hash is unsalted and survives `redact units`.** For a short or guessable `--text`, the hash in the payload confirms a guess about wording that `redact units` erased; only `redact event` takes it. Spec §2.1 accepts erasure "of the event" taking it along; `redact units` is not addressed. Stated on `cli.md` and `hash-format.md`, not engineered around. Possibly a point for the map / `erasure.md` (task 6).
3. **`SourceKeyTaken` early return skips the comparison.** Unreachable per its existing argument (`pragma: no cover`); a comment now says so. If it ever becomes reachable, a competitor's other artifact passes unrefused there.
4. **Public `check_units`**: a new public name in `core.append`, for the reason above.
5. **Not validated, named here only:** an `artifact_hash` of a length other than 32 bytes, and non-`str` fields in `ChannelIdentity` (canonical form still refuses non-JSON types, null bytes, surrogates). An event from before this unit whose payload carries a 64-hex `artifact_hash` of its caller's own meaning would be compared (misuse-only, per the working rule).
6. Small: `test_docs_typed_output` stayed green with the placeholder in place (no `N passed` left to hold), so the placeholder step has no guard of its own; the old comment in `_cmd_append` about `surrogatepass` ("canonicalisation … reports … naming the field") was already inaccurate before this task and is untouched.
