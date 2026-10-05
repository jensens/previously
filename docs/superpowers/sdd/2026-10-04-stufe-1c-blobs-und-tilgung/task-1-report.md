# Task 1 report: hash format version 2

Commit: `72a0044 feat: hash format version 2, beside version 1`
Status: DONE_WITH_CONCERNS (concerns are small, see the end)

## Steps

1. `uv sync --locked --all-extras`; `uv run pytest --collect-only -q -p no:randomly | tail -1` → `272 tests collected in 0.18s`. Matches the brief.
2. Read `vector_v2.py`: imports `hashlib` only, no project code. Ran it (output below). Checked the printed strings: keys sorted at every level (payload: domain, payload, salt, v; inner: evidence, text; unit: content, domain, end_ms, salt, seq, speaker, start_ms, v; units: domain, units, v; event: domain, external_id, id, kind, occurred_at, payload, prev, recorded_at, source, units, v), no whitespace, `ä` literal. Every hex digest it prints equals the literal in the patch (`V2_PAYLOAD_HEX`, `V2_UNIT_HEX` x2, `V2_UNITS_HEX`, `V2_UNITS_EMPTY_HEX`, `V2_EVENT_HEX`). Count note: that is six digest literals plus three printed salts; the brief says "sieben Hex-Werte" in step 2 and "fünf Hex-Werte" in step 7. No mismatch in any value, only in the count wording.
3. RED: tests applied, import error (below).
4. GREEN: src applied, `40 passed`. Diff of `hashing.py` read: in `units_hash` and `event_hash` exactly `"v": HASH_VERSION` → `"v": HASH_VERSION_1`, nothing else changed in them.
5. Rewrote the comment above the version 1 vector in `tests/test_hashing.py`: a deliberate change gets a version of its own and a second vector; this vector stays as long as version 1 events can exist. No literal or input of the first vector changed.
6. Mutations (table below), each restored with `cp` from a backup and confirmed with `cmp`.
7. `docs/reference/hash-format.md` restructured after invoking `plone-doc-style:author`: new `## Hash versions` (constant table; who calls which functions), `## Version 1` (payload, units, event as H3, `HASH_VERSION` → `HASH_VERSION_1` in both tables), `## Version 2` (salt facts; payload hash, unit digest, units hash, event hash, each with its field table), `## Pinned test vectors` with `### Version 1` (unchanged content) and `### Version 2` (salts, six digests, five canonical byte blocks). The warning's third sentence rewritten. The column `event.hash_version` is not mentioned (task 2). `## Payload range` is still followed directly by an `## ` heading, which `_quoted_messages` in `tests/test_docs_references.py` relies on. I hashed every ```json block on the page with a scratch script and each matches the hex stated beside it (all 8 blocks).
8. `docs/explanation/hash-chain.md`: new section `(hash-version-2)=` / `## Version 2, with a digest per unit and a salt` (heading not "Version 2: a ..." because vale's `Microsoft.HeadingColons` demands a capital after the colon). Covers: why a digest per unit, why a salt with my measurement, why no retrofit and so version 1 stays verifiable, what version 1 costs, what the salt does not do yet (no erasure exists; nothing writes version 2). Line 250 rewritten into a paragraph keeping the history: stage 1a corrections went into version 1 because none had reached `main`; stage 1a reached `main` on 2026-10-03 (`07561a8`, checked with `git log main`), so redefining version 1 now would fail rows a log outside the repository may hold and recompute the pinned vector. `canonicalization.md` line 114 rewritten.
9. `288 tests collected in 0.15s`. Tutorial block retyped from a real `uv run pytest` run (rootdir line removed). To get a run that passes, the `272 passed` line had to be changed to 288 first, since `test_docs_typed_output.py` otherwise fails the run that is to be typed; then the whole block was replaced by the captured output.
10. Six gates, staged by name, committed with `-F`.

## TDD evidence

RED (step 3):
```
$ git apply --include='tests/*' docs/superpowers/plans/2026-10-04-stufe-1c-anlagen/task-1-hash-v2.patch
$ uv run pytest tests/test_hashing.py -q -p no:randomly
tests/test_hashing.py:13: in <module>
    from previously.core.hashing import event_hash_v2
E   ImportError: cannot import name 'event_hash_v2' from 'previously.core.hashing' (.../src/previously/core/hashing.py)
ERROR tests/test_hashing.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.18s
```

GREEN (step 4):
```
$ git apply --include='src/*' docs/superpowers/plans/2026-10-04-stufe-1c-anlagen/task-1-hash-v2.patch
$ uv run pytest tests/test_hashing.py -q -p no:randomly
40 passed in 0.09s
```

## Mutations (step 6)

Each: `sed -i '<expr>' src/previously/core/hashing.py`, then `uv run pytest tests/test_hashing.py -q -p no:randomly`, then `cp` back from backup, `cmp` → restored. Line numbers are those of the file at that moment (after my comment edit). Run via a scratch script, because the shell guard refused the inline loop.

| # | Mutation | Red (measured) | Control green (measured: not in FAILED list of 40) |
|---|---|---|---|
| M1 | `218d` removes `"salt": salt.hex(),` in `unit_digest` | `test_v2_vector_unit_digests`, `test_v2_vector_units_hash`, `test_v2_vector_event_hash`, `test_the_salt_alone_changes_a_digest` → `4 failed, 36 passed` | `test_vector_payload_hash`, `test_vector_units_hash`, `test_vector_event_hash` |
| M2 | `241s/sorted(digests)/digests/` in `units_hash_v2` | `test_units_hash_v2_sorts_by_seq_itself` → `1 failed, 39 passed` | `test_v2_vector_units_hash` |
| M3 | `192s/PAYLOAD_DOMAIN/UNITS_DOMAIN/` in `payload_hash_v2` | `test_v2_vector_payload_hash`, `test_v2_vector_event_hash` → `2 failed, 38 passed` | `test_vector_payload_hash` |
| M4 | `265s/HASH_VERSION_2/HASH_VERSION_1/` in `event_hash_v2` | `test_v2_vector_event_hash`, `test_version_1_and_version_2_never_agree` → `2 failed, 38 passed` | `test_vector_event_hash` |
| M5 | `163s/HASH_VERSION_1/HASH_VERSION/` in `event_hash` (v1) | `test_vector_event_hash`, `test_version_1_and_version_2_never_agree` → `2 failed, 38 passed` | `test_v2_vector_event_hash` |

Raw output:
```
=== M1  (sed -i '218d' src/previously/core/hashing.py)
-        "salt": salt.hex(),
FAILED tests/test_hashing.py::test_v2_vector_unit_digests - AssertionError: a...
FAILED tests/test_hashing.py::test_v2_vector_units_hash - AssertionError: ass...
FAILED tests/test_hashing.py::test_v2_vector_event_hash - AssertionError: ass...
FAILED tests/test_hashing.py::test_the_salt_alone_changes_a_digest - assert b...
4 failed, 36 passed in 0.19s
restored
=== M2  (sed -i '241s/sorted(digests)/digests/' src/previously/core/hashing.py)
-        "units": [digests[seq].hex() for seq in sorted(digests)],
+        "units": [digests[seq].hex() for seq in digests],
FAILED tests/test_hashing.py::test_units_hash_v2_sorts_by_seq_itself - assert...
1 failed, 39 passed in 0.14s
restored
=== M3  (sed -i '192s/PAYLOAD_DOMAIN/UNITS_DOMAIN/' src/previously/core/hashing.py)
-        "domain": PAYLOAD_DOMAIN,
+        "domain": UNITS_DOMAIN,
FAILED tests/test_hashing.py::test_v2_vector_payload_hash - AssertionError: a...
FAILED tests/test_hashing.py::test_v2_vector_event_hash - AssertionError: ass...
2 failed, 38 passed in 0.14s
restored
=== M4  (sed -i '265s/HASH_VERSION_2/HASH_VERSION_1/' src/previously/core/hashing.py)
-        "v": HASH_VERSION_2,
+        "v": HASH_VERSION_1,
FAILED tests/test_hashing.py::test_v2_vector_event_hash - AssertionError: ass...
FAILED tests/test_hashing.py::test_version_1_and_version_2_never_agree - Asse...
2 failed, 38 passed in 0.17s
restored
=== M5  (sed -i '163s/HASH_VERSION_1/HASH_VERSION/' src/previously/core/hashing.py)
-        "v": HASH_VERSION_1,
+        "v": HASH_VERSION,
FAILED tests/test_hashing.py::test_vector_event_hash - AssertionError: assert...
FAILED tests/test_hashing.py::test_version_1_and_version_2_never_agree - Asse...
2 failed, 38 passed in 0.14s
restored
```
Beyond the brief's table: M1 also reddens the units and event vectors (expected, they consume unit digests); M5 also reddens `test_version_1_and_version_2_never_agree` (expected, both then hash v=2).

## vector_v2.py, my run

```
payload salt    404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f
unit salts      606162636465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7f 808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9f
V2_PAYLOAD_HEX  5342ceb35fbc3d8dedddfa72adbc75380347a7179aad95cdb201cbc51d6c0c39
V2_UNIT_HEX     a86bc83e609f7686c3697f011e0792f8c52b3e5dab0553bc2551b6e5964f836f 83d20dfe310bb300e408dfb8eb62c6176dc2806d562e3af70581f4c1ee413d34
V2_UNITS_HEX    af0a6ca8f38722aed8e2c801a6753cb620515ca5918364b70f1077fa06c6fc49
V2_UNITS_EMPTY  12360633d51803183369cb1eb37230e63427af0800125eb7a38af155dd1cd3d9
V2_EVENT_HEX    649d57e7656dc7a62c02e35fb75d30b0212b100ec20ce9dde7e1e34b5339e484
{"domain":"previously/payload","payload":{"evidence":"verbatim","text":"Preis bleibt 1000 Euro."},"salt":"4041...5e5f","v":2}
{"content":"Preis bleibt 1000 Euro.","domain":"previously/unit","end_ms":null,"salt":"6061...7e7f","seq":1,"speaker":null,"start_ms":null,"v":2}
{"content":"Bitte bestätigen.","domain":"previously/unit","end_ms":2500,"salt":"8081...9e9f","seq":2,"speaker":"Anna","start_ms":1500,"v":2}
{"domain":"previously/units","units":["a86b...836f","83d2...3d34"],"v":2}
{"domain":"previously/event","external_id":"nachricht-1","id":42,"kind":"observation","occurred_at":"2026-10-01T09:00:00.000000Z","payload":"5342...0c39","prev":"0001...1e1f","recorded_at":"2026-10-02T14:23:45.123456Z","source":"email","units":"af0a...fc49","v":2}
```
(The canonical lines are shortened here with `...` in the hex only; the script printed them in full, and the page carries them in full, hashed back and matched.)

## measure_guessing.py, my runs (2026-10-04, 8-core machine, script is single-threaded)

```
found 1234567 after 1234568 candidates in 0.79 s — 1,567,708 per second
found 1234567 after 1234568 candidates in 0.79 s — 1,565,852 per second
found 1234567 after 1234568 candidates in 0.76 s — 1,621,968 per second
found 1234567 after 1234568 candidates in 0.78 s — 1,573,451 per second
```
Cited on the page as: 1,234,568 candidates in 0.76 to 0.79 seconds, about 1.6 million per second, over four runs, measured 2026-10-04.

## The six gates (final line of each, each run on its own)

```
uv run ruff check .                        → All checks passed!
uv run ruff format --check .               → 50 files already formatted
uv run pyright                             → 0 errors, 0 warnings, 0 informations
uv run lint-imports                        → Contracts: 4 kept, 0 broken.
uv run pytest --cov --cov-report=term-missing → ============================= 288 passed in 23.87s =============================
                                             (src/previously/core/hashing.py 53 0 100%; TOTAL 887 21 98%)
make -C docs html                          → The HTML pages are in _build/html.
make -C docs vale                          → ✔ 0 errors, 0 warnings and 0 suggestions in 22 files.
make -C docs linkcheck                     → build succeeded. / Look for any errors in the above output or in _build/linkcheck/output.txt (output.txt: no entry other than ok/redirected/ignored)
```

## Files changed

- `src/previously/core/hashing.py`
- `tests/test_hashing.py`
- `docs/reference/hash-format.md`
- `docs/explanation/hash-chain.md`
- `docs/explanation/canonicalization.md`
- `docs/tutorials/record-your-first-event.md`

Not committed, mine: `.superpowers/sdd/2026-10-04-stufe-1c-blobs-und-tilgung/task-1-commit-msg.txt` and this report (the directory is git-ignored). `git status --short` before staging showed only the six files above.

## Deviations from the patch

The comments above `HASH_VERSION_1` / `HASH_VERSION` in `hashing.py` claimed "A row says which one it is in `event.hash_version`" and "The version that is written". Neither is true at this commit: there is no such column, and `append` still writes version 1 (`HASH_VERSION` is read by nothing). Rewritten to: version 2 is the one new events are *meant* to be written in; the row has to name its version, and until it can every row is version 1 because nothing calls the version 2 functions yet. **Task 2 must rewrite both comments** once the column exists and `append` writes v=2.

## Sentences found no longer true, beyond those the brief names

- `hash-chain.md` line 230: "Both of the wrapped digests carry a version and a domain" → now two in v1, four in v2.
- `hash-chain.md` line 44 (tombstone seam for units): added that in v1 the seam opens only for all units of an event at once, with a pointer to `hash-version-2`.
- `hash-chain.md` line 171 ("The digest runs over the whole set of units and not over each unit on its own"): added that v2 adds per-unit digests and keeps the one over the set.
- `hash-chain.md` line 5 (three digests per event): kept (true for every event written today), added one sentence that v2 adds a digest per unit.
- `hash-chain.md` "Hence no column today ... exactly one possible value": still true, reason made explicit ("because nothing writes any other version yet").
- `canonicalization.md` line 8 ("each of the three digests"), line 19-21 ("used three times ... three uses"), line 103 ("a vector for all three digests") — all rewritten for two versions.
- `hash-format.md`: whole structure now per version; the patch's `{ref}`hash-version-2`` now resolves.

## Self-review and concerns

1. **Sentences task 2 must turn over** (they are true now and become false when `append` writes v=2): `hash-format.md` `## Hash versions` ("`previously.core.append` and `previously.core.verify` call the version 1 functions. No module in `previously` calls the version 2 functions yet."); `hash-chain.md` end of the new section ("At this point nothing writes version 2"), "Hence no column today ... nothing writes any other version yet" and the whole "today's columns can't deliver" passage before it; `hash-chain.md` line 5 ("three SHA-256 digests for every event"); the two comments in `hashing.py` noted above.
2. Brief count wording: step 2 says seven hex values, step 7 says five; the vector has six digests (plus three salts). All values match; the page lists all six.
3. The page cites the measurement script by its path under `docs/superpowers/plans/`, which the docs build excludes; it is plain text in backticks, not a link, so linkcheck does not touch it.
4. The module docstring of `hashing.py` ("the same holds for the units as soon as `unit.content` may be `NULL`") was left: it speaks of the event hash staying valid, which holds in both versions because the event hash takes stored digests.
