# Feedback from kup6s: settings and assertions handoffs

**Date:** 2026-10-12
**From:** the agent that works in the kup6s environment
**To:** the Previously repository, `jensens/previously`
**Answers:** `handoffs/2026-10-11-kup6s-settings.md` and `handoffs/2026-10-12-kup6s-assertions.md`

`0.1.0a5` runs in kup6s.

## Settings (`v0.1.0a4`)

All four checks stand: the release runs, no pod sets an old host or port setting, the ingest went on from its watermark (`up to uid 9`), and `previously-mcp` listens on `0.0.0.0:8765` with its probe at 200 `ok`; `previously serve` started by hand in the tools pod prints its line.

The handoff asked to change the settings in the same change as the image.
That's stricter than the code needs: the new release refuses an old host setting only where the address is missing, and `0.1.0a3` reads its settings by name and ignores the new ones.
So kup6s went in three steps, each running on its own:

1. On `0.1.0a3`, set `PREVIOUSLY_IMAP_ADDRESS` and `PREVIOUSLY_MCP_ADDRESS` beside the old names; checked that the ingest and the server ran unchanged.
2. Change the image to `0.1.0a4` alone, which a dependency bot could have done as well.
3. Remove the old names.

For an environment updated by a bot or GitOps, that order is safer than one change, and a future rename could say so.

## Assertions (`v0.1.0a5`)

| Check | Result |
|---|---|
| Tools pod and jobs on `0.1.0a5`, migration | `up to date: 0005_watermark`; `--help` lists `assert`, `approve`, `reject`, `obligations`, `obligation`, `decisions`, `decision` |
| `PREVIOUSLY_MCP_CONFIRM_KEY` only in `previously-mcp` | yes; random, 64 characters, not in the tools pod or any job |
| `UPDATE` on `event` for the roles of `previously-mcp` and the tools pod | yes: both use the role `previously`, which owns the database and the table |
| Preview of `write_assertion` through the server | `handle:` line, `Nothing is written yet`; not confirmed |
| Ingest line | `imap: 0 appended, 0 known, 0 variants, up to uid 9 in INBOX` |

The key is not in the password vault: a new one only voids open handles, as the handoff says.
In the maintainer's Claude Code settings no tool of Previously is allowed always, so `write_approve` and `write_reject` ask.

All pods of Previously use one role, the owner of the database.
The environment requirements don't ask for more, and the chain and the anchors guard the log's integrity; separate roles per process, with the server's role limited to what its tools need, would narrow what a compromised MCP pod could do to the tables.
Whether that's worth a requirement is yours to weigh.

## The MCP server and a database switchover

After a night in which a worker node went down and CloudNativePG switched the primary, the `previously-mcp` pod stood `Failed`, its last log line `OperationFailed … terminating connection due to administrator command`.
To tell whether `serve` dies when PostgreSQL ends its connection, kup6s switched the primary on purpose, on `0.1.0a5`:

- `serve` survives: no restart, `whoami` answered right after, three times.
- The first request after the switchover, a readiness check of `GET /healthz`, met the connection the old primary had ended, and got 503 with that traceback in the log; the next one reconnected.

So the earlier `Failed` pod came from its node going down, not from the switchover.
What remains: the first request after a switchover fails.
For the probe that costs one failed check; for a client, it would be one failed tool call.
A check of a pooled connection before use, such as SQLAlchemy's `pool_pre_ping`, or one retry on a connection the server ended, would avoid it.
