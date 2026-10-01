# Arbeitsnotizen — Brainstorming

Laufendes Protokoll der Entscheidungen. **Kein Spec.** Das Spec entsteht,
wenn das Bild steht, unter `docs/superpowers/specs/`.

Stand: 2026-10-01

## Ziel

Nicht mehr in N Inboxen nachsehen müssen, um zu wissen, wo ein Kundenprojekt
steht. Alles fließt rein, wird Kunde/Projekt/Thread zugeordnet, Verlauf und
offene Todos jederzeit parat — und von dort aus handeln können (Antwort
entwerfen, Work Item anlegen, Protokoll ablegen).

## Entschieden

| # | Frage | Entscheidung |
|---|-------|--------------|
| 1 | Nutzerkreis | Single-User (Jens) zuerst, Team-Fähigkeit architektonisch offenhalten. Kunden-Zugang raus. FOSS-Release als Option, kein Hauptziel. |
| 2 | Datenabfluss | **A mit Naht**: Cloud-API okay (ZDR + DPA), aber nichts verbauen, falls später B (gestuft) oder C (alles lokal). |
| — | Motoren | Vier, alle hinter *einem* Gate: Max-Plan (interaktiv/Cockpit), Anthropic-API direkt (sensible Masse, ZDR), OpenRouter (Experimente + unkritische Masse), lokal (Whisper, Embeddings). |
| 6 | Stack | **Python**, strikt typisiert (pyright strict, nicht als Deko). **PyO3 als benannter Notausgang** für Rust, falls etwas schnell werden muss. **Maximal zwei Sprachen.** Später reevaluieren. Begründung nicht "Jens kann es", sondern: `pyannote` (Diarisation) und das Dokumenten-/OCR-Ökosystem haben keinen gleichwertigen Weg daneben. Datenbank **bewusst offen** — hinter schmalem Speicher-Adapter. |
| 5 | MVP-Schnitt | **A + manueller Einwurf.** IMAP breit über alle Kunden, plus drei manuelle Pfade (Drop-Ordner für PDFs, Einwurf per Prompt für Chat-Texte, Quelle verlinken für GitLab-/GitHub-Issues). Oberfläche = Claude Code über MCP. Voice und eigene UI verschoben. Pilotkunde: Auftraggeber A oder Auftraggeber B — **Bestandsimport nötig**. |
| 4 | System of Record | **B — der Kern hält die Wahrheit.** OpenProject/GitLab/Nextcloud sind *Inbox und Artefakt* gleichzeitig. Begründung: keine Technologiebindung; wenn etwas Besseres als OpenProject kommt, muss es austauschbar sein. |
| 3 | "auditiert" | **Alle drei** — A (Freigabe-Pflicht, aber Dauerfreigaben pro Klasse möglich), B (Nachvollziehbarkeit), C (revisionssicher). Plus: Template-gebundene Aktionen dürfen raus. GitLab Issues als erstes Beispiel. |

## Offen

- **Recherche Datenbank** (von Jens aufgeschoben, Kriterien unten notiert).
- **Recherche Voxtral/Diarisation** (angeboten, nicht blockierend — Teil 2
  ist verschoben).
- **Rechtsfrage Gesprächsaufnahme** vor Teil 2 klären (Österreich, Einwilligung).
- Call-Plattformen für Teil 2: Jitsi, Teams, Signal, Telefon?
- Pilotkunde endgültig: Auftraggeber A oder Auftraggeber B. Vorher
  **Vertrag/AVV prüfen** — Auftraggeber A ist eine öffentliche Einrichtung, die Naht
  aus Frage 2 wird damit im Pilot geprüft, nicht in zwei Jahren.
- Voice: welche Call-Plattformen konkret?
- Implementierungssprache (für später, nicht für den Entwurf).

## Annahmen, die auf Korrektur warten

- **Kein harter externer Compliance-Anlass** (ISO 27001, öffentlicher
  Sektor, Vertragsklausel) wurde genannt. Annahme: "belegbar für Jens und
  auf Kundennachfrage", nicht zertifizierungsgetrieben. Heißt konkret:
  Hash-Kette und lückenloses Log ja; keine Aufbewahrungsfristen-Automatik,
  keine WORM-Speicherung, keine Prüfer-Exportformate. Falls doch, wird C
  von einer Tabelle zu einem Teilprojekt.

## Architektur-Festlegungen

### Der Riegel (Policy Gate)

Eine Stelle, durch die *jeder* Modell-Aufruf geht. Nichts ruft ein SDK direkt auf.

    llm(task, payload, kontext{kunde, projekt, klassifikation}) -> ergebnis

Das Gate entscheidet Anbieter + Modell für diese Nutzlast. Heute immer
"Cloud okay"; später eine Regel pro Kunde. Ein Modul, keine Umbaumaßnahme.

Dasselbe Gate schreibt mit: Zeitpunkt, Aufgabe, Datenreferenzen (keine
Kopien), Modell, Prompt-Version, Ergebnis, Kosten. **Das Audit-Log ist
Nebenprodukt der Policy-Schicht, kein Extra-Projekt.**

Adapter: Anthropic-SDK + OpenAI-kompatibel. Letzteres deckt OpenRouter,
Ollama und llama.cpp ab.

### Drei Regeln, die A offenhalten

1. Keine SDK-Aufrufe in der Fläche — alles durch das Gate.
2. Jedes Event trägt Kunde, Projekt, Klassifikation ab Tag eins, auch
   solange nichts damit macht. Nachträgliche Klassifikation von
   Bestandshistorie ist vermeidbare Arbeit.
3. **Embeddings bleiben lokal.** Nicht wegen Geld: es ist der einzige
   Schritt, bei dem jeder einzelne Inhalt vollständig das Haus verlässt —
   schlechtestes Verhältnis Nutzen/Exposition. Und bei späterem Wechsel
   auf C muss die Historie nicht neu eingebettet werden.

### Kern: Wissensspeicher + MCP-Server

              Wissensspeicher (Events, Entitäten, Zeitachse)
                              | MCP
            +-----------------+-----------------+
       Claude Code       Pipeline-Worker    später: Web-UI,
       (Max, Cockpit)    (Haiku/Batch       Spracheingabe,
                          oder lokal)       Kollegen

Intelligenz nicht im Kern verdrahtet — sonst kann nur ein Motor dran.
Ein MCP-Server über einem sauberen Store ist auch das FOSS-fähige Artefakt;
die Verdrahtung mit konkreten Postfächern ist Konfiguration, nicht Code.

## Zerlegung (fünf Teile)

Ursprünglich sechs; "Ingest" und "Write-back" sind nach Frage 4 **eine**
Schicht (siehe unten).

1. **Konnektoren** (bidirektional) — IMAP, Signal, Discord, OpenProject,
   GitLab, Nextcloud. Alle nach demselben Muster: Renderer raus, Events rein.
2. **Voice** — PipeWire-Abgriff, Transkription, Diarisation. Technisch
   eigenständig genug für einen eigenen Teil. Nur Inbox-Richtung.
3. **Kern** — Event-Store, Hash-Kette, Kernmodell, Identitätsgraph,
   Projektionen. **Das Rückgrat.**
4. **KI-Layer** — Gate, Retrieval, Templates, Freigabe-Klassen, Audit.
5. **Oberfläche** — Freigabe-Queue, Protokollansicht, Spracheingabe.

## Hardware-Befund (2026-10-01)

Tuxedo-Laptop: i7-11370H, 4C/8T, 62 GB RAM, **nur Intel Iris Xe — keine
dGPU**. Ollama installiert, PipeWire 1.6.7.

Lokale LLM-Inferenz = CPU. RAM reicht zum Laden, Durchsatz nicht für
Kontext-Zusammenfassung. Whisper auf 8 Threads ist machbar.

Konsequenz: lokal ist **keine Kostenentscheidung**. Die mengenintensive
Arbeit (Klassifikation, Extraktion) ist in der Cloud fast gratis; der teure
Teil (Denken, Formulieren) ist genau der, den die CPU am schlechtesten kann.
GPU für ein brauchbares 24-32B-Modell: 1.500-2.500 EUR. Bei ~20 USD/Monat
Cloud rechnet sich das monetär nicht.

**Hardware-Frage empirisch klären, nicht kaufen:** Open-Weight-Modelle über
OpenRouter gegen Haiku auf echten Mails messen. Erst danach entscheiden, ob
und welche Hardware.

## Kostenschätzung

Annahme: ~150 Mails/Tag, 2 h transkribierte Calls/Tag, etwas Chat
= ~3-4 Mio. Input-Tokens/Monat für die Fleißarbeit.

| Modell | Input $/1M | Output $/1M | Kontext |
|---|---|---|---|
| Claude Haiku 4.5 | 1,00 | 5,00 | 200K |
| Claude Sonnet 5 | 2,00 | 10,00 | 1M |
| Claude Opus 5 | 5,00 | 25,00 | 1M |

- Triage mit Haiku 4.5: ~5 USD/Monat, mit **Batch API** (50 % Rabatt,
  asynchron — passt, Ingest braucht keine Echtzeit) ~2,50 USD.
- Interaktive Schicht ist der teure Teil (50 Abfragen/Tag à 30K Kontext
  wären bei Sonnet 5 ~90 USD/Monat). **Dieser Teil läuft über den
  Max-Plan.** Prompt Caching + gutes Retrieval drücken den Rest stark.

Hausnummer: 10-50 USD/Monat.

## Max-Plan: Grenze

Deckt: Jens am Terminal in Claude Code — der interaktive, teure Teil.
Deckt nicht: unbeaufsichtigte 24/7-Pipeline. Limits sind nicht als
Dauerlast gedacht, und ein Hintergrundprozess, der mittags das Limit reißt,
macht das Arbeitsgerät kaputt.

Token-Abgriff aus Claude Code als API: ToS-Verstoß, bricht bei jedem
Refresh. Nicht bauen.

Grauzone: `claude -p` headless, von Jens angestoßen, auf seiner Maschine,
für seine Arbeit. Nächtlicher Lauf = normale Nutzung. Hunderte Calls/h = nicht.

## OpenRouter: Vorbehalte

- Vermittler, kein Abkürzungsweg: Daten gehen an OpenRouter *und* den
  dahinterliegenden Anbieter. Unterauftragsverarbeiter-Kette ist nichts,
  was man einem Kunden nach Art. 28 DSGVO stabil hinschreibt. Für
  Mandantendaten schwächer als direkter Anthropic-DPA mit ZDR.
- Claude über OpenRouter kostet den direkten Vertrag (kein DPA, kein ZDR)
  und macht Prompt Caching unvorhersagbarer — der größte Kostenhebel.
  Claude also direkt; OpenRouter für Experimente und unkritische Masse.

## Freigabe-Modell (aus Frage 3)

**Leitsatz: Autonomie entsteht durch Einschränkung, nicht durch Vertrauen.**

Eine Aktion darf nur automatisch laufen, wenn sie **an ein Template
gebunden** ist — die KI füllt Felder in einer vorgegebenen Form, sie
formuliert nicht frei. Freier Prosa-Output bleibt dauerhaft
freigabepflichtig, egal wie gut er wird. Nicht "ich vertraue dem Modell
inzwischen", sondern "an dieser Stelle *kann* das Modell nichts anderes tun".

### Risiko-Ordnung

|            | strukturiert | freie Prosa |
|------------|--------------|-------------|
| **intern** | GitLab Issue, OpenProject Work Item, Nextcloud-Ablage -> früh automatisierbar | Protokoll-Entwurf -> Freigabe, später evtl. mit Hinweis |
| **extern** | Empfangsbestätigung, Terminvorschlag -> enge Automatisierung möglich | Kundenmail -> **immer Freigabe** |

GitLab Issues sind der beste Kandidat im System (strukturiert, intern,
kleiner Schaden, umkehrbar). Kundenmail der schlechteste (frei, extern,
unwiderruflich).

### Aktionsklassen

Jede vorgeschlagene Aktion bekommt eine Klasse:
*was* (Issue anlegen / Mail antworten / Dokument ablegen)
x *wo* (Kunde, Projekt, Kanal)
x *mit welchem Template*.

Zustand pro Klasse: `fragen` (Standard für alles Neue) | `auto` (optional
mit Hinweis danach) | `nie`.

**Entscheidend für die Praxis:** Die Dauerfreigabe wird *aus der
Freigabe-Queue heraus* erteilt. Beim Abnehmen stehen "einmal" und "diese
Klasse ab jetzt" nebeneinander. Der Regelsatz lagert sich aus echten
Entscheidungen ab; niemand setzt sich hin, um Policy zu konfigurieren.

### B ist dieselbe Maschine wie A

Das Modell wird **nie** um freien Text gebeten, sondern immer um
strukturierte Ausgabe mit einem `quellen`-Feld (Event-IDs). Retrieval gibt
nur Inhalte heraus, die eine ID tragen. Eine Behauptung ohne Quelle ist
dann kein Vertrauensproblem, sondern ein **Schemafehler**.

Ein Template ist ein Schema; eine Quellenangabe ist ein Feld darin.
B fällt an, wenn A richtig gebaut ist.

### C zwingt die Datenhaltung — zum Guten

**Append-only, nichts wird je überschrieben oder gelöscht.** Jeder Eintrag
hasht den vorherigen (Hash-Kette, ~20 Zeilen). Aller Zustand —
Projektstand, offene Todos, Zuordnungen — ist eine **Projektion**, jederzeit
neu berechenbar.

Keine Übertreibung, sondern die natürliche Form: die Eingangsdaten *sind*
schon ein Event-Strom. Mails, Nachrichten, Transkripte kommen an und ändern
sich nie.

Drei Dinge fallen gratis an:

1. **Audit-Log und Wissensspeicher sind dasselbe Ding** — keine zwei
   Systeme, die auseinanderlaufen.
2. **"Was wusste ich am 14. März?"** wird beantwortbar — das eigentliche
   Ziel, nur anders formuliert.
3. **Regel 2** (Klassifikation nachrüsten) wird vom Datenmigrations- zum
   Projektions-Neuberechnungsproblem. Besser klassifizieren können heißt
   dann: über die Historie laufen lassen. Keine Migration.

Deshalb jetzt: die Hash-Kette kostet heute fast nichts und ist nachträglich
unmöglich.

## Kundenprotokoll (Nachtrag zu Frage 3)

Anforderung: **Immer ein Protokoll pro Kunde vorhanden.** Jens: "entweder
als Text oder aus DB-Daten generiert, das sind aber Details".

Keine Zusatzanforderung, sondern das, was aus append-only + Quellenangaben
von selbst herausfällt. Das Protokoll ist **keine gepflegte Datei, sondern
eine Projektion** über den Event-Strom des Kunden. Die Textform ist ein
Rendering, keine zweite Wahrheit — damit löst sich "Text oder DB" auf.

Drei Eigenschaften fallen zu:

- **Nie veraltet**, weil nie gepflegt. Ein händisch nachgeführtes Protokoll
  ist nach drei Wochen gelogen.
- **Jede Zeile trägt ihre Quelle** (= B). Im Kundengespräch auf eine Aussage
  zeigen und in zwei Klicks bei der Mail vom 14. März landen.
- **Auf jeden Stichtag berechenbar.** "Wie sah das Protokoll aus, als wir
  den Change Request verhandelt haben?" ist eine Abfrage, keine Archäologie.

**Zentrale Beobachtung: Audit-Anforderung und Nutzen sind dasselbe Feature.**
Hash-Kette, Quellenangaben und Kundenprotokoll sind drei Blickwinkel auf
eine Datenstruktur. Nicht kaputtmachen.

### Kein Detail: Bearbeitbarkeit

Eine Korrektur am Protokoll ist selbst ein **Korrektur-Event**, append-only
wie alles andere. Sie überschreibt nie die Quelle, tritt daneben und gewinnt
in der Projektion. Spur bleibt intakt, Jens behält das letzte Wort.

### Folge für Frage 4

"Protokoll pro Kunde" macht **Kunde** zu einer erstklassigen Entität.
OpenProject modelliert Projekte, aber kein Kundenobjekt — das verschärft
die System-of-Record-Frage.

## System of Record (Frage 4): B, mit Konsequenzen

Jens: "OpenProject etc. ist Inbox oder Artefakt, aber auch B — wir wollen
immer die Wahrheit. Ich möchte mich aber nicht an eine Technologie binden.
Wenn plötzlich was Besseres als OpenProject kommt, muss das austauschbar sein."

### Inbox *und* Artefakt = ein Konnektor mit zwei Richtungen

              KERN: Event-Store + Kernmodell   <- die Wahrheit
                |  Projektion         ^ Events
                v  (rendern)          | (aufnehmen)
              Konnektor: OpenProject

**Derselbe Mechanismus wie beim Kundenprotokoll.** Das Protokoll ist eine
Projektion, gerendert als Text. Ein Work Item ist eine Projektion, gerendert
als Work Item. Ein Konnektor ist nichts Besonderes.

Damit löst sich das Sync-Problem, das B normalerweise hat: **eine Änderung
direkt in OpenProject ist ein Korrektur-Event** — dieselbe Mechanik wie die
Protokoll-Bearbeitung. Fließt rein, Wahrheit im Kern aktualisiert sich,
nächstes Rendern ist ein No-Op. Kein Konflikt-Dialog, keine Sync-Richtung.
Eine Mechanik, überall.

Zu prüfen pro System: abfragbarer Änderungs-Strom. OpenProject (Activities),
GitLab (Webhooks/Events), Nextcloud (Activity) haben alle etwas in der
Richtung — keiner ist eine Blackbox.

### Austauschbarkeit: Regel und Test

**Regel: Das Kernmodell darf nichts enthalten, was tool-förmig ist.**

Test für jedes Feld: *Würde es noch Sinn ergeben, wenn OpenProject nicht
existierte?* Wenn nein -> Adapter, nicht Kern. Kein `work_package_type`,
keine OpenProject-Status-IDs, keine GitLab-Label-Semantik im Kern.

Das Kernmodell kommt aus **der Domäne**: Kunde, Projekt, Verpflichtung,
Frist, Entscheidung, Aussage. Adapter übersetzen.

Hier sterben solche Systeme normalerweise: man übernimmt beim ersten
Konnektor dessen Datenmodell, weil es bequem ist, und ist gebunden, ohne es
zu merken.

**Test: Austauschbarkeit ist genau dann wahr, wenn das Zielsystem
weggeworfen und aus dem Kern neu erzeugt werden kann.**

Abnahmebedingung, keine Hoffnung: leere OpenProject-Instanz, Renderer
drüberlaufen lassen, alles wieder da. Was *nicht* wiederherstellbar ist,
zeigt präzise, wo die Bindung sitzt — jetzt, nicht in drei Jahren.
**Als automatisierten Test bauen, nicht als Vorsatz.**

## Kundeninfrastruktur — die Rahmenbedingung, die alles schärft

Jens: "Wir versuchen gerade alles auf OpenProject zu schieben. Aber es ist je
nach Kunde nicht möglich, da wir auch **kooperatives Projektmanagement**
machen und **in Kundeninfrastruktur arbeiten** müssen. Ein GitLab des Kunden
geht per API-Key, bei einem JIRA würde es schwieriger. Wir müssen flexibel sein."

### Warum B damit zwingend ist, nicht nur bevorzugt

Wenn das PM-System je nach Kunde ein anderes ist, **kann** keines davon die
Wahrheit halten — es gibt keins, das alle Kunden kennt. Der Kern ist nicht
der bequemste Ort für die Wahrheit, sondern der einzige mögliche.

Die Regel "Kernmodell darf nichts Tool-förmiges enthalten" ist damit tragend,
nicht Hygiene: ein OpenProject-förmiger Kern wäre bei jedem Kunden-JIRA ein
Übersetzungsdrama.

### Neue Eigenschaft: verlustbehaftetes Rendern ist erlaubt

**Weil der Kern die Wahrheit hält, darf das Rendern verlustbehaftet sein.**
Ein schwaches Zielsystem zeigt weniger — eine "Verpflichtung mit Frist"
landet im Kunden-JIRA als Issue mit Label, die Nuance bleibt im Kern. Wäre
OpenProject die Wahrheit, wäre Verlust beim Rendern *Datenverlust*; so ist er
nur Darstellungsverlust. **Deshalb ist eine heterogene Kundenlandschaft
überlebbar.**

### Konnektoren haben Fähigkeitsstufen

| Stufe | Beispiel | Was geht |
|---|---|---|
| **beidseitig** | eigenes OpenProject, Kunden-GitLab mit API-Key | Events rein, Rendern raus |
| **nur lesend** | API-Key ohne Schreibrechte; Kunde erlaubt keine Writes | Events rein, kein Rendern |
| **gar keine API** | Kunde will nicht, Altsystem, Freigabe dauert Monate | siehe unten |

### Fund: IMAP ist der universelle Notfall-Konnektor

JIRA schickt Benachrichtigungsmails. Confluence auch. Teams auch. Fast jedes
System kann Mail. Ein Kundensystem ohne API-Zugriff redet trotzdem mit uns —
seine Events kommen als Mail und sind damit im Kern. Nicht schön, aber
vollständig genug für Verlauf und Protokoll.

Verschiebt den Aufwand für die vielen Einzelsysteme von "N Integrationen"
auf "N Mail-Parser",
und einen Mail-Parser kann die KI schreiben. Für Stufe 3 der Unterschied
zwischen unmöglich und mühsam.

**Folge: der Mail-Konnektor muss sehr gut sein.** Er ist nicht eine Inbox von
vielen, er ist das Auffangbecken für alles Nicht-Integrierbare.

### JIRA konkret

Technisch weniger schlimm als der Ruf: Jira Cloud nimmt E-Mail + API-Token
(Basic Auth), Data Center nimmt Personal Access Tokens. Das Problem ist
**organisatorisch**: der Token hängt an einem Benutzerkonto mit dessen
Rechten, der Kunden-Admin muss Token-Erstellung erlauben, und Jiras
Feldmodell (kryptische Custom-Field-IDs) ist beim Mappen unangenehm.

Also: nicht "schwieriger zu bauen", sondern "schwieriger zu bekommen" —
eine Freigabe-Frage an den Kunden, kein Entwicklungsrisiko.

### Neues Objekt: Kundenprofil

Vier Dinge, die alle pro Kunde variieren, an einer Stelle:

- **welche Systeme** (eigenes OpenProject / deren GitLab / deren JIRA / nur Mail)
- **Zugangsdaten** je System, mit Fähigkeitsstufe
- **Datenpolitik** — darf Inhalt dieses Kunden in die Cloud? (= die Naht aus
  Frage 2)
- **Freigabeklassen** — was darf bei diesem Kunden automatisch laufen

Policy-Gate, Konnektor-Lader und Freigabe-Queue lesen alle dort.

### Ehrliche Konsequenz zur Naht aus Frage 2

Die Naht wird früher gebraucht als gedacht. Ein Kunde, der sein GitLab selbst
hostet, hat das aus einem Grund getan — die Chance, dass derselbe Kunde "nein"
zu Anthropic sagt, ist nicht klein. "A derzeit" bleibt richtig, aber die
Policy-Schicht enthält im ersten Jahr echte Regeln, nicht nur `return CLOUD_OK`.

## MVP-Schnitt (Frage 5): A + manueller Einwurf

### Der Mensch ist ein erstklassiger Konnektor, kein Notausgang

PDFs in einen Ordner, Chat-Text in einen Prompt, eine Issue-URL nennen —
drei Einwurfpfade, die ab Tag eins **jede Quelle auf der Welt** abdecken.
Kein JIRA-Token, keine Kundenfreigabe, kein Wartezyklus.

**Bauordnung: der manuelle Einwurf ist die Referenzimplementierung des
Konnektor-Vertrags.** Jeder automatische Konnektor ist danach die
Automatisierung eines Pfades, der schon funktioniert. Umgekehrt (erst IMAP,
dann manuell) bekommt man einen Vertrag, der nach Mail aussieht.

**Bootstrap für das größte Risiko:** Beim manuellen Einwurf sagt Jens die
Zuordnung mit — das ist **Grundwahrheit**. Risiko 1 ("erkennt die KI, zu
welchem Kunden das gehört?") ist bei IMAP eine Hoffnung, beim manuellen
Einwurf eine bekannte Antwort. Der Datensatz zum Messen und Verbessern der
automatischen Zuordnung entsteht beim normalen Arbeiten.

### Die vier Einwurfpfade

| Pfad | Zuordnung | Anmerkung |
|---|---|---|
| **IMAP** | geraten (= das Risiko) | automatisch, kontinuierlich |
| **Drop-Ordner** | aus Unterordner = Kunde | am besten ein **Nextcloud**-Ordner — geht auch vom Handy, ist schon da |
| **Einwurf per Prompt** | Jens sagt sie | hier landet später die **Spracheingabe** — derselbe Pfad, anderes Eingabegerät |
| **Quelle verlinken** | Jens sagt sie | GitLab-/GitHub-Issue-URL, System holt und hält nach. Billiger als ein Abo-Konnektor |

Drop-Ordner braucht Textextraktion, bei Scans OCR — lokal, kostenlos.

### Teil 5 fällt aus dem MVP: Claude Code ist die Oberfläche

Der MCP-Server bekommt Schreib-Werkzeuge. Einwurf, Freigabe-Queue auflisten,
abnehmen, Protokoll rendern — alles MCP-Werkzeuge. Kein Formular, keine
Web-App im MVP.

    MVP                                     verschoben
    ---                                     ----------
    Teil 1  IMAP + 3 manuelle Pfade         Teil 2  Voice
    Teil 3  Kern (Event-Store, Hash-Kette,  Teil 5  eigene Oberfläche
            Kernmodell, Identitätsgraph,
            Projektionen, Kundenprotokoll)
    Teil 4  Gate + Retrieval + Templates
    ------------------------------------
    + MCP-Server als einzige Schnittstelle

Voice bleibt Teil 2 mit festem Platz; eigene Oberfläche, wenn Claude Code
als Cockpit nicht mehr reicht oder Kolleg:innen dazukommen.

## Bestandsimport — ein Feature, kein Skript

Pilotkunde ist "seit längerem aktiv" → **Projektkontext muss importiert
werden.** Passiert pro Kunde bei jedem Onboarding, also eigene Mechanik.

### Zwei Zeitstempel pro Event (technischer Kern)

| Feld | Bedeutung |
|---|---|
| `ereignis_zeit` | wann es wirklich passierte — die Mail ist vom März 2024 |
| `erfasst_am` | wann es in den Store kam — heute |

Ohne die Trennung bricht beides aus Frage 3: die **Hash-Kette** ist nach
Einfügereihenfolge geordnet (muss sie sein, sonst ist sie keine Kette), das
**Protokoll** nach Ereigniszeit (muss es sein, sonst ist es keine Chronik).
Zwei Ordnungen über denselben Daten, beide nötig.

Nebeneffekt: "Was wusste ich am 14. März?" hat zwei Bedeutungen — *was war
bis dahin passiert* (Ereigniszeit) und *was stand damals im Store*
(Erfassungszeit). Mit zwei Zeitstempeln beide Antworten, mit einem keine
zuverlässig.

### Import ist nicht Triage

- **Import** extrahiert und legt ab: Verpflichtungen, Fristen,
  Entscheidungen, Aussagen landen im Kern. Protokoll wird vollständig.
- **Vorschläge** nur in einem eigenen, ausgelösten Durchgang, gebündelt
  durchgesehen.

Sonst: 500 veraltete Todo-Vorschläge, die niemand anschaut. Die offene Frage
von vor vier Monaten will man finden — aber als bewussten Durchgang "zeig
mir, was aus der Historie noch offen ist".

**Batch API passt perfekt:** 50 % Rabatt, asynchron, beim Bestandsimport ist
nichts zeitkritisch.

### Der Import darf unsicher sein

Zwei Jahre Historie = zwei Jahre Unschärfe (verschobene Projektgrenzen,
Umbenennungen, gewanderte Themen). **Weil alles eine Projektion ist, wird
neu gerechnet, wenn die Struktur besser verstanden ist.** Der Import muss
nicht korrekt sein, nur **vollständig**. Druckabbau, erkauft durch die
append-only-Entscheidung.

### Der erste Import ist die Abnahmeprüfung des Kernmodells

Geht beim Import von OpenProject-Projektkontext etwas Wesentliches verloren,
ist das **Kernmodell** falsch, nicht der Import. Die Austauschbarkeits-Regel
aus Frage 4 wird hier erstmals scharf geprüft — an echten Daten, früh.

Quellen für den Import = genau die vier Einwurfpfade (Mailhistorie,
OpenProject-Projekt, Issues per URL, Angebote/Protokolle als PDF).
**Keine neue Maschinerie nötig** — gutes Zeichen für den MVP-Schnitt.

## Datenbank: aufgeschoben, Kriterien festgehalten

Jens: "Technologie sollte vor allem passen und sich nicht so sehr an dem
orientieren, was ich kann. Datenbank für solche Daten — das wäre eine
Recherche wert, muss aber nicht zu Beginn definiert werden."

**Richtig, und konsequent:** dieselbe Regel wie bei OpenProject. Der Kern
kennt keine Datenbank, der Speicher-Adapter kennt eine. Die
Produktentscheidung ist "append-only Event-Log + Projektionen +
Vektorsuche" — eine Form, kein Hersteller.

### Was aber jetzt feststeht, weil nachträglich unmöglich

**Die append-only-Disziplin, nicht die Engine.** Wenn das Log append-only
ist, zwei Zeitstempel hat, eine Hash-Kette trägt und alle Projektionen
jederzeit neu berechenbar sind, ist ein Engine-Wechsel ein Re-Import.
Werden Projektionen irgendwann zu primären Daten (veränderliche Zeilen, die
niemand mehr herstellen kann), sitzt man fest — unabhängig von der Engine.

**Warnung:** Speicher-Abstraktionen lecken. Nicht spekulativ zwei Backends
bauen (= kleinster gemeinsamer Nenner). Ein Backend, hinter einer **schmalen**
Schnittstelle, und die Schmalheit wird verteidigt.

### Recherche-Auftrag: die drei Kriterien

Vorweg: **das Datenvolumen ist klein.** 150 Mails/Tag über 5 Jahre
= ~275.000 Mails; mit Transkripten und Chats einstellige Millionen Events,
zweistellige Gigabytes Text. Eine Maschine. Keine Datenplattform. Bei der
Größe funktioniert praktisch jede Engine — die Wahl ist weniger riskant,
als sie sich anfühlt. Deshalb entscheiden nicht Durchsatzfragen, sondern:

1. **Vektorsuche mit Vorfilter.** "Ähnliche Passagen, aber nur Kunde X, nur
   vor dem 14. März." Manche Engines filtern erst *nach* der Suche nach und
   liefern dann zu wenige Treffer.
2. **Deutsche Volltextsuche.** Unterschätzt und hier zentral:
   Snowball-Stemming kommt mit **Komposita** nicht zurecht — wer
   "Vergaberecht" sucht, findet "Recht der Vergabe" nicht.
3. **Reprojektions-Geschwindigkeit.** Alle Events eines Kunden lesen und neu
   rechnen. Die Schnittstelle muss das als **Stream** hergeben, nicht alles
   in den Speicher ziehen.

## Voice: Voxtral, und das größere Problem

Hinweis von dritter Seite: es gibt offene Mistral-Modelle zur Spracherkennung.

**Voxtral** (Mistral, Apache 2.0, ~3B und ~24B) — anders als Whisper: nicht
nur Transkription, sondern Audio-Verstehen (anpromptbar, Fragen zur
Aufnahme, Funktionsaufrufe aus Sprache). **Wissensstand möglicherweise
veraltet, zu prüfen.**

**Die entscheidende offene Frage: macht es Diarisation?** Stabile
Sprecherzuordnung über eine zweistündige Aufnahme. Audio-LLMs sind darin
traditionell schwach. Wenn nein, bleibt `pyannote` und das Python-Argument
steht. Wenn ja, ändert sich Teil 2 erheblich.

**Hardware:** 24B ist auf dem i7 ohne GPU keine Option, 3B zäh für 2 h
Audio/Tag. whisper.cpp (mittlere Größe) auf 8 Threads ist praktikabel.
Also lokal nicht realistisch — **über OpenRouter testen**: Voxtral und
Whisper über dieselben zehn echten Calls, dann entscheiden.

### Audio ist die heikelste Datenart im System

Sensibler als jede Mail. Whisper lokal = Audio verlässt die Maschine nie.
Voxtral über API = ein Kundengespräch geht an einen Dritten. Ein Kunde, der
bei Mails zustimmt, muss bei Gesprächsaufnahmen nicht zustimmen.

**Zwei Entwurfskonsequenzen:**

1. **Transkribieren, Audio nicht aufbewahren.** Der Nutzen steckt im
   Transkript; Verwerfen senkt die Exposition drastisch und kostet fast nichts.
2. **Aufnahme-Einwilligung gehört ins Kundenprofil**, neben Datenpolitik und
   Freigabeklassen.

**Rechtsfrage vor dem Bau klären** (keine Rechtsauskunft): Mitschnitt
nicht-öffentlicher Gespräche in Österreich — vermutlich § 120 StGB; DSGVO
braucht Rechtsgrundlage und Transparenz gegenüber allen Beteiligten.
Praktisch: Ansage am Call-Beginn, Einwilligung pro Kunde hinterlegt, ohne
Einwilligung läuft der Abgriff nicht.

**Erste Aufgabe in Teil 2 ist damit nicht "PipeWire abgreifen", sondern
"Einwilligung modellieren".**

## KERNMODELL

Stand nach Jens' Korrekturen. Noch nicht endgültig bestätigt.

### Schicht 1: Event-Log — die einzige Wahrheit

Append-only. Jedes Event:

| Feld | Zweck |
|---|---|
| `id`, `hash`, `vorgaenger_hash` | die Kette aus Frage 3 |
| `erfasst_am` / `ereignis_zeit` | die zwei Ordnungen (Bestandsimport) |
| `quelle` | welcher Pfad (imap/drop/prompt/link/openproject …) **plus quellennative ID** — dagegen läuft die Idempotenz |
| `beteiligte Kanalidentitäten` | für die Teilnehmerregel |
| `inhalt` | |

**KORRIGIERT:** `zuordnung` und `klassifikation` sind **nicht** Felder am
Event — siehe Abschnitt "Zerlegung" unten. Sie sind Feststellungen.

`zuordnung.herkunft` ∈ **`mensch` | `regel` | `modell`**.
Bei Konflikt: **Mensch schlägt Regel schlägt Modell.**
Das ist der Bootstrap aus Frage 5 hart im Modell — "wie gut rät das System?"
wird eine SQL-Abfrage über die eigene Arbeit, kein Evaluierungsprojekt.

### Drei Event-Arten (die wichtigste Entscheidung)

| Art | Was | Wer erzeugt sie |
|---|---|---|
| **Wahrnehmung** | Mail kam an, Transkriptabschnitt, Datei eingeworfen, Issue geändert | Konnektoren. **Nie die KI.** |
| **Feststellung** | "ist Verpflichtung mit Frist 30.4." / "gehört zu Auftraggeber A" / "Kunde hat Y entschieden" | KI **oder** Jens |
| **Handlung** | "GitLab-Issue #42 angelegt", "Mail versendet" — mit welcher Freigabe | die Freigabe-Schicht |

- **Wahrnehmungen können nicht falsch sein** — sie behaupten nur, dass etwas
  ankam. Nie gelöscht, nie korrigiert.
- **Feststellungen können falsch sein.** Neuere überschreibt ältere ohne
  Löschung. **Jens' Korrektur am Protokoll ist einfach eine Feststellung mit
  `herkunft: mensch`** — kein Sonderfall, kein eigener Mechanismus.
- **Nur Feststellungen kommen aus der KI.** "Was hat das Modell je behauptet,
  worauf gestützt?" ist eine Abfrage über eine Event-Art = C aus Frage 3
  ohne Zusatzaufwand.

Protokoll = Projektion über Wahrnehmungen + geltende Feststellungen.
Audit-Log = Projektion über Handlungen + begründende Feststellungen.
**Zwei Sichten, eine Datenstruktur.**

### DER WICHTIGSTE FUND: Teilnehmermenge als Primärklassifikator

Jens' Discord-Beispiel: generelle Rooms, 10:00 projekt-b-Meeting mit Alex,
11:00 Auftraggeber A-Meeting mit Alex. Unterschied ist, **wer noch dabei ist.**

    Discord #general, 10:00-10:45
      anwesend: Jens, Alex, [Kundenperson projekt-b]
      -> Schnittmenge der Projekt-Beteiligungen: { projekt-b }
      -> Zuordnung: projekt-b, herkunft: regel, sicher

    Discord #general, 11:00-12:00
      anwesend: Jens, Alex, [Kundenperson Auftraggeber A] x2
      -> Schnittmenge: { auftraggeber-a }
      -> Zuordnung: auftraggeber-a, herkunft: regel, sicher

**Regel: schneide die Projekt-Beteiligungen aller Anwesenden; bleibt genau
eines übrig, ist es das.** Deterministisch, auditierbar, kostenlos, kein
Modell kann es falsch machen. Alex trägt nichts zur Unterscheidung bei —
die Kundenpersonen tragen alles.

**Zweistufig: billige Regel zuerst, KI nur für den Rest** (wenn mehr als ein
Projekt übrig bleibt).

Gilt überall: bei Mail der Empfängerkreis/CC (oft besser als der Betreff),
bei Voice die erkannten Sprecher, bei Discord die Anwesenden im Zeitfenster.

**Zwei Folgen:**

1. **Risiko 1 (Zuordnung) ist kleiner als gedacht** — der stärkste Hinweis
   ist strukturell, nicht semantisch. Großteils eine Mengenoperation.
2. **Der Identitätsgraph ist nicht Hausarbeit, er ist der Motor.** Rückt im
   MVP von "nice to have" auf "zuerst richtig machen".

### Schicht 2: Neun Entitäten (alle Projektionen, keine Wahrheitstabellen)

| # | Entität | Anmerkung |
|---|---------|-----------|
| 1 | **Kunde** | lebt im Kern, kein Fremdsystem kennt ihn |
| 2 | **Projekt** | muss verschobene Grenzen/Umbenennungen aushalten (Import) |
| 3 | **Person** | |
| 4 | **Kanalidentität** | eigenständig: eine unbekannte Mailadresse ist eine Identität **ohne** Person — das ist der Zustand "unsortiert" |
| 5 | **Beteiligung** | NEU — Person × (Projekt **oder** Aufgabe) × Rolle × Zeitraum |
| 6 | **Vorgang** | unscharf: vorgeschlagen, korrigierbar, **nie autoritativ** |
| 7 | **Verpflichtung** | mit **Richtung** und Art (`lieferung`, `antwort`, …); Schuldner darf **leer** sein |
| 8 | **Aufgabe** | NEU — ausführbare Arbeit, trägt die PM-Verknüpfung |
| 9 | **Entscheidung** | |
| — | ~~Frage~~ | aufgelöst in Verpflichtung mit `art: antwort` |

Tool-Form-Test: alle neun überleben ohne OpenProject. Einziger Ort mit
Werkzeugnamen ist die Verknüpfung an der Aufgabe — laut Frage 4 genau dort.

#### Beteiligung: Rolle ist eine Beziehung, keine Eigenschaft

Jens' Korrektur. Eine Person kann Mitarbeiter, Partner, Freelancer **oder**
Kundenperson sein, und gleichzeitig an zwei oder mehr Projekten arbeiten.

- Alex = *Freelancer bei projekt-b* **und** *Freelancer bei Auftraggeber A*: zwei
  Beteiligungen, nicht zwei Rollen an einer Person.
- "an Tasks runterbrechen": dieselbe Relation zeigt auf Projekt **oder**
  Aufgabe. Grob und fein sind kein Modellunterschied, nur ein Zielunterschied.
- "das kann sich verschieben": der Zeitraum fällt gratis an, weil Beteiligung
  eine Projektion über Feststellungen mit Ereigniszeit ist. "Wer war im März
  2024 beteiligt?" = dieselbe Abfrage, anderer Stichtag.

Rollen: `mitarbeiter`, `partner`, `freelancer`, `kundenperson`. Die Rolle
macht die Zuordnungsregel auswertbar — **Kundenpersonen diskriminieren stark,
eigene Leute kaum.**

#### Verpflichtung vs. Aufgabe

| | |
|---|---|
| **Verpflichtung** | der Sachverhalt: "Wir schulden Auftraggeber A den Bericht bis 30.4." Richtung, Frist, Zustand. |
| **Aufgabe** | die ausführbare Arbeit: "Kapitel 3 schreiben". Bearbeiter (über Beteiligung), Zustand. |

Eine Verpflichtung erzeugt 0..n Aufgaben. Eine Aufgabe kann ohne
Verpflichtung existieren (interne Arbeit). **Eine Verpflichtung *des Kunden*
erzeugt keine Aufgabe bei uns, muss aber im Protokoll stehen und überfällig
werden können** — bei zusammengelegter Entität wäre das kaputt.

PM-Verknüpfung (OpenProject WP #123, GitLab #42, JIRA-Key) hängt an der
**Aufgabe** und lebt in der Adapter-Abbildung. Jens' "je nach PM-Art" ist
damit die Adaptersache aus Frage 4. **Binden** (auf existierenden Task
zeigen) und **generieren** (neu anlegen) sind dieselbe Verknüpfung.

#### Frage → Verpflichtung

Jens: "Fragen sind aber auch immer eine Verpflichtung sie zu beantworten oder?"
Ja. Eine adressierte Frage **ist** eine Verpflichtung (Schuldner, Frist,
Zustand, gleiche Form).

Ausnahme: die **unadressierte** Frage ("weiß jemand, ob die Messdaten
georeferenziert sind?"). Kein Schuldner. Lösung ohne neue Entität:
`art: antwort` + `schuldner: null` — "das muss jemand beantworten, wir wissen
noch nicht wer". Genau die "offene Frage von vor vier Monaten".

#### Vorgang — Definition

**Eine zusammenhängende Klärung oder Abwicklung mit erkennbarem Anlass und
erkennbarem Abschluss.** Beispiele: "Change Request Datenmodell", "Angebot
Phase 2", "Exportfehler vom 14.3." Feiner als ein Projekt, grober als ein Event.

Technisch: ein Bündel von Events, angesetzt an harten Signalen
(Mail-Thread-Header, Issue-Referenzen, Nummernverweise), vom Modell
erweitert, von Jens korrigierbar.

**Ehrlich: die einzige Entität mit unscharfer Grenze.** Die anderen haben
klare Identitätskriterien. Deshalb nie autoritativ. Das Protokoll
funktioniert ohne ihn (Chronik + Verpflichtungen + Entscheidungen); der
Vorgang macht es besser. Im MVP mitbauen, aber nichts davon abhängig machen,
dass er gut ist.

### Schicht 3: Kundenprofil

Systeme, Zugangsdaten mit Fähigkeitsstufe, Datenpolitik, Freigabeklassen,
**Aufnahme-Einwilligung**. Alles, was pro Kunde variiert, an einer Stelle.

### Protokollform

    KUNDE AUFTRAGGEBER A — Stand 1. Oktober 2026

    Offen von uns          3 Verpflichtungen, davon 1 überfällig
    Offen vom Kunden       2 Verpflichtungen, 1 unbeantwortete Frage (4 Mon.)
    Letzte Entscheidungen  3

    -- Chronik (Ereigniszeit) --------------------------
    2024-03-14  Kickoff-Call. Entscheidung: Datenmodell
                nach Variante B.              [T-0231, M-0442]
    2024-03-18  Kunde sagt Messdaten bis Ende März zu.  [M-0455]

Jede Zeile trägt ihre Event-IDs (= B aus Frage 3). Der Kopf ist keine
Zusammenfassung, sondern eine Abfrage über Verpflichtungen und Fragen.

## ZERLEGUNG — ein Event kann nicht *eine* Zuordnung haben

Jens: "Ein E-Mail eines Kunden kann tatsächlich auch mehrere Vorgänge
betreffen (der schickt ja selten ein E-Mail für einen Vorgang), das muss
zerlegt werden. Genau wie bei Besprechungen — da hat man ein Transkript und
dann wird da ganz viel Verschiedenes besprochen."

Und: "**Ein Vorgang ist das, was mich inhaltlich klammert**" — und er ist
"Dreh- und Angelpunkt für den Zugang zu den Infos später".

### Die Einheit der Zuordnung ist nicht das Event, sondern ein Abschnitt

**Die Zerlegung ist eine Feststellung, keine Wahrnehmung.** Die Mail ist eine
Mail — Wahrnehmung, kann nicht falsch sein. "Absatz 2-4 gehören zum Change
Request, Absatz 5 zur Rechnung" ist eine **Interpretation** und kann falsch sein.

Früherer Fehler im Modell: `zuordnung` und `klassifikation` hingen am Event.
Das war inkonsistent mit dem eigenen Grundsatz "Wahrnehmungen können nicht
falsch sein" — Fehlbares lag im Unfehlbaren. **Beide wandern raus.**

    Wahrnehmung
      id, hash, vorgaenger_hash
      erfasst_am, ereignis_zeit
      quelle + quellennative ID        (Idempotenz)
      beteiligte Kanalidentitäten      (für die Teilnehmerregel)
      inhalt

    Feststellung · art: zuordnung
      ziel      event-id + spanne
      spanne    { art: zeichen | zeit | seite, von, bis }
      kunde, projekt, vorgang
      herkunft  mensch | regel | modell
      sicherheit

Spanne ist medienabhängig: **Zeichenbereiche** in Mail, **Zeitbereiche** im
Transkript (Themenwechsel bei 00:34:12), **Seiten** im PDF, Kommentare als
eigene Abschnitte beim Issue.

### Was das gewinnt

- Einfache Mail = eine Zuordnungs-Feststellung über die ganze Spanne.
  Komplexe Mail = drei. **Kein Sonderfall**, dieselbe Struktur.
- Teilnehmerregel liefert eine Feststellung (`herkunft: regel`) über das
  ganze Event; das Modell verfeinert danach in Abschnitte. Zwei Stufen,
  ein Mechanismus.
- **Regel 2 aus Frage 2 ist besser erfüllt:** Neuklassifizieren ist eine
  *neue Feststellung*, keine Mutation — genau das, was die Regel wollte.
- "Wie gut rät das System?" wird präziser: Feststellungen mit
  `herkunft: regel`/`modell` gegen spätere mit `herkunft: mensch`
  **über derselben Spanne**. Treffergenauigkeit pro Abschnitt, nicht pro Mail.

### Die Zerlegung ist die wertvollste KI-Operation im System

Ein 2h-Transkript ist als Klumpen wertlos und als zwölf Abschnitte auf fünf
Vorgänge verteilt Gold. **Dort wird der Dschungel gelichtet** — nicht beim
Einsortieren von Mails.

Kosten unkritisch: ~30k Tokens, passt in Haikus Kontext, ein Aufruf pro
Besprechung. Bei Mails lohnt ein billiger Vorlauf, der "ein Thema" erkennt
und die Zerlegung überspringt (dürfte die Mehrheit sein).

### Protokoll ist eine Familie, nicht eine Form

Der Vorgang ist die **Abrufeinheit**. "Zeig mir alles zum Change Request" =
alle Abschnitte dieses Vorgangs, über Mail, Transkript, Chat und Issues
hinweg, in Ereigniszeit-Ordnung.

**Kundenprotokoll · Projektprotokoll · Vorgangsprotokoll — eine Maschine,
drei Zuschnitte.** Der Vorgang bekommt seine Ansicht gratis.

Vorgang hängt an einem Kunden, kann mehrere Projekte berühren.

### Korrektur der früheren Einschätzung

Vorher notiert: "Vorgang mitbauen, aber nichts davon abhängig machen." Falsch
gewichtet — Jens sagt, er ist die primäre Zugangsebene, also tragend.

Auflösung des scheinbaren Widerspruchs: **Unschärfe ist für einen Zugangsweg
unschädlich und nur für Autorität tödlich.** Man muss die Klammer nicht
perfekt setzen, um etwas zu finden. Falsch wäre nur, eine Rechnung oder eine
Frist von der Vorgangsgrenze abhängig zu machen.

**Zentral als Zugang, nie autoritativ für Fakten.** Beides gleichzeitig wahr.

## Bestätigt von Jens (Kernmodell)

1. **Beteiligung** als eigene Relation — ja
2. **Aufgabe** als eigene Entität — ja ("sonst sind wir zu wenig konkret")
3. **Frage** aufgelöst in `Verpflichtung{art: antwort}` — ja
4. **Vorgang** vorgeschlagen/korrigierbar — ja, **und** Dreh- und Angelpunkt
   für den Zugang

## KORREKTUR: "Kunde" ist keine Entität, sondern eine Rolle

Jens: "Der Kunde kommt ja von mir. Aber brauchen wir ihn überhaupt als
Entität? Als 'Beteiligte Organisationen'. Weil darum geht es oft. Ein Projekt
hat eine Designagentur mit Personen, einen Auftraggeber (aka Kunde), eine
Hostingfirma und dann Projektpartner unserer BlueDynamics Alliance. Eine Person
kann auch einmal Kunde sein (z.B. Mirko bekommt einen Auftrag und wir arbeiten
als Subunternehmer) — Mirko ist aber Partner in der BlueDynamics Alliance wie
wir. Nächstes Mal arbeite ich mit ihm als ARGE an einem grossen Projekt. **Das
ist nicht hypothetisch, sondern durchaus was wir die letzten 20 Jahre gelebt
haben.**"

### Derselbe Fehler zum zweiten Mal

Rolle als Eigenschaft statt als Beziehung — erst bei Person (von Jens
korrigiert), dann bei "Kunde" als Entitätsart. Zweimal ist ein Muster, nicht
ein Versehen. Daher **Leitsatz 7: Rollen sind immer Beziehungen, nie
Eigenschaften.** Prüffrage: *Könnte das im nächsten Projekt anders sein?*

### Änderungen

- `Kunde` → **`Organisation`** mit `art: firma | einzelperson | verein |
  behörde`. Die eigene trägt `eigene`. `einzelperson` darf auf eine `Person`
  verweisen, ohne den Menschen mit seiner Gesellschaft zu verwechseln.
- **`Beteiligung` wird über Akteure verallgemeinert**: Akteur (Person *oder*
  Organisation) × Ziel × Rolle × Zeitraum. Eine Relation, nicht zwei — damit
  es *einen* Ort für Rollen gibt. Preis: Organisationsbeteiligung geht
  praktisch nie auf Aufgabenebene, die Relation wird ungleichmäßig genutzt.
- Rollenvokabular **erweiterbar, nicht abgeschlossen**. Organisation:
  `auftraggeber`, `auftragnehmer`, `subunternehmer`, `arge-partner`,
  `allianzpartner`, `dienstleister`. Person: `mitarbeiter`, `partner`,
  `freelancer`, `ansprechpartner`.

### Der eigentliche Gewinn: drei Fälle statt zwei

Verpflichtung bekommt **Schuldner und Gläubiger als Akteure** statt einer
binären Richtung:

| Schuldner | Folge |
|---|---|
| eigene Organisation | erzeugt Aufgaben |
| ein anderer, Gläubiger sind wir | keine Aufgabe, wird überfällig, sichtbar |
| **zwei andere, uns betreffend** | **beobachtet** — wir treiben es, ohne Partei zu sein |

> "Die Hostingfirma schuldet der Designagentur die DNS-Umstellung — und das
> blockiert uns."

Der dritte Fall ist kooperatives Projektmanagement in Reinform und war vorher
nicht ausdrückbar. Ketten ebenso: `wir → Subunternehmer-Auftraggeber →
Endauftraggeber`.

### Drei Folgewirkungen

**Teilnehmerregel wird besser.** Alt: "Kundenpersonen diskriminieren stark,
eigene Leute kaum." Das war ein Behelf. Neu: **Unterscheidungskraft ist
umgekehrt proportional zur Zahl der Projekte, in denen ein Akteur beteiligt
ist.** Gilt für Personen *und* Organisationen. Eigene Leute sind nur deshalb
schwach, weil sie in vielen Projekten stecken — nicht weil sie eigene sind.

**Kundenprofil → Organisationsprofil, mit Auflösung.** Ein Projekt hat mehrere
beteiligte Organisationen, jede bringt ein Profil mit. Es gilt **die strengste
Festlegung** — daher **Leitsatz 8**. Datenpolitik: sagt eine `nur_lokal`, gilt
das für alles im Projekt. Aufnahme: nur wenn *jede* anwesende Organisation
zugestimmt hat. Zugangsdaten werden **nicht** aufgelöst — das GitLab der einen
öffnet man nicht mit dem Schlüssel der anderen.

**Organisationsprotokoll statt Kundenprotokoll.** "Alles mit Mirko" über alle
Projekte und Rollen — nach Rolle filterbar, nicht nach Rolle zerschnitten.
Nach 20 Jahren vermutlich die häufiger gebrauchte Ansicht.
