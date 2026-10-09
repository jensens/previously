# Previously — Pilot, Einheit 3: Gate und Policy

**Datum:** 2026-10-09
**Status:** Entwurf, vom Betreuer am 2026-10-09 durchgesehen („spec passt"),
Grundlage des Plans

Detail-Spec für die dritte Einheit des Piloten an einem echten Kunden. Setzt
die Stufen 1a, 1b, den äußeren Anker, Stufe 1c, die Auslieferung und die
Aufnahme aus IMAP voraus (auf `main` seit `009c669`, veröffentlicht als
`0.1.0a2`). Einheit 2, der Betrieb in kup6s, entsteht parallel beim Agenten
dort und ist keine Voraussetzung.

Grundlage sind das Gespräch mit dem Betreuer am 2026-10-09, die Landkarte, der
Entwurf (§7, §9.2, §10) und die Architektur (§2, §9, §12). Die Fakten zu den
Anbietern (Modelle, Preise, `inference_geo`) sind am 2026-10-09 in der
Dokumentation von Anthropic nachgesehen; was dort nicht stand, ist unten als
ungeprüft benannt.

Dieser Spec friert ein, sobald seine Explanation-Seiten stehen (`CLAUDE.md`);
seine offenen Punkte gehen dann in die Landkarte.

---

## 1. Zweck und Zuschnitt

Kein Modell hat bisher Inhalt aus dem Log gesehen. Diese Einheit baut die
Grenze, hinter der das geschehen darf: **jeder Modellaufruf des Systems geht
durch das Gate, das Gate entscheidet aus einer Policy, die im Log steht, und
jeder Aufruf — auch ein abgelehnter — wird ein Event in der Kette.**

**Lieferungen:**

1. **Das Modell der Policy** als Handlungen im Log: Kreise,
   Mitgliedschaften, Regeln, Zusagen der Anbieter, eigene Identitäten (§2).
2. **Die Entscheidung** als reine Funktion über diese Events und den Inhalt
   (§2.5).
3. **Das Gate** mit drei Adaptern — Anthropic, Mistral und ein lokales
   Modell über die OpenAI-kompatible Schnittstelle von Ollama oder
   llama.cpp — und einer ersten Aufgabe, `mail_overview` (§3).
4. **Das Audit** als Event der Art `action`, mit der Kaskade der Tilgung und
   den Prüfungen in `verify` (§4).
5. **Kommandos:** `previously policy …`, `previously policy gaps`,
   `previously gate explain`, `previously gate try` (§5).
6. **Die Dokumentation dazu**, darunter eine Seite über die Vertrauensgrenzen
   des ganzen Systems, und ein Handoff an kup6s, im selben Pull-Request
   (§9, §6).

**Nicht enthalten:**

- **Die Prüfung vor dem Schreiben nach außen** — darf dieser Inhalt in ein
  fremdes oder öffentliches System, ein GitLab, GitHub, das Jira eines
  Kunden, OpenProject? Das ist eine andere Prüfung an einer anderen Stelle
  (§1.2) und kommt mit der ersten Aktion, die nach außen schreibt.
- **Der Weg per Prompt** zu einer Regel. Er kommt mit Einheit 4: der Betreuer
  sagt es Claude Code, Claude Code ruft über MCP ein Werkzeug mit festem
  Schema, `previously` zeigt die Struktur, der Betreuer bestätigt. Diese
  Einheit baut den strukturierten Schreibweg, auf den jener aufsetzt.
- **Projekte** als Geltungsbereich einer Regel; es gibt noch keine
  Zuordnung (Einheit 5).
- **Feststellungen** (`assertion`) und ihr Schreibweg (Einheit 5). Die
  Policy braucht keinen davon (§1.2).
- **Die KI-Schicht** mit Vorschlägen (Einheit 6), die Batch API, OpenRouter.
- **Ein Modellserver in kup6s.** Der lokale Adapter wird gegen Ollama auf dem
  Rechner des Betreuers abgenommen; der Server im Cluster folgt als Handoff
  (§6).
- **Der MCP-Server** (Einheit 4). Er verwendet die Entscheidung aus §2.5
  wieder, um zu prüfen, was Claude Code sehen darf.

### 1.1 Der Rahmen des Piloten

Die Datenpolitik des Pilotkunden erlaubt, dass sein Inhalt an Anthropic geht
(Betreuer, 2026-10-04). Der Betreuer hat am 2026-10-09 dennoch zwei Anbieter
verlangt, Anthropic und Mistral, damit die Policy schon im Piloten zwischen
zwei Anbietern mit verschiedenen Zusagen wählt — eine Verifizierung mehr.

Ein lokales Modell, das in kup6s neben der Datenbank läuft, sieht nichts,
was nicht ohnehin dort liegt: seine Verarbeitung ist der von Previously
gleichwertig (Betreuer, 2026-10-09). Darauf ruht die Vorgabe „ohne Regel nur
lokal" (§2.5).

Der Betreuer wird nicht einen Posteingang je Kunde haben. Welcher Inhalt zu
wem gehört, ergibt sich deshalb aus den Beteiligten, nicht aus dem Ordner
(§2.2).

### 1.2 Was dieser Spec an früheren Festlegungen ändert

- **Zwei Prüfungen, nicht eine.** Die Landkarte gab Einheit 3 eine
  „Offenlegungsprüfung" und Einheit 4 eine „Offenlegungsprüfung davor". Der
  Entwurf trennt in §7.2 schon Verarbeitungspolitik und
  „Offenlegungsbefugnis"; der Begriff verwirrt und wird aufgegeben
  (Betreuer, 2026-10-09). Es gibt:
  - **die Verarbeitungsprüfung** — welches Modell bei welchem Anbieter in
    welchem Raum darf diesen Inhalt sehen? Gate und MCP-Server; dieser Spec;
  - **die Prüfung vor dem Schreiben nach außen** — darf dieser Inhalt in
    dieses fremde System, wo ihn jeder dort sieht? Die Aktionsschicht, später.
  Die Landkarte wird mit diesem Spec korrigiert.
- **Kreis statt Organisation.** Der Entwurf kennt in §7 ein
  `organization`-Profil. Was eine Regel bindet, ist aber jede soziale Gruppe,
  der Identitäten angehören: Kunde, Agentur, Projektverbund, Verein. Der Name
  ist **`circle`**, deutsch **Kreis** — nach Simmels Kreuzung sozialer
  Kreise: eine Identität steht in mehreren (Betreuer, 2026-10-09).
- **Haiku 5.5 statt Haiku 4.5.** Entwurf §10.2 plant Haiku 4.5 für
  Zuordnung, Zerlegung und Extraktion. Haiku 4.5 kennt `inference_geo` nicht
  — ein Aufruf mit dem Parameter wird mit 400 abgewiesen —, und damit fiele
  der Nachweis des Verarbeitungsraums pro Aufruf (Entwurf §10.1) für das
  geplante Modell aus. Seit 2026-10-07 gibt es `claude-haiku-5-5`, zu einem
  Zehntel des Preises von Haiku 4.5. Gemessen am 2026-10-09: Haiku 5.5
  nimmt `inference_geo` und `output_config.format` an; Haiku 4.5 antwortet
  auf `inference_geo` mit 400 („does not support inference_geo").
- **Kein Raum `eu` bei Anthropic.** `inference_geo` kennt `global` und `us`;
  gespeichert wird bei Anthropic in den USA, und die Workspace-Geo ist
  unveränderlich `us`. Eine Regel „nur EU" ist mit Anthropic nicht
  erfüllbar. Mistral sagt EU für Rechnung und Speicherung zu (Betreuer,
  2026-10-09; im Bau gegen Mistrals Bedingungen gehalten).
- **Die Policy steht im Log, nicht in einer Datei.** Der Entwurf lässt offen,
  wo das Profil liegt. Der Betreuer will, dass sie sich aus dem Log ergibt
  und mit einem Satz gesetzt wird (§2).
- **Die Policy ist eine Handlung, keine Feststellung.** Eine Regel ist eine
  Entscheidung des Betreibers, und Entscheidungen sind nach dem Entwurf
  Feststellungen. Die Architektur verlangt aber von **jeder** `assertion`
  eine Quelle: `evidenced_by` ist nicht optional (§4.4), `$defs.sources` hat
  `minItems: 1` (§8.6). Eine Policy hat keine Quelle im Log; sie gilt, weil
  der Betreiber sie setzt. Als `assertion` müsste diese Einheit eine Ausnahme
  von der Quellenpflicht festschreiben, bevor Einheit 5 die Feststellungen
  entworfen hat. Eine Policy zu setzen ist deshalb eine **Handlung** des
  Betreibers, wie eine Tilgung anzuordnen, die auch einen Grund trägt und
  keinen Beleg (Betreuer, 2026-10-09). Neben `redaction` kommen zwei
  Unterarten von `action` dazu: `policy` und `model_call`.

---

## 2. Das Modell der Policy

### 2.1 Fünf Arten von Policy-Events

Jedes ist ein Event der Art `action` mit `payload.action = "policy"`, gesetzt
vom Betreuer, ohne Quellschlüssel — so wie eine Tilgung. Welche Art es ist,
steht unter `payload.policy`. Jedes trägt
den **Satz**, mit dem sie gesetzt wurde, unter `statement` — Herkunft, die
das Gate nie auswertet.

| Unterart | Schlüssel | Inhalt |
|---|---|---|
| `circle` | `name` | ein Kreis |
| `membership` | `circle`, `member` | eine Adresse (`eva.huber@kunde-xz.at`) oder eine Domain (`@kunde-xz.at`) gehört zum Kreis |
| `own_identity` | `member` | eine Adresse oder Domain des Betreibers selbst (§2.2) |
| `rule` | `scope` | ein Geltungsbereich bekommt Auflagen (§2.3) |
| `provider` | `provider` | was ein Anbieterkonto zusagt (§2.4) |

**Ein neueres Event mit demselben Schlüssel löst das ältere ab.** Ein
Widerruf ist ebenfalls ein Event derselben Unterart, mit `revoked: true`.
Das ältere bleibt in der Kette: welche Policy am 12. Oktober galt, liest man
aus dem Log bis zu jenem Tag. Eine Tilgung eines Policy-Events (Stufe 1c)
wirkt wie ein Widerruf: es gilt die vorige Fassung, oder keine.

Policy-Events sind keine Kundeninhalte und haben keine Einheiten; der Satz
steht in der Nutzlast.

### 2.2 Wer beteiligt ist

Ein Inhalt gehört zu **jedem Kreis, dessen Mitglied unter seinen Beteiligten
ist.** Beteiligte sind die `channel_identities` des Events (seit Einheit 1).

- **Eine Mitgliedschaft wird gesetzt, nicht erraten.** Eine Adresse oder eine
  Domain, ausdrücklich. Das ist eine Setzung des Betreibers, keine
  Deutung; den Identitätsgraphen (Teilprojekt 7) braucht es dafür nicht.
- **Verglichen wird die Domain ohne Rücksicht auf Groß- und
  Kleinschreibung**, der lokale Teil genau so, wie er steht — Domains sind
  nach RFC 5321 unabhängig von der Schreibung, lokale Teile nicht.
- **Die eigenen Identitäten zählen nicht.** Der Betreiber steht in fast jeder
  Mail; zählte er mit, fiele jede Mail unter die Regeln jedes Kreises, mit
  dem er arbeitet. Was als `own_identity` gesetzt ist, wird vor der
  Auflösung entfernt.
- **Unbekannte Beteiligte binden nicht.** Eine Adresse, die keinem Kreis
  angehört, trägt keine Auflage bei. Gilt für ihren Inhalt auch keine Regel
  der Quelle, greift die Vorgabe „nur lokal" (§2.5), und der Rückfall wird
  sichtbar (§2.6). Gilt eine Regel der Quelle, etwa „`source:email`
  überall", geht der Inhalt nach ihr hinaus. Das ist eine Grenze, und die
  Dokumentation nennt sie (§9): wer einen Kreis nicht anlegt, schützt ihn
  nur so weit, wie die Regel der Quelle reicht.

### 2.3 Regeln

Eine Regel hat einen **Geltungsbereich** und **Auflagen**.

| Geltungsbereich | heißt |
|---|---|
| `circle:<name>` | jeder Inhalt, an dem ein Mitglied des Kreises beteiligt ist |
| `source:<source>` | jeder Inhalt dieser Quelle, z. B. `source:email` |

`project:<name>` ist vorgesehen und wird mit Einheit 5 wirksam; bis dahin
weist der Schreibweg ihn ab.

| Auflage | Werte | Vorgabe |
|---|---|---|
| `regions` | Menge aus `eu`, `us`, oder `any` | — (Pflicht) |
| `max_retention_days` | ganze Zahl ≥ 0; `0` heißt Zero Retention | keine Grenze |
| `excluded_providers` | Menge von Anbieternamen | leer |

`regions` gilt für **Rechnung und Speicherung** zugleich (§2.4).

### 2.4 Zusagen der Anbieter

Was ein Anbieter tut, meldet er pro Aufruf höchstens zum Teil: Anthropic
meldet den Raum der Rechnung in `usage.inference_geo`, Mistral nichts.
Aufbewahrung und Speicherort sind Zusagen aus Konto und Vertrag. Deshalb
**deklariert** der Betreiber sie:

| Feld | heißt |
|---|---|
| `inference` | die wählbaren Räume der Rechnung und was jeder bedeutet, z. B. `global` → überall, `us` → `us` |
| `storage` | wo der Anbieter speichert |
| `retention_days` | wie lange; `null` heißt unbekannt |
| `reports_inference_geo` | ob die Antwort den Raum meldet |
| `local` | ob der Anbieter auf Hardware läuft, die der Betreiber selbst betreibt, im selben Vertrauensbereich wie die Datenbank |

Für den Piloten, Stand 2026-10-09:

| | `inference` | `storage` | `retention_days` | meldet |
|---|---|---|---|---|
| `anthropic` | `global` → überall, `us` → `us` | `us` | 30 (Konsole: „Organization default", vom Betreuer abgelesen) | ja |
| `mistral` | `eu` | `eu` | unbekannt; Training abbestellt | nein |
| `local` (Ollama) | `eu`, der Standort der Hardware | keine | 0 | nein |

`local` ist die einzige Zusage, die der Betreiber nicht einem Vertrag
entnimmt, sondern selbst verantwortet: er betreibt die Hardware. Sie ist
deshalb an eine Adresse gebunden, die er setzt (§3.3), und steht wie jede
Zusage im Log.

Eine Zusage löst die vorige ab, sobald sich etwas ändert — etwa wenn Zero
Retention bei einem Anbieter vereinbart wird.

### 2.5 Die Entscheidung

Eine reine Funktion: Policy-Events bis zu einem Zeitpunkt, das Event, die
Aufgabe → Entscheidung. Keine Tabelle; sie wird bei jedem Aufruf aus dem Log
gelesen. Es sind wenige Events.

1. **Kreise bestimmen:** Beteiligte des Events ohne eigene Identitäten,
   gegen die Mitgliedschaften.
2. **Regeln sammeln:** jede Regel für einen dieser Kreise, und die Regel für
   die Quelle des Events.
3. **Fehlt eine Regel, gilt „nur lokal".** Ein beteiligter Kreis ohne
   Regel trägt die eingebaute Regel `local_only` bei — nur Anbieter mit
   `local` —, und dieselbe gilt, wenn überhaupt keine Regel gilt. Außer Haus
   geht nur, was ausdrücklich erlaubt ist. Die eingebaute Regel steht in
   `policy show`, damit niemand eine stille Vorgabe suchen muss.
4. **Zusammenführen, die strengste gewinnt** (Leitsatz 8): `regions` als
   Schnitt, `max_retention_days` als Minimum, `excluded_providers` als
   Vereinigung, `local_only`, sobald eine Regel es verlangt.
5. **Kandidaten:** die Modelle der Aufgabe in ihrer Reihenfolge (§3.1). Ein
   Kandidat besteht, wenn sein Anbieter nicht ausgeschlossen ist, unter
   `local_only` `local` ist, sein `storage` in `regions` liegt oder er
   nichts speichert, `retention_days` bekannt und höchstens
   `max_retention_days` ist (sofern eine Grenze gilt), und eine wählbare
   `inference` ganz in `regions` liegt. **Das Gate setzt den Raum, den die
   Regeln verlangen, und keinen engeren:** `us` nur, wenn `regions` auf
   `us` beschränkt ist, sonst `global`. Eine Rangfolge zwischen Räumen gibt
   es nicht — aus Sicht der EU liegen `global` und `us` beide außerhalb
   (Betreuer, 2026-10-09); `us` ohne Not zu setzen kostete bei Anthropic nur
   das 1,1-Fache.
6. **Der erste Kandidat gewinnt.** Besteht keiner: ablehnen, mit dem Grund
   je Kandidat — unter `local_only` ohne deklarierten lokalen Anbieter heißt
   der Grund „kein lokaler Anbieter".

Die Entscheidung trägt, was sie getragen hat: die Kreise, die Ids der
Regeln und Zusagen, die zusammengeführten Auflagen, den gewählten Anbieter,
Modell und Raum, oder den Grund der Ablehnung — und den Rückfall (§2.6).

### 2.6 Der Rückfall wird sichtbar

„Nur lokal" ist sicher, aber ein lokales Modell auf CPU ist schwächer. Die
Gefahr ist, dass der Rückfall unbemerkt bleibt und die Qualität still
sinkt (Betreuer, 2026-10-09). Er wird deshalb an drei Stellen sichtbar:

1. **Im Event.** Ein `model_call`, unter dem die eingebaute Regel gewirkt
   hat, trägt `policy.fallback`, etwa `{"reason": "no_rule", "circles":
   ["xz"]}`, oder mit leerer Liste, wenn gar keine Regel galt. Das ist kein
   Alarm — nichts ist schiefgelaufen —, sondern eine eigene Markierung: das
   Ergebnis ist schwächer, als es sein müsste.
2. **Beim Aufruf.** `gate explain` und `gate try` sagen es auf stderr, mit
   dem Kommando, das es behebt.
3. **Über die Zeit.** `previously policy gaps [--since …]` listet die Kreise
   und Quellen, deren Aufrufe zurückgefallen sind, mit Anzahl und letztem
   Datum — eine Leseabfrage über die `model_call`-Events, ohne Tabelle. Läufe
   der KI-Schicht (Einheit 6) sieht niemand einzeln; diese Liste schon. Der
   MCP-Server kann sie Claude Code zeigen, ein CronJob sie melden.

---

## 3. Das Gate

### 3.1 Eine Aufgabe

Eine Aufgabe ist **Code**, versioniert:

- `name`, `version`;
- eine **Prompt-Vorlage**, aus der mit dem Inhalt der Prompt wird;
- ein **Ausgabeschema**, JSON Schema;
- eine **geordnete Liste von Modellen**: Anbieter, Modell-Id, Aufwand.
  Modell-Ids sind festgenagelte Fassungen, keine Aliase wie `…-latest`, damit
  ein Audit-Event sagt, was wirklich gerechnet hat.

Der Aufrufer sagt *was* — Aufgabe und Event —, nie *womit*. Die Reihenfolge
der Liste ist eine Behauptung der Aufgabe über das passendste Modell, keine
Messung; sie lässt sich später begründen und ändern, ohne dass die Policy
etwas merkt (§11).

**Die erste Aufgabe: `mail_overview`.** Eingabe sind die Einheiten eines
Events. Ausgabe:

```json
{
  "language": "de",
  "topic": "Angebot für den Relaunch, neuer Zeitplan angenommen",
  "participants": ["Eva Huber", "Max Gruber"]
}
```

`language` als Sprachkennung nach BCP 47, `topic` ein Satz, `participants`
die im Text genannten Personen. Modelle: zuerst `claude-haiku-5-5` mit
Aufwand `low`, dann ein Modell von Mistral, dann ein lokales; die beiden
letzten legt der Plan fest, nachdem er gemessen hat, ob sie die Ausgabe mit
Schema zuverlässig liefern — das lokale auf CPU, in einer Zeit, die für eine
Mail tragbar ist.

Sie ist eine Probe, keine Funktion des Systems: sie lässt Policy, Adapter,
Audit und den Nachweis des Raums einmal ganz durchlaufen. Ihr Ergebnis wird
nicht als Feststellung verwendet.

### 3.2 Ablauf eines Aufrufs

1. Das Event und seine Einheiten lesen.
2. Entscheiden (§2.5).
3. **Abgelehnt:** ein `model_call` mit `outcome: denied` schreiben. Fertig.
4. Den Prompt bauen, den Adapter aufrufen, **den Raum immer ausdrücklich
   setzen**, auch wenn er `global` ist.
5. Die Antwort gegen das Ausgabeschema prüfen.
6. Den `model_call` schreiben (§4.1): Metadaten in die Nutzlast, das
   geprüfte Ergebnis in die Einheiten.
7. **Weicht der gemeldete Raum ab** — verlangt `us`, gemeldet etwas
   anderes —, steht `geo_mismatch` unter `alarms`, und das Kommando sagt es
   auf stderr.

Scheitert der Aufruf nach der Entscheidung — Netz, Zeitüberschreitung,
Ablehnung durch das Modell (`stop_reason: refusal`), Ausgabe gegen das
Schema —, wird das ebenfalls ein `model_call`, mit `outcome` `error`,
`refused` oder `schema_invalid` und ohne Einheiten. Ein Aufruf, der stattfand,
steht immer im Log.

Das Event wird nach dem Aufruf geschrieben. Bricht der Prozess zwischen
Antwort und Schreiben ab, fehlt ein bezahlter Aufruf im Audit; das ist eine
Grenze, und sie steht in der Dokumentation. Ein Event *vor* dem Aufruf
würde sie schließen und kostet ein zweites Event je Aufruf; der Pilot nimmt
sie hin (§11).

### 3.3 Adapter

Eine schmale Schnittstelle, die ein dritter Adapter ohne Umbau nutzen kann:

- **hinein:** Modell-Id, Aufwand, System- und Nutzerteil des Prompts,
  Ausgabeschema, Raum oder keiner;
- **heraus:** die Ausgabe als JSON, der gemeldete Raum oder keiner, der
  Verbrauch, die Request-Id, der Stoppgrund.

**Anthropic** über das offizielle SDK, mit `output_config.format` für die
Ausgabe mit Schema und `inference_geo`. **Mistral** über einen Client, den
der Plan wählt und nach `CLAUDE.md` auf Pflege prüft; die Ausgabe mit Schema
über Mistrals eigenes Merkmal, sofern es eine erzwingt — sonst prüft nur das
Gate, und der Spec-Abschnitt wird nachgezogen.

**Lokal** über die OpenAI-kompatible Schnittstelle, die Ollama und
llama.cpp beide anbieten, an einer Adresse, die `PREVIOUSLY_LOCAL_MODEL_URL`
setzt; die Ausgabe mit Schema über das Merkmal des Servers, im Plan an
Ollama gemessen. Kein gemeldeter Raum, keine Kosten.

Das Gate prüft jede Ausgabe selbst gegen das Schema, auch wenn der Anbieter
sie erzwingt: Leitsatz 1 hängt nicht an einer Zusage.

### 3.4 Kosten

Eine **Preisdatei** im TOML-Format, mit dem Datum, an dem die Preise
abgelesen wurden, und je Modell Eingabe und Ausgabe je Million Tokens sowie
den Aufschlag für einen Raum. Eine Vorgabe liegt im Paket; eine eigene gibt
`PREVIOUSLY_PRICES` an. TOML, nicht YAML: Python liest es mit `tomllib` aus
der Standardbibliothek, ohne neue Abhängigkeit.

Jeder `model_call` trägt den SHA-256 der Preisdatei und den errechneten
Betrag, **als Schätzung**: maßgeblich ist die Rechnung des Anbieters. Fehlt
ein Modell in der Datei, steht `cost_usd: null`; der Aufruf scheitert daran
nicht.

---

## 4. Das Audit

### 4.1 `model_call`

Ein Event der Art `action`, `payload.action = "model_call"`, ohne
Quellschlüssel. Zwei Aufrufe sind zwei Events, auch über dasselbe Event mit
derselben Aufgabe: es fanden zwei statt.

```
payload
{
  "action": "model_call",
  "task":    {"name": "mail_overview", "version": 1,
              "prompt_sha256": "…", "schema_sha256": "…"},
  "inputs":  [{"event": 42, "units": [1, 2, 3, 4], "blobs": []}],
  "policy":  {"circles": ["xz"], "rules": [17, 19], "providers": [12, 13],
              "regions": ["any"], "max_retention_days": null,
              "decision": "allowed", "provider": "anthropic",
              "model": "claude-haiku-5-5", "inference_geo": "global",
              "fallback": null, "reason": "…"},
  "response": {"request_id": "req_…", "model": "claude-haiku-5-5",
               "inference_geo": "global", "stop_reason": "end_turn",
               "usage": {"input_tokens": 1830, "output_tokens": 212},
               "cost_usd": "0.000289", "prices_sha256": "…"},
  "outcome": "ok",
  "alarms":  []
}
units
  1  {"language": "de", "topic": "…", "participants": ["…"]}
```

- **Die Nutzlast enthält keinen Inhalt:** Ids, Hashes, Zahlen, Namen. Darum
  steht dort der Hash der Prompt-Vorlage, nicht der Prompt — der enthielte
  die Mail.
- **Das Ergebnis steht in den Einheiten**, als kanonisches JSON in einer
  Einheit.
- `policy.fallback` ist `null`, wo eine echte Regel galt, sonst der Grund
  des Rückfalls (§2.6).
- `response` fehlt bei `denied`; `response.inference_geo` ist `null`, wo der
  Anbieter nichts meldet. **Bei `global` meldet Anthropic `global` zurück**,
  die Klasse der Weiterleitung, nicht den Ort der Rechnung (gemessen am
  2026-10-09). Belegt ist ein Raum also nur, wo einer verlangt war — genau
  dort, wo der Alarm (§3.2) greift. Zusage und Meldung bleiben getrennt: was zugesagt
  war, sagen die Ids unter `policy.providers`.
- `cost_usd` ist eine Zeichenkette mit Dezimalzahl: die Kette lässt keine
  Gleitkommazahlen zu (Architektur §4.1).

### 4.2 Tilgung

Wird ein Event getilgt, das ein `model_call` gelesen hat — es steht unter
`inputs` —, **tilgt `redact` in derselben Transaktion die Einheiten dieses
`model_call`**, also das Ergebnis. Die Nutzlast bleibt: sie belegt weiter,
dass ein Aufruf stattfand, mit welchem Modell, wo und zu welchen Kosten,
und enthält nichts vom Inhalt.

Dasselbe gilt, wenn nur Einheiten der Quelle getilgt werden, die der Aufruf
gelesen hat, oder ein Blob, den er gelesen hat. Die Tilgung von Einheiten
aus Stufe 1c trägt das; neu ist nur die Kaskade. `redact` nennt die
mitgetilgten Aufrufe in seiner Ausgabe, so wie heute einen Blob, den ein
anderes Event noch benutzt.

### 4.3 `verify`

Zwei neue Prüfungen:

1. **Die Kaskade ist vollständig:** kein `model_call` hat Einheiten mit
   Inhalt, wenn etwas, das er unter `inputs` liest, getilgt ist.
2. **Die Form stimmt:** ein `model_call` hat eine lesbare Nutzlast; Einheiten
   genau bei `outcome: ok`; ein Policy-Event hat seine Art unter
   `payload.policy` und deren Schlüssel, und keine Einheiten.

`verify` verlangt seit Stufe 1c von jeder Handlung einen Namen und prüft die
Form nur bei `redaction`; jeder andere Name besteht still. `policy` und
`model_call` kommen als bekannte Unterarten mit ihren Regeln dazu, und **eine
Handlung mit unbekanntem Namen wird ein Befund**: mit drei Unterarten, die
das System selbst schreibt, ist ein fremder Name ein Schreibfehler oder eine
Fälschung, keine Erweiterung.

### 4.4 Projektionen

**Die Chronik zeigt nur Events der Art `observation`.** Heute zeigt sie jedes
Event mit Einheiten; ein `model_call` hat welche und erschiene als Geschehen
beim Kunden. Die Änderung ist eine neue Version der Projektion, mit
Neuaufbau (Stufe 1b). `p_source_stats` zählt weiter alles nach Quelle; die
neuen Events haben keine Quelle.

---

## 5. Kommandos

- **`previously policy circle <name> --statement "…"`**, **`policy member
  <circle> <address-or-@domain> --statement "…"`**, **`policy own
  <address-or-@domain> --statement "…"`**, **`policy rule <scope> --regions …
  [--max-retention-days N] [--exclude-provider P …] --statement "…"`**,
  **`policy provider <name> --inference … --storage … --retention-days N|unknown
  [--reports-geo] --statement "…"`**, jeweils mit **`--revoke`**. Jedes
  zeigt die strukturierte Fassung und schreibt erst nach Bestätigung;
  `--yes` überspringt die Frage für Skripte.
- **`previously policy show [--at <zeit>]`** — die geltende Policy, als
  Tabelle, die eingebaute Regel `local_only` eingeschlossen.
- **`previously policy gaps [--since <zeit>]`** — wo die Vorgabe „nur
  lokal" gewirkt hat (§2.6).
- **`previously gate explain <event>`** — die Entscheidung für
  `mail_overview` über dieses Event, **ohne Aufruf**: Kreise, Regeln,
  Auflagen, jeder Kandidat mit Grund, die Wahl. Kostet nichts und schreibt
  nichts.
- **`previously gate try <event>`** — die Aufgabe ausführen; gibt Ergebnis,
  Entscheidung und die Id des `model_call` aus.

Rückgabewerte wie bisher: 0 bei Erfolg, 2 bei einem benannten Fehler mit
einem Satz auf stderr. Für `gate try` ist eine Ablehnung ein benannter
Fehler (2), ein Alarm bei sonst gelungenem Aufruf gibt 3, damit ein Skript
ihn nicht überliest.

---

## 6. Was das für den Betrieb heißt

- **kup6s.** Ein kleiner Handoff, englisch:
  - zwei Secrets im Werkzeug-Pod, `ANTHROPIC_API_KEY` und `MISTRAL_API_KEY`;
  - Netz nach außen: die beiden API-Hosts auf Port 443;
  - wahlweise die Preisdatei als ConfigMap, über `PREVIOUSLY_PRICES`;
  - kein CronJob: `gate try` stößt man von Hand an. Die erste Policy setzt
    der Betreuer im Werkzeug-Pod;
  - **danach, als eigener Handoff:** ein Modellserver (Ollama oder
    llama.cpp) im Cluster, nur von innen erreichbar, mit einem kleinen
    Modell auf CPU, und `PREVIOUSLY_LOCAL_MODEL_URL` im Werkzeug-Pod. Bis er
    steht, lehnt das Gate im Cluster ab, wo die Vorgabe „nur lokal" greift.
- **Ein Host mit `docker-compose`.** Drei Umgebungsvariablen, wahlweise eine
  Datei, und ein Dienst `ollama` neben der Datenbank. Keine Tabelle, keine
  Migration, kein Zeitgeber.
- **Die Schlüssel erscheinen nirgends:** nicht im Event, nicht in einer
  Fehlermeldung.
- **Die Aufbewahrung beim Anbieter gehört zur Tilgungszusage.** Was an
  Anthropic ging, liegt dort 30 Tage; eine Tilgung in Previously erreicht
  diese Kopie nicht. Die Seite zur Tilgung und die zu den Vertrauensgrenzen
  sagen es.
- **Der Einfachheits-Check** fällt gut aus: keine neue Tabelle, keine
  Migration; neu sind zwei Geheimnisse, zwei Hosts nach außen und ein
  Modellserver, den man auch weglassen kann — dann lehnt das Gate ab, statt
  lokal zu rechnen.

---

## 7. Schnitt im Code

### 7.1 Module

| Ort | Was |
|---|---|
| `core/policy.py` | die Policy-Events lesen und prüfen, die Entscheidung als reine Funktion |
| `core/policy_write.py` | der Schreibweg für die Policy-Events aus §2.1 |
| `core/redact.py` | die Kaskade (§4.2) |
| `core/verify.py` | die Prüfungen aus §4.3 |
| `core/projection/chronicle.py` | nur `observation` (§4.4) |
| `gate/task.py`, `gate/tasks/mail_overview.py` | Aufgabe, Vorlage, Schema |
| `gate/gate.py` | der Ablauf (§3.2), das Schreiben des `model_call` |
| `gate/adapters/anthropic.py`, `gate/adapters/mistral.py`, `gate/adapters/local.py` | die Adapter |
| `gate/prices.py`, `gate/prices.toml` | Preisdatei und Schätzung |
| `cli.py` | die Kommandos |

### 7.2 Grenzen

Ein neues Modul `previously.gate`, über `core` und unter `cli`, neben
`connectors`. **Nur `gate` importiert die Clients der Anbieter**; die
Verträge im `import-linter` zählen die Ausnahme namentlich auf. Die
Entscheidung liegt in `core`, nicht in `gate`, weil der MCP-Server sie
wiederverwendet und ein Modell dafür nicht gebraucht wird.

### 7.3 Abhängigkeiten

- **`anthropic`**, das offizielle SDK.
- **Ein Client für Mistral**, im Plan gewählt; Kandidat ist das offizielle
  `mistralai`.
- **Ein Client für die OpenAI-kompatible Schnittstelle** des lokalen
  Servers; Kandidat ist `openai`, den die Verträge im `import-linter` heute
  schon außerhalb von `gate` verbieten. Ob Mistral über denselben Client
  geht, entscheidet der Plan.
- **Ein Prüfer für JSON Schema** — Pydantic (Architektur §10.1, bisher
  zurückgestellt) oder `jsonschema`; Wahl im Plan.

Jede mit Urteil, Datum und Beleg in `DEPENDENCIES.md`.

---

## 8. Zusicherungen und Tests

Jede Zusicherung bekommt einen Test, gemessen rot, wenn sie zurückgenommen
wird, mit einer grünen Kontrolle. Gegen echtes PostgreSQL im Container.

**Die Anbieter im Test.** CI hat keine Secrets, und ein echter Aufruf kostet
Geld. Wie GreenMail für IMAP steht deshalb ein **Testserver**, der die
Messages-API von Anthropic und die Chat-API von Mistral auf HTTP-Ebene
beantwortet, mit festgelegten Antworten; die echten Clients reden über eine
umgelenkte Basis-URL mit ihm. Ein echter Aufruf ist Sache der Abnahme (§10).

1. **Ohne Regel nur lokal**; ohne lokalen Anbieter abgelehnt, mit Grund.
2. **Ein beteiligter Kreis ohne Regel: nur lokal**, auch wenn für einen
   anderen beteiligten Kreis „überall" gilt.
3. **Die strengste gewinnt:** eine zusätzliche Regel macht eine Entscheidung
   nie lockerer (Hypothesis) — außer sie gibt einem beteiligten Kreis seine
   erste Regel: die hebt die eingebaute `local_only` auf, und das ist ihr
   Zweck.
4. **Eigene Identitäten zählen nicht.**
5. **„EU" führt zu Mistral, „überall" zu Anthropic mit `global`, „us" zu
   Anthropic mit `us`.**
6. **Unbekannte Aufbewahrung besteht keine Grenze.**
7. **Der Rückfall ist markiert** — im Event, auf stderr, in `policy gaps` —,
   und ein Aufruf unter einer echten Regel trägt keine Markierung.
8. **Ein neueres Policy-Event löst das ältere ab; ein Widerruf hebt auf;
   `--at` liest die damalige Policy.**
9. **Jeder Aufruf wird ein `model_call`**, auch abgelehnt, gescheitert, vom
   Modell verweigert oder mit falscher Ausgabe.
10. **Die Nutzlast eines `model_call` enthält keinen Inhalt** des Events, das
    er liest.
11. **Der Raum wird immer gesetzt; eine Abweichung ist ein Alarm**, mit
    Rückgabewert 3.
12. **Die Kaskade:** eine Tilgung der Quelle — Event, Einheiten, Blob — tilgt
    die Einheiten jedes `model_call`, der sie las; `verify` findet eine
    unvollständige.
13. **Die Chronik zeigt keinen `model_call` und kein Policy-Event.**
14. **Die Schlüssel erscheinen nirgends**, auch bei abgewiesener Anmeldung.
15. **Nur `gate` importiert die Clients der Anbieter** (`lint-imports`).
16. **Was die Referenz zu Kommandos und Nutzlast zitiert**, wird gegen den
    Code gehalten.

---

## 9. Dokumentation

Im selben Pull-Request, nach `plone-doc-style:author`.

- **Explanation, neu: Vertrauensgrenzen** (`trust-boundaries.md`). Jede
  Stelle, an der Inhalt das System verlässt, und wer sie bewacht: IMAP, S3,
  Sicherungen, der Anker, jetzt das Gate; MCP und das Schreiben nach außen,
  die kommen. Verweist auf die bestehenden Seiten und nennt die Lücken —
  unbekannte Beteiligte, die Aufbewahrung beim Anbieter, der Aufruf ohne
  Audit bei einem Abbruch.
- **Explanation, neu: die Verarbeitungspolicy.** Warum Verarbeitung und
  Schreiben nach außen getrennt sind; Kreise; warum die strengste Regel
  gewinnt; warum eine Zusage etwas anderes ist als eine Meldung; warum ohne
  Regel abgelehnt wird; warum das Audit im Log liegt und das Ergebnis in den
  Einheiten.
- **Reference:** die Policy-Events und die Nutzlast von `model_call`;
  `cli.md` (die Kommandos), `configuration.md` (die beiden Schlüssel,
  `PREVIOUSLY_PRICES`).
- **How-to, neu:** eine Policy setzen und einen Aufruf prüfen.
- **Explanation, bestehend:** `erasure.md` (die Kaskade, die Aufbewahrung
  beim Anbieter), `projections.md` (die Chronik zeigt Wahrnehmungen),
  `module-boundaries.md` (`gate`).
- **Handoff** an kup6s (§6), englisch. **README** und **Landkarte.**

---

## 10. Abnahme

| # | Bedingung |
|---|---|
| 1 | Die fünf Arten aus §2.1 werden als `action` mit `policy` geschrieben, abgelöst und widerrufen; `policy show --at` liest die damalige Policy. |
| 2 | Die Entscheidung folgt §2.5; jeder Fall aus §8 Punkt 1–8 hat einen Test. |
| 3 | Jeder Aufruf und jede Ablehnung wird ein `model_call` nach §4.1; die Nutzlast enthält keinen Inhalt. |
| 4 | Die Kaskade tilgt das Ergebnis mit der Quelle; `verify` findet eine unvollständige. |
| 5 | Die Chronik zeigt nur Wahrnehmungen. |
| 6 | Nur `gate` importiert die Clients; die Schlüssel erscheinen nirgends. |
| 7 | Jede Zusicherung aus §8 hat eine gemessene Mutation und eine grüne Kontrolle. |
| 8 | Die Dokumente aus §9 stehen. |
| 9 | Alle sechs Tore grün; `pip-audit` ohne Befund. |
| 10 | **Ein Lauf des Betreuers, lokal, gegen die echten APIs**, nach dem Merge: zwei Zusagen, ein Kreis mit einer Mitgliedschaft, eine eigene Identität; Regel „überall" → `gate explain` und `gate try` wählen Anthropic, `response.inference_geo` steht im Event; Regel auf „EU" geändert → Mistral, ohne gemeldeten Raum; Regel
widerrufen → das lokale Modell über Ollama, mit Warnung, und `policy gaps`
nennt den Kreis; die Quelle getilgt → die Einheiten des `model_call` sind leer, `verify` grün. Danach Probe-Log verwerfen. |

Abgenommen ist die Arbeit mit dem Merge nach `main`; Bedingung 10 folgt ihm,
wie bei der Aufnahme.

---

## 11. Was offen bleibt

1. **Die Prüfung vor dem Schreiben nach außen** (§1.2), mit der ersten Aktion,
   die nach außen schreibt.
2. **Der Weg per Prompt** zu einer Regel, mit Einheit 4.
3. **Projekt als Geltungsbereich**, mit Einheit 5.
4. **Die Reihenfolge der Modelle einer Aufgabe** ist eine Behauptung; sie
   durch Vergleiche an echten Fällen zu begründen, etwa über OpenRouter, ist
   offen.
5. **Unbekannte Beteiligte binden nicht**, wo eine Regel der Quelle gilt
   (§2.2). Ob ein Inhalt mit Beteiligten außerhalb jedes Kreises dann
   strenger behandelt werden soll, ist offen.
6. **Der Modellserver in kup6s** (§6) und welches lokale Modell dort
   reicht.
7. **Ein Aufruf ohne Audit**, wenn der Prozess zwischen Antwort und Schreiben
   abbricht (§3.2).
8. **Zero Retention** bei Anthropic und Mistral: beantragen, dann deklarieren.
9. **Die Aufbewahrung bei Mistral** nachsehen und deklarieren.
10. **Die Batch API** für Masse, mit der KI-Schicht.
11. **Die Preisdatei** pflegt sich nicht selbst; ein veralteter Preis macht
    nur die Schätzung falsch.
