# Final review: documentation package (fd3e17f..42425e7)

**Verdict: Ready after fixes.** 0 Critical, 3 Important, 10 Minor.

The pages are accurate to an unusual degree.
Every name, payload key, wording and setting I checked against the code holds.
The typed output is real: I reproduced it, and recomputed the hashes it quotes.
I found three problems, and they share one shape: a page tells its reader to act in a way that leaves something out.
The erasure list for a mail is incomplete.
The handoff's alarm rule misses the one failure its own memory limit invites.
Two pages promise a complete list of errors that `cli.md` does not have.

## What was measured (all read-only; scratch in the session scratchpad)

- **How-to spot-check, with containers.**
  I ran a scratch pytest file against the suite's own fixtures (`imap` and `blobs` from `tests/test_cli.py`: GreenMail, PostgreSQL and RustFS, removed afterward).
  It ran `ingest imap` twice, then `project`, `chronicle --since 2026-10-06T00:00:00+00:00`, `redact event 4` and `redact event 5`.
  The output matches `ingest-a-mail-folder.md:48-75` and `:128-134` byte for byte, including the shared blob `90f565d1…`.
  It also showed something the page doesn't say: the raw mail of event 4 (`911ba009…`, 1113 bytes) holds event 5 entire (see I1).
- **Recomputed artifact hashes.**
  Computed with `artifact_hash_of`, the hashes quoted in `attach-and-fetch-a-file.md` (`8afe5fdf…`), the tutorial (`dc61469d…`) and `cli.md` (`f20cefad…`) all match.
  The retyped `show` blocks therefore come from current code.
- **The tutorial's test block.**
  The dots for each file equal `pytest --collect-only`, file by file, 1045 in all.
  `Resolved 110 packages` matches the `[[package]]` entries in `uv.lock`.
- **`html2text` 2025.4.15 with the module's settings.**
  `<br>`, `**`, `_`, links, blockquote, the table (`a| b` / `---|---`), `1\. Punkt`, `a<b and c>d` → `a**d`, and the dropped alt text all hold as `mail-mapping.md:84-93` states them.
  `charset=base64` gives `unreadable mail: LookupError`, as the map says.
- **`lint-imports`.**
  `Contracts: 8 kept, 0 broken`, and every contract name is as `module-boundaries.md` quotes it.
  The edges counted by grep come to 10 of the 14 the layer order permits, and the 4 missing ones are as named; 8 arrows leave the package.
- **Paragraph signs.**
  `grep -rn "§" src tests | grep -v "frozen design record"` prints nothing, and the 15 lines in 7 files remain, as `design-records.md` says.
- **The map.**
  The command from `CLAUDE.md` counts **149** open points, against 120 at `fd3e17f`.
  All eleven points of spec §11 are present, each under the unit the brief names.
  So is every named item of the addendum: the eleven behaviors, the `ubuntu-latest` note, the erased mail forwarded again, and the "six contract names" note for the maintainer.
  The four struck items each name their commit.
- `tests/test_docs_references.py` and `tests/test_docs_typed_output.py`: 11 passed.

Items already queued for the fix wave in `progress.md` are not repeated here.
These are the `artifact-identity` → `connectors` pointers, "five modules" in `contract/store.py`, and the map's points on the PyPI name and Bedingung 8.

## Important

### I1: Erasing a mail leaves its variants, and the mail that carried it, in the log and the bucket

`docs/how-to/ingest-a-mail-folder.md:112-159` (also `docs/explanation/erasure.md:199-211`, `docs/how-to/erase-something.md:18-19`)

The how-to's list of "erase these as well" has three gaps, and a reader who follows it leaves the content behind.

1. **Variants.**
   A mail under a known Message-ID with other content becomes an event of its own under `<Message-ID>#<16 hex>`.
   That event has its own raw-mail blob and its own units, which hold mostly the same subject and text.
   The list never mentions it.
   It can be found with `payload ->> 'variant_of' = '<message-id>'`, and for a variant, in the other direction, through the key before `#`.
2. **The mail it lies inside.**
   A mail that came in as an attachment, event 5 in the page's own example, is held byte for byte in two places.
   One is the attachment blob of the outer mail.
   The other is the outer mail's **raw-mail blob**.
   Measured: after `redact event 5` alone, the outer event 4 still holds `911ba009…` (1113 bytes), which contains the whole invoice mail.
   `redact` names only the shared attachment blob, and only on standard error, so nothing points at the raw mail.
   The page covers "every mail inside it" and "an erased mail forwarded again" (`:158-159`), but not a mail that was already forwarded in when it gets erased.
3. **Depth.**
   The `forwarded_in` query (`:122-124`) finds one level.
   A mail inside the inner one names the inner key, and the query has to be repeated down to depth 5.

**Suggested fix:**
Add two bullets to *Erase a mail*: "Its variants", with the `variant_of` query, and "The mail it was forwarded in", with `forwarded_in` read from the event's own payload, noting that the outer mail's raw mail holds it.
Add one sentence: repeat the `forwarded_in` query for each mail found.
Mention the variants in the mail bullet of `erase-something.md`.
On `erasure.md`, extend *An erasure holds for the event, not for the content* with one sentence: the same content stands in every event whose raw mail or attachment holds it, a variant or a forwarding mail.
Put this into the map under *Tilgung*: no command finds them.

### I2: The handoff's alarm rule misses an OOM kill, a crash and a stop

`docs/superpowers/handoffs/2026-10-06-kup6s-ingest.md:94-95`

The handoff says the job "returns `2` on any error" and tells the reader to **"Alarm on `2`"**.
That is false for the failures this handoff makes likely.
The kernel kills a container that goes over the 768 MiB limit set at `:107`, which is exit `137`.
An exception that neither `PreviouslyError` nor `StorageError` covers ends in a traceback and exit `1`; `cli.py` lets foreign exceptions through on purpose (`main`, the comment at the `except`).
A deadline or a stop gives `143` (`:103`).
An agent that wires the alarm exactly as written stays silent on all three.
The first handoff has the right rule for its nightly check: "an alarm on any exit code but `0`" (`2026-10-05-kup6s-delivery.md:216`).

**Suggested fix:**
"**Alarm on any exit code but `0`**, a failed Job.
`2` is Previously's own refusal, with one sentence on standard error.
Anything else, such as `137` for the memory limit, is the platform's."
Keep "a variant is no error and returns `0`".

### I3: `cli.md` lacks errors that two pages say it lists

`docs/how-to/ingest-a-mail-folder.md:92` ("{ref}`cli-reference` lists every error") and `docs/superpowers/handoffs/2026-10-06-kup6s-ingest.md:96` ("`docs/reference/cli.md` lists every sentence") make that promise.
`docs/reference/cli.md:233-240` and the exit table at `:56` don't keep it.

These sentences are in the code and on no page that either claim points to:

- `connectors/imap.py:167-169`: `the IMAP server … names no UIDVALIDITY for the folder '…'`
- `connectors/imap.py:199-202`: `the IMAP server … gave uid N the INTERNALDATE '…', which is not a date`
- `connectors/imap.py:213`, with `the search in the folder '…'` and `to fetch uid N from the folder '…'`; only the open-folder form is quoted
- `connectors/imap.py:236-238`: `the IMAP server … refused a command: …`
- The two refusals of the log, which recur **at every run** until the mail leaves the folder.
  One is `ArtifactChanged` (`email/<key> is known with another content (artifact … ≠ …)`), for a variant key that is already held.
  The other is `BatchTooLarge` (`501 events in one transaction, 500 are allowed — …`).
  `mail-mapping.md` describes both, but the `ingest` row of the exit table (`cli.md:56`) and the error list leave them out.
  For a handoff reader they are the two errors that will never clear on their own.

**Suggested fix:**
Add the five sentences to the error block in `cli.md`.
Add "the log refused the batch: a mail with more than 500 events, or a variant key that is already held with other content" to the `2` column of the `ingest` row, with a pointer to {ref}`mail-mapping`.
Alternatively, soften both claims to "lists the errors".
The first fix is better, because the handoff's reader acts on these sentences.

## Minor

1. **`docs/reference/mail-mapping.md:233`.**
   "HTML only | Converted; see *HTML*." points to a section that doesn't exist.
   The section is *Text from markup*.
2. **`docs/explanation/connectors.md:77`.**
   "So the connector decides what counts, and writes it on its reference page" contradicts `:13-16`, where `core.mail` maps and the connector never sees the result.
   It also contradicts `:80` ("`core.mail` takes the mail apart itself").
   Suggest "So whoever maps a source decides what counts…".
3. **`docs/explanation/erasure.md:119`.**
   "{ref}`connectors` explains why each of the three is where it is."
   `connectors.md` explains the raw mail as a blob and the unsalted hash, but not why the subject stands in `headers`.
   Point to {ref}`mail-mapping` for *where*, or narrow the claim.
4. **`docs/reference/cli.md:186`.**
   The `ingest` section points at {ref}`artifact-identity` and never at {ref}`mail-mapping` or {ref}`connectors`, which say what a mail turns into.
   Add the pointer.
5. **`docs/how-to/ingest-a-mail-folder.md:37` with `:99`.** Name only; it matters only under misuse.
   The shell block writes `PREVIOUSLY_IMAP_FOLDER="Kunde Müller"`.
   `docker run --env-file` takes values literally, quotes included, so a copied line would look for a folder named with quotes.
   One clause fixes it: "without quotes".
6. **Handoff `:85`.**
   "Run them as two containers of the job, `ingest` first" is not something a pod does: its regular containers start together, and an order needs an init container.
   The `/bin/sh` variant also needs the entrypoint overridden (`ENTRYPOINT ["previously"]`).
   With `sh` as process 1, `SIGTERM` doesn't reach `previously`, so the `143` of `:103` doesn't hold; nothing is lost either way.
   Suggest "`ingest` as an init container, or one shell with `exec` before the last command".
7. **Handoff `:111-115`.**
   The text says the measurements ran "with `--memory 768m`, two runs each", but Task 6's report says one of the two runs of 1 × 49.5 MiB ran under `--memory 512m`.
   Say so, or drop that run from the row.
8. **Handoff `:120`.**
   "so the numbers include the temporary file": only the `memory.peak` column includes a tmpfs; the resident peak (VmHWM) does not.
   Say which column.
9. **Handoff `:161`.**
   "`appended` equal to … the mails, plus one for each mail attached as a mail" ignores copies in the folder, which count as known, and the depth limit.
   Make it "at most", or "minus copies".
10. **Small wording and spelling.**
    The password claim is in `ingest-a-mail-folder.md:14`, handoff `:39` and `configuration.md`.
    It says "the IMAP login can't carry any other [character than ASCII]", but that limit is Python's `imaplib`, which writes the login as ASCII.
    The protocol itself can carry 8-bit bytes in a literal.
    "`previously` can't send any other" is accurate; the code's message has the same wording and belongs in the fix wave.
    On spelling, "travelled" in `connectors.md:78` and `mail-mapping.md:111` should be "traveled" in American English, and "afterwards" in handoff `:143` should be "afterward".

## Checked and holding (no finding)

- **`mail-mapping.md`.**
  Every row checked against `core/mail.py` and `core/ingest.py`: the fields of the event; the three sentences and the rule for encryption; body-part selection; the character-set table, including the `us-ascii` and unknown-label paths; the identity document and the LF rule; channel roles; blob names; the payload and body-entry tables, which a test holds; depth 5 and `not_unpacked`; the fallback event and its payload; `forwarded_in` as rewritten for a variant outer mail; the cases table.
  The batch refusal is quoted exactly.
- **`connectors.md`.**
  Explanation only.
  The 2^32 figure ("about four billion") is right for a 64-bit birthday bound.
  `EXAMINE` plus `BODY.PEEK[]` matches the code.
- **`cli.md` and `configuration.md`.**
  The order the settings are read in, the port refusal, thirteen variables, the watermark name without the port, modified UTF-7, the output line, the variant notice, the 60 s timeout, and the quoted error sentences that are present.
- **`database-schema.md`, `module-boundaries.md` and `design-records.md`.**
  Counts and names hold: eight tables, `set_at` from the caller, `0005_watermark`, eight contracts, the two methods of `WatermarkStore`, `Connector` with `name` and `fetch`, eight frozen records.
- **Erasure.**
  `redact event`, not `redact units`, with the three reasons.
  Folder, mailbox backups, quoting replies and re-forwarded mail are stated as limits on `erasure.md`, the explanation, and as steps on the how-to.
  The quadrants are right.
- **The handoff otherwise.**
  It covers what someone holding only the image needs: the CronJob and its schedule, `Forbid`, a secret of its own with the five settings, and DSN, bucket and recipient by reference to the first handoff's table.
  It also covers port 993 and DNS out, a Mailu user of its own, 768 MiB with the measurement and its reasons, a writable `/tmp`, TLS and `SSL_CERT_FILE`, the first ingest in the cluster, and how to recognize that it stands.
  It names no real host, user or secret, and it doesn't prescribe cdk8s.
- **docker-compose.**
  It is considered in spec §6 and given as a cron line with `docker run --memory 768m` and `flock` on the how-to.
- **Dockerfile.**
  `ENV MALLOC_MMAP_THRESHOLD_=131072`, and its comment's figures (241/346/383 and 240/241/241 MiB on the host; 336/360/361 and 335–336 MiB in the image; 529–533 MiB for 49.5 MiB) agree with the report and the handoff.
- **Indexes and labels.**
  `connectors`, `mail-mapping` and `ingest-a-mail-folder` are in their toctrees and on `docs/index.md`.
  README says twelve commands, eight records and one connector.
