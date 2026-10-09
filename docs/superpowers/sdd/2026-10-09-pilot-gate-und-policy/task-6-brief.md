## Task 6: Die Kaskade — eine Tilgung nimmt das Ergebnis mit

**Files:** `core/redact.py`, `core/verify.py`, `cli.py` (Ausgabe von `redact`), `tests/test_cascade.py` (neu), `docs/explanation/erasure.md`, `docs/how-to/erase-something.md`.

**Interfaces — Consumes:** `write_action` (1), `call` (5). **Produces:** `Redacted.cascaded: tuple[int, ...]` — die Ids der `model_call`, deren Einheiten mitgetilgt wurden.

In `redact_event`, `redact_units`, `redact_blob`, unter derselben Sperre und in derselben Transaktion: die `model_call` finden, deren `inputs` das Ziel lesen (Event; eine der Einheiten; den Blob), und für jeden mit Einheiten mit Inhalt eine `redaction` mit `scope: units`, alle seine Einheiten, Grund `cascade of redaction <id>` (Entscheidung 5). `redact` druckt `cascaded: model_call <id>` je Event.

`verify` (Spec §4.3, Punkt 1): kein `model_call` mit Einheiten mit Inhalt, dessen gelesenes Event, gelesene Einheit oder gelesener Blob getilgt ist — Befund `model_call <id> keeps the result of erased input`.

- [ ] **Step 1: Tests, die scheitern:** je Tilgungsart (Event, eine gelesene Einheit, ein gelesener Blob — für den Blob ein `model_call` mit `inputs[].blobs`, über `append_action` geschrieben) sind danach die Einheiten des `model_call` ohne Inhalt, die Nutzlast steht, eine Tilgung mit dem Grund aus den Global Constraints existiert, `verify` grün; eine Einheit, die der Aufruf **nicht** las, nimmt nichts mit; zweimal tilgen schreibt keine zweite Kaskade; die Kaskade ohne Tilgungs-Event (Einheiten von Hand gelöscht) ist ein Befund von `verify` (der bestehende) — und ein `model_call`, der nach einer Tilgung noch Einheiten hat, der neue.
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** die Kaskade entfällt → rot; sie tilgt ohne eigenes Tilgungs-Event → `verify`-Test rot; die neue Prüfung in `verify` entfällt → rot; Kontrolle grün.
- [ ] **Step 5:** `erasure.md` (die Kaskade; die Aufbewahrung beim Anbieter, 30 Tage bei Anthropic, erreicht keine Tilgung), `erase-something.md` (die Ausgabe `cascaded`), sechs Tore, Commit.

---

