# Feedback from kup6s: `v0.1.0a6`

**Date:** 2026-10-13
**From:** the agent that works in the kup6s environment
**To:** the Previously repository, `jensens/previously`
**Answers:** `handoffs/2026-10-13-kup6s-a6.md`

## It stands

1. The tools pod, the jobs and `previously-mcp` run `0.1.0a6`; the migration job reported `up to date: 0005_watermark`.
2. Switchover on purpose, `previously-postgres-1` to `-2`, requested at 13:08:11 UTC, the cluster healthy again at 13:08:36.
   After it, every readiness check answered 200, the log of `previously-mcp` shows no traceback, `whoami` answered three times in a row, and the pod didn't restart.

## One failure, inside the switchover, and a correction

One readiness check failed with 503, at 13:08:12.6, a second after the switchover began.
Its traceback shows `pool_pre_ping` at work: the ping found the pooled connection dead (`InvalidatePoolError`), and the new connection was refused, `connection to server at "10.43.6.108", port 5432 failed: Connection refused`, because no primary served the `-rw` service at that moment.
That 503 is right: the database didn't answer.

This corrects our feedback of 2026-10-12.
We wrote that the first request *after* a switchover fails; measured again, the failing check of that run came at 23:28:18, while the switchover ran until 23:28:28.
So on `0.1.0a5` too, the failure fell inside the switchover, and the requests after it already succeeded.
`pool_pre_ping` still earns its round trip: it keeps a connection that died while nobody asked from failing the next request, however much later that comes.

One thing remains, small: every failed readiness check during a switchover writes a full traceback chain of three or four exceptions to the log.
For an expected outage of the database, one line per failed check, such as the `ServerUnreachable` sentence, would say the same.

## The clients

`write_approve` and `write_reject` now write in one call, so the client's question to the person is the only confirmation left.
In the maintainer's Claude Code settings, no tool of Previously is allowed always.

## Stage A2: the MCP server in the tailnet

Check 6 of the MCP handoff stands since 2026-10-13.
A tailscale container in userspace runs beside `serve` in the `previously-mcp` pod and joins the Headscale tailnet as `previously-mcp.tail.kup.tirol`; `tailscale serve` forwards TCP 8765 to the server on `127.0.0.1`.
`PREVIOUSLY_MCP_ALLOWED_HOSTS` holds that name, and Claude Code connects to `http://previously-mcp.tail.kup.tirol:8765/mcp`.
The Headscale policy lets the maintainer alone reach that port, and no rule has the server's tag as its source, so the pod reaches nobody in the tailnet.
The path is plain HTTP inside WireGuard, which we read as the "encrypted or private path" your docs ask of `serve`.
`whoami` through that address answered, and `previously access` lists it like every call.
The pod's network policy grew by the Headscale server on 443 and 3478/udp only; a restart of the pod keeps the same tailnet node.
`kubectl port-forward` stays as a fallback; it had proved unstable for longer sessions.
