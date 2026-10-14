(vocabulary-reference)=

# Vocabulary

The vocabulary says which kinds of entities and relations exist, and what a statement about one may say.
It's a sequence of events of the kind `action` with `payload.action` set to `vocabulary`, written with no source key and no units.
`previously vocabulary apply` writes them, and `previously vocabulary show` prints the vocabulary in force; {ref}`cli-vocabulary` describes the command.

## The payload

The payload holds exactly these keys, no more and no fewer.

| Key | Value |
|---|---|
| `action` | `vocabulary`. |
| `declares` | `entity` or `relation`. |
| `name` | The identifier of the kind: a letter from `a` to `z`, then up to 39 of `a` to `z`, digits and `_`. |
| `labels` | An object from a language tag to a text of 1 to 80 characters without control characters. At least one language. |
| `fields` | A list of fields, each an object with exactly the keys below. |
| `behaviors` | A list. An entity kind has `closable` and `period`, a relation kind has `transitive`, `acyclic` and `period`. |
| `from`, `to` | For a relation, lists of identifiers of entity kinds. For an entity, `null`. |
| `retired` | `true` when the kind takes nothing new. |
| `statement` | The sentence it was written with. It isn't blank. |

A field has these keys:

| Key | Value |
|---|---|
| `name` | An identifier. Field names are unique within a kind. |
| `type` | `text`, `date`, `period`, `choice` or `ref`. |
| `values` | For a `choice`, 1 to 50 distinct texts. Otherwise `null`. |
| `ref` | For a `ref`, the identifier of an entity kind. Otherwise `null`. |
| `required` | `true` or `false`. |

A language tag is two or three lower-case letters, then any number of groups of one to eight letters or digits after a hyphen.

### Rules across the keys

- Every entity kind has a required text field `name`.
- A field named `period` has the type `period`, and an entity kind with the behavior `period` has one.
- A relation kind has no field `period`, because the relation has a period of its own.
- A relation kind that isn't built in names at least one kind in `from` and in `to`.

## What a write checks

`apply` checks the whole vocabulary as it would stand afterward, so one file may declare a relation together with the entity kinds it connects.
It refuses with one sentence and writes nothing when one of these holds:

- A kind in `from`, `to` or the `ref` of a field isn't an entity kind that stands, which includes a retired one.
- A kind that another one names is retired.
- A built-in kind is retired, or differs from its fixed form in anything but its labels.

## Reading the vocabulary

A newer event with the same `declares` and `name` replaces the older one, and the vocabulary of a past day is the log read up to that day.
A retired kind stays in the vocabulary with `retired` set.
An event that was erased, or whose form is broken, counts as nothing.
`verify` reports a broken form with a finding of the form `vocabulary event has no valid form: it has no label in any language`, and an event with units with `vocabulary event has units`.

## Built-in kinds

Three kinds are built in, because the gate reads them: the entity kind `circle` and the relation kinds `member_of` and `in_circle`.
They always exist.
Their connections and behaviors stand in the code, and an event for one of them sets the labels and nothing else.

| Kind | Connects | Behaviors |
|---|---|---|
| `circle` | An entity kind with the field `name`. | None. |
| `member_of` | `organization` and `person` to `circle`. | `period`. |
| `in_circle` | Nothing yet, to `circle`. | None. |

`show` marks each of the three with the comment line `# built in: the gate reads it; only its labels can change` directly above its table.
`apply` reads it as the comment it is.

`in_circle` starts at an event, which isn't an entity kind, so its `from` is empty until a later phase gives a relation that start.

## The file

The file is TOML.
A table `[entity.NAME]` or `[relation.NAME]` declares a kind, with the keys `labels`, `fields`, `behaviors`, `from`, `to` and `retired`.
An unknown key or table is an error.
`show` prints one canonical form: entity kinds before relation kinds, each sorted by identifier.
A retired kind has `retired = true`.

## The base vocabulary

The package ships `vocabulary.toml`, and `previously vocabulary apply --base` adds each of its kinds that the log doesn't hold.
It never retires a kind or changes one the log holds.
Nothing applies it on its own.
The built-in kinds always exist, so `apply --base` never writes them.
It writes the nine kinds in the table below, while `show` lists those nine and the three built-in kinds, twelve in all.

| Kind | Declares | Behaviors | Connects |
|---|---|---|---|
| `organization` | entity | None. | |
| `project` | entity | `closable`, `period`. | |
| `matter` | entity | `closable`, `period`. | |
| `post` | entity | None. | |
| `person` | entity | None. | |
| `part_of` | relation | `transitive`, `acyclic`. | `matter` and `project` to `project` and `organization`. |
| `holds` | relation | `period`. | `person` to `post`. |
| `post_in` | relation | None. | `post` to `organization`. |
| `involved_in` | relation | `period`. | `circle`, `organization` and `person` to `matter` and `project`; the text field `role`. |

Every label comes in German and English.
The relation `concerns` isn't in it, because it starts at an event.
