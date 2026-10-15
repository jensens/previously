# Landkarte und offene Punkte

> **Gepflegtes Dokument, nicht eingefroren.** Die Specs unter `specs/` und die
> Protokolle unter `sdd/` halten fest, was an einem Tag entschieden wurde, und
> ändern sich danach nicht mehr. Dieses Dokument ist das Gegenstück: es sagt,
> wo das Projekt **heute** steht, was als Nächstes kommt und wo jeder offene
> Punkt wohnt. Wer einen Spec einfriert, trägt dessen offene Punkte hierher;
> wer einen Punkt schließt, streicht ihn hier und nennt den Commit.
>
> Angelegt am 2026-10-04 mit dem
> [Prüfpunkt nach Teilprojekt 1](sdd/2026-10-04-pruefpunkt-teilprojekt-1/index.md),
> der die Belege zu allem trägt, was hier ohne Begründung steht.

## Wo das Projekt steht

Gebaut und abgenommen, auf `main`:

| Stufe | Inhalt | Spec | Abnahme |
|---|---|---|---|
| 1a | Der Log: `event`, `unit`, `source_key`, Hash-Kette, `append`, `verify` | `specs/2026-10-02-stufe-1a-log.md` | Merge vom 2026-10-03 |
| 1b | Projektionen: Arbeiter, `p_chronicle`, `p_source_stats`, `project`, `chronicle`, `stats` | `specs/2026-10-04-stufe-1b-projektionen.md` | PR #1, `b0396b6` |
| — | Der äußere Anker: `anchor`, `verify --anchors [--exact]`, `examine` in einem Schnappschuss | `specs/2026-10-04-aeusserer-anker.md` | PR #2, `2bc42d4` |
| 1c | Hash-Format v=2 mit Salz; Tilgung von Event, Einheiten und Blob als Event der Art `action`, mit Anordnung und Vollzug in `verify`; Projektionen folgen einer Tilgung; Blobs im Format `age` auf S3, `append --attach`, `blob get`, `verify --blobs`; `redact` | `specs/2026-10-04-stufe-1c-blobs-und-tilgung.md` | PR #5, `d16f3fc` |
| Auslieferung | Die Migrationen im Paket und `previously migrate` unter einer Advisory-Sperre; `PREVIOUSLY_DSN` nach einer eigenen Grammatik gelesen; ein Image aus dem Paket auf PyPI, mit Smoke-Test; `release.yml`: Test-PyPI bei jedem Push auf `main`, PyPI und Image für zwei Plattformen bei einem veröffentlichten Release; der Handoff an kup6s | `specs/2026-10-05-auslieferung.md` | PR #6, `fd3e17f`; veröffentlicht als `0.1.0a1`, wie der Spec der Aufnahme festhält |
| Aufnahme | `RawEvent` trägt `artifact_hash` und `channel_identities`, `append` vergleicht die Inhaltsidentität und weist Abweichendes mit `ArtifactChanged` ab; eine Mail als Event (`core/mail.py`), mit Rohmail und Anhängen als Blobs und einer Mail im Anhang als eigenem Event; `Connector`, `Fetched`, `Watermark`, `WatermarkStore` in `contract`, die Tabelle `watermark` (Migration `0005_watermark`); der Lauf (`core/ingest.py`), der das Wasserzeichen erst nach dem Anfügen schreibt; `connectors/imap.py` und `previously ingest imap`; der Handoff `handoffs/2026-10-06-kup6s-ingest.md` | `specs/2026-10-06-pilot-imap-aufnahme.md` | PR #7, `009c669`; Bedingung 11, der Lauf des Betreuers gegen seinen echten Mailu-Ordner, bestanden am 2026-10-09; veröffentlicht als `v0.1.0a2` am 2026-10-09, der Handoff `handoffs/2026-10-06-kup6s-ingest.md` am selben Tag an den Agenten in kup6s übergeben |
| Einheit 3 | Gate und Policy: Kreise, Mitgliedschaften, eigene Identitäten, Regeln und die Zusagen der Anbieter als Handlungen im Log (`policy`); die Entscheidung als reine Funktion in `core/decide.py`, die strengste Regel gewinnt, ohne Regel nur lokal, und der Rückfall wird sichtbar (`policy gaps`); `gate` mit den Adaptern für Anthropic, Mistral und ein lokales Modell, der Aufgabe `mail_overview`, einer Preisdatei und dem Audit als `model_call` mit der Kaskade der Tilgung und den Prüfungen in `verify`; die Chronik zeigt nur Wahrnehmungen; die Seiten `trust-boundaries.md`, `processing-policy.md`, `policy-and-model-calls.md` und die Anleitung; der Handoff `handoffs/2026-10-09-kup6s-gate.md` | `specs/2026-10-09-pilot-gate-und-policy.md` | PR #9, `d75c4b3`; Bedingung 10, der Lauf des Betreuers gegen die echten APIs, bestanden am 2026-10-09 |
| Einheit 4 | MCP-Lesezugang: Clients als Prinzipale mit Token und Verarbeitungskette (`client`); die Zusage um Betreiber, Training, Unterverarbeiter und Herkunft des Modells erweitert, die Regel um die vier passenden Einschränkungen; `previously mcp` (stdio) und `previously serve` (HTTP, beide Generationen, Bereitschaft über `GET /healthz` ohne Token); fünf Werkzeuge, zwei Ressourcen-Vorlagen, zwei Prompts, jeder Inhalt nur nach `decide` mit der Kette des Clients; das Zugriffsprotokoll als `mcp_access` und `previously access`; `policy gaps` zählt, was MCP zurückhielt; die Seiten `mcp-interface.md`, `mcp-tools.md` und die Anleitung `connect-claude-code-and-vibe.md`; der Handoff `handoffs/2026-10-11-kup6s-mcp.md` | `specs/2026-10-10-pilot-mcp-lesezugang.md` mit dem Konzept `specs/2026-10-10-mcp-schnittstelle.md`, beide eingefroren am 2026-10-11 | PR #12, `ffa28fb`; veröffentlicht als `v0.1.0a3` am 2026-10-11; Bedingung 9 erledigt am 2026-10-11, nach Entscheidung des Betreuers auf den Lauf von kup6s (RG), ohne Vibe und ohne die drei Kreise |
| Einheit 5 | Feststellungen: Verpflichtung und Entscheidung mit Quellen (`core/assertion.py`, `core/assertions.py`), Vorschläge, Freigabe und Ablehnung, Lesen durch Falten des Logs, die Kommandos dazu, fünf MCP-Werkzeuge; die Antworten in einem Aufruf (PR #20) | `specs/2026-10-12-pilot-feststellungen.md`, eingefroren am 2026-10-12 | PR #17, `4735e3f`; veröffentlicht als `v0.1.0a5`; die Abnahme nach F §14 lief am 2026-10-13; `v0.1.0a6` mit PR #20 |
| Zuordnungen, Phase 1 | Das Vokabular als Handlung `vocabulary` mit Grundvokabular (`core/vocabulary.py`), Entitäten und Beziehungen als Feststellungen (`core/graph.py`, `core/graph_write.py`), die Freigabeklassen (`core/classes.py`), die Kommandos dazu, fünf MCP-Werkzeuge | `specs/2026-10-14-zuordnungen.md` (lebendig) | PR #24, `cce8b4b`; veröffentlicht als `v0.1.0a7`; der Lauf mit Vellenfeld nach Z §17 Punkt 1 lief am 2026-10-14 in kup6s (die vier Befunde sind geschlossen, `14de3d3`) |
| Zuordnungen, Phase 2 | Die Zuordnung von Events und Einheiten an Klammern: die Art `concerns` im Grundvokabular (`from = ["event"]`, `to = ["*"]`), ein Event am Anfang ist Quelle, `members` (die Menge einer Klammer, das Genauere ersetzt das Allgemeine); die Projektion `graph` (Migration `0006_graph`, `p_graph_version`, `p_graph_thread`), von Lesern beim Lesen nachgezogen, mit Rückfall auf das Falten des Logs; `project --check`; `chronicle --within N` und MCP `previously(within=N)`, über MCP zählt eine Kante nur, wo der Client sie sieht; die Seiten und `handoffs/2026-10-15-kup6s-graph-phase-2.md` | `specs/2026-10-14-zuordnungen.md` (lebendig), Plan `plans/2026-10-15-zuordnungen-phase-2.md` | gebaut auf dem Zweig `worktree-zuordnungen-2`, noch nicht gemerged; Endprüfung, PR, Release und Handoff stehen aus |

Mit Stufe 1c ist Teilprojekt 1 gebaut und abgeschlossen, wie die Architektur
es in §12.1 zuschneidet: Log, Projektionen, Blobs. Die Auslieferung und die
Aufnahme sind die Einheiten 0 und 1 des Piloten (unten).

Das Gate ist gebaut (Einheit 3, oben) und am 2026-10-09 gegen alle drei
Anbieter gelaufen (Bedingung 10). Der MCP-Lesezugang ist abgenommen und mit
`v0.1.0a3` veröffentlicht (Einheit 4, oben). Beide laufen seit dem
2026-10-11 in kup6s (RG).

In Betrieb ist `v0.1.0a6` in kup6s (R6), nach den Handoffs der Auslieferung, der
Aufnahme, des Gates, des MCP-Servers, der Einstellungen und der Feststellungen: Datenbank, Bucket, Werkzeug-Pod, die
CronJobs `project`, `anchor` (täglich seit dem 2026-10-06) und `verify`, die
Aufnahme des echten Ordners mit neun Mails (RK); dazu die beiden Schlüssel des
Gates nur im Werkzeug-Pod, der allein `api.anthropic.com` und `api.mistral.ai`
erreicht, und das Deployment `previously-mcp` mit einem Replikat, das nur die
Datenbank erreicht. Seit dieser Rückmeldung verbieten Netzwerk-Richtlinien
jedem Pod von Previously alles außer DNS, der Datenbank und den Hosts seiner
Kommandos (RG). Jede Prüfung der Handoffs ist bestanden, und kup6s weicht an
fünf Stellen begründet ab — PostgreSQL 18, verschlüsselte Dumps statt Barman
oder pgBackRest, Zugangsdaten für das ganze Hetzner-Projekt, die Ankerdatei in
Git bei keinem Dritten, die Restore-Probe von Hand (RK). Nicht gebaut ist
dort der Modellserver — das Gate lehnt ab, wo nur ein lokales Modell darf;
den Zugang zum MCP-Server gibt seit dem 2026-10-13
das Tailnet (Stufe A2, R6), `kubectl port-forward` bleibt die Rückfalllinie (RG).
Das Log dort ist eine Probe: die Daten werden vor dem
regulären Gebrauch zurückgesetzt, das dauerhafte Log beginnt danach.

Seit dem 2026-10-13 läuft `0.1.0a6` in kup6s (R6): Werkzeug-Pod, Jobs und
`previously-mcp` auf der neuen Version, die Migration meldet `up to date:
0005_watermark`. Der Handoff `handoffs/2026-10-13-kup6s-a6.md` steht, beide
Prüfungen. Die Umschaltung der Primärinstanz auf Probe, am 2026-10-13 um
13:08 UTC, hat eine Anfrage gekostet, und zwar mitten im Wechsel, als kein
Primärknoten antwortete; danach antwortete jede Prüfung mit 200 (R6). Die
Annahme, `pool_pre_ping` spare den Wechsel, hat sich damit nicht bestätigt
(unten unter *Erledigt*). Stufe A2 steht seit demselben Tag: eine
Tailscale-Instanz im Pod, ein Headscale als Steuerserver, einfaches HTTP
innerhalb von WireGuard, der Name des Tailnets in
`PREVIOUSLY_MCP_ALLOWED_HOSTS`; `whoami` antwortete, `previously access`
listete den Aufruf (R6).

Seit dem 2026-10-12 läuft `0.1.0a5` in kup6s (RA). Die vier Prüfungen des
Handoffs der Einstellungen (`v0.1.0a4`) stehen: das Release läuft, kein Pod
setzt einen alten Host- oder Port-Namen, die Aufnahme ging von ihrer
Wasserlinie weiter (`up to uid 9`), `previously-mcp` hört auf `0.0.0.0:8765`
mit der Probe bei 200 `ok`. Beim Handoff der Feststellungen stehen: Werkzeug-Pod
und Jobs auf `0.1.0a5` mit Migration `0005_watermark`, der Schlüssel
`PREVIOUSLY_MCP_CONFIRM_KEY` nur in `previously-mcp`, die vorgesehene Aufnahmezeile, und
die Vorschau von `write_assertion` über den Server (`handle:`-Zeile, `Nothing
is written yet`), und `UPDATE` auf `event` für die Rollen von `previously-mcp`
und Werkzeug-Pod — gegeben, weil alle Pods die Rolle `previously` benutzen, die
Eigentümerin der Datenbank (siehe *Betrieb*). kup6s hat die Umbenennung der Einstellungen in drei Schritten
ausgerollt (neue Namen neben die alten, dann das Image, dann die alten Namen
weg); `cut-a-release.md` sagt es jetzt.

Abgenommen: Einheit 5, die Feststellungen (Verpflichtung und Entscheidung mit
Quellen, Vorschläge über MCP, Freigabe und Ablehnung, die Kaskade der Tilgung),
gemergt am 2026-10-12 (PR #17, `4735e3f`) und als `v0.1.0a5` veröffentlicht.
Die Abnahme nach F §14 durch den Betreuer ist am 2026-10-13 gelaufen (siehe
*Erledigt*): Vorschläge von Claude Code und Vibe, Freigabe und Ablehnung auf der
Kommandozeile und über MCP mit Rückfrage des Clients, Listen, überfällig und
Geschichte, Tilgung mit Kaskade und `verify` ohne Befund, und die Policy für
einen zweiten Client. Nicht gelaufen: der Schlüssel der Vibe-Ask-Einstellung.
Die Kennzeichnung `requiresUserInteraction` ist am selben Tag gegen
`0.1.0a6` nachgemessen (unter *Feststellungen und Entitäten*).

Abgenommen: Phase 1 der Zuordnungen, der Kern (Z §3–§7), gemergt am 2026-10-14
(PR #24, `cce8b4b`) und als `v0.1.0a7` veröffentlicht, gebaut auf dem Zweig
`worktree-zuordnungen` nach dem Spec `specs/2026-10-14-zuordnungen.md`
(lebendig, nicht eingefroren) und dem Plan `plans/2026-10-14-zuordnungen-phase-1.md`.
Das Vokabular als Handlung `vocabulary` mit Grundvokabular, Entitäten und
Beziehungen als Feststellungen mit den drei Stufen `direct`, `transitive` und
`open`, die Freigabeklassen mit Trefferquote und Stichprobe, Einwände und
Rückfragen, die Kommandos `vocabulary`, `entity`, `relate`, `entities`,
`relations`, `classes`, `triage`, `answer` und `status`, fünf MCP-Werkzeuge
(fünfzehn in allem) und der Kopf mit der Zahl der Einwände. Ohne Migration und
ohne Projektionstabelle (Z §10.1). Am Gate ändert sich nichts. Die Seiten stehen
(`explanation/graph.md`, die drei Anleitungen, die Referenz), der Handoff
`handoffs/2026-10-14-kup6s-graph-phase-1.md` liegt bei.

Seit dem 2026-10-14 läuft `0.1.0a7` in kup6s (R7, Antwort in
`handoffs/2026-10-14-kup6s-feedback-graph-phase-1.md`): alle vier Prüfungen des
Handoffs stehen. `previously vocabulary apply --base` hat neun Ereignisse
geschrieben, `entities` antwortet auf dem leeren Graphen, `list_entities`
antwortet über MCP, und `previously-mcp` zeigt fünfzehn Werkzeuge. Eine Regel
für `source:recollection` ist nicht gesetzt. Der übergebene Handoff bleibt
unverändert; sein Satz, der `member_of` zum Grundvokabular zählt, führte in
die Irre: `member_of` ist eingebaut (wie `circle` und `in_circle`) und steht
nicht unter den neun.

Die Abnahme von Phase 1 nach Z §17 Punkt 1 lief am 2026-10-14 in kup6s, Schritt
für Schritt durch `how-to/keep-a-club-and-its-offices.md`, alles mit
`--recollection`, die Ids 107 bis 128, die Probe danach widerrufen. Jede Antwort
war, wie die Anleitung sie nennt; vier Befunde, alle im Zweig
`worktree-rueckmeldung-a7` geschlossen (unter *Erledigt*, `14de3d3`).

Phase 2 ist gebaut (Zweig `worktree-zuordnungen-2`, Basis `0bfb228`): die Art
`concerns` ist im Grundvokabular deklariert und keine eingebaute Art; ein Event
am Anfang einer Beziehung ist Quelle, so dass die Kaskade der Tilgung die
Zuordnung mit ihrer Mail fällt; `members` findet die Menge einer Klammer rein
in `core`, ohne eine Art beim Namen zu nennen; die Projektion `graph` hält
keinen Inhalt, die Leser ziehen sie vor dem Lesen nach und falten bei einem
Versionssprung den Log; `previously project --check` vergleicht sie mit der
Faltung; `chronicle --within N` und `previously(within=N)` finden und geben
nichts frei. Ausführungsprotokoll: `sdd/2026-10-15-zuordnungen-phase-2/`
(kommt mit der Endprüfung ins Repository). Die Seiten stehen
(`explanation/graph.md`, `explanation/projections.md`,
`how-to/assign-mails-and-read-a-bracket.md`, die Referenz), der Handoff liegt bei.

Nicht gebaut: die Suche, Kreise im Graphen
und am Gate (Phase 3), Verpflichtungen im Schema (Phase 4), KI-Schicht, jeder
Konnektor außer dem für IMAP.

## Was als Nächstes kommt

Zuerst Phase 2 der Zuordnungen zu Ende bringen: die Endprüfung über den Zweig
`worktree-zuordnungen-2` mit Messung auf einer festen Kopie (10 000 und 100 000
Beziehungen), eine Fixwelle, der PR, das Release nach `v0.1.0a7`, der Handoff
`handoffs/2026-10-15-kup6s-graph-phase-2.md` (erst nach grünem `manifest`) und
die Abnahme von Phase 2 nach Z §17 Punkt 2. Danach der Pilot, wie unten.

Der Pilot an einem echten Kunden, jetzt an erster Stelle. Die Reihenfolge
hat der Betreuer am 2026-10-04 entschieden, nach dem Prüfpunkt und der kleinen
Wartungsrunde (ihre vier Punkte stehen unten unter *Erledigt*): erst Stufe 1c,
dann der Pilot. Stufe 1c ist abgenommen (oben); was sie offen lässt, steht
unten unter *Tilgung* und *Blobs und Speicher*, und an den Einheiten, zu denen
es gehört.

Vor die Aufnahme aus IMAP hat der Betreuer am 2026-10-05 die Auslieferung
gestellt: sie hängt an nichts aus der Aufnahme, und kup6s kann mit dem Image
des heutigen Stands Datenbank, Sicherung und Werkzeug-Pod aufbauen, während
die Aufnahme entsteht. Die Aufnahme kommt dann mit dem nächsten
Alpha-Release. Was die Auslieferung offen lässt, steht unten unter
*Auslieferung*.

Die Aufnahme ist abgenommen, und Bedingung 11 ist bestanden (oben); das
Alpha-Release mit `ingest imap`, `v0.1.0a2`, ist am 2026-10-09 veröffentlicht,
und der Handoff der Aufnahme ist am selben Tag an den Agenten in kup6s
übergeben. Einheit 3, Gate und Policy, ist abgenommen (PR #9, `d75c4b3`).
Bedingung 10, der Lauf des Betreuers gegen die echten APIs, ist bestanden
(unten unter *Erledigt*). Einheit 4, der MCP-Lesezugang, ist abgenommen
(PR #12, `ffa28fb`) und mit Gate und Policy als `v0.1.0a3` am 2026-10-11
veröffentlicht; der Handoff des Gates wurde zurückgehalten, damit Gate und
MCP-Server mit einem Release kommen. Am selben Tag hat kup6s auf die Handoffs
der Auslieferung und der Aufnahme geantwortet (RK), und der Betreuer hat
daraufhin vier Dinge entschieden: Sicherungen sind Anforderungen, das System
wählt der Betrieb; eine Tilgungszusage deckt nie die Quellsysteme; PostgreSQL
18 ist die getestete und unterstützte Version, 17 nicht mehr; Ablageort der
Anker und Rückgabecode auf leerem Log sind für den Piloten hingenommen. Der
Zweig `worktree-betrieb-rueckmeldung` hat das umgesetzt (PR #13, `d97f9ed`),
und die Handoffs des Gates und des MCP-Servers sind übergeben. Noch am
2026-10-11 hat kup6s auf beide geantwortet (RG): alles steht, mit einem
Fehler von uns — `PREVIOUSLY_MCP_PORT` kollidierte mit den Variablen, die
Kubernetes für einen Service setzt — und Hinweisen für Doku und Meldungen.
Der Betreuer hat den Lauf von kup6s als Bedingung 9 der Einheit 4 genommen
(unten unter *Erledigt*). Der Zweig `worktree-gate-mcp-rueckmeldung` setzt
die Antwort um: die Adress-Einstellungen, die Meldungen, die Anforderung an
das Netz, der Handoff `handoffs/2026-10-11-kup6s-settings.md`; er ist
gemergt (PR #14, `347c37b`), `v0.1.0a4` ist am 2026-10-12 veröffentlicht, und
der Handoff der Einstellungen ist übergeben. Die 1..n IMAP-Ordner als
Eingang (Betreuer, 2026-10-12) sind gemergt (PR #16, `739912b`; unten unter
*Erledigt*). Einheit 5, die Feststellungen, hat ihren Spec
(`specs/2026-10-12-pilot-feststellungen.md`, eingefroren am 2026-10-12) und
ist gebaut auf dem Zweig `worktree-feststellungen`, ohne Projektionstabellen
und ohne Migration (Planentscheidung 1, vom Betreuer am 2026-10-12
bestätigt); der Handoff `handoffs/2026-10-12-kup6s-assertions.md` liegt bei.
Die Endprüfung hat am 2026-10-12 die Lesezeit bei 5 000 Feststellungen
gemessen (unten unter *Feststellungen*), und ihre Fixwelle ist gelaufen.
Sie ist gemergt (PR #17, `4735e3f`), `v0.1.0a5` ist am 2026-10-12
veröffentlicht, der Handoff ist übergeben, und kup6s hat geantwortet (RA). Was
jetzt kommt: die Abnahme nach F §14 ist gelaufen (2026-10-13, siehe
*Erledigt*), der Zweig `mcp-erklaeren` ist gemergt (PR #20, `248a001`) und
mit `pool_pre_ping` als `v0.1.0a6` am 2026-10-13 veröffentlicht; der Handoff
`handoffs/2026-10-13-kup6s-a6.md` liegt bei und bittet kup6s, die Umschaltung
der Primärinstanz zu wiederholen; kup6s hat geantwortet (R6, siehe unten). Die Zuordnungen
haben ihren Spec (`specs/2026-10-14-zuordnungen.md`, lebendig bis die Seiten
aller Phasen stehen), und Phase 1 ist abgenommen und veröffentlicht (oben): die Endprüfung
mit der Messung von `entities`, `relations --at` und des Kopfes bei 10 000 und
100 000 Beziehungen (Planentscheidung 14; die Zahlen stehen unten unter
*Zuordnungen* und auf `explanation/graph.md`) ist gelaufen, der Merge war PR #24
(`cce8b4b`), das Release `v0.1.0a7`, der Handoff ist übergeben und beantwortet
(R7). Der Lauf mit Vellenfeld nach Z §17 Punkt 1 ist am 2026-10-14 gelaufen
(oben), seine vier Befunde sind geschlossen. Was als Nächstes kommt, ist der
Plan der Phase 2, der Zuordnung von Events, mit der Projektion oder der
inkrementellen Faltung, die die Messungen verlangen (unten unter *Zuordnungen
(Phasen 1–4)*, der Punkt zum Falten des Graphen bei jedem Aufruf).
Was die Aufnahme offen lässt, steht unten unter *Aufnahme aus IMAP* und an
den Einheiten, zu denen es gehört.

Der Weg dorthin hatte zwei Umwege, und sie stehen hier, damit die Reihenfolge
nicht wie ein Versehen aussieht: der Prüfpunkt empfahl zuerst den Einwurf mit
eigenen Notizen, weil das System noch kein echtes Event gehalten hatte; der
Betreuer machte daraus den Piloten an einem Kunden; und an echter Kundenpost
wog dann schwerer, was 1c liefert.

### Der Pilot an einem echten Kunden

Der Zuschnitt, den der Prüfpunkt zuerst festhielt — der Einwurf per Prompt,
zuerst eigene Notizen —, ist verworfen: reine Gedankennotizen wären Theorie
und sagten wenig. Stattdessen:

- **Quellen:** ein eigens angelegter IMAP-Ordner und ein Ordner in der
  Nextcloud. Was der Betreuer dorthin kopiert, ist relevant.
- **Ziele, alle vier:** die Chronik des Kunden lesen; die Aufnahme an echter
  Post härten; Claude Code fragt das Log; Protokoll und offene Punkte.
- **Der Weg: Durchstich mit Gate von Anfang an.** Vorschläge kommen aus einer
  eigenen KI-Schicht hinter dem Gate, mit Policy und Audit — nicht aus dem
  Cockpit, das der Betreuer dann abnickt.
- **Datenpolitik des Pilotkunden:** sein Inhalt darf über Claude Code an
  Anthropic gehen („bei diesem Kunden gedeckt", Betreuer, 2026-10-04).
- **Betrieb:** gleich in kup6s, nicht erst lokal.

Die Einheiten, in dieser Reihenfolge; nur die jeweils nächste bekommt einen
Spec:

| # | Einheit | bringt | Spec |
|---|---|---|---|
| 0 | Auslieferung: Migrationen im Paket, `previously migrate`, Image, Release-Weg, Handoff an kup6s | ein Image, aus dem kup6s alles startet | `specs/2026-10-05-auslieferung.md`, eingefroren am 2026-10-05; abgenommen mit PR #6 (oben) |
| 1 | Aufnahme aus dem IMAP-Ordner, mit dem Einwurf- und dem Konnektor-Vertrag | Chronik des Kunden; echte Post im Log | `specs/2026-10-06-pilot-imap-aufnahme.md`, eingefroren am 2026-10-06; abgenommen mit PR #7 (oben). Er ersetzt den Entwurf vom 2026-10-04 auf dem Zweig `worktree-pilot-imap-aufnahme` (`9b493f0`) |
| 2 | Betrieb in kup6s: Datenbank mit Sicherung, Restore-Probe, Bucket, Werkzeug-Pod, CronJobs für Aufnahme, Projektion und Anker | Daten, die bleiben | beginnt beim Image aus Einheit 0; gebaut wird er vom Agenten in kup6s, nie von hier. Was er braucht, sagen die Handoffs `handoffs/2026-10-05-kup6s-delivery.md` und, für die Aufnahme, `handoffs/2026-10-06-kup6s-ingest.md` und, für das Gate, `handoffs/2026-10-09-kup6s-gate.md` und, für den MCP-Server, `handoffs/2026-10-11-kup6s-mcp.md`, englisch; alle vier liegen dort und stehen, wie die Rückmeldungen vom 2026-10-11 sagen (RK, RG), bis auf den Modellserver und das Tailnet; mit `v0.1.0a4` ist am 2026-10-12 `handoffs/2026-10-11-kup6s-settings.md` übergeben |
| 3 | Gate und Policy: Kreise statt Organisationsprofil, drei Anbieter-Adapter, Audit, die Verarbeitungsprüfung (nicht mehr „Offenlegungsprüfung“: PG §1.2) | die Grenze, hinter der ein Modell Inhalt sieht | `specs/2026-10-09-pilot-gate-und-policy.md`, eingefroren am 2026-10-09; abgenommen mit PR #9 (oben) |
| 4 | MCP-Lesezugang, mit der Verarbeitungsprüfung davor (die Entscheidung aus Einheit 3, wiederverwendet) | Claude Code fragt das Log | `specs/2026-10-10-pilot-mcp-lesezugang.md` mit dem Konzept `specs/2026-10-10-mcp-schnittstelle.md`, das §8 der Architektur ablöst; beide eingefroren am 2026-10-11; abgenommen mit PR #12 (oben) |
| 5 | Feststellungen: Schreibweg, Verpflichtung und Entscheidung, Freigabe und Ablehnung, Lesen durch Falten des Logs | was festgestellt ist, mit Quelle und Verantwortung | `specs/2026-10-12-pilot-feststellungen.md`, eingefroren am 2026-10-12; gebaut auf dem Zweig `worktree-feststellungen`, ohne Projektionen (Planentscheidung 1); abgenommen mit PR #17 (`4735e3f`, 2026-10-12), veröffentlicht als `v0.1.0a5`, die Abnahme nach F §14 lief am 2026-10-13 |
| 6 | KI-Schicht: Vorschläge hinter dem Gate | Protokoll und offene Punkte | — |
| 7 | Nextcloud-Ordner mit Textextraktion | Dokumente | — |

Für Einheit 2 beantwortet, mit der Auslieferung: kup6s arbeitet mit cdk8s,
ArgoCD und dem CloudNativePG-Operator; das Image kommt von `ghcr.io`; was dort
entsteht, baut der Agent in kup6s nach dem Handoff (Betreuer, 2026-10-05). Der
Zugang vom Arbeitsplatz ist `kubectl exec` in den Werkzeug-Pod für die
Kommandos und, seit dem 2026-10-11, `kubectl port-forward` zu
`previously-mcp` für die Clients; das Tailnet (Stufe A2) steht seit dem
2026-10-13 (R6), der Port-Forward ist die Rückfalllinie (RG).

## Was vor was kommen muss

Keine Planung der Teilprojekte — die Architektur nennt das zu Recht Fiktion
(§12.2) —, sondern die Zwänge, die heute schon feststehen. Jede Zeile hat
ihren Beleg im Prüfpunkt.

| Zuerst | dann | weil |
|---|---|---|
| Der Einwurf-Vertrag entscheidet, was mit geändertem Inhalt unter bekanntem Schlüssel geschieht — **gebaut mit Einheit 1**: `append` vergleicht `artifact_hash` und weist ab | jeder Konnektor | `append` verwarf ihn stumm; wer die Issue-Nummer als `external_id` nimmt, verlöre jede Änderung nach der ersten |
| `RawEvent` bekommt Rohbytes und Kanalidentitäten, oder die Architektur gibt sie auf — **gebaut mit Einheit 1**: Kanalidentitäten im Vertrag, die Rohbytes als Blob | IMAP, Drop-Ordner | Leitsatz 6: was nicht aufgenommen wurde, ist nicht nachholbar |
| Feststellungen: zweiter Schreibweg, Art und Unterart, Regeln je Art in `verify` | Triage, `record_assertion`, KI-Schicht, Identitätsgraph, jede fachliche Projektion | `append` schreibt nur `observation`; `verify` kennt keine Art-Regeln |
| Blobs mit Verschlüsselung — **gebaut mit Stufe 1c** | Drop-Ordner mit Dateien, IMAP mit Anhängen und Rohmail, Voice | es gab keinen Ort für Bytes |
| Tilgung als Event, die Einheiten und Projektionen mitnimmt — **gebaut mit Stufe 1c** | Inhalte Dritter im Log (Mail, Dokumente) — also der Pilot | ein Grabstein war von einer Fälschung nicht zu unterscheiden, und die Einheiten blieben stehen |
| Ein Betrieb mit Sicherung, Restore-Probe und Anker-Routine — das Image **gebaut mit der Auslieferung**, der Rest **steht in kup6s** mit stündlichen verschlüsselten Dumps und täglichen Ankern, die Restore-Probe bisher von Hand (RK) | Daten, deren Verlust weh tut | bis zur Rückmeldung vom 2026-10-11 gab es nur Wegwerf-Datenbanken; auch das Log in kup6s ist noch eine Probe, die vor dem regulären Gebrauch zurückgesetzt wird |
| Echte, gemischtsprachige Einheiten im Log | die Messung zur Textsuche und die Wahl des Embedding-Modells | beide verlangen einen Testsatz aus echten gemischten Einheiten (Architektur §11, Nachtrag) |
| Warteschlange (die Sperre auf der Zustandszeile ist gebaut, Commit `3ae7038`) | der erste asynchrone Produzent | ein asynchroner Produzent braucht Entprellung und Wiederholung |
| Das Gate — **gebaut mit Einheit 3**, nur `gate` importiert die Clients der Anbieter | jeder Modellaufruf | Regel 2 der Architektur: nur `gate` ruft Modelle |
| Die Prüfung vor dem Schreiben nach außen (PG §1.2) | die erste Aktion, die in ein fremdes oder öffentliches System schreibt | eine andere Prüfung an einer anderen Stelle als die Verarbeitungsprüfung des Gates: wer sieht es dort? |
| Prüfung, ob Claude Code MRTR und die Tasks-Erweiterung kann | blockierende Rückfragen und lange Läufe über MCP | Architektur §13 |
| Die Rechtsfrage zur Gesprächsaufzeichnung | Teil 2, Voice | Entwurf §16 |

## Zwei Stücke ohne Teilprojekt

Die Zerlegung in §12 der Architektur hat acht Teilprojekte. Zwei Dinge, die
das MVP braucht, stehen in keinem:

- **Feststellungen und Entitäten.** Teilprojekt 1 heißt „`core` und
  `storage`" und liefert in seinen drei Stufen die Mechanik: Log,
  Projektionen, Blobs. Die Event-Art `assertion`, ihr Schreibweg, die zehn
  Entitäten als Projektionen stehen in keiner Stufe. Die Teilprojekte 5
  (Triage) und 7 (Identitätsgraph) setzen sie voraus.
- **Betrieb.** Die Architektur nennt den Deployment-Mechanismus eine
  Betriebsentscheidung, an der kein Modul hängt (§11). Der Anker hängt daran,
  und `CLAUDE.md` verlangt seit dem 2026-10-04 von jedem Spec eine Aussage zum
  Betrieb. Image, Deployment, Sicherung, Restore-Probe und Anker-Routine waren
  eine Einheit Arbeit, die niemand zugeschnitten hatte; seit dem 2026-10-05
  sind sie zwei Einheiten des Piloten, die Auslieferung (das Image) und der
  Betrieb in kup6s (alles andere), aber weiter in keinem Teilprojekt.

## Offene Punkte, nach ihrem Zuhause

Herkunft in Klammern: **A** Architektur, **E** Entwurf, **1a**/**1b**/**AA**/**1c**
die Stufen-Specs mit Abschnitt, **P-1b**/**P-AA** das `index.md` des
jeweiligen Ausführungsprotokolls, **P-1c** das Ausführungsprotokoll der Stufe
1c (`sdd/2026-10-04-stufe-1c-blobs-und-tilgung/`), **AL** der Spec der
Auslieferung mit Abschnitt, **P-AL** das Ausführungsprotokoll der Auslieferung
(`sdd/2026-10-05-auslieferung/`) mit dem Ruling oder der Aufgabe, **PI** der
Spec der Pilot-Einheit 1 mit Abschnitt, **P-PI** ihr Ausführungsprotokoll
(`sdd/2026-10-06-pilot-imap-aufnahme/`) mit dem Ruling oder der Aufgabe,
**PG** der Spec der Pilot-Einheit 3 mit Abschnitt, **P-PG** ihr
Ausführungsprotokoll (`sdd/2026-10-09-pilot-gate-und-policy/`) mit dem
Ruling oder der Aufgabe,
**MK** das Konzept der MCP-Schnittstelle (`specs/2026-10-10-mcp-schnittstelle.md`)
mit Abschnitt, **ML** der Spec der Pilot-Einheit 4, des MCP-Lesezugangs, mit
Abschnitt, **P-ML** dessen Ausführungsprotokoll
(`sdd/2026-10-11-pilot-mcp-lesezugang/`) mit dem Ruling oder der Aufgabe,
**F** der Spec der Pilot-Einheit 5, der Feststellungen, mit Abschnitt, **P-F**
dessen Ausführungsprotokoll (`sdd/2026-10-12-pilot-feststellungen/`) mit dem
Ruling oder der Aufgabe,
**PP** der Prüfpunkt vom 2026-10-04 mit der Zeile seines Belegberichts,
**RK** die Rückmeldung des Agenten in kup6s vom 2026-10-11 auf die Handoffs
der Auslieferung und der Aufnahme
(`handoffs/2026-10-11-kup6s-feedback-delivery-and-ingest.md`), englisch, wie
erhalten, **RG** seine Rückmeldung vom selben Tag auf die Handoffs des Gates
und des MCP-Servers (`handoffs/2026-10-11-kup6s-feedback-gate-and-mcp.md`),
ebenso, **RA** seine Rückmeldung vom 2026-10-12 auf die Handoffs der
Einstellungen und der Feststellungen
(`handoffs/2026-10-12-kup6s-feedback-settings-and-assertions.md`), ebenso,
**R6** seine Rückmeldung vom 2026-10-13 auf den Handoff von `0.1.0a6`
(`handoffs/2026-10-13-kup6s-feedback-a6.md`), ebenso, **Z** der Spec der
Zuordnungen (`specs/2026-10-14-zuordnungen.md`) mit Abschnitt, **P-Z1** das
Ausführungsprotokoll seiner Phase 1 (`sdd/2026-10-14-zuordnungen-phase-1/`)
mit dem Ruling oder der Aufgabe.

### Einwurf-Vertrag (`contract`, Teilprojekt 2)

- Gmail und OAuth: ein Postfach bei Google Workspace braucht in der Regel
  `XOAUTH2`, der Konnektor nimmt dann ein Token statt eines Passworts; das
  Holen und Erneuern des Tokens ist die eigentliche Arbeit (`google-auth`)
  (PI §1, §11 Punkt 1).
- `RawEvent.payload` steht in keinem Vertrag der Architektur (PP, A1 Zeile
  13). Bis Commit `09c5d81` legte die Kommandozeile den Volltext dort ab, und
  der Text stand dreimal in der Datenbank — Nutzlast, Einheiten,
  `p_chronicle` —; aus 1 GB Text wurden 4,5 GB (PP, Bericht C). Seitdem steht
  der Text eines `append --text` zweimal, in den Einheiten und in
  `p_chronicle`; die Zahl aus Bericht C ist mit der Kopie gemessen und nicht
  neu gemessen. Was ein Konnektor in die Nutzlast legt, legt seit Einheit 1
  der Konnektor fest und schreibt es auf seine Reference-Seite (PI §2.2); für
  Mail steht es in `mail-mapping.md`, der Text nur in den Einheiten, der
  Betreff auch unter `headers`. Für jeden weiteren Konnektor bleibt es offen.
- `--occurred-at` fällt auf „jetzt" zurück, `--evidence` auf `recollection`:
  zwei Vorgabewerte, die als Tatsache in der Kette stehen; und was
  `occurred_at` bei einer Erinnerung meint, die Notiz oder das Ereignis, ist
  nicht entschieden (PP, A1 Zeile 34 und Leitsatz 9).
- Zerlegungsregeln der weiteren Medien (1a §12).
- Interne Abgleichlogik je Konnektor (A §11).
- Der Einwurf per Prompt, der Drop-Ordner mit Textextraktion und OCR, „Quelle
  verlinken" (E §11.4).
- Textextraktion aus Blobs, und damit ihr Inhalt in Einheiten (1c §12 Punkt 8);
  für die Anhänge einer Mail mit Einheit 7 (PI §11 Punkt 8). Am 2026-10-11 das
  Erste, was ein Leser der Chronik vermisste: Claude Code fasste über MCP die
  Mails eines Kreises zusammen und konnte die Word- und Excel-Dateien, die die
  Substanz trugen, nur beim Namen nennen (RG). Der Betreuer am 2026-10-14:
  Kunden schicken die wichtige Information oft nur als Anhang, und in der Mail
  steht wenig — ein PDF, ein Word-Dokument. Der Spec der Zuordnungen
  (`specs/2026-10-14-zuordnungen.md`, §8) legt schon fest, wie ein gelesener
  Anhang aussehen soll: ein eigenes Event wie eine Mail im Anhang (PI §3.6),
  mit eigenen Einheiten und eigenen Zuordnungen, das die Kreise der Mail erbt,
  mit der es kam, weil es selbst keine Adressen hat.
- Der Quellschlüssel überlebt jede Tilgung: `source` und `external_id` stehen
  im Event-Hash, und eine Message-ID trägt eine Domain (1c §4.5, §12 Punkt 4).
- Nach einer Wiederherstellung kann ein getilgtes Event, das mit ihr verloren
  ging, neu eingeliefert werden und trägt dann eine neue `id` und einen neuen
  Hash; die Prüfung am Hash weist es zu Recht ab. Die Aufzeichnung einer
  Tilgung führt deshalb den Quellschlüssel (`erase-something.md`,
  `restore-from-a-backup.md`). Kein Kommando findet ein Event an seinem
  Quellschlüssel: `show` druckt ihn nicht, nur `chronicle` neben jeder Einheit,
  die dort eine Zeile hat. Für den Piloten, dessen Aufnahme ein Postfach erneut
  liest (Endprüfung der Doku, Befund 12; P-1c). Mit `ingest imap` geschieht es
  von selbst: das Wasserzeichen kommt mit der Wiederherstellung zurück, und
  der nächste Lauf nimmt eine Mail, die noch im Ordner liegt, neu auf;
  `ingest-a-mail-folder.md` sagt deshalb, die Mail auch im Ordner zu löschen
  (PI §6).
- Benannt, nur bei Fehlbedienung: der frühe Rücksprung von `append` bei
  `SourceKeyTaken` überspringt den Vergleich der Inhaltsidentität; ein
  ankommender `artifact_hash`, der nicht 32 Bytes hat, schaltet den Vergleich
  für diesen Schlüssel ab, und ein gespeicherter, der kein Hex aus 64 Zeichen
  ist, zählt als keiner (P-PI, Aufgabe 1; `hash-format.md` nennt den letzten).

### Feststellungen und Entitäten (ohne Teilprojekt)

- Projekt als Geltungsbereich einer Regel: `project:<name>` ist vorgesehen,
  und der Schreibweg weist es ab, bis es eine Zuordnung von Events zu
  Projekten gibt (PG §2.3, §11 Punkt 3; die Zuordnungen, F §1).
- Wie Projekte entworfen werden, zu entscheiden mit dem Spec der Zuordnungen
  (MK §4.1, §10 Punkt 1; F §1, §15). Die Idee des Betreuers: ein Projekt als „Kreis von Kreisen“,
  rekursiv aufgelöst, mit Unterprojekten — „sind Projekte nur Mengenlehre über
  Identitäten?“ **Die Gegenthese** aus dem Gespräch vom 2026-10-10: Kreise in
  Kreisen tragen (die Policy erbt die strengste Regel, die Chronik umfasst die
  Unterkreise); ein Projekt ist aber keine Menge von Identitäten — dieselben
  drei Leute arbeiten an zwei Projekten —, sondern eine Zuordnung von Events
  (eine Feststellung), die einen Kreis als stärkstes Signal hat, mit einem
  Ziel und einem Zeitraum; Unterprojekte über Projekte, die auf Projekte
  zeigen. In der MCP-Schnittstelle sind `project` und `matter` als Parameter
  des Werkzeugs `previously` reserviert.
- **Kreise für Quellen ohne Adressen.** Ein Kreis ergibt sich heute nur aus
  Adressen in `channel_identities` (`circles_of` in `core/decide.py`). Eine
  Aufnahme, ein Transkript oder eine Datei aus Nextcloud hat keine und gehört
  darum zu keinem Kreis: freigeben kann sie nur eine Regel `source:<name>`,
  nie die Regel eines Kunden, und `previously access --circle` sieht sie
  nicht. Zu entscheiden mit den Projekten (Punkt oben): die Zuordnung eines
  Events zu einem Kreis als Feststellung wäre derselbe Mechanismus.
  Aufgefallen am 2026-10-11 bei der Frage des Betreuers nach anderen
  Eingängen des MCP-Servers (siehe *MCP-Lesezugang*).
- Die Idempotenz einer Handlung ist weiter „Sache des Aufrufers"; der
  zweite Schreibweg, der der Feststellungen, hat sie über die Kennung des
  Handles (PP, A1 S1 und Zeile 19; die Hälfte zu `assertion` steht unter
  *Erledigt*).
- `verify` prüft Regeln je Art für `action` und, seit Einheit 5, für
  `assertion`; eine Wahrnehmung ohne `evidence` und ohne Schlüssel besteht
  weiter (PP, A1 S2, Messungen M3 und M4; die Hälfte zu den Feststellungen
  steht unter *Erledigt*).
- Keine Validierung der Nutzlast gegen ein Schema je Art, gegen Architektur
  §4.1 (PP, A1 Zeile 20).
- Wer tilgt: der 1a-Spec nennt für das Tilgungs-Event „Zeitpunkt, Anlass und
  Urheber", es trägt die ersten beiden; das System kennt noch keine Personen
  (1c §12 Punkt 5).
- Ein Event ohne Einheiten erscheint in `p_chronicle` gar nicht (PP, A1 S4;
  die Hälfte zu den Verweisen einer Feststellung steht unter *Erledigt*).
- Zuordnung zu Projekten: `p_chronicle` bekommt `project`, der Index seine
  erste Spalte (1b §10 Punkt 6, AA §10 Punkt 9).
- Weitere Fundorte: dieselbe Mail in einem zweiten Ordner schreibt nichts,
  nur der erste Fundort steht im Log, unter `found_in`. Mit den Zuordnungen
  wird das Ablegen eine Zuordnung, und die kann mehrfach sein (PI §3.4, §11 Punkt 2;
  `connectors.md`).
- Gesprächsfäden sind eine Form von Vorgang, kein Begriff von Mail: eine Mail
  führt zu einem Termin mit Videokonferenz, der zu einem Chat, und alles
  gehört zu einer Sache (Betreuer, 2026-10-06). Ein Faden ist darum eine
  Zuordnung über Kanäle hinweg — Feststellung (die Zuordnungen), als Vorschlag aus
  der KI-Schicht hinter dem Gate (Einheit 6). Mail liefert Signale, keine
  Struktur: `In-Reply-To` und `References` unter `headers`, eine Einladung
  als `.ics`-Anhang, ein Link zu einer Konferenz im Text. Offen auch, ob
  zitierter Verlauf in Antworten in der Chronik ausgeblendet werden soll —
  Zitate zu erkennen ist Deutung (PI §3.4, §11 Punkt 10).
- Fünf der neun Leitsätze (1, 2, 5, 7, 8) hatten noch keinen Kontakt mit Code
  (PP, A1 Frage 4).
- **Die Zuordnungen, mit eigenem Spec als Nächstes:** Events zu Projekten und
  Vorgängen, Quellen ohne Adressen zu einem Kreis, weitere Fundorte einer Mail
  (die Punkte oben). Leitbeispiel des Betreuers (2026-10-12): Markus und er
  sind im selben Verein und haben beide eine Firma; sie schreiben sich über
  die Firmenadressen zu Themen des Vereins. Die Organisation folgt also nicht
  aus der Adresse, sondern aus dem Thema — eine Zuordnung hängt am Inhalt, als
  Feststellung über Events, nicht an der Identität; das stützt die
  Gegenthese zu „Projekte sind Mengenlehre über Identitäten" (F §1, §15).
- Adressbücher als Quelle, 1..n, in beide Richtungen (Betreuer, 2026-10-12):
  Kontakte etwa aus der Nextcloud lesen ist ein Konnektor, Kontakte werden
  Wahrnehmungen; neue Adressdaten aus Mails von Neukunden zurückschreiben ist
  eine Handlung in einem Fremdsystem, mit Befugnis (F §15).
- Der Identitätsgraph: Personen und Organisationen als Projektionen über
  Feststellungen, Zuordnungen tragfähiger Verweise (`address:` → `person:`),
  `circle:` → Organisation, und wer `human:operator` ist. `name:` gehört nicht
  dazu, es wird je Verpflichtung durch eine neue Fassung präzisiert. Mit dem
  Graphen fragt das System zurück: ein `name:`, den es keiner Person zuordnen
  kann, wird eine Rückfrage mit den Kandidaten, die einen Bezug zu den
  Kreisen der Quellen haben, und die Antwort ist eine neue, direkte Fassung
  (`list_triage`, `write_triage_answer`, MK §4.2–§4.3; F §2.1, §15).
- Das Teilen einer Verpflichtung, Aufgaben, die transitive Verantwortung mit
  Freigabeklassen, die beobachtete Erfüllung — im Piloten ist Erfüllung eine
  Feststellung mit Quelle, weil kein Konnektor Arbeit sieht (F §1, §4, §15).
- Ob ein Kreis umbenannt werden kann, ohne dass `circle:`-Verweise in
  Feststellungen ins Leere zeigen (F §15).

### Zuordnungen (Phasen 1–4)

Phase 1 ist abgenommen (PR #24, `cce8b4b`), die Seiten stehen (`explanation/graph.md`). Was sie offen
lässt, mit ihrem Ausführungsprotokoll (`sdd/2026-10-14-zuordnungen-phase-1/`,
das mit der Endprüfung ins Repository kommt):

- **Der Rest von einem Bit beim Zyklus.** Ein Modell wird für einen Zyklus nie
  abgewiesen, und keine Klasse deckt eine Art mit dem Verhalten `acyclic`, so
  dass seine Fassung davon immer `open` bleibt (P-Z1, Ruling T6-a). Übrig
  bleibt: `write_approve` und `write_triage_answer` über MCP weisen eine
  Freigabe, die einen Zyklus schlösse, mit einem Satz ab, der einem von der
  Person bestätigten Aufruf ein Bit über Kanten sagt, die der Client nicht
  sehen darf (`mcp-tools.md`, `explanation/graph.md`). Der Preis ist gewollt;
  zu entscheiden bleibt, ob eine spätere Phase ihn ganz abträgt (Z §9.4).
- **`verify` wächst überlinear über azyklischen Kanten, etwa quadratisch.**
  Jede Kante einer azyklischen Art wird gegen die Kanten davor geprüft.
  Gemessen von der Endprüfung am 2026-10-14, nur Kanten `part_of`, Median
  aus drei Läufen, ohne Befund: als Kette 1 000 Kanten 0,84 s, 2 000 2,34 s,
  5 000 14,84 s; als Baum 0,78 s, 2,10 s, 13,05 s — zweieinhalbmal so viele
  Kanten, sechsmal so lang; eine Kette aus 10 000 Kanten 78,6 s, ein Lauf.
  (Aufgabe 4 hatte 0,57 s und 1,77 s für die Kette gemessen; die Zahlen der
  Endprüfung ersetzen sie.) Ein ganzes Log mit 10 000 Beziehungen (1 000
  davon `part_of` als Baum) prüfte `verify` in 2,77 s, bei 2 000 in 0,62 s,
  bei 100 000 in 135 s, ein Lauf auf festem Stand von `9967268` (P-Z1,
  Ruling T4-c). Als täglicher Job bleibt das tragbar; wächst der Graph weit
  darüber, wird die Prüfung auf Zyklen in `verify` inkrementell, spätestens
  mit Phase 2.
- **Jeder MCP-Aufruf faltet den ganzen Graphen für die Zahl im Kopf.** (Seit
  Phase 2 gemildert: der Kopf liest `p_graph_thread` und faltet nur Fäden mit
  Einwand, siehe die Punkte unten zum Schreibweg und zu `list_entities`; die
  Messung von Phase 1 bleibt als Beleg.) Um die
  anhängigen Einwände zu zählen, faltet `Service.answer` vor jedem Werkzeug
  den Graphen und fragt die Policy nach den Quellen jedes Einwands, auch bei
  `whoami` und den Werkzeugen der Einheit 5, die den Graphen sonst nie lesen.
  Gemessen von der Endprüfung am 2026-10-14, Median aus drei Läufen, bei
  10 000 Beziehungen und 5 000 Entitäten: `whoami` 0,52 s, `list_entities`
  1,72 s, `read_graph` 0,47 s, `previously entities` 0,53 s, ein Schreiben
  0,47 s, `verify` 2,77 s; bei 2 000 Beziehungen `whoami` 0,10 s,
  `list_entities` 0,28 s, `verify` 0,62 s. Bis 10 000 wächst es linear. Bei
  100 000 Beziehungen und 50 000 Entitäten, auf festem Stand von `9967268`
  (i7-11370H): `read_graph` 7,35 s (Median aus drei), in Einzelläufen
  `whoami` 7,69 s, `list_entities` 23,7 s, mit 20 Einwänden 7,33 s und
  24,2 s; aus dem ersten Lauf `entities` 7,59 s, `relations --at` 7,50 s,
  ein Schreiben 7,34 s — sechzehnmal so lang für zehnmal so viel. Bei
  10 000 tragen Listen, Schreiben und Kopf noch, `list_entities` liegt mit
  1,7 s schon über einer Sekunde; bei 100 000 trägt keins davon. Phase 1 nimmt die Kosten
  hin (Ruling F-c): ein Zwischenspeicher, der am Tip hängt, verfällt mit dem
  Zugriffseintrag jedes Aufrufs, und beim Piloten mit einigen hundert
  Aussagen sind es Millisekunden. **Phase 2 braucht eine Projektion oder eine
  inkrementelle Faltung, bevor die Daten wachsen** (Planentscheidung 14,
  Z §3.4; gebaut in Phase 2, die Leser lesen die Projektion); `explanation/graph.md` trägt die Zahlen. Die Messungen der
  Aufgabe 6 (`whoami` bei 1 000 Entitäten ohne Beziehungen 53 ms, bei 5 000
  153 ms) stehen dort daneben.
- **`verify` hält vom Vokabular und von den Freigabeklassen nur die Form
  fest.** Der Schreibweg weist beim Vokabular eine Art ab, die eine Art nennt,
  die nicht steht (auch einen `ref` auf eine Beziehungsart), das Stilllegen
  einer Art, die eine andere braucht, und eine umgeformte eingebaute Art
  (`core/vocabulary.py`, `refusal`); bei einer Klasse eine Art, die nicht
  steht, und eine azyklische Art (`core/classes.py`, `_refusal`). `verify`
  prüft davon nur die Form. Schaden richtet das nicht an, der Lesepfad
  neutralisiert beides (nur Beschriftungen einer eingebauten Art,
  `conformance_problem` weist Enden von Arten ab, die nicht stehen,
  `_covering` prüft azyklisch); der Docstring von `_Claims` sagt es seit der
  Endprüfung. `verify` faltet das Vokabular schon in Kettenfolge
  (`VocabularyFold`) und könnte je Event `refusal(before, [spec])` fragen
  (P-Z1, Endprüfung M3).
- **Offene Enden und offene Kanten zählen als stehend.** `EntityTypes`
  (`graph_write.py`) und `Graph.entities()` geben auch Entitäten zurück, die
  nur ein Modell vorgeschlagen hat, und `relations()` offene Gewinner. Eine
  direkte Beziehung des Betreibers oder eine Freigabe kann also auf eine nur
  vorgeschlagene Entität zeigen, auch ein direktes `member_of` auf einen
  vorgeschlagenen `circle`. In Phase 1 harmlos. Phase 2 (`chronicle --in`)
  und Phase 3 (das Gate) müssen beide Enden und die Kante nach Stufe filtern;
  das Gate liest nur direkte Enden (P-Z1, Endprüfung M4).
- **Die eingebauten Arten stehen im Code, `verify` misst alte Aussagen an der
  heutigen Form.** `VocabularyFold.add` ersetzt die Form einer eingebauten
  Art an jeder Stelle durch die des Codes. Gibt Phase 3 `member_of` weitere
  `from`-Arten (Adresse, Domain) und `in_circle` ein Ereignis als Beginn, wird
  jedes frühere `member_of` am neuen Code gemessen; nimmt sie `person` oder
  `organization` aus `from`, werden Mitgliedschaften der Phase 1 zu Befunden.
  Unter Phase 3: die Verbindungen einer eingebauten Art dürfen nur wachsen,
  oder ihre Form bekommt eine Version (P-Z1, Endprüfung M5).
- **Triage, Freigabe und Antwort stehen zweimal, je Oberfläche einmal.**
  `cli.py` `_waiting` entspricht `mcp_server/read.py` `waiting_versions`,
  `_approval_of` dem `replace(…)` in `graph_approval_write`, die Antwort in
  `cli.py` der in `triage_answer_write`. Z §7.5 will, dass `status` und der
  MCP-Kopf dasselbe zeigen, und zwei Sortierungen laufen auseinander.
  Mechanisch: `waiting_versions`, `approval_of(thread, version, reason)` und
  `answer_of(question, choice, reason)` nach `core/graph_write.py`, von beiden
  benutzt; die vorhandenen Tests halten es (P-Z1, Endprüfung M8).
- **Der Platzhalter einer verborgenen Entität verschwindet, wenn ihr letzter
  Vorschlag abgelehnt wird.** `list_entities` zeigt für jede verborgene
  Entität mit Gewinner einen Platzhalter; ein Faden ohne Gewinner fällt
  heraus (`read.py`, `entities`). Das ist ein Bit über Aktivität auf einem
  verborgenen Faden, die Art Signal, die Ruling T6-b aus der Triage genommen
  hat; Verpflichtungen verhalten sich ebenso. Zu entscheiden, ob ein
  Platzhalter bleibt, solange der Faden besteht (P-Z1, Endprüfung). Seit dem
  Zweig `worktree-rueckmeldung-a7` bleibt der Platzhalter einer verborgenen,
  widerrufenen Entität unter jedem Filter stehen, mit Absicht (Option A des
  Betreuers).
- ~~**Ein Ereignis als Beginn einer Beziehung, was Phase 2 ändern muss.**~~
  Erledigt in Phase 2 (Aufgaben 1 und 2, `5f791e6`, `fbdd05e`, `a6d358a`).
  Der alte Wortlaut: Die
  Form (`RelationBody.start: int | Source`) nimmt es schon an,
  `conformance_problem` weist es in Phase 1 mit einem Satz ab, und `reaches`,
  `closes_cycle`, `relation_ends` und `relation_visible` überspringen es.
  Phase 2 ändert: die Abweisung und den `int`-Cast in `_ends_conformance`,
  `EntityTypes` und die Enden, und `relation_visible`, das für jeden
  Source-Beginn `False` gibt (P-Z1, Endprüfung).
- **Das Vokabular kann sich zwischen Vorschau und Schreiben von `vocabulary
  apply FILE` ändern.** `_cmd_vocabulary_apply` zeigt die Unterschiede aus
  einer Transaktion, `apply_vocabulary` rechnet sie unter dem Tip neu und
  schreibt, was dann abweicht; ein Vokabular-Event dazwischen wird
  überschrieben, ohne gezeigt worden zu sein. Dasselbe Muster wie bei
  `policy`, mit einem Betreiber harmlos. `--base` rechnet die fehlenden Arten
  seit der Endprüfung in der Schreib-Transaktion (P-Z1, Ruling F-a).
- **`cli.py` teilen.** 4 274 Zeilen zur Endprüfung; die Befehle des Graphen
  stehen in einem Block (etwa Zeilen 2 995–3 950) und könnten ohne
  Verhaltensänderung `previously/cli_graph.py` werden (P-Z1, Endprüfung).
- **Zurückgestellte Kleinigkeiten, die Erinnerung verdienen:**
  - Aufgabe 1: Eine Art, die eine eingebaute nennt, lässt sich stilllegen,
    ohne dass die Prüfung der Verweise greift — `person` stilllegen, während
    das eingebaute `member_of` sie nennt, wird nicht abgewiesen und ist
    ungetestet.
  - Aufgabe 3: Die Trefferquote zählt eine Fassung als korrigiert, wenn eine
    spätere transitive Fassung desselben Fadens freigegeben wird (folgt dem
    Auftrag, ungeprüft festgehalten), und der Gleichstand zweier Klassen
    nimmt die Kennung des jüngsten Ereignisses je Name, so dass eine neu
    gesetzte Klasse ihr Dienstalter gegen eine gleichrangige verliert.
  - Aufgabe 5: Die Spalte der Art zeigt die Beschriftung und nicht den
    Bezeichner, so dass eine Liste nicht unmittelbar `--type` füttert (die
    Seite einer Entität zeigt beides).
  - Aufgabe 1: `_text` in `core/vocabulary.py` nimmt `isprintable()` und weist
    damit ein geschütztes Leerzeichen in einer Beschriftung ab. Strenger ist
    sicher; mit einer gemeinsamen Textregel zusammenzulegen, wenn sie kommt.
  - Aufgabe 1: `tests/test_wheel.py` baut das Wheel zweimal. Kostet nur
    Testzeit.
- **Weitere Fundorte einer Mail (Z §8, später; Planentscheidung 12 der Phase
  2).** Dieselbe Mail liegt in mehr als einem IMAP-Ordner, und aus jedem Fundort
  kann ein Hinweis auf eine Klammer kommen. Der Betreuer am 2026-10-15: „nicht
  vergessen, nichts verbauen". Verbaut ist nichts: eine Zuordnung, die die
  Aufnahme schreibt, ist eine gewöhnliche `concerns`-Beziehung mit dem Event als
  Anfang und Quelle, und nichts in Phase 2 nimmt an, dass nur Menschen oder
  Modelle `concerns` schreiben. Offen: wer sie schreibt (der Betreiber über eine
  Zuordnung von Ordner zu Klammer, oder eine Regel) und auf welcher Stufe.
- **Der Schreibweg faltet noch den ganzen Log.** Er prüft unter dem Tip, und
  die Projektion hinkt in der Transaktion eines Schreibvorgangs nach; ebenso
  `verify`, `--as-of` und `project --check`. Gemessen in Phase 1: 7 s je
  Schreibvorgang bei 100 000 Beziehungen. Für den Piloten tragbar; eine
  Aufgabe, bevor der Graph wächst (Planentscheidungen 5 und 7).
- **Jeder Nachzug der Projektion `graph` liest alle `approval_class`-Handlungen.**
  Die Projektion braucht die Klassen, um einen Faden neu zu falten, und liest
  sie bei jedem Batch, der etwas berührt (Aufgabe 3, ungemessen).
- **MCP `list_entities` faltet jede Entität einer Seite einzeln aus dem Log.**
  Die Richtlinie entscheidet jede Entität vor jedem Filter, und der Platzhalter
  einer zurückgehaltenen Entität besteht jeden Filter; ein Filter nach `types`
  in SQL ließe ihn aus und bräche Option A (Aufgabe 4, M-4, bewusst nicht
  gebaut). Kostet ein Lesen je Entität.
- **Die Kosten von `seen_members` und `_last_member` sind ungemessen.**
  `seen_members` wächst mit den verborgenen entscheidenden Kanten (eine Klammer
  mit nur verborgenen Mitgliedern antwortet etwas langsamer als eine leere,
  derselbe Zeitunterschied wie beim nächsten Punkt), `_last_member` liest die
  Payloads aller Mitglieds-Events je Aufruf (Aufgabe 5; die Endprüfung misst).
- **`ProjectionGap` aus einem Nachzug fängt der Rückfall der Leser nicht.**
  `ProjectionRebuilt` und jeder `StorageError` fallen auf das Falten zurück, ein
  `ProjectionGap` noch nicht (Aufgabe 4, Endprüfungswelle).
- **Zeitunterschied zwischen verborgener und fehlender Klammer.** Beide
  antworten mit demselben Satz, aber eine verborgene Klammer geht erst durch die
  Sichtbarkeitsprüfung; ein Client könnte den Unterschied messen. Die Probe ist
  grob, gibt keinen Inhalt frei und ist von der Art, die die Schreibwerkzeuge schon hinnehmen (Aufgabe 5, Review ⚠️ 4).
- **Zurückgestellte Kleinigkeiten aus Phase 2:**
  - Aufgabe 1: Kein Test für eine zurückgezogene Entität als Ziel `*`.
  - Aufgabe 2: Der Zweig für einen Ereignis-Beginn in `cli.py`
    `_claim_fields` hat keinen Aufrufer (nur Entitäten-Historien erreichen
    ihn); toter Code, in der Endprüfungswelle zu entfernen.
  - Aufgabe 3: Der Test der gleichzeitigen Nachzüge nimmt an, dass die Leser
    die Sperre abwechseln; nichts erzwingt es. Eine mögliche Flocke
    (`test_two_catch_ups_at_once…`), deterministisch zu machen.
  - Aufgabe 4: Die Rückfalltests der Kommandozeile decken `entities`, `triage`
    und `status`, nicht `relations`, `show` und `classes` (derselbe Helfer);
    die Warnung trägt `str(error)`, bei `ServerUnreachable` mit Datenbank,
    Host und Port, nie mit Passwort.
- **Eine Rolling-Update-Lücke ohne Lösung.** Zwei Versionen nebeneinander
  bauen die Projektion einander um, jeder Aufruf fällt auf das Falten zurück
  (richtig, langsamer). Der Handoff sagt es: das Update zu Ende führen, dann
  `previously project`.
- **Phasen 3 und 4 selbst**, im Spec ausgearbeitet und nicht gebaut (Phase 2,
  die Zuordnung von Events und Einheiten mit `chronicle --within` und `within`
  über MCP, ist gebaut, der Parameter heißt `within` und nicht `in`): Kreise im Graphen, die das Gate liest, mit
  der schweren Prüfung der Sicherheitsgrenze (Z §9, Phase 3), und
  Verpflichtungen und Entscheidungen im Schema (Z §11, Phase 4). Jede mit
  eigenem Plan, Merge, Release und Abnahme (Z §1, §17); `concerns`
  mit Ereignis als Beginn kam mit Phase 2, `in_circle` mit Ereignis als Beginn
  kommt mit Phase 3 (P-Z1, Ruling P-2).

### Projektionen

- Eine neue Projektion kostet Methoden im Store-Protokoll, ihre SQL-Umsetzung
  und eine Migration — nicht nur eine Versionsnummer; `write_projection(name,
  rows)` aus der Architektur wurde zu getypten Methoden je Tabelle, ohne
  aufgeschriebenen Grund (PP, A1 Zeile 30 und S5; A2, §10.1).
- Neubau an Ort und Stelle statt Schattentabelle mit Umschaltung; ein Leser
  sieht während des Neubaus eine leere oder halbe Projektion. Architektur §7.3
  Regeln 3 und 4 verlangen das Gegenteil, ein Grund ist nicht aufgeschrieben
  (PP, A2). Gemessen bei 700 000 Events: der Neubau dauert fünf bis sieben
  Minuten, der Eingang läuft dabei weiter, und die Standardausgabe von
  `chronicle` und `stats` sieht in dieser Zeit vollständig aus — `stats`
  zeigt Teilsummen. Der einzige Hinweis ist die Rückstandszeile auf der
  Standardfehlerausgabe, im Wortlaut eines gewöhnlichen Rückstands (PP,
  Bericht C). Zu entscheiden: die Schattentabelle bauen, oder dabei bleiben,
  den Neubau in der Meldung benennen und es auf eine Seite schreiben.
- Jede Projektion liest das ganze Log für sich: 29 % eines Neubaus sind
  doppeltes Lesen, und `source-stats` liest alle Inhalte, um Einheiten zu
  zählen (PP, Bericht C).
- Der Neubau leert mit `DELETE`: bei 700 000 Events bleiben 5,1 Millionen tote
  Zeilen, bis `VACUUM` sie räumt; die Wirkung ist ungemessen (PP, Bericht C).
- Dass der Eingang während eines Neubaus weiterläuft, ist gemessen, aber von
  keinem Test bewacht; die Architektur nennt es als Nachweis für Stufe 1b
  (PP, A2 und Bericht C).
- `Projection.write` könnte sich eine eigene Transaktion nehmen (1b §10, F9);
  `projection_state.version` ohne `CHECK` (F12). Beide vor der dritten
  Projektion zu entscheiden.
- `previously stats` ohne Zeitraum; ein Zeitraum wäre eine neue Projektion
  (1b §10 Punkt 7).
- Die Projektionsnamen stehen zweimal: in `core` und als Abbildung auf die
  Tabelle in `storage` (PP, A2).
- `_catch_up_after` in `cli.py` hört an der ersten Projektion auf, die
  scheitert, und nennt die übrigen nicht: scheitert `chronicle`, wird
  `source-stats` weder nachgezogen noch im Satz genannt. Eine gescheiterte
  Löschung hält das Nachziehen seit Commit `b9b0cdc` nicht mehr auf (P-1c;
  Nachprüfung der Endkorrektur).
- Zwei Releases gegen eine Datenbank bauen eine Projektion gegeneinander neu:
  ein Nachziehen baut neu, sobald die Fassung, die es findet, von seiner
  abweicht, in beide Richtungen. `ProjectionRebuilt` hält einen Lauf an, der
  das zwischen zwei Stapeln bemerkt (Commit `3ae7038`); das Hin und Her über
  Läufe hinweg verhindert nichts. Die Anleitung `rebuild-a-projection.md` sagt,
  den Prozess der anderen Release anzuhalten (Endkorrektur, Teil 2).
- `occurred_at` einer Mail kommt aus `Date`, der Uhr des Absenders, und kann
  falsch sein. Beide Zeiten stehen in der Nutzlast (`date_source`,
  `internaldate`); welche die Chronik ordnet, wenn sie weit auseinanderliegen,
  ist nicht entschieden (PI §11 Punkt 4).
- Die Variante in der Chronik: eine Variante erscheint als zweites Event, und
  die Chronik sagt nicht, dass sie eine ist; nur die Standardfehlerausgabe von
  `ingest imap` und `variant_of` in der Nutzlast sagen es (PI §11 Punkt 6).
- `p_chronicle` hält den Inhalt jeder Einheit ein zweites Mal und ist damit
  größer als die Tabelle `unit`: 1,9 GB gegen 1,4 GB bei 700 000 Events; ihr
  Schreiben ist mit 48 % der größte Posten eines Neubaus (PP, Bericht C).

### Storage-Schnittstelle

- Worauf `core` baut, steht nicht im Protokoll: Isolationsstufe von `begin()`
  und `snapshot()`, die Fehlerklassen `ChainPositionTaken` und
  `SourceKeyTaken` aus `previously.storage.errors`, und dass `LogStore` und
  `ProjectionStore` eine Verbindung teilen (PP, A2 Frage 2).
- Drei der fünf Eigenschaften aus Architektur §5 gelten nicht mehr oder nur
  für `LogStore`, und keine Seite begründet eine der fünf (PP, A2;
  `design-records.md`).
- Vier Lesemethoden außerhalb jedes Protokolls, heute nur von `cli` benutzt;
  ein zweiter Einstieg braucht sie (PP, A2).
- `stream(project=…)` aus der Architektur kam nicht; der 1a-Spec schob es nach
  1b, der 1b-Spec nennt es nicht (PP, A2).
- Der Docstring von `SourceKeyTaken` sagt „Do not retry", `append` wiederholt
  im Teilfall (PP, A2).
- `show` liest Event und Einheiten in zwei Anweisungen; die Begründung im
  Kommentar gilt nur, solange nichts ein Event nach dem Commit umschreibt
  (P-AA).
- `WatermarkStore`: Werte von `position`, die keine Zeichenketten sind, prüft
  niemand, und der Zweig für ein `set_at` mit `utcoffset() is None` ist nur
  zur Hälfte geprüft; beides nur bei Fehlbedienung erreichbar (P-PI, Aufgabe
  3).

### Tilgung

- Aufnehmen und Tilgen zugleich: sieht ein `append --attach`, dass ein Blob
  schon liegt, und tilgt ein `redact` in diesem Augenblick dessen letzte
  Referenz, zeigt das neue Event auf ein Objekt, das fehlt. `verify --blobs`
  meldet es, `concurrency.md` benennt es, verhindert wird es nicht (1c §12
  Punkt 2; P-1c).
- Die Weigerung „is a redaction" trifft jedes Event der Art `action`; heute
  ist jede Handlung eine Tilgung, mit der zweiten Art von Handlung ist der
  Satz falsch (`core/redact.py`, der Kommentar daneben sagt es; P-1c).
- `redact_event` nimmt die Blobs eines Events nur aus dem Register. An einem
  beschädigten Register, das `verify` meldet, nennt und löscht die Tilgung
  einen Blob nicht, den nur die Nutzlast nennt. Mit der Nutzlast vereinigen
  oder die Tilgung abweisen — nicht entschieden (ruling E-6 der
  Endkorrektur).
- Ein Schlüssel je Betroffenem und das Krypto-Schreddern (1c §12 Punkt 6).
- Eine Mail tilgt `redact units` nicht: der Betreff steht auch unter
  `headers`, die Rohmail ist ein Blob, und `artifact_hash` ist ungesalzen und
  bestätigt einen kurzen Text — ein Salz zerstörte seinen Zweck, zwei
  Sichtungen müssen denselben Wert ergeben. Tilgen heißt bei Mail
  `redact event`; `erasure.md`, `erase-something.md` und
  `ingest-a-mail-folder.md` sagen es. Ob `redact units` an einem Event mit
  `artifact_hash` warnen oder abweisen soll, ist nicht entschieden; derselbe
  ungesalzene Hash bleibt nach `redact units` auch an einem Event von
  `append --text` stehen (ruling T1-a der Aufnahme, P-PI).
- Tilgen gilt je Event, nicht je Inhalt: eine getilgte Mail, die jemand
  erneut als Anhang weiterleitet, kommt als Anhang der neuen äußeren Mail
  wieder in den Bucket; ihr eigenes Event bleibt getilgt und bekannt
  (Prüfung der Aufgabe 4, P-PI; `erasure.md`). Ob die Aufnahme einen getilgten
  Inhalt wiedererkennen soll, ist eine Frage an den Spec der nächsten Einheit,
  die Tilgung berührt.
- Eine Mail steht in mehr Events als ihrem eigenen: ihre Varianten unter
  `<Message-ID>#<16 Hex>` mit eigener Rohmail, die Mails in ihr auf jeder
  Tiefe, und jede Mail, die sie als Anhang trug, deren Rohmail sie ganz
  enthält. Kein Kommando findet sie; `ingest-a-mail-folder.md` gibt eine
  rekursive SQL-Abfrage, gegen die Testcontainer geprüft. Eine Mail, die sie
  nach der Tilgung erneut weiterleitet, findet auch die Abfrage nicht mehr,
  nur die notierte Adresse der Rohmail über `event_blob` (Endprüfung Doku,
  Befund I1, P-PI).
- Zitate in Antworten überleben eine Tilgung: wer den Inhalt einer Mail
  tilgen muss, tilgt auch die Antworten, die sie zitieren. Kein Kommando
  findet sie; `ingest-a-mail-folder.md` gibt eine SQL-Abfrage über
  `In-Reply-To` und `References`, und eine Antwort, die zitiert, ohne die Mail
  zu nennen, findet auch sie nicht (PI §6).
- Das Ziel von `redact event` und `redact units` ist eine `id`, und eine `id`
  überlebt keine Wiederherstellung: sie vergibt jede `id` über ihrer Spitze
  neu (`id` = Spitze + 1). Eine Tilgung, nach einer Wiederherstellung wörtlich
  wiederholt, kann ein anderes Event treffen. Die Anleitung
  `restore-from-a-backup.md` lässt den Leser das Ziel am `hash` bestätigen,
  den er bei der Tilgung notiert hat; ob `redact` selbst sein Ziel gegen
  etwas prüfen soll, das eine Wiederherstellung überlebt — den `hash` des
  Events —, ist nicht entschieden (Prüfung der Aufgabe 8, P-1c). Die
  Codeprüfung der Endprüfung schlägt eine Option `--hash` an `redact event`
  und `redact units` vor, gegen die gesperrte Zeile geprüft, bevor etwas
  geschrieben wird — empfohlen vor dem Piloten.

### Blobs und Speicher

- Verwaiste Blobs: scheitert das Anfügen nach dem Speichern, bleibt ein Blob
  ohne Event; ihn zu finden heißt, den Bucket gegen `event_blob` zu halten,
  gebaut ist das nicht (1c §12 Punkt 1). Ebenso lässt ein abgewiesenes
  `append --attach` seine neuen Blobs im Bucket (P-PI, Aufgabe 1).
- Ein Objekt ohne Event bei der Aufnahme: die Blobs eines Stapels, der nicht
  angefügt wurde, liegen bis zum nächsten Lauf ohne Event, der sie dann
  vorfindet; für immer nur, wenn die Mail vorher aus dem Ordner verschwindet,
  dieselbe Grenze wie oben (PI §4.2, §11 Punkt 7).
- Hochladen ohne Zwischendatei; heute braucht das Aufnehmen Platz in der
  Größe des größten Blobs (1c §2.3, §12 Punkt 10).
- Bedingtes Schreiben (`If-None-Match: *`) machte aus „erster gewinnt" ein
  Schloss statt eines Nachsehens; dafür müsste das Hochladen in Teilen von
  Hand gebaut und an Hetzner gemessen werden (1c §2.7, §12 Punkt 13).
- Ein beschädigtes Objekt ersetzen: „erster gewinnt" lässt es liegen, ein
  Kommando, das einen Inhalt bewusst neu ablegt, gibt es nicht (1c §2.7, §12
  Punkt 14).
- `pyrage` 1.4.0 kehrt beim Versiegeln eines kleinen Inhalts normal zurück,
  wenn der eine Schreibzugriff der Senke scheitert (gemessen am 2026-10-05,
  12 Bytes; bei größerem Inhalt wirft es). Im Baum umgangen, `core/sealing.py`
  beobachtet Quelle und Senke selbst; dem Projekt `pyrage` nicht gemeldet
  (P-1c).
- `s3transfer` hält den Fehler eines abgewiesenen Hochladens in Zyklen, samt
  der Verbindung. Im Baum umgangen, `put` in `storage/s3.py` wirft den
  eigenen Fehler unverkettet; nicht gemeldet (P-1c).
- Die Lesefrist des S3-Clients, 20 s (`_READ_TIMEOUT` in `storage/s3.py`), ist
  gegen keinen langsamen echten Speicher erprobt, auch nicht der Fall, dass
  die Antwort auf einen Teil eines Hochladens länger braucht (P-1c).

### Aufnahme aus IMAP (Pilot, Einheit 1)

- Die Aufnahme hält nur den Posteingang: im Testordner in kup6s stehen nur
  empfangene Mails, und Claude Code bemerkte, dass keine Antwort des Betreuers
  im Log ist. Für den regulären Gebrauch will der Betreuer den größten Teil
  seines Posteingangs und alles Gesendete, Spam und Belangloses
  herausgefiltert. Wie die Mail in das eine Postfach kommt, das die Aufnahme
  liest, entscheidet kup6s; ob ein Job je Ordner oder ein Sammelordner, ist
  auf beiden Seiten offen (RG). Ein Lauf liest seit dem Zweig
  `worktree-imap-ordner` mehrere Ordner eines Postfachs (`--folder`, unten
  unter *Erledigt*); wie sie genutzt werden — gesendete Mails, Sammelordner,
  Filter —, ist damit nicht entschieden und bleibt dieser Punkt.
- `IDLE`, Aufnahme ohne Zeitgeber, mit dem MCP-Dienst denkbar (PI §1,
  §11 Punkt 5).
- Eine Weiterleitung als zitierter Text bleibt Text der äußeren Mail; sie zu
  zerlegen wäre Deutung, und ob das eine spätere Einheit leisten soll, ist
  offen. Die Anleitung bittet um Weiterleitung als Anhang (PI §3.6, §11
  Punkt 11).
- Der Alt-Text von Bildern fällt weg (`ignore_images`, damit die Adressen von
  Zählpixeln nicht in den Text kommen); auf `mail-mapping.md` benannt (ruling
  T2-g der Aufnahme, P-PI).
- `html2text` schreibt Markdown: `<br>` als zwei Leerzeichen und Umbruch,
  Fettes als `**`, Links als `[Text](Adresse)`, und es maskiert Zeichen, die
  Markdown beginnen würden (`1\.`); benannt (ruling T2-g der Aufnahme, P-PI).
- Ein unmaskiertes `<` im HTML verschluckt den Text bis zum nächsten `>`
  (`a<b and c>d` wird `a**d`); benannt (ruling T2-g der Aufnahme, P-PI).
- Eine kaputte Adressliste bildet ab, so weit der Parser kommt; die übrigen
  Adressen fehlen in `channel_identities` und stehen nur in `headers` und der
  Rohmail; benannt (ruling T2-g der Aufnahme, P-PI). Eine Kopfzeile, an der
  der Parser wirft (`To: a@example.org, "`), trägt seit der Fixwelle keine
  Adresse bei, statt die ganze Mail unlesbar zu machen.
- Undurchsichtig signiertes S/MIME (`smime-type=signed-data`) liest sich als
  `no readable body: attachments only`, der signierte Inhalt ist ein Anhang;
  benannt (ruling T2-g der Aufnahme, P-PI).
- Mails ohne Message-ID mit gleichem Betreff, Körper und Anhängen — ein
  tägliches „Backup OK" — verschmelzen zu einem Event, weil ihr Schlüssel
  `sha256:<artifact_hash>` ist (ruling T2-g der Aufnahme, P-PI).
- Ein `charset=`, das einen Codec für Bytes statt für Text nennt (`base64`),
  macht die ganze Mail unlesbar: der Rückfall greift, die Einheit heißt
  `unreadable mail: LookupError`; benannt (Nachprüfung der Aufgabe 2, P-PI).
- Der Teil `text/rfc822-headers` einer Unzustellbarkeitsmeldung wird
  Körpertext, weil er ein Textteil ohne Dateinamen ist; benannt (Nachprüfung
  der Aufgabe 2, P-PI).
- Eine Mail, die mit den Mails in ihr mehr als 500 Events ergibt, wird bei
  jedem Lauf abgewiesen (`BatchTooLarge`), und der Lauf kommt nicht über sie
  hinaus, bis sie aus dem Ordner verschwindet (P-PI, Aufgabe 4).
- Zwei Varianten einer Message-ID, deren Hashes die ersten 64 Bit teilen,
  halten den Lauf an, bei jedem Lauf; zufällig kommt das nicht vor, gemacht
  braucht es rund vier Milliarden Versuche. Für einen Ordner, den ein Mensch
  füllt, hingenommen; `connectors.md` nennt es als Erstes, was bei einer
  Quelle zu prüfen ist, in die jeder schreiben kann (P-PI, Aufgabe 4).
- Anhangnamen: ein `/` wird `_`, ein leerer Name, `.` oder `..` wird kein
  Name; der Name im Event weicht dann von dem der Rohmail ab, die ihn behält
  (ruling T4-b der Aufnahme, P-PI).
- Die Zähler `appended` und `known` haben ein kleines Rennfenster: ein Event,
  das ein anderer Schreiber zwischen dem Lesen der Spitze und dem Anfügen
  unter demselben Schlüssel schreibt, zählt als angefügt (Docstring von
  `Ingested`; P-PI, Aufgabe 4).
- Der Filter `> after` auf die Antwort der Suche ist gegen GreenMail nicht
  messbar: GreenMail gibt für `UID n:*` jenseits der höchsten UID nichts,
  Dovecot nach RFC 3501 die letzte. Ohne Filter holte jeder Lauf die letzte
  Mail erneut und zählte sie als bekannt (P-PI, Aufgabe 5).
- Die Meldungen der Varianten eines schon angefügten Stapels gehen verloren,
  wenn ein späterer Stapel desselben Laufs abbricht; die Varianten selbst
  stehen im Log (P-PI, Aufgabe 5).
- Der erste Lauf über einen großen Ordner kommt über seine Suche nicht
  hinaus: `UID SEARCH UID 1:*` kommt als eine Zeile zurück, und `imaplib`
  weist eine Zeile über 1.000.000 Bytes ab (`_MAXLINE`, Python 3.14.3); bei
  etwa 7 Bytes je UID sind das rund 140.000 Mails, und jeder erste Lauf endet
  mit `refused a command: got more than 1000000 bytes`. Der Pilotordner ist
  kuratiert; eine Suche in UID-Bereichen, etwa zu 50.000, höbe die Grenze auf
  (Endprüfung Code, Befund M-3, P-PI).
- Eine Antwort auf `FETCH`, die `OK` ist und in der der Parser kein Literal
  `BODY[] {n}` findet, gilt als gelöschte Mail: sie wird übergangen, und die
  Position der nächsten trägt das Wasserzeichen still an ihr vorbei. RFC 3501
  erlaubt `BODY[]` auch als Zeichenkette in Anführungszeichen; Dovecot,
  Gmail, Exchange und GreenMail senden ein Literal. Laut machen hieße: bei
  `OK` ohne Körper mit `UID SEARCH UID <n>` nachsehen und sonst `ImapError`
  werfen (Endprüfung Code, Befund M-4, P-PI).
- 18 Adressen unter `example.at` und 4 unter `example.de` in den Testmails
  sind keine reservierten Namen (RFC 2606 reserviert `example.com`, `.net`,
  `.org` und die Endung `.example`), und `example.de` ist vergeben. Es wird
  nichts gesendet; sie zu ändern änderte die Bytes der Testmails und jeden
  Hash, der an ihnen hängt (Endprüfung Code, Befund M-5, P-PI).

### Gate und Policy (Pilot, Einheit 3)

Die Punkte aus PG §11, soweit sie nicht zu einer anderen Einheit gehören (der
Weg per Prompt steht unter *Spätere Teilprojekte*, Projekte als Geltungsbereich
unter *Feststellungen und Entitäten*, die Batch API bei der KI-Schicht), und
was die Ausführung offen ließ (P-PG).

- Die Prompt-Vorlage von `mail_overview` legt die Sprache von `topic` nicht
  fest: im Lauf der Bedingung 10 antwortete Anthropic auf eine deutsche Mail
  englisch, Mistral deutsch, beide mit `language: de`. Für die Probe
  unerheblich; die erste Aufgabe der KI-Schicht (Einheit 6) sollte es
  festlegen.
- Die Testmails des Laufs der Bedingungen 10 und 11 liegen noch im Ordner
  `previously-pilot`; sie müssen heraus, bevor kup6s die erste echte Aufnahme
  startet, sonst stehen sie im dauerhaften Log.

- Die Prüfung vor dem Schreiben nach außen — darf dieser Inhalt in ein fremdes
  oder öffentliches System, ein GitLab, GitHub, das Jira eines Kunden,
  OpenProject? — ist eine andere Prüfung an einer anderen Stelle als die
  Verarbeitungsprüfung des Gates und kommt mit der ersten Aktion, die nach
  außen schreibt. Bis dahin schreibt nichts nach außen (PG §1.2, §11 Punkt 1).
- Die Reihenfolge der Modelle einer Aufgabe ist eine Behauptung des Plans, keine
  Messung; sie durch Vergleiche an echten Fällen zu begründen, etwa über
  OpenRouter, ist offen (PG §3.1, §11 Punkt 4).
- Unbekannte Beteiligte binden keine Regel. Gilt für einen Inhalt eine Regel
  der Quelle, geht er nach ihr hinaus, gleich wie viele Beteiligte keinem Kreis
  angehören; ob er dann strenger behandelt werden soll, ist offen. Steht auf
  `trust-boundaries.md` (PG §2.2, §11 Punkt 5).
- Der Modellserver in kup6s und welches lokale Modell dort reicht: der eigene
  Abschnitt des Handoffs `handoffs/2026-10-09-kup6s-gate.md`. Speicher und CPU
  sind ungemessen; bis er steht, lehnt das Gate im Cluster ab, wo die Vorgabe
  „nur lokal“ greift (PG §6, §11 Punkt 6).
- Die Güte des lokalen Modells auf CPU: `qwen3:4b` antwortet nur mit
  `reasoning_effort: none` (ohne brauchte ein Aufruf über 600 s), braucht 7 bis
  15 s je Mail und liefert Schwaches (das Thema „Email Response“; eine
  erfundene „Budgetfunktionalität“, wo die Mail sagt, das Budget bleibe wie
  besprochen). Der sichtbare Rückfall (`policy gaps`) macht das erkennbar, er
  bessert es nicht (Messung vom 2026-10-09; die Sekunden im Handoff
  `handoffs/2026-10-09-kup6s-gate.md`, *The model server*, die Antwort in
  `set-a-policy-and-try-a-call.md`, das Thema auf `processing-policy.md`).
- Ein Aufruf ohne Audit, wenn der Prozess zwischen Antwort und Schreiben
  abbricht; ein Event vor dem Aufruf würde die Lücke schließen und kostet ein
  zweites Event je Aufruf. Steht auf `trust-boundaries.md` (PG §3.2, §11
  Punkt 7).
- Ein NUL oder ein einsames Surrogat in `model`, `request_id` oder
  `stop_reason` der Antwort eines Anbieters lässt das Schreiben des
  `model_call` nach einem bezahlten Aufruf scheitern; für das Ergebnis selbst
  gilt das nicht, es wird `schema_invalid` (P-PG, Aufgabe 5).
- Eine Ablehnung im Format der OpenAI-Schnittstelle (`message.refusal`) endet
  als `schema_invalid`, nicht als `refused`; der Zweig `stop_reason == refusal`
  kennt nur Anthropic (P-PG, Aufgabe 5).
- Zero Retention bei Anthropic und Mistral: beantragen, dann als Zusage
  deklarieren (PG §2.4, §11 Punkt 8).
- Die Aufbewahrung bei Mistral nachsehen und deklarieren; bis dahin steht dort
  „unbekannt“, und eine Regel mit Grenze lässt Mistral nicht durch (PG §2.4,
  §11 Punkt 9). kup6s hat danach gefragt; der Handoff der Einstellungen
  antwortet, dass es die Zusage `retention_days` des Betreuers ist (RG).
- Die Preisdatei pflegt sich nicht selbst; ein veralteter Preis macht nur die
  Schätzung falsch. Sie bildet auch den Aufschlag für Prompts über 100.000
  Tokens bei Haiku 5.5 nicht ab (PG §3.4, §11 Punkt 11; Kopf von
  `prices.toml`).
- Die `model_call`-Events, die eine Quelle lasen, findet die Kaskade durch
  Lesen aller Handlungen; für den Piloten genügt das, ein Index wäre die erste
  Verbesserung (PG-Plan, Entscheidung 6; `erasure.md`).
- Die Kaskade ist nicht transitiv: ein Aufruf, der das Ergebnis eines anderen
  las, wird nicht mitgetilgt. Das Gate nimmt deshalb nur Events der Art
  `observation` als Eingabe (ruling R-11 der Einheit 3, P-PG); eine Aufgabe,
  die auf Ergebnissen aufbaut, braucht die transitive Kaskade zuerst.
- Die Sperrreihenfolge der Kaskade (Ziele und Aufrufe in einer aufsteigenden
  Runde, ruling R-12 der Einheit 3, P-PG) ist für ein Paar gemessen, nicht
  unter Last mit mehreren gleichzeitigen Tilgungen.
- Der Blob-Pfad der Kaskade findet Aufrufe über die Adresse in
  `inputs[].blobs`, ohne zu prüfen, ob das Event der Tilgung dazugehört;
  Übertilgen ist die sichere Richtung (P-PG, Aufgabe 6).
- Auf dem Pfad „unfinished“ von `redact` fehlen die Zeilen `cascaded:`; der
  wiederholte Lauf findet die Kaskade bedeckt und schreibt sie nicht noch
  einmal (P-PG, Aufgabe 6).
- Ohne Quelle schlägt die Zeile des Rückfalls `policy rule event:<id>` vor, das
  `policy rule` abweist; Fehlbedienung, benannt (P-PG, Aufgabe 5).
- `policy rule --revoke` verlangt `--regions`, dessen Wert nichts bewirkt, weil
  die Aussage wohlgeformt sein muss; benannt in
  `set-a-policy-and-try-a-call.md` (Aufgabe 7).
- `policy provider --revoke` verlangt ebenso `--storage` und
  `--retention-days`, deren Werte nichts bewirken; benannt in
  `set-a-policy-and-try-a-call.md` (Endprüfung Doku, P-PG).
- Bis zu 200 Zeichen der Fehlermeldung eines Anbieters gehen bei `gate try`
  auf stderr (`gate/adapters/__init__.py`), und die Meldung kann den Prompt
  zurückgeben. Von Hand ist das harmlos; sobald ein Job das Gate aufruft
  (Einheit 6), wird es Kundeninhalt im Log des Containers (Endprüfung Doku,
  P-PG).
- Ein CronJob, der `policy gaps` meldet, damit ein Rückfall auch ohne
  jemanden am Terminal gesehen wird (PG §2.6 Punkt 3; der Handoff nennt ihn
  „a later idea“).
- Offene Frage zu ruling R-5 der Einheit 3 (P-PG): ein widerrufener Kreis hat
  keine Mitglieder, sein Inhalt geht dann nach den übrigen Regeln, etwa der
  der Quelle, auch `any`, und nicht nach `local_only`. Ob ein Widerruf den
  Inhalt stattdessen lokal halten soll, ist offen; heute hält ihn lokal, wer
  die Regel des Kreises widerruft und den Kreis stehen lässt
  (`processing-policy.md`).
- `gate try` auf ein getilgtes Event oder eines, das keine Wahrnehmung ist,
  nennt unter `policy.providers` jede Zusage, obwohl kein Kandidat gewogen
  wurde; ein Prüfer liest „diese Zusagen wurden herangezogen“ (Endprüfung
  Code M-7, P-PG).
- Eine fehlerhafte `PREVIOUSLY_LOCAL_MODEL_URL` (etwa `http://[::1`) lässt
  jeden `gate try` mit einem Traceback scheitern, schon beim Bauen der
  Adapter und vor der Entscheidung, auch wenn der Aufruf zu Anthropic ginge;
  Fehlkonfiguration, benannt (Endprüfung Code M-8, P-PG).
- Das Zählkommando für Ruling-Zitate in `CLAUDE.md` sucht nur
  `ruling (P|T[0-9]+)-…` und findet die Labels `R-…` dieser Einheit nicht
  (Endprüfung Code M-6, P-PG).
- Der Schlüssel wird aus einer Meldung eines Anbieters mit `str.replace`
  entfernt und also nur in der Schreibung, in der er gesendet wurde; eine
  maskierte Form würde nicht erfasst. Echte Schlüssel sind URL-sicher (P-PG,
  Aufgabe 4).
- Ein Anbieter mit leerer `inference`-Liste besteht nie, und der Grund liest
  sich seltsam; das tritt nur bei einer Fehldeklaration auf (P-PG, Aufgabe 3).
- `gate explain` liest die Policy in zwei Transaktionen, einmal für die
  Entscheidung und einmal für die Zeilen des Rückfalls; zwischen beiden kann
  eine Aussage dazukommen (P-PG, Aufgabe 5).
- Der Test, dass die Nutzlast keinen Inhalt trägt, läuft über `ok`;
  `denied`, `refused` und `schema_invalid` werden nicht durchsucht, `error`
  hat einen eigenen Test (ruling R-9, P-PG, Aufgabe 5).
- Kleinkram der Ausführung, benannt und nicht verfolgt (P-PG): die
  Untergrenzen `anthropic>=1.13.0` und `openai>=3.27.0` sind ungemessen; `__all__`
  steht nur in `gate/adapters/anthropic.py`; die Kommandozeile benutzt Zeichenketten
  statt der Konstanten aus `core.action` und `RULE`; `cli.md` nennt `--regions`
  ohne Raum als abgewiesen, und argparse weist es ab; einige Tests importieren in
  der Funktion; `tests/test_chronicle.py` liest Spalten über den Index; für den
  Neuversuch von `append_action` gibt es keinen eigenen Test, er ist über
  `redact` abgedeckt.

### MCP-Lesezugang (Pilot, Einheit 4)

Die Punkte aus MK §10 und ML §13, soweit sie nicht zu einer anderen Einheit
gehören (die Projekte stehen unter *Feststellungen und Entitäten*), und was die
Ausführung offen ließ (P-ML). Die benannten Grenzen, die keiner Arbeit bedürfen,
stehen auf `mcp-interface.md` unter *What the pilot leaves open*.

- Die Grenze von 60.000 Zeichen je Seite (`PAGE_CHARS` in
  `mcp_server/render.py`) ist geschätzt, nicht an echten Mails gemessen;
  der Lauf der Bedingung 9 meldet dazu nichts, sie bleibt ungemessen (ML §5.1,
  §13 Punkt 2; RG).
- `previously-mcp` unter Last ist ungemessen: gesetzt sind 50m CPU und 128 MiB
  angefordert, 1 CPU und 512 MiB als Grenze, gebraucht im Leerlauf 3m CPU und
  98 MiB (RG). Eine Messung unter Last, etwa mit mehreren Clients, die die
  Chronik eines langen Logs lesen, steht aus.
- Die Chronik nach Kreis liest das Log in Stapeln von 200 Zeilen, ohne Grenze
  je Aufruf; ein Kreis mit wenigen Treffern liest für eine Seite das ganze Log.
  Eine eigene Projektion, sobald das zu langsam wird, an echter Menge zu messen
  (ML §5.1, §13 Punkt 1; ruling R-12, P-ML). Der Maßstab: jeder Aufruf bleibt
  deutlich unter 60 Sekunden, dem Zeitlimit, mit dem Vibe auf einen Aufruf
  wartet (MK §9); ein dünner Kreis über einem langen Log erreicht es zuerst.
- Der Rest einer einzelnen Einheit, die allein über die Seitengrenze geht, wird
  im Piloten nicht ausgeliefert; die Kürzung sagt es. Ein Weg dorthin wäre ein
  Argument wie `from_char` (ruling R-5, P-ML).
- Die Middleware, die vom SDK abgewiesene Aufrufe ins Zugriffsprotokoll
  schreibt, nutzt eine Schnittstelle, die `mcp` 2.3.0 vorläufig nennt
  („Provisional - the signature may change in a 2.x minor release“); bei jedem
  Upgrade von `mcp` prüfen (P-ML, Aufgabe 5).
- Vibe auf `mcp` 2.x: Vibe 2.26.1 spricht `2025-11-25`. Sobald Vibe die neue
  Generation spricht, fallen `stateless_http=True` als Schalter für die alte
  und der Test mit `mode="legacy"` weg (MK §1.1, §10 Punkt 3). Ob
  `/mcp refresh` in Vibes Standard-Harness neue Werkzeuge holt, ist ungemessen
  (M); bis dahin nach einem Release `--legacy-harness`, wie die Anleitung sagt.
- Die Menge der `mcp_access`-Events — eine Handlung je Aufruf, geschätzt einige
  tausend im Monat — beobachten und eine Schwelle nennen, ab der
  zusammengefasst werden müsste (MK §5, §10 Punkt 2). Sie bremst jeden Aufruf:
  jeder liest die Policy, über HTTP zweimal (Token und Aufruf). Bis 2026-10-11
  las `read_policy` dabei jede Handlung und übersprang die `mcp_access` erst in
  Python; gemessen am 2026-10-11 mit 6.000 Einträgen 0,341 s je Lesen (die
  Endprüfung maß am selben Tag 0,425 s). Seitdem holt `LogStore.actions` per
  SQL-Filter nur die Policy-Handlungen, ohne Migration: 0,010 s bei 6.000
  Einträgen, am selben Tag gemessen (ruling R-17, P-ML). Die Datenbank besucht
  weiter jede Handlung; die Zeit wächst langsamer, aber sie wächst.
- Eine Projektion der Policy, sobald auch das gefilterte Lesen spürbar wird;
  `previously access`, `policy gaps` und die Lesungen der Tilgung lesen
  weiterhin jede Handlung (ruling R-17, P-ML).
- Mehrere Replikate erst, wenn zwei Worker hinter einem Lastverteiler gemessen
  sind; bis dahin eines (MK §2, §10 Punkt 4; der Handoff
  `handoffs/2026-10-11-kup6s-mcp.md`).
- OAuth mit einem Autorisierungsserver, wenn mehr als ein Mensch zugreift; der
  Wechsel tauscht die eigene ASGI-Hülle in `mcp_server/auth.py` gegen den
  `TokenVerifier` des SDK (MK §7, §10 Punkt 5).
- Elicitation als Aufwertung der Bestätigung eines schreibenden Aufrufs, wo ein
  Client sie meldet (MK §4.3, §10 Punkt 6). Die ersten schreibenden Werkzeuge
  kamen mit Einheit 5 ohne sie (unten unter *Feststellungen*).
- Tasks für lange Läufe, wenn das SDK und ein Client sie haben (MK §10 Punkt 7;
  zur Prüfung von Claude Code siehe *Spätere Teilprojekte*).
- Der Effekt der Einzäunung von Fremdinhalt auf aktuelle Modelle ist
  ungemessen (MK §6, §10 Punkt 8).
- Ein Eintrag ohne Zustellung: das `mcp_access` wird vor der Antwort
  geschrieben, also fehlt nie der Eintrag einer Antwort, die ankam. Geht die
  Antwort danach verloren — stdin geschlossen, HTTP-Verbindung abgebrochen,
  Prozess beendet —, steht sie im Protokoll als geliefert. Die Lesart von ML §7,
  ein Abbruch verliere den Eintrag wie beim Gate, trifft hier nicht zu: das Gate
  ruft erst und schreibt dann, der Server liest, schreibt und antwortet (ruling
  R-21, P-ML). Steht auf `trust-boundaries.md` und `mcp-interface.md`.
- Eine Rotation zwischen Tokenprüfung und Aufruf: die Hülle löst den Token zu
  einem Namen auf, der Aufruf sucht den Client danach im eigenen Lesen der
  Policy. Ein `client add` desselben Namens dazwischen bedient die eine Anfrage
  mit dem alten Token unter dem neuen Eintrag, der einen anderen Anbieter
  nennen kann. Fenster: eine Anfrage. Behebung, wenn nötig: den Hash des Tokens
  in `scope["state"]` mitgeben und im Schnappschuss des Aufrufs gegen
  `token_sha256` prüfen (Endprüfung, P-ML). Steht auf `mcp-interface.md`.
- Kleinkram der Ausführung, benannt und nicht verfolgt (P-ML, Aufgabe 5):
  scheitert `record_access` selbst nach einem erfolgreichen Lesen, bekommt der
  Client die Meldung des SDK `Error executing tool …`, die nicht mit `Error: `
  beginnt — geschlossen gescheitert, nichts wurde geliefert; eine ID außerhalb
  des Bereichs, die nicht mehr auf die Seite passt, fehlt in `ids=[…]` des
  Fußes; `withholding` sagt bei einem lokalen Anbieter, der unter `local_only`
  scheitert, „the built-in rule local_only do not allow“.
- **Andere Quellen als Mail, ein Folgeschritt vor der zweiten Quelle** — vom
  Betreuer am 2026-10-11 gefragt, ob der Server andere Eingänge genug bedenkt,
  und als Folgezweig nach dem Merge entschieden, „wir sollten es nur nicht
  vergessen". Filter, Prüfung je Inhalt, Zugriffsprotokoll und Cursor sind
  quellenneutral; die Darstellung ist es nicht, und kein Test liefert etwas
  anderes als eine Mail (alle Fixtures in `tests/test_mcp_server.py` laufen
  über `map_mail`). Drei Dinge, eine kleine Aufgabe, fällig bevor die Sprache
  (Zweig `worktree-voice-rahmen`) oder eine Nicht-Mail-Datei aus Nextcloud
  ankommt:
  1. `UnitRow` trägt `speaker`, `start_ms` und `end_ms` — für Transkripte
     angelegt —, aber `_texts` in `mcp_server/read.py` gibt nur
     `(seq, content)` weiter; ein Transkript käme als namenlose Absätze ohne
     Zeiten an. In die Einheitenmarke im Zaun, etwa
     `#unit-3 · 00:12:04–00:12:31 · remote-2`, bereinigt wie jeder Fremdtext.
  2. Der Kopf kennt nur die Rollen `from`/`sender` und `to`/`cc`/`bcc`
     (`_SENDER_ROLES`, `_RECIPIENT_ROLES` in `read.py`); jede andere Rolle
     fällt still weg. Unbekannte Rollen allgemein zeigen (`<role>: <name>`),
     mit derselben Kappung wie die Empfänger.
  3. Zwei Tests: eine schlichte Wahrnehmung ohne Beteiligte
     (`previously append --source note`) und eine mit Einheiten in Form eines
     Transkripts — je gerendert, je durch die Prüfung (ohne Kreis greift nur
     eine Regel `source:<name>` oder `local_only`).

### Feststellungen (Pilot, Einheit 5)

Was F §15 an andere Einheiten gibt, steht dort (die Zuordnungen und der
Identitätsgraph oben unter *Feststellungen und Entitäten*, die automatische
Feststellung unten unter *Spätere Teilprojekte*). Hier steht, was der Bau
offen ließ (P-F). Die benannten Grenzen, die keiner Arbeit bedürfen, stehen
auf `assertions.md` unter *What the pilot leaves open*.

- Eine Projektion für Feststellungen, nur wenn die Messung sie verlangt:
  gelesen wird durch Falten aller Feststellungen aus dem Log, bei jeder Liste
  und jedem Schreiben (Planentscheidung 1). Gemessen am 2026-10-12 bei 5 000
  Feststellungen (i7-11370H, PostgreSQL 18, Median aus drei): das Falten
  150 ms; langsam waren nur die Listen, die Policy oder Kreise fragen, weil
  sie jede Quelle einzeln lasen — `obligations --circle` 2 824 ms,
  `list_obligations` Seite 1 941 ms, mit dünnem Kreis 1 964 ms. Seit der
  Fixwelle liest ein Aufruf die Quellen gesammelt in zwei Abfragen (P-F,
  Ruling F-16), und dieselben Listen brauchen 193, 225 und 224 ms; die
  Zahlen stehen auf `assertions.md`. Die Projektion verlangt die Messung
  damit nicht.
- Die Forderung, dass der Client vor `write_approve` und `write_reject` fragt,
  hängt allein an seiner Einstellung. Die Doku von Claude Code nennt
  MCP-Werkzeuge mit `_meta["anthropic/requiresUserInteraction"]`, die fragen
  wie mit einer Ask-Regel; Vibe kennt es nicht (gefunden beim Schreiben der
  Anleitung, 2026-10-12). Seit dem Zweig `mcp-erklaeren` tragen
  `write_approve` und `write_reject` die Kennzeichnung (und nur sie).
  Gemessen am 2026-10-13 gegen `0.1.0a6` vom Betreuer: Claude Code 2.1.296,
  neue Sitzung, keine Ask-Regel für `write_reject` — vor dem Aufruf kam der
  Dialog, die Kennzeichnung allein trägt. Die Ask-Regel bleibt trotzdem die
  Forderung, weil Vibe und ältere Versionen sie nicht kennen. Claude Code startet ab v2.1.283 im Auto-Modus, in
  dem ohne Ask-Regel ein Klassifikator entscheidet; die Anleitung verlinkt
  seit der Fixwelle die Quellen. Gemessen am 2026-10-13: Claude Codes Ask-Regel
  `mcp__previously__write_approve` greift im Auto-Modus. Ungemessen bleibt die
  Ask-Einstellung von Vibe: es führt die Werkzeuge als
  `mcp_previously.<Werkzeug>`, nicht als `previously_<Werkzeug>` wie seine
  Doku und unsere Anleitung, und ob `[tools.previously_write_approve]`
  greift, ist offen. Vibe fragt ohnehin bei jedem MCP-Werkzeug (Standard).
- Der Abnahmelauf vom 2026-10-13 mit Claude Code las die Daten zweimal falsch:
  die Freigabe 43 stehe als „direct, model:claude-code“, also habe sie „eine
  andere Claude-Code-Sitzung“ freigegeben, und Previously halte „den Client
  fest, nicht den Menschen“. Beides ist falsch: eine Freigabe behält den
  Verfasser des Vorschlags, und `direct` heißt, der Betreiber steht dafür
  (`assertions.md`); seit F-6 kann eine direkte Fassung eines `model:`-Autors
  nur eine Freigabe sein. Dazu rief der Client `write_approve` auf, ohne den
  Betreuer zu fragen, weil die Ask-Regel fehlte. Der Zweig `mcp-erklaeren`
  antwortet darauf, ohne Skill auf der Seite des Clients: der Server erklärt
  sich selbst (`INSTRUCTIONS`), Freigaben und Ablehnungen tragen in Liste,
  Geschichte und Seite der Kommandozeile einen Zusatz („made its own by the
  operator (approval of N), formulated by AUTHOR“; „rejected (by the
  operator)“), und die beiden Werkzeuge tragen die Kennzeichnung. Dass
  Claude Code damit fragt, ist gemessen (oben); ob es damit richtig liest,
  zeigt erst der nächste Lauf; offen
  bleibt, über welchen Weg der Betreiber antwortete — die Nutzlast hält das
  nicht fest, nur `mcp_access` für Aufrufe über MCP.
  Am selben Tag entschied der Betreuer nach dem Lauf, dass Freigabe und
  Ablehnung über MCP ein Aufruf sind (eine Freigabe kostete drei Fragen): kein
  `confirm`, kein Handle, ein wiederholter gleicher Aufruf ist ein Erfolg ohne
  Schreiben; der Spec trägt die Abweichung im Kopf (§6.1), und gemessen ist
  auch das erst im nächsten Lauf.
- Eine Erfüllung, die der Betreiber nur sagt („43 ist heute erfüllt“), hat
  keine Wahrnehmung als Quelle: der Vorschlag konnte sich nur auf die
  ursprüngliche Mail stützen, und sein Grund sagte es (Abnahmelauf
  2026-10-13). Der Einwurfweg `write_submit` (K §4.3, „später“) würde eine
  solche Aussage zu einer Wahrnehmung machen; bis dahin bleibt der Grund die
  einzige Spur.
- Eine Geschichte, die länger ist als eine Seite, wird über MCP nach einer
  ganzen Zeile gekürzt, und ihr Rest kommt über keinen Aufruf; die
  Kommandozeile zeigt sie ganz. Ein Weg wäre ein Cursor für die Geschichte
  (P-F, Aufgabe 4).
- Zwei Stücke von F, die der Bau nicht hat: der Hinweis auf `address:` in der
  Vorschau über MCP (F §2.1; nur die Kommandozeile gibt ihn) und „zuletzt
  geändert am" je Eintrag einer Liste (F §3.5; die Listen zählen Fassungen
  und Vorschläge, die Geschichte nennt die Zeit jeder Fassung).
- Geparkt aus den Prüfungen, benannt und nicht verfolgt (P-F): die
  Hypothesis-Eigenschaft in `tests/test_assertion.py` tilgt die erste Fassung
  nicht (F-2 decken drei Beispieltests); ein toter Zweig und eine
  überschriebene Zuweisung dort um die Eigenschaft; der Statussatz
  `no obligation stands under event ID` steht außerhalb des Zitattests; der
  Abweisungszweig für das aufgeschobene Schreiben in `mcp_server/server.py`
  ist ungetestet, weil er einen Stellvertreter für die Datenbank bräuchte;
  `_cmd_decisions` setzt die Listenfilter auf `args`; die Geschichte über MCP
  schreibt einen fehlenden Grund in `set`-Zeilen als `none` und in
  `change`-Zeilen als `(none)` (gefunden in der Fixwelle, 2026-10-12).

### Nextcloud-Ordner (Pilot, Einheit 7)

- Mails als Dateien: eine `.eml`-Datei ist dieselbe Mail nach RFC 822, die
  IMAP liefert, und läuft durch dieselbe Abbildung (`core/mail.py`) zu einem
  Event mit `source = email`; liegt dieselbe Mail auch im IMAP-Ordner, ist sie
  über Message-ID und Inhaltsidentität dasselbe Event, gleich welcher Weg
  zuerst kam. Offen: Outlooks `.msg` (eigenes Binärformat) und `.mbox` (viele
  Mails in einer Datei) müssen erst umgewandelt oder zerlegt werden — was davon
  gebraucht wird, zeigt, was im Ordner tatsächlich landet. Vom Betreuer am
  2026-10-06 gefragt, „dann wird es nicht vergessen" (PI §11 Punkt 9).

### Suche

- Textsuchvariante: Messversuch mit gemischtsprachigen Einheiten (A §11 und
  Nachtrag; E §12.3, §16).
- Embedding-Modell und Dimension, mit einem Testsatz aus echten gemischten
  Einheiten; die Architektur weist es Teilprojekt 1 zu, keine Stufe trägt es
  (A §11; PP, A2).
- `pg_dict` mit Hunspell; Versionsstände der Erweiterungen; Tokenizer-Weg
  (A §13, E §16). Die erste Migration richtet keine Erweiterung ein.
- `p_unit_search` teilt den Primärschlüssel mit `p_chronicle` (1b §1).

### Warteschlange (mit dem ersten asynchronen Produzenten)

- Tabelle `job`, Entprellung, Wiederholung, `SKIP LOCKED` (A §7.1; 1b §10
  Punkt 4).

### Auslieferung (Paket, Image, Release)

- Signaturen und Herkunftsnachweise (Sigstore/cosign, SLSA-Provenance, SBOM)
  für Paket und Image. PyPI erzeugt mit Trusted Publishing schon
  Attestierungen für das Paket; für das Image ist nichts vorgesehen (AL §12
  Punkt 1).
- Das Image installiert aus PyPI; scheitert sein Smoke-Test, ist die Version
  auf PyPI schon sichtbar und kommt nie wieder. Ein Image aus dem gebauten
  Wheel des Laufs wäre die Alternative, mit dem Preis, dass es nicht beweist,
  dass das Paket auf PyPI installierbar ist (AL §5, §12 Punkt 2;
  `delivery.md`).
- Nichts prüft, dass die gebaute Version dem Tag gleicht. Ein Tag mit
  führender Null (`v1.02.3`) besteht die Tag-Prüfung und endet mit einer
  Version auf PyPI ohne Image; zwei Tags auf einem Commit (rc und final)
  scheitern sicher, gemessen. Eine Zeile in `build`, die das Wheel unter dem
  Namen des Tags sucht, finge jede solche Klasse vor dem Hochladen ab;
  Entscheidung des Betreuers (P-AL, Prüfung der Aufgabe 4; benannt in
  `cut-a-release.md` und im Kommentar von `release.yml`).
- Ein stabiles Release einer älteren Linie, nach einem neueren
  veröffentlicht, setzt `latest` auf sich zurück: `enable` liest nur die
  Markierung als Vorabversion (P-AL, Prüfung der Aufgabe 4; `delivery.md`,
  `cut-a-release.md`). Folgenlos, solange es keine Wartungslinie gibt.
- Eine Vorabversion bekommt nur den Image-Tag `<version>`, kein
  `<major>.<minor>`, anders als AL §3.2 Punkt 6: `docker/metadata-action`
  verlängert eine Vorabversion nur zur genauen Fassung (ruling T4-a; P-AL).
  Hingenommen, kup6s pinnt die genaue Version; bis `1.0.0` hat jedes Image
  genau einen Tag.
- `scripts/smoke-image.sh`: `trap` steht nach `mktemp`; dass das Skript `uv`
  und `openssl` auf dem Wirt braucht, steht in `run-the-image.md`, nicht im
  Kopf des Skripts; ein Abbruch kann einen `--rm`-Container und das Netz
  zurücklassen; `useradd --system` mit uid 1000 warnt harmlos beim Bau (P-AL,
  Prüfung der Aufgabe 3).
- `scripts/smoke-image.sh` unter rootless Docker oder als uid 0: rootless
  Docker bildet `--user` auf eine subuid ab, und ein Wirt mit uid 0 lässt die
  Container mit `--user "$(id -u):$(id -g)"` als root laufen; dann beweist der
  Smoke-Test nicht mehr, dass das Image unter fremder uid läuft. Die Prüfung
  auf uid 1000 läuft ohne `--user` und hält weiter (P-AL, Prüfung der
  Aufgabe 3; Fehlbedienung, benannt nach ruling E-2 der Auslieferung).
- Das Wheel für PyPI baut `uv build` mit dem hatchling, der an diesem Tag
  aktuell ist: `[build-system] requires` ist nicht gelockt, `uv.lock` hält
  hatchling 1.32.4 nur als Dev-Abhängigkeit für `tests/test_wheel.py`. Keine
  zweite Fassungsangabe, sondern eine fehlende; abhelfen könnte `uv build
  --build-constraint` (Endprüfung Code, Befund Minor 9; benannt nach ruling
  E-2 der Auslieferung).
- Image-Etikett für die Paketseite auf `ghcr.io`: für ein Image über mehrere
  Plattformen liest GitHub die Beschreibung womöglich aus dem Index, nicht aus
  den Images; `docker buildx imagetools create --annotation
  "index:org.opencontainers.image.description=…"` in `manifest` wäre der Weg.
  Ungemessen, erst beim ersten Release sichtbar (Endprüfung Code, Befund
  Important 3).

### Betrieb (ohne Teilprojekt)

- Benannter Restore-Point im Takt des Ankerns, für `--exact` nach einer
  Wiederherstellung (AA §10 Punkt 4); mit stündlichen Dumps ohne
  Point-in-Time-Recovery, wie in kup6s (RK), fällt ein Dump nur zufällig auf
  einen Anker. Ob Previously die Ankerdatei selbst irgendwohin veröffentlichen
  soll, ist offen (AL §12 Punkt 4).
- Anforderung: die Bucket-Zugangsdaten, die Previously hält, reichen an den
  Blob-Bucket und an nichts sonst, kein anderer Schlüssel kann dessen
  Objekte löschen oder überschreiben, und kein Schlüssel eines Prozesses,
  der fremden Inhalt verarbeitet (Aufnahme, Gate, MCP-Server, Werkzeug-Pod),
  kann eine Sicherung löschen oder überschreiben. Gründe in `blobs.md`
  („Who may reach the bucket") und `backup-encryption.md` („Out of reach of
  what handles foreign content"), gesammelt in `reference/environment.md`.
  kup6s erfüllt das in der Testphase noch nicht: ein S3-Schlüssel bei Hetzner
  gilt für jeden Bucket eines Projekts, und Blob- und Dump-Bucket nutzen die
  Zugangsdaten der Flotte (RK). Vor dem regulären Gebrauch erfüllt kup6s es —
  ein zweites Hetzner-Projekt nur für den Blob-Bucket und Object Lock auf dem
  Dump-Bucket wären ein Weg, die Wahl liegt bei kup6s — oder entscheidet sich
  bewusst dagegen und trägt das benannte Risiko (Grundsatz in `CLAUDE.md`,
  „Previously demands, the environment provides"; RK; 1c §7).
- Anforderung: die Restore-Probe läuft in einem benannten Takt; wo sie den
  privaten Schlüssel der Sicherungen hält, wählt die Umgebung, solange er
  außerhalb des Systems liegt, das er schützt (`backup-encryption.md`). kup6s
  erfüllt das in der Testphase noch nicht: die Probe läuft von Hand, der
  Schlüssel kommt nur für sie in den Cluster (RK). Vor dem regulären Gebrauch
  erfüllt kup6s es oder entscheidet sich bewusst dagegen.
- Die Rolle in `PREVIOUSLY_DSN` darf Zeilen löschen und ändern, und jeder
  Prozess, der fremde Inhalte verarbeitet (Aufnahme, Gate, MCP-Server), hält
  sie. Kette und Anker erkennen ein Löschen, verhindern es nicht. Gebraucht
  wird je Prozess weniger: die Aufnahme hängt an und schreibt ihre
  Wasserlinie, der MCP-Server liest und hängt `mcp_access` an, nur `redact`
  ändert Zeilen. Getrennte Rollen wären eine Forderung an die Umgebung samt
  einer Aufteilung in Previously, die es heute nicht gibt (gefunden bei der
  Rückmeldung von kup6s, 2026-10-11). kup6s bestätigt es am 2026-10-12 (RA):
  alle Pods nutzen eine Rolle, die Eigentümerin der Datenbank, die
  Anforderungen an die Umgebung verlangen nicht mehr, und getrennte Rollen,
  der des Servers beschränkt auf das, was seine Werkzeuge brauchen, würden
  verengen, was ein gekaperter MCP-Pod mit den Tabellen tun könnte; ob das eine
  Anforderung wert ist, liege bei uns.
- `previously migrate` geht nur vorwärts; ein Zurück im Betrieb ist eine
  Wiederherstellung, kein Kommando (AL §12 Punkt 3; `delivery.md`).
- Der Container-Weg der Anker-Routine ist für `kubectl exec` ungemessen
  (P-AA).
- Der Bucket der Blobs bei Hetzner, ohne Versionierung und ohne Object Lock,
  mit eigenen Zugangsdaten; die Identität über External Secrets als
  Verzeichnis eingehängt (1c §7). Was bei Hetzner anders ist als beim
  Testserver, hat seit der Ausführung Namen: ob der Speicher das Metadatum
  `key-id` so zurückgibt; was ein Leser sieht, während ein Objekt ersetzt
  wird (bei RustFS bricht sein Lesen ab); ob ein bedingtes Schreiben
  angenommen wird; ob Löschen ohne Version und ohne Löschmarke löscht (1c §12
  Punkt 11; P-1c). Nichts prüft, dass der Bucket ohne Versionierung und ohne
  Objektsperre ist; ein Bucket mit einem von beiden behält getilgte Blobs, und
  `verify --blobs` sieht es nicht, könnte es aber melden (Endprüfung der Doku,
  Befund 5).
- Ein Tresor hinter der Schlüssel-Naht; heute ein Verzeichnis mit einer Datei
  je Empfänger (1c §12 Punkt 7).
- Keine Seite sagt einem Betreiber, der von Stufe 1b kommt, was mit seinen
  Events im Format 1 ist: kein Salz, Einheiten nur zusammen tilgbar
  (Endprüfung der Doku, als Lücke des Projekts zurückgestellt). Dass er die
  Datenbank migrieren muss, sagen seit der Auslieferung `run-the-image.md`
  und die Release-Notes für Betreiber, die `cut-a-release.md` verlangt — mit
  `previously migrate` statt `alembic upgrade head`.
- Die Cron-Zeile für einen Host mit Docker in `ingest-a-mail-folder.md` ist
  als Zeile nicht gelaufen; ihre Befehle sind es (PI §6).
- Ein Verzeichnis der Tilgungen außerhalb der Datenbank: nach einer
  Wiederherstellung auf einen älteren Stand weiß das Log nicht mehr, was
  seither getilgt wurde, und die Tilgungen sind zu wiederholen; die Anker-Datei
  wäre ein Muster (1c §4.5, §12 Punkt 3). Die Anleitung
  `restore-from-a-backup.md` verlangt es, gebaut ist nichts.
- Der Notfallweg mit dem Werkzeug `age`: am 2026-10-05 in einem Container mit
  `age` 1.2.1 gegangen, ein Objekt mit der AWS-Kommandozeile geholt und mit
  der Identität allein geöffnet (Aufgabe 8, P-1c); von Hand, mit installiertem
  Werkzeug, steht er für die Abnahme aus (1c §11 Bedingung 14).
- „Kettenprüfung schlägt an → alles Schreiben anhalten" (A §7.4) ist nicht
  gebaut; es gibt nur den Alarm. Kein Grund aufgeschrieben (PP, A2).
- Zwei gleichzeitig laufende Anker-Routinen hängen beide an; folgenlos, aber
  ohne Sperre (P-AA).
- GitHub schaltet geplante Workflows in einem öffentlichen Repository nach 60
  Tagen ohne Aktivität ab; die wöchentliche Prüfung mit `pip-audit` kann dann
  still aufhören (Prüfung der Wartungsrunde, 2026-10-04).
- Die Renovate-App ist auf dem Repository noch nicht installiert; ohne sie tut
  `renovate.json5` nichts. Validiert ist die Konfiguration mit Renovate
  42.99.0, nicht mit der aktuellen Hauptversion, und ob Renovate den
  Versionskommentar neben einem gepinnten Action-Commit mitzieht, steht nicht
  in seiner Dokumentation — am ersten solchen Pull-Request nachsehen (Prüfung
  der Wartungsrunde, 2026-10-04).

### Kette und Anker

- Die Signatur des Schreibers: nur sie schließt gefälschtes Anhängen außerhalb
  eines Moments der Ruhe (AA §10 Punkt 1).
- Ein beglaubigtes „wann" über den Ablageort hinaus (AA §10 Punkt 3).
- Die Kettenprüfung geht bei jedem Lauf das ganze Log ab und hält ihren
  Schnappschuss so lange offen: gemessen 13 s je 100 000 Events, hochgerechnet
  rund elf Minuten bei fünf Millionen — bei jedem Lauf der Anker-Routine. Eine
  Prüfung, die beim jüngsten Anker beginnt, gibt es nicht; und ein so lange
  offener Schnappschuss hält `VACUUM` zurück, was niemand gemessen hat (PP,
  Bericht C).
- `verify --blobs` liest alles: eine Prüfung nur der Blobs seit dem letzten
  Lauf gibt es nicht (1c §12 Punkt 9); und es hält die Referenzen aller Blobs
  im Speicher des Prozesses, im Docstring gesagt, nicht gemessen (P-1c).
- In v=1 ist an einem ganz getilgten Event nichts mehr über seine Einheiten
  bezeugt: Zahl und `seq` der Grabstein-Zeilen prüft nichts. In v=2 fällt
  beides auf. Steht auf `erasure.md`, festgenagelt von
  `test_the_tombstone_rows_of_a_fully_erased_version_1_event_are_attested_by_nothing`
  in `tests/test_verify.py`; wer die Grenze schließt, dreht den Test bewusst
  um (P-1c).
- `previously anchor` allein prüft keine alten Anker (P-AA).
- Ein Befund nennt die `id`, nicht die Zeile der Ankerdatei (P-AA).
- `anchored event is missing (the log ends at 5)` für ein Event aus der Mitte
  liest sich wie ein Widerspruch (P-AA).
- Der Ablageort der Anker ist kein Dritter: in kup6s liegt `anchors.txt` in
  Git auf `git.bluedynamics.eu`, außerhalb des Clusters, Force-Push gesperrt,
  Schreiben nur mit dem Deploy-Key des Anker-Jobs — betrieben aber von
  denselben Leuten (RK). Gegenüber Dritten ist der Anker so kein Beleg
  (AA §10 Punkt 4). Für den Piloten hingenommen, später muss es eine Lösung
  geben; Object Lock klingt gut (Betreuer, 2026-10-11: „beim Piloten egal,
  später muss es eine Lösung geben"). Object Lock gibt es bei Hetzner,
  einschaltbar nur beim Anlegen des Buckets (RK).
- `verify --anchors` endet auf einem leeren Log mit 2: `anchor` schreibt dort
  keinen Anker, und eine Ankerdatei ohne Ankerzeile ist ein Eingabefehler.
  Der Anker-CronJob einer frischen Installation, der zuerst die alten Anker
  prüft, scheitert so bis zum ersten Event; die Handoffs verlangten von jedem
  CronJob 0 (RK). Für den Piloten hingenommen (Betreuer, 2026-10-11).
- Externer Compliance-Anlass: die Annahme „nicht zertifizierungsgetrieben" ist
  unbestätigt, und der Anker hat Teile eines Drittbelegs vorweggenommen
  (E §16; PP, A2).

### Kommandozeile

- Eine unerwartete Ausnahme endet mit Rückgabecode 1, dem Code eines Befunds
  (P-AA).
- `show` druckt Einheiten roh; eine Einheit mit Umbruch bricht die
  Zeilenstruktur (1b §10 Punkt 3).
- `cli.py` hat rund 3 000 Zeilen (3 034, gezählt am 2026-10-12 mit
  `wc -l`); die sieben Kommandos der Feststellungen kamen mit Einheit 5 dazu.
  Ein Schnitt in Module je Gegenstand steht aus (P-F, Aufgabe 3).
- Eine Obergrenze für `--limit` (P-1b).
- `N blobs match` zählt getilgte, zu Recht fehlende Blobs mit (Endprüfung,
  ruling E-6 der Endkorrektur).
- Die Hilfe von `verify --blobs` sagt „also read every blob in the store and
  check it"; gelesen wird jeder Blob, den das Register nennt und der liegen
  muss, nach einem getilgten wird nur gefragt (Endkorrektur, Teil 2).
- Die Kommandozeile ist mit zwölf Kommandos, Ausgabeverträgen und Rückgabecodes
  faktisch eine Oberfläche mit Vertrag geworden, obwohl sie nur der Einstieg
  ist, bis der MCP-Server steht (PP, A2 §11 Zeile 8).
- `PREVIOUSLY_DSN` wird nach einer Grammatik gelesen (ruling T2-k), die einen
  Text nur auf eine Weise liest, nicht immer so, wie er gemeint war. Eine
  vertippte Zeichenkette, die passt, kann ein Stück Passwort in eine Meldung
  bringen: ein Passwort aus höchstens fünf Ziffern bei vergessenem `@host`
  (`user:12345/db`) als Port (ruling T2-j), dieselbe Form ohne Datenbank als
  Datenbank, ein rohes `@` im Passwort bei vergessenem `@host` als Host, ein
  Passwort als Wert von `sslmode`, `require_auth`, `channel_binding`, gegen
  einen Server mit TLS auch von `sslrootcert` und `sslkey`, im Grund von
  libpq, ein Passwort als Benutzer oder als Datenbank (ruling T2-m). Kein
  Parser unterscheidet `user:12345` von `host:12345`. Benannt als Tabelle auf
  `configuration.md` und im Docstring von `_url_of`; gejagt wird es nicht
  (Arbeitsregel des Betreuers vom 2026-10-05: Fehlbedienung wird benannt).
  `alembic` im Checkout liest die Zeichenkette mit SQLAlchemy, nicht mit der
  Grammatik (P-AL).
- `alembic` zu importieren kostet jedes Kommando rund 70 ms, nicht nur
  `migrate` (ruling T2-e; P-AL, gemessen vom Prüfer).
- Ein Datenbankfehler beim COMMIT von `migrate`, der weder eine aufgeschobene
  Prüfung noch ein `OperationalError` ist, entginge `_refusals` und endete
  als Traceback; in PostgreSQL ist keiner bekannt (P-AL, Fixrunde 5 der
  Aufgabe 2).
- Nur `migrate` vergleicht Revisionen. Jedes andere Kommando scheitert an
  einem zurückliegenden Schema nur, wo es eine fehlende Tabelle oder Spalte
  berührt, und läuft sonst: gemessen am 2026-10-05 eine Revision zurück,
  `append`, `log` und `project` mit 0, nur `verify` verweigert; ebenso laufen
  die Kommandos eines älteren Images gegen ein neueres Schema. Bis dahin
  schützt allein die Reihenfolge der Jobs, und die Seiten sagen es so. Ob
  jedes Kommando die Revision prüfen soll, etwa in `_storage()`, entscheidet
  der Betreuer (Endprüfung der Doku, Befund Important 2; ruling E-2 der
  Auslieferung).
- Zwei Zeilen in `alembic_version`, von Hand oder aus einer verzweigten
  Geschichte, lassen `migrate` mit Traceback und Code 1 enden
  (`CommandError` aus `get_current_revision`), gemessen von der Endprüfung
  Code; kein Passwort darin. Fehlbedienung, benannt (ruling E-2 der
  Auslieferung).

### Tore und Werkzeuge

- Ein Wackler, einmal gesehen und nicht wiederholbar:
  `test_a_mail_that_carries_an_earlier_tag_does_not_close_the_fence[auto]` in
  `tests/test_mcp_server.py` scheiterte am 2026-10-13 einmal in einem
  Teillauf; acht Läufe mit wechselnder Reihenfolge danach waren grün. Kommt er
  wieder, die Saat von `pytest-randomly` aus der Ausgabe notieren und damit
  nachstellen. Diagnose (Endprüfung von Phase 1): der Test scheitert, wenn
  der Zufallsanteil des Markers eine lange Folge von Ziffern enthält, die die
  Zahlenprüfung des Testrahmens als Zahl über 2^53 liest; das Auftreten hängt
  also an der Zufallsfolge und nicht an der Reihenfolge der Tests.
- Drei geparkte Testlöcher am Doku-Tor (1b §10 Punkt 5).
- Die Reihenfolge der zwei `stderr`-Hinweise in `cli.md` hält nichts
  mechanisch; `_message_patterns` nimmt auch die `_describe`-Literale auf
  (P-1b).
- Das Tor für `§`-Zitate prüft den Marker, nicht, ob der zitierte Spec
  eingefroren ist (P-1b).
- Die Reinheit von `parse_anchors` und `format_anchor` hat Tests, aber keine
  gemessene Mutation (P-AA).
- `ruling`-Labels im Baum lösen nicht auf; das Hauptbuch der Stufe 1a ist
  verloren (`CLAUDE.md`).
- Der Zensus der Ruling-Zitate in `CLAUDE.md`,
  `grep -rnioE 'ruling (P|T[0-9]+)-[a-z0-9]+' …`, findet die Labels der
  Einheiten 3 bis 5 nicht, `R-…` und `F-…`; gezählt wird so nur ein Teil.
  Den Satz ändert der Betreuer (P-F, Aufgabe 6).
- Der Testlauf ist mit Stufe 1c von rund 31 s auf 87 s gewachsen (`632 passed in 86.80s`, gemessen am 2026-10-05 nach der Endkorrektur): ein
  zweiter Container, und Tests, die wirklich hochladen (P-1c). Mit der
  Aufnahme kam ein dritter, GreenMail, und der Lauf steht bei fast drei
  Minuten (`1071 passed in 170.26s`, im Tutorial getippt am 2026-10-06 nach
  der Fixwelle; P-PI).
- `ubuntu-latest` ist ab 2026-10-19 Ubuntu 26; die ersten Läufe der CI danach
  beobachten, vor allem die drei Container der Tests (Betreuer, 2026-10-06).
- `CLAUDE.md` nennt „the six contract names in `.importlinter`"; es sind acht.
  Den Satz ändert der Betreuer, nicht ein Umsetzer (P-PI, Aufgaben 2 und 5).
- Die Hälfte des Zertifikatstests mit `127.0.0.2` läuft nur unter Linux
  (P-PI, Aufgabe 5).
- Die neun Befunde der Kette selbst stehen seit der Endkorrektur in `cli.md`,
  aber `tests/test_docs_references.py` hält nur die Blöcke, die es mit ihrem
  Einleitungssatz kennt, und zählt dreizehn; den neuen Block hält kein Test.
  Am 2026-10-05 mit den Helfern des Tests per Skript geprüft, alle sieben
  Zeilen stimmen. Ihn aufzunehmen ist eine Änderung an `tests/` (Endkorrektur,
  Teil 2).
- Der Zitat-Test in `tests/test_docs_references.py` lässt hinter einem
  eingesetzten Wert am Satzende beliebigen Text zu; eine Verschärfung auf
  „kein Leerzeichen im eingesetzten Ende" bräche an Sätzen, die mit einem
  Grund enden (P-1c).
- Drei Tests laufen nur unter Linux und werden sonst übersprungen
  (`ru_maxrss`, `/proc`); zwei senken für die Dauer eines Kommandos die
  Dateigrößengrenze des Testprozesses (P-1c).
- Der Test zum abgebrochenen Lesen verlässt sich darauf, dass RustFS das
  Senden einstellt, wenn das Objekt gelöscht wird; an den ersten CI-Läufen
  beobachten (P-1c).
- import-linter liest `src/previously/migrations/versions/` nicht: das
  Verzeichnis hat kein `__init__.py`, und die Dateinamen der Revisionen
  beginnen mit Ziffern, sind also keine importierbaren Modulnamen. Gemessen
  blieb eine Kante von `0004_event_blob.py` nach `cli` ungemeldet. Ein
  `__init__.py` dort ist in dieser Stufe nicht gebaut; was grimp dann mit den
  Namen tut, ist ungemessen (ruling T1-d; P-AL).
- Der `` {ref}`delivery` `` im Kommentar des `Dockerfile` (ruling P-1 der
  Auslieferung) liegt außerhalb dessen, was `tests/test_docs_references.py`
  liest (`*.py`); eine umbenannte Marke ließe ihn still veralten. Ebenso nennt
  die Sprachregel in `CLAUDE.md` `scripts/`, das `Dockerfile` und
  `.dockerignore` nicht, obwohl alle drei englisch sind (Endprüfung Code,
  Befund Minor 10; an den Betreuer).
- `module-boundaries.md`: die zwei alten Blöcke mit dem früheren
  Vertragsnamen sind nur durch einen Satz weiter oben als Geschichte
  gekennzeichnet; wer direkt dorthin springt, sieht es nicht (P-AL, Prüfung
  der Aufgabe 1).
- `migrate`: zwei Mechanismen, die Autocommit-Verbindung und kein Entsperren
  im Fehlerweg, verhindern je für sich, dass das Entsperren einen Fehler
  verdeckt; der Test wird nur rot, wenn beide fehlen, und nur eine der zwei
  Sperr-Prüfungen fängt ein fehlendes `storage.close()` (P-AL, Fixrunde 1 der
  Aufgabe 2).

### Spätere Teilprojekte, unverändert offen

- Teilprojekt 3, MCP-Server: der Lesezugang ist gebaut (Einheit 4, oben unter
  *MCP-Lesezugang*), und das Konzept `specs/2026-10-10-mcp-schnittstelle.md`
  löst §8 der Architektur ab. MRTR und Tasks in Claude Code prüfen (A §13;
  gemessen am 2026-10-10 meldete Claude Code 2.1.289 `roots` und
  `elicitation`, keine Tasks);
  Pydantic kam am 2026-10-09 mit dem Gate (Ausgabeschema von `mail_overview`,
  `DEPENDENCIES.md`). Mit dem MCP-Server kommt der
  Zugang ohne `kubectl exec`; bis dahin ist der Werkzeug-Pod der Zugang (AL
  §12 Punkt 5). Der Weg per Prompt zu einer Regel gehört dazu: der Betreuer
  sagt es Claude Code, Claude Code ruft über MCP ein Werkzeug mit festem
  Schema, `previously` zeigt die Struktur, der Betreuer bestätigt; Einheit 3
  baut den strukturierten Schreibweg, auf den er aufsetzt (PG §11 Punkt 2).
  Das Konzept nennt das Werkzeug `write_policy`, mit Vorschau und Bestätigung
  über einen versiegelten Handle, nach Einheit 4 (MK §4.3).
- Teilprojekt 4, Gate: Trace-Verknüpfung über OpenTelemetry (A §13). Die
  Verarbeitungsräume der Anbieter (E §16) stehen unten unter *Erledigt*.
- Teilprojekt 5, KI-Schicht und Triage: die Batch API für Masse, mit der
  KI-Schicht (PG §11 Punkt 10); Prompt- und Templatetexte;
  Rangfunktion der Triage (A §11).
- Automatische Feststellung mit Rückfrage, Einheit 6 des Piloten: sie muss
  Inhalt, Organisation und in Folge Projekt herausfinden und im Zweifel
  fragen (`list_triage`, `write_triage_answer`, MK §4.2–§4.3); ihre Vorschläge
  kommen über den Weg der Freigabe aus Einheit 5 (F §1, §15).
- Teilprojekt 8, Bestandsimport: Pilotkunde (E §16). Gemessen lädt `append`
  rund 700 Events in der Sekunde; fünf Millionen Events sind zwei Stunden
  (PP, Bericht C).
- Teil 2, Voice: Rechtsfrage zur Gesprächsaufzeichnung; Voxtral und
  Diarisation; Call-Plattformen (E §16). Das Schema trägt `speaker`,
  `start_ms`, `end_ms` schon.
- Oberfläche jenseits MCP (A §11); Mehrsprachigkeit der Bedienung (A §11,
  Nachtrag).

## Erledigt, seit es auf einer Liste stand

- ~~Die vier Befunde aus dem Lauf der Anleitung `keep-a-club-and-its-offices.md`
  in kup6s~~ (R7, Abnahme von Phase 1 nach Z §17 Punkt 1, 2026-10-14;
  `handoffs/2026-10-14-kup6s-feedback-graph-phase-1.md`) — gefunden und
  geschlossen im Zweig `worktree-rueckmeldung-a7`, Commit `14de3d3`:
  1. `entity … --retract` gab es nicht; es ist jetzt `--state retracted`, wie
     `relate … --retract`; mit einem anderen `--state` ein Satz Abweisung,
     ohne `--subject` der Satz von `--state retracted`; die Anleitung zeigt
     die Form. Ein Test, gemessen rot unter vier Mutationen.
  2. `list_entities` zeigte eine widerrufene Entität; jetzt gilt für Entitäten,
     die der Client sieht, der Vorgabewert des Kommandos, aktive Entitäten.
     Ein Platzhalter bleibt unter jedem Filter gleich (Entscheidung des
     Betreuers, Option A, wie bei Verpflichtungen): `state`, `types` und
     `proposals` gelten nur für sichtbare Entitäten, der Client erfährt von
     einer verborgenen nur, dass sie besteht, weder Zustand noch Art. Ein
     Test, gemessen rot, wenn der Zustandsfilter wieder auf Platzhalter
     wirkt; `TOOLS_SHA256` neu genommen. `list_triage` und die übrigen Listen
     zeigen keinen Platzhalter für einen Faden, den sie auslassen.
  3. Der Platzhalter bleibt allgemein; stattdessen nennt `policy gaps` die
     Regel `source:recollection` mit der Zahl der Entitäten und Beziehungen,
     die auf einer Erinnerung stehen, solange keine Regel sie deckt
     (`graph:source:recollection`); `cli.md` und die Anleitung sagen es. Ein
     Test, gemessen rot unter vier Mutationen.
  4. Das Beispiel des Zyklus in der Anleitung scheiterte früher, an den Arten.
     Es ist ersetzt durch zwei Projekte und `part_of` in beide Richtungen,
     getippt aus einem Lauf gegen ein PostgreSQL 18 mit testcontainers.

- ~~Die eingebauten Arten sind in `vocabulary show` nicht zu erkennen~~ (R7) —
  gefunden am 2026-10-14 in der Antwort von kup6s auf den Handoff der Phase 1
  (`handoffs/2026-10-14-kup6s-feedback-graph-phase-1.md`): `apply --base` schrieb
  neun Arten, `show` listete zwölf. Geschlossen im Zweig
  `worktree-rueckmeldung-a7`: `render_file` setzt über die Tabelle von
  `circle`, `member_of` und `in_circle` die Zeile `# built in: the gate reads
  it; only its labels can change`, `parse_file` liest sie als Kommentar, und
  `vocabulary.toml` trägt sie auch. Zwei Tests, gemessen rot ohne die Zeile
  (für alle drei und für `member_of` allein), grün danach; die Referenz
  `vocabulary.md` sagt es.
- ~~Der Handoff ging mit dem Tag hinaus, bevor das Image auf `ghcr.io` stand~~
  (R7) — `v0.1.0a7` (2026-10-14): das Tag stand gut neun Minuten vor dem Image,
  und kup6s wartete. `cut-a-release.md` sagt jetzt, dass ein Handoff oder jede
  Aufforderung, die neue Version zu ziehen, erst nach `manifest` hinausgeht;
  Zweig `worktree-rueckmeldung-a7`.
- ~~`entity … --retract` ohne `--subject` kann eine erste Fassung schreiben,
  die schon widerrufen ist~~ (P-Z1, Aufgabe 5) — Commit `1b5fbf4`:
  `entity … --state retracted` ohne `--subject` wird vor dem Schreiben
  abgewiesen, wie `relate --retract`; ein Test, gemessen rot ohne die
  Prüfung (Endprüfung M12).
- ~~Eine direkte, stehende Beziehung, die Kandidaten trägt, wird auf einem
  Faden mit anhängiger Rückfrage abgewiesen~~ (P-Z1, Aufgabe 4) — kann nicht
  eintreten: `_to_problem` in `core/graph.py` weist Kandidaten an jeder nicht
  offenen Fassung schon als Formfehler ab (Endprüfung, Ruling F-d).

- ~~Die Abnahme der Einheit 5 nach F §14 durch den Betreuer; je ein echter
  Aufruf von `write_assertion` mit Claude Code und mit Vibe, das verschachtelte
  Eingabeschema über `$defs` und `$ref` probiert~~ (P-F, Aufgabe 5) — gelaufen
  am 2026-10-13 gegen `0.1.0a5` in kup6s, Zweig `mcp-erklaeren`, Commit
  `8c65e3e` (die Anleitungen). Es liefen: Vorschläge von Claude Code und Vibe;
  Freigabe und Ablehnung auf der Kommandozeile und über MCP, mit Rückfrage des
  Clients (Claude Codes Ask-Regel im Auto-Modus, Vibes Standard); Listen,
  überfällig, Geschichte; Tilgung mit Kaskade, `verify` ohne Befund; die
  Policy für einen zweiten Client (Vibe sah `ana-u` erst, nachdem seine Kette
  mit `training no` erklärt war, und die Änderung galt sofort). Das
  verschachtelte Schema ging in beiden Clients, flach machen ist nicht nötig.
  Vibe sprach `2025-11-25`. Der `kubectl port-forward` starb im Lauf und löste
  die Wiederholungen der Clients aus; der Handle fing sie ab, es entstand kein
  Duplikat; er erholt sich nicht von selbst, Stufe A2 ist die bleibende Antwort — sie steht
  seit dem 2026-10-13 (R6), der Port-Forward bleibt die Rückfalllinie.
  Nicht gelaufen: der Schlüssel der Vibe-Ask-Einstellung (siehe oben unter
  *Feststellungen*); die Kennzeichnung ist am selben Tag gegen `0.1.0a6`
  nachgemessen.
- ~~Die erste Anfrage nach einem Wechsel des Datenbank-Primärknotens scheitert~~
  (RA) — der Zweig `worktree-rueckmeldung-a5`, erster Commit `383d0ab`:
  `from_dsn` erzeugt die Engine mit `pool_pre_ping=True`, ein Test gegen echtes
  PostgreSQL beendet alle anderen Backends und liest danach (gemessen rot ohne
  die Prüfung, grün mit). Der Preis ist ein Hin und Zurück je Entnahme aus dem
  Pool; eine Verbindung, die erst nach der Prüfung stirbt, fängt es nicht.
  **Berichtigt am 2026-10-13 (R6):** die Voraussetzung war falsch gemessen. Die
  Rückmeldung RA hatte behauptet, die erste Anfrage *nach* dem Wechsel
  scheitere; kup6s misst es erneut: die fehlgeschlagene Prüfung fiel beide Male
  *in* den Wechsel (2026-10-12 um 23:28:18, der Wechsel lief bis 23:28:28), und
  die Anfragen danach gelangen schon auf `0.1.0a5`. Auf `0.1.0a6` kostete ein
  Wechsel eine Anfrage, eine Sekunde nach seinem Beginn: die Prüfung fand die
  Verbindung tot, und die neue wurde abgewiesen, weil kein Primärknoten
  antwortete. Dieses 503 ist richtig. `pool_pre_ping` bleibt, aber mit dem
  wirklichen Grund: es bewahrt die nächste Anfrage davor, an einer Verbindung
  zu scheitern, die im Leerlauf starb, wie spät sie auch kommt. Der Docstring
  von `from_dsn`, die Seite `mcp-interface.md` und der Test in
  `tests/test_storage.py` sagen das jetzt (Zweig `worktree-rueckmeldung-a6`,
  Commit `ff616c1`).
- ~~Jede fehlgeschlagene Bereitschaftsprüfung schreibt eine Kette von drei oder
  vier Tracebacks ins Log~~ (R6) — gefunden und geschlossen am 2026-10-13 im
  Zweig `worktree-rueckmeldung-a6`, Commit `ff616c1`: `ready()` in
  `mcp_server/server.py` fängt `ServerUnreachable` (eine abgewiesene
  Verbindung) und `OperationFailed` (eine Verbindung, die der Server beendete)
  und schreibt eine `WARNING`-Zeile mit dem Satz des Fehlers; jede andere
  Ausnahme behält `logger.exception`. Drei Tests gegen echtes PostgreSQL,
  gemessen rot mit `logger.exception` anstelle der Warnung. Nebenbei gefunden:
  `migrations/env.py` schaltete über `fileConfig` jeden schon bestehenden
  Logger ab, im Testlauf nach der ersten Migration auch den des Servers —
  jetzt `disable_existing_loggers=False`.
- ~~Der Warteschritt in `image` fragt die JSON-Schnittstelle von PyPI, das
  Image installiert aus dem einfachen Index; hinkt der zweite nach, scheitert
  der Bau nach PyPI~~ (P-AL, Prüfung der Aufgabe 4) — seit `v0.1.0a4` fragte
  der Schritt den einfachen Index mit `curl`, und für `v0.1.0a5` sah er die
  Version nach 2 s, `uv` im Bau fand sie noch gut eine Minute später nicht
  (RA). Jetzt löst der Schritt die Version mit `uv` selbst auf, wie das
  `Dockerfile` fragt; Zweig `worktree-rueckmeldung-a5`, erster Commit
  `383d0ab`. Lokal gegen PyPI gemessen: `0.1.0a5` besteht, `9.9.9` scheitert.
- ~~Ein zweiter Schreibweg neben `append` für `assertion`~~ (PP, A1 S1 und
  Zeile 19, zur Hälfte; F §9) — Einheit 5, Commit `69bd77f`:
  `write_statements` in `core/assertions.py` sperrt die Quellen, prüft, was
  eine Feststellung nennt, und schreibt einen Stapel in einer Transaktion,
  idempotent über die Kennung des Handles. Die Hälfte zu `action` steht oben
  unter *Feststellungen und Entitäten*.
- ~~`verify` prüft Regeln je Art erst für `action`; eine Feststellung ohne
  `sources` besteht~~ (PP, A1 S2, zur Hälfte; F §9) — Einheit 5, Commit
  `69bd77f`, mit der Fixrunde `c17879b`: die Form je Unterart, nicht leere
  Quellen, die Grammatik der Verweise, `subject`, `approves`, `of` und
  `replaces`, Quellen, die Wahrnehmungen sind und nicht getilgt; steht in
  `cli.md` unter `verify`.
- ~~`p_obligation` passt nicht durch den Projektionsmechanismus, die
  Vorrangregel braucht die `responsibility`~~ (PP, A1 S5; F §9) — ohne
  Projektion beantwortet: jede Fassung trägt ihre `responsibility`, und
  gelesen wird durch Falten aller Fassungen aus dem Log (Planentscheidung 1,
  vom Betreuer am 2026-10-12 bestätigt), Commits `97b6e8d` und `482ceb9`.
  Ob doch eine Projektion kommt, entscheidet die Messung (oben unter
  *Feststellungen*).
- ~~`kind` heißt zweierlei: die Unterart einer Feststellung hat keinen Ort~~
  (PP, A1 S3) — sie steht in der Nutzlast unter `assertion`, wie die einer
  Handlung unter `action`, Commit `97b6e8d` (F §2).
- ~~Verweise einer Feststellung auf Einheiten sind ungeprüftes JSON~~ (PP, A1
  S4, zur Hälfte) — der Schreibweg weist eine fehlende oder getilgte Einheit
  ab, und `verify` meldet eine, die das Event nicht hat, Commit `69bd77f`.

- ~~1..n IMAP-Ordner als Eingang~~ (Betreuer, 2026-10-12; PI §11 Punkt 3
  hatte einen Ordner je Lauf für den Piloten genügen lassen) — auf dem Zweig
  `worktree-imap-ordner`, Commit `5626f98`, gemergt mit PR #16 (`739912b`):
  `ingest imap --folder NAME`, wiederholbar, ohne die Option weiter
  `PREVIOUSLY_IMAP_FOLDER`; je Ordner die Wasserlinie unter dem bisherigen
  Namen `imap:<user>@<host>/<folder>` und eine Zeile, die den Ordner nennt;
  ein Ordner, der scheitert, hält die übrigen nicht auf, der Lauf endet mit
  2; eine abgewiesene Anmeldung, ein unerreichbarer Server, ein Fehler der
  Datenbank oder des Blob-Speichers halten ihn sofort an. Mehrere Postfächer
  sind mehrere Läufe, je mit eigenen Zugangsdaten. Getestet gegen GreenMail
  und PostgreSQL, auch zwei Läufe zugleich über zwei Ordner. Wie die Ordner
  genutzt werden, bleibt unter *Aufnahme aus IMAP* offen.

- ~~Bedingung 9 der Abnahme des MCP-Lesezugangs: der Lauf des Betreuers mit
  Claude Code und Vibe gegen `previously serve`~~ (ML §12) — erledigt durch
  Entscheidung des Betreuers am 2026-10-11 („mir reicht der Lauf") auf den
  Lauf von kup6s: Claude Code über `kubectl port-forward` gegen
  `previously-mcp`, `whoami` beantwortet und von `previously access`
  gelistet; mit einer Regel für `circle:ana-u` fasste Claude Code die drei
  Mails des Kreises mit Belegen zusammen, alles andere blieb Platzhalter (RG).
  **Nicht gelaufen:** Vibe, und die drei Kreise der Bedingung — einer mit
  einer Regel für beide Clients, einer mit einer für einen, einer ohne — und
  damit die Frage aus MK §1 an zwei Clients. Commit `8b93549`, die
  Rückmeldung im Repository.
- ~~Die Hinweise der Rückmeldung RG an Code, Doku und Meldungen~~ (RG) — auf
  dem Zweig `worktree-gate-mcp-rueckmeldung`: keine Einstellung trägt mehr
  einen Namen, den Kubernetes für einen Service setzt,
  `PREVIOUSLY_MCP_ADDRESS` und `PREVIOUSLY_IMAP_ADDRESS` statt der vier
  `_HOST`/`_PORT`, mit einem Test über jeden Namen der Quelle, Commit
  `07aa93e`; eine Frage ohne Antwort nennt `--yes`, eine Ablehnung nennt die
  Anbieter des Gates ohne Zusage, die Anleitung sagt, wie ein Kopf ohne
  `Bearer ` aussieht, Commit `52fac0f`; dass jeder Prozess nur erreicht, was
  seine Kommandos brauchen, ist eine Anforderung in `environment.md`, Commit
  `aa7d5dd`; der Handoff `handoffs/2026-10-11-kup6s-settings.md`, Commit
  `b9b1003`.
- ~~Das Alpha-Release `v0.1.0a3` mit Gate und MCP-Lesezugang~~ (unter *Was
  als Nächstes kommt*) — veröffentlicht am 2026-10-11 aus `ffa28fb`, dem Merge
  von PR #12. Die Handoffs des Gates und des MCP-Servers kamen nicht mit ihm,
  sie folgen mit dem Zweig `worktree-betrieb-rueckmeldung`.
- ~~Welche pgBackRest-Plugin-Implementierung~~ (A §11, §13;
  `backup-encryption.md`) — keine. kup6s hat am 2026-10-09 beide Plugins
  (experimentell, kaum gepflegt, nie gegen Hetzner oder Ceph erprobt), Barman
  Cloud (ohne Verschlüsselung beim Client) und Barman hinter `rclone serve s3`
  verworfen und sichert stündlich mit `pg_dump` durch `gpg` (RK). Der Betreuer
  hat am 2026-10-11 aus der Wahl eines Systems Anforderungen gemacht; das
  System wählt der Betrieb. Commit `15ab87a`, `backup-encryption.md`. Mit
  erledigt: der Deployment-Mechanismus und die Datenbank mit Sicherung in
  kup6s, die der Agent dort nach dem Handoff gebaut hat (RK).
- ~~Die Aufbewahrungsfrist der Sicherungen als Teil der Tilgungszusage, keine
  Frist gewählt; seit der Aufnahme die der Sicherungen des Mailservers und die
  Mail im Ordner dazu~~ (1c §4.5, §7; P-1c; PI §6) — in kup6s sieben Tage für
  die verschlüsselten Dumps, keine Sicherung und keine Kopie des Blob-Buckets
  (RK). Die Quellsysteme gehören nicht dazu: eine Tilgungszusage deckt nie den
  Mailserver, seinen Ordner, seine Sicherungen oder die Mailprogramme der
  Empfänger (Betreuer, 2026-10-11). Commit `15ab87a`: `erasure.md`,
  `erase-something.md`, `ingest-a-mail-folder.md`, `blobs.md`,
  `trust-boundaries.md`, `backup-encryption.md`, der Handoff des Gates.
- ~~Ablageort und Intervall der Anker~~ (AA §10 Punkt 4) — in kup6s
  `anchors.txt` in Git auf einem eigenen Server, täglich seit dem 2026-10-06
  (RK), Commit `3465fb1`. Dass der Ort kein Dritter ist, steht als neuer Punkt
  unter *Kette und Anker*; der benannte Restore-Point bleibt unter *Betrieb*.
- ~~Ein Bucket mit Object Lock als Ablageort der Anker: „ungeprüft, ob der
  Anbieter das hat"~~ (AA §10 Punkt 4) — Hetzner hat Object Lock, mit
  Aufbewahrung und Legal Hold, einschaltbar nur beim Anlegen des Buckets (RK),
  Commit `3465fb1`.
- ~~Die Aufnahme in kup6s nach dem Handoff
  `handoffs/2026-10-06-kup6s-ingest.md`; die erste Aufnahme des echten Ordners
  geschieht dort~~ (PI §6) — gebaut; der erste Lauf meldete `imap: 10
  appended, 1 known, 0 variants, up to uid 9` für neun Mails, der zweite
  `0 appended`, die Flags im Ordner blieben unverändert (RK), Commit
  `3465fb1`. Gemessen am 2026-10-06 im Image: 529 bis 531 MiB für eine Mail
  von 49,5 MiB (P-PI, Aufgabe 6).
- ~~Bedingung 10 der Abnahme von Gate und Policy~~ (PG §10) — der Lauf des
  Betreuers am 2026-10-09, lokal, aus `main` nach PR #9, gegen die echten APIs
  und Ollama mit `qwen3:4b`, in einer Probe mit zehn Mails aus dem Ordner
  `previously-pilot`: ohne Regel lokal, mit der Warnung und in `policy gaps`;
  „überall" → Anthropic, `inference_geo` verlangt und gemeldet `global`, die
  geschätzten Kosten $0.0001095 für 790 und 61 Tokens; „EU" → Mistral, ohne
  gemeldeten Raum; die Quelle getilgt → drei `model_call` mitgetilgt
  (`cascaded`), `verify` intakt. Dabei gefunden und mit dieser Nachlese
  behoben: das Feld `request_id` trug bei Anthropic die Id der Nachricht
  (`msg_…`) statt der Anfrage (`req_…`, Kopfzeile `request-id`); die
  Anleitung nannte drei Voraussetzungen nur in einem Satz, setzte
  `ollama serve` voraus, wo Ollama als Dienst läuft, und sagte nicht, wie man
  eine Mail mit einem Mitglied des Kreises findet.
- ~~Ein `model_call`, der zwischen dem Lesen und dem Sperren der Kaskade
  entsteht, wird nicht mitgetilgt~~ (P-PG, Aufgabe 6) — Commit `89a79f0`. Der
  Eintrag beschrieb das Fenster von `redact` aus, als den Augenblick zwischen
  Lesen und Sperren; vom Gate aus dauerte es den ganzen Aufruf beim Anbieter,
  Sekunden bis zum Timeout, und `verify` wurde mit zwei legitimen Kommandos
  rot (Endprüfung Code I-1). Nach ruling R-14 der Einheit 3 schreibt das Gate
  den Aufruf unter der Zeilensperre seiner Eingabe und tilgt seine Antwort
  selbst, wenn die Eingabe inzwischen getilgt wurde; eine Tilgung, die an der
  Sperre wartete, liest die Aufrufe danach noch einmal. Steht auf
  `erasure.md`.
- ~~Die Zeile `processed locally: …` erscheint auch bei einer Ablehnung und
  bei einem lokalen Server, der nicht antwortet~~ (P-PG, Aufgabe 5) — Commit
  `89a79f0`: sie erscheint nur noch, wo das lokale Modell geantwortet hat.

- ~~Teilprojekt 4, Gate: Verarbeitungsräume der Anbieter~~ (E §16) — Einheit 3
  des Piloten, Commits `5cbdf9d` und `26f4cb4`: was ein Anbieter zusagt
  (Räume der Rechnung, Speicherort, Aufbewahrung, ob er den Raum meldet) steht
  als Aussage `provider` im Log, und die Entscheidung setzt den Raum, den die
  Regeln verlangen. Gemessen am 2026-10-09: Anthropic meldet bei `global`
  `global` zurück. Steht auf `processing-policy.md`. Die Aufbewahrung bei
  Mistral bleibt offen (oben unter *Gate und Policy*).
- ~~Das nächste Alpha-Release mit `ingest imap`~~ — `v0.1.0a2`, veröffentlicht
  am 2026-10-09; der Handoff der Aufnahme, `handoffs/2026-10-06-kup6s-ingest.md`,
  ist am selben Tag an den Agenten in kup6s übergeben.
- ~~Bedingung 11 der Abnahme der Aufnahme~~ (PI §10 Punkt 11) — der Lauf des
  Betreuers am 2026-10-09, lokal, aus `main` nach PR #7 (`009c669`), gegen
  einen eigenen, bis dahin ungenutzten Mailu-Benutzer in kup6s und dessen
  Ordner `previously-pilot`; `chronicle`, `blob get` der Rohmail und eines
  Anhangs und der zweite Lauf mit `0 appended` so, wie die Bedingung sie
  verlangt („alles korrekt", Betreuer). In der Probe-Datenbank danach
  abgelesen: 10 Events aus `email`, 2 davon Mails im Anhang einer anderen,
  26 Zuordnungen zu 22 Blobs, 123 Einheiten, das Wasserzeichen bei UID 9.
  Der Lauf folgte dem Merge, wie das Protokoll es festhielt (P-PI,
  `index.md`) und der Betreuer es vorhatte; die Landkarte setzte ihn bis
  2026-10-09 vor den Merge.
- ~~Der Name `previously` auf PyPI ist erst belegt, wenn das erste Release
  veröffentlicht ist~~ (AL §12 Punkt 6), und mit ihm ~~Bedingung 8 der
  Abnahme~~ — Release `v0.1.0a1` vom 2026-10-05, Tag auf Commit `fd3e17f`:
  `previously 0.1.0a1` auf PyPI, die Entwicklungsversion `0.1.dev193` auf
  Test-PyPI, `ghcr.io/jensens/previously:0.1.0a1` für `linux/amd64` und
  `linux/arm64`, ohne Anmeldung abrufbar; nachgesehen am 2026-10-06 über die
  JSON-Schnittstellen von PyPI und Test-PyPI und das Manifest auf `ghcr.io`.
  Den Probelauf vor dem Merge, den AL §10 Punkt 7 vorsah, gab es nicht:
  GitHub startet einen Workflow von Hand nur aus einer Datei auf dem
  Standardzweig; `cut-a-release.md` sagt es (Plan, Entscheidung 1).
- Der äußere Anker (1a §12; 1b §10 Punkt 1) — PR #2.
- `LogStore[Conn]` als Protokoll in `contract`, beide import-linter-Ausnahmen
  entfallen (1a §12) — Stufe 1b.
- `verify` und `READ COMMITTED` (AA §10 Punkt 2) — für `examine` mit
  `snapshot()`, Commit `59072c4`.
- `_quoted_notices` mit lesbarer Zusicherung (P-1b) — Stufe Anker.
- JCS-Implementierung gewählt; Versionsquelle entschieden (1a §12) — Stufe 1a,
  `DEPENDENCIES.md`.
- `previously anchor` druckt Befunde auf die Standardfehlerausgabe statt auf
  die Standardausgabe, sodass `>>` sie nicht in die Ankerdatei trägt (P-AA);
  weicht vom eingefrorenen Anker-Spec §3 ab, die Reference-Seite gilt —
  Wartungsrunde, Commit `43f8df7`.
- Unterparser und Dispatch-Tabelle entstehen aus einer Folge `COMMANDS`; ein
  Test hält die Kommandos aus `previously --help` gegen sie (P-1b; AA §10
  Punkt 11) — Wartungsrunde, Commit `d702007`.
- `pip-audit` in der CI, als eigener Workflow `audit.yml`, wöchentlich und an
  jedem Pull-Request (A §10.6; PP, A2) — Wartungsrunde, Commit `a5ac2db`.
- Renovate konfiguriert, `renovate.json5`; die App muss der Betreuer noch auf
  dem Repository installieren (A §10.7; PP, A2) — Wartungsrunde, Commit
  `b36e715`.
- ~~Fassungsangabe je Zeile, `hash_version`, mit dem ersten `v = 2`~~ (1a
  §12) — Stufe 1c, Commits `72a0044` und `4c078ad`.
- ~~Tilgung als Event im Log (`action`, Unterart `redaction`); erst damit ist
  ein Grabstein von einer Fälschung unterscheidbar~~ (1a §12; A §4.6) —
  Stufe 1c, Commit `a0377ba`; die Blob-Form Commit `a65d1cc`.
- ~~Zeitpunkt für den Bau der Tilgung~~ (A §13) — Stufe 1c, Commit `a0377ba`.
- ~~Eine Tilgung der Nutzlast tilgt die Einheiten nicht, und `p_source_stats`
  stimmt danach nicht ohne Neubau~~ (1b §10 Punkt 2, AA §10 Punkt 5) — eine
  Tilgung des Events nimmt die Einheiten mit, Commit `a0377ba`; die Chronik
  folgt, und `p_source_stats` zählt einen Grabstein inkrementell wie neu
  gebaut weiter, Commit `600f757`.
- ~~Blobs inhaltsadressiert, clientseitig verschlüsselt, Schlüsselbehandlung,
  Dateisystem-Adapter; keine Versionierung auf dem Bucket~~ (A §4.6
  Vorkehrungen 2 und 3, §10.3, §12.1) — Stufe 1c, Commits `13d0d5e` und
  `9efb419`. Statt eines Dateisystem-Adapters gibt es einen einzigen, für
  S3 (1c §1.1); „ohne Versionierung" steht in `configuration.md` und in der
  Anleitung für den eigenen Rechner, geprüft wird es nicht.
- ~~`evidence` steht in der Nutzlast; eine Tilgung nimmt die Belegart mit~~
  (PP, A1 Zeilen 10 und 11) — entschieden: die Belegart geht mit der Nutzlast,
  `erasure.md` sagt es; Stufe 1c, Commit `a0377ba`.
- ~~Sperre auf der Zustandszeile: zwei gleichzeitige Läufe einer Projektion
  schreiben heute beide~~ (1b §10 Punkt 8, F11) — Endkorrektur, Commit
  `3ae7038`: jede Transaktion eines Nachziehens sperrt die Zustandszeile und
  liest Lesezeichen und Fassung aus ihr.
- Die Unterart einer Handlung hat einen Ort, die Nutzlast unter `action`, und
  `verify` kennt eine erste Regel je Art, für `action` (PP, A1 S2 und S3, je
  zur Hälfte; die andere Hälfte steht oben unter *Feststellungen und
  Entitäten*) — Stufe 1c, Commit `a0377ba`.
- ~~Image~~ (A §11, §13; aus dem Punkt „Deployment-Mechanismus; Image; …"
  unter *Betrieb*) — Auslieferung, Commits `aa5ee8c` (Image und Smoke-Test),
  `ea7ceb2` (Release-Weg), `05372db` und `4d7e4b9` (der Smoke-Test unter
  fremder uid). Der Rest des Punkts steht weiter dort.
- ~~`redact units` lässt den Wortlaut der Einheiten in der Nutzlast stehen,
  und `append --text` legt den ganzen Text unter `text` ab~~ (Aufgabe 8, P-1c;
  ruling E-3 der Endkorrektur) — entschieden vom Betreuer am 2026-10-05:
  `append --text` legt den Text nur noch in die Einheiten, die Nutzlast trägt
  `evidence` und mit Anhängen `blobs`; Events von vorher behalten ihre Kopie.
  Der Hinweis von `redact units` kommt nur noch, wenn ein Text der Nutzlast den
  Wortlaut einer getilgten Einheit enthält — Commit `09c5d81`. Dass eine
  Nutzlast, die den Wortlaut hält, ihn nach `redact units` behält, bleibt als
  Regel stehen und steht in `cli.md` und `erasure.md`.
- ~~Vier Kommentare in `release.yml` stimmen nicht ganz: `tag` läuft neben
  `gates`, nicht davor; „none cancelled by a newer one" gilt nur für einen
  laufenden Lauf; „widen" statt „replace"; vor dem ersten Tag ist die Version
  auf `main` `0.1.devN`, nicht `0.1.0a2.dev3`~~ (P-AL, Prüfung der Aufgabe 4)
  — Fixwelle der Endprüfung, Commit `d1813df`.
- ~~Die Etiketten `org.opencontainers.image.title`, `description`, `url` und
  `revision` erbt das Image vom Basis-Image `uv` und beschreibt damit `uv`~~
  (Aufgabe 5; Endprüfung Code, Befund Important 3) — Fixwelle der
  Endprüfung, Commit `d1813df`: das `Dockerfile` setzt jedes Etikett, das das
  Basis-Image setzt; `revision` und `created` reicht `release.yml` aus
  `github.sha` und dem Zeitpunkt der Veröffentlichung herein.
- ~~Der Docstring von `_unreadable` in `storage/postgres.py` sagt „every part
  takes the escape"; Host, Port und Schema nehmen keine~~ (P-AL, Nachprüfung
  der Fixrunde 5 der Aufgabe 2) — Fixwelle der Endprüfung, Commit `72327ea`.
- ~~Geänderter Inhalt unter bekanntem `(source, external_id)` wird stumm
  verworfen~~ (PP, A1 Zeile 8 und S7) — Einheit 1 des Piloten, Commit
  `5aa447a`: `append` vergleicht die Inhaltsidentität `artifact_hash` und weist
  Abweichendes mit `ArtifactChanged` ab; was dann geschieht, entscheidet der
  Aufrufer. Steht auf `hash-format.md` und `connectors.md`.
- ~~`RawEvent` ohne `raw: bytes` und ohne `channel_identities`~~ (PP, A1
  Zeile 12) — Einheit 1 des Piloten: `channel_identities` und
  `artifact_hash` im Vertrag, Commit `5aa447a`; die Rohbytes als Blob statt
  als eigenes Feld, weil es seit Stufe 1c einen Ort für Bytes gibt (PI §1.2
  Punkt 1), Commit `b4e5a8c`. Der Grund steht auf `connectors.md`.
- ~~Der Nutzlastbereich weist Mail-Header-Schlüssel und Bytes ab; ein
  Konnektor muss umformen~~ (PP, A1 Zeile 14 und Leitsatz 4) — für Mail
  umgeformt, Commits `0807c35` und `a1da00e`: die Kopfzeilen als Liste von
  Paaren, die Bytes als Blobs; `mail-mapping.md`. Gleitkommazahlen bleiben
  ausgeschlossen.
- ~~Eine Wiedersichtung nach der Tilgung~~ (1c §12 Punkt 12) — Einheit 1 des
  Piloten: ein getilgtes Event ist unter seinem Schlüssel bekannt, Commit
  `5aa447a`, und der Lauf schlägt nach, bevor er Blobs speichert, sodass eine
  getilgte Mail ihre Rohbytes nicht in den Bucket zurücklegt (ruling T4-a der
  Aufnahme), Commit `b4e5a8c`. Dass der Hash kein Salz trägt, steht auf
  `erasure.md`; dass eine erneut weitergeleitete Mail als Anhang zurückkommt,
  oben unter *Tilgung*.
