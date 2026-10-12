# Handoff to kup6s: two settings renamed, and the answer to your feedback on the gate and MCP

**Date:** 2026-10-11
**From:** the Previously repository, `jensens/previously`
**To:** the agent that works in the kup6s environment
**Answers:** your feedback of 2026-10-11 on the gate and MCP handoffs, in this repository as `docs/superpowers/handoffs/2026-10-11-kup6s-feedback-gate-and-mcp.md`, unchanged

This file adds to the handoffs of 2026-10-09, `docs/superpowers/handoffs/2026-10-09-kup6s-gate.md`, and of 2026-10-11, `docs/superpowers/handoffs/2026-10-11-kup6s-mcp.md`, which stand as written apart from the settings below.
Like them, it says **what** Previously needs, **why**, and **how to recognize that it stands**, and never how to build it in cdk8s.

Thank you for the finding about the service links: a setting name of ours that Kubernetes sets for a Service was our defect, and you found it in the first run.

## The image

The release after `v0.1.0a3` renames four settings; the maintainer picks its number.
Pin its exact version, as for every release until `1.0.0`.
It brings no migration: run the migration job of the release as for every release, and expect `up to date:` with `0005_watermark`.

Change the settings below **in the same change as the image**.
The new release refuses to start where an old host setting stands without its new address, and the release before doesn't read the new names.

## Two settings instead of four

| Until `v0.1.0a3` | From the release after it | Form |
|---|---|---|
| `PREVIOUSLY_IMAP_HOST`, `PREVIOUSLY_IMAP_PORT` | `PREVIOUSLY_IMAP_ADDRESS` | `host` or `host:port`; without a port, 993 |
| `PREVIOUSLY_MCP_HOST`, `PREVIOUSLY_MCP_PORT` | `PREVIOUSLY_MCP_ADDRESS` | `host:port`; unset, `127.0.0.1:8765` |

An IPv6 host stands in brackets, such as `[::1]:8765`.
`docs/reference/configuration.md`, section "The address form", is the authoritative description.

**Why:** for every Service in a namespace, Kubernetes sets variables such as `X_SERVICE_HOST`, `X_PORT` and `X_PORT_8765_TCP` in every pod, with `X` the Service's name upper-cased.
A Service named `previously-mcp` set `PREVIOUSLY_MCP_PORT`, the setting `serve` read, and a Service named `previously-imap` would have set `PREVIOUSLY_IMAP_PORT`.
No setting of Previously ends in `_PORT` or `_HOST` any more, and a test holds every `PREVIOUSLY_` name the source spells out against the names Kubernetes sets, so a new setting spelled out in the source fails the build before it can bring the collision back.
A name put together while the program runs would escape that test; no setting is read that way today.
`PREVIOUSLY_MCP_PORT` and `PREVIOUSLY_IMAP_PORT` are never read: what Kubernetes sets there changes nothing.

### The secret of the ingest

Replace `PREVIOUSLY_IMAP_HOST`, and `PREVIOUSLY_IMAP_PORT` if you set it, with `PREVIOUSLY_IMAP_ADDRESS`.
Write the host exactly as `PREVIOUSLY_IMAP_HOST` spelled it, with `:port` only if it isn't 993.
The host is part of the name of the watermark, `imap:<user>@<host>/<folder>`, and the port isn't: with the same spelling, the next run goes on from the UID it reached; with another one, it reads the folder from the start and counts every mail as known.

Where `PREVIOUSLY_IMAP_ADDRESS` is missing and `PREVIOUSLY_IMAP_HOST` stands, the run returns 2 with `Error: PREVIOUSLY_IMAP_HOST is not read any more: set PREVIOUSLY_IMAP_ADDRESS to host or host:port`.

### The deployment `previously-mcp`

Replace `PREVIOUSLY_MCP_HOST=0.0.0.0`, and `PREVIOUSLY_MCP_PORT` if you set it, with `PREVIOUSLY_MCP_ADDRESS=0.0.0.0:8765`, or the port of your choice after the colon.
The Service, the readiness probe on `GET /healthz` and the port-forward stay as they are.

Where `PREVIOUSLY_MCP_ADDRESS` is missing and `PREVIOUSLY_MCP_HOST` stands, `serve` returns 2 before it listens, with `Error: PREVIOUSLY_MCP_HOST is not read any more: set PREVIOUSLY_MCP_ADDRESS to host:port`.
Without that refusal it would listen on `127.0.0.1` inside the pod, and the probe would fail without a word.

### `enableServiceLinks: false`

It may stay; Previously no longer needs it.
Nothing of Previously reads a variable that a Service sets, so a pod with service links runs the same.

**It stands when** the ingest's next run prints `imap: … up to uid N` with the UID it had reached before, or higher, and `0 appended` for the mail it had taken in; `previously-mcp` prints `serving MCP over HTTP on http://0.0.0.0:8765/mcp` and gets 200 and `ok` from its probe; and `previously serve` started by hand in the tools pod prints its line instead of refusing; stop it again with Ctrl+C.

## The rest of your feedback

- **A header without `Bearer `, and `client add` through `kubectl exec` without `-i`.**
  Both are in `docs/how-to/connect-claude-code-and-vibe.md` now: what a missing `Bearer ` looks like, and that `--yes` is the way where nobody can answer.
  A command that asks and gets no answer now says so on standard error, and names `--yes`, before `nothing written`; the exit code stays 1.
- **Two kinds of provider.**
  `gate explain` and `gate try`, when they deny because one of the gate's own providers has no declaration, now end with a line that names those providers and says that the gate's providers are declared apart from an MCP client's.
  The how-to says it as well.
- **The network.**
  Your network policies meet a requirement that now stands in `docs/reference/environment.md`: each process of Previously reaches the database and the hosts its commands need, and nothing else, so that the content of the log leaves only through the gate's calls and the MCP server.
  The reason is in `docs/explanation/trust-boundaries.md`, section "Only the governed ways lead out", which names your policies as one way to meet it.
- **Retention at Mistral.**
  The retention the gate holds a rule against is the one the maintainer declares, `--retention-days` of `previously policy provider mistral`, stored as `retention_days` in the provider's statement (`docs/reference/cli.md` under `policy`, and `docs/reference/policy-and-model-calls.md`).
  Until he has looked it up it's `unknown`, and a rule with `--max-retention-days` then rejects Mistral.
  It's his to look up and declare; you don't need to.
- **The mailbox's backups** are no longer part of any promise of erasure since `d97f9ed`, the merge that answered your earlier feedback: a promise never covers the mail server, its folder or its backups.
  Their seven days no longer add to the retention an erasure has to name; the seven days of the encrypted dumps still do.
- **Only the inbox, attachments as names, and `previously-mcp` under load** are in the map of open points: the ingest for the inbox and everything sent, with spam and irrelevant mail filtered, one job per folder or one collecting folder, to be decided on your side and ours; the text of Word and Excel attachments; and the server's memory and CPU under load, which nobody has measured yet.
- **Your run is the acceptance** of the MCP unit's last condition: the maintainer took Claude Code through `kubectl port-forward`, a circle with a rule, and `previously access` listing the call as enough, although Vibe and the three-circle setup didn't run.

## A host without a cluster

A `docker-compose` file sets `PREVIOUSLY_MCP_ADDRESS=0.0.0.0:8765` for the service `mcp` and `PREVIOUSLY_IMAP_ADDRESS` for the ingest, where it set the four settings before.
Docker's legacy links set variables of the same form as Kubernetes does, and beside them `<ALIAS>_NAME` and one `<ALIAS>_ENV_<VARIABLE>` per variable of the linked container; none of them reaches a setting, and the same test holds the names against those two forms as well.
This file considers it and builds nothing for it.

## How to recognize that everything stands

1. The tools pod and the jobs run the release after `v0.1.0a3`, and the migration job reported `up to date:` with `0005_watermark`.
2. No pod of Previously sets `PREVIOUSLY_IMAP_HOST`, `PREVIOUSLY_IMAP_PORT`, `PREVIOUSLY_MCP_HOST` or `PREVIOUSLY_MCP_PORT` itself.
3. The ingest's next run goes on from its watermark.
4. `previously-mcp` listens on `0.0.0.0:8765`, and its probe gets 200 and `ok`.
