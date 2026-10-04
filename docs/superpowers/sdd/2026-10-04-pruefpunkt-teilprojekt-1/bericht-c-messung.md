# Bericht C — Was die Projektionsmechanik kostet, gemessen

Gemessen am 2026-10-04, 17:30–18:42 (MESZ), gegen den Stand `2bc42d4` des Worktrees `pruefpunkt-teilprojekt-1`.
Im Worktree wurde nichts verändert außer dieser Datei.
Die Änderungen, die `git status` dort zeigt (`M CLAUDE.md`, `?? docs/superpowers/landkarte.md`, `?? docs/superpowers/sdd/2026-10-04-pruefpunkt-teilprojekt-1/`), stammen nicht von mir.

**Die Größe 1.000.000 wurde nicht erreicht.**
Das Laden lief mit 700–870 Events/s; bis 700.000 Events kamen 969 s reine `append`-Zeit zusammen (gut 16 Minuten).
Bei der zuletzt gemessenen Rate von 710 Events/s hätten die restlichen 300.000 Events noch einmal etwa 7 Minuten gekostet, zusammen also etwa 23 Minuten.
Das liegt deutlich über den „etwa fünfzehn Minuten“ des Auftrags, also habe ich bei **700.000** aufgehört.
Die drei gemessenen Größen sind 10.000, 100.000 und 700.000.

## Maschine und Aufbau

- CPU: 11th Gen Intel Core i7-11370H @ 3.30GHz, 4 Kerne, 8 Threads (`lscpu`), max. 4,8 GHz.
- RAM: 62 GiB, kein Swap (`free -h`); zu Beginn waren 31 GiB verfügbar.
- Platten: `nvme0n1` Samsung SSD 980 PRO 1TB, `nvme1n1` Samsung SSD 970 EVO Plus 2TB, beide `ROTA 0` (`lsblk -d -o NAME,ROTA`). Docker 29.8.2, `overlay2`, Root `/var/lib/docker` auf `/dev/mapper/system-root`.
- **Kein ruhiger Rechner.** Es ist ein Laptop mit laufender Desktop-Sitzung. Die Load Average lag während der Messungen zwischen 1,3 und 8 (`uptime` steht in den Rohausgaben). Um 18:07 lief ein Firefox-Content-Prozess (PID 2833744) mit 92 % CPU neben der Messung (`top -b -n1`). Daneben lief der fremde Container `development-postgres-1` auf Port 5433. Streuungen über ein Viertel unten haben hier ihre wahrscheinlichste Ursache.
- PostgreSQL: `postgres:17` → `PostgreSQL 17.9 (Debian 17.9-1.pgdg13+1)`, Standardkonfiguration, nichts verändert: `shared_buffers=128MB`, `max_wal_size=1024MB`, `work_mem=4MB`, `synchronous_commit=on`, `checkpoint_timeout=300s`.
- Container: `docker run -d --name previously-messung-c -p 55432:5432 -e POSTGRES_USER=previously -e POSTGRES_PASSWORD=previously -e POSTGRES_DB=previously postgres:17`, Schema mit `PREVIOUSLY_DSN=postgresql+psycopg://previously:previously@localhost:55432/previously uv run alembic upgrade head` (0001_log, 0002_projections). **Am Ende mit `docker rm -f previously-messung-c` entfernt**; `docker ps -a --filter name=previously-messung-c` danach leer.
- Python 3.14.3, SQLAlchemy 2.1.2, psycopg 3.3.6 aus der `.venv` des Worktrees (über `uv run`, nie `--isolated`).

### Die Daten

Erzeugt von `load.py` (unten), deterministisch: Event `i` kommt aus `random.Random(i)`, so dass schrittweises Laden dasselbe Log ergibt wie ein Durchgang.

- Vier Quellen: `mail` 70 %, `chat` 15 %, `transcript` 10 %, `notes` 5 %.
- Mails: Anrede, 1–7 Absätze mit je 1–6 Sätzen, in 40 % ein zitierter Antwortblock aus `> `-Zeilen, Signatur; mit CRLF-Zeilenenden wie nach RFC 5322. Chats 1–3 kurze Absätze, Transkripte 8–40 Absätze, Notizen 1–5.
- Zerlegt mit dem projekteigenen `split_plaintext`. Im Mittel 7,3 Units und 1,5 KB Text pro Event (10.000 Events: 73.631 Units, 15,1 MB Text).
- `payload={"text": text}`, also so wie `previously append` (`_cmd_append`) es baut. Der Text steht damit zweimal im Log, einmal im `payload` und einmal in den Units, und ein drittes Mal in `p_chronicle`.
- `occurred_at` läuft über fünf Jahre ab 2021-10-01, linear im Index, bezogen auf geplante 1.000.000 Events, mit ±3 Tagen Zufallsversatz. Bei 700.000 deckt das Log also etwa 3,5 Jahre ab, und die Events kommen nicht streng zeitlich geordnet an.
- `evidence`: `verbatim`, nur bei `notes` ist es `recollection`.

### Batchgröße beim Laden

Was ein Batch ist, steht in `append` (`src/previously/core/append.py`).
Ein Aufruf ist **eine Transaktion**: einmal `tip` lesen, dann pro Event ein `lookup` auf `source_key`, ein `INSERT` in `event`, ein `INSERT` mit executemany in `unit` und ein `INSERT` in `source_key`, am Ende der Commit.
`MAX_BATCH = 500` ist die Obergrenze.
Fest pro Batch sind also nur das `tip`-Lesen und der Commit mit seinem WAL-Flush; alles andere fällt pro Event an.

Gemessen in einer eigenen Datenbank `batchprobe` (später gelöscht), je 2.000 Events, jede Größe zweimal:

| Batch | Events/s, Lauf 1 | Events/s, Lauf 2 |
|---|---|---|
| 1 | 198 | 190 |
| 50 | 786 | 661 |
| 500 | 798 | 801 |

Ab etwa 50 ist der Commit amortisiert, darüber zählen nur noch die vier Anweisungen pro Event.
Ich habe **500** genommen: Das ist das Maximum, das `append` zulässt, und ein Import-Konnektor würde es so nutzen.
Zwischen den beiden Läufen mit Batch 50 liegen 19 %; das erkläre ich mit der Last auf dem Rechner, ohne es belegt zu haben.

## Ergebnisse

Alle Zeiten sind Wanduhrzeit und enthalten den Prozessstart, weil sie Läufe des Konsolenskripts `.venv/bin/previously` unter `/usr/bin/time -v` sind (Peak-RSS kommt aus `time -v`).
Die Werte für „Laden“ und „Neubau“ unten gehören zur jeweiligen Größe; Neubau, Prüfung und Lesen liefen auf genau 10.000, 100.000 bzw. 700.000 Events.
Jede Zelle führt alle drei Läufe auf, den Median **fett**.

| Größe | Laden (Events/s) | Unit-Zeilen | Neubau (s) | Neubau (Events/s, Median) | Neubau Peak-RSS (MiB) | Nachziehen von 1.000 (s) | Kettenprüfung (s) | Prüfung Peak-RSS (MiB) | `chronicle` (s) | `chronicle` mit Fenster (s) | `stats` (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 10.000 | 871 | 73.631 | 3,77 / 3,40 / 3,77 (**3,77**) | 2.650 | 91 / 96 / 97 | 0,65 / 0,63 / 0,60 (**0,63**) | 1,53 / 1,49 / 1,52 (**1,52**) | 99,6 | 0,270 / 0,273 / 0,277 | 0,273 / 0,285 / 0,282 | 0,284 / 0,351 / 0,277 |
| 100.000 | 800 | 734.303 | 38,9 / 38,8 / 42,2 (**38,9**) | 2.570 | 107 / 106 / 105 | 0,61 / 0,67 / 0,68 (**0,67**) | 12,5 / 12,5 / 12,4 (**12,5**) | 107,5 | 0,266 / 0,270 / 0,273 | 0,284 / 0,274 / 0,283 | 0,270 / 0,274 / 0,268 |
| 700.000 | 710 | 5.137.856 | 415,8 / 311,6 / 388,0 (**388,0**) | 1.800 | 107 / 107 / 108 | 0,71 / 0,77 / 0,74 (**0,74**) | 88,8 / 93,7 / 95,5 (**93,7**) | 111,3 | 0,270 / 0,275 / 0,292 | 0,272 / 0,267 / 0,288 | 0,283 / 0,302 / 0,306 |

Erläuterungen zu den Spalten:

- **Laden** ist die Rate des Abschnitts, der die Größe erreicht hat: 1–10.000, 13.001–100.000 und 103.001–700.000; dazwischen lagen jeweils 3.000 Events aus dem Nachziehen. Gezählt ist nur die Zeit in `append`; Erzeugen und `split_plaintext` sind getrennt gemessen (0,6 s, 5,7 s, 41,9 s). Die 100.000er-Scheiben bis 700.000 brauchten 134,5 / 128,0 / 133,4 / 137,7 / 159,9 s und für die letzten 97.000 Events 147 s. Das Laden wird also mit wachsendem Log langsamer, von 871 auf 710 Events/s, aber nicht dramatisch. Peak-RSS des Ladeprozesses: 64–65 MiB.
- **Neubau** heißt: `TRUNCATE p_chronicle, p_source_stats; DELETE FROM projection_state; CHECKPOINT` (das ist Aufbau und nicht gemessen), danach gemessen `previously project`. Der Worker findet keinen Zustand und baut beide Projektionen aus dem ganzen Log, in Batches zu 500 Events.
- **Nachziehen**: `load.py` hängt 1.000 Events an (nicht gemessen), dann wird `previously project` gemessen. Zum Vergleich der Leerlauf, also `previously project` ohne neue Events: 0,278 s, 0,269 s, 0,284 s.
- **Kettenprüfung**: `previously verify` ohne Anker; Ausgabe jedes Mal `chain intact`.
- **Lesen**: `chronicle` mit `--limit 50` (Standard) gab 50 Zeilen aus, `stats` 4 Zeilen. `chronicle` mit Fenster bekam `--since` als Mitte zwischen `min(occurred_at)` und `max(occurred_at)` und `--until` einen Tag später; in diesem Fenster lagen 4.195, 4.146 bzw. 4.013 Chronik-Zeilen, ausgegeben wurden 50. Die Tabelle zeigt die Läufe über `.venv/bin/previously`.
- **Prozessstart**: `uv run previously --help` brauchte 0,21–0,25 s, `.venv/bin/previously --help` 0,195–0,212 s, bei 44 MiB RSS. `cli.py` importiert `storage.postgres` und damit SQLAlchemy schon auf Modulebene, so dass `--help` den vollen Importaufwand enthält. Ein Leseaufruf dauert also rund 0,27–0,30 s, davon sind **etwa 0,20 s Start** und 0,07–0,09 s eigentliches Lesen, und das bei allen drei Größen gleich. `uv run` kostet gegenüber dem direkten Aufruf zusätzlich 0,01–0,03 s (alle Werte unten in den Rohausgaben).
- Ein vierter Prüflauf bei 700.000, neben dem `pg_stat_activity` jede Sekunde abgefragt wurde, brauchte 111,6 s bei 113,9 MiB.

### Wie lange die Transaktion der Kettenprüfung offen steht

`examine` liest in **einer** `REPEATABLE READ`-Transaktion (`storage.snapshot()`).
Beim vierten Prüflauf bei 700.000 lieferte `xactpoll.py` 111 Abtastungen hintereinander für dieselbe Backend-PID 386, mit `xact_age` von `0:00:00.996` bis `0:01:51.12`.
Der Zustand war 100-mal `idle in transaction` und 11-mal `active`: Die meiste Zeit hält die Transaktion den Snapshot offen, während Python hasht, und die Datenbank wartet.
**Bei 700.000 Events steht die Transaktion also 89–112 s offen**, so lange wie die ganze Prüfung.
Das ist die Zeit, die eine geplante Anker-Routine bei jedem Anker eine `xmin`-Grenze festhält.

### Speicher

**Der Speicher bleibt flach.**
Beim Neubau lag der Peak bei 91–97 MiB für 10.000 Events, 105–107 MiB für 100.000 und 107–108 MiB für 700.000; beim Neubau während laufender Anhänge (unten) waren es 110 MiB.
Bei der Prüfung waren es 99,6 MiB, 107 MiB und 111 MiB.
Ein Lesekommando braucht 59–60 MiB, `--help` 44 MiB.
Von 100.000 auf 700.000 (Faktor 7) wächst der Peak um 1–4 MiB.
Der Sprung von 10.000 auf 100.000 um etwa 10 MiB ist kein Wachstum mit dem Log; er bleibt danach stehen.
Die Server-seitigen Cursor (`stream_results=True, yield_per=100` in `read`) und die Batches zu 500 bzw. 1.000 Events halten, was die Architekturaufzeichnung verlangt: Ein Neubau zieht das Log nicht in den Speicher.

### Größe der Tabellen

| Größe | `event` | `unit` | `source_key` | `p_chronicle` |
|---|---|---|---|---|
| 10.000 | 15 MB | 20 MB | 1,6 MB | 28 MB |
| 100.000 | 153 MB | 197 MB | 15 MB | 278 MB |
| 700.000 | 1.068 MB | 1.380 MB | 103 MB | 1.947 MB |

Am Ende umfasste die Datenbank mit 710.577 Events 4.572 MB, bei etwa 1,05 GB Rohtext.

## Wie die Kosten wachsen

Die Kosten pro Event aus den Medianen:

| | 10.000 | 100.000 | 700.000 |
|---|---|---|---|
| Laden (ms/Event) | 1,15 | 1,25 | 1,41 |
| Neubau (ms/Event) | 0,377 | 0,389 | 0,554 (Spanne 0,445–0,594) |
| Kettenprüfung (ms/Event) | 0,152 | 0,125 | 0,134 |
| Nachziehen von 1.000 (s) | 0,63 | 0,67 | 0,74 |
| Lesen (s) | ≈ 0,28 | ≈ 0,27 | ≈ 0,28 |

- **Die Kettenprüfung wächst linear.** Pro Event ändert sich zwischen 100.000 und 700.000 kaum etwas; bei 10.000 wiegt der Start von 0,2 s mit.
- **Lesen wächst nicht**, denn beide Lesepfade gehen über einen Index mit `LIMIT`.
- **Nachziehen** wächst kaum: Von 0,63 auf 0,74 s, und davon sind etwa 0,27 s Start und Zustandsabfrage (der Leerlauf).
- **Beim Neubau** ist pro Event zwischen 100.000 und 700.000 ein Anstieg um den Faktor 1,4 gemessen. **Diesen Anstieg kann ich nicht dem Datenvolumen zuschreiben.** Die reine Python-Ableitung `chronicle.derive`, die bei jeder Größe dieselben 500-Event-Batches bekommt und keine Datenbank berührt, wurde zwischen dem 100.000er- und dem 700.000er-Lauf der Zerlegung ebenfalls langsamer, von 5,3 auf 6,9 ms pro Batch (Faktor 1,31). `insert_chronicle` wurde um den Faktor 1,37 langsamer, `units_by_event` um 1,25 und `read` um 1,27. Wenn der Code, der vom Log unabhängig ist, um fast denselben Faktor langsamer wird wie der Code, der die Datenbank fragt, liegt die Ursache eher am Zustand des Rechners (Last 6–8, Firefox) als an der Größe des Logs. Ausschließen kann ich einen Größeneffekt damit nicht, aber belegen kann ich ihn auch nicht.

**Hochrechnung auf 5.000.000 Events.** Das ist eine Extrapolation, keine Messung.

- **Neubau**: linear mit 0,39–0,55 ms pro Event, also **etwa 32–46 Minuten**. Setzte sich der bei 700.000 gemessene Anstieg pro Event fort (noch einmal Faktor 1,4 auf 7-fache Größe), wären es etwa 66 Minuten.
- **Kettenprüfung**: linear mit 0,13–0,135 ms pro Event, also **etwa 11 Minuten**. So lange stünde die `REPEATABLE READ`-Transaktion bei jedem Anker offen.
- **Laden des Bestands**: bei 700 Events/s etwa **2 Stunden** für 5.000.000 Events.
- **Platz**: linear aus 700.000 hochgerechnet, etwa 32 GB, davon etwa 14 GB in `p_chronicle`.
- Nachziehen und Lesen bleiben nach allem, was gemessen ist, unter einer Sekunde.

## Wo die Zeit hingeht

Gemessen mit `breakdown.py` in einem Prozess.
Das Skript umhüllt das Storage-Objekt, misst so jeden Storage-Aufruf, und bindet die beiden reinen `derive`-Funktionen und die drei Hashfunktionen in ihren Modulen neu, um sie zu messen.
Am Projektcode ist nichts verändert.
`read` wird innerhalb der Messspanne vollständig gelesen.
Was sich keinem Aufruf zuordnen lässt („Rest“), umfasst die Commits am Ende jedes `with store.begin()` und die Schleife in `catch_up`; einzeln gemessen habe ich das nicht.
Diese Läufe hatten 703.000 bzw. 103.000 Events, weil sie nach den drei Nachzieh-Runden liefen.

**Neubau `chronicle`, 703.000 Events, 284,9 s:**

| Anteil | s | % |
|---|---|---|
| `insert_chronicle` (Schreiben, executemany, etwa 3.650 Zeilen pro Batch) | 168,8 | 59,2 |
| `units_by_event` (Lesen) | 27,7 | 9,7 |
| `read` (Lesen) | 20,9 | 7,3 |
| `chronicle.derive` (reines Python) | 9,8 | 3,4 |
| `source_keys` (Lesen) | 6,4 | 2,2 |
| `set_projection_state` + `tip` | 3,1 | 1,1 |
| Rest (Commits, Schleife) | 48,3 | 17,0 |

**Neubau `source-stats`, 703.000 Events, 65,4 s:**

| Anteil | s | % |
|---|---|---|
| `units_by_event` + `read` + `source_keys` (Lesen des Logs) | 46,9 | 71,7 |
| `source_stats.derive` (reines Python) | 1,65 | 2,5 |
| `upsert_source_stats` + `source_stats` | 2,3 | 3,6 |
| `tip` + `set_projection_state` | 1,8 | 2,7 |
| Rest | 12,7 | 19,5 |

**Daraus folgt für den Neubau beider Projektionen (350 s):**

- Das Ableiten in reinem Python macht **11,4 s (3 %)** aus.
- Das Schreiben der Chronik macht **169 s (48 %)** aus.
- Das Lesen des Logs macht **102 s (29 %)** aus, und es geschieht **zweimal**: Jede Projektion liest das ganze Log samt aller Unit-Inhalte für sich.
- Der Rest ist Commit und Schleife.

Dieselben Anteile zeigt der Lauf mit 103.000 Events (32,4 s + 9,5 s): `insert_chronicle` 55,9 %, `derive` 3,4 %, Lesen in `source-stats` 71 %.
Die Aufteilung ist also stabil über die Größen.
Die Summe aus der Zerlegung (350 s) liegt innerhalb der Spanne der Läufe über die Kommandozeile (312–416 s); das Umhüllen kostet erkennbar wenig.

**Kettenprüfung, 703.000 Events, 96,0 s:**

| Anteil | s | % |
|---|---|---|
| `units_hash` (reines Python) | 27,7 | 28,9 |
| `units_by_event` (Lesen) | 21,4 | 22,3 |
| `read` (Lesen) | 17,2 | 17,9 |
| `event_hash` (reines Python) | 12,4 | 12,9 |
| `payload_hash` (reines Python) | 8,9 | 9,3 |
| `source_keys` (Lesen) | 5,0 | 5,2 |
| `count_events` | 0,03 | 0,0 |

Die Prüfung verbringt also **51 % im Hashen** und 45 % im Lesen.
Das passt zu den 100 Abtastungen mit `idle in transaction`: Der Server wartet die meiste Zeit auf Python.

## Eingang und Lesen während eines Neubaus

Nachgereicht auf Bitte des Koordinators, gemessen auf der größten geladenen Größe: 703.000 Events zu Beginn, 710.577 am Ende.
Das Skript ist `during_rebuild.py`, aufgerufen über `during.sh`; die Rohausgabe steht unten vollständig.

**Wie der Neubau erzwungen wurde:** mit `UPDATE projection_state SET version = 0`.
Der Code deklariert Version 1, und `catch_up` baut bei `!=` neu.
Dabei läuft genau der Pfad im Code: `truncate_projection` (ein `DELETE` aller Zeilen) und der Zustand in einer Transaktion, danach das Wiederauffüllen in Batches, **an Ort und Stelle**, während die alten Daten noch da sind.
Gestartet wurde der Neubau mit `/usr/bin/time -f '…' .venv/bin/previously project` als Kindprozess.

**Eingang.** Ein Thread hängt über das projekteigene `append` alle 50 ms ein Event an (Batch 1, `make_event` aus `load.py`).
Zuerst 60 s ohne Neubau, dann mit demselben Takt ab 2 s vor dem Start bis 2 s nach dem Ende des Neubaus.

| | n | Median | p95 | Max | Min | Fehler |
|---|---|---|---|---|---|---|
| ohne Neubau | 1.198 | 8,7 ms | 13,0 ms | 27,2 ms | 5,2 ms | keine |
| während des Neubaus | 6.379 | 13,8 ms | 85,6 ms | 1.391,9 ms | 5,1 ms | keine |

- **Jedes Anhängen während des Neubaus ging durch**, ohne Fehler und ohne `ChainConflict`; jedes bekam die erwartete `id`.
- Es wurde langsamer: im Median um den Faktor 1,6, im p95 um 6,6, im Maximum um 51. Den Ausreißer von 1,39 s habe ich keinem Ereignis zugeordnet, weil ich die Zeitpunkte einzelner Latenzen nicht aufgezeichnet habe.
- Durch die Verzögerung kamen statt 20 nur etwa 17 Events pro Sekunde zustande, weil das Skript nach einem langsamen `append` nicht nachholt.
- **Der Neubau selbst** lief mit Rückgabewert 0 durch, ohne `ProjectionGap`. Er brauchte 374,0 s (110 MiB) und lag damit innerhalb der Spanne der drei Neubauten ohne Last (312–416 s). Ein Bremsen durch den Eingang ist bei dieser Streuung nicht nachweisbar. Ausgabe: `chronicle built: 709132 events, up_to_id 709132` und `source-stats built: 710517 events, up_to_id 710517`. Jede Projektion endet an der Spitze, die sie bei ihrem letzten Batch sah, und hat dabei die während des Neubaus angehängten Events mitgenommen.

**Was ein Leser sah.** Alle etwa 16 s liefen `previously chronicle` und `previously stats` (Rückgabewert immer 0), dazu eine Abfrage von `projection_state`.
Eine Auswahl, alle Zeilen stehen in der Rohausgabe:

| Zeit | `projection_state` (chronicle / source-stats) | `chronicle` stdout | `chronicle` stderr | `stats` stdout (mail: Events) | `stats` stderr |
|---|---|---|---|---|---|
| 18:30:01 | 703000 v0 / 703000 v0 | 50 Zeilen ab Event 15 | `projection is 1274 events behind` | 492137 (alter Stand) | `1278 events behind` |
| 18:30:17 | 703000 v0 / 703000 v0 | dasselbe | `1426 events behind` | 492137 | `1431 events behind` |
| 18:30:33 | **11500 v1** / 703000 v0 | 50 Zeilen ab Event 15 | **`projection is 694605 events behind`** | 492137 | `1612 events behind` |
| 18:33:12 | 414500 v1 / 703000 v0 | 50 Zeilen ab Event 15 | `292764 events behind` | 492137 | `4265 events behind` |
| 18:35:02 | 709132 v1 / **81000 v1** | 50 Zeilen ab Event 15 | `152 events behind` | **56272** | **`projection is 629292 events behind`** |
| 18:36:06 | 709132 v1 / 681000 v1 | 50 Zeilen ab Event 15 | `1304 events behind` | 475974 | `30442 events behind` |
| 18:36:16 (nach dem Nachziehen) | 710577 / 710577 | 50 Zeilen ab Event 15 | nur `output truncated at 50 lines; …` | 497429 | leer |

Daraus lese ich:

1. **In den ersten 16–32 s sieht der Leser den alten, vollständigen Stand.** Die Transaktion, die 5,1 Millionen Chronik-Zeilen löscht und den Zustand setzt, ist noch nicht committet; der Zustand zeigt noch Version 0.
2. **Danach sieht der Leser eine halb gebaute Projektion.** Ab 18:30:33 enthält `p_chronicle` nur die bisher neu gebauten Events (11.500 und aufwärts). Ab 18:35:02 zeigt `stats` Teilsummen, etwa `mail 56272` statt 497.429 Events, mit `last_seen` 2022-02-26 statt 2025-04-22.
3. **stdout sieht dabei nicht unvollständig aus.** `chronicle` mit Standardlimit zeigt die zeitlich frühesten Zeilen, und genau die baut der Neubau zuerst; die 50 Zeilen sind in jedem Lauf dieselben ab Event 15. `stats` gibt vier plausible Zeilen aus. Wer nur stdout liest, sieht nichts.
4. **Der einzige Hinweis steht auf stderr**: die gewöhnliche Rückstandszeile `projection is N events behind; run \`previously project\``. N springt dabei von etwa 1.400 auf 694.605. Sie lautet genau so wie bei einem gewöhnlichen Rückstand und sagt nicht, dass gerade neu gebaut wird.
5. Jedes Lesekommando misst den Rückstand an seiner **eigenen** Projektion, so wie es der Code in `_cmd_stats` begründet. Solange die Chronik neu gebaut wurde, zeigte `stats` korrekt den alten, vollständigen Stand mit kleinem Rückstand, und umgekehrt.

Die Architekturaufzeichnung verlangt, dass Leser nie eine halb gebaute Projektion sehen. **Gemessen: Sie sehen eine**, etwa 6 Minuten lang bei 700.000 Events.
Gekennzeichnet ist sie nur durch die Rückstandszeile auf stderr.
Die Forderung „Eingang läuft weiter“ ist dagegen erfüllt.

**Nach dem Neubau und einem Nachziehen gleich wie ein Neubau aus dem Nichts.**
Das Nachziehen meldete `chronicle caught up: 1445 events` und `source-stats caught up: 60 events`; beide standen danach bei `up_to_id 710577`.
Danach wurde verglichen: zuerst das Ergebnis des Neubaus an Ort und Stelle, dann nach `TRUNCATE` und `DELETE FROM projection_state` ein frischer `previously project` auf demselben Log.

- `p_chronicle` an Ort und Stelle: 5.214.291 Zeilen, 5.214.291 verschiedene `(event_id, seq)`, Prüfsumme `sum(hashtext(concat_ws(chr(31), alle elf Spalten)))` = 4217032151250. Frisch: 5.214.291 / 5.214.291 / 4217032151250. **Gleich.** Die Zahl der Unit-Zeilen im Log ist ebenfalls 5.214.291.
- `stats` gab beide Male byteweise dieselbe Ausgabe (`stats equal: True`), in der Ausgabe `mail 497429 3187243 …` und so weiter für alle vier Quellen.

## Beobachtungen

Bemerkt, aber nicht angefasst. Weder PostgreSQL noch der Code wurden verändert.

1. **Der Neubau an Ort und Stelle zeigt Lesern einen halben Stand**, und nur stderr sagt es, mit denselben Worten wie bei gewöhnlichem Rückstand (oben). Das widerspricht der Forderung der Architekturaufzeichnung und wiegt in diesem Bericht am schwersten. Was es ändern würde, etwa in eine Schattentabelle bauen und am Ende umschalten oder den Neubau in der Rückstandszeile benennen, ist eine Designfrage und keine Messung.
2. **Jede Projektion liest das ganze Log für sich.** `source-stats` verbringt 72 % seiner Zeit damit, Events und alle Unit-Inhalte zu lesen, nur um die Units zu zählen (`len(batch.units.get(...))`). Bei 700.000 Events kostet das zweifache Lesen etwa 100 s von 350 s. Ein gemeinsamer Lesedurchgang für beide Projektionen oder eine Unit-Zählung ohne `content` würde das ändern; gemessen habe ich das nicht.
3. **Das Schreiben der Chronik ist der größte Einzelposten** (48 % des Neubaus). Die reine Ableitung kostet 3 %. Die Trennung im Worker in Ableiten und Schreiben ist also billig; die Kosten liegen beim Schreiben und beim Lesen, nicht beim Ableiten.
4. **Die Snapshot-Transaktion der Kettenprüfung steht so lange offen wie die Prüfung**: 89–112 s bei 700.000 Events, hochgerechnet etwa 11 Minuten bei 5.000.000. Eine offene `REPEATABLE READ`-Transaktion hält den `xmin`-Horizont fest, so dass VACUUM in dieser Zeit keine toten Tupel entfernen kann. Das gilt etwa für die 5,1 Millionen Zeilen, die das `DELETE` eines Neubaus an Ort und Stelle hinterlässt. Gemessen habe ich nur die Dauer, nicht die Wirkung auf VACUUM.
5. **Der Neubau an Ort und Stelle löscht mit `DELETE`** und nicht mit `TRUNCATE`; das ist im Code begründet. Bei 700.000 Events sind das 5,1 Millionen tote Tupel in einer Tabelle von 1,9 GB, bis VACUUM sie aufräumt. Die Tabellengröße nach diesem Neubau habe ich nicht gemessen.
6. **Der Text wird dreimal gespeichert**: in `event.payload` (wie bei `previously append`), in `unit` und in `p_chronicle`. Das ergibt 4,5 GB Datenbank für etwa 1 GB Text. Ob ein Mail-Konnektor den Text ebenfalls in den `payload` schreibt, ist noch offen; meine Daten folgen hier `_cmd_append`.
7. **Ein Import des Bestands dauert Stunden**: etwa 23 Minuten für 1.000.000 Events, etwa 2 Stunden für 5.000.000 bei 700 Events/s. Vier Anweisungen pro Event (`lookup`, drei `INSERT`) bestimmen die Rate, sobald der Batch über etwa 50 liegt.
8. **Streuung über ein Viertel**:
   - Neubau bei 700.000: 415,8 / 311,6 / 388,0 s, also 33 % zwischen dem ersten und dem zweiten Lauf. Ich vermute vor allem die Last auf dem Rechner (Firefox mit 92 % CPU, Load Average 6–8 auf 8 Threads). Daneben kommen in Frage: erzwungene Checkpoints (`pg_stat_checkpointer.num_requested = 33` und `num_timed = 0` nach den Neubauten; ein Neubau schreibt etwa 2 GB, `max_wal_size` ist 1 GB) und Autovacuum auf `p_chronicle` während der Läufe (`last_autovacuum` 16:06 UTC). Getrennt habe ich diese Ursachen nicht.
   - `stats` bei 10.000: 0,351 s gegen 0,277 und 0,284 s, ein einzelner Ausreißer.
   - Laden mit Batch 50: 786 und 661 Events/s.
   - Alle anderen Wiederholungen liegen innerhalb von 10 %.
9. **Der Prozessstart beträgt 0,2 s** von 0,27–0,30 s jedes Lesekommandos. Der größere Teil dessen, worauf ein Nutzer bei `chronicle` und `stats` wartet, ist der Import von SQLAlchemy und psycopg; `uv run` legt nur 0,01–0,03 s darauf.

## Skripte und Rohausgaben

Alle Skripte liegen unter `/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/messung/` und sind unten vollständig wiedergegeben.
Sie liefen jeweils mit `bash <skript>.sh > out-<größe>.txt 2>&1`, mit dem Worktree als Arbeitsverzeichnis und mit `PREVIOUSLY_DSN=postgresql+psycopg://previously:previously@localhost:55432/previously`.
Reihenfolge: `batchprobe.sh`, `size10k.sh`, `size100k.sh`, `size700k.sh`, `during.sh`.

In den Rohausgaben von `measure.py` folgen auf jede Zeile eine oder zwei Zeilen `stdout:`/`stderr:` mit dem Anfang der Ausgabe des Kommandos.
In `out-10k.txt` sind sie vollständig wiedergegeben; in `out-100k.txt` und `out-700k.txt` sind sie gleichförmig und deshalb weggelassen.
Ihre Inhalte waren bei jedem Lauf dieser Art dieselben:

- `rebuild`: `chronicle built: N events …` und `source-stats built: …`
- `verify`: stdout `chain intact`, stderr `no anchor given: …`
- `chronicle`: 50 Zeilen, stderr `output truncated at 50 lines; …`
- `stats`: 4 Zeilen, ohne stderr
- `catch-up`: `caught up: 1000 events …` für beide Projektionen

### `load.py`

````
"""Load events through previously.core.append.append, in batches.

usage: load.py START COUNT [BATCH]
Event i (1-based, global) is generated deterministically from random.Random(i),
so loading 1..10000 and then 10001..100000 yields the same log as one run.
Only the append() calls are timed; generation (incl. split_plaintext) separately.
"""

import os
import random
import resource
import sys
import time
from datetime import UTC, datetime, timedelta

from previously.contract.types import Evidence, RawEvent
from previously.core.append import append
from previously.core.units import split_plaintext
from previously.storage.postgres import from_dsn

WORDS = (
    "the project meeting budget review proposal deadline client server deploy release "
    "branch migration database schema index query backup restore anchor chain hash log "
    "event unit projection worker invoice contract offer change request ticket issue bug "
    "fix test coverage gate documentation page tutorial reference explanation design "
    "der die das und ist nicht wir haben bitte danke Termin Angebot Rechnung Vertrag "
    "Besprechung Kunde Projekt Änderung Abnahme Frist Freigabe Entwurf Rückfrage Woche "
    "Montag Dienstag Mittwoch Donnerstag Freitag morgen heute gestern noch schon auch "
    "would could should will can may must please thanks regards next last week month "
    "Kubernetes ArgoCD PostgreSQL Plone Python cluster node volume certificate DNS mail"
).split()

SOURCES = (("mail", 0.70), ("chat", 0.15), ("transcript", 0.10), ("notes", 0.05))
START = datetime(2021, 10, 1, tzinfo=UTC)
SPAN = timedelta(days=5 * 365)
PLANNED_TOTAL = 1_000_000


def sentence(r: random.Random) -> str:
    n = r.randint(5, 18)
    words = [r.choice(WORDS) for _ in range(n)]
    return words[0].capitalize() + " " + " ".join(words[1:]) + r.choice((".", ".", ".", "?", "!"))


def paragraph(r: random.Random, lo: int, hi: int) -> str:
    return " ".join(sentence(r) for _ in range(r.randint(lo, hi)))


def make_text(r: random.Random, source: str) -> str:
    if source == "mail":
        parts = [r.choice(("Hallo Jens,", "Hi all,", "Sehr geehrte Damen und Herren,", "Hi,"))]
        parts += [paragraph(r, 1, 6) for _ in range(r.randint(1, 7))]
        if r.random() < 0.4:  # quoted reply, as one block of "> " lines
            quoted = "\n".join("> " + sentence(r) for _ in range(r.randint(2, 15)))
            parts.append("On some day somebody wrote:\n" + quoted)
        parts.append(r.choice(("Beste Grüße\nJens", "Regards,\nAnna", "--\nKlein & Partner")))
        return "\r\n\r\n".join(p.replace("\n", "\r\n") for p in parts)  # RFC 5322 CRLF
    if source == "chat":
        return "\n\n".join(paragraph(r, 1, 2) for _ in range(r.randint(1, 3)))
    if source == "transcript":
        return "\n\n".join(paragraph(r, 1, 3) for _ in range(r.randint(8, 40)))
    return "\n\n".join(paragraph(r, 1, 4) for _ in range(r.randint(1, 5)))


def make_event(i: int) -> RawEvent:
    r = random.Random(i)
    x = r.random()
    acc = 0.0
    source = SOURCES[-1][0]
    for name, weight in SOURCES:
        acc += weight
        if x < acc:
            source = name
            break
    occurred = START + SPAN * (i / PLANNED_TOTAL) + timedelta(seconds=r.randint(-3 * 86400, 3 * 86400))
    text = make_text(r, source)
    return RawEvent(
        source=source,
        external_id=f"{source}-{i:08d}",
        occurred_at=occurred,
        evidence=Evidence.VERBATIM if source != "notes" else Evidence.RECOLLECTION,
        units=split_plaintext(text),
        payload={"text": text},
    )


def main() -> None:
    start, count = int(sys.argv[1]), int(sys.argv[2])
    batch = int(sys.argv[3]) if len(sys.argv) > 3 else 500
    storage = from_dsn(os.environ["PREVIOUSLY_DSN"])
    gen_s = append_s = 0.0
    units = text_bytes = 0
    per_slice: list[float] = []
    done = 0
    slice_t = 0.0
    for b0 in range(start, start + count, batch):
        t0 = time.perf_counter()
        events = [make_event(i) for i in range(b0, min(b0 + batch, start + count))]
        t1 = time.perf_counter()
        ids = append(storage, events, recorded_at=datetime.now(UTC))
        t2 = time.perf_counter()
        assert ids == list(range(b0, b0 + len(events))), (ids[:3], b0)
        gen_s += t1 - t0
        append_s += t2 - t1
        slice_t += t2 - t1
        units += sum(len(e.units) for e in events)
        text_bytes += sum(len(str(e.payload["text"]).encode()) for e in events)
        done += len(events)
        if done % 100_000 == 0:
            per_slice.append(slice_t)
            print(f"  .. {start + done - 1}: last 100k appended in {slice_t:.1f} s", flush=True)
            slice_t = 0.0
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(
        f"loaded ids {start}..{start + count - 1}: {count} events, {units} units, "
        f"{text_bytes / 1e6:.1f} MB text, batch {batch}\n"
        f"  generate+split {gen_s:.2f} s; append {append_s:.2f} s = {count / append_s:.0f} events/s, "
        f"{units / append_s:.0f} units/s; maxrss {rss / 1024:.0f} MiB",
        flush=True,
    )


if __name__ == "__main__":
    main()
````

### `measure.py`

````
"""Measure one size. usage: measure.py N   (the log must hold exactly N events)

Phases, each run as a fresh process of the project's own console script
(.venv/bin/previously, no uv in between) under /usr/bin/time -v:
  rebuild x3   (setup per run, untimed: TRUNCATE both projection tables,
                DELETE projection_state, CHECKPOINT)
  verify x3
  readings x3  (chronicle, chronicle with a one-day window in the middle,
                stats) — once through `uv run`, once through .venv/bin directly
  catch-up x3  (setup per run, untimed: load.py appends 1000 events)
Wall time is perf_counter around the child; peak RSS from time -v.
"""

import os
import re
import subprocess
import sys
import time
from datetime import timedelta

from sqlalchemy import create_engine, text

WT = "/home/jensens/ws/jwk/previously/.claude/worktrees/pruefpunkt-teilprojekt-1"
HERE = os.path.dirname(os.path.abspath(__file__))
DSN = os.environ["PREVIOUSLY_DSN"]
engine = create_engine(DSN, isolation_level="AUTOCOMMIT")
PREV = f"{WT}/.venv/bin/previously"


def sql(stmt: str):
    with engine.connect() as c:
        return c.execute(text(stmt)).all() if stmt.lstrip().upper().startswith("SELECT") else c.execute(text(stmt))


def timed(label: str, argv: list[str]) -> tuple[float, int, str]:
    t0 = time.perf_counter()
    p = subprocess.run(["/usr/bin/time", "-v", *argv], cwd=WT, capture_output=True, text=True)
    wall = time.perf_counter() - t0
    m = re.search(r"Maximum resident set size \(kbytes\): (\d+)", p.stderr)
    rss = int(m.group(1)) if m else -1
    stdout_lines = p.stdout.count("\n")
    tool_err = "\n".join(l for l in p.stderr.splitlines() if not l.startswith("\t"))
    print(
        f"{label:<28} wall {wall:8.3f} s  maxrss {rss / 1024:7.1f} MiB  rc {p.returncode}  "
        f"stdout_lines {stdout_lines}",
        flush=True,
    )
    first = p.stdout.splitlines()[:2]
    if first:
        print("    stdout: " + " | ".join(first)[:200], flush=True)
    if tool_err.strip():
        print("    stderr: " + tool_err.strip().replace("\n", " | ")[:300], flush=True)
    if p.returncode != 0:
        print(p.stderr, flush=True)
    return wall, rss, p.stdout


def reset_projections() -> None:
    sql("TRUNCATE p_chronicle, p_source_stats")
    sql("DELETE FROM projection_state")
    sql("CHECKPOINT")


def main() -> None:
    n = int(sys.argv[1])
    (count,) = sql("SELECT count(*) FROM event")[0]
    assert count == n, (count, n)
    (units,) = sql("SELECT count(*) FROM unit")[0]
    print(f"=== size {n}: {units} unit rows", flush=True)
    for row in sql(
        "SELECT relname, pg_size_pretty(pg_total_relation_size(oid)) FROM pg_class "
        "WHERE relname IN ('event','unit','source_key','p_chronicle') ORDER BY relname"
    ):
        print(f"    {row[0]}: {row[1]}", flush=True)

    for i in range(3):
        reset_projections()
        timed(f"rebuild #{i + 1}", [PREV, "project"])
    (chron,) = sql("SELECT count(*) FROM p_chronicle")[0]
    print(f"    p_chronicle rows after rebuild: {chron}", flush=True)
    for row in sql(
        "SELECT relname, pg_size_pretty(pg_total_relation_size(oid)) FROM pg_class "
        "WHERE relname IN ('p_chronicle') ORDER BY relname"
    ):
        print(f"    {row[0]}: {row[1]}", flush=True)

    sql("CHECKPOINT")
    for i in range(3):
        timed(f"verify #{i + 1}", [PREV, "verify"])

    lo, hi = sql("SELECT min(occurred_at), max(occurred_at) FROM event")[0]
    mid = lo + (hi - lo) / 2
    since, until = mid.isoformat(), (mid + timedelta(days=1)).isoformat()
    (in_window,) = sql(
        f"SELECT count(*) FROM p_chronicle WHERE occurred_at >= '{since}' AND occurred_at < '{until}'"
    )[0]
    print(f"    window {since} .. {until}: {in_window} chronicle rows in it", flush=True)
    readings = {
        "help": ["--help"],
        "chronicle": ["chronicle"],
        "chronicle-window": ["chronicle", "--since", since, "--until", until],
        "stats": ["stats"],
    }
    for name, args in readings.items():
        for i in range(3):
            timed(f"uv {name} #{i + 1}", ["uv", "run", "previously", *args])
        for i in range(3):
            timed(f"venv {name} #{i + 1}", [PREV, *args])

    timed("project (up to date)", [PREV, "project"])
    nxt = n + 1
    for i in range(3):
        subprocess.run(
            [f"{WT}/.venv/bin/python", f"{HERE}/load.py", str(nxt), "1000", "500"],
            cwd=WT, check=True, capture_output=True,
        )
        nxt += 1000
        timed(f"catch-up 1000 #{i + 1}", [PREV, "project"])
    (count,) = sql("SELECT count(*) FROM event")[0]
    print(f"=== size {n} done, log now {count}", flush=True)


if __name__ == "__main__":
    main()
````

### `breakdown.py`

````
"""Where a rebuild and a chain check spend their time. usage: breakdown.py

Runs the project's own catch_up (both projections) and examine in-process,
with the storage object wrapped so that every storage call is timed, and the
two pure `derive` functions timed by rebinding the module names (the write
steps look `derive` up as a module global). No project file is changed.
Projections are reset first (TRUNCATE + DELETE projection_state, untimed).
The wrapper adds overhead of its own; the totals are printed beside a plain
run's wall time so that the overhead is visible.
"""

import os
import resource
import time
from collections import defaultdict

import previously.core.hashing as hashing
import previously.core.projection.chronicle as chronicle_mod
import previously.core.projection.source_stats as stats_mod
import previously.core.verify as verify_mod
from previously.core.projection import PROJECTIONS, catch_up
from previously.core.verify import examine
from previously.storage.postgres import from_dsn
from sqlalchemy import create_engine, text

acc: dict[str, float] = defaultdict(float)
calls: dict[str, int] = defaultdict(int)


def timing(name, fn):
    def wrapper(*a, **k):
        t0 = time.perf_counter()
        try:
            return fn(*a, **k)
        finally:
            acc[name] += time.perf_counter() - t0
            calls[name] += 1

    return wrapper


class Timed:
    def __init__(self, inner):
        self._inner = inner

    def read(self, conn, from_id, limit):
        t0 = time.perf_counter()
        rows = list(self._inner.read(conn, from_id, limit))  # consume the cursor inside the span
        acc["storage.read"] += time.perf_counter() - t0
        calls["storage.read"] += 1
        return iter(rows)

    def __getattr__(self, name):
        attr = getattr(self._inner, name)
        if name in ("begin", "snapshot") or not callable(attr):
            return attr
        return timing(f"storage.{name}", attr)


def report(title: str, wall: float) -> None:
    print(f"--- {title}: wall {wall:.2f} s", flush=True)
    for name, s in sorted(acc.items(), key=lambda kv: -kv[1]):
        print(f"    {name:<32} {s:8.2f} s  {100 * s / wall:5.1f} %  calls {calls[name]}", flush=True)
    acc.clear()
    calls.clear()


def main() -> None:
    dsn = os.environ["PREVIOUSLY_DSN"]
    admin = create_engine(dsn, isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        c.execute(text("TRUNCATE p_chronicle, p_source_stats"))
        c.execute(text("DELETE FROM projection_state"))
        c.execute(text("CHECKPOINT"))
    storage = Timed(from_dsn(dsn))

    chronicle_mod.derive = timing("chronicle.derive (pure)", chronicle_mod.derive)
    stats_mod.derive = timing("source_stats.derive (pure)", stats_mod.derive)
    for p in PROJECTIONS:
        t0 = time.perf_counter()
        out = catch_up(storage, storage, p)
        report(f"catch_up {p.name} ({out.events} events)", time.perf_counter() - t0)

    # examine: hashing is the pure part. verify imported the three names directly.
    verify_mod.event_hash = timing("event_hash (pure)", hashing.event_hash)
    verify_mod.payload_hash = timing("payload_hash (pure)", hashing.payload_hash)
    verify_mod.units_hash = timing("units_hash (pure)", hashing.units_hash)
    t0 = time.perf_counter()
    ex = examine(storage)
    report(f"examine ({len(ex.findings)} findings, tip {ex.tip.id if ex.tip else None})", time.perf_counter() - t0)
    print(f"maxrss {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:.0f} MiB", flush=True)


if __name__ == "__main__":
    main()
````

### `xactpoll.py`

````
"""Poll pg_stat_activity every second; print every open transaction other than our own.
Runs until killed. Used beside one `previously verify` to see how long its snapshot stays open."""

import os
import time

from sqlalchemy import create_engine, text

engine = create_engine(os.environ["PREVIOUSLY_DSN"], isolation_level="AUTOCOMMIT")
Q = text(
    "SELECT pid, now() - xact_start AS xact_age, state, "
    "current_setting('transaction_isolation') AS mine, left(query, 70) AS q "
    "FROM pg_stat_activity WHERE datname = current_database() "
    "AND xact_start IS NOT NULL AND pid <> pg_backend_pid()"
)
with engine.connect() as c:
    while True:
        for r in c.execute(Q):
            print(f"{time.strftime('%H:%M:%S')} pid {r.pid} xact_age {r.xact_age} {r.state} | {r.q}", flush=True)
        time.sleep(1)
````

### `during_rebuild.py`

````
"""Intake and reading during a forced rebuild. usage: during_rebuild.py

1. baseline: one append every 50 ms for 60 s, no rebuild running (append() of one
   event through the project's own function; latency per call)
2. force a rebuild of both projections the least invasive way: UPDATE projection_state
   SET version = 0 (the code declares 1, `!=` triggers truncate + refill), then run
   `.venv/bin/previously project` as a child process; meanwhile the same appender
   thread runs, and a reader thread runs `previously chronicle` and `previously stats`
   every 15 s
3. after: one more `previously project` (catch-up), record p_chronicle count + stats;
   then a rebuild from nothing (TRUNCATE, DELETE projection_state, project) and the same
   two readings; compare
"""

import os
import statistics
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import make_event  # noqa: E402

from previously.core.append import append  # noqa: E402
from previously.storage.postgres import from_dsn  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

WT = "/home/jensens/ws/jwk/previously/.claude/worktrees/pruefpunkt-teilprojekt-1"
PREV = f"{WT}/.venv/bin/previously"
DSN = os.environ["PREVIOUSLY_DSN"]
admin = create_engine(DSN, isolation_level="AUTOCOMMIT")
storage = from_dsn(DSN)


def q(stmt):
    with admin.connect() as c:
        r = c.execute(text(stmt))
        return r.all() if r.returns_rows else None


def stamp():
    return time.strftime("%H:%M:%S")


class Appender(threading.Thread):
    def __init__(self, next_i):
        super().__init__(daemon=True)
        self.next_i = next_i
        self.stop = threading.Event()
        self.lat: list[float] = []
        self.errors: list[str] = []

    def run(self):
        while not self.stop.is_set():
            t_due = time.perf_counter() + 0.05
            ev = make_event(self.next_i)
            t0 = time.perf_counter()
            try:
                ids = append(storage, [ev], recorded_at=datetime.now(UTC))
                self.lat.append(time.perf_counter() - t0)
                assert ids == [self.next_i], (ids, self.next_i)
            except Exception as e:  # a finding, not to be swallowed silently
                self.errors.append(f"{stamp()} {type(e).__name__}: {e}")
            self.next_i += 1
            time.sleep(max(0.0, t_due - time.perf_counter()))


def summary(name, lat):
    s = sorted(lat)
    p95 = s[int(0.95 * (len(s) - 1))]
    print(
        f"{name}: n={len(s)} median {statistics.median(s) * 1000:.1f} ms  p95 {p95 * 1000:.1f} ms  "
        f"max {s[-1] * 1000:.1f} ms  min {s[0] * 1000:.1f} ms",
        flush=True,
    )


def run(args):
    p = subprocess.run([PREV, *args], cwd=WT, capture_output=True, text=True)
    return p


def readings(tag):
    c = run(["chronicle"])
    s = run(["stats"])
    lines = c.stdout.splitlines()
    print(
        f"  [{stamp()} {tag}] chronicle rc {c.returncode}: {len(lines)} lines, first event_id "
        f"{lines[0].split(chr(9))[0] if lines else '-'}; stderr: {c.stderr.strip()!r}",
        flush=True,
    )
    print(f"  [{stamp()} {tag}] stats rc {s.returncode}: {s.stdout.strip()!r}; stderr: {s.stderr.strip()!r}", flush=True)
    st = q("SELECT name, up_to_id, version FROM projection_state ORDER BY name")
    print(f"  [{stamp()} {tag}] projection_state {st}", flush=True)


def main():
    (tip,) = q("SELECT max(id) FROM event")[0]
    print(f"{stamp()} log tip {tip}; projection_state {q('SELECT name, up_to_id, version FROM projection_state ORDER BY name')}", flush=True)

    base = Appender(tip + 1)
    base.start()
    time.sleep(60)
    base.stop.set()
    base.join()
    summary("baseline appends (no rebuild)", base.lat)
    print(f"  baseline errors: {base.errors}", flush=True)

    q("UPDATE projection_state SET version = 0")
    print(f"{stamp()} forced: {q('SELECT name, up_to_id, version FROM projection_state ORDER BY name')}", flush=True)
    app = Appender(base.next_i)
    app.start()
    time.sleep(2)
    t0 = time.perf_counter()
    proc = subprocess.Popen(["/usr/bin/time", "-f", "rebuild wall %e s maxrss %M kB", PREV, "project"],
                            cwd=WT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print(f"{stamp()} rebuild started (pid {proc.pid})", flush=True)
    time.sleep(3)
    while proc.poll() is None:
        readings("during rebuild")
        for _ in range(15):
            if proc.poll() is not None:
                break
            time.sleep(1)
    out, err = proc.communicate()
    wall = time.perf_counter() - t0
    print(f"{stamp()} rebuild ended rc {proc.returncode} after {wall:.1f} s\n  stdout: {out.strip()!r}\n  stderr: {err.strip()!r}", flush=True)
    time.sleep(2)
    app.stop.set()
    app.join()
    summary("appends during rebuild", app.lat)
    print(f"  errors during rebuild: {app.errors}", flush=True)
    readings("after rebuild, before catch-up")

    p = run(["project"])
    print(f"{stamp()} catch-up rc {p.returncode}: {p.stdout.strip()!r} {p.stderr.strip()!r}", flush=True)
    readings("after catch-up")
    inplace_count = q("SELECT count(*), count(DISTINCT (event_id, seq)), sum(hashtext(concat_ws(chr(31), event_id, seq, content, occurred_at, kind, evidence, source, external_id, speaker, start_ms, end_ms))::bigint) FROM p_chronicle")[0]
    inplace_stats = run(["stats"]).stdout
    (units,) = q("SELECT count(*) FROM unit")[0]
    print(f"  in-place: p_chronicle (rows, distinct keys) {inplace_count}; unit rows in log {units}", flush=True)

    q("TRUNCATE p_chronicle, p_source_stats")
    q("DELETE FROM projection_state")
    p = run(["project"])
    print(f"{stamp()} rebuild from nothing rc {p.returncode}: {p.stdout.strip()!r}", flush=True)
    fresh_count = q("SELECT count(*), count(DISTINCT (event_id, seq)), sum(hashtext(concat_ws(chr(31), event_id, seq, content, occurred_at, kind, evidence, source, external_id, speaker, start_ms, end_ms))::bigint) FROM p_chronicle")[0]
    fresh_stats = run(["stats"]).stdout
    print(f"  fresh: p_chronicle {fresh_count}", flush=True)
    print(f"  stats equal: {inplace_stats == fresh_stats}\n  in-place stats:\n{inplace_stats}  fresh stats:\n{fresh_stats}", flush=True)
    print(f"  chronicle counts equal: {inplace_count == fresh_count}", flush=True)
    print(f"{stamp()} log tip now {q('SELECT max(id) FROM event')[0][0]}", flush=True)


if __name__ == "__main__":
    main()
````

### `batchprobe.sh`

````
#!/bin/bash
# Batch-size probe in a separate database "batchprobe": same generator, batch 1 / 50 / 500, twice each.
set -e
cd /home/jensens/ws/jwk/previously/.claude/worktrees/pruefpunkt-teilprojekt-1
export PREVIOUSLY_DSN=postgresql+psycopg://previously:previously@localhost:55432/batchprobe
L=/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/messung/load.py
.venv/bin/python $L 1 2000 1
.venv/bin/python $L 2001 2000 50
.venv/bin/python $L 4001 2000 500
.venv/bin/python $L 6001 2000 1
.venv/bin/python $L 8001 2000 50
.venv/bin/python $L 10001 2000 500
````

### `size10k.sh`

````
#!/bin/bash
set -e
cd /home/jensens/ws/jwk/previously/.claude/worktrees/pruefpunkt-teilprojekt-1
export PREVIOUSLY_DSN=postgresql+psycopg://previously:previously@localhost:55432/previously
M=/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/messung
docker exec previously-messung-c psql -U previously -c 'drop database batchprobe'
date -Is; uptime
.venv/bin/python $M/load.py 1 10000 500
.venv/bin/python $M/measure.py 10000
.venv/bin/python $M/breakdown.py
date -Is
````

### `size100k.sh`

````
#!/bin/bash
set -e
cd /home/jensens/ws/jwk/previously/.claude/worktrees/pruefpunkt-teilprojekt-1
export PREVIOUSLY_DSN=postgresql+psycopg://previously:previously@localhost:55432/previously
M=/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/messung
date -Is; uptime
.venv/bin/python $M/load.py 13001 87000 500
.venv/bin/python $M/measure.py 100000
.venv/bin/python $M/breakdown.py
date -Is
````

### `size700k.sh`

````
#!/bin/bash
set -e
cd /home/jensens/ws/jwk/previously/.claude/worktrees/pruefpunkt-teilprojekt-1
export PREVIOUSLY_DSN=postgresql+psycopg://previously:previously@localhost:55432/previously
M=/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/messung
date -Is; uptime
.venv/bin/python $M/load.py 103001 597000 500
date -Is; uptime
.venv/bin/python $M/measure.py 700000
echo "--- verify #4 with pg_stat_activity polled beside it"
.venv/bin/python $M/xactpoll.py > $M/xactpoll-700k.txt 2>&1 &
POLL=$!
sleep 2
/usr/bin/time -f 'verify #4 wall %e s maxrss %M kB' .venv/bin/previously verify
kill $POLL
grep -c xact_age $M/xactpoll-700k.txt || true
head -3 $M/xactpoll-700k.txt; echo ...; tail -3 $M/xactpoll-700k.txt
.venv/bin/python $M/breakdown.py
date -Is; uptime
````

### `during.sh`

````
#!/bin/bash
set -e
cd /home/jensens/ws/jwk/previously/.claude/worktrees/pruefpunkt-teilprojekt-1
export PREVIOUSLY_DSN=postgresql+psycopg://previously:previously@localhost:55432/previously
M=/tmp/claude-1000/-home-jensens-ws-jwk-previously/e74a1184-b926-462d-955f-35c8c996119e/scratchpad/messung
date -Is; uptime
.venv/bin/python $M/during_rebuild.py
date -Is; uptime
````

### Rohausgabe `batchprobe.sh`

````
loaded ids 1..2000: 2000 events, 14407 units, 3.0 MB text, batch 1
  generate+split 0.21 s; append 10.08 s = 198 events/s, 1430 units/s; maxrss 59 MiB
loaded ids 2001..4000: 2000 events, 14677 units, 3.0 MB text, batch 50
  generate+split 0.13 s; append 2.54 s = 786 events/s, 5767 units/s; maxrss 60 MiB
loaded ids 4001..6000: 2000 events, 14702 units, 3.0 MB text, batch 500
  generate+split 0.12 s; append 2.51 s = 798 events/s, 5862 units/s; maxrss 64 MiB
loaded ids 6001..8000: 2000 events, 14844 units, 3.0 MB text, batch 1
  generate+split 0.22 s; append 10.52 s = 190 events/s, 1411 units/s; maxrss 59 MiB
loaded ids 8001..10000: 2000 events, 15001 units, 3.0 MB text, batch 50
  generate+split 0.14 s; append 3.02 s = 661 events/s, 4961 units/s; maxrss 60 MiB
loaded ids 10001..12000: 2000 events, 14606 units, 3.0 MB text, batch 500
  generate+split 0.13 s; append 2.50 s = 801 events/s, 5850 units/s; maxrss 65 MiB
````

### Rohausgabe `size10k.sh` (`out-10k.txt`, vollständig)

````
DROP DATABASE
2026-10-04T17:33:12+02:00
 17:33:12 up 2 days,  6:50,  1 user,  load average: 1,28, 1,56, 1,47
loaded ids 1..10000: 10000 events, 73631 units, 15.1 MB text, batch 500
  generate+split 0.61 s; append 11.48 s = 871 events/s, 6416 units/s; maxrss 64 MiB
=== size 10000: 73631 unit rows
    event: 15 MB
    p_chronicle: 24 kB
    source_key: 1560 kB
    unit: 20 MB
rebuild #1                   wall    3.773 s  maxrss    91.4 MiB  rc 0  stdout_lines 2
    stdout: chronicle       built: 10000 events, up_to_id 10000 | source-stats    built: 10000 events, up_to_id 10000
rebuild #2                   wall    3.404 s  maxrss    95.6 MiB  rc 0  stdout_lines 2
    stdout: chronicle       built: 10000 events, up_to_id 10000 | source-stats    built: 10000 events, up_to_id 10000
rebuild #3                   wall    3.767 s  maxrss    97.0 MiB  rc 0  stdout_lines 2
    stdout: chronicle       built: 10000 events, up_to_id 10000 | source-stats    built: 10000 events, up_to_id 10000
    p_chronicle rows after rebuild: 73631
    p_chronicle: 28 MB
verify #1                    wall    1.528 s  maxrss    99.6 MiB  rc 0  stdout_lines 1
    stdout: chain intact
    stderr: no anchor given: verify attests that the log is unchanged, not that it is complete; see `previously anchor`
verify #2                    wall    1.491 s  maxrss    99.4 MiB  rc 0  stdout_lines 1
    stdout: chain intact
    stderr: no anchor given: verify attests that the log is unchanged, not that it is complete; see `previously anchor`
verify #3                    wall    1.520 s  maxrss    99.7 MiB  rc 0  stdout_lines 1
    stdout: chain intact
    stderr: no anchor given: verify attests that the log is unchanged, not that it is complete; see `previously anchor`
    window 2021-10-10T02:32:01.280000+00:00 .. 2021-10-11T02:32:01.280000+00:00: 4195 chronicle rows in it
uv help #1                   wall    0.213 s  maxrss    44.1 MiB  rc 0  stdout_lines 16
    stdout: usage: previously [-h] |                   {append,log,verify,anchor,show,project,chronicle,stats} ...
uv help #2                   wall    0.214 s  maxrss    44.1 MiB  rc 0  stdout_lines 16
    stdout: usage: previously [-h] |                   {append,log,verify,anchor,show,project,chronicle,stats} ...
uv help #3                   wall    0.218 s  maxrss    44.1 MiB  rc 0  stdout_lines 16
    stdout: usage: previously [-h] |                   {append,log,verify,anchor,show,project,chronicle,stats} ...
venv help #1                 wall    0.203 s  maxrss    44.1 MiB  rc 0  stdout_lines 16
    stdout: usage: previously [-h] |                   {append,log,verify,anchor,show,project,chronicle,stats} ...
venv help #2                 wall    0.212 s  maxrss    44.1 MiB  rc 0  stdout_lines 16
    stdout: usage: previously [-h] |                   {append,log,verify,anchor,show,project,chronicle,stats} ...
venv help #3                 wall    0.199 s  maxrss    44.1 MiB  rc 0  stdout_lines 16
    stdout: usage: previously [-h] |                   {append,log,verify,anchor,show,project,chronicle,stats} ...
uv chronicle #1              wall    0.300 s  maxrss    59.5 MiB  rc 0  stdout_lines 50
    stdout: 15	1	2021-09-28T02:21:15.200000+00:00	notes	notes-00000015	Change meeting client DNS please restore thanks. | 15	2	2021-09-28T02:21:15.200000+00:00	notes	notes-00000015	Explanation Besprechung next de
    stderr: output truncated at 50 lines; raise --limit or narrow --since/--until
uv chronicle #2              wall    0.289 s  maxrss    59.7 MiB  rc 0  stdout_lines 50
    stdout: 15	1	2021-09-28T02:21:15.200000+00:00	notes	notes-00000015	Change meeting client DNS please restore thanks. | 15	2	2021-09-28T02:21:15.200000+00:00	notes	notes-00000015	Explanation Besprechung next de
    stderr: output truncated at 50 lines; raise --limit or narrow --since/--until
uv chronicle #3              wall    0.292 s  maxrss    59.6 MiB  rc 0  stdout_lines 50
    stdout: 15	1	2021-09-28T02:21:15.200000+00:00	notes	notes-00000015	Change meeting client DNS please restore thanks. | 15	2	2021-09-28T02:21:15.200000+00:00	notes	notes-00000015	Explanation Besprechung next de
    stderr: output truncated at 50 lines; raise --limit or narrow --since/--until
venv chronicle #1            wall    0.270 s  maxrss    59.8 MiB  rc 0  stdout_lines 50
    stdout: 15	1	2021-09-28T02:21:15.200000+00:00	notes	notes-00000015	Change meeting client DNS please restore thanks. | 15	2	2021-09-28T02:21:15.200000+00:00	notes	notes-00000015	Explanation Besprechung next de
    stderr: output truncated at 50 lines; raise --limit or narrow --since/--until
venv chronicle #2            wall    0.273 s  maxrss    59.7 MiB  rc 0  stdout_lines 50
    stdout: 15	1	2021-09-28T02:21:15.200000+00:00	notes	notes-00000015	Change meeting client DNS please restore thanks. | 15	2	2021-09-28T02:21:15.200000+00:00	notes	notes-00000015	Explanation Besprechung next de
    stderr: output truncated at 50 lines; raise --limit or narrow --since/--until
venv chronicle #3            wall    0.277 s  maxrss    59.7 MiB  rc 0  stdout_lines 50
    stdout: 15	1	2021-09-28T02:21:15.200000+00:00	notes	notes-00000015	Change meeting client DNS please restore thanks. | 15	2	2021-09-28T02:21:15.200000+00:00	notes	notes-00000015	Explanation Besprechung next de
    stderr: output truncated at 50 lines; raise --limit or narrow --since/--until
uv chronicle-window #1       wall    0.287 s  maxrss    59.6 MiB  rc 0  stdout_lines 50
    stdout: 3807	1	2021-10-10T02:33:16.760000+00:00	transcript	transcript-00003807	Schema Projekt wir release Vertrag. | 3807	2	2021-10-10T02:33:16.760000+00:00	transcript	transcript-00003807	Plone next please Ve
    stderr: output truncated at 50 lines; raise --limit or narrow --since/--until
uv chronicle-window #2       wall    0.288 s  maxrss    59.7 MiB  rc 0  stdout_lines 50
    stdout: 3807	1	2021-10-10T02:33:16.760000+00:00	transcript	transcript-00003807	Schema Projekt wir release Vertrag. | 3807	2	2021-10-10T02:33:16.760000+00:00	transcript	transcript-00003807	Plone next please Ve
    stderr: output truncated at 50 lines; raise --limit or narrow --since/--until
uv chronicle-window #3       wall    0.299 s  maxrss    59.7 MiB  rc 0  stdout_lines 50
    stdout: 3807	1	2021-10-10T02:33:16.760000+00:00	transcript	transcript-00003807	Schema Projekt wir release Vertrag. | 3807	2	2021-10-10T02:33:16.760000+00:00	transcript	transcript-00003807	Plone next please Ve
    stderr: output truncated at 50 lines; raise --limit or narrow --since/--until
venv chronicle-window #1     wall    0.273 s  maxrss    59.6 MiB  rc 0  stdout_lines 50
    stdout: 3807	1	2021-10-10T02:33:16.760000+00:00	transcript	transcript-00003807	Schema Projekt wir release Vertrag. | 3807	2	2021-10-10T02:33:16.760000+00:00	transcript	transcript-00003807	Plone next please Ve
    stderr: output truncated at 50 lines; raise --limit or narrow --since/--until
venv chronicle-window #2     wall    0.285 s  maxrss    59.6 MiB  rc 0  stdout_lines 50
    stdout: 3807	1	2021-10-10T02:33:16.760000+00:00	transcript	transcript-00003807	Schema Projekt wir release Vertrag. | 3807	2	2021-10-10T02:33:16.760000+00:00	transcript	transcript-00003807	Plone next please Ve
    stderr: output truncated at 50 lines; raise --limit or narrow --since/--until
venv chronicle-window #3     wall    0.282 s  maxrss    59.7 MiB  rc 0  stdout_lines 50
    stdout: 3807	1	2021-10-10T02:33:16.760000+00:00	transcript	transcript-00003807	Schema Projekt wir release Vertrag. | 3807	2	2021-10-10T02:33:16.760000+00:00	transcript	transcript-00003807	Plone next please Ve
    stderr: output truncated at 50 lines; raise --limit or narrow --since/--until
uv stats #1                  wall    0.297 s  maxrss    59.6 MiB  rc 0  stdout_lines 4
    stdout: chat	1466	2952	2021-09-28T08:17:10.480000+00:00	2021-10-22T01:59:46.040000+00:00 | mail	7081	45238	2021-09-28T05:28:54.560000+00:00	2021-10-22T02:42:47.360000+00:00
uv stats #2                  wall    0.282 s  maxrss    59.5 MiB  rc 0  stdout_lines 4
    stdout: chat	1466	2952	2021-09-28T08:17:10.480000+00:00	2021-10-22T01:59:46.040000+00:00 | mail	7081	45238	2021-09-28T05:28:54.560000+00:00	2021-10-22T02:42:47.360000+00:00
uv stats #3                  wall    0.281 s  maxrss    59.5 MiB  rc 0  stdout_lines 4
    stdout: chat	1466	2952	2021-09-28T08:17:10.480000+00:00	2021-10-22T01:59:46.040000+00:00 | mail	7081	45238	2021-09-28T05:28:54.560000+00:00	2021-10-22T02:42:47.360000+00:00
venv stats #1                wall    0.284 s  maxrss    59.4 MiB  rc 0  stdout_lines 4
    stdout: chat	1466	2952	2021-09-28T08:17:10.480000+00:00	2021-10-22T01:59:46.040000+00:00 | mail	7081	45238	2021-09-28T05:28:54.560000+00:00	2021-10-22T02:42:47.360000+00:00
venv stats #2                wall    0.351 s  maxrss    59.4 MiB  rc 0  stdout_lines 4
    stdout: chat	1466	2952	2021-09-28T08:17:10.480000+00:00	2021-10-22T01:59:46.040000+00:00 | mail	7081	45238	2021-09-28T05:28:54.560000+00:00	2021-10-22T02:42:47.360000+00:00
venv stats #3                wall    0.277 s  maxrss    59.5 MiB  rc 0  stdout_lines 4
    stdout: chat	1466	2952	2021-09-28T08:17:10.480000+00:00	2021-10-22T01:59:46.040000+00:00 | mail	7081	45238	2021-09-28T05:28:54.560000+00:00	2021-10-22T02:42:47.360000+00:00
project (up to date)         wall    0.278 s  maxrss    59.6 MiB  rc 0  stdout_lines 2
    stdout: chronicle       up to date, up_to_id 10000 | source-stats    up to date, up_to_id 10000
catch-up 1000 #1             wall    0.653 s  maxrss    73.9 MiB  rc 0  stdout_lines 2
    stdout: chronicle       caught up: 1000 events, up_to_id 11000 | source-stats    caught up: 1000 events, up_to_id 11000
catch-up 1000 #2             wall    0.631 s  maxrss    73.8 MiB  rc 0  stdout_lines 2
    stdout: chronicle       caught up: 1000 events, up_to_id 12000 | source-stats    caught up: 1000 events, up_to_id 12000
catch-up 1000 #3             wall    0.602 s  maxrss    73.7 MiB  rc 0  stdout_lines 2
    stdout: chronicle       caught up: 1000 events, up_to_id 13000 | source-stats    caught up: 1000 events, up_to_id 13000
=== size 10000 done, log now 13000
--- catch_up chronicle (13000 events): wall 3.54 s
    storage.insert_chronicle             2.13 s   60.1 %  calls 26
    storage.units_by_event               0.39 s   11.0 %  calls 26
    storage.read                         0.28 s    7.9 %  calls 26
    chronicle.derive (pure)              0.13 s    3.6 %  calls 26
    storage.source_keys                  0.09 s    2.5 %  calls 26
    storage.set_projection_state         0.02 s    0.7 %  calls 27
    storage.tip                          0.02 s    0.6 %  calls 27
    storage.projection_state             0.00 s    0.0 %  calls 1
    storage.truncate_projection          0.00 s    0.0 %  calls 1
--- catch_up source-stats (13000 events): wall 0.91 s
    storage.units_by_event               0.36 s   40.0 %  calls 26
    storage.read                         0.26 s   29.0 %  calls 26
    storage.source_keys                  0.08 s    8.9 %  calls 26
    source_stats.derive (pure)           0.03 s    2.8 %  calls 26
    storage.upsert_source_stats          0.02 s    2.2 %  calls 26
    storage.source_stats                 0.02 s    1.8 %  calls 26
    storage.tip                          0.01 s    1.5 %  calls 27
    storage.set_projection_state         0.01 s    1.4 %  calls 27
    storage.projection_state             0.00 s    0.1 %  calls 1
    storage.truncate_projection          0.00 s    0.0 %  calls 1
--- examine (0 findings, tip 13000): wall 1.66 s
    units_hash (pure)                    0.48 s   28.8 %  calls 13000
    storage.units_by_event               0.38 s   23.1 %  calls 13
    storage.read                         0.29 s   17.2 %  calls 14
    event_hash (pure)                    0.21 s   12.9 %  calls 13000
    payload_hash (pure)                  0.15 s    9.3 %  calls 13000
    storage.source_keys                  0.09 s    5.4 %  calls 13
    storage.count_events                 0.00 s    0.1 %  calls 1
maxrss 108 MiB
2026-10-04T17:34:08+02:00
````

### Rohausgabe `size100k.sh` (`out-100k.txt`, ohne die `stdout:`/`stderr:`-Echozeilen)

````
2026-10-04T17:34:21+02:00
 17:34:21 up 2 days,  6:51,  1 user,  load average: 3,63, 2,06, 1,64
loaded ids 13001..100000: 87000 events, 638800 units, 130.9 MB text, batch 500
  generate+split 5.67 s; append 108.80 s = 800 events/s, 5871 units/s; maxrss 65 MiB
=== size 100000: 734303 unit rows
    event: 153 MB
    p_chronicle: 36 MB
    source_key: 15 MB
    unit: 197 MB
rebuild #1                   wall   38.879 s  maxrss   106.9 MiB  rc 0  stdout_lines 2
rebuild #2                   wall   38.768 s  maxrss   106.2 MiB  rc 0  stdout_lines 2
rebuild #3                   wall   42.193 s  maxrss   105.0 MiB  rc 0  stdout_lines 2
    p_chronicle rows after rebuild: 734303
    p_chronicle: 278 MB
verify #1                    wall   12.535 s  maxrss   107.0 MiB  rc 0  stdout_lines 1
verify #2                    wall   12.471 s  maxrss   107.5 MiB  rc 0  stdout_lines 1
verify #3                    wall   12.400 s  maxrss   107.2 MiB  rc 0  stdout_lines 1
    window 2021-12-31T06:34:44.920000+00:00 .. 2022-01-01T06:34:44.920000+00:00: 4146 chronicle rows in it
uv help #1                   wall    0.212 s  maxrss    44.1 MiB  rc 0  stdout_lines 16
uv help #2                   wall    0.230 s  maxrss    44.1 MiB  rc 0  stdout_lines 16
uv help #3                   wall    0.217 s  maxrss    44.1 MiB  rc 0  stdout_lines 16
venv help #1                 wall    0.200 s  maxrss    44.1 MiB  rc 0  stdout_lines 16
venv help #2                 wall    0.200 s  maxrss    44.1 MiB  rc 0  stdout_lines 16
venv help #3                 wall    0.195 s  maxrss    44.1 MiB  rc 0  stdout_lines 16
uv chronicle #1              wall    0.287 s  maxrss    59.6 MiB  rc 0  stdout_lines 50
uv chronicle #2              wall    0.294 s  maxrss    59.4 MiB  rc 0  stdout_lines 50
uv chronicle #3              wall    0.287 s  maxrss    59.7 MiB  rc 0  stdout_lines 50
venv chronicle #1            wall    0.266 s  maxrss    59.7 MiB  rc 0  stdout_lines 50
venv chronicle #2            wall    0.270 s  maxrss    59.7 MiB  rc 0  stdout_lines 50
venv chronicle #3            wall    0.273 s  maxrss    59.8 MiB  rc 0  stdout_lines 50
uv chronicle-window #1       wall    0.297 s  maxrss    59.7 MiB  rc 0  stdout_lines 50
uv chronicle-window #2       wall    0.286 s  maxrss    59.6 MiB  rc 0  stdout_lines 50
uv chronicle-window #3       wall    0.293 s  maxrss    59.7 MiB  rc 0  stdout_lines 50
venv chronicle-window #1     wall    0.284 s  maxrss    59.5 MiB  rc 0  stdout_lines 50
venv chronicle-window #2     wall    0.274 s  maxrss    59.4 MiB  rc 0  stdout_lines 50
venv chronicle-window #3     wall    0.283 s  maxrss    59.6 MiB  rc 0  stdout_lines 50
uv stats #1                  wall    0.286 s  maxrss    59.6 MiB  rc 0  stdout_lines 4
uv stats #2                  wall    0.291 s  maxrss    59.6 MiB  rc 0  stdout_lines 4
uv stats #3                  wall    0.297 s  maxrss    59.2 MiB  rc 0  stdout_lines 4
venv stats #1                wall    0.270 s  maxrss    59.6 MiB  rc 0  stdout_lines 4
venv stats #2                wall    0.274 s  maxrss    59.5 MiB  rc 0  stdout_lines 4
venv stats #3                wall    0.268 s  maxrss    59.5 MiB  rc 0  stdout_lines 4
project (up to date)         wall    0.269 s  maxrss    59.4 MiB  rc 0  stdout_lines 2
catch-up 1000 #1             wall    0.611 s  maxrss    74.4 MiB  rc 0  stdout_lines 2
catch-up 1000 #2             wall    0.666 s  maxrss    73.7 MiB  rc 0  stdout_lines 2
catch-up 1000 #3             wall    0.676 s  maxrss    74.3 MiB  rc 0  stdout_lines 2
=== size 100000 done, log now 103000
--- catch_up chronicle (103000 events): wall 32.39 s
    storage.insert_chronicle            18.10 s   55.9 %  calls 206
    storage.units_by_event               3.23 s   10.0 %  calls 206
    storage.read                         2.41 s    7.5 %  calls 206
    chronicle.derive (pure)              1.09 s    3.4 %  calls 206
    storage.source_keys                  0.73 s    2.3 %  calls 206
    storage.set_projection_state         0.17 s    0.5 %  calls 207
    storage.tip                          0.16 s    0.5 %  calls 207
    storage.projection_state             0.00 s    0.0 %  calls 1
    storage.truncate_projection          0.00 s    0.0 %  calls 1
--- catch_up source-stats (103000 events): wall 9.46 s
    storage.units_by_event               3.44 s   36.4 %  calls 206
    storage.read                         2.52 s   26.7 %  calls 206
    storage.source_keys                  0.78 s    8.3 %  calls 206
    source_stats.derive (pure)           0.23 s    2.4 %  calls 206
    storage.upsert_source_stats          0.17 s    1.8 %  calls 206
    storage.source_stats                 0.14 s    1.5 %  calls 206
    storage.tip                          0.12 s    1.3 %  calls 207
    storage.set_projection_state         0.09 s    1.0 %  calls 207
    storage.truncate_projection          0.00 s    0.0 %  calls 1
    storage.projection_state             0.00 s    0.0 %  calls 1
--- examine (0 findings, tip 103000): wall 13.30 s
    units_hash (pure)                    3.86 s   29.0 %  calls 103000
    storage.units_by_event               3.02 s   22.7 %  calls 103
    storage.read                         2.32 s   17.4 %  calls 104
    event_hash (pure)                    1.70 s   12.8 %  calls 103000
    payload_hash (pure)                  1.24 s    9.3 %  calls 103000
    storage.source_keys                  0.69 s    5.2 %  calls 103
    storage.count_events                 0.01 s    0.1 %  calls 1
maxrss 111 MiB
2026-10-04T17:40:09+02:00
````

### Rohausgabe `size700k.sh` (`out-700k.txt`, ohne die `stdout:`/`stderr:`-Echozeilen)

````
2026-10-04T17:40:32+02:00
 17:40:32 up 2 days,  6:57,  1 user,  load average: 6,00, 4,36, 2,80
  .. 203000: last 100k appended in 134.5 s
  .. 303000: last 100k appended in 128.0 s
  .. 403000: last 100k appended in 133.4 s
  .. 503000: last 100k appended in 137.7 s
  .. 603000: last 100k appended in 159.9 s
loaded ids 103001..700000: 597000 events, 4380806 units, 897.2 MB text, batch 500
  generate+split 41.92 s; append 840.46 s = 710 events/s, 5212 units/s; maxrss 65 MiB
2026-10-04T17:55:16+02:00
 17:55:16 up 2 days,  7:12,  1 user,  load average: 5,62, 5,99, 4,60
=== size 700000: 5137856 unit rows
    event: 1068 MB
    p_chronicle: 287 MB
    source_key: 103 MB
    unit: 1380 MB
rebuild #1                   wall  415.789 s  maxrss   107.2 MiB  rc 0  stdout_lines 2
rebuild #2                   wall  311.600 s  maxrss   106.7 MiB  rc 0  stdout_lines 2
rebuild #3                   wall  388.027 s  maxrss   107.8 MiB  rc 0  stdout_lines 2
    p_chronicle rows after rebuild: 5137856
    p_chronicle: 1947 MB
verify #1                    wall   88.770 s  maxrss   111.2 MiB  rc 0  stdout_lines 1
verify #2                    wall   93.739 s  maxrss   111.0 MiB  rc 0  stdout_lines 1
verify #3                    wall   95.468 s  maxrss   111.3 MiB  rc 0  stdout_lines 1
    window 2023-07-01T16:27:55.460000+00:00 .. 2023-07-02T16:27:55.460000+00:00: 4013 chronicle rows in it
uv help #1                   wall    0.246 s  maxrss    44.1 MiB  rc 0  stdout_lines 16
uv help #2                   wall    0.218 s  maxrss    44.2 MiB  rc 0  stdout_lines 16
uv help #3                   wall    0.231 s  maxrss    44.1 MiB  rc 0  stdout_lines 16
venv help #1                 wall    0.199 s  maxrss    44.2 MiB  rc 0  stdout_lines 16
venv help #2                 wall    0.201 s  maxrss    44.0 MiB  rc 0  stdout_lines 16
venv help #3                 wall    0.209 s  maxrss    43.8 MiB  rc 0  stdout_lines 16
uv chronicle #1              wall    0.300 s  maxrss    59.7 MiB  rc 0  stdout_lines 50
uv chronicle #2              wall    0.322 s  maxrss    59.4 MiB  rc 0  stdout_lines 50
uv chronicle #3              wall    0.292 s  maxrss    59.8 MiB  rc 0  stdout_lines 50
venv chronicle #1            wall    0.270 s  maxrss    59.8 MiB  rc 0  stdout_lines 50
venv chronicle #2            wall    0.275 s  maxrss    59.6 MiB  rc 0  stdout_lines 50
venv chronicle #3            wall    0.292 s  maxrss    59.2 MiB  rc 0  stdout_lines 50
uv chronicle-window #1       wall    0.290 s  maxrss    59.6 MiB  rc 0  stdout_lines 50
uv chronicle-window #2       wall    0.282 s  maxrss    59.7 MiB  rc 0  stdout_lines 50
uv chronicle-window #3       wall    0.304 s  maxrss    59.7 MiB  rc 0  stdout_lines 50
venv chronicle-window #1     wall    0.272 s  maxrss    59.6 MiB  rc 0  stdout_lines 50
venv chronicle-window #2     wall    0.267 s  maxrss    59.6 MiB  rc 0  stdout_lines 50
venv chronicle-window #3     wall    0.288 s  maxrss    59.5 MiB  rc 0  stdout_lines 50
uv stats #1                  wall    0.298 s  maxrss    59.5 MiB  rc 0  stdout_lines 4
uv stats #2                  wall    0.302 s  maxrss    59.6 MiB  rc 0  stdout_lines 4
uv stats #3                  wall    0.287 s  maxrss    59.6 MiB  rc 0  stdout_lines 4
venv stats #1                wall    0.283 s  maxrss    59.6 MiB  rc 0  stdout_lines 4
venv stats #2                wall    0.302 s  maxrss    59.2 MiB  rc 0  stdout_lines 4
venv stats #3                wall    0.306 s  maxrss    59.5 MiB  rc 0  stdout_lines 4
project (up to date)         wall    0.284 s  maxrss    59.4 MiB  rc 0  stdout_lines 2
catch-up 1000 #1             wall    0.708 s  maxrss    73.6 MiB  rc 0  stdout_lines 2
catch-up 1000 #2             wall    0.767 s  maxrss    74.4 MiB  rc 0  stdout_lines 2
catch-up 1000 #3             wall    0.740 s  maxrss    73.2 MiB  rc 0  stdout_lines 2
=== size 700000 done, log now 703000
--- verify #4 with pg_stat_activity polled beside it
no anchor given: verify attests that the log is unchanged, not that it is complete; see `previously anchor`
chain intact
verify #4 wall 111.60 s maxrss 113876 kB
111
18:19:09 pid 386 xact_age 0:00:00.996699 idle in transaction | FETCH FORWARD 100 FROM "c_7cebc910ae00_9"
18:19:10 pid 386 xact_age 0:00:01.997844 idle in transaction | FETCH FORWARD 100 FROM "c_7cebc84206b0_11"
18:19:11 pid 386 xact_age 0:00:03.000498 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
...
18:20:58 pid 386 xact_age 0:01:49.120369 active | FETCH FORWARD 100 FROM "c_7cebc8d6b680_2b3"
18:20:59 pid 386 xact_age 0:01:50.122563 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:21:00 pid 386 xact_age 0:01:51.123300 idle in transaction | CLOSE "c_7cebc956fbd0_2bf"
--- catch_up chronicle (703000 events): wall 284.91 s
    storage.insert_chronicle           168.79 s   59.2 %  calls 1406
    storage.units_by_event              27.71 s    9.7 %  calls 1406
    storage.read                        20.90 s    7.3 %  calls 1406
    chronicle.derive (pure)              9.77 s    3.4 %  calls 1406
    storage.source_keys                  6.39 s    2.2 %  calls 1406
    storage.set_projection_state         1.57 s    0.6 %  calls 1407
    storage.tip                          1.48 s    0.5 %  calls 1407
    storage.projection_state             0.00 s    0.0 %  calls 1
    storage.truncate_projection          0.00 s    0.0 %  calls 1
--- catch_up source-stats (703000 events): wall 65.36 s
    storage.units_by_event              23.54 s   36.0 %  calls 1406
    storage.read                        17.92 s   27.4 %  calls 1406
    storage.source_keys                  5.43 s    8.3 %  calls 1406
    source_stats.derive (pure)           1.65 s    2.5 %  calls 1406
    storage.upsert_source_stats          1.21 s    1.9 %  calls 1406
    storage.source_stats                 1.11 s    1.7 %  calls 1406
    storage.tip                          1.07 s    1.6 %  calls 1407
    storage.set_projection_state         0.72 s    1.1 %  calls 1407
    storage.projection_state             0.00 s    0.0 %  calls 1
    storage.truncate_projection          0.00 s    0.0 %  calls 1
--- examine (0 findings, tip 703000): wall 96.00 s
    units_hash (pure)                   27.71 s   28.9 %  calls 703000
    storage.units_by_event              21.36 s   22.3 %  calls 703
    storage.read                        17.21 s   17.9 %  calls 704
    event_hash (pure)                   12.41 s   12.9 %  calls 703000
    payload_hash (pure)                  8.93 s    9.3 %  calls 703000
    storage.source_keys                  5.00 s    5.2 %  calls 703
    storage.count_events                 0.03 s    0.0 %  calls 1
maxrss 111 MiB
2026-10-04T18:28:27+02:00
 18:28:27 up 2 days,  7:45,  1 user,  load average: 3,63, 6,21, 6,68
````

### Rohausgabe `xactpoll-700k.txt` (alle 111 Zeilen)

````
18:19:09 pid 386 xact_age 0:00:00.996699 idle in transaction | FETCH FORWARD 100 FROM "c_7cebc910ae00_9"
18:19:10 pid 386 xact_age 0:00:01.997844 idle in transaction | FETCH FORWARD 100 FROM "c_7cebc84206b0_11"
18:19:11 pid 386 xact_age 0:00:03.000498 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:12 pid 386 xact_age 0:00:04.001545 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:13 pid 386 xact_age 0:00:05.002277 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:14 pid 386 xact_age 0:00:06.003192 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:15 pid 386 xact_age 0:00:07.003986 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:16 pid 386 xact_age 0:00:08.004879 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:17 pid 386 xact_age 0:00:09.005775 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:18 pid 386 xact_age 0:00:10.009124 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:19 pid 386 xact_age 0:00:11.009957 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:20 pid 386 xact_age 0:00:12.010843 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:21 pid 386 xact_age 0:00:13.011690 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:22 pid 386 xact_age 0:00:14.012531 idle in transaction | CLOSE "c_7cebc866b680_57"
18:19:23 pid 386 xact_age 0:00:15.013294 idle in transaction | FETCH FORWARD 100 FROM "c_7cebc9529480_5c"
18:19:24 pid 386 xact_age 0:00:16.015813 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:25 pid 386 xact_age 0:00:17.016692 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:26 pid 386 xact_age 0:00:18.017589 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:27 pid 386 xact_age 0:00:19.021844 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:28 pid 386 xact_age 0:00:20.022734 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:29 pid 386 xact_age 0:00:21.023491 idle in transaction | FETCH FORWARD 100 FROM "c_7cebc8692140_79"
18:19:30 pid 386 xact_age 0:00:22.024325 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:31 pid 386 xact_age 0:00:23.025175 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:32 pid 386 xact_age 0:00:24.026797 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:33 pid 386 xact_age 0:00:25.027660 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:34 pid 386 xact_age 0:00:26.029741 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:35 pid 386 xact_age 0:00:27.030535 idle in transaction | CLOSE "c_7cebc952b350_95"
18:19:36 pid 386 xact_age 0:00:28.035804 idle in transaction | FETCH FORWARD 100 FROM "c_7cebc952bce0_9a"
18:19:37 pid 386 xact_age 0:00:29.036620 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:38 pid 386 xact_age 0:00:30.037404 active | FETCH FORWARD 100 FROM "c_7cebc8746140_a3"
18:19:39 pid 386 xact_age 0:00:31.038241 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:40 pid 386 xact_age 0:00:32.039234 idle in transaction | FETCH FORWARD 100 FROM "c_7cebc915dae0_ac"
18:19:41 pid 386 xact_age 0:00:33.040300 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:42 pid 386 xact_age 0:00:34.043838 idle in transaction | SELECT source_key.event_id, source_key.source, source_key.external_id 
18:19:43 pid 386 xact_age 0:00:35.046882 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:44 pid 386 xact_age 0:00:36.047924 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:45 pid 386 xact_age 0:00:37.048963 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:46 pid 386 xact_age 0:00:38.050152 idle in transaction | FETCH FORWARD 100 FROM "c_7cebc9199ae0_c4"
18:19:47 pid 386 xact_age 0:00:39.051106 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:48 pid 386 xact_age 0:00:40.055614 idle in transaction | FETCH FORWARD 100 FROM "c_7cebc9198f30_cc"
18:19:49 pid 386 xact_age 0:00:41.056580 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:50 pid 386 xact_age 0:00:42.057623 idle in transaction | FETCH FORWARD 100 FROM "c_7cebc89e3df0_d4"
18:19:51 pid 386 xact_age 0:00:43.058583 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:52 pid 386 xact_age 0:00:44.059469 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:53 pid 386 xact_age 0:00:45.061983 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:54 pid 386 xact_age 0:00:46.063064 idle in transaction | FETCH FORWARD 100 FROM "c_7cebc89f2580_e5"
18:19:55 pid 386 xact_age 0:00:47.064764 idle in transaction | DECLARE "c_7cebc9582470_e9" CURSOR FOR SELECT event.id, event.kind, ev
18:19:56 pid 386 xact_age 0:00:48.065570 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:57 pid 386 xact_age 0:00:49.069142 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:58 pid 386 xact_age 0:00:50.070256 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:19:59 pid 386 xact_age 0:00:51.071814 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:00 pid 386 xact_age 0:00:52.072713 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:01 pid 386 xact_age 0:00:53.073776 active | SELECT source_key.event_id, source_key.source, source_key.external_id 
18:20:02 pid 386 xact_age 0:00:54.074588 active | FETCH FORWARD 100 FROM "c_7cebc89f2ad0_107"
18:20:03 pid 386 xact_age 0:00:55.075378 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:04 pid 386 xact_age 0:00:56.076194 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:05 pid 386 xact_age 0:00:57.078973 idle in transaction | FETCH FORWARD 100 FROM "c_7cebc89f2be0_118"
18:20:06 pid 386 xact_age 0:00:58.080306 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:07 pid 386 xact_age 0:00:59.081026 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:08 pid 386 xact_age 0:01:00.081921 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:09 pid 386 xact_age 0:01:01.082993 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:10 pid 386 xact_age 0:01:02.084897 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:11 pid 386 xact_age 0:01:03.085471 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:12 pid 386 xact_age 0:01:04.086355 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:13 pid 386 xact_age 0:01:05.087831 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:14 pid 386 xact_age 0:01:06.088782 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:15 pid 386 xact_age 0:01:07.089691 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:16 pid 386 xact_age 0:01:08.090764 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:17 pid 386 xact_age 0:01:09.091628 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:18 pid 386 xact_age 0:01:10.092268 active | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:19 pid 386 xact_age 0:01:11.092944 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:20 pid 386 xact_age 0:01:12.093837 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:21 pid 386 xact_age 0:01:13.094756 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:22 pid 386 xact_age 0:01:14.095336 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:23 pid 386 xact_age 0:01:15.095889 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:24 pid 386 xact_age 0:01:16.096772 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:25 pid 386 xact_age 0:01:17.097373 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:26 pid 386 xact_age 0:01:18.098113 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:27 pid 386 xact_age 0:01:19.098713 idle in transaction | SELECT source_key.event_id, source_key.source, source_key.external_id 
18:20:28 pid 386 xact_age 0:01:20.099319 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:29 pid 386 xact_age 0:01:21.100048 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:30 pid 386 xact_age 0:01:22.100858 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:31 pid 386 xact_age 0:01:23.101422 active | FETCH FORWARD 100 FROM "c_7cebc8994c00_1ec"
18:20:32 pid 386 xact_age 0:01:24.102094 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:33 pid 386 xact_age 0:01:25.102950 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:35 pid 386 xact_age 0:01:26.103677 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:36 pid 386 xact_age 0:01:27.104523 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:37 pid 386 xact_age 0:01:28.105611 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:38 pid 386 xact_age 0:01:29.106336 active | FETCH FORWARD 100 FROM "c_7cebc9d12e00_21d"
18:20:39 pid 386 xact_age 0:01:30.107249 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:40 pid 386 xact_age 0:01:31.108150 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:41 pid 386 xact_age 0:01:32.108886 active | FETCH FORWARD 100 FROM "c_7cebca1f4f30_235"
18:20:42 pid 386 xact_age 0:01:33.109608 idle in transaction | CLOSE "c_7cebc95cdae0_23d"
18:20:43 pid 386 xact_age 0:01:34.110310 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:44 pid 386 xact_age 0:01:35.110998 active | FETCH FORWARD 100 FROM "c_7cebc9de3680_24e"
18:20:45 pid 386 xact_age 0:01:36.111558 active | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:46 pid 386 xact_age 0:01:37.112160 active | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:47 pid 386 xact_age 0:01:38.112736 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:48 pid 386 xact_age 0:01:39.113402 idle in transaction | SELECT source_key.event_id, source_key.source, source_key.external_id 
18:20:49 pid 386 xact_age 0:01:40.113932 idle in transaction | SELECT source_key.event_id, source_key.source, source_key.external_id 
18:20:50 pid 386 xact_age 0:01:41.114477 idle in transaction | FETCH FORWARD 100 FROM "c_7cebc95b6580_27e"
18:20:51 pid 386 xact_age 0:01:42.115023 idle in transaction | SELECT source_key.event_id, source_key.source, source_key.external_id 
18:20:52 pid 386 xact_age 0:01:43.115598 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:53 pid 386 xact_age 0:01:44.116197 idle in transaction | FETCH FORWARD 100 FROM "c_7cebc956d370_295"
18:20:54 pid 386 xact_age 0:01:45.116775 idle in transaction | CLOSE "c_7cebc95cdd00_29d"
18:20:55 pid 386 xact_age 0:01:46.117467 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:56 pid 386 xact_age 0:01:47.118189 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:57 pid 386 xact_age 0:01:48.119543 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:20:58 pid 386 xact_age 0:01:49.120369 active | FETCH FORWARD 100 FROM "c_7cebc8d6b680_2b3"
18:20:59 pid 386 xact_age 0:01:50.122563 idle in transaction | SELECT unit.event_id, unit.seq, unit.content, unit.start_ms, unit.end_
18:21:00 pid 386 xact_age 0:01:51.123300 idle in transaction | CLOSE "c_7cebc956fbd0_2bf"
````

### Rohausgabe `during.sh` (`out-during.txt`, vollständig)

````
2026-10-04T18:28:55+02:00
 18:28:55 up 2 days,  7:45,  1 user,  load average: 2,92, 5,79, 6,53
18:28:55 log tip 703000; projection_state [('chronicle', 703000, 1), ('source-stats', 703000, 1)]
baseline appends (no rebuild): n=1198 median 8.7 ms  p95 13.0 ms  max 27.2 ms  min 5.2 ms
  baseline errors: []
18:29:55 forced: [('chronicle', 703000, 0), ('source-stats', 703000, 0)]
18:29:57 rebuild started (pid 2946774)
  [18:30:01 during rebuild] chronicle rc 0: 50 lines, first event_id 15; stderr: 'output truncated at 50 lines; raise --limit or narrow --since/--until\nprojection is 1274 events behind; run `previously project`'
  [18:30:01 during rebuild] stats rc 0: 'chat\t105371\t210739\t2021-09-28T08:17:10.480000+00:00\t2025-04-08T09:00:09.360000+00:00\nmail\t492137\t3153405\t2021-09-28T05:28:54.560000+00:00\t2025-04-08T17:35:14.680000+00:00\nnotes\t34968\t104525\t2021-09-28T02:21:15.200000+00:00\t2025-04-08T04:57:31.960000+00:00\ntranscript\t70524\t1690949\t2021-09-28T19:03:17.200000+00:00\t2025-04-07T15:07:09.960000+00:00'; stderr: 'projection is 1278 events behind; run `previously project`'
  [18:30:01 during rebuild] projection_state [('chronicle', 703000, 0), ('source-stats', 703000, 0)]
  [18:30:17 during rebuild] chronicle rc 0: 50 lines, first event_id 15; stderr: 'output truncated at 50 lines; raise --limit or narrow --since/--until\nprojection is 1426 events behind; run `previously project`'
  [18:30:17 during rebuild] stats rc 0: 'chat\t105371\t210739\t2021-09-28T08:17:10.480000+00:00\t2025-04-08T09:00:09.360000+00:00\nmail\t492137\t3153405\t2021-09-28T05:28:54.560000+00:00\t2025-04-08T17:35:14.680000+00:00\nnotes\t34968\t104525\t2021-09-28T02:21:15.200000+00:00\t2025-04-08T04:57:31.960000+00:00\ntranscript\t70524\t1690949\t2021-09-28T19:03:17.200000+00:00\t2025-04-07T15:07:09.960000+00:00'; stderr: 'projection is 1431 events behind; run `previously project`'
  [18:30:17 during rebuild] projection_state [('chronicle', 703000, 0), ('source-stats', 703000, 0)]
  [18:30:33 during rebuild] chronicle rc 0: 50 lines, first event_id 15; stderr: 'output truncated at 50 lines; raise --limit or narrow --since/--until\nprojection is 694605 events behind; run `previously project`'
  [18:30:33 during rebuild] stats rc 0: 'chat\t105371\t210739\t2021-09-28T08:17:10.480000+00:00\t2025-04-08T09:00:09.360000+00:00\nmail\t492137\t3153405\t2021-09-28T05:28:54.560000+00:00\t2025-04-08T17:35:14.680000+00:00\nnotes\t34968\t104525\t2021-09-28T02:21:15.200000+00:00\t2025-04-08T04:57:31.960000+00:00\ntranscript\t70524\t1690949\t2021-09-28T19:03:17.200000+00:00\t2025-04-07T15:07:09.960000+00:00'; stderr: 'projection is 1612 events behind; run `previously project`'
  [18:30:33 during rebuild] projection_state [('chronicle', 11500, 1), ('source-stats', 703000, 0)]
  [18:30:49 during rebuild] chronicle rc 0: 50 lines, first event_id 15; stderr: 'output truncated at 50 lines; raise --limit or narrow --since/--until\nprojection is 644913 events behind; run `previously project`'
  [18:30:49 during rebuild] stats rc 0: 'chat\t105371\t210739\t2021-09-28T08:17:10.480000+00:00\t2025-04-08T09:00:09.360000+00:00\nmail\t492137\t3153405\t2021-09-28T05:28:54.560000+00:00\t2025-04-08T17:35:14.680000+00:00\nnotes\t34968\t104525\t2021-09-28T02:21:15.200000+00:00\t2025-04-08T04:57:31.960000+00:00\ntranscript\t70524\t1690949\t2021-09-28T19:03:17.200000+00:00\t2025-04-07T15:07:09.960000+00:00'; stderr: 'projection is 1921 events behind; run `previously project`'
  [18:30:49 during rebuild] projection_state [('chronicle', 61000, 1), ('source-stats', 703000, 0)]
  [18:31:04 during rebuild] chronicle rc 0: 50 lines, first event_id 15; stderr: 'output truncated at 50 lines; raise --limit or narrow --since/--until\nprojection is 610193 events behind; run `previously project`'
  [18:31:04 during rebuild] stats rc 0: 'chat\t105371\t210739\t2021-09-28T08:17:10.480000+00:00\t2025-04-08T09:00:09.360000+00:00\nmail\t492137\t3153405\t2021-09-28T05:28:54.560000+00:00\t2025-04-08T17:35:14.680000+00:00\nnotes\t34968\t104525\t2021-09-28T02:21:15.200000+00:00\t2025-04-08T04:57:31.960000+00:00\ntranscript\t70524\t1690949\t2021-09-28T19:03:17.200000+00:00\t2025-04-07T15:07:09.960000+00:00'; stderr: 'projection is 2200 events behind; run `previously project`'
  [18:31:04 during rebuild] projection_state [('chronicle', 96500, 1), ('source-stats', 703000, 0)]
  [18:31:20 during rebuild] chronicle rc 0: 50 lines, first event_id 15; stderr: 'output truncated at 50 lines; raise --limit or narrow --since/--until\nprojection is 564506 events behind; run `previously project`'
  [18:31:20 during rebuild] stats rc 0: 'chat\t105371\t210739\t2021-09-28T08:17:10.480000+00:00\t2025-04-08T09:00:09.360000+00:00\nmail\t492137\t3153405\t2021-09-28T05:28:54.560000+00:00\t2025-04-08T17:35:14.680000+00:00\nnotes\t34968\t104525\t2021-09-28T02:21:15.200000+00:00\t2025-04-08T04:57:31.960000+00:00\ntranscript\t70524\t1690949\t2021-09-28T19:03:17.200000+00:00\t2025-04-07T15:07:09.960000+00:00'; stderr: 'projection is 2512 events behind; run `previously project`'
  [18:31:20 during rebuild] projection_state [('chronicle', 142500, 1), ('source-stats', 703000, 0)]
  [18:31:36 during rebuild] chronicle rc 0: 50 lines, first event_id 15; stderr: 'output truncated at 50 lines; raise --limit or narrow --since/--until\nprojection is 519805 events behind; run `previously project`'
  [18:31:36 during rebuild] stats rc 0: 'chat\t105371\t210739\t2021-09-28T08:17:10.480000+00:00\t2025-04-08T09:00:09.360000+00:00\nmail\t492137\t3153405\t2021-09-28T05:28:54.560000+00:00\t2025-04-08T17:35:14.680000+00:00\nnotes\t34968\t104525\t2021-09-28T02:21:15.200000+00:00\t2025-04-08T04:57:31.960000+00:00\ntranscript\t70524\t1690949\t2021-09-28T19:03:17.200000+00:00\t2025-04-07T15:07:09.960000+00:00'; stderr: 'projection is 2812 events behind; run `previously project`'
  [18:31:36 during rebuild] projection_state [('chronicle', 187000, 1), ('source-stats', 703000, 0)]
  [18:31:52 during rebuild] chronicle rc 0: 50 lines, first event_id 15; stderr: 'output truncated at 50 lines; raise --limit or narrow --since/--until\nprojection is 488001 events behind; run `previously project`'
  [18:31:52 during rebuild] stats rc 0: 'chat\t105371\t210739\t2021-09-28T08:17:10.480000+00:00\t2025-04-08T09:00:09.360000+00:00\nmail\t492137\t3153405\t2021-09-28T05:28:54.560000+00:00\t2025-04-08T17:35:14.680000+00:00\nnotes\t34968\t104525\t2021-09-28T02:21:15.200000+00:00\t2025-04-08T04:57:31.960000+00:00\ntranscript\t70524\t1690949\t2021-09-28T19:03:17.200000+00:00\t2025-04-07T15:07:09.960000+00:00'; stderr: 'projection is 3008 events behind; run `previously project`'
  [18:31:52 during rebuild] projection_state [('chronicle', 219000, 1), ('source-stats', 703000, 0)]
  [18:32:09 during rebuild] chronicle rc 0: 50 lines, first event_id 15; stderr: 'output truncated at 50 lines; raise --limit or narrow --since/--until\nprojection is 443759 events behind; run `previously project`'
  [18:32:09 during rebuild] stats rc 0: 'chat\t105371\t210739\t2021-09-28T08:17:10.480000+00:00\t2025-04-08T09:00:09.360000+00:00\nmail\t492137\t3153405\t2021-09-28T05:28:54.560000+00:00\t2025-04-08T17:35:14.680000+00:00\nnotes\t34968\t104525\t2021-09-28T02:21:15.200000+00:00\t2025-04-08T04:57:31.960000+00:00\ntranscript\t70524\t1690949\t2021-09-28T19:03:17.200000+00:00\t2025-04-07T15:07:09.960000+00:00'; stderr: 'projection is 3261 events behind; run `previously project`'
  [18:32:09 during rebuild] projection_state [('chronicle', 263000, 1), ('source-stats', 703000, 0)]
  [18:32:25 during rebuild] chronicle rc 0: 50 lines, first event_id 15; stderr: 'output truncated at 50 lines; raise --limit or narrow --since/--until\nprojection is 414988 events behind; run `previously project`'
  [18:32:25 during rebuild] stats rc 0: 'chat\t105371\t210739\t2021-09-28T08:17:10.480000+00:00\t2025-04-08T09:00:09.360000+00:00\nmail\t492137\t3153405\t2021-09-28T05:28:54.560000+00:00\t2025-04-08T17:35:14.680000+00:00\nnotes\t34968\t104525\t2021-09-28T02:21:15.200000+00:00\t2025-04-08T04:57:31.960000+00:00\ntranscript\t70524\t1690949\t2021-09-28T19:03:17.200000+00:00\t2025-04-07T15:07:09.960000+00:00'; stderr: 'projection is 3494 events behind; run `previously project`'
  [18:32:25 during rebuild] projection_state [('chronicle', 292500, 1), ('source-stats', 703000, 0)]
  [18:32:40 during rebuild] chronicle rc 0: 50 lines, first event_id 15; stderr: 'output truncated at 50 lines; raise --limit or narrow --since/--until\nprojection is 364788 events behind; run `previously project`'
  [18:32:40 during rebuild] stats rc 0: 'chat\t105371\t210739\t2021-09-28T08:17:10.480000+00:00\t2025-04-08T09:00:09.360000+00:00\nmail\t492137\t3153405\t2021-09-28T05:28:54.560000+00:00\t2025-04-08T17:35:14.680000+00:00\nnotes\t34968\t104525\t2021-09-28T02:21:15.200000+00:00\t2025-04-08T04:57:31.960000+00:00\ntranscript\t70524\t1690949\t2021-09-28T19:03:17.200000+00:00\t2025-04-07T15:07:09.960000+00:00'; stderr: 'projection is 3795 events behind; run `previously project`'
  [18:32:40 during rebuild] projection_state [('chronicle', 343000, 1), ('source-stats', 703000, 0)]
  [18:32:56 during rebuild] chronicle rc 0: 50 lines, first event_id 15; stderr: 'output truncated at 50 lines; raise --limit or narrow --since/--until\nprojection is 332508 events behind; run `previously project`'
  [18:32:56 during rebuild] stats rc 0: 'chat\t105371\t210739\t2021-09-28T08:17:10.480000+00:00\t2025-04-08T09:00:09.360000+00:00\nmail\t492137\t3153405\t2021-09-28T05:28:54.560000+00:00\t2025-04-08T17:35:14.680000+00:00\nnotes\t34968\t104525\t2021-09-28T02:21:15.200000+00:00\t2025-04-08T04:57:31.960000+00:00\ntranscript\t70524\t1690949\t2021-09-28T19:03:17.200000+00:00\t2025-04-07T15:07:09.960000+00:00'; stderr: 'projection is 4015 events behind; run `previously project`'
  [18:32:56 during rebuild] projection_state [('chronicle', 375000, 1), ('source-stats', 703000, 0)]
  [18:33:12 during rebuild] chronicle rc 0: 50 lines, first event_id 15; stderr: 'output truncated at 50 lines; raise --limit or narrow --since/--until\nprojection is 292764 events behind; run `previously project`'
  [18:33:12 during rebuild] stats rc 0: 'chat\t105371\t210739\t2021-09-28T08:17:10.480000+00:00\t2025-04-08T09:00:09.360000+00:00\nmail\t492137\t3153405\t2021-09-28T05:28:54.560000+00:00\t2025-04-08T17:35:14.680000+00:00\nnotes\t34968\t104525\t2021-09-28T02:21:15.200000+00:00\t2025-04-08T04:57:31.960000+00:00\ntranscript\t70524\t1690949\t2021-09-28T19:03:17.200000+00:00\t2025-04-07T15:07:09.960000+00:00'; stderr: 'projection is 4265 events behind; run `previously project`'
  [18:33:12 during rebuild] projection_state [('chronicle', 414500, 1), ('source-stats', 703000, 0)]
  [18:33:28 during rebuild] chronicle rc 0: 50 lines, first event_id 15; stderr: 'output truncated at 50 lines; raise --limit or narrow --since/--until\nprojection is 245556 events behind; run `previously project`'
  [18:33:28 during rebuild] stats rc 0: 'chat\t105371\t210739\t2021-09-28T08:17:10.480000+00:00\t2025-04-08T09:00:09.360000+00:00\nmail\t492137\t3153405\t2021-09-28T05:28:54.560000+00:00\t2025-04-08T17:35:14.680000+00:00\nnotes\t34968\t104525\t2021-09-28T02:21:15.200000+00:00\t2025-04-08T04:57:31.960000+00:00\ntranscript\t70524\t1690949\t2021-09-28T19:03:17.200000+00:00\t2025-04-07T15:07:09.960000+00:00'; stderr: 'projection is 4563 events behind; run `previously project`'
  [18:33:28 during rebuild] projection_state [('chronicle', 463500, 1), ('source-stats', 703000, 0)]
  [18:33:44 during rebuild] chronicle rc 0: 50 lines, first event_id 15; stderr: 'output truncated at 50 lines; raise --limit or narrow --since/--until\nprojection is 210789 events behind; run `previously project`'
  [18:33:44 during rebuild] stats rc 0: 'chat\t105371\t210739\t2021-09-28T08:17:10.480000+00:00\t2025-04-08T09:00:09.360000+00:00\nmail\t492137\t3153405\t2021-09-28T05:28:54.560000+00:00\t2025-04-08T17:35:14.680000+00:00\nnotes\t34968\t104525\t2021-09-28T02:21:15.200000+00:00\t2025-04-08T04:57:31.960000+00:00\ntranscript\t70524\t1690949\t2021-09-28T19:03:17.200000+00:00\t2025-04-07T15:07:09.960000+00:00'; stderr: 'projection is 4797 events behind; run `previously project`'
  [18:33:44 during rebuild] projection_state [('chronicle', 498500, 1), ('source-stats', 703000, 0)]
  [18:33:59 during rebuild] chronicle rc 0: 50 lines, first event_id 15; stderr: 'output truncated at 50 lines; raise --limit or narrow --since/--until\nprojection is 160097 events behind; run `previously project`'
  [18:33:59 during rebuild] stats rc 0: 'chat\t105371\t210739\t2021-09-28T08:17:10.480000+00:00\t2025-04-08T09:00:09.360000+00:00\nmail\t492137\t3153405\t2021-09-28T05:28:54.560000+00:00\t2025-04-08T17:35:14.680000+00:00\nnotes\t34968\t104525\t2021-09-28T02:21:15.200000+00:00\t2025-04-08T04:57:31.960000+00:00\ntranscript\t70524\t1690949\t2021-09-28T19:03:17.200000+00:00\t2025-04-07T15:07:09.960000+00:00'; stderr: 'projection is 5104 events behind; run `previously project`'
  [18:33:59 during rebuild] projection_state [('chronicle', 549500, 1), ('source-stats', 703000, 0)]
  [18:34:15 during rebuild] chronicle rc 0: 50 lines, first event_id 15; stderr: 'output truncated at 50 lines; raise --limit or narrow --since/--until\nprojection is 117381 events behind; run `previously project`'
  [18:34:15 during rebuild] stats rc 0: 'chat\t105371\t210739\t2021-09-28T08:17:10.480000+00:00\t2025-04-08T09:00:09.360000+00:00\nmail\t492137\t3153405\t2021-09-28T05:28:54.560000+00:00\t2025-04-08T17:35:14.680000+00:00\nnotes\t34968\t104525\t2021-09-28T02:21:15.200000+00:00\t2025-04-08T04:57:31.960000+00:00\ntranscript\t70524\t1690949\t2021-09-28T19:03:17.200000+00:00\t2025-04-07T15:07:09.960000+00:00'; stderr: 'projection is 5387 events behind; run `previously project`'
  [18:34:15 during rebuild] projection_state [('chronicle', 592000, 1), ('source-stats', 703000, 0)]
  [18:34:31 during rebuild] chronicle rc 0: 50 lines, first event_id 15; stderr: 'output truncated at 50 lines; raise --limit or narrow --since/--until\nprojection is 78169 events behind; run `previously project`'
  [18:34:31 during rebuild] stats rc 0: 'chat\t105371\t210739\t2021-09-28T08:17:10.480000+00:00\t2025-04-08T09:00:09.360000+00:00\nmail\t492137\t3153405\t2021-09-28T05:28:54.560000+00:00\t2025-04-08T17:35:14.680000+00:00\nnotes\t34968\t104525\t2021-09-28T02:21:15.200000+00:00\t2025-04-08T04:57:31.960000+00:00\ntranscript\t70524\t1690949\t2021-09-28T19:03:17.200000+00:00\t2025-04-07T15:07:09.960000+00:00'; stderr: 'projection is 5676 events behind; run `previously project`'
  [18:34:31 during rebuild] projection_state [('chronicle', 632000, 1), ('source-stats', 703000, 0)]
  [18:34:47 during rebuild] chronicle rc 0: 50 lines, first event_id 15; stderr: 'output truncated at 50 lines; raise --limit or narrow --since/--until\nprojection is 23479 events behind; run `previously project`'
  [18:34:47 during rebuild] stats rc 0: 'chat\t105371\t210739\t2021-09-28T08:17:10.480000+00:00\t2025-04-08T09:00:09.360000+00:00\nmail\t492137\t3153405\t2021-09-28T05:28:54.560000+00:00\t2025-04-08T17:35:14.680000+00:00\nnotes\t34968\t104525\t2021-09-28T02:21:15.200000+00:00\t2025-04-08T04:57:31.960000+00:00\ntranscript\t70524\t1690949\t2021-09-28T19:03:17.200000+00:00\t2025-04-07T15:07:09.960000+00:00'; stderr: 'projection is 5987 events behind; run `previously project`'
  [18:34:47 during rebuild] projection_state [('chronicle', 686500, 1), ('source-stats', 703000, 0)]
  [18:35:02 during rebuild] chronicle rc 0: 50 lines, first event_id 15; stderr: 'output truncated at 50 lines; raise --limit or narrow --since/--until\nprojection is 152 events behind; run `previously project`'
  [18:35:02 during rebuild] stats rc 0: 'chat\t11908\t23868\t2021-09-28T08:17:10.480000+00:00\t2022-02-26T20:13:00.080000+00:00\nmail\t56272\t360399\t2021-09-28T05:28:54.560000+00:00\t2022-02-26T22:08:58.920000+00:00\nnotes\t3942\t11870\t2021-09-28T02:21:15.200000+00:00\t2022-02-25T21:59:40.080000+00:00\ntranscript\t7878\t189889\t2021-09-28T19:03:17.200000+00:00\t2022-02-26T12:03:25.920000+00:00'; stderr: 'projection is 629292 events behind; run `previously project`'
  [18:35:02 during rebuild] projection_state [('chronicle', 709132, 1), ('source-stats', 81000, 1)]
  [18:35:18 during rebuild] chronicle rc 0: 50 lines, first event_id 15; stderr: 'output truncated at 50 lines; raise --limit or narrow --since/--until\nprojection is 466 events behind; run `previously project`'
  [18:35:18 during rebuild] stats rc 0: 'chat\t37939\t75762\t2021-09-28T08:17:10.480000+00:00\t2023-01-10T02:32:33.200000+00:00\nmail\t177880\t1139800\t2021-09-28T05:28:54.560000+00:00\t2023-01-10T06:21:54.360000+00:00\nnotes\t12551\t37455\t2021-09-28T02:21:15.200000+00:00\t2023-01-09T21:00:46.920000+00:00\ntranscript\t25630\t618568\t2021-09-28T19:03:17.200000+00:00\t2023-01-10T01:53:15.360000+00:00'; stderr: 'projection is 455604 events behind; run `previously project`'
  [18:35:18 during rebuild] projection_state [('chronicle', 709132, 1), ('source-stats', 254500, 1)]
  [18:35:34 during rebuild] chronicle rc 0: 50 lines, first event_id 15; stderr: 'output truncated at 50 lines; raise --limit or narrow --since/--until\nprojection is 778 events behind; run `previously project`'
  [18:35:34 during rebuild] stats rc 0: 'chat\t64557\t128981\t2021-09-28T08:17:10.480000+00:00\t2023-11-28T15:41:00.280000+00:00\nmail\t301265\t1930468\t2021-09-28T05:28:54.560000+00:00\t2023-11-28T14:44:12.160000+00:00\nnotes\t21406\t64034\t2021-09-28T02:21:15.200000+00:00\t2023-11-28T02:47:52.640000+00:00\ntranscript\t43272\t1039062\t2021-09-28T19:03:17.200000+00:00\t2023-11-28T08:29:56+00:00'; stderr: 'projection is 279417 events behind; run `previously project`'
  [18:35:34 during rebuild] projection_state [('chronicle', 709132, 1), ('source-stats', 431500, 1)]
  [18:35:50 during rebuild] chronicle rc 0: 50 lines, first event_id 15; stderr: 'output truncated at 50 lines; raise --limit or narrow --since/--until\nprojection is 1011 events behind; run `previously project`'
  [18:35:50 during rebuild] stats rc 0: 'chat\t80158\t160145\t2021-09-28T08:17:10.480000+00:00\t2024-06-06T00:05:05+00:00\nmail\t374575\t2400129\t2021-09-28T05:28:54.560000+00:00\t2024-06-06T05:42:27+00:00\nnotes\t26619\t79540\t2021-09-28T02:21:15.200000+00:00\t2024-06-05T23:59:36.320000+00:00\ntranscript\t53648\t1286676\t2021-09-28T19:03:17.200000+00:00\t2024-06-06T03:32:44.560000+00:00'; stderr: 'projection is 175155 events behind; run `previously project`'
  [18:35:50 during rebuild] projection_state [('chronicle', 709132, 1), ('source-stats', 536000, 1)]
  [18:36:06 during rebuild] chronicle rc 0: 50 lines, first event_id 15; stderr: 'output truncated at 50 lines; raise --limit or narrow --since/--until\nprojection is 1304 events behind; run `previously project`'
  [18:36:06 during rebuild] stats rc 0: 'chat\t101991\t203929\t2021-09-28T08:17:10.480000+00:00\t2025-02-25T16:34:09.640000+00:00\nmail\t475974\t3049861\t2021-09-28T05:28:54.560000+00:00\t2025-02-25T20:58:17.600000+00:00\nnotes\t33821\t101140\t2021-09-28T02:21:15.200000+00:00\t2025-02-25T18:59:35.520000+00:00\ntranscript\t68214\t1636157\t2021-09-28T19:03:17.200000+00:00\t2025-02-25T09:51:05.160000+00:00'; stderr: 'projection is 30442 events behind; run `previously project`'
  [18:36:06 during rebuild] projection_state [('chronicle', 709132, 1), ('source-stats', 681000, 1)]
18:36:12 rebuild ended rc 0 after 374.9 s
  stdout: 'chronicle       built: 709132 events, up_to_id 709132\nsource-stats    built: 710517 events, up_to_id 710517'
  stderr: 'rebuild wall 374.04 s maxrss 110108 kB'
appends during rebuild: n=6379 median 13.8 ms  p95 85.6 ms  max 1391.9 ms  min 5.1 ms
  errors during rebuild: []
  [18:36:15 after rebuild, before catch-up] chronicle rc 0: 50 lines, first event_id 15; stderr: 'output truncated at 50 lines; raise --limit or narrow --since/--until\nprojection is 1445 events behind; run `previously project`'
  [18:36:15 after rebuild, before catch-up] stats rc 0: 'chat\t106562\t213120\t2021-09-28T08:17:10.480000+00:00\t2025-04-22T13:37:53.520000+00:00\nmail\t497388\t3186985\t2021-09-28T05:28:54.560000+00:00\t2025-04-22T11:05:42.360000+00:00\nnotes\t35317\t105590\t2021-09-28T02:21:15.200000+00:00\t2025-04-22T10:30:41.920000+00:00\ntranscript\t71250\t1708168\t2021-09-28T19:03:17.200000+00:00\t2025-04-22T05:37:31.360000+00:00'; stderr: 'projection is 60 events behind; run `previously project`'
  [18:36:15 after rebuild, before catch-up] projection_state [('chronicle', 709132, 1), ('source-stats', 710517, 1)]
18:36:15 catch-up rc 0: 'chronicle       caught up: 1445 events, up_to_id 710577\nsource-stats    caught up: 60 events, up_to_id 710577' ''
  [18:36:16 after catch-up] chronicle rc 0: 50 lines, first event_id 15; stderr: 'output truncated at 50 lines; raise --limit or narrow --since/--until'
  [18:36:16 after catch-up] stats rc 0: 'chat\t106572\t213139\t2021-09-28T08:17:10.480000+00:00\t2025-04-22T13:37:53.520000+00:00\nmail\t497429\t3187243\t2021-09-28T05:28:54.560000+00:00\t2025-04-22T12:01:46.840000+00:00\nnotes\t35319\t105597\t2021-09-28T02:21:15.200000+00:00\t2025-04-22T10:30:41.920000+00:00\ntranscript\t71257\t1708312\t2021-09-28T19:03:17.200000+00:00\t2025-04-22T05:37:31.360000+00:00'; stderr: ''
  [18:36:16 after catch-up] projection_state [('chronicle', 710577, 1), ('source-stats', 710577, 1)]
  in-place: p_chronicle (rows, distinct keys) (5214291, 5214291, Decimal('4217032151250')); unit rows in log 5214291
18:41:56 rebuild from nothing rc 0: 'chronicle       built: 710577 events, up_to_id 710577\nsource-stats    built: 710577 events, up_to_id 710577'
  fresh: p_chronicle (5214291, 5214291, Decimal('4217032151250'))
  stats equal: True
  in-place stats:
chat	106572	213139	2021-09-28T08:17:10.480000+00:00	2025-04-22T13:37:53.520000+00:00
mail	497429	3187243	2021-09-28T05:28:54.560000+00:00	2025-04-22T12:01:46.840000+00:00
notes	35319	105597	2021-09-28T02:21:15.200000+00:00	2025-04-22T10:30:41.920000+00:00
transcript	71257	1708312	2021-09-28T19:03:17.200000+00:00	2025-04-22T05:37:31.360000+00:00
  fresh stats:
chat	106572	213139	2021-09-28T08:17:10.480000+00:00	2025-04-22T13:37:53.520000+00:00
mail	497429	3187243	2021-09-28T05:28:54.560000+00:00	2025-04-22T12:01:46.840000+00:00
notes	35319	105597	2021-09-28T02:21:15.200000+00:00	2025-04-22T10:30:41.920000+00:00
transcript	71257	1708312	2021-09-28T19:03:17.200000+00:00	2025-04-22T05:37:31.360000+00:00

  chronicle counts equal: True
18:42:11 log tip now 710577
2026-10-04T18:42:11+02:00
 18:42:11 up 2 days,  7:59,  1 user,  load average: 4,51, 6,90, 6,99
````

### Weitere Abfragen

````
$ docker exec previously-messung-c psql -U previously -tAc "select name||'='||setting||coalesce(unit,'') from pg_settings where name in ('shared_buffers','max_wal_size','work_mem','synchronous_commit','checkpoint_timeout')"
checkpoint_timeout=300s
max_wal_size=1024MB
shared_buffers=163848kB   [setting 16384 und unit '8kB' ohne Trenner verkettet: 16384 x 8 kB = 128 MB]
synchronous_commit=on
work_mem=4096kB

$ psql: select num_timed, num_requested, buffers_written from pg_stat_checkpointer   (18:07, nach Neubau #2 bei 700.000)
 num_timed | num_requested | buffers_written
         0 |            33 |           87103

$ psql: select relname, last_autovacuum, last_autoanalyze, autovacuum_count, n_dead_tup from pg_stat_user_tables   (18:07)
 event            | 2026-10-04 15:54:15.958722+00 | 2026-10-04 15:54:16.919638+00 | 10 | 0
 p_chronicle      | 2026-10-04 16:06:22.711578+00 | 2026-10-04 16:06:23.841046+00 | 11 | 0
 p_source_stats   | 2026-10-04 16:02:10.977554+00 | 2026-10-04 16:07:11.068867+00 |  3 | 0
 projection_state | 2026-10-04 16:07:11.059926+00 | 2026-10-04 16:07:11.064983+00 | 12 | 121
 source_key       | 2026-10-04 15:55:21.331219+00 | 2026-10-04 15:54:19.024346+00 | 11 | 0
 unit             | 2026-10-04 15:55:21.069506+00 | 2026-10-04 15:54:18.681711+00 | 12 | 0

$ top -b -n1 -o %CPU   (18:07:41, Auszug)
load average: 6,53, 7,81, 6,79
2833744 jensens  ... 91,7 %CPU ... /usr/lib/firefox/firefox-bin -contentproc ...   (ps: ELAPSED 01:38:48)
2921677 jensens  ... 50,0 %CPU ... (der Neubau-Prozess)
2921678 dnsmasq  ... 25,0 %CPU ... postgres

$ psql: select pg_size_pretty(pg_database_size('previously'))   (am Ende, 710.577 Events)
4572 MB

$ docker rm -f previously-messung-c && docker ps -a --filter name=previously-messung-c --format '{{.Names}}' | wc -l
previously-messung-c
0
````
