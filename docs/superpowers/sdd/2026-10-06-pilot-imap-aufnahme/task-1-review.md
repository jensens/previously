# Task 1 — review (commit `5aa447a`, base `05ba61e`)

Reviewer: Opus, read-only on the worktree. Read: brief, global constraints, spec §2 (§2.2 table), rulings P-1 and T1-a, the report, the whole diff, `core/append.py` at the head (retry loop, `SourceKeyTaken` branch), `storage/postgres.py` (`begin`, `lookup`, `read`, `insert_event`), `storage/schema.py` (`source_key`), the explanation pages that talk about idempotency.

Measured by me, not taken from the report:

- `ruff check .` green, `ruff format --check .` 75 files formatted, `pyright` 0 errors, `lint-imports` 6 kept. `make -C docs vale` 0/0/0 in 31 files. `tests/test_identity.py`, `tests/test_docs_references.py`, `tests/test_docs_typed_output.py`: 11 passed. `tests/test_append.py` 50 passed, `tests/test_append.py tests/test_cli.py` 323 passed. Did not run `make -C docs html`/`linkcheck` or the whole suite with `--cov` (task-scoped; the report claims them).
- The hashes quoted in `cli.md` recomputed: `--text Hello` gives `f20cefad…3a5d`, `A`/`B` give `7b1a628ef0d8a64e`/`0a422dac18a45b5e`. Match.
- Two probes in the scratchpad against real PostgreSQL (the project's `conftest.py`, nothing in the worktree touched; `git status --short` clean):
  - **Concurrency:** 40 rounds, two threads behind a barrier appending the same new key with different artifact hashes. 40/40: one `list`, one `ArtifactChanged`. Never two ids, never a silent `[id]`.
  - **Known key plus new events in one batch:** `m1` stored with hash `A`, then `append([m1(A), m2, m3])` returns `[1, 2, 3]` and three events stand. That's the path where `_check_artifact` leaves an open server-side cursor before `insert_event` runs on the same connection. It works.

### Spec Compliance

**§2.1.** `ChannelIdentity(channel, role, address, name=None)` as in the brief. `RawEvent.artifact_hash: bytes | None = None` and `channel_identities: tuple[ChannelIdentity, ...] = ()` come after `blobs`. Both get mixed into the payload under the reserved names (hex, and a list of four-key objects in order), and a payload already carrying either name is refused. `payload_hash` covers them (test with a hand edit → two `verify` findings). An event that gives neither has the payload it had before (`{"evidence": …}` alone). Matches.

**§2.2, the table, row by row** (`_check_artifact`, `core/append.py:298-321`):

| Row | Code | Test |
|---|---|---|
| same hash → known, same `id`, nothing written | falls through, `ids.append(existing)` | `test_same_key_same_artifact_is_known` |
| other hash → `ArtifactChanged`, key and both hashes, whole batch not written | raises inside `with storage.begin()`, not caught by either `except`, transaction rolls back | `test_same_key_other_artifact_is_refused_and_nothing_is_written` (new `m2` **before** `m1` in the batch, `m2` absent afterwards) |
| erased (payload `NULL`) → known | `row.payload is None: return` | `test_an_erased_event_stays_known` (payload still `NULL`, two events: original + redaction) |
| no `artifact_hash` → known | `known` not a 64-hex string → return | `test_an_event_without_artifact_hash_stays_known` |

Arriving `None` compares nothing, which is right because §2.1 says "`None` heißt nicht angegeben". `ArtifactChanged` is a `PreviouslyError` with `source`, `external_id`, `known`, `arrived`. `append` makes no decision of its own: it raises, and the CLI turns the error into exit 2.

**The "nothing of the batch written" path by path** (focus 1):

- *Loop body:* raised inside the transaction. Events inserted earlier in the same attempt are rolled back. Holds.
- *Retry on a taken chain position:* `ChainPositionTaken` → backoff → a new attempt re-reads the tip, and `lookup` now sees the competitor's committed key, so the comparison runs on the retry. Measured 40/40 under real concurrency. Holds.
- *`SourceKeyTaken` early return* (`core/append.py:556-569`): the failed attempt's transaction has rolled back, and the reread runs in a separate read-only use of `begin`. So **nothing is written there either**. What that path skips is the *refusal*, not the rollback: with every key taken, it returns ids without comparing. The branch is unreachable from `append` itself, by the four-precondition argument already in that comment, and reachable only by hanging a `source_key` row onto a committed event by raw SQL (finding N-1). That's misuse, so it's named, not fixed (Minor 1). The implementer's added comment says exactly this, and it's true.

**Isolation** (focus 2): `begin` is READ COMMITTED (`storage/postgres.py:155`). PostgreSQL has no dirty reads at any level, so neither `lookup` nor `read` can see a row from a concurrent transaction that hasn't committed, and hence never one that later rolls back. A competitor's uncommitted event at the same chain position makes our `INSERT` block on the unique index. If the competitor rolls back, our insert proceeds. If it commits, we get `ChainPositionTaken` and the retry compares, which the probe confirms. `lookup` and `read` are two statements with two snapshots. In between, the row can't disappear: `source_key.event_id` is a foreign key to `event.id` (`schema.py:160`), and nothing deletes events. The only change it can undergo in between is a committed `redact event` setting `payload` to `NULL`, and then the rule says "known", the same answer as reading after the erasure. So `read(conn, event_id, 1)` returns exactly that row. Sound.

**`check_units` public** (focus 3): its only new consumer is `cli._cmd_append` (`cli.py:442`). `cli` already imported `core.append`, and the import-linter contracts are unchanged and kept. `append` itself still calls it, so the CLI checks twice, which is harmless. One side effect, and a benign one: with `PREVIOUSLY_DSN` unset, `append --text $'\x00'` now reports the unit before the DSN. That's an input error before an environment error. No test pinned the old order. Nothing else depends on the new name. The only leftovers are two test comments that still say `_check_units` (Minor 3).

**CLI sentence and pages** (focus 4): the code's message `"{source}/{external_id} is known with another content (artifact {known.hex()[:16]} ≠ {arrived.hex()[:16]})"` is the global-constraints wording, cut at 16 hex characters. `cli.md` quotes it with `Error: ` as the CLI prints it, and `hash-format.md` quotes it bare. `test_the_reference_quotes_the_refusal_of_another_artifact` holds **both** quotes by raising the exception with the page's values, so it pins the hashes and the cut, not just the static parts. The reserved-key refusal on `hash-format.md` is held against `core/append.py` by `_raised_patterns`. `docs/reference/cli.md`: the exit-code table, the payload example (hash verified), "same `--text` and the same attachments in any order", the erased / pre-hash sentence, and the `redact units` sentence are all true. `hash-format.md`: true except one clause (Minor 4).

**Brief steps:** Step 1: every named test exists with the named content, plus the CLI test and two documentation tests. Step 4: the mutations M1/M2 with controls are in the report. I didn't re-run them, but I read each pair and they read the right thing: the erased test asserts no exception *and* payload still `NULL`, and the refused test asserts the absent `m2`. Step 5: done. Step 6: the tutorial block was retyped per P-1 (`820 passed`, `test_append.py` 50 dots = my 50, `test_identity.py` 3). The commit trailer is `Assisted-By:`.

**Ruled elsewhere, not counted:** stale typed `show` output on the tutorial and two how-tos goes to task 6 (T1-a, concern 1). The unsalted hash surviving `redact units` is named, not fixed (T1-a, concern 2).

### Strengths

- The comparison sits exactly where the brief puts it, inside the transaction that looked the key up, and `LogStore` is untouched, as §2.2 asks.
- The refused-batch test puts the new event *before* the conflicting key, which is the arrangement that actually proves the rollback. With the order reversed it would prove nothing.
- The documentation test produces the quoted sentence by calling the code with the page's inputs instead of matching static fragments. A wrong hash or a 12-character cut goes red (D1/D2).
- The foreign-value test writes its row the way pre-unit `append` did, through `prepare`/`link`/`insert_event`, not by raw SQL.
- `artifact_hash_of` reuses `core.canonical`, and `test_it_is_the_sha256_of_the_canonical_form` spells out the bytes, so a second canonicalisation would fail.
- The new comment at the `SourceKeyTaken` return is honest about the hole instead of claiming coverage.

### Issues

#### Critical

None.

#### Important

None.

#### Minor

1. **`src/previously/core/append.py:556-569` — the all-keys-taken early return skips the comparison.** Nothing is written on that path (rollback, then a separate reread), but a changed artifact under one of the keys would come back as known instead of `ArtifactChanged`. The branch is reachable only through misuse (a `source_key` row hung onto a committed event, N-1), so per the working rule: **name it**, which the new comment does. If anyone touches the branch anyway, the change is cheap: call `_check_artifact(storage, conn, i, e)` for each reread pair inside the reread transaction. Or just `continue`: a retry that finds every key returns from the loop body without writing and compares on the way, and since it's no chain-position collision it won't spin.

2. **`tests/test_append.py` — no test for "known key with the same artifact, plus new events, in one batch".** It's the ordinary shape of a connector run (task 4: a re-sighting beside new mails), and it's the one new code path where `_check_artifact` leaves an open server-side cursor (`next(iter(storage.read(...)))`, `core/append.py:319`) before `insert_event` runs on the same connection. My probe shows it works (`[1, 2, 3]`, three events), so this is a gap in coverage, not a defect. Worth one test here or in task 4. Related, and a "name it": under `-W error::ResourceWarning`, psycopg reports a `ServerCursor … deleted while still open` from this pattern. `core/verify.py:481` uses the same idiom, and `test_verify.py`/`test_redact.py` show 18–19 such warnings at the head already. The cursor dies with the transaction, so it's harmless.

3. **`tests/test_append.py:487` and `:530` still name `_check_units`.** Line 487 is a present-tense claim ("four of the six messages in `_check_units`") about a name that no longer exists. Line 530 sits inside a dated measurement, so it could arguably stay. A comment is a claim, and :487 should follow the rename.

4. **`docs/reference/hash-format.md:66` — "only an event written before the key was reserved can carry one".** Through `append`, yes. But `LogStore.insert_event` takes any payload, and the test `test_a_foreign_value_under_the_name_counts_as_no_artifact_hash` writes such a row *today*. Suggest "through `append`, only an event written before the key was reserved can carry one".

5. **`src/previously/core/errors.py:38` — "Raised by `append` before anything of the batch is written."** Strictly, it's raised after earlier events of the batch were inserted, and they're then rolled back. `core/append.py` says it right ("Raised inside the transaction, so nothing of the batch is written"). Suggest: "Raised by `append` inside its transaction, so nothing of the batch is written."

6. **`src/previously/cli.py:454` with the documented sentence at `docs/reference/cli.md:137` — the CLI artifact is the text byte for byte, while the units normalise line endings.** The same text with CRLF and with LF gives identical units but another artifact, so it's refused under a known key. This follows §2.2 literally ("SHA-256 des übergebenen Texts") and is arguably right: what was submitted differs. It can happen in ordinary use, though (the same note pasted from two editors). Whether it's a decision or an accident is the controller's call. Either the page says "byte for byte, line endings included", or the CLI hashes `normalize_line_endings(args.text)`. Not a defect against the spec.

7. **A refused `append --attach` now leaves its new blobs in the bucket.** `_attach` stores before `append` refuses, and the test `…_sorted_attachment_addresses` uploads `third.txt` and then gets exit 2. This is the accepted "blob first" order (`docs/explanation/blobs.md:168-176`), and `cli.md:168` ("or the append fails") already covers it, but `ArtifactChanged` makes it an ordinary-use path rather than a failure path. **Name it**, perhaps on the map entry for the missing sweep. No change in this task.

8. **Named by the implementer and confirmed as misuse-only:** an arriving `artifact_hash` that isn't 32 bytes is stored as-is and then compares as "none" forever. Per §2.1 it's mandatory for a connector, so a connector bug would silently switch the rule off for its keys. Refusing `len(event.artifact_hash) != 32` in `_identities` is a one-line guard if anyone wants it. **Name it.**

### Assessment

**Approved.** Every row of the §2.2 table holds and is tested. "Nothing of the batch written" holds on every path, including the early return, which writes nothing and skips only the refusal, and only under misuse. The comparison is sound under READ COMMITTED and measured under real concurrency. `check_units` has exactly the one new consumer it was made public for. The CLI sentence matches the global constraints, and `test_docs_references` holds both quotes. The eight Minors are wording, coverage, or named-not-fixed. Of them, 3, 4 and 5 are one-line text fixes worth taking along in a later commit. 2 is worth a test, here or in task 4. 6 needs a decision.
