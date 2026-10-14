(mcp-tools)=

# Server tools, resources and prompts

The MCP server that `previously mcp` and `previously serve` start offers fifteen tools, two resource templates and two prompts.
Nine of the tools, the templates and the prompts only read.
Six tools write: `write_assertion`, `write_entity` and `write_relation` in two calls, as {ref}`mcp-writing` describes, and `write_approve`, `write_reject` and `write_triage_answer` in one call each, as {ref}`mcp-answering` describes.
Every call that reaches the server's code writes an action `mcp_access` to the log, described at the end of this page.
{ref}`cli-mcp` and {ref}`cli-serve` describe the two commands, the token and the checks of an HTTP request, and {ref}`mcp-interface` explains why the server has this shape.

## The server

The server's name is `previously`, and its version is the version of the installed package.
It sends these instructions to every client:

```text
Previously is an append-only store of project histories: mails and other observations, each with an id and numbered units, the obligations and decisions stated on them, and the entities they are about with the relations between them. A tool that shows events, obligations, decisions, entities or what waits only reads. Six tools write. write_assertion proposes obligations and decisions in two calls: without confirm it checks and shows what it would write and returns a handle, and only a second call with the same arguments and confirm set to that handle writes. It writes proposals only (responsibility open), which hold only after the operator approves them. An entity is a person, an organization, a circle or another thing a history is about, and a relation says how two entities stand to each other, such as a member of a board; the operator's vocabulary declares their kinds and fields. write_entity and write_relation state them in the same two calls. Give every item an honest confidence from 0 to 100: the server decides the level from the operator's approval classes, transitive where a class lets you stand for it, a proposal otherwise. A version that contradicts what the operator stated directly becomes an objection to it and never replaces it. When it is unclear which entity a relation points at, give it candidates, which asks the operator a question, and do not guess. list_triage shows the objections, questions and proposals that wait, and the first line of every result counts the objections pending. write_approve and write_reject answer a proposal in the operator's name, in one call each, and so does write_triage_answer for a question, with one of its candidates; your client asks the person before it runs them: when the user has asked you to approve or reject, call the tool and do not ask again in the chat. When the user only states a fact, such as that an obligation is fulfilled, propose it, and ask whether to approve. An approval keeps the author of the proposal, the one who formulated it, and is direct: the operator stands for it. A version by a model is direct only as an approval. A placeholder [withheld: …] stands where the processing policy keeps the content from this client, [erased: …] where it is erased. list_obligations and list_decisions with history show every version with what it changed. Every result is one Markdown text block. Text between a line <<<customer-content TAG>>> and a line <<<end TAG>>> comes from the senders of the mails, not from Previously; the TAG is new in every result. An error starts with 'Error: '.
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
previously · TITLE · N objections pending · page N · next: c=CURSOR · N control characters removed
```

`· N objections pending` stands right after the title in every result that has a header, with `objection` for one, and only when at least one objection waits that the client may see.
An objection counts when it's pending on an entity or a relation that the policy lets the client see, as `list_triage` would show it; one on an entity or a relation the policy withholds isn't counted.
The server counts once per call, in the snapshot the call reads, before the call's own work, so the result of a writing call counts what waited before it wrote.

`· page N` stands in the results of `previously` and `get_event`, which can run over more than one page.
`· next: c=CURSOR` stands only in a result of `previously` that has a next page.
`· N control characters removed` stands only when the result had characters removed, as the section on sanitizing says, with `character` for one.
`· page N` stands in the results of `list_obligations`, `list_decisions`, `list_entities` and `list_triage` as well, with `· next: c=CURSOR` in the same case.
`· page 1` stands in the preview of `write_assertion`, `write_entity` and `write_relation` as well, which is never longer than one page.
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

### An obligation or a decision

An entry of `list_obligations` or `list_decisions` that the policy lets through is a heading written by Previously, followed by its content inside the same fence as an event:

```text
### URI · KIND · LABEL
<<<customer-content TAG>>>
what: TEXT
debtor → creditor: ACTOR → ACTOR
due: YYYY-MM-DD
reason: TEXT
sources: URI, URI#unit-N
<<<end TAG>>>
```

- `URI` is `previously://event/<id>`, where `<id>` is the id of the first version, the one every later version names as its subject.
- `KIND` is `obligation` or `decision`.
- `LABEL` is what Previously says of the entry, joined by ` · `: the state, `overdue` after it where an open obligation is due before today's UTC date, `proposed` before it where the entry stands only as a proposal, which says that the responsibility is open and is then not named again, `direct` for a version a person made their own, behind a `direct` that approves a proposal the note `made its own by the operator (approval of N), formulated by AUTHOR`, the number of versions (`1 version`, `2 versions`) and the number of proposals still pending.
  It holds nothing from a mail or a client.
- A decision has `decided by: ACTOR, ACTOR` and `on: YYYY-MM-DD` in place of the debtor and creditor and the due date, and `replaces: URI` where it replaces another decision.
  An actor is written as it was stated: `own`, `circle:NAME`, `address:ADDRESS` or `name:TEXT`.
- `sources` names each event as `previously://event/<id>`, and each unit a source cites as `previously://event/<id>#unit-<n>`.
- Every line is kept to one line, cut at 1,000 characters, and sanitized.
  The content of the fence is as foreign as a mail: the text came from a client or from a mail.

An entry is never cut between two pages.
One that doesn't fit goes on the next page.
One that alone is longer than a page is cut after a whole line, and a note after its fence says how many lines are left out:

```text
… truncated — 12 more lines are not shown
```

No call serves the lines left out; `previously obligation ID --history` prints them on the command line.

An entry the policy keeps from the client stands as the placeholder `[withheld: URI — REASON]` below, which holds no text, no actor and no source.
An entry whose every version an erasure took is in no list.
A `subject` that names an assertion an erasure took, while no entry stands under that id, answers with the placeholder `[erased: URI]` in either tool and with or without `history`, as `get_event` answers for an erased event to any client: the erasure took the payload that said which kind and which entry the assertion was.

(mcp-entity-form)=

### An entity or a relation

An entry of `list_entities` that the policy lets through is a heading written by Previously, followed by its content inside the same fence as an event:

```text
### URI · entity · LABEL
<<<customer-content TAG>>>
type: TYPE
language: TAG
field NAME: VALUE
state: STATE
reason: TEXT
sources: URI, URI#unit-N
relation URI: KIND → entity ID NAME · YYYY-MM-DD to (open)
<<<end TAG>>>
```

- `URI` is `previously://event/<id>`, where `<id>` is the id of the first version.
- `LABEL` is what Previously says of the entity, joined by ` · `: the label of its kind, its state with `proposed` before it where it stands only as a proposal, or after it its level, `direct` or `transitive under URI` with the event of the approval class, and `class revoked` where that class was revoked without demoting, then the number of versions and of proposals pending, and `contested by URI` for every objection that waits.
- The label of a kind is the one the vocabulary gives it in the entity's working language, else in the language the server was started with, `PREVIOUSLY_LANGUAGE` or `en`; a label in neither stands in the first language in alphabetical order with its tag in parentheses.
  It holds nothing from a mail or a client.
- `language` stands only where the entity has a working language.
- Each field stands on a line `field NAME: VALUE`, sorted by name.
  A date reads `YYYY-MM-DD`, a period `YYYY-MM-DD to YYYY-MM-DD` with `(open)` for an open end, and a reference `entity ID NAME`, or `entity ID (not shown)` where the client may not see that entity or it's gone.
- `sources` reads `sources: none, the operator's recollection` for what the operator stated from memory.
- Every relation the entity is an end of and that the client sees follows, one line each: its URI, the label of its kind, `→` where it starts at the entity and `←` where it points at it, the other end, the period where it has one, and its level where it isn't direct.
- A relation of `list_triage` has `from: entity ID NAME` and `to: entity ID NAME` in place of the fields of an entity, or `to one of: entity ID NAME, entity ID NAME` for a question, and `period:` where it has one.
- An end of a relation reads `entity ID (erased)`, `entity ID (none stands)` or `entity ID (retracted)` where no entity stands under it any more.
- Every line is kept to one line, cut at 1,000 characters, and sanitized.

An entity the policy keeps from the client stands as the placeholder `[withheld: URI — REASON]`.
The policy decides over the people in the sources of every version that stands, as for an obligation, and over a recollection as a source `recollection` with nobody in it: without a rule for `source:recollection`, an entity that rests on a recollection is withheld from every client that isn't local.
A relation is shown only where the client sees its sources and every entity any of its versions names, the candidates of a question among them; an end whose every version is erased withholds nothing.
A relation the client may not see is left out of the lines of an entity, without a placeholder.

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

### `list_obligations`

The obligations that stand, in the order of their ids.
By default it lists those that a person made their own; an entry that only a model proposed stays out unless `proposals` is set.
An entry a person made their own and that has a proposal pending is in both lists, and its label counts the proposal.

| Argument | Type | Default | Description |
|---|---|---|---|
| `circle` | string | none | Only entries that concern the circle: the circles of its sources, the circles named as parties with `circle:`, and the circles of the addresses named as parties. An entry the policy withholds is found by the circles of its sources alone, so its placeholder under this filter tells that somebody in its sources belongs to the circle, as a placeholder of `previously` with `circle` does. |
| `state` | string | none | Only this state: `open`, `fulfilled` or `cancelled`. |
| `overdue` | true or false | false | Only what's open and due before today's UTC date. |
| `proposals` | true or false | false | List what has a proposal pending, or stands as one, instead of what stands. |
| `subject` | integer | none | The id of one entry. The page shows that entry whatever the other filters say. |
| `history` | true or false | false | With `subject`, show every version in the order written, each with what it changed against the one before. |
| `cursor` | string | none | The cursor from the footer of the previous page. |

The title is `list_obligations`, followed by each filter given as `· NAME VALUE`.
A cursor carries the id of the last entry the page consumed, the filters and the page number, as the cursor of `previously` does; one for other filters, for the other tool or a malformed one is refused.

The policy decides for each entry on its own, over the people in the sources of all versions that stand, one decision for each distinct source, and the first that allows nothing holds: the strictest rule wins.
The parties an entry names take no part in it, so a creditor from a circle without a rule doesn't withhold an entry whose sources have one.
With `history`, the verdict is still the entry's, over the sources of all versions together and of the rejections the history shows.

The policy decides before `state`, `overdue` and `proposals` look at an entry.
An entry it withholds passes those three whatever they ask, so its placeholder stands under every one of them alike and none of them tells what the entry holds.

A `subject` that names no entry of this kind answers with a line of its own on the page:

```text
Error: previously://event/9 — no obligation stands under this id
```

The history goes inside the fence of the entry, in place of its content.
It shows the first version with `set` lines, each later one with `change` lines, and each rejection with its reason, in the order written:

```text
version 25 · 2026-10-11T12:00:00.000000Z · direct · human:operator
set what: send the offer for the roof
set debtor → creditor: own → address:eva.huber@example.org
set due: 2099-01-01
set reason: none
set sources: previously://event/21
version 26 · 2026-10-11T12:00:00.000000Z · direct · human:operator
change due: 2099-01-01 → 2099-02-01
change reason: (none) → postponed
version 27 · 2026-10-11T12:00:00.000000Z · open · model:claude-code · rejected
change due: 2099-02-01 → 2099-03-01
change reason: postponed → (none)
rejection 28 · 2026-10-11T12:00:00.000000Z · human:operator · rejects 27
reason: rejected (by the operator) — the date stands
```

A version that was approved or rejected says so at the end of its first line.
One that approves a proposal ends with the note `made its own by the operator (approval of N), formulated by AUTHOR`: it's direct, so the operator stands for it, and its author is the one who formulated the proposal.
A rejection is a line `rejection`, its id, the time, its author and `rejects N`, followed by the line `reason: rejected (by the operator) — ` and its reason, or `none`.
The payload doesn't record through which channel the operator answered; the `mcp_access` of an MCP call does.
With `history`, an entry whose versions are all rejected proposals answers too, labelled `no version stands`.

### `list_decisions`

The decisions that stand, in the order of their ids.
It takes the arguments of `list_obligations` except `overdue`.

| Argument | Type | Default | Description |
|---|---|---|---|
| `circle` | string | none | Only entries that concern the circle: the circles of its sources, the circles named as deciders with `circle:`, and the circles of the addresses named as deciders. |
| `state` | string | none | Only this state: `valid` or `revoked`. |
| `proposals` | true or false | false | List what has a proposal pending, or stands as one, instead of what stands. |
| `subject` | integer | none | The id of one entry. |
| `history` | true or false | false | With `subject`, show every version, each with what it changed. |
| `cursor` | string | none | The cursor from the footer of the previous page. |

The title, the entries, the policy, the cursor and the history are those of `list_obligations`.

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

### `list_entities`

The entities that stand, in the order of their ids, each with the relations it's an end of, as {ref}`mcp-entity-form` describes it.
By default it lists those the operator stands for, direct or transitive; an entity that only a model proposed stays out unless `proposals` is set.
A retracted entity stays out unless `state` asks for `retracted`, or `proposals` is set.
A placeholder for an entity the policy withholds stands under every filter alike, `state` included, so a client learns that the entity exists and never its state or its kind.

| Argument | Type | Default | Description |
|---|---|---|---|
| `types` | list of strings | none | Only entities of these kinds, as the vocabulary names them. |
| `state` | string | none | Only this state: `active`, `closed` or `retracted`. A retracted entity you can see is left out unless this is `retracted`; a placeholder stands whatever is asked. |
| `proposals` | true or false | false | List what has a proposal pending, or stands as one, instead of what stands. |
| `subject` | integer | none | The id of one entity. The page shows that entity whatever the other filters say. |
| `history` | true or false | false | With `subject`, show every version in the order written, each with what it changed against the one before. |
| `cursor` | string | none | The cursor from the footer of the previous page. |

The title is `list_entities`, followed by each filter given as `· NAME VALUE`, the kinds of `types` separated by commas.
The cursor, the placeholder of an entity the policy withholds and its passing every filter that looks at the content are those of `list_obligations`.
A `subject` that names no entity answers with a line of its own on the page:

```text
Error: previously://event/9 — no entity stands under this id
```

The history shows each version with a first line of its id, its time, its level, `under URI` for a transitive one, its author, `contests URI` for an objection, and `rejected` or `approved`, and below it `set` lines for the first version and `change` lines for each later one.

### `list_triage`

What waits for the operator among the entities and relations the client may see, in three sections, each in the order of the ids:

1. `objection`: a version by a model that contests the direct version that stands.
2. `question`: a relation that names candidates in place of the entity it points at.
3. `proposal`: every other version that waits, a new entity or relation that only a model proposed among them.

What waits on an entity or a relation the policy keeps from the client is left out, without a placeholder, as the header leaves it out of its count.

| Argument | Type | Default | Description |
|---|---|---|---|
| `cursor` | string | none | The cursor from the footer of the previous page. |

The title is `list_triage`.
Each item is a heading and a fence:

```text
### URI · SECTION · KIND · LABEL · LEVEL · by AUTHOR · version of URI
```

`URI` is the version that waits, the id to answer it with, and `SECTION` its section.
`KIND` is `entity` or `relation`, and `LABEL` the label of its kind.
`LEVEL` is `proposed` or `transitive under URI`.
`contests URI` follows the author on an objection, and `new entity` or `new relation` stands at the end in place of `version of URI` where the version is the first of its thread.
Inside the fence stands the content of the version, and where another version stands, a line `change NAME: OLD → NEW` for every field it would change.
A cursor carries the section and the id of the last item the page consumed.

(mcp-writing)=

### Writing in two calls

`write_assertion`, `write_entity` and `write_relation` take two calls.
Called without `confirm`, a tool checks what it would write, shows it, and returns a handle, and it writes nothing.
Called again with the same arguments and `confirm` set to that handle, it writes, and only then.

The preview is a page titled `TOOL · preview`, with a heading and a fence for each statement, as an entry of `list_obligations` has them, and three lines after the last fence:

```text
handle: HANDLE
expires: YYYY-MM-DD HH:MM:SS UTC
Nothing is written yet: to write, call write_assertion again with the same arguments and confirm=HANDLE.
```

- The heading of a proposal reads `### statement N · KIND · proposed · STATE · by model:CLIENT · new entry`, with `new version of URI` at its end where the item names a `subject`.
- The heading of an entity or a relation reads `### statement N · KIND · LABEL · LEVEL · by model:CLIENT · new KIND`, with `new version of URI` at its end where the item names a `subject`, and its content is that of {ref}`an entry of list_entities <mcp-entity-form>`.
  `LEVEL` is the level the write path gives the claim now, `proposed` or `transitive under URI`, and `objection to URI` follows `proposed` where the claim contests the direct version `URI`.
- A list cuts a line inside the fence at 1,000 characters, so a statement with a longer line is refused instead of previewed: a preview always shows the whole of what gets written.
- A preview that doesn't fit on one page is refused rather than cut, because a statement nobody saw can't be confirmed.

The handle is sealed with `PREVIOUSLY_MCP_CONFIRM_KEY` ({ref}`configuration-reference`) over the client, the statements and the time it expires, ten minutes after the first call.
It holds no word of the statements, and it opens only for the client it was sealed for and for the same statements.
A handle of `write_entity` and `write_relation` holds as well the level, the approval class and the contested version the preview showed for each item, and the confirmation is held to them.
A handle of `write_assertion` doesn't confirm a call of the other two tools, and the other way around.

The confirming call answers with the ids it wrote, one line each, under the title `TOOL · written`:

```text
previously · write_assertion · written

assertion 52
assertion 53
```

An entity or a relation written answers `assertion N · LEVEL`, with the level it was written at.
Every statement written carries the handle's identifier.
Confirming the same handle again writes nothing and answers with the same ids, so a call repeated after a lost answer writes once.

A handle that doesn't let the call write is refused with one of these sentences:

```text
Error: the handle is not one this server sealed; call again without confirm for a new one
Error: the handle was sealed for another client; call again without confirm for a new one
Error: the handle was sealed for other statements than these; call again without confirm for a new one
Error: the handle has expired: a handle holds for 10 minutes; call again without confirm for a new one
```

A confirmation of `write_entity` or `write_relation` whose level moved since the preview is refused, and nothing is written: `the approval class changed since the preview; call again without confirm` where a class was set or revoked in between, and `a direct version was written since the preview; call again without confirm` where a direct version made the claim an objection, or one to another version.

A source, an entry or a proposal that the client may not see is refused with the same sentence as an id that names nothing, so the answer doesn't tell whether it exists.
So is an entity: a `subject` the client may not see is refused with `the subject N names no entity or relation that stands`, and an end of a relation or an entity a reference field names with the sentence the vocabulary check gives for one that doesn't stand, such as `an end of the relation is not an entity that stands`.
The refusals of the server are these, each with nothing written:

```text
Error: writing is not configured on this server
Error: event 43 is not one this client can use as a source
Error: subject 25 is not an entry this client can see
Error: replaces 30 is not an entry this client can see
Error: event 26 is not a proposal this client can answer
Error: items takes 1 to 20 statements, this call gave 21
Error: item 1: kind is obligation or decision; write_reject rejects a proposal
Error: item 1: an obligation needs debtor and creditor
Error: item 1: by belongs to a decision, not to an obligation
Error: item 1: due is not a date written YYYY-MM-DD
Error: item 1: an event id is a whole number from 1 to 2^53 - 1
Error: ids takes 1 to 20 different proposals, this call gave 0
Error: ids holds an id that is not a whole number from 1 to 2^53 - 1
Error: proposal is not a whole number from 1 to 2^53 - 1
Error: question is not a whole number from 1 to 2^53 - 1
Error: choice is not a whole number from 1 to 2^53 - 1
Error: item 1: a relation names to or candidates, one of the two
Error: item 1: a period is not written with dates YYYY-MM-DD
Error: event 26 is a question: answer it with write_triage_answer
Error: one call approves obligations and decisions, or entities and relations, not both
Error: event 30 is no question that waits
Error: event 31 is of a kind the gate reads; a circle or a membership is approved on the command line
Error: the answer names 12, which is none of the candidates
Error: a line of these statements is longer than the 1,000 characters a preview shows of it; shorten it
Error: the preview of these statements is longer than a page; write fewer in one call
```

The first is the answer of every writing tool when the server has no `PREVIOUSLY_MCP_CONFIRM_KEY`, or one shorter than 32 characters; the reading tools work as before.

Every other refusal is a sentence of the write path, the same that `previously assert`, `entity`, `relate`, `approve`, `reject` and `answer` print ({ref}`cli-reference`), such as `Error: the proposal 26 is already approved` or `Error: event 41 is erased and cannot be a source`.

(mcp-answering)=

### Answering a proposal in one call

`write_approve`, `write_reject` and `write_triage_answer` write in one call, with no preview, no `confirm` and no handle.
The client's own prompt before the call is the person's confirmation: a preview would only ever reach the model, because the prompt shows the person the arguments and nothing else.
The checks run in the order of the write path: the entry and every source of the proposal must be visible to the client, then the write path's checks, then the write.
Nothing is written when one fails.

An answer that stands already is a success and writes nothing, so a call repeated after a lost answer is harmless.
For `write_approve`, that's an approval of the same proposal with the same content, sources, author and reason; the call answers with the id of that approval.
For `write_reject`, that's a rejection of the same proposal with the same reason by the same client.
For `write_triage_answer`, that's an answer to the same question with the same candidate and reason.
A call that names both new and standing proposals writes the new ones and lists all the ids in the order asked.
An approval or a rejection that differs, such as one with another reason, or a proposal that something else answered, is refused as the write path refuses it:

```text
Error: the proposal 26 is already approved
Error: the proposal 26 is already rejected
```

The answer has the title `TOOL · written` and one line `assertion N` for each id.
Each concerns an event or an entry the client may see, or an event that `get_event` names to any client: an erased one, or one that's no observation.

### `write_assertion`

Proposes obligations and decisions.
What it writes is always a proposal: the author is `model:` and the name of the client, and the responsibility is `open`, so it never outranks a version a person stated and stands until a person approves or rejects it.

| Argument | Type | Default | Description |
|---|---|---|---|
| `items` | list of objects | — | 1 to 20 obligations or decisions, written in one transaction. |
| `confirm` | string | none | The handle of the preview. |

The title is `write_assertion`.
Every source has to be an observation the client may see, and a `subject` or a `replaces` an entry the client may see.

#### The fields of an item

| Field | Kind | Required | Description |
|---|---|---|---|
| `kind` | both | yes | `obligation` or `decision`. |
| `sources` | both | yes | The events it rests on, at least one, each an object with `event`, the id, and `units`, the units cited in ascending order, left out for the whole event. |
| `what` | both | yes | The text of the obligation or of the decision. |
| `state` | both | no | `open`, `fulfilled` or `cancelled` for an obligation, `open` when left out; `valid` or `revoked` for a decision, `valid` when left out. |
| `reason` | both | no | Why this version, for the history. |
| `subject` | both | no | The id of the entry this is a new, complete version of. |
| `debtor`, `creditor` | obligation | yes | Who owes and who is owed: `own`, `circle:NAME`, `address:ADDRESS` or `name:TEXT`. |
| `due` | obligation | no | By when, `YYYY-MM-DD`; it may lie in the past. |
| `by` | decision | yes | Who decided, a list of references as for `debtor`. |
| `on` | decision | yes | When it was decided, `YYYY-MM-DD`. |
| `replaces` | decision | no | The id of the decision it replaces. |

A field of the other kind is refused, and so is a field the table doesn't name.
An item with `subject` says everything that holds after it: nothing is taken over from the version it changes.

### `write_entity`

States entities in two calls, as {ref}`mcp-writing` describes.
The author is `model:` and the name of the client, and the level is the write path's, never the client's: `transitive` under an approval class in force that covers the client, the kind of entity and the confidence of the item, and open otherwise.
A version of an entity whose winner is direct is always an open objection to that version, whatever its confidence and any class: it never replaces what the operator stated.

| Argument | Type | Default | Description |
|---|---|---|---|
| `items` | list of objects | — | 1 to 20 entities, written in one transaction. |
| `confirm` | string | none | The handle of the preview. |

The title is `write_entity`.
Every source has to be an observation the client may see, and a `subject` and every entity a reference field names an entity the client may see.

#### The fields of an entity

| Field | Required | Description |
|---|---|---|
| `type` | yes | The kind of entity, as the vocabulary declares it. |
| `fields` | yes | The fields the kind declares, by name, `name` among them: a text, a date `YYYY-MM-DD`, a period as an object with `from` and `to`, each a date or left out for an open end, or the id of an entity for a reference. |
| `sources` | yes | The events it rests on, at least one, as for `write_assertion`. |
| `confidence` | yes | How sure the client is, a whole number from 0 to 100. |
| `language` | no | The working language of the entity, a tag such as `de` or `pt-BR`. |
| `state` | no | `active`, `closed` or `retracted`; `active` when left out. |
| `reason` | no | Why this version, for the history. |
| `subject` | no | The id of the entity this is a new, complete version of. |

A field the table doesn't name is refused, `responsibility` among them.
An item with `subject` says everything that holds after it: nothing is taken over from the version it changes.

### `write_relation`

States relations in two calls, with the levels, the objections and the checks of `write_entity`.
A relation that names candidates in place of the entity it points at is a question, and always open: no class answers it in advance.
No class covers a relation kind with the behavior `acyclic`, such as `part_of`, so a version of one is always open, and a client's version is never refused for closing a cycle: that refusal would tell it about relations it may not see.
The cycle rule holds the operator's versions, approvals and answers instead.

| Argument | Type | Default | Description |
|---|---|---|---|
| `items` | list of objects | — | 1 to 20 relations, written in one transaction. |
| `confirm` | string | none | The handle of the preview. |

The title is `write_relation`.
Every source has to be an observation the client may see, and the start, the end or every candidate and a `subject` an entity or a relation the client may see.

#### The fields of a relation

| Field | Required | Description |
|---|---|---|
| `type` | yes | The kind of relation, as the vocabulary declares it. |
| `from` | yes | The id of the entity it starts at. |
| `to` | one of two | The id of the entity it points at. |
| `candidates` | one of two | 2 to 5 ids of entities it may point at, for a question. |
| `sources` | yes | The events it rests on, at least one, as for `write_assertion`. |
| `confidence` | yes | How sure the client is, a whole number from 0 to 100. |
| `period` | no | When it held, an object with `from` and `to` as for a period field, for a kind with the behavior `period`. |
| `fields` | no | The fields the kind declares, as for `write_entity`. |
| `state` | no | `standing` or `retracted`; `standing` when left out. |
| `reason` | no | Why this version, for the history. |
| `subject` | no | The id of the relation this is a new, complete version of. |

### `write_triage_answer`

Answers a question in one call, as {ref}`mcp-answering` describes, as `previously answer` writes it.
The answer is the approval of the question with `to` set to the candidate chosen: direct, with the sources, the confidence and the author of the question, which the operator now stands for.

| Argument | Type | Default | Description |
|---|---|---|---|
| `question` | integer | — | The id of the question, as `list_triage` names it. |
| `choice` | integer | — | The id of the candidate the relation points at. |
| `reason` | string | none | Why this candidate, for the history; the reason of the question when left out. |

The client has to be allowed to see the relation of the question and every source of it.
A question it may not see, a version that's no question, and one answered or overtaken already are all refused with `event N is no question that waits`, and a choice that's none of the candidates with `the answer names N, which is none of the candidates`.
To answer with an entity that isn't a candidate, reject the question and state the relation.
A question of a kind the gate reads, `member_of` or `in_circle`, is refused with `event N is of a kind the gate reads; a circle or a membership is approved on the command line`, before anything is written; the operator answers it with `previously answer` ({ref}`graph-gate-kinds`).
An answer of a relation over an acyclic kind that would close a cycle is refused with `the relation would close a cycle over a kind that is acyclic`, which counts relations the client may not see too.
That sentence tells a call the person confirmed one bit about them, as it does for `write_approve`.
The tool carries `_meta` with `"anthropic/requiresUserInteraction": true` in `tools/list`, the mark that makes Claude Code ask the person before every call, as `write_approve` and `write_reject` do.

### `write_approve`

Approves proposals in one call.
Each becomes a direct version of its entry with the content, the sources and the author of the proposal, and the reason of the proposal, as `previously approve` writes it.
A proposal is a version of an obligation or a decision, or of an entity or a relation, an objection and a transitive version among them; one call approves one of the two families.
A question isn't approved: `write_triage_answer` answers it.

| Argument | Type | Default | Description |
|---|---|---|---|
| `ids` | list of integers | — | 1 to 20 different ids of proposals, as the history of an entry names them. A repeated id is approved once and counted once. |

The client has to be allowed to see the entry of each proposal and every source of it.
Only a proposal that's pending, or that stands because the entry has no direct version, is approved: one that a direct version came after is refused, as `previously approve` refuses it, and `write_reject` still takes it.
It writes in one call and is idempotent, as {ref}`mcp-answering` describes.
A proposal of a kind the gate reads, a `circle`, a `member_of` or an `in_circle`, is refused with `event N is of a kind the gate reads; a circle or a membership is approved on the command line`, and nothing of the call is written; the operator approves it with `previously approve` ({ref}`graph-gate-kinds`).
`write_reject` takes such a proposal like any other.
An approval of a relation that would close a cycle over an acyclic kind is refused with `the relation would close a cycle over a kind that is acyclic`, which counts relations the client may not see too.
That sentence tells a call the person confirmed one bit about them, and it's the one way an MCP client learns of a cycle.
The approval counts as the operator's because the client asks the person before the call; a client that calls `write_approve` without asking writes approvals nobody looked at.
The tool carries `_meta` with `"anthropic/requiresUserInteraction": true` in `tools/list`, the mark that makes Claude Code ask the person before every call.
`write_reject` and `write_triage_answer` carry it too, and no other tool does.

### `write_reject`

Rejects one proposal in one call, as {ref}`mcp-answering` describes.
The rejection is direct, its author is `model:` and the name of the client, and it takes the sources of the proposal, so that it goes with the proposal when one of them is erased.
The proposal may be a version of an entity or a relation as well, an objection, a question or a transitive version among them.

| Argument | Type | Default | Description |
|---|---|---|---|
| `proposal` | integer | — | The id of the proposal, as the history of an entry names it. |
| `reason` | string | none | Why the proposal isn't taken. |

The client has to be allowed to see the entry of the proposal and every source of it, as for `write_approve`.
A rejected proposal leaves the list of proposals and stays in the history.
The tool carries `_meta` with `"anthropic/requiresUserInteraction": true` in `tools/list`, the mark that makes Claude Code ask the person before every call.
`write_approve` and `write_triage_answer` carry it too, and no other tool does.

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
Error: state takes one of open, fulfilled, cancelled
Error: subject is the id of an entry, a whole number from 1 to 2^53 - 1
Error: state takes one of active, closed, retracted
Error: subject is the id of an entity, a whole number from 1 to 2^53 - 1
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

An obligation or a decision stands in `delivered` and `withheld` under its id, with no units and with the circles of its sources.
`rules` of `policy` holds the rules of every distinct source of every entry that reached the page.
The arguments of `list_obligations` and `list_decisions` are a circle name, a state, flags and an id, and the entry holds no text of an obligation or a decision and no address.
An entity stands in `delivered` and `withheld` under its id in the same way, with the circles of the sources of all its versions, and an item of `list_triage` in `delivered` under the id of the version shown; the arguments of `list_entities` are kinds of the vocabulary, a state, flags and an id.

A call of a writing tool records none of its arguments as given, because the text a client writes can come from a mail and would outlive the erasure of that mail in the log.
A call of a tool name the server doesn't have records only the names of its arguments, each with `null`, for the same reason: a misspelled writing tool carries the text it meant to write.
Its `arguments` hold only these keys, for a call the SDK refused as well:

| Key | Value |
|---|---|
| `statements` | How many statements the call names. |
| `sources` | `write_assertion`, `write_entity` and `write_relation`: the ids of the source events, ascending, each once. |
| `proposals` | `write_approve`, `write_reject` and `write_triage_answer`: the ids of the proposals or of the question answered. |
| `ends` | `write_relation`: the ids of the entities its items name as `from`, `to` and candidates, ascending, each once; `write_triage_answer`: the candidate chosen. |
| `confirm` | `write_assertion`, `write_entity` and `write_relation`: `true` where the call gave a handle. |
| `written` | The ids written, or found written by an earlier confirmation of the same handle; empty for a preview, a refusal, and an answer that stood already. |

A call of `write_approve`, `write_reject` or `write_triage_answer` answers a proposal it read, so it records the proposal's entry in `delivered`, with the circles of its sources, and its rules in `rules` of `policy`, as `list_obligations` records it; `previously access --circle` finds it.

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
