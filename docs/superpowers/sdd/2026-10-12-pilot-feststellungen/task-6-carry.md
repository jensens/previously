# What Task 6 has to carry (collected by the controller from Tasks 1–5)

Every item has a home in Task 6. Check each technical claim against the code
before writing it; where the code disagrees, the code wins and the report
says so. Rulings F-1 to F-14 are in `progress.md` (German).

## Explanation page `docs/explanation/assertions.md` (new)

The reasons, each a section:

1. **Complete versions, not changes** (spec §3.1): precedence would otherwise
   assemble fields from different levels of responsibility; the change is
   computed when reading; `reason` is the one thing that can't be derived.
2. **Author and responsibility are two questions**; precedence follows
   responsibility: direct beats open, the newest within a level wins; a
   proposal never outranks a direct version, however new (spec §3.2).
3. **MCP only proposes** (spec §6): the server can't know that a person read a
   single item, and the second call of the two-step confirmation is a model's
   call too. An approval or rejection over MCP counts as the operator's only
   because the client asks the person — a requirement on the environment
   (`CLAUDE.md`, "Previously demands, the environment provides"), with the risk
   named: a client that auto-allows `write_approve`/`write_reject` approves
   without a look. Ruling F-6: a version by `model:` is direct only as an
   approval, a form rule, so `verify` reports any other.
4. **Approval is making a proposal one's own**: a new version with the
   proposal's content, sources and author, `responsibility: direct`. The
   approving client is recorded in `mcp_access` (`client`, `written`), not in
   the assertion — by design (spec §3.3). An approval stands even if its
   proposal is erased on its own (F-5).
5. **Rejection is its own sub-kind**, naming the proposal; it takes the
   proposal's sources so it goes with them (spec §3.4).
6. **Erasure cascades** (spec §8): whole event, a cited unit, or — for a source
   cited whole (`units: null`) — a unit erasure *after* the assertion was
   written (a unit already gone when it was written isn't what it rests on).
   Over-erasure is the safe direction. A blob erasure and a model call don't
   cascade (F-8): an assertion names no blob, a model call is no source.
   Sources must be observations. A thread lives as long as one version stands,
   and keeps its id when its first version is erased (F-2).
7. **Mentioned is not involved** (spec §7): policy runs over sources only, the
   circle filter over sources and actors. A withheld entry is found by the
   filter through its sources only, never through an actor — otherwise the
   filter would reveal which circle a party belongs to. Named limit: the filter
   on a withheld entry does show that a participant of its sources is in a
   circle that has a rule, as the chronicle does.
8. **`name:` is a label, not an identity**: two `name:` references never count
   as the same actor; a name is made precise by a new version of the one
   obligation; with the identity graph the system will ask back which person
   is meant (spec §2.1, §15).
9. **Folded, not projected** (plan decision 1, confirmed by the maintainer
   2026-10-12: "schauen wir mal, ob wir ohne Projektionstabellen auskommen"):
   the fallback after an erasure needs every version anyway; circles depend on
   today's policy; the MCP server reads only the log. The final review measures
   reading at 5 000 assertions — its figure goes here, dated.
10. **Named limits:**
    - Replaying a confirmation whose assertions were since erased writes them
      again (F-7) — the operator erased them, a handle lives ten minutes.
    - `verify` can tell an erased non-thread assertion from an erased first
      version only when an approval named it under another subject.
    - A history longer than one page isn't reachable over MCP beyond the cut.
    - Over MCP, every text line of a statement is at most 1 000 characters
      (F-12), so a preview always shows what will be written; the command line
      has no such limit.
    - The approving client appears only in the access log.

## Reference `docs/reference/assertions.md` (new)

The payload per sub-kind as `core/assertion.py` checks it (all fields, with
types), the reference grammar (`own`, `circle:<non-blank>`, `address:` with
one `@`, no blanks, ≤ 254, `name:` 1–200 without control characters), the
states, "overdue" (open, `due` before the UTC date). `docs/reference/cli.md`
and `mcp-tools.md` already hold the commands and tools — link, don't repeat.

## How-to `docs/how-to/record-what-is-owed-and-decided.md` (new)

Record an obligation and a decision on the command line; let Claude Code
propose from a customer's mails and go through the proposals (`obligations
--proposals`, `approve`, `reject`); ask what is open and overdue; set up the
client so that `write_approve` and `write_reject` always ask (Claude Code's
permission settings — check its docs, mark unmeasured parts as such).

## `environment.md`, `configuration.md`, `connect-claude-code-and-vibe.md`

- `environment.md`: `PREVIOUSLY_MCP_CONFIRM_KEY` reaches only the MCP server,
  not the tools pod; the client asks the person before `write_approve` and
  `write_reject` — requirement with risk.
- The connect how-to: the tool list grew from 5 to 10 — Vibe's cached list
  needs refreshing (the page already says how); the measurement still owed:
  one real `write_assertion` call per client, because its input schema nests
  (`$defs`/`$ref`) and only the SDK's client has been tried.

## Handoff `docs/superpowers/handoffs/2026-10-12-kup6s-assertions.md` (English)

For the release after `v0.1.0a4`: no migration; a new secret
`PREVIOUSLY_MCP_CONFIRM_KEY` (≥ 32 characters) for `previously-mcp` only;
without it the server reads but doesn't write; the requirement on the client;
and the note from PR #16: the ingest's stdout line now ends in ` in <folder>`
and a folder's error starts with `Error: folder <name>:` — only matters if
log alerting matches on either. Never a token or key in the handoff.

## Map `docs/superpowers/landkarte.md`

Count before and after. Unit 5 built (not accepted). Strike, with the commit:
"ein zweiter Schreibweg neben `append` für `assertion`", "`verify` prüft …
eine Feststellung ohne `sources` besteht", "`p_obligation` braucht
`responsibility`". The open points of spec §15 under their units. New:
- a projection for assertions, only if the measurement asks for it;
- `cli.py` has about 3 000 lines;
- one real `write_assertion` call per client (nested schema) — at acceptance;
- the long-history limit over MCP;
- parked from the reviews: the Hypothesis property doesn't erase the first
  version (F-2 is covered by three example tests); a dead branch in
  `tests/test_assertion.py` around the property; the status sentence
  `no obligation stands under event ID` is outside the quotation test; the
  deferred-write refusal branch in `server.py` is untested (it would need a
  stand-in for the database); `_cmd_decisions` sets list filters on `args`.

## Freezing the spec

Header like the other frozen specs, with the departures of the build: no
projection tables and no migration (plan decision 1); the handle form (plan
decision 9); `MAX_STATEMENTS = 20`; the 1 000-character line limit over MCP
(F-12); a version by a model is direct only as an approval (F-6); sources must
be observations; the fixed sentence for missing and hidden sources. "Was offen
bleibt" in the past tense; its points go to the map. `design-records.md` gets
any newly cited paragraphs.
