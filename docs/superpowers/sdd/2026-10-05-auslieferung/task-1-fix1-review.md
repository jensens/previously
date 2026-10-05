# Task 1, fix round 1 re-review (dadaa95..4de9be9)

### Finding Verdicts

1. ADDRESSED. `.importlinter:52-53` renames the contract to `core and contract import no sqlalchemy` (id `core-and-contract-know-no-sql`); sources are still `core` and `contract`, so the name is true. `uv run lint-imports` prints exactly the six names quoted at `docs/explanation/module-boundaries.md:91-96` ("6 kept, 0 broken"). `tests/test_contracts.py:156` holds the new name. `git grep` for the old name outside specs, plans and sdd finds only history: `.importlinter:68-72` (comment saying "was named ... until 2026-10-05"), `module-boundaries.md:104` ("read ... until the same day"), and the two old probe blocks at `:183` and `:188`. Those two blocks are 4-contract, 2026-10-04-era measurements. The sentence at `:105` ("the older blocks further down keep the name of their day") marks them as history. No other quotation of the old name remains.
2. ADDRESSED. `design-records.md:91` now says the directories were walked "until the migrations moved under `src/` on 2026-10-05". `:101` is in the past tense ("printed nothing") and `:102` gives the new command. I ran `grep -rn "§" src tests | grep -v "frozen design record"`: it prints nothing. The same signs stand on 15 lines in 7 files, as `:102` says. The old command (with `migrations`) is kept only as history. It now emits a "No such file or directory" warning on stderr and nothing on stdout, and the page does not claim otherwise.
3. ADDRESSED. `pyproject.toml:85-88` now reads `cli` → `core` | `migrations` → `storage` → `contract`, five modules, with the shared layer explained.
4. ADDRESSED. `module-boundaries.md:110` is now a blank line, so "The second and third lines read ..." starts its own paragraph.

Check of the implementer's new claim (`module-boundaries.md:107`): `.importlinter:11-17` declares the layer `previously.core | previously.migrations`. In import-linter, `|` makes siblings independent, whereas `:` would allow imports between them. So the sentence "an import of `core.units` written into `migrations/dsn.py` broke the first contract with `previously.migrations is not allowed to import previously.core`" is consistent with the configuration. The message form is the mirror of the one already measured for the other direction. I did not re-measure it, because that needs a probe written into the tree and this review is read-only.

### New Breakage in the Fix Diff

None.

### Out-of-Scope Observations

- `module-boundaries.md:183` and `:188` still quote the old name inside old probe output. That is acceptable only because of the sentence at `:105`. A reader who lands on the section "Why the two exemptions were enumerated and not matched" does not see that sentence.
- I did not run the docs gate or `tests/test_contracts.py`. The latter writes probe modules into `src/`, which a read-only review must not do.

### Verdict

All four findings ADDRESSED, no new breakage. Approve.
