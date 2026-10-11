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

