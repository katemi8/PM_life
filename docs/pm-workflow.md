# PM Workflow

Этот документ описывает, как агент должен обрабатывать продуктовые запросы PM.

Основной читатель: агент. PM может читать документ как описание ожидаемого поведения.

## Core Rule

Agent must separate:

- official Notion documentation;
- captured meeting context;
- assumptions;
- open questions;
- proposed changes.

KTalk-derived meeting context is not product truth until it is reflected in official Notion documentation through the normal approval flow.

## Notion Read Flow

Use the official hosted Notion MCP as the supported read path:

- `notion_fetch` for known pages, databases, data sources and templates;
- `notion_query_database_view` for exact Notion database views;
- `notion_search` scoped to workspace or data source as fallback.

For structured databases such as `Метрики ver_10`, view reads should use `notion_query_database_view`. Search plus fetch is acceptable only as partial fallback.

Before relying on a Notion page, database or view, agent must verify that the official Notion MCP can read it. If access is missing, agent reports the missing source and does not pretend the context is complete.

## Default Workflow

1. Identify request type:
   - metrics markup;
   - context search;
   - meeting review;
2. Identify product, area and feature.
3. Verify access and read relevant official Notion docs through the official Notion MCP.
4. Use KTalk only when meeting context is relevant to the request.
5. Separate official facts from meeting-derived candidates.
6. Highlight conflicts, gaps and low-confidence context.
7. Use the relevant skill.
8. Show preview before creating new content, or diff before updating existing content.
9. Wait for explicit approval for the concrete official Notion write.
10. Write only after approval and verify by readback.

## Prompt Examples

```text
Собери контекст по фиче X перед продуктовой задачей.
```

Expected behavior:

- read official docs;
- use KTalk as raw source only when relevant;
- return compact summary by source type and confidence;
- show conflicts/open questions.

```text
Разбери встречу из KTalk.
```

Expected behavior:

- prepare read-only extraction/review packet;
- extract only significant action-worthy points;
- do not copy raw transcript to GitHub.

## Answer Modes

Agent should choose compact mode by default.

Use source-deep mode when:

- there is conflict;
- context is low confidence;
- request affects product rules;
- PM asks for source audit.

## Official Write Preview

Before official Notion write, show:

- target page/database;
- exact new content for creation;
- exact old/new content or properties as diff for updates;
- source docs/items used;
- unresolved assumptions;
- approval phrase or explicit confirmation needed;
- readback verification plan.
