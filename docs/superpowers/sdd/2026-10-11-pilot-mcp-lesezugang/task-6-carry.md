# What Task 6 has to carry (collected by the controller from Tasks 1–5)

Every item below came out of an implementation or a review and has a home in
Task 6. Nothing here is optional; each line names where it goes.

## Named limits — explanation page `mcp-interface.md` (and, where marked, the map)

1. **The fence is a bet, not a boundary** (K §6, R §5.4). Inside it a mail can
   forge a `#unit-<n>` marker; the effect is a misleading citation inside text
   that is untrusted anyway. Named, not fixed (Task 4).
2. **Display names stand outside the fence**, in the heading, because the
   spec puts them there. They are sanitized, stripped of line breaks, capped
   at 200 characters per field and 10 recipients (`+N more`). Roughly 2.2k
   characters per event of possibly mail-supplied names sit outside the fence.
3. **A single unit larger than a page** is cut; the rest of that unit is not
   served in the pilot (ruling R-5). → map: serve the rest (e.g. `from_char`).
4. **The order of placeholders** between visible events narrows when a withheld
   event happened; the cursor no longer carries its time (ruling R-13).
5. **stdio: written, never sent.** A call still running when stdin closes
   writes its `mcp_access`, but the answer never reaches the client; the log
   then names a delivery the client did not receive (ruling R-12). The
   opposite case — answer sent, log not written — is the named limit of S §7.
6. **No read bound per call.** The chronicle reads in batches of 200 rows
   with no limit per call; a circle matching few events reads the whole log
   (S §13 point 1). → map.
7. **`PAGE_CHARS = 60_000` is not measured against real mail** (S §13 point 2).
   → map, due at acceptance 9.
8. **A 401 without a valid token writes no `mcp_access`**: there is no
   principal to write it for. A known client no longer in force is logged
   with outcome `error` (ruling R-12).
9. **The SDK middleware** that logs calls the SDK refuses before a handler
   runs uses an API the SDK marks provisional. → map: watch on `mcp` upgrades.
10. **What the sanitizer removes** on output (stored bytes unchanged, verify
    green): C0/C1 except `\n` `\t`, ESC and 8-bit CSI/OSC sequences, category
    `Cf`, the tag block U+E0000–E007F, variation selectors U+FE00–FE0F and
    U+E0100–E01EF (together the 256-value smuggling channel), U+034F, the
    Hangul fillers U+115F, U+1160, U+3164, U+FFA0, lone surrogates; U+2028/9
    are flattened in heading lines. Emoji lose their presentation selector —
    accepted (ruling R-6). Check against `render.py` before writing.

## How-to `connect-claude-code-and-vibe.md`

- A **local** provider must be declared with `--training no
  --subprocessors none`, or the new restrictions withhold everything from it
  (deferred from Task 2).
- Vibe needs `headers`, not `api_key_env` (measured 2026-10-10).
- Vibe's unified harness caches the tool list; after a server upgrade new tools
  are invisible until the cache is refreshed or `--legacy-harness` is used.
- The dated list of tested configurations: Claude Code 2.1.289 (2026-07-28),
  Vibe 2.26.1 (2025-11-25), measured 2026-10-10 — see
  `docs/superpowers/recherche/2026-10-10-mcp-messungen.md`.

## Reference `mcp-tools.md`

- The resource template is `previously://event/{event_id}` (ruling R-11), not
  `{id}` as the spec writes it; concrete URIs are `previously://event/<n>`.
- The cursor carries the id of the last consumed item and the filters; the
  server looks up the time (ruling R-13). It is not sealed; it grants nothing.
- `/.well-known/oauth-protected-resource`: 401 without a token, 404 with one.
- The `mcp_access` payload, field by field, as `core/access.py` checks it
  (`era` required, null allowed; `circles` required on each delivered entry).
- Every quoted message must be real; `tests/test_docs_references.py` holds
  them against the code.

## Code comments

- Comments in `src/` and `tests/` that cite "unit specification, section N" or
  "concept, section N": once both specs freeze, a reason that explains today's
  code names a page (`` {ref}`label` ``); a statement about what was decided
  when keeps the paragraph and carries `(frozen design record)` on the same
  line (CLAUDE.md, "Citing a reason from code"). Every newly cited paragraph
  enters the table in `docs/explanation/design-records.md`.
- Ruling citations read `ruling R-<n> of the 2026-10-11 MCP read access plan`.
  The ledger ships after Task 6, under
  `docs/superpowers/sdd/2026-10-11-pilot-mcp-lesezugang/` — the controller
  moves it; Task 6 does not.
- Deferred from Task 2: the docstring of a test in `tests/test_clients.py`
  names `hmac.compare_digest`, a path it does not touch. Correct it.

## Map `docs/superpowers/landkarte.md`

Count with the command in CLAUDE.md before and after, and report both.
Unit 4 built (not accepted — the merge is the acceptance). New open points,
each under its unit:

- the project idea for unit 5, **with its counter-thesis**: projects as
  set algebra over identities, perhaps a circle of circles — or a project is
  more than its members (a goal, a period);
- "Vibe on `mcp` 2.x": Vibe speaks 2025-11-25 today;
- the volume of `mcp_access` (one action per call);
- items 3, 6, 7, 9 above;
- the open points of K §10 and S §13 not already covered.

## Handoff `docs/superpowers/handoffs/2026-10-11-kup6s-mcp.md` (English)

One handoff together with the held-back gate handoff
(`2026-10-09-kup6s-gate.md`) and the local model server: release
`v0.1.0a3`; deployment `previously-mcp` running `previously serve`, a
service, one replica, readiness via `server/discover`; access stage A
(`kubectl port-forward`) and A2 (Tailscale/Headscale, worked out by the agent
there, `PREVIOUSLY_MCP_ALLOWED_HOSTS`); client tokens created by the
maintainer in the tools pod. Never a token in the handoff.
