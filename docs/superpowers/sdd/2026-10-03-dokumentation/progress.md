# SDD ledger — plan: docs/superpowers/plans/2026-10-03-dokumentation.md

Zweig: `worktree-dokumentation` (aus `main` bei c79ed63, Baum identisch).
Worktree: `/home/jensens/ws/jwk/previously/.claude/worktrees/stufe-1a-log`
(der Name stammt aus der Vorstufe; der Zweig ist umbenannt, der Worktree
gehoert der Umgebung und bleibt).

Ruling M-a: **Methode subagent-driven.** Abgewogen, nicht gewohnt. Sechs der
  acht Aufgaben haben einen knapp pruefbaren Liefergegenstand
  (Werkzeugkette, Reference gegen Code, abgetippte Sitzung, How-tos,
  Verweisumstellung mit Test, Einfrieren). Die Versuchung war, die beiden
  Explanation-Aufgaben inline zu machen, weil diese Sitzung die ganze
  Argumentation traegt. **Dagegen das Entscheidende: die Fehlerart dort ist
  unsichtbar** — eine verlorene Begruendung sieht aus wie eine knappe, und
  genau dort ist ein unabhaengiger Pruefer am meisten wert. Mein Wissen geht
  darum in die **Briefe**: je Explanation-Aufgabe eine Liste der
  Begruendungen, die ueberleben muessen, mit Zahl und Messung. Damit wird
  das Unsichtbare pruefbar und der frische Blick bleibt.
  Als Regel in die CLAUDE.md geschrieben (62045f6), auf Wunsch des
  Auftraggebers, samt der Lehre: Wissen zu haben ist kein Grund, die Arbeit
  selbst zu machen — es ist ein Grund, einen besseren Brief zu schreiben.

=====================================================================
VORAB-DURCHSICHT DES PLANS

## Paare mit gemeinsamer Datei oder Schnittstelle

| Paar | gemeinsam | erzeugt / verbraucht | Befund |
|---|---|---|---|
| T1 → T2 | `docs/reference/index.md` | T1 legt an, T2 traegt ein | sauber, Reihenfolge im Plan |
| T1 → T3 | `docs/tutorials/index.md` | dito | sauber |
| T1 → T4 | `docs/how-to/index.md` | dito | sauber |
| T1 → T5, T6 | `docs/explanation/index.md` | T1 legt an, **T5 und T6 tragen beide ein** | sauber, weil sequenziell — aber beide fassen dieselbe Datei an, also darf hier nie parallelisiert werden |
| T2 → T7 | Label `cli-reference`, `configuration-reference`, `database-schema`, `hash-format` | T2 erzeugt, T7 verweist | sauber, T7 laeuft spaeter |
| T5 → T7 | Label `hash-chain`, `hash-domain`, `tombstone-seam`, `canonicalization`, `timestamps` | T5 erzeugt, T7 verweist | sauber |
| T6 → T7 | Label `concurrency`, `conflict-classes`, `module-boundaries`, `backup-encryption` | T6 erzeugt, T7 verweist | sauber |
| T3 → T7 | `tests/` | T3 legt `test_docs_typed_output.py` an, T7 durchsucht `tests/` nach `§` | sauber, die neue Datei traegt kein `§` |
| T1 → T7 | `tests/` | verschiedene Dateien | sauber |
| **T7 ↔ T8** | **der Einfrier-Zustand** | T7 schreibt `design-records.md` und markiert Code-Verweise als „frozen design record" — **T8 friert aber erst ein** | **BEFUND P2**, siehe Ruling |
| T8 → T3, T7 | `CLAUDE.md` nennt `tests/test_docs_typed_output.py` und `tests/test_docs_references.py` | T8 verweist auf beides | sauber, T8 laeuft zuletzt |

## Jede Aufgabe gegen sich selbst

| Aufgabe | geprueft | Befund |
|---|---|---|
| T1 | Reihenfolge der Schritte: `docs/index.md` (Schritt 6) nennt die vier Quadranten, die erst Schritt 10 anlegt; erster Bau ist Schritt 11 | sauber — der Bau kommt nach dem Anlegen |
| T1 | Test (Schritt 8) soll scheitern (Schritt 9), bevor Schritt 10 ihn gruen macht | sauber, TDD-Reihenfolge stimmt |
| T2 | sagt ausdruecklich „In den Toctree eintragen und bauen" (Schritt 5) | sauber |
| **T4, T5, T6** | sagen **nicht**, dass die neuen Seiten in den Quadranten-Toctree gehoeren | **BEFUND P1**, siehe Ruling |
| T3 | abgetippte Sitzung, Test leitet Testzahl ab, Testlauf zuletzt | sauber, und die Reihenfolge ist ausdruecklich begruendet |
| T7 | Abbildung 20 Paragraphen statt 72 Entscheidungen; Test zuerst, muss scheitern | sauber |
| T8 | Einfrier-Kopf, Sprachregel als Ablauf, Doku-Regel | sauber in sich |

## Rulings aus der Durchsicht

Ruling P1: **Die Aufgaben 4, 5 und 6 bekommen je einen ausdruecklichen
  Schritt „neue Seiten in den Quadranten-Toctree eintragen".** Grund: das
  Tor faehrt `sphinx-build -W`, und eine Seite, die in keinem Toctree
  steht, erzeugt die Warnung „document isn't included in any toctree" —
  unter `-W` also einen Fehlschlag. Aufgabe 2 sagt es, 4/5/6 nicht. Das
  waere kein stiller Fehler, sondern ein lauter; er kostet aber je eine
  vermeidbare Fixrunde, und Fixrunden fuer etwas, das im Brief haette
  stehen koennen, sind mein Fehler und nicht der des Umsetzers.

Ruling P2: **Das Einfrieren wandert in Aufgabe 7, vor die
  Verweisumstellung — die Aufgabenzahl bleibt acht.**
  Der Befund: die alte Aufgabe 7 markiert Code-Verweise als „frozen design
  record" und schreibt eine Seite, die die Specs als eingefroren
  beschreibt — waehrend das Einfrieren erst in Aufgabe 8 passierte. Beides
  waere zum Zeitpunkt des Schreibens **unwahr**, und ein Verweis, der
  seinen Zielzustand falsch behauptet, ist genau der Fehler, den diese
  Umstellung beheben soll.
  **Erst erwogen, dann verworfen:** die Aufgabe in drei zu teilen und auf
  neun umzunummerieren. Dagegen sprach, dass ein 900-Zeilen-Plan mit
  Querverweisen („Test in Aufgabe 7") beim Umnummerieren genau dort bricht,
  wo man es nicht sieht — und das Umnummerieren haette keinen inhaltlichen
  Gewinn gebracht.
  **Gewaehlt:** das Einfrieren wird Schritt 1 von Aufgabe 7. Das ergibt
  einen zusammenhaengenden Liefergegenstand („die Berichte einfrieren und
  den Code auf die Doku zeigen lassen"), den ein Pruefer als Einheit
  annehmen oder ablehnen kann — was die Skill fuer eine Aufgabengrenze
  verlangt. Aufgabe 8 behaelt nur die Regeln; ihre Dateiliste sagt jetzt
  ausdruecklich, warum das Einfrieren nicht dort steht.
  Aufgabe 7 hat damit 8 Schritte, Aufgabe 8 hat 4; die Querverweise in der
  Selbstpruefung des Plans sind nachgezogen (Schritt 1 → 2, Schritt 2 → 3).
  Beim Umsetzen ist mir dabei ein Duplikat entstanden — der ausgeschnittene
  Block trug den Einfrier-Schritt schon, und ich habe ihn ein zweites Mal
  angefuegt. Gefunden, weil ich die Schrittliste nach dem Umbau
  nachgezaehlt habe statt sie zu glauben; entfernt.

Beide Befunde sind Planfehler von mir, gefunden vor dem ersten Dispatch —
  der Zweck der Durchsicht. Der Plan wird entsprechend nachgezogen, bevor
  Aufgabe 1 beauftragt wird.

=====================================================================
Task 1: DONE (commit 9f2804a, BASE 0a4b6e2). Selbst nachgemessen:
  `make -C docs html` -> „build succeeded", **Rueckgabewert 0**. Das ist
  der Beleg, nicht die Abwesenheit des Wortes „warning": mein erster
  Grep fand einen Treffer und war ein **Fehlalarm** —
  `suppress_warnings=[]` im Konfigurationsabdruck von MyST. Unter
  `-W --keep-going` bricht jede echte Warnung den Lauf ab, also beweist
  exit 0 genau das Gewuenschte. Nebenbei bestaetigt die Zeile, dass
  nichts unterdrueckt wird.
  Fuenf bestehende Tore unveraendert gruen: ruff sauber, 37 Dateien
  formatiert, pyright 0 Fehler, lint-imports 4 kept / 0 broken,
  **187 Tests** (181 + 6 aus test_docs_build.py). Baum sauber.

  **Vier der sechs Abweichungen sind Fehler in meinem Brief**, alle vom
  Umsetzer durch Laufenlassen gefunden statt durch Lesen:
  1. `linkify-it-py` fehlte. Mein `conf.py` schaltet `linkify` ein,
     markdown-it-py braucht das Gegenstueck, sonst `ModuleNotFoundError`.
     Achte Abhaengigkeit, Pflegepruefung wie bei den anderen sieben
     gemacht (2.2.0, 2026-08-29, nicht archiviert) und in
     DEPENDENCIES.md eingetragen.
  2. Der Grid-Fence in `docs/index.md` brauchte 4 statt 3 Backticks.
     Mit gleicher Anzahl baute es „erfolgreich", **aber mit drei
     `[design.grid]`-Warnungen** — unter `-W` toedlich. Mein Markdown
     war falsch.
  3. Zwei Saetze, die ich woertlich vorgegeben hatte, verstossen gegen
     Vales `Microsoft.Contractions` („cannot" -> „can't", „does not" ->
     „doesn't"). Der Stil stand in meinen eigenen Global Constraints.
  4. Der Importblock meines Testdateitexts entsprach nicht der
     isort-Konfiguration dieses Projekts (I001).
  Dazu zwei richtige Eigeninitiativen: die veralteten Zahlen in
  `gates.yml` („five gates" -> „six") nachgezogen, und die
  `vale sync`-Luecke geloest, auf die ich im Dispatch hingewiesen hatte
  (`test -d .vale-styles || vale sync`, einmalig lokal, je Lauf in der CI
  — die frisch auscheckt).

Ruling T1-a: **Die `.gitignore`-Abweichung ist kein Befund.** Der
  Umsetzer hat die Regel korrekt gelesen: die englisch gebundene Liste in
  `CLAUDE.md` nennt `pyproject.toml`, `.importlinter`, `alembic.ini`,
  `.pre-commit-config.yaml` — `.gitignore` fehlt dort. Das war aber eine
  **Auslassung von mir, keine Entscheidung**: die
  „Programmausgabe"-Haelfte der Begruendung trifft auf `.gitignore` nicht
  zu (es wird nirgends gedruckt), die andere Haelfte schon (wer
  `pyproject.toml` liest, liest auch `.gitignore`).
  Nicht an Aufgabe 1 angehaengt, sondern als **Schritt 3 in Aufgabe 8**
  nachgetragen, wo die Regeln ohnehin geschrieben werden. Dem Pruefer
  ausdruecklich gesagt, dass er es nicht melden soll.

Task 1: Pruefung beauftragt (Modell sonnet, Paket
  review-0a4b6e2..9f2804a.diff). Hauptfrage: **das Tor zum Scheitern
  bringen** — drei Experimente in einer Arbeitskopie ausserhalb des
  Checkouts (Seite ohne Toctree, kaputter Querverweis, Stilverstoss).
  Ein Tor, das nicht greift, ist schlimmer als keines, und bei einem
  frischen Sphinx-Baum ist genau das die Frage.

Task 1: Pruefung angenommen, beide Urteile, **ein Befund mittlerer
  Schwere**. Der Pruefer hat die drei verlangten Scheitern-Experimente
  gemacht und ein **viertes selbst ergaenzt** — und genau das brachte den
  Befund. Ergebnisse:
    Seite ohne Toctree      -> exit 2, `toc.not_included`   Tor haelt
    kaputter {doc}-Verweis  -> exit 2, `ref.doc`            Tor haelt
    Stilverstoss (Prosa)    -> exit 2, Microsoft.Contractions, und das
                               aus frischem Zustand ohne .vale-styles/
                               (vale sync greift, zweiter Lauf nicht)
    Stilverstoss in {note}  -> **exit 0, unentdeckt**
  Dazu linkcheck gezielt geprueft: echte tote Domain als `broken`
  gemeldet, erfundene GitHub-Issue-URL korrekt `-ignored-`, eine andere
  erfundene GitHub-URL ausserhalb des Musters weiter als 404. Der
  `linkcheck_ignore`-Regex nimmt nur aus, was er soll.

BEFUND: **Vale prueft keinen Text innerhalb einer Backtick-Fence.** Selbst
  nachgemessen, drei Stellen in einer Datei:
    Zeile  3  reine Prosa        -> beanstandet
    Zeile  6  in ```{note} …     -> NICHT beanstandet
    Zeile 10  in :::{note} …     -> beanstandet
  Vale haelt eine Backtick-Fence fuer einen Codeblock und ueberspringt
  sie, auch wenn eine MyST-Direktive darin steht und der Inhalt Prosa ist.
  Belegt am echten Fall: `docs/index.md:42` traegt „does not cover" in
  einer `{grid-item-card}`-Fence und blieb unbeanstandet, waehrend
  derselbe Ausdruck ausserhalb einer Fence in derselben Aufgabe korrigiert
  wurde.

Ruling T1-b: **Doppelpunkt-Fences fuer Direktiven mit Prosa.** Die Loesung
  kostet nichts, weil `colon_fence` in `conf.py` schon eingeschaltet ist —
  `:::{note}` statt ```{note}`, beim Verschachteln zaehlen die
  Doppelpunkte wie die Backticks. Codebloecke bleiben bei Backticks; dort
  ist das Ueberspringen richtig.
  In die **Global Constraints des Plans** geschrieben, nicht nur in die
  Fixrunde: Admonitions, Karten und Tabs sind genau die Stellen, an denen
  in einer Dokumentation wichtige Saetze stehen, und alle sieben
  folgenden Aufgaben schreiben solche. Ein Tor mit einem blinden Fleck an
  der interessantesten Stelle ist schlechter als eines, dessen Grenzen
  man kennt.
  Damit hat dieser Befund nicht eine Seite verbessert, sondern das Tor.

Task 1: fix round 1/5 beauftragt (derselbe Umsetzer fortgesetzt): Fences
  umstellen, die dadurch sichtbar werdenden Stellen beheben, und am HTML
  nachpruefen, dass die vier Karten weiter rendern — an der Stille haette
  er es nicht gemerkt.

Task 1: fix round 1/5 (1 behoben, 0 offen; commit fefe40c).
  Der Umsetzer hat die **richtige Messreihenfolge** gewaehlt, und das ist
  der Teil, der den Fix belegt: erst Vale auf dem Backtick-Zustand (0
  Fehler — der blinde Fleck bestaetigt), dann **nur die Fences**
  umgestellt und die Formulierung stehen gelassen, dann Vale erneut
  (`42:88 Use 'doesn't' instead of 'does not'` — der Fang belegt), dann
  die Formulierung behoben, dann wieder gruen. Haette er beides in einem
  Schritt gemacht, waere unbelegt geblieben, ob die Fence-Umstellung oder
  die Wortaenderung gewirkt hat.
  Fences korrekt verschachtelt: aussen `::::{grid}`, innen
  `:::{grid-item-card}`. Die vier Quadranten-Indexseiten brauchten nichts
  — sie tragen nur einen leeren `{toctree}` ohne Prosa.

  **Eigene Fehlmessung, festgehalten:** ich habe die Karten mit
  `grep -o sd-card | wc -l` gezaehlt und 24 bekommen, dazu 6 `sd-row` —
  und damit der Angabe „4 Karten in 1 Reihe" scheinbar widersprochen.
  Falsch war meine Messung: `sd-card` steckt in mehreren Klassennamen je
  Karte (`sd-card`, `sd-card-body`, `sd-card-header`, `sd-card-text`).
  Genau gezaehlt ueber das Klassenattribut:
    4 x class="sd-card sd-sphinx-override …"
    1 x class="sd-row sd-row-cols-1 …"
  Also 4 Karten in 1 Reihe, wie berichtet. Lehre, schon mehrfach in dieser
  Sitzung: ein Teilstring ist keine Einheit.

Task 1: complete (commits 9f2804a..fefe40c, Pruefung und Fixrunde sauber).
  Stand: 187 Tests, Abdeckung 99,80 %, sechs Tore gruen, Doku baut
  warnungsfrei, Vale und linkcheck sauber, Baum sauber.

Task 2: DONE (commit 8abda3b). Vier Reference-Seiten, vier Label
  (`cli-reference`, `configuration-reference`, `database-schema`,
  `hash-format`), alle vier im gebauten HTML mit genau diesen ids
  bestaetigt. Tore gruen: html ohne Warnung, vale 0 Fehler in 9 Dateien,
  linkcheck sauber, 187 Tests unberuehrt.

  **Vier der sechs Abweichungen sind Fehler in meinem Brief**, und die Art
  des Findens ist der Grund, warum ich alle vier uebernehme:
  1. Mein Beispiel in `configuration.md` verwies auf `{ref}`concurrency``
     — ein **Vorwaertsverweis** auf ein Label, das erst Aufgabe 5 anlegt.
     Gemessen: `WARNING: undefined label: 'concurrency' [ref.ref]`, unter
     `-W` ein Fehlschlag. Zu Recht weggelassen.
  2. Mein Brief liess `append` „denselben (source, external_id) zweimal im
     selben Aufruf" abweisen. **Auf diese CLI trifft das nicht zu**:
     `_cmd_append` baut immer genau ein `RawEvent`, der Stapelpfad ist von
     der Kommandozeile aus unerreichbar. Die Abweisung existiert, aber in
     `core.append._prepare()`. Er hat das tatsaechliche Verhalten
     dokumentiert (idempotent ueber wiederholte Aufrufe).
  3. Meine Rueckgabewert-Regel („1 nur wenn verify einen Befund meldet")
     **zaehlt zu wenig**: `show` gibt auch 1 zurueck, wenn es kein Event
     mit der id gibt. Als 4x3-Tabelle je Befehl dokumentiert statt als
     eine globale Regel.
  4. Meine Liste der acht Beschraenkungen und Indexe **vergass
     `unit_pkey`** — nach meinem eigenen Kriterium („Namen, die in
     Fehlermeldungen auftauchen") gehoert es genauso dazu wie `event_pkey`.
     Gefunden, weil er die Namen **gegen eine echte PostgreSQL-17-Instanz
     geprueft** hat (Migration im Testcontainer, `pg_constraint` und
     `pg_indexes` abgefragt) statt Postgres' Namenskonvention zu
     unterstellen. Dabei kamen vier weitere Namen dazu.

Ruling T2-a: **Das Vale-Vokabular war durch Aufgabe 1 verbaut, und das ist
  mein Fehler.** Vale legt sein Projektvokabular unter
  `StylesPath/config/vocabularies/` ab — und Aufgabe 1 hat `.vale-styles/`
  **als Ganzes** auf die `.gitignore` gesetzt, womit kein committetes
  Vokabular moeglich ist. Folge: `Vale.Spelling` beanstandet gewoehnliche
  Fachwoerter (`SQLAlchemy`, `canonicalized`, `subcommand`, `nullable`),
  und der Umsetzer musste herumformulieren. „Nullable" in einer
  Schema-Reference weglassen kostet Genauigkeit.
  Nachgesehen: `vale sync` legt **nur** `.vale-styles/Microsoft/` an. Der
  Ausschluss ist also zu breit. Vierteiliger Fix beauftragt:
  `.gitignore` auf `.vale-styles/Microsoft/` verengen, Vokabular anlegen
  und committen, `Vocab = Previously` in `.vale.ini`, und den
  Makefile-Waechter auf `test -d .vale-styles/Microsoft` aendern — er
  greift sonst nie mehr, weil das Verzeichnis dann committet ist.
  Dazu: die ausgewichenen Formulierungen zurueckdrehen.

Ruling T2-b: **`:alt:` wird entfernt, nicht stehen gelassen.** Der Befund
  stimmt und ich habe ihn nachgemessen: mit
  `mermaid_output_format = "raw"` traegt das Diagramm **kein** `alt` und
  kein `aria-label`; die 17 Treffer im HTML sind alle Theme-Zubehoer
  (Suche, Navigation, Farbmodus, Vollbild). Die `:caption:` **rendert**
  dagegen („event, unit, and source_key, with their foreign keys.").
  Die naheliegende Loesung — `svg`-Ausgabe per `mmdc` — **abgelehnt**: eine
  Node.js-Werkzeugkette in einem Python-Projekt, fuer vier Diagramme,
  gegen die Regel „`uv.lock` ist der einzige Ort fuer Werkzeugfassungen".
  Stattdessen: kein `:alt:`, dafuer `:caption:` **und ein Satz Prosa
  davor**, der sagt, was das Diagramm zeigt. Begruendung, die in den Plan
  gewandert ist: eine Option, die aussieht, als erledigte sie
  Barrierefreiheit, aber nichts tut, ist **schlimmer** als keine — und bei
  einem Diagramm ist ein beschreibender Satz im Fliesstext ohnehin mehr
  wert als ein Attribut.

Plan nachgezogen: die Diagramm-Regel im Abschnitt „Diagramme" (gilt fuer
  die drei Diagramme der Aufgaben 5 und 6), und ein neuer Schritt 3 in
  Aufgabe 5, der den Querverweis `{ref}`concurrency`` nachruestet, den
  Aufgabe 2 zu Recht weglassen musste.

Task 2: fix round 1/5 beauftragt (derselbe Umsetzer).

Task 2: fix round 1/5 (2 behoben, 0 offen; commit 73bcb5e).
  Selbst am entscheidenden Punkt geprueft — ob der Fix echt oder
  kosmetisch ist:
    `git ls-files .vale-styles/` -> accept.txt **versioniert**
    `git check-ignore .vale-styles/Microsoft/` -> ausgeschlossen
    `git check-ignore …/accept.txt` -> **nicht** ausgeschlossen
  Waere das Vokabular weiter von der .gitignore verschluckt worden, haette
  der ganze Umbau nichts gebracht. Dazu: kein `alt=` mehr im Schema-HTML
  (0 Treffer), vale 0 Fehler in 9 Dateien, 187 Tests, Baum sauber.

  Drei Dinge hat der Umsetzer besser gemacht als verlangt:
  1. Den Vokabularpfad **empirisch** festgenagelt statt meiner Angabe zu
     glauben — ein leeres Vokabularverzeichnis provozierte Vales eigene
     Meldung „vocabulary not found; searched: …", und die nannte den Pfad.
  2. Jedes Wort **einzeln** geprueft, bevor er es eintrug. `PostgreSQL`
     geht schon durch und steht darum **nicht** in der Datei — „ein Wort
     eintragen, das schon durchgeht, waere Rauschen".
  3. `psycopg`, `testcontainers`, `idempotency` scheitern zwar in
     Isolation, werden aber auf keiner der vier Seiten ausserhalb einer
     Code-Spanne benutzt — **weggelassen statt auf Vorrat eingetragen**.
     Richtig: ein Vokabular auf Vorrat ist eine Behauptung ueber kuenftige
     Seiten. Der Preis ist, dass spaetere Aufgaben die Datei ergaenzen
     muessen; das ist sichtbar und darum in Ordnung.
  Und er hat „connection string" **nicht** zurueckgedreht: das loeste eine
  separate `Microsoft.GeneralURL`-Warnung, nicht eine Vokabularluecke, und
  deckt sich mit der Wortwahl in `storage/postgres.py`. Richtig
  unterschieden.

Task 2: complete (commits 8abda3b..73bcb5e, eine Fixrunde). Stand: vier
  Reference-Seiten, vier Label im HTML bestaetigt, ein ER-Diagramm mit
  Bildunterschrift und beschreibendem Satz statt eines unwirksamen
  `:alt:`, committetes Vale-Vokabular, alle Tore gruen.

Task 3: DONE (commit 3eb41ec). 188 Tests (187 + 1 Tor-Test), alle Tore
  gruen. Die Sitzung wurde wirklich abgetippt: frischer Checkout unter
  /tmp, eigener PostgreSQL-17-Container, ein zusammenhaengender Lauf, die
  Testzahl **zuletzt** — danach Container und Checkout entfernt.

  **Ein neuer Fund, und er trifft meinen Brief:** mein Code fuer
  `tests/test_docs_typed_output.py` trug ein `# noqa: S603`, das ruff als
  **unbenutzt** meldet (`RUF100`). Begruendung des Umsetzers, praezise und
  nachvollziehbar: S603 greift nur, wenn ruff nicht beweisen kann, dass
  alle Argumente Literale sind — bei meinem Aufruf sind sie es alle,
  anders als beim Vorbild `test_contracts.py:206`, wo eine Variable drin
  steckt. Entfernt, und damit war die Unterdrueckungsliste in der
  CLAUDE.md **nicht** zu ergaenzen. Richtige Folgerung.

  Zur Bemerkung, dass keiner der drei historischen Fehler wieder auftrat
  (fehlende DSN, fehlende Extras, veraltete Zahl): seine Erklaerung ist
  richtig und uebernommen. Ein Tutorial gibt **einen** garantierten Weg,
  nicht einen vorgefuehrten Fehler; mein Brief hat den korrigierten Pfad
  vorgegeben, also war nichts zu finden. Kein Mangel der Uebung, sondern
  ihr Zweck.

Ruling T3-a: **Die ungefragte README-Umstrukturierung angenommen.** Er hat
  „The basic idea" und „What it is not" als Abschnitte entfernt und als
  Ermessensentscheidung gekennzeichnet. Ich habe die **Datei gelesen**
  statt seiner Beschreibung zu folgen — und der Inhalt ist da: „What it
  does not do" samt Liste, und der Absatz ueber den fehlenden aeusseren
  Anker, der die charakteristische Ehrlichkeit dieses Projekts traegt. Er
  hat Ueberschriften zusammengefuehrt, nicht Inhalt entfernt; besser
  gegliedert als vorher. Haette ich nach der Selbstbeschreibung
  entschieden, haette ich eine Verbesserung zurueckgewiesen.

Ruling T3-b: **Die Port-Sorge ist keine.** Er hat offengelegt, dass sein
  Lauf auf Port 5544 lief, weil 5432 im Sandkasten belegt war, das
  Tutorial aber 5432 zeigt. Nachgemessen: `5432` steht **nur** in
  Befehlen, die der Leser tippt (`docker run -p 5432:5432`, das
  `export`), in **keiner** abgetippten Ausgabe. Es ist also nichts
  substituiert — die Befehle sind fuer einen Leser mit freiem 5432
  richtig, die Ausgaben echt und portfrei. Richtig, es zu melden.

Ruling T3-c: **Die zwei `Microsoft.We`-Warnungen werden abgeschaltet, nicht
  umgeschrieben.** Der Skill **verlangt** fuer Tutorials die erste Person
  Plural (Abschnitt 2a), der Microsoft-Stil verbietet „we" — ein echter
  Widerspruch, und fuer dieses Projekt gilt der Skill. Umschreiben waere
  also falsch.
  Stehenlassen aber auch: eine Meldung, die dauerhaft erscheint und die
  man ignorieren soll, trainiert den Leser darauf, die Ausgabe zu
  ueberfliegen — dieselbe Begruendung, die der Skill fuer den sparsamen
  Gebrauch von Admonitions gibt. Dann uebersieht er irgendwann eine echte.
  Beauftragt: pfadbezogene Ausnahme fuer `docs/tutorials/` **allein**, mit
  Kommentar, der den Konflikt benennt — und ausdruecklich die Messung, dass
  die Regel **ausserhalb** weiter greift. Eine Ausnahme, die zu weit
  greift, ist schlimmer als die Warnung.

Ein veralteter Zahlwert selbst gefunden: `README.md:58` sagt „the five
  gates", es sind **sechs** (nachgezaehlt: 6 x `- name: Gate` in
  gates.yml). Die uebrigen Zahlen der README gleich mitgeprueft, damit er
  nicht suchen muss: „four commands" stimmt (4 x `add_parser`), „256" und
  „six mailboxes" sind in Ordnung. Nur diese eine.

Plan nachgezogen: Aufgabe 7 bekommt einen Schritt fuer die **README-
  Verweise**. Nicht nur der Code zeigt auf die Specs — die README sagt
  „§11 of the stage 1a specification states which forgeries are covered",
  und das beantwortet eine **heutige** Frage, gehoert also auf die
  Explanation-Seite. Die Dokumententabelle darf dagegen auf die
  eingefrorenen Berichte zeigen; sie beschreibt Provenienz.

  **Eigener Fehler beim Nachziehen, zum zweiten Mal in dieser Sitzung:**
  mein Umnummerierungsskript hat die „3" nicht mit hochgezaehlt, also gab
  es zwei „Schritt 3" und kein „Schritt 4". Gefunden durch Nachzaehlen
  danach — und zwar maschinell: die Schrittfolge von Task 7 gegen
  `range(1, n+1)` geprueft, Ergebnis jetzt `[1..9] lueckenlos: True`.
  Lehre: beim Umnummerieren per Skript ist die Pruefung nicht optional,
  und sie gehoert maschinell gemacht, nicht mit dem Auge.

Task 3: fix round 1/5 beauftragt (derselbe Umsetzer): veraltete Zahl,
  pfadbezogene Vale-Ausnahme.

Task 3: fix round 1/5 (2 behoben, 0 offen; commit 7a35ba6).
  Beide Richtungen gemessen, wie verlangt: `make -C docs vale` meldet jetzt
  0 Fehler und 0 Warnungen in 10 Dateien, **und** eine Wegwerfseite in
  `docs/how-to/` mit denselben Woertern bekommt die drei
  `Microsoft.We`-Warnungen weiter. Die Ausnahme greift also nicht zu weit
  — das war die eigentliche Frage, nicht ob die Warnungen verschwinden.
  Die Zahl hat er unabhaengig nachgezaehlt statt meine Angabe zu
  uebernehmen (`grep -c '^      - name: Gate'` -> 6).

Ruling T3-d: **Die CLAUDE.md-Stelle wird jetzt behoben, nicht in Aufgabe 8.**
  Der Umsetzer hat gefunden, dass `CLAUDE.md`s `## Gates` weiter „All five
  pass" sagt und nur fuenf Befehle auflistet — dieselbe Veraltung eine
  Ebene hoeher —, und hat sie korrekt aus seiner Runde herausgehalten und
  Aufgabe 8 zugeschrieben. Fuer **seine** Runde war das richtig; als
  Auftraggeber entscheide ich anders.
  Grund: das ist das Dokument, das das Projekt regiert, und **vier weitere
  Aufgaben lesen es, bevor Aufgabe 8 laeuft**. Wer von der CLAUDE.md
  allein arbeitet, faehrt fuenf Befehle und fasst das Doku-Tor nie an —
  genau der Fehlschlag, den das Tor verhindern soll. Dass es bisher nicht
  gebissen hat, liegt daran, dass ich den sechsten Befehl in jeden
  Dispatch geschrieben habe; das ist Glueck, nicht Entwurf.
  Selbst behoben (06dd2f5), und die Regel „Doku folgt dem Code im selben
  Change" gleich mit hineingeschrieben — sie stand bisher nur im Plan, und
  der Plan endet, diese Datei nicht.

Task 3: complete (commits 3eb41ec..7a35ba6, eine Fixrunde). Stand: 188
  Tests, Tutorial mit abgetippter Sitzung, README auf einen Zeiger
  geschrumpft, Doku-Tor in der CLAUDE.md verankert.

Task 4: DONE (commit 738dfec), Pruefung angenommen (beide Urteile), zwei
  Befunde — einer davon **mein** Fehler.

  Zwei Dinge hat der Umsetzer richtig gemacht, die ich hervorheben will:
  1. **Nicht fehlverlinkt.** Mein Brief liess die Passphrase in
     `restore-from-a-backup.md` auf „die Reference fuer die Konfiguration"
     zeigen. Dort gibt es keinen solchen Inhalt — `configuration-reference`
     dokumentiert nur `PREVIOUSLY_DSN`, die Passphrase liegt in einem
     Kubernetes-Secret, ausserhalb der Konfigurationsflaeche. Er hat den
     Verweis nur dort gesetzt, wo er wahr ist. Mein Brief war falsch.
  2. **Keine Befehle erfunden.** Per grep festgestellt, dass es im
     Repository keinen Restore-Weg gibt, und die Seite auf das verengt, was
     existiert. Der Pruefer hat gegengeprueft: null Treffer fuer
     `backup|restore|passphrase` in src/, tests/, migrations/ — und haelt
     die Verengung fuer richtig.

BEFUND, und er trifft mich: `add-a-migration.md:20` sagt „nothing here
  catches the mismatch". Das war beim Schreiben wahr. Dann habe **ich** in
  c3d67e8 den Schema-Test hinzugefuegt und damit eine
  Dokumentationsaussage ungueltig gemacht, die eine Stunde alt war — ohne
  zu pruefen, ob die Doku etwas Gegenteiliges behauptet.
  **Das verstoesst gegen die Regel, die ich kurz davor selbst in die
  CLAUDE.md geschrieben habe** („aendert sich Code, wird geprueft, ob die
  Doku nachzuziehen ist, und sie kommt im selben Change mit"). Gebrochen
  von mir, in derselben Sitzung, im Dokumentationsprojekt. Der Pruefer
  nennt es ausdruecklich „kein Versaeumnis des Umsetzers".
  Lehre, die mehr wert ist als der Fix: die Regel gilt auch fuer den
  Auftraggeber, und sie gilt besonders fuer kleine Commits „nebenbei".
  Ein Test, der eine Zusicherung staerkt, aendert damit die Aussage jeder
  Seite, die ueber diese Zusicherung spricht.

Ruling T4-a: Beim Nachziehen soll die Seite **genauer** werden als „es gibt
  jetzt einen Test", denn die Lage ist dreiteilig und das ist die
  eigentliche Information fuer einen Leser:
    - der **Namenstest** faengt die Abweichung weiter **nicht** (Namen
      tragen kein Flag)
    - `test_only_one_genesis_is_permitted` faengt sie **schon immer**,
      verhaltensseitig — das hatten der Umsetzer und ich uebersehen, und
      ich habe es erst gemerkt, als mein neuer Test absichtlich rot
      gemacht **zwei** rote Tests ergab
    - mein neuer Test faengt den **Abgleich** zwischen `metadata` und
      Datenbank, fuer jeden erklaerten Index, und auch die Gegenrichtung,
      die kein Verhaltenstest sehen kann
  Die Gefahr bleibt real (ein `--autogenerate` kann das Flag weiter fallen
  lassen), sie faellt nur jetzt auf. Angewiesen, die Testnamen am Code
  nachzusehen statt sie aus meiner Nachricht zu zitieren.

Ruling T4-b: Titel/Inhalt von `restore-from-a-backup.md` — **Dateiname
  bleibt, H1 wird genau.** Der Befund (gering) ist richtig: die Seite
  verspricht eine Restore-Anleitung und liefert den Verify-danach-Teil.
  Umbenennen waere aber Laerm: `restore-from-a-backup.md` ist der richtige
  langfristige Ort, die Seite waechst, sobald es ein Deployment mit echtem
  Restore gibt, und dann muesste man zurueckbenennen. Die H1 sagt
  stattdessen, was die Seite **heute** tut. In einem Projekt, dessen
  schwerster Befund eine Zusage war, die mehr versprach als sie hielt
  („Kettenintegritaet: vollstaendig"), ist das die passende Loesung.

Task 4: fix round 1/5 beauftragt (derselbe Umsetzer).

Task 4: fix round 1/5 (2 behoben, 0 offen; commit f3e010f). Der Umsetzer hat
  `c3d67e8` und den neuen Test **selbst gelesen** statt meiner Beschreibung
  zu glauben, und beides bestaetigt. Die Seite nennt jetzt beide Tests und
  sagt, welcher was faengt. H1 von `restore-from-a-backup.md` praezisiert,
  Dateiname behalten; er hat „chain" statt „log" gewaehlt, weil
  `cli-reference` und der Rest der Seite diesen Begriff fuer das benutzen,
  was `verify` prueft — richtig abgeglichen statt uebersetzt.

ZWEITER FEHLER IN MEINEM NEBENCOMMIT, von ihm beim Lesen gefunden und
  korrekt **nicht** angefasst (Doku-Aufgabe): dem neuen Schema-Test fehlte
  `@pytest.mark.db`, den jeder Nachbartest in der Datei traegt.
  Nicht folgenlos, nur **latent** — nachgemessen:
    vorher  `-m "not db"`  ->  97 passed in 7.59s   (mein Test lief mit)
    nachher `-m "not db"`  ->  96 passed in 1.52s   (kein Container)
            `-m db`        ->  93 passed
  Die Laufzeit ist der klarste Beleg: die Auswahl „braucht keine
  Datenbank" startet jetzt gar keinen Container mehr. Hier bestand der
  Test nur, weil Docker zufaellig vorhanden ist; auf einer Maschine ohne
  Docker waere genau diese Auswahl an meinem Test gescheitert.
  Behoben (5e2eced).

  **Zwei Defekte in einem kleinen Nebencommit**, beide von anderen beim
  Lesen gefunden: die veraltete Doku-Aussage und der fehlende Marker. Die
  Lehre, die ich mitnehme: ein Commit, der „nebenbei" entsteht, bekommt
  dieselbe Lesung wie einer, der absichtlich entsteht — und bekommt sie
  besser vorher. Ich haette nach dem Hinzufuegen des Tests `grep` auf die
  Doku und einen Blick auf die Nachbartests machen muessen; beides haette
  eine Minute gekostet.

Task 4: complete (commits 738dfec..f3e010f plus meine c3d67e8, 9dbcf42,
  5e2eced). Stand: 189 Tests, drei How-tos, Doku-Tor gruen.

Task 5: complete (commits 8d0f42b..a816d4f, eine Fixrunde). Pruefung:
  **15/15 Punkte der Ueberlebensliste bestaetigt**, jede Zahl vom Pruefer
  am **Code** nachgeprueft statt am Bericht. Acht Befunde, keiner
  blockierend. Tore gruen, 189 Tests, alle fuenf Label buchstabengleich
  **und** als `std:label` in `objects.inv` — Aufgabe 7 kann darauf
  verweisen.

  **Die Ueberlebensliste hat funktioniert — und zwar in beide
  Richtungen.** Sie hat nicht nur die Seiten pruefbar gemacht; der
  Umsetzer hat **drei Fehler in ihr** gefunden (Punkt 11 zaehlte zweimal
  statt dreimal, Punkt 12 gab zwei Einschraenkungen einen gemeinsamen
  falschen Grund, Punkt 3 war zu schwach), und der Pruefer hat danach
  keinen weiteren gefunden. Das ist der Beleg, dass das Verfahren traegt:
  ein Maszstab, den zwei unabhaengige Leser gegen den Code halten, wird
  dabei selbst geprueft.

Lehre aus der Fixrunde, die mir am meisten wert ist: **der Umsetzer hat
  sich geweigert, die Zahl einzutragen, um die ich gebeten hatte.** Ich
  wollte „vier von elf" vor einen Satz setzen, der von Feldern sprach, die
  „never reach that output". Nachgemessen trifft das auf **sechs** zu
  (`v` und `domain` werden auch nicht gedruckt). Nicht
  **wiedergewinnbar** sind genau vier, weil `v`/`domain` Konstanten sind
  und die Digest-Felder aus der gedruckten Nutzlast und den gedruckten
  Einheiten nachzurechnen sind. Er hat also nicht die Zahl geaendert,
  sondern das **Verb** — „can't be recovered from that output at all".
  Selbst nachgemessen und bestaetigt: elf gehashte Felder, `show` druckt
  id, kind, occurred_at, payload, units, evidence und den hash; nicht
  gedruckt sind sechs, nicht wiedergewinnbar vier.
  Haette er meine Bitte befolgt, stuende jetzt eine falsche Zahl da — und
  zwar eine, die ich selbst verlangt hatte.

Zweite Lehre, vom Umsetzer selbst benannt: **die „elf H2-Abschnitte" waren
  seine Zahl**, standen in seinem Bericht an mich, wanderten von dort in
  meinen Brief und von dort in meine Zusammenfassung. Nachgezaehlt:
  `grep -c '^## '` gibt **10** fuer hash-chain.md und 5 fuer
  canonicalization.md. Seine Einordnung ist die richtige: „genau der
  Fehlertyp, gegen den die Ueberlebensliste gebaut ist, nur eine Ebene
  hoeher." Die Liste sichert Tatsachen **in den Seiten**, nicht Tatsachen
  **in den Berichten ueber die Seiten** — und Berichte sind genau der Weg,
  auf dem eine Zahl in einen Brief gelangt.

Dritte Lehre: er hat eine eigene Beinahe-Falle selbst eingefangen — „the
  four values" fuer die Bereichskennungen, waehrend `hash-format` vier
  Zellen mit nur **drei verschiedenen** Werten listet. „Eine Zahl, die
  sich zweimal zaehlen laesst, ist genau der Fehler, den Punkt 1 dieser
  Runde abstellt."

Ruling T5-a: Zwei Befunde des Pruefers sind **Planluecken, nicht Fehler
  der Aufgabe**, und beide muessen vor dem Einfrieren schliessen. Als
  Schritte in Aufgabe 6 eingetragen:
  - Der **Nutzlastbereich** (`^[a-z][a-z0-9_]*$`, `±(2**53−1)`) hat keine
    Reference-Heimat; er steht allein in der Explanation. Falsche Stelle:
    wer einen Konnektor schreibt, schlaegt die Pflichtmenge in der
    Reference nach, nicht in einem Aufsatz.
  - „the five silent losses of data" ist aus `docs/` **nicht
    aufloesbar** — nirgends steht eine Liste der fuenf, der einzige Anker
    ist die Spec („der fuenfte dieser Sitzung"), und die friert ein. Der
    CRLF-Fund ist ueberhaupt nirgends als einer der fuenf verzeichnet.
    Daraus wird eine eigene Seite mit Label `(silent-losses)=`, samt dem
    Verbindenden: keiner war ein Programmierfehler, jeder war eine Luecke
    zwischen Zusage und Wirklichkeit, jeder wurde durch Messen gefunden.

Ruling T5-b: `Vale.Terms` nagelt **jeden** Vokabulareintrag fest, nicht nur
  Paare — meine frühere Diagnose war zu eng. Gemessen: zehn Fehler bei
  einer Form je Eintrag; neun der elf Eintraege sind klein, diese neun
  Woerter koennen also keinen Satz und keine Ueberschrift beginnen. Beisst
  heute nichts, weil die Seite „About canonicalization" heisst. In die
  `.vale.ini` geschrieben, samt dem Rat, **nicht** die Grossform
  nachzutragen (das dreht den Zwang nur um).

Ruling T5-c: **Mermaid bleibt bei Backticks.** Gemessen vom Pruefer: eine
  `:::{mermaid}`-Fence rendert ein **byteidentisches** `<figure>`, zieht
  aber den Diagrammtext in Vales Geltungsbereich, das dann ueber
  `payload_hash`/`units_hash`/`event_hash` stolpert. Diagrammtext ist
  Code; das Ueberspringen ist dort richtig. Die Doppelpunkt-Regel gilt fuer
  Direktiven mit **Prosa**.

Ruling T5-d: `hash-chain.md` bleibt **ungeteilt**, jetzt aus gemessenem
  Grund. Der Pruefer wuerde einer Teilung widersprechen: fuenf Rueckgriffe
  ueber Abschnittsgrenzen, und Teilen machte daraus Seitenuebergaenge —
  „No scattering", woertlich aus dem Quadranten. Billigste Naht, falls
  doch: die zwei Datenmodell-Abschnitte.

---

## Aufgabe 6 — Bericht erhalten, Tore selbst nachgefahren

Commit `ed84bf5`, BASE `a816d4f`, ein Commit (nicht drei: `concurrency.md`
verweist auf `{ref}`silent-losses``, `canonicalization.md` auf
`{ref}`payload-range``; eine Aufteilung haette Zwischenzustaende erzeugt, in
denen `sphinx-build -W` scheitert). Trailer `Assisted-By:`, kein
`Co-Authored-By`. 11 Dateien, 603 Einfuegungen.

**Selbst nachgemessen, nicht aus dem Bericht uebernommen:**

| Tor / Zahl | gemessen | Quelle |
|---|---|---|
| `pytest -q` | 189 passed in 16.62s | selbst gefahren |
| `lint-imports` | 4 kept, 0 broken | selbst gefahren |
| `make -C docs html` | build succeeded | selbst gefahren |
| `make -C docs vale` | 0/0/0 in 19 Dateien | selbst gefahren |
| `make -C docs linkcheck` | output.txt 0 Bytes | selbst gefahren |
| Label, sechs | alle an den genannten Zeilen | `grep -rn '^([a-z-]*)='` |
| `BACKOFF_BASIS` / `_CAP` | 0.005 / 0.2 | `core/append.py:78,79` |
| `MAX_RETRIES` / `MAX_BATCH` | 8 / 500 | `core/append.py:59,64` |
| PG-Untergrenze | 15 or newer | `reference/configuration.md:16` |
| Vokabular | 15 Eintraege, 11 klein | `awk 'NF && /^[a-z]/'` |
| How-tos unberuehrt | `git diff` leer | selbst geprueft |

Ruling T6-c: **vier Beschraenkungsnamen, nicht drei.** Mein Brief sagte drei
  und im selben Atemzug „alle drei in denselben Fehler" — und das waren
  andere drei. Der Code gilt: `_CHAIN_POSITION_CONSTRAINTS` in
  `storage/postgres.py` enthaelt `event_prev_hash_idx`, `event_pkey` **und**
  `event_hash_idx`; `source_key_pkey` ist der vierte Name und die zweite
  Wiederherstellung. Der Kommentar dort traegt die Begruendung schon
  (Befund W2 der Stufe 1a): `id` und `prev_hash` gehen in den Event-Hash,
  derselbe Hash kann also nur an derselben Kettenposition entstehen. Die
  Ueberschrift bleibt `## Three classes of conflict, two recoveries` — daran
  haengt das Label `(conflict-classes)=`, und drei **Klassen** bei vier
  **Namen** ist richtig. Kosten, falls falsch: eine Ueberschrift und ein
  Label, mechanisch.

Ruling T6-d: **„gemessen durch Drehen der Anlegereihenfolge" gab es nie.**
  Selbst am Code bestaetigt: `tests/test_storage.py:338-363` fuegt eine Zeile
  ein, die `event_pkey` und `event_hash_idx` gleichzeitig verletzt, und
  prueft darum den **Fehlertyp**, nicht den Namen. Die Anlegereihenfolge
  wurde nicht gedreht. Die Seite sagt, was gemessen wurde; die Folgerung
  (alle vier gleich uebersetzen) bleibt, weil sie nicht an dieser Messung
  haengt. Das war eine Annahme in **meinem** Brief, keine im Code.

Ruling T6-e: **das sechste Label `(payload-range)=` bleibt.** Nicht in der
  Produktliste des Briefs, aber `canonicalization.md` soll auf den
  Abschnitt verweisen und nicht auf die Seite. Aufgabe 7 prueft damit gegen
  **sechs** Label, nicht fuenf.

Ruling T6-f: **`namespace` als kleingeschriebener Vokabulareintrag
  angenommen.** Preis bekannt und in `.vale.ini` vermerkt: das Wort darf im
  ganzen Baum keinen Satz und keine Ueberschrift mehr beginnen (Ruling
  T5-b). Billiger als der Fehler, den es sonst wirft. `unencrypted` wurde
  richtigerweise **nicht** eingetragen, sondern durch „in the clear"
  ersetzt — ein Vokabulareintrag ist eine dauerhafte Last, eine
  Umformulierung nicht.

Ruling T6-g: **Mermaid-Syntax bleibt ungeprueft, und das bleibt so.** Bei
  `mermaid_output_format = "raw"` baut Sphinx den Diagrammtext ungeprueft
  ein; ein Syntaxfehler faellt erst im Browser auf. Ein Tor dafuer waere
  Node plus mermaid-cli im CI — zu teuer fuer zwei Diagramme. Die Seiten
  setzen konservativ. Kosten, falls falsch: ein kaputtes Diagramm im HTML,
  sichtbar beim ersten Lesen, nicht stillschweigend.

**Von mir gefundene Unstimmigkeit, an den Pruefer gegeben:**
  `silent-losses.md:62` nennt **zwei** Schweigen der Spezifikation
  (Schluesselkollision, Stapel-Duplikat), aber Zeile 21 sagt ueber CRLF
  „The splitting rule said nothing about line endings" — ein **drittes**.
  Entweder traegt das „as it was about" als Beispiel, oder ein zaehlender
  Leser wird irregefuehrt. Nicht allein entschieden.

**Zahl, die der Umsetzer richtigerweise nicht eingetragen hat:** „in vier von
  fuenf Faellen war die Spezifikation falsch" traegt nicht — der reservierte
  Schluessel `evidence` kommt in der 1a-Spec nicht vor, ist also auch ein
  Schweigen. Die Seite sagt es ohne Zahl. Das ist das vierte Mal in dieser
  Sitzung, dass eine naheliegende Zahl beim Nachsehen nicht trug.

Pruefer auf opus dispatcht mit `review-a816d4f..ed84bf5.diff`.

---

## Vorab-Messung fuer Aufgabe 7 (waehrend der Pruefer von Aufgabe 6 laeuft)

Die Planzahlen **stimmen**, zum ersten Mal in dieser Sitzung ohne Korrektur:
`72` Vorkommen von `§x.y`, `21` Dateien, `20` verschiedene Paragraphen in
`src/` (39), `tests/` (30) und `migrations/` (3). Selbst gezaehlt mit
`grep -rno` plus `cut`/`uniq`. Haeufigste: §3.2 (12x), §3.1 (9x), §5.1 (8x).

Beim Zaehlen zwei Dinge gefunden, die der Plan nicht hatte.

Ruling T7-a: **Es sind drei Klassen von Verweis, nicht eine — und die dritte
  haette der geplante Test durchgewinkt.** Zwei der 72 stehen nicht in einem
  Kommentar, sondern in einer **Fehlermeldung, die der Nutzer liest**:
  `core/canonical.py:53` druckt `(§3.2)`, `core/append.py:301` druckt
  `(§5.1)`. Der Plan bot nur zwei Behandlungen an — auf ein `{ref}`-Label
  abbilden oder als `frozen design record` kennzeichnen — und **beide sind
  hier falsch**: ein `{ref}` erscheint dem CLI-Nutzer als wortwoertlicher
  Unsinn, und `(§3.2, frozen design record)` in einer Fehlermeldung ist
  schlimmer als heute. Wer `previously append` aufruft, hat
  `docs/superpowers/specs/` nicht. Entscheidung: die Zitierung **aus der
  Meldung entfernen**, die Begruendung in den Kommentar darueber, der dann
  nach Klasse 1 auf `{ref}`payload-range`` zeigt. Der geplante Test
  `test_no_bare_paragraph_references_remain` haette
  `(§3.2, frozen design record)` in der Nutzerausgabe **gruen** gemeldet —
  darum ein zweiter Test daneben. In den Plan geschrieben.
  Kosten, falls falsch: zwei Fehlermeldungen ohne Quellenangabe, die der
  Nutzer ohnehin nicht nachschlagen konnte.

Ruling T7-b: **Die Reference zitiert fuenf Fehlermeldungen, und nichts haelt
  sie.** `docs/reference/hash-format.md` traegt seit Aufgabe 6 fuenf
  Meldungen aus `core/canonical.py` woertlich. Nachgemessen am 2026-10-03
  durch **Aufruf des Codes** (nicht durch Zeichenkettensuche): alle fuenf
  stimmen buchstabengenau, `$.amount`/`$`/`$.text` als Pfadpraefix, der
  zitierte Teil jeweils im Seitentext enthalten. Gehalten wird das von
  **nichts** — `test_docs_typed_output.py` deckt nur die Testzahlen im
  Tutorial. Daraus folgt, dass der Plansatz „diese Aufgabe fasst nur
  Kommentare an" falsch war: sie fasst eine Reference-Seite mit an, im
  selben Commit, genau nach der Dokumentationsregel. Der Test dafuer muss
  die Meldungen **vom Code erzeugen lassen**; eine Zeichenkettensuche
  folgte einer geaenderten Meldung in die Seite hinein und koennte nie
  scheitern. Testlogik vorab erprobt (`scratchpad/probe_quotes.py`), fuenf
  von fuenf `OK`.

Ruling T7-c: **datierte Entscheidung gegen lebende Begruendung** — die
  Trennlinie, die die 16 Verweise ausserhalb des Codes aufloest. Ein
  Verweis, der erklaert *warum der Code heute so ist*, muss auf die lebende
  Doku zeigen; ein Verweis, der *eine an einem Datum getroffene Entscheidung
  zitiert*, darf auf den eingefrorenen Bericht zeigen — das Einfrieren ist
  gerade, was ihn zitierfaehig macht. Danach: `DEPENDENCIES.md` (13
  Verweise) bleibt, denn jede Zeile ist ein datiertes Urteil, aber mit
  `(frozen design record)` gekennzeichnet. `pyproject.toml:88` ist lebende
  Begruendung, die Klammer `(§9 of the stage 1a spec)` faellt weg, weil der
  Satz davor die Ausnahme schon vollstaendig begruendet.
  `docs/reference/hash-format.md:22` ist keines von beiden, sondern ein
  **Zitat der Programmausgabe** und folgt T7-a.

Plan auf 1229 Zeilen ergaenzt (Klassen, die Kopplung an die Reference, zwei
zusaetzliche Tests in Schritt 5). Der Brief fuer Aufgabe 7 wird nach dem
Pruefbericht neu erzeugt, damit diese Ergaenzungen mitkommen.

---

## Aufgabe 6 — Pruefung: nicht freigegeben, 8 Befunde. Fixrunde 1 laeuft.

Pruefer bestaetigt die **Ueberlebensliste als vollstaendig** — kein verlangter
Punkt fehlt, keine Begruendung verloren. Alle acht Befunde sind von einer Art:
eine Zahl oder Zusage, die mehr behauptet als die Messung dahinter deckt.

**Selbst nachgemessen, beide bestaetigt:**

1. Backoff: `for attempt in range(MAX_RETRIES)` laeuft achtmal, und
   `except ChainPositionTaken` ruft `time.sleep(backoff_delay(attempt))` am
   Ende **jeder** Runde, auch der achten, bevor die Schleife in
   `raise ChainConflict` faellt. **Acht** Wartezeiten, nicht sieben.
   Obergrenzen `[0.005, 0.01, 0.02, 0.04, 0.08, 0.16, 0.2, 0.2]` — nur die
   letzten zwei am Deckel. Schlechtfall **0,715 s**. Der Satz auf der Seite
   widerlegte sich selbst: `7 x 0.2 = 1,4 s` ist nicht „under a second".
2. Kanten: die Schichtenordnung erlaubt sechs, **fuenf existieren**, genau
   `storage -> contract` nicht. Gezaehlt je Modulpaar (`cli->core` 5,
   `cli->storage` 3, `cli->contract` 2, `core->storage` 8, `core->contract` 3,
   `storage->contract` 0). „half of the permitted edges" ist unter keiner
   Zaehlweise richtig — und die Seite nennt die eine fehlende Kante **eine
   Zeile vorher selbst korrekt**.

Ruling T6-h: **zwei Kommentarzeilen im Code werden in dieser Fixrunde
  mitgezogen**, obwohl Aufgabe 6 „fasst keinen Code an" hiess. Beide sind
  **falsche Aussagen**, und eine ist die Quelle von Befund 1:
  `core/append.py:73-77` traegt denselben Fehler woertlich („seven waits
  between eight attempts, every one of them at the cap"), und
  `tests/test_contracts.py:181-182` sagt „without any one of the five gates
  going off", was der Pruefer gegen die Projektkonfiguration als falsch
  gemessen hat (`ruff check` meldet sehr wohl `TC001`). Eine Seite
  richtigzustellen und ihre Quelle falsch stehen zu lassen, laesst den
  Fehler dort, wo der naechste ihn wieder abschreibt — und die Hausregel
  sagt, Code und Doku ziehen in derselben Aenderung nach. Beides muss
  ausserdem vor dem Einfrieren stimmen. Kosten, falls falsch: zwei
  Kommentarzeilen in einem Doku-Commit, sichtbar im Diff.

Ruling T6-i: **die GitHub-Zahlen in `backup-encryption.md` bleiben
  unveraendert.** Der GitHub-MCP-Server ist in dieser Sitzung nicht
  verbunden (`400: Authorization header is badly formatted`). Der Pruefer hat
  sie darum ausdruecklich **offen gelassen statt zu raten** — das ist das
  richtige Verhalten und wird nicht nachgebessert. Gegen die Briefquelle
  (Architektur §10.5, `architektur.md:1179-1213`) sind sie zeichengenau
  uebernommen. Wer sie vor dem Einfrieren pruefen will, braucht den
  Serverzugang wieder. **Offener Punkt fuer Aufgabe 7.**

**Geparkt, nicht in dieser Runde — Verhaltensfrage:** die achte Wartezeit
  liegt **vor** dem Aufgeben. `time.sleep` laeuft nach dem letzten Versuch
  und dann wird geworfen; das sind bis zu 0,2 s Wartezeit, die niemandem
  nuetzen. Kein Fehler, eine Warze. Eine Aenderung waere Verhalten und
  braeuchte einen eigenen Test — nicht in einem Dokumentationsplan.

**Die Lehre des Pruefers, und sie gilt fuer Aufgabe 7:** zwei der acht
  Befunde stammen aus **Quelltextkommentaren**, die uebernommen statt
  nachgerechnet wurden. Gegen den Code wurde sorgfaeltig geschrieben, gegen
  den Kommentar nicht. Ein Kommentar ist eine Behauptung wie jede andere —
  und Aufgabe 7 geht durch 72 davon.

Fixrunde 1 an den Umsetzer (`a24bbbc116b503fb0`) dispatcht, Bericht nach
`task-6-fix-1-report.md`.

---

## Fixrunde 1 zu Aufgabe 6: alle acht behoben, plus ein neunter. Und mein Tor-Versaeumnis.

Commit `5a8bedb` (sechs Dateien, +54/-24). Der Umsetzer hat **alle acht
Befunde selbst nachgemessen, bevor er sie behoben hat**, alle acht bestaetigt,
keinen zurueckgewiesen — und einen **neunten** derselben Art gefunden, den
weder ich noch der Pruefer gesehen hatten: der Absatz „Each was a gap between
a promise and the world" listete **vier** Zusagen fuer **fuenf** Verluste, der
`evidence`-Schluessel fehlte. Er fiel erst auf, nachdem der Absatz darueber zu
einer ausdruecklichen Rechnung geworden war — Praezision an einer Stelle macht
Unpraezision an der naechsten sichtbar.

**Mein Versaeumnis, und es ist das wichtigste Ergebnis dieser Runde:** ich habe
fuer Aufgabe 6 **fuenf** Tore gefahren (pytest, lint-imports, html, vale,
linkcheck) und „alle gruen" berichtet. `uv run ruff check` und `uv run pyright`
habe ich nie gefahren. `pyright` war **rot**, mit drei Fehlern — und zwar in
`tests/test_schema.py`, dem Test, den **ich selbst** in Aufgabe 5 in einem
kleinen Seitencommit angelegt habe. Der Umsetzer hat nicht bloss gemeldet, dass
es rot ist, sondern **bewiesen, dass es vorher rot war**: seine zwei Dateien
per `git checkout --` beiseite, `git diff --stat HEAD -- src/ tests/` leer,
`pyright` gegen unveraendertes `ed84bf5` identisch `3 errors`. Dann
zurueckgelegt. Richtig gehandelt: er hat es **nicht** behoben, weil es keine
der zwei freigegebenen Kommentarzeilen war.

Das ist der **dritte** Fehler in demselben kleinen Seitencommit, und alle drei
hat jemand anderes beim Lesen gefunden: unbenutztes `# noqa: S603` (RUF100),
fehlendes `@pytest.mark.db`, jetzt pyright strict. Der Seitencommit war
jedesmal die Stelle, an der ich meine eigene Disziplin nicht angewandt habe.

Ruling T6-j: **ich behebe das selbst, nicht der Umsetzer** (Commit `2cac05a`).
  Es ist mein Test und mein Versaeumnis. `Index.dialect_options` ist ein
  `_DialectArgView`, das SQLAlchemy so lose typisiert, dass strict mode die
  Kette `.get(...).get(...)` ablehnt — Member, Argument und die `{}`-Vorgabe
  kommen alle teilweise unbekannt zurueck. Behoben mit dem Mittel, das
  CLAUDE.md vorschreibt: ein `cast` auf die Gestalt, auf die sich dieses
  Projekt verlaesst, **kein** `# type: ignore`. Der Ausdruck ist dabei aus
  dem Dict-Comprehension in eine benannte Funktion gewandert — das war
  ohnehin faellig, denn die verschachtelte Fassung ist der Grund, warum ich
  die fehlende Typisierung beim Schreiben nicht gesehen habe. `Mapping`
  steht in einem `TYPE_CHECKING`-Block mit Zeichenketten-`cast`, weil ruffs
  `TC001` das verlangt und das Cast-Argument beim Fixen selbst bequotet hat.

Ruling T6-k: **jeder kuenftige Dispatch nennt alle sechs Tore namentlich.**
  Mein Aufgabe-6-Dispatch sagte „alle gruen" und meine Pruefer-Dispatch
  listete fuenf. Beide Male fehlte dieselbe Haelfte von Tor 1-3. Der Pruefer
  von Aufgabe 6 hat `pyright` darum auch nicht gefahren. Eine Liste, die
  nicht vollstaendig ist, ist schlimmer als keine: sie sieht nach Pruefung
  aus. Kosten, falls falsch: eine Zeile mehr je Dispatch.

**Die drei Einwaende des Umsetzers, alle angenommen:**
  (1) Befund 8 kostete mehr Text als „ein Satz" — der vorgeschlagene Einschub
  haette **neben** der alten, unvollstaendigen Messung gestanden, zwei
  Messbloecke zum selben Vorgang. Umbau statt Einschub war richtig.
  (2) Die achte Wartezeit gehoert auf die Seite, obwohl ich sie freigestellt
  hatte — ohne sie geht die Summe nicht auf: wer „acht Versuche" liest,
  zaehlt sieben Luecken und kommt auf 0,515 statt 0,715. Der Satz, dessen
  Fehlen den Fehler erzeugt hat, ist genau der Satz, der ihn verhindert.
  (3) Meine Fundstelle war `tests/test_contracts.py:181-182`, richtig ist
  `:182-183`; und die Zeile trug neben der gemessen falschen Aussage auch
  eine ueberholte Zahl („five gates", CLAUDE.md zaehlt **sechs**). Die neue
  Fassung nennt keine Zahl, sondern die Tore, die sie meint.

Alle sechs Tore jetzt selbst gefahren und gruen: ruff `All checks passed!`,
format `38 files already formatted`, pyright **`0 errors`**, lint-imports
`4 kept, 0 broken`, pytest `189 passed`, html/vale/linkcheck sauber.

Plan-Ergaenzung zu Aufgabe 7 als `6f240dc` committet (war uncommitted im Baum
und hat den Umsetzer irritiert). Eng umrissene Nachpruefung der neun Befunde
auf sonnet dispatcht mit `review-ed84bf5..6f240dc.diff`.

Task 6: complete.

Nachpruefung (sonnet) hat **alle neun Befunde als behoben** bestaetigt, jede
Zahl selbst am Code nachgerechnet statt aus dem Bericht uebernommen: Summe
`0.715` aus den acht Obergrenzen, fuenf von sechs Kanten (`storage->contract`
die fehlende), elf Hash-Felder mit `v`/`domain` als Modulkonstanten,
`grep -cin "CRLF|Zeilenende|\r"` ueber das 1a-Spec → `0`, die Rechnung
1+3+1 = 5 deckt sich mit den fuenf Abschnitten, und die zwei vormals
widerspruechlichen Stellen zur Vektor-Neuberechnung sagen jetzt dasselbe. Die
`TC001`-Behauptung hat sie in einer Kopie **selbst nachgemessen**: Symbol nur
in Annotationen → `TC001` feuert; plus ein Laufzeitgebrauch → `All checks
passed!`. Alle sechs Tore selbst gefahren, mit `rm -rf _build` davor.

Ruling T6-l: **ein neuer Befund, und wieder gegen mich — ein Typname, den ich
  nicht nachgesehen habe.** Mein Docstring in `tests/test_schema.py` (und der
  Commit-Text von `2cac05a`) behauptete, `Index.dialect_options` sei ein
  `_DialectArgView`. Selbst nachgemessen per Introspektion:
  `type(index.dialect_options)` ist `sqlalchemy.util._collections.
  PopulateDict`, und `_DialectArgView` ist der Typ von `dialect_kwargs` —
  der flachen Sicht auf dieselben Daten, die den Schluessel
  `postgresql_nulls_not_distinct` in **einem** Stueck schreibt statt in
  zwei. Der `cast` war richtig und bleibt unberuehrt:
  `PopulateDict[str, _DialectArgDict]` ist genau das zweistufige Mapping,
  das `Mapping[str, Mapping[str, object]]` beschreibt. Falsch war nur der
  Name daneben — dieselbe Fehlerart, die dieser Zweig den ganzen Tag auf den
  Doku-Seiten behebt: ein Name uebernommen statt nachgesehen. Behoben als
  `220c6a0`, mit der Messung im Kommentar statt der Folgerung.
  **Historie nicht umgeschrieben**: ein Commit, der die Korrektur samt
  Messung festhaelt, ist der bessere Beleg als eine stillschweigend
  geaenderte Historie — und so haelt es dieses Projekt auch in
  `task-5-must-survive.md`.

Nebenbefund der Nachpruefung, angenommen: der Waechter
  `if index.dialect_options else {}` in meiner ersten Fassung war
  **wirkungslos** — ein leeres Mapping liefert ueber `.get()` denselben
  Rueckfall. Mit dem Umbau ist er weg.

**Stand nach Aufgabe 6:** 105 Commits, alle sechs Tore gruen, 189 Tests,
19 Doku-Dateien, sechs Explanation-Seiten, sechs Label fuer Aufgabe 7.

---

## Aufgabe 7 — Bericht erhalten, alle sechs Tore selbst gefahren

Commit `fae1c25`, BASE `220c6a0`, ein Commit, 34 Dateien, +552/-200.
Begruendung fuer einen statt zwei: die Torfestigkeit des ersten liesse sich
nicht **nachweisen**, weil der Baum dann schon die Aenderungen des zweiten
traegt und `git stash` hier auf einem mit anderen Sitzungen geteilten Stack
liegt. Dazu ist die Kopplung echt — Meldung in `canonical.py`, Zeile in
`hash-format.md` und abgetippte Testzahl im Tutorial haengen ueber zwei Tore
zusammen. Angenommen.

**Selbst gemessen, nicht aus dem Bericht uebernommen:**

| | gemessen |
|---|---|
| ruff / format / pyright | `All checks passed!` / `39 files already formatted` / `0 errors` |
| lint-imports | `4 kept, 0 broken` |
| pytest | **193 passed** (189 + vier neue) |
| html / vale / linkcheck | `build succeeded` (0 WARNING) / `0 errors in 20 files` / 0 Bytes — nach `rm -rf _build` |
| `print`-Aufrufe in `cli.py` | **13** (`grep -c '^\s*print('`) — der Kommentar sagt jetzt dreizehn |
| Zitierungen in Programmausgaben | **0** (`grep § canonical.py append.py` findet nur noch Kommentare, mit `(frozen design record)`) |
| Einfrier-Koepfe | alle **drei** Specs |
| §10.5 im Code | **0** Vorkommen — die Briefangabe war falsch |

**Und ich habe den neuen Test angegriffen statt ihm zu glauben:** einen nackten
Verweis in `core/verify.py` eingeschmuggelt →
`assert not {'src/previously/core/verify.py': 1}`, schlaegt an. Danach
zurueckgespielt, `git diff` leer.

Ruling T7-d: **Zweitziele sind zugelassen.** Der Brief verlangte „je Paragraph
  ein Ziel", der Umsetzer hat fuer §3.1, §4.2, §5 (1a), §7 und §9 ein
  Zweitziel vergeben, weil eine erzwungene Einzelabbildung **falsche Saetze**
  erzeugt haette (sein Beispiel: „`insert_event(..., key=None)`, was
  `{ref}`hash-chain`` erlaubt" — erlaubt wird es vom Vertrag). Das ist
  richtig: die Abbildung dient dem Satz, nicht die Satz der Abbildung. Die
  Regel, die das Zweitziel auswaehlt, steht auf `design-records.md`. Dem
  Pruefer ausdruecklich zur Beurteilung gegeben, weil es eine Hintertuer
  sein koennte. Kosten, falls falsch: 20 Zeilen Tabelle.

Ruling T7-e: **`DEPENDENCIES.md` wird einmal markiert, nicht dreizehnmal.**
  Neun der dreizehn Zitierungen sind woertlich derselbe Satz in neun
  Tabellenzeilen. Ein Absatz ueber der Tabelle plus Link auf
  `design-records.md` sagt dasselbe und macht die Tabelle nicht unlesbar.
  Ebenfalls dem Pruefer vorgelegt mit der Gegenfrage, ob eine einzelne Zeile
  damit ueber die Aktualitaet ihres Ziels luegt.

Ruling T7-f: **der `SELF`-Ausschluss im Test bleibt.** `test_docs_references.py`
  durchsucht `tests/**/*.py`, also sich selbst, und seine eigenen Docstrings
  halten die gemessenen Fundstellen (`§3.2`, `§5.1`) fest. Entweder das Loch
  oder der Verlust der Messung aus der Dokumentation des Tests. Der Umsetzer
  hat das Loch gewaehlt und **benannt** — richtig: ein benanntes Loch ist
  billiger als eine Dokumentation, die ihre eigene Messung nicht nennen darf.

**Die drei Abbildungskorrekturen des Umsetzers gegen meinen Brief**, alle mit
  Begruendung und alle plausibel: §4.6 → `tombstone-seam` statt
  `backup-encryption` (alle vier Zitierungen handeln vom Grabstein, nicht von
  der Blob-Verschluesselung im selben Abschnitt); §3.1 → `hash-chain` statt
  `hash-domain` (`hash-domain` labelt „Separating the domains", also
  `v`/`domain`, wovon keine der neun Zitierungen handelt); §5.1 liegt im
  **Entwurf**, nicht im 1a-Spec. Dem Pruefer zur Nachpruefung gegeben.

**Offener Punkt fuer den Merge, nicht fuer diese Aufgabe:** die abgetippte
  `pytest`-Ausgabe im Tutorial enthaelt
  `rootdir: …/.claude/worktrees/stufe-1a-log`. War vorher schon so, und „tipp
  einen echten Lauf ab" erzwingt es. Nach dem Merge auf `main` waere ein Lauf
  aus dem Hauptcheckout ehrlicher. **Entscheidung des Auftraggebers.**

**Kosten, die der Umsetzer gemeldet hat und die bleiben:** `(frozen design
  record)` muss auf **einer Zeile** mit dem `§` stehen, sonst greift der Test
  nicht. Das hat Kommentare zu Umbruechen gezwungen, die ein Mensch anders
  gesetzt haette, und wird den naechsten ebenso zwingen. Absatzweise Pruefung
  waere freundlicher, aber schwer korrekt zu schreiben. Tauschhandel
  angenommen, Kosten vermerkt.

Pruefer auf opus dispatcht mit `review-220c6a0..fae1c25.diff`, mit dem
Schwerpunkt auf der Abbildungstabelle und dem Auftrag, die zwei neuen Tests zu
**brechen** statt sie zu lesen.

---

## Aufgabe 7 — Pruefung: nicht ohne Nacharbeit. 16 Befunde, Fixrunde 1 laeuft.

Urteil: **17 der 21 Tabellenzeilen tragen**, und die **drei eigenmaechtigen
Korrekturen des Umsetzers gegen meinen Brief sind alle drei richtig** und gegen
die eingefrorene Stelle nachgeprueft. Drei Zeiger fuehren in eine Begruendung,
die ihr Ziel nicht traegt; vier Tore haben Loecher.

**Die vier schweren Befunde selbst nachgemessen, alle vier bestaetigt:**

| Befund | meine Messung |
|---|---|
| H1 `canonical.py:49-53` → `payload-range` | Die Seite endet mit **„For why the range is drawn here and not wider, see {ref}`canonicalization`"** — sie sagt selbst, dass sie das Warum nicht traegt. Zeiger eine Station zu frueh, und der einzige Ort dieser Begruendung im Code. |
| H2 `storage/postgres.py:6` → `module-boundaries` | Alle fuenf Negativ-Eigenschaften gegen `docs/` geprueft: **null Treffer**, jede einzeln. Architektur §5 traegt den Satz woertlich. |
| H3 `test_hashing.py:49` → `timestamps` | „ISO 8601"/„six fractional digits" stehen in `reference/hash-format.md:78` und `reference/cli.md`, **nicht** im `timestamps`-Abschnitt. |
| H4 `design-records.md:70` | ``as `{ref}`label``,`` — zwei Rueckstriche bleiben stehen, Sphinx warnt nicht, weil es kein Verweis ist. |

**Die Methode des Pruefers ist das Ergebnis dieser Runde:** er hat die Tests
**angegriffen statt gelesen**, mit gemessenen Mutationen in Kopien unter dem
Scratchpad. Vier Loecher, die zweimaliges Lesen nicht gefunden hatte:

- `RUNTIME_MESSAGE_FILES` nennt zwei Dateien — und `cli.py`, die **einzige**
  Datei im Baum mit `print` (dreizehnmal), fehlt. Gemessen durchgelassen:
  markierte Meldung in `core/verify.py` → `4 passed`;
  `print("… §9 (frozen design record) …")` in `cli.py` → `4 passed`. Selbst
  nachgeprueft: `grep -rlc "print(" src/` nennt genau `cli.py`.
- `test_the_reference_quotes…` kann **wieder gruen sein, waehrend es falsch
  ist**: sechste Tabellenzeile mit einer Meldung, die niemand druckt → gruen;
  Zitat aus der Zelle in die Prosa verschoben → gruen. Die Verschaerfung
  schloss nur eine Richtung.
- Die `REFERENCE`-Regex uebersieht zwei Formen **schweigend**:
  `{ref}`hash_chain`` (Unterstrich nicht im Zeichenvorrat → gar nicht als
  Verweis erkannt) und `` {ref}`text <target>` `` — **die die Doku selbst
  zweimal benutzt** (`canonicalization.md:71`, `hash-chain.md:197`, von mir
  nachgezaehlt).
- Der `SELF`-Ausschluss: die Begruendung des Umsetzers traf **nicht zu** — er
  hatte die Paragraphennummern aus genau diesem Docstring schon
  herausgeschrieben, das Loch kauft also nichts mehr. Dritter Weg vom Pruefer
  gefahren und gemessen: `SECTION = "§"`, `4 passed`, ruff sauber, Loch zu,
  andere Scharfe unveraendert.

Ruling T7-g: **H2 wird wie §10.1 behandelt — eingefroren.** Dieselbe Lage, und
  §10.1 hat der Umsetzer richtig markiert. Die Tabellenzeile „§5 |
  Architektur | `module-boundaries`" wird „eingefrorener Bericht".
  Begruendung: ein Zeiger, der behauptet, eine Begruendung sei in die Doku
  gewandert, die **nie geschrieben wurde**, ist teurer als eine fehlende
  Seite — ein spaeterer Leser schreibt sie neu statt den eingefrorenen
  Bericht zu lesen.

Ruling T7-h: **die nackte Zitierung in `pyproject.toml` bleibt
  ungeprueft, und das ist eine Entscheidung.** Der Pruefer nennt es
  Inkonsistenz zum Brief („gilt fuer jede englischsprachige Datei"). Die
  Trennlinie ist aber nicht die Dateiendung, sondern **wie die Stelle gelesen
  wird**: ein Kommentar wird allein gelesen und braucht die Markierung auf
  seiner Zeile; eine Tabelle wird als Ganzes gelesen, also traegt ein Absatz
  darueber sie fuer alle Zeilen. Dasselbe Argument rettet die
  `DEPENDENCIES.md`-Entscheidung (T7-e). Gehoert in den Docstring des Tests,
  dann ist es eine Entscheidung und keine Luecke.

Ruling T7-i: **die Lehre hinter H1/H2/H3/M3 gehoert auf die Seite.** Alle vier
  haben eine Ursache: eine Spec-Stelle hat zwei Haelften, die die Doku auf
  Reference und Explanation getrennt hat, und der Verweis hat die falsche
  erwischt. **Zweimal stand die richtige Antwort in der Tabelle schon da.**
  Also: die Tabelle ist je **Zeile** anzuwenden, nicht je Paragraph — genau
  wie die frozen/lebendig-Regel es schon fordert. §3.2 ist der Beweis: mit
  zwoelf Zitierungen der haeufigste Paragraph, dieselben zwei Haelften, und
  der einzige vielzitierte **ohne** Zweitziel. „§3.2 und §5.1 sind
  eindeutig" ist die eine Stelle, an der der Umsetzer seine eigene Regel
  nicht angewandt hat.

**Vom Pruefer bestaetigt und damit erledigt:** die Zweitziel-Regel traegt und
  ist keine Hintertuer (Beweis ist der Fall, in dem sie **fehlt** — §3.2);
  `DEPENDENCIES.md` einmal statt dreizehnmal markieren ist richtig, weil die
  Zeilen selbst ein Datum tragen; `design-records.md` ist **richtig** in
  Explanation, mit vier Gruenden, darunter der tragende: die Tabelle ist ohne
  das Argument um sie herum nicht benutzbar, und sie nach Reference zu heben
  trennte die Zeilen von der Regel, die sie lesbar macht — genau der Fehler,
  gegen den diese Aufgabe geschrieben ist.

**Zur Modalitaet, nach der ich ausdruecklich gefragt hatte:** gemessen gibt es
  **keine** Stelle, an der ein „schreibt vor" zu einem „erklaert" geworden
  ist, ohne dass die Nummer mitgegangen waere. `hashing.py:131` („The event
  hash as {ref}`hash-format` defines it") ist sogar eine Verbesserung — die
  Vorrangregel der Kopfzeile zu Ende gedacht.

**Vier Zahlen des Berichts nachgezogen:** der identische Satz in
  `DEPENDENCIES.md` kommt **achtmal** vor, nicht neunmal; benutzt werden
  **12** Label aus dem Code, nicht 15; ohne Verweis sind **fuenf**, nicht
  vier; und es sind **20** Label, nicht 19 — meine Dispatchzahl war beim
  Absenden richtig und ist durch die neue Seite veraltet.

Fixrunde 1 an den Umsetzer (`ae622bb9abc4f318a`) mit 16 Befunden (H1-H4,
M1-M4, T1-T4, D1-D4).

---

## Aufgabe 7, Fixrunde 1: alle 16 bestaetigt behoben. Drei neue Loecher. Fixrunde 2 laeuft.

Commit `a2671ee`. Alle sechs Tore selbst gefahren und gruen: ruff, format,
pyright `0 errors`, lint-imports `4 kept`, pytest **`194 passed`**,
html/vale/linkcheck sauber aus `rm -rf _build` (20 Dateien).

**Zwei Angriffe selbst gefahren**, in situ mit byteweiser Sicherung, genau die
zwei, die vor der Fixrunde gruen waren: `{ref}`hash_chain`` mit Unterstrich in
einem Kommentar → `1 failed`; sechste Tabellenzeile in `hash-format.md`, die
niemand druckt → `1 failed`. `git status` danach leer. Beide Loecher zu.

Der Pruefer hat seine Suite **erweitert** und drei neue Loecher gemessen, also
hat dreimaliges Angreifen dreimal etwas gefunden, was Lesen nicht fand.

Ruling T7-j: **meine „ein Label" bei H1 war zu eng, der Umsetzer hatte
  recht.** Er nennt zwei (`canonicalization` fuer das Warum,
  `payload-range` fuer die Restriktion selbst). Die Begruendung des Pruefers
  ist die, die mir fehlte: das ist **nicht** der Zweitziel-Mechanismus, der
  *eine* Zitierung nach einer von zwei Haelften aufloest — der Kommentar
  macht **zwei verschiedene Aussagen**, und die Probe ist, dass beim
  Streichen eines Labels ein wahrer Satz seine Quelle verliert. Freigegeben,
  und mein Brief war an dieser Stelle schlechter als seine Umsetzung.

Ruling T7-k: **E1 und E2 werden behoben, E3/E4 geparkt.**
  - **E1** (`migrations/dsn.py:46` wirft eine Meldung, die
    `configuration.md:13` ausdruecklich dokumentiert, und das Tor sieht sie
    nicht) ist derselbe Fehler eine Ebene hoeher: `_modules()` liegt auf
    Zeile 60 und benutzt `SOURCE_DIRS` mit drei Verzeichnissen, drei
    Geschwisterpruefungen benutzen ihn, und Zeile 170 nimmt
    `(ROOT / "src").rglob`. Selbst gegengemessen: die Meldung hat **genau
    die Gestalt der zwei Urspruengstaeter** (implizit verkettetes f-Literal
    in einem `raise`).
  - **E2** (ein zwischen `{ref}` und Rueckstrich umbrochener Rollenaufruf
    ist weder gefangen noch als `unreadable` gemeldet) waere ein
    Schoenheitsfehler — wenn nicht Zeile 43 des Moduls die ausdrueckliche
    **Zusage** traege „A role that fits neither form is reported rather than
    skipped". CLAUDE.md verlangt fuer eine ausdrueckliche Zusage einen Test,
    der bricht, wenn jemand sie zuruecknimmt. Heute ist sie falsch. Also
    heilen oder streichen; heilen ist richtig, weil die Zusage die
    wertvolle Haelfte dieses Tores ist.
  - **E3/E4** (die Spalte `Restriction` liest kein Tor) **geparkt**, und
    nicht aus Bequemlichkeit: die **Werte** jener Spalte stehen bereits in
    der Spalte `Message` derselben Zeile und sind vom verschaerften Tor
    festgenagelt (`^[a-z][a-z0-9_]*$` und `±9007199254740991` stehen in den
    Meldungen). Eine verfaelschte `Restriction` widerspraeche der gepinnten
    Nachbarzelle zwei Spalten weiter, sichtbar fuer jeden Leser der Zeile.
    Ungedeckt ist die **englische Umformulierung**, nicht der Wert. Ein Tor
    dafuer hiesse Prosa gegen Code pruefen; halbfertig waere es schlechter
    als keines. Kosten, falls falsch: eine Reference-Zeile, deren Prosa von
    ihrer eigenen gepinnten Nachbarzelle abweicht.

Ruling T7-l: **`ast.AsyncFunctionDef` ist erledigt, weil gemessen wurde statt
  gelesen.** Die Behauptung des Umsetzers „faellt zur sicheren Seite" hat der
  Pruefer geprueft: ein `async def` mit `§` im Docstring laesst das Tor
  **klagen** statt schweigen, die Kontrolle im gewoehnlichen `def` bleibt
  gruen. Ein Falschtreffer ist in einem bewusst synchronen Projekt die
  richtige Fehlerrichtung, und die Weigerung, eine **ungetestete**
  Erweiterung einzubauen, deckt sich mit CLAUDE.md.

**Meine Zahl war wieder falsch, und diesmal haben es zwei nachgezaehlt.** Ich
  hatte „zwei der drei" Fehlzeiger geschrieben, bei denen die Antwort in der
  eigenen Tabellenzeile schon stand. Der Umsetzer kam auf sechs Fehlzeiger
  und zwei; der Pruefer hat ihn bestaetigt und nachgeschaerft: bei **M1**
  nannte die Zeile zwar `concurrency`, aber die angehaengte Klausel deckte
  den Backoff-Fall nicht ab — richtige Seite aus dem falschen Grund.
  Verlangt man Seite **und** Fall, ist es eins von sechs. Beide Lesarten
  stuetzen seine Zahl. Mein Fehler war, zwei verschiedene Mengen zu
  vermischen: §3.1 war kein Befund, sondern eine bestaetigte Korrektur.

Drei Prosa-Punkte in Fixrunde 2: ein Off-by-one in `DEPENDENCIES.md` („The
thirteenth is §2" — der dreizehnte ist §10.1), ein Selbstwiderspruch in
`design-records.md` (die fuenf Eigenschaften „appear" jetzt genau einmal,
naemlich eine Zeile darueber — gemeint ist „argues"), und ein zu weit
gefasster Lehrsatz (vier der sechs Fehlzeiger waren Faelle der falschen
Haelfte, H2 und M2 nicht).

Task 7: complete.

Fixrunde 2 als `fbc7fee` (3 Dateien, +67/-28). Alle sechs Tore selbst gefahren
und gruen, 194 Tests, Doku aus `rm -rf _build`.

**Das entscheidende Paar selbst nachgemessen, weil es das subtile ist:**
E2a (umbrochener Rollenaufruf, Label existiert **nicht**) → `1 failed`;
E2b (derselbe Umbruch, Label existiert) → `5 passed`. Vorher waren **beide**
gruen, weil der Verweis unsichtbar war. Die Asymmetrie ist der Beweis: der
Aufruf wird jetzt **gelesen**, nicht bloss strenger abgewiesen. `git status`
danach leer.

Ruling T7-m: **`src/` + `migrations/` statt `_modules()` — der Umsetzer hat
  besser entschieden als mein Vorschlag.** Ich hatte beide Wege zur Wahl
  gestellt und die Falschtrefferfreiheit von `_modules()` selbst gemessen
  (9 `§` in 3 Testdateien, alle Docstring oder Kommentar). Sein Grund ist
  der bessere: **ein Tor, dessen Geltungsbereich weiter ist als sein Name,
  ist genau die Art Behauptung, die diese Aufgabe entfernen soll** — und ein
  `§` in einem Testliteral erreicht niemanden. `_modules(directories)` nimmt
  die Verzeichnisse jetzt als Argument, alle vier Pruefungen gehen durch
  denselben Helfer; das war die Ursache, Zeile 170 griff den Pfad **neben**
  dem Helfer von Hand.

**Der Fehler, den seine eigene Suite gefangen hat, und er gehoert ins Ledger:**
  sein erster E2-Versuch hatte `\A` in `AFTER_ROLE`, angewandt mit
  `match(text, pos)`. `\A` bindet an den echten Stringanfang, nicht an `pos`
  — Ergebnis: **alle 61 Verweise im Baum** kamen als `unreadable` zurueck.
  Gefangen, weil er die Kontrollmutation mitgefahren hat. Das ist der Beleg
  fuer die Regel, die Aufgabe 8 aufschreiben soll: ohne Kontrolle beweist
  ein roter Test nur Strenge, nicht dass er liest.

**Dreimal angegriffen, dreimal etwas gefunden.** Die zwei Tore dieses Zweigs
sind in drei Runden verschaerft worden — meine Planfassung, die Korrektur des
Umsetzers, die des Pruefers. Jede Runde fand Loecher, **jede durch gemessene
Mutation, keine durch Lesen.** Die Angriffssuite steht am Ende bei 14
Mutationen plus zwei Kontrollen, `unexpected results: 0`.

**Stand nach Aufgabe 7:** 108 Commits, alle sechs Tore gruen, 194 Tests,
20 Doku-Dateien, 20 Label, 60 `{ref}` im Code, 14 markierte eingefrorene
Verweise, drei eingefrorene Specs.

---

## Aufgabe 8 dispatcht — und warum nicht inline

CLAUDE.md verlangt, die Ausfuehrungsmethode je Plan abzuwaegen. Die vier
Fragen fuer diese Aufgabe: die Fehlerart ist **sichtbar** (eine falsch
formulierte Regel liest sich falsch), das Ergebnis ist Prosa die ich pruefen
kann, es gibt **keine** Kopplung, und sie braucht Kontext, den nur diese
Sitzung hat.

Der letzte Punkt zieht scheinbar nach inline, und CLAUDE.md warnt genau davor:
„holding the knowledge is not a reason to do the work. It is a reason to write
a better brief." Hier kommt ein eigener Grund dazu, der staerker ist als die
Verfahrensregel: **das Publikum der CLAUDE.md ist jemand ohne diese Sitzung im
Kopf.** Ich weiss, was ich gemeint habe — das ist beim Schreiben einer Regel
ein **Nachteil**, weil ich eine schwammige Formulierung nicht als schwammig
lesen kann. Also schreibt sie jemand, der sie zum ersten Mal liest, mit dem
ausdruecklichen Auftrag, meine Formulierungen umzuschreiben, wo sie unklar
sind.

Drei Regeln ueber den Brief hinaus im Dispatch, jede mit ihrem gemessenen
Anlass von heute: (1) jeder Dispatch nennt alle sechs Tore namentlich — mein
Fuenfer-Verzeichnis liess einen roten `pyright` durch zwei Pruefungen; (2) ein
Kommentar ist eine Behauptung wie jede andere — drei Faelle an einem Tag
(Backoff-Kommentar, „nine print calls" statt dreizehn, `_DialectArgView` statt
`PopulateDict`), jedesmal war der Code richtig und die Behauptung daneben
falsch; (3) eine Zusage braucht einen Test, von dem **gemessen** ist, dass er
bricht, **samt Kontrollmutation** — sonst beweist ein roter Test nur Strenge.

Task 8: complete.

---

## Abschlusspruefung des ganzen Zweigs: 11 Befunde. Letzte Fixrunde: alle behoben.

Pruefpaket von Hand gebaut, weil `review-package` verweigerte: **HEAD ist kein
Abkoemmling von `main`.** Drei-Punkte-Diff, 13 560 Zeilen.

**Der Fund, auf den die Pruefung angelegt war — F1, Pruefbefund B5.** Die
eingefrorene 1a-Spec §11 Zusatzbedingung 8 sagt: sind Nutzlast **und**
Einheiten derselben Zeile kaputt, gibt es **zwei** Befunde und nicht einen.
Selbst nachgeprueft: `core/verify.py:119-121` ruft `_payload_finding` und
`_units_finding` getrennt und haengt beide an; `tests/test_verify.py:305` misst
es und haelt die Mutation fest (alle Tests blieben gruen, als die Bloecke
zusammengelegt wurden). **Auf keiner der zwanzig Seiten.** `hash-chain.md:283`
hatte nur die andere Haelfte (W1, ueber Zeilen hinweg). Die Doku behauptete
also **weniger**, als die Pruefung leistet — und die Spec, die es trug, ist
eingefroren. Behoben in `hash-chain.md:285-288`.

**Die Ursache, und sie ist die uebertragbare Lehre:** B5 stand **nicht** auf
`task-5-must-survive.md`. Die Liste war die Rettungsleine, und was nicht darauf
stand, hing an der Aufmerksamkeit des Umsetzers. Vorschlag des Pruefers fuer
die naechste Stufe, angenommen: die Liste **mechanisch erzeugen** — jedes
Befundlabel (`W…`, `G…`, `B…`, `K…`, `N…`) aus Code und Tests ziehen und
abhaken, ob es auf einer Seite angekommen oder ausdruecklich als „bleibt im
eingefrorenen Bericht" vermerkt ist. B5 waere so aufgefallen.

**Zwei Befunde, bei denen der Zweig eine Regel aufschrieb und im selben Atemzug
brach:** `CLAUDE.md` sagte „five suppressions … If you add one, add it here",
es waren sechs, und die fehlende hat **dieser Zweig** hinzugefuegt (F3). Und
`module-boundaries.md` berief sich auf eine Messung „against the project
configuration" und liess **pyright** aus — wenige Zeilen nachdem `CLAUDE.md`
genau das als Lehre des Tages festhaelt (F5). Der Pruefer hat die Mutation
gefahren: `reportUnnecessaryIsInstance` faengt das Beispiel der Seite ab.

Ruling F-a: **Auswahlprinzip der letzten Fixrunde — eine falsche geschriebene
  Behauptung wird behoben, neue Pruefmaschinerie nicht gebaut.** Das ist der
  Standard des Projekts („A comment is a claim"). Danach behoben: F1-F7, F9,
  F10a-c, H-a, H-b. Geparkt: die fuenf Nutzlasten aus dem Code ableiten
  (F6-Tiefe), `collected N items` bewachen (F7-Tiefe), die `:ref:`-Form und
  Fence-Bewusstsein im Label-Regex (F8), der Quadranten-Grenzfall
  `design-records.md` (F11). Alle vier sind echte Arbeit und keine Saetze.

Ruling F-b: **meine F3-Begruendung war falsch, der Umsetzer hat gemessen.** Ich
  nannte die `A001`-Suppression in `docs/conf.py` „tragend". Gemessen:
  `extend-exclude = ["docs"]` haelt `ruff check .` aus dem Verzeichnis
  (36 Dateien, **keine** unter `docs/`), und der pre-commit-Hook setzt
  `--force-exclude`, ueberspringt die Datei also auch. **Kein Tor erreicht
  sie.** Selbst gegengemessen. Die Zahl ist jetzt sechs **und** die Datei sagt,
  dass diese eine kein Tor braucht — besser als meine Anweisung.

Ruling F-c: **H-b besser geloest als verlangt.** Ich hatte „Zaehlverfahren
  danebenschreiben oder Zahl ersetzen" zur Wahl gestellt. Der Umsetzer hat die
  Zahl **ersatzlos gestrichen** und nur das Verfahren hingeschrieben, mit der
  Begruendung, dass dann nichts mehr veraltet, sobald jemand einen Kommentar
  umformuliert. Gemessen: `83` reproduziert mit **nichts** — 98 heute, 97 beim
  Commit der die Zahl schrieb, 168/163 ueber den ganzen Baum, 72 mit
  Stichwortfilter. Dazu der Hinweis, dass die Gross-/Kleinschreibung die
  tragende Haelfte des Musters ist.

Ruling F-d: **der dritte Nummernraum, von mir selbst nachgetragen** (`2de4791`).
  Der Umsetzer fand ihn beim Zaehlen fuer H-b: `ruling T6-b`, `T10-c` und neun
  weitere, **16 Zitierungen / 11 Label** in `src/`, `tests/`, `pyproject.toml`
  — und `CLAUDE.md` beschrieb nur die zwei Pruefbefund-Raeume. Selbst
  gemessen und es ist schlimmer als undokumentiert: `.gitignore:24` schliesst
  `.superpowers/` aus, **das Ziel wird nicht ausgeliefert.** Ein Ruling-Label
  ist damit schwaecher als ein `W2` oder ein eingefrorenes `§` — beide sind
  erreichbar, ein Ruling fuer niemanden. Regel: das Label traegt Provenienz,
  **der Grund steht im Kommentar daneben**; gemessen tun das alle sechzehn
  schon, und `_CHAIN_POSITION_CONSTRAINTS` ist als Vorbild benannt. Ich habe
  es selbst geschrieben, weil es meine Rulings sind.

**Was der Pruefer gegen eine echte migrierte PostgreSQL-17 gemessen und
richtig befunden hat**, und das gehoert ins Hauptbuch, weil es die Arbeit
abschliesst: `database-schema.md` **vollstaendig** — alle 9+6+3 Spalten mit Typ
und Nullbarkeit und **alle 13 Beschraenkungs-/Indexnamen**, darunter die fuenf
von PostgreSQL erzeugten, die kein Test festnagelt. Dazu der festgenagelte
Vektor byteweise (drei Digests **und** drei kanonische JSON-Zeichenketten), die
fuenf Fehlermeldungen zeichengenau, elf Hash-Felder, acht Backoff-Schranken und
Summe 0,715, fuenf von sechs Importkanten, vier Vertraege, der abgetippte
pytest-Lauf mit 15 Dateizaehlern und 15 Prozentwerten, `74`/`71` Pakete, und
die Verweis-Arithmetik 72 = 14 + 2 + 56. **Davon war ein Satz falsch** (F4,
`cli.md:61`).

**Stand:** 112 Commits, alle sechs Tore gruen, 194 Tests, 20 Doku-Seiten,
drei eingefrorene Specs. Plan vollstaendig: acht von acht Aufgaben.

**Offen fuer den Betreuer, dreierlei:** die `rootdir:`-Zeile im Tutorial; ob
`CLAUDE.md` mit 331 Zeilen zu lang ist; und die GitHub-Zahlen in
`backup-engryption.md`, die in dieser Sitzung nicht nachpruefbar waren.
