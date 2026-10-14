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
