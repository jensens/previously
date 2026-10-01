# Architektur — Wissensspeicher für Kundenprojekte

Stand: 2026-10-01 · Status: zur Abnahme

Geschrieben für Jens als Reviewer und als Vorlage für die Zerlegung in
Teilprojekte. Setzt den Entwurf in `2026-10-01-wissensspeicher-design.md`
voraus; Paragraphenverweise ohne Dokumentangabe beziehen sich darauf.

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
   ki_layer ──► gate ─┼──► kern ──► speicher
       │             │        │
       └─────────────┘        ▼
   konnektoren ──────────► vertrag  (reine Typen, kennt nichts)
       │                      ▲
       └─────────────────────┘
```

| Modul | Zuständigkeit | kennt |
|---|---|---|
| **`speicher`** | Append-only Log, Projektionstabellen, Suchindex. Nichts über Domäne. | — |
| **`kern`** | Event-Arten, Entitäten, Projektionen, Hash-Kette, Idempotenz | `speicher`, `vertrag` |
| **`vertrag`** | Der Konnektor-Vertrag als Typen und Protokoll. Keine Logik. | **—** |
| **`konnektoren`** | Je Quelle/Ziel eine Implementierung des Vertrags | `vertrag`, `kern` |
| **`gate`** | Modellaufrufe, Policy, Anbieterwahl, Audit der Aufrufe | `kern` (nur Typen) |
| **`ki_layer`** | Zuordnung, Zerlegung, Extraktion, Templates, Vorschläge | `gate`, `kern` |
| **`mcp_server`** | Protokoll, Werkzeuge, Handles, Offenlegungsprüfung | `kern`, `ki_layer` |

**Drei Regeln, die diese Grenzen verteidigen und testbar sind:**

1. **`kern` kennt kein Fremdsystem und kein Modell.** Kein Import aus
   `konnektoren`, `gate`, `ki_layer`, `mcp_server`. Statisch prüfbar.
   (`vertrag` ist erlaubt: reine Typen, kennt selbst nichts — sonst entstünde ein
   Zyklus, weil der Kern `RohEreignis` entgegennehmen muss.)
2. **Nur `gate` ruft Modelle.** Kein Anbieter-SDK außerhalb. Statisch prüfbar
   (Abnahmebedingung 7 im Entwurf).
3. **Nur `speicher` kennt SQL.** `kern` spricht Methoden, nicht Abfragen.

**Warum `vertrag` ein eigenes Modul ist:** Der manuelle Einwurf ist laut §11.4
die Referenzimplementierung des Konnektor-Vertrags. Liegt der Vertrag in
`konnektoren`, kennt ihn der Kern nicht und jeder Konnektor erfindet ihn neu.
Als eigenes Modul ist er zitierbar und veränderungsfest.

---

## 3. Schema

PostgreSQL. Namen deutsch, weil das Domänenmodell deutsch ist; SQL-Schlüsselwörter
nicht.

### 3.1 Der Log

Eine Tabelle für alle drei Event-Arten. Keine Vererbungshierarchie: die Arten
unterscheiden sich in Nutzlast, nicht in Lebenszyklus, und eine Tabelle hält die
Hash-Kette trivial.

```sql
CREATE TABLE ereignis (
  id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  art           text NOT NULL CHECK (art IN ('wahrnehmung','feststellung','handlung')),
  erfasst_am    timestamptz NOT NULL DEFAULT now(),
  ereignis_zeit timestamptz NOT NULL,
  hash          bytea NOT NULL,
  vorgaenger    bytea,
  nutzlast      jsonb NOT NULL
);
```

- **`id` ist monoton und die Kettenreihenfolge.** `erfasst_am` ist Anzeige, nicht
  Ordnung — zwei Einfügungen in derselben Mikrosekunde brauchen eine eindeutige
  Folge.
- **`ereignis_zeit` ist indiziert**, weil jede Chronik darüber sortiert (§5.1).
- Die Nutzlast ist `jsonb`, validiert gegen JSON-Schema **in `kern`**, nicht als
  Spaltenzwang. Grund: Leitsatz 9 — neue Feststellungs-Arten dürfen ohne
  Migration dazukommen.

```sql
CREATE INDEX ON ereignis (ereignis_zeit);
CREATE INDEX ON ereignis (art, ereignis_zeit);
CREATE UNIQUE INDEX ON ereignis (hash);
```

### 3.2 Idempotenz

```sql
CREATE TABLE quellenschluessel (
  quelle       text NOT NULL,
  fremd_id     text NOT NULL,
  ereignis_id  bigint NOT NULL REFERENCES ereignis(id),
  PRIMARY KEY (quelle, fremd_id)
);
```

Jede Wahrnehmung trägt `quelle` + quellennative ID (§5.1). Ein zweiter Import
stößt auf den Primärschlüssel und wird verworfen, nicht verdoppelt. **Das ist
auch die Transportanforderung aus MCP 2026-07-28** (§7.3): ein abgebrochener
Aufruf wird mit neuer Request-ID wiederholt, und nur diese Tabelle verhindert
das Duplikat.

### 3.3 Einheiten

```sql
CREATE TABLE einheit (
  ereignis_id bigint NOT NULL REFERENCES ereignis(id),
  nr          int NOT NULL,
  inhalt      text NOT NULL,
  von_ms      int,              -- Transkript: Zeitbereich
  bis_ms      int,
  sprecher    text,
  PRIMARY KEY (ereignis_id, nr)
);
```

`sprache` steht **nicht** hier: sie ist eine Feststellung (§5.1), kein Merkmal
der Wahrnehmung.

### 3.4 Projektionen

Alle Projektionstabellen sind **ableitbar und wegwerfbar**. Sie tragen daher
keine eigene Wahrheit und keine Fremdschlüssel auf einander — nur auf `ereignis`.

```sql
CREATE TABLE projektionsstand (
  name        text PRIMARY KEY,
  bis_id      bigint NOT NULL,
  version     int NOT NULL,
  gebaut_am   timestamptz NOT NULL
);
```

**`version`** ist der Wiederaufbau-Auslöser: ändert sich die Projektionslogik,
erhöht man die Version, und der Arbeiter baut neu. Keine Migration, kein
Handgriff.

Je Projektion eine Tabelle, alle nach demselben Muster — Beispiel:

```sql
CREATE TABLE p_verpflichtung (
  id              text PRIMARY KEY,          -- fachliche Kennung
  projekt         text,
  vorgang         text,
  schuldner       text,                      -- Akteur-Kennung, darf NULL sein
  glaeubiger      text,
  art             text NOT NULL,
  frist           date,
  zustand         text NOT NULL,
  aufgeteilt_in   text[],                    -- Dach (§6.2)
  belegt_durch    bigint[] NOT NULL,         -- Feststellungs-IDs
  letzte_id       bigint NOT NULL REFERENCES ereignis(id)
);
```

`belegt_durch` ist **nicht optional** — das ist die Quellenpflicht in
Tabellenform.

### 3.5 Suche

Zwei Spalten an der Einheit, beide Projektion:

```sql
CREATE TABLE p_einheit_suche (
  ereignis_id bigint NOT NULL,
  nr          int NOT NULL,
  projekt     text,                 -- B-Tree: Vorfilter vor der Vektorsuche
  ereignis_zeit timestamptz NOT NULL,
  sprache     text,
  volltext    tsvector,
  einbettung  vector(N),          -- N kommt mit der Modellwahl (§9)
  PRIMARY KEY (ereignis_id, nr)
);
CREATE INDEX ON p_einheit_suche (projekt, ereignis_zeit);
```

Die B-Tree-Spalte `projekt` ist der Grund, warum §12.2 im günstigen Fall landet:
bei stark selektiven Filtern filtert Postgres **vor** der Vektorsuche.

**Welche Textvariante gewinnt, ist offen** (§12.3). Die Grenze ist deshalb so
gezogen, dass `volltext` ersetzt werden kann, ohne `kern` anzufassen: die
Suchschnittstelle nimmt eine Anfrage und gibt Einheitenverweise zurück, nicht
`tsquery`.

---

## 4. Die Speicher-Schnittstelle

Schmal, damit sie hält (§12). Alles, was darüber hinausgeht, gehört in `kern`.

```python
class Speicher(Protocol):
    def anfuegen(self, ereignisse: Sequence[NeuesEreignis]) -> list[int]: ...
    def lesen(self, ab_id: int, limit: int) -> Iterator[Ereignis]: ...
    def strom(self, *, projekt: str | None, ab_id: int) -> Iterator[Ereignis]: ...
    def letzter_hash(self) -> bytes | None: ...
    def nachschlagen(self, quelle: str, fremd_id: str) -> int | None: ...

    def projektion_schreiben(self, name: str, zeilen: Sequence[Mapping]) -> None: ...
    def projektion_leeren(self, name: str) -> None: ...
    def projektionsstand(self, name: str) -> Stand | None: ...

    def suchen(self, anfrage: Suchanfrage) -> list[Treffer]: ...
```

Fünf Eigenschaften, die diese Schnittstelle **nicht** hat und bewusst nicht
haben darf: kein Update, kein Delete, keine Transaktionssteuerung nach außen,
kein SQL-Durchlass, keine Rückgabe von Datenbankobjekten.

`strom` gibt einen **Iterator**, nicht eine Liste (Abnahmekriterium aus §12.2) —
Reprojektion über Jahre Historie darf nichts in den Speicher ziehen.

---

## 5. Der Konnektor-Vertrag

Das Stück, das im Entwurf dreimal behauptet und nie geschrieben wurde.

### 5.1 Zwei Richtungen, getrennt deklariert

```python
class Konnektor(Protocol):
    kennung: str                      # 'imap', 'drop', 'prompt', 'link', 'gitlab', …
    faehigkeit: Faehigkeit            # BEIDSEITIG | NUR_LESEND | KEINE_API

    def aufnehmen(self, seit: Wasserzeichen) -> Iterator[RohEreignis]: ...

class Renderer(Protocol):             # nur bei BEIDSEITIG
    def zielorte(self) -> list[Zielort]: ...
    def rendern(self, ziel: Zielort, projektion: Mapping) -> Renderergebnis: ...
```

Ein Konnektor ohne Renderer ist zulässig; ein Renderer ohne Konnektor nicht —
sonst kann die Echo-Unterdrückung (§5.5) nicht vergleichen.

### 5.2 Was ein `RohEreignis` tragen muss

```python
@dataclass(frozen=True)
class RohEreignis:
    quelle: str
    fremd_id: str                     # Idempotenz
    ereignis_zeit: datetime
    belegart: Belegart                # WORTLAUT | ERINNERUNG
    kanalidentitaeten: list[KanalIdentitaet]
    einheiten: list[RohEinheit]       # nummeriert, mechanisch zerlegt
    roh: bytes | None                 # Leitsatz 6: im Zweifel mehr aufnehmen
```

**Keine Zuordnung, keine Klassifikation, keine Sprache.** Ein Konnektor
*interpretiert* nicht — er nimmt auf. Das ist die Grenze, an der Leitsatz 4
hängt, und sie ist im Typ erzwungen, nicht in der Prosa.

### 5.3 Wasserzeichen und Wiederaufnahme

```python
@dataclass(frozen=True)
class Wasserzeichen:
    konnektor: str
    stand: Mapping[str, str]          # konnektorspezifisch, opak für den Kern
    gesetzt_am: datetime
```

Der Kern behandelt `stand` als opak — IMAP legt `UIDVALIDITY`/`UIDNEXT` ab,
GitLab eine Cursor-Kennung. **Fortgeschrieben wird es erst, nachdem die
Ereignisse angefügt sind**, nie vorher. Bricht ein Abgleich ab, läuft er von der
letzten bestätigten Stelle neu und läuft dabei idempotent ins Leere (§3.2).

### 5.4 Rendern und Echo

```python
@dataclass(frozen=True)
class Renderergebnis:
    fremd_referenz: str               # 'gitlab:issue/42'
    gerenderter_zustand: Mapping      # exakt das Geschriebene
```

`gerenderter_zustand` wird an der Handlung gespeichert und ist der Vergleichswert
für §5.5: **vergleichen, nicht annehmen.** Gleichheit heißt Echo und wird
verworfen; Unterschied heißt Wahrnehmung.

### 5.5 Zielort

```python
@dataclass(frozen=True)
class Zielort:
    kennung: str                      # 'gitlab:gruppe/kunde-b'
    deckung: list[str]                # Vereinbarungs-Kennungen (§7.2 Entwurf)
    publikumszustand: Publikumszustand
```

`deckung` ist **erklärt, nicht entdeckt** — das Gate der Offenlegungsprüfung
braucht keinen Adapter (§7.2 im Entwurf). `publikumszustand` ist die Prüfung
darüber und darf `UNBEKANNT` sein, was Rendern blockiert.

---

## 6. Prozessmodell

### 6.1 Was läuft als was

| Prozess | Art | Aufgabe |
|---|---|---|
| `mcp` | langlebig | MCP-Server, zustandslos (§7) |
| `aufnahme` | periodisch je Konnektor | `aufnehmen()` → Log |
| `projektion` | ereignisgetrieben | Log → Projektionstabellen |
| `anreicherung` | gestapelt | Zuordnung, Zerlegung, Extraktion über das Gate |
| `rendern` | ereignisgetrieben | Projektion → Zielorte, nach Freigabe |
| `wartung` | täglich | Kettenprüfung, Publikum neu aufzählen, Schwingungswächter |

**Eine Warteschlange in Postgres, kein Broker.** Bei diesem Volumen (§12.1) ist
ein zusätzliches System reiner Betriebsaufwand. `SELECT … FOR UPDATE SKIP LOCKED`
reicht für mehrere Arbeiter.

```sql
CREATE TABLE auftrag (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  art         text NOT NULL,
  schluessel  text NOT NULL,          -- fachliche Entprellung
  nutzlast    jsonb NOT NULL,
  zustand     text NOT NULL DEFAULT 'offen',
  versuche    int NOT NULL DEFAULT 0,
  nicht_vor   timestamptz NOT NULL DEFAULT now(),
  letzter_fehler text
);

-- Entprellung: partieller Unique-Index, nicht als Tabellenbedingung möglich
CREATE UNIQUE INDEX auftrag_offen_eindeutig
  ON auftrag (art, schluessel)
  WHERE zustand IN ('offen', 'laeuft');
```

Der partielle Unique-Index auf offenen Aufträgen ist die Entprellung: hundert
neue Mails eines Projekts erzeugen **einen** Anreicherungsauftrag, nicht hundert.

### 6.2 Die Batch-API passt ins Auftragsmodell

Die Anreicherung ist nicht zeitkritisch und läuft über die Batch-API (§10.2 im
Entwurf, 50 % Rabatt). Das ist ein dreiphasiger Auftrag:

```
sammeln ──► eingereicht ──► abgeholt
   │            │  (Anbieter-ID in nutzlast)
   │            └──► bei Fehler: zurück auf 'sammeln', einzeln erneut
   └──► Schwelle: Menge oder Alter
```

**Der Auftrag hält die Anbieter-Kennung**, nicht der Prozess. Ein Neustart
mitten im Lauf verliert nichts.

### 6.3 Nebenläufigkeit

Vier Regeln, und sie reichen:

1. **Anfügen ist die einzige Schreiboperation am Log** und serialisiert über die
   Hash-Kette: `vorgaenger` muss der aktuell letzte Hash sein, sonst Konflikt und
   Wiederholung. Ein Schreiber pro Anfügung, mehrere Prozesse erlaubt.
2. **Projektionen sind pro Name einfädig.** Zwei Arbeiter an derselben Projektion
   sind ein Fehler, kein Durchsatzgewinn — der Vorschub `bis_id` ist die Sperre.
3. **Reprojektion läuft neben dem Eingang**, in eine Schattentabelle, und wird
   am Ende umgeschaltet. Kein Stillstand.
4. **Lesen sieht nie halbe Projektionen**, weil die Umschaltung in einer
   Transaktion passiert.

### 6.4 Fehlerverhalten

| Fehler | Verhalten |
|---|---|
| Konnektor nicht erreichbar | Auftrag `nicht_vor` verschieben, exponentiell, Wasserzeichen unverändert |
| Modellaufruf scheitert | Gate wiederholt begrenzt; danach Auftrag auf `fehler`, Eintrag in die Queue |
| Rendern scheitert | **Handlung wird trotzdem geschrieben**, mit `ergebnis.fehler`. Sonst fehlt die Spur |
| Kettenprüfung schlägt an | Alles Schreiben anhalten, Alarm. Kein Selbstheilungsversuch |
| Zielort `UNBEKANNT` | Rendern blockiert, Queue-Eintrag |

Der dritte Punkt ist der, den man leicht falsch macht: ein gescheiterter Versuch
ist ein Ereignis. Nur erfolgreiche Handlungen zu protokollieren erzeugt ein Log,
das besser aussieht als die Wirklichkeit.

---

## 7. MCP-Schnittstelle

Zugrunde liegt **Revision 2026-07-28** (GA). Drei ihrer Eigenschaften prägen den
Entwurf, zwei widerlegen Ideen, die sonst naheliegend gewesen wären.

### 7.1 Zustandslos, Zustand über Handles

Kein `initialize`, keine Sessions, keine `Mcp-Session-Id`. Protokollversion und
Client-Fähigkeiten stehen je Aufruf in `_meta`; `server/discover` ist Pflicht.

Zustand über Aufrufe hinweg läuft über **servergeprägte Handles als gewöhnliche
Werkzeugparameter**. Bei uns ist das angenehm: **ein Handle ist eine Event-ID
oder eine Auftrags-Kennung** — es gibt nichts zu erfinden und nichts zu
verwalten.

### 7.2 Sampling ist abgekündigt — eine Idee weniger

Die naheliegende Versuchung wäre, den Server über `sampling/createMessage` das
Modell des Clients arbeiten zu lassen, also Pipeline-Arbeit über den Max-Plan.
**Das ist abgekündigt** (empfohlene Migration: direkt gegen die Anbieter-API),
und es soll nicht gebaut werden.

Damit bleibt die Arbeitsteilung aus §10.2 unverändert und ohne Hintertür: der
Max-Plan deckt die interaktive Arbeit, das Gate ruft für die Pipeline selbst.

Ebenfalls abgekündigt: **Roots** (Pfade über Parameter oder Konfiguration — der
Drop-Ordner wird konfiguriert, nicht erfragt) und **Logging** (stderr oder
OpenTelemetry).

### 7.3 Keine Stromwiederaufnahme — Idempotenz ist Pflicht

Bricht die Antwort ab, ist der Aufruf verloren und wird mit **neuer** Request-ID
wiederholt. Alle Schreibwerkzeuge müssen daher idempotent sein.

`einwerfen` nimmt deshalb eine **vom Client vergebene Kennung** als `fremd_id`
(§3.2). Zweiter Aufruf, gleiche Kennung: dieselbe Event-ID zurück, kein
Duplikat.

### 7.4 Rückfragen: MRTR für blockierende, Werkzeuge für gestapelte

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

### 7.5 Lange Läufe: die Tasks-Erweiterung

`io.modelcontextprotocol/tasks`, Abfrage über `tasks/get`, und Server dürfen
Task-Handles **unaufgefordert** zurückgeben. Genau passend für Bestandsimport
und Batch-Läufe: `import_starten` gibt sofort ein Handle zurück, der Fortschritt
wird abgefragt.

### 7.6 Schemata: die Quellenpflicht wird erzwingbar

`inputSchema`/`outputSchema` erlauben jetzt beliebige JSON-Schema-2020-12-Schlüsselwörter
samt `$ref`. Damit ist die Quellenpflicht aus §5.2 **schemaseitig** durchsetzbar
statt erhofft: ein gemeinsames `$defs.quellen` mit `minItems: 1`, referenziert
von jeder Feststellungs-Art.

Ebenfalls Pflicht: `ttlMs` und `cacheScope` auf allen Listenergebnissen, und
`tools/list` **deterministisch sortiert** — letzteres ist kein Komfort, sondern
zahlt direkt auf die Prompt-Cache-Trefferquote und damit auf die Kosten ein.

### 7.7 Werkzeuge

Zustandslos, idempotent wo schreibend, strukturierte Ausgabe mit Schema.

| Werkzeug | Art | Anmerkung |
|---|---|---|
| `protokoll` | lesend | Zuschnitt Organisation \| Projekt \| Vorgang, optional Stichtag und Zeitordnung |
| `offene_verpflichtungen` | lesend | Filter: Projekt, eigene/fremde/beobachtet |
| `entscheidungen` | lesend | |
| `suche` | lesend | der Rückfallpfad aus §18 im Entwurf |
| `ereignis` / `einheiten` | lesend | Zitaten folgen |
| `einwerfen` | schreibend | Client-Kennung als `fremd_id`, idempotent |
| `feststellen` | schreibend | Korrektur, `verantwortung: {jens, direkt}` |
| `triage_liste` | lesend | nach Hebelwirkung sortiert |
| `triage_antworten` | schreibend | |
| `freigabe_liste` | lesend | getrennt von der Triage (§10.3 im Entwurf) |
| `abnehmen` / `ablehnen` | schreibend | Ablehnung wird festgehalten (§10.4) |
| `import_starten` | schreibend | gibt Task-Handle zurück |

**Die Offenlegungsprüfung sitzt im `mcp_server`**, nicht im Kern: er ist der
zweite Durchsetzungspunkt aus §10.1 und entscheidet, was die interaktive Seite
überhaupt bekommt.

---

## 8. Die Gate-Schnittstelle

```python
class Gate(Protocol):
    def rufen(self, aufgabe: Aufgabe, nutzlast: Nutzlast,
              kontext: Kontext) -> Ergebnis: ...

@dataclass(frozen=True)
class Kontext:
    projekt: str | None
    vertraulichkeit: Vertraulichkeit
    verarbeitungsraum_erlaubt: list[str]      # aufgelöst nach §7.1 im Entwurf
```

Zwei Dinge, die das Gate **immer** tut und die nicht abschaltbar sind:

1. **Anbieter- und Modellwahl aus der Politik**, nicht aus dem Aufrufparameter.
   Der Aufrufer sagt *was*, nicht *womit*.
2. **Protokollieren**: Zeitpunkt, Aufgabe, Datenreferenzen (keine Kopien),
   Modell, Prompt-Version, **gesetzter und gemeldeter Verarbeitungsraum**,
   Ergebnis, Kosten. Abweichung zwischen gesetzt und gemeldet ist ein Alarm.

Zwei Adapter: Anthropic-SDK und OpenAI-kompatibel. Letzteres deckt OpenRouter,
Ollama und llama.cpp.

**Alle Modellausgaben sind strukturiert**, nie freier Text — das ist Leitsatz 1
in der Schnittstelle: `rufen` nimmt ein Ausgabeschema und validiert dagegen,
bevor es zurückgibt.

---

## 9. Was bewusst offen bleibt

Nach dem Aufnahmekriterium aus §1 gehört nichts davon hierher.

| offen | entschieden in |
|---|---|
| Textsuchvariante (Hunspell / Subword / BM25) | Messversuch §12.3 im Entwurf |
| Konkretes Embedding-Modell (mehrsprachig, lokal) | Teilprojekt Kern |
| Interne Abgleichlogik je Konnektor | je Konnektor |
| Prompt- und Templatetexte | Teilprojekt KI-Layer |
| Rangfunktion der Triage-Hebelwirkung | Teilprojekt KI-Layer, messbar nachjustierbar |
| Deployment (Container, systemd, k3s) | Betriebsentscheidung, kein Modul hängt daran |
| Oberfläche jenseits MCP | verschoben (§14 im Entwurf) |

---

## 10. Zerlegung in Teilprojekte

Reihenfolge aus §14 im Entwurf, mit der Kaltstart-Vorgabe aus §8.1.

| # | Teilprojekt | Umfang | eigenes Detail-Spec? |
|---|---|---|---|
| 1 | **Kern und Speicher** | Log, Hash-Kette, Idempotenz, Einheiten, Projektionsgerüst, Speicher-Schnittstelle | **ja** — Hash-Kette und Reprojektion verdienen es |
| 2 | **Vertrag und manueller Einwurf** | `vertrag`, Drop-Ordner, Einwurf per Prompt, Quelle verlinken | nein |
| 3 | **MCP-Server** | Protokoll 2026-07-28, Werkzeuge, Handles, Offenlegungsprüfung | nein |
| 4 | **Gate** | Policy, Adapter, Audit, Verarbeitungsraum | nein |
| 5 | **KI-Layer und Triage** | Zeitliche und inhaltliche Signale, Zerlegung, Triage | nein |
| 6 | **IMAP** | Konnektor nach Vertrag | nein |
| 7 | **Identitätsgraph und Beteiligtenregel** | strukturelle Signale, rückwirkend auf die Historie | nein |
| 8 | **Bestandsimport** | Pilotprojekt, Batch-Läufe | nein |

**Teilprojekt 1 ist der einzige echte Flaschenhals** — alles andere hängt daran.
Teilprojekte 3, 4 und 6 sind danach voneinander unabhängig.

Nur Teilprojekt 1 bekommt ein eigenes Detail-Spec. Bei allem anderen ist nach
diesem Dokument nichts Offenes mehr, das eine Spezifikation bräuchte, sondern nur
noch Arbeit — und ein Spec dafür wäre die Fiktion aus §1.

---

## 11. Offene Punkte

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

## 12. Quellen

- [MCP Änderungsbericht 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/changelog) · [Ankündigung](https://blog.modelcontextprotocol.io/posts/2026-07-28/)
- [MRTR-Muster](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)
