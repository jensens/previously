## Task 2: Das Graph-Modell — `core/graph.py`

**Files:** `src/previously/core/graph.py` (neu), `tests/test_graph.py` (neu).

Rein: keine Datenbank, keine Uhr. Nimmt `Source`, `OPERATOR`, `MODEL_PREFIX`, `model_author`, `DIRECT`, `OPEN` aus `core/assertion.py` (CF §1); `Statement` wird nicht erweitert (CF §12: zehn Positionsfelder).

**Interfaces — Consumes:** Aufgabe 1 (`Vocabulary`, `KindSpec`, `GATE_TYPES`). **Produces:**
```python
ENTITY: Final = "entity"; RELATION: Final = "relation"; GRAPH_KINDS: Final = frozenset({ENTITY, RELATION})
TRANSITIVE: Final = "transitive"; LEVELS: Final = (DIRECT, TRANSITIVE, OPEN)
SOURCES: Final = "sources"; RECOLLECTION: Final = "recollection"
ACTIVE, CLOSED, RETRACTED, STANDING: Final[str]
@dataclass(frozen=True)
class Period: start: date | None; end: date | None
    def holds(self, day: date) -> bool: ...
type FieldValue = str | date | Period | int
@dataclass(frozen=True)
class EntityBody: type: str; language: str | None; fields: Mapping[str, FieldValue]; state: str
@dataclass(frozen=True)
class RelationBody: type: str; start: int; to: int | None; candidates: tuple[int, ...] | None
    period: Period | None; fields: Mapping[str, FieldValue]; state: str
@dataclass(frozen=True)
class Claim:                                    # nicht `Statement` (zweimal vergeben, CF §12)
    kind: str; author: str; responsibility: str; evidence: str; sources: tuple[Source, ...]
    reason: str | None; handle: str | None; subject: int | None; approves: int | None
    under: int | None; confidence: int | None; contests: int | None
    body: EntityBody | RelationBody
def claim_payload(claim: Claim) -> dict[str, object]: ...
def claim_problem(payload: Mapping[str, object]) -> str | None: ...      # Form allein, wirft nie (Planentscheidung 3, 4)
def parse_claim(payload: Mapping[str, object]) -> Claim | None: ...
def conformance_problem(claim: Claim, vocabulary: Vocabulary, *, new_thread: bool) -> str | None: ...
# Art deklariert; neue Kennung nicht bei stillgelegter Art (Review Focus 4); Felder nach Typ, Pflichtfelder;
# closed nur bei closable; period nur bei period; Enden-Arten nach from/to; GATE_TYPES nur direct oder open
@dataclass(frozen=True)
class ClassState: id: int; revoked: bool; demote: bool          # aus Aufgabe 3 befüllt; hier nur der Typ
@dataclass(frozen=True)
class GraphVersion: id: int; recorded_at: datetime; claim: Claim
@dataclass(frozen=True)
class GraphThread:
    subject: int; kind: str; versions: tuple[GraphVersion, ...]
    rejected: frozenset[int]; approved: frozenset[int]
    def winner(self, classes: Mapping[int, ClassState]) -> GraphVersion | None: ...  # Planentscheidung 10
    def pending(self, classes: Mapping[int, ClassState]) -> tuple[GraphVersion, ...]: ...
    def objections(self, classes: Mapping[int, ClassState]) -> tuple[GraphVersion, ...]: ...  # anhängige mit contests auf den direkten Gewinner
    def question(self, classes: Mapping[int, ClassState]) -> GraphVersion | None: ...   # anhängige Rückfrage
@dataclass(frozen=True)
class Graph:
    threads: Mapping[int, GraphThread]; classes: Mapping[int, ClassState]
    def entities(self) -> Mapping[int, GraphVersion]: ...     # Gewinner, nicht retracted
    def relations(self, *, at: date | None = None) -> Mapping[int, GraphVersion]: ...   # Gewinner, standing, Zeitraum hält am Tag
    def reaches(self, start: int, end: int, types: frozenset[str]) -> bool: ...   # über Gewinner, für Zyklen
def fold_graph(rows: Iterable[tuple[int, datetime, Mapping[str, object] | None]],
               classes: Mapping[int, ClassState]) -> Graph: ...
# überspringt getilgte Zeilen, Zeilen ohne Graph-Unterart und mit Formfehler; nimmt rejection-Zeilen, deren of eine Graph-Fassung nennt
def claim_changes(before: Claim, after: Claim) -> tuple[tuple[str, str, str], ...]: ...
```
Freigabe: eine direkte Fassung mit `approves`, die Inhalt, Quellen und `author` ihrer offenen oder transitiven Fassung übernimmt (F §3.3); ein Modell schreibt `direct` nur als Freigabe (F-6, wie in Einheit 5); `transitive` verlangt `under` und `confidence` und einen Modell-Autor; `recollection` verlangt leere Quellen, `human:operator` und `direct`; `contests` nur bei `open` und Modell-Autor; `candidates` nur bei `open`.

- [ ] **Step 1: Tests, die scheitern:** jede Form hin und zurück; jeder Formfehler einzeln mit Satz (Float in `confidence`, `confidence` 101, `transitive` ohne `under`, `recollection` mit Quellen, `recollection` von einem Modell, `contests` bei `direct`, `candidates` mit einem Kandidaten oder Doppel, `closed` bei einer Beziehung, Datum `2026-02-30`); `conformance_problem` für jede Regel einzeln, auch Review Focus 4; **Hypothesis** (Z §15 Punkt 3): für beliebige Folgen von Fassungen aller drei Stufen, Ablehnungen, Freigaben, Tilgungen und Klassen (zurückgezogen, mit und ohne `demote`) ist der Gewinner die jüngste direkte, sonst die jüngste geltende transitive, sonst die jüngste unbeantwortete offene — die Erwartung aus den Zeilen allein, nicht aus `fold_graph` (wie CF §9); eine transitive nie Gewinner über einer direkten (Z §15 Punkt 4); `objections` und `question`; `relations(at=…)` an den Grenzen eines Zeitraums und mit offenen Enden; `reaches` über eine Kette und mit einer Kante zu sich selbst.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** transitiv vor direkt → Hypothesis rot; `demote` übergangen → rot; ein Modell darf `recollection` → rot; `GATE_TYPES` transitiv erlaubt → rot; Kontrolle grün.
- [ ] **Step 5:** sechs Tore, Commit.

---

