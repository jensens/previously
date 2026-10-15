(keep-a-club-and-its-offices)=

# How to keep a club and its offices

This guide shows you how to record an association, its founding, the offices and who held them over the years, and how to ask who sat on the board on a given day.
The example is Vellenfeld, a club whose founder was chair, then secretary, and is now treasurer.
For why the model has this shape, see {ref}`graph`; for every option, {ref}`cli-graph`; for the kinds used here, {ref}`vocabulary-reference`.

You need two things before you start.

- The `previously` command from the first release with entities and relations, the one after `0.1.0a6`, or from a checkout, where `uv run previously …` runs it.
- A database that `previously migrate` has brought up to date and `previously project` has built the projections in, with `PREVIOUSLY_DSN` exported.

## Apply the base vocabulary

The kinds used below come with the package, and nothing applies them on its own:

```shell
previously vocabulary apply --base
```

The command prints one line per kind it would write, asks, and prints `vocabulary event ID` for each.
Run it again after an update; it adds the kinds the update brings and changes none that the log holds, so a kind you've adapted stays as it is.
A run with nothing to add prints `nothing to change`.
To change the kinds, see {ref}`adapt-the-vocabulary`.

## Name the sources

Every statement says what it rests on.
Where a mail or a document in the log shows it, give its event with `--source`, as for an obligation ({ref}`record-what-is-owed-and-decided`):

```shell
previously entity organization --name "Vellenfeld" --source 42
```

Where only you know it, state it as your own memory with `--recollection`, which excludes `--source`.
The rest of this guide uses `--recollection`, because the minutes of a founding in 2009 aren't in the log.
A recollection has no source, so it stays out of a client's sight until a rule opens it; see {ref}`graph-recollection`.
A client such as Claude Code sees a placeholder, `no rule covers this content`, where one of them stands.
`previously policy gaps` tells you which rule would open them: it counts the entities and relations stated from memory under `graph:source:recollection`, the rule `source:recollection`; see {ref}`cli-reference`.

## Record the club and its parts

Each command shows the payload and asks `write? [y/N]`; answer `y`, or add `--yes` to skip the question.
It prints the id of what it wrote, such as `assertion 10`.
Note the ids, because the relations name them.

```shell
previously entity organization --name "Vellenfeld" --recollection
previously entity circle --name "Board of Vellenfeld" --recollection
previously entity post --name "Chair" --recollection
previously entity post --name "Secretary" --recollection
previously entity post --name "Treasurer" --recollection
previously entity person --name "Jens" --recollection
previously entity person --name "Eva" --recollection
```

The ids in the rest of this guide are 10 for the club, 11 for the board, 12, 13 and 14 for the three posts, and 15 and 16 for the two people.
Yours differ; read them from `previously entities`.

## Record the founding

A founding is a matter with a day, and it's a part of the club.
The base vocabulary has no founding date on an organization; to add one, see {ref}`adapt-the-vocabulary`.

```shell
previously entity project --name "Founding of Vellenfeld" \
    --field period=2009-05-01..2009-05-01 --recollection
previously relate part_of --from 17 --to 10 --recollection
```

A period is written `FROM..TO`, and either end may be empty.
`part_of` is acyclic and transitive: the write path refuses an edge that would close a cycle, as {ref}`the check at the end <check-a-cycle-is-refused>` shows, and anything that's part of the founding is part of the club.

## Record the offices

Say that the three posts belong to the club:

```shell
previously relate post_in --from 12 --to 10 --recollection
previously relate post_in --from 13 --to 10 --recollection
previously relate post_in --from 14 --to 10 --recollection
```

Then record who held which post and when.
`--from-date` and `--to-date` are the first and the last day, and both count:

```shell
previously relate holds --from 15 --to 12 --from-date 2009-05-01 --to-date 2015-12-31 --recollection
previously relate holds --from 15 --to 13 --from-date 2016-01-01 --to-date 2021-12-31 --recollection
previously relate holds --from 15 --to 14 --from-date 2022-01-01 --recollection
previously relate holds --from 16 --to 14 --from-date 2016-01-01 --to-date 2021-12-31 --recollection
```

A relation without `--to-date` holds until further notice.

## Record the board

The board is a circle, and a membership carries the period in which someone sat on it:

```shell
previously relate member_of --from 15 --to 11 --from-date 2009-05-01 --recollection
previously relate member_of --from 16 --to 11 --from-date 2016-01-01 --to-date 2021-12-31 --recollection
```

The circle is a built-in kind, because the gate reads it.
You write it as the operator, and no model gets to write it other than as a proposal; see {ref}`graph-gate-kinds`.

## Ask who was on the board

To see who sat on the board on March 1, 2019:

```shell
previously relations --type member_of --to 11 --at 2019-03-01
```

```text
26	standing	Member of	15 Jens	11 Board of Vellenfeld	2009-05-01..	1 version
27	standing	Member of	16 Eva	11 Board of Vellenfeld	2016-01-01..2021-12-31	1 version
```

`--type` takes the identifier of the kind, and the listing shows its label.
A relation without a period holds on every day.

To see the offices held on that day, or everyone who held the treasurer's post:

```shell
previously relations --type holds --at 2019-03-01
previously relations --type holds --to 14
```

To see everything about one person, including the relations they're an end of:

```shell
previously entity 15
```

## Correct and end

An office ends with a new version that sets the last day.
Eva stepped down in June 2021:

```shell
previously relate holds --subject 25 --to-date 2021-06-30 --reason "Eva stepped down in June"
```

The version keeps the ends, the first day and the fields, and the listing now shows `2 versions`.
To take a relation back altogether, write `previously relate holds --subject 25 --retract`.
An entity is taken back the same way: `previously entity circle --subject 11 --retract`, which is short for `--state retracted`.
A retracted entity leaves `previously entities` unless you ask for `--state retracted`.
To change an entity, such as the name of the board, write a new version with `--subject`:

```shell
previously entity circle --subject 11 --name "Vellenfeld board"
```

Every version stays in the log.
`previously entity 11 --history` shows them all, and `previously relations --as-of 2026-01-01T00:00:00+00:00` shows the graph as the log stood at that moment.

(check-a-cycle-is-refused)=

## Check that a cycle is refused

The write path refuses an edge that would close a cycle over an acyclic kind.
To see it, state two projects and make the first a part of the second:

```shell
previously entity project --name "Phase one" --recollection
previously entity project --name "Phase two" --recollection
previously relate part_of --from 30 --to 31 --recollection
```

Each command ends with the id of what it wrote:

```text
assertion 30
assertion 31
assertion 32
```

Now make the second a part of the first:

```shell
previously relate part_of --from 31 --to 30 --recollection
```

```text
Error: the relation would close a cycle over a kind that is acyclic
```

Nothing is written.
An edge from the club to the founding is refused earlier, for its kinds: `part_of` starts at a matter or a project, and an organization is neither.
To remove the probe, take the relation back first and then the two entities:

```shell
previously relate part_of --subject 32 --retract
previously entity project --subject 30 --retract
previously entity project --subject 31 --retract
```

`previously entities --type project` now lists only the founding.
`previously entities --type project --state retracted` lists the two phases.

## Let a client look

Claude Code or Vibe reads the same graph with `list_entities`, and writes proposals with `write_entity` and `write_relation`; see {ref}`mcp-tools`.
What a model writes is a proposal until you approve it or you let it stand for a class of statements; {ref}`let-a-model-stand-for-a-class` shows how.
