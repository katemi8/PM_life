# Notion MCP

Этот документ фиксирует рабочий read-flow для Notion.

Основной читатель: агент. PM может открыть документ, чтобы понять, какие Notion tools должны быть доступны.

Для подключения Notion MCP в **Cursor / PM-Live** см. также [`notion-mcp-cursor.md`](notion-mcp-cursor.md).

## Status

Current v0 uses the official hosted Notion MCP as the only supported Notion read path.

For Codex, the expected config is:

```powershell
codex mcp add notion --url https://mcp.notion.com/mcp
```

This writes the server config to the user's Codex MCP configuration.

Equivalent config shape:

```toml
[mcp_servers.notion]
url = "https://mcp.notion.com/mcp"
```

Then authenticate:

```powershell
codex mcp login notion
```

Expected check:

```powershell
codex mcp list
codex mcp get notion
```

The `notion` server should be `enabled`, use `streamable_http`, and show OAuth auth.

Each PM authenticates with their own Notion account. Current v0 does not use a shared Notion service account.

## Supported Tools

In a fresh Codex session, the official Notion MCP appears as `mcp__notion__`.

Use these tools for Notion reads:

- `mcp__notion__.notion_fetch` to read pages, databases, data sources and schemas;
- `mcp__notion__.notion_query_database_view` to read rows from an existing Notion database view;
- `mcp__notion__.notion_search` to search workspace content or a specific data source.

Before relying on a page, database or view, verify that the official Notion MCP can actually read it. If access is missing, report the missing page/database/view instead of continuing as if coverage is complete.

Equivalent official MCP tool names are:

- `notion-fetch`;
- `notion-query-database-view`;
- `notion-search`.

## Database View Read Flow

When the PM provides a Notion database view link:

1. Fetch the database or view URL with `notion_fetch`.
2. Read the database schema, data source URL and view configuration.
3. Query the exact view with `notion_query_database_view`.
4. Fetch individual pages only when row details or page content are needed.
5. Summarize fields and links; do not copy unrelated private database content.

This is the primary flow for `Метрики ver_10` and other structured Notion databases.

## Metrics Read Flow

For analytics markup:

1. Fetch `Метрики ver_10` or the provided view URL.
2. Query the relevant view with `notion_query_database_view`.
3. Reuse existing `event_page`, `event_category`, `Группы параметров`, `Параметры TrendAgent`, `Custom group` and `Счетчик` values when they match.
4. Propose new schema objects only when existing records do not cover the feature.
5. Show batch preview before any write.

## Fallback

If `notion_query_database_view` is unavailable:

1. Use `notion_search` scoped to the data source.
2. Fetch matching pages one by one with `notion_fetch`.
3. Clearly state that the result may not cover the whole view.
4. Stop if full view coverage is required for the task.

Do not silently pretend that search results are a complete database export.

## Session Note

After adding the official Notion MCP, already-open Codex chats may still have stale tool discovery. A new Codex session may be required before `mcp__notion__` appears.
