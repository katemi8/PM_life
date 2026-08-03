# metrics-markup

## When to Use

Use when a PM asks to create or update product analytics markup.

## Scope

Prepare analytics events, parameters and schema updates according to the current Notion analytics schema.

Use the official hosted Notion MCP as the supported read path. In Codex fresh sessions this appears as `mcp__notion__`.

## Inputs

- feature description;
- screenshots or flow description, if available;
- target product/area;
- related product artifact or user story;
- existing Notion analytics pages.

## Outputs

- proposed events and parameters;
- mapping to existing schema;
- unresolved questions;
- batch preview for new Notion changes;
- diff preview for changes to existing Notion analytics records.

## Read Sources

- live Notion analytics schema;
- related product artifact or user story;
- existing event/category/parameter pages.

## Read Tools

Supported path:

1. `mcp__notion__.notion_fetch` for the database/view URL, schema and data source details.
2. `mcp__notion__.notion_query_database_view` for rows from the exact Notion view provided by the PM.
3. `mcp__notion__.notion_fetch` for individual event/category/parameter pages when row details are needed.

Partial fallback path:

1. `mcp__notion__.notion_search` scoped to the data source.
2. `mcp__notion__.notion_fetch` for matching pages.
3. Report that search may not cover the whole view.

Use only the official hosted Notion MCP flow for metrics view reads.

## Write Targets

- Notion analytics schema pages only after explicit approval.

## Approval Rules

Any Notion write requires preview or diff plus explicit approval for the concrete batch.

When updating existing analytics records, show old/new fields as a diff before approval.

After an approved write, reread changed records and report whether readback matches the approved preview/diff.

## Workflow

1. Read live Notion analytics schema with `notion_fetch`.
2. If PM provided a metrics view link, query that exact view with `notion_query_database_view`.
3. Identify target feature and user actions.
4. Reuse existing categories and parameters when possible.
5. Propose new events/parameters only when needed.
6. Show batch preview, including diff for existing records.
7. Wait for approval.
8. Write and verify by readback.

## Failure Policy

Stop and report if:

- schema cannot be read;
- the exact Notion view must be covered but `notion_query_database_view` is unavailable;
- target feature is ambiguous;
- existing schema conflicts with proposed markup;
- approval is missing.

## Examples

Good request:

```text
Подготовь разметку метрик для нового экрана, но сначала покажи batch preview.
```

Bad behavior:

```text
Creating new event parameters without checking the live Notion schema.
```

## Smoke Tests

- Given a feature description, agent proposes events and marks reused/new schema elements.
- Given a Notion metrics view URL, agent uses `notion_fetch` and `notion_query_database_view` before proposing events.
- Given unavailable view query, agent falls back to scoped `notion_search` plus page fetch and marks coverage as partial.
- Given an existing analytics record update, agent shows a field diff before asking for approval.
- Given missing approval, agent does not write to Notion.
