## Task 6: Explanation, Teil 2 — Nebenläufigkeit, Grenzen, Backups

**Files:**
- Create: `docs/explanation/concurrency.md`, `docs/explanation/module-boundaries.md`, `docs/explanation/backup-encryption.md`
- Modify: `docs/explanation/index.md`

**Interfaces:**
- Produces: Label `(concurrency)=`, `(conflict-classes)=`, `(module-boundaries)=`, `(backup-encryption)=`.

**Quelle:** 1a-Spec §4.1–§4.4 und §8, Architektur §2, §10.1, §10.5.

- [ ] **Schritt 1: `concurrency.md`**

Die beiden Unique-Indexe als **gesamte** Nebenläufigkeitssteuerung — kein Advisory-Lock, kein `FOR UPDATE`. Warum `NULLS NOT DISTINCT` nicht optional ist. Die drei Konfliktklassen mit **zwei** Wiederherstellungen, und warum der Quellschlüssel-Zweig nicht zurückweicht: unter READ COMMITTED kann die Verletzung erst entstehen, **nachdem** der Wettbewerber committet hat, es kann also keinen Partner im Gleichschritt geben. Warum welcher Index zuerst anschlägt an der Index-OID-Reihenfolge hängt und darum alle drei in denselben Fehler übersetzt werden.

- [ ] **Schritt 2: `module-boundaries.md`**

`cli` → `core` → `storage` → `contract`, als Verträge geprüft. Warum die beiden Ausnahmen **namentlich** aufgezählt sind und nicht gemustert — samt der Messung mit dem Wegwerfmodul, die zeigt, dass ein Wildcard eine neue Kante lautlos durchlässt. Warum es den Riegel im Testlauf gibt. Und dass ein `LogStore[Conn]`-Protokoll die Ausnahmen ersatzlos entbehrlich machen würde.

- [ ] **Schritt 3: `backup-encryption.md`**

Aus Architektur §10.5, das die vollständige Abwägung schon trägt: dass Hetzner **gar keine** Verschlüsselung im Ruhezustand hat, dass SSE-C bei Kopien bricht (Ceph), dass barman-cloud clientseitig nicht kann, der Preis der Passphrase, und die drei Wege A/B/C samt dem, was A umstoßen würde.

- [ ] **Schritt 4: Dem Nutzlastbereich eine Heimat in der Reference geben**

Befund mittlerer Schwere aus der Prüfung von Aufgabe 5, und er muss **vor dem
Einfrieren** behoben sein: `^[a-z][a-z0-9_]*$` und `±(2**53 − 1)` kommen in
`docs/reference/`, `docs/how-to/`, `docs/tutorials/` und `docs/index.md`
**nirgends** vor. Sie stehen allein in der Explanation.

Das ist die falsche Heimat. Der Nutzlastbereich ist eine **Pflichtmenge für
jeden Aufrufer** — wer einen Konnektor schreibt, schlägt nach, was eine
Nutzlast enthalten darf, und schlägt es in der Reference nach, nicht in einem
Aufsatz über Kanonisierung. Ab Aufgabe 7 wäre die einzige maßgebliche Quelle
dafür eine Explanation-Seite.

Zu tun: einen Abschnitt in `docs/reference/hash-format.md` (dort gehört er hin,
denn er sagt, was gehasht werden **darf**), mit den fünf Einschränkungen als
Tatsachen — keine Gleitkommazahlen, Schlüsselmuster, Zahlenbereich, keine
Nullbytes, keine einsamen Surrogate — und je Zeile die Fehlermeldung, die
`core/canonical.py` dazu ausgibt. Lies sie dort ab. Dann verweist
`canonicalization.md` dorthin statt die Werte zu tragen, und behält die
Begründung.

- [ ] **Schritt 5: Die fünf stillen Datenverluste auflistbar machen**

Zweiter Befund derselben Prüfung: die Explanation sagt zweimal „one of the five
silent losses of data", und diese Fünf sind aus `docs/` **nicht auflösbar** —
nirgends steht eine Liste. Der einzige Anker ist die Spezifikation, die „der
fünfte … **dieser Sitzung**" sagt und in Aufgabe 7 einfriert. Der CRLF-Fund ist
überhaupt nirgends als einer der fünf verzeichnet.

Zu tun: eine Seite `docs/explanation/silent-losses.md`, Label
`(silent-losses)=`, die die fünf **nennt**, je in zwei bis drei Sätzen, und
sagt, was sie verbindet. Es sind:

1. Der reservierte Schlüssel `evidence` — eine Nutzlast, die ihn schon trug,
   wäre still überschrieben worden, und die Belegart ist in einem append-only
   Speicher nicht nachtragbar.
2. CRLF-Text, der als **eine** Einheit angekommen wäre und damit die Zerlegung
   ausgehebelt hätte, auf der das Zuordnungsmodell beruht.
3. Einheiten und Quellenangabe waren von der Kette **nicht gedeckt** — drei
   gemessene Fälschungen gingen durch.
4. JSON-`null` galt als Grabstein, war aber für die Grabstein-Abfrage
   unsichtbar.
5. Derselbe Quellschlüssel zweimal in einem Stapel verwarf den Inhalt des
   zweiten Eintrags und gab dem Aufrufer trotzdem zwei `id`s zurück.

Das Verbindende gehört dazu, denn es ist die Lehre des Projekts: **keiner war
ein Programmierfehler.** Jeder war eine Lücke zwischen einer Zusage und der
Wirklichkeit, und jeder wurde durch Messen gefunden, nicht durch Lesen. In
einem append-only Speicher ist jeder davon unwiederbringlich gewesen.

Danach lösen die zwei Verweise in `hash-chain.md` und `canonicalization.md`
auf — setz dort `{ref}`silent-losses``.

- [ ] **Schritt 6: Die drei Seiten in den Toctree von `docs/explanation/index.md` eintragen**

Aufgabe 5 hat dort schon zwei Einträge; füge deine an, ohne die bestehenden
anzufassen. Das Tor fährt `sphinx-build -W`, eine Seite ohne Eintrag lässt den
Bau scheitern.

- [ ] **Schritt 7: Tore und Commit**

`docs: explain concurrency, the module boundaries and the backup encryption`

---

