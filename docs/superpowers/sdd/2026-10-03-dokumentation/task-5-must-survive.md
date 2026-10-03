# Aufgabe 5: die Begründungen, die überleben müssen

Diese Liste ist der Grund, warum diese Aufgabe an einen frischen Umsetzer geht
und nicht vom Auftraggeber geschrieben wird. Bei einer Übersetzung ist die
Fehlerart **unsichtbar**: eine verlorene Begründung sieht aus wie eine knappe.
Ein Prüfer kann „ist es kürzer geworden?" nicht beantworten — aber „steht
Punkt 7 drin, mit seiner Zahl?" kann er.

**Jeder Punkt unten muss auf der Seite erscheinen, mit seiner Zahl und seiner
Messung.** Nicht wörtlich übersetzt — sinngemäß, in gutem Englisch, in der
Diátaxis-Form der Explanation. Aber vollständig. Fehlt eine Zahl, ist die
Aufgabe nicht fertig.

Der Prüfer bekommt dieselbe Liste und geht sie Punkt für Punkt durch.

---

## Für `hash-chain.md`

**1. Der Hash deckt den Digest, nicht die Nutzlast.**
Das ist die Tilgungs-Naht: wird `payload` zum Grabstein, bleibt der Event-Hash
gültig, weil er `payload_hash` trägt und nicht den Inhalt. Dazu der **Preis**,
und der gehört dazugesagt: solange es kein Tilgungs-Event gibt, ist ein
Grabstein von einer Fälschung **nicht zu unterscheiden**. Und der Weg, der ihn
einlöst: eine Tilgung muss selbst ein Event im Log sein, dann ist ein Grabstein
ohne zugehöriges Tilgungs-Event erkennbar.

**2. `id = Vorgänger.id + 1`, keine Sequenz.**
Eine Sequenz garantiert die **Commit-Reihenfolge** nicht. Die Kette läse dann
9 → 11 → 10, während die Prüfung sie in id-Reihenfolge durchläuft. Das ist der
Grund, warum hier keine Sequenz steht — nicht Sparsamkeit.

**3. `recorded_at` ist Eingabe, nicht Ausgabe.**
Es geht in den Hash ein, also muss es über Wiederholungen **stabil** bleiben.
Die Anfügeschleife erzeugt es nie selbst. Daraus folgt auch, dass der Hash in
der `show`-Ausgabe für einen Leser nicht reproduzierbar ist — und zwar
stärker, als hier zunächst stand: `_cmd_show` druckt `recorded_at` überhaupt
nicht, und `prev`, `source` und `external_id` ebenfalls nicht. **Vier der elf
gehashten Felder fehlen der Ausgabe**, der Leser könnte den Hash also auch mit
allem Fleiß nicht nachrechnen. Nachgemessen vom Umsetzer, Formulierung
übernommen.

**4. Einheiten und Quellenangabe gehören in den Hash — mit den drei Messungen.**
Vor der Korrektur gingen drei dauerhafte Fälschungen durch, gemessen gegen
echtes PostgreSQL:

```
Inhalt einer Einheit umgeschrieben   ->  verify() -> []
eine von zwei Einheiten gelöscht     ->  verify() -> []
Quellenangabe gefälscht              ->  verify() -> []
Gegenprobe: Nutzlast verändert       ->  verify() -> [payload_hash passt nicht]
```

Die Gegenprobe ist der Punkt: `verify` arbeitete, der Hash-Bereich war zu eng.
Die Ursache war ein **Widerspruch in der Spezifikation** — §3.1 zählte acht
Hash-Felder auf, die Abnahmetabelle verlangte „Kettenintegrität: vollständig".
Heute sind es elf Felder.

**5. Was die Kette nicht deckt — und die Zuspitzung.**
Ohne äußeren Anker gehen durch: die **Spitze löschen**, ein selbst gehashtes
Event **anhängen**, die **ganze Kette neu schreiben**. Allen drei ist gemeinsam,
dass das Ergebnis in sich stimmig ist.

Die Zuspitzung gehört dazu: **Anhängen ist schärfer als Löschen.** Löschen
nimmt dem Speicher eine Aussage, Anhängen legt ihm eine in den Mund.

Und der Satz, der das Kapitel schließen soll, sinngemäß:
*Was im Log steht, ist unverändert. Dass es vollständig ist, bezeugt das Log
nicht selbst.*

**6. Der Zählabgleich, und warum er nötig ist.**
`verify` beginnt bei `id = 1` und `read` filtert `id >= from_id` — eine Zeile
darunter lag darum außerhalb des Blickfelds. Gemessen:

```
Zeile mit id = 0 eingeschmuggelt  ->  verify() -> []
                                      read(from_id=-5) -> [0, 1]
```

Also angezeigt, aber nie geprüft. Heute zählt die Prüfung die durchlaufenen
Zeilen gegen `count(*)` in derselben Transaktion. Dazu das Nebenergebnis, das
erklärt, warum ein Fälscher sich etwas anstrengen muss: eine *genesis-artige*
`id=0`-Zeile mit `prev_hash = NULL` lässt sich **nicht** einschmuggeln, weil
`event_prev_hash_idx` sie abweist.

**7. JSON-`null` war ein falscher Grabstein.**
`payload = 'null'::jsonb` ist nicht SQL-`NULL`, aber psycopg macht aus **beidem**
Python `None`. Gemessen:

```
id | payload IS NULL | jsonb_typeof       Was Python sieht:
 1 | True            | None               id 1: None  (echter Grabstein)
 2 | False           | null                id 2: None  (die Fälschung)

Grabstein-Buchführung `WHERE payload IS NULL` findet: [1]   <- id 2 fehlt
verify() -> []
```

Die Zeile war für die Prüfung getilgt und für jede Revision unsichtbar. Heute
verboten durch `CHECK (payload IS NULL OR jsonb_typeof(payload) = 'object')`.

Die Einordnung gehört dazu, und sie ist zweiteilig: die Beschränkung
**schränkt nichts ein, was der Vertrag erlaubt** — der Nutzlastbereich ist ein
JSON-Objekt, `null` war dort nie zulässig. Und: §3.4 verlangte `payload IS
NULL`, der Code prüfte `row.payload is None`; mit der Beschränkung werden die
beiden erst **äquivalent**. Nicht der Code wurde an die Spec angepasst — die
Datenbank erzwingt, was die Spec voraussetzte.

**8. Bereichstrennung, und was ein `v = 2` wirklich bräuchte.**
`v` und `domain` stecken im gehashten Objekt, damit ein Hash aus einem anderen
Zusammenhang hier nicht gültig wird. Die Zusage „ein Formatwechsel ist eine
Versionserhöhung statt eines stillen Bruchs" ist aber mit den heutigen Spalten
**nicht einlösbar**: es gibt keine Fassungsangabe **je Zeile**, `verify` wüsste
bei gemischten Fassungen nicht, mit welchem Bereich es rechnet. Nachrüstbar ist
sie, weil alle bis dahin geschriebenen Zeilen per Definition v=1 sind.

**9. Was eine Einheit ist, und der CRLF-Fund.**
Die Zerlegung ist mechanisch und je Medium festgelegt (§6): an Leerzeilen
trennen, Leerraum am Rand entfernen, leere Abschnitte verwerfen, ab 1
nummerieren. Entscheidend und einer der fünf stillen Datenverluste dieses
Projekts: **`\r\n` und `\r` werden vorher normalisiert.** Ohne das käme ein
E-Mail-Text als **eine** Einheit an und hebelte die Zerlegung aus, auf der das
ganze Zuordnungsmodell beruht.

**10. Höchstens eine Quellenangabe je Event — und warum das keine Willkür ist.**
Der Hash deckt die Quellenangabe, also muss sie **bestimmt** sein; darum der
Unique-Constraint auf `source_key.event_id`. Daraus folgt eine Vorgabe für jeden
künftigen Konnektor: **`external_id` bezeichnet das Artefakt, nicht den
Transportweg** — die Message-ID einer Mail, nicht die IMAP-UID. Dann ergeben
zwei Zugangswege denselben Schlüssel und die Idempotenz greift von selbst.

---

## Für `canonicalization.md`

**11. JCS statt Verkettung.**
Feldverkettung ist **mehrdeutig**: zwei verschiedene Feldbelegungen können
denselben Bytestrom ergeben. Ein kanonisiertes Objekt kann das nicht.
Nebeneffekt: dieselbe Maschinerie wird **dreimal** gebraucht — für
`payload_hash`, für `units_hash` und für den Event-Hash.

> **Korrigiert am 2026-10-03.** Hier stand „zweimal … für `payload_hash` und
> für den Event-Hash". Falsch, und bezeichnend: ich erinnerte den Stand **vor
> meiner eigenen K1-Korrektur**, die `units_hash` hinzufügte. Vom Umsetzer
> gefunden und am Code belegt — `canonical()` wird in `core/hashing.py` in den
> Zeilen 52, 116 und 153 gerufen.

**12. Der Nutzlastbereich ist absichtlich eng — je Einschränkung der Grund.**

- **keine Gleitkommazahlen** — ihre Textdarstellung ist nicht eindeutig
  reproduzierbar, also wäre der Hash es auch nicht
- **Schlüssel auf `^[a-z][a-z0-9_]*$`** — keine Normalisierungsfragen, keine
  Groß-/Kleinschreibungsfallen
- **ganze Zahlen in ±(2⁵³−1)** — jenseits davon verliert ein JSON-Leser mit
  Gleitkomma-Zahlen Genauigkeit, und der Hash wäre über Sprachen hinweg nicht
  mehr derselbe
- **keine Nullbytes** — PostgreSQLs `jsonb` kann sie nicht speichern
- **keine einsamen UTF-16-Surrogate** — nicht als UTF-8 darstellbar

> **Korrigiert am 2026-10-03.** Hier standen beide Einschränkungen unter dem
> gemeinsamen Grund „nicht als UTF-8 darstellbar". Für U+0000 ist das **falsch**
> — ein Nullbyte ist in UTF-8 sehr wohl darstellbar. `core/canonical.py` nennt
> zwei verschiedene Gründe, und der Code gilt: Zeile 58 „null byte not allowed
> — PostgreSQL jsonb cannot store it", Zeile 65 „string not representable as
> UTF-8 … a lone UTF-16 surrogate". Vom Umsetzer gefunden.

**13. Der reservierte Schlüssel `evidence`.**
`append` mischt die Belegart in jede Nutzlast ein und **weist eine Nutzlast ab,
die den Schlüssel schon trägt**. Grund: die Belegart trennt Beweis von Bericht,
und in einem append-only Speicher ist sie nach dem Schreiben nicht mehr
nachzutragen. Wäre sie still überschrieben worden, wäre sie für immer verloren
gewesen — einer der fünf stillen Datenverluste.

**14. Derselbe Schlüssel zweimal in einem Stapel wird abgewiesen.**
Gemessen, vor der Korrektur:

```
append([erster, zweiter])  ->  [1, 1]
  payload des zweiten   -> NICHT gespeichert
  units des zweiten     -> NICHT gespeichert
```

Der Aufrufer bekam **zwei ids** zurück, als wäre beides verzeichnet. Die
Begründung, die nicht offensichtlich ist: Idempotenz **zwischen** Aufrufen ist
die gewollte Eigenschaft; Idempotenz **innerhalb eines Stapels** hat niemand
verlangt und ist von einem Aufruferfehler nicht zu unterscheiden.

**15. Der festgenagelte Testvektor und warum er so aussieht.**
Er hält nicht nur drei Hex-Werte fest, sondern auch die **kanonischen
JCS-Bytes** wörtlich. Grund: ein Hex-Wert allein sagt „etwas ist anders"; mit
den Bytes daneben zeigt ein Fehlschlag, **welches Feld** sich geändert hat.
Verweise auf {ref}`hash-format` statt die Werte zu wiederholen.
