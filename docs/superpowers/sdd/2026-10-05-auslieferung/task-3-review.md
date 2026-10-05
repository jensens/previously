# Task 3 review: image and smoke test (194acf4..aa5ee8c)

### Spec Compliance

- `Dockerfile`: identical to the brief except for the one line ruling P-1 removes (`against ({ref}`delivery`).` became `against.`). Checked by extracting the brief's code block and diffing.
- `scripts/smoke-image.sh`: byte-identical to the brief's text (diff empty); mode 100755 in the index.
- `.dockerignore`: identical to the brief.
- Base image: the digest in `FROM` is the one named in `global-constraints.md` (`sha256:8e88a074...c96c43a`). Pinned by digest, yes. (`postgres:17` and `rustfs/rustfs:1.0.1` in the script are tags, not digests; the constraint covers only the image base, so this is a note and not a finding.)
- `.dockerignore` against `COPY`: the Dockerfile copies exactly `pyproject.toml` and `uv.lock` from the main context; `.dockerignore` admits exactly those two. The `wheels` bind mount comes from a named context, which `.dockerignore` does not govern. Match.
- Non-root: `USER previously` (uid 1000) comes after the install steps; the smoke test checks `id -u` = 1000, and the implementer measured it red without `USER`.
- Secrets: the bucket secret (`$SECRET`) and the generated identity are never echoed. The identity goes to a file and only the public recipient is printed; the Python snippets that handle the secret have stdout and stderr sent to `/dev/null` or capture only the recipient. The secret does travel in `docker run -e` arguments (visible to `ps` and `docker inspect` on the host while the run lasts); it is a random throwaway for a local network, so this is a note.
- Ruling T3-a: the replacement mutation (`urllib3<2.8.0` over the lock, red with `urllib3==2.7.0`) is reported and measured; the brief's `--upgrade` mutation does not reach the comparison, as the report explains (the build fails earlier without a checkout). Consistent with the ruling.
- Mutations 1 and 3 and the control are reported with their output; shellcheck v0.11.0 clean. I did not rerun them (no containers by instruction).
- Commit trailer: `Assisted-By: Claude Sonnet 5.5`, whereas `global-constraints.md` names `Claude Opus 5.5` (report concern 5 notes it). Not a spec violation of CLAUDE.md (the form `Assisted-By:` is right, no `Co-Authored-By`), but the model name differs from the constraint text.

Comments checked as claims:
- Dockerfile header: "version of the release, from PyPI, without resolving anything again" is true of `--no-deps`; "The image thus holds the package that is on PyPI" is true for the release path only, and the comment at `wheels` says as much. The `({ref}`delivery`)` is absent per P-1; Task 5 must add it.
- Dockerfile `wheels` comment: "an empty directory in the release workflow" describes Task 4, not yet in the tree. Acceptable as a forward statement, but Task 4 must make it true.
- Script header: "PostgreSQL 17 and RustFS 1.0.1" matches `postgres:17` and `rustfs/rustfs:1.0.1`. "removes everything it started, also when a step fails" is true for the two containers and the network, and false for the working directory in one case (see Important 1).
- `tzdata` comment: `uv.lock` has `tzdata` with the marker `sys_platform == 'win32'` under `psycopg`. True.
- `LABEL ...image.source`: matches `repository_url` in `docs/conf.py` and `origin`.

### Issues

**Critical**

None.

**Important**

1. `scripts/smoke-image.sh:17-22, 79-90` (cleanup vs. the identity directory) — the script can fail after every check passed, and leave the working directory behind. The container (uid 1000) runs `os.makedirs('/work/identities')`, so `$WORK/identities` is owned by uid 1000 with mode 755, and the key file inside it is 0600. `chmod 0777 "$WORK"` makes `$WORK` itself deletable, but removing the file inside `identities/` needs write permission on that subdirectory, and a host user other than uid 1000 does not have it. The implementer's host user is uid 1000 (`id -u` here prints 1000), so the green run could not show it. The GitHub-hosted runner user is not uid 1000 (it is 1001), and Task 4 calls this script there. Measured with a stand-in (a 555 subdirectory in a temp dir, same trap and `set -euo pipefail`): the body ran, `rm -rf` printed `Permission denied`, and the script exited 1 (`exit=1`) because the failing last command of `cleanup` becomes the exit status. So on CI the smoke test would go red at the end of a good run, and the key file (a throwaway identity, but still a private key) stays in the runner's temp directory. The header's promise "removes everything it started" is then false. This is not misuse; it is the designed environment. Fix, either: create `$WORK/identities` on the host before the first `run` and `chmod 0777` it (files made by the container in it are then removable); or let `cleanup` finish with `rm -rf "$WORK" || true` after a `docker run --rm -v "$WORK:/work" --entrypoint rm "$IMAGE" -rf /work/identities` step. The first is smaller. Ideally with a test: run the script as a uid other than 1000 and check that `$TMPDIR` holds nothing afterwards and the exit code is 0.

**Minor**

1. `scripts/smoke-image.sh:36-39` — the readiness loop uses `pg_isready` without `-h`, so it asks over the Unix socket. The official `postgres` image starts a temporary socket-only server during first-time initialisation, so `pg_isready` can answer "ready" before the final server, which listens on the network, is up. The script then has several seconds of other work (uv export, pip freeze, bucket loop) before `migrate`, so it usually passes, but on a slow runner it is a source of rare flakes. `pg_isready -h 127.0.0.1` (TCP) closes it. Also, the loop does not fail when PostgreSQL never becomes ready; the later steps fail instead, which is acceptable.
2. `scripts/smoke-image.sh:14` — the trap is installed after `mktemp -d` and `chmod`; a failure between them would leak the directory. Negligible; named only.
3. `scripts/smoke-image.sh` header — the script needs `uv`, `openssl`, `docker` and the repository root as working directory (`uv export`); only the last is stated. Task 4's job has to provide `uv` and `openssl` (report concern 4 says so).
4. Signals: `trap ... EXIT` runs on SIGINT (measured: `cleanup-ran` printed on `timeout -s INT`), but a `docker run --rm` started by `run()` and still running at that moment is not named and is not stopped by `cleanup`; `docker network rm` then fails silently (`|| true`) and the network stays. Arises only from interrupting the script; named, not to be fixed.
5. `Dockerfile` build prints a `useradd` warning (uid 1000 above `SYS_UID_MAX`). Cosmetic; the brief's text is kept.
6. Commit trailer names Sonnet 5.5 where the constraint text names Opus 5.5; decide which is right for the record.

### Assessment

Needs fixes

One Important finding (Important 1). The files match the brief and the pinned digest, `.dockerignore`, non-root user and secret handling are right. The cleanup claim is false on a runner whose uid is not 1000, which is where Task 4 runs it. The fix is a few lines and does not change the interface.
