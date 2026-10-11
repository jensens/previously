# Previously — Pilot, Einheit 4: der MCP-Lesezugang

**Datum:** 2026-10-10
**Status:** Entwurf, vom Betreuer am 2026-10-11 durchgesehen („ok für den Plan"), Grundlage des Plans

Detail-Spec für die vierte Einheit des Piloten. Er schneidet aus dem Konzept
`specs/2026-10-10-mcp-schnittstelle.md` („K" mit Abschnitt) den Lesezugang und
setzt die Einheiten 0 bis 3 voraus (auf `main` seit `d8d0b16`). Messungen und
Recherche: `recherche/2026-10-10-mcp-messungen.md` („M"),
`recherche/2026-10-09-mcp-stand-und-designgrundlagen.md` („R").

Dieser Spec friert ein, sobald seine Explanation-Seiten stehen (`CLAUDE.md`);
mit ihm friert das Konzept ein.

---

## 1. Zweck und Zuschnitt

Claude Code und Mistral Vibe fragen das Log: die Chronik eines Kunden, einzelne
Mails im Ganzen, welche Kreise und Regeln es gibt, was der Client sehen darf —
jeder Inhalt nur, wenn die Policy die Verarbeitungskette des Clients zulässt,
und jeder Aufruf im Log.

**Lieferungen:**

1. **Clients als Prinzipale** mit Token und Verarbeitungskette (§2).
2. **Die erweiterte Verarbeitungskette** und Regeln, die jede ihrer
   Eigenschaften einschränken (§3).
3. **Der Server**: `previously mcp` (stdio) und `previously serve` (HTTP),
   beide Generationen über das SDK (§4).
4. **Fünf Werkzeuge, zwei Ressourcen, zwei Prompts** mit der Prüfung je Inhalt
   (§5, §6).
5. **Das Zugriffsprotokoll** als Handlung `mcp_access` und das Kommando
   `previously access`, das es liest (§7).
6. **Doku, Handoff an kup6s, Release** (§10, §8).

**Nicht enthalten:** schreibende Werkzeuge (auch `write_policy`), die Suche,
Projekte und Vorgänge, OAuth, mehrere Replikate, Elicitation, Tasks.

---

## 2. Clients

- `previously client add <name> --processor <zusage> --statement "…"` legt
  einen Client an und gibt **einmal** einen Token aus: 32 Zufallsbytes aus
  `secrets`, URL-sicher kodiert. Gespeichert wird `token_sha256`.
- Gespeichert als Handlung `policy` mit `policy: "client"`: Schlüssel `name`,
  Felder `processor`, `token_sha256`, `statement`, `revoked`. Der Schreibweg und
  die Ablösung sind die aus Einheit 3; `--revoke` hebt auf, `client list`
  zeigt Name, Zusage und Datum, nie den Hash.
- Abgewiesen wird eine Zusage, die nicht deklariert ist.
- `client add` für einen Namen, der schon einem gültigen Client gehört, **löst
  ihn ab**: ein neuer Token, der alte gilt ab dem nächsten Aufruf nicht mehr.
  So wird ein Token rotiert; der Befehl sagt es, bevor er schreibt.
- `read_policy` liefert die Clients unter `Policy.clients`, mit den Ids für das
  Audit wie bei den anderen Arten.
- Ein Token wird gegen die Hashes der gültigen Clients verglichen, in
  konstanter Zeit (`hmac.compare_digest`).

---

## 3. Die Verarbeitungskette

### 3.1 Vier neue Felder einer Zusage

`previously policy provider` bekommt `--operator <name>`,
`--training yes|no|unknown`, `--subprocessors <name> …|none|unknown`,
`--model-origin <name>` (K §3.2). Alle sind für **neue** Zusagen Pflicht außer
`--model-origin` (Vorgabe: unbekannt); eine bestehende Zusage aus Einheit 3
liest sich mit `operator`, `training`, `subprocessors` als unbekannt, bis sie
neu deklariert wird. Die Nutzlast bekommt `operator`, `training` (`true`,
`false`, `null`), `subprocessors` (Liste oder `null`), `model_origin`.

### 3.2 Vier neue Einschränkungen einer Regel

`previously policy rule` bekommt `--no-training`, `--no-subprocessors`,
`--exclude-operator <name>`, `--exclude-model-origin <name>`. Zusammengeführt
wird wie in Einheit 3: Flags als „eine verlangt es, also gilt es", Mengen als
Vereinigung. Ein Kandidat besteht eine Einschränkung nicht, wenn der
betroffene Wert unbekannt ist — wie bei der Aufbewahrung.

### 3.3 Für den Piloten

Der Betreuer deklariert die Kette von Claude Code im Max-Plan als eigene
Zusage, getrennt von `anthropic` des Gates, mit den Werten seines Kontos
(Verbraucherbedingungen; ob Training an ist, steht in den Einstellungen von
claude.ai), und die Kette von Vibe (Mistral, Free-Plan). Die Werte sind seine
Aussage, mit dem Satz als Herkunft; der Spec setzt keine.

---

## 4. Der Server

- **`previously mcp`** — stdio. Der Client steht in `PREVIOUSLY_MCP_CLIENT`;
  ist er nicht angelegt oder widerrufen, endet der Befehl mit 2 und einem
  Satz, bevor er eine Anfrage liest.
- **`previously serve`** — Streamable HTTP unter `/mcp`, Antworten als JSON
  (`json_response=True`), beide Generationen (`stateless_http=True`).
  `PREVIOUSLY_MCP_HOST` (Vorgabe `127.0.0.1`), `PREVIOUSLY_MCP_PORT` (Vorgabe
  `8765`), `PREVIOUSLY_MCP_ALLOWED_HOSTS` (weitere Hostnamen, etwa im Tailnet).
  Ohne gültigen Token: 401 mit einem Satz; ein Aufruf mit Token eines
  widerrufenen Clients ebenso.
- **Zustandslos**, ein Prozess. Jeder Aufruf liest die Policy neu; ein
  widerrufener Client ist ab dem nächsten Aufruf ausgesperrt.
- **Die Werkzeugliste** ist fest; ein Test hält Namen, Beschreibungen und
  Schemata gegen eine Prüfsumme (K §8).

---

## 5. Die Werkzeuge

Alle Ergebnisse folgen K §6: ein Textblock in Markdown, Quellen als URI,
Fremdinhalt eingezäunt mit einem zufälligen Begrenzer je Antwort, Steuer- und
unsichtbare Zeichen bei der Ausgabe entfernt und gezählt, Platzhalter für
Zurückgehaltenes und Getilgtes, keine Zahl über 2^53, Fehler mit `Error:`.

### 5.1 `previously`

Argumente: `circle` (optional), `source` (optional), `since`, `until`
(optional, ISO-Datum oder -Zeitpunkt), `cursor` (optional).

- Liefert die **Wahrnehmungen** (`observation`) in Zeitordnung
  (`occurred_at`, dann `id`), auf die die Filter passen: `circle` — ein Mitglied
  des Kreises ist beteiligt (ohne eigene Identitäten, wie in `decide`);
  `source` — die Quelle; `since`/`until` — `occurred_at`.
- Je Event: Kopf (URI, Zeit, Quelle, Absender und Empfänger aus
  `channel_identities`), dann **alle Einheiten** im Zaun.
- **Eine Seite** endet, bevor sie 60.000 Zeichen überschreitet (rund 15.000 bis
  20.000 Tokens, unter der Kappung von Claude Code; im Bau an echten Mails
  nachgemessen); ein einzelnes Event, das allein darüber läge, wird gekürzt
  und verweist auf `get_event`. Der Fuß nennt Seite und `cursor`.
- Der Cursor kodiert die letzte Stelle (`occurred_at`, `id`) und die Filter; er
  ist nicht versiegelt — er gibt nichts frei, die Prüfung läuft bei jedem
  Aufruf neu.
- Gelesen wird **aus dem Log**, nicht aus `p_chronicle`: die Projektion kennt
  die Beteiligten nicht, und für den Piloten reicht das Lesen des Logs. Ab
  welcher Menge eine eigene Projektion nötig wird, ist offen (§13).

### 5.2 `get_event`

Argumente: `ids` (1 bis 20 Event-IDs), `from_unit` (optional, für lange
Events). Liefert jedes Event ganz, mit Kopf, allen Einheiten, den Namen der
Blobs (Anhänge) ohne ihren Inhalt, und der Herkunft (`found_in`, Message-ID).
Ein Event, das keine Wahrnehmung ist, liefert `Error: … is not an observation`
für diese ID; die anderen bleiben unberührt.

### 5.3 `list_circles`

Je Kreis: Name, Satz, geltende Regel (oder „keine — nur lokal"), Anzahl der
Mitglieder, und ob **dieser** Client Inhalte des Kreises sieht. Keine Adressen.

### 5.4 `whoami`

Name des Clients, seine Zusage mit allen Feldern, die Generation des Aufrufs,
und eine Liste: welche Kreise und Quellen dieser Client sieht, welche nicht,
mit Grund.

### 5.5 `policy_gaps`

Wie `previously policy gaps` (Einheit 3), erweitert um die Zurückhaltungen aus
`mcp_access`, deren Grund das Fehlen einer Regel war: je Kreis oder Quelle
Anzahl und letztes Datum, getrennt nach Gate und MCP.

---

## 6. Ressourcen und Prompts

- Ressourcen-Templates `previously://circle/{name}/chronicle` (die erste Seite
  von `previously(circle=name)`) und `previously://event/{id}` (wie
  `get_event`). `resources/list` liefert keine Einträge, nur die Templates:
  eine Liste der Kreise als Ressourcen verriete nichts, was `list_circles`
  nicht auch sagt, kostete aber eine zweite Oberfläche.
- Prompts `chronicle_summary(circle, since, until)` und `whats_open(circle)`:
  sie formulieren einen Auftrag an den Client und nennen die Werkzeuge; sie
  enthalten selbst keinen Inhalt.
- Beide laufen durch dieselbe Prüfung und schreiben `mcp_access`.

---

## 7. Das Zugriffsprotokoll

- Jeder Aufruf schreibt ein `mcp_access` nach K §5, auch ein abgewiesener und
  ein gescheiterter, in eigener Transaktion nach dem Lesen. Ein Abbruch
  zwischen Antwort und Schreiben verliert den Eintrag; wie beim Gate ist das
  eine benannte Grenze.
- `withheld` trägt je Event `reason_code` (`no_rule` oder `rule`), die
  betroffenen Kreise und den Satz; `policy_gaps` liest `reason_code`.
- **`previously access [--client <name>] [--circle <name>] [--since …]`** liest
  das Protokoll: je Aufruf Zeit, Client, Werkzeug, gelieferte und
  zurückgehaltene Events. Es beantwortet „was hat Claude über Kunde X
  gesehen".
- Die Chronik zeigt `mcp_access` nicht (nur Wahrnehmungen, seit Einheit 3).

---

## 8. Was das für den Betrieb heißt

- **kup6s**, ein Handoff, englisch, zusammen mit dem zurückgehaltenen Handoff
  des Gates (`handoffs/2026-10-09-kup6s-gate.md`) und dem lokalen Modellserver:
  ein Deployment `previously-mcp` mit `previously serve`, ein Service, ein
  Replikat, Bereitschaft über `server/discover`; Zugang in Stufe A
  (`kubectl port-forward`) und A2 (Tailscale/Headscale, ausgearbeitet vom
  Agenten dort); die Tokens der Clients legt der Betreuer im Werkzeug-Pod an.
- **Release.** Nach dem Merge `v0.1.0a3` mit Gate und MCP-Lesezugang; die Notes
  nennen die neuen Kommandos, Variablen und dass keine Migration dazukommt.
- **docker-compose.** Ein Dienst `mcp` (`previously serve`) neben der
  Datenbank, auf `127.0.0.1` veröffentlicht.
- **Der Einfachheits-Check**: ein Prozess, ein Token je Client, keine Tabelle,
  keine Migration.

---

## 9. Schnitt im Code

| Ort | Was |
|---|---|
| `core/policy.py`, `core/decide.py` | Art `client`; die vier Felder der Zusage, die vier Einschränkungen der Regel |
| `core/access.py` | Nutzlast `mcp_access`, Schreiben, Lesen für `previously access` |
| `core/gaps.py` | Zurückhaltungen aus `mcp_access` |
| `core/action.py`, `core/verify.py` | `mcp_access` als bekannte Handlung mit Form |
| `mcp_server/server.py` | `MCPServer`, Werkzeuge, Ressourcen, Prompts, stdio und ASGI |
| `mcp_server/render.py` | Markdown, Zaun, Bereinigung, Platzhalter, Seiten |
| `mcp_server/auth.py` | `TokenVerifier` gegen die Clients |
| `cli.py` | `client`, `mcp`, `serve`, `access`, die neuen Optionen von `policy` |
| `.importlinter` | `previously.mcp_server` in der Schicht von `gate` und `connectors`; nur `mcp_server` importiert `mcp` |

Abhängigkeit: `mcp>=2.3` (und was es für ASGI braucht), mit Urteil in
`DEPENDENCIES.md` — die Recherche (R §7) liefert den Entwurf dafür.

---

## 10. Zusicherungen und Tests

Gegen echtes PostgreSQL; der Server über den In-Memory-`Client` des SDK **in
beiden Generationen** (`mode="legacy"` für die alte), dazu über HTTP gegen die
ASGI-App. Jede Zusicherung mit gemessener Mutation und grüner Kontrolle.

1. **Was die Policy zurückhält, erscheint nie** — weder Text noch Betreff noch
   Beteiligte; nur der Platzhalter mit Grund.
2. **Ohne Regel sieht ein nicht-lokaler Client nichts**, ein lokaler alles, was
   die Policy sonst erlaubt.
3. **Jeder Aufruf schreibt ein `mcp_access`**, auch ein abgewiesener; seine
   Nutzlast enthält keinen Inhalt.
4. **Ein widerrufener Client ist ab dem nächsten Aufruf ausgesperrt**; ohne
   Token 401; der Token steht nirgends im Klartext.
5. **Kein Ergebnis enthält `structuredContent`, `resource_link` oder eine Zahl
   über 2^53.**
6. **Der Begrenzer ist je Antwort zufällig**, und eine Mail, die den Begrenzer
   einer früheren Antwort enthält, bricht den Zaun nicht.
7. **Steuer- und unsichtbare Zeichen** werden bei der Ausgabe entfernt und
   gezählt; die gespeicherten Bytes bleiben unverändert (verify grün).
8. **Eine Seite bleibt unter der Grenze**; der Cursor liefert die nächste
   lückenlos und ohne Doppel.
9. **Die neuen Einschränkungen** — Training, Unterverarbeiter, Betreiber,
   Herkunft — folgen „unbekannt besteht nicht", und die Eigenschaft aus
   Einheit 3 (eine weitere Regel lockert nicht) gilt weiter (Hypothesis).
10. **Die Werkzeugliste entspricht der Prüfsumme.**
11. **Beide Generationen** liefern dieselben Ergebnisse.
12. **Was die Referenz zitiert**, wird gegen den Code gehalten.

---

## 11. Dokumentation

- **Explanation, neu: die MCP-Schnittstelle** — warum der Client ein
  Verarbeiter ist, warum ein Textblock, warum der Zaun eine Wette ist, warum das
  Zugriffsprotokoll im Log liegt; die Messungen als Beleg. Mit ihr frieren
  dieser Spec und das Konzept ein.
- **Reference, neu:** die Werkzeuge, Ressourcen und Prompts mit Argumenten und
  Ausgabe; die Nutzlast von `mcp_access`; `cli.md` (`client`, `mcp`, `serve`,
  `access`, die neuen Optionen von `policy`); `configuration.md`.
- **How-to, neu:** Claude Code und Mistral Vibe verbinden — mit der datierten
  Liste der getesteten Konfigurationen.
- **Bestehend:** `trust-boundaries.md` (MCP als Grenze), `processing-policy.md`
  (die Kette, die neuen Felder), `module-boundaries.md`.
- **Handoff** an kup6s (§8), **README**, **Landkarte**; §8 der Architektur als
  abgelöst vermerkt in `design-records.md`.

---

## 12. Abnahme

| # | Bedingung |
|---|---|
| 1 | Clients werden angelegt, abgelöst, widerrufen; der Token nur einmal ausgegeben, nur gehasht gespeichert. |
| 2 | Die Kette kennt die vier neuen Felder, die Regel die vier neuen Einschränkungen; `decide` wendet sie an. |
| 3 | `previously mcp` und `previously serve` bedienen beide Generationen; ohne gültigen Token 401. |
| 4 | Die fünf Werkzeuge, zwei Ressourcen und zwei Prompts nach §5 und §6. |
| 5 | Jeder Aufruf schreibt `mcp_access`; `previously access` liest es. |
| 6 | Jede Zusicherung aus §10 hat eine gemessene Mutation und eine grüne Kontrolle. |
| 7 | Die Dokumente aus §11 stehen. |
| 8 | Alle sechs Tore grün; `pip-audit` ohne Befund. |
| 9 | **Ein Lauf des Betreuers, nach dem Merge**, mit Claude Code **und** Mistral Vibe gegen `previously serve` mit seiner Probe-Datenbank: zwei Clients mit eigener Kette, ein Kreis mit einer Regel, die beide Ketten zulässt, ein zweiter, dessen Regel nur eine zulässt, ein dritter ohne Regel; die Frage aus K §1 an beide; danach zeigt `previously access`, was jeder Client gesehen hat und was ihm vorenthalten blieb. |

Abgenommen ist die Arbeit mit dem Merge nach `main`; Bedingung 9 folgt ihm.

---

## 13. Was offen bleibt

1. **Eine eigene Projektion für die Chronik nach Kreis**, sobald das Lesen des
   Logs zu langsam wird (§5.1); zu messen an echter Menge.
2. **Die Grenze von 60.000 Zeichen je Seite** an echten Mails nachmessen.
3. Alles aus K §10.
