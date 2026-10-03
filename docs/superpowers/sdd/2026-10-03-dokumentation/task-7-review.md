# Aufgabe 7 — Prüfung

**Urteil: nicht ohne Nacharbeit freigeben.** Die Umstellung trägt in 17 von 21
Zeilen der Abbildungstabelle, die drei eigenmächtigen Korrekturen des
Umsetzers (§4.6, §3.1, §5.1) sind alle drei **richtig** und gegen die
eingefrorenen Stellen nachgeprüft, und die zwei neuen Tests schlagen bei allen
Angriffen an, für die sie geschrieben wurden. Aber **drei Zeiger führen in eine
Begründung, die ihr Ziel nicht trägt** — einer davon in einen Kommentar, den
dieser Commit selbst neu geschrieben hat, und einer in eine Tabellenzeile von
`design-records.md`. Nach dem Einfrieren ist das kein Tippfehler mehr. Die
Korrekturen sind klein (drei Codezeilen, eine Tabellenzeile, eine
Markup-Zeile); sie sollten vor dem Merge hinein.

Alle Messungen unten sind in Kopien unter dem Scratchpad gefahren, der Baum ist
unangetastet (`git status` leer).

---

## 1. Die Abbildungstabelle, Zeile für Zeile

Geprüft wurde für jeden Paragraphen: die eingefrorene Spec-Stelle, jede
einzelne Zitierung im Code in ihrer **neuen** Fassung, und der Abschnitt der
Zielseite, der die Behauptung tragen müsste.

Vorweg die Gegenmessung der Mengen, weil die Urteile darauf aufbauen: 72
Vorkommen auf 71 Zeilen vor dem Commit (`test_schema.py:111` trug zwei), 20
Paragraphen, alle 20 Häufigkeiten des Berichts stimmen. Nachher 58 `{ref}` auf
12 verschiedene Label, 13 eingefrorene Zitierungen, 2 aus Programmausgaben
gestrichen. 57 + 13 + 2 = 72 ✓. Die Verteilung der 58 auf die Label geht
Paragraph für Paragraph auf.

| Paragraph | Dokument | Ziel(e) im Code | Trägt es? |
|---|---|---|---|
| §2 | Architektur | `module-boundaries` ×1 | **Ja.** Die Seite sagt wörtlich „`storage` carries rows and knows nothing about the domain". |
| §3.1 | 1a | `hash-chain` ×5, `hash-format` ×2, `tombstone-seam` ×2 | **Ja, alle drei.** `hash-format` listet die elf Felder; `hash-chain` trägt den schlüssellosen Fall und „At most one source attribution per event" wörtlich; `tombstone-seam` trägt „The same seam stays open for the units" und die offengelegte Grenze. Korrektur gegen den Brief (`hash-domain`) **bestätigt**: `hash-domain` ist „Separating the domains", also das Paar `v`/`domain` — keine der neun Zitierungen handelt davon. |
| §3.2 | 1a | `payload-range` ×12 | **Zum Teil.** Für die zehn Tatsachenaussagen („the payload range is a JSON object", „violates the rules of") richtig. **Nicht** für den neuen Kommentar in `canonical.py` (Befund H1) und nur schwach für `test_verify.py:268` (Befund M3). §3.2 ist der einzige vielzitierte Paragraph **ohne** Zweitziel, und er ist der, der es am dringendsten braucht. |
| §3.3 | 1a | `timestamps` ×1 | **Nein** (Befund H3). Die einzige Zitierung behauptet die ISO-8601-Form; `timestamps` sagt dazu nur „{ref}`hash-format` holds its exact shape". Gemessen: „ISO 8601" und „six fractional digits" stehen im ganzen Baum nur in `hash-format.md:78`. Richtig wäre das Zweitziel, das die Tabelle selbst nennt. |
| §3.4 | 1a | `hash-chain` ×3 (+2 eingefroren) | **Ja.** „Counting the rows the check has seen" trägt die Zählabstimmung, die fünf Prüfungen und `event_id = 0`. |
| §4 | 1a | `concurrency` ×1 | **Ja.** Der Modul-Docstring argumentiert genau die Index-Serialisierung, die die Seite trägt. |
| §4.1 | 1a | `hash-chain` ×2 | **Ja.** „The identifier comes from the predecessor, not from a sequence"; „the chain starts at 1". |
| §4.2 | 1a | `conflict-classes` ×2, `concurrency` ×1 (+2 eingefroren) | **Zwei von drei ja.** `schema.py:83` → `concurrency` („The indexes are the serialization") ✓; `append.py:437` → `conflict-classes` („either duplicates events or spins the loop") ✓. `append.py:73` (Backoff-Schranken) → `conflict-classes`: **falsches Ziel innerhalb der richtigen Seite** (Befund M1), die acht Schranken und das Full-Jitter-Argument stehen im Abschnitt davor. |
| §4.4 | 1a | `concurrency` ×4 | **Ja.** „Batching is the remedy against contention, not its amplifier", mit `MAX_BATCH = 500` und der Starvation. |
| §4.6 | Architektur | `tombstone-seam` ×4 | **Ja.** Korrektur gegen den Brief (`backup-encryption`) **bestätigt**: alle vier Zitierungen handeln vom Grabstein, und §4.6 Unterabschnitt 1 heißt „Die Kette hängt am Hash, nicht am Inhalt" — wörtlich die Überschrift des Zielabschnitts. |
| §5 | Architektur | `module-boundaries` ×1 | **Nein** (Befund H2). Der Satz nennt fünf Negativ-Eigenschaften der Storage-Schnittstelle; gemessen stehen „no update", „no delete", „passthrough", „returning of database objects" **nirgends** in `docs/`. Nach der eigenen Regel müsste das „architecture §5 (frozen design record)" heißen — genau wie §10.1 behandelt wurde. |
| §5 | 1a | `hash-chain` ×3, `canonicalization` ×1 | **Zwei von vier klar ja.** `hashing.py:135` und `postgres.py:297` → `hash-chain` wörtlich ✓. `append.py:427` → **schwächeres Ziel** (Befund M2): der ganze Kommentar steht in `concurrency`, dort sogar mit derselben Formel „which the contract permits". `test_append:534` → `canonicalization` trägt es („The wanted property is idempotency *between* calls"), aber der Satz ist beim Umbau beschädigt (Befund M4). |
| §5.1 | Entwurf | `canonicalization` ×7 | **Ja.** Korrektur gegen den Brief **bestätigt**: 1a §5 hat keine Unterabschnitte, Entwurf §5.1 „Wahrnehmung" definiert `evidence` als `verbatim | recollection` und „trennt Beweis von Bericht" — und `canonicalization` → „The reserved key" trägt genau diesen Satz auf Englisch. |
| §6 | 1a | `hash-chain` ×1 | **Ja.** „What a unit is" trägt die vierschrittige Regel und „No language detection, no attribution, no classification" — die Zeilenenden-Normalisierung sogar zusätzlich. |
| §7 | 1a | `database-schema` ×1, `concurrency` ×1 | **Ja, beide.** `database-schema` listet alle neun `event`-Spalten, die `EventRow` spiegelt; `concurrency` sagt wörtlich „`append` owes the caller exactly one `int` per event". Anmerkung: keine Seite nennt `EventRow`/`UnitRow` beim Namen, der Feldvertrag ist nur über die Spaltentabelle gedeckt. |
| §8 | 1a | `module-boundaries` ×1 | **Ja.** |
| §9 | 1a | `cli-reference` ×1, `configuration-reference` ×1 | **Ja, beide.** `configuration.md` trägt `PREVIOUSLY_DSN` samt Vorrangregel, also genau das, was `migrations/dsn.py` begründet. |
| §10.1 | Architektur | eingefroren | **Richtig.** Das Argument („ein append-only Speicher hat keine Verwendung für ein ORM") steht in keiner Seite; `database-schema` hält nur das Ergebnis. Genau die Behandlung, die §5 der Architektur auch gebraucht hätte. |
| §10.2 | 1a | eingefroren | **Richtig.** Registernamen P1–P7. |
| §11 | 1a | eingefroren | **Richtig** — und der README-Satz, der eine heutige Frage stellte, ist korrekt auf `hash-chain` umgezogen, wo „What the chain doesn't cover" ihn trägt. |
| §12 | 1a | eingefroren | **Richtig.** Offene Punkte, datiert. |

### Die drei Korrekturen des Umsetzers

Alle drei richtig, alle drei gegen die eingefrorene Stelle geprüft, und keine
von ihnen hat unterwegs etwas anderes kaputt gemacht. §3.1 ist der
bemerkenswerte Fall: der Umsetzer hat nicht nur das Brief-Ziel verworfen,
sondern die neun Zitierungen auf **drei** Ziele aufgeteilt, und jede der drei
Gruppen landet auf dem Abschnitt, der sie wirklich trägt.

---

## 2. Angriffe auf die zwei neuen Tests

Vorgehen: Kopie des Baums unter dem Scratchpad, Mutation einspielen,
`pytest tests/test_docs_references.py` fahren, zurückspielen. Ausgangslage in
der Kopie `4 passed`.

### `test_no_program_output_cites_a_specification`

| # | Mutation | Ergebnis |
|---|---|---|
| 1 | Zitierung in der **Fortsetzung eines f-Strings** in `canonical.py` | **gefangen** — `{'…/canonical.py': [58]}` |
| 2 | Zitierung in einem **`%`-formatierten** String in `canonical.py` | **gefangen** — `[58]` |
| 3 | Zitierung in einem **Literal einer Hilfsfunktion** in `canonical.py` | **gefangen** — `[42]` |
| 9 | Meldung in `canonical.py`, markiert als `(§3.2, frozen design record)` | **gefangen, und nur von diesem Test** — der Nachbartest ist grün. Der Test verdient damit nachweislich seinen Platz. |
| 14/15 | Mutation 1, einmal gegen die **Heuristik des Briefs**, einmal gegen die ausgelieferte `ast`-Prüfung | Heuristik: `1 passed`. `ast`: `1 failed`. Die Verschärfung ist gemessen begründet. |
| 4 | Dieselbe Meldung, markiert als frozen, in **`core/verify.py`** | **durchgelassen** — `4 passed` |
| 4b | `print("hint: §9 (frozen design record) …")` in **`cli.py`** | **durchgelassen** — `4 passed` |

Befund: die Erkennung ist dicht — f-String-Fortsetzung, `%`-Format und
Hilfsfunktions-Literale findet sie alle, und sie findet den einen Fall, den der
Nachbartest nicht finden kann. **Das Loch ist die Dateiliste, nicht die
Prüfung.** `RUNTIME_MESSAGE_FILES` nennt zwei Dateien; die Datei, die
tatsächlich auf das Terminal druckt, ist `cli.py` mit dreizehn `print`-Aufrufen,
und sie steht nicht darin. Damit ist genau der Fehler, vor dem der Brief warnt
(„sonst schreibt der nächste Umsetzer `(frozen design record)` in die
Fehlermeldung und der Test ist grün"), in elf von dreizehn Dateien weiter
möglich. Die Prüfung über alle `src/**/*.py` zu fahren statt über zwei Pfade
kostet nichts: `ast.parse` über das halbe Dutzend Module ist schneller als der
Zeilenscan, den der Nachbartest ohnehin macht.

Nebenbei, ohne Messung, weil im Baum nicht erreichbar: `_docstrings()` kennt
`ast.AsyncFunctionDef` nicht und auch keine Attribut-Docstrings — beides wäre
ein Falschtreffer, beides ist in einem bewusst synchronen Projekt ohne
Attribut-Docstrings heute kein Problem.

### `test_the_reference_quotes_what_the_code_actually_prints`

| # | Mutation | Ergebnis |
|---|---|---|
| 6 | Der Tabelle eine **sechste Zeile** mit einer Meldung hinzufügen, die niemand druckt (`emoji not allowed — use words`) | **grün** |
| 7 | Das Float-Zitat aus der Tabellenzelle entfernen („none") und es stattdessen in einen **Prosa-Satz am Seitenende** stellen | **grün** |

Befund: **ja, der Test kann wieder grün sein, während die Seite falsch ist.**
Die Verschärfung auf `` f"`{quoted}`" in page `` schließt die eine Richtung
(die Zelle darf nicht *mehr* sagen als die Meldung) und lässt die andere offen:
die Seite darf Meldungen zitieren, die **nichts** erzeugt, und sie darf das
Zitat aus der Tabelle herausnehmen. Das ist dieselbe Fehlerklasse wie A9, nur
in der anderen Richtung — A9 war der veraltete Zusatz *in* der Zelle, Angriff 6
ist die veraltete Zelle als Ganzes.

Was fehlt, ist die Rückrichtung: die Zeilen der Tabelle „Payload range"
einlesen, die Zitate aus der Spalte `Message` ziehen und gegen die Menge der
vom Code erzeugten Meldungen abgleichen — Gleichheit beider Mengen, nicht
Teilmenge. Dann fällt Angriff 6 **und** Angriff 7, und die fünf hartkodierten
Payloads wären obendrein keine stille Obergrenze mehr (heute ist das sechste
Zitat der Seite, `type set not allowed`, von niemandem gedeckt).

### Zwei Löcher daneben, die beim Angreifen aufgefallen sind

| # | Mutation | Ergebnis |
|---|---|---|
| 11 | `{ref}`hash_chain`` (Unterstrich statt Bindestrich) in `verify.py` | **grün** |
| 12 | `` {ref}`the chain <hash-chain-typo>` `` in `verify.py` | **grün** |
| 13 | `{ref}`hash-chainn`` in `verify.py` (Kontrolle) | **rot** ✓ |
| 8 | Nackte Zitierung `§9` in `pyproject.toml` | **grün** |

`REFERENCE = re.compile(r"\{ref\}`([a-z0-9-]+)`")` sieht nur die
Grundform. Ein Vertipper mit einem Zeichen außerhalb `[a-z0-9-]` ist für die
Auflösungsprüfung **unsichtbar**, und die Form mit explizitem Titel —
diejenige, die die Doku selbst benutzt
(`` {ref}`five silent losses of data <silent-losses>` ``) — ebenso. Da `{ref}`
in `.py` nie von Sphinx gerendert wird, fängt das niemand sonst. Zwei Zeichen
im Muster (`([a-z0-9_-]+)` plus optionaler Titelteil) schließen beides.

Angriff 8 zeigt die zweite Grenze: der Brief erklärt die Markierungspflicht
ausdrücklich für **jede englischsprachige Datei, nicht nur für `.py`** — und
die Begründung dafür ist `DEPENDENCIES.md`. Das Tor prüft nur `.py` unter drei
Verzeichnissen. `pyproject.toml` ist gerade die Datei, aus der dieser Commit
einen Verweis entfernt hat.

### Der `SELF`-Ausschluss: der Tauschhandel ist falsch gewählt, und es gibt einen dritten Weg

Angriff 5 (nackte Zitierung in `test_docs_references.py` selbst) läuft wie
angekündigt durch: `4 passed`.

Die Begründung des Berichts für das Loch trifft nicht zu. Sie lautet, die
Alternative „hätte die gemessene Fundstelle (`canonical.py:53`,
`append.py:309`) aus der Dokumentation des Tests entfernt" — aber der Umsetzer
hat die Paragraphennummern in genau diesem Docstring **schon** herausgeschrieben:
dort steht „`canonical.py:53` with the canonicalisation paragraph and the
literal beginning at `append.py:309` with the perception paragraph". Die
Messung ist also bereits ohne das Zeichen notiert. Übrig sind drei Stellen: die
beiden Prüfzeilen, die das Zeichen brauchen, und **ein** illustratives `§3.1`
in einer einzeiligen Docstring-Zeile.

Dritter Weg, gemessen in der Kopie:

1. `SECTION = "§"` am Modulkopf, mit einem Satz, warum es gebaut und nicht
   geschrieben wird; beide Prüfungen benutzen `SECTION`.
2. Das illustrative `§3.1` in Zeile 59 wird zu „A bare paragraph number".
3. `SELF` und der `continue` fallen weg — die Datei prüft sich mit.

Ergebnis:

```
A  vier Tests, SELF-Ausschluss entfernt, kein Zeichen mehr in der Datei
   4 passed in 0.08s
B  ruff check tests/test_docs_references.py        -> All checks passed!
   ruff format --check tests/test_docs_references.py -> 1 file already formatted
C  Angriff 5 noch einmal (nackte Zitierung in der Testdatei)
   FAILED test_no_bare_paragraph_references_remain
D  Angriff 9 noch einmal (markierte Meldung in canonical.py)
   FAILED test_no_program_output_cites_a_specification
```

Beides bleibt: die Messung in der Dokumentation **und** die Selbstprüfung. Das
Loch muss nicht bezahlt werden.

---

## 3. Die Einfrier-Kopfzeilen

**Die eine Frage, die der Auftraggeber gestellt hat, ist mit Ja zu
beantworten:** die nächste Stufe kann die Kopfzeile nicht als Verbot lesen. Der
Satz „Ein neuer Spec für eine neue Stufe entsteht wieder auf Deutsch — das ist
die Sprache, in der die Absicht formuliert wird. Er friert ein, sobald seine
Explanation-Seiten stehen" sagt beides, was er sagen muss: dass wieder einer
entsteht, und was ihn dann einfriert. Er steht in allen drei Dokumenten gleich
und wörtlich wie im Brief. Kein Arbeitsablauf blockiert hier.

Zwei Einwände, beide klein, beide am selben Satz:

**„Die lebende Begründung steht in `docs/explanation/`" ist zu eng.** Gemessen
zeigen 17 der 58 Code-Verweise in `docs/reference/` (`payload-range` 12,
`hash-format` 2, `database-schema`, `cli-reference`,
`configuration-reference`). Der Satz danach (**„gilt die Doku"**) ist richtig
allgemein; der Ortsangabe-Satz nennt nur ein Viertel. Ein Wort: „in der
Dokumentation unter `docs/`".

**Die Kopfzeile steht unqualifiziert auch über dem Entwurf.** Der Entwurf
behandelt Zuordnung, Projektionen, Konnektoren, den KI-Layer und zehn
Entitäten; die Architektur §6–§9 dazu Konnektorvertrag, Prozessmodell, MCP und
die Gate-Schnittstelle. Für all das gibt es keine Explanation-Seite. „Die
lebende Begründung steht in `docs/explanation/`" ist dort nicht falsch, sondern
leer — und `design-records.md` sagt es für die zwanzig zitierten Paragraphen
ehrlich („nowhere; frozen design record"), die Kopfzeile aber nicht. Ein
Halbsatz („soweit sie dort steht; sonst ist dieses Dokument die einzige
Quelle") würde die nächste Stufe davor bewahren, in einem stillen Quadranten zu
suchen.

Als Ablauf hingeschrieben, wie der Brief es verlangt, ist es übrigens eher auf
der Seite als in der Kopfzeile: `design-records.md` hat den Abschnitt „Freezing
is a step in a procedure, not a state the project arrived at", und der ist
genau das. Die Kopfzeile verweist nicht auf ihn. Ein Link dorthin wäre die
billigste Verstärkung, die hier zu haben ist — zumal auf `design-records`
gemessen **nichts** zeigt (siehe Befund N2).

---

## 4. Die zwei Klassengrenzen

### `DEPENDENCIES.md`: richtig entschieden, aber der Absatz behauptet zu viel

Die Entscheidung selbst — einmal über der Tabelle statt dreizehnmal in den
Zellen — ist richtig. Neun gleiche Klammern in einer Spalte sind keine
Information, sondern Rauschen, und die Begründung des Umsetzers („jede Zeile
dieses Registers ist selbst eine datierte Entscheidung") trägt für die
Tabellenzeilen. Eine einzelne Tabellenzeile lügt dadurch **nicht** über die
Aktualität ihres Ziels: die Zeile sagt „Stand 2026-10-02, aktiv", also ist sie
schon selbst datiert, und die Zahlen stammen nicht aus dem Spec.

Zwei Befunde am Absatz, nicht an der Entscheidung:

**Der Satz stimmt für §2 nicht.** „Every paragraph reference on this page points
into a **frozen design record**" — die `import-linter`-Zeile begründet sich mit
„The architectural boundaries of §2 checked as contracts", und §2 ist in der
Tabelle, auf die der Absatz verlinkt, auf `module-boundaries` abgebildet. Das
ist eine lebende Begründung (Klasse 1), kein datiertes Zitat. Entweder die
Zeile nennt die Seite, oder der Absatz sagt „mit einer Ausnahme".

**Der Link überspricht.** „the map from a paragraph to its page is in [About the
frozen design records]" — gemessen stehen 11 der 13 Zitierungen dieser Seite
(§10.6 achtmal, §10.7 zweimal, §8.6 einmal) in jener Tabelle **gar nicht**; sie
bildet nur die zwanzig aus dem Code ab. Wer dem Link folgt, sucht das, wofür er
ihm gegeben wurde, und findet es nicht.

**Gegenmessung zur Zahl:** 13 Vorkommen auf 12 Zeilen (Zeile 26 trägt §2 und
§10.6), davon zehn in Tabellenzellen und drei in Prosa. Der identische Satz
„reasoning in §10.6 of the architecture (choice of tooling)" kommt **achtmal**
vor, nicht neunmal (`grep -c` = 8). A11 ist in diesem Detail falsch — ohne
Folgen für die Entscheidung, aber es ist eine Zahl, die eine Entscheidung
stützt.

### Zweitziele: die Regel trägt, aber sie ist nicht die Regel, die der Bericht beschreibt

Die Regel, die die Seite hinschreibt — „ein Verweis, der erklärt, *warum der
Code heute so ist*, nennt eine Seite; ein Verweis, der sagt, *was wann
entschieden wurde*, behält die Nummer" — ist scharf und auf jeder Zeile
anwendbar. Sie ist keine Hintertür: sie wählt nicht zwischen zwei Seiten,
sondern zwischen Seite und eingefrorenem Bericht, und das Tor prüft sie
zeilenweise.

Was das Zweitziel auswählt, ist aber eine **andere** Regel, und die steht nur
in den Tabellenzellen als Relativsatz („where the citation asks for the field
list", „where it's about the erasure seam"). Sie trägt überall dort, wo die
Spec-Stelle zwei Hälften hat, die die Doku auf zwei Seiten getrennt hat — und
das ist der Normalfall, nicht die Ausnahme: §3.1 hat drei Ziele, §3.3, §4.2,
§5 (1a), §7 und §9 haben zwei. Genau deshalb ist sie keine Hintertür, sondern
die einzige ehrliche Form.

Der Beweis, dass sie trägt, ist der Fall, in dem sie **fehlt**: §3.2 ist mit
zwölf Zitierungen der häufigste Paragraph und hat nur ein Ziel. Die Spec-Stelle
heißt „Kanonisierung: JCS, und keine Gleitkommazahlen" und hat damit dieselben
zwei Hälften wie alle anderen — und die Doku hat sie sauber getrennt:
`payload-range` (Reference) „lists the restrictions as facts", `canonicalization`
(Explanation) ist „the other half: each exclusion has its own reason". Die
Einzelabbildung hat sofort einen falschen Satz erzeugt (Befund H1). Die
Behauptung des Berichts, „§3.2 und §5.1 sind eindeutig", ist der eine Punkt, an
dem die eigene Regel nicht angewandt wurde.

Nebenbei: die Tabelle im Bericht und die Tabelle auf der Seite sind nicht
deckungsgleich — die Seite gibt §3.3 ein Zweitziel (`hash-format`), der
Bericht nicht, und Bedenken 5 zählt fünf Paragraphen mit Zweitziel, wo die
Seite sechs hat (und §3.1 drei Ziele).

---

## 5. Sätze, die durch die Umstellung falsch geworden sind

### H1 — `src/previously/core/canonical.py:49–53`, neuer Kommentar

```python
# Why floating point numbers are out at all —
# their rendering is language-dependent, and a hash that comes out
# differently per runtime is worthless — is in {ref}`payload-range`.
```

Die Begründung steht **nicht** in `payload-range`. `payload-range` ist die
Reference-Tabelle und schließt mit dem Satz „For why the range is drawn here
and not wider, see {ref}`canonicalization`"; die Erklärung steht in
`canonicalization` → „The payload range is narrow on purpose", die ausdrücklich
sagt: „`payload-range` lists the restrictions as facts … This section is the
other half: each exclusion has its own reason". Der Kommentar schickt den Leser
in die Tabelle und sagt ihm, die Begründung stehe dort.

Das ist der schwerste Befund, aus drei Gründen: der Kommentar ist **neu in
diesem Commit** (er nimmt die gestrichene Begründung aus der Fehlermeldung
auf), er ist der einzige Ort, an dem die Begründung dieser Meldung jetzt noch
steht, und er behauptet über seine Zielseite etwas, das die Zielseite selbst
dementiert. Fix: `{ref}`canonicalization``.

### H2 — `src/previously/storage/postgres.py:6`

```
Deliberately narrow ({ref}`module-boundaries`): no update, no delete, no
transaction control to the outside, no SQL passthrough, no returning of
database objects.
```

Vorher: „(§5 der Architektur)". Dort steht der Satz wörtlich: „Fünf
Eigenschaften, die diese Schnittstelle **nicht** hat und bewusst nicht haben
darf: kein Update, kein Delete, keine Transaktionssteuerung nach außen, kein
SQL-Durchlass, keine Rückgabe von Datenbankobjekten", mit der Begründung
„Schmal, damit sie hält". `module-boundaries` argumentiert **keine** der fünf —
gemessen: „no update", „no delete", „passthrough", „database objects" haben im
ganzen `docs/`-Baum null Treffer. Die Seite argumentiert Schichtordnung,
Kanten und Ausnahmen, also *welche Modul-Importe* erlaubt sind, nicht *welche
Methoden* die Schnittstelle hat.

Das ist §10.1 in grün: dort ist das Argument auch im eingefrorenen Bericht
geblieben, und der Umsetzer hat die Zitierung richtig als
„architecture §10.1, frozen design record" markiert. Hier hat er dieselbe Lage
anders behandelt. Fix: dieselbe Behandlung wie §10.1 — und die Tabellenzeile
„§5 | architecture | {ref}`module-boundaries`" in `design-records.md` mit.

### H3 — `tests/test_hashing.py:49`

```
The hashed form is ISO 8601 ({ref}`timestamps`), and that wants four
digits of year.
```

Vorher: „§3.3 prescribes ISO 8601". §3.3 „Zeitstempel" hat zwei Hälften: die
Hashform („ISO 8601, UTC, exakt sechs Nachkommastellen, `Z`-Suffix") und
„`recorded_at` wird vom Aufrufer gesetzt". `timestamps` trägt die zweite und
verweist für die erste ausdrücklich weiter: „Inside the hash the timestamp is a
canonical string, and {ref}`hash-format` holds its exact shape." Gemessen steht
die Form nur in `hash-format.md:78`. Die einzige Zitierung des Paragraphen
greift also die falsche der zwei Hälften — obwohl die Abbildungstabelle die
richtige benennt. Fix: `{ref}`hash-format``.

Nebenbei der Modalitätswechsel, nach dem ausdrücklich gefragt war: aus
„prescribes" wurde „is". Hier ist das **unschädlich**, weil die neue Fassung
eine Tatsache über den Code behauptet und nicht über ein Dokument — und die
Doku ist nach der Kopfzeile ohnehin die maßgebliche Quelle. Die drei Stellen,
die wirklich *über das Dokument* sprechen (§3.4 „prescribes `payload IS NULL`",
§4.2 „said ‚no retry'", §11/§12), haben ihre Nummer **und** ihr Verb behalten.
Gemessen gibt es keine Stelle, an der ein „schreibt vor" zu einem „erklärt"
geworden ist, ohne dass die Nummer mitgegangen ist. Das ist sauber gemacht.

### M1 — `src/previously/core/append.py:74`

„Backing off between the attempts ({ref}`conflict-classes`, review finding W3):
the bounds double … 0.005 … 0.2" — die acht Schranken, das Full-Jitter-Argument
und die Summe 0,715 s stehen im Abschnitt „The indexes are the serialization",
nicht in `conflict-classes` (Zeile 69 ff.). Richtiges Ziel: `concurrency`.

### M2 — `src/previously/core/append.py:427`

„(`insert_event(..., key=None)`, which the contract permits, see
{ref}`hash-chain`)" — der ganze Kommentarblock (vier Vorbedingungen, die vierte
von einem Prüfer gegangen) steht in `concurrency` → „The source-key branch
doesn't back off", dort sogar mit derselben Formulierung: „an event written
*without* a source attribution, **which the contract permits**". `hash-chain`
ist nicht falsch (es trägt den schlüssellosen Fall), aber es ist nicht die
Seite, die diesen Kommentar trägt. Zugleich ist das der Satz, in dem der
Umsetzer über den Verweis hinaus den Begründungstext geändert hat („§5 permits"
→ „the contract permits"); die Änderung macht die Aussage richtiger und ist
gemeldet — sie zeigt aber, dass hier das Ziel nachgezogen gehört.

### M3 — `tests/test_verify.py:268`

„the canonicalisation rejects it ({ref}`payload-range`), because its rendering
is language-dependent" — die Zurückweisung steht in `payload-range`, die
Sprachabhängigkeit in `canonicalization`. Dieselbe Trennung wie H1, nur in
einem Kommentar, der die Begründung schon selbst trägt. Schwach, aber dieselbe
Ursache.

### M4 — `tests/test_append.py:535`, beschädigter Satz

Vorher: „idempotency **between** calls stays, and that is §5's whole point."
Jetzt: „idempotency **between** calls stays, and that is the whole point of it
({ref}`canonicalization`)." Das „it" hat kein Bezugswort mehr; der nächste
Kandidat ist „idempotency between calls", womit der Satz zirkulär wird. Das
Ziel trägt („The wanted property is idempotency *between* calls"), die Prosa
nicht. Vorschlag: „…stays, which is what the idempotency is for
({ref}`canonicalization`)."

### Was ich nachgemessen und **richtig** befunden habe

- **F1 gegengemessen:** mit `"src/previously/cli.py" = ["T201"]` entfernt
  meldet ruff in der Kopie **13** T201 — und `grep -c "print("` in `cli.py`
  ergibt ebenfalls 13, auf genau den Zeilen, die der Bericht nennt. Die
  Korrektur „nine → thirteen" stimmt, der neue Kommentar ist wahr und trägt die
  Messung bei sich.
- README: „§11 … states which forgeries are covered and which are not" →
  „[About the hash chain] states …". Die Seite trägt es („What the chain has to
  cover" plus „What the chain doesn't cover" mit den drei Manipulationen).
  Modalität bleibt, weil es von Anfang an eine Feststellung war und keine
  Vorschrift. Richtig umgezogen; die Tabellenzeilen sind als eingefrorene
  Berichte markiert.
- Die zwei Prosa-Sätze in den How-tos sind in `{ref}`-Verweise auf
  `hash-chain` bzw. `backup-encryption` umgewandelt (Schritt 3), und `grep`
  findet keine weiteren Sätze dieser Form.
- `hashing.py:131`: „The event hash after §3.1." → „The event hash as
  {ref}`hash-format` defines it." Das ist eine **Verbesserung**: die
  Reference-Seite als definierende Quelle zu benennen, ist genau die
  Vorrangregel der Kopfzeile, zu Ende gedacht.
- Die Docstrings landen nicht in der Programmausgabe: `cli.py` baut seinen
  `ArgumentParser` ohne `description=__doc__`, und es gibt kein autodoc. Die
  `{ref}`-Marker in Docstrings sind also nirgends sichtbarer Unsinn.

---

## 6. Der Quadrant von `docs/explanation/design-records.md`

**Explanation ist richtig; der Plan hat nicht geirrt.** Vier Gründe, in
Reihenfolge ihres Gewichts:

1. **Die Tabelle ist ohne das Argument um sie herum nicht benutzbar.** Wer mit
   einem `§4.2` in der Hand nachschlägt, findet zwei Antworten — eine Seite und
   einen eingefrorenen Bericht — und welche von beiden gilt, entscheidet die
   Zwei-Klassen-Regel, die ein Argument ist und keine Tatsache. Die Tabelle
   nach Reference zu heben, hieße, die Zeilen von der Regel zu trennen, die
   sie lesbar macht. Das ist genau der Fehler, gegen den diese Aufgabe
   geschrieben ist.
2. **Das Nachschlagbare an der Seite ist nicht lebendig.** Eine Reference-Seite
   wird gegen den Code gepflegt; diese Tabelle wird gegen nichts gepflegt — die
   zwanzig Paragraphen sind eingefroren, und die nächste Stufe bringt einen
   neuen Spec mit neuen Seiten, nicht neue Zeilen hier. Eine Reference-Seite,
   die sich nie ändern kann, ist keine Reference, sondern ein Protokoll.
3. **Das Publikum ist das von Explanation.** Niemand, der das System bedient,
   braucht die Seite. Sie wird von zwei Lesern gebraucht: wer im Code über ein
   `§` stolpert, und wer wissen will, warum drei deutsche Dokumente im
   Repository liegen. Der zweite will Verständnis, nicht eine Tabelle, und der
   erste braucht beides.
4. **Drei der vier Abschnitte sind reine Erklärung**, und zwar gute: „Freezing
   is a step in a procedure, not a state" (die Prozess-Einsicht des
   Auftraggebers), „What a frozen record is still good for" (warum Provenienz
   von keiner gepflegten Seite geliefert werden kann — das Argument mit der
   verworfenen Route, die eine Erklärung fallen lassen muss) und „Two kinds of
   citation". Das Argument dominiert, die Tabelle dient ihm.

Zwei Verbesserungen, die den Quadranten nicht anfassen:

- Die Tabelle liegt in der Mitte der Seite, ohne Wegweiser. Ein Satz oben
  („Wer von einer Paragraphennummer in einem Kommentar hierher kommt: die
  Tabelle unten ist die Karte") kostet eine Zeile und bedient den
  nachschlagenden Leser, ohne der Erklärung etwas zu nehmen.
- Auf `design-records` zeigt gemessen **nichts** (Befund N2). Eine
  Explanation-Seite, die nur über den Toctree erreichbar ist, während 57
  Code-Verweise ihre Regel benutzen, ist unterverlinkt.

---

## 7. Befunde nach Schwere

### Vor dem Merge zu beheben

- **H1** `canonical.py:49–53` — der neue Kommentar behauptet, die Begründung
  des Float-Verbots stehe in `payload-range`; sie steht in `canonicalization`,
  und `payload-range` verweist dorthin. Fix: ein Label.
- **H2** `postgres.py:6` + die Tabellenzeile „§5 | architecture" — zeigt auf
  eine Seite, die keine der fünf Negativ-Eigenschaften argumentiert (gemessen:
  null Treffer in `docs/`). Richtig wäre die Behandlung von §10.1:
  „architecture §5 (frozen design record)".
- **H3** `test_hashing.py:49` — zeigt auf `timestamps`, das die ISO-8601-Form
  ausdrücklich an `hash-format` weiterverweist. Fix: `{ref}`hash-format``.
- **H4** Markup-Defekt auf der Seite, die die Konvention definiert.
  `design-records.md` schreibt ``as `{ref}`label``,`` — gerendert kommt heraus:
  `{ref}` als Code, dann `label`, dann zwei stehengebliebene Rückstriche
  (gemessen in `docs/_build/html/explanation/design-records.html`:
  `<code>…{ref}…</code>label``, and the gate in`). Sphinx warnt nicht, weil es
  kein Verweis ist, nur Text. Richtige Form sind doppelte Rückstriche außen.

### Sollte hinein, kostet wenig

- **M1** `append.py:74`: Backoff-Schranken → `concurrency`, nicht
  `conflict-classes`.
- **M2** `append.py:427`: der Unerreichbarkeits-Kommentar → `concurrency`.
- **M3** `test_verify.py:268`: die Sprachabhängigkeit → `canonicalization`.
- **M4** `test_append.py:535`: „the whole point of it" ohne Bezugswort.
- **M5** Das Tor deckt die druckende Datei nicht ab: `RUNTIME_MESSAGE_FILES`
  nennt zwei Pfade, `cli.py` mit dreizehn `print`-Aufrufen fehlt (Angriff 4b
  gemessen grün). Über `src/**/*.py` laufen lassen.
- **M6** `test_the_reference_quotes_what_the_code_actually_prints` prüft nur
  eine Richtung: die Seite darf Meldungen zitieren, die niemand druckt
  (Angriff 6), und das Zitat aus der Tabelle herausnehmen (Angriff 7). Beide
  Mengen gleichsetzen statt Teilmenge prüfen.
- **M7** `REFERENCE` sieht nur `[a-z0-9-]` und nur die Grundform; ein Vertipper
  mit Unterstrich und die Form mit explizitem Titel sind unsichtbar (Angriffe
  11 und 12).
- **M8** Der `SELF`-Ausschluss ist vermeidbar. Der dritte Weg ist in der Kopie
  gefahren: vier Tests grün, ruff grün, Loch zu, Messung in der Dokumentation
  erhalten.
- **M9** `DEPENDENCIES.md`: der Absatz behauptet pauschal frozen, obwohl §2 in
  der verlinkten Tabelle auf `module-boundaries` abgebildet ist; und 11 der 13
  Zitierungen der Seite stehen in jener Tabelle gar nicht.

### Kleinigkeiten / Zahlen

- **N1** Die Kopfzeile nennt nur `docs/explanation/`, obwohl 17 der 58
  Verweise nach `docs/reference/` zeigen; und sie steht unqualifiziert über
  Entwurf und Architektur, deren Mehrheit keine Explanation-Seite hat.
- **N2** Gemessen zeigt auf fünf Label nichts, nicht auf vier: zusätzlich zu
  `hash-domain`, `add-a-migration`, `first-event-tutorial`,
  `restore-from-a-backup` auch auf **`design-records` selbst** (der Link aus
  `DEPENDENCIES.md` ist ein Pfad-Link, kein `{ref}`). Und es sind 20 Label, nicht
  19.
- **N3** A11 zählt „neun wörtlich derselbe Satz" — gemessen achtmal (13
  Vorkommen auf 12 Zeilen, zehn in Zellen, drei in Prosa).
- **N4** Der Bericht behauptet „Benutzt werden 15 davon" — gemessen sind es
  **12** verschiedene Label aus dem Code.
- **N5** Die Tabelle im Bericht und die auf der Seite weichen ab (§3.3
  Zweitziel); Bedenken 5 zählt fünf Paragraphen mit Zweitziel, die Seite hat
  sechs, und §3.1 hat drei Ziele.
- **N6** Die Markierungspflicht gilt nach dem Brief für jede
  englischsprachige Datei; das Tor prüft `.py` unter drei Verzeichnissen
  (Angriff 8: nackte Zitierung in `pyproject.toml` grün).
- **N7** `_docstrings()` kennt `ast.AsyncFunctionDef` und Attribut-Docstrings
  nicht. Heute unerreichbar (das Projekt ist bewusst synchron), aber eine
  Zeile.

---

## 8. Bedenken

1. **Die drei H-Befunde haben dieselbe Ursache, und sie wird wiederkommen.**
   In allen drei Fällen hat eine Spec-Stelle zwei Hälften, die die Doku auf
   zwei Quadranten getrennt hat — Tatsache nach Reference, Begründung nach
   Explanation —, und der Verweis hat die falsche Hälfte erwischt. Die
   Abbildungstabelle hat in zwei der drei Fälle die richtige Antwort schon
   dastehen (§3.3 nennt `hash-format`, §3.1 nennt alle drei Ziele); benutzt
   wurde sie nicht. Für die nächste Stufe ist das die lehrreiche Stelle: die
   Tabelle je **Zeile** anwenden, nicht je Paragraph, so wie die Klassenregel
   es für frozen/lebendig schon fordert.
2. **Die Prüfung, die den Umsetzer entlastet hätte, ist nicht gebaut.** Ein
   Test „jedes Label wird mindestens einmal angesprochen" (Bedenken 1 des
   Berichts) hätte H2 nicht gefunden, aber ein Test „jedes Label, das ein
   Code-Verweis nennt, steht auf der Seite, deren Abschnitt die Zitierung
   behauptet" ist nicht automatisierbar. Das heißt: die drei H-Befunde sind
   genau die Klasse, für die es kein Tor gibt, und sie sind der Grund, warum
   diese Prüfung von Hand laufen musste. Das ist kein Vorwurf, sondern die
   Begründung dafür, die nächste Einfrier-Runde wieder so zu prüfen.
3. **Nach dem Einfrieren ist der Rückweg teurer als heute.** Solange die
   Markierung `(frozen design record)` neu ist, kostet eine Korrektur eine
   Zeile. Sobald eine zweite Stufe auf diesen 58 Verweisen aufbaut, wird aus
   dem falschen Zeiger eine Konvention. H2 ist der Fall, bei dem das weh tun
   würde: er behauptet, eine Begründung sei in die Doku gewandert, die nie
   geschrieben wurde — und ein späterer Leser, der sie dort nicht findet,
   schreibt sie neu, statt den eingefrorenen Bericht zu lesen.
4. **Der Worktree-Pfad in der Tutorial-Ausgabe** (Bedenken 3 des Berichts)
   bleibt offen und ist richtig gemeldet. Nach dem Merge wäre ein Lauf aus dem
   Hauptcheckout die ehrlichere Ausgabe; wer das entscheidet, entscheidet
   zugleich, ob `test_docs_typed_output` die Zeile `rootdir:` überhaupt prüfen
   soll.
5. **`(frozen design record)` auf derselben Zeile** (Bedenken 4) halte ich wie
   der Umsetzer für den richtigen Tauschhandel. Eine absatzweise Prüfung wäre
   freundlicher und deutlich schwerer korrekt hinzuschreiben — und die
   Zeilenprüfung hat einen Nebennutzen, der in der Diskussion fehlt: sie
   erzwingt, dass Nummer und Markierung beim Umbrechen nicht
   auseinanderlaufen. Was sie nicht erzwingt: eine Zeile mit **zwei**
   Zitierungen, von denen nur eine eingefroren ist, geht komplett durch. Im
   Baum gibt es diese Zeile nicht mehr (`test_schema.py:111` ist getrennt
   worden), aber sie ist wieder schreibbar.
