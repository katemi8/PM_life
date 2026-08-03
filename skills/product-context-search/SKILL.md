# product-context-search

## When to Use

Use when a PM asks to gather product context for a feature, artifact, question or decision.

## Scope

Search official Notion docs and use KTalk only when meeting context is relevant. Return a compact context summary.

## Inputs

- PM question;
- product/area/feature, if known;
- optional Notion/KTalk links;
- requested answer mode: compact, source-deep or conflict audit.

## Outputs

- official facts;
- meeting-derived candidates, if KTalk was used;
- conflicts;
- open questions;
- suggested next action.

## Read Sources

- official Notion docs;
- KTalk primary source when needed;
- current Notion templates only when artifact creation is requested.

If KTalk is used, raw transcript text must not be copied into GitHub or presented as product truth.

## Read Tools

Use the official hosted Notion MCP:

- use `mcp__notion__.notion_fetch` for known Notion pages, databases and templates;
- use `mcp__notion__.notion_search` for workspace or data-source search;
- use `mcp__notion__.notion_query_database_view` only when the user provided a structured database view and full view coverage is needed.

If the official MCP tools are not visible in the current Codex session, report that the session may need restart. Do not use another Notion connector as a substitute.

## Write Targets

None by default.

If PM asks to update docs, route to the relevant write-capable skill and require approval.

## Approval Rules

Search is read-only. Any follow-up write to official docs must be routed to a write-capable skill and requires preview or diff, explicit approval and readback.

## Workflow

1. Clarify product/area if needed.
2. Verify access and search official Notion docs first through the official Notion MCP.
3. Use KTalk as a raw source only when meeting context is relevant.
4. Separate official facts from meeting-derived candidates.
5. Use plain-language confidence notes.
6. Highlight conflicts and gaps.
7. Return compact answer unless source-deep mode is requested.

## Failure Policy

Report limitations if:

- Notion search/read is unavailable;
- relevant product/area cannot be inferred;
- results contain conflicting official docs;
- relevant KTalk source is unavailable.
- source-deep mode would require exposing raw transcript text beyond the allowed summary/excerpt.

## Examples

Good request:

```text
Собери контекст по premium_status перед продуктовой задачей.
```

Bad behavior:

```text
Presenting captured context as official product truth.
```

## Smoke Tests

- Given a context request, agent separates official docs from meeting-derived candidates.
- Given conflict, agent highlights it instead of choosing silently.
