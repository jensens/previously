You are taking one measurement for a checkpoint ("Prüfpunkt") in the project "Previously", an append-only event log for project histories (Python 3.14, SQLAlchemy Core, PostgreSQL, AGPL). The project's architecture record asks, before the remaining sub-projects are planned: **"Was hat die Projektionsmechanik wirklich gekostet — Reprojektionsdauer über echte Datenmengen?"** Nobody has measured it. You do. You change nothing in the repository.

Work in the git worktree `/home/jensens/ws/jwk/previously/.claude/worktrees/pruefpunkt-teilprojekt-1`; run `uv run …` from there so that the project's own environment is used (never `--isolated`, or you measure a different project). Never touch the parent checkout. Scripts and scratch files go to `/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/messung/`; nothing is written into the worktree except your report (below). Do not dispatch subagents.

## What "real volumes" means here

The design states the expected volume (`docs/superpowers/specs/2026-10-01-previously-design.md`, lines 1420 to 1425): about 275,000 mails over five years, "einstellige Millionen Events", on one machine. So the sizes that matter are 10,000 (a pilot), 100,000, and 1,000,000 events.

## What to measure

Against a scratch PostgreSQL the way the tutorial sets one up (`docs/tutorials/record-your-first-event.md`: a `postgres:17` container, schema by `alembic upgrade head`; pick a free port, a container name of your own, and remove the container at the end). One container, default configuration; note the machine (CPU model, cores, RAM, disk type as far as `lscpu`, `free -h` and `lsblk -d -o NAME,ROTA` tell).

At each size — 10,000, 100,000, and 1,000,000 if loading it takes under about fifteen minutes; if not, stop at the largest size you can load in that time and say so:

1. **Loading**: events appended through the project's own `append` (`src/previously/core/append.py`), in batches — find out from the code what a batch is and what it costs, and say which batch size you used and why. Events should look like the real thing rather than like a benchmark: a few sources, text of mail-like length split into units by the project's own `split_plaintext`, with some variation in size. Report events per second and the number of unit rows.
2. **Rebuilding both projections from nothing**: the worker's catch-up over the whole log (`src/previously/core/projection/worker.py`, what `previously project` runs). Wall-clock time, events per second, and the peak resident memory of the process (`/usr/bin/time -v` or `resource.getrusage`) — the architecture record demands that a rebuild "nichts in den Speicher ziehen" darf, so memory at 1,000,000 against memory at 10,000 is the number that says whether that holds.
3. **Catching up**: after a rebuild, append 1,000 more events and time the next catch-up. This is the everyday case.
4. **The chain check**: `examine` over the whole log (`src/previously/core/verify.py`, what `previously verify` runs), wall-clock time and peak memory. Since the external anchor shipped, a scheduled routine runs this check on every anchoring, and it reads in one `REPEATABLE READ` snapshot held for the whole pass — so its duration at 1,000,000 events is an operations number: say how long that transaction stays open.
5. **Reading**: `previously chronicle` with its default limit, and with a time window in the middle of the log; `previously stats`. Time each once the projections are current.

Each timing at least three times where it is cheap enough, with all the values reported, not only a mean. If two runs differ by more than a quarter, say so and say what you think moved.

## What to be careful about

- Measure the thing, not its setup: no container start, no `uv` start-up, no schema creation inside a timed span. For the command-line readings, the process start is part of what a user waits for — report it, and say how much of it is start-up (`uv run previously --help` timed gives a floor).
- The projections' cost has two parts the worker's code keeps apart: deriving rows (pure Python) and writing them. If you can tell from the code or a profile where the time goes, say so with the evidence; do not guess.
- A number without its command is not a measurement. The report carries each script, or its path and the exact command line, and the raw output.
- If something fails at a size — a timeout, memory, an error from the database — that is a finding: report it with the output instead of working around it.
- Do not tune PostgreSQL and do not change the project's code to make it faster. If you see where the time goes and what would change it, say so in a section of its own, as an observation.

## Report

Write the report in German (identifiers, commands and output stay as they are) to:
`/home/jensens/ws/jwk/previously/.claude/worktrees/pruefpunkt-teilprojekt-1/.superpowers/pruefpunkt/bericht-c-messung.md`

Structure:
- `## Maschine und Aufbau`
- `## Ergebnisse` — one table: size, loading (events/s), unit rows, rebuild (s, events/s, peak RSS), catch-up of 1,000 (s), chain check (s, peak RSS), each reading (s).
- `## Wie die Kosten wachsen` — linear or not, from the three sizes; what a rebuild and a chain check would take at 5,000,000 if the growth you measured continues, marked as an extrapolation.
- `## Wo die Zeit hingeht` — only what you can show.
- `## Beobachtungen` — what you noticed and did not act on.
- `## Skripte und Rohausgaben`

Then reply with ONLY (under 15 lines): the table's row for the largest size you reached; whether memory stayed flat across sizes; the one or two observations that weigh most; the report file path. Confirm that the container is removed.
