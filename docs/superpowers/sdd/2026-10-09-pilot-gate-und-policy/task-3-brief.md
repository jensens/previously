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

