(assign-mails-and-read-a-bracket)=

# How to assign mails and read the chronicle of a bracket

This guide shows you how to assign a mail, or some of its units, to a project, a matter or an organization, and how to read everything that belongs to one of them.
The example is a mail from Markus about the project XZ that ends with an afterthought about the summer party of the club.
For why finding works the way it does, see {ref}`chronicle-of-a-bracket`; for every option, {ref}`cli-graph` and {ref}`cli-reference`.

You need three things before you start.

- The `previously` command from the first release with assignments, the one after `0.1.0a7`, or from a checkout, where `uv run previously …` runs it.
- A database that `previously migrate` has brought up to date and `previously project --build` has built the projections in, with `PREVIOUSLY_DSN` exported.
- The base vocabulary, applied with `previously vocabulary apply --base` after the update, which adds the relation kind `concerns`; see {ref}`keep-a-club-and-its-offices`.

## Find the mail and its units

An assignment names an event, and for part of it the units by their numbers.
`previously chronicle` prints one line per unit: the event's id, the unit's number, the time, the source, the external id and the text.
Run `previously project` first if it says the projection stands behind.
Markus's mail is event 1 here, and its fourth unit is the afterthought:

```text
1	1	2026-10-07T10:00:00+00:00	email	markus-1	Projekt XZ
1	2	2026-10-07T10:00:00+00:00	email	markus-1	Der Entwurf für XZ liegt bei.
1	3	2026-10-07T10:00:00+00:00	email	markus-1	Die Abnahme von XZ ist am Freitag.
1	4	2026-10-07T10:00:00+00:00	email	markus-1	Ach übrigens, der Caterer hat zugesagt.
2	1	2026-10-08T18:00:00+00:00	email	verein-1	Sommerfest
2	2	2026-10-08T18:00:00+00:00	email	verein-1	Wer bringt die Bänke mit?
```

## Record the brackets

A bracket is any entity: here the project XZ, the club, and the summer party as a matter that's part of the club.

```shell
previously entity project --name XZ --recollection
previously entity organization --name Verein --recollection
previously entity matter --name Sommerfest --recollection
```

Each command ends with the id of what it wrote, here `assertion 13`, `assertion 14` and `assertion 15`.
Yours differ; read them from `previously entities`.
Make the summer party a part of the club, so that what belongs to the summer party belongs to the club as well:

```shell
previously relate part_of --from 15 --to 14 --recollection
```

## Assign the mail, then the unit that differs

Assign the whole mail to XZ:

```shell
previously relate concerns --from-event 1 --to 13
```

The command shows the version, asks `write? [y/N]`, and prints `assertion 17`.
The mail is its own source, so `--from-event` needs no `--source`.
Then assign the afterthought, unit 4, to the summer party:

```shell
previously relate concerns --from-event 1:4 --to 15
```

The unit's own assignment replaces the mail's for that unit, so unit 4 now belongs to the summer party and not to XZ.
If you want it in both, assign it to XZ as well, with `--from-event 1:4 --to 13`.
A mail that's about the summer party as a whole gets one assignment, `--from-event 2 --to 15`.

To check what stands, list the assignments:

```shell
previously relations --type concerns
```

```text
17	standing	concerns	event 1	13 XZ	-	1 version
18	standing	concerns	event 1 #4	15 Sommerfest	-	1 version
19	standing	concerns	event 2	15 Sommerfest	-	1 version
```

## Read the chronicle of a bracket

Bring the chronicle up to date, and read the summer party's:

```shell
previously project
previously chronicle --within 15
```

```text
1	4	2026-10-07T10:00:00+00:00	email	markus-1	Ach übrigens, der Caterer hat zugesagt.
2	1	2026-10-08T18:00:00+00:00	email	verein-1	Sommerfest
2	2	2026-10-08T18:00:00+00:00	email	verein-1	Wer bringt die Bänke mit?
```

One level up, `previously chronicle --within 14` prints the same three lines for the club, because the summer party is part of it.
The project's chronicle holds the rest of the mail:

```shell
previously chronicle --within 13
```

```text
1	1	2026-10-07T10:00:00+00:00	email	markus-1	Projekt XZ
1	2	2026-10-07T10:00:00+00:00	email	markus-1	Der Entwurf für XZ liegt bei.
1	3	2026-10-07T10:00:00+00:00	email	markus-1	Die Abnahme von XZ ist am Freitag.
```

`--since`, `--until` and `--limit` narrow it as they narrow the whole chronicle.
An id that isn't an entity that stands is refused, and the chronicle isn't read:

```shell
previously chronicle --within 99
```

```text
Error: --within 99 is not an entity that stands
```

An MCP client reads the chronicle of a bracket with the tool `previously` and its argument `within`, through the assignments and the parts it may see, and within what the processing policy lets it see; see {ref}`mcp-tools`.

## Correct an assignment

An assignment is taken back like any relation, with a new version.
If the afterthought belongs to XZ after all, retract its own assignment:

```shell
previously relate concerns --subject 18 --retract --reason "belongs to XZ after all"
```

Unit 4 then inherits the mail's assignment again, and after `previously project`, `previously chronicle --within 13` prints it as the fourth line:

```text
1	4	2026-10-07T10:00:00+00:00	email	markus-1	Ach übrigens, der Caterer hat zugesagt.
```

Erasing a mail, or a unit of it, takes its assignments with it, and an assignment of the whole mail falls with any unit erased after it; see {ref}`erase-something`.
