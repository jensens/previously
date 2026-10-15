# Handoff to kup6s: assignments and the graph projection, the second phase

**Date:** 2026-10-15
**From:** the Previously repository, `jensens/previously`
**To:** the agent that works in the kup6s environment
**Source:** the specification `docs/superpowers/specs/2026-10-14-zuordnungen.md`, phase 2, and the plan `docs/superpowers/plans/2026-10-15-zuordnungen-phase-2.md`

This file adds to the earlier handoffs under `docs/superpowers/handoffs/`, which stand as written.
Like them, it says **what** Previously needs, **why**, and **how to recognize that it stands**, and never how to build it in cdk8s.

The release adds one migration, `0006_graph`, which creates two tables, and one kind of relation, `concerns`, which the maintainer's log doesn't hold yet.
It asks for no new setting and no secret.
It asks two things, which the sections below give with their reasons: `previously project` runs after `previously migrate` and before the new release serves, and the database role of every process that reads the graph may write the projection tables.
It adds the assignment of mails and their units to a project, a matter or an organization, the command `chronicle --within`, an argument `within` of the MCP tool `previously`, and the check `previously project --check`.
The tool list stays at fifteen.

## The image

The release after `v0.1.0a7`; the maintainer picks its number when they cut it.
Pin its exact version, as for every release until `1.0.0`.
Run the migration job before anything else uses the new image, and expect `migrated: 0005_watermark -> 0006_graph`.
The migration creates the tables `p_graph_version` and `p_graph_thread`.
They hold no content, only ids, counts, words of the vocabulary and the period dates of a relation, and the migration only creates them: it reads no event.

**It stands when** the migration job reported `0006_graph`, and `previously migrate` run again in the tools pod prints `up to date: 0006_graph`.

## `previously project` after the migration, before the release serves

**Requirement: `previously project` of the new release runs after `previously migrate` and before the first pod of the new release serves**, on this upgrade, on every later upgrade whose release notes say that a projection's version changed, and on a new database.
A job of the upgrade step after the migration job does it, or an init container of the server that waits for it; how, the environment decides.

**Why:** only `previously project` builds a projection.
The migration `0006_graph` creates the graph projection's tables empty, with no state row, and a reader of this release doesn't build one: it catches up from where the projection stands, and where the projection isn't built at the version its code declares, it fails with a sentence that names `previously project`.
A reader that built instead would put a build as long as the log inside a client's call, and during a rolling update an old pod would rebuild the old version and a new pod the new one, call after call.
Earlier builds of this release let a reader that couldn't use the projection fold the whole log instead; that second way to the graph is gone, because it turned misconfiguration and damage into answers that were right and slow.

**What an operator sees if the step is skipped:**

- `previously serve` and `previously mcp` refuse to start, exit code 2, with `Error: projection graph is not built, and this code declares version 1; ` followed by `` `previously project` builds it ``.
- A server that is already running answers `/healthz` with 503 and the body `Error: the graph projection is not built at this server's version`, and writes one `WARNING` line per probe: `the readiness probe found projection graph not built, and this code declares version 1`.
  So the readiness probe keeps the new pods out of the Service until the projection stands.
- A call that reaches such a server anyway fails with `Error: the call failed inside the server; its log says why, this result cannot`, and the log names the projection.
- The graph listings of the command line exit 2 with the same sentence, and `previously redact` records its redaction and reports it as unfinished, with the advice to run `previously project` and then the same command again.

The build reads the whole log once: milliseconds at the size of a pilot, 3.5 s at 10,000 relations and 35 s at 100,000, measured by the maintainer on 2026-10-15 at commit `22b3dec`.

**It stands when** `previously project` printed a `graph` line that begins with `built:` or `rebuilt:`, or `up to date` where nothing was new, and `/healthz` of every pod of the new release answers 200.

## One step after the image

A step of the operator, once, in the tools pod: the new relation kind.
Which kinds exist is declared in the log, and `concerns` is new in the base vocabulary:

```shell
previously vocabulary apply --base
```

On a log from the first phase it prints one line for `concerns` and nothing else, asks, and writes one event.
It adds the base kinds the log doesn't hold yet and changes nothing that the maintainer adapted.
With nothing to add, it prints `nothing to change`.
The readers catch the event up into the projection by themselves.

**It stands when** `previously vocabulary show` lists `concerns` among the relations.

## A rolling update runs two versions at once

A projection has a version, and only `previously project` builds it at the version its code declares.
The image of `v0.1.0a7` keeps no `graph` projection and reads none, so the update from it meets nothing of this.
Any later release that changes the version of `graph` does.

**Requirement: in such an update, `previously project` of the new release runs before the first new pod serves, as above, and the old pods leave once it has.**
**Why:** from the moment `project` of the new release rebuilt the projection, it stands at a version the old pods don't declare.
They don't rebuild it back, so the two releases don't undo each other's work; they fail their graph calls instead, and their readiness probe answers 503, until they are replaced.
The new pods find the projection at their version, and their probe answers 200 from the start.
The window of failed calls is the time the old pods stay, so a rollout that replaces them promptly keeps it short.

**It stands when** after the rollout only pods of the new release run, every `/healthz` answers 200, and the log of `previously-mcp` shows no `the readiness probe found projection graph` line any more.

## Every reader catches the projection up first

Every graph reader of the command line and every call of `previously-mcp`, `whoami` included, brings the graph projection up to the tip of the log before it reads.
Where nothing is new, that costs two short transactions.
Where much is new, the catch-up does the work inside the call.

**Requirement: the database role of every reader may write the projection tables.**
The catch-up takes the row of `graph` in `projection_state` with `SELECT … FOR UPDATE`, inserts it if it's missing, and inserts, updates and deletes rows of `p_graph_version` and `p_graph_thread`.
So the role of `previously-mcp`, of the tools pod and of any job that reads the graph needs `SELECT`, `INSERT`, `UPDATE` and `DELETE` on those three tables.
**Why:** the projection is kept current by whoever reads, so that no job has to run for an answer to be current.
A role without that access gets no answer from the graph: every call fails, and its reason in the server's log, like the error of a listing on the command line, names the missing privilege and the table, such as `the role of PREVIOUSLY_DSN lacks a privilege on database previously at <host>:<port>: permission denied for table projection_state`.
Until this release's fix round that refusal read `database schema incomplete — previously migrate has not run yet`, and the reader folded the log behind it.
All pods of Previously in kup6s use the one role that owns the database, as the feedback of 2026-10-12 reports, and that role holds all of it.
**It stands when** `previously project` in the tools pod prints a `graph` line, and the log of `previously-mcp` shows no `an MCP call failed` line naming the projection once the rollout has finished.

**Recommended: run `previously project` after a bulk ingest.**
Two catch-ups of one projection take turns at that row lock, batch by batch, and no lock timeout is set.
So while a long catch-up runs, every reader that arrives waits at the lock, takes its own turns, and returns only when the projection has reached the tip.
**Why:** a bulk ingest leaves much to catch up, and the first reader would carry that work while every reader beside it waits.
Measured by the maintainer on 2026-10-15, on an i7-11370H at commit `22b3dec`, a catch-up after one write takes 0.04 s, and the first build of the whole log 3.5 s at 10,000 relations and 35 s at 100,000, which bounds what a catch-up after an ingest can take.
At the size of a pilot, a few hundred statements, it is milliseconds, and the `project` CronJob every few minutes catches up between calls anyway.
Running `previously project` by hand right after the ingest keeps that wait out of the calls of a client.
**It stands when** `previously project` run a second time prints `up to date, up_to_id <id>` on its `graph` line.

**Recommended: `previously project --check` as a scheduled job, like `verify`, with an alarm on exit code `1`.**
Exit `1` means it found a row that differs from what folding the log makes of it, and it prints one line per difference; exit `2` is an error that kept it from checking, as for every command.
**Why:** a reader trusts the projection for which threads a question concerns, so a row that drifted hides a thread from every answer until somebody looks, and nothing else would look.
Two ways out of band are known to make one drift: an approval or an objection forged across threads, and a payload set to null without an erasure; a fault nobody has found yet would be a third.
A row that drifted can hide a thread, never add one, and never releases content.
The check folds the whole log: 1.0 s at 10,000 relations and 10.6 s at 100,000, measured the same day, so daily is enough.
Repair what it reports by rebuilding the projection, as `docs/how-to/rebuild-a-projection.md` says, and report the lines.
**It stands when** the job has run once with exit code `0`.

## What a reader can do with it

`previously chronicle --within N` prints the chronicle of the entity `N` and of everything below it.
`previously project --check` compares every row of the graph projection with what folding the log makes of it, and prints one line per difference.
It exits 0 when nothing differs and 1 when something does.
The projection is disposable: the log is the truth, and a difference is something to report and then to repair by rebuilding the projection.
The MCP tool `previously` takes `within=N`.
Over MCP, an assignment or a part of a bracket counts only where the client may see it, so a client finds less than the maintainer does on the command line, and never more content: the processing policy still decides every event.

## What this release leaves

- **A write still folds the whole log.**
  Writing a relation costs what it cost in the previous release: 0.54 s at 10,000 relations and 6.9 s at 100,000, measured by the maintainer on 2026-10-15 at `22b3dec`.
  Readers are faster; writers are not.
  At the size of a pilot it is milliseconds.
- **`verify` is unchanged** and grows with the square of the edges of an acyclic kind, as the previous handoff says: 3.6 s at 10,000 relations and 130 s at 100,000, measured the same day, fine as a nightly job.
- **Listing everything and `within` over a large bracket are slow at scale.**
  At 100,000 relations `previously entities` takes 3.5 s, `relations --at` 6.8 s, `list_entities` over MCP 5.0 s, and `previously(within=N)` over one of three brackets that share 2,000 of 5,000 assignments 17.5 s, although it returns one page.
  The header, `whoami`, `list_triage` and `chronicle --within` on the command line stay well under a second.
  At the size of a pilot all of it is milliseconds; the map carries what would change it.
- **The gate is untouched.**
  An assignment finds; it releases nothing, and no policy answer changes.

## A host without a cluster

A `docker-compose` file does the same in the same order: change the image tag, run `previously migrate` and then `previously project` with `docker compose run` before the server container starts, then `previously vocabulary apply --base` once.
A server started before `project` refuses to start with the sentence above, and a restart policy brings it up once `project` has run.
A container of `v0.1.0a7` that still runs beside the new one reads no `graph` projection; a container of a later release with another version fails its graph calls until it is replaced, and rebuilds nothing.
The scheduled `project --check` is one more line in the host's cron, beside `verify`.
This file considers it and builds nothing for it.

## How to recognize that everything stands

1. The tools pod, the jobs and `previously-mcp` run the new version, and `previously migrate` prints `up to date: 0006_graph`.
2. `previously project` ran before `previously-mcp` of the new version served, and `/healthz` answers 200.
3. `previously vocabulary show` lists `concerns`.
4. `previously project` prints a `graph` line, and `previously project --check` exits 0.
5. `previously chronicle --within <id>` answers for an entity that stands.
   On a log without assignments, it prints no lines and exits 0.
   With an id that is no entity it prints `Error: --within <id> is not an entity that stands` and exits 2, which also shows that the command runs.
6. `tools/list` of `previously-mcp` still shows fifteen tools, and `previously(within=<id>)` answers over MCP.
