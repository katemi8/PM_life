# MCP Servers

Этот документ описывает, какие MCP-серверы входят в `TA-agent-system` и как агент должен с ними работать.

Основной читатель: агент, который устанавливает repo в workspace PM.

## Status

Active v0 rule.

`TA-agent-system` хранит project-local MCP server code, если сервер нужен для рабочих skills и не является hosted внешним сервисом.

Репозиторий хранит:

- код project-local MCP-серверов;
- безопасные example-конфиги;
- инструкции подключения;
- expected tool names.

Репозиторий не хранит:

- реальные токены;
- browser cookies;
- `.mcp.json` с локальной пользовательской конфигурацией;
- `.claude/local/*`;
- raw transcripts.

## Servers

### KTalk / Контур.Толк

Project-local server:

```text
.mcp/ktalk-readonly/server.py
```

Local config template:

```text
.mcp/ktalk-readonly/ktalk-session.example.json
```

Local MCP config template:

```text
.mcp.example.json
```

PM creates local ignored files:

```text
.mcp.json
.claude/local/ktalk-session.json
```

Expected server name: `ktalk`.

Expected read tools:

- `ktalk_list_recordings`;
- `ktalk_get_recording`;
- `ktalk_get_transcript`;
- `ktalk_get_summary`;
- `ktalk_get_summary_by_type`;
- `ktalk_list_calendar_events`.

Guarded write tools may exist in the server, but product-context extraction skills remain read-only in current v0 unless a separate meeting-scheduling workflow explicitly uses the guarded approval flow.

### RAG Gateway

Project-local server:

```text
.mcp/rag-gateway/server.js
```

Local config: two secrets passed through the MCP client `env` block (or an
ignored local `.env` next to `server.js`):

```text
RAG_GATEWAY_TOKEN
N8N_API_KEY
```

See the `rag_gateway` entry in `.mcp.example.json` and `.mcp/rag-gateway/.env.example`.
Request both tokens from **Александр Фенин** (@afenin). Never commit real tokens.

Expected server name: `rag_gateway`.

Expected tools:

- `research_confirm_hypothesis` — validate a product hypothesis against the research-evidence base;
- `research_exploratory_slice` — explore a topic as thematic evidence clusters;
- `research_search_evidence` — raw Qdrant evidence retrieval with metadata filters (not the default);
- `research_data_query` — read-only SQL analytics over the real-estate catalog warehouse (Postgres `mongosync`);
- `research_get_result` — fetch a pending async result by `execution_id`.

The server talks to the async n8n «RAG MCP Gateway» workflow and polls the n8n
Executions API until the pipeline finishes. `research_data_query` runs guarded
read-only SQL (SELECT/WITH only, statement timeout, row cap, granted-tables
subset). Canonical upstream: `gitverse.ru/afenin/trendtech-rag-bot-mcp`.

### Notion

Notion uses the official hosted MCP:

```text
https://mcp.notion.com/mcp
```

There is no Notion server code to vendor into this repo in v0. The project stores Notion MCP setup instructions in `docs/notion-mcp.md` and installation flow in `skills/agent-system-install/SKILL.md`.

Expected server name: `notion`.

Expected tools:

- `notion_fetch`;
- `notion_query_database_view`;
- `notion_search`.

## Install Contract

During first run, the agent must:

1. Verify `.mcp/ktalk-readonly/server.py` exists.
2. Verify `.mcp.example.json` exists.
3. Help PM create local ignored `.mcp.json` from `.mcp.example.json` if `ktalk` is not configured.
4. Help PM create `.claude/local/ktalk-session.json` from `.mcp/ktalk-readonly/ktalk-session.example.json`.
5. Ask PM to put credentials only into local config, not chat and not committed files.
6. Run KTalk config/preflight checks.
7. Report KTalk status as ready, partial or blocked.

If Notion is needed, the agent must configure the hosted Notion MCP through Codex MCP commands and OAuth, not by creating a local Notion server.
