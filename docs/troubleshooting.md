# Troubleshooting

Этот документ описывает типовые сбои и ожидаемую реакцию агента.

## Notion Template Not Found

Agent must not use a stale local template.

Expected behavior:

- report missing template;
- ask PM for the current Notion template link or location;
- stop before creating final artifact.

## Official Notion MCP Not Visible

If `codex mcp list` shows `notion` but the current chat does not expose `mcp__notion__` tools:

- report that the current session may have cached tool discovery;
- start a fresh Codex session or restart Codex;
- verify `codex mcp get notion`;
- do not downgrade a full database-view task to partial search without saying so.

## Notion Database View Query Unavailable

If the task requires a complete Notion database view and `notion_query_database_view` is unavailable:

- use `notion_search` scoped to the data source only as a partial fallback;
- fetch matching pages individually;
- clearly state that coverage is partial;
- stop if the task requires full view coverage.

## Missing Approval

If the request requires official Notion write and approval is missing:

- show preview for new content, or diff for existing document updates;
- ask for explicit approval;
- do not write.

## Readback Failed

If a Notion write was approved but readback does not match the approved preview/diff:

- report the mismatch;
- do not claim the write succeeded;
- show expected vs actual at the smallest practical scope;
- ask PM whether to retry, revert through a new approved change, or leave as-is.

## KTalk Source Not Available

If KTalk source cannot be fetched:

- report source and error class;
- continue only with already available official docs;
- mark meeting-derived context as unavailable.

If KTalk MCP is unavailable, unauthorized or reports expired local auth:

- verify `.mcp/ktalk-readonly/server.py` exists;
- ask PM to create or fix local `.mcp.json` from `.mcp.example.json`;
- ask PM to create or refresh `.claude/local/ktalk-session.json` according to `docs/ktalk-access.md`;
- do not ask PM to paste token into chat;
- do not print existing local token values.
- after PM updates local MCP setup, rerun the read-only KTalk preflight and report ready / partial / blocked.

## Conflict Between Sources

If captured context conflicts with official docs:

- do not silently update the doc;
- mark conflict;
- show both sides;
- ask owner/PM for resolution.

## Stale Skill Version

If skill behavior does not match docs/contracts:

- report suspected stale version;
- point to update flow;
- do not guess new behavior.
