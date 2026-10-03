## Task 5: Explanation, Teil 1 — die Kette

**Files:**
- Create: `docs/explanation/hash-chain.md`, `docs/explanation/canonicalization.md`
- Modify: `docs/explanation/index.md`

**Interfaces:**
- Produces: Label `(hash-chain)=`, `(hash-domain)=`, `(tombstone-seam)=`, `(canonicalization)=`, `(timestamps)=`. Aufgabe 7 bildet Paragraphen darauf ab.

**Quelle:** `docs/superpowers/specs/2026-10-02-stufe-1a-log.md` §3.1–§3.4 und
**§6**, und `docs/superpowers/specs/2026-10-01-architektur.md` §4.6.

§6 (die Zerlegung in Einheiten) war in keiner Aufgabe dieses Plans
untergebracht — eine Lücke, die beim Vorbereiten der Überlebensliste
auffiel. Sie gehört hierher und nicht auf eine eigene Seite: wer liest,
**warum** die Einheiten im Hash stecken, will im selben Atemzug wissen, was
eine Einheit überhaupt ist. Dazu gehört der CRLF-Fund, einer der fünf stillen
Datenverluste dieses Projekts — ohne Normalisierung von `\r\n` käme ein
E-Mail-Text als **eine** Einheit an und hebelte damit die Zerlegung aus, auf
der das ganze Zuordnungsmodell beruht.

- [ ] **Schritt 1: `hash-chain.md` übersetzen**

Quadrant: Explanation. Also diskursiv, verbindend, begründend — und **keine** Anleitung, **keine** Faktenlisten (die stehen in der Reference).

Diese Begründungen müssen hinüberkommen, jede mit ihrer Zahl und ihrer Messung:

- warum der Hash den **Digest** der Nutzlast deckt und nicht die Nutzlast — die Tilgungs-Naht, und ihr Preis: ein Grabstein ist heute von einer Fälschung nicht zu unterscheiden, weil es kein Tilgungs-Event gibt
- warum `id = Vorgänger.id + 1` und **keine** Sequenz: eine Sequenz garantiert die Commit-Reihenfolge nicht, die Kette wäre 9 → 11 → 10
- warum `recorded_at` **Eingabe** ist und nicht Ausgabe
- warum Einheiten und Quellenangabe dazugehören — mit den drei gemessenen Fälschungen, die vorher durchgingen
- was die Kette **nicht** deckt: Spitze löschen, ein selbst gehashtes Event anhängen, die Kette neu schreiben. Mit der Zuspitzung, dass Anhängen schärfer ist als Löschen, und dem Satz, der das Kapitel schließen soll: *What the log says is unaltered; that it is complete, the log cannot attest by itself.*

**Übersetzen heißt nicht kürzen.** Lass keine Messung und keine Zahl weg. Ein Absatz, der danach nur noch sagt *was* gilt statt *warum*, ist ein Verlust, den niemand bemerkt.

- [ ] **Schritt 2: `canonicalization.md` übersetzen**

Aus §3.2: JCS nach RFC 8785, und warum der Nutzlastbereich absichtlich eng ist — keine Gleitkommazahlen, Schlüssel auf `^[a-z][a-z0-9_]*$`, ganze Zahlen in ±(2⁵³−1), keine Nullbytes, keine einsamen Surrogate. Je Einschränkung der Grund, nicht nur die Regel.

- [ ] **Schritt 3: Den Querverweis nachrüsten, den Aufgabe 2 weglassen musste**

`docs/reference/configuration.md` sollte laut meinem Brief auf
`{ref}`concurrency`` verweisen. Aufgabe 2 hat die Zeile zu Recht weggelassen
und das gemessen: `WARNING: undefined label: 'concurrency' [ref.ref]`, unter
`-W` ein Fehlschlag — das Label entsteht erst hier. Jetzt existiert es, also
trag den Verweis dort ein, wo er hingehört: bei der Angabe, dass PostgreSQL 15
die Untergrenze ist und `NULLS NOT DISTINCT` nicht optional.

- [ ] **Schritt 4: Beide Seiten in den Toctree von `docs/explanation/index.md` eintragen**

Das Tor fährt `sphinx-build -W`; eine Seite ohne Toctree-Eintrag lässt den Bau
scheitern. Aufgabe 6 trägt später **weitere** Seiten in dieselbe Datei ein —
schreib deinen Eintrag so, dass ein Anfügen daneben keine Konflikte macht.

- [ ] **Schritt 5: Tore und Commit**

`docs: explain the hash chain and the canonicalization`

---

