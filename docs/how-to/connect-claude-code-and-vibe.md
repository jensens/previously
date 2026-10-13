(connect-claude-code-and-vibe)=

# How to connect Claude Code and Mistral Vibe

This guide shows you how to let Claude Code or Mistral Vibe read the log: declare the client's processing chain, give the circles it may read a rule, add the client, start the server, connect the client, and check that the connection stands.
For why a client is treated as a processor, see {ref}`mcp-interface`, for the tools it gets, {ref}`mcp-tools`, and for every option, {ref}`cli-reference`.
To let a client propose obligations and decisions as well, and to make it ask you before it answers one, continue with {ref}`record-what-is-owed-and-decided` once the connection stands.

You need three things before you start.

- The `previously` command from the first release with the MCP server, `0.1.0a3`, or from a checkout, where `uv run previously …` runs it.
- A database that `previously migrate` has brought up to date, with `PREVIOUSLY_DSN` exported, and mail in it ({ref}`ingest-a-mail-folder`).
- A policy with circles and members, as {ref}`set-a-policy-and-try-a-call` sets one up.

## Declare the client's processing chain

Whatever a client reads goes to whoever runs its model, so a client is declared as a provider, like the providers of the gate.
Declare a provider of its own for each client, even when a provider of the same company already exists for the gate: Claude Code under a Max plan runs under other terms than the Anthropic API.

```shell
previously policy provider claude-max --inference us=us --storage us \
    --retention-days 30 --operator Anthropic --training no --subprocessors unknown \
    --model-origin Anthropic \
    --statement "Claude Code, Max plan: consumer terms, training off in the settings" --yes
previously policy provider vibe-free --inference eu=eu --storage eu \
    --retention-days unknown --operator Mistral --training unknown --subprocessors unknown \
    --model-origin Mistral \
    --statement "Mistral Vibe, free plan" --yes
```

Write what your account and its terms say, and not what the examples above say.
The statement is your source for the values, and it stays in the log.

These declarations are the clients' and not the gate's.
`previously gate` calls only the providers its task names, `anthropic`, `mistral` and `local`, and each of them needs a declaration of its own, even when a client of the same company is declared already.
A `gate explain` that says `denied` after a client's setup names on standard error the gate's providers that have no declaration, or, where no rule applies, says that only a provider declared with `--local` can be chosen; {ref}`set-a-policy-and-try-a-call` declares them.

A harness against a local model is declared with `--local`.
Declare it with `--training no --subprocessors none` as well: without them it fails every rule that forbids training or subprocessors, and a circle with such a rule stays withheld from it.

## Give each circle the client may read a rule

Without a rule, only a local processor may read a circle's content, and a client that isn't local gets placeholders instead of mails.
Give the circle a rule that allows the client's chain:

```shell
previously policy rule circle:xz --regions eu us \
    --statement "XZ may be read through Claude Code" --yes
```

A rule for a region the client doesn't process in, or one that forbids a property the client's provider has or didn't declare, keeps the circle from that client.

## Add the client

Add the client with the provider you declared for it:

```shell
previously client add claude-code --processor claude-max \
    --statement "Claude Code on my laptop" --yes
```

The command asks before it writes, and `--yes` answers for you.
Keep `--yes` where nobody can answer, such as in `kubectl exec` without `-i`: there the question gets no input, and the command writes nothing and prints no token.

The command prints the token once:

```text
client claude-code	processor claude-max
client claude-code: token TOKEN
shown once; store it now
```

Store the token in your password manager.
Nothing can show it again; if it's lost, run `client add` for the same name, which replaces the client and its token.

## Start the server

Start the server over HTTP on your machine:

```shell
previously serve
```

It listens on `http://127.0.0.1:8765/mcp` and runs until you stop it.
To reach a server in the Kubernetes cluster instead, forward its port first, such as with `kubectl port-forward svc/previously-mcp 8765:8765`, and use the same address.
The port-forward doesn't recover by itself: when it dies, the client's calls fail and retry until you start it again, and it proved unstable for longer sessions.
The lasting answer is a path that stays up: a private network that the clients and the server share, with a name for the server.
`serve` asks two things of that path: the path is encrypted or private, as {ref}`environment-requirements` states, and the name that clients use is in `PREVIOUSLY_MCP_ALLOWED_HOSTS` ({ref}`configuration-reference`), or the requests get the status 421.
A tailnet is one way to meet both, and the one measured below: a Tailscale client beside the server joins the network under a name such as `previously-mcp.tailnet.example`, forwards the port to the server on `127.0.0.1`, and Claude Code connects to `http://previously-mcp.tailnet.example:8765/mcp`.
WireGuard encrypts the path, so plain HTTP inside the tailnet needs no TLS of its own.
Another private network, or TLS ended in front of `serve`, works as well.

## Connect Claude Code

Add the server with the token as a header:

```shell
claude mcp add --transport http previously http://127.0.0.1:8765/mcp \
    --header "Authorization: Bearer TOKEN"
```

Write `Bearer ` before the token, with the space.
A header without it, `Authorization: TOKEN`, gets the status 401 from the server, and Claude Code says no more than that the server failed, in the list that `/mcp` shows.
If `/mcp` lists the server as failed, remove it with `claude mcp remove previously` and add it again with `Bearer ` in the header.

To let Claude Code start the server itself over standard input and output instead, on a machine that reaches the database, add it as a command:

```shell
claude mcp add --transport stdio --env PREVIOUSLY_MCP_CLIENT=claude-code \
    --env PREVIOUSLY_DSN="$PREVIOUSLY_DSN" previously -- previously mcp
```

That form needs no token, because whoever starts the process is the client, and no running server.
It puts the connection string with its password into the configuration of Claude Code, so use it only where that file is as safe as the database's password.
It isn't on the list of tested configurations below.

## Connect Mistral Vibe

Add the server to `.vibe/config.toml` in your project, or to `~/.vibe/config.toml`, with the token in `headers`:

```toml
[[mcp_servers]]
name = "previously"
transport = "streamable-http"
url = "http://127.0.0.1:8765/mcp"
headers = { Authorization = "Bearer TOKEN" }
```

Use `headers`, not `api_key_env`.
With `api_key_env`, Vibe 2.26.1 sent no header at all, the server refused every call, and Vibe didn't say so: its model reported that each tool returned nothing.

Vibe's default harness keeps the list of tools across sessions.
After a release of Previously that changes the tools, start Vibe with `--legacy-harness` until the default harness offers the new ones.
The first release with assertions is such a release: it adds `list_obligations`, `list_decisions` and the three writing tools, ten tools in all where there were five.
Whether `/mcp refresh` in Vibe brings the new tools into the default harness hasn't been measured.
A server added to Vibe's default harness for the first time showed all ten tools.

Vibe 2.26.1 lists the tools as `mcp_previously.<tool>`, such as `mcp_previously.whoami` and `mcp_previously.write_approve`, and not as `previously_<tool>`.
Vibe asks for permission before every MCP tool call, the reading tools included, with the choices `Allow once`, `for this session`, `Always allow` and `Deny`, and its prompt shows the whole arguments of the call, an assertion's text among them.
Never choose `Always allow` for `write_approve` or `write_reject`: an approval is the operator's word, and {ref}`record-what-is-owed-and-decided` explains why a client has to ask before it answers.

## Check the connection

Ask the client to call the tool `whoami`.
Its answer starts with the name of the client and its processing chain, and lists which circles it sees and which not, with the reason.

Then check that the server recorded the call:

```shell
previously access --client claude-code
```

A line with `tool:whoami` and `ok` means the client reached the server with its token.
No line means the call never arrived, which is the only sign of a refused token that Vibe gives.

## Replace or revoke a token

Run `client add` with the same name to get a new token; the old one stops working with the next request.
Run `client revoke` to lock a client out:

```shell
previously client revoke claude-code --statement "laptop lost" --yes
```

## Tested configurations

The first two configurations were measured on 2026-10-10, against a test server on the MCP SDK `mcp` 2.3.0 that accepted a static bearer token, and not against `previously serve`; the third was measured against `previously serve` itself:

- **Claude Code 2.1.289**, which speaks the protocol revision `2026-07-28`, added with `claude mcp add --transport http … --header "Authorization: Bearer …"`: the token was sent and accepted.
- **Mistral Vibe 2.26.1**, which speaks `2025-11-25`, with the server in `.vibe/config.toml`: `headers` with `Authorization` was sent and accepted, and the static `api_key_env` sent no header.
  The default harness didn't see two tools that the restarted server offered, and `--legacy-harness` called them.
- **Claude Code against `previously serve`** in a Kubernetes cluster, through `kubectl port-forward`, on 2026-10-11, in a version nobody wrote down: `whoami` answered, `previously access` listed the call, and Claude Code summarized the mails of a circle with a rule and nothing of the circles without one.
  The same run found the header without `Bearer ` that the section on Claude Code describes.

The form of a result that the server uses, one text block, arrived whole in the first two.
The measurement recorded the key `headers` of the Vibe entry and not the rest of it; `name`, `transport` and `url` above follow [Vibe's documentation of MCP servers](https://docs.mistral.ai/vibe/code/cli/mcp-servers).
Nothing else on this page was measured with a real client: not the form with standard input and output.

Claude Code and Mistral Vibe 2.26.1, in its default harness, were measured on 2026-10-13 against `previously serve` `0.1.0a5` in the cluster, through `kubectl port-forward`:

- Vibe listed ten tools for a freshly added server, as `mcp_previously.<tool>`, and called with the protocol revision `2025-11-25`.
- Vibe asked before every tool call, reading tools included, and showed the full arguments.
- The input schema of `write_assertion`, which nests its items and their sources through `$defs` and `$ref`, worked in both clients: each wrote proposals through it.
- The ask rule `mcp__previously__write_approve` in Claude Code worked in auto mode: the client showed `Ask rule mcp__previously__write_approve overrides auto mode for this tool` and offered `Yes`, `Yes, and don't ask again` and `No`.
- The `kubectl port-forward` died during the run, and the clients retried.
  The handle of `write_assertion` absorbed the retries: no duplicate was written.

Claude Code was measured on 2026-10-13 against `previously serve` `0.1.0a6` in the cluster through a tailnet, not a port-forward: a Tailscale client in userspace beside the server, a self-hosted Headscale control server, plain HTTP inside WireGuard, and the tailnet name of the server in `PREVIOUSLY_MCP_ALLOWED_HOSTS`.
`whoami` answered through that address, and `previously access` listed the call like every other.
The access policy of the tailnet let one person's machine reach the port, and no rule let the pod reach anyone.

Claude Code 2.1.296 was measured on 2026-10-13 against `0.1.0a6` in `auto` mode without an ask rule for `write_reject`: the mark `anthropic/requiresUserInteraction` alone made it show its prompt before the call.

Not measured: the `[tools.…]` keys of Vibe's configuration, whose names assume `previously_<tool>`.
