## Task 5: Der Server — Lesen, Werkzeuge, Ressourcen, Prompts, Zugang, Einstiege

**Files:** `contract/store.py`, `storage/postgres.py` (`observations`), `mcp_server/read.py`, `mcp_server/server.py`, `mcp_server/auth.py` (neu), `cli.py` (`mcp`, `serve`), `.importlinter`, `pyproject.toml`, `uv.lock`, `DEPENDENCIES.md`, `tests/test_mcp_server.py` (neu), `tests/test_cli.py`, `docs/reference/cli.md`, `docs/reference/configuration.md`, `docs/explanation/module-boundaries.md`.

**Interfaces — Consumes:** alles aus 1–4; `decide`, `circles_of`, `read_policy`, `Candidate` (Einheit 3). **Produces:**
```python
# contract/store.py, LogStore:
def observations(self, conn: Conn, *, since: datetime | None, until: datetime | None,
                 source: str | None) -> Iterator[EventRow]: ...   # nach (occurred_at, id)

# mcp_server/read.py
@dataclass(frozen=True)
class Seen: items: tuple[Item, ...]; delivered: tuple[Delivered, ...]; withheld: tuple[Withheld, ...]; last: tuple[datetime, int] | None
def chronicle[Conn](log: LogStore[Conn], conn: Conn, policy: Policy, client: Client, *,
                    circle: str | None, source: str | None, since: datetime | None,
                    until: datetime | None, after: tuple[datetime, int] | None) -> Seen: ...
def events[Conn](log: LogStore[Conn], conn: Conn, policy: Policy, client: Client,
                 ids: Sequence[int], *, from_unit: int | None) -> Seen: ...

# mcp_server/server.py
def build_server[Conn](log: LogStore[Conn], *, stdio_client: str | None) -> MCPServer: ...
def build_app[Conn](log: LogStore[Conn], *, allowed_hosts: Sequence[str]) -> Starlette: ...   # Hülle + streamable_http_app(stateless_http=True, json_response=True)

# mcp_server/auth.py
def guarded(app: ASGIApp, *, resolve: Callable[[str], str | None]) -> ASGIApp: ...   # Token → Name oder 401
```
Je Event: `decide(policy, identities=…, source=…, candidates=(Candidate(provider=client.processor, model="", effort=None),))`; besteht nicht → `Withheld` mit `reason_code` aus `decision.fallback` (`no_rule`) oder `rule`, und ein `WithheldMark`. Ein getilgtes Event (`payload is None`) → `ErasedMark`. Jeder Aufruf — Werkzeug, Ressource, Prompt — schreibt nach dem Lesen ein `mcp_access` (Aufgabe 3), auch bei Fehler. Die fünf Werkzeuge nach S §5, Ressourcen und Prompts nach S §6, Beschreibungen deklarativ ohne Kundendaten. `whoami` und `list_circles` lesen nur Policy. `previously mcp` startet stdio mit `PREVIOUSLY_MCP_CLIENT` (fehlt oder unbekannt → 2 und ein Satz, bevor gelesen wird); `previously serve` startet uvicorn mit `build_app`.

`.importlinter`: `previously.mcp_server` in die Schicht `previously.connectors | previously.gate`; ein Vertrag „Only the MCP server imports the MCP SDK" mit `ignore_imports` namentlich für die Module von `mcp_server`, die `mcp`, `uvicorn`, `starlette` importieren.

- [ ] **Step 1: Tests, die scheitern** — gegen PostgreSQL, mit Mails aus `tests/mails/` über `map_mail` und `append`, einer Policy mit Kreisen, Regeln, zwei Zusagen (eine lokal, eine `us`) und zwei Clients:
  - S §10 Punkte 1–11, je über `Client(server)` **und** `Client(server, mode="legacy")` (Punkt 11 vergleicht beide);
  - HTTP über die ASGI-App mit `httpx2` und ASGI-Transport: ohne Token 401 mit dem Wortlaut; mit Token geht es; Review Focus 2 (Rotation);
  - Review Focus 3 und 5;
  - die Werkzeugliste gegen eine Prüfsumme (Namen, Beschreibungen, Schemata, kanonisch), die im Test steht; eine Änderung macht ihn rot (S §10 Punkt 10);
  - jedes Ergebnis: genau ein Textblock, `structured_content is None`, kein `resource_link`, keine Ganzzahl über 2^53 im Text (S §10 Punkt 5);
  - `mcp_access` je Aufruf, mit `era`;
  - `previously mcp` ohne `PREVIOUSLY_MCP_CLIENT` → 2.
- [ ] **Step 2: rot. Step 3: umsetzen** — vorher `DEPENDENCIES.md` mit den Urteilen für `mcp` und `uvicorn` (Datum, Fassung, Bewegung, Typen, Lizenz; R §7 hat den Entwurf), `uv add 'mcp>=2.3' 'uvicorn>=0.31'`.
- [ ] **Step 4: grün; Mutationen:** die Prüfung je Inhalt entfällt → S §10 Punkt 1 rot; `mcp_access` nur bei Erfolg → rot; ein `WithheldMark` mit Betreff → rot; die Hülle lässt ohne Token durch → rot; eine Beschreibung geändert → Prüfsumme rot; `lint-imports` mit einem `import mcp` in `core` → rot; Kontrolle grün.
- [ ] **Step 5:** `cli.md`, `configuration.md`, `module-boundaries.md`, `T201` neu messen, sechs Tore, Testblock des Tutorials, Commit.

---

