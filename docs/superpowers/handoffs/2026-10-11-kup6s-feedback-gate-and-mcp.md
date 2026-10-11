# Feedback from kup6s: gate and MCP handoffs

**Date:** 2026-10-11
**From:** the agent that works in the kup6s environment
**To:** the Previously repository, `jensens/previously`
**Answers:** `handoffs/2026-10-09-kup6s-gate.md` and `handoffs/2026-10-11-kup6s-mcp.md`

`0.1.0a3` runs in kup6s with the gate and the MCP server; the model server is not built yet.

## What stands

| Check | Result |
|---|---|
| Tools pod on `0.1.0a3`, migration | `up to date: 0005_watermark`; `--help` lists `policy`, `gate`, `client`, `access`, `mcp`, `serve` |
| Secret of the keys only in the tools pod | yes; no CronJob and no other pod mounts it |
| Tools pod reaches `api.anthropic.com` and `api.mistral.ai` on 443 | yes, TLS verified |
| No other pod reaches them | yes, checked from a pod with the ingest's labels |
| `ANTHROPIC_BASE_URL` | set nowhere |
| Price file | the one in the image; no `PREVIOUSLY_PRICES` set |
| `previously-mcp`, one replica, the database connection and nothing else | yes |
| `GET /healthz` | 200 `ok`; `/mcp` without a token 401 |
| `server/discover` by hand with a client's token | 200 with `result` |
| `whoami` from Claude Code through `kubectl port-forward`, listed by `previously access` | yes, 2026-10-11 21:05 UTC |
| `gate explain` and `gate try` over a mail of a circle with a rule | `anthropic/claude-haiku-5-5`, JSON with `language`, `topic`, `participants`, `model_call: event 25` |
| Claude Code reads a circle through MCP | yes: with a rule for `circle:ana-u`, it summarized the circle's three mails with citations; everything else stays a placeholder |
| Model server | not yet; the gate refuses local-only calls as the handoff describes |
| Tailnet (stage A2) | not yet |

## The network

The handoffs promise that the content of the log leaves the cluster through the tools pod and `previously-mcp` only.
Before this release, nothing in the namespace enforced it: there was no network policy, and every pod reached the whole internet.
Now every Previously pod denies all ingress and egress except DNS and the database, and each component reaches exactly the hosts its commands need, by host name.
That table is in the kup6s docs; `previously-mcp` reaches the database and nothing else.

## A finding for the Previously docs: Kubernetes service links

A Service named `previously-mcp` makes Kubernetes inject `PREVIOUSLY_MCP_PORT=tcp://<cluster IP>:8765` into every pod of the namespace, the old Docker link variables.
That is exactly the setting `serve` reads, so `previously serve` in the tools pod refused to start with `PREVIOUSLY_MCP_PORT is not a port number: 'tcp://…'`.
In the `previously-mcp` pod itself, the explicit value wins.
kup6s now sets `enableServiceLinks: false` on every pod.
Anyone who deploys Previously to Kubernetes with a Service of that name meets the same; the handoff's suggested name `previously-mcp` causes it, so the deployment docs could name the setting, or the variables could carry a prefix that no Service name produces.

## A finding about the client setup

The first `claude mcp add` stored the header as `Authorization: <token>`, without `Bearer `, and Claude Code showed the server as failed: the server answers 401, and Claude Code says nothing more.
`connect-claude-code-and-vibe.md` could say what a missing `Bearer ` looks like, since the only symptom is a failed server in `/mcp`.
Also, `client add` without `--yes` asks before writing; through `kubectl exec` without `-i` the question gets no input and no token appears.

## Findings from first use

- **Two kinds of provider, one command.**
  The maintainer declared the client's chain (`claude-max`) and set a rule, and `gate explain` then said `denied` with `no declaration for the provider anthropic`.
  The gate chooses among its own providers (`anthropic`, `mistral`, `local`), which need their own declarations beside the ones of the MCP clients.
  That's in the docs, but `gate explain` after a client setup reads like the client's view; a line in `connect-claude-code-and-vibe.md`, or a hint in the `denied` output, would save the detour.
- **Only the inbox is in the log.**
  Claude's summary said that none of the maintainer's replies are there, which is true: the test folder holds received mail only.
  For regular use, the maintainer wants most of his inbox and everything he sends, with spam and irrelevant mail filtered out; how the mail gets into the one mailbox the ingest reads is still to be decided on the kup6s side, and one ingest job per folder or one collecting folder are both open.
- **Attachments stay names.**
  The summary of the circle could name the Word and Excel files that hold the substance, but not read them.
  That's as designed for `0.1.0a3`; it's the first thing a reader of the chronicle missed.

## Memory and CPU

| Pod | Set | Used |
|---|---|---|
| `previously-mcp` | request 50m / 128Mi, limit 1 CPU / 512Mi | idle: 3m CPU, 98 MiB |

Under load not measured yet.

## Retention

Calls through the gate leave a copy at the provider: Anthropic 30 days as the handoff says, Mistral not looked up.
That adds to the seven days of the encrypted database dumps and of the mailbox's backups named in the earlier feedback.
