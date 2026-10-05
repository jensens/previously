# Previously — Die Auslieferung: Paket, Image, Release

> **Eingefrorener Entwurfsbericht, Stand 2026-10-05.**
> Dieses Dokument wird nicht mehr nachgezogen.
> Es hält fest, **wie und warum** entschieden wurde, und bleibt dafür im
> Repository. Die lebende Begründung steht in der Dokumentation unter
> `docs/` — soweit sie dort steht; wo sie fehlt, ist dieses Dokument die
> einzige Quelle. Weicht es von der Doku ab, gilt die Doku.
>
> Ein neuer Spec für eine neue Stufe entsteht wieder auf Deutsch — das ist
> die Sprache, in der die Absicht formuliert wird. Er friert ein, sobald
> seine Explanation-Seiten stehen. Das Einfrieren als **Ablauf**, und die
> Karte von jedem zitierten Paragraphen zu seiner Seite, stehen in
> [About the frozen design records](../../explanation/design-records.md).

**Datum:** 2026-10-05
**Status:** eingefroren am 2026-10-05; zuvor Entwurf, vom Betreuer am
2026-10-05 durchgesehen, Grundlage des Plans
`docs/superpowers/plans/2026-10-05-auslieferung.md`

Detail-Spec für die erste Einheit des Piloten, die der Landkarte vom
2026-10-04 noch fehlte: der Weg vom Commit auf `main` zu einem Paket auf PyPI
und einem Image, das kup6s betreiben kann. Setzt die Stufen 1a, 1b, den
äußeren Anker und Stufe 1c voraus (auf `main` seit `d16f3fc`).

Dieser Spec friert ein, sobald seine Explanation-Seiten stehen (`CLAUDE.md`);
seine offenen Punkte gehen dann in die Landkarte.

---

## 1. Zweck und Zuschnitt

Der Betrieb in kup6s (Einheit 2 des Piloten) **beginnt beim Image**. Den
Cluster, die Datenbank, den Bucket und die Jobs baut der Agent in kup6s;
dieses Repository liefert das Image, aus dem er alles startet, und sagt ihm
in einem Handoff, was das Image braucht. Bis heute gibt es weder ein Paket
noch ein Image: Previously läuft nur aus einem Arbeitsverzeichnis.

Die Einheit kommt **vor** der Aufnahme aus IMAP (Pilot-Einheit 1), vom
Betreuer am 2026-10-05 so geschnitten: sie hängt an nichts aus der Aufnahme,
und kup6s kann mit dem Image des heutigen Stands Datenbank, Sicherung und
Werkzeug-Pod aufbauen, während die Aufnahme entsteht. Die Aufnahme kommt dann
mit dem nächsten Alpha-Release.

**Lieferungen:**

1. **Die Migrationen im Paket** und ein Kommando `previously migrate` (§2).
2. **Der Release-Weg** nach dem Muster des Projekts `fuellhorn` desselben
   Betreuers: Test-PyPI bei jedem Push auf `main`, PyPI und ein Image für zwei
   Plattformen bei einem veröffentlichten GitHub-Release (§3).
3. **Das Image** (§4) und **sein Smoke-Test** an jeder Plattform, gegen
   PostgreSQL und einen S3-Speicher (§5).
4. **Der Handoff an kup6s**, englisch (§6).
5. **Die Dokumentation dazu**, im selben Pull-Request (§9).

**Nicht enthalten:**

- **Jeder Bau in kup6s.** Was dort entsteht, steht im Handoff; gebaut wird es
  vom Agenten dort, nie von hier aus (Betreuer, 2026-10-05).
- **Ein Helm-Chart.** kup6s arbeitet mit cdk8s und nimmt das Image.
- **Ein Dienst.** Previously ist bis zum MCP-Server eine Kommandozeile; das
  Image hat keinen Port und keinen Health-Check.
- **Signaturen und Herkunftsnachweise** des Images (§12).

### 1.1 Was dieser Spec an früheren Festlegungen ändert

1. **Wo die Migrationen liegen.** Seit Stufe 1a liegen sie in `migrations/` an
   der Wurzel des Repositorys, außerhalb des Pakets; das Wheel enthält sie
   nicht. Ein Image, das das Paket installiert, könnte die Datenbank nicht
   anlegen. Sie ziehen ins Paket (§2.1).
2. **Wie die Datenbank angelegt wird.** Die Dokumentation sagt heute
   `uv run alembic upgrade head`. Sie sagt künftig `previously migrate`;
   `alembic` bleibt im Repository für die Entwicklung benutzbar.
3. **`gates.yml` wird aufrufbar.** Sein Kopfkommentar sagt „nichts über die
   Tore hinaus: kein Veröffentlichen, keine Geheimnisse". Das bleibt für diese
   Datei wahr; veröffentlicht wird in einer zweiten Datei, die die Tore ruft
   und nicht wiederholt (§3.2).

---

## 2. Die Migrationen und `previously migrate`

### 2.1 Ins Paket

`migrations/` zieht nach `src/previously/migrations/`, samt `env.py`,
`dsn.py`, `script.py.mako` und `versions/`. Alembic findet das Verzeichnis
über den Paketpfad (`script_location = previously:migrations`), also auch in
einem installierten Wheel, ohne Arbeitsverzeichnis und ohne `alembic.ini`.
`alembic.ini` bleibt an der Wurzel und zeigt auf den neuen Ort, damit
`uv run alembic …` in der Entwicklung weiter geht.

Was dabei mitzieht und im Plan einzeln stehen muss: die Importe
`migrations.dsn` in Tests und `env.py`, die Liste `SOURCE_DIRS` und
`OUTPUT_DIRS` in `tests/test_docs_references.py`, die Verträge in
`.importlinter` (wo `previously.migrations` in den Schichten steht, und dass
`core` es nicht importiert), die Sprachregel in `CLAUDE.md`, die
`migrations/` namentlich nennt.

**Ein Test hält fest, dass das gebaute Wheel die Migrationen enthält** — jede
Revision, `env.py` und die Vorlage. Ohne ihn fiele ein vergessener Eintrag
erst im Smoke-Test des Releases auf, nach dem Upload zu PyPI.

### 2.2 Das Kommando

```
previously migrate
```

Das elfte Kommando. Es bringt die Datenbank aus `PREVIOUSLY_DSN` auf die
neueste Revision und druckt eine Zeile auf die Standardausgabe:

```
migrated: 0002_projections -> 0004_event_blob
migrated: (empty) -> 0004_event_blob
up to date: 0004_event_blob
```

- **Nur vorwärts.** Ein Zurück gibt es über die Kommandozeile nicht; es bleibt
  `alembic downgrade` in der Entwicklung, mit den Weigerungen aus Stufe 1c.
- **Nie zwei zugleich.** `migrate` nimmt für seine Dauer eine
  Advisory-Sperre in PostgreSQL. Ein zweiter Aufruf wartet und findet dann
  „up to date". Ohne die Sperre liefen zwei Migrations-Jobs eines Releases —
  im Cluster nicht ausgeschlossen — dieselbe DDL zweimal.
- **Rückgabecodes:** 0 bei Erfolg, auch „up to date"; 2 bei einem Eingabe-
  oder Speicherfehler, mit einem Satz, ohne Traceback, ohne das Passwort der
  Datenbank.
- **Eine Datenbank, die eine neuere Revision trägt** als das Paket kennt (ein
  älteres Image gegen eine schon weiter migrierte Datenbank), ist ein Fehler
  mit einem Satz, der beide Revisionen nennt — nicht stilles Nichtstun.

---

## 3. Der Release-Weg

### 3.1 Auslöser

| Auslöser | Was geschieht |
|---|---|
| **Push auf `main`** | die sechs Tore; Paket bauen; Veröffentlichung auf **Test-PyPI**. Kein Image |
| **Veröffentlichtes GitHub-Release** (Tag `vX.Y.Z…`) | die sechs Tore; Paket bauen; **PyPI**; Image je Plattform mit Smoke-Test; Multi-Arch-Manifest |
| **Manueller Start** | wie ein Push auf `main`: ein Probelauf, der nichts außer Test-PyPI erreicht |

Ein Release entsteht nicht durch einen Tag allein und nicht durch einen
Merge, sondern erst, wenn das GitHub-Release veröffentlicht wird.

### 3.2 Der Workflow

Eine neue Datei `.github/workflows/release.yml`. `gates.yml` bekommt den
Auslöser `workflow_call`, und `release.yml` ruft ihn als ersten Job; die Tore
stehen an einer Stelle.

Die Jobs, jeder erst nach dem vorigen:

1. **Tore** (aufgerufen).
2. **Tag prüfen**, nur beim Release: der Tag hat die Form `vX.Y.Z`,
   `vX.Y.ZaN`, `vX.Y.ZbN` oder `vX.Y.ZrcN`; jede andere bricht hier ab, **vor**
   jedem Upload. (Bei `fuellhorn` prüft das erst der letzte Job, nachdem Paket
   und Image schon veröffentlicht sind; das ist hier vorgezogen.)
3. **Paket bauen** mit `uv build`; die Version kommt aus dem Tag
   (`hatch-vcs`, schon heute eingestellt). Auf `main` ergibt das eine
   Entwicklungsversion wie `0.1.0a2.dev3`, die Test-PyPI annimmt.
4. **Veröffentlichen**: Test-PyPI auf `main` (mit `skip-existing`, damit ein
   wiederholter Lauf nicht scheitert), PyPI beim Release. Beides über
   **Trusted Publishing** (OIDC) aus den GitHub-Environments `testpypi` und
   `pypi`: im Repository liegt kein Upload-Token.
5. **Image je Plattform**, `linux/amd64` auf `ubuntu-latest` und
   `linux/arm64` auf `ubuntu-24.04-arm`, je unter einem Zwischen-Tag
   `<version>-linux-<arch>`; vorher wartet der Job, bis die Version auf PyPI
   abrufbar ist. Danach der **Smoke-Test** (§5).
6. **Manifest**: erst jetzt entstehen die Tags, die jemand benutzt —
   `<version>` und `<major>.<minor>`, und `latest` **nur** bei einem stabilen
   Release, nie bei einem Alpha.

Die Aktionen werden auf Commits gepinnt, die Fassung daneben, wie in
`gates.yml`; Renovate bewegt sie. Die Rechte sind je Job das Nötige:
`id-token: write` nur beim Veröffentlichen, `packages: write` nur bei Image
und Manifest.

### 3.3 Versionen

Das erste Release ist **`0.1.0a1`**. Bis `1.0.0` sind Alpha-Releases der
Normalfall. Eine Versionsnummer, die einmal auf PyPI liegt, kommt nie wieder:
scheitert ein Release danach, kommt die nächste Nummer.

### 3.4 Was der Betreuer einrichtet

Einmal, vor dem ersten Release, und nur er kann es:

- auf **PyPI** einen *pending trusted publisher* für das Projekt `previously`
  (Repository `jensens/previously`, Workflow `release.yml`, Environment
  `pypi`); auf **Test-PyPI** dasselbe mit Environment `testpypi`. Der Name
  `previously` war am 2026-10-05 auf PyPI frei (`/pypi/previously/json`
  antwortete 404); wer ihn zuerst veröffentlicht, hat ihn;
- in GitHub die Environments `pypi` und `testpypi`, `pypi` mit dem Betreuer
  als erforderlichem Prüfer, wenn er jeden Upload freigeben will;
- nach dem ersten Release das Paket `previously` auf ghcr.io **öffentlich**
  stellen, damit kup6s es ohne Zugangsdaten zieht — oder, wenn es privat
  bleiben soll, ein Pull-Secret im Handoff.

Die Anleitung dazu steht in der Dokumentation (§9).

---

## 4. Das Image

- **Basis:** `ghcr.io/astral-sh/uv` mit Python 3.14, schlank, per Digest
  gepinnt; Renovate bewegt den Digest.
- **Abhängigkeiten exakt aus `uv.lock`** (`uv sync --frozen --no-dev
  --no-install-project`), dann Previously selbst **von PyPI** in der Version
  des Releases, ohne erneute Auflösung (`--no-deps`). Das Image enthält damit
  genau das Paket, das auf PyPI liegt, und genau die Fassungen, gegen die die
  Tore liefen.
- **Läuft als Benutzer 1000**, nicht als root.
- **Einstiegspunkt** `previously`; ohne Argumente druckt es die Hilfe. Ein
  Job im Cluster gibt Kommando und Argumente an; ein Werkzeug-Pod überschreibt
  den Einstieg mit einem Schlafbefehl.
- **Kein Port, kein Health-Check, kein Volume.** Eine Zwischendatei braucht
  nur `blob get` (Stufe 1c, §2.3); sie entsteht im Verzeichnis der Ausgabe.
- **Etiketten** nach OCI: Quelle (`org.opencontainers.image.source`), Lizenz
  `AGPL-3.0-or-later`, Version.

Die Datei `Dockerfile` liegt an der Wurzel; ein lokaler Bau mit einer
angegebenen Version geht ohne den Workflow.

---

## 5. Der Smoke-Test

An jedem Plattform-Image, im Job, der es gebaut hat, bevor das Manifest
entsteht. Schlägt er fehl, gibt es für diese Version kein Manifest: nur die
Zwischen-Tags, die niemand benutzt. Das Paket liegt dann schon auf PyPI — das
ist der Preis dafür, dass das Image aus PyPI installiert, und er steht in der
Anleitung.

Er läuft gegen ein PostgreSQL 17 und ein RustFS 1.0.1 als Container im
Job und prüft:

1. **Die installierten Fassungen entsprechen `uv.lock`** — keine weicht ab.
2. **`previously migrate`** auf einer leeren Datenbank, dann ein zweites Mal:
   „up to date".
3. **Ein Event mit Anhang**: ein Schlüssel wird zur Laufzeit im Image
   erzeugt (über `pyrage`, das das Image ohnehin hat), `append --attach`
   versiegelt einen Anhang in den Bucket.
4. **`blob get`** holt ihn byte-gleich zurück; **`verify --blobs`** meldet die
   Kette intakt; **`anchor`** druckt eine Zeile.
5. Das Image läuft als Benutzer 1000.

Damit ist der Weg geprüft, den der Werkzeug-Pod und die Jobs im Cluster gehen
— auf beiden Plattformen, am fertigen Image, nicht an den Tests.

---

## 6. Der Handoff an kup6s

Eine Datei, englisch, unter `docs/superpowers/handoffs/` (vom Bau der
Dokumentation ausgenommen wie alles unter `docs/superpowers/`). Der Betreuer
gibt sie dem Agenten in kup6s. Sie sagt **was** gebraucht wird, **warum**,
und **woran man erkennt, dass es steht** — nie, wie es in cdk8s zu bauen ist.

Inhalt:

- **Das Image**: Ort, Tags, kein `latest` für Alphas; Benutzer 1000; keine
  Ports.
- **PostgreSQL** über CloudNativePG, Version 17, mit Sicherung samt
  WAL-Archiv und einer **Restore-Probe** — die Anleitung
  `restore-from-a-backup` gilt dort, und `verify --anchors` ist ihre Prüfung.
- **Ein Bucket** für die Blobs, **ohne Versionierung und ohne Object Lock**,
  mit eigenen Zugangsdaten nur für ihn; die Aufbewahrung seiner Sicherungen
  ist Teil jeder Tilgungszusage.
- **Secrets**, nach Verwendern getrennt:
  - die Datenbank (`PREVIOUSLY_DSN`) — alle;
  - der Bucket (fünf Angaben) — alle, die Blobs schreiben, lesen oder
    löschen;
  - der Empfänger (`PREVIOUSLY_BLOB_RECIPIENT`, öffentlich) — wer aufnimmt;
  - **die Identität** (`PREVIOUSLY_BLOB_IDENTITIES`, ein Verzeichnis mit einer
    Datei je Schlüssel) — **nur der Werkzeug-Pod** und der nächtliche
    `verify --blobs`. Ihre Sicherung liegt **getrennt** von Datenbank und
    Bucket; ihr Verlust ist der Verlust aller Blobs.
- **Ein Migrations-Job je Release**: `previously migrate`, vor allem anderen.
- **Ein Werkzeug-Pod**: ein Deployment mit einem Pod aus dem Image, Schlaf als
  Befehl, alle Secrets einschließlich Identität. Der Betreuer arbeitet mit
  `kubectl exec … -- previously …`; bis zum MCP-Server ist das der Zugang.
- **CronJobs**, je mit `concurrencyPolicy: Forbid`:
  - `previously project` in kurzen Abständen;
  - `previously anchor` täglich, mit dem Ergebnis **außerhalb** der Datenbank
    abgelegt (wohin, entscheidet der Betrieb; die Anleitung `verify-the-chain`
    nennt die Bedingungen);
  - `previously verify --anchors … --blobs` nächtlich, mit Alarm bei einem
    Rückgabecode ungleich 0.
  Der CronJob der Aufnahme folgt mit dem Handoff der Aufnahme.
- **Netz nach außen**: der S3-Speicher; mit der Aufnahme der Mailserver auf
  Port 993.
- **Woran man erkennt, dass es steht**: `previously migrate` meldet die
  neueste Revision; im Werkzeug-Pod gehen `append --attach`, `blob get`,
  `verify --blobs`; eine Restore-Probe ist einmal gegangen und
  `verify --anchors` hat danach gehalten.

---

## 7. Was das für den Betrieb heißt

- **kup6s.** Alles aus §6, gebaut vom Agenten dort. Neu für den Betrieb ist,
  dass es überhaupt etwas zu betreiben gibt: Datenbank, Bucket, Schlüssel und
  vier Jobs. Für Previously selbst gibt es kein neues Geheimnis — das
  Veröffentlichen läuft über OIDC ohne Token.
- **Ein Host mit `docker-compose`.** Dasselbe Image; ein `postgres`-Dienst,
  ein S3-kompatibler Dienst, ein Verzeichnis mit der Identität; `previously
  migrate` als einmaliger Dienst vor den anderen; Cron-Zeilen auf dem Host,
  die `docker compose run --rm previously …` rufen, statt CronJobs; `docker
  compose exec` statt `kubectl exec`. Nicht gebaut, nur durchdacht.
- **Der Einfachheits-Check** fällt gut aus: ein Image, ein Einstiegspunkt,
  kein Dienst, keine eigene Konfigurationsdatei — alles kommt aus der
  Umgebung. Er findet eine Sache: das Image installiert aus PyPI, also ist ein
  Release, dessen Image scheitert, auf PyPI schon sichtbar. Für ein Alpha
  vertretbar.

---

## 8. Schnitt im Code

| Ort | Was |
|---|---|
| `src/previously/migrations/` | die Migrationen, aus `migrations/` verschoben |
| `alembic.ini` | `script_location = previously:migrations` |
| `src/previously/cli.py` | `migrate`; liest `PREVIOUSLY_DSN`, formatiert |
| `src/previously/storage/` | die Advisory-Sperre und der Aufruf von Alembic, hinter einer Funktion, die `cli` ruft; `core` kennt Alembic nicht |
| `.github/workflows/gates.yml` | Auslöser `workflow_call` |
| `.github/workflows/release.yml` | neu |
| `Dockerfile`, `.dockerignore` | neu |
| `.importlinter` | `previously.migrations` in den Schichten; namentlich, wie die bestehenden Verträge |
| `docs/superpowers/handoffs/` | neu, der Handoff |

Wo genau `previously.migrations` in den Schichten steht, entscheidet der Plan
an den Importen: `env.py` importiert heute `previously.storage.schema`.

---

## 9. Dokumentation

Im selben Pull-Request, nach `plone-doc-style:author`, eine Seite je Quadrant.

- **How-to, neu: ein Release schneiden** — Vorbedingungen, das einmalige
  Einrichten aus §3.4, Tag-Regeln, der Befehl, was zu beobachten ist, was zu
  tun ist, wenn ein Schritt scheitert (welcher Schritt hat was schon
  veröffentlicht), Release-Notes für Betreiber (neue Migrationen).
- **How-to, neu: Previously aus dem Image betreiben** — die Angaben, die
  Reihenfolge `migrate` vor allem anderen, ein Lauf mit `docker run`; für den
  Cluster der Verweis, dass der Betrieb ihn baut.
- **Reference:** `cli.md` (`migrate`, elf Kommandos), `configuration.md`
  (wer `PREVIOUSLY_DSN` liest, jetzt auch `migrate`).
- **Explanation:** eine Seite oder ein Abschnitt zur Auslieferung — warum das
  Image aus PyPI installiert und nicht aus dem Checkout, warum die Fassungen
  gegen `uv.lock` geprüft werden, warum kein `latest` für Alphas, warum die
  Migrationen ins Paket gehören.
- **Bestehende Seiten:** jede, die `alembic upgrade head` sagt — das Tutorial
  (neu getippt), die Anleitungen zur Wiederherstellung und zur Migration, das
  README.
- **README:** Installation aus PyPI und das Image.
- **Landkarte:** die neue Einheit, und was sie schließt.

---

## 10. Zusicherungen und Tests

Jede Zusicherung bekommt einen Test, von dem gemessen ist, dass er bricht,
und eine Kontrolle, die gemessen grün bleibt; gegen echtes PostgreSQL.

1. **Das Wheel enthält die Migrationen.** Mutation: eine Revision aus dem
   Paket nehmen.
2. **`migrate` legt eine leere Datenbank an und meldet danach „up to date".**
3. **Zwei `migrate` zugleich: einer migriert, der andere wartet und findet
   die Datenbank fertig.** Mutation: die Sperre entfällt.
4. **Eine Datenbank mit unbekannter, neuerer Revision ist ein Fehler** mit
   einem Satz.
5. **Kein Passwort in der Ausgabe** von `migrate`, auch bei falscher
   Anmeldung.
6. **Die bestehenden Migrations-Tests** laufen gegen den neuen Ort,
   unverändert in dem, was sie prüfen.
7. **Der Smoke-Test** (§5) prüft das Image; er ist der Test des Workflows.
   Bevor der Pull-Request gemergt wird, läuft der Workflow einmal von Hand auf
   dem Zweig und erreicht Test-PyPI nicht (der Probelauf veröffentlicht nur
   von `main`); Image und Smoke-Test erprobt erst das erste Release.

---

## 11. Abnahme

| # | Bedingung |
|---|---|
| 1 | Die Migrationen liegen im Paket; das Wheel enthält sie; `alembic` geht in der Entwicklung weiter. |
| 2 | `previously migrate` nach §2.2, mit Sperre, ohne Traceback, ohne Passwort. |
| 3 | `release.yml` nach §3, `gates.yml` aufrufbar; die Aktionen gepinnt. |
| 4 | `Dockerfile` nach §4; ein lokaler Bau und ein lokaler Lauf des Smoke-Tests gehen. |
| 5 | Der Handoff (§6) liegt im Repository. |
| 6 | Die Dokumente aus §9 stehen; jede Stelle, die `alembic upgrade head` sagte, sagt `previously migrate`. |
| 7 | Alle sechs Tore grün; `pip-audit` ohne Befund. |
| 8 | **Nach dem Merge, vom Betreuer:** Trusted Publishing eingerichtet (§3.4); der Lauf auf `main` legt eine Entwicklungsversion auf Test-PyPI; das Release `v0.1.0a1` legt `previously 0.1.0a1` auf PyPI und `ghcr.io/jensens/previously:0.1.0a1` für beide Plattformen, Smoke-Test grün; das Image ist ziehbar. |

Abgenommen ist die Arbeit mit dem Merge nach `main`; Bedingung 8 folgt ihm,
weil Trusted Publishing und ein Release erst auf `main` möglich sind. Was
dabei scheitert, ist ein Befund für einen Folge-Pull-Request.

---

## 12. Was offen bleibt

Gepflegt, solange der Spec lebte; beim Einfrieren am 2026-10-05 gingen die
Punkte in die Landkarte (`docs/superpowers/landkarte.md`), jeder unter die
Einheit, zu der er gehört, und dort leben sie weiter. Die Liste hier ist der
Stand dieses Tages.

1. **Signaturen und Herkunftsnachweise** (Sigstore/cosign, SLSA-Provenance,
   SBOM) für Paket und Image. PyPI erzeugt mit Trusted Publishing schon
   Attestierungen für das Paket; für das Image ist nichts vorgesehen.
2. **Das Image installiert aus PyPI**; scheitert sein Smoke-Test, ist die
   Version auf PyPI schon sichtbar (§5). Ein Image aus dem gebauten Wheel des
   Laufs wäre die Alternative, mit dem Preis, dass das Image dann nicht
   beweist, dass das PyPI-Paket installierbar ist.
3. **`previously migrate` nur vorwärts.** Ein Zurück im Betrieb ist eine
   Wiederherstellung, kein Kommando.
4. **Wo die Ankerdatei im Cluster liegt**, entscheidet der Betrieb; die
   Bedingungen stehen in der Anleitung. Ob Previously sie selbst irgendwohin
   veröffentlichen soll, ist offen.
5. **Zugriff ohne `kubectl exec`** kommt mit dem MCP-Server.
6. **Der Name `previously` auf PyPI** ist erst belegt, wenn das erste Release
   veröffentlicht ist.
