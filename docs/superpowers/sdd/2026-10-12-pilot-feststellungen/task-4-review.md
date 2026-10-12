# Review Task 4: list_obligations / list_decisions (0d825c5..90d431a)

Run: the permitted pytest selection 45 passed; pyright on mcp_server and core/assertions.py 0 errors. No full suite run (per rules).

## Spec compliance
- Policy over sources only, decision per distinct source, strictest wins: OK (assertions.py `assertion_decisions`/`assertion_verdict`; read.py `_entry` takes `source_identities`, never actors). Identities come from every version in `thread.versions` (assertions.py `source_identities`), so pending proposals count (risk 3: OK).
- Withheld entry: `WithheldMark(uri, reason)` only; reason from `withholding` (policy names), read.py `_entry`. OK.
- Filter over sources and actors for shown entries (`thread_circles`), sources only for withheld (`_entry`, `decision.circles`). OK per spec §3.5.
- Fence: heading `### uri · kind · label` outside, label built from state, overdue mark, `responsibility` (validated against RESPONSIBILITIES), counts; `due`, `on`, `what`, actors, reason, sources, history lines with author all inside (`_statement_lines`, `_history_lines`, render.py `_stated_block`), every line through `counter.line` (sanitize + one line + 1000 cap). OK (risk 4).
- Access log: `_given(...)` records only circle name (policy-validated), state (validated), flags, int subject, cursor; no text, no address (server.py). Delivered/Withheld carry the subject id and circles; rules are the union over all decisions (read.py `_entry`). OK (risk 1).
- Error lines: "no {kind} stands under this id" with the uri; other-kind subject and nonexistent subject give the identical error; withheld subject gives the placeholder. No content in any path.
- Cursor carries `kind` in `filters` (server.py `assertion_page`) and is refused across tools. OK.
- Paging (risk 5): `assertions` stops at the first read after `size > PAGE_CHARS` and sets `more`; render_page cuts at entry boundaries and takes the cursor from the last consumed block (`cursor_for` = id of that read); ids ascend, so no gap, no duplicate. A single entry over the page is cut at a line boundary with an honest count note. OK.
- Docs (risk 6): mcp-tools.md matches the code (heading, label, arguments, errors, truncation note, cursor, rules). INSTRUCTIONS "A tool that shows events, obligations or decisions only reads" stays true after Task 5 because it is scoped to show-tools; but see Minor 3.

Verdict: spec compliant.

## Strengths
- `assertion_decisions` returning all decisions makes the log's rules complete; verdict is a thin fold over it.
- Policy and filter separation is explicit and commented, with tests for "actor of another circle changes nothing" and "placeholder never found by an actor".
- Subject path drops the circle filter for the entry (no circle probing through subject).
- Truncation is deterministic and counted; the tag skips tags occurring in lines (test).

## Issues
### Critical
None.

### Important
None.

### Minor
1. read.py `_entry` (blocked branch), judgment of decision 2: `circle=X` on a withheld entry matches `decision.circles`, which holds every circle of the source participants, while the placeholder reason names only circles without a rule (or the rule scopes). A client can thus learn that a participant of a withheld source belongs to a circle that has a rule. Same exposure as the existing chronicle filter and circle names are visible via `list_circles`, so I accept it as the design of spec §3.5; worth one sentence in mcp-tools.md ("found by the circles of its sources", already there) stating that this reveals source circle membership. Not a blocker.
2. server.py `assertion_page` / read.py `assertions`: with `subject` + `history`, `cursor` is ignored and `more` is never set, so the history of one entry longer than a page (about 60 versions of a few lines) is cut and the rest is unreachable; the note says lines are not shown but gives no way to get them. Realistic only for very long histories. Fix: either document the limit in mcp-tools.md, or page history by version.
3. server.py INSTRUCTIONS: after Task 5 adds write tools, "A tool that shows ... only reads" is true but invites the reading that other tools write; Task 5 should rewrite the sentence (and "seven tools" in the module docstring and mcp-tools.md) rather than rely on this wording.
4. server.py cursor `filters` omit `history` (and `subject`, ignored with cursor): a cursor made with history=true can be replayed with history=false. Harmless (ids only), mention only.
5. A `subject` whose thread has no winner gives the error without history even if a policy-blocked entry; reveals nothing placeholder-worthy beyond "stands", acceptable.

## Assessment
Approved (Minor points only; 1 and 3 are for the docs/Task 5).
