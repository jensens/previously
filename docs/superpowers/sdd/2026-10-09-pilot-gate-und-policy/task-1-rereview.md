# Task 1 re-review (5c2e44d..377f713)

1. ADDRESSED - cli.md table row and quoted block (Ten findings), docs reference test count 14, keyed on the new sentence.
2. ADDRESSED - tutorial block is one run (seed 2448098401, 1080 passed); the hand-set number was fully replaced by the retyped block; coverage table and rootdir omitted (not value edits). Minor: run was with --cov, page shows `uv run pytest`.
3. ADDRESSED - version 3 -> 4 example.
4. ADDRESSED - redact.py comment above retrying carries position/tombstone reasoning; new unreachable-store test for the naive datetime check.

New breakage: none.
Out of scope: long docstring line (cosmetic).
Verdict - all findings addressed: yes
