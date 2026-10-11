# Task 4 review: `mcp_server/render.py` (b37aeb6..6b92903)

Reviewer: task-scoped gate, adversarial.
Measured on 2026-10-11 with `uv run pytest tests/test_render.py` (37 passed) and in-process probes and mutations.
The probes monkeypatched the module from scripts in the scratchpad, with Hypothesis `database=None`.
Nothing in the worktree was changed.

## Spec compliance

| Requirement | Verdict | Where |
|---|---|---|
| Fence `<<<customer-content TAG>>>` … `<<<end TAG>>>`, TAG = `secrets.token_hex(4)`, one per answer, shared by all fences | ✅ | render.py:155-157, 217-222, 359-361 |
| Tag redrawn if it occurs in the sanitized content (case-insensitive) | ✅ code, ❌ untested in `render_page` (I-3) | render.py:147-152, 359 |
| Sanitizing: C0/C1 except `\n` `\t`, ESC sequences, `Cf`, tag block U+E0000–E007F; counted; header `· N control characters removed` | ✅ (8-bit CSI body survives, M-2) | render.py:65-70, 113-137, 270-274 |
| "Every string that reaches the page passes through `sanitize`" (module docstring, brief Step 1) | ❌ truncation note uses the raw URI (I-2) | render.py:213-214, 259 |
| Subject inside the fence | ✅ | render.py:233-234 |
| Heading: URI · time · source · sender → recipients, sanitized, one line | ✅ | render.py:190-205 |
| Units marked inside the fence | ✅ (form differs from K §6 `#unit-<n>`, M-9) | render.py:236 |
| Placeholders exactly `[withheld: <uri> — <reason>]`, `[erased: <uri>]`, without subject or address | ✅ | render.py:263-267 |
| Truncation pointer `… truncated — continue with get_event ids=[<id>] from_unit=<n>` | ✅ | render.py:213-214 |
| Ruling R-5: a single unit over the page does not point at itself | ❌ absent (ruling postdates the implementation, not the implementer's fault) | render.py:252-255; test_render.py:320-325 pins the old behavior |
| `PAGE_CHARS` comment: value from the spec, measurement still open | ✅ content, ❌ citation wrong (I-5) | render.py:45-52 |
| Page never exceeds `PAGE_CHARS`, header and footer included | ✅ measured, but rests on untested caps (I-4) | render.py:288-295, 332, 348-349 |
| Cursor: URL-safe base64 of canonical JSON `{"after": [...], "filters": {...}}`; other filters → `ValueError` | ✅ | render.py:373-405 |
| `render_error` starts with `Error: ` | ✅ | render.py:367-370 |
| Footer names page and cursor (unit spec §5.1) | ⚠️ footer names only the cursor (M-8) | render.py:284-285 |
| No mocks of randomness, time or database; no `# type: ignore`; no suppressions; English | ✅ | grep over the diff: none |
| Tutorial block retyped from one run | ✅ self-consistent: 1,382 dots, every percentage equals `floor(cumulative × 100 / 1382)` | docs/tutorials/record-your-first-event.md |

## Strengths

- Laying the page out with an 8-NUL sentinel and swapping the tag in afterwards is neat.
  The tag is drawn against exactly the sanitized strings that stayed on the page, and the swap cannot change a length.
- The length accounting is exact: `_length` reproduces the assembled page byte for byte.
  The cut budget in `_shown_block` was checked by hand, including the note-width reserve.
  A fuzz run of 3,000 random pages fed the module dirty headings, 0–15 recipients, units up to 120,000 characters, seqs up to 10^7 and pages up to 10^6.
  The longest page came to 59,998 characters, no page exceeded `PAGE_CHARS`, every page had at most one tag, and opening and closing fences always balanced.
- Fence escape attempts failed:
  - `<<<end 0000beef>>>` in a unit;
  - an uppercase copy of the tag in the content, which the redraw lowercases;
  - a closing line split across two units, where the `[unit n]` marker always separates them;
  - a closing line in the sender, which is flattened onto the `###` line and also feeds the tag check;
  - NULs aimed at the sentinel, which `sanitize` removes.
- `decode_cursor` raised a `ValueError` (or subclass) on every garbage input tried.
  The inputs were: `""`, `"A"`, `"@@@@"`, non-ASCII, `[1]`, `{"after":5}`, a bool or float id, three-element `after`, missing `filters`, invalid UTF-8, trailing junk, and a 5,000-digit id.
  A tz-aware non-UTC datetime with microseconds round-trips equal.
  Reordered filter mappings are canonical (`sort_keys`, dict comparison).
  No integer reaches the client: the cursor is an opaque string.
- The implementer's mutation claims were reproduced in-process:
  - fixed tag → `test_two_answers_do_not_share_a_tag` red;
  - `Cf` kept → six tests red, the property among them;
  - no truncation → four red;
  - control green.
- The Hypothesis property does catch a `Cf`-only leak in a heading field.
  With the sender cleaned of `Cc` but not `Cf`, it was red 20 out of 20 runs (Risk 5).

## Issues

### Critical

None.

### Important

**I-1. Ruling R-5 is not implemented** (render.py:252-255; test_render.py:320-325).
A unit that alone exceeds the page is cut inside and gets `from_unit=<its own seq>`, so `get_event` would serve the same cut again.
Reproducer: `render_page("t", [Shown(head, ((7, "z"*100_000),))], cursor_for=str)` ends with `… truncated — continue with get_event ids=[42] from_unit=7`.
`test_the_only_unit_over_the_limit_is_cut_inside_too` asserts exactly this loop (`"from_unit=1" in page.text`).
Fix:
- In the `if not shown:` branch, end the cut unit with an honest note that the rest of unit `n` is not served in the pilot.
- If further units follow, keep the boundary pointer and point it at the next unit (`from_unit=<next seq>`), never at `n`.
- With no further unit, give no `get_event` pointer at all.
- Rewrite the test so it asserts no `from_unit=<n>` for the cut unit, and add the case where a unit follows (pointer to `n+1`).
- Measure: restoring `from_unit = seq` turns the new test red.

**I-2. The truncation note puts the raw URI on the page** (render.py:208-214, 259).
`_truncation_note(item.head.uri, …)` takes the unsanitized URI.
`_event_id` falls back to the whole string when it does not end in digits.
Reproducer:

```python
render_page("t", [Shown(Head("evt\x1b[2J‮", M, "email", "Eva", ("Jens",), "S"), ((1, "z"*100_000),))], cursor_for=str)
```

The last line is `'… truncated — continue with get_event ids=[evt\x1b[2J‮] from_unit=1'`, so ESC and U+202E reach the page.
That breaks the module docstring ("every string that reaches the page passes through it") and the brief's "kein Ausgabezeichen außerhalb von `sanitize` ungeprüft".
It is not reachable while Task 5 builds URIs from integer ids, which is why it is not Critical.
The property cannot see it: the `Shown` URI is fixed and no generated page reaches truncation.
Fix:
- Compute the cleaned URI once in `_shown_block` (`counter.line(item.head.uri)`, already done inside `_heading`) and pass that to `_truncation_note`.
- Add a test with a dirty `Shown` URI on a truncated page.

**I-3. The redraw in `render_page` is an assurance without a test** (render.py:359).
`draw_tag` is tested alone, but nothing checks that `render_page` feeds it the page content.
Measured: with `draw_tag` replaced by one that ignores its `content`, and separately with `_Counter.text` no longer recording content, **all 37 tests stay green**.
Fix:
- Give `render_page` the same seam `draw_tag` has, for example `tags: Iterator[str] | None = None`, passed through to `draw_tag(candidates=…)`.
  That is not a mock of randomness; it is the same pattern the implementer already chose.
- Test that a page whose unit, and separately whose sender, contains the first candidate uses the second.
- Measure red with `draw_tag("")`.

**I-4. The heading caps carry the page bound and nothing tests them** (render.py:54-57, 196-198).
The cut path assumes the heading of one event fits; `_FIELD_CHARS` and `_MAX_RECIPIENTS` are what make that true.
Measured: with `_MAX_RECIPIENTS = 10**9`, all 37 tests stay green.
Yet a mail to 400 recipients with 300-character names then renders to **81,210 characters**.
A mailing-list mail makes this realistic, not a misuse.
Fix:
- Add a test with about 400 long recipient names and a long sender.
- Assert `len(page.text) <= PAGE_CHARS` and the `+390 more` tail.
- Measure red with the cap removed.

**I-5. The `PAGE_CHARS` comment cites the wrong paragraph** (render.py:49-51).
The comment says "that measurement belongs to the acceptance run (section 12, item 2 of the unit specification)".
§12 item 2 of the unit specification is "Die Kette kennt die vier neuen Felder …".
The open measurement is **§13** ("Was offen bleibt") item 2: "Die Grenze von 60.000 Zeichen je Seite an echten Mails nachmessen".
The plan's decision 4 puts the measurement "im Bau", not at acceptance.
A comment is a claim, and a pointer to the wrong item is worse than none.
Fix:
- Cite §13 item 2.
- Drop "acceptance run".
- Since the project rule says open points live in `docs/superpowers/landkarte.md`, point there once the point is moved.

### Minor

**M-1. Two of the implementer's own additions have no red-measured test.**
`Cs` removal (render.py:116) and the U+2028/U+2029 flattening in heading fields (render.py:71) are both untested.
Measured: dropping `Cs` from `_removable`, or `  ` from `_LINE_BREAKS`, leaves all 37 green.
Hypothesis `st.text()` excludes surrogates by default, so the property never generates one.
Add `sanitize("a\ud800b") == ("ab", 1)` and a sender containing ` ` that must not split the `###` line.

**M-2. 8-bit CSI leaves its parameter bytes** (render.py:65-70).
`sanitize("\x9b31mred") == ("31mred", 1)`; only U+009B goes.
To remove the whole sequence, extend the CSI branch to `(?:\x1b\[|\x9b)[0-?]*[ -/]*[@-~]`, and likewise OSC `(?:\x1b\]|\x9d)`.
For comparison, an unterminated `\x1b]0;t` drops only `\x1b]`, leaving `0;t`, which is acceptable.

**M-3. Invisible characters outside `Cf` survive.**
Decision 5 does not name them, so this is a question for the controller rather than a defect.
They survive because they are categories `Mn` and `Lo`:
- variation selectors U+FE00–FE0F and **U+E0100–E01EF**, the "variation-selector smuggling" channel, analogous to the tag block;
- Hangul fillers U+115F, U+1160, U+3164 and U+FFA0;
- U+034F;
- U+2800.

Measured: `sanitize("ᅟㅤ⠀͏")` returns all four unchanged.
At least U+E0100–E01EF could go without hurting German text.
`Default_Ignorable_Code_Point` is the principled set.

**M-4. U+2028/U+2029 inside the fence: acceptable as is.**
They are kept in units (`sanitize(" x ")` removes 0).
They are not Markdown line endings (CommonMark knows LF, CR, CRLF), and they cannot close the fence without the tag.
In the heading they already become spaces, which is where a line break would matter.
Optional: map them to `\n` in units.
No action required.

**M-5. CR: removed, which is fine here.**
A lone CR joins words: `sanitize("l2\rl3") == ("l2l3", 1)`.
But `core/units.py:26` normalizes `\r\n` and `\r` to `\n` before units are stored, so this reaches only heading fields, which are flattened anyway.
CRLF mail text is not broken, and CR does not inflate the removed count for units.

**M-6. The cursor is neither sanitized nor bounded** (render.py:277-285).
`cursor_for` output goes raw into the header and the footer.
With `cursor_for=lambda i: "c"*40000` the page is 80,271 characters, on both the fitting and the cut path.
It is reachable only if Task 5 passes something other than `encode_cursor` output, or a filter string tens of kilobytes long.
That is misuse: name it in the `render_page` docstring as a contract ("`cursor_for` returns an `encode_cursor` value") and do not chase it further.

**M-7. `decode_cursor` leaks parser messages.**
Every malformed input raises a `ValueError` subclass, as required.
But the messages vary: `Expecting value: line 1 column 1 (char 0)`, `'utf-16-le' codec can't decode …`, `Exceeds the limit (4300 digits)…`, `too many values to unpack …`.
If Task 5 echoes `str(error)` into `render_error`, the model sees internals.
Adding `ValueError` to the `except` tuple at render.py:401 makes them all `malformed cursor`.

**M-8. The footer names no page.**
Unit spec §5.1 says "Der Fuß nennt Seite und `cursor`"; the footer (render.py:284-285) names only the cursor, while the page is in the header.
Either add the page to the footer or record the deviation.

**M-9. The unit marker does not use the URI form.**
K §6 says "eine Einheit als `#unit-<n>`".
The marker `[unit n]` (render.py:236) leaves the model to assemble `previously://event/42#unit-3` itself.
Consider `[#unit-3]`.
The controller's resolution fixed placement, not form.
The forgeability of the marker inside the fence is acknowledged and not counted here.

**M-10. One assertion can never fail** (test_render.py:167).
`heading[0].count("\n") == 0` runs on an element of `splitlines()` and is always true.
The test is still guarded by line 171; drop the dead assertion.

**M-11. A lot of attacker-settable text sits outside the fence.**
This was acknowledged by the implementer and follows the spec.
Per event, sender plus ten recipients at 200 characters each come to about 2.2k characters of possibly mail-derived prose outside the fence, on a `###` line.
Whether display names come from mail headers or from operator-maintained `channel_identities` is decided in Task 5.
If from headers, consider a much smaller name cap (for example 80).

## Assessment

**Needs fixes.**
- I-1 (R-5) is required by the ruling.
- I-2 breaks the module's central sanitizing promise, cheaply fixable.
- I-3 and I-4 are assurances that were measured to survive their own removal.
- I-5 is a wrong pointer in a comment.

All five fit in one fix round.
The minors can ride along or be named and left.
