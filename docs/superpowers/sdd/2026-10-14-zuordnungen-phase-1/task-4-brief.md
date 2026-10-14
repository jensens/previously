## Task 4: Schreibweg, Lesen, Prüfung, Kaskade — `core/graph_write.py`

**Files:** `src/previously/core/graph_write.py` (neu), `src/previously/core/assertions.py`, `src/previously/core/verify.py`, `tests/test_graph_write.py` (neu), `tests/test_cascade.py`, `tests/test_verify.py`, `tests/test_assertions.py`.

**Interfaces — Consumes:** Aufgaben 1–3; `retrying`, `prepare`, `link`, `LogStore`, `RedactionStore.lock_event`, `read_policy`, `decide`, `Candidate`, `SourceEvents`/`read_source_events` (CF §2, §4, §5). **Produces:**
```python
class GraphRefused(PreviouslyError): ...            # ein Satz, kein Text, keine Adresse
@dataclass(frozen=True)
class Written: ids: tuple[int, ...]; levels: tuple[str, ...]
def check_claims[Conn](log: LogStore[Conn], conn: Conn, claims: Sequence[Claim], *, recorded_at: datetime) -> tuple[Claim, ...]: ...
# Vorschau: gibt die Aussagen mit der Stufe zurück, die der Schreibweg jetzt bestimmen würde (Planentscheidung 9)
def write_claims[Conn](log: LogStore[Conn], locker: RedactionStore[Conn], claims: Sequence[Claim],
                       *, recorded_at: datetime, expect_levels: Sequence[str] | None = None) -> Written: ...
# eine Transaktion (retrying): Quellen aufsteigend sperren; Tip; ist ein handle gesetzt und steht schon eine Aussage mit ihm, deren IDs zurück;
# Vokabular, Klassen und Graph unter dem Tip lesen; Quellen wie in Einheit 5; Stufe und contests bestimmen; mit expect_levels abweichend → GraphRefused (Review Focus 2);
# conformance_problem; Enden stehen und haben die richtige Art; Freigabe nach F §3.3; acyclic über reaches, mit den Aussagen desselben Stapels; anhängen
def read_graph[Conn](log: LogStore[Conn], conn: Conn, *, as_of: datetime | None = None) -> Graph: ...
def claim_verdict(policy: Policy, client: Client, identities: Sequence[Mapping[str, object]],
                  sources: Sequence[str | None], *, recollection: bool) -> Decision: ...   # Planentscheidung 12
def relation_visible(policy: Policy, client: Client, relation: GraphVersion, ends: Mapping[int, bool],
                     identities: Sequence[Mapping[str, object]], sources: Sequence[str | None]) -> bool: ...
# eigene Quellen nach claim_verdict und beide Enden sichtbar (ends: Kennung der Entität → sichtbar)
```
In `core/assertions.py` lernen `check_statements`/`write_statements`, dass das `of` einer `rejection` auch eine offene oder transitive Graph-Fassung nennen darf (Planentscheidung 5); die Ablehnung übernimmt ihre Quellen unverändert. Leer sind sie nie: abgelehnt wird nur eine offene oder transitive Fassung, und die schreibt nur ein Modell, immer mit Quellen (Planentscheidung 12). `verify`: ein Zweig vor `assertion_problem` für `GRAPH_KINDS` — Form, Verweise auf frühere Fassungen derselben Unterart, Konformität gegen das Vokabular **zur Zeit der Aussage** (es faltet `vocabulary` und `approval_class` beim Durchgang mit), Stufe passt zur Klasse zur Zeit, Enden stehen davor, `acyclic`; in `reconcile` getilgte Quellen wie bei Feststellungen. Die Kaskade braucht keinen neuen Code (Planentscheidung 1); ein Test hält es fest.

- [ ] **Step 1: Tests, die scheitern:** schreiben und lesen (Vellenfeld: Organisation, Ämter, Personen, `holds` mit Zeiträumen, `relations(at=2019-03-01)`); idempotent über `handle`; Stufe nach Klasse, `contests` gegen einen direkten Gewinner (Z §15 Punkt 4), ein Modell ohne Klasse → `open`; `recollection` vom Betreiber geht, von einem Modell nicht (Punkt 6); Vokabular geändert zwischen `check_claims` und `write_claims` → abgewiesen (Review Focus 1); `expect_levels` weicht ab → abgewiesen (Review Focus 2); stillgelegte Art (Review Focus 4); **Zyklus** durch neue Kante, durch neue Fassung einer Kante, zu sich selbst, innerhalb eines Stapels (Review Focus 5), und durch **zwei gleichzeitige** Schreibvorgänge über zwei Verbindungen, von denen jeder für sich erlaubt ist (Z §15 Punkt 7, Planentscheidung 13); Ablehnung einer Graph-Fassung schreiben und falten; Kaskade: Quelle getilgt → Aussage getilgt, `verify` grün, Gewinner fällt zurück; `verify` findet eine Graph-Aussage mit kaputter Form, gegen das Vokabular ihrer Zeit, mit einer Stufe ohne Klasse (von Hand über `chain.prepare` und `insert_event`); `claim_verdict` mit `recollection` ohne Regel zurückgehalten, mit `source:recollection` frei.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** Zyklus nur gegen den gefalteten Graphen, nicht gegen den Stapel → rot; Vokabular zur Zeit der Vorschau statt unter dem Tip → rot; `verify` prüft gegen das heutige Vokabular statt das der Zeit → rot; die Stufe vom Client übernommen → rot; Kontrolle grün.
- [ ] **Step 5:** Kommentar in `assertions.py` zur Reihenfolge in der Transaktion (CF §12) und `docs/explanation/concurrency.md` nachziehen, falls sich die Reihenfolge ändert; sechs Tore, Commit.

---

