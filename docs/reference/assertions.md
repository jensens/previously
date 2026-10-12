(assertions-reference)=

# Assertions

An assertion is an event of the kind `assertion`: an obligation, a decision, or the rejection of a proposal.
It has no units and no source key, its `occurred_at` is its `recorded_at`, and its payload holds the whole statement.
`previously assert`, `approve` and `reject` write assertions, and so do the MCP tools `write_assertion`, `write_approve` and `write_reject`; {ref}`cli-reference` describes the commands and {ref}`mcp-tools` the tools.
{ref}`assertions` explains why an assertion has this form.

## The payload

The payload holds exactly the keys of its kind, no more and no fewer.
The kind stands under `assertion`.

Every kind has these keys:

| Key | Value |
|---|---|
| `assertion` | `obligation`, `decision` or `rejection`. |
| `author` | Who formulated it: `human:operator`, or `model:` and the name of a client, of 1 to 200 characters, without white space and without control or format characters. |
| `responsibility` | Who stands for it: `direct` or `open`. |
| `sources` | The events it rests on: a list of at least one object with exactly the keys `event` and `units`. |
| `reason` | Why this version was written: a text that isn't blank, or `null`. |
| `handle` | The identifier of the MCP handle whose confirmation wrote it, or `null` for an assertion the command line wrote. |

An entry of `sources` holds:

| Key | Value |
|---|---|
| `event` | The id of an event, a whole number from 1 to 2^53 − 1. |
| `units` | The units it cites, as a list of at least one whole number from 0 to 2^53 − 1, ascending and without a repeat, or `null` for the whole event. |

An obligation and a decision add `subject` and `approves`:

| Key | Value |
|---|---|
| `subject` | The id of the first version of the entry this version belongs to, or `null` for a first version. |
| `approves` | The id of the proposal this version approves, or `null`. |

An obligation adds:

| Key | Value |
|---|---|
| `debtor` | Who owes: a reference. |
| `creditor` | To whom: a reference. |
| `what` | What's owed: a text that isn't blank. |
| `due` | By when: a date written `YYYY-MM-DD`, or `null`. |
| `state` | `open`, `fulfilled` or `cancelled`. |

A decision adds:

| Key | Value |
|---|---|
| `what` | What was decided: a text that isn't blank. |
| `by` | Who decided: a list of at least one reference. |
| `on` | When it was decided: a date written `YYYY-MM-DD`. |
| `state` | `valid` or `revoked`. |
| `replaces` | The id of the decision it replaces, or `null`. |

A rejection adds:

| Key | Value |
|---|---|
| `of` | The id of the proposal it rejects. |

A date is a day of the calendar in exactly the form `YYYY-MM-DD`: `2026-02-30`, `20261130` and `30.11.2026` aren't dates here.
A text is blank when it holds nothing but white space.
The payload follows the payload range of every event ({ref}`payload-range`), so it holds no floating point number.

### Rules across the keys

- An approval, a version with `approves`, has a `subject` and is `direct`.
- A version whose `author` starts with `model:` is `direct` only as an approval.
- A rejection is `direct`.

### Examples

A first version of an obligation, written on the command line:

```json
{
  "assertion": "obligation",
  "author": "human:operator",
  "responsibility": "direct",
  "sources": [{"event": 42, "units": [2, 3]}, {"event": 45, "units": null}],
  "reason": null,
  "handle": null,
  "subject": null,
  "approves": null,
  "debtor": "own",
  "creditor": "circle:huber",
  "what": "Send the offer for the roof",
  "due": "2026-11-30",
  "state": "open"
}
```

A proposal of a decision, written by the client `claude-code`:

```json
{
  "assertion": "decision",
  "author": "model:claude-code",
  "responsibility": "open",
  "sources": [{"event": 42, "units": [4]}],
  "reason": null,
  "handle": "Hk2l9mXcPq3vT0aYbW8eRg",
  "subject": null,
  "approves": null,
  "what": "The TLS certificate comes from the customer's own CA",
  "by": ["address:eva@huber.example", "own"],
  "on": "2026-09-12",
  "state": "valid",
  "replaces": null
}
```

The rejection of that proposal, written on the command line, where the proposal is event 57:

```json
{
  "assertion": "rejection",
  "author": "human:operator",
  "responsibility": "direct",
  "sources": [{"event": 42, "units": [4]}],
  "reason": "Eva asked about it and nobody decided",
  "handle": null,
  "of": 57
}
```

(assertions-references)=

## References to actors

`debtor`, `creditor` and every entry of `by` are references, in one of four forms:

| Form | Means | Rule |
|---|---|---|
| `own` | The own side. | Exactly these three letters. |
| `circle:NAME` | A customer, by its circle. | `NAME` isn't blank, the rule the policy applies to the name of a circle. The circle doesn't have to exist in the policy. |
| `address:ADDRESS` | A person, by a mail address. | `ADDRESS` has at most 254 characters, exactly one `@` with a part before and after it, no white space and no control or format characters. |
| `name:TEXT` | Anybody else, by a label. | `TEXT` has 1 to 200 characters, isn't blank, and holds no control or format character and neither U+2028 nor U+2029. |

A reference in any other form is refused.
Two `name:` references never count as the same actor, whatever their text.

## Entries, versions and proposals

An obligation or a decision is an entry, named after the id of its first version, as `previously://event/<id>` over MCP.
Every version of it whose `subject` names that id belongs to it.
A rejection belongs to the entry of the proposal it rejects.

| Term | Definition |
|---|---|
| Direct version | A version with `responsibility` `direct`. |
| Proposal | A version with `responsibility` `open`. |
| Answered | A proposal that an approval names in `approves` or a rejection in `of`. |
| What stands | The latest direct version; without one, the latest proposal that isn't answered. |
| Stands as a proposal | An entry whose version that stands is a proposal. |
| Pending proposal | A proposal that isn't answered, isn't what stands, and, where a direct version exists, is newer than it. |
| Replaced | A decision that the `replaces` of another decision names, where the version that stands of that other decision is direct. The command line marks it; a list over MCP doesn't. |
| Overdue | An obligation whose version that stands is `open` and has a `due` before the reader's date, which the command line and the MCP server take as the UTC date of the moment they read. |

Latest and newer mean the order of the chain.
"Overdue" is never stored; it's computed when an entry is read.

An entry stands as long as one of its versions stands, and keeps its id when its first version is erased.
An entry without a standing version is in no list, and asking for it answers as for an id that names nothing.
An entry whose every version is a rejected proposal has nothing that stands either: it's in no list, and only its history answers for it.

## What a write checks

Beyond the form above, a write refuses a batch when any of these fails, and writes nothing:

| Check | Rule |
|---|---|
| Size | One batch holds 1 to 500 statements, all with the same `handle`. Over MCP, one call holds 1 to 20. |
| Sources | Every source is an event that exists, is an observation and isn't erased, and every unit it cites exists and isn't erased. |
| `subject` | Names an entry of the same kind that stands below the tip, or that an earlier statement of the same batch creates. |
| `replaces` | Names a decision that stands. |
| `approves` | Names a proposal of the entry that `subject` names, which isn't answered, and the approval carries its content, its sources and its author unchanged. |
| `of` | Names a proposal that stands and isn't answered, and the rejection carries its sources unchanged. |

A batch whose `handle` an assertion in the log carries already is written once: a repeat writes nothing and answers with the ids of the assertions that carry it and still stand.
`verify` checks the same rules for every assertion in the log, and {ref}`cli-reference` lists its findings under `verify`.

## What an erasure takes

An erasure takes an assertion along when it erases a source event of it, a unit it cites, or a unit of an event it cites whole that's erased after the assertion.
The assertion's payload is erased by a redaction of its own, with the reason `cascade of redaction ID`, in the same transaction; `redact` prints it as `cascaded: assertion ID` ({ref}`cli-reference`).
An erasure of a blob takes no assertion along.
