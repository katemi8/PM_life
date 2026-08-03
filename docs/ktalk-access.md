# KTalk MCP Access

Этот документ описывает, как PM подключает KTalk / Контур.Толк для работы skills.

Основной читатель: агент и PM, который устанавливает систему в своем workspace.

## Status

Active v0 access rule.

`TA-agent-system` хранит project-local KTalk MCP server code, но не хранит KTalk credentials, не поставляет общий KTalk account и не коммитит локальные настройки доступа.

## Access Model

KTalk access goes through the project-local MCP server included in this repo.

Supported v0 model:

- repo contains KTalk MCP server code in `.mcp/ktalk-readonly/server.py`;
- PM creates local `.mcp.json` from `.mcp.example.json`;
- PM creates local `.claude/local/ktalk-session.json` from `.mcp/ktalk-readonly/ktalk-session.example.json`;
- expected MCP server name: `ktalk`;
- PM uses their own KTalk account/access through that MCP server;
- any browser session, token or adapter credential is managed only inside local ignored config;
- agent uses KTalk only through the configured MCP server;
- agent must not print, commit, request or paste `sessionToken`.

The shared repo contains MCP server code and safe examples. It must not contain:

- `sessionToken`;
- bearer tokens;
- copied browser storage;
- `.env` with real credentials;
- `.mcp.json` with local user config;
- `.claude/local/*`;
- raw transcripts.

## Setup Flow

During installation or first run, agent must guide PM through KTalk MCP setup until the preflight succeeds or the missing access is clearly reported.

1. Agent verifies that `.mcp/ktalk-readonly/server.py` exists.
2. Agent checks whether MCP server `ktalk` is already available.
3. If it is missing, agent guides PM to create local ignored `.mcp.json` from `.mcp.example.json`.
4. Agent guides PM to create `.claude/local/ktalk-session.json` from `.mcp/ktalk-readonly/ktalk-session.example.json`.
5. PM completes local authentication/configuration without pasting credentials into chat.
6. If the server needs a browser/session token, PM enters it only into `.claude/local/ktalk-session.json`.
7. PM restarts the local agent/tool session if required.
8. Agent runs a read-only KTalk preflight.
9. Agent reports whether KTalk meeting workflows are ready.

This repo must not document or store a shared token. If the MCP server needs a browser session or token, that value belongs only in local ignored PM config.

## Agent-Guided First Run

When installing this project for a PM, agent must run this guided flow:

```text
1. Проверю, доступен ли KTalk MCP server.
2. Если сервер не подключен, настрою локальный `.mcp.json` по шаблону `.mcp.example.json`.
3. Создайте `.claude/local/ktalk-session.json` по шаблону `.mcp/ktalk-readonly/ktalk-session.example.json`.
4. Вставьте token только в локальный config. Не отправляйте token в чат.
5. После подключения я сделаю read-only проверку: metadata + summary/transcript access.
```

Agent must not continue a KTalk-dependent workflow until it has one of these outcomes:

- `ready`: KTalk MCP server is available and the requested meeting/source can be read;
- `partial`: metadata is available, but summary/transcript is unavailable;
- `blocked`: MCP server is missing, auth is expired, permission is missing, or source cannot be found.

If status is `blocked`, agent should explain the exact missing step and stop the KTalk part of the workflow.

## Required MCP Capabilities

The KTalk MCP server should support read-only operations needed by skills:

- search meetings by title/date/participants;
- fetch meeting metadata;
- fetch summary or transcript when permitted;
- return stable source URL or source ID.

Expected read tools:

- `ktalk_list_recordings`;
- `ktalk_get_recording`;
- `ktalk_get_transcript`;
- `ktalk_get_summary`;
- `ktalk_get_summary_by_type`;
- `ktalk_list_calendar_events`.

Repo-local MCP config shape:

```json
{
  "mcpServers": {
    "ktalk": {
      "command": "python",
      "args": [
        ".mcp/ktalk-readonly/server.py",
        "--config",
        ".claude/local/ktalk-session.json"
      ]
    }
  }
}
```

The repo commits `.mcp/ktalk-readonly/server.py` and safe examples. The repo must not commit `.mcp.json` or `.claude/local/ktalk-session.json`.

The included server may expose guarded meeting create/update tools. Meeting-context skills remain read-only in v0. Guarded scheduling tools may be used only by a separate meeting-scheduling workflow with exact approval and must not weaken current read-only context rules.

## Agent Preflight

Before using KTalk context for a task, agent must verify access with a safe read-only check:

1. confirm the KTalk MCP server is available;
2. confirm expected tools are exposed by server `ktalk`;
3. call `ktalk_list_recordings` with a narrow date/title query or small `top` value;
4. fetch one user-provided meeting/source with `ktalk_get_recording`;
5. confirm summary/transcript access only if the task needs it using `ktalk_get_summary` or `ktalk_get_transcript`;
6. report missing access without printing credentials.

Expected report:

```text
KTalk MCP: available / unavailable
Meeting metadata: available / unavailable
Transcript or summary: available / unavailable
Setup status: ready / partial / blocked
Limitations: <missing MCP server, missing access, expired local auth, source not found, permission issue>
```

## Failure Handling

If KTalk access fails:

- MCP server not connected: guide PM to create or fix local `.mcp.json` from `.mcp.example.json`;
- local config missing: guide PM to create `.claude/local/ktalk-session.json` from `.mcp/ktalk-readonly/ktalk-session.example.json`;
- unauthorized or expired local auth: ask PM to refresh authentication in the local KTalk MCP config;
- forbidden: report permission issue for that meeting/source;
- source not found: ask PM for title/date/link or confirm that the meeting exists;
- transcript unavailable: continue only with metadata/summary if enough, otherwise stop;
- credential printed accidentally: stop, tell PM to rotate/refresh access in the MCP server setup, and remove it from any local logs/files before publishing.

## Privacy Boundary

KTalk is a raw source, not product truth.

Agent may use meeting context to prepare a review packet, summary or payload draft.

Agent must not copy raw transcript text into:

- GitHub;
- examples;
- generated artifacts;
- Product Context Item body;
- official Notion docs by default.

Use source links, timestamps and short sanitized excerpts only when needed.
