# MCP client capabilities: Claude Code and Mistral Vibe (as of 2026-10-09)

Scope: what each client supports of the MCP specification, with version and source, so the Previously server design relies only on what both (or explicitly one) support.

Versions this applies to:

- **Claude Code 2.1.296**, published 2026-10-09 (npm `latest` and `next`; the npm `stable` tag points at 2.1.287 of 2026-10-01). Dates per version below come from the npm registry publish times, because the changelog carries no dates. — [npm registry](https://registry.npmjs.org/@anthropic-ai/claude-code); [GitHub releases](https://github.com/anthropics/claude-code/releases); [CHANGELOG.md](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
- **Mistral Vibe 2.26.1**, released 2026-10-09; Python package `mistral-vibe`, Apache-2.0, `requires-python >= 3.12`, MCP client built on the Python SDK pinned to `mcp==1.28.1`. — [pyproject.toml](https://github.com/mistralai/mistral-vibe/blob/main/pyproject.toml); [CHANGELOG.md](https://github.com/mistralai/mistral-vibe/blob/main/CHANGELOG.md); [releases](https://github.com/mistralai/mistral-vibe/releases)
- **MCP specification revision 2026-07-28** is the current one; it deprecates Roots, Sampling and Logging, reclassifies HTTP+SSE as deprecated, moves Tasks into an official extension, and introduces MRTR. — [MCP changelog 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/changelog)

Re-check rule: anything whose evidence is dated before 2026-07-10 is marked **[re-check]**.

Legend for the matrix: ✔ supported · ◐ partial · ✘ not supported · ? unknown (no documentation, no code, no issue found).

## Overview matrix (feature × client)

### Takeaway

Claude Code covers the whole server-facing surface (tools, resources, prompts, elicitation, roots, progress, OAuth, tool search) but not sampling, and it has open bugs in how `structuredContent` reaches the model. Mistral Vibe is a tools-only MCP client: it supports tools, sampling and OAuth, and nothing I could find for resources, prompts, elicitation or legacy SSE. A design that both clients can use is: **tools over Streamable HTTP with OAuth or a static bearer header, results carried as text content blocks, optional `structuredContent` only as a duplicate of the text.**

### Cited Findings

| Feature | Claude Code 2.1.296 | Mistral Vibe 2.26.1 | Evidence |
| :-- | :-- | :-- | :-- |
| **Transport: stdio** | ✔ | ◐ (see stdio note) | CC: [MCP docs](https://code.claude.com/docs/en/mcp). Vibe: [README](https://github.com/mistralai/mistral-vibe/blob/main/README.md); open issue [#590](https://github.com/mistralai/mistral-vibe/issues/590) "stdio mcp servers have no persistent connection" (2026-04-14, **[re-check]**) |
| **Transport: Streamable HTTP** | ✔ (`http`, alias `streamable-http`) | ✔ (`http` and `streamable-http` both map to the SDK's `streamable_http_client`) | CC docs; Vibe [tools.py](https://github.com/mistralai/mistral-vibe/blob/main/vibe/core/tools/mcp/tools.py) line 20 import, [registry.py](https://github.com/mistralai/mistral-vibe/blob/main/vibe/core/tools/mcp/registry.py) `case "http" \| "streamable-http"` |
| **Transport: legacy HTTP+SSE** | ✔ (`sse`, documented as deprecated; automatic fallback from `http` since 2.1.265) | ✘ (no `sse` transport in the config model; workaround `mcp-proxy` via stdio) | CC docs + changelog 2.1.265 (2026-09-08), 2.1.274; Vibe [config/models.py](https://github.com/mistralai/mistral-vibe/blob/main/vibe/core/config/models.py) has `MCPHttp`, `MCPStreamableHttp`, `MCPStdio` only; issue [#152](https://github.com/mistralai/mistral-vibe/issues/152) closed 2026-02-12 with the proxy workaround **[re-check]** |
| **Transport: WebSocket** | ✔ (`ws`/`wss`; no OAuth, no `claude mcp add --transport`) | ✘ | CC docs |
| **Protocol revision** | 2026-07-28 on the v2 runtime (MCP TypeScript SDK 2.0), default since 2.1.274 (2026-09-16); v1 runtime = TS SDK 1.x | ? (Python SDK `mcp==1.28.1`; revision not stated in docs) | CC docs "MCP client runtimes"; Vibe pyproject |
| **Config: project scope** | `.mcp.json` at project root (approval prompt, folder trust) | `./.vibe/config.toml` `[[mcp_servers]]` (trusted folders only) | CC docs "MCP installation scopes"; Vibe README, [docs MCP servers](https://docs.mistral.ai/vibe/code/cli/mcp-servers) |
| **Config: user scope** | `~/.claude.json` (user and local scope); `claude mcp add`, `claude mcp add-json` | `~/.vibe/config.toml`; `vibe mcp add`, `/mcp add` (OAuth-only shortcut) | same |
| **Config: managed/enterprise** | `managedMcpServers`, `allowedMcpServers`, `deniedMcpServers`, `managed-mcp.json` (exclusive) | "Admin config layer for shared/enforced config that applies over user config" (2.24.0) | CC docs "Managed MCP configuration", changelog 2.1.259; Vibe changelog line 752 |
| **OAuth 2.1 for remote servers** | ✔ DCR, CIMD (SEP-991, 2.1.81), RFC 9728 discovery (2.1.85), pre-registered `--client-id/--client-secret`, `oauth.scopes`, `authServerMetadataUrl`, step-up re-auth (2.1.288), `claude mcp login` | ✔ `auth.type = "oauth"` with `scopes`, `client_id` (PKCE) **or** `client_metadata_url` (CIMD), `redirect_port` default 47823; tokens in keychain; `/mcp login` — **the docs page still says OAuth is not supported; README, source and changelog 2.25.x contradict it** | CC docs "Authenticate with remote MCP servers"; Vibe models.py `class MCPOAuth`, README "MCP Server Configuration", changelog 2.25.5/2.25.6/2.25.8/2.26.1; [docs page](https://docs.mistral.ai/vibe/code/cli/mcp-servers) "Known limitation: the CLI does not yet support MCP servers that require OAuth authentication" |
| **Static headers / bearer token** | ✔ `headers` object, `--header`, `${VAR}` expansion in `url`/`headers` | ✔ `auth.type = "static"` with `headers`, `api_key_env`, `api_key_header` (default `Authorization`), `api_key_format` (default `Bearer {token}`) | CC docs; Vibe models.py `class MCPStaticAuth` |
| **Dynamic header helper** | ✔ `headersHelper` script (10 s timeout, re-run and retry once on 401/403, needs folder trust in project scope since 2.1.238) | ✘ (no equivalent in config model) | CC docs "Use dynamic headers for custom authentication" |
| **Plain `http://` to non-localhost** | v2 runtime refuses to send OAuth credentials to a non-HTTPS token endpoint except `localhost`/`127.0.0.1`/`::1` | needs `--allow-insecure-http` (2.25.5) | CC docs; Vibe changelog 2.25.5 |
| **Tools** | ✔ | ✔ (names `{server}_{tool}`) | both docs |
| **Resources: list/read** | ✔ `ListMcpResourcesTool`/`ReadMcpResourceTool`; `@server:uri` mentions; MCP Apps `ui://` resources hidden from lists (2.1.281) | ✘ (no `list_resources`/`read_resource` call anywhere in `vibe/` or `harness/` client code) | CC docs "Use MCP resources"; Vibe source grep |
| **Resources: templates** | ✔ (`resources/templates/list` deferred to first `@`-mention, 2.1.116, 2026-04 **[re-check]**) | ✘ | CC changelog 2.1.116 |
| **Resources: subscriptions** | ? (v2 holds a `subscriptions/listen` stream for `list_changed`; per-resource `resourceSubscriptions` not documented) | ✘ | CC docs "Notification streams on the v2 runtime"; changelog 2.1.233 |
| **Prompts as slash commands** | ✔ `/servername:promptname (MCP)` or `/mcp__servername__promptname`, arguments split on whitespace | ✘ (no `list_prompts`/`get_prompt` in client code) | CC docs "Use MCP prompts as commands" |
| **Completions (`completion/complete`)** | ? not documented | ✘ | — |
| **`list_changed` notifications** | ✔ tools everywhere; prompts/resources only in interactive sessions (not `-p`/SDK) | ? (manual refresh with `r` in `/mcp`, 2.25.5) | CC docs "Dynamic tool updates"; Vibe changelog |
| **`outputSchema` / `structuredContent`** | ◐ accepted since 2.0.21; validated against `outputSchema`; `outputSchema` **not** shown to the model (#90150 open); when `structuredContent` is present the text block is dropped (#79944 open); on HTTP only the first text block reaches the model (#89630 open); `isError` results drop `structuredContent` (#86032 open) | ◐ legacy loop: if `structuredContent` is present it is returned and the `content` text blocks are ignored, else text blocks are joined with `\n`; non-text blocks are discarded. Unified harness parses `outputSchema` and `annotations` and keeps all content blocks as JSON | CC changelog 2.0.21; issues [#90150](https://github.com/anthropics/claude-code/issues/90150), [#79944](https://github.com/anthropics/claude-code/issues/79944), [#89630](https://github.com/anthropics/claude-code/issues/89630), [#86032](https://github.com/anthropics/claude-code/issues/86032); Vibe tools.py `_parse_call_result`, harness [`_mcp_transport.py`](https://github.com/mistralai/mistral-vibe/blob/main/harness/runtimes/python/python/mistralai_vibe_local_harness/vibe/_mcp_transport.py) |
| **Tool annotations (`readOnlyHint` etc.)** | ◐ shown in `/mcp` view (1.0.44 **[re-check]**); **no effect on permissions** (#87452 closed "not planned"), not passed to hooks (#83886 closed "not planned"), ignored by plan mode (#90058 open). Anthropic uses `_meta` keys instead: `anthropic/requiresUserInteraction`, `anthropic/maxResultSizeChars`, `anthropic/alwaysLoad` | ? parsed into `MCPRemoteToolDescriptor.annotations` in the harness; no documented effect | CC changelog 1.0.44; issues [#87452](https://github.com/anthropics/claude-code/issues/87452), [#83886](https://github.com/anthropics/claude-code/issues/83886), [#90058](https://github.com/anthropics/claude-code/issues/90058); CC docs "Require approval for a specific tool" |
| **Tool `title`** | ✔ displayed in `/mcp` (1.0.44 **[re-check]**); permission prompts name the tool "by its server and readable name" (2.1.295) | ? | CC changelog |
| **Icons** | ? (no mention in docs or changelog) | ? | — |
| **`resource_link` / embedded resources in results** | ✔ `resource_link` since 1.0.44 **[re-check]**; images kept alongside `structuredContent` since 2.1.128 | ✘ in the legacy loop (`_MCPContentBlock` has only `text`); issue [#1189](https://github.com/mistralai/mistral-vibe/issues/1189) "MCP resource block discarded" (open, 2026-10-06); harness imports `ResourceLink`/`EmbeddedResource` | CC changelog; Vibe source and issue |
| **Elicitation: form** | ✔ terminal since 2.1.76 (2026-03-14); `Elicitation`/`ElicitationResult` hooks; **auto-declined** in VS Code extension (#98978), Desktop/Cowork (#96043, #88901, #94450) and SDK `stream-json` (#89858) | ✘ (`ClientSession` is built without `elicitation_callback`) | CC docs "Respond to MCP elicitation requests"; issues listed below; Vibe tools.py lines 157–191, 415–420 |
| **Elicitation: URL** | ✔ on 2026-07-28 connections (2.1.281) and on 2025-11-25 (2.1.287; `bareElicitationCapability: true` fallback); waits for "I'm done, continue" when the server cannot signal completion (2.1.288) | ✘ | CC changelog |
| **Sampling (`sampling/createMessage`)** | ✘ (feature request [#1785](https://github.com/anthropics/claude-code/issues/1785) open) | ✔ `sampling_enabled` default `true` per server; `sampling_callback` on every `ClientSession`; [mcp_sampling.py](https://github.com/mistralai/mistral-vibe/blob/main/vibe/core/tools/mcp_sampling.py) | spec deprecates sampling in 2026-07-28 |
| **Roots** | ✔ `roots/list` returns launch dir plus `--add-dir`; `notifications/roots/list_changed` (2.1.203, 2026-07-07 **[re-check]**) | ? no `list_roots_callback` in the legacy loop; harness `_session.py` mentions roots (not inspected) | CC docs "Service location and roots"; spec deprecates roots |
| **MRTR (`input_required`)** | ◐ via v2 runtime: declares `elicitation: {form: {}, url: {}}` on 2026-07-28 connections | ✘/? (depends on `mcp==1.28.1`; not documented) | CC docs; issue [#88075](https://github.com/anthropics/claude-code/issues/88075) |
| **Tasks extension (`io.modelcontextprotocol/tasks`)** | ? not documented (Claude Code's "background tasks" are client-side) | ? | — |
| **Progress notifications** | ✔ rendered (2.1.153), kept after backgrounding (2.1.283); progress resets the idle timeout | ? (no `progress_callback` found) | CC changelog; env-vars `CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT` |
| **Cancellation** | ◐ user can stop a backgrounded call from `/tasks`; model is told (2.1.295); whether `notifications/cancelled` is sent: not documented | ? | CC changelog |
| **Logging (`notifications/message`)** | ? | ? | — |
| **Output size limit** | 25,000 tokens default (`MAX_MCP_OUTPUT_TOKENS`), warning at 10,000; text results > 50,000 chars persisted to file; per-tool `_meta["anthropic/maxResultSizeChars"]` up to 500,000; error text > ~11,000 chars cut to first 5,000 + last 5,000; HTTP/SSE body cap 16 MB | ? none found for MCP results | CC docs "MCP output limits and warnings"; [env-vars](https://code.claude.com/docs/en/env-vars) |
| **Timeouts** | `MCP_TIMEOUT` 30,000 ms startup; `MCP_TOOL_TIMEOUT` 100,000,000 ms; HTTP per-request 60 s unless raised; idle 5 min HTTP / 30 min stdio (`CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT`); per-server `timeout` (< 1000 ms ignored); auto-background after 2 min; `headersHelper` 10 s | `startup_timeout_sec` default 10; `tool_timeout_sec` default 60 | CC env-vars, docs; Vibe models.py `_MCPBase` |
| **Tool count / descriptions** | no fixed cap; tool search default; descriptions cut at 2,048 chars (4,096 since 2.1.296), 16,384 via tool search; tool names > 128 chars excluded (2.1.292) | `/mcp` crashed with > 128 tools (#1056, closed 2026-10-09: "unified harness ... dynamic tool discovery") | CC docs, changelog; Vibe issue [#1056](https://github.com/mistralai/mistral-vibe/issues/1056) |
| **Tool search / deferred loading** | ✔ default; `ENABLE_TOOL_SEARCH` (`true`/`auto`/`auto:N`/`false`), per-server `alwaysLoad`, per-tool `_meta["anthropic/alwaysLoad"]` | ◐ "dynamic tool discovery" in the unified harness (issue comment only) | CC docs "Scale with MCP tool search" |
| **Permission rules** | `mcp__server__tool` in `allow`/`ask`/`deny`; `mcp__*` glob only in deny/ask; no parentheses in MCP rules; `_meta["anthropic/requiresUserInteraction"]` forces a prompt every call | `[tools.<server>_<tool>] permission = "always" \| "ask" \| "never"`; `enabled_tools`/`disabled_tools` (exact, glob, `re:`); per-server `disabled`, `disabled_tools`; MCP tools "ask before running by default, and remember your approval" (2.25.5) | [CC permissions](https://code.claude.com/docs/en/permissions); Vibe docs, models.py, changelog |
| **Hooks on MCP tools** | ✔ `PreToolUse`/`PostToolUse` matcher `mcp__server__.*`; input carries `mcp_server.name` and `source`; `Elicitation` hooks | ✔ `hooks.toml` `pre_tool`/`post_tool`/`post_agent`; `match` "matches the tool the model actually calls, including ... MCP tools" (2.25.5) | [CC hooks](https://code.claude.com/docs/en/hooks); Vibe README, changelog |
| **Modes** | `default`, `acceptEdits`, `plan`, `auto`, `bypassPermissions`, `dontAsk` | `ask`, `plan`, `accept-edits`, `auto-approve` (`--yolo`), plus "smart approve" (classifier on a fast Mistral model) | CC permissions docs; Vibe README line 136, changelog 2.25.1 |
| **Project-server approval / trust** | ✔ `.mcp.json` servers need approval (`⏸ Pending approval`), `enableAllProjectMcpServers`, `enabledMcpjsonServers`/`disabledMcpjsonServers`, `claude mcp reset-project-choices`, `--strict-mcp-config` | ✔ trusted-folder system; project config loaded only when trusted | CC docs; Vibe README "Trust Folder System" |
| **Client identification** | — | sends `User-Agent: MistralAI-VibeCLI/<version>` on MCP HTTP requests (2.25.5) | Vibe changelog |

### Inferences

- The intersection both clients support without caveat: **tools** over **Streamable HTTP** or **stdio**, **OAuth** (both do DCR-less flows: Claude Code via CIMD or pre-registered client, Vibe via `client_id` or `client_metadata_url`) or a **static `Authorization: Bearer` header**, results as **text content blocks**.
- Anything beyond tools (resources, prompts, elicitation, roots, progress) is Claude-Code-only today. If the server exposes resources or prompts, they are a convenience for Claude Code and must not be the only path to a capability.
- `structuredContent` is a trap on both clients: Claude Code drops the text block when it is present (#79944) and Vibe's legacy loop ignores `content` entirely when it is present. Put everything the model needs into the first text block; if `structuredContent` is sent, make it a faithful duplicate of that text.
- Access logging on the server must assume **at-least-once delivery**: Claude Code re-sends `tools/call` after a mid-call connection drop (#98466), so a non-idempotent tool can run twice without the model noticing. Idempotency keys or server-minted handles belong in the design.
- Neither client acts on `readOnlyHint`/`destructiveHint` for permissions. The one annotation that changes Claude Code's behaviour is Anthropic's `_meta["anthropic/requiresUserInteraction"]`; Vibe has no counterpart, so per-tool permission has to be configured on the client side there.

### Gaps

- The MCP project's client feature matrix at `modelcontextprotocol.io/clients` now redirects to the intro page (`/docs/2026-07-28/getting-started/intro`); I found no maintained client matrix to cite, so every cell above rests on the vendors' own docs, changelogs, source and issues.
- Which protocol revision Vibe negotiates (`mcp==1.28.1`) is not stated anywhere I found; whether it can talk to a 2026-07-28-only (stateless, no `initialize`) server is unverified.
- Claude Code's support for the Tasks extension, `completion/complete`, `notifications/message`, `notifications/cancelled` and tool/server icons is undocumented in the MCP page, the changelog and the issue tracker searches I ran; absence of evidence, not evidence of absence.
- Vibe has no documented MCP result-size limit; the agent loop may truncate large tool results generically ("Tool calls with a very large result ... marked as truncated", changelog line 79) but I found no number.

## Transports and configuration

### Takeaway

Claude Code speaks stdio, Streamable HTTP, legacy SSE and WebSocket and configures servers in `.mcp.json` (project) or `~/.claude.json` (user/local), with managed overrides. Vibe speaks stdio and Streamable HTTP only, configured in TOML under `[[mcp_servers]]` in `.vibe/config.toml` (project) or `~/.vibe/config.toml` (user).

### Cited Findings

- Claude Code transports: "stdio ... HTTP (alias `streamable-http`) ... SSE (Server-Sent Events): Remote servers; deprecated in favor of HTTP ... WebSocket (ws/wss)". WebSocket "supports neither" OAuth nor `claude mcp add --transport`. — [Claude Code MCP docs](https://code.claude.com/docs/en/mcp)
- Claude Code scopes: Local `~/.claude.json` (project entry), Project `.mcp.json`, User `~/.claude.json` (top level), Plugin; precedence local > project > user > plugin > claude.ai connectors > managed. — [MCP docs, "MCP installation scopes"](https://code.claude.com/docs/en/mcp)
- `.mcp.json` supports `${VAR}` and `${VAR:-default}` in `command`, `args`, `env`, `url`, `headers`; credential-named variables (`ANTHROPIC_API_KEY`, `NPM_TOKEN`, names containing TOKEN/SECRET/PASSWORD/KEY/AUTH) read as empty. — same
- Claude Code 2.1.265 (2026-09-08): "Fixed MCP servers configured as `http` that only speak the legacy HTTP+SSE transport never connecting; Claude Code now falls back to SSE as the MCP spec describes". 2.1.274 extended the fallback to 4xx answers. — [CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
- Claude Code v2 runtime: "MCP TypeScript SDK 2.0, which adds MCP protocol revision 2026-07-28"; default on 2.1.232+ with feature flags, 2.1.274+ without; `MCP_SDK_GENERATION=v1|v2`, `MCP_PROTOCOL_NEGOTIATION=auto|legacy`. — [MCP docs, "MCP client runtimes"](https://code.claude.com/docs/en/mcp)
- Claude Code reconnection: remote drops retried with backoff 1 s → 16 s, up to 5 attempts; first-connection failures up to 3; stdio no reconnection; `/mcp reconnect all` (2.1.284+). — same
- Vibe transports: "`http`: Standard HTTP transport; `streamable-http`: HTTP transport with streaming support; `stdio`". — [Vibe README](https://github.com/mistralai/mistral-vibe/blob/main/README.md)
- Vibe maps both `http` and `streamable-http` to the same discovery path, and the only HTTP client import is `from mcp.client.streamable_http import streamable_http_client`. — [registry.py](https://github.com/mistralai/mistral-vibe/blob/main/vibe/core/tools/mcp/registry.py), [tools.py](https://github.com/mistralai/mistral-vibe/blob/main/vibe/core/tools/mcp/tools.py)
- Vibe config layering: "1. Admin config 2. Command-line flags 3. Environment variables 4. Project-level `./.vibe/config.toml` 5. User-level `~/.vibe/config.toml`". — [Vibe docs, configuration](https://docs.mistral.ai/vibe/code/cli/configuration)
- Vibe issue #840 (2026-06-25, open): project `.vibe/config.toml` replaced the `[[mcp_servers]]` array from the user config; last comment points to 2.24.0 "trusted project config overlays user config instead of replacing it" as a possible fix. **[re-check]** — [#840](https://github.com/mistralai/mistral-vibe/issues/840)
- Vibe stdio: issue #590 (2026-04-14, open) reports the stdio process is started for discovery and then stopped, so servers with connection state cannot be used; a `pool.py` module now exists in the MCP package, which I did not verify against the issue. **[re-check]** — [#590](https://github.com/mistralai/mistral-vibe/issues/590)
- Vibe shell commands: `vibe mcp add NAME --url ... --transport streamable-http --api-key-env VAR`, `--header`, `--api-key-header`, `--api-key-format`, `--startup-timeout-sec`, `--tool-timeout-sec`, `--no-login`; under `VIBE_CLI=rust` the shell `mcp add` is OAuth-only. — [Vibe README](https://github.com/mistralai/mistral-vibe/blob/main/README.md)
- Vibe issue #1218 (2026-10-09, open): `vibe mcp add --url` for an **unauthenticated** remote server fails with "the server never issued an OAuth challenge" and the server is then stuck in "needs OAuth authentication". — [#1218](https://github.com/mistralai/mistral-vibe/issues/1218)

### Inferences

- A server that serves Streamable HTTP at one URL works for both clients; a server that offers only SSE works for Claude Code only.
- For Vibe, an unauthenticated remote server is currently awkward to add from the shell (#1218); a static-auth entry in `config.toml` avoids the OAuth path.

### Gaps

- Whether Vibe's `pool.py` keeps stdio processes alive (resolving #590) was not verified.

## Authorization

### Takeaway

Both clients do OAuth with PKCE against a remote server and both accept a static bearer header; Claude Code additionally runs a `headersHelper` script for short-lived credentials. Vibe's published docs page lags its code on OAuth.

### Cited Findings

- Claude Code OAuth: "Dynamic Client Registration ... `/.well-known/oauth-authorization-server` and `/.well-known/oauth-protected-resource`"; pre-configured `--client-id`, `--client-secret`, `--callback-port`; `oauth.scopes`; `authServerMetadataUrl` override; automatic refresh; `claude mcp login/logout`. — [MCP docs](https://code.claude.com/docs/en/mcp)
- Claude Code 2.1.81: "Updated MCP OAuth to support Client ID Metadata Document (CIMD / SEP-991) for servers without Dynamic Client Registration"; 2.1.85: "MCP OAuth now follows RFC 9728 Protected Resource Metadata discovery"; 2.1.196: no longer requests the full `scopes_supported` catalog; 2.1.265: no OAuth client registration until the user actually authenticates; 2.1.288 (2026-10-02): re-authenticate prompt on step-up scope. — [CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
- Claude Code v2 runtime: "Fails an MCP OAuth sign-in whose authorization response names an unexpected issuer" and sends credentials only to HTTPS or loopback token endpoints. — [MCP docs](https://code.claude.com/docs/en/mcp)
- Claude Code `headersHelper`: "Outputs JSON object of string key-value pairs to stdout; Timeout: 10 seconds; Runs fresh on each connection"; env `CLAUDE_CODE_MCP_SERVER_NAME`, `CLAUDE_CODE_MCP_SERVER_URL`; on 401/403 re-runs and retries once (2.1.193); credential env vars stripped (2.1.238). — [MCP docs](https://code.claude.com/docs/en/mcp)
- Vibe OAuth config model: `type = "oauth"`, `scopes: list[str]` ("Pass an empty list to accept the AS default"), `client_id` ("Pre-registered OAuth public client_id (PKCE). Mutually exclusive with client_metadata_url"), `client_metadata_url` ("RFC 9728 client-metadata-document URL"), `redirect_port` default 47823. — [config/models.py](https://github.com/mistralai/mistral-vibe/blob/main/vibe/core/config/models.py)
- Vibe static auth: `headers`, `api_key_env`, `api_key_header` (default `Authorization`), `api_key_format` (default `Bearer {token}`); legacy top-level keys promoted into `[auth]`. — same; [README](https://github.com/mistralai/mistral-vibe/blob/main/README.md)
- Vibe changelog: 2.25.5 "`/mcp login` now recovers when a stored OAuth token refresh fails transiently"; 2.25.6 "`/mcp login` fails loudly when a server never issues an OAuth challenge"; 2.25.8 "MCP OAuth login no longer fails after the browser callback on servers that issue a client secret (e.g. Supabase)"; 2.26.1 (2026-10-09) "A corrupted MCP OAuth token in the keychain no longer crashes Vibe". — [CHANGELOG](https://github.com/mistralai/mistral-vibe/blob/main/CHANGELOG.md)
- Vibe docs page states: "Known limitation: the CLI does not yet support MCP servers that require OAuth authentication. Use the `stdio` or `http` transport with an API key or other static credential." — [docs.mistral.ai MCP servers](https://docs.mistral.ai/vibe/code/cli/mcp-servers); contradicted by the README, the config model and the changelog above.
- Vibe Windows: OAuth token storage fails when the payload exceeds the 2,400-byte Credential Manager limit (#841, 2026-08, open). — [#841](https://github.com/mistralai/mistral-vibe/issues/841)
- MCP 2026-07-28 deprecates RFC 7591 Dynamic Client Registration "in favor of Client ID Metadata Documents". — [MCP changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)

### Inferences

- An authorization server that publishes RFC 9728 protected-resource metadata and accepts CIMD (or a pre-registered public PKCE client) serves both clients without DCR.
- Vibe's `client_metadata_url` field description says "RFC 9728" where CIMD is actually SEP-991; this is a docstring slip, not a behaviour claim.

### Gaps

- Whether Vibe validates the `iss` parameter (RFC 9207) or supports step-up (`insufficient_scope`) re-auth was not found.

## Primitives: tools, resources, prompts, completions

### Takeaway

Claude Code exposes resources (as `@` mentions and as list/read tools) and prompts (as slash commands); Vibe's MCP client calls `list_tools` and `call_tool` and nothing else.

### Cited Findings

- Claude Code resources: "Type `@` in your prompt to see available resources ... Use the format `@server:protocol://resource/path`"; "Claude Code automatically provides tools to list and read MCP resources when servers support them"; MCP Apps UI resources (`ui://` or `text/html;profile=mcp-app`) hidden from lists. — [MCP docs, "Use MCP resources"](https://code.claude.com/docs/en/mcp)
- Claude Code issue #85230 (open, 2026-09): "Background subagents lose ListMcpResourcesTool/ReadMcpResourceTool - MCP resources unreachable from subagents by default"; #80300 (open): `ReadMcpResourceTool` intermittently "not enabled in this context" after reconnect. — [#85230](https://github.com/anthropics/claude-code/issues/85230), [#80300](https://github.com/anthropics/claude-code/issues/80300)
- Claude Code 2.1.292 (2026-10-06): "the first turn no longer waits for HTTP and SSE MCP servers to answer `resources/list`" in `-p`/SDK sessions; 2.1.147: "Fixed paginating MCP servers dropping resources, templates, and prompts past page 1"; 2.1.295: fixed servers that repeat a pagination cursor being asked up to 20 times. — [CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
- Claude Code prompts: "Claude Code lists each MCP prompt as `/servername:promptname (MCP)` ... Claude Code splits the arguments on whitespace, so each argument is a single token"; 2.1.145 names the missing required argument. — [MCP docs, "Use MCP prompts as commands"](https://code.claude.com/docs/en/mcp)
- Claude Code names `anthropic-skills` and `claude-ai` are special-cased for prompts (2.1.282, partly reverted 2.1.283). — [CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
- Claude Code capability discovery sends `tools/list`, `prompts/list`, `resources/list`, retried up to three times on transient errors (2.1.191). — [MCP docs](https://code.claude.com/docs/en/mcp)
- Vibe: `grep -rnlE 'list_resources|list_prompts|read_resource|get_prompt|elicitation_callback|elicit' vibe harness --include='*.py'` matches only `vibe/cli/cli.py` and `vibe/acp/agent.py` (ACP, not MCP). Discovery calls `session.list_tools()` only. — [tools.py](https://github.com/mistralai/mistral-vibe/blob/main/vibe/core/tools/mcp/tools.py) lines 157–162
- Vibe per-server `prompt` field: "Optional usage hint appended to tool descriptions". — [config/models.py](https://github.com/mistralai/mistral-vibe/blob/main/vibe/core/config/models.py)
- MCP 2026-07-28 requires `ttlMs` and `cacheScope` on `tools/list`, `prompts/list`, `resources/list`, `resources/read`, `resources/templates/list` results and asks for deterministic tool order. — [MCP changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)

### Inferences

- Whatever the server offers as a resource or prompt must also be reachable through a tool, or Vibe users cannot reach it at all.
- Claude Code's whitespace-split prompt arguments make multi-word prompt arguments impractical; prompts should take short tokens.

### Gaps

- No evidence either way on `completion/complete` in Claude Code.

## Tool result features: structuredContent, annotations, titles, icons, resource links

### Takeaway

Both clients accept `structuredContent`, and both have result-shaping behaviour that loses content: Claude Code drops the text block when `structuredContent` is present and drops `structuredContent` on errors; Vibe's legacy loop drops the text block when `structuredContent` is present and drops every non-text block always. Standard annotations do not change permissions in either client.

### Cited Findings

- Claude Code 2.0.21: "Support MCP `structuredContent` field in tool responses"; 2.1.128 (2026-05-04): "Fixed MCP tool results dropping images when the server returns both structured content and content blocks". — [CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
- #79944 (open, 2026-07-21, updated 2026-10-08): "When calling an MCP tool whose response includes both a `structuredContent` block ... and a `content` text block ..., Claude Code appears to surface only the structured block and silently drops the text block"; same tool returns the full body in Cursor. — [#79944](https://github.com/anthropics/claude-code/issues/79944)
- #89630 (open, 2026-08-25, updated 2026-10-08): on HTTP transport "only the first [text] block is surfaced to the model. The remaining text blocks are silently dropped"; reproduced on 2.1.233 and 2.1.245 with Outline's `fetch` tool. — [#89630](https://github.com/anthropics/claude-code/issues/89630)
- #86032 (open, 2026-08-12): "When an MCP tool returns `isError: true`, Claude Code renders only `content[0].text` and does not surface `structuredContent`"; second reproduction on 2.1.260. — [#86032](https://github.com/anthropics/claude-code/issues/86032)
- #90150 (open, 2026-08-27): "Claude Code parses [`outputSchema`] and uses it internally (it caches a validator per tool and enforces that a tool declaring an output schema returns matching `structuredContent`), but the tool definition presented to the model contains only `name`, `description`, and `input_schema`." — [#90150](https://github.com/anthropics/claude-code/issues/90150)
- #88988 (open, 2026-08): "Filesystem MCP server ... fails all tool calls: outputSchema declares unsupported draft-07 dialect". — [#88988](https://github.com/anthropics/claude-code/issues/88988)
- #78762 (open, 2026-09): "MCP client transport loses precision on integers > 2^53"; Vibe #1138 (open, 2026-09-24): turn crashes with `rfc8785._impl.IntegerDomainError` on integers outside ±2^53. — [#78762](https://github.com/anthropics/claude-code/issues/78762), [#1138](https://github.com/mistralai/mistral-vibe/issues/1138)
- Claude Code input schemas: top-level property names 1–64 chars of `[A-Za-z0-9_.-]`; schema must validate against JSON Schema 2020-12 meta-schema when no `$schema` or 2020-12 is declared; root-level `anyOf`/`oneOf`/`allOf` is flattened and described in the tool description (since 2.1.216). — [MCP docs, "Tools with invalid input schemas"](https://code.claude.com/docs/en/mcp)
- Claude Code annotations: 1.0.44 "MCP: tool annotations and tool titles now display in /mcp view"; "MCP: resource_link tool results are now supported". — [CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md) **[re-check]**
- #87452 "Permission engine should process MCP ToolAnnotations hints (readOnlyHint, destructiveHint, etc.)" closed **NOT_PLANNED** 2026-09-21; #83886 "Surface MCP tool annotations ... in PreToolUse hook input" closed **NOT_PLANNED** 2026-10-06; #90058 (open) plan mode prompts for an allow-listed read-only MCP tool. — [#87452](https://github.com/anthropics/claude-code/issues/87452), [#83886](https://github.com/anthropics/claude-code/issues/83886), [#90058](https://github.com/anthropics/claude-code/issues/90058)
- Claude Code vendor `_meta` keys on `tools/list` entries: `anthropic/requiresUserInteraction: true` ("shows that tool's permission prompt on every call, even in `acceptEdits`, `auto`, and `bypassPermissions` ... doesn't offer a 'don't ask again' option"; denied in `dontAsk`; denied under `--permission-prompt-tool`), `anthropic/maxResultSizeChars` (≤ 500,000), `anthropic/alwaysLoad`. — [MCP docs](https://code.claude.com/docs/en/mcp)
- Claude Code 2.1.246: `requiresUserInteraction` tools no longer offer "Yes, and don't ask again". — [CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
- Vibe legacy loop result parsing: `_MCPResultIn` has `structuredContent` and `content: list[_MCPContentBlock]` where `_MCPContentBlock` has only `text`; `_parse_call_result` returns `structured` when present, else `"\n".join(text parts)`. — [tools.py](https://github.com/mistralai/mistral-vibe/blob/main/vibe/core/tools/mcp/tools.py) lines 91–125
- Vibe unified harness: `_normalize_result` keeps every content block as a JSON object; descriptors carry `output_schema` and `annotations`. — [_mcp_transport.py](https://github.com/mistralai/mistral-vibe/blob/main/harness/runtimes/python/python/mistralai_vibe_local_harness/vibe/_mcp_transport.py)
- Vibe #1189 (open, 2026-10-06, Vibe Work): GitHub connector `get_file_contents` returns only "successfully downloaded text file (SHA...)"; the resource block with the content is discarded. — [#1189](https://github.com/mistralai/mistral-vibe/issues/1189)
- MCP 2026-07-28 loosens `inputSchema`/`outputSchema` to any JSON Schema 2020-12 keywords and `structuredContent` to any JSON value. — [MCP changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)

### Inferences

- The safe result shape for both clients: exactly one text content block carrying everything; `structuredContent` optional and redundant; no reliance on embedded resources or `resource_link` for data the model must see; integers kept below 2^53 (use strings for 64-bit IDs); input schemas with ASCII property names and draft 2020-12.
- Errors: put the diagnostic detail into the text of the `isError` result; `structuredContent` on errors is invisible in Claude Code.
- Access control cannot be delegated to `readOnlyHint`; the server enforces it and the client's per-tool permission is a second, user-side layer.

### Gaps

- Whether Vibe's harness shows `structuredContent` or the content blocks to the model when both are present was not traced past `_normalize_result`.
- Icons (`icons` on tools/servers) are unmentioned in both clients.

## Client features: elicitation, sampling, roots, MRTR, tasks, progress, cancellation, logging

### Takeaway

Claude Code does elicitation (form and URL) in the terminal, roots and progress, but no sampling; Vibe does sampling and nothing else from this list. The 2026-07-28 revision deprecates roots, sampling and logging, which narrows what a new server should depend on.

### Cited Findings

- Claude Code 2.1.76 (2026-03-14): "Added MCP elicitation support — MCP servers can now request structured input mid-task via an interactive dialog (form fields or browser URL)". **[re-check]** — [CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
- Claude Code docs: "On connections that use protocol revision 2026-07-28, Claude Code declares `elicitation: {form: {}, url: {}}` in its client capabilities"; `Elicitation` hook can auto-respond. — [MCP docs](https://code.claude.com/docs/en/mcp)
- 2.1.281 (2026-09-23): URL-mode elicitation on 2026-07-28; 2.1.287 (2026-10-01): URL prompts on 2025-11-25, with `"bareElicitationCapability": true` as a compatibility switch; 2.1.288: waits for "I'm done, continue". — [CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
- Elicitation surfaces that auto-decline (all open): VS Code extension #98978 (2.1.287), Desktop #96043, Cowork #94450 and #94806 ("2026-07-28 MRTR ... tool call hangs 180s"), embedded #88901, SDK `--input-format stream-json` #89858. — [#98978](https://github.com/anthropics/claude-code/issues/98978), [#96043](https://github.com/anthropics/claude-code/issues/96043), [#94450](https://github.com/anthropics/claude-code/issues/94450), [#94806](https://github.com/anthropics/claude-code/issues/94806), [#88901](https://github.com/anthropics/claude-code/issues/88901), [#89858](https://github.com/anthropics/claude-code/issues/89858)
- Claude Code: "A call waiting on an open elicitation dialog isn't backgrounded". — [MCP docs](https://code.claude.com/docs/en/mcp)
- Claude Code sampling: #1785 "[Feature Request] Support for MCP Sampling" open (updated 2026-08-17); no changelog or docs entry mentions MCP sampling. — [#1785](https://github.com/anthropics/claude-code/issues/1785)
- Claude Code roots: "`roots/list` MCP request: Returns session's launch directory + all `--add-dir` directories; Notification: `notifications/roots/list_changed` when set changes (v2.1.203+)". — [MCP docs](https://code.claude.com/docs/en/mcp)
- Claude Code progress: 2.1.153 "Fixed MCP tool progress notifications not rendering in the collapsed tool view"; 2.1.283 "Fixed MCP progress notifications being discarded once a long-running tool call moved to the background"; `CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT` aborts when the server "sends no response and no progress notification for this long". — [CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md); [env-vars](https://code.claude.com/docs/en/env-vars)
- Claude Code cancellation: 2.1.295 "Fixed Claude not being told when you stop a long-running MCP tool call from the tasks panel or a connected client". — [CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
- Vibe sampling: `_MCPBase.sampling_enabled: bool = True` ("Allow this MCP server to request LLM completions via sampling/createMessage"); `ClientSession(..., sampling_callback=sampling_callback)` for HTTP and stdio. — [config/models.py](https://github.com/mistralai/mistral-vibe/blob/main/vibe/core/config/models.py), [tools.py](https://github.com/mistralai/mistral-vibe/blob/main/vibe/core/tools/mcp/tools.py)
- Vibe elicitation: no `elicitation_callback` is passed to any `ClientSession`; the only `elicitation` hits are in the ACP agent and tests. — source grep, see above
- MCP 2026-07-28: "Deprecate the Roots, Sampling, and Logging features (SEP-2577) ... Suggested migrations: pass directories or files via tool parameters, resource URIs, or server configuration instead of Roots; integrate directly with LLM provider APIs instead of Sampling; log to `stderr` (stdio) or use OpenTelemetry instead of Logging." Tasks moved to extension `io.modelcontextprotocol/tasks` with `tasks/get` polling and `tasks/update`. MRTR: "Servers return an `InputRequiredResult` (`resultType: "input_required"`) ... Clients respond with `inputResponses` on a retry of the original request." — [MCP changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)

### Inferences

- Elicitation is usable only in Claude Code's terminal UI; a consent step that *must* reach a human is better modelled as a tool with `anthropic/requiresUserInteraction` for Claude Code and as an `ask`-permission tool in Vibe, with the server refusing until the grant exists.
- Sampling would work in Vibe only and is deprecated; not a design basis.
- Progress notifications pay off in Claude Code for long calls (they keep the idle timeout alive); Vibe gives no evidence it reads them, and its 60 s default tool timeout is the binding limit there.

### Gaps

- Tasks extension: no client evidence either way.
- Whether Claude Code sends `notifications/cancelled` to the server when the user stops a call is undocumented.

## Limits: output size, timeouts, tool counts, tool search

### Takeaway

Claude Code's numbers are documented and tunable (25k tokens / 50k chars per result, 16 MB per HTTP body, 60 s per HTTP request unless raised, 2 min to background); Vibe documents only two timeouts (10 s startup, 60 s per tool) and no result-size limit.

### Cited Findings

- Claude Code: "Output warning threshold ... 10,000 tokens ... `MAX_MCP_OUTPUT_TOKENS` ... default maximum is 25,000 tokens"; results over the limit "saves it to a file and replaces it ... with a message that names the file path"; "Character limit for text results ... longer than 50,000 characters"; "Error text longer than about 11,000 characters keeps only its first 5,000 and last 5,000"; HTTP/SSE "once one JSON response body, or one event of an event stream, passes 16 MB after decompression ... The request ... fails". — [MCP docs, "MCP output limits and warnings"](https://code.claude.com/docs/en/mcp)
- `_meta["anthropic/maxResultSizeChars"]` per tool "up to a hard ceiling of 500,000 characters" (2.1.91, 2026-04-02 **[re-check]**). — same; [CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
- Claude Code timeouts: `MCP_TIMEOUT` "Timeout in milliseconds for MCP server startup (default: 30000)"; `MCP_TOOL_TIMEOUT` "default: 100000000, about 28 hours ... For an HTTP, SSE, or claude.ai connector server, each request also times out after 60 seconds by default; set this variable, or the per-server `timeout`, above 60000 to raise that per-request limit"; `CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT` "Overrides the per-transport defaults of 300000 (5 minutes)" for HTTP and 30 minutes for stdio; `MCP_CONNECT_TIMEOUT_MS` default 5000. — [env-vars](https://code.claude.com/docs/en/env-vars); [MCP docs](https://code.claude.com/docs/en/mcp)
- Claude Code per-server `"timeout"` in ms; values below 1000 ignored (2.1.162). Streamable HTTP calls timing out at ~5 min despite a longer `timeout` was fixed in 2.1.274. — [CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
- Claude Code backgrounding: "Tool calls in main conversation running > 2 minutes move to background"; `CLAUDE_CODE_MCP_AUTO_BACKGROUND_MS`; never in subagents, IDE servers, or non-interactive mode unless `CLAUDE_AUTO_BACKGROUND_TASKS=1`. — [MCP docs](https://code.claude.com/docs/en/mcp)
- Claude Code tool count: "Claude Code doesn't impose a fixed per-server tool cap; the practical limit is your context window budget"; descriptions and server instructions "truncates ... at 2,048 characters by default" (`CLAUDE_CODE_MAX_MCP_DESCRIPTION_LENGTH`, 2.1.280+); 2.1.296 (2026-10-09) raised the default to 4,096; tool search loads descriptions up to 16,384 (2.1.295); tool names over 128 characters are left out (2.1.292). — [MCP docs](https://code.claude.com/docs/en/mcp); [CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
- Claude Code tool search: "Tool search is enabled by default: MCP tools are deferred and discovered on demand"; off when `ANTHROPIC_BASE_URL` is non-first-party; `ENABLE_TOOL_SEARCH` values `true`, `auto` (10 % threshold), `auto:N`, `false`; needs Claude Sonnet 4.5/Haiku 4.5/Opus 4.5 or later; `alwaysLoad` per server (startup waits up to 5 s), `anthropic/alwaysLoad` per tool. "Server instructions help Claude understand when to search for your tools". — [MCP docs, "Scale with MCP tool search"](https://code.claude.com/docs/en/mcp)
- Vibe timeouts: `startup_timeout_sec` default 10.0, `tool_timeout_sec` default 60.0. — [config/models.py](https://github.com/mistralai/mistral-vibe/blob/main/vibe/core/config/models.py)
- Vibe tool count: #1056 "Vibe crashes on MCP with >128 tools" (2.24.5) closed as completed 2026-10-09; maintainer comment: "with the new unified harness used in vibe it is already doing dynamic tool discovery". — [#1056](https://github.com/mistralai/mistral-vibe/issues/1056)
- Vibe global and per-server filters: `enabled_tools`/`disabled_tools` globs "now apply to MCP tools, not just connector tools" (2.25.5). — [CHANGELOG](https://github.com/mistralai/mistral-vibe/blob/main/CHANGELOG.md)

### Inferences

- A tool that may take longer than 60 s needs the client to raise a limit on both sides (`tool_timeout_sec` in Vibe; per-server `timeout` or `MCP_TOOL_TIMEOUT` in Claude Code); better to design calls to finish well under a minute and page results.
- Keep tool descriptions under ~2,000 characters and front-load the important part; keep per-result text under 50,000 characters or declare `anthropic/maxResultSizeChars`.
- Server `instructions` matter for Claude Code's tool search; Vibe appends the per-server `prompt` to tool descriptions instead.

### Gaps

- No Vibe result-size limit or truncation rule for MCP results found in source or docs.

## Permissions and safety: allowlists, per-tool approval, hooks, managed settings

### Takeaway

Both clients gate MCP tools per tool with an allow/ask/deny model, both run shell hooks before and after tool calls, and both have an organisation layer. Only Claude Code lets the server itself force a prompt (`anthropic/requiresUserInteraction`).

### Cited Findings

- Claude Code rule syntax: `mcp__server__tool`; "When Claude Code loads a settings file, it skips any `mcp__` rule that has parentheses"; deny/ask accept globs, "`mcp__*` matches every MCP tool across all servers"; allow rules reject non-MCP globs (2.1.166). — [permissions](https://code.claude.com/docs/en/permissions); [CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
- Claude Code `dontAsk` mode denies `requiresUserInteraction` tools and organisation-`ask` connector tools "even if you've allowed them". — [permissions](https://code.claude.com/docs/en/permissions)
- Claude Code hooks: matcher "`mcp__memory__.*` matches every tool from the `memory` server"; a bare `mcp__memory` matches nothing; plugin servers use `mcp__plugin_<plugin>_<server>__<tool>`; hook input carries `mcp_server` with `name` and `source`; `Elicitation`/`ElicitationResult` hooks keyed by server name, can `accept`/`decline`/`cancel` and fill `content`. — [hooks](https://code.claude.com/docs/en/hooks)
- Claude Code project approval: `.mcp.json` servers prompt in interactive sessions; `claude -p`, SDK and cloud sessions "loads project-scoped servers without asking"; `--strict-mcp-config`; `enableAllProjectMcpServers`, `enabledMcpjsonServers`, `disabledMcpjsonServers`; `claude mcp reset-project-choices`. — [MCP docs](https://code.claude.com/docs/en/mcp)
- Claude Code managed: `managedMcpServers` (HTTP/SSE only; command entries skipped, 2.1.259), `allowedMcpServers`/`deniedMcpServers` by name or `serverUrl` pattern, `managed-mcp.json` "overrides everything", `allowManagedMcpServersOnly`, `disableClaudeAiConnectors`; organisation connector tools can be `ask` or `blocked`. — [MCP docs](https://code.claude.com/docs/en/mcp)
- Claude Code: stdio servers receive `CLAUDE_CODE_SESSION_ID` and `CLAUDECODE=1` (2.1.154); `CLAUDE_PROJECT_DIR` is set; servers should prefer `roots/list`. — [CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md); [MCP docs](https://code.claude.com/docs/en/mcp)
- Vibe per-tool: `[tools.{server_name}_{tool_name}]` with `permission = "always"` or `"ask"`; `ToolPermission` enum `ALWAYS`, `NEVER`, `ASK`; 2.26.0 "a tool set to `permission = "never"` now denies a sensitive path instead of prompting". — [docs MCP servers](https://docs.mistral.ai/vibe/code/cli/mcp-servers); [tools/models.py](https://github.com/mistralai/mistral-vibe/blob/main/vibe/core/tools/models.py); [CHANGELOG](https://github.com/mistralai/mistral-vibe/blob/main/CHANGELOG.md)
- Vibe 2.25.5: "MCP and connector tool calls now respect the permission system: they honor each tool's configured permission, ask before running by default, and remember your approval for later calls"; 2.25.1: "Approve for session" on an MCP tool "covers the whole tool instead of the exact arguments". — [CHANGELOG](https://github.com/mistralai/mistral-vibe/blob/main/CHANGELOG.md)
- Vibe modes: `ask`, `plan`, `accept-edits`, `auto-approve` (`--auto-approve`/`--yolo` "Approves all tool calls without prompting"); "smart approve" runs a classifier "on the fast Mistral model regardless of the session's active model" and escalates to a prompt after a streak of risky calls. — [README](https://github.com/mistralai/mistral-vibe/blob/main/README.md); [CHANGELOG](https://github.com/mistralai/mistral-vibe/blob/main/CHANGELOG.md) 2.25.1, 2.25.4
- Vibe hooks: `.vibe/hooks.toml` / `~/.vibe/hooks.toml`, `type = "pre_tool" | "post_tool" | "post_agent"`, `match`, `command`, `timeout`; `match` covers MCP tools (2.25.5). — [README](https://github.com/mistralai/mistral-vibe/blob/main/README.md); [CHANGELOG](https://github.com/mistralai/mistral-vibe/blob/main/CHANGELOG.md)
- Vibe `enabled_tools`/`disabled_tools` "support exact names, glob patterns, and regex with the `re:` prefix", e.g. `disabled_tools = ["mcp_*", "grep"]`. — [docs configuration](https://docs.mistral.ai/vibe/code/cli/configuration)
- Vibe trust: "When you first run Vibe in a new directory which contains a `.vibe` subfolder, it may ask you to confirm whether you trust the folder"; `~/.vibe/trusted_folders.toml`. — [README](https://github.com/mistralai/mistral-vibe/blob/main/README.md)

### Inferences

- The server cannot rely on the client to ask a human; in Vibe `--yolo` approves every MCP call, in Claude Code `bypassPermissions` approves everything except `requiresUserInteraction` tools. Server-side enforcement plus server-side access logging is the only layer that holds on both.

### Gaps

- Vibe's admin config layer: I found the changelog line (2.24.0) but no documentation of its file location or of MCP-specific allow/deny lists.

## Known bugs and gaps that affect a server design

### Takeaway

The open issues cluster around result delivery (content dropped), delivery guarantees (duplicate calls), elicitation outside the terminal, and integer precision.

### Cited Findings

- Claude Code #98466 (open, 2026-09-30): after `MCP error -32000: Connection closed` mid-call on Streamable HTTP, Claude Code "re-initializes, and re-sends the same tool call ... the retry ran it a second time"; the model saw one `tool_use`. — [#98466](https://github.com/anthropics/claude-code/issues/98466)
- Claude Code result-content issues #79944, #89630, #86032, #90150 (all open, see above).
- Claude Code #99677 (open, 2026-10-07): MCP App widgets lose the tool result's `_meta` on reload; #88370 (open): MCP Apps widgets stopped rendering after `server/discover` negotiation rollout (2.1.234). — [#99677](https://github.com/anthropics/claude-code/issues/99677), [#88370](https://github.com/anthropics/claude-code/issues/88370)
- Claude Code #96934 (open, 2026-09-30): "VS Code: MCP permission prompts show only the tool name, not what the call does". — [#96934](https://github.com/anthropics/claude-code/issues/96934)
- Claude Code #14353 (open): "MCP tools running sequentially instead of in parallel". — [#14353](https://github.com/anthropics/claude-code/issues/14353)
- Claude Code #89643 (open, 2026-10-08): feature request to keep a server's tools while excluding its resources from the `@` picker. — [#89643](https://github.com/anthropics/claude-code/issues/89643)
- Vibe #683 (open, 2026-05 **[re-check]**): tools visible in `/mcp` but "command not found" after `/resume`; #779 (open, 2026-08): VS Code extension "hardcodes mcpServers: [], ignoring project MCP config"; #966 (open): `/mcp login <connector>` "Unknown MCP server"; #1172: an image attachment poisons a session when the model cannot read images. — [#683](https://github.com/mistralai/mistral-vibe/issues/683), [#779](https://github.com/mistralai/mistral-vibe/issues/779), [#966](https://github.com/mistralai/mistral-vibe/issues/966), [#1172](https://github.com/mistralai/mistral-vibe/issues/1172)
- Vibe 2.26.0: "Resuming a session imported from an older Vibe version no longer fails when its transcript carries embedded resource blocks". — [CHANGELOG](https://github.com/mistralai/mistral-vibe/blob/main/CHANGELOG.md)
- Vibe 2.25.5: Vibe sends `User-Agent: MistralAI-VibeCLI/<version>` on MCP HTTP requests. — same

### Inferences

- Server-side access logs should record a request identifier the server mints and return it in the result text, so a duplicate execution is detectable afterwards (#98466); write tools should accept an idempotency key.
- The `User-Agent` header lets the server tell Vibe from Claude Code in its access log; Claude Code's own `clientInfo` (name/version in `initialize` or `_meta` on 2026-07-28) is the counterpart, not verified here.

### Gaps

- I did not verify what `clientInfo.name` Claude Code sends.

## Mistral Vibe: what it is

### Takeaway

Mistral Vibe is Mistral AI's open-source (Apache-2.0) coding agent: a Python/Textual terminal CLI (`mistral-vibe` on PyPI), an optional Rust TUI front-end over the same Python app-server, an ACP agent for editors, a VS Code extension, plus hosted "Vibe Code Web" and "Vibe Work"; it defaults to Mistral's API but accepts any OpenAI-compatible provider.

### Cited Findings

- "Mistral's open-source CLI coding assistant"; license Apache 2.0, "Copyright 2025 Mistral AI"; install `curl -LsSf https://mistral.ai/vibe/install.sh | bash`, `uv tool install mistral-vibe`, `pip install mistral-vibe`. — [README](https://github.com/mistralai/mistral-vibe/blob/main/README.md)
- Package `mistral-vibe` version 2.26.1, `requires-python >= 3.12`, `mcp==1.28.1`, `textual==8.2.8`. — [pyproject.toml](https://github.com/mistralai/mistral-vibe/blob/main/pyproject.toml)
- Vibe 2.0 was released 2026-01-27 with "custom subagents, multi-choice clarifications, slash-command skills, unified agent modes", powered by the Devstral 2 model family; "available on Le Chat Pro and Team plans — with pay-as-you-go credits for power use, or bring your own API key". — [Mistral news, Vibe 2.0](https://mistral.ai/news/mistral-vibe-2-0) (primary page not fetched directly; summarised via [The Decoder](https://the-decoder.com/mistral-ai-launches-terminal-based-coding-agent-vibe-2-0/) and [VentureBeat](https://venturebeat.com/technology/a-european-ai-challenger-goes-after-github-copilot-mistral-launches-vibe-2-0))
- Vibe 2.0 "added custom subagents, slash-command skills, Model Context Protocol (MCP) support". — [vibecodinghub review](https://vibecodinghub.org/tools/mistral-vibe) (secondary source)
- Model backends: docs list nine Mistral models with "Mistral Medium 3.5 (recommended)" (`mistral-medium-latest`), Codestral, Mistral Large 3, Ministral 3B–14B; third-party via a custom provider with `api_base`, `api_key_env_var`, `api_style`, `backend = "generic"` (OpenRouter example). — [docs configuration](https://docs.mistral.ai/vibe/code/cli/configuration); `ProviderConfig.api_style = "openai"`, `backend: Backend = Backend.GENERIC` in [config/models.py](https://github.com/mistralai/mistral-vibe/blob/main/vibe/core/config/models.py)
- Changelog references to non-Mistral providers: 2.25.1 smart approve fix for "a session on another model (e.g. a non-Mistral provider)"; issue #1092 "unable to call tool when switching to venice/deepseek-v4-flash-0731". — [CHANGELOG](https://github.com/mistralai/mistral-vibe/blob/main/CHANGELOG.md); [#1092](https://github.com/mistralai/mistral-vibe/issues/1092)
- Rust CLI: "`VIBE_CLI=rust vibe` starts the Rust TUI"; ADR 0016: "The Rust `vibe-rs` binary is a delivery surface for Vibe, parallel to the Python Textual CLI ... a thin client over the Python `vibe-app-server` ... connected by newline-delimited JSON-RPC 2.0 on stdio. It never imports Python internals or duplicates the agent runtime." — [README](https://github.com/mistralai/mistral-vibe/blob/main/README.md); [ADR 0016](https://github.com/mistralai/mistral-vibe/blob/main/docs/adr/0016-rust-cli-delivery-surface.md)
- Two session backends: ADR 0011 names `harness_kind` "`legacy` for the legacy `AgentLoop` adapter and `unified` for the Unified Harness"; the 2.26.1 changelog refers to `--experimental-harness` turns. — [ADR 0011](https://github.com/mistralai/mistral-vibe/blob/main/docs/adr/0011-unified-harness-backend.md); [CHANGELOG](https://github.com/mistralai/mistral-vibe/blob/main/CHANGELOG.md)
- ACP: "Mistral Vibe can be used in text editors and IDEs that support Agent Client Protocol". — [README](https://github.com/mistralai/mistral-vibe/blob/main/README.md); [docs/acp-setup.md](https://github.com/mistralai/mistral-vibe/blob/main/docs/acp-setup.md)
- Other surfaces named in the changelog and issues: "Vibe Code Web" (`/teleport`, 2.26.0), "Vibe Work" (#1189), VS Code extension (#779, 2.25.5 `/loop` panel), "Studio" connectors and a "Document Library connector" (2.26.1). — [CHANGELOG](https://github.com/mistralai/mistral-vibe/blob/main/CHANGELOG.md)
- Non-interactive use: `vibe -p` with `--prompt-file`, `--output-dir` (writes `export.json`), `--time-limit`, `--auto-approve`. — [README](https://github.com/mistralai/mistral-vibe/blob/main/README.md); [CHANGELOG](https://github.com/mistralai/mistral-vibe/blob/main/CHANGELOG.md) 2.26.1

### Inferences

- How Vibe differs from Claude Code for an MCP server author: open source and inspectable (the matrix cells for Vibe come from reading the client code, which is impossible for Claude Code); model-agnostic (any OpenAI-style endpoint), so the server cannot assume a specific model's tool-use quality; tools-only MCP; sampling on, elicitation off; TOML config with per-tool permission keyed by `{server}_{tool}`; two runtimes (legacy loop vs unified harness) with different result handling, so behaviour depends on which the user runs.
- Because Vibe pins `mcp==1.28.1`, its protocol behaviour tracks the Python SDK release train, not Mistral's own schedule.

### Gaps

- Whether the unified harness or the legacy loop is the default in 2.26.1 is not stated in the README or changelog I read; the `--experimental-harness` flag name suggests the legacy loop is still default, but that is an inference.
- The exact protocol revision implemented by `mcp` 1.28.1 was not looked up.
