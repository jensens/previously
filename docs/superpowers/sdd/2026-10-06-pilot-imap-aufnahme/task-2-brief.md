## Task 2: Eine Mail als Event — `core/mail.py`

**Files:** `core/mail.py` (neu), `tests/test_mail.py` (neu), `tests/mails/*.eml` (neu, erfunden), `pyproject.toml` und `uv.lock` (`html2text>=2025.4`), `DEPENDENCIES.md`, `.importlinter` (nur `core.mail` importiert `html2text`; namentlich, wie `pyrage`).

**Interfaces — Produces:**
```python
@dataclass(frozen=True)
class Attachment:
    content: bytes            # dekodiert
    filename: str | None
    media_type: str

@dataclass(frozen=True)
class Mapped:
    event: RawEvent           # ohne `blobs`; `payload` ohne `raw`
    raw: bytes                # die Rohmail, Blob mit media_type "message/rfc822"
    attachments: tuple[Attachment, ...]
    inner: tuple["Mapped", ...]   # Mails im Anhang, §3.6, bis Tiefe MAX_FORWARD_DEPTH

MAX_FORWARD_DEPTH = 5
def map_mail(raw: bytes, *, internaldate: datetime, found_in: Mapping[str, str]) -> Mapped: ...
def variant_key(message_id: str, artifact_hash: bytes) -> str: ...   # "<id>#<16 hex>"
```

`map_mail` ist rein: kein Netz, keine Datenbank, keine Uhr (der Fallback für `occurred_at` ist `internaldate`, nicht „jetzt").

- [ ] **Step 1: Testmails** als Dateien unter `tests/mails/`, je eine erfundene Mail für: einfach (`text/plain`, Umlaute, zwei `Received`), nur HTML (Outlook-Absätze), HTML mit `blockquote`, ohne Message-ID, `Date` unlesbar, unbekannter Zeichensatz, verschlüsselt (`multipart/encrypted`), nur Anhänge, signiert (`multipart/signed`), Antwort mit `In-Reply-To`/`References`, weitergeleitet als Anhang mit leerer Rahmenmail, verschachtelt sechs tief, `broken_mime` (Grenze fehlt), zwei Anhänge mit gleichem Inhalt.
- [ ] **Step 2: Tests, die scheitern** — je Datei die erwarteten Felder nach Spec §3.1–§3.6: `source == "email"`, `external_id`, `occurred_at` und `date_source`, Einheiten (Betreff zuerst; der feste Satz bei keinem lesbaren Körper), `channel_identities` in Kopfreihenfolge, `headers` vollständig mit Dubletten, `body` (Teil, Zeichensatz, Umwandler samt Fassung, `replaced`), `artifact_hash` nach §3.3, `inner` bei Weiterleitung mit `forwarded_in`, Tiefe sechs → fünf entpackt, die sechste bleibt Anhang und die Nutzlast auf Tiefe fünf vermerkt es. Dazu: zwei Kopien derselben Mail mit verschiedenen `Received`-Zeilen haben denselben `artifact_hash`; ein anderer Körper einen anderen; der Text steht nirgends in der Nutzlast.
- [ ] **Step 3: rot.**
- [ ] **Step 4: Umsetzen** mit `email.message_from_bytes(raw, policy=email.policy.default)` (gemessen, siehe oben). HTML: `html2text.HTML2Text()` mit `body_width = 0`, `ignore_images = True`. Ein unbekannter Zeichensatz: als Latin-1 lesen, `replaced = True`. Nullbyte und Unlesbares: U+FFFD, `replaced = True`. Kaputtes MIME: was lesbar ist, und die Mail fällt nicht heraus.
- [ ] **Step 5: grün; Mutationen:** Transportzeilen gehen in den `artifact_hash` → der Kopien-Test rot; das Entpacken entfällt → der Weiterleitungs-Test rot; die Tiefe ohne Grenze → der Tiefe-sechs-Test rot; `Date` ohne Fallback → der Test mit unlesbarem `Date` rot.
- [ ] **Step 6: `DEPENDENCIES.md`** (Urteil aus „Was der Plan am Spec entscheidet", 1), sechs Tore, Commit.

---

