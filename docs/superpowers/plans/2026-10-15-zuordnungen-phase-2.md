# Zuordnungen, Phase 2: Zuordnung, Chronik einer Klammer, Projektion — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Events und Einheiten lassen sich Klammern zuordnen; die Chronik einer Klammer liest sich auf der Kommandozeile und über MCP; und das Lesen des Graphen kostet nicht mehr das Falten des ganzen Logs.

**Architecture:** `concerns` bleibt eine **deklarierte** Art: das Vokabular lernt `event` als Ausgangspunkt und `*` als Ziel. Eine Beziehung, die an einem Event beginnt, hat dieses Event unter ihren Quellen; so tilgt die Kaskade sie mit der Mail, und die Policy sieht auf die Mail. Eine Projektion `graph` hält je Kennung eine Zusammenfassung, wird beim Lesen nachgezogen und faltet nur die Kennungen neu, die neue Events berühren; Inhalte kopiert sie nicht. Die Chronik einer Klammer liest ihre Menge aus der Projektion und ihre Ordnung aus `p_chronicle`.

**Tech Stack:** Python 3.14, SQLAlchemy Core, PostgreSQL 18, Alembic, `mcp` 2.3, Hypothesis.

**Spec:** `docs/superpowers/specs/2026-10-14-zuordnungen.md` („Z"), lebendig. Phase 2: Z §8, §10. Die Fakten aus dem Code, gemessen am 2026-10-15 auf `0bfb228`: `.superpowers/sdd/2026-10-15-zuordnungen-phase-2/code-facts.md` („CF §n").

**Entscheidungen des Betreuers am 2026-10-15:**
- **Projektion (A):** Tabellen, beim Lesen nachgezogen — immer aktuell, kein Job nötig, Kommandozeile und MCP profitieren.
- **Weitere Fundorte einer Mail: später**, „aber nicht vergessen und nichts verbauen" (Planentscheidung 12).
- **Der Parameter heißt `within`**, auf der Kommandozeile (`--within N`) wie über MCP; `in` ist in Python reserviert, und ein Alias auf einem Parameter eines Werkzeugs scheitert gemessen (CF §11). „Wenn dann konsistent beides."
- **Ein Event am Anfang ist Quelle**; und `concerns` wird **keine eingebaute Art**: „wir müssen aufpassen, nicht inflationär eingebaute Arten einzuführen, sonst führen wir das ganze Deklarative ad absurdum." Eingebaut bleiben die drei, die das Gate liest.

**Ausführung:** subagent-driven, wie Phase 1, mit demselben Zyklenbudget (je Aufgabe eine Fixrunde und eine Nachprüfung; Endprüfung eine Fixwelle). Opus für die Aufgaben 3 und 4 (Projektion, Leser), Sonnet sonst. **Messungen laufen nur gegen eine feste Kopie eines Commits**, nie gegen den Baum, an dem gearbeitet wird (Lehre aus Phase 1).

---

## Was der Plan am Spec entscheidet

1. **`event` und `*` im Vokabular.** Eine Art von Beziehung darf in `from` den Wert `event` nennen (Ausgangspunkt ist ein Event oder Einheiten eines Events, eine Wahrnehmung) und in `to` den Wert `*` (jede Art von Entität). `event` steht nie in `to`; `*` nie in `from`; `*` steht allein. Die Vokabulardatei schreibt beides als Text (`from = ["event"]`, `to = ["*"]`); die Form der Handlung `vocabulary` bekommt keine neuen Schlüssel, nur zwei erlaubte Werte.
2. **`concerns` im Grundvokabular:** `from = ["event"]`, `to = ["*"]`, keine Verhalten, keine Felder, Beschriftungen `de = "betrifft"`, `en = "concerns"`. `apply --base` fügt es auf einem Log aus Phase 1 hinzu (es fehlt dort), ohne sonst etwas zu ändern (F-a).
3. **Ein Event am Anfang ist Quelle.** Für jede Beziehung, deren Anfang ein Event ist: unter `sources` steht ein Eintrag mit diesem Event, dessen Einheiten die Einheiten des Anfangs umfassen (`units: null` umfasst alle). Fehlt er, weist der Schreibweg ab („the event a relation starts at must be among its sources") und `verify` meldet es. Damit tilgt die vorhandene Kaskade die Zuordnung mit der Mail oder mit ihren Einheiten (CF §1, §6), und die Policy entscheidet über die Mail. Die Kommandozeile und MCP setzen den Anfang als Quelle selbst, wenn der Aufrufer ihn nicht nennt.
4. **Die Menge einer Klammer** (Z §8), rein in `core`, `members(bracket, edges) -> Members`:
   - die Klammer und alles, was über `part_of` darunter liegt (transitiv nach unten: ein Vorgang `part_of` ein Projekt gehört zum Projekt); gezählt werden geltende Gewinner, die stehen, wie `Graph.relations()` sie gibt;
   - jede `concerns`-Kante in diese Menge: vom ganzen Event (alle Einheiten) oder von Einheiten;
   - **das Genauere ersetzt das Allgemeine:** hat eine Einheit eigene `concerns`-Kanten, gilt für sie nur, was diese sagen; die Kante ihres Events gilt für sie nicht;
   - Ergebnis: je Event `None` (alle Einheiten) oder die Menge der Einheiten.
5. **Die Projektion `graph`** (Entscheidung A; CF §4, §5, §6):
   - Tabellen (Migration `0006_graph`): `p_graph_version` (`id` PK→`event.id`, `subject`, `kind`, `under` nullable) — eine Zeile je Graph-Fassung und je Ablehnung einer Graph-Fassung (`kind = 'rejection'`, `subject` = die Kennung der abgelehnten Fassung); `p_graph_thread` (`subject` PK→`event.id`, `kind`, `type`, `winner_id`, `level`, `state`, `start_event`, `start_units` int[] nullable, `start_entity`, `to_entity`, `candidates` int[] nullable, `period_start`, `period_end`, `pending`, `objections`, `question` bool) mit Indizes auf `(kind, type)`, `to_entity`, `start_event`. Keine Inhalte, keine Felder, keine Namen: was gezeigt wird, liest der Leser aus dem Log (`events_by_id`) — so hält eine Tilgung, ohne dass die Projektion Inhalt löschen muss.
   - **Nachzug nur der berührten Kennungen:** `GraphProjection.write(batch)` merkt sich je Batch die schmutzigen Kennungen: eine neue Graph-Fassung (ihre Kennung); eine Ablehnung einer Graph-Fassung; eine `redaction`, deren Ziel eine Graph-Fassung ist; ein `approval_class`-Event (alle Kennungen mit einer Fassung `under` einer Klasse desselben Namens). Dann liest es für diese Kennungen die Fassungen aus `p_graph_version`, holt sie mit `events_by_id` aus dem Log (getilgte kommen als `None`), faltet sie mit dem vorhandenen Modell unter `read_classes` und schreibt die Zusammenfassung. Ein `vocabulary`-Event macht nichts schmutzig: was zum Vokabular passt, entscheidet der Leser.
   - **Beim Lesen nachgezogen:** jeder Leser (Kommandozeile, MCP) ruft vor dem Lesen `catch_up(log, store, GRAPH)` in eigener Transaktion; ist nichts neu, kostet das eine Abfrage. Gleichzeitige Nachzüge warten am Zeilenschloss von `projection_state` (CF §4). `previously project` und `redact` ziehen sie wie die anderen nach; ihre Ausgabe bekommt eine Zeile `graph`.
   - **Der Schreibweg bleibt beim Falten** des ganzen Logs (Z §3.4, Messung): er prüft unter dem Tip, und die Projektion hinkt in der Transaktion eines Schreibvorgangs nach. Gemessen kostet das 7 s je Schreibvorgang bei 100 000 Beziehungen; für den Piloten tragbar, und eine Aufgabe für später (Landkarte).
   - **Gleichwertigkeit als Zusicherung:** für beliebige Folgen von Fassungen, Ablehnungen, Freigaben, Tilgungen und Klassen gibt die Projektion nach jedem Nachzug dieselben Gewinner, Zustände und Zähler wie `fold_graph` über das ganze Log — Hypothesis gegen echtes PostgreSQL, auch mit einem Nachzug mitten in der Folge.
6. **Der Leser hat ein eigenes Protokoll** `GraphStore` in `contract/store.py` (CF §4: kein Protokoll liest heute eine Projektion), neben `ProjectionStore`: Abfragen auf `p_graph_thread` (Entitäten nach Art und Zustand; Beziehungen nach Art, Enden, Stichtag; anhängige Fassungen und Einwände; die Kanten für `members`). `build_server` bekommt ihn als Parameter; `PostgresStorage` erfüllt ihn. Die gezählten Methoden im Docstring von `contract/store.py` werden nachgemessen.
7. **`--as-of`** (`relations --as-of`, `entity --history` mit Stichtag) liest weiter das Log und faltet: die Projektion kennt nur den heutigen Stand. Das ist selten und darf langsam sein.
8. **`chronicle --within N`:** die Zeilen von `p_chronicle`, deren `(event_id, seq)` in `members(N)` liegen, in derselben Ordnung und mit denselben Grenzen (`--since`, `--until`, `--limit`). Eine Klammer, die es nicht gibt oder die keine Entität ist: `Error:` mit Exit 2. Die Ausgabezeile bleibt gleich.
9. **`previously(within=N)` über MCP:** zeigt die Events, die in `members(N)` liegen, und von ihnen nur die Einheiten, die dazugehören; `within` geht in die Filter des Cursors (als Text, CF §4) und in den Titel (`chronicle · within 12`). Eine Klammer, die der Client nicht sehen darf oder die es nicht gibt: derselbe Satz. Die Policy entscheidet je Event wie bisher; `within` findet nur, es gibt nichts frei (Z §10.4).
10. **Der Kopf** zählt die Einwände aus `p_graph_thread.objections > 0` und prüft die Sichtbarkeit nur für diese Kennungen; `list_entities`, `list_triage` und `previously status` lesen aus der Projektion. Jeder MCP-Aufruf zieht zuerst nach.
11. **`verify`** bleibt beim Falten des Logs, und `previously project --check` vergleicht die Projektion mit der Faltung und meldet jede Abweichung (eine Zeile je Kennung) — die Projektion ist wegwerfbar, ihr Fehler darf nicht still bleiben.
12. **Nicht verbauen — weitere Fundorte einer Mail** (Z §8, später): eine Zuordnung, die die Aufnahme schreibt, ist eine gewöhnliche `concerns`-Beziehung mit dem Event als Anfang und Quelle; wer sie schreibt (Betreiber über eine Ordner-Zuordnung, oder eine Regel) und auf welcher Stufe, bleibt offen. Nichts in Phase 2 nimmt an, dass nur Menschen oder Modelle `concerns` schreiben; die Landkarte bekommt den Punkt mit diesem Satz.

## Global Constraints

- Sprache nach `CLAUDE.md`: Code, Kommentare, Meldungen, Testnamen, Seiten, Handoff englisch; Plan, Landkarte deutsch.
- Die sechs Tore, jedes für sich, vor jeder Fertigmeldung:
  ```
  uv run ruff check .
  uv run ruff format --check .
  uv run pyright
  uv run lint-imports
  uv run pytest --cov --cov-report=term-missing
  make -C docs html && make -C docs vale && make -C docs linkcheck
  ```
- `uv run pip-audit --skip-editable` ohne Befund vor dem PR.
- Kein `# type: ignore`; keine neue Lint-Unterdrückung; `cast` statt Zwischenannotation; kein privater Name aus einem Test.
- Kein Mock für Zeit, Datenbank oder Zufall; gegen echtes PostgreSQL.
- `core` importiert kein SQL; neue Abfragen nur hinter `contract.store`. Kein Vertrag in `.importlinter` wird erweitert.
- **Keine neue eingebaute Art.** Das Gate (`core/decide.py`) bleibt unberührt; eine Zuordnung gibt in Phase 2 nichts frei.
- **Kein Inhalt in der Projektion**, und kein Text in `mcp_access`, in einer Fehlermeldung, in einem Platzhalter.
- Jede Zusicherung bekommt einen Test, gemessen rot bei zurückgenommener Zusicherung, mit grüner Kontrolle.
- Ein Kommentar ist eine Behauptung: `T201` in `pyproject.toml`, die Zählungen in `contract/store.py`, „eight tables" auf `database-schema.md`, „fifteen tools" — nachmessen, was sich bewegt.
- Typed-out output (`project`-Zeilen, `migrate`-Zeilen mit `0006_graph`, Tutorial) wird aus echten Läufen neu getippt.
- Commits: Dateien namentlich, Trailer `Assisted-By: <Modell> <noreply@anthropic.com>`, nie `Co-Authored-By`.
- **Wortlaute**, vertraglich:

  | Wo | Wortlaut |
  |---|---|
  | Kommandozeile | `previously chronicle --within N`; `previously relate concerns --from-event E[:SEQ,SEQ] --to N` |
  | MCP | Parameter `within` am Werkzeug `previously`; Titel `chronicle · within N` |
  | Ausgabe von `project` | eine Zeile `graph` mit `_describe` wie die anderen |
  | Migration | `0006_graph` |
  | Abweisung | `the event a relation starts at must be among its sources` |

## Review Focus

1. **Eine Zuordnung überlebt ihre Mail:** die Mail oder ihre Einheit wird getilgt → die Zuordnung fällt mit, die Projektion zieht nach, `chronicle --within` zeigt nichts mehr davon, `verify` ist sauber. → Aufgaben 2 und 3.
2. **Die Projektion weicht still ab:** nach Tilgung einer Fassung, nach Rückzug einer Klasse mit `demote`, nach einer Ablehnung — Gewinner, Zustand und Zähler stimmen nicht mehr mit der Faltung. → Aufgabe 3 (Gleichwertigkeit), Aufgabe 4 (`project --check`).
3. **`within` gibt frei:** ein Client sieht über `within` eine Einheit, die er ohne nicht sähe, oder erfährt über eine leere Seite, dass eine verborgene Klammer existiert. → Aufgabe 5.
4. **Das Genauere ersetzt das Allgemeine falsch:** eine Einheit mit eigener Kante zu einer anderen Klammer erscheint trotzdem in der Chronik der Klammer ihres Events; oder eine Einheit ohne eigene Kante fällt aus der Chronik ihres Events. → Aufgabe 2.
5. **Zwei Leser ziehen gleichzeitig nach** (zwei MCP-Aufrufe, ein CronJob): keiner sieht einen halben Stand, keiner schreibt doppelt. → Aufgabe 3.

---

## Dateistruktur

| Datei | Aufgabe | Verantwortung |
|---|---|---|
| `src/previously/core/vocabulary.py`, `src/previously/vocabulary.toml` | 1 | `event` und `*`; `concerns` im Grundvokabular |
| `src/previously/core/graph.py`, `core/graph_write.py`, `core/verify.py` | 1, 2 | Anfang als Ereignis, Quelle-Regel, `members` |
| `src/previously/core/projection/graph.py` (neu), `core/projection/__init__.py` | 3 | die Projektion `graph` |
| `src/previously/storage/schema.py`, `migrations/versions/0006_graph.py` (neu), `storage/postgres.py`, `contract/rows.py`, `contract/store.py` | 3, 4 | Tabellen, Migration, `ProjectionStore`-Methoden, `GraphStore` |
| `src/previously/cli.py` | 2, 4, 5 | `relate concerns --from-event`, Leser aus der Projektion, `project --check`, `chronicle --within` |
| `src/previously/mcp_server/*` | 2, 4, 5 | `write_relation` mit Event-Anfang, Leser aus der Projektion, `within` |
| Tests | 1–5 | |
| Seiten, Handoff, Landkarte | 6 | |

---

## Task 1: Vokabular — `event` als Anfang, `*` als Ziel, `concerns`

**Files:** `core/vocabulary.py`, `vocabulary.toml`, `core/graph.py` (`conformance_problem`), `tests/test_vocabulary.py`, `tests/test_graph.py`, `docs/reference/vocabulary.md`.

**Interfaces — Produces:** `EVENT_START: Final = "event"`, `ANY_ENTITY: Final = "*"` in `core/vocabulary.py`; `KindSpec.from_`/`to` dürfen sie enthalten (Planentscheidung 1); `conformance_problem` lässt einen Event-Anfang zu, wenn die Art `event` in `from_` nennt, und ein Ziel jeder Art bei `*` — und weist sonst wie bisher ab.

- [ ] **Step 1: Tests, die scheitern:** Form und Datei mit `event` und `*` hin und zurück; `event` in `to`, `*` in `from`, `*` mit einer anderen Art zusammen → abgewiesen mit Satz; `concerns` im Grundvokabular; `apply --base` auf einem Log aus Phase 1 schreibt genau `concerns` und meldet sonst nichts (F-a); `conformance_problem`: Event-Anfang bei `concerns` passt, bei `holds` nicht; Ziel `*` nimmt jede Art, `retracted` eingeschlossen nicht neu.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutation:** `*` nimmt nur Arten aus `to` → rot; Kontrolle grün.
- [ ] **Step 5:** sechs Tore, Commit.

---

## Task 2: Zuordnung schreiben und ihre Menge — Quelle-Regel, `members`, Kommandozeile und MCP

**Files:** `core/graph.py`, `core/graph_write.py`, `core/verify.py`, `cli.py` (`relate`), `mcp_server/server.py` (`write_relation`), Tests, `docs/reference/cli.md`, `docs/reference/mcp-tools.md`.

**Interfaces — Produces:**
```python
@dataclass(frozen=True)
class Members:
    events: Mapping[int, frozenset[int] | None]     # Event → None (alle Einheiten) oder die Einheiten
    brackets: frozenset[int]                         # die Klammer und alles darunter
    def holds(self, event_id: int, seq: int) -> bool: ...
def members(graph: Graph, bracket: int) -> Members: ...            # Planentscheidung 4; rein
START_NOT_A_SOURCE: Final = "the event a relation starts at must be among its sources"
```
Der Schreibweg und `verify` prüfen Planentscheidung 3; die Kommandozeile (`relate concerns --from-event E[:SEQ,SEQ] --to N [--source …]`) und `write_relation` (Element `from: {"event": int, "units": [int]|null}`) setzen den Anfang als Quelle, wenn er fehlt. Ein Modell schreibt `concerns` über MCP wie jede Beziehung: Stufe nach Klasse, sonst offen; eine Rückfrage mit Kandidaten ist erlaubt. `Graph.relations()` gibt Kanten mit Event-Anfang zurück; `reaches` und `members` trennen sie sauber (eine Kante vom Event ist keine Kante zwischen Entitäten).

- [ ] **Step 1: Tests, die scheitern:** Quelle-Regel (fehlt → abgewiesen, `verify` meldet es; Einheiten nicht umfasst → abgewiesen; `units: null` umfasst alle); **Kaskade** (Review Focus 1: Mail getilgt → Zuordnung getilgt; eine genannte Einheit getilgt → die Zuordnung dieser Einheit getilgt, die des ganzen Events steht, sofern sie die Einheit nicht nennt — wie F §8); `members` (Hypothesis über Bäume von `part_of` und Kanten vom Event und von Einheiten: eine Einheit ist Mitglied genau dann, wenn ihre eigenen Kanten — oder, ohne eigene, die ihres Events — in die Menge der Klammer zeigen; Review Focus 4); die Kommandozeile und MCP schreiben eine Zuordnung, eine Rückfrage, einen Widerruf; Markus' Mail (Z §8): Einheiten über XZ zum Projekt, der Nachsatz zum Sommerfest.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** Quelle-Regel entfernt → rot; „das Genauere ersetzt" entfernt → Hypothesis rot; `part_of` nach oben statt nach unten → rot; Kontrolle grün.
- [ ] **Step 5:** sechs Tore, Commit.

---

## Task 3: Die Projektion `graph`

**Files:** `storage/schema.py`, `migrations/versions/0006_graph.py` (neu), `contract/rows.py`, `contract/store.py` (`ProjectionStore`), `storage/postgres.py` (Methoden, `_PROJECTION_TABLES` für zwei Tabellen eines Namens), `core/projection/graph.py` (neu), `core/projection/__init__.py`, `tests/test_schema.py`, `tests/test_projection_worker.py`, `tests/test_projection_graph.py` (neu), Tests mit getippter `project`-/`migrate`-Ausgabe, `docs/reference/database-schema.md`, `docs/explanation/projections.md`.

**Interfaces — Produces:** `GraphThreadRow` und `GraphVersionRow` in `contract/rows.py` (Planentscheidung 5); `ProjectionStore`-Methoden `insert_graph_versions`, `graph_version_ids(conn, subjects) -> dict[int, list[int]]`, `class_subjects(conn, under_ids) -> set[int]`, `upsert_graph_threads`, `delete_graph_threads`; `GRAPH = GraphProjection(name="graph", version=1)` in `PROJECTIONS` (nach `chronicle`, `source-stats`). `truncate_projection("graph")` leert beide Tabellen.

- [ ] **Step 1: Tests, die scheitern:**
  - Schema und Migration gleich (die vorhandenen Tests in `test_schema.py` decken es mit; Text von `test_the_projection_tables_exist` nachziehen);
  - **Gleichwertigkeit** (Review Focus 2): Hypothesis über Folgen von Fassungen aller Stufen, Ablehnungen, Freigaben, Tilgungen (auch einer Quelle, die per Kaskade die Aussage nimmt), Klassen (Rückzug mit und ohne `demote`), mit Nachzügen an zufälligen Stellen — danach ist jede Zeile von `p_graph_thread` gleich der Zusammenfassung von `fold_graph` über das ganze Log; inkrementell gleich neu gebaut (`test_incremental_equals_rebuilt` erweitert);
  - **gleichzeitig** (Review Focus 5): zwei Verbindungen ziehen nach, jede sieht einen ganzen Stand, keine Zeile doppelt;
  - kein Inhalt in den Tabellen (die Spalten sind die von Planentscheidung 5, ein Test hält die Spaltennamen).
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** eine Tilgung macht ihre Kennung nicht schmutzig → Gleichwertigkeit rot; ein Klassenrückzug macht nichts schmutzig → rot; Kontrolle grün.
- [ ] **Step 5:** getippte `project`-Ausgaben und `migrate`-Zeilen aus echten Läufen nachziehen; sechs Tore, Commit.

---

## Task 4: Lesen aus der Projektion — `GraphStore`, Kommandozeile, MCP, `project --check`

**Files:** `contract/store.py` (`GraphStore`), `storage/postgres.py`, `core/graph_read.py` (neu: die Leser über `GraphStore` mit Nachzug), `cli.py` (`entities`, `relations` ohne `--as-of`, `entity N`, `triage`, `status`, `project --check`), `mcp_server/server.py`, `read.py` (`list_entities`, `list_triage`, Kopf), Tests, `docs/reference/cli.md`, `docs/reference/mcp-tools.md`, `contract/store.py`-Docstring.

**Interfaces — Produces:** `GraphStore[Conn]` mit Lese-Abfragen auf `p_graph_thread` (Planentscheidung 6); `read_brackets[Conn](log, projection, graph_store, conn, bracket) -> Members` (Nachzug, dann `members` aus den Kanten der Projektion); `build_server(..., graph: GraphStore[Conn] | None)`; `previously project --check` (Planentscheidung 11). `--as-of` liest weiter das Log (Planentscheidung 7).

- [ ] **Step 1: Tests, die scheitern:** jede Liste gleich vorher (die Tests aus Phase 1 bleiben grün, unverändert); der Kopf zählt dieselben Einwände; **ein Aufruf liest das Log nicht mehr ganz** (der zählende Test aus Phase 1, `test_a_call_folds_the_graph_once_for_its_header_and_its_body`, wird ersetzt durch einen, der null vollständige Lesungen von `assertion` zählt, wenn nichts neu ist); `project --check` sauber nach jeder Folge, und eine von Hand verfälschte Zeile wird gemeldet.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** ein Leser ohne Nachzug → ein Test, der zwischen zwei Aufrufen schreibt, wird rot; `--check` vergleicht nichts → rot; Kontrolle grün.
- [ ] **Step 5:** Zählungen in `contract/store.py` nachmessen; sechs Tore, Commit.

---

## Task 5: Die Chronik einer Klammer — `chronicle --within`, `previously(within=)`

**Files:** `cli.py` (`chronicle`), `storage/postgres.py` (`read_chronicle` mit Menge), `mcp_server/read.py`, `server.py` (`previously`), Tests, `docs/reference/cli.md`, `docs/reference/mcp-tools.md` (`TOOLS_SHA256` neu), `docs/how-to/keep-a-club-and-its-offices.md` oder eine neue Anleitung zum Zuordnen.

**Interfaces — Consumes:** `read_brackets`, `Members.holds`. **Produces:** `--within N` (Planentscheidung 8), `within` (Planentscheidung 9).

- [ ] **Step 1: Tests, die scheitern:** die Chronik des Sommerfests zeigt die zugeordneten Einheiten, eine Stufe höher den Verein (Markus, Z §17 Punkt 2); die Grenzen `--since`/`--until`/`--limit` gelten; eine unbekannte Klammer → `Error:` Exit 2; über MCP nur die Einheiten der Klammer, Cursor mit `within`, Titel; **Review Focus 3:** ein Event, das der Client nicht sehen darf, bleibt Platzhalter, auch mit `within`; eine Klammer, die der Client nicht sehen darf, gibt denselben Satz wie eine, die es nicht gibt; `within` lässt keine Einheit durch, die die Policy zurückhält.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutation:** `within` vor der Policy statt nach ihr → rot; Kontrolle grün.
- [ ] **Step 5:** sechs Tore, Commit.

---

## Task 6: Doku, Handoff, Landkarte

- [ ] **Explanation** (`graph.md`): warum `concerns` deklariert und nicht eingebaut ist; warum ein Event am Anfang Quelle ist; die Menge einer Klammer und „das Genauere ersetzt"; die Projektion: was sie hält (keinen Inhalt), wie sie nachzieht, warum der Schreibweg noch faltet, `project --check`; `projections.md` um `graph`.
- [ ] **How-to:** Mails und Einheiten zuordnen und die Chronik einer Klammer lesen (Markus).
- [ ] **Handoff** (englisch): **Migration `0006_graph`**, `previously migrate` zuerst; dann `vocabulary apply --base` (fügt `concerns` hinzu); `previously project` baut die Projektion beim ersten Lauf, oder der erste Leser tut es; Prüfungen: `migrate` meldet `0006_graph`, `vocabulary show` zeigt `concerns`, `project` zeigt eine Zeile `graph`, `chronicle --within` antwortet. Zugestellt erst, wenn `manifest` grün ist.
- [ ] **Landkarte:** Phase 2 gebaut; Fundorte als offener Punkt mit Planentscheidung 12; der Schreibweg, der noch faltet; zählen vorher/nachher.
- [ ] Sechs Tore, `pip-audit`, Tutorial-Block aus einem grünen Lauf, Commits.

---

## Nach Aufgabe 6

1. Endprüfung über den Zweig, eine Fixwelle, eine Nachprüfung. **Messung auf einer festen Kopie** bei 10 000 und 100 000 Beziehungen: `entities`, `relations --at`, `chronicle --within`, MCP `whoami` und `list_entities`, ein Schreibvorgang, `verify`, `project` (erster Bau und Nachzug).
2. Ausführungsprotokoll nach `docs/superpowers/sdd/2026-10-15-zuordnungen-phase-2/`.
3. Push und PR.

## Selbstprüfung dieses Plans

- **Spec-Abdeckung, Phase 2:** Z §8 (concerns, Einheit, keine Partition, transitiv, das Genauere, Markus) → 1, 2; Anhänge → nur Planentscheidung 3 (ein Anhang als Event wird gleich behandelt, wenn es ihn gibt); Fundorte → Planentscheidung 12, Landkarte; Zusammenhang aus dem Graphen → Einheit 6, nicht hier; §10.1 (Projektion) → 3, 4; §10.2 (`--within`) → 5; §10.3 (`within`) → 5; §10.4 → Global Constraints, Review Focus 3; §15 Punkte 9–11 → 2, 5; §17 Punkt 2 → 5.
- **Abweichung vom Spec, bewusst:** der Parameter heißt `within` statt `in` (Entscheidung des Betreuers); `--as-of` und der Schreibweg falten weiter (Planentscheidungen 5, 7).
- **Platzhalter:** keine; die Meldungen legen die Umsetzer fest, die Seiten zitieren sie.
- **Namen:** `EVENT_START`, `ANY_ENTITY`, `Members`, `members`, `START_NOT_A_SOURCE`, `GraphProjection`, `GRAPH`, `GraphThreadRow`, `GraphVersionRow`, `GraphStore`, `read_brackets` — überall gleich.
