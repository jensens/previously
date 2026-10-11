(trust-boundaries)=

# About trust boundaries

Content leaves Previously at a handful of places, and at each of them somebody or something decides what may cross.
This page lists the places, says who guards each one, and then names what nobody guards yet.
It's the one page that looks at the whole system from the outside, so it repeats no mechanism: each one has a page of its own, and the sections below point to it.

The list matters because the project holds the mail of a customer.
A boundary that lives only in the head of whoever built it gets crossed by the next person who adds a feature.

## Where content crosses

Every row names a place, what crosses there, who guards it, and the page that explains the guard.

| Place | What crosses | Who guards it |
|---|---|---|
| IMAP folder | Mail comes in; nothing goes out. | The connector opens the folder read-only, over TLS only, and fetches with `BODY.PEEK[]`, which leaves a mail unread ({ref}`connectors`). |
| Blob store (S3) | Attachments and raw mails go out, sealed. | The `age` seal, applied before the bytes leave the process ({ref}`blobs`). |
| Backups | The whole database goes out, content included. | Encryption on the client, with a key outside the data path ({ref}`backup-encryption`). |
| External anchor | One line, the `id` and the hash of the tip, goes out. | The line holds no content, and it's kept where the database's writer can't write ({ref}`external-anchor`). |
| The gate | The units of an event go to a model provider. | The processing policy, and a `model_call` in the chain for every attempt ({ref}`processing-policy`). |
| The MCP server | The units of an event go to a client such as Claude Code, and through it to whoever runs the client's model. | The processing policy, decided for every event with the client's chain, a bearer token per client, and an `mcp_access` in the chain for every call ({ref}`mcp-interface`). |

One more place exists in the design and not yet in the code.
The first action that writes into a foreign system, such as an issue tracker of a customer, is a separate question: may this content appear where everybody there sees it?
That check is a different one, at a different place, and it arrives with the first action that needs it ({ref}`processing-policy` says why the two are kept apart).

## The mail comes in and stays in

The IMAP connector is the door through which a customer's mail enters, beside what the operator types or attaches with `append`, and it opens inward only.
It never changes the folder, it never marks a mail as read, and a password that opens the one mailbox opens nothing else.
So the connector is a boundary in one direction: nothing a run does can reach back into the mailbox.
That's also why an erasure in the log doesn't erase the mail in the mailbox.
The mailbox belongs to the source, not to Previously, and no promise of erasure covers it, which {ref}`erasure` states as a limit of the erasure, not of the connector.

## The blobs go out sealed

A blob is sealed in the `age` format before it leaves the process, so the bucket's operator holds ciphertext.
What that operator does see is the name of each object, and the name is the SHA-256 of the plaintext without a salt ({ref}`blobs` gives the reason).
Whoever holds a candidate file can hash it and learn whether the bucket holds it.
The seal protects the content, and the address leaks equality.
It also protects reading only, not deleting: who may delete or overwrite the objects, and what else the credentials Previously holds may reach, are requirements on the environment that {ref}`blob-bucket-requirements` states with their reasons.

## The backups carry everything

A backup of the database holds every unit in plain text, because the database does.
Its protection is the client-side encryption of {ref}`backup-encryption`, and nothing in this repository runs a backup: that's the work of the environment that hosts Previously.
Encryption keeps a backup from being read, not from being deleted, so no credential of a process that handles foreign content may reach the backups; {ref}`backup-deletion` gives the reason.
An erasure doesn't reach a backup taken before it, and a restore to an earlier point brings the erased content back ({ref}`erasure`).

## The anchor carries a hash

An anchor line is an `id` and a hash.
The hash covers the units through their salted digests, so a short erased text can't be recovered from it.
The anchor is the one boundary on this list that was built to be crossed: it has to leave the database's reach to mean anything.

## The gate and its three providers

The gate is the place with the most to say, because three providers sit behind it and each promises something different.

| Provider | Where it processes and stores | How long it keeps the request |
|---|---|---|
| Anthropic | Processing in the region the call requests, `global` or `us`; storage in the United States. | 30 days. |
| Mistral | In the EU, for processing and storage. | Not known; training on the content is switched off. |
| A local model | On hardware the operator runs, next to the database. | Not at all. |

These are what the pilot declares as of 2026-10-09, and they're declarations: the operator writes them down as policy events, and the gate holds them against the rules.
{ref}`processing-policy` explains why a promise and a report are different things, and why the gate treats them differently.

Three properties of this boundary are worth stating on their own.

The first is that the gate is the only caller.
Only `gate` imports the libraries of the vendors, and `lint-imports` fails the build when another module does ({ref}`module-boundaries`).
A model call that doesn't pass the gate has to get past a gate of the build first.

The second is that the log holds a record of every attempt.
A call that was denied, refused by the model, answered against the schema or lost to a network error is a `model_call` all the same, and the payload of one holds no content: ids, hashes, numbers and names.
The record can be read by whoever reads the log, and a provider that echoes the prompt in an error message can't put the customer's words into the chain, because the payload never takes the provider's wording.

The third is that no key appears anywhere.
The two API keys are read from the environment, they're never written to an event, and a message that quotes a provider's error has the key removed from it.

### The environment is the operator's

The Anthropic SDK reads `ANTHROPIC_BASE_URL` on its own.
An environment that sets it sends the call, content included, to whatever address it names, and `previously` doesn't inspect it.
That's a place where content can go elsewhere without a rule or an event saying so.
It's accepted, for the reason the keys are accepted: whoever controls the environment of the process already holds the keys, the database address and the blob identity, and a variable adds no reach beyond those.
But it belongs on this list, because a deployment that copies an environment from somewhere else copies this variable with it.

## Clients that read the log

The MCP server is the second place where content leaves for a model, and it reuses the decision of the gate rather than having one of its own.
A client is declared as a processor, because whatever Claude Code reads goes to Anthropic and whatever Vibe reads goes to Mistral, so the same policy decides about each event a call would show, with the client's chain as the only candidate.
An event that doesn't pass comes back as a placeholder without its subject and its participants.

Four properties of this boundary are worth stating on their own.

The first is that every tool only reads.
Nothing a client does through the server changes the log, beyond the record of the call itself.

The second is that a client is known by its token and not by the network.
Over HTTP every request needs the bearer token of a client in force, looked up at every request, and only the SHA-256 of a token is ever stored.
Over standard input and output, whoever starts the process is the client it names.

The third is that the log holds a record of every call that has a client, a refused one included, and the record holds no content.
`previously access` answers what a client saw and what it didn't get.

The fourth is the one that isn't a boundary: the fence around the text of a mail.
It marks foreign text for the model, and a model can still follow what the text says; {ref}`mcp-interface` explains why the pilot relies on read-only tools and the policy instead.

What every client sees regardless of the policy is what the operator stated and what isn't content of a customer: the names of the circles, their rules, the number of members, and the promises of the providers.
No address of a member is among it.

(network-ways-out)=

## Only the governed ways lead out

Two of the places above hand readable content of the log to somebody outside: the gate, to a model provider, and the MCP server, to a client and the provider behind it.
Both decide with the policy, and both write a record of every attempt.
That's what makes them boundaries: a call nobody allowed doesn't happen, and a call that happened can be found.

Every other process of Previously reaches no more than its commands need.
`ingest imap` reaches the mail server and the bucket, and the blob commands reach the bucket, which only ever receives sealed content.
`gate try` reaches the providers its adapters call, and the local model server.
`previously serve` answers requests and sends none of its own.
All of them reach the database, and every other command reaches the database alone.

That holds for the code as it's written, and the code isn't all that runs.
The ingest parses mail anybody could have sent, through a mail parser and an HTML converter it didn't write; the gate and the server run the clients of their vendors; and any of them could be taken over by a flaw in that code, or by a dependency that changes.
A process that holds the database connection and can reach any host is then a way out that no rule decides and no record shows: what it sends leaves no `model_call` and no `mcp_access` behind.

So the network has to say what the code says, and that's a requirement on the environment ({ref}`environment-requirements`): each process of Previously reaches name resolution, the database and the hosts its commands need, and nothing else.
The environment chooses how.
In a Kubernetes cluster, network policies that deny every connection to and from a pod of Previously, except DNS, the database and the hosts that pod's commands name, are one way; on a single host, a firewall for the user the commands run as is another.

The network can't do it alone.
The gate's adapters call whatever address the environment of the process names for them, as `ANTHROPIC_BASE_URL` shows above, and a rule that lets a process reach a host is a rule about the host, not about what the process sends there.

## What nobody guards yet

These are the gaps as of 2026-10-11.
Each is known, each has a place in the map of open points, and none is hidden by a mechanism that looks like a guard.

**The provider's own retention.**
Anthropic keeps requests and responses for 30 days.
The retention at Mistral isn't known.
No erasure in Previously reaches either copy, neither the cascade of a `model_call` nor `redact` itself.
What went out before an erasure is out.
The policy can only decide what goes out in the first place, and a rule with `max_retention_days` is how an operator limits that.
Zero retention is something the operator has to arrange with each provider, and then declare.

**An unknown participant binds no rule.**
A rule for a circle applies to content in which a member of the circle takes part.
An address that belongs to no circle contributes nothing.
When a rule for the source applies, such as one for `source:email`, the content goes out under that rule, however many unknown people took part.
When none applies, the built-in `local_only` takes over and the fallback shows.
So a customer that nobody put into a circle is protected exactly as far as the rule of the source reaches.
The processing policy page argues why the pilot leaves it at that.

**A call can go unrecorded.**
The `model_call` is written after the call.
A process that dies between the provider's answer and the write leaves a paid call that no event records.
Writing an event before each call would close the gap and cost a second event for every call, and the pilot takes the gap.

**An error of the log after a paid call.**
The write can fail after the call succeeded, for example when a provider's request id holds a character the log refuses.
The call happened and the chain doesn't know.

**What a client read stays with its provider.**
The retention of the gate's providers applies to the provider behind a client too: what Claude Code read is at Anthropic under the terms of the account, and no erasure in Previously reaches it.

**Names outside the fence.**
The heading of an event carries the display names of its sender and recipients, which a mail supplies, outside the fence: up to about 2,200 characters per event, cleaned and kept to one line.

**A record can name an answer that never arrived.**
The `mcp_access` is written after the call has read and before the answer leaves, so the log never misses an answer that a client got, and a write that fails sends the client an error instead of content.
The reverse can happen on either transport: an answer lost after its entry committed, because standard input closed, an HTTP connection dropped or the process stopped, stands in the log as delivered.

**Writing outward.**
It's ahead.
When it arrives it crosses the boundaries above in a new place, and this page gets a row for it.
