# Handoff to kup6s: the answer to the feedback on `v0.1.0a9`

**Date:** 2026-10-20
**From:** the Previously repository, `jensens/previously`
**To:** the agent that works in the kup6s environment
**Answers:** `handoffs/2026-10-20-kup6s-feedback-a9.md`

This file adds to the earlier handoffs under `docs/superpowers/handoffs/`, which stand as written.
Like them, it says **what** Previously offers or needs, **why**, and **how to recognize that it stands**, and never how to build it in cdk8s.

The release brings no migration, no new setting, no secret, no grant, no network rule and no change of a projection's version.
It answers the two small things of the feedback, and it asks for one measurement.
Nothing here is a requirement, except that the measurement is asked for once.

## The image

The release after `v0.1.0a9`; the maintainer picks its number when they cut it.
Pin its exact version, as for every release until `1.0.0`.
The migration job runs as before and prints `up to date: 0006_graph`.

**It stands when** the tools pod, the jobs and `previously-mcp` run the new version, and `previously migrate` in the tools pod prints `up to date: 0006_graph`.

## Exit code 4: this release's projection isn't built here

**What:** every command that stops because a projection has no state row, or stands at another version than the release declares, exits **4** instead of 2.
That is a plain `previously project` without `--build`, the listings and readers of the graph, `previously mcp` and `previously serve` at their start, and a `previously redact` whose unfinished redaction includes such a projection.
The sentence on standard error is the one it was, such as ``projection graph stands at version 2, and this code declares version 1; the release that is to serve builds it with `previously project --build` ``.
Only the code changed.

**Why:** running such a command again doesn't help until the step that deploys the release has run `previously project --build`, while an unreachable database, a conflict with a concurrent transaction or a rebuild that landed under a catch-up may well be gone by the next try.
With the same code 2 for both, the scheduled `project` in the window of an upgrade fails three times, because its two retries can't tell the cases apart.

**A scheduler may skip its retries on 4.**
That is an option and no requirement: a scheduler that retries on every nonzero code works as before, only with the retries wasted in that window.
Whether to treat 4 specially is kup6s's decision.
Exit codes 2 and 3 stay as they were (3 is for `gate try` alone), so nothing that reads 2 breaks: it simply doesn't see the finding above any more.

**An older image still exits 2.**
Until the scheduled job and the hook run the new image, the same finding exits 2 from them.
So a rule that skips retries on 4 takes effect when the image of the job is this release or later.

**It stands when** a check against a scratch database, never the real one, shows it.
Start a throwaway PostgreSQL, point `PREVIOUSLY_DSN` at it, and run the commands of the new image in turn.
Measured on 2026-10-20 against a fresh PostgreSQL 18 with the code of this release:

```text
$ previously migrate
migrated: (empty) -> 0006_graph
$ previously project
Error: projection chronicle is not built, and this code declares version 3; `previously project --build` builds it
$ previously entities
Error: projection graph is not built, and this code declares version 1; `previously project --build` builds it
$ previously project --build
chronicle       up to date, up_to_id 0
source-stats    up to date, up_to_id 0
graph           up to date, up_to_id 0
$ previously project
chronicle       up to date, up_to_id 0
source-stats    up to date, up_to_id 0
graph           up to date, up_to_id 0
```

The exit codes are 0, 4, 4, 0 and 0.
As the contrast, a wrong password in the DSN ends with `Error: connecting to database … failed: … password authentication failed …` and exit code 2.

## `previously --version`

**What:** `previously --version` prints `previously <version>`, the version of the installed distribution, to standard output and exits 0.
It needs no database and no setting.

**Why:** the check which release a pod runs can run inside the pod, where a script or the restore probe looks, instead of reading the image tag from outside.

**It stands when** `previously --version` in the tools pod prints `previously ` followed by the version of the image tag, and exits 0.
Images up to `v0.1.0a9` print the usage and exit 2.

## Ollama: one measurement instead of a pin

No behavior of Ollama `0.13.2` is known to matter to the gate, so nothing needs pinning.
The local path of the gate was last run against `0.13.2`, and not since the move to `0.40.5`, so this release asks for one run of it.

**What:** run `previously gate try` once, against one event the policy allows to be processed locally, with `PREVIOUSLY_LOCAL_MODEL_URL` set to the local model server, as in the how-to (`docs/how-to/set-a-policy-and-try-a-call.md`), and report the exit code:

```shell
previously gate try EVENT_ID
```

**What the code means:** 0 means that the local server answered, the answer matched the schema of the task, and the call is recorded as an event; nothing needs doing.
Any other code: report the sentence on standard error as it stands, and the code.
A 2 with a sentence about the local server, and the outcome `error` in the recorded call, is the case in which the server didn't answer in the form the gate expects.

**Why:** the call goes through `/v1/chat/completions` with `reasoning_effort` set to `none`; a server that reads either differently from `0.13.2` shows up in this one run, and the sentence says how.

**It stands when** the run's exit code, and the sentence if it isn't 0, are reported back.

## What doesn't change

No new setting, no secret, no grant and no network rule.
No migration, and the versions of the projections stand: `git diff v0.1.0a9 -- src/previously/core/projection/` is empty, and the migrations directory holds the same revisions, the newest `0006_graph`.
The tool list of `previously-mcp` stays at fifteen tools.

## A host without a cluster

A `docker-compose` file changes as little: the image tag.
A cron line that runs `previously project` may skip its retries on exit code 4 as a Kubernetes job may, or retry on every nonzero code as before.
This file considers it and builds nothing for it.

## How to recognize that everything stands

1. The tools pod, the jobs and `previously-mcp` run the new version, and `previously migrate` prints `up to date: 0006_graph`.
2. The hook runs `previously project --build` and exits 0; the scheduled `project` exits 0.
3. `previously --version` in the tools pod prints the version of the image tag.
4. `previously gate try` against one event ran once, and its exit code is reported.
5. `tools/list` of `previously-mcp` still shows fifteen tools.
