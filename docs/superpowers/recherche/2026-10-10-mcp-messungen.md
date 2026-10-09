# MCP gemessen: zwei Clients gegen einen Testserver

> **Messbericht, Stand 2026-10-10.** Er wird nicht nachgezogen; wer ihn
> zitiert, nennt das Datum. Er prüft, was der
> [Recherchebericht vom 2026-10-09](2026-10-09-mcp-stand-und-designgrundlagen.md)
> in Abschnitt 10 als offene Messungen nennt, an den Clients, mit denen der
> Betreuer arbeitet. Gemessen am 2026-10-09 (Server, Typen) und in der Nacht
> auf den 2026-10-10 (Clients).

## Kurzfassung

Ein Wegwerf-Server auf dem offiziellen Python-SDK `mcp` 2.3.0 bedient beide
Protokoll-Generationen am selben Endpunkt, und Pyright strict meldet über
einen minimalen Server unter der Projektkonfiguration keinen Fehler. Die
Clients unterscheiden sich stärker, als die Recherche erwarten ließ: Claude
Code 2.1.289 spricht `2026-07-28`, Mistral Vibe 2.26.1 spricht `2025-11-25`
und öffnet für jeden Werkzeugaufruf eine neue Verbindung. In beiden Clients
verdrängt `structuredContent` den Textblock; in Vibe verschluckt ein
`resource_link` das ganze Ergebnis, ein Fehler mit `structuredContent` kommt
gar nicht an, und der alte Harness verliert das Fehlerkennzeichen. Eine Zahl
über 2^53 rundet Claude Code und lässt Vibe den ganzen Zug abbrechen. Was
bleibt, ist schmal und hält in beiden: **ein einziger Textblock je Ergebnis,
Fehler, die sich im Text selbst als Fehler ausweisen, Quellen als URI im Text,
keine Zahl über 2^53, eine stabile Werkzeugliste, ein statischer Token im
Header.**

## Aufbau

- **Server:** `mcp` 2.3.0, `MCPServer`, `streamable_http_app(stateless_http=True, json_response=True)`,
  uvicorn auf `127.0.0.1:8765`, eine eigene ASGI-Hülle, die jede Anfrage
  mitschreibt (Header ohne `Authorization`, Körper) und ohne gültigen
  statischen Bearer-Token mit 401 ablehnt. Code im Anhang.
- **Werkzeuge:** jedes liefert eine Form von Ergebnis mit eindeutigen Marken
  (`MARK-…`): nur Text; Text und `structuredContent`; zwei Textblöcke; Fehler
  mit `structuredContent`; Text und `resource_link`; eingebettete Ressource;
  eine Zahl 2^60+1 in `structuredContent`; Fehler nur mit Text; Text mit einem
  Zitat als URI. Dazu eine Ressource und ein Prompt.
- **Messung:** der Client bekommt einen Prompt (Anhang), ruft die Werkzeuge
  und berichtet wörtlich, welche Marken in welchem Teil des Ergebnisses bei ihm
  ankamen. Der Mitschnitt des Servers sagt, was der Client gesendet hat.
- **Clients:** Claude Code 2.1.289 (cli), Server mit `claude mcp add --transport http … --header "Authorization: Bearer …"`;
  Mistral Vibe 2.26.1 mit Mistral Medium 3.5, offiziell installiert
  (`curl -LsSf https://mistral.ai/vibe/install.sh | bash`), Server in
  `.vibe/config.toml` des Probe-Verzeichnisses.

## M1 — beide Generationen am selben Endpunkt (2026-10-09)

| Anfrage | Antwort |
|---|---|
| `server/discover` mit `_meta` `protocolVersion: 2026-07-28` | 200; `supportedVersions: ["2026-07-28"]`, `cacheScope: private`, `ttlMs: 0` |
| `initialize` mit `protocolVersion: 2025-06-18` | 200; `protocolVersion: 2025-06-18`, `listChanged: false` |
| ohne Token | 401 (eigene Hülle) |

Ein Schalter, `stateless_http=True`; kein eigener Code verzweigt nach
Generation.

## M2 — Pyright strict (2026-10-09)

`uv run --all-extras --with mcp==2.3.0 pyright` im Worktree, also unter der
Projektkonfiguration und nicht mit `--isolated`, über einen minimalen Server —
Werkzeuge mit Rückgabe `str`, Pydantic-Modell und rohem `CallToolResult`, eine
Ressourcenvorlage, ein Prompt, die ASGI-App — und einen Test mit dem
In-Memory-`Client` des SDK: **0 errors, 0 warnings**; der Test grün. Die
Felder der SDK-Typen heißen in Python `is_error`, `structured_content`, auf der
Leitung `isError`, `structuredContent`.

## M3 — was die Clients senden

| | Claude Code 2.1.289 | Mistral Vibe 2.26.1 |
|---|---|---|
| Generation | `2026-07-28` (Header `MCP-Protocol-Version`, `Mcp-Method`, `Mcp-Name`) | `2025-11-25` (`initialize`, `notifications/initialized`) |
| `User-Agent` | `claude-code/2.1.289 (cli)` | `MistralAI-VibeCLI/2.26.1` |
| `clientInfo` | `claude-code` 2.1.289 | `mcp` 0.1.0 |
| Fähigkeiten | `roots.listChanged`, `elicitation` (`form`, `url`) | keine (`capabilities: {}`) |
| Ablauf | `server/discover`, `prompts/list`, `resources/list`, `tools/list`, dann je Aufruf `tools/call` | je Aufruf eine neue Verbindung: `initialize`, `notifications/initialized`, `tools/call`, `tools/list` |
| Ressourcen, Prompts | listet beide | fragt keins von beiden |
| statischer Token | `--header` — angenommen | `auth.type = "static"` mit `api_key_env`: **kein Header gesendet**, fünfmal 401; mit `headers = { Authorization = "Bearer …" }`: angenommen |

Vibe hat die 401 nicht gemeldet: das Modell berichtete für jedes Werkzeug
„returned nothing I can see". Ein abgelehnter Zugang kommt bei Vibe also nicht
beim Nutzer an.

Der „unified harness" von Vibe ist bei der offiziellen Installation der
Standard (die Recherche nahm opt-in an). Er ruft Werkzeuge aus einem
TypeScript-Sandkasten (`run_typescript`, `tools.<server>.<werkzeug>`) und hält
die Werkzeugliste über Sitzungen hinweg: zwei Werkzeuge, die der Server nach
einem Neustart neu anbot, sah er nicht („TypeError: tools.mcp_probe.shape_error_text is not a function"),
und er fragte den Server dabei gar nicht an. `--legacy-harness` startet den
Python-Weg; dort heißen die Werkzeuge `probe_<werkzeug>`.

## M4 — was beim Modell ankommt

| Form | Claude Code 2.1.289 | Vibe, unified harness | Vibe, `--legacy-harness` |
|---|---|---|---|
| nur Text | ✔ vollständig | ✔ | — |
| Text + `structuredContent` | ✘ nur `structuredContent`, Text fehlt | ✘ nur `structuredContent`, Text fehlt | — |
| zwei Textblöcke | ⚠ beide, ohne Trenner aneinandergehängt | ✔ beide | — |
| Fehler + `structuredContent` | ⚠ nur der Text, als `<error>…</error>` | ✘ **nichts** | — |
| Fehler nur mit Text | — | — (Werkzeug nicht gesehen, s. M3) | ⚠ Text kommt an, aber als `ok: True` — das Fehlerkennzeichen fehlt |
| Text + `resource_link` | ✔ Text und Link | ✘ **nichts, auch der Text fehlt** | — |
| eingebettete Ressource | ✔ | ✔ (das Modell zählt sie als „Ressource") | — |
| Zitat als URI im Text | — | — | ✔ exakt (`previously://event/42#unit-3`) |
| Zahl 2^60+1 in `structuredContent` | ✘ gerundet zu `1152921504606847000`; der Text mit der exakten Zahl fehlt | ✘ **Zug bricht ab**: „exceeds safe integer domain for JSON floats" | — |
| Ressource `probe://doc/1` | sichtbar (über `resources/list`) | nicht abgefragt | — |
| Prompt | dem Modell nicht sichtbar (Slash-Befehl für den Nutzer) | nicht abgefragt | — |

Ein Strich heißt: in diesem Lauf nicht gemessen. Die Aussagen in der Tabelle
sind die der Modelle über das, was sie sahen; der Mitschnitt bestätigt jeweils,
dass der Server die Form gesendet hat.

## Was daraus für den Entwurf folgt

1. **Ein einziger Textblock je Ergebnis**, ohne `structuredContent` daneben
   und ohne `resource_link`: beides kostet in mindestens einem Client Inhalt,
   in Vibe das ganze Ergebnis.
2. **Ein Fehler weist sich im Text selbst als Fehler aus** (etwa
   „Error: …"), und er enthält die Handlung, die weiterhilft; das Kennzeichen
   `isError` wird gesetzt, aber nicht vorausgesetzt.
3. **Quellen als URI im Text**, in einem festen Schema
   (`previously://event/<id>#unit-<n>`).
4. **Keine Zahl über 2^53** in einem Ergebnis; Hashes als Hex-Zeichenkette.
5. **Eine stabile Werkzeugliste**: neue Werkzeuge kommen mit einem Release,
   und die Clients verbinden danach neu.
6. **Zugang über einen statischen Token im `Authorization`-Header**; für Vibe
   über `headers`, nicht `api_key_env` (Stand 2.26.1).
7. **Beide Generationen über das SDK, ohne eigenen Code** — Entscheidung des
   Betreuers vom 2026-10-10: Entwurf für `2026-07-28`; die alte Generation nur
   über `stateless_http=True` und je einen Test pro Generation; kein Code
   verzweigt nach Generation, und ein Merkmal, das das bräuchte, bekommt die
   alte Generation nicht. Sobald Vibe `mcp` 2.x spricht, fallen Schalter und
   alter Test weg.
8. **Fehler beim Verbinden sieht ein Vibe-Nutzer nicht**: die Dokumentation
   des Servers sagt, wie man den Zugang prüft.

## Was offen bleibt

- Ob `/mcp refresh` im unified harness neue Werkzeuge holt (nicht gemessen).
- Wie der unified harness einen Fehler nur mit Text zeigt (das Werkzeug kam
  dort nicht an).
- Wie Claude Code einen Fehler nur mit Text und ein Zitat als URI zeigt (nicht
  gemessen; nach M4 ist bei Text kein Verlust zu erwarten).
- Zwei uvicorn-Worker hinter einem Lastverteiler (nicht gemessen; M1 lief mit
  einem Prozess).

## Anhang: die Prompts

Erster Lauf:

```text
Call every tool of the MCP server "probe", one after the other:
shape_text, shape_text_and_structured, shape_two_text, shape_error_structured,
shape_resource_link, shape_embedded, shape_big_int.

For each tool, report verbatim every string starting with MARK- that you
received, and in which part of the result it reached you (text block,
structured content, error, resource link, embedded resource). If a tool
returned nothing you can see, say so. For shape_big_int also report the
number exactly as you received it.

Then list which resources and prompts of the server you can see, if any.
```

Zweiter Lauf (Vibe, ohne die große Zahl):

```text
Call these tools of the MCP server "probe", one after the other:
shape_text, shape_text_and_structured, shape_two_text, shape_error_structured,
shape_resource_link, shape_embedded.

For each tool, report verbatim every string starting with MARK- that you
received, and in which part of the result it reached you (text block,
structured content, error, resource link, embedded resource). If a tool
returned nothing you can see, say so.

Then list which resources and prompts of the server you can see, if any.
```

Dritter Lauf:

```text
Call these two tools of the MCP server "probe", one after the other:
shape_error_text, shape_text_with_uri.

For each tool, report verbatim every string starting with MARK- that you
received, whether the result was marked as an error, and in which part of
the result it reached you. If a tool returned nothing you can see, say so.
For shape_text_with_uri, also report the source it cites, exactly.
```

## Anhang: der Testserver

Wegwerf-Code, nicht Teil des Projekts; die Markierungen für die Typprüfung
sind hier weggelassen.

```python
"""Throwaway MCP probe server (spike, 2026-10-09). Not project code.

Every tool returns one result shape with unique markers, so that asking the
client's model "what exactly did the tool return?" shows what reached it.
Every HTTP request is logged (headers, protocol era, capabilities) to
requests.jsonl; a static bearer token is required.
"""

import json
import pathlib
import time

import uvicorn
from mcp.server.mcpserver import MCPServer
from mcp.types import (
    CallToolResult,
    EmbeddedResource,
    ResourceLink,
    TextContent,
    TextResourceContents,
)

HERE = pathlib.Path(__file__).parent
TOKEN = (HERE / "token.txt").read_text().strip()
LOG = HERE / "requests.jsonl"

mcp = MCPServer("previously-probe", instructions="A probe server. Tools return markers like MARK-1.")


@mcp.tool(description="Returns one text block.")
def shape_text() -> CallToolResult:
    return CallToolResult(content=[TextContent(type="text", text="MARK-1 text only")])


@mcp.tool(description="Returns a text block and structuredContent with different markers.")
def shape_text_and_structured() -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text="MARK-2T in the text block")],
        structuredContent={"marker": "MARK-2S in structuredContent"},
    )


@mcp.tool(description="Returns two text blocks.")
def shape_two_text() -> CallToolResult:
    return CallToolResult(
        content=[
            TextContent(type="text", text="MARK-3A first text block"),
            TextContent(type="text", text="MARK-3B second text block"),
        ]
    )


@mcp.tool(description="Returns an error with a text block and structuredContent.")
def shape_error_structured() -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text="MARK-4T error text")],
        structuredContent={"marker": "MARK-4S error structured"},
        isError=True,
    )


@mcp.tool(description="Returns a text block and a resource link.")
def shape_resource_link() -> CallToolResult:
    return CallToolResult(
        content=[
            TextContent(type="text", text="MARK-5T see the linked resource"),
            ResourceLink(type="resource_link", name="doc-1", uri="probe://doc/1", description="MARK-5L link"),
        ]
    )


@mcp.tool(description="Returns an embedded resource.")
def shape_embedded() -> CallToolResult:
    return CallToolResult(
        content=[
            EmbeddedResource(
                type="resource",
                resource=TextResourceContents(uri="probe://doc/2", mimeType="text/plain", text="MARK-6 embedded resource text"),
            )
        ]
    )


@mcp.tool(description="Returns a large integer in structuredContent.")
def shape_big_int() -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text="MARK-7T big int follows: 1152921504606846977")],
        structuredContent={"n": 2**60 + 1},
    )


@mcp.tool(description="Returns an error with a text block only.")
def shape_error_text() -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text="MARK-8 error text only: access denied by the processing policy")],
        isError=True,
    )


@mcp.tool(description="Returns one text block that cites a source by URI.")
def shape_text_with_uri() -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text="MARK-9 the customer accepted the offer [source: previously://event/42#unit-3]")]
    )


@mcp.resource("probe://doc/1", name="doc-1", mime_type="text/plain", description="A probe document.")
def doc_1() -> str:
    return "MARK-R1 resource content"


@mcp.prompt(description="A probe prompt with one argument.")
def probe_prompt(topic: str) -> str:
    return f"MARK-P1 Please summarize the topic: {topic}"


def logged(app):
    async def wrapper(scope, receive, send):
        if scope["type"] != "http":
            return await app(scope, receive, send)
        body = b""
        more = True
        messages = []
        while more:
            message = await receive()
            messages.append(message)
            body += message.get("body", b"")
            more = message.get("more_body", False)
        headers = {k.decode(): v.decode() for k, v in scope["headers"]}
        auth = headers.pop("authorization", None)
        valid = auth == f"Bearer {TOKEN}"
        try:
            parsed = json.loads(body) if body else None
        except ValueError:
            parsed = body.decode("utf-8", "replace")
        entry = {"t": time.time(), "method": scope["method"], "path": scope["path"], "auth": "valid" if valid else ("invalid" if auth else "missing"), "headers": headers, "body": parsed}
        statuses = []

        async def capture(message):
            if message["type"] == "http.response.start":
                statuses.append(message["status"])
            await send(message)

        if not valid:
            await send({"type": "http.response.start", "status": 401, "headers": [(b"content-type", b"application/json"), (b"www-authenticate", b"Bearer")]})
            await send({"type": "http.response.body", "body": b'{"error":"unauthorized"}'})
            entry["status"] = 401
        else:
            queue = list(messages)

            async def replay():
                return queue.pop(0) if queue else await receive()

            await app(scope, replay, capture)
            entry["status"] = statuses[0] if statuses else None
        with LOG.open("a") as f:
            f.write(json.dumps(entry) + "\n")

    return wrapper


app = logged(mcp.streamable_http_app(stateless_http=True, json_response=True))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")
```
