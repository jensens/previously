# Aufgabe 6 — Prüfung: Explanation, Teil 2 (Nebenläufigkeit, Grenzen, Backups)

Geprüft wurde `ed84bf5` gegen `a816d4f`, im Worktree
`.claude/worktrees/stufe-1a-log`. Kein Code und keine Doku angefasst; alle
Messungen liefen gegen Kopien im Scratchpad oder lesend gegen den Baum.
`git status` nach der Prüfung: nur `docs/superpowers/plans/2026-10-03-dokumentation.md`
geändert, und das war es schon vorher (ein neuer Abschnitt zu Aufgabe 7, nicht
von mir).

**Urteil: nicht freigegeben.** Vier Befunde mittlerer Schwere müssen vor dem
Einfrieren weg, dazu vier kleinere. Die Überlebensliste ist vollständig
abgearbeitet — kein verlangter Punkt fehlt, keine Begründung ist verloren. Die
Befunde sind alle von derselben Art: eine Zahl oder eine Zusage, die mehr
behauptet, als die Messung dahinter deckt.

---

## 1. Die Überlebensliste, Punkt für Punkt

Alle Zeilenangaben auf den Stand `ed84bf5`.

### Schritt 1 — `concurrency.md`

| Verlangt | Gefunden | Vollständig? |
|---|---|---|
| Die zwei Unique-Indexe als **gesamte** Nebenläufigkeitssteuerung, kein Advisory-Lock, kein `FOR UPDATE`, keine Koordination | `concurrency.md:6-7`, `:12-15` | ja |
| Der Verlierer liest neu und wiederholt, mit Zurückweichen, Begründung gegen ein festes Intervall (Gleichschritt) | `concurrency.md:46-50` | ja, aber die **Zahlen falsch** → Befund 1 |
| `READ COMMITTED` ausdrücklich, unter `SERIALIZABLE` andere Fehlerklasse | `concurrency.md:41-44` | ja |
| Warum `NULLS NOT DISTINCT` nicht optional ist (mehrere `NULL` sonst verschieden, Genesis-Verzweigung) | `concurrency.md:55-66` | ja, samt PG-15-Boden und Rückverweis auf die `id = 0`-Messung |
| Drei Konfliktklassen, **zwei** Wiederherstellungen | `concurrency.md:67-77` | ja |
| Warum welcher Index zuerst anschlägt an der Index-OID-Reihenfolge hängt, darum alle drei derselbe Fehler | `concurrency.md:85-105` | ja, mit Messblock und `REINDEX`/`pg_repack`-Begründung |
| `event_kind_check` bleibt unübersetzt | `concurrency.md:107-110` | ja |
| Der Quellschlüssel-Zweig weicht nicht zurück: Verletzung erst **nach** dem Commit, vorher blockiert der Duplikat-INSERT, kein Partner im Gleichschritt | `concurrency.md:112-123` | ja |
| Der Teiltreffer, die kürzere Liste wäre still falsch | `concurrency.md:135-151` | ja, mit `{ref}`silent-losses`` |
| Stapeln als Mittel gegen Konkurrenz, Verhungern möglich, `MAX_BATCH`, `MAX_RETRIES`, ein einziger Anfüge-Prozess statt Sperre | `concurrency.md:153-168` | ja |
| `sequenceDiagram` (Planvorgabe), `:caption:`, Prosa davor, kein `:alt:` | `concurrency.md:17-39` | ja |

### Schritt 2 — `module-boundaries.md`

| Verlangt | Gefunden | Vollständig? |
|---|---|---|
| `cli` → `core` → `storage` → `contract`, als Verträge geprüft | `module-boundaries.md:6-8`, `:44-55` | ja, die vier Namen wörtlich wie die Torausgabe |
| Warum die beiden Ausnahmen **namentlich** und nicht gemustert, samt Wegwerfmodul-Messung (Wildcard lässt neue Kante lautlos durch) | `module-boundaries.md:84-123` | ja, Messblock von mir nachgefahren und exakt bestätigt |
| Warum es den Riegel im Testlauf gibt (Ausnahme hängt an der Kante, nicht an TYPE_CHECKING) | `module-boundaries.md:125-148` | ja, aber die Alleinstellung des Riegels **überzogen** → Befund 4 |
| Ein `LogStore[Conn]`-Protokoll macht die Ausnahmen **ersatzlos** entbehrlich | `module-boundaries.md:150-158` | ja, samt `storage.rows` als unbedenkliche Typquelle |
| `graph TD` mit **gestrichelten** Ausnahmen (Planvorgabe), `:caption:`, Prosa davor, kein `:alt:` | `module-boundaries.md:15-31` | ja, genau zwei gestrichelte Kanten |
| (Zusatz aus Architektur §2/§10.1, nicht im Brief verlangt) Zweck der Grenzen, `contract` als eigenes Modul, zwei absichtliche Abweichungen | `:10-13`, `:57-82` | ja |

### Schritt 3 — `backup-encryption.md`

| Verlangt | Gefunden | Vollständig? |
|---|---|---|
| Hetzner hat **gar keine** Verschlüsselung im Ruhezustand, nur SSE-C beim Hochladen | `backup-encryption.md:10-18`, Zitat als Blockquote | ja |
| SSE-C bricht bei Kopien, Ursache Ceph; operativ schon aufgeschlagen (kup6s, `501` auf Tagging) | `backup-encryption.md:20-30` | ja |
| barman-cloud kann clientseitig nicht; die Datenbank läge im Klartext im Bucket | `backup-encryption.md:32-36` | ja |
| Der Preis der Passphrase | `backup-encryption.md:82-93` | ja, inklusive „vor dem ersten Backup" und dem ungeprüften Schlüssel |
| Die drei Wege A/B/C samt Preis, A gewählt wegen *wer den Schlüssel hat* | `backup-encryption.md:108-123` | ja |
| Was A umstoßen würde, samt dem Hinweis, dass die Prüfung nicht geführt ist | `backup-encryption.md:125-131` | ja |
| (Zusatz) Pluginstand datiert, kein „bewährt gegen neu", Schlüsselablage, zwei verbleibende Einwände | `:42-80`, `:95-106`, `:133-143` | ja |

### Schritt 4 — Nutzlastbereich in der Reference

| Verlangt | Gefunden | Vollständig? |
|---|---|---|
| Abschnitt in `docs/reference/hash-format.md` | `hash-format.md:9-33`, Label `(payload-range)=` | ja |
| Die fünf Einschränkungen als Tatsachen | `hash-format.md:20-26`, fünf Zeilen | ja |
| Je Zeile die Fehlermeldung aus `core/canonical.py`, **abgelesen** | `hash-format.md:22-26` | ja — alle fünf plus die Typmeldung von mir durch Aufruf des Codes reproduziert, byteidentisch |
| `^[a-z][a-z0-9_]*$` und `±(2**53 − 1)` wandern aus der Explanation in die Reference | je **genau einmal** im Baum, in `hash-format.md:23` und `:24` | ja |
| `canonicalization.md` verweist dorthin und behält die Begründung | `canonicalization.md:30`, `:44`, `:49` | ja, beide Begründungsabsätze unverändert |

### Schritt 5 — die fünf stillen Datenverluste

| Verlangt | Gefunden | Vollständig? |
|---|---|---|
| Seite `silent-losses.md`, Label `(silent-losses)=` | `silent-losses.md:1` | ja |
| 1. Reservierter Schlüssel `evidence`, nicht nachtragbar | `silent-losses.md:12-16` | ja |
| 2. CRLF, eine Einheit statt vieler, Zuordnungsmodell ausgehebelt | `silent-losses.md:18-23` | ja, mit dem Hash-Argument zum stehengelassenen `\r` dazu |
| 3. Einheiten und Quellenangabe nicht gedeckt, drei gemessene Fälschungen | `silent-losses.md:25-30` | ja, mit Gegenprobe |
| 4. JSON-`null` als Grabstein, für die Grabstein-Abfrage unsichtbar | `silent-losses.md:32-37` | ja |
| 5. Doppelter Quellschlüssel im Stapel, zwei `id`s für einen Eintrag | `silent-losses.md:39-56` | ja, mit Messblock |
| Das Verbindende: **keiner ein Programmierfehler**, Lücke zwischen Zusage und Wirklichkeit, durch Messen gefunden, unwiederbringlich | `silent-losses.md:58-78` | ja — aber drei Präzisionsmängel → Befunde 5, 6, 7, 8 |
| Die zwei Verweise lösen auf | `hash-chain.md:197`, `canonicalization.md:71` | ja |
| Kein Diagramm (Planvorgabe: ausdrücklich keines auf diesen Seiten) | — | ja |

### Schritte 6 und 7

Toctree: vier Einträge angefügt, die zwei bestehenden unberührt
(`explanation/index.md:8-13`). Commit-Titel wörtlich wie verlangt,
Trailer `Assisted-By: Claude Opus 5` — die Regel aus CLAUDE.md ist eingehalten,
kein `Co-Authored-By:`, kein „Generated with".

---

## 2. Jede Zahl gegen den Code

### Falsch

**Befund 1 (mittel) — `concurrency.md:49`, die Backoff-Rechnung.**

> „Eight attempts is the limit, so the worst case is seven waits with every one
> of them at the cap—under a second in total"

Gemessen mit einem Stub-Storage, der `ChainPositionTaken` wirft, und gezählten
`time.sleep`-Aufrufen:

```
raised: ChainConflict chain position not acquired after 8 attempts
MAX_RETRIES: 8
number of sleeps performed: 8
upper bound per attempt: [0.005, 0.01, 0.02, 0.04, 0.08, 0.16, 0.2, 0.2]
sum of all eight upper bounds: 0.715
sum of the first seven: 0.515
seven times the cap: 1.4
attempts whose bound equals the cap: [6, 7]
```

Drei Fehler in einem Satz:

1. **Acht Wartezeiten, nicht sieben.** Der `ChainPositionTaken`-Zweig
   (`core/append.py:460-466`) schläft nach *jedem* gescheiterten Versuch, den
   achten eingeschlossen, und fällt erst danach aus der Schleife in
   `raise ChainConflict`. Die letzte Wartezeit ist nutzlos, aber sie findet
   statt.
2. **Nicht „jede am Deckel".** Nur die Versuche 6 und 7 erreichen `0.2`;
   `0.005 * 2**5 = 0.16` liegt darunter.
3. **Der Satz widerspricht sich selbst.** Sieben Wartezeiten am Deckel wären
   `7 × 0.2 = 1.4 s`, also *über* einer Sekunde — während derselbe Satz „under
   a second" sagt. Richtig ist der Schluss, nicht die Begründung: der
   schlechteste Fall summiert sich auf `0.715 s`.

Die Formulierung ist aus dem Kommentar in `src/previously/core/append.py:73-77`
übernommen, der denselben Fehler macht („seven waits between eight attempts,
every one of them at the cap"). Das ist genau die Fehlerart, die diese Prüfung
sucht: eine Zahl aus einer Quelle übernommen statt nachgezählt.

Kleinste heilende Formulierung:

> Eight attempts is the limit, and the waits grow until they hit the cap:
> 0.005, 0.01, 0.02, 0.04, 0.08, 0.16 and then 0.2 seconds, so even the worst
> case stays under three quarters of a second — long enough to bring two
> writers out of step, short enough not to slow the test suite down.

(Der Kommentar im Code trägt denselben Fehler. Eine Dokuseite, die ihn
korrigiert, während die Quelle ihn behält, ist die nächste Drift; das gehört in
die Rückmeldung, auch wenn Aufgabe 6 keinen Code anfasst.)

**Befund 3 (mittel) — `module-boundaries.md:37`, „half of the permitted edges".**

> „whether an edge exists is a separate question, and here half of the
> permitted edges simply don't."

Gemessen am Importgraphen (`grep` über alle `from previously…`-Zeilen in
`src/`): die Schichtenordnung erlaubt sechs Kanten — `cli→core`, `cli→storage`,
`cli→contract`, `core→storage`, `core→contract`, `storage→contract`. **Fünf
von sechs existieren.** Einzig `storage → contract` nicht. „Die Hälfte" stimmt
unter keiner Zählweise (nur die benachbarten Kanten gezählt: eine von drei).

Kleinste heilende Formulierung: `…and here one of the six the layer order
permits — `storage → contract` — simply doesn't.`

### Richtig, selbst nachgemessen

| Zahl / Wert | Seite | Gegen was geprüft | Ergebnis |
|---|---|---|---|
| `MAX_RETRIES = 8` | `concurrency.md:164` | `core/append.py:59` | stimmt |
| `MAX_BATCH = 500` | `concurrency.md:164` | `core/append.py:64` | stimmt |
| `[0, 0.005 * 2**attempt]`, Deckel `0.2` | `concurrency.md:47` | `BACKOFF_BASIS`, `BACKOFF_CAP`, `backoff_delay` | stimmt |
| Elf Hash-Felder heute, acht vorher | `silent-losses.md:27`, `:30` | `core/hashing.py:140-152` (11 Schlüssel), Spec §1.1 Nr. 7 / K1 | stimmt |
| Drei Beschränkungsnamen in `_CHAIN_POSITION_CONSTRAINTS` | `concurrency.md:83` | `storage/postgres.py:55` | stimmt (vierter Name `source_key_pkey` separat) |
| Vier Module | `module-boundaries.md:6` | `cli`, `core`, `storage`, `contract` | stimmt — und `previously.cli` ist die oberste Schicht des `layers`-Vertrags, was Spec §8 verschweigt |
| Vier Verträge, Namen wörtlich, `2 ignored imports` zweimal, `4 kept, 0 broken` | `module-boundaries.md:48-55` | eigener `uv run lint-imports` | zeichengleich |
| Zwei ignorierte Importe je Vertrag | `module-boundaries.md:86-91` | `.importlinter`, beide `ignore_imports`-Blöcke | stimmt |
| PostgreSQL-15-Boden; Klausel kam mit 15 | `concurrency.md:64` | `reference/configuration.md:16` | stimmt |
| „a real PostgreSQL 17" | `concurrency.md:87` | `tests/conftest.py:23,54` → `postgres:17` | stimmt |
| `NULLS NOT DISTINCT` auf `event_prev_hash_idx` | `concurrency.md:57` | `storage/schema.py:91-95`, `migrations/versions/0001_log.py:71-79` | stimmt |
| Messblock „fresh id and the tip's hash" → `ChainPositionTaken('event_hash_idx')` | `concurrency.md:90-91` | `tests/test_storage.py:307-334`, `_row(1, None)` hat `hash=b"\x01"*32` | stimmt |
| Messblock „tip's id and tip's hash and a foreign prev_hash" | `concurrency.md:93-96` | `tests/test_storage.py:338-363` | stimmt, inklusive „`event_prev_hash_idx` not" |
| `event_kind_check`-Test verneint `StorageError` namentlich | `concurrency.md:110` | `tests/test_storage.py:366-394` | stimmt |
| Kette `IntegrityError` → aus `core` heraus → Stapelspur beim Benutzer | `concurrency.md:103` | `storage/postgres.py:177-183` (`raise`), `core/append.py:460`, `cli.py:207` (`except (PreviouslyError, StorageError)`) | stimmt |
| Quellschlüssel-Probe: `SourceKeyTaken(source_key_pkey)`, kein Warten, drei Transaktionen, je eine `int` | `concurrency.md:123` | `core/append.py:448-451` | stimmt (historische Probe, hier nicht nachfahrbar; Wortlaut deckungsgleich) |
| „one user and six processes" | `concurrency.md:165` | `architektur.md:1382` | stimmt |
| Wildcard-Messung `KEPT (3 ignored imports)` / benannte Kanten `BROKEN (2 ignored imports)` | `module-boundaries.md:101-111` | von mir nachgefahren, Wegwerfmodul in einer Scratchpad-Kopie des Baums | stimmt, beide Hälften zeichengleich |
| Verneinungs-Messung `previously.cli -> previously.storage.postgres (l.21, l.22)` | `module-boundaries.md:69-75` | eigener Lauf, s. Abweichung C unten; `cli.py:21-22` | stimmt |
| Die fünf Fehlermeldungen des Nutzlastbereichs | `hash-format.md:22-26` | `core/canonical.py` durch Aufruf | zeichengleich, inklusive `±9007199254740991`, `^[a-z][a-z0-9_]*$`, `surrogates not allowed` |
| `MAX_SAFE_INT`, Vergleich `abs(value) <= …` | `hash-format.md:24` | `core/canonical.py:37,45` | stimmt |
| Elf von fünfzehn Vokabeleinträgen klein | `.vale.ini` | `accept.txt`: 15 Zeilen, 11 klein | stimmt; der alte Satz „nine of the eleven" war tatsächlich zehn von elf |

### Nicht nachmessbar — ausdrücklich offen

Die Tabelle in `backup-encryption.md:57-64` und die pgBackRest-Pflegeprüfung in
`:77-80` stammen aus der GitHub-API vom 2026-10-03. **Der GitHub-MCP-Server
ist in dieser Sitzung nicht verbunden** (`plugin:github:github (400):
Authorization header is badly formatted`), also habe ich diese Zahlen *nicht*
gegen GitHub geprüft und rate sie nicht.

Gegen die im Brief genannte Quelle — Architektur §10.5, `architektur.md:1179-1213`
— sind sie vollständig und zeichengenau übernommen: 2 gegen 30 Commits seit
03.07.2026, v0.0.3 (25.06.) gegen v0.8.0 (25.08.)/v0.7.0/v0.6.1, 23 gegen 44
offene Vorgänge, README „EXPERIMENTAL"; `archived: false`, letzter Push
02.10.2026, 24 Commits in 30 Tagen, drei Freigaben 2.59.0/2.59.1/2.59.2 mit
27.09. als letzter; `barmanObjectStore` seit CNPG 1.26 abgekündigt, Entfernung
mit 1.30, Operas Plugin ab CNPG 1.25. Dass die Seite „Collect that table again;
don't read this one" sagt, ist der richtige Umgang mit Zahlen dieser Art.

---

## 3. Die Unstimmigkeit in `silent-losses.md` — Befund 5

**Sie bricht.** Das „as it was about" trägt nicht als Beispiel.

`silent-losses.md:62`:

> „where the specification was silent—as it was about the key collision and
> about the duplicate inside a batch—the gap had no owner at all."

`silent-losses.md:21`:

> „The splitting rule said nothing about line endings"

Nachgeprüft, ob der CRLF-Fall wirklich ein Schweigen ist: Spec §6
(`stufe-1a-log.md:766-783`) führt die Zerlegung in **vier** Schritten auf, keiner
nennt Zeilenenden; „CRLF" kommt im gesamten 1a-Spec nicht vor; die Normalisierung
steht allein im Code (`core/units.py:32` samt Docstring). Es ist also ein
Schweigen, und zwar ein drittes.

Warum die Apposition nicht als Beispiel durchgeht, in drei Schritten:

1. **Grammatisch** ist „as it was about A and about B" eine Beisetzung, die
   identifiziert, welche Fälle gemeint sind — nicht eine, die illustriert.
   Illustrieren würde „as with the key collision" oder „as it was, for
   instance, about …". Der Gedankenstrich verstärkt das: er schiebt eine
   Erläuterung ein, keine Auswahl.
2. **Die Seite ist eine Zählseite.** Ihr Titel nennt die Fünf, ihr Zweck ist,
   eine Zahl auflösbar zu machen, und ihr letzter Abschnitt heißt sinngemäß
   „warum die Zahl überhaupt zählt". Auf so einer Seite rechnet ein Leser mit,
   und hier rechnet er: zwei Schweigen, also drei falsche Zusagen. Gemessen
   sind es mindestens drei Schweigen.
3. **Der Satz ist eine Zweiteilung**, die alle fünf erschöpfen soll („where the
   specification was wrong … where the specification was silent …"). Eine
   Zweiteilung mit einer namentlich aufgezählten Hälfte lädt dazu ein, die
   andere Hälfte durch Abzug zu bilden. Genau das führt in die Irre.

Kleinste heilende Formulierung — das dritte Schweigen dazuschreiben statt die
Aufzählung aufzuweichen, weil ein „for instance" den Leser wieder zählen lässt:

> where the specification was silent—as it was about the line endings, about
> the key collision and about the duplicate inside a batch—the gap had no owner
> at all.

Damit geht die Rechnung auf: drei Schweigen, zwei Fälle, in denen die
Spezifikation etwas Falsches sagte (der Hash-Bereich und die Grabstein-Naht) —
und zur zweiten Hälfte siehe Befund 8.

---

## 4. Die Abweichungen C bis F

**C — „die Verneinung bricht heute" — bestätigt, und zwar wörtlich.**

Selbst gemessen mit einer Probe-Konfiguration im Scratchpad
(`previously.core`, `previously.contract`, `previously.cli` als Quellen,
dieselben zwei Ausnahmen):

```
Probe everything except storage BROKEN (2 ignored imports)

previously.cli is not allowed to import sqlalchemy:

-   previously.cli -> previously.storage.postgres (l.21, l.22)
    previously.storage.postgres -> sqlalchemy (l.23, l.24, …)
```

`cli.py:21-22` sind `from previously.storage.postgres import from_dsn` und
`… import PostgresStorage`, beide zur Laufzeit. Die Kette bricht also heute,
an einem Modul, das existiert, und nicht erst an einem künftigen — die Spec
(`stufe-1a-log.md:948-950`) begründet die Aufzählung nur mit dem
Zukunftsargument. Die Ergänzung ist richtig und ist kein Widerspruch zur Spec.

Die zweite Messung desselben Abschnitts habe ich ebenfalls nachgefahren, mit
einem `core/zz_probe.py` in einer **Kopie** des Baums (der echte `src/` blieb
unberührt): Wildcard → `KEPT (3 ignored imports)` auf beiden Verträgen,
`4 kept, 0 broken`; zwei benannte Kanten → `BROKEN (2 ignored imports)` mit
`previously.core.zz_probe -> previously.storage.postgres` in der Begründung.
Zeichengleich mit dem Block auf der Seite (nur die Zeilennummer der
Probendatei weicht ab, weil meine Probe anders eingerückt war — kein Befund).

Und die Nebenbemerkung der Abweichung stimmt auch: Spec §8 sagt „In 1a
existieren `core`, `storage` und `contract`" (`stufe-1a-log.md:919`), während
`previously.cli` existiert und die oberste Schicht des `layers`-Vertrags ist.
Die Seite nennt vier Module, wie der Code. Richtig entschieden.

**D — die nicht gegossene Zählung — bestätigt, die Begründung mit einer
Einschränkung.**

Nachgeprüft: `reserviert`/`Reservier` kommt in **keiner** der beiden Specs vor;
die Regel „`evidence` ist reserviert, eine Nutzlast damit wird abgewiesen"
steht nirgends in der Spezifikation, nur im Code
(`core/append.py:294-302`). Insofern trägt die Schlussfolgerung: es ist
ebenfalls ein Fall, über den nichts geschrieben stand, und „in vier von fünf
Fällen war die Spezifikation falsch" wäre falsch gewesen. Die Entscheidung,
ohne Zahl auszukommen, war richtig.

Die *Formulierung* der Abweichung ist allerdings zu stark: das Wort `evidence`
kommt im 1a-Spec zweimal vor — in einem Messblock (`stufe-1a-log.md:697`) und
als Verweis „§5.1 bezeichnet in diesem Baum die Belegart aus dem Entwurf"
(`:724`). Was fehlt, ist die *Reservierungsregel*, nicht das Wort. Für den
Bericht ist das eine Ungenauigkeit ohne Folgen für die Seite; auf der Seite
steht nichts Falsches.

**E — die Vokabelzählung — bestätigt.**

`accept.txt`: 15 nicht leere Einträge, davon 11 kleingeschrieben
(`SQLAlchemy`, `Hetzner`, `Ceph`, `Dalibo` groß). Vor dem Commit: 11 Einträge,
10 klein. Der alte Kommentar „Nine of the eleven entries are lowercase" war
also tatsächlich falsch, der neue („Eleven of the fifteen") stimmt, und dass
er die Korrektur mitnennt, ist genau richtig für eine Zahl, die schon einmal
fortgeschrieben statt nachgezählt wurde.

**F — die vier Vokabeleinträge — plausibel, nicht vollständig nachfahrbar.**

Die Zwischenstände (12 → 10 → 7 → 4 Fehler) sind Zustände, die nur während der
schrittweisen Ergänzung existierten; sie sind aus dem Endzustand nicht
rekonstruierbar, und ich habe sie nicht nachgefahren. Prüfbar und geprüft ist
das Ergebnis: vier Einträge, `Hetzner`/`Ceph`/`Dalibo` groß (also von der
`Vale.Terms`-Pinnung unbelastet), `namespace` klein und im Baum nirgends am
Satz- oder Überschriftsanfang — das deckt `make vale` mit 0 Fehlern ab. Dass
`unencrypted` durch „in the clear" ersetzt wurde statt eingetragen, ist die
richtige Richtung: ein Eintrag weniger für ein Wort ohne Fachgehalt.

*Zur Nummerierung:* die Frage nach dem reservierten Schlüssel `evidence`
betrifft **Abweichung D**, nicht F — F ist im Bericht die Vokabelliste.
Beantwortet ist sie oben unter D.

---

## 5. Der Quadrant

**Die vier neuen Seiten sind Explanation.** Sie argumentieren durchgehend:
jede Messung steht als Beleg für eine Entscheidung, nicht als nachschlagbare
Tatsache, und jede Seite nennt, was sie *nicht* leistet
(`concurrency.md:162`, `module-boundaries.md:160-162`,
`backup-encryption.md:127`, `silent-losses.md:75-78`). Kein Abschnitt ist eine
Schrittfolge, keiner eine Tabelle, die man im Betrieb aufschlägt.

Zwei Grenzfälle, beide tragbar:

- `module-boundaries.md:44-55` listet die Vertragsinhalte — das ist dem
  Material nach Reference. Es trägt hier, weil jeder Punkt unmittelbar
  begründet wird und `.importlinter` selbst die maßgebliche Quelle bleibt (die
  Namen *sind* die Torausgabe). Eine Reference-Seite für die Verträge gibt es
  nicht und braucht es nicht.
- `backup-encryption.md:57-64` ist eine datierte Erhebung in einer
  Explanation. Sie trägt, weil der Abschnitt ausdrücklich sagt, dass die
  Tabelle neu zu erheben und nicht zu lesen ist — das ist eine
  Explanation-Aussage über eine Reference-Tatsache, nicht eine
  Reference-Tatsache.

Zwei Vorschriften in `backup-encryption.md:89-93` („die Passphrase muss vor dem
ersten Backup stehen", „im Tresor, mit dokumentiertem Wiederherstellungsweg,
geprüft") sind der Form nach How-to. Kein Befund: die Passphrase-Sorgfalt steht
schon in `how-to/restore-from-a-backup.md:14-15`, und eine Einrichtungs-How-to
gibt es nicht, weil das Deployment einer späteren Stufe gehört.

**Der neue Abschnitt in `reference/hash-format.md` ist austeres
Reference-Material.** Er behauptet, er argumentiert nicht: Pflichtmenge,
Pfadaufbau, fünf Zeilen Einschränkung plus Meldung, der reservierte Schlüssel,
die Anwendung auf `source`/`external_id` — und ein einziger Satz, der die
Begründung dorthin schiebt, wo sie hingehört (`:33`,
„For why the range is drawn here and not wider, see {ref}`canonicalization`").
Genau die richtige Richtung über die Quadrantengrenze.

**Ein Satz pro Zeile: hält durchgehend.** Maschinell geprüft über alle sechs
berührten Dateien (Suche nach satzinternen Grenzen `. ` + Großbuchstabe): ein
einziger Treffer, `hash-format.md:22`, und der liegt in einer Tabellenzelle,
die sich nicht umbrechen lässt. Kein Befund, allenfalls Politur
(„Floating point numbers are not allowed; state a scale and use an integer.").

---

## 6. Was die Seiten behaupten, ohne es zu dürfen

**Befund 2 (mittel) — `reference/hash-format.md:82-85`. Der offene Fall, und er
steht noch dort.**

```{warning}
Do not recompute these values.
They are pinned in `tests/test_hashing.py`, and recomputing them to make a test
pass destroys the proof that the hash is reproducible.
```

Fixrunde 1 (`a816d4f`) hat genau diese Zusage auf der Explanation-Seite
zurückgenommen: aus „A failing pinned vector is **never** fixed by recomputing
it" wurde „almost never", samt der einen Ausnahme und dem Kennzeichen, an dem
man sie erkennt (`canonicalization.md:112-115`: eine absichtliche Änderung des
Hash-Bereichs hebt `HASH_VERSION` mit an; ein neu gerechneter Vektor neben
unveränderter Version ist die Signatur der Abkürzung).

Die Reference trägt weiter die absolute Fassung. Nach dem Einfrieren sind diese
zwei Seiten die maßgebliche Quelle für diese Disziplin, und sie widersprechen
sich: die eine verbietet, was die andere unter genannter Bedingung erlaubt.
Dass Aufgabe 6 dieselbe Datei bearbeitet und den Kasten zwölf Zeilen über dem
neuen Abschnitt stehen gelassen hat, macht es zu einem Befund dieser Aufgabe.

Kleinste heilende Formulierung — ein Satz in den Kasten:

> The one exception is a deliberate change to the hash range, which raises
> `HASH_VERSION` along with the vector; see {ref}`canonicalization`.

**Befund 4 (mittel) — `module-boundaries.md:125-148`. Der Riegel ist nicht der
einzige, der anschlägt.**

Die Seite sagt (`:128`): „Pull one of those two imports out of its
`if TYPE_CHECKING:` block and the exemption keeps covering it: `core` would
load SQLAlchemy at runtime, the separation of layers would be broken, and the
gate would report nothing." Dann (`:130`): „`tests/test_contracts.py` is the
missing gate", und (`:142`): „without it written down the test looks like
redundancy beside `lint-imports` and somebody deletes it."

Gemessen in einer Kopie des Baums, mit der **Projektkonfiguration** (kein
`--isolated`; `pyproject.toml` mitkopiert, damit `[tool.ruff.lint] select`
greift): den Import in `core/append.py` aus dem `TYPE_CHECKING`-Block heraus
gezogen und `uv run ruff check` darauf gefahren —

```
TC001 Move application import `previously.storage.postgres.PostgresStorage`
      into a type-checking block
  --> …/src/previously/core/append.py:42:41
Found 1 error.
```

Also schlägt **Tor 1** an, nicht nur der Test. Streng gelesen ist „the gate
would report nothing" verteidigungsfähig, weil die Seite „the gate" durchweg
für `lint-imports` benutzt. „The missing gate" und „redundancy beside
`lint-imports`" sind es nicht: sie sagen dem Leser, dass sonst nichts auffällt,
und das ist gemessen falsch.

Das Unangenehme daran: das Argument der Seite ist dadurch *schwächer* als das
wahre. `TC001` greift nur, solange das Symbol **ausschließlich** in
Annotationen steht. Sobald `core` es auch zur Laufzeit benutzt — der Fall, der
wirklich weh tut —, schweigt ruff, und dann ist der Vertragstest das einzige,
was bleibt. Kleinste heilende Formulierung, ein Satz nach `:128`:

> `uv run ruff check` catches the simplest version of this with `TC001`, as
> long as the symbol stays in annotations only; the moment `core` also uses it
> at runtime, ruff falls silent and this test is the only thing left.

*Nebenbei, außerhalb dieser Aufgabe:* `tests/test_contracts.py:181-182` trägt
die unzweideutige und gemessen falsche Fassung („without any one of the five
gates going off"). Das ist eine Codeänderung und nicht Aufgabe 6 — aber die
Doku sollte die Behauptung nicht in eingefrorener Form übernehmen.

**Befund 6 (klein) — `silent-losses.md:66`.**

> „A chain promised integrity and covered eight of the eleven fields that could
> be forged."

Von den elf gehashten Feldern sind `v` und `domain` Konstanten aus
`core/hashing.py:35-36`, keine Zeilenwerte — fälschbar sind sie nicht. Die
Rechnung 8 von 11 stimmt, der Relativsatz nicht. Dieselbe Zählfalle hat
Fixrunde 1 auf `hash-chain.md:143` schon einmal beseitigt („four of the eleven
**hashed** fields"). Kleinste Heilung: `covered eight of the eleven hashed
fields.`

**Befund 7 (klein) — `silent-losses.md:73`.**

> „that's why the pages in this quadrant quote their measurements verbatim
> instead of summarizing them"

Sieben Zeilen darüber steht ein Block, der weder wörtlich noch vollständig ist:
die Aufzeichnung in Spec §5 liest
`payload {'note': 'the second'} -> NICHT gespeichert`, die Seite liest
`payload of the second entry -> NOT stored`. Die Übersetzung ist durch die
Sprachregel erzwungen und völlig in Ordnung — „verbatim" ist dann aber das
falsche Wort, zumal Spec §1.1 ausdrücklich argumentiert, eine Aufzeichnung werde
wörtlich zitiert oder nicht. Kleinste Heilung: `quote their measurements rather
than summarizing them`.

**Befund 8 (klein) — `silent-losses.md:63`, der Grabstein-Fall in der
Zweiteilung.**

> „In every case the code did what the specification said."

Für den Grabstein-Fall sagt die Spezifikation selbst etwas anderes
(`stufe-1a-log.md:403-406`): „Der Code prüft `row.payload is None`, diese
Spezifikation schreibt `payload IS NULL` vor — die beiden waren damit nie
äquivalent." Wer den eingefrorenen Entwurfsbericht liest und dann diese Seite,
findet dort eine Abweichung zwischen Code und Spec, also dem Buchstaben nach
einen Programmierfehler.

Die fette Zusage „Not one of them was a programming error" bleibt richtig —
aber aus einem Grund, den die Seite nicht nennt: die Vorgabe `payload IS NULL`
war in Python nur unter einer Voraussetzung umsetzbar (Nutzlast ist ein
JSON-Objekt), die die Spezifikation voraussetzte und nirgends erzwang. Behoben
wurde darum die Voraussetzung (`event_payload_object_check`), nicht die
Prüfung. Das ist die dritte Kategorie neben „falsch" und „schweigt", und die
Zweiteilung in `:62` hat keinen Platz dafür. Ein Halbsatz genügt, und er macht
die Behauptung belastbarer statt schwächer.

**Nicht beanstandet, aber geprüft und für tragbar gehalten:**

- `concurrency.md:120` „There *can't* be a partner in lockstep here" — aus dem
  Isolationsgrad begründet, nicht aus einer Beobachtung, und die Seite sagt das
  (`:115`).
- `concurrency.md:125-133` — der Unerreichbarkeitsanspruch ist genau so weit
  gefasst, wie er trägt („out of `append` itself"), und nennt den Pfad, den
  jemand gegangen ist. Vorbildlich.
- `module-boundaries.md:6-8` „two unique indexes" gegen „three names": die
  Spec sagt „die beiden Unique-Indizes" (§4.3), und das Argument auf `:80-83`
  trägt es — ein `event_hash_idx`-Konflikt setzt denselben `id` voraus, kann
  also nichts abweisen, was `event_pkey` nicht auch abwiese. Konsistent.

**Kleinigkeiten ohne Handlungsbedarf:** `concurrency.md:12` „one transaction
per call" (es ist eine je Versuch, plus eine im Quellschlüssel-Zweig — die
eigene Messung auf `:123` sagt „three transactions");
`concurrency.md:109` „retry it eight times" (acht Versuche, sieben
Wiederholungen); `module-boundaries.md:145` „rather than the return code" (der
Test prüft den Rückgabewert *auch*, `tests/test_contracts.py:161`);
`hash-format.md:18` „the path to the offending value" (bei der
Schlüsselregel ist es der Pfad des *umgebenden Objekts*: `$: key 'Total' …`);
der `graph TD` mischt Schicht- und Modulknoten, `storage.postgres` hängt an
keiner Kante von `storage`.

---

## 7. Bedenken

1. **Zwei der acht Befunde sind aus Quelltextkommentaren übernommen** (Befund 1
   aus `core/append.py:73-77`, Befund 4 aus `tests/test_contracts.py:181-182`).
   Die Seiten sind sorgfältig gegen den Code geschrieben — aber ein Kommentar
   ist kein Code, und beim Kommentar hat das Nachrechnen gefehlt. Für Aufgabe 7
   und die noch folgenden Umstellungen ist das die wichtigste Lehre dieser
   Prüfung: ein Kommentar ist eine Behauptung wie jede andere.
2. **Die beiden Prosa-Verweise in den How-tos** (`verify-the-chain.md:29`,
   `restore-from-a-backup.md:29`) zeigen weiter auf „the explanation of backup
   encryption" statt auf `{ref}`backup-encryption``, obwohl das Label seit
   diesem Commit existiert. Das ist korrekt so: Plan `:876-877` und
   `task-7-brief.md:71-72` weisen sie ausdrücklich Aufgabe 7 zu. Nur nicht
   vergessen — nach dem Einfrieren sind es die einzigen zwei Querverweise im
   Baum, die nicht auflösen.
3. **Die Zahlen aus `backup-encryption.md` bleiben in dieser Sitzung
   unverifizierbar.** Wer sie vor dem Einfrieren prüfen will, braucht den
   GitHub-Zugang wieder; derzeit meldet der Server
   `Authorization header is badly formatted`. Die Seite ist dagegen richtig
   gebaut: datiert, mit der Anweisung neu zu erheben, und mit einem Kriterium
   („wird daran gearbeitet") statt einer Versionsnummer.
4. **Kein Code, kein Test, keine Spec wurde angefasst** — nachgeprüft:
   `git status` zeigt nur die (fremde) Änderung an der Plandatei, `src/` enthält
   kein Probenmodul, `tests/` ist unberührt. Alle meine Messungen liefen gegen
   Kopien unter dem Scratchpad.
