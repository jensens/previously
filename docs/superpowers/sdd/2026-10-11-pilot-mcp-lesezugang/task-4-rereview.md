# Task 4 re-review (fix round 1, 6b92903..3d9b911)

Measured 2026-10-11: `uv run pytest tests/test_render.py -q` gives 68 passed; probes via `uv run python`.

## Items
- I-1 / R-5: RESOLVED. render.py:244-253 (`_cut_unit_note`), 297-303. Probes: a lone 70,000-char unit ends "the rest of unit 7 is not served in the pilot", no pointer, page 59,951 chars. First of two units ends with "...; continue with get_event ids=[42] from_unit=2". Last unit and middle unit of 70,000 (preceded by a small unit 1) are boundary cuts that keep unit 1 and point at `from_unit=2` (the unit not shown, never a cut one); 201 chars.
- I-2: RESOLVED. render.py:270 computes the cleaned URI once; used in heading and both notes (291, 298, 303, 306). Dirty-URI test is present per the report.
- I-3: RESOLVED. render.py:351, 407; tests/test_render.py:395-416 (candidate in a unit, in the sender, absent).
- I-4: RESOLVED. tests/test_render.py:429-438 (400 recipients, `<= PAGE_CHARS`, `+390 more`) and the 200-char field cap test at 441.
- I-5: RESOLVED. render.py:44-53 cites section 13 point 2 and plan decision 4, says "NOT measured".
- Minor surrogates and U+2028/2029 tests: RESOLVED. test_render.py:450-462. Probe: `sanitize("a\ud800b") == ("ab", 1)`; the separators are in `_LINE_BREAKS` (line 74, checked with od).
- Minor 8-bit CSI: RESOLVED. render.py:68-73. Probe: `sanitize("a\x9b31mb") == ("ab", 4)`, and 8-bit OSC `("ab", 5)`.
- Minor dead assertion: RESOLVED (removed, per the diff).
- R-6: RESOLVED. render.py:78-94, 137. Probe: U+FE00, FE0F, E0100, E01EF, 034F, 115F, 1160, 3164 and FFA0 each give `("ab", 1)`. Tests (parametrized plus a property) are present.
- R-7: RESOLVED. `#unit-<n>` at render.py:275, 300; footer "End of page N." at 331-332 with a test at test_render.py:250-257; `decode_cursor` raises the single message `cursor is not valid for these filters`, `from error` at 452. Probe: the cause is a JSONDecodeError.
- Tutorial block: RESOLVED. 1413 dots across the progress lines sum to N = 1413, and all 47 percentages equal `int(100*cumulative/1413)`. The seed line and the `1413 passed` line agree.

## New issues
- Minor: the `render_page` docstring (render.py:361-363) still says the rest of a cut item is "reachable through `get_event` with `from_unit`". For a unit cut inside that is no longer true under R-5 (the pilot serves no more of it). Wording only.
- Minor: render.py:291 defaults the boundary note to `from_unit=0` when an item has no units. That path cannot truncate, so it is unreachable and harmless.
- Minor: render.py:355, the docstring line, is long (about 100 characters). The report says ruff passes, so it is within the configured limit.

No Critical or Important issues.

## Verdict
Approved
