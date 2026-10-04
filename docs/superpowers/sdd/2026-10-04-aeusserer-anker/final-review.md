# Endprüfung — der äußere Anker, `b0396b6..7c936be`

Prüfer: Opus 5.5, 2026-10-04. In einem Durchgang über beide Pakete, danach
Spec (ganz), Plan (Global Constraints, Review Focus, Aufgabenköpfe), Ledger,
beide Mutationsprotokolle. Dateien an HEAD nachgelesen, wo ein Hunk
abgeschnitten war: keiner war es für ein Urteil. Eine Mutation im Baum
gemessen (unten), Baum danach sauber (`git status --short` leer). Container
`fr-anchor` und das Compose-Projekt `frtty` entfernt; kein Container läuft
mehr.

### Strengths

- **Die Zusage hält überall, wo ich sie gelesen habe.** README (Punkt und
  Grenzabsatz), `hash-chain.md` (Tabelle, Zusage, „closes two of the three up
  to the newest anchor"), beide Anleitungen, `cli.md`, Tutorial, Docstrings in
  `core/verify.py`, `core/anchor.py`, `contract/types.py`: kein Satz sagt mehr
  zu als die Tabelle. Die drei heiklen Punkte stehen ausdrücklich da:
  angehängtes Event von „contains" nicht gesehen, gelöschte Spitze über dem
  jüngsten Anker von keiner Prüfung gesehen (`restore…:35` „Whatever it should
  hold there and doesn't, this check doesn't see"), `--exact` meldet
  ehrliches Wachstum (`hash-chain.md` „Once a legitimate event arrives …
  exact reports that one too"). Die Grenze ist in
  `test_a_tip_deleted_above_the_newest_anchor_is_seen_by_neither_check`
  festgenagelt.
- **Ein Durchlauf, wirklich.** `pending` wird beim Vorbeikommen abgebaut, die
  Spitze ist die letzte gesehene Zeile, `_closing_findings` braucht keine
  Verbindung. Keine Abfrage je Anker; `verify()` mit unveränderter Signatur.
- **`_read_anchors` ist sauber geworden** (Ruling T2-a): Bytes, eine
  Dekodierung mit `utf-8-sig`, `StringIO(newline=None)`, Parser nach dem
  `try`. Von Hand bestätigt: BOM+CRLF, Leerzeilen, Verzeichnis, Nicht-UTF-8,
  leere Standardeingabe — je ein Satz, Code 2.
- **Die Restore-Anleitung nach zwei Fixrunden ist richtig**, und ich habe
  jeden ihrer Fälle gegen eine zweite Datenbank gespielt: jede Ausgabe und
  jeder Code wie die Seite sagt, einschließlich der zuerst genannten Grenze
  des Auswegs ohne Geschichte (ein zu früh gestoppter Replay besteht ihn).
  Ruling T3-f („Maßstab vom Ablageort, nicht vom Ergebnis") hält.
- **Die Zitatprüfung wächst mit**: drei Befundtexte gegen `core/verify.py`,
  Präfix `FINDING <id>` gehalten, lesbare Zusicherung statt `IndexError`.
- Zahlen in Kommentaren gemessen und datiert, Labels mit Plandatum, keine
  neue Suppression, kein `§` aus diesem Zweig, `Assisted-By` überall.

### Gates run

- `uv run ruff check .` — `All checks passed!`
- `uv run ruff format --check .` — `50 files already formatted`
- `uv run pyright` — `0 errors, 0 warnings, 0 informations`
- `uv run lint-imports` — `Contracts: 4 kept, 0 broken.`
- `uv run pytest --cov --cov-report=term-missing` — `============================= 265 passed in 22.42s =============================` (Gesamt 97.65 %, `cli.py`, `core/anchor.py`, `core/verify.py` je 100 %)
- `make -C docs html` — `The HTML pages are in _build/html.`
- `make -C docs vale` — `✔ 0 errors, 0 warnings and 0 suggestions in 22 files.`
- `make -C docs linkcheck` — **nicht gefahren** (Netz, laut Auftrag).

### Hands-on session

Frischer `postgres:17` (`fr-anchor`, Port 55432), zwei Datenbanken
(`previously` als Live, `restored` als Restore), Schema per `alembic upgrade
head`. Kommandos über `uv run --project <worktree> previously` aus dem
Scratchpad; `P` steht unten für `previously`. Exit-Code in eckigen Klammern,
stderr und stdout gemischt in Reihenfolge des Terminals.

**1. Routine, wie gedruckt, und Fälschungen**

```
### leeres Log
$ P anchor
the log is empty: nothing to anchor
[exit 0]
$ P anchor > anchors.txt; echo "anchor exit $?"; wc -l < anchors.txt
the log is empty: nothing to anchor
anchor exit 0
0
$ P verify --anchors anchors.txt
Error: the anchor file holds no anchor
[exit 2]
### Routine-Zeile beim ersten Mal, ohne Datei
$ P verify --anchors anchors.txt && P anchor >> anchors.txt
Error: cannot read the anchor file 'anchors.txt': No such file or directory
[exit 2]
### zwei Events, erster Anker wie die Anleitung sagt
$ P anchor > anchors.txt
[exit 0]
$ cat anchors.txt
2 4b2887e7a9544197e37279cb8af4f695ec8bb16e2a29a93a3fde06950e3ce3f4
$ P verify
no anchor given: verify attests that the log is unchanged, not that it is complete; see `previously anchor`
chain intact
[exit 0]
$ P verify --anchors anchors.txt
chain intact, 1 anchor holds
[exit 0]
$ P verify --anchors anchors.txt --exact
chain intact, 1 anchor holds, the tip is the newest anchor
[exit 0]
### Routine zweimal ohne neues Event, dann ein Event, Routine
$ P verify --anchors anchors.txt && P anchor >> anchors.txt
chain intact, 1 anchor holds
$ P verify --anchors anchors.txt && P anchor >> anchors.txt
chain intact, 2 anchors hold
$ P append … m3 …
3
$ P verify --anchors anchors.txt --exact
FINDING 3: the log continues past the newest anchor (2)
[exit 1]
$ P verify --anchors anchors.txt && P anchor >> anchors.txt
chain intact, 3 anchors hold
$ cat anchors.txt
2 4b2887e7…e3f4
2 4b2887e7…e3f4
2 4b2887e7…e3f4
3 2cb03645…bf29
$ P verify --anchors - < anchors.txt
chain intact, 4 anchors hold
$ cat anchors.txt | P verify --anchors - --exact
chain intact, 4 anchors hold, the tip is the newest anchor
$ P verify --anchors - < /dev/null
Error: the anchor file holds no anchor
[exit 2]
### Fälschung 1: Spitze (3, geankert) per SQL gelöscht
$ P verify
no anchor given: …
chain intact
[exit 0]
$ P verify --anchors anchors.txt
FINDING 3: anchored event is missing (the log ends at 2)
[exit 1]
$ P verify --anchors anchors.txt --exact
FINDING 3: anchored event is missing (the log ends at 2)
[exit 1]
$ P verify --anchors anchors.txt && P anchor >> anchors.txt
FINDING 3: anchored event is missing (the log ends at 2)
[exit 1]
$ P anchor                      # allein, nicht über die Routine
2 4b2887e7…e3f4
[exit 0]
### Fälschung 2: Hash des geankerten Events 2 überschrieben
$ P verify --anchors anchors.txt
FINDING 2: hash does not match the fields
FINDING 2: hash does not match the anchor
FINDING 2: hash does not match the anchor
FINDING 2: hash does not match the anchor
FINDING 3: anchored event is missing (the log ends at 2)
[exit 1]
$ P anchor
FINDING 2: hash does not match the fields
[exit 1]
$ P anchor >> anchors.txt; tail -3 anchors.txt
2 4b2887e7…e3f4
3 2cb03645…bf29
FINDING 2: hash does not match the fields
$ P verify --anchors anchors.txt
Error: anchor line 5: expected `<id> <hash>`, got 8 fields
[exit 2]
```

**2. Restore-Anleitung, beide Fälle** (Live: fünf Events, Routine nach jedem
der Events 1–4, Dateistand nach jedem Lauf als `hist-N.txt` aufbewahrt als
„Version im Ablageort"; `restored` per `pg_dump --data-only` befüllt, ältere
Punkte per `DELETE` oberhalb der Grenze nachgestellt)

```
$ cat -n anchors.txt
     1	1 08a2eb00…1d3e
     2	2 1c98c8ea…19d2
     3	3 1fc46d04…3994
     4	4 c1c704d8…7728
### Fall 1: letzter Stand (Spitze 5)
$ P verify --anchors anchors.txt
chain intact, 4 anchors hold
[exit 0]
$ P verify --anchors anchors.txt --exact
FINDING 5: the log continues past the newest anchor (4)
[exit 1]
### Fall 1, Replay vor dem jüngsten Anker stehen geblieben (Spitze 3)
$ P verify --anchors anchors.txt
FINDING 4: anchored event is missing (the log ends at 3)
[exit 1]
### Fall 2: absichtlich auf den Punkt von Anker 2, Datei aus dem Ablageort
$ cp hist-2.txt anchors-restored.txt
$ P verify --anchors anchors-restored.txt
chain intact, 2 anchors hold
[exit 0]
$ P verify --anchors anchors-restored.txt --exact
chain intact, 2 anchors hold, the tip is the newest anchor
[exit 0]
$ P verify --anchors anchors.txt
FINDING 3: anchored event is missing (the log ends at 2)
FINDING 4: anchored event is missing (the log ends at 2)
[exit 1]
### Fall 2, Replay zu früh (Spitze 1, gemeint 2), Datei aus dem Ablageort
$ P verify --anchors hist-2.txt
FINDING 2: anchored event is missing (the log ends at 1)
[exit 1]
### dasselbe über den Ausweg ohne Geschichte
$ P verify --anchors anchors.txt
FINDING 2: anchored event is missing (the log ends at 1)
FINDING 3: …   FINDING 4: …
[exit 1]
$ head -n 1 anchors.txt > anchors-restored.txt
$ P verify --anchors anchors-restored.txt --exact
chain intact, 1 anchor holds, the tip is the newest anchor
[exit 0]                       # die Grenze, die die Seite zuerst nennt
### Nach der Prüfung: Routine gegen anchors-restored.txt (Spitze 2), neues Event
$ P append … m6 …
3
$ P verify --anchors anchors-restored.txt && P anchor >> anchors-restored.txt
chain intact, 2 anchors hold
$ P verify --anchors anchors.txt
FINDING 3: hash does not match the anchor
FINDING 4: anchored event is missing (the log ends at 3)
[exit 1]
### Restore vor den ersten Anker (leeres Log)
$ P verify --anchors anchors.txt
FINDING 1: … (the log ends at 0)   … FINDING 4: … (the log ends at 0)
[exit 1]
$ P verify
no anchor given: …
chain intact
[exit 0]
```

**3. Eingaben eines Betreibers**

```
BOM + CRLF                         chain intact, 2 anchors hold        [0]
Leerzeile in der Mitte und am Ende chain intact, 2 anchors hold        [0]
umgekehrt + doppelt, --exact       FINDING 5: the log continues past the newest anchor (2)  [1]
id 0                               Error: anchor line 1: the id has to be a positive integer, got '0'   [2]
id -1                              Error: anchor line 1: the id has to be a positive integer, got '-1'  [2]
Hash in Großbuchstaben             chain intact, 1 anchor holds        [0]
Verzeichnis (/tmp)                 Error: cannot read the anchor file '/tmp': Is a directory  [2]
Anker 99 jenseits + zwei, die halten, --exact
                                   FINDING 99: anchored event is missing (the log ends at 5)  [1]
"1 <hash>  # taken monday"         Error: anchor line 1: expected `<id> <hash>`, got 5 fields  [2]
id mit 5000 Ziffern                ValueError: Exceeds the limit (4300 digits) …  Traceback  [1]
--anchors - mit geschlossenem stdin (<&-, direkt aus .venv/bin)
                                   AttributeError: 'NoneType' object has no attribute 'buffer'  [1]
verify --exact --anchors (ohne Wert)   argparse: expected one argument   [2]
anchor --anchors x                 argparse: unrecognized arguments     [2]
```

**4. Container-Weg** (für F5): `docker exec` ohne `-i` reicht keine
Standardeingabe durch (`echo abc | docker exec … wc -c` → `0`; mit `-i` →
`4`). `docker exec -t` mischt stderr in stdout (`o u t \r \n e r r \r \n`).
Docker Compose v5.6.0 schaltet ohne Terminal auf stdin von selbst kein TTY
zu und reicht eine Pipe auch ohne `-T` durch (gemessen) — der Cron-Fall mit
Compose geht also so, wie die Seite ihn zeigt.

**5. Nebenläufigkeit** (für F2): `examine` in einer Schleife, 20 s lang,
während ein zweiter Thread fortlaufend anhängt:

```
examine runs: 539, appends: 1421, runs with findings: 27
(Finding(event_id=0, reason='event has 2 rows, 1 checked — the rest is unreachable'),)
(Finding(event_id=0, reason='event has 6 rows, 5 checked — the rest is unreachable'),)
```

**Was daraus folgt.** Die Kommandos tun, was `cli.md` sagt, Zeile für Zeile.
Für den Menschen um drei Uhr nachts: jeder Befund nennt die `id`, und der
Rückgabecode trennt Befund (1) von Eingabefehler (2) zuverlässig — bis auf
zwei Wege, die mit einem Traceback auf 1 landen (F4, Rückstand 5). Was ein
Befund **nicht** nennt, ist die Zeile der Ankerdatei, aus der er kommt; bei
den Duplikaten, die die Routine selbst erzeugt, wird daraus eine Wiederholung
desselben Satzes (F3). Die Anleitungen lassen sich wörtlich befolgen; die
Bedingung für den ersten Anker („once the log holds at least one event")
stimmt mit dem Lauf. Zwei Dinge sah nur der Lauf: der Vergiftungsweg von
`anchor >> anchors.txt` endet bei Code 2 statt 1 (Rückstand 6), und ein
Fehlalarm unter gleichzeitigem Anhängen (F2).

### Issues

#### Critical (Must Fix)

Keine. Kein Satz verspricht mehr als die Tabelle; jede Fälschung, die die
Tabelle „seen" nennt, sah der Code im Lauf.

#### Important (Should Fix)

**F1 — `src/previously/cli.py:278–295`, `src/previously/core/verify.py:51–62`, `:278`.**
Die Regel „auf einer gebrochenen Kette entsteht kein Anker" (Spec §3: ein
Anker würde den Bruch beglaubigen) steht **nur** in `_cmd_anchor`.
`Examination.tip` wird auch bei Befunden gesetzt (`:278`, unbedingt), und der
Docstring von `Examination` sagt „an anchor printed from it describes exactly
the chain that was checked" — ohne die Bedingung. Ein MCP-Werkzeug, das
`examine(...).tip` zurückgibt, beglaubigt den Bruch, wenn sein Autor die
Regel nicht aus `cli.py` abschreibt. Das ist genau die Frage des Betreuers
(„was müsste ein zweiter Einstieg neu schreiben?"), und die Antwort ist eine
Sicherheitsregel, keine Formatierung. Alles andere in `cli.py` ist Lesen und
Formatieren (geprüft: Zählung `N`, Hinweis nur ohne Befund, Plural,
`--exact needs --anchors` — der Kern lehnt das selbst ab). **Fix:** der Kern
liefert den Anker, z. B. `Examination.anchor` (Property: `tip` nur ohne
Befunde, sonst `None`) oder `take_anchor(storage) -> Examination` mit dieser
Semantik; `_cmd_anchor` formatiert nur noch. `tip` bleibt für „the log ends
at" erhalten. Ein Kern-Test mit gebrochener Kette, gemessen rot gegen die
Mutation „Property gibt immer `tip`".

**F2 — `src/previously/core/verify.py:226–231` (Kommentar, nicht vom Zweig geändert) gegen `docs/how-to/verify-the-chain.md:50–55`.**
Gemessen: unter fortlaufendem Anhängen liefern 27 von 539 Läufen von
`examine` einen Fehlbefund `FINDING 0: event has N rows, N-1 checked — the
rest is unreachable`. Ursache ist die offene Frage aus Spec §10 Punkt 2:
`READ COMMITTED` gibt jeder Anweisung ihren eigenen Schnappschuss
(`storage/postgres.py:98`, `:461–467` sagt es selbst), und zwischen dem
leeren Lesen am Ende und `count_events` kann ein Commit liegen. Der Spec hat
das bewusst nicht angefasst, „der Anker fügt ihr nichts hinzu: er liest
nichts Zusätzliches". Das stimmt für den Code, nicht für den Betrieb: dieser
Zweig macht den **zeitgesteuerten** `verify` zur dokumentierten Routine und
sagt „Treat any exit code other than `0` as an alarm" — der Fehlalarm ist
jetzt die Erfahrung, die ein Betreiber mit dieser Routine macht, sobald
Konnektoren nebenher schreiben, und ein Fehlalarm, der sich beim zweiten Lauf
„erledigt", erzieht dazu, den echten zu übergehen. Der Kommentar an `:226`
(„only that way do all the reads see the same snapshot") ist dabei eine
falsche Behauptung im Baum. **Fix vor dem Merge, oder ein ausdrückliches
Ruling des Betreuers, ihn mit §10 Punkt 2 zu vertagen:** `examine` liest
unter `REPEATABLE READ` (eine Stelle, z. B. eine `begin`-Variante im Storage;
Test: der Rennlauf oben als deterministischer Test mit zwei Verbindungen ist
schwer, aber ein Test, der zwischen den Lesungen einer `REPEATABLE
READ`-Transaktion anhängt, geht), und der Kommentar sagt danach die Wahrheit.
Mindestens aber nennt die Anleitung den Fall.

#### Minor (Nice to Have)

**F3 — `src/previously/core/verify.py:224`, `docs/reference/cli.md:75`, `docs/how-to/verify-the-chain.md:57–58`.**
Die Routine hängt bei ruhigem Log dieselbe Zeile wieder an (dokumentiert),
und jede gleiche Zeile ergibt bei einer Fälschung ihren eigenen gleichen
Befund — im Lauf dreimal `FINDING 2: hash does not match the anchor`; bei
stündlicher Routine über ein ruhiges Wochenende Dutzende. Spec §2 nennt
Duplikate „harmlos"; für die Prüfung stimmt das, für die Ausgabe nicht. **Fix:**
je `id` eine Menge statt einer Liste (gleiche Hashes einmal, abweichende weiter
je einzeln); `cli.md:75` folgt. Alternativ hängt die Routine nur an, wenn sich
die Spitze geändert hat — das wäre eine längere Shell-Zeile und schlechter.

**F4 — `src/previously/core/anchor.py:46`, `:58`.**
Eine `id` mit mehr als 4300 Ziffern lässt `int()` mit `ValueError` scheitern:
Traceback, Code 1 — der Code eines Befunds. Der Kommentar an `:44–45`
begründet `isascii` gerade damit, dass ein unübersetzter `ValueError` nicht
durchrutschen soll. Kein realistischer Betreiber tippt das, aber eine
beschädigte Datei kann es enthalten. **Fix:** Länge der `id` begrenzen (z. B.
≤ 19 Ziffern, `bigint`) oder `ValueError` übersetzen; ein Parser-Fall dazu.

**F5 — `docs/how-to/verify-the-chain.md:41`, `:60–66`.**
Der Container-Weg ist nur als `previously verify --anchors - < anchors.txt`
gezeigt. Gemessen: `docker exec` ohne `-i` (und ebenso `kubectl exec` ohne
`-i`) reicht keine Eingabe durch → `Error: the anchor file holds no anchor`,
Code 2 — fail-closed, aber die Meldung führt in die falsche Richtung. Von Hand
am Terminal mit TTY mischt `docker exec -t` (und `docker compose exec` mit
Terminal) stderr in stdout: auf leerem Log landet `the log is empty: nothing
to anchor` in `anchors.txt`, und die Prüfung an `:41` („holds exactly one
line") **besteht**. **Fix:** die Container-Form ausschreiben
(`docker compose exec -T app previously …`, `kubectl exec -i …`), und `:41`
prüft „eine Zeile der Form `<id> <hash>`" statt „eine Zeile".

**F6 — `docs/how-to/verify-the-chain.md:32–58`.**
Die Seite verlangt den Ort außerhalb (`:32–33`), aber die Routine schreibt
`>> anchors.txt` lokal, und kein Schritt sagt, dass die Datei danach dorthin
muss (Push, Kopie) und vor dem nächsten Lauf von dort geholt wird. Spec §5.1
beschreibt genau das für kup6s („holt sie, prüft, ankert, schiebt sie
zurück"). Der Ablageort selbst ist bewusst offen (§10 Punkt 4); ein Satz,
dass die Routine zwischen Holen und Zurückschieben läuft, ist es nicht.

**F7 — `pyproject.toml:90`.**
Der Zweig hat den Kommentarblock neu umbrochen und erweitert, `(ruling T9-c)`
darin blieb nackt. `CLAUDE.md`: „Whoever touches one qualifies it." Das
Ruling stammt aus der Ausführung von Stufe 1a, deren Ledger verloren ist; die
Qualifizierung sagt also auch das. Der Grund steht schon daneben.

**F8 — `docs/tutorials/record-your-first-event.md:111`.**
Das Tutorial legt `anchors.txt` in die Wurzel des frischen Klons; `.gitignore`
kennt die Datei nicht, sie erscheint in `git status` und kann mitcommittet
werden — im selben Repository wie die Datenbank-Konfiguration, also genau am
falschen Ort. Ein Halbsatz („in a real deployment this file lives elsewhere,
see …") oder ein Pfad außerhalb des Klons.

**F9 — Spec §7/§9 Zeile 9, Mutationsprotokolle.**
§9 Zeile 9 verlangt eine gemessene Mutation für **jede** Zusicherung aus §7;
§7 selbst nennt nur vier Mutationen (für 1, 2, 3, 5), und genau die sind
gemessen. Für 6 und 7 hatte niemand gemessen. Ich habe 6 gemessen:
`if examination.findings: return 1` in `_cmd_anchor` entfernt →
`test_anchor_says_nothing_on_an_empty_log_and_refuses_a_broken_chain` rot
(`1 failed, 11 passed, 37 deselected`, die Ausgabe war `1 0000…0000`),
zurückgenommen, Kontrolle `12 passed`, `git status --short` leer. 7 (Hinweis
nur ohne Befund) bleibt ungemessen; aus dem Code gelesen würde `assert err ==
""` rot. Befund gegen den Spec (innerer Widerspruch §7/§9), nicht gegen die
Umsetzung; das Ausführungsprotokoll sollte festhalten, welche gemessen sind.

**F10 — `src/previously/core/verify.py:302`.**
Fehlt ein geankertes Event aus der **Mitte**, lautet der Befund
`anchored event is missing (the log ends at 5)` für `id` 3 — wörtlich wahr,
liest sich aber wie ein Widerspruch. Die Kette meldet daneben ihren eigenen
Bruch (Kommentar `:297–298`), der Mensch hat also den Hinweis. Kosmetisch;
`cli.md:83` erklärt „the log ends at" richtig.

### Deferred items

1. **`_count_finding`-Docstring** — **fallen lassen.** Er steht in
   `src/previously/core/verify.py:169`, nicht in `tests/test_verify.py` (der
   Ledger nennt die falsche Datei). „measured `verify() -> []`" ist als
   Messung markiert, Vergangenheit, und `verify()` existiert unverändert.
2. **`_read_anchors`-Docstring kein Raw-String** — **vor dem Merge** in der
   Fixwelle; ein Zeichen, `help()` zeigt sonst Steuerzeichen.
3. **„the anchor file holds no anchor" aus dem Kern** — **vor dem Merge.** Im
   Lauf gesehen: `--anchors - < /dev/null` meldet „anchor file"; mit F5 führt
   das den Container-Betreiber in die falsche Richtung. Ruling T2-d hält.
4. **`cli.md` „a file that can't be read"** — **vor dem Merge**, Halbsatz
   („or standard input that can't be read").
5. **Geschlossene Standardeingabe / Traceback = Code 1** — **später**, aber
   ins Protokoll. Gemessen: Traceback, Code 1. Der Fall `<&-` ist selten;
   allgemeiner betrifft es jeden unerwarteten Fehler (auch F4). Die saubere
   Lösung ist eine Entscheidung über `main` (ein letzter Handler, der auf 2
   abbildet und den Traceback auf stderr lässt) und gehört nicht in diese
   Fixwelle; F4 schließt den einen realistischen Weg im Parser.
6. **`anchor` druckt Befunde auf stdout** — **Meinung: später, Entscheidung
   des Betreuers.** Mit `&&` erreicht der Weg die Datei nur bei einem Rennen
   zwischen den zwei Kommandos oder beim ersten Anker; im Lauf gemessen ist
   das Ergebnis dann ein Eingabefehler (Code 2, „got 8 fields") statt des
   Befunds — fail-closed, aber die Alarmklasse stimmt nicht mehr. Meine
   Präferenz: `anchor` schreibt Befunde auf stderr, weil sein stdout ein
   Datenkanal in eine Datei ist, anders als der von `verify` (Abweichung vom
   Spec §3; die Seite gilt, das Protokoll vermerkt sie). Kein Merge-Hindernis.
7. **M1–M4 der zweiten Nachprüfung** — **M1 vor dem Merge** (`restore…:118`
   „start over … as verify-the-chain shows" führt wörtlich auf
   `previously anchor > anchors.txt` und überschreibt die Datei, die `:114`
   unverändert halten will; „in a new file" reicht nicht, die Datei braucht
   einen Namen). M2–M4 in derselben Fixwelle, je ein Satz.
8. **Spec §5.1 unvollständig** — **zur Kenntnis, Ruling T3-e hält.** Dazu
   kommen die zwei Spec-Befunde aus diesem Bericht (F9; §2 „harmlos" in F3;
   §6 „der Anker fügt ihr nichts hinzu" in F2) — ins `index.md` des
   Ausführungsprotokolls.
9. **Test „Unterparser ↔ Tabelle"** — **später**, wie im Plan entschieden.

Zum Abgleich §10 ↔ Ledger: §10 hat die fünfzehn Punkte (gezählt), und Punkt
11 ist der einzige, über den der Plan entschied. Was nach dem Einfrieren
offen blieb (Rückstand 5, 6, 9; F2–F6 hier), steht nicht im Spec und kann es
nicht — es gehört in `index.md` des Ausführungsprotokolls, wenn es unter
`docs/superpowers/sdd/2026-10-04-aeusserer-anker/` landet (das Verzeichnis
existiert an HEAD noch nicht).

### Declined to judge

- Ein Kommentar hinter dem Anker (`1 <hash>  # taken monday`) ist ein Fehler
  — Spec §2 entscheidet das ausdrücklich („ein drittes Feld"); die Meldung
  nennt Zeile und Feldzahl.
- `previously anchor` prüft keine alten Anker und druckt nach einer gelöschten
  Spitze die gekürzte Spitze, wenn man es allein ruft — Spec §3 so gewollt,
  die Routine mit `&&` schützt davor.
- `verify --anchors -` am interaktiven Terminal wartet auf Eingabe — übliches
  Unix-Verhalten.
- Zwei gleichzeitig laufende Routinen (überlappender Cron) hängen beide an —
  ergibt eine doppelte Zeile, harmlos bis auf F3; Sperren steht in keinem Spec.
- Erklärende Sätze in der Restore-Anleitung („Those findings are true …") —
  kurz und mit Verweis auf die Explanation; kein zweiter Quadrant, den ich
  abspalten würde.
- Die Zahl „72 paragraph references across 21 files" in `design-records.md`
  — nicht von diesem Zweig berührt, nicht nachgezählt.
- `linkcheck` — laut Auftrag nicht gefahren.

### Recommendations

Geprüfte Behauptungen (Auswahl, je mit Weg):
`print`-Zahl 24 (`ruff --select T201 … | grep -c` und `grep -c 'print('`,
beide 24) in `pyproject.toml` und `tests/test_docs_references.py` ✓;
„eight keys"/`main` bei 2 (`max-complexity = 1`) ✓; `_read_anchors` 4,
`_cmd_verify` 5, `_cmd_anchor` 4 ✓; Kette „stünde bei 10" ist als abgelesen
markiert, nicht gemessen — ehrlich; Tutorial `collected 265`/`265 passed`
(`--collect-only … | tail -1` → 265) ✓, Zahlen je Datei gegen die Sammlung
(19 Dateien, alle gleich) und die Prozente (Untergrenzen, z. B. 74/265 → 27 %)
nachgerechnet ✓; Tutorial-Hash `52a060a8734b` in `log` und `show` gleich ✓;
„fifteen" `§`-Zeilen an `b0396b6` und HEAD (15/15) ✓; „five" Berichte (5
Dateien unter `specs/`, fünf Zeilen im README, `design-records.md`) ✓;
„four standard-error sentences … in three blocks" (2+1+1) ✓; „Five events in
batches of two: anchor at 3 in the second batch, tip in the third" ✓;
`_read_anchors` „the parser runs after the `try`" ✓; Spec §10 „fünfzehn
Punkte" ✓.

Zitate: `grep -rnE '§|review focus|[Rr]uling ' src tests` — die vom Zweig
hinzugefügten Zeilen tragen nur „review focus N of the 2026-10-04
external-anchor plan" mit Grund daneben; kein `§` neu; keine Programmausgabe
mit Zitat. Ausnahme F7.

Commits: 15, englische Betreffs, je `Assisted-By:` (Opus 5.5 bzw. Fable 5.1),
kein `Co-Authored-By`, kein „Generated with".

Reihenfolge für die Fixwelle: F1, F2 (oder Ruling), Rückstand 2/3/4/7-M1,
dann F3–F8 nach Lust. F2 betrifft Code außerhalb des Ankers; wird er
vertagt, muss die Anleitung den Fehlalarm nennen, sonst lernt der Betreiber
es aus dem Alarm.

### Assessment

**Ready to merge? With fixes.**

Die Zusage ist nirgends überdehnt, die Prüfungen sehen im Lauf genau, was die
Tabelle sagt, und die Anleitungen lassen sich wörtlich befolgen. Zu beheben
sind die eine Sicherheitsregel, die nur in `cli.py` steht (F1) und die ein
zweiter Einstieg verlieren würde, und der gemessene Fehlalarm der jetzt
dokumentierten zeitgesteuerten Routine (F2) — beheben oder vom Betreuer
ausdrücklich vertagen lassen; dazu die kleinen Punkte 2, 3, 4 und M1 der
Rückstandsliste.
