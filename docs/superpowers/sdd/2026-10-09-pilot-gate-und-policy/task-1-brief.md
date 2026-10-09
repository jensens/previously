## Task 1: Handlungen — gemeinsamer Schreibweg, bekannte Namen, die Chronik zeigt Wahrnehmungen

**Files:** `core/action.py` (neu), `core/redact.py`, `core/verify.py`, `core/projection/chronicle.py`, `tests/test_action.py` (neu), `tests/test_verify.py`, `tests/test_chronicle.py`, `docs/explanation/projections.md`.

**Interfaces — Produces:**
```python
# core/action.py
REDACTION = "redaction"; POLICY = "policy"; MODEL_CALL = "model_call"
KNOWN_ACTIONS: frozenset[str] = frozenset({REDACTION, POLICY, MODEL_CALL})

def write_action[Conn](log: LogStore[Conn], conn: Conn, payload: Mapping[str, object],
                       units: Sequence[RawUnit], *, recorded_at: datetime) -> int: ...
    # auf der Spitze, in der Transaktion des Aufrufers; occurred_at = recorded_at; kein Schlüssel

def append_action[Conn](log: LogStore[Conn], payload: Mapping[str, object],
                        units: Sequence[RawUnit], *, recorded_at: datetime) -> int: ...
    # eigene Transaktion, wiederholt bei ChainPositionTaken wie redact._retrying
```

`redact._write` wird `write_action(..., units=())`; `REDACTION` zieht von
`core/redaction.py` nach `core/action.py` um, `redaction.py` importiert es.

- [ ] **Step 1: Tests, die scheitern:**
  - `test_action.py`: `append_action` schreibt ein Event der Art `action` ohne Quellschlüssel, mit `occurred_at == recorded_at`, mit Einheiten, die `units_by_event` liest; `verify` grün danach.
  - `test_verify.py`: eine Handlung mit `action: "teleport"` (über `append_action`) ist ein Befund `unknown action "teleport"`; eine Handlung mit `policy` oder `model_call` ist keiner (die Form prüfen Aufgaben 2 und 5).
  - `test_chronicle.py`: eine Handlung mit Einheiten erscheint nicht in der Chronik; eine Wahrnehmung schon; nach dem Wechsel auf Version 3 baut `project` neu, und die Zeilen sind dieselben wie bei einem frischen Aufbau.
- [ ] **Step 2: rot.**
- [ ] **Step 3: umsetzen.** In `chronicle.derive`: `if event.kind != "observation": continue` vor den Einheiten; `version = 3` mit einem Kommentar, warum. In `verify.ActionReader.observe` (der Leser bei Zeile ~411): nach `action_name` ein Befund, wenn der Name nicht in `KNOWN_ACTIONS` liegt.
- [ ] **Step 4: grün; Mutationen:** der Filter in `derive` entfällt → Chronik-Test rot; die Prüfung des Namens entfällt → `teleport`-Test rot; Kontrolle grün.
- [ ] **Step 5:** `projections.md`: die Chronik zeigt Wahrnehmungen, und warum. Sechs Tore, Commit.

---

