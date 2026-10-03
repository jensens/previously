# Aufgabe 6 — Bericht: Explanation, Teil 2 (Nebenläufigkeit, Grenzen, Backups)

Zweig `worktree-dokumentation`, Worktree `.claude/worktrees/stufe-1a-log`, BASE `a816d4f`.
Ein Commit: `ed84bf5` — *docs: explain concurrency, the module boundaries and the backup encryption*.
Ein Commit und nicht drei, weil `concurrency.md` auf `{ref}`silent-losses`` und
`canonicalization.md` auf `{ref}`payload-range`` verweist: eine Aufteilung entlang der
Schritte hätte Zwischenzustände erzeugt, in denen `sphinx-build -W` scheitert, und einen
grünen Zwischenzustand hätte ich nur behaupten, nicht messen können.

Angelegt: `docs/explanation/concurrency.md`, `docs/explanation/module-boundaries.md`,
`docs/explanation/backup-encryption.md`, `docs/explanation/silent-losses.md`.
Geändert: `docs/explanation/index.md` (Toctree), `docs/reference/configuration.md` (Schritt 3),
`docs/reference/hash-format.md` (Schritt 4), `docs/explanation/canonicalization.md` und
`docs/explanation/hash-chain.md` (Schritt 4 und 5), `.vale-styles/config/.../accept.txt` (vier Wörter),
`.vale.ini` (Zählung im Kommentar, siehe Abweichung E).

Kein Code angefasst, 189 Tests unberührt. Alle sieben Schritte ausgeführt.

Die fünf Label, wörtlich: `(concurrency)=`, `(conflict-classes)=`, `(module-boundaries)=`,
`(backup-encryption)=`, `(silent-losses)=`. Dazu ein sechstes, unverlangtes:
`(payload-range)=` in `docs/reference/hash-format.md`, damit `canonicalization.md` auf den
Abschnitt und nicht nur auf die Seite verweisen kann.

---

## Muss überleben → steht hier

### `concurrency.md`

| Muss überleben | Steht hier |
|---|---|
| Die **zwei** Unique-Indexe sind die **gesamte** Nebenläufigkeitssteuerung, kein Advisory-Lock, kein `FOR UPDATE`, keine Koordination | Einleitung und `## The indexes are the serialization` |
| Der Verlierer liest die Spitze neu und wiederholt, **mit Zurückweichen** | `## The indexes are the serialization`, samt `[0, 0.005 * 2**attempt]`, Deckel `0.2`, acht Versuche, sieben Wartezeiten, `ChainConflict` danach; und die Begründung gegen ein festes Intervall (Gleichschritt) |
| `READ COMMITTED` ausdrücklich, nicht per Default; unter `SERIALIZABLE` andere Fehlerklasse | ebenda |
| `NULLS NOT DISTINCT` **nicht optional**: mehrere `NULL` gelten sonst als verschieden, jeder Prozess könnte seinen eigenen Genesis-Eintrag schreiben — die Verzweigung, die der Index verhindern soll | `## The index clause that isn't optional`, mit dem PostgreSQL-15-Boden über `{ref}`configuration-reference`` und dem Rückverweis auf die `id = 0`-Messung in `{ref}`hash-chain`` |
| **Drei Konfliktklassen, zwei Wiederherstellungen**; `event_prev_hash_idx` und `event_pkey` derselbe Vorfall (wiederholen), `source_key_pkey` Idempotenz-Rennen (neu nachsehen) | `(conflict-classes)=` `## Three classes of conflict, two recoveries`, erster Absatz |
| Welcher Index zuerst anschlägt hängt an der Index-OID-Reihenfolge, darum werden **alle drei** in denselben Fehler übersetzt | ebenda, mit dem Messblock und dem Satz, warum der Test den **Typ** und nicht den Namen prüft; samt `REINDEX CONCURRENTLY`/`pg_repack` und der sqlalchemy-Ausnahme, die ohne die Übersetzung aus `core` ausgetreten wäre. **Mit Abweichung A** |
| `event_kind_check` bleibt unübersetzt | ebenda, letzter Absatz des Abschnitts |
| Der Quellschlüssel-Zweig weicht **nicht** zurück: unter READ COMMITTED entsteht die Verletzung erst **nach** dem Commit des Wettbewerbers, vorher **blockiert** der Duplikat-INSERT; es kann keinen Partner im Gleichschritt geben | `## The source-key branch doesn't back off, and that's not an omission`, samt Sondenmessung und dem Hinweis, dass ein dritter Schreiber auf der Kettenposition kollidiert |
| Der Teiltreffer: fremdgehaltene **und** wirklich neue Schlüssel in einem Stapel; `append` muss je Event genau eine `id` liefern; eine kürzere Liste wäre **still** falsch | `## The partial hit, and the shorter list that would have been silent`, mit Verweis auf `{ref}`silent-losses`` |
| Stapeln als Mittel gegen Konkurrenz, Verhungern ist möglich, `MAX_BATCH = 500`, `MAX_RETRIES = 8`, die Antwort wäre ein einziger Anfüge-Prozess | `## Batching is the remedy against contention, not its amplifier` |
| `sequenceDiagram` des Schreibrennens | nach `## The indexes are the serialization`, mit `:caption:`, einem Satz Prosa davor, Backtick-Fence, **kein** `:alt:` |

### `module-boundaries.md`

| Muss überleben | Steht hier |
|---|---|
| `cli → core → storage → contract`, als Verträge geprüft | Einleitung und `## Four contracts, and the names are the output` (die vier Namen wörtlich, als Torausgabe) |
| Warum die zwei Ausnahmen **namentlich** aufgezählt sind und nicht gemustert, mit der Wegwerfmodul-Messung: `previously.core.*` → KEPT, `3 ignored imports`, lautlos; zwei benannte Kanten → BROKEN mit Nennung der neuen Kante | `## Why the two exemptions are enumerated and not matched`, Messblock; dazu das Argument über die **Importeur**-Seite und die Gleichsetzung mit dem global verworfenen `exclude_type_checking_imports` |
| Warum es den Riegel im Testlauf gibt: die Ausnahme hängt an der Importkante, **nicht** an deren TYPE_CHECKING-Eigenschaft | `## The bolt in the test run`, mit der Messung `4 kept, 0 broken` gegen `failed: "loaded sqlalchemy at runtime"` und dem Grund für den frischen Interpreter |
| Ein `LogStore[Conn]`-Protokoll in `contract` macht die Ausnahmen **ersatzlos** entbehrlich | `## The protocol that would make all of this unnecessary`, samt `storage.rows` als unbedenkliche Typquelle |
| `graph TD` der Modulgrenzen mit **gestrichelten** Ausnahmen | nach `## The edges, and the two that are exempted`, mit `:caption:`, Prosa davor, Backtick-Fence, **kein** `:alt:` |

Zusätzlich untergebracht, weil Architektur §2 und §10.1 als Quellen genannt sind und ohne
sie der Zweck der Grenzen fehlte: warum `contract` ein eigenes Modul ist (Zyklus, der Kern
muss `RawEvent` entgegennehmen), dass `storage` nichts kennt, und die zwei absichtlichen
Abweichungen der 1a-Verträge von der Architekturtabelle. Letztere um eine **eigene Messung**
ergänzt, siehe Abweichung B.

### `backup-encryption.md`

| Muss überleben | Steht hier |
|---|---|
| Hetzner hat **gar keine** Verschlüsselung im Ruhezustand, nur SSE-C beim Hochladen; nachgeprüft am 2026-10-03 | `## The provider encrypts nothing at rest`, mit dem Zitat als Blockquote |
| SSE-C bricht bei Kopien, Ursache Ceph (kein SSE-Modus mit CopyObject); operativ schon aufgeschlagen (kup6s, „never use server-side encryption", `501` auf Tagging) | `## Server-side encryption breaks on copies` |
| barman-cloud kann **nur** serverseitig (AES256, `aws:kms`); klassisches Barman kann GPG, die Cloud-Werkzeuge nicht, offene Anfrage; die Datenbank läge unverschlüsselt im Bucket | `## One tool can do it, and the obvious one can't` |
| pgBackRest-CNPG-I-Plugin: clientseitig für Backups **und** WAL-Archive, `aes-256-cbc`, Schlüssel aus einem Secret, dazu Restore, Archivierung, PITR, Replica-Cluster | ebenda |
| Keine Abwägung „bewährt gegen neu": `barmanObjectStore` seit CNPG 1.26 abgekündigt, Entfernung mit 1.30, Nachfolger ebenfalls ein CNPG-I-Plugin. **Zwei neue Plugins, nur eines verschlüsselt** | `## It isn't a choice between proven and new` |
| Der datierte Pluginstand (2 gegen 30 Commits, v0.0.3 gegen v0.8.0, 23 gegen 44 Vorgänge, EXPERIMENTAL im README), die gedrehte Erwartung, und das Kriterium „wird daran gearbeitet" statt Versionsnummer — Tabelle neu erheben | `## Which implementation, measured and dated`, samt der Warnung über die Artikel zu pgBackRest (`archived: false`, letzter Push 2026-10-02, 24 Commits in 30 Tagen, drei Freigaben) |
| Der Preis der Passphrase: verloren heißt endgültig verloren; Passphrase **vor** dem ersten Backup; dieselbe Sorgfalt wie die Daten; ein ungeprüfter Schlüssel ist so wenig ein Schlüssel wie ein ungeprüfter Restore ein Backup | `## The price of the passphrase`, mit Verweis auf `{ref}`verify-the-chain`` |
| Wo die Schlüssel liegen: External Secrets Operator, eigener Namespace, getrennte Schlüssel für Blobs und Backups bei gleichem Tresor, Vault delegiert mit zwei nachprüfbaren Anforderungen | `## Where the keys lie, and why the question stops here` |
| Die drei Wege A/B/C mit ihrem jeweiligen Preis, A gewählt wegen *wer den Schlüssel hat*, und **was A umstoßen würde** samt dem Hinweis, dass diese Prüfung nicht geführt ist | `## Three paths, and what would overturn the chosen one`, inklusive kup6s als Beleg und nicht als Argument |
| Die zwei verbleibenden Einwände: Pluginreife (Antwort: ein ungeprüfter Restore ist kein Backup, und die Kette prüft den **wiederhergestellten Bestand**) und zwei Backupwerkzeuge im Betrieb (zwei Proben, nicht eine; der Einwand war zunächst nicht genannt) | `## The two objections that remain` |
| Was es architektonisch aufräumt: eine Linie mit den Blobs, clientseitig, Schlüssel außerhalb des Datenpfads | `## What it tidies up` |

**Kein Diagramm** in `backup-encryption.md` und keines in `silent-losses.md`, wie vorgegeben.

### `silent-losses.md` (Schritt 5)

Alle fünf benannt, je in zwei bis drei Sätzen, in der Reihenfolge des Briefs, jede mit
Verweis auf die Seite, die das volle Argument trägt:

1. `## The reserved key that would have been overwritten` → `{ref}`canonicalization``
2. `## The mail that would have arrived as one unit` → `{ref}`hash-chain``
3. `## The three forgeries the chain waved through` → `{ref}`hash-chain``
4. `## The tombstone that no tombstone query found` → `{ref}`tombstone-seam``
5. `## The batch entry that vanished` → `{ref}`canonicalization``, mit dem Messblock

Das Verbindende steht in `## What the five have in common`: keiner war ein Programmierfehler,
jeder war eine Lücke zwischen Zusage und Wirklichkeit (vier benannte Zusagen, einzeln
aufgeführt), jeder wurde durch **Messen** gefunden statt durch Lesen, und in einem append-only
Speicher wäre jeder unwiederbringlich gewesen. Siehe Abweichung D zur Zählung „vier von fünf".

Die zwei Verweise lösen jetzt auf:

- `docs/explanation/hash-chain.md`: `one of its {ref}`five silent losses of data <silent-losses>``
- `docs/explanation/canonicalization.md`: `one of the {ref}`five silent losses of data <silent-losses>` this project has found`

### Schritt 3 und Schritt 4

**Schritt 3.** `docs/reference/configuration.md`:
`` `NULLS NOT DISTINCT` is not optional; see {ref}`concurrency`. `` — wörtlich die Zeile, die
der Plan (Zeile 493) vorgesehen hatte und Aufgabe 2 weglassen musste.

**Schritt 4.** Neuer Abschnitt `(payload-range)=` `## Payload range` in
`docs/reference/hash-format.md`, mit der Pflichtmenge als Tatsachen und je Zeile der
Fehlermeldung, **abgelesen** aus `core/canonical.py` durch Aufruf des Codes:

```
$.a: floating point number not allowed — state a scale as an integer (§3.2)
$: key 'Total' must match ^[a-z][a-z0-9_]*$
$.a: integer outside the safe range (±9007199254740991) — not exact across languages
$.a: null byte not allowed — PostgreSQL jsonb cannot store it
$.a: string not representable as UTF-8 (surrogates not allowed) — a lone UTF-16 surrogate, for instance
$.a: type set not allowed
```

Dazu der Pfadaufbau (`$`, `.name`, `[n]`), der reservierte Schlüssel `evidence` und die
Anwendung der beiden Zeichenbedingungen auf `source` und `external_id`.
`canonicalization.md` trägt die Werte jetzt **nicht** mehr: aus
`**Keys match `^[a-z][a-z0-9_]*$`.**` wurde `**Keys stay in lower-case ASCII.**` und aus
`**Integers stay inside `±(2**53 - 1)`.**` wurde `**Integers stay inside the safe range.**`,
beide Begründungen unverändert, und der Abschnitt verweist auf `{ref}`payload-range``.

**Nicht eingetragen**, wie angeordnet: die zwei Prosa-Sätze in
`how-to/verify-the-chain.md:29` und `how-to/restore-from-a-backup.md:29`.
`git diff -- docs/how-to/` ist leer.

### Schritt 6

`docs/explanation/index.md`, die zwei bestehenden Einträge unberührt, vier angefügt:
`hash-chain`, `canonicalization`, `concurrency`, `module-boundaries`, `backup-encryption`,
`silent-losses` — `silent-losses` zuletzt, weil es die Lehre aus den anderen zieht.

---

## Gelesene Quellabschnitte

- `docs/superpowers/specs/2026-10-02-stufe-1a-log.md`: §4.1, §4.2 samt dem G-7-Kasten zum
  Teiltreffer, §4.3, §4.4, §5 (Anfang und der N-5-Kasten), §8 vollständig, §9 (Testaufbau),
  §12 (der `LogStore[Conn]`-Eintrag), §1.1 samt Korrektur K1 (für `silent-losses.md`).
- `docs/superpowers/specs/2026-10-01-architektur.md`: §2 vollständig, §3 (Belegart), §10.1
  vollständig, §10.5 vollständig samt allen Unterabschnitten.
- Code, gegen den ich die Spezifikation geprüft habe: `src/previously/core/append.py`
  (Modul-Docstring, `_prepare`, `append`, beide `except`-Zweige, `backoff_delay`),
  `storage/postgres.py` (`_CHAIN_POSITION_CONSTRAINTS`, `_constraint_name`, `insert_event`,
  `begin`), `storage/errors.py`, `storage/schema.py`, `core/canonical.py`, `core/units.py`,
  `cli.py` (Importkopf), `.importlinter` vollständig, `tests/test_contracts.py` vollständig,
  `tests/test_storage.py` (die beiden OID-Reihenfolge-Tests und der `event_kind_check`-Test),
  `tests/test_append.py` (die zwei Nebenläufigkeitstests, `MAX_BATCH`).
- Vorhandene Doku: `explanation/hash-chain.md` und `explanation/canonicalization.md`
  vollständig (Ton und Anschluss), alle vier Quadranten-Indizes, `reference/hash-format.md`,
  `reference/configuration.md`, `reference/database-schema.md`, `docs/index.md`, die beiden
  betroffenen How-tos, `conf.py`, `docs/Makefile`, `.vale.ini`, das Vale-Vokabular und die
  Microsoft-Regeln unter `.vale-styles/Microsoft/` (Alarmstufen, Adverbs, Dashes, Quotes,
  HeadingAcronyms, Contractions, Units, DateFormat).
- Der Bericht und die Prüfung von Aufgabe 5, für die Anschlussstellen.

---

## Abweichungen zwischen Spec, Brief und Code

### A. Es sind **vier** Beschränkungsnamen, nicht drei — der Code gilt

Spec §4.2 und der Brief nennen drei Konfliktklassen: `event_prev_hash_idx`, `event_pkey`,
`source_key_pkey`. Der Code nennt einen vierten, `event_hash_idx`, und ordnet ihn der ersten
Gruppe zu (`storage/postgres.py:55`, `storage/errors.py:17`, `core/append.py:12`). Der Brief
sagt im selben Atemzug „darum **alle drei** in denselben Fehler übersetzt werden" — und diese
drei sind `event_pkey`, `event_prev_hash_idx`, `event_hash_idx`, also nicht dieselben drei wie
in der Klasseneinteilung.

Aufgelöst zugunsten des Codes und offen gesagt: der Abschnitt behält die Überschrift
`## Three classes of conflict, two recoveries` (so heißt die Einteilung der Spezifikation,
und `(conflict-classes)=` hängt daran), nennt die drei Klassen, und erklärt dann in einem
eigenen Absatz, dass der Code einen vierten Namen in die erste Gruppe aufnimmt, samt der
Begründung, warum die erste Fassung dieser Entscheidung falsch war (`id` und `prev_hash`
gehen in den Event-Hash, also kann derselbe `hash` nur an derselben Kettenposition
entstehen).

### B. „gemessen durch Drehen der Anlegereihenfolge" — so ist es nicht gemessen worden

Der Brief schreibt der OID-Reihenfolge eine Messung zu, die es in diesem Baum nicht gibt.
Gemessen wurde anders, und das steht in `tests/test_storage.py:338-363`: ein INSERT, der
`event_pkey` und `event_hash_idx` **gleichzeitig** verletzt, und ein Test, der darum den
**Fehlertyp** prüft und nicht den Beschränkungsnamen. Dazu ein zweiter Test, der
`ChainPositionTaken('event_hash_idx')` namentlich festhält. Die Anlegereihenfolge wurde nicht
gedreht.

Die Seite sagt, was gemessen wurde, und nicht, was der Brief dafür hielt — der Satz lautet
jetzt „Measured with an insert that violates `event_pkey` and `event_hash_idx` at the same
time" mit dem Messblock darunter. Die Folgerung ist dieselbe und bleibt stehen.

Zweitens, dieselbe Stelle: der Brief sagt, ohne die einheitliche Übersetzung wäre „nach einem
`REINDEX` eine sqlalchemy-Ausnahme aus `core` ausgetreten". Das stimmt und ist nachgeprüft:
`insert_event` lässt einen nicht zugeordneten `IntegrityError` mit `raise` durch, `append`
fängt nur die zwei übersetzten Fehler, und `cli.main` fängt `StorageError` und
`PreviouslyError` — ein `IntegrityError` ist keines von beiden und landet beim Benutzer als
Stapelspur. Die Seite sagt es in dieser Kette.

### C. Die Vertragsbegründung aus Spec §8 ist stärker, als sie dort steht — nachgemessen

Spec §8 begründet die Aufzählung `core`/`contract` statt „alles außer `storage`" mit
*„die Verneinung würde stillschweigend auch jedes künftige Modul einschließen"* — ein
Zukunftsargument. Gemessen bricht die Verneinung **heute**, an einem Modul, das es gibt:

```
Probe everything except storage BROKEN (2 ignored imports)

previously.cli is not allowed to import sqlalchemy:
-   previously.cli -> previously.storage.postgres (l.21, l.22)
    previously.storage.postgres -> sqlalchemy
```

`cli.py:21-22` importiert `from_dsn` und `PostgresStorage` zur Laufzeit, was die
Schichtenordnung erlaubt. Gemessen mit einer Kopie von `.importlinter` im Scratchpad und
`lint-imports --config`, ohne den Baum anzufassen. Die Seite trägt diese Messung; das ist
eine Ergänzung der Spec, kein Widerspruch zu ihr.

Ebenfalls nachgemessen, weil ich eine Zahl zitiere: das Wegwerfmodul-Ergebnis des
`.importlinter`-Kommentars. `core/zz_probe.py` mit demselben `TYPE_CHECKING`-Muster angelegt,
beide Konfigurationen gefahren, Probe sofort wieder entfernt:
`previously.core.*` → `KEPT (3 ignored imports)`, `4 kept, 0 broken`; zwei benannte Kanten →
`BROKEN (2 ignored imports)` mit `previously.core.zz_probe -> previously.storage.postgres
(l.4)` in der Begründung. `git status` danach sauber, `lint-imports` wieder `4 kept, 0 broken`.

Und eine Ungenauigkeit in Spec §8, die ich nicht übernommen habe: dort steht „In 1a existieren
`core`, `storage` und `contract`." `previously.cli` existiert ebenfalls und ist die **oberste**
Schicht des `layers`-Vertrags. Der Vertragsname sagt es nicht („Layers: core above storage,
contract below both"), der Vertragsinhalt schon. Die Seite nennt vier Module, wie der Code.

### D. Die Zählung „keiner war ein Programmierfehler" habe ich nicht in eine Zahl gegossen

Für `silent-losses.md` lag es nahe zu schreiben „in vier von fünf Fällen war die
Spezifikation falsch, im fünften war der Fall nirgends beschrieben". Nachgesehen trägt das
nicht: der reservierte Schlüssel `evidence` kommt in der 1a-Spec **überhaupt nicht** vor
(nur `evidence: Evidence` in Architektur §6.2 und die Belegart in §3), ist also ebenfalls ein
Fall, über den nichts geschrieben stand. Die Seite sagt darum ohne Zahl: wo die Spezifikation
falsch war, war der Code mit ihr falsch; wo sie schwieg — beim Schlüsselkonflikt und beim
Doppelschlüssel im Stapel —, hatte die Lücke keinen Eigentümer. Die Aussage „keiner war ein
Programmierfehler" steht unverändert und fett.

### E. `.vale.ini` zählte neun statt zehn kleingeschriebene Vokabeleinträge

Der Kommentar in `.vale.ini` (aus `1b176d3`) sagte: „Nine of the eleven entries are
lowercase". Gezählt waren es zehn von elf — nur `SQLAlchemy` war groß. Nachgezählt mit
`awk 'NF && /^[a-z]/' .vale-styles/config/vocabularies/Previously/accept.txt | wc -l` → `10`,
bei `wc -l` → `11`.

Da ich vier Wörter hinzufügen musste, hätte der Satz so oder so wandern müssen. Er steht
jetzt auf dem neuen Stand — **elf von fünfzehn** — und nennt die Korrektur, damit die Zahl
beim nächsten Mal nachgezählt und nicht fortgeschrieben wird.

### F. Vier Vokabeleinträge, einzeln geprüft

Je einer angefügt, danach `make vale` gefahren, erst dann der nächste. Die Zahl ist der
Fehlerstand **nach** dem jeweiligen Eintrag, über alle 19 Dateien:

| Eintrag | `make vale` danach |
|---|---|
| `Hetzner` | 12 errors |
| `Ceph` | 10 errors |
| `Dalibo` | 7 errors |
| `namespace` | 4 errors (Rest: Contractions und ein Adverb, umformuliert) |

Drei davon sind großgeschriebene Eigennamen, also von der `Vale.Terms`-Pinnung unbelastet.
`namespace` ist klein und darf damit nirgends im Baum einen Satz oder eine Überschrift
beginnen; es tut es nicht.

`unencrypted` habe ich **nicht** eingetragen, obwohl Vale es dreimal angemahnt hat, sondern
durch „in the clear" ersetzt — ein Eintrag weniger für ein Wort, das nichts Fachliches sagt.
Dasselbe für `psycopg` und `testcontainers`, die als Paketnamen in Codespannen gehören und
dort aus Vales Geltungsbereich fallen. `pgBackRest`, `passphrase`, `Barman` und `kup6s` hat
`Vale.Spelling` ohne Eintrag akzeptiert.

### G. Von Vale erzwungene Formulierungen

`Microsoft.HeadingAcronyms` (warning, Muster `[A-Z]{2,4}`, Geltungsbereich Überschrift)
verbietet die naheliegende Überschrift:

```
55:14  warning  Avoid using acronyms in a title or heading.  Microsoft.HeadingAcronyms
```

Aus `## Why NULLS NOT DISTINCT isn't optional` wurde darum
`## The index clause that isn't optional`; die Klausel steht im ersten Satz darunter.
Wer in diesem Baum eine Überschrift mit `SQL`, `OID` oder `JSON` plant, läuft in dieselbe
Regel.

`Microsoft.Contractions` (error) greift auch über Wortgrenzen hinweg, was zweimal überrascht
hat: „the request for **it is** open" und „the event **that is** new" wurden angemahnt,
obwohl beides keine Kopula-Konstruktion ist. Beide umformuliert.

`Microsoft.Adverbs` (warning) hat „really", „very", „deliberately", „separately", „silently",
„faithfully" und „carefully" angemahnt — alle sieben umformuliert, keine Abschaltung.
Dabei ist „eine **sehr** große Transaktion" aus Spec §4.4 zu „a transaction that carries
hundreds of events" geworden, was dieselbe Sache sagt und nachprüfbarer ist.

`Vale.Spelling` mahnt „OIDs" an, „OID" nicht. Der Satz nennt jetzt „the physical order of
their `oid` values".

---

## Tor-Ausgaben

```
$ make -C docs html
build succeeded.
The HTML pages are in _build/html.

$ make -C docs vale
✔ 0 errors, 0 warnings and 0 suggestions in 19 files.

$ make -C docs linkcheck
build succeeded.
$ wc -c docs/_build/linkcheck/output.txt
0 docs/_build/linkcheck/output.txt

$ uv run pytest -q
189 passed in 16.46s

$ uv run lint-imports
Layers: core above storage, contract below both KEPT
core knows no foreign system and no model KEPT (2 ignored imports)
Only storage imports sqlalchemy KEPT (2 ignored imports)
No vendor SDK in stage 1a KEPT
Contracts: 4 kept, 0 broken.
```

Beide Mermaid-Blöcke sind im gebauten HTML nachgesehen: `<pre class="mermaid">` mit dem
Diagrammtext und die `:caption:`-Zeile als Bildunterschrift, bei
`mermaid_output_format = "raw"` (Default, in `conf.py` nicht gesetzt). Backtick-Fence, kein
`:alt:`, ein Satz Prosa davor.

Seitenlängen: `concurrency.md` 167 Zeilen, `module-boundaries.md` 162,
`backup-encryption.md` 148, `silent-losses.md` 78.
