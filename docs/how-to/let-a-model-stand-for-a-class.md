(let-a-model-stand-for-a-class)=

# How to let a model stand for a class of statements

This guide shows you how to allow a model to state a class of entities or relations in your name, how to read how well it does, how to take the permission back, and how to answer the objections and questions that wait for you.
For why there are three levels of responsibility and a hit rate, see {ref}`graph-levels`; for every option, {ref}`cli-graph`; for the tools, {ref}`mcp-tools`.

You need the base vocabulary applied ({ref}`keep-a-club-and-its-offices`) and a client connected as {ref}`connect-claude-code-and-vibe` describes, with the ask rules from {ref}`record-what-is-owed-and-decided` in place.
A class lets a model write without your looking at each statement, so set the ask rules first.

## Set up a class

A class names an author, the kind of statement, the kinds, and a threshold of the confidence the model states:

```shell
previously classes add offices_claude --author model:claude-code \
    --assertion relation --type holds --type post_in --threshold 90 \
    --statement "Claude Code may state offices at 90 percent"
```

The command shows the class as the payload of the event, asks, and prints `approval class event ID`.

- The name is an identifier: lower-case letters, digits and `_`.
- The author is the client as the log names it, `model:` and the name of the client.
- The threshold is a number from 0 to 100.
  A statement of that author about those kinds whose confidence reaches it gets written `transitive` under the class, and anything below stays `open`.
- `--from` and `--until` limit the class to a window of time, with `--from` included and `--until` excluded.

Some kinds no class can cover.
The command refuses `circle`, `member_of` and `in_circle`, which the gate reads, and a relation kind with the behavior `acyclic`, such as `part_of` in the base vocabulary ({ref}`graph-gate-kinds`, {ref}`graph-acyclic`).
A model's statement of such a kind stays a proposal.

A class never lets a model replace something you wrote.
A statement of a model about an entity you stand for becomes an objection, whatever its confidence.

## Read the hit rate

```shell
previously classes list
```

Each line ends with the hit rate and the event of the class:

```text
offices_claude	model:claude-code	relation	holds,post_in	90	-	active	12 total, 9 confirmed, 1 corrected, 2 standing	(event 30)
```

The hit rate counts what the class let through.
*Confirmed* are versions you approved, *corrected* the ones you rejected or replaced with a version of your own, and *standing* the ones nobody has answered.
A model's stated confidence is badly calibrated, so set the threshold by these numbers: if the corrected count rises, raise the threshold or revoke the class.

Look at the versions themselves with a random sample:

```shell
previously classes sample offices_claude --count 10
```

Each line shows the version, its entity or relation, the kind, a short label, the confidence and the author.
The command prints all of them when there are fewer than you asked for.
To correct one, write a direct version of the same entity or relation with `--subject`, or reject it with `previously reject ID`.

## Take the permission back

Revoke a class that does too much:

```shell
previously classes revoke offices_claude --statement "Too many wrong offices"
```

The versions under the class stay `transitive` and carry `(class revoked)` in listings, so you can go through them one at a time.
If the class produced nonsense from the start, set everything under it back to a proposal:

```shell
previously classes revoke offices_claude --demote --statement "Nothing it stated was right"
```

With `--demote` the versions count as `open` again.
Neither form rewrites the log.
A model that keeps writing after the revocation writes proposals, because no class applies any more.

## See what waits

```shell
previously status
previously triage
```

`status` counts the objections, the questions and the other proposals.
`triage` lists them in the order to work through them, objections first:

- An **objection** is a model's statement against something you stand for.
  The version you wrote keeps standing until you answer, and the objection shows in `triage` and `status` and, over MCP, in `list_triage`.
  On the command line neither `entity ID` nor `relations` marks it; over MCP the label of an entity says `contested by` the objection, and an assignment appears on no entity page.
- A **question** is a relation whose end a model couldn't decide: it names two to five candidates.
- A **proposal** is any other version that waits.

Over MCP, `list_triage` shows the same, limited to what the client may see, and the header of every result counts the objections, such as `· 2 objections pending`.

## Answer an objection or a proposal

Approve what you agree with and reject the rest:

```shell
previously approve 87 --reason "The mail of 14 March shows it"
previously reject 91 --reason "That was a different board"
```

Approving an objection makes it your own direct version, and the mark on the older version goes away.
Rejecting it leaves the older version as it was, and the mark goes away as well.
Both stay in the history.

## Answer a question

Choose one of the candidates:

```shell
previously answer 95 --choose 16 --reason "Eva was treasurer then"
```

The answer is an approval of the question with the chosen candidate as the end.
`approve` refuses a question and names this command.

To answer with something that isn't among the candidates, reject the question first and then state the relation yourself:

```shell
previously reject 95 --reason "None of them"
previously relate holds --from 17 --to 14 --from-date 2016-01-01 --recollection
```

The question and the answer follow one rule, which is why `answer` offers only the candidates.

## Answer through the client

`write_approve`, `write_reject` and `write_triage_answer` answer in your name, so your client has to ask you before it calls any of them.
{ref}`record-what-is-owed-and-decided` shows the ask rules for Claude Code and for Vibe, and `write_triage_answer` belongs on the same list.
A model that writes a version on a thread with a question waiting, with an end that's none of the candidates, gets it written as a proposal whatever its class says.
