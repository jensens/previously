# Previously — die MCP-Schnittstelle als Ganzes

**Datum:** 2026-10-10
**Status:** Entwurf, zur Durchsicht durch den Betreuer

Konzept für das Hauptinterface von Previously. Es **löst §8 der Architektur
ab** (`specs/2026-10-01-architektur.md`, eingefroren) und entscheidet, wie die
MCP-Schnittstelle im Endausbau aussieht — Werkzeuge, Ressourcen, Prompts,
Zugang, Verarbeitungsprüfung, Zugriffsprotokoll, Fehler, Versionen,
Sicherheit, Betrieb. Gebaut wird davon zuerst nur der Lesezugang, mit eigenem
Spec (`specs/2026-10-10-pilot-mcp-lesezugang.md`). Was das Konzept für spätere
Einheiten festlegt, ist der Rahmen, in den sie sich fügen; jede bekommt ihren
eigenen Spec.

Grundlage sind die Recherche vom 2026-10-09
(`recherche/2026-10-09-mcp-stand-und-designgrundlagen.md`, „R" mit Abschnitt),
die Messungen vom 2026-10-10 (`recherche/2026-10-10-mcp-messungen.md`, „M" mit
Abschnitt), das Gespräch mit dem Betreuer am 2026-10-10 und die Landkarte.

Dieser Spec friert ein, sobald seine Explanation-Seiten stehen (`CLAUDE.md`);
die stehen mit Einheit 4.

---

## 1. Zweck und Rahmen

MCP ist die Oberfläche, über die gearbeitet wird: der Betreuer fragt, ein
Client (Claude Code, Mistral Vibe, ein lokaler Harness) übersetzt die Frage in
Aufrufe, Previously liefert Belege, der Client urteilt. „Was ist bei Kunde X
offen?" braucht kein Modell in Previously — der Client *ist* in dem Moment die
Intelligenz (Entwurf §4). Ein Designfehler hier wird teuer, weil jeder Client
und jede Gewohnheit an der Schnittstelle hängt.

**Drei Ziele, in dieser Rangfolge:**

1. **Kein Inhalt geht an einen Verarbeiter, den die Policy nicht zulässt** —
   auch nicht an den Client selbst (§3).
2. **Eine Frage wie „Was ist der Stand der Serverinstallation unseres
   foobar-Connectors im XY-Projekt, was ist erledigt, welche Todos sind bis
   wann offen, hat der Kunde noch Fragen?" ist mit wenigen Aufrufen
   beantwortbar** (Betreuer, 2026-10-10).
3. **Was über MCP geschieht, ist im Log nachweisbar**: was welcher Client wann
   gesehen hat und was ihm vorenthalten blieb (§5).

### 1.1 Die Clients

Claude Code und Mistral Vibe sind die beiden Clients, an denen der Entwurf
geprüft wird; ein lokaler Harness gegen ein lokales Modell ist der dritte
(Architektur §8.8). Gemessen am 2026-10-10 (M3, M4):

- Claude Code 2.1.289 spricht die Revision `2026-07-28`, kennt Werkzeuge,
  Ressourcen, Prompts und Elicitation.
- Vibe 2.26.1 spricht `2025-11-25`, kennt **nur Werkzeuge**, öffnet für jeden
  Aufruf eine neue Verbindung und hält im „unified harness" die Werkzeugliste
  über Sitzungen.

**Das Design richtet sich nach der neuen Generation.** Die alte bekommt, was
das SDK ihr ohne eigenen Code gibt (`stateless_http=True`), und **hält nichts
Neues auf**; kein Code von Previously verzweigt nach Generation, und ein
Merkmal, das das bräuchte, bekommt die alte Generation nicht (Betreuer,
2026-10-10). Vibe ist Prüfstein dafür, dass der Kern über Werkzeuge erreichbar
ist, nicht Bremse für das, was nur ein moderner Client kann. Sobald Vibe die
neue Generation spricht, fallen Schalter und Test der alten weg.

### 1.2 Was dieser Spec an früheren Festlegungen ändert

- **§8 der Architektur ist abgelöst.** Bestätigt bleiben (R §1.8): die Revision
  `2026-07-28`, Zustandslosigkeit mit Handles, kein Sampling, Idempotenz bei
  schreibenden Aufrufen, Quellenpflicht über Schemata, das austauschbare
  Cockpit. Geändert: der Werkzeugkatalog (§4), die Bestätigung schreibender
  Aufrufe ohne Elicitation (§4.3), Tasks erst additiv (R §1.4).
- **Die „Offenlegungsprüfung im `mcp_server`"** (Architektur §8.7) ist die
  Verarbeitungsprüfung aus Einheit 3, angewandt auf den Client (§3); die
  Prüfung vor dem Schreiben nach außen bleibt davon getrennt (PG §1.2).
- **Die Werkzeugnamen des Entwurfs** (`list_open_obligations`, `submit`,
  `record_assertion`, `approve`) werden durch den Katalog in §4 ersetzt; das
  Leitwerkzeug heißt weiter `previously`.

---

## 2. Ort und Prozesse

- **Ein Modul `previously.mcp_server`**, in der Schicht von `gate` und
  `connectors`, über `core`. Es liest über `core`, entscheidet mit
  `core/decide.py` und ruft **nie** ein Modell auf; das tut nur das Gate
  (Architektur-Regel 2). Nur `mcp_server` importiert das SDK `mcp`; der
  import-linter zählt die Ausnahme namentlich auf.
- **Das offizielle SDK `mcp` 2.x** mit `MCPServer` (R §7). Gemessen: es bedient
  beide Generationen am selben Endpunkt (M1), und pyright strict meldet über
  einen minimalen Server unter der Projektkonfiguration nichts (M2).
- **Zwei Einstiege im selben Paket und Image:**
  - `previously mcp` — stdio, für einen Client, der den Prozess selbst startet
    und die Datenbank erreicht;
  - `previously serve` — die ASGI-App mit Streamable HTTP, Antworten als JSON,
    nicht als Strom.
- **Zustandslos.** Ein Aufruf trägt alles, was er braucht; ein Cursor ist ein
  Argument, kein Zustand (R §1.1). Zunächst ein Replikat; mehrere erst, wenn
  zwei Worker gemessen sind (M „Was offen bleibt").

---

## 3. Wer fragt, und was er sehen darf

### 3.1 Ein Client ist ein Prinzipal mit einer Verarbeitungskette

Was ein Client sieht, geht an seinen Verarbeiter: was Claude Code sieht, an
Anthropic; was Vibe sieht, an Mistral; was ein lokaler Harness sieht, bleibt im
Haus. **Der Client ist also ein Verarbeiter wie die Anbieter des Gates**, und
dieselbe Policy entscheidet über ihn (Betreuer, 2026-10-10).

- **`previously client add <name> --processor <zusage>`** legt einen Client an:
  einen Namen und die Zusage, die seine Verarbeitungskette beschreibt. Der
  Befehl gibt einen Token **einmal** aus; gespeichert wird sein SHA-256.
  `client revoke`, `client list` wie bei der Policy.
- **Gespeichert als Handlung `policy` mit der neuen Art `client`**: Schlüssel
  der Name, Inhalt die Zusage und der Hash des Tokens, dazu der Satz als
  Herkunft. Ein neueres Event löst ab, ein Widerruf hebt auf; welcher Client
  wann galt, steht im Log.
- **Über stdio gibt es keinen Token**: wer den Prozess startet, ist der
  Client. Der Name steht in `PREVIOUSLY_MCP_CLIENT` und muss als Client
  angelegt sein; sonst startet der Server nicht.

### 3.2 Die Verarbeitungskette

Eine Zusage beschreibt die **ganze Kette**, nicht nur einen Anbieternamen: GLM
über Mistral rechnet bei Mistral in der EU mit einem Modell von Zhipu;
OpenRouter vermittelt an wechselnde Unterverarbeiter; Claude Code im Max-Plan
läuft unter Verbraucherbedingungen und ist nicht dieselbe Kette wie die
Anthropic-API des Gates. Die Zusage aus Einheit 3 bekommt deshalb vier Felder
dazu (Betreuer, 2026-10-10):

| Feld | heißt | gibt es |
|---|---|---|
| `operator` | wer rechnet, als juristische Person | neu |
| `inference` | Rechenräume und ihre Bedeutung | seit Einheit 3 |
| `storage` | Speicherort, leer = keiner | seit Einheit 3 |
| `retention_days` | Aufbewahrung, `null` = unbekannt | seit Einheit 3 |
| `training` | ob die Daten zum Training dienen: `true`, `false`, `null` = unbekannt | neu |
| `subprocessors` | Liste weiterer Verarbeiter, `null` = unbekannt | neu |
| `model_origin` | wer das Modell gebaut hat | neu |
| `local` | auf Hardware des Betreibers | seit Einheit 3 |

Eine **Regel** kann jede Eigenschaft einschränken: dazu kommen
`no_training`, `no_subprocessors`, `excluded_operators`,
`excluded_model_origins`. Wie bei der Aufbewahrung besteht ein unbekannter
Wert keine Einschränkung, die ihn betrifft. Die Liste ist erweiterbar
(Rechtsgrundlage, Zertifizierung), wenn ein Kunde mehr verlangt; heute nicht
(Betreuer: „zu akademisch").

### 3.3 Die Prüfung je Inhalt

Für **jedes Event**, das ein Aufruf liefern würde, entscheidet `decide` aus
Einheit 3 — mit den Beteiligten und der Quelle des Events und der Kette des
Clients als einzigem Kandidaten. Besteht sie nicht, wird das Event
**zurückgehalten**: es erscheint als Platzhalter mit URI und Grund, **ohne
Betreff und ohne Beteiligte** — auch die sind Inhalt.

```
[withheld: previously://event/43 — circle h_da requires eu; this client (claude-code-max) processes in us]
```

**Die Vorgabe „ohne Regel nur lokal" gilt auch hier.** Ein Kreis ohne Regel
ist für jeden Client unsichtbar, der nicht lokal ist; bevor Claude Code die
Chronik eines Kunden sieht, braucht dessen Kreis eine Regel, die die Kette von
Claude Code zulässt. Das ist gewollt und wird sichtbar gemacht: der
Platzhalter nennt den Grund, `whoami` sagt, was ein Client grundsätzlich sieht,
`policy_gaps` listet die Lücken.

Was **kein Kundeninhalt** ist, liefert der Server jedem Client: die Namen der
Kreise, ihre Regeln, die Anzahl der Mitglieder, die Zusagen. Das sind
Setzungen des Betreibers, keine Inhalte eines Kunden. Die Adressen der
Mitglieder gehören nicht dazu; sie sind Identitäten Dritter.

---

## 4. Der Katalog

### 4.1 Grundsätze

- **Werkzeuge sind der Vertrag**; jede Fähigkeit ist über ein Werkzeug
  erreichbar, weil Vibe nur Werkzeuge kennt (M3). Ressourcen und Prompts sind
  Abkürzungen für Clients, die sie kennen.
- **Wenige Werkzeuge, nach Arbeitsabläufen geschnitten** (R §2.4): im
  Endausbau etwa fünfzehn.
- **Eine Frage in wenigen Aufrufen**: ein Aufruf liefert viel Zusammenhang
  (§6), ein Werkzeug nimmt mehrere IDs, die Suche wird zuerst ein Parameter des
  Leitwerkzeugs.
- **Lesen und Schreiben sind am Namen getrennt.** Alles Schreibende beginnt
  mit `write_`; so reicht in beiden Clients ein Muster
  (`mcp__previously__write_*`, `previously_write_*`), um Schreiben auf „immer
  fragen" zu stellen. Kein Werkzeug versteckt Lesen und Schreiben hinter einem
  Parameter.
- **Der Zuschnitt ist der Kreis** (Betreuer, 2026-10-10); `project` und
  `matter` sind als Parameter reserviert und kommen mit Einheit 5 dazu, ohne
  dass sich ein bestehender Aufruf ändert. Wie Projekte entworfen werden, ist
  offen (§10).

### 4.2 Lesen

| Werkzeug | liefert | kommt mit |
|---|---|---|
| `previously` | die Chronik: `circle`, `source`, `since`, `until`, `cursor`; später `project`, `matter`, `query` | Einheit 4 |
| `get_event` | ein oder mehrere Events (`ids`) mit allen Einheiten und ihrer Herkunft, stückweise | Einheit 4 |
| `list_circles` | Kreise, ihre Regeln, Anzahl der Mitglieder | Einheit 4 |
| `whoami` | Client, Kette, was die Policy ihm grundsätzlich erlaubt | Einheit 4 |
| `policy_gaps` | wo die Vorgabe „nur lokal" gegriffen hat — im Gate und hier | Einheit 4 |
| `search` | Treffer als URI mit Ausschnitt, über alle Kreise | mit der Suche |
| `list_obligations`, `list_decisions` | Feststellungen mit Frist und Quelle | Einheit 5 |
| `list_triage`, `list_approvals`, `get_job` | Rückfragen, Freigaben, Läufe | Einheit 6 |

### 4.3 Schreiben

Jedes schreibende Werkzeug ist **ein** Werkzeug mit **zwei Schritten**: ein
Aufruf ohne `confirm` liefert eine Vorschau und einen Handle; erst ein Aufruf
mit `confirm=<handle>` schreibt. Der Handle ist versiegelt (HMAC über Inhalt,
Client und Ablauf), an den Client gebunden, läuft nach zehn Minuten ab und
gilt einmal. Das funktioniert in jedem Client; Elicitation, wo ein Client sie
kann, ist eine spätere Aufwertung, nie der einzige Weg (R §1.3, M3).

| Werkzeug | schreibt | kommt mit |
|---|---|---|
| `write_policy` | eine Regel, einen Kreis, eine Mitgliedschaft — der Client übersetzt den Satz des Betreuers, der Betreuer bestätigt die Struktur | nach Einheit 4 |
| `write_submit` | einen Einwurf | später |
| `write_assertion` | eine Feststellung, etwa eine Korrektur | Einheit 5 |
| `write_triage_answer`, `write_approve` | Antwort auf eine Rückfrage, Freigabe oder Ablehnung | Einheit 6 |
| `write_import` | startet einen Bestandsimport, liefert eine Job-ID | Teilprojekt 8 |

**Idempotenz:** ein schreibender Aufruf trägt optional eine
`idempotency_key`; ohne leitet der Server einen Schlüssel aus Inhalt, Client
und Art ab. Eine Wiederholung — Claude Code wiederholt einen Aufruf nach einem
Verbindungsabbruch (R §6) — liefert das ursprüngliche Ergebnis.

**Lese- und Schreibserver werden zwei Prozesse**, sobald ein schreibendes
Werkzeug Zugangsdaten eines fremden Systems hält (GitLab, Jira), damit eine
Kompromittierung des lesenden keine erbeutet (R §5).

### 4.4 Ressourcen und Prompts

Für Clients, die sie kennen, nur lesend, mit derselben Prüfung und demselben
Eintrag im Zugriffsprotokoll wie die Werkzeuge:

- Ressourcen: `previously://circle/{name}/chronicle` (erste Seite) und
  `previously://event/{id}`, als Templates; `cacheScope: private`.
- Prompts: `chronicle_summary(circle, since, until)` und
  `whats_open(circle)` — Abkürzungen für den Betreuer, die einen Auftrag an den
  Client formulieren und auf die Werkzeuge verweisen.

---

## 5. Das Zugriffsprotokoll

Jeder Aufruf — Werkzeug, Ressource, Prompt — wird ein Event der Art `action`,
`payload.action = "mcp_access"`, ohne Quellschlüssel. Eine Quelle der Wahrheit
neben dem Wissensspeicher gibt es nicht (Betreuer, 2026-10-10).

```
payload
{
  "action": "mcp_access",
  "client": "claude-code",
  "policy": {"client": 31, "processor": 12, "rules": [19]},
  "call": {"kind": "tool", "name": "previously",
           "arguments": {"circle": "h_da", "since": "2026-09-01"}},
  "delivered": [{"event": 42, "units": [1, 2, 3]}],
  "withheld": [{"event": 43, "reason": "circle h_da requires eu; this client processes in us"}],
  "outcome": "ok",
  "era": "2026-07-28"
}
```

- **Kein Inhalt**: IDs, Namen, Gründe, die Argumente des Aufrufs. Darum keine
  Kaskade bei einer Tilgung; die IDs zeigen dann auf Grabsteine.
- **Das Log beantwortet**, was ein Client je über einen Kreis gesehen hat, und
  was ihm vorenthalten blieb.
- **Die Menge** liegt bei einigen tausend Events im Monat. Sie wird
  beobachtet; ab welcher Schwelle zusammengefasst werden müsste, ist ein
  offener Punkt (§10).

---

## 6. Form der Ergebnisse

Gemessen am 2026-10-10 (M4) und daraus abgeleitet:

- **Ein Textblock in Markdown je Ergebnis**, ohne `structuredContent` und ohne
  `resource_link`: beides kostet in mindestens einem Client Inhalt, in Vibe das
  ganze Ergebnis.
- **Quellen als URI im Text**: `previously://event/<id>`, eine Einheit als
  `#unit-<n>`.
- **Fremdinhalt eingezäunt**, mit einem zufälligen Begrenzer je Antwort, den
  eine Mail nicht vorhersagen kann; der Kopf darüber stammt von Previously.
  Eine Wette gegen Prompt-Injection, keine Schutzgrenze (R §5.4): die Grenze
  sind getrennte Werkzeuge und die Bestätigung jedes Schreibens.
- **Steuer- und unsichtbare Zeichen werden nur bei der Ausgabe entfernt**,
  gezählt und vermerkt; gespeichert bleiben sie, weil die Bytes in der Kette
  festgeschrieben sind.
- **Platzhalter** für Zurückgehaltenes (§3.3) und Getilgtes
  (`[erased: previously://event/44]`).
- **Grenzen**: rund 20.000 Tokens je Seite, unter der Kappung von Claude Code
  (25.000); ein undurchsichtiger Cursor für die nächste Seite; keine Zahl über
  2^53, Hashes als Hex.
- **Fehler** beginnen mit `Error:`, nennen den nächsten Schritt und zitieren nie
  Kundeninhalt; `isError` wird gesetzt, nicht vorausgesetzt (Vibe verliert es,
  M4).

````
previously · circle h_da · 2026-09-01 – 2026-09-30 · page 1 of 2 · next: c=7f3a…

### previously://event/42 · 2026-09-12 09:14 · email · Eva Huber → Jens Klein
Subject: AW: Serverinstallation foobar connector
<<<customer-content 9c1e>>>
Der Server steht, es fehlt noch der TLS-Zugang. Bis Freitag?
<<<end 9c1e>>>

[withheld: previously://event/43 — circle h_da requires eu; this client (claude-code-max) processes in us]
[erased: previously://event/44]
````

---

## 7. Zugang

- **Über HTTP**: ein statischer Token je Client als `Authorization: Bearer`,
  geprüft hinter der `TokenVerifier`-Schnittstelle des SDK. Ein Wechsel zu
  OAuth tauscht diese Prüfung aus und sonst nichts; beide Clients können CIMD,
  ein Autorisierungsserver ohne DCR genügt dann (R §4).
- **Keine Protected Resource Metadata**, solange es keinen
  Autorisierungsserver gibt; ohne gültigen Token antwortet der Server mit 401
  und einem Satz.
- **`Origin` und Host werden geprüft**; ohne Konfiguration bindet der Server an
  `127.0.0.1`, weitere Namen (etwa im Tailnet) erlaubt
  `PREVIOUSLY_MCP_ALLOWED_HOSTS`.
- **Der Token bleibt Pflicht, auch in einem geschlossenen Netz**: das Netz sagt,
  dass jemand aus dem eigenen Netz fragt; der Token sagt, welcher Client, und
  das braucht das Zugriffsprotokoll.

---

## 8. Versionen und Stabilität

- Der Server meldet die Paketversion. **Die Werkzeugliste ändert sich nur mit
  einem Release**; danach verbinden die Clients neu — Vibes „unified harness"
  sieht neue Werkzeuge sonst nicht (M3).
- Ein Test hält die Werkzeugliste — Namen, Beschreibungen, Schemata — gegen eine
  Prüfsumme; eine Änderung ist eine bewusste Änderung mit Release.
- Eine Änderung, die einen bestehenden Aufruf bricht, bekommt einen **neuen
  Namen**; der alte bleibt ein Release lang.
- **Beschreibungen und `instructions` sind deklarativ**, nennen nie Kundendaten
  und enthalten keine Anweisungen an das Modell, die über die Bedienung des
  Werkzeugs hinausgehen.
- **Die getesteten Clientkonfigurationen stehen datiert in der Doku**: für
  Claude Code `claude mcp add --transport http … --header`, für Vibe `headers`
  statt `api_key_env` (M3).

---

## 9. Was das für den Betrieb heißt

- **kup6s.** Ein eigenes Deployment `previously-mcp` mit `previously serve`,
  ein Service, ein Replikat, Bereitschaft über `server/discover`. Der Zugang in
  Stufen:
  - **A** — `kubectl port-forward`, dasselbe Vertrauensmodell wie der
    Werkzeug-Pod;
  - **A2** — über das vorhandene Tailscale/Headscale-Netz des Betreuers; der
    Agent in kup6s weiß, wie (Betreuer, 2026-10-10); `PREVIOUSLY_MCP_ALLOWED_HOSTS`
    nennt den Namen im Tailnet;
  - **B** — ein Ingress mit TLS und Token, vielleicht nie nötig; eine
    Hosting-Frage, hier nicht entschieden.
  Der Handoff kommt mit Einheit 4, zusammen mit dem zurückgehaltenen Handoff
  des Gates und dem lokalen Modellserver, und mit dem Release, das beides
  enthält.
- **Ein Host mit `docker-compose`.** Ein Dienst `mcp` neben der Datenbank, nur
  auf `127.0.0.1` veröffentlicht; ein Token je Client.
- **Lokal.** `previously mcp` über stdio, wenn der Client die Datenbank
  erreicht.
- **Zeitlimits.** Jeder Aufruf bleibt deutlich unter 60 Sekunden, der Vorgabe
  von Vibe; was länger dauert, liefert eine Job-ID (R §3).
- **Der Einfachheits-Check**: ein Prozess mehr, ein Token je Client, kein
  Zustand, keine neue Tabelle.

---

## 10. Was offen bleibt

1. **Wie Projekte entworfen werden.** Die Idee des Betreuers: ein Projekt als
   „Kreis von Kreisen", rekursiv aufgelöst, mit Unterprojekten — „sind
   Projekte nur Mengenlehre über Identitäten?" Die Gegenthese aus dem
   Gespräch: **Kreise in Kreisen** tragen (die Policy erbt die strengste
   Regel, die Chronik umfasst die Unterkreise); **ein Projekt ist aber keine
   Menge von Identitäten** — dieselben drei Leute arbeiten an zwei Projekten —,
   sondern eine Zuordnung von Events (eine Feststellung), die einen Kreis als
   stärkstes Signal hat; Unterprojekte über Projekte, die auf Projekte zeigen.
   Zu entscheiden mit Einheit 5.
2. **Die Menge der `mcp_access`-Events** beobachten und eine Schwelle nennen,
   ab der zusammengefasst werden müsste.
3. **Vibe auf `mcp` 2.x**: dann Schalter und Test der alten Generation
   entfernen.
4. **Mehrere Replikate**, sobald zwei Worker hinter einem Lastverteiler
   gemessen sind.
5. **OAuth** mit einem Autorisierungsserver, wenn mehr als ein Mensch zugreift.
6. **Elicitation als Aufwertung** der Bestätigung, wo ein Client sie meldet.
7. **Tasks** für lange Läufe, wenn SDK und ein Client sie haben (R §1.4).
8. **Der Effekt der Einzäunung** von Fremdinhalt auf aktuelle Modelle ist
   ungemessen (R §10 Punkt 13).
