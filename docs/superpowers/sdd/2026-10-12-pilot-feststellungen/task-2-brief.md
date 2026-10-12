## Task 2: Schreibweg, Kaskade, Prüfung — `core/assertions.py`, `redact.py`, `verify.py`

**Files:** `src/previously/core/assertions.py` (neu), `src/previously/core/redact.py`, `src/previously/core/verify.py`, `tests/test_assertions.py` (neu), `tests/test_cascade.py`, `tests/test_verify.py`.

**Interfaces — Consumes:** Aufgabe 1; `chain.prepare`/`chain.link`, `action.retrying`, `LogStore`, `RedactionStore.lock_event`, `read_policy`, `circles_of`, `decide`, `Candidate` (code-facts §1, §2, §6). **Produces:**
```python
class AssertionRefused(PreviouslyError): ...      # ein Satz, kein Text der Feststellung
def write_statements[Conn](log: LogStore[Conn], locker: RedactionStore[Conn], statements: Sequence[Statement],
                           *, recorded_at: datetime) -> tuple[int, ...]: ...
# eine Transaktion (retrying): Tip lesen; ist ein handle gesetzt und steht schon eine Feststellung mit ihm, deren IDs zurück;
# Quellen aufsteigend sperren, getilgte oder fehlende abweisen; subject/approves/of/replaces unter dem Tip prüfen (Planentscheidung 5);
# je Statement prepare(kind="assertion", occurred_at=recorded_at, payload, units=(), key=None) und link
def read_threads[Conn](log: LogStore[Conn], conn: Conn) -> dict[int, Thread]: ...
def source_identities[Conn](log: LogStore[Conn], conn: Conn, thread: Thread) -> tuple[list[Mapping[str, object]], tuple[str | None, ...]]: ...
def assertion_verdict(policy: Policy, client: Client, identities: Sequence[Mapping[str, object]],
                      sources: Sequence[str | None]) -> Decision: ...   # Planentscheidung 7: die erste, die nichts wählt, sonst die letzte
def thread_circles(policy: Policy, identities: Sequence[Mapping[str, object]], statement: Statement) -> tuple[str, ...]: ...
# Filter (F §7): Kreise der Quellen ∪ circle:X der Akteure ∪ Kreise der address:-Akteure
```
`redact.py`: die drei `redact_*` und `append_call` finden zusätzlich Feststellungen, deren `sources` das getilgte Event (oder eine getilgte genannte Einheit, oder das ganze Event bei Einheiten-Tilgung, wenn die Quelle `units: null` hat) nennen, sperren sie in derselben aufsteigenden Runde, schreiben je eine Tilgung `event_payload(id, blobs=(), reason=f"cascade of redaction {trigger}")` und `erase_payload`. `Redacted.cascaded` nennt sie mit. `verify`: vor der `action`-Prüfung ein Zweig für `kind == "assertion"`: `assertion_problem`, Verweise auf frühere Feststellungen passender Unterart, Quellen auf frühere Events; in `reconcile` „assertion stands on an erased source".

- [ ] **Step 1: Tests, die scheitern:** schreiben und lesen (eine Verpflichtung, drei Fassungen, Gewinner, Geschichte); idempotent über `handle`; Quelle fehlt, Quelle getilgt, `approves` auf Freigegebenes, Abgelehntes, Getilgtes → `AssertionRefused` und nichts geschrieben (Review Focus 2); **Kaskade** (Review Focus 3): ganzes Event, genannte Einheit, nicht genannte Einheit (steht weiter), Quelle `units: null` bei Einheiten-Tilgung, eine von drei Quellen — danach `verify` grün und `read_threads` mit Rückfall (Review Focus 1); die Gegenseite: eine Tilgung, die während des Schreibens gesperrt ist (zwei Verbindungen, wie `test_cascade.py`); `verify` findet eine Feststellung mit kaputter Form, mit Verweis nach vorn, mit getilgter Quelle ohne eigene Tilgung (von Hand geschrieben über `chain.prepare` und `insert_event`).
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** Kaskade übergeht Feststellungen → rot; Quellen nicht gesperrt → der Wettlauf-Test rot; idempotenz entfällt → rot; `verify` ohne Zweig → rot; Kontrolle grün.
- [ ] **Step 5:** Docstring-Zahlen in `contract/store.py` und `redact.py` nachmessen, falls berührt; sechs Tore, Commit.

---

