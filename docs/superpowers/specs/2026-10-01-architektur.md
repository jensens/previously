# Previously — Architektur

Stand: 2026-10-01 · Status: zur Abnahme

Geschrieben für Jens als Reviewer und als Vorlage für die Zerlegung in
Teilprojekte. Setzt den Entwurf in `2026-10-01-previously-design.md`
voraus; Paragraphenverweise ohne Dokumentangabe beziehen sich darauf.

**Sprachregelung: Prosa und Begründungen deutsch, alles Technische englisch.**
Code, SQL, Bezeichner, Tabellen- und Spaltennamen, Werkzeugnamen, Modulnamen
und Aufzählungswerte sind englisch. Das Glossar in §3 legt die Zuordnung fest —
wer eine zweite Übersetzung erfindet, erzeugt zwei Vokabulare für dieselbe Sache.

---

## 1. Was dieses Dokument festlegt — und was nicht

Der Entwurf legt Modell, Leitsätze und Grenzen fest. Er sagt nicht, aus welchen
Modulen das System besteht und wie sie miteinander reden. Genau das steht hier.

**Aufnahmekriterium für jede Festlegung in diesem Dokument:**

> **Hängt mehr als ein Modul davon ab? Dann jetzt entscheiden. Sonst später.**

Schnittstellen, Schema und Prozessmodell hängen voneinander ab und gehören
hierher. Wie ein IMAP-Konnektor intern Ordner abgleicht, hängt an nichts und
bleibt offen.

**Leitsatz dieses Dokuments: Grenzen scharf, Innenleben lose.**

Was im Voraus festgeschrieben wird, muss teuer zu ändern sein — sonst schreibt
man Fiktion. Das ist dieselbe Logik wie Leitsatz 6 im Entwurf: teuer ist nur,
was nicht aufgenommen wurde und was eine Grenze verletzt.

---

## 2. Module und Grenzen

Sieben Module. Die Pfeile sind Abhängigkeitsrichtungen: ein Modul kennt nur,
worauf es zeigt.

```
   mcp_server ───────┐
   ai_layer ──► gate ─┼──► core ──► storage
       │             │       │
       └─────────────┘       ▼
   connectors ──────────► contract   (reine Typen, kennt nichts)
       │                      ▲
       └──────────────────────┘
```

| Modul | Zuständigkeit | kennt |
|---|---|---|
| **`storage`** | Append-only Log, Projektionstabellen, Suchindex. Nichts über Domäne. | — |
| **`contract`** | Der Konnektor-Vertrag als Typen und Protokoll. Keine Logik. | **—** |
| **`core`** | Event-Arten, Entitäten, Projektionen, Hash-Kette, Idempotenz | `storage`, `contract` |
| **`connectors`** | Je Quelle/Ziel eine Implementierung des Vertrags | `contract`, `core` |
| **`gate`** | Modellaufrufe, Policy, Anbieterwahl, Audit der Aufrufe | `core` |
| **`ai_layer`** | Zuordnung, Zerlegung, Extraktion, Templates, Vorschläge | `gate`, `core` |
| **`mcp_server`** | Protokoll, Werkzeuge, Handles, Offenlegungsprüfung | `core`, `ai_layer` |

**Drei Regeln, die diese Grenzen verteidigen und testbar sind:**

1. **`core` kennt kein Fremdsystem und kein Modell.** Kein Import aus
   `connectors`, `gate`, `ai_layer`, `mcp_server`. Statisch prüfbar.
   (`contract` ist erlaubt: reine Typen, kennt selbst nichts — sonst entstünde
   ein Zyklus, weil der Kern `RawEvent` entgegennehmen muss.)
2. **Nur `gate` ruft Modelle.** Kein Anbieter-SDK außerhalb. Statisch prüfbar
   (Abnahmebedingung 7 im Entwurf).
3. **Nur `storage` kennt SQL.** `core` spricht Methoden, nicht Abfragen.

**Warum `contract` ein eigenes Modul ist:** Der manuelle Einwurf ist laut §11.4
die Referenzimplementierung des Konnektor-Vertrags. Liegt der Vertrag in
`connectors`, kennt ihn der Kern nicht und jeder Konnektor erfindet ihn neu.
Als eigenes Modul ist er zitierbar und veränderungsfest.

---

## 3. Glossar

Die Domäne ist deutsch gedacht; die Bezeichner sind englisch. Diese Tabelle ist
die einzige erlaubte Zuordnung.

### Event-Arten

| deutsch | Bezeichner | Begründung der Wahl |
|---|---|---|
| Wahrnehmung | `observation` | was beobachtet wurde, nicht was gilt |
| Feststellung | `assertion` | eine Behauptung kann falsch sein — trägt Leitsatz 4 im Wort |
| Handlung | `action` | |

### Entitäten

| deutsch | Bezeichner | Begründung der Wahl |
|---|---|---|
| Organisation | `organization` | |
| Projekt | `project` | |
| Person | `person` | |
| Kanalidentität | `channel_identity` | |
| Beteiligung | `involvement` | Akteur × Ziel × Rolle × Zeitraum |
| **Vorgang** | **`matter`** | In der professionellen Dienstleistung genau das: ein abgegrenztes Stück Arbeit mit Anfang und Ende. `case` und `thread` wären beide schiefer |
| Verpflichtung | `obligation` | |
| Aufgabe | `task` | |
| Entscheidung | `decision` | |
| Vereinbarung | `agreement` | NDA, AVV, Rahmen-, ARGE-Vertrag |

### Wiederkehrende Felder

| deutsch | Bezeichner |
|---|---|
| erfasst am / Ereigniszeit | `recorded_at` / `occurred_at` |
| Art | `kind` |
| Quelle / quellennative ID | `source` / `external_id` |
| Belegart (Wortlaut, Erinnerung) | `evidence` (`verbatim`, `recollection`) |
| Einheit, Nummer, Inhalt | `unit`, `seq`, `content` |
| Sprache | `language` |
| Urheber | `author` |
| Verantwortung (direkt, transitiv) | `responsibility` (`direct`, `transitive`) |
| Sicherheit | `confidence` |
| Quellen | `sources` |
| Zuordnung | `assignment` |
| Schuldner / Gläubiger | `debtor` / `creditor` |
| Frist / Zustand | `due_date` / `state` |
| aufgeteilt in / zusammengelegt in | `split_into` / `merged_into` |
| Rechtsraum | `jurisdiction` |
| Datenpolitik | `data_policy` |
| Vertraulichkeit | `confidentiality` |
| Verarbeitungsraum | `processing_region` |
| Befugnis (Auftrag, einmal, Klasse) | `authorization` (`instructed`, `once`, `class`) |
| Zielort / Deckung / Publikumszustand | `target` / `coverage` / `audience_state` |
| Wasserzeichen | `watermark` |
| Auftrag | `job` |

### Rollen

| deutsch | Bezeichner |
|---|---|
| Auftraggeber | `client` |
| Auftragnehmer | `contractor` |
| Subunternehmer | `subcontractor` |
| ARGE-Partner | `joint_venture_partner` |
| Allianzpartner | `alliance_partner` |
| Dienstleister | `service_provider` |
| Mitarbeiter | `employee` |
| Partner | `partner` |
| Freelancer | `freelancer` |
| Ansprechpartner | `contact` |

---

## 4. Schema

PostgreSQL.

### 4.1 Der Log

Eine Tabelle für alle drei Event-Arten. Keine Vererbungshierarchie: die Arten
unterscheiden sich in Nutzlast, nicht in Lebenszyklus, und eine Tabelle hält die
Hash-Kette trivial.

```sql
CREATE TABLE event (
  id           bigint PRIMARY KEY,       -- vom Vorgänger, keine Sequenz
  kind         text NOT NULL CHECK (kind IN ('observation','assertion','action')),
  recorded_at  timestamptz NOT NULL,
  occurred_at  timestamptz NOT NULL,
  hash         bytea NOT NULL,
  prev_hash    bytea,
  payload_hash bytea NOT NULL,       -- die Kette hängt hieran, nicht am Inhalt
  payload      jsonb                 -- NULL = Grabstein (§4.6)
);

CREATE INDEX event_occurred_idx ON event (occurred_at);
CREATE INDEX event_kind_occurred_idx ON event (kind, occurred_at);
CREATE UNIQUE INDEX event_hash_idx ON event (hash);

-- Serialisiert nebenläufige Anfügungen UND erzwingt genau einen Genesis-Eintrag
CREATE UNIQUE INDEX event_prev_hash_idx
  ON event (prev_hash) NULLS NOT DISTINCT;
```

**Die beiden Unique-Indizes auf `prev_hash` und `id` sind die gesamte
Nebenläufigkeitssteuerung des Logs.** Zwei nebenläufige Anfügungen lesen
dieselbe Kettenspitze, berechnen daraus dieselbe `id` und dasselbe `prev_hash` —
eine verletzt einen der beiden Indizes und wiederholt. Welcher zuerst anschlägt,
ist unbestimmt; die Wiederherstellung ist dieselbe. Keine Vorab-Sperre, kein
Advisory Lock, keine Koordination.

Als Nebeneffekt **beweist** der Index die Linearität: eine Verzweigung ist
unmöglich, weil kein Vorgänger zweimal vorkommen darf. Strukturelle Garantie
statt Prüfroutine.

**`NULLS NOT DISTINCT` ist dabei nicht optional** (PostgreSQL 15+): ohne sie
gelten mehrere `NULL` in einem Unique-Index als verschieden, jeder Prozess
könnte einen eigenen Genesis-Eintrag schreiben — und damit wäre genau die
Verzweigung erlaubt, die der Index verhindern soll. Eine frühere Fassung hatte
das übersehen und die Garantie damit still wertlos gemacht.

- **`id` ist monoton und die Kettenreihenfolge** — und das gilt nur, weil sie
  **vom Vorgänger abgeleitet** wird (`id = Vorgänger.id + 1`) und **nicht aus
  einer Sequenz** kommt. Eine Sequenz garantiert keine Commit-Reihenfolge: zwei
  nebenläufige Schreiber könnten ihre Nummern in umgekehrter Reihenfolge
  festschreiben, und dann wäre die Kette `9 → 11 → 10` — eine intakte Kette, auf
  der die Prüfung in `id`-Reihenfolge **anschlägt**. Eine frühere Fassung hatte
  hier eine Sequenz vorgesehen; Herleitung in `2026-10-02-stufe-1a-log.md` §4.1.
- `recorded_at` ist Anzeige, nicht Ordnung — und **Eingabe, nicht Erzeugnis**,
  weil es in den Hash eingeht und über Wiederholungen stabil bleiben muss.
- **`occurred_at` ist indiziert**, weil jede Chronik darüber sortiert (§5.1).
- `payload` ist `jsonb`, validiert gegen JSON-Schema **in `core`**, nicht als
  Spaltenzwang. Grund: Leitsatz 9 — neue Arten von `assertion` dürfen ohne
  Migration dazukommen.
- **`payload_hash` ist nicht redundant.** Die Kette hängt an ihm, nicht am
  Inhalt — das ist die Voraussetzung für Tilgung (§4.6) und heute zu
  entscheiden.

```
payload_hash = sha256( jcs(payload) )
hash         = sha256( jcs({ v, domain, id, kind, recorded_at,
                             occurred_at, prev, payload: <hex> }) )
```

Kanonisierung nach **RFC 8785 (JCS)**, und **keine Gleitkommazahlen in
Nutzlasten** — Gleitkomma-Serialisierung ist sprachabhängig, und ein Hash, der
je nach Laufzeitumgebung anders ausfällt, macht die Kette wertlos.

Der Event-Hash geht über ein **kanonisiertes Objekt**, nicht über eine
Verkettung der Felder: Verkettung ist mehrdeutig (`"ab"+"c"` = `"a"+"bc"`).
Vollständige Festlegung in `2026-10-02-stufe-1a-log.md` §3.

### 4.2 Idempotenz

```sql
CREATE TABLE source_key (
  source      text NOT NULL,
  external_id text NOT NULL,
  event_id    bigint NOT NULL REFERENCES event(id),
  PRIMARY KEY (source, external_id)
);
```

Jede `observation` trägt `source` + quellennative ID (§5.1). Ein zweiter Import
stößt auf den Primärschlüssel und wird verworfen, nicht verdoppelt. **Das ist
auch die Transportanforderung aus MCP 2026-07-28** (§8.3): ein abgebrochener
Aufruf wird mit neuer Request-ID wiederholt, und nur diese Tabelle verhindert
das Duplikat.

### 4.3 Einheiten

```sql
CREATE TABLE unit (
  event_id bigint NOT NULL REFERENCES event(id),
  seq      int NOT NULL,
  content  text NOT NULL,
  start_ms int,                    -- Transkript: Zeitbereich
  end_ms   int,
  speaker  text,
  PRIMARY KEY (event_id, seq)
);
```

`language` steht **nicht** hier: die Sprache ist eine `assertion` (§5.1), kein
Merkmal der `observation`.

### 4.4 Projektionen

Alle Projektionstabellen sind **ableitbar und wegwerfbar**. Sie tragen daher
keine eigene Wahrheit und keine Fremdschlüssel aufeinander — nur auf `event`.
Namenspräfix `p_`.

```sql
CREATE TABLE projection_state (
  name      text PRIMARY KEY,
  up_to_id  bigint NOT NULL,
  version   int NOT NULL,
  built_at  timestamptz NOT NULL
);
```

**`version`** ist der Wiederaufbau-Auslöser: ändert sich die Projektionslogik,
erhöht man die Version, und der Arbeiter baut neu. Keine Migration, kein
Handgriff.

Je Projektion eine Tabelle, alle nach demselben Muster — Beispiel:

```sql
CREATE TABLE p_obligation (
  id            text PRIMARY KEY,        -- fachliche Kennung
  project       text,
  matter        text,
  debtor        text,                    -- Akteur-Kennung, darf NULL sein
  creditor      text,
  kind          text NOT NULL,           -- delivery | answer | decision | payment
  due_date      date,
  state         text NOT NULL,
  split_into    text[],                  -- Dach (§6.2)
  evidenced_by  bigint[] NOT NULL,       -- assertion-IDs
  last_event_id bigint NOT NULL REFERENCES event(id)
);
```

`evidenced_by` ist **nicht optional** — das ist die Quellenpflicht in
Tabellenform.

### 4.5 Suche

```sql
CREATE TABLE p_unit_search (
  event_id    bigint NOT NULL,
  seq         int NOT NULL,
  project     text,                 -- B-Tree: Vorfilter vor der Vektorsuche
  occurred_at timestamptz NOT NULL,
  language    text,
  fulltext    tsvector,
  embedding   vector(N),            -- N kommt mit der Modellwahl (§10)
  PRIMARY KEY (event_id, seq)
);

CREATE INDEX p_unit_search_project_idx ON p_unit_search (project, occurred_at);
```

Die B-Tree-Spalte `project` ist der Grund, warum §12.2 im günstigen Fall landet:
bei stark selektiven Filtern filtert Postgres **vor** der Vektorsuche.

**Welche Textvariante gewinnt, ist offen** (§12.3). Die Grenze ist deshalb so
gezogen, dass `fulltext` ersetzt werden kann, ohne `core` anzufassen: die
Suchschnittstelle nimmt eine Anfrage und gibt Einheitenverweise zurück, nicht
`tsquery`.

---

### 4.6 Tilgung: heute nichts verbauen

Append-only verträgt sich nicht von selbst mit einem Löschverlangen (DSGVO
Art. 17). Gebaut wird der Mechanismus **jetzt nicht** — aber drei Dinge müssen
heute stimmen, sonst ist er später unerreichbar.

#### 1. Die Kette hängt am Hash, nicht am Inhalt

Hasht die Kette die Nutzlast inline, bricht jede Tilgung sie. Über
`payload_hash` (§4.1) bleibt sie gültig: Tilgung ersetzt `payload` durch einen
Grabstein und **behält `payload_hash`**. Die Verifikation läuft unverändert
durch — und es bleibt beweisbar, *was* dort stand, ohne es zu haben.

Kosten heute: eine Spalte. Nachträglich: unmöglich, weil die Kette über alle
Altdaten falsch würde.

Eine Tilgung ist selbst ein Event (`action`, `kind: redaction`) mit Ziel,
Umfang und Begründung. Kein neuer Mechanismus.

#### 2. Blobs werden von Anfang an verschlüsselt — aus eigenem Recht

Zwei Dinge, die leicht vermischt werden und verschiedene Kosten haben:

| | Zweck | ermöglicht Schreddern? |
|---|---|---|
| **(a) Verschlüsselung, ein Schlüssel** | Schutz bei Bucket-Kompromittierung, gestohlenen Zugangsdaten, Anbieterzugriff | **nein** — ein Schlüssel weg heißt alles weg |
| **(b) Schlüssel pro Betroffenem** | Schreddern | ja |

**(a) wird jetzt gebaut und braucht (b) nicht.** Client-seitig verschlüsselt
heißt: gestohlene Bucket-Zugangsdaten liefern nur Chiffretext. Für
Mandantendaten unter NDA ist das ein belegbares Argument gegenüber
Auftraggebern.

**Und beim gewählten Anbieter gibt es keine Alternative.** Hetzner Object
Storage (Ceph-basiert) unterstützt **nur SSE-C** — Schlüssel vom Kunden, pro
Anfrage mitgesendet — und **kein SSE-S3, kein SSE-KMS**. Anbieterverwaltete
Verschlüsselung steht also gar nicht zur Wahl. Dazu eine Ceph-Einschränkung:
mit SSE-C funktioniert **CopyObject nicht**.

Client-seitig ist damit nicht nur gleichwertig, sondern besser als SSE-C: kein
CopyObject-Problem, der Anbieter sieht den Schlüssel nie, und der lokale
Dateisystem-Adapter verhält sich identisch.

**Keine Verwechslung:** (a) macht die heute geschriebenen Blobs **nicht**
schredderbar. Deren Entfernungsweg bleibt Löschen — was genügt, solange keine
Versionierung läuft (Punkt 3). (b) gilt erst für Blobs, die nach Einführung der
Schlüssel pro Betroffenem geschrieben werden; `key_id` hält diesen Weg offen.

#### Verschränkung mit der Inhaltsadressierung

Verschlüsselt man mit frischem Nonce, ist der Chiffretext jedes Mal anders —
wäre der Bucket-Schlüssel der Chiffretext-Hash, wäre die Deduplizierung weg.

> **Bucket-Schlüssel ist der Klartext-Hash** (er steht ohnehin im Log), und beim
> Schreiben gilt **erster gewinnt**: existiert das Objekt, wird nicht neu
> hochgeladen.

Damit bleiben Dedup und Unveränderlichkeit erhalten, und die Nonce-Frage
erledigt sich. AES-GCM, Nonce im Objekt-Header, `key_id` in der Blob-Referenz —
der tatsächlich verwendete Schlüssel, nicht `null`.

#### Der Schlüssel darf nicht im selben Backup liegen wie die Daten

Steckt er als Kubernetes-Secret in etcd, und etcd wird dorthin gesichert, wo
auch die Blobs liegen, hat ein Angreifer mit Zugriff auf diesen Ort beides. Also
Schlüssel über External Secrets aus einem separaten Tresor, und die
Tresor-Sicherung getrennt von der Datensicherung.

Das ist die dritte Anwendung desselben Grundsatzes:

| Trennung | Grund |
|---|---|
| Blob-Bucket ↔ Backup-Bucket | Anwendungs-Kompromittierung darf nicht an die Backups |
| Cluster-Standort ↔ Backup-Standort | nicht gemeinsam ausfallen |
| **Schlüssel ↔ Daten** | nicht gemeinsam erbeutet werden |

> **Trenne, was nicht gemeinsam fallen darf.**

#### Der ehrliche Preis

**Schlüsselverlust ist Totalverlust** — das echte Risiko, nicht die Komplexität.
Der Schlüssel ist winzig und damit gut sicherbar, aber er *muss* gesichert
werden, und zwar getrennt. Dazu eine Unannehmlichkeit im Betrieb: ein Dokument
lässt sich nicht mehr per `s3 cp` herausziehen und anschauen, es braucht immer
den Entschlüsselungsweg.

Keine Leistungsbedenken: die Pipeline liest jeden Blob einmal zur
Textextraktion, der MCP-Server selten.

#### 3. Keine Versionierung auf dem Blob-Bucket

Der nicht offensichtliche Punkt, weil er eine Betriebsbequemlichkeit mit einer
Rechtsfähigkeit koppelt:

> **Objektversionierung oder Object Lock auf dem Blob-Bucket verwandelt "Blob
> löschen" in "Krypto-Schreddern oder nichts".**

Inhaltsadressierte Blobs lassen sich einzeln löschen, ohne die Kette zu
berühren — der Hash bleibt im Log als Beleg, dass dort etwas war. Das
funktioniert nur, solange Löschen auch löscht. Versionierung, die man sonst
gern "zur Sicherheit" anschaltet, macht den einfachen Weg kaputt und erzwingt
rückwirkend genau das, was rückwirkend nicht geht.

**Versionierung auf dem Backup-Bucket gern, auf dem Blob-Bucket nicht.** Dritter
Grund für die Zwei-Bucket-Trennung (§10.3), aus wieder einer anderen Richtung.

#### Was eine Tilgung kostet

Sie nimmt den **Beleg**, nicht die **abgeleiteten Fakten**. Die `assertion`
"Einheiten 3–4 sind eine Verpflichtung mit Frist 30.4." ist ein eigenes Event
und überlebt; die Verpflichtung bleibt im Protokoll, ihre Quellenangabe zeigt
auf einen Grabstein.

Das ist richtiges Verhalten: dass etwas vereinbart wurde, verschwindet nicht,
weil jemand Löschung verlangt — was verschwindet, ist der Wortlaut. Trägt auch
die `assertion` personenbezogene Daten, greift derselbe Mechanismus auf sie,
weil `payload_hash` einheitlich gilt.

## 5. Die Storage-Schnittstelle

Schmal, damit sie hält (§12). Alles, was darüber hinausgeht, gehört in `core`.

> **Das `Protocol` ist Zielform, nicht Bestand** (Prüfbefund W-4 der zweiten
> Endprüfung von Stufe 1a). Im Baum gibt es kein `class Storage(Protocol)`:
> `core` ist gegen den konkreten `storage.postgres.PostgresStorage`
> typisiert. Daran hängen die zwei benannten import-linter-Ausnahmen und der
> Riegel, der ihre `TYPE_CHECKING`-Eigenschaft sichert. §7 der 1a-Spezifikation
> begründet, warum das für 1a genügt; §12 dort führt die saubere Form — ein
> über den Verbindungstyp generisches `class LogStore[Conn](Protocol)` in
> `contract` — als offenen Punkt für die Neuplanung nach Teilprojekt 1.
>
> Die Signaturen unten sind außerdem die der **Endfassung** über alle Stufen
> (`stream`, Projektionen, `search`); die Teilmenge, die 1a wirklich hat,
> steht in §7 der 1a-Spezifikation und nimmt überall die `Connection` entgegen.

```python
class Storage(Protocol):
    def append(self, events: Sequence[NewEvent]) -> list[int]: ...
    def read(self, from_id: int, limit: int) -> Iterator[Event]: ...
    def stream(self, *, project: str | None, from_id: int) -> Iterator[Event]: ...
    def last_hash(self) -> bytes | None: ...
    def lookup(self, source: str, external_id: str) -> int | None: ...

    def write_projection(self, name: str, rows: Sequence[Mapping]) -> None: ...
    def clear_projection(self, name: str) -> None: ...
    def projection_state(self, name: str) -> ProjectionState | None: ...

    def search(self, query: SearchQuery) -> list[Hit]: ...
```

Fünf Eigenschaften, die diese Schnittstelle **nicht** hat und bewusst nicht
haben darf: kein Update, kein Delete, keine Transaktionssteuerung nach außen,
kein SQL-Durchlass, keine Rückgabe von Datenbankobjekten.

`stream` gibt einen **Iterator**, nicht eine Liste (Abnahmekriterium aus §12.2) —
Reprojektion über Jahre Historie darf nichts in den Speicher ziehen.

---

## 6. Der Konnektor-Vertrag

Das Stück, das im Entwurf dreimal behauptet und nie geschrieben wurde.

### 6.1 Zwei Richtungen, getrennt deklariert

```python
class Capability(StrEnum):
    BIDIRECTIONAL = "bidirectional"
    READ_ONLY     = "read_only"
    NO_API        = "no_api"

class Connector(Protocol):
    name: str                         # 'imap', 'drop', 'prompt', 'link', 'gitlab', …
    capability: Capability

    def ingest(self, since: Watermark) -> Iterator[RawEvent]: ...

class Renderer(Protocol):             # nur bei BIDIRECTIONAL
    def targets(self) -> list[Target]: ...
    def render(self, target: Target, projection: Mapping) -> RenderResult: ...
```

Ein Konnektor ohne Renderer ist zulässig; ein Renderer ohne Konnektor nicht —
sonst kann die Echo-Unterdrückung (§5.5) nicht vergleichen.

### 6.2 Was ein `RawEvent` tragen muss

```python
class Evidence(StrEnum):
    VERBATIM     = "verbatim"
    RECOLLECTION = "recollection"

@dataclass(frozen=True)
class RawEvent:
    source: str
    external_id: str                  # Idempotenz
    occurred_at: datetime
    evidence: Evidence
    channel_identities: list[ChannelIdentity]
    units: list[RawUnit]              # nummeriert, mechanisch zerlegt
    raw: bytes | None                 # Leitsatz 6: im Zweifel mehr aufnehmen
```

**Kein `assignment`, keine Klassifikation, keine `language`.** Ein Konnektor
*interpretiert* nicht — er nimmt auf. Das ist die Grenze, an der Leitsatz 4
hängt, und sie ist im Typ erzwungen, nicht in der Prosa.

### 6.3 Wasserzeichen und Wiederaufnahme

```python
@dataclass(frozen=True)
class Watermark:
    connector: str
    position: Mapping[str, str]       # konnektorspezifisch, opak für core
    set_at: datetime
```

`core` behandelt `position` als opak — IMAP legt `UIDVALIDITY`/`UIDNEXT` ab,
GitLab eine Cursor-Kennung. **Fortgeschrieben wird es erst, nachdem die Events
angefügt sind**, nie vorher. Bricht ein Abgleich ab, läuft er von der letzten
bestätigten Stelle neu und läuft dabei idempotent ins Leere (§4.2).

### 6.4 Rendern und Echo

```python
@dataclass(frozen=True)
class RenderResult:
    external_ref: str                 # 'gitlab:issue/42'
    rendered_state: Mapping           # exakt das Geschriebene
```

`rendered_state` wird an der `action` gespeichert und ist der Vergleichswert für
§5.5: **vergleichen, nicht annehmen.** Gleichheit heißt Echo und wird verworfen;
Unterschied heißt `observation`.

### 6.5 Zielort

```python
class AudienceState(StrEnum):
    DECLARED  = "declared"
    CONFIRMED = "confirmed"
    DIVERGENT = "divergent"
    UNKNOWN   = "unknown"

@dataclass(frozen=True)
class Target:
    name: str                         # 'gitlab:group/client-b'
    coverage: list[str]               # agreement-Kennungen (§7.2 im Entwurf)
    audience_state: AudienceState
```

`coverage` ist **erklärt, nicht entdeckt** — das Gate der Offenlegungsprüfung
braucht keinen Adapter (§7.2 im Entwurf). `audience_state` ist die Prüfung
darüber und darf `UNKNOWN` sein, was Rendern blockiert.

---

## 7. Prozessmodell

### 7.1 Was läuft als was

| Prozess | Art | Aufgabe |
|---|---|---|
| `mcp` | langlebig | MCP-Server, zustandslos (§8) |
| `ingest` | periodisch je Konnektor | `ingest()` → Log |
| `project` | ereignisgetrieben | Log → Projektionstabellen |
| `enrich` | gestapelt | Zuordnung, Zerlegung, Extraktion über das Gate |
| `render` | ereignisgetrieben | Projektion → Zielorte, nach Freigabe |
| `maintain` | täglich | Kettenprüfung, Publikum neu aufzählen, Schwingungswächter |

**Eine Warteschlange in Postgres, kein Broker.** Bei diesem Volumen (§12.1) ist
ein zusätzliches System reiner Betriebsaufwand. `SELECT … FOR UPDATE SKIP LOCKED`
reicht für mehrere Arbeiter.

```sql
CREATE TABLE job (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  kind       text NOT NULL,
  key        text NOT NULL,           -- fachliche Entprellung
  payload    jsonb NOT NULL,
  state      text NOT NULL DEFAULT 'pending',
  attempts   int NOT NULL DEFAULT 0,
  not_before timestamptz NOT NULL DEFAULT now(),
  last_error text
);

-- Entprellung: partieller Unique-Index, nicht als Tabellenbedingung möglich
CREATE UNIQUE INDEX job_pending_unique
  ON job (kind, key)
  WHERE state IN ('pending', 'running');
```

Der partielle Unique-Index auf offenen Aufträgen ist die Entprellung: hundert
neue Mails eines Projekts erzeugen **einen** `enrich`-Auftrag, nicht hundert.

### 7.2 Die Batch-API passt ins Auftragsmodell

Die Anreicherung ist nicht zeitkritisch und läuft über die Batch-API (§10.2 im
Entwurf, 50 % Rabatt). Das ist ein dreiphasiger Auftrag:

```
collecting ──► submitted ──► fetched
    │              │  (Anbieter-ID in payload)
    │              └──► bei Fehler: zurück auf 'collecting', einzeln erneut
    └──► Schwelle: Menge oder Alter
```

**Der Auftrag hält die Anbieter-Kennung**, nicht der Prozess. Ein Neustart
mitten im Lauf verliert nichts.

### 7.3 Nebenläufigkeit

Vier Regeln, und sie reichen:

1. **`append` ist die einzige Schreiboperation am Log**, serialisiert durch die
   Unique-Indizes auf `prev_hash` und `id` (§4.1) — nicht durch eine Sperre.
   Mehrere Prozesse dürfen gleichzeitig anfügen; der Verlierer wiederholt.
   Isolationsstufe **`READ COMMITTED`**, ausdrücklich und nicht per Default.
   **Stapeln ist das Mittel gegen Konkurrenz**: hundert Events in einer
   Transaktion belegen eine Kettenposition, nicht hundert — mit dem
   Gegenrisiko, dass sehr große Stapel verhungern können. Begrenzte
   Stapelgröße, begrenzte Wiederholungen; Herleitung in
   `2026-10-02-stufe-1a-log.md` §4.4.
2. **Projektionen sind pro Name einfädig.** Zwei Arbeiter an derselben
   Projektion sind ein Fehler, kein Durchsatzgewinn — der Vorschub `up_to_id`
   ist die Sperre.
3. **Reprojektion blockiert den Eingang nicht**: sie baut in eine
   Schattentabelle und schaltet am Ende um. Währenddessen wird weiter
   aufgenommen.
4. **Lesen sieht nie halbe Projektionen**, weil die Umschaltung in einer
   Transaktion passiert.

### 7.4 Fehlerverhalten

| Fehler | Verhalten |
|---|---|
| Konnektor nicht erreichbar | `not_before` verschieben, exponentiell, Wasserzeichen unverändert |
| Modellaufruf scheitert | Gate wiederholt begrenzt; danach Auftrag auf `failed`, Eintrag in die Queue |
| Rendern scheitert | **`action` wird trotzdem geschrieben**, mit Fehler im Ergebnis. Sonst fehlt die Spur |
| Kettenprüfung schlägt an | Alles Schreiben anhalten, Alarm. Kein Selbstheilungsversuch |
| Zielort `UNKNOWN` | Rendern blockiert, Queue-Eintrag |

Der dritte Punkt ist der, den man leicht falsch macht: ein gescheiterter Versuch
ist ein Ereignis. Nur erfolgreiche Handlungen zu protokollieren erzeugt ein Log,
das besser aussieht als die Wirklichkeit.

---

## 8. MCP-Schnittstelle

Zugrunde liegt **Revision 2026-07-28** (GA). Drei ihrer Eigenschaften prägen den
Entwurf, zwei widerlegen Ideen, die sonst naheliegend gewesen wären.

### 8.1 Zustandslos, Zustand über Handles

Kein `initialize`, keine Sessions, keine `Mcp-Session-Id`. Protokollversion und
Client-Fähigkeiten stehen je Aufruf in `_meta`; `server/discover` ist Pflicht.

Zustand über Aufrufe hinweg läuft über **servergeprägte Handles als gewöhnliche
Werkzeugparameter**. Bei uns ist das angenehm: **ein Handle ist eine `event.id`
oder eine `job.id`** — es gibt nichts zu erfinden und nichts zu verwalten.

### 8.2 Sampling ist abgekündigt — eine Idee weniger

Die naheliegende Versuchung wäre, den Server über `sampling/createMessage` das
Modell des Clients arbeiten zu lassen, also Pipeline-Arbeit über den Max-Plan.
**Das ist abgekündigt** (empfohlene Migration: direkt gegen die Anbieter-API),
und es soll nicht gebaut werden.

Damit bleibt die Arbeitsteilung aus §10.2 unverändert und ohne Hintertür: der
Max-Plan deckt die interaktive Arbeit, das Gate ruft für die Pipeline selbst.

Ebenfalls abgekündigt: **Roots** (Pfade über Parameter oder Konfiguration — der
Drop-Ordner wird konfiguriert, nicht erfragt) und **Logging** (stderr oder
OpenTelemetry).

### 8.3 Keine Stromwiederaufnahme — Idempotenz ist Pflicht

Bricht die Antwort ab, ist der Aufruf verloren und wird mit **neuer** Request-ID
wiederholt. Alle Schreibwerkzeuge müssen daher idempotent sein.

`submit` nimmt deshalb eine **vom Client vergebene Kennung** als `external_id`
(§4.2). Zweiter Aufruf, gleiche Kennung: dieselbe `event.id` zurück, kein
Duplikat.

### 8.4 Rückfragen: MRTR für blockierende, Werkzeuge für gestapelte

*Multi Round-Trip Requests* ersetzen Elicitation: der Server antwortet mit
`resultType: "input_required"` und `inputRequests`, der Client wiederholt den
Aufruf mit `inputResponses`. Korrelation über `requestState`.

**Das deckt genau eine der beiden Queue-Arten aus §8.4** — und bestätigt die
Trennung:

| | Mechanismus |
|---|---|
| **blockierende Rückfrage** — nötig, um *diesen* Aufruf abzuschließen | MRTR |
| **gestapelte Triage** — nach Hebelwirkung sortiert, aufschiebbar | eigene Werkzeuge |
| **Freigabe** — Befugnis, will gelesen werden | eigene Werkzeuge |

MRTR für die gestapelte Triage zu verwenden wäre falsch: sie ist
definitionsgemäß *nicht* blockierend (§6.4 im Entwurf).

### 8.5 Lange Läufe: die Tasks-Erweiterung

`io.modelcontextprotocol/tasks`, Abfrage über `tasks/get`, und Server dürfen
Task-Handles **unaufgefordert** zurückgeben. Genau passend für Bestandsimport
und Batch-Läufe: `start_import` gibt sofort ein Handle zurück, der Fortschritt
wird abgefragt.

### 8.6 Schemata: die Quellenpflicht wird erzwingbar

`inputSchema`/`outputSchema` erlauben jetzt beliebige
JSON-Schema-2020-12-Schlüsselwörter samt `$ref`. Damit ist die Quellenpflicht
aus §5.2 **schemaseitig** durchsetzbar statt erhofft: ein gemeinsames
`$defs.sources` mit `minItems: 1`, referenziert von jeder Art von `assertion`.

Ebenfalls Pflicht: `ttlMs` und `cacheScope` auf allen Listenergebnissen, und
`tools/list` **deterministisch sortiert** — letzteres ist kein Komfort, sondern
zahlt direkt auf die Prompt-Cache-Trefferquote und damit auf die Kosten ein.

### 8.7 Werkzeuge

Zustandslos, idempotent wo schreibend, strukturierte Ausgabe mit Schema.

| Werkzeug | Art | Anmerkung |
|---|---|---|
| **`previously`** | lesend | Zuschnitt `organization` \| `project` \| `matter`, optional Stichtag und Zeitordnung. Das Leitwerkzeug — siehe Anmerkung unten |
| `list_open_obligations` | lesend | Filter: Projekt, eigene/fremde/beobachtet |
| `list_decisions` | lesend | |
| `search` | lesend | der Rückfallpfad aus §18 im Entwurf |
| `get_event` / `get_units` | lesend | Zitaten folgen |
| `submit` | schreibend | Client-Kennung als `external_id`, idempotent |
| `record_assertion` | schreibend | Korrektur, `responsibility: {jens, direct}` |
| `list_triage` | lesend | nach Hebelwirkung sortiert |
| `answer_triage` | schreibend | |
| `list_approvals` | lesend | getrennt von der Triage (§10.3 im Entwurf) |
| `approve` / `reject` | schreibend | Ablehnung wird festgehalten (§10.4) |
| `start_import` | schreibend | gibt Task-Handle zurück |

**Zum Namen `previously`:** Der Aufruf liest sich wie der Satz, den er
beantwortet — `previously(project="auftraggeber-a")`. Damit ist er als einziges
Werkzeug **nicht verbgeführt**, während alle anderen es sind
(`list_…`, `get_…`, `record_…`). Das ist Absicht und soll nicht
„vereinheitlicht“ werden: es ist das Leitwerkzeug, und der Name ist
selbsterklärend.

Die vorige Fassung hieß `get_dossier`. Das war aus demselben Grund falsch, aus
dem `Dossier` bei der Namenssuche ausgeschlossen wurde — überwachungsnaher
Begriff für eine Ansicht, die schlicht eine Chronik mit Quellenangaben ist.

**Die Offenlegungsprüfung sitzt im `mcp_server`**, nicht im Kern: er ist der
zweite Durchsetzungspunkt aus §10.1 und entscheidet, was die interaktive Seite
überhaupt bekommt.

---

### 8.8 Das Cockpit ist austauschbar — und das ist der Zweck

Das Cockpit ist **ein MCP-Client, nichts weiter**. Claude Code heute (§14 im
Entwurf), eine eigene Oberfläche später, ein anderer Harness dazwischen — der
Kern merkt davon nichts. Das war der Grund, MCP als einzige Schnittstelle zu
wählen, und es heißt: **es gibt hier nichts zu entscheiden und nichts zu
bereuen.**

#### Zwei Fälle, in denen Claude Code nicht reicht

| Fall | Bedarf |
|---|---|
| Ein Projekt mit `local_only`-Auflage (§10.1 im Entwurf) | Ein Client, der gegen ein **lokales Modell** läuft |
| FOSS-Release (§2 im Entwurf) | "Du brauchst Claude Code" ist eine Abhängigkeit von einem kommerziellen Produkt |

#### Benannte Alternative: Pi (`pi.dev`)

Minimalistischer Terminal-Harness, MIT-Lizenz, kein Cloud-Backend, 15+
Modellanbieter einschließlich lokaler, **MCP eingebaut**, Betriebsarten
interaktiv / print-JSON / RPC / SDK. Erfüllt damit beide Fälle oben.

**Nicht heute einsetzen.** Claude Code bleibt das Cockpit, solange keiner der
beiden Fälle eintritt — Reifegrad gegen eine Abstraktion zu tauschen, die man
noch nicht braucht, wäre ein schlechter Handel. Die Alternative ist festgehalten,
damit sie im Bedarfsfall nicht erst gesucht werden muss.

**Zu klären, bevor es ein Argument wird:** Pi authentifiziert per API-Key *oder
OAuth*. Für API-Keys unproblematisch. Soll damit ein **Abo-Zugang** genutzt
werden, ist das dieselbe Frage wie in §8.2 — Abobedingungen decken die Produkte
des Anbieters, nicht Drittclients.

#### Wo ein Agent-Harness ausdrücklich **nicht** hingehört

Nicht in den `ai_layer`. Zwei Gründe, beide aus diesem Dokument:

1. **Wir wollen keine Agentenschleife.** Zuordnung, Zerlegung und Extraktion sind
   strukturierte Einzelaufrufe mit Ausgabeschema (§9). Eine Werkzeugschleife
   löst dort kein Problem und kostet Kontrolle über die Ausgabeform.
2. **Es würde das Gate umgehen** (§2, Regel 2). Ein Harness mit eigenen
   Anbieterverbindungen trägt weder Policy noch Audit noch den
   Verarbeitungsraum-Nachweis.

Ein Harness ist ein **Client**, kein Baustein der Pipeline. Diese Trennung sollte
beim nächsten interessanten Harness nicht neu diskutiert werden müssen.

## 9. Die Gate-Schnittstelle

```python
class Gate(Protocol):
    def call(self, task: TaskKind, payload: Payload,
             context: Context, output_schema: Mapping) -> Result: ...

@dataclass(frozen=True)
class Context:
    project: str | None
    confidentiality: Confidentiality
    allowed_processing_regions: list[str]      # aufgelöst nach §7.1 im Entwurf
```

Zwei Dinge, die das Gate **immer** tut und die nicht abschaltbar sind:

1. **Anbieter- und Modellwahl aus der Politik**, nicht aus dem Aufrufparameter.
   Der Aufrufer sagt *was*, nicht *womit*.
2. **Protokollieren**: Zeitpunkt, Aufgabe, Datenreferenzen (keine Kopien),
   Modell, Prompt-Version, **gesetzter und gemeldeter `processing_region`**,
   Ergebnis, Kosten. Abweichung zwischen gesetzt und gemeldet ist ein Alarm.

Zwei Adapter: Anthropic-SDK und OpenAI-kompatibel. Letzteres deckt OpenRouter,
Ollama und llama.cpp.

**Alle Modellausgaben sind strukturiert**, nie freier Text — das ist Leitsatz 1
in der Schnittstelle: `output_schema` ist ein Pflichtparameter, und `call`
validiert dagegen, bevor es zurückgibt.

---

## 10. Technische Festlegungen

Python, strikt typisiert (`pyright` im strict-Modus), PyO3 als benannter
Notausgang für Rust, maximal zwei Sprachen — siehe §2 im Entwurf.

### 10.1 SQLAlchemy Core, Pydantic, Alembic — kein ORM

| Schicht | Werkzeug |
|---|---|
| Schema und Abfragen | **SQLAlchemy Core** |
| Nutzlastvalidierung, MCP-Schemata | **Pydantic** |
| Migrationen | **Alembic** (arbeitet gegen Core-Metadaten) |

#### Begründung: ein append-only Speicher hat keine Verwendung für ein ORM

Der Wert eines ORM ist **Änderungsverfolgung** — Identity Map, Dirty Tracking,
Unit of Work, Lazy Loading, veränderliche Objektgraphen zusammenhalten. Hier
wird nie etwas geändert: es gibt `append` und Lesen, kein `UPDATE`, kein
`DELETE`, keine Beziehungsnavigation über Entitäten (§5).

Die Lesewege wollen auch keine Entitäten: Projektionen sind Zeilen, `stream` ist
ein Cursor, die Suche gibt Einheitenverweise. §5 verlangt "keine Rückgabe von
Datenbankobjekten" — ein ORM wäre die dauerhafte Versuchung, genau das zu tun.

#### Was `storage` zurückgibt

Die Frage fällt erst ohne ORM auf, und sie ist wichtig: `storage` kennt laut §2
**nichts** und kann daher keine Domänentypen zurückgeben.

Also liefert es **Zeilen ohne Domänenbedeutung** — `kind` als Text, `payload` als
rohes JSON, Zeitstempel, Hashes. Der Typ heißt deshalb `EventRow`, nicht
`Event`: `core` deutet die Zeile, `storage` transportiert sie nur.

```python
@dataclass(frozen=True)
class EventRow:
    id: int
    kind: str
    recorded_at: datetime
    occurred_at: datetime
    hash: bytes
    prev_hash: bytes | None
    payload: Mapping[str, object]      # rohes JSON, ungedeutet
```

Mit einem ORM wären hier stillschweigend Entitäten über die Modulgrenze
gereicht worden.

#### Verworfen: SQLModel

War als Vorgabe im Gespräch und wurde nach Prüfung verworfen. Die Begründung
steht hier, damit später nachvollziehbar ist, warum es so ist und nicht anders:

- **Sein Verkaufsargument löst unser Problem nicht.** SQLModel koppelt Tabelle
  und Validierungsmodell in einer Klasse. Diese Architektur **trennt** sie
  absichtlich: stabile äußere Tabelle, veränderliche validierte Nutzlast (§4.1,
  Leitsatz 9). Die Pydantic-Modelle, die wirklich gebraucht werden, sind die der
  `assertion`-Arten — und die sind **keine Tabellen**.
- **Fünf Tabellen, fast keine Beziehungen.** Die gesparte Boilerplate liegt in
  der Größenordnung von dreißig Zeilen.
- **Alle harten Pfade liegen außerhalb**: Vektorsuche mit Vorfilter,
  serverseitige Cursor, `FOR UPDATE SKIP LOCKED`, partielle Unique-Indizes,
  `tsvector`-Operatoren.
- **Projektionen werden in Massen geschrieben**, nicht zeilenweise — das will
  `COPY` oder `executemany`. Bei Reprojektion über Jahre Historie ist der
  Identity-Map-Aufwand kein akademisches Thema.
- **`pyright` im strict-Modus** ist Auflage (§2 im Entwurf). SQLModel hat dort
  historisch Reibung erzeugt; ein Werkzeug, das `# type: ignore` erzwingt,
  kollidiert mit einer bereits getroffenen Entscheidung.

**Wann das neu zu bewerten ist:** kommt Teil 5 als FastAPI-Oberfläche, zahlt
sich SQLModels Kopplung von API- und DB-Modell genau dort aus. Teil 5 ist
verschoben (§14 im Entwurf); die Frage wird dann erneut gestellt, nicht früher.

#### Die Zuständigkeitsgrenze, die Leitsatz 3 schützt

Unabhängig vom ORM gilt für Alembic:

> **Alembic migriert `event`, `source_key`, `unit`, `job` und
> `projection_state`. Projektionstabellen (`p_*`) werden von Code erzeugt und
> verworfen, nicht migriert.**

Treten Projektionen als migrierte Tabellen auf, hat jemand sie versehentlich
schemabehaftet gemacht — und wird sie beim nächsten Logikwechsel *migrieren*
statt neu zu bauen. Leitsatz 3 wäre beschädigt, und zwar lautlos. Beim
Versionssprung einer Projektion: `DROP` und neu bauen (§4.4).

Die erste Migration richtet die Erweiterungen ein (`CREATE EXTENSION`) —
`vector` und, je nach Ergebnis des Messversuchs, `vchord_bm25` und
`pg_tokenizer`.

#### Drei Pfade mit besonderem Zugriff

| Pfad | Umsetzung |
|---|---|
| `stream` als Iterator | serverseitiger Cursor (`stream_results`), darf nichts materialisieren |
| Projektionen schreiben | `COPY` oder `executemany`, nicht zeilenweise |
| Vektorsuche mit Vorfilter | `pgvector.sqlalchemy` für den `vector`-Typ, Indexsteuerung in rohem SQL |

### 10.2 Modularer Monolith mit mehreren Einsprungpunkten

**Ein Codestand, ein Abhängigkeitssatz, eine Datenbank, eine Version — und
mehrere daraus gestartete Prozesse.** Keine Microservices.

Die Frage "ein Prozess oder viele" stellt sich nicht: §7.1 beschreibt schon
sechs. Die Frage ist, ob sie **unabhängig ausgelieferte Dienste mit
Netzschnittstellen** sind. Sie sind es nicht.

#### Warum nicht

- **Microservices würden Grenzen kaufen, die schon bestehen.** §2 legt die
  Modulgrenzen mit drei **statisch prüfbaren** Regeln fest. Das ist genau der
  Nutzen, für den man sonst Netzgrenzen zieht — ohne Serialisierung,
  Versionierung und verteiltes Debugging.
- **Sie müssten sich dieselbe Datenbank teilen**, und Dienste mit geteilter
  Datenbank sind ein verteilter Monolith mit Zusatzaufwand. Teilen lässt sich
  die Datenbank hier auch nicht: der Entwurf ruht auf **einem** append-only Log,
  aus dem alles projiziert wird. **Das Log ist der Integrationspunkt.**
- **Die Architektur ist schon ereignisgetrieben.** Module rufen sich nicht auf —
  sie fügen an und projizieren. Das ist dieselbe lose Kopplung, die
  Microservices anstreben, prozessintern erreicht. Das Netz würde nichts
  entkoppeln, was nicht schon entkoppelt ist.
- **Ein Benutzer.** Kein Bedarf, etwas unabhängig zu skalieren.
- **Der FOSS-Gedanke schneidet umgekehrt:** etwas, das man mit einem Postgres
  daneben installiert und startet, wird benutzt. Acht Dienste mit Compose-Datei
  werden angeschaut.

#### Die Verwechslung, die das Thema meist trägt

> **Gute Schnitte sind die Voraussetzung für Microservices, nicht der Grund
> dafür.**

Der Grund wären unabhängige Skalierung, unabhängige Auslieferungstakte oder
Teamgrenzen — bei einem Benutzer und einem Entwickler existiert keiner davon.
Die Schnitte sind gut, und genau deshalb brauchen sie kein Netz dazwischen.

> **Modulgrenzen trennen Verantwortung. Prozessgrenzen trennen Laufzeitbedarf.**

Zwei Achsen. Sie zu verwechseln ist der Weg zu Microservices, die niemand
braucht.

#### Zwei vorgemerkte Nähte

Nach der Regel oben — unterschiedlicher **Laufzeitbedarf**, nicht
unterschiedliche Verantwortung:

| Naht | Grund |
|---|---|
| **Voice** (Teil 2) | braucht PipeWire-Zugriff, läuft also dort, wo das Audio ist — nicht wo die Datenbank steht. Dazu Torch, viel RAM, eigener Lebenszyklus. Reine Eingangsrichtung |
| **Embeddings** | Modell laden, speicherintensiv; wandert bei eigener GPU-Hardware dorthin. Reine Eingangsrichtung |

Beide brauchen **keine Netzschnittstelle zum Rest** — sie brauchen Zugriff auf
das Log. Das ist ein Datenbankzugang, kein Dienstvertrag.

### 10.3 Blob-Speicher: inhaltsadressiert, privat

Binär fällt an: Mail-Anhänge, PDFs aus dem Drop-Ordner, Bilder in Issues.
Größenordnung über fünf Jahre etwa 50 GB — vergleichbar mit oder größer als
der Text. **Audio fällt nicht an**: transkribieren, nicht aufbewahren (§10.2 im
Entwurf).

**Nicht in Postgres.** Technisch ginge `bytea`, aber jedes Base-Backup kopiert
alle Blobs, die WAL-Menge steigt mit jedem Anhang, Point-in-Time-Recovery wird
teuer, und `stream` müsste die Blobs sorgfältig aussparen, sonst zieht die
Reprojektion 50 GB durch den Speicher.

**S3-kompatibel ist keine neue Abhängigkeit:** CNPG archiviert Base-Backups und
WAL ohnehin gegen Objektspeicher.

#### Inhaltsadressiert — die Form, die zum Log passt

Liegt ein Blob außerhalb und das Log hält nur eine URL, ist das Log nicht mehr
selbsttragend und die Hash-Kette deckt den Inhalt nicht ab. **Daher steht der
Blob-Hash im Log, und der Hash ist der Schlüssel:**

```
observation
  …
  blob: { hash: sha256, media_type, size, ref, key_id }   # hash = Klartext-Hash
```

| Eigenschaft | Folge |
|---|---|
| Die Kette deckt den Blob mit | nicht die Bytes, aber ihre Identität — Austausch nachweisbar, Fehlen erkennbar |
| Deduplizierung gratis | derselbe Anhang fünfmal weitergeleitet ist ein Objekt |
| **Append-only von Bauart** | ein Objekt unter seinem Hash lässt sich nicht ändern, nur neu schreiben |

**Aufteilungsregel: Postgres hält, was durchsucht und projiziert wird — der
Objektspeicher hält, was belegt.** Das deckt sich mit `evidence: verbatim`: der
Blob *ist* der Wortlaut.

Dateien aus dem Nextcloud-Drop-Ordner werden **kopiert, nicht verlinkt**.
Nextcloud ist Konnektor, kein Wahrheitsspeicher (§11.1 im Entwurf) — löscht
dort jemand die Datei, muss der Beleg überleben.

Ein Adapter, S3-kompatibel; lokaler Dateisystem-Adapter für die
Entwicklungsmaschine, damit dort kein MinIO nötig ist.

**Blobs werden client-seitig verschlüsselt** (AES-GCM, `key_id` in der
Referenz) — Begründung und die Verschränkung mit der Inhaltsadressierung in
§4.6.

#### Private Buckets, keine öffentlichen

Das kostet heute **nichts**, weil kein Pfad eine URL nach außen gibt:

| Zugriff | Weg | URL nach außen? |
|---|---|---|
| Pipeline liest Blob zur Textextraktion | im Cluster, Dienst-Zugangsdaten | nein |
| Jens schaut ein Dokument an | MCP-Server holt es und legt es lokal ab, oder liefert den Text | nein |
| Anhang in ein Fremdsystem rendern | die Anwendung lädt die Bytes hoch | nein |

Presigned URLs werden erst mit Teil 5 zur Frage. Die Regel steht jetzt hier,
solange sie gratis ist.

**Drei Regeln:**

1. **Zwei Buckets, zwei Zugangsdaten — die Anwendung erreicht den
   CNPG-Backup-Bucket nicht, auch nicht lesend.** Der Backup-Bucket enthält die
   ganze Datenbank, dauerhaft und vollständig; ein kompromittierter
   Anwendungsprozess darf daraus keinen Totalverlust machen.
2. **Gerenderte Artefakte verlinken nie in den eigenen Bucket.** Ein Link wäre
   entweder öffentlich (verboten) oder für den Empfänger kaputt (nutzlos). Also
   Kopie hochladen oder nur benennen — verlustbehaftetes Rendern ist erlaubt
   (§11.1 im Entwurf).
3. **Wenn Presigning kommt: kurze Laufzeit, Ausgabe protokolliert.** Eine
   ausgegebene signierte URL wirkt für jeden, der sie hat, bis sie abläuft — sie
   **umgeht die Offenlegungsprüfung nach der Ausgabe**. Für alles, was das Haus
   verlässt, lieber durch die Anwendung proxyen als signieren.

### 10.4 Deployment und Datenpolitik im Ruhezustand

**cdk8s-Charts, ArgoCD, CNPG-Operator. Hetzner, EU — Standorte DE und FI.**

**Backup über das pgBackRest-CNPG-I-Plugin, mit clientseitiger
Verschlüsselung** (`encryption: aes-256-cbc`, Schlüssel aus einem Secret) —
Begründung in §10.5.

Damit ist die Speicherseite der Datenpolitik (§7.1 im Entwurf) **einmalig und
durch das Deployment** erfüllt, nicht pro Aufruf.

Das ist keine Nebenbemerkung: ein Modellaufruf ist flüchtig, der Bucket hält
alles dauerhaft. Läge er außerhalb des erlaubten Raums, wäre die Politik **im
Ruhezustand** verletzt — deutlich schwerer als ein einzelner Inferenzaufruf.

> **Ruhezustand durch Deployment, Verarbeitung durch das Gate.** Zwei Fragen,
> zwei Orte.

**Zum Schweiz-Fall:** Soweit bekannt erkennen EU und Schweiz einander
gegenseitig als angemessenes Datenschutzniveau an. Daten eines Schweizer
Auftraggebers in DE oder FI zu verarbeiten ist damit normalerweise
unproblematisch; der Unterschied zwischen revDSG und DSGVO betrifft das
**anwendbare Recht** für unsere Pflichten, nicht den **Hostingort**. Keine
Rechtsauskunft — im konkreten Vertrag zu prüfen.

**Grenze der Ein-Instanz-Bauweise:** Eine Datenbank hält alle Projekte, also
lässt sich der Speicherort nicht pro Projekt auflösen. Nach Leitsatz 8 gilt die
strengste Auflage — das Deployment ist so eingeschränkt wie der restriktivste
Auftraggeber. Verlangt einer einmal Verarbeitung ausschließlich in einem Raum,
den dieses Deployment nicht abdeckt, braucht er eine getrennte Instanz oder
bleibt lokal.

**Die zwei Standorte gegeneinander ausgespielt:**

| Bucket | Standort | Grund |
|---|---|---|
| Blob-Speicher der Anwendung | **beim Cluster** | sonst zahlt jeder Blob-Zugriff die Laufzeit zwischen den Standorten |
| CNPG-Backup | **im anderen Standort** | Cluster und Backup fallen nicht gemeinsam aus |

Das verstärkt Regel 1 oben aus einem **zweiten, unabhängigen Grund**: die
Trennung ist sicherheitsseitig richtig *und* betrieblich.

### 10.5 Backup-Verschlüsselung: pgBackRest statt barman-cloud

**Problem.** Hetzner Object Storage bietet nur SSE-C (§4.6), und
`barman-cloud-backup` sowie `barman-cloud-wal-archive` unterstützen **nur
serverseitige** Verschlüsselung (AES256, aws:kms). Barman klassisch kann
GPG-Verschlüsselung, die Cloud-Werkzeuge nicht — es gibt dazu eine offene
Anfrage. Die vollständige Datenbank würde damit unverschlüsselt im Bucket
liegen.

**Nachgeprüft am 2026-10-03 gegen Hetzners Dokumentation**, und die Lage ist
schärfer als dieser Absatz zunächst sagte:

> „There is **no default data-at-rest encryption** of objects, but you can
> encrypt your data during the upload using SSE-C."

Es gibt dort also nicht nur kein SSE-S3 — es gibt **gar keine**
Verschlüsselung im Ruhezustand, solange niemand selbst eine anwendet.
Clientseitig ist damit nicht die bequemere Variante, sondern die einzige, die
überhaupt etwas verschlüsselt.

Und SSE-C ist für ein Backupwerkzeug nicht bloß unbequem, sondern gefährlich:

> „Only this encryption type: SSE-C" · „**Copy of SSE-C encrypted objects: Not
> supported**" · CopyObject: „Only supported within the same Bucket."

Die Ursache ist die Technik darunter — Hetzner bestätigt „Any data you save in
your Bucket is saved in a **Ceph** cluster", und in Ceph RGW hat **keiner** der
SSE-Modi CopyObject-Unterstützung. Jeder Ablauf, der verschlüsselte Objekte
kopiert, bricht dort. Das ist in einem Schwesterprojekt (kup6s) schon
operativ aufgeschlagen: dort gilt die Regel „never use server-side
encryption", zusammen mit dem Umweg um die Tagging-Aufrufe, die Hetzner mit
`501` abweist.

**Lösung.** Das **pgBackRest-CNPG-I-Plugin** kann clientseitige
Verschlüsselung von Backups **und** WAL-Archiven (`encryption: aes-256-cbc`,
Schlüssel aus einem Secret), dazu Datenverzeichnis-Backup und -Restore,
WAL-Archivierung, PITR und Replica-Cluster. Hetzners fehlendes SSE-S3 ist
damit irrelevant: die Daten sind verschlüsselt, bevor sie den Cluster verlassen.

Implementierungen von Dalibo und Opera Software. **Welche zur Bauzeit die
bestgepflegte ist, ist nachzusehen** — hier ein datierter Stand, damit das
Nachsehen nicht bei null anfängt.

#### Stand der beiden Plugins am 2026-10-03

| | `dalibo/cnpg-plugin-pgbackrest` | `operasoftware/cnpg-plugin-pgbackrest` |
|---|---|---|
| Commits seit 03.07.2026 | **2** | **30** |
| letzte Freigaben | v0.0.3 (25.06.) | v0.8.0 (25.08.), v0.7.0, v0.6.1 |
| offene Vorgänge | 23 | 44 |
| Selbstauskunft | — | README: „**Status:** EXPERIMENTAL" |

Das **dreht die Erwartung**: dieser Abschnitt nannte Operas Implementierung
anfangs „ausdrücklich experimentell" und legte damit Dalibos näher. Gemessen
ist Dalibos seit Juni praktisch stehengeblieben, während Operas im August
wöchentlich freigegeben hat. Operas README trägt den
Experimentell-Vermerk weiterhin — es ist also nicht „das reifere", sondern
**das, an dem gearbeitet wird**.

Operas Plugin nennt ausdrücklich, was dieser Abschnitt braucht:
„Client-side encryption of both backups **and** WAL archives",
`encryption: aes-256-cbc` mit `encryptionKey` aus einem Secret, CNPG ab 1.25.

Keines von beiden nennt sich produktionsreif. Die Wahl bleibt darum eine
Bauzeit-Entscheidung; das Kriterium ist nicht die Versionsnummer (0.0.3 gegen
0.8.0 ist eher Zählweise als Reife), sondern **ob zum Zeitpunkt des Baus noch
jemand daran arbeitet**. Dieselbe Tabelle neu erheben, nicht diese lesen.

#### Eine Warnung für die nächste Pflegeprüfung

Zu **pgBackRest selbst** zirkulieren Artikel, die behaupten, das Projekt sei
archiviert bzw. werde nicht mehr gepflegt. **Das ist falsch**, am 2026-10-03
gegen die GitHub-API geprüft: `archived: false`, letzter Push am 02.10.2026,
24 Commits in den letzten 30 Tagen, drei Freigaben in drei Monaten (2.59.0 im
Juli, 2.59.1 im August, 2.59.2 am 27.09.).

Wer die Pflege das nächste Mal prüft, wird über dieselben Seiten stolpern.
Sie sind ein Beispiel für genau das, wogegen §10.7 die Pflegeprüfung
verlangt: eine Behauptung über Pflege ist gegen das Repository zu prüfen,
nicht gegen eine Überschrift.

#### Warum das keine Abwägung ist

Es sieht aus wie *bewährtes barman gegen junges Plugin*. Ist es nicht:
`barmanObjectStore` ist in CNPG seit 1.26 **abgekündigt** und soll mit 1.30
entfernt werden; Nachfolger ist das **Barman-Cloud-Plugin** — also ebenfalls ein
CNPG-I-Plugin, ebenfalls neu.

> **Zwei neue Plugins, und nur eines verschlüsselt.**

#### Was es architektonisch aufräumt

Die Backup-Verschlüsselung folgt damit derselben Linie wie die Blobs (§4.6):
**clientseitig, Schlüssel außerhalb des Datenpfads.** Ein Grundsatz, zwei
Stellen — statt verschlüsselter Blobs neben einer unverschlüsselten Datenbank.

**Getrennte Schlüssel für Blobs und Backups, gleicher Tresor.** Unterschiedliche
Schadensreichweite, also nicht derselbe Schlüssel.

#### Wo die Schlüssel liegen — und warum das hier aufhört

Beide Verschlüsselungsstellen dieses Entwurfs brauchen einen Schlüssel von
außerhalb des Datenpfads: die Blobs (§10.3, AES-GCM mit `key_id` in der
Referenz) und die Backups (clientseitig, `aes-256-cbc`).

Stand heute kommen sie über den **External Secrets Operator** aus einem
**eigenen Namespace** — also nicht aus dem Namespace, in dem die Datenbank
läuft. Das ist die betriebliche Antwort auf „gleicher Tresor": ein Ort, zwei
Schlüssel, und beide außerhalb der Reichweite dessen, was sie schützen.

**Ein echter Tresor (Vault) ist die Zielrichtung, aber nicht Sache dieses
Projekts.** Das ist eine Plattformentscheidung und gehört dorthin, wo die
Cluster bewirtschaftet werden — nicht in diese Architektur. Previously
verlangt von der Plattform nur zwei Eigenschaften, und beide sind unabhängig
davon, womit sie erfüllt werden:

1. Die Schlüssel liegen **nicht** im Namespace der Datenbank und nicht im
   Backupziel.
2. Es gibt einen **geprobten** Weg, sie wiederzubeschaffen — denn nach dem
   Absatz oben verliert man mit der Passphrase die Backups endgültig.

Damit ist die Frage „welcher Tresor" hier zu Recht **nicht** offen: sie ist
delegiert, mit zwei nachprüfbaren Anforderungen anstelle einer Antwort.

#### Der Preis der clientseitigen Verschlüsselung

Er gehört dazugesagt, weil er aus derselben Familie ist wie alles in diesem
Entwurf: **wer die Passphrase verliert, verliert die Backups, endgültig.** Bei
serverseitiger Verschlüsselung hält der Anbieter den Schlüssel und kann im
Zweifel helfen; hier kann es niemand. Daraus folgen zwei Vorgaben:

- Die Passphrase muss **vor dem ersten Backup** stehen. Ein Wechsel später ist
  eine Operation über das ganze Repository, nicht ein Konfigurationseintrag.
- Sie braucht dieselbe Sorgfalt wie die Daten selbst: im Tresor, mit einem
  dokumentierten Wiederherstellungsweg, und geprüft — ein Schlüssel, mit dem
  nie ein Restore versucht wurde, ist so wenig ein Schlüssel wie ein
  ungeprüfter Restore ein Backup ist.

#### Die verbleibenden Einwände und ihre Antworten

**Erstens: Plugin-Reife.** Ein Backup-System ist die schlechteste Stelle für
junge Software — aber die Antwort darauf ist von der Pluginwahl unabhängig:

> **Ein ungeprüfter Restore ist kein Backup.**

Siehe Abnahmebedingung 23. Bei uns ist die Prüfung besonders aussagekräftig,
weil die Hash-Kette den **wiederhergestellten Bestand** verifiziert und nicht
nur, dass Postgres startet.

**Zweitens: zwei Backupwerkzeuge im selben Betrieb.** Im übrigen Cluster
läuft barman; dieser Entwurf setzt pgBackRest daneben. Das kostet zwei
Betriebswege, zwei Restore-Prozeduren — und nach dem Grundsatz eben heißt das
**zwei Proben einüben**, nicht eine. Der Einwand ist berechtigt und war in
diesem Abschnitt zunächst gar nicht genannt.

Drei Wege, mit ihrem jeweiligen Preis:

| | Weg | Preis |
|---|---|---|
| **A** | pgBackRest nur für diese Datenbank | ein zweites Werkzeug, zweite Restore-Probe |
| **B** | barman-cloud behalten, Backupziel auf ein EU-S3 mit echtem SSE-S3 | zweite Anbieterbeziehung, **der Anbieter hält den Schlüssel** |
| **C** | barman-cloud behalten, Backups unverschlüsselt | nichts technisch — aber es muss eine *Entscheidung* sein, kein Versehen |

**Gewählt ist A**, und der Grund ist nicht Werkzeuggüte, sondern wer den
Schlüssel hat: bei A verlässt er die eigene Maschine nicht, bei B kann der
Anbieter im Zweifel entschlüsseln, bei C jeder, der an das Bucket kommt. Für
einen Speicher, dessen ganzer Zweck ein verteidigungsfähiger Verlauf von
Mandantenprojekten ist, ist das der entscheidende Unterschied.

**Was A umstoßen würde:** wenn die Backups dieser Datenbank im Bedrohungsmodell
nicht anders stünden als die der übrigen Cluster-Datenbanken. Dann gewinnt
Einheitlichkeit und B ist die saubere Wahl. Diese Prüfung ist nicht
geführt — sie hängt daran, was in den anderen Datenbanken liegt, und das ist
eine Frage an den Betrieb, nicht an diese Architektur.

Dass das Schwesterprojekt kup6s denselben Punkt offen hat — barman-cloud auf
Hetzner, ohne Verschlüsselung — ist dabei kein Argument für A, sondern nur der
Beleg, dass die Lücke real ist und nicht aus diesem Entwurf stammt.

### 10.6 Werkzeuge

Grundlage ist die bestehende Praxis in `zodb-pgjsonb` — übernommen, nicht neu
erfunden. Ergänzt um das, was dieses Projekt zusätzlich braucht.

| Zweck | Werkzeug |
|---|---|
| Abhängigkeiten | **uv**, Lockfile committet |
| Build und Version | **hatchling** + **hatch-vcs** (Version aus Git-Tags) |
| Lint und Format | **ruff** |
| Typprüfung | **pyright**, strict |
| Architekturgrenzen | **import-linter** |
| Tests | **pytest**, **pytest-cov**, **coverage** (`fail_under = 90`) |
| Datenbank im Test | **testcontainers[postgres]** — echtes Postgres, kein Mock |
| Invarianten | **hypothesis** |
| Testreihenfolge | **pytest-randomly** |
| Hooks | **pre-commit** |
| Schwachstellen | **pip-audit** in CI |

Python **3.14**, `requires-python = ">=3.14"`, `target-version = "py314"`.

#### Typprüfung: pyright, und der Grund ist unspektakulär

Stand Oktober 2026 liegen **Pyrefly** (Meta, Rust, stabil 1.0 seit Mai 2026,
~98 % Konformität zur Typing-Spezifikation) und **pyright** (~97 %) sachlich
gleichauf. Pyrefly ist 10–50× schneller als mypy — **bei dieser Projektgröße
ist das theoretisch.**

Also entscheidet ein praktischer Punkt: **pyright läuft über Pylance schon im
Editor.** Derselbe Prüfer in Editor und CI vermeidet „läuft bei mir, scheitert
in CI". **Pyrefly ist die benannte Alternative**; der Wechsel ist billig, weil
beide normale Annotationen lesen.

**`ty` (Astral) fällt raus**, und nicht weil es unreif ist (Beta), sondern aus
einem schärferen Grund: strikte Typisierung setzt hier **Architekturgrenzen**
durch (§2). Ein Prüfer mit ~53 % Spezifikationsabdeckung liefert *falsche
Sicherheit*, und die ist schlechter als keine. Für den Editor interessant, für
CI nicht.

#### import-linter macht §2 wahr

§2 behauptet drei **statisch prüfbare** Grenzregeln. Ruff kann das nicht
ausdrücken — „`core` darf nicht aus `connectors` importieren" ist eine
Schichtenregel, keine Stilregel. `import-linter` kann es mit `layers`- und
`forbidden`-Verträgen.

**Damit wird aus einer Spec-Zusage ein Test.** Die drei Regeln aus §2 werden als
Verträge hinterlegt und in CI geprüft.

#### Ruff: vier Gruppen über die bestehende Auswahl hinaus

| Gruppe | Warum **hier** |
|---|---|
| **`DTZ`** | verbietet naive `datetime`. `recorded_at` und `occurred_at` sind `timestamptz` — ein naiver Zeitstempel in der Chronik bleibt jahrelang unentdeckt |
| **`S`** | fest eingebaute Geheimnisse, schwache Krypto, SQL-Verkettung. Wir verschlüsseln Blobs und verwalten Schlüssel |
| **`TID`** | verbietet relative Importe — hält die Modulgrenzen für import-linter lesbar |
| **`TC`** | Typ-nur-Importe nach `TYPE_CHECKING` — trennt Laufzeit- von Typabhängigkeiten |

Dazu eine Unstimmigkeit aus der Vorlage beheben: `max-line-length = 120` bei
ignoriertem `E501`, während `[tool.ruff] line-length` ungesetzt (also 88) ist —
der Formatter bricht bei 88, der Linter schweigt. **`line-length` einmal oben
setzen.**

#### Synchron, nicht async

Eigene Entscheidung, nicht Bequemlichkeit: das Nebenläufigkeitsmodell aus §7.3
sind **mehrere Arbeiterprozesse mit `SKIP LOCKED`**, nicht viele Koroutinen in
einem Prozess. Bei sechs Prozessen und einem Benutzer kauft async Komplexität
ohne Gegenwert. Damit entfällt auch die Ruff-Gruppe `ASYNC`.

#### hypothesis für die Invarianten

„Neu gebaut ergibt dasselbe Ergebnis" (Abnahmebedingung 2) und „keine
Verzweigung der Kette möglich" (§4.1) sind **Invarianten über zufällige
Event-Folgen**, keine Beispieltests. Eine der wenigen Stellen, an denen
eigenschaftsbasiertes Testen klar überlegen ist.

`pytest-randomly` dazu: bei Tests mit Datenbankzustand findet zufällige
Reihenfolge Abhängigkeiten zwischen Tests, die sonst erst in CI auffallen.

### 10.7 Abhängigkeiten: keine Zombies, und zwar prüfbar

**Methode.** Der Pflegezustand wird nicht geschätzt, sondern am
Veröffentlichungsdatum gemessen — die PyPI-JSON-Schnittstelle
(`https://pypi.org/pypi/<paket>/json`) liefert Version und Datum der letzten
Veröffentlichung. Das ist ein Einzeiler und gilt für jede neue Abhängigkeit.

**Ein Datum allein entscheidet aber nichts.** Ein triviales, stabiles Paket darf
alt sein; eine komplexe Bibliothek nicht. Deshalb gehört zum Datum ein Urteil,
und das Urteil gehört aufgeschrieben — sonst wird es beim nächsten Mal neu
gefällt.

**Abhängigkeits-Register** (`DEPENDENCIES.md`), je Eintrag:

- **wofür** — welcher Zweck, welches Modul
- **Alternative verworfen weil** — damit die Frage nicht wiederkehrt
- **zuletzt geprüft am** — mit Urteil, nicht nur Datum

Worked example aus der ersten Prüfung: **`hatch-vcs`, letzte Veröffentlichung
vor über einem Jahr** — bewertet als **fertig, nicht verlassen**, weil es ein
paar Zeilen Klebstoff um `setuptools-scm` ist. Genau dieses Urteil ist der Grund
für das Register: die Zahl allein hätte einen Fehlalarm ausgelöst.

Dazu **`pip-audit`** in CI für Schwachstellen und **Renovate** für
Aktualisierungen. Beides deckt etwas anderes ab als der Pflegezustand: CVEs und
Versionsstand sind nicht dasselbe wie „lebt das Projekt noch".

## 11. Was bewusst offen bleibt

Nach dem Aufnahmekriterium aus §1 gehört nichts davon hierher.

| offen | entschieden in |
|---|---|
| Textsuchvariante (Hunspell / Subword / BM25) | Messversuch §12.3 im Entwurf |
| Konkretes Embedding-Modell (mehrsprachig, lokal) und damit `N` | Teilprojekt 1 |
| ORM-Detailabbildung der Projektionen | je Teilprojekt, innerhalb der Grenze aus §10.1 |
| Interne Abgleichlogik je Konnektor | je Konnektor |
| Prompt- und Templatetexte | Teilprojekt 5 |
| Rangfunktion der Triage-Hebelwirkung | Teilprojekt 5, messbar nachjustierbar |
| Deployment-*Mechanismus* (Container, systemd, k3s) | Betriebsentscheidung, kein Modul hängt daran. Die Architekturfrage ist in §10.2 entschieden |
| Oberfläche jenseits MCP | verschoben (§14 im Entwurf) |

### Nachtrag 2026-10-03: Deutsch und Englisch, und zwar gemischt

Zwei Zeilen dieser Tabelle — Textsuchvariante und Embedding-Modell — standen
bisher unter „mehrsprachig". Der Auftraggeber hat das verschärft, und die
Verschärfung ändert, was dort entschieden werden kann:

> **Deutsch und Englisch sind immer beide da, oft im Mix** — und zwar nicht
> nur im Bestand, sondern **innerhalb eines Dokuments**. Das Projekt soll in
> beiden Sprachen bedienbar sein.

Innerhalb eines Dokuments gemischt ist etwas anderes als mehrsprachig. Was es
für die zwei offenen Punkte heißt:

- **Textsuche:** Hunspell arbeitet mit Wörterbüchern **je Sprache**. Bei einer
  Einheit, die beide Sprachen trägt, ist die Frage nicht mehr „welches
  Wörterbuch", sondern „woher weiß ich die Sprache dieser Einheit" — und bei
  einem Satz mit englischen Fachwörtern in deutscher Prosa gibt es darauf
  keine Antwort, die nicht selbst eine Schätzung ist. Das spricht für ein
  sprachunabhängiges Verfahren (Subword, BM25) und gegen Spracherkennung je
  Einheit. **Entschieden wird es trotzdem erst mit der Messung aus §12.3** —
  hier steht nur, dass die Messung diesen Fall enthalten muss.
- **Embedding-Modell:** „mehrsprachig" genügt als Anforderung nicht. Ein
  Modell, das Deutsch und Englisch getrennt gut kann, ist nicht dasselbe wie
  eines, das einen **gemischten** Satz in einen sinnvollen Vektor legt. Die
  Auswahl braucht darum einen Testsatz aus echten, gemischten Einheiten, nicht
  zwei getrennte Sprachproben.

**Ausdrücklich keine Entscheidung in diesem Dokument.** Die Mehrsprachigkeit
der **Bedienung** (Ein- und Ausgabe des Werkzeugs, Prompts, Oberfläche) ist
noch gar nicht betrachtet und gehört in einen eigenen Entwurf; sie ist von der
Mehrsprachigkeit der **Daten** zu trennen, die hier steht.

---

## 12. Zerlegung in Teilprojekte

Reihenfolge aus §14 im Entwurf, mit der Kaltstart-Vorgabe aus §8.1.

| # | Teilprojekt | Umfang |
|---|---|---|
| **1** | **`core` und `storage`** | in drei Stufen, siehe §12.1 |
| 2 | **`contract` und manueller Einwurf** | `contract`, Drop-Ordner, Einwurf per Prompt, Quelle verlinken |
| 3 | **`mcp_server`** | Protokoll 2026-07-28, Werkzeuge, Handles, Offenlegungsprüfung |
| 4 | **`gate`** | Policy, Adapter, Audit, `processing_region` |
| 5 | **`ai_layer` und Triage** | Zeitliche und inhaltliche Signale, Zerlegung, Triage |
| 6 | **IMAP** | Konnektor nach Vertrag |
| 7 | **Identitätsgraph und Beteiligtenregel** | strukturelle Signale, rückwirkend auf die Historie |
| 8 | **Bestandsimport** | Pilotprojekt, Batch-Läufe |

**Teilprojekt 1 ist der einzige echte Flaschenhals** — alles andere hängt daran.
Teilprojekte 3, 4 und 6 sind danach voneinander unabhängig.

### 12.1 Teilprojekt 1 in drei Stufen

Drei unabhängig prüfbare Mechanismen, nicht ein Block.

| Stufe | Inhalt | Nachweis |
|---|---|---|
| **1a Der Log** | `event`, `payload_hash`, Hash-Kette, `append` mit Unique-Index auf `prev_hash`, Kettenprüfung, `unit`, `source_key` | Events schreiben, Kette verifizieren, Idempotenz belegen, Verzweigung als unmöglich zeigen |
| **1b Projektionen** | `projection_state`, Versionssprung, Schattentabelle mit Umschaltung, Reprojektion als Stream | Projektion bauen, Version erhöhen, neu bauen, identisches Ergebnis zeigen, Eingang läuft weiter |
| **1c Blobs** | inhaltsadressiert, clientseitige Verschlüsselung, Schlüsselbehandlung, lokaler Dateisystem-Adapter, Tilgungs-Vorkehrungen (§4.6) | Blob ablegen, Dedup zeigen, Verschlüsselung zeigen, Löschen zeigen |

**Jede Stufe muss lauffähig sein**, einschließlich Migrationen und Testaufbau —
nicht weil es nützlich ist, sondern weil **Lauffähigkeit Dinge hervortreibt, die
man sonst vergisst.** Eine Stufe, die nur als Spezifikation existiert, hat ihre
Annahmen nicht geprüft. Das zieht Alembic und Testinfrastruktur in 1a hinein,
und das ist beabsichtigt.

**Detail-Spec: `2026-10-02-stufe-1a-log.md`.**

**1a** ist das irreduzible Fundament und vollständig ohne Projektionen testbar.
**1b** hängt an 1a, ist aber ein eigener Mechanismus mit eigenen Tests.
**1c** hängt nur an der Event-Form und bringt die externen Abhängigkeiten mit
(Objektspeicher, Secrets).

### 12.2 Jedes Teilprojekt bekommt seinen Plan, wenn es anfängt

Eine frühere Fassung behauptete, nur Teilprojekt 1 brauche ein eigenes Spec,
weil danach „nichts Offenes mehr übrig" sei. **Das war falsch** und widersprach
Leitsatz 6: Teilprojekt 1 zu bauen wird Annahmen in diesem Dokument widerlegen.

Der Fehler war, *jetzt nicht planen* mit *braucht keinen Plan* zu verwechseln.

> **Die Fiktion wäre, die Teilprojekte 2–8 heute zu planen — nicht, sie zu
> planen.**

Das ist auch konsistent mit dem Aufnahmekriterium aus §1: ein Plan für den
IMAP-Konnektor hängt an nichts anderem, wird also später entschieden — aber er
wird entschieden.

### 12.3 Der Prüfpunkt nach Teilprojekt 1

Nach 1a, 1b und 1c, **vor** der Planung von 2–8. Mit Agenda, sonst wird er ein
Ritual:

1. **Hat das Kernmodell den Kontakt überlebt?** Sind von den zehn Entitäten
   welche falsch, zusammenzulegen oder zu ergänzen?
2. **Ist die Storage-Schnittstelle noch schmal**, oder ist SQL durchgesickert?
3. **Was hat die Projektionsmechanik wirklich gekostet** — Reprojektionsdauer
   über echte Datenmengen?
4. **Steht jeder Leitsatz noch**, oder wurde einer unter Druck gebogen?
5. **Was aus §11 war doch tragend?**

Die fünfte ist die wichtigste. §11 ist die Sammlung dessen, was dieses Dokument
für unkritisch erklärt hat — genau dort werden die Überraschungen liegen.

## 13. Offene Punkte

| Punkt | Art |
|---|---|
| Verifizieren, dass `pg_dict` in `pg_tokenizer` ein Hunspell-Wörterbuch einbinden kann | §12.2 im Entwurf, beim Bau |
| Versionsstände der Postgres-Erweiterungen | beim Bau |
| Fähigkeit von Claude Code bezüglich MRTR und der Tasks-Erweiterung | vor Teilprojekt 3 zu prüfen |
| Zeitpunkt für den Bau der Tilgung | §4.6 hält sie offen; wann sie gebaut wird, ist offen |
| Welche pgBackRest-Plugin-Implementierung | §10.5 — zur Bauzeit nachsehen |
| Trace-Verknüpfung MCP-Aufruf ↔ Gate-Einträge über OpenTelemetry | Komfort, Teilprojekt 4 |

Der dritte ist der einzige, der einen Umbau auslösen könnte: unterstützt der
Client MRTR nicht, müssen blockierende Rückfragen vorerst als gewöhnliche
Werkzeuge laufen — unschön, aber nicht strukturell.

**Zur Tilgung:** Entschieden ist, dass Tombstoning und Krypto-Schreddern
**gebaut werden sollen, aber nicht jetzt** — und dass heute nichts verbaut wird.
Die drei Vorkehrungen dafür stehen in §4.6 und sind Teil von Teilprojekt 1.
Offen ist nur der Zeitpunkt des Baus.

---

## 14. Quellen

- [MCP Änderungsbericht 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/changelog) · [Ankündigung](https://blog.modelcontextprotocol.io/posts/2026-07-28/)
- [MRTR-Muster](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)
- [Hetzner Object Storage — unterstützte Aktionen](https://docs.hetzner.com/storage/object-storage/supported-actions/) · [FAQ](https://docs.hetzner.com/storage/object-storage/faq/general/)
- [barman-cloud-Plugin: Feature-Anfrage SSE-C](https://github.com/cloudnative-pg/plugin-barman-cloud/issues/646)
- [Vergleich S3-kompatibler Anbieter](https://blog.n0p.me/2025/10/2025-10-25-s3-compatible-storage-comparsion/)
- [Pi Coding Agent](https://pi.dev/)
- [pgBackRest-Plugin für CloudNativePG (Dalibo)](https://blog.dalibo.com/2026/06/25/plugin-pgbackrest.html) · [Implementierung Opera Software](https://github.com/operasoftware/cnpg-plugin-pgbackrest)
- [Barman: clientseitige Verschlüsselung fehlt in den Cloud-Werkzeugen](https://github.com/EnterpriseDB/barman/issues/1155) · [pgBackRest-Repository-Verschlüsselung](https://www.percona.com/blog/enhancing-postgresql-security-how-to-encrypt-the-pgbackrest-repository/)
