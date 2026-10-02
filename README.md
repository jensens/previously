# Previously

> *Previously, on Projekt …*

Ein Werkzeug, das Verläufe, Zusagen und offene Punkte aus vielen Kanälen
zusammenträgt, einordnet und belegbar macht — damit die Frage „wie steht es
hier?" beantwortbar ist, ohne in sechs Postfächer zu schauen.

Der Name ist die Hauptansicht: Protokollkopf und Chronik eines Projekts, jede
Zeile mit Quellenangabe.

## Stand

**Spezifikation. Kein Code.** Dieses Repository enthält derzeit ausschließlich
Entwurfsdokumente. Wer lauffähige Software sucht, ist zu früh hier.

| Dokument | Inhalt |
|---|---|
| [Entwurf](docs/superpowers/specs/2026-10-01-previously-design.md) | Ziel, Leitsätze, Kernmodell, Zuordnung, Projektionen, Freigabemodell, Abnahmebedingungen |
| [Architektur](docs/superpowers/specs/2026-10-01-architektur.md) | Module und Grenzen, Schema, Konnektor-Vertrag, Prozessmodell, MCP, Werkzeuge |
| [Stufe 1a](docs/superpowers/specs/2026-10-02-stufe-1a-log.md) | Detail-Spezifikation des append-only Logs mit Hash-Kette |
| [NOTIZEN.md](NOTIZEN.md) | Gesprächsprotokoll der Entstehung, einschließlich der verworfenen Wege |

## Grundgedanke

Ein **append-only Event-Log** ist die einzige Wahrheit; jeder Zustand ist eine
daraus neu berechenbare Projektion. Fremdsysteme wie Projektverwaltungen oder
Issue-Tracker sind gleichzeitig Eingang **und** Ausgabeziel, nie Wahrheitsquelle
— damit bleiben sie austauschbar.

Drei Event-Arten tragen das Ganze: **Wahrnehmungen** können nicht falsch sein,
sie behaupten nur, dass etwas ankam. **Feststellungen** können falsch sein und
werden überschrieben, nie gelöscht. **Handlungen** sind belegt, mit der
Befugnis, auf der sie beruhen. Nur Feststellungen kommen aus einem Sprachmodell.

Die Leitsätze stehen in §3 des Entwurfs. Der wichtigste:

> Autonomie entsteht durch Einschränkung, nicht durch Vertrauen.

## Sprache

**Prosa und Begründungen deutsch, alles Technische englisch** — Bezeichner,
Schema, Werkzeugnamen. Das Glossar in §3 der Architektur ist die verbindliche
Zuordnung.

Die Dokumente sind bewusst auf Deutsch: sie enthalten mehr Begründung als
Beschreibung, und die Begründungen sind der eigentliche Inhalt.

## Was es nicht ist

- **Kein Überwachungswerkzeug.** Gesprächsmitschnitte setzen Einwilligung
  voraus, Offenlegung an Dritte setzt eine deckende Vereinbarung voraus, und
  beides ist im Modell verankert statt in einer Richtlinie.
- **Kein SaaS.** Selbst betrieben, Daten im eigenen Haus.
- **Kein KI-Produkt.** Das Sprachmodell ist austauschbares Beiwerk hinter einer
  einzigen Schnittstelle; der Kern ist ein Event-Log mit Projektionen.

## Lizenz

[AGPL-3.0-or-later](LICENSE).

Bewusst Affero: Previously ist eine Server-Anwendung, und die gewöhnliche GPL
greift nicht, wenn jemand eine geänderte Fassung als Dienst betreibt, ohne
Code herauszugeben.
