## Task 4: Die Darstellung — `mcp_server/render.py`

**Files:** `mcp_server/__init__.py`, `mcp_server/render.py` (neu), `tests/test_render.py` (neu).

Rein: keine Datenbank, keine Uhr. Zufall nur über `secrets` für den Tag.

**Interfaces — Produces:**
```python
PAGE_CHARS: Final = 60_000
@dataclass(frozen=True)
class Head: uri: str; occurred_at: datetime; source: str; sender: str | None; recipients: tuple[str, ...]; subject: str | None
@dataclass(frozen=True)
class Shown: head: Head; units: tuple[tuple[int, str], ...]     # (seq, text)
@dataclass(frozen=True)
class WithheldMark: uri: str; reason: str
@dataclass(frozen=True)
class ErasedMark: uri: str
type Item = Shown | WithheldMark | ErasedMark
@dataclass(frozen=True)
class Page: text: str; next_cursor: str | None; removed_characters: int
def sanitize(text: str) -> tuple[str, int]: ...              # (clean, removed count) — Entscheidung 5
def render_page(title: str, items: Sequence[Item], *, cursor_for: Callable[[int], str]) -> Page: ...
def render_error(message: str) -> str: ...                   # "Error: …"
def encode_cursor(after: tuple[datetime, int], filters: Mapping[str, str]) -> str: ...
def decode_cursor(cursor: str, filters: Mapping[str, str]) -> tuple[datetime, int]: ...  # ValueError bei anderen Filtern
```
`render_page` setzt den Kopf (Titel, Seite, nächster Cursor, entfernte Zeichen), je `Shown` Kopfzeilen und die Einheiten in **einem** Zaun mit dem Tag der Antwort; hört vor `PAGE_CHARS` auf; ein `Shown`, das allein darüber läge, wird gekürzt und endet mit `… truncated — continue with get_event ids=[<id>] from_unit=<n>`. Kopfzeilen (Betreff, Absender) werden ebenfalls bereinigt und stehen außerhalb des Zauns nur als Metadaten von Previously — der Betreff kommt in den Zaun.

- [ ] **Step 1: Tests, die scheitern:** Review Focus 1 (Zaun nachgeahmt; ANSI, U+200B, U+202E, U+E0041 entfernt und gezählt; `\n`, `\t`, Umlaute bleiben); der Tag zweier Antworten unterscheidet sich; Seitengrenze nie überschritten, Review Focus 4 (Kürzung mit Verweis); Platzhalter ohne Betreff und Adresse; Cursor hin und zurück, anderer Filter → `ValueError`; kein Ausgabezeichen außerhalb von `sanitize` ungeprüft (eine Property mit Hypothesis: für beliebigen Text enthält die Seite kein Zeichen der Kategorie `Cc` außer `\n`, `\t`).
- [ ] **Step 2: rot. Step 3: umsetzen. Step 4: grün; Mutationen:** fester Tag → der Test der zwei Antworten rot; `Cf` nicht entfernt → rot; Grenze ohne Kürzung → rot; Kontrolle grün.
- [ ] **Step 5:** sechs Tore, Commit.

---

