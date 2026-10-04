# SDD ledger — plan: docs/superpowers/plans/2026-10-04-stufe-1b-projektionen.md

Spec: docs/superpowers/specs/2026-10-04-stufe-1b-projektionen.md (abgenommen
2026-10-04, vier Korrekturblöcke beim Planen nachgetragen). Worktree
`.claude/worktrees/stufe-1b-projektionen`, Zweig `worktree-stufe-1b-projektionen`,
abgezweigt von lokalem `main` auf `cdc508a` (origin war sechs Commits zurück —
Falle umgangen per `git worktree add … main` + `EnterWorktree path`).

Ausführungsmethode: **subagent-driven**, vom Betreuer freigegeben („setze ihn
gem. deiner empfehlung um"). Begründung nach den vier Fragen der CLAUDE.md:
Fehlerart in Aufgabe 1 (Umbau `module-boundaries.md`) und 7 (Explanation)
unsichtbar — Übersetzung, verlorene Begründung sieht aus wie knappe; sechs
Code-Aufgaben sequenziell gekoppelt mit Testzahl-Vorhersage je Aufgabe; Plan
trägt für 2–4 vollständigen Code → günstige Umsetzer, Prüfung bleibt.

Modelle: Umsetzer opus für 1, 5, 6, 7, 8; haiku/sonnet für 2, 3, 4 (Code steht
im Plan). Prüfer opus für 1, 5, 7; sonnet sonst. Nachprüfungen sonnet.

BASE vor Aufgabe 1: `ec1c666` (Plan mit drei Scan-Korrekturen committet).

---

## Vorab-Durchsicht (vor Aufgabe 1)

### Paare, die eine Datei oder Schnittstelle teilen

| Aufgaben | Geteilt | Erzeugt → verbraucht | Befund |
|---|---|---|---|
| 1 ↔ 3 | `contract/store.py`, `contract/rows.py` | 1 legt an (LogStore, 3 Zeilentypen); 3 fügt an (ProjectionStore, 3 Zeilentypen) | stimmig; 3 schreibt nicht neu |
| 1 ↔ 5 | `LogStore` 8 Methoden | 5 ruft `begin`, `tip`, `read`, `units_by_event`, `source_keys` | alle fünf in den acht |
| 2 ↔ 3 | Tabellen in `schema.py` | 2 deklariert drei; 3 importiert sie in `postgres.py` | Namen gleich |
| 2 ↔ 5 | `conftest.py` TRUNCATE | 2 erweitert auf sechs Tabellen; 5s Eigenschaftstest truncatet dieselben sechs inline | Liste identisch |
| 3 ↔ 4 | Zeilentypen | `ChronicleRow(event_id, seq, content, occurred_at, kind, evidence, source, external_id, speaker=None, start_ms=None, end_ms=None)`; 4 konstruiert benannt; `SourceStatsRow` positional in 4s Tests = (source, events, units, first_seen, last_seen, last_event_id) | Reihenfolge gleich |
| 3 ↔ 5 | `ProjectionStore` 7 Methoden | 5s `_FailingStore` implementiert genau diese sieben | vollständig |
| 3 ↔ 6 | `read_chronicle(conn, *, since, until, limit)`, `read_source_stats(conn)`, `projection_state`, `tip` | 6 ruft mit Schlüsselwörtern | stimmig |
| 4 ↔ 5 | `Batch`; `ChronicleProjection(version=)`, `SourceStatsProjection(version=)`; `write[Conn](self, store, conn, batch)` | 5s `Projection`-Protokoll und Versions-Tests | **Defekt gefunden:** Protokoll mit `name: str` (veränderlich) gegen eingefrorenes Dataclass-Feld (nur lesbar) — pyright lehnt ab. **Behoben:** read-only `@property` im Protokoll (`ec1c666`). |
| 4 ↔ 5 | `worker.py` | 4 legt an mit `Batch`; 5 fügt `Projection`, `Outcome`, `catch_up` + Importe an | stimmig, kein Importzirkel (chronicle/source_stats importieren `Batch` nur unter TYPE_CHECKING) |
| 5 ↔ 6 | `Outcome(name, version, rebuilt_from, events, up_to_id)`, `PROJECTIONS`, `catch_up(log, store, projection)` | 6s `_describe`, `_cmd_project` | **Defekt gefunden:** `_describe` sagte auf leerem Log `built: 0 events`; Review Focus 5 und der Test in 6 verlangen `up to date, up_to_id 0`. Und der zweite `project`-Lauf in `test_project_says_which_path_it_took` wäre `caught up`, nicht `built` — der erste Lauf auf dem leeren Log legt die Zustandszeile schon an. **Behoben:** `_describe` prüft Versionswechsel zuerst, dann `events == 0`, dann Erstbau; Test fügt vor dem ersten Lauf an; eigener Test für leeres Log (`ec1c666`). Aufgabe 6 hat damit neun Tests, Endstand **229**. |
| 5 ↔ 6 ↔ 3 | Projektionsnamen `"chronicle"`, `"source-stats"` | 3s `_PROJECTION_TABLES`, 4s Dataclass-Defaults, 6s CLI-Reads | gleich an allen drei Stellen |
| 6 ↔ 8 | `built: 1 event, up_to_id 1` beim ersten Lauf nach `append` | Tutorial in 8 tippt genau das ab | stimmig nach der Korrektur oben |
| 2/5/6/7 ↔ `projections.md` | 2 legt an (2 Abschnitte, Label), 5 +3, 6 +2, 7 +1 | sequenzielles Anfügen | stimmig |
| 1 ↔ 7 | `module-boundaries.md` | 1 baut um; 7 fasst sie nicht an | keine Kollision |
| 3 (Konformitätstest) | `assert log is projections` | zwei protokolltypisierte Namen per `is` — pyright könnte „immer falsch" melden | **Behoben:** zwei `isinstance`-Prüfungen, die Zuweisungen bleiben der Beweis (`ec1c666`). |

### Je Aufgabe: stimmt der Text mit sich selbst?

| Aufgabe | Geprüft | Befund |
|---|---|---|
| 1 | 8 Methoden gegen `grep storage\.X(` in append/verify (gemessen: begin, lookup, units_by_event, tip, source_keys, read, insert_event, count_events = 8); `import sys` nur in `_RUNTIME_PROBE`; Testzahl 194−1 | stimmig |
| 2 | `op.create_index` Spalten = `Index(...)` Spalten; `set(metadata.tables)` sind Tabellennamen; TRUNCATE-Liste | stimmig |
| 3 | `_event`-Helfer: `prev_hash` je Event verschieden (Unique-Index), `source_key` je Event eindeutig; `read_chronicle`-Ordnung bei gleichem `NOW` = Einfügeordnung; `ValueError` durchläuft `begin()` (fängt nur Operational/Programming) | stimmig |
| 4 | Aggregationstest: email 2 Events / 3 Einheiten / T1..T2 / last_event_id 2; cli 1/0/T3; `_evidence` narrowed via `isinstance` | stimmig |
| 5 | Abbruchtest: Stapel 2, Fehler im 3. `insert_chronicle` → Rollback → `up_to_id 4`, 8 Zeilen (2 Einheiten je Event), Folgelauf 6 Events; `RuntimeError` durchläuft `begin()`; Versionstest Kontrolle = gleicher Lauf ohne Bump ändert nichts; `stats_row[3]` = `first_seen` | stimmig |
| 6 | Zeitordnung im `chronicle`-Test (Event 2 vor Event 1); `--limit` holt `limit+1`; leeres Fenster 0 Zeilen → keine Kappung; `parse_moment` → `InvalidPayload` → 2; `Callable` unter TYPE_CHECKING (lokale Annotation, nie ausgewertet) | stimmig nach Korrektur |
| 7 | nur Doku, keine Schnittstelle | — |
| 8 | Testzahl 229 ins Tutorial; `grep "§"` über neue Module muss nur Architektur-Zitate finden | stimmig |

### Rulings der Vorab-Durchsicht

Ruling P-1: **`_describe` meldet Versionswechsel zuerst, dann Leerlauf, dann
  Erstbau** — weil ein Versionswechsel die Zustandszeile ändert und darum
  auch bei null Events gemeldet werden muss, und weil `up_to_id 0` nach Spec
  „noch nichts gebaut" heißt, also `up to date` und nicht `built: 0`.
  Kosten, falls falsch: eine Ausgabezeile, ein Test.

Ruling P-2: **`Projection.name`/`.version` sind read-only Properties.** Die
  Implementierungen sind eingefrorene Dataclasses, deren Felder pyright als
  nur lesbar behandelt; ein veränderliches Protokollattribut passte nicht.
  Kosten, falls falsch: pyright rot in Aufgabe 5, eine Runde.

Ruling P-3: **Zeilentypen nach `contract`, nicht `storage`** (schon beim Planen
  in den Spec eingetragen): `contract → storage` wäre ein Import nach oben,
  `layers` BROKEN. Kosten, falls falsch: sechs Importstellen zurück.

Keine Konflikte mit den Global Constraints gefunden. Kein Schritt verlangt
etwas, das die Prüfrubrik als Defekt behandelt (kein Test ohne Assertion,
keine wörtliche Logikduplikation — `_snapshot`/`_project_all`/`_force_rebuild`
sind Helfer, keine Kopien).

---

## Aufgabe 1 — Bericht: DONE_WITH_CONCERNS, Commit `afcbe11`

193 passed (= Vorhersage), Coverage 97.65 %, alle sechs Tore gruen,
`lint-imports` viermal `KEPT` **ohne** `(N ignored imports)`. Bericht in
`task-1-report.md` (12 Abschnitte). Sieben Bedenken, alle Beobachtungen:

Ruling T1-a: **`contract/store.py` bleibt bei 0 % Coverage, kein `pragma`,
  kein Import-nur-Test.** Grund gemessen: beide Importeure nennen `LogStore`
  nur unter `TYPE_CHECKING`, das Modul erreicht `sys.modules` nie. Ein
  Protokoll mit `...`-Koerpern hat kein Verhalten, das Coverage messen
  koennte; eine Zahl zu heben, indem man das Modul importiert, misst nichts.
  Aufgabe 3s Konformitaetstest (`log: LogStore[Connection] = storage`)
  importiert das Modul ohnehin zur Laufzeit. Gesamt 97.65 % gegen Schwelle
  90. Kosten, falls falsch: eine Zeile `exclude_lines` spaeter.

Ruling T1-b: **Jede Aufgabe, die die Testzahl aendert, tippt den Testlauf im
  Tutorial neu ab — aus einem echten Lauf.** Der Plan hatte das nur in
  Aufgabe 8; `tests/test_docs_typed_output.py` haelt aber jede `N passed`
  gegen den Baum und war in Aufgabe 1 rot („claims 194, the tree has 193").
  Der Umsetzer hat richtig gehandelt: nicht die Zahl editiert (das
  Transkript trug auch `collected 194 items` und die Punktzeilen), sondern
  `uv run pytest` gefahren und die Ausgabe eingesetzt. Gilt ab jetzt fuer
  2, 3, 4, 5, 6 — in jeden Dispatch. Aufgabe 8 tippt dann ein letztes Mal.
  Kosten, falls falsch: Rauschen im Tutorial-Diff je Aufgabe; der Preis
  dafuer, dass das Transkript nie luegt.

Ruling T1-c: **`module-boundaries.md` nennt „the protocol" im Singular, bis
  Aufgabe 3 das zweite anlegt.** Der Umsetzer hat Plural plus Praesens
  verweigert, weil `ProjectionStore` nach Aufgabe 1 nicht existiert — eine
  am Baum nicht messbare Behauptung. Richtig. **Aufgabe 3 pluralisiert**
  und zieht ins Praesens; in den Dispatch.

Bedenken ohne Ruling, fuer die Abschlusspruefung notiert:
- `module-boundaries.md` waechst 189 → 251 Zeilen, weil jeder abgeschaffte
  Zustand seine Begruendung in der Vergangenheit behaelt. Frage fuer spaeter:
  gehoert die 1a-Vergangenheit in die eingefrorenen Design-Records statt auf
  die lebende Seite? → Task 1: minor (deferred).
- Die pyright-Gegenprobe (Schritt 5) landete nicht in `core/verify.py`, wie
  der Plan erwartete, sondern an **75 Aufrufstellen in sechs Dateien** —
  `core` nennt `PostgresStorage` nicht mehr, also kann der Fehler dort nicht
  entstehen. Staerkere Bindung als erwartet; die Planerwartung war falsch.
- Eine Messung sah erst gruen aus und war falsch: der Probe-Import fuer
  `contract -> storage` landete per `sed` im Docstring. Korrekt platziert:
  `Layers … BROKEN`, `previously.contract.store -> previously.storage.errors`.
  Vom Umsetzer selbst gefangen — und genau die Fehlerart, vor der die
  Kontrollmutation schuetzt.
- Fuenf Brief-Abweichungen, alle begruendet: TYPE_CHECKING-Importe in
  `store.py` (sonst sechs `TC001`); Ueberschrift ohne Kontraktion
  (`Microsoft.Contractions`); Singular (T1-c); ein Messblock entfallen, der
  eine nicht mehr durchfuehrbare Mutation beschrieb; siebte Datei
  `core/hashing.py:59` (Docstring nannte `storage.rows.UnitRow`) — kein Tor
  haette das gefunden.
- `CLAUDE.md`: drei Zahlen statt zwei — `A001` hiess „The sixth" und ist
  jetzt die fuenfte. Ohne diese dritte Aenderung haette die Datei sich
  widersprochen.

Pruefer (opus) wird dispatcht mit `review-ec1c666..afcbe11.diff`.

## Aufgabe 1 — Pruefung (opus): Spec ✅ bis auf eine Luecke, 1 Important, 4 Minor

Beide Gegenproben byteweise reproduziert (pyright 75 Fehler in sechs Dateien,
71 Protokoll + 4 Attribut; `contract -> storage` BROKEN `(l.27)`). Alle
Zahlen stimmen (8/6/193/5/40/97.65 %/75/251/13). Alle fuenfzehn Punktzaehler
und Prozentwerte des neu abgetippten Tutorials gegen `--collect-only`
nachgerechnet. Abweichungen (a), (c), (e) des Umsetzers als **besser als der
Brief** eingestuft; (b) richtig; (d) **falsch** — das ist I-1.

**I-1 (Important):** der Sechs-Tore-Messblock hinter dem `TC001`-Argument
  wurde geloescht, der abhaengige Satz (Z. 179, „that measurement was the
  whole argument") steht ohne Bezug. Die Behauptung „survived every gate but
  that one test" ist ungedeckt — die Fehlerart aus CLAUDE.md woertlich. Beide
  Begruendungen des Umsetzers gepruefte und widerlegt: Grund 1 gilt identisch
  fuer den behaltenen Block; Grund 2 (Zahlenkollision 193) verlangt eine
  Beschriftung, keine Loeschung.

**Minor:** M-1 `.importlinter` Leerzeile am EOF (`end-of-file-fixer` wird sie
  dem naechsten als unerklaerte Aenderung zeigen); M-2 Beschriftung zaehlt
  sechs, Bild zeigt sieben Pfeile (`sqlalchemy`); M-3 „in a comment" — eine
  der zwei Stellen ist ein Docstring; M-4 Bericht sagt „woertlich", der
  Docstring hat einen nicht deklarierten Coverage-Absatz.

Ruling T1-d: **M-1, M-2, M-3 gehen mit in Fixrunde 1**, obwohl Minor nach dem
  Skill nicht in die Schleife gehoeren. Grund: M-1 beisst den naechsten
  Beitragenden aktiv (pre-commit aendert eine Datei, die er nicht angefasst
  hat), M-2/M-3 liegen auf derselben Seite, die I-1 ohnehin aendert — ein
  Wort je. Drei Ein-Wort-Aenderungen in einer Datei, die die Runde sowieso
  anfasst, gefaehrden die Enge der Schleife nicht; eine spaetere Fixwelle
  fuer drei Woerter kostete mehr. M-4 ist eine Berichtskorrektur. Kosten,
  falls falsch: die Nachpruefung hat vier Zeilen mehr zu verdikten.

Dazu drei „defensibly lost"-Formulierungen des Pruefers (der `_is_text`-
Querverweis, „same trade one level up", und „a correct decision and a wrong
one look exactly alike in the configuration") an den Umsetzer mit der
Vorgabe: tragende wiederherstellen, Weglassen begruenden. Das dritte habe
ich als tragend benannt.

Task 1: minor (deferred): `module-boundaries.md` 251 Zeilen — gehoert die
  1a-Vergangenheit in die Design-Records statt auf die lebende Seite? Fuer die
  Abschlusspruefung.

Fixrunde 1 an den Umsetzer (`a57e3095839fb7314`), FIX_BASE = `afcbe11`.

Task 1: fix round 1/5 (I-1 + M-1..M-4 + drei Formulierungen gemeldet
  behoben; commit `fdd3215`; alle sechs Tore gruen, 193 passed).

  Umsetzer waehlte den **vollstaendigen** Block statt der Drei-Zeilen-
  Kurzfassung, mit dem richtigen Grund: die Kurzfassung haette genau die
  Zeilen behalten, die zeigen, dass die Tore *schweigen*, und die
  `pytest`-Zeile verloren, die zeigt, dass der Test *zuschlug* — „but that
  one test" waere wieder unbelegt gewesen.

  **Widerspruch des Umsetzers, berechtigt:** die vom Pruefer vorgeschlagene
  Beschriftung „the tree has 193 today for an unrelated reason" war
  **falsch** — es ist derselbe Grund: 194 Tests damals, einer davon der
  Riegel, der in der Messung fehlschlug und den 1b geloescht hat. 194 − 1 =
  193, die Mengen sind identisch. Die Seite sagt das jetzt positiv: „the 193
  that passed then are the 193 that remain, because the one that failed is
  the one stage 1b deleted." Ich hatte die Formulierung ungeprueft
  weitergereicht.

  **M-3 anders geloest als vorgeschlagen, erzwungen:** „docstring" ist nicht
  im Vokabular, `Vale.Spelling` schlug an. Umsetzer hat es **nicht**
  eingetragen (richtig: ein kleingeschriebener Eintrag darf baumweit keinen
  Satz beginnen, das ist eine Entscheidung mit Nebenwirkung, keine fuer eine
  Fixrunde) und „in prose rather than in an import" geschrieben.

  Seite jetzt 279 Zeilen (189 → 251 → 279). Deferred minor verstaerkt.

Nachpruefung (sonnet) mit `review-afcbe11..fdd3215.diff`.

Nachpruefung (sonnet): I-1, 2a, 2b, 2c, M-1, M-2, M-3, M-4 **alle ADDRESSED**,
keine neuen Schaeden, Doku-Tore gruen, 279 Zeilen bestaetigt. Nachgerechnet:
`git show afcbe11 --stat` zeigt genau eine entfernte Testfunktion, der Name
ist der im wiederhergestellten Block — 194 − 1 = 193 ist derselbe Test.

Task 1: minor (deferred): `module-boundaries.md:206` — „that measurement was
  the whole argument" steht textuell direkt hinter dem `isinstance`/`pyright`-
  Block, nicht hinter dem Sechs-Tore-Block, auf den es sich bezieht; der
  umgebende Absatz klaert es, aber das naechstliegende Antezedens beim ersten
  Lesen ist das falsche. Zusammen mit der Laengenfrage (279 Zeilen) fuer die
  Abschlusspruefung.

Task 1: complete (commits ec1c666..fdd3215, review clean)

---

## Aufgabe 2 — Dispatch

BASE: `fdd3215`.

Ruling T2-a: **Umsetzer auf sonnet, nicht haiku.** Das Hauptbuch hatte fuer
  Aufgabe 2 „haiku/sonnet (Code steht im Plan)" vorgesehen. Der Code ist
  Transkription — aber Schritt 7 (`database-schema.md`: Spaltentabellen aus
  einer **migrierten Datenbank** ablesen, Beschraenkungsnamen nachschlagen)
  und Schritt 8 (zwei Explanation-Abschnitte in Prosa, Diátaxis-Ton, Vale)
  sind Prosa aus Beschreibung. Der Skill setzt fuer Prosa-Umsetzer die
  Mittelklasse als Boden; „turn count beats token price". Kosten, falls
  falsch: ein teureres Modell fuer eine Aufgabe, die haiku geschafft haette.

Umsetzer Aufgabe 2: sonnet, Agent `a5da37e4ab7807f7f` (Fixrunden 1-3 resumen diesen). Brief `task-2-brief.md` (240 Zeilen), Bericht nach `task-2-report.md`.

## Aufgabe 2 — Bericht: DONE_WITH_CONCERNS, Commit `a7b1e0b`

194 passed (= Vorhersage), Coverage 97.67 %, sechs Tore gruen, Vale 21
Dateien. Fuenf Bedenken:

1. **Zwei Defekte im Plan-Code**, beide von Toren gefangen: ein nacktes
   `§4.1` im Kommentar von `schema.py` („architecture §4.1 wants both") —
   `test_no_bare_paragraph_references_remain` schlug an; und eine
   `Index(...)`-Zeile mit 103 Zeichen (E501, Grenze 100). Beide ohne
   Bedeutungsaenderung behoben. **Mein Plan hat die Zitierregel des Projekts
   verletzt, die ich gestern selbst aufgeschrieben habe** — der Riegel
   existiert genau dafuer.
2. **`tests/test_properties.py` fehlte in der Dateiliste des Plans**, traegt
   aber fuenf eigene Inline-`TRUNCATE source_key, unit, event` (Hypothesis
   setzt je Beispiel zurueck). Mit den neuen Fremdschluesseln auf `event`
   bricht das (`NotSupportedError`: cannot truncate a table referenced in a
   foreign key constraint). Auf sechs Tabellen erweitert; ohne das waere Tor
   5 rot. Planluecke, vom Umsetzer geschlossen. Bestaetigt nebenbei, dass
   Aufgabe 5s Eigenschaftstest mit dem Sechs-Tabellen-TRUNCATE richtig
   geplant ist.
3. Die zwei `{ref}`projections``-Anschluesse in `module-boundaries.md`
   (Z. 271, 273) sind Interpretation von „zwei vorbereitete Anschlussstellen"
   — an den Pruefer.
4. Vier Vale-Korrekturen in `projections.md` durch Umformulieren, **kein**
   neuer Vokabeleintrag.
5. Der vorausblickende Schlusssatz von Abschnitt 2 in `projections.md` nennt
   keine kuenftige Ueberschrift (Aufgabe 5 schreibt sie erst). **In den
   Dispatch von Aufgabe 5:** den Uebergang pruefen.

Pruefer (sonnet) mit `review-fdd3215..a7b1e0b.diff`.
Pruefer Aufgabe 2: sonnet, Agent `a88cc8ce8bedce663`.

## Aufgabe 2 — Pruefung (sonnet): Spec ✅, Qualitaet freigegeben, 4 Minor

`database-schema.md` gegen einen frisch migrierten Container verifiziert:
alle Spalten (Name, Typ, Nullbarkeit) und alle sechs erzeugten
Beschraenkungsnamen stimmen. Fuenf TRUNCATE-Stellen in `test_properties.py`
+ eine in `conftest.py`, alle sechs identisch. Tutorial: 15 Punktzaehler
gegen `--collect-only` nachgerechnet, Summe 194, `rootdir:` fehlt, Satz
darunter steht. `41 files` = +`0002_projections.py`, per `git ls-tree`
gezaehlt (37 → 38 `.py`). Die `§4.1`-Stelle traegt jetzt
`(frozen design record)` und bleibt wahr.

⚠️ „97.67 % Coverage nicht erneut gefahren" — **aufgeloest**: der Umsetzer hat
  Tor 5 mit Ausgabe berichtet, der Pruefer hat Testzahl und -logik unabhaengig
  bestaetigt; eine zweite `--cov`-Messung derselben Commits misst dasselbe.

Task 2: minor (deferred): `database-schema.md:5` sagt „three PostgreSQL
  tables" und das `erDiagram` zeigt drei — die Seite dokumentiert jetzt sechs.
  Nicht falsch (Events liegen in dreien), aber unvollstaendig gegen den
  eigenen Umfang. **In den Dispatch von Aufgabe 7** (Doku-Politur).
Task 2: minor (deferred): `tests/test_schema.py` Docstring des neuen Tests
  zitiert `test_the_declared_indexes_exist`, der echte Name ist
  `test_the_declared_indexes_exist_in_the_migrated_database`. **Mein
  Plantext**, aus dem Gedaechtnis zitiert statt nachgesehen — die Fehlerart
  aus `zahlen-selbst-nachzaehlen`. Ein Wort; Aufgabe 7 oder Abschlusswelle.
Task 2: minor (deferred): Vorgriffssatz Ende Abschnitt 2 `projections.md` —
  Pruefer liest ihn als Uebergang, nicht Luecke; Aufgabe 5 sieht beim
  Anhaengen nach.

Task 2: complete (commits fdd3215..a7b1e0b, review clean)

---

## Aufgabe 3 — Dispatch

BASE: `a7b1e0b`.

Ruling T3-a: **Umsetzer auf sonnet, nicht haiku.** Der Plan traegt den
  vollstaendigen Code — das waere nach dem Skill der Fall fuer die
  guenstigste Stufe. Aber: sieben Store-Methoden mit SQLAlchemy-Spezifika
  (`on_conflict_do_update`, `excluded`, executemany), pyright strict ueber
  `Row`-Attributzugriffe, ein Konformitaetstest, dazu die Pluralisierung in
  `module-boundaries.md` (T1-c) als Prosa. „Turn count beats token price" —
  Aufgabe 2 brauchte auf sonnet 104 Werkzeugaufrufe; haiku braeuchte
  erfahrungsgemaess das Doppelte und die Fehlerwahrscheinlichkeit bei
  pyright-Strenge ist hoeher. Kosten, falls falsch: ein teureres Modell fuer
  Transkription.

Mitzugeben (der Brief kann es nicht wissen): Importe in `contract/store.py`
unter `TYPE_CHECKING` (Aufgabe 1, sonst `TC001`); `module-boundaries.md`
Ueberschrift „The protocol that …" wird Plural + Praesens, der Absatz ueber
das zweite Protokoll ins Praesens (T1-c); Tutorial neu abtippen bei 202
(T1-b); Zeilentypen in `contract/rows.py`.
Umsetzer Aufgabe 3: sonnet, Agent `aae264a1b583e435c`. Brief `task-3-brief.md` (472 Zeilen), Bericht nach `task-3-report.md`.

## Aufgabe 3 — Bericht: DONE_WITH_CONCERNS, Commit `44bdc66`

202 passed (= Vorhersage), Coverage 96.55 % (`storage/postgres.py` 100 %,
`contract/store.py` 0 %), sechs Tore gruen, `42 files`. pyright meldete an
den SQLAlchemy-Ausdruecken **nichts** — die Stubs tragen strict ohne `cast`.
Vier Bedenken, alle Beobachtungen; drei Brief-Abweichungen, alle Tor-erzwungen:

- `_PROJECTION_TABLES` brauchte `ClassVar[dict[str, Table]]` (RUF012 auf den
  Brief-Code) — Typkorrektur, keine Suppression. **Plandefekt.**
- `from datetime import datetime` in `store.py` war F401 — kein Protokoll
  nennt `datetime` nackt. Entfernt. **Plandefekt** (ich hatte den Import
  gelistet, ohne zu pruefen, ob eine Signatur ihn braucht).
- Testdatei: eine E501-Zeile umgebrochen, `LogStore`/`ProjectionStore`-
  Importe unter `TYPE_CHECKING` (TC001).

**Korrektur an Ruling T1-a:** die zweite Begruendung („Aufgabe 3s
  Konformitaetstest importiert das Modul zur Laufzeit") ist **falsch** —
  ruff hat genau diese Importe unter `TYPE_CHECKING` gezwungen, das Modul
  bleibt bei 0 %. Die erste Begruendung traegt allein: `...`-Koerper haben
  kein Verhalten. Der statische Beweis des Konformitaetstests gilt trotzdem —
  pyright prueft die Zuweisung unabhaengig von `TYPE_CHECKING`; zur Laufzeit
  sind es zwei `isinstance`.

Bedenken 2 des Umsetzers, fuer den Pruefer: der `ProjectionStore`-Docstring
  nennt `core.projection.source_stats`, das erst Aufgabe 4 anlegt — eine
  Behauptung ueber den Baum, die heute nicht stimmt und im naechsten Commit
  stimmen wird. Bedenken 1: `module-boundaries.md:256` („when a second
  protocol follows") unveraendert gelassen, als allgemeine Begruendung
  gelesen — Pruefer soll die Zeitform beurteilen.

Pruefer (sonnet) mit `review-a7b1e0b..44bdc66.diff`.
Pruefer Aufgabe 3: sonnet, Agent `a3f38d729b7284408`.

## Aufgabe 3 — Pruefung (sonnet): Spec ✅ vollstaendig, Qualitaet freigegeben

Protokoll gegen Implementierung Signatur fuer Signatur inkl. Parameternamen;
`read_*` korrekt ausserhalb; `set_` nur `excluded.<spalte>`; `core/` nutzt
nichts Neues (grep leer). Acht Tests gegen echtes PostgreSQL gefahren, je
Zusage geprueft: Upsert ersetzt (gedeckt), truncate trifft nur die genannte
Tabelle (gedeckt), state-Upsert dupliziert nicht (indirekt gedeckt).
`ClassVar`-Fix richtig, `Table` unter TYPE_CHECKING, keine neue Kante.
Coverage-Rechnung **exakt** nachgerechnet: 515/12 → 579/20, `store.py` von
11 auf 19 Statements bei 0 %. `42 files` = `tests/test_projection_store.py`.
Tutorial mit gepinntem Seed nachgefahren, 16 Punktzeilen, Summe 202.

⚠️ `linkcheck` nicht erneut gefahren — **aufgeloest**: Umsetzer hat es mit
  Ausgabe berichtet, der Diff aendert keinen Link.

Task 3: minor (deferred): `read_chronicle` mit `since == until` nicht direkt
  getestet (deduktiv aus `>=`/`<` gedeckt). **In den Dispatch von Aufgabe 6:**
  der Fenstertest dort prueft `since > until`; um `since == until` erweitern,
  eine Assertion.
Task 3: note: Vorwaertsreferenz `core.projection.source_stats` im
  `ProjectionStore`-Docstring — akzeptabel (naechster Commit, kein Tor prueft
  Modulpfade in Docstrings); **Aufgabe 4 verifiziert den Pfad**, sobald das
  Modul existiert.
Task 3: nit: `module-boundaries.md:256` „when a second protocol follows" —
  zeitlose Lesart vertretbar, Praeteritum waere gleich richtig.

Task 3: complete (commits a7b1e0b..44bdc66, review clean)

---

## Aufgabe 4 — Dispatch

BASE: `44bdc66`.

Ruling T4-a: **Umsetzer auf haiku — der Versuch, den der Skill vorsieht.**
  Aufgabe 4 ist die reinste Transkription des Plans: vier Dateien mit
  vollstaendigem Code, neun Unit-Tests **ohne** Datenbank, eine gemessene
  Mutation, keine Prosa-Seite. Kein SQLAlchemy, kein Container. Wenn haiku
  irgendwo in diesem Plan traegt, dann hier — und das Ergebnis sagt etwas
  ueber den Modellboden fuer dieses Repo. Fallback: bei BLOCKED oder einem
  Bericht, der die Mutation nicht gemessen hat, frischer Umsetzer auf sonnet
  (Skill: nie dasselbe Modell unveraendert nochmal). Kosten, falls falsch:
  eine verlorene Runde haiku-Tokens.

Mitzugeben: Importe nur unter TYPE_CHECKING wo nur in Annotationen (TC001);
`Batch` aus `worker.py` in chronicle/source_stats nur unter TYPE_CHECKING
(kein Importzirkel); den Docstring-Pfad `core.projection.source_stats` in
`contract/store.py` verifizieren; Tutorial neu abtippen bei 211 (T1-b);
Zeilentypen aus `contract.rows`.
Umsetzer Aufgabe 4: haiku, Agent `a480383d00a1580b5`. Brief `task-4-brief.md` (375 Zeilen), Bericht nach `task-4-report.md`.

## Aufgabe 4 — Bericht: DONE_WITH_CONCERNS, Commit `6f5667a` — und ein Fund gegen Spec und Plan

211 passed (= Vorhersage), Coverage 95.96 %, `47 files` (+5), sechs Tore
gruen, haiku 62 Werkzeugaufrufe / 84k Tokens — schneller und billiger als
sonnet in Aufgabe 3. **Aber zwei Urteilsfehler, beide selbst nachgemessen:**

1. **Die Mutation lief umgekehrt zur Vorhersage, und haiku hat recht.**
   `first_seen=addition.first_seen` (immer ueberschreiben) laesst den
   **In-Order-Test** fallen (T3 statt T1) und den **Nachzuegler-Test
   bestehen** (der aeltere Nachzuegler *ist* das Minimum). Mein Plan sagte
   das Gegenteil, und **Spec §5.2 trug dasselbe falsche Beispiel**: „beide
   nach zehn Events in Reihenfolge gruen" gilt nicht fuer das
   Ueberschreiben — nach zehn Events staende dort das zehnte. Die Fassung,
   die das Argument meint, ist das **Nie-Nachziehen** (`first_seen` bleibt):
   gruen in Reihenfolge, rot beim ersten aelteren Nachzuegler. Spiegelbild
   fuer `last_seen`: Ueberschreiben ist dort der natuerliche Fehler.
   **Haikus Diagnose „test naming is misleading" ist falsch** — die
   Testnamen stimmen, das Plan-Docstring stimmte nicht. Und: **der falsche
   Docstring steht wortwoertlich im Baum** (`test_projection_derive.py:110-
   114`: „with `first_seen=addition.first_seen` this test fails and the one
   above stays green"), waehrend haikus eigener Bericht das Gegenteil misst.
   „Ein Kommentar ist eine Behauptung" — im selben Commit verletzt.
2. **`from __future__ import annotations` in allen drei neuen Modulen**, null
   Vorkommen sonst im Projekt (`git grep` auf `44bdc66`). In `worker.py`
   stehen `Mapping`/`Sequence`/`EventRow`/`UnitRow` ohnehin zur Laufzeit
   (Dataclass-Felder, wie `contract/rows.py` es haelt) — das `__future__`
   ist dort ueberfluessig. In `chronicle.py`/`source_stats.py` reicht PEP
   649 (3.14) fuer TYPE_CHECKING-Importe in Signaturen. Haiku hat eine
   fremde Idiomatik eingefuehrt statt das Hausmuster eine Ebene hoeher zu
   kopieren. Plandefekt dahinter: mein `worker.py` hatte die
   Dataclass-Feldtypen unter TYPE_CHECKING → TC004 mit
   `runtime-evaluated-decorators`.

Ruling T4-b: **Spec §5.2 und Plan (Aufgabe 4 Schritt 6, Aufgabe 5 Schritt 7)
  korrigiert, datiert.** Die falsche Fassung ist das Nie-Nachziehen; die
  Messung wird **zweifach**: (a) Nie-Nachziehen → Nachzuegler-Test rot,
  In-Order gruen; (b) Ueberschreiben → In-Order rot, Nachzuegler gruen. Das
  Paar faengt beide natuerlichen Fehler, und jeder Test hat eine Mutation,
  die genau ihn faellt. Haette Aufgabe 5 das alte Beispiel in
  `projections.md` geschrieben, waere ein falsches Beispiel eingefroren
  worden. Kosten, falls falsch: zwei Absaetze.

Ruling T4-c: **Fixrunde 1 folgt der Pruefung, nicht umgekehrt** — der
  Pruefer sieht Bericht und Diff mit haikus Messung drin; findet er die
  Widersprueche selbst, sind es seine Befunde; findet er sie nicht, fuege ich
  meine zwei gemessenen hinzu. Eine Fixrunde vor der Pruefung kostete eine
  zweite Pruefung. Nicht vorverurteilen: der Pruefer bekommt die Tatsachen
  (Docstring vs. Bericht; `__future__` neu im Baum), nicht das Verdikt.

Pruefer (sonnet) mit `review-44bdc66..6f5667a.diff`.
Spec/Plan-Korrektur committet als `675b85a` (zwischen Aufgabe-4-Commit und Fixrunde; FIX_BASE bleibt `6f5667a`, das Paket der Fixrunde enthaelt dann auch diesen Doku-Commit).
Pruefer Aufgabe 4: sonnet, Agent `a8dc56e2e9f73b0d6`.

## Aufgabe 4 — Pruefung (sonnet): nicht freigegeben, 1 Hoch, 1 Mittel, 1 Niedrig

Code, Arithmetik, Signaturen, Namen, Importgrenzen, Tutorial, Zahlen: alles
stimmt. Beide Mutationen selbst gefahren: (a) Ueberschreiben → **zwei** Tests
rot (`…aggregates_a_batch_per_source` **und** `…adds_counts…`, beide haben
In-Order-Daten), Nachzuegler gruen; (b) Nie-Nachziehen → genau der
Nachzuegler-Test rot. Testcode ist richtig und deckt beide Fehlfassungen.

**Hoch:** Docstring `test_projection_derive.py:109-114` behauptet die
  Brief-Erwartung, die der Umsetzer selbst widerlegt hat — unkorrigiert im
  Baum, auch nach `675b85a` (das nur Spec/Plan anfasste).
**Mittel:** `from __future__ import annotations` in drei Dateien, 0 Vorkommen
  vorher. **Gemessen:** ohne die drei Zeilen sind ruff/pyright/Tests gruen;
  mit Brief-Wortlaut in `worker.py` (Feldtypen unter TYPE_CHECKING) feuert
  TC004 viermal — **mit und ohne `__future__` gleich**. Die wirksame
  Korrektur war die Importverlagerung, nicht der `__future__`-Import; die
  Berichtsbegruendung (PEP 563) war in der Kausalitaet falsch.
**Niedrig:** zwei `— frozen design record`-Marker an `{ref}`projections`` —
  nicht Tor-erzwungen (gemessen: alle fuenf `test_docs_references` ohne sie
  gruen) und semantisch falsch: `{ref}` zeigt auf eine lebende Seite.

Ruling T4-d: **1b-Code zitiert nie `§` des eigenen Specs.** Der Spec ist bis
  Aufgabe 8 nicht eingefroren, also waere `(frozen design record)` eine
  falsche Behauptung; nackt laesst der Riegel es nicht durch. Also `{ref}`
  auf die Seite — auch wenn der betreffende Abschnitt dort erst Aufgabe 5
  schreibt: das Label existiert, der Verweis loest auf, am Ende des Zweigs
  traegt die Seite das Argument. Deckt sich mit Aufgabe 8 Schritt 2 im
  Plan. Kosten, falls falsch: ein Verweis, der eine Aufgabe lang auf eine
  Seite ohne den Abschnitt zeigt.

Fixrunde 1 an haiku (`a480383d00a1580b5`) mit exakten Edits: Docstring-Text
vorgegeben (beide Mutationen, kein `§`), drei `__future__`-Zeilen raus,
zwei Marker raus, Berichtskorrektur, Commit-Botschaft vorgegeben.
FIX_BASE = `6f5667a` (das Paket enthaelt dann auch `675b85a`).

Task 4: fix round 1/5 (F1-F4 gemeldet behoben; commit `96de1b5`; sechs Tore
  gruen, 211 passed). Selbst gemessen vor der Nachpruefung: `§`/Marker in der
  Testdatei **0**, `from __future__` im Baum **0**, Docstring woertlich der
  vorgegebene Text. Haikus Formulierung „kept only on § references" war nur
  unscharf — es gibt kein `§` mehr. Fix-Paket `review-6f5667a..96de1b5.diff`
  enthaelt zwei Commits (`675b85a` Controller, `96de1b5` Fix).
Nachpruefer Aufgabe 4: sonnet, Agent `a914888446559003b`.

Nachpruefung (sonnet): F1, F2, F3 **ADDRESSED** — beide Mutationen selbst
  gefahren, Docstring deckt sich wortgenau; kein `§`, kein Marker, kein
  `__future__`; `worker.py` Laufzeit-Importe stehen; keine neuen Schaeden;
  211 unveraendert. **F4 NOT ADDRESSED:** der Bericht widerruft „test naming
  is misleading" nicht (nur ein `[RESOLVED]`-Tag am alten Satz), und Zeile 96
  sagt „The `min()`-Funktion (never update) fails the regression test alone" —
  `min()` ist die richtige Implementierung und faellt nichts.

Task 4: fix round 1/5 (3 addressed, 1 open — F4 Berichtstext; commits
  6f5667a..96de1b5)

Ruling T4-e: **F4 bekommt eine Runde 2, obwohl es nur den Bericht betrifft.**
  Die Berichte dieses Plans werden am Ende wie die des letzten unter
  `docs/superpowers/sdd/` ausgeliefert, als Provenienz fuer die
  Ruling-Zitierungen im Code. Ein Bericht, der die Umkehrung ein drittes Mal
  falsch erklaert, waere dann eingefroren — genau das Gegenteil des Zwecks.
  Haiku hat die Erklaerung zweimal verdreht, also bekommt es den Text
  woertlich, nicht die Aufgabe, ihn zu formulieren. Kein Commit, keine Tore:
  die Datei ist nicht versioniert. Kosten, falls falsch: zwei Minuten haiku.

Fixrunde 2 an haiku (`a480383d00a1580b5`), zwei Saetze vorgegeben.

Task 4: fix round 2/5 (F4 Berichtstext, zwei Saetze ersetzt — Z. 96 `min()`-Satz, Z. 116 Widerruf; kein Commit, unversionierte Datei). Nachpruefung F4 an denselben Nachpruefer (`a914888446559003b`).

Nachpruefung Runde 2 (sonnet): **F4 ADDRESSED** — Widerruf steht
  ausdruecklich, `min()` nirgends mehr als Mutation, Zuordnungen richtig.

Task 4: complete (commits 44bdc66..96de1b5, review clean after 2 fix rounds)

Bilanz haiku: 62 + 30 + 8 Werkzeugaufrufe, ~280k Tokens ueber drei Runden;
sonnet in Aufgabe 3: 74 Aufrufe, 143k Tokens, eine Runde. Haiku hat die
Transkription sauber geliefert und die Mutation **richtig gemessen** — das
war der Fund des Tages gegen meinen Spec. Aber zwei Urteilsfehler (falsche
Deutung der eigenen Messung; fremde Idiomatik eingefuehrt), beide zweimal
nachzuarbeiten. **Ergebnis fuer den Modellboden:** haiku traegt fuer reine
Transkription mit Toren; sobald eine Messung zu *deuten* oder ein
Hausmuster zu *erkennen* ist, kostet es Runden. Fuer 5-8 bleibt opus.

---

## Aufgabe 5 — Dispatch

BASE: `96de1b5`. Brief `task-5-brief.md` (543 Zeilen), extrahiert nach
`675b85a`, traegt die korrigierte `first_seen`-Fassung (Z. 504 geprueft).

Ruling T5-a: **Sechs Test-Docstrings im Brief zitieren nackt `Spec §n.n`** —
  `§5.2`, `§5.4`, `§4.1`, `§3.3`, `§1.1`, `§5.3`. `test_no_bare_paragraph_
  references_remain` faengt jedes. Nach T4-d (1b-Code zitiert nie `§` des
  eigenen Specs, der nicht eingefroren ist) werden alle sechs zu
  `{ref}`projections`` oder zu Prosa ohne `§`. Plandefekt, meiner; in den
  Dispatch statt den Umsetzer in den Riegel laufen zu lassen. Kosten, falls
  falsch: nichts — der Riegel haette es ohnehin erzwungen, nur eine Runde
  spaeter.
Umsetzer Aufgabe 5: opus, Agent `a96c7d6b083a4624a`. Bericht nach `task-5-report.md`.

## Aufgabe 5 — Bericht: DONE_WITH_CONCERNS, Commit `49086f8`

220 passed (= Vorhersage), Coverage 96.79 %, `48 files`, sechs Tore gruen.
Hypothesis 25 Beispiele. Abbruchmessung deckungsgleich mit dem Brief
(`up_to_id 4`, 8 Zeilen, Folgelauf 6 bis 10). Versionsbump mit Kontrolle,
Mutation „Ausloeser entfernt" → 2 failed. **Sieben** nackte `§` ersetzt, nicht
sechs (`_force_rebuild` trug ein siebtes — meine Zaehlung war um eins
daneben). Fuenf Suppressions bleiben.

**Bedenken 1 ist der zweite konzeptionelle Fund gegen Spec §5.2** — und
  wieder gemessen, nicht gelesen: der Vergleich inkrementell/neu gebaut
  **kann** eine falsche `merge`-Arithmetik nicht fangen, weil `merge` auf
  beiden Wegen liegt (Neubau faltet den Stapel ueber dieselbe Funktion).
  Nie-Nachziehen-Mutation → `incremental == rebuilt` **bleibt gruen**, rot
  wird nur die festgenagelte `first_seen`-Zusicherung. Ueberschreib-Mutation
  → alle neun Worker-Tests gruen (der letzte Event ist zufaellig der
  aelteste). Der echte Ein-Weg-Fehler (`write` mischt mit `None` statt der
  gespeicherten Zeile) → Vergleich **und** Eigenschaft rot, reine Tests
  gruen. Die Zusage haelt durch **drei Schichten**. Der Umsetzer hat es auf
  die Seite und in den Docstring geschrieben und den Spec richtigerweise
  nicht angefasst.

Ruling T5-b: **Spec §5.2 bekommt den zweiten datierten Korrekturblock**, von
  mir, vor §5.3: der Vergleich faengt die Buchfuehrung des inkrementellen
  Wegs, nicht die Arithmetik; drei Schichten tragen die Zusage. Mein
  Abschnitt sagte „nur der Vergleich faengt den falschen inkrementellen
  Schritt" — richtig fuer die Buchfuehrung, falsch fuer die Arithmetik.
  Kosten, falls falsch: ein Absatz.

**Eigener Fund beim Lesen des Berichts, am Code bestaetigt:**
  `ProjectionGap` feuert nur bei **leerem** `read` (`worker.py:115`). Eine
  Luecke in der **Mitte** — id 5 fehlt, `read(from_id=5)` liefert 6..10 —
  wird **nicht** erkannt: der Arbeiter verarbeitet 6..10 und setzt
  `up_to_id = 10`. Das ist genau der „silent loss", den der Docstring des
  Fehlertyps ausschliessen will. **Mein Entwurfsfehler** im Plan. Dazu
  Bedenken 3 (`batch_size=0` → `LIMIT 0` → leeres Lesen → irrefuehrender
  `ProjectionGap`) und Bedenken 2 (`ProjectionGap` ungetestet). An den
  Pruefer als Frage; Fixrunde danach gebuendelt.

Pruefer (opus) mit `review-96de1b5..49086f8.diff`.
Pruefer Aufgabe 5: opus, Agent `a375ae89598328ec5`. Spec-Korrektur §5.2 (zweiter Block) als eigener Commit nach `49086f8`; FIX_BASE fuer die Fixrunde bleibt `49086f8`.

Ruling T5-c: **`catch_up` prueft Lueckenlosigkeit, nicht Leere, und weist
  `batch_size < 1` als Aufruferfehler ab.** Plan (Aufgabe 5 Schritt 4)
  entsprechend geaendert und committet, damit Plan und Fix uebereinstimmen.
  Die Pruefung vergleicht die gelesenen ids mit `range(up_to_id + 1, …)` —
  eine Liste von hoechstens 500 Ganzzahlen. Kosten, falls falsch: eine
  Vergleichszeile; der Gewinn ist, dass `ProjectionGap` tut, was sein
  Docstring verspricht. Die drei Tests (Luecke in der Mitte, `batch_size=0`,
  quellenloser Stapel → frueher `return`) kommen mit der Fixrunde in Plan und
  Baum.

## Aufgabe 5 — Pruefung (opus): nicht freigegeben, 1 Erheblich, 3 Mittel, 8 Gering

Alle drei Mutationen selbst gefahren, Zahl fuer Zahl mit der Seite
deckungsgleich; Tutorial mit Seed 2553335422 Zeile fuer Zeile reproduziert;
Dreischichten-Darstellung als **ehrlich** beurteilt („measuring that was worth
more than the measurement it confirmed" ist das Gegenteil von Beschoenigen).

**F1 (Erheblich) — bestaetigt und verschaerft meinen Fund T5-c:** `if not
  events` kann fuer **keine** Luecke feuern. Die Spitze hat `id = tip.id >=
  up_to_id + 1` und `read` filtert `id >= from_id`, also ist das Ergebnis nie
  leer, solange `limit >= 1`. Die Bedingung ist aequivalent zu
  `batch_size == 0`. Gemessen im Container: Event 5 geloescht bei
  `up_to_id 4`, `catch_up` → `events=5 up_to_id=10`, projiziert
  `[1,2,3,4,6,7,8,9,10]`, **kein** `ProjectionGap`. Drei Behauptungen im Baum
  (Docstring `core/errors.py`, `projections.md:74-76`, Commit `49086f8`) gegen
  eine Messung. `worker.py:116` unabgedeckt — der `raise`-Block liesse sich
  loeschen, ohne dass einer von 220 Tests rot wird. Ein Fehler **des
  Briefs**, treu umgesetzt.
**F2 (Mittel):** `batch_size=0` → irrefuehrender `ProjectionGap`;
  `batch_size=-1` → rohe `DataError` (`LIMIT must not be negative`)
  unuebersetzt. `append` prueft seine Stapelgroesse, `catch_up` nicht.
**F3 (Mittel):** Seite traegt Schicht 1 und 3; Schicht 2 (festgenagelte
  Zusicherung faengt Arithmetik Ende-zu-Ende) nur negativ. Ein Satz.
**F4 (Mittel):** „fails, and alone" (`projections.md:111`) — baumweit faellt
  Mutation A zwei Tests. Einschraenken.
**F5-F7 (Gering):** drei `{ref}`projections`` zeigen auf Punkte, die die
  Seite nicht traegt: Truncate-plus-Null-Weg (`_force_rebuild`), Kommandozeile
  (`Outcome` — Vorgriff auf Aufgabe 6), quellenloses Event fehlt in Statistik.
**F8 (Gering):** „this wrapper is twenty lines" — gemessen 36 / 27 ohne
  Leerzeilen. Rhetorische Zahl, in diesem Baum ein Befund.
**F9-F12 (Notizen):** `write` koennte sich via `store.begin()` eine eigene
  Transaktion nehmen, Typsystem verhindert es nicht; Abbruch zwischen
  Versionspruefung und erstem Stapel laesst `rebuilt_from` verloren gehen
  (Folgelauf meldet `None`) — **fuer Aufgabe 6**; keine Sperre auf
  `projection_state`, zwei gleichzeitige `catch_up` unterzaehlen — heute kein
  Weg dorthin, **offener Punkt fuer die Warteschlange** (Spec §10);
  `version` ohne `CHECK > 0`.
**Seite:** dritter Absatz von „Why there are no gaps to worry about"
  (Z. 74-76) ist durch F1 **falsch** („the worker doesn't step over one
  either"), und `{ref}`silent-losses`` dort zeigt auf eine Seite, die mit
  „None of them is a defect that stayed in the code" schliesst.
**⚠️ Nebenbei:** Pruefer zaehlt **vier** Suppressions im Baum, CLAUDE.md sagt
  fuenf, und er schreibt die `S603`-Entfernung `36464d7` zu — das stimmt
  nicht, sie fiel in Aufgabe 1 (`afcbe11`) und CLAUDE.md wurde dort auf fuenf
  gesetzt. **Selbst gemessen** (siehe naechster Eintrag), bevor ich es
  weiterreiche.

**Suppressions selbst gemessen: fuenf** (`A001` docs/conf.py, `C901`, `S607`,
  2× `DTZ001`), CLAUDE.md sagt fuenf. Der Pruefer hat sich verzaehlt —
  vermutlich `docs/conf.py` nicht mitgezaehlt, weil ruff es nicht prueft;
  CLAUDE.md fuehrt es genau deshalb als die fuenfte, „die kein Tor erreicht".
  **Kein Befund.** Haette ich es ungeprueft weitergereicht, haette der
  Umsetzer CLAUDE.md auf vier gesetzt — falsch.

Ruling T5-d: **F6 (`Outcome`-Docstring → Kommandozeile) bleibt als Vorgriff
  auf Aufgabe 6**, die den CLI-Abschnitt der Seite schreibt. Ein Verweis, der
  eine Aufgabe lang auf eine Seite ohne den Abschnitt zeigt, ist dasselbe
  Muster wie T4-d. **In den Dispatch von Aufgabe 6**, zusammen mit F10
  (`rebuilt_from` geht bei Abbruch zwischen Versionspruefung und erstem
  Stapel verloren → Folgelauf meldet `caught up` statt `rebuilt` — die
  Kommandozeile soll das wissen, wenn sie `_describe` schreibt).

Ruling T5-e: **F11 (keine Sperre auf `projection_state`, zwei gleichzeitige
  `catch_up` unterzaehlen) wird offener Punkt in Spec §10**, nicht gebaut: 1b
  hat keinen asynchronen Produzenten, die Warteschlange (Spec §1.1) ist auf
  den ersten Konnektor vertagt, und genau dort gehoert die Sperre hin —
  `SELECT … FOR UPDATE` auf der Zustandszeile oder ein Advisory-Lock je
  Projektion. Trage ich beim Einfrieren (Aufgabe 8) ein. F9 (`write` koennte
  sich eine eigene Transaktion nehmen) und F12 (`version` ohne `CHECK > 0`)
  ebenso als Notizen. Kosten, falls falsch: eine Unterzaehlung, die heute
  niemand ausloesen kann.

Fixrunde 1 an den Umsetzer (`a96c7d6b083a4624a`): F1 + F2 mit Plan-Code, drei
Tests (Luecke in der Mitte, `batch_size < 1`, quellenloser Stapel), Docstring
`ProjectionGap`, fuenf Seitenstellen (falscher Luecken-Absatz, F3, F4, F5,
F7), F8. Testzahl → **223**, Tutorial neu. FIX_BASE `49086f8` (Paket
enthaelt dann `b465cdc` und `fd46f94`).

Plan nachgefuehrt: drei Tests in Aufgabe 5 Schritt 2, Vorhersagen 223 / 231 /
231 / 231 (Aufgabe 6 bringt acht Tests, der Plan sagte das schon), Selbstpruefung. Wird mit dem naechsten Controller-Commit
festgehalten.

Plan-Commit `4f01d8d`: drei Tests in Aufgabe 5 Schritt 2, Zahlen 223 / 231 /
231 / 231. Aufgabe-6-Brief danach neu gezogen, damit er die 231 traegt.

**Korrektur sofort danach:** Aufgabe 6 hat im Plantext **neun** `def test_` (der
Vorab-Scan `ec1c666` brachte den Test fuer das leere Log, der Ledger sagte
„Endstand 229", die Zahl im Plan blieb bei 228 und die Selbstpruefung bei
„acht, nicht neun"). Nachgezaehlt gegen den Text: 223 / **232** / 232 / 232.
Die 231 in 4f01d8d war von der falschen Planzeile abgeschrieben statt gezaehlt.

## Task 5 — Fixrunde 1: Bericht

Commit `f2687a6` (Umsetzer, Opus). 12 Tests in der Datei, **223** gesamt,
sechs Tore gruen (ruff / format 48 files / pyright 0 / 4 kept / 223 passed
97.10 % / html+vale 21 files+linkcheck). `worker.py` und `source_stats.py`
auf 100 %. Tutorial neu aus Seed 316378120, ohne `rootdir:`.

Zwei Stellen ueber den Auftrag hinaus, beide richtig: der vorausblickende
Satz der Einleitung („never has to worry about a gap" → „can't arise and is
checked for all the same") und die Mutationszahl am Seitenende („other seven
green" → „other ten green", neu gemessen `2 failed, 10 passed`). `onwards`
(britisch, Vale 1 error) → „the run that has to start at `up_to_id + 1`".

**Widerspruch 1 (angenommen):** mein Brief sagte „der Lueckentest war gruen
gegen den alten Code". Falsch formuliert — der Test erwartet `ProjectionGap`
und ist gegen den alten Code rot mit `DID NOT RAISE`; was gruen blieb, war
der alte *Arbeiter*, der 6..10 projizierte. Der Umsetzer hat das mit einer
Wegwerfsonde ohne die Erwartung gemessen und die Commit-Zeile umgeschrieben.
Gleicher Satz stand in meiner Plan-Notiz (4f01d8d) — korrigiert im naechsten
Plan-Commit. Sonde `tests/test_zz_gap_probe.py` ist nicht im Baum (geprueft).

**Widerspruch 2 (Hinweis, Ruling T5-f):** `batch_size < 1` wirft `ValueError`
und ist damit der einzige Fehler in `core`, der nicht unter `PreviouslyError`
haengt. **Bleibt so:** die Kommandozeile reicht `batch_size` nicht durch
(Aufgabe-6-Brief geprueft), also kann kein Nutzer ihn ausloesen; ein
Programmierfehler heisst in Python `ValueError`. Faellt neu, sobald ein
Kommando `--batch-size` anbietet. Kosten, falls falsch: eine Ausnahmeklasse
umbenennen.

**Vermischung:** der Umsetzer hat mit `git add -A` meine zweite Plan-Korrektur
(231 → 232, fuenf Zeilen) in `f2687a6` mitgenommen; mein eigener Commit dazu
fand nichts mehr vor. Die Zeilen sind richtig, die Botschaft von `f2687a6`
nennt sie nicht. Keine History-Umschreibung; der naechste Plan-Commit nennt
es. Lehre fuer die Dispatches: Plan-Commits des Controllers **vor** dem
Dispatch oder nach dem Bericht, nie waehrend der Umsetzer arbeitet — oder
der Umsetzer bekommt die Dateiliste statt `git add -A`.

Plan-Commit `71dc078`: Notiz zum Lueckentest korrigiert (rot mit DID NOT RAISE,
Sonde als Messung), Vermischung in f2687a6 benannt. Ruling T5-g: **Commit
nicht teilen** — Inhalt richtig, History bleibt, 71dc078 nennt es.

Re-Review Fixrunde 1 (Sonnet) dispatcht: FIX_BASE 49086f8, HEAD 71dc078,
Paket review-49086f8..71dc078.diff (5 Commits, 54 KB). Drei gezielte
Pruefauftraege: Zahlen in der Prosa („other ten green", 36/27/21), die
Arithmetik der Lueckentest-Zusicherung (4, 4, 8), Aufloesbarkeit des
`{ref}hash-chain` im Worker-Kommentar.

## Task 5 — Re-Review Fixrunde 1 (Sonnet): sauber

Alle zehn Befunde ADDRESSED mit file:line. Die drei Zusatzpruefungen bestanden:
12 `def test_`, Mutation D trifft nur die zwei Versionstests → „other ten
green" stimmt; (4, 4, 8) nachgerechnet (dritter `insert_chronicle` scheitert,
2 Einheiten je Event aus `split_plaintext("one\n\ntwo")`, 4 × 2 = 8);
`(hash-chain)=` existiert in `docs/explanation/hash-chain.md:1`. Der Pruefer
hat zusaetzlich die kurze Schlusscharge bedacht: `expected` aus `len(ids)`,
nicht aus `batch_size`, also kein falscher `ProjectionGap` am Logende.

Task 5: minor (deferred): Docstring von `catch_up` (`worker.py:80-96`) nennt
  den `batch_size`-Riegel nicht in der Prosa, nur der Inline-Kommentar am
  `raise`. Fuer die Fixwelle nach der Endpruefung; Aufgabe 6 fasst
  `worker.py` nicht an.

Task 5: complete (commits 49086f8..71dc078, Fixrunde 1, Re-Review sauber)

## Task 6 — Dispatch

BASE `71dc078`. Umsetzer Opus (vier Dateien, Kommandozeile mit exakten
Ausgabeformaten, zwei Doku-Seiten; Plan traegt den Code, aber die Seiten
brauchen Urteil). Dispatch-Text im Scratchpad, traegt: echte Signaturen aus
dem Baum (`read_chronicle`, `read_source_stats`, `Outcome`-Felder,
`PROJECTIONS`-Reihenfolge), Aufloesungen (`escape_field` statt `_escape`;
`_lag_line` statt `_report_lag`; P-1-Reihenfolge; F10 als Satz in „Saying
what it doesn't know"; `since == until` als eine Assertion; F6 landet durch
die neuen Abschnitte; `log`-Hilfetext „print the chronicle" ist seit heute
falsch → korrigieren; nur die eigenen Dateien stagen). Testzahl 232,
Tutorial nur der Testblock.

## Vorbereitung Aufgabe 7 (waehrend Aufgabe 6 laeuft)

Gegen den Baum geprueft: der Arbeiter leert die Tabelle und schreibt eine
frische Zustandszeile in **einem** Zweig fuer `state is None` und
`version != ` — `DELETE FROM projection_state` + `project` → `built` stimmt.

Ruling T7-a: **der `:::{warning}`-Text des How-tos im Plan ist so nicht
  richtig** („until the next `project` the chronicle is empty"). Nach dem
  DELETE stehen die Zeilen von `p_chronicle` noch; die Lesekommandos drucken
  sie und melden das ganze Log als Rueckstand auf stderr; geleert wird erst in
  der ersten Transaktion von `project`, aufgefuellt stapelweise — waehrend
  eines langen Neubaus ist die Chronik partiell, mit Rueckstandszeile.
  Dispatch beschreibt das Verhalten, der Umsetzer formuliert die Warnung.
  Kosten, falls falsch: eine Admonition.

Ruling T7-b: **`database-schema.md` Einleitung nennt sechs Tabellen in zwei
  Gruppen** (drei Log, drei Projektionen, `{ref}projections`); das erDiagram
  bleibt bei den dreien des Logs, die Bildunterschrift sagt es. Nicht
  umzeichnen — die Projektionsabschnitte beschreiben den FK schon.
  Kosten, falls falsch: eine Bildunterschrift.

Vokabular-Basis selbst gemessen: 15 Eintraege, 11 klein — deckt sich mit dem
`.vale.ini`-Kommentar („Eleven of the fifteen"). Vale derzeit 21 Dateien, das
How-to macht 22. Labels `add-a-migration`, `tombstone-seam`, `projections`
existieren. `tests/test_schema.py:351` zitiert den falschen Testnamen (Task-2-
minor) → in Aufgabe 7 mit einem Satz in der Commit-Botschaft.

Dispatch-Entwuerfe fuer Aufgabe 7 und fuer die Pruefung von Aufgabe 6 liegen
im Scratchpad (`task-7-dispatch.md`, `task-6-review-dispatch.md`, letzterer
mit Platzhaltern HEAD_SHA / DIFF_FILE).

## Task 6 — Bericht

Commit `a2dbe17` (Opus), DONE_WITH_CONCERNS. 7 Dateien +553/−54, **232**
Tests, 97.31 %, `cli.py` 100 %, sechs Tore gruen, acht Mutationen je rot
gemessen mit Kontrolle. Tree clean, keine Sonde im Baum (geprueft).

Selbst nachgemessen: `cli.py` hat **19** `print` (grep und
`ruff --select T201` stimmen ueberein) — die Zahl „thirteen" in
`pyproject.toml` (T201-Begruendung) und `test_docs_references.py` waere mit
dem Commit falsch geworden; der Umsetzer hat beide korrigiert (zwei Dateien
ueber die Liste aus Aufloesung 8 hinaus). **Richtig so** — eine Behauptung,
die der eigene Commit falsch macht, zieht man im selben Commit nach.

Ruling T6-a: **Plan-Argument zu C901 war falsch** — sieben `if` plus `except`
  haetten `main` auf 9 gegen Schwelle 10 gebracht, nicht „auf die Schwelle";
  gemessen vom Umsetzer, plausibel (1 + 7 + 1). Tabelle bleibt (2 statt 9),
  Kommentar und Botschaft nennen die Messung. Plan-Nachtrag folgt.
Ruling T6-b: **zwei Tests umbenannt und erweitert**, damit `rebuilt:` und der
  `stats`-Rueckstand — beide in `cli.md` versprochen — einen Test haben:
  `test_project_on_an_empty_log_is_up_to_date_at_zero_but_still_names_a_rebuild`,
  `test_both_reading_commands_report_the_lag_on_stderr_and_only_there`.
  Neun Tests, 232. Plan-Nachtrag folgt (Namen).

Bedenken des Umsetzers, Zuordnung:
- README `the four commands` / „no projections" veraltet → **Aufgabe 7** (Brief
  Schritt 3 deckt es).
- Tutorial-Ueberschrift „Look at the chronicle" steht ueber `previously log`
  und kollidiert jetzt mit dem Kommando → **in den Dispatch von Aufgabe 8**.
- Nichts haelt die zwei stderr-Saetze in `cli.md` gegen den Code (Luecke seit
  1a fuer `log`/`show`) → **deferred**, Fixwelle nach der Endpruefung oder
  offener Punkt; ein Test wuerde die 232 bewegen.
- Ruling P-1 im Test-Docstring nicht nachschlagbar, Ledger liegt noch im
  git-ignorierten `.superpowers/` → **Ruling T6-c: der Ledger wird am Ende
  dieses Plans als eigener Commit nach `docs/superpowers/sdd/2026-10-04-
  stufe-1b-projektionen/` geschoben**, wie beim Doku-Plan („ja, eigner
  commit") und wie CLAUDE.md es seit heute verlangt. Der Plan hat den Schritt
  nicht; Nachtrag als Schritt nach Aufgabe 8, vor `finishing-a-development-
  branch`. Kosten, falls falsch: ein Commit.

Review-Paket `review-71dc078..a2dbe17.diff`; Pruefer Opus (sieben Dateien,
Ausgabeformate vertraglich, zwei Doku-Quadranten, zwei Dateien ausserhalb der
Liste).

Plan-Commit `ccaa021`: Nachtraege T6-a (C901-Korrektur), T6-b (Testnamen),
zwei Dateien mehr in Aufgabe 6, und der neue Schlussschritt „Nach Aufgabe 8:
Das Ausfuehrungsprotokoll wird eingecheckt" (T6-c) — Reihenfolge: nach
Endpruefung und Fixwelle, vor Loeschen des Arbeitsverzeichnisses, ohne die
`review-*.diff`. Committet waehrend der Pruefer liest (read-only, liest das
Paket) und kein Umsetzer laeuft.

Fuer das auszuliefernde Protokoll nachgetragen, was bisher nur in der
Sitzung lag: `task-5-fix-1-brief.md` (Fixauftrag wortgetreu, mit dem
widerlegten Satz markiert), `task-5-re-review-1.md` (Re-Review wortgetreu),
`task-6-dispatch.md`, `task-6-review-dispatch.md`. Ab jetzt wird jeder
Pruefbericht beim Eintreffen als `task-N-review.md` abgelegt; die Pruefungen
der Aufgaben 1-5 liegen nur als Befundlisten in diesem Hauptbuch.

## Task 6 — Pruefung (Opus): Needs fixes

Wortgetreu in `task-6-review.md`. Zwei Important, beides Prosa-Behauptungen;
sieben Minor; zwei ⚠️ (acht Mutationen nicht nachgemessen — ich zitiere sie
nirgends als gemessen; Torausgaben im Bericht mit `...` gekuerzt).

**I1 — `cli.py:333-334` C901-Kommentar „one branch short of breaking the
gate".** Gemessen vom Pruefer: C901 feuert strikt oberhalb der Schwelle
(heutiges `main` = 2 wird bei `max-complexity = 2` nicht gemeldet, bei 1 schon);
Kette mit 7 Kommandos = 9, mit 8 = 10 — bei Projektschwelle 10 **noch gruen**;
das Tor risse erst beim neunten (11 > 10). Zwei Zweige Luft, nicht einer.
**Meine Plan-Korrektur in ccaa021 hatte denselben Fehler eine Stufe kleiner**
(„einen Zweig unter der Schwelle") — nachgezogen, naechster Plan-Commit.
Ruling T6-d: **Commit-Botschaft von a2dbe17 bleibt** (gleiche falsche Zeile);
keine History-Umschreibung, der Fix-Commit nennt die Abweichung. Dazu: die
13 im Kommentar als historische Zahl zu einer Fassung kennzeichnen, die es im
Baum nicht mehr gibt.

**I2 — `cli.md:19`** `stats` Exit 2 „The input was invalid, or storage raised
an error" — `stats` hat keine Argumente. **Plan-mandatiert** (Brief Schritt 5);
Plan korrigiert (Notiz unter Schritt 5). Zelle → „Storage raised an error."

Minors, Zuordnung (Ruling T6-e):
- in die Fixrunde (billig, gleiche Dateien): `cli.md:83` „No event was
  projected, and the version was unchanged."; `cli.md:129` Begruendung aus dem
  Referenz-Quadranten streichen, Tatsache bleibt; `pyproject.toml:90-94`
  Satz und Befehl in Deckung bringen („with the per-file table emptied for the
  measurement") und „gone stale" → „was wrong"; `--limit < 1` bei `chronicle`
  abweisen (Exit 2, Meldung nennt `--limit`) — als Zusicherung in den
  bestehenden Limit-Test gefaltet, Zahl bleibt 232; `row.source or ''`-Zweig
  (cli.md:99 „two empty fields") durch ein quellenloses Event per
  `storage.insert_event` im bestehenden Chronik-Test erreichen.
- **deferred** in die Fixwelle nach der Endpruefung: `log --limit` ebenso
  offen seit 1a (gleiche Klasse, nicht diese Aufgabe); `set(sub.choices) ==
  set(commands)` als eigener Test (233 → Tutorial-Retype, das Aufgabe 8
  ohnehin macht — eine Retype fuer alles, nicht zwei).
- P-1 nicht nachschlagbar → T6-c (Schlussschritt), nicht diese Runde.

Fixrunde 1 an den Umsetzer (`a99ba11b6c61a5e51`, Opus). FIX_BASE `a2dbe17`.
Verlangt zusaetzlich: die sechs Torausgaben ungekuerzt in ihren Schlusszeilen.

Plan-Commit `eae7357` (C901-Luft, stats-Zelle). Fixrunde 1 Aufgabe 6 dispatcht,
FIX_BASE `a2dbe17`; `--limit < 1` und der quellenlose Chronikzweig in die
bestehenden Tests gefaltet, Zahl bleibt 232.

## Rueckstandsliste (Stand nach Pruefung Aufgabe 6) — fuer Endpruefung und Fixwelle

Zugeordnet an Aufgaben, noch offen:
- **A7:** `database-schema.md:5` „three PostgreSQL tables" + erDiagram (T7-b);
  `tests/test_schema.py:351` falscher Testname; README „four commands" /
  „no projections"; Warnungstext How-to (T7-a).
- **A8:** Tutorial-Ueberschrift „Look at the chronicle" ueber `previously log`;
  F11 (keine Sperre auf `projection_state`) als offener Punkt in Spec §10,
  F9 (`write` koennte eigene Transaktion nehmen) und F12 (`version` ohne
  `CHECK > 0`) als Notizen dort; Tutorial-Retype zuletzt (Zahl nach der
  Fixwelle messen, nicht 232 annehmen).
- **Schlussschritt (T6-c):** Ledger nach `docs/superpowers/sdd/`.

Fuer die Fixwelle nach der Endpruefung (kein Eigentuemer unter A7/A8):
- `catch_up`-Docstring nennt den `batch_size`-Riegel nicht (Task 5 minor).
- `log --limit < 1` offen seit 1a (gleiche Klasse wie der `chronicle`-Fix).
- Test `set(sub.choices) == set(commands)` (ein vergessener Tabelleneintrag
  wuerde zum `KeyError`-Traceback) → 233, Tutorial-Retype in A8 deckt es,
  wenn die Fixwelle **vor** A8 laeuft — sie laeuft aber danach. Also: Zahl
  aendert sich, A8s Retype wird in der Fixwelle wiederholt. Alternativ in A8
  vorziehen; entscheide ich beim Dispatch von A8 (Ruling folgt).
- Nichts haelt die zwei stderr-Saetze in `cli.md` gegen den Code (seit 1a
  auch fuer `log`/`show`): Erweiterung von
  `test_the_reference_quotes_what_the_code_actually_prints` auf `print(...,
  file=sys.stderr)`-Literale, oder offener Punkt.
- `module-boundaries.md`: Laenge 279 Zeilen / 1a-Vergangenheit auf lebender
  Seite; `:206` Antezedens; `:256` Tempus (Task 1/3 minors).
- `projections.md` Vorgriffssatz Ende Abschnitt 2 (Task 2 minor) — Aufgabe 5
  hat angehaengt; beim Lesen der ganzen Seite in A7 Schritt 2 mitpruefen.

Entschieden, nicht offen: `ValueError` fuer `batch_size` (T5-f); F6 landet
durch A6 (geprueft: `projections.md:84`, F10-Satz im richtigen Quadranten).

Ruling T6-f: **die beiden Testerweiterungen aus der Rueckstandsliste
(`set(sub.choices) == set(commands)`, `log --limit < 1`) bleiben in der
Fixwelle nach der Endpruefung**, nicht in A8. A8 ist Doku (Einfrieren,
Design-Records, Tutorial); ein CLI-Test dort vermischt den Zuschnitt, und die
Endpruefung bringt ohnehin Befunde mit, die Tests nach sich ziehen. Aendert
sich die Zahl, wird das Tutorial in der Fixwelle **noch einmal** aus einem
echten Lauf getippt — das ist die Regel („retype when stale"), kein
Sonderfall. Kosten, falls falsch: ein zweiter Retype, zehn Minuten.

## Task 6 — Fixrunde 1: Bericht

Commit `daea417` (Opus), vier Dateien namentlich gestaged, Tree clean. Kein
Widerspruch; I1 vom Umsetzer selbst nachgemessen (7 → 9, 8 → 10, 9 → 11,
Tabelle 2; C901 feuert strikt oberhalb). Kommentar in drei Teilen: Struktur
zuerst, dann die vier Zahlen mit Kommando, dann beide falschen Fassungen
benannt (Plan: „auf der Schwelle"; a2dbe17: „one short"); 13 als historisch
markiert. a2dbe17-Botschaft unangetastet, daea417 nennt die Abweichung.
`--limit < 1` → `InvalidPayload` vor jedem Lesen (nicht argparse-`type=`, weil
das ueber `parser.error()` nach `sys.exit(2)` ginge — der Weg, den
`_parse_evidence` seit W2 vermeidet); Altverhalten gemessen: `--limit -2` war
ein **Traceback mit Exit 1**, schaerfer als mein Brief sagte. Quellenlose
Zeile als drittes Event **zwischen** den beiden anderen, damit die Ordnung
unter Test bleibt. Beide Zusicherungen rot gemessen, Kontrolle 35 gruen.
Sechs Schlusszeilen ungekuerzt: `All checks passed!` / `48 files already
formatted` / `0 errors, 0 warnings, 0 informations` / `Contracts: 4 kept, 0
broken.` / `232 passed in 26.27s`, 97.32 % / `build succeeded.` · `0 errors,
0 warnings and 0 suggestions in 21 files.` · `build succeeded.`

Re-Review (Sonnet) dispatcht: FIX_BASE `a2dbe17`, HEAD `daea417`, Paket
`review-a2dbe17..daea417.diff` (enthaelt auch Plan-Commit `eae7357`).

## Task 6 — Re-Review Fixrunde 1 (Sonnet): sauber

Alle sieben Befunde ADDRESSED mit file:line (wortgetreu in
`task-6-re-review-1.md`). Pruefer hat C901 „strikt oberhalb" selbst
nachgemessen (`max-complexity = 2` nennt `main` nicht, `= 1` meldet `2 > 1`),
T201 → 19, `--collect-only` 35 in der Datei / 232 gesamt, und fuenf Tore auf
dem aktuellen Baum selbst gefahren (nicht pytest, nicht linkcheck). Keine
History-Umschreibung (a2dbe17 per `git log` gegengeprueft).

Out-of-scope, notiert: der Hauptbericht sagte „26 → 35 in der Datei"; roh sind
es 21 → 30 `def test_`, 35 ist die **gesammelte** Zahl (Parametrisierung bei
Zeile 426). Berichtszahl, nicht Baumzahl — nichts zu fixen, aber die Lehre
steht: „Tests in der Datei" ist zweideutig, gesammelt oder definiert.

Task 6: complete (commits 71dc078..daea417, Fixrunde 1, Re-Review sauber)

## Task 7 — Dispatch

BASE `daea417`. Umsetzer Opus (How-to, Explanation-Abschnitt, README,
Vokabular, zwei Korrekturen aus Task 2 — Urteil ueber Quadranten und
Formulierung, nicht Transkription). Dispatch wortgetreu in
`task-7-dispatch.md` (Rulings T7-a, T7-b; Vokabular-Basis 15/11; nur eigene
Dateien stagen; 232 unveraendert).

## Vorbereitung Aufgabe 8 (waehrend Aufgabe 7 laeuft)

Gemessen: in `core/projection`, `contract/store.py`, `contract/rows.py` steht
**ein** `§`, mit `(frozen design record)` auf der Zeile (Architektur); null auf
den 1b-Spec. Spec §10 hat sieben Punkte, Anker zuerst, Einleitung im Praesens
(„ist gepflegt … solange der Spec lebt") → fuer das Einfrieren umschreiben.
Tutorial: Einleitung Z. 5 „look at the chronicle it produces" und Ueberschrift
Z. 80 „Look at the chronicle" ueber `previously log` — beides seit Aufgabe 6
falsch, beides in A8 (Bedenken des A6-Umsetzers). `design-records.md` nennt
das Ausfuehrungsprotokoll vom 2026-10-03 nicht; kein Link auf das 1b-Protokoll
aus A8 heraus (Verzeichnis existiert erst nach der Endpruefung, `html` wuerde
den toten Link als Fehler werten).

Ruling T8-a: **F11 wird Punkt 8 in Spec §10, F9 und F12 Notizen darunter**,
zitiert mit ihren Pruef-Labels (das Protokoll, das sie traegt, wird
ausgeliefert). Die stderr-Satz-Luecke kommt **nicht** in §10 — sie ist ein
Kandidat der Fixwelle, kein Entwurfs-Punkt.
Ruling T8-b: **die 1a-Spec bleibt unangetastet**, obwohl ihre `Stand:`-Zeile
unter dem eingefrorenen Kopf noch „Status: zur Abnahme" sagt — ein
eingefrorener Bericht wird nicht nachgezogen, das sagt sein Kopf selbst. Fuer
den Betreuer als Beobachtung notiert, nicht als Aufgabe.

Dispatch-Entwurf `task-8-dispatch.md` im Scratchpad; Testzahl ist zu
**messen**, nicht 232 anzunehmen.

## Task 7 — Bericht

Commit `773cf4a` (Opus), DONE_WITH_CONCERNS. Sechs Tore gruen, 232, Vale
**0 errors in 22 files** beim ersten Lauf — **kein Vokabelwort noetig**,
`.vale.ini` unberuehrt (11/15 nachgezaehlt, unveraendert). Der Plan hatte
Treffer vorhergesagt (`upsert`, `denormalization`, `catch-up`); die Seiten
brauchten keines dieser Woerter. Tree clean.

Selbst geprueft:
- Titel `# How to rebuild a projection` statt Brief `# Rebuild a projection`:
  alle drei Geschwister beginnen mit „How to" (gemessen `grep '^# '
  docs/how-to/*.md`). **Ruling T7-c: Umsetzer hat recht, der Brief war der
  Ausreisser.** Label, Datei, Abschnittstitel wie beauftragt.
- `docs/index.md:24` Karte nennt drei How-tos („restore a backup, add a
  migration, check the chain in operation") — das vierte fehlt. **Fixrunde.**
- `README.md:9-10` „the header and the chronicle of a project" ist der
  Zielsatz des Projekts, kein Zustandsbericht; „What it does not do" sagt
  „kein Kopf". **Bleibt** (Ruling T7-d).
- How-to Z. 39 „Both stand at `1`." — Zahl, die kein Tor haelt und beim ersten
  Versionssprung veraltet; **Fixrunde:** die Stelle nennen, nicht den Wert.
- How-to Z. 60 `psql postgresql://previously:previously@localhost:5432/
  previously` — die Wegwerf-Zugangsdaten des Tutorials in einem Operator-
  How-to; **Fixrunde:** Platzhalterform plus Verweis auf die Konfigurations-
  Referenz. Der Satz Z. 65 (`+psycopg`-Praefix wird von libpq als Datenbankname
  gelesen) ist gemessen und bleibt.
- How-to Z. 49 `rebuilt: version 1 -> 2, 12 events, up_to_id 12` — woher die
  12? Pruefer soll klaeren, ob echter Lauf oder erfunden.
- Warnung ohne `stats`: richtig, `DELETE … name = 'chronicle'` trifft nur die
  Chronik; Schlusssatz nennt `source-stats`.
- `projections.md` jetzt 215 Zeilen — Laengenfrage wie `module-boundaries.md`,
  fuer die Endpruefung.

Review-Paket `review-daea417..773cf4a.diff` (16 KB); Pruefer Opus
(Quadranten-Urteil, Zahlen auf Seiten).

## Task 7 — Pruefung (Opus): Needs fixes

Wortgetreu in `task-7-review.md`. Vier Important, alle Einzeiler, zwei Minor.
Der Pruefer hat die `libpq`-Behauptung **unabhaengig** nachgemessen
(`PQconnectdbParams` mit `expand_dbname`: `PQdb` = ganzer String, `PQhost` =
Socket) und den Warnhinweis gegen `catch_up` + Schema (kein FK von
`p_chronicle` auf `projection_state`) geprueft — alle drei Saetze wahr.
Titel „How to …" bestaetigt (T7-c), `stats`-Auslassung als Korrektur des
Dispatch anerkannt, README-Zielsatz kein Befund (T7-d).

I1 `docs/index.md:24` vierte How-to fehlt; I2 „Both stand at `1`" → „Read the
current value there"; I3 drei `text`-Bloecke erfundene Laeufe (12 Events) —
**Ruling T7-e: Prosaform** wie `verify-the-chain.md`, Verweis auf
`cli-reference` fuer den Wortlaut; ein gemessener Wegwerf-Log waere genauso
wenig der Log des Lesers, und die Geschwisterseiten kommen ohne aus. Loest
zugleich den Nebenbefund (nur erste von zwei `project`-Zeilen gezeigt) und die
ungedeckte Kopie des Rueckstandssatzes. I4 Tutorial-Zugangsdaten im
Operatorbefehl → Platzhalterform + `configuration-reference` ersetzt sie.
Minor 1 `:80` zweideutiges `chronicle` → `'chronicle'` im `DELETE`; Minor 2
§4.6 „was verschwindet, ist der Wortlaut" als schaerferer Beleg — beide in die
Runde.

**Fuer Aufgabe 8 (vom Pruefer gefunden):** `README.md:58-70` „The three
specifications below are frozen design records" → vier mit dem Einfrieren;
README in den A8-Dispatch und seine Dateiliste aufgenommen.

Fixrunde 1 an den Umsetzer (`a7d246ce8cf746abd`, Opus), FIX_BASE `773cf4a`,
drei Dateien namentlich; Zahl bleibt 232.

## Task 7 — Fixrunde 1: Bericht

Commit `af5f5de` (Opus), drei Dateien namentlich, Tree clean, How-to 82 → 73
Zeilen. Kein Widerspruch. I1 Karte nennt vier; I2 „Read the current value
there."; I3 alle drei `text`-Bloecke → Prosa, Nebenbefund (nur erste von zwei
Zeilen) damit geschlossen, Rueckstandssatz nicht mehr als Kopie; I4
Platzhalterform, `configuration-reference` ersetzt die Zugangsdaten, libpq-Satz
unberuehrt; Minor 1 `'source-stats'`/`'chronicle'` als SQL-Werte; Minor 2 ein
Satz zu §4.6 („was verschwindet, ist der Wortlaut", `unit.content`). Zwei
Hinweise, keine Widersprueche: ein `cli-reference`-Verweis statt dreimal im
Abschnitt; der `psql`-Befehl ist nicht mehr copy-and-run — der Preis der
Platzhalterform, `:60` sagt, woher die vier Werte kommen. Sechs Schlusszeilen
ungekuerzt (232, 22 files).

Re-Review (Sonnet) dispatcht: FIX_BASE `773cf4a`, HEAD `af5f5de`.

## Task 7 — Re-Review Fixrunde 1 (Sonnet): sauber

Alle sechs Befunde ADDRESSED mit file:line (wortgetreu in
`task-7-re-review-1.md`). Pruefer hat die Prosa gegen `_describe`/`_lag_line`/
`_cmd_project` gelesen (keine Ueberbehauptung), die vier verbleibenden
Codebloecke gezaehlt (Befehle und eine Codeaenderung, keine Ausgabe), `html`
und `vale` selbst gefahren (gruen, 22 files), die §4.6-Uebersetzung gegen
`architektur.md:449-459` gelesen.

Task 7: complete (commits daea417..af5f5de, Fixrunde 1, Re-Review sauber)

## Task 8 — Dispatch

BASE `af5f5de`. Umsetzer Opus (Einfrieren eines deutschen Specs mit §10-
Ergaenzungen in seinem Register, Design-Records, Tutorial als echter Lauf —
Urteil, nicht Transkription). Dispatch wortgetreu in `task-8-dispatch.md`
(T8-a, T8-b; README „three frozen records" → vier; Testzahl messen; F-Labels
mit Nummernraum nennen; kein Link auf das noch nicht existierende sdd-
Verzeichnis).

## Vorbereitung Schlussschritt (waehrend Aufgabe 8 laeuft)

Gemessen `grep -rnoE 'ruling (P|T[0-9]+)-[a-z0-9]+' src tests pyproject.toml |
sort -u` → **16** Zitate, davon **eines** aus diesem Plan: `tests/test_cli.py:504
ruling P-1`. Die anderen 15 (T2-e, T5-b, T6-b ×2, T8-a ×2, T9-a ×3, T9-c,
T10-a ×2, T10-b, T10-c, T10-d) stammen aus der Ausfuehrung davor.

**Befund (Controller, fuer die Fixwelle):** dieser Plan hat Rulings T5-b, T6-b,
T8-a vergeben — dieselben Labels stehen im Baum fuer Entscheidungen des
**anderen** Plans (`tests/test_schema.py:257 ruling T5-b`,
`tests/test_storage.py:309 ruling T6-b`, `tests/test_verify.py:106 ruling
T8-a`). Der Ruling-Namensraum ist je Plan, und nichts im Label sagt, welcher.
Fuer `W3`/`W-3` loest CLAUDE.md das mit dem Bindestrich; fuer Rulings gibt es
keine Konvention. Ruling T8-c: **die Fixwelle qualifiziert das eine 1b-Zitat**
(`ruling P-1` → nennt den Plan, z. B. „ruling P-1 of the 2026-10-04 stage 1b
plan"), **und CLAUDE.md bekommt unter *A ruling citation is provenance* den
Satz, dass Ruling-Labels je Plan vergeben werden und ein Zitat das Plan-
Verzeichnis nennt** — die 15 alten Zitate bleiben, weil sie bis heute
eindeutig waren und ihr Ledger-Verzeichnis das einzige war; wer sie anfasst,
qualifiziert sie. Dem Betreuer ausdruecklich vorlegen: Regelaenderung in
CLAUDE.md. Kosten, falls falsch: ein Satz.

Fuer `index.md` des 1b-Protokolls: „ein Zitat", nicht sechzehn; der
Kollisionshinweis gehoert hinein.

**Befund (Controller), ueber diesen Plan hinaus:** das ausgelieferte Protokoll
`docs/superpowers/sdd/2026-10-03-dokumentation/index.md` sagt „Sechzehn
Kommentare … zitieren Entscheidungen aus dieser Ausfuehrung … Jetzt loest es
auf. Die Rulings stehen in progress.md". Gemessen: von den zehn verschiedenen
Labels im Baum steht **eines** in jenem Ledger (`Ruling T5-b`); T2-e, T6-b,
T8-a, T9-a, T9-c, T10-a, T10-b, T10-c, T10-d fehlen — der Doku-Plan hatte acht
Aufgaben, Labels T9/T10 kann er nicht vergeben haben. Sie stammen aus der
Ausfuehrung des **1a-Plans** (zehn Aufgaben), deren Ledger nie eingecheckt
wurde und auf dieser Platte nicht mehr existiert (kein `.superpowers/sdd/` im
Haupt-Checkout; das Backup-Verzeichnis ist das des Doku-Plans). Neun von zehn
Labels zeigen also auf nichts; dass CLAUDE.md am 2026-10-03 gemessen hat, der
Grund stehe bei allen sechzehn daneben, ist das, was sie rettet.

Ruling T8-d: **keine Aenderung am eingefrorenen 2026-10-03-Protokoll** (sein
Kopf: „absichtlich unveraendert"). Die Korrektur gehoert in die lebende Regel:
CLAUDE.md, *A ruling citation is provenance*, bekommt in der Fixwelle den
gemessenen Stand — ein Label von zehn loest in einem ausgelieferten Ledger
auf, die neun anderen nennen Entscheidungen der 1a-Ausfuehrung ohne Ledger,
fuer die der Kommentar die einzige Quelle ist — und das 1b-Protokoll sagt es
in seiner `index.md` noch einmal. Dem Betreuer vorlegen (Regeltext). Kosten,
falls falsch: zwei Absaetze.

Fuer die Rueckstandsliste der Fixwelle: (1) `ruling P-1` qualifizieren (T8-c),
(2) CLAUDE.md Ruling-Abschnitt: Namensraum je Plan + gemessener Stand (T8-c,
T8-d).

## Task 8 — Bericht

Commit `fee6d2b` (Opus), DONE_WITH_CONCERNS, vier Dateien namentlich, Tree
clean (einmal amended nach Selbstpruefung: haengendes „Er" nach dem
geloeschten Absatz). Sechs Tore gruen, 232 **gemessen**, 22 files. Grep: ein
`§` (`contract/store.py:66`, Architektur §4.4), null auf den 1b-Spec — meine
Vormessung reproduziert. Tutorial aus frischem Clone + frischem Container;
Vorhersage des Briefs hielt exakt.

**Fund, den niemand hatte:** der Block `Create the schema` zeigte **eine**
Migration und sagte „exactly one upgrade step" — falsch seit `0002` (Aufgabe
2). Der Pruefer von Aufgabe 2 sah die Seite nicht, `test_docs_typed_output`
haelt nur `N passed`. Neu getippt, zwei Schritte, Text umgeschrieben.
Abweichung 1: `alembic`, `log`, `show` ebenfalls neu getippt, weil
`chronicle`/`stats` den Zeitstempel desselben Events drucken — sonst id 1 mit
2026-10-03 oben und 2026-10-04 unten; Hash wandert mit (`recorded_at`).
**Richtig** (Ruling T8-e: ein Tutorial ist ein Lauf, nicht eine Collage).
Abweichung 2: Herkunftssatz nennt keinen Checkout-Pfad mehr; `uv sync`-Block
bleibt aus der Task-3-Sitzung, weil ein neuer Lauf `file:///tmp/...` druckt und
die Seite sagt, keine Ausgabe nenne ein Verzeichnis. Abweichung 3: Hash-Notiz
„and the timestamps"; ein `{ref}projections` unter Next steps.

Bedenken 1 → **Fixwelle:** `CLAUDE.md:72` „the three frozen records … not a
rule against writing a fourth" — der vierte existiert jetzt. Zusammen mit den
anderen CLAUDE.md-Saetzen (T8-c, T8-d) ein Commit, dem Betreuer vorlegen.
Bedenken 2: §10 nennt den Ledger-Pfad als Prosa — der Schlussschritt (T6-c)
liefert ihn; ohne ihn waere T8-a uneingeloest. Bleibt im Blick.

Review-Paket `review-af5f5de..fee6d2b.diff`; Pruefer Opus (deutscher Spec-
Kopf und §10 im Register, getippte Bloecke gegen das Roh-Transkript).

## Rueckstandsliste (Stand vor der Endpruefung, nach Aufgabe 8)

Erledigt durch A7 (`773cf4a`, `af5f5de`): `database-schema.md` sechs Tabellen
(T7-b); `tests/test_schema.py:351` Testname; README „four commands" / „no
projections"; Warnungstext (T7-a); `docs/index.md` Karte.
Erledigt durch A8 (`fee6d2b`): Tutorial-Ueberschrift und Einleitung; F11 als
Punkt 8, F9/F12 als Notizen in Spec §10 (T8-a); README vier eingefrorene
Berichte; Tutorial neu getippt (232, gemessen); dazu der ungeplante Fund
„exactly one upgrade step".

**Offen fuer die Fixwelle nach der Endpruefung** (ein Dispatch, Opus; die
Endpruefung kann Punkte dazulegen oder streichen):
1. `tests/test_cli.py:504` `ruling P-1` → Plan qualifizieren (T8-c).
2. `CLAUDE.md`, drei Stellen, **dem Betreuer vorlegen**: (a) *A ruling citation
   is provenance*: Ruling-Labels sind je Plan vergeben, ein Zitat nennt das
   Plan-Verzeichnis (T8-c); (b) ebendort der gemessene Stand: von den zehn
   Labels im Baum loest eines im 2026-10-03-Ledger auf, neun nennen
   Entscheidungen der 1a-Ausfuehrung ohne Ledger — der Kommentar ist dort die
   einzige Quelle (T8-d); (c) Z. 72 „the three frozen records … not a rule
   against writing a fourth" → vier (A8-Bedenken 1).
3. `catch_up`-Docstring (`worker.py`) nennt den `batch_size`-Riegel nicht
   (T5 minor).
4. `log --limit < 1` offen seit 1a — gleicher Riegel wie `chronicle`, als
   Zusicherung in den bestehenden `log`-Test gefaltet (T6 minor).
5. Test `set(sub.choices) == set(commands)` — ein vergessener Tabelleneintrag
   wuerde zum `KeyError`-Traceback (T6 minor). Neuer Test → Zahl 233 →
   Tutorial-Testblock **noch einmal** aus echtem Lauf (T6-f).
6. Nichts haelt die `print(..., file=sys.stderr)`-Saetze in `cli.md` gegen den
   Code (seit 1a auch `log`/`show`): `test_the_reference_quotes_what_the_code_
   actually_prints` auf stderr-Literale erweitern, oder als offenen Punkt
   begruenden (T6 minor).
7. `module-boundaries.md`: 279 Zeilen / 1a-Vergangenheit auf lebender Seite;
   `:206` Antezedens; `:256` Tempus (T1/T3 minors). `projections.md` 215
   Zeilen (T7). **Endpruefung entscheidet**, ob kuerzen oder lassen.
8. Berichtsformulierung „26 → 35 Tests in der Datei" (A6-Bericht) — nur
   Bericht, nichts im Baum; keine Aktion.

Entschieden, nicht offen: `ValueError` fuer `batch_size` (T5-f); F6 landet
durch A6; README-Zielsatz (T7-d); 1a-Spec `Status: zur Abnahme` unter
eingefrorenem Kopf bleibt (T8-b) — dem Betreuer als Beobachtung.

Danach Schlussschritt T6-c (Ledger nach `docs/superpowers/sdd/`, eigener
Commit, `index.md` mit **einem** Ruling-Zitat und dem Kollisionshinweis), dann
Arbeitsverzeichnis loeschen, dann `finishing-a-development-branch`.

## Task 8 — Pruefung (Opus): Needs fixes

Wortgetreu in `task-8-review.md`. Vier Important, alle Behauptungen, die der
Baum widerlegt; sieben Minor. Staerken: jeder getippte Block per `repr()`
zeichengleich mit dem Protokoll, Testblock 18/18 Dateizahlen gegen
`--collect-only`, Kopf per difflib eine Zeile Differenz, `uv sync`-Block
nachgemessen weiter wahr (74/71).

**I1 — der groesste Fund, und er faellt auf den Plan zurueck:**
`tests/test_cli.py:478` und `:591` zitieren `Spec §6.3`/`§6.2` **des 1b-
Specs**, markiert „(frozen design record)" — vom Plan so vorgegeben (Z. 2083,
2143), gegen Ruling T4-d; der A6-Umsetzer haengte den Marker an, damit
`test_no_bare_paragraph_references_remain` durchlaesst, als der Spec noch
nicht eingefroren war; der A6-Pruefer sah es nicht; der Brief-grep fuer A8
sah `tests/` nicht. **Das Tor kann nicht sehen, auf welchen Spec ein `§`
zeigt und ob der eingefroren ist** — fuer die Endpruefung/Fixwelle als
Luecke notiert (nicht billig schliessbar: Dokumentzugehoerigkeit eines `§`
ist nicht maschinenlesbar; ein `§` ohne Dokumentnamen koennte das Tor aber
verweigern).
Ruling T8-f: **die zwei Docstrings zitieren Seiten** (`cli-reference`,
`projections`), kein `§`; der design-records-Satz bleibt mit gemessenem
Bereich. Plan-Nachtrag (A6 Schritt 1) folgt mit meinem naechsten Commit.

I2 Abbildungstabelle ohne Architektur-§4.1/§4.4 (drei 1b-Zitate) → zwei
Zeilen. I3 „Fourteen of the 72" → 12 (zwei §12 in `test_contracts.py`
fielen mit A1); §12-Zeile sagt es. I4 Spec §10 Punkt 8 „zaehlt unter" ist die
falsche Richtung (PK → Unique-Verletzung; `merge` → Ueberzaehlung; Neubau-
Pfad → Unterzaehlung). **Ruling T8-g: der eingefrorene Spec wird in der
Fixrunde seiner eigenen Aufgabe noch korrigiert** — das Einfrieren ist die
Lieferung, und die ist nicht abgeschlossen; danach gilt der Kopf.

Minors in die Runde: „niemand starten" → „das System startet keine zwei"
(aus meinem Dispatch); zwei Komma-Spleisse Tutorial; Next-steps-Zusammen-
fassung; README-Daten fuer alle vier Zeilen (hebt meine Vorgabe „nichts
anderes" fuer drei Zellen auf); Rohprotokoll des Testlaufs nachliefern,
falls vorhanden. Nicht: Commit-Text von fee6d2b (History), `:7` vs `:31`
(vorbestehend, relativ).

Fixrunde 1 an den Umsetzer (`a36ad1da90130d9f3`, Opus), FIX_BASE `fee6d2b`,
fuenf Dateien namentlich (darunter `tests/test_cli.py`).

## Task 8 — Fixrunde 1: Bericht

Commit `51c3cfb` (Opus), fuenf Dateien namentlich, Tree clean, fee6d2b
unangetastet. I1: beide Docstrings zitieren Seiten, Labels **am Inhalt**
geprueft (`cli.md:90/:102`, `projections.md:160-174`), kein `§` mehr in
`test_cli.py`; Seitensatz nennt den Bereich, ein Folgesatz sagt, dass zwei
Zitate es bis Fixrunde 1 taten. I2: §4.1 → `projections`; §4.4 →
`projections` **und** `module-boundaries` (`store.py:66` argumentiert die
Protokolltrennung — meine Vermutung stimmte nur halb; der Umsetzer hat am
Kommentar geprueft, wie verlangt); Tabelleneinleitung „§4.1, §4.4 and §5
appear twice each". I3 gemessen: main 14, fee6d2b 17 (5 neu), nach I1 15 (3
neu) → 12 von 14; §12-Zeile sagt es. I4: alle drei Richtungen am Code
geprueft (PK + `insert_chronicle` ohne `on_conflict` → laut; `merge` → ueber;
Neubau-Pfad → unter). Fuenf Minors erledigt, Rohprotokoll nachgeliefert.

Zwei kleine Widersprueche, **beide angenommen:** (1) `design-records.md:10`
brauchte eine vierte Teilmenge, weil 12 + 2 + 56 ≠ 72 — richtig gerechnet;
(2) Vale lehnte „docstrings" ab, Satz umformuliert statt Vokabular erweitert
(`accept.txt` nicht in der Stageliste) — richtig entschieden, „docstring"
kommt ins Vokabular, wenn es gebraucht wird (Singular **und** Plural).
Sechs Schlusszeilen ungekuerzt (232, 97.32 %, 22 files). Offen bleibt
`CLAUDE.md:72` (Fixwelle, Punkt 2c).

Plan-Nachtrag T8-f (A6 Schritt 1: die zwei `§`-Docstrings kamen aus dem
Plantext, gegen T4-d; Torluecke benannt) — Commit folgt sofort, dann Re-Review.

Plan-Commit `4c52091` (T8-f-Nachtrag). Re-Review Fixrunde 1 Aufgabe 8 (Sonnet)
dispatcht: FIX_BASE `fee6d2b`, HEAD `4c52091`, Paket review-fee6d2b..4c52091.diff.

## Task 8 — Re-Review Fixrunde 1 (Sonnet): sauber

Alle neun Befunde ADDRESSED mit file:line (wortgetreu in
`task-8-re-review-1.md`). Pruefer hat die `§`-Zahlen selbst gemessen
(cdc508a 14, 4c52091 15, drei neu → 12 von 14; 12+2+2+56 = 72), die
Tabellenzuordnung an den Kommentaren geprueft (§4.4 aus `store.py:66` →
`module-boundaries`, richtig unterschieden), I4 an PK/`insert_chronicle`/
`merge`/`worker` nachgelesen, `vale` und `html -W` selbst gefahren.

Task 8: complete (commits af5f5de..4c52091, Fixrunde 1, Re-Review sauber)

**Alle acht Aufgaben abgeschlossen.** HEAD `4c52091`, Tree clean, 232 Tests,
sechs Tore gruen laut letztem Bericht.

## Endpruefung — Dispatch

Zwei Pakete bei `4c52091`: `final-review-code-cdc508a..4c52091.diff` (135 KB:
src, tests, migrations, pyproject.toml, .importlinter) und
`final-review-docs-cdc508a..4c52091.diff` (95 KB: docs ohne superpowers,
README, CLAUDE.md, .vale.ini, .vale-styles). Spec und Plan liest der Pruefer
als Dateien. Pruefer Opus (Architektur-Review, faehigstes Modell laut Skill).
Dispatch wortgetreu in `final-review-dispatch.md`: Naehte zwischen Aufgaben,
mindestens zehn Behauptungen nachgemessen, drei Zusicherungsschichten, die
Rueckstandsliste mit Verdikt je Punkt, „Declined to judge"-Liste.

## Endpruefung (Opus): With fixes

Wortgetreu in `final-review.md`. Keine Critical. Sieben Important: I-1
`source`/`external_id` unentschaerft im Tab-Strom (echte Verhaltensluecke, Spec
§6.3 faellt an der ungeprueften Stelle); I-2 „eine Transaktion = ein
Zeitpunkt" gilt unter READ COMMITTED nicht (Snapshot je Anweisung) — die
Seite begruendet falsch; I-3 Docstring „nine tests" → zwoelf; I-4/I-5 zwei
veraltete Gegenwartszahlen im datierten Messblock von `module-boundaries.md`
(40 → 48, 193 → 232); I-6 `.importlinter:30-31` (von diesem Zweig geschrieben)
zeigt mit „rulings T7-a and T8-c of stage 1a, in docs/superpowers/sdd/" auf
die **falsche** Entscheidung (T7-a dort = anderes Ruling, T8-c dort nicht
vorhanden), `.importlinter:51` traegt das 17. Zitat — meine Erhebung sah
`.importlinter` nicht; I-7 der eingefrorene Spec nennt den sdd-Pfad, den HEAD
nicht hat (→ Schlussschritt vor Merge). Zehn Minors. Sieben von acht Toren
selbst gefahren (linkcheck ausgeschlossen, laut Auftrag — der Pruefer
kritisiert diese Form zu Recht als die vom 2026-10-03). Alle 14
Abnahmebedingungen §9 am Baum belegt; drei Zusicherungsschichten einzeln
nachgemessen (Mutation `first_seen=addition.first_seen`: Worker-Datei 12
passed, Derive-Test rot — wie die Seite sagt).

Rulings zu den Befunden (Controller):
- **I-1 → Fixwelle**, `escape_field` auf jedes Feld beider Kommandos, Test in
  bestehenden Test gefaltet, Altverhalten messen.
- **I-2 → Fixwelle, wahr machen statt abschwaechen (Ruling E-1):** eine
  Storage-Methode liest `max(event.id)` und `up_to_id` in **einer** Anweisung
  (zwei Skalar-Unterabfragen); beide Kommandos nutzen sie; die Seite sagt,
  warum eine Transaktion nicht reicht. Isolationsstufe bleibt. Das
  vorbestehende `verify`-Argument (`postgres.py:203-214`) **nicht** anfassen —
  dem Betreuer als Beobachtung.
- **I-3, I-4, I-5 → Fixwelle**; der `module-boundaries`-Block bleibt datierte
  Messung, Gegenwartsaussagen raus (Empfehlung des Pruefers uebernommen).
- **I-6 → Fixwelle**, beide `.importlinter`-Stellen: Verzeichnis-Zeiger
  streichen, 1a-Ausfuehrung ohne Ledger benennen. T8-c erweitert: CLAUDE.md
  nennt das Plan-**Datum** im Zitat und bekommt die Erhebung als
  **Kommandozeile** mit `.importlinter` und `pyproject.toml` (Ruling E-2).
- **I-7 → Schlussschritt T6-c nach der Re-Review der Fixwelle, vor dem Merge**
  — nicht in der Fixwelle, weil das Protokoll die Fixwelle enthalten soll
  (Ruling E-3). Pruefer-Empfehlung „zuerst" damit nur in der Reihenfolge
  abgelehnt, nicht in der Sache.
- **T8-d geschaerft** (Ruling E-4): CLAUDE.md nennt das 1a-Hauptbuch als
  **verloren**, trennt „dieses Ledger haelt jedes Ruling seiner Ausfuehrung"
  (wahr) von „die Zitate im Baum loesen dort auf" (eins von zehn), und das
  2026-10-03-`index.md` bleibt unveraendert, obwohl seine Arbeitsanweisung
  („such dort nach Ruling T6-b") ins Leere fuehrt — der Kopf sagt
  „absichtlich unveraendert", die lebende Regel sagt den Stand.
- Minors: neun in die Fixwelle (cli.md-Reihenfolge, project-Exit-2-Text,
  „stage 1a" bei p_chronicle, Vertragsname `No vendor SDK in stage 1a` →
  Paket, `{ref}`-Pruefung auf `.importlinter`/`pyproject.toml` ausdehnen,
  `CHRONICLE.name`-Literale, `expected[0]`, How-to-Doppelung, TRUNCATE-Helper
  falls sauber); **nicht**: `--limit`-Obergrenze (Ruling E-5: Produktfrage,
  naechste Stufe).
- Rueckstandsliste wie vom Pruefer adjudiziert: 1-4 vor Merge, **5 spaeter**
  (Ruling E-6: der Retype ist der Preis; wenn I-1 gefaltet wird, aendert sich
  die Zahl nicht, und 5 allein erzwaenge ihn), 6 teils jetzt (Reihenfolge,
  Literale-Pruefung versucht), 7 und 8 gestrichen. Zwei Wortstellen in
  `module-boundaries.md` (`:206`, `:256`) bleiben in der Welle.

**Fuer die naechste Stufe** (Spec §10 ist eingefroren und traegt es nicht; ins
Hauptbuch und an den Betreuer): Subkommando-Tabellentest; `--limit`-
Obergrenze; stderr-Literale samt Reihenfolge gegen den Code halten, falls die
Fixwelle es nicht schafft; die Frage aus I-2, welche Isolationsstufe eine
Lesezusicherung braucht (auch fuer `verify`).

Fixwelle: **ein** Dispatch, Opus, frischer Agent; Dispatch wortgetreu in
`final-fix-dispatch.md`; alle sechs Tore inkl. linkcheck; zwei Commits
(Regelaenderung CLAUDE.md getrennt). BASE `4c52091`.

## Fixwelle — Bericht

Zwei Commits (Opus): `d4bcb53` rules (CLAUDE.md + `.importlinter`-Zeiger),
`ff3c261` fix (alles andere). Alle Items geschlossen, 232 unveraendert (alles
in bestehende Tests gefaltet, kein Retype), Abdeckung 97.35 %, **alle sechs
Tore inkl. linkcheck** gruen, jede neue Zusicherung rot/gruen gemessen, Tree
clean (Sonde `test_zz_measure.py` nicht im Baum — geprueft).

**Widersprueche, alle angenommen, zwei selbst nachgemessen:**
- B.2(b): **14** verschiedene Labels (case-insensitive, `.importlinter`
  dazu), nicht 10 — selbst gemessen: 22 Fundstellen, 14 Labels. Und **keines**
  loest zur Entscheidung auf, die es nennt: T5-b und T7-a finden im
  2026-10-03-Ledger eine Zeile gleichen Namens, aber eine **andere**
  Entscheidung (T5-b dort = `Vale.Terms`; `test_schema.py` zitiert es fuer
  eine Index-Naht) — selbst geprueft, Zeile 583. CLAUDE.md sagt es so: keines
  loest auf, zwei loesen falsch auf. Meine Zahl „eins von zehn" war aus einer
  case-sensitiven Erhebung ueber weniger Pfade und in der Sache zu guenstig.
- Erhebung braucht `-i` (satzinitiales „Ruling") und ein `ruling` je Label
  (kein Plural) — in CLAUDE.md als Kommandozeile samt Regel.
- B.6: die Rueckstandszeile wird aus `_lag_line` **zurueckgegeben** und ueber
  eine Variable gedruckt; die Pruefung liest deshalb auch zurueckgegebene
  Literale. Richtig.
- TRUNCATE-Helfer ist ein `str`, kein Callable: Hypothesis wertet `@given`-
  Signaturen mit `eval_str` aus, `Callable` unter `TYPE_CHECKING` gab
  `NameError` beim Sammeln. Pragmatisch richtig; Suppressions bleiben fuenf.

Offen (wie geruled): I-7 → Schlussschritt (jetzt zwei Zitate warten: Spec
§10 und `ruling P-1`-Kommentar); `--limit`-Obergrenze, Subkommando-Test →
naechste Stufe. Fuenf Stellen unter `docs/superpowers/` tragen den alten
Vertragsnamen `No vendor SDK in stage 1a` (eingefrorener Plan, vier
Berichte, 1a-Spec) — eingefrorene Aufzeichnungen, bleiben (Ruling E-7).

Re-Review (Opus — CLAUDE.md-Regelaenderung und SQL-Aenderung drin) dispatcht:
FIX_BASE `4c52091`, HEAD `ff3c261`, Paket `review-4c52091..ff3c261.diff`.

## Fixwelle — Re-Review (Opus): sauber

Wortgetreu in `final-re-review.md`. Alle Items der Abschnitte A und B
ADDRESSED, keine Abweichung vom Ruling bei I-2 (eine Anweisung, zwei
Skalar-Unterabfragen, Isolationsstufe unberuehrt). Pruefer hat die vier
billigen Tore, vale und die zwei Testdateien selbst gefahren, die B.2(b)-
Zahlen selbst gemessen (14 Labels, keines loest richtig auf, zwei falsch;
„lost" per `ls`), zwei Mutationen in einem Spiegelbaum nachgefahren, CLAUDE.md
Abschnitt fuer Abschnitt gegen die Messungen gelesen.

Drei Minor-Reste, zwei im Baum, einer nur im Bericht. **Ruling E-8: die zwei
im Baum und eine Out-of-scope-Beobachtung inline durch den Controller**, mit
den Messungen des Pruefers daneben — je ein Satz, keine Verhaltensaenderung,
der Pruefer hat die Fakten geliefert: `module-boundaries.md:193` datierte den
Dateizuwachs auf den Messtag (alle 27 Commits des Zweigs sind vom 2026-10-04);
`contract/rows.py:69-71` sagte „both numbers are 0" fuer beide Leerfaelle
(ohne Zustandszeile ist nur `up_to_id` 0 — der Lag-Test faehrt genau den
Fall); `CLAUDE.md:410` Erhebung ohne `migrations`. Commit `6e46952`,
Fable. Sechs Tore vor dem Commit gefahren: All checks passed! / 48 files /
0 errors / 4 kept / 232 passed, 97.35 % / html ok, vale 22 files, linkcheck
output.txt 0 Bytes. Berichtszahl (sechs statt sieben Stellen) nur im
Fixbericht — nichts im Baum.

Uebrige Out-of-scope-Beobachtungen → **naechste Stufe** (ins Hauptbuch, dem
Betreuer): Seiten-Reihenfolge der stderr-Hinweise haelt nichts mechanisch;
`_quoted_notices` → `IndexError` statt Assertion bei fehlendem Ankersatz;
`_message_patterns` nimmt auch `_describe`-Literale auf; `postgres.py:462`
„in those words" eine Spur zu stark (PostgreSQL sagt command/query).

**Plan vollstaendig: acht Aufgaben, Endpruefung, Fixwelle, Re-Review.**
Schlussschritt T6-c folgt: Protokoll nach `docs/superpowers/sdd/`.

## Schlussschritt T6-c — das Protokoll wird eingecheckt

Kopiert nach `docs/superpowers/sdd/2026-10-04-stufe-1b-projektionen/`: alle
`*.md` dieses Verzeichnisses, unveraendert; die `review-*.diff` und
`final-review-*.diff` nicht (aus `git diff` rekonstruierbar). `index.md` neu,
nach dem Muster vom 2026-10-03, mit dem einen Ruling-Zitat, dem
Kollisionsbefund und dem, was fehlt (Pruefberichte 1-5 nur als Befundlisten
hier). Der Commit, der das Verzeichnis anlegt, ist der naechste auf dem Zweig
nach `6e46952`; danach wird dieses Arbeitsverzeichnis unter `.superpowers/`
geloescht und `finishing-a-development-branch` uebernimmt — der Merge ist die
Entscheidung des Betreuers.
