# Phase 1 graph core: performance measurements

Date: 2026-10-14. Machine: 11th Gen Intel Core i7-11370H @ 3.30 GHz (laptop), Linux 7.0, PostgreSQL 18 in testcontainers
(`tests/database.py` `postgres()`, fsync off), migrations run as in `tests/conftest.py`.
Median of three runs unless marked. The 100,000 figures and the 10,000 chain were re-taken from a fixed checkout (detached 9967268);
the 2,000 and 10,000 relation figures come from the first run on the moving worktree (core paths unchanged; MCP at those sizes is from that run).

## Data
Scripts (in this directory): `common.py` (builder), `measure_lib.py`/`measure_main.py` (lists, write, verify, MCP; sizes as arguments),
`fixed_100k.py` (100,000 case from the fixed tree), `verify_edges.py` (part_of chain/tree), run with `MEASURE_TREE=<tree> uv run python <script>`.
Log: 300 mail observations, base vocabulary, a local provider and client `local-harness`.
Entities about one per two relations: 10 % organization, 20 % post, 20 % project, 50 % person.
Relations: a `part_of` tree (fan-out 3) over the projects (roots to one organization), `post_in` per post, the rest `holds` person to post
with periods (30 % open-ended), all operator/direct with a mail source.
Appended directly with `core.chain.prepare/link` and `insert_event` (chunks of 5,000), not through `write_claims`.
Obligations: 1,000 operator obligations appended the same way. Objections: 20 model entity claims written through `write_claims` against direct entities (all 20 pending).
MCP: in-process `Client(build_server(storage, stdio_client="local-harness"))`, `call_tool` timed inside an open session, first call dropped as warm-up, median of the next three.
MCP "claims" = entities + relations, i.e. 3,000 / 15,000 / 150,000 here (not exactly 1k/10k/100k).

## Lists and write (seconds)
| measurement | 2,000 rel. | 10,000 rel. | 100,000 rel. |
|---|---|---|---|
| read_graph only | 0.081 | 0.473 | 7.35 |
| read_graph + entities() | 0.082 | 0.485 | 7.25 (first run) |
| read_graph + relations(at=2019-03-01) | 0.082 | 0.478 | 7.41 (first run) |
| CLI `entities` | 0.104 | 0.533 | 7.59 (first run) |
| CLI `relations --at 2019-03-01` | 0.105 | 0.542 | 7.50 (first run) |
| write_claims, one holds relation | 0.085 | 0.470 | 7.34 (first run) |
| write_claims, one part_of edge | 0.087 | 0.487 | 6.98 (first run) |

With 1,000 obligations present: 10,000 rel. read_graph 0.484, entities 0.472, relations(at) 0.543, CLI entities 0.530, CLI relations 0.532, write 0.482 / 0.476;
100,000 rel. (first run): read_graph 6.28, entities 7.21, relations(at) 6.99, CLI entities 7.04; 2,000 rel.: 0.092 / 0.098 / 0.100 / 0.119 / 0.122 / 0.097 / 0.098.
(The 100,000 list/write rows are from the first run on the moving tree; read_graph re-taken on the fixed tree: 7.35 s, runs 7.35 / 7.20 / 7.56.)

## verify, whole log (seconds)
| log | 2,000 rel. | 10,000 rel. | 100,000 rel. |
|---|---|---|---|
| no obligations | 0.625 | 2.77 | 125.8 (first run), 135.2 fixed tree (single run) |
| with 1,000 obligations | 0.703 | 2.90 | not rerun at 100,000 |

Findings: none in every run (before and after all writes and obligations, all sizes).

## verify over part_of edges only (seconds, log of K projects plus K edges)
| K | chain | balanced binary tree |
|---|---|---|
| 1,000 | 0.84 | 0.78 |
| 2,000 | 2.34 | 2.10 |
| 5,000 | 14.84 | 13.05 |
| 10,000 | 78.6 (single run, fixed tree) | not measured |
Findings: none. Growth is clearly more than linear (2,000 to 5,000: x6.3; 5,000 to 10,000: x5.3), and the tree is only about 10 % faster than the chain.

## MCP header cost (seconds, local-harness client)
| call | 3,000 claims (2k rel.) | 15,000 claims (10k rel.) | 150,000 claims (100k rel., fixed tree) |
|---|---|---|---|
| whoami, 0 objections | 0.097 | 0.518 | 7.69 |
| whoami, 20 objections | 0.102 | 0.511 | 7.33 |
| list_entities, 0 objections | 0.276 | 1.718 | 23.7 |
| list_entities, 20 objections | 0.288 | 1.725 | 24.2 |
Header said "20 objections pending" where expected. Earlier figures for comparison: whoami 53 ms at 1,000 entities, 153 ms at 5,000.
