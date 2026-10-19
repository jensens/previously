# Handoff to kup6s: the answer to the feedback on `v0.1.0a8`

**Date:** 2026-10-19
**From:** the Previously repository, `jensens/previously`
**To:** the agent that works in the kup6s environment
**Answers:** `handoffs/2026-10-19-kup6s-feedback-a8.md`

This file adds to the earlier handoffs under `docs/superpowers/handoffs/`, which stand as written, except for the one requirement it drops below.
Like them, it says **what** Previously needs, **why**, and **how to recognize that it stands**, and never how to build it in cdk8s.

The release brings no migration, no new setting, no secret and no change of a projection's version.
It changes two behaviors that the feedback pointed at: `previously project` no longer builds a projection back to an older version unless asked, and `previously(within=N)` over MCP names a bracket the client may not see as withheld, as `list_entities` does.

## The image

The release after `v0.1.0a8`; the maintainer picks its number when they cut it.
Pin its exact version, as for every release until `1.0.0`.
The migration job runs as before and prints `up to date: 0006_graph`.

**It stands when** the tools pod, the jobs and `previously-mcp` run the new version, and `previously migrate` in the tools pod prints `up to date: 0006_graph`.

## The scheduled `project` no longer has to move before the upgrade step

**Dropped: the requirement that the scheduled `previously project` runs the new image, or is suspended, before the upgrade step's `previously project` runs** (`handoffs/2026-10-15-kup6s-graph-phase-2.md`, the section on a rolling update).

**Why:** the feedback found the window it guarded against: the CronJobs move to the new image in the sync wave after the hook, so a scheduled `project` of the old image can start in the seconds between.
Until `v0.1.0a8`, that run built the projection back to the old version, and the new server failed its graph calls until the next scheduled run of the new image.
From this release on, a `project` that meets a projection at a newer version than its own leaves the projection as it stands, its tables and its state row, and exits 2.
So the window costs nothing but one failed run, and moving or suspending the CronJob around every sync isn't needed.

That protection holds from the first upgrade *after* this release.
The upgrade to this release still has `v0.1.0a8` as its old image, whose `project` builds back as before; it changes no projection version, so there is nothing for it to build back on this upgrade.

**What a refused run looks like:** the job's `previously project` prints the lines of the projections before the newer one, and on standard error one sentence, such as:

```text
Error: projection graph stands at version 2, newer than this release's version 1; it was left as it stands, and a rollback to this release runs `previously project --build-back`
```

It exits 2, so the job run counts as failed, and the cluster's job alert may report it.
One such run in the window of an upgrade is expected; the next scheduled run, of the new image, catches up as usual.
A refused run that repeats means that an old image keeps running `project` against the database, and that's worth a look.

**It stands when** after an upgrade that changes a projection's version, every scheduled `project` of the new image exits 0, and `/healthz` of `previously-mcp` answers 200 throughout, apart from the one window the release's own rollout causes.

## A rollback runs `previously project --build-back`

**Requirement: a rollback to a release that has the flag runs that release's `previously project --build-back` before it serves.**
**Why:** the older release's plain `project` now refuses the newer projection, so the step back has to be asked for.
Building back is right in a rollback and wrong in the window of an upgrade, and the two look the same from inside the process; only the operator knows which it is.
`--build-back` permits the step back and forces nothing: at the release's own version or an older one it does what a plain `project` does, so a step that carries it can run on every sync.

So the flag may stand for good on the `project` of the step that runs before a release serves, the hook in kup6s, because the release that step runs is by definition the one about to serve; then a rollback needs no step of its own.
It must not stand on the scheduled `project`: a scheduled run of the old image with `--build-back` would build back in exactly the window this release closes.
Releases up to `v0.1.0a8` don't know the flag and refuse it as an unknown argument, exit code 2; their plain `project` builds back by itself.
So the hook can carry the flag once its image is the release after `v0.1.0a8` or later, and not before.

**It stands when** a rollback's `project` printed a line that begins with `rebuilt: version <newer> -> <older>` for each projection whose version the rollback lowers, and `/healthz` answers 200 afterwards.

## `within` names a withheld bracket as `list_entities` does

The feedback found that `previously(within=107)` answered `Error: within 107 is not an entity that stands` while `list_entities` showed a placeholder for 107, `no rule covers this content`, so the two tools disagreed about whether the client may know that the entity exists.
The maintainer wanted the same behavior in both, and `list_entities` keeps its placeholder: it shows one under every filter alike, so that a client learns neither the state nor the kind of what it may not see.
`within` now follows it.
Where `list_entities` shows a placeholder for an id, `within` answers with the same reason:

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

A `docker-compose` file changes as little: the image tag, and `previously migrate` and `previously project` with `docker compose run` before the server starts, as before.
A cron line that runs `previously project` of an old image during an upgrade fails once and leaves the projection to the new one.
A rollback runs `docker compose run previously project --build-back` with the older image before its server starts.
This file considers it and builds nothing for it.

## How to recognize that everything stands

1. The tools pod, the jobs and `previously-mcp` run the new version, and `previously migrate` prints `up to date: 0006_graph`.
2. `previously project` in the tools pod exits 0, and `previously project --build-back` there prints the same lines, since every projection stands at this release's version.
3. `previously project --check` exits 0.
4. `previously(within=107)` over MCP answers `Error: within 107 is withheld: ` and the reason of the placeholder `list_entities` shows for 107; `previously(within=3)` still answers `Error: within 3 is not an entity that stands`, if 3 is an event.
5. `tools/list` of `previously-mcp` still shows fifteen tools.
