# Task 6 report — documentation, handoff, map, freeze

Status: DONE_WITH_CONCERNS (concerns at the end; none blocks the gates).

Base `bfe301a`; commits, in order:

| Commit | What |
|---|---|
| `7704fdf` | `Dockerfile`: `ENV MALLOC_MMAP_THRESHOLD_=131072`, with the host and the in-image measurements in its comment |
| `d8a0929` | The three new pages, the pages that lagged, the retyped `show` blocks of the two blob how-tos, the new tests in `tests/test_docs_references.py`, README, Vale vocabulary |
| `459e3e7` | Handoff `docs/superpowers/handoffs/2026-10-06-kup6s-ingest.md` |
| `702dbe3` | Map, freeze of the spec, `design-records.md`, one line of `DEPENDENCIES.md` |
| `42425e7` | Tutorial retyped from a fresh clone, the test-run block last (ruling P-1); the map quotes the new count |

Each commit ends with exactly one trailer, `Assisted-By: Claude Opus 5.5 <noreply@anthropic.com>`; files staged by name.

## Pages

**New**

- `docs/explanation/connectors.md`, label `connectors` (explanation): a connector takes in and doesn't interpret (bytes and a position; mapping in `core.mail` because an `.eml` in Nextcloud is the same bytes; quotes, signatures, addresses kept as written); the watermark follows the append (why that order, why re-reading is harmless, read-only `EXAMINE` + `BODY.PEEK[]`, the folder as a door not a mirror); `source` names the channel; two sightings of one artifact (why `ArtifactChanged`, why neither units nor payload can carry the identity, the rule belongs to the project, why no salt); the variant (and the 64-bit collision, stated honestly as about four billion attempts and a run that stops at every run — acceptable for a hand-filled folder); the raw mail is a blob (no `raw` field, an unmappable mail never stops a run, lookup before storing); a mail inside a mail is a mail; the folder isn't a property of the mail.
- `docs/reference/mail-mapping.md`, label `mail-mapping` (reference): the event field by field; units (subject, body, the three fixed sentences); body-part selection; character sets table; HTML via `html2text 2025.4.15` with its three settings and a table of what the Markdown output looks like (`<br>`, `**`, `_`, links, blockquote, tables, escaping `1\.`, the swallowing `<`); the artifact-identity document and its rules; channel identities; blobs and attachment names (`/`→`_`, empty/`.`/`..` → none); payload keys table and body-entry table; a mail inside a mail (depth 5, `not_unpacked`, the 500-event refusal quoted); a mail that doesn't map (`unreadable mail: <class>`, quoted from a test mail; the non-text `charset=` case); cases table (known, variant, the 64-bit collision, erased, no Message-ID incl. the daily "Backup OK" merge, no/unreadable `Date`, HTML only, `multipart/signed`, opaque S/MIME → `attachments only`, encrypted, bounce `text/rfc822-headers` as body). Every name and wording taken from the code.
- `docs/how-to/ingest-a-mail-folder.md`, label `ingest-a-mail-folder` (how-to): a Mailu user of its own (ASCII password); create and fill the folder, forward **as attachment**; set the settings (placeholders); run (typed against GreenMail: `imap: 5 appended, 0 known, 0 variants, up to uid 4`, second run `0 appended`), `project`, `chronicle --since …`; read the output; run on a schedule (cron line with `flock -n`, `docker run --memory 768m`, writable `/tmp`; Kubernetes in one sentence); erase a mail: `redact event`, never `redact units` (subject in `headers`, raw mail blob, unsalted `artifact_hash`), the mails inside (SQL on `forwarded_in`, typed `redact` output naming the shared blob), the replies that quote it (SQL over `In-Reply-To`/`References`, measured against PostgreSQL 17), the folder and the mailbox backups; restore re-reads; an erased mail forwarded again comes back as the new mail's attachment.

**Changed**

- `docs/explanation/erasure.md`: unsalted `artifact_hash` survives `redact units` (a salt would destroy its purpose); for a mail, erasing means the event; three new limits: a mail stays where it came from (folder, clients, mail-server backups; restore forgets the key), quotes outlive the mail (`In-Reply-To`/`References`), an erasure holds per event, not per content (forwarded again → back as attachment). The old sentence "is for the contract of the connectors to settle" replaced.
- `docs/how-to/erase-something.md`: a bullet for a mail under *Choose the target*; the unsalted `artifact_hash` under *What the erasure doesn't reach*; three `show` blocks retyped.
- `docs/how-to/attach-and-fetch-a-file.md`: `show` block retyped.
- `docs/explanation/module-boundaries.md`: six modules, `connectors` in the layer order; diagram ten internal edges, eight arrows out (`imaplib`); fourteen permitted edges, ten exist, the four missing named; the grep block re-measured on 2026-10-06 with `connectors`; eight contracts with the gate's output re-measured, the history of the first line's name; "last four contracts"; the second contract needn't name `connectors`; a new section *A contract for the connectors*; `LogStore` named by six modules of `core`, still 13 methods (measured with the store's command plus `core/ingest.py`); `WatermarkStore` as fourth protocol, `Connector` named.
- `docs/explanation/design-records.md`: eight records; a paragraph on this spec and the pages that took it over; "No row names …" with the paragraph-sign measurement (same fifteen lines in the same seven files, byte-identical to `fd3e17f`; the unit's code cites `artifact-identity` 12× and `cli-reference` 3×).
- `docs/reference/database-schema.md`: `set_at` is given by the caller; `ingest` gives the moment its run started, its `recorded_at`.
- `docs/how-to/cut-a-release.md:87`: `0006_example`.
- `docs/tutorials/record-your-first-event.md`: every block retyped from one fresh-clone session (`Resolved 110 packages`, `Installed 107`, `artifact_hash` in the payload, the note now says `artifact_hash` is the one value that matches the reader's); test-run block last, `1045 passed in 161.14s`.
- Indexes (`docs/index.md`, the three quadrant indexes), `README.md` (state, an `ingest imap` bullet, twelve commands, one connector in "does not do", mail limits of erasure, eight frozen records with a row for the pilot spec).
- `DEPENDENCIES.md`: `html2text` "turns every HTML part of the body", not "a mail that has only HTML" (stale since ruling T2-d).
- `.vale.ini` + `.vale-styles/config/vocabularies/Previously/accept.txt`: `Mailu` added; the comment's count updated (twenty entries, fifteen lowercase, recounted with its `awk`).
- `cli.md` and `configuration.md` were already complete from Tasks 3–5; checked, not changed.

**Tests added** (`tests/test_docs_references.py`, three tests; suite 1042 → 1045):

- `test_the_mail_mapping_quotes_the_units_of_a_mail_without_text` — the three no-body sentences and `unreadable mail: UnicodeEncodeError`, produced by mapping `encrypted.eml`, `attachments_only.eml`, `empty.eml`, `unreadable_header.eml`.
- `test_the_mail_mapping_names_every_key_the_mapping_writes` — payload table == union of payload keys `map_mail` writes for all 41 test mails (inner mails included) ∪ keys `core/ingest.py` writes into a spread dict (`raw`, `variant_of`, `forwarded_in`); body-entry table == keys of a body entry.
- `test_the_mail_mapping_names_the_converter_and_quotes_the_batch_refusal` — `CONVERTER` named on the page; the `BatchTooLarge` quote against `core/append.py`.

Mutations, each run with `-k mail_mapping`, files restored after each: page drops the `not_unpacked` row → red; page names `raw_size` → red; page drops the `guessed` row → red; code rewords `NO_BODY_EMPTY` → red; `ingest.py` renames `raw` → red; `mail.py` renames `declared` → red; page names `html2text 2024.2.26` → red; code rewords the batch refusal → red; page quotes the unreadable unit with a message → red. Control, unchanged tree: `3 passed`.

## Addendum items, where each landed

| Item | Where |
|---|---|
| Retype `show` on tutorial, `erase-something.md`, `attach-and-fetch-a-file.md` (T1-a) | `d8a0929` (how-tos, from one session against PostgreSQL 17 + RustFS 1.0.1); `42425e7` (tutorial, fresh clone) |
| Tutorial test block last (P-1) | `42425e7`: placeholder in the clone, green run `1045 passed`, whole block typed |
| Mail → `redact event`; unsalted `artifact_hash` as reason | `erasure.md`, `erase-something.md`, `ingest-a-mail-folder.md`; map *Tilgung* |
| Erased mail forwarded again comes back | `erasure.md`, `ingest-a-mail-folder.md`; map *Tilgung* |
| Folder, mailbox backups, quoting replies | `erasure.md`, `ingest-a-mail-folder.md`, handoff; map *Tilgung* and *Betrieb* |
| The 11 named behaviours | stated as fact on `mail-mapping.md`; each a bullet in the map (*Aufnahme aus IMAP*) |
| Shapes (`body` list, per-part identity, LF, `headers` unfolded, `headers_replaced`, `not_unpacked`, fallback event) | `mail-mapping.md`, from the code; held by the new tests |
| `ENV MALLOC_MMAP_THRESHOLD_=131072` with comment, measured in image | `7704fdf`; measurement below |
| Memory limit 768 MiB in handoff and compose consideration | handoff *Memory*; the compose/cron consideration on `ingest-a-mail-folder.md` (`--memory 768m`); map *Betrieb* |
| `ubuntu-latest` → Ubuntu 26 from 2026-10-19 | map *Tore und Werkzeuge* |
| `module-boundaries.md` (eight contracts, layer name, edges, `WatermarkStore`) | `d8a0929`, counted from `lint-imports` and `grep` |
| README "eleven" → twelve, other counts | `d8a0929` |
| `cut-a-release.md:87` → `0006_example` | `d8a0929` |
| `database-schema.md` `set_at` | `d8a0929` |
| CLAUDE.md not edited | untouched; "six contract names" vs eight put into the map *Tore und Werkzeuge* for the maintainer |

## Memory measurement in the image

Image built from this branch exactly as `run-the-image.md` says (`uv build --wheel`, `docker build --build-context wheels=…`); `scripts/smoke-image.sh previously:local` passed. Image glibc: **Debian GLIBC 2.41-12+deb13u4** (host: Ubuntu GLIBC 2.39). Trust store in the image: 150 CAs in Python's default `ssl` context.

1. `map_mail` alone (as the addendum asked): `python mapmem.py measure` over three invented mails of 49.54 MiB (attachment 36.2 MiB of random bytes in base64), files written by a separate process: VmHWM after imports 28 MiB, after each mail **459–460 MiB**, three runs; the same with the setting unset (`env -u MALLOC_MMAP_THRESHOLD_`): 460 MiB. No growth either way — a block of this size lies above glibc's 32 MiB cap on the dynamic threshold.
2. The whole command, since that is what the pod limit has to hold: `previously ingest imap` in the image against GreenMail 2.1.14 (TLS, certificate for the container name, trusted through `SSL_CERT_FILE`), PostgreSQL 17, RustFS 1.0.1, run as `docker run --memory 768m --memory-swap 768m --user 1000:1000 --read-only --tmpfs /tmp … python runmem.py ingest imap`, where `runmem.py` calls `previously.cli.main` and then prints `VmHWM` and `/sys/fs/cgroup/memory.peak`. Two rounds each:

| Mails | Setting on (image as built): VmHWM / memory.peak | Setting unset: VmHWM / memory.peak |
|---|---|---|
| 1 × 49.5 MiB | 529, 530 / 511, 511 MiB (one of these under `--memory 512m`) | — |
| 3 × 49.5 MiB | 531, 529 / 513, 511 | 533, 533 / 515, 514 |
| 1 × 27.4 MiB | 335, 336 / 316, 317 | 336, 335 / 318, 317 |
| 3 × 27.4 MiB | 336, 336 / 317, 317 | 360, 360 / 342, 342 |
| 6 × 27.4 MiB | 336, 335 / 318, 317 | 360, 361 / 342, 342 |

So in the image the setting still keeps the peak flat, but saves only ~25 MiB (host: 105–142 MiB); the reviewer's 528 MiB absolute for 49.3 MiB is reproduced (529–531). `--memory 512m` passed one 49.5 MiB mail with `memory.peak` 511 MiB — no margin, so **768 MiB stays** in the handoff and the how-to. `/tmp` was a tmpfs, so the sealed temporary file is inside these numbers. The migration from a `0.1.0a1` database was measured too: `migrated: 0004_event_blob -> 0005_watermark` (quoted in the handoff). All mails invented, generated in scratch, deleted afterwards; all containers removed.

## Map

Counted with the command in `CLAUDE.md`: **120 before, 149 after** (+33 added, −4 struck into *Erledigt* with commits: silent drop of changed content → `5aa447a`; `RawEvent` without raw/channel identities → `5aa447a`, `b4e5a8c`; payload range forces reshaping → `0807c35`, `a1da00e`; re-sighting after erasure → `5aa447a`, `b4e5a8c`). Unit 1 marked **built** on `worktree-pilot-aufnahme`, accepted with the merge (Bedingung 11 named before it); the delivery row moved to "built and accepted" with PR #6 `fd3e17f`; the pilot table, *Was vor was* and the legend (**PI**, **P-PI**) updated; new sections *Aufnahme aus IMAP (Pilot, Einheit 1)* and *Nextcloud-Ordner (Pilot, Einheit 7)*. All §11 points placed as the brief says (threads under *Feststellungen*, `.msg`/`.mbox` under unit 7, OAuth under *Einwurf-Vertrag*). Beyond the addendum, the ledger's other named items went in too (counter race, `> after` filter, lost variant notices, 127.0.0.2 Linux-only, the misuse-only items of Tasks 1 and 3, a refused `append --attach` leaving blobs).

Spec frozen with the header of the two earlier records, status line (`eingefroren am 2026-10-06; … „passt so"; §3.2–§3.5 nachgezogen, 5735843`), §11 intro rewritten in the past tense naming where each point went.

## Gates (final run, after the last commit `42425e7`, each separately)

- `uv run ruff check .` — All checks passed!
- `uv run ruff format --check .` — 88 files already formatted
- `uv run pyright` — 0 errors, 0 warnings, 0 informations
- `uv run lint-imports` — Contracts: 8 kept, 0 broken.
- `uv run pytest --cov --cov-report=term-missing` — 1045 passed in 162.67s, total coverage 97.84 %
- `make -C docs html` — build succeeded; `make -C docs vale` — 0 errors, 0 warnings, 0 suggestions in 34 files; `make -C docs linkcheck` — build succeeded, `output.txt` empty
- `uv run pip-audit --skip-editable` — No known vulnerabilities found

## Concerns

1. Code cites `{ref}`artifact-identity`` (a reference section) in the module docstrings of `core/mail.py` and `core/ingest.py` for reasoning that now stands on `{ref}`connectors``; repointing is a code-comment change, left for the fix wave.
2. `src/previously/contract/store.py` docstring says the count runs over "the five modules that name `LogStore` today"; `core/ingest.py` is a sixth (the count, 13, is unchanged — measured). A stale comment claim; fix wave.
3. The 2026-10-05 handoff still quotes `0004_event_blob` outputs; it is a dated record and was left as is; the new handoff gives `0005_watermark`.
4. The map's *Auslieferung* points on the PyPI name and Bedingung 8 may be closable (the spec says `0.1.0a1` is published, and that image exists); not struck, because I did not verify the release steps myself.
5. The Mailu steps on the how-to are deliberately generic (no UI labels); the "50 MB default" comes from the spec, not checked against a Mailu instance. The cron line was not run as a cron line; its two `docker run` commands' parts were (the 768 MiB container run, the commands).
6. `--memory` was measured with Docker, not in Kubernetes; the handoff says so ("an image built from this branch", `docker --memory`), and also that an `emptyDir` with `medium: Memory` counts, which the tmpfs measurement covers.
7. Root config touched: `.vale.ini` comment and the Vale vocabulary (`Mailu`); both English.
8. `html2text` is GPL-3.0-or-later (already recorded in `DEPENDENCIES.md`), for the maintainer as the ledger says.
