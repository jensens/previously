You are gathering evidence for a checkpoint ("Prüfpunkt") in the project "Previously", an append-only event log for project histories (Python 3.14, SQLAlchemy Core, PostgreSQL, AGPL). The project's architecture record prescribes this checkpoint before the remaining sub-projects are planned. Your part is two of its five questions. You read and measure; you change nothing in the repository.

Work in the git worktree `/home/jensens/ws/jwk/previously/.claude/worktrees/pruefpunkt-teilprojekt-1`. Run every command from there; never touch the parent checkout. The one file you create is your report (below). Do not dispatch subagents.

## What exists and what does not

Built and merged: stage 1a (the log: `event`, `unit`, `source_key`, hash chain, `append`, `verify`), stage 1b (projections: a worker, `p_chronicle`, `p_source_stats`, commands `project`, `chronicle`, `stats`), and the external anchor (`anchor`, `verify --anchors`). Not built: stage 1c (blobs, search), every entity of the core model, every assertion ("Feststellung") and action ("Handlung"), connectors, the MCP server, the gate, the AI layer.

The specifications are German and frozen: they record what was decided on their date and are not updated. What is authoritative today is the tree and the English pages under `docs/explanation/`. So "the specification says X and the tree does Y" is the normal case, and it is exactly what you are looking for.

## The two questions

They are quoted from `docs/superpowers/specs/2026-10-01-architektur.md` §12.3 (read §12 there first, lines 1484 to 1555):

**1. "Hat das Kernmodell den Kontakt überlebt? Sind von den zehn Entitäten welche falsch, zusammenzulegen oder zu ergänzen?"**

The honest starting point is that the ten entities have had no contact yet — none is built. Do not speculate about them. What did have contact is the layer below them, and that is where you look:

- **The log as designed against the log as built.** The design: `docs/superpowers/specs/2026-10-01-previously-design.md` §5 (lines 215 to 520) and the architecture record §3 (glossary) and §4.1 to §4.3 (schema). The tree: `migrations/`, `src/previously/storage/schema.py`, `src/previously/contract/types.py`, `src/previously/contract/rows.py`, `src/previously/core/` (`append.py`, `hashing.py`, `canonical.py`, `units.py`, `verify.py`). List every difference you can show: a field or table the design has and the tree has not, one the tree has and the design has not, a field whose meaning moved, a rule that was added (what goes into the hash, what `append` refuses, what a tombstone leaves standing). For each: where the design says it, where the tree does it, and — if a frozen specification's amendment, an explanation page or an execution record gives the reason — the reason, with its place.
- **What the built layer now presupposes about the layers above.** Only concrete points you can show in the tree: for example the event kinds that exist (`observation` and what else?), how an assertion event would have to look to pass `append` and `verify` as they are, what the projection mechanism as built (`src/previously/core/projection/`, the `Projection` protocol with its pure functions) demands of a projection like the design's `p_obligation` example in the architecture record §4.4. A tension is a place where the design's description of an entity, an assertion or a projection does not fit through what is built without one of them changing. State each as: what the design assumes, what the tree requires, why they do not fit. If you find none in an area, say so in one line.

**4. "Steht jeder Leitsatz noch, oder wurde einer unter Druck gebogen?"**

The nine guiding principles are in the design, §3 (lines 82 to 153). For each of the nine: what in the tree, the frozen specifications' amendments, the explanation pages or the execution records touches it — either holds it, or bends it, or shows that it has not been tested yet because nothing it governs is built. Give evidence both ways where both exist. Candidates worth checking, without presuming the answer: principle 3 ("nothing is deleted") against the tombstone seam and what stage 1b found about erasure; principle 6 ("take in more": full raw content, all headers) against what a `RawEvent` carries; principle 4 (perceptions cannot be wrong) against what `append` refuses; principle 9 (undecidedness must be representable) against any default the tree sets.

## Where the evidence is

- The design and the architecture record, as above. The stage specifications: `docs/superpowers/specs/2026-10-02-stufe-1a-log.md` (its dated amendments, "Nachtrag", and its sections on what stays open), `docs/superpowers/specs/2026-10-04-stufe-1b-projektionen.md` (§1.1 and §10), `docs/superpowers/specs/2026-10-04-aeusserer-anker.md` (§1.1, §10).
- `docs/explanation/*.md` — the reasoning as it stands today; `docs/explanation/design-records.md` carries a table from cited paragraphs to pages.
- The execution records' summaries: `docs/superpowers/sdd/2026-10-03-dokumentation/index.md`, `docs/superpowers/sdd/2026-10-04-stufe-1b-projektionen/index.md`, `docs/superpowers/sdd/2026-10-04-aeusserer-anker/index.md`. Their `progress.md` files hold every ruling; consult them when a difference puzzles you.
- `NOTIZEN.md` in the repository root: the maintainer's brainstorming notes.

## How to work

Evidence, not opinion: every row of your report carries a place in a document (`file:line`) and a place in the tree, or says that one of the two does not exist. Where you count something, give the command. Where you judge — "this bends the principle", "this is a tension" — mark the sentence as your judgment and keep it apart from the evidence. A finding you cannot show is not a finding; say what you looked at instead.

Do not propose designs for the sub-projects that are not built, and do not grade the work that is. The checkpoint's author decides what follows from your evidence.

## Report

Write the report in German (identifiers and quoted English stay as they are) to:
`/home/jensens/ws/jwk/previously/.claude/worktrees/pruefpunkt-teilprojekt-1/.superpowers/pruefpunkt/bericht-a1-kernmodell-leitsaetze.md`

Structure:
- `## Frage 1: der Log, wie entworfen und wie gebaut` — a table: what, design (place), tree (place), reason (place) or "kein Grund gefunden".
- `## Frage 1: was die gebaute Schicht von den Schichten darüber verlangt` — one short entry per tension: assumption, requirement, why they do not fit; or the areas where you found none.
- `## Frage 4: die neun Leitsätze` — a table: principle, what touches it (places), status: hält | gebogen | ungeprüft, and one sentence of judgment marked as such.
- `## Was ich nicht klären konnte` — questions the evidence left open.
- `## Was ich gelesen und gefahren habe` — files with line ranges, commands.

Then reply with ONLY (under 15 lines): the three to five findings that weigh most, one line each with its place; the count of rows in each table; the report file path.
