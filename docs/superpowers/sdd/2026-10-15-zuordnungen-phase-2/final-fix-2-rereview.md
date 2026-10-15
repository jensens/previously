# Re-review of the F2 re-fix (96dac0f..9b4ffef)

Reviewer: read-only, 2026-10-15. Tree clean after mutations (`git diff`, `git status --short` empty).

## Per finding

- I-1 ADDRESSED: `cli.py:1292-1326` (`_AGAIN`/`_BUILD`/`_RELEASE`, three static sentences), `cli.py:1385` picks `_RELEASE` whenever `found is not None`, in either direction. Test has `newer-version`; `reference/cli.md` quotes the fourth form with the reason. Mutation (always `_BUILD`) -> `[older-version]` and `[newer-version]` red, `[no-state-row]` green.
- M-1 ADDRESSED: `server.py` `except PrivilegeMissing` -> `NOT_PERMITTED` (`auth.py:54`), one WARNING, no traceback; `reference/cli.md` quotes the body. Mutation (branch never matches) -> `test_a_role_the_database_refuses_makes_the_probe_say_so_in_one_line` red, the other probe tests green.
- M-2 ADDRESSED: `Service.answer` (`server.py` ~1029-1035) logs the four classes as one WARNING, client text unchanged; handoff reworded.
- M-3 ADDRESSED: `graph_now()` (`server.py:1725-1732`) raises `RuntimeError` outside a call.
- M-5 ADDRESSED: handoff states the requirement with reason and "It stands when"; `rebuild-a-projection.md` step 1.
- M-6 ADDRESSED: landkarte status row names PR #26.
- M-7 ADDRESSED: `reference/cli.md` "catches every projection up to the tip of the log".
- M-8 ADDRESSED: `tests/test_projection_worker.py` redact side uses `rebuild=False`.
- M-4 (not built, F-f) HONESTLY LISTED: `core/graph_read.py:25-32` docstring, `docs/explanation/projections.md:370-373`, landkarte (point under Zuordnungen, ruling F-f, finding M-4).
- F-e ADDRESSED: `Service`, `build_server`, `build_app` require `graph` and `projections`; no fold branch in `reading`; probe always reads the state row; no remaining text on a projection-less mode (grep of `src tests docs`).

## F-e call-site classification (`read_graph(` / `fold_graph(` in `src/`)

- `cli.py:2690` (`approve`), `2728` (`_rejection_of`), `3368` (`_stated`, builds a claim), `3845` (`answer`): write path.
- `cli.py:3580`: `relations --as-of`, kept.
- `mcp_server/server.py:1739` `graph_of`: only callers are `claims_staged`, `graph_approval_write`, `graph_rejection_write`, `triage_answer_write`: write path.
- `core/assertions.py:296`, `core/graph_write.py:179`: write path (checks under the tip it locks).
- `core/projection/graph.py:266`: the projection's own build.
- `core/graph_read.py:398`: the fold of named threads from the projection, not a whole fold.
- `core/gaps.py:176`: `policy gaps` / `policy_gaps`, the one serving path left, now listed.
- `verify` and `project --check` fold through `check_graph`, not these two names, as before.

No serving path folds the whole log except `policy gaps`, `verify`, `project --check`, `--as-of` and the write path.

## The three flagged points

1. `reader_bracket_edges` raising `TypeError` on a non-`ProjectedGraph`: acceptable. It is a programming-error guard with a test (`...refuses_a_fold`) and a green control. Retyping to `ProjectedGraph` would run through the `Graph`-typed chain of `mcp_server/read.py`; a Minor to do later, not a defect. It does leave a `cast` after an `isinstance` that already narrows (harmless).
2. Oracle tests monkeypatching `projected_graph` / `reader_bracket_edges`: not covered by the CLAUDE.md ban (time, database, randomness). The replacement is the real fold, the database stays real, and the CLI oracles already did this. Renaming the target fails loudly (monkeypatch raises on a missing attribute). Accept.
3. `_ProbedThrough` rewiring: acceptable. It subclasses the real `PostgresStorage`, serves the start check from the real database, and hands only the probe's snapshot/state row to the failing store, which is the same fault injection the earlier `_Armed` stores used (a failing store, not a stand-in for the database). The server refusing to start against a failing store is the reason, and it is stated in the docstring.

## Mutations re-run by the reviewer

- r1 (I-1): `_BUILD if found is None else _RELEASE` -> `_BUILD`: 2 failed (`older-version`, `newer-version`), `no-state-row` passed.
- r2 (M-1): `except PrivilegeMissing` made unmatchable: 1 failed (the new probe test), 7 other probe tests passed.

## Gates at 9b4ffef

```
uv run ruff check .                 All checks passed!
uv run ruff format --check .        143 files already formatted
uv run pyright                      0 errors, 0 warnings, 0 informations
uv run lint-imports                 Contracts: 9 kept, 0 broken.
uv run pytest --cov ...             2827 passed in 424.57s; TOTAL 11452 stmts, 245 missed, 98 % (pytest run with -p no:cacheprovider)
make -C docs html / vale / linkcheck   built / 0 errors, 0 warnings, 0 suggestions in 51 files / no non-ok entry
```

## New issues introduced by this diff

Critical: none. Important: none.
Minor: `docs/explanation/projections.md` and the handoff are accurate; the `auth.py` module docstring has one overlong line after the reflow (cosmetic, ruff does not check docstring length here).
