# Previously — Pilot, Einheit 5: Feststellungen

> **Eingefrorener Entwurfsbericht, Stand 2026-10-12.**
> Dieses Dokument wird nicht mehr nachgezogen.
> Es hält fest, **wie und warum** entschieden wurde, und bleibt dafür im
> Repository. Die lebende Begründung steht in der Dokumentation unter
> `docs/` — soweit sie dort steht; wo sie fehlt, ist dieses Dokument die
> einzige Quelle. Weicht es von der Doku ab, gilt die Doku.
>
> Ein neuer Spec für eine neue Stufe entsteht wieder auf Deutsch — das ist
> die Sprache, in der die Absicht formuliert wird. Er friert ein, sobald
> seine Explanation-Seiten stehen. Das Einfrieren als **Ablauf**, und die
> Karte von jedem zitierten Paragraphen zu seiner Seite, stehen in
> [About the frozen design records](../../explanation/design-records.md).

**Datum:** 2026-10-12
**Status:** eingefroren am 2026-10-12; zuvor Entwurf, aus dem Brainstorming mit
dem Betreuer am 2026-10-12, vom Betreuer am selben Tag durchgesehen („ja"),
Grundlage des Plans `docs/superpowers/plans/2026-10-12-pilot-feststellungen.md`.
Die Abnahme nach §14 folgt dem Merge. Wo der Bau vom Wortlaut abweicht, steht
es im Plan und im Ausführungsprotokoll
(`docs/superpowers/sdd/2026-10-12-pilot-feststellungen/`), an diesen Stellen:

- **Keine Projektionstabellen, keine Migration** (§9 „zwei Projektionen,
  `p_obligation` und `p_decision`", §10 „eine Migration", §11). Gelesen wird
  durch Falten aller Feststellungen aus dem Log, bei jeder Liste und jedem
  Schreiben: der Rückfall nach einer Tilgung braucht ohnehin alle Fassungen,
  die Kreise hängen an der Policy von heute, und der MCP-Server liest nur den
  Log. Vom Betreuer am 2026-10-12 vor dem Bau bestätigt („schauen wir mal, ob
  wir ohne Projektionstabellen auskommen — das kann man notfalls
  nachliefern"; Planentscheidung 1). Die Endprüfung misst die Lesezeit bei
  5 000 Feststellungen.
- **Die Form des Handles** (§6.1 „HMAC über Inhalt, Client und Ablauf"):
  `base64url(kanonisches JSON {client, digest, expires, nonce})` und, nach
  einem Punkt, `base64url(HMAC-SHA256)`; `digest` ist der SHA-256 der
  kanonischen Liste der Nutzlasten ohne `handle`, und die Kennung im Log ist
  der `nonce` (Planentscheidung 9).
- **Höchstens 20 Feststellungen je Aufruf** über MCP (§6 „mehrere Vorschläge
  gehen in einem Aufruf"), `MAX_STATEMENTS = 20`; ebenso höchstens 20
  Vorschläge je `write_approve`. Der Schreibweg selbst nimmt bis zu 500.
- **Keine Zeile über 1 000 Zeichen über MCP.** Eine Liste kürzt eine Zeile
  dort, also weisen die schreibenden Werkzeuge eine Feststellung mit längerer
  Zeile ab, statt sie gekürzt vorzuzeigen; ein Vorschlag mit längerer Zeile
  lässt sich über MCP weder freigeben noch ablehnen. Die Kommandozeile hat
  keine Grenze (Ruling F-12).
- **Eine Fassung von `model:` ist nur als Freigabe direkt** (§3.3, §6), als
  Regel der Form: der Schreibweg weist jede andere ab, und `verify` meldet
  sie. Sonst hinge „ein Vorschlag überschreibt nie eine direkte Fassung"
  allein am Werkzeug. Ablehnungen sind ausgenommen (Ruling F-6).
- **Quellen müssen Wahrnehmungen sein** (§2 „eine Quelle zeigt auf ein Event,
  das es gibt"): eine Handlung oder eine Feststellung als Quelle ließe eine
  Kaskade der Tilgung einer anderen folgen. Darum kaskadieren auch die Tilgung
  eines Blobs und ein Modellaufruf nicht auf Feststellungen (Ruling F-8).
- **Eine Quelle ohne Einheiten** (§8 „oder das ganze Event") geht mit einer
  Tilgung von Einheiten ihres Events nur, wenn die Tilgung jünger ist als die
  Feststellung: eine Einheit, die beim Schreiben schon getilgt war, ist nicht,
  worauf sie sich stützt.
- **Der feste Satz für fehlende und verborgene Quellen** (§6 „mit derselben
  Meldung wie für ein Event, das es nicht gibt") lautet `Error: event <id> is
  not one this client can use as a source`; je ein eigener fester Satz gilt
  ebenso für ein `subject`, ein `replaces` und einen Vorschlag, die es nicht
  gibt oder die der Client nicht sehen darf (`mcp-tools.md`).
- **Ein Eintrag ohne stehende Fassung erscheint nicht als getilgt** (§8
  „gibt es keine, erscheint sie als getilgt"). Er fehlt in jeder Liste, und
  eine Frage nach ihm wird beantwortet wie die nach einer Kennung, die nichts
  nennt.
- **Eine Freigabe steht, wenn ihr Vorschlag für sich getilgt wird** (§3.3,
  §8), nicht über eine Quelle: sie ist eine ganze, beim Schreiben geprüfte
  Aussage mit eigenen Quellen (Ruling F-5). Ein Eintrag behält seine Kennung,
  wenn seine erste Fassung getilgt wird und eine andere steht (Ruling F-2).
- **Kein Hinweis auf `address:` in der Vorschau über MCP** (§2.1), nur auf der
  Kommandozeile, und **kein „zuletzt geändert am"** je Eintrag einer Liste
  (§3.5); beide stehen in der Landkarte.

Die Seiten `assertions.md` (Explanation und Reference), `cli.md`,
`mcp-tools.md` und die Anleitung `record-what-is-owed-and-decided.md` tragen
den Stand, und sie gelten.

**Grundlage:** der Design-Record (`2026-10-01-previously-design.md`, §5.2
Feststellung, §5.3 Zuordnungen, §5.5 Rückkopplung, §6.2 Verpflichtung), die
Architektur (`2026-10-01-architektur.md`, §4 Projektionen), das MCP-Konzept
(`2026-10-10-mcp-schnittstelle.md`, „K", §4.2–§4.3), der Spec des
MCP-Lesezugangs (`2026-10-10-pilot-mcp-lesezugang.md`, „S"), die Landkarte
(*Feststellungen und Entitäten*), und das Prinzip „Previously demands, the
environment provides" aus `CLAUDE.md`.

---

## 1. Zweck und Zuschnitt

Einheit 5 bringt, **was festgestellt ist, mit Quelle und Verantwortung**: wer
wem was schuldet und bis wann, und was wann von wem auf welcher Grundlage
entschieden wurde. Zusammen ergibt das „Protokoll und offene Punkte", das
vierte Ziel des Piloten.

**Zugeschnitten am 2026-10-12 (Betreuer, Antwort D):** Verpflichtung und
Entscheidung kommen in dieser Einheit; die **Zuordnung** — Events zu Projekten
und Vorgängen, Quellen ohne Adressen zu einem Kreis — bekommt danach einen
eigenen Spec. Sie ist eine eigene Designfrage (die Idee „Kreis von Kreisen"
und ihre Gegenthese, Landkarte) und hätte diese Einheit zu groß gemacht. Der
Betreuer: „Das sind jetzt drei sehr wichtige Basisfeatures."

**Wer schreibt:** der Betreuer auf der Kommandozeile, und ein MCP-Client —
Claude Code — auf seine Anweisung. Eine automatische Extraktion aus dem
Eingang, mit Rückfrage im Zweifel, ist Einheit 6 (KI-Schicht hinter dem Gate);
diese Einheit baut den Weg, auf dem ihre Vorschläge später zur Freigabe kommen.

**Nicht in dieser Einheit:** das Teilen einer Verpflichtung (Design §6.2),
Aufgaben, die transitive Verantwortung (sie kommt mit Freigabeklassen),
Personen und Organisationen als Entitäten, die Zuordnungen. Alles davon steht
in §15.

---

## 2. Die Form einer Feststellung

Eine Feststellung ist ein Event der Art `assertion` — die Art kennt das Schema
seit Stufe 1a, einen Schreibweg hat sie bis jetzt nicht. Ihre Unterart steht in
der Nutzlast unter `assertion`, wie die einer Handlung unter `action`
(Landkarte: „`kind` heißt zweierlei"). Diese Einheit kennt die Unterarten
`obligation`, `decision` und `rejection` (§3.4).

Jede Feststellung trägt:

| Feld | Inhalt |
|---|---|
| `assertion` | die Unterart |
| `subject` | die Kennung der Verpflichtung oder Entscheidung, über die sie spricht (§3.1); `null` bei der ersten Fassung |
| `author` | wer formuliert hat: `human:operator` oder `model:<client>` (§6) |
| `responsibility` | wer dafür einsteht: `direct` oder `open` (§3.2) |
| `sources` | **Pflicht, nie leer:** eine Liste von Events, je mit den Einheiten, auf die sie sich stützt, oder ohne Einheiten für das ganze Event |
| `reason` | optional: warum diese Fassung, etwa „Kunde hat um Aufschub gebeten" |
| die Felder der Unterart | §4, §5 |

**Feststellungen gehen über Events hinweg.** Erst das PDF aus der Nextcloud,
die kurze Mail des Kunden und der Kommentar in GitLab zusammen ergeben eine
Feststellung (Betreuer, 2026-10-12). Darum ist `sources` eine Liste, und jede
Quelle ist gleichberechtigt — über Kanäle hinweg.

**`sources` ist Pflicht und wird erzwungen** (Design §5.2: „eine Feststellung
ohne Quellenangabe ist ein Schemafehler"): der Schreibweg weist eine
Feststellung ohne Quelle ab, und `verify` meldet eine, die trotzdem im Log
steht. Eine Quelle zeigt auf ein Event, das es gibt; eine genannte Einheit auf
eine Einheit dieses Events.

### 2.1 Verweise auf Akteure

Schuldner, Gläubiger und Entscheider sind **Verweise mit Präfix**
(Betreuer, 2026-10-12, Antwort A):

| Präfix | meint |
|---|---|
| `own` | wir, die eigene Seite |
| `circle:<name>` | einen Kunden über seinen Kreis |
| `address:<adresse>` | einen Menschen über seine Mailadresse |
| `name:<text>` | alles andere — „die Hostingfirma", „der Anbieter XY" |

- **Die Liste ist fest.** Der Verweis steht in gehashten Nutzlasten, also gilt
  seine Grammatik ab heute für immer; ein unbekanntes Präfix wird abgewiesen.
  Ein neues Präfix später (`person:`, `org:`) ist eine Änderung am Code, nicht
  an den Daten.
- **Geprüft wird die Form, nicht die Existenz.** Ein `circle:` muss heute in der
  Policy nicht stehen: eine Feststellung beschreibt die Welt und hängt nicht am
  Stand der Policy.
- **`address:` und `circle:` sind die tragfähigen Verweise**, `name:` ist der
  Notausgang — und wirklich unscharf: es gibt viele Frau Hubers (Betreuer,
  2026-10-12). Darum:
  - **`name:` ist eine Beschriftung, keine Identität.** Zwei `name:`-Verweise
    gelten nie als derselbe Akteur, auch bei gleichem Text; eine Liste sucht im
    Text, setzt die Treffer aber nicht gleich.
  - **Präzisiert wird mit einer neuen Fassung**, nicht mit einer globalen
    Zuordnung: wird die Adresse bekannt, bekommt genau diese Verpflichtung eine
    Fassung mit `address:` statt `name:`, und `reason` sagt, warum. Eine andere
    Frau Huber in einer anderen Verpflichtung bleibt unberührt.
  - **Beim Schreiben ein Hinweis, kein Verbot:** steht in einer Quelle eine
    Adresse, die zum Namen passen kann, schlagen Kommandozeile und
    MCP-Vorschau `address:` vor.
- **Erwähnt heißt nicht beteiligt.** Ein Akteur, der nur im Text einer Mail
  vorkommt, wird ein Verweis, aber er macht die Feststellung nicht zum Inhalt
  eines Kreises (§7). Schreibt er Wochen später selbst, ist die Zuordnung
  `name:Anbieter XY` → `address:office@xy.at` eine neue Fassung der
  Verpflichtung, in der er vorkommt (siehe oben).

**Warum das nichts verbaut:** Personen und Organisationen wären auch später
Projektionen über Feststellungen (Design §6), keine Wahrheitstabellen. Kommen
sie, sagt eine neue Feststellung „`address:huber@…` gehört zu `person:huber`",
und die Projektion löst den alten Verweis beim Bauen auf — ein Neubau mit
erhöhter Version, keine Migration. `circle:` braucht dann je Kreis die
Feststellung, für welche Organisation er steht, denn ein Kreis ist ein
Konstrukt der Policy, kein Kunde.

---

## 3. Fassungen, Vorrang, Freigabe

### 3.1 Vollständige Aussagen

**Jede Feststellung über eine Verpflichtung oder Entscheidung sagt alles,
was nach ihr gilt** (Betreuer, 2026-10-12: „sonst wird es unübersichtlich").
Eine Korrektur der Frist ist eine neue, vollständige Fassung. Die Alternative —
Änderungen, die nur ein Feld nennen — hätte Felder aus verschiedenen Stufen der
Verantwortung zusammengesetzt und die Schwingung, die der Design-Record (§5.5)
ausschließt, durch die Hintertür gebracht.

- Eine Verpflichtung oder Entscheidung **heißt nach dem Event ihrer ersten
  Fassung**: `previously://event/<id>`. Jede weitere Fassung nennt diese
  Kennung in `subject`.
- **Keine Markierung der Änderung.** Was sich geändert hat, ist aus dem
  Vergleich mit dem Vorgänger ableitbar; gespeichert wäre es eine zweite
  Wahrheit, die der ersten widersprechen kann. Was sich **nicht** ableiten
  lässt, ist der Grund: dafür ist `reason` da.

### 3.2 Vorrang

**Direkt schlägt offen; innerhalb derselben Stufe gewinnt die jüngste
Fassung** (Design §5.2, ohne die transitive Stufe, die diese Einheit nicht
kennt). Ein Vorschlag überschreibt nie eine direkte Fassung, auch wenn er
jünger ist.

- **Gewinner** einer Kennung ist die jüngste direkte Fassung; gibt es keine,
  die jüngste offene, die weder abgelehnt noch freigegeben ist — sie erscheint
  als **Vorschlag**.
- Offene Fassungen, die jünger sind als der direkte Gewinner und weder
  abgelehnt noch freigegeben, sind **anhängige Vorschläge**; sie werden beim
  Eintrag gezählt und gezeigt, sie gelten nicht.

### 3.3 Freigabe

**Freigeben heißt sich zu eigen machen.** Die Freigabe ist eine neue Fassung
mit dem Inhalt des Vorschlags, `responsibility: direct`, und einem Verweis auf
den Vorschlag (`approves`). Als `author` bleibt stehen, wer formuliert hat —
das Modell —, denn wer formuliert und wer einsteht, sind zwei Fragen (Design
§5.2). Die Projektion muss nichts zusammenführen.

Freigegeben wird einzeln oder als Liste, auf der Kommandozeile und über MCP
(§6).

### 3.4 Ablehnung

**Ablehnen ist eine Feststellung der Unterart `rejection`**, direkt
verantwortet, mit dem abgelehnten Vorschlag in `of`, einem optionalen
`reason`, und den Quellen des Vorschlags als ihren Quellen — so geht sie mit
ihm, wenn eine Quelle getilgt wird (§8).

Ein abgelehnter Vorschlag bleibt in der Geschichte sichtbar, aber nicht unter
den offenen Punkten. Ohne Ablehnung würde Einheit 6 denselben Vorschlag immer
wieder machen.

### 3.5 Ist-Zustand und Geschichte

**Standard ist der Ist-Zustand; die Geschichte gibt es auf Wunsch**
(Betreuer, 2026-10-12: „im Prinzip interessiert mich oft der Ist-Zustand und
nicht die Historie — vielleicht sollte man beides supporten").

- **Listen** zeigen, was gilt, und je Eintrag einen Hinweis wie „3 Fassungen,
  zuletzt geändert am 4.11." und die Zahl anhängiger Vorschläge.
- **Ein einzelner Eintrag mit Geschichte** zeigt alle Fassungen der Reihe nach,
  je mit dem Unterschied zum Vorgänger — beim Lesen berechnet —, Grund,
  Quellen und Verantwortung, Vorschläge und Ablehnungen eingeschlossen.

---

## 4. Verpflichtung

| Feld | Inhalt |
|---|---|
| `debtor` | wer schuldet: ein Verweis (§2.1) |
| `creditor` | wem: ein Verweis |
| `what` | was, als Text |
| `due` | bis wann: ein Datum, oder keins |
| `state` | `open`, `fulfilled` oder `cancelled` |

- **„Überfällig" wird nicht gespeichert**, sondern beim Lesen aus `due`,
  `state` und dem Tag berechnet.
- **Drei Fälle, nicht zwei** (Design §6.2): wir schulden; man schuldet uns;
  zwei andere schulden sich etwas, das uns betrifft. Alle drei sind dieselbe
  Form mit anderen Verweisen; eine Liste filtert danach (`own` als Schuldner,
  `own` als Gläubiger, weder noch).
- **Erfüllung ist im Piloten eine Feststellung mit Quelle** — „erfüllt, siehe
  Mail vom 3.11." —, weil kein Konnektor sie beobachten kann. Der
  Design-Record will sie beobachtet, nicht gemeldet (§5.6); das kommt mit
  einem Konnektor, der Arbeit sieht.

## 5. Entscheidung

| Feld | Inhalt |
|---|---|
| `what` | was entschieden wurde, als Text |
| `by` | wer entschieden hat: ein oder mehrere Verweise |
| `on` | wann: ein Datum |
| `state` | `valid` oder `revoked` |
| `replaces` | optional: die Kennung einer Entscheidung, die sie ablöst |

Eine Entscheidung, die eine andere ablöst, ist eine neue Entscheidung mit
`replaces`, keine Fassung der alten; die alte zeigt in der Liste, dass sie
abgelöst ist.

---

## 6. Schreibwege

| Weg | `author` | `responsibility` |
|---|---|---|
| Kommandozeile: `previously assert obligation …`, `… decision …` | `human:operator` | `direct` |
| MCP: `write_assertion` | `model:<client>` | `open` — immer ein Vorschlag |
| Freigabe: `previously approve …`, MCP `write_approve` | bleibt der des Vorschlags | `direct` |
| Ablehnung: `previously reject …`, MCP `write_reject` | wie der Weg | `direct` |

- **Kommandozeile:** der Betreiber tippt selbst; vor dem Schreiben die
  bekannte Rückfrage `write? [y/N]`, mit `--yes` ohne. Personen kennt das
  System noch nicht, also `human:operator`, bis der Identitätsgraph kommt.
- **MCP schreibt immer Vorschläge.** Der Server kann nicht wissen, ob ein
  Mensch den einzelnen Punkt gelesen hat; auch die Bestätigung in zwei
  Schritten ist ein zweiter Werkzeugaufruf des Modells. Mehrere Vorschläge
  gehen in **einem** Aufruf: eine Vorschau, eine Bestätigung.
- **Freigabe und Ablehnung über MCP gelten als direkt, weil die Umgebung
  dafür sorgt, dass der Client den Menschen fragt.** Das ist eine Forderung im
  Sinn des Prinzips aus `CLAUDE.md`: `write_approve` und `write_reject` dürfen
  im Client nicht automatisch erlaubt sein. Die Doku sagt es und nennt das
  Risiko: wer sie automatisch erlaubt, hat Freigaben ohne Blick und trägt das
  bewusst.
- **Ein Client schlägt nur über Quellen vor, die er sehen darf.** Eine Quelle,
  die die Policy ihm zurückhält, weist `write_assertion` ab — mit derselben
  Meldung wie für ein Event, das es nicht gibt, sonst verriete die Meldung,
  dass es existiert.

### 6.1 Die Bestätigung in zwei Schritten

Nach K §4.3: ein Aufruf ohne `confirm` liefert die Vorschau und ein Handle;
erst ein Aufruf mit `confirm=<handle>` schreibt.

- **Das Handle ist versiegelt** (HMAC über Inhalt, Client und Ablauf), an den
  Client gebunden und läuft nach zehn Minuten ab. Der Schlüssel ist eine neue
  Einstellung, die **nur der MCP-Server** bekommt; Rotieren macht nur offene
  Handles ungültig.
- **„Gilt einmal" braucht keinen eigenen Zustand.** Die geschriebene
  Feststellung trägt die Kennung des Handles; ein zweites Bestätigen findet
  sie und liefert dasselbe Ergebnis, ohne zu schreiben. Das ist zugleich die
  Idempotenz des Schreibwegs (§9): ein Netzfehler, nach dem der Client noch
  einmal bestätigt, schreibt nichts doppelt.

---

## 7. Lesen und Policy

**Eine Feststellung ist Inhalt der Kreise aller ihrer Quellen.** Sie trägt
deren Inhalt in eigenen Worten weiter.

Zwei Dinge sind getrennt (Betreuer, 2026-10-12, zum erwähnten Anbieter: „kann
er dann im Kreis sein vorher? eher nicht, er ist ja nicht direkt beteiligt"):

- **Wer sehen darf — die Policy — nur über die Quellen.** Beim Lesen über MCP
  entscheidet `decide` aus Einheit 3, mit den Identitäten aller Quell-Events
  zusammen als Beteiligten; damit gilt die strengste Regel unter allen
  betroffenen Kreisen. Ein Verweis auf einen Akteur gibt nichts frei und
  nimmt nichts weg.
- **Wo etwas auftaucht — der Filter — über die Quellen und die Akteure.**
  `list_obligations(circle=X)` findet eine Verpflichtung, deren Quellen Kreis
  X berühren, und auch eine, deren Schuldner oder Gläubiger `circle:X` heißt
  oder eine Adresse ist, die Mitglied von X ist. Der Filter sortiert; was die
  Policy zurückhält, bleibt ein Platzhalter.

Weiter:

- **Zurückgehalten erscheint als Platzhalter** mit Kennung und Grund, ohne
  `what`, ohne Verweise, ohne Adressen — wie bei Events (K §3.3).
- **Text und Verweise stehen im Zaun**, bereinigt wie jeder fremde Text: auch
  eine Feststellung, die ein Mensch oder ein Modell formuliert hat, ist aus
  Kundeninhalt gemacht, und eine eingeschleuste Anweisung kann über sie
  weiterwandern.
- **Das Zugriffsprotokoll** nennt jede gelieferte und zurückgehaltene
  Feststellung mit ihren Kreisen, wie heute die Events.
- **Die Kommandozeile zeigt alles**, ohne Prüfung, wie `chronicle`: wer sie
  hat, ist der Betreiber.
- **Die Chronik bleibt bei Wahrnehmungen.** Feststellungen erscheinen in ihren
  eigenen Listen, nicht im Werkzeug `previously`.

---

## 8. Tilgung

**Wird eine Quelle getilgt, wird jede Feststellung mitgetilgt, die sich auf
sie stützt** (Betreuer, 2026-10-12: „A ist das einzig Konsequente"). Das gilt

- für ein ganz getilgtes Event, und für getilgte Einheiten, wenn die
  Feststellung genau diese Einheiten nennt oder das ganze Event;
- auch, wenn sie sich auf mehrere Quellen stützt und nur eine getilgt wird;
- für Vorschläge, Freigaben und Ablehnungen gleichermaßen.

**Der Grund:** die Tilgungszusage gilt für alles, was Previously hält. Eine
Feststellung, die den Inhalt einer getilgten Mail weiterträgt, unterliefe sie
still. Übertilgen ist die sichere Richtung. **Was es kostet:** eine
Verpflichtung auf drei Mails verschwindet ganz, wenn eine getilgt wird; wer sie
behalten will, schreibt sie neu, gestützt auf die verbliebenen Quellen.

- Die Kaskade läuft **in derselben Transaktion** wie die Tilgung, wie die der
  Modellaufrufe seit Einheit 3.
- Eine Verpflichtung, deren gewinnende Fassung getilgt ist, **fällt auf die
  nächste stehende Fassung zurück**; gibt es keine, erscheint sie als getilgt.

---

## 9. Schreibweg, Prüfung, Projektionen

- **Ein zweiter Schreibweg neben `append`**, für Feststellungen, mit
  Idempotenz über die Kennung des Handles (§6.1) oder, auf der Kommandozeile,
  über die Rückfrage. Er erledigt den Punkt der Landkarte „ein zweiter
  Schreibweg neben `append` für `assertion`".
- **`verify` kennt die Form**: Pflichtfelder je Unterart, nicht leere
  Quellen, die Grammatik der Verweise, `subject`, `approves` und `of` zeigen auf
  eine Feststellung der passenden Unterart, die Zustände sind bekannte Werte.
  Das erledigt den Punkt der Landkarte „eine Feststellung ohne `sources`
  besteht".
- **Zwei Projektionen, `p_obligation` und `p_decision`**, aus dem Log neu
  baubar wie `p_chronicle` (Architektur §4). Je Kennung: die gewinnende
  Fassung, die Zahl der Fassungen, die Zahl anhängiger Vorschläge, die Kreise
  der Quellen. „Überfällig" bleibt berechnet. Die Geschichte liest aus dem
  Log, nicht aus der Projektion. Der Punkt der Landkarte, dass `p_obligation`
  die `responsibility` braucht, ist damit beantwortet: sie steht in jeder
  Fassung.

---

## 10. Was das für den Betrieb heißt

- **Eine Migration** mit den zwei Tabellen. Das Release sagt, dass
  `previously migrate` zuerst läuft; die bestehende Routine `project` zieht
  die Projektionen nach, ohne neuen Job.
- **Ein neues Geheimnis**, der Schlüssel der Handles (§6.1), nur im
  MCP-Server, nicht im Werkzeug-Pod — als Forderung auf `environment.md`.
- **Die Werkzeugliste wächst** um `list_obligations`, `list_decisions`,
  `write_assertion`, `write_approve`, `write_reject`; ihre Prüfsumme ändert
  sich, und Vibe hält eine zwischengespeicherte Liste (die How-to sagt, wie
  man sie auffrischt).
- **kup6s** bekommt einen kurzen Handoff: die Migration, das Geheimnis nur für
  `previously-mcp`, und die Forderung, dass `write_approve` und
  `write_reject` im Client nicht automatisch erlaubt sind — samt Risiko. Mit
  ihm geht die Notiz zur Ausgabezeile der Aufnahme mit mehreren Ordnern
  (PR #16).
- **docker-compose:** eine Variable mehr für den MCP-Dienst und `migrate` vor
  dem Start, wie bei jedem Release mit Migration. **Der Einfachheits-Check
  hält:** ein Prozess, keine Tabelle für Handles, kein neuer Dienst.

---

## 11. Schnitt im Code

| Ort | Was |
|---|---|
| `core/assertion.py` (neu) | Form, Verweise, Fassungen, Vorrang, Prüfung |
| ein Schreibweg in `core` | Feststellungen anhängen, idempotent |
| `core/redact.py` | die Kaskade auf Feststellungen |
| `core/verify.py` | die Form der Feststellungen |
| `core/projection/` | `p_obligation`, `p_decision` |
| `storage/`, Migration `0006` | die zwei Tabellen |
| `mcp_server/` | die fünf Werkzeuge, das Handle |
| `cli.py` | `assert`, `approve`, `reject`, `obligations`, `obligation`, `decisions`, `decision` |

Die genauen Namen und Grenzen legt der Plan fest.

---

## 12. Zusicherungen und Tests

Gegen echtes PostgreSQL; jede Zusicherung mit einem Test, der unter Mutation rot
gemessen wird, und einer grünen Kontrolle.

1. **Quellenpflicht:** ohne Quelle, mit unbekanntem Präfix oder mit einem
   `subject`, das auf nichts zeigt, wird nicht geschrieben; `verify` meldet eine
   solche Feststellung im Log.
2. **Vorrang:** ein Vorschlag überschreibt nie eine direkte Fassung, auch wenn
   er jünger ist; innerhalb einer Stufe gewinnt die jüngste (Hypothesis über
   beliebige Folgen von Fassungen).
3. **Freigabe und Ablehnung:** Freigeben macht direkt; Abgelehntes fällt aus
   den offenen Punkten und bleibt in der Geschichte.
4. **Tilgungskaskade:** ein getilgtes Event oder eine getilgte Einheit nimmt
   jede Feststellung mit, die sich darauf stützt; danach ist `verify` grün, und
   die Verpflichtung fällt auf die nächste stehende Fassung zurück.
5. **Policy:** eine Feststellung mit einer Quelle aus einem Kreis ohne Regel ist
   für einen nicht lokalen Client ein Platzhalter, ohne Text und ohne Verweise;
   ein erwähnter Akteur ändert daran nichts.
6. **Bestätigung:** ein Handle ist an den Client gebunden, läuft ab, und ein
   zweites Bestätigen schreibt nichts Neues; ein fremder Client löst es nicht
   ein.
7. **Ein Client schlägt nichts über Quellen vor, die er nicht sehen darf**, und
   die Meldung verrät nicht, ob es sie gibt.
8. **Die Werkzeugliste entspricht der Prüfsumme**, und beide Generationen des
   Protokolls liefern dieselben Ergebnisse (wie in Einheit 4).

---

## 13. Dokumentation

- **Explanation:** warum Feststellungen vollständige Fassungen sind; warum
  Verantwortung und Autor getrennt sind und der Vorrang über die
  Verantwortung läuft; warum MCP nur vorschlägt; warum die Tilgung kaskadiert;
  warum erwähnt nicht beteiligt heißt.
- **Reference:** die Form einer Feststellung je Unterart, die Verweise, die
  Kommandos, die Werkzeuge.
- **How-to:** eine Verpflichtung festhalten, Vorschläge von Claude Code
  durchgehen und freigeben, was offen ist abfragen.
- `environment.md`: das Geheimnis der Handles, und die Forderung an den Client.
- Der Handoff an kup6s (§10), die Landkarte, und dieser Spec friert ein, wenn
  seine Seiten stehen.

## 14. Abnahme

Vom Betreuer, nach dem Merge:

1. Claude Code liest die Mails eines Kunden und schlägt Verpflichtungen und
   Entscheidungen vor.
2. Der Betreuer gibt einen Teil frei — über MCP und über die Kommandozeile — und
   lehnt einen ab.
3. `list_obligations` zeigt, was offen und was überfällig ist, und
   `--history` die Fassungen eines Eintrags.
4. Er tilgt eine Quelle; die Feststellung verschwindet mit, und `verify` bleibt
   grün.

## 15. Was offen bleibt

Gepflegt, solange der Spec lebte; beim Einfrieren am 2026-10-12 gingen die
Punkte in die Landkarte (`docs/superpowers/landkarte.md`), je unter ihre
Einheit — die Zuordnungen, die Adressbücher, der Identitätsgraph, das Teilen,
die Aufgaben, die transitive Verantwortung, die beobachtete Erfüllung und das
Umbenennen eines Kreises unter *Feststellungen und Entitäten*, die
automatische Feststellung unter *Spätere Teilprojekte* —, zusammen mit dem,
was die Ausführung offen ließ, unter *Feststellungen (Pilot, Einheit 5)*. Die
Liste hier ist der Stand dieses Tages.

- **Die Zuordnungen**, mit eigenem Spec als Nächstes: Events zu Projekten und
  Vorgängen, Quellen ohne Adressen zu einem Kreis, weitere Fundorte einer Mail.
  **Leitbeispiel des Betreuers (2026-10-12):** Robert und er sind im selben
  Verein und haben beide eine Firma; sie schreiben sich über die
  Firmenadressen zu Themen des Vereins. Die Organisation folgt also nicht aus
  der Adresse, sondern aus dem Thema — eine Zuordnung hängt am Inhalt, als
  Feststellung über Events, nicht an der Identität. Das stützt die Gegenthese
  zu „Projekte sind Mengenlehre über Identitäten".
- **Adressbücher als Quelle, 1..n, in beide Richtungen** (Betreuer,
  2026-10-12): Kontakte etwa aus der Nextcloud lesen ist ein Konnektor,
  Kontakte werden Wahrnehmungen; neue Adressdaten aus Mails von Neukunden
  zurückschreiben ist eine Handlung in einem Fremdsystem, mit Befugnis.
- **Der Identitätsgraph:** Personen und Organisationen als Projektionen,
  Zuordnungen tragfähiger Verweise (`address:` → `person:`), `circle:` →
  Organisation, und wer `human:operator` ist. `name:` gehört nicht dazu: es
  wird je Verpflichtung durch eine neue Fassung präzisiert (§2.1). **Mit dem
  Graphen fragt das System zurück** (Betreuer, 2026-10-12): ein `name:`, den es
  keiner Person zuordnen kann, wird eine Rückfrage — „welche Frau Huber ist in
  Verpflichtung 42 gemeint?" —, mit den Kandidaten aus dem Graphen, die einen
  Bezug zu den Kreisen der Quellen haben; die Antwort ist eine neue, direkte
  Fassung mit dem richtigen Verweis (`list_triage`, `write_triage_answer`,
  K §4.2–§4.3).
- **Automatische Feststellung mit Rückfrage** — Einheit 6: sie muss Inhalt,
  Organisation und in Folge Projekt herausfinden und im Zweifel fragen
  (`list_triage`, `write_triage_answer`, K §4.2–§4.3).
- Das **Teilen** einer Verpflichtung, **Aufgaben**, die **transitive**
  Verantwortung mit Freigabeklassen, die **beobachtete** Erfüllung.
- Ob ein Kreis umbenannt werden kann, ohne dass `circle:`-Verweise ins Leere
  zeigen.
