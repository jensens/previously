# Fix wave after the final review — brief

The branch is ready after these fixes. Two final reviews: `final-review-code.md` and `final-review-docs.md` in this directory — read both; they have file:line, failure scenarios and suggested fixes.
This is the only fix round; each item below is decided. Items not listed here stay as the reviews name them.

## Code

1. **A mail that `append` refuses must not stop every run** (code review I-1). Two cheap guards in `core/mail.py`, each with a test measured red without it:
   - a Message-ID too long for the key index (measured: ~3.2 KB fails the btree limit of 2704 bytes on `source_key_pkey`) falls back to `external_id = sha256:<raw sha>`, the same fallback a missing Message-ID uses. Pick a bound well below the index limit and argue it in a comment (UTF-8 bytes, not characters). Check what else goes into that key (variant suffix `#<16 hex>`, the source) so the bound covers the longest key the run can build.
   - a `Date` header that parses but cannot become an aware UTC instant (`Fri, 31 Dec 9999 23:30:00 -0100` → `OverflowError` in `iso_utc`) is treated as unreadable: `occurred_at` from `INTERNALDATE`, `date_source` as for an unreadable `Date`.
   Say on `docs/reference/mail-mapping.md` what happens in both cases.
2. **One malformed address header must not make the whole mail unreadable** (code review M-1): a trailing lone `"` (`To: a@example.org, "`) raises `IndexError` in the standard library. Catch per header in `_channel_identities` (that header contributes no identities; the mail maps normally), so `mail-mapping.md:130` is true. Test with an invented mail, measured red without the fix.
3. **Terminal control sequences from mail content** (code review M-2): `escape_field` lets C0/C1 controls (ESC, OSC, BEL, …) through to the terminal in `chronicle` and `show`. Mail is written by strangers. Make the human-readable output escape them visibly (in the style `escape_field` already uses for what it escapes), keep tab/newline handling as it is, and test ESC and an OSC sequence. If `show` prints JSON, check whether JSON escaping already covers it (it does for C0 in `json.dumps` with `ensure_ascii`; check C1 U+0080–U+009F) and only change what is actually raw. Retype any typed output this changes.
4. **Ruling T1-b** (ledger): `previously append --text` hashes its text byte for byte; the same text with CRLF instead of LF would be refused under a known key. Normalize line endings before hashing, the way `split_plaintext` does (`normalize_line_endings`). Test, mutation red.
5. **Ruling citations** (code review I-2): `tests/test_mail.py:649, 731, 780, 811` cite T2-d, T2-e, "rulings T2-b and T2-f", T2-g with no plan; the same labels exist in the shipped 2026-10-05 delivery record as different decisions. Rewrite each as `ruling T2-x of the 2026-10-06 pilot ingest plan`, one `ruling` per label, and make sure the reason stands in the comment beside it (CLAUDE.md, "A ruling citation is provenance, never the reason"). Run the census `grep -rnioE 'ruling (P|T[0-9]+)-[a-z0-9]+' src tests pyproject.toml .importlinter` and qualify every citation this branch added. The controller ships this plan's ledger to `docs/superpowers/sdd/2026-10-06-pilot-imap-aufnahme/progress.md` after your round — do not create it yourself.
6. **Comments that claim too much** (task reviews, deferred): correct each against the code:
   - `core/errors.py:38` "before anything … is written" and `docs/explanation/hash-format.md:66` "only an event written before …" — check against what `append` does now with `ArtifactChanged`;
   - stale `_check_units` names in `tests/test_append.py` (~487);
   - the docstring of `_recovered` in `core/mail.py` (~437-443) claims to recover bytes from `unknown-8bit` encoded words, but `_headers` decodes encoded words after it runs;
   - `core/ingest.py` / `core/append.py`: the `known_id` docstring "the one place the rule lives" (`_Run._holds` compares too); the module docstring "a batch holds … not their content" (events carry their units); the memory test's docstring states varying figures as fixed and omits glibc's 32 MiB cap on the dynamic threshold; the docstring of `test_a_batch_the_log_refuses_leaves_the_watermark` ("yet another", "looked both up");
   - the ragged comment above `watermark` in `storage/schema.py`;
   - `{ref}`artifact-identity`` in `core/mail.py` and `core/ingest.py` where the reasoning now stands on `{ref}`connectors``;
   - `contract/store.py` "five modules" name `LogStore` — count them now.

## Documentation and handoff

7. **Erasing a mail** (docs review I1): the "erase these as well" list on `docs/how-to/ingest-a-mail-folder.md` (~112-159), and the matching passages on `docs/explanation/erasure.md` and `docs/how-to/erase-something.md`, must cover: the mail's variants (`<message-id>#<hex>`, own events with own raw mail); the outer mail it was forwarded in (its raw mail holds the inner mail whole — erase the outer event too, or say what remains); forwards nested deeper than one level (the query must follow `forwarded_in` transitively, or the page says how to repeat it). Give a query or command sequence that a reader can run, and check it by running it against containers (invented mail; discard afterwards).
8. **Handoff alarm** (docs review I2): `docs/superpowers/handoffs/2026-10-06-kup6s-ingest.md` (~94-95) — alarm on any exit code other than 0, and list what the codes mean (2 the command's own errors; 1 an unexpected failure; 137 killed, e.g. out of memory at the limit; 143 stopped), as the 2026-10-05 delivery handoff does.
9. **Error list in `cli.md`** (docs review I3): add the five IMAP sentences the review names and the two refusals of the log that recur at every run (`ArtifactChanged`, `BatchTooLarge`) to `docs/reference/cli.md`, including the exit-code row for `ingest` (~56). Quote from the code exactly; extend `tests/test_docs_references.py` if it holds that list, so a missing sentence fails.
10. **Docs review Minors**: fix each that states something false or is a cheap style fix; leave the others named in your report with one line why.
11. **The map** (`docs/superpowers/landkarte.md`, German): the delivery points about the PyPI name and about condition 8 may be closable. Facts: release `v0.1.0a1` was published on 2026-10-05 from commit `fd3e17f` — `previously 0.1.0a1` on PyPI and `ghcr.io/jensens/previously:0.1.0a1` (public). Verify on PyPI (e.g. `curl -s https://pypi.org/pypi/previously/json`) and strike each point that this closes, naming the tag. Add as open points (German, under the right unit) the code review's named Minors M-3 (`UID SEARCH` over ~140,000 mails exceeds imaplib's 1,000,000-byte line limit), M-4 (an unrecognised FETCH answer counts as expunged), M-5 (`example.at`/`example.de` in test mails are not RFC 2606 names; changing them changes hashes). Recount with the awk command from CLAUDE.md and report before/after.

## Not yours

`CLAUDE.md` (its contract count is the maintainer's decision), the frozen spec (do not edit it), and the execution record.

## Finish

- Retype typed output this changes (from real runs), the tutorial's test-run block last (ruling P-1).
- All six gates, each separately, plus `uv run pip-audit --skip-editable`:
  ```
  uv run ruff check .
  uv run ruff format --check .
  uv run pyright
  uv run lint-imports
  uv run pytest --cov --cov-report=term-missing
  make -C docs html && make -C docs vale && make -C docs linkcheck
  ```
- Commits staged by name, English messages, each ending with exactly one trailer naming your model (`Assisted-By: Claude Opus 5.5 <noreply@anthropic.com>`); never `Co-Authored-By`, never "Generated with". Group them sensibly (code guards; escaping; citations and comments; docs and handoff; map).
- Report to `fixwave-report.md` in this directory: per item what changed, tests, mutations (red with green control), what stayed named and why, gate results, map counts.
