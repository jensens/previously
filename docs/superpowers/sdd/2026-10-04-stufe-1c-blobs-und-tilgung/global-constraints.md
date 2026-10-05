## Global Constraints

Aus `CLAUDE.md` und dem Spec, für jede Aufgabe verbindlich:

- **Einrichtung des Worktrees:** `uv sync --locked --all-extras`.
- **Alle sechs Tore**, namentlich, je einzeln gefahren, mit ungekürzter Schlusszeile im Bericht. Den Block kopieren, nicht aus dem Gedächtnis aufzählen:
  ```
  uv run ruff check .
  uv run ruff format --check .
  uv run pyright
  uv run lint-imports
  uv run pytest --cov --cov-report=term-missing
  make -C docs html && make -C docs vale && make -C docs linkcheck
  ```
- **Englisch** in `src/`, `tests/`, `migrations/`, `docs/` außer `docs/superpowers/`, `README.md`, `DEPENDENCIES.md`, Wurzelkonfiguration. Deutsch nur in Spec, Plan, Landkarte und Ausführungsprotokoll.
- **Trailer `Assisted-By: Claude <Modell> <noreply@anthropic.com>`** mit dem Modell, das die Arbeit getan hat. Niemals `Co-Authored-By:`, niemals „Generated with".
- **Kein `# type: ignore`**, pyright strict; `cast` ist das Mittel. **Kein Mock** für Zeit, Datenbank, Speicher oder Zufall: Tests gegen echtes PostgreSQL (`db`) und, ab Aufgabe 5, gegen einen echten S3-Server (`blob_store`). **Keine neue Suppression**; die Liste in `CLAUDE.md` steht bei fünf.
- **Ein Kommentar ist eine Behauptung.** Jede Zahl in Kommentar, Docstring oder Seite wird am Baum gemessen, nicht aus diesem Plan übernommen. Das gilt für die Testzahlen hier — sie sind Vorhersagen — und für jede Messung, die eine Seite zitiert: wer sie zitiert, fährt das Skript aus den Anlagen selbst und nennt seine Zahl und sein Datum.
- **Was durch diese Stufe falsch wird, steht unten in jeder Aufgabe** unter *Sätze, die nicht mehr stimmen*. Die Liste ist ein Anfang, kein Ende: wer eine Datei anfasst, liest ihre Kommentare gegen den neuen Stand.
- **Eine Zusage braucht einen Test, von dem gemessen ist, dass er bricht** — mit einer Kontrolle daneben, die gemessen grün bleibt. Die Mutationen stehen in den Aufgaben; Ergebnis mit Ausgabe in den Bericht.
- **Mutationen im Baum sind erlaubt** (Betreuer, 2026-10-04): eine Zeile ändern, die deckenden Tests fahren, die Datei zurücknehmen. Verweigert das Berechtigungssystem es einem Umsetzer, sucht er keinen anderen Weg, sondern meldet es, und der Controller misst.
- **Code zitiert Seiten, nie einen Paragraphen dieses Specs.** Ein Grund steht als `` {ref}`hash-version-2` ``, `` {ref}`erasure` ``, `` {ref}`blobs` `` oder ein bestehendes Label im Kommentar. Kein `§`. In Programmausgabe steht kein Zitat.
- **Ein Label je Plan nennt seinen Plan:** `ruling X of the 2026-10-04 stage 1c plan`, `review focus N of the 2026-10-04 stage 1c plan` — und der Grund steht im Satz daneben.
- **Doku im selben Zweig**, nach `plone-doc-style:author` (unter genau diesem Namen aufrufen): ein Quadrant je Seite, ein Satz pro Zeile, Überschriften in Satzschreibung, amerikanisches Englisch, höchstens zwei Admonitions je Seite.
- **Getippte Ausgabe ist eine Messung.** Der Testlauf im Tutorial wird am Ende **jeder** Aufgabe aus einem echten `uv run pytest`-Lauf getippt, ohne die `rootdir:`-Zeile; `tests/test_docs_typed_output.py` hält `N passed` gegen den Baum.
- **Stagen namentlich**, nie `git add -A`: vorher `git status --short`, nur die eigenen Dateien; alles andere melden.
- **Kein Geheimnis in einer Ausgabe.** Weder das Geheimnis des Speichers noch eine Identität erscheint in einer Meldung, einem Befund oder einem `repr`. Eine Fehlermeldung nennt Endpunkt und Bucket, nie Zugangsdaten.
- **Testdaten sind erfunden.** Das Repository ist öffentlich.
- **Betrieb mitdenken:** Anleitungen zeigen Kommandos, die in kup6s und auf einem Host mit `docker-compose` gleich aussehen. Nichts Hosting-Spezifisches wird gebaut.

**Vertragliche Wortlaute** — exakt so, weil Tests und die Reference sie zitieren. `<hex>` ist der volle SHA-256 in 64 Hex-Zeichen, klein.

| Wo | Text |
|---|---|
| Befund | `unit <seq> does not match its digest` |
| Befund | `hash_version <n> is not known` |
| Befund | `payload is erased without a redaction` |
| Befund | `unit <seq> is erased without a redaction` |
| Befund | `redaction of event <id> is not carried out` |
| Befund | `redaction of unit <seq> of event <id> is not carried out` |
| Befund | `redaction names a target that does not exist` |
| Befund | `units are erased in part, which version 1 cannot attest` |
| Befund | `action has no valid form` |
| Befund | `blob register does not match the payload` |
| Befund | `blob <hex> is missing` |
| Befund | `blob <hex> does not match its address` |
| Befund | `blob <hex> cannot be opened` |
| Befund | `blob <hex> is erased and still present` |
| `redact`, `stdout` | `redacted by event <id>` |
| `redact`, `stdout` | `already redacted by event <id>` |
| `redact`, `stderr` | `unit <seq> was already erased` |
| `redact`, `stderr` | `blob <hex> stays in the store: event <ids> still uses it` (`<ids>` mit Komma und Leerzeichen getrennt; ab zwei Events `events … still use it`) |
| `redact`, Fehler | `the redaction is recorded as event <id>, but it is not finished: <was aussteht>; run the same command again` |
| `redact`, Weigerung | `there is no event <id>` |
| `redact`, Weigerung | `event <id> is a redaction, and a redaction cannot be redacted` |
| `redact`, Weigerung | ``event <id> was written in hash format 1, which attests its units only together: use `previously redact event` `` |
| `redact`, Weigerung | `event <id> has no unit <seq>` |
| `redact`, Weigerung | `no event uses blob <hex>` |
| `redact`, Weigerung | `--reason must not be empty` |
| `blob get`, `stdout` | `wrote <n> bytes to <file>` |
| `blob get`, `stderr`, Rückgabecode 1 | `blob <hex> is erased (event <id>)` |
| `blob get`, `stderr`, Rückgabecode 1 | `no event uses blob <hex>` |
| `blob get`, Fehler | `blob <hex> does not match its address; nothing was written` |
| `blob get`, Fehler | `blob <hex> cannot be opened: <Grund>` |
| `blob get`, Fehler | `blob <hex> is not in the store` |
| `append --attach`, Eingabefehler | `cannot read the attachment <Name>: <Grund>` |
| `append`, Eingabefehler | `payload already carries the key 'blobs' — it is reserved for the attachments` |
| Eingabefehler | `<hex> is not a blob address: 64 hexadecimal characters, lower case` |
| Eingabefehler | `<VARIABLE> is not set` |
| `show`, Nutzlast | `payload=<erased by event <id>>`; ohne Anordnung weiter `payload=<erased>` |
| `show`, Einheit | `  ¶<seq> <erased by event <id>>`; ohne Anordnung `  ¶<seq> <erased>` |
| `show`, Blob | `  blob <hex> <size> <media_type> <filename oder ->`, bei getilgter Referenz gefolgt von ` <erased by event <id>>` |
| `verify --blobs`, Zusatz | `, 1 blob matches` / `, N blobs match` — am Ende der Erfolgszeile |

**Umgebungsvariablen:** `PREVIOUSLY_BLOB_ENDPOINT`, `PREVIOUSLY_BLOB_REGION`, `PREVIOUSLY_BLOB_BUCKET`, `PREVIOUSLY_BLOB_ACCESS_KEY`, `PREVIOUSLY_BLOB_SECRET_KEY`, `PREVIOUSLY_BLOB_RECIPIENT`, `PREVIOUSLY_BLOB_IDENTITIES`.

## Review Focus
