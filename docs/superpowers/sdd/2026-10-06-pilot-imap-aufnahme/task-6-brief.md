## Task 6: Doku, Handoff, Landkarte, Einfrieren

**Files:** `docs/explanation/connectors.md` (neu, Marke `connectors`), `docs/reference/mail-mapping.md` (neu), `docs/how-to/ingest-a-mail-folder.md` (neu), `docs/explanation/erasure.md`, `docs/how-to/erase-something.md`, Indexseiten, `README.md`, `docs/superpowers/handoffs/2026-10-06-kup6s-ingest.md` (neu, englisch), `docs/superpowers/landkarte.md`, der Spec (Einfrieren).

- [ ] Nach Spec §9, und:
  - `mail-mapping.md` (Reference): die Tabellen aus Spec §3, mit den Namen und Wortlauten, die der Code hat — `test_docs_references` hält die zitierten Wortlaute;
  - `ingest-a-mail-folder.md` (How-to): eigener Mailu-Benutzer, Ordner anlegen, Angaben setzen, laufen lassen, die Ausgabe lesen; **Tilgen**: auch im Ordner, in den Sicherungen des Postfachs und in den Antworten, die die Mail zitieren (über `In-Reply-To`/`References` zu finden); Weiterleitung als Anhang statt als zitierter Text;
  - `erasure.md`: Zitate in Antworten als Grenze der Tilgung bei Mail;
  - der Handoff (englisch, Spec §6): CronJob, Secret mit den fünf Angaben, Port 993, eigener Mailu-Benutzer, die erste Aufnahme des echten Ordners im Cluster;
  - die Landkarte: Einheit 1 gebaut; die offenen Punkte aus Spec §11 je unter ihre Einheit (Fäden als Vorgang unter Feststellungen; `.msg`/`.mbox` unter Einheit 7; OAuth unter Einwurf-Vertrag); der Hinweis, dass `ubuntu-latest` ab 2026-10-19 Ubuntu 26 ist, unter *Tore und Werkzeuge*; zählen vorher und nachher.
  - Spec einfrieren (Kopf wie die anderen, Statuszeile, §11 in der Vergangenheit).
- [ ] Sechs Tore, `pip-audit`, Commits.

---

## Nach Aufgabe 6

1. Endprüfung in zwei Paketen (Code; Doku samt Handoff).
2. Eine Fixwelle, eine Nachprüfung; Fehlbedienung benannt, nicht gejagt.
3. Das Ausführungsprotokoll nach `docs/superpowers/sdd/2026-10-06-pilot-imap-aufnahme/`.
4. Push und PR.
5. **Abnahme 11 (Spec §10), vom Betreuer, lokal:** sein echter Mailu-Ordner, `ingest imap`, `project`, `chronicle`, `blob get` der Rohmail und eines Anhangs, zweiter Lauf `0 appended`; danach Probe-Log und Bucket verwerfen.

## Selbstprüfung dieses Plans

- **Spec-Abdeckung:** §2 → 1; §3 → 2; §3.6 → 2 und 4; §4.1 → 3; §4.2 → 4; §4.3 und §5 → 5; §6 und §9 → 6; §7.3 → 2 (Entscheidung 1); §8 Punkte 1–4 → 1, 5–9 und 14 → 2/4, 10–12 → 5, 13 → 2, 15 → 1/5/6; §10 → die Aufgaben und „Nach Aufgabe 6"; §11 → Landkarte.
- **Platzhalter:** keine „TBD"; die Grenze für den Spitzenspeicher misst der Umsetzer (Review Focus 3), mit Begründung im Test.
- **Namen:** `artifact_hash_of`, `ArtifactChanged`, `ChannelIdentity`, `Mapped`, `Attachment`, `map_mail`, `variant_key`, `MAX_FORWARD_DEPTH`, `Watermark`, `Fetched`, `Connector`, `WatermarkStore`, `Ingested`, `ingest`, `ImapConnector`, `encode_folder` — überall gleich.
- **Code nur, wo gelaufen:** die Aufrufe von `imaplib` und `email` und die Einstellungen von `html2text` sind gemessen; der Rest steht als Schnittstelle und Test.
