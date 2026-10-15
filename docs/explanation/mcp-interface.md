(mcp-interface)=

# About the client interface

The Model Context Protocol, MCP, is the surface the operator works through.
The operator asks a question, a client such as Claude Code, Mistral Vibe or a local harness turns it into calls, Previously answers with evidence, and the client does the judging.
"What's open with customer X?" needs no model inside Previously, because in that moment the client is the intelligence.

This page explains the choices that shape the server of the pilot's fourth unit: why a client is treated as a processor, why every result is a single block of text, why the fence around a mail is a bet rather than a boundary, why the record of every call lives in the log, and why the older generation of the protocol holds nothing up.
It ends with the limits the pilot names and leaves.
{ref}`mcp-tools` lists the tools, the form of a result and the access entry field by field, {ref}`connect-claude-code-and-vibe` shows how to connect the two clients, and {ref}`cli-mcp` and {ref}`cli-serve` describe the two commands that start the server.

(mcp-client-processor)=

## A client is a processor

Whatever a client sees goes to whoever runs its model.
What Claude Code sees goes to Anthropic, what Vibe sees goes to Mistral, and what a harness against a local model sees stays on the operator's hardware.
So a client isn't a neutral window onto the log.
It's a processor in the sense the gate already knows, and the same policy decides about it.

The maintainer took that decision on 2026-10-10, and the rest of the design follows from it.
A client is a principal with a name and a processing chain: `previously client add` writes it as a policy event of the kind `client`, which names a declared provider as its processor.
For every event a call would show, the server asks `decide`, the function the gate uses, with the participants and the source of the event and with the client's chain as the only candidate.
An event that doesn't pass comes back as a placeholder with its URI and the reason, and without its subject or its participants, because those are content too.
{ref}`processing-policy` explains how that decision is built, and the server adds nothing to it.

One consequence is deliberate and easy to trip over.
Without a rule, only a local processor may see content, and that default holds for clients too.
A circle without a rule is invisible to every client that isn't local, so before Claude Code sees the chronicle of a customer, the customer's circle needs a rule that allows the chain of Claude Code.
The server makes that visible in three places: the placeholder names the reason, `whoami` says what a client sees in principle, and `policy_gaps` lists where the default acted, apart for the gate and for this server.

A chain is more than a provider's name.
Claude Code under a Max plan runs under consumer terms and isn't the same chain as the Anthropic API that the gate calls; a model of one company may run at another company in another region; a broker passes requests to subprocessors that change.
So a provider's promise gained four properties with this unit, the operator, whether it trains on its input, its subprocessors and the origin of its model, and a rule can restrict each of them.
A value that isn't known fails a restriction that concerns it, as an unknown retention already did.
That holds for a local provider as well: a rule that forbids training doesn't take the word `local` as an answer to the question whether the provider trains, so a local provider that a restricted circle should reach has to declare it.

What isn't content of a customer, the server tells every client: the names of the circles, their rules, how many members each has, and the promises of the providers.
Those are statements of the operator.
The addresses of the members aren't among them, because they're identities of third parties.

(mcp-text-block)=

## Every result is one block of text

The protocol offers richer results than text: structured content beside the text, a link to a resource, several blocks.
The pilot measured, on 2026-10-10, what of each actually reaches the model in the two clients the maintainer works with, Claude Code 2.1.289 and Mistral Vibe 2.26.1, against a server built for the purpose and thrown away afterward.
The results decided the form:

| Form of the result | Claude Code 2.1.289 | Vibe, default harness | Vibe, `--legacy-harness` |
|---|---|---|---|
| One text block | Arrives whole. | Arrives. | Not measured. |
| Text and structured content | Only the structured content arrives; the text is missing. | Only the structured content arrives; the text is missing. | Not measured. |
| Two text blocks | Both arrive, joined without a separator. | Both arrive. | Not measured. |
| An error with structured content | Only the text arrives, marked as an error. | Nothing arrives. | Not measured. |
| An error with text only | Not measured. | Not measured. | The text arrives, but the error flag is lost. |
| Text and a resource link | Both arrive. | Nothing arrives, the text included. | Not measured. |
| An embedded resource | Arrives. | Arrives. | Not measured. |
| A number of 2^60 + 1 in structured content | Rounded, and the exact number in the text is missing. | The whole turn ends with an error. | Not measured. |
| A source cited as a URI in the text | Not measured. | Not measured. | Arrives exactly. |

Structured content and a resource link each cost content in at least one client, and in Vibe sometimes the whole result.
Two text blocks and an embedded resource arrived in both clients, though Claude Code joins two blocks without a separator.
Nothing the server returns needs more than one block, and one text block is the form both clients carry whole.
What holds in both is narrow, and the server keeps to it: one Markdown text block per result, no structured content and no resource link, sources cited by URI inside the text, no number above 2^53, and an error that says it's an error in its first word.
The server sets the protocol's error flag as well, and relies on it nowhere, because one of the two clients drops it.

Citations are the reason the URI matters.
An event is `previously://event/<id>` and a unit within it `previously://event/<id>#unit-<n>`, and a client that quotes one hands the operator an event id that `previously show` prints.

(mcp-fence)=

## The fence is a bet, not a boundary

A mail is text that a stranger wrote, and the model that reads it also holds tools.
A mail can contain sentences addressed to that model, which is what prompt injection means.
The server can't stop a model from following them, and it doesn't pretend to.

What it does is mark the foreign text.
Every event comes with a heading that Previously writes, and the content of the mail follows inside a fence, `<<<customer-content TAG>>>` to `<<<end TAG>>>`.
The tag is eight hexadecimal characters drawn from `secrets` for every answer, and drawn again if the content of the answer happens to contain it, so a mail can't know the tag in advance and can't close the fence early.
The server's instructions tell the client that the text inside comes from the senders of the mails.
The subject, the names of attachments and the provenance of a mail stand inside the fence too, because the mail supplied them.

That's a bet on how models treat marked text, and the effect of such marking on current models hasn't been measured.
The boundary that holds lies elsewhere.
Most tools only read, and `write_assertion` only proposes: a proposal never outranks a statement of the operator.
`write_approve` and `write_reject` do write direct versions, which the operator stands for, and what makes them the operator's is that the client asks the person before it calls them.
That's a requirement on the client, which the server can't check: a client that allows the two tools without asking writes approvals nobody looked at.
Each writing tool's name starts with `write_`, so that one pattern per client can make the client always ask before any of them, and `write_assertion` takes two steps, a preview and a confirmation, where an answer is one call ({ref}`assertions-proposals`).
And before any of this, the policy decides which content reaches the client at all.

The fence has two named gaps.
Inside it, a mail can write a line that looks like the marker of a unit, such as `#unit-3`; the effect is a misleading citation inside text that nobody trusts anyway, and the pilot leaves it at that.
Outside it, the heading carries the display names of the sender and the recipients, because that's where a reader expects them.
A mail supplies those names, so they're cleaned like everything else, kept to one line, cut at 200 characters each and to ten recipients with a count of the rest, which still leaves about 2,200 characters of names per event that a mail chose and that stand outside the fence.

### Characters that a reader can't see

A mail can carry characters that a terminal interprets or that a reader never sees: escape sequences, zero-width characters, bidirectional controls, the tag characters of Unicode.
Some of them hide text from the operator and show it to the model.
The variation selectors are the sharpest case: there are 256 of them, so a mail can smuggle one byte per invisible character.
The server removes all of these from what it shows, counts them, and says so in the header of the answer; {ref}`mcp-tools` lists them.

They're removed **on output only**.
The stored bytes are part of the hash chain, and changing them would break the chain or require an erasure, so the log keeps them and `verify` stays green.
Removing the variation selectors costs emoji their choice of presentation, and removing the Hangul fillers harms Korean text; the customers of the pilot write German, and the stored bytes keep everything, so the pilot accepts both.

(mcp-access-log)=

## The record of every call lives in the log

Every call that reaches the server's code, whether of a tool, a resource or a prompt, becomes an event of the kind `action` with `payload.action` set to `mcp_access`.
There's no second store of truth beside the knowledge store, and an access log kept elsewhere would be one.
In the log, the question "what has Claude seen of customer X?" has the same answer for anybody who reads the chain, and `previously access` reads it.

The entry holds no content: the client, the ids of the policy events that decided, the call with its arguments, the events delivered with the units that appeared and the circles they belonged to at the time, the events withheld with a reason, the outcome and the protocol generation.
Because it holds no content, an erasure has nothing to take from it; its ids then point at tombstones.
The circles are recorded with each event so that a call of `get_event` by id is found under the circle of the event, and not only a call that named the circle in its arguments.

The entry records what reached the page, not what the server read.
A page ends before it would grow past its limit, and an item that didn't fit was never seen by the model, so it belongs to the entry of the next page; a unit that was cut appeared in part, and is listed.

The entry is written after the call has read and before its answer leaves, in a transaction of its own.
So no answer reaches a client without its entry.
A write that fails replaces the answer with the error of the SDK, and the client gets no content.
A request without a valid token writes nothing, because no principal exists to write it for, and over HTTP that includes the token of a client revoked since: it no longer resolves to anybody.
Two refusals of the transport of the SDK write nothing either, although the token was valid: a host that the check against DNS rebinding doesn't allow gets 421, and a protocol version the transport doesn't take gets 400, both before any code of the server runs.
On standard input and output the client is fixed when the process starts, so a client revoked while it runs gets an error from its next call on, and that call is recorded with the outcome `error`.
A call that the SDK refuses before any function of the server runs, such as one for an unknown tool or with arguments that don't fit the schema, is recorded too, by a hook that the SDK offers for every message.

(mcp-generations)=

## The older generation holds nothing up

Two generations of the protocol are in use, and the two clients sit on different sides.
Measured on 2026-10-10, Claude Code 2.1.289 speaks the revision `2026-07-28`, and Vibe 2.26.1 speaks `2025-11-25`, knows only tools, opens a connection for every call, and in its default harness keeps the list of tools across sessions.

The maintainer decided on 2026-10-10 that the design follows the newer generation.
The older one gets what the SDK gives it without code of its own in Previously: one switch, a server without sessions, which answers both handshakes at the same address.
No code of Previously branches on the generation; the access entry records it, and that's all.
A feature that would need such a branch doesn't come to the older generation.
Vibe is the test that every capability is reachable through a tool, which is why resources and prompts are only shortcuts for the clients that know them, and it's not a brake on what only a modern client can do.
When Vibe speaks the newer generation, the switch and the test of the older handshake go.

(mcp-tool-list)=

## A stable list of tools

Vibe's default harness didn't see two tools that a restarted server offered, and didn't ask the server again.
So the list of tools changes only with a release, after which the clients connect again, and a test holds the names, descriptions and schemas against a checksum, which makes every change to them a deliberate one.
No change has broken a call yet; one that would comes under a new name, and the old one stays for one release.

The descriptions and the server's instructions are declarative.
They name no data of a customer, and they tell the model nothing beyond how to use a tool, because they reach every client before any policy has decided anything.

(mcp-token)=

## A token, not the network

Over HTTP, each client presents a static token as `Authorization: Bearer`, and the server looks it up in the policy on every request, so a replaced or revoked token stops working at the next one.
The lookup and the call aren't one read, though.
The wrapper turns the token into the name of a client, and the call then finds that client by name in its own, later read of the policy.
A `previously client add` for the same name that commits in between, or a revocation followed by a new `client add`, has the one request that carried the old token served under the new record, which may name another processor.
The window is that one request, and the pilot leaves it open.
The token stays required inside a closed network too.
The network tells the server that somebody from inside asks; the token tells it which client, and the access log needs exactly that.
A header that names a client is no identity.

`previously serve` speaks plain HTTP and has no setting for TLS.
A token on a path that somebody else can read is a token that somebody else holds, so the path from a client to the server has to be encrypted or private: the address `127.0.0.1` of the same machine, a port-forward, a private network, or TLS ended in front of the server.
Which one is the environment's choice; {ref}`environment-requirements` lists it with the other requirements.

The SDK has a token verifier of its own, and the server doesn't use it.
With it, the SDK publishes metadata that sends a client to an authorization server, and there is none.
So a small wrapper of the server's own checks the token, and moving to an authorization server later replaces that wrapper and nothing else.

One request passes without a token: `GET /healthz`, the probe that tells a deployment whether the server is ready.
It answers `ok` after one read of the graph projection's state row, or 503 when the database doesn't answer, and it reaches no MCP, returns no data and writes no entry.
It also answers 503, with a body of its own, while the graph projection isn't at the version this release declares: every graph call would fail meanwhile, since only `previously project` builds the projection ({ref}`graph-readers`), and a pod that isn't ready gets no requests.
That's what keeps a rolling update that changes the projection's version in order: once the new release's `previously project` has run, the old pods drop out and the new ones come in.
The probe reads the state row and doesn't catch up, so it stays one read however far the projection lags; the next call catches up.
A switchover of the database's primary costs requests while it lasts: for the seconds in which no primary answers, the probe gets 503, and so would a tool call, because the database doesn't answer.
After it, requests succeed again.
A connection that died while it sat idle, whether in a switchover or a restart of the database, costs no request on top of that: the storage checks a pooled connection when it takes it from the pool, and replaces a dead one before the request uses it.
A failed check writes one line to the server's log, with the sentence of the storage error and no traceback, since a database that doesn't answer is an expected state.
Any other failure of the probe keeps its traceback.
A probe that carried a token would need a client of its own, and a client can call every tool and read whatever its processor may see, so a deployment would keep a reading credential just to learn whether the server is up.
The reason for the token, knowing who asked, doesn't reach a route that asks nothing of the log.
The path is matched exactly and only for `GET`, so it opens no door to anything else.

Over standard input and output there is no token: whoever starts the process is the client, named in `PREVIOUSLY_MCP_CLIENT`.
That fits a client that starts the server itself on a machine that reaches the database.

(mcp-open-limits)=

## What the pilot leaves open

These limits are known, named, and left for later; the map of open points holds each one.

- **A unit larger than a page** is cut, and the rest of that unit isn't served in the pilot.
  Pointing the model at the same unit again would serve the same cut and invite a loop, so the note says so plainly instead.
- **The limit of a page**, 60,000 characters, is an estimate: about 15,000 to 20,000 tokens, under the cap of 25,000 tokens that Claude Code puts on one result.
  It hasn't been measured against real mail yet; the run of the maintainer after the merge is where it gets measured.
- **The chronicle reads the log**, in batches of 200 rows and with no bound per call, because the derived chronicle doesn't know who took part in an event.
  A circle that matches few events reads the whole log for one page, and a derived view of its own waits until reading the log gets too slow.
  The yardstick is 60 seconds, the time Vibe waits for a call by default: every call should stay well under it, and a sparse circle on a long log is what reaches it first.
- **The order of the placeholders** narrows the time of a withheld event: it happened between the visible events around it.
  The cursor carries the id of the last item and no time, because the time of a withheld event is content like its subject, but the order of the page can't be hidden.
- **A record can name an answer that never arrived.**
  The entry is written before the answer leaves, so the log never misses an answer that a client got.
  The reverse can happen on either transport: an answer lost after its entry committed, because standard input closed, an HTTP connection dropped or the process stopped, stands in the log as delivered.
  The gate has the opposite limit, because it calls the provider first and writes afterward; this server reads, writes, and then answers.
- **The hook** that records the calls the SDK refuses uses an interface that the SDK calls provisional, so a minor release of the SDK may change it.
- **The volume of the access log** is one event per call, an estimated few thousand a month.
  Where it would have to be summarized is open.
- **Every call reads the policy**, twice over HTTP, once for the token and once for the call.
  Until 2026-10-11 that read went through every action and passed over the access entries one by one, so each call made the next one slower.
  Measured that day with 6,000 access entries, one read of the policy took 0.341 seconds.
  It now asks the database for the policy's own actions, and the same read took 0.010 seconds.
  The database still visits every action, so the time still grows with the log, at a far lower rate; a derived view of the policy is the step that's left.
  `previously access` and `policy gaps` still read every action.
