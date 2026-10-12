## Task 5: Schreiben über MCP — Handle, `write_assertion`, `write_approve`, `write_reject`

**Files:** `src/previously/mcp_server/confirm.py` (neu), `server.py`, `src/previously/cli.py` (Einstellung), `tests/test_confirm.py` (neu), `tests/test_mcp_server.py`, `tests/test_settings.py` (falls die Sammlung es verlangt), `.importlinter` (nur falls `confirm.py` das SDK importiert — soll es nicht).

**Interfaces — Consumes:** Aufgaben 1, 2, 4. **Produces:**
```python
# confirm.py — rein; Uhr übergeben
HANDLE_SECONDS: Final = 600
def seal(key: bytes, *, client: str, payloads: Sequence[Mapping[str, object]], now: datetime, nonce: str) -> str: ...
def open_handle(key: bytes, handle: str, *, client: str, payloads: Sequence[Mapping[str, object]], now: datetime) -> str: ...
#   gibt den nonce zurück; HandleRefused mit einem Satz bei falschem Siegel, anderem Client, anderem Inhalt, Ablauf
class HandleRefused(PreviouslyError): ...
# Werkzeuge
write_assertion(items: list[...], confirm: str | None)     # items: je kind, Felder der Unterart, sources, reason, subject
write_approve(ids: list[int], confirm: str | None)
write_reject(proposal: int, reason: str | None, confirm: str | None)
```
- Ohne `confirm`: prüfen (Form, Sichtbarkeit jeder Quelle für diesen Client, Verweise) und eine Vorschau plus Handle liefern, nichts schreiben. Mit `confirm`: Handle öffnen, `write_statements` mit `handle=<nonce>` — idempotent.
- `write_assertion` schreibt immer `author: model:<client>`, `responsibility: open`. `write_approve`/`write_reject` schreiben direkt (F §6); jede Quelle der betroffenen Vorschläge muss für den Client sichtbar sein.
- Eine Quelle, die der Client nicht sehen darf oder die es nicht gibt, ergibt **dieselbe** Meldung (F §6).
- Der Schreibteil läuft **außerhalb** der Schnappschuss-Verbindung von `Service.answer` (sie liest nur): Policy und Sichtbarkeit im Schnappschuss, dann `write_statements` in eigener Transaktion; das `mcp_access` nach Planentscheidung 10, ein Eintrag je Aufruf.
- `PREVIOUSLY_MCP_CONFIRM_KEY` fehlt oder ist kürzer als 32 Zeichen → die drei Werkzeuge antworten `Error: writing is not configured on this server`; die lesenden arbeiten.

- [ ] **Step 1: Tests, die scheitern:** `confirm.py` rein: hin und zurück; anderes Siegel, anderer Client, anderer Inhalt, abgelaufen (mit `now` + 601 s) → `HandleRefused`; Werkzeuge in beiden Generationen: Vorschau ohne Schreiben; Bestätigen schreibt Vorschläge mit `model:claude-code`; zweites Bestätigen → dieselben IDs, nichts Neues (Review Focus 4); ein fremder Client löst das Handle nicht ein; eine unsichtbare Quelle und eine fehlende ergeben denselben Satz; `write_approve` durch einen Client, der eine Quelle nicht sehen darf → abgewiesen (Review Focus 2); ohne Schlüssel die Fehlermeldung, lesend weiter; `mcp_access` eines Schreibaufrufs enthält keinen Text und keine Adresse (rekursive Suche wie in `test_access.py`).
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** Handle nicht an den Client gebunden → rot; Idempotenz entfällt → rot; Text im `mcp_access` → rot; unterschiedliche Meldung für unsichtbar und fehlend → rot; Kontrolle grün.
- [ ] **Step 5:** `configuration.md` (Variable), `cli.md` falls `serve`/`mcp` betroffen, Prüfsumme der Werkzeugliste; sechs Tore, Commit.

---

