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

