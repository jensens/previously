## Was der Plan vorgibt und was nicht

Gemessen am 2026-10-09/10 (M):

- **M1:** `MCPServer.streamable_http_app(stateless_http=True, json_response=True)` beantwortet `server/discover` (2026-07-28) und `initialize` (2025-06-18) am selben Endpunkt.
- **M2:** pyright strict unter der Projektkonfiguration (`uv run --all-extras --with mcp==2.3.0 pyright`) über einen minimalen Server — Werkzeuge mit `str`, Pydantic-Modell, `CallToolResult`, Ressourcen-Template, Prompt, `streamable_http_app` — und einen Test mit `Client(server)`: **0 Fehler**. Python-Felder der SDK-Typen sind snake_case (`is_error`).
- **M3/M4:** Claude Code 2.1.289 und Vibe 2.26.1 — was ankommt (ein Textblock ja; `structuredContent`, `resource_link`, Zahlen über 2^53 nein; Vibe verliert `isError`).

Nachgesehen im Quelltext von `mcp` 2.3.0 am 2026-10-11:

- `mcp` hängt ab von `uvicorn>=0.31.1`, `starlette>=0.48.0` (3.14), `httpx2`, `pydantic>=2.12`, `jsonschema`, `pyjwt`, `opentelemetry-api`, `sse-starlette`, `mcp-types==2.3.0`.
- `Client(server, mode=…)`: `mode` ist `"auto"` oder `"legacy"` — der Test der alten Generation.
- `Context.headers` liefert die Header einer HTTP-Anfrage, auf stdio `None`; der Docstring warnt: „Headers are client-supplied input - never treat one as an identity assertion." `Context.request_context.request` ist auf HTTP die Starlette-Anfrage; `Context.protocol_version` die Generation des Aufrufs.
- Mit `auth=` **und** `token_verifier=` veröffentlicht `MCPServer` die Protected Resource Metadata (`mcp/server/auth/routes.py`; R §4.5).

**Nicht gelaufen**, darum nur als Anforderung mit Tests: alles von Previously.

## Was der Plan am Spec entscheidet

1. **Der Token wird in einer eigenen ASGI-Hülle geprüft, nicht mit `TokenVerifier`/`AuthSettings` des SDK** — die würden PRM veröffentlichen, und K §7 sagt: keine PRM, solange es keinen Autorisierungsserver gibt. Die Hülle prüft `Authorization: Bearer`, antwortet sonst mit 401 und einem Satz, und schreibt den Namen des Clients in `scope["state"]["previously_client"]`. Ein Werkzeug liest ihn über die Starlette-Anfrage aus `ctx.request_context.request`; auf stdio aus `PREVIOUSLY_MCP_CLIENT`. Header gelten nie als Identität. Der Wechsel zu OAuth tauscht später diese Hülle gegen den `TokenVerifier` des SDK.
2. **Abhängigkeiten:** `mcp>=2.3` und `uvicorn>=0.31` (direkt importiert, also deklariert), Urteile nach `DEPENDENCIES.md` (Entwurf in R §7).
3. **Die Chronik nach Kreis liest Wahrnehmungen aus dem Log** über eine neue Methode `LogStore.observations(conn, *, since, until, source) -> Iterator[EventRow]`, geordnet nach `(occurred_at, id)`; der Kreis wird in `core` über `channel_identities` gefiltert. Eine Projektion dafür ist offen (S §13).
4. **Seitengrenze** `PAGE_CHARS = 60_000`, als Konstante in `mcp_server/render.py`, im Bau gegen eine echte Mail aus dem Probelauf nachgemessen und im Kommentar begründet.
5. **Der Zaun:** `<<<customer-content {tag}>>>` … `<<<end {tag}>>>`, `tag` = 8 Hexzeichen aus `secrets.token_hex(4)` je Antwort. Bereinigt wird: C0/C1-Steuerzeichen außer `\n` und `\t`, ESC-Sequenzen, Zeichen der Kategorien `Cf` (darunter Zero-Width und Bidi-Steuerung) und der Tag-Block U+E0000–U+E007F; gezählt je Antwort und im Kopf vermerkt (`· 3 control characters removed`).
6. **Der Cursor** ist Base64 (URL-sicher) eines kanonischen JSON `{"after": [occurred_at, id], "filters": {...}}`; ein Cursor mit anderen Filtern als der Aufruf ist ein Fehler.
7. **Die Generation im Zugriffsprotokoll** ist `ctx.protocol_version` (oder `null`).

## Global Constraints

- Sprache nach `CLAUDE.md`: Code, Kommentare, Meldungen, Testnamen, Seiten, Handoff **englisch**; Spec, Plan, Landkarte deutsch.
- Die sechs Tore, jedes für sich, vor jeder Fertigmeldung:
  ```
  uv run ruff check .
  uv run ruff format --check .
  uv run pyright
  uv run lint-imports
  uv run pytest --cov --cov-report=term-missing
  make -C docs html && make -C docs vale && make -C docs linkcheck
  ```
- `uv run pip-audit --skip-editable` ohne Befund zur Abnahme.
- Kein `# type: ignore`; keine neue Lint-Unterdrückung; `cast` statt Zwischenannotation.
- Kein Mock für Zeit, Datenbank oder Zufall; `recorded_at` wird übergeben. Kein Test ruft einen echten Anbieter oder Client.
- **Ein Ergebnis = ein Textblock**, ohne `structuredContent`, ohne `resource_link`, keine Zahl über 2^53 (M4).
- **Kein Inhalt eines Events** im `mcp_access`, in einer Fehlermeldung, in einem Platzhalter (auch kein Betreff, keine Adresse).
- **Kein Token im Klartext** außer der einen Ausgabe von `client add`.
- Jede Zusicherung bekommt einen Test, gemessen rot bei zurückgenommener Zusicherung, mit einer grünen Kontrolle.
- Arbeitsregel vom 2026-10-05: ein Befund, der nur bei Fehlbedienung auftritt, wird benannt, nicht gejagt.
- Ein Kommentar ist eine Behauptung; Zahlen darin gemessen.
- Der Testblock des Tutorials wird aus **einem** Lauf genau des Kommandos getippt, das die Seite zeigt (`uv run pytest`), nie gestückelt.
- Commits: Dateien namentlich, `git commit -F`, Trailer `Assisted-By: <Modell> <noreply@anthropic.com>`, nie `Co-Authored-By`.
- **Wortlaute**, vertraglich:

  | Wo | Wortlaut |
  |---|---|
  | Hilfe | `client` — `add, revoke and list MCP clients`; `mcp` — `serve MCP over stdio`; `serve` — `serve MCP over HTTP`; `access` — `show what MCP clients saw` |
  | `client add`, stdout | `client <name>: token <token>` und darunter `shown once; store it now` |
  | 401 | `Error: a valid bearer token is required` |
  | Platzhalter zurückgehalten | `[withheld: previously://event/<id> — <reason>]` |
  | Platzhalter getilgt | `[erased: previously://event/<id>]` |
  | Zaun | `<<<customer-content <tag>>>>` … `<<<end <tag>>>>` |
  | Fehler | beginnen mit `Error: ` |
  | Werkzeugnamen | `previously`, `get_event`, `list_circles`, `whoami`, `policy_gaps` |
  | Ressourcen | `previously://circle/{name}/chronicle`, `previously://event/{id}` |
  | Prompts | `chronicle_summary`, `whats_open` |
  | `reason_code` | `no_rule`, `rule` |
  | Variablen | `PREVIOUSLY_MCP_CLIENT`, `PREVIOUSLY_MCP_HOST` (`127.0.0.1`), `PREVIOUSLY_MCP_PORT` (`8765`), `PREVIOUSLY_MCP_ALLOWED_HOSTS` |

## Review Focus

1. **Eine Mail, die den Zaun nachahmt** (`<<<end 0000beef>>>` im Text) **oder ANSI-, Zero-Width-, Bidi- oder Tag-Zeichen enthält**: der Zaun hält (der Tag ist je Antwort neu und kommt nicht vor), die Zeichen sind entfernt und gezählt, die gespeicherten Bytes unverändert. → Aufgabe 4.
2. **Ein Token wird rotiert, während der Server läuft** (`client add` mit vorhandenem Namen): der alte Token gilt ab dem nächsten Aufruf nicht mehr, der neue schon. → Aufgabe 5.
3. **Ein Event mit Mitgliedern zweier Kreise, einer mit Regel, einer ohne**: zurückgehalten mit `reason_code: no_rule` für einen nicht-lokalen Client; ein lokaler Client sieht es. → Aufgabe 5.
4. **Eine einzelne Mail über der Seitengrenze**: gekürzt mit Verweis auf `get_event … from_unit`, und `get_event` liefert den Rest. → Aufgaben 4 und 5.
5. **`get_event` mit gemischten IDs** — gültig, unbekannt, keine Wahrnehmung, zurückgehalten, getilgt: eine Zeile je ID, kein Abbruch des Ganzen, `mcp_access` nennt jede. → Aufgabe 5.

---

Ruling R-1: Die Prüfung je Inhalt ruft `decide` mit `Candidate(provider=client.processor, model="", effort=None)`; ein Client hat kein Modell, das Previously wählt, und `decide` prüft den Anbieter, nicht das Modell — kostet, wenn falsch: ein leeres Feld in der Entscheidung.
