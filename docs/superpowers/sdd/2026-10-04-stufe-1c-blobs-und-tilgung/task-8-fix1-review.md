### Finding Verdicts
1. Restore guide repeats erasures verbatim — ADDRESSED. restore-from-a-backup.md:158-180: only erasures whose target the log still holds; tip from `anchor` (first field `<id> <hash>`, cli.md:322); `show <id>` hash compared (hash= is the third printed line, cli.py:559; erased events keep their hash); `No event 42` to stderr (cli.py:597, cli.md:351); event_hash_v2 includes id and prev (hashing.py:297-301), so a different event at the same id differs. erase-something.md:28-32 names command, date, id, hash. Blob reach/order true per redact_blob (redact.py:330-337). Map point added. No step left where a careful reader erases the wrong event.
2. Units reach — ADDRESSED. README.md:79-85, erasure.md Units row and new paragraph, erase-something.md:165; consistent with cli.py:410 (`payload={"text": args.text}`).
3. uv warning — ADDRESSED. tutorial line 39 now names it.
4. Backup encryption present tense — ADDRESSED. backup-encryption.md:5, 100 now "plans".
5. Third/fourth migration — ADDRESSED. tutorial line 67 (hash format 2 used; fourth is for attachments).
6. Map pending merge — ADDRESSED. landkarte.md:24-33 wording true before and after the merge.
7. `--blobs` "reads every blob" — ADDRESSED. verify-the-chain.md:92 matches verify.py `_blob_reason` (erased blob only stat'ed); README:52 likewise.
8. Ambiguous "it" — ADDRESSED. erase-something.md:143 reworded.

Map count: awk gives 94 (matches report).

### New Breakage in the Fix Diff
None.

### Out-of-Scope Observations
None.

### Verdict
**Fix round:** All findings addressed, no new Critical/Important breakage
