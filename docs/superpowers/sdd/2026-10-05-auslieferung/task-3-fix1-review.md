# Task 3 fix round 1 review (ea7ceb2..05372db)

Read-only: I read the diff, the script as committed, and `_fetch_to` in `src/previously/cli.py`. I ran no container and could not become another uid, so the points below come from reading and from POSIX rules, not from a run.

### Finding Verdicts

**Important 1 (cleanup fails for a host user other than 1000): closed.**
- `$WORK` comes from `mktemp -d` (host user, 0700), then `chmod 0777`. `$WORK/identities` is now made by the host (`mkdir`) and set to 0777. Both belong to the host user.
- Removing a file needs write permission on its directory, not on the file, and no sticky bit is set on either directory (the sticky bit is on `/tmp`, which only governs `$WORK` itself, owned by the host user). So `rm -rf "$WORK"` as any uid removes every entry the container (uid 1000) put there:
  - the identity file, mode 0600, in `identities/`;
  - `fetched.txt` in `$WORK`;
  - the `.previously-*.part` file that `blob get` makes with `mkstemp` (0600) in `$WORK` if a fetch fails midway.
- Anything else the container writes into `/work`? I found nothing: `append`, `migrate`, `verify`, `anchor` write to the database and the store, and `uv` runs with `UV_CACHE_DIR=/tmp/uv-cache` inside the container. The `os.makedirs('/work/identities', exist_ok=True)` in the Python snippet is now a no-op and harmless.
- A container that created a *directory* inside `$WORK` would again be the problem, but none does.
- This also holds under rootless Docker or user-namespace remapping, where uid 1000 maps to a subuid: the directories are 0777, so write access does not depend on the mapping.
- The implementer's stand-in measured the removal for uid 1001 (old red, new green). That matches what I derive.

**Minor 1 (`pg_isready` without `-h`): closed.**
- The official image runs its first-time initialization server with `listen_addresses=''`, socket only. `-h localhost` makes `pg_isready` use TCP, which only the final server answers. So the loop now waits for the real server.
- The loop still falls through after 60 s without failing. That is pre-existing; the later steps fail instead. Note only.

**Comment check.**
- Comment at `chmod`: "The container runs as uid 1000 and writes into these two directories" is true (`$WORK` for `fetched.txt` and `.part`, `identities` for the key). "owned by the host user" is true for both. "a directory the container made would belong to uid 1000, and `rm -rf` in `cleanup` could not remove the key inside it" is true for a host user other than 1000. The comment does not mention `fetched.txt`; incomplete, not false.
- Comment at `pg_isready`: true as far as I can derive. The claim "the temporary server that the image starts while it initializes (socket only)" matches the `postgres` image's entrypoint behavior. I did not run the image.

### New Breakage

**Important (new, same class as the fixed one): on a host uid other than 1000, `cmp "$WORK/attachment.txt" "$WORK/fetched.txt"` fails with "Permission denied".**
- `_fetch_to` (`src/previously/cli.py:706-745`) writes the content into a `mkstemp` file, which is created with mode 0600, and `os.replace` keeps that mode. Its docstring says so ("`mkstemp` creates it readable by its owner only, and the rename keeps that"). Nothing in the command chmods it afterwards.
- So `fetched.txt` is owned by uid 1000 with mode 0600. The host user on a GitHub runner (1001) cannot read it. `cmp` exits 2, and under `set -e` the script stops after `blob get` has succeeded. `verify --blobs` and `anchor` never run, and the smoke test goes red on CI.
- The fix removes the cleanup failure but leaves this one, and the green run (host uid 1000, owner of the file) cannot show it. The stand-in measured only the removal, never a read as uid 1001. The question "can a host user of any uid remove everything" is yes; the neighbouring question "can it read what it must compare" is no.
- This was already present in `aa5ee8c` and my first review missed it. It surfaces now only because the cleanup failure came first.
- Smallest fix: compare inside a container (`run --entrypoint cmp ...` is not possible without `cmp` in the image, so use `run --entrypoint python "$IMAGE" -c ...` with `filecmp`/bytes compare), or hash it there: `run --entrypoint sha256sum "$IMAGE" fetched.txt` (coreutils is in the Debian-based image) and compare with `$ADDRESS`. A host-side `chmod` is not possible, because the file belongs to uid 1000. A second option, `run --entrypoint chmod "$IMAGE" 0644 /work/fetched.txt`, works too but weakens what the test checks (the 0600 mode is a documented property of `blob get`).
- Measure it this way: run the script as a user other than 1000. A stand-in without containers: create a 0600 file as uid 1000 in a 0777 directory, then `cmp` it as uid 1001. If no second uid is available, say so in the report; do not report the script as proven for CI.

Minor:
- `attachment.txt` is created by the host with the host's umask and read by the container. On a host with umask 077 it would be unreadable for uid 1000. GitHub runners use 022, so no problem there; named only.
- `chmod 0777` on the work directory: the identity file inside is 0600 and owned by uid 1000, so other local users cannot read it (the identity is a throwaway that protects one blob in a bucket that is removed with the run). What they can do is list the directory (the recipient is the file name, public anyway) and delete or replace entries, which would spoil or redirect this run's checks, not leak anything. Any local user with uid 1000 can read the key (on a GitHub-hosted runner there is `runneradmin`, uid 1000, which is root-equivalent anyway). The directory name is random (`mktemp -d`) and exists for seconds to minutes. On a shared, self-hosted runner that is an integrity exposure only for the duration of the run, not a confidentiality one. Acceptable for a smoke test; if one wanted to narrow it, `docker run --user "$(id -u):$(id -g)"` for the host-side steps is not possible because the test is about uid 1000 on purpose.

### Verdict

**Needs fixes.** Both findings are closed as stated and the comments are true, but the fix does not make the script pass for a host user other than 1000: `cmp` cannot read `fetched.txt` (0600, owned by uid 1000), so on the GitHub runner the smoke test fails at that step instead of at the cleanup. One more fix round, for that step only, with the stand-in measurement extended to the read.

Open items:
1. Make the `fetched.txt` comparison independent of the host uid (compare or hash inside the container), and measure it with a second uid or state that none was available.
2. The `chmod 0777` exposure is acceptable and needs no change; consider one sentence in the comment naming `fetched.txt` as a reason `$WORK` itself is open.
