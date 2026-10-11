# Pilot, Einheit 4: der MCP-Lesezugang — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Claude Code und Mistral Vibe lesen über MCP die Chronik eines Kreises und einzelne Events — jeder Inhalt nur, wenn die Policy die Verarbeitungskette des Clients zulässt, und jeder Aufruf als `mcp_access` im Log.

**Architecture:** Die Policy aus Einheit 3 bekommt Clients (Prinzipal, gehashter Token, Zusage) und eine reichere Verarbeitungskette; `decide` prüft den Client wie einen Anbieter. `core/access.py` schreibt und liest das Zugriffsprotokoll. Ein neues Modul `previously.mcp_server` stellt mit dem offiziellen SDK `mcp` 2.x fünf Werkzeuge, zwei Ressourcen und zwei Prompts bereit, rendert jedes Ergebnis als einen Markdown-Textblock mit eingezäuntem Fremdinhalt, und läuft über stdio (`previously mcp`) und Streamable HTTP (`previously serve`), beide Protokoll-Generationen über das SDK.

**Tech Stack:** Python 3.14, `mcp` 2.3 (`MCPServer`, `Client`), `uvicorn`, Starlette (über `mcp`), SQLAlchemy Core, PostgreSQL 17.

**Spec:** `docs/superpowers/specs/2026-10-10-pilot-mcp-lesezugang.md` („S"), mit dem Konzept `docs/superpowers/specs/2026-10-10-mcp-schnittstelle.md` („K"); beide vom Betreuer am 2026-10-11 durchgesehen („ok für den Plan"). Messungen: `docs/superpowers/recherche/2026-10-10-mcp-messungen.md` („M"); Recherche: `docs/superpowers/recherche/2026-10-09-mcp-stand-und-designgrundlagen.md` („R").

---

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

## Dateistruktur

| Datei | Aufgabe | Verantwortung |
|---|---|---|
| `src/previously/core/policy.py` | 1, 2 | Felder der Kette, Einschränkungen der Regel; Art `client` |
| `src/previously/core/decide.py` | 1 | die neuen Einschränkungen |
| `src/previously/core/clients.py` (neu) | 2 | Token prägen, hashen, prüfen |
| `src/previously/core/access.py` (neu) | 3 | `mcp_access`: Nutzlast, Schreiben, Lesen |
| `src/previously/core/action.py`, `core/verify.py`, `core/gaps.py` | 3 | `mcp_access` bekannt, Form; Lücken aus `mcp_access` |
| `src/previously/contract/store.py`, `storage/postgres.py` | 5 | `LogStore.observations` |
| `src/previously/mcp_server/__init__.py`, `render.py` (neu) | 4 | Markdown, Zaun, Bereinigung, Platzhalter, Seiten, Cursor |
| `src/previously/mcp_server/read.py` (neu) | 5 | Chronik und Events lesen, je Inhalt prüfen |
| `src/previously/mcp_server/server.py`, `auth.py` (neu) | 5 | `MCPServer`, Werkzeuge, Ressourcen, Prompts; ASGI-Hülle |
| `src/previously/cli.py` | 1, 2, 3, 5 | `policy`-Optionen, `client`, `access`, `mcp`, `serve` |
| `.importlinter`, `pyproject.toml`, `uv.lock`, `DEPENDENCIES.md` | 5 | Schicht `mcp_server`; nur dort `mcp`, `uvicorn`, `starlette` |
| `tests/test_policy.py`, `test_decide.py`, `test_clients.py`, `test_access.py`, `test_render.py`, `test_mcp_server.py`, `test_cli.py`, `test_verify.py` | 1–5 | Tests |
| Seiten, Handoff, Landkarte, Specs | 6 | Doku |

---

## Task 1: Die Verarbeitungskette und die Einschränkungen der Regel

**Files:** `core/policy.py`, `core/decide.py`, `cli.py` (`policy provider`, `policy rule`, `policy show`), `tests/test_policy.py`, `tests/test_decide.py`, `tests/test_cli.py`, `docs/reference/cli.md`, `docs/reference/policy-and-model-calls.md`.

**Interfaces — Produces:**
```python
# core/policy.py — Provider bekommt vier Felder (Vorgabe: unbekannt)
@dataclass(frozen=True)
class Provider:
    name: str; inference: tuple[Inference, ...]; storage: frozenset[str]
    retention_days: int | None; reports_inference_geo: bool; local: bool
    operator: str | None = None              # None: unknown
    training: bool | None = None             # None: unknown
    subprocessors: frozenset[str] | None = None   # None: unknown; frozenset(): none
    model_origin: str | None = None          # None: unknown
# Rule bekommt vier Einschränkungen
@dataclass(frozen=True)
class Rule:
    scope: str; regions: frozenset[str]; max_retention_days: int | None
    excluded_providers: frozenset[str]
    no_training: bool = False
    no_subprocessors: bool = False
    excluded_operators: frozenset[str] = frozenset()
    excluded_model_origins: frozenset[str] = frozenset()
```
Nutzlast: `operator`, `training` (`true`/`false`/`null`), `subprocessors` (sortierte Liste oder `null`), `model_origin`; bei der Regel `no_training`, `no_subprocessors`, `excluded_operators`, `excluded_model_origins` (sortiert). Eine Zusage aus Einheit 3 ohne diese Schlüssel liest sich mit den Vorgaben.

`decide` (S §3.2): zusammengeführt wie in Einheit 3 — Flags „eine verlangt es", Mengen als Vereinigung; ein Kandidat besteht `no_training` nur bei `training is False`, `no_subprocessors` nur bei `subprocessors == frozenset()`, `excluded_operators` nur bei bekanntem, nicht ausgeschlossenem `operator`, `excluded_model_origins` ebenso; der Grund je verworfenem Kandidaten nennt die Eigenschaft.

CLI: `policy provider … --operator NAME --training yes|no|unknown --subprocessors NAME…|none|unknown [--model-origin NAME]` — `--operator`, `--training`, `--subprocessors` Pflicht für neue Zusagen; `policy rule … [--no-training] [--no-subprocessors] [--exclude-operator NAME]… [--exclude-model-origin NAME]…`; `policy show` zeigt die neuen Felder.

- [ ] **Step 1: Tests, die scheitern:** je Einschränkung ein Kandidat, der besteht, einer, der scheitert, einer mit unbekanntem Wert, der scheitert; eine Zusage aus Einheit 3 (Nutzlast ohne die Schlüssel) liest sich mit Vorgaben; die Hypothesis-Eigenschaft aus Einheit 3 (`test_adding_a_rule_never_widens_the_passing_candidates`) zieht die neuen Einschränkungen mit; CLI: Pflichtoptionen fehlen → Rückgabe 2, ein Satz.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** unbekanntes `training` besteht `no_training` → rot; `excluded_operators` als Schnitt statt Vereinigung → Hypothesis rot; Kontrolle grün.
- [ ] **Step 5:** `cli.md`, `policy-and-model-calls.md` (die neuen Schlüssel), sechs Tore, Testblock des Tutorials nach der Regel, Commit.

---

## Task 2: Clients — Prinzipal, Token, Zusage

**Files:** `core/policy.py` (Art `client`), `core/clients.py` (neu), `cli.py` (`client add|revoke|list`), `tests/test_clients.py` (neu), `tests/test_policy.py`, `tests/test_cli.py`, `docs/reference/cli.md`.

**Interfaces — Consumes:** `set_policy`, `read_policy`, `Policy` (Einheit 3). **Produces:**
```python
# core/policy.py
CLIENT: Final = "client"
@dataclass(frozen=True)
class Client:
    name: str; processor: str; token_sha256: str   # hex
# Policy bekommt: clients: Mapping[str, Client]   (ids wie die anderen Arten)

# core/clients.py
def mint_token() -> str: ...                       # secrets.token_urlsafe(32)
def token_hash(token: str) -> str: ...             # sha256 hex
def client_for_token(policy: Policy, token: str) -> Client | None: ...   # hmac.compare_digest je Client
def add_client[Conn](log: LogStore[Conn], name: str, *, processor: str,
                     statement: str, recorded_at: datetime) -> tuple[int, str]: ...  # (event id, token)
```
`set_policy` weist ab: eine Zusage, die nicht deklariert ist (S §2). `client add` für einen vorhandenen Namen löst ab und sagt es vor der Rückfrage (S §2). Die Nutzlast trägt nie den Token, nur `token_sha256`; `client list` zeigt nie den Hash.

- [ ] **Step 1: Tests, die scheitern:** anlegen, ablösen (alter Token → `None`, neuer → Client), widerrufen; unbekannte Zusage abgewiesen, nichts geschrieben; der Token steht in keiner Nutzlast, keiner Ausgabe außer der einen Zeile von `client add` (alle Events durchsucht); `client_for_token` mit falschem Token → `None`; CLI-Wortlaute aus den Global Constraints.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** der Token statt des Hashes in der Nutzlast → rot; Ablösen behält den alten Token gültig → rot; Kontrolle grün.
- [ ] **Step 5:** `cli.md`, sechs Tore, Commit.

---

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

## Task 4: Die Darstellung — `mcp_server/render.py`

**Files:** `mcp_server/__init__.py`, `mcp_server/render.py` (neu), `tests/test_render.py` (neu).

Rein: keine Datenbank, keine Uhr. Zufall nur über `secrets` für den Tag.

**Interfaces — Produces:**
```python
PAGE_CHARS: Final = 60_000
@dataclass(frozen=True)
class Head: uri: str; occurred_at: datetime; source: str; sender: str | None; recipients: tuple[str, ...]; subject: str | None
@dataclass(frozen=True)
class Shown: head: Head; units: tuple[tuple[int, str], ...]     # (seq, text)
@dataclass(frozen=True)
class WithheldMark: uri: str; reason: str
@dataclass(frozen=True)
class ErasedMark: uri: str
type Item = Shown | WithheldMark | ErasedMark
@dataclass(frozen=True)
class Page: text: str; next_cursor: str | None; removed_characters: int
def sanitize(text: str) -> tuple[str, int]: ...              # (clean, removed count) — Entscheidung 5
def render_page(title: str, items: Sequence[Item], *, cursor_for: Callable[[int], str]) -> Page: ...
def render_error(message: str) -> str: ...                   # "Error: …"
def encode_cursor(after: tuple[datetime, int], filters: Mapping[str, str]) -> str: ...
def decode_cursor(cursor: str, filters: Mapping[str, str]) -> tuple[datetime, int]: ...  # ValueError bei anderen Filtern
```
`render_page` setzt den Kopf (Titel, Seite, nächster Cursor, entfernte Zeichen), je `Shown` Kopfzeilen und die Einheiten in **einem** Zaun mit dem Tag der Antwort; hört vor `PAGE_CHARS` auf; ein `Shown`, das allein darüber läge, wird gekürzt und endet mit `… truncated — continue with get_event ids=[<id>] from_unit=<n>`. Kopfzeilen (Betreff, Absender) werden ebenfalls bereinigt und stehen außerhalb des Zauns nur als Metadaten von Previously — der Betreff kommt in den Zaun.

- [ ] **Step 1: Tests, die scheitern:** Review Focus 1 (Zaun nachgeahmt; ANSI, U+200B, U+202E, U+E0041 entfernt und gezählt; `\n`, `\t`, Umlaute bleiben); der Tag zweier Antworten unterscheidet sich; Seitengrenze nie überschritten, Review Focus 4 (Kürzung mit Verweis); Platzhalter ohne Betreff und Adresse; Cursor hin und zurück, anderer Filter → `ValueError`; kein Ausgabezeichen außerhalb von `sanitize` ungeprüft (eine Property mit Hypothesis: für beliebigen Text enthält die Seite kein Zeichen der Kategorie `Cc` außer `\n`, `\t`).
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** fester Tag → der Test der zwei Antworten rot; `Cf` nicht entfernt → rot; Grenze ohne Kürzung → rot; Kontrolle grün.
- [ ] **Step 5:** sechs Tore, Commit.

---

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

## Task 6: Doku, Handoff, Landkarte, Einfrieren

**Files:** `docs/explanation/mcp-interface.md` (neu), `docs/reference/mcp-tools.md` (neu), `docs/how-to/connect-claude-code-and-vibe.md` (neu), `docs/explanation/trust-boundaries.md`, `docs/explanation/processing-policy.md`, `docs/explanation/design-records.md`, Indexseiten, `README.md`, `docs/superpowers/handoffs/2026-10-11-kup6s-mcp.md` (neu, englisch), `docs/superpowers/landkarte.md`, beide Specs (Einfrieren).

- [ ] Nach S §11 und K, und:
  - `mcp-interface.md` (Explanation): warum der Client ein Verarbeiter ist; warum ein Textblock (die Tabelle aus M4); warum der Zaun eine Wette ist und was die Grenze wirklich ist; warum das Zugriffsprotokoll im Log liegt; warum die alte Generation nichts aufhält (Entscheidung vom 2026-10-10);
  - `mcp-tools.md` (Reference): Werkzeuge, Ressourcen, Prompts mit Argumenten und Ausgabe; die Nutzlast von `mcp_access`; `test_docs_references` hält die zitierten Wortlaute;
  - die How-to: Client anlegen, Claude Code (`claude mcp add --transport http … --header`) und Vibe (`headers`, nicht `api_key_env`) verbinden, prüfen mit `whoami`; **die datierte Liste der getesteten Konfigurationen**; stdio für Claude Code lokal;
  - `design-records.md`: §8 der Architektur ist durch das Konzept abgelöst;
  - der Handoff (englisch): `previously-mcp` Deployment, Service, ein Replikat, Bereitschaft über `server/discover`, Stufe A (port-forward) und A2 (Tailscale/Headscale, `PREVIOUSLY_MCP_ALLOWED_HOSTS`), Tokens im Werkzeug-Pod anlegen; zusammen mit dem Handoff des Gates (`2026-10-09-kup6s-gate.md`) und dem lokalen Modellserver; welches Release (`v0.1.0a3`);
  - die Landkarte: Einheit 4 gebaut; die offenen Punkte aus K §10 und S §13 je unter ihre Einheit, darunter **die Idee zu Projekten mit Gegenthese** unter Einheit 5; der Punkt „Vibe auf `mcp` 2.x"; die Menge von `mcp_access`; zählen vorher und nachher;
  - beide Specs einfrieren (Kopf wie die anderen, Statuszeile, „Was offen bleibt" in der Vergangenheit).
- [ ] Sechs Tore, `pip-audit`, Commits.

---

## Nach Aufgabe 6

1. Endprüfung in zwei Paketen (Code; Doku samt Handoff), eine Fixwelle, eine Nachprüfung.
2. Das Ausführungsprotokoll nach `docs/superpowers/sdd/2026-10-11-pilot-mcp-lesezugang/`.
3. Push und PR.
4. Nach dem Merge: Release `v0.1.0a3`; dann **Abnahme 9 (S §12), vom Betreuer**: Claude Code und Vibe gegen `previously serve` mit seiner Probe-Datenbank, drei Kreise (Regel für beide, Regel für einen, keine Regel), die Frage aus K §1, danach `previously access`.

## Selbstprüfung dieses Plans

- **Spec-Abdeckung:** S §2 → 2; §3 → 1; §4 → 5; §5, §6 → 4, 5; §7 → 3, 5; §8 → 6 (Handoff), „Nach Aufgabe 6" (Release); §9 → Dateistruktur; §10 Punkte 1–11 → 5 (4 für 6–8), 9 → 1, 12 → 3/5/6; §11 → 6; §12 → die Aufgaben und „Nach Aufgabe 6"; §13 und K §10 → Landkarte.
- **Platzhalter:** keine „TBD"; die Seitengrenze misst der Umsetzer gegen eine echte Mail und begründet sie im Kommentar.
- **Namen:** `Provider`, `Rule`, `Client`, `CLIENT`, `mint_token`, `token_hash`, `client_for_token`, `add_client`, `MCP_ACCESS`, `Access`, `Delivered`, `Withheld`, `AccessRow`, `record_access`, `read_access`, `PAGE_CHARS`, `Head`, `Shown`, `WithheldMark`, `ErasedMark`, `Item`, `Page`, `sanitize`, `render_page`, `render_error`, `encode_cursor`, `decode_cursor`, `LogStore.observations`, `Seen`, `chronicle`, `events`, `build_server`, `build_app`, `guarded` — überall gleich.
- **Code nur, wo gelaufen:** die SDK-Aufrufe sind gemessen (M1, M2) oder im Quelltext nachgesehen (oben); der Rest steht als Schnittstelle und Test.
