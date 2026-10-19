# Handoff to kup6s: the answer to the feedback on `v0.1.0a8`

**Date:** 2026-10-19
**From:** the Previously repository, `jensens/previously`
**To:** the agent that works in the kup6s environment
**Answers:** `handoffs/2026-10-19-kup6s-feedback-a8.md`

This file adds to the earlier handoffs under `docs/superpowers/handoffs/`, which stand as written, except for the requirement it drops below.
Like them, it says **what** Previously needs, **why**, and **how to recognize that it stands**, and never how to build it in cdk8s.

The release brings no migration, no new setting, no secret and no change of a projection's version.
It changes two behaviors that the feedback pointed at.
`previously project` without a flag no longer builds a projection, in either direction: only `previously project --build`, run by the step that deploys a release, builds.
`previously(within=N)` over MCP names a bracket the client may not see as withheld, as `list_entities` does.

## The image

The release after `v0.1.0a8`; the maintainer picks its number when they cut it.
Pin its exact version, as for every release until `1.0.0`.
The migration job runs as before and prints `up to date: 0006_graph`.

**It stands when** the tools pod, the jobs and `previously-mcp` run the new version, and `previously migrate` in the tools pod prints `up to date: 0006_graph`.

## The deployment step runs `previously project --build`

**Requirement: the step that runs `previously project` before a release serves, the hook in kup6s, runs `previously project --build`, permanently. The scheduled `previously project` stays without the flag.**

**Why:** a plain `previously project` now only catches up, as every reader does.
Where it meets a projection without a state row, or at another version than its release declares, it leaves the projection as it stands, prints one sentence and exits 2.
`--build` is what builds: from scratch on a new database, forward after an upgrade that raises a projection's version, back after a rollback to a release that declares an older one.
At the release's own version it catches up and builds nothing, so the hook can carry it on every sync.
A scheduled run with `--build` would build whenever its image differs from the projection's version, which is what happens in the seconds in which the scheduled job still runs the other image, so the flag must not go there.

**When it has to be there:** this release changes no projection version, so it rolls out with today's hook, whose plain `project` catches up and exits 0.
The flag has to be on the hook before the first release that changes a projection's version, or the hook's `project` exits 2 and the sync stops, and on any new database, whose projections nobody else builds.
Putting it on with the image of this release is simplest.
Images up to `v0.1.0a8` don't know the flag and refuse it as an unknown argument, exit code 2, so the hook can carry it only once its image is this release or later.

What a plain run says where it would have to build:

```text
Error: projection graph stands at version 2, and this code declares version 1; the release that is to serve builds it with `previously project --build`
Error: projection chronicle is not built, and this code declares version 3; `previously project --build` builds it
```

**It stands when** the hook's `previously project --build` prints one line per projection and exits 0, `/healthz` of `previously-mcp` answers 200 after the sync, and the scheduled `project` runs without `--build`.

## The scheduled `project` no longer has to move before the hook

**Dropped: the requirement that the scheduled `previously project` runs the new image, or is suspended, before the upgrade step's `previously project` runs** (`handoffs/2026-10-15-kup6s-graph-phase-2.md`, the section on a rolling update), and that in both directions, an upgrade and a rollback.

**Why:** the feedback found the window it guarded against: the CronJobs move to the new image in the sync wave after the hook, so a scheduled `project` of the other image can start in the seconds between.
Until `v0.1.0a8` that run built the projection back to its own version, and the server failed its graph calls until the next scheduled run of the new image.
In a rollback it is the same the other way round: a scheduled run of the newer image would build forward again what the rollback's hook built back, and every later scheduled run of the older image would then fail to read it, so the server would stay unready until somebody stepped in.
From this release on, the scheduled run builds in neither direction: in that window it exits 2 once and leaves the projection to the hook.
Its job alert may report that one failed run; the next scheduled run, of the image the sync deployed, catches up and exits 0.

**The protection holds only once both sides are this release or later.**
An image up to `v0.1.0a8` still builds with a plain `project`, in either direction.
The upgrade to this release has `v0.1.0a8` as its old image, but changes no projection version, so its scheduled run has nothing to build back on this upgrade.
A rollback from this release to `v0.1.0a8` or earlier leaves that image's scheduled `project` building as it always did.

**It stands when** after the next upgrade that changes a projection's version, a scheduled `project` of the old image failed at most once in the window, every scheduled run of the new image exits 0, and `/healthz` answers 200 from the end of the rollout on.

## The condition the hook carries, and the risk

The hook's `project --build` decides which version the projection stands at, so it has to be the hook of the release being deployed, and only that one.
That holds when one deployment serves the database, and no leftover or retried hook pod of an earlier release runs after the current sync's hook.
If such a pod of an older release runs anyway, it builds the projection back without a word, and the newer server answers 503 on `/healthz` until the hook of the newer release runs again, at the next sync or by hand.
Nothing heals that by itself, because the scheduled `project` no longer builds.
A scheduled `project` that keeps exiting 2 with `stands at version <n>` after a finished sync, and a 503 with `the graph projection is not built at this server's version`, are the sign; `previously project --build` of the release meant to serve, in the tools pod, ends it.

## `within` names a withheld bracket as `list_entities` does

The feedback found that `previously(within=107)` answered `Error: within 107 is not an entity that stands` while `list_entities` showed a placeholder for 107, `no rule covers this content`, so the two tools disagreed about whether the client may know that the entity exists.
The maintainer wanted the same behavior in both, and `list_entities` keeps its placeholder: it shows one under every filter alike, so that a client learns neither the state nor the kind of what it may not see.
`within` now follows it.
Where `list_entities` shows a placeholder for an id, `within` answers with the same reason, cut where the placeholder cuts it:

```text
Error: within 107 is withheld: no rule covers this content, so only local processing is allowed; this client (<client>) processes with <processor>, which is not local
```

Nothing of the bracket is read; the refusal is the one sentence.
Where `list_entities` shows no entity, such as for an event, a relation or an unknown id, `within` still answers `is not an entity that stands`.
The tool list and the tool descriptions don't change.
No requirement follows from it; a rule for `source:recollection` would let the client see entity 107, and its chronicle with it, in both tools at once.

**It stands when** `previously(within=107)` over MCP, with the maintainer's client token, answers `Error: within 107 is withheld: ` followed by the reason that `list_entities` with `subject` 107 shows in its placeholder.

## The role every pod uses

The feedback reports that all pods still use the one role that owns the database.
This release asks for no privilege beyond those of the earlier handoffs, so nothing follows from it.

## A host without a cluster

A `docker-compose` file changes as little: the image tag, and `docker compose run previously migrate` and `docker compose run previously project --build` before the server starts, on every deployment.
The cron line that runs `previously project` stays without the flag; a run of it during a deployment fails once and leaves the projection to the deployment.
This file considers it and builds nothing for it.

## How to recognize that everything stands

1. The tools pod, the jobs and `previously-mcp` run the new version, and `previously migrate` prints `up to date: 0006_graph`.
2. The hook runs `previously project --build` and exits 0; `previously project` in the tools pod, without the flag, prints one line per projection and exits 0.
3. The CronJob `previously project` runs without `--build`, and `previously project --check` exits 0.
4. `previously(within=107)` over MCP answers `Error: within 107 is withheld: ` and the reason of the placeholder `list_entities` shows for 107; `previously(within=3)` still answers `Error: within 3 is not an entity that stands`, if 3 is an event.
5. `tools/list` of `previously-mcp` still shows fifteen tools.
