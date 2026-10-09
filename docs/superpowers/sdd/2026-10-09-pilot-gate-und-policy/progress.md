# SDD ledger — plan: docs/superpowers/plans/2026-10-09-pilot-gate-und-policy.md

Spec: docs/superpowers/specs/2026-10-09-pilot-gate-und-policy.md (Stand 62d044f).
Zweig worktree-pilot-gate, Start 78b0d85.

## Zyklenbudget (Betreuer, 2026-10-09: „die Zyklen im Griff halten")

- Je Aufgabe: umsetzen, prüfen, **höchstens eine** Fixrunde, eine Nachprüfung
  nur der Fixes (Sonnet). Was danach offen bleibt: benannt, mit Ruling geparkt,
  in die Landkarte — nicht weiter gejagt. Das ersetzt die fünf Runden des Skills.
- Befunde nach Gewicht: echte Fehler beheben; Fehlbedienung, Stil, „könnte auch":
  benennen.
- Endprüfung: eine Fixwelle, eine Nachprüfung.

## Vorprüfung (Paare mit gemeinsamer Datei oder Schnittstelle)

| Paar | erzeugt → verbraucht | Befund |
|---|---|---|
| 1↔2 | `append_action`, `POLICY`; beide `verify.py` | passt |
| 1↔5 | `append_action`, `MODEL_CALL`; beide `verify.py` | passt |
| 1↔6 | `write_action` (aus `redact._write`); beide `redact.py` | passt |
| 2↔3 | `Policy`, `Rule`, `Provider`, `Inference` | passt — aber `LOCAL_ONLY` erst in 3 definiert, `policy show` (2) zeigt es → R-1 |
| 2↔5 | `read_policy`, `Policy.ids`; beide `cli.py` | passt |
| 3↔5 | `decide`, `Candidate`, `Decision.inference_geo` → `Request.inference_geo` | passt |
| 4↔5 | `Adapter`, `Request`, `Response`, `AdapterError`; Pydantic für `Task` | Pydantic in 4 deklariert, erst in 5 importiert → R-2 |
| 5↔6 | Nutzlast `model_call.inputs` → Kaskade sucht danach | passt |

| Aufgabe | in sich | Befund |
|---|---|---|
| 1 | Tests ↔ Code ↔ Dateien | passt |
| 2 | passt | |
| 3 | „Spec §8 Punkt 1–7" | passt zur Nummerierung des Specs (Stand 62d044f) |
| 4 | passt bis auf R-2 | |
| 5 | „Spec §8 Punkt 8–11 und 13" | alte Nummerierung; Spec §8 wurde nach dem Plan umnummeriert → R-3 |
| 6 | passt | |
| 7 | passt | |

Ruling R-1: `LOCAL_ONLY` (der Name der eingebauten Regel) wohnt in `core/policy.py` (Aufgabe 2), `core/decide.py` importiert ihn — `policy show` braucht ihn vor Aufgabe 3 — kostet, wenn falsch: ein Import mehr.
Ruling R-2: `pydantic` samt ruff-Eintrag `runtime-evaluated-base-classes` und Urteil in `DEPENDENCIES.md` kommt mit Aufgabe 5, nicht 4 — eine deklarierte Abhängigkeit, die nichts importiert, ist nach CLAUDE.md eine Leiche, auch für eine Aufgabe lang — kostet, wenn falsch: nichts.
Ruling R-3: Zuordnung nach Inhalt, Spec §8 in der Fassung 62d044f: 1–7 → Aufgabe 3; 8 (Ablösen) → 2; 9, 10, 11, 14 → 5; 12 (Kaskade) → 6; 13 (Chronik) → 1; 15 (lint-imports) → 4; 16 (Referenz) → 2, 5, 7 — der Plan zählte vor der Umnummerierung — kostet, wenn falsch: ein Test fehlt, die Endprüfung findet ihn.

## Verlauf
Task 1: implementer DONE_WITH_CONCERNS (5c2e44d; 1079 passed; Mutationen rot mit grüner Kontrolle; Testblock des Tutorials aus zwei Läufen gestückelt, ein F als "." getippt).
Task 1: review — Needs fixes: Important (a) `unknown action "<name>"` fehlt in der Befundtabelle von cli.md; (b) Tutorial-Testblock von Hand gestückelt.
Ruling T1-a: Der Testblock des Tutorials wird in jeder Aufgabe, deren Testzahl sich ändert, aus **einem** vollständigen grünen Lauf neu getippt — nie gestückelt; Aufgabe 7 tippt ihn zuletzt — `test_docs_typed_output` hält `N passed` gegen den Baum, also kann keine Aufgabe ihn bis zum Ende liegen lassen — kostet, wenn falsch: ein Testlauf je Aufgabe.
Task 1: minor (deferred): test_chronicle liest Spalten über Index (r[0], r[1], r[4]).
Task 1: minor (deferred): kein eigener Test für den Retry von append_action (indirekt über redact abgedeckt).
Task 1: fix round 1/1 (4 addressed, 0 open; commits 5c2e44d..377f713)
Task 1: complete (commits 78b0d85..377f713, review clean)
Task 2: implementer DONE_WITH_CONCERNS (7c662ca; 1118 passed; drei Mutationen rot, Kontrolle grün). Einwände: redact weist jede Handlung ab; Ablehnen der Rückfrage gibt 1; RED als ImportError.
Ruling R-4: `redact` weist künftig nur Tilgungen ab (`payload.action == "redaction"`), nicht jede Handlung — der Kommentar „every action this system writes is a redaction" ist seit Aufgabe 1 falsch; ein Policy-Event muss tilgbar sein (Spec §2.1), und die Kaskade tilgt Einheiten eines `model_call` (Spec §4.2). Umgesetzt in Aufgabe 6 samt Test `redact event <policy-event>` wirkt wie Widerruf; bis dahin erzeugt der Test in Aufgabe 2 den Grabstein über `erase_payload` — kostet, wenn falsch: ein Tilgungsweg mehr, den verify mit seinen bestehenden Regeln abgleicht.
Task 2: review — Approved, drei Minor.
Task 2: minor (deferred): cli.md nennt `--regions` ohne Raum als von policy abgewiesen; argparse weist es ab (nargs="+").
Task 2: minor (deferred): test_cli `_action_count` importiert in der Funktion, `db: object` mit isinstance.
Ruling R-5: Eine Mitgliedschaft zählt in `decide` nur, wenn ihr Kreis in `Policy.circles` steht (angelegt und nicht widerrufen) — ein widerrufener Kreis hat keine Mitglieder und also keine Regel, die greift; ohne das zöge ein widerrufener Kreis über seine alten Mitglieder `local_only` nach sich — Umsetzung in Aufgabe 3 (Filter in `circles_of`), `read_policy` bleibt, wie es ist — kostet, wenn falsch: ein Inhalt eines widerrufenen Kreises geht nach der Regel der Quelle statt lokal.
Ruling T2-a: Ablehnen der Rückfrage gibt 1 mit `nothing written` — der Prüfer fand es dokumentiert und passend zu `verify`; bleibt.
Task 2: complete (commits 377f713..7c662ca, review clean)
Task 3: implementer DONE_WITH_CONCERNS (5cbdf9d; 1146 passed; vier Mutationen rot, Kontrolle grün).
Ruling R-6: Ein Anbieter mit nur einem deklarierten Raum (Mistral `eu`, lokal) bekommt `inference_geo = None` — es gibt nichts zu wählen und nichts zu setzen; was zugesagt war, steht über die Id der Zusage im Audit — kostet, wenn falsch: das Audit nennt den Raum nur indirekt.
Ruling R-7: „Nicht enger als nötig" heißt: von den wählbaren Räumen, deren Bedeutung ganz in `regions` liegt, der weiteste — `global` ({any}) vor `us`. Bei `regions = {eu, us}` besteht Anthropic mit `us`. Die wörtliche Lesart „us nur bei regions == {us}" ließ Anthropic dort durchfallen — kostet, wenn falsch: nichts, die Lesart ist die des Betreuers („setzt den Raum, den die Regeln verlangen").
Ruling R-8: Spec §8 Punkt 3 gilt nicht für eine Regel, die einem beteiligten Kreis ohne Regel die erste gibt: die hebt `local_only` auf, absichtlich. Die Hypothesis-Eigenschaft deckt jede andere Regel ab (Quelle, Kreis mit Regel, unbeteiligter Kreis), nicht nur Regeln der Quelle; der Spec-Satz wird präzisiert (Controller, Doku) — kostet, wenn falsch: nichts am Code.
Task 3: review (Opus) — Needs fixes: Important (1) Raumwahl nach der überholten Lesart, gemessen nicht monoton (Kreisregel {eu,us} + Quellregel {us} lässt Anthropic neu durch); (2) Eigenschaft nur für Quellregeln; (3) der Test überspringt „gar keine Regel", was weder R-8 noch Spec nennen; (4) zwei `pyright: ignore` in tests/test_decide.py.
Ruling R-8 (präzisiert): „Eine Regel hinzufügen" heißt eine Regel für einen Geltungsbereich, der noch keine hat; das Ersetzen einer bestehenden Regel ist kein Hinzufügen und kann lockern (`{eu}` → `{any}`), dafür gilt keine Eigenschaft. Die Eigenschaft gilt für: eine Regel der Quelle, wo schon eine Regel galt; eine Regel für einen unbeteiligten Kreis; einen weiteren beteiligten Kreis samt Regel (Mitgliedschaft und Regel). Ausgenommen, weil sie `local_only` absichtlich aufheben: die erste Regel eines beteiligten Kreises und die erste Regel, die überhaupt gilt — kostet, wenn falsch: eine Lücke in der Eigenschaft, die die Endprüfung sieht.
Task 3: minor (named, not chased): ein Anbieter mit leerer `inference`-Liste besteht nie; Grund liest sich seltsam — nur bei Fehldeklaration.
Task 3: fix round 1/1 (4 addressed, 0 open; commits 5a2fa6f..26f4cb4)
Task 3: complete (commits 7c662ca..26f4cb4, review clean)
Task 4: implementer DONE_WITH_CONCERNS (c9552f8; 1172 passed; drei Mutationen rot, zwei Probe-Tests für lint-imports; pip-audit sauber). Einwände: cli→gate fehlt noch in module-boundaries.md (Aufgabe 5); AdapterError trägt bis 200 Zeichen der Meldung des Anbieters; ModelServer schreibt Zugriffszeilen auf stderr.
Ruling R-9: Die Nutzlast eines `model_call` trägt bei `outcome: error` nie den Text einer Meldung des Anbieters — nur Anbieter, Fehlerklasse und HTTP-Status; der Satz von `AdapterError` geht nur auf stderr. Ein Anbieter, der den Prompt in seiner Fehlermeldung zurückgibt, brächte sonst Kundeninhalt in die Kette (Spec §4.1, „die Nutzlast enthält keinen Inhalt") — umgesetzt in Aufgabe 5 — kostet, wenn falsch: das Audit nennt den Fehler gröber.
Task 4: review — Approved, acht Minor. uv.lock revision 5 von uv 0.12.23 (CI) gelesen: `uv lock --check` grün.
Task 4: minor (deferred): Docstring von AdapterError sagt „kein Prompt", der Code behält bis 200 Zeichen der Meldung des Anbieters — mit R-9 in Aufgabe 5 angleichen.
Task 4: minor (deferred): Untergrenzen `anthropic>=1.13.0`, `openai>=3.27.0` dreistellig, sonst zweistellig; ungemessen.
Task 4: minor (deferred): `__all__` nur in adapters/anthropic.py.
Task 4: minor (deferred): Entfernen des Schlüssels per str.replace erfasst keine maskierte Form; echte Schlüssel URL-sicher.
Task 4: complete (commits 26f4cb4..c9552f8, review clean)
Task 5: implementer (Opus) DONE_WITH_CONCERNS (9362d0a; 1233 passed; zehn Mutationen rot, Kontrollen grün; Preise Haiku 5.5 0.10/0.50, mistral-small-2603 0.15/0.60, abgelesen 2026-10-09). Abweichungen der Schnittstellen: Task.template + render(units), Prices.surcharges, Called.reported_geo.
Ruling R-10: Dass das Anthropic-SDK `ANTHROPIC_BASE_URL` liest, bleibt — die Umgebung setzt der Betreiber, wie die Schlüssel; aber es ist eine Stelle, an der Inhalt anderswohin gehen kann, und gehört deshalb auf die Seite zu den Vertrauensgrenzen (Aufgabe 7) — kostet, wenn falsch: eine gesetzte Variable lenkt Aufrufe um, sichtbar nur in der Konfiguration.
Task 5: review (Opus) — Approved, acht Minor; die sechs benannten Risiken sauber.
Task 5: gemessen (Controller, 2026-10-09): das Pydantic-Schema von MailOverview (mit `title`, `description`) nehmen Mistral strict und Ollama/qwen3:4b an, beide Antworten bestehen `model_validate_json`; das lokale Ergebnis ist inhaltlich schwach („topic": "Email Response").
Task 5: minor (deferred): der Kein-Inhalt-Test läuft nur über `ok`; denied/refused/schema_invalid werden nicht durchsucht (R-9 hat einen eigenen Test).
Task 5: minor (deferred): NUL oder einsames Surrogat in model/request_id/stop_reason des Anbieters lässt das Schreiben nach einem bezahlten Aufruf scheitern — Landkarte.
Task 5: minor (deferred): „processed locally: …" erscheint auch bei Ablehnung und bei nicht erreichbarem lokalem Server.
Task 5: minor (deferred): ohne Quelle schlägt die Zeile `policy rule event:<id>` vor, das `policy rule` abweist (Fehlbedienung).
Task 5: minor (deferred): CLI nutzt Zeichenketten statt der Konstanten aus core.action / RULE.
Task 5: minor (deferred): `gate explain` liest die Policy zweimal in getrennten Transaktionen.
Task 5: minor (deferred): Ablehnung im OpenAI-Format (`message.refusal`) endet als schema_invalid statt refused.
Task 5: minor (deferred): zwei Tests importieren in der Funktion.
Task 5: complete (commits c9552f8..9362d0a, review clean)
Task 6: implementer DONE (8cac96f; 1249 passed; vier Mutationen rot, Kontrolle grün). Einwände: Kaskade nicht transitiv; Sperren: Ziele aufsteigend, dann model_calls aufsteigend, nicht unter Last geprüft.
Ruling R-11: Das Gate nimmt nur Events der Art `observation` als Eingabe; jede andere Art (eine Handlung, ein `model_call`, ein Policy-Event) ist `denied` mit dem Grund `the event is not an observation` — so kann kein `model_call` das Ergebnis eines anderen lesen, und die Kaskade braucht nicht transitiv zu sein; sonst ließe `gate try <model_call-id>` und danach `redact` einen Befund von verify stehen, mit legitimen Kommandos — kostet, wenn falsch: eine spätere Aufgabe, die auf Ergebnissen aufbaut, braucht dann die transitive Kaskade.
Task 6: review — Needs fixes: Important (1) Deadlock: A `redact event 1` (Aufruf 5 las 1) und B `redact event 5` — A sperrt 1, B sperrt 5, A nimmt Kettenposition N, B wartet auf N, A wartet auf Zeile 5; Docstring behauptet das Gegenteil. (2) Tutorial zeigt `$ uv run pytest`, der Block enthält die Coverage-Tabelle aus `--cov`.
Ruling T1-b (ersetzt T1-a): Der Testblock wird aus einem Lauf genau des Kommandos getippt, das die Seite zeigt (`uv run pytest`), aus einem Lauf, nie gestückelt. T1-a verlangte `--cov` und erzeugte den Widerspruch selbst — kostet, wenn falsch: nichts.
Ruling R-12: Die Kaskade findet und sperrt die betroffenen model_calls zusammen mit den Zielen in einer aufsteigenden Sperrrunde, bevor eine Kettenposition genommen wird; dann wartet eine zweite Tilgung schon an der Zeilensperre, nicht an der Kette — kostet, wenn falsch: ein Deadlock unter gleichzeitigen Tilgungen, den PostgreSQL abbricht, sauber zurückgerollt.
Task 6: fix round 1/1 (4 addressed, 0 open; commits 8cac96f..a1f632a). Rest-Race (ein model_call, der zwischen Lesen und Sperren entsteht, wird nicht mitgetilgt; verify meldet ihn, eine spätere Tilgung findet ihn) im Docstring benannt — Landkarte.
Task 6: minor (deferred): `cascaded:`-Zeilen fehlen auf dem Pfad „unfinished".
Task 6: complete (commits 9362d0a..a1f632a, review clean)
Task 7: implementer DONE_WITH_CONCERNS (e6bbe89, d7651f7, 82bb0de, b9276e7; 1255 passed; alle Tore grün; pip-audit sauber; Landkarte 152 → 178). Einwände: PR-Nummer fehlt in der Landkarte; P-PG verweist auf das noch nicht eingecheckte Protokoll; `policy rule --revoke` verlangt `--regions`; gehostete Anbieter in der How-to nicht echt gelaufen.
Ruling R-13: Die Prüfung von Aufgabe 7 ist das Doku-Paket der Endprüfung (Opus) — dieselbe Diff zweimal zu prüfen kostet eine Runde ohne neue Augen; die Endprüfung läuft in zwei Paketen: Code (78b0d85..a1f632a) und Doku (a1f632a..b9276e7) — kostet, wenn falsch: ein Befund der Doku kommt eine Stufe später.
Task 7: complete (commits a1f632a..b9276e7, reviewed in the final docs package)
Endprüfung Doku (Opus): ready with fixes — I-1 Kopf des eingefrorenen Specs falsch (26f4cb4 ändert §2.5 nicht; R-6, R-7 fehlen unter den Abweichungen; design-records.md „four places"); I-2 How-to unterschlägt Ausgabe von `policy rule … --yes`; I-3 R-5 auf keiner Seite; I-4 Verweise auf das noch nicht eingecheckte Protokoll (Controller, nach der Welle). 16 Minor; vier Punkte fehlen in der Landkarte.
Endprüfung Code (Opus): ready with fixes — I-1 Tilgung während eines Anbieteraufrufs lässt das Ergebnis stehen, verify rot (gemessen); M-1 verify prüft nicht, dass ein Policy-Event keine Einheiten hat; M-2 T201-Kommentar 49 statt 50; M-3 Docstring set_policy behauptet zu viel unter READ COMMITTED; M-4 „processed locally" bei Ablehnung; M-5 `--storage` optional statt Pflicht (Spec §5); M-6 R-6/R-9-Zitate ohne Plan; M-7, M-8 Landkarte.
Ruling R-14: Das Gate nimmt in der Schreibtransaktion des `model_call` dieselbe Zeilensperre auf seine Eingabe-Events wie `redact`, liest sie erneut und schreibt, wenn eine Eingabe seit dem Lesen getilgt wurde, in derselben Transaktion die Kaskade auf die eigenen Einheiten (Grund `cascade of redaction <id>` mit der Tilgung, die die Eingabe traf). So bleibt verify nach jeder Folge legitimer Kommandos grün; das Fenster wäre sonst so lang wie der Aufruf beim Anbieter — kostet, wenn falsch: eine Sperre mehr je Aufruf.
Ruling R-15: Fixwelle (eine, Opus) nimmt Code I-1 (R-14), M-1 bis M-6, Doku I-1 bis I-3, die sachlich falschen Doku-Minor (Richtung der Verzögerung, Reihenfolge stderr im explain-Block, Schlüssel-Schritt der How-to, die vier ungenauen Formulierungen) und die vier fehlenden Landkartenpunkte; M-7, M-8 und die übrigen Minor gehen in die Landkarte. Doku I-4 macht der Controller nach der Welle (Protokoll einchecken).
Fixwelle (Opus): DONE (89a79f0 Code, 13241a5 Doku, f08ca34 Landkarte; 1267 passed; alle Tore grün; pip-audit sauber; Landkarte 178 → 183). R-14 brauchte zusätzlich ein zweites Lesen der model_calls in redact nach dem Sperren; M-3 im Code behoben (write_action_at); `gate try` meldet `erased: …` mit 2.
