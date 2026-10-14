(adapt-the-vocabulary)=

# How to adapt the vocabulary

This guide shows you how to change the kinds of entities and relations that Previously knows: add a field, add a kind, rename a label, and retire a kind.
For why the meaning is declared and where the limit lies, see {ref}`graph-generic-core`; for the form of a declaration, {ref}`vocabulary-reference`; for the command, {ref}`cli-vocabulary`.

You need the base vocabulary applied, as {ref}`keep-a-club-and-its-offices` shows.

## Write the vocabulary out

Print the vocabulary in force as a file, and edit the file:

```shell
previously vocabulary show > vocabulary.toml
```

`show` prints entity kinds before relation kinds, each sorted by identifier.
Printing the file after `apply` of the same file gives the same file back.

## Add a field

To give an organization the day it was founded, add a field to its table:

```toml
[entity.organization]
labels = { de = "Organisation", en = "Organization" }
behaviors = []
fields = [
  { name = "name", type = "text", required = true },
  { name = "founded", type = "date", required = false },
]
```

A field has a type: `text`, `date`, `period`, `choice` or `ref`.
A `choice` lists its `values`, and a `ref` names the kind of entity it points at.
Every entity kind keeps its required text field `name`.

## Add a kind

A kind has an identifier of lower-case letters, digits and `_`, at most 40 characters, and a label in at least one language:

```toml
[entity.event]
labels = { en = "Event" }
behaviors = ["period"]
fields = [
  { name = "name", type = "text", required = true },
  { name = "period", type = "period", required = false },
]
```

A relation kind names the kinds of entity at its ends in `from` and `to`, and may switch on `transitive`, `acyclic` and `period`.
The behaviors are the whole list: a declaration chooses among them and can't invent one.

## Apply it

```shell
previously vocabulary apply vocabulary.toml
```

The command compares the file with the vocabulary in force and prints `add`, `change` or `retire` for each kind, with the attributes that differ under a `change`.
It asks, and writes one event per kind in one transaction.
A refusal comes before the question, such as a relation that names a kind that doesn't exist.
Add `--yes` to skip the question.
Run it again and it prints `nothing to change`.

From then on `previously entity organization --name Test --field founded=2009-05-01` is accepted.
Entities written before the change stay as written; a version that today's vocabulary wouldn't take carries `(does not fit the vocabulary)` in listings and changes nothing in the log.

## Rename a label

Change the `labels` of a kind and apply the file.
Labels are per language, and a listing shows the working language of the entity or, when it has none, the language of `PREVIOUSLY_LANGUAGE` ({ref}`configuration-reference`).
The identifier stays, because the command line, the tools and the approval classes use it.

## Retire a kind

A kind that the file leaves out is retired by `apply`, and the kind stays in the vocabulary with `retired` set.
A retired kind takes no new entity, while a new version of an entity already there may still be written to close, retract or rename it.
A built-in kind, `circle`, `member_of` and `in_circle`, is never retired, and an event for one sets its labels and nothing else.
A kind that another one names in `from`, `to` or a `ref` can't be retired until the other no longer names it.

## After an update

A release that changes the base vocabulary doesn't change yours.
Run `apply --base` after the update; it's safe whether or not you've adapted the vocabulary:

```shell
previously vocabulary apply --base
```

It adds the base kinds the log doesn't hold yet, and it changes nothing else: it never retires a kind, and it never changes one the log already holds, yours included.
For every kind the base holds in another form than your log, it prints a `differs` line with the attributes that differ, the value in the log first and the value in the base second.
To take such a change, print the vocabulary in force, edit it, and apply the file:

```shell
previously vocabulary show > vocabulary.toml
previously vocabulary apply vocabulary.toml
```

Copy the parts you want from the `vocabulary.toml` of the package into your file before you apply it.
Unlike `--base`, `apply FILE` treats the file as the whole vocabulary, so a kind that your file leaves out is retired.
