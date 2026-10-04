# Ausführungsprotokoll: der äußere Anker, 2026-10-04

> **Eingefrorene Arbeitsaufzeichnung, Stand 2026-10-04.**
> Die Dateien in diesem Verzeichnis werden nicht nachgezogen und sind
> **absichtlich unverändert**, so wie sie während der Ausführung entstanden
> sind. Eine Arbeitsaufzeichnung, die später glattgezogen wird, ist keine
> mehr.
> Die lebende Begründung steht in der Dokumentation unter `docs/`. Weicht
> etwas hier davon ab, gilt die Doku.

Diese Dateien halten fest, wie der Plan
[2026-10-04-aeusserer-anker](../../plans/2026-10-04-aeusserer-anker.md)
ausgeführt wurde: drei Aufgaben, je mit Auftrag (`task-N-brief.md`,
`task-N-dispatch.md`), Bericht, Prüfauftrag, Prüfbericht, Fixaufträgen und
Nachprüfungen als eigene Dateien; dazu die Endprüfung des ganzen Zweigs mit
einer Sitzung von Hand gegen eine Datenbank, die Fixwelle danach mit ihrer
Nachprüfung und einem Nachzug, und das Hauptbuch [`progress.md`](progress.md)
mit jeder Entscheidung, die unterwegs getroffen werden musste — zu finden
unter `Ruling`, von `P-1` bis `E-7`.

## Warum das hier liegt

Kommentare im Baum zitieren ein Label dieser Ausführung: `review focus N of
the 2026-10-04 external-anchor plan`, in `tests/test_anchor.py`,
`tests/test_verify.py` und `tests/test_cli.py`. Die Liste, auf die es zeigt,
steht im Plan unter *Review Focus*; was aus jedem Punkt wurde, steht hier im
Hauptbuch. Die Regel, ein Label mit seinem Plan zu nennen, hat diese
Ausführung auf „Review focus" ausgedehnt (Ruling T1-b): es ist je Plan
nummeriert wie ein Ruling, und ältere Tests tragen es noch nackt.

Ein `ruling …` dieser Ausführung zitiert der Baum **nicht**. Gemessen am
2026-10-04 mit der Erhebung, die `CLAUDE.md` unter *A ruling citation is
provenance* als Kommandozeile führt:

```
grep -rnioE 'ruling (P|T[0-9]+)-[a-z0-9]+' src tests migrations pyproject.toml .importlinter | sort -u
```

Sie findet dieselben vierzehn Labels wie vor diesem Zweig. Eines davon hat
der Zweig angefasst und dabei qualifiziert: `ruling T9-c` in `pyproject.toml`
sagt jetzt, dass es aus der Ausführung der Stufe 1a stammt, deren Hauptbuch
verloren ist.

Die Regel bleibt, dass **der Grund im Kommentar steht** und das Label nur die
Herkunft trägt.

## Was fehlt, und warum

Die `review-*.diff`- und `final-review-*.diff`-Pakete, die jeder Prüfer
gelesen hat, liegen nicht hier: sie sind aus `git diff` zwischen den im
Hauptbuch genannten Commits jederzeit wieder zu erzeugen.

Die vier Mutationen der Aufgabe 1 hat nicht der Umsetzer gemessen, sondern
der Controller (`task-1-mutations.md`): das Berechtigungssystem hatte dem
Umsetzer die erste als „Security Test Removal" verweigert, und eine
verweigerte Aktion wird nicht über einen zweiten Weg erledigt. Der Betreuer
hat das Messen im Baum danach ausdrücklich erlaubt; ab Aufgabe 2 haben die
Umsetzer selbst gemessen, und nichts wurde mehr verweigert.

Der Nachzug nach der Nachprüfung der Fixwelle (Commit `c2828b9`, vier kleine
Reste) hat keinen eigenen Prüfbericht. Der Controller hat den Diff gelesen
und die sechs Tore gefahren; das Hauptbuch hält beides unter *Reste* fest
(Ruling E-7).

Der Commit, der dieses Verzeichnis anlegt, steht nicht im Hauptbuch — er
konnte es nicht, weil das Hauptbuch vor ihm kopiert wurde. Es ist der erste
Commit auf dem Zweig nach `c2828b9`.

## Wo der eingefrorene Spec und der Baum auseinandergehen

Der Spec
[2026-10-04-aeusserer-anker](../../specs/2026-10-04-aeusserer-anker.md) fror
mit Aufgabe 3 ein; die Befunde danach gingen in den Baum und in die Seiten,
nicht in ihn. Wo beide sich widersprechen, gilt die Seite (`CLAUDE.md`). Das
sind die Stellen:

- **§5.1, der zweite Restore-Fall.** Der Spec lässt einen Restore „auf einen
  festen Punkt" mit `--exact` gegen die Ankerdatei prüfen und setzt dabei
  stillschweigend voraus, dass der Anker dieses Punkts der jüngste der Datei
  ist. Die Routine hängt aber laufend Anker an. Die Anleitung
  `docs/how-to/restore-from-a-backup.md` prüft gegen die Ankerdatei, **wie
  sie am gemeinten Restore-Punkt stand**, und nimmt diesen Stand vom
  Ablageort der Datei, nicht aus der wiederhergestellten Datenbank (Rulings
  T3-c und T3-f; T3-c hatte den Schnitt zuerst aus dem Ergebnis abgeleitet,
  das er prüfen sollte, und die Nachprüfung hat es gefunden).
- **§6, „der Anker fügt ihr nichts hinzu".** Der Spec ließ die Frage, unter
  welcher Isolationsstufe `verify` liest, in §10 Punkt 2 offen, mit der
  Begründung, der Anker lese nichts Zusätzliches. Die Endprüfung hat unter
  gleichzeitigem Anhängen 27 Fehlbefunde in 539 Läufen gemessen. Seit dem
  Commit `59072c4` liest `examine` in einem Schnappschuss
  (`LogStore.snapshot()`, `REPEATABLE READ`, nur lesend); §10 Punkt 2 ist
  damit für `examine` erledigt und steht im Spec noch als offen (Ruling E-1).
- **§2, Duplikate sind „harmlos".** Für die Prüfung ja; für die Ausgabe gab
  jede gleiche Zeile ihren eigenen gleichen Befund, und die Routine erzeugt
  gleiche Zeilen selbst, wenn kein Event dazukam. `examine` vergleicht je
  `id` jeden Hash einmal (Ruling E-3).
- **§3, wo die Regel „kein Anker auf gebrochener Kette" steht.** Der Spec
  beschreibt sie am Kommando. Sie steht jetzt im Kern, als
  `Examination.anchor`, damit ein zweiter Einstieg sie nicht abschreiben muss
  (Ruling E-2).
- **§2, die Meldung für eine Eingabe ohne Anker** nennt keine Datei mehr
  (`the input holds no anchor`): der Kern bekommt Zeilen (Ruling T2-d). Und
  eine `id` ist höchstens 19 Zeichen lang; der Spec nennt keine Grenze.
- **§7 und §9 Zeile 9** widersprechen sich im Spec selbst: §9 verlangt für
  jede Zusicherung eine gemessene Mutation, §7 nennt vier. Der Stand steht im
  nächsten Abschnitt.

## Welche Zusicherungen gemessen sind

Je Zusicherung aus Spec §7, ob eine Mutation gemessen ist und wo es steht:

| Zusicherung | gemessen | wo |
|---|---|---|
| 1 gelöschte Spitze | ja, Controller an `11de3f6` (M2) | `task-1-mutations.md` |
| 2 Umschreiben unter dem Anker | ja, ebenda (M1) | `task-1-mutations.md` |
| 3 gefälschtes Anhängen | ja, ebenda (M3) | `task-1-mutations.md` |
| 4 die Grenze über dem jüngsten Anker | keine Mutation möglich: der Test nagelt fest, dass **keine** Prüfung sie sieht | `tests/test_verify.py` |
| 5 fehlerhafte Datei | ja, ebenda (M4), und für die Standardeingabe in Aufgabe 2 | `task-1-mutations.md`, `task-2-report.md` |
| 6 `anchor` auf gebrochener Kette | ja, Endprüfung; nach Ruling E-2 erneut in der Fixwelle | `final-review.md` F9, `final-fix-report.md` F1 |
| 7 Hinweis nur ohne Befund | ja, Fixwelle | `final-fix-report.md` F9 |
| 8 `parse_anchors` und `format_anchor` rein | **nein**, keine eigene Mutation; die Tests stehen in `tests/test_anchor.py` | — |
| 9 Zitate der Reference | ja, Umsetzer der Aufgabe 2, vier Mutationen und eine Kontrolle | `task-2-report.md` |

Dazu, über den Spec hinaus und je mit Mutation: die Standardeingabe wird
gelesen wie eine Datei (`task-2-report.md`, Fixrunde 1); ein Schnappschuss
für `examine` (`final-fix-report.md` F2); ein Befund je gleicher Zeile (F3);
die Länge der `id` (F4 und Nachzug); die Fehlerübersetzung unter `snapshot()`
(Nachzug).

## Das Rennen, zum Nachmessen

`docs/explanation/hash-chain.md` und der Docstring von `snapshot()` nennen
„27 of 539" als Messung vom 2026-10-04. Das ist das Skript der Endprüfung; es
braucht eine migrierte Wegwerf-Datenbank unter dem DSN und läuft zwanzig
Sekunden. Am Stand vor `59072c4` meldet es Läufe mit Befund (Endprüfung: 27
von 539; Umsetzer der Fixwelle: 19 von 563), danach keinen (0 von 161 und 0
von 116 — weniger Läufe, weil dieselbe Datenbank über die Läufe wuchs und
jeder Lauf das ganze Log abgeht).

```python
"""Does examine report a false finding while appends run concurrently?"""

import threading
import time
from datetime import UTC, datetime

from previously.contract.types import Evidence, RawEvent
from previously.core.append import append
from previously.core.units import split_plaintext
from previously.core.verify import examine
from previously.storage.postgres import from_dsn

DSN = "postgresql+psycopg://previously:previously@localhost:55432/restored"
storage = from_dsn(DSN)
stop = False
n = 0


def writer() -> None:
    global n
    while not stop:
        n += 1
        ev = RawEvent(
            source="race",
            external_id=f"r{time.time_ns()}",
            occurred_at=datetime.now(UTC),
            evidence=Evidence.RECOLLECTION,
            units=split_plaintext(f"text {n}"),
            payload={"text": f"text {n}"},
        )
        append(storage, [ev], recorded_at=datetime.now(UTC))


t = threading.Thread(target=writer)
t.start()
runs = 0
false = []
deadline = time.time() + 20
while time.time() < deadline:
    ex = examine(storage)
    runs += 1
    if ex.findings:
        false.append(ex.findings)
stop = True
t.join()
print(f"examine runs: {runs}, appends: {n}, runs with findings: {len(false)}")
for f in false[:3]:
    print(f)
```

## Was diese Ausführung gelehrt hat

- **Code im Plan wird auf jedem Weg ausgeführt, den er hat — messen genügt
  nicht.** Zweimal gab der Plan einen Rumpf wörtlich vor, der falsch war:
  `examine` riss die Komplexitätsgrenze (ungemessen), und `_read_anchors`
  kehrte für `-` vor dem `try` zurück, sodass Bytes, die kein UTF-8 sind, mit
  Traceback und Rückgabecode 1 endeten — dem Code eines Befunds. Beim zweiten
  Mal war die Komplexität gemessen; das Verhalten auf der Standardeingabe
  nicht.
- **Eine Prüfung darf ihren Maßstab nicht aus dem nehmen, was sie prüft.**
  Die Restore-Anleitung schnitt die Ankerdatei an der Spitze des
  wiederhergestellten Logs. Gegen eine so geschnittene Datei kann kein Anker
  fehlen; ein Replay, das zu früh stehen blieb, ging als der gemeinte frühere
  Punkt durch. Das Ruling dazu kam vom Controller, und es las sich wie eine
  Lösung.
- **Benutzen findet, was Lesen nicht findet.** Drei Aufgabenprüfungen haben
  jede Zeile gegen den Code gehalten. Den Fehlalarm unter gleichzeitigem
  Anhängen, den vergifteten Weg von `anchor >> anchors.txt` und den
  Container-Aufruf, der keine Standardeingabe durchreicht, hat erst die
  Endprüfung gesehen — weil ihr Auftrag war, die Kommandos zu fahren.
  `CLAUDE.md` sagt es für jede Stufe („Running the thing by hand surfaces
  what reading it does not"); für eine Prüfung gilt es genauso.
- **Die Frage nach dem Betrieb findet die Löcher.** Beide Lücken in der
  Restore-Logik — im Spec vor der Ausführung, in der Anleitung während ihr —
  kamen aus der Frage, was ein Betreiber mit einer wiederhergestellten
  Datenbank und einer Ankerdatei wirklich in der Hand hat.
- **„Eine Transaktion" ist unter `READ COMMITTED` nicht „ein Zeitpunkt"** —
  das Protokoll der Stufe 1b hatte es für die Rückstandszeile gelernt und für
  `verify` als Frage weitergegeben. Hier ist die Antwort, mit einer Messung:
  es war ein Fehlalarm, kein Schönheitsfehler im Kommentar.

## Was der Betreuer entscheidet

- **`previously anchor` druckt bei einem Befund die `FINDING`-Zeilen auf die
  Standardausgabe** (Spec §3). Mit `>> anchors.txt` landen sie in der
  Ankerdatei; der nächste Lauf endet dann mit Rückgabecode 2 (Eingabefehler)
  statt 1 (Befund). Die Anleitung sagt, dass man die Zeilen von Hand
  entfernt. Endprüfung und Controller empfehlen beide, dass `anchor` Befunde
  auf die Standardfehlerausgabe schreibt: seine Standardausgabe ist ein
  Datenkanal in eine Datei. Das weicht vom eingefrorenen Spec ab und ist
  deshalb nicht in der Fixwelle (Ruling E-5).
- **Der Schnappschuss für `examine`** (Ruling E-1) geht über den Spec hinaus
  und steht deshalb als eigener Commit im Zweig, `59072c4`.

## Was in die nächste Stufe geht

Spec §10 ist eingefroren und trägt nichts mehr auf; das hier ist die Liste,
die der nächste Spec übernimmt, zusätzlich zu den fünfzehn Punkten dort (von
denen Punkt 2 für `examine` erledigt ist):

- **Eine unerwartete Ausnahme endet mit Rückgabecode 1, dem Code eines
  Befunds.** Fail-closed, aber von einem Befund nicht zu unterscheiden.
  Gemessen für eine geschlossene Standardeingabe (`--anchors - <&-`). Die
  saubere Lösung ist eine Entscheidung über `main`, nicht über einen
  einzelnen Weg.
- **`previously anchor` allein prüft keine alten Anker.** Nach einer
  gelöschten Spitze druckt es die gekürzte Spitze; nur die Routine mit `&&`
  schützt davor. Vom Spec so gewollt; ob `anchor` eine Ankerdatei annehmen
  soll, ist offen.
- **Ein Befund nennt die `id`, nicht die Zeile der Ankerdatei**, aus der er
  kommt.
- **`anchored event is missing (the log ends at 5)` für ein Event aus der
  Mitte** ist wörtlich wahr und liest sich wie ein Widerspruch; die Kette
  meldet daneben ihren eigenen Bruch.
- **Der Container-Weg ist für `kubectl exec` ungemessen.** Die Anleitung
  nennt, was durchgereicht werden muss und was nicht zugeteilt werden darf,
  und als Beispiele die zwei gemessenen Aufrufe.
- **`show` liest Event und Units in zwei Anweisungen unter `READ
  COMMITTED`.** Beobachtbar ist davon nichts, solange nichts ein Event nach
  dem Commit umschreibt; der Kommentar in `_cmd_log` sagt das jetzt. Kommt
  die Löschung am Tombstone-Saum, gilt die Begründung nicht mehr.
- **Zwei gleichzeitig laufende Routinen** hängen beide an; die doppelte Zeile
  ist seit Ruling E-3 folgenlos. Eine Sperre steht in keinem Spec.
