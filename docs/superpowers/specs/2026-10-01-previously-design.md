# Previously — Entwurf

Stand: 2026-10-01 · Status: zur Abnahme

Geschrieben für Jens als Reviewer und als Grundlage für den
Implementierungsplan.

## Zum Namen

**Previously.** Weil die Hauptansicht des Systems wörtlich das ist: *previously,
on Projekt Auftraggeber A…* — der Protokollkopf plus Chronik aus §9.1. Der Name
benennt die Funktion, nicht eine Figur, die sie bedient, und er braucht keine
Erklärung.

Geprüft und verworfen: **`Memex`** (DARPA-Programm für Strafverfolgung
dominiert die Suche, dazu ein lebendes Open-Source-Werkzeug mit demselben
Pitch), **`Moneypenny`** (ein deutscher Sekretariatsdienst führt den Namen —
gleiche Funktion, gleicher Markt; das Bond-IP war laut OLG Hamburg nicht das
Problem), **`Seshat`**, **`Nisaba`**, **`Thoth`**, **`Nabu`** (Schreiber- und
Gedächtnisgottheiten sind systematisch vergeben, oft mehrfach, teils im
MCP-Umfeld), **`Herodot`** (sauber und gemeinfrei, aber international landet man
bei `Herodotus` in einer Blockchain-Organisation).

Ausgeschlossen als Familie: alles mit Überwachungsgeruch — `Argus`, `Heimdall`,
`Panoptes`, `Palantir`. Sie passen sachlich und verkaufen genau das Gegenteil
dessen, was das System ist. Ebenso alles mit `AI`, `Mind` oder `Brain`: die KI
ist hier austauschbares Beiwerk, der Kern ist ein Event-Log mit Projektionen.

**Sprachregelung: Prosa deutsch, alles Technische englisch.** Bezeichner,
Feldnamen, Werkzeugnamen und Aufzählungswerte sind englisch; das Glossar steht
in §3 des Architektur-Specs und ist die einzige erlaubte Zuordnung. Das Gesprächsprotokoll mit allen Zwischenschritten und
verworfenen Varianten liegt in `../../../NOTIZEN.md`.

---

## 1. Zweck

Nicht mehr in N Inboxen nachsehen müssen, um zu wissen, wo ein Kundenprojekt
steht.

Alles, was zu einem Projekt hereinkommt — Mail, Chat, Besprechung, Dokument,
Issue — fließt in einen Speicher, wird Organisation, Projekt und Vorgang
zugeordnet,
und ist von dort als Verlauf, offene Verpflichtung und getroffene Entscheidung
jederzeit abrufbar. Von derselben Stelle aus wird gehandelt: Antwort
entwerfen, Aufgabe anlegen, Protokoll bereitstellen.

**Erfolgsmaß:** Die Frage "Wie steht Projekt X?" ist in unter einer Minute
vollständig beantwortet, ohne in ein Postfach zu schauen — und jede Antwort
ist auf ihre Quelle zurückführbar.

---

## 2. Feste Entscheidungen

| # | Gegenstand | Entscheidung |
|---|---|---|
| 1 | Nutzerkreis | Ein Benutzer (Jens). Team-Fähigkeit bleibt architektonisch möglich. Kein Kundenzugang. FOSS-Release als offene Option, kein Ziel. |
| 2 | Datenabfluss | Cloud-API erlaubt (ZDR + DPA). Nichts verbauen, falls später gestuft oder vollständig lokal nötig wird. |
| 3 | Motoren | Vier, alle hinter *einem* Gate: Max-Plan (interaktiv), Anthropic-API direkt (Masse, ZDR), OpenRouter (Experimente, unkritische Masse), lokal (Whisper, Embeddings). |
| 4 | Audit | Freigabepflicht **und** Nachvollziehbarkeit **und** revisionssicheres Protokoll. Dauerfreigaben pro Aktionsklasse möglich. |
| 5 | Wahrheit | Der Kern. Fremdsysteme sind Inbox *und* Artefakt, nie Wahrheitsquelle. |
| 6 | Sprache | Python, strikt typisiert. PyO3 als benannter Notausgang. Maximal zwei Sprachen. |
| 7 | Datenbank | **PostgreSQL mit pgvector**, hinter schmalem Speicher-Adapter. Recherche und Begründung in §12. Suchindex bleibt austauschbar, weil er eine Projektion ist. |
| 8 | MVP | Teile 1, 3, 4 plus MCP-Server. Voice und eigene Oberfläche verschoben. |

---

## 3. Leitsätze

Diese Sätze entscheiden im Zweifelsfall. Wenn eine Implementierung mit
einem von ihnen bricht, ist die Implementierung falsch.

**1. Autonomie entsteht durch Einschränkung, nicht durch Vertrauen.**
Eine Aktion darf nur automatisch laufen, wenn sie an ein Template gebunden
ist — das Modell füllt Felder, es formuliert nicht frei. Freier Prosa-Output
bleibt dauerhaft freigabepflichtig, unabhängig davon, wie gut er wird.

**2. Das Kernmodell enthält nichts Werkzeugförmiges.**
Test für jedes Feld: Würde es noch Sinn ergeben, wenn OpenProject nicht
existierte? Wenn nein, gehört es in einen Adapter. Werkzeugnamen tauchen an
genau einer Stelle auf: der PM-Verknüpfung an der Aufgabe.

**3. Append-only. Jeder Zustand ist eine Projektion.**
Nichts wird überschrieben, nichts gelöscht. Wird eine Projektion zur primären
Daten­haltung, ist das System kaputt — unabhängig von der Datenbank darunter.

**4. Wahrnehmungen können nicht falsch sein, Feststellungen können es.**
Was hereinkam, ist Tatsache. Was daraus geschlossen wird, ist widerlegbar.
Fehlbares gehört nie ins Unfehlbare.

**5. Die Unordnung bleibt in der Quelle, die Ordnung entsteht in der
Feststellung.**
Zuordnungen dürfen so chaotisch sein wie die Wirklichkeit — verstreut,
überlappend, lückenhaft. Verpflichtung, Frist und Entscheidung sind trotzdem
scharf.

**6. Im Zweifel mehr aufnehmen, weniger interpretieren.**
Volle Rohinhalte, alle Kopfzeilen, alle Beteiligten — auch Felder, die heute
niemand liest. Die Aufnahme ist der einzige unwiederbringliche Schritt.

**7. Rollen sind immer Beziehungen, nie Eigenschaften.**
Prüffrage für jedes Feld: *Könnte das im nächsten Projekt anders sein?* Wenn
ja, ist es eine Beziehung mit Zeitraum. Dieser Entwurf hat den Fehler zweimal
gemacht — erst "Rolle" an der Person, dann "Kunde" als Entitätsart — und beide
Male war die Antwort offensichtlich ja, sobald jemand hingesehen hat.

**8. Bei mehreren Beteiligten gewinnt die strengste Festlegung.**
Datenpolitik, Aufnahme-Einwilligung, Freigabeklassen, **Rechtsraum**: ein
Projekt hat mehrere beteiligte Organisationen, und es gilt die restriktivste. Nicht die des
Auftraggebers, nicht die zuerst eingetragene — die strengste.

Das gilt für **Politiken**. Bei **Befugnissen** (§7.2) ist die Logik eine andere:
dort geht es um die *Existenz* einer deckenden Vereinbarung, nicht um ein
Minimum. Wer das verwechselt, baut entweder zu viel oder zu wenig.

**9. Unentschiedenheit muss darstellbar sein, nicht erzwungen entschieden.**
Wo das System es nicht wissen kann, gibt es einen Zustand für "noch offen" —
keinen Vorgabewert, der eine Vermutung als Tatsache ausgibt. Dieser Grundsatz
wirkt schon an sechs Stellen: `assignment.confidence`, `debtor: null`,
erlaubte Lücken bei der Zerlegung, "der Import darf unsicher sein" (§13),
`author: unknown` und das Dach beim Teilen (§6.3, §6.2). Wer hier
"aufräumt" und Vorgabewerte einsetzt, macht das System still kaputt.

### Warum das zusammen die Revisionsfähigkeit trägt

Dieser Entwurf wird sich ändern. Entscheidend ist, dass die beiden Arten von
Änderung unterschiedlich teuer sind, und dass das kein Zufall ist:

**Billig ist alles, was Interpretation ist.** Eine neue Feststellungs-Art
dazunehmen, neu projizieren — fertig. Keine Migration, keine Schemaänderung an
Bestandsdaten. Fällt in sechs Monaten auf, dass "Risiko" eine eigene Entität
sein müsste, ist das ein Nachmittag plus ein Durchlauf über die Historie.

**Teuer ist genau zweierlei:** was nicht aufgenommen wurde (Leitsatz 6), und
ein gebrochener Leitsatz. Alles andere ist nachholbar.

Wer eine Abkürzung erwägt, prüft deshalb zuerst, ob sie einen dieser beiden
Punkte berührt. Wenn nicht, ist sie harmlos. Wenn ja, ist sie keine Abkürzung.

---

## 4. Architektur

```
  KONNEKTOREN                   KERN                      ZUGANG
  (bidirektional)

  IMAP        ──────────►  ┌────────────────────────┐
  Drop        ──────────►  │  Event-Log             │ ◄──►  MCP-Server
  Prompt      ──────────►  │  (append-only)         │           │
  Link        ──────────►  │                        │           ├─► Claude Code
  OpenProject ◄─────────►  │  Projektionen          │           │   (Max-Plan)
  GitLab      ◄─────────►  │  Entitäten             │           │
  Nextcloud   ◄─────────►  │  Organisationsprofil   │           └─► später: own
                           └───────────┬────────────┘               UI, Spracheingabe
                                       │
                                       ▼
                           ┌────────────────────────┐
                           │  KI-LAYER              │   unbeaufsichtigt:
                           │  Gate · Policy · Audit │   Wahrnehmung
                           │  Zuordnung · Zerlegung │   → Feststellung
                           │  Templates             │
                           └────────────────────────┘
```

**Der KI-Layer liegt neben dem Kern, nicht zwischen Kern und Zugang.**
Interaktive Arbeit geht über den MCP-Server **direkt** auf den Kern: "Was ist
bei Kunde X offen?" ist eine Abfrage über Projektionen und braucht kein
Modell — der Mensch (bzw. Claude Code) *ist* in dem Moment die Intelligenz.
Ein Weg durch den KI-Layer wäre ein Modell, das ein Modell aufruft.

Der KI-Layer ist der **Arbeiter an der Pipeline**: er macht aus Wahrnehmungen
Feststellungen, unbeaufsichtigt, mit Haiku über die Batch API. Ausgelöst wird
er vom Eingang, nicht vom Benutzer.

### MCP-Werkzeuge (im MVP die gesamte Oberfläche)

| lesend | schreibend |
|---|---|
| `previously(organization\|project\|matter, as_of?)` | `submit(content, organization?, project?, matter?)` |
| `list_open_obligations(project?, own_role?)` | `record_assertion(…)` — Korrektur, `responsibility: {jens, direct}` |
| `list_decisions(project\|organization, period?)` | `list_approvals()` / `approve(id, once\|class)` |
| `search(query, project?, before?)` — der RAG-Pfad (§18) | |
| `get_event(id)` / `get_units(event_id)` — Zitaten folgen | |

**Fünf Teile.** Ingest und Write-back sind *eine* Schicht, weil jedes
Fremdsystem beides ist.

1. **Konnektoren** (bidirektional) — IMAP, Drop-Ordner, Einwurf per Prompt,
   Quelle verlinken, OpenProject, GitLab, Nextcloud, später mehr.
2. **Voice** — PipeWire-Abgriff, Transkription, Diarisation. Nur
   Inbox-Richtung. *Nicht im MVP.*
3. **Kern** — Event-Log, Hash-Kette, Kernmodell, Identitätsgraph,
   Projektionen. Das Rückgrat.
4. **KI-Layer** — Gate, Policy, Audit, Retrieval, Zerlegung, Templates,
   Freigabeklassen.
5. **Oberfläche** — *Im MVP ist das Claude Code über MCP.*

---

## 5. Kern, Schicht 1: Das Event-Log

Eine append-only Folge. Drei Event-Arten, und die Unterscheidung trägt das
gesamte Audit-Konzept.

| Art | Inhalt | Erzeuger |
|---|---|---|
| **Wahrnehmung** | Eine Mail kam an. Ein Redebeitrag. Eine Datei wurde eingeworfen. Ein Issue hat sich geändert. | Konnektoren. **Nie das Modell.** |
| **Feststellung** | "Einheiten 3–4 gehören zu Vorgang X." · "Das ist eine Verpflichtung mit Frist 30.4." · "Der Kunde hat Y entschieden." | Modell **oder** Mensch |
| **Handlung** | "GitLab-Issue #42 angelegt." · "Mail versendet." — mit der Freigabe, auf der sie beruht. | Freigabe-Schicht |

### 5.1 Wahrnehmung

```
id, hash, prev_hash
recorded_at                 wann es in den Speicher kam
occurred_at                 wann es tatsächlich geschah
source + external_id        welcher Pfad + sourcesnative ID
evidence                    verbatim | recollection
channel_identities
units                       [{seq, content, …}]
```

**`evidence` trennt Beweis von Bericht.** Mail, Issue, Transkript und PDF sind
`verbatim`. Eine diktierte Notiz ist `recollection`.

Der Unterschied ist nicht kosmetisch. Wird ein Telefonat eingeworfen — "Kunde
XYZ hat angerufen und gesagt, die Lieferung kommt erst im Mai" — dann ist die
**Wahrnehmung nicht das Telefonat, sondern die Notiz darüber.** Das Telefonat
wurde nicht erfasst, nur der Bericht davon. So bleibt Leitsatz 4 intakt:
"Jens hat das notiert" kann nicht falsch sein, "der Kunde hat zugesagt" kann es.

Im Protokoll wird es sichtbar:

```
2026-05-02  Kunde verschiebt Lieferung auf Mai.  [M-0455 ¶3]
2026-10-01  Kunde verschiebt Lieferung auf Juni.  [N-0112 — Notiz, Erinnerung]
```

Im Streitfall ist der Unterschied zwischen "der Kunde hat das geschrieben" und
"Jens erinnert sich, dass der Kunde das sagte" entscheidend. Die
Unterscheidung fällt gratis an, wenn die Notiz als Notiz modelliert wird, und
ist unwiederbringlich verloren, wenn beides als gleichwertiges Event eingeht.

**Nebeneffekt, der eigenständigen Wert hat:** Eine große Verpflichtung, die
nur von einer `recollection` getragen wird, ist ein Signal, das schriftlich
nachzuziehen.

`evidence` steht orthogonal zu `author` und `responsibility` (§5.2): die
beiden sagen, wer formuliert hat und wer einsteht; `evidence` sagt, **wie gut
der Beleg darunter ist**. Eine von Jens eingeworfene Notiz hat
`responsibility: {jens, direct}` und trägt volles Gewicht — und gleichzeitig
`evidence: recollection`, weil die Grundlage ein Gedächtnis ist. Seine Zuordnung
bleibt Grundwahrheit; nur die inhaltliche Behauptung trägt den Vorbehalt.

**Zwei Zeitstempel sind zwingend.** Die Hash-Kette ist nach `erfasst_am`
geordnet — anders ist sie keine Kette. Jede Chronik ist nach `ereignis_zeit`
geordnet — anders ist sie keine Chronik. Beim Bestandsimport fallen beide
Ordnungen auseinander, und beide werden gebraucht. Als Nebeneffekt wird
"Was wusste ich am 14. März?" in beiden Bedeutungen beantwortbar: was bis
dahin geschehen war, und was damals im Speicher stand.

**Die quellennative ID trägt die Idempotenz.** Ein zweiter Import verdoppelt
nichts.

**Einheiten** sind die nummerierte, mechanische Zerlegung des Inhalts.
Mechanisch, nicht interpretierend — deshalb Teil der Wahrnehmung.

| Medium | Einheit |
|---|---|
| Mail, PDF | Absatz |
| Transkript | Redebeitrag (liefert die Diarisation) |
| Issue | Beschreibung, dann je Kommentar |

**Die Sprache hängt an der Einheit, nicht am Dokument.** Projekte enthalten
regelmäßig deutsche und englische Texte — eine deutsche Mail, die eine englische
Spezifikation zitiert; ein Transkript, in dem gewechselt wird, weil ein Partner
dazukommt. Die Einheit ist die richtige Körnung dafür und schon vorhanden.

Die Sprachbestimmung ist eine **Feststellung, keine Eigenschaft der
Wahrnehmung**: Spracherkennung ist ein Klassifikator und kann irren, besonders
bei kurzen Einheiten. Nach Leitsatz 4 gehört sie damit ins Fehlbare — und eine
Neubestimmung mit besserem Erkenner ist später eine neue Feststellung, keine
Migration.

Eine Neutranskription mit besserem Modell ist eine **neue** Wahrnehmung, keine
Änderung der alten.

### 5.2 Feststellung

```
id, hash, prev_hash, recorded_at
kind                assignment | obligation | decision | language | …
target              event-id
units               [3, 4, 7, 12]      verteilt, nicht zusammenhängend
author              human:<person> | model:<id+version> | rule:<id> | unknown
responsibility      { person, kind: direct | transitive, basis? } | null
confidence
payload             artabhängig
sources             Event-IDs + Einheiten, auf die sie sich stützt
```

**Zwei Felder, weil es zwei verschiedene Fragen sind:** wer hat die Aussage
*formuliert*, und wer *steht dafür ein*. Sie fallen regelmäßig auseinander:

| Fall | `author` | `responsibility` |
|---|---|---|
| Jens tippt eine Korrektur | `human:jens` | `{jens, direkt}` |
| Die Pipeline extrahiert eine Verpflichtung | `model:haiku-4-5` | `offen` — Vorschlag bis zur Abnahme |
| Ein Agent legt auf Jens' Anweisung ein Issue an | `model:claude-code` | `{jens, transitiv}` |
| Der Auftraggeber schreibt eine Mail | `human:<contact>` | **nicht Jens** |

### Verantwortung ist direkt oder transitiv

Ein `Assisted-By`-Marker heißt nicht "unverantwortet". Arbeitet ein Agent unter
einem Spec oder Plan, den Jens abgenommen hat, dann ist das Ergebnis **transitiv
abgesegnet** — er hat den Vorgang autorisiert, auch wenn er diese einzelne
Zeile nicht gelesen hat.

| `art` | Bedeutung |
|---|---|
| `direkt` | selbst getippt, oder dieser Einzelfall abgenommen |
| `transitiv` | unter einem abgenommenen Spec, Plan oder einer Freigabeklasse entstanden; `grundlage` zeigt darauf |
| — (`offen`) | niemand hat etwas autorisiert |

**Transitive Verantwortung ist kein Notbehelf, sondern das, was Delegation erst
tragfähig macht.** Müsste jede Agentenausgabe einzeln gelesen werden, wäre
Delegieren sinnlos. Dieselbe Idee trägt schon die Handlungs-Befugnis
`authorization: class:<id>` (§5.4) — hier ist sie für Feststellungen formuliert, und
die Symmetrie ist ein Hinweis darauf, dass es die richtige Abstraktion ist.

Wo die `grundlage` nicht ermittelbar ist — ein Marker sagt "ein Modell war
beteiligt", aber nicht unter welchem Plan — ist `transitiv` mit unbekannter
Grundlage ein zulässiger Zustand. Jens hat *etwas* autorisiert; was, wissen wir
nicht.

### Vorrangordnung läuft über `responsibility`, nicht über `author`

**`direkt` schlägt `transitiv` schlägt `offen`**; unter `offen` gilt **Regel vor
Modell**, weil Regeln deterministisch und nachprüfbar sind. Unabhängig davon,
wer formuliert hat.

Der Grund für die Abstufung: was Jens selbst gelesen hat, wägt schwerer als
was unter einem von ihm abgenommenen Plan entstand, ohne dass er es gesehen
hat. Beides trägt, aber nicht gleich schwer — und im Streitfall sind "das habe
ich selbst geprüft" und "das entstand unter einem abgenommenen Verfahren" zwei
verschiedene, beide ehrliche Aussagen. Die Unterscheidung ist abfragbar.

Eine Korrektur durch Jens ist damit kein Sonderfall: sie ist eine Feststellung
mit `responsibility: {jens, direct}`. Das gilt gleichermaßen für eine Korrektur am
Protokoll und für eine Änderung, die direkt in einem Fremdsystem gemacht wurde.

**Warum die Trennung nötig ist — der Fall, der sonst still falsch läuft:** Eine
Mail des Auftraggebers ist von einem Menschen geschrieben. Mit einem einzigen
`origin`-Feld hätte sie unser Modell geschlagen *und* wäre gleichrangig mit
Jens' eigener Korrektur gewesen. Behauptet der Auftraggeber "Sie haben X
zugesagt" und die Aufzeichnungen sagen anderes, darf seine Behauptung nicht
gewinnen, nur weil ein Mensch sie getippt hat.

**Wessen Behauptung es ist, ist Inhalt. Wessen Autorität sie trägt, ist
Metadatum.** Die Mail bleibt `evidence: verbatim` und starker Beleg; die daraus
gezogene Feststellung hat `author: model` (der Extraktor hat sie gelesen) und
`responsibility: null`, bis Jens sie sich zu eigen macht.

### `author` ist oft nicht feststellbar

Ein Fremdsystem verzeichnet als Autor den Kontoinhaber — ein Agent handelt mit
Jens' Token und ist von Handänderung nicht zu unterscheiden. Das einzige
maschinenlesbare Signal sind **Marker im Text**: `Co-Authored-By`- und
`Assisted-By`-Zeilen in Commits, Trailer in Beschreibungen, Labels. Der
Konnektor wertet sie aus. (`Assisted-By` wird in den Projekten schon gesetzt,
aber nicht flächendeckend — deshalb bleibt `unknown` ein eigener Wert und
keine Annahme.)

**Wo kein Marker ist: `author: unknown`, nicht `human` angenommen.**
Unbekannt wird aus der Grundwahrheitsmenge ausgeschlossen (§8.5). Lieber eine
kleinere, ehrliche Messbasis als eine große, in der Modelloutput als
menschliches Urteil mitläuft.

**Nur Feststellungen kommen aus dem Modell.** Damit ist "Was hat das Modell je
behauptet, und worauf gestützt?" eine Abfrage über eine Event-Art.

**`sources` ist Pflicht und wird im Schema erzwungen.** Eine Feststellung ohne
Quellenangabe ist kein Vertrauensproblem, sondern ein Schemafehler. Das Modell
wird nie um freien Text gebeten, sondern immer um strukturierte Ausgabe mit
diesem Feld.

### 5.3 Zuordnungs-Feststellungen bilden keine Partition

Über einem Event dürfen sich Zuordnungen **überlappen**, und sie müssen den
Inhalt **nicht abdecken**.

- **Lücken sind erlaubt und gewollt.** Begrüßung und Smalltalk gehören zu
  keinem Vorgang. Ein System, das alles zuordnen *muss*, erzeugt dort Müll,
  und Müll in der Zuordnung verfälscht jedes Protokoll.
- **Überlappungen sind erlaubt.** "Wegen des Change Requests verschieben wir
  die Rechnung" gehört zu zwei Vorgängen, und zwar wirklich zu beiden.

### 5.4 Handlung

```
id, hash, prev_hash, recorded_at
kind                task_created | mail_sent | …
target              Entität, auf die sie wirkt
authorization       instructed | once | class:<id>
basis               assertion-IDs
result              external_ref, rendered_state, error
```

**Handlung ist die Spur delegierter Handlungsmacht** — sie beantwortet "was hat
das System getan, und mit welcher Befugnis?".

Daraus folgt eine beabsichtigte Asymmetrie: **Was Jens selbst tut, ist keine
Handlung, sondern Eingang.** Legt er ein Issue direkt in GitLab an, sieht der
Konnektor die Änderung, sie wird Wahrnehmung, daraus eine Feststellung mit
`responsibility: {jens, direct}`. Ein Befugnisnachweis ist dafür sinnlos — er
ist der
Auftraggeber, nicht der Beauftragte.

Die drei Befugnisse:

| Wert | Bedeutung |
|---|---|
| `instructed` | direkt angewiesen (z. B. in Claude Code), es gab keinen Vorschlag |
| `once` | ein Vorschlag wurde abgenommen, dieses eine Mal |
| `class:<id>` | eine Dauerfreigabe deckte es |

**Eine Handlung ohne einen dieser Werte ist ein Defekt, kein Zustand.** Einen
Wert wie "nie gefragt" als zulässig zu führen würde unautorisiertes Handeln
normalisieren; die Integritätsprüfung (§15) schlägt darauf an.

### 5.5 Rückkopplung ist gewollt, Schwingung nicht

Dieses System **ist** eine Rückkopplungsschleife, und das ist Absicht. Das
System schlägt ein Issue vor, Jens ändert es in GitLab, die Änderung fließt
zurück und verbessert das Verständnis im Kern. Diese Schleife ist der
**Lernmechanismus**: eine Korrektur an einem vom System erzeugten Artefakt ist
Grundwahrheit nach §8.5 — der wertvollste Eingang überhaupt.

Eine Regel wie "ignoriere alles zu Issue #42" würde genau dieses Signal
wegwerfen. Zu verhindern ist nicht die Schleife, sondern die **selbsterhaltende
Schwingung**: ein Umlauf, der Zustand ändert, ohne Information hinzuzufügen.

Vier Bedingungen sichern Konvergenz. Drei folgen schon aus Entscheidungen
anderswo im Entwurf — das ist kein Zufall, sondern der Grund, warum sie
getroffen wurden.

**1. Idempotentes Rendern.** Dieselbe Projektion zweimal gerendert ergibt
denselben Zielzustand; der zweite Durchlauf ist ein No-Op (§11.1). Keine
Bequemlichkeit, sondern eine Konvergenzbedingung.

**2. Keine Wahrnehmung ohne neue Information.** Der Konnektor meldet nur, wenn
der eingehende Zustand von dem abweicht, was er zuletzt dorthin gerendert hat
(`ergebnis.gerenderter_zustand` der Handlung). Abweichung heißt: jemand
anders hat etwas geändert. Der Vergleich dient der **Informationsprüfung**,
nicht der Abwehr.

**3. Strikte Vorrangordnung.** Verantwortet schlägt unverantwortet, darunter
Regel vor Modell, strikt (§5.2). Damit ist die wahrscheinlichste Schwingung
konstruktiv unmöglich — Modell behauptet A, Mensch korrigiert auf B, Modell
behauptet wieder A — weil eine unverantwortete Feststellung eine verantwortete
nie überschreiben darf.

Für Modell gegen Modell gilt zusätzlich: **nur bei sachlicher Änderung
schreiben.** Eine neue Feststellung entsteht nur, wenn sich die Eingangsmenge
oder die Prompt-Version geändert hat; eine bloß anders formulierte Aussage
über dieselben Einheiten wird verworfen.

**4. Ein Schwingungswächter statt eines Verbots.** Weil Rückkopplung gewollt
ist, ist Detektion das richtige Werkzeug: ändert eine Entität ihren Zustand
mehr als k-mal in einem Zeitfenster, **ohne dass in der Ursachenkette eine
externe Wahrnehmung oder ein Mensch vorkommt**, wird die Kette angehalten und
landet in der Queue — nicht als Fehler, sondern als Beobachtung. Das erlaubt
beliebig tiefe legitime Rückkopplung und fängt nur den unbedachten Fall.

**Das Log diagnostiziert sich selbst.** Weil alles append-only mit
Ursachenangabe vorliegt, ist eine Schwingung im Log *sichtbar*: als Kette von
Feststellungen, deren Ursachen zirkulär auf eigene Handlungen zurückführen,
ohne externen Eintritt. Nachträglich auffindbar, nicht nur zur Laufzeit
abfangbar. Ein weiteres Argument für Leitsatz 3: wer Projektionen mutiert
statt sie zu berechnen, hat diese Diagnose nicht.

### 5.6 Erfüllung wird beobachtet, nicht gemeldet

Ein Commit, der ein Issue schließt, ist Beleg dafür, dass eine Verpflichtung
erfüllt wurde. Niemand hakt etwas ab: Jens arbeitet, der Konnektor sieht es,
und die Verpflichtung wechselt den Zustand mit Quellenangabe auf den Commit.

Umgekehrt zu jedem Ticketsystem, in dem doppelt gearbeitet wird — erst tun,
dann eintragen, dass man es getan hat. Gilt überall, wo die Fähigkeitsstufe
mindestens "nur lesend" erreicht ist.

### 5.7 Hash-Kette

Jeder Eintrag hasht seinen Vorgänger. Rund zwanzig Zeilen Code, heute fast
kostenlos, nachträglich unmöglich. Sie belegt, dass nichts nachträglich
verändert oder entfernt wurde.

Angenommen ist dabei: belegbar für Jens und auf Kundennachfrage, **nicht**
zertifizierungsgetrieben. Keine Aufbewahrungsfristen-Automatik, keine
WORM-Speicherung, keine Prüfer-Exportformate. Kommt ein harter externer
Anlass dazu (ISO 27001, Vertragsklausel, öffentlicher Auftraggeber), wird
dieser Abschnitt zu einem eigenen Teilprojekt.

---

## 6. Kern, Schicht 2: Zehn Entitäten

Alle sind Projektionen über das Event-Log, keine Wahrheitstabellen. Alle
überleben den Wegfall jedes Fremdsystems.

| # | Entität | Zweck |
|---|---|---|
| 1 | **Organisation** | Firma, Einzelperson, Verein, Behörde. **Keine Rolle im Namen** — "Kunde" ist eine Beteiligung, keine Art von Organisation. Die eigene ist mit `own` markiert. |
| 2 | **Projekt** | Ein Vorhaben mit mehreren beteiligten Organisationen. Muss verschobene Grenzen und Umbenennungen aushalten. |
| 3 | **Person** | Ein Mensch. |
| 4 | **Kanalidentität** | Mailadresse, Signal-Nummer, Discord-Handle, Sprecherkennung, Fremdsystem-Benutzer. Eigenständig, weil eine unbekannte Adresse eine Identität **ohne** Person ist — das ist der Zustand "unsortiert". |
| 5 | **Beteiligung** | Akteur (Person **oder** Organisation) × Ziel (Projekt oder Aufgabe) × Rolle × Zeitraum. |
| 6 | **Vorgang** | Die inhaltliche Klammer. Primäre Zugangsebene. |
| 7 | **Verpflichtung** | Wer schuldet wem was, bis wann, in welchem Zustand. **Schuldner und Gläubiger**, beide Akteure. |
| 8 | **Aufgabe** | Ausführbare Arbeit. Trägt die PM-Verknüpfung. |
| 9 | **Entscheidung** | Was wurde entschieden, von wem, wann, auf welcher Grundlage. |
| 10 | **Vereinbarung** | NDA, AVV, Rahmen- oder ARGE-Vertrag. Begrenzt, **wer was sehen darf** — und das hängt an der Beziehung, nicht an der Organisation. |

### 6.1 Organisation und Beteiligung

**"Kunde" ist keine Entitätsart, sondern eine Rolle in einem Projekt.** Die
gelebte Wirklichkeit der letzten zwanzig Jahre: ein Projekt hat eine
Designagentur mit eigenen Leuten, einen Auftraggeber, eine Hostingfirma und
Projektpartner aus der BlueDynamics Alliance. Dieselbe Organisation ist in
einem Projekt Auftraggeber (wir als Subunternehmer), im nächsten ARGE-Partner
auf Augenhöhe, daneben dauerhaft Allianzpartner.

`Organisation.art`: `company | sole_trader | association | public_body`. Der Fall
`einzelperson` deckt ab, dass wirklich eine natürliche Person Auftraggeber
ist, und darf auf eine `Person` verweisen — ohne den Menschen mit seiner
Gesellschaft zu verwechseln. Die eigene Organisation trägt `own`.

**Beteiligung ist eine Relation über Akteure**, nicht zwei getrennte
Relationen. Akteur ist Person oder Organisation; das Rollenvokabular ist nach
Akteursart getrennt, die Relation ist dieselbe. Der Grund ist nicht Sparsamkeit,
sondern Leitsatz 7: wenn es **einen** Ort für Rollen gibt, kann man beim
nächsten Mal nicht vergessen, eine Rolle relational zu machen.

| Akteursart | Rollen (erweiterbar) |
|---|---|
| Organisation | `client`, `contractor`, `subunternehmer`, `arge-partner`, `allianzpartner`, `dienstleister` |
| Person | `mitarbeiter`, `partner`, `freelancer`, `ansprechpartner` |

Das Vokabular ist **erweiterbar, nicht abgeschlossen.** Ein fester Satz wäre
nach zwanzig Jahren wechselnder Konstellationen innerhalb eines Jahres falsch.

Weitere Eigenschaften, unverändert aus der vorigen Fassung:

- Alex ist *Freelancer bei Projekt A* **und** *Freelancer bei Projekt B* —
  zwei Beteiligungen, nicht zwei Rollen an einer Person.
- Das Ziel ist Projekt **oder** Aufgabe. Grobe und feine Beteiligung sind kein
  Modellunterschied, nur ein Zielunterschied. (Organisationsbeteiligung geht
  praktisch nie auf Aufgabenebene — die Relation wird ungleichmäßig genutzt,
  das ist in Kauf genommen.)
- Der Zeitraum fällt gratis an, weil Beteiligung eine Projektion über
  Feststellungen mit Ereigniszeit ist. "Wer war im März 2024 beteiligt?" ist
  dieselbe Abfrage mit anderem Stichtag.

### 6.2 Verpflichtung und Aufgabe sind zwei Dinge

| | |
|---|---|
| **Verpflichtung** | Der Sachverhalt: "Wir schulden dem Auftraggeber den Bericht bis 30.4." |
| **Aufgabe** | Die Arbeit: "Kapitel 3 schreiben", "Review mit Anna". |

Eine Verpflichtung erzeugt null bis mehrere Aufgaben. Eine Aufgabe kann ohne
Verpflichtung existieren (interne Arbeit).

**Schuldner und Gläubiger sind beide Akteure**, nicht eine binäre Richtung
"wir / die anderen". Daraus ergeben sich **drei** Fälle, nicht zwei:

| Schuldner | Folge |
|---|---|
| die eigene Organisation | erzeugt Aufgaben |
| ein anderer, Gläubiger sind wir | erzeugt **keine** Aufgabe, wird überfällig, muss sichtbar sein |
| zwei andere, uns betreffend | **beobachtet** — wir treiben es, ohne Partei zu sein |

#### Eine Verpflichtung kann selbst geteilt werden

"Wir liefern den Bericht **und** die Datenmigration bis 30.4." ist eine
Verpflichtung, die zwei Sachen bündelt. Solange sie eine ist, ist ihr Zustand
**unehrlich**: Bericht geliefert, Migration nicht — "halb erfüllt" ist keine
Information. Nach dem Teilen gibt es eine `fulfilled` und eine `offen`, und die
ist überfällig. **Das Teilen ist, was den Zustand wahr macht.**

Darum ist es eine eigenständige Operation und kein Nebeneffekt eines
Vorgangs-Splits — auch wenn ein Vorgangs-Split sie oft auslöst.

Mechanik wie beim Vorgang: `obligation_split { from: V, into: [V1, V2] }`,
V bleibt als **Dach** mit `split_into`, und sein Zustand wird aus den Teilen
berechnet:

| Teile | Dach |
|---|---|
| alle erfüllt | `fulfilled` |
| irgendeiner überfällig | `overdue` |
| gemischt | `partially_fulfilled` |

Frist, Schuldner und Gläubiger können sich pro Teil unterscheiden — das ist
häufig der eigentliche Grund zu teilen.

Der dritte Fall ist kooperatives Projektmanagement in Reinform:

> *"Die Hostingfirma schuldet der Designagentur die DNS-Umstellung — und das
> blockiert uns."*

Eine Verpflichtung, bei der wir weder Schuldner noch Gläubiger sind, die aber
überfällig werden kann und im Protokoll stehen muss. In keinem Werkzeug
abbildbar, das nur "meine Aufgaben" kennt. Dasselbe gilt für Ketten:
wir → Subunternehmer-Auftraggeber → Endauftraggeber ist eine Kette, nicht
zwei unverbundene Zweiparteien-Sachen.

Arten: `delivery`, `answer`, `decision`, `payment`.

**`debtor` darf leer sein.** Eine unadressierte Frage — "weiß eigentlich
jemand, ob die Messdaten georeferenziert sind?" — ist eine Verpflichtung mit
`kind: answer` und leerem Schuldner. Das liest sich als "jemand muss das
beantworten, wir wissen noch nicht wer" und ist der Zustand, aus dem heraus
zugewiesen wird. Genau das ist die offene Frage von vor vier Monaten, die
gefunden werden soll.

Die PM-Verknüpfung (`openproject:wp/123`, `gitlab:issue/42`, `jira:ABC-17`)
hängt an der **Aufgabe** und lebt in der Adapter-Abbildung. **Binden** (auf
einen bestehenden Task zeigen) und **generieren** (einen neuen anlegen) sind
dieselbe Verknüpfung, einmal vorhanden und einmal erzeugt.

### 6.3 Vorgang

**Eine zusammenhängende Klärung oder Abwicklung mit erkennbarem Anlass und
erkennbarem Abschluss.** Beispiele: "Change Request Datenmodell", "Angebot
Phase 2", "Exportfehler vom 14.3." Feiner als ein Projekt, grober als ein
Event. Hängt an einem Projekt — oder, wenn er projektübergreifend ist, an
einer Organisation.

Technisch ein Bündel von Einheiten aus mehreren Events, angesetzt an harten
Signalen (Mail-Thread-Header, Issue-Referenzen, Nummernverweise), vom Modell
erweitert, von Jens korrigierbar.

**Der Vorgang ist die einzige Entität mit unscharfer Grenze** — die anderen
acht haben klare Identitätskriterien. Daraus folgt nicht, dass er unwichtig
ist: er ist die primäre Zugangsebene. Unschärfe ist für einen Zugangsweg
unschädlich und nur für Autorität tödlich. Ein Vorgang, der zwei Themen
zusammenfasst, ist beim Suchen immer noch nützlich; eine Frist, die von einer
Vorgangsgrenze abhängt, wäre falsch.

**Also: zentral als Zugang, nie autoritativ für Fakten.**

#### Mergen und Splitten

Durch neue Erkenntnis muss ein Vorgang aufgeteilt werden, oder zwei stellen
sich als dasselbe heraus. Beides ist vorgesehen — und beides ist **nicht
symmetrisch**.

**Mergen: umleiten, nie löschen.** Eine Feststellung
`matter_merge { from: B, into: A, rationale, sources }`. B behält
seine Kennung und bekommt den Zustand `merged_into: A`; Projektionen
folgen der Umleitung.

Das ist praktisch wichtig, nicht nur formal: **alte Verweise auf B funktionieren
weiter.** B's Kennung steht vielleicht in einem Work Item, in einer Mail, in
einem Protokoll beim Auftraggeber. Und Verpflichtungen und Entscheidungen, die
auf B zeigten, werden **nicht umgeschrieben** — die Auflösung folgt dem Zeiger.
Keine Historienänderung.

**Splitten lässt das Ursprüngliche als Dach stehen.** Die Einheiten brauchen
keinen neuen Mechanismus: das sind Zuordnungs-Feststellungen mit anderem
`matter`, genau wie jede menschliche Korrektur. Das Problem ist, **was an A
hing**: eine Verpflichtung, die auf A zeigte, gehört zu A1 oder A2, und das kann
das System nicht wissen.

Beim Mergen zeigt die Umleitung auf *ein* Ziel; beim Splitten auf mehrere, also
ist "löse A auf" nicht beantwortbar. Ein Standard-Nachfolger wäre eine
Vermutung, die als Tatsache auftritt — Leitsatz 9 verbietet das. Stattdessen:

`matter_split { from: A, into: [A1, A2], rationale, sources }`. A bleibt und
bekommt `split_into: [A1, A2]`.

- **Alte Verweise auf A bleiben sinnvoll** — sie meinen "die Sache als Ganzes".
- **Abhängigkeiten bleiben am Dach, bis jemand es besser weiß.** Eine
  Verpflichtung, die an A hing, hängt danach an "A als Ganzes" — eine *wahre*
  Aussage, während "A1" eine Vermutung wäre. Keine Waisen, keine Falschzuweisung.
- **Die Entscheidung ist aufschiebbar, ohne Schaden** — siehe §6.4.

**Beides bleibt dauerhaft freigabepflichtig — benannte Ausnahme von der
Risiko-Ordnung in §10.3.** Ein Merge ist strukturiert und intern, wäre nach jener
Tabelle also früh automatisierbar. Hier ist das falsch: der Vorgang ist die
primäre Zugangsebene, und wenn das Modell im Hintergrund umgruppiert, bricht die
mentale Landkarte. Der Schaden ist nicht Datenverlust — beides ist umkehrbar —
sondern **Orientierungsverlust**, und der ist bei einem Werkzeug, das Übersicht
verschaffen soll, der schwerere. Modell darf vorschlagen, nur ein Mensch
ausführen.

**Stichtagsabfragen funktionieren weiter.** "Vorgangsprotokoll von A, Stand
März", obwohl A und B im September zusammengelegt wurden: über `erfasst_am`
erscheint A ungemergt, so wie es im März bekannt war; über `ereignis_zeit` der
zusammengelegte Inhalt bis März. Beide Antworten sind sinnvoll, und die zwei
Zeitstempel liefern beide.

---

### 6.4 Faule Auflösung: nie blockierend fragen

Weil das Dach nichts blockiert, muss niemand im Moment des Teilens entscheiden.
"Im Zweifel den Menschen fragen" würde sonst wieder den Fragebogen erzeugen,
den §6.3 verwirft.

> **Nicht fragen, weil die Daten unvollständig sind — fragen, wenn eine Antwort
> gebraucht wird.**

| Auslöser | Queue-Eintrag |
|---|---|
| Eine Frist nähert sich, unklar für welchen Teil sie gilt | "Welcher Teil ist am 30.4. fällig?" |
| Das Protokoll würde irreführend | "V1 oder V2 — sonst steht da 'teilweise erfüllt' ohne Aussage" |
| Jemand fragt nach dem Zustand eines Teils | direkt im Moment der Frage |

Dazwischen liegt es am Dach und stört niemanden. Das Modell darf jederzeit eine
Aufteilung mit Belegstellen vorschlagen, aber die Queue füllt sich nur, wenn es
beisst. Das ist der Unterschied zwischen einer Queue, die man anschaut, und
einer, die man wegklickt — vgl. §10.4.

### 6.5 Vereinbarung

Eine Organisation ist nicht pauschal vertrauenswürdig oder nicht. Eine Agentur
hat mit Auftraggeber A ein NDA unterschrieben und darf dessen Projektinhalte
sehen; mit Auftraggeber B hat sie keines, und derselbe Partner darf dort nichts
sehen. **Gleiche Organisation, unterschiedliche Befugnis je Projekt — begrenzend
ist die Vereinbarung, nicht die Organisation.**

```
agreement
  kind        nda | dpa | framework | joint_venture
  parties     [organization]
  scope       project | organization | global
  valid_from / valid_until
  sources     ← der unterschriebene Vertrag
```

Die Entität passt in die vorhandene Mechanik, ohne etwas Neues zu brauchen: der
Vertrag liegt als PDF im Drop-Ordner, ist damit eine Wahrnehmung mit
`evidence: verbatim`, und die Vereinbarung ist eine Feststellung mit genau
diesem Beleg. Die Frage "warum durfte die Agentur das sehen?" endet damit beim
unterschriebenen Dokument.

**Offenlegungsbefugnis wird nicht gespeichert, sondern abgefragt** — eine
Projektion: *gibt es eine gültige Vereinbarung, die diesen Umfang abdeckt und
diesen Empfänger einschließt?*

## 7. Kern, Schicht 3: Organisationsprofil

Alles, was pro **Organisation** variiert, an einer Stelle. Gelesen vom
Policy-Gate, vom Konnektor-Lader und von der Freigabe-Queue.

```
organization
jurisdiction            AT | DE | CH | EU | …   (maßgebliche Rechtsordnung)
systems                 [{kind, base_url, capability, credentials_ref}]
data_policy             { external_allowed: bool,
                          allowed_regions: [EU, CH, …],
                          excluded_providers: […] }
approval_classes        [{action_class, state}]
recording_consent
```

**Die Datenpolitik ist strukturiert, nicht dreiwertig.** Eine frühere Fassung
hatte `cloud_allowed | tiered | local_only` — das kann **"EU ja, USA nein"**
nicht ausdrücken, und genau das wird die häufigste Auflage sein, nicht
"nur lokal".

**Die Schweiz ist nicht EU.** Dort gilt das revidierte DSG, nicht die DSGVO.
EU-Verarbeitung ist für einen Schweizer Auftraggeber also nicht automatisch die
Antwort, und Schweizer Verarbeitung für einen EU-Auftraggeber nicht automatisch
ausreichend — zwei Regime, keine Abstufung einer Skala. Daher ist
`allowed_regions` eine Liste und kein Rang.

### 7.1 Auflösung bei mehreren Beteiligten

Ein Projekt hat mehrere beteiligte Organisationen, und jede bringt ihr Profil
mit. **Es gilt die strengste Festlegung** (Leitsatz 8) — nicht die des
Auftraggebers, nicht die zuerst eingetragene.

| Gegenstand | Auflösung |
|---|---|
| `data_policy` | strengste aller Beteiligten. Sagt eine Organisation `local_only`, gilt das für **alles** in diesem Projekt. |
| `recording_consent` | eine Besprechung darf nur mitgeschnitten werden, wenn **jede** anwesende Organisation zugestimmt hat **und** die Zustimmung der strengsten beteiligten Rechtsordnung genügt |
| `jurisdiction` | ein Gespräch mit Beteiligten aus mehreren Rechtsordnungen berührt alle gleichzeitig; praktisch bindet die strengste |
| `approval_classes` | eine Dauerfreigabe gilt nur, wenn keine beteiligte Organisation sie ausschließt |

Beispiel: Sagt der Auftraggeber "unsere Daten bleiben in der EU" und die
Designagentur ist entspannt, dann gilt EU — für den gesamten Projektinhalt,
auch für die Mails der Designagentur.

**Zugangsdaten** hängen dagegen an der einzelnen Organisation und werden nicht
aufgelöst: das GitLab der einen öffnet man nicht mit dem Schlüssel der anderen.

### 7.2 Verarbeitungspolitik ist nicht Offenlegungsbefugnis

Zwei verschiedene Fragen, die leicht verwechselt werden:

| | Frage | Gegenstand |
|---|---|---|
| **Verarbeitungspolitik** | Wo darf dieser Inhalt *verarbeitet* werden? | Maschinen, Anbieter, Rechtsräume |
| **Offenlegungsbefugnis** | Wer darf diesen Inhalt *sehen*? | Organisationen, Personen, Vereinbarungen (§6.5) |

**Die Befugnis gilt am Ausgang, nicht am Eingang.** Das ist die entscheidende
Festlegung. Fragt Jens *"was wissen wir über die Leistungsfähigkeit dieser
Agentur?"*, speist sich die Antwort legitim aus **allen** Projekten — das ist
sein Wissen, keine Offenlegung. Griffe die Befugnis beim Abrufen, könnte er
seine eigene Erfahrung nicht nutzen.

Geprüft wird, wenn Inhalt **an eine Partei hinausgeht**: Mail, Issue in deren
Tracker, geteiltes Protokoll.

> **Verarbeitungspolitik gilt am Eingang. Offenlegungsbefugnis gilt am Ausgang.**

Daraus folgen drei Prüfpunkte:

| Prüfpunkt | prüft |
|---|---|
| **Gate** (§10.1) | Verarbeitung — darf das in die Cloud? (Pipeline) |
| **MCP-Server** (§10.1) | Verarbeitung — darf Claude Code das sehen? (interaktiv) |
| **Renderer / Aktionsschicht** | **Offenlegung** — darf dieser Empfänger das sehen? |

#### Das Publikum: Zielorte werden erklärt, nicht entdeckt

Ein Work Item im GitLab eines Partners sieht **jeder dort**, nicht nur der
Ansprechpartner. Und "dort" ist nicht das System, sondern der Container darin:
ein GitLab-Projekt, eine Gruppe, ein Nextcloud-Ordner, ein Confluence-Space mit
Page Restrictions. Jedes System hat ein eigenes Berechtigungsmodell — GitLab
Instanz/Gruppe/Untergruppe/Projekt mit Rollen, JIRA Permission Schemes und
Issue Security Levels, Nextcloud Freigaben und Links.

**Diese Modelle werden nicht nachgebildet.** Sie nachzubauen und synchron zu
halten wäre N Berechtigungssysteme als Nebenprodukt — das Projekt würde daran
sterben. Zwei Umkehrungen vermeiden es.

**Erste Umkehrung: nicht "welches Publikum hat ein beliebiger Container?",
sondern "wohin rendert dieses Projekt?"** Das ist eine kurze, endliche Liste,
die beim Projektaufsetzen ohnehin festgelegt wird — typisch zwei bis fünf
Zielorte. Ein Konfigurationsproblem in Menschengröße statt ein
Entdeckungsproblem in Systemgröße.

**Zweite Umkehrung: Deklaration ist das Gate, Aufzählung nur die Prüfung.**

| | Mechanik | verfügbar |
|---|---|---|
| **Gate** | Jeder Zielort **erklärt**, welche Vereinbarung ihn deckt. Rendern erlaubt, wenn der Inhaltsumfang gedeckt ist. Ein Nachschlagen. | **immer** |
| **Prüfung** | Wo die API es hergibt: Mitglieder aufzählen, gegen die Deckung vergleichen. Abweichung → **Warnung, keine Sperre**. | je Adapter |

Das Gate braucht kein Berechtigungsmodell, keine API, keinen Adapter. Es ist
eine Aussage: *"diese Gruppe ist durch NDA1 mit der Agentur für Projekt B
gedeckt"* — eine Feststellung mit `responsibility: {jens, direct}`, mit Datum
und Begründung.

Die Aufzählung ist Komfort, nicht Fundament. **Hätte das Gate sie gebraucht,
hänge die gesamte Offenlegungsprüfung am schwächsten Adapter.** Wo GitLab die
Mitgliederliste hergibt, wird nachgeprüft; wo JIRA zickt, fällt nur die
Prüfung aus und das Gate steht weiter.

#### Vier Zustände, mit sicherer Fehlerrichtung

| Zustand | Bedeutung | Folge beim Rendern |
|---|---|---|
| `declared` | Deckung ist angegeben | gedeckt → rendern |
| `confirmed` | Aufzählung passt zur Deckung | rendern |
| `divergent` | Aufzählung zeigt mehr als gedeckt | Warnung in die Queue, Rendern braucht Einzelfreigabe |
| `unknown` | keine Erklärung, keine Aufzählung | **gilt als weiter als erlaubt** → blockiert, bis erklärt |

Die Fehlerrichtung ist bewusst asymmetrisch: für ein **Ja** braucht es
Vollständigkeit (ein übersehenes Mitglied ist ein Leck), für ein **Nein**
genügt ein einziger Ungedeckter. Unwissen kippt daher immer auf Nein — das ist
Leitsatz 9 mit Vorzeichen.

#### Rendern in ein fremdes System ist unumkehrbar

Mitgliedschaften wachsen. Tritt später jemand der Partnergruppe bei, sieht die
Person Inhalte, die vorher dort hinterlassen wurden. Das fremde System wird
nicht kontrolliert, und kein Gate fängt das nachträglich ein.

Verhindern geht nicht. Bemerken geht: periodisch neu aufzählen und melden, wenn
das Publikum **gewachsen** ist und der Zuwachs nicht gedeckt ist — dasselbe
Muster wie die Vereinbarungslücken-Meldung unten.

#### Was das System nicht kann — und was es stattdessen tut

Sitzt jemand von der Agentur in einer Besprechung zu einem Projekt, für das
keine Vereinbarung vorliegt, dann *findet* die Offenlegung statt, in der
Wirklichkeit, außerhalb des Systems. Kein Programm verhindert das.

Aber es kann es **bemerken**: eine Projektion über Beteiligung × Vereinbarung
meldet *"diese Besprechung hatte Teilnehmer ohne deckende Vereinbarung"*. Kostet
nichts, weil beide Seiten ohnehin im Modell sind — und ist für ein
Beratungsunternehmen vermutlich eine der nützlicheren Warnungen überhaupt. Es
verhindert die Lücke nicht, es zeigt sie.

## 8. Zuordnung: drei Signalklassen, Modell zuletzt

Welcher Organisation, welchem Projekt und welchem Vorgang ein Abschnitt
gehört, wird aus drei Signalklassen bestimmt — in dieser Reihenfolge, weil sie
nach Kosten und Verlässlichkeit geordnet ist:

| Signal | Kosten | Beispiel |
|---|---|---|
| **strukturell** | keine | Beteiligte, Thread-Header, Referenzen |
| **zeitlich** | keine | eine Mail am Tag nach der Besprechung zu Thema X |
| **inhaltlich** | Modellaufruf | das Modell liest den Abschnitt |

Reicht keine der drei, geht es in die **Triage** (§8.4) — nicht als Fehlerfall,
sondern als vorgesehene Betriebsart.

### 8.1 Strukturelle Signale: die Beteiligtenregel

Die Grundidee: **schneide die Projekt-Beteiligungen der Anwesenden.** Bleibt
genau eines übrig, ist es das.

```
Discord #general, 10:00–10:45
  anwesend: Jens, Alex, [Ansprechpartner Organisation A]
  → Schnittmenge der Projekt-Beteiligungen: { Projekt A }
  → assignment: Projekt A · author: rule · confidence: hoch

Discord #general, 11:00–12:00
  anwesend: Jens, Alex, [Ansprechpartner Org. B], [Ansprechpartner Org. B]
  → Schnittmenge: { Projekt B }
  → assignment: Projekt B · author: rule · confidence: hoch
```

Derselbe Raum, dieselbe Person Alex, zwei Projekte. Alex trägt zur
Unterscheidung nichts bei; die projektspezifisch Beteiligten tragen alles.

Der allgemeine Satz dahinter: **Unterscheidungskraft ist umgekehrt proportional
zur Zahl der Projekte, in denen ein Akteur beteiligt ist.** Wer in genau einem
Projekt steckt, identifiziert es eindeutig; wer in zehn steckt, trägt fast
nichts bei. Das gilt für Personen **und Organisationen** — die Absenderdomäne
einer Hostingfirma, die nur in einem Projekt vorkommt, identifiziert es sofort.

Deterministisch, auditierbar, kostenlos, und kein Modell kann es falsch machen.
Gilt überall: bei Mail der Empfängerkreis einschließlich CC (oft ein besserer
Hinweis als der Betreff), bei Voice die erkannten Sprecher, bei Chat die
Anwesenden im Zeitfenster.

**Folge: Der Identitätsgraph ist nicht Hausarbeit, er ist der Klassifikator.**

#### Die Schnittmenge muss Ausreißer überleben

Eine naive Schnittmenge ist zu zerbrechlich. Zwei Fälle, die beide eintreten
werden:

- Jemand kommt **zu spät** — die Beteiligtenmenge ändert sich innerhalb des Events.
- Jemand **platzt herein**, gehört nicht dazu und verabschiedet sich wieder. Dessen
  Beteiligungen sind zu allen anderen disjunkt, und eine strenge Schnittmenge
  wäre **leer** — die Regel fällt durch eine Person aus, die neunzig Sekunden im
  Raum war.

Daher gilt nicht die rohe Schnittmenge, sondern: **Schnittmenge über die
verlässlich Beteiligten, nach Anwesenheitsdauer gewichtet.** Wer zwei von
neunzig Minuten anwesend war, ist kein Teilnehmer des Themas. Und ein Akteur
ohne bekannte Beteiligungen trägt **nichts** bei, statt alles zu zerstören —
das ist der entscheidende Unterschied.

**Die Regel läuft pro Zeitfenster beziehungsweise pro Einheit, nicht pro
Event**, und ist damit mit der Zerlegung (§5.3) verschränkt: ein Themenwechsel
und ein Teilnehmerwechsel sind oft dasselbe Ereignis.

#### Dasselbe Vorkommnis: Rauschen hier, Signal dort

Wer kurz hereinplatzt und nicht dazugehört, ist für die Zuordnung Störung — und
genau der Fall, den die Vereinbarungslücken-Meldung aus §7.2 finden soll. Für
die eine Frage wird er ignoriert, für die andere ist er das Interessanteste am
ganzen Gespräch. Beides aus derselben Datenlage.

#### Leere Schnittmenge ist eine eigene Aussage

Null übrige Projekte heißt **nicht** "keine Antwort", sondern **"unsere
Beteiligungsdaten sind unvollständig"**. Das ist ein anderer Befund mit anderer
Folge: er erzeugt eine Triage-Rückfrage über die *Beteiligung*, nicht über die
Zuordnung — und deren Antwort hat große Hebelwirkung (§8.4).

#### Kaltstart — die Regel ist kein Tag-eins-Mechanismus

Die Beteiligtenregel braucht Beteiligungen, und die entstehen erst, nachdem
Zuordnung eine Weile gelaufen ist. **Beim Bestandsimport ist die Schnittmenge
meist leer oder nutzlos.**

Das ist keine Schwäche der Regel, aber eine harte Vorgabe für die Phasierung:

- Am Anfang tragen **zeitliche und inhaltliche Signale plus Triage** die Last.
- Beteiligungen werden anfangs selbst vorgeschlagen — aus Mail-Kopfzeilen, aus
  dem gemeinsamen Vorkommen in Verteilern, aus den manuellen Einwürfen, bei denen
  Jens die Zuordnung ohnehin mitgibt.
- Die Regel wird **stärker, je länger das System läuft**, und ist nach dem
  Bestandsimport eines Projekts für dieses Projekt brauchbar.

*Einschränkung bei Chat:* Für Voice-Räume ist Anwesenheit pro Zeitfenster exakt
(Join/Leave). Für Text-Kanäle gibt es keine Anwesenheit — dort gilt "wer hat im
Zeitfenster geschrieben", schwächer aber brauchbar, und stille Mitleser sind
unsichtbar (für die Offenlegungsprüfung relevant, nicht für die Zuordnung).

### 8.2 Zeitliche Signale

Zeitliche Nähe zu bereits zugeordneten Events ist eine reine Datenbankabfrage
und kostet keinen Token — und sie trägt mehr, als sie klingt, weil Projektarbeit
in Schüben läuft: nach einer Besprechung kommen die Mails zu dieser Besprechung.

Verwendbar als eigenständiger Hinweis (eine Mail am Tag nach dem Call zu Thema
X ist vermutlich zu X) und als **Verstärker**, wenn strukturelle Signale mehrere
Kandidaten übrig lassen. Die zeitliche Spur zahlt auf `confidence` ein, nicht
auf Gewissheit — sie kann immer irren.

### 8.3 Inhaltliche Signale: Zerlegung durch das Modell

Erst wenn Struktur und Zeit nicht entscheiden, oder wenn ein Event mehrere
Vorgänge betrifft.

Eine Mail enthält selten genau ein Thema; ein zweistündiges Transkript enthält
viele. Das Modell gibt Zuordnungs-Feststellungen über Einheitenmengen aus,
verteilt und überlappend erlaubt (§5.3).

**Das ist die wertvollste Modelloperation im System.** Ein Transkript ist als
Klumpen wertlos und als zwölf Abschnitte auf fünf Vorgänge verteilt brauchbar.
Dort wird der Dschungel gelichtet.

Kosten: ein 2-Stunden-Transkript sind ~30.000 Tokens, ein Aufruf pro
Besprechung. Bei Mails ist ein billiger Vorlauf denkbar, der "ein Thema"
erkennt und die Zerlegung überspringt — **ob das die Mehrheit ist, ist eine
unbelegte Annahme und am Bestand zu messen, bevor darauf optimiert wird.**

### 8.4 Triage: wenn alle drei Signalklassen nicht reichen

Mail sauber zu kategorisieren ist schwierig, und eine vollständige
Automatisierung ist nicht in Sicht. Daraus folgt nicht ein Fehlerpfad, sondern
eine **eigene Betriebsart**: das System fragt, und zwar konkret.

#### Zwei Arten von Queue-Einträgen, zwei Oberflächen

| | Freigabe (§10.3) | Rückfrage (Triage) |
|---|---|---|
| Frage | "Darf ich X tun?" | "Ich kann Y nicht entscheiden — was ist es?" |
| geht um | Befugnis | **Wissen** |
| Antworten heißt | autorisieren | die Lücke füllen |
| braucht | sorgfältiges Lesen | **einen Tastendruck** |

Beides in eine Liste zu werfen schadet beidem: eine Freigabe will gelesen
werden, eine Rückfrage will in drei Sekunden beantwortet sein.

#### Der Hebel liegt im Wert der Antwort, nicht in der Zahl der Fragen

**Rückfragen werden nach Hebelwirkung sortiert, nicht nach Alter.** Zuerst
gefragt wird, was am meisten auflöst.

Beantwortet jemand *"Alex in diesem Gespräch ist Alex Berger von der
Agentur"*, ist nicht ein Gespräch zugeordnet — es ist eine Kanalidentität an
eine Person gebunden, und daran können vierzig unentschiedene Events hängen.
Eine einzelne Mail zuzuordnen löst eine Mail.

Die Hebelwirkung ist abschätzbar: wie viele offene Zuordnungen hängen an dieser
einen Antwort? Und sie ist messbar — **beantwortete Fragen pro Woche ×
durchschnittlich aufgelöste Posten pro Antwort.** Damit gibt es eine Zahl dafür,
ob die Triage besser wird oder nur fleissiger.

#### Was eine gute Rückfrage ausmacht

- **Kandidaten statt leerem Feld.** "Alex Berger (Agentur) oder Alex Winter
  (Auftraggeber)?" — nicht "wer ist Alex?"
- **Aus einer Vermutung abgeleitet, mit Beleg.** Einheitenverweis dabei, damit
  im Zweifel nachgelesen werden kann.
- **Aufschiebbar** (§6.4) — eine Rückfrage blockiert nichts.
- **Vorzugsweise über Struktur, nicht über Inhalt.** Eine Frage nach einer
  Identität oder einer Beteiligung wirkt dauerhaft; eine Frage nach der
  Zuordnung eines einzelnen Abschnitts wirkt einmal.

### 8.5 Messbarkeit fällt gratis an — bei sauberem Filter und pro Einheit

Beim manuellen Einwurf gibt Jens die Zuordnung mit, also entsteht
**Grundwahrheit**. Ebenso bei jeder beantworteten Rückfrage.

**Verglichen wird pro Einheit, nicht pro Feststellung.** Das Modell sagt
Einheiten 3–4, Jens sagt 3–5 — bei Mengengleichheit als Bedingung gäbe es fast
nie einen Vergleich und die Messbarkeit wäre auf dem Papier schön und praktisch
leer. Auf Einheitenebene ergibt dieselbe Lage drei Datenpunkte: 3 richtig, 4
richtig, 5 übersehen. Daraus Genauigkeit und Vollständigkeit, wie üblich.

**Der Filter läuft auf `author`, nicht auf `responsibility`.** Legt ein Agent
auf Jens' Anweisung etwas an, ist das `responsibility: {jens, transitive}`, aber
`author: model`. Würde die Messung auf `responsibility` filtern, verglich man
das Modell mit sich selbst und bekäme eine geschmeichelte Trefferquote.

Ebenso ausgeschlossen: `author: unknown`. Eine kleinere, ehrliche Messbasis
ist mehr wert als eine große mit Modelloutput darin.

## 9. Projektionen

Jeder Zustand wird aus dem Event-Log berechnet und ist jederzeit neu
berechenbar — auf jeden Stichtag, in beiden Zeitordnungen.

### 9.1 Die Protokollfamilie

**Eine Maschine, drei Zuschnitte:** Organisationsprotokoll, Projektprotokoll,
Vorgangsprotokoll. Das Organisationsprotokoll ist dabei nützlicher als ein
"Kundenprotokoll" wäre: "alles mit Mirko" über alle Projekte und alle Rollen
hinweg — nach Rolle filterbar, aber nicht nach Rolle zerschnitten. Der Vorgang bekommt seine Ansicht dadurch gratis.

```
ORGANISATION <name> — Stand 1. Oktober 2026
Rollen: Auftraggeber (Projekt X), ARGE-Partner (Projekt Y)

Wir schulden           3 Verpflichtungen, davon 1 overdue
Uns wird geschuldet    2 Verpflichtungen, 1 unbeanswerete Frage (4 Monate)
Beobachtet             1 overdue zwischen Dritten, blockiert uns
Letzte Entscheidungen  3

── Chronik (Ereigniszeit) ──────────────────────────────
2024-03-14  Kickoff-Call. Entscheidung: Datenmodell
            nach Variante B.                  [T-0231 ¶12, M-0442 ¶3]
2024-03-18  Kunde sagt Messdaten bis Ende März zu.    [M-0455 ¶3,7]
```

Der Kopf ist keine Zusammenfassung, sondern eine Abfrage über Verpflichtungen
und Fragen. Jede Zeile trägt Event-IDs und Einheitennummern — stabil,
nachprüfbar, klickbar.

**Feststellungen stehen in einer Arbeitssprache (Deutsch), Quellen in
Originalsprache.** Ergibt eine englische Mail eine Verpflichtung, ist deren
Text deutsch; der zitierte Wortlaut bleibt unübersetzt. Sonst wird das
Protokoll ein Sprachsalat und als Dokument wertlos. Es braucht dafür nichts
Neues: die `sources` zeigen auf die englischen Einheiten, und ein Klick führt
zum Originalsatz.

**Das Protokoll ist keine gepflegte Datei.** Es wird nie nachgeführt und ist
deshalb nie veraltet. Eine Korrektur daran ist eine Feststellung mit
`responsibility: {jens, direct}`: sie überschreibt die Quelle nicht, tritt
daneben und
gewinnt in der Projektion.

### 9.2 Audit-Sicht

Dieselben Daten, anderer Zuschnitt: Handlungen plus die Feststellungen, die
sie begründet haben, plus jeder Modellaufruf, der dazu geführt hat.

**Audit-Log und Wissensspeicher sind dasselbe Ding.** Keine zwei Systeme, die
auseinanderlaufen können.

---

## 10. KI-Layer

### 10.1 Das Gate — und der zweite Durchsetzungspunkt

Eine Stelle, durch die jeder Modellaufruf **des Systems** geht. Kein
SDK-Aufruf in der Fläche.

**Wichtige Einschränkung:** Das Gate kann Claude Code nicht kontrollieren.
Wenn Jens interaktiv arbeitet, ruft Claude Code Anthropic mit *seinen*
Zugangsdaten auf — das Gate sieht davon nichts. Es gibt daher **zwei**
Durchsetzungspunkte:

| | Gate | MCP-Server |
|---|---|---|
| kontrolliert | Aufrufe, die *das System* macht | welche Daten die interaktive Seite überhaupt bekommt |
| Mechanismus | Anbieter/Modell wählen oder ablehnen | Herausgabe verweigern oder auf Metadaten reduzieren |

Beide schreiben in dasselbe Audit-Log. "Was hat Claude je über Kunde X
gesehen?" wird aus dem **MCP-Zugriffsprotokoll** beantwortet, nicht aus dem
Gate-Log.

**Konsequenz:** Steht eine beteiligte Organisation auf `local_only`, verweigert
der MCP-Server die Inhalte des betroffenen Projekts an Claude Code — das Cockpit
würde für dieses Projekt stumpf (strukturierte Abfragen ja, KI-Unterstützung
nein).

**Das ist lösbar, nicht hinzunehmen.** Weil das Cockpit nur ein MCP-Client ist
(§4), genügt für solche Projekte ein **anbieterneutraler Client gegen ein
lokales Modell** — der Weg ist in §8.8 des Architektur-Specs benannt. Die
Datenpolitik kostet dann Modellstärke, nicht die Arbeitsweise.

```
call(task, payload, context{project, confidentiality}) → result
```

**`confidentiality` ist nicht dasselbe wie Zuordnung** und hat deshalb einen
eigenen Namen. Sie kommt aus zwei Quellen, in dieser Reihenfolge: der
aufgelösten `data_policy` des Projekts (§7.1) als Vorgabe, und optional einer
Feststellung
`kind: confidentiality` über einzelne Einheiten, wenn ein Abschnitt sensibler
ist als die Projektvorgabe (Gehaltsdaten, Vertragsentwurf, Personensache).
Die strengere der beiden gewinnt.

Das Gate entscheidet Anbieter und Modell für diese Nutzlast daraus. Heute gibt
es für alle Projekte "Cloud erlaubt" zurück; später steht dort die aufgelöste
Regel des Projekts. Ein Modul, keine
Umbaumaßnahme.

**Damit zu rechnen:** Die Policy-Schicht enthält im ersten Jahr echte Regeln.
Ein Kunde, der seine Entwicklungsumgebung selbst hostet, hat das aus einem
Grund getan.

#### Der Verarbeitungsraum ist belegbar, nicht nur versprochen

Die Claude-API nimmt einen Parameter für den Verarbeitungsraum, und **die
Antwort meldet zurück, wo tatsächlich gerechnet wurde** (`usage.inference_geo`).
Welche Räume wählbar sind, ist beim Bau nachzusehen.

Damit wird aus einer Vertragszusage ein Audit-Eintrag: das Gate setzt den Raum
aus der aufgelösten `data_policy`, liest aus der Antwort, wo gerechnet wurde,
und schreibt es mit. Einem Auftraggeber gegenüber lässt sich dann nicht nur
sagen "wir verarbeiten in der EU", sondern es **pro Aufruf belegen** — und eine
Abweichung zwischen gesetztem und gemeldetem Raum ist ein Alarm, kein
Schulterzucken.

Dasselbe Gate protokolliert: Zeitpunkt, Aufgabe, Datenreferenzen (keine
Kopien), Modell, Prompt-Version, **gesetzter und gemeldeter Verarbeitungsraum**,
Ergebnis, Kosten. **Das Audit-Log ist ein
Nebenprodukt der Policy-Schicht, kein Extra-Projekt.**

Zwei Adapter genügen: Anthropic-SDK und OpenAI-kompatibel. Letzteres deckt
OpenRouter, Ollama und llama.cpp ab.

### 10.2 Modellzuweisung

| Aufgabe | Motor | Begründung |
|---|---|---|
| Zuordnung, Zerlegung, Extraktion | Haiku 4.5, über Batch API wo möglich | Masse, nicht zeitkritisch, 50 % Rabatt |
| Bestandsimport | Haiku 4.5 + Batch API | nichts davon ist zeitkritisch |
| Interaktive Arbeit, Entwürfe | Claude Code über Max-Plan | deckt den teuren Teil ab |
| Embeddings | **lokal, immer** | siehe unten |
| Open-Weight-Vergleiche | OpenRouter | messen statt Hardware kaufen |

**Das Embedding-Modell muss mehrsprachig sein.** Harte Auswahlbedingung, nicht
Komfort: ein mehrsprachiges Modell bettet "fishing rights" und "Vergaberecht"
in dieselbe Nachbarschaft ein, ein einsprachig deutsches nicht — und dann
findet eine deutsche Suche die englische Spezifikation nicht. **Im gemischten
Fall verdienen die Embeddings ihr Geld am meisten**, weil die Volltextsuche
dort sprachgetrennt und spröde ist, während Embeddings von Bauart her
sprachübergreifend arbeiten (§12).

**Embeddings bleiben lokal, ohne Ausnahme.** Nicht aus Kostengründen:
Embedding ist der einzige Schritt, bei dem *jeder einzelne Inhalt
vollständig* das Haus verlässt — das schlechteste Verhältnis von Nutzen zu
Exposition im ganzen System. Und bei einem späteren Wechsel auf
"alles lokal" muss die Historie nicht neu eingebettet werden.

**Der Max-Plan deckt den interaktiven Teil ab, nicht die Pipeline.** Seine
Grenzen sind nicht als Dauerlast ausgelegt, und ein Hintergrundprozess, der
mittags das Limit reißt, macht das Arbeitsgerät unbrauchbar. Token-Abgriff aus
Claude Code als API ist ausgeschlossen: Verstoß gegen die
Nutzungsbedingungen, bricht bei jedem Refresh.

Erwartete Gesamtkosten bei etwa 150 Mails pro Tag und zwei Stunden
transkribierten Gesprächen: **10 bis 50 USD pro Monat.**

### 10.3 Templates und Freigabeklassen

Jede vorgeschlagene Aktion erhält eine **Aktionsklasse**: was × wo × mit
welchem Template. Pro Klasse ein Zustand: `fragen` (Vorgabe für alles Neue),
`auto` (optional mit Hinweis danach), `nie`.

**Die Dauerfreigabe wird aus der Freigabe-Queue heraus erteilt.** Beim
Abnehmen stehen "einmal" und "diese Klasse ab jetzt" nebeneinander. Der
Regelsatz lagert sich aus echten Entscheidungen ab; niemand setzt sich hin,
um Berechtigungen zu konfigurieren.

**Die Queue hat zwei Arten von Einträgen** — Freigaben und Rückfragen (§8.4) —
und sie gehören in **getrennte Oberflächen**. Eine Freigabe will gelesen werden,
eine Rückfrage will in drei Sekunden beantwortet sein. In einer Liste vermischt
leidet beides: die Freigaben werden überflogen, die Rückfragen liegen.

### 10.4 Ablehnung wird festgehalten, nicht nur Annahme

Lehnt Jens einen Vorschlag ab, ist **das Nein selbst eine Feststellung** mit
`responsibility: {jens, direct}` — etwa *"diese zwei Vorgänge sind absichtlich
getrennt"* oder *"diese Aussage ist keine Verpflichtung"*. Der nächste Durchlauf
sieht sie und schlägt dasselbe nicht erneut vor.

**Ohne das fragt das System endlos nach.** Die Vorrangordnung (§5.2) verhindert, dass ein
Modell gegen eine menschliche Entscheidung *gewinnt* — aber nicht, dass es
dieselbe Frage bei jedem Durchlauf neu stellt. Eine Queue, in der immer die
gleichen abgelehnten Vorschläge liegen, schaut sich nach drei Wochen niemand
mehr an, und dann ist die gesamte Freigabe-Mechanik wertlos — einschließlich
der Dauerfreigaben, die aus ihr entstehen sollen.

Eine Ablehnung gilt für die **konkrete Aussage über dieselben Einheiten**, nicht
pauschal für eine Art von Vorschlag; ändert sich die Eingangsmenge, darf erneut
vorgeschlagen werden.

Risiko-Ordnung, die bestimmt, was wann automatisierbar wird:

| | strukturiert | freie Prosa |
|---|---|---|
| **intern** | Aufgabe im eigenen System, Dokument in eigener Ablage → früh automatisierbar | Protokoll-Entwurf → Freigabe |
| **extern** | Empfangsbestätigung, Terminvorschlag, **Issue im Partner-System** → enge Automatisierung, Deckung vorausgesetzt | Mail nach außen → **immer Freigabe** |

> **`intern` und `extern` heißt nicht "unser Werkzeug" gegen "Mail", sondern
> unser Publikum gegen fremdes Publikum.**

Das ist eine Korrektur gegenüber einer früheren Fassung, die "GitLab Issue" als
besten Automatisierungskandidaten nannte — im Blick war dabei das *eigene*
GitLab. Ein Issue im GitLab eines Partners ist eine externe, unumkehrbare
Offenlegung an ein fremdes Publikum (§7.2). Strukturiert ja, aber die Struktur
schützt hier nichts: sie begrenzt, *was* gesagt wird, nicht *wer es liest*.

---

## 11. Konnektoren

### 11.1 Der Vertrag

Ein Konnektor ist nichts Besonderes: **Renderer** in die eine Richtung,
**Event-Quelle** in die andere. Dieselbe Mechanik wie beim Protokoll — ein
Work Item ist eine Projektion, gerendert als Work Item.

Dadurch verschwindet das Sync-Problem: eine Änderung direkt im Fremdsystem
kommt als Feststellung mit `responsibility: <person>` herein, die Wahrheit im Kern
aktualisiert sich, und das nächste Rendern ist ein No-Op. **Die Idempotenz des
Renderns ist dabei eine Konvergenzbedingung, keine Bequemlichkeit** — siehe
§5.5. Kein Konfliktdialog,
keine Sync-Richtung.

**Weil der Kern die Wahrheit hält, darf Rendern verlustbehaftet sein.** Eine
"Verpflichtung mit Frist" landet in einem schwachen Zielsystem als Issue mit
Label, die Nuance bleibt im Kern. Deshalb ist eine heterogene
Kundenlandschaft überlebbar.

### 11.2 Fähigkeitsstufen

| Stufe | Beispiel | Was geht | Publikum |
|---|---|---|---|
| beidseitig | eigenes OpenProject, Kunden-GitLab mit API-Key | Events rein, Rendern raus | zu erfassen |
| nur lesend | API-Key ohne Schreibrechte | Events rein | — |
| keine API | Kunde will nicht, Altsystem, Freigabe dauert | siehe 11.3 | — |

**Zielorte statt Systeme.** Die Rendern-Richtung zeigt nie auf ein System,
sondern auf einen **Zielort** darin — ein GitLab-Projekt, eine Gruppe, einen
Ordner. Jeder Zielort trägt seine **Deckung** (welche Vereinbarung ihn deckt)
und seinen **Publikumszustand** (`declared | confirmed | divergent | unknown`).
Siehe §7.2 — Berechtigungsmodelle der Zielsysteme werden ausdrücklich **nicht**
nachgebildet.

### 11.3 IMAP ist das Auffangbecken

Fast jedes System der Welt schickt Benachrichtigungsmails. Ein Kundensystem
ohne API-Zugriff redet trotzdem mit uns: seine Ereignisse kommen als Mail und
sind damit im Kern. Nicht elegant, aber vollständig genug für Verlauf und
Protokoll.

Das verschiebt den Aufwand für die vielen Einzelsysteme von "N Integrationen"
auf "N Mail-Parser". **Folge: Der Mail-Konnektor ist nicht eine Inbox von vielen,
sondern das Auffangbecken für alles Nicht-Integrierbare — und muss
entsprechend gut sein.**

### 11.4 Der manuelle Einwurf ist der Referenz-Konnektor

| Pfad | Zuordnung | Anmerkung |
|---|---|---|
| **IMAP** | geraten | automatisch, kontinuierlich |
| **Drop-Ordner** | Unterordner = Organisation | ein Nextcloud-Ordner: funktioniert auch vom Telefon |
| **Einwurf per Prompt** | Jens sagt sie | `evidence: recollection`. Hier landet später die Spracheingabe — derselbe Pfad, anderes Eingabegerät |
| **Quelle verlinken** | Jens sagt sie | GitLab-/GitHub-Issue-URL; wird geholt und nachgehalten |

**Der Prompt-Pfad ist der qualitativ beste, nicht der Notausgang.** Er kann
etwas, was weder Formular noch Drop-Ordner kann: **beim Einwurf nachfragen** —
"Welches Projekt?", "Hat er ein Datum genannt?", "Zusage oder
Absichtserklärung?" — und zwar während die Erinnerung frisch ist. Bei
Telefonaten ist er auch dauerhaft der einzige Weg: ein Handy-Anruf läuft nie
durch die PipeWire-Pipeline, Teil 2 deckt das nie ab.

Suboptimal ist er nur dort, wo ein Konnektor dasselbe holen könnte — nicht
wegen des Aufwands, sondern weil die Quelle dann `verbatim` wäre und die
Zusammenfassung davon `recollection`.

Diese Pfade decken ab Tag eins jede Quelle ab, ohne Token, Kundenfreigabe
oder Wartezyklus. **Deshalb sind sie zuerst zu bauen:** jeder automatische
Konnektor ist danach die Automatisierung eines Pfades, der schon funktioniert.
In der umgekehrten Reihenfolge entsteht ein Vertrag, der nach Mail aussieht.

Drop-Ordner braucht Textextraktion und bei Scans OCR — lokal, kostenlos.

### 11.5 JIRA und ähnliche

Technisch unproblematisch (Cloud: Mail + API-Token; Data Center: Personal
Access Token). Das Problem ist organisatorisch: der Token hängt an einem
Benutzerkonto mit dessen Rechten, der Kunden-Admin muss Token-Erstellung
erlauben, und das Feldmodell mit Custom-Field-IDs ist beim Abbilden
unangenehm. Also schwieriger zu *bekommen*, nicht zu bauen — eine
Freigabefrage an den Kunden, kein Entwicklungsrisiko.

---

## 12. Speicher-Adapter

Der Kern kennt keine Datenbank. Die Produktentscheidung ist "append-only
Event-Log, Projektionen, Vektorsuche" — eine Form, kein Hersteller.

**Was festgelegt ist, ist die Disziplin, nicht die Engine.** Ist das Log
append-only mit zwei Zeitstempeln und Hash-Kette, und sind alle Projektionen
neu berechenbar, dann ist ein Engine-Wechsel ein Re-Import.

**Nicht spekulativ zwei Backends bauen** — das endet beim kleinsten
gemeinsamen Nenner. Ein Backend, hinter einer schmalen Schnittstelle, und die
Schmalheit wird verteidigt.

### 12.1 Vorbemerkung: das Datenvolumen ist klein

Bei 150 Mails pro Tag über fünf Jahre rund 275.000 Mails; mit Transkripten und
Chats einstellige Millionen Events und zweistellige Gigabytes Text. Eine
Maschine. Deshalb entscheiden nicht Durchsatzfragen, sondern die drei Kriterien
unten.

### 12.2 Rechercheergebnis (Oktober 2026)

**Empfehlung: PostgreSQL mit pgvector** — eine Datenbank für Event-Log,
Projektionen und Vektoren.

#### Vektorsuche mit Vorfilter — gelöst

Das alte Problem: der Vektorindex holt k nächste Nachbarn, *danach* filtert die
`WHERE`-Klausel — verwirft der Filter die meisten, bekommt man drei Treffer statt
dreißig und merkt es nicht.

**pgvector 0.8 hat iterative Indexscans**: der Index wird weitergescannt, bis
genug Treffer übrig sind. Und für **stark selektive Filter** (unter etwa 10.000
Zeilen) gibt es den besseren Weg: ein B-Tree-Index auf der Filterspalte, dann
filtert Postgres *vor* der Vektorsuche. "Nur Projekt X, nur vor dem 14. März"
ist genau das — ein Projekt hat tausende, nicht Millionen Events. Also der
günstige Fall, nicht der Problemfall.

#### Textsuche: zwei unabhängige Achsen, nicht eine Entscheidung

Der häufigste Denkfehler hier — und eine frühere Fassung dieses Abschnitts hat
ihn gemacht — ist, Tokenisierung und Rangfolge als *eine* Wahl zu behandeln. Es
sind zwei:

| Achse | Optionen |
|---|---|
| **lexikalische Analyse** | Snowball deutsch · Hunspell-Wörterbuch · Subword-Modell |
| **Index und Rangfolge** | `tsvector` + `ts_rank` · BM25 (`vchord_bm25`) |

Frei kombinierbar. "Hunspell **oder** BM25" ist eine Scheinalternative.

#### Die lexikalische Achse: Komposita

| Analyse | Komposita | zweites System? |
|---|---|---|
| Snowball (`german`) | **nein** — "Vergaberecht" findet "Recht der Vergabe" nicht | nein |
| Hunspell-Wörterbuch | **teilweise** — Postgres setzt nur die Grundfunktionen der Hunspell-Kompositalogik um | nein |
| Subword-Modell | **umgeht sie** — statistische Teilstücke statt Wörterbuch, sprachneutral | nein |
| Lucene-Zerleger (OpenSearch) | **ja** — `hyphenation_decompounder` (empfohlen) und `dictionary_decompounder`, mit fertigen deutschen Datensätzen | **ja** |

Ehrliche Einordnung der beiden mittleren Wege: ein anderer Kompromiss, keine
strikte Verbesserung gegeneinander.

| | Teilstücke | Stärke | Schwäche |
|---|---|---|---|
| Hunspell | linguistisch korrekt | hohe Genauigkeit | nur teilweise umgesetzt, pro Sprache zu konfigurieren |
| Subword | statistisch gelernt | sprachneutral, hohe Trefferquote | kurze Teilstücke erzeugen Falschtreffer; IDF dämpft das, hebt es nicht auf |

#### Die Werkzeuge auf der Postgres-Seite

**`vchord_bm25` (VectorChord-BM25) ist sprachneutral.** Es liefert
BM25-Indexierung und -Rangfolge, sonst nichts. Tokenisierung ist Sache der
eigenständigen Erweiterung **`pg_tokenizer.rs`**, und die bietet zwei Wege:

**Text-Analyzer** (klassische Kette): Zeichenfilter → Vor-Tokenizer (`regex`,
`unicode_segmentation`, `jieba`) → Token-Filter. Unter den Token-Filtern:
Snowball-Stemmer für 23 Sprachen **einschließlich Deutsch**, Stoppwörter,
Synonyme — und **`pg_dict`, eine Integration von Postgres-Wörterbüchern.**

> Damit lässt sich das deutsche **Hunspell-Wörterbuch in die BM25-Kette
> hängen** — linguistisch korrekte Kompositazerlegung *und* BM25-Rangfolge
> statt eines von beidem. Vermutlich der stärkste Kandidat überhaupt. Laut
> Dokumentation möglich; beim Bau zu verifizieren.

**Modell** (Subword): ein vortrainierter Tokenizer. Die Dokumentation zeigt
BERT für Englisch, `jieba` für Chinesisch, `lindera` für Japanisch und benennt
für Mehrsprachigkeit ausdrücklich `gemma2b` oder `llmlingua2`.

**Stoppwörter und Synonyme sind benutzerdefiniert** (`create_stopwords()`,
`create_synonym()`), keine mitgelieferten Sätze — für Deutsch also selbst
anzulegen.

*Versionsnummern stehen hier absichtlich nicht: sie veralten schneller als
dieses Dokument, und die drei Erweiterungen (VectorChord als Vektorindex,
`vchord_bm25`, `pg_tokenizer.rs`) zählen getrennt. Beim Bau nachsehen.*

**ParadeDB / `pg_search`** (BM25 auf Tantivy) ist der dritte Postgres-Weg: hat
deutsches Stemming nach Snowball, aber kein Hinweis auf Kompositazerlegung
gefunden. Damit für dieses Problem ohne Vorteil gegenüber den beiden oben.

#### Warum das trotzdem kein Grund ist, Postgres zu verwerfen

**Erstens: die Embeddings tragen den Paraphrasen-Fall.** Lokale Embeddings sind
ohnehin Pflicht (§10.2), und "Vergaberecht" ≈ "Recht der Vergabe" ist genau,
was semantische Suche kann. Die Volltextsuche muss die Umschreibung nicht
leisten — sie muss **wörtliche** Treffer sicher liefern: Namen, Rechnungsnummern,
Zitate. Dafür genügt Snowball.

**Zweitens, und wichtiger: der Suchindex ist kein Speicher-Entscheid.** Nach
Leitsatz 3 ist jeder Zustand eine Projektion — ein Suchindex ist ein Zustand und
damit **jederzeit aus dem Event-Log in eine beliebige Engine neu aufbaubar**.

> Die Wahl der Datenbank legt die Suche nicht fest. Zeigt sich später, dass die
> Kompositazerlegung wirklich weh tut, kommt ein OpenSearch-Index als
> **Zweitindex** daneben — ohne den Speicher anzufassen.

Das Kriterium, das am schwerwiegendsten aussah, hat damit die niedrigste
Bindungswirkung. Umgekehrt als erwartet.

#### Mehrsprachigkeit

Projekte enthalten deutsche **und** englische Texte. Volltextsuche ist in
Postgres sprachabhängig konfiguriert: `sprache` an der Einheit (§5.1), Index mit
der passenden Konfiguration, bei der Abfrage beide befragen und zusammenführen.
Billig und Standard.

Die `simple`-Konfiguration für alles ist **keine** Lösung — ohne Stemming
verliert man gerade bei deutschen Flexionsformen die halbe Trefferquote.

Englisch macht **beide** Optionen gleichermaßen aufwendiger (Postgres braucht
`german` und `english`, Lucene braucht zwei Analyzer) und verschiebt den
Vergleich daher nicht.

#### Reprojektion als Stream — unkritisch

Serverseitige Cursor, Standard. Die Schnittstelle muss es als Stream anbieten,
damit niemand alles in eine Liste lädt — eine Disziplinfrage, keine Engine-Frage.

### 12.3 Offener Messversuch

Die Kompositafrage wird mit Daten entschieden, nicht mit Meinung: tausend echte
Mails und Transkriptabschnitte, zwanzig Suchanfragen, die Jens wirklich tippen
würde — deutsche und englische — dann Trefferquote **und Genauigkeit** messen.

Weil die beiden Achsen unabhängig sind, ist es eine kleine Matrix und keine
Liste:

| | `tsvector` + `ts_rank` | BM25 (`vchord_bm25`) |
|---|---|---|
| Snowball deutsch | Grundlinie | — |
| Hunspell | Kandidat | **Kandidat, vermutlich der stärkste** |
| Subword, mehrsprachig | — | Kandidat |

Dazu zwei Vergleichspunkte außerhalb der Matrix: **nur Embeddings** als
Untergrenze, und die **Kombination** aus dem besten Textweg mit Embeddings als
erwartete Endgestalt.

Alle Kandidaten bleiben in Postgres. OpenSearch als Zweitindex steht nur noch
als Ausweichoption, falls die Matrix nichts Brauchbares hergibt.

**Vektoren bleiben pgvector** — bei einstelligen Millionen Events rechtfertigt
das Volumen nichts Exotisches, und pgvector ist in jedem Managed-Postgres
vorhanden. (VectorChord bietet auch einen Vektorindex; der Messversuch betrifft
nur die Textseite.)

Ein Tag Arbeit, und es steht fest, welcher Weg gilt.

### 12.4 Quellen

- [pgvector](https://github.com/pgvector/pgvector) · [Skalierung und Filterung](https://clickhouse.com/resources/engineering/scale-vector-search-postgres)
- [Postgres-Diskussion zu deutschen Komposita](https://www.postgresql.org/message-id/556C1411.4010608@tbz-pariv.de) · [Hunspell-Wörterbuch mit Kompositaunterstützung](https://github.com/vpikulik/hunspell_de_compounds)
- [ParadeDB Tokenizer](https://www.paradedb.com/docs/reference/tokenizers/overview) · [ParadeDB Stemmer](https://www.paradedb.com/docs/documentation/token-filters/stemming)
- [Elastic `dictionary_decompounder`](https://www.elastic.co/docs/reference/text-analysis/analysis-dict-decomp-tokenfilter) · [Kompositasuche](https://www.elastic.co/search-labs/blog/compound-word-search) · [deutsche Datensätze](https://github.com/uschindler/german-decompounder)
- [VectorChord-BM25](https://github.com/supervc-stack/VectorChord-bm25/blob/main/README.md) · [Hybridsuche mit BM25](https://blog.vectorchord.ai/hybrid-search-with-postgres-native-bm25-and-vectorchord) · [`pg_tokenizer.rs`](https://github.com/tensorchord/pg_tokenizer.rs) · [vchord_bm25 Übersicht](https://pigsty.io/ext/e/vchord_bm25/)

## 13. Bestandsimport

Der Pilotkunde ist seit längerem aktiv. Projektkontext muss importiert
werden, und das passiert bei jedem Onboarding erneut — **ein Vorgang des
Systems, kein Migrationsskript.**

**Import ist nicht Triage.** Der Import extrahiert und legt ab:
Verpflichtungen, Fristen, Entscheidungen landen im Kern, das Protokoll wird
vollständig. **Vorschläge** entstehen nur in einem eigenen, ausgelösten
Durchgang, der gebündelt durchgesehen wird. Zwei Jahre Mail durch die
Vorschlagsmaschine ergeben 500 veraltete Vorschläge, die niemand ansieht —
während "zeig mir, was aus der Historie noch offen ist" wertvoll ist.

**Der Import darf unsicher sein.** Zwei Jahre Historie bedeuten verschobene
Projektgrenzen, Umbenennungen, gewanderte Themen. Weil alles eine Projektion
ist, wird neu gerechnet, sobald die Struktur besser verstanden ist. **Der
Import muss nicht korrekt sein, nur vollständig.**

**Der erste Import ist die Abnahmeprüfung des Kernmodells.** Geht beim Import
von Projektkontext aus OpenProject etwas Wesentliches verloren, ist das
Kernmodell falsch, nicht der Import. Leitsatz 2 wird hier erstmals an echten
Daten geprüft.

Quellen sind genau die vier Einwurfpfade — Mailhistorie, bestehendes
OpenProject-Projekt, Issues per URL, Angebote und Protokolle als PDF.
Es braucht keine neue Maschinerie.

---

## 14. MVP-Abgrenzung

**Im MVP:**

- Teil 1: IMAP plus die drei manuellen Pfade
- Teil 3: Kern vollständig — Event-Log, Hash-Kette, neun Entitäten,
  Identitätsgraph, Projektionen, Protokollfamilie
- Teil 4: Gate, Policy, Audit, zweistufige Zuordnung, Zerlegung, Templates,
  Freigabeklassen
- MCP-Server als einzige Schnittstelle
- Bestandsimport für einen Pilotkunden

**Nicht im MVP, mit reserviertem Platz:**

- **Teil 2, Voice.** PipeWire-Abgriff, Transkription, Diarisation. Erste
  Aufgabe darin ist nicht der Abgriff, sondern **Einwilligung modellieren** —
  siehe §15.
- **Teil 5, eigene Oberfläche.** Im MVP ist die Oberfläche Claude Code über
  MCP: Einwurf, Freigabe-Queue auflisten, abnehmen, Protokoll rendern. Eine
  eigene Oberfläche kommt, wenn das nicht mehr reicht oder Kolleg:innen
  dazukommen.
- Weitere Konnektoren (Signal, Discord, Nextcloud, Kunden-JIRA).

Der MVP ist auch nach dieser Abgrenzung groß. Der Implementierungsplan wird in
Phasen zu schneiden sein, und §8.1 gibt dafür eine harte Vorgabe:

**Die Beteiligtenregel ist kein Tag-eins-Mechanismus.** Sie braucht
Beteiligungen, die erst entstehen, wenn Zuordnung schon läuft. Daraus folgt die
Reihenfolge:

1. **Kern, Einwurfpfade, Triage.** Ohne Triage ist am Anfang nichts zuzuordnen —
   sie ist die erste Betriebsart, nicht die letzte Ausbaustufe.
2. **Zeitliche und inhaltliche Signale.** Tragen die Last, solange der
   Identitätsgraph leer ist.
3. **Identitätsgraph und Beteiligtenregel.** Wächst aus (1) und (2) und wird
   rückwirkend auf die Historie angewandt — was dank Leitsatz 3 eine
   Neuberechnung ist und keine Migration.

Der Identitätsgraph bleibt das wertvollste Bauteil, aber er ist ein **Ergebnis**
der ersten Phasen, nicht deren Voraussetzung. Ihn zuerst bauen zu wollen wäre
der naheliegende und falsche Schnitt.

---

## 15. Abnahmebedingungen

Testbare Kriterien, keine Absichtserklärungen.

1. **Austauschbarkeit.** Eine leere OpenProject-Instanz wird aus dem Kern
   vollständig wiederhergestellt. Was dabei fehlt, benennt präzise die
   Bindung. **Als automatisierter Test, nicht als Vorsatz.**
2. **Reprojektion.** Jede Projektion wird aus dem Event-Log von Null neu
   berechnet und ergibt dasselbe Ergebnis.
3. **Kettenintegrität.** Eine Prüfung läuft über das gesamte Log und findet
   jede Manipulation.
4. **Quellenpflicht.** Keine Feststellung ohne `sources`. Durch Schema
   erzwungen, durch Test belegt.
5. **Stichtagsabfrage.** "Stand am Datum X" ist in beiden Zeitordnungen
   beantwortbar.
6. **Zuordnungsgüte.** Die Trefferquote von `author: rule` und
   `author: model` gegen `author: human` ist pro Abschnitt abfragbar — und
   die Abfrage schließt `unknown` sowie modellformulierte Einträge mit
   menschlicher Verantwortung aus.
7. **Gate-Dichte.** Kein Modellaufruf außerhalb des Gates. Statisch geprüft.
8. **Befugnis.** Keine Handlung ohne `instructed`, `once` oder `class:<id>`.
9. **Konvergenz.** Rendern, abfragen, erneut rendern erreicht einen Festpunkt
   innerhalb eines Umlaufs: die eigene Handlung erzeugt **keine** neue
   Wahrnehmung. Und die Gegenprobe, die genauso wichtig ist: eine *fremde*
   Änderung am Ziel erzeugt **genau eine** Wahrnehmung — die Schleife darf
   nicht so dicht gemacht werden, dass sie das Lernen mit abwürgt.
10. **Schwingungserkennung.** Eine künstlich konstruierte Zirkularität wird
   vom Wächter angehalten und landet in der Queue, statt unbemerkt zu laufen.
11. **Umleitung nach Merge.** Ein Verweis auf einen zusammengelegten Vorgang
   löst weiter auf, und keine Feststellung musste dafür umgeschrieben werden.
12. **Nicht zweimal fragen.** Ein abgelehnter Vorschlag erscheint beim nächsten Durchlauf
   nicht wieder, solange die Eingangsmenge unverändert ist.
13. **Verantwortungsgrad.** "Was hat Jens selbst geprüft?" und "was entstand
   unter einem abgenommenen Plan?" sind getrennt abfragbar.
14. **Dach nach Teilung.** Nach einem Split löst ein Verweis auf das Ursprüngliche
   weiter auf, sein Zustand ist aus den Teilen berechnet, und keine Abhängigkeit
   wurde geraten zugewiesen.
15. **Offenlegung am Ausgang.** Eine Frage, die Wissen aus mehreren Projekten
   verbindet, wird beantwortet; ein Rendern in ein System ohne deckende
   Vereinbarung wird verweigert. Beides im selben Durchlauf geprüft.
16. **Vereinbarungslücke sichtbar.** Eine Besprechung mit einem Teilnehmer ohne
   deckende Vereinbarung erzeugt eine Meldung.
17. **Gate ohne Adapter.** Die Offenlegungsprüfung funktioniert für einen
   Zielort, dessen System keine Mitgliederliste hergibt — allein aus der
   erklärten Deckung.
18. **Unbekannt blockiert.** Ein Zielort ohne Erklärung und ohne Aufzählung
   lässt sich nicht berendern.
19. **Ausreißer-Robustheit.** Ein kurz anwesender Akteur ohne bekannte
   Beteiligungen lässt die Beteiligtenregel nicht ausfallen — und erzeugt
   gleichzeitig die Vereinbarungslücken-Meldung.
20. **Hebelwirkung.** Rückfragen sind nach Zahl der auflösbaren offenen Posten
   sortiert, und diese Zahl ist pro Frage abfragbar.
21. **Verarbeitungsraum belegt.** Zu jedem Modellaufruf steht im Log der
   gesetzte *und* der gemeldete Verarbeitungsraum, und eine Abweichung löst
   einen Alarm aus.
22. **Messung pro Einheit.** Eine Zuordnung des Modells über Einheiten 3–4 und
   eine menschliche über 3–5 ergeben drei Datenpunkte, nicht null.
23. **Geprüfter Restore.** Regelmäßig und automatisiert: Restore in eine
   Wegwerf-Instanz, danach **Kettenprüfung auf dem wiederhergestellten
   Bestand**. Ein ungeprüfter Restore ist kein Backup — und die Hash-Kette
   prüft mehr als nur, dass Postgres startet.


---

## 16. Offene Punkte

| Punkt | Art | Blockiert |
|---|---|---|
| ~~Datenbankwahl~~ | **entschieden**: PostgreSQL + pgvector (§12.2) | — |
| Messversuch Textsuche | §12.3 — Hunspell vs. VectorChord-BM25 vs. Embeddings | nein |
| Tokenizer-Weg (falls `vchord_bm25`): `pg_dict`+Hunspell oder Subword-Modell | §12.2 | nein |
| Auswahl des mehrsprachigen Embedding-Modells | §10.2 | nein |
| Voxtral und Diarisation: aktueller Stand | Recherche | nein — Teil 2 ist verschoben |
| Gesprächsaufnahme: Österreich, **Deutschland, Schweiz, EU** | **Rechtsfrage, vor Teil 2 zu klären** — nicht sofort nötig, aber vor dem Bau des Abgriffs | ja, für Teil 2 |
| Wählbare Verarbeitungsräume der Anbieter | Recherche — welche Werte nimmt `inference_geo`, was bieten andere Anbieter | nein |
| Call-Plattformen (Jitsi, Teams, Signal, Telefon) | Erhebung | ja, für Teil 2 |
| Pilotkunde endgültig | Entscheidung, Vertrag prüfen | nein |
| Externer Compliance-Anlass | Annahme in §5.5, zu bestätigen | nein |

**Zur Rechtsfrage:** Sie betrifft Österreich, Deutschland, die Schweiz und die
EU — Mandate verteilen sich über diese Räume, und die Vorschriften zum
Mitschnitt unterscheiden sich. Die Schweiz steht dabei unter eigenem Recht
(revidiertes DSG, nicht DSGVO). Geklärt werden muss das nicht sofort, aber vor
dem Bau des Abgriffs.

Der Mitschnitt nicht öffentlicher Gespräche ist in
Österreich nicht ohne Weiteres zulässig — einschlägig dürfte § 120 StGB sein,
datenschutzrechtlich braucht es Rechtsgrundlage und Transparenz gegenüber
allen Beteiligten. Dies ist keine Rechtsauskunft. Praktisch zu erwarten:
Ansage zu Gesprächsbeginn, Einwilligung pro Organisation im
Organisationsprofil, und ohne
Einwilligung läuft der Abgriff nicht. Zwei Entwurfsfolgen stehen schon fest:
**transkribieren, Audio nicht aufbewahren**, und **Einwilligung gehört ins
Organisationsprofil**.

**Hardware:** Der vorhandene Rechner (4 Kerne, 62 GB RAM, keine dedizierte
GPU) trägt Whisper-Transkription und lokale Embeddings, aber kein
Open-Weight-Modell als Arbeitspferd. Lokale Inferenz ist deshalb **keine
Kostenfrage, sondern eine Datenschutzfrage.** Ob Hardware sinnvoll ist, wird
empirisch geklärt: Open-Weight-Modelle über OpenRouter gegen Haiku auf echten
Daten messen, danach entscheiden.

---

## 17. Bewusst nicht gebaut

| Verworfen | Grund |
|---|---|
| "Aussage" / "Zusage" als eigene Entität | Überlappt mit Verpflichtung und Entscheidung, wird zur Resterampe. Kommt, wenn im Betrieb etwas fehlt, das nirgends passt. |
| Löschen beim Mergen von Vorgängen | Alte Verweise auf die Kennung stehen in Work Items, Mails und Protokollen beim Auftraggeber. Statt Löschen eine Umleitung. |
| Pro-Abhängigkeit-Fragebogen beim Splitten | Niemand beendet ihn. Stattdessen bleibt alles am Dach, und gefragt wird erst, wenn eine Antwort gebraucht wird (§6.4). |
| Standard-Nachfolger beim Splitten | War in einer früheren Fassung vorgesehen. Eine Vermutung, die als Tatsache auftritt — verstößt gegen Leitsatz 9. Ersetzt durch das Dach. |
| Nur Annahmen festhalten | Ohne festgehaltene Ablehnung stellt das System bei jedem Durchlauf dieselbe Frage erneut, und die Queue wird nach drei Wochen ignoriert. |
| Verantwortung als Ja/Nein | Agentenarbeit unter einem abgenommenen Spec ist transitiv abgesegnet, nicht unverantwortet. Ohne die Abstufung wäre entweder Delegation unmöglich oder "selbst geprüft" nicht mehr von "unter Verfahren entstanden" unterscheidbar. |
| Rohe Schnittmenge bei der Beteiligtenregel | Jemand, der neunzig Sekunden hereinplatzt, hätte die Regel ausfallen lassen. Gewichtung nach Anwesenheitsdauer, und unbekannte Akteure tragen nichts bei statt alles zu zerstören. |
| Triage als Fehlerpfad | Vollständige Automatisierung der Zuordnung ist nicht in Sicht. Triage ist eine vorgesehene Betriebsart und in der ersten Phase die *primäre*. |
| Freigaben und Rückfragen in einer Liste | Eine Freigabe will gelesen werden, eine Rückfrage in drei Sekunden beantwortet. Vermischt leidet beides. |
| Messung auf Mengengleichheit | "Modell sagt 3–4, Mensch sagt 3–5" hätte als Nichtvergleich gezählt; die Messbarkeit wäre auf dem Papier schön und praktisch leer. Verglichen wird pro Einheit. |
| Identitätsgraph als erste Bauphase | Naheliegend und falsch: er ist ein Ergebnis der ersten Phasen, nicht deren Voraussetzung. |
| Berechtigungsmodelle der Zielsysteme nachbilden | GitLab-Gruppen und -Rollen, JIRA Permission Schemes und Issue Security Levels, Nextcloud-Freigaben: N Berechtigungssysteme als Nebenprodukt, dauerhaft synchron zu halten. Stattdessen erklärte Zielorte mit erklärter Deckung. |
| Aufzählung als Gate | Hätte die gesamte Offenlegungsprüfung am schwächsten Adapter aufgehängt. Aufzählung ist Prüfung, Deklaration ist Gate. |
| Dreiwertige Datenpolitik | `cloud_allowed \| tiered \| local_only` kann "EU ja, USA nein" nicht ausdrücken — und das wird die häufigste Auflage sein, nicht "nur lokal". Ersetzt durch erlaubte Räume als Liste. |
| Rechtsräume als Rangfolge | Die Schweiz ist nicht "EU minus etwas", sondern ein eigenes Regime. Liste statt Skala. |
| Offenlegung am Eingang filtern | Hätte verhindert, dass Jens sein eigenes projektübergreifendes Wissen nutzen kann — "was wissen wir über diese Agentur?" wäre unbeantwortbar. Die Prüfung sitzt am Ausgang. |
| Datenpolitik und Offenlegung als ein Feld | Zwei verschiedene Fragen: wo darf verarbeitet werden, und wer darf sehen. Dieselbe Agentur ist in einem Projekt befugt und im nächsten nicht — begrenzend ist die Vereinbarung, nicht die Organisation. |
| Einzelnes `origin`-Feld | Vermischte "wer hat formuliert" mit "wer steht dafür ein". Hätte die Mail eines Auftraggebers mit Jens' eigener Korrektur gleichgestellt und die Messung der Modellgüte still korrumpiert. Ersetzt durch `author` + `responsibility`. |
| Entität "Kunde" | "Kunde" ist eine Rolle in einem Projekt, keine Art von Organisation. Dieselbe Organisation ist mal Auftraggeber, mal ARGE-Partner, mal Allianzpartner. Ersetzt durch `Organisation` + `involvement`. |
| Binäre Richtung an der Verpflichtung | "wir / die anderen" kann den Fall nicht ausdrücken, dass zwei Dritte sich etwas schulden und uns das blockiert. Ersetzt durch Schuldner und Gläubiger als Akteure. |
| Getrennte Relationen für Personen- und Organisationsbeteiligung | Strukturell dieselbe Relation. Ein Ort für Rollen, damit Leitsatz 7 nicht wieder vergessen wird. |
| Eigene Entität "Frage" | Eine adressierte Frage *ist* eine Verpflichtung. Gelöst als `kind: answer` mit optionalem Schuldner. |
| Zwei Speicher-Backends | Führt zum kleinsten gemeinsamen Nenner. |
| Token-Abgriff aus Claude Code als API | Verstoß gegen Nutzungsbedingungen, technisch brüchig. |
| Claude über OpenRouter für Mandantendaten | Kostet den direkten DPA und ZDR, macht Prompt Caching unvorhersagbar. |
| Mandantenfähigkeit im MVP | Ein Benutzer. Die Architektur hält sie offen (Organisationsprofil, MCP-Kontext), gebaut wird sie nicht. |
| Konfigurationsoberfläche für Freigaben | Benutzt niemand. Freigaben entstehen in der Queue. |

---

## 18. Verhältnis zu RAG

Diese Frage stellt jeder, der den Entwurf liest. Kurz: **RAG ist eine
Komponente hierin, nicht die Architektur** — und der Unterschied erklärt die
meisten Entscheidungen oben.

### Der entscheidende Satz

**"Überfällig" steht in keinem Dokument.**

Kein Textabschnitt im Postfach enthält die Information, dass eine
Verpflichtung überfällig ist. Das ist eine Rechnung aus einer extrahierten
Frist und dem heutigen Datum. Retrieval findet Stellen, die *über* Fristen
reden; es findet nicht, welche gerissen sind.

Dasselbe gilt für fast alles, was gefragt werden soll: "Was schuldet der
Kunde uns?", "Was haben wir im März entschieden?", "Welche Frage ist seit vier
Monaten unbeantwortet?" Keine davon ist eine Suchfrage.

### Der architektonische Unterschied

RAG verschiebt das Verstehen auf die **Abfragezeit**: Frage einbetten, k
ähnlichste Abschnitte holen, in den Prompt stopfen, Modell antworten lassen.
Dieser Entwurf verschiebt es auf die **Aufnahmezeit**: einmal verstehen, als
Feststellung ablegen — danach ist die Abfrage eine Datenbankabfrage.

| | klassisches RAG | dieser Entwurf |
|---|---|---|
| Verstehen passiert | bei jeder Frage neu | einmal, bei der Aufnahme |
| Weltmodell | keines — nur Text und Ähnlichkeit | neun Entitäten mit Bedeutung |
| "alle offenen Punkte" | die k ähnlichsten Abschnitte | **vollständig**, per Abfrage |
| Kosten pro Frage | immer ein Modellaufruf | meist keiner |
| Belegbarkeit | "aus diesem Abschnitt" | Feststellung mit Pflicht-`sources` bis zur Einheit |
| Zeit | nur der aktuelle Index | zwei Zeitstempel, Stichtagsabfragen |
| Schreibt zurück | nein | ja, mit Freigabeklassen und Audit |

Die dritte Zeile wiegt am meisten. Eine Vektorsuche liefert die ähnlichsten
Treffer, und **man erfährt nie, was der (k+1)-te war.** Für "wo stand das
nochmal?" ist das in Ordnung. Für "was ist alles offen?" ist es falsch, und
zwar unauffällig falsch: man bekommt eine plausible Liste und hält sie für
vollständig.

Dazu: das schwierigste Problem dieses Systems ist kein Retrieval-Problem,
sondern **Zuordnung und Zerlegung** (§8). RAG hat keine Meinung dazu, zu
welcher Organisation oder welchem Projekt eine Mail gehört. Der stärkste Hebel dafür — die
Beteiligtenregel in §8.1 — ist eine Mengenoperation, gar keine KI-Technik.

### Wo RAG tatsächlich steckt

In §10, als **Rückfallpfad für Fragen, bei denen Struktur nicht hilft**: "Wo
haben wir mal über Georeferenzierung geredet?" Das ist semantische Suche, das
sind Embeddings, das ist RAGs Heimspiel. Die Embedding-Entscheidung in §10.2
(lokal, immer) *ist* eine RAG-Komponentenentscheidung.

Suchmaschine angebaut — nicht Suchmaschine als Fundament.

### Ehrliche Einordnung

RAG ist das, wonach man zuerst greift, weil es in zwei Tagen steht, und es
hätte einen Teil des Problems gelöst: die "wo stand das nochmal"-Fragen, grob
ein Drittel. Der Rest — der Teil, der durch den Inbox-Dschungel führt —
braucht Extraktion vorab.

Preis: mehr Arbeit vorne. Gewinn: billiger pro Frage, vollständige Antworten,
und ein Audit-Trail, der kein Zusatzprojekt ist.
