(connectors)=

# About connectors

A connector is how something that happened elsewhere comes into the log: a mail in a folder today, a file in a shared folder or an issue in a tracker later.
The first one reads an IMAP folder, and it's the occasion for most of what this page explains, but the decisions are about every source that follows.
This page explains what a connector does and what it leaves to `core`, why `source` names the channel, why an artifact has an identity of its own and why neither the units nor the payload could carry it, what a variant is, why the raw mail and its attachments are blobs, and why the folder a mail lay in isn't a property of the mail.
{ref}`mail-mapping` lists how a mail maps, field by field, and {ref}`cli-reference` the command that runs it.

## A connector takes in, and doesn't interpret

A connector hands over bytes and a position, and nothing else.
It doesn't turn a mail into an event: `core.mail` does, and the IMAP connector never sees the result.
The split looks like a detour until you ask where else the same bytes arrive.
A mail saved as an `.eml` file in a shared folder is the same bytes that IMAP delivers, and when a connector for that folder exists, it has to map that mail to the same event, or the same mail would be two artifacts depending on the door it came through.
So the mapping lives in one place, beside the rules of the log, and every connector that carries mail hands its bytes to it.

The other half of the split is that a connector knows its source and nothing about the log.
`connectors` is a layer of its own, between `cli` and `core`, and `.importlinter` keeps `imaplib` in `connectors.imap` by name, as {ref}`module-boundaries` explains.
A second place that spoke IMAP would be a second place where a folder could be changed or a password could end up in a message.

Taking in without interpreting goes further than the module boundary.
Quotes and signatures stay in the text, because telling a quote from new text is a judgment, and a wrong judgment would drop words without a trace.
An address stays as the mail wrote it, not converted to lowercase and not merged with another spelling of the same person, because deciding that two addresses are one person is an assertion, and assertions don't come from a connector.
Nothing is decrypted.
What a connector writes is what the source said, and everything that reads meaning into it comes later, with its own name on it.

## The watermark follows the append

A connector reads from where it stopped, and the position it stopped at is the watermark: for IMAP, the folder's `UIDVALIDITY` and the UID of the last mail taken in.
The run writes the watermark after each batch it appended, and never before.
The order is the one in which a failure costs a repetition rather than a loss.
A run that stops anywhere in between leaves the watermark where the last batch left it, and the next run fetches the same mails again, finds their blobs in the store and their events in the log, and writes nothing twice.
The other order would lose mail: a watermark moved past a batch that then failed to append would skip that batch for good.

That's also why a renamed folder, a server that changes the `UIDVALIDITY`, or another host name are harmless.
Each makes the run read the folder from the start, and every mail found there counts as known.
Re-reading is cheap because recognizing a mail is, and recognizing one is what the artifact's identity is for.

The connector reads without changing anything: it opens the folder read-only and fetches each mail with `BODY.PEEK[]`, which leaves the mail unread.
Either one alone would leave the flags alone, and both are there because the folder belongs to somebody's mailbox, and a tool that marks mail as read is a tool that changes what a person sees.
A mail that leaves the folder later stays in the log.
The folder is the door the mail came in through, not a mirror the log keeps in step with.

## `source` names the channel

Every mail has `source = "email"`, whatever the mailbox, the folder or the connector that read it.
The source key `(source, external_id)` is what makes a second sighting the same event, so `source` has to name what the identifier belongs to.
A Message-ID belongs to the channel: the same mail in two mailboxes carries the same one, and so does the same mail as an `.eml` file.
Had `source` named the connector, `imap:pilot@…/Kunde Müller` and `imap:office@…/INBOX` would be two sources, and one mail lying in both would be two events.

Where a sighting came from still matters, and it isn't lost: it stands in the payload, under `found_in`, with the name of the connector's watermark and the UID.

## Two sightings of one artifact

A connector reads the same thing more than once, by design: a folder re-read from the start, two copies of a mail in one folder, a mail in two mailboxes.
Each sighting arrives under the same source key, and `append` used to answer every one of them with the event it already had, whatever the sighting held.
That was fine for a mail, which doesn't change, and wrong for anything that does: an issue whose number is its key would keep its first state and lose every edit after it without a word.

So an event can carry the identity of its artifact, `artifact_hash`, a SHA-256 over what has to be equal for two sightings to be the same thing.
`append` compares it under a key it knows already.
The same hash is a sighting, and nothing gets written.
Another hash is refused with `ArtifactChanged`, and the caller decides what that means, because only the caller knows whether its artifacts are supposed to change.

### Why neither the units nor the payload could carry it

The obvious candidates were already in the event, and each fails for a reason worth keeping.

The units are a derivation.
They come out of a converter from HTML into text, a guess at a character set, a rule for splitting paragraphs, and each of those can get better.
An identity over the units would turn every improvement into a changed artifact, and every re-read folder into a wall of refusals.

The payload carries the transport.
The same mail fetched from two mailboxes has other `Received` headers, and the same mail saved on a Unix machine has other line endings; by the rule that made a source key, both are one mail.
An identity over the payload would make them two.

So whoever maps a source decides what counts, and writes it on the reference page of that mapping; for mail, that's `core.mail` and {ref}`mail-mapping`.
For a mail it's the decoded subject, the bytes of each body part after the transfer encoding and before any conversion into text, and the bytes of every attachment, with line endings made equal where the bytes traveled as lines.
That rule belongs to the project and not to a library.
If a new version of a library decoded a part differently, the identity of every mail would change with it, and every sighting would become a variant; so `core.mail` takes the mail apart itself, with the standard library's `email` package, and the tests hold the rule.

The hash carries no salt, and it can't.
Two sightings of the same mail have to give the same value, and a salt drawn per event would make them differ.
That has a price, which {ref}`erasure` names: for a short text, the hash confirms a guess.

### The variant

A mail isn't supposed to change, and when a known Message-ID arrives with another content, the mail is still something that happened.
A mailing list rewrites the body and keeps the identifier, a client sends it again with another attachment, somebody forges a Message-ID.
Refusing would lose the second mail, and overwriting is what an append-only log can't do, so the run takes it in under a key of its own: the Message-ID, `#`, and the first sixteen hexadecimal characters of its artifact hash.
Its payload names the Message-ID it deviates from, under `variant_of`, and the run names it on standard error, so that nobody has to find it by accident.

The variant key takes 64 bits of the hash, which keeps the variants of one Message-ID apart, and is short enough to read.
Two variants whose hashes share those 64 bits don't happen by accident, but they can be made: finding such a pair takes about four billion attempts, which is little for a computer.
The run then stops rather than guess which of the two the key means, and it stops at that mail on every run until the mail leaves the folder.
That's acceptable for a folder that a person fills by hand, and it's the first thing to revisit for a source that anybody can write to.

## The raw mail is a blob

A mapping is a reading of the mail, and a reading can be wrong or get better.
The mail itself is the evidence, so every mail goes into the store as it arrived, byte for byte, beside its event, and so does every attachment.
The architecture once foresaw a field of its own for those bytes; a place for bytes exists since stage 1c, and the raw mail is a blob like any other, sealed and addressed by its content, as {ref}`blobs` explains.

Addressing by content does two things here at once.
An attachment that arrives on five mails is one object.
And a mail that can't be mapped at all, because the parser raises on it, still has its raw bytes in the store, with an event that says so; a better parser can read it later, and the event can be erased and the mail taken in again.
A mail that can't be mapped never stops a run, because a run that stopped at one mail would stop there at every run after it, and take in nothing more.

The run looks every event up before it stores anything.
A second copy of a mail is other raw bytes, other `Received` headers, and storing them would put a second object into the bucket for an event that already exists.
A mail whose event has been erased would put its bytes back into the store the erasure deleted them from.
Neither happens, because the lookup comes first.

## A mail inside a mail is a mail

When a customer forwards a mail as an attachment, the interesting part is the mail inside, and the outer one often says no more than "see below."
Kept only as a blob, the mail inside would lie unreadable beside an empty line of the chronicle.
So it becomes an event of its own, mapped like any mail, with its own date, so that the chronicle shows it where it belongs, and with `forwarded_in` pointing back at the outer one.
The outer mail stays an event as well, because that somebody forwarded something, when, and with which sentence, is something that happened too.

Forwarding a mail as quoted text, under a line such as `---------- Forwarded message ----------`, is a different thing for the log.
Taking that text apart would mean reading meaning into it, and so it stays the text of the outer mail.

## The folder isn't a property of the mail

The maintainer copies a mail into a folder because it belongs to a customer, and that's tempting to write down as a fact about the mail.
It's a fact about a decision of the maintainer instead: the same mail could belong to two customers, could be moved, or could have been filed by mistake.
So the folder appears in the payload as where this sighting lay, under `found_in`, and nowhere else.
A second sighting in another folder writes nothing, so only the first place stands in the log.
Which project or customer a mail belongs to is an assignment, an assertion with somebody responsible for it, and it waits for the unit of work that brings assertions.
