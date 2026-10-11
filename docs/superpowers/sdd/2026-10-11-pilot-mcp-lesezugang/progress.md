# SDD ledger — plan: docs/superpowers/plans/2026-10-11-pilot-mcp-lesezugang.md

Spec: docs/superpowers/specs/2026-10-10-pilot-mcp-lesezugang.md (S), Konzept 2026-10-10-mcp-schnittstelle.md (K); Stand 1e9040a.
Zweig worktree-mcp-konzept, Start c90fb40.

## Zyklenbudget (Betreuer, wie in Einheit 3)
Je Aufgabe höchstens eine Fixrunde und eine Nachprüfung der Fixes (Sonnet); Endprüfung eine Fixwelle, eine Nachprüfung. Prüfer auf Opus für Aufgaben 4 und 5, sonst Sonnet. Befunde nach Gewicht; Fehlbedienung benennen.

## Vorprüfung
| Paar | erzeugt → verbraucht | Befund |
|---|---|---|
| 1↔2 | `Provider` (Zusage muss existieren) → `set_policy` weist unbekannte Zusage ab | passt |
| 1↔5 | `decide` mit neuen Einschränkungen → Prüfung je Inhalt mit der Kette des Clients | `Candidate` verlangt `model`; für einen Client gibt es kein Modell → R-1 |
| 2↔5 | `Client`, `client_for_token` → ASGI-Hülle, stdio | passt |
| 3↔5 | `Access`, `Delivered`, `Withheld`, `record_access` → jeder Aufruf | passt |
| 3↔gaps | `reason_code` → `policy_gaps` getrennt nach Gate/MCP | passt |
| 4↔5 | `Item`, `render_page`, Cursor → Werkzeuge | passt |
| Aufgabe | in sich | |
|---|---|---|
| 1–4, 6 | Tests ↔ Code ↔ Dateien | passt |
| 5 | groß (Store, Lesen, Server, Hülle, CLI, Verträge, Abhängigkeiten) | bleibt eine Aufgabe; Umsetzer auf Opus |

Ruling R-1: Die Prüfung je Inhalt ruft `decide` mit `Candidate(provider=client.processor, model="", effort=None)`; ein Client hat kein Modell, das Previously wählt, und `decide` prüft den Anbieter, nicht das Modell — kostet, wenn falsch: ein leeres Feld in der Entscheidung.

## Verlauf
Task 1: implementer DONE (890de55; 1304 passed; vier Mutationen rot, Kontrolle grün). Einwände: fehlende Pflichtoptionen gibt argparse mit Usage aus; ein lokaler Anbieter muss `--training no --subprocessors none` deklarieren, sonst besteht er `--no-training`/`--no-subprocessors` nicht (richtig so, gehört in die How-to); `Decision` zeigt die zusammengeführten Einschränkungen nicht (Audit nennt die Regel-Ids, reicht).
Task 1: review — Approved, vier Minor.
Ruling R-2: Zwei Minor aus Aufgabe 1 sind kleine echte Fehler und gehen in den Auftrag von Aufgabe 2 (dieselbe Datei cli.py): `--model-origin unknown` wird als Wort gespeichert statt als unbekannt; `.vale.ini` nennt vorn „Fifteen of the twenty", hinten sechzehn (24 Einträge). Kostet eine eigene Runde nicht — kostet, wenn falsch: Aufgabe 2 wird minimal größer.
Task 1: minor (deferred): ein lokaler Anbieter muss `--training no --subprocessors none` deklarieren — How-to (Aufgabe 6).
Task 1: complete (commits c90fb40..890de55, review clean)
Task 2: implementer DONE (fadfdc2; 1329 passed; zwei Mutationen rot, Kontrolle grün; R-2 (a) und (b) erledigt; T201 auf 61).
Task 2: review — Approved, ein Important (cli.md: `client add` druckt mehr als zwei Zeilen), drei Minor.
Task 2: fix round 1/1 (3 addressed, 0 open; commits fadfdc2..bde877b)
Task 2: minor (deferred): Docstring eines Tests nennt `hmac.compare_digest`, der Pfad berührt es nicht.
Task 2: complete (commits 890de55..bde877b, review clean)
Task 3: implementer DONE (da30de4; 1343 passed; zwei Mutationen rot, Kontrolle grün). Einwände: `--circle` findet ausgelieferte Events nur über `arguments.circle`; `policy gaps` zeigt MCP-Lücken mit Präfix `mcp:`.
Ruling R-3: `Delivered` trägt die Kreise des ausgelieferten Events zum Zeitpunkt des Zugriffs (`circles: tuple[str, ...]`), und `read_access --circle` filtert auch darüber — sonst beantwortet `previously access` die Frage „was hat Claude über Kreis X gesehen" für `get_event` nicht, also das Ziel des Protokolls (K §1 Ziel 3); Aufgabe 5 füllt das Feld. In der Fixrunde von Aufgabe 3 — kostet, wenn falsch: ein Feld mehr je Eintrag.
Task 3: review (Sonnet) — Needs fixes: 4 Important (Inhaltstest prüft nichts Echtes; Formprüfung stürzt bei unhashbaren Werten ab; cli.md-Beispiel `policy gaps` falsch sortiert; R-3), 3 Minor. Getippte Ausgabe im Tutorial nachgemessen: ein Lauf, stimmig. Bericht: task-3-review.md
Task 3: fix round 1/1 dispatched (base da30de4): Wichtig 1–4 + Minor 5 (Formprüfung für units/circles, bool ausschließen) + Minor 7 (Umbenennung); Minor 6 nur benannt.
Task 3: fix round 1/1 done (b37aeb6; 1345 passed; drei Mutationen rot, Kontrolle grün). Einwand: `circles` und `era` sind Pflichtfelder der Form — Aufgabe 5 muss beide füllen (`era` darf null sein).
Task 3: re-review (Sonnet) Approved — alle Befunde erledigt, keine neuen. task-3-rereview.md
Task 3: complete (commits bde877b..b37aeb6, review clean)
Task 4: dispatched (Sonnet; base b37aeb6; Prüfer Opus).
Ruling R-4: Der Betreff steht im Zaun (Plan), nicht darüber (Beispiel in K §6) — er ist Kundeninhalt; Kopfzeile nur URI, Zeit, Quelle, Absender → Empfänger, bereinigt und ohne Zeilenumbruch. Ein Tag je Antwort, neu gezogen, falls er im bereinigten Inhalt vorkommt (Review Focus 1). PAGE_CHARS-Kommentar begründet aus dem Spec und nennt die Messung an echten Mails als offen (S §12 Abnahme 2), statt sie zu behaupten — kostet, wenn falsch: eine Zeile Kommentar und ein Umbau des Beispiels in der Doku.
Task 4: implementer DONE_WITH_CONCERNS (6b92903; 1382 passed; fünf Mutationen rot, Kontrolle grün; `draw_tag(content, *, candidates=None)` öffentlich, `render_page(..., page=1)`, Kopf `page N` ohne Gesamtzahl).
Ruling R-5: Eine einzelne Einheit über der Seitengrenze verweist nicht auf sich selbst (`from_unit=n` würde dieselbe Kürzung wieder liefern — eine Schleife für das Modell). Sie endet mit einem ehrlichen Vermerk, dass der Rest der Einheit im Piloten nicht ausgeliefert wird; der Verweis auf `get_event … from_unit` bleibt für Kürzungen an einer Einheitengrenze. Offener Punkt für die Landkarte (Aufgabe 6): Rest übergroßer Einheiten (z. B. `from_char`). In der Fixrunde von Aufgabe 4 — kostet, wenn falsch: der Rest einer übergroßen Einheit fehlt über MCP, sichtbar markiert.
Task 4: Einwand Einheitenmarke `[unit n]` fälschbar im Zaun — benannt, nicht behoben (Wirkung nur irreführende Zitate innerhalb ohnehin nicht vertrauenswürdigen Inhalts); in die Erklärseite (Aufgabe 6). Anzeigenamen außerhalb des Zauns: nach Spec, bereinigt, ohne Umbruch, 200 Zeichen.
Task 4: review (Opus) — Needs fixes: I-1 R-5 fehlt; I-2 Kürzungsvermerk mit roher URI; I-3 Neuziehen des Tags in render_page ungetestet; I-4 Kappungen der Kopfzeile ungetestet (400 Empfänger → 81.210 Zeichen); I-5 PAGE_CHARS-Kommentar zitiert §12 statt §13. Zaun, Seitengrenze (3.000 Seiten gefuzzt), Cursor halten. task-4-review.md
Ruling R-6: Bei der Ausgabe zusätzlich entfernt und gezählt: Variantenselektoren U+FE00–FE0F und U+E0100–E01EF (zusammen 256 Werte — der bekannte Schmuggelkanal; nur einen Bereich zu entfernen ließe 4 Bit je Zeichen), U+034F, die Hangul-Füller U+115F, U+1160, U+3164, U+FFA0, und 8-Bit-CSI (`\x9b` samt Sequenz wie ESC [). Kostet: Emoji verlieren die Darstellungswahl, koreanischer Text mit Füllern leidet — die Kunden schreiben deutsch, gespeicherte Bytes bleiben unverändert.
Ruling R-7: Einheitenmarke im Zaun ist `#unit-<n>` (Zitierform aus K §6) statt `[unit n]`; der Fuß nennt die Seite (S §5.1); `decode_cursor` wirft mit fester Meldung statt der des Parsers. Cursor-Länge: Fehlbedienung, benannt, nicht behoben (Grenzen der Argumente prüft Aufgabe 5).
Task 4: fix round 1/1 dispatched (base 6b92903): I-1..I-5 + Minors (Surrogat-/U+2028-Tests, 8-Bit-CSI, R-6, R-7, tote Assertion).
Task 4: fix round 1/1 done (3d9b911; 1413 passed; je Fix Mutation rot, Kontrolle grün).
Task 4: re-review (Sonnet) Approved — alle Befunde erledigt; Minor: Docstring von render_page verspricht noch `from_unit` für eine innen gekürzte Einheit (→ Aufgabe 5). task-4-rereview.md
Task 4: complete (commits b37aeb6..3d9b911, review clean)
Ruling R-8: render.py wird in Aufgabe 5 erweitert, wo `get_event` es braucht: `Shown` trägt Namen der Anhänge und die Herkunft (`found_in`, Message-ID) — im Zaun, weil fremd geliefert; ein neues Element für den Fehler einer einzelnen ID (`Error: <uri> — …`, bereinigt), damit die übrigen IDs unberührt bleiben (S §5.2). Kostet, wenn falsch: ein Element mehr in der Darstellung.
Ruling R-9: `mcp_access` nennt genau, was auf der Seite steht — `Page` meldet, wie viele Elemente sie verbraucht hat und welche Einheiten je Event gezeigt wurden; `Delivered.units` und die `Withheld`-Einträge kommen daraus, nicht aus dem Gelesenen. Sonst nennte das Protokoll bei einer Kürzung Einheiten als geliefert, die das Modell nie sah (K §1 Ziel 3). Kostet, wenn falsch: zwei Felder an `Page`.
Ruling R-10: S §9 nennt für `auth.py` den `TokenVerifier` des SDK; die Planentscheidung 1 (eigene ASGI-Hülle, keine PRM, K §7) geht vor — der Spec-Satz ist eine Zeile der Schnitttabelle, der Plan begründet die Abweichung. Kostet, wenn falsch: der Wechsel zum SDK-Verifier, den der Plan ohnehin für OAuth vorsieht.
Task 5: dispatched (Opus — Integration über sechs Module, SDK, Sicherheit; base 3d9b911; Prüfer Opus).
Task 5: implementer DONE_WITH_CONCERNS (71218db, 5694f77; 1509 passed, 97,31 %; neun Mutationen rot, Kontrolle grün). Einwände: `# noqa: A002` für `id` im Template und dazu CLAUDE.md geändert; Middleware des SDK (vorläufige API) protokolliert vom SDK abgewiesene Aufrufe; 401 ohne Prinzipal schreibt kein `mcp_access`; stdio: Abbruch nach dem Schreiben, vor dem Senden protokolliert eine nie empfangene Lieferung; Chronik liest ohne Grenze je Aufruf (S §13 Punkt 1).
Ruling R-11: Keine neue Unterdrückung — die Variable des Templates heißt `{event_id}` statt `{id}`; die URIs bleiben `previously://event/<n>`, nur der Name der Variablen im angebotenen Template ändert sich. CLAUDE.md-Änderung wird zurückgenommen. „Remove the cause before you suppress the symptom" (CLAUDE.md). Kostet, wenn falsch: ein Variablenname weicht vom Wortlaut des Specs ab; die Doku nennt den echten.
Ruling R-12: stdio-Lücke (geschrieben, nie gesendet) und die unbegrenzte Lesemenge je Aufruf sind benannte Grenzen, keine Fixes: in die Erklärseite und die Landkarte (Aufgabe 6). 401 ohne gültigen Token ohne `mcp_access` ist richtig (kein Prinzipal); „abgewiesen" in S §7 ist der bekannte, nicht mehr geltende Client.
Task 5: review (Opus) — Needs fixes: I-1 R-11; I-2 der Cursor verrät `occurred_at` eines zurückgehaltenen (oder getilgten) Events auf die Sekunde; I-3 der Test „Header ist keine Identität" schickt keinen Token und kann nicht scheitern. 6 Minor. Inhalt, Token, Protokoll, Seiten, Form halten unter Gegenproben. task-5-review.md
Ruling R-13: Der Cursor trägt nur die ID des letzten verbrauchten Elements und die Filter; `occurred_at` schlägt der Server beim Dekodieren im Log nach (gegen Planentscheidung 6). Ein Platzhalter trägt nach K §3.3 nur URI und Grund — die Zeit eines zurückgehaltenen Events ist Kopf, also Inhalt. Die ID steht ohnehin im Platzhalter. Rest bleibt benannt: die Reihenfolge der Platzhalter zwischen sichtbaren Events grenzt deren Zeit ein (Erklärseite, Aufgabe 6). Kostet, wenn falsch: eine Abfrage je Folgeseite.
Ruling R-14: Was `src` direkt importiert, wird deklariert und bekommt ein Urteil in DEPENDENCIES.md (starlette, mcp-types, anyio — sofern nicht durch eigene Typen vermeidbar); was nur Tests importieren, gehört in die Dev-Gruppe. Kostet, wenn falsch: drei Zeilen mehr in pyproject.toml.
Task 5: fix round 1/1 dispatched (base 5694f77): I-1..I-3 + M-1..M-6.
Task 5: fix round 1/1 done (964584f; 1517 passed; R-13-Test rot gegen altes Format, I-3-Test rot gegen Header-Vertrauen; CLAUDE.md unverändert gegen 3d9b911). Nebenbei: botocore (seit 2026-10-05 von storage/s3.py importiert, nie deklariert) deklariert mit Urteil; anyio aus src entfernt; mcp_types über mcp.types.
Task 5: re-review (Sonnet) Approved — alle Befunde erledigt, keine neuen. task-5-rereview.md
Task 5: complete (commits 3d9b911..964584f, review clean)
Task 6: dispatched (Opus — Doku, unsichtbarer Fehlermodus; base 964584f; Mitgabe task-6-carry.md; Prüfer Sonnet).
Task 6: implementer DONE_WITH_CONCERNS (8b49768, 7aaadd7, d86fbfe, 7896b56, 2e71dc3; 1522 passed; Landkarte 185 → 200; beide Specs eingefroren). Code widersprach der Mitgabe an vier Stellen, Seiten folgen dem Code. Gemessen: Bereitschaft über `server/discover` braucht Token und die Header `MCP-Protocol-Version`, `Mcp-Method` — sonst HTTP 200 mit JSON-RPC-Fehler; Handoff nennt die genaue Anfrage. Offen: `cacheScope: private` (K §4.4) nicht geprüft.
Ruling R-15: Die Aufgabenprüfung von Aufgabe 6 ist zugleich das Doku-Paket der Endprüfung (Opus, ganzer Zweig), parallel zum Code-Paket; die Fixrunde von 6 und die Fixwelle der Endprüfung sind eine. Beide prüften sonst dieselben Seiten zweimal. Kostet, wenn falsch: ein Befund, den nur eine aufgabenbezogene Prüfung gefunden hätte — die Doku-Prüfung bekommt den Brief von 6 und die Mitgabe ausdrücklich.
Endprüfung: zwei Pakete dispatched (Opus, parallel, nur lesend): Code c90fb40..2e71dc3 (final-code.diff), Doku samt Aufgabe 6 (final-docs.diff).
Endprüfung Doku (Opus): Ready after fixes — I-1 benannte Grenze „Antwort ohne Eintrag“ gibt es im Code nicht (Eintrag vor der Antwort geschrieben); die echte ist umgekehrt und breiter als stdio (Mitgabe Punkt 5 war halb falsch — Controllerfehler); I-2 Zitattest hält Gründe nur über Bruchstücke; I-3 M4-Tabelle ohne eingebettete Ressource, Satz zu weit. 12 Minor. Landkarte 200, Einheit 3 per PR #9 gemerged. final-docs-review.md
Endprüfung Code (Opus): Ready after fixes — kein Leck, 48 echte `mcp_access`-Zeilen bestehen Form und verify. I-1 `policy gaps` nennt Kreise mit Regel; I-2 jeder Aufruf liest alle Handlungen (read_policy 0,425 s bei 6.000 Zeilen, wächst je Aufruf); I-3 `get_event`-Seite über PAGE_CHARS bei vielen Anhangsnamen. 6 Minor. Empfehlungen: `/healthz` ohne Token; Cache-Hinweise ausdrücklich. final-code-review.md
Ruling R-16: `Withheld` trägt zusätzlich die Kreise ohne Regel und die Quelle; `gaps` zählt nur jene, Events ohne Kreis unter `source:` — sonst zählt `policy gaps` Kreise mit Regel als Lücke. Kostet, wenn falsch: zwei Felder.
Ruling R-17: Eine Store-Methode liest Handlungen einer Art per SQL-Filter, ohne Migration; `read_policy` nutzt sie. Projektion der Policy bleibt offener Punkt. Kostet, wenn falsch: eine Methode mehr im Protokoll.
Ruling R-18: `GET /healthz` ohne Token vor der Prüfung (konstanter Körper nach `SELECT 1`, kein MCP, keine Daten, kein Eintrag); Bereitschaft im Handoff darüber; `server/discover` mit Token bleibt Handprobe. Weicht von S §8 ab — ein Bereitschafts-Token wäre ein voller Client mit Lesezugriff, und der Grund für den Token (wer fragte) gilt für eine Route ohne Aufruf nicht. Kostet, wenn falsch: eine Route.
Ruling R-19: Cache-Hinweise ausdrücklich privat, mit Test auf dem Draht — gegen eine stille Änderung des SDK-Standards.
Ruling R-20: Ein getilgtes Event bleibt unter `delivered` ohne Einheiten (geliefert als Platzhalter); die Referenz sagt es.
Ruling R-21: Die benannte Grenze ist umgekehrt: der Eintrag wird vor der Antwort geschrieben; eine nach dem Schreiben verlorene Antwort (stdin, HTTP-Abbruch, Prozessende) steht als geliefert. Weicht von S §7 ab; Kopf des eingefrorenen Specs vermerkt es.
Endprüfung: Fixwelle 1/1 dispatched (Opus, frisch; base 2e71dc3; final-fix-brief.md).
Endprüfung: Fixwelle 1/1 done (5102e1d, d51b671, fb890d9; 1537 passed; read_policy bei 6.000 Zeilen 0,341 s → 0,010 s; Landkarte 200 → 202). Abweichungen vom Brief angenommen: `/healthz` nutzt `log.tip` in `snapshot()` statt `SELECT 1` (mcp_server sieht nur LogStore); `/healthz` auch vor der Host-Prüfung (kubelet nennt die Pod-IP; Route zeigt nichts). 5102e1d allein lässt test_docs_typed_output rot, Zweigspitze grün.
Endprüfung: Nachprüfung (Sonnet) Approved — alle Punkte der Fixwelle erledigt, keine neuen wichtigen Befunde. final-rereview.md
Endprüfung: sechs Tore vom Controller selbst auf fb890d9 gelaufen, grün (1537 passed, 97,29 %; vale 0 in 41 Dateien; linkcheck grün; 9 Verträge).
