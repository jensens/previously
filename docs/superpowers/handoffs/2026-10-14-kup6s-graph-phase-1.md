# Handoff to kup6s: entities and relations, the first phase

**Date:** 2026-10-14
**From:** the Previously repository, `jensens/previously`
**To:** the agent that works in the kup6s environment
**Source:** the specification `docs/superpowers/specs/2026-10-14-zuordnungen.md`, phase 1, and the answer of the maintainer to the feedback of `v0.1.0a6`

This file adds to the earlier handoffs under `docs/superpowers/handoffs/`, which stand as written.
Like them, it says **what** Previously needs, **why**, and **how to recognize that it stands**, and never how to build it in cdk8s.

The release asks nothing new of the environment: no migration, no setting that has to be set, no secret, no grant.
One setting is new and optional, `PREVIOUSLY_LANGUAGE`, the language of the labels in listings, `en` when it's unset.
It adds entities and relations to the log, five tools to the MCP server, and one step the maintainer takes by hand once.

## The image

The release after `v0.1.0a6`; the maintainer picks its number when they cut it.
Pin its exact version, as for every release until `1.0.0`.
Run the migration job as for every release, and expect `up to date:` with `0005_watermark`, which is unchanged: this release adds no table.
The graph is read by folding the log, with no table in between.

**It stands when** the tools pod, the jobs and `previously-mcp` run the new version, and the migration job reported `up to date:` with `0005_watermark`.

## One step after the image: the base vocabulary

Which kinds of entities and relations exist is declared in the log, and nothing declares them on its own.
After the image runs, once, in the tools pod:

```shell
previously vocabulary apply --base
```

The command prints one line per kind it would write, asks, and writes one event per kind.
It needs no `--yes` when the maintainer runs it from a terminal.
Run it again after an update whose notes say the base vocabulary changed; it prints `nothing to change` otherwise.

That is a step of the operator and not of a job.
A CronJob that applied the base vocabulary would undo whatever the maintainer adapts: `apply --base` treats the file as the whole vocabulary and retires a kind that the file leaves out.

**It stands when** `previously vocabulary show` in the tools pod prints the base vocabulary, with the kinds `organization`, `person`, `post`, `project`, `matter` and the relations `holds`, `post_in`, `part_of`, `involved_in` and `member_of`.

## The tool list grows from ten to fifteen

`previously-mcp` offers `list_entities`, `write_entity`, `write_relation`, `list_triage` and `write_triage_answer` in addition to the ten it has.
`write_triage_answer` answers a question in the maintainer's name, like `write_approve` and `write_reject`, so the requirement on the clients stands as the earlier handoffs state it, and it covers the third tool: the client asks the person before every call, and none of the three may be allowed always.
That is on the maintainer's machine and not in kup6s.

A client that keeps its tool list across sessions has to fetch it again.
Mistral Vibe may need that; the maintainer knows.

The header of every MCP result now counts the objections waiting for the operator, as `· N objections pending`, only when N is more than zero.
It costs one fold of the graph per call.
The maintainer measured `whoami` at 53 ms with 1,000 entities and at 153 ms with 5,000, on 2026-10-14; a pod that is much slower than the maintainer's machine will show more.

**It stands when** `list_entities` answers over MCP, from the maintainer's client or with a token from `previously client`, and `previously access` lists the call.
An empty graph answers with an empty list and no error.

## What a client doesn't see by default

A statement that rests on the operator's memory has no source event.
The policy treats it as content of a source named `recollection`, and with no rule for that source a client that isn't local gets a placeholder.
That is the safe side.

**Only if the maintainer wants a client to see recollections,** they set the rule themselves with `previously policy rule source:recollection …`.
Do not set it for them, and do not set it in a job.
The default stays as it is until they say so.

## What this release leaves

- **The gate is untouched.**
  Nothing in the graph reaches the processing policy in this phase, and no approval class covers the kinds the gate will read later.
  A check of the policy after the update gives the same answers as before.
- **`verify` costs more with a large graph.**
  Over a chain of 2,000 edges of an acyclic kind it took 1.77 s, and the cost grows faster than the number of edges.
  The daily `verify` job needs no change at the sizes of a pilot.
  If the graph grows into the tens of thousands of relations, report the time of the job.

## A host without a cluster

A `docker-compose` file changes its image tag, runs `previously vocabulary apply --base` once with `docker compose run` or `docker compose exec`, and nothing else.
This file considers it and builds nothing for it.

## How to recognize that everything stands

1. The tools pod, the jobs and `previously-mcp` run the new version, and the migration job reported `up to date:` with `0005_watermark`.
2. `previously vocabulary show` prints the base vocabulary, and `previously entities` answers, with an empty list on a log that has no entities yet.
3. `list_entities` answers over MCP, and `previously access` lists the call.
4. `tools/list` of `previously-mcp` shows fifteen tools.
