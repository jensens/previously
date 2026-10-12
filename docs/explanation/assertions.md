(assertions)=

# About assertions

An observation records what arrived: a mail, its paragraphs, who sent it.
An assertion records what somebody concludes from observations: who owes whom what and by when, or what was decided, by whom and on which day.
Previously writes both into the same chain, as events of different kinds, and an assertion always names the observations it rests on and who stands for it.

This page explains why an assertion has the shape it has: complete versions, an author apart from the responsibility, proposals that a client can make and only a person can answer, an erasure that takes an assertion along with its source, and a policy that looks at the sources and not at the people an assertion names.
{ref}`assertions-reference` lists the payload field by field, {ref}`cli-reference` the commands, {ref}`mcp-tools` the tools of the MCP server, and {ref}`record-what-is-owed-and-decided` shows the routine.

(assertions-complete-versions)=

## Every version says everything

An obligation changes over its life.
Its date moves, its wording gets sharper, and one day it's fulfilled.
The log is append-only, so every change is a new event, and the question is what that event holds.

It could hold the change alone, such as a due date that moves to December 15.
Previously writes the whole statement instead: every version of an obligation or a decision says everything that holds after it.

The reason is precedence, which the next section explains.
Versions come from different levels of responsibility, a statement of the operator's and a proposal of a model's.
If a version held one field, the state of an obligation would be put together from fields of different levels: the date from a proposal nobody approved, the wording from the operator.
That's a statement nobody made, and the operator's word would lose against a proposal through the back door.
With complete versions, what holds is always one version that one party stated whole, and it's either direct or open.

What changed between two versions isn't stored.
It follows from comparing a version with the one before it, and the history that `previously obligation --history` and `list_obligations` print computes it when it's read.
Stored, it would be a second truth that could contradict the first.
The one thing that can't be derived is why a version was written, and that's what its `reason` is for.

An obligation or a decision is named after the event of its first version, `previously://event/<id>`, and every later version carries that name in `subject`.
The name stays when the first version is erased, as long as another version stands.
A later version is a whole statement with its own sources, so it doesn't need the first one to say what it says, and every version and every approval that names the entry keeps finding it.

The command line fills what `assert --subject` leaves out from the version that stands, before it asks, so that a change of one field takes one option.
What it writes is complete all the same.
`write_assertion` takes nothing over: an item with a `subject` says everything a client means to hold.

(assertions-responsibility)=

## Who wrote it, and who stands for it

Every version carries two answers that look alike and aren't.
`author` says who formulated it: `human:operator` or `model:` and the name of a client.
`responsibility` says who stands for it: `direct` for the operator, `open` for nobody yet.

The two come apart in the most ordinary case.
A model reads a customer's mails and formulates an obligation; the operator reads it and makes it his own.
The version that results was formulated by the model and is the operator's responsibility.
Merging the two fields would either credit the operator with words a model wrote, or keep a statement he approved among the proposals.

Precedence follows the responsibility, and not the author or the time.
The latest direct version holds.
Without one, the latest open version that's neither approved nor rejected holds, and every list shows it as a proposal.
Within one level the newest wins, but a proposal never outranks a direct version, however much newer it is.
If it could, a model that writes later would overwrite the operator, and the operator would have to keep correcting what a model keeps proposing.

Open versions that are newer than the direct one, and neither approved nor rejected, are pending proposals.
A list counts them and the page of an entry shows them, and none of them holds.
The proposal that holds because no direct version exists is never counted as pending as well, or a list would count it twice.

The system doesn't know people yet, so every statement the operator makes is `human:operator` until the identity graph exists.

That a proposal never outranks the operator doesn't rest on the MCP tool writing `open`.
A version whose author is a model is direct only as an approval, and that's a rule of the form: the write path refuses any other, and `verify` reports one that stands in the log all the same.
Without the rule, a row written around the tool would win over the operator without a trace.
A rejection is exempt, because it's no version: `write_reject` writes it direct, with the client as its author.

(assertions-proposals)=

## A client proposes, and only a person answers

What `write_assertion` writes is always a proposal.
The server can't know whether a person read the item it's about to write.
It asks for a second call before it writes, but the second call is a tool call of the model just as the first one was, and a model can make both.
So a client's statement goes in as `open`, and it stays a proposal until a person answers it.
Several proposals go in one call, so that a person looks at one preview and confirms it once.

An approval or a rejection is different: it's the answer, and it's direct.
Over the command line the operator types it himself.
Over MCP, `write_approve` and `write_reject` count as the operator's only because the client asks the person before it confirms them.
That's a requirement on the environment and not something Previously can check, in the sense that {ref}`environment-requirements` gives the word: Previously says what it requires, and the configuration of the client meets it.

Not meeting it carries a concrete risk.
A client that runs `write_approve` without asking, because it was allowed always or because a mode lets a classifier or nobody decide, writes direct versions that no person looked at.
They outrank every proposal, they stand in the log for good, and nothing in them says that nobody read them.
Whoever allows that does so consciously and carries it.
All three writing tools start with `write_`, so that one rule per client can make it ask before any of them; {ref}`record-what-is-owed-and-decided` shows the rules for Claude Code and for Vibe.

The key that seals a handle is a secret of the MCP server alone.
No other process writes through a handle, so a copy anywhere else, in the tools pod or beside the ingest, would be a key that nothing uses and that can still leak.
Rotating it makes the handles not yet confirmed fail, and nothing else.

Which client carried an approval stands in the access log, not in the assertion.
The `mcp_access` of the confirming call names the client and the ids it wrote, so the question "who approved this, and through what" has an answer.
The assertion itself says what holds and who formulated it, and the way the operator's word reached the log is a fact of the call and not of the statement.

A client proposes only on sources it may see.
A source the policy keeps from the client is refused with the same sentence as an event that doesn't exist, and so is an entry or a proposal it may not see, because a different sentence would tell the client that the event exists.

And a preview shows everything that gets written.
A list cuts a line at 1,000 characters, so a writing tool refuses a statement with a longer line instead of previewing it cut: a person who confirms a preview has seen all of it.

(assertions-approval)=

## Approving makes a proposal one's own

An approval is a new direct version of the same entry, with the content, the sources and the author of the proposal, and `approves` naming it.
Nothing has to be merged to read it: it's a complete version like every other, and it wins by being direct.
Its reason can be the operator's own, since why it's taken can differ from why it was proposed.

A proposal is answered once.
Approving one that's approved or rejected already is refused, because two answers to one proposal would stand side by side, and the second would win without a word.

An approval stands when its proposal is erased on its own, by an erasure of the proposal and not of a source.
It was checked against the proposal when it was written, it carries the same sources, and it's a whole statement that doesn't need the proposal to say what it says.
An approval whose proposal went through a source goes with it, since it rests on the same sources.

(assertions-rejection)=

## A rejection is a statement too

A rejection is an assertion of its own kind, `rejection`: direct, with the proposal in `of`, an optional reason, and the sources of the proposal as its own sources.
A rejected proposal leaves the open points and stays in the history of its entry.

It's written as a statement rather than as a flag on the proposal, because the log can't change the proposal, and because the rejection is worth reading later.
A layer that proposes on its own, which is the next unit of the pilot, would otherwise propose the same thing again after every rejection.

It takes the sources of its proposal so that it goes with the proposal when one of them is erased.
Its reason can quote what it rejects, and a rejection that outlived the erasure of its proposal's mail would keep that.

(assertions-erasure)=

## An erasure takes the assertion along

An assertion says in its own words what its sources said.
If it outlived the erasure of a source, the promise that an erasure takes content out of the log would fail without anybody noticing, through a sentence somebody wrote about the erased mail.
So an erasure takes along every assertion that rests on what it erases, in the same transaction, by a redaction of the whole assertion; {ref}`erasure` places this cascade beside the one for the answers of model calls.

An assertion rests on an event it names as a source, on a unit it cites, and, for an event it cites whole, on every unit of that event erased after the assertion was written.
A unit erased before was gone when the assertion was formulated, so the assertion can't repeat it, and an erasure of it doesn't take the assertion.

An assertion on three mails goes whole when one of them is erased.
That's more than necessary, and it's the safe direction: telling which sentence of an assertion came from which mail is interpretation, and an erasure can't rest on interpretation.
Whoever wants to keep the obligation writes it again, on the sources that are left.
Proposals, approvals and rejections go alike.

When the version that holds is erased, the entry falls back to the next direct version that stands.
Without one, a proposal that stands appears again, as a proposal and never as direct.
Without any standing version the entry is gone: every list leaves it out, and asking for it answers as for an id that names nothing.

The write path and an erasure can meet.
The write path locks every source, in ascending order, with the row lock an erasure takes, and reads them again under it, so a source erased a moment before is refused, and an erasure that comes a moment later waits and then finds the assertion; {ref}`concurrency` describes that lock.

Two erasures take no assertion along.
An erasure of a blob erases no payload and no unit, and an assertion names no blob, only events and their units.
A model call is never a source, because the sources of an assertion have to be observations.
That rule keeps the cascade one step deep: a source that was an action or another assertion would make one cascade follow another, and an assertion is meant to say what was observed, in its own words.

The access entry of a writing call holds no text for the same reason.
It records how many statements a call named, the ids of the sources and the proposals, whether it confirmed, and the ids it wrote, and never the wording.
A text a client derived from a mail would otherwise stand in the access log and outlive the erasure of the mail.

(assertions-mentioned)=

## Mentioned isn't involved

Two questions sound alike here and get different answers: who may see an assertion, and where it shows up.

The policy decides who may see it over its sources alone.
An assertion carries the content of its sources in other words, so it's content of the circles its sources belong to.
The policy decides over the people in the source events of every standing version together, once for each distinct source, and the first decision that allows nothing holds, so the strictest rule among all of them wins; {ref}`processing-policy` explains the decision itself.

The people an assertion names, its debtor, its creditor and its deciders, take no part in that.
A provider that a mail mentions in passing isn't a party to the mail, and naming it in an obligation doesn't make the obligation its content.
If it did, naming a circle with a generous rule would hand out content of a circle with a strict one, and naming a circle without a rule would withhold an obligation from a client that may read every one of its sources.
A reference to an actor grants nothing and takes nothing away.

Where an assertion shows up is a matter of sorting, and there the people it names count.
A list filtered by a circle finds an entry whose sources touch the circle, and also one whose debtor or creditor is that circle or an address that belongs to it.
The filter only sorts: what the policy keeps from a client stays a placeholder in any list.

A withheld entry is found by the circles of its sources alone, never by the people it names.
Otherwise the filter would tell, of an entry the client may not read, which circle one of its parties belongs to, and the parties are content.
What it still tells is the same as the chronicle's filter tells of a withheld event: a placeholder found under a circle says that somebody in its sources belongs to that circle, also where the circle has a rule and the placeholder's reason names only circles without one.

The command line shows everything, without asking the policy, as `chronicle` does: whoever has the command line is the operator.
The chronicle itself stays with observations, and assertions appear in lists of their own.

(assertions-names)=

## A name is a label, not an identity

A reference to an actor has one of four forms: `own`, `circle:` and a circle's name, `address:` and a mail address, or `name:` and a text.
The list is fixed, because a reference stands in a hashed payload, and its grammar has to hold for every payload written under it.
A new form later, such as one for a person, is a change to the code and not to the data.
The form is checked and not the existence: a `circle:` doesn't have to stand in the policy today, because an assertion describes the world and not the state of the policy.

`address:` and `circle:` are the references that hold: an address names one mailbox, a circle one entry of the policy.
`name:` is the way out for everything else, such as a hosting company whose address nobody has, and it's fuzzy in a way that matters, since many people share a name.

So a `name:` is a label and never an identity.
Two `name:` references never count as the same actor, even with the same text, and a list filtered by a name searches the text without treating the matches as one party.
A name is made precise in the one obligation where it stands: when the address becomes known, that obligation gets a new version with `address:` in place of `name:`, and its reason says why.
A global mapping from a name to an address would change every obligation with that name, the ones that meant somebody else among them.

When a source of a statement shows an address whose display name contains the text of a `name:`, the command line says so before it asks, and goes on: it suggests the reference that holds and forbids nothing.

None of this blocks the identity graph.
People and organizations will be derived from assertions, as everything else is, and a statement such as "this address belongs to this person" will let a derived view resolve an `address:`.
A `name:` it can't resolve is the case where the system will ask back which person is meant, offering the people that have a link to the circles of the sources, and the answer will be a new direct version with the right reference.

(assertions-folded)=

## Folded from the log, not kept in a table

The specification of this unit planned two derived tables, one for obligations and one for decisions, built from the log like the chronicle.
The build has none: every read folds all assertions from the log, which a single query reads by their kind, and no migration came with the unit.
The maintainer confirmed that on 2026-10-12, with the proviso that a table can still follow when it's needed.

Three things decided it.
The fallback after an erasure needs every version of an entry, so a table that held the winner would have to read them all again whenever one is erased.
Whether a client may see an entry depends on the policy in force at the moment of reading, and a policy can change between two reads, so that part can't be stored.
And the MCP server reads the log through the store protocol alone and never through `storage`, where the readers of the derived tables live ({ref}`module-boundaries`).
What holds is computed and not kept, so nothing beside the log can disagree with it.

The cost is that every list, every page of an entry and every write reads every assertion in the log.
The write path reads them as well, inside its transaction, to check what a statement names and whether its handle was confirmed before.
How long that takes at 5,000 assertions, for `previously obligations` and for `list_obligations`, hasn't been measured yet: the final review of the build measures it, and this section carries the figure with its date once it's taken.
A derived table comes only when a measurement asks for one.

(assertions-limits)=

## What the pilot leaves open

These limits are known and named; the map of open points holds the ones that call for work.

- **A confirmation repeated after an erasure writes again.**
  A second confirmation of the same handle finds the assertions that carry its identifier and writes nothing, but the identifier lives in the payload, and an erasure takes the payload.
  When the assertions of a handle were erased in the meantime, confirming it again writes them anew.
  The operator erased them, a handle holds for ten minutes, and the client holds the text anyway; a key kept beside the payload would survive the erasure, and would be a second truth.
- **`verify` can't tell every erased version apart.**
  An erased assertion keeps no payload, so `verify` can't say whether it was the first version of an entry or a later one, and a version whose `subject` names an erased later version passes, unless an approval once named the erased one under another subject.
  The write path refuses such a version; only a row written around it can carry one.
- **A history longer than a page** is cut over MCP after a whole line, and no call serves the rest; `previously obligation ID --history` prints all of it.
- **A line longer than 1,000 characters** can't be written or answered over MCP, because the preview would cut it.
  The command line has no such limit, since it shows the whole payload.
- **The approving client** is in the access log and not in the assertion.
- **The hint about an address** comes from the command line only; a preview over MCP doesn't suggest `address:`.
- **A list doesn't say when an entry last changed.**
  It counts the versions and the pending proposals, and the history shows the time of each version.
