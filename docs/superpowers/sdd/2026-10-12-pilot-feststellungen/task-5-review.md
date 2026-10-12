# Task 5 review: MCP write tools (base 90d431a, head 42a0a03)

Reviewer: Opus, adversarial, read-only. I ran these myself:
- the write tests, five times;
- `uv run pyright`;
- three probe files in the scratchpad, using the repo's fixtures and the real PostgreSQL testcontainer.

I did not run the full suite or the doc gates.

## Spec compliance

| Requirement | Verdict | Where |
|---|---|---|
| `write_assertion` always writes `model:<client>`, `open`. There is no field for `responsibility`, `author` or `approves` (`extra="forbid"`). | ✅ | server.py:1131-1190 (`_proposed`), :1186-1187 |
| `write_approve` copies the content, sources and author, sets `direct`, `approves=version.id` and `subject=thread.subject`. F-6 holds, because a model version is direct only as an approval. | ✅ | server.py:906-946 (:929) |
| `write_reject` is direct, by `model:<client>` (spec §6: "wie der Weg"), and takes the proposal's sources. | ✅ | server.py:948-983 (:968) |
| Visibility is checked against the client of **this** call, before `check_statements`. It covers every source, `subject` and `replaces`. For approve and reject it covers the thread over all standing versions plus the version's sources. | ✅ | server.py:878-897, :985-1009; read.py:445-466, :670-681 |
| Missing and withheld get one sentence (spec §6), with and without `confirm`. | ✅ | server.py:882, :888, :894, :1009; tests :2083, :2113, :2156 |
| The two steps, and the write runs after the snapshot closes. | ✅ | server.py:615-616, :1011-1060 |
| The handle: HMAC-SHA256 over the canonical `{client, digest, expires, nonce}`. The digest leaves out `handle`. Expiry is 600 s. The nonce comes from `secrets` on the server. | ✅ | confirm.py:111-128, :132-155; server.py:1042 |
| Confirming twice writes nothing and returns the same ids (Review Focus 4). | ✅ | tests :1971 |
| No key, or one under 32 characters, gives `Error: writing is not configured on this server`. The reading tools still work. | ✅ | confirm.py:79-84; server.py:851-854; test :2244 |
| Decision 10: a write's access entry holds only counts, ids, `confirm` and `written`, and this includes the SDK-refused safety net. | ✅ for the three tool names; ❌ for a misspelled writer name (I-2) | server.py:639-642, :1207-1245 |
| Spec §7: the access log names every assertion delivered, with its circles. | ❌ The approve and reject previews deliver a proposal's text and record `delivered=()` and `rules=[]` (I-3). | server.py:932-945, :978-982 |
| Your own principle that a preview is never cut, because what is not shown cannot be confirmed. | ❌ Lines are cut at 1,000 characters, but the full text is written (I-1). | server.py:1088-1094; render.py:64, :392 |

## Strengths

- **Visibility comes first and the sentences are uniform.**
  - `event_hidden` treats "no row" and "withheld" alike.
  - `thread_hidden(None)` is `True`, so a missing `subject` or `replaces` and a withheld one read the same. This also covers a `subject` that names a non-first version or a rejection.
  - `answerable` breaks on the first thread that holds the id and gives one sentence.
- **Erased events and non-observations pass through, and that is correct.** Probe: `plain` is withheld from claude-code.
  - Before the erasure, `write_assertion` answers `event 17 is not one this client can use as a source`.
  - After the erasure, `get_event` answers `[erased: previously://event/17]` and `write_assertion` answers `event 17 is erased and cannot be a source`.
  - `get_event` also names the kind of a non-observation to any client (read.py:422-427).
  - So the write path's sentences tell this client nothing that `get_event` doesn't.
- **The handle code is clean.**
  - The MAC is checked with `compare_digest` before any JSON is parsed.
  - Decoding is strict (`validate=True`). Every decode failure (non-ASCII, a lone surrogate, bad base64, bad JSON) becomes `HandleRefused`, and the tests cover each of them.
  - The body is checked for its keys and types even after the MAC passes.
- **The tool is bound implicitly, and a probe confirms it.** The payload sets of the three tools are disjoint:
  - `write_assertion` writes `open` with `approves=null`;
  - `write_approve` writes `direct` with `approves` set;
  - `write_reject` writes `assertion: rejection`.

  Probe: an approve handle presented to `write_reject` for the same proposal answers `the handle was sealed for other statements than these`.
- **Idempotence holds on a repeat.** The handle is opened before the checks, so a repeat confirm of an approval is not refused as "already approved".
- **The no-text test is strong.** It searches recursively, covers both a written proposal and a rejection with a reason, and includes an SDK-refused call that put text in `confirm`. Its control finds the private strings in the payloads.
- The count in `contract/store.py` is correct: the grep it quotes now names seven distinct methods.
- Pyright: 0 errors. The write tests ran green five times out of five (59 passed each run).

## Issues

### Important

**I-1. A preview cuts long lines, and confirming writes the uncut text, so an approval makes text direct that no MCP surface ever showed.**
- **Where:**
  - server.py:1088-1094 (`_preview`: "A preview is never cut");
  - render.py:64 and :392 (`_STATED_LINE_CHARS = 1_000`, `counter.line(line, _STATED_LINE_CHARS)`);
  - docs/reference/mcp-tools.md:367-368, which states both rules next to each other.
- **What:** `what` has no length limit in the form (assertion.py:353). The preview cuts each line at 1,000 characters with `…`, and the page check only refuses a preview longer than a page.
- **Why it matters:** this is the threat "a proposal becoming direct without an approval" in a weaker form.
  - A model, or an instruction injected into it, can propose an obligation whose text continues past character 1,000.
  - The person approving through `write_approve` sees the first 1,000 characters and a `…`.
  - The confirm writes a direct version with the full text.
  - The reading tools cut at the same place, so no MCP surface ever shows the tail.
- **Reproducer (probe):**
  1. `what = "a"*1500 + " HIDDEN-TAIL the operator owes everything"`, then `write_assertion`, then confirm.
  2. Result: `PREVIEW HAS TAIL: False`, `STORED HAS TAIL: True`. The `write_approve` preview by local-harness shows `HIDDEN-TAIL: False` and one `…`.
- **Fix:** in `staged`, refuse a batch in which any line of `shown` is longer than the limit. Make the limit public in render.py, for example `STATED_LINE_CHARS`. Use one fixed sentence, such as `a line of these statements is longer than a preview shows; shorten it`. That covers all three tools.
  - Alternatively, cap `what`, `reason` and `name:` in the form at 1,000 characters, but that is a decision for the spec.
  - Test with 1,001 characters (refused) and a 1,000-character control (previewed).
  - Fix the docs line :367 to match.

**I-2. A misspelled writer name lands its text in `mcp_access`.**
- **Where:** server.py:639-642 (`net`). Only names in `WRITERS` go through `write_record`. Any other unknown tool name keeps its arguments as given, through `recordable` with up to 1,000 characters per string.
- **Why it matters:**
  - Decision 10 exists so that text a client derived from a mail does not outlive the mail's erasure in the access log.
  - A model that calls `write_assertions`, `write_obligation` or `write_approval` with its items is a realistic slip.
  - Its text then stands in `mcp_access` permanently.
- **Reproducer (probe):** `call_tool("write_assertions", {"items": [_item(scanned, what=PRIVATE_TEXT)]})` answers `Error: write_assertions did not run: Unknown tool: write_assertions`. Then `any(PRIVATE_TEXT in s for s in strings(mcp_access payloads))` returns `True`.
- **Fix:** in `net`, when the tool name is not one the server has, record no argument values. For example, record `{"keys": sorted(arguments)[:50]}`, or `write_record`'s shape for any name that starts with `write_`. The first is simpler and closes the class.
  - Test: an unknown name with private text gives no hit.
  - Control: a known reading tool's SDK-refused arguments are still recorded.
  - A related point, not a defect of this task: a known reading tool records free text a client puts in a filter. The probe showed `list_obligations` with `state=PRIVATE_TEXT` recorded. That is client-chosen input, not mail-derived, so I leave it.

**I-3. The approve and reject previews deliver a proposal's content, but the access entry records no `delivered` and no rules (spec §7).**
- **Where:** server.py:932-945 and :978-982. `Answer(..., written=())` leaves `delivered=()` and `rules=()`.
- **Why it matters:**
  - A `write_approve` or `write_reject` preview shows `what`, the debtor or creditor (addresses among them) and the reason of a proposal, often one by another client.
  - `previously access --circle office` and the delivered column (cli.md:1090-1094) miss that delivery.
  - The ids do sit in `arguments.proposals`, but without circles, and `--circle` filters on delivered and withheld.
- **Reproducer (probe):** a `write_approve` preview of a proposal on `attachments_only` records `DELIVERED: ()` and `{'rules': []}`. The same entry through `list_obligations(proposals=True)` records `Delivered(event=25, circles=('office',))` and `rules: [13]`.
- **Fix:** have `answerable` return the decisions it already computes in `thread_hidden` (`assertion_decisions`). Build `Delivered(thread.subject, (), decisions[-1].circles)` and the rule ids the way `_entry` does (read.py:~664). Carry them in the preview Answer and the confirm Answer.
  - Test: an approve preview names the thread in `delivered`, with circles.
  - Control: a `write_assertion` preview without `subject` records `delivered=[]`.
- If the controller weighs this down: the ids are recoverable from `proposals`, so it would be Minor. But the spec sentence is explicit.

### Minor

- **M-1. A stale count.** docs/reference/configuration.md:5 still says "nineteen environment variables". The table now has twenty: `grep -oE '^\| \`[A-Z_]+\`' docs/reference/configuration.md | sort -u | wc -l` returns 20. CLAUDE.md treats a number in a doc as a claim.
- **M-2. A sentence too broad.** docs/reference/mcp-tools.md:418 says "Each concerns an event or an entry the client may see." That is not true for an erased event or a non-observation, which `event_hidden` deliberately passes through. Suggested wording: "…the client may see, or an event that `get_event` names to any client: an erased one, or one that is no observation."
- **M-3. The explanation pages overclaim.**
  - docs/explanation/mcp-interface.md:88 says "the three that write can't do what a person stated". But `write_approve` and `write_reject` do write direct versions that the operator stands for. What protects them is the client asking the person, which the server cannot enforce.
  - docs/explanation/trust-boundaries.md:101 says "an answer to one that its user confirmed", which states the demand of spec §6 as a fact.
  - Say it the way mcp-tools.md:463 does: they count as the operator's only if the client asks, and a client that allows them automatically writes approvals nobody looked at. Task 6 writes the how-to, but these two sentences changed in this diff.
- **M-4. The `$defs`/`$ref` schema has not been measured (concern 2).**
  - The `items` input schema uses `$defs` (`SourceItem`, `StatementItem`) and `$ref`; I confirmed this with `TypeAdapter(list[StatementItem]).json_schema()`.
  - The research says local `$ref` is valid 2020-12 and spec-conformant (recherche/2026-10-09-mcp-notizen/spec_state.md:170-184). Claude Code requires the schema to validate against the 2020-12 meta-schema, which a local `$ref` does (clients.md:184).
  - Nothing measured either client with a nested schema: the 2026-10-10 measurements only cover flat tools. Vibe speaks 2025-11-25 and passes schemas on to Mistral function calling, where `$ref` support is unknown.
  - Recommendation: do not flatten blindly. Before merge, measure one `write_assertion` preview with each client, using the 2026-10-10 probe setup. Flatten only if one of them fails, by inlining the definitions; it costs a checksum change.
  - While the schema is open: `kind: Literal["obligation", "decision"]` would give models an enum, and `sources` could carry `min_length=1`.
- **M-5. The CLI wiring of the key is untested.** Dropping `confirm_key=os.environ.get(KEY_VARIABLE)` from cli.py:2878 or :2919 leaves every test green, because no test starts `mcp` or `serve` past their input errors. It fails safe (writing is refused), hence Minor.
- **M-6. The branch "erased between check and write" is untested (concern 3).**
  - Where: server.py:1053-1056.
  - It is reachable without threads: a test can pass `build_server(..., locker=…)` a `PostgresStorage` subclass whose first `lock_event` runs `redact_event` on its own connection and then calls `super().lock_event`.
  - Expected: the write path refuses, the answer is `Error: event N is erased…`, nothing is written, and the access entry shows outcome `error` with `written: []`.
- **M-7. The approving client is not recorded in the payload (concern 4).** That is by spec §3.3: the author stays the proposal's. The `mcp_access` entry of the confirm call holds `client` and `written`, so the question "who approved X" is answerable from the log. Say so in the reference (Task 6) rather than adding a field.
- **M-8. A docstring overclaims.** The `open_handle` docstring (confirm.py:168) says "Every comparison is `hmac.compare_digest`", but the expiry comparison at :178 is a plain integer comparison. That is correct, but the sentence should say "every comparison of a value from the handle".
- **M-9. The count in an error.** `approval_write` (server.py:917-918) limits the unique ids and reports `len(ids)`. With 22 ids of which 21 are unique, it says "gave 22"; 25 ids of which 20 are unique pass. This is a nit; report `len(unique)` or say "different".

### Notes (no action)

- **Self-approval is possible and allowed by spec §6.** Probe: claude-code proposes through `write_assertion`, then approves with `write_approve`, and the result is a direct version with `author: model:claude-code` and `approves` set. This relies entirely on the client not allowing `write_approve` automatically (Task 6 how-to).
- **The handle checks hold.**
  - Constant-time MAC: yes.
  - Bound to client and content: yes. Bound to the tool: implicitly, as shown above.
  - Expiry: yes; at exactly 600 s a handle still holds, and at 601 s it is refused.
  - The nonce: drawn on the server by `secrets.token_urlsafe(16)`. A client cannot choose it without the key.
  - Every decode failure is a `HandleRefused`.
- **Flakiness (concern 1).** No new test depends on the wall clock in a way that can fail:
  - The expired-handle test seals at `now - 660 s` and its control at `now`.
  - The preview's `expires` is not compared.
  - The dates used are `2099-01-01`, `FAR_FUTURE` and `LONG_AGO`.
  - Task 3's CLI tests that compute `today` themselves (test_cli.py:5258, :5753) keep their verdict across a UTC midnight rollover, and they assert the test's own dates.

  Plausible sources of the unnamed failure:
  - (a) `test_the_winner_is_the_latest_direct_else_the_latest_unanswered_open` (test_assertion.py:709, Task 1) runs `@given` with Hypothesis's default 200 ms deadline. No profile disables it, and under `--cov` a slow example can raise `FlakyFailure`.
  - (b) An order dependency under pytest-randomly. The failing run printed `Using --randomly-seed=N`, and if that seed is still in the log, rerunning with it reproduces the failure.
  - (c) Older and cluster-wide: test_cascade.py:340-345 counts lock waits across all of `pg_stat_activity`.

  I could not confirm any of them under my read-only constraint. The cheapest guard is `@settings(deadline=None)` on (a).

## Assessment

**Needs fixes.**

I-1 and I-2 each break a named threat:
- I-1 lets text become direct without being shown, a weak form of "a proposal becoming direct without an approval".
- I-2 lets text reach `mcp_access`.

Both fixes are small and local to server.py. I-3 is a spec §7 gap with a contained fix. All three fit in one fix round, together with M-1 to M-3 and, if wanted, M-6. Measure M-4 before merge.
