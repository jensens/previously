# Architektur — Wissensspeicher für Kundenprojekte

Stand: 2026-10-01 · Status: zur Abnahme

Geschrieben für Jens als Reviewer und als Vorlage für die Zerlegung in
Teilprojekte. Setzt den Entwurf in `2026-10-01-wissensspeicher-design.md`
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
  id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  kind         text NOT NULL CHECK (kind IN ('observation','assertion','action')),
  recorded_at  timestamptz NOT NULL DEFAULT now(),
  occurred_at  timestamptz NOT NULL,
  hash         bytea NOT NULL,
  prev_hash    bytea,
  payload      jsonb NOT NULL
);

CREATE INDEX event_occurred_idx ON event (occurred_at);
CREATE INDEX event_kind_occurred_idx ON event (kind, occurred_at);
CREATE UNIQUE INDEX event_hash_idx ON event (hash);
```

- **`id` ist monoton und die Kettenreihenfolge.** `recorded_at` ist Anzeige,
  nicht Ordnung — zwei Einfügungen in derselben Mikrosekunde brauchen eine
  eindeutige Folge.
- **`occurred_at` ist indiziert**, weil jede Chronik darüber sortiert (§5.1).
- `payload` ist `jsonb`, validiert gegen JSON-Schema **in `core`**, nicht als
  Spaltenzwang. Grund: Leitsatz 9 — neue Arten von `assertion` dürfen ohne
  Migration dazukommen.

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

## 5. Die Storage-Schnittstelle

Schmal, damit sie hält (§12). Alles, was darüber hinausgeht, gehört in `core`.

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

1. **`append` ist die einzige Schreiboperation am Log** und serialisiert über
   die Hash-Kette: `prev_hash` muss der aktuell letzte Hash sein, sonst Konflikt
   und Wiederholung. Ein Schreiber pro Anfügung, mehrere Prozesse erlaubt.
2. **Projektionen sind pro Name einfädig.** Zwei Arbeiter an derselben
   Projektion sind ein Fehler, kein Durchsatzgewinn — der Vorschub `up_to_id`
   ist die Sperre.
3. **Reprojektion läuft neben dem Eingang**, in eine Schattentabelle, und wird
   am Ende umgeschaltet. Kein Stillstand.
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
| `get_dossier` | lesend | Zuschnitt `organization` \| `project` \| `matter`, optional Stichtag und Zeitordnung |
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

**Die Offenlegungsprüfung sitzt im `mcp_server`**, nicht im Kern: er ist der
zweite Durchsetzungspunkt aus §10.1 und entscheidet, was die interaktive Seite
überhaupt bekommt.

---

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

## 10. Was bewusst offen bleibt

Nach dem Aufnahmekriterium aus §1 gehört nichts davon hierher.

| offen | entschieden in |
|---|---|
| Textsuchvariante (Hunspell / Subword / BM25) | Messversuch §12.3 im Entwurf |
| Konkretes Embedding-Modell (mehrsprachig, lokal) und damit `N` | Teilprojekt 1 |
| Interne Abgleichlogik je Konnektor | je Konnektor |
| Prompt- und Templatetexte | Teilprojekt 5 |
| Rangfunktion der Triage-Hebelwirkung | Teilprojekt 5, messbar nachjustierbar |
| Deployment (Container, systemd, k3s) | Betriebsentscheidung, kein Modul hängt daran |
| Oberfläche jenseits MCP | verschoben (§14 im Entwurf) |

---

## 11. Zerlegung in Teilprojekte

Reihenfolge aus §14 im Entwurf, mit der Kaltstart-Vorgabe aus §8.1.

| # | Teilprojekt | Umfang | eigenes Detail-Spec? |
|---|---|---|---|
| 1 | **`core` und `storage`** | Log, Hash-Kette, Idempotenz, Units, Projektionsgerüst, Storage-Schnittstelle | **ja** — Hash-Kette und Reprojektion verdienen es |
| 2 | **`contract` und manueller Einwurf** | `contract`, Drop-Ordner, Einwurf per Prompt, Quelle verlinken | nein |
| 3 | **`mcp_server`** | Protokoll 2026-07-28, Werkzeuge, Handles, Offenlegungsprüfung | nein |
| 4 | **`gate`** | Policy, Adapter, Audit, `processing_region` | nein |
| 5 | **`ai_layer` und Triage** | Zeitliche und inhaltliche Signale, Zerlegung, Triage | nein |
| 6 | **IMAP** | Konnektor nach Vertrag | nein |
| 7 | **Identitätsgraph und Beteiligtenregel** | strukturelle Signale, rückwirkend auf die Historie | nein |
| 8 | **Bestandsimport** | Pilotprojekt, Batch-Läufe | nein |

**Teilprojekt 1 ist der einzige echte Flaschenhals** — alles andere hängt daran.
Teilprojekte 3, 4 und 6 sind danach voneinander unabhängig.

Nur Teilprojekt 1 bekommt ein eigenes Detail-Spec. Bei allem anderen ist nach
diesem Dokument nichts Offenes mehr, das eine Spezifikation bräuchte, sondern
nur noch Arbeit — und ein Spec dafür wäre die Fiktion aus §1.

---

## 12. Offene Punkte

| Punkt | Art |
|---|---|
| Verifizieren, dass `pg_dict` in `pg_tokenizer` ein Hunspell-Wörterbuch einbinden kann | §12.2 im Entwurf, beim Bau |
| Versionsstände der Postgres-Erweiterungen | beim Bau |
| Fähigkeit von Claude Code bezüglich MRTR und der Tasks-Erweiterung | vor Teilprojekt 3 zu prüfen |
| Trace-Verknüpfung MCP-Aufruf ↔ Gate-Einträge über OpenTelemetry | Komfort, Teilprojekt 4 |

Der dritte ist der einzige, der einen Umbau auslösen könnte: unterstützt der
Client MRTR nicht, müssen blockierende Rückfragen vorerst als gewöhnliche
Werkzeuge laufen — unschön, aber nicht strukturell.

---

## 13. Quellen

- [MCP Änderungsbericht 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/changelog) · [Ankündigung](https://blog.modelcontextprotocol.io/posts/2026-07-28/)
- [MRTR-Muster](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)
