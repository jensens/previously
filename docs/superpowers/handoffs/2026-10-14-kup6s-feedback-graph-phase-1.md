# Feedback from kup6s: `v0.1.0a7`, entities and relations

**Date:** 2026-10-14
**From:** the agent that works in the kup6s environment
**To:** the Previously repository, `jensens/previously`
**Answers:** `handoffs/2026-10-14-kup6s-graph-phase-1.md`

All four checks stand.

1. The tools pod, the six jobs and `previously-mcp` run `0.1.0a7`; the migration job reported `up to date: 0005_watermark`.
2. `previously vocabulary apply --base`, run by the maintainer in the tools pod, wrote nine events (98 to 106), and `previously vocabulary show` prints the kinds `organization`, `person`, `post`, `project`, `matter` and the relations `holds`, `post_in`, `part_of`, `involved_in` and `member_of`; `previously entities` answers on the empty graph without an error.
3. `list_entities` over MCP, with the maintainer's client token, answered `No results.`, and `previously access` lists the call.
4. `tools/list` of `previously-mcp` shows fifteen tools.

Nothing else changed in kup6s: no setting, secret, grant or network rule.
`PREVIOUSLY_LANGUAGE` stays unset.
No rule for `source:recollection` was set.
In the maintainer's Claude Code settings, `write_approve`, `write_reject` and `write_triage_answer` stand under `permissions.ask`.

## One thing a reader stumbles over

The handoff counts `member_of` among what `vocabulary apply --base` declares.
The command didn't list it among its nine `add` lines, yet `vocabulary show` prints it, together with the entity `circle` and the relation `in_circle`, which nobody wrote either.
We read those three as built-in, coming from the policy's circles and memberships.
If that's right, a sentence in the handoff or in `vocabulary show`'s output saying which kinds are built-in would spare the comparison.

## Timing

The tag `v0.1.0a7` stood in the repository about nine minutes before the image was on ghcr.io, while the release workflow built and tested it.
kup6s waited for the image; a handoff that arrives with the tag can say so, or arrive after the workflow.

## The club how-to as acceptance

The maintainer asked for `docs/how-to/keep-a-club-and-its-offices.md` as the acceptance of the graph, and kup6s ran it in the tools pod step by step, all with `--recollection`, the ids read from the output (107 to 124 instead of 10 to 27).
Every step answered as the how-to says:

- The board on 2019-03-01 lists Jens and Eva; the offices held that day are Jens as secretary and Eva as treasurer; the treasurer's post lists Eva 2016 to 2021 and Jens from 2022; `previously entity 112` shows Jens's offices and his membership.
- Eva stepping down gave her relation a second version ending 2021-06-30; the renamed board has two versions in `--history`; `--as-of` a moment before the corrections shows the old period and one version.
- Through MCP, `list_entities` for `claude-code` returns placeholders only, with `no rule covers this content`, since there's no rule for `source:recollection`.

The how-to says the write path refuses an edge that would make the founding a part of itself.
A reversed edge from the club to the founding is refused for its kinds before any cycle is checked (`the start of the relation is of a kind its relation kind does not start from`), so we probed the rule with a second project: `the relation would close a cycle over a kind that is acyclic`.
The probe's edge and entity were retracted afterwards (events 125 to 128).

Three small things came up:

- **Retracting differs by command.** A relation is taken back with `relate … --subject N --retract`, an entity with `entity … --subject N --state retracted`; `entity … --retract` is refused as an unknown argument.
  The how-to shows only the relation's form.
- **A retracted entity still shows over MCP.** `previously entities` lists active entities by default and leaves out the retracted probe; `list_entities` over MCP returns a placeholder for it as well, so a client learns that it exists, though not that it was retracted.
  If MCP is meant to default to active entities as the command line does, it doesn't yet.
- **The placeholder could name the scope.** `no rule covers this content` is right; naming `source:recollection` in it would tell the operator which rule would open it, as the handoff explains.
