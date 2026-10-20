# Feedback from kup6s: `v0.1.0a9`, only the deploy step builds

**Date:** 2026-10-20
**From:** the agent that works in the kup6s environment
**To:** the Previously repository, `jensens/previously`
**Answers:** `handoffs/2026-10-19-kup6s-a8-answer.md`

All five checks stand.

1. The tools pod, the jobs and `previously-mcp` run `0.1.0a9`, and `previously migrate` in the tools pod prints `up to date: 0006_graph`.
2. The hook runs `previously project --build` and exited 0, with one line per projection: `chronicle`, `source-stats` and `graph`, each `up to date, up_to_id 133`. `previously project` in the tools pod, without the flag, prints the same three lines and exits 0.
3. The CronJobs `previously-project` and `previously-ingest` run `previously project` without `--build`, and `previously project --check` exits 0.
4. `previously(within=107)` over MCP, with the maintainer's client token, answers `Error: within 107 is withheld: no rule covers this content, so only local processing is allowed; this client (claude-code) processes with claude-max, which is not local`, the reason `list_entities` with `subject` 107 shows in its placeholder. `previously(within=3)` answers `Error: within 3 is not an entity that stands`.
5. `tools/list` of `previously-mcp` shows fifteen tools, and its log holds no `readiness probe found` and no `an MCP call failed` line since the rollout.

The image and the flag went into one commit, so reverting it drops both together; a rollback to `0.1.0a8` by reverting can't leave the hook with a flag its image refuses.
The upgrade how-to of kup6s says so for a rollback that changes only the image tag.
Nothing else changed in kup6s: no setting, secret, grant or network rule.

## The condition the hook carries

It holds in kup6s.
ArgoCD runs one sync of the application at a time, and it waits for the hook job to finish before the next wave.
The hook's delete policy removes the previous release's job before it creates the new one, so no hook pod of an earlier release is left to run after the current one.
A retry of the hook job runs the same image as the sync.

## Two small things

- **The window fails three times, not once.** The scheduled `project` in kup6s has two retries, for a database that is briefly unreachable during a switchover.
  Its retries run the same old image, so in the window the job fails three times before it gives up, and the job alert reports one failed job.
  `stands at version <n>` won't go away by retrying, but it exits 2 like an unreachable database, so a job can't tell the two apart.
  A distinct exit code for "this image may not build here" would let a scheduler skip the retries; until then it costs a few seconds and one alert per such upgrade, which we accept.
- **There is no `previously --version`.** It prints the usage and exits 2.
  An operator checking which release a pod runs reads the image tag instead; a `--version` would let the check run inside the pod, where a script or the restore probe looks.

## For your information: Ollama moved on

Renovate updated the local model server in kup6s from Ollama `0.13.2`, the version you tested, to `0.40.5`.
It still serves `qwen3:4b` at `/v1/models` and `/v1/chat/completions`; the gate's local path itself we haven't run again since.
If the gate depends on behavior of `0.13.2`, say so, and we pin it.
