# Metrics Markup Good Example

Status: current v0 example.

This file shows the expected shape of an agent result for product analytics markup. It is not a Notion template and not a replacement for the live analytics schema.

## Source Basis

The source of truth is the Notion database `Метрики ver_10`.

The example is based on the current database schema and real good-reference views provided by PMs:

- `Ипотечный калькулятор`;
- `Вознаграждения`;
- `Премиум`;
- other feature-specific views from the same database when the PM provides links.

The agent must always reread the live Notion schema before preparing a batch. Stored examples can only show the expected reasoning and output shape.

Preferred read path:

1. `mcp__notion__.notion_fetch` for the database/view URL and schema.
2. `mcp__notion__.notion_query_database_view` for rows from the provided view.
3. `mcp__notion__.notion_search` plus `notion_fetch` only as fallback when full view coverage is not required.

## PM Request

```text
Подготовь разметку метрик для нового экрана/флоу. Возьми за основу уже размеченные события из Метрики ver_10 и сначала покажи batch preview.
```

## Required Read Step

Before drafting events, the agent reads:

- target feature description, screenshots or flow;
- related product artifact, user story or Jira link if available;
- live `Метрики ver_10` schema;
- existing events in the relevant Notion views;
- related `event_page`, `event_category`, `Группы параметров`, `Параметры TrendAgent` and `Custom group` records.

The agent should explicitly separate reused schema objects from new proposed objects.

If `notion_query_database_view` is not available, the agent must say whether it can continue with partial search results or must stop.

## Good Reference Patterns

| Pattern | What Makes It Good |
| --- | --- |
| View-based grouping | Feature views group all related events by Jira/product area, so the agent can compare a new batch with the closest existing batch. |
| Clear event name | `event_name (event_group)` uses a stable analytics-style name such as `page_view_*`, `click_*`, `select_*` or `view_*`. |
| Human title | `Название` explains the user action in product language. |
| Trigger text | `Описание/триггер web` describes when the event fires and when it should not fire. |
| Reused relations | `event_page`, `event_category`, `Группы параметров`, `Параметры TrendAgent` and `Custom group` are reused when the existing schema already covers the case. |
| Platform status | `Статус задачи (web)` and `Статус задачи (app)` are filled separately when the event exists on both platforms. |
| Counter clarity | `Счетчик` shows whether the event goes to `яндекс.метрика`, `app.метрика` or both. |
| Jira/source link | `Ссылка на джиру` links the event batch to the product task or feature marker. |

## Example Agent Output

### Source Check

- Live schema read: yes.
- Exact view query completed: yes, through official Notion MCP.
- Closest examples found: feature-specific views in `Метрики ver_10`.
- Existing schema reused: pages, categories and common parameter groups.
- New schema objects proposed: only if no existing relation matches the feature.
- Write target: Notion analytics database only after explicit approval.

### Proposed Events

| Action | `event_name (event_group)` | `Название` | Trigger | Reused Schema | New Schema |
| --- | --- | --- | --- | --- | --- |
| Page or screen is opened | `page_view_<feature>` | Просмотр страницы/экрана | User opens the target page or screen. | Existing page/category if present. | New page only if the feature has no matching page. |
| User clicks a primary entry point | `click_<feature>_entry` | Клик по точке входа | User clicks the entry point that opens the feature. | Existing click category and common user/session parameters. | New custom group only if the feature needs unique parameters. |
| User changes a selector/filter | `select_<feature>_<field>` | Выбор значения в фильтре | User selects a value different from the current one. | Existing selector/filter parameters if present. | New parameter only if the selected value is not represented in the schema. |

### Batch Preview

The agent shows the batch before any write:

```text
Will create:
- 2 new events in Метрики ver_10.

Will update:
- 1 existing event. Diff preview required before update.

Will reuse:
- existing event_page;
- existing event_category;
- existing parameter groups;
- existing counters.

Needs PM approval:
- confirm that the trigger is correct;
- confirm whether the event is web-only, app-only or both;
- confirm whether a new custom parameter is actually needed.
```

### Update Diff

If an existing event is changed, the preview must include a diff for the changed fields:

```diff
- Описание/триггер web: fires when the user opens the block.
+ Описание/триггер web: fires when at least the agreed visible part of the block is shown; does not fire for the empty state.
```

## Good Result Criteria

- The agent does not invent event pages, categories or parameters before checking Notion.
- Every event has a clear trigger and a clear non-trigger when relevant.
- The event name is stable and implementation-friendly.
- The PM can review the batch without opening every Notion relation manually.
- Existing Notion records are changed only after explicit approval and readback verification.
