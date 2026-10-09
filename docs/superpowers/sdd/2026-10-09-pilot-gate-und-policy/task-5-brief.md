## Task 5: Das Gate — Aufgabe, Preise, Ablauf, `model_call`, `gate explain`, `gate try`, `policy gaps`

**Files:** `gate/task.py`, `gate/tasks/__init__.py`, `gate/tasks/mail_overview.py`, `gate/prices.py`, `gate/prices.toml`, `gate/gate.py`, `core/gaps.py` (neu), `core/verify.py`, `cli.py`, `tests/test_gate.py` (neu), `tests/test_cli.py`, `docs/reference/cli.md`, `docs/reference/configuration.md`.

**Interfaces — Consumes:** `append_action`, `MODEL_CALL` (1); `read_policy`, `Policy`, `Provider` (2); `decide`, `Candidate`, `Decision` (3); `Adapter`, `Request`, `Response`, `AdapterError` (4).
**Produces:**
```python
# gate/task.py
@dataclass(frozen=True)
class Task[Out: BaseModel]:
    name: str; version: int; system: str
    render: Callable[[EventRow, Sequence[UnitRow]], str]    # der Nutzerteil aus dem Event
    output: type[Out]; candidates: tuple[Candidate, ...]
    def prompt_sha256(self) -> str: ...; def schema_sha256(self) -> str: ...

# gate/tasks/mail_overview.py
class MailOverview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: str; topic: str; participants: list[str]
MAIL_OVERVIEW: Task[MailOverview]

# gate/prices.py
@dataclass(frozen=True)
class Prices: as_of: date; sha256: str; table: Mapping[str, tuple[Decimal, Decimal]]  # Modell → (Eingabe, Ausgabe) je Mio.
def load_prices(path: Path | None = None) -> Prices: ...     # None → die Datei im Paket; PREVIOUSLY_PRICES liest die CLI
def estimate(prices: Prices, model: str, geo: str | None, input_tokens: int | None, output_tokens: int | None) -> str | None: ...

# gate/gate.py
@dataclass(frozen=True)
class Called:
    event_id: int; outcome: str; decision: Decision
    output: BaseModel | None; alarms: tuple[str, ...]; message: str | None
def explain[Conn](log: LogStore[Conn], task: Task[Any], event_id: int, *, at: datetime | None = None) -> Decision: ...
def call[Conn](log: LogStore[Conn], task: Task[Any], event_id: int, adapters: Mapping[str, Adapter],
               prices: Prices, *, recorded_at: datetime) -> Called: ...

# core/gaps.py
@dataclass(frozen=True)
class Gap: what: str; count: int; last: datetime         # "circle:<name>" oder "source:<source>"
def gaps[Conn](log: LogStore[Conn], conn: Conn, *, since: datetime | None) -> list[Gap]: ...
```

`call` nach Spec §3.2: das Event lesen (Review Focus 1: getilgt → `denied`, Grund `the event is erased`); `read_policy`; `decide` mit `channel_identities` aus der Nutzlast und der Quelle aus `source_keys`; abgelehnt → `model_call` mit `denied`; sonst `Request` bauen, den Adapter des gewählten Anbieters rufen, **den Raum setzen, den `decide` nennt**; `stop_reason == "refusal"` → `refused`; `output_model.model_validate_json` scheitert → `schema_invalid`; `AdapterError` → `error`; gelungen → eine Einheit mit dem kanonischen JSON der Ausgabe. Alarm `geo_mismatch`, wenn ein Raum gesetzt und ein anderer gemeldet wurde. Nutzlast genau nach Spec §4.1, mit `policy.ids` aus `Policy.ids`. Ein Adapter fehlt in `adapters` (kein Schlüssel gesetzt) → wie `AdapterError`: der Anbieter ist nicht konfiguriert.

`verify` (Spec §4.3, Punkt 2): Form eines `model_call` — `outcome` aus der Liste, Einheiten genau bei `ok`, `inputs` eine Liste von Objekten mit `event`.

CLI: `gate explain <event>` druckt Kreise, Regeln, Auflagen, jeden Kandidaten mit Grund, die Wahl, und den Rückfall auf stderr; `gate try <event>` baut die Adapter aus der Umgebung (`ANTHROPIC_API_KEY`, `MISTRAL_API_KEY`, `PREVIOUSLY_LOCAL_MODEL_URL`; fehlt eins, fehlt nur dieser Adapter), Preise aus `PREVIOUSLY_PRICES` oder dem Paket, Rückgaben 0 / 2 / 3 nach Spec §5; `policy gaps [--since]`. Wortlaute aus den Global Constraints.

`prices.toml`, abgelesen am 2026-10-09 von der Preisseite von Anthropic und aus Mistrals Preisliste (der Umsetzer liest sie nach und nennt die Quelle im Kopf der Datei); `qwen3:4b` steht nicht drin (lokal, kein Preis): `cost_usd` dort `null`. Der Aufschlag für `us` (1,1) als eigener Eintrag.

- [ ] **Step 1: Tests, die scheitern** — `test_gate.py`, gegen PostgreSQL und den Testserver, die Mail aus `tests/mails/plain.eml` über `map_mail` und `append` ins Log:
  - jede Zeile von Spec §8 Punkt 8–11 und 13 (Kaskade in Aufgabe 6);
  - die Nutzlast eines `model_call` enthält keinen Text einer Einheit des gelesenen Events (rekursiv über alle Zeichenketten, wie `payload_holds_wording` in `core/redact.py`);
  - der Raum aus `decide` steht in der Anfrage am Testserver; gemeldet anders → `alarms == ("geo_mismatch",)`, CLI-Rückgabe 3;
  - Rückfall: ohne Regel → lokal, `policy.fallback` gesetzt, stderr mit dem Wortlaut, `policy gaps` nennt die Quelle; mit Regel → `fallback is None` und keine Zeile auf stderr;
  - Review Focus 1, 3, 4;
  - `estimate`: 1830/212 Tokens bei 0,10/0,50 → `"0.000289"`; unbekanntes Modell → `None`; `us` → das 1,1-Fache;
  - `explain` schreibt nichts (Anzahl Events gleich);
  - `verify`: ein `model_call` mit `outcome: ok` ohne Einheiten ist ein Befund.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** der Raum wird nicht gesetzt → Raum-Test rot; der Alarm entfällt → rot; ein abgelehnter Aufruf schreibt kein Event → rot; der Prompt-Text statt seines Hashes in der Nutzlast → der Kein-Inhalt-Test rot; die Prüfung gegen das Schema entfällt → Review Focus 3 rot; Kontrolle grün.
- [ ] **Step 5:** `cli.md`, `configuration.md` (drei Variablen, `PREVIOUSLY_PRICES`, wer was liest), `T201` neu messen, sechs Tore, Testblock des Tutorials, Commit.

---

