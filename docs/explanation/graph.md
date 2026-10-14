(graph)=

# About entities, relations and the vocabulary

Previously keeps more than the mails that arrive.
It also keeps what the operator knows about the people and things the mails talk about: an association, its chair, the years someone held that post, the project a mail belongs to.
An **entity** is such a thing, and a **relation** connects two of them, or later an event and a thing.
Both are assertions, written into the same chain as obligations and decisions, with the events they rest on and an answer to who stands for them.

This page explains why the model has the shape it has: a core that knows no project and no association, a graph with fields on its nodes and edges, three levels of responsibility instead of two, and a few kinds that no class of statements can ever reach.
{ref}`vocabulary-reference` lists the declarations, {ref}`cli-graph` the commands, {ref}`mcp-tools` the tools, and {ref}`keep-a-club-and-its-offices` shows the routine.
This page covers the first phase of the model, the core.
Assigning events and passages to an entity, circles that the gate reads from the graph, and obligations in the vocabulary come in later phases.

(graph-generic-core)=

## A generic core, and meaning that's declared

Asking what a project is leads nowhere that code can follow.
A project has a goal and an end, but an association has neither, a hosting business runs for years, and the work with a tax advisor never closes.
If "project" were the umbrella term, those would have to be bent into a shape that gives them an end.
Other systems solve this by separating things with a goal from areas of responsibility, or by a fixed hierarchy of file, case and document.
Both work for the people who chose them and fit other work badly.

So the code of Previously doesn't know a project.
It knows entities with a kind, fields and versions, and relations with a kind, two ends, and optionally a period.
What a kind is, which fields it carries and which kinds a relation may connect is **declared**, as events of the action `vocabulary` in the log.
The package ships a base vocabulary with a project, a matter, an organization, a person and a post, and an operator who calls a matter a case, or who needs a `founded` date on an organization, declares it, with no release in between.
{ref}`adapt-the-vocabulary` shows how.

A layer of declarations has a known way to go wrong.
It grows, one request at a time, until it's a poor programming language that nobody can debug.
The line against that gets drawn in three places:

- **Vocabulary is declared, behavior is code.**
  A declaration names kinds, fields and permitted connections.
  What a kind can do is a small fixed set that lives in the code: a relation can be `transitive`, `acyclic` or carry a `period`, and an entity can be `closable` or carry a `period`.
  A declaration switches a behavior on for its kind and invents none.
- **A declaration never loosens the policy.**
  The gate reads three built-in kinds, `circle`, `member_of` and `in_circle`, and their connections stand in the code.
  An event for one of them sets the labels and nothing else, so no declaration can create a kind that opens content to a model, and none can redefine a built-in kind so that the gate decides differently.
  Without that, the layer of meaning would be a back door into the processing policy.
- **The kinds stay coarse.**
  A vocabulary of dozens of kinds is usable; one with a kind for every shade of a business isn't.

An assignment helps to find things, and it doesn't settle facts.
A mail in the wrong matter is found where nobody looks for it, which is annoying and easy to correct.
Whether a deadline holds, or an invoice is paid, never depends on which matter a mail belongs to: that stands in the obligation itself.
This is why a model may be allowed to assign without asking, as the sections below describe, and why the gate is the one place where it may not.

(graph-property-graph)=

## A graph with fields, folded from the log

Three shapes were weighed.

- **A kind per entity in the code** contradicts the generic core.
- **Plain triples, as in RDF,** where even the name of a project is an edge.
  Renaming an entity and moving the end of a relation would then be two statements, each approved on its own, and the operator would see fragments.
  An edge would also have to carry its period and its origin through reification or named graphs.
- **Nodes and edges that carry fields.**
  An entity is one entry that a person proposes, approves and changes in versions as a whole, the way an obligation is.
  A relation carries its period and its sources directly.

Previously takes the third.
It borrows the words where an established vocabulary has them, such as the membership with a period, the post and the holding of a post of the W3C organization ontology, and it takes no technique along: no reasoner, no ontology language.
An entity with fields can be written out as triples without loss, so an export stays possible.

The graph isn't stored anywhere else.
The log is the truth, and the graph is **folded** from the assertions and the actions `vocabulary` and `approval_class` every time it's read.
A triple store holds its edges as the truth and changes them in place, and here nothing is ever changed: a new version is a new event, and what holds is a function of the log.
That has three consequences that the rest of the system relies on.
Reading the graph as it stood at an earlier moment is the same fold over the log up to that moment, so the question "what did Previously know in March about the board of 2019" has an answer.
The graph needs no migration and no rebuild, because there is no table to fill.
And an erasure takes an entity along with its source the way it takes an obligation, because the entity is an assertion with sources.

(graph-two-times)=

## Two times

Every assertion has a `recorded_at`: when Previously learned of it.
A period is when it held.
That the operator held the chair from 2009 to 2015, written down in 2026, needs both, and the two answer different questions.
`previously relations --at 2019-03-01` asks who stood in which relation on that day, and `--as-of` asks what the log said at a given moment.

(graph-levels)=

## Three levels, decided by the server

An obligation is either the operator's word or a proposal.
That line suited obligations, because a wrong one costs an argument.
For the relations that put a mail where it belongs, it would make the operator confirm each one, and models are supposed to find those relations in the end, more of them than anyone can verify.
So the graph has a third level between the two.

| Level | Meaning | Where it comes from |
|---|---|---|
| `direct` | The operator stands for it. | The operator wrote it, or approved a version. |
| `transitive` | The operator stands for it, because they allowed this class of statements in advance. | A model, under an approval class. |
| `open` | A proposal. Nobody stands for it. | A model with no class that fits, or below the threshold. |

What holds is the direct version, else the transitive one, else the open one, and within a level the newest.
Obligations and decisions keep their two levels: the third level exists for entities and relations only, because an obligation is authority.

**The server decides the level, never the client.**
A client gives a confidence and nothing more.
If the client could name its level, a client with a bug or a prompt injection would write itself into the operator's name.
So the write path looks at the author, the kind and the confidence, and at the approval classes in force, and writes `transitive` under the class that covers all three, else `open`.
A preview shows the level the write would decide now; if the decision has moved between preview and confirmation, such as a class that was revoked in between, the write is refused with a sentence and not written otherwise than shown.

**A model never replaces a direct statement.**
Under a class or not, a version from a model on an entity whose standing version is direct is written `open` and contests that version.
That's an **objection**.
If a model could outvote the operator, the log would contain something the operator is supposed to stand for and never saw.
The direct version keeps standing and carries a mark, `contested by`, followed by the objection, in every list, so that anyone who reads the log sees that it wobbles before the operator has answered.
Accepting the objection makes it a direct version, and rejecting it removes the mark.
Both stay in the history.
Objections lead every triage list, and the header of every MCP result counts them, so that a person working with Claude Code or Vibe sees `· 2 objections pending` without asking and the model can point at it.

The operator can be wrong too.
What holds and whether it's still tenable are two questions, and the objection keeps them apart: the direct statement holds until the operator changes it, and the mark says someone found a reason not to trust it.

**A model's answer outside the candidates is open.**
When a model is unsure, it doesn't guess.
It asks a question: a relation that names two to five candidates for its end instead of one entity.
The operator answers it with a direct version that names one of them.
If a model then writes a version on that thread whose end is none of the candidates, it's written `open` whatever its class says.
A question exists because nobody was sure, and an answer from outside the candidates is new information that a person should look at.
The same holds for a retraction by a model on such a thread, since it ends the thread and so answers the question as much as an end does.

**Answering is approving.**
`previously answer` and `write_triage_answer` write the approval of the question with the chosen candidate as its end.
Over MCP that makes `write_triage_answer` the operator's word in the same way `write_approve` is, and it carries the same requirement on the client, to ask the person before every call ({ref}`environment-requirements`).

**A class is measured, not trusted.**
The confidence a model states is badly calibrated: a threshold of 80 doesn't mean 80 percent are right.
Every direct version above a transitive one is a counted error, and each class shows its hit rate, how many of its statements the operator confirmed, corrected, or left standing, with a random sample to look at.
The threshold is set by those numbers.
Revoking a class leaves the statements under it standing and marks them `class revoked`; revoking with `--demote` sets them back to `open`, for a class that produced nonsense from its first day.
Neither rewrites anything.

(graph-gate-kinds)=

## The kinds the gate reads are never transitive

`member_of` and `in_circle` decide which model gets to see a customer's content.
An assignment that errs elsewhere hides or shows a mail in the wrong place; a membership that errs here releases content.
So these kinds, and the entity kind `circle`, are fixed in the code, no approval class covers them, and a model writes them `open` and never otherwise.
`set_class` refuses a class that names one, and the level of a statement of such a kind is `open` even where an event that came another way names the kind in a class.
A transitive version of such a kind can only have come around the write path, and the fold counts it as `open` too, the same fail-safe as for a class nobody knows; `verify` reports the row.

Only the operator makes a circle or a membership direct, and only on the command line.
Over MCP, `write_approve` and `write_triage_answer` refuse a version of such a kind with one sentence, before anything is written: a circle or a membership is approved on the command line.
The reason is that the question a client asks the person before these tools run is a hint, not a lock.
Claude Code offers "Yes, and don't ask again," and once a person has said that, a model could approve its own memberships with nobody looking.
The log couldn't tell that approval from the operator's, either: both are direct, and both keep the model as the author.
Every membership written that way in phases 1 and 2 would be one that phase 3, when the gate starts to read the graph, has to either trust or find a way to distrust.
`write_reject` stays allowed for these kinds, since a rejection makes nothing stand.
Phase 1 keeps the gate itself untouched: nothing in the graph reaches `decide`.

(graph-acyclic)=

## Cycles, and why a model is never refused for one

A kind declared `acyclic`, such as `part_of` in the base vocabulary, forbids cycles: a project can't be part of itself, however indirectly.
The write path checks every version that will stand for the operator against the edges that stand, and refuses the one that would close a cycle.
That covers a direct version, an approval, and an answer.

A model's version is a different case, and it's never refused for a cycle.
The reason is confidentiality.
A client sees part of the graph.
If a refusal said "this would close a cycle," a client could write relations in a preview and learn from the refusals which edges exist among entities it may not see, a free probe it could repeat as often as it liked.
So a model's version of an acyclic kind goes in without that check, and to keep the graph sound the other half holds: **no approval class covers an acyclic kind**.
A model's version of one is therefore always `open`, and an open version stands for nothing.
It can't enter a cycle that anyone relies on, and the operator, who sees the whole graph, is the one who approves it.
The graph in the lists may show a cycle that runs through an open edge; that's a proposal waiting, and not a fact.

A check applies again when the operator approves such a proposal.
If it would close a cycle, the approval is refused.
Over MCP that refusal tells a call that the person confirmed one bit about edges the client may not see.
It's a **residual**, accepted with its reason: the call needs a person's approval, and the bit is the price of keeping the operator's graph free of cycles.
The cost of the rule is that a class can't assign `part_of` in phase 1, and that costs approvals, not safety.

There is no lock for this.
The write path folds the graph under the tip of the chain and appends at the next position; a concurrent write that closes the other half of a cycle loses the position, retries with a fresh fold that includes the winner, and is refused ({ref}`concurrency-graph`).

(graph-recollection)=

## A recollection is withheld until a rule opens it

A statement can rest on events, or on the operator's memory.
A recollection has no sources, only the operator writes one, and it's direct: there's nothing a model could check it against.
That raises a question for the processing policy: it decides what a client sees by the sources of the content, and a recollection has none.

Previously treats it as content of a source named `recollection`, with no identities.
Without a rule for that source, the policy has no rule, and the policy without a rule releases nothing to a client that isn't local ({ref}`processing-policy`).
So an operator's recollection stays out of an MCP client's sight until the operator sets a rule `source:recollection`.
That's the safe side, and it costs one step when the operator wants Claude Code to see what they remember.
A relation is visible to a client when its own sources and both its ends are.
Otherwise the client doesn't see it at all: the lines of an entity and the triage leave it out, without a placeholder, because a placeholder that appears when somebody writes on a hidden thread would itself be a signal.

(graph-cost)=

## What it costs

Reading folds the whole log of assertions, with no projection table in between.
That's the simplest design that keeps the graph a function of the log, and it has a price that grows with the number of statements.

The final review of phase 1 measured it on a graph of about one entity per two relations: organizations, posts, projects and persons, a `part_of` tree over the projects, a `post_in` for every post, and `holds` for the rest.
Each figure is the median of three runs, measured on 2026-10-14.

| What | 2,000 relations, 1,000 entities | 10,000 relations, 5,000 entities |
|---|---|---|
| Folding the graph alone, `read_graph` | 0.08 s | 0.47 s |
| `previously entities` | 0.10 s | 0.53 s |
| `previously relations --at` a day | 0.10 s | 0.54 s |
| Writing one relation | 0.08 s | 0.47 s |
| `verify` over the whole log | 0.62 s | 2.77 s |
| MCP `whoami` | 0.10 s | 0.52 s |
| MCP `list_entities` | 0.28 s | 1.72 s |

The figures at 100,000 relations are still being measured, and this page gets them when they're in.

Every MCP call pays for the fold, `whoami` included, and so do the tools that have nothing to do with the graph.
The first line of every result counts the objections pending, and to count them the server folds the whole graph and asks the processing policy about the sources of every objection, once per call.
Between 2,000 and 10,000 relations the cost grew in line with the graph, so a call costs about half a second at 10,000 relations whatever it asks for.
A cache keyed on the tip of the chain would not help, since every call writes its own access entry and moves the tip.
Phase 1 accepts that cost: a graph of a few hundred statements, which is where a pilot starts, costs milliseconds.
Phase 2 needs a projection or an incremental fold before the data grows, and these figures are what that decision rests on.

Earlier measurements during the build, all on 2026-10-14, show where `verify` grows faster than the graph:

| What | Size | Time |
|---|---|---|
| `verify` over `part_of` chains | 1,000 edges | 0.57 s |
| `verify` over `part_of` chains | 2,000 edges | 1.77 s |
| `verify` over `post_in` relations | 2,000 relations | 0.56 s |
| `verify` over `post_in` relations | 10,000 relations | 2.67 s |
| The header of an MCP result, `whoami`, entities without relations | 1,000 entities | 53 ms |
| The header of an MCP result, `whoami`, entities without relations | 5,000 entities | 153 ms |

The first pair shows that `verify` grows faster than the number of edges when the edges are of an acyclic kind: each such edge is checked against the edges before it, so doubling the chain took about three times as long.
Extrapolated, 10,000 such edges in one chain come to about a minute, which isn't measured.
`verify` runs once a day, so a minute would be tolerable, and the question is only how soon an operator with a large graph gets there.
The `post_in` relations aren't acyclic, and they grow in line with their number.
