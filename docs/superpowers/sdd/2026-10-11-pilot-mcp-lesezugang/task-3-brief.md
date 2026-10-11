## Task 3: Das Zugriffsprotokoll

**Files:** `core/access.py` (neu), `core/action.py`, `core/verify.py`, `core/gaps.py`, `cli.py` (`access`), `tests/test_access.py` (neu), `tests/test_verify.py`, `tests/test_cli.py`, `docs/reference/cli.md`.

**Interfaces — Consumes:** `append_action` (Einheit 3), `gaps`. **Produces:**
```python
# core/action.py: MCP_ACCESS = "mcp_access" in KNOWN_ACTIONS
# core/access.py
@dataclass(frozen=True)
class Withheld: event: int; reason_code: str; circles: tuple[str, ...]; reason: str   # reason_code: "no_rule" | "rule"
@dataclass(frozen=True)
class Delivered: event: int; units: tuple[int, ...]
@dataclass(frozen=True)
class Access:
    client: str; policy_ids: Mapping[str, object]   # {"client": id, "processor": id, "rules": [ids]}
    kind: str; name: str; arguments: Mapping[str, object]   # kind: "tool" | "resource" | "prompt"
    delivered: tuple[Delivered, ...]; withheld: tuple[Withheld, ...]
    outcome: str; era: str | None                   # outcome: "ok" | "error"
def record_access[Conn](log: LogStore[Conn], access: Access, *, recorded_at: datetime) -> int: ...
@dataclass(frozen=True)
class AccessRow: id: int; recorded_at: datetime; access: Access
def read_access[Conn](log: LogStore[Conn], conn: Conn, *, client: str | None, circle: str | None,
                      since: datetime | None) -> list[AccessRow]: ...
```
Nutzlast nach K §5 mit den Feldern oben. `verify` prüft die Form (bekannte Felder, `outcome` aus der Liste, `delivered`/`withheld` als Listen von Objekten mit `event`). `gaps` zählt zusätzlich die `withheld` mit `reason_code: no_rule`, getrennt nach Herkunft (`gate`, `mcp`). `previously access [--client] [--circle] [--since]` druckt je Aufruf Zeit, Client, Werkzeug, gelieferte und zurückgehaltene Event-IDs mit Grund.

- [ ] **Step 1: Tests, die scheitern:** schreiben, lesen, filtern; die Nutzlast enthält keine Zeichenkette einer Einheit eines genannten Events (rekursiv, wie in `test_gate.py`); `verify` findet eine kaputte Form; `gaps` zählt MCP-Lücken getrennt; CLI-Ausgabe.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** `gaps` ignoriert `mcp_access` → rot; die Formprüfung entfällt → rot; Kontrolle grün.
- [ ] **Step 5:** `cli.md`, sechs Tore, Commit.

---

