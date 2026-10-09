# Final review, documentation package — Pilot, Einheit 3: Gate und Policy

Range a1f632a..b9276e7 (e6bbe89, d7651f7, 82bb0de, b9276e7). Reviewer: Opus, 2026-10-09, read-only.
Stands in for the review of Task 7 (ruling R-13).

What I ran: `uv run previously gate --help`, `uv run previously policy --help`, `pytest --collect-only` (per-file counts of the tutorial block against the tree), the open-points command from CLAUDE.md at a1f632a and b9276e7, `git log`/`git show` on the spec.
I did not run the six gates (`ruff check`, `ruff format --check`, `pyright`, `lint-imports`, `pytest --cov --cov-report=term-missing`, `make -C docs html && make -C docs vale && make -C docs linkcheck`), as the brief asked; the Task 7 report says all six were green at b9276e7.

## Strengths

- Every quoted message on the four new pages exists in the code, word for word: the fallback line (`cli.py` `_fallback_line`), `write? [y/N]`, `Error: anthropic: the provider is not configured — set ANTHROPIC_API_KEY`, the three denial reasons (`gate/gate.py:72-74`), `no local provider is declared` (`core/decide.py:31`), every candidate rejection sentence in the how-to (`core/decide.py:143-171`), `NoChoice`/`not_configured`, `geo_mismatch`.
  The reference tables are held key by key by the new tests in `tests/test_docs_references.py`.
- The how-to's `gate explain` blocks are consistent with the code down to the event numbers (mail 1, six statements 2–7, `model_call` 8, rules 9 and 10) and the region choice (R-7: `global` under `any`, nothing under Mistral's single space, R-6).
- The tutorial block is one plain `uv run pytest` run: 43 files, 1255 tests, every per-file count equal to `pytest --collect-only` at head (T1-b holds).
- `processing-policy.md` carries the reasons, not only the claims: two checks (different subjects, different places), circles after Simmel, strictest-wins argued from the asymmetry of visible failure, the R-8 exceptions with "replacing is not adding", promise vs. report with the measured `global` → `global`, local-only argued from the operator's statement and the visible fallback argued from the measured weakness, audit in the log and result in the units argued from erasure, R-11 tied to the one-level cascade.
- `trust-boundaries.md` names all four required gaps: R-10 (`ANTHROPIC_BASE_URL`, with the reason it is accepted), provider retention reached by no erasure, a call unrecorded on a crash between answer and write, unknown participants under a source rule — plus the write failure after a paid call.
- The handoff has the two secrets (tools pod only, no CronJob), egress to `api.anthropic.com` and `api.mistral.ai` on 443 plus DNS, the optional price file via `PREVIOUSLY_PRICES`, the model server as its own section, "Memory and CPU: **not measured.**", `ANTHROPIC_BASE_URL` set nowhere, and the compose paragraph.
  The claim that TLS verifies against the image's trust store is right: `httpx2` uses `truststore` (`.venv/.../httpx2/_config.py:40-41`).
- The map: count 152 → 178 reproduces with the CLAUDE.md command; all eleven points of spec §11 and plan decision 6 are present under their units; the terminology fix is made for units 3 and 4 and as a new precondition row; `v0.1.0a2` and the ingest handoff are struck to *Erledigt*; every deferred minor of the ledger (Tasks 1–6) is present.
- Frozen header and status line match the 1c, Auslieferung and IMAP records; §11 is in the past tense and points to the map.

## Issues

### Critical

None.

### Important

**I-1. The frozen header misstates what was amended and omits a departure the pages carry.**
`docs/superpowers/specs/2026-10-09-pilot-gate-und-policy.md:20-27` says the same-day amendments covered "die Fassung von §2.5 Punkt 5 und §8 Punkt 3 (Commits `5a2fa6f`, `26f4cb4`)".
`26f4cb4` touches only `core/decide.py` and `tests/test_decide.py`; no commit ever changed §2.5 Punkt 5 (`git log -S'sonst \`global\`'` finds only `f2661d7`, its origin).
So the frozen §2.5 Punkt 5 (line 278-283) still states the literal reading ruling R-7 overrode — "`us` nur, wenn `regions` auf `us` beschränkt ist, sonst `global`" — while `core/decide.py:112-127` picks the widest fitting space (with `regions = {eu, us}`: `us`, which the frozen text would make `global` and so reject Anthropic).
The header's list of "four" departures omits it; `docs/explanation/design-records.md:52` repeats "four places".
Likewise R-6 departs from the wording of §3.2 Punkt 4 and §8 Punkt 11 ("den Raum immer ausdrücklich setzen"): for a provider with one space nothing is set (`decide.py:124-125`).
Why it matters: a frozen record is provenance; one that cites a code commit as a spec amendment and states an overridden rule without a marker reads as the decision.
The page wins (`processing-policy.md:78-80` has R-7), so not Critical.
Fix: in the header, cite `da6c574` and `5a2fa6f` for §8 Punkt 3, drop `26f4cb4` and "§2.5 Punkt 5" from the amendments, and add R-7 (and R-6) to the departures; change "four" in `design-records.md:52` to the new number.

**I-2. Two typed console blocks in the how-to drop the output of the command they show.**
`docs/how-to/set-a-policy-and-try-a-call.md:128-131` and `:145-148` show `$ previously policy rule circle:xz … --yes` followed directly by `$ previously gate explain 1`.
`_cmd_policy_set` (`src/previously/cli.py`, the `print(json.dumps(payload, indent=2, …))` and `print(f"policy event {event_id}")` lines) prints the statement as indented JSON and `policy event 9` / `policy event 10` even with `--yes`.
Why it matters: CLAUDE.md treats typed output as a measurement; a block that silently omits a dozen lines reads as "this command prints nothing".
Fix: move the two `policy rule` commands into a `shell` block of their own (as the earlier sections do), or type their output from the run.

**I-3. Ruling R-5 is on no page, and the how-to's last step triggers it unannounced.**
`core/decide.py:86` counts a membership only for a circle in `Policy.circles`; a revoked circle has no members.
Its content then goes by the source rule (possibly `any`), not by `local_only` — the ledger's own "kostet, wenn falsch" names exactly this.
`grep` over `docs/explanation`, `docs/reference`, `docs/how-to` finds nothing on it, and `set-a-policy-and-try-a-call.md:185` revokes the circle ("XZ is no longer a customer") without saying where its mail goes next.
Why it matters: an operator who revokes a circle expecting its content to stay local releases it to the source rule.
Fix: one paragraph in `processing-policy.md` (why: a membership is a statement about a circle that exists), one row or sentence in `policy-and-model-calls.md` / `cli.md`, one sentence after the revoke example in the how-to.

**I-4. The citations P-PG point at a record not in the tree, and the status will be stale at the merge.**
The map defines **P-PG** as `sdd/2026-10-09-pilot-gate-und-policy/` "folgt mit der Endprüfung" and cites it in some twenty entries; the frozen header refers to "Ausführungsprotokoll"; tests cite rulings R-5, R-6, R-9, R-11, R-12 (`tests/test_gate.py:421,548,699`, `tests/test_decide.py:441`, `tests/test_cascade.py:328`).
`docs/superpowers/sdd/2026-10-09-pilot-gate-und-policy/` does not exist at b9276e7.
The unit-3 row says "Merge nach `main` steht aus" with no PR number.
Fix: before the merge, ship `progress.md` there (controller step 3), and then replace "folgt mit der Endprüfung"; the row and "Was jetzt kommt" follow the merge, as for the ingest (commit `456e140`).

### Minor

- **M-1** `set-a-policy-and-try-a-call.md:27` and `landkarte.md` (Güte des lokalen Modells): "got the direction of the delay wrong".
  `tests/mails/plain.eml` says only "the timeline moves by two weeks": no direction, so the claim isn't supported.
  The visible error in the typed answer is the invented "bewerbung für die neue Budgetfunktionalität" (the mail: "The budget stays as discussed").
  Fix: name that.
- **M-2** `set-a-policy-and-try-a-call.md:81-82`: the `processed locally:` line stands first, and `:94` calls it "the first line on standard error".
  `_cmd_gate_explain` prints the stdout lines first and the stderr line after them, so on a terminal it comes last; the block is a capture with stdout piped.
  Fix: retype from a terminal, or print the fallback before the table in the code.
- **M-3** `set-a-policy-and-try-a-call.md:57`: "not what the table above says": this page has no table.
  Fix: "the examples above".
- **M-4** `set-a-policy-and-try-a-call.md:165-174`: after the previous step the rule is `eu` and the decision is Mistral, but the example exports `ANTHROPIC_API_KEY`.
  Followed in order, it ends in `set MISTRAL_API_KEY`.
- **M-5** `set-a-policy-and-try-a-call.md:188`: only `rule --revoke` is said to need a dummy option; `provider --revoke` needs `--retention-days` too (`cli.py` `required=True`).
- **M-6** `set-a-policy-and-try-a-call.md:70`: "the mails you wrote yourself pull your own domain into every circle you work with" isn't the mechanism.
  Your address counts only where it's a member of a circle; it's then removed before resolution (`decide.py:75-80`).
- **M-7** `policy-and-model-calls.md:136`, `processing-policy.md:99` (and spec §2.6, `core/gaps.py` docstring): "an empty list where no rule applied at all" isn't quite right.
  With circles involved and no rule at all, `fallback.circles` lists those circles (`decide.py:190,227`); it's empty only when no circle is involved and no source rule applies.
- **M-8** `policy-and-model-calls.md:241`: the "When" column reads "The event is a policy event or a `model_call`".
  `gate.py:153` denies every kind but `observation`, so a redaction is denied too, and so will an assertion be.
- **M-9** `policy-and-model-calls.md:104`: `prompt_sha256` isn't reproducible from the page.
  It's the SHA-256 of the canonical JSON of `{"system": …, "template": …}` (`gate/task.py:58-61`).
- **M-10** `processing-policy.md:102` ("from the `model_call` events alone") and `cli.md` ("nothing else") both overstate.
  `core/gaps.py:305` also reads the source key of each input event.
- **M-11** `processing-policy.md:19`: "an earlier plan called it the disclosure check", but it was the map (units 3 and 4).
- **M-12** `trust-boundaries.md:32`: "the only door through which a customer's content enters" overlooks `append`, which takes text and `--attach` files as well.
- **M-13** In the map, the Güte entry cites `processing-policy.md` for "7 bis 15 s", but that page doesn't have the figure (the handoff, line 115, does).
- **M-14** The map (line 38) says "noch gegen keine echte API gelaufen", but the how-to ran against Ollama.
  Fix: "gegen keinen gehosteten Anbieter".
- **M-15** Handoff line 104 says "an error that names the server".
  With a `local` provider declared and no URL set, the error names the variable `PREVIOUSLY_LOCAL_MODEL_URL` (`_failure_line`), and the outcome is `error`, not a denial.
- **M-16** `policy-and-model-calls.md:127,146`: `policy.inference_geo` is also `null` for a denied call, and `usage` values can be `null` (`openai_compatible.py:329-330`).

## Missing from the map

- Up to 200 characters of a provider's error text go to stderr of `gate try` (`gate/adapters/__init__.py:96,166`).
  The text may echo the prompt.
  It's harmless when the maintainer runs it by hand, but it becomes customer content in container logs once a job runs the gate (unit 6).
- A CronJob that reports `policy gaps` (spec §2.6 Punkt 3).
  The handoff, line 91, calls it "a later idea", but no map entry carries it.
- `policy provider --revoke` demands `--retention-days`, the sibling of the listed `rule --revoke` entry.
- Optional: the consequence of R-5 as an open question, namely whether a revoked circle should keep its content local rather than release it to the source rule.

## Assessment

Ready to merge: **yes with fixes** — I-1 to I-3 are small text edits, and I-4 is the controller's step 3 (the record in the tree) plus the post-merge map update.
