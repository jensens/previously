# Final review, documentation package, with Task 6's own review

Reviewer: Opus, read-only. Worktree `worktree-mcp-konzept` at `2e71dc3`, range `c90fb40..2e71dc3`.
Yardstick: CLAUDE.md, the Task 6 brief, `task-6-carry.md`, rulings R-1 to R-15, and the code. Every claim was checked against the code, not against the specs.

## What I ran

```
make -C docs html                     build succeeded (warnings are errors)
make -C docs vale                     0 errors, 0 warnings and 0 suggestions in 41 files
make -C docs linkcheck                build succeeded; _build/linkcheck/output.txt empty
uv run pytest tests/test_docs_references.py tests/test_docs_typed_output.py -q -p no:randomly
                                      22 passed
awk '/^## Offene Punkte/{f=1} /^## Erledigt/{f=0} f && /^- /{n++} END{print n}' docs/superpowers/landkarte.md
                                      200 (185 at c90fb40)
git log --merges --oneline main       d75c4b3 "Merge pull request #9 from jensens/worktree-pilot-gate" (unit 3)
grep -rn "§" src tests | grep -v "frozen design record"      (nothing)
grep -rnioE 'ruling (P|T[0-9]+|R)-[a-z0-9]+' src tests pyproject.toml .importlinter
awk 'NF' / awk 'NF && /^[a-z]/' .vale-styles/config/vocabularies/Previously/accept.txt   24 / 16
uv run previously --help              18 subcommands, client/access/mcp/serve among them
```

I also ran one in-memory probe, with no file changed: I imported the helpers of `tests/test_docs_references.py` and fed `_is_the_same_sentence` altered quotations (finding I-2).
I read the SDK's `mcp/shared/inbound.py` (the modern-route ladder) and `mcp/server/transport_security.py` (421/403) for the handoff.
I did not run the code gates, which belong to the other package.

## Carry list

| Item | Where it landed | |
|---|---|---|
| 1. Fence a bet, forgeable `#unit-<n>` | `mcp-interface.md` `mcp-fence`, l. 83–90; matches `render.py` `_shown_block` (`#unit-{seq}` inside the fence) | ✅ |
| 2. Display names outside the fence, 200 chars, 10 recipients, `+N more`, about 2.2k | `mcp-interface.md` l. 91–92, `trust-boundaries.md` l. 146–147, `mcp-tools.md` l. 63–64; `_FIELD_CHARS`, `_MAX_RECIPIENTS`, `_heading`; 11 × 200 = 2,200 | ✅ |
| 3. Unit over a page, rest not served (R-5), map `from_char` | `mcp-interface.md` l. 172–173; `mcp-tools.md` l. 95–106; map entry | ✅ |
| 4. Order of placeholders, cursor without time (R-13) | `mcp-interface.md` l. 178–179; `mcp-tools.md` l. 175; `encode_cursor` writes `after`, `filters`, `page` only | ✅ |
| 5. stdio written, never sent (R-12); the S §7 opposite | `mcp-interface.md` l. 180–182, `trust-boundaries.md` l. 149–151, map l. 699 | ❌ The first half is right but scoped too narrowly; the opposite case doesn't exist in this code (I-1) |
| 6. No read bound per call, batches of 200 | `mcp-interface.md` l. 176–177; map; `BATCH = 200` and the loop in `chronicle` | ✅ |
| 7. `PAGE_CHARS` not measured | `mcp-interface.md` l. 174–175; map, due with condition 9; `render.py` comment | ✅ |
| 8. 401 without token writes no entry; known client not in force → `error` | `mcp-interface.md` l. 120–122; `mcp-tools.md` l. 326; `auth.py` docstring | ✅ The implementer's qualification is right: over HTTP, `resolve` only finds clients in force, so a revoked token gets 401 and no entry. The `error` entry happens on stdio, where the client is fixed at start, or in the race between wrapper and handler (`Service.answer` reads the policy again). |
| 9. Provisional SDK middleware | `mcp-interface.md` l. 183; map entry quoting "Provisional - the signature may change…" | ✅ |
| 10. Sanitizer list | `mcp-tools.md` l. 143–157; reasons in `mcp-interface.md` l. 94–103 | ✅ The implementer's correction is right: `\r` is in `_LINE_BREAKS`, but `_Counter.line` sanitizes first, so it is removed as `Cc`. The page lists the 8-bit DCS/SOS/PM/APC forms (U+0090, U+0098, U+009E, U+009F), matching `_ESCAPE_SEQUENCE`. |
| How-to: local provider `--training no --subprocessors none` | how-to l. 33–34; `mcp-interface.md` l. 37; `processing-policy.md` | ✅ The carry overstated this, and the page follows the code: without a rule, `local_only` admits a local provider whatever it declared (`decide.py` l. 201). Only `no_training`/`no_subprocessors` reject an undeclared value (l. 160–169). |
| How-to: Vibe `headers`, not `api_key_env` | how-to l. 102–113 | ✅ Matches M3 ("returned nothing I can see", five times 401) |
| How-to: Vibe harness caches the tool list; `--legacy-harness` | how-to l. 115–116, 147 | ✅ (see M-8 on "until") |
| How-to: dated tested configurations | how-to l. 141–151 | ✅ Measured 2026-10-10, on `mcp` 2.3.0, against the throwaway server and not `previously serve`; the unmeasured parts (stdio, the Vibe keys besides `headers`) are labeled |
| Reference: `{event_id}` (R-11) | `mcp-tools.md` l. 289–295; `EVENT_TEMPLATE` | ✅ |
| Reference: cursor = id + filters (+ page), not sealed | `mcp-tools.md` l. 175–176; the example cursor decodes to `{"after":44,"filters":{"circle":"huber","since":"2026-09-01"},"page":2}` | ✅ |
| Reference: PRM 401/404 | `cli.md` l. 1098–1108, linked from `mcp-tools.md` l. 8 | ✅ |
| Reference: `mcp_access` field by field, `era` required with null, `circles` on each delivered entry | `mcp-tools.md` l. 321–378; `access_problem`, `_payload` | ✅ (two small inaccuracies, M-3 and M-4) |
| Reference: every quotation real, held by `test_docs_references` | five new tests | ✅ They pass, but parts of the quotes are barely held (I-2) |
| Code comments: `{ref}` for today, `(frozen design record)` for when | `7896b56`; census below | ✅ |
| Ruling citations `ruling R-<n> of the 2026-10-11 MCP read access plan` | all R-citations in `src`/`tests` | ✅ (`auth.py` l. 13: "ruling R-10 of the same plan", nit M-11) |
| Deferred docstring (`hmac.compare_digest`) | `tests/test_policy.py` l. 533–538, not `test_clients.py` | ✅ The implementer was right about the file |
| Map: unit 4 built, not accepted; counts before and after | map l. 31–33 "noch nicht gemergt"; 185 → 200 | ✅ |
| Map: projects with counter-thesis under unit 5 | map, *Feststellungen und Entitäten* | ✅ |
| Map: Vibe on `mcp` 2.x; `mcp_access` volume; items 3, 6, 7, 9; rest of K §10 and S §13 | map *MCP-Lesezugang (Pilot, Einheit 4)*: K §10 points 1–8 and S §13 points 1–2 all present | ✅ |
| Handoff: release, deployment, Service, one replica, `server/discover`, A/A2, tokens in the tools pod, no token, together with gate and model server | `handoffs/2026-10-11-kup6s-mcp.md` | ✅ (M-1, M-2) |

## Strengths

- **The four contradictions are real, and in every case the pages follow the code.** I re-derived each one: the 401/`error` split, `\r`, the local provider, and the docstring's file.
- **The reference page is precise.** I checked more than 30 sentences against `render.py`, `read.py`, `server.py` and `access.py`. They cover:
  - header composition (`_Frame.header`, `render_text`);
  - the heading and its caps;
  - the `get_event` lines (`_attachments`, `_provenance`);
  - placeholders and the 500-character cap;
  - the three cut notes, the two footers and `No results.`;
  - every tool's arguments and title;
  - the four id errors and the call errors;
  - the `list_circles` and `whoami` line forms (`rule_line`, `chain_line`);
  - the `policy_gaps` origin values (`gaps.py`);
  - the templates and the resource-id refusal;
  - both prompt texts and `_said`'s 1,000-character cut;
  - the `recordable` limits (1,000 / 50 / depth 4 / `KEY_PATTERN` `^[a-z][a-z0-9_]*$`);
  - the erased-event entry with no units and no circles.

  All of them hold, apart from the four minor points below.
- **The example page is regenerated by a test** character for character, the cursor included. This is the strongest kind of hold a reference page can have.
- **The M4 table is honest about what wasn't measured.** It says "Not measured" where the measurement has a dash, rather than extrapolating (but see I-3).
- **The readiness section of the handoff was measured and is right about the SDK.**
  - `classify_inbound_request` requires the `_meta` envelope pair and matching `MCP-Protocol-Version`/`Mcp-Method` headers, so the exact request and "check the body, not the status" are warranted.
  - `server/discover` writes no record: `_KINDS` holds only `tools/call`, `resources/read` and `prompts/get`.
  - The 421/403 statuses match `transport_security.py` l. 116/121.
- **The frozen headers match the form of the earlier records**, with the boilerplate verbatim, a status line, the departures and "Was offen bleibt" in the past tense. The concept records that it supersedes architecture §8.
- **`design-records.md` lists all five paragraphs that code cites today:** concept §5 (`test_access.py`), concept §6 (`test_render.py`), unit §5.1 (`render.py`), unit §9 (`auth.py`) and unit §10 (`test_mcp_server.py`). It also lists the ones the build cited before the freeze, marked "no longer cited", and marks architecture §8 as superseded.
- **Unit 3 in the accepted table is correct:** PR #9, `d75c4b3`, is a merge on `main`.
- **README and indexes:** eleven records in the table (counted), eighteen commands (matches `--help`), and all three new pages in their toctrees.
- **The `.vale.ini` count (16 of 24) is recounted**, not carried forward.
- **Language:** American English, sentence-case headings and one sentence per line hold on all four new files.

## Issues

### Critical

None.

### Important

**I-1. The named limit "a delivery without a record" doesn't exist in this code. The real one, a record without a delivery, is wider than stdio.**

- Where:
  - `docs/explanation/mcp-interface.md:180-182`;
  - `docs/explanation/trust-boundaries.md:149-151`;
  - `docs/superpowers/landkarte.md:699-703`;
  - the unit spec's frozen header, which doesn't list §7's sentence as a departure.
- What:
  - `Service.answer` writes the `mcp_access` in its `finally` (`server.py:381-383`) **before** it returns the answer to the SDK, and `Service.net` does the same (`server.py:400-411`). So no answer leaves before its entry is committed.
  - If the write fails, the exception replaces the answer, and the client gets the SDK's `Error executing tool …`. The map's own Kleinkram entry (l. 704–707) says exactly that: "geschlossen gescheitert, nichts wurde geliefert". The map therefore contradicts itself.
  - "A process that stops between the answer and the write leaves an answer that no event records" is the gate's limit, copied over through S §7. The gate calls the provider first and writes afterward; this server reads, writes, then answers.
  - Conversely, a committed entry whose answer never arrives isn't specific to stdio. A dropped HTTP connection, a proxy timeout, or a process killed after the commit gives the same outcome.
- Why: this is a boundary page and the map, so a wrong sentence there reads as a known gap of the access log. It sends the next unit to "fix" a gap that isn't there. It also hides that every lost answer, on either transport, shows up in `previously access` as delivered. The R-12 limit isn't wrong; it is scoped to one of several causes.
- Fix:
  - In `mcp-interface.md` and `trust-boundaries.md`, say that the entry is written before the answer leaves, so the log never misses a delivered answer. Any answer that then fails to arrive is a record without a delivery: stdin closed, connection dropped, process stopped after the commit.
  - Rename the trust-boundaries heading. "A call can go unrecorded here too" is false; for example, "A record can name an answer that never arrived".
  - Rewrite the map entry the same way.
  - Add one bullet to the unit spec's frozen header: §7 "Ein Abbruch zwischen Antwort und Schreiben verliert den Eintrag" didn't happen, because the entry comes before the answer. The header lists departures, and freezing is the moment to record this one.
  - For the code reviewer: the `record_access` docstring (`core/access.py:118-121`) carries the same wrong sentence.

**I-2. The quotation test holds some quotes by a fragment of 13 characters.**

- Where: `tests/test_docs_references.py:1322-1359`, through `_static_parts`/`_is_the_same_sentence`.
- What: I measured this in memory, against the current helpers and with no file changed. Each of these altered lines is accepted as "a text the module builds":
  - `the rules of circle:bauer forbid claude-max entirely: whatever` matches `f"the rules of {…}"` (`read.py:177`, the `named` fragment). Its only static part is `"the rules of "` followed by an open end, so any line that starts with those 13 characters passes. That is the whole hold on the `rule` reason the page quotes at l. 279.
  - `circle team lacks any rule, so only local processing is allowed; this client (claude-code) uses claude-max, which is not local` passes. The opening and the `this client (…) processes with …` part come from other literals (`scope`, `who`), which are never composed.
  - `cursor is NOT VALID ANYWHERE; call again without a cursor for the first page` passes, because `CURSOR_REFUSED` is interpolated.
  - `since is not a date at all, such as 2026-09-01` passes, because `_MOMENT_HELP` is interpolated.

  The implementer named the leading-interpolation case. The trailing case is worse: a short literal with an open end, which reaches every line with that prefix.
- Why: under CLAUDE.md, an assurance needs a test measured to fail. For the withheld reasons, the most policy-relevant text on the page, a change to `withholding`'s wording or a typo on the page stays green.
- Fix:
  1. Produce the reason lines rather than pattern-match them. `decide` and `withholding` are pure, so a test can build a minimal `Policy` (circles `team` without a rule, `bauer` with an EU rule; provider `claude-max` in the US) and compare the page's lines exactly, the way the example-page test does.
  2. In `_static_parts`, inline a `FormattedValue` that names a module-level string `Final` (`CURSOR_REFUSED`, `_MOMENT_HELP`).
  3. Optionally, refuse a match whose static parts cover less than about half of the line.

  Then mutate `who` and `named` in `read.py` and measure red, with a control kept green.

**I-3. The M4 table drops the one row that contradicts the page's conclusion.**

- Where: `docs/explanation/mcp-interface.md:51-62`.
- What:
  - The measurement has an "eingebettete Ressource" row: ✔ in Claude Code and ✔ in Vibe. The page's table leaves it out.
  - The next sentence says "every addition to plain text costs content in at least one client". That is false for the embedded resource, and for two text blocks, which in the page's own table lose nothing.
  - The reason the measurement actually gives (M, "Was daraus folgt" 1) is narrower: structured content and a resource link each cost content, and in Vibe the whole result.
- Why: this is an explanation page whose reason is overstated. A reader who later wants an embedded resource finds a measured "no" that the measurement doesn't contain.
- Fix:
  - Add the row: "An embedded resource | Arrives. | Arrives. | Not measured."
  - Reword l. 62 along the lines of: "structured content and a resource link each cost content in at least one client, Vibe sometimes the whole result; two blocks and an embedded resource arrived, but nothing in them needs more than one block."

### Minor

**M-1. The combined handoff leaves a sentence of the gate handoff false.**
`handoffs/2026-10-09-kup6s-gate.md:59,62` says "Nothing inbound", and "the content of the log leaves the cluster there [the tools pod] and nowhere else in this release".
With `v0.1.0a3`, content also leaves through `previously-mcp`, inbound through the Service, to a client and its provider.
The MCP handoff says that file "stands as written" (l. 9).
Fix: add one sentence to the MCP handoff, in the section on the gate, saying that for this release the gate handoff's "nowhere else" now has a second way out, the MCP Service, and that its egress rule for the tools pod is unchanged.

**M-2. The readiness token is a full client credential, and the handoff leaves its processor open** (`handoffs/2026-10-11-kup6s-mcp.md:54-61`).
With `--processor PROVIDER`, a maintainer might pick `claude-max`, or a local provider, which sees every circle without a rule.
It adds no reach beyond the `PREVIOUSLY_DSN` mounted beside it in the same pod, so this is minor.
Fix: say that the token can call every tool. Say to give it a provider of its own that isn't `--local`, and to confirm with `whoami` under that token that no circle reads "sees it".

**M-3. The reference's `policy` row misstates when it is empty** (`docs/reference/mcp-tools.md:335`).
It says "an empty object where the call ended before the policy was read, such as for a client not in force".
For a client not in force the policy *was* read; the client wasn't found in it (`server.py:363-369`).
It is also empty for every call that the SDK refused (`net`, `server.py:404`).
Fix: "an empty object where the call found no client in force, or never reached the server's code".

**M-4. The reference's `call.name` row is incomplete** (`mcp-tools.md:347`).
For a resource call that the SDK refuses, `net` records the requested URI, not the template (`server.py:392-393`).
Fix: add "for a refused resource call, the URI it asked for".

**M-5. "Counted in the header" isn't true of every result** (`mcp-tools.md:145`).
Error results (`render_error`) and prompt texts (`_said`) are sanitized but have no header and no count.
Fix: "…removed from it, and counted in the header where the result has one".

**M-6. A garbled sentence** (`mcp-interface.md:145`): "No change has broken a call yet; the design has one that would come under a new name, with the old one kept for one release."
Fix: "No change has broken a call yet; one that would comes under a new name, and the old one stays for one release."

**M-7. K §9's time limit is in neither the pages nor the map.**
K §9 says every call stays well under 60 seconds, Vibe's default timeout.
With the chronicle reading the whole log for a sparse circle, that is the consequence that will be felt first.
Fix: add it to the map entry on the read bound (l. 669ff.), and add half a sentence to `mcp-open-limits`.

**M-8. Two unchecked things are missing from the map.**
`cacheScope: private` for the resource templates (K §4.4) is unchecked; this is the implementer's own concern 5.
The how-to says to use `--legacy-harness` "until the default harness offers the new ones" (l. 116), without saying how. The measurement lists `/mcp refresh` as unmeasured.
Fix: add one map entry for `cacheScope`. In the how-to, say that whether `/mcp refresh` brings the new tools hasn't been measured.

**M-9. Docker-compose: considered, but the token step isn't placed** (`handoffs/2026-10-11-kup6s-mcp.md:117-121`).
A compose reader finds the service, the variable and the port binding, but not where `previously client add` runs.
Fix: half a sentence, such as "tokens come from `docker compose run --rm mcp previously client add …`". S §8 asks for consideration only, so this is minor.

**M-10. Nits on the reference.**
The heading omits the case with neither a sender nor recipients; the part is then left out (`_heading`).
`whoami` prints `processor NAME: not declared` for an undeclared provider (`chain_line`).
A `list_circles` statement reads `erased` after an erasure (`statement`).
Each is one clause, if wanted.

**M-11. Citation form, nit** (`src/previously/mcp_server/auth.py:13`).
It reads "by ruling R-10 of the same plan" rather than the prescribed form.
The census still finds it, and the referent is named on the line before, so the fix is optional.

**M-12. Out of scope, named only.**
`tests/test_gate.py:328,425,511,538,1091,1637` and `tests/test_cascade.py:266` cite the frozen gate record as "Spec section N" without `(frozen design record)`.
The paragraph-sign check doesn't see the word "section".
This is not this branch's change; it belongs in the map.

### Diátaxis

- `mcp-interface.md` stays an explanation, and `mcp-tools.md` stays a reference with no arguing.
- The how-to explains in three places, each in one sentence and each tied to a step: why a client is a provider (l. 16), the stdio risk (l. 96–97), and why `headers` (l. 113). That is acceptable.
- "Tested configurations" (l. 141–151) is reference-shaped, but the brief puts it there deliberately, and it is dated and labeled.
- No page needs splitting.

## Assessment

**Ready after fixes.**

The pages are accurate to an unusual degree, and the freeze, the map (200, unit 4 built and not accepted, unit 3 rightly accepted), the design-records table, the handoff and the citation census all hold.

What has to change before the merge:

- **I-1:** a named limit that is false against the code, in four places.
- **I-2:** a quotation test that holds the policy reasons by 13 characters.
- **I-3:** an explanation whose reason overstates its measurement.

Each fix is local: a few sentences in four files, plus one test that produces the reasons instead of matching them.
The minor items can ride along in the same fix wave, or go to the map.
