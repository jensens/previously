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

Two more places exist in the design and not yet in the code.
The MCP server of the pilot's fourth unit will show content to Claude Code, which sends it on to Anthropic.
It will reuse the decision of the gate, because a decision that lives in `core` can be asked by anything that has to decide what a model may see.
The first action that writes into a foreign system, such as an issue tracker of a customer, is a separate question: may this content appear where everybody there sees it?
That check is a different one, at a different place, and it arrives with the first action that needs it ({ref}`processing-policy` says why the two are kept apart).

## The mail comes in and stays in

The IMAP connector is the only door through which a customer's content enters, and it opens inward only.
It never changes the folder, it never marks a mail as read, and a password that opens the one mailbox opens nothing else.
So the connector is a boundary in one direction: nothing a run does can reach back into the mailbox.
That's also why an erasure in the log doesn't erase the mail in the mailbox, which {ref}`erasure` states as a limit of the erasure, not of the connector.

## The blobs go out sealed

A blob is sealed in the `age` format before it leaves the process, so the bucket's operator holds ciphertext.
What that operator does see is the name of each object, and the name is the SHA-256 of the plaintext without a salt ({ref}`blobs` gives the reason).
Whoever holds a candidate file can hash it and learn whether the bucket holds it.
The seal protects the content, and the address leaks equality.

## The backups carry everything

A backup of the database holds every unit in plain text, because the database does.
Its protection is the client-side encryption of {ref}`backup-encryption`, and nothing in this repository runs a backup: that's the work of the environment that hosts Previously.
An erasure doesn't reach a backup taken before it, and a restore to an earlier point brings the erased content back ({ref}`erasure`).

## The anchor carries a hash

An anchor line is an `id` and a hash.
The hash covers the units through their salted digests, so a short erased text can't be recovered from it.
The anchor is the one boundary on this list that was built to be crossed: it has to leave the database's reach to mean anything.

## The gate and its three providers

The gate is the newest place and the one with the most to say, because three providers sit behind it and each promises something different.

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

## What nobody guards yet

These are the gaps as of 2026-10-09.
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

**MCP and writing outward.**
Both are ahead.
When they arrive they cross the boundaries above in new places, and this page gets a row for each.
