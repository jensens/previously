# Offene Punkte, die die Ausführung gefunden hat

Vom Controller aus dem Protokoll (`progress.md`) zusammengetragen, für Aufgabe 8,
Schritt 6: sie gehen in die Landkarte, **neben** die vierzehn Punkte aus §12 des
Specs, jeder unter der Einheit, zu der er gehört. Jeder ist am Baum nachzulesen,
bevor er hingeschrieben wird — die Fundstelle steht dabei.

## Kette und Prüfung

1. **In v=1 ist an einem ganz getilgten Event nichts mehr über seine Einheiten
   bezeugt.** Zahl und `seq` der Grabstein-Zeilen prüft nichts; eine gelöschte
   oder hinzugefügte Zeile ist kein Befund. In v=2 fällt beides auf. Die Grenze
   steht auf `docs/explanation/erasure.md` und ist mit einem Test festgenagelt
   (`tests/test_verify.py`, `test_the_tombstone_rows_of_a_fully_erased_version_1_event_are_attested_by_nothing`).
   Wer sie schließt, dreht den Test bewusst um.
2. **`verify --blobs` hält die Referenzen aller Blobs im Speicher des Prozesses.**
   Im Docstring gesagt, nicht gemessen.

## Tilgung

3. **Die Weigerung „is a redaction" trifft jedes Event der Art `action`.** Heute
   ist jede Handlung eine Tilgung; mit der zweiten Art von Handlung ist der Satz
   falsch (`src/previously/core/redact.py`, der Kommentar daneben sagt es).
4. **Aufnehmen gegen Tilgen** (Spec §12 Punkt 2) ist jetzt auf
   `docs/explanation/concurrency.md` benannt und weiter nicht verhindert.
5. **`_catch_up_after` hört an der ersten Projektion auf, die scheitert**
   (`src/previously/cli.py`). Heute folgenlos: beide lesen dasselbe Log.

## Blobs und Speicher

6. **`pyrage` 1.4.0 kehrt beim Versiegeln eines kleinen Inhalts normal zurück,
   wenn der eine Schreibzugriff der Senke scheitert** (gemessen am 2026-10-05,
   12 Bytes; bei größerem Inhalt wirft es). Im Baum umgangen: `core/sealing.py`
   beobachtet Quelle und Senke selbst. Dem Projekt `pyrage` ist es nicht
   gemeldet.
7. **`s3transfer` hält den Fehler eines abgewiesenen Hochladens in Zyklen, samt
   der Verbindung.** Im Baum umgangen: `put` in `storage/s3.py` wirft den eigenen
   Fehler unverkettet. Nicht gemeldet.
8. **Die Lesefrist des S3-Clients (20 s) ist gegen keinen langsamen echten
   Speicher erprobt** — auch nicht der Fall, dass die Antwort auf einen Teil
   eines Hochladens länger braucht.
9. **Was bei Hetzner anders ist** (Spec §12 Punkt 11) hat seit der Ausführung
   Namen: ob der Speicher das Metadatum `key-id` so zurückgibt; was ein Leser
   sieht, während ein Objekt ersetzt wird (bei RustFS bricht sein Lesen ab);
   ob ein bedingtes Schreiben angenommen wird; ob Löschen ohne Version und ohne
   Löschmarke löscht.

## Betrieb

10. **Die Aufbewahrung der Sicherungen oder Kopien des Buckets ist Teil der
    Tilgungszusage**, wie die der Datenbank (Spec §4.5, nachgetragen am
    2026-10-05; `erasure.md`, `blobs.md`).
11. **Der Notfallweg mit dem Werkzeug `age`** ist bis zur Abnahme nicht gegangen
    (Abnahmebedingung 14).

## Tore und Werkzeuge

12. **Der Testlauf ist von rund 31 s auf rund 75 s gewachsen**: ein zweiter
    Container, und Tests, die wirklich hochladen. Die Zahl am Baum messen.
13. **Der Zitat-Test lässt hinter einem eingesetzten Wert am Satzende beliebigen
    Text zu** (`tests/test_docs_references.py`). Eine Verschärfung auf „kein
    Leerzeichen im eingesetzten Ende" bräche an Sätzen, die mit einem Grund
    enden.
14. **Drei Tests laufen nur unter Linux** und werden sonst übersprungen
    (`ru_maxrss`, `/proc`); zwei senken für die Dauer eines Kommandos die
    Dateigrößengrenze des Testprozesses.
15. **Der Test zum abgebrochenen Lesen verlässt sich darauf, dass RustFS das
    Senden einstellt, wenn das Objekt gelöscht wird.** An den ersten CI-Läufen
    beobachten.
