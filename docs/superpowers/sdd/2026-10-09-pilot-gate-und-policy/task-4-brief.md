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

