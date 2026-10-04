# SDD ledger — plan: docs/superpowers/plans/2026-10-04-aeusserer-anker.md

Spec: `docs/superpowers/specs/2026-10-04-aeusserer-anker.md` (abgenommen im
Gespräch, friert in Aufgabe 3 ein). Worktree `.claude/worktrees/aeusserer-anker`,
Zweig `worktree-aeusserer-anker`, Basis `b0396b6`, Start-HEAD `edcb9e0`,
232 Tests (gemessen). Freigabe des Betreuers 2026-10-04: „passt, go!",
„subagenten bitte".

Regeln dieser Ausführung, über den Skill hinaus:
- Prüfer schreiben ihren Bericht in eine Datei hier (`task-N-review.md`,
  `task-N-re-review-R.md`) und geben ≤15 Zeilen zurück.
- Controller committet nie, während ein Umsetzer läuft; Umsetzer stagen
  namentlich.
- Einträge hier knapp, Fakten statt Prosa.
- Modelle: Umsetzer Opus; Aufgabenprüfungen Opus; Nachprüfungen Sonnet, wenn
  die Fixrunde nur Prosa trifft, sonst Opus; Endprüfung Opus.

## Vorab-Scan

| Paar / Aufgabe | produziert ↔ konsumiert | Befund |
|---|---|---|
| 1 ↔ 2 | `Anchor`, `parse_anchors`, `format_anchor`, `examine`, `Examination`; drei Befundtexte; Label `external-anchor` | Namen und Texte gleichlautend in beiden Aufgaben (am Plantext verglichen). Befundtexte enden auf festem Text → `_is_the_same_sentence` in A2 findet sie. |
| 1 ↔ 2 | `hash-chain.md` (A1) nennt Prüfarten und `verify`-Schalter, die A2 baut | Vorgriff um eine Aufgabe → Ruling P-1. |
| 1 ↔ 3 | Tabelle und Zusage auf `hash-chain.md` ↔ README, Anleitungen | A3 liest die Seite; „nicht mehr zusagen, als die Tabelle hält" steht im Plan. Sauber. |
| 2 ↔ 3 | Ausgaben der Kommandos ↔ Tutorial, Anleitungen | Tutorial-`verify`-Block ist zwischen A2 und A3 veraltet → Ruling P-2. |
| 1, 2, 3 | Testlauf-Block im Tutorial in jeder Aufgabe | 251 / 263 / 263, am Plantext gezählt (12 + 9 `def test_`, parametrisiert 7+2 und 4). |
| A1 in sich | Tests ↔ Code | Alle sieben Parser-Fälle gegen `parse_anchors` durchgespielt, alle acht DB-Tests gegen `examine`: stimmig. Mutationstabelle: vier Zeilen, je gegen die Tests geprüft. |
| A2 in sich | Tests ↔ Code | `test_exact_without_anchors…` braucht keine DB, weil `_cmd_verify` vor `_storage()` wirft: stimmig. Hinweis als Literal im `print`, damit `_message_patterns` ihn sieht: im Plan begründet. |
| A3 in sich | — | Nur Doku; Kopf wörtlich aus der 1b-Spec Z. 3–14 (dort geprüft). |

Ruling P-1: **Die Seite in A1 darf die Schalter `--anchors`/`--exact` und das
Kommando `anchor` nennen, obwohl A2 sie erst baut** — Namen sind im Plan fest,
Vorgriff um eine Aufgabe wie in 1b (T4-d). Kosten, falls falsch: ein Satz.

Ruling P-2: **Der `verify`-Block im Tutorial bleibt zwischen A2 und A3
veraltet** (eine stderr-Zeile fehlt); A3 tippt die Sitzung neu. Kein Tor hält
ihn, und zweimal tippen wäre Leerlauf. Kosten, falls falsch: ein Zwischenstand
im Zweig, nie auf main.

## Task 1 — Dispatch

BASE `edcb9e0`. Umsetzer Opus. Brief `task-1-brief.md`, Dispatch
`task-1-dispatch.md`, Bericht `task-1-report.md`.

Vorbereitet, während A1 läuft: `task-1-review-dispatch.md` (Platzhalter
HEAD_SHA/DIFF_FILE; Bericht → `task-1-review.md`, Rückgabe ≤15 Zeilen),
Briefs 2 und 3 gezogen, `task-2-dispatch.md` (Platzhalter TASK1_CARRY),
`task-3-dispatch.md` (Platzhalter TASK12_CARRY).

## Task 1 — Bericht

Commit `11de3f6` (Opus 5.5), DONE_WITH_CONCERNS. 251 Tests, 97.53 %,
`core/anchor.py` und `core/verify.py` 100 %, sechs Tore grün, sieben Dateien
namentlich gestaged, Tree clean.

- **Mutationen nicht gemessen.** Der Berechtigungs-Klassifizierer hat dem
  Umsetzer die erste Mutation (`if anchored != row.hash:` → `if False:`) als
  „Security Test Removal" verweigert; er hat keinen anderen Weg versucht.
  Kontrolle ohne Mutation: 36 passed. **Ich führe sie nicht selbst aus und
  gebe sie keinem anderen Agenten** — eine verweigerte Aktion wird nicht über
  einen zweiten Weg erledigt. Frage an den Betreuer gestellt.
- Abweichung: `examine` riss `C901` (11 > 10) mit dem Rumpf aus dem Brief →
  Helfer `_closing_findings` für den Teil nach dem Durchlauf. Plan-Defekt: ich
  habe die Komplexität von `examine` nicht gemessen.
  Ruling T1-a: **Helfer bleibt** — Ursache entfernt statt Symptom
  unterdrückt, Verhalten und Texte unverändert. Kosten, falls falsch: ein
  Funktionsname. Plan-Nachtrag folgt.
- Abweichung: ruff hat zwei f-Strings auf eine Zeile gezogen und Importe in
  `test_verify.py` sortiert; Texte unverändert.
- Bedenken: zwei Kommentare nennen noch `verify`, wo der Durchlauf `examine`
  heißt (`_check_event`-Docstring, Stapel-Kommentar) → an den Prüfer.
- Seite: Abschnitt geschrieben, nennt die CLI-Schalter nicht (P-1 nicht
  gebraucht). Tutorial-Testblock neu (Seed 1203233239).

Prüfung (Opus) dispatcht: Paket `review-edcb9e0..11de3f6.diff`; dem Prüfer
ausdrücklich **keine** Mutation aufgetragen, nur Begründung aus dem Code,
als solche gekennzeichnet.

## Task 1 — Prüfung (Opus 5.5): Needs fixes

Bericht in `task-1-review.md`. Keine Critical. Spec ❌ nur wegen der
ungemessenen Mutationen; Prüfer liest aus dem Code, dass alle vier rot würden.
- I1 (plan-mandated): drei Docstrings zitieren „Review focus N" ohne Plan;
  einer besteht nur aus dem Zitat. Der Doku-Plan hat eine eigene Liste.
- I2: `_check_event`-Docstring sagt, `verify` laufe über Stapel — tut
  `examine`.
- Minors 1–6; ⚠️ 2 (Tore nicht nachgefahren, wie beauftragt; C901 nur gezählt).

**Freigabe des Betreuers für die Mutationen: „Im Baum messen".** Vom
Controller gemessen an `11de3f6` (Skript mit Sicherungskopien, Baum danach
sauber): M1 3 rot, M2 2 rot, M3 1 rot, M4 2 rot, Kontrolle 36 passed davor
und danach — Zeile für Zeile wie die Plan-Tabelle. Protokoll:
`task-1-mutations.md`. Für spätere Mutationsschritte gilt dieselbe Erlaubnis;
verweigert das System wieder, misst der Controller.

Ruling T1-b: **„Review focus N" ist ein Label je Plan und wird wie ein Ruling
zitiert** — Grund im Satz daneben, Plan-Datum am Label. Der Plantext gab die
drei Docstrings nackt vor (mein Fehler, dieselbe Klasse wie die §-Docstrings
in 1b). Kosten, falls falsch: drei Docstrings.
Ruling T1-c: **Minor 4 (`_closing_findings` nimmt `anchors` nur fürs Maximum)
bleibt** — Geschmack. Minor 6 (BOM) ist für den Kern richtig; A2 öffnet mit
`utf-8-sig` (steht im Brief).

Fixrunde 1 an den Umsetzer: I1, I2 + Minor 1, Minor 2 (Seite: „up to the
newest anchor", „the chain alone"), Minor 3 (zwei `exact=True`-Assertions),
Minor 5 (sichtbare Kontrolle). FIX_BASE `11de3f6`. Zahl bleibt 251.

Task 1: fix round 1/5 (6 addressed, 0 open — mutations measured, I1 labels,
I2 `examine` in two comments, minors 2/3/5; commits 11de3f6..c7d8b47)

Re-Review (Sonnet): alle Befunde ADDRESSED, keine neue Breakage; Bericht
`task-1-re-review-1.md`.
Task 1: minor (deferred): `_count_finding`-Docstring zitiert `verify() -> []`
  als datierte Messung; kann als Gegenwart gelesen werden. Für die Endprüfung.
Task 1: note: Mutationsprotokoll M2 weicht im Wortlaut von der Plantabelle ab
  (Schleife über leeres Tupel statt Block entfernt), Wirkung gleich.

Task 1: complete (commits edcb9e0..c7d8b47, review clean after fix round 1)

Plan-Commit `4d1720a`: Nachtrag T1-a (C901 von `examine` ungemessen → Helfer),
T1-b (Label je Plan), drei Docstrings der A2-Tests korrigiert, zwei Regeln in
Global Constraints (Mutationen erlaubt; Label nennt Plan). A2-Funktionen
vorab gemessen: `_read_anchors` 4, `_cmd_verify` 5, `_cmd_anchor` 4.

## Task 2 — Dispatch

BASE `4d1720a`. Umsetzer Opus. Brief neu gezogen (537 Zeilen, kein nacktes
Label mehr), Dispatch `task-2-dispatch.md` mit dem Übertrag aus A1
(`_closing_findings`, BOM/`utf-8-sig`, Label-Regel, Mutations-Erlaubnis).
Umsetzer-Agent `a802b3480dc5faed5`.

Vorbereitet, während A2 läuft (alle mit Platzhaltern für HEAD und Paket):
`task-2-review-dispatch.md`, `task-3-review-dispatch.md` (zusätzlich
BASE_SHA), `final-review-dispatch.md` (HEAD_SHA, CODE_DIFF, DOCS_DIFF;
Bericht → `final-review.md`; neu gegenüber 1b: der Prüfer **benutzt** die
Kommandos von Hand und legt das Protokoll in den Bericht; erwartet einen
Abschnitt `## Rückstandsliste vor der Endprüfung` hier im Ledger).

## Task 2 — Bericht

Commit `2637c8e` (Opus 5.5), DONE_WITH_CONCERNS. 263 Tests, 97.64 %,
`cli.py` 100 %, sechs Tore grün (laut Bericht), sechs Dateien, Tree clean.
Vier Mutationen rot wie vorhergesagt, beide Kontrollen grün, nichts
verweigert.
- Bedenken: `how-to/verify-the-chain.md:8` sagt noch „takes no arguments" →
  A3 Schritt 1 (steht im Brief). Tutorial-`verify`-Block eine Zeile kurz →
  P-2, A3.
- Bedenken: Befund-Zitatprüfung läuft nur Seite → Code; ein Grund im Kern,
  den `cli.md` nicht zitiert, bleibt unbemerkt. Docstring sagt es. → Prüfer.
- Abweichung: `tail -1` aus meinem Dispatch liefert „No fixes available",
  nicht die Zahl (Dispatch-Defekt). Gemessen: 24 `print`.
- Abweichung: ruff zog ein zweizeiliges `raise` zusammen. Testblock aus dem
  zweiten Lauf (Seed 546515917), der erste war nur an der alten `251 passed`
  rot.

Prüfung (Opus) dispatcht: Paket `review-4d1720a..2637c8e.diff`.

## Task 2 — Prüfung (Opus 5.5): Needs fixes

Bericht in `task-2-review.md`. Keine Critical. Reihenfolge, Spitze aus
demselben Durchlauf, Zählungen (24 `print`, acht Kommandos, C901 2/4/5/4),
`cli.md`, Tutorial-Block (263, Summe und Prozente nachgerechnet): alles ✅.
- I1 (plan-mandated, an der Kommandozeile gemessen): `--anchors -` mit
  Nicht-UTF-8 → Traceback, **Code 1** (= Befund für einen Cron-Job); BOM auf
  stdin verweigert. Der Rumpf aus dem Plan ließ den stdin-Zweig vor dem `try`
  und ohne `utf-8-sig`. Widerlegt `cli.md:64–69` für `-`.
- Minor 1: `cli.md:73` „each line is checked" — fehlendes Event wird je `id`
  gemeldet, nicht je Zeile. Minor 2: Präfix `FINDING <n>: ` der zitierten
  Zeilen ungeprüft. Minor 3: Docstring nennt die Richtung Seite → Code nur
  für Befunde, gilt auch für stderr-Hinweise.
- ⚠️ 1: Mutationen nicht wiederholt (wie beauftragt).

Ruling T2-a: **Beide Quellen werden als Bytes gelesen und an einer Stelle
dekodiert (`utf-8-sig`), in einem `try`; Zeilen über
`io.StringIO(text, newline=None)`.** Plan-Defekt, meiner: ich habe die
Komplexität des Rumpfs gemessen, nicht sein Verhalten auf stdin. Rumpf vorab
im Scratchpad gemessen (`stdin_probe.py`: plain, BOM+CRLF, Nicht-UTF-8, leer —
je Datei und stdin; fehlende Datei, Verzeichnis; C901 4; `StringIO` mit
`newline=None` bricht wie Textmodus, `splitlines()` bräche auch an U+2028).
Dateimeldungen wortgleich. Kosten, falls falsch: eine Funktion.
Ruling T2-b: **Minor 1 und 3 werden mitgefixt** (je ein Satz).
Ruling T2-c: **Minor 2 wird mitgefixt**: die Zitatprüfung hält auch die Form
`FINDING <Ziffern>`; die Code-Seite derselben Form halten die exakten
Vergleiche in `tests/test_cli.py` — im Kommentar benannt, weil die Form dann
im Test steht und nicht aus `cli.py` gelesen wird. Kosten, falls falsch: eine
Assertion.

Fixrunde 1 an den Umsetzer (`task-2-fix-1-dispatch.md`), FIX_BASE `2637c8e`.
Zwei neue Tests (stdin BOM+CRLF, stdin Nicht-UTF-8), der bestehende
stdin-Test bekommt Bytes; drei Mutationen. Vorhersage 265.

Task 2: fix round 1/5 (4 addressed laut Bericht, 0 open — stdin wie Datei,
`cli.md` Satz zur wiederholten `id`, Präfix `FINDING <id>` gehalten,
Docstring; commits 2637c8e..81992f9). 265 Tests, 97.65 %, sechs Tore grün.
Mutationen: beide Zeilen der `_read_anchors`-Tabelle wie vorhergesagt,
`FINDINGS 42` rot. Von Hand: Nicht-UTF-8 auf `-` → ein Satz, Code 2.
- Bedenken: mit `-` und Eingabe ohne Anker heißt die Meldung weiter „the
  anchor file holds no anchor" (aus `core/anchor.py`). → Rückstandsliste.
- Notiz: erster Vale-Lauf rot (Kontraktion in `cli.md`), umformuliert,
  Tore danach neu.

Nachprüfung (Opus, weil Code) dispatcht: Paket `review-2637c8e..81992f9.diff`.

Re-Review (Opus 5.5): alle vier Befunde ADDRESSED, keine Critical/Important;
Bericht `task-2-re-review-1.md`. Von Hand nachgefahren: Nicht-UTF-8, BOM mit
nur Kommentar, `/dev/null` auf `-` → je ein Satz, Code 2.
Task 2: minor (deferred): Docstring von `_read_anchors` ist kein Raw-String —
  `\r\n`, `\r`, `\n` sind zur Laufzeit Steuerzeichen, `help()` zerbricht den
  Satz. Muster im Baum: `core/units.py:25` (`\\r\\n`). Für die Fixwelle.
Task 2: minor (deferred): `the anchor file holds no anchor` kommt aus
  `core/anchor.py` und sagt „file", auch für `-`.
  Ruling T2-d: **Der Kern nennt keine Quelle** — er bekommt Zeilen, und ein
  zweiter Einstieg (MCP) hat keine Datei. Die Meldung wird in der Fixwelle
  quellenneutral (`the input holds no anchor`); `cli.md` sagt schon „Input
  without a single anchor line". Kosten, falls falsch: ein Satz, zwei Tests.
Task 2: minor (deferred): `cli.md` „a file that can't be read" — für `-`
  unvollständig (derselbe `except OSError` fängt die Standardeingabe).
Task 2: note für die Endprüfung: geschlossene Standardeingabe
  (`sys.stdin is None`) → `AttributeError`, Traceback, Code 1; keine
  Regression. Allgemeiner: jede unerwartete Ausnahme endet mit Code 1, dem
  Code eines Befunds — fail-closed, aber nicht unterscheidbar.

Task 2: complete (commits 4d1720a..81992f9, review clean after fix round 1)

Plan-Commit `1df139c`: Nachtrag T2-a am Rumpf von `_read_anchors` (Zweig vor
dem `try`; Lehre: Plan-Code auf jedem Weg ausführen, nicht nur messen),
Review Focus 1 und 2 auf die Standardeingabe erweitert, Zahlen 263 → 265,
erwartete Zahl der Aufgabe 3 nachgezogen.

## Task 3 — Dispatch

BASE `1df139c`. Umsetzer Opus. Brief neu gezogen (135 Zeilen, 265), Dispatch
`task-3-dispatch.md` mit dem Übertrag aus A1 und A2 (Seite nach Fixrunde:
„up to the newest anchor", „the chain alone"; zwei bewusst veraltete Stellen;
`cli.md` fertig und geprüft; 265; Vale 22 Dateien; stdin wie Datei).
Umsetzer-Agent `a42f2e5330ab18275`.

## Task 3 — Bericht

Commit `a09f56a` (Opus 5.5), DONE_WITH_CONCERNS. 265 Tests, 97.65 %, sechs
Tore grün (laut Bericht), sechs Dateien, Tree clean, nicht gepusht.
Tutorial aus einem Lauf gegen frischen `postgres:17`-Container in frischem
Klon; `uv sync`-Block unverändert (Maschinenpfad).
- Abweichung: Spec-Einleitung behält einen Satz mehr (wer die Zusage gab,
  wann). → Prüfer.
- Abweichung: README ohne Aufzählungspunkt zum Anker unter „What it does"
  (meine Resolution 4 „Nothing else"). → Prüfer.
- `design-records.md`: „fifteen" `§`-Zeilen, gemessen; kein unmarkiertes.
- Nicht gefahren: die Routine als **eine** Zeile (`verify … && anchor >> …`),
  nur ihre Teile samt stdin-Form; die Bedingung „once the log holds at least
  one event" aus `cli.md` übernommen. → Prüfer liest, Endprüfung fährt die
  Anleitungen von Hand.

Prüfung (Opus) dispatcht: Paket `review-1df139c..a09f56a.diff`.

## Task 3 — Prüfung (Opus 5.5): Needs fixes

Bericht in `task-3-review.md`. Keine Critical. Tutorial gleicht dem
Rohprotokoll Zeichen für Zeichen, Testblock 265 (Summe nachgerechnet),
Spec-Kopf per `diff` identisch mit 1b Z. 3–14, §10 hat 15 Punkte, README und
`design-records.md` halten.
- I1: `restore-from-a-backup.md:36–45` — der Festpunkt-Fall prüft mit
  `--exact` gegen die **ganze** Datei. `--exact` vergleicht mit dem jüngsten
  Anker, die Routine hängt laufend Anker an → ein korrekter Restore auf einen
  früheren Punkt meldet jeden späteren Anker als fehlend, und `:49–50` sagt
  „discard". Geht auf Spec §5.1 zurück (zweiter Fall setzt stillschweigend
  voraus, dass der Anker der jüngste der Datei ist).
- I2: `:33` „came back from the write-ahead log" stellt als Tatsache hin, was
  keine Prüfung sieht (Tabelle Zeile 3).
- Minors 1–6; ⚠️ 2 — beide vom Controller nachgemessen: Trailer
  `Assisted-By: Claude Opus 5.5` ✓.; `git grep '§'` über `src tests
  migrations` 15 Zeilen an `b0396b6` und an HEAD, zeilengleich ✓.

Ruling T3-a: **README bekommt den Aufzählungspunkt zum Anker.** Meine
Resolution 4 („Nothing else") war zu eng. Kosten, falls falsch: eine Zeile.
Ruling T3-b: **Der Satz in der Spec-Einleitung (wer die Zusage gab, wann)
bleibt** — Herkunft ist der Zweck eines eingefrorenen Berichts.
Ruling T3-c: **Der zweite Fall der Restore-Anleitung wird „Restore auf einen
früheren Punkt".** Die Befunde gegen die ganze Datei sind **wahr** — ein
solcher Restore ist ein Abschneiden, und das zu sehen ist der Zweck der
Anker. Geprüft wird gegen die Datei, wie sie am Restore-Punkt stand (Zeilen
bis einschließlich des letzten Ankers davor, `head -n N`); `--exact` nur,
wenn der Punkt mit diesem Anker zusammenfällt; die Schnittzeile ergibt sich
aus `the log ends at <tip>`; die Routine läuft danach gegen die gekürzte
Datei weiter, die alte bleibt als Beleg dessen, was der Restore aufgab.
Hosting-neutral, eine Shell-Zeile — besteht den Einfachheits-Check.
Kosten, falls falsch: ein Abschnitt einer Anleitung.
Ruling T3-d: **`hash-chain.md` bekommt einen kurzen Absatz** (ein Restore
auf einen früheren Punkt ist für die Anker eine gelöschte Spitze), damit die
Anleitung verweisen kann statt zu begründen.
Ruling T3-e: **Der Spec bleibt eingefroren, wie committet.** §5.1 ist beim
zweiten Fall unvollständig; die Seite gilt, das Protokoll (`index.md`) hält
es fest. Wie in 1b: Befunde nach dem Einfrieren gehen nicht in den Spec.

Fixrunde 1 an den Umsetzer (`task-3-fix-1-dispatch.md`), FIX_BASE `a09f56a`.
Pflicht: eine echte Sitzung (leeres Log, drei Anker über die Routine-Zeile
wie gedruckt, viertes Event, Restore auf Anker 2 per rohem SQL, Schnitt,
`--exact`), Protokoll in den Bericht. Zahl bleibt 265.

Für die Rückstandsliste (Gestaltungsfrage, vom Spec §3 so festgelegt):
`anchor` druckt bei einem Befund die `FINDING`-Zeilen auf **stdout** —
`>> anchors.txt` schreibt sie in die Ankerdatei. Die Anleitung sagt jetzt,
dass man sie von Hand entfernt; sauberer wäre, `anchor` ließe auf stdout nur
je eine Ankerzeile zu. Entscheidung des Betreuers, nicht meine.

Task 3: fix round 1/5 (8 addressed laut Bericht, 0 open — Restore auf einen
früheren Punkt, beide Richtungen über dem jüngsten Anker, erstes Ankern,
Einleitung und Titel, Code 2, README-Punkt, `design-records.md`, Absatz auf
`hash-chain.md`; commits a09f56a..da79b41). 265 Tests, Vale 22 Dateien, sechs
Tore grün. Sitzung in fünf Schritten gegen frischen Container gefahren, jede
wie vorhergesagt; Protokoll im Bericht.
- Bedenken: die Routine hängt dieselbe Spitze erneut an, wenn kein Event
  dazukam → „n anchors hold" wächst mit Läufen. Nicht dokumentiert. → Prüfer.
- Bedenken: die Anleitung setzt voraus, dass der Betreiber weiß, welchen
  Restore er gemacht hat. → Prüfer.
- Abweichung: Schnitt als `head -n 2` (Beispiel) statt `<N>`; Seitentitel
  geändert (Label gleich). → Prüfer.
- Nicht gefahren: Minor 1, Hälfte „Kette mit Befund" — aus `_cmd_anchor` und
  `tests/test_cli.py:1006` übernommen, im Bericht so benannt.

Nachprüfung (Opus) dispatcht: Paket `review-a09f56a..da79b41.diff`.

Re-Review 1 (Opus 5.5): alle acht Punkte ADDRESSED, aber **zwei neue
Important** im neuen Abschnitt; Bericht `task-3-re-review-1.md`.
- N1: kein Fall für „kein Anker auf oder unter der Spitze" (Restore vor den
  ersten Anker) → `head -n 0`, leere Datei, Code 2, kein nächster Zug.
- N2: **der Schnitt kommt aus der beobachteten Spitze, nicht aus dem
  gemeinten Restore-Punkt.** Gegen eine so geschnittene Datei kann „missing"
  nicht mehr auftreten → der zweite Fall sieht nie ein Abschneiden; ein
  Replay, das zu früh stehen blieb, geht mit Code 0 durch. Herkunft: mein
  Ruling T3-c („die Schnittzeile ergibt sich aus `the log ends at <tip>`").
- Minor N3 (README:89 zitiert den alten Titel), N4 (`id` und Zeilennummer im
  Beispiel beide 2), N5 (`:35` „although nothing is missing"), N6 (Restore
  auf einen Punkt über dem jüngsten Anker hat keinen Abschnitt).
  Out-of-scope 1: Duplikatzeilen der Routine, ein Satz wert.

Ruling T3-f (**ersetzt den Schnitt aus T3-c**): **Der Maßstab ist die
Ankerdatei, wie sie am gemeinten Restore-Punkt stand, und das weiß man von
außerhalb der wiederhergestellten Datenbank — vom Ablageort der Datei**
(Version, Kopie, Nachricht von damals). Deckt sich mit Spec §10 Punkt 3: der
Anker trägt keinen Zeitpunkt, das „wann" gibt der Ablageort. Gegen diese
Datei ist „missing" ein **Verlust**. Der Schnitt an der beobachteten Spitze
bleibt nur als schwächerer Ausweg für eine Datei ohne Geschichte, mit seiner
Grenze zuerst gesagt: er zeigt kein Abschneiden. Mein Fehler in T3-c: ich
habe die Prüfung ihren Maßstab aus dem Ergebnis nehmen lassen, das sie
prüft. Kosten, falls falsch: derselbe Abschnitt noch einmal.
Ruling T3-g: **N3–N6 und der Satz zu den Duplikatzeilen gehen mit.**

Fixrunde 2 an den Umsetzer (`task-3-fix-2-dispatch.md`), FIX_BASE `da79b41`.
Pflicht: die Seite dreimal als Betreiber lesen (Replay zu früh stehen
geblieben; absichtlicher früherer Punkt mit versionierter Datei; dasselbe
mit nur angehängter Datei) und je eine Zeile in den Bericht.

Task 3: fix round 2/5 (7 addressed laut Bericht, 0 open — Maßstab vom
Restore-Punkt, Ausweg mit Grenze zuerst, Restore vor den ersten Anker,
erster Fall nennt „missing" einen Verlust und deckt jeden Punkt über dem
jüngsten Anker, `--exact`-Satz, README-Linktext, Duplikatzeilen; commits
da79b41..7c936be). 265 Tests, Vale 22 Dateien, sechs Tore grün.
`hash-chain.md` unberührt (Absatz stimmt weiter).
- Bedenken: der Hauptweg wurde nicht als eigener Fall gefahren; keine neue
  Sitzung, jede gezeigte Kommandozeile lief in Runde 1. → Prüfer.
- Abweichung: Datei des Restore-Punkts und Schnittdatei des Auswegs heißen
  beide `anchors-restored.txt`; gemeinsamer Unterabschnitt danach. → Prüfer.

Nachprüfung 2 (Opus) dispatcht: Paket `review-da79b41..7c936be.diff`.

Re-Review 2 (Opus 5.5): N1–N6 und Beobachtung 1 ADDRESSED, keine neue
Critical/Important; vier Lesarten durchgespielt (auch die des Betreibers, der
nicht noch einmal wiederherstellen will: die Seite lässt es nicht zu).
Bericht `task-3-re-review-2.md`. Hauptweg nicht eigens gemessen — Äquivalenz
zum Protokoll der Runde 1 vom Prüfer bestätigt (jedes Kommando, jede Ausgabe,
jeder Code steht dort).
Task 3: minor (deferred) M1: *After the check* — Fall ohne Anker steht nach
  dem Routine-Absatz; „start over … as verify-the-chain shows" führt auf
  `previously anchor > anchors.txt` und überschriebe die Datei, die eine
  Zeile davor „unchanged" bleiben soll. Für die Fixwelle, **nicht fallen
  lassen**.
Task 3: minor (deferred) M2: Ausweg nennt seine Eingangsbedingung nur über
  die Datei, nicht über den Restore (`:80`, `:107`, `:124`).
Task 3: minor (deferred) M3: Ausweg Schritt 1 schweigt, wenn die Prüfung
  gegen die ganze Datei 0 liefert oder nur `hash does not match`.
Task 3: minor (deferred) M4: „as it stood at the restore point" → „the last
  version from before that point".

Task 3: complete (commits 1df139c..7c936be, review clean after fix round 2)

## Rückstandsliste vor der Endprüfung

Was die Aufgabenprüfungen zurückgestellt haben, nummeriert; jede Zeile mit
dem, was ich dazu entschieden habe oder nicht entscheide.

1. **A1** — `_count_finding`-Docstring (`tests/test_verify.py`) zitiert
   `verify() -> []` als datierte Messung; lesbar als Gegenwart.
2. **A2** — Docstring von `_read_anchors` (`src/previously/cli.py`) ist kein
   Raw-String: `\r\n`, `\r`, `\n` sind zur Laufzeit Steuerzeichen. Muster:
   `src/previously/core/units.py:25`. → Fixwelle.
3. **A2, Ruling T2-d** — `the anchor file holds no anchor` kommt aus
   `core/anchor.py` und nennt eine Datei; der Kern bekommt Zeilen. →
   Fixwelle: quellenneutral (`the input holds no anchor`), Tests in
   `tests/test_anchor.py` und `tests/test_cli.py` folgen, `cli.md` und die
   Restore-Anleitung (`:126`) gegenlesen.
4. **A2** — `docs/reference/cli.md`: „a file that can't be read" ist für `-`
   unvollständig. → Fixwelle, ein Halbsatz.
5. **A2** — geschlossene Standardeingabe (`sys.stdin is None`) →
   `AttributeError`, Traceback, Code 1. Allgemein: jede unerwartete Ausnahme
   endet mit Code 1, dem Code eines Befunds — fail-closed, aber von einem
   Befund nicht zu unterscheiden. → Urteil der Endprüfung.
6. **A3, Gestaltungsfrage, vom Spec §3 festgelegt** — `anchor` druckt bei
   einem Befund die `FINDING`-Zeilen auf **stdout**; `>> anchors.txt`
   schreibt sie in die Ankerdatei. Die Anleitung sagt, dass man sie von Hand
   entfernt. → Meinung der Endprüfung; die Entscheidung ist die des Betreuers.
7. **A3, M1–M4** der zweiten Nachprüfung, alle auf
   `docs/how-to/restore-from-a-backup.md` (oben). → Fixwelle.
8. **A3, zur Kenntnis** — Spec §5.1 ist beim zweiten Restore-Fall
   unvollständig (setzt voraus, dass der Anker am Restore-Punkt der jüngste
   der Datei ist) und bleibt eingefroren (Ruling T3-e); die Seite gilt.
9. **Plan, zur Kenntnis** — der Test „jeder Unterparser hat einen
   Tabelleneintrag" kam bewusst nicht mit (Plan, *Was der Plan am Spec
   entscheidet*, Punkt 1; Spec §10 Punkt 11).

## Endprüfung — Dispatch

BASE `b0396b6`, HEAD `7c936be`. Opus. Zwei Pakete:
`final-review-code-b0396b6..7c936be.diff` (65 kB),
`final-review-docs-b0396b6..7c936be.diff` (52 kB). Auftrag
`final-review-dispatch.md`, Bericht → `final-review.md`. Neu gegenüber 1b:
der Prüfer fährt die Kommandos und beide Anleitungen von Hand gegen eine
Datenbank und legt das Protokoll in den Bericht.

## Endprüfung (Opus 5.5): With fixes

Bericht `final-review.md`. Keine Critical: kein Satz sagt mehr zu als die
Tabelle, jede „seen"-Zelle im Lauf gesehen. Sechs Tore grün außer
`linkcheck` (nicht gefahren, wie beauftragt). 265 Tests, 97.65 %. Sitzung
von Hand in fünf Teilen (Routine wie gedruckt, Fälschungen, beide
Restore-Fälle gegen eine zweite Datenbank, Betreiber-Eingaben, Container-Weg,
Nebenläufigkeit). Eine Mutation selbst gemessen (Zusicherung 6), Baum sauber.

Important:
- F1: „kein Anker auf gebrochener Kette" steht nur in `_cmd_anchor`;
  `Examination.tip` ist auch bei Befunden gesetzt → ein zweiter Einstieg
  beglaubigt den Bruch.
- F2: **gemessen 27 von 539 `examine`-Läufen mit Fehlbefund** `event has N
  rows, N-1 checked` unter gleichzeitigem Anhängen (READ COMMITTED,
  Spec §10 Punkt 2). Die dokumentierte Routine macht daraus einen Alarm.
Minor F3–F10. Rückstand: 1 fallen lassen (und der Ledger nannte die falsche
Datei: der Docstring steht in `core/verify.py:169`), 2/3/4/7 vor dem Merge,
5 später, 6 Betreuer, 8/9 zur Kenntnis. Sieben Zeilen *Declined to judge*.

Ruling E-1: **F2 wird in der Fixwelle behoben, als eigener Commit** —
`LogStore.snapshot()`, in `PostgresStorage` unter `REPEATABLE READ`,
`examine` nutzt es; `begin()`, `append` und der Arbeiter bleiben bei
`READ COMMITTED`. Geht über den Spec hinaus, der es in §10 Punkt 2 vertagt
hatte mit „der Anker fügt ihr nichts hinzu". Für den Code stimmt das, für den
Betrieb nicht: der Zweig macht den zeitgesteuerten `verify` zur Routine mit
„jeder Code ≠ 0 ist ein Alarm", und drei Sätze auf `hash-chain.md` (268,
281, 309) behaupten „same snapshot", was die Messung widerlegt. Vertagen
hieße, einen Fehlalarm zu dokumentieren — das erzieht dazu, den echten zu
übergehen. Kosten, falls falsch: ein Commit zurück, eine Protokoll-Methode.
Der Betreuer sieht es im PR einzeln.
Ruling E-2: **F1 → `Examination.anchor`** (Spitze nur ohne Befund), `tip`
bleibt; `_cmd_anchor` formatiert nur. Kosten, falls falsch: eine Property.
Ruling E-3: **F3 → je `id` eine Menge von Hashes** statt einer Liste; die
Routine erzeugt die Duplikate selbst. Zählung „n anchors hold" bleibt Zeilen.
Ruling E-4: **F4 (id ≤ 19 Ziffern), F5/F6 (hosting-neutral: kein Werkzeug
vorgeschrieben; der erste Anker wird mit `verify --anchors` geprüft, nicht
mit dem Auge), F7, F8, F9 (Zusicherung 7 messen) gehen mit.** F10 nicht.
Ruling E-5: **Rückstand 6 (`anchor`-Befunde auf stdout) bleibt, wie der Spec
es festlegt** — Entscheidung des Betreuers, mit der Empfehlung des Prüfers
(stderr) und meiner im PR. Rückstand 5 (unerwartete Ausnahme = Code 1) und 9
gehen in `index.md` für die nächste Stufe; Rückstand 1 fällt.
Ruling E-6, zu *Declined to judge*: alle sieben Zeilen angenommen, wie der
Prüfer sie abgelegt hat — Kommentar hinter dem Anker ist ein Fehler (Spec
§2); `anchor` allein prüft keine alten Anker (Spec §3, die Routine schützt
mit `&&`) → als offener Punkt in `index.md`; `-` am Terminal wartet;
überlappende Routinen hängen doppelt an (mit E-3 folgenlos); die
erklärenden Sätze der Restore-Anleitung bleiben; „72 … across 21 files" ist
eine datierte Messung vom 2026-10-03; `linkcheck` fährt die Fixwelle.

## Fixwelle — Dispatch

BASE `7c936be`. Umsetzer Opus, frisch. Auftrag `final-fix-dispatch.md`
(A: F2 zuerst und allein, F1, F3–F9; B: Rückstand 2, 3, 4, 7; C: Zahlen,
Zitatprüfung, Tutorial, sechs Tore, jeder Commit grün). Bericht →
`final-fix-report.md`.

## Fixwelle — Bericht

Commits `59072c4` (F2 allein: `snapshot()`, 267 Tests) und `059ccbd` (der
Rest, 270 Tests), Opus 5.5, DONE_WITH_CONCERNS. 97.56 %, sechs Tore grün an
`059ccbd` (auch `linkcheck`), Vale 22 Dateien; beide Commits grün auf
`pytest`, Tutorial-Testblock je aus echtem Lauf. 17 Dateien, Tree clean.
- Rennen: vorher 19 von 563 Läufen mit Befund, nachher 0 von 161 und 0 von
  116. Jede neue Assertion rot unter ihrer Mutation, grün danach.
- Bedenken: `59072c4` ließ `module-boundaries.md` veraltet (Methodenliste,
  „eight methods"); `059ccbd` zieht es nach — der F2-Commit steht bei der
  Doku nicht ganz allein.
- Beobachtung außerhalb des Auftrags: der Kommentar in `_cmd_log`
  (`cli.py` ~237–241) sagt, `show` lese Event und Units „in the same
  snapshot" — `show` liest unter `begin()`. Nicht angefasst. → Prüfer.
- F5 nennt nur `docker exec -i` und `docker compose exec -T` (die zwei
  gemessenen); `kubectl` ungemessen, weggelassen. → Prüfer.

Nachprüfung (Opus) dispatcht: Paket `review-7c936be..059ccbd.diff` (62 kB),
Auftrag `final-re-review-dispatch.md`, Bericht → `final-re-review.md`. Der
Prüfer fährt die Tore selbst.

## Nachprüfung der Fixwelle (Opus 5.5): Ready for the pull request — Yes

Bericht `final-re-review.md`. F1–F9, B2, B3, B4, B7 (M1–M4) alle ADDRESSED.
Fünf Tore selbst gefahren und grün (270 passed, 97.56 %), `linkcheck` laut
Bericht. F2 gegen die Datenbank gemessen: dieselbe Pool-Verbindung (PID 65)
kommt nach `snapshot()` mit `read committed`/`off` zurück; `verify` und
`anchor` gegen toten Server und unmigrierte Datenbank → ein Satz, Code 2.
Keine Critical/Important. Drei Minor und ein falscher Satz:
- Minor 1: „a read-only transaction never has a serialization conflict"
  ohne „at REPEATABLE READ" (`postgres.py`, `concurrency.md:48`).
- Minor 2: „the id has more than 19 digits" auch für ein Feld ohne Ziffern.
- Minor 3: kein Test hält die Fehlerübersetzung für `snapshot()`.
- `_cmd_log`-Kommentar (`cli.py:237–240`): „same snapshot" für `show` ist
  falsch; beobachtbar ist nichts, kleinster Fix ist der Kommentar.

Ruling E-7: **Die vier Reste werden jetzt geschlossen, nicht weitergetragen**
— drei sind Behauptungen, die mehr sagen, als stimmt, einer ist eine
Zusicherung ohne Test, und alle vier sind klein. Ein Nachzug an den Umsetzer
der Fixwelle (`final-fix-residuals-dispatch.md`), danach liest der Controller
den Diff selbst und fährt die sechs Tore; kein weiterer Prüfer für rund
vierzig Zeilen, deren Mutationen im Bericht stehen. Abweichung vom Ablauf
„eine Fixwelle, eine Nachprüfung": bewusst. Kosten, falls falsch: ein
ungeprüfter kleiner Commit im PR, den der Betreuer ohnehin liest.
Zu Minor 2: die Längenprüfung bleibt **vor** der Ziffernprüfung (kein langes
Feld gleich welcher Art kommt in einer Meldung zurück), der Satz wird für
jedes Feld wahr.

## Reste — Bericht und Prüfung durch den Controller

Commit `c2828b9` (Opus 5.5), DONE. 271 Tests (270 + der Buchstaben-Fall),
97.56 %. Bericht im Abschnitt `## Residuals after the re-review` von
`final-fix-report.md`. Mutationen: Längenprüfung entfernt → beide
5000-Zeichen-Fälle rot (Ziffern: `ValueError`; Buchstaben: die Meldung gibt
das ganze Feld zurück); `snapshot()` am Helfer vorbei → beide CLI-Fehlertests
rot (`OperationalError`, `ProgrammingError`); je grün nach dem Zurücknehmen.

Diff `059ccbd..c2828b9` vom Controller gelesen (sieben Dateien, außerhalb
des Tutorials 41 geänderte Zeilen):
- `concurrency.md` und der Docstring von `snapshot()` nennen die Stufe; der
  Docstring sagt dazu, was dieselbe PostgreSQL-Seite für `SERIALIZABLE` sagt.
- `anchor.py`: „longer than 19 characters", Prüfung weiter vor jedem Echo.
- `_cmd_log`-Kommentar: zwei Anweisungen, zwei Schnappschüsse; ein Zustand,
  weil Event und Units gemeinsam committen und nichts in `src` sie danach
  umschreibt.
- `tests/test_cli.py`: `verify` in beiden Fehlertests, Satzgleichheit mit
  `log`.
`grep "more than 19 digits\|_MAX_ID_DIGITS"` über `src tests docs README.md`:
leer.

**Die sechs Tore, vom Controller an `c2828b9` gefahren:**
- `uv run ruff check .` — `All checks passed!`
- `uv run ruff format --check .` — `50 files already formatted`
- `uv run pyright` — `0 errors, 0 warnings, 0 informations`
- `uv run lint-imports` — `Contracts: 4 kept, 0 broken.`
- `uv run pytest --cov --cov-report=term-missing` —
  `271 passed in 23.78s`, `Total coverage: 97.56%`
- `make -C docs html` — `The HTML pages are in _build/html.`;
  `make -C docs vale` — `✔ 0 errors, 0 warnings and 0 suggestions in 22
  files.`; `make -C docs linkcheck` — 0 Zeilen mit `broken` in `output.txt`.
`print`-Zahl: `Found 24 errors.`, `pyproject.toml` und der Docstring sagen
vierundzwanzig.

## Schluss

Endprüfung sauber nach einer Fixwelle und einem Nachzug. Zweig
`b0396b6..c2828b9`, 18 Commits (`git rev-list --count`). Was offen bleibt und was der Betreuer
entscheidet, steht in `index.md` des Protokolls unter
`docs/superpowers/sdd/2026-10-04-aeusserer-anker/`; dieses Hauptbuch wird
dorthin kopiert und danach nicht mehr geführt. Als Nächstes: Protokoll als
eigener Commit, Arbeitsverzeichnis löschen, Push, Pull-Request gegen `main`.
Der Merge ist die Abnahme.
