# Task 1 review: hash format version 2 (88e9db4..72a0044)

Reviewer read the brief, the global constraints, the report and the review diff.
Checks outside the diff, each against a named risk:

- Risk: something outside `hashing.py` reads `HASH_VERSION` and changes behavior now that its value moved from 1 to 2. Check: `grep -rn HASH_VERSION src docs` (excluding `docs/superpowers` and the two files under review). Result: no reader in `src/`; only the pages under review mention it.
- Risk: the date in `hash-chain.md:256` ("Stage 1a reached `main` on 2026-10-03") is false. Check: `git log -1 07561a8` gives `2026-10-03 09:39:09 +0200 feat: stage 1a — the log`, and `git merge-base --is-ancestor 07561a8 main` holds.
- Risk: wrong commit trailer. Check: `git log -1 --format=%B 72a0044` ends in `Assisted-By: Claude Opus 5.5 <noreply@anthropic.com>`; no `Co-Authored-By`, no "Generated with".
- Risk: the page misdescribes what `measure_guessing.py` measures. Check: read the script. It hashes a version 2 unit header without salt, content `+43 660 %07d`, single-threaded plain Python, and stops at candidate 1,234,567 (so 1,234,568 tried). The page's description matches; the figure is the implementer's own (0.76 to 0.79 s, four runs, 2026-10-04), not the script header's (0.72 s).

No test was re-run; the independent vector computation below is the only code executed.

### Spec Compliance

- ✅ Spec compliant.
  - Interfaces: `HASH_VERSION_1 = 1`, `HASH_VERSION_2 = 2`, `HASH_VERSION = HASH_VERSION_2`, `PAYLOAD_DOMAIN`, `UNIT_DOMAIN`, `SALT_BYTES = 32`, `new_salt`, `payload_hash_v2(payload, salt)`, `unit_digest` keyword-only, `units_hash_v2(digests: Mapping[int, bytes])` sorting itself, `event_hash_v2` with the arguments of `event_hash` — all as given (`src/previously/core/hashing.py:561-581`, `643-741`).
  - Version 1 untouched: in `units_hash` and `event_hash` exactly `"v": HASH_VERSION` → `"v": HASH_VERSION_1` (diff lines 604-605, 627-628); `payload_hash` unchanged; no literal and no input of the first vector changed (`tests/test_hashing.py` hunk at 216-245 touches only the comment).
  - Step 5: the comment above the version 1 vector is rewritten (`tests/test_hashing.py:225-228`) and no longer tells anyone to recompute.
  - Step 6: all five mutations from the brief's table run, each with the red tests the brief names and the green control it names, with raw output in the report. The extra reds (M1 also reddens units/event vectors, M5 also reddens `never_agree`) are explained and expected.
  - Step 7: `docs/reference/hash-format.md` has the four version 2 forms with field tables, the version constants, the second vector with salts, six digests and five canonical strings, and where it stands; the warning's third sentence is rewritten (line ~386); both `(HASH_VERSION)` table cells now read `HASH_VERSION_1`; the `event.hash_version` column is not mentioned, as the brief requires for this task.
  - Step 8: `(hash-version-2)=` exists on `docs/explanation/hash-chain.md:192` and covers all five points: digest per unit, salt with the implementer's own measurement and date, no retrofit and therefore version 1 verified for good, the cost of version 1, and what the salt does not do yet. The sentence at old line 250 is rewritten keeping the history (`hash-chain.md:254-258`); `canonicalization.md:82-84` is rewritten.
  - Step 9: tutorial block retyped, `288 passed`; 16 new tests counted in the diff (11 plain plus one with five cases), `tests/test_hashing.py` row shows 40 dots.
  - Beyond the brief, the implementer caught further sentences made false or incomplete (`hash-chain.md:233` "Both of the wrapped digests", `canonicalization.md:8`, `19-22`, `68`), which the global constraints ask for.
- ⚠️ Cannot verify from diff: that the six gates are green at 72a0044 (taken from the report, not re-run, per the instructions); that `{ref}` labels in code resolve is covered by `tests/test_docs_references.py`, reported green.

### The vector, recomputed

Computed with a throwaway script under the scratchpad (`v2.py`), using `hashlib` only, with canonical strings typed by hand from the test file's inputs: payload `{"text": "Preis bleibt 1000 Euro.", "evidence": "verbatim"}`, units from `VECTOR_UNITS`, salts `bytes(range(64,96))`, `bytes(range(96,128))`, `bytes(range(128,160))`, `prev = bytes(range(32))`, `id` 42, `kind` observation, recorded `2026-10-02T14:23:45.123456Z`, occurred `2026-10-01T09:00:00.000000Z`, source `email`, external id `nachricht-1`. Keys sorted, no whitespace, `ä` as itself (UTF-8 `c3 a4` confirmed in the encoded unit 2 string).

| Digest | Recomputed | Equals the literal in `tests/test_hashing.py` |
|---|---|---|
| payload | `5342ceb35fbc3d8dedddfa72adbc75380347a7179aad95cdb201cbc51d6c0c39` | yes (`V2_PAYLOAD_HEX`) |
| unit 1 | `a86bc83e609f7686c3697f011e0792f8c52b3e5dab0553bc2551b6e5964f836f` | yes (`V2_UNIT_HEX[0]`) |
| unit 2 | `83d20dfe310bb300e408dfb8eb62c6176dc2806d562e3af70581f4c1ee413d34` | yes (`V2_UNIT_HEX[1]`) |
| units | `af0a6ca8f38722aed8e2c801a6753cb620515ca5918364b70f1077fa06c6fc49` | yes (`V2_UNITS_HEX`) |
| units, empty | `12360633d51803183369cb1eb37230e63427af0800125eb7a38af155dd1cd3d9` | yes (`V2_UNITS_EMPTY_HEX`) |
| event | `649d57e7656dc7a62c02e35fb75d30b0212b100ec20ce9dde7e1e34b5339e484` | yes (`V2_EVENT_HEX`) |

My canonical strings are identical to `JCS_V2_PAYLOAD`, `JCS_V2_UNITS`, `JCS_V2_UNITS_HASH` and `JCS_V2_EVENT` in the test file and to the five `json` blocks on `docs/reference/hash-format.md`; no difference found. The empty units hash string I used is `{"domain":"previously/units","units":[],"v":2}`, which the test pins only by its digest, not by a canonical string.

### Strengths

- The version 1 functions changed by exactly the one word allowed, and the v1/v2 domain separation is pinned by `test_version_1_and_version_2_never_agree`, with M5 as the control that the v1 vector really holds version 1.
- Each vector test asserts both the hex literal and the hash of the hand-written canonical string, so a failure points at the field that moved.
- The implementer's departure from the patch at the `HASH_VERSION` comments is correct on the merits: the patch's "A row says which one it is in `event.hash_version`" and "The version that is written" are both false at this commit (no column; `append` writes version 1; grep confirms nothing reads `HASH_VERSION`). The rewrite says what is true and the report hands task 2 the sentences it must turn over.
- The history in `hash-chain.md:254-258` is kept rather than deleted: why stage 1a corrected into version 1, and why that stopped being right once 1a reached `main`, with a date that checks out.
- The measurement is the implementer's own, with range, run count and date; the brief's discrepancy in hex counts (seven/five vs. six) was reported instead of papered over.

### Issues

#### Critical (Must Fix)

None.

#### Important (Should Fix)

None.

#### Minor (Nice to Have)

1. `src/previously/core/hashing.py:578-580` (`SALT_BYTES` comment, from the patch): "they are erased together with that content" states as present fact an erasure that does not exist at this commit; `hash-chain.md:214` says the same thing correctly as "is meant to be erased". The implementer applied the stricter reading to the `HASH_VERSION` comments but not here. Likewise `unit_digest`'s docstring (`hashing.py:675-678`): "a stored unit may have lost its content to an erasure" — at this commit `unit.content` is `NOT NULL` and nothing erases. Both become true later in this stage; either reword to intent now or put them on task 3's list of sentences to check.
2. `src/previously/core/hashing.py:556` — "Version 1 is what every event written before stage 1c carries": at this commit the code in stage 1c still writes version 1, which the same comment's last sentence admits. Harmless, but task 2 should rewrite it together with the two comments the report already names.
3. `docs/reference/hash-format.md:371` — "`seq` doesn't stand in the list, because every unit digest covers its own." A reason on a reference page; the second clause belongs to the explanation page (or can go, since the unit digest table already shows `seq`).
4. `docs/explanation/hash-chain.md:215-216` — "the check has both halves of the input" / "missing half of what went into it": the input has more than two parts (seq, offsets, speaker, domain, v). The picture is fine as rhetoric but reads as a count; "missing the salt" would be exact.
5. `docs/reference/hash-format.md:267` — `HASH_VERSION` described as "the version new events are meant to be written in" while the next line says `append` calls version 1. True, and plan-mandated (`HASH_VERSION = HASH_VERSION_2` is in the brief's Interfaces), but the constant names a value no writer uses until task 2; noted so the branch review checks task 2 closes it.

### Assessment

**Task quality:** Approved
**Reasoning:** The interfaces, the untouched version 1, the second vector (independently recomputed and matching in all six digests and all canonical strings), the mutations with controls and both pages meet the brief; what remains are wording points about not-yet-existing erasure that the following tasks of this stage resolve.
