## Task 4: Lesen über MCP — `list_obligations`, `list_decisions`

**Files:** `src/previously/mcp_server/render.py`, `read.py`, `server.py`, `tests/test_render.py`, `tests/test_mcp_server.py`.

**Interfaces — Consumes:** Aufgaben 1, 2; `Service.answer`, `record_access`, `Delivered`/`Withheld`, `render_page` (code-facts §7, §8). **Produces:**
```python
# render.py
@dataclass(frozen=True)
class Stated:
    uri: str; kind: str; label: str        # label: Zustand, überfällig, Verantwortung, "n versions", "k proposals" — von Previously
    lines: tuple[str, ...]                 # Text, Akteure, Frist, Grund, Quellen-URIs — fremd, im Zaun
type Item = Shown | WithheldMark | ErasedMark | ErrorMark | Stated
# Werkzeuge
list_obligations(circle: str | None, state: str | None, overdue: bool, proposals: bool, subject: int | None, history: bool, cursor: str | None)
list_decisions(circle: str | None, state: str | None, proposals: bool, subject: int | None, history: bool, cursor: str | None)
# `subject`, nicht `id`: der Name `id` verlangte eine Lint-Unterdrückung (Einheit 4, Ruling R-11 des Plans vom 2026-10-11)
```
Je Eintrag `assertion_verdict` (Planentscheidung 7); zurückgehalten → `WithheldMark` ohne Text und Verweise; `mcp_access` nennt jede gelieferte und zurückgehaltene Feststellung (die Kennung der gewinnenden Fassung) mit ihren Kreisen. `Stated` wird durch `sanitize` und den Zaun gerendert wie `Shown`; die Seitengrenze gilt. Die Beschreibungen sind deklarativ; `INSTRUCTIONS`, der Modul-Docstring und `mcp-tools.md` sagen nicht mehr „only reads" (code-facts §7).

- [ ] **Step 1: Tests, die scheitern:** beide Werkzeuge in beiden Generationen; ein Eintrag mit einer Quelle aus einem Kreis ohne Regel ist für `claude-code` ein Platzhalter, für `local-harness` sichtbar; ein erwähnter `address:`-Akteur aus einem anderen Kreis ändert daran nichts (F §7); `circle`-Filter über Akteure; `history`; Platzhalter ohne Text; `mcp_access` je Eintrag; die Prüfsumme der Werkzeugliste neu (Namensliste und Hex); ein Ergebnis bleibt ein Textblock.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** Policy über die Akteure statt über die Quellen → rot; Platzhalter mit Text → rot; Kontrolle grün.
- [ ] **Step 5:** sechs Tore, Commit.

---

