(record-what-is-owed-and-decided)=

# How to record what's owed and decided

This guide shows you how to record obligations and decisions with the mails they rest on, how to let Claude Code propose them from a customer's mails and go through its proposals, and how to ask what's open and what's overdue.
For why an assertion works this way, see {ref}`assertions`; for every option, {ref}`cli-reference`; for the tools, {ref}`mcp-tools`.

You need two things before you start.

- The `previously` command from the first release with assertions, the one after `0.1.0a4`, or from a checkout, where `uv run previously …` runs it.
- A database that `previously migrate` has brought up to date, with `PREVIOUSLY_DSN` exported, and mail in it ({ref}`ingest-a-mail-folder`).

For the part with Claude Code you also need a client connected as {ref}`connect-claude-code-and-vibe` describes.

## Find the sources

Every assertion names the events it rests on, and for a mail, the units that say it.
Read the chronicle and note the event id and the unit of each line you rely on:

```shell
previously chronicle --since 2026-09-01T00:00:00+00:00
```

The first field of a line is the event id, the second the unit.

## Record an obligation

State who owes whom what, by when, and on which mail:

```shell
previously assert obligation --debtor own --creditor circle:huber \
    --what "Send the offer for the roof" --due 2026-11-30 \
    --source 42:2,3
```

The command shows the payload and asks `write? [y/N]`; answer `y`, and it prints the id of the new obligation, such as `assertion 57`.

- For a debtor or creditor, use `own` for your side, `circle:NAME` for a customer, `address:ADDRESS` for a person whose address you know, and `name:TEXT` for anybody else.
- To rest on a whole event, give its id alone, such as `--source 45`, and repeat `--source` for every further event.
- If the command prints a `hint:` line naming an address, the person behind your `name:` has an address in the sources: consider `address:` instead.

## Record a decision

State what was decided, by whom and on which day:

```shell
previously assert decision --what "The certificate comes from the customer's own CA" \
    --by address:eva@huber.example --by own --on 2026-09-12 \
    --source 42:4
```

If it replaces an earlier decision, add `--replaces` with the id of that decision.

## Change or close an obligation

Write a new version with `--subject` and the id of the obligation, and only the options that change:

```shell
previously assert obligation --subject 57 --due 2026-12-15 \
    --reason "Eva asked for two more weeks" --source 42:2,3 --source 61
```

The command takes every option you leave out from the version that stands, shows one `change` line per field that differs, and asks.
`--source` replaces the sources of the version, so name every event the new version rests on, the old ones included.
`--reason` is never taken over, so give one for each version whose reason matters.
To close it, set `--state fulfilled` or `--state cancelled` the same way, with the mail that shows it as a source.
To clear the due date, write `--due none`.

## Let Claude Code propose

The server writes only with a key for its handles.
Set `PREVIOUSLY_MCP_CONFIRM_KEY` for `previously serve` or `previously mcp`, at least 32 characters, before you start it ({ref}`configuration-reference`):

```shell
export PREVIOUSLY_MCP_CONFIRM_KEY="$(openssl rand -base64 48)"
previously serve
```

Without it, the server reads as before and every writing tool answers `Error: writing is not configured on this server`.
If your client starts `previously mcp` over standard input, pass the key the way it passes the other settings, such as with one more `--env PREVIOUSLY_MCP_CONFIRM_KEY=…` to `claude mcp add` ({ref}`connect-claude-code-and-vibe`); the client's configuration then holds the key, as {ref}`environment-requirements` says under the MCP server.

Then ask Claude Code, for example: "Read the mails of the circle `huber` since September and propose, with `write_assertion`, every obligation and decision in them, each with the units it rests on."
Claude Code calls `write_assertion` once to preview its proposals and once more to confirm them.
What it writes stays a proposal, out of every default list, until you approve it.

## Make the client ask before it answers

`write_approve` and `write_reject` count as your own word, so the client has to ask you before it confirms either.
Set that up before you let a client answer proposals.

For Claude Code, add an ask rule to your user settings in `~/.claude/settings.json`, with the server named `previously` as in {ref}`connect-claude-code-and-vibe`:

```json
{
  "permissions": {
    "ask": [
      "mcp__previously__write_approve",
      "mcp__previously__write_reject"
    ]
  }
}
```

Claude Code's [documentation of permissions](https://code.claude.com/docs/en/permissions#manage-permissions) says that an ask rule prompts even where an allow rule also matches, and in every permission mode, `auto` and `bypassPermissions` included, except `dontAsk`, which refuses the call instead.
Without the rule, `auto` mode lets a classifier decide in your place, and Claude Code starts in `auto` mode from v2.1.283 on, as its [documentation of permission modes](https://code.claude.com/docs/en/permission-modes) says.
The same documentation names a mark an MCP tool can carry, `_meta["anthropic/requiresUserInteraction"]`, that makes Claude Code ask for it as an ask rule does; the tools of Previously don't carry it, so the ask rule is what makes Claude Code ask.
Never add either tool to `allow`.

For Mistral Vibe, its [documentation of MCP servers](https://docs.mistral.ai/vibe/code/cli/mcp-servers) sets a tool to ask in `.vibe/config.toml`, with the tool named after the server and the tool:

```toml
[tools.previously_write_approve]
permission = "ask"

[tools.previously_write_reject]
permission = "ask"
```

Neither configuration has been measured against Previously yet; check that the client asks before you rely on it.

## Go through the proposals

List the entries with a proposal pending, or that stand as a proposal:

```shell
previously obligations --proposals
previously decisions --proposals
```

Look at one entry with its proposals, or at its whole history:

```shell
previously obligation 57
previously obligation 57 --history
```

Each pending proposal shows as `proposal` lines, one per field it would change, with its own id.
Approve the ones you take, one or several at once, and reject the others:

```shell
previously approve 71 72
previously reject 73 --reason "Eva asked about it and nobody decided"
```

Of several proposals on one entry, approve one and reject the others: an approval is a direct version that comes after them, and `approve` refuses a proposal that a direct version came after.
An approval keeps the proposal's wording and sources; to change a word, approve and then write a new version with `--subject`, or reject and write your own.
Over MCP, ask Claude Code to approve or reject by the ids its history names; it previews, asks you, and confirms.

## Ask what's open

```shell
previously obligations --state open
previously obligations --overdue
previously obligations --owed-by own
previously obligations --owed-to own --circle huber
previously decisions --state valid
```

`--overdue` lists what's open and due before today's UTC date.
Over MCP, ask for `list_obligations` with `overdue` set, or with `subject` and `history` for the versions of one entry.

## When a source gets erased

An erasure of a mail takes every assertion that rests on it along, as `redact` reports with a `cascaded: assertion ID` line.
To keep an obligation that also rested on other mails, write it again with `assert`, on the sources that are left.
