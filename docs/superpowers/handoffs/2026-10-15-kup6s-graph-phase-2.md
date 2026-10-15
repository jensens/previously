# Handoff to kup6s: assignments and the graph projection, the second phase

**Date:** 2026-10-15
**From:** the Previously repository, `jensens/previously`
**To:** the agent that works in the kup6s environment
**Source:** the specification `docs/superpowers/specs/2026-10-14-zuordnungen.md`, phase 2, and the plan `docs/superpowers/plans/2026-10-15-zuordnungen-phase-2.md`

This file adds to the earlier handoffs under `docs/superpowers/handoffs/`, which stand as written.
Like them, it says **what** Previously needs, **why**, and **how to recognize that it stands**, and never how to build it in cdk8s.

The release adds one migration, `0006_graph`, which creates two tables, and one kind of relation, `concerns`, which the maintainer's log doesn't hold yet.
It asks for no new setting and no secret.
It asks one thing of the database role of every process that reads the graph, which the section on readers below gives with its reason: write access to the projection tables.
It adds the assignment of mails and their units to a project, a matter or an organization, the command `chronicle --within`, an argument `within` of the MCP tool `previously`, and the check `previously project --check`.
The tool list stays at fifteen.

## The image

The release after `v0.1.0a7`; the maintainer picks its number when they cut it.
Pin its exact version, as for every release until `1.0.0`.
Run the migration job before anything else uses the new image, and expect `migrated: 0005_watermark -> 0006_graph`.
The migration creates the tables `p_graph_version` and `p_graph_thread`.
They hold no content, only ids, counts, words of the vocabulary and the period dates of a relation, and the migration only creates them: it reads no event.

**It stands when** the migration job reported `0006_graph`, and `previously migrate` run again in the tools pod prints `up to date: 0006_graph`.

## Two steps after the image

Both are steps of the operator, once, in the tools pod, in this order.

First, the new relation kind.
Which kinds exist is declared in the log, and `concerns` is new in the base vocabulary:

```shell
previously vocabulary apply --base
```

On a log from the first phase it prints one line for `concerns` and nothing else, asks, and writes one event.
It adds the base kinds the log doesn't hold yet and changes nothing that the maintainer adapted.
With nothing to add, it prints `nothing to change`.

Second, the projection.
Readers bring the graph projection up to date by themselves before they read, so this step is not required for correctness.
It makes the first reader not pay for building it inside a call:

```shell
previously project
```

It prints one line per projection and a third line, `graph`, which says `built:` with the number of events on the first run.
If a reader built the projection first, the line says `caught up:` where events arrived since, and `up to date, up_to_id <id>` where none did.
The build reads the whole log once.
At the size of a pilot, a few hundred statements, that is milliseconds.

**They stand when** `previously vocabulary show` lists `concerns` among the relations, and `previously project` prints a `graph` line, `up to date, up_to_id <id>` when you run it a second time.

## A rolling update runs two versions at once

A projection has a version, and a reader whose code declares another version rebuilds it.
Two images that both keep the projection `graph` at different versions, running side by side, rebuild it for each other.
The image of `v0.1.0a7` keeps no `graph` projection, so an update from it doesn't start that exchange by itself.
It starts with any later release that changes the version of `graph`, and with a pod of an intermediate build, which is why the advice stands for every update from here on.

What the readers do while it happens is correct and slower.
A reader checks, in the snapshot it reads from, that the projection stands where its own catch-up left it.
Where it doesn't, or where the catch-up fails, the reader folds the log for that one call, as the previous release did for every call, and writes one warning line to the server's log.
The answer is never empty, never half-built and never an error.

So: finish the rollout, so that only one version runs, then run `previously project` once.
Warning lines in the log of `previously-mcp` during the rollout are the expected sign, not a fault.
Lines that continue after the rollout has finished are worth a report.

## Every reader catches the projection up first

Every graph reader of the command line and every call of `previously-mcp`, `whoami` included, brings the graph projection up to the tip of the log before it reads.
Where nothing is new, that costs two short transactions.
Where much is new, the catch-up does the work inside the call.

**Requirement: the database role of every reader may write the projection tables.**
The catch-up takes the row of `graph` in `projection_state` with `SELECT … FOR UPDATE`, inserts it if it's missing, and inserts, updates and deletes rows of `p_graph_version` and `p_graph_thread`.
So the role of `previously-mcp`, of the tools pod and of any job that reads the graph needs `SELECT`, `INSERT`, `UPDATE` and `DELETE` on those three tables.
**Why:** the projection is kept current by whoever reads, so that no job has to run for an answer to be current.
A role without that access gets correct answers and slow ones: every call fails its catch-up, folds the whole log as the previous release did, and writes one warning line to the server's log.
That line then names `database schema incomplete`, misleadingly: the storage layer says so for every refusal in the class a missing privilege belongs to, and the map carries it as an open point.
All pods of Previously in kup6s use the one role that owns the database, as the feedback of 2026-10-12 reports, and that role holds all of it.
**It stands when** `previously project` in the tools pod prints a `graph` line, and the log of `previously-mcp` shows no line with `the graph projection could not be caught up` once the rollout has finished.

**Run `previously project` after an upgrade and after a bulk ingest.**
Two catch-ups of one projection take turns at that row lock, batch by batch, and no lock timeout is set.
So while a long catch-up runs, every reader that arrives waits at the lock, takes its own turns, and returns only when the projection has reached the tip.
**Why:** a release that changes the version of `graph` rebuilds the projection on its first catch-up, and a bulk ingest leaves much to catch up; either way the first reader would carry that work and every reader beside it would wait.
Measured by the maintainer on 2026-10-15, on an i7-11370H at commit `22b3dec`, a first build takes 3.5 s at 10,000 relations and 35 s at 100,000, while a catch-up after one write takes 0.04 s.
At the size of a pilot, a few hundred statements, it is milliseconds, and the `project` CronJob every few minutes catches up between calls anyway.
Running `previously project` by hand right after the step that brought the new events or the new version keeps that wait out of the calls of a client.
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

A `docker-compose` file does the same in the same order: change the image tag, run `previously migrate`, run `previously vocabulary apply --base` and then `previously project` once with `docker compose run` or `docker compose exec`.
A container of `v0.1.0a7` that still runs beside the new one rebuilds nothing, since it keeps no `graph` projection.
A container of an intermediate build would, so stop that one before you run `project`, as the section on rolling updates says.
The scheduled `project --check` is one more line in the host's cron, beside `verify`.
This file considers it and builds nothing for it.

## How to recognize that everything stands

1. The tools pod, the jobs and `previously-mcp` run the new version, and `previously migrate` prints `up to date: 0006_graph`.
2. `previously vocabulary show` lists `concerns`.
3. `previously project` prints a `graph` line, and `previously project --check` exits 0.
4. `previously chronicle --within <id>` answers for an entity that stands.
   On a log without assignments, it prints no lines and exits 0.
   With an id that is no entity it prints `Error: --within <id> is not an entity that stands` and exits 2, which also shows that the command runs.
5. `tools/list` of `previously-mcp` still shows fifteen tools, and `previously(within=<id>)` answers over MCP.
