## Task 1: Vokabular — `core/vocabulary.py`, die Datei, `previously vocabulary`

**Files:** `src/previously/core/vocabulary.py` (neu), `src/previously/vocabulary.toml` (neu), `src/previously/core/action.py`, `src/previously/core/verify.py`, `src/previously/cli.py`, `tests/test_vocabulary.py` (neu), `tests/test_action.py`, `tests/test_access.py`, `tests/test_verify.py`, `tests/test_cli.py`, `tests/test_wheel.py`, `tests/test_docs_references.py`, `docs/reference/vocabulary.md` (neu), `docs/reference/cli.md`, `docs/reference/policy-and-model-calls.md` (Liste der Handlungen), `pyproject.toml` (T201).

**Interfaces — Consumes:** `write_action_at`, `retrying`, `KNOWN_ACTIONS` (CF §3); das Muster von `set_policy`/`read_policy`. **Produces:**
```python
VOCABULARY: Final = "vocabulary"                 # in core/action.py, in KNOWN_ACTIONS
ENTITY_KIND: Final = "entity"; RELATION_KIND: Final = "relation"
TEXT, DATE, PERIOD, CHOICE, REF: Final[str]      # die Feldtypen
CLOSABLE, PERIOD_BEHAVIOR, TRANSITIVE, ACYCLIC: Final[str]
BUILT_IN: Final[frozenset[tuple[str, str]]]      # {("entity","circle"), ("relation","member_of"), ("relation","in_circle")}
GATE_TYPES: Final[frozenset[str]]                 # {"circle", "member_of", "in_circle"}
@dataclass(frozen=True)
class FieldSpec: name: str; type: str; values: tuple[str, ...] | None; ref: str | None; required: bool
@dataclass(frozen=True)
class KindSpec:
    declares: str; name: str; labels: Mapping[str, str]; fields: tuple[FieldSpec, ...]
    behaviors: frozenset[str]; from_: tuple[str, ...] | None; to: tuple[str, ...] | None; retired: bool
@dataclass(frozen=True)
class Vocabulary:
    kinds: Mapping[tuple[str, str], KindSpec]; ids: Mapping[tuple[str, str], int]
    def kind(self, declares: str, name: str) -> KindSpec | None: ...
    def label(self, declares: str, name: str, language: str) -> tuple[str, str | None]: ...  # (Text, Ausweichsprache oder None), Planentscheidung 11
class VocabularyRefused(PreviouslyError): ...
def vocabulary_problem(payload: Mapping[str, object]) -> str | None: ...       # Formprüfung, wirft nie
def to_payload(spec: KindSpec, *, statement: str) -> dict[str, object]: ...
def read_vocabulary[Conn](log: LogStore[Conn], conn: Conn, *, at: datetime | None = None) -> Vocabulary: ...
def parse_file(text: str) -> tuple[KindSpec, ...]: ...                         # VocabularyRefused mit Satz bei Fehler
def render_file(vocabulary: Vocabulary) -> str: ...
def differences(current: Vocabulary, wanted: Sequence[KindSpec]) -> tuple[KindSpec, ...]: ...  # zu schreiben, stillgelegt eingeschlossen
def apply_vocabulary[Conn](log: LogStore[Conn], specs: Sequence[KindSpec], *, recorded_at: datetime) -> tuple[int, ...]: ...
def base_vocabulary() -> str: ...                                              # importlib.resources
```
Die eingebauten Arten stehen in `read_vocabulary` immer drin, mit festen Verbindungen und festem Verhalten; ein Event zu ihnen setzt nur `labels`, jede andere Abweichung weist `apply_vocabulary` ab. Prüfungen beim Schreiben: Bezeichner, Beschriftungen, Feldtypen und ihre Bedingungen (Planentscheidung 7), `from`/`to` nennen deklarierte, nicht stillgelegte Arten von Entitäten (auch solche aus derselben Datei), `name` Pflichtfeld jeder Entität.

- [ ] **Step 1: Tests, die scheitern:** jede Form hin und zurück (`to_payload` → `vocabulary_problem is None`); jeder Formfehler einzeln mit Satz (Bezeichner mit Großbuchstaben, leere Beschriftung, `choice` ohne `values`, `ref` auf eine Beziehung, `period`-Verhalten bei einer Entität ohne Feld `period`, unbekanntes Verhalten, unbekannter Schlüssel in der Datei); Faltung zur Zeit (`at` vor und nach einer Änderung, Z §15 Punkt 1 vorbereitet); die eingebauten Arten: Beschriftung änderbar, `from` oder Verhalten von `member_of` geändert → abgewiesen (Z §15 Punkt 2); `render_file(read_vocabulary(...))` nach `apply` derselben Datei ist dieselbe Datei, und ein zweites `apply` schreibt nichts (Z §15 Punkt 8); eine Art, die in der Datei fehlt, wird stillgelegt und bleibt lesbar; das Grundvokabular besteht die Form und steht im Wheel; `verify` meldet eine Handlung `vocabulary` mit kaputter Form; `previously vocabulary show [--at]`, `apply FILE|--base [--yes]` mit Unterschieden vor dem Fragen.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** eingebaute Art wird umdeklarierbar → rot; `apply` schreibt auch Unverändertes → rot; `verify` ohne Zweig → rot; Kontrolle grün.
- [ ] **Step 5:** `KNOWN_ACTIONS`-Tests und -Seiten (CF §3), Seite `docs/reference/vocabulary.md` (die Handlung, die Datei, das Grundvokabular), `cli.md` mit Zeile in der Tabelle der Exit-Codes, T201 nachmessen; sechs Tore, Commit.

---

