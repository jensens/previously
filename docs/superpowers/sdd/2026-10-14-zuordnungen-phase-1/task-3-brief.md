## Task 3: Freigabeklassen — `core/classes.py`

**Files:** `src/previously/core/classes.py` (neu), `src/previously/core/action.py`, `src/previously/core/verify.py`, `tests/test_classes.py` (neu), die Tests und Seiten, die `KNOWN_ACTIONS` festhalten.

**Interfaces — Consumes:** Aufgaben 1, 2 (`ClassState`, `Graph`, `GATE_TYPES`). **Produces:**
```python
APPROVAL_CLASS: Final = "approval_class"          # in core/action.py, in KNOWN_ACTIONS
@dataclass(frozen=True)
class ApprovalClass:
    name: str; author: str; assertion: str; types: frozenset[str]; threshold: int
    valid_from: datetime | None; valid_until: datetime | None; revoked: bool; demote: bool
class ClassRefused(PreviouslyError): ...
def class_problem(payload: Mapping[str, object]) -> str | None: ...
def class_payload(item: ApprovalClass, *, statement: str) -> dict[str, object]: ...
@dataclass(frozen=True)
class Classes:
    by_name: Mapping[str, tuple[ApprovalClass, int]]          # (geltend, Event-Id)
    states: Mapping[int, ClassState]                          # jede Event-Id einer Klasse → ihr heutiger Stand
    def level(self, *, author: str, kind: str, type: str, confidence: int | None,
              recorded_at: datetime) -> tuple[str, int | None]: ...   # (TRANSITIVE, id) oder (OPEN, None); GATE_TYPES nie
def read_classes[Conn](log: LogStore[Conn], conn: Conn, *, at: datetime | None = None) -> Classes: ...
def set_class[Conn](log: LogStore[Conn], item: ApprovalClass, *, statement: str, recorded_at: datetime) -> int: ...
@dataclass(frozen=True)
class HitRate: class_id: int; name: str; total: int; confirmed: int; corrected: int; standing: int
def hit_rates(graph: Graph, classes: Classes) -> tuple[HitRate, ...]: ...
# corrected: über der transitiven Fassung steht eine spätere direkte, die nicht ihre Freigabe ist, oder ein Widerruf des Betreibers
def sample(graph: Graph, class_id: int, count: int, rng: random.Random) -> tuple[GraphVersion, ...]: ...
```
`states` gibt jedem Event, das eine Klasse je gesetzt hat, den Stand ihres **jüngsten** Events: zieht der Betreiber sie zurück, sehen alle Fassungen darunter es (Z §7.2). `set_class` weist ab: Typen aus `GATE_TYPES` (Z §7.6 Punkt 1), Typen, die das Vokabular nicht kennt, `demote` ohne `revoked`.

- [ ] **Step 1: Tests, die scheitern:** Form hin und zurück, Formfehler einzeln; `level` über und unter der Schwelle, genau an ihr, außerhalb von `valid`, für einen anderen Autor, für eine andere Art, nach Rückzug (Z §15 Punkt 5); `GATE_TYPES` in einer Klasse → abgewiesen, und `level` gibt für sie nie `transitive`, auch wenn ein Event sie im Log nennt (von Hand geschrieben); `hit_rates` mit bestätigter, korrigierter, widerrufener, stehender Fassung; `sample` mit `SystemRandom` gibt `count` verschiedene Fassungen der Klasse oder alle, wenn weniger; `verify` meldet eine kaputte Handlung `approval_class`.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** `GATE_TYPES` nicht geprüft → rot; Schwelle mit `>` statt `>=` → rot; Rückzug wirkt nur auf das jüngste Event → rot; Kontrolle grün.
- [ ] **Step 5:** sechs Tore, Commit.

---

