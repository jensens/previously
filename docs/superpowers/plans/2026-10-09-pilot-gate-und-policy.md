# Pilot, Einheit 3: Gate und Policy — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Jeder Modellaufruf des Systems geht durch ein Gate, das aus einer Policy im Log Anbieter, Modell und Raum wählt — ohne Regel nur lokal —, und jeder Aufruf wird ein Event in der Kette, dessen Ergebnis eine Tilgung der Quelle mitnimmt.

**Architecture:** Handlungen (`action`) bekommen einen gemeinsamen Schreibweg; neben `redaction` kommen `policy` und `model_call`. Die Policy (Kreise, Mitgliedschaften, eigene Identitäten, Regeln, Zusagen) und die Entscheidung liegen als reine Funktionen in `core`, weil der MCP-Server sie wiederverwendet. Ein neues Modul `previously.gate` hält Aufgaben, Preise, den Ablauf und zwei Adapter-Klassen: Anthropic und OpenAI-kompatibel, letztere zweimal konfiguriert, für Mistral und für ein lokales Modell über Ollama.

**Tech Stack:** Python 3.14, `anthropic` (SDK), `openai` (Client für Mistral und Ollama), `pydantic` (Ausgabeschema), `tomllib`, SQLAlchemy Core, PostgreSQL 17; Ollama 0.13 mit `qwen3:4b` lokal.

**Spec:** `docs/superpowers/specs/2026-10-09-pilot-gate-und-policy.md` (Commits `05c8149`..`62d044f`, vom Betreuer am 2026-10-09 durchgesehen: „spec passt").

---

## Was der Plan vorgibt und was nicht

Gelaufen am 2026-10-09, Wegwerfcode im Scratchpad, nicht übernommen; je eine
erfundene Mail (Betreff, drei Zeilen, deutsch und englisch gemischt) mit dem
Schema `{language, topic, participants}`, `additionalProperties: false`:

| Anbieter, Modell | Aufruf | Ergebnis |
|---|---|---|
| Anthropic, `claude-haiku-5-5` | `messages.create(..., output_config={"format": {"type": "json_schema", "schema": S}, "effort": "low"}, inference_geo="global")` | gültiges JSON, 3,1 s; `usage.inference_geo == "global"`; 400 Tokens hinein, 130 heraus |
| ebenso | `inference_geo="us"` | gültiges JSON, 1,9 s; `usage.inference_geo == "us"` |
| Anthropic, `claude-haiku-4-5` | `inference_geo="global"` | **400**: `'claude-haiku-4-5-20251001' does not support inference_geo.` |
| Mistral, `mistral-small-2603` | `openai.OpenAI(base_url="https://api.mistral.ai/v1").chat.completions.create(..., response_format={"type": "json_schema", "json_schema": {"name": "mail_overview", "schema": S, "strict": True}})` | gültiges JSON, 0,6 s; `model == "mistral-small-2603"`; kein Feld zum Raum |
| Ollama 0.13.2, `qwen3:4b`, OpenAI-kompatibel | wie Mistral, `base_url="http://localhost:11434/v1"`, **`reasoning_effort="none"`** | gültiges JSON, 6,7 s auf CPU (i7-11370H, unter fremder Last) |
| ebenso, ohne `reasoning_effort` | | **über 600 s, abgebrochen**: das Modell denkt |

Daraus, und nur daraus, die Aufrufe in Aufgabe 4. `/v1/models` von Mistral
listet `mistral-small-2603` und `ministral-8b-2512` als feste Fassungen;
`mistral-small-latest` antwortet unter seinem Alias.

**Nicht gelaufen**, darum nur als Anforderung mit Tests: Policy, Entscheidung,
Ablauf, Kaskade, Kommandos.

## Was der Plan am Spec entscheidet

1. **Eine Adapter-Klasse für Mistral und lokal**, `OpenAICompatibleAdapter`
   über den Client `openai` (Messung oben). `mistralai` (Spec §7.3) entfällt:
   eine Abhängigkeit weniger, und die Architektur nennt `openai` für den
   OpenAI-kompatiblen Weg ohnehin.
2. **Das Ausgabeschema ist ein Pydantic-Modell** (Architektur §10.1, bisher
   zurückgestellt, `DEPENDENCIES.md`): `model_json_schema()` gibt das Schema
   für den Anbieter, `model_validate_json()` prüft die Antwort. Pydantic ist
   unter pyright strikt getypt; `jsonschema` bräuchte Stubs. `extra="forbid"`
   ergibt `additionalProperties: false`. Der Eintrag
   `runtime-evaluated-base-classes = ["pydantic.BaseModel"]` kommt in die
   ruff-Konfiguration, wie `DEPENDENCIES.md` es vorhersagt.
3. **Modelle von `mail_overview`**, in dieser Reihenfolge:
   `anthropic/claude-haiku-5-5` (Aufwand `low`),
   `mistral/mistral-small-2603`, `local/qwen3:4b`.
4. **Der lokale Adapter setzt immer `reasoning_effort="none"`** (Messung).
5. **Die Kaskade schreibt Tilgungen.** `verify` meldet heute jede getilgte
   Einheit ohne Tilgung, die sie anordnet. Die Kaskade schreibt deshalb je
   betroffenem `model_call` eine `redaction` mit `scope: units` und dem Grund
   `cascade of redaction <id>`, in derselben Transaktion wie die auslösende.
   `verify` gleicht sie mit seinen bestehenden Regeln ab.
6. **`model_call`-Events, die eine Quelle lesen, werden durch Lesen aller
   Handlungen gefunden** (`read_by_kind(conn, "action")`). Für den Piloten
   genügt das; ein Index ist ein offener Punkt der Landkarte.
7. **Die Adressen der Anbieter** sind Konstanten in den Adaptern, mit einem
   Parameter `base_url` im Konstruktor, den nur die Tests setzen. Lokal liest
   `PREVIOUSLY_LOCAL_MODEL_URL` (ohne Vorgabe: kein lokaler Anbieter
   erreichbar).
8. **Der Testserver** ist ein `http.server.ThreadingHTTPServer` im
   Testprozess, als Fixture in `tests/conftest.py`: er beantwortet
   `POST /v1/messages` (Anthropic) und `POST /v1/chat/completions`
   (OpenAI-kompatibel) mit Antworten, die der Test vorher einreiht, und hält
   jede empfangene Anfrage fest, damit ein Test sie lesen kann (gesetzter
   Raum, Schema, `reasoning_effort`). Kein Container, keine Mocks: die echten
   Clients reden echtes HTTP mit ihm.

## Global Constraints

- Sprache nach `CLAUDE.md`: Code, Kommentare, Meldungen, Testnamen, Seiten,
  Handoff **englisch**; Spec, Plan, Landkarte deutsch.
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
- Kein `# type: ignore`; keine neue Lint-Unterdrückung (fünf, `CLAUDE.md`).
- Kein Mock für Zeit, Datenbank oder Zufall. `recorded_at` wird übergeben,
  wie überall im Kern. Der Testserver aus Entscheidung 8 ist ein Server, kein
  Mock.
- **Kein Test ruft einen echten Anbieter.** CI hat keine Secrets
  (`gates.yml`); echte Aufrufe sind Abnahme 10.
- **Kein Schlüssel erscheint** in einem Event, einer Meldung, einem
  Traceback auf stderr (Spec §6).
- Jede Zusicherung bekommt einen Test, gemessen rot bei zurückgenommener
  Zusicherung, mit einer grünen Kontrolle.
- **Arbeitsregel vom 2026-10-05:** ein Befund, der nur bei Fehlbedienung
  auftritt, wird benannt, nicht gejagt.
- Ein Kommentar ist eine Behauptung; Zahlen darin gemessen.
- Getippte Ausgabe ist eine Messung; der Testblock des Tutorials wird aus
  einem grünen Lauf neu getippt, wenn sich die Zahl ändert.
- Commits: Dateien namentlich, `git commit -F`, Trailer
  `Assisted-By: <Modell> <noreply@anthropic.com>`, nie `Co-Authored-By`.
- **Wortlaute**, vertraglich:

  | Wo | Wortlaut |
  |---|---|
  | Hilfe | `policy` — `set and show the processing policy`; `gate` — `explain or try a model call` |
  | `gate try`, stdout | die Ausgabe als JSON, dann `model_call: event <id>` |
  | stderr, Rückfall | `processed locally: no rule for <what> — set one with previously policy rule <scope> …` |
  | stderr, Alarm | `alarm: inference_geo requested <a>, reported <b>` |
  | stderr, Ablehnung | `denied: <reason>` |
  | Grund, kein lokaler Anbieter | `no local provider is declared` |
  | Grund der Kaskade | `cascade of redaction <id>` |
  | Namen in der Nutzlast | `action`, `policy`, `statement`, `revoked`, `task`, `inputs`, `response`, `outcome`, `alarms`, `fallback` |
  | `outcome` | `ok`, `denied`, `refused`, `schema_invalid`, `error` |

## Review Focus

1. **Ein getilgtes Event** (`payload is None`, Einheiten ohne Inhalt) als
   Eingabe von `gate try`: kein Aufruf, kein Prompt aus Grabsteinen — ein
   Satz, Rückgabe 2, und ein `model_call` mit `outcome: denied`, Grund
   `the event is erased`. → Aufgabe 5.
2. **Eine Adresse mit großgeschriebener Domain** (`Eva.Huber@Kunde-XZ.at`)
   gegen die Mitgliedschaft `@kunde-xz.at`: Mitglied. Ein lokaler Teil mit
   anderer Schreibung ist es nicht. → Aufgabe 3.
3. **Der Anbieter antwortet mit gültigem JSON, das dem Schema nicht genügt**
   (ein Feld zu viel, eines fehlt) oder mit Text statt JSON:
   `outcome: schema_invalid`, keine Einheiten, Rückgabe 2. → Aufgabe 5.
4. **Ollama läuft nicht**, und die Vorgabe „nur lokal" greift: ein Satz, der
   den lokalen Server nennt, `outcome: error`, Rückgabe 2, kein Traceback.
   → Aufgabe 5.
5. **Eine Mitgliedschaft in einem Kreis, der nicht angelegt ist**, oder eine
   Regel mit `project:…`: abgewiesen beim Schreiben, ein Satz, nichts
   geschrieben. → Aufgabe 2.

---

## Dateistruktur

| Datei | Aufgabe | Verantwortung |
|---|---|---|
| `src/previously/core/action.py` (neu) | 1 | gemeinsamer Schreibweg für Handlungen, die bekannten Namen |
| `src/previously/core/redact.py` | 1, 6 | nutzt `core/action.py`; die Kaskade |
| `src/previously/core/verify.py` | 1, 2, 5, 6 | unbekannte Handlung ist ein Befund; Form von `policy` und `model_call`; Vollständigkeit der Kaskade |
| `src/previously/core/projection/chronicle.py` | 1 | nur `observation`, Version 3 |
| `src/previously/core/policy.py` (neu) | 2 | Policy-Events: Formen, Schreiben, Lesen zu einem Zeitpunkt |
| `src/previously/core/decide.py` (neu) | 3 | die Entscheidung als reine Funktion |
| `src/previously/gate/__init__.py`, `adapters/__init__.py`, `adapters/anthropic.py`, `adapters/openai_compatible.py` (neu) | 4 | Adapter |
| `src/previously/gate/task.py`, `tasks/mail_overview.py`, `prices.py`, `prices.toml`, `gate.py` (neu) | 5 | Aufgabe, Preise, Ablauf |
| `src/previously/core/gaps.py` (neu) | 5 | `policy gaps` als Leseabfrage |
| `src/previously/cli.py` | 2, 5 | `policy …`, `gate explain`, `gate try` |
| `.importlinter`, `pyproject.toml`, `uv.lock`, `DEPENDENCIES.md` | 4 | Schicht `gate`; nur die Adapter importieren die Clients; drei Abhängigkeiten |
| `tests/conftest.py` | 4 | Testserver |
| `tests/test_action.py`, `test_policy.py`, `test_decide.py`, `test_gate_adapters.py`, `test_gate.py`, `test_cascade.py`, `test_verify.py`, `test_chronicle.py`, `test_cli.py` | 1–6 | Tests |
| Seiten, Handoff, Landkarte, Spec | 7 | Doku |

---

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

## Task 2: Policy-Events — Formen, Schreiben, Lesen zu einem Zeitpunkt, `previously policy`

**Files:** `core/policy.py` (neu), `core/verify.py`, `cli.py`, `tests/test_policy.py` (neu), `tests/test_verify.py`, `tests/test_cli.py`, `docs/reference/cli.md`.

**Interfaces — Consumes:** `append_action`, `POLICY` (1).
**Produces:**
```python
# core/policy.py
class Region(StrEnum): EU = "eu"; US = "us"
ANY: Final = "any"

@dataclass(frozen=True)
class Circle: name: str
@dataclass(frozen=True)
class Membership: circle: str; member: str          # Adresse oder "@domain"
@dataclass(frozen=True)
class OwnIdentity: member: str
@dataclass(frozen=True)
class Rule:
    scope: str                                       # "circle:<name>" | "source:<source>"
    regions: frozenset[str]                          # {"eu"}, {"us"}, {"eu","us"} oder {"any"}
    max_retention_days: int | None
    excluded_providers: frozenset[str]
@dataclass(frozen=True)
class Inference: name: str; regions: frozenset[str]  # "global" → {"any"}, "us" → {"us"}, "eu" → {"eu"}
@dataclass(frozen=True)
class Provider:
    name: str
    inference: tuple[Inference, ...]
    storage: frozenset[str]                          # leer = speichert nichts
    retention_days: int | None                       # None = unbekannt
    reports_inference_geo: bool
    local: bool

@dataclass(frozen=True)
class Policy:
    circles: Mapping[str, Circle]; memberships: tuple[Membership, ...]
    own: tuple[OwnIdentity, ...]; rules: Mapping[str, Rule]; providers: Mapping[str, Provider]
    ids: Mapping[tuple[str, str], int]               # (Art, Schlüssel) → Event-Id, für das Audit

type Statement = Circle | Membership | OwnIdentity | Rule | Provider
class PolicyRefused(PreviouslyError): ...           # ein Satz, nichts geschrieben

def to_payload(item: Statement, *, statement: str, revoked: bool = False) -> dict[str, object]: ...
def set_policy[Conn](log: LogStore[Conn], item: Statement, *, statement: str,
                     revoked: bool = False, recorded_at: datetime) -> int: ...
def read_policy[Conn](log: LogStore[Conn], conn: Conn, *, at: datetime | None = None) -> Policy: ...
def check_payload(payload: Mapping[str, object]) -> str | None: ...  # Befund für verify, None = gut
```

Nutzlast: `{"action": "policy", "policy": "<circle|membership|own_identity|rule|provider>", <Felder>, "statement": "…", "revoked": false}`. Mengen als sortierte Listen (kanonisch). Schlüssel je Art nach Spec §2.1; ein neueres Event mit demselben Schlüssel löst ab, `revoked: true` hebt auf. `read_policy(at=…)` liest Handlungen mit `recorded_at <= at`. Ein getilgtes Policy-Event (`payload is None`) zählt nicht.

`set_policy` weist ab (`PolicyRefused`): eine Mitgliedschaft in einem Kreis, der nicht angelegt ist; einen Geltungsbereich `project:…` (Spec §2.3) oder einen unbekannten; `regions` leer oder mit `any` neben einem Raum; einen Satz, der leer ist oder nur aus Leerzeichen besteht; eine Domain ohne Punkt.

`previously policy circle|member|own|rule|provider|show` nach Spec §5, als Unterkommandos wie `blob get`: jedes schreibende zeigt die strukturierte Fassung, fragt `write? [y/N]`, `--yes` überspringt die Frage; `--revoke`; `show [--at]` druckt eine Tabelle je Art, die eingebaute Regel `local_only` eingeschlossen.

- [ ] **Step 1: Tests, die scheitern** — `test_policy.py`, gegen PostgreSQL:
  - jede Art schreiben und lesen; ein neueres Event löst ab; ein Widerruf hebt auf; `at` vor dem zweiten Event liest das erste;
  - ein getilgtes Policy-Event zählt nicht, die vorige Fassung gilt;
  - jede Abweisung oben, mit dem Satz, und nichts geschrieben (Anzahl Events gleich);
  - `to_payload` gibt Mengen sortiert aus (zweimal mit vertauschter Eingabe: gleiche Nutzlast);
  - `verify`: ein Policy-Event mit fehlendem Schlüssel oder unbekannter Art ist ein Befund (Nutzlast über `append_action` am Schreibweg vorbei).
  - `test_cli.py`: `policy circle xz --statement "…" --yes` schreibt; ohne `--yes` und mit Eingabe `n` nichts; `policy show` zeigt Kreis und `local_only`; Review Focus 5 auf der Kommandozeile: Rückgabe 2, ein Satz.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** das Ablösen nimmt das ältere Event → Ablösungs-Test rot; die Prüfung auf den angelegten Kreis entfällt → Review-Focus-5-Test rot; `at` wird ignoriert → `at`-Test rot; Kontrolle grün.
- [ ] **Step 5:** `cli.md` (die Unterkommandos, die Wortlaute), sechs Tore, `T201`-Zählung in `pyproject.toml` neu messen, Commit.

---

## Task 3: Die Entscheidung — `core/decide.py`

**Files:** `core/decide.py` (neu), `tests/test_decide.py` (neu).

**Interfaces — Consumes:** `Policy`, `Rule`, `Provider`, `Inference` (2). Rein: keine Datenbank, keine Uhr, kein Netz.
**Produces:**
```python
@dataclass(frozen=True)
class Candidate: provider: str; model: str; effort: str | None

LOCAL_ONLY = "local_only"

@dataclass(frozen=True)
class Fallback: reason: str; circles: tuple[str, ...]        # reason == "no_rule"

@dataclass(frozen=True)
class Decision:
    circles: tuple[str, ...]; rule_keys: tuple[str, ...]
    regions: frozenset[str]; max_retention_days: int | None
    excluded_providers: frozenset[str]; local_only: bool
    chosen: Candidate | None; inference_geo: str | None      # None, wo der Anbieter keinen wählbaren Raum hat
    fallback: Fallback | None; reasons: tuple[str, ...]      # je verworfenem Kandidaten ein Satz

def circles_of(policy: Policy, identities: Sequence[Mapping[str, object]]) -> tuple[str, ...]: ...
def decide(policy: Policy, *, identities: Sequence[Mapping[str, object]], source: str | None,
           candidates: Sequence[Candidate]) -> Decision: ...
```

Nach Spec §2.2, §2.5: Domain ohne Rücksicht auf Groß- und Kleinschreibung, lokaler Teil genau; eigene Identitäten vor der Auflösung entfernt; ein Kreis ohne Regel und „keine Regel" tragen `local_only` bei; strengste gewinnt; Kandidat besteht nach Spec §2.5 Punkt 5; der Raum ist `us` nur, wenn `regions == {"us"}`, sonst der eine wählbare Raum, dessen Bedeutung ganz in `regions` liegt (`global` bedeutet `{"any"}` und liegt nur in `{"any"}`); kein Kandidat → `chosen is None`, unter `local_only` ohne lokalen Anbieter mit dem Grund `no local provider is declared`.

- [ ] **Step 1: Tests, die scheitern:**
  - Spec §8 Punkt 1–7, je ein Test mit einer Policy aus Werten (ohne Datenbank);
  - „überall" → Anthropic, `inference_geo == "global"`; „us" → Anthropic, `"us"`; „eu" → Mistral, `None`; ohne Regel → lokal, `fallback.reason == "no_rule"`;
  - zwei Kreise, einer mit „überall", einer ohne Regel → lokal, `fallback.circles == ("<der ohne>",)`;
  - `max_retention_days = 0` → nur lokal (Aufbewahrung 0); Mistral mit unbekannter Aufbewahrung fällt durch, Grund benennt es;
  - Review Focus 2;
  - **Hypothesis:** für zufällige Policies und eine zusätzliche Regel ist die Menge der bestehenden Kandidaten nach dem Hinzufügen eine Teilmenge der vorher bestehenden (`hypothesis` ist im Projekt, `tests/test_properties.py` zeigt das Muster).
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** `regions` als Vereinigung statt Schnitt → Hypothesis rot; eigene Identitäten werden nicht entfernt → Test rot; ein Kreis ohne Regel wird übergangen statt `local_only` → Zwei-Kreise-Test rot; die Domain wird genau verglichen → Review Focus 2 rot; Kontrolle grün.
- [ ] **Step 5: Sechs Tore, Commit.**

---

## Task 4: Adapter, Testserver, Abhängigkeiten, Grenzen

**Files:** `gate/__init__.py`, `gate/adapters/__init__.py`, `gate/adapters/anthropic.py`, `gate/adapters/openai_compatible.py` (neu), `tests/conftest.py`, `tests/test_gate_adapters.py` (neu), `.importlinter`, `pyproject.toml`, `uv.lock`, `DEPENDENCIES.md`, `docs/explanation/module-boundaries.md`.

**Interfaces — Produces:**
```python
# gate/adapters/__init__.py
@dataclass(frozen=True)
class Request:
    model: str; effort: str | None; system: str; user: str
    schema: Mapping[str, object]; schema_name: str; inference_geo: str | None

@dataclass(frozen=True)
class Response:
    output: str                       # der Text, ungeprüft — das Gate prüft
    reported_geo: str | None
    model: str; request_id: str | None; stop_reason: str | None
    input_tokens: int | None; output_tokens: int | None

class AdapterError(PreviouslyError): ...   # ein Satz, ohne Schlüssel, ohne Prompt

class Adapter(Protocol):
    provider: str
    def complete(self, request: Request) -> Response: ...

# gate/adapters/anthropic.py
class AnthropicAdapter:
    def __init__(self, *, api_key: str, base_url: str | None = None, timeout: float = 60.0) -> None: ...
# gate/adapters/openai_compatible.py
class OpenAICompatibleAdapter:
    def __init__(self, *, provider: str, api_key: str, base_url: str,
                 extra: Mapping[str, object] = {}, timeout: float = 60.0) -> None: ...
MISTRAL_BASE_URL = "https://api.mistral.ai/v1"

# tests/conftest.py
class ModelServer:                    # Fixture `model_server`
    url: str
    def enqueue(self, path: str, status: int, body: Mapping[str, object]) -> None: ...
    requests: list[tuple[str, dict[str, object]]]   # (Pfad, JSON der Anfrage)
```

Die Aufrufe genau wie gemessen (Abschnitt oben): Anthropic mit `output_config={"format": {"type": "json_schema", "schema": …}, "effort": …}` und `inference_geo`, `usage.inference_geo` → `reported_geo`, `stop_reason` durchgereicht (auch `refusal`); OpenAI-kompatibel mit `response_format` und `strict: True`, `extra` wird in den Aufruf gemischt (lokal: `{"reasoning_effort": "none"}`), `reported_geo = None`. `max_retries=0` in beiden Clients: das Gate schreibt jeden Versuch, also wiederholt nicht der Client still. Jede Ausnahme der Clients wird `AdapterError` mit einem Satz, der Anbieter und Fehlerklasse nennt — den Text der Ausnahme nur nach Entfernen des Schlüssels.

`.importlinter`: der Vertrag `no-vendor-sdk` wird „Only the gate adapters import vendor SDKs", mit `ignore_imports` namentlich: `previously.gate.adapters.anthropic -> anthropic`, `previously.gate.adapters.openai_compatible -> openai`. In den Schichten kommt `previously.gate` neben `previously.connectors`: `previously.connectors | previously.gate`. Der Name des Schichtvertrags folgt.

Abhängigkeiten mit Urteil in `DEPENDENCIES.md` (Datum, letzte Fassung, Bewegung des Repositorys, `py.typed`): `anthropic`, `openai`, `pydantic`; der Eintrag „No `pydantic` — not yet" wird abgelöst.

- [ ] **Step 1: Testserver** in `conftest.py` (Entscheidung 8), Thread mit `serve_forever`, Port 0, eine Fixture je Test.
- [ ] **Step 2: Tests, die scheitern** — gegen den Testserver:
  - Anthropic: die Anfrage trägt `inference_geo`, `output_config.format.schema`, `output_config.effort`; die Antwort mit `usage.inference_geo` wird `reported_geo`; ohne gesetzten Raum fehlt `inference_geo` in der Anfrage ganz;
  - OpenAI-kompatibel: `response_format.json_schema.strict is True`; `extra` landet in der Anfrage (`reasoning_effort`); `reported_geo is None`;
  - 401, 500, Zeitüberschreitung (der Server antwortet nicht innerhalb `timeout`), Verbindung abgelehnt (Port ohne Server): `AdapterError`, der Satz enthält den Schlüssel nicht (Schlüssel im Test ein auffälliger Wert);
  - genau eine Anfrage je `complete` (kein stilles Wiederholen).
- [ ] **Step 3: rot. Step 4: umsetzen. Step 5: grün; Mutationen:** `inference_geo` wird nicht gesetzt → rot; `max_retries` bleibt auf der Vorgabe → der Test „genau eine Anfrage" bei 500 rot; der Schlüssel wird nicht entfernt (ein Fehlertext, den der Testserver mit dem Schlüssel zurückgibt) → rot; Kontrolle grün.
- [ ] **Step 6:** `module-boundaries.md` (`gate`, der geänderte Vertrag), `lint-imports` mit einem absichtlichen `import anthropic` in `core` gemessen rot, sechs Tore, Commit.

---

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

## Task 6: Die Kaskade — eine Tilgung nimmt das Ergebnis mit

**Files:** `core/redact.py`, `core/verify.py`, `cli.py` (Ausgabe von `redact`), `tests/test_cascade.py` (neu), `docs/explanation/erasure.md`, `docs/how-to/erase-something.md`.

**Interfaces — Consumes:** `write_action` (1), `call` (5). **Produces:** `Redacted.cascaded: tuple[int, ...]` — die Ids der `model_call`, deren Einheiten mitgetilgt wurden.

In `redact_event`, `redact_units`, `redact_blob`, unter derselben Sperre und in derselben Transaktion: die `model_call` finden, deren `inputs` das Ziel lesen (Event; eine der Einheiten; den Blob), und für jeden mit Einheiten mit Inhalt eine `redaction` mit `scope: units`, alle seine Einheiten, Grund `cascade of redaction <id>` (Entscheidung 5). `redact` druckt `cascaded: model_call <id>` je Event.

`verify` (Spec §4.3, Punkt 1): kein `model_call` mit Einheiten mit Inhalt, dessen gelesenes Event, gelesene Einheit oder gelesener Blob getilgt ist — Befund `model_call <id> keeps the result of erased input`.

- [ ] **Step 1: Tests, die scheitern:** je Tilgungsart (Event, eine gelesene Einheit, ein gelesener Blob — für den Blob ein `model_call` mit `inputs[].blobs`, über `append_action` geschrieben) sind danach die Einheiten des `model_call` ohne Inhalt, die Nutzlast steht, eine Tilgung mit dem Grund aus den Global Constraints existiert, `verify` grün; eine Einheit, die der Aufruf **nicht** las, nimmt nichts mit; zweimal tilgen schreibt keine zweite Kaskade; die Kaskade ohne Tilgungs-Event (Einheiten von Hand gelöscht) ist ein Befund von `verify` (der bestehende) — und ein `model_call`, der nach einer Tilgung noch Einheiten hat, der neue.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** die Kaskade entfällt → rot; sie tilgt ohne eigenes Tilgungs-Event → `verify`-Test rot; die neue Prüfung in `verify` entfällt → rot; Kontrolle grün.
- [ ] **Step 5:** `erasure.md` (die Kaskade; die Aufbewahrung beim Anbieter, 30 Tage bei Anthropic, erreicht keine Tilgung), `erase-something.md` (die Ausgabe `cascaded`), sechs Tore, Commit.

---

## Task 7: Doku, Handoff, Landkarte, Einfrieren

**Files:** `docs/explanation/trust-boundaries.md` (neu), `docs/explanation/processing-policy.md` (neu), `docs/reference/policy-and-model-calls.md` (neu), `docs/how-to/set-a-policy-and-try-a-call.md` (neu), Indexseiten, `README.md`, `docs/superpowers/handoffs/2026-10-09-kup6s-gate.md` (neu, englisch), `docs/superpowers/landkarte.md`, der Spec (Einfrieren).

- [ ] Nach Spec §9, und:
  - `trust-boundaries.md` (Explanation): jede Stelle, an der Inhalt das System verlässt — IMAP, S3, Sicherungen, der Anker, das Gate je Anbieter —, wer sie bewacht, was offen ist (unbekannte Beteiligte, Aufbewahrung beim Anbieter, Aufruf ohne Audit bei Abbruch, MCP und Schreiben nach außen kommen);
  - `processing-policy.md` (Explanation): Spec §1.2 erster Punkt, Kreise nach Simmel, strengste gewinnt, Zusage und Meldung (mit der Messung: `global` meldet `global`), „ohne Regel nur lokal" und warum der Rückfall sichtbar sein muss, warum das Audit im Log liegt und das Ergebnis in den Einheiten;
  - `policy-and-model-calls.md` (Reference): die Nutzlasten aus Spec §2.1 und §4.1 mit den Namen, die der Code hat — `test_docs_references` hält die Wortlaute;
  - die How-to: Zusagen deklarieren, einen Kreis anlegen, Mitglied, eigene Identität, Regel, `gate explain`, `gate try`, `policy gaps`; Ollama mit `qwen3:4b` lokal;
  - der Handoff (englisch, Spec §6): zwei Secrets, Egress auf 443 zu `api.anthropic.com` und `api.mistral.ai`, wahlweise `PREVIOUSLY_PRICES`; und, als eigener Abschnitt, der Modellserver im Cluster mit `PREVIOUSLY_LOCAL_MODEL_URL`;
  - die Landkarte: Einheit 3 gebaut; „Offenlegungsprüfung" bei den Einheiten 3 und 4 durch die beiden Prüfungen ersetzt (Spec §1.2); Release `v0.1.0a2` vom 2026-10-09 und die Übergabe des Handoffs der Aufnahme nachgetragen; die offenen Punkte aus Spec §11 und Entscheidung 6 je unter ihre Einheit; zählen vorher und nachher.
  - Spec einfrieren (Kopf wie die anderen, Statuszeile, §11 in der Vergangenheit).
- [ ] Sechs Tore, `pip-audit`, Commits.

---

## Nach Aufgabe 7

1. Endprüfung in zwei Paketen (Code; Doku samt Handoff).
2. Eine Fixwelle, eine Nachprüfung; Fehlbedienung benannt, nicht gejagt.
3. Das Ausführungsprotokoll nach `docs/superpowers/sdd/2026-10-09-pilot-gate-und-policy/`.
4. Push und PR.
5. **Abnahme 10 (Spec §10), vom Betreuer, lokal, nach dem Merge:** die echten Schlüssel, Ollama mit `qwen3:4b`; Zusagen, Kreis, Mitgliedschaft, eigene Identität; „überall" → Anthropic mit `response.inference_geo` im Event; „EU" → Mistral; widerrufen → lokal mit Warnung, `policy gaps` nennt den Kreis; Quelle getilgt → Einheiten des `model_call` leer, `verify` grün. Danach Probe-Log verwerfen.

## Selbstprüfung dieses Plans

- **Spec-Abdeckung:** §1.2 → 1 (Handlung statt Feststellung), 7 (Landkarte); §2.1 → 2; §2.2–§2.5 → 3; §2.6 → 3 (`Fallback`), 5 (Event, stderr, `gaps`); §3.1–§3.4 → 4, 5; §4.1 → 5; §4.2 → 6; §4.3 → 1, 2, 5, 6; §4.4 → 1; §5 → 2, 5; §6 → 7 (Handoff), 4 (Schlüssel nirgends); §7 → Dateistruktur (`core/decide.py` statt der Entscheidung in `core/policy.py`, eine Datei je Verantwortung); §8 Punkt 1–7 → 3, 8–11 und 13 → 5, 11 → 6, 12 → 1, 14 → 4, 15 → 2/5/7, der Rückfall → 3/5; §9 → 7; §10 → die Aufgaben und „Nach Aufgabe 7"; §11 → Landkarte.
- **Platzhalter:** keine „TBD"; die Preise liest der Umsetzer nach und nennt die Quelle.
- **Namen:** `write_action`, `append_action`, `KNOWN_ACTIONS`, `REDACTION`, `POLICY`, `MODEL_CALL`, `Circle`, `Membership`, `OwnIdentity`, `Rule`, `Inference`, `Provider`, `Policy`, `PolicyRefused`, `set_policy`, `read_policy`, `check_payload`, `Candidate`, `Fallback`, `Decision`, `LOCAL_ONLY`, `circles_of`, `decide`, `Request`, `Response`, `Adapter`, `AdapterError`, `AnthropicAdapter`, `OpenAICompatibleAdapter`, `MISTRAL_BASE_URL`, `ModelServer`, `Task`, `MailOverview`, `MAIL_OVERVIEW`, `Prices`, `load_prices`, `estimate`, `Called`, `explain`, `call`, `Gap`, `gaps`, `Redacted.cascaded` — überall gleich.
- **Code nur, wo gelaufen:** die Aufrufe der drei Anbieter sind gemessen; der Rest steht als Schnittstelle und Test.
