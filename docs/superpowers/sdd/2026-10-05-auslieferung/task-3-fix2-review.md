# Task 3 fix round 2 review (05372db..4d7e4b9)

Read-only: I read the diff, the script as committed (`git show 4d7e4b9:scripts/smoke-image.sh`), the Dockerfile, and grepped `src/` for uid, home and mode handling.
I ran no container and could not become another uid, so the points below come from reading, not from a run of mine.

### Finding Verdict

**Important (`fetched.txt` unreadable for `cmp` under a host uid other than 1000): closed.**

- Every `docker run` that has `$WORK` mounted goes through `run()`, which now has `--user "$(id -u):$(id -g)"`. I counted them: `run()` is the only place that mounts `$WORK`. The other two `docker run` calls start PostgreSQL and RustFS with no mount, and the uid check has no mount either.
- So `blob get` writes `fetched.txt` (via `mkstemp`, mode 0600) as the host user, and `cmp` reads its own file. The same holds for the whole class: the identity key, the `.previously-*.part` file of an aborted fetch, `expected.txt`/`actual.txt` (written by the host anyway). `rm -rf "$WORK"` removes all of it as the owner.
- `$WORK` is `mktemp -d`, 0700, owned by the host user. Before this fix a container as uid 1000 could not have written there at all without the round 1 `chmod 0777`; now the writer and the owner are the same uid, so no mode bits are needed and removing `mkdir`/`chmod 0777` is correct. The exposure I named in round 1 (a world-writable work directory) is gone with it.
- The uid check, `test "$(docker run --rm --entrypoint id "$IMAGE" -u)" = 1000`, has no `--user`, so it still reports the image's default. It needs no environment or mount, so nothing else was lost by leaving `run()`. It is the only step that still measures `USER previously` in the Dockerfile.
- Nothing else assumes uid 1000:
  - Identity file: written by the Python snippet with `os.chmod(path, 0o600)` as the host user, read by `blob get` as the same user. `src/` has no `getuid`, `st_uid`, `getpwuid` or `expanduser`; the only mode logic is the `mkstemp` one already known.
  - `HOME`: for a uid without a passwd entry Docker sets `HOME=/`. The Dockerfile's `--home-dir /app` is therefore not in effect. Nothing in `src/` reads the home directory, and the script's steps ran green under it according to the report.
  - uv: its cache directory is the only thing that would want a writable home. The one `uv` step already sets `UV_CACHE_DIR=/tmp/uv-cache` (`/tmp` is world-writable in the image), so a foreign uid is covered. The other steps use `python` or `previously` and do not run uv.
  - `/app/.venv`: built as root by `uv sync` under the default umask, so readable and executable for any uid. The report says python, pyrage, boto3, `migrate`, `append`, `blob get`, `verify` and `anchor` ran as 1001. Python cannot write `__pycache__` under `/app`; that is silent.
  - `attachment.txt`: written by the host with its own umask, read by the container as the same user. The umask-077 caveat from round 1 is gone.
- Comment above `run()`: true in substance. "can read and remove all of it whatever its uid is" and "`blob get` writes mode 0600" are correct. One imprecision: "and the key could not be removed" described round 1's layout (a directory made by uid 1000 inside a host-owned directory). Without `--user`, and without `chmod 0777`, a container as uid 1000 could not create the directory in a 0700 host-owned `$WORK` in the first place, so it would fail earlier, with a different symptom. The comment names a failure that the pre-fix script no longer had. Not false enough to block; one word to fix on the next touch.
- The claim "as it does in Kubernetes with `runAsUser`" is fair for the image's own files. It says nothing about volumes (`fsGroup`), which a smoke test does not cover.

**The measurement: believable.**

- The setup is described concretely enough to reproduce: a scratch image (`docker:cli` plus bash, openssl, coreutils, diffutils, grep, sed, the `uv` binary), run `--user 1001:1001 --group-add <socket gid>`, the Docker socket mounted, the worktree read-only, a 0777 `TMPDIR` mounted at the same path so the daemon resolves the bind mounts. The script ran inside, unchanged, and `id` printed `uid=1001 gid=1001`. The helper is `inner.sh` in the scratchpad.
- It is a real uid, not a simulation: the inner `id -u` that `run()` passes is 1001, so the daemon starts the image under 1001.
- It has a control: the round 1 version (05372db) in the same setup fails at exactly the step the earlier review predicted, `cmp: …/fetched.txt: Permission denied`, `EXIT=2`. The new version gives `EXIT=0` and an empty `TMPDIR`, so the cleanup is covered as well. That is red before, green after, with the red reproducing the finding, which is what CLAUDE.md asks of an assurance.
- The report is honest about the host-uid-1000 run: it cannot tell the two layouts apart.
- What I cannot check: the figures themselves (I ran nothing). They are consistent with what I derive from reading.

### New Breakage

None that blocks.

Minor, named only:

1. The comment imprecision above ("and the key could not be removed").
2. Rootless Docker or user-namespace remapping: `--user "$(id -u):$(id -g)"` then maps to a subuid, not to the host user, so files written into `$WORK` may not belong to the host user. That is not a regression: before this fix the container ran as uid 1000, which was equally a subuid there, and the script targets a GitHub runner and a developer's ordinary Docker.
3. A host user of uid 0 (root in CI containers) runs the image as root. It works, and it proves less about "not root", but the uid check still covers the default.
4. The already deferred minors in `progress.md` (`trap` after `mktemp`, missing `uv`/`openssl` note in the header, leftover container after an abort) are untouched and not part of this diff.

### Verdict

**Approved.** The finding is closed for the whole class of files the container writes, the uid check still measures the image's default, nothing else in the script or in `src/` depends on uid 1000, and the measurement with a real uid 1001 (control red, fix green, cleanup empty) is described concretely enough to be believed.
Open items: none that blocks. Optionally correct the one clause in the comment above `run()` on the next touch.
