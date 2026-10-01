# Wissensspeicher für Kundenprojekte — Entwurf

Stand: 2026-10-01 · Status: zur Abnahme

Geschrieben für Jens als Reviewer und als Grundlage für den
Implementierungsplan. Das Gesprächsprotokoll mit allen Zwischenschritten und
verworfenen Varianten liegt in `../../../NOTIZEN.md`.

---

## 1. Zweck

Nicht mehr in N Inboxen nachsehen müssen, um zu wissen, wo ein Kundenprojekt
steht.

Alles, was zu einem Kunden hereinkommt — Mail, Chat, Besprechung, Dokument,
Issue — fließt in einen Speicher, wird Kunde, Projekt und Vorgang zugeordnet,
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
| 6 | Sprache | Python, strikt typisiert. PyO3 als benannte Notausstiegstür. Maximal zwei Sprachen. |
| 7 | Datenbank | Bewusst offen, hinter schmalem Speicher-Adapter. Kriterien in §12. |
| 8 | MVP | Teile 1, 3, 4 plus MCP-Server. Voice und eigene Oberfläche verschoben. |

---

## 3. Leitsätze

Diese fünf Sätze entscheiden im Zweifelsfall. Wenn eine Implementierung mit
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

  IMAP ─────────►   ┌────────────────────────┐
  Drop ─────────►   │  Event-Log             │ ◄──►  MCP-Server
  Prompt ───────►   │  (append-only)         │           │
  Link ─────────►   │                        │           ├─► Claude Code
  OpenProject ◄──►   │  Projektionen          │           │   (Max-Plan)
  GitLab ◄───────►   │  Entitäten              │           │
  Nextcloud ◄────►   │  Kundenprofil          │           └─► später: eigene
                     └───────────┬────────────┘               UI, Spracheingabe
                                 │
                                 ▼
                     ┌────────────────────────┐
                     │  KI-LAYER              │   unbeaufsichtigt:
                     │  Gate · Policy · Audit  │   Wahrnehmung
                     │  Zuordnung · Zerlegung  │   → Feststellung
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
| `protokoll(kunde\|projekt\|vorgang, stichtag?)` | `einwerfen(inhalt, kunde?, projekt?, vorgang?)` |
| `offene_verpflichtungen(kunde?, richtung?)` | `feststellen(…)` — Korrektur, `herkunft: mensch` |
| `entscheidungen(kunde, zeitraum?)` | `queue()` / `abnehmen(id, einmal\|klasse)` |
| `suche(frage, kunde?, vor?)` — der RAG-Pfad (§18) | |
| `event(id)` / `einheiten(event_id)` — Zitaten folgen | |

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
id, hash, vorgaenger_hash
erfasst_am                  wann es in den Speicher kam
ereignis_zeit               wann es tatsächlich geschah
quelle                      welcher Pfad + quellennative ID
belegart                    wortlaut | erinnerung
beteiligte_kanalidentitaeten
einheiten                   [{nr, inhalt, …}]
```

**`belegart` trennt Beweis von Bericht.** Mail, Issue, Transkript und PDF sind
`wortlaut`. Eine diktierte Notiz ist `erinnerung`.

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
nur von einer `erinnerung` getragen wird, ist ein Signal, das schriftlich
nachzuziehen.

`belegart` und `herkunft` sind orthogonal: `herkunft: mensch` heißt "Jens hat
das festgestellt" und schlägt weiterhin jedes Modell; `belegart: erinnerung`
heißt "die Grundlage ist ein Gedächtnis". Eine von Jens gegebene Zuordnung
bleibt Grundwahrheit — nur die inhaltliche Behauptung trägt den Vorbehalt.

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

Eine Neutranskription mit besserem Modell ist eine **neue** Wahrnehmung, keine
Änderung der alten.

### 5.2 Feststellung

```
id, hash, vorgaenger_hash, erfasst_am
art                 zuordnung | verpflichtung | entscheidung | …
ziel                event-id
einheiten           [3, 4, 7, 12]      verteilt, nicht zusammenhängend
herkunft            mensch | regel | modell
sicherheit
inhalt              artabhängig
quellen             Event-IDs + Einheiten, auf die sie sich stützt
```

**`herkunft` ist der Kern des Audits und des Lernens.** Bei Konflikt gilt:
**Mensch schlägt Regel schlägt Modell.** Eine Korrektur durch Jens ist eine
Feststellung mit `herkunft: mensch` — kein Sonderfall, kein eigener
Mechanismus. Das gilt gleichermaßen für eine Korrektur am Protokoll und für
eine Änderung, die direkt in OpenProject gemacht wurde.

**Nur Feststellungen kommen aus dem Modell.** Damit ist "Was hat das Modell je
behauptet, und worauf gestützt?" eine Abfrage über eine Event-Art.

**`quellen` ist Pflicht und wird im Schema erzwungen.** Eine Feststellung ohne
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
id, hash, vorgaenger_hash, erfasst_am
art                 aufgabe_angelegt | mail_versendet | …
ziel                Entität, auf die sie wirkt
freigabe            auftrag | einmal | klasse:<id>
begruendung         Feststellungs-IDs
ergebnis            externe Referenz, gerenderter Zustand, Fehler
```

**Handlung ist die Spur delegierter Handlungsmacht** — sie beantwortet "was hat
das System getan, und mit welcher Befugnis?".

Daraus folgt eine beabsichtigte Asymmetrie: **Was Jens selbst tut, ist keine
Handlung, sondern Eingang.** Legt er ein Issue direkt in GitLab an, sieht der
Konnektor die Änderung, sie wird Wahrnehmung, daraus eine Feststellung mit
`herkunft: mensch`. Ein Befugnisnachweis ist dafür sinnlos — er ist der
Auftraggeber, nicht der Beauftragte.

Die drei Befugnisse:

| Wert | Bedeutung |
|---|---|
| `auftrag` | direkt angewiesen (z. B. in Claude Code), es gab keinen Vorschlag |
| `einmal` | ein Vorschlag wurde abgenommen, dieses eine Mal |
| `klasse:<id>` | eine Dauerfreigabe deckte es |

**Eine Handlung ohne einen dieser Werte ist ein Defekt, kein Zustand.** Einen
Wert wie "nie gefragt" als zulässig zu führen würde unautorisiertes Handeln
normalisieren; die Integritätsprüfung (§15) schlägt darauf an.

### 5.5 Rückkopplung ist gewollt, Schwingung nicht

Dieses System **ist** eine Rückkopplungsschleife, und das ist Absicht. Das
System schlägt ein Issue vor, Jens ändert es in GitLab, die Änderung fließt
zurück und verbessert das Verständnis im Kern. Diese Schleife ist der
**Lernmechanismus**: eine Korrektur an einem vom System erzeugten Artefakt ist
Grundwahrheit nach §8.3 — der wertvollste Eingang überhaupt.

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

**3. Strikte Vorrangordnung.** Mensch schlägt Regel schlägt Modell, strikt
(§5.2). Damit ist die wahrscheinlichste Schwingung konstruktiv unmöglich —
Modell behauptet A, Mensch korrigiert auf B, Modell behauptet wieder A — weil
ein Modell eine menschliche Feststellung nie überschreiben darf.

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

## 6. Kern, Schicht 2: Neun Entitäten

Alle sind Projektionen über das Event-Log, keine Wahrheitstabellen. Alle
überleben den Wegfall jedes Fremdsystems.

| # | Entität | Zweck |
|---|---|---|
| 1 | **Kunde** | Lebt im Kern, weil kein Fremdsystem ihn kennt. |
| 2 | **Projekt** | Arbeit für einen Kunden. Muss verschobene Grenzen und Umbenennungen aushalten. |
| 3 | **Person** | Ein Mensch. |
| 4 | **Kanalidentität** | Mailadresse, Signal-Nummer, Discord-Handle, Sprecherkennung, Fremdsystem-Benutzer. Eigenständig, weil eine unbekannte Adresse eine Identität **ohne** Person ist — das ist der Zustand "unsortiert". |
| 5 | **Beteiligung** | Person × (Projekt oder Aufgabe) × Rolle × Zeitraum. |
| 6 | **Vorgang** | Die inhaltliche Klammer. Primäre Zugangsebene. |
| 7 | **Verpflichtung** | Wer schuldet wem was, bis wann, in welchem Zustand. **Mit Richtung.** |
| 8 | **Aufgabe** | Ausführbare Arbeit. Trägt die PM-Verknüpfung. |
| 9 | **Entscheidung** | Was wurde entschieden, von wem, wann, auf welcher Grundlage. |

### 6.1 Beteiligung

Rolle ist eine Beziehung, keine Eigenschaft der Person. Alex ist
*Freelancer bei Projekt A* **und** *Freelancer bei Projekt B* — zwei
Beteiligungen, nicht zwei Rollen an einer Person.

Rollen: `mitarbeiter`, `partner`, `freelancer`, `kundenperson`.

Das Ziel ist Projekt **oder** Aufgabe. Grobe und feine Beteiligung sind kein
Modellunterschied, nur ein Zielunterschied.

Der Zeitraum fällt gratis an, weil Beteiligung eine Projektion über
Feststellungen mit Ereigniszeit ist. "Wer war im März 2024 beteiligt?" ist
dieselbe Abfrage mit anderem Stichtag.

### 6.2 Verpflichtung und Aufgabe sind zwei Dinge

| | |
|---|---|
| **Verpflichtung** | Der Sachverhalt: "Wir schulden dem Kunden den Bericht bis 30.4." |
| **Aufgabe** | Die Arbeit: "Kapitel 3 schreiben", "Review mit Anna". |

Eine Verpflichtung erzeugt null bis mehrere Aufgaben. Eine Aufgabe kann ohne
Verpflichtung existieren (interne Arbeit).

**Eine Verpflichtung des Kunden erzeugt bei uns keine Aufgabe** — muss aber im
Protokoll stehen und überfällig werden können. Bei einer zusammengelegten
Entität wäre genau das kaputt, und es ist die Hälfte der Wahrheit in
kooperativem Projektmanagement: was der Kunde *uns* schuldet, steht heute in
keinem Werkzeug und liegt nur in Mails herum.

Arten: `lieferung`, `antwort`, `entscheidung`, `zahlung`.

**`schuldner` darf leer sein.** Eine unadressierte Frage — "weiß eigentlich
jemand, ob die Messdaten georeferenziert sind?" — ist eine Verpflichtung mit
`art: antwort` und leerem Schuldner. Das liest sich als "jemand muss das
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
Event. Hängt an einem Kunden, kann mehrere Projekte berühren.

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

---

## 7. Kern, Schicht 3: Kundenprofil

Alles, was pro Kunde variiert, an einer Stelle. Gelesen vom Policy-Gate, vom
Konnektor-Lader und von der Freigabe-Queue.

```
kunde
systeme             [{art, basis_url, fähigkeitsstufe, zugangsdaten-ref}]
datenpolitik        cloud_erlaubt | gestuft | nur_lokal
freigabeklassen     [{aktionsklasse, zustand}]
aufnahme_einwilligung
```

---

## 8. Zuordnung: zweistufig

### 8.1 Stufe eins — die Teilnehmerregel

**Schneide die Projekt-Beteiligungen aller Anwesenden. Bleibt genau ein
Projekt übrig, ist es das.**

```
Discord #general, 10:00–10:45
  anwesend: Jens, Alex, [Kundenperson A]
  → Schnittmenge der Beteiligungen: { Projekt A }
  → Zuordnung: Projekt A · herkunft: regel · sicher

Discord #general, 11:00–12:00
  anwesend: Jens, Alex, [Kundenperson B], [Kundenperson C]
  → Schnittmenge: { Projekt B }
  → Zuordnung: Projekt B · herkunft: regel · sicher
```

Derselbe Raum, dieselbe Person Alex, zwei Projekte. Alex trägt zur
Unterscheidung nichts bei; die Kundenpersonen tragen alles. Rollen sind
deshalb nicht Dekoration: **Kundenpersonen diskriminieren stark, eigene Leute
kaum.**

Deterministisch, auditierbar, kostet keinen Token, und kein Modell kann es
falsch machen. Gilt überall: bei Mail der Empfängerkreis einschließlich CC —
oft ein besserer Hinweis als der Betreff; bei Voice die erkannten Sprecher;
bei Discord die Anwesenden im Zeitfenster.

**Folge: Der Identitätsgraph ist nicht Hausarbeit, er ist der Klassifikator.**
Er wird im MVP zuerst richtig gemacht.

*Einschränkung:* Für Discord-**Voice**-Räume ist Anwesenheit pro Zeitfenster
exakt (Join/Leave). Für Text-Kanäle gibt es keine Anwesenheit — dort gilt
"wer hat im Zeitfenster geschrieben", schwächer aber brauchbar.

### 8.2 Stufe zwei — Zerlegung durch das Modell

Nur wenn Stufe eins mehr als ein Projekt übrig lässt, oder wenn ein Event
mehrere Vorgänge betrifft.

Eine Kundenmail enthält selten genau ein Thema; ein zweistündiges Transkript
enthält viele. Das Modell gibt Zuordnungs-Feststellungen über Einheitenmengen
aus, verteilt und überlappend erlaubt.

**Das ist die wertvollste Modelloperation im System.** Ein Transkript ist als
Klumpen wertlos und als zwölf Abschnitte auf fünf Vorgänge verteilt
brauchbar. Dort wird der Dschungel gelichtet — nicht beim Einsortieren von
Mails.

Kosten: ein 2-Stunden-Transkript sind ~30.000 Tokens, ein Aufruf pro
Besprechung. Bei Mails läuft ein billiger Vorlauf, der "ein Thema" erkennt
und die Zerlegung überspringt; das dürfte die Mehrheit sein.

### 8.3 Messbarkeit fällt gratis an

Beim manuellen Einwurf gibt Jens die Zuordnung mit — `herkunft: mensch`, also
**Grundwahrheit**. Damit wird die Güte der automatischen Zuordnung eine
Abfrage: vergleiche Feststellungen mit `herkunft: regel` oder `modell` gegen
spätere mit `herkunft: mensch` **über derselben Einheitenmenge**.

Treffergenauigkeit pro Abschnitt, aus normaler Arbeit erzeugt, ohne
Evaluierungsprojekt.

---

## 9. Projektionen

Jeder Zustand wird aus dem Event-Log berechnet und ist jederzeit neu
berechenbar — auf jeden Stichtag, in beiden Zeitordnungen.

### 9.1 Die Protokollfamilie

**Eine Maschine, drei Zuschnitte:** Kundenprotokoll, Projektprotokoll,
Vorgangsprotokoll. Der Vorgang bekommt seine Ansicht dadurch gratis.

```
KUNDE <name> — Stand 1. Oktober 2026

Offen von uns          3 Verpflichtungen, davon 1 überfällig
Offen vom Kunden       2 Verpflichtungen, 1 unbeantwortete Frage (4 Monate)
Letzte Entscheidungen  3

── Chronik (Ereigniszeit) ──────────────────────────────
2024-03-14  Kickoff-Call. Entscheidung: Datenmodell
            nach Variante B.                  [T-0231 ¶12, M-0442 ¶3]
2024-03-18  Kunde sagt Messdaten bis Ende März zu.    [M-0455 ¶3,7]
```

Der Kopf ist keine Zusammenfassung, sondern eine Abfrage über Verpflichtungen
und Fragen. Jede Zeile trägt Event-IDs und Einheitennummern — stabil,
nachprüfbar, klickbar.

**Das Protokoll ist keine gepflegte Datei.** Es wird nie nachgeführt und ist
deshalb nie veraltet. Eine Korrektur daran ist eine Feststellung mit
`herkunft: mensch`: sie überschreibt die Quelle nicht, tritt daneben und
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

**Konsequenz:** Steht ein Kunde auf `nur_lokal`, verweigert der MCP-Server
dessen Inhalte an Claude Code — das Cockpit wird für diesen Kunden stumpfer
(strukturierte Abfragen ja, KI-Unterstützung nur mit lokalem Client). Das ist
kein Konstruktionsfehler, sondern der Preis der Datenpolitik, und er trifft
die interaktive Seite härter als die Pipeline.

```
llm(aufgabe, nutzlast, kontext{kunde, projekt, vertraulichkeit}) → ergebnis
```

**`vertraulichkeit` ist nicht dasselbe wie Zuordnung** und hat deshalb einen
eigenen Namen. Sie kommt aus zwei Quellen, in dieser Reihenfolge: der
`datenpolitik` des Kundenprofils als Vorgabe, und optional einer Feststellung
`art: vertraulichkeit` über einzelne Einheiten, wenn ein Abschnitt sensibler
ist als der Kundenstandard (Gehaltsdaten, Vertragsentwurf, Personensache).
Die strengere der beiden gewinnt.

Das Gate entscheidet Anbieter und Modell für diese Nutzlast daraus. Heute gibt es für alle Kunden "Cloud erlaubt"
zurück; später steht dort eine Regel pro Kunde. Ein Modul, keine
Umbaumaßnahme.

**Damit zu rechnen:** Die Policy-Schicht enthält im ersten Jahr echte Regeln.
Ein Kunde, der seine Entwicklungsumgebung selbst hostet, hat das aus einem
Grund getan.

Dasselbe Gate protokolliert: Zeitpunkt, Aufgabe, Datenreferenzen (keine
Kopien), Modell, Prompt-Version, Ergebnis, Kosten. **Das Audit-Log ist ein
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

Risiko-Ordnung, die bestimmt, was wann automatisierbar wird:

| | strukturiert | freie Prosa |
|---|---|---|
| **intern** | Aufgabe anlegen, Dokument ablegen → früh automatisierbar | Protokoll-Entwurf → Freigabe |
| **extern** | Empfangsbestätigung, Terminvorschlag → enge Automatisierung | Kundenmail → **immer Freigabe** |

---

## 11. Konnektoren

### 11.1 Der Vertrag

Ein Konnektor ist nichts Besonderes: **Renderer** in die eine Richtung,
**Event-Quelle** in die andere. Dieselbe Mechanik wie beim Protokoll — ein
Work Item ist eine Projektion, gerendert als Work Item.

Dadurch verschwindet das Sync-Problem: eine Änderung direkt im Fremdsystem
kommt als Feststellung mit `herkunft: mensch` herein, die Wahrheit im Kern
aktualisiert sich, und das nächste Rendern ist ein No-Op. **Die Idempotenz des
Renderns ist dabei eine Konvergenzbedingung, keine Bequemlichkeit** — siehe
§5.5. Kein Konfliktdialog,
keine Sync-Richtung.

**Weil der Kern die Wahrheit hält, darf Rendern verlustbehaftet sein.** Eine
"Verpflichtung mit Frist" landet in einem schwachen Zielsystem als Issue mit
Label, die Nuance bleibt im Kern. Deshalb ist eine heterogene
Kundenlandschaft überlebbar.

### 11.2 Fähigkeitsstufen

| Stufe | Beispiel | Was geht |
|---|---|---|
| beidseitig | eigenes OpenProject, Kunden-GitLab mit API-Key | Events rein, Rendern raus |
| nur lesend | API-Key ohne Schreibrechte | Events rein |
| keine API | Kunde will nicht, Altsystem, Freigabe dauert | siehe 11.3 |

### 11.3 IMAP ist der Auffangboden

Fast jedes System der Welt schickt Benachrichtigungsmails. Ein Kundensystem
ohne API-Zugriff redet trotzdem mit uns: seine Ereignisse kommen als Mail und
sind damit im Kern. Nicht elegant, aber vollständig genug für Verlauf und
Protokoll.

Das verschiebt den Langschwanz-Aufwand von "N Integrationen" auf "N
Mail-Parser". **Folge: Der Mail-Konnektor ist nicht eine Inbox von vielen,
sondern der Auffangboden für alles Nicht-Integrierbare — und muss
entsprechend gut sein.**

### 11.4 Der manuelle Einwurf ist der Referenz-Konnektor

| Pfad | Zuordnung | Anmerkung |
|---|---|---|
| **IMAP** | geraten | automatisch, kontinuierlich |
| **Drop-Ordner** | Unterordner = Kunde | ein Nextcloud-Ordner: funktioniert auch vom Telefon |
| **Einwurf per Prompt** | Jens sagt sie | `belegart: erinnerung`. Hier landet später die Spracheingabe — derselbe Pfad, anderes Eingabegerät |
| **Quelle verlinken** | Jens sagt sie | GitLab-/GitHub-Issue-URL; wird geholt und nachgehalten |

**Der Prompt-Pfad ist der qualitativ beste, nicht der Notausgang.** Er kann
etwas, was weder Formular noch Drop-Ordner kann: **beim Einwurf nachfragen** —
"Welches Projekt?", "Hat er ein Datum genannt?", "Zusage oder
Absichtserklärung?" — und zwar während die Erinnerung frisch ist. Bei
Telefonaten ist er auch dauerhaft der einzige Weg: ein Handy-Anruf läuft nie
durch die PipeWire-Pipeline, Teil 2 deckt das nie ab.

Suboptimal ist er nur dort, wo ein Konnektor dasselbe holen könnte — nicht
wegen des Aufwands, sondern weil die Quelle dann `wortlaut` wäre und die
Zusammenfassung davon `erinnerung`.

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

Kriterien für die Entscheidung. Vorweg: **das Datenvolumen ist klein** — bei
150 Mails pro Tag über fünf Jahre rund 275.000 Mails, mit Transkripten und
Chats einstellige Millionen Events und zweistellige Gigabytes Text. Eine
Maschine. Deshalb entscheiden nicht Durchsatzfragen, sondern:

1. **Vektorsuche mit Vorfilter.** "Ähnliche Passagen, aber nur Kunde X, nur
   vor dem 14. März." Manche Engines filtern erst nach der Suche nach und
   liefern dann zu wenige Treffer.
2. **Deutsche Volltextsuche.** Snowball-Stemming kommt mit Komposita nicht
   zurecht — wer "Vergaberecht" sucht, findet "Recht der Vergabe" nicht.
   Bei diesen Inhalten keine Randnotiz.
3. **Reprojektion als Stream.** Alle Events eines Kunden lesen und neu
   rechnen, ohne alles in den Speicher zu ziehen.

---

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

Der MVP ist auch nach dieser Abgrenzung groß. Der Implementierungsplan wird
in Phasen zu schneiden sein; der Identitätsgraph gehört in die erste, weil er
der Klassifikator ist.

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
4. **Quellenpflicht.** Keine Feststellung ohne `quellen`. Durch Schema
   erzwungen, durch Test belegt.
5. **Stichtagsabfrage.** "Stand am Datum X" ist in beiden Zeitordnungen
   beantwortbar.
6. **Zuordnungsgüte.** Die Trefferquote von `regel` und `modell` gegen
   `mensch` ist pro Abschnitt abfragbar.
7. **Gate-Dichte.** Kein Modellaufruf außerhalb des Gates. Statisch geprüft.
8. **Befugnis.** Keine Handlung ohne `auftrag`, `einmal` oder `klasse:<id>`.
9. **Konvergenz.** Rendern, abfragen, erneut rendern erreicht einen Festpunkt
   innerhalb eines Umlaufs: die eigene Handlung erzeugt **keine** neue
   Wahrnehmung. Und die Gegenprobe, die genauso wichtig ist: eine *fremde*
   Änderung am Ziel erzeugt **genau eine** Wahrnehmung — die Schleife darf
   nicht so dicht gemacht werden, dass sie das Lernen mit abwürgt.
10. **Schwingungserkennung.** Eine künstlich konstruierte Zirkularität wird
   vom Wächter angehalten und landet in der Queue, statt unbemerkt zu laufen.

---

## 16. Offene Punkte

| Punkt | Art | Blockiert |
|---|---|---|
| Datenbankwahl | Recherche nach §12 | nein — Adapter-Schnittstelle genügt |
| Voxtral und Diarisation: aktueller Stand | Recherche | nein — Teil 2 ist verschoben |
| Gesprächsaufnahme in Österreich | **Rechtsfrage, vor Teil 2 zu klären** | ja, für Teil 2 |
| Call-Plattformen (Jitsi, Teams, Signal, Telefon) | Erhebung | ja, für Teil 2 |
| Pilotkunde endgültig | Entscheidung, Vertrag prüfen | nein |
| Externer Compliance-Anlass | Annahme in §5.5, zu bestätigen | nein |

**Zur Rechtsfrage:** Der Mitschnitt nicht öffentlicher Gespräche ist in
Österreich nicht ohne Weiteres zulässig — einschlägig dürfte § 120 StGB sein,
datenschutzrechtlich braucht es Rechtsgrundlage und Transparenz gegenüber
allen Beteiligten. Dies ist keine Rechtsauskunft. Praktisch zu erwarten:
Ansage zu Gesprächsbeginn, Einwilligung pro Kunde im Kundenprofil, und ohne
Einwilligung läuft der Abgriff nicht. Zwei Entwurfsfolgen stehen schon fest:
**transkribieren, Audio nicht aufbewahren**, und **Einwilligung gehört ins
Kundenprofil**.

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
| Eigene Entität "Frage" | Eine adressierte Frage *ist* eine Verpflichtung. Gelöst als `art: antwort` mit optionalem Schuldner. |
| Zwei Speicher-Backends | Führt zum kleinsten gemeinsamen Nenner. |
| Token-Abgriff aus Claude Code als API | Verstoß gegen Nutzungsbedingungen, technisch brüchig. |
| Claude über OpenRouter für Mandantendaten | Kostet den direkten DPA und ZDR, macht Prompt Caching unvorhersagbar. |
| Mandantenfähigkeit im MVP | Ein Benutzer. Die Architektur hält sie offen (Kundenprofil, MCP-Kontext), gebaut wird sie nicht. |
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
| Belegbarkeit | "aus diesem Abschnitt" | Feststellung mit Pflicht-`quellen` bis zur Einheit |
| Zeit | nur der aktuelle Index | zwei Zeitstempel, Stichtagsabfragen |
| Schreibt zurück | nein | ja, mit Freigabeklassen und Audit |

Die dritte Zeile wiegt am meisten. Eine Vektorsuche liefert die ähnlichsten
Treffer, und **man erfährt nie, was der (k+1)-te war.** Für "wo stand das
nochmal?" ist das in Ordnung. Für "was ist alles offen?" ist es falsch, und
zwar unauffällig falsch: man bekommt eine plausible Liste und hält sie für
vollständig.

Dazu: das schwierigste Problem dieses Systems ist kein Retrieval-Problem,
sondern **Zuordnung und Zerlegung** (§8). RAG hat keine Meinung dazu, zu
welchem Kunden eine Mail gehört. Der stärkste Hebel dafür — die
Teilnehmerregel in §8.1 — ist eine Mengenoperation, gar keine KI-Technik.

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
