You are gathering evidence for a checkpoint ("Prüfpunkt") in the project "Previously", an append-only event log for project histories (Python 3.14, SQLAlchemy Core, PostgreSQL, AGPL). The project's architecture record prescribes this checkpoint before the remaining sub-projects are planned. Your part is two of its five questions. You read and measure; you change nothing in the repository.

Work in the git worktree `/home/jensens/ws/jwk/previously/.claude/worktrees/pruefpunkt-teilprojekt-1`. Run every command from there; never touch the parent checkout. The one file you create is your report (below). Do not dispatch subagents.

## What exists and what does not

Built and merged: stage 1a (the log: `event`, `unit`, `source_key`, hash chain, `append`, `verify`), stage 1b (projections: a worker, `p_chronicle`, `p_source_stats`, commands `project`, `chronicle`, `stats`), and the external anchor (`anchor`, `verify --anchors`). Not built: stage 1c (blobs, search), every entity of the core model, connectors, the MCP server, the gate, the AI layer.

The specifications are German and frozen: they record what was decided on their date and are not updated. What is authoritative today is the tree and the English pages under `docs/explanation/`. So "the specification says X and the tree does Y" is the normal case, and it is exactly what you are looking for.

## The two questions

They are quoted from `docs/superpowers/specs/2026-10-01-architektur.md` §12.3 (read §12 there first, lines 1484 to 1555):

**2. "Ist die Storage-Schnittstelle noch schmal, oder ist SQL durchgesickert?"**

The architecture record's §5 (lines 462 to 500) gives the interface as it was meant: nine methods, and five properties it "deliberately must not have" — no update, no delete, no transaction control outward, no SQL pass-through, no database objects returned. Measure the tree against that:

- **The protocols**: `src/previously/contract/store.py`. Count the methods of each protocol, with the command. For each of the five properties: does the interface as built have it or not, and where is the decision recorded (a frozen specification's amendment, `docs/explanation/module-boundaries.md`, an execution record)? `begin()` and `snapshot()` hand a connection to the caller — say plainly what that means for "no transaction control outward" and "no database objects returned", and what the generic `Conn` type parameter does and does not hide.
- **What goes around the protocols**: every method of `PostgresStorage` in `src/previously/storage/postgres.py` that is in no protocol, and every caller of it (`grep` over `src/`). Every import of `previously.storage` and of `sqlalchemy` outside `src/previously/storage/` (`grep`, and `.importlinter` for what the gate enforces and which exemptions are named). Does any module above `storage` build a query, name a table or a column, or depend on a PostgreSQL behavior — an isolation level, an index, an error class? The comments in `src/previously/core/append.py` and `docs/explanation/concurrency.md` are where to look for the last.
- **Growth**: how many methods did the interface have after stage 1a, after stage 1b, after the anchor? `git log -p -- src/previously/contract/store.py src/previously/storage/postgres.py` and the frozen stage specifications tell. A number per stage, and what each addition was for.
- Your judgment, marked as such, in two or three sentences: narrow, or leaking, and at which seam the next sub-projects (a second reader of the log; search; blobs) will press on it.

**5. "Was aus §11 war doch tragend?"** — the architecture record calls this the most important of the five: §11 collects what the document declared uncritical, "genau dort werden die Überraschungen liegen".

- **§11 itself** (lines 1435 to 1480, a table of eight rows and an amendment of 2026-10-03): for each row, was it touched while stages 1a, 1b and the anchor were built? Did something that was built turn out to depend on it, or to pre-empt it? Evidence from the tree and the records; "not touched, nothing built depends on it" is a valid answer and most rows will have it.
- **§13 of the architecture record** (open points, lines 1556 to 1574) and **§16 of the design** (`docs/superpowers/specs/2026-10-01-previously-design.md`, lines 1720 to 1759): the same question, row by row.
- **What the architecture record declared decided and the build changed.** This is the other half of the same question — surprises in what was thought settled. Go through §4.4 (projections), §4.6 (erasure: "heute nichts verbauen"), §7 (process model: the job queue, concurrency, error behavior), §10.1 (SQLAlchemy Core, Pydantic, Alembic), §10.6 and §10.7 (tools, dependencies), and the "Nachweis" column of the table in §12.1 for stages 1a and 1b. For each determination: built as stated, built differently, or deferred — with the place in the record, the place in the tree or the stage specification, and the reason where one is written down. Two to check without presuming the answer: §12.1 names for stage 1b a "Schattentabelle mit Umschaltung" and "Eingang läuft weiter" during a rebuild; and §4.6 names three provisions for erasure as part of sub-project 1.
- **Surprises from places nobody listed.** The three execution records each end with what the execution taught: `docs/superpowers/sdd/2026-10-03-dokumentation/index.md`, `docs/superpowers/sdd/2026-10-04-stufe-1b-projektionen/index.md`, `docs/superpowers/sdd/2026-10-04-aeusserer-anker/index.md`. Which of those lessons concern something that neither §11, §13 nor §16 had on a list? Name each with its place.

## Where the evidence is

- The architecture record and the design, as above. The stage specifications: `docs/superpowers/specs/2026-10-02-stufe-1a-log.md`, `docs/superpowers/specs/2026-10-04-stufe-1b-projektionen.md`, `docs/superpowers/specs/2026-10-04-aeusserer-anker.md` — their dated amendments ("Nachtrag") and their sections on what stays open.
- `docs/explanation/*.md`, in particular `module-boundaries.md`, `projections.md`, `concurrency.md`; `DEPENDENCIES.md`; `.importlinter`; `pyproject.toml`.
- The execution records' `index.md` files as above; their `progress.md` files hold every ruling.

## How to work

Evidence, not opinion: every row of your report carries a place in a document (`file:line`) and a place in the tree, or says that one of the two does not exist. Where you count something, give the command and its output. Where you judge, mark the sentence as your judgment and keep it apart from the evidence. A finding you cannot show is not a finding; say what you looked at instead.

Do not propose designs for the sub-projects that are not built, and do not grade the work that is. The checkpoint's author decides what follows from your evidence.

## Report

Write the report in German (identifiers and quoted English stay as they are) to:
`/home/jensens/ws/jwk/previously/.claude/worktrees/pruefpunkt-teilprojekt-1/.superpowers/pruefpunkt/bericht-a2-storage-und-offenes.md`

Structure:
- `## Frage 2: die Storage-Schnittstelle` — the counts with commands; a table of the five properties (property, as meant, as built, where decided); what goes around the protocols; growth per stage; your judgment, marked.
- `## Frage 5: §11, §13, §16 Zeile für Zeile` — a table: point, touched (ja/nein), what depends on it or pre-empts it (place), status.
- `## Frage 5: was als entschieden galt und anders gebaut wurde` — a table: determination (place), built (place), status: wie festgelegt | anders | vertagt, reason (place).
- `## Frage 5: Überraschungen von keiner Liste` — one line each with its place.
- `## Was ich nicht klären konnte`
- `## Was ich gelesen und gefahren habe` — files with line ranges, commands.

Then reply with ONLY (under 15 lines): the three to five findings that weigh most, one line each with its place; the count of rows in each table; the report file path.
