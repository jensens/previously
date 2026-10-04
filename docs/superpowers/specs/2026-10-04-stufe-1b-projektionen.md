# Previously — Stufe 1b: Projektionen

Stand: 2026-10-04 · Status: Entwurf, zur Abnahme

Dieser Spec entsteht auf Deutsch, weil Absicht hier genauer zu fassen ist. Er
friert ein, sobald seine Explanation-Seiten stehen, mit datiertem Kopf — so, wie
`CLAUDE.md` es unter *A specification starts in German and then freezes*
beschreibt und [About the frozen design records](../../explanation/design-records.md)
es als Ablauf festhält. Bis dahin ist er das maßgebliche Dokument für 1b.

Er argumentiert aus der Architektur (`2026-10-01-architektur.md`, eingefroren)
und aus dem, was Stufe 1a gebaut hat. Wo er der Architektur widerspricht oder
sie präzisiert, sagt er es in §1.1.

---

## 1. Was 1b liefert — und was nicht

Vier Dinge, in dieser Reihenfolge, weil jedes auf dem vorigen sitzt:

1. **Das Protokoll.** `LogStore[Conn]` und `ProjectionStore[Conn]` in
   `previously.contract`, generisch über den Verbindungstyp. Danach existiert
   die Kante `core → storage.postgres` nicht mehr, und zwei
   import-linter-Ausnahmen samt dem Riegel im Testlauf fallen **ersatzlos**
   (§2).
2. **Die Maschinerie.** `projection_state` nach §4.4 der Architektur, ein
   Arbeiter, der gestapelt von `up_to_id` bis zur Spitze nachzieht und bei
   Versionserhöhung neu baut (§4), und die Zusage, die ihn rechtfertigt:
   *ableitbar und wegwerfbar*, als Test gegen den inkrementellen Weg (§5).
3. **Zwei Projektionen.** `p_chronicle`, einheitenweise, jede Zeile mit ihrer
   Quellenangabe. Und `p_source_stats`, eine Aggregation je Quelle — im Inhalt
   bewusst trivial, in der **Form** der eigentliche Prüfstein (§3).
4. **Drei Kommandos.** `previously project` zieht nach, `previously chronicle`
   und `previously stats` lesen und weisen den Rückstand aus (§6).

**Nicht enthalten:**

- **Die Auftrags-Warteschlange aus §7.1 der Architektur** (`job`, Entprellung,
  Wiederholung, `SELECT … FOR UPDATE SKIP LOCKED`). Begründung in §1.1. Sie
  kommt mit dem ersten Konnektor in Stufe 2, wenn es einen Produzenten gibt,
  der asynchron Events erzeugt — dann ist Entprellung auch zu **testen**.
- **Blobs und Suche** (1c). `p_unit_search` teilt mit `p_chronicle` den
  Primärschlüssel `(event_id, seq)`; das ist Absicht, aber die Tabelle gehört
  nach 1c.
- **Alles, was Feststellungen voraussetzt**: `project`, `matter`, Verpflichtungen,
  der Kopf. Es gibt in 1a nur `observation` (§1.1).
- **Das Tilgungs-Event** und jede Form von Löschung. 1b nimmt eine Tilgung nur
  so hin, wie 1a sie hinterlässt — und findet dabei etwas (§1.1, §10).
- **Zuordnung** von Events zu Projekten. Darum ist `chronicle` heute die
  Chronik des **ganzen** Logs, nicht eines Projekts.

**Nachweis von 1b** (§9): das Protokoll ist drin und die Ausnahmen sind
draußen, messbar am Torprotokoll; inkrementell und neu gebaut stimmen für beide
Projektionen überein, auch bei Zeitordnung gegen id-Ordnung; eine
Versionserhöhung baut neu und sonst nichts; ein Abbruch hinterlässt einen
stimmigen Teilstand; die Kommandos laufen und sagen, was sie wissen und was
nicht.

### 1.1 Was 1b an der Architektur korrigiert oder präzisiert

**§4.4, die Beispielprojektion `p_obligation`, ist vor Stufe 4 nicht baubar.**
Sie trägt `debtor`, `creditor`, `due_date`, `state`, `evidenced_by` — das sind
Feststellungen (`assertion`), und die entstehen im Gate. Stufe 1a schreibt
ausschließlich `observation`: das Schema erlaubt alle drei Arten
(`event_kind_check`), `append` nagelt eine fest (`_KIND = "observation"`). Das
ist kein Fehler der Architektur, aber eine Folge, die sie nicht ausspricht:
**die erste Stufe mit Projektionen kann nur die Maschinerie liefern, nicht die
fachliche Projektion.** 1b nimmt das ernst und macht die Maschinerie zur
Lieferung — mit zwei Projektionen, die aus reinen Wahrnehmungen ableitbar sind.

**§7.1 sieht `project` als ereignisgetriebenen Prozess vor.** In 1a gibt es
nichts Asynchrones: Events kommen ausschließlich über `previously append`,
synchron, aus einem Prozess. Eine Warteschlange mit Entprellung, Wiederholung
und `not_before` löst ein Problem, das erst mit einem Konnektor entsteht, der
IMAP abfragt — und sie wäre heute nur mit künstlich erzeugten Aufträgen zu
testen. 1b baut den Arbeiter darum als **Kommando**, das von `up_to_id` bis zur
Spitze nachzieht. Die ereignisgetriebene Form ist davon unabhängig: wenn die
Warteschlange kommt, ruft ihr Arbeiter dasselbe `catch_up()`.

**§4.6 übersieht, dass eine Tilgung der Nutzlast die Einheiten nicht tilgt.**
Eine Tilgung setzt `event.payload` auf SQL-`NULL`; die Einheiten stehen in
`unit`, einer eigenen Tabelle, und bleiben davon unberührt. Eine Chronik auf
Einheitenebene zeigt den Inhalt eines getilgten Events also **weiter an**. Das
ist keine Entscheidung von 1b, sondern eine Vorgabe an das Tilgungs-Event, die
weder 1a noch die Architektur nennen: **wer tilgt, muss die Einheiten mittilgen,
oder er tilgt den Inhalt nicht.** 1b nagelt das heutige Verhalten mit einem Test
fest (§5), damit eine künftige Tilgung es bewusst ändern muss, und trägt den
Punkt in §10 ein.

**§5, die Storage-Schnittstelle, wird zu zwei Protokollen.** Die Architektur
beschreibt eine Schnittstelle. 1b trennt, was das Log tut (anfügen, lesen — nie
ändern), von dem, was eine Projektion tut (leeren, einfügen, aktualisieren —
ausdrücklich wegwerfbar). Ein Protokoll für beides verwischte genau die Linie,
die §4.4 zieht: Projektionen *tragen keine eigene Wahrheit*. Siehe §2.

**Ein Fund an vorhandenem Code, nicht an der Architektur:** `previously show`
druckt Einheiten als `¶{seq} {content}` **roh**. Einheiten werden an
Leerzeilen getrennt, einfache Umbrüche bleiben also erhalten — eine Einheit mit
einem Umbruch darin bricht in `show` still auf mehrere Zeilen um, und die
dokumentierte Zeilenstruktur stimmt dann nicht. 1b ändert `show` nicht
(§6 begründet die Trennung), trägt es aber in §10 ein.

---

## 2. Die Protokolle

### 2.1 Warum jetzt

[About the module boundaries](../../explanation/module-boundaries.md) sagt
über das Protokoll: „scheduled for the planning round after the first part of
the project". Das ist diese Runde. Und 1b bringt ein **drittes** `core`-Modul an
die Storage-Naht. Nach Ruling T8-c der Stufe 1a ist das kein Zufall, sondern
der Zweck der namentlichen Aufzählung: jedes neue Modul mit demselben Muster
**bricht** den Vertrag, bis jemand seine Kante bewusst einträgt. 1b hätte also
sofort entscheiden müssen — dritte Ausnahme oder Protokoll. Die Doku sagt, was
die Ausnahmen sind: „the cost of typing `core` against a concrete store … the
number is there so the cost stays countable until it is paid off." Vor Stufe 2,
die viele weitere `core`-Module bringt, ist Zahlen billiger als danach.

### 2.2 Gestalt

Beide Protokolle liegen in `previously.contract`, das heute schon von allen
Schichten importiert werden darf und selbst nichts importiert. Beide sind
generisch über `Conn`, den Verbindungstyp, den **nur `storage` kennt**.

```python
class LogStore[Conn](Protocol):
    def begin(self) -> AbstractContextManager[Conn]: ...
    def tip(self, conn: Conn) -> Tip | None: ...
    def lookup(self, conn: Conn, source: str, external_id: str) -> int | None: ...
    def insert_event(self, conn: Conn, row: EventRow, units: Sequence[UnitRow],
                     key: tuple[str, str] | None) -> None: ...
    def read(self, conn: Conn, from_id: int, limit: int) -> Iterator[EventRow]: ...
    def units_by_event(self, conn: Conn, event_ids: Sequence[int]) -> dict[int, list[UnitRow]]: ...
    def count_events(self, conn: Conn) -> int: ...
    def source_keys(self, conn: Conn, event_ids: Sequence[int]) -> dict[int, tuple[str, str]]: ...
```

Das sind **acht** Methoden, und es ist genau die Menge, die `append` und
`verify` heute auf `PostgresStorage` rufen — gemessen am 2026-10-04 mit
`grep -o 'storage\.[a-z_]*(' src/previously/core/append.py src/previously/core/verify.py`,
nicht aus der Methodenliste von `postgres.py` abgeschrieben. Die erste Fassung
dieses Abschnitts hatte `units(conn, event_id)` dabei; das ruft nur `cli.py`
für `show`, und es bleibt eine Methode von `PostgresStorage` außerhalb des
Protokolls. Der Arbeiter aus 1b braucht Einheiten stapelweise und nimmt
`units_by_event`. Die Signaturen werden aus `storage/postgres.py` **abgelesen**,
nicht entworfen; der Plan prüft sie dort.

```python
class ProjectionStore[Conn](Protocol):
    def begin(self) -> AbstractContextManager[Conn]: ...
    def projection_state(self, conn: Conn, name: str) -> ProjectionState | None: ...
    def set_projection_state(self, conn: Conn, state: ProjectionState) -> None: ...
    def truncate_projection(self, conn: Conn, name: str) -> None: ...
    def insert_chronicle(self, conn: Conn, rows: Sequence[ChronicleRow]) -> None: ...
    def source_stats(self, conn: Conn, sources: Sequence[str]) -> dict[str, SourceStatsRow]: ...
    def upsert_source_stats(self, conn: Conn, rows: Sequence[SourceStatsRow]) -> None: ...
```

Die Zeilentypen (`ProjectionState`, `ChronicleRow`, `SourceStatsRow`) kommen
nach `storage/rows.py`, das heute schon kein SQLAlchemy importiert und darum
über die Grenze hinweg eine unbedenkliche Quelle für Typen ist — die Doku nennt
das „the shape is already half in place". `Tip`, `EventRow`, `UnitRow` liegen
dort bereits.

> **Korrigiert beim Planen, 2026-10-04.** Der Absatz oben ist falsch, und
> zwar an der Schicht: `contract` ist die **unterste** Schicht des
> `layers`-Vertrags in `.importlinter`, und die Protokolle in `contract`
> können keine Typen aus `storage/rows.py` nennen, ohne dass `contract`
> `storage` importiert — ein Import nach oben, der den Vertrag bricht
> (gemessen beim Planen: `BROKEN`). „Unbedenkliche Quelle über die Grenze"
> stimmt nur für `core → storage`, nicht für `contract → storage`. Also
> wandern **alle** Zeilentypen nach `previously.contract.rows`, und
> `storage/rows.py` wird gelöscht, kein Re-Export. Folge: `storage` importiert
> dann `contract`, und damit existieren **alle sechs** Kanten, die die
> Schichtenordnung erlaubt — `module-boundaries.md` sagte fünf. Der Plan
> trägt das in Aufgabe 1.

`PostgresStorage` implementiert beide Protokolle und bindet `Conn` an
`sqlalchemy.Connection`. `core` nennt diesen Typ nie.

**Warum `upsert_source_stats` die Zeile nimmt, wie sie ist, und nicht
rechnet:** die Aggregation (`events + n`, `least(first_seen, …)`) ist
Fachlogik und gehört nach `core`, wo ein Test sie ohne Datenbank trifft. Der
Store schreibt, was er bekommt. Täte er die Arithmetik in SQL
(`ON CONFLICT DO UPDATE SET …`), läge die Korrektheit des inkrementellen
Schritts in `storage`, und die Behauptung „Ableitung ohne SQL" aus §7 wäre
falsch.

### 2.3 Was fällt

In `.importlinter` fallen aus **beiden** Verträgen (`core-is-clean`,
`only-storage-knows-sql`) die zwei Zeilen

```
previously.core.append -> previously.storage.postgres
previously.core.verify -> previously.storage.postgres
```

und die beiden Begründungsblöcke (Rulings T7-a, T8-c) werden auf das
reduziert, was noch wahr ist: dass es sie gab, warum, und dass das Protokoll sie
eingelöst hat. `tests/test_contracts.py::test_the_exempted_core_modules_load_no_sql_at_runtime`
fällt **ersatzlos** — er bewachte eine Kante, die nicht mehr existiert. Das
Torprotokoll von `lint-imports` zeigt danach `0 ignored imports` an beiden
Stellen, wo heute `2` steht. Das ist eine **negative Messung** und als solche
in §9 festgehalten.

Die Gegenprobe gehört dazu, nach der Regel aus `CLAUDE.md` (*An assurance needs
a test measured to fail*): einen `from previously.storage.postgres import …` in
ein `core`-Modul zurücksetzen und messen, dass `lint-imports` **bricht** und das
Modul namentlich nennt. Das steht im Plan als Schritt, nicht als Test im Baum —
es ist eine Messung der Vertragsdatei, keine Zusage des Codes.

---

## 3. Schema

### 3.1 `projection_state`

Wörtlich aus §4.4 der Architektur:

```sql
CREATE TABLE projection_state (
  name      text PRIMARY KEY,
  up_to_id  bigint NOT NULL,
  version   int NOT NULL,
  built_at  timestamptz NOT NULL
);
```

`name` ist der Schlüssel, weil die Maschinerie für **mehrere** Projektionen
gebaut ist — mit nur einer bliebe genau das ungetestet. Darum zwei (§1).

`up_to_id = 0` heißt „noch nichts gebaut". Das ist eindeutig, weil Events ab 1
nummerieren (`id = Vorgänger.id + 1`, Genesis hat `id = 1`).

### 3.2 `p_chronicle`

Eine Zeile je **Einheit**, nicht je Event. Das ist der Unterschied zur
Lebendabfrage `log` und der Grund, warum die Chronik keine Kopie davon ist: sie
ist eine Entnormalisierung über vier Tabellen (`event`, `unit`, `source_key`,
und die Nutzlast für die Belegart), geschnitten auf die Frage „was ist
geschehen, Zeile für Zeile, und woher weiß ich das".

```sql
CREATE TABLE p_chronicle (
  event_id    bigint NOT NULL REFERENCES event(id),
  seq         int    NOT NULL,
  content     text   NOT NULL,
  occurred_at timestamptz NOT NULL,
  kind        text   NOT NULL,
  evidence    text,                    -- NULL: Nutzlast getilgt (§1.1, §10)
  source      text,                    -- NULL: Event ohne Quellenangabe
  external_id text,
  speaker     text,                    -- fuer Voice (Stufe 2) schon da
  start_ms    int,
  end_ms      int,
  PRIMARY KEY (event_id, seq)
);

CREATE INDEX p_chronicle_occurred_idx
  ON p_chronicle (occurred_at, event_id, seq);
```

Der Primärschlüssel trägt die **Kettenordnung**, der Index die **Zeitordnung**
— §4.1 der Architektur will beide, und `chronicle` liest in Indexrichtung
(§6.3). Das Tripel `(occurred_at, event_id, seq)` ist eindeutig, die Ausgabe
also deterministisch.

`evidence` ist **nullable**, und zwar aus dem Fund in §1.1: die Belegart steht
in der Nutzlast, und eine getilgte Nutzlast ist `NULL`. Ein `NOT NULL` hier
hieße, dass die Chronik getilgte Events nicht abbilden kann — und damit stiller
Verlust einer Zeile, die im Log steht. `source`/`external_id` sind nullable,
weil `source_key` höchstens eine Quellenangabe je Event erzwingt, nicht
mindestens eine.

Fremdschlüssel **nur** auf `event`, keiner auf `unit` und keiner auf eine
andere Projektion — §4.4: Projektionen tragen keine Fremdschlüssel aufeinander.
Der auf `event` ist richtig, weil eine Projektion für ein Event, das es nicht
gibt, nie gebaut werden darf.

### 3.3 `p_source_stats`

```sql
CREATE TABLE p_source_stats (
  source        text   PRIMARY KEY,
  events        bigint NOT NULL,
  units         bigint NOT NULL,
  first_seen    timestamptz NOT NULL,  -- min(occurred_at)
  last_seen     timestamptz NOT NULL,  -- max(occurred_at)
  last_event_id bigint NOT NULL REFERENCES event(id)
);
```

Events **ohne** Quellenangabe zählen nicht hinein — es gibt keine Quelle, der
man sie zurechnen könnte. Die Chronik zeigt sie (mit `source NULL`), die
Statistik nicht. Das ist eine Entscheidung und steht darum hier.

**Warum diese Aggregation der Prüfstein ist.** `events` und `units` sind
additiv, `first_seen` und `last_seen` sind Extrema. Inkrementell nachziehbar sind
sie **nur, weil das Log append-only ist**: könnte eine Zeile verschwinden,
bräuchte ein Minimum einen Neubau, weil man einem Minimum nicht ansieht, ob sein
Träger noch existiert. Die Projektion ist also aus genau der Eigenschaft
korrekt, die das Projekt ausmacht. Eine Tilgung ändert daran nichts, solange sie
nur die Nutzlast leert — `occurred_at`, `kind` und die Einheiten bleiben. Sobald
eine Tilgung Einheiten löscht (§10), stimmt `units` nicht mehr, und dieser Satz
hier wird falsch; darum steht er so ausdrücklich.

---

## 4. Der Arbeiter

### 4.1 Nachziehen, gestapelt

`catch_up(log, store, projection, batch_size=500)`:

1. `state = store.projection_state(conn, name)`; fehlt die Zeile oder ist
   `state.version != projection.VERSION`, dann **Neubau**: `truncate_projection`,
   `up_to_id = 0`, `version = projection.VERSION`. **Ungleich**, nicht kleiner:
   auch ein zurückgenommener Code (Version 2 im Baum, Version 3 in der Tabelle)
   hat eine andere Ableitungslogik als die, mit der die Tabelle gebaut wurde.
2. `tip = log.tip(conn)`; ist `tip is None` oder `tip.id == up_to_id`, dann
   nichts zu tun.
3. Sonst in Stapeln von höchstens `batch_size` Events: lesen ab
   `up_to_id + 1`, Zeilen ableiten (§7), schreiben, `up_to_id` auf das letzte
   verarbeitete Event setzen — **alles in einer Transaktion je Stapel**.

**Die tragende Invariante: Zeilen und `up_to_id` wandern in derselben
Transaktion oder gar nicht.** Bricht ein Lauf mitten im Nachziehen ab, bleibt
eine in sich stimmige Teilprojektion, und der nächste Lauf macht bei
`up_to_id + 1` weiter. Das ist der ganze Grund, warum `up_to_id` existiert; ein
einziger Transaktionsblock über das ganze Log wäre das Gegenteil davon (und die
1a-Spec §4.4 benennt „eine sehr große Transaktion" ausdrücklich als Risiko in
der Gegenrichtung zum Stapeln).

`batch_size = 500` ist dieselbe Zahl wie `MAX_BATCH` in `append`, und aus
keinem stärkeren Grund als dem, dass eine Zahl leichter zu merken ist als zwei.
Sie ist **nicht tragend**: kein Test darf von ihr abhängen, und der Abbruchtest
(§5.4) setzt sie absichtlich klein.

### 4.2 Keine Lücken, keine Nachzügler

Eine Eigenschaft aus 1a macht das Nachziehen einfacher als in den meisten
Systemen: `id = Vorgänger.id + 1` ohne Sequenz, und der Unique-Index auf
`prev_hash` (`NULLS NOT DISTINCT`) erzwingt eine einzige Kette. **Es gibt keine
Lücken und keine Zeilen, die später erscheinen.** Ein Arbeiter, der von
`up_to_id + 1` bis `tip.id` liest, kann nichts überspringen. Bei einer Sequenz
wäre das die schwierige Stelle — eine Transaktion mit `id = 41` kann nach einer
mit `id = 42` committen, und ein Arbeiter, der 42 schon gesehen hat, verliert 41
für immer. [About the hash chain](../../explanation/hash-chain.md) begründet,
warum es keine Sequenz gibt; 1b ist der erste Ort, an dem das außerhalb der
Kettenprüfung Geld wert ist.

### 4.3 Versionserhöhung

Jede Projektion deklariert `VERSION: int` im Code. Ändert sich die
Ableitungslogik, erhöht man die Zahl, und der nächste `catch_up` baut neu —
„keine Migration, kein Handgriff" (§4.4). Die Tabellen**struktur** ändert sich
dabei nicht; eine Strukturänderung bleibt eine Alembic-Migration, wie bei jeder
anderen Tabelle.

### 4.4 Idempotenz

Ein zweiter `catch_up` ohne neue Events ändert nichts und sagt das (§6.1).

---

## 5. Die Zusage, und wie sie geprüft wird

### 5.1 Was „ableitbar und wegwerfbar" praktisch heißt

Man muss die Projektion wegwerfen können **und beim Neubau dasselbe
bekommen**. Sonst trägt sie stillschweigend eine eigene Wahrheit, und genau das
verbietet §4.4.

Ein Test, der baut, löscht und neu baut, beweist nur, dass der Neubau
**deterministisch** ist. Das ist nicht die Fehlerart, die Projektionen
umbringt. Die Fehlerart ist ein **falsches inkrementelles Nachziehen**, und das
sieht man nur, wenn man die zwei Wege gegeneinander stellt.

### 5.2 Der zentrale Test

> Events **einzeln** anfügen und nach jedem `catch_up` laufen lassen — den
> inkrementellen Weg vollständig gehen. Dann einen Neubau von Null erzwingen
> (`VERSION` erhöhen oder `truncate` + `up_to_id = 0`). **Beide Ergebnisse
> müssen zeilenweise übereinstimmen**, für beide Projektionen.

Verglichen werden **Zeilen**, nicht ein Digest. Ein Digest sagt „etwas ist
anders"; die Zeilen sagen *welches Feld* — dieselbe Lehre wie beim
festgenagelten Hash-Vektor in 1a. Bei Abweichung meldet der Test die
unterschiedlichen Zeilen.

**Das Beispiel, das den Unterschied macht**, und das als **benannter**
Regressionsfall im Test steht, nicht nur als Zufallstreffer:

```
first_seen = first_seen                          # falsch: nie nachziehen
first_seen = min(first_seen, occurred_at_neu)    # richtig
```

Beide Fassungen sind nach einem Event grün. Beide sind nach zehn Events in
Zeitreihenfolge grün — das erste bleibt das erste. Die falsche fällt erst auf,
wenn ein Event mit **früherem** `occurred_at` nachkommt — und das ist der
Normalfall, sobald eine Mail von gestern heute eingelesen wird, denn
`occurred_at` ist, wann es geschah, nicht wann es ankam. Der Testfall: drei
Events, deren `occurred_at` rückwärts läuft, inkrementell projiziert gegen neu
gebaut.

> **Korrigiert beim Umsetzen, 2026-10-04 (Aufgabe 4, gemessen).** Hier stand
> als falsche Fassung `first_seen = occurred_at_des_neuen_events` — immer
> überschreiben. Das ist **nicht** die Fassung, die in Zeitreihenfolge grün
> bleibt: nach zehn Events in Reihenfolge stünde dort das zehnte, nicht das
> erste. Gemessen vom Umsetzer: diese Mutation lässt den In-Order-Test
> fallen und den Nachzügler-Test **bestehen**, weil der ältere Nachzügler
> zufällig das Minimum *ist*. Die Fassung, die das Argument meint — grün in
> Reihenfolge, rot beim ersten älteren Nachzügler —, ist das Nie-Nachziehen
> oben. Die spiegelbildliche natürliche Falschfassung für `last_seen` ist das
> Überschreiben: `last_seen = occurred_at_neu` ist in Reihenfolge richtig und
> senkt beim älteren Nachzügler das Maximum. Beide Fehler zusammen brauchen
> beide Tests: der In-Order-Test fängt das Überschreiben, der Nachzügler-Test
> das Nie-Nachziehen. Das Argument des Abschnitts bleibt; das Beispiel war
> falsch, und ein falsches Beispiel in einer Explanation-Seite wäre
> eingefroren worden.

Bei `p_chronicle` ist dieser Unterschied nicht herstellbar — jede Zeile steht
für sich, nichts wird zusammengerechnet. **Darum eine Aggregation als zweite
Projektion**: sie ist der Teil, an dem die Zusage wirklich geprüft wird.

> **Korrigiert beim Umsetzen, 2026-10-04 (Aufgabe 5, gemessen).** Der
> Vergleich inkrementell gegen neu gebaut kann einen Fehler in der
> Zusammenführungs-Arithmetik (`merge`) **nicht** fangen. `merge` liegt auf
> beiden Wegen: der Neubau faltet den Stapel über dieselbe Funktion, die der
> inkrementelle Weg zum Mischen mit der gespeicherten Zeile benutzt. Eine
> falsche Arithmetik rechnet auf beiden Wegen gleich falsch, und der
> Vergleich ist grün. Gemessen: die Nie-Nachziehen-Mutation lässt
> `incremental == rebuilt` bestehen; rot wird nur die festgenagelte
> Zusicherung `first_seen == NOW − 5 Tage` daneben im selben Test. Was der
> Vergleich — und die Hypothesis-Eigenschaft — fängt, ist der
> **Ein-Weg-Fehler**: ein Fehler, den nur der inkrementelle Weg macht. Die
> falsche gespeicherte Zeile zum Mischen, eine verschobene Stapelgrenze, ein
> übersprungenes Event. Gemessen: `write` mischt mit `None` statt der
> gespeicherten Zeile → Vergleich **und** Eigenschaft rot, alle reinen Tests
> grün. Die Zusage „ableitbar und wegwerfbar" hält also durch **drei
> Schichten**, nicht durch den Vergleich allein: die reinen `merge`-Tests
> (Aufgabe 4) fangen die Arithmetik, die festgenagelte Zusicherung fängt sie
> Ende-zu-Ende, der Vergleich fängt die Buchführung des inkrementellen Wegs.
> Der Abschnitt oben sagt „nur der Vergleich fängt den falschen
> inkrementellen Schritt" — richtig für die Buchführung, falsch für die
> Arithmetik. Die Explanation-Seite trägt die drei Schichten mit ihren
> Messungen.

### 5.3 Die Eigenschaft

Eine Hypothesis-Eigenschaft über zufällige Verschränkungen: eine Folge aus
„`k` Events anfügen" und „`catch_up`", mit `occurred_at` zufällig und
ungeordnet, Quellen aus einer kleinen Menge gezogen (damit Aggregation
stattfindet), gegen einen Schluss-Neubau. Das Projekt hat die Maschinerie dafür
(`tests/test_properties.py`); die Eigenschaft folgt deren Muster.

### 5.4 Die übrigen Zusagen, je mit Kontrolle

Nach der Regel *mutate the assurance and measure that the test goes red — and
keep beside the test a case measured to stay green*:

- **Versionserhöhung baut neu.** Eine Zeile in `p_source_stats` vergiften,
  `VERSION` erhöhen, `catch_up` — das Gift ist weg. **Kontrolle:** ohne
  Erhöhung bleibt das Gift. Ohne die Kontrolle bewiese der rote Test nur, dass
  der Arbeiter schreibt, nicht dass die Version ihn auslöst.
- **Abbruch hinterlässt einen stimmigen Stand.** `batch_size = 2`, zehn Events,
  ein `ProjectionStore`-Wrapper, der beim dritten `insert_chronicle` eine
  Ausnahme wirft. Danach: `up_to_id` ist gleich der höchsten `event_id` in
  `p_chronicle`, und die Zeilen bis dorthin sind vollständig. Ein weiterer
  `catch_up` ohne Wrapper schließt auf. **Dass der Wrapper so leicht zu
  schreiben ist, ist eine direkte Dividende des Protokolls** — gegen
  `PostgresStorage` getypt gäbe es ihn nicht ohne Mock.
- **Zweiter Lauf ändert nichts.** Zeilen vor und nach einem `catch_up` ohne
  neue Events sind gleich, und `project` meldet `up to date`.
- **Event ohne Quellenangabe.** Erscheint in `p_chronicle` mit `source NULL`,
  erscheint nicht in `p_source_stats`.
- **Getilgtes Event.** Ein Event mit `payload = NULL` erzeugt weiter Zeilen aus
  seinen Einheiten, mit `evidence NULL`. Das nagelt den Fund aus §1.1 fest:
  wer eine Tilgung baut, die Einheiten löscht, muss diesen Test bewusst
  ändern — und findet dann §10.
- **Ordnung.** Drei Events, deren `occurred_at`-Reihenfolge der id-Reihenfolge
  widerspricht; `chronicle` gibt sie in Zeitordnung aus, `log` in Kettenordnung.
- **Entschärfung.** Eine Einheit mit Tab, einfachem Umbruch und Rückstrich im
  Inhalt erscheint in `chronicle` auf **einer** Zeile mit `\t`, `\n` und `\\`
  als je zwei Zeichen. Der gespeicherte Inhalt in `p_chronicle` ist
  unverändert — die Entschärfung ist Ausgabeformat, nicht Daten.
- **Rückstand.** Nach `append` ohne `project`: `chronicle` schreibt
  `projection is 1 event behind; run `previously project`` nach `stderr`,
  `stdout` enthält nur Zeilen. **Kontrolle:** nach `project` schreibt es
  nichts nach `stderr`. (Hier stand `1 events`; Singular korrigiert beim
  Planen, 2026-10-04.)
- **Kappung.** `--limit 2` bei fünf Zeilen im Fenster: zwei Zeilen auf `stdout`
  und ein Hinweis auf `stderr`. **Kontrolle:** `--limit 10` bei fünf Zeilen,
  kein Hinweis.

Alle Tests gegen echtes PostgreSQL via testcontainers, kein Mock — wie in 1a.
Die Ableitungsfunktionen (§7) bekommen zusätzlich reine Unit-Tests ohne
Datenbank, weil sie ohne Datenbank laufen.

---

## 6. Kommandos

### 6.1 `previously project`

Zieht alle registrierten Projektionen nach, je eine Zeile auf `stdout`, die
sagt, **welchen Weg** der Arbeiter genommen hat — sonst wäre ein
versionsgetriebener Neubau unsichtbar:

```
chronicle       caught up: 12 events, up_to_id 42
source-stats    rebuilt: version 1 -> 2, 42 events, up_to_id 42
```

Nichts zu tun:

```
chronicle       up to date, up_to_id 42
source-stats    up to date, up_to_id 42
```

> **Präzisiert beim Planen, 2026-10-04.** Der erste Lauf auf eine leere
> `projection_state` ist ein vierter Fall, den die drei Ausgaben oben nicht
> decken. `rebuilt: version 0 -> 1` wäre wörtlich falsch — es gab nichts zu
> *re*-bauen. Er heißt `built: 42 events, up_to_id 42`. Und alle vier zählen
> richtig: `1 event`, `12 events`.

Die Projektionsnamen in der Ausgabe sind die aus `projection_state.name`:
`chronicle`, `source-stats`. Rückgabecode 0; 1 bei Fehler, wie die anderen
Kommandos.

### 6.2 Zwei Ordnungen, zwei Kommandos

`occurred_at` läuft nicht parallel zu `id`. Eine Mail von letzter Woche, heute
eingelesen, bekommt `id = 42` und ein `occurred_at` vor dem von `id = 41`.
`--from`/`--limit` auf `id` und ein Zeitraum auf `occurred_at` sind damit zwei
Ordnungen, und beides in einem Kommando erzeugte Ausgaben, die niemand erklären
kann. Also:

**`log` ist die Kettenordnung**, nach `id`, mit `--from`/`--limit`. Unverändert.
Es zeigt das Log, wie die Kette es trägt.

**`chronicle` ist die Chronologie**, nach `(occurred_at, event_id, seq)`, mit
`--since`/`--until` auf `occurred_at`. Es zeigt, was geschah, in der
Reihenfolge, in der es geschah.

Das sind genau die zwei Zeitordnungen aus §4.1 der Architektur, und es
beantwortet die Frage, warum es neben `log` eine Chronik braucht.

### 6.3 `previously chronicle`

Ein **Strom**, darum streng tabgetrennt wie `log`. Sechs Felder je Zeile, in
dieser Reihenfolge: `event_id`, `seq`, `occurred_at` (ISO 8601), `source`,
`external_id`, `content`. Fehlende Quellenangabe: zwei leere Felder.

```
1	1	2026-10-03T15:41:19.888666+00:00	email	2026-10-03-kickoff@example.org	The client approved the new homepage design.
1	2	2026-10-03T15:41:19.888666+00:00	email	2026-10-03-kickoff@example.org	Next milestone: content migration starts Monday.
```

**Tabs und Umbrüche im Inhalt werden als die zwei Zeichen `\t` und `\n`
ausgeschrieben.** Eine Zeile ist eine Einheit — das ist der Zweck von
Einheiten, und ein mehrzeiliges Feld in einem tabgetrennten Strom wäre weder
lesbar noch auswertbar. Der Rückstrich selbst wird als `\\` ausgeschrieben,
damit die Entschärfung umkehrbar ist.

> **Präzisiert beim Planen, 2026-10-04.** Auch `\r` wird als die zwei Zeichen
> `\r` ausgeschrieben. `split_plaintext` normalisiert nur den eigenen Weg;
> ein Konnektor kann ein `\r` in einer Einheit liefern, und es bricht eine
> Terminalzeile genauso wie `\n`. Vier Zeichen also, Rückstrich zuerst. `show` bleibt, wie es ist: es zeigt
**ein** Event für Menschen, `chronicle` ist ein Strom für Menschen und
Werkzeuge.

Optionen: `--since <ISO 8601>`, `--until <ISO 8601>` auf `occurred_at`
(einschließlich/ausschließlich, wie ein halboffenes Intervall), `--limit`
(Vorgabe 50) als Kappung.

### 6.4 `previously stats`

Je Quelle eine Zeile, tabgetrennt: `source`, `events`, `units`, `first_seen`,
`last_seen`. Sortiert nach `source`. Keine Optionen.

### 6.5 Rückstand und Kappung gehen nach `stderr`

Beide Lesekommandos lesen `tip.id` und das `up_to_id` **der Projektion, die
sie lesen** — `chronicle` das von `chronicle`, `stats` das von `source-stats`,
denn die beiden können nach einem Neubau auseinanderliegen — und beides **in
einer Transaktion**, sonst stammen die zwei Zahlen aus zwei Zeitpunkten, und
ihre Differenz ist eine Zahl, die es nie gab. Bei Rückstand:

```
projection is 12 events behind; run `previously project`
```

Bei greifender Kappung:

```
output truncated at 50 lines; raise --limit or narrow --since/--until
```

Beides nach **`stderr`**, nicht in den Strom: in `stdout` wäre es eine Zeile,
die jeder Auswerter als Datensatz liest. Fehlt der Rückstand, kommt nichts —
**Schweigen heißt aktuell.** Der Rückgabecode bleibt 0; beides ist Hinweis,
kein Fehler.

Das ist derselbe Gedanke zweimal: ein abgeschnittenes Fenster sieht wie ein
vollständiges aus, und eine veraltete Projektion wie eine aktuelle. Beides
sagt das Werkzeug dazu, statt es den Leser merken zu lassen.

---

## 7. Modulgrenzen

Neu ist das Paket `previously.core.projection`:

```
core/projection/__init__.py     catch_up(), die Registrierung der Projektionen
core/projection/chronicle.py    derive(event, units, key) -> list[ChronicleRow]
core/projection/source_stats.py derive(...) und merge(existing, batch) -> SourceStatsRow
```

Die `derive`-Funktionen sind **reine Ableitung**: sie nehmen Zeilentypen aus
`storage/rows.py` und geben Zeilentypen zurück, ohne SQL, ohne Verbindung.
`merge` ist die Aggregationsarithmetik (§2.2 begründet, warum sie hier liegt
und nicht in SQL). Alle drei sind ohne Datenbank testbar, und das ist der Punkt.

`catch_up` ist gegen `LogStore[Conn]` und `ProjectionStore[Conn]` getypt. Es
importiert `previously.storage.rows` (Typen) und `previously.contract`
(Protokolle) — **nie** `previously.storage.postgres`. Die Schichtung `cli →
core → storage → contract` bleibt; die vier Verträge in `.importlinter`
bleiben, nur ihre Ausnahmen fallen (§2.3).

`cli.py` bekommt die drei Kommandos und importiert `catch_up` aus `core` und
`from_dsn`/`PostgresStorage` aus `storage`, wie bisher für `append`/`verify`.
Die Entschärfung aus §6.3 ist eine Funktion in `cli.py`, denn sie ist
Ausgabeformat.

`storage/postgres.py` implementiert `ProjectionStore` zusätzlich zu
`LogStore`; `storage/schema.py` und eine neue Migration `0002_projections`
tragen die drei Tabellen. `storage/rows.py` bekommt die drei Zeilentypen.

---

## 8. Dokumentation, im selben PR

Die Regel aus `CLAUDE.md`: ändert sich Code, zieht die Doku **im selben Pull
Request** nach. Für 1b heißt das:

- **Reference.** `cli.md` um `project`, `chronicle`, `stats`, mit den exakten
  Ausgabeformaten aus §6 und den Optionen. `database-schema.md` um die drei
  Tabellen und den Index, Spalte für Spalte wie bei den dreien aus 1a.
- **Explanation.** Eine neue Seite `docs/explanation/projections.md`, Label
  `(projections)=`, „About derived views". Sie trägt das Argument dieses
  Specs: warum *wegwerfbar* eine Zusage ist und kein Komfort; warum
  inkrementell gegen neu gebaut der Test ist und Neubau allein nichts
  beweist, mit dem `first_seen`-Beispiel; warum die Aggregation prüft, was
  die Chronik nicht prüfen kann; warum die inkrementelle Korrektheit aus der
  append-only-Eigenschaft folgt; warum es keine Lücken gibt (§4.2); warum zwei
  Ordnungen zwei Kommandos sind. Dazu der Tilgungsfund als das, was eine
  Chronik auf Einheitenebene über die Tilgung lehrt.
- **Explanation, bestehend.** `module-boundaries.md` wird nachgezogen: der
  Abschnitt über das Protokoll beschreibt heute einen Plan und muss den
  eingelösten Zustand beschreiben — zwei Ausnahmen weniger, Riegel weg, und
  warum zwei Protokolle statt eines. Die Messblöcke mit `2 ignored imports`
  werden neu gemessen und zeigen `0`.
- **How-to.** `rebuild-a-projection.md`: wann man `VERSION` erhöht, wie man
  einen Neubau erzwingt, wie man den Rückstand liest. Kurz, Handlung ohne
  Erklärung, Verweis auf die Explanation.
- **Tutorial.** `record-your-first-event.md` bekommt nach `show` die Schritte
  `project` und `chronicle` — als echter, abgetippter Lauf, **zuletzt**, wenn
  der Baum steht, und ohne Maschinenpfad.
- **Design records.** `design-records.md` bekommt diesen Spec in die Liste der
  eingefrorenen Berichte, sobald er einfriert, und seine zitierten Paragraphen
  in die Abbildungstabelle.

Der Spec friert ein, sobald `projections.md` steht und `module-boundaries.md`
nachgezogen ist. Dann bekommt er den datierten Kopf wie die drei vor ihm.

Vale, Sphinx mit `-W` und linkcheck gelten wie bisher. Die Vokabelliste wird
voraussichtlich `upsert` brauchen; der Plan misst das.

---

## 9. Abnahmebedingungen

| # | Bedingung | Nachweis |
|---|---|---|
| 1 | Die Kante `core → storage.postgres` existiert nicht mehr | `lint-imports`: vier Verträge KEPT, **`0 ignored imports`** an beiden Stellen, wo heute `2` steht; `test_the_exempted_core_modules_load_no_sql_at_runtime` ist gelöscht |
| 2 | Gegenprobe zu 1 | Ein zurückgesetzter Import in `core` lässt `lint-imports` BROKEN melden und das Modul nennen (Messung im Plan, nicht im Baum) |
| 3 | Inkrementell gleich neu gebaut | Für beide Projektionen, zeilenweise, einschließlich des benannten Falls mit rückwärts laufendem `occurred_at` |
| 4 | Eigenschaft | Hypothesis über zufällige Verschränkungen und ungeordnete Zeiten, gegen Schluss-Neubau |
| 5 | Versionserhöhung | Gift weg nach Erhöhung; Gift bleibt ohne Erhöhung |
| 6 | Abbruch | Nach Ausnahme im dritten Stapel: `up_to_id` gleich höchster `event_id` in `p_chronicle`, Zeilen bis dort vollständig; Folgelauf schließt auf |
| 7 | Idempotenz | Zweiter Lauf ändert keine Zeile, meldet `up to date` |
| 8 | Ordnung | `chronicle` in `(occurred_at, event_id, seq)`, `log` in `id`, an denselben Events mit widersprüchlicher Ordnung |
| 9 | Entschärfung | Tab und Umbruch im Inhalt: eine Ausgabezeile, `\t`/`\n`/`\\` als Zeichen, Daten unverändert |
| 10 | Rückstand und Kappung | Auf `stderr`, nicht `stdout`; Schweigen wenn aktuell bzw. nicht gekappt |
| 11 | Quellenlos und getilgt | `source NULL` in der Chronik, nicht in der Statistik; `payload NULL` erzeugt Chronikzeilen mit `evidence NULL` |
| 12 | Ableitung ohne Datenbank | `derive` und `merge` haben Unit-Tests, die ohne testcontainers laufen |
| 13 | Dokumentation | Alle Punkte aus §8 im selben PR; sechs Tore grün; Tutorial zuletzt neu abgetippt |
| 14 | Lauffähigkeit | `append` → `project` → `chronicle` → `stats` von Hand, gegen echtes PostgreSQL 17, als das abgetippte Tutorial |

---

## 10. Was offen bleibt

Dieser Abschnitt ist **gepflegt**, nicht eingefroren, solange der Spec lebt —
und wenn er einfriert, wandert, was dann noch offen ist, in den Spec der
nächsten Stufe. Mit dem Einfrieren der drei ersten Specs hat das Projekt den
Ort für offene Punkte verloren; dieser Abschnitt stellt ihn wieder her.

1. **Der äußere Anker.** Ausdrückliche Zusage des Betreuers vom 2026-10-04:
   darf nicht vergessen werden. Ohne Anker bezeugt die Kette, dass
   *unverändert* ist, was im Log steht — nicht, dass es *vollständig* ist.
   Spitze löschen, selbst gehashtes Event anhängen, Kette neu schreiben: alle
   drei hinterlassen ein in sich stimmiges Ergebnis. Der Weg aus der 1a-Spec
   §11: `(id, hash)` zu einem Zeitpunkt außerhalb veröffentlichen, dann prüft
   `verify` **Länge und Spitzenwert**. Die `id`-Hälfte ist die wichtige — sie
   macht den Anker gegen ein Abschneiden wirksam — und sie fehlt in
   `hash-chain.md`, das nur „publishing the tip's hash" behielt. **Ein halber
   Tag, keine Stufe.** Nicht in 1b, weil 1b sonst zwei Dinge liefert.
2. **Eine Tilgung der Nutzlast tilgt die Einheiten nicht** (§1.1). Vorgabe an
   das Tilgungs-Event: Einheiten mittilgen, oder der Inhalt bleibt in
   `p_chronicle` und in `show`. Und dann stimmt `p_source_stats.units` nicht
   mehr ohne Neubau (§3.3) — das Tilgungs-Event muss die Version erhöhen oder
   die Projektion gezielt korrigieren.
3. **`show` druckt Einheiten roh** (§1.1). Eine Einheit mit einfachem Umbruch
   bricht die dokumentierte Zeilenstruktur. Entweder entschärfen wie
   `chronicle`, oder die Reference sagt, dass die `¶`-Zeilen mehrzeilig sein
   können. Nicht in 1b, weil `show` nicht Gegenstand von 1b ist.
4. **Die Warteschlange** aus §7.1 der Architektur, vertagt auf den ersten
   Konnektor (Stufe 2). Der Arbeiter aus 1b ist so geschnitten, dass sie ihn
   aufruft statt ersetzt.
5. **Drei geparkte Testlöcher am Doku-Tor**, aus der Abschlussprüfung der
   Dokumentation: die fünf Nutzlasten im Zitat-Test sind aufgezählt statt
   abgeleitet; `test_docs_typed_output` bewacht eine Zahl von rund 35; der
   Label-Regex kennt `:ref:` nicht und sieht Labels in Codeblöcken als
   definiert. Die Lehre dazu steht im Hauptbuch: Tore halten, wo Werte aus dem
   Code **abgeleitet** werden, und lecken, wo sie **aufgezählt** sind.
6. **Zuordnung zu Projekten.** `chronicle` ist die Chronik des ganzen Logs.
   Sobald das Gate Projekte zuordnet, bekommt `p_chronicle` eine Spalte
   `project` und der Index aus §4.5 der Architektur seine erste Spalte — eine
   Versionserhöhung, keine Migration der Daten, aber eine der Struktur.
7. **`previously stats` ohne Zeitraum.** Bewusst, damit `stats` nicht zur
   zweiten Zeitordnung wird. Wenn ein Zeitraum gebraucht wird, ist das eine
   neue Projektion (je Quelle und Tag), nicht ein Filter auf dieser.
