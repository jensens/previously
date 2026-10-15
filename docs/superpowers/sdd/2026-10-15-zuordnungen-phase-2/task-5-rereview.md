# Task 5 re-review, fix round c205fea..08b1882 (rulings T5-b, T5-c)

Method: read the diff once; nothing re-run.
Line numbers are those of `review-c205fea..08b1882.diff`.

## Verdicts

- **I-1 / T5-c: ADDRESSED.**
  - `mcp_server/read.py` `seen_members` (diff ~760) walks all edges, takes `deciding_edges`, builds one `graph_view` over their subjects, and runs `members` over the deciding edges that `view.seen` lets through. `Service.bracket` uses it (server.py hunk ~880).
  - `core/members.py` `deciding_edges` (diff ~596) takes every hierarchy edge into `found.brackets` and every assignment whose event is in `found.events`. That includes a unit's own edges into brackets outside the walk (channel 3).
  - The property (tests/test_members.py, diff ~1245, 400 examples) compares against an independent oracle. `everywhere = members([e for e in edges if e.subject in seen], ...)` filters the raw edge list directly, and `deciding_edges` is used only on the `decided` side. The mask has 24 entries and the strategies cap at 10+10+4 = 24 edges, so no edge falls off the zip. Noise edges are included.
  - The fixed channel-3 test and mutations f2 and f3 (property red) show the property reads the right thing.
- **I-2: ADDRESSED.**
  - Tests (a) to (d) are in tests/test_mcp_server.py, diff ~960 to ~1075. Each has a `local-harness` control, and (c) has a same-client control as well. The report's mutation f1 takes all four red.
  - The inverted placeholder test (a) asserts the URI is absent under `within`, `access.withheld == ()`, and the placeholder present in the whole chronicle.
  - Pages: graph.md states the rule, the hidden part, the hidden bracket, the CLI difference and the "one more unit" case. mcp-tools.md, cli.md and projections.md follow. The `_CHRONICLE` description and `TOOLS_SHA256` are updated together.
- **M-1: ADDRESSED.**
  - An empty bracket reads no observation: `read.py` `chronicle` returns `Seen(())` when `_last_member` is `None`. The test asserts `scans == 0`.
  - The scan stops at the last member: `position >= last` returns. The test asserts 1 scan for the party and 3 for the control that is last in the log.
  - `contract/store.py` count: `grep -ohE 'log\.[a-z_]*\(' src/previously/mcp_server/*.py | sort -u` gives nine (begin, events_by_id, observations, read, read_by_kind, snapshot, source_keys, tip, units_by_event). The text now says nine and names `events_by_id` as the ninth.
- **M-2: ADDRESSED.** cli.md now says "refused before the chronicle is read, after the catch-up of the graph projection". The how-to says "the chronicle isn't read".
- **⚠️ 7: ADDRESSED.** `_read_of` returns `None` when a shown event has no unit content left under `within`, and the loop skips it before the page-size check. The test (diff ~1085) has a control in which the party shows the mail whole. Mutation f6 goes red.
- **⚠️ 6: ADDRESSED.** The test (diff ~1105) hands a `local-harness` cursor to `claude-code` and asserts the refusal. The control shows `local-harness` continues with that cursor.

## Channel check on `_last_member` and the early return

No new channel found.

- `_last_member` reads `within.events`, which is already the client's view (visible edges only). A hidden member is absent from it, so it cannot move `last`.
- A bracket with only hidden members and an empty bracket both give `within.events == {}`, then `last is None`, then the same `Seen(())` with zero scans. The answer and the scan count are identical.
- A cursor at or past `last` gives the same `Seen(())` as a visible empty page.
- Residual timing (not a new class, see out-of-scope): `seen_members` cost depends on the number of deciding edges, and the walk over all edges counts hidden ones. A hidden-only bracket therefore costs a `graph_view` read where a truly empty one returns at the `if not deciding` line. That is the same milliseconds-scale difference as ⚠️ 4.

## New Critical or Important issues in the fix diff

None.

## Out of scope (minor, not blocking)

- The timing note above: hidden-edge count influences the cost of `seen_members` and the early return. Same class as ⚠️ 4, already accepted. It could be mentioned beside that item.
- `_read_of` drops a shown event whose units all have `content is None` under `within`, while the whole chronicle would show its heading with an empty fence. This is consistent with `_texts` (line 273) and with ⚠️ 7's intent. It is cosmetic and releases nothing.
- `_last_member` reads the payloads of all member events per call. The report names this as the price of the bound. Not measured.
