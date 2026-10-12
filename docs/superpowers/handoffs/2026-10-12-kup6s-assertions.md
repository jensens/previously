# Handoff to kup6s: assertions, a key for the MCP server, and the ingest's new line

**Date:** 2026-10-12
**From:** the Previously repository, `jensens/previously`
**To:** the agent that works in the kup6s environment
**Source:** the specification `docs/superpowers/specs/2026-10-12-pilot-feststellungen.md`, §10 (German, frozen), and the merge of PR #16, which reads one or more IMAP folders in one run

This file adds to the handoffs of 2026-10-05, 2026-10-06, 2026-10-09 and 2026-10-11 under `docs/superpowers/handoffs/`, which stand as written apart from what the handoff of the settings, `docs/superpowers/handoffs/2026-10-11-kup6s-settings.md`, renamed.
Like them, it says **what** Previously needs, **why**, and **how to recognize that it stands**, and never how to build it in cdk8s.
Nothing in this repository deploys anything into kup6s.

What the release adds are assertions: obligations and decisions, each with the mails it rests on and who stands for it.
The maintainer writes them on the command line in the tools pod, and an MCP client such as Claude Code proposes them through the server, for the maintainer to approve or reject.
They're events in the chain, like everything else.

## The image

The release after `v0.1.0a4`; the maintainer picks its number.
Pin its exact version, as for every release until `1.0.0`.

It brings **no migration**: an assertion is an event of the kind `assertion`, which the schema has allowed since the first migration, and the lists of obligations and decisions are computed from the log at every read, with no table of their own.
Run the migration job of the release as for every release, and expect `up to date:` with `0005_watermark`.

**It stands when** the tools pod runs the new image, and `previously --help` there lists `assert`, `approve`, `reject`, `obligations`, `obligation`, `decisions` and `decision`.

## A new secret, for `previously-mcp` only

| Variable | Value |
|---|---|
| `PREVIOUSLY_MCP_CONFIRM_KEY` | A random string of at least 32 characters, such as the output of `openssl rand -base64 48`. |

Give it to the Deployment `previously-mcp` and to nothing else: not to the tools pod, not to the ingest's CronJob, not to any other job.
`docs/reference/configuration.md` is the authoritative description, and `docs/reference/environment.md` holds the requirement.

**Why:** three tools of the server write, `write_assertion`, `write_approve` and `write_reject`, and each writes in two calls: the first shows what it would write and returns a handle, and only a second call that presents the handle writes.
The server seals the handle with this key, so that it opens only for the client and the statements it was issued for, for ten minutes.
No other process writes through a handle, so the key has no use anywhere else.
Rotating it makes only the handles not yet confirmed fail; nothing stored depends on it.

**Without it,** or with a value shorter than 32 characters, the server starts and reads as before, and every writing tool answers `Error: writing is not configured on this server`.
That's a safe state to deploy first and add the key later.

Neither `serve` nor anything else prints the key or writes it to a log.
The connection string of `previously-mcp` already belongs to a role that may write, since every call appends its access record; writing assertions needs no other grant.

**It stands when** a client connected through `kubectl port-forward` asks for `write_assertion` without `confirm`, on a mail it may see, and gets a preview with a `handle:` line instead of the sentence above.
Confirming isn't needed for the check, and a preview writes nothing but its access record.

## A requirement on the clients, not on the cluster

`write_approve` and `write_reject` write the maintainer's own word: an approval makes a model's proposal a statement he stands for.
The server can't tell whether a person looked, so the client has to ask the person before every call of either tool.
Neither tool may be allowed always in a client's configuration, and no mode of the client may let one through without the person.

That's on the maintainer's machine, not in kup6s; it stands here so that nobody configures a client for him on the way.
**The risk:** a client that runs either tool without asking writes approvals nobody looked at, and they outrank every proposal and stay in the log.
`docs/how-to/record-what-is-owed-and-decided.md` shows the setting for Claude Code and for Vibe.

## The tool list grew

The server offers ten tools now, where it offered five: `list_obligations`, `list_decisions` and the three writing tools came with this release.
Vibe's default harness keeps the old list across sessions, so after the deployment it needs `--legacy-harness` until it offers the new tools.
That's the client's side as well; nothing in the cluster changes for it.

## The ingest's line, since PR #16

The release carries the ingest of one or more folders, merged on 2026-10-12.
Nothing has to change: a run without `--folder` reads the folder `PREVIOUSLY_IMAP_FOLDER` names, as before, under the same watermark.

Two lines changed, and they matter only if a log alert or a dashboard matches on them:

- The line on standard output for a folder now ends in ` in <folder>`, such as `imap: 5 appended, 0 known, 0 variants, up to uid 4 in INBOX`.
- An error that concerns one folder now starts with `Error: folder <name>: `, followed by the error's sentence; the run goes on with the next folder and returns 2 at the end.
  An error that every folder would meet, such as a refused login or an unreachable server, keeps its old form and ends the run at once.

`docs/reference/cli.md`, under `ingest`, quotes every line.

## A host without a cluster

A `docker-compose` file sets `PREVIOUSLY_MCP_CONFIRM_KEY` for the service `mcp` and for no other service, and runs `migrate` before it starts the others, as for every release.
It needs no new service, no new volume and no table: the handle carries what the server needs to check it, and a confirmed handle is found again through the assertions it wrote.
This file considers it and builds nothing for it.

## How to recognize that everything stands

1. The tools pod and the jobs run the release after `v0.1.0a4`, and the migration job reported `up to date:` with `0005_watermark`.
2. `previously-mcp` has `PREVIOUSLY_MCP_CONFIRM_KEY`, and no other pod or job has it.
3. A preview of `write_assertion` through `kubectl port-forward` shows a `handle:` line.
4. The ingest's next run prints its line with ` in ` and the folder's name at the end, and goes on from its watermark.
