# Final fix wave — pilot unit 5 (assertions)

One wave, then one re-review. Close every item; there is no second round.
The two reports carry the reproducers:

- code: the final code review — its findings are summarised in `progress.md`
  ("Endprüfung Code", "Messung") and quoted below;
- docs: `final-docs-review.md` if present, otherwise the items below are the
  whole of it.

Rulings F-16 to F-19 are in `progress.md` (German) and binding.

## Code

1. **I-1 — MCP lists drop a direct entry with a pending proposal**
   (`mcp_server/read.py` ~614: `if listing.proposals != (proposed or
   bool(thread.pending()))`). Fix: with `proposals` keep `proposed or
   pending`, without it keep `not proposed` (as `cli.py` ~2465 does). Test: a
   direct entry with a pending proposal appears in the default list labelled
   `1 proposal` and in the proposals list; mutate back → red.
2. **I-2 — content filters run before the policy** (`read.py` ~729 `_listed`
   filters `state`, `overdue`, `proposals` before `_entry` decides). Fix:
   decide the policy first; apply content filters only to entries the client
   sees; a withheld entry passes them unconditionally (it shows as the same
   placeholder whatever the filter), the circle filter stays as it is. Test:
   the placeholder appears identically under `state=open` and
   `state=fulfilled` and `overdue=true/false`; a visible control entry is
   still filtered; mutate → red.
3. **I-3 — `verify` checks only an approval's sources**
   (`core/verify.py` `_Joined` ~498, comparison ~632). Fix: keep body and
   author per open version; report "approval does not take the content and
   the author of its proposal" when either differs (reason may differ) while
   the proposal stands. Test: a forged approval with another `what` is
   reported (mutate → red); an honest approval with a new reason stays green.
   cli.md's list of `verify` findings and the count in
   `test_the_reference_quotes_the_findings_about_assertions` follow.
4. **F-16 — batch the source reads.** `source_identities` reads every source
   event with its own `log.read` (85–90 % of the slow lists). Read the
   payloads and source keys of all events a call needs once — one query
   through a new `LogStore` method (protocol in `contract/store.py`, Postgres
   in `storage/postgres.py`, no SQL in core; recount the method list in the
   store.py docstring) or a per-call memo; pass identities into the CLI list
   and the MCP `assertions()`. Keep results identical (existing tests). Then
   **re-measure** with the controller's benchmark
   `/tmp/claude-1000/-home-jensens-ws-jwk-previously/b09c575a-1e77-447f-abd7-dad887b18049/scratchpad/bench.py`
   (+ `common.py` there; read them, run them, don't copy them into the repo):
   median of three, same rows as before (see `progress.md` "Messung"), and
   write the before/after figures, dated, with the CPU model, onto
   `docs/explanation/assertions.md` (section `assertions-folded`) and into the
   map's entries named in the docs review (and the `source_identities`
   docstring, the comment at `assertions.py` ~466).
5. **F-17 — approve only what is pending** (or stands as the winning
   proposal): a proposal a newer direct version overtook is refused by
   `write_statements`/`check_statements` (CLI and MCP alike) with its own
   sentence; rejecting it stays allowed. Test, mutate → red. Docs: the
   `approves` row of reference/assertions.md, explanation ~115, cli.md's
   `approve` exit-code row and refusal block (held by a test), mcp-tools.md if
   the tool description changes (then the tool-list checksum).
6. **F-18 — an all-erased entry answers "erased":** MCP `subject=N` on a
   thread whose versions are all erased (N is an erased assertion that was a
   first version, or a thread id with only erased versions) renders
   `[erased: previously://event/N]`; the CLI `obligation N`/`decision N`
   prints a sentence `obligation N is erased` (pick the wording; stderr, exit
   as today for "no … stands"). Lists keep not showing it. The MCP history
   shows rejections with their reason, as the CLI does. Tests both surfaces;
   cover read.py's history markers (`rejected`, `approved`, `approves N`, "no
   version stands" — the Minor 9 gaps). Docs: reference/assertions.md ~169,
   explanation ~153, mcp-tools.md (the erased sentence, the history
   sentence), cli.md (`obligation`/`decision` paragraph and exit-code row),
   and **the frozen spec header** — its departure "Ein Eintrag ohne stehende
   Fassung erscheint nicht als getilgt" becomes false: amend it to what the
   code now does.
7. **F-19:**
   - `check_statements` also runs the canonical check (as `_prepare` does),
     so the CLI never asks for what the write then refuses (test with a lone
     surrogate in `what`; mutate → red); cli.md's "What only the log knows…"
     names it.
   - `redact` (CLI) says, when its target was an approved proposal, that the
     approval keeps its words (one stderr line; pick the wording); document it
     in cli.md under `redact`, how-to/erase-something.md, reference
     "What an erasure takes", explanation ~118.
   - verify's docstring and the explanation's limits bullet name the F-5 limit:
     an approval naming any erased id is accepted.

## Docs (from the docs review)

8. **Important — the how-to's client settings**
   (`how-to/record-what-is-owed-and-decided.md` ~103–107): link the sources —
   `https://code.claude.com/docs/en/permissions#manage-permissions`,
   `https://code.claude.com/docs/en/permission-modes`, Vibe's MCP page — and
   say "from v2.1.283 on, as its documentation says" instead of "recent
   versions"; optionally name `_meta["anthropic/requiresUserInteraction"]` as
   the map does. Keep them marked unmeasured. linkcheck must pass.
9. Explanation ~183: "whose parties (debtor, creditor or deciders)".
10. How-to ~83: "it stays a proposal, out of every default list, until you
    approve it".
11. mcp-tools.md history example: complete it with the lines the code emits,
    or mark it an excerpt.
12. **The database privilege:** the write path takes `FOR NO KEY UPDATE` on
    source rows (`postgres.py` ~678), which needs UPDATE privilege on `event`
    for the role that writes assertions. Say so in the handoff (~44), and as a
    requirement on `environment.md`'s Database row (check what the row says
    about roles today). Verify the PostgreSQL rule against its documentation
    and say in the report whether you measured it.
13. **stdio and the key:** a stdio setup puts `PREVIOUSLY_MCP_CONFIRM_KEY` into
    the client's config (`claude mcp add … --env`). One how-to line for stdio,
    and a qualifier in environment.md's key row (with stdio the client starts
    the server and so holds the key; name the risk: low, a forged handle gains
    nothing a preview doesn't give).
14. "Rotating it … and nothing else" (explanation ~95, configuration.md row,
    handoff ~38): "makes every handle issued before it fail; nothing stored
    depends on it".
15. `assertions.py` ~439: rewrap so "ruling F-7 of the …" stays on one line.
16. `test_the_reference_quotes_the_findings_about_assertions`: name its
    prefix limit in the docstring.
17. Reference `handle` row: "the nonce of the MCP handle".

## Rules

- `CLAUDE.md` whole; `plone-doc-style:author` for pages under `docs/`; map and
  frozen-spec header German, the rest English; a comment is a claim.
- Every code fix: a test measured red under mutation, a green control.
- All six gates, `--cov` over the whole suite with `-rf`, and `pip-audit`:
  ```
  uv run ruff check .
  uv run ruff format --check .
  uv run pyright
  uv run lint-imports
  uv run pytest --cov --cov-report=term-missing
  make -C docs html && make -C docs vale && make -C docs linkcheck
  uv run pip-audit --skip-editable
  ```
- The tutorial's pytest block from ONE green `uv run pytest` run, last.
- Map: count before and after.
- Stage files by name; trailer `Assisted-By: Claude Opus 5.5
  <noreply@anthropic.com>`; no subagents; never read `~/.config/previously/`.
