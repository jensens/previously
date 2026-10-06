# Task 6 — what earlier tasks handed over

The brief (`task-6-brief.md`) is the requirement; this file lists what Tasks 1–5 left for Task 6, each with the ruling it comes from (German ledger: `progress.md`).
Every item here is part of Task 6.

## Typed output to retype from real runs (ruling T1-a)

- `previously show` output on the tutorial, `docs/how-to/erase-something.md` and `docs/how-to/attach-and-fetch-a-file.md` no longer matches: the payload now carries `artifact_hash`.
  No gate catches it.
  Retype each block from a real run (these how-tos need S3: use the RustFS and PostgreSQL containers the tests use, or the compose setup the pages describe), never by editing a value.
- The tutorial's test-run block: retype last, once the tree has stopped moving (ruling P-1).

## Erasure (ruling T1-a, Task 4 review minor 1)

- For a mail, `redact units` does not erase what counts: the subject stands in `headers`, the raw mail is a blob, and `artifact_hash` is an unsalted SHA-256 that confirms a short text.
  So erasing a mail means `redact event`.
  Say so in `erase-something.md` and `docs/explanation/erasure.md`, with the unsalted `artifact_hash` as the reason (a salt would destroy its purpose: two sightings must give the same value).
- An erased mail that someone forwards again comes back, as an attachment of the new outer mail: erasure holds per event, not per content.
  Name it on `erasure.md`; it goes to the map as an open point.
- Plus what the brief says: the folder itself, the mailbox backups, replies that quote the mail.

## Named behaviour for `docs/reference/mail-mapping.md` (rulings T2-g, Task 2 re-review, Task 5)

State these as facts on the reference page (not as excuses), and put each into the map as an open point under the unit it belongs to:

- alt text of images is dropped (`ignore_images`);
- `html2text` escapes Markdown characters in text;
- an unescaped `<` in HTML can swallow text up to the next `>`;
- malformed address lists map as far as the parser gets;
- opaque-signed S/MIME reads as `no readable body: attachments only`;
- identical mails without a Message-ID (a daily "Backup OK") merge into one event — map;
- a `charset=` label that names a non-text codec makes the mail unreadable (fallback event);
- a bounce's `text/rfc822-headers` part becomes body text;
- a mail with more than 499 attached mails cannot be appended (refused at every run);
- a collision of `variant_key`'s first 64 bits stops the run;
- attachment names: `/` becomes `_`; an empty name, `.` or `..` becomes no name (ruling T4-b).

Also the shapes the code has now (spec §3.2–§3.5 were updated in commit 5735843): `body` is a list with one entry per part (`part`, `charset`, `declared`, `guessed`, `converter`, `replaced`); identity `"body"` is a list of per-part hashes, line endings normalized, also for attachments that travel as lines; `headers` values unfolded; `headers_replaced`; `not_unpacked`; the fallback event `unreadable mail: <exception class>`.
Take every name and wording from the code, not from this list.

## Operations (ruling T4-c)

- Add `ENV MALLOC_MMAP_THRESHOLD_=131072` to the `Dockerfile`, with a comment that states why (without it, peak memory grows with the number of large mails in one run: measured 241/346/383 MiB for 1/3/6 mails on glibc 2.39; glibc caps its dynamic threshold at 32 MiB).
  Measure the peak inside the image (its glibc may differ from the host's) for one mail of about 49 MiB through `map_mail`, or say in the report why you could not and what you measured instead.
- The handoff and the compose consideration name a memory limit of **768 MiB** for the ingest job (the reviewer measured 528 MiB absolute peak for a 49.3 MiB mail: 97 MiB baseline plus 431 MiB).
  If your measurement in the image says otherwise, use your number with headroom and say so.
- `ubuntu-latest` becomes Ubuntu 26 from 2026-10-19: into the map under *Tore und Werkzeuge* (brief).

## Pages that lag (Task 3 and Task 5 reviews)

- `docs/explanation/module-boundaries.md`: the contracts (now eight), the layers contract's new name `Layers: cli, connectors, core beside migrations, storage, contract`, the edge counts with `connectors`, and `WatermarkStore` as a fourth protocol (the page tells of a second and third only). Count from `uv run lint-imports` and the code, not from this line.
- `README.md`: "the eleven commands" → twelve; check every other count there.
- `docs/how-to/cut-a-release.md:87`: example revision `0005_example` collides with the real `0005_watermark` → `0006_example` (as `cli.md` already does).
- `docs/reference/database-schema.md`: `set_at` is supplied by the caller, not "when the row was last written".
- Do NOT edit `CLAUDE.md` — its "six contract names" sentence is the maintainer's decision.

## Not in Task 6

Code comment fixes from the reviews (docstrings in `core/mail.py`, `core/ingest.py`, `core/append.py`, tests) and ruling T1-b (CRLF normalization for `append --text`) go into the fix wave after the final review.
