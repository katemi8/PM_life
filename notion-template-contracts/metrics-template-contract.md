# Metrics Template Contract

Source of truth: current metrics/analytics template in Notion.

The agent must follow the live Notion schema and must not invent event names, parameters or categories without showing a preview.

Read path:

1. Use official Notion MCP `notion_fetch` for schema and view metadata.
2. Use official Notion MCP `notion_query_database_view` for rows from the exact provided metrics view.
3. Use `notion_search` scoped to the data source plus `notion_fetch` only as fallback.

If full view coverage is required and `notion_query_database_view` is unavailable, stop and report the limitation.
