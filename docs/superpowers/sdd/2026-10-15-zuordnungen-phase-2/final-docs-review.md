# Final docs review, phase 2 (docs diff 1aa8a36..22b3dec)

Docs: Approved

Counts: Critical 0, Important 0, Minor 6.

Measured: map count 242 (awk command of CLAUDE.md); `COMMANDS` in `cli.py` has 34 entries, as README.md:125 and cli.md:6 say; 10 tables in `schema.py`, as database-schema.md:5 and :10 say; 15 `.tool(` registrations, 9 reading + 6 writing, as mcp-tools.md:5-7 say; 10 base kinds in the table of vocabulary.md and 13 in `vocabulary.toml` with the three built-in ones; `pytest --collect-only` 2804, as the tutorial's `2804 passed` (record-your-first-event.md:292); the four tests named in projections.md exist. I did not run the docs gate (html, vale, linkcheck) because it writes to `docs/_build`.

## Reasons against code and rulings (check 1)

All hold. Verified against `core/members.py`, `core/graph_read.py`, `core/projection/graph.py`, `mcp_server/read.py` (`seen_members`, `objections_seen`), `mcp_server/server.py` (`bracket`) and `cli.py`:
- `concerns` is declared (`vocabulary.toml:49`), `bracket_kinds` names no kind, gate kinds are excluded (T2-a, T2-e).
- The start of an assignment is a source, added by CLI (`_relation_claim`) and MCP (`sources_with_start`), refused otherwise with `START_NOT_A_SOURCE` (P-1, T2-f).
- Only a direct or transitive unit edge replaces; an open one adds and takes nothing away (`_STANDS_FOR`, T2-c).
- Periods are ignored (T2-d). Over MCP only visible edges count (`seen_members`, T5-b, T5-c); the CLI walks every edge (`bracket_members`).
- Reader fallback with one warning (T4-b), `--check` (rows and version rows), vocabulary event touches nothing, write path and `verify` still fold.
- The edge case of one unit more for a client (graph.md:255-259) matches the `deciding_edges` docstring.

## Commands (check 2)

All option names and forms checked against `--help` output and the parsers: `relate --from-event EVENT[:SEQ,SEQ]`, `chronicle --within N`, `project --check`, `entity --recollection/--state/--history/--retract`, `relations --type/--from/--to/--at/--as-of`, `vocabulary apply --base`, `policy gaps`, `entities --type/--state/--proposals`. Typed output of `relations` (`event 1`, `event 1 #4`, `13 XZ`, `1 version`), chronicle lines, `Error: --within 99 is not an entity that stands`, `write? [y/N]`, `nothing to change`, the `graph  built:` / `up to date, up_to_id` lines, and the error sentences quoted in cli.md all match the code. The event ids of the how-to (assertions 13-19 after two mails and ten vocabulary events) are consistent.

## Handoff (check 3)

- Order migrate (`0006_graph`) -> `vocabulary apply --base` -> `project` is right and stated.
- Rolling update: correct. v0.1.0a7 declares `PROJECTIONS = (CHRONICLE, SOURCE_STATS)` and reads and writes `projection_state` by name only, so it neither rebuilds nor is rebuilt by `graph`. The statement that the exchange starts only with a later release that changes `GraphProjection.version` (now 1) is right.
- Compose host covered. No cdk8s; kup6s names ("tools pod", `previously-mcp`) only as in the earlier handoffs.

## Map (check 4) and README (4b)

- Count 242 = 233 + 9 new top-level points. New entries are German and each says what it is; the find-spots point carries "nicht vergessen, nichts verbauen" and Planentscheidung 12.
- README command list and "thirty-four" match `COMMANDS`.

## Findings

### Minor

1. landkarte.md:577 (struck event-start point, kept in *Offene Punkte* with the old wording). The header (line 8) says "streicht ihn hier und nennt den Commit"; every other closed point sits in *Erledigt* (line 1604 onward), and this is the only `- ~~` left among the open ones. The awk count of 242 therefore includes a closed point (241 without it). Move it to *Erledigt* with the commit names, or accept the in-place strike and leave the count. Also, the commits named there (`5f791e6`, `fbdd05e`, `a6d358a`) are branch commits and change if the merge squashes.
2. projections.md:348. "finding what belongs to a bracket for the operator folds no thread and reads nothing of the log but the vocabulary" holds for the `members` step, but `chronicle --within` also checks that the bracket stands (`bracket not in EntityTypes(graph)`, `cli.py:1587`), which folds that one thread, and `projected_graph` reads the approval classes. Say "the walk" and not the command, or add "beyond the bracket's own thread and the classes".
3. graph.md:71, projections.md:10, README.md:121 and the handoff (line 22) say the projection "holds no content" / "only ids, counts and words of the vocabulary". `p_graph_thread` holds the period dates of the winning relation; database-schema.md and projections.md say so correctly, the shorter statements omit it. Add "except period dates" at least in the handoff.
4. Handoff line 49: `caught up:` is printed only if events arrived after the reader built the projection; if a reader built it and nothing is new, `project` prints `up to date, up_to_id N` (`_describe`). Say "`up to date` or `caught up:`".
5. Handoff line 93 (compose) tells the reader to stop an old container before `project`, while line 59 says an a7 container causes no exchange. Harmless; tie it to "a container of an intermediate build".
6. vocabulary.md, new bullets on `event` and `*`: two sentences on one line each (one sentence per line).

No Critical or Important findings.
