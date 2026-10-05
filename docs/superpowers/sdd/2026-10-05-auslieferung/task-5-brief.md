## Task 5: Handoff, Dokumentation, Landkarte, Einfrieren

**Files:**
- Create: `docs/superpowers/handoffs/2026-10-05-kup6s-delivery.md`, `docs/how-to/cut-a-release.md`, `docs/how-to/run-the-image.md`, `docs/explanation/delivery.md`
- Modify: `docs/how-to/index.md`, `docs/explanation/index.md`, `docs/index.md`, `README.md`, `docs/tutorials/record-your-first-event.md`, `docs/explanation/design-records.md`, `docs/superpowers/landkarte.md`, `docs/superpowers/specs/2026-10-05-auslieferung.md` (Einfrieren)

- [ ] **Step 1: Der Handoff, englisch**, nach Spec §6, Punkt für Punkt; dazu, was der Spec §3.4 vom Betreuer verlangt, als Voraussetzung („before the first image exists"). Er sagt was, warum, woran man es erkennt — nie, wie in cdk8s. Jede Umgebungsvariable mit dem Kommando, das sie liest, aus `docs/reference/configuration.md` übernommen, nicht aus dem Gedächtnis. Kein Geheimnis, kein Platzhalter, der wie eines aussieht.

- [ ] **Step 2: Die Seiten**, nach `plone-doc-style:author` (die Fähigkeit unter genau diesem Namen aufrufen):
  - `cut-a-release.md` (How-to): Spec §3.1, §3.3, §3.4, der Befehl `gh release create v0.1.0a1 --prerelease --generate-notes --target main`, was zu beobachten ist, was zu tun ist, wenn ein Schritt scheitert — welcher Schritt hat was schon veröffentlicht (Spec §5: ein gescheiterter Smoke-Test lässt die Version auf PyPI) —, Release-Notes für Betreiber (neue Migrationen: `previously migrate` vor allem anderen).
  - `run-the-image.md` (How-to): die Angaben, `migrate` zuerst, ein `docker run` je Kommando, der lokale Bau aus einem Wheel (Aufgabe 3, Step 4); für den Cluster der Verweis, dass der Betrieb ihn baut.
  - `delivery.md` (Explanation, Marke `(delivery)=`): warum das Image aus PyPI installiert, warum der Vergleich gegen `uv.lock` nur in eine Richtung geht (`tzdata`), warum kein `latest` für Alphas, warum die Migrationen im Paket liegen, warum `migrate` eine Sperre nimmt, warum die Tag-Prüfung vor dem Upload steht. Prüfen, dass die zwei `{ref}`delivery`` aus Aufgabe 2 und 3 jetzt auflösen (`test_docs_references` für `storage/migrate.py`; das Dockerfile von Hand).
  - Indexseiten und `docs/index.md`: die neuen Seiten.
  - README: Installation aus PyPI (`pip install previously` mit dem Hinweis auf Alphas, `--pre`), das Image, `previously migrate`; die Zahl der Kommandos.
  - `design-records.md`: die siebte Zeile der eingefrorenen Berichte, beim Einfrieren (Step 4).

- [ ] **Step 3: Die Landkarte**: die neue Einheit „Auslieferung" in *Wo das Projekt steht* (gebaut, zur Abnahme: der Merge dieses Zweigs — so gefasst, dass es vor und nach dem Merge stimmt), die Tabelle des Piloten (Einheit 2 beginnt beim Image; der Handoff liegt), die offenen Punkte aus Spec §12 je unter ihre Einheit. Zählen vorher und nachher mit dem Kommando aus `CLAUDE.md`.

- [ ] **Step 4: Den Spec einfrieren**: Kopf wie die anderen eingefrorenen Specs (wörtlich aus `docs/superpowers/specs/2026-10-04-stufe-1c-blobs-und-tilgung.md` übernehmen, Datum 2026-10-05), Statuszeile, die Einleitung von §12 in der Vergangenheit. Sonst nichts am Spec. Dazu: der Spec sagt in §10 Punkt 7, der Workflow laufe vor dem Merge einmal von Hand; das geht nicht (Entscheidung 1 dieses Plans) — der eingefrorene Spec bleibt, die Seite `cut-a-release.md` sagt, wie es ist.

- [ ] **Step 5: Das Tutorial, zuletzt**: aus einem frischen Lauf neu tippen, mit `uv run previously migrate` statt `uv run alembic upgrade head`; den Testblock als Letztes, aus einem grünen Lauf.

- [ ] **Step 6: Sechs Tore, `pip-audit`, Commits** — die Seiten, die Landkarte und das Einfrieren in eigenen Commits, das Tutorial zuletzt.

---

## Nach Aufgabe 5

Sache des Controllers:

1. Endprüfung des ganzen Zweigs (Code und Konfiguration; englische Doku samt Handoff).
2. Eine Fixwelle, eine Nachprüfung.
3. Das Ausführungsprotokoll nach `docs/superpowers/sdd/2026-10-05-auslieferung/`.
4. Push und Pull-Request, nach Rückfrage. Der Merge ist die Abnahme.
5. Danach der Betreuer: Trusted Publishing einrichten, der erste Lauf auf `main`, das Release `v0.1.0a1` (Spec §11, Bedingung 8).

## Selbstprüfung dieses Plans

- **Spec-Abdeckung:** §2.1 → Aufgabe 1; §2.2 → Aufgabe 2; §3 → Aufgabe 4 (§3.4 als Anleitung in Aufgabe 5); §4 → Aufgabe 3; §5 → Aufgabe 3 (Skript) und 4 (Aufruf); §6 → Aufgabe 5; §7 → Handoff und `delivery.md`; §9 → Aufgaben 2 und 5; §10 Punkte 1–6 → Aufgaben 1–2, Punkt 7 → Entscheidung 1; §11 → die Aufgaben und „Nach Aufgabe 5"; §12 → Landkarte.
- **Platzhalter:** `<sha>` in `release.yml` und `<message-file>` sind Werte, die der Umsetzer misst oder schreibt, mit der Anweisung, wie. Die Auslassungen in `storage/migrate.py` sind die Anpassung an bestehenden Code mit Verweis, was wiederzuverwenden ist; der Kern ist gelaufen.
- **Namen:** `migrate`, `Migrated`, `MIGRATION_LOCK`, `UnknownRevision`, `previously:migrations`, `wheels`, `PREVIOUSLY_VERSION`, `scripts/smoke-image.sh` — überall gleich.
- **Zahlen:** 299 MB, vier Revisionen, sieben Tabellen, sechs Verträge, fünf Unterdrückungen, elf Kommandos — gemessen am 2026-10-05 oder aus dem Baum gezählt; die Zahl der `print` in `cli.py` misst Aufgabe 2 neu.
