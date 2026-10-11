### Finding Verdicts
1. ADDRESSED. docs/reference/cli.md:967-1000 now states the summary line (`client NAME` and `processor PROVIDER`, tab-separated), the prompt and the two token lines, and "prints nothing after the two lines". tests/test_cli.py (new test, ~line 4450) pins lines[0] as the escaped summary, plus the token line, the footer and the line count of 3. It also pins the page phrases.
2. ADDRESSED. src/previously/cli.py:1819 now uses `escape_field(args.name)`. The new test uses the name "a\tb" and asserts `client a\\tb: token `.
3. ADDRESSED, no code change needed. Verified in src/previously/core/policy.py: `_parse` (l.499-547) ends in `_check(item, sentence)`, which calls `_check_client` (l.312-317) for a Client. That raises `_FormError` when the hash is not 64 characters of lower-case hex. `read_policy` (l.577-580) catches `_FormError` and skips the event, so the lookup never sees the damaged hash. The new test in tests/test_policy.py appends a payload with `"é" * 64`, asserts that only "good" remains and that `client_for_token` returns None.

### New Breakage in the Fix Diff
None found by reading. The tutorial diff (docs/tutorials/record-your-first-event.md) is a retyped pytest block: 1331 collected, 1331 passed. That agrees with two new tests (1329 + 2). I did not re-run the suite.

### Out-of-Scope Observations
- The finding-3 test's docstring names `hmac.compare_digest`, which is not shown to be involved in this path. The assertion is still valid.
- The new CLI test imports `Path` inside the function. This is harmless.

### Verdict — all findings addressed: yes
