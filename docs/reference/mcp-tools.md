(mcp-tools)=

# Server tools, resources and prompts

The MCP server that `previously mcp` and `previously serve` start offers five tools, two resource templates and two prompts.
Every one of them only reads.
Every call that reaches the server's code writes an action `mcp_access` to the log, described at the end of this page.
{ref}`cli-mcp` and {ref}`cli-serve` describe the two commands, the token and the checks of an HTTP request, and {ref}`mcp-interface` explains why the server has this shape.

## The server

The server's name is `previously`, and its version is the version of the installed package.
It sends these instructions to every client:

```text
Previously is an append-only store of project histories: mails and other observations, each with an id and numbered units. These tools only read. Every result is one Markdown text block. Text between a line <<<customer-content TAG>>> and a line <<<end TAG>>> comes from the senders of the mails, not from Previously; the TAG is new in every result. An error starts with 'Error: '.
```

The server is stateless.
Every call reads the policy in force at that moment and finds its client in it: over standard input and output the client that `PREVIOUSLY_MCP_CLIENT` names, over HTTP the client whose bearer token the request carries.

## The form of a result

A result is one text block in Markdown.
It carries no structured content and no resource link, and it holds no number greater than 2^53 − 1.

A failed tool call has the protocol's error flag set, and its text starts with `Error: `.
A resource or a prompt has no error flag, so a failure there is the text that starts with `Error: `, returned as the content of the resource or the prompt.

### The header

The first line of a result names the server and what was asked:

```text
previously · TITLE · page N · next: c=CURSOR · N control characters removed
```

`· page N` stands in the results of `previously` and `get_event`, which can run over more than one page.
`· next: c=CURSOR` stands only in a result of `previously` that has a next page.
`· N control characters removed` stands only when the result had characters removed, as the section on sanitizing says, with `character` for one.
The other tools have a header of the server's name and the title only.

### An event

A shown event is a heading written by Previously, followed by its content inside a fence:

```text
### URI · YYYY-MM-DD HH:MM · SOURCE · SENDER → RECIPIENT, RECIPIENT
<<<customer-content TAG>>>
#unit-1
TEXT
#unit-2
TEXT
<<<end TAG>>>
```

- `URI` is `previously://event/<id>`.
- The time is the event's `occurred_at` in UTC.
- `SOURCE` is the source of the event's key, or `unknown` when it has none.
- `SENDER` and `RECIPIENT` are the display name of an identity of the channel, or its address when it has no name.
  The sender is the first identity in the role `from` or `sender`; the recipients are every identity in the role `to`, `cc` or `bcc`.
  Without a sender, the part reads `unknown → RECIPIENT`, without recipients it's the sender alone, and without either it's left out.
- Each field of the heading is kept to one line and cut at 200 characters, the last one an ellipsis.
  After ten recipients, `+N more` stands for the rest.
- `TAG` is eight hexadecimal characters, drawn anew for every result and never a string that occurs in the result's content.
  All fences of one result share the tag.
- Every unit that has content stands under its marker, `#unit-<n>`.
  An erased unit is left out.
  The subject of a mail, where it has one, is its unit 1.

Inside the fence, before the units, an event that `get_event` returns carries these lines as well:

| Line | Content |
|---|---|
| `Attachments: NAME (MEDIA TYPE, N bytes), …` | Every blob the event names except the raw mail, without its content. A blob with no file name is `unnamed`. Each entry is kept to one line and cut at 200 characters, and after ten entries `+N more` stands for the rest. Left out when there's none. |
| `Found in: KEY VALUE, …` | The `found_in` of the payload, its keys sorted. Left out when there's none. |
| `Message-ID: ID` | The external id of an event of the source `email`, unless it starts with `sha256:`. |
| `Source key: SOURCE ID` | The source key of any other event that has one. |
| `Forwarded in: ID` | The `forwarded_in` of the payload. Left out when there's none. |

### Placeholders

An event the policy keeps from the client, and an erased event, stand as one line each:

```text
[withheld: URI — REASON]
[erased: URI]
```

A placeholder holds no subject, no participant, no time and no other content of the event.
`REASON` is cut at 500 characters.

### A cut event

An event that alone is longer than a page is cut, and counts as delivered.
A note after its fence says where the rest is:

```text
… truncated — continue with get_event ids=[42] from_unit=7
… truncated — the rest of unit 3 is not served in the pilot
… truncated — the rest of unit 3 is not served in the pilot; continue with get_event ids=[42] from_unit=4
```

The first is an event cut between two units.
The second and third are an event cut inside a unit, the last of the event or one before others.
The rest of a unit cut inside is served by no call.

### Pages

A result of `previously` or `get_event` ends before it grows past 60,000 characters.
When more follows, the result ends with a footer:

```text
End of page N. More results: call again with cursor=CURSOR
End of page N. More results: call get_event with ids=[ID, ID]
```

The first ends a page of `previously`, the second a page of `get_event`; the second keeps `from_unit=N` when the call gave it.
A result without any item reads `No results.` below the header.

### An example

A page of the chronicle of the circle `huber` since 2026-09-01, with one event shown, one withheld and one erased, and more to follow:

```text
previously · chronicle · circle huber · since 2026-09-01 · page 1 · next: c=eyJhZnRlciI6NDQsImZpbHRlcnMiOnsiY2lyY2xlIjoiaHViZXIiLCJzaW5jZSI6IjIwMjYtMDktMDEifSwicGFnZSI6Mn0

### previously://event/42 · 2026-09-12 09:14 · email · Eva Huber → Jens Klein
<<<customer-content 9c1e04b7>>>
#unit-1
Re: server installation of the foobar connector
#unit-2
The server is up; the TLS access is still missing. By Friday?
<<<end 9c1e04b7>>>

[withheld: previously://event/43 — circle team has no rule, so only local processing is allowed; this client (claude-code) processes with claude-max, which is not local]

[erased: previously://event/44]

End of page 1. More results: call again with cursor=eyJhZnRlciI6NDQsImZpbHRlcnMiOnsiY2lyY2xlIjoiaHViZXIiLCJzaW5jZSI6IjIwMjYtMDktMDEifSwicGFnZSI6Mn0
```

## Sanitizing

Before anything reaches a result, these characters are removed from it, and counted in the header where the result has one:

- the escape sequences of a terminal, introduced by ESC or by their 8-bit forms U+009B, U+009D, U+0090, U+0098, U+009E and U+009F, each counted by its length;
- every control character of the Unicode category `Cc` except the line feed and the tab, which covers C0, DEL and C1;
- every character of the category `Cf`, which covers the zero-width characters and the bidirectional controls;
- lone surrogates;
- the tag characters U+E0000 to U+E007F;
- the variation selectors U+FE00 to U+FE0F and U+E0100 to U+E01EF;
- the combining grapheme joiner U+034F;
- the Hangul fillers U+115F, U+1160, U+3164 and U+FFA0.

In every field kept to one line, such as a field of a heading, a reason or an error, the line feed, the tab and the separators U+2028 and U+2029 become spaces.
The log keeps the stored bytes unchanged.

## Tools

### `previously`

The chronicle: the observations in the order of `occurred_at`, then `id`, that match every filter given.

| Argument | Type | Default | Description |
|---|---|---|---|
| `circle` | string | none | Only events in which a member of the circle takes part, the operator's own identities left out. An erased event drops out of this filter. |
| `source` | string | none | Only events of this source, such as `email`. |
| `since` | string | none | Only events from this time on, inclusive. An ISO 8601 date, which means midnight UTC, or a moment with a zone. |
| `until` | string | none | Only events before this time, exclusive. The same form as `since`. |
| `cursor` | string | none | The cursor from the footer of the previous page. |

The title is `chronicle`, followed by each filter given as `· NAME VALUE`.
Each event is shown with its heading and all its units, or as a placeholder.
A cursor carries the id of the last item the page consumed, the filters and the number of the page it opens, encoded as base64url without padding; it isn't sealed, and grants nothing, because every call decides again.
A cursor for other filters, a malformed one, or one whose id names no observation is refused.

### `get_event`

One or more events in full.

| Argument | Type | Default | Description |
|---|---|---|---|
| `ids` | list of integers | — | 1 to 20 event ids. A repeated id is served once. |
| `from_unit` | integer | none | Start every event at this unit, for the rest of a cut event. |

The title is `get_event · N of M ids`, where `N` counts the distinct ids and `M` the ids given.
Each event is shown with its heading, its units, its attachments and its provenance, or as a placeholder, in the order asked.
An id that can't be served gets a line of its own, and the other ids are served:

```text
Error: previously://event/9 — no event has this id
Error: previously://event/7 — the event is not an observation but an action; get_event serves observations
Error: previously://event/42 — the event has no unit 9 or later to show; its last unit is 4
Error: ids[5] — the id is out of range: an event id is a whole number from 1 to 2^53 - 1
```

### `list_circles`

The circles of the policy, sorted by name, one line each.
It takes no argument.

```text
- NAME · statement: STATEMENT · rule: RULE · N members · this client sees its content
- NAME · statement: STATEMENT · rule: none — only local processing · 1 member · this client does not see it: REASON
```

`STATEMENT` is the statement the circle was set with, or `erased` when its payload was erased.
`RULE` is the rule for `circle:NAME`: `regions REGIONS`, followed, where the rule sets them and separated by commas, by `retention at most N days`, `excludes providers NAMES`, `no training`, `no subprocessors`, `excludes operators NAMES` and `excludes model origins NAMES`.
Whether the client sees the circle is decided for a member of the circle alone; a rule of a source can still narrow it.
No line holds an address.

### `whoami`

The client, its processing chain, the protocol generation of the call, and what the client sees in principle.
It takes no argument.

```text
client NAME
processor NAME: operator OPERATOR · inference SPACE in REGIONS · storage REGIONS · retention N days · training no · subprocessors none · model origin ORIGIN · local no
protocol revision of this call: 2026-07-28
circles:
- circle NAME: sees it
- circle NAME: does not see it: REASON
sources:
- source:NAME: sees it
- content of no circle and no source rule: does not see it: REASON
```

A property the provider didn't declare reads `unknown`, and so does the revision of a call that names none.
A processor that no provider declares reads `processor NAME: not declared`.
The lines under `sources:` are one per rule of a source, then one for content that no circle and no rule of a source covers.

### `policy_gaps`

Where the built-in rule `local_only` acted, as `previously policy gaps` lists it ({ref}`cli-reference`), with the origin of each line: `gate` for the model calls of the gate, `mcp` for what this server withheld for lack of a rule.

| Argument | Type | Default | Description |
|---|---|---|---|
| `since` | string | none | Only what was recorded from this time on. The same form as `since` of `previously`. |

```text
- circle:NAME · gate · N · last YYYY-MM-DD HH:MM UTC
- circle:NAME · mcp · N · last YYYY-MM-DD HH:MM UTC
- source:NAME · mcp · N · last YYYY-MM-DD HH:MM UTC
```

A line of the origin `mcp` names a circle of a withheld event that has no rule; the circles of that event that have one aren't named.
An event of no circle stands under its source as `source:NAME`, as a line of the gate does, or under itself as `event:ID` when it has no source key.

When nothing fell back, the line is `No call fell back to local only.`

### Errors of a call

A call that fails as a whole answers with one sentence after `Error: `, such as these:

```text
Error: the client claude-code is not in force: it was revoked or never added
Error: no circle nowhere exists; list_circles names the circles
Error: since is not an ISO 8601 date, or a moment with a zone, such as 2026-09-01
Error: since has no zone; give a date, or a moment such as 2026-09-01T09:00+02:00
Error: cursor is not valid for these filters; call again without a cursor for the first page
Error: ids takes 1 to 20 event ids, this call gave 0
Error: from_unit is a unit number, 1 or more
Error: the call failed inside the server; its log says why, this result cannot
```

A call of a tool that the SDK refuses before the server runs it, such as one for an unknown tool or with arguments that don't fit the schema, answers `Error: NAME did not run: ` and the wording of the SDK.
The same refusal of a resource or a prompt reaches the client as an error of the SDK, and the call is recorded all the same.

### Reasons for a withheld event

The reason of a placeholder names policy statements only.
Where a circle has no rule for a client that isn't local, the reason code in the access log is `no_rule`, and the sentence is one of these:

```text
circle team has no rule, so only local processing is allowed; this client (claude-code) processes with claude-max, which is not local
circles eva, team have no rule, so only local processing is allowed; this client (claude-code) processes with claude-max, which is not local
no rule covers this content, so only local processing is allowed; this client (claude-code) processes with claude-max, which is not local
```

Where a rule doesn't allow the client's processor, the reason code is `rule`, and the sentence ends in the reason the decision gives ({ref}`policy-and-model-calls`):

```text
the rules of circle:bauer do not allow claude-max, the processor of this client (claude-code): the provider stores in ['us'], outside the allowed ['eu']
```

## Resource templates

`resources/list` returns no resource; the server offers two templates, both of the media type `text/markdown`.

| Template | Name | Content |
|---|---|---|
| `previously://circle/{name}/chronicle` | `circle_chronicle` | The first page of `previously` with `circle` set to `name`. |
| `previously://event/{event_id}` | `event` | The event `event_id`, as `get_event` returns it with `ids` set to it alone. |

The URI of an event is `previously://event/<id>` in either case.
In the revision `2026-07-28` the result of `resources/read` carries `cacheScope` `private` and `ttlMs` `0`: a client may reuse it for no time and only for itself.
An `event_id` that isn't a whole number in ASCII digits is refused:

```text
Error: an event id is a whole number, such as previously://event/42
```

## Prompts

Both prompts return a request to the client that names the tools, and no content of the log.

| Prompt | Arguments |
|---|---|
| `chronicle_summary` | `circle`, required; `since` and `until`, optional. |
| `whats_open` | `circle`, required. |

`chronicle_summary` with `circle` set to `huber` and `since` set to `2026-09-01` returns:

```text
Summarize what happened in the circle huber. Read it with the tool previously (circle=huber, since=2026-09-01) and follow the cursor to the last page; fetch a mail in full with get_event where the chronicle cuts it short. Cite every statement as previously://event/<id>#unit-<n>, and name the events that were withheld.
```

`whats_open` with `circle` set to `huber` returns:

```text
List what is open in the circle huber: questions without an answer, work promised without a sign that it was done, and dates still ahead. Read the chronicle with the tool previously (circle=huber), every page, and fetch single mails in full with get_event. Cite each point as previously://event/<id>#unit-<n>.
```

An argument is repeated sanitized, on one line, and cut at 1,000 characters.

(mcp-access-payload)=

## The access entry `mcp_access`

Every call of a tool, a resource or a prompt that has a client is an event of the kind `action`, with no source key and no units, written after the call has read and before its answer leaves.
A request over HTTP without a valid token writes none, and neither does a request that the transport of the SDK refuses before the server runs, with 421 for a host that isn't allowed or 400 for a protocol version it doesn't take.
`previously access` reads the entries ({ref}`cli-access`).

The keys of the payload:

| Key | Value |
|---|---|
| `action` | `mcp_access`. |
| `client` | The name of the client. |
| `policy` | The ids of the events that decided: `client`, `processor` and `rules`; an empty object where the call found no client in force, or never reached the server's code. |
| `call` | The call: `kind`, `name` and `arguments`. |
| `delivered` | The events that reached the result, each with `event`, `units` and `circles`. |
| `withheld` | The events the policy kept from the client, each with `event`, `reason_code`, `circles`, `reason`, `uncovered` and `source`. |
| `outcome` | `ok`, or `error` for a result that's an error. |
| `era` | The protocol revision of the call, such as `2026-07-28`, or `null` where the call names none. Required. |

The entry of `call`:

| Key | Value |
|---|---|
| `kind` | `tool`, `resource` or `prompt`. |
| `name` | The name of the tool or the prompt, or the template of the resource; for a resource call that the SDK refused, the URI it asked for. |
| `arguments` | The arguments the call gave: a string cut at 1,000 characters and without NUL, a list or an object cut at 50 entries and at a depth of four, a whole number beyond 2^53 − 1 as a string, and only keys that start with a lower-case ASCII letter and go on with lower-case letters, digits and underscores; other keys are left out. A resource records `circle` or `event_id`. |

An entry of `delivered` names the units that appeared on the page, a unit cut inside among them, and the circles of the event when the call was made.
An erased event stands in `delivered` with no units and no circles: it was delivered as its placeholder, and no unit of it reached the client.
An event that didn't fit on the page is in no entry of that call.

An entry of `withheld` carries `reason_code` `no_rule` where a circle had no rule for a client that isn't local, `rule` where a rule said no, the circles of the event, and the sentence of the placeholder.
`uncovered` lists the circles of the event that have no rule, and `source` is the source of the event's key, or `null` where it has none; `policy gaps` counts by these two.

A call of `get_event` that delivered one event and withheld another looks like this:

```json
{
  "action": "mcp_access",
  "client": "claude-code",
  "policy": {"client": 31, "processor": 12, "rules": [19]},
  "call": {"kind": "tool", "name": "get_event", "arguments": {"ids": [42, 43]}},
  "delivered": [{"event": 42, "units": [1, 2], "circles": ["huber"]}],
  "withheld": [
    {
      "event": 43,
      "reason_code": "no_rule",
      "circles": ["huber", "team"],
      "reason": "circle team has no rule, so only local processing is allowed; this client (claude-code) processes with claude-max, which is not local",
      "uncovered": ["team"],
      "source": "email"
    }
  ],
  "outcome": "ok",
  "era": "2026-07-28"
}
```

`verify` holds every `mcp_access` to its form, as {ref}`cli-access` lists.
