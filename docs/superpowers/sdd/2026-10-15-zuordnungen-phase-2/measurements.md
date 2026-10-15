# Phase 2 graph core: performance measurements

Date: 2026-10-15. Commit: 22b3dec (fixed detached copy, `uv sync --locked --all-extras --all-groups`).
Machine: 11th Gen Intel(R) Core(TM) i7-11370H @ 3.30GHz, 8 threads, 62 GB; PostgreSQL 18 in testcontainers (`tests/database.py` `postgres()`, fsync off), migrated as `tests/conftest.py` (alembic head, 0006_graph).
Median of three runs; MCP: median of three calls after one dropped warm-up call, in-process `Client(build_server(storage, stdio_client="local-harness", graph=storage, projections=storage))`.
CLI rows run `cli.main` in-process (no interpreter start) unless marked "as a process". No run exceeded 10 minutes, so all are three runs.

## Data
Built as phase 1 (`../measure/common.py`, copied and extended in `common.py`): about one entity per two relations (10 % organization, 20 % post, 20 % project, 50 % person),
`part_of` tree (fan-out 3) over the projects, `post_in` per post, the rest `holds` with periods (30 % open-ended); operator, direct, appended straight with `core.chain.prepare/link` and `insert_event` (chunks of 5,000); base vocabulary first, local provider, client `local-harness`.
Added: mails = max(300, N/10) (1,000 and 10,000, not phase 1's 300, so the chronicle has something to select); `concerns` assignments, one per two mails (500 and 5,000), 30 % at unit level, 40 % into three big brackets
(the root project and its first two children, subtrees = whole tree and a third each), the rest to random projects; one extra project "Empty bracket" with nothing.
Sizes: 10,000 rel. = 5001 entities, 16513 events; 100,000 rel. = 50001 entities, 165013 events (relations excluding concerns).
Build time 8 s and 79 s.
`previously verify`: clean before and after all writes at both sizes (0 findings, exit 0; `core.verify.verify` also 0 findings). Verify ran before any projection existed and before the writes.

## Results (seconds, median of three)
| measurement | 10,000 rel. | 100,000 rel. |
|---|---|---|
| verify | 3.571 | 129.938 |
| project first build | 3.544 | 34.560 |
| project catch-up, nothing new | 0.022 | 0.023 |
| project catch-up after one write | 0.038 | 0.040 |
| CLI entities | 0.304 | 3.508 |
| CLI relations --at 2019-03-01 | 0.694 | 6.777 |
| CLI chronicle --within big (root project) | 0.040 | 0.143 |
| CLI chronicle --within big (child project) | 0.044 | 0.133 |
| CLI chronicle --within empty | 0.042 | 0.135 |
| CLI entities, as a process (incl. interpreter start) | 0.865 | 3.811 |
| CLI chronicle --within big, as a process | 0.589 | 0.686 |
| MCP whoami  | 0.012 | 0.019 |
| MCP list_entities  | 0.691 | 4.974 |
| MCP list_triage  | 0.015 | 0.033 |
| MCP previously(within=big bracket) | 1.745 | 17.516 |
| MCP previously(within=empty bracket) | 0.025 | 0.135 |
| write_claims, one relation | 0.542 | 6.937 |
| project --check | 1.023 | 10.633 |

Phase 1 for comparison (2026-10-14, no projection): read_graph/list 0.47 / 7.35; MCP whoami 0.52 / 7.69; list_entities 1.72 / 23.7; one write 0.47 / 7.34; verify 2.77 / 135.
Outputs checked: `entities` printed 5,001 / 50,001 lines; `relations --at` 4,971 / 50,124; chronicle `--within` big printed 50 lines (truncated, limit 50), the empty bracket 0; MCP calls returned no error; MCP `list_entities` and `previously` return one page (about 1,300-1,500 lines).
Raw runs in `results_10000.json`, `results_100000.json`, log `run100k.log`.
