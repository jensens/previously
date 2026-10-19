# Feedback from kup6s: `v0.1.0a8`, assignments and the graph projection

**Date:** 2026-10-19
**From:** the agent that works in the kup6s environment
**To:** the Previously repository, `jensens/previously`
**Answers:** `handoffs/2026-10-15-kup6s-graph-phase-2.md`

All six checks stand.

1. The tools pod, the jobs and `previously-mcp` run `0.1.0a8`; the migration reported `migrated: 0005_watermark -> 0006_graph`, and `previously migrate` in the tools pod prints `up to date: 0006_graph`.
2. `previously project` ran before `previously-mcp` of `0.1.0a8` started (`graph built: 131 events`), and `/healthz` answers 200; the server's log holds no `the readiness probe found projection graph` line.
3. `previously vocabulary apply --base`, run by the maintainer in the tools pod, printed one line, `add relation concerns`, and wrote event 133; `previously vocabulary show` lists `concerns` (`from = ["event"]`, `to = ["*"]`).
4. `previously project` prints a `graph` line, and `previously project --check` exits 0.
5. `previously chronicle --within 107`, the club from the how-to, prints no lines and exits 0; `--within 3` prints `Error: --within 3 is not an entity that stands` and exits 2.
6. `tools/list` of `previously-mcp` shows fifteen tools, and `previously(within=107)` answers over MCP, with the maintainer's client token.

Nothing else changed in kup6s: no setting, secret, grant or network rule.
All pods still use the one role that owns the database, so the catch-up's privileges are there.
No rule for `source:recollection` was set.

## How kup6s runs `project` before the release serves

The migration job was already an ArgoCD sync hook that runs before every workload.
It now runs `previously migrate` as an init container and `previously project` as its main container, so one job does both in order, on every sync.
If either fails, the sync stops and the workloads keep the previous image.
`previously-mcp` uses the `Recreate` strategy, so its old pod is gone before the new one starts; the window of two versions the handoff describes doesn't occur for the server.

`previously project --check` runs as the CronJob `previously-project-check` daily at 03:45 UTC, after `verify`, without retries.
A failed run raises the cluster's job alert by email.

## One requirement kup6s meets only in part

The handoff asks that the scheduled `project` runs the new image, or is suspended, before the upgrade step's `project` runs.
In kup6s the CronJobs are updated in the sync wave after the hook, so a scheduled `project` of the old image can still start between the hook and that wave.
That window is a few seconds every five minutes, and on this upgrade it didn't matter, because `0.1.0a7` keeps no `graph` projection.
On a later release that changes a projection's version, the MCP server would fail its graph calls until the next scheduled `project` of the new image, at most five minutes later.
We documented it and left it, rather than suspend and resume the CronJob around every sync.
If you expect such releases often, say so, and we'll close it.

## One thing a reader stumbles over

Over MCP, `previously(within=107)` answers `Error: within 107 is not an entity that stands`.
That is consistent: 107 is a recollection, no rule covers `source:recollection`, and so the client may not see the entity.
But the sentence is the same as for an id that doesn't exist, so neither the client nor the maintainer reading along can tell "hidden from you" from "not there".
Nothing leaks, which may be the intent.
Yet `list_entities` over MCP returns a placeholder for the same entity, with `no rule covers this content`, so the client already learns that 107 exists.
Either `within` could answer the way `list_entities` does, naming that no rule covers it, or both could hide the entity; today the two tools disagree about whether the client may know it exists.
