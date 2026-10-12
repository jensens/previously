## Task 1: Form und Faltung — `core/assertion.py`

**Files:** `src/previously/core/assertion.py` (neu), `tests/test_assertion.py` (neu).

Rein: keine Datenbank, keine Uhr.

**Interfaces — Produces:**
```python
OBLIGATION: Final = "obligation"; DECISION: Final = "decision"; REJECTION: Final = "rejection"
DIRECT: Final = "direct"; OPEN: Final = "open"
OPERATOR: Final = "human:operator"
def model_author(client: str) -> str: ...                          # "model:<client>"
def reference_problem(text: str) -> str | None: ...                # §3 der Planentscheidungen
@dataclass(frozen=True)
class Source: event: int; units: tuple[int, ...] | None
@dataclass(frozen=True)
class ObligationBody: debtor: str; creditor: str; what: str; due: date | None; state: str
@dataclass(frozen=True)
class DecisionBody: what: str; by: tuple[str, ...]; on: date; state: str; replaces: int | None
# nicht `Decision`: so heißt das Ergebnis von `decide` (core/decide.py), das derselbe Code importiert
@dataclass(frozen=True)
class Statement:
    kind: str; author: str; responsibility: str; sources: tuple[Source, ...]; reason: str | None
    handle: str | None; subject: int | None; approves: int | None; of: int | None
    body: ObligationBody | DecisionBody | None   # None nur bei REJECTION
def payload_of(statement: Statement) -> dict[str, object]: ...
def assertion_problem(payload: Mapping[str, object]) -> str | None: ...   # Formprüfung, wirft nie
def parse_statement(payload: Mapping[str, object]) -> Statement | None: ...
@dataclass(frozen=True)
class Version: id: int; recorded_at: datetime; statement: Statement
@dataclass(frozen=True)
class Thread:
    subject: int; kind: str
    versions: tuple[Version, ...]                 # stehende Fassungen in Kettenfolge
    rejected: frozenset[int]; approved: frozenset[int]
    def winner(self) -> Version | None: ...       # jüngste direkte, sonst jüngste offene weder abgelehnt noch freigegeben
    def pending(self) -> tuple[Version, ...]: ... # offene, jünger als der direkte Gewinner, weder abgelehnt noch freigegeben
def fold(rows: Iterable[tuple[int, datetime, Mapping[str, object] | None]]) -> dict[int, Thread]: ...
def changes(before: Statement, after: Statement) -> tuple[tuple[str, str, str], ...]: ...   # (Feld, vorher, nachher), beim Lesen berechnet
def overdue(obligation: ObligationBody, today: date) -> bool: ...
```
`fold` überspringt getilgte Zeilen (`payload is None`) und Zeilen mit Formfehler; eine erste Fassung gründet ihre Kennung mit ihrer eigenen ID.

- [ ] **Step 1: Tests, die scheitern:** jede Form hin und zurück (`payload_of` → `assertion_problem is None` → `parse_statement`); jeder Formfehler einzeln mit seinem Satz (leere Quellen, unbekanntes Präfix, `address:` ohne `@`, `name:` mit Steuerzeichen, `due` `2026-02-30`, `30.11.2026`, leer, Zustand unbekannt, Unterart unbekannt, `by` leer, `of` fehlt bei Ablehnung, Float); **Hypothesis**: für beliebige Folgen von Fassungen (direkt/offen, Ablehnungen, Freigaben, Tilgungen) ist der Gewinner die jüngste stehende direkte, sonst die jüngste stehende offene ohne Ablehnung und Freigabe — und ein offener nie Gewinner, solange eine direkte steht (Review Focus 1); `changes` nennt genau die geänderten Felder; `overdue` mit `due` gestern, heute, morgen, ohne `due`, `fulfilled`.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** Vorrang nach Zeit statt Verantwortung → Hypothesis rot; leere Quellen erlaubt → rot; `name:` mit Steuerzeichen erlaubt → rot; Kontrolle grün.
- [ ] **Step 5:** sechs Tore, Commit.

---

