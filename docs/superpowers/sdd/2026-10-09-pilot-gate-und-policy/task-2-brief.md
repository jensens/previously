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

