# Install

Этот документ описывает, как подключить `TA-agent-system` к продуктовому workspace.

Основной читатель: агент. PM может открыть документ, чтобы понять процесс.

## Status

Published v0 install flow for GitHub repo `TrendPM/AI-Skills`: `https://github.com/TrendPM/AI-Skills`.

После публикации установка для PM начинается с clone repo, затем PM запускает установочный skill `agent-system-install`. Commit/push, tags и releases выполняются только в repo maintenance flow, а не в PM first-run setup.

## PM First-Run Command

После clone PM открывает repo агенту и пишет:

```text
Я склонировал TrendPM/AI-Skills. Используй skills/agent-system-install/SKILL.md и настрой этот проект для моей работы.
```

Agent must follow `skills/agent-system-install/SKILL.md`.

## Goal

После установки агент в продуктовом workspace должен:

- видеть доступные team skills;
- соблюдать общие правила approval;
- понимать, что Notion является source of truth;
- использовать официальный Notion MCP для чтения Notion;
- использовать project-local KTalk MCP server из repo;
- не переносить продуктовую правду в GitHub;
- использовать KTalk только как raw source для summary и review packet.

## External Tool Requirements

### Official Notion MCP

Supported Notion read access is the official hosted Notion MCP.

For Codex:

```powershell
codex mcp add notion --url https://mcp.notion.com/mcp
```

Equivalent config shape:

```toml
[mcp_servers.notion]
url = "https://mcp.notion.com/mcp"
```

Authenticate:

```powershell
codex mcp login notion
```

Verify:

```powershell
codex mcp list
codex mcp get notion
```

Expected result: server `notion` is enabled, uses `streamable_http`, and has OAuth auth. Each PM authenticates with their own Notion account.

In a fresh Codex session the tools should appear as:

- `mcp__notion__.notion_fetch`;
- `mcp__notion__.notion_query_database_view`;
- `mcp__notion__.notion_search`.

If these tools do not appear after setup, restart the Codex session and check again.

### KTalk / Контур.Толк

KTalk access is configured through the project-local MCP server included in this repo. See `docs/ktalk-access.md` and `docs/mcp-servers.md`.

Rules:

- use `.mcp/ktalk-readonly/server.py`;
- create local `.mcp.json` from `.mcp.example.json`;
- create local `.claude/local/ktalk-session.json` from `.mcp/ktalk-readonly/ktalk-session.example.json`;
- expected MCP server name: `ktalk`;
- during install or first run, agent guides PM through this connection;
- use the PM's own KTalk account/access through local ignored config;
- keep any credential/session handling inside `.claude/local/`;
- never commit or paste `sessionToken`;
- run a read-only KTalk preflight before meeting workflows.

## Installation Model

Базовая модель для текущего MVP:

1. PM clones `TrendPM/AI-Skills`.
2. PM opens the cloned repo in the agent workspace.
3. PM runs the first-run command above.
4. Agent follows `skills/agent-system-install/SKILL.md`.
5. Agent checks `manifest.json` and confirms target repo = `TrendPM/AI-Skills`.
6. Agent verifies `AGENTS.md`, `.mcp/`, `skills/`, `contracts/`, `notion-template-contracts/`, `docs/` and `scripts/`.
7. Agent checks official Notion MCP tools.
8. Agent guides PM through project-local KTalk MCP setup if meeting workflows are needed.
   - expected server: `ktalk`;
   - server file: `.mcp/ktalk-readonly/server.py`;
   - local MCP config template: `.mcp.example.json`;
   - local KTalk config template: `.mcp/ktalk-readonly/ktalk-session.example.json`;
   - expected read tools: `ktalk_list_recordings`, `ktalk_get_recording`, `ktalk_get_transcript`, `ktalk_get_summary`, `ktalk_get_summary_by_type`, `ktalk_list_calendar_events`.
9. Agent runs local checks and smoke prompt.
10. Agent reports install status: ready / partial / blocked.

## Agent Install Steps

Выполнять из корня cloned repo (`AI-Skills` by default, or another local folder name):

```powershell
python scripts\validate-skills.py
python scripts\smoke-skills.py
python scripts\validate-manifest.py
python scripts\scan-secrets.py
python -m json.tool .mcp.example.json
python -m json.tool .mcp\ktalk-readonly\ktalk-session.example.json
python -m json.tool manifest.json
python -m json.tool manifest.example.json
git diff --check
```

`git diff --check` применяется после git initialization. Если любая проверка падает, установка не считается завершенной. Агент должен показать файл и правило, которое не прошло проверку.

После проверок агент должен подтвердить:

- какие skills доступны;
- какие contracts подключены;
- какой target repository указан в `manifest.json`;
- какие external tools доступны;
- готов ли KTalk MCP для meeting workflows: ready / partial / blocked;
- какие локальные действия нужны PM, если доступы не готовы.

## Smoke Prompt

```text
Проверь, какие skills доступны в этом repo, и объясни, как ты будешь работать с Notion и KTalk.
```

Expected behavior:

- agent lists available skills;
- agent says that Notion is product documentation source of truth;
- agent says that official Notion MCP is the supported read path;
- agent verifies required Notion pages/databases/views before using them;
- agent says that official Notion writes require explicit approval;
- agent says that KTalk raw transcripts must not be copied into GitHub.
- agent guides PM through project-local KTalk MCP setup if KTalk is unavailable;
- agent reports KTalk setup status as ready, partial or blocked.

## Install Checklist

- `AGENTS.md` copied or connected.
- `.mcp/ktalk-readonly/server.py` available.
- `.mcp.example.json` available as the local MCP config template.
- `skills/` available to the agent.
- `contracts/` available to the agent.
- `manifest.json` target repo is `TrendPM/AI-Skills`.
- Official Notion MCP read access available.
- KTalk MCP server connected from the repo-local `.mcp/ktalk-readonly/server.py` if meeting workflows are needed.
- Agent-guided KTalk first-run preflight completed.
- No KTalk credentials stored in repo.
- No local secrets committed to repo.
- `python scripts/validate-skills.py` passes.
- `python scripts/smoke-skills.py` passes.
- `python scripts/validate-manifest.py` passes.
- `python scripts/scan-secrets.py` passes.
- MCP example JSON files are valid.
- manifest JSON files are valid.
